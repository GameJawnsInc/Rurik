"""test_regenjoin -- retail's health-regeneration wire, read back as the referee for
the server's signed pips and natural ramp (studies/skills/FINDINGS.md 64, SKILLS-RG;
regenjoin.py's docstring holds the predictions as registered and what refuted them).

    python toolkit/authsrv/test_regenjoin.py

Section 1 runs anywhere: the arithmetic (one clamp on the signed sum and its two
known-bad arms), the carried slot table, and the natural-ramp readers on hand-built
batches, each against the arm that must redden it. Section 0 checks the carried slot
table against the vault's own `skills` rows (a declared skip on a machine with no
vault/content DIRECTORY; a directory whose rows disagree is a FAIL). Section 2 is the
live corpus (a declared skip with no captures/live DIRECTORY; a corpus that will not
decode RAISES -- the one set-aside is a manifest-declared gap, asserted with
capgaps.audit): P1-P5, the cap, property 32, and the known-bad arms (a 3 s delay, a
1 s step, separate caps, an unsigned clamp) scored on the same rows, each red.
"""
import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import effects                                                 # noqa: E402
import regenjoin                                               # noqa: E402
import vaultpath                                               # noqa: E402

HAVE_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_CAPTURES = os.path.isdir(vaultpath.vault_path("captures", "live"))
# Floors from the green runs of 2026-10-07: bare (RURIK_VAULT at an empty directory
# AND at a nonexistent path, sections 0 and 2 declared skips) 21; with the vault 50
# (section 0: 7, section 2: 22). Decided on the DIRECTORIES, never on what loaded.
# The review fix (same day): +1 bare (1c', the TARGETED / FRIEND_ACT split) and +1 in
# section 2 (OWN_CAST binds no scored-kind step, EV-1): 22 bare, 52 with the vault, from
# the green runs. Round 2 (2026-10-08, the verifier's VF-1): +3 bare (1c'' the heal-landing
# reader, 1c''' score's two reports on a hand-built PvP player, 1c'''' --json) and +2 in
# section 2 (OWN_CAST on the unscored kind; the heal-landing evidence): 25 bare, 57 with the
# vault, from the green runs.
FLOOR_BARE = 25
FLOOR_VAULT = FLOOR_BARE + (7 if HAVE_CONTENT else 0) + (25 if HAVE_CAPTURES else 0)
LEDGER = checks.Ledger("retail's health regeneration", floor=FLOOR_VAULT)
check = checks.adopt(LEDGER)

OP_A2, OP_A3, OP_9F, OP_A0, OP_APPLY = 0x00A2, 0x00A3, 0x009F, 0x00A0, 0x0042


def _bits(x):
    import struct
    return struct.unpack("<I", struct.pack("<f", x))[0]


def word(t, agent, pips, h=480):
    return (0, t, OP_A2, [OP_A2, 44, agent, _bits(pips * 2.0 / h)])


