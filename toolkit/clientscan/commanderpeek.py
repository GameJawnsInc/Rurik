"""Read the live client's hero-commander state, to settle a question static reading cannot.

WHY THIS EXISTS. The party-window hero button asserts `commander` /
`GmView.cpp(5890)` because the commander container holds no entry for our
hero. Three static hypotheses for that have been refuted by experiment --
`inventoryId` (studies/heroes/FINDINGS.md 16), `msg+0x10` (19), and the
party-cache gate on the event raise (26). Each cost a client run to kill, and
each was a guess about a thing we could have MEASURED instead. This measures
it: after the instance loads, does a commander exist at all, and are the seven
slots populated?

WHAT IT READS, and every step of the chain is OBSERVED in the binary:

  [0x00C07850]            the GmHeroCommander context pointer, a static global
                          (`0x004E0B90` is `mov eax,[0xc07850]` + a non-null
                          assert, GmHeroCommander:70)
  ctx+0x20                the commander CONTAINER -- the thing `0x00524DB0`
                          looks up and asserts on
  ctx+0x30 .. ctx+0x4c    heroCommanderSlot[7], which hold KEYS into that
                          container, not the objects (25.1, and the bound is
                          asserted at GmHeroCommander:81/108/246)

READ-ONLY, and deliberately so: OpenProcess with
PROCESS_QUERY_INFORMATION|PROCESS_VM_READ through `keytap`, which is the same
pure-ctypes reader the live key capture uses. No breakpoint, no injection, no
write. A debugger would answer a sharper question (does the event FIRE) at the
cost of native tooling and the risk of freezing a client mid-run; this answers
the question that actually blocks the arc, for free.

    python toolkit/clientscan/commanderpeek.py            # find Gw.exe itself
    python toolkit/clientscan/commanderpeek.py --pid 1234

Standard library only.
"""
import argparse
import ctypes
import os
import struct
import sys
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import keytap  # noqa: E402

IMAGE_BASE = 0x00400000
CTX_GLOBAL_VA = 0x00C07850          # GmHeroCommander context pointer
CONTAINER_OFF = 0x20                # ctx+0x20, what 0x00524DB0 searches
SLOTS_OFF, SLOTS_N = 0x30, 7        # heroCommanderSlot[7]

# The UI event SUBSCRIBER MAP. 0x0064CA30 does `mov ecx, 0xc11bc4` -- the
# address IS the map object, not a pointer to one -- then looks the event id up
# through 0x00491F20 before calling any handler. So an event with no entry here
# is raised into nothing, which is a thing we can MEASURE rather than trace.
# Hash-map layout read from that lookup: buckets at +0x10, bucket count +0x18,
# mask +0x1c, 12-byte entries whose +8 is a state word (`test al,1` rejects).
EVENTMAP_VA = 0x00C11BC4
EVMAP_BUCKETS, EVMAP_COUNT = 0x10, 0x18


