"""Proves the credential scrub actually removes the credential.

The temptation with a scrubber is to test that it ran. That check cannot fail in the
way that matters: the interesting failure is a secret-bearing field NOBODY PUT ON THE
LIST, which a "did it run" test passes cheerfully while the credential sits in the
output. So the load-bearing assertion here is the other direction -- harvest every
secret value out of the ORIGINALS, then assert not one of them appears anywhere in the
scrubbed bytes, field list or no field list.

That check can fail, and it is proved to fail: a later section deliberately removes
Password from the element list, re-scrubs, and asserts the leak is caught.

EVERY PASS READS ONE SNAPSHOT. This test reads the capture tree four times -- harvest,
scrub, count, compare -- and on 2026-08-10 it went red twice with "326648 in, 326631
out, 15 unparseable" for no reason but that a live authsrv was appending to the tree
between two of those passes. The arithmetic was correct and the corpus was moving. So
`sc.Snapshot` fixes the file list and each file's length once, up front, and every pass
reads exactly those bytes; records written afterwards are not part of the corpus under
test. The arithmetic itself is untouched -- it is what caught 181 values leaking through
`response` -- and nothing here skips when a server is up, which would delete the check
exactly when captures are being written. The last section proves the pin holds by
growing a corpus underneath one.

    python toolkit/test_scrub.py
"""
import base64
import json
import os
import re
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import vaultpath  # noqa: E402
import scrub_captures as sc  # noqa: E402

# 1 snapshot + 6 structural + 6 leak/property + 2 red-team + 6 blind-spot
# + 4 snapshot red-team = 25, measured green over the whole capture tree. Nothing here is
# optional; a run under this floor has lost a section.
LEDGER = checks.Ledger("credential scrub", floor=25)

# Derived output of previous runs. Not evidence, and scrubbing a scrub would double-count
# every record. Baked into the snapshot, so no pass can disagree about what was excluded.
SKIP = ("captures-scrubbed", "portal-scrubbed")


def harvest_secrets(snap):
    """Every account-identifying value in the ORIGINALS, gathered independently.

    Deliberately does NOT reuse scrub_captures' field lists -- if it did, a field the
    scrubber forgets would also be a field this test forgets, and the whole check
    would be the scrubber grading its own homework.

    Reads the snapshot, not the tree, so the values harvested here are the values the
    scrub pass will see: a secret appended after the snapshot is in neither.
    """
    out = set()
    elem = re.compile(r"<(LoginName|Password|AccountAlias|Session|Token|ResumeToken"
                      r"|UserId|UserName|Alias)>(.*?)</\1>")
    for rel, _size in snap.jsonl():
        for line in snap.lines(rel):
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            # `master_secret` joined this list on 2026-08-10, later than it joined
            # SECRET_KEYS. Until then it was on NEITHER list, and a value missing from
            # both is invisible twice over: the scrubber shipped it and the leak check
            # could not see that it had. Two lists that forget the same field are one
            # list, which is the failure this function's docstring exists to prevent
            # -- arriving by omission rather than by reuse.
            for key in ("email", "token", "user_id", "account_uuid", "char_uuid",
                        "arc4_key", "master_secret", "a", "sent"):
                v = rec.get(key)
                if v not in (None, "", 0):
                    out.add(str(v))
            auth = rec.get("authorization")
            if isinstance(auth, str) and " " in auth:
                cred = auth.split(" ", 1)[1]
                if cred not in sc.AUTH_SENTINELS:
                    out.add(cred)
            body = rec.get("body")
            if isinstance(body, str):
                for _, text in elem.findall(body):
                    if text:
                        out.add(text)
    # Values short enough to collide with ordinary text would make the leak test
    # meaningless (searching for "0" finds everything). Keep the real ones.
    return {s for s in out if len(s) >= 6}


def jsonl_under(root):
    """Every .jsonl anywhere under root. Walks, because the credential was never
    only in captures/portal -- 206 `email`, 113 `account_uuid` and 341 ARC4 keys
    sat in sibling directories this test used not to look at.

    Only ever pointed at the SCRUBBED output now: that tree is written by this run and
    nothing else touches it, so walking it live is safe. The originals go through the
    snapshot instead.
    """
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        out.extend(os.path.join(base, f) for f in sorted(files)
                   if f.endswith(".jsonl"))
    return sorted(out)


def count_lines(paths):
    """Non-blank lines across a list of on-disk files."""
    return sum(1 for p in paths for line in
               open(p, encoding="utf-8", errors="replace") if line.strip())


