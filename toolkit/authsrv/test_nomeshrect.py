"""NOMESH-RECT: a meshless instance's leads stop at the map's rect, and a portal
will not zone into a map whose file the archive does not hold.

THE SPECIMEN (maprect.py has the whole of it): harness 20260925T083808,
loopback, build 38797. The player backpedalled into `ascalon_to_corridor`,
zoned to map 168, whose file 0x5F0B3 neither archive held; the client logged
`Creating default map`; a W hold armed a lead at (2056, 1536) and the 1z-di
re-grant chain walked the copy east 520 u per arrival, unbounded, until the
client asserted `pos.x <= worldDims.x1` (agint.h(929)) inside the 0x0029
handler on RE-GRANT 4's own point, (4136, 1536).

What this file pins, section by section:

  1. the two numbers and where each came from -- the rect against the
     client's own log line when the run folder is on this machine;
  2. maprect's pure geometry, including the heading a clipped ray keeps;
  3. the lead's no-mesh door: bounded with a rect, the historical answer
     without one (the revert arm), and a MESHED instance never consulting it;
  4. THE CAPTURE REPLAYED through the real `kbd_lead_chain_tick`: with no
     rect the chain reproduces the run's eight wire points exactly (the
     known-bad arm must reproduce the thing itself), and with the rect it
     sends two, the second stopped at the bound, then stops and says why;
  5. send()'s backstop for every other sender of a point, and its lock;
  6. the rect read beside load_pathmap, against the real archive, with a
     positive control that can fail (every trapezoid of a real mesh inside
     the rect that map's own file declares);
  7. the portal refusal on the real `ascalon_to_corridor` row, with the
     firing control, and the startup scan's wiring.

Sections 1 and 6 read the vault and declare their skips; the rest need no
vault, no client and no socket.
"""
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                    # noqa: E402
import authsrv                                                   # noqa: E402
import maprect                                                   # noqa: E402
import vaultpath                                                 # noqa: E402
from test_position_trust import Sent, FakeRec                    # noqa: E402

# MEASURED 2026-09-25: 45 on a machine holding the vault; 37 is the core that
# needs none -- sections 1 and 6 declare their 8 as skips without it.
LEDGER = checks.Ledger("NOMESH-RECT, the meshless instance's bound", floor=37)
check = checks.adopt(LEDGER)

SRC = open(authsrv.__file__, encoding="utf-8").read()
MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
RUN = "20260925T083808"           # the specimen
RUN_0914 = "20260914T085004"      # the second witness
# The run's own wire, from its gamesrv.log: KBD LEAD then RE-GRANT 1..8.
CAPTURE_REGRANTS = [2576.0, 3096.0, 3616.0, 4136.0, 4656.0, 5176.0, 5696.0,
                    6216.0]


class _Guard:
    """The AgTrack guard, reduced to what the chain reads: the mirror's
    world-0 and its arrival tick (0 = parked, which is `due`)."""

    def __init__(self, w0):
        class _S:
            pass
        self.mirror = _S()
        self.mirror.sync = _S()
        self.mirror.sync.plane = 0
        self.mirror.sync.t_arrive = 0
        self.mirror.sync.position = lambda ms, _w=w0: _w

    def _ms(self, now):
        return 0

    def __getattr__(self, name):
        return lambda *a, **k: None


class _Open:
    """A mesh that is walkable everywhere and clips nothing -- so any bound in
    the answer can only have come from somewhere else."""

    def walkable(self, x, y):
        return True

    def on_mesh(self, x, y, tol=1.0):
        return True

    def plane_at(self, x, y, prefer=None):
        return 0

    def plane_near(self, x, y, prefer=None):
        return 0

    def planes_at(self, x, y):
        return {0}

    def containing(self, x, y):
        class _T:
            plane = 0
        return [_T()]

    def clip(self, x0, y0, x1, y1, step=2.0, plane=None):
        return (x1, y1)

    def route(self, x0, y0, x1, y1, **kw):
        return [(x0, y0), (x1, y1)]


