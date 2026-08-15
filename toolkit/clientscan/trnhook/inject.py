"""Load `trnhook.dll` into a running 32-bit client. Read-only in intent.

`LoadLibraryA` cannot be taken from OUR address space: this interpreter is
64-bit and the client is WOW64, so their `kernel32` bases differ and ours is
the wrong image entirely. The address is therefore resolved out of the
TARGET's own 32-bit `kernel32` by walking its export directory through
`ReadProcessMemory` -- the same primitive `keytap.py` already uses.

Usage: inject.py <pid> [dll]
"""
import ctypes
import os
import struct
import sys
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import keytap  # noqa: E402

PROCESS_ALL = 0x1F0FFF
MEM_COMMIT_RESERVE = 0x3000
PAGE_READWRITE = 0x04
k32 = ctypes.windll.kernel32


def export_rva(pid, module, name):
    """The RVA of `name` in the target's own copy of `module`."""
    base = keytap.module_base(pid, module)
    if not base:
        raise SystemExit(f"{module} not found in pid {pid}")
    hdr = keytap.read_at(pid, base, 0x400)
    pe = struct.unpack_from("<I", hdr, 0x3C)[0]
    magic = struct.unpack_from("<H", hdr, pe + 0x18)[0]
    if magic != 0x10B:
        raise SystemExit(f"{module} in pid {pid} is not PE32 (magic {magic:#x});"
                         f" the target must be 32-bit")
    dd = pe + 0x18 + 0x60                      # PE32 data directory
    exp_rva, exp_size = struct.unpack_from("<II", hdr, dd)
    exp = keytap.read_at(pid, base + exp_rva, max(exp_size, 0x1000))
    n_names, names_rva, ords_rva, funcs_rva = (
        struct.unpack_from("<I", exp, 0x18)[0],
        struct.unpack_from("<I", exp, 0x20)[0],
        struct.unpack_from("<I", exp, 0x24)[0],
        struct.unpack_from("<I", exp, 0x1C)[0])
    names = keytap.read_at(pid, base + names_rva, 4 * n_names)
    want = name.encode()
    for i in range(n_names):
        nrva = struct.unpack_from("<I", names, 4 * i)[0]
        s = keytap.read_at(pid, base + nrva, 64)
        if s.split(b"\0", 1)[0] == want:
            o = struct.unpack_from(
                "<H", keytap.read_at(pid, base + ords_rva + 2 * i, 2), 0)[0]
            f = struct.unpack_from(
                "<I", keytap.read_at(pid, base + funcs_rva + 4 * o, 4), 0)[0]
            return base, f
    raise SystemExit(f"{name} not exported by {module}")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    pid = int(argv[0])
    dll = os.path.abspath(argv[1] if len(argv) > 1
                          else os.path.join(HERE, "trnhook.dll"))
    if not os.path.exists(dll):
        raise SystemExit(f"no DLL at {dll} -- run build.ps1")

    base, rva = export_rva(pid, "KERNEL32.DLL", "LoadLibraryA")
    loadlib = base + rva
    print(f"target kernel32 0x{base:08X}, LoadLibraryA 0x{loadlib:08X}")

    h = k32.OpenProcess(PROCESS_ALL, False, pid)
    if not h:
        raise SystemExit(f"OpenProcess failed: {ctypes.GetLastError()} "
                         f"(the client may be elevated; run this elevated too)")
    buf = dll.encode() + b"\0"
    k32.VirtualAllocEx.restype = ctypes.c_void_p
    remote = k32.VirtualAllocEx(h, None, len(buf), MEM_COMMIT_RESERVE,
                                PAGE_READWRITE)
    if not remote:
        raise SystemExit(f"VirtualAllocEx failed: {ctypes.GetLastError()}")
    written = ctypes.c_size_t(0)
    if not k32.WriteProcessMemory(h, ctypes.c_void_p(remote), buf, len(buf),
                                  ctypes.byref(written)):
        raise SystemExit(f"WriteProcessMemory failed: {ctypes.GetLastError()}")

    tid = wintypes.DWORD(0)
    th = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(loadlib),
                                ctypes.c_void_p(remote), 0, ctypes.byref(tid))
    if not th:
        raise SystemExit(f"CreateRemoteThread failed: {ctypes.GetLastError()}")
    print(f"remote LoadLibraryA thread {tid.value} started; waiting")
    k32.WaitForSingleObject(th, 30000)
    code = wintypes.DWORD(0)
    k32.GetExitCodeThread(th, ctypes.byref(code))
    print(f"LoadLibraryA returned 0x{code.value:08X} "
          f"({'loaded' if code.value else 'FAILED'})")
    return 0 if code.value else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
