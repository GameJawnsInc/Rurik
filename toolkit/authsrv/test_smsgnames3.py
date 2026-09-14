r"""Fourteen names from the MANTID capture (2026-09-13), vs ArenaNet's wire.

    python toolkit/authsrv/test_smsgnames3.py

`vault/captures/live/20260913T210901` (the Factions tutorial, a Mesmer, build
38888; scored in studies/quests/FINDINGS.md 10) witnessed twelve GAME_SMSG and
two GAME_CMSG opcodes that carried `name: null` with readable shapes. Their
rows are in `schema/overrides.json`; the binary-side claims (handler chains,
asserts, the +0x24 slot array, the ItemTimer, the kind-11/12 view events)
live in each row's `why`. This file pins the half a `.raw` can arbitrate --
invariants the recorded traffic could have violated and did not -- so a name
that stops describing the traffic goes red.

  0x00A4 / 0x00A7  every arrival answers an outstanding launch on the same
                   (agent, shot handle), at t + flight time within 30 ms
  0x0168           field 1 is the kind-4 agent created in the same frame
  0x0135           assigned to the local player for 600 s, every time
  0x0159           the picked-up item is the one the last c2s PICKUP targeted,
                   and ITEM_ADD_TO_INVENTORY follows in the same frame
  0x00D9 / 0x00DC  a per-slot bar write, slot < 8, beside a copies word
  0x010E / 0x0111  prop ids are their own id space; the mask is bit 0 or none
  0x015A           the byte is a profession number, 1..10
  0x006F           one slot, 46 ms after c2s EQUIP_ITEM on that item
  0x0105           once, on the cinematic connection
  0x003F / 0x0030  every PICKUP targets a kind-4 agent named by TARGET_SELECT
                   in the same frame; EQUIP_ITEM is answered by 0x014B + 0x006F

Needs the vault; declares a LEDGER.skip when the capture is absent rather
than scoring zero.
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks       # noqa: E402
import livewire     # noqa: E402
import vaultpath    # noqa: E402

# Floor from a real green run (42 checks, 2026-09-13).
LEDGER = checks.Ledger("GAME_SMSG names round 3 (MANTID)", floor=42)
check = checks.adopt(LEDGER)

STAMP = "20260913T210901"
SMSG_NAMES = {
    0x00D9: "SKILLBAR_UPDATE_SKILL", 0x00DC: "SKILL_SET_COPIES",
    0x010E: "PROP_SET_STATE", 0x0111: "PROP_UPDATE_FLAGS",
    0x0105: "CINEMATIC_END", 0x006F: "AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT",
    0x0135: "ITEM_ASSIGN", 0x015A: "ITEM_SET_PROFESSION",
    0x0168: "ITEM_AGENT_DROP_SOURCE", 0x0159: "ITEM_PICKED_UP",
    0x00A4: "AGENT_PROJECTILE_LAUNCHED", 0x00A7: "AGENT_PROJECTILE_ARRIVED",
}
CMSG_NAMES = {0x003F: "PICKUP", 0x0030: "EQUIP_ITEM"}


def f32(u):
    return struct.unpack("<f", struct.pack("<I", u & 0xFFFFFFFF))[0]


# ---------------------------------------------------------------- section 1
print("== 1. the names the invariants defend are the schema's ==")
ROOT = os.path.dirname(os.path.dirname(HERE))
with open(os.path.join(ROOT, "schema", "overrides.json"), encoding="utf-8") as fh:
    chans = json.load(fh)["channels"]
for chan, names in (("GAME_SMSG", SMSG_NAMES), ("GAME_CMSG", CMSG_NAMES)):
    rows = {op: chans[chan].get(str(op), {}) for op in names}
    got = {op: r.get("name") for op, r in rows.items()}
    check(got == names, f"{chan}: all {len(names)} rows carry the pinned names",
          ", ".join(f"0x{o:04X}={n}" for o, n in sorted(got.items())))
    check(all("fields" not in r for r in rows.values()),
          f"{chan}: name-only rows -- no field claim, so the widths stay "
          f"msgshape's and messages.json's",
          [f"0x{o:04X}" for o, r in rows.items() if "fields" in r])
    check(all(r.get("name_confidence") in ("high", "medium") and STAMP in r.get("why", "")
              for r in rows.values()),
          f"{chan}: every row labels its strength and cites the capture as witness")

# ---------------------------------------------------------------- the walk
try:
    live = vaultpath.require_dir("captures", "live", why="the MANTID invariants")
except (Exception, SystemExit) as exc:                                    # noqa: BLE001
    LEDGER.skip("corpus sections", f"vault unavailable: {exc}")
    sys.exit(LEDGER.verdict())
cap = os.path.join(live, STAMP)
if not os.path.isdir(cap):
    LEDGER.skip("corpus sections", f"capture {STAMP} absent under {live}")
    sys.exit(LEDGER.verdict())

streams = {}
for cf in livewire.connections(cap):
    conn, merged, ok = livewire.decode_conn(cap, cf)
    port = conn.split("->")[0].split(":")[1]
    streams[port] = (merged, ok)
check(set(streams) >= {"60648", "60877"},
      "the cinematic (60648) and tutorial (60877) connections both decode",
      sorted(streams))
check(streams["60877"][1] and streams["60648"][1],
      "and both consumed every byte (decode_conn ok=True)")
world, _ok = streams["60877"]
s2c = [(t, op, v) for (t, d, op, v) in world if d == "s2c"]
c2s = [(t, op, v) for (t, d, op, v) in world if d == "c2s"]


def same_frame(t):
    return [(op, v) for (mt, op, v) in s2c if abs(mt - t) < 1e-6]


# ---------------------------------------------------------------- section 2
print("== 2. the projectile pair: launch and arrival ==")
pend = collections.defaultdict(list)
pairs, orphan_a7 = [], 0
for t, op, v in s2c:
    if op == 0x00A4:
        pend[(v[1], v[6])].append((t, v))
    elif op == 0x00A7:
        q = pend[(v[1], v[2])]
        if q:
            t0, v0 = q.pop(0)
            pairs.append((t - t0, f32(v0[4]), v0, v))
        else:
            orphan_a7 += 1
n_a4 = sum(1 for _t, op, _v in s2c if op == 0x00A4)
n_a7 = sum(1 for _t, op, _v in s2c if op == 0x00A7)
check(n_a4 >= 68 and n_a7 >= 68, "floor: >= 68 launches and >= 68 arrivals",
      f"0x00A4={n_a4} 0x00A7={n_a7}")
check(orphan_a7 == 0 and len(pairs) == n_a7,
      "every 0x00A7 answers an outstanding 0x00A4 on the same (agent, handle)",
      f"paired={len(pairs)} orphans={orphan_a7}")
check(sum(len(q) for q in pend.values()) == 0,
      "and no launch is left unanswered", f"{sum(len(q) for q in pend.values())} pending")
errs = [abs(dt - ft) for dt, ft, _a, _b in pairs]
check(errs and max(errs) <= 0.030,
      "the arrival lands at launch + field 4 (f32 seconds) within 30 ms, "
      "every pair -- the invariant with no free parameter",
      f"max={1000 * max(errs):.1f} ms mean={1000 * sum(errs) / len(errs):.1f} ms")
check(all(0.0 < ft < 2.0 for _dt, ft, _a, _b in pairs),
      "field 4 read as f32 is a plausible flight time (0 < s < 2), never raw u32")
check(all(v0[3] == 0 for _dt, _ft, v0, _b in pairs),
      "0x00A4 field 3 (u16) is 0 in every launch")
shooters = {v0[1] for _dt, _ft, v0, _b in pairs}
check(9 in shooters and len(shooters) > 1,
      "the player (agent 9, a Mesmer with a wand) launches too -- the pair is "
      "ranged fire, not 'the foe's attack'", f"{len(shooters)} shooters")
check(len({(v0[5], v1[3]) for _dt, _ft, v0, v1 in pairs}) <= 6
      and all(v0[5] == 0 and v1[3] == 6 for _dt, _ft, v0, v1 in pairs if v0[1] == 9),
      "field 5 / field 3 co-vary per attacker (the player's shots are 0 -> 6)",
      sorted({(v0[5], v1[3]) for _dt, _ft, v0, v1 in pairs}))

# ---------------------------------------------------------------- section 3
print("== 3. the drop chain: 0x0168, 0x0135, 0x0159 and c2s PICKUP ==")
drops = [(t, v) for t, op, v in s2c if op == 0x0168]
check(len(drops) >= 8, "floor: >= 8 drops", f"n={len(drops)}")
k4 = [v[1] in [mv[1] for mo, mv in same_frame(t) if mo == 0x0020 and mv[3] == 4]
      for t, v in drops]
check(all(k4), "0x0168 field 1 is the kind-4 (item) agent 0x0020 creates in the "
      "SAME frame, every time", f"{sum(k4)}/{len(k4)}")
src = [v[2] in [mv[1] for mo, mv in same_frame(t) if mo == 0x00F1] for t, v in drops]
check(sum(src) >= 7, "field 2 is the agent whose 0x00F1 AGENT_UPDATE_STATUS fires "
      "in the same frame (the foe that just died) in all but the chest's drop",
      f"{sum(src)}/{len(src)} -- the exception is [21, 10], agent 10 the chest")
assigns = [(t, v) for t, op, v in s2c if op == 0x0135]
check(len(assigns) >= 7 and all(v[2] == 9 for _t, v in assigns),
      "0x0135 assigns every drop to the local player (agent 9)", f"n={len(assigns)}")
check(all(abs(f32(v[3]) - 600.0) < 0.01 for _t, v in assigns),
      "for 600.0 s as f32 -- the ItemTimer's ten minutes",
      sorted({round(f32(v[3]), 3) for _t, v in assigns}))
check(all(any(mo in (0x0161, 0x0162) and mv[1] == v[1] for mo, mv in same_frame(t))
          for t, v in assigns),
      "and the assigned item is declared (0x0161/0x0162) in the same frame")

pickups = [(t, v) for t, op, v in c2s if op == 0x003F]
check(len(pickups) >= 3, "floor: >= 3 c2s PICKUP sends", f"n={len(pickups)}")
kinds = [[mv[3] for (mt, mo, mv) in s2c if mo == 0x0020 and mv[1] == v[1] and mt < t]
         for t, v in pickups]
check(all(k and k[-1] == 4 for k in kinds),
      "every PICKUP targets an agent whose latest create is kind 4 (an item agent)",
      kinds)
check(all(v[2] == 0 for _t, v in pickups), "and its byte is 0")
check(all(any(mo == 0x00C1 and mv[1] == v[1] and abs(mt - t) < 1e-6
              for (mt, mo, mv) in c2s) for t, v in pickups),
      "0x00C1 TARGET_SELECT names the same agent in the same c2s frame")

picked = [(t, v) for t, op, v in s2c if op == 0x0159]
check(len(picked) >= 2 and all(v[2] == 9 for _t, v in picked),
      "0x0159 names the player as the picker", f"n={len(picked)}")
ok_chain = []
for t, v in picked:
    last = [mv[1] for (mt, mo, mv) in c2s if mo == 0x003F and mt < t]
    ground = [mv[1] for (mt, mo, mv) in s2c if mo == 0x0020 and mv[3] == 4
              and mv[2] == v[1] and mt < t]
    ok_chain.append(bool(last and ground) and last[-1] == ground[-1])
check(all(ok_chain),
      "the picked-up item is the one carried by the agent the LAST PICKUP targeted",
      ok_chain)
check(all(any(mo == 0x013E and mv[2] == v[1] for mo, mv in same_frame(t))
          for t, v in picked),
      "and 0x013E ITEM_ADD_TO_INVENTORY for that item follows in the same frame")

# ---------------------------------------------------------------- section 4
print("== 4. the skill grant: 0x00D9 beside 0x00DC ==")
bar = [(t, v) for t, op, v in s2c if op == 0x00D9]
check(len(bar) >= 3 and all(v[1] == 9 and v[2] < 8 and v[4] == 0 for _t, v in bar),
      "0x00D9 writes the player's bar at a hotKey slot < 8 with field 4 = 0",
      [v[1:] for _t, v in bar])
check(all(any(mo == 0x00DC and mv[1] == v[3] and mv[2] == 1 for mo, mv in same_frame(t))
          for t, v in bar),
      "and each write's skill has a 0x00DC [skill, 1] in the same frame")
copies = [v for _t, op, v in s2c if op == 0x00DC]
check(len(copies) >= 3 and all(v[2] == 1 for v in copies),
      "every copies word carries 1 -- a count above 1 is UNVERIFIED and the "
      "row says so", [v[1:] for v in copies])

# ---------------------------------------------------------------- section 5
print("== 5. props, professions, the one-slot equip, the cinematic ==")
prop_ids, agent_ids, create_f2 = set(), set(), set()
masks, states = collections.Counter(), collections.Counter()
for port, (merged, _ok) in streams.items():
    for t, d, op, v in merged:
        if d != "s2c":
            continue
        if op == 0x0020:
            agent_ids.add(v[1])
            create_f2.add(v[2])
        elif op == 0x010E:
            prop_ids.add(v[1])
            states[v[2]] += 1
        elif op == 0x0111:
            prop_ids.add(v[1])
            masks[v[3]] += 1
check(len(prop_ids) >= 14 and not (prop_ids & agent_ids) and not (prop_ids & create_f2),
      "prop ids are their own id space: disjoint from agent ids and from "
      "0x0020's second field", f"{len(prop_ids)} props")
check(set(masks) <= {0, 1}, "0x0111 masks only bit 0 (or nothing)", dict(masks))
gate = [(t, v[1:]) for (t, d, op, v) in world if d == "s2c" and op == 0x010E and v[1] == 24771]
check(any(abs(t - 391.157) < 0.01 and v == [24771, 1, 0] for t, v in gate),
      "the tutorial gate: 0x010E [24771, 1, 0] at t=391.157", gate)

prof = collections.Counter(v[2] for port, (m, _o) in streams.items()
                           for t, d, op, v in m if d == "s2c" and op == 0x015A)
check(sum(prof.values()) >= 66 and all(1 <= k <= 10 for k in prof),
      "0x015A's byte is a profession number, 1..10, in every sighting",
      dict(sorted(prof.items())))
starter = [v[2] for t, op, v in s2c if op == 0x015A and v[1] in (72, 73, 74, 75, 76)]
check(starter and set(starter) == {5},
      "the Mesmer's own starter armour (items 72..76) says 5 = Mesmer", starter)

equip = [(t, v) for t, op, v in c2s if op == 0x0030]
slot = [(t, v) for t, op, v in s2c if op == 0x006F]
check(len(equip) == 1 and len(slot) == 1 and slot[0][1][1:] == [9, 0, equip[0][1][1]]
      and 0 < slot[0][0] - equip[0][0] < 0.5,
      "c2s EQUIP_ITEM [item] is answered by ONE 0x006F [9, 0, item] within 0.5 s",
      f"equip={equip[0][1][1:] if equip else None} slot={slot[0][1][1:] if slot else None}")
check(any(mo == 0x014B and mv[2] == equip[0][1][1] for mo, mv in same_frame(slot[0][0])),
      "beside 0x014B ITEM_CHANGE_LOCATION for the same item, and no 0x006E",
      f"0x006E in frame: {any(mo == 0x006E for mo, mv in same_frame(slot[0][0]))}")
check(not any(mo == 0x006E for mo, mv in same_frame(slot[0][0])),
      "(the nine-dword bulk write is NOT sent for an equip)")

cine = [(port, t) for port, (m, _o) in streams.items()
        for t, d, op, v in m if d == "s2c" and op == 0x0105]
check(cine == [("60648", cine[0][1])] if cine else False,
      "0x0105 arrives exactly once, on the cinematic connection", cine)
check(cine and any(mo == 0x0099 for mo, mv in
                   [(op, v) for (t, d, op, v) in streams["60648"][0]
                    if d == "s2c" and abs(t - cine[0][1]) < 1e-6]),
      "in the same frame as the 0x0099 instance transfer")

sys.exit(LEDGER.verdict())
