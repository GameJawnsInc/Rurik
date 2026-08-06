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
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import vaultpath  # noqa: E402
import scrub_captures as sc  # noqa: E402

# 6 structural + 6 leak/property + 2 red-team = 14. Every section reads the same real capture
# directory, so nothing here is optional; a run under this floor has lost a section.
LEDGER = checks.Ledger("credential scrub", floor=14)


def harvest_secrets(src):
    """Every account-identifying value in the ORIGINALS, gathered independently.

    Deliberately does NOT reuse scrub_captures' field lists -- if it did, a field the
    scrubber forgets would also be a field this test forgets, and the whole check
    would be the scrubber grading its own homework.
    """
    out = set()
    elem = re.compile(r"<(LoginName|Password|AccountAlias)>(.*?)</\1>")
    for name in sorted(os.listdir(src)):
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(src, name), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                for key in ("email", "token", "user_id"):
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


def leaked(out_dir, secrets):
    """Any secret appearing literally anywhere in the scrubbed output."""
    blob = []
    for name in sorted(os.listdir(out_dir)):
        with open(os.path.join(out_dir, name), encoding="utf-8",
                  errors="replace") as fh:
            blob.append(fh.read())
    text = "\n".join(blob)
    return {s for s in secrets if s in text}


def main():
    src = vaultpath.require_dir("captures", "portal",
                                why="the scrub test reads the real portal captures")
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
        files, records, stats, distinct = sc.scrub_dir(src, out)

        # --- structure is preserved -------------------------------------------
        LEDGER.ok(records > 0, "records were read", f"{records} across {len(files)}")
        written = sorted(f for f in os.listdir(out) if f.endswith(".jsonl"))
        LEDGER.ok(written == sorted(files),
                  "every source file has a scrubbed counterpart",
                  f"{len(written)}/{len(files)}")

        src_lines = sum(1 for f in files for line in
                        open(os.path.join(src, f), encoding="utf-8",
                             errors="replace") if line.strip())
        out_lines = sum(1 for f in written for line in
                        open(os.path.join(out, f), encoding="utf-8",
                             errors="replace") if line.strip())
        LEDGER.ok(src_lines == out_lines,
                  "no record was silently dropped", f"{src_lines} -> {out_lines}")

        # every output line is still valid JSON
        bad = 0
        for f in written:
            for line in open(os.path.join(out, f), encoding="utf-8"):
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
        for f in files:
            a = [line for line in open(os.path.join(src, f), encoding="utf-8",
                                       errors="replace") if line.strip()]
            b = [line for line in open(os.path.join(out, f), encoding="utf-8",
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
            sc.scrub_dir(src, broken)
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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
