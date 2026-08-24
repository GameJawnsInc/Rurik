"""Walk-on-cancel: what retail actually sends at a movement-cancel, re-derived.

    python toolkit/authsrv/cancelwalk.py

The question `studies/movement/CANCELWALK.md` exists to answer, and this is
its evidence reader: everything that document claims about capture
`20260824T074002` (live) and `authsrv-20260824T081335-c1.jsonl` (ours) should
reproduce by running this. Read-only over the vault; no client, no server, no
socket. Stdlib only.

THREE FACTS THIS PRINTS, each of which corrects a standing claim:

1. ORDER. In every movement-triggered cancel (t=81.660 W, 98.779 click,
   128.805 W) and the mid-windup stop (114.641), the movement answer
   (0x0025/0x002B/0x0029) rides AFTER the release burst, at the batch tail.
   `castmech/FINDINGS.md` 3f recorded the grant "BEFORE the three" and its
   3g proposed message order as the one no-warp experiment; both rested on a
   misreading. Wire order here is byte order: one TCP segment, one stable
   sort.

2. STEERING. The retail client does NOT walk toward the granted point. The
   grant is `reported + vec2 (+0.5)` where vec2 is a LATCHED heading -- bit-
   identical across presses 33 s apart, and exactly negated when the operator
   backpedals -- so its direction is stale by construction. At t=128.805 the
   grant points north (0.017, 0.999) and the client walks WNW (-0.79, +0.62);
   at t=114.641 same grant direction, client walks west. The client self-
   walks in its own live input direction the moment the burst clears the
   hold; the 0x0029 moves the sync copy and nothing else, exactly as
   REALFIX-O1 models it.

3. THE FREEZE. Our client, answered with the same burst in the same order
   plus a ZERO-lead grant, holds a movement episode open for ~0.8 s
   (0x003D at t=5.417 to 0x0047 at t=6.234) and moves ZERO units -- ~25
   client frames with the hold visually cleared (the 3g run: animation
   stops). That kills every timing/frame-race hypothesis. The one wire delta
   present against BOTH retail walking cancels is the 0x0029's destination:
   zero-lead vs strictly-ahead. See CANCELWALK.md's elimination table.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import cmsgstream  # noqa: E402
import vaultpath   # noqa: E402

LIVE_STAMP = "20260824T074002"
OURS_NAME = "authsrv-20260824T081335-c1.jsonl"

GV_SKILL_STOPPED = 59
GV_ATTACK_STOPPED = 3
MOVEMENT_ANSWER = {0x0025, 0x0029, 0x002A, 0x002B}
RELEASE_BURST = {0x009F, 0x00E2}


def _fmt1(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, (list, tuple)):
        return "(" + ", ".join(_fmt1(x) for x in v) + ")"
    if isinstance(v, str):
        return ascii(v)
    return str(v)


def _fmt(vals):
    return "[" + ", ".join(_fmt1(v) for v in vals) + "]"


def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


def live_merged():
    """Both directions of the live game channel on one clock, wire order.

    `cmsgstream.timed` sorts stably by segment time, and message order within
    a connection is stream-offset order, so ties preserve byte order -- which
    is what makes the ORDER claim below a reading rather than an inference.
    """
    c2s = [(t, conn, "c2s", op, vals) for (t, conn, op, vals)
           in cmsgstream.timed(LIVE_STAMP, "c2s", "game")]
    s2c = [(t, conn, "s2c", op, vals) for (t, conn, op, vals)
           in cmsgstream.timed(LIVE_STAMP, "s2c", "game")]
    return sorted(c2s + s2c, key=lambda r: r[0])


def cancel_instants(allm):
    """[(t, conn, which)] for every skill-stop (59) and attack-stop (3)."""
    out = []
    for t, conn, d, op, vals in allm:
        if d == "s2c" and op == 0x009F and len(vals) > 1 \
                and vals[1] in (GV_SKILL_STOPPED, GV_ATTACK_STOPPED):
            out.append((t, conn, vals[1]))
    return out


def burst_and_walk(allm, at, conn):
    """One cancel instant: the trigger, the answer batch in wire order, and
    the client's own next report -- the walk vector the verdicts hang on."""
    trigger = None
    for t, c, d, op, vals in allm:
        if c == conn and d == "c2s" and at - 0.6 <= t <= at \
                and op in (0x003D, 0x003E, 0x0028):
            trigger = (t, op, vals)
    batch = [(t, op, vals) for t, c, d, op, vals in allm
             if c == conn and d == "s2c" and abs(t - at) < 0.005
             and op in (MOVEMENT_ANSWER | RELEASE_BURST)]
    after = [(t, op, vals) for t, c, d, op, vals in allm
             if c == conn and d == "c2s" and at < t <= at + 1.2
             and op in (0x003D, 0x0047)]
    return trigger, batch, after


