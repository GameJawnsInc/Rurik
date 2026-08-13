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
exactly when captures are being written. Section 8 proves the pin holds by growing a
corpus underneath one.

SECTIONS 9-11 (2026-08-13) ARE THE OTHER TREE. `vault/state/sessions.json` is the
portal's issued-session table and it sat OUTSIDE the scrub root -- five cleartext records,
each with an `email`, a 36-character `user_id` and a 36-character `token`, three of the
five emails real-shaped. It was excluded from RUNBOOK's off-disk list in prose and by
nothing else, which is the state the module docstring's ruling ends.

Every fixture here is SYNTHETIC and built by this file. The real store is never copied
anywhere, and the one claim made about it -- section 11's -- is that the census reports
no value out of it, harvested from the SAME string the census was built from.

THAT SAMENESS IS THE RACE ANSWER, and it is not `Snapshot`. The store is live, but it is
not appended to: `sessionstore._write` dumps the whole map to a temp file and
`os.replace`s it, and `issue()` prunes 200 records down to 100. So a legitimate rewrite
can make the file SHORTER, and `Snapshot`'s size pin would report the server doing its
job as `SnapshotChanged`. What `os.replace` does guarantee is that one `read()` returns
one whole version. So `sc.audit_state_text` is pure over a string, this test reads the
file once, and both the harvest and the census come from that one read. A session landing
mid-run cannot make the two disagree, because there is only one set of bytes.

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
# + 1 state census stamp + 4 snapshot red-team + 11 session store + 6 state refusal
# + 2 destination = 45 mandatory, plus 2 that need `vault/state` to exist. MEASURED green
# 2026-08-13 at 47 over the whole capture tree with the store present. The floor is the
# mandatory core, so a machine whose vault has no `state/` still has to run everything
# else; the two real-store checks declare a skip. Nothing here is optional beyond that.
LEDGER = checks.Ledger("credential scrub", floor=45)

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
        # The audit is computed ONCE, before anything is written, exactly as `main()`
        # does it -- so the census stamped into the manifest describes the store as it
        # stood when the run began. A login landing later moves the store and not the
        # report, which is a true statement about a fixed set of bytes.
        state_audit = sc.audit_state(
            os.path.join(os.path.dirname(src), sc.CREDENTIAL_STATE_DIR))
        files, records, stats, distinct, unscrubbed = sc.scrub_tree(
            src, out, snapshot=snap, state_audit=state_audit)

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

        # And the state store's exclusion is STAMPED into the report a human actually
        # reads. This is the whole difference between "excluded by construction" and
        # "nobody walked it": both leave the tree identical, and only one of them tells
        # the next person widening RUNBOOK's off-disk list that a credential file exists.
        census = real_man.get("credential_state_census", {})
        LEDGER.ok(census.get("policy") == sc.STATE_POLICY
                  and census.get("dir") == state_audit["dir"]
                  and census.get("sessions") == state_audit["sessions"],
                  "the tree-wide manifest carries the credential-state census and says "
                  "the exclusion was deliberate",
                  f"{census.get('sessions')} session record(s) named as NOT scrubbed")
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


# Harvested by SHAPE, never by field name, and deliberately not `sc.SECRET_KEYS` or
# `sc.UUID_RE`. The point of section 9 is the same as `harvest_secrets`': if this test
# asked the scrubber which fields are secret, a field the scrubber forgets is a field
# this test forgets too, and the two lists would be one list. A regex over the raw text
# also catches the value the field-name approach structurally cannot -- the MAP KEY.
STATE_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
STATE_UUID_RE = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}"
                           r"-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}")


def harvest_state_secrets(text):
    """Every account-identifying value in a session store, by shape alone."""
    found = set(STATE_EMAIL_RE.findall(text)) | set(STATE_UUID_RE.findall(text))
    return {s for s in found if len(s) >= 6}


