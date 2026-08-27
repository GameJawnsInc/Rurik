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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "harness"))

import autoinject                                              # noqa: E402
import inject                                                  # noqa: E402

DLL = os.path.join(HERE, "movehook.dll")


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
    """Every armed site's first byte must be 0x55 IN THE LIVE PROCESS.

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
    sites, _offs = gensites.rows()
    base = keytap.module_base(pid, "Gw.exe")
    bad = []
    for name in sorted(sites):
        rva = sites[name]["rva"]
        got = keytap.read_at(pid, base + rva, 1)
        if not got:
            bad.append(f"{name}: could not read 0x{base + rva:08X} in the live "
                       f"process")
        elif got[0] != 0x55:
            bad.append(f"{name}: rva 0x{rva:08X} holds 0x{got[0]:02X} in the "
                       f"running client, not 0x55 (push ebp)")
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
    a = ap.parse_args(argv)

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
    print(f"build check: every site reads 0x55 in the live process "
          f"(image base 0x{base:08X})")

    # THE CONFIG GOES IN A FILE, NOT THE ENVIRONMENT, and the difference is not
    # stylistic. `GetEnvironmentVariableA` inside the injected DLL reads the
    # CLIENT's environment -- inherited from whatever launched Gw.exe -- not this
    # process's. Setting os.environ here would change nothing and the DLL would
    # quietly use its defaults while the operator believed the run was bounded.
    cfg = os.path.join(HERE, "movehook.cfg")
    lines = [f"ms={int(a.minutes * 60_000)}"]
    if a.out:
        lines.append(f"out={os.path.abspath(a.out)}")
    with open(cfg, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"config -> {cfg}")
    for ln in lines:
        print(f"  {ln}")

    rc = inject.main([str(pid), DLL])
    if rc:
        print("\ninjection FAILED. If the client is elevated, run this elevated too.")
        return rc
    print(f"\narmed for {a.minutes:g} minute(s). Walk the character -- click across "
          f"open ground, click where something is IN THE WAY (that is the case "
          f"MOVECODE-P1a is about), walk on the keyboard, and stand still for a "
          f"stretch.\n"
          f"When it elapses the DLL disarms itself and writes. Then:\n"
          f"  python toolkit/clientscan/movehook/readhook.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
