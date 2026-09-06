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

AND THE AGTRACK FENCE (MOVECODE-1z-an, `--no-fence` reverts). `clientControlled`
-- the dword at the agent's AgTrack record that the dispatcher's 0x00606002
tests before it will run the three-gate snap test at all -- is the field REALFIX
sec.0.11's two-stage lock account turns on, and sec.1z-am named reading it here
as the cheap next step: `movetap` has read it since sec.1z-aa, but NO movetap
tape overlaps any lead run (the arm shipped after that campaign) and movetap
cannot certify under the harness anyway (sec.1z-ag.6, 10-12 Hz against a 50 Hz
floor). This tape already runs beside those captures.

It is `movetap.agtrack_fence` CALLED, not reimplemented -- same record walk, same
bounds checks, same string sentinels, so a drift in the offsets breaks one place
and `movetap --selftest` still owns them. Two things are this file's own: the
reads are memoised per sample (`memo_reader`), because the AgTrack header is
per-AgTrack and would otherwise be re-fetched for every tapped agent on a reader
already delivering ~9 Hz of the 30 it asks for; and the SYNC block is the one
handed over, because the record is keyed by agent id and only `gate_reach`'s
world term depends on the copy -- world 0 being the branch where the test is
actually reached.

THE NEGATIVE CONTROL IS FREE AND IS THE POINT. 0x00605F10 writes
`clientControlled` from exactly two callers, both in the ChCliBase local-command
block, so it is set for the LOCAL PLAYER and nobody else: the Hatcher's record
must read `shut` for the whole run. The summary asserts that, and says so loudly
when it fails -- an `open` there means this reader is on the wrong record and the
player's column is worth nothing.

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
import struct
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
                     A_POINT, A_SEGMENT, A_TARGET, A_VEL, A_ID, A_WORLD,
                     agtrack_fence, _fence_blank)

import groundz as _groundz   # noqa: E402  (GROUNDZ-F1: the AgentView height read)

A_FOLLOW = 0x98      # the destination AGENT (ANIMREF-RE 38.2: 0x00602AA8 writes it)

# THE CAMERA (MOVECODE-1z-ay, `--no-camera` reverts). Imported from fovread
# rather than restated: those three addresses are the frustum builder's own
# failure-path arguments, and a drift must break ONE place. sec.1z-ax's
# projection is exact GIVEN the camera, and this is what puts the camera on the
# same clock as the click -- sec.1z-aw's whole failure was fitting a camera that
# moves between samples instead of reading it.
from fovread import (VA_FOV, VA_POSITION, VA_TARGET,            # noqa: E402
                     IMAGE_BASE as FOV_IMAGE_BASE)


def read_camera(handle, base):
    """{fov, pos, tgt} from the client, or a reason it could not be read.

    Same sentinel doctrine as the fence: a camera that could not be read is a
    THIRD thing, not a zero one -- a (0,0,0) position would project every click
    to the same fraction and look like data.
    """
    def f32(va, n):
        raw = keytap.read_handle(handle, base + (va - FOV_IMAGE_BASE), 4 * n)
        if raw is None or len(raw) < 4 * n:
            return None
        return list(struct.unpack("<%df" % n, raw))
    fov = f32(VA_FOV, 1)
    pos = f32(VA_POSITION, 3)
    tgt = f32(VA_TARGET, 3)
    if fov is None or pos is None or tgt is None:
        return {"cam": "unread:camera-unreadable"}
    return {"fov": fov[0], "pos": pos, "tgt": tgt}


def memo_reader(handle):
    """A `read(addr, n)` closure that answers each address ONCE per sample.

    `agtrack_fence` fetches the AgTrack header (`+0x20..+0x2C`) and the armed
    id on every call, and this file calls it once per tapped agent -- but those
    two reads are per-AGTRACK, not per-agent, so the second agent's copies are
    pure cost. That matters here in a way it does not in movetap: this tape
    already delivers ~9 Hz against the 30 it asks for (MOVECODE-1z-ak.7, gap
    p50 109 ms), so every avoidable cross-process round trip is bought out of
    the sample rate the fence is being added to explain.

    Scoped to ONE sample and thrown away, because the whole point of the tape is
    that these words change: a memo that outlived the sample would report a
    stale fence with a fresh timestamp, which is worse than not reading it.
    """
    cache = {}

    def read(addr, n):
        key = (addr, n)
        if key not in cache:
            cache[key] = keytap.read_handle(handle, addr, n)
        return cache[key]
    return read


