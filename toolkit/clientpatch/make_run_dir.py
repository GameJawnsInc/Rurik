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


def root_meaning(path):
    """(kind, root) that `path` sits under, or (None, None) if it is neither run root.

    The destination decides what a build MEANS to everything downstream --
    `drive_client.assert_safe` reads "under vault/run" as "cleared for loopback", and
    `isolate_client.ps1`'s bare sweep cages every client under vault/run and skips
    vault/run-live. So the directory is a safety assertion, and it has to be checked
    against the bytes rather than against the flag that chose the default.

    The prefix test is `root + os.sep`, never a bare startswith: "run-live" starts with
    "run", so a bare prefix match would file every live build as a loopback one -- which
    is the exact failure this function exists to catch, arriving through the check
    itself.
    """
    p = os.path.normcase(os.path.abspath(path))
    for name, kind in (("run", dhbuild.OURS), ("run-live", dhbuild.STOCK)):
        r = os.path.normcase(os.path.abspath(vaultpath.vault_path(name)))
        if p == r or p.startswith(r + os.sep):
            return kind, name
    return None, None


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

    # The DESTINATION is checked against the build's own bytes, not against --live.
    # Until 2026-08-07 only the source was classified: --dest was taken on trust and was
    # not required to fall under the run root the script had just computed. So
    #
    #     make_run_dir.py --dest <vault>/run-live/<tag>
    #
    # with no --live passed every guard in this file -- want was OURS, the source really
    # was ours, and nothing looked at where it was going -- and assembled a DH-PATCHED
    # client into the directory §6.2 documents as "meant to reach the real service" and
    # "must NOT be caged". That is the account-losing configuration, reachable by a
    # command with no dangerous-sounding flag in it. The mirror case put a stock build
    # under vault/run/, where drive_client trusts it as a loopback target.
    #
    # Comparing `kind` (read from the DH struct) rather than `want` (read from argv) is
    # what makes the flag irrelevant to safety: --live now only picks a default, and
    # cannot authorise anything.
    dest_kind, dest_name = root_meaning(dest)
    if dest_kind is None:
        raise SystemExit(
            f"REFUSING to assemble into {dest}\n"
            f"  A run directory must live under vault/run/ or vault/run-live/. Those\n"
            f"  two paths are read as safety assertions downstream -- drive_client.py\n"
            f"  accepts anything under vault/run/ as a loopback target, and\n"
            f"  isolate_client.ps1 cages everything there and nothing under run-live.\n"
            f"  A build somewhere else inherits neither guarantee and no sweep.")
    if dest_kind != kind:
        raise SystemExit(
            f"REFUSING to assemble into vault/{dest_name}/\n"
            f"  {os.path.basename(patched)} carries {kind} parameters: {detail}\n"
            f"  vault/{dest_name}/ means {dest_kind} -- {dhbuild.WHERE[dest_kind][1]}.\n"
            f"  This is checked against the binary's Diffie-Hellman struct, not against\n"
            f"  --live, so passing or omitting that flag cannot make it true.\n"
            f"  {'A DH-patched client reaching the real service completes a REAL Stage A'  if kind == dhbuild.OURS else 'A stock client cannot key against our server at all'}\n"
            f"  {'login with the autofilled credential before it fails. See PLAN.md §6.2.' if kind == dhbuild.OURS else '-- the channel would never come up. See PLAN.md §6.2.'}")

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

    # Registered HERE as well as in make_custom_client.py, and the duplication is
    # the point: this is the only thing that creates `vault/run/<stamp>/Gw.exe`,
    # which is the exact path `pinned.find()` hands back and the exact path a
    # running client reports through `keytap.module_info`. Hooking only the
    # earlier stage would leave a run directory assembled from a hand-supplied
    # `--patched` exe unregistered. A copy has the source's digest, so the usual
    # case is `already` and costs one hash.
    #
    # THE BUILD COMES FROM THE BYTES, and `tag` may only DISAGREE, loudly. This
    # passed `build=tag` until 2026-08-19 -- and `tag` is a regex over the source
    # exe's FILENAME (see above), while `register_patched` prefers an explicit
    # build over both the source hash and its own inference. `CLAUDE.md`'s rule
    # is "never select a build by filename", and this file already carries the
    # reason in its own header: picking the source by name is what would have
    # assembled a stock-DH client into vault/run/. The same mistake through the
    # registry is quieter -- 38797 and 38833 are the SAME LENGTH, so a mis-named
    # source would have been filed under the wrong build with every size check
    # passing. So `infer_build` (hash and structural distance) decides, the
    # filename is a cross-check, and a disagreement refuses the registration
    # rather than picking one.
    #
    # NON-FATAL, deliberately, and the import is INSIDE the same try as the call
    # so that sentence is enforced here rather than asserted in prose: the run
    # directory is already assembled and verified, and an unregistered copy is
    # not dangerous, it is refused later by a gate that says how to recover.
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clientscan"))
        import pinned  # noqa: E402
        named = pinned.known_build(tag)
        inferred, iwhy = pinned.infer_build(tgt)
        if named is not None and inferred is not None and named is not inferred:
            digest, action, note = None, "refused", (
                f"the source exe is NAMED {tag} -- build {pinned.name_of(named)} "
                f"-- but its bytes are build {pinned.name_of(inferred)} ({iwhy}). "
                f"A build is never selected by filename here. Rename the source, "
                f"or register it by hand once you know which it is.")
        else:
            if named is None:
                agrees = (f"the filename tag {tag} names no build we hold, so "
                          f"the bytes decided alone")
            elif inferred is None:
                agrees = (f"the filename tag {tag} was NOT corroborated -- the "
                          f"bytes named no build ({iwhy})")
            else:
                agrees = f"the filename tag {tag} agrees with the bytes"
            digest, action, note = pinned.register_patched(
                tgt, build=None, tool="make_run_dir.py",
                how=(f"{kind} parameters -- {detail}; assembled into "
                     f"vault/{dest_name}/; {agrees}"))
    except Exception as exc:                                 # noqa: BLE001
        digest, action, note = None, "unavailable", f"{type(exc).__name__}: {exc}"
    if action in ("added", "already"):
        print(f"  registered        {action}: pinned.py accepts this copy "
              f"({digest[:16] if digest else '?'}...)")
    else:
        print(f"\n!! NOT REGISTERED ({action}): {note}")
        print(f"!! The run directory is fine, but pinned.assert_build() will REFUSE")
        print(f"!! this exe. Recover with:")
        print(f"!!   python toolkit/clientscan/pinned.py --register {tgt}")

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
  * The launch gate decides from the BYTES, not from this directory. Whatever launches
    it goes through cage.assert_launch_safe(exe, host), which reads the Diffie-Hellman
    struct: this build may only be pointed at the real service, the loopback build only
    at 127.x, and neither can be argued into the other by a flag or a path. A missing
    -portal counts as LIVE, because the client falls back to its compiled-in ArenaNet
    endpoint.
  * The secondary account only, and it must carry `automation: true` in
    vault/keys/accounts.json (toolkit/harness/accounts.py enforces that). The flag is
    opt-in, so the primary is refused by default rather than by being remembered.
  * Human cadence, human hours, one client, never in a competitive context. PLAN.md
    §6.1's risk row is explicit that the traffic PATTERN is what closes accounts, not
    any single request -- so no guard in this repo can substitute for that one.

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
