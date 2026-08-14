"""Read the equipped item's flags -- and bit 25 -- out of the running client.

    python toolkit/clientscan/itemprobe.py            # every item, bit 25 marked
    python toolkit/clientscan/itemprobe.py --dump 4   # + hex of the first four records

WHY. `studies/enemy/PLAN.md` §10.3 read the attack refusal down to one bit. For a
target whose allegiance is ENEMY, GmCoreAction's target classifier (0x005149A0)
switches through the table at 0x00514A60 onto 0x00514A1C, whose entire body is:

    00514A1C  call 0x5147f0
    00514A21  test eax, eax
    00514A23  je  0x514a56          ; -> mov eax, 1

and the caller SKIPS the target when the classifier returns nonzero. So the
target is offered when 0x005147F0 returns nonzero and withheld when it returns
zero -- and 0x005147F0 never looks at the target at all. It reads OUR OWN
equipment:

    005147FB  call 0x845890         ; ItCliApi:687  the inventory
    00514801  call 0x845470         ; ItCliApi:485  slot 0 of it
    0051480D  je  0x514838          ; NO ITEM        -> return 0
    0051480F  call 0x80d3e0
    00514815  call 0x80cee0         ; player-side predicate
    0051481F  jne 0x514838          ; PREDICATE SET  -> return 0
    00514822  call 0x8451e0         ; ItCliApi:400  the item record
    0051482A  mov eax, [eax + 0xc]
    0051482D  shr eax, 0x19
    00514830  and eax, 1            ; BIT 25

Three ways to be refused, all on our side of the interaction. §10.3's standing
instruction is to READ the bit before changing anything, because four earlier
sessions were spent adjusting the target instead. This is that read.

THE CHAIN, and every link is named by ArenaNet's own assert text:

    G  = *(*(fs:[0x2c])[ *0x00C0F300 ] + 8)     the per-thread client context
    M  = *(G + 0x40)                            ItCliApi's manager
    inv= *(M + 0xf8)   ; bag = *inv             ItCliApi:687 "inventory"
    obj= (*(M + 0xb8))[handle]                  ItCliApi:400, handle < *(M+0xc0)
    rec= obj + 0x1c                             what 0x8451e0 returns
    bit25 = (*(uint32 *)(rec + 0xc) >> 25) & 1  ==  *(uint32 *)(obj + 0x28)

WHY THIS WALKS THREADS. G lives in thread-local storage (`fs:[0x2c]`), not in a
global the way the agent array does, so there is no one address to read. Every
thread is tried and the ones that carry a usable context are reported -- with the
count of those that did not, because "one thread answered" and "every thread
answered" are different facts about the process.

THE 32-BIT TEB IS VERIFIED, NOT ASSUMED. NtQueryInformationThread hands a 64-bit
reader the 64-bit TEB of a WOW64 thread; the 32-bit TEB conventionally sits at
+0x2000. Rather than trust that, the 32-bit TEB's self-pointer at +0x18 is read
and must equal the address it was found at. A wrong guess would otherwise return
whatever lives there and every value below it would be fiction.

READ ONLY, by construction: keytap.open_read takes PROCESS_VM_READ and nothing
else, so this module cannot write to the client even by mistake. Start a client
with `python toolkit/harness/session.py --keep-open --hold 120` first.
"""
import argparse
import ctypes
import os
import struct
import sys
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import agentprobe  # noqa: E402   -- gw_pids()
import keytap  # noqa: E402
import pinned  # noqa: E402

IMAGE_BASE = 0x00400000
RVA_TLS_INDEX = 0x00C0F300 - IMAGE_BASE   # the dword 0x0047F660 indexes fs:[0x2c] with

OFF_CTX_IN_TLS_SLOT = 8       # 0x0047F660: mov eax, [eax + 8]
OFF_MANAGER = 0x40            # G + 0x40, shared by every ItCliApi accessor
OFF_INVENTORY = 0xF8          # M + 0xf8 -> "inventory" (ItCliApi:687)
OFF_ITEM_ARRAY = 0xB8         # M + 0xb8 -> handle-indexed object array
OFF_ITEM_COUNT = 0xC0         # M + 0xc0 -> its bound (ItCliApi:400)

