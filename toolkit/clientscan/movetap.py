#!/usr/bin/env python3
"""Watch the client's own movement solution while the operator plays.

    python toolkit/clientscan/movetap.py --selftest     # no client needed
    python toolkit/clientscan/movetap.py --seconds 120  # poll a running client

WHAT THIS IS FOR. Our server grants a click with GAME_SMSG 0x0029 and, seconds
later, the CLIENT teleports onto that destination -- 2,305 u in 0.23 s = 9,878
u/s, measured on the wire in run 20260819T135526. The wire cannot say WHY,
because everything that decides it happens inside the client between two
packets. This reads that decision out of the running process.

THE MECHANISM, read out of the pinned binary (build 38797, and see BUILDS
below). 0x0029's handler 0x005FD890 calls 0x00602A40, which writes the wire
point into BOTH m_segmentPoint (+0x88) and m_targetPoint (+0x9C), and calls
0x005FE950, which caches a velocity at +0xB0/+0xB4 and an arrival time at +0x48:

    m_timeStopMovement = m_timeUpdated + floor(dist * 1000 / (maxSpeed * moveSpeed))

in absolute milliseconds on the world clock. Until that instant the agent is
dead-reckoned. AT that instant -- and the compare at 0x006001EB is `time == +0x48`
EXACTLY, not `>=` -- the movement tick either glides again or TELEPORTS, chosen
by m_flags bit 18 (0x40000) at 0x0060029F. 0x00602A40 passes isWaypoint = 0
(push at 0x00602A7F), which CLEARS bit 18 at 0x005FEA49. **So every grant we
send arms the teleport branch and never the glide branch.**

WHAT THIS PROBE ASKS, and it is not the obvious question. The arrival formula,
applied to the flagship run's own numbers with no free parameter, predicts the
jump at t = 45.6 s. It happened at t = 40.1 s -- 5.4 s EARLY. Two readings
survive and nothing static can separate them:

    (A) +0x58 was stale, so the arrival time was computed from an old clock;
    (B) something client-side re-armed +0x48 after the grant.

So the record below is built around +0x48 and the world clock, NOT around the
position.

WHY NOT THE POSITION -- and this is the mistake this file exists to avoid.
+0x78 is not where the agent is. It is where the agent was at +0x58, advanced
only when 0x005FF880 runs, and that has 8 call sites, all event-driven, none per
frame. Across a PERFECTLY NORMAL glide the +0x78 trace is therefore: flat for
the whole leg, then one step onto the destination -- which is exactly what a
teleport looks like. A probe that watched +0x78 would have called every
ordinary click-to-move a teleport. The live position has to be reconstructed:

    live = (+0x78, +0x7C) + (+0xB0, +0xB4) * (now - +0x58) * 0.001

which is why every sample carries +0x58, the velocity and the world clock, and
why `--selftest` refuses to pass without them.

THE PREDICTION, stated before any run (toolkit/authsrv/probes.py's rule, applied
to a memory probe): at the moment a grant lands, +0x48 holds the exact
millisecond the jump will occur and +0x9C..+0xA8 holds the exact point it will
land on. So the observed lag must equal (+0x48 - world clock at grant), and NOT
any function of distance. REFUTED IF: +0x48 changes between the grant and the
jump (that names a re-armer, reading B), or the jump lands at a time that is
neither +0x48 nor any value +0x48 ever held (that means the tick was missed and
the agent reckoned past its destination, which is a third mechanism).

READ ONLY, by construction: PROCESS_VM_READ only, via toolkit/harness/keytap.py.
It never writes, never injects, never launches anything. Start a client with
`python toolkit/harness/session.py --keep-open` first.

BUILDS. The struct DISPLACEMENTS below are stable across builds 38519, 38797 and
38833 (measured: `fld [esi+0x9c]` sits at the same displacement in all three
while the code around it moved 0x3600). The ADDRESSES are not, and the two this
file dereferences -- _tls_index and the module base -- are the kind that do not
return a wrong number, they read whatever else is mapped. Hence the build gate
and the self-checks, which are the whole reason this file is longer than the
poll loop it contains.
"""
import argparse
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import keytap      # noqa: E402
import pinned      # noqa: E402
import vaultpath   # noqa: E402
import agentprobe  # noqa: E402  (gw_pids only -- its ARRAY is a DIFFERENT struct)

