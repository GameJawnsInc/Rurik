r"""Health regeneration on retail's wire: the natural ramp, the signed pip sum,
and the one message that ends a positive rate at full health.

    python toolkit/authsrv/regenjoin.py            # every live capture
    python toolkit/authsrv/regenjoin.py --json

WHY THIS EXISTS. Until 2026-10-07 our server sent property 44 (0x00A2 [44,
agent, f32], the NET health-regeneration rate in max-health fractions per
second, 2/H per pip -- studies/isle B4) only as DEGENERATION: `push_regen`'s
rate was -(pips x 2)/H and nothing raised health over time. Retail's corpus
carries 760 positive words. This instrument reads them, states what they
obey, and is the referee every regen or degen row is scored against
(studies/skills/FINDINGS.md 64, SKILLS-RG).

THE PREDICTIONS, registered before the first run (NOTES of the desk-regen
lane, 2026-10-07; the outcome of each is printed by `main` and recorded in
the study -- two of them were refuted in part, and the instrument keeps the
registered form beside the corrected one rather than rewriting it):

  P1  APPLY WORDS. At a 0x0042 whose wearer's natural term is zero (the word
      before the batch equals the effects-only sum -- `natural_zero`), the
      [44] word in the batch is the SIGNED pip sum of the wearer's live
      episodes, clamped ONCE to [-10, +10]: degeneration (the four
      conditions' table, a hex's slot) negative, regeneration (a regen
      skill's slot) positive, each slot interpolated at the episode's rank
      (field 3) by the client's formula. 446 +3 (rank 0), 814 +5, 288 +8 at
      rank 13, and 288 on 20260928T103123 :50061 at -13 + 8 = -5.
  P2  NATURAL DELAY. (a) no natural first step lands < 4.90 s after the
      wearer's last LOSS (a damage word, a negative 55, the end of a
      negative-rate window); (b) the modal delay bin is [4.90, 5.10].
      (c, registered: the wearer's own skill/attack ACTIVATIONS also anchor.)
  P3  STEPS. >= 95 % of consecutive natural +1 steps are 2.00 +- 0.10 s apart.
  P4  BOUNDS. No word beyond +-10 pips where the maximum is known.
  P5  NATURAL ZERO UNDER DEGENERATION. No natural step while the wearer's
      net word is negative; a degeneration apply on a running ramp sends the
      effects-only sum (the natural term drops to 0, not natural - degen).

WHAT THE CORPUS SAID (`score`; numbers in the study, never typed here):
  * P2 as registered is REFUTED IN PART: a natural first step also follows,
    by 5.00 s, the wearer's OWN attack (the swing's start, its hit, a ranged
    launch 0x00A4) and its own offensive skill COMPLETION, and a skill another
    agent aims AT the wearer (its activation, then its landing). P2(c) as
    registered -- any own activation -- is refuted outright: a self heal
    (Healing Signet) never resets the ramp. `ANCHOR_CLASSES` is the corrected
    set; `first_steps` scores both.
  * The natural ramp CAPS AT +7 (`cap_witnesses`): with health still below
    the maximum (no [32] for seconds after), no word ever carries an 8th step.
  * Property 32 (GV_MAX_HP_REACHED, 0x009F [32, agent, 0]) ends a positive
    rate on a FULL wearer: every one follows a positive word, and it is the
    whole close batch of a regen effect -- the "silent" regen closes are not
    silent, they carry 32 instead of a [44]. The client's handler (build
    38797, the int record path 0x00818170, case 32 at 0x008181E5) sets the
    health fraction to 1.0 (0x009215F0, the setter property 34 uses at
    0x0081828D) and the health REGEN to 0.0 (0x00921780, the setter property
    44 uses at 0x008182C5) -- OBSERVED, a static read.

THE LABELS: everything numeric here is OBSERVED on the live corpus; the slot
endpoints are the client's own table (toolkit/clientscan/skilltable.py,
carried below and checked against the vault's rows by test_regenjoin). What
the corpus cannot say is printed as such: an agent kind whose effects are
not on the wire (another PLAYER in PvP: its 0x0042 never reaches the
observer) is reported, never scored.

Standard library only. Reads the vault through `vaultpath`; a connection its
manifest declares gapped is set aside BY NAME (deepwoundjoin.whole_s2c ->
capgaps), and any other refusal raises.
"""
import argparse
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

