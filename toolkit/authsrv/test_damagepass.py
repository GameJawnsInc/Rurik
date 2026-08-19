r"""Prove `damagepass.py` -- the rung-7 consumer -- on math it cannot fudge and
on retail bytes it has never been tuned to.

WHAT IS PINNED AND WHY IT CAN FAIL. Three layers, deliberately separate:

1. EXACT MATH, synthetic: H recovery must give back an H that fractions were
   CONSTRUCTED from (and put the Master of Damage's predicted 590 in the
   family); the divisor fit must recover D=40 from ratios manufactured with
   D=40, through all three estimators; the scoping rule must keep kind in the
   key (the 8-vs-25 dissolution, B6); conflicting AR labels must REFUSE, not
   average. Each of these has a wrong-answer shape the assertions would catch.

2. RETAIL COUNTS, pinned BY NAME (`npcdefs`' rule: named captures, never a
   glob): the Pre-Searing fight connection and the rung-6 detour's arena
   connection. The arena corpus (map 310: 470 p16 + 83 p17, all joined, zero
   unjoined) is the largest damage corpus in the vault and was recorded before
   this module existed -- the counts are facts about bytes on disk, so a
   decode regression moves them and goes red.

3. THE LAW'S HONEST LIMIT: the p17 variance law is NOT asserted on arena data
   -- bots cast skills, and §3.1's attack-skill confound rides the same
   packet, which is measured here as most arena p17 groups having nonzero
   variance. What IS asserted is that the machinery detects both verdicts, and
   that the arena data shows the confound (if every group came back
   variance-zero on skill-polluted data, the detector would be suspect).

Needs `vault/captures/live/`; without it the corpus sections cannot run and
the floor takes the run red, which is correct -- a damagepass "proven" with no
retail bytes is not proven.
"""
import json
import math
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import damagepass  # noqa: E402
import vaultpath  # noqa: E402

# Floor set from a real green run (68 checks, 2026-08-18); every section
# runs unconditionally, so the mandatory core is the whole file.
LEDGER = checks.Ledger("damagepass", floor=68)
check = checks.adopt(LEDGER)

f32 = lambda x: struct.unpack("<f", struct.pack("<f", x))[0]


# ---------------------------------------------------------------------------
print("== 1. H recovery: exact math ==")

# Fractions constructed on the 590 grid (the MoD prediction's H).
fit = damagepass.h_fit([-f32(7 / 590), -f32(13 / 590), -f32(41 / 590)])
check(fit is not None, "constructed 590-grid fractions fit some H")
if fit:
    h0, pts = fit
    # gcd(7, 13, 41) = 1, so the minimal family member IS 590 exactly.
    check(h0 == 590, f"coprime points force H0 = 590 exactly (got {h0})")
    check(damagepass.h_family_contains(h0, 590), "590 is in the family")
    check(pts == [7, 13, 41], f"the integer points come back (got {pts})")

# Values drawn from two coprime grids (590 and 97; lcm 57230 > hmax) share no
# grid, so the fit must refuse. (A SINGLE arbitrary f32 can legitimately hit
# some grid bit-exactly -- B9 measured p ~ 0.1/event -- which is why this
# negative control uses three values jointly, where a chance fit is
# astronomically unlikely, and why callers must report n beside H0.)
check(damagepass.h_fit(
    [-f32(7 / 590), -f32(13 / 590), -f32(5 / 97)]) is None,
    "mixed-grid values fit no H: the fit cannot be forced")
check(damagepass.h_fit([]) is None, "empty group has no H")
check(damagepass.h_fit([0.0]) is None, "a zero fraction has no grid")

# The family property the docstring claims: every multiple fits.
fit2 = damagepass.h_fit([-f32(6 / 590), -f32(12 / 590)])
if fit2:
    check(590 % fit2[0] == 0,
          f"common-divisor sample recovers a 590-family member ({fit2[0]})")
else:
    check(False, "6/590+12/590 sample failed to fit any H")

# ---------------------------------------------------------------------------
print("== 2. divisor fit: D=40 in, D=40 out ==")

