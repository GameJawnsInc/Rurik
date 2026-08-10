"""Write an anonymised copy of the portal captures, leaving the originals alone.

WHY. The client sends the owner's real ArenaNet credential to our own webgate on every
login, and we record what the client sent, because recording what the client actually
sent is the whole method. `vault/captures/portal/*.jsonl` therefore holds, per session:
the account email (in `email` and again in the body's `<LoginName>`), the password as
base64 inside `<Password>`, the account alias, the issued session token, and the
`Authorization: Arena <token>` header on every subsequent request.

None of it has ever been in git -- `vault/` was gitignored in the first commit, before
any content existed. The exposure is that the vault is the single copy of the most
valuable artifact in the project and cannot be backed up anywhere off this machine
while it carries a live credential. That was recorded as a blocker; it is a filter.

WHAT THIS IS NOT. It does not touch the originals and it is not a fidelity reduction.
The original captures stay exactly as recorded, because a scrubbed capture is evidence
about a session and an original capture is evidence about the protocol, and the second
one is why we record at all. This writes a second, derived set that is safe to copy.

HOW THE SUBSTITUTION WORKS, and why not a hash.

  * Placeholders are assigned SEQUENTIALLY in order of first appearance, not derived
    from the value. A hash would be reversible here: the password is short, and
    anyone holding the scrubbed file plus the hash function could brute-force it in
    seconds. Sequential assignment carries no information about the input at all.
  * The mapping is one-to-one and global, so the same value gets the same placeholder
    everywhere it appears -- the email in the `email` field and the same email inside
    `<LoginName>` land on the same token. Correlation survives; identity does not.
  * Placeholders are the SAME LENGTH as what they replace. Body length is protocol
    -relevant (it is the Content-Length the client sent) and the base64 width of the
    password field is a fact about the encoding. Changing lengths would quietly corrupt
    exactly the thing the capture exists to preserve.
  * The mapping is held in memory and written nowhere. The manifest records COUNTS per
    field, never values.

The tree is read through a `Snapshot` (below), not walked live, because a running server
appends to `vault/captures/` while this is working and a caller that also counts records
would otherwise be counting a moving corpus.

The `Arena 0` authorization header is NOT redacted: the literal `0` is what the client
sends before it has a token, it is documented in studies/handshake/PLAN.md, and it is
not a secret. Only the 36-character token form is replaced.

    python toolkit/scrub_captures.py                    # portal -> portal-scrubbed
    python toolkit/scrub_captures.py --check            # report what would be replaced
    python toolkit/scrub_captures.py --src X --out Y

Proved by `toolkit/test_scrub.py`, which asserts that no original secret value survives
anywhere in the output -- the check that can actually fail, as opposed to trusting that
the field list below is complete.
"""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vaultpath  # noqa: E402

# Top-level JSONL keys whose whole value is account-identifying or is session key
# material. The first three were all this tool covered when it only ran against
# captures/portal; the rest are why it now walks the whole tree. MEASURED 2026-08-06
# across the other capture directories: 206 `email`, 113 `account_uuid`, 113
# `char_uuid` and 341 ARC4 keys/seeds sat entirely outside the scrubber, and
# RUNBOOK's own off-disk recipe shipped them.
#
# The key material is loopback-only today -- it keys our own server, so it unlocks
# nothing of ArenaNet's -- and is scrubbed anyway, because the moment a live session
# is captured the identical fields carry a real session key and nobody should be
# relying on remembering to change the policy on that day.
SECRET_KEYS = {
    "email": "email",
    "token": "tokn",
    "user_id": "uid",
    "account_uuid": "acct",
    "char_uuid": "char",
    "arc4_key": "key",
    "master_secret": "msec",   # what the key-tap cave reads; arc4_key is its hash
    "a": "dh",          # client DH public value
    "sent": "seed",     # server seed
}