def leaked(out_dir, secrets):
    """Any secret appearing literally anywhere in the scrubbed output.

    Reads every file, not only the .jsonl -- a scrubber that redacted every
    record and then wrote the values into its own manifest would pass a
    shallower check.

    OPAQUE PAYLOADS ARE EXCLUDED, and that exclusion is the honest half of a bargain
    rather than a loophole. `plain` and `payload` are raw protocol bytes -- a decrypted
    frame, a captured TCP segment -- and redacting them does not clean the capture, it
    deletes it. They demonstrably carry secrets: the first live capture put `a` and `sent`
    into `payload` as hex, because the DH handshake crosses the wire in the clear, and this
    check found both. What the scrub can do is REFUSE TO CLAIM otherwise, so the other half
    of the bargain is section 7 below, which requires every such field to be counted, every
    file holding one to be named in the manifest, and the manifest to say the tree is not
    shareable. Drop that section and this exclusion becomes the hole it is not today.
    """
    blob = []
    for base, _dirs, files in os.walk(out_dir):
        for f in sorted(files):
            path = os.path.join(base, f)
            with open(path, encoding="utf-8", errors="replace") as fh:
                if not f.endswith(".jsonl"):
                    blob.append(fh.read())
                    continue
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        blob.append(line)      # unparseable: search it whole
                        continue
                    if isinstance(rec, dict):
                        rec = {k: v for k, v in rec.items() if k not in sc.OPAQUE_KEYS}
                    blob.append(json.dumps(rec))
    text = "\n".join(blob)
    return {s for s in secrets if s in text}