import adrenjoin       # noqa: E402  (whose_agent: the observer by property 41)
import bufflog         # noqa: E402
import deepwoundjoin   # noqa: E402  (whole_s2c: the set-aside; sequence)
import vaultpath       # noqa: E402

OP_CREATE = 0x0020
OP_APPLY = 0x0042
OP_REMOVE = 0x0044
OP_INT = 0x009F            # [prop, agent, value]
OP_INT_T = 0x00A0          # [prop, a, b, value]
OP_FLOAT = 0x00A2          # [prop, agent, f32]
OP_FLOAT_T = 0x00A3        # [prop, target, cause, f32]
OP_LAUNCH = 0x00A4         # [shooter, aim, 0, flight, ...] -- a ranged release

PROP_REGEN = 44
PROP_HEALTH_MAX = 42
PROP_MAX_HP_REACHED = 32   # agents.GV_MAX_HP_REACHED
PROP_DAMAGE = (16, 17)
PROP_ARMOR_IGNORING = 55   # signed: a heal (+) or a sacrifice / steal (-)
PROP_ATTACK_STARTED = 4    # 0x00A0 [4, attacker, target]
PROP_SWING_DONE = (1, 2, 47)        # 0x009F [p, attacker]: a melee strike's instant
PROP_ACTIVATIONS = (60, 50, 48)     # 0x00A0 [p, caster, target, skill]
PROP_COMPLETIONS = (58, 46)         # 0x009F [p, caster, 0]
PROP_EFFECT_ON_TARGET = 20          # 0x00A0 [20, target, caster, visual]: a landing

BATCH = 0.050              # the corpus's batch shoulder (deepwoundjoin.BATCH)
NATURAL_DELAY = 5.0        # P2
NATURAL_STEP = 2.0         # P3
TOL = 0.10
NATURAL_CAP = 7            # OBSERVED (cap_witnesses) -- NOT the net clamp
NET_CAP = 10               # P1/P4: one clamp on the signed sum
UNIT_TOL = 0.02            # pips: a word is an integer pip count within this

HOSTILE_TOKENS = ("mon1", "band")      # npcdefs.HOSTILE_TOKENS

# THE FOUR DEGENERATING CONDITIONS (effects.CONDITION_PIPS; WIKI, GWW "Health
# degeneration", read for studies/isle 5) and the six that move no rate.
CONDITION_PIPS = {478: 3, 480: 7, 483: 4, 484: 4}
RATE_FREE_CONDITIONS = (479, 481, 482, 485, 486, 2077)

# THE SLOTS, carried: the client's own table (skilltable.py), build 38974 unless
# keyed. Sign +1 regenerates, -1 degenerates. `test_regenjoin` section 0 checks
# every row against the vault's `skills` rows where the vault has them, so a
# carried number that drifts from the extractor goes red, not quiet.
#   (which slot, lo, hi, sign)
RATE_SLOTS = {
    446: ("scale", 3, 10, +1),         # type 10, args 2: the scale bit set
    288: ("scale", 4, 9, +1),          # type 6, args 2
    814: ("bonus_scale", 5, 10, +1),   # type 6, args 7 (its scale 40..100 is its end heal)
    31: ("scale", 5, 5, -1),           # type 4, args 1: bit CLEAR, equal endpoints (flat 5)
    44: ("scale", 1, 4, -1),           # type 4, args 7
    108: ("scale", 0, 3, -1),          # type 4, args 1: bit CLEAR, differing (row 108 carries them)
}
# Faintheartedness 135's bonus slot moved between builds (test_mechanics 35).
RATE_SLOTS_BY_BUILD = {
    135: {38797: ("bonus_scale", 0, 3, -1), 38888: ("bonus_scale", 1, 3, -1),
          38974: ("bonus_scale", 1, 3, -1)},
}


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def interp(lo, hi, rank):
    """The client's two-point scaler (effects.interp; 0x005A8920)."""
    exact = lo + (hi - lo) * rank / 15.0
    return max(0, int(math.floor(exact + 0.5)))


def signed_pips(skill, rank, build=None):
    """A skill's signed pips at `rank` (+ regeneration, - degeneration), 0 for
    a rate-free condition, or None when this module carries no number for it."""
    if skill in CONDITION_PIPS:
        return -CONDITION_PIPS[skill]
    if skill in RATE_FREE_CONDITIONS:
        return 0
    row = RATE_SLOTS.get(skill)
    if row is None and skill in RATE_SLOTS_BY_BUILD:
        row = RATE_SLOTS_BY_BUILD[skill].get(build)
    if row is None:
        return None
    _which, lo, hi, sign = row
    return sign * interp(lo, hi, rank)


