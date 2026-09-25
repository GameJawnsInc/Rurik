r"""The instant skill's announce on retail's wire: the batch around every `[48, caster, skill]`.

    python toolkit/authsrv/instantjoin.py            # every live capture
    python toolkit/authsrv/instantjoin.py --rows     # one line per announce batch
    python toolkit/authsrv/instantjoin.py --json

WHY THIS EXISTS. skills FINDINGS 56.2 found that retail announces a shout with
`0x009F [48, caster, skill]` -- `agents.GV_INSTANT_SKILL_ACTIVATED`, which this server
sent nowhere -- and not with the spell's property 60 that `cast_anim_msg` sends for
everything; the same section counted property 48 by skill type (Stance 64, Shout 67,
type 16 2) and named the announce and the BATCH ORDER (retail: every apply, then every
speed word; ours per wearer) as open divergences. This reader re-derives the whole
batch, per skill type and per caster kind, so the server can send retail's shape and a
test can pin it to literals the tape produced.

WHAT A BATCH IS HERE. Every s2c message inside BATCH_S (60 ms, the corpus's batch
shoulder, speedwords.py) of the announce, in wire order; the order is reported as the
list of opcodes with the fields that matter. The announce's own timestamp is the
anchor; `dt_same` says whether every message of the batch shares the anchor's stamp
exactly (one TCP segment) or straddles a boundary.

THE CASTER'S KIND is read from the create (0x0020) and the connection's own agent
(`shoutjoin.observer_of`: property 41 cross-checked against the answered presses):
  observer      the connection's own player
  hero          the observer's allegiance token and its effect list is on the wire
                (a 0x0042 ever addressed to it -- JARIN's rule for a hero; the one
                hero on tape, agent 30 of 20260914T005758, is a kind-8 create)
  ally          the observer's token, no list on the wire -- on the arena tape these
                are the observer's human TEAM-MATES (kind-9 creates, the same word a
                party body carries); no henchman casts an instant skill on any tape
  noncombatant  the client's own 'nonc' token
  foe           any other token
  unknown       no create seen for the caster
(The create's kind word does not split a player from a body -- the observer is 5,
the arena's other players 9, the hero 8 -- so the split is by the effect list.)

WHAT THE FIRST RUN FOUND (2026-09-25, every capture through 20260919T103604; the
predictions above were written first, in the lane's scratch record):
  P-A1 HELD, 0 of 133; P-A2 HELD, 64 / 67 / 2; P-A3 HELD, 0 on 0x00A0.
  P-A4 HALF-REFUTED: the [21] follows the client table's +0x78 (346 -> 601 is the
       row content already carried), but it is present for EVERY instant skill,
       133 of 133 -- none of the eight ids on tape holds the table's 2077 "none".
  P-A5 HELD, 67 of 67 shouts, 0 of 66 others. P-A6 HELD: one coded word, no marker,
       25944 for 364 (56) and 25911 for 348 (11) -- NOT the name id (25942 / 25909 at
       +0x98) but the block's third record (name_id + 2 on both), which the table's
       name_id spacing says cannot hold for 16 of the 52 corpus shouts.
  P-A7 HELD: [48] < [21] 133/133, [21] < 0x00A5 67/67, 0x00A5 < 0x0042 59/59, E5 <
       [48] 93/93, 0x0042 < E3 86/86, E3 < 0x0027 29/29, 0x00F1 < E3 8/8.
  P-A8 HELD, 62 of 62 at dt = 0 (E4, E5 and E3 alike).
  P-A9 REFUTED in the label: the arena's same-token casters are team-mates, 20 of
       them; a hero 24; a foe 27; no henchman. No property 8 in any of the 62.
  P-B1 UNWITNESSED: the 6 two-apply batches are all 348 (the hero's), which moves
       no speed, so no batch has two applies AND a speed word; the applies are
       adjacent 6 of 6. P-B2 HELD, 16 of 16 multi-word batches whose wearer has a
       word lead with it (the 17th re-cast over an open shout: no own word, 56.5).
  P-B3 HELD, 29 of 29.

THE PREDICTIONS, registered before the first run (the scratch file of 2026-09-25 is
the record; they are repeated here so a reader can see what the numbers were judged
against):

  P-A1  property 60 for a skill of type 3 / 15 / 16: 0 (INT and INT_TARGET together).
  P-A2  property 48 by type reproduces 56.2 at the 2026-09-23 cutoff: 3 -> 64,
        15 -> 67, 16 -> 2.
  P-A3  every 48 rides 0x009F, never 0x00A0.
  P-A4  the [21, caster, v] beside an announce follows the skill_visual row, not
        the announce: present for some ids, absent for others.
  P-A5  0x00A5 [caster, words] rides every Shout announce and no Stance / type-16 one.
  P-A6  the 0x00A5 words are a CODED string (codedstr) -- an id, not text.
  P-A7  order in a stranger's batch: [48], [21]?, 0x00A5, 0x0042.., words; the
        observer's own: E4, E5, [48], [21]?, 0x00A5, 0x0042.., E3, 0x0027..
  P-A8  the observer's own instant cast: E4 and 48 at dt = 0, 100 %.
  P-A9  caster kinds present: observer, hero, ally-player, foe; no ally-body.
  P-B1  a batch with >= 2 applies puts every 0x0042 before the first 0x0027.
  P-B2  with one apply, the wearer's own 0x0027 precedes the other agents'.
  P-B3  the observer's E3 sits between the applies and the speed words.

Standard library only; reads the vault through `vaultpath`; a connection whose byte
accounting does not close, or whose observer the two rules do not agree on, is refused
and counted, never scored (shoutjoin's rule).
"""
import argparse
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import livewire         # noqa: E402
import shoutjoin        # noqa: E402  (observer_of, skill_types, BATCH_S, the tokens)
import tape             # noqa: E402
import vaultpath        # noqa: E402
from clientscan import codedstr    # noqa: E402  (the coded-string words -> ids)