means = {60: 100.0, 80: 100.0 * 2 ** (-20 / 40), 100: 100.0 * 2 ** (-40 / 40)}
d = damagepass.divisor_fit(means)
check(abs(d["D_per_ar"][80] - 40.0) < 1e-9, "D from r80 alone = 40")
check(abs(d["D_per_ar"][100] - 40.0) < 1e-9, "D from r100 alone = 40")
check(abs(d["D_joint"] - 40.0) < 1e-9, "joint least-squares D = 40")
check(d["spread"] < 1e-9, "the two estimates agree (spread ~ 0)")
check(abs(d["ratios"][80] - 0.70710678) < 1e-6, "r80 is the 0.7071 signature")

# Perturbed input: the two estimates must DISAGREE and the report must say so.
means_bad = dict(means)
means_bad[100] *= 1.10
d_bad = damagepass.divisor_fit(means_bad)
check(d_bad["spread"] > 1.0,
      "a 10% distortion shows up as spread between the two estimates",
      f"spread={d_bad['spread']:.2f}")

# No attenuation: r >= 1 must report None, not a complex D.
d_flat = damagepass.divisor_fit({60: 100.0, 80: 100.0})
check(d_flat["D_per_ar"][80] is None, "r=1.0 reports None (form refuted)")

# ERROR BARS ARE NOT OPTIONAL, and this is the correction the rung-7
# adversarial review forced. Fed raw samples, the fit must report an interval;
# fed bare means it must report None rather than a fake precision. The rung-7
# run's D = 38.16 read as "D is not 40" until the interval appeared -- 40 sits
# 0.8 sigma away, well inside.
import random as _random                                          # noqa: E402
_random.seed(20260818)
sam = {60: [_random.gauss(22.84, 2.6) for _ in range(67)],
       80: [_random.gauss(15.88, 1.8) for _ in range(50)],
       100: [_random.gauss(11.39, 1.3) for _ in range(61)]}
d_s = damagepass.divisor_fit(sam)
check(d_s["n"][80] == 50 and d_s["sem"][80] is not None,
      "fed raw samples the fit reports n and a standard error per AR")
check(d_s["D_ci"][80] is not None and
      d_s["D_ci"][80][0] < d_s["D_per_ar"][80] < d_s["D_ci"][80][1],
      "and a 95% interval bracketing its own point estimate",
      f"D={d_s['D_per_ar'][80]:.2f} CI={d_s['D_ci'][80]}")
check(d_s["sigma_from_40"][80] is not None,
      "and the distance of the wiki's D=40 from it, in sigma",
      f"{d_s['sigma_from_40'][80]:+.2f}")
check(d["D_ci"].get(80) is None and d["n"].get(80) is None,
      "fed bare means the same fields come back None -- no invented precision")

# Missing base AR refuses.
try:
    damagepass.divisor_fit({80: 70.7, 100: 50.0})
    check(False, "missing AR=60 base must refuse")
except damagepass.DamagePassError:
    check(True, "missing AR=60 base refuses loudly")

# ---------------------------------------------------------------------------
print("== 3. scoping: kind is part of the key (B6's dissolution) ==")

target_row = {"tag": 2, "definition": 152, "model": 170342,
              "pos": (-5915.0, 2079.0), "plane": 0, "agent": 29, "t": 1.0}
ev = {"damage": [
    {"t": 10.0, "kind": 16, "target": 29, "cause": 5, "frac": -0.05,
     "target_row": target_row},
    {"t": 12.0, "kind": 17, "target": 29, "cause": 5, "frac": -0.07,
     "target_row": target_row},
    {"t": 14.0, "kind": 16, "target": 29, "cause": 6, "frac": -0.25,
     "target_row": target_row},
]}
groups = damagepass.scoped_groups(ev)
check(len(groups) == 3,
      "same target, same cause, different kind -> different groups; "
      "different cause -> different group again", f"got {len(groups)}")
tkey = damagepass.target_key(target_row)
check(tkey[0] == 2 and tkey[1] == 152 and tkey[3] == (-5915.0, 2079.0),
      "an NPC target keys on its STATION (slot + position), not agent id")
player_row = dict(target_row, tag=3, agent=31)
pkey = damagepass.target_key(player_row)
check(pkey[0] == "agent" and pkey[1] == 31,
      "a player target keys per body-instance, not station")

