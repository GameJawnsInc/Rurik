"""READ-ONLY desk check for panel item prior-art-and-retail-F2.

Drives toolkit/authsrv/agtrack_mirror.py (HEAD 9f7d91a) with a SYNTHETIC event
stream shaped like each upstream's keyboard policy, and prints the verdict the
mirror gives at the first post-walk click grant.  Prints only; writes nothing.

Scenario (OpenTyria policy):
  t=0        player at A, fence state as given
  0..T       keyboard walk A -> B at 288 u/s, one 0x003D report every `rep_ms`
             SERVER SENDS NOTHING (OpenTyria has no 0x003D handler)
  T          0x0047 stop report at B (OpenTyria: accepted only if <=100 u,
             and in either case sends NOTHING back)
  T+idle     player clicks at C; OpenTyria answers 0x0029 with the first
             waypoint of a path that starts at its own stale copy (A).
             The client bakes it: q = the sync copy's own +0x78 (= A).

The question the item answers "by construction": does that grant SNAP?
"""
import os
import sys

TOOLKIT = r"C:\gd\Rurik\toolkit"
sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
import agtrack_mirror as am  # noqa: E402

SPEED = 288.0
TICK = 100


def run(leg_u, idle_s, prune_ms, rep_ms=250, label=""):
    m = am.AgTrackMirror(mesh=None, prune_ms=prune_ms)   # NoMesh: straightline
    # --- the client's sync copy is parked at A, the last hard pin -----------
    A = (0.0, 0.0)
    m.sync.set_position(A[0], A[1], 0, 0)
    # --- keyboard walk A -> B ------------------------------------------------
    T = int(leg_u / SPEED * 1000)
    t = 0
    while t <= T:
        d = SPEED * t / 1000.0
        pos = (A[0] + d, A[1])
        m.on_player_command(t, pos, 0, ("hdg", 1.0, 0.0))
        # the client's own per-tick machinery between reports
        for tt in range(t + TICK, min(t + rep_ms, T + 1), TICK):
            m.tick(tt, async_pos=(A[0] + SPEED * tt / 1000.0, A[1]))
        t += rep_ms
    B = (A[0] + leg_u, A[1])
    m.on_player_command(T, B, 0, ("stop",))
    # --- idle, then the click ----------------------------------------------
    for tt in range(T + TICK, T + int(idle_s * 1000) + 1, TICK):
        m.tick(tt, async_pos=B)
    now = T + int(idle_s * 1000)
    m.on_player_command(now, B, 0, ("click",), dest=(B[0], B[1] + 1000.0, 0))
    # OpenTyria answers with a leg starting at ITS copy (A); the wire carries
    # only the destination, so the bake measures from the client's +0x78 (= A).
    v = m.predict(now, async_pos=B)
    print("%-34s leg=%6.0fu idle=%4.1fs prune=%-6s chain=%2d -> %-12s "
          "sep=%s matched_age=%s"
          % (label, leg_u, idle_s, prune_ms, v.chain_len, v.code,
             ("%.0f" % v.gate1_sep) if v.gate1_sep is not None else "-",
             v.matched_age_ms))
    return v.code


print("== OpenTyria keyboard policy (server silent during keys) ==")
print("q = the client sync copy parked at the walk start A\n")
for prune in (None, 3000, 2500):
    for leg in (150.0, 400.0, 800.0, 2000.0):
        for idle in (0.5, 2.0, 5.0):
            run(leg, idle, prune, label="OpenTyria")
    print()