OP_CREATE = 0x0020
OP_SPEED = 0x0027
OP_APPLY = 0x0042
OP_REMOVE = 0x0044
OP_INT = 0x009F
OP_INT_TARGET = 0x00A0
OP_SPEECH = 0x00A5         # [agent, string16] -- the speech bubble (GAME_SMSG_0165)
OP_RELEASED = 0x00E2
OP_E3 = 0x00E3
OP_E4 = 0x00E4
OP_E5 = 0x00E5
OP_E6 = 0x00E6
OP_STATUS = 0x00F1
PROP_INSTANT = 48
PROP_SKILL_ACTIVATED = 60
PROP_EFFECT_ON_AGENT = 21
INSTANT_TYPES = (3, 15, 16)      # Stance, Shout, the type-16 pair
BATCH_S = shoutjoin.BATCH_S
TOKEN_NONCOMBATANT = shoutjoin.TOKEN_NONCOMBATANT
KIND_OBSERVER_CREATE = 5         # adrenjoin: the observer's 0x0020 carries 5 in word 4;
#                                  the arena's other players 9, the hero 8 (kept as a
#                                  record, not a rule -- the split is by effect list)


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def _brief(op, v):
    """One message as (opcode, the fields that matter) for a batch listing."""
    v = list(v)
    if op == OP_INT and len(v) > 3:
        return (op, int(v[1]), int(v[2]), int(v[3]))
    if op == OP_INT_TARGET and len(v) > 4:
        return (op, int(v[1]), int(v[2]), int(v[3]), int(v[4]))
    if op == OP_SPEECH and len(v) > 2:
        return (op, int(v[1]), tuple(codedstr.from_wire(v[2])))
    if op == OP_APPLY and len(v) > 5:
        return (op, int(v[1]), int(v[2]), int(v[3]), int(v[4]), round(_f32(int(v[5])), 3))
    if op == OP_SPEED and len(v) > 2:
        return (op, int(v[1]), round(float(v[2]), 2))
    if op in (OP_E3, OP_E4, OP_E5, OP_E6, OP_RELEASED, OP_STATUS, OP_REMOVE):
        return (op,) + tuple(int(x) if isinstance(x, int) else x for x in v[1:5])
    # Any other message: its first three fields, a string16 (a chat line in the
    # same window) as its code units so the listing prints on a cp1252 console.
    return (op,) + tuple(tuple(codedstr.from_wire(x)) if isinstance(x, str) else x
                         for x in v[1:4])