# XML elements whose text is account-identifying, in EITHER direction. The request
# body carries the credential; the reply carries the session it issued and the account
# it belongs to. The first version of this list had only the request half, and
# test_scrub.py caught 181 values still leaking through `response` -- which is exactly
# the failure a "did it run" test passes and this one does not. Do not trim this list
# without re-running that test.
SECRET_ELEMENTS = {
    # request -> us
    "LoginName": "email",   # the same address as the `email` key -- shares its mapping
    "Password": "pw",
    "AccountAlias": "alias",
    # us -> client
    "Session": "sess",
    "Token": "tokn",
    "ResumeToken": "rtok",
    "UserId": "uid",
    "UserName": "user",
    "Alias": "alias",
}

# Deliberately NOT redacted, and each for a reason: `Provider` and `GameCode` are
# constants of the protocol, `EmailVerified` and `Row` are flags, `Created` is a
# timestamp, and `UserCenter` is a region rather than an account. If any of these turns
# out to identify the account, test_scrub.py's leak check is what will say so.
XML_FIELDS = ("body", "response")

# `Authorization: <scheme> <credential>`. The credential is only a secret when it is a
# real token; the literal "0" is the pre-login sentinel and is documented behaviour.
AUTH_SENTINELS = {"0"}

# Keys whose value is a HUMAN-READABLE LINE with secrets embedded in it, rather than a
# secret on its own. `who` is authsrv's login_ok log line -- "<account_uuid> / token
# <token>" -- so whole-value substitution does nothing for it: the string is unique per
# session and the pseudonym would just be a different unique string of the same length.
#
# This was the third field the leak check found that nobody had listed, after `response`
# and the whole authsrv/ directory. Each time, the harvest-then-search design caught what
# a field list could not, which is the argument for keeping the test built that way.
COMPOSITE_KEYS = ("who",)

# Keys whose value is an OPAQUE PAYLOAD -- a hex blob of protocol bytes -- which this tool
# cannot clean and must therefore not appear to have cleaned.
#
# It is not a hypothetical. MEASURED 2026-08-07 over the vault's 401 captures that carry a
# first c2s frame: the auth channel's opening client message is opcode 0x8001 followed by a
# UTF-16 string, and that string is the ACCOUNT EMAIL -- 271 captures begin `0180 0500
# 7300 6b00 ...`, which is the owner's own address, one byte pair at a time. The scrubber
# matches JSON keys, the address here is bytes inside a value, and `plain` was in no list,
# so scrub_record fell through to `else: out[key] = value` and copied it verbatim into
# captures-scrubbed/ -- the tree RUNBOOK names as the one that may leave the machine.
#
# Redacting the blob is not the fix: it is the capture. So the policy is to REPORT rather
# than pretend -- the manifest names every file that still holds one, and the tool says so
# on the way out. A live capture makes this sharper, because then the same field holds a
# real session against ArenaNet rather than one against ourselves.
# `payload` joined the list on 2026-08-07, put there by the first live capture rather than
# by review: wirecapture's raw records hold the PLAINTEXT DH handshake as hex, so the same
# `a` and `sent` values the scrub carefully redacts in their own fields sit in the clear
# inside payload, two records earlier. test_scrub's leak check found both the first time a
# live capture entered the corpus -- which is the check working, not failing.
OPAQUE_KEYS = ("plain", "payload")
OPAQUE_STAT = "NOT_CLEANED_opaque_payload"

# 8-4-4-4-12 hex. Matching the shape rather than the field means a UUID picks up the same
# pseudonym here as it does in `account_uuid`, so correlation survives across both.
UUID_RE = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}"
                     r"-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b")


def scrub_composite(value, names, stats):
    """Replace every UUID inside a log line, leaving the prose around it intact."""
    def repl(m):
        stats["composite_uuid"] = stats.get("composite_uuid", 0) + 1
        return names.get(m.group(0), "id")
    return UUID_RE.sub(repl, value)


