"""Read a value out of a running client's memory, fail-closed, under ASLR.

The key half of the R0b live-capture driver (route C, studies/livekey/CAPTURE.md): the
ciphertext is captured off the wire, and the 20-byte session key material is read from the
client process here. This module is only the READER -- OpenProcess + ReadProcessMemory,
with the runtime module base resolved from the toolhelp module list because the client
ships with ASLR on (MEASURED: DYNAMIC_BASE + a real .reloc), so a fixed image_base+RVA is
wrong every run and every address must be `runtime_base + RVA`.

WHAT IT DELIBERATELY IS NOT. It does not decide WHERE the key lives, or write anything into
the client. Locating the tap (a duplicate-store to a BSS slot behind a small code cave, or
a pointer chain to the persistent RC4 S-box at conn+0x7C) is static-analysis work tracked
in studies/livekey/. The honest correction to CAPTURE.md's "duplicate-store, no new code":
adding a store is new code -- a small code cave -- so the key tap is not the same
zero-new-code edit the DH/updater/mutex patches are. This reader works against whichever
tap wins, by RVA into a named module or by absolute address.

VERIFIABLE WITHOUT A LIVE RUN. Its correctness is the RPM machinery, not the game: the test
reads a known marker out of a process this machine controls, resolves a real module base
cross-process, and confirms an unmapped read fails cleanly. On loopback, once a tap exists,
the value it reads is checkable against the master_secret we independently derive
(toolkit/authsrv/replay.py) -- a live session is only the final confirmation.

Windows only, standard library only (ctypes). Read-only: PROCESS_VM_READ, never WRITE.
"""
import ctypes
import os
import sys
from ctypes import wintypes

# Read + query only. No PROCESS_VM_WRITE, no PROCESS_VM_OPERATION -- this module cannot
# modify the target by construction, which is the property that lets it run against a live
# client without being an instrument of change.
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010  # the 32-bit modules of a WOW64 target, read from 64-bit
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
MAX_MODULE_NAME32 = 255
MAX_PATH = 260

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * (MAX_MODULE_NAME32 + 1)),
        ("szExePath", wintypes.WCHAR * MAX_PATH),
    ]


kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32FirstW.restype = wintypes.BOOL
kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32NextW.restype = wintypes.BOOL


class TapError(Exception):
    """A read could not be made. Never returns a half-value or a guess."""


def open_read(pid):
    """A read-only handle to `pid`, or raise. Caller closes it (or use read_at)."""
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, int(pid))
    if not h:
        raise TapError(f"OpenProcess({pid}) failed: WinError {ctypes.get_last_error()} "
                       f"(is the pid right, and does this shell have access to it?)")
    return h


def read_handle(handle, address, size):
    """`size` bytes at `address` in the process `handle` refers to. None on failure.

    None rather than a raise, because a caller polling for a value that is not written yet
    (a BSS slot still zero, a stack slot already gone) expects to retry, not to crash. A
    hard failure -- bad handle -- is the caller's to notice via the following reads.
    """
    buf = (ctypes.c_char * size)()
    got = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address),
                                    buf, size, ctypes.byref(got))
    if not ok or got.value != size:
        return None
    return bytes(buf)


def read_at(pid, address, size):
    """Open, read `size` bytes at absolute `address`, close. None if the read failed."""
    h = open_read(pid)
    try:
        return read_handle(h, address, size)
    finally:
        kernel32.CloseHandle(h)


def module_base(pid, module_name):
    """The runtime load address of `module_name` in `pid`, or raise.

    Resolved every call, never cached: ASLR moves it per launch, and a stale base is the
    exact failure this module exists to avoid. Matches case-insensitively on the leaf name
    (e.g. "Gw.exe"), and snapshots both the native and the WOW64 (32-bit) module lists so a
    64-bit reader can locate a 32-bit client's modules.
    """
    want = os.path.basename(str(module_name)).lower()
    snap = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, int(pid))
    if snap == INVALID_HANDLE_VALUE or not snap:
        raise TapError(f"module snapshot of pid {pid} failed: "
                       f"WinError {ctypes.get_last_error()}")
    try:
        ent = MODULEENTRY32W()
        ent.dwSize = ctypes.sizeof(MODULEENTRY32W)
        ok = kernel32.Module32FirstW(snap, ctypes.byref(ent))
        seen = []
        while ok:
            name = ent.szModule
            seen.append(name)
            if name.lower() == want:
                return ent.modBaseAddr
            ok = kernel32.Module32NextW(snap, ctypes.byref(ent))
        raise TapError(f"module {module_name!r} not in pid {pid}; "
                       f"{len(seen)} modules present, e.g. {', '.join(seen[:6])}")
    finally:
        kernel32.CloseHandle(snap)


def read_rva(pid, module_name, rva, size):
    """`size` bytes at `module_base(module) + rva`. This is the ASLR-correct read.

    Returns bytes, or None if the read itself failed (module resolution failing is a raise,
    because it means the wrong process or a missing module, not a not-yet-written value).
    """
    base = module_base(pid, module_name)
    return read_at(pid, base + rva, size)


def _self_test_marker():
    """A buffer in THIS process, so a test can read a known value cross-call. Returns
    (address, bytes). Kept alive by the caller holding the returned buffer."""
    marker = bytes(range(0x40, 0x54))  # 20 distinctive bytes
    buf = ctypes.create_string_buffer(marker, len(marker))
    return ctypes.addressof(buf), marker, buf


def main():
    if len(sys.argv) < 4:
        print("read a value out of a running process (ASLR-correct)\n")
        print("  python toolkit/harness/keytap.py <pid> <module.exe> <rva-hex> [size=20]")
        print("  python toolkit/harness/keytap.py <pid> @<abs-hex> - [size=20]")
        return 2
    pid = int(sys.argv[1], 0)
    size = int(sys.argv[4], 0) if len(sys.argv) > 4 else 20
    mod = sys.argv[2]
    try:
        if mod.startswith("@"):
            data = read_at(pid, int(mod[1:], 16), size)
        else:
            data = read_rva(pid, mod, int(sys.argv[3], 16), size)
    except TapError as e:
        print(f"refused: {e}")
        return 1
    if data is None:
        print("read failed (address not mapped, or value not present yet)")
        return 1
    print(data.hex())
    return 0


if __name__ == "__main__":
    sys.exit(main())