def caster_kind(agent, observer, alleg, kinds, listed):
    if agent == observer:
        return "observer"
    if agent not in alleg or observer not in alleg:
        return "unknown"
    if alleg[agent] == alleg[observer]:
        return "hero" if agent in listed else "ally"
    if TOKEN_NONCOMBATANT in (alleg[agent], alleg[observer]):
        return "noncombatant"
    return "foe"


def rows_of(merged, types):
    """(announces, controls, observer, refused_reason).

    An ANNOUNCE row, one per s2c 0x009F [48, caster, skill]:
      {"t", "skill", "type", "caster", "kind", "batch": [_brief...] (every s2c
       message inside BATCH_S of the anchor, wire order), "dt_same" (all share the
       anchor's stamp), "speech" (the 0x00A5 words for this caster in the batch, or
       None), "speech_ids" (codedstr.parse_coded of them, or the error), "vis21"
       ([v] of [21, caster, v] in the batch), "e4_dt" / "e5_dt" / "e3_dt" (the
       observer's own E4 / E5 / E3 of this skill inside the batch, dt from the
       anchor, or None), "applies" ([(wearer, skill)]), "speeds" ([(agent, u/s)]),
       "applies_before_speeds" (True / False / None when either is absent),
       "index" ({op: [positions]} of the batch's opcodes), "prop60_in_batch"}.
    CONTROLS: {"prop60_instant": n (INT + INT_TARGET, any instant-type id),
      "prop48_on_int_target": n, "speech_total": n, "speech_beside_48": n,
      "speech_elsewhere": [(t, agent, words)] (an 0x00A5 with no 48 inside BATCH_S)}.
    """
    observer, _press, why = shoutjoin.observer_of(merged)
    if observer is None:
        return [], {}, None, why
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    alleg, kinds, listed = {}, {}, set()
    for t, op, v in s2c:
        if op == OP_CREATE and len(v) > 12:
            alleg[int(v[1])] = int(v[12])
            kinds[int(v[1])] = int(v[4])
        elif op == OP_APPLY and len(v) > 2:
            listed.add(int(v[1]))
    instant_ids = {sid for sid, tc in types.items() if tc in INSTANT_TYPES}
    controls = {"prop60_instant": 0, "prop48_on_int_target": 0, "speech_total": 0,
                "speech_beside_48": 0, "speech_elsewhere": []}
    times = [t for t, _op, _v in s2c]
    anchors = []
    for i, (t, op, v) in enumerate(s2c):
        if op == OP_INT and len(v) > 3 and int(v[1]) == PROP_INSTANT:
            anchors.append(i)
        elif op == OP_INT and len(v) > 3 and int(v[1]) == PROP_SKILL_ACTIVATED \
                and int(v[3]) in instant_ids:
            controls["prop60_instant"] += 1
        elif op == OP_INT_TARGET and len(v) > 4:
            if int(v[1]) == PROP_SKILL_ACTIVATED and int(v[4]) in instant_ids:
                controls["prop60_instant"] += 1
            if int(v[1]) == PROP_INSTANT:
                controls["prop48_on_int_target"] += 1
    anchor_times = [s2c[i][0] for i in anchors]
    import bisect
    for t, op, v in s2c:
        if op == OP_SPEECH and len(v) > 2:
            controls["speech_total"] += 1
            j = bisect.bisect_left(anchor_times, t - BATCH_S)
            near = j < len(anchor_times) and anchor_times[j] <= t + BATCH_S
            if near:
                controls["speech_beside_48"] += 1
            else:
                controls["speech_elsewhere"].append(
                    (round(t, 3), int(v[1]), tuple(codedstr.from_wire(v[2]))))
    out = []
    for i in anchors:
        t, _op, v = s2c[i]
        caster, skill = int(v[2]), int(v[3])
        lo = bisect.bisect_left(times, t - BATCH_S)
        hi = bisect.bisect_right(times, t + BATCH_S)
        batch = [(s2c[k][0], _brief(s2c[k][1], s2c[k][2])) for k in range(lo, hi)]
        briefs = [b for _t, b in batch]
        speech = [b[2] for b in briefs if b[0] == OP_SPEECH and b[1] == caster]
        speech_ids = None
        if speech:
            try:
                speech_ids = codedstr.parse_coded(list(speech[0]))
            except ValueError as exc:
                speech_ids = f"NOT CODED: {exc}"
        vis21 = [b[3] for b in briefs if b[0] == OP_INT and b[1] == PROP_EFFECT_ON_AGENT
                 and b[2] == caster]
        def own_dt(opc):
            for bt, b in batch:
                if b[0] == opc and len(b) > 2 and b[1] == observer and b[2] == skill:
                    return round(bt - t, 6)
            return None
        applies = [(b[1], b[2]) for b in briefs if b[0] == OP_APPLY]
        speeds = [(b[1], b[2]) for b in briefs if b[0] == OP_SPEED]
        index = collections.defaultdict(list)
        for pos, b in enumerate(briefs):
            index[b[0]].append(pos)
        abs_ = (None if not (index[OP_APPLY] and index[OP_SPEED])
                else max(index[OP_APPLY]) < min(index[OP_SPEED]))
        out.append({
            "t": round(t, 6), "skill": skill, "type": types.get(skill),
            "caster": caster,
            "kind": caster_kind(caster, observer, alleg, kinds, listed),
            "batch": briefs,
            "dt_same": all(abs(bt - t) < 1e-9 for bt, _b in batch),
            "speech": speech[0] if speech else None,
            "speech_ids": speech_ids,
            "vis21": vis21,
            "e4_dt": own_dt(OP_E4), "e5_dt": own_dt(OP_E5), "e3_dt": own_dt(OP_E3),
            "applies": applies, "speeds": speeds,
            "applies_before_speeds": abs_,
            "index": {hex(k): pos for k, pos in index.items()},
            "prop60_in_batch": sum(1 for b in briefs if b[0] in (OP_INT, OP_INT_TARGET)
                                   and b[1] == PROP_SKILL_ACTIVATED),
            "anchor_pos": briefs.index((OP_INT, PROP_INSTANT, caster, skill)),
        })
    return out, controls, observer, None