def check_corpus(src, snap):
    """Everything that is a claim about the real capture tree, all of it read from
    `snap` so the four passes cannot disagree about what the tree contains."""
    LEDGER.ok(bool(snap.jsonl()) and snap.total_bytes() > 0,
              "the run pinned a corpus before making claims about it",
              f"{len(snap.jsonl())} .jsonl + {len(snap.raw())} .raw, "
              f"{snap.total_bytes()} bytes, enumerated once")

    secrets = harvest_secrets(snap)
    LEDGER.ok(len(secrets) >= 3,
              "the originals really do contain secrets to remove",
              f"{len(secrets)} distinct values, harvested independently")

    # A password we can recognise: base64 that decodes cleanly is the real thing.
    decodable = 0
    for s in secrets:
        try:
            if base64.b64decode(s, validate=True):
                decodable += 1
        except Exception:
            pass
    LEDGER.ok(decodable >= 1,
              "at least one harvested value is decodable base64 (the password form)",
              f"{decodable} of {len(secrets)}")

    tmp = tempfile.mkdtemp(prefix="rurik-scrub-")
    try:
        out = os.path.join(tmp, "scrubbed")
        files, records, stats, distinct, unscrubbed = sc.scrub_tree(
            src, out, snapshot=snap)

        # --- structure is preserved -------------------------------------------
        LEDGER.ok(records > 0, "records were read", f"{records} across {files} file(s)")
        written = jsonl_under(out)
        LEDGER.ok(len(written) == files,
                  "every source file has a scrubbed counterpart",
                  f"{len(written)}/{files}")

        # Both sides of the arithmetic are the SAME bytes: `src_lines` re-counts the
        # snapshot the scrub read, not the tree as it stands now.
        src_lines = sum(1 for rel, _n in snap.jsonl()
                        for line in snap.lines(rel) if line.strip())
        out_lines = count_lines(written)
        dropped = stats.get("UNPARSEABLE", 0)
        LEDGER.ok(src_lines - dropped == out_lines,
                  "every parseable record survives; unparseable ones are dropped",
                  f"{src_lines} in, {out_lines} out, {dropped} unparseable")

        # every output line is still valid JSON
        bad = 0
        for f in written:
            for line in open(f, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
        LEDGER.ok(bad == 0, "every scrubbed record is still valid JSON", f"{bad} bad")

        # --- THE CHECK THAT MATTERS -------------------------------------------
        found = leaked(out, secrets)
        LEDGER.ok(not found,
                  "no harvested secret survives anywhere in the scrubbed output",
                  f"{len(secrets)} checked" if not found
                  else f"LEAKED {len(found)} value(s)")

        # --- properties the substitution promises ------------------------------
        lengths_ok, corr_ok = True, True
        seen = {}
        elem = re.compile(r"<(LoginName|Password|AccountAlias)>(.*?)</\1>")
        for rel, _n in snap.jsonl():
            of = os.path.join(out, rel)
            if not os.path.isfile(of):
                continue
            a = [line for line in snap.lines(rel, "utf-8-sig") if line.strip()]
            b = [line for line in open(of, encoding="utf-8-sig",
                                       errors="replace") if line.strip()]
            for la, lb in zip(a, b):
                ra, rb = json.loads(la), json.loads(lb)
                for tag, text in elem.findall(ra.get("body", "") or ""):
                    repl = dict(elem.findall(rb.get("body", "") or "")).get(tag, "")
                    if len(repl) != len(text):
                        lengths_ok = False
                    if text in seen and seen[text] != repl:
                        corr_ok = False
                    seen[text] = repl
        LEDGER.ok(lengths_ok,
                  "placeholders are the same length as what they replaced",
                  "body length is the Content-Length the client sent")
        LEDGER.ok(corr_ok,
                  "the same secret always becomes the same placeholder",
                  "correlation survives, identity does not")
        LEDGER.ok(distinct >= 3, "the manifest counted the substitutions",
                  f"{distinct} distinct values")
        LEDGER.ok(os.path.isfile(os.path.join(out, "SCRUB-MANIFEST.json")),
                  "a manifest was written")

        man = json.load(open(os.path.join(out, "SCRUB-MANIFEST.json"),
                             encoding="utf-8"))
        man_text = json.dumps(man)
        LEDGER.ok(not any(s in man_text for s in secrets),
                  "and the manifest itself carries counts, never values")

        # --- prove the leak check can go red -----------------------------------
        # Drop Password from the element list and re-scrub: the password must now
        # survive, and the leak check must catch it. If this section passes silently
        # the leak check above is decorative.
        saved = dict(sc.SECRET_ELEMENTS)
        try:
            sc.SECRET_ELEMENTS.pop("Password")
            broken = os.path.join(tmp, "broken")
            sc.scrub_tree(src, broken, snapshot=snap)
            caught = leaked(broken, secrets)
            LEDGER.ok(bool(caught),
                      "removing Password from the list makes the leak check FAIL",
                      f"caught {len(caught)} leaked value(s)")
            LEDGER.ok(found != caught,
                      "and that is a real difference from the clean run",
                      f"clean leaked {len(found)}, broken leaked {len(caught)}")
        finally:
            sc.SECRET_ELEMENTS.clear()
            sc.SECRET_ELEMENTS.update(saved)

        # --- the blind spot, stated rather than papered over --------------------
        # The leak check above searches for the harvested ASCII values. The auth
        # channel's first client message carries the account email as UTF-16 inside a
        # `plain` hex blob (MEASURED: 271 of the vault's 276 auth captures begin
        # 0180 0500 7300 6b00 ...), so the address is present as "7300 6b00 ..." and
        # the ASCII search walks straight past it. That is why the leak check stayed
        # green while the credential shipped, and why the scrub now REPORTS the field
        # instead of appearing to have handled it.
        print("\n7. the opaque-payload blind spot is reported, not silently passed")
        email = "leaky.address@example.invalid"
        blob = struct.pack("<HH", 0x8001, len(email)) + email.encode("utf-16-le")
        opq = os.path.join(tmp, "opaque")
        os.makedirs(opq, exist_ok=True)
        with open(os.path.join(opq, "frames.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": "frame", "direction": "c2s",
                                 "plain": blob.hex()}) + "\n")
        opq_out = os.path.join(tmp, "opaque-scrubbed")
        _f, _r, ostats, _d, _u = sc.scrub_tree(opq, opq_out)
        LEDGER.ok(ostats.get(sc.OPAQUE_STAT) == 1,
                  "a `plain` frame payload is COUNTED as not-cleaned, not ignored",
                  f"{sc.OPAQUE_STAT} = {ostats.get(sc.OPAQUE_STAT)}")
        out_text = open(os.path.join(opq_out, "frames.jsonl"), encoding="utf-8").read()
        LEDGER.ok(blob.hex() in out_text,
                  "the payload really does survive the scrub verbatim -- this is the fact "
                  "the report exists to state", f"{len(blob)} bytes copied through")
        LEDGER.ok(email not in out_text and email.encode("utf-16-le").hex() in out_text,
                  "and the email inside it is invisible to an ASCII search but present "
                  "as UTF-16", "which is exactly why the leak check above stayed green")
        oman = json.load(open(os.path.join(opq_out, "SCRUB-MANIFEST.json"),
                              encoding="utf-8"))
        LEDGER.ok(oman.get("NOT_CLEANED_opaque_payloads") == ["frames.jsonl"],
                  "the manifest names the file that still carries one")
        LEDGER.ok("NOT safe to hand to anyone" in oman.get("WARNING", ""),
                  "and says plainly that the output is not shareable")

        # And the same promise against the REAL corpus, which is where it has to hold: if
        # any vaulted capture carries an opaque payload, the tree-wide manifest must name
        # it. This is the assertion that pays for leaked()'s exclusion -- without it, the
        # exclusion would be a blind spot rather than a declared one.
        real_man = json.load(open(os.path.join(out, "SCRUB-MANIFEST.json"),
                                  encoding="utf-8"))
        listed = real_man.get("NOT_CLEANED_opaque_payloads", [])
        if stats.get(sc.OPAQUE_STAT):
            LEDGER.ok(len(listed) > 0 and "NOT safe" in real_man.get("WARNING", ""),
                      "the real corpus's own manifest names its opaque-payload files",
                      f"{len(listed)} of {files} file(s) carry one")
        else:
            LEDGER.skip("corpus opaque census", "no vaulted capture carries a payload field")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write_records(path, start, count):
    """Append `count` portal-shaped records, as a live authsrv would."""
    with open(path, "a", encoding="utf-8") as fh:
        for i in range(start, start + count):
            fh.write(json.dumps({
                "kind": "request", "email": f"player{i}@example.invalid",
                "authorization": f"Arena {i:036d}",
                "body": f"<LoginName>player{i}@example.invalid</LoginName>",
            }) + "\n")