def read_copy(handle, agbase, array_off, count_off, aid):
    """One agent's block from one world array: (fields, raw block).

    Returns the RAW block beside the decoded fields because `agtrack_fence`
    needs it -- it re-checks the agent's own id field against the id we indexed
    with, and reads the world word for the `gate_reach` term. Handing it the
    decoded dict instead would mean trusting our own decode twice."""
    cnt = keytap.read_handle(handle, agbase + count_off, 4)
    arr = keytap.read_handle(handle, agbase + array_off, 4)
    if not cnt or not arr:
        return None, None
    count, array = u32(cnt), u32(arr)
    if not array or aid >= count:
        return None, None
    p = keytap.read_handle(handle, array + aid * 4, 4)
    if not p or not u32(p):
        return None, None
    blk = keytap.read_handle(handle, u32(p), AGENT_SPAN)
    if not blk or len(blk) < AGENT_SPAN:
        return None, None
    if u32(blk, A_ID) != aid:
        return {"bad_id": u32(blk, A_ID)}, blk
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
        # THE PLANE WORDS (MOVECODE-1z-bx, 2026-09-05).  Each of the three
        # points is (x, y, plane) and the plane is a SIGNED int in the third
        # dword -- +0x80 for m_point, +0x90 for m_segmentPoint, +0xA4 for
        # m_targetPoint (the one a 0x0029/0x002A field 3 writes).  Four
        # independent witnesses: movetap's own A_POINT/A_SEGMENT/A_TARGET
        # arithmetic, agents.py's CHECKSUM_FIELDS naming +0x80 as the int,
        # MOVECODE FINDINGS sec.433/677 (`out->plane = [esi+0x80]`), and
        # agtrack_mirror.bake_grant's independent statement of the split.
        # movetap already emits all three per sample (movetap.py:1361-1366).
        #
        # WHY IT WAS MISSING AND WHY IT COSTS NOTHING.  ANIMREF sec.42 derived
        # the NPC follow's frozen spawn-plane fault and could not SHIP it,
        # because its own PASS criteria need the client's plane belief and
        # this tape had no column for it -- so RUN-1zBW produced the geometry
        # (4 follow orders onto plane-18-only bridge deck, all stamped plane
        # 0) and STILL could not confirm it.  The read is free: read_copy
        # already pulls the whole AGENT_SPAN (0xD0) block in one call and
        # 0x80 < 0x90 < 0xA4 < 0xD0, so these are three decodes of bytes
        # already in hand and ZERO extra cross-process reads.
        "plane": i32(blk, A_POINT + 8),
        "segplane": i32(blk, A_SEGMENT + 8),
        "tplane": i32(blk, A_TARGET + 8),
    }, blk


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
    ap.add_argument("--no-camera", dest="camera", action="store_false",
                    help="skip the camera read (MOVECODE-1z-ay). ON by "
                         "default; sec.1z-ax's projection needs it on the "
                         "same clock as the click")
    ap.add_argument("--no-groundz", dest="groundz", action="store_false",
                    help="skip the AgentView height read (GROUNDZ-F3). ON by "
                         "default. It is the ONLY way to see a drawn height: "
                         "the agent's own movement record has no z at all and "
                         "its fourth point word is a literal zero (MOVECODE "
                         "sec.1z-cb). Every offset it uses is STATIC "
                         "disassembly that has never been read from a running "
                         "client, so this is the revert if it misbehaves -- and "
                         "a refusal in the `groundz.why` column is the tell.")
    ap.add_argument("--no-fence", dest="fence", action="store_false",
                    help="skip the AgTrack fence read (MOVECODE-1z-an). ON by "
                         "default; this is the revert if the extra reads cost "
                         "more sample rate than the fence is worth")
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
    elif os.path.dirname(a.out):
        # An explicit --out into a directory that does not exist yet crashed
        # here with FileNotFoundError AFTER the client was found -- twice, on
        # RUN-NPCTRACK-R1 (2026-09-06), whose runsheet named a new arc's
        # directory. The default path made its own directory; this one now
        # does too. A tape that dies at open() costs a whole client run.
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
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
            rd = memo_reader(handle) if a.fence else None
            if a.camera:
                row["camera"] = read_camera(handle, base)
            for aid in ids:
                sync, sync_blk = read_copy(handle, agbase, OFF_SYNC_ARRAY,
                                           OFF_SYNC_COUNT, aid)
                asy, _asy_blk = read_copy(handle, agbase, OFF_ASYNC_ARRAY,
                                          OFF_ASYNC_COUNT, aid)
                one = {"sync": sync, "async": asy}
                if a.groundz:
                    # GROUNDZ-F3: the height is NOT on the agent -- it is on the
                    # client's AgentView object, and this walks there from the
                    # agent id. Every failure mode returns a NAMED refusal
                    # rather than a float, so a wrong module base cannot show up
                    # as a body at ground level (groundz.py, test_groundz.py).
                    one["groundz"] = _groundz.read_groundz(
                        lambda addr, n: keytap.read_handle(handle, addr, n),
                        base, aid)
                if a.fence:
                    # THE SYNC BLOCK, deliberately. The AgTrack record is keyed
                    # by agent id, so which copy we hand over cannot change
                    # `clientControlled` -- but it DOES change `gate_reach`,
                    # whose world term separates "test-runs" (world != 1) from
                    # "world1:append". World 0 is the branch on which the snap
                    # test at 0x006055E0 is actually reached, and that is the
                    # question the fence is being read to answer.
                    one["fence"] = (agtrack_fence(rd, agbase, aid, sync_blk)
                                    if sync_blk is not None
                                    else _fence_blank("no-sync-block"))
                row["agents"][str(aid)] = one
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
                pf = (p.get("fence") or {}).get("fence_state")
                key = (line["h_stop_s"] != 0, line["h_stop_a"] != 0,
                       line["h_follow"], pf)
                if key != last_line.get("key"):
                    print(f"  t={t:6.2f}  Hatcher sync {line['d_sync'] and round(line['d_sync'])} u / "
                          f"async {line['d_async'] and round(line['d_async'])} u from the player; "
                          f"+0x48 sync={line['h_stop_s']} async={line['h_stop_a']}  +0x98={line['h_follow']}"
                          + (f"  player fence={pf}" if pf else ""),
                          flush=True)
                    last_line["key"] = key
            time.sleep(period)
    print(f"{n} samples written to {a.out}")
    summarise(a.out, ids)