def report_live():
    allm = live_merged()
    print(f"=== live {LIVE_STAMP}: "
          f"{sum(1 for m in allm if m[2] == 'c2s')} c2s + "
          f"{sum(1 for m in allm if m[2] == 's2c')} s2c ===")

    # The latch: mid-action presses report a STALE vec2. Bit-identical
    # repeats across tens of seconds are the fingerprint.
    vecs = {}
    for t, conn, d, op, vals in allm:
        if d == "c2s" and op == 0x003D:
            vecs.setdefault(tuple(vals[3]), []).append(round(t, 3))
    stale = {v: ts for v, ts in vecs.items() if len(ts) >= 3}
    print("\n-- LATCHED vec2 (>=3 bit-identical 0x003D reports):")
    for v, ts in stale.items():
        print(f"   {v} at t={ts}")

    for at, conn, which in cancel_instants(allm):
        name = "SKILL_STOPPED(59)" if which == GV_SKILL_STOPPED \
            else "ATTACK_STOPPED(3)"
        trigger, batch, after = burst_and_walk(allm, at, conn)
        print(f"\n-- t={at:.3f}  {name}")
        if trigger:
            tt, top, tv = trigger
            print(f"   trigger  t={tt:.3f} c2s 0x{top:04X} {_fmt(tv)}")
        for t, op, vals in batch:
            print(f"   answer   t={t:.3f} s2c 0x{op:04X} {_fmt(vals)}")
        # Steering verdict: grant direction vs the client's own displacement.
        grant = next((vals for _, op, vals in batch if op == 0x0029), None)
        if trigger and grant and trigger[1] == 0x003D and after:
            rep = trigger[2][1]
            gd = _unit((grant[2][0] - rep[0], grant[2][1] - rep[1]))
            nt, nop, nv = after[0]
            disp = (nv[1][0] - rep[0], nv[1][1] - rep[1])
            dist = math.hypot(*disp)
            if dist > 5.0:
                wd = _unit(disp)
                dot = gd[0] * wd[0] + gd[1] * wd[1]
                print(f"   WALK     {dist:6.1f} u in {nt - trigger[0]:.3f} s, "
                      f"direction ({wd[0]:+.3f},{wd[1]:+.3f}); "
                      f"grant direction ({gd[0]:+.3f},{gd[1]:+.3f}); "
                      f"cos = {dot:+.3f}"
                      + ("  <- NOT along the grant" if dot < 0.9 else ""))
            else:
                print(f"   WALK     none ({dist:.1f} u by t={nt:.3f})")


def report_ours():
    path = os.path.join(vaultpath.vault_root(), "captures", "gamesrv",
                        OURS_NAME)
    if not os.path.exists(path):
        print(f"\n[SKIP] {OURS_NAME} not in the vault; the loopback half "
              f"of the evidence cannot be shown")
        return
    print(f"\n=== ours {OURS_NAME} (map pinned by the 3g run) ===")
    events = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            k, t = r.get("kind"), r.get("t", 0.0)
            if k == "decoded":
                events.append((t, "c2s", r["opcode"],
                               r.get("name", "?"), r.get("values")))
            elif k == "sent" and r.get("opcode") not in (12, 13, 30):
                events.append((t, "s2c", r["opcode"],
                               r.get("label", ""), None))
    for t, d, op, name, vals in events:
        if 4.5 <= t <= 8.1:
            tail = _fmt(vals) if vals is not None else name
            print(f"   t={t:8.3f} {d} 0x{op:04X} {tail[:110]}")
    # The freeze, stated as arithmetic: the press that cancelled a cast
    # opens a movement episode that moves 0 u. Anchor on our own 59 send,
    # not on file order -- the first 0x003D in the file is ordinary walking.
    stop59 = [e for e in events if e[1] == "s2c" and e[2] == 0x9F
              and "skill_stopped" in e[3]]
    stops = [e for e in events if e[1] == "c2s" and e[2] == 0x47]
    for t59, *_ in stop59:
        p = next((e for e in reversed(events) if e[1] == "c2s"
                  and e[2] == 0x3D and t59 - 0.2 <= e[0] <= t59), None)
        if p is None:
            continue  # an Esc cancel; no movement episode to measure
        s = next((x for x in stops if x[0] > p[0]), None)
        if s:
            dist = math.hypot(s[4][1][0] - p[4][1][0],
                              s[4][1][1] - p[4][1][1])
            print(f"\n   FREEZE: cancel press 0x003D t={p[0]:.3f} -> 0x0047 "
                  f"t={s[0]:.3f} ({s[0] - p[0]:.3f} s) moved {dist:.1f} u")


def main():
    report_live()
    report_ours()
    print("\nSee studies/movement/CANCELWALK.md for what this eliminates "
          "and the pre-registered run ladder.")


if __name__ == "__main__":
    main()