def section_arithmetic():
    print("== 1. the arithmetic, the slots, the readers on hand-built batches (anywhere) ==")
    # 1a. ONE clamp on the signed sum, and the two arms that must differ from it
    pips = [-2, -4, -7, +8]           # 135 r11 (38888), 44 r15, Burning, 288 r13 -- :50061
    check(regenjoin.net_sum(pips) == -5,
          "the 288 witness's live set sums to -13 + 8 = -5 under ONE clamp (P1)")
    check(regenjoin.net_sum(pips, separate_caps=True) == -2,
          "KNOWN-BAD ARM, separate caps: the degeneration clamped to -10 FIRST reads -2 -- "
          "the number retail's -5 refutes")
    check(regenjoin.net_sum([-2, -4, -7]) == -10 and regenjoin.net_sum([-2, -4, -7], unsigned=True) == -13,
          "the same set before 288 reads -10 (the clamp binds); KNOWN-BAD ARM, unsigned: -13")
    check(regenjoin.net_sum([7, 8]) == 10 and regenjoin.net_sum([3]) == 3,
          "the positive side clamps at +10 too, and a lone +3 passes")
    # 1b. the client's scaler, the carried slots and their signs
    same = all(regenjoin.interp(lo, hi, r) == effects.interp(lo, hi, r)
               for lo, hi in ((3, 10), (4, 9), (5, 10), (1, 4), (0, 3), (5, 5))
               for r in range(0, 21))
    check(same, "regenjoin.interp IS effects.interp (0x005A8920) on every carried slot, ranks 0..20")
    got = {s: regenjoin.signed_pips(s, r, 38888) for s, r in
           ((446, 0), (814, 0), (288, 13), (31, 15), (44, 15), (108, 12), (135, 11), (478, 0),
            (480, 0), (479, 0), (482, 9), (364, 10))}
    want = {446: 3, 814: 5, 288: 8, 31: -5, 44: -4, 108: -2, 135: -2, 478: -3, 480: -7,
            479: 0, 482: 0, 364: None}
    check(got == want, "signed pips: 446 +3, 814 +5, 288 +8 at rank 13, 31 -5, 44 -4 at 15, 108 -2 "
          "at 12, 135 -2 at 11 (build 38888), Bleeding -3, Burning -7, Blind / Deep Wound 0, and "
          "a skill with no carried number None (never 0)", f"{got}")
    check(regenjoin.signed_pips(135, 11, 38797) == -2 and regenjoin.signed_pips(135, 0, 38797) == 0
          and regenjoin.signed_pips(135, 0, 38888) == -1 and regenjoin.signed_pips(135, 0, None) is None,
          "Faintheartedness 135 is keyed on the TAPE's build (0..3 on 38797, 1..3 on 38888); an "
          "unknown build has no number")
    # 1c. a hand-built connection: the observer 25 (property 41), a hostile 117 ('mon1')
    seq = [
        (0, 1.0, OP_9F, [OP_9F, 41, 25, 50]),
        (0, 1.0, 0x0020, [0x0020, 117, 0x20000000, 0, 0, (0.0, 0.0), 0, 0, 0, 0.0, 0, 0,
                          int.from_bytes(b"mon1", "big")]),
        (0, 1.0, 0x0020, [0x0020, 25, 0x30000000, 0, 5, (0.0, 0.0), 0, 0, 0, 0.0, 0, 0,
                          int.from_bytes(b"play", "big")]),
        (0, 1.0, OP_9F, [OP_9F, 42, 25, 480]),
        (0, 10.0, OP_A3, [OP_A3, 16, 25, 117, _bits(-0.05)]),       # the player is hit
        (0, 12.0, OP_A0, [OP_A0, 4, 25, 117, 0]),                   # its own swing starts
        (0, 12.5, OP_9F, [OP_9F, 1, 25, 0]),                        # and strikes
        word(17.5, 25, 1), word(19.5, 25, 2), word(21.5, 25, 3),    # the ramp, 5.0 after
        (0, 22.0, OP_9F, [OP_9F, 32, 25, 0]),                       # full
    ]
    tl = regenjoin.timeline(seq)
    check(tl["observer"] == 25 and regenjoin.kind_of(tl, 25) == "player"
          and regenjoin.kind_of(tl, 117) == "hostile",
          "the observer by property 41, the hostile by its 'mon1' token")
    seq0 = [word(9.0, 25, 0)] + seq
    tl0 = regenjoin.timeline(sorted(seq0, key=lambda r: r[1]))
    runs = regenjoin.natural_runs(tl0, 25)
    check(len(runs) == 1 and [lv for _t, lv in runs[0]["levels"]] == [1, 2, 3]
          and regenjoin.natural_runs(tl, 25) == [],
          "one natural run, levels 1, 2, 3 -- and none without the ZERO word a run starts from",
          f"{runs}")
    fs = regenjoin.first_steps(tl0)
    check([(round(f["delay"], 2), f["class"], f["on_time"]) for f in fs] == [(5.0, "OWN_HIT", True)],
          "its first step is 5.0 s after the player's own STRIKE (the latest anchor), on time",
          f"{fs}")
    fs = regenjoin.first_steps(tl0, regenjoin.REGISTERED)
    check([(round(f["delay"], 2), f["class"], f["on_time"]) for f in fs] == [(7.5, "LOSS", False)],
          "P2 AS REGISTERED (loss only) reads the same step 7.5 s late -- the refutation's shape")
    fs = regenjoin.first_steps(tl0, delay=3.0)
    check(fs and not fs[0]["on_time"], "KNOWN-BAD ARM, a 3 s delay: the 5.0 s step is not on time")
    iv = regenjoin.step_intervals(tl0)
    check([x[2] for x in iv] == [True, True] and not any(x[2] for x in regenjoin.step_intervals(tl0, 1.0)),
          "steps 2.0 s apart; KNOWN-BAD ARM, a 1 s step: neither interval is on time")
    check(regenjoin.full_census(tl0) == [("player", 1, False)],
          "the [32] follows a positive word, no regen close in its batch")
    # 1c'. the TARGETED split (the review's EV-2): a FOE's activation at the player and any
    # landing on it are TARGETED; a FRIENDLY ('nonc') activation is FRIEND_ACT, no anchor
    npc = (0, 1.0, 0x0020, [0x0020, 87, 0x20000000, 0, 0, (0.0, 0.0), 0, 0, 0, 0.0, 0, 0,
                            int.from_bytes(b"nonc", "big")])
    seqt = seq[:5] + [npc,
                      (0, 30.0, OP_A0, [OP_A0, 60, 117, 25, 31]),      # the hostile's activation
                      (0, 40.0, OP_A0, [OP_A0, 60, 87, 25, 160]),      # the NPC's activation
                      (0, 40.8, OP_A0, [OP_A0, 20, 25, 87, 284])]      # and its landing
    tlt = regenjoin.timeline(seqt)
    check(sorted(tlt["anchors"][25]) == [(10.0, "LOSS"), (30.0, "TARGETED"), (40.0, "FRIEND_ACT"),
                                         (40.8, "TARGETED")]
          and "FRIEND_ACT" not in regenjoin.ANCHOR_CLASSES and "FRIEND_ACT" in regenjoin.ACTIVATIONS,
          "a FOE's activation at the player is TARGETED, a FRIENDLY one is FRIEND_ACT (not an "
          "anchor: :50061's interrupted ally cast kept the timer), and the friendly LANDING is "
          "TARGETED; P2(c)'s ACTIVATIONS keeps FRIEND_ACT so its numbers did not move",
          f"{sorted(tlt['anchors'][25])}")
    # 1c''. a FRIENDLY HEAL's landing (2026-10-08, VF-1's follow-on): reported in
    # `heal_landings` and never removed from the anchors -- a non-foe [20] with a positive 55
    # from the SAME caster on the same agent within BATCH. A foe's, a bare landing, a heal
    # 0.2 s late, another caster's heal and a negative 55 are not.
    ally = (0, 1.0, 0x0020, [0x0020, 30, 0x30000000, 0, 5, (0.0, 0.0), 0, 0, 0, 0.0, 0, 0,
                             int.from_bytes(b"play", "big")])

    def a3(t, prop, target, cause, f):
        return (0, t, OP_A3, [OP_A3, prop, target, cause, _bits(f)])

    def land(t, target, caster):
        return (0, t, OP_A0, [OP_A0, 20, target, caster, 500])
    seqh = seq[:5] + [npc, ally,
                      land(40.8, 25, 87), a3(40.8, 55, 25, 87, 0.10),     # the NPC's heal lands
                      land(50.0, 25, 117), a3(50.0, 55, 25, 117, 0.05),   # a FOE's
                      land(60.0, 25, 30),                                  # a bare landing
                      land(70.0, 25, 30), a3(70.2, 55, 25, 30, 0.10),     # its heal 0.2 s late
                      land(80.0, 25, 30), a3(80.0, 55, 25, 87, 0.10),     # another caster's heal
                      land(90.0, 25, 30), a3(90.0, 55, 25, 30, -0.10)]    # a negative 55
    tlh = regenjoin.timeline(seqh)
    targeted = [t for t, c in sorted(tlh["anchors"][25]) if c == "TARGETED"]
    check(dict(tlh["heal_landings"]) == {25: [40.8]} and targeted == [40.8, 50.0, 60.0, 70.0, 80.0, 90.0],
          "a FRIENDLY HEAL's landing is the one with a positive 55 from the same caster in its "
          "batch (a foe's, a bare landing, a heal 0.2 s late, another caster's heal and a negative "
          "55 are not) -- reported in heal_landings, every landing still TARGETED",
          f"{dict(tlh['heal_landings'])} {targeted}")
    # 1c'''. and the two reports `score` builds on it, on an UNSCORED PvP player: 40 ('att2')
    # casts at 41 ('att1') and completes at 102.0 (OWN_CAST); a heal lands on it at 104.0; its
    # first natural step at 107.0 is 5.0 s from the OWN_CAST and 3.0 s from the heal. The
    # control: the same landing from the FOE 41 is no heal landing, so nothing is reported.
    def mk(agent, tok):
        return (0, 1.0, 0x0020, [0x0020, agent, 0x30000000, 0, 5, (0.0, 0.0), 0, 0, 0, 0.0, 0, 0,
                                 int.from_bytes(tok, "big")])

    def pvp(healer):
        return regenjoin.score([("S", "C", regenjoin.timeline(
            [seq[0], mk(40, b"att2"), mk(41, b"att1"), mk(42, b"att2"),
             (0, 1.0, OP_9F, [OP_9F, 42, 40, 480]),
             (0, 100.0, OP_A0, [OP_A0, 60, 40, 41, 68]), word(101.0, 40, 0),
             (0, 102.0, OP_9F, [OP_9F, 58, 40, 0]),
             land(104.0, 40, healer), a3(104.0, 55, 40, healer, 0.05),
             word(107.0, 40, 1)]))])
    mate, foe = pvp(42), pvp(41)
    got = (mate["p2_heal_crossed"], dict(mate["p2_heal_bound"]), foe["p2_heal_crossed"],
           dict(foe["p2_heal_bound"]), mate["p2_owncast_other"], mate["p2_binding_class_other"])
    check(got == ([("S", "C", 40, "other", 107.0, 5.0, 3.0)], {"other early": 1}, [], {}, [], {}),
          "score's reports: a PvP player's step 5.0 s from its own OWN_CAST straight across a "
          "TEAMMATE's heal landing is CROSSED, and bound by that landing it is EARLY (3.0 s); the "
          "same landing from a FOE reports neither", f"{got}")
    # 1c''''. `--json`: score's cap_tops is keyed by (kind, top) tuples, which json refuses as
    # keys (the flag raised on it until 2026-10-08); jsonable names each such key as text
    raw = {"cap_tops": collections.Counter({("hostile", 7): 5}), "n": 1}
    try:
        json.dumps(raw)
        refused = False
    except TypeError:
        refused = True
    try:
        back = json.loads(json.dumps(regenjoin.jsonable(raw)))
    except TypeError as e:
        back = repr(e)
    check(refused and back == {"cap_tops": {"hostile 7": 5}, "n": 1},
          "--json: a tuple-keyed count is refused by json as it stands, and jsonable writes it with "
          "its key as text", f"{back}")
    # 1d. the cap reader: a ramp that stops at 7 below the maximum is a witness, one that
    # stops because the [32] arrives is not
    ramp = [word(30.0, 117, 0)] + [word(35.0 + 2 * k, 117, k + 1) for k in range(7)]
    tl7 = regenjoin.timeline([seq[1]] + [(0, 29.0, OP_9F, [OP_9F, 42, 117, 480])] + ramp
                             + [(0, 60.0, OP_9F, [OP_9F, 32, 117, 0])])
    tlf = regenjoin.timeline([seq[1]] + [(0, 29.0, OP_9F, [OP_9F, 42, 117, 480])] + ramp
                             + [(0, 47.4, OP_9F, [OP_9F, 32, 117, 0])])
    check(regenjoin.cap_witnesses(tl7) == [("hostile", 7, 60.0 - 47.0)] and regenjoin.cap_witnesses(tlf) == [],
          "a run topping at 7 with the [32] 13 s later is a cap witness; the same run with its "
          "[32] 0.4 s after the top is not (it stopped because it was full)")
    # 1e. P1 on a hand-built apply: Burning onto 135 + 44 at H=480, then 288
    def apply(t, agent, skill, rank, buff):
        return (0, t, OP_APPLY, [OP_APPLY, agent, skill, rank, buff, _bits(15.0)])
    seq1 = [seq[0], seq[2], seq[3], apply(100.0, 25, 135, 11, 1), word(100.0, 25, -2),
            apply(101.0, 25, 44, 15, 2), word(101.0, 25, -6),
            apply(102.0, 25, 480, 1, 3), word(102.0, 25, -10),
            apply(103.0, 25, 288, 13, 4), word(103.0, 25, -5)]
    tl1 = regenjoin.timeline(seq1, build=38888)
    rows = regenjoin.apply_words(tl1)
    check([(r["skill"], round(r["word"]), r["want"], r["scored"]) for r in rows]
          == [(135, -2, -2, True), (44, -6, -6, True), (480, -10, -10, True), (288, -5, -5, True)],
          "P1 on the 288 witness's shape: -2, -6, -10 (clamped), then -5 -- every word the "
          "one-clamp sum", f"{[(r['skill'], r['word'], r['want'], r['scored']) for r in rows]}")
    rows = regenjoin.apply_words(tl1, separate_caps=True)
    check([r["want"] for r in rows][-1] == -2
          and abs(rows[-1]["word"] - rows[-1]["want"]) > regenjoin.UNIT_TOL,
          "KNOWN-BAD ARM, separate caps: the 288 apply wants -2 and the word -5 refutes it")
    rows = regenjoin.apply_words(tl1, unsigned=True)
    check(rows[2]["want"] == -13 and abs(rows[2]["word"] - rows[2]["want"]) > regenjoin.UNIT_TOL,
          "KNOWN-BAD ARM, unsigned: the Burning apply wants -13 and the word -10 refutes it")
    # 1f. P5 (b) on a hand-built ramp: a Bleeding onto natural +3 reads -3, not 0
    seq5 = [seq[0], seq[2], seq[3], word(200.0, 25, 0), word(205.0, 25, 1), word(207.0, 25, 2),
            word(209.0, 25, 3), apply(210.0, 25, 478, 0, 9), word(210.0, 25, -3)]
    steps, onto = regenjoin.under_degeneration(regenjoin.timeline(seq5))
    check(steps == 0 and onto == [(25, 3, -3.0, -3)],
          "P5: a Bleeding landing on a natural +3 sends -3, the effects alone (natural to 0)")
    seq5b = seq5[:-1] + [word(210.0, 25, 0)]
    _s, onto = regenjoin.under_degeneration(regenjoin.timeline(seq5b))
    check(onto == [], "and a word that is NOT negative after the ramp is not a degeneration onto it")
    seq5c = seq5 + [word(211.0, 25, -2)]
    steps, _o = regenjoin.under_degeneration(regenjoin.timeline(seq5c))
    check(steps == 1, "the steps-under-a-negative counter counts a +1 above a negative word "
          "(the reader can see the thing P5 says never happens)")