def census(cutoff=None):
    """Every live capture stamped at or before `cutoff` (all when None), every game
    connection that decodes whole and names one observer."""
    types = shoutjoin.skill_types()
    live = vaultpath.require_dir("captures", "live",
                                 why="instantjoin reads live captures")
    out = {"announces": [], "connections": 0, "refused": [], "cutoff": cutoff,
           "controls": collections.Counter(), "speech_elsewhere": [],
           "observers": {}}
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir) or (cutoff is not None and stamp > cutoff):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                _conn, merged, ok = livewire.decode_conn(cap_dir, ch["file"])
            except Exception as exc:                            # noqa: BLE001
                out["refused"].append((stamp, ch["connection"], str(exc)[:80]))
                continue
            if not ok:
                out["refused"].append((stamp, ch["connection"], "byte accounting open"))
                continue
            rows, controls, observer, why = rows_of(merged, types)
            if observer is None:
                out["refused"].append((stamp, ch["connection"], why))
                continue
            out["connections"] += 1
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
            out["observers"][f"{stamp}/{port}"] = observer
            for k in ("prop60_instant", "prop48_on_int_target", "speech_total",
                      "speech_beside_48"):
                out["controls"][k] += controls[k]
            out["speech_elsewhere"].extend((stamp, port) + r
                                           for r in controls["speech_elsewhere"])
            for r in rows:
                r.update(capture=stamp, port=port, observer=observer)
            out["announces"].extend(rows)
    out["controls"] = dict(out["controls"])
    return out