class Pseudonyms:
    """Value -> same-length placeholder, assigned in order of first appearance."""

    def __init__(self):
        self._map = {}
        self._n = 0

    def get(self, value, label):
        if value in self._map:
            return self._map[value]
        self._n += 1
        placeholder = self._make(label, self._n, len(value))
        if placeholder in self._map.values():
            raise RuntimeError(
                f"placeholder collision on {label!r} at length {len(value)}: "
                "two distinct secrets would become indistinguishable, which "
                "destroys the correlation this is supposed to preserve")
        self._map[value] = placeholder
        return placeholder

    @staticmethod
    def _make(label, index, length):
        """A placeholder of exactly `length` characters, unique per index."""
        core = f"{label}{index}"
        if length <= 0:
            return ""
        if len(core) >= length:
            # Not enough room to be readable; keep the digits, they carry uniqueness.
            return core[-length:]
        return core + "x" * (length - len(core))

    def count(self):
        return len(self._map)


def scrub_xml(payload, names, stats):
    """Replace the text of every secret element in an XML payload, preserving length."""
    def repl(m):
        tag, text = m.group(1), m.group(2)
        label = SECRET_ELEMENTS[tag]
        stats[tag] = stats.get(tag, 0) + 1
        return f"<{tag}>{names.get(text, label)}</{tag}>"

    pattern = re.compile(
        r"<(" + "|".join(map(re.escape, SECRET_ELEMENTS)) + r")>(.*?)</\1>")
    return pattern.sub(repl, payload)


def scrub_record(rec, names, stats):
    """One JSONL record in, one anonymised record out. Shape is never changed."""
    out = {}
    for key, value in rec.items():
        if key in SECRET_KEYS and isinstance(value, str) and value:
            out[key] = names.get(value, SECRET_KEYS[key])
            stats[key] = stats.get(key, 0) + 1
        elif key in SECRET_KEYS and isinstance(value, int):
            # user_id arrives as a number in some records. Keep the type.
            out[key] = names.get(str(value), SECRET_KEYS[key])
            stats[key] = stats.get(key, 0) + 1
        elif key == "authorization" and isinstance(value, str):
            out[key] = scrub_auth(value, names, stats)
        elif key in XML_FIELDS and isinstance(value, str):
            out[key] = scrub_xml(value, names, stats)
        elif key in COMPOSITE_KEYS and isinstance(value, str):
            out[key] = scrub_composite(value, names, stats)
        elif key in OPAQUE_KEYS and isinstance(value, str) and value:
            # Passed through UNCHANGED, and counted. The count is the whole point: this is
            # the one field the tool knowingly does not clean, and a silent pass-through is
            # indistinguishable from "there was nothing to do".
            stats[OPAQUE_STAT] = stats.get(OPAQUE_STAT, 0) + 1
            out[key] = value
        else:
            out[key] = value
    return out


def scrub_auth(value, names, stats):
    parts = value.split(" ", 1)
    if len(parts) != 2 or parts[1] in AUTH_SENTINELS:
        return value
    stats["authorization"] = stats.get("authorization", 0) + 1
    return f"{parts[0]} {names.get(parts[1], 'tokn')}"


class SnapshotChanged(Exception):
    """A snapshotted file no longer holds the bytes the snapshot recorded.

    Growth is invisible to a snapshot by construction -- that is the whole point.
    Truncation and deletion are not: they mean the corpus a claim is about is gone,
    and a short read would quietly shrink every count downstream instead of saying so.
    """


