"""Proves the launch-time cage guard refuses, and refuses for the right reasons.

The guard exists because on 2026-08-06 two patched binaries sat under `vault/run` and
only one was caged, for a day, and `assert_safe` waved the uncaged one through -- it
checks the exe's path and the loopback flags, both of which an uncaged copy passes.

So the assertions here are almost all NEGATIVE: constructed situations that MUST be
refused. A guard nobody has watched refuse is the same class of thing as a test nobody
has watched fail, and this one stands between a patched client and an account.

The live half -- "every patched client on this machine is currently caged" -- declares a
skip rather than a failure when the firewall cannot be read, because that is an
environment fact rather than a defect. It is never silent.

    python toolkit/clientpatch/test_cage.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
import checks  # noqa: E402
import cage  # noqa: E402
import pinned  # noqa: E402
import vaultpath  # noqa: E402

# 7 refusal + 2 live = 9, measured green on a machine with both clients caged. The live
# pair declares a skip when the firewall cannot be read, which drops the count to 7 --
# so the floor is 7, and the skip is printed rather than the run silently shrinking.
LEDGER = checks.Ledger("launch cage guard", floor=7)


def refused(fn, *a, **kw):
    """True if the call raised rather than returning. The only acceptable outcome."""
    try:
        fn(*a, **kw)
        return False
    except SystemExit:
        return True


def main():
    # --- an unrecognised binary is refused, not waved through -------------------
    # This is the case that matters most for the future: make_custom_client generates
    # fresh DH parameters, so the NEXT patched copy has a hash nobody has recorded.
    # A guard that passed everything it did not recognise would be worthless exactly
    # when a new binary appears.
    with tempfile.TemporaryDirectory() as tmp:
        junk = os.path.join(tmp, "Gw.exe")
        with open(junk, "wb") as fh:
            fh.write(b"MZ" + b"\0" * 4096)
        LEDGER.ok(refused(cage.assert_caged, junk),
                  "an unrecognised binary is REFUSED", "wrong size, unknown hash")

        missing = os.path.join(tmp, "nope", "Gw.exe")
        LEDGER.ok(refused(cage.assert_caged, missing),
                  "a path that does not exist is REFUSED")

    # --- the pristine client is refused too, and for its own reason -------------
    pristine = vaultpath.vault_path("client", pinned.STAMP, "Gw.exe")
    if os.path.isfile(pristine):
        kind, _ = pinned.identify(pristine)
        LEDGER.ok(kind == "pristine",
                  "the vaulted pristine client is identified as pristine", kind)
        LEDGER.ok(refused(cage.assert_caged, pristine),
                  "the PRISTINE client is REFUSED as a launch target",
                  "it carries ArenaNet's DH parameters, not ours")
    else:
        LEDGER.skip("pristine client", f"not in the vault at {pristine}")

    # --- the state parser only accepts the four states it knows ------------------
    # Guards against the failure where a changed PowerShell output format is read as
    # a pass. Anything unexpected must become None, and None must refuse.
    LEDGER.ok(cage.cage_state(os.path.join("C:\\", "no", "such", "Gw.exe")) in
              ("UNCAGED", None),
              "a path no firewall rule names reads as UNCAGED or undeterminable")

    saved = cage.cage_state
    try:
        cage.cage_state = lambda _exe: None
        run_exe = _any_patched()
        if run_exe:
            LEDGER.ok(refused(cage.assert_caged, run_exe),
                      "when the cage state cannot be determined, launching is REFUSED",
                      "undeterminable is not permission")
        else:
            LEDGER.skip("undeterminable-state refusal", "no patched client on disk")

        cage.cage_state = lambda _exe: "UNCAGED"
        if run_exe:
            LEDGER.ok(refused(cage.assert_caged, run_exe),
                      "an UNCAGED patched client is REFUSED")
            cage.cage_state = lambda _exe: "ALLOW-ONLY"
            LEDGER.ok(refused(cage.assert_caged, run_exe),
                      "ALLOW-ONLY is REFUSED -- the block rule is the cage",
                      "an orphaned allow looks like cleanup and permits everything")
        else:
            LEDGER.skip("uncaged refusal", "no patched client on disk")
    finally:
        cage.cage_state = saved

    # --- and the live state, which is the thing the guard is protecting ----------
    run_root = vaultpath.vault_path("run")
    clients = []
    if os.path.isdir(run_root):
        clients = [os.path.join(run_root, d, "Gw.exe")
                   for d in sorted(os.listdir(run_root))
                   if os.path.isfile(os.path.join(run_root, d, "Gw.exe"))]
    if not clients:
        LEDGER.skip("live cage state", f"no patched client under {run_root}")
    else:
        states = {c: cage.cage_state(c) for c in clients}
        if any(v is None for v in states.values()):
            LEDGER.skip("live cage state",
                        "firewall could not be enumerated from this session")
        else:
            uncaged = [c for c, v in states.items() if v != "CAGED"]
            LEDGER.ok(not uncaged,
                      f"every patched client on this machine is caged "
                      f"({len(clients)} found)",
                      "; ".join(f"{os.path.basename(os.path.dirname(c))}="
                                f"{states[c]}" for c in uncaged) if uncaged else "")
            LEDGER.ok(all(cage.assert_caged(c) == "patched" for c in clients),
                      "and assert_caged accepts each of them")

    return LEDGER.verdict()


def _any_patched():
    run_root = vaultpath.vault_path("run")
    if not os.path.isdir(run_root):
        return None
    for d in sorted(os.listdir(run_root)):
        exe = os.path.join(run_root, d, "Gw.exe")
        if os.path.isfile(exe) and pinned.identify(exe)[0] == "patched":
            return exe
    return None


if __name__ == "__main__":
    sys.exit(main())