def score(c):
    """The numbers the predictions are judged on."""
    an = c["announces"]
    by_type = collections.Counter(r["type"] for r in an)
    by_kind = collections.Counter((r["type"], r["kind"]) for r in an)
    by_skill = collections.Counter((r["type"], r["skill"]) for r in an)
    speech_by_type = collections.Counter((r["type"], r["speech"] is not None) for r in an)
    vis_by_skill = collections.Counter((r["skill"], tuple(r["vis21"])) for r in an)
    ids_by_skill = collections.defaultdict(collections.Counter)
    coded_bad = []
    for r in an:
        if r["speech"] is None:
            continue
        if isinstance(r["speech_ids"], str):
            coded_bad.append((r["capture"], r["port"], r["t"], r["speech_ids"]))
        else:
            ids_by_skill[r["skill"]][tuple(r["speech_ids"])] += 1
    own = [r for r in an if r["kind"] == "observer"]
    own_e4_dt = collections.Counter(r["e4_dt"] for r in own)
    own_e5_dt = collections.Counter(r["e5_dt"] for r in own)
    own_e3_dt = collections.Counter(r["e3_dt"] for r in own)
    # Order shapes: the batch's opcode sequence, per (type, kind), as a Counter.
    shapes = collections.defaultdict(collections.Counter)
    for r in an:
        seq = tuple(hex(b[0]) if b[0] != OP_INT else f"[{b[1]}]" for b in r["batch"])
        shapes[(r["type"], r["kind"])][seq] += 1
    # Relative order of the announce's own parts, per row.
    def rel(r):
        ix = r["index"]
        pos48 = r["anchor_pos"]
        pos21 = [p for p, b in enumerate(r["batch"]) if b[0] == OP_INT and b[1] == 21
                 and b[2] == r["caster"]]
        posA5 = ix.get(hex(OP_SPEECH), [])
        posE4 = ix.get(hex(OP_E4), [])
        posE5 = ix.get(hex(OP_E5), [])
        posE3 = ix.get(hex(OP_E3), [])
        posApply = ix.get(hex(OP_APPLY), [])
        posSpeed = ix.get(hex(OP_SPEED), [])
        posStatus = ix.get(hex(OP_STATUS), [])
        return {"48<21": (pos48 < min(pos21)) if pos21 else None,
                "21<A5": (max(pos21) < min(posA5)) if pos21 and posA5 else None,
                "48<A5": (pos48 < min(posA5)) if posA5 else None,
                "A5<apply": (max(posA5) < min(posApply)) if posA5 and posApply else None,
                "48<apply": (pos48 < min(posApply)) if posApply else None,
                "E4<E5": (max(posE4) < min(posE5)) if posE4 and posE5 else None,
                "E5<48": (max(posE5) < pos48) if posE5 else None,
                "apply<E3": (max(posApply) < min(posE3)) if posApply and posE3 else None,
                "E3<speed": (max(posE3) < min(posSpeed)) if posE3 and posSpeed else None,
                "status<E3": (max(posStatus) < min(posE3)) if posStatus and posE3 else None,
                "apply<speed": r["applies_before_speeds"]}
    rel_counts = collections.defaultdict(collections.Counter)
    for r in an:
        for k, val in rel(r).items():
            rel_counts[k][val] += 1
    multi = [r for r in an if len(r["applies"]) >= 2]
    # The batch-order halves (56.7's divergence): applies ADJACENT when there are
    # two; the WEARER's speed word first when there are several.
    def adjacent(r):
        pos = r["index"][hex(OP_APPLY)]
        return max(pos) - min(pos) == len(pos) - 1
    own_multi = [r for r in own if len(r["speeds"]) >= 2]
    own_multi_with_word = [r for r in own_multi
                           if any(a == r["caster"] for a, _s in r["speeds"])]
    return {
        "multi_apply_adjacent": sum(1 for r in multi if adjacent(r)),
        "multi_apply_with_speed": sum(1 for r in multi if r["speeds"]),
        "own_multi_speed": len(own_multi),
        "own_multi_speed_with_word": len(own_multi_with_word),
        "own_multi_speed_wearer_first": sum(1 for r in own_multi_with_word
                                            if r["speeds"][0][0] == r["caster"]),
        "own_no_prop8": sum(1 for r in own if not any(
            b[0] == OP_INT and b[1] == 8 and b[2] == r["caster"] for b in r["batch"])),
        "connections": c["connections"], "refused": len(c["refused"]),
        "announces": len(an),
        "by_type": {str(k): n for k, n in sorted(by_type.items(), key=str)},
        "by_type_kind": {f"{k[0]}/{k[1]}": n for k, n in sorted(by_kind.items(), key=str)},
        "by_type_skill": {f"{k[0]}/{k[1]}": n for k, n in sorted(by_skill.items(), key=str)},
        "controls": c["controls"],
        "speech_elsewhere": c["speech_elsewhere"],
        "speech_by_type": {f"{k[0]}/{'A5' if k[1] else 'noA5'}": n
                           for k, n in sorted(speech_by_type.items(), key=str)},
        "speech_ids_by_skill": {str(s): {str(k): n for k, n in cnt.items()}
                                for s, cnt in sorted(ids_by_skill.items())},
        "speech_not_coded": coded_bad,
        "vis21_by_skill": {f"{k[0]}/{k[1]}": n for k, n in sorted(vis_by_skill.items(), key=str)},
        "dt_same": collections.Counter(r["dt_same"] for r in an),
        "own": len(own),
        "own_e4_dt": {str(k): n for k, n in own_e4_dt.items()},
        "own_e5_dt": {str(k): n for k, n in own_e5_dt.items()},
        "own_e3_dt": {str(k): n for k, n in own_e3_dt.items()},
        "prop60_in_batch": sum(r["prop60_in_batch"] for r in an),
        "shapes": {f"{k[0]}/{k[1]}": [(n, " ".join(seq)) for seq, n in cnt.most_common(6)]
                   for k, cnt in sorted(shapes.items(), key=str)},
        "rel": {k: {str(val): n for val, n in cnt.items()} for k, cnt in rel_counts.items()},
        "multi_apply": [(r["capture"], r["port"], r["t"], r["skill"], r["kind"],
                         [(hex(b[0]),) + tuple(b[1:3]) for b in r["batch"]])
                        for r in multi],
        "applies_before_speeds": dict(collections.Counter(
            str(r["applies_before_speeds"]) for r in an)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true")
    ap.add_argument("--cutoff", default=None, metavar="STAMP")
    a = ap.parse_args()
    c = census(cutoff=a.cutoff)
    s = score(c)
    if a.json:
        print(json.dumps({"score": s, "announces": c["announces"], "refused": c["refused"]},
                         indent=1, default=str))
        return 0
    print(f"instantjoin: {s['connections']} connections with one observer, "
          f"{s['refused']} refused; {s['announces']} [48] announces")
    print(f"  by type: {s['by_type']}; by type/kind: {s['by_type_kind']}")
    print(f"  by type/skill: {s['by_type_skill']}")
    print(f"  controls: {s['controls']}; prop 60 inside an announce batch: "
          f"{s['prop60_in_batch']}")
    print(f"  0x00A5 beside the announce, by type: {s['speech_by_type']}")
    print(f"  0x00A5 words as coded ids, by skill: {s['speech_ids_by_skill']}; "
          f"not coded: {s['speech_not_coded']}")
    for row in s["speech_elsewhere"][:20]:
        print(f"    0x00A5 with no [48] inside {BATCH_S} s: {row}")
    if len(s["speech_elsewhere"]) > 20:
        print(f"    ... {len(s['speech_elsewhere']) - 20} more")
    print(f"  [21, caster, v] beside the announce, by skill: {s['vis21_by_skill']}")
    print(f"  batch shares the anchor's stamp: {dict(s['dt_same'])}")
    print(f"  the observer's own: {s['own']}; E4 dt {s['own_e4_dt']}; E5 dt "
          f"{s['own_e5_dt']}; E3 dt {s['own_e3_dt']}")
    print(f"  relative order (True / False / None = a part absent): ")
    for k, cnt in s["rel"].items():
        print(f"    {k}: {cnt}")
    print(f"  applies before speeds per batch: {s['applies_before_speeds']}")
    print(f"  the observer's batches with >= 2 speed words: {s['own_multi_speed']}, of "
          f"them with the wearer's own word {s['own_multi_speed_with_word']}, wearer's "
          f"word FIRST {s['own_multi_speed_wearer_first']}; the observer's batches with "
          f"no property 8 for the caster: {s['own_no_prop8']} of {s['own']}")
    print(f"  batches with >= 2 applies: {len(s['multi_apply'])} (applies adjacent "
          f"{s['multi_apply_adjacent']}, with a speed word {s['multi_apply_with_speed']})")
    for row in s["multi_apply"]:
        print(f"    {row}")
    print("  batch shapes by type/kind (count, opcodes; [n] = 0x009F prop n):")
    for k, rows in s["shapes"].items():
        print(f"    {k}:")
        for n, seq in rows:
            print(f"      {n:3d}  {seq}")
    if a.rows:
        for r in c["announces"]:
            print(f"  ANNOUNCE {r['capture']} {r['port']} t={r['t']:.3f} skill {r['skill']} "
                  f"type {r['type']} caster {r['caster']} ({r['kind']}) e4={r['e4_dt']} "
                  f"e5={r['e5_dt']} e3={r['e3_dt']} vis21={r['vis21']} "
                  f"speech_ids={r['speech_ids']} batch={r['batch']}")
    for stamp, conn, why in c["refused"]:
        print(f"  refused {stamp} {conn}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
