"""Inject movehook into the already-running client, in one command.

    python toolkit/clientscan/movehook/attach.py                 # 10 minute capture
    python toolkit/clientscan/movehook/attach.py --minutes 3
    python toolkit/clientscan/movehook/attach.py --out D:\\scratch\\hookout

WHY THIS AND NOT `autoinject.py`, WHICH IS THE OBVIOUS THING TO REACH FOR.
`autoinject.py` polls at 25 ms and injects the instant the pid appears, because
**terrain builds once at map load** -- a measured ~7 second window, after which a
perfectly correct breakpoint sees `hits 0`. Movement is not like that: the bake, the
setter and the teleport fire continuously for as long as anything moves, so there is
no window to miss.

And autoinject would actively hurt here. The DLL's run timer starts at INJECTION, so
arming at launch spends the first minutes of a bounded capture sitting on the login
screen. The right shape for this hook is the opposite one: let the operator get the
character into the world and into position, THEN attach, so the whole capture window
is spent on the behaviour being measured.

REFUSES A SECOND ATTACH, for the same reason autoinject does: the DLL patches bytes
and restores them on disarm, so a double load arms each site twice and restores once
-- leaving a live 0xCC in the client's code after the run ends. That is a crash with
our name on it, so it is checked rather than trusted.

Stdlib only; the remote-thread dance is `inject.py`'s and is not reimplemented here.
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "harness"))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))     # toolkit/

import autoinject                                              # noqa: E402
import inject                                                  # noqa: E402
import vaultpath                                               # noqa: E402

DLL = os.path.join(HERE, "movehook.dll")
STATUS = os.path.join(HERE, "movehook.status")

# The DLL's own DEFDIR, duplicated deliberately: --stop has to know where to
# look for the artifact, and importing anything from the C source is not a
# thing. If DEFDIR in movehook.c ever moves, this is the line that must move
# with it -- and test_movehook.py checks the two agree rather than trusting it.
#
# FOUND WITH vaultpath, NEVER WITH A RELATIVE WALK, 2026-08-31. This was
# `dirname(dirname(dirname(HERE)))/vault/...`, which is correct in the main tree
# and WRONG in every worktree: a worktree has no vault of its own, so the walk
# resolved to a directory that does not exist while the DLL -- whose DEFDIR is
# compiled in as an ABSOLUTE path -- kept writing to the real one. §16 is the
# check that catches it and its own message names the cost: `--stop` reports a
# missing capture that exists. CLAUDE.md's rule, and the reason it is a rule.
def default_outdir():
    return os.path.abspath(vaultpath.vault_path("research", "movecode"))


DEFAULT_OUT = default_outdir()


def armed_outdir(explicit=None):
    """Where the run that is CURRENTLY ARMED is writing.

    Precedence: an explicit --out, then `movehook.cfg`, then the default.

    THE CFG IS THE POINT. `--stop` has to look where the DLL is actually
    writing, and the DLL reads that path out of the cfg -- so the cfg is the
    ground truth, not this script's default. Without this, the natural
    `attach.py --stop` (no --out, exactly what the operator typed on R5) would
    look in the default vault directory, find nothing, and report a MISSING
    capture for a run that wrote correctly into `--out`. That is the same class
    of failure as the one this whole change is about: an instrument confidently
    describing a place nobody wrote to.
    """
    if explicit:
        return os.path.abspath(explicit)
    cfg = os.path.join(HERE, "movehook.cfg")
    try:
        with open(cfg, encoding="ascii", errors="replace") as fh:
            for line in fh:
                if line.startswith("out="):
                    val = line[4:].strip()
                    if val:
                        return os.path.abspath(val)
    except OSError:
        pass
    return default_outdir()


def status_state():
    """The DLL's own `state:` line, or None if it left no status file."""
    try:
        with open(STATUS, encoding="ascii", errors="replace") as fh:
            for line in fh:
                if line.startswith("state:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def run_finished():
    """Has the armed run already ended?

    Two independent witnesses, either sufficient: the DLL says so in its own
    status file, or there is no client left to be running it. Deliberately NOT
    decided by the presence of movehook.bin -- the periodic snapshot writes
    that file mid-run, so existence proves the path works, never that the run
    is over.
    """
    if (status_state() or "").startswith("finished"):
        return True
    try:
        return not autoinject.find_pid("Gw.exe")
    except Exception:
        return False


def report_status():
    """Print the DLL's own status file, if it left one.

    It is written BESIDE THE DLL rather than into the output directory, which
    is the point: when the configured output path is the broken thing, that is
    the one place still writable.
    """
    if not os.path.exists(STATUS):
        return False
    try:
        with open(STATUS, encoding="ascii", errors="replace") as fh:
            text = fh.read().strip()
    except OSError as exc:
        print(f"(movehook.status unreadable: {exc})")
        return False
    print("\n-- the DLL's own status --")
    for line in text.splitlines():
        print(f"  {line}")
    return True


def sites_stale(here=None, dll=None):
    """(stale, [reason lines]) -- was this DLL built against THIS sites.h?

    DECIDED BY CONTENT WHERE POSSIBLE. `build.ps1` writes the sha256 of the header
    it compiled against into `movehook.sites.sha256`; when that stamp is present it
    is the whole answer, and timestamps are ignored.

    MTIME WAS WRONG TWICE IN ONE SESSION and is only the fallback now. sites.h is
    git-managed and generated, so its mtime moves without its bytes changing:
    `gensites.py` rewriting a byte-identical header -- which RUN-R4.md's own
    preconditions ask the operator to do, as a check that looks read-only -- and git
    normalising line endings on commit both bump it. Both refused a DLL that was
    perfectly current, once in the middle of a live run.

    The real case this exists for is unaffected: a header regenerated while the old
    DLL is still LOCKED by a running client makes the build fail with LNK1104, the
    .dll on disk keeps the OLD site set, and arming it would capture one site list
    while every downstream reader assumed another.
    """
    here = here or HERE
    dll = dll or DLL
    hdr = os.path.join(here, "sites.h")
    stamp_path = os.path.join(here, "movehook.sites.sha256")
    if not os.path.isfile(hdr) or not os.path.isfile(dll):
        return False, []
    stamp = None
    if os.path.isfile(stamp_path):
        try:
            stamp = open(stamp_path, encoding="ascii").read().strip().lower()
        except OSError:
            stamp = None
    if stamp:
        import hashlib
        with open(hdr, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got == stamp:
            return False, []
        return True, [
            f"REFUSING: {os.path.basename(dll)} was built against a DIFFERENT "
            f"sites.h.",
            f"  sites.h now   sha256 {got[:16]}",
            f"  the DLL wants sha256 {stamp[:16]}",
        ]
    if os.path.getmtime(hdr) <= os.path.getmtime(dll) + 1:
        return False, []
    return True, [
        f"REFUSING: {os.path.basename(dll)} is OLDER than sites.h, so it may have "
        f"been built against a different site set.",
        "  sites.h  " + time.strftime("%H:%M:%S",
                                      time.localtime(os.path.getmtime(hdr))),
        "  the DLL  " + time.strftime("%H:%M:%S",
                                      time.localtime(os.path.getmtime(dll))),
        "  (no build stamp -- this DLL predates content checking, so this is an "
        "mtime",
        "   comparison and CAN be a false alarm; rebuilding stamps it and settles "
        "it.)",
    ]


def already_loaded(pid):
    """Is movehook.dll already in `pid`? None when it cannot be determined.

    Three-valued on purpose: a snapshot can fail for reasons that have nothing to do
    with the DLL, and refusing on 'unknown' would block a legitimate run while
    proceeding on 'unknown' would risk the double-arm. The caller decides, loudly.
    """
    try:
        import keytap
        keytap.module_base(pid, "movehook.dll")
        return True
    except Exception as ex:
        if "not in pid" in str(ex):
            return False
        return None


def verify_running_build(pid):
    """Every armed site's first byte must be ITS OWN SHAPE'S byte IN THE LIVE PROCESS.

    THE FAILURE THIS IS AGAINST IS A CRASH, not a wrong number, and it is the trap
    this repo has walked into three times in three files. `session.py --exe`
    defaults to the NEWEST build under `vault/run/` -- `sorted()[-1]` -- while every
    address in `content/movecode.toml` is build 38797. `gensites.py --check` reads
    the PINNED FILE and would say OK while a different build is the one running:
    it is checking the wrong artifact to catch this.

    Arming a 38797 RVA in a 38833 image does not miss politely. It writes 0xCC into
    whatever byte lives there, which is usually the middle of an instruction, and
    the client dies somewhere unrelated with our patch in it.

    So the same property `gensites.py` verifies against the file is verified here
    against the process we are about to inject. Returns ([], base) when every site
    agrees, or (reasons, base) when it must be refused.
    """
    import keytap
    import gensites
    sites, _offs, _coffs = gensites.rows()
    base = keytap.module_base(pid, "Gw.exe")
    bad = []
    for name in sorted(sites):
        rva = sites[name]["rva"]
        got = keytap.read_at(pid, base + rva, 1)
        # THE SHAPE'S BYTE, LOOKED UP RATHER THAN RESTATED. Since 2026-08-29 the
        # sites are not all `55 push ebp` -- the MapFindPath ret tap is `C3 ret`
        # -- and this check imports gensites' own map instead of hardcoding a
        # second copy. Q12(a) refuses two homes for one fact, and the failure
        # mode here is not subtle: a hardcoded 0x55 refuses every ret site and
        # the operator loses a session to a message naming the wrong problem.
        shape = sites[name].get("shape", gensites.DEFAULT_SHAPE)
        need = gensites.SHAPE_BYTE.get(shape)
        if not got:
            bad.append(f"{name}: could not read 0x{base + rva:08X} in the live "
                       f"process")
        elif need is None:
            bad.append(f"{name}: shape {shape!r} is not one movehook emulates "
                       f"({sorted(gensites.SHAPE_BYTE)})")
        elif got[0] != need:
            bad.append(f"{name}: rva 0x{rva:08X} holds 0x{got[0]:02X} in the "
                       f"running client, not the 0x{need:02X} that shape "
                       f"{shape!r} requires")
    return bad, base


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=10.0,
                    help="capture length; the DLL disarms and writes when it elapses")
    ap.add_argument("--out", default=None, help="output directory (default: the vault)")
    ap.add_argument("--image", default="Gw.exe")
    ap.add_argument("--force", action="store_true",
                    help="attach even if the DLL looks already loaded. Read the "
                         "docstring first -- this can leave a live 0xCC behind.")
    ap.add_argument("--stop", action="store_true",
                    help="end a run that is already armed, NOW. There is no Ctrl+C "
                         "for an injected DLL -- it runs on the client's threads "
                         "and this console has already exited -- so the stop is a "
                         "file the DLL polls. It disarms and writes immediately.")
    a = ap.parse_args(argv)

    if a.stop:
        stop = os.path.join(HERE, "movehook.stop")
        outdir = armed_outdir(a.out)
        binpath = os.path.join(outdir, "movehook.bin")
        print(f"looking for the capture in {outdir}")
        # A SECOND --stop ON A FINISHED RUN IS NOT A FAILURE, and the first
        # version of this said it was: it demanded a FRESH write, so running
        # --stop twice -- which the operator did, reasonably, on 2026-08-29 --
        # reported "NO CAPTURE APPEARED" about a complete 1 MB capture sitting
        # right there. Waiting for a new write is correct while a run is live
        # and nonsense once it has ended, so establish which case this is
        # BEFORE arming the wait.
        if run_finished() and os.path.exists(binpath):
            report_status()
            size = os.path.getsize(binpath)
            when = time.strftime("%H:%M:%S", time.localtime(
                os.path.getmtime(binpath)))
            print(f"\nthe run had ALREADY ENDED -- nothing to stop.")
            print(f"capture: {binpath}  ({size:,} bytes, written {when})")
            print("  python toolkit/clientscan/movehook/readhook.py "
                  f"--bin {binpath}")
            return 0
        before = os.path.getmtime(binpath) if os.path.exists(binpath) else None
        with open(stop, "w", encoding="ascii") as fh:
            fh.write("stop\n")
        print(f"wrote {stop}")
        # WAIT FOR THE FILE, DO NOT ANNOUNCE IT. This used to print "it will
        # disarm and write within a second" and exit, and on the R5 run that
        # sentence was false: the DLL never wrote, the operator believed the
        # capture existed, and it was gone by the time anyone looked. The
        # instrument has to prove the artifact.
        deadline = time.time() + 8.0
        wrote = False
        while time.time() < deadline:
            time.sleep(0.25)
            if os.path.exists(binpath):
                now = os.path.getmtime(binpath)
                if before is None or now > before:
                    wrote = True
                    break
            if not os.path.exists(stop) and os.path.exists(binpath):
                wrote = True                 # cleared the stop AND has a file
                break
        report_status()
        if wrote:
            size = os.path.getsize(binpath)
            print(f"capture written: {binpath}  ({size:,} bytes)")
            print("  python toolkit/clientscan/movehook/readhook.py "
                  f"--bin {binpath}")
            return 0
        print(f"\nNO CAPTURE APPEARED at {binpath} within 8 s.")
        if not autoinject.find_pid(a.image):
            print(f"  {a.image} is NOT running. A run only writes from a live "
                  f"process -- if it exited, the last periodic snapshot (every "
                  f"15 s) is what survives, and there is none here.")
        elif os.path.exists(stop):
            print("  the stop file was NOT consumed, so the DLL's poll loop is "
                  "not running: either nothing is injected into that process, "
                  "or its worker thread is gone. Check movehook.status above.")
        else:
            print("  the stop file WAS consumed but no file appeared -- the "
                  "write itself failed. movehook.status above names the error.")
        return 4

    if not os.path.isfile(DLL):
        return print(f"no DLL at {DLL} -- build it:\n"
                     f"  cd {HERE} && powershell -ExecutionPolicy Bypass "
                     f"-File ./build.ps1 movehook.c") or 2

    pid = autoinject.find_pid(a.image)
    if not pid:
        return print(f"no {a.image} is running. Launch the client and get the "
                     f"character into the world FIRST -- the capture window starts "
                     f"at injection, not at login.") or 2
    print(f"{a.image} pid {pid}")

    loaded = already_loaded(pid)
    if loaded and not a.force:
        return print("movehook.dll is ALREADY LOADED in that process. Refusing: a "
                     "second load arms every site twice and restores once, which "
                     "leaves a live 0xCC in the client after the run. Restart the "
                     "client, or pass --force if you know the first load already "
                     "disarmed.") or 3
    if loaded is None:
        print("  (could not determine whether it is already loaded -- proceeding; "
              "if this is a re-attach, restart the client instead)")

    # THE STALE-DLL CHECK. `gensites.py` can regenerate sites.h while the previous
    # DLL is still LOCKED by a running client (the hook is deliberately never
    # unloaded), so the build silently fails with LNK1104 and the .dll on disk keeps
    # the OLD site set. Arming that would capture 9 sites while the runsheet, the
    # rows and every downstream reader say 11 -- a confident wrong answer of exactly
    # the shape this directory keeps producing. Compare mtimes and refuse.
    stale, why = sites_stale()
    if stale:
        for line in why:
            print(line)
        print("")
        print("Rebuild it. If the build fails with LNK1104 the DLL is still loaded "
              "in a running")
        print("client -- close the client first; the hook does not unload itself.")
        print(f"  cd {HERE} && powershell -ExecutionPolicy Bypass "
              f"-File ./build.ps1 movehook.c")
        return 5

    # THE BUILD CHECK, against the running process and not against the pinned file.
    try:
        bad, base = verify_running_build(pid)
    except Exception as ex:
        print(f"cannot verify the running client's build: {ex}")
        print("Refusing rather than arming addresses that may not belong to this "
              "build. Every movehook address is 38797.")
        return 4
    if bad:
        print("REFUSING TO INJECT -- the running client is not the build these "
              "addresses were measured against:")
        for b in bad:
            print(f"  {b}")
        print("")
        print("Launch the 38797 build EXPLICITLY -- session.py defaults to the "
              "newest build under vault/run/, which is not this one:")
        print("  python toolkit/harness/session.py --exe "
              "vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900")
        return 4
    print(f"build check: every site reads its own shape's byte in the live "
          f"process (image base 0x{base:08X})")

    # THE CONFIG GOES IN A FILE, NOT THE ENVIRONMENT, and the difference is not
    # stylistic. `GetEnvironmentVariableA` inside the injected DLL reads the
    # CLIENT's environment -- inherited from whatever launched Gw.exe -- not this
    # process's. Setting os.environ here would change nothing and the DLL would
    # quietly use its defaults while the operator believed the run was bounded.
    # PROVE THE OUTPUT PATH BEFORE THE RUN, NOT AFTER IT. The R5 capture was
    # lost into a directory that never existed, and nothing said so until the
    # run was over and the client was closed. Eight minutes of the operator's
    # play is worth two syscalls up front. The DLL creates the directory too --
    # this is not redundant, it is the check that can still ABORT.
    outdir = os.path.abspath(a.out) if a.out else default_outdir()
    try:
        os.makedirs(outdir, exist_ok=True)
        probe = os.path.join(outdir, ".movehook-writable")
        with open(probe, "w", encoding="ascii") as fh:
            fh.write("ok\n")
        os.remove(probe)
    except OSError as exc:
        print(f"REFUSING TO INJECT -- cannot write the output directory:\n"
              f"  {outdir}\n  {exc}\n"
              f"Fix the path (or pass a different --out) before spending a run "
              f"on it.")
        return 6
    # A status file from a PREVIOUS run would be read as this one's.
    try:
        os.remove(STATUS)
    except OSError:
        pass

    cfg = os.path.join(HERE, "movehook.cfg")
    lines = [f"ms={int(a.minutes * 60_000)}", f"out={outdir}"]
    with open(cfg, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"config -> {cfg}")
    for ln in lines:
        print(f"  {ln}")

    rc = inject.main([str(pid), DLL])
    if rc:
        print("\ninjection FAILED. If the client is elevated, run this elevated too.")
        return rc
    import datetime
    ends = datetime.datetime.now() + datetime.timedelta(minutes=a.minutes)
    print(f"\narmed for {a.minutes:g} minute(s) -- ends at "
          f"{ends.strftime('%H:%M:%S')} unless you stop it sooner.")
    print("Walk the character: click across open ground, click where something is "
          "IN THE WAY (that is the case MOVECODE-P1a is about), walk on the "
          "keyboard, and stand still for a stretch.")
    print("")
    print("STOP EARLY when you have what you need -- there is no reason to stand "
          "around, and a long tail of a motionless character is dead weight in the "
          "capture:")
    print("  python toolkit/clientscan/movehook/attach.py --stop")
    print("")
    print(f"The capture lands at {os.path.join(outdir, 'movehook.bin')} -- and it "
          f"is now snapshotted every 15 s, so a client that exits or crashes "
          f"mid-run costs at most the last 15 seconds instead of the whole run. "
          f"--stop waits for the file and tells you if it did not appear.")
    print("")
    print("Then read it:")
    print(f"  python toolkit/clientscan/movehook/readhook.py --bin "
          f"{os.path.join(outdir, 'movehook.bin')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
