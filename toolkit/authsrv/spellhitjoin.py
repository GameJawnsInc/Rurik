r"""Does a CAST's damage roll a hit location the way a SWING's does? Retail's wire.

    python toolkit/authsrv/spellhitjoin.py            # every live capture
    python toolkit/authsrv/spellhitjoin.py --json
    python toolkit/authsrv/spellhitjoin.py --pairs    # every (caster, skill, target)

WHY THIS EXISTS. `studies/skills/FINDINGS.md` 39.6 left the incoming-Flare
armour term unbuilt because GWW is ambiguous about WHICH armour a spell
scales against: every hit-location sentence it has says "attack" (chest 3/8,
legs 2/8, feet/hands/head 1/8), and the non-attack formula names no
location. It proposed a loopback probe with a lopsided armour set -- which
cannot answer the question, because on loopback OUR server computes the
number (two of our own components agreeing). The instrument is retail's
own casts: one caster, one skill, one target, many hits. A location roll on
a set whose pieces differ shows as a second value bucket; a single rating
shows as one value for as long as the target's armour holds.

THE JOIN. A cast's damage rides the same `0x00A3` property 16/17 a swing
does, in the batch its caster's property-58 (skill_finished) closes; the
SKILL is named by the cast announcement `0x00A0 [60 SKILL_ACTIVATED, caster,
target, skill]`, and the damage lands one activation later (Mind Burn's
1.0 s, Fireball's 1.5 s -- the `age` column reproduces the wiki's
activation times). A DAMAGE-OVER-TIME tick (Fire Storm, once a second, no
58 of its own) can share a batch with a cast from the same caster; a value
in a 58-batch that also occurs as a NO-58 hit from the same cause onto the
same target within 5 s is a tick and is set aside, not counted as the cast.

THE PREDICTIONS, stated before the numbers:

  P1  cast damage is ANNOUNCED: >= 95% of damage in a 58-batch has a
      property-60 from its cause inside 4 s.
  P2  one caster + one skill + one target is ONE VALUE: over every pair with
      >= 3 non-tick hits, the number of distinct fractions is 1 -- for at
      least 10 pairs and 60 hits. A 1-in-8 head roll on ANY armour
      difference leaves a single bucket with probability (7/8)^n; at n = 60
      that is 0.03%. What P2 cannot separate: a roll on a set whose pieces
      are all equal, which is what a PvP set usually is (43.5).
  P3  the CONTROL, so the instrument is known to see variance where it
      exists: swing damage from one cause onto one target with >= 10 hits
      has >= 3 distinct values (a weapon's range).
  P4  the wiki's own second packet: Mind Burn (185) "if you have more Energy
      than target foe, that foe ... take[s] an additional 15..60" -- read
      as TWO identical 16s onto one target in one batch, >= 10 times.

TWO ROWS THE JOIN MUST NOT COUNT AS THE ANNOUNCED SKILL'S (2026-09-29, CASTAI-Z2,
20260929T100038 -- the Smiting Monks):

  PAYOFF  a word riding ANOTHER skill's completion batch. The wire names the
      observer's own damage ahead of the word -- `[10, obs, S]` (GV_SKILL_DAMAGE,
      the prefix hexjoin reads on 179's payoff) -- and on the Zaishen-2 tape every
      word a monk landed on the observer in the completion batch of its Mend
      Condition 275 / Reversal of Fortune 307 / Smite Hex 302 / Balthazar's Aura 272 /
      Resurrection Signet 2 is named 271, Zealot's Fire (WIKI: an enchantment on the
      caster; "whenever you use a skill that targets an ally, all foes adjacent to
      that target are struck for 5..35 fire damage"). The join's `skill` is the
      cause's latest announce ahead of the word, i.e. the skill whose completion the
      payoff rides, so P2 keyed on it read one payoff under five skill ids. A row is
      a payoff when (a) the wire names it (`named` is not None and differs from
      `skill`), or (b) it is such a word's SIBLING (the same cause, the same batch --
      the foe beside the observer takes the same trigger and carries no [10] of its
      own), or (c) the announce named an ALLY of the caster (the same allegiance
      token on the 0x0020 creates; a targetless announce is the caster itself) and
      the word landed on a FOE -- a skill cast at an ally has no target damage of
      its own -- AND the wire has already backed both halves of that reading on the
      same connection: the (caster, skill) has an (a) row (its completion was named
      as another skill's at least once) and the (target, value) has an (a) or (b)
      row (that amount onto that body was named or sat beside a named word). (a) is
      the wire's word; (b) and (c) reach the bodies the wire never names, and (c)
      without its two witnesses is NOT set aside (`ally_cast_unbacked`, counted and
      reported): a self-targeted nuke's word, or a stray value beside a witnessed
      trigger, stays a value P2 can see. `classify_payoffs` is the rule, applied by
      `events` and again by `score` (an injected row is judged by its shape).
  CONVERTED  a `+0.0` word (bits 0x00000000) with a property-55 heal onto the same
      target in the same batch: Reversal of Fortune took the hit (healjoin P6, the
      RB tape: a fully converted hit's word is +0.0, never -0.0). It carries no
      amount; a `+0.0` WITHOUT the heal beside it is NOT set aside and would stand
      as a second value.

Both are set aside from the pairs the way a DoT tick is (`pairs`), counted in
`score` (`payoff_set_aside`, `converted_set_aside`), and `score(rows, classify=False)`
is the known-bad arm that counts them as the announced skill's again. At the pin
(every capture before 20260929T100038) both counts are 0 -- the old numbers are
unmoved by construction, and test_skilldamage 12 asserts them to the digit.

THE ANNOUNCE IS READ IN WIRE ORDER (2026-09-29, the review of this lane's first cut).
The first cut collected every announce of a batch BEFORE reading its words, so a
cast announced later in the batch claimed a word ahead of it (age 0.0), and it did
not read the targetless `0x009F [60, agent, skill]` form at all (Balthazar's Aura,
a self-cast Reversal of Fortune), so a 4 s-stale targeted announce claimed the
word instead: 50 of the tape's 212 payoff rows were keyed to a stale or later
announce, 18 of them to Drain Enchantment 68, whose own completions carry no word.
`ANNOUNCE_BY_ORDER` (default True) reads both forms as they come; False is that
first cut, the known-bad arm. Read in order, every payoff's `age` reproduces its
trigger's activation (275 at 0.73-0.76 s, 307 at 0.21-0.27, 272 at 0.99-1.05, 302
at 1.00-1.02, 2 at 3.00-3.02), and at the pin no cast row changes its skill.

Standard library only; reads the vault through `vaultpath`; refuses a tape
that does not frame whole (`deepwoundjoin.sequence`).
"""
import argparse
import bisect
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import adrenjoin        # noqa: E402
import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import healjoin         # noqa: E402
import livewire         # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_CREATE = 0x0020         # v[1] agent, v[12] allegiance token (hexjoin's read)
OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_FLOAT_TARGET = 0x00A3   # [prop, target, cause, f32]
OP_SKILL_ACTIVATED = 0x00E3
PROP_MELEE_FINISHED = 1
PROP_SKILL_DAMAGE = 10     # [10, obs, skill]: the wire's own name for the observer's damage
PROP_SKILL_FINISHED = 58
PROP_ATTACK_SKILL_ACTIVATED = 50
PROP_SKILL_ACTIVATED = 60
PROP_HEALTH_MAX = 42
PROP_HEALTH_GAIN = 55
PROP_DAMAGE = (16, 17)
ANNOUNCE_WINDOW = 4.0      # s; longer than any activation on the wire
TICK_WINDOW = 5.0          # s; a DoT's cadence is 1 s
MIND_BURN = 185
ANNOUNCE_BY_ORDER = True   # the announce read as it comes, both forms (docstring); False is
                           # the first cut of 2026-09-29 -- the known-bad arm


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def events(seq):
    """Every 16/17 in one sequence, classified.

    A row: {"t", "prop", "target", "cause", "value", "kind" (swing / cast /
    both / none -- what the cause finished in the batch), "skill" (the
    cause's latest property-60 skill ahead of the word, None if none inside
    ANNOUNCE_WINDOW), "age" (seconds since that announcement), "form" (which
    announce: "0x00A0" targeted, "0x009F" targetless), "maxhp" (the target's
    last property 42, None if never seen), "tick" (a 58-batch value that also
    occurs as a no-58 hit from the same cause onto the same target within
    TICK_WINDOW), "twin" (another identical 16 onto this target from this
    cause in the same batch), "named" (the skill the wire itself names for
    this word -- the nearest `[10, target, S]` ahead of it in the batch; the
    wire names only the observer's damage, so None elsewhere), "ann_target"
    (the announcement's target; the caster itself for the targetless form),
    "ally_cast" (that target shares the cause's allegiance token and this
    word's target does not), "converted" (a +0.0 word with a property-55 heal
    onto the same target in the batch), "batch" (its index in the sequence),
    and from `classify_payoffs`: "payoff", "why" ("named" / "sibling" /
    "ally-cast" / None) and "ally_cast_unbacked" (the docstring's (c) shape
    without its witnesses -- NOT set aside)}.
    """
    ann = {}
    maxhp = {}
    alleg = {}
    rows = []
    for nb, batch in enumerate(healjoin.batches(seq)):
        fin = collections.defaultdict(set)
        healed = set()                       # targets with a positive 55 in the batch
        for _i, t, op, v in batch:
            if op == OP_INT_TARGET and v[1] == PROP_SKILL_ACTIVATED and not ANNOUNCE_BY_ORDER:
                ann[v[2]] = (v[4], t, v[3], "0x00A0")      # the first cut: read ahead of the words
            elif op == OP_INT and v[1] == PROP_HEALTH_MAX:
                maxhp[v[2]] = v[3]
            elif op == OP_INT and v[1] in (PROP_MELEE_FINISHED,
                                           PROP_SKILL_FINISHED):
                fin[v[2]].add(v[1])
            elif op == OP_CREATE and len(v) > 12:
                alleg[int(v[1])] = int(v[12])
            elif op == OP_FLOAT_TARGET and len(v) > 4 and v[1] == PROP_HEALTH_GAIN \
                    and not (v[4] & 0x80000000) and (v[4] & 0x7FFFFFFF):
                healed.add(v[2])
        seen = collections.Counter()
        named_now = {}                       # target -> the latest [10, target, S] so far
        for _i, t, op, v in batch:
            if op == OP_INT and v[1] == PROP_SKILL_DAMAGE and len(v) > 3:
                named_now[v[2]] = v[3]
                continue
            if ANNOUNCE_BY_ORDER and len(v) > 3 and v[1] == PROP_SKILL_ACTIVATED:
                if op == OP_INT_TARGET and len(v) > 4:
                    ann[v[2]] = (v[4], t, v[3], "0x00A0")
                elif op == OP_INT:
                    ann[v[2]] = (v[3], t, v[2], "0x009F")   # targetless: the caster itself
                continue
            if op != OP_FLOAT_TARGET or v[1] not in PROP_DAMAGE:
                continue
            prop, target, cause, value = v[1], v[2], v[3], round(_f32(v[4]), 5)
            kinds = fin.get(cause, set())
            kind = {frozenset(): "none",
                    frozenset({PROP_MELEE_FINISHED}): "swing",
                    frozenset({PROP_SKILL_FINISHED}): "cast"}.get(
                        frozenset(kinds), "both")
            skill, age, ann_target, form = None, None, None, None
            a = ann.get(cause)
            if a is not None and 0.0 <= t - a[1] <= ANNOUNCE_WINDOW:
                skill, age, ann_target, form = a[0], round(t - a[1], 3), a[2], a[3]
            key = (target, cause, value)
            seen[key] += 1
            ally_cast = (ann_target is not None and cause in alleg and target in alleg
                         and ann_target in alleg and alleg[ann_target] == alleg[cause]
                         and alleg[target] != alleg[cause])
            rows.append({"t": round(t, 6), "prop": prop, "target": target,
                         "cause": cause, "value": value, "kind": kind,
                         "skill": skill, "age": age, "ann_target": ann_target, "form": form,
                         "maxhp": maxhp.get(target), "tick": False,
                         "twin": seen[key] > 1,
                         "named": named_now.get(target),
                         "ally_cast": ally_cast,
                         "converted": v[4] == 0 and target in healed,
                         "payoff": False, "why": None, "ally_cast_unbacked": False,
                         "batch": nb})
    # Ticks: a 58-batch value also seen as a no-58 hit nearby.
    bare = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "none":
            bare[(r["target"], r["cause"], r["value"])].append(r["t"])
    for r in rows:
        if r["kind"] == "cast":
            near = bare.get((r["target"], r["cause"], r["value"]), ())
            r["tick"] = any(abs(t - r["t"]) <= TICK_WINDOW for t in near)
    classify_payoffs(rows)
    return rows