OFF_RECORD = 0x1C             # 0x008451E0 returns obj + 0x1c
OFF_FLAGS_IN_RECORD = 0x0C    # 0x0051482A: mov eax, [eax + 0xc]
OFF_FLAGS = OFF_RECORD + OFF_FLAGS_IN_RECORD          # = 0x28 from the object
BIT_ATTACK_GATE = 25          # 0x0051482D: shr eax, 0x19 / and eax, 1

TEB32_FROM_TEB64 = 0x2000
OFF_TEB32_SELF = 0x18         # NT_TIB.Self -- the check that the +0x2000 guess held
OFF_TEB32_TLS = 0x2C          # ThreadLocalStoragePointer, which is what fs:[0x2c] IS

# The container hash map at M+0xd4, read out of 0x008445A0 rather than guessed.
# Its key is the bag handle 0x845890 returns; its value is the bag object whose
# slot array 0x0084AA50 indexes. Walking every bucket is used instead of
# replaying ArenaNet's hash (the jenkins-ish mix over the key's four bytes at
# 0x008445C0, table 0x0093D1A8) -- the answer is the same and a table walk
# cannot be wrong about the hash function.
OFF_MAP = 0xD4
OFF_MAP_HASHFIELD = 0x0C      # 0x00844621: mov ecx, [edi + 0xc]
OFF_MAP_BUCKETS = 0x10        # 0x00844607: mov eax, [edi + 0x10]
OFF_MAP_NBUCKETS = 0x18       # 0x008445EE: cmp ebx, [edi + 0x18]
BUCKET_STRIDE = 12            # 0x0084460A: lea ecx, [ebx + ebx*2] / [eax + ecx*4]
OFF_BUCKET_OBJ = 8            # 0x00844610: mov eax, [edx + 8]; low bit set = empty

OFF_BAG_SLOTS = 0x58          # 0x0084AA54: mov esi, [ecx + 0x58]
OFF_SLOTS_ARRAY = 0x18        # 0x0084AA7F: mov eax, [esi + 0x18]
OFF_SLOTS_COUNT = 0x20        # 0x0084AA66: cmp edi, [esi + 0x20]
EQUIP_SLOT_WEAPON = 0         # the slot 0x005147F8 pushes: `push 0`

TH32CS_SNAPTHREAD = 0x4
THREAD_QUERY_INFORMATION = 0x0040

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll", use_last_error=True)


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long),
                ("dwFlags", wintypes.DWORD)]


class THREAD_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("ExitStatus", ctypes.c_long), ("TebBaseAddress", ctypes.c_void_p),
                ("ClientId", ctypes.c_void_p * 2), ("AffinityMask", ctypes.c_void_p),
                ("Priority", ctypes.c_long), ("BasePriority", ctypes.c_long)]


def thread_ids(pid):
    """Every thread of `pid`, in enumeration order."""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    out = []
    e = THREADENTRY32()
    e.dwSize = ctypes.sizeof(THREADENTRY32)
    if kernel32.Thread32First(snap, ctypes.byref(e)):
        while True:
            if e.th32OwnerProcessID == pid:
                out.append(e.th32ThreadID)
            if not kernel32.Thread32Next(snap, ctypes.byref(e)):
                break
    kernel32.CloseHandle(snap)
    return out


def teb64(tid):
    """The 64-bit TEB address of `tid`, or None if it cannot be queried."""
    h = kernel32.OpenThread(THREAD_QUERY_INFORMATION, False, tid)
    if not h:
        return None
    try:
        tbi = THREAD_BASIC_INFORMATION()
        status = ntdll.NtQueryInformationThread(h, 0, ctypes.byref(tbi),
                                                ctypes.sizeof(tbi), None)
        if status != 0:
            return None
        return tbi.TebBaseAddress
    finally:
        kernel32.CloseHandle(h)


class Reader:
    """Reads held open across a whole walk, so one pointer chain is one handle."""

    def __init__(self, pid):
        self.pid = pid
        self.h = keytap.open_read(pid)

    def close(self):
        kernel32.CloseHandle(self.h)

    def raw(self, addr, size):
        return keytap.read_handle(self.h, addr, size)

    def u32(self, addr):
        b = self.raw(addr, 4)
        return None if b is None else struct.unpack("<I", b)[0]


