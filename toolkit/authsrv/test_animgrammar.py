"""The ANIMREF episode machines, proven on synthetic streams they cannot force.

Everything here is bare-machine: no vault, no capture, no socket -- the wire
layouts are synthetic rows in `decode_all`'s own shape (opcode at index 0),
and every expectation was written from the corpus-verified grammar
(`studies/animref/FINDINGS.md`), not from the code under test. The corpus run
itself is guarded separately by `animgrammar.py --control` (P-CTRL), which
pins the castmech-overlap figures; THIS file proves the machines' mechanics:
batch signatures, episode state transitions, damage pairing, the windup
arithmetic, and the traps named in the module docstring (A3's victim-first
slot order, the queued-terminated family that has no animation property, an
E-tag never reaching back past its episode's open).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))

import checks  # noqa: E402
import animgrammar as ag  # noqa: E402

led = checks.Ledger("animgrammar episode machines", floor=48)
ok = checks.adopt(led)

# --- f32 -------------------------------------------------------------------
ok(ag.f32(0x3F800000) == 1.0, "f32 decodes 1.0")
ok(ag.f32(1073741824) == 2.0, "f32 decodes 2.0 (the Hatcher's declared base)")

# --- prop_events normalisation --------------------------------------------
msgs = [
    (1.0, 0x009F, [159, 8, 31, 1]),
    (1.0, 0x00A0, [160, 60, 31, 40, 153]),
    (1.5, 0x00A2, [162, 62, 31, 0x3F800000]),
    (2.0, 0x00A3, [163, 16, 31, 40, 0x40000000]),   # victim 31, SOURCE 40
    (2.5, 0x0035, [53, 40, 1073741824, 0x3F800000]),
    (3.0, 0x00F1, [241, 40, 16]),
    (3.5, 0x00E4, [228, 31, 153, 0]),
    (4.0, 0x0777, [0x777, 1, 2, 3]),                 # not ours; skipped
]
evs = list(ag.prop_events(msgs))
ok(len(evs) == 7, "seven of eight rows normalise (the foreign opcode drops)")
ok(evs[0] == {"t": 1.0, "kind": "prop", "prop": 8, "agent": 31,
              "target": None, "value": 1}, "0x009F: [op, prop, agent, value]")
ok(evs[1]["target"] == 40 and evs[1]["value"] == 153,
   "0x00A0 carries target then value")
ok(evs[3]["agent"] == 31 and evs[3]["target"] == 40 and evs[3]["value"] == 2.0,
   "0x00A3 keeps VICTIM in the agent slot and SOURCE in the target slot")
ok(evs[4] == {"t": 2.5, "kind": "speed", "agent": 40, "base": 2.0,
              "modifier": 1.0}, "0x0035 declares (base, modifier)")
ok(evs[5]["kind"] == "status" and evs[5]["value"] == 16, "0x00F1 is a status mark")
ok(evs[6]["kind"] == "E4" and evs[6]["skill"] == 153, "E-series tagged")

# --- token -----------------------------------------------------------------
ok(ag.token({"kind": "prop", "prop": 8, "value": 0}) == "8:0", "hold token")
ok(ag.token({"kind": "prop", "prop": 16}) == "dmg", "damage token")
ok(ag.token({"kind": "prop", "prop": 60, "target": None}) == "60",
   "untargeted cast token")
ok(ag.token({"kind": "prop", "prop": 60, "target": 40}) == "60T",
   "targeted cast token keeps the channel distinction (ANIMREF-Q1)")
ok(ag.token({"kind": "prop", "prop": 50, "target": 0}) == "50",
   "a zero target is NOT the targeted form")

# --- the adrenaline family (ANIMREF-R9) ------------------------------------
# Four opcodes, one event shape, and the ABSENT fields stay None: a gain names
# no skill and a spend names no units, and `0` for either would read as a
# measurement that was never taken.
adren = list(ag.prop_events([
    (1.0, 0x00CF, [0x00CF, 31, 25]),           # gain: agent, units
    (2.0, 0x00D2, [0x00D2, 31, 382, 0]),       # spend: agent, skill, copy
    (3.0, 0x00D0, [0x00D0, 31]),               # clear: agent
    (4.0, 0x00D1, [0x00D1, 31, 384, 1, 75]),   # set: agent, skill, copy, units
]))
ok([e["kind"] for e in adren] ==
   ["adren_gain", "adren_spend", "adren_clear", "adren_set"],
   "all four adrenaline opcodes decode into the event stream",
   f"{[e['kind'] for e in adren]}")
ok(adren[0]["units"] == 25 and adren[0]["skill"] is None,
   "a gain carries units and NO skill -- absent stays None, never 0",
   f"{adren[0]}")
ok(adren[1]["skill"] == 382 and adren[1]["units"] is None,
   "a spend carries the skill and NO units",
   f"{adren[1]}")
ok(adren[3]["skill"] == 384 and adren[3]["units"] == 75,
   "a set carries both", f"{adren[3]}")
ok(adren[2]["units"] is None and adren[2]["skill"] is None,
   "a clear carries neither", f"{adren[2]}")

# AND THEY DO NOT ENTER SIGNATURES unless asked. This is the regression that
# matters: letting them in would silently rewrite every published signature
# (FINDINGS sec.3's ['E5','46','dmg','E3'] and every count in sec.3 and 8), so
# the default is measured-as-before and the opt-in is explicit.
_sig_evs = [
    {"t": 1.0, "kind": "prop", "prop": 4, "agent": 40, "target": 31,
     "value": 0},
    {"t": 1.0, "kind": "adren_gain", "agent": 40, "skill": None,
     "copy": None, "units": 25},
]
ag.assign_batches(_sig_evs, eps=0.0)
_by = {}
for _e in _sig_evs:
    _by.setdefault(_e["bt"], []).append(_e)
_toks = tuple(ag.token(x) for x in _by[1.0]
              if ag.involves(x, 40)
              and (ag.SIGN_ADRENALINE or x["kind"] not in ag.ADREN_KINDS))
ok(_toks == ("4",),
   "an adrenaline event in a batch does NOT enter the signature by default "
   "-- a new instrument must not invalidate the measurements taken with the "
   "old one", f"{_toks}")
ok(ag.SIGN_ADRENALINE is False and ag.ADREN_KINDS == {
       "adren_gain", "adren_clear", "adren_set", "adren_spend"},
   "the opt-in switch exists and is OFF, and the kind set is the gate",
   f"SIGN_ADRENALINE={ag.SIGN_ADRENALINE}")

# --- swing machine ---------------------------------------------------------
def P(t, prop, agent, target=None, value=0):
    return {"t": t, "kind": "prop", "prop": prop, "agent": agent,
            "target": target, "value": value}


swings = ag.swing_episodes([
    {"t": 0.0, "kind": "speed", "agent": 40, "base": 2.0, "modifier": 1.0},
    P(1.0, 4, 40, 31),                       # open
    P(1.9, 16, 31, 40, -0.1),                # damage, source == attacker
    P(1.9, 16, 99, 7, -0.5),                 # damage from someone ELSE
    P(1.9, 1, 40),                           # FINISHED, same instant
    P(3.0, 4, 40, 31),                       # second swing...
    P(3.4, 3, 40),                           # ...stopped
    P(5.0, 4, 40, 31),                       # third...
    P(5.5, 4, 40, 31),                       # ...reopened by a fourth
    P(9.0, 4, 12, 31),                       # a speedless attacker, censored
])
by = {(s["attacker"], s["close"]): s for s in swings}
ok(len(swings) == 5, "five swing episodes out", f"got {len(swings)}")
landed = by[(40, "landed")]
ok(abs(landed["dt"] - 0.9) < 1e-9 and abs(landed["ratio"] - 0.45) < 1e-9,
   "windup 0.9 over declared 2.0x1.0 scores ratio 0.45")
ok(landed["damage"] == [(31, -0.1)],
   "same-instant damage pairs by SOURCE slot; the stranger's row does not")
ok(by[(40, "stopped")]["dt"] == 0.4, "prop 3 closes STOPPED with its dt")
ok((40, "reopened") in by and by[(40, "reopened")]["t0"] == 5.0,
   "a second STARTED closes the open swing as reopened")
ok(by[(12, "censored")]["ratio"] is None,
   "no 0x0035 for the attacker means ratio None, not a guess")

# --- cast machine: self ----------------------------------------------------
def E(t, tag, agent, skill):
    op = {v: k for k, v in ag.E_SERIES.items()}[tag]
    return {"t": t, "kind": tag, "agent": agent, "skill": skill, "copy": 0}


free_cast = [
    E(1.0, "E4", 31, 153), P(1.0, 8, 31, None, 0), P(1.0, 62, 31, None, 10),
    P(1.0, 60, 31, 40, 153), P(1.0, 8, 31, None, 1),
    E(2.0, "E5", 31, 153), P(2.0, 58, 31), P(2.0, 20, 40, 31, 276),
    E(2.75, "E3", 31, 153),
    E(9.0, "E6", 31, 153),
]
eps = ag.cast_episodes(free_cast, me=31)
ok(len(eps) == 1 and eps[0]["close"] == "complete",
   "a full self cycle closes complete at E6")
ep = eps[0]
ok(ep["family"] == "spell" and ep["target"] == 40,
   "the animation property assigns family and target")
ok(ep["open_sig"] == ("E4", "8:0", "62", "60T", "8:1"),
   "open-batch signature in stream order", f"{ep['open_sig']}")
ok(ep["finish_sig"] == ("E5", "58", "20"),
   "E5-batch signature captured at the finish instant", f"{ep['finish_sig']}")
ok(ep["e"] == {"E4": 0.0, "E5": 1.0, "E3": 1.75, "E6": 8.0},
   "E-series gaps join by skill", f"{ep['e']}")

terminated = ag.cast_episodes(
    [E(1.0, "E4", 31, 394), E(1.9, "E2", 31, 394)], me=31)
ok(terminated[0]["close"] == "refused_or_terminated"
   and terminated[0]["family"] is None,
   "a queued-terminated press (E4 then E2, NO animation property) survives "
   "-- the family an animation-property open would delete")

cancelled = ag.cast_episodes(
    [E(1.0, "E4", 31, 153), P(1.0, 60, 31, 40, 153),
     P(2.0, 8, 31, None, 0), P(2.0, 59, 31), E(2.0, "E2", 31, 153)], me=31)
ok(cancelled[0]["close"] == "cancelled"
   and cancelled[0]["cancel_sig"] == ("8:0", "59", "E2"),
   "the begun-cast cancel closes at 59 with the [8:0, 59, E2] burst",
   f"{cancelled[0].get('cancel_sig')}")

stale = ag.cast_episodes(
    [E(1.0, "E4", 31, 153), E(0.5, "E5", 31, 153),
     E(50.0, "E4", 31, 105)], me=31)
ok("E5" not in stale[0]["e"],
   "an E-tag from before the open never reaches into the episode")

inter = ag.cast_episodes(
    [E(1.0, "E4", 31, 153), E(1.5, "E4", 31, 105),
     E(2.0, "E5", 31, 153), E(2.6, "E5", 31, 105)], me=31)
ok(len(inter) == 2
   and {round(ep["e"]["E5"] - ep["e"]["E4"], 2) for ep in inter} == {1.0, 1.1},
   "two interleaved skills key independent episodes (castgaps parity)")

# --- cast machine: other agents -------------------------------------------
others = ag.cast_episodes([
    P(1.0, 60, 8, 9, 313),
    P(2.0, 58, 8), P(2.0, 55, 8, None, -0.2),
    P(3.0, 50, 14, 31, 402),
    P(3.5, 59, 14),
    P(4.0, 60, 20, None, 111),
    P(5.0, 60, 20, None, 111),
], me=31)
byc = {(ep["caster"], ep["close"]): ep for ep in others}
ok(byc[(8, "finished")]["finish_sig"] == ("58", "55"),
   "an other-agent cast closes at its 58 with the batch signature")
ok(byc[(14, "cancelled")]["family"] == "attack_skill",
   "prop 50 opens the attack-skill family for others")
ok((20, "reopened") in byc and (20, "censored") in byc,
   "a second open reopens; the stream's end censors")

marked = ag.cast_episodes(
    [P(1.0, 60, 8, 9, 313),
     {"t": 1.5, "kind": "status", "agent": 8, "value": 16},
     P(2.0, 58, 8)], me=31)
ok(marked[0]["status_marks"] == [(1.5, 16)],
   "a 0x00F1 during the episode is recorded, never a close by itself")

timeout = ag.cast_episodes(
    [P(1.0, 60, 8, 9, 313), P(40.0, 4, 40, 31)], me=31)
ok(timeout[0]["close"] == "timeout",
   "a silent open episode is swept as timeout, not left to lie")

# --- census keeps the anomalies -------------------------------------------
cen = ag.prop_census([P(1.0, 60, 8, 9, 313), P(1.1, 777, 8)])
ok(cen[777]["name"] == "UNKNOWN" and cen[777]["n"] == 1,
   "a property id outside the register is counted, not dropped")

# --- batch clustering (the ours-side timestamp granularity) ----------------
evs = ag.assign_batches([P(1.0, 4, 40, 31), P(1.0004, 1, 40),
                         P(1.2, 3, 40)], eps=0.005)
ok(evs[0]["bt"] == evs[1]["bt"] == 1.0 and evs[2]["bt"] == 1.2,
   "eps=5ms clusters a burst written in one breath; a later instant opens "
   "a new batch")
evs = ag.assign_batches([P(1.0, 4, 40, 31), P(1.0004, 1, 40)], eps=0.0)
ok(evs[0]["bt"] != evs[1]["bt"],
   "eps=0 (the live tape's exact-timestamp regime) does not merge them")
clustered = ag.assign_batches(
    [{"t": 0.0, "kind": "speed", "agent": 40, "base": 2.0, "modifier": 1.0},
     P(1.0, 4, 40, 31), P(1.9, 16, 31, 40, -0.1), P(1.9004, 1, 40)],
    eps=0.005)
sw = ag.swing_episodes(clustered)
ok(sw[0]["close"] == "landed" and sw[0]["damage"] == [(31, -0.1)],
   "damage pairing rides the CLUSTER, so a log whose sends carry their own "
   "clocks still pairs the FINISHED with its damage")

# --- scan_ours over a synthetic vault (the reader itself) ------------------
import json as _json
import struct as _struct
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    gs = os.path.join(tmp, "captures", "gamesrv")
    os.makedirs(gs)

    def prop_int_blob(prop, agent, value):
        return _struct.pack("<HIII", 0x009F, prop, agent, value).hex()

    def write_log(name, rows, origin_kind=True):
        with open(os.path.join(gs, name), "w", encoding="utf-8") as fh:
            if origin_kind:
                fh.write(_json.dumps(
                    {"kind": "origin", "origin": "ours",
                     "produced_by": "test", "peer": "127.0.0.1:1"}) + "\n")
                fh.write(_json.dumps({"kind": "key_exchange_ok",
                                      "peer": "127.0.0.1:1"}) + "\n")
            for r in rows:
                fh.write(_json.dumps(r) + "\n")

    # Agent 10, not 1: agent 1 is self by construction in scan_ours, and a
    # SELF episode opens on E4 -- a bare prop-60 for self opens nothing
    # (that is the machine working, and the first draft of this test
    # tripped over it).
    write_log("authsrv-20260823T000000-c1.jsonl", [
        {"kind": "sent", "seq": 0, "t": 1.0, "label": "anim",
         "plain": prop_int_blob(60, 10, 42)},
        {"kind": "sent", "seq": 1, "t": 2.0, "label": "finish",
         "plain": prop_int_blob(58, 10, 0)},
    ])
    write_log("authsrv-20260820T000000-c2.jsonl", [
        {"kind": "sent", "seq": 0, "t": 1.0, "label": "anim",
         "plain": prop_int_blob(60, 1, 42)},
    ])
    write_log("authsrv-20260824T000000-c3.jsonl", [
        {"kind": "sent", "seq": 0, "t": 1.0, "label": "tape[0]",
         "plain": prop_int_blob(60, 7, 999)},
    ])

    saved_env = os.environ.get("RURIK_VAULT")
    os.environ["RURIK_VAULT"] = tmp
    try:
        meta, conns = ag.scan_ours()
        ok(meta["used"] == 2 and meta["skipped_tape"] == 1,
           "scan_ours decodes the hand-packed 0x009F rows and excludes the "
           "tape-replay connection by its label",
           f"used={meta['used']} tape={meta['skipped_tape']}")
        c1 = [c for c in conns if "c1" in c["capture"]][0]
        ok(c1["casts"] and c1["casts"][0]["close"] == "finished"
           and c1["casts"][0]["skill"] == 42,
           "and the episode machines run on the decoded rows -- the codec "
           "framed our hand-packed message, which also pins the 0x009F "
           "layout this file assumes",
           f"{c1['casts'][0]['close']}")
        meta2, _ = ag.scan_ours(after="20260822")
        ok(meta2["used"] == 1,
           "the --after era filter drops the pre-castmech file (the "
           "known-bad control's own mechanism)")
    finally:
        if saved_env is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = saved_env

sys.exit(led.verdict())
