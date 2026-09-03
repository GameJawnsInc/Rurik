#!/usr/bin/env python3
"""Poll BOTH client copies of chosen agents while a session runs (ANIMREF-RE 40.11).

    python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 60
    python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 60 --out vault/research/animref/agenttap.jsonl

WHY. Three CASE 8 runs in a row put the SERVER's copy of the Hatcher at exactly
80 u from a standing player and the operator saw the swing "from long range",
then, once the halt waited for retail's half-second clock, "warping into my
body". The wire cannot see an NPC's rendered position -- the client never sends
it -- so every fix so far steered around a body nobody had measured. This reads
it out of the running client: for each agent id, the SYNC copy (world 0,
`[[AGBASE+0xE8] + id*4]`, the one 0x0029/0x002A/0x0028 write) and the ASYNC
copy (world 1, `[[AGBASE+0x14C] + id*4]`, the one that is drawn), with the
fields the collision resolver and the movement tick read:

    +0x20 m_flags (bit 0/1 the resolver tests, bit 17 IN_WORLD, 18 glide, 19 stale)
    +0x48 m_timeStopMovement (0 = parked)      +0x58 m_timeUpdated
    +0x5C maxSpeed  +0x60 moveSpeed            +0x78 m_point (x, y)
    +0x88 m_segmentPoint  +0x9C m_targetPoint  +0xB0 velocity
    +0x98 the followed agent (0x002A's fifth field; 0 = none)

Every displacement is movetap.py's, read from the pinned build with codescan and
re-checked by movetap --selftest; this file adds only the +0x98 read, which
ANIMREF-RE 38.2 located (0x00602AA8, the shared setter's third argument).

WHAT IT ANSWERS, stated before the run: with the player standing still and the
Hatcher walking in, (1) does the SYNC copy's +0x48 clear (park) at ~80 u from the
player on its own, before our 0x0028 lands, or does it walk to the player's point;
(2) where is the ASYNC copy when the SYNC copy parks or the halt lands -- how far
behind; (3) is +0x98 the player's id on the Hatcher's sync copy while it follows;
(4) what m_flags bits 0/1 read on both agents. The resolver (0x006011F0) parks a
follower only if both agents carry bit 0 and the follower is moving.

Read-only, loopback client only, pinned build (--any-build to override). Stdlib +
keytap's ctypes; no third-party module. Polls at --hz (default 30) and writes one
JSON line per sample; prints a summary at the end.
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, os.path.join(HERE, ".."))

import keytap        # noqa: E402
import agentprobe    # noqa: E402
import movetap       # noqa: E402
from movetap import (u32, i32, f32, resolve, TapFail, OFF_SYNC_ARRAY,   # noqa: E402
                     OFF_SYNC_COUNT, OFF_ASYNC_ARRAY, OFF_ASYNC_COUNT,
                     OFF_WORLD_STRIDE, OFF_WORLD_CLOCK, AGENT_SPAN,
                     A_FLAGS, A_STOP, A_UPDATED, A_MAXSPEED, A_MOVESPEED,
                     A_POINT, A_SEGMENT, A_TARGET, A_VEL, A_ID, A_WORLD)

A_FOLLOW = 0x98      # the destination AGENT (ANIMREF-RE 38.2: 0x00602AA8 writes it)


def read_copy(handle, agbase, array_off, count_off, aid):
    """One agent's block from one world array, or None if absent."""
    cnt = keytap.read_handle(handle, agbase + count_off, 4)
    arr = keytap.read_handle(handle, agbase + array_off, 4)
    if not cnt or not arr:
        return None
    count, array = u32(cnt), u32(arr)
    if not array or aid >= count:
        return None
    p = keytap.read_handle(handle, array + aid * 4, 4)
    if not p or not u32(p):
        return None
    blk = keytap.read_handle(handle, u32(p), AGENT_SPAN)
    if not blk or len(blk) < AGENT_SPAN:
        return None
    if u32(blk, A_ID) != aid:
        return {"bad_id": u32(blk, A_ID)}
    return {
        "ptr": u32(p),
        "flags": u32(blk, A_FLAGS),
        "world": i32(blk, A_WORLD),
        "stop": u32(blk, A_STOP),
        "updated": u32(blk, A_UPDATED),
        "maxspeed": f32(blk, A_MAXSPEED),
        "movespeed": f32(blk, A_MOVESPEED),
        "x": f32(blk, A_POINT), "y": f32(blk, A_POINT + 4),
        "segx": f32(blk, A_SEGMENT), "segy": f32(blk, A_SEGMENT + 4),
        "tx": f32(blk, A_TARGET), "ty": f32(blk, A_TARGET + 4),
        "vx": f32(blk, A_VEL), "vy": f32(blk, A_VEL + 4),
        "follow": u32(blk, A_FOLLOW),
    }


def world_clock(handle, agbase, world):
    raw = keytap.read_handle(handle, agbase + world * OFF_WORLD_STRIDE + OFF_WORLD_CLOCK, 4)
    return u32(raw) if raw else None


