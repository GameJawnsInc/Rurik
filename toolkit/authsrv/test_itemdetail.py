r"""Five GAME_SMSG names from the 2026-08-22 static pass, vs ArenaNet's own wire.

    python toolkit/authsrv/test_itemdetail.py

The names (ITEM_LOW_DETAIL 0x015E, ITEM_HIGH_DETAIL 0x0161, ITEM_UPDATE_EQUIP_SET
0x0147, ITEM_SET_ACTIVE_EQUIP_SET 0x0148, AGENT_SET_MODEL_SCALE 0x009A) rest on
binary reads recorded in `studies/smsgnames/FINDINGS.md` 9 and in each
`schema/overrides.json` why. This file holds the half the corpus can arbitrate --
invariants the recorded traffic could have violated and did not, so a `.raw` in
the vault can take a name back. The binary-side claims (builder field map, the
IsDetailHigh bit, assert text) are NOT re-checked here; that is clientscan ground.

Counts are pinned as FLOORS (the corpus grows); per-message invariants are pinned
as zero-violation over everything decoded.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks       # noqa: E402
import tape         # noqa: E402
import vaultpath    # noqa: E402
from codec import Codec  # noqa: E402

# Floor set from a real green run (19 checks, 2026-08-22).
LEDGER = checks.Ledger("item detail / equip set / model scale names", floor=19)
check = checks.adopt(LEDGER)

LOW, HIGH = 0x015E, 0x0161
STREAM, UPD, ACT = 0x0144, 0x0147, 0x0148
SCALE = 0x009A
TERMINATOR = 0xC0000000

# ---------------------------------------------------------------- section 1
print("== 1. the names these invariants defend are the names the schema carries ==")
ROOT = os.path.dirname(os.path.dirname(HERE))
with open(os.path.join(ROOT, "schema", "overrides.json"), encoding="utf-8") as fh:
    g = json.load(fh)["channels"]["GAME_SMSG"]
for key, name in (("350", "ITEM_LOW_DETAIL"), ("353", "ITEM_HIGH_DETAIL"),
                  ("327", "ITEM_UPDATE_EQUIP_SET"),
                  ("328", "ITEM_SET_ACTIVE_EQUIP_SET"),
                  ("154", "AGENT_SET_MODEL_SCALE")):
    check(g.get(key, {}).get("name") == name,
          f"overrides {key} is {name}",
          f"found {g.get(key, {}).get('name')!r}")

# ---------------------------------------------------------------- the walk
try:
    live = vaultpath.require_dir("captures", "live", why="the name invariants")
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("corpus sections", f"vault unavailable: {exc}")
    sys.exit(LEDGER.verdict())

codec = Codec()
n = collections.Counter()
q_hist = collections.Counter()
sets_hist = collections.Counter()
pair_shape = collections.Counter()
scale_tops = collections.Counter()

for stamp in sorted(os.listdir(live)):
    cap = os.path.join(live, stamp)
    if not os.path.isdir(cap):
        continue
    for chan in tape.channel_files(cap):
        try:
            _i, events = tape.load_tape(cap, chan["connection"])
            msgs, _r = tape.decode_all(events, codec, "GAME_SMSG", 0)
        except Exception:                                   # noqa: BLE001
            continue
        declared, invkeys = set(), set()
        for _t, op, v in msgs:
            if op in (LOW, HIGH) and len(v) > 1:
                declared.add(int(v[1]))
            elif op == STREAM and len(v) > 1:
                invkeys.add(int(v[1]))

        for _t, op, v in msgs:
            if op == LOW and len(v) > 9:
                n["low"] += 1
                if int(v[2]) & 0x80000000:
                    n["low_topbit"] += 1
            elif op == HIGH and len(v) > 13:
                n["high"] += 1
                n["high_extra_field"] += len(v) > 14
                if int(v[2]) & 0x80000000:
                    n["high_topbit"] += 1
                q_hist[int(v[11])] += 1
                for row in v[13]:
                    w = int(row[0]) if isinstance(row, (list, tuple)) else int(row)
                    n["code_dwords"] += 1
                    if (w & 0xFFFFFFFF) == TERMINATOR:
                        n["terminators_on_wire"] += 1
            elif op == UPD and len(v) > 4:
                n["upd"] += 1
                sets_hist[int(v[2])] += 1
                n["upd_set_oob"] += int(v[2]) >= 4
                n["upd_key_undeclared"] += int(v[1]) not in invkeys
                a, b = int(v[3]), int(v[4])
                for iid in (a, b):
                    if iid:
                        n["upd_item_refs"] += 1
                        n["upd_item_undeclared"] += iid not in declared
                pair_shape["both" if (a and b) else
                           ("A_only" if a else ("B_only" if b else "empty"))] += 1
            elif op == ACT and len(v) > 2:
                n["act"] += 1
                n["act_set_oob"] += int(v[2]) >= 4
                n["act_key_undeclared"] += int(v[1]) not in invkeys
            elif op == SCALE and len(v) > 2:
                n["scale"] += 1
                val = int(v[2]) & 0xFFFFFFFF
                n["scale_lowbits"] += bool(val & 0xFFFFFF)
                scale_tops[val >> 24] += 1

# ---------------------------------------------------------------- section 2
print("== 2. the item-detail pair (0x015E / 0x0161) ==")
check(n["low"] >= 4210 and n["high"] >= 2235,
      "corpus floors: >= 4,210 low / >= 2,235 high declares (2026-08-22 counts)",
      f"low={n['low']} high={n['high']}")
check(n["terminators_on_wire"] == 0 and n["code_dwords"] >= 5266,
      "ItemCode:516's demand holds: ZERO ITEM_CODE_TERMINATOR dwords arrive, "
      "over >= 5,266 code words -- the client appends its own",
      f"dwords={n['code_dwords']} terminators={n['terminators_on_wire']}")
check(n["high_extra_field"] == 0,
      "declared field 14 (trailing u32) is absent from EVERY high declare -- "
      "the format table declares a slot retail never fills")
check(n["low_topbit"] == 0 and n["high_topbit"] > 0,
      "the fileId deferred-fetch top bit rides ONLY the high-detail stream",
      f"low={n['low_topbit']}/{n['low']} high={n['high_topbit']}/{n['high']}")
check(q_hist and all(1 <= q <= 250 for q in q_hist),
      "every quantity is a plausible stack size (1..250)",
      f"histogram={dict(sorted(q_hist.items()))}")

print("== 3. the equip-set pair (0x0147 / 0x0148) ==")
check(n["upd"] >= 236 and n["act"] >= 59,
      "corpus floors: >= 236 set updates / >= 59 active-set selects",
      f"upd={n['upd']} act={n['act']}")
check(n["upd_set_oob"] == 0 and n["act_set_oob"] == 0,
      "set < ITEM_PLAYER_EQUIP_SETS (4) in every message of both opcodes "
      "-- the client asserts it, so retail cannot violate it and does not")
check(len(sets_hist) == 4 and len(set(sets_hist.values())) == 1,
      "the four set indices arrive in EQUAL counts -- the server streams the "
      "complete four-set table, never a partial one",
      f"histogram={dict(sorted(sets_hist.items()))}")
check(n["upd_key_undeclared"] == 0 and n["act_key_undeclared"] == 0,
      "every inventory key was declared by a prior ITEM_STREAM_CREATE (0x0144) "
      "in the same connection")
check(n["upd_item_undeclared"] == 0 and n["upd_item_refs"] > 0,
      "every non-null item ref was declared by a prior 0x015E/0x0161 "
      "in the same connection",
      f"refs={n['upd_item_refs']}")
print(f"   (pair asymmetry, reported not asserted: {dict(pair_shape)})")

print("== 4. the model-scale store (0x009A) ==")
check(n["scale"] >= 965,
      "corpus floor: >= 965 messages (2026-08-22 count)", f"n={n['scale']}")
check(n["scale_lowbits"] == 0,
      "every value is a pure top-byte percent -- the packed word's low 24 "
      "bits (the UPSTREAM hue/sat/lightness decode) never arrive on retail",
      f"violations={n['scale_lowbits']}")
check(scale_tops and max(scale_tops, key=scale_tops.get) == 100
      and scale_tops[100] * 2 > sum(scale_tops.values()),
      "100% is the dominant scale (the CpsMonster no-op case, cmp al,0x64)",
      f"tops={dict(sorted(scale_tops.items()))}")
check(all(0 < t <= 200 for t in scale_tops),
      "every scale percent is sane (0 < s <= 200); observed span 8..115",
      f"span={min(scale_tops)}..{max(scale_tops)}")

sys.exit(LEDGER.verdict())