def section_carried():
    print("== 0. the carried slots against the vault's own skills rows ==")
    if not HAVE_CONTENT:
        LEDGER.skip("0. carried slots vs vault rows", "no vault/content directory")
        return
    import agents
    for skill, (which, lo, hi, _sign) in sorted(regenjoin.RATE_SLOTS.items()):
        row = agents.WORLD.get("skills", str(skill))
        got = (int(row[f"{which}0"]), int(row[f"{which}15"]))
        check(got == (lo, hi), f"skill {skill}'s {which} slot in the vault's table is the carried "
              f"{lo}..{hi}", f"vault {got} (build {row.provenance.get('build')})")
    row = agents.WORLD.get("skills", "135")
    b = row.provenance.get("build")
    carried = regenjoin.RATE_SLOTS_BY_BUILD[135].get(b)
    check(carried is not None and (int(row["bonus_scale0"]), int(row["bonus_scale15"])) == carried[1:3],
          f"135's bonus slot on the vault's build {b} is the carried row for that build",
          f"{carried}")


def section_corpus():
    print("== 2. the live corpus ==")
    if not HAVE_CAPTURES:
        LEDGER.skip("2. the live corpus", "no vault/captures/live directory")
        return
    import capgaps
    import tape
    aside = []
    rows = regenjoin.census(set_aside=aside)
    live = vaultpath.require_dir("captures", "live", why="test_regenjoin")
    caps = [os.path.join(live, d) for d in sorted(os.listdir(live))
            if os.path.isdir(os.path.join(live, d))]
    ok, why = capgaps.audit(aside, caps, tape.refuses)
    check(ok and len(rows) >= 127, f"{len(rows)} connections read whole; the set-aside is exactly "
          f"the manifests' declared gap", why)
    sc = regenjoin.score(rows)
    # P1
    by = sc["p1_by_skill"]
    check(sc["p1_scored"] >= 28 and sc["p1_match"] == sc["p1_scored"],
          f"P1: every scored apply word is the one-clamp signed sum ({sc['p1_match']} of "
          f"{sc['p1_scored']})", f"misses {sc['p1_misses']}")
    check(by.get(446, [0, 0]) >= [3, 3] and by[446][0] == by[446][1]
          and by.get(814, [0, 0]) >= [2, 2] and by[814][0] == by[814][1],
          "P1: 446 +3 at rank 0 and 814 +5, every one", f"{by}")
    check(sc["p1_clamp_witness"] == [("20260928T103123", 288, -5.0, -5)],
          "P1: 288 at rank 13 under -13 of degeneration reads -5 (20260928T103123 :50061)",
          f"{sc['p1_clamp_witness']}")
    check(by.get(31, [0, 0])[0] >= 1 and by[31][0] == by[31][1]
          and by.get(44, [0, 0])[0] >= 1 and by[44][0] == by[44][1],
          "P1: the hexes 31 (flat -5) and 44 (-4 at rank 15) sum in with everything else", f"{by}")
    for name, kw in (("separate caps", {"separate_caps": True}), ("unsigned", {"unsigned": True})):
        bad = regenjoin.score(rows, **kw)
        check(bad["p1_match"] < bad["p1_scored"],
              f"KNOWN-BAD ARM, {name}: P1 goes red on the same corpus",
              f"{bad['p1_match']} of {bad['p1_scored']}; misses {bad['p1_misses'][:3]}")
    check(all(want == 0 and word < 0 for _c, _a, _s, _b, want, word in sc["p1_natural_nonzero"])
          and len(sc["p1_natural_nonzero"]) >= 2,
          "the applies onto a RUNNING ramp (natural not zero) read the effects alone -- reported, "
          "and every one is a degeneration landing (P5)", f"{sc['p1_natural_nonzero']}")
    # P2
    pa, ha = sc["p2_anchors_player"], sc["p2_anchors_hostile"]
    check(pa["n"] >= 19 and pa["on_time"] == pa["n"],
          f"P2: every observer first step is 5.00 +- 0.10 s after its latest anchor "
          f"({pa['on_time']} of {pa['n']})", f"{pa}")
    check(ha["n"] >= 22 and ha["on_time"] >= ha["n"] - 1 and ha["early_list"] in ([], [0.78]) and not ha["late"],
          f"P2: every hostile first step but the one named exception is on time ({ha['on_time']} "
          f"of {ha['n']}; 20260917T224104 agent 117's 0.78 s after a Bleeding end is CONTESTED)",
          f"{ha}")
    pr = sc["p2_registered_player"]
    check(pr["early"] == 0 and len(pr["late"]) >= 5,
          "P2 AS REGISTERED (loss only) is refuted in part: the observer's late first steps are "
          "each on time under the corrected anchors", f"{pr}")
    pc = sc["p2_activations_player"]
    check(pc["early"] >= 1, "P2(c) AS REGISTERED (any own activation anchors) is refuted: a "
          "self skill would put a first step early", f"{pc}")
    bound = sc["p2_binding_class"]
    check(all(bound.get(c, 0) >= 1 for c in regenjoin.OBSERVED_CLASSES)
          and set(regenjoin.OBSERVED_CLASSES) | {"OWN_CAST"} == set(regenjoin.ANCHOR_CLASSES),
          "every OBSERVED anchor class binds at least one on-time first step (LOSS, NEGEND, "
          "OWN_START, OWN_HIT, TARGETED -- OWN_CAST is the one carried member left out)", f"{bound}")
    check(bound.get("OWN_CAST", 0) == 0,
          "OWN_CAST (the wearer's own cast completing at a foe) binds NO on-time first step of a "
          "SCORED kind (the observer, hostiles): it is carried by analogy with the swing, "
          "RECONSTRUCTION -- the label the server's cast_tick reset wears (the review's EV-1)",
          f"{bound}")
    oc = sc["p2_owncast_other"]
    check({(s, a) for s, _c, a, _t, _d in oc} >= {("20260929T100038", 6), ("20260928T103123", 4)}
          and all(abs(d - regenjoin.NATURAL_DELAY) <= regenjoin.TOL for _s, _c, _a, _t, d in oc),
          "...and on the UNSCORED 'other' kind (PvP players) it does bind on-time first steps: "
          "20260929T100038 :62925 agent 6 with no other anchor in reach, 20260928T103123 :58544 "
          "agent 4 with a LOSS in the same instant -- reported, never scored (most of that kind's "
          "steps are off time), so the label stays RECONSTRUCTION (the verifier's VF-1)",
          f"{oc} {sc['p2_binding_class_other']}")
    hb, hx = sc["p2_heal_bound"], sc["p2_heal_crossed"]
    check(not any(k.split()[0] in ("player", "hostile") for k in hb) and hb.get("other early", 0) >= 10
          and {(s, a) for s, _c, a, *_r in hx} >= {("20260817T231139", 13), ("20260929T100038", 3)},
          "a friendly HEAL's landing: no observer or hostile first step is bound by one (nothing "
          "scored bears on it), while two PvP players' steps run 5.0 s from their own OWN_CAST "
          "straight across a teammate's heal landing and most of that kind's early steps are early "
          "only against one -- why the server's reset at a heal's landing is CONTESTED",
          f"{dict(hb)} {hx}")
    bad = regenjoin.score(rows, delay=3.0)
    check(bad["p2_anchors_player"]["on_time"] == 0 and bad["p2_anchors_hostile"]["on_time"] == 0,
          "KNOWN-BAD ARM, a 3 s delay: no first step is on time", f"{bad['p2_anchors_player']}")
    # P3
    p3p, p3h = sc["p3_player"], sc["p3_hostile"]
    check(p3p["n"] >= 45 and p3p["on_time"] == p3p["n"] and p3h["n"] >= 60 and p3h["on_time"] == p3h["n"],
          "P3: every natural step is 2.00 +- 0.10 s after the last", f"{p3p} {p3h}")
    bad = regenjoin.score(rows, step=1.0)
    check(bad["p3_player"]["on_time"] == 0 and bad["p3_hostile"]["on_time"] == 0,
          "KNOWN-BAD ARM, a 1 s step: no step is on time")
    # the cap
    tops = sc["cap_tops"]
    check(sc["max_level"] == 7 and tops.get(("hostile", 7), 0) >= 5
          and not any(top > 7 for (_k, top) in tops),
          "THE CAP IS +7: no natural run reaches 8, and five stop at 7 with health still below "
          "the maximum (no [32] for seconds)", f"max {sc['max_level']}, {dict(tops)}")
    # P4
    check(sc["p4_scored"] >= 500 and sc["p4_beyond_scored"] == 0 and sc["p4_at_minus_10"] >= 30,
          f"P4: no observer or foe word beyond +-10 ({sc['p4_scored']} words; {sc['p4_at_minus_10']} at "
          f"-10)", f"beyond, any kind: {sc['p4_beyond']} (other players over a stale maximum)")
    # P5
    check(sc["p5_steps_under_negative"] == 0 and sc["p5_onto_ramp"] >= 6
          and sc["p5_onto_ramp_effects_only"] == sc["p5_onto_ramp"],
          "P5: no natural step above a negative word; every degeneration landing on a running ramp "
          "reads the effects alone", f"{sc['p5_onto_ramp_effects_only']} of {sc['p5_onto_ramp']}")
    # property 32
    check(sc["p32_n"] >= 113 and sc["p32_after_positive"] == sc["p32_n"],
          f"property 32 follows a POSITIVE word every time ({sc['p32_after_positive']} of {sc['p32_n']})")
    check(sc["regen_closes"] >= 7 and sc["regen_closes_neither"] == 0
          and sc["regen_closes_32"] >= 6 and sc["regen_closes_32"] + sc["regen_closes_44"] == sc["regen_closes"],
          "every regen close carries a [32] or a [44] -- none is silent (the [44] one is 288's under "
          "degeneration)", f"{sc['regen_closes_32']} [32], {sc['regen_closes_44']} [44]")
    silent = regenjoin.rate_free_skills([tl for _s, _c, tl in rows])
    check(not (silent & set(regenjoin.CONDITION_PIPS)) and not (silent & {446, 814, 288, 31, 44}),
          "the measured rate-free set holds no degenerating condition and no carried rate skill")


def main():
    t0 = time.time()
    section_arithmetic()
    section_carried()
    section_corpus()
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