def contexts(rd, tls_index):
    """Every distinct client context reachable from a thread of the process.

    Returns (list of context addresses, threads tried, threads whose 32-bit TEB
    could not be confirmed). The last number is reported rather than swallowed:
    a walk that silently examined two threads of forty is not a walk of the
    process.
    """
    found, unconfirmed = [], 0
    tids = thread_ids(rd.pid)
    for tid in tids:
        t64 = teb64(tid)
        if not t64:
            unconfirmed += 1
            continue
        t32 = t64 + TEB32_FROM_TEB64
        self_ptr = rd.u32(t32 + OFF_TEB32_SELF)
        if self_ptr != (t32 & 0xFFFFFFFF):
            unconfirmed += 1
            continue
        tls = rd.u32(t32 + OFF_TEB32_TLS)
        if not tls:
            continue
        slot = rd.u32(tls + tls_index * 4)
        if not slot:
            continue
        ctx = rd.u32(slot + OFF_CTX_IN_TLS_SLOT)
        if ctx and ctx not in found:
            found.append(ctx)
    return found, len(tids), unconfirmed


def items(rd, ctx):
    """(manager, bag handle, [(handle, obj, flags)]) for one context, or None."""
    man = rd.u32(ctx + OFF_MANAGER)
    if not man:
        return None
    arr = rd.u32(man + OFF_ITEM_ARRAY)
    count = rd.u32(man + OFF_ITEM_COUNT)
    if arr is None or count is None or not arr or count > 100000:
        return None
    inv = rd.u32(man + OFF_INVENTORY)
    bag = rd.u32(inv) if inv else None
    rows = []
    for h in range(count):
        obj = rd.u32(arr + h * 4)
        if not obj:
            continue
        flags = rd.u32(obj + OFF_FLAGS)
        if flags is None:
            continue
        rows.append((h, obj, flags))
    return man, bag, rows


def containers(rd, man):
    """Every bag in the manager's hash map: (key, object, [slot item ids]).

    The whole bucket array is walked rather than hashed into, so this reports
    what the map HOLDS. `0x005147F0` reaches exactly one of these -- the one
    whose key is `*(M+0xf8)` -- and asks for slot 0.
    """
    this = man + OFF_MAP
    buckets = rd.u32(this + OFF_MAP_BUCKETS)
    n = rd.u32(this + OFF_MAP_NBUCKETS)
    if not buckets or not n or n > 1 << 20:
        return None
    out = []
    for b in range(n):
        obj = rd.u32(buckets + b * BUCKET_STRIDE + OFF_BUCKET_OBJ)
        if not obj or obj & 1:
            continue
        key = rd.u32(obj)
        holder = rd.u32(obj + OFF_BAG_SLOTS)
        slots = []
        if holder:
            arr = rd.u32(holder + OFF_SLOTS_ARRAY)
            cnt = rd.u32(holder + OFF_SLOTS_COUNT)
            if arr and cnt is not None and cnt <= 256:
                for s in range(cnt):
                    ent = rd.u32(arr + s * 4)
                    slots.append(rd.u32(ent) if ent else None)
        out.append((key, obj, slots))
    return out