def classify_payoffs(rows):
    """The docstring's PAYOFF rule, on rows grouped by (capture, connection) -- one
    connection's `events` rows carry neither key and are one group. Sets `payoff`,
    `why` and `ally_cast_unbacked` on every row from its shape (`named`, `skill`,
    `batch`, `ally_cast`, `tick`) and the evidence around it, and returns the rows.

    Decided AFTER the ticks: a word the wire names as another skill's is a payoff
    unless it is the caster's own periodic tick riding the batch (I2r: Fire Storm's
    tick in a Fireball batch is named 197, and stays a tick); its siblings (the same
    cause, the same batch) ride the same trigger; an ally-cast's word onto a foe is
    one only where the same connection has ALREADY named that (cause, skill)'s
    completion as another skill's -- an (a) row -- and named that (target, value) --
    an (a) or (b) row. `score` applies this again, so a row injected past `events`
    is judged by its shape, not by the flag it was handed."""
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r.get("capture"), r.get("connection"))].append(r)
    for g in groups.values():
        live = [r for r in g if r["skill"] is not None and not r["tick"]]
        renamed = {(r["batch"], r["cause"]) for r in live
                   if r["named"] is not None and r["named"] != r["skill"]}
        trigger_named, value_named = set(), set()
        for r in g:
            r["why"], r["payoff"], r["ally_cast_unbacked"] = None, False, False
        for r in live:
            if r["named"] is not None and r["named"] != r["skill"]:
                r["why"] = "named"
                trigger_named.add((r["cause"], r["skill"]))
            elif (r["batch"], r["cause"]) in renamed:
                r["why"] = "sibling"
            if r["why"] is not None:
                value_named.add((r["target"], r["value"]))
        for r in live:
            if r["why"] is None and r["ally_cast"]:
                backed = ((r["cause"], r["skill"]) in trigger_named
                          and (r["target"], r["value"]) in value_named)
                if backed:
                    r["why"] = "ally-cast"
                r["ally_cast_unbacked"] = not backed
            r["payoff"] = r["why"] is not None
    return rows