def check_snapshot_pins_a_growing_corpus():
    """Prove the pin, on a corpus that grows on purpose while the run is holding it.

    This is the section that would have been red before the snapshot existed. A
    synthetic tree, because the real failure needs a server writing during the run and
    a test cannot start one -- but the mechanism is identical: enumerate, then append,
    then check that the arithmetic is still about what was enumerated.

    The third check is the load-bearing one. Without it this section would pass just as
    happily if `Snapshot` were a no-op wrapper around a live walk that happened not to
    race, so it asserts the un-snapshotted read of the SAME tree really does disagree.
    """
    print("\n8. the snapshot pins a corpus that is being appended to")
    tmp = tempfile.mkdtemp(prefix="rurik-scrub-grow-")
    try:
        corpus = os.path.join(tmp, "captures")
        os.makedirs(os.path.join(corpus, "portal"))
        live = os.path.join(corpus, "portal", "live.jsonl")
        write_records(live, 0, 10)

        snap = sc.Snapshot(corpus, skip=SKIP)
        pinned = sum(1 for line in snap.lines(os.path.join("portal", "live.jsonl"))
                     if line.strip())

        # The server keeps going, exactly as it did on 2026-08-10.
        write_records(live, 100, 7)

        out = os.path.join(tmp, "scrubbed")
        _files, records, stats, _distinct, _un = sc.scrub_tree(
            corpus, out, snapshot=snap)
        src_lines = sum(1 for rel, _n in snap.jsonl()
                        for line in snap.lines(rel) if line.strip())
        out_lines = count_lines(jsonl_under(out))
        dropped = stats.get("UNPARSEABLE", 0)
        LEDGER.ok(src_lines - dropped == out_lines,
                  "the arithmetic still balances when the corpus grows under the run",
                  f"{src_lines} in, {out_lines} out, {dropped} unparseable, "
                  f"7 appended after the snapshot")
        LEDGER.ok(records == 10,
                  "and the claim is about the 10 snapshotted records, not the 17 "
                  "now on disk", f"{records} read, {pinned} pinned by the snapshot")

        walked = count_lines([os.path.join(base, f)
                              for base, _d, fs in os.walk(corpus)
                              for f in fs if f.endswith(".jsonl")])
        LEDGER.ok(walked != records,
                  "an un-snapshotted read of the same tree disagrees -- the bug this "
                  "removes", f"{walked} walked now vs {records} snapshotted")

        # Growth is invisible; shrinkage must never be. A short read would silently
        # lower every count downstream, which is the failure mode checks.py exists
        # to refuse.
        with open(live, "w", encoding="utf-8") as fh:
            fh.write("")
        try:
            snap.text(os.path.join("portal", "live.jsonl"))
            loud = False
        except sc.SnapshotChanged:
            loud = True
        LEDGER.ok(loud,
                  "a snapshotted file that SHRINKS is a loud refusal, not a short read",
                  "growth is invisible by design; truncation is not")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    src = vaultpath.require_dir("captures",
                                why="the scrub test reads the real capture tree")
    snap = sc.Snapshot(src, skip=SKIP)
    try:
        check_corpus(src, snap)
    except sc.SnapshotChanged as exc:
        # Routed through the ledger rather than a traceback: a test that dies without
        # printing [FAIL] has still told nobody which claim went unmeasured.
        LEDGER.ok(False,
                  "the snapshotted corpus stayed readable at its recorded size",
                  str(exc))
    check_snapshot_pins_a_growing_corpus()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