# The two absolute minimums, below which nothing is readable whatever the
# reader's rate: a run has to have lasted long enough for the phenomenon to
# occur and to hold enough samples to see it. Set from the shortest run in this
# arc that produced a real finding (60.8 s, 786 samples) with a wide margin --
# NOT from a guess, and deliberately far below it so this pair never becomes the
# binding constraint. The rate floor in main() is the one that does the work.
MIN_SPAN_SECONDS = 5.0
MIN_SAMPLES = 40

IMAGE_BASE = 0x00400000
# _tls_index. The PE TLS directory's AddressOfIndex reads 0x00C0F300, and
# 0x0047F660 -- the accessor every Agent-context read goes through -- is
# literally `mov ecx,[0xC0F300] / mov eax,fs:[0x2C] / mov eax,[eax+ecx*4] /
# mov eax,[eax+8] / ret`.
RVA_TLS_INDEX = 0x00C0F300 - IMAGE_BASE

# --- the Agent context, reached from the TLS block -------------------------
OFF_CTX_IN_TLS = 0x08      # [tls_block + 8] -> ctx        (0x0047F660)
OFF_AGBASE = 0x08          # [ctx + 8] -> AGBASE           (0x005FD8A1)
OFF_CHCLI = 0x44           # [ctx + 0x44] -> ChCli ctx     (0x0084DCB5)
OFF_CONTROLLED = 0x2AC     # [chcli + 0x2AC] -> agent ID   (0x0084DCB8)
OFF_SYNC_ARRAY = 0xE8      # [AGBASE + 0xE8] -> AgAgent*[] (0x005FD8CE)
OFF_SYNC_COUNT = 0xF0      # [AGBASE + 0xF0]               (0x005FD8B2, Array:587)
OFF_WORLD_STRIDE = 0x64    # imul eax,[esi+0x24],0x64      (0x005FF896)
OFF_WORLD_CLOCK = 0x148    # [AGBASE + world*0x64 + 0x148] (0x005FF89E)

# --- AgAgent displacements. Stable across 38519/38797/38833. ---------------
A_FLAGS = 0x20             # bit 17 IN_WORLD, bit 18 glide-vs-teleport, bit 19 STALE
A_WORLD = 0x24
A_STOP = 0x48              # m_timeStopMovement, absolute ms, 0 = not moving
A_UPDATED = 0x58           # m_timeUpdated -- the epoch m_point is dated to
A_MAXSPEED = 0x5C          # float, units/second
A_MOVESPEED = 0x60         # float multiplier, AGENT_MAX_MOVE_SPEED = 1.0
A_POINT = 0x78             # m_point   : x f, y f, plane i, w i
A_SEGMENT = 0x88           # m_segmentPoint (assert AgAgent:1143)
A_TARGET = 0x9C            # m_targetPoint  (assert AgAgent:1144) -- the landing point
A_VEL = 0xB0               # vx f, vy f, units/second
AGENT_SPAN = 0xD0          # every field above lies inside; do NOT extend blind

FLAG_IN_WORLD = 0x00020000
FLAG_GLIDE = 0x00040000    # SET = re-issue a timed move; CLEAR = teleport
FLAG_STALE = 0x00080000    # INTERNAL_FLAG_MOVEMENT_STALE (assert AgAgent:1198)
INVALID_POS = 0x7F800000   # +inf, AGENT_INVALID_POSITION


class TapFail(Exception):
    """Loud. Every failure here is 'we read the wrong thing', never a bad number."""


def u32(b, off=0):
    return struct.unpack_from("<I", b, off)[0]


def i32(b, off=0):
    return struct.unpack_from("<i", b, off)[0]


def f32(b, off=0):
    return struct.unpack_from("<f", b, off)[0]


