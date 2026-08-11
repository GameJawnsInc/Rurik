"""Read a live agent's type tag and allegiance out of the running client.

    python toolkit/clientscan/agentprobe.py            # every agent in the array
    python toolkit/clientscan/agentprobe.py --agent 10

WHY. `studies/enemy/PLAN.md` section 10 read the refusal out of the binary: the
client offers no attack action against our agents, and the decision funnels
through ONE dword. Both agent lookups share the same array -- base at VA
0x00BF96CC, count at 0x00BF96D4 -- and differ only in the tail:

    0x00802140   bounds-check, return array[id]                  (any agent)
    0x00802160   bounds-check, load array[id], then
                   cmp [ecx+0x9c], 0xDB / setne al / dec eax / and eax, ecx

so the second returns the object only when `+0x9C == 0xDB` and NULL otherwise.
NULL makes the allegiance getter (0x007DF870) return **7**, and 7 fails the
`cmp eax,5 / ja` range check in GmCoreAction's available-actions builder, which
drops it to a mask with no attack in it.

Everything therefore reduces to a question a read can answer: what IS our agent's
+0x9C? This prints it, and the allegiance byte at +0x1B5 beside it, for whatever
is standing in the map right now.

READ ONLY, and by construction: it opens the client with PROCESS_VM_READ only
(keytap.open_read), never writes, never injects, never launches anything. The
client it reads is whichever Gw.exe is already running -- start one with
`session.py --keep-open` first.

WHY THE ADDRESSES ARE RVAs. The client relocates: three crash reports from one
evening carry BaseAddr 00340000, 00C80000 and 00340000 for the same binary. An
absolute VA read against a relocated image returns whatever happens to live
there, silently. Module base comes from the process at run time and the offsets
below are image-relative.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import keytap  # noqa: E402

IMAGE_BASE = 0x00400000
RVA_ARRAY = 0x00BF96CC - IMAGE_BASE
RVA_COUNT = 0x00BF96D4 - IMAGE_BASE

OFF_TYPE_TAG = 0x9C        # == 0xDB is what makes an agent a CHARACTER
OFF_ALLEGIANCE = 0x1B5     # 1..6; the six-arm switch; 3 is ALLEGIANCE_ENEMY
# The flags dword 0x007DF8A0 returns (AvApi:618 'agent'). GmCoreAction tests bit
# 0x10 on the TARGET at 0x005145A9 and SKIPS the whole allegiance switch if set --
# so a set bit here is as fatal to the attack action as a wrong type tag.
OFF_FLAGS = 0x13C
FLAG_SKIPS_ACTIONS = 0x10
TYPE_CHARACTER = 0xDB

ALLEGIANCE = {1: "ALLY_NONATTACKABLE", 2: "NEUTRAL", 3: "ENEMY",
              4: "SPIRIT_PET", 5: "MINION", 6: "NPC_MINIPET",
              7: "(none -- lookup MISS, out of the switch's 1..6 range)"}


def gw_pids():
    """Every running Gw.exe, newest last. Empty if none."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    TH32CS_SNAPPROCESS = 0x2

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = []
    e = PE32()
    e.dwSize = ctypes.sizeof(PE32)
    if k32.Process32First(snap, ctypes.byref(e)):
        while True:
            if e.szExeFile.decode("latin-1").lower() == "gw.exe":
                out.append(e.th32ProcessID)
            if not k32.Process32Next(snap, ctypes.byref(e)):
                break
    k32.CloseHandle(snap)
    return out


def u32(b):
    return struct.unpack("<I", b)[0]


def probe(pid, want=None, limit=64):
    base = keytap.module_base(pid, "Gw.exe")
    arr = u32(keytap.read_at(pid, base + RVA_ARRAY, 4))
    count = u32(keytap.read_at(pid, base + RVA_COUNT, 4))
    print(f"pid {pid}  Gw.exe base 0x{base:08X}")
    print(f"  agent array 0x{arr:08X}, count {count}")
    if not arr or count > 100000:
        print("  array looks unset -- is the client actually in a map?")
        return []

    rows = []
    ids = [want] if want is not None else range(min(count, limit))
    for aid in ids:
        if aid >= count:
            print(f"  agent {aid} is past the array count {count}")
            continue
        ptr = u32(keytap.read_at(pid, arr + aid * 4, 4))
        if not ptr:
            continue
        tag = u32(keytap.read_at(pid, ptr + OFF_TYPE_TAG, 4))
        alleg = keytap.read_at(pid, ptr + OFF_ALLEGIANCE, 1)[0]
        flags = u32(keytap.read_at(pid, ptr + OFF_FLAGS, 4))
        rows.append((aid, ptr, tag, alleg, flags))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, help="client pid; default = the running Gw.exe")
    ap.add_argument("--agent", type=int, help="one agent id, instead of a sweep")
    ap.add_argument("--limit", type=int, default=64)
    a = ap.parse_args()

    pid = a.pid
    if pid is None:
        pids = gw_pids()
        if not pids:
            print("no Gw.exe is running -- start one with "
                  "`python toolkit/harness/session.py --keep-open --hold 120`")
            return 1
        pid = pids[-1]

    rows = probe(pid, a.agent, a.limit)
    if not rows:
        return 1
    header = (f"{'agent':>6} {'+0x9C':>10} {'char?':<6} {'+0x1B5':>6} "
              f"{'allegiance':<20} {'+0x13C flags':>12}  bit 0x10")
    print("")
    print(header)
    for aid, ptr, tag, alleg, flags in rows:
        is_char = "yes" if tag == TYPE_CHARACTER else "NO"
        blocked = "SET -- BLOCKS" if flags & FLAG_SKIPS_ACTIONS else "clear"
        print(f"{aid:>6} 0x{tag:08X} {is_char:<6} {alleg:>6} "
              f"{ALLEGIANCE.get(alleg, '?')[:20]:<20} 0x{flags:08X}  {blocked}")
    bad = [r for r in rows if r[2] != TYPE_CHARACTER]
    flagged = [r for r in rows if r[4] & FLAG_SKIPS_ACTIONS]
    print("")
    if flagged:
        print(f"{len(flagged)} agent(s) carry +0x13C bit 0x10, which makes "
              f"GmCoreAction skip the allegiance switch entirely -- as fatal to "
              f"the attack action as a wrong type tag.")
    print(f"{len(rows) - len(bad)} of {len(rows)} agents carry the CHARACTER tag "
          f"0x{TYPE_CHARACTER:X}.")
    if bad:
        print("Agents WITHOUT it cannot be attacked: 0x00802160 returns NULL for "
              "them, the allegiance getter falls to 7, and 7 is outside the "
              "1..6 the action switch accepts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