def net_sum(pips, separate_caps=False, unsigned=False):
    """The wire's sum of signed pips: ONE clamp to [-10, +10] (P1).

    `separate_caps` is the known-bad arm the 288 witness refutes: the
    degeneration clamped to -10 FIRST, the regeneration added after.
    `unsigned` is the other: min(sum, +10) with no floor."""
    if separate_caps:
        degen = max(sum(p for p in pips if p < 0), -NET_CAP)
        return max(-NET_CAP, min(NET_CAP, degen + sum(p for p in pips if p > 0)))
    total = sum(pips)
    if unsigned:
        return min(total, NET_CAP)
    return max(-NET_CAP, min(NET_CAP, total))


# ---------------------------------------------------------------------------
# reading

def sequence(cap_dir, connection, codec):
    """(seq, build): deepwoundjoin.sequence plus the tape's own build."""
    import tape
    _info, events = tape.load_tape(cap_dir, connection)
    return deepwoundjoin.sequence(cap_dir, connection, codec), getattr(events, "build", None)


def timeline(seq, build=None):
    """Everything this instrument reads from one connection, per agent.

    Returns {"observer", "tokens" {agent: fourcc}, "build", "words" {agent:
    [(t, rate)]}, "hmax" {agent: [(t, H)]}, "anchors" {agent: [(t, class)]},
    "full" {agent: [t]}, "episodes" (bufflog.episodes rows)}. Anchor classes:
      LOSS       a damage word or a negative 55 on the agent
      OWN_START  0x00A0 [4, agent, x]: the agent's own swing begins
      OWN_HIT    the agent's own strike instant: 0x009F [1|2|47, agent] (a
                 melee strike), 0x00A4 it launched (a ranged release)
      DEALT      a damage word the agent CAUSED (reported, not an anchor: a
                 projectile's lands a flight after the release that anchors)
      OWN_CAST   the agent's completion [58|46] of an activation it AIMED AT A
                 FOE (a different allegiance token, neither 'nonc')
      TARGETED   another agent's activation naming the agent, and that skill's
                 landing ([20, agent, caster])
      SELF_CAST  the agent's completion of a skill aimed at itself or an ally
                 (scored as NOT an anchor -- P2(c)'s refutation)
    """
    s2c = [(t, op, v) for _i, t, op, v in seq]
    out = {"observer": adrenjoin.whose_agent(s2c), "tokens": {}, "build": build,
           "words": collections.defaultdict(list), "hmax": collections.defaultdict(list),
           "anchors": collections.defaultdict(list), "full": collections.defaultdict(list)}
    ev = {"applies": [], "removes": []}
    aimed = {}                       # caster -> target of its last activation
    for t, op, v in s2c:
        if op == OP_CREATE and len(v) > 12:
            out["tokens"][v[1]] = int(v[12]).to_bytes(4, "big").decode("latin1")
    tok = out["tokens"]

    def foes(a, b):
        ta, tb = tok.get(a), tok.get(b)
        return ta is not None and tb is not None and ta != tb and "nonc" not in (ta, tb)

    for t, op, v in s2c:
        if op == OP_APPLY:
            ev["applies"].append({"t": t, "target": v[1], "skill": v[2], "field3": v[3],
                                  "buff": v[4], "duration": _f32(v[5])})
        elif op == OP_REMOVE:
            ev["removes"].append({"t": t, "target": v[1], "buff": v[2]})
        elif op == OP_FLOAT and v[1] == PROP_REGEN:
            out["words"][v[2]].append((t, _f32(v[3])))
        elif op == OP_INT and v[1] == PROP_HEALTH_MAX:
            out["hmax"][v[2]].append((t, v[3]))
        elif op == OP_INT and v[1] == PROP_MAX_HP_REACHED:
            out["full"][v[2]].append(t)
        elif op == OP_FLOAT_T and v[1] in PROP_DAMAGE:
            if _f32(v[4]) < 0:
                out["anchors"][v[2]].append((t, "LOSS"))
            if v[3] != v[2]:
                # the CAUSE's damage word is NOT its anchor: a ranged hit lands a
                # flight after the release, and the release is what anchors
                # (20260914T005758 hostile 54: 0x00A4 at -5.001, the hit -4.396)
                out["anchors"][v[3]].append((t, "DEALT"))
        elif op == OP_FLOAT_T and v[1] == PROP_ARMOR_IGNORING and _f32(v[4]) < 0:
            out["anchors"][v[2]].append((t, "LOSS"))
        elif op == OP_LAUNCH:
            out["anchors"][v[1]].append((t, "OWN_HIT"))
        elif op == OP_INT and v[1] in PROP_SWING_DONE:
            out["anchors"][v[2]].append((t, "OWN_HIT"))
        elif op == OP_INT_T and v[1] == PROP_ATTACK_STARTED:
            out["anchors"][v[2]].append((t, "OWN_START"))
        elif op == OP_INT_T and v[1] in PROP_ACTIVATIONS:
            caster, target = v[2], v[3]
            aimed[caster] = target
            if target != caster:
                out["anchors"][target].append((t, "TARGETED"))
        elif op == OP_INT and v[1] in PROP_ACTIVATIONS:
            aimed[v[2]] = v[2]                      # untargeted: self
        elif op == OP_INT_T and v[1] == PROP_EFFECT_ON_TARGET and v[2] != v[3]:
            out["anchors"][v[2]].append((t, "TARGETED"))
        elif op == OP_INT and v[1] in PROP_COMPLETIONS:
            caster = v[2]
            target = aimed.pop(caster, None)
            if target is not None and target != caster and foes(caster, target):
                out["anchors"][caster].append((t, "OWN_CAST"))
            else:
                out["anchors"][caster].append((t, "SELF_CAST"))
    out["episodes"] = bufflog.episodes(ev)
    return out


