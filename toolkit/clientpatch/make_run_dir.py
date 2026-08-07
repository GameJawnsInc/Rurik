"""Assemble a self-contained directory the patched client can actually run from.

A patched Gw.exe on its own does nothing: the client wants Gw.dat and its DLLs
beside it. This builds an isolated run directory so none of that has to happen
inside C:\\gw.

Why a full copy of Gw.dat rather than a hardlink, given it is 4 GB: the client
WRITES to Gw.dat when it patches content, and a hardlink is the same file under
two names -- a patched client that mangles it would mangle the real install's copy
too. The vault snapshot is not a safe link target either, because the point of a
snapshot is that nothing writes to it. Disk is cheap and the install is not.

Gw.dat is a moving target in its own right. It grew between two reads on the day
this was written (4,196,497,128 -> 4,198,489,600 bytes), so treat any run
directory as a point-in-time working copy, not a reference.

TWO DESTINATIONS, and they are not interchangeable (PLAN.md §6.2):

    vault/run/<tag>       OUR DH parameters.  Loopback only, and caged.
    vault/run-live/<tag>  ArenaNet's stock DH. Live capture only, and NOT caged.

`assert_safe` in `toolkit/harness/drive_client.py` accepts any Gw.exe under
`vault/run/`, so what lands there is a safety decision rather than a filing one.
This used to pick the source exe with `sorted(...)[-1]` over `vault/client-patched/`,
which on 2026-08-06 -- once a stock-DH build was written into that directory as
`Gw.live.<tag>.exe`, and `l` sorts after `c` -- would have assembled the stock build
into `vault/run/` and handed the harness a loopback target that cannot key. Selection
is by parameters now, through `dhbuild.py`, and an explicitly passed `--patched` is
classified too rather than trusted.
"""

import argparse
import os
import re
import shutil
import stat
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dhbuild  # noqa: E402
import vaultpath  # noqa: E402

SRC = r"C:\gw"
# Everything the client loads beside itself. GwLoginClient.dll is deliberately
# absent: Gw.exe never calls it (see studies/handshake/PLAN.md §3), it belongs to
# third-party launchers, and leaving it out keeps that fact honest.
SUPPORT = ["OpenAL32.dll", "steam_api.dll", "steam_appid.txt", "Gw.dat"]


