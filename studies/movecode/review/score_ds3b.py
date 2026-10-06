"""Score DSBATCH3B-run-registered.txt's new items (N3, held clicks, W) on one gamesrv tape.
usage: score_ds3b.py GAMESRV_TAPE

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); the follow-up scorer for DSBATCH3B's N3, held-click and W
items, published with score_ds3.py as FINDINGS 1z-ds.35 (harness 20261003T164555, tape authsrv-20261003T164631-c1.jsonl). Input is
one gamesrv tape as an argument; no path or sibling import to port.
"""
import json
import sys

T = sys.argv[1]
recs = [json.loads(l) for l in open(T, encoding="utf-8") if l.strip().startswith("{")]
recs.sort(key=lambda r: (r.get("t", 0.0), r.get("seq", 0)))
sent = [x for x in recs if x.get("kind") == "sent"]
dec = [x for x in recs if x.get("kind") == "decoded"]
L = lambda x: x.get("label", "")
print("tape", T)

follows = [x for x in recs if x.get("kind") == "approach" and x.get("act") == "send"]
presses = [d for d in dec if d.get("opcode") == 0x26]
starts = [x for x in sent if "player swings" in L(x)]
spared_rows = [x for x in recs if x.get("kind") == "press_spared"]

# ---- N3: every press on the target of our last follow, with nothing of the player's in between
print("\nN3 same-target presses after our own follow:")
n_same, n_end, n_row = 0, 0, 0
for p in presses:
    tgt = (p.get("values") or [0, 0])[1]
    f = max((x for x in follows if x["t"] < p["t"]), key=lambda x: x["t"], default=None)
    if f is None or f.get("target") != tgt:
        continue
    between = [d for d in dec if f["t"] < d["t"] < p["t"]
               and (d.get("opcode") == 0x3E
                    or (d.get("opcode") == 0x3D and (d.get("values") or [0] * 5)[4])
                    or (d.get("opcode") == 0x26 and (d.get("values") or [0, 0])[1] != tgt))]
    if between:
        continue
    n_same += 1
    win = [x for x in sent if p["t"] <= x["t"] <= p["t"] + 0.02]
    ended = any("PRESS ENDS THE WALK" in L(x) for x in win)
    row = next((x for x in spared_rows if p["t"] <= x["t"] <= p["t"] + 0.02), None)
    n_end += ended
    n_row += row is not None
    nxt = next((s["t"] for s in starts if s["t"] >= p["t"]), None)
    swung_before = any(f["t"] < s["t"] < p["t"] for s in starts)
    print(f"  {p['t']:8.3f} tgt {tgt} follow@{f['t']:.3f} (+{p['t'] - f['t']:.2f} s, run {f.get('run')})"
          f" {'after a swing' if swung_before else 'walking up'}:"
          f" ENDS={ended} spared_row={None if row is None else (row.get('arrived'), row.get('age'))}"
          f" next swing {None if nxt is None else round(nxt - p['t'], 3)} s"
          f" | sent {[L(x)[:40] for x in win][:4]}")
print(f"N3 summary: {n_same} same-target presses; PRESS ENDS THE WALK on {n_end} (PREDICT 0);"
      f" press_spared rows {n_row} (registered floor 3; arrived {sum(bool(x.get('arrived')) for x in spared_rows)},"
      f" not-yet-eta {sum(not x.get('arrived') for x in spared_rows)} of {len(spared_rows)} rows on the tape)")

# ---- H-W4 detail: clicks under a hold, the answer's first frames
hold_ev = [(x["t"], 1 if L(x).startswith("action holds") else 0) for x in sent
           if L(x).startswith("action holds") or L(x).startswith("action released")]


def hold_at(t):
    v = 0
    for tt, s in hold_ev:
        if tt > t:
            break
        v = s
    return v


print("\nH-W4 clicks under a hold:")
for c in (d for d in dec if d.get("opcode") == 0x3E):
    if not hold_at(c["t"] - 1e-6):
        continue
    since = max((s["t"] for s in starts if s["t"] <= c["t"]), default=None)
    ans = [x for x in sent if c["t"] <= x["t"] <= c["t"] + 0.1]
    first_mv = next((x for x in ans if x.get("opcode") in (0x29, 0x2A)), None)
    rel = next((x for x in ans if L(x).startswith("action released")), None)
    print(f"  {c['t']:8.3f} ({None if since is None else round(c['t'] - since, 3)} s after a start):"
          f" release {None if rel is None else round(rel['t'] - c['t'], 4)}"
          f" move {None if first_mv is None else (hex(first_mv['opcode']), round(first_mv['t'] - c['t'], 4))}"
          f" release-first {rel is not None and first_mv is not None and rel['t'] <= first_mv['t']}"
          f" | {[L(x)[:36] for x in ans][:4]}")

# ---- W: a re-approach riding a landing
print("\nW re-approaches at a landing:")
for f in follows:
    batch = [x for x in sent if f["t"] - 0.01 <= x["t"] <= f["t"] + 0.005]
    if any("landed" in L(x) or "LATE HIT" in L(x).upper() for x in batch):
        print(f"  {f['t']:8.3f} tgt {f.get('target')} run {f.get('run')} | {[L(x)[:40] for x in batch]}")