class Snapshot:
    """A capture tree pinned to one instant: the file list, and how long each file was.

    WHY THIS EXISTS. `vault/captures/` is APPENDED TO by a running authsrv/gamesrv, and
    anything that audits the scrub reads the tree more than once -- harvest the secrets,
    scrub, count the lines, compare original against output. On 2026-08-10
    `toolkit/test_scrub.py` went red twice with "326648 in, 326631 out, 15 unparseable".
    Nothing was wrong with the scrubber: a session was live, and two records had been
    appended between the scrub pass and the pass that counted the originals -- so the
    "in" side counted two lines the "out" side never had the chance to write. The
    arithmetic was right. The corpus was moving.

    Neither obvious repair is acceptable. Relaxing the arithmetic gives up the check that
    caught 181 real values leaking through `response`. Skipping while a server is up
    deletes the check exactly when captures are being written, which is when it matters.

    So instead every pass reads the SAME BYTES: enumerate once, remember each file's
    length, and never read past it. Records appended after the snapshot are simply not
    part of the corpus under test, and a file that appears afterwards is not in it at all.
    The claim becomes one about a fixed corpus, which is the only kind of claim record
    arithmetic can honestly make.
    """

    def __init__(self, root, skip=()):
        self.root = os.path.abspath(root)
        entries = []
        for base, dirs, fnames in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in skip]
            rel = os.path.relpath(base, self.root)
            for name in sorted(fnames):
                try:
                    size = os.path.getsize(os.path.join(base, name))
                except OSError:
                    # Gone between the walk and the stat. It was never in the snapshot,
                    # so nothing downstream will go looking for it.
                    continue
                entries.append((os.path.normpath(os.path.join(rel, name)), size))
        self.entries = sorted(entries)
        self._size = dict(self.entries)

    def jsonl(self):
        """(relpath, size) for every .jsonl in the snapshot, in a stable order."""
        return [(rel, n) for rel, n in self.entries if rel.endswith(".jsonl")]

    def raw(self):
        """(relpath, size) for every .raw -- recorded, never read, never copied."""
        return [(rel, n) for rel, n in self.entries if rel.endswith(".raw")]

    def total_bytes(self):
        return sum(n for _rel, n in self.entries)

    def text(self, rel, encoding="utf-8"):
        """Exactly the bytes recorded for `rel`, decoded. Never one byte more."""
        size = self._size[rel]
        try:
            with open(os.path.join(self.root, rel), "rb") as fh:
                data = fh.read(size)
        except OSError as exc:
            raise SnapshotChanged(f"{rel}: gone since the snapshot ({exc})") from exc
        if len(data) != size:
            raise SnapshotChanged(
                f"{rel}: the snapshot recorded {size} bytes and only {len(data)} are "
                "there now -- the corpus shrank under the run, so counts taken before "
                "and after would be about two different things")
        return data.decode(encoding, "replace")

    def lines(self, rel, encoding="utf-8"):
        """The snapshotted file's lines. `split`, not `splitlines`: the only thing that
        ends a line here is the newline text mode used to see, and a stray U+0085 inside
        a record must not silently become two records."""
        return self.text(rel, encoding).split("\n")