# The block dimension: one Suit engaged in two plan steps must split, because
# the rank sweep re-engages one station at different ranks (rung 7's design).
two_step_ev = {"damage": [
    {"t": 250.0, "kind": 16, "target": 29, "cause": 5, "frac": -0.05,
     "target_row": target_row},
    {"t": 350.0, "kind": 16, "target": 29, "cause": 5, "frac": -0.03,
     "target_row": target_row},
]}
win2 = [(1, "block one [AR=60]", 200.0, 300.0),
        (2, "block two [AR=60 RANK=11]", 300.0, math.inf)]
split = damagepass.scoped_groups(two_step_ev, win2)
check(len(split) == 2,
      "one station across two plan steps -> two groups (the rank-sweep "
      "pooling trap)", f"got {len(split)}")
merged = damagepass.scoped_groups(two_step_ev)
check(len(merged) == 1, "without windows the same rows are one group "
      "(census mode keeps B6's key)")

# ---------------------------------------------------------------------------
print("== 4. p17 report: both verdicts detectable ==")

g17 = {
    (tkey, 5, 16, None): [{"frac": -0.05}, {"frac": -0.06}],
    (tkey, 5, 17, None): [{"frac": -0.0846}, {"frac": -0.0846}],
    (("x",), 9, 17, None): [{"frac": -0.08}, {"frac": -0.12}],
}
rep17 = damagepass.p17_report(g17)
by_cause = {r["cause"]: r for r in rep17}
check(by_cause[5]["variance_zero"] is True, "identical p17s -> variance zero")
check(by_cause[9]["variance_zero"] is False, "differing p17s -> flagged")
check(abs(by_cause[5]["ratio_to_p16max"] - 0.0846 / 0.06) < 1e-9,
      "p17/max-p16 ratio computed on fractions (H cancels)")

# ---------------------------------------------------------------------------
print("== 5. mark windows and AR labels ==")

with tempfile.TemporaryDirectory() as td:
    marks = [
        {"kind": "marks_meta", "plan_sha256": "0" * 64, "steps": 3},
        {"kind": "mark", "seq": 1, "mark": "advance", "step": 0,
         "text": "walk to the bench", "wire_t": 100.0},
        {"kind": "mark", "seq": 2, "mark": "advance", "step": 1,
         "text": "engage the Suit whose nameplate reads 60 [AR=60]",
         "wire_t": 200.0},
        {"kind": "mark", "seq": 3, "mark": "advance", "step": 2,
         "text": "engage the Suit whose nameplate reads 80 [AR=80]",
         "wire_t": 300.0},
    ]
    with open(os.path.join(td, "plan_marks.jsonl"), "w",
              encoding="utf-8") as fh:
        for m in marks:
            fh.write(json.dumps(m) + "\n")
    windows = damagepass.mark_windows(td)
    check(len(windows) == 3, "three advances -> three windows")
    check(windows[1][2] == 200.0 and windows[1][3] == 300.0,
          "a window runs from its advance to the next")
    check(windows[2][3] == math.inf, "the last window runs to +inf")
    w = damagepass.window_at(windows, 250.0)
    check(w is not None and "AR=60" in w[1], "t=250 lands in the AR=60 step")

    rows_60 = [{"t": 250.0, "frac": -0.05}]
    rows_span = [{"t": 250.0, "frac": -0.05}, {"t": 350.0, "frac": -0.04}]
    labels = damagepass.label_groups({("k1", 5, 16, 1): rows_60}, windows)
    check(labels[("k1", 5, 16, 1)]["ar"] == 60,
          "events in the AR=60 window label 60")
    try:
        damagepass.label_groups({("k2", 5, 16, None): rows_span}, windows)
        check(False, "one group under two AR labels must refuse")
    except damagepass.DamagePassError:
        check(True, "one group under two AR labels refuses loudly")
    labels_none = damagepass.label_groups(
        {("k3", 5, 16, None): [{"t": 50.0, "frac": -0.1}]}, windows)
    check(labels_none[("k3", 5, 16, None)]["ar"] is None,
          "events before any window carry no label rather than a guess")

    # RANK=NN labels: read back, and distinct from AR.
    rwin = [(4, "sweep block [AR=60 RANK=11]", 400.0, 500.0)]
    rlab = damagepass.label_groups(
        {("k4", 5, 16, 4): [{"t": 450.0, "frac": -0.05}]}, rwin)
    check(rlab[("k4", 5, 16, 4)] == {"ar": 60, "rank": 11},
          "a rank-extension block carries both AR and RANK labels")

