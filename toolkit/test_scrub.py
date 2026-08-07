"""Proves the credential scrub actually removes the credential.

The temptation with a scrubber is to test that it ran. That check cannot fail in the
way that matters: the interesting failure is a secret-bearing field NOBODY PUT ON THE
LIST, which a "did it run" test passes cheerfully while the credential sits in the
output. So the load-bearing assertion here is the other direction -- harvest every
secret value out of the ORIGINALS, then assert not one of them appears anywhere in the
scrubbed bytes, field list or no field list.

That check can fail, and it is proved to fail: the last section deliberately removes
Password from the element list, re-scrubs, and asserts the leak is caught.

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

# 6 structural + 6 leak/property + 2 red-team + 5 blind-spot = 19, measured green over the
# whole capture tree. Nothing here is optional; a run under this floor has lost a section.
LEDGER = checks.Ledger("credential scrub", floor=19)


def harvest_secrets(src):
    """Every account-identifying value in the ORIGINALS, gathered independently.

    Deliberately does NOT reuse scrub_captures' field lists -- if it did, a field the
    scrubber forgets would also be a field this test forgets, and the whole check
    would be the scrubber grading its own homework.
    """
    out = set()
    elem = re.compile(r"<(LoginName|Password|AccountAlias|Session|Token|ResumeToken"
                      r"|UserId|UserName|Alias)>(.*?)</\1>")
    for path in jsonl_under(src):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                for key in ("email", "token", "user_id", "account_uuid",
                            "char_uuid", "arc4_key", "a", "sent"):
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
    sat in sibling directories this test used not to look at."""
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("captures-scrubbed",
                                                "portal-scrubbed")]
        out.extend(os.path.join(base, f) for f in sorted(files)
                   if f.endswith(".jsonl"))
    return sorted(out)


def leaked(out_dir, secrets):
    """Any secret appearing literally anywhere in the scrubbed output.

    Reads every file, not only the .jsonl -- a scrubber that redacted every
    record and then wrote the values into its own manifest would pass a
    shallower check.
    """
    blob = []
    for base, _dirs, files in os.walk(out_dir):
        for f in sorted(files):
            with open(os.path.join(base, f), encoding="utf-8",
                      errors="replace") as fh:
                blob.append(fh.read())
    text = "\n".join(blob)
    return {s for s in secrets if s in text}


def main():
    src = vaultpath.require_dir("captures",
                                why="the scrub test reads the real capture tree")
    secrets = harvest_secrets(src)
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
            src, out, skip=("captures-scrubbed", "portal-scrubbed"))

        # --- structure is preserved -------------------------------------------
        LEDGER.ok(records > 0, "records were read", f"{records} across {files} file(s)")
        written = jsonl_under(out)
        LEDGER.ok(len(written) == files,
                  "every source file has a scrubbed counterpart",
                  f"{len(written)}/{files}")

        src_lines = sum(1 for f in jsonl_under(src) for line in
                        open(f, encoding="utf-8", errors="replace")
                        if line.strip())
        out_lines = sum(1 for f in written for line in
                        open(f, encoding="utf-8", errors="replace")
                        if line.strip())
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
        for sf in jsonl_under(src):
            of = os.path.join(out, os.path.relpath(sf, src))
            if not os.path.isfile(of):
                continue
            a = [line for line in open(sf, encoding="utf-8-sig",
                                       errors="replace") if line.strip()]
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
            sc.scrub_tree(src, broken,
                          skip=("captures-scrubbed", "portal-scrubbed"))
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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
