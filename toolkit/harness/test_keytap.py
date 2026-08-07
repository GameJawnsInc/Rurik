"""Prove the ReadProcessMemory key reader works, without any game client.

keytap.py is the key half of the R0b live-capture driver, and it must be trustworthy
before it is ever pointed at a real client, because a wrong read there would silently
corrupt the one artifact this project cannot reproduce. Its correctness is the RPM
machinery -- OpenProcess, ReadProcessMemory, and ASLR-correct module-base resolution -- not
anything about Guild Wars, so it is tested against processes this machine already controls:

  1. read a known 20-byte marker back out of THIS process (RPM round-trips a value);
  2. resolve a real module's runtime base and read its MZ header (base resolution + read,
     the ASLR-correct path);
  3. do the same in a SEPARATE process we spawn (cross-process, the real configuration);
  4. an unmapped address fails cleanly -- None, not a crash, and not a wrong value.

A live loopback session later adds the confirmation that the bytes read equal the
master_secret we independently derive; that needs a launched client and is out of scope
here. This file is what lets the reader be trusted up to that point.

Windows only. If not on Windows, every section skips and the run is honestly empty.
"""
import ctypes
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import keytap  # noqa: E402

# Floor 5: the four capability checks plus the negative. All run on any Windows box with no
# fixture -- they read this interpreter's own memory and one child process, nothing vaulted.
LEDGER = checks.Ledger("keytap", floor=5)

IS_WINDOWS = sys.platform == "win32"


def main():
    if not IS_WINDOWS:
        LEDGER.skip("all", f"keytap is Windows-only; platform is {sys.platform}")
        return LEDGER.verdict()

    pid = os.getpid()

    # ---- 1. RPM round-trips a known value out of our own process ---------------
    print("1. ReadProcessMemory reads a known marker back out of this process")
    addr, marker, _keep = keytap._self_test_marker()
    got = keytap.read_at(pid, addr, len(marker))
    LEDGER.ok(got == marker,
              "the bytes read at the buffer's address equal the bytes written",
              f"wrote {marker.hex()}, read {got.hex() if got else None}")

    # ---- 2. ASLR-correct base resolution + read, in our own process ------------
    print("\n2. a module's runtime base resolves and reads as a PE ('MZ')")
    # The interpreter's own image is always present; resolve it by leaf name.
    exe_leaf = os.path.basename(sys.executable)
    try:
        base = keytap.module_base(pid, exe_leaf)
        resolved = True
    except keytap.TapError as e:
        base = None
        resolved = False
        detail = str(e)
    LEDGER.ok(resolved, f"module {exe_leaf!r} resolves to a runtime base",
              f"base 0x{base:x}" if resolved else detail)
    if resolved:
        head = keytap.read_rva(pid, exe_leaf, 0, 2)
        LEDGER.ok(head == b"MZ",
                  "base+0 reads the DOS 'MZ' signature -- base is a real image start",
                  f"read {head!r}")
    else:
        LEDGER.skip("self MZ", "module base did not resolve")

    # ---- 3. cross-process: the real configuration ------------------------------
    print("\n3. the same read works against a SEPARATE process we spawn")
    # A child that just waits, so it is alive while we read it. kernel32.dll is loaded in
    # every Win32 process at a base we must resolve per-process -- exactly the ASLR case.
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        # Give the loader a moment to map modules.
        deadline = time.monotonic() + 5
        kbase = None
        while time.monotonic() < deadline:
            try:
                kbase = keytap.module_base(child.pid, "kernel32.dll")
                break
            except keytap.TapError:
                pass
        LEDGER.ok(kbase is not None,
                  "kernel32.dll resolves in the child process",
                  f"child pid {child.pid}, base 0x{kbase:x}" if kbase else "did not resolve")
        if kbase is not None:
            head = keytap.read_at(child.pid, kbase, 2)
            LEDGER.ok(head == b"MZ",
                      "reading the child's kernel32 base returns 'MZ' cross-process",
                      f"read {head!r}")
        else:
            LEDGER.skip("cross-process read", "child kernel32 base did not resolve")
    finally:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()

    # ---- 4. an unmapped read fails cleanly, never a wrong value ----------------
    print("\n4. reading an unmapped address returns None, not a crash or a guess")
    # Address 0x10 is in the reserved null page of every Win32 process: never mapped.
    got = keytap.read_at(pid, 0x10, 20)
    LEDGER.ok(got is None,
              "a read of the reserved null page is refused with None",
              f"got {got!r} -- a non-None here would be memory we do not understand")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