def named_words(seq):
    """The wire's own attribution of the OBSERVER'S damage and health loss: for every
    property-16 / 17 word and every NEGATIVE property-55 word that follows a
    `[10, target, S]` in its batch, the pair (S, prop) -> count. On 20260929T100038
    Zealot's Fire's fire damage (271) rides 16 and the holy words -- Smite Hex 302,
    Balthazar's Aura 272, Scourge Healing 251 -- ride 55 with a negative fraction;
    the corpus before it carried 20260916T213125's skill 143 on 55 the same way."""
    out = collections.Counter()
    for batch in healjoin.batches(seq):
        named_now = {}
        for _i, _t, op, v in batch:
            if op == OP_INT and v[1] == PROP_SKILL_DAMAGE and len(v) > 3:
                named_now[v[2]] = v[3]
            elif op == OP_FLOAT_TARGET and len(v) > 4 and v[2] in named_now and (
                    v[1] in PROP_DAMAGE
                    or (v[1] == PROP_HEALTH_GAIN and (v[4] & 0x80000000) and (v[4] & 0x7FFFFFFF))):
                out[(named_now[v[2]], v[1])] += 1
    return out


# WHOSE CONNECTION IT IS (2026-09-23). This used to be "the agent of the FIRST
# 0x00E3", and on the one tape with a hero (20260914T005758, conn 56011) that
# ack is the HERO's: agent 30 (a kind-9 create) holds 48 of the 54 -- 346, 322,
# 382, 348, 385, one 2 -- and the player, agent 29 (the kind-5 create, whose acks
# answer all 18 c2s presses: 392, 394, 433, 446, 455), holds 6. On 69 more connections the
# player never cast, so there was no 0x00E3 and the old rule named NOBODY while
# property 41 named the observer. Every consumer's "own" split was scored on that
# (studies/skills 43.8). The observer is now `adrenjoin.whose_agent` -- property
# 41, self-scoped, with the JARIN kind-5 tie-break -- cross-checked against the
# agent whose 0x00E3 / 0x00E2 answers the connection's own c2s presses; the two
# disagreeing is REFUSED (no player named), never settled by picking one.
# `shoutjoin.observer_of` (branch desk-d5c) is the same rule on a merged stream.
OP_SKILL_RELEASED = 0x00E2
OP_CMSG_PRESS = (0x0027, 0x0046)   # c2s: attack-skill and cast presses
PRESS_ANSWER_S = 0.3       # s; the observer's E3 / E2 answering its own press


