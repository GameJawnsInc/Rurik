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

# Floor set from the first real green run (41 checks, 2026-08-18); every
# section runs unconditionally, so the mandatory core is the whole file.
LEDGER = checks.Ledger("damagepass", floor=41)
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

# ---------------------------------------------------------------------------
print("== 4. p17 report: both verdicts detectable ==")

g17 = {
    (tkey, 5, 16): [{"frac": -0.05}, {"frac": -0.06}],
    (tkey, 5, 17): [{"frac": -0.0846}, {"frac": -0.0846}],
    (("x",), 9, 17): [{"frac": -0.08}, {"frac": -0.12}],
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
    labels = damagepass.label_groups({("k1", 5, 16): rows_60}, windows)
    check(labels[("k1", 5, 16)] == 60, "events in the AR=60 window label 60")
    try:
        damagepass.label_groups({("k2", 5, 16): rows_span}, windows)
        check(False, "one group under two AR labels must refuse")
    except damagepass.DamagePassError:
        check(True, "one group under two AR labels refuses loudly")
    labels_none = damagepass.label_groups(
        {("k3", 5, 16): [{"t": 50.0, "frac": -0.1}]}, windows)
    check(labels_none[("k3", 5, 16)] is None,
          "events before any window carry no label rather than a guess")

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
p480 = [g for (tk, cause, kind), rows in agroups.items()
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

# The chat channel: the level-up template's cleartext args (B8's pin).
lvl = damagepass.read_events(
    os.path.join(CAPS, "20260807T143055"), "10.0.0.210:60935->52.3.40.244:80")
found = any(
    [x for k, x in c["parts"] if k == "id"][-4:] == [13, 51, 1, 17]
    for c in lvl["chat"] if c["op"] == damagepass.OP_CHAT_CODED and c["parts"])
check(found, "the level-up 0x5D carries cleartext args [13, 51, 1, 17] "
             "(B8's observed pin -- the MoD announcement path)")

sys.exit(LEDGER.verdict())
