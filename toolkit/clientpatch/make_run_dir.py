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
import sys
import time

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
    ap.add_argument("--patched", help="patched exe; default = newest in vault/client-patched")
    ap.add_argument("--dest", help="run directory; default = vault/run/<build tag>")
    a = ap.parse_args()

    pdir = r"C:\gd\Rurik\vault\client-patched"
    if a.patched:
        patched = a.patched
    else:
        exes = sorted(f for f in os.listdir(pdir) if f.endswith(".exe"))
        if not exes:
            raise SystemExit("No patched client. Run toolkit/clientpatch/make_custom_client.py first.")
        patched = os.path.join(pdir, exes[-1])

    tag = os.path.basename(patched).replace("Gw.custom.", "").replace(".exe", "")
    dest = a.dest or os.path.join(r"C:\gd\Rurik\vault\run", tag)
    os.makedirs(dest, exist_ok=True)

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
        secs = copy_with_progress(src, dst)
        print(f"  {name:18s}done in {secs:.1f}s")

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