# --------------------------------------------------------------------------
# The 32-bit TEB of a WOW64 target, read from 64-bit Python.
#
# THIS IS THE STEP MOST LIKELY TO BE SILENTLY WRONG, so it validates itself.
# NtQueryInformationThread(ThreadBasicInformation) hands back the SIXTY-FOUR bit
# TEB for a WOW64 thread; ThreadLocalStoragePointer at +0x2C belongs to the
# THIRTY-TWO bit TEB, which is a different structure living at a fixed offset
# after it. Using +0x2C on the 64-bit TEB reads an unrelated dword and every
# read after it is garbage that looks like data.
#
# The 32-bit TEB carries a self-pointer at +0x18 (NT_TIB.Self). Requiring it to
# equal the address we think we are reading is a check the artifact can refute,
# so a wrong WOW64_TEB_OFFSET fails here rather than three dereferences later.
# --------------------------------------------------------------------------
WOW64_TEB_OFFSET = 0x2000
TEB32_SELF = 0x18
TEB32_TLS_POINTER = 0x2C


def _threads_of(pid):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    TH32CS_SNAPTHREAD = 0x4

    class TE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ThreadID", wintypes.DWORD),
                    ("th32OwnerProcessID", wintypes.DWORD),
                    ("tpBasePri", ctypes.c_long),
                    ("tpDeltaPri", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD)]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    out, e = [], TE32()
    e.dwSize = ctypes.sizeof(TE32)
    if k32.Thread32First(snap, ctypes.byref(e)):
        while True:
            if e.th32OwnerProcessID == pid:
                out.append(e.th32ThreadID)
            if not k32.Thread32Next(snap, ctypes.byref(e)):
                break
    k32.CloseHandle(snap)
    return out


def _teb64_of(tid):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    THREAD_QUERY_INFORMATION = 0x0040

    class TBI(ctypes.Structure):
        _fields_ = [("ExitStatus", ctypes.c_long),
                    ("TebBaseAddress", ctypes.c_void_p),
                    ("UniqueProcessId", ctypes.c_void_p),
                    ("UniqueThreadId", ctypes.c_void_p),
                    ("AffinityMask", ctypes.c_void_p),
                    ("Priority", ctypes.c_long),
                    ("BasePriority", ctypes.c_long)]
    k32.OpenThread.restype = wintypes.HANDLE
    h = k32.OpenThread(THREAD_QUERY_INFORMATION, False, tid)
    if not h:
        return None
    try:
        tbi = TBI()
        n = ctypes.c_ulong(0)
        rc = ntdll.NtQueryInformationThread(h, 0, ctypes.byref(tbi),
                                            ctypes.sizeof(tbi), ctypes.byref(n))
        return None if rc else tbi.TebBaseAddress
    finally:
        k32.CloseHandle(h)


def tls_blocks(pid, handle, tls_index):
    """Every thread's TLS block for `tls_index`, with the TEB32 self-check.

    Returns [(tid, block_address)], validated. Empty is a hard failure upstream,
    never a quiet zero -- a probe that reads nothing must say so.
    """
    out = []
    for tid in _threads_of(pid):
        teb64 = _teb64_of(tid)
        if not teb64:
            continue
        teb32 = teb64 + WOW64_TEB_OFFSET
        raw = keytap.read_handle(handle, teb32 + TEB32_SELF, 4)
        if not raw or u32(raw) != (teb32 & 0xFFFFFFFF):
            continue          # not a WOW64 TEB32 at that offset -- skip, loudly upstream
        raw = keytap.read_handle(handle, teb32 + TEB32_TLS_POINTER, 4)
        if not raw or not u32(raw):
            continue
        slot = keytap.read_handle(handle, u32(raw) + tls_index * 4, 4)
        if not slot or not u32(slot):
            continue
        out.append((tid, u32(slot)))
    return out