def kind_of(tl, agent):
    """'player' (the observer), 'hostile', or 'other' (an ally, another
    player, an NPC -- their effects mostly never reach the observer)."""
    if agent == tl["observer"]:
        return "player"
    if tl["tokens"].get(agent) in HOSTILE_TOKENS:
        return "hostile"
    return "other"


def health_max(tl, agent, t):
    """The agent's maximum at `t`: the last 42 at or before the batch's end
    (a 42 riding the same batch BEHIND the word counts -- Deep Wound's)."""
    best = None
    for tt, h in tl["hmax"].get(agent, ()):
        if tt <= t + BATCH:
            best = h
    return best


def pips_of(tl, agent, t, rate):
    h = health_max(tl, agent, t)
    return None if not h else rate * h / 2.0


def _near(times, t):
    return any(abs(x - t) <= BATCH for x in times)


def effect_times(tl, agent):
    out = []
    for e in tl["episodes"]:
        if e["target"] == agent:
            out.append(e["t"])
            if e["close_t"] is not None:
                out.append(e["close_t"])
    return out


# ---------------------------------------------------------------------------
# the natural ramp

def natural_runs(tl, agent):
    """Observed natural runs: a word one unit above a ZERO word with no effect
    event in its batch starts one; each further word one unit higher, no
    effect event in its batch, extends it. The unit is 2/H where H is known,
    else the agent's first such step. Returns [{"t", "levels" [(t, level)],
    "unit", "next" (the word after the run or None)}]."""
    ws = list(tl["words"].get(agent, ()))     # WIRE order: never re-sort a batch
    eff = effect_times(tl, agent)
    unit = None
    runs = []
    k = 1
    while k < len(ws):
        t, r = ws[k]
        prev = ws[k - 1]
        u = None
        h = health_max(tl, agent, t)
        if h:
            u = 2.0 / h
        elif unit is not None:
            u = unit
        if (prev[1] == 0.0 and r > 0 and not _near(eff, t)
                and (u is None or abs(r - u) <= u * UNIT_TOL)):
            u = u or r
            unit = unit or r
            levels = [(t, 1)]
            j = k + 1
            while (j < len(ws) and not _near(eff, ws[j][0])
                   and abs(ws[j][1] - ws[j - 1][1] - u) <= u * UNIT_TOL):
                levels.append((ws[j][0], levels[-1][1] + 1))
                j += 1
            runs.append({"t": t, "levels": levels, "unit": u,
                         "next": ws[j] if j < len(ws) else None})
            k = j
            continue
        k += 1
    return runs


def negative_ends(tl, agent):
    """Times the agent's net word went from negative to >= 0 (a degeneration
    window closing: the last instant of a continuous loss)."""
    ws = list(tl["words"].get(agent, ()))     # WIRE order: never re-sort a batch
    return [ws[k][0] for k in range(1, len(ws)) if ws[k - 1][1] < 0 <= ws[k][1]]