def c2s_of(cap_dir, conn_file):
    """[(t, opcode)] of the client's own requests, on the capture clock, or []."""
    _conn, events, err = livewire.build_events(cap_dir, conn_file, "c2s")
    if err is not None or not events:
        return []
    msgs, _receipt = tape.decode_all(events, livewire._get_codec(),
                                     channel="GAME_CMSG", mask=livewire.CMSG_MASK,
                                     strict=False)
    return [(t, op) for t, op, _v in msgs]


def observer_of(seq, c2s=()):
    """(player, press_agent, why): the connection's own agent by two rules.

    Property 41 (`adrenjoin.whose_agent`, NO fallback) and the landslide vote of
    the agent whose `0x00E3` / `0x00E2` is the next answer inside PRESS_ANSWER_S
    after each c2s press in `c2s` ([(t, opcode)] on `seq`'s clock, `c2s_of`).
    Both, when both answer, must agree; `why` is None when a player is named and
    says which case it is when not ("no observer: ..." -- neither rule answers;
    "observer rules disagree: ..." -- the REFUSAL). A press answered later than
    the window casts no vote (a walk into range first); it does not refute.
    """
    s2c = [(t, op, v) for _i, t, op, v in seq]
    by_41 = adrenjoin.whose_agent(s2c)
    answers = [(t, int(v[1])) for t, op, v in s2c
               if op in (OP_SKILL_ACTIVATED, OP_SKILL_RELEASED) and len(v) > 1]
    times = [t for t, _a in answers]
    votes = collections.Counter()
    for t, op in c2s:
        if op not in OP_CMSG_PRESS:
            continue
        i = bisect.bisect_left(times, t)
        if i < len(answers) and answers[i][0] - t <= PRESS_ANSWER_S:
            votes[answers[i][1]] += 1
    by_press = votes.most_common(1)[0][0] if votes else None
    if by_41 is None and by_press is None:
        return None, None, "no observer: no property 41 and no answered press"
    if by_41 is not None and by_press is not None and by_41 != by_press:
        return None, by_press, (f"observer rules disagree: property 41 says {by_41}, "
                                f"the answered presses say {by_press} ({dict(votes)})")
    return (by_41 if by_41 is not None else by_press), by_press, None


