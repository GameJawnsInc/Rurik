r"""Two more GAME_SMSG names (2026-08-22), vs ArenaNet's own wire.

    python toolkit/authsrv/test_smsgnames2.py

The 2026-08-18 pass held `0x003C` and `0x003E` as PARTIAL for "consumers
unread"; reading the consumers earned them (studies/smsgnames 10). This pins
the half a `.raw` can arbitrate -- invariants the recorded traffic could have
violated and did not. The binary-side claims (the +0x34 masked store, the
0x10000067 event, the by-id-list removal) are clientscan's ground and live in
each overrides `why`, not here.

  0x003C PLAYER_UPDATE_FLAGS  masked flags RMW into the player record, keyed by
                              playerId; the mask is the 3 low bits.
  0x003E AGENT_VIEW_UNLINK    a per-agent view unlink, [agent_id] only.
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

# Floor from a real green run (9 checks, 2026-08-22).
LEDGER = checks.Ledger("GAME_SMSG names round 2", floor=9)
check = checks.adopt(LEDGER)

PLAYER_UPDATE_FLAGS = 0x003C
AGENT_VIEW_UNLINK = 0x003E

# ---------------------------------------------------------------- section 1
print("== 1. the names the invariants defend are the schema's ==")
ROOT = os.path.dirname(os.path.dirname(HERE))
with open(os.path.join(ROOT, "schema", "overrides.json"), encoding="utf-8") as fh:
    g = json.load(fh)["channels"]["GAME_SMSG"]
check(g.get("60", {}).get("name") == "PLAYER_UPDATE_FLAGS",
      "overrides 0x3c is PLAYER_UPDATE_FLAGS", g.get("60", {}).get("name"))
check(g.get("62", {}).get("name") == "AGENT_VIEW_UNLINK",
      "overrides 0x3e is AGENT_VIEW_UNLINK", g.get("62", {}).get("name"))

# ---------------------------------------------------------------- the walk
try:
    live = vaultpath.require_dir("captures", "live", why="the name invariants")
except (Exception, SystemExit) as exc:                                    # noqa: BLE001
    LEDGER.skip("corpus sections", f"vault unavailable: {exc}")
    sys.exit(LEDGER.verdict())

codec = Codec()
flags_rows = []
unlink_rows = []
for stamp in sorted(os.listdir(live)):
    cap = os.path.join(live, stamp)
    if not os.path.isdir(cap):
        continue
    for chan in tape.channel_files(cap):
        try:
            _i, ev = tape.load_tape(cap, chan["connection"])
            msgs, _r = tape.decode_all(ev, codec, "GAME_SMSG", 0)
        except Exception:                                   # noqa: BLE001
            continue
        for _t, op, v in msgs:
            if op == PLAYER_UPDATE_FLAGS and len(v) > 3:
                flags_rows.append((int(v[1]), int(v[2]), int(v[3])))
            elif op == AGENT_VIEW_UNLINK and len(v) > 1:
                unlink_rows.append(int(v[1]))

# ---------------------------------------------------------------- section 2
print("== 2. PLAYER_UPDATE_FLAGS: a masked flags RMW ==")
check(len(flags_rows) >= 1393,
      "corpus floor: >= 1,393 messages (2026-08-22 count)",
      f"n={len(flags_rows)}")
masks = collections.Counter(m for _p, _v, m in flags_rows)
check(set(masks) == {7},
      "the MASK (field 3) is 7 in EVERY message -- a 3-bit flags word, which "
      "is what makes the +0x34 store a flags update and not an arbitrary write",
      f"masks={dict(masks)}")
check(all((val & ~mask) == 0 for _p, val, mask in flags_rows),
      "the VALUE (field 2) never sets a bit outside the mask -- consistent "
      "with `(old & ~mask) | value` and inconsistent with value being an "
      "unrelated field")
players = {p for p, _v, _m in flags_rows}
check(len(players) > 1,
      "the messages address MANY distinct playerIds, not one -- keyed by "
      "player as the store is", f"{len(players)} distinct")

# ---------------------------------------------------------------- section 3
print("== 3. AGENT_VIEW_UNLINK: [agent_id], and it is not the world remove ==")
check(len(unlink_rows) >= 65,
      "corpus floor: >= 65 messages", f"n={len(unlink_rows)}")
check(all(a > 0 for a in unlink_rows),
      "every message carries a single positive agent id")
# The narrowing witness: 0x003E is far RARER than the world-level despawn
# 0x0021 (WORLD_REMOVE_AGENT) -- a view unlink is not the canonical remove.
remove_agent = []
for stamp in sorted(os.listdir(live)):
    cap = os.path.join(live, stamp)
    if not os.path.isdir(cap):
        continue
    for chan in tape.channel_files(cap):
        try:
            _i, ev = tape.load_tape(cap, chan["connection"])
            msgs, _r = tape.decode_all(ev, codec, "GAME_SMSG", 0)
        except Exception:                                   # noqa: BLE001
            continue
        remove_agent += [1 for _t, op, _v in msgs if op == 0x0021]
check(len(remove_agent) > len(unlink_rows) * 3,
      "0x0021 WORLD_REMOVE_AGENT vastly outnumbers 0x003E -- the narrowed "
      "name is right: 0x003E is a view unlink, not the world despawn",
      f"0x0021={len(remove_agent)} vs 0x003E={len(unlink_rows)}")

sys.exit(LEDGER.verdict())