def scrub_tree(src, out, dry_run=False, skip=(), snapshot=None):
    """Scrub every .jsonl under `src` AND its subdirectories into `out`.

    Walks, because the credential was never only in captures/portal. Directory
    structure is preserved so a scrubbed tree can stand in for the original.

    Reads through a `Snapshot` always -- taken here when the caller does not supply one.
    A caller whose own passes have to agree with these counts must pass the same
    snapshot it read from; see `Snapshot` for the run that made that necessary. `skip`
    belongs to building the snapshot, so passing both is refused rather than ignored.
    """
    src, out = os.path.abspath(src), os.path.abspath(out)
    if os.path.normcase(src) == os.path.normcase(out):
        raise SystemExit("refusing to scrub a directory into itself")
    if snapshot is None:
        snapshot = Snapshot(src, skip=skip)
    else:
        if skip:
            raise ValueError(
                "skip= is applied when the snapshot is built, not here -- passing it "
                "with a snapshot would silently do nothing")
        if os.path.normcase(snapshot.root) != os.path.normcase(src):
            raise ValueError(
                f"snapshot is of {snapshot.root} but the scrub was asked for {src}: the "
                "counts would describe a different tree than the one being written")
    names, stats = Pseudonyms(), {}
    files = records = 0
    unscrubbed = [rel for rel, _n in snapshot.raw()]
    opaque_files = []
    for rel, _size in snapshot.jsonl():
        files += 1
        opaque_before = stats.get(OPAQUE_STAT, 0)
        lines = []
        for line in snapshot.lines(rel):
            line = line.strip()
            if not line:
                continue
            records += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                stats["UNPARSEABLE"] = stats.get("UNPARSEABLE", 0) + 1
                continue
            lines.append(json.dumps(scrub_record(rec, names, stats)))
        if stats.get(OPAQUE_STAT, 0) > opaque_before:
            opaque_files.append(rel)
        if not dry_run:
            os.makedirs(os.path.join(out, os.path.dirname(rel)), exist_ok=True)
            with open(os.path.join(out, rel), "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + ("\n" if lines else ""))
    if not dry_run:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "SCRUB-MANIFEST.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({
                "source": src, "files": files, "records": records,
                "distinct_secrets_replaced": names.count(),
                "replacements_by_field": dict(sorted(stats.items())),
                "NOT_SCRUBBED": unscrubbed,
                "NOT_CLEANED_opaque_payloads": opaque_files,
                "note": "Placeholders are sequential, not derived from the values. "
                        "No mapping is stored anywhere. Lengths are preserved. "
                        ".raw files are NOT scrubbed and are not copied -- they are "
                        "the undecoded byte stream and nothing here parses them.",
                "WARNING": (
                    f"{len(opaque_files)} file(s) here still carry `plain` frame "
                    f"payloads, copied through UNCHANGED. This tool matches JSON keys "
                    f"and cannot see inside a hex blob of protocol bytes -- and the auth "
                    f"channel's first client message embeds the account email as UTF-16 "
                    f"inside exactly such a blob (MEASURED over 271 captures). A tree "
                    f"listed here is NOT safe to hand to anyone. See "
                    f"NOT_CLEANED_opaque_payloads."
                ) if opaque_files else "No opaque payloads: every field here was cleanable.",
            }, fh, indent=2)
    return files, records, stats, names.count(), unscrubbed


DO_NOT_SHARE = "DO-NOT-SHARE.txt"