def resolve(pid, handle, base, verbose=False):
    """(ctx, agbase, agent_id, agent_ptr). Raises TapFail with a reason.

    Re-resolved on EVERY poll on purpose. The agent array is ArenaNet's growable
    Array template -- its own bounds assert (Array:587) fires in this very
    lookup -- and array[id] is a heap object destroyed across map loads. A
    cached pointer would keep returning plausible numbers from freed memory.
    """
    raw = keytap.read_handle(handle, base + RVA_TLS_INDEX, 4)
    if not raw:
        raise TapFail("could not read _tls_index")
    tls_index = u32(raw)
    blocks = tls_blocks(pid, handle, tls_index)
    if not blocks:
        raise TapFail(
            "no thread yielded a TLS block. Either WOW64_TEB_OFFSET (0x2000) is "
            "wrong for this Windows build -- the TEB32 self-check at +0x18 "
            "rejected every thread -- or the process is not the 32-bit client.")
    for _tid, block in blocks:
        raw = keytap.read_handle(handle, block + OFF_CTX_IN_TLS, 4)
        if not raw or not u32(raw):
            continue
        ctx = u32(raw)
        raw = keytap.read_handle(handle, ctx + OFF_AGBASE, 4)
        if not raw or not u32(raw):
            continue
        agbase = u32(raw)
        cnt = keytap.read_handle(handle, agbase + OFF_SYNC_COUNT, 4)
        arr = keytap.read_handle(handle, agbase + OFF_SYNC_ARRAY, 4)
        if not cnt or not arr:
            continue
        count, array = u32(cnt), u32(arr)
        if not array or not (0 < count < 100000):
            continue
        raw = keytap.read_handle(handle, ctx + OFF_CHCLI, 4)
        if not raw or not u32(raw):
            continue
        raw = keytap.read_handle(handle, u32(raw) + OFF_CONTROLLED, 4)
        if not raw:
            continue
        aid = u32(raw)
        if aid == 0 or aid >= count or (aid & 0xF0000000):
            continue          # ChCliApi's own bound: !(id & 0xF0000000)
        raw = keytap.read_handle(handle, array + aid * 4, 4)
        if not raw or not u32(raw):
            continue
        if verbose:
            print(f"  ctx 0x{ctx:08X}  AGBASE 0x{agbase:08X}  array 0x{array:08X}"
                  f"  count {count}  controlled agent {aid}")
        return ctx, agbase, aid, u32(raw)
    raise TapFail("found TLS blocks but none resolved to an Agent context with a "
                  "controlled agent -- is the client actually in a map?")


def sample(handle, agbase, agent_ptr):
    """One agent snapshot plus the world clock it must be read against."""
    blk = keytap.read_handle(handle, agent_ptr, AGENT_SPAN)
    if not blk or len(blk) < AGENT_SPAN:
        return None
    world = i32(blk, A_WORLD)
    clk = keytap.read_handle(
        handle, agbase + world * OFF_WORLD_STRIDE + OFF_WORLD_CLOCK, 4)
    if not clk:
        return None
    now = i32(clk)
    flags = u32(blk, A_FLAGS)
    updated = i32(blk, A_UPDATED)
    vx, vy = f32(blk, A_VEL), f32(blk, A_VEL + 4)
    px, py = f32(blk, A_POINT), f32(blk, A_POINT + 4)
    # THE RECONSTRUCTION. m_point is dated to m_timeUpdated; the live position is
    # that plus the cached velocity over the elapsed milliseconds. Sampling
    # m_point alone is what would have made every ordinary glide look like a
    # teleport -- it only moves when 0x005FF880 runs, which is event-driven.
    dt = (now - updated) * 0.001
    return {
        "now": now, "stop": i32(blk, A_STOP), "updated": updated,
        "flags": flags,
        "in_world": bool(flags & FLAG_IN_WORLD),
        "glide": bool(flags & FLAG_GLIDE),
        "stale": bool(flags & FLAG_STALE),
        "maxspeed": round(f32(blk, A_MAXSPEED), 3),
        "movespeed": round(f32(blk, A_MOVESPEED), 4),
        "point": [round(px, 2), round(py, 2), i32(blk, A_POINT + 8)],
        "live": [round(px + vx * dt, 2), round(py + vy * dt, 2)],
        "segment": [round(f32(blk, A_SEGMENT), 2), round(f32(blk, A_SEGMENT + 4), 2),
                    i32(blk, A_SEGMENT + 8)],
        "target": [round(f32(blk, A_TARGET), 2), round(f32(blk, A_TARGET + 4), 2),
                   i32(blk, A_TARGET + 8)],
        "target_invalid": u32(blk, A_TARGET) == INVALID_POS,
        "vel": [round(vx, 2), round(vy, 2)],
    }