def summarise_fence(samples, P, H):
    """The AgTrack fence over the run, with its own built-in negative control.

    THE CONTROL IS FREE AND IT IS THE POINT. `clientControlled` is written by
    0x00605F10, whose only two callers sit in the ChCliBase local-command block
    -- i.e. it is set for the LOCAL PLAYER's agent and nobody else. So the
    Hatcher's record must read `shut` for the whole run. If it ever reads
    `open`, this reader is indexing the wrong record and the player's column is
    not evidence of anything. That check costs one extra agent we were already
    tapping.

    Every `unread:` value is printed rather than dropped: a fence that could not
    be read is a third thing, not a shut one (movetap's own rule, and the reason
    the state is a string).
    """
    have = [r for r in samples if (r["agents"].get(P) or {}).get("fence")]
    if not have:
        print("  fence: not read (--no-fence, or an older tape)")
        return
    def states(who):
        out = {}
        for r in have:
            f = (r["agents"].get(who) or {}).get("fence") or {}
            s = f.get("fence_state")
            out[s] = out.get(s, 0) + 1
        return out
    ps, hs = states(P), states(H)
    print(f"  FENCE player agent {P}: {ps}")
    print(f"  FENCE Hatcher {H} (NEGATIVE CONTROL, must be shut throughout): {hs}")
    bad = [s for s in hs if s not in ("shut",) and not str(s).startswith("unread:")]
    if bad:
        print(f"    !! CONTROL FAILED: the Hatcher's fence read {bad}. Only the "
              f"local player's agent is client-controlled (0x00605F10 has two "
              f"callers, both local-command), so this reader is on the wrong "
              f"record and the player's column above proves nothing.")
    # transitions on the player, which is what the lock question is about
    prev = None
    for r in have:
        f = (r["agents"].get(P) or {}).get("fence") or {}
        s = f.get("fence_state")
        if prev is not None and s != prev:
            print(f"    t={r['t']:.2f}: player fence {prev} -> {s} "
                  f"(gate_reach {f.get('gate_reach')}, raw {f.get('fence_raw')})")
        prev = s
    reach = {}
    for r in have:
        g = ((r["agents"].get(P) or {}).get("fence") or {}).get("gate_reach")
        reach[g] = reach.get(g, 0) + 1
    print(f"  player gate_reach over the run: {reach}")


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
    summarise_fence(samples, P, H)
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