def _replay_chain(rect, ticks=len(CAPTURE_REGRANTS) + 1):
    """The run's leg from its KBD LEAD row, then `ticks` arrivals. Returns
    (wire x values, the recorder). The leg is armed exactly as the capture's
    `kbd_leg act=arm` row says: from (1536, 1536) to (2056, 1536), ray the
    unclipped lead (2056, 1536), clip_why 'no-mesh'."""
    now = time.time()
    st = {"pos": (1536.0, 1536.0), "plane": 0, "pathmap": None,
          "map_rect": rect, "kbd_moving_at": now - 0.3,
          "fence_shut_at": None, "dest": (2056.0, 1536.0),
          "kbd_leg": authsrv.a2_leg_note((1536.0, 1536.0), (2056.0, 1536.0),
                                         0, 1, now, ray=(2056.0, 1536.0),
                                         clip_why="no-mesh")}
    rec = FakeRec()
    xs = []
    for _ in range(ticks):
        st["agtrack_guard"] = _Guard(tuple(st["kbd_leg"]["dest"]))
        w = Sent(st)
        authsrv.kbd_lead_chain_tick(w, st, 0, rec)
        for _op, vals, label in w.of(MOVE):
            xs.append((float(vals[1][0]), float(vals[1][1]), label))
    return xs, rec


