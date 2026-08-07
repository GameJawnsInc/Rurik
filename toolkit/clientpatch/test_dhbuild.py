"""Prove a client build is placed by its bytes, and that the old failure cannot recur.

    python toolkit/clientpatch/test_dhbuild.py

WHAT THIS IS DEFENDING. On 2026-08-06 a live-capture build -- ArenaNet's stock DH,
correct and wanted -- was written into `vault/client-patched/` as `Gw.live.<tag>.exe`,
beside the DH-patched `Gw.custom.<tag>.exe`. Two tools chose "the patched client" from
that directory with `sorted(...)[-1]`, `l` sorts after `c`, and both silently changed
which binary they were talking about. `test_handshake.py` reported four failures and a
short check count that read as a crypto regression; `make_run_dir.py` would have
assembled a client that cannot key into `vault/run/`, which `drive_client.assert_safe`
treats as the set of legal loopback targets.

So the load-bearing test here is section 3, which rebuilds that directory -- both builds
together, the stock one named so it sorts LAST -- and requires selection to still return
the DH-patched one. A fix for a name-ordering bug that is never shown a hostile ordering
has not been tested.

Sections 1 and 2 are the classifier itself, including the half-written struct, because a
classifier that only ever answers on well-formed input is not one. Section 4 asserts the
live invariant: every build in the vault sits in the directory its parameters say it
belongs in.

Section 5 asserts the other half of that, and it is a different claim. Section 4 says
every build is filed correctly TODAY; section 5 says the tool cannot file one wrongly
TOMORROW. Until 2026-08-07 it could: `make_run_dir.py` classified the source exe
byte-for-byte and accepted `--dest` on trust, so `--dest <vault>/run-live/<tag>` with no
`--live` assembled a DH-patched client into the one directory that must not be caged --
no flag in that command sounds dangerous, and every existing guard passed it.

Read-only. Reads client binaries and key files out of the vault and launches nothing.
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import dhbuild  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED, not guessed: a green run on 2026-08-07 with every fixture present reports
# 24 checks -- 4 + 4 + 6, plus one per build on disk in section 4 (5 here), plus 5 in
# section 5.
#
# The floor is 13: sections 1, 2 and 5. Sections 1 and 2 need only a pristine client and
# the vault's key files; section 5 is pure path arithmetic and needs no fixture at all,
# so it belongs in the mandatory core rather than below it.
#
# It stays well below 24 because the two richer sections are genuinely fixture-dependent
# and both declare skips: section 3 needs one build of EACH kind, and a machine that has
# not built the live client yet is a legal state (it was this repo's state until
# 2026-08-06), while section 4 counts whatever is on disk. checks.py asks a floor to be
# the mandatory core for exactly this case; the skips are what keep a thin run from
# reading as a thorough one, and the ledger prints them in the verdict.
#
# Section 3 is still outside the floor and that is a known weakness, not a decision this
# comment is defending: it is the only section that proves the 2026-08-06 regression is
# fixed, and a machine missing either build silently does not run it.
LEDGER = checks.Ledger("dhbuild", floor=13)


def scratch_copy(src, dst):
    """Copy a client binary into a scratch directory. A COPY, deliberately.

    The first version hardlinked, to save writing 10 MB twice. A hardlink is the same
    inode under two names, so the `os.utime` below -- which exists to make the scratch
    file the newest one -- rewrote the mtime of the VAULT artifact instead. Harmless in
    itself and exactly the class of thing a read-only test must not do; make_run_dir.py's
    own header makes the same argument about Gw.dat. 10 MB is cheap.
    """
    shutil.copy2(src, dst)
    return dst


def main():
    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})")

    # ---- 1. read the struct out of a binary we did not write ------------------
    print("\n1. the pinned struct, read from ArenaNet's own shipped client")
    cdir = vaultpath.require_dir("client", why="a pristine client to classify")
    pristine = None
    for build in sorted(os.listdir(cdir), reverse=True):
        cand = os.path.join(cdir, build, "Gw.exe")
        if os.path.isfile(cand):
            pristine = cand
            break
    if pristine is None:
        raise SystemExit(f"no Gw.exe under any build in {cdir} — see RUNBOOK.md")
    print(f"   {os.path.relpath(pristine, vaultpath.vault_root())}")

    g, p, B = dhbuild.read_params(pristine)
    LEDGER.ok(g == 4, "generator is 4", str(g))
    LEDGER.ok(p.bit_length() == 512, "prime is 512-bit", f"{p.bit_length()} bits")
    LEDGER.ok(1 < B < p, "B is in range 1 < B < p")

    # The shipped client must classify as stock. This is the check the artifact can
    # refute: the parameters come from the exe, the record they are compared against
    # came out of dump_dh_params.py on a different day, and nothing here forces
    # agreement.
    kind, detail = dhbuild.classify(pristine)
    LEDGER.ok(kind == dhbuild.STOCK, "the pristine client classifies as stock",
              f"{kind} -- {detail}")

    # ---- 2. the classifier, on parameters this test controls -------------------
    print("\n2. the classifier, against records it is handed")
    ours = [(dhbuild.OURS, "synthetic-ours.json", p, B)]
    kind, _ = dhbuild.classify(pristine, known=ours)
    LEDGER.ok(kind == dhbuild.OURS, "the same bytes classify as ours against an ours record",
              kind)

    # A prime that matches with a B that does not is the four-byte struct shift
    # make_custom_client.py's own comment records catching in development. It must be
    # named, not filed under "unrecognised build".
    half = [(dhbuild.OURS, "synthetic-half.json", p, B ^ 1)]
    kind, detail = dhbuild.classify(pristine, known=half)
    LEDGER.ok(kind == dhbuild.UNKNOWN, "a half-written struct is not accepted", kind)
    LEDGER.ok("half-written" in detail, "and it is reported AS half-written, not as new",
              detail)

    kind, detail = dhbuild.classify(pristine, known=[])
    LEDGER.ok(kind == dhbuild.UNKNOWN, "no key material at all means unknown", kind)

    # ---- 3. THE REGRESSION: hostile filename order ----------------------------
    print("\n3. both builds in one directory, stock sorting LAST")
    loop_dir = vaultpath.vault_path(dhbuild.LOOPBACK_DIR)
    live_dir = vaultpath.vault_path(dhbuild.LIVE_DIR)
    try:
        ours_exe = dhbuild.select(dhbuild.OURS, loop_dir)
        stock_exe = dhbuild.select(dhbuild.STOCK, live_dir)
    except SystemExit as e:
        ours_exe = stock_exe = None
        LEDGER.skip("hostile filename order",
                    f"need one build of each kind in the vault: {str(e).splitlines()[0]}")

    if ours_exe and stock_exe:
        with tempfile.TemporaryDirectory() as tmp:
            # `Gw.zzz...` sorts after `Gw.aaa...` under exactly the rule that broke
            # this -- and it is also the NEWER file by mtime, so neither the old
            # selection nor a naive "newest wins" would get it right.
            scratch_copy(ours_exe, os.path.join(tmp, "Gw.aaa.exe"))
            wrong = scratch_copy(stock_exe, os.path.join(tmp, "Gw.zzz.exe"))
            os.utime(wrong, None)

            names = sorted(os.listdir(tmp))
            LEDGER.ok(names[-1] == "Gw.zzz.exe",
                      "the scratch directory really does sort the stock build last",
                      str(names))

            picked = dhbuild.select(dhbuild.OURS, tmp)
            LEDGER.ok(os.path.basename(picked) == "Gw.aaa.exe",
                      "select(ours) ignores name order and returns the DH-patched build",
                      os.path.basename(picked))
            LEDGER.ok(dhbuild.classify(picked)[0] == dhbuild.OURS,
                      "and what it returned really does carry our parameters")

            picked = dhbuild.select(dhbuild.STOCK, tmp)
            LEDGER.ok(os.path.basename(picked) == "Gw.zzz.exe",
                      "select(stock) finds the live build in the same directory",
                      os.path.basename(picked))

        # A directory holding only the wrong kind must REFUSE, and the refusal is the
        # product: it has to say ARTIFACT loudly enough that nobody opens gwcrypto.py.
        with tempfile.TemporaryDirectory() as tmp:
            scratch_copy(stock_exe, os.path.join(tmp, "Gw.live.exe"))
            try:
                got = dhbuild.select(dhbuild.OURS, tmp)
                LEDGER.ok(False, "a stock-only directory refuses select(ours)",
                          f"returned {got}")
            except SystemExit as e:
                msg = str(e)
                LEDGER.ok(True, "a stock-only directory refuses select(ours)")
                LEDGER.ok("WRONG ARTIFACT" in msg and "gwcrypto" in msg,
                          "and the refusal names the artifact instead of the crypto",
                          msg.splitlines()[0])

    # ---- 4. the live invariant ------------------------------------------------
    print("\n4. every build in the vault is where its parameters say it belongs")
    seen = 0
    for subdir, expect in ((dhbuild.LOOPBACK_DIR, dhbuild.OURS),
                           (dhbuild.LIVE_DIR, dhbuild.STOCK),
                           ("run", dhbuild.OURS), ("run-live", dhbuild.STOCK)):
        root = vaultpath.vault_path(subdir)
        if not os.path.isdir(root):
            continue
        found = list(dhbuild.inventory(root))
        for name in sorted(os.listdir(root)):
            nested = os.path.join(root, name, "Gw.exe")
            if os.path.isfile(nested):
                found.append((nested,) + dhbuild.classify(nested))
        for path, kind, detail in found:
            seen += 1
            LEDGER.ok(kind == expect,
                      f"vault/{subdir}/{os.path.relpath(path, root)} is {expect}",
                      f"{kind} -- {detail}")
    if not seen:
        LEDGER.skip("vault placement", "no builds in any staging or run directory")

    # ---- 5. the destination is a safety assertion, and it is checked -----------
    # Section 4 proves every build on disk is filed correctly TODAY. This proves the
    # tool cannot file one wrongly TOMORROW, which is a different claim: until
    # 2026-08-07 make_run_dir.py classified the source exe byte-for-byte and took
    # --dest entirely on trust, so `--dest <vault>/run-live/<tag>` with no --live
    # assembled a DH-patched client into the directory that must not be caged.
    #
    # Pure-function checks, so no 4 GB copy is involved: the refusal happens before
    # anything is written.
    print("\n5. a run directory cannot be assembled into the other kind's root")
    import make_run_dir  # noqa: E402  -- imported here; it is a CLI, not a library

    for subdir, expect, why in (
            ("run", dhbuild.OURS, "vault/run means ours"),
            ("run-live", dhbuild.STOCK, "vault/run-live means stock"),
    ):
        got, _ = make_run_dir.root_meaning(vaultpath.vault_path(subdir, "2026-01-01_x"))
        LEDGER.ok(got == expect, why, f"got {got}")

    # The trap this function was written around: "run-live" starts with "run", so a
    # bare startswith would file every live build as a loopback one -- the failure
    # arriving through the check meant to catch it.
    got, _ = make_run_dir.root_meaning(vaultpath.vault_path("run-live"))
    LEDGER.ok(got == dhbuild.STOCK,
              "the run/run-live prefix trap: run-live does not read as run",
              f"got {got}")

    got, _ = make_run_dir.root_meaning(vaultpath.vault_path("runaway"))
    LEDGER.ok(got is None,
              "a sibling that merely starts with 'run' belongs to neither",
              f"got {got}")

    got, _ = make_run_dir.root_meaning(os.path.join(tempfile.gettempdir(), "elsewhere"))
    LEDGER.ok(got is None,
              "a path outside both roots is refused rather than defaulted",
              f"got {got} -- it would inherit no cage sweep and no assert_safe guarantee")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