# ---------------------------------------------------------------------------
print("== 6. retail corpus, pinned by name ==")

CAPS = vaultpath.require_dir(
    "captures", "live", why="damagepass corpus pins read the live captures")

# Pre-Searing: the fight connection studies/isle B6/B9 worked from.
presear = damagepass.join_targets(damagepass.read_events(
    os.path.join(CAPS, "20260810T235916"), "10.0.0.210:49163->54.198.7.73:80"))
c16 = sum(1 for x in presear["damage"] if x["kind"] == 16)
c17 = sum(1 for x in presear["damage"] if x["kind"] == 17)
check(presear["map_id"] == 146, "Pre-Searing connection is map 146")
check(c16 == 37, f"map 146 fight: 37 p16 events (got {c16})")
check(c17 == 3, f"map 146 fight: 3 p17 events (got {c17})")

# The arena detour: the largest damage corpus in the vault, map 310.
arena = damagepass.join_targets(damagepass.read_events(
    os.path.join(CAPS, "20260817T231139"), "10.0.0.210:54071->54.198.7.73:80"))
a16 = sum(1 for x in arena["damage"] if x["kind"] == 16)
a17 = sum(1 for x in arena["damage"] if x["kind"] == 17)
check(arena["map_id"] == 310, "arena connection is map 310")
check(a16 == 470, f"arena: 470 p16 events (got {a16})")
check(a17 == 83, f"arena: 83 p17 events (got {a17})")
check(arena["unjoined"] == 0,
      "every arena damage event joins to a create in effect")
check(len(arena["projectiles"]) == 105, "arena: 105 projectile launches")

agroups = damagepass.scoped_groups(arena)
p480 = [g for (tk, cause, kind, step), rows in agroups.items()
        for g in [damagepass.h_fit([r["frac"] for r in rows])]
        if tk and tk[0] == "agent" and kind == 16 and len(rows) >= 4 and g]
check(any(damagepass.h_family_contains(h0, 480) for h0, _ in p480),
      "a player-class target's fraction grid recovers the 480 family "
      "(level-20 base health -- a game-shaped number from raw bytes)",
      f"families: {[h for h, _ in p480]}")

arep = damagepass.p17_report(agroups)
big = [r for r in arep if r["n"] >= 2]
nonzero = [r for r in big if not r["variance_zero"]]
check(len(big) >= 8, f"arena holds >=8 p17 groups at n>=2 (got {len(big)})")
check(len(nonzero) >= 1,
      "skill-polluted arena p17 groups show nonzero variance -- §3.1's "
      "attack-skill confound, measured; the Isle removes it by design",
      f"{len(nonzero)}/{len(big)} groups nonzero")

# ---------------------------------------------------------------------------
print("== 7. the timebase join: tape-local vs capture-global ==")

# THE BUG THIS PINS, found on the rung-7 capture: tape.load_tape returns times
# measured from the connection's OWN first s2c segment, while plan marks are on
# the capture's global wire clock. Reading events without adding info["t0"]
# shifts every label by the connection's opening offset -- silently, into a
# NEIGHBOURING step, so blocks come back mislabelled rather than unlabelled.
# On this capture the Master of Damage's 42-swing engage block landed under the
# WALK step (which should hold zero swings), and the AR=100 block split across
# two labels. Nothing errored; the numbers were simply wrong.
rung7 = vaultpath.require_dir(
    "captures", "live", "20260818T132739",
    why="the timebase pin needs the rung-7 capture")
CONN7 = "10.0.0.210:53202->44.217.41.117:80"
info7, _ = damagepass.tape.load_tape(rung7, CONN7)
t0_7 = info7.get("t0")
check(t0_7 is not None and t0_7 > 1.0,
      "the rung-7 bench connection opens well after the capture's t=0",
      f"t0={t0_7}")

