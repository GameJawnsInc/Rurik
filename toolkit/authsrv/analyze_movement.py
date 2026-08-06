"""Measure what the client actually says when it moves.

studies/movement/FINDINGS.md ends with two questions no reference can answer,
because no reference server handles 0x003D at all -- OpenTyria has no handler and
its table leaves the opcode unnamed:

  1. Is the second Vec2f on 0x003D a UNIT VECTOR or a DISPLACEMENT?
     Our code does `dest = pos + heading` (authsrv.py:701-703), which is only
     sensible if it is a displacement in world units. If it is a unit vector, we
     have been asking the character to walk one world unit per message, and the
     walk only appears to work because the client re-sends continuously.
     Magnitudes clustered at 1.0 settle it one way; anything else settles it the
     other.

  2. Is the trailing DWORD a boolean "moving" flag or an enum?
     We test it for truthiness. GWLP-R names the same field `movementType`.
     Truthiness over an enum is a guess wearing a boolean's clothes.

Both are answered by our own capture, which is the only ground truth we have.

The script reads nothing but what the server already recorded, so it can be run
against a session that has already happened. Field names come from the schema,
not from any semantic table, because for GAME_CMSG we do not have one.

    python toolkit/authsrv/analyze_movement.py
    python toolkit/authsrv/analyze_movement.py --capture <path.jsonl>
"""

import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "schema"))
sys.path.insert(0, os.path.dirname(HERE))
from codec import Codec  # noqa: E402
import vaultpath  # noqa: E402

VAULT = vaultpath.vault_path("captures", "authsrv")

TURN_TO_DIRECTION = 0x003D
MOVE_TO_COORD = 0x003E
LAST_POS_BEFORE_MOVE_CANCELED = 0x0047

# What one server tick advances us, for scale. Straight from authsrv.py.
DEFAULT_RUN_SPEED = 288.0
TICK_SECONDS = 0.05


def newest_captures():
    files = sorted(glob.glob(os.path.join(VAULT, "authsrv-*.jsonl")),
                   key=os.path.getmtime, reverse=True)
    return files


def load(path):
    events = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass          # a half-flushed final line is normal on a live run
    return events


def is_pair(v):
    return isinstance(v, (list, tuple)) and len(v) == 2 \
        and all(isinstance(x, (int, float)) for x in v)


