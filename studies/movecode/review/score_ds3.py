"""Score DSBATCH3-run-registered.txt (MOVECODE-1z-ds.23..32).
usage: score_ds3.py HARNESS_DIR | score_ds3.py --tape GAMESRV_TAPE

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for the wire half of FINDINGS
1z-ds.34 (harness 20261003T130816: c1 = the default capture, c3 via --tape authsrv-20261003T131011-c3.jsonl) and 1z-ds.35
(harness 20261003T164555, with score_ds3b.py). It takes its input as an argument (a harness dir, or --tape a gamesrv
tape) and had no path or sibling import to port. Its W row ("own follows inside a windup") and D rows (player deaths) are the
windup-follow and death-stop exposure counts DEATHWALK is about.

    python studies/movecode/review/score_ds3.py <vault>/captures/harness/20261003T130816
    python studies/movecode/review/score_ds3.py --tape <vault>/captures/gamesrv/authsrv-20261003T131011-c3.jsonl
(<vault> is `python toolkit/vaultpath.py`'s answer; the tape and harness dir are the scorer's argument, not a path it resolves.)
"""
import json
import math
import os
import sys

if sys.argv[1] == "--tape":
    T, gw, H = sys.argv[2], [], None
else:
    H = sys.argv[1]
    rep = json.load(open(os.path.join(H, "report.json"), encoding="utf-8"))
    gw = rep.get("gw_log") or []
    T = [p for p in rep["captures"] if "gamesrv" in p][0]
print("tape", T)
if H:
    print("Q0 asserts", [x[:80] for x in gw if "Assert" in x][:2],
          "| crash", os.path.exists(os.path.join(H, "crash-dialog.txt")))
    print("Q4 Pending:", sum("Pending skill" in x for x in gw))
recs = [json.loads(l) for l in open(T, encoding="utf-8") if l.strip().startswith("{")]
recs.sort(key=lambda r: (r.get("t", 0.0), r.get("seq", 0)))
sent = [x for x in recs if x.get("kind") == "sent"]
dec = [x for x in recs if x.get("kind") == "decoded"]
L = lambda x: x.get("label", "")

# the hold state over the sent stream, transition by transition
hold_ev = [(x["t"], 1 if L(x).startswith("action holds") else 0) for x in sent
           if L(x).startswith("action holds") or L(x).startswith("action released")]


def hold_at(t):
    v = 0
    for tt, s in hold_ev:
        if tt > t:
            break
        v = s
    return v


starts = [x for x in sent if "player swings" in L(x)]
approach_sends = [x for x in sent if L(x).startswith("APPROACH:") or L(x).startswith("APPROACH re-path")]
presses = [x for x in dec if x.get("opcode") == 0x26]

# ---- H-W1 / H-W2
held = sum(hold_at(s["t"] + 0.1) for s in starts)
print(f"\nH-W1 own starts held at +0.1 s: {held} of {len(starts)}"
      f" ({100.0 * held / max(1, len(starts)):.1f} %)  PREDICT >= 99 %")
walkins, bad_batch = [], []
for s in starts:
    prev_p = max((p["t"] for p in presses if p["t"] <= s["t"]), default=None)
    if prev_p is None:
        continue
    if any(prev_p <= a["t"] < s["t"] and not L(a).startswith("APPROACH re-path") for a in approach_sends):
        walkins.append(s)
        batch = [L(x) for x in sent if s["t"] - 0.001 <= x["t"] <= s["t"] + 0.005]
        if any("AGENT_STOP_MOVING" in b and "APPROACH HALT" not in b for b in batch):
            bad_batch.append(round(s["t"], 3))
wi_held = sum(hold_at(s["t"] + 0.1) for s in walkins)
print(f"H-W2 walk-in starts {len(walkins)} (floor 5), held {wi_held}; batches with a melee 0x0028: {bad_batch}")

# ---- H-W3 / H-W4: answers to inputs under a hold
mov = [d for d in dec if d.get("opcode") == 0x3D and (d.get("values") or [0] * 5)[4]]
rel_reports, zero_after_rel = 0, []
for d in mov:
    if not hold_at(d["t"] - 1e-6):
        continue
    ans = [x for x in sent if d["t"] <= x["t"] <= d["t"] + 0.03]
    if any(L(x).startswith("action released") for x in ans):
        rel_reports += 1
        if any("ZERO LEAD" in L(x) for x in ans):
            zero_after_rel.append(round(d["t"], 3))
print(f"H-W3 key reports releasing a hold: {rel_reports} (floor 5); ZERO LEAD among their answers: "
      f"{zero_after_rel}  ABORT IF ANY")
clicks = [d for d in dec if d.get("opcode") == 0x3E]
held_clicks, unanswered = 0, []
for c in clicks:
    if not hold_at(c["t"] - 1e-6):
        continue
    held_clicks += 1
    if not any(c["t"] <= x["t"] <= c["t"] + 0.1 and x.get("opcode") in (0x29, 0x2A) for x in sent):
        unanswered.append(round(c["t"], 3))
print(f"H-W4 clicks under a hold: {held_clicks} (floor 2); unanswered in 0.1 s: {unanswered}  ABORT IF ANY")
land_rel = [round(x["t"], 3) for x in sent if L(x).startswith("action released")
            and ("swing landed" in L(x) or "shot is away" in L(x))]
print(f"H-W5 releases at a landing / launch: {land_rel}  PREDICT []")

