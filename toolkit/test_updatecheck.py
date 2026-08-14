"""The before/after update commands, and that the baseline carries no key material.

    python toolkit/test_updatecheck.py

WHY. `studies/crossbuild/PLAN.md` §11. Half this arc's measurements need a BEFORE
state, an update is not schedulable, and `RUNBOOK.md`:136 warns that snapshotting
after accepting one means the build you were working against is gone. That
warning was prose a session had to remember, and the before-work was six commands
with six exit conventions.

THE CHECKS THAT EARN THE FILE:

  * §1 is PROVENANCE, and it is the one that would matter most if it failed. The
    baseline records the Diffie-Hellman parameters as a FINGERPRINT -- generator,
    prime bit length, sha256 prefix -- and never the values, which are ArenaNet
    key material. `dump_dh_params.py` prints only fingerprints by default for the
    same reason. This reads the REAL parameters out of the vaulted client and
    requires that neither the prime nor B appears anywhere in the serialised
    baseline, in decimal or in hex. A fingerprint diffs exactly as well, because
    it changes when they change, which is the entire question being asked.
  * §2 pins the distinction the report exists to draw: a signature whose HIT
    COUNT changed must be flagged RE-DERIVE, and one that merely moved to a new
    address must NOT. The second is what a healthy update looks like -- shapes
    holding while addresses drift -- and a report that shouted about it would be
    deleted after the first real update.
  * §3 is the exit contract, `datcheck.py`'s: 0 nothing moved, 1 something did
    and that is a RESULT, 2 the run could not be made. Each is driven, and the
    unchanged case is the positive control -- without it "it detects changes" is
    satisfied by a differ that reports changes always.
  * §4 refuses to write the baseline into any checkout of this repo, including
    the OTHER one, since a worktree's root is not the main checkout's.

Sections 2-4 need no vault. §1 and §5 read the vaulted client. Floor 26, ~60 s.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "clientscan"))
sys.path.insert(0, os.path.join(HERE, "clientpatch"))

import checks                                                # noqa: E402
import dhbuild                                               # noqa: E402
import pinned                                                # noqa: E402
import updatecheck as UC                                     # noqa: E402
import vaultpath                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

LEDGER = checks.Ledger("update check", floor=26)
check = checks.adopt(LEDGER)


def _base():
    """A minimal baseline shaped like `capture()`'s output."""
    return {
        "captured": "2026-01-01T00:00:00Z",
        "builds": {"S": {"stamp": "S", "build": 38519, "size": 1,
                         "signatures": {"SIG_KEYS": {"hits": 1, "vas": [0x1000]},
                                        "TAP_SIG": {"hits": 1, "vas": [0x2000]}}}},
        "live_install": {"identify": "pristine", "size": 1, "build": 38519},
        "pins": [{"file": "a.py", "symbol": "X", "value": 0x401000, "kind": "va"}],
        "schema": {"messages.json": {"validated_against_build": 38519}},
        "dh": {"S": {"struct_va": 0x900000, "generator": 4, "prime_bits": 512,
                     "prime_fp": "aaaa", "public_fp": "bbbb"}},
    }


print("\n1. the baseline carries a FINGERPRINT, never the key material")

try:
    exe = os.path.join(vaultpath.require_dir(
        "client", pinned.PINNED.stamp, why="update check"), "Gw.exe")
except BaseException as exc:                                 # noqa: BLE001
    exe = None
    LEDGER.skip("the provenance check", f"vault/client unavailable: {exc}")

if exe:
    _va, _rva, _off, (g, p, B) = dhbuild.locate_keys(PE(exe), exe)
    state = UC.capture()
    blob = json.dumps(state, sort_keys=True)

    check(len(blob) > 500, "capture() produced a baseline", f"{len(blob)} bytes")
    for name, value in (("prime", p), ("server public B", B)):
        forms = [str(value), f"{value:x}", f"{value:X}"]
        leaked = [f for f in forms if f in blob]
        check(not leaked,
              f"the {name} does NOT appear in the baseline, in any form",
              "decimal and both hex spellings checked; it is ArenaNet key material")
    dh = state["dh"][pinned.PINNED.stamp]
    check(dh["prime_fp"] == UC._fingerprint(p)
          and dh["public_fp"] == UC._fingerprint(B),
          "what it records instead is a sha256 fingerprint of each")
    check(dh["generator"] == g and dh["prime_bits"] == p.bit_length(),
          "plus the generator and the bit length, which are shape not secret")
    check(UC._fingerprint(p) != UC._fingerprint(p + 1),
          "and a fingerprint changes when the value does",
          "which is the only property the diff needs from it")

print("\n2. a moved address is not a broken signature")

before = _base()
after = json.loads(json.dumps(before))
after["builds"]["S"]["signatures"]["SIG_KEYS"]["vas"] = [0x9999]
lines, changed = UC.diff(before, after)
check(changed and any("sig moved" in ln for ln in lines),
      "a signature at a NEW address with the same count is reported as moved")
check(not any("RE-DERIVE" in ln for ln in lines),
      "and is NOT flagged for re-derivation",
      "that is what a healthy update looks like -- shapes hold, addresses drift")