def selftest():
    """Everything that can be checked without a client. Exits non-zero on any gap."""
    bad = 0
    print("movetap selftest -- no client required\n")
    print("1. the reconstruction is present, because sampling m_point alone")
    print("   would call every ordinary glide a teleport")
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    for need, why in (
            ('"updated"', "m_timeUpdated -- the epoch m_point is dated to"),
            ('"now"', "the world clock, the only shared time base"),
            ('"live"', "the reconstructed position"),
            ("vx * dt", "the actual integration"),
            ('"glide"', "m_flags bit 18 -- which decides teleport vs glide"),
            ('"stop"', "m_timeStopMovement -- the whole question")):
        ok = need in src
        bad += not ok
        print(f"   [{'PASS' if ok else 'FAIL'}] {need:14} {why}")
    print("\n2. the TEB32 walk validates itself rather than trusting 0x2000")
    ok = "TEB32_SELF" in src and "!= (teb32 & 0xFFFFFFFF)" in src
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] the self-pointer check is present -- a wrong "
          f"WOW64_TEB_OFFSET must fail here, not three dereferences later")
    print("\n3. we do NOT reuse agentprobe's array, which is a different struct")
    # Asked of the SYNTAX TREE, not of a grep. A grep for the forbidden name
    # matches the grep's OWN literal -- the first draft of this check failed
    # itself for exactly that reason, which is a check that cannot pass, the
    # mirror of a check that cannot fail.
    import ast
    used = {n.attr for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == "agentprobe"}
    ok = used == {"gw_pids"}
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] agentprobe is used for {sorted(used)} and "
          f"nothing else. AgentView's +0x9C is the 0xDB type tag while AgAgent's "
          f"+0x9C is m_targetPoint.x, so resolving an agent through agentprobe's "
          f"array would pass a CHARACTER check on the wrong object")
    print("\n4. a client is present?")
    pids = agentprobe.gw_pids()
    print(f"   {'yes, pid(s) ' + str(pids) if pids else 'no Gw.exe running -- '
          'start one with session.py --keep-open to go further'}")
    print("\nselftest " + ("FAILED" if bad else "passed"))
    return 1 if bad else 0