def tree_text(root):
    """Every byte of every file under `root`, concatenated. Manifests included.

    A scrubber that redacted every record and then wrote the values into its own
    manifest would pass a shallower check -- `leaked()` learned that the same way.
    """
    blob = []
    for base, _dirs, files in os.walk(root):
        for f in sorted(files):
            with open(os.path.join(base, f), encoding="utf-8", errors="replace") as fh:
                blob.append(fh.read())
    return "\n".join(blob)


def synthetic_store(records):
    """`sessionstore.issue()`'s own shape, built here, with values that are ours.

    Keyed BY THE TOKEN and carrying the token again inside the record, because that is
    what `sessionstore.issue()` does and it is the trap the shape carries: the credential
    is present twice and only one of the two is a value.
    """
    return {"sessions": {r["token"]: dict(r) for r in records}}


def check_session_store():
    """Section 9: the session-store shape, cleaned -- and what it refuses to clean.

    Synthetic throughout. The real store is never copied, never into a test and never
    into the repo; the values below are invented and the addresses are `.invalid`, the
    reserved TLD that can never resolve.
    """
    print("\n9. the portal session store is a shape the scrub can clean")
    tmp = tempfile.mkdtemp(prefix="rurik-scrub-state-")
    try:
        recs = [{"email": f"synthetic.{i}@example.invalid",
                 "user_id": f"{i}1111111-2222-3333-4444-55555555555{i}".upper(),
                 "token": f"{i}AAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEE{i}".upper(),
                 "issued_utc": f"2026-01-0{i}T03:04:05Z"} for i in (1, 2, 3)]
        state = os.path.join(tmp, "state")
        os.makedirs(state)
        store_path = os.path.join(state, "sessions.json")
        with open(store_path, "w", encoding="utf-8") as fh:
            json.dump(synthetic_store(recs), fh, indent=1)

        raw = open(store_path, encoding="utf-8").read()
        secrets = harvest_state_secrets(raw)
        LEDGER.ok(len(secrets) >= 9,
                  "the synthetic store really does contain secrets to remove",
                  f"{len(secrets)} distinct values, harvested by shape not by field name")

        out = os.path.join(tmp, "state-scrubbed")
        rows, refused, unknown, sstats, distinct = sc.scrub_state_tree(state, out)

        # --- THE CHECK THAT MATTERS -------------------------------------------
        found = {s for s in secrets if s in tree_text(out)}
        LEDGER.ok(not found,
                  "no harvested secret survives anywhere in the scrubbed store",
                  f"{len(secrets)} checked" if not found
                  else f"LEAKED {len(found)} value(s)")

        after = json.load(open(os.path.join(out, "sessions.json"), encoding="utf-8"))
        keys_in = set(synthetic_store(recs)["sessions"])
        keys_out = set(after["sessions"])
        LEDGER.ok(not (keys_in & keys_out) and len(keys_out) == len(keys_in),
                  "the MAP KEY is replaced too, not only the record's `token` field",
                  f"{len(keys_out)} keys, 0 of them the original -- `scrub_record` walks "
                  "values, and the key is where half of this credential lives")

        LEDGER.ok(all(k == rec["token"] for k, rec in after["sessions"].items()),
                  "and the key and the record's own token land on the SAME placeholder",
                  "the scrubbed store is still a store; correlation survives")

        # Paired by POSITION, not by looking the record up on a surviving field. The
        # first version matched on `issued_utc`, and the sabotage that blanks every
        # field made that lookup raise IndexError -- so the positive control below,
        # which is the check that sabotage exists to redden, never got to run. A
        # control that crashes instead of failing has told nobody which claim broke.
        # Insertion order is preserved end to end: the fixture dict, scrub_state_json's
        # rebuild, json.dump and json.load all keep it.
        lengths_ok = True
        for r, rec in zip(recs, after["sessions"].values()):
            for field in ("email", "user_id", "token"):
                if len(rec[field]) != len(r[field]):
                    lengths_ok = False
        key_lengths_ok = sorted(len(k) for k in keys_out) == sorted(
            len(k) for k in keys_in)
        LEDGER.ok(lengths_ok and key_lengths_ok,
                  "placeholders are the same length as what they replaced, keys included",
                  "36 characters stays 36 characters")

        # --- POSITIVE CONTROL: this is a scrub, not a blanking ------------------
        stamps_in = sorted(r["issued_utc"] for r in recs)
        stamps_out = sorted(v["issued_utc"] for v in after["sessions"].values())
        LEDGER.ok(stamps_in == stamps_out and list(after) == ["sessions"],
                  "an ordinary non-credential field survives BYTE-IDENTICAL",
                  f"{len(stamps_out)} `issued_utc` unchanged -- a scrub that blanked "
                  "everything would pass the leak check and be useless")

        fields_in = sorted(recs[0])
        fields_out = sorted(next(iter(after["sessions"].values())))
        LEDGER.ok(fields_in == fields_out and len(after["sessions"]) == len(recs),
                  "and the shape is unchanged: same records, same fields",
                  f"{len(after['sessions'])} records, fields {fields_out}")

        # --- the field nobody listed, which is how `plain` shipped ---------------
        # A second store, because the unknown field's VALUE is copied through by design
        # and would otherwise poison the leak check above. Keeping them apart is the
        # same bargain `leaked()` strikes with OPAQUE_KEYS: exclude the thing that is
        # honestly reported, and then require the report.
        grown = os.path.join(tmp, "state-grown")
        os.makedirs(grown)
        extra = dict(recs[0])
        extra["refresh_secret"] = "SYNTHETIC-FUTURE-FIELD-VALUE"
        with open(os.path.join(grown, "sessions.json"), "w", encoding="utf-8") as fh:
            json.dump(synthetic_store([extra]), fh, indent=1)
        gout = os.path.join(tmp, "state-grown-scrubbed")
        _rows, _ref, gunknown, gstats, _d = sc.scrub_state_tree(grown, gout)

        LEDGER.ok(gstats.get(sc.STATE_UNKNOWN_STAT) == 1
                  and gunknown == ["refresh_secret"],
                  "a session field the tool does not recognise is COUNTED and NAMED",
                  f"{sc.STATE_UNKNOWN_STAT} = {gstats.get(sc.STATE_UNKNOWN_STAT)}, "
                  f"{gunknown}")

        gman = json.load(open(os.path.join(gout, "SCRUB-MANIFEST.json"),
                              encoding="utf-8"))
        LEDGER.ok(gman.get("NOT_CLEANED_unknown_state_fields") == ["refresh_secret"]
                  and "not recognised" in gman.get("WARNING", ""),
                  "and the manifest names it and refuses to call the output clean",
                  "the record shape belongs to the server and grows")

        gtext = open(os.path.join(gout, "sessions.json"), encoding="utf-8").read()
        LEDGER.ok(extra["refresh_secret"] in gtext
                  and extra["refresh_secret"] not in json.dumps(gman),
                  "its value really does survive -- stated, not pretended away",
                  "the manifest carries the field NAME and never the value")

        # --- a shape it does not understand is refused, not half-cleaned ---------
        odd = os.path.join(tmp, "state-odd")
        os.makedirs(odd)
        with open(os.path.join(odd, "sessions.json"), "w", encoding="utf-8") as fh:
            json.dump({"logins": [{"email": "other.shape@example.invalid"}]}, fh)
        oout = os.path.join(tmp, "state-odd-scrubbed")
        orows, orefused, _u, _s, _d = sc.scrub_state_tree(odd, oout)
        oman = json.load(open(os.path.join(oout, "SCRUB-MANIFEST.json"),
                              encoding="utf-8"))
        LEDGER.ok(orefused == ["sessions.json"]
                  and not os.path.exists(os.path.join(oout, "sessions.json"))
                  and orows[0]["shape"] == sc.STATE_SHAPE_UNKNOWN
                  and oman["REFUSED_unrecognised_shape"] == ["sessions.json"],
                  "a file that is not the session-store shape is REFUSED, not written",
                  "a half-cleaned credential file still looks scrubbed in a listing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_state_is_excluded_from_the_shareable_tree():
    """Section 10: the exclusion is a rule with teeth, not an accident of file extension.

    `vault/state/sessions.json` was already never copied into `captures-scrubbed/` --
    but only because the store is `.json` and `scrub_tree` walks `.jsonl`. Rename it,
    or hand `--src` a tree that keeps one line per session, and the credentials land in
    the one tree RUNBOOK says may leave this machine, with nothing anywhere to say so.

    So the fixture is deliberately the case the accident does NOT cover: a `state/`
    directory holding a `.jsonl` the walk would otherwise take. The positive control is
    the sibling `portal/` file, which must still be scrubbed -- a refusal that refuses
    everything protects nothing, because then nobody runs the tool.
    """
    print("\n10. anything under a `state/` component is refused and named")
    tmp = tempfile.mkdtemp(prefix="rurik-scrub-excl-")
    try:
        corpus = os.path.join(tmp, "captures")
        os.makedirs(os.path.join(corpus, "portal"))
        os.makedirs(os.path.join(corpus, "state"))
        write_records(os.path.join(corpus, "portal", "live.jsonl"), 0, 4)

        state_line = {"email": "store.only@example.invalid",
                      "user_id": "99999999-8888-7777-6666-555555555555",
                      "token": "11111111-2222-3333-4444-555555555555",
                      "issued_utc": "2026-01-01T00:00:00Z"}
        state_file = os.path.join(corpus, "state", "sessions.jsonl")
        with open(state_file, "w", encoding="utf-8") as fh:
            for _ in range(3):
                fh.write(json.dumps(state_line) + "\n")

        audit = sc.audit_state(os.path.join(corpus, "state"))
        out = os.path.join(tmp, "scrubbed")
        _files, _records, stats, _distinct, _un = sc.scrub_tree(
            corpus, out, state_audit=audit)
        written = jsonl_under(out)

        LEDGER.ok(len(written) == 1
                  and not any(sc.path_has_component(os.path.relpath(w, out), "state")
                              for w in written),
                  "nothing under a `state/` component reaches the output tree",
                  f"{len(written)} file(s) written, 0 of them from state/")

        # THE POSITIVE CONTROL, and it is deliberately not "one file exists". The first
        # version folded `len(written) == 1` in here, and the sabotage that deletes the
        # refusal reddened BOTH -- so this check was measuring the refusal rather than
        # controlling it. Kept apart, it stays green under that sabotage and goes red
        # under the opposite one (a refusal that matches everything), which is the only
        # arrangement in which it means anything.
        portal_out = [w for w in written if w.endswith("live.jsonl")]
        portal_secrets = harvest_state_secrets(
            open(os.path.join(corpus, "portal", "live.jsonl"), encoding="utf-8").read())
        LEDGER.ok(len(portal_out) == 1 and portal_secrets
                  and not {s for s in portal_secrets
                           if s in open(portal_out[0], encoding="utf-8").read()},
                  "and the sibling capture file IS still written AND scrubbed",
                  "a refusal that refuses everything protects nothing, because then "
                  "nobody runs the tool")
        LEDGER.ok(stats.get(sc.STATE_STAT) == 3,
                  "the refused records are COUNTED, not silently dropped",
                  f"{sc.STATE_STAT} = {stats.get(sc.STATE_STAT)} of 3 written")

        man = json.load(open(os.path.join(out, "SCRUB-MANIFEST.json"), encoding="utf-8"))
        named = [os.path.normpath(p) for p in man.get("NOT_SCRUBBED_credential_state", [])]
        LEDGER.ok(named == [os.path.normpath(os.path.join("state", "sessions.jsonl"))],
                  "and the manifest NAMES the file it refused",
                  f"{named}")

        secrets = harvest_state_secrets(open(state_file, encoding="utf-8").read())
        found = {s for s in secrets if s in tree_text(out)}
        LEDGER.ok(secrets and not found,
                  "no value out of the refused file appears anywhere in the output",
                  f"{len(secrets)} checked")

        # A `.jsonl` store is not the shape `sessionstore.py` writes, and the census has
        # to say so rather than report a confident zero. "There are no sessions here" and
        # "nothing here can parse this" are different results and only one is an
        # all-clear -- the same rule the opaque payloads are reported under.
        LEDGER.ok(audit["unrecognised"] == 1 and audit["sessions"] == 0
                  and audit["files"][0]["shape"] == sc.STATE_SHAPE_UNKNOWN,
                  "a state file the census cannot parse is UNRECOGNISED, not 0 sessions",
                  audit["files"][0].get("note", "")[:60])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_destination_guard_and_real_store():
    """Section 11: the ruling cannot be opted out of, and the real store is censused.

    The destination guard is what makes "excluded by construction" a ruling rather than
    a default: without it, the next caller who wants everything in one place writes the
    scrubbed store into `captures-scrubbed/` and the exclusion evaporates. Its positive
    control is that an ordinary destination is still allowed, because a guard that
    refuses everything is never run and therefore protects nothing.

    The real-store half makes ONE claim, and makes it about ONE read. See the module
    docstring for why that is the right instrument here and `Snapshot` is not.
    """
    print("\n11. the destination guard, and the real store's census")
    tmp = tempfile.mkdtemp(prefix="rurik-scrub-dest-")
    try:
        state = os.path.join(tmp, "state")
        os.makedirs(state)
        with open(os.path.join(state, "sessions.json"), "w", encoding="utf-8") as fh:
            json.dump(synthetic_store([{
                "email": "guard.case@example.invalid",
                "user_id": "ABCDEF01-2345-6789-ABCD-EF0123456789",
                "token": "FEDCBA98-7654-3210-FEDC-BA9876543210",
                "issued_utc": "2026-01-01T00:00:00Z"}]), fh)

        refused = False
        try:
            sc.scrub_state_tree(state, os.path.join(tmp, "captures-scrubbed", "state"))
        except SystemExit:
            refused = True
        LEDGER.ok(refused,
                  "the scrubbed store is REFUSED into the tree that may leave the machine",
                  "a ruling any caller can opt out of by naming a path is not a ruling")

        allowed = os.path.join(tmp, "state-scrubbed")
        sc.scrub_state_tree(state, allowed)
        LEDGER.ok(os.path.isfile(os.path.join(allowed, "sessions.json")),
                  "and an ordinary destination is still allowed -- POSITIVE CONTROL",
                  "the capability exists; it just is not the default")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    real = os.path.join(vaultpath.vault_root(), sc.CREDENTIAL_STATE_DIR)
    store = os.path.join(real, "sessions.json")
    if not os.path.isfile(store):
        LEDGER.skip("real session store census",
                    f"no {store} on this machine -- nothing to exclude, and a fabricated "
                    "census would be worse than a declared skip")
        return

    # ONE read. Both the harvest and the census come from `raw`, so a login landing
    # between them cannot exist: there is no "between them".
    with open(store, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    row = sc.audit_state_text("sessions.json", raw)
    secrets = harvest_state_secrets(raw)

    LEDGER.ok(row["shape"] == sc.STATE_SHAPE and row["sessions"] >= 1
              and set(row["credential_fields"]) >= {"email", "token", "user_id"},
              "the real store is censused by field name and count",
              f"{row['sessions']} session record(s), fields "
              f"{sorted(row['credential_fields'])} -- counts, never values")

    # Deliberately printed as a count. This test reads the owner's real credentials into
    # memory, the way `harvest_secrets` already does for the capture tree, and prints not
    # one of them.
    blob = json.dumps(row)
    leaks = {s for s in secrets if s in blob}
    LEDGER.ok(secrets and not leaks,
              "and the census carries no value out of it",
              f"{len(secrets)} value(s) checked against the same bytes the census read")


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
    check_session_store()
    check_state_is_excluded_from_the_shareable_tree()
    check_destination_guard_and_real_store()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