# The anchor sets the study compares. REGISTERED is P2 as written before the
# run; ANCHOR_CLASSES is the corpus's own; ACTIVATIONS adds P2(c)'s refuted
# reading (any own activation, self casts included).
REGISTERED = ("LOSS", "NEGEND")
ANCHOR_CLASSES = ("LOSS", "NEGEND", "OWN_START", "OWN_HIT", "OWN_CAST", "TARGETED")
ACTIVATIONS = ANCHOR_CLASSES + ("SELF_CAST",)


def first_steps(tl, classes=ANCHOR_CLASSES, delay=NATURAL_DELAY):
    """[{"agent", "kind", "t", "anchor", "class", "delay"}] for every natural
    run's first step that has an anchor of `classes` before it."""
    out = []
    for agent in tl["words"]:
        anchors = list(tl["anchors"].get(agent, ()))
        if "NEGEND" in classes:
            anchors += [(t, "NEGEND") for t in negative_ends(tl, agent)]
        anchors = sorted(a for a in anchors if a[1] in classes)
        for run in natural_runs(tl, agent):
            before = [a for a in anchors if a[0] <= run["t"] + 1e-6]
            if not before:
                continue
            at, cls = before[-1]
            out.append({"agent": agent, "kind": kind_of(tl, agent), "t": run["t"],
                        "anchor": at, "class": cls, "delay": run["t"] - at,
                        "on_time": abs(run["t"] - at - delay) <= TOL})
    return out


def step_intervals(tl, step=NATURAL_STEP):
    """[(kind, interval, on_time)] between consecutive steps of every run."""
    out = []
    for agent in tl["words"]:
        for run in natural_runs(tl, agent):
            lv = run["levels"]
            for a, b in zip(lv, lv[1:]):
                out.append((kind_of(tl, agent), b[0] - a[0], abs(b[0] - a[0] - step) <= TOL))
    return out


def cap_witnesses(tl, cap=NATURAL_CAP):
    """Runs that STOP at their top with health still below the maximum: no
    [32] and no anchor within STEP + TOL of the top step, while the next word,
    the next [32] or the next anchor is later still. [(kind, top, gap_s)]. The
    ramp's cap is the top every such run shares; `cap` is only reported."""
    out = []
    for agent in tl["words"]:
        anchors = sorted(t for t, _c in tl["anchors"].get(agent, ()))
        full = sorted(tl["full"].get(agent, ()))
        for run in natural_runs(tl, agent):
            top_t, top = run["levels"][-1]
            nxt = [x for x in ([run["next"][0]] if run["next"] else [])
                   + [a for a in anchors if a > top_t + 1e-6]
                   + [f for f in full if f > top_t - BATCH]]
            gap = (min(nxt) - top_t) if nxt else None
            fulls = [f for f in full if f > top_t - BATCH]
            first_full = fulls[0] if fulls else None
            stopped = gap is not None and gap > NATURAL_STEP + TOL
            below_max = first_full is None or first_full - top_t > NATURAL_STEP + TOL
            if stopped and below_max:
                out.append((kind_of(tl, agent), top, gap))
    return out


def under_degeneration(tl):
    """P5. (a) natural steps observed while the wearer's previous word was
    negative -- impossible by construction of a run (a run starts at a zero
    word), so this counts +1 steps of ANY word above a negative one with no
    effect event in the batch; (b) degeneration applies on a running ramp:
    [(agent, ramp level, apply word pips, effects-only pips)]."""
    steps_under = 0
    onto_ramp = []
    for agent, ws in tl["words"].items():
        ws = list(ws)
        eff = effect_times(tl, agent)
        for k in range(1, len(ws)):
            t, r = ws[k]
            p = pips_of(tl, agent, t, r)
            q = pips_of(tl, agent, t, ws[k - 1][1])
            if p is None or q is None or _near(eff, t):
                continue
            if ws[k - 1][1] < 0 and abs(p - q - 1.0) <= UNIT_TOL:
                steps_under += 1
        for run in natural_runs(tl, agent):
            if run["next"] is None:
                continue
            t, r = run["next"]
            p = pips_of(tl, agent, t, r)
            if p is None or p >= 0:
                continue
            live = live_at(tl, agent, t)
            pips = [signed_pips(s, rank, tl["build"]) for s, rank in live]
            if not live or any(x is None for x in pips):
                continue
            if not any(x < 0 for x in pips):
                continue
            onto_ramp.append((agent, run["levels"][-1][1], round(p, 2), net_sum(pips)))
    return steps_under, onto_ramp