# ---- W: no own follow between a start and its close
mid = []
for s in starts:
    close = next((x["t"] for x in sent if x["t"] > s["t"] and x.get("opcode") == 0x9F
                  and ("attack_stopped" in L(x) or "landed" in L(x) or "lands" in L(x))), None)
    fin = next((x["t"] for x in sent if x["t"] > s["t"] and "FINISHED" in L(x).upper()), None)
    end = min([t for t in (close, fin, s["t"] + 1.2) if t is not None])
    f = [round(a["t"], 3) for a in approach_sends if s["t"] < a["t"] < end - 0.001]
    if f:
        mid.append((round(s["t"], 3), f))
print(f"W   own follows inside a windup: {mid}  PREDICT []")

# ---- N3
ends = [x for x in sent if "PRESS ENDS THE WALK" in L(x)]
spared = [x for x in recs if x.get("kind") == "press_spared"]
print(f"N3  press_spared rows {len(spared)} (floor 2); PRESS ENDS THE WALK sends {len(ends)}: "
      f"{[round(x['t'], 3) for x in ends][:10]} (each should follow a click or interact, not our follow)")

# ---- K-B / K-A
rr = [x for x in recs if x.get("kind") == "router_route"]
live = [x for x in rr if x.get("arm") == "live-key"]
drops = [x for x in rr if x.get("verdict") == "kbd-drop"]
print(f"K-B live-key answers {len(live)} (floor 3); kbd-drop rows {len(drops)} "
      f"{[round(x['t'], 3) for x in drops]}  PREDICT 0 drops")
reps = [d for d in dec if d.get("opcode") in (0x3D, 0x47)]
for a in live:
    nxt = next((d for d in mov if d["t"] > a["t"]), None)
    relead = None
    if nxt is not None and nxt["t"] - a["t"] <= 2.5:
        relead = next((round(x["t"] - nxt["t"], 4) for x in sent
                       if nxt["t"] <= x["t"] <= nxt["t"] + 0.015 and "KBD LEAD" in L(x)), None)
    win = [d for d in reps if a["t"] - 1.0 <= d["t"] <= a["t"] + 2.5]
    worst = 0.0
    for p, q in zip(win, win[1:]):
        pp, qq = (p.get("values") or [0, [0, 0]])[1], (q.get("values") or [0, [0, 0]])[1]
        step = math.hypot(qq[0] - pp[0], qq[1] - pp[1]) - 300.0 * max(0.0, q["t"] - p["t"])
        if q["t"] >= a["t"]:
            worst = max(worst, step)
    print(f"    live-key {a['t']:.3f} age {a.get('keyboard_age')}: next key report "
          f"{'none' if nxt is None else round(nxt['t'] - a['t'], 3)} s, its KBD LEAD at {relead}; "
          f"worst unexplained report step {worst:.0f} u  REFUTED IF >= 299")
r10 = [x for x in sent if x.get("opcode") == 0x2B and "1.0 = 288" in L(x)]
nr = 0
miss = []
_seen = set()
for r in r10:
    nxt = next((d for d in mov if d["t"] > r["t"]), None)
    if nxt is None or nxt["values"][4] in (1,) or id(nxt) in _seen:
        continue
    _seen.add(id(nxt))
    nr += 1
    if not any(nxt["t"] <= x["t"] <= nxt["t"] + 0.015 and "KBD SPEED-TRUTH" in L(x) for x in sent):
        miss.append(round(nxt["t"], 3))
print(f"K-A non-run key reports after a router [1.0]: {nr} (floor 2); without KBD SPEED-TRUTH: {miss}")

# ---- SK / I / E / D
inst = [x for x in sent if "cast-stop SKIPPED" in L(x)]
sk_stops = [x for x in sent if "ends the swing" in L(x)]
print(f"SK/I skill [3]s {len(sk_stops)} at {[round(x['t'], 3) for x in sk_stops]} (each must be mid-windup)")
for x in sk_stops:
    s = max((y["t"] for y in starts if y["t"] <= x["t"]), default=None)
    print(f"     [3] {x['t']:.3f}: last start {None if s is None else round(x['t'] - s, 3)} s before")
pins_at_skill = [round(x["t"], 3) for x in sent if "CAST-STOP PIN" in L(x)]
print(f"     cast-stop pins {pins_at_skill}")
kills = [x for x in sent if L(x).startswith("KILL the player")]
for k in kills:
    s = max((y["t"] for y in starts if y["t"] <= k["t"]), default=None)
    nxt = [L(x) for x in sent if k["t"] <= x["t"] <= k["t"] + 0.003][:3]
    print(f"D   death {k['t']:.3f}: last start {None if s is None else round(k['t'] - s, 3)} s before; "
          f"batch head {nxt}")
escs = [d for d in dec if d.get("opcode") == 0x28]
for e in escs:
    ans = [L(x) for x in sent if e["t"] <= x["t"] <= e["t"] + 0.03 and x.get("opcode") == 0x9F]
    print(f"E   Esc {e['t']:.3f}: {ans}")

# ---- B2a
ap = [x for x in recs if x.get("kind") == "approach" and x.get("act") == "send"]
fo = [x for x in ap if "frame_origin" in x]
diff = [round(math.hypot(x["origin"][0] - x["frame_origin"][0], x["origin"][1] - x["frame_origin"][1]), 1)
        for x in fo]
print(f"\nB2a approach sends {len(ap)}, with frame_origin {len(fo)}; |origin - frame| {diff}")
