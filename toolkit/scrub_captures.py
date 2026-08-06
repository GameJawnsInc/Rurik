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

# Top-level JSONL keys whose whole value is account-identifying.
SECRET_KEYS = {
    "email": "email",
    "token": "tokn",
    "user_id": "uid",
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
        else:
            out[key] = value
    return out


def scrub_auth(value, names, stats):
    parts = value.split(" ", 1)
    if len(parts) != 2 or parts[1] in AUTH_SENTINELS:
        return value
    stats["authorization"] = stats.get("authorization", 0) + 1
    return f"{parts[0]} {names.get(parts[1], 'tokn')}"


def scrub_dir(src, out, dry_run=False):
    """Scrub every .jsonl under `src` into `out`. Returns (files, records, stats)."""
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
    ap.add_argument("--src", default=None, help="capture dir (default: vault portal)")
    ap.add_argument("--out", default=None, help="output dir")
    ap.add_argument("--check", action="store_true",
                    help="report what would be replaced; write nothing")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing output directory")
    args = ap.parse_args()

    src = args.src or vaultpath.require_dir(
        "captures", "portal", why="the credential scrub reads the portal captures")
    out = args.out or os.path.join(os.path.dirname(src), "portal-scrubbed")

    if not args.check and os.path.isdir(out):
        if not args.force:
            raise SystemExit(f"{out} exists. Re-run with --force to replace it.")
        shutil.rmtree(out)

    files, records, stats, distinct = scrub_dir(src, out, dry_run=args.check)

    print(f"source   {src}")
    print(f"files    {len(files)}")
    print(f"records  {records}")
    print(f"distinct secrets replaced  {distinct}")
    for field, n in sorted(stats.items()):
        print(f"  {field:16s} {n}")
    if stats.get("UNPARSEABLE"):
        print("  NOTE: unparseable lines were DROPPED from the scrubbed copy rather "
              "than passed through unchecked.")
    print("\n(dry run -- nothing written)" if args.check else f"\nwrote    {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
