"""MOVECODE-1z-v retrodiction: replay a gamesrv capture's clicks through the
router as it now ships, from the router's OWN origin model (the integrator
walking the last granted leg at 288 u/s, reset by every accepted report), and
census the verdicts. No free parameter: the click's own geometry decides.

Also measures the two conditions' EXPOSURE on this capture:
  (a) how many answers were multi-leg or clip-fallback (the record would have
      differed from the raw chord) and how many presses landed inside one;
  (b) how many verbatim answers' field 4 differ between the frozen report
      plane and the mesh under the modelled sync copy.

Usage: python studies/movecode/review/clickretro.py <capture.jsonl> [--map 146]
(MOVECODE-1z-v, FINDINGS sec.1z-v.2. The map id is the instance's
MAP_UPDATE_CURRENT -- 146 for the operator's 2026-09-03 sessions -- not the
`version` row's login map, 1z-u.6.)
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# THIS tree's authsrv.py (studies/movecode/review -> the repo root), never a
# sibling worktree's: a stale tree returns a confident census from an old
# router. RURIK_TREE overrides for a deliberate cross-tree replay.
ROOT = os.environ.get("RURIK_TREE") or os.path.abspath(
    os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
import authsrv                                                  # noqa: E402

RUN = authsrv.DEFAULT_RUN_SPEED


class Rec:
    def __init__(self):
        self.rows = []

    def event(self, kind, **kw):
        kw["kind"] = kind
        self.rows.append(kw)


class Send:
    def __init__(self):
        self.sent = []

    def __call__(self, opcode, payload, label="", quiet=False):
        self.sent.append((opcode, payload, label))


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("--map", type=int, default=None,
                    help="map id (default: the capture's MAP_UPDATE_CURRENT)")
    a = ap.parse_args()
    rows = load(a.capture)
    flags = next(r for r in rows if r.get("kind") == "flags")
    print(f"capture flags: ROUTER={flags.get('ROUTER')} "
          f"KBD_SYNC_LEAD_ON={flags.get('KBD_SYNC_LEAD_ON')} "
          f"CLICK_ECHO={flags.get('CLICK_ECHO')}")
    map_id = a.map
    if map_id is None:
        for r in rows:
            if r.get("kind") == "sent" and "MAP_UPDATE_CURRENT" in str(
                    r.get("label", "")) + str(r.get("name", "")):
                v = r.get("values") or []
                if v:
                    map_id = int(v[0])
                    break
    if map_id is None:
        raise SystemExit("no MAP_UPDATE_CURRENT in the capture; pass --map")
    cfg = authsrv.MAP_STATIC_CONFIG[map_id]
    fid, spawn, spawn_plane = cfg[0], cfg[1], cfg[2]
    print(f"map {map_id}: file 0x{fid:X}, spawn {spawn} plane {spawn_plane}")
    pm = authsrv.load_pathmap(fid)
    if pm is None:
        raise SystemExit("no mesh -- the router would fall through here")

    # state, seeded as instance bring-up seeds it
    state = {"pathmap": pm, "pos": tuple(spawn), "plane": spawn_plane,
             "dest": None, "kbd_moving_at": None, "grant_pending": None,
             "sync_from": tuple(spawn), "sync_to": None, "sync_at": 0.0,
             "client_pos": None, "declared_speed_base": RUN}
    authsrv.ROUTER = True

    # the events in time order: clicks (decoded 0x3E), reports, stops, presses
    clicks = [r for r in rows if r.get("kind") == "decoded"
              and r.get("opcode") == 0x3E]
    reports = [r for r in rows if r.get("kind") == "position_report"]
    presses = [r for r in rows if r.get("kind") == "decoded"
               and r.get("opcode") == 0x26]
    stops = [r for r in rows if r.get("kind") == "decoded"
             and r.get("opcode") == 0x47]
    kbd_reports = [r for r in rows if r.get("kind") == "decoded"
                   and r.get("opcode") == 0x3D]
    print(f"clicks {len(clicks)}, reports {len(reports)} (0x3D rows "
          f"{len(kbd_reports)}), stops {len(stops)}, presses {len(presses)}")

    events = ([("click", r["t"], r) for r in clicks]
              + [("report", r["t"], r) for r in reports]
              + [("stop", r["t"], r) for r in stops]
              + [("press", r["t"], r) for r in presses])
    events.sort(key=lambda e: e[1])

    # the integrator: walk `pos` toward `dest` at RUN u/s between events
    last_t = 0.0

    def advance(t):
        nonlocal last_t
        dt = max(t - last_t, 0.0)
        last_t = t
        d = state.get("dest")
        if not d:
            return
        px, py = state["pos"]
        dx, dy = d[0] - px, d[1] - py
        dist = math.hypot(dx, dy)
        step = RUN * dt
        if dist <= step:
            state["pos"], state["dest"] = (float(d[0]), float(d[1])), None
        else:
            state["pos"] = (px + dx / dist * step, py + dy / dist * step)

    verdicts = {}
    n_wp_hist = {}
    plane4_diff = 0
    plane4_rows = 0
    press_in_chain = 0
    press_total = 0
    chain_live = False
    per_click = []
    t_kbd = None
    for kind, t, r in events:
        advance(t)
        if kind == "report":
            state["pos"] = tuple(r["ours"]) if r.get("accepted") else state["pos"]
            if r.get("accepted"):
                state["client_pos"] = tuple(r["reported"])
                state["plane"] = int(r.get("plane", state["plane"]))
                state["dest"] = None
            state["kbd_moving_at"] = t          # the 0x3D arm arms the latch
            t_kbd = t
            chain_live = False
            continue
        if kind == "stop":
            state["kbd_moving_at"] = None
            state["dest"] = None
            chain_live = False
            continue
        if kind == "press":
            press_total += 1
            if chain_live:
                press_in_chain += 1
            chain_live = False
            continue
        # a click: the router's own kbd-drop reads the latch by age against
        # the click's instant, so re-express the stamp relative to `t`
        import time as _t
        now = _t.time()
        kb = state.get("kbd_moving_at")
        state["kbd_moving_at"] = None if kb is None else now - (t - kb)
        state["sync_at"] = now - (t - state.get("_sync_t", t))
        dest = r["values"][1]
        dest_plane = int(r["values"][2])
        cur_plane = int(state["plane"])
        send, rec = Send(), Rec()
        handled = authsrv.router_answer_click(
            send, state, 1, rec, dest, dest_plane, cur_plane,
            dest_plane, cur_plane)
        state["kbd_moving_at"] = kb
        row = next((x for x in rec.rows if x["kind"] == "router_route"), None)
        v = row["verdict"] if row else ("fallthrough" if not handled else "?")
        verdicts[v] = verdicts.get(v, 0) + 1
        if row and row.get("n_wp"):
            n_wp_hist[row["n_wp"]] = n_wp_hist.get(row["n_wp"], 0) + 1
        if v == "verbatim":
            plane4_rows += 1
            if row.get("plane4") != row.get("plane4_report"):
                plane4_diff += 1
        chain_live = v == "routed" and (row.get("n_wp") or 1) > 1
        # the sync model follows the grant the router put on the wire
        for op, payload, _l in send.sent:
            if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT:
                state["sync_from"] = tuple(state.get("sync_from") or spawn)
                sf = authsrv._sync_position(state, now)
                state["sync_from"], state["sync_to"] = sf, tuple(payload[1])
                state["_sync_t"] = t
        d = math.hypot(dest[0] - state["pos"][0], dest[1] - state["pos"][1])
        per_click.append((round(t, 2), v, row.get("n_wp") if row else None,
                          round(d, 1), row.get("reason") if row else None))
    print()
    print("verdicts:", verdicts)
    print("n_wp histogram (routed):", n_wp_hist)
    print(f"(a) exposure: multi-leg or fallback answers = "
          f"{sum(c for k, c in n_wp_hist.items() if k > 1) + verdicts.get('clip-fallback', 0)}; "
          f"presses inside a live chain = {press_in_chain} of {press_total}")
    print(f"(b) exposure: verbatim rows {plane4_rows}, field 4 differs from "
          f"the report plane on {plane4_diff}")
    print()
    print("t        verdict        n_wp  dist_from_origin  reason")
    for t, v, n, d, why in per_click:
        print(f"{t:7.2f}  {v:13s}  {str(n):4s}  {d:8.1f}          {why or ''}")


if __name__ == "__main__":
    main()