def live_at(tl, agent, t):
    """[(skill, rank)] of the agent's episodes live through the batch at `t`."""
    return [(e["skill"], e["field3"]) for e in tl["episodes"]
            if e["target"] == agent and e["t"] <= t + BATCH
            and (e["close_t"] is None or e["close_t"] > t + BATCH)]


# ---------------------------------------------------------------------------
# apply words (P1) and bounds (P4)

def rate_free_skills(tl_list):
    """Skills whose every apply AND close on the corpus carries no [44] word
    on its wearer in the batch: measured silent, so a live one adds 0. A skill
    with any word in any of its batches is not in the set (it may be a rate,
    or a coincident change); the four degenerating conditions never are."""
    seen, worded = set(), set()
    for tl in tl_list:
        for e in tl["episodes"]:
            seen.add(e["skill"])
            times = [e["t"]] + ([e["close_t"]] if e["close_t"] is not None else [])
            ws = [w[0] for w in tl["words"].get(e["target"], ())]
            if any(_near(ws, x) for x in times):
                worded.add(e["skill"])
    return (seen - worded - set(CONDITION_PIPS)) | set(RATE_FREE_CONDITIONS)


def apply_words(tl, silent=frozenset(), **arm):
    """P1 rows: every apply of a skill with a carried number whose wearer's
    live set is all carried-or-silent and whose batch carries a [44] word.
    Row: {"agent", "skill", "rank", "t", "word" (pips), "want", "before",
    "want_before", "natural_zero", "scored"}."""
    out = []
    for e in tl["episodes"]:
        if signed_pips(e["skill"], e["field3"], tl["build"]) is None:
            continue
        agent, t = e["target"], e["t"]
        ws = list(tl["words"].get(agent, ()))     # WIRE order: never re-sort a batch
        at = [w for w in ws if abs(w[0] - t) <= BATCH]
        if not at:
            continue
        word = pips_of(tl, agent, at[-1][0], at[-1][1])
        live = live_at(tl, agent, t)
        known = [signed_pips(s, r, tl["build"]) for s, r in live]
        unknown = [s for (s, _r), p in zip(live, known) if p is None and s not in silent]
        pips = [p for p in known if p is not None]
        want = net_sum(pips, **arm)
        # the word BEFORE the batch, and what the effects alone said then
        prev = [w for w in ws if w[0] < t - BATCH / 10]
        fulls = [f for f in tl["full"].get(agent, ()) if f < t - BATCH / 10]
        before = None
        if prev and not (fulls and fulls[-1] > prev[-1][0]):
            before = pips_of(tl, agent, prev[-1][0], prev[-1][1])
        elif fulls or not prev:
            before = 0.0                             # [32] zeroed the client's rate
        live_before = [(s, r) for s, r in live_at(tl, agent, t - 2 * BATCH)]
        kb = [signed_pips(s, r, tl["build"]) for s, r in live_before]
        want_before = net_sum([p for p in kb if p is not None], **arm)
        nz = before is not None and abs(before - want_before) <= UNIT_TOL
        out.append({"agent": agent, "kind": kind_of(tl, agent), "skill": e["skill"],
                    "rank": e["field3"], "t": t, "word": word, "want": want,
                    "before": before, "want_before": want_before,
                    "natural_zero": nz, "unknown": unknown,
                    "scored": word is not None and nz and not unknown})
    return out


def word_bounds(tl):
    """P4: [(agent, kind, pips)] for every word whose maximum is known."""
    out = []
    for agent, ws in tl["words"].items():
        for t, r in ws:
            p = pips_of(tl, agent, t, r)
            if p is not None:
                out.append((agent, kind_of(tl, agent), p))
    return out


def full_census(tl):
    """Every [32]: the sign of the agent's last word before it, and whether a
    regen effect closes in its batch. [(kind, last_sign, regen_close)]."""
    out = []
    for agent, ts in tl["full"].items():
        ws = list(tl["words"].get(agent, ()))     # WIRE order: never re-sort a batch
        for t in ts:
            prev = [w for w in ws if w[0] <= t + BATCH]
            sign = None if not prev else (1 if prev[-1][1] > 0 else (0 if prev[-1][1] == 0 else -1))
            closes = [e for e in tl["episodes"] if e["target"] == agent
                      and e["close_t"] is not None and abs(e["close_t"] - t) <= BATCH]
            regen = any((signed_pips(e["skill"], e["field3"], tl["build"]) or 0) > 0
                        for e in closes)
            out.append((kind_of(tl, agent), sign, regen))
    return out