def describe_shape(codec, opcode):
    """Field types from the schema, so we label slots without inventing names."""
    try:
        fields = codec.fields_for("GAME_CMSG", opcode)
    except Exception:
        return None
    return [f["type"] for f in fields]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", help="a specific authsrv-*.jsonl")
    args = ap.parse_args()

    paths = [args.capture] if args.capture else newest_captures()
    if not paths:
        print(f"no captures under {VAULT}")
        return 1

    codec = Codec()

    # A game session is whichever capture actually carries movement.
    chosen, events = None, None
    for p in paths:
        evs = load(p)
        if any(e.get("kind") == "decoded" and e.get("opcode") == TURN_TO_DIRECTION
               for e in evs):
            chosen, events = p, evs
            break
    if chosen is None:
        print(f"no capture contains 0x003D. Looked at {len(paths)} file(s);")
        print(f"newest is {os.path.basename(paths[0])}.")
        print("Walk around with WASD while connected, then re-run.")
        return 1

    print(f"capture: {os.path.basename(chosen)}")
    shape = describe_shape(codec, TURN_TO_DIRECTION)
    print(f"0x003D schema shape: {shape}")
    print()

    turns = [e for e in events
             if e.get("kind") == "decoded" and e.get("opcode") == TURN_TO_DIRECTION]
    moves = [e for e in events
             if e.get("kind") == "decoded" and e.get("opcode") == MOVE_TO_COORD]
    cancels = [e for e in events
               if e.get("kind") == "decoded"
               and e.get("opcode") == LAST_POS_BEFORE_MOVE_CANCELED]

    print(f"0x003D  {len(turns):5d}   0x003E  {len(moves):5d}   "
          f"0x0047  {len(cancels):5d}")
    if not turns:
        return 1

    # Locate the two Vec2f slots without assuming an index. The schema says
    # there are exactly two; the first is the client's own position, the second
    # is the thing in question.
    sample = turns[0]["values"]
    vec_slots = [i for i, v in enumerate(sample) if is_pair(v)]
    scalar_slots = [i for i, v in enumerate(sample) if not is_pair(v)]
    print(f"value slots: {len(sample)}  vec2 at {vec_slots}  "
          f"scalar at {scalar_slots}")
    if len(vec_slots) < 2:
        print("expected two Vec2f slots; the schema shape may have changed.")
        return 1
    pos_slot, dir_slot = vec_slots[0], vec_slots[1]
    print(f"reading slot {pos_slot} as the client's position, "
          f"slot {dir_slot} as the contested vector")
    print()

    # ---- Question 1: unit vector, or displacement? --------------------------
    mags = []
    for e in turns:
        v = e["values"][dir_slot]
        mags.append(math.hypot(v[0], v[1]))
    mags_sorted = sorted(mags)
    n = len(mags)

    def pct(p):
        return mags_sorted[min(n - 1, int(p * n))]

    print("1. magnitude of the contested vector")
    print(f"   n={n}  min={mags_sorted[0]:.4f}  p50={pct(0.50):.4f}  "
          f"p90={pct(0.90):.4f}  max={mags_sorted[-1]:.4f}")
    near_unit = sum(1 for m in mags if abs(m - 1.0) < 0.01)
    near_zero = sum(1 for m in mags if m < 0.01)
    print(f"   within 1% of 1.0: {near_unit}/{n}"
          f"   effectively zero: {near_zero}/{n}")
    step = DEFAULT_RUN_SPEED * TICK_SECONDS
    if near_unit > 0.9 * (n - near_zero) and near_unit:
        print(f"   -> UNIT VECTOR. `dest = pos + heading` asks for a 1-unit walk,")
        print(f"      while one tick steps {step:.1f} units. Arrival every tick.")
    elif mags_sorted[-1] > 10:
        print("   -> DISPLACEMENT (or something scaled). Not a unit vector.")
    else:
        print("   -> inconclusive; see the distribution above.")
    print()

    # ---- Question 2: boolean, or enum? -------------------------------------
    # How much the player actually turned between reports. Without this, a high
    # rate of keyboard MOVE_TO_POINT reads as a broken throttle when it may just
    # be someone swinging the camera around.
    angles = []
    for a, b in zip(turns, turns[1:]):
        va, vb = a["values"][dir_slot], b["values"][dir_slot]
        m = math.hypot(*va) * math.hypot(*vb)
        if m > 0:
            dot = (va[0] * vb[0] + va[1] * vb[1]) / m
            angles.append(math.degrees(math.acos(max(-1.0, min(1.0, dot)))))
    if angles:
        asort = sorted(angles)
        over5 = sum(1 for x in angles if x > 5.0)
        print(f"1b. turn between consecutive reports: p50={asort[len(asort) // 2]:.1f}deg"
              f"  max={asort[-1]:.1f}deg   over 5deg: {over5}/{len(angles)}")
        print()

    print("2. the trailing scalar slots")
    for s in scalar_slots:
        vals = {}
        for e in turns:
            v = e["values"][s]
            key = v if isinstance(v, (int, str)) else repr(v)
            vals[key] = vals.get(key, 0) + 1
        top = sorted(vals.items(), key=lambda kv: -kv[1])[:8]
        distinct = len(vals)
        rendered = "  ".join(f"{k}x{c}" for k, c in top)
        verdict = ""
        if s == scalar_slots[-1]:
            if distinct > 2:
                verdict = "   <- MORE THAN TWO VALUES: an enum, not a boolean"
            elif distinct == 2:
                verdict = "   <- two values only; boolean still possible"
        print(f"   slot {s}: {distinct} distinct   {rendered}{verdict}")
    print()

    # ---- Free extra: does the client's own position advance? ---------------
    # If the client is animating a walk it reports a smoothly advancing
    # position. If we are teleporting it, its reports jump.
    print("3. the client's own reported position, between consecutive 0x003D")
    deltas, dts = [], []
    for a, b in zip(turns, turns[1:]):
        pa, pb = a["values"][pos_slot], b["values"][pos_slot]
        d = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
        dt = b.get("t", 0) - a.get("t", 0)
        if 0 < dt < 1.0:          # ignore gaps where the player stood still
            deltas.append(d)
            dts.append(dt)
    if deltas:
        ds = sorted(deltas)
        m = len(ds)
        mean_dt = sum(dts) / len(dts)
        print(f"   n={m}  min={ds[0]:.2f}  p50={ds[m // 2]:.2f}  "
              f"max={ds[-1]:.2f} units")
        print(f"   mean gap {mean_dt * 1000:.0f} ms  ->  "
              f"{ds[m // 2] / mean_dt:.0f} units/sec at the median")
        print(f"   for reference, DEFAULT_RUN_SPEED is {DEFAULT_RUN_SPEED}")
    else:
        print("   not enough consecutive samples")
    print()

    # How far apart the two simulations had drifted by the time the client
    # stopped. This is the number that says whether upstream's 100.0 tolerance
    # is right for us, and whether our run speed matches the client's.
    reports = [e for e in events if e.get("kind") == "position_report"]
    if reports:
        ds = sorted(r["drift"] for r in reports)
        k = len(ds)
        accepted = sum(1 for r in reports if r.get("accepted"))
        print("3b. drift between our position and the client's, at each stop")
        print(f"   n={k}  min={ds[0]:.1f}  p50={ds[k // 2]:.1f}  "
              f"p90={ds[min(k - 1, int(0.9 * k))]:.1f}  max={ds[-1]:.1f} units")
        print(f"   accepted {accepted}/{k}; the rest were corrected (a teleport)")
        if ds[k // 2] > 60:
            print("   -> the two simulations disagree badly even at the median.")
            print("      Suspect the run speed, not the tolerance.")
        print()

    print("4. what we sent back while this was happening")
    sent = {}
    for e in events:
        if e.get("kind") == "sent":
            sent[e.get("label", "?")] = sent.get(e.get("label", "?"), 0) + 1
    for label, count in sorted(sent.items(), key=lambda kv: -kv[1])[:10]:
        print(f"   {count:5d}  {label}")
    movetopoint = sum(c for l, c in sent.items() if "MOVE_TO_POINT" in l)
    updatepos = sum(c for l, c in sent.items() if "UPDATE_POSITION" in l)
    print()
    keyed = sum(c for l, c in sent.items() if "MOVE_TO_POINT" in l and "key" in l)
    print(f"   MOVE_TO_POINT {movetopoint} (keyboard {keyed}, click "
          f"{movetopoint - keyed})   AGENT_UPDATE_POSITION {updatepos}")
    if turns and keyed == 0:
        print("   -> every MOVE_TO_POINT answered a click. Keyboard movement")
        print("      produced none, so the client was never told to walk.")
    elif keyed:
        per_turn = keyed / len(turns)
        print(f"   -> {keyed} keyboard legs over {len(turns)} reports "
              f"({per_turn:.2f} per report).")
        big = sum(1 for x in angles if x > 5.0) if angles else 0
        if keyed > big * 1.25 + 3:
            print(f"      More legs ({keyed}) than real direction changes ({big}):")
            print("      the throttle is not biting, or something else is resetting it.")
        else:
            print(f"      Tracks the {big} real direction changes (>5deg), which")
            print("      is the intent -- a turning player earns a new leg.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