def copy_with_progress(src, dst):
    total = os.path.getsize(src)
    done = 0
    t0 = time.time()
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while True:
            b = fi.read(16 << 20)
            if not b:
                break
            fo.write(b)
            done += len(b)
            if total > (1 << 30) and done % (1 << 30) < (16 << 20):
                print(f"      {100*done/total:5.1f}%  ({done/1e9:.1f}/{total/1e9:.1f} GB)",
                      flush=True)
    shutil.copystat(src, dst)
    return time.time() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patched",
                    help="source exe; default = newest build with the right DH "
                         "parameters in vault/client-patched (or -live, with --live)")
    ap.add_argument("--dest", help="run directory; default = vault/run[-live]/<build tag>")
    ap.add_argument("--live", action="store_true",
                    help="assemble the LIVE-CAPTURE client -- ArenaNet's stock DH, into "
                         "vault/run-live/. This one is meant to reach the real service, "
                         "so it must not be caged and must not be driven by "
                         "drive_client.py. See PLAN.md §6.2 and §7 Q4.")
    a = ap.parse_args()

    want = dhbuild.STOCK if a.live else dhbuild.OURS
    run_root = vaultpath.vault_path("run-live" if a.live else "run")

    if a.patched:
        patched = a.patched
        # An explicit path is classified, not trusted. Passing the wrong build by hand is
        # the same mistake as picking it by filename order, and it lands in the same
        # place -- a directory whose contents the harness reads as a safety guarantee.
        kind, detail = dhbuild.classify(patched)
        if kind != want:
            fix = "Drop --live" if a.live else "Add --live"
            raise SystemExit(
                f"REFUSING to assemble {patched}\n"
                f"  It carries {kind} parameters ({detail}),\n"
                f"  and {os.path.basename(run_root)}/ takes {want}.\n"
                f"  vault/run/ is loopback-only, vault/run-live/ is live-only, and\n"
                f"  drive_client.py accepts anything under vault/run/ -- so the wrong\n"
                f"  build here is a safety failure, not a filing error.\n"
                f"  {fix} if that is what you meant.")
    else:
        patched = dhbuild.select(want, why=f"assembling a {want} run directory")

    kind, detail = dhbuild.classify(patched)
    # Both staging names are Gw.<variant>.<tag>.exe. The old `.replace("Gw.custom.", "")`
    # left "Gw.live." in place for anything not called custom, producing a run directory
    # named after the variant instead of the build.
    m = re.match(r"Gw\.[^.]+\.(.+)\.exe$", os.path.basename(patched), re.I)
    tag = m.group(1) if m else os.path.splitext(os.path.basename(patched))[0]
    dest = a.dest or os.path.join(run_root, tag)
    os.makedirs(dest, exist_ok=True)

    print(f"source exe  : {patched}")
    print(f"parameters  : {kind} -- {detail}")
    print(f"run dir     : {dest}")
    print(f"posture     : {dhbuild.WHERE[kind][1]}\n")

    # Named plain Gw.exe so nothing downstream depends on an odd filename.
    tgt = os.path.join(dest, "Gw.exe")
    # The run copy is left read-only: the client's own patcher replaces Gw.exe by
    # writing Gw.tmp and renaming over it, and a successful self-update would
    # rotate the Diffie-Hellman parameters and turn our patch into a brick. The
    # read-only bit makes that fail loudly instead of silently succeeding. It has
    # to be cleared here or this copy raises PermissionError on the second run.
    if os.path.exists(tgt):
        os.chmod(tgt, stat.S_IWRITE | stat.S_IREAD)
    shutil.copy2(patched, tgt)
    os.chmod(tgt, stat.S_IREAD)
    print(f"  Gw.exe            copied ({os.path.getsize(tgt)/1e6:.1f} MB), read-only")

    for name in SUPPORT:
        src = os.path.join(SRC, name)
        dst = os.path.join(dest, name)
        if not os.path.exists(src):
            print(f"  {name:18s}MISSING in {SRC}")
            continue
        size = os.path.getsize(src)
        if os.path.exists(dst) and os.path.getsize(dst) == size:
            print(f"  {name:18s}already present, skipping ({size/1e6:.1f} MB)")
            continue
        print(f"  {name:18s}copying {size/1e6:.1f} MB ...", flush=True)
        secs = copy_with_progress(src, dst)
        print(f"  {name:18s}done in {secs:.1f}s")

    if a.live:
        # Deliberately NOT a copy-paste command line. This build is the one that can
        # reach ArenaNet, its preconditions are §6.2's and not this script's to certify,
        # and printing a ready-to-run invocation is how a staging step turns into a
        # launch nobody decided to make.
        print(f"""
Assembled the LIVE-CAPTURE client: ArenaNet's stock DH, updater off, multi-instance on.

  {tgt}

This one is the mirror image of the loopback build, in every rule that matters:

  * DO NOT cage it. isolate_client.ps1 pins a client to loopback by program path and
    has no partial setting, so a caged live client simply cannot work. It enumerates
    vault/run/ only, which is why this directory is not under it.
  * DO NOT drive it with toolkit/harness/drive_client.py. That refuses anything outside
    vault/run/ and requires -authsrv/-portal at 127.x, which is the opposite of this
    build's purpose. There is no automation path for it yet, on purpose.
  * The secondary account only, and it must carry `automation: true` in
    vault/keys/accounts.json (toolkit/harness/accounts.py enforces that).
  * Human cadence, human hours, one client, never in a competitive context. PLAN.md
    §6.1's risk row is explicit that the traffic PATTERN is what closes accounts.

Read PLAN.md §6.2 before the first live run. Having this build is one precondition,
not all of them.
""")
        return

    # PowerShell parses a leading quoted string as a VALUE, not a command, so
    # `"C:\...\Gw.exe" -authsrv ...` is a parser error rather than a launch. The
    # call operator `&` is what makes it a command. cmd.exe wants no operator at
    # all. Print both rather than guess which shell is reading this.
    print(f"""
Run it from three terminals:

  1)  python toolkit/portal/webgate.py
  2)  python toolkit/authsrv/authsrv.py
  3)  the patched client:

      PowerShell:
        & "{tgt}" -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed

      cmd.exe:
        "{tgt}" -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed

If you have run isolate_client.ps1, do NOT launch it that way -- the pre-login
patcher needs one outbound check and the cage denies it forever, leaving the
client on "Connecting to ArenaNet". Use the launcher instead, elevated:

      & "C:\\gd\\Rurik\\toolkit\\clientpatch\\launch_caged.ps1"

Terminal 3 must be THIS copy. A stock client keys against ArenaNet's compiled-in
public value, so the handshake completes and nothing after it can be decrypted.
""")


if __name__ == "__main__":
    sys.exit(main())