def mark_tree_unsafe(root, session, files, count):
    """Invalidate a scrubbed tree's all-clear when a session lands in it uncleanable.

    THE HAZARD THIS CLOSES, found by adversarial review 2026-08-07 and confirmed on disk.
    `vault/captures-scrubbed/` carries a root SCRUB-MANIFEST.json describing the tree, and
    RUNBOOK names that tree as the copy which may go off this machine. The live driver
    started writing per-session scrubbed output INTO it -- and the root manifest, written
    2026-08-06 before any live capture existed, still said `files: 421`, carried no
    WARNING, and had no NOT_CLEANED_opaque_payloads key at all.

    So a human reading the top-level report got an ALL-CLEAR on a tree that by then
    contained the account name as UTF-16 inside a `plain` frame payload -- MEASURED in
    live-20260807T143055's auth channel. The per-session manifest one level down said so
    correctly; nobody copying a directory reads one level down.

    A stale all-clear is worse than no report. This writes a plain-text refusal at the root
    that any file manager shows, and stamps the same fact into the root manifest if one is
    there, so the tree cannot look safe while it is not.
    """
    os.makedirs(root, exist_ok=True)
    line = (f"{session}: {count} `plain` frame payload(s) across {len(files)} file(s) "
            f"copied through UNCLEANED")
    path = os.path.join(root, DO_NOT_SHARE)
    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            existing = fh.read()
    if line not in existing:
        with open(path, "a", encoding="utf-8") as fh:
            if not existing:
                fh.write(
                    "THIS TREE IS NOT SAFE TO SHARE.\n"
                    "\n"
                    "The scrub matches JSON keys and cannot see inside a hex blob of\n"
                    "protocol bytes. The auth channel's first client message carries the\n"
                    "account email as UTF-16 INSIDE such a blob, so `plain` frame payloads\n"
                    "are copied through verbatim and the credential travels with them.\n"
                    "\n"
                    "Sessions that put uncleanable payloads in this tree:\n")
            fh.write(f"  - {line}\n")
    man = os.path.join(root, "SCRUB-MANIFEST.json")
    if os.path.exists(man):
        try:
            with open(man, encoding="utf-8") as fh:
                data = json.load(fh)
            data["WARNING"] = (
                f"STALE AND SUPERSEDED. Live capture sessions were scrubbed into this tree "
                f"after this manifest was written, and they carry `plain` frame payloads "
                f"the scrub cannot clean. See {DO_NOT_SHARE}. Re-run "
                f"`python toolkit/scrub_captures.py --force` to regenerate.")
            with open(man, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except (OSError, json.JSONDecodeError):
            pass
    return path


def scrub_dir(src, out, dry_run=False):
    """Scrub every .jsonl directly under `src` into `out`. One flat directory."""
    src, out = os.path.abspath(src), os.path.abspath(out)
    if os.path.normcase(src) == os.path.normcase(out):
        raise SystemExit("refusing to scrub a directory into itself -- the originals "
                         "are the evidence and this tool never edits them")

    names, stats = Pseudonyms(), {}
    files = sorted(f for f in os.listdir(src) if f.endswith(".jsonl"))
    if not files:
        raise SystemExit(f"no .jsonl under {src}")

    if not dry_run:
        os.makedirs(out, exist_ok=True)

    records = 0
    for name in files:
        lines = []
        with open(os.path.join(src, name), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records += 1
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    # Refuse to guess. A line we cannot parse is a line we cannot
                    # promise we scrubbed, so it does not go in the safe copy.
                    stats["UNPARSEABLE"] = stats.get("UNPARSEABLE", 0) + 1
                    continue
                lines.append(json.dumps(scrub_record(rec, names, stats)))
        if not dry_run:
            with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + ("\n" if lines else ""))

    if not dry_run:
        manifest = {
            "source": os.path.basename(src),
            "files": len(files),
            "records": records,
            "distinct_secrets_replaced": names.count(),
            "replacements_by_field": dict(sorted(stats.items())),
            "note": "Placeholders are sequential, not derived from the values. "
                    "No mapping is stored anywhere. Lengths are preserved.",
        }
        with open(os.path.join(out, "SCRUB-MANIFEST.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
    return files, records, stats, names.count()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=None, help="capture root (default: vault captures)")
    ap.add_argument("--out", default=None, help="output dir")
    ap.add_argument("--check", action="store_true",
                    help="report what would be replaced; write nothing")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing output directory")
    args = ap.parse_args()

    src = args.src or vaultpath.require_dir(
        "captures", why="the credential scrub reads the capture tree")
    out = args.out or os.path.join(os.path.dirname(src), "captures-scrubbed")

    if not args.check and os.path.isdir(out):
        if not args.force:
            raise SystemExit(f"{out} exists. Re-run with --force to replace it.")
        shutil.rmtree(out)

    files, records, stats, distinct, unscrubbed = scrub_tree(
        src, out, dry_run=args.check, skip=("captures-scrubbed", "portal-scrubbed"))

    print(f"source   {src}")
    print(f"files    {files}")
    print(f"records  {records}")
    print(f"distinct secrets replaced  {distinct}")
    for field, n in sorted(stats.items()):
        print(f"  {field:16s} {n}")
    if unscrubbed:
        print(f"\nNOT SCRUBBED, and NOT copied: {len(unscrubbed)} .raw file(s).")
        print("  They are the undecoded byte stream; nothing here parses them, so")
        print("  nothing here can promise what is in them. They stay behind.")
    if stats.get(OPAQUE_STAT):
        print(f"\nNOT CLEANED, and copied anyway: {stats[OPAQUE_STAT]} `plain` frame "
              f"payload(s).")
        print("  This tool matches JSON keys and cannot see inside a hex blob of protocol")
        print("  bytes. The auth channel's first client message embeds the account email")
        print("  as UTF-16 inside exactly such a blob (MEASURED, 271 captures), so the")
        print(f"  output tree is NOT safe to hand to anyone. {out}/SCRUB-MANIFEST.json")
        print("  names every file that still carries one.")
    print("\n(dry run -- nothing written)" if args.check
          else f"\nwrote    {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