def main():
    vault = vaultpath.vault_path()

    print("1. the numbers, and where each came from")
    check(maprect.CLIENT_DEFAULT_MAP_RECT == (-3072.0, -3072.0, 3072.0, 3072.0)
          and maprect.NO_MESH_RECT_INSET == 32.0,
          "the default map's rect is (-3072,-3072,3072,3072) OBSERVED, and the "
          "inset 32 u RECONSTRUCTION")
    rep = os.path.join(vault, "captures", "harness", RUN, "report.json")
    if os.path.isfile(rep):
        with open(rep, encoding="utf-8") as fh:
            log = json.load(fh).get("gw_log", [])
        rects = {m.group(1) for line in log
                 for m in [re.search(r"mapRect=\(([^)]*)\)", line)] if m}
        xs = [float(m.group(1)) for line in log
              for m in [re.search(r"point=\(([-\d.]+),", line)] if m]
        steps = [b - a for a, b in zip(xs, xs[1:])]
        got = (tuple(float(v) for v in next(iter(rects)).split(","))
               if len(rects) == 1 else None)
        check(got == maprect.CLIENT_DEFAULT_MAP_RECT
              and "Error: Creating default map" in log,
              f"1a. the client's own log in {RUN}: `Creating default map`, then "
              f"ONE mapRect on every MapQueryAltitude line, and it is ours",
              f"rects {sorted(rects)}")
        check(len(steps) >= 100 and max(steps) < maprect.NO_MESH_RECT_INSET / 5,
              "1b. the inset is over five of the body's largest per-frame steps "
              "in that log (108 lines, 4.03-5.76 u at 288 u/s)",
              f"n {len(steps)} max {max(steps) if steps else None}")
    else:
        LEDGER.skip("1a-1b", f"{rep} is not on this machine")
    rep14 = os.path.join(vault, "captures", "harness", RUN_0914, "report.json")
    if os.path.isfile(rep14):
        with open(rep14, encoding="utf-8") as fh:
            log14 = json.load(fh).get("gw_log", [])
        check("Error: Creating default map" in log14
              and any("0x05f0b3" in line for line in log14),
              f"1c. the second witness {RUN_0914} built the same default map "
              f"for the same missing file")
    else:
        LEDGER.skip("1c", f"{rep14} is not on this machine")

    print("\n2. maprect's geometry")
    R = maprect.CLIENT_DEFAULT_MAP_RECT
    check(maprect.inset_rect(R) == (-3040.0, -3040.0, 3040.0, 3040.0),
          "2a. the default rect inset by 32 u is +/-3040")
    try:
        maprect.inset_rect((0.0, 0.0, 50.0, 50.0))
        refused = False
    except ValueError:
        refused = True
    check(refused, "2b. a rect that holds nothing once inset REFUSES rather than "
          "returning an inverted box every containment test would fail")
    check(maprect.clip_ray((2056.0, 1536.0), (2576.0, 1536.0), R)
          == ([2576.0, 1536.0], False),
          "2c. a ray inside the box comes back unchanged and unclipped")
    check(maprect.clip_ray((2576.0, 1536.0), (3096.0, 1536.0), R)
          == ([3040.0, 1536.0], True),
          "2d. the specimen's RE-GRANT 2 ray (2576 -> 3096) stops at x = 3040")
    got, c = maprect.clip_ray((0.0, 0.0), (4000.0, 2000.0), R)
    check(c and abs(got[0] - 3040.0) < 1e-9 and abs(got[1] - 1520.0) < 1e-9,
          "2e. a DIAGONAL keeps its heading: it stops where it leaves the box "
          "(3040, 1520), it does not slide along the edge to (3040, 2000)", got)
    check(maprect.clip_ray((0.0, -3000.0), (0.0, -3600.0), R)
          == ([0.0, -3040.0], True),
          "2f. and on the other axis, the other sign")
    check(maprect.clip_ray((3040.0, 0.0), (3560.0, 0.0), R)
          == ([3040.0, 0.0], True),
          "2g. from ON the bound, heading out: a zero-length answer at the origin")
    check(maprect.clip_ray((3096.0, 1536.0), (3616.0, 1536.0), R)
          == ([3040.0, 1536.0], True),
          "2h. an origin already PAST the bound gets the nearest point inside, "
          "never one further out")
    check(maprect.clamp_point((4136.0, 1536.0), R) == ([3040.0, 1536.0], True)
          and maprect.clamp_point((-5000.0, 9000.0), R) == ([-3040.0, 3040.0], True)
          and maprect.clamp_point((10.0, -20.0), R) == ([10.0, -20.0], False),
          "2i. clamp_point: per axis, and a point inside is not moved")

    print("\n3. the lead's no-mesh door")
    st = {"pathmap": None, "map_rect": R}
    check(authsrv.a2_clip_lead(st, (3096.0, 1536.0), [3616.0, 1536.0])
          == ([3040.0, 1536.0], True, "no-mesh-rect"),
          "3a. no mesh, rect known: RE-GRANT 3's ray is stopped at the bound and "
          "the word says which door -- no-mesh-rect")
    check(authsrv.a2_clip_lead(st, (2056.0, 1536.0), [2576.0, 1536.0])
          == ([2576.0, 1536.0], False, "no-mesh"),
          "3b. a ray the bound does not touch keeps the historical word")
    got = authsrv.a2_clip_lead({"pathmap": None, "map_rect": None},
                               (3616.0, 1536.0), [4136.0, 1536.0])
    check(got == ([4136.0, 1536.0], False, "no-mesh"),
          "3c. REVERT ARM: no rect known -> the ray unbounded, as every run "
          "before NOMESH-RECT (this is the grant that asserted)", got)
    tiny = (-10.0, -10.0, 100.0, 100.0)
    got = authsrv.a2_clip_lead({"pathmap": _Open(), "map_rect": tiny,
                                "plane": 0}, (0.0, 0.0), [520.0, 0.0])
    check(got == ([520.0, 0.0], False, "clear"),
          "3d. a MESHED instance never consults the rect: a rect that would cut "
          "this ray at 68 u is ignored, the mesh's answer goes out unchanged",
          got)

    print("\n4. the capture replayed through the real re-grant chain")
    bad, _r = _replay_chain(None)
    check([p[0] for p in bad[:8]] == CAPTURE_REGRANTS
          and all(p[1] == 1536.0 for p in bad[:8])
          and "KBD LEAD RE-GRANT 4 (4136,1536)" in bad[3][2]
          and "[no-mesh]" in bad[3][2],
          f"4a. KNOWN-BAD ARM REPRODUCES {RUN}: with no rect the chain sends the "
          f"run's eight points, 2576 .. 6216 at y 1536, RE-GRANT 4 at (4136, "
          f"1536) labelled [no-mesh] -- the grant the client asserted on",
          [p[0] for p in bad])
    good, rec = _replay_chain(R)
    stops = [e for e in rec.of("kbd_leg") if e.get("act") == "regrant-stop"]
    check([p[0] for p in good] == [2576.0, 3040.0]
          and "[no-mesh-rect]" in good[1][2],
          "4b. WITH THE BOUND: two re-grants, the second stopped at x = 3040 and "
          "labelled [no-mesh-rect]; nothing past the rect goes on the wire",
          [(p[0], p[2][-40:]) for p in good])
    check(len(stops) == 1 and stops[0].get("why") == "no-progress"
          and stops[0].get("clip_why") == "no-mesh-rect",
          "4c. and the chain then STOPS and says why (regrant-stop, no-progress, "
          "no-mesh-rect) instead of re-granting the same point", stops)
    check(all(maprect.inside(p[:2], maprect.inset_rect(R)) for p in good),
          "4d. every point the bounded chain sent lies inside the inset rect")

    print("\n5. send()'s backstop, for every other sender of a point")
    UPD = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
    DST = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    vals = [1, [4136.0, 1536.0], 0, 0]
    out, was = authsrv._rect_bound_wire_point(st, MOVE, vals)
    check(out == [1, [3040.0, 1536.0], 0, 0] and was == (4136.0, 1536.0)
          and vals == [1, [4136.0, 1536.0], 0, 0],
          "5a. a 0x0029 at the asserting point is clamped to (3040, 1536), the "
          "caller's list untouched", (out, was))
    out, was = authsrv._rect_bound_wire_point(st, UPD, [1, [-5000.0, 9000.0], 0])
    check(out == [1, [-3040.0, 3040.0], 0],
          "5b. a 0x002C hard set is clamped per axis", out)
    out, was = authsrv._rect_bound_wire_point(
        st, DST, [1, (1536.0, 10400.0), 0, 0, 94])
    check(out[1] == (1536.0, 3040.0) and isinstance(out[1], tuple),
          "5c. a 0x002A too, and a tuple point stays a tuple", out)
    out, was = authsrv._rect_bound_wire_point(st, MOVE, [94, [1536.0, 10400.0], 0, 0])
    check(out[1] == [1536.0, 3040.0] and was == (1536.0, 10400.0),
          "5d. ANY agent's point, not only the player's (an NPC's walk to the "
          "corridor boss's y = 10400)", out)
    inside_vals = [1, [2000.0, 1536.0], 0, 0]
    out, was = authsrv._rect_bound_wire_point(st, MOVE, inside_vals)
    check(out is inside_vals and was is None,
          "5e. a point inside: the SAME object back, nothing noted")
    meshed = [1, [9999.0, 9999.0], 0, 0]
    out, was = authsrv._rect_bound_wire_point(
        {"pathmap": _Open(), "map_rect": R}, MOVE, meshed)
    check(out is meshed and was is None,
          "5f. a MESHED instance: the same object back even far past the rect "
          "-- the wire is byte-identical")
    out, was = authsrv._rect_bound_wire_point(
        {"pathmap": None, "map_rect": None}, MOVE, meshed)
    check(out is meshed and was is None,
          "5g. no rect known: the same object back (the historical wire)")
    create = [94, 0, 0, 0, (1536.0, 10400.0), 0]
    out, was = authsrv._rect_bound_wire_point(
        st, authsrv.GAME_SMSG_WORLD_CREATE_AGENT, create)
    check(out is create and was is None,
          "5h. a CREATE is not a grant and is not touched -- the 0914 witness's "
          "assert is the portal refusal's to prevent (section 7)")
    body = SRC[SRC.index("        def send(opcode, values, label, quiet=False):"):]
    first = [ln.strip() for ln in body.splitlines()[1:40]
             if ln.strip() and not ln.strip().startswith("#")]
    check(first[0] == "values, _rect_from = _rect_bound_wire_point(state, "
                      "opcode, values)",
          "5i. LOCK: it is send()'s FIRST statement, so every hook after it "
          "(the sync model, the shadow, the recorder) sees the wire's point",
          first[:2])

    print("\n6. the rect read where the mesh fails, against the real archive")
    try:
        from archive import Archive, file_id_table
        ar = Archive()
    except Exception as exc:                                  # noqa: BLE001
        ar = None
        LEDGER.skip("6a-6e", f"no archive on this machine ({exc})")
    if ar is not None:
        try:
            tbl = file_id_table(ar)
            asc = authsrv.MAP_STATIC_CONFIG[148][0]
            if 0x5F0B3 in tbl:
                LEDGER.skip("6a", f"{ar.path} holds 0x5F0B3 -- the default map "
                            "is not what its client would build")
            else:
                check(authsrv._read_no_mesh_rect(0x5F0B3, ar, tbl)
                      == (maprect.CLIENT_DEFAULT_MAP_RECT, "client-default"),
                      "6a. a file id the archive lacks -> the client's default "
                      "rect, source client-default")
            rect, src = authsrv._read_no_mesh_rect(asc, ar, tbl)
            check(src == "map-params" and rect[0] < rect[2] and rect[1] < rect[3],
                  f"6b. a present file (map 148, 0x{asc:X}) -> its own Map "
                  f"Parameters rect", (rect, src))
            check(round(rect[2] - rect[0]) % 96 == 0
                  and round(rect[3] - rect[1]) % 96 == 0,
                  "6c. and the rect's sides are whole terrain cells (96 u) -- "
                  "the client's own `dims.x * XY_DIST == mapRect.x1 - x0`",
                  rect)
            pm = authsrv.PathingMap.load(asc, archive=ar, table=tbl)
            xs = [v for t in pm.trapezoids for v in (
                t.x_top_left, t.x_top_right, t.x_bottom_left, t.x_bottom_right)]
            ys = [v for t in pm.trapezoids for v in (t.y_top, t.y_bottom)]
            check(rect[0] <= min(xs) and max(xs) <= rect[2]
                  and rect[1] <= min(ys) and max(ys) <= rect[3],
                  f"6d. POSITIVE CONTROL: all {len(pm.trapezoids)} trapezoids of "
                  f"that map's own mesh lie inside the rect its own file declares "
                  f"(a wrong offset or chunk would put four floats of noise here)",
                  (min(xs), max(xs), min(ys), max(ys), rect))
        finally:
            ar.close()
        saved = (dict(authsrv._PATHMAPS), dict(authsrv._MAPRECTS))
        try:
            authsrv._PATHMAPS.pop(0x5F0B3, None)
            authsrv._MAPRECTS.pop(0x5F0B3, None)
            if 0x5F0B3 in tbl:
                LEDGER.skip("6e", "the archive holds 0x5F0B3")
            else:
                pm = authsrv.load_pathmap(0x5F0B3, role="test_nomeshrect")
                check(pm is None and authsrv.no_mesh_rect(0x5F0B3)
                      == (maprect.CLIENT_DEFAULT_MAP_RECT, "client-default"),
                      "6e. load_pathmap's failure RECORDS the rect at the same "
                      "moment, and no_mesh_rect answers from the record")
        finally:
            authsrv._PATHMAPS.clear()
            authsrv._PATHMAPS.update(saved[0])
            authsrv._MAPRECTS.clear()
            authsrv._MAPRECTS.update(saved[1])

    class _Locked:
        @staticmethod
        def load(*a, **k):
            raise PermissionError("[Errno 13] Permission denied: 'Gw.dat'")
    saved = (authsrv.PathingMap, dict(authsrv._PATHMAPS), dict(authsrv._MAPRECTS))
    try:
        authsrv.PathingMap = _Locked
        authsrv._PATHMAPS.pop(0xABCDE, None)
        authsrv.load_pathmap(0xABCDE, role="test_nomeshrect")
        rect, why = authsrv.no_mesh_rect(0xABCDE)
        check(rect is None and "held by the client" in why,
              "6f. an archive the CLIENT holds: no rect, and the reason names it "
              "-- no read is attempted against a locked file", why)
    finally:
        authsrv.PathingMap = saved[0]
        authsrv._PATHMAPS.clear()
        authsrv._PATHMAPS.update(saved[1])
        authsrv._MAPRECTS.clear()
        authsrv._MAPRECTS.update(saved[2])
    check(authsrv.no_mesh_rect(0x7FFFFFF)[0] is None,
          "6g. a file id with no recorded failure has no rect -- never a guess")
    load_at = SRC.index('state["pathmap"] = load_pathmap(spawn[0])')
    tail = SRC[load_at:load_at + 600]
    check('state["map_rect"] = None' in tail
          and "no_mesh_rect(spawn[0])" in tail,
          "6h. LOCK: instance load sets map_rect beside the pathmap, from the "
          "record, never a fresh read")

    print("\n7. the portal: no zoning into a map the archive does not hold")
    cfg = authsrv.MAP_STATIC_CONFIG
    full = {int(v[0]) for v in cfg.values()}
    table_without = {f: 0 for f in full if f != 0x5F0B3}
    got = authsrv.portal_unservable(table_without, r"X:\Gw.dat")
    check(sorted(got) == [168] and "0x5F0B3" in got[168],
          "7a. against an archive without 0x5F0B3, exactly the corridor (168) is "
          "withheld -- 148 and 146 are served", got)
    check(authsrv.portal_unservable({f: 0 for f in full}, r"X:\Gw.dat") == {},
          "7b. an archive holding every file withholds nothing (the slice "
          "archive's case)")

    class _World:
        def __init__(self, rows):
            self._rows = rows

        def rows(self, kind):
            return dict(self._rows) if kind == "portal" else {}
    fake = {900: (0xDEAD, (0.0, 0.0), 0)}
    got = authsrv.portal_unservable({}, "X", static_config=fake, world=_World(
        {"off": {"map": 1, "to_map": 900, "enabled": False}}))
    got2 = authsrv.portal_unservable({}, "X", static_config=fake, world=_World(
        {"on": {"map": 1, "to_map": 900, "enabled": True},
         "loose": {"map": 1, "to_map": 901, "enabled": True}}))
    check(got == {} and sorted(got2) == [900],
          "7c. a DISABLED portal is not scanned, and a destination with no static "
          "config (no file id to look up) is skipped rather than guessed",
          (got, got2))

    row = authsrv.agents.WORLD.rows("portal")["ascalon_to_corridor"]
    saved = (list(authsrv.TRANSFER_HOSTS), authsrv.TRANSFER_PORT,
             dict(authsrv.TRANSFERS_ISSUED), dict(authsrv.TRANSFER_ARRIVALS),
             authsrv.PORTALS, dict(authsrv.PORTAL_UNSERVABLE))
    try:
        authsrv.TRANSFER_HOSTS[:] = ["127.0.0.3", "127.0.0.33"]
        authsrv.TRANSFER_PORT = 6112
        authsrv.PORTALS = True
        inside = (float(row["x"]) + 120.0, float(row["y"]))    # the run's "120 u in"
        outside = (float(row["x"]) + 400.0, float(row["y"]))

        def walk_in(withheld):
            authsrv.PORTAL_UNSERVABLE.clear()
            authsrv.PORTAL_UNSERVABLE.update(withheld)
            sent = []
            send = (lambda op, vals, label="", **kw: sent.append((op, label)))
            state = {"pos": outside, "map_id": 148, "world_id": 777,
                     "player_id": 4242, "plane": 0}
            authsrv.portal_tick(send, state, 1, "127.0.0.3")   # arms it
            state["pos"] = inside
            fired = authsrv.portal_tick(send, state, 1, "127.0.0.3")
            return fired, sent, state

        fired, sent, state = walk_in({})
        check(fired is True and len(sent) == 3,
              "7d. CONTROL: the real ascalon_to_corridor row, walked into from "
              "outside, fires the three-message transfer when 168 is served",
              [l for _o, l in sent])
        fired, sent, state = walk_in({168: "its file 0x5F0B3 is not in X"})
        check(fired is False and not sent
              and state.get("transfer_sent") is None
              and state["portal_armed"].get("ascalon_to_corridor") is False,
              "7e. WITHHELD: the same walk-in sends NOTHING and disarms the "
              "portal, so the player stays on 148", sent)
        again = authsrv.portal_tick(lambda *a, **k: sent.append(a), state, 1,
                                    "127.0.0.3")
        state["pos"] = outside
        authsrv.portal_tick(lambda *a, **k: sent.append(a), state, 1, "127.0.0.3")
        rearmed = state["portal_armed"].get("ascalon_to_corridor")
        state["pos"] = inside
        refire = authsrv.portal_tick(lambda *a, **k: sent.append(a), state, 1,
                                     "127.0.0.3")
        check(again is False and rearmed is True and refire is False and not sent,
              "7f. standing in the circle does not repeat it; leaving re-arms and "
              "walking back in is refused again, still with nothing sent")
    finally:
        authsrv.TRANSFER_HOSTS[:] = saved[0]
        authsrv.TRANSFER_PORT = saved[1]
        authsrv.TRANSFERS_ISSUED.clear()
        authsrv.TRANSFERS_ISSUED.update(saved[2])
        authsrv.TRANSFER_ARRIVALS.clear()
        authsrv.TRANSFER_ARRIVALS.update(saved[3])
        authsrv.PORTALS = saved[4]
        authsrv.PORTAL_UNSERVABLE.clear()
        authsrv.PORTAL_UNSERVABLE.update(saved[5])

    start = SRC.index("    # NOMESH-RECT: and which portal destinations this archive")
    block = SRC[start:start + 800]
    prewarm = SRC.index('print("[map] no --map: no navmesh is pre-warmed')
    check("if not a.no_portals:\n        portal_unservable_scan()" in block
          and start > prewarm,
          "7g. LOCK: main() scans at startup, OUTSIDE the --map branch (the "
          "specimen had no --map), gated on a.no_portals read directly")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