def regen_closes(tl):
    """Every close of a carried REGENERATION episode: [(skill, has_32, has_44)]."""
    out = []
    for e in tl["episodes"]:
        if e["close_t"] is None or (signed_pips(e["skill"], e["field3"], tl["build"]) or 0) <= 0:
            continue
        a, tc = e["target"], e["close_t"]
        out.append((e["skill"], _near(tl["full"].get(a, ()), tc),
                    _near([w[0] for w in tl["words"].get(a, ())], tc)))
    return out


# ---------------------------------------------------------------------------
# the corpus

def census(codec=None, set_aside=None):
    """[(stamp, connection, timeline)] for every live connection that frames
    whole; a manifest-declared gap is set aside BY NAME into `set_aside`."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live", why="regenjoin reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in deepwoundjoin.whole_s2c(cap_dir, set_aside):
            seq, build = sequence(cap_dir, ch["connection"], codec)
            out.append((stamp, ch["connection"], timeline(seq, build)))
    return out


def score(rows, **arm):
    """The numbers every prediction is judged on, from `census` rows.
    `arm` passes a known-bad arithmetic to P1 (separate_caps / unsigned)
    and `delay` / `step` to P2 / P3 -- each must redden what it targets."""
    delay = arm.pop("delay", NATURAL_DELAY)
    step = arm.pop("step", NATURAL_STEP)
    tls = [tl for _s, _c, tl in rows]
    silent = rate_free_skills(tls)
    out = {"connections": len(rows)}
    # P1
    p1 = []
    for stamp, conn, tl in rows:
        for r in apply_words(tl, silent, **arm):
            r.update(capture=stamp, connection=conn)
            p1.append(r)
    scored = [r for r in p1 if r["scored"]]
    out["p1_scored"] = len(scored)
    out["p1_match"] = sum(1 for r in scored if abs(r["word"] - r["want"]) <= UNIT_TOL)
    out["p1_by_skill"] = {}
    for r in scored:
        row = out["p1_by_skill"].setdefault(r["skill"], [0, 0])
        row[0] += 1
        row[1] += abs(r["word"] - r["want"]) <= UNIT_TOL
    out["p1_misses"] = [(r["capture"], r["connection"][-24:], r["agent"], r["skill"], r["rank"],
                         round(r["t"], 3), round(r["word"], 2), r["want"])
                        for r in scored if abs(r["word"] - r["want"]) > UNIT_TOL]
    out["p1_clamp_witness"] = [(r["capture"], r["skill"], round(r["word"], 2), r["want"])
                               for r in scored if r["skill"] == 288 and r["want"] < 0]
    out["p1_natural_nonzero"] = [(r["capture"], r["agent"], r["skill"], r["before"],
                                  r["want_before"], round(r["word"], 2) if r["word"] is not None else None)
                                 for r in p1 if not r["natural_zero"] and r["word"] is not None]
    # P2 / P3 per kind
    for name, classes in (("registered", REGISTERED), ("anchors", ANCHOR_CLASSES),
                          ("activations", ACTIVATIONS)):
        fs = [f for _s, _c, tl in rows for f in first_steps(tl, classes, delay)]
        for kind in ("player", "hostile", "other"):
            ks = [f for f in fs if f["kind"] == kind]
            out[f"p2_{name}_{kind}"] = {
                "n": len(ks),
                "on_time": sum(1 for f in ks if abs(f["delay"] - delay) <= TOL),
                "early": sum(1 for f in ks if f["delay"] < delay - TOL),
                "late": sorted(round(f["delay"], 2) for f in ks if f["delay"] > delay + TOL),
                "early_list": sorted(round(f["delay"], 2) for f in ks if f["delay"] < delay - TOL),
            }
    by_class = collections.Counter(f["class"] for _s, _c, tl in rows
                                   for f in first_steps(tl, ANCHOR_CLASSES, delay)
                                   if f["kind"] in ("player", "hostile") and f["on_time"])
    out["p2_binding_class"] = dict(by_class)
    iv = [x for _s, _c, tl in rows for x in step_intervals(tl, step)]
    for kind in ("player", "hostile", "other"):
        ks = [x for x in iv if x[0] == kind]
        out[f"p3_{kind}"] = {"n": len(ks), "on_time": sum(1 for x in ks if x[2])}
    # the cap
    caps = [c for _s, _c, tl in rows for c in cap_witnesses(tl)]
    out["cap_tops"] = collections.Counter((k, top) for k, top, _g in caps)
    out["cap_max_top"] = max((top for k, top, _g in caps if k != "other"), default=None)
    tops = [run["levels"][-1][1] for _s, _c, tl in rows for a in tl["words"]
            for run in natural_runs(tl, a)]
    out["max_level"] = max(tops, default=None)
    # P4
    b = [x for _s, _c, tl in rows for x in word_bounds(tl)]
    out["p4_n"] = len(b)
    out["p4_beyond"] = sum(1 for _a, _k, p in b if abs(p) > NET_CAP + UNIT_TOL)
    # Another PLAYER's maximum reaches the observer only on the observer's next
    # landed hit (PVPMAX, F46.10), so its words divide by a STALE 42 -- every
    # word "beyond 10" is one of those, and none is the observer's or a foe's.
    out["p4_beyond_scored"] = sum(1 for _a, k, p in b
                                  if k != "other" and abs(p) > NET_CAP + UNIT_TOL)
    out["p4_scored"] = sum(1 for _a, k, _p in b if k != "other")
    out["p4_at_minus_10"] = sum(1 for _a, _k, p in b if abs(p + NET_CAP) <= UNIT_TOL)
    out["p4_at_plus_10"] = sum(1 for _a, _k, p in b if abs(p - NET_CAP) <= UNIT_TOL)
    # P5
    under = [under_degeneration(tl) for _s, _c, tl in rows]
    out["p5_steps_under_negative"] = sum(u[0] for u in under)
    onto = [x for u in under for x in u[1]]
    out["p5_onto_ramp"] = len(onto)
    out["p5_onto_ramp_effects_only"] = sum(1 for _a, _lv, p, want in onto if abs(p - want) <= UNIT_TOL)
    # property 32
    fc = [x for _s, _c, tl in rows for x in full_census(tl)]
    out["p32_n"] = len(fc)
    out["p32_after_positive"] = sum(1 for _k, s, _r in fc if s == 1)
    rc = [x for _s, _c, tl in rows for x in regen_closes(tl)]
    out["regen_closes"] = len(rc)
    out["regen_closes_32"] = sum(1 for _s, f, _w in rc if f)
    out["regen_closes_44"] = sum(1 for _s, _f, w in rc if w)
    out["regen_closes_neither"] = sum(1 for _s, f, w in rc if not f and not w)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    aside = []
    rows = census(set_aside=aside)
    sc = score(rows)
    if args.json:
        print(json.dumps(sc, indent=1, default=str))
        return 0
    print(f"connections {sc['connections']}; set aside {[(a['capture'], a['connection']) for a in aside]}")
    print(f"P1 apply words scored {sc['p1_scored']}, match {sc['p1_match']}; by skill "
          f"{sc['p1_by_skill']}; misses {sc['p1_misses']}")
    print(f"   288's clamp witness {sc['p1_clamp_witness']}")
    print(f"   natural NOT zero at the apply (reported, unscored): {sc['p1_natural_nonzero']}")
    for name in ("registered", "anchors", "activations"):
        for kind in ("player", "hostile", "other"):
            print(f"P2 [{name:11s}] {kind:7s} {sc[f'p2_{name}_{kind}']}")
    print(f"   the binding anchor class of each on-time first step: {sc['p2_binding_class']}")
    for kind in ("player", "hostile", "other"):
        print(f"P3 {kind:7s} {sc[f'p3_{kind}']}")
    print(f"CAP: runs that stop below the maximum, by (kind, top): {dict(sc['cap_tops'])}; "
          f"highest natural level anywhere {sc['max_level']}")
    print(f"P4 {sc['p4_n']} words with a known maximum ({sc['p4_scored']} the observer's or a "
          f"foe's: beyond 10 {sc['p4_beyond_scored']}); beyond 10 anywhere {sc['p4_beyond']}, "
          f"at -10 {sc['p4_at_minus_10']}, at +10 {sc['p4_at_plus_10']}")
    print(f"P5 +1 steps above a negative word {sc['p5_steps_under_negative']}; degeneration "
          f"applies onto a running ramp {sc['p5_onto_ramp']}, effects-only "
          f"{sc['p5_onto_ramp_effects_only']}")
    print(f"[32] {sc['p32_n']}, after a positive word {sc['p32_after_positive']}; regen closes "
          f"{sc['regen_closes']}: with [32] {sc['regen_closes_32']}, with [44] "
          f"{sc['regen_closes_44']}, neither {sc['regen_closes_neither']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