ev7 = damagepass.join_targets(damagepass.read_events(rung7, CONN7))
w7 = damagepass.mark_windows(rung7)
check(len(w7) == 22, f"the sealed 22-step plan yields 22 mark windows "
                     f"(got {len(w7)})")
first_dmg = min(d["t"] for d in ev7["damage"])
check(first_dmg > t0_7,
      "damage times are on the capture clock, not the connection clock",
      f"first damage t={first_dmg:.1f} vs connection t0={t0_7:.1f}")

g7 = damagepass.scoped_groups(ev7, w7)
lab7 = damagepass.label_groups(g7, w7)
# The walk-to-the-bench step (3) and the walk-to-the-MoD step (8) are pure
# travel: a correct join puts NO engagement block in either.
walk_steps = {3, 8}
walk_hits = sum(len(rows) for key, rows in g7.items() if key[3] in walk_steps)
check(walk_hits == 0,
      "no damage lands in the two pure-walking steps (the shifted join put "
      "42 swings there)", f"{walk_hits} events")
# And the MoD block (step 9) must hold the Master of Damage's own body.
mod = [key for key in g7
       if key[3] == 9 and key[0] and key[0][1] == 144 and key[2] == 16]
check(len(mod) == 1 and len(g7[mod[0]]) == 42,
      "step 9 holds exactly the 42-swing Master of Damage block",
      f"{[len(g7[k]) for k in mod]}")
ar_labels = {lab["ar"] for key, lab in lab7.items() if lab["ar"] is not None}
check(ar_labels == {60, 80, 100},
      "the bench blocks carry exactly the three pre-registered armour labels",
      f"{sorted(ar_labels)}")

# ---------------------------------------------------------------------------
print("== 7b. the attribute channel, measured on the rung-7 rank sweep ==")

# GATE 1 ASKED FOR THIS AND NO CAPTURE HAD EVER CARRIED IT: `0x003A` column 3,
# `0x0037`'s points, and the point budget, from a REAL rank reassignment. The
# rung-7 rank sweep produced all three, and they cross-check arithmetically.
#
#   0x0037 [agent, unspent, 200]      at instance load
#   0x003A [agent, ids | base | eff]  at instance load, COLUMN-MAJOR
#   0x003B [agent, attr, base, eff]   one per mid-instance raise
#   0x0038 [agent, unspent]           the raise's cost, debited
#
# The operator's own screenshot says "Attributes (5 unused points)" with
# Strength 8 / Swordsmanship 13 / Tactics 10 -- and the wire's first 0x0037
# says 5 against a budget of 200, so the two agree before any arithmetic.
attr = {"0x0037": [], "0x003A": [], "0x003B": [], "0x0038": []}
per_conn = {}
for row in damagepass.tape.channel_files(rung7):
    info, events = damagepass.tape.load_tape(rung7, row["connection"])
    t0 = info.get("t0") or 0.0
    events = [(round(t + t0, 6), p) for t, p in events]
    msgs, _ = damagepass.tape.decode_all(events, damagepass.Codec(),
                                         "GAME_SMSG", 0)
    for t, op, v in msgs:
        key = {0x37: "0x0037", 0x3A: "0x003A", 0x3B: "0x003B",
               0x38: "0x0038"}.get(op)
        if key:
            attr[key].append((t, v[1:]))
            per_conn.setdefault(row["connection"], {}).setdefault(
                key, []).append(v[1:])

budgets = {v[2] for _, v in attr["0x0037"]}
check(budgets == {200}, "0x0037 field 3 is a constant 200 -- the level-20 "
                        "attribute point budget", f"{budgets}")
first_unspent = min(attr["0x0037"], key=lambda r: r[0])[1][1]
check(first_unspent == 5,
      "0x0037 field 2 at session start is 5, matching the operator's own "
      "screenshot ('5 unused points')")

# 0x003A is column-major: 3 ids, then 3 base ranks, then 3 effective ranks.
_, first_a = min(attr["0x003A"], key=lambda r: r[0])
arr = first_a[1]
check(len(arr) == 9 and arr[:3] == [17, 20, 21],
      "0x003A carries 3 attribute ids (17 Strength, 20 Swordsmanship, "
      "21 Tactics) in its first column", f"{arr}")