def hexdump(rd, addr, size, indent="    "):
    b = rd.raw(addr, size)
    if b is None:
        return indent + "(unreadable)"
    out = []
    for off in range(0, size, 16):
        chunk = b[off:off + 16]
        cols = " ".join(f"{c:02x}" for c in chunk)
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append(f"{indent}+0x{off:03X}  {cols:<47}  {txt}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, help="client pid; default = the running Gw.exe")
    ap.add_argument("--dump", type=int, default=0,
                    help="hex-dump this many item objects (0x60 bytes each)")
    ap.add_argument("--any-build", action="store_true",
                    help="read a client that is NOT the build RVA_TLS_INDEX was "
                         "measured on. The TLS walk below may then be following "
                         "unrelated memory; the run says so")
    a = ap.parse_args()

    pid = a.pid
    if pid is None:
        pids = agentprobe.gw_pids()
        if not pids:
            print("no Gw.exe is running -- start one with "
                  "`python toolkit/harness/session.py --keep-open --hold 120`")
            return 1
        pid = pids[-1]

    # The build gate, BEFORE the first read. `RVA_TLS_INDEX` was measured on one
    # build; against another it does not give a wrong TLS index, it gives an
    # arbitrary dword that the walk below then follows as if it were a pointer.
    # studies/crossbuild/FINDINGS.md §2.1.
    base, path = keytap.module_info(pid, "Gw.exe")
    what = pinned.assert_build(path, why=f"walking item memory in pid {pid}",
                               allow_any=a.any_build)
    if what not in ("pristine", "patched"):
        print(f"  !! --any-build: pid {pid} is running {path}, which is not a\n"
              f"     build {pinned.BUILD} copy we recorded. The walk below may be\n"
              f"     following unrelated memory.")
    rd = Reader(pid)
    try:
        tls_index = rd.u32(base + RVA_TLS_INDEX)
        print(f"pid {pid}  Gw.exe base 0x{base:08X}  TLS index {tls_index}")
        if tls_index is None or tls_index > 1088:
            print("  TLS index is not a plausible slot -- refusing to walk further")
            return 1

        ctxs, tried, unconfirmed = contexts(rd, tls_index)
        print(f"  {len(ctxs)} client context(s) from {tried} thread(s); "
              f"{unconfirmed} thread(s) had no confirmable 32-bit TEB")
        if not ctxs:
            print("  no thread carries the ItCliApi context -- is the client in a map?")
            return 1

        shown = 0
        for ctx in ctxs:
            got = items(rd, ctx)
            if got is None:
                continue
            man, bag, rows = got
            if not rows:
                continue
            shown += 1
            bagtxt = f"0x{bag:08X}" if bag else "(none)"
            print("")
            print(f"context 0x{ctx:08X}  manager 0x{man:08X}  "
                  f"inventory[0] (the bag handle slot 0 is looked up in) {bagtxt}")
            print("")
            print(f"{'handle':>6} {'object':>10}  {'+0x28 flags':>11}  bit 25")
            for h, obj, flags in rows:
                mark = "SET -- attackable" if flags & (1 << BIT_ATTACK_GATE) else "clear"
                print(f"{h:>6} 0x{obj:08X}  0x{flags:08X}  {mark}")

            set25 = [r for r in rows if r[2] & (1 << BIT_ATTACK_GATE)]
            print("")
            print(f"{len(set25)} of {len(rows)} items carry bit 25. The classifier "
                  f"offers an ENEMY target only when the item in EQUIP SLOT 0 has it; "
                  f"any other item having it is irrelevant to the gate.")

            # ---- the first branch: is slot 0 occupied at all? -----------------
            bags = containers(rd, man)
            print("")
            if bags is None:
                print("  the container map at M+0xd4 could not be read")
                continue
            print(f"  {len(bags)} bag(s) in the container map:")
            byflags = {h: f for h, _o, f in rows}
            for key, obj, slots in bags:
                used = [(s, i) for s, i in enumerate(slots) if i]
                mark = " <== the one the gate looks in" if key == bag else ""
                print(f"    key 0x{key:08X} at 0x{obj:08X}, {len(slots)} slot(s), "
                      f"{len(used)} filled: {used}{mark}")
            gatebag = next((b for b in bags if b[0] == bag), None)
            print("")
            if gatebag is None:
                print(f"  REFUSED AT BRANCH 1: no bag with key 0x{bag:08X} is in the "
                      f"map at all, so 0x845470 asserts and returns nothing.")
            elif len(gatebag[2]) <= EQUIP_SLOT_WEAPON or not gatebag[2][EQUIP_SLOT_WEAPON]:
                print(f"  REFUSED AT BRANCH 1: slot {EQUIP_SLOT_WEAPON} of that bag is "
                      f"EMPTY, so 0x005147F0 returns 0 before it ever reads a flag.")
            else:
                iid = gatebag[2][EQUIP_SLOT_WEAPON]
                fl = byflags.get(iid)
                ftxt = "unknown (that item id is not in the array)" if fl is None else (
                    f"0x{fl:08X}, bit 25 "
                    + ("SET" if fl & (1 << BIT_ATTACK_GATE) else "CLEAR"))
                print(f"  BRANCH 1 PASSES: slot {EQUIP_SLOT_WEAPON} holds item {iid}, "
                      f"whose gate dword is {ftxt}.")

            for h, obj, _f in rows[:a.dump]:
                print("")
                print(f"  item handle {h} at 0x{obj:08X} "
                      f"(record = +0x{OFF_RECORD:X}, gate dword at +0x{OFF_FLAGS:X}):")
                print(hexdump(rd, obj, 0x60))

        if not shown:
            print("  a context was found but its item manager held no items -- "
                  "the character may not be in a map yet")
            return 1
        return 0
    finally:
        rd.close()


if __name__ == "__main__":
    sys.exit(main())