def find_client_pids():
    """Every running Gw.exe pid, via ToolHelp. Empty list if none."""
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        raise SystemExit("CreateToolhelp32Snapshot failed")
    out, e = [], PROCESSENTRY32()
    e.dwSize = ctypes.sizeof(PROCESSENTRY32)
    try:
        ok = k32.Process32First(snap, ctypes.byref(e))
        while ok:
            if e.szExeFile.decode("latin-1").lower() == "gw.exe":
                out.append(int(e.th32ProcessID))
            ok = k32.Process32Next(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return out


def peek(pid):
    """The commander context, its container header, and the seven slots."""
    rva = CTX_GLOBAL_VA - IMAGE_BASE
    ctx = struct.unpack("<I", keytap.read_rva(pid, "Gw.exe", rva, 4))[0]
    if ctx == 0:
        return {"ctx": 0}
    # An Array<T> header here is {ptr, capacity, count, alloc} -- the same shape
    # the attribState record's three arrays use (13), and the same one 0x01C2's
    # worker grows via 0x4739c0.
    ptr, cap, count, alloc = struct.unpack(
        "<4I", keytap.read_at(pid, ctx + CONTAINER_OFF, 16))
    slots = struct.unpack(
        "<%dI" % SLOTS_N, keytap.read_at(pid, ctx + SLOTS_OFF, SLOTS_N * 4))
    return {"ctx": ctx, "ptr": ptr, "cap": cap, "count": count,
            "alloc": alloc, "slots": slots}


def event_subscribers(pid, wanted):
    """{event_id: n} for `wanted` -- or None if the reader FAILS ITS CONTROL.

    THIS RETURNED A CONFIDENTLY WRONG ANSWER FIRST TIME AND THE CONTROL IS WHY
    IT NO LONGER CAN. The first version read the bucket array at map+0x10 as
    512 twelve-byte {key, value, state} rows and reported that 0x1000011E,
    0x10000114 AND 0x100001A4 all have NO SUBSCRIBER. That is refuted by
    behaviour we already had: 0x100001A4 demonstrably reaches its handler,
    because the party-window button raises it and the client asserts INSIDE
    case 125 (GmView:5890). A reader that says a known-live event is
    unsubscribed is broken, not surprising.

    Dumping the array confirmed it: all 512 slots non-empty, and NO
    event-id-shaped value at any of the three offsets. The map does not store
    raw ids in its buckets -- the lookup hashes through 0x004920B0 first, so
    the keys are hashed or held indirectly, and a walk cannot find them without
    replicating that hash.

    So the control is now the tool's own gate: 0x100001A4 MUST be found or this
    refuses to answer. `wanted` results are meaningless otherwise, and the one
    thing worse than no measurement here is a dramatic false one -- "the event
    has no subscriber" would have been exactly that.
    """
    CONTROL = 0x100001A4          # known live: it raises the GmView:5890 assert
    base = keytap.module_base(pid, "Gw.exe") - IMAGE_BASE
    hdr = keytap.read_at(pid, base + EVENTMAP_VA, 0x20)
    buckets = struct.unpack_from("<I", hdr, EVMAP_BUCKETS)[0]
    nbuckets = struct.unpack_from("<I", hdr, EVMAP_COUNT)[0]
    if not buckets or not (0 < nbuckets <= 1 << 20):
        return buckets, nbuckets, None
    raw = keytap.read_at(pid, buckets, nbuckets * 12)
    seen = {}
    for i in range(nbuckets):
        for v in struct.unpack_from("<3I", raw, i * 12):
            seen[v] = seen.get(v, 0) + 1
    if not seen.get(CONTROL):
        return buckets, nbuckets, None    # control absent -> reader is wrong
    return buckets, nbuckets, {w: seen.get(w, 0) for w in wanted}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--events", action="store_true",
                    help="also report whether the commander events have "
                         "SUBSCRIBERS: 0x1000011E (0x01C2's incremental path) "
                         "and 0x10000114 (the bulk activeHeroes scan). An "
                         "event with no entry is raised into nothing.")
    ap.add_argument("--pid", type=int, default=None,
                    help="client pid; omit to find Gw.exe automatically")
    a = ap.parse_args(argv)

    pids = [a.pid] if a.pid else find_client_pids()
    if not pids:
        raise SystemExit(
            "no Gw.exe is running. This reads a LIVE client -- start a session "
            "with --keep-open and run this during the hold.")
    if len(pids) > 1 and not a.pid:
        print(f"NOTE: {len(pids)} clients running {pids}; reading all of them. "
              f"Two clients is itself worth knowing about -- a stale one is how "
              f"a run measures the wrong process.")
    for pid in pids:
        print(f"\npid {pid}")
        try:
            s = peek(pid)
        except Exception as ex:
            print(f"  unreadable: {ex}")
            continue
        if not s["ctx"]:
            print("  commander context is NULL -- the UI module has not "
                  "initialised, so nothing below would mean anything")
            continue
        print(f"  ctx                 0x{s['ctx']:08X}")
        print(f"  container ctx+0x20  ptr=0x{s['ptr']:08X} cap={s['cap']} "
              f"count={s['count']} alloc={s['alloc']}")
        print(f"  heroCommanderSlot   {[hex(x) for x in s['slots']]}")
        # The whole point, stated so a reader cannot mistake which way it cuts.
        if a.events:
            try:
                bkt, n, hits = event_subscribers(pid, (0x1000011E, 0x10000114,
                                                       0x100001A4))
            except Exception as ex:
                print(f"  event map unreadable: {ex}")
            else:
                print(f"  event map           buckets=0x{(bkt or 0):08X} n={n}")
                if hits is None:
                    print("    READER FAILED ITS OWN CONTROL -- 0x100001A4 is "
                          "known live (it raises the GmView:5890 assert) and "
                          "was not found, so the bucket walk does not see the "
                          "real keys. NO SUBSCRIBER ANSWER IS GIVEN; the map "
                          "hashes through 0x004920B0 and needs that replicated.")
                else:
                    for ev, c in hits.items():
                        verdict = "SUBSCRIBED" if c else "NO SUBSCRIBER"
                        print(f"    0x{ev:08X}  {verdict} ({c} hit(s))")
        if s["count"] == 0:
            print("  => NO COMMANDER EXISTS. The click's resolver "
                  "(0x00524DB0) has nothing to find, which is exactly the "
                  "GmView:5890 assert. So the event never created one.")
        else:
            print(f"  => {s['count']} commander(s) EXIST. The container is "
                  f"populated, so the assert is NOT 'nothing was created' -- "
                  f"it is a KEY MISMATCH between what the button passes and "
                  f"what the slots hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