def calibrate(handle, agbase, ptr, reads=40):
    """How fast can this reader ACTUALLY sample? Measured, before the run.

    WHY THIS EXISTS. The floor used to be `seconds * hz * 0.5` -- half the
    REQUESTED rate. But a full sample is one resolve plus ~20 cross-process
    ReadProcessMemory calls, and on the owner's machine that sustains about
    13 Hz against a default request of 50. So the floor could not be met by a
    healthy run at the default flags, and run 20260819T171436 duly printed FAIL
    over 786 samples that contained 304 re-arms, 7 arrivals and the measurement
    that overturned this arc's mechanism. A floor that fires on every good run
    is worse than no floor: it is how a REAL failure gets waved through.

    The fix must not be "compute the floor from the achieved rate" -- that is
    circular and could never fail, which is the other half of the same rule.
    So capability is measured HERE, before the run, and the floor is set from
    it. A run that then samples at half its own demonstrated capability really
    did stall, and that is a finding.
    """
    t0 = time.perf_counter()
    got = 0
    for _ in range(reads):
        if sample(handle, agbase, ptr) is not None:
            got += 1
    dt = time.perf_counter() - t0
    if dt <= 0 or got == 0:
        return None
    return got / dt


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--hz", type=float, default=50.0)
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--any-build", action="store_true",
                    help="read a build the pin does not recognise. The struct "
                         "displacements are stable across 38519/38797/38833 but "
                         "_tls_index's ADDRESS is not.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    pids = [a.pid] if a.pid else agentprobe.gw_pids()
    if not pids:
        print("no Gw.exe running. Start one: python toolkit/harness/session.py "
              "--keep-open")
        return 2
    pid = pids[-1]
    base, path = keytap.module_info(pid, "Gw.exe")
    pinned.assert_build(path, why=f"reading the movement model out of pid {pid}",
                        allow_any=a.any_build)

    print("PREDICTION, stated before the run and not after it:")
    print("  When a grant lands, +0x48 (m_timeStopMovement) holds the exact")
    print("  millisecond the jump will occur and m_targetPoint holds the exact")
    print("  point it will land on, so the observed lag must equal")
    print("  (+0x48 - the world clock at grant) and NOT any function of distance.")
    print("REFUTED IF: +0x48 changes between the grant and the jump (that names a")
    print("  re-armer), or the jump lands at a time +0x48 never held (the tick was")
    print("  missed and the agent reckoned past its destination).\n")

    out_dir = vaultpath.vault_path("captures", "movetap")
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    out = os.path.join(out_dir, f"movetap-{stamp}.jsonl")
    handle = keytap.open_read(pid)
    n = 0
    changes = 0
    last = None
    interrupted = False
    t_start = time.time()
    t_end = t_start + a.seconds
    period = 1.0 / a.hz
    try:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": "head", "pid": pid, "exe": path,
                                 "hz": a.hz, "wall": stamp}) + "\n")
            _ctx, agbase, aid, ptr = resolve(pid, handle, base, verbose=True)
            cap_hz = calibrate(handle, agbase, ptr)
            target_hz = a.hz if cap_hz is None else min(a.hz, cap_hz)
            if cap_hz is None:
                print("could not calibrate the reader; floor falls back to the "
                      "requested rate")
            else:
                print(f"reader capability {cap_hz:.1f} Hz (measured, 40 reads)"
                      + (f" -- BELOW the requested {a.hz:.0f} Hz, so the floor "
                         f"is set from {target_hz:.1f}"
                         if cap_hz < a.hz * 0.95 else ""))
            print(f"polling agent {aid} at {a.hz:.0f} Hz for {a.seconds:.0f}s "
                  f"-> {out}\n")
            while time.time() < t_end:
                try:
                    _ctx, agbase, aid, ptr = resolve(pid, handle, base)
                except TapFail:
                    time.sleep(period)
                    continue
                s = sample(handle, agbase, ptr)
                if s is None:
                    time.sleep(period)
                    continue
                s["kind"] = "sample"
                s["t"] = round(time.time(), 4)
                s["agent"] = aid
                fh.write(json.dumps(s) + "\n")
                n += 1
                # Print only what a human needs to see live: the arrival time
                # changing is the entire experiment.
                if last is not None and s["stop"] != last["stop"]:
                    changes += 1
                    d = s["stop"] - s["now"]
                    print(f"  +0x48 {last['stop']} -> {s['stop']} "
                          f"({'due in %.2fs' % (d / 1000.0) if s['stop'] else 'CLEARED'})"
                          f"  target {s['target'][:2]} glide={s['glide']}")
                last = s
                time.sleep(period)
    except KeyboardInterrupt:
        # Ctrl+C IS THE NORMAL WAY TO END A RUN. The operator stops when the
        # thing they were reproducing has happened, which is usually before
        # --seconds elapses. This used to escape as a traceback, so the summary
        # and the floor verdict never printed and the operator was left holding
        # a file with no idea whether it measured anything.
        interrupted = True
        print("\n  (interrupted -- scoring what was captured)")
    finally:
        import ctypes
        ctypes.WinDLL("kernel32").CloseHandle(handle)

    elapsed = max(1e-9, time.time() - t_start)
    rate = n / elapsed
    print(f"\n{n} samples over {elapsed:.1f}s = {rate:.1f} Hz, "
          f"{changes} change(s) to +0x48 -> {out}")
    if interrupted:
        print(f"  stopped early: {elapsed:.1f}s of the {a.seconds:.0f}s "
              f"requested. That is not a failure -- the floor below is scored "
              f"against the time actually run.")
    # A RUN THAT MEASURED NOTHING FAILED. Two things can make that true and they
    # are different: the poller never resolved an agent / sampled a handful of
    # times, or it ran for no time at all. Score them separately, and score the
    # rate against what this reader DEMONSTRATED it can do rather than against
    # what was asked for -- see calibrate().
    floor = int(elapsed * target_hz * 0.5)
    if elapsed < MIN_SPAN_SECONDS or n < MIN_SAMPLES:
        print(f"FAIL: {n} samples over {elapsed:.1f}s is too little to read "
              f"anything from (need {MIN_SAMPLES} samples and "
              f"{MIN_SPAN_SECONDS:.0f}s). This run measured nothing.")
        return 1
    if n < floor:
        print(f"FAIL: {n} samples is below the floor of {floor} -- half of "
              f"{target_hz:.1f} Hz over {elapsed:.1f}s, and this reader "
              f"measured itself at {target_hz:.1f} Hz before the run. It "
              f"stalled; do not read a null out of it.")
        return 1
    print(f"  floor {floor} met ({n} samples at half of {target_hz:.1f} Hz "
          f"over {elapsed:.1f}s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