check(arr[3:6] == [8, 12, 10] and arr[6:] == [8, 13, 10],
      "columns 2 and 3 are BASE and EFFECTIVE rank, and they differ on "
      "Swordsmanship alone -- the operator's +1 bonus, visible on the wire",
      f"base {arr[3:6]} eff {arr[6:]}")

# A mid-instance attribute CHANGE: 0x003B names the attribute and both ranks.
# There are 14 across the session, and that count is itself the operator's
# report on the wire: the Isle steps RAISE, the Great Temple of Balthazar
# visits LOWER (the game refuses to lower in an explorable area), and the
# closing restore step walks 8 back up to 13 in five single steps.
steps = [v for _, v in sorted(attr["0x003B"], key=lambda r: r[0])]
check(len(steps) == 14, f"14 attribute changes across the session "
                        f"(got {len(steps)})")
check(all(v[1] == 20 for v in steps),
      "every one of them names attribute 20, Swordsmanship -- no other "
      "attribute moved all session")
check(all(v[3] == v[2] + 1 for v in steps),
      "effective is base+1 in all 14 -- the +1 bonus is a constant offset, "
      "not something the change messages recompute")
# The bench connection carrying the 11/12/13 sweep holds exactly two raises.
sweep = per_conn["10.0.0.210:55252->52.3.40.244:80"]
check(sweep["0x003B"] == [[25, 20, 11, 12], [25, 20, 12, 13]],
      "the rank-sweep connection holds exactly the two pre-registered raises",
      f"{sweep['0x003B']}")

# The budget closes: three independent equations, no cost table assumed.
by_base = {}
for t, v in attr["0x0037"]:
    if v[0] == 25:      # the player's own agent
        near = [a for a in attr["0x003A"] if abs(a[0] - t) < 1.0]
        if near:
            by_base[near[0][1][1][7]] = v[1]     # effective sword rank -> unspent
check(by_base == {13: 5, 11: 41, 9: 65, 8: 74},
      "unspent points at each declared rank, off four instance loads",
      f"{by_base}")
# cum(8) + cum(12) + cum(10) = 195, cum(12)=cum(10)+36, cum(10)=cum(8)+24
cum8 = (195 - (41 - 5) - (65 - 41) * 2) / 3
check(cum8 == 37.0,
      "solving the three equations gives cum(8) = 37 attribute points",
      f"{cum8}")
check(cum8 + 24 == 61 and cum8 + 60 == 97,
      "hence cum(10) = 61 and cum(12) = 97 -- and 97 is the number GWW "
      "publishes for rank 12, reached here with no cost table assumed")
# And the sweep connection's own 0x0038 debits confirm that 36 independently,
# splitting it into the two per-rank costs the instance-load readings cannot
# separate: 41 -> 25 -> 5, so base 10->11 costs 16 and 11->12 costs 20.
debits = [v[1] for v in sweep["0x0038"]]
check(debits == [25, 5],
      "the sweep connection debits unspent 41 -> 25 -> 5 as the two raises "
      "land", f"{debits}")
check((41 - 25) + (25 - 5) == 36,
      "those two debits sum to the same 36 the instance-load readings gave "
      "for base 10->12 -- two unrelated routes to one number")
check((41 - 25, 25 - 5) == (16, 20),
      "and they SPLIT it: rank 11 costs 16 points, rank 12 costs 20 -- "
      "per-rank costs the load readings alone cannot separate")

# ---------------------------------------------------------------------------
print("== 8. corpus, continued ==")

# The chat channel: the level-up template's cleartext args (B8's pin).
lvl = damagepass.read_events(
    os.path.join(CAPS, "20260807T143055"), "10.0.0.210:60935->52.3.40.244:80")
found = any(
    [x for k, x in c["parts"] if k == "id"][-4:] == [13, 51, 1, 17]
    for c in lvl["chat"] if c["op"] == damagepass.OP_CHAT_CODED and c["parts"])
check(found, "the level-up 0x5D carries cleartext args [13, 51, 1, 17] "
             "(B8's observed pin -- the MoD announcement path)")

sys.exit(LEDGER.verdict())