def player_of(seq, c2s=()):
    """The connection's own agent, or None when `observer_of` names nobody."""
    return observer_of(seq, c2s)[0]


def census(codec=None, unnamed=None, set_aside=None, refused=None, named=None,
           stamps=None):
    """Every live capture (or, with `stamps`, those in that set), every game
    connection that frames whole. A
    connection whose player `observer_of` cannot name keeps its rows (player
    None) and, when `unnamed` is a list, is appended to it as (capture,
    connection, why). When `named` is a list, each connection's `named_words`
    census is appended to it as (capture, connection, {(skill, prop): n}).

    A connection the capture's OWN manifest declares gapped
    (`livewire.declared_gaps`, 2026-09-28) is set aside BY NAME, printed, and
    decoded once to show it still refuses -- appended to `set_aside` (a list)
    as (capture, connection, why); one declared but decoding whole goes there
    as (capture, connection, None). Any OTHER connection that does not frame
    whole is appended to `refused` -- it used to be dropped without a word."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="spellhitjoin reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir) or (stamps is not None and stamp not in stamps):
            continue
        declared = livewire.declared_gaps(cap_dir)
        for ch in tape.channel_files(cap_dir):
            if ch["connection"] in declared:
                why = None
                try:
                    deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
                except (bufflog.BuffLogError, tape.TapeError) as exc:
                    why = str(exc)[:100]
                    print(f"   SET ASIDE {stamp} {ch['connection']}: its manifest declares "
                          f"it gapped {declared[ch['connection']]} -- still refused")
                if set_aside is not None:
                    set_aside.append((stamp, ch["connection"], why))
                continue
            try:
                seq = deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError) as exc:
                if refused is not None:
                    refused.append((stamp, ch["connection"], str(exc)[:100]))
                continue
            player, _press, why = observer_of(seq, c2s_of(cap_dir, ch["file"]))
            if player is None and unnamed is not None:
                unnamed.append((stamp, ch["connection"], why))
            if named is not None:
                named.append((stamp, ch["connection"], dict(named_words(seq))))
            for row in events(seq):
                row.update(capture=stamp, connection=ch["connection"],
                           player=player)
                out.append(row)
    return out


def counted(r, classify=True):
    """Is this row the announced skill's own hit -- not a tick, and (with
    `classify`, the default, on a CAST row) not a payoff riding the batch nor a
    converted +0.0? A swing row is never set aside here: P3 is the control that
    sees a weapon's range, and a converted swing under Reversal of Fortune (the RB
    tape's) is one more value there, never one fewer. `classify=False` is the
    known-bad arm: the reader before 2026-09-29."""
    if r["tick"]:
        return False
    if r["kind"] != "cast" or not classify:
        return True
    return not (r["payoff"] or r["converted"])


def pairs(rows, kind="cast", min_hits=3, classify=True):
    """{(capture, connection, cause, skill, target): [values]} for one kind,
    ticks (and, with `classify`, payoffs and converted words) set aside, pairs
    under `min_hits` dropped."""
    g = collections.defaultdict(list)
    for r in rows:
        if r["kind"] != kind or not counted(r, classify):
            continue
        g[(r["capture"], r["connection"], r["cause"], r["skill"],
           r["target"])].append(r["value"])
    return {k: v for k, v in g.items() if len(v) >= min_hits}


def payoff_census(rows):
    """What the payoff rule set aside, by shape: {"rows": n, "by_announced": {skill: n}
    (the JOIN'S attribution -- the cause's latest announce ahead of the word in wire
    order, whose completion the payoff rides), "named": {S: n} (the wire's own name,
    observer words), "why": {"named" / "sibling" / "ally-cast": n}, "targets": {agent:
    n}, "unbacked": n (the (c) shape without its witnesses -- NOT set aside; counted
    here so a tape where the rule could not reach a body is read, not absorbed)}.
    Cast-kind rows only."""
    cast = [r for r in rows if r["kind"] == "cast" and not r["tick"]]
    pay = [r for r in cast if r["payoff"]]
    return {
        "rows": len(pay),
        "by_announced": dict(collections.Counter(r["skill"] for r in pay)),
        "named": dict(collections.Counter(r["named"] for r in pay if r["named"] is not None)),
        "why": dict(collections.Counter(r["why"] for r in pay)),
        "targets": dict(collections.Counter(r["target"] for r in pay)),
        "unbacked": sum(1 for r in cast if r["ally_cast_unbacked"]),
    }


AGE_BAND = 0.25            # s; a projectile's flight is steady per (caster, skill)
INTEGER_EPS = 0.06         # points; the word is whole points of SOME maximum


def location_buckets(rows, min_hits=5):
    """PROJECTILE spell hits (no 58 in the batch -- the cast closed before the
    orb landed), per (capture, connection, cause, skill, target), as a Counter
    of WHOLE POINTS. SKILLS-LR (RUN-SKILLS-RB2, 2026-09-17): this is where a
    location roll shows, as two buckets 2^(dAR/40) apart.

    Two filters, both measured on the RB2 tape. AGE: the caster's wand hits
    share the announcement window, and a projectile's flight time is steady
    (Lightning Orb 2.38-2.50 s, Javelin 1.57-1.77 s), so rows more than
    AGE_BAND off the group's median age are another source. MAXIMUM: a killing
    blow's batch carries the death penalty's new prop 42 AHEAD of the damage
    word, so `maxhp` is one death stale there; the word is whole points of
    SOME maximum this target held (F46), and the first that makes it whole
    is taken, the current one tried first."""
    g = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "none" and r["skill"] is not None \
                and r["age"] is not None and r["maxhp"] is not None:
            g[(r["capture"], r["connection"], r["cause"], r["skill"],
               r["target"])].append(r)
    held = collections.defaultdict(set)      # every maximum a target held
    for r in rows:
        if r["maxhp"] is not None:
            held[(r["capture"], r["connection"], r["target"])].add(r["maxhp"])
    out = {}
    for k, rs in g.items():
        ages = sorted(r["age"] for r in rs)
        med = ages[len(ages) // 2]
        maxima = sorted(held[(k[0], k[1], k[4])], reverse=True)
        pts = collections.Counter()
        for r in rs:
            if abs(r["age"] - med) > AGE_BAND:
                continue
            for m in [r["maxhp"]] + [x for x in maxima if x != r["maxhp"]]:
                p = -r["value"] * m
                if abs(p - round(p)) <= INTEGER_EPS:
                    pts[int(round(p))] += 1
                    break
        if sum(pts.values()) >= min_hits:
            out[k] = dict(sorted(pts.items()))
    return out


def score(rows, classify=True):
    """The numbers P1-P4 are judged on. `classify=False` is the known-bad arm:
    payoffs and converted words counted as the announced skill's (pre-2026-09-29).
    With `classify` the payoff rule is applied afresh on copies of the rows
    (`classify_payoffs`): a row handed in past `events` -- a synthetic capture, an
    injected value -- is judged by its shape and the witnesses around it."""
    if classify:
        rows = classify_payoffs([dict(r) for r in rows])
    cast = [r for r in rows if r["kind"] == "cast"]
    announced = [r for r in cast if r["skill"] is not None]
    cp = pairs(rows, "cast", 3, classify)
    named = {k: v for k, v in cp.items() if k[3] is not None}
    multi = {k: sorted(set(v)) for k, v in named.items() if len(set(v)) > 1}
    # A multi-valued pair whose fraction moved WITH its target's maximum --
    # one value per maximum, several across them -- is a DEATH-PENALTY SPLIT,
    # not a second bucket: the word is points / max and a penalty moves the
    # max (studies/slice F46). Named by signature (SLICE-F47 2026-09-16)
    # so the next hero tape does not redden P2 on confirming evidence. A pair
    # with a hit whose maximum was never seen does not qualify.
    by_max = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if r["kind"] == "cast" and counted(r, classify) and r["skill"] is not None:
            by_max[(r["capture"], r["connection"], r["cause"], r["skill"],
                    r["target"])][r["maxhp"]].add(r["value"])
    penalty_split = {k: {m: sorted(vs) for m, vs in by_max[k].items()}
                     for k in multi
                     if len(by_max[k]) > 1 and None not in by_max[k]
                     and all(len(vs) == 1 for vs in by_max[k].values())}
    # Two hits, two values: below P2's floor, and named rather than dropped.
    # The corpus's one such pair is a MIXED batch -- Fireball's projectile
    # and Incendiary Bonds' hex-end payoff from the same caster landing on
    # one target 43 ms apart (studies/skills 43.5) -- not a second bucket.
    two = {k: sorted(set(v)) for k, v in pairs(rows, "cast", 2, classify).items()
           if len(v) == 2 and len(set(v)) == 2 and k[3] is not None}
    sp = pairs(rows, "swing", 10, classify)
    swing_distinct = {k: len(set(v)) for k, v in sp.items()}
    twins = [r for r in cast if r["twin"] and r["skill"] == MIND_BURN
             and not r["tick"]]
    onto_player = {k: v for k, v in named.items()
                   if any(r["target"] == r["player"] and r["capture"] == k[0]
                          and r["connection"] == k[1] and r["cause"] == k[2]
                          for r in rows if r["kind"] == "cast")
                   and k[4] == next((r["player"] for r in rows
                                     if r["capture"] == k[0]
                                     and r["connection"] == k[1]), None)}
    return {
        "n_cast": len(cast),
        "announced": len(announced),
        "ticks_set_aside": sum(1 for r in cast if r["tick"]),
        # the 2026-09-29 classes (counted whether or not `classify` set them aside)
        "payoff_set_aside": sum(1 for r in cast if r["payoff"] and not r["tick"]),
        "converted_set_aside": sum(1 for r in cast if r["converted"] and not r["tick"]
                                   and not r["payoff"]),
        "classify": classify,
        "pairs": len(named),
        "pair_hits": sum(len(v) for v in named.values()),
        "multi_valued": {" ".join(map(str, k[2:])): v for k, v in multi.items()},
        "penalty_split": {" ".join(map(str, k[2:])): v
                          for k, v in penalty_split.items()},
        "two_hit_two_valued": {" ".join(map(str, k[2:])): v
                               for k, v in two.items()},
        "skills": sorted({k[3] for k in named}),
        "swing_pairs": len(sp),
        "swing_pairs_3plus": sum(1 for n in swing_distinct.values() if n >= 3),
        "swing_min_distinct": min(swing_distinct.values()) if sp else None,
        "mind_burn_twins": len(twins),
        "onto_player": {" ".join(map(str, k[2:])): (len(v), sorted(set(v)))
                        for k, v in onto_player.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pairs", action="store_true",
                    help="print every (caster, skill, target) pair's values")
    args = ap.parse_args()
    unnamed = []
    rows = census(unnamed=unnamed)
    sc = score(rows)
    if args.json:
        print(json.dumps({"score": sc, "rows": rows, "unnamed": unnamed}, indent=1))
        return
    refused = [u for u in unnamed if u[2].startswith("observer rules disagree")]
    print(f"connections whose player is named by nobody: {len(unnamed) - len(refused)}; "
          f"REFUSED (property 41 and the answered presses disagree): {len(refused)}")
    for stamp, conn, why in refused:
        print(f"   {stamp} {conn}: {why}")
    print(f"cast damage events {sc['n_cast']}: announced by a property-60 "
          f"inside {ANNOUNCE_WINDOW:.0f} s {sc['announced']} (P1); DoT ticks "
          f"set aside {sc['ticks_set_aside']}")
    print(f"   set aside as another skill's PAYOFF riding the batch {sc['payoff_set_aside']} "
          f"{payoff_census(rows)}; as a CONVERTED +0.0 (Reversal of Fortune) "
          f"{sc['converted_set_aside']}")
    print(f"P2 (caster, skill, target) pairs with >= 3 hits: {sc['pairs']} "
          f"over {sc['pair_hits']} hits, skills {sc['skills']}; "
          f"multi-valued pairs: {len(sc['multi_valued'])} "
          f"{sc['multi_valued'] or ''}; two-hit two-valued pairs (below the "
          f"floor, named): {sc['two_hit_two_valued']}")
    print(f"   of the multi-valued, split by a death penalty (one value per "
          f"maximum): {sc['penalty_split'] or 'none'}")
    print(f"   onto the connection's own player: {sc['onto_player']}")
    print(f"P3 control: swing pairs with >= 10 hits {sc['swing_pairs']}, of "
          f"which >= 3 distinct values {sc['swing_pairs_3plus']} (min "
          f"distinct {sc['swing_min_distinct']})")
    print(f"P4 Mind Burn's second packet as a twin 16 in one batch: "
          f"{sc['mind_burn_twins']}")
    if args.pairs:
        for k, v in sorted(pairs(rows, "cast", 2).items(),
                           key=lambda kv: (kv[0][0], kv[0][1], kv[0][2],
                                           str(kv[0][3]), kv[0][4])):
            c = collections.Counter(v)
            print(f"   {k[0]} {k[1][11:16]} cause {k[2]:3d} skill "
                  f"{str(k[3]):>4s} -> {k[4]:3d} n={len(v):3d} :: "
                  + " ".join(f"{val:.4f}x{n}" for val, n in sorted(c.items())))


if __name__ == "__main__":
    main()