after = json.loads(json.dumps(before))
after["builds"]["S"]["signatures"]["SIG_KEYS"]["hits"] = 2
lines, changed = UC.diff(before, after)
check(changed and any("RE-DERIVE" in ln for ln in lines),
      "while a changed HIT COUNT is flagged RE-DERIVE",
      "the anchor is ambiguous or gone; every tool that owns it is untrustworthy")

after = json.loads(json.dumps(before))
after["live_install"]["build"] = 38797
after["builds"]["S"]["build"] = 38797
lines, changed = UC.diff(before, after)
check(any("BUILD MOVED" in ln for ln in lines), "a moved build number is reported")
advice = UC._advice(before, after)
check(any("DH parameters rotate" in ln for ln in advice),
      "and the advice names the DH rotation, which no census can see")
check(any("38519" in ln and "schema" in ln for ln in advice),
      "and that the schema stamp is now stale",
      "PLAN.md §4 A3: stamp a NEW revision, never edit in place")

after = json.loads(json.dumps(before))
after["pins"][0]["value"] = 0x402000
lines, _c = UC.diff(before, after)
check(any("PIN MOVED" in ln for ln in lines), "a moved class-(a) pin is reported")

after = json.loads(json.dumps(before))
after["dh"]["S"]["prime_fp"] = "cccc"
lines, _c = UC.diff(before, after)
check(any("DH" in ln and "prime_fp" in ln for ln in lines),
      "and a rotated DH prime is reported, from the fingerprint alone")

print("\n3. the exit contract: 0 / 1 / 2")

lines, changed = UC.diff(before, json.loads(json.dumps(before)))
check(not changed and not lines,
      "a baseline against itself reports nothing",
      "the positive control -- without it, 'it detects changes' is satisfied "
      "by a differ that always does")

# Through the PROCESS, because that is what a script reading the exit code sees.
# Asking the exception for its `.code` is how the first version of this check
# passed while the process was exiting 1: `SystemExit("text")` carries the TEXT
# as its code, so a `CannotRun` raised out of main() would have been
# indistinguishable from "something moved".
import subprocess                                            # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    r = subprocess.run([sys.executable, os.path.join(HERE, "updatecheck.py"),
                        "--after", os.path.join(tmp, "nope.json")],
                       capture_output=True, text=True, timeout=600)
    check(r.returncode == 2,
          "an unreadable baseline exits 2 -- could not run, not a finding",
          f"rc={r.returncode}; 1 would be indistinguishable from 'it changed'")

    good = os.path.join(tmp, "b.json")
    with open(good, "w", encoding="utf-8") as fh:
        json.dump(UC.capture() if exe else before, fh)
    if exe:
        r = subprocess.run([sys.executable, os.path.join(HERE, "updatecheck.py"),
                            "--after", good],
                           capture_output=True, text=True, timeout=900)
        check(r.returncode == 0, "an unchanged state exits 0", f"rc={r.returncode}")

        doctored = os.path.join(tmp, "c.json")
        with open(good, encoding="utf-8") as fh:
            d = json.load(fh)
        d["live_install"]["build"] = 1
        with open(doctored, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        r = subprocess.run([sys.executable, os.path.join(HERE, "updatecheck.py"),
                            "--after", doctored],
                           capture_output=True, text=True, timeout=900)
        check(r.returncode == 1, "and a CHANGED state exits 1 -- a result",
              f"rc={r.returncode}")

print("\n4. the baseline never lands in a checkout of this repo")

try:
    UC._refuse_repo(os.path.join(HERE, "before.json"))
    check(False, "a path inside the working tree is REFUSED", "it allowed it")
except UC.CannotRun:
    check(True, "a path inside the working tree is REFUSED")

try:
    vroot = vaultpath.vault_root()
    ok = UC._refuse_repo(os.path.join(vroot, "updatecheck", "b.json"))
    check(ok.startswith(os.path.abspath(vroot)),
          "while a path in the vault is allowed",
          "a guard that refuses everything protects nothing")
except BaseException as exc:                                 # noqa: BLE001
    LEDGER.skip("the vault-path control", str(exc))

print("\n5. against the real tree")

if exe:
    state = UC.capture()
    for b in pinned.BUILDS:
        row = state["builds"].get(b.stamp, {})
        check(row.get("build") == b.number,
              f"{b.stamp}: capture reads build {b.number}", str(row.get("build")))
        check(len(row.get("signatures", {})) == 8,
              f"{b.stamp}: and all eight signature readings",
              str(len(row.get("signatures", {}))))
    check(state["schema"]["messages.json"]["validated_against_build"] == pinned.BUILD,
          "the schema stamp is read from where it actually lives",
          "nested under `provenance`; the top level answers None")
    check(len(state["pins"]) == 71,
          "and the class-(a) census rides along, at 71",
          f"{len(state['pins'])} -- and it must agree with test_buildpins.py's own "
          f"literal, which is the same number asserted from the other side. Was 64 "
          f"until 2026-08-14, when this tooling was cherry-picked onto a `main` that "
          f"had gained seven more build-coupled constants (modelfile.py's FVF stride "
          f"tables and accessor, atex.py's two level-codec VAs) while the branch sat "
          f"unmerged. Both literals moved together, on purpose: a baseline that "
          f"quietly disagreed with the census it is a baseline OF is how an update "
          f"report goes green over the wrong tree")

sys.exit(LEDGER.verdict())
