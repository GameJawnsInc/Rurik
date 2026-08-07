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
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import buildid  # noqa: E402

SRC = r"C:\gw"
# Everything the client loads beside itself. GwLoginClient.dll is deliberately
# absent: Gw.exe never calls it (see studies/handshake/PLAN.md §3), it belongs to
# third-party launchers, and leaving it out keeps that fact honest.
SUPPORT = ["OpenAL32.dll", "steam_api.dll", "steam_appid.txt", "Gw.dat"]


def _running_clients():
    """One line naming every Gw.exe currently up, so the operator knows which to close.

    Best effort by design: this is a diagnostic on an error path, and a tasklist that
    will not run must not turn a clear message into a second failure.
    """
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Gw.exe", "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
        pids = [ln.split()[1] for ln in out.splitlines() if ln.strip().startswith("Gw.exe")]
        return f"Running Gw.exe: {', '.join(f'pid {p}' for p in pids) or 'none found'}"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "Could not enumerate running clients."


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
    ap.add_argument("--patched", help="patched exe; default = newest in vault/client-patched")
    ap.add_argument("--dest", help="run directory; default = vault/run/<build tag>")
    ap.add_argument("--exe", dest="patched", help=argparse.SUPPRESS)  # alias
    ap.add_argument("--live", action="store_true",
                    help="stage the LIVE-CAPTURE build (ArenaNet's DH parameters, "
                         "updater and mutex patches only) into vault/run-live instead. "
                         "That root is deliberately separate: isolate_client.ps1 sweeps "
                         "vault/run and would cage this build, which is the one place "
                         "it cannot work.")
    a = ap.parse_args()

    # Two roots, and the split is load-bearing rather than tidy. isolate_client.ps1
    # with no arguments cages every Gw.exe under vault/run -- that default is itself a
    # fix, for the day a -probe copy sat uncaged -- so a live-capture build parked
    # there would be silently caged by the very sweep that keeps us safe. The bytes
    # still decide at launch (cage.assert_launch_safe reads the DH parameters); the
    # root only decides who sweeps what.
    stem = "Gw.live." if a.live else "Gw.custom."
    root = "run-live" if a.live else "run"

    pdir = r"C:\gd\Rurik\vault\client-patched"
    if a.patched:
        patched = a.patched
    else:
        # Select by PREFIX, never by "newest .exe". Plain lexicographic order puts
        # Gw.live.* after Gw.custom.*, so the moment a live-capture build exists the
        # bare default would silently start staging it into vault/run.
        exes = sorted(f for f in os.listdir(pdir)
                      if f.endswith(".exe") and f.startswith(stem))
        if not exes:
            raise SystemExit(
                f"No {stem}*.exe in {pdir}.\n"
                f"  Run: python toolkit/clientpatch/make_custom_client.py"
                f"{' --live-capture' if a.live else ''}")
        patched = os.path.join(pdir, exes[-1])

    tag = os.path.basename(patched)
    for p in ("Gw.custom.", "Gw.live."):
        tag = tag.replace(p, "")
    tag = tag.replace(".exe", "")
    dest = a.dest or os.path.join(r"C:\gd\Rurik\vault", root, tag)
    os.makedirs(dest, exist_ok=True)

    # What we are about to stage, checked against the mode we were asked for, before
    # 4 GB of Gw.dat is copied. --dest can point anywhere, and a live build staged
    # under vault/run is exactly the confusion the two roots exist to prevent.
    want = buildid.STOCK if a.live else buildid.OURS
    got, why = buildid.dh_verdict(patched)
    if got != want:
        raise SystemExit(
            f"REFUSING to stage {patched} as {'--live' if a.live else 'the loopback build'}\n"
            f"  its Diffie-Hellman parameters read as {got!r}, wanted {want!r}\n"
            f"  {why}")

    print(f"patched exe : {patched}")
    print(f"run dir     : {dest}\n")

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
        try:
            secs = copy_with_progress(src, dst)
        except PermissionError as exc:
            # A running client holds Gw.dat open exclusively, and Windows reports that
            # as a bare Errno 13 four frames deep. RUNBOOK already records the mirror
            # case (a run dir's Gw.dat cannot be opened while its client is up); this
            # is the same fact from the other side and it deserves the same sentence
            # rather than a traceback that reads like a permissions bug.
            raise SystemExit(
                f"\nCannot read {src}: {exc.strerror}.\n"
                f"  A running Guild Wars client holds its Gw.dat open exclusively.\n"
                f"  {_running_clients()}\n"
                f"  Close the client that owns {os.path.dirname(src)} and re-run this;\n"
                f"  everything already copied is kept and skipped on the next pass.\n"
                f"  {dest} is INCOMPLETE until then, and the launch gate refuses an\n"
                f"  incomplete run directory rather than starting a client that would\n"
                f"  fail somewhere less obvious.")
        print(f"  {name:18s}done in {secs:.1f}s")

    # PowerShell parses a leading quoted string as a VALUE, not a command, so
    # `"C:\...\Gw.exe" -authsrv ...` is a parser error rather than a launch. The
    # call operator `&` is what makes it a command. cmd.exe wants no operator at
    # all. Print both rather than guess which shell is reading this.
    if a.live:
        print(f"""
This is the LIVE-CAPTURE build. It carries ArenaNet's own Diffie-Hellman
parameters, so it cannot talk to our server at all, and it must NOT be caged --
the cage pins to loopback, which is the one place it has no business being.

  1)  Do NOT run isolate_client.ps1 against it. That script sweeps vault/run;
      this copy is under vault/run-live so the bare sweep will not find it.
  2)  Read PLAN.md §6.2 before launching. The behavioural rule is the control
      that matters -- human cadence, human hours, one client -- and the account
      is named per launch rather than autofilled.
  3)  Check the whole machine's state first:

        python toolkit/clientpatch/cage.py

The launch gate reads the DH parameters out of the binary, so pointing this copy
at loopback is refused, and pointing the vault/run copy at the real service is
refused. Neither refusal depends on which directory it sits in.
""")
    else:
        print(f"""
Run it from three terminals:

  1)  python toolkit/portal/webgate.py
  2)  python toolkit/authsrv/authsrv.py
  3)  the patched client:

      PowerShell:
        & "{tgt}" -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed

      cmd.exe:
        "{tgt}" -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed

Cage it first, elevated, or the launch gate refuses it:

      & "C:\\gd\\Rurik\\toolkit\\clientpatch\\isolate_client.ps1"

Launching the exe directly is correct as long as the updater kill switch is in
this build -- check with `python toolkit/clientpatch/buildid.py`. It is what
makes the cage survivable: the pre-login patcher needs one outbound check that
the cage denies forever, and with the updater off that patcher never runs.
launch_caged.ps1 is the old workaround for a build WITHOUT the kill switch, and
it opens the cage to do its job; it refuses to run against a build that does not
need it.

Terminal 3 must be THIS copy. A stock client keys against ArenaNet's compiled-in
public value, so the handshake completes and nothing after it can be decrypted.
""")


if __name__ == "__main__":
    sys.exit(main())