def dist(a, b):
    if a is None or b is None or "x" not in a or "x" not in b:
        return None
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--agents", default="1,10",
                    help="agent ids to poll, comma-separated (default 1,10: the "
                         "player as our server numbers it, and the Hatcher)")
    ap.add_argument("--hz", type=float, default=30.0)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--wait", type=float, default=120.0,
                    help="seconds to keep retrying until a client is in a map")
    ap.add_argument("--out", default=None, help="JSONL path (default: vault/research/animref/agenttap-<stamp>.jsonl)")
    ap.add_argument("--any-build", action="store_true")
    a = ap.parse_args()
    ids = [int(x) for x in a.agents.split(",") if x.strip()]

    # wait for a client in a map
    t_wait = time.time()
    handle = base = None
    pid = None
    while True:
        pids = [a.pid] if a.pid else agentprobe.gw_pids()
        if pids:
            pid = pids[-1]
            try:
                base, path = keytap.module_info(pid, "Gw.exe")
                import pinned
                pinned.assert_build(path, why=f"agenttap on pid {pid}", allow_any=a.any_build)
                handle = keytap.open_read(pid)
                resolve(pid, handle, base)
                break
            except (TapFail, Exception) as ex:       # not in a map yet
                handle = None
                last = str(ex)
        if time.time() - t_wait > a.wait:
            sys.exit(f"no client in a map within {a.wait:.0f} s ({last if pids else 'no Gw.exe'})")
        time.sleep(0.5)

    if a.out is None:
        import vaultpath
        d = vaultpath.vault_path("research", "animref")
        os.makedirs(d, exist_ok=True)
        a.out = os.path.join(d, time.strftime("agenttap-%Y%m%dT%H%M%S.jsonl"))
    print(f"pid {pid}, polling agents {ids} at {a.hz:.0f} Hz for {a.seconds:.0f} s -> {a.out}", flush=True)
    period = 1.0 / a.hz
    t0 = time.time()
    n = 0
    last_line = {}
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "head", "pid": pid, "agents": ids, "t0": t0, "hz": a.hz}) + "\n")
        while time.time() - t0 < a.seconds:
            t = time.time() - t0
            try:
                _ctx, agbase, ctrl, _ptr = resolve(pid, handle, base)
            except TapFail as ex:
                fh.write(json.dumps({"kind": "lost", "t": t, "why": str(ex)}) + "\n")
                time.sleep(period)
                continue
            row = {"kind": "sample", "t": round(t, 4), "controlled": ctrl,
                   "clock0": world_clock(handle, agbase, 0),
                   "clock1": world_clock(handle, agbase, 1), "agents": {}}
            for aid in ids:
                row["agents"][str(aid)] = {
                    "sync": read_copy(handle, agbase, OFF_SYNC_ARRAY, OFF_SYNC_COUNT, aid),
                    "async": read_copy(handle, agbase, OFF_ASYNC_ARRAY, OFF_ASYNC_COUNT, aid),
                }
            fh.write(json.dumps(row) + "\n")
            n += 1
            # a terse live line whenever the Hatcher's state changes
            if len(ids) >= 2:
                p, h = row["agents"][str(ids[0])], row["agents"][str(ids[1])]
                line = {
                    "d_sync": dist(h["sync"], p["sync"]), "d_async": dist(h["async"], p["async"]),
                    "h_stop_s": (h["sync"] or {}).get("stop"), "h_stop_a": (h["async"] or {}).get("stop"),
                    "h_follow": (h["sync"] or {}).get("follow"),
                }
                key = (line["h_stop_s"] != 0, line["h_stop_a"] != 0, line["h_follow"])
                if key != last_line.get("key"):
                    print(f"  t={t:6.2f}  Hatcher sync {line['d_sync'] and round(line['d_sync'])} u / "
                          f"async {line['d_async'] and round(line['d_async'])} u from the player; "
                          f"+0x48 sync={line['h_stop_s']} async={line['h_stop_a']}  +0x98={line['h_follow']}",
                          flush=True)
                    last_line["key"] = key
            time.sleep(period)
    print(f"{n} samples written to {a.out}")
    summarise(a.out, ids)


def summarise(path, ids):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    samples = [r for r in rows if r.get("kind") == "sample"]
    if len(ids) < 2 or not samples:
        print("nothing to summarise")
        return
    P, H = str(ids[0]), str(ids[1])
    print("\nSUMMARY")
    for copy in ("sync", "async"):
        ds = [dist(r["agents"][H][copy], r["agents"][P][copy]) for r in samples]
        ds = [d for d in ds if d is not None]
        if ds:
            print(f"  Hatcher {copy:5} copy: distance to the player's {copy} copy: "
                  f"min {min(ds):.1f}  max {max(ds):.1f}  last {ds[-1]:.1f} u  (n={len(ds)})")
    flags_h = {(r["agents"][H]["sync"] or {}).get("flags") for r in samples} - {None}
    flags_p = {(r["agents"][P]["sync"] or {}).get("flags") for r in samples} - {None}
    print(f"  m_flags seen -- Hatcher sync: {[hex(f) for f in flags_h]}   player sync: {[hex(f) for f in flags_p]}")
    fol = {(r["agents"][H]["sync"] or {}).get("follow") for r in samples} - {None}
    print(f"  Hatcher sync +0x98 (followed agent) values seen: {sorted(fol)}")
    # when did the sync copy park (stop -> 0) and how far apart were the copies then
    prev = None
    for r in samples:
        hs, ha = r["agents"][H]["sync"], r["agents"][H]["async"]
        if not hs or not ha or "stop" not in hs:
            continue
        st = hs["stop"]
        if prev is not None and prev != 0 and st == 0:
            print(f"  t={r['t']:.2f}: Hatcher SYNC copy parked (+0x48 {prev} -> 0) at "
                  f"{dist(hs, r['agents'][P]['sync']):.1f} u from the player; ASYNC copy "
                  f"{dist(ha, r['agents'][P]['async']):.1f} u, {dist(hs, ha):.1f} u behind the sync copy; "
                  f"sync flags {hs['flags']:#x} follow {hs['follow']}")
        if prev is not None and prev == 0 and st != 0:
            print(f"  t={r['t']:.2f}: Hatcher SYNC copy set off (+0x48 0 -> {st}); "
                  f"maxspeed {hs['maxspeed']:.0f} x {hs['movespeed']:.2f}; follow {hs['follow']}")
        prev = st


if __name__ == "__main__":
    main()
