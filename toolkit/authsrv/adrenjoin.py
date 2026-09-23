r"""The adrenaline census, stratified by whether the player's bar can hold any.

    python toolkit/authsrv/adrenjoin.py              # the split, and the join
    python toolkit/authsrv/adrenjoin.py --rows       # every damage row, sorted
    python toolkit/authsrv/adrenjoin.py --json       # for another tool

WHAT IT IS FOR, AND THE TRAP IT EXISTS TO STOP. `pools.damage_units` grants one
adrenaline unit per 1% of maximum health lost, rounded to nearest, and the
rounding was measured on 2026-08-21 by joining GAIN -> DAMAGE: 32 sub-25
`0x00CF`s, 31 joinable, round fits 31 of 31. That population is SELECTED ON THE
OUTCOME -- every row in it is a damage event that DID produce a gain -- so it
cannot contain the band where the rule stops granting, and the docstring said
so: "which side of it retail lands on is UNVERIFIED".

The obvious repair is to run the join the other way, DAMAGE -> GAIN, over every
`0x00A3` naming the observer as target. Run naively that produces a confident
and completely wrong answer: 32 damage events granting nothing, the largest of
them **7.5% of maximum health**, which read at face value would put retail's
cutoff an order of magnitude above the wiki's and refute round() outright.

It is an artifact of a variable nobody had stratified on. Every one of those 32
rows is in a connection whose player carries NO ADRENALINE SKILL ON THE BAR, and
in those connections retail's server sends no `0x00CF` AT ALL -- not for damage
taken, and not for the 45 weapon hits and 13 completed melee attacks those same
connections contain. Split on the bar and the corpus is two clean populations
(see `studies/skills/FINDINGS.md` 34):

    ARMED bars  36 connections   918 gains,  27 clears, 40 spends
    DARK  bars  22 connections     0 gains,   0 clears,  0 spends

That accounts for the whole family census exactly, which is this scanner's own
consistency check -- `test_adrenwire`'s CENSUS is 918/27/0/40 and the ARMED
column reproduces it from a completely different query.

WHAT IT DOES NOT SETTLE, and this is the point of running it: the gate's
variable is CONFOUNDED. Every DARK connection is also a non-Warrior character,
so "the bar carries an adrenal skill" and "the profession uses adrenaline" fit
the same 58 connections and this corpus cannot separate them. Both are recorded
as candidates; neither is implemented in the sender.

READ-ONLY. It opens `vault/captures/live/` and writes nothing anywhere.
Standard library only, like everything else on this path.
"""
import argparse
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

import content      # noqa: E402
import tape         # noqa: E402
import vaultpath    # noqa: E402
from codec import Codec  # noqa: E402

PROP_INT = 0x009F           # [prop, agent, value]
PROP_FLOAT_SELF = 0x00A2    # [prop, agent, f32]           -- no source field
PROP_FLOAT_TARGET = 0x00A3  # [prop, target, source, f32]
SKILLBAR_UPDATE = 0x00DA    # [agent, skills[8], ...]
ADRENALINE_GAIN = 0x00CF
ADRENALINE_CLEAR = 0x00D0
ADRENALINE_SPEND = 0x00D2

# FIELD INDEXING, AND IT DIFFERS FROM moralescan.py ON PURPOSE. `decode_all`
# returns values with THE OPCODE AT INDEX 0, so this module reads a 0x009F as
# v[0]=159, v[1]=property, v[2]=agent, v[3]=value. `moralescan.py` slices it
# off first (`v = vals[1:]`) and therefore reads the property at v[0]. BOTH ARE
# CORRECT; they are not the same convention.
#
# Written down because on 2026-08-22 the two files were compared side by side,
# the disagreement read as an off-by-one in one of them, and a false correction
# against moralescan was one step away from being filed. If you are here to
# reconcile them: check for the slice before concluding anything.
PROP_MAX_ENERGY = 41        # SELF-SCOPED -- see whose_agent below
PROP_MAX_HEALTH = 42        # re-sent on change -- see whose_max_health below
PROP_MELEE_FINISHED = 1
DAMAGE_PROPS = (16, 17)     # both carry a negative fraction of max health
# PROPERTY 55 CHARGES TOO (studies/skills 53.5, read in 2026-09-19): RB's
# three life steals at the observer -- `[55, me, source, -0.0854167]`, 41 of
# 480 -- each carry `0x00CF [me, 9]` = round(8.54) in their batch, ahead of
# both 55 words. But 55 is SIGNED where 16/17 are not: the same batch holds a
# `[55, source, source, +0.0854167]` (the steal's heal), and a positive 55 to
# the OBSERVER is a heal to self. So a 55 word is a damage row only when it
# names the observer as target AND its value is negative; `abs()` downstream
# is then safe because the sign has already been read.
LIFE_DRAIN_PROP = 55
STRIKE_UNITS = 25

# --by-connection (DESKWORK-D5 step 1, 2026-09-22): the messages that say WHO a
# dark connection's character is, read off the same GAME stream as the bar --
# so that "every dark connection is a non-Warrior" (34.5) is a measurement
# rather than a reading of the bar's profession byte.
AGENT_PROFESSIONS = 0x00B7     # [agent, primary, secondary, flag]  (authsrv 3051)
PROP_LEVEL = 36                # int property 36 on 0x009F: the per-AGENT level
                               # that drives the nameplate (authsrv.py's 0x003A
                               # block says which channel is which; 0x003A is
                               # the attribute RANKS and was this scanner's
                               # first, wrong, read -- 9 dwords, no level in it)
PLAYER_INFO = 0x0059           # [player, agent, appearance, ...]; the profession
                               # nibble at bits 20-23 (charsummary.py)
SKILLBAR_UPDATE_SKILL = 0x00D9  # [agent, slot, skill, copy]  -- an in-game edit
ACCOUNT_LIBRARY = 0x001D       # array32[128]; the ACCOUNT's unlocks (skills 47).
                               # ONCE PER SESSION, not per map connection: 1 of
                               # 6 connections on 20260818T132739 carries it, so
                               # it is collected per CAPTURE below and labelled so
CHARACTER_LIBRARY = 0x00DB     # array32[128]; the CHARACTER's learned set --
                               # this one rides every map connection
AGENT_UPDATE_FLAGS = 0x0026    # [agent, flags]; 4 is the player's death
PLAYER_DEAD_FLAG = 4
PROFESSION_SHIFT = 20


def is_damage_to(op, v, me):
    """A damage word whose TARGET is `me`: 16/17 at me, or a NEGATIVE 55 at me."""
    if op not in DAMAGE_OPS or int(v[2]) != me:
        return False
    prop = int(v[1])
    if prop in DAMAGE_PROPS:
        return True
    if prop == LIFE_DRAIN_PROP:
        return f32(v[4] if op == PROP_FLOAT_TARGET else v[3]) < 0.0
    return False

# DAMAGE ARRIVES ON BOTH FLOAT CHANNELS, and the sourceless one is easy to miss
# because it is rare: 0x00A3 carries 63 damage events at the observer and 0x00A2
# carries ONE. That one is a 6.25% hit granting 6 units, and a scan that reads
# only 0x00A3 reports it as a gain with no damage anywhere near it. The first
# pass of this scanner did exactly that, printed the orphan, and moved on; a
# blind replication run the same hour chased it instead and found the channel.
# Hence: an unexplained row is a lead, and the ledger closing at 918 of 918 is
# what says none is left.
DAMAGE_OPS = (PROP_FLOAT_SELF, PROP_FLOAT_TARGET)


def f32(dw):
    """Four bytes read as a float, because reading them as an int never errors.

    Same trap `moralescan.s32` documents from the signed side: property 16's
    payload is IEEE-754 and 3,172,012,305 is a perfectly plausible-looking
    integer for -0.0354.
    """
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


# PRINT NINE DECIMALS, AND THAT IS NOT FUSSINESS. The single most interesting
# damage event in the corpus is 0xBC23D70A = -0.009999999776482582, which four
# decimals render as "1.0000%" -- and 1.0% is exactly where the two surviving
# rules AGREE. Read from the bytes it is 0.999999978%, just below, where they
# do NOT. Three independent readers (this scanner and two replication agents)
# printed it rounded and all three read past it. studies/skills 34.D.
PCT_FMT = "%12.9f"


def whose_max_health(msgs, me, before):
    """The observer's maximum health IN FORCE at stream index `before`.

    NOT the last one in the connection, and not any one of them. Property 42 is
    re-sent when it changes -- a death penalty moves it, and so does a gear
    change -- so a connection can carry 120 for its whole fight and 102 three
    thousand messages later. Two replication agents both took a set of the
    values and both assigned the WRONG maximum to two connections; the skeptic
    pass caught it from the bytes. Immaterial to the rule as it happens (those
    rows are excluded anyway, and all four ARMED connections carry only 480),
    material as a method: a denominator read non-temporally is a denominator
    that can be silently wrong.

    The leading 1 is skipped: property 42 arrives as the PAIR (1, real_max) for
    every own agent in the corpus, which `pools.py`'s header records as
    unexplained and which nothing here depends on.
    """
    seen = [int(v[3]) for i, (_t, op, v) in enumerate(msgs)
            if op == PROP_INT and len(v) > 3 and int(v[1]) == PROP_MAX_HEALTH
            and int(v[2]) == me and i < before and int(v[3]) > 1]
    return seen[-1] if seen else None


# THE `> 1` IN THAT COMPREHENSION IS LOAD-BEARING, and it is the same trap on
# property 41. Both maxima arrive as the PAIR (1, real_max) for every own agent
# in the corpus. A scan that takes the FIRST match reads 1 every time: on
# 2026-08-22 exactly that produced an observer max-energy census of "1" across
# all 58 connections, which is uniform enough to be an obvious tell and was
# nearly reported anyway. Skip the 1s, or take the last.


def whose_agent(msgs):
    """The observing player's agent id, or None. NO FALLBACK.

    Property 41 on the int channel is self-scoped. This is `moralescan.py`'s
    corrected rule and it is corrected for a measured reason: identifying the
    observer by the first `0x0059` was WRONG ON 20 OF 44 CONNECTIONS
    (studies/skills 26.13), because the server broadcasts one of those per
    player in the instance.

    AND DO NOT BE TEMPTED TO USE "the agent named by a 0x00CF" HERE. It is
    right on every connection that has one, and it would silently delete the
    entire DARK population from the denominator -- the connections with no
    gains are exactly the ones this scanner exists to count. That is the
    outcome-selection defect one level down, and it would have hidden the
    finding rather than producing a wrong number, which is worse.
    """
    seen = {int(v[2]) for _t, op, v in msgs
            if op == PROP_INT and len(v) > 2 and int(v[1]) == PROP_MAX_ENERGY}
    if len(seen) == 1:
        return seen.pop()
    # JARIN (2026-09-14): a HERO gets property 41 too -- the player's own
    # character block addressed to a second agent, 3 of 3 instances on
    # 20260914T005758 -- so the rule above answers None on a hero tape. The
    # tie-break is the kind-5 create: the observer's 0x0020 carries 5 in its
    # fourth word where a party body's carries 9 (other PLAYERS in a town are
    # kind 5 too, but they never receive property 41 on our stream).
    fives = {int(v[1]) for _t, op, v in msgs
             if op == 0x0020 and len(v) > 4 and int(v[4]) == 5}
    both = seen & fives
    return both.pop() if len(both) == 1 else None


def adrenal_costs():
    """skill id -> raw adrenaline cost, from our own extracted table."""
    return {int(k): int(r.get("adrenaline_units") or 0)
            for k, r in content.load().rows("skills").items()}


def bars():
    """Every connection's OWN skill bar: (capture, connection, agent, bar).

    This is a DIRECT READ of the 0x00DA addressed to the observing player --
    the observer resolved by `whose_agent`'s property-41 rule, the bar being
    the one message retail sends about our own slots. It exists because the
    other route was tried and refuted: `studies/skills/FINDINGS.md` 36.9
    aborted a live run whose plan inferred "on the operator's bar" from a
    skill's effect episodes in a town capture, where anyone nearby could have
    cast it. An effect row is ambient; a 0x00DA naming our own agent is not.
    36.10 is this query's first result. The bar can still change between
    sessions, so a plan built on this read must have the operator confirm the
    tooltip at run time -- this answers "what WAS the bar", never "what is".
    """
    live = vaultpath.require_dir("captures", "live", why="the bar readback")
    codec = Codec()
    out = []
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        for chan in tape.channel_files(cap):
            conn = chan["connection"]
            try:
                _info, events = tape.load_tape(cap, conn)
                msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                                  # noqa: BLE001
                continue
            me = whose_agent(msgs)
            if me is None:
                continue
            for _t, op, v in msgs:
                if op == SKILLBAR_UPDATE and len(v) > 2 and int(v[1]) == me:
                    out.append({"capture": stamp, "connection": conn,
                                "agent": me,
                                "bar": [int(x) for x in v[2]]})
    return out


def scan(costs=None):
    """Walk the live corpus once. Returns (stats, rows, skipped)."""
    costs = adrenal_costs() if costs is None else costs
    live = vaultpath.require_dir("captures", "live",
                                 why="the adrenaline census")
    codec = Codec()
    stats = {"armed": collections.Counter(), "dark": collections.Counter(),
             # JARIN (2026-09-14): a THIRD population -- a HERO's family, on
             # its own agent, keyed by the hero's own 0x00DA (adrenal skills on
             # it). 107 / 9 / 19 on 20260914T005758; a henchman's never.
             "hero": collections.Counter()}
    rows, skipped, captures = [], [], 0

    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        captures += 1
        for chan in tape.channel_files(cap):
            conn = chan["connection"]
            try:
                _info, events = tape.load_tape(cap, conn)
                msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                                  # noqa: BLE001
                continue
            me = whose_agent(msgs)
            if me is None:
                skipped.append({"capture": stamp, "connection": conn})
                continue

            bars = [tuple(int(x) for x in v[2]) for _t, op, v in msgs
                    if op == SKILLBAR_UPDATE and len(v) > 2 and int(v[1]) == me]
            on_bar = {s for bar in bars for s in bar if s}
            adrenal = sorted(s for s in on_bar if costs.get(s, 0) > 0)
            arm = "armed" if adrenal else "dark"
            s = stats[arm]
            s["connections"] += 1
            s["messages"] += len(msgs)
            # JARIN: every OTHER agent this connection sent a bar to, and
            # whether that bar is adrenal -- a hero's family is scoped to the
            # hero, not to the observer.
            other_bars = {}
            for _t, op, v in msgs:
                if op == SKILLBAR_UPDATE and len(v) > 2 and int(v[1]) != me:
                    other_bars.setdefault(int(v[1]), set()).update(
                        int(x) for x in v[2] if x)
            hero_agents = {a for a, bar in other_bars.items()
                           if any(costs.get(sk, 0) > 0 for sk in bar)}
            if hero_agents:
                stats["hero"]["connections"] += 1

            for _t, op, v in msgs:
                if (op in (ADRENALINE_GAIN, ADRENALINE_CLEAR, ADRENALINE_SPEND)
                        and int(v[1]) in hero_agents):
                    stats["hero"][{ADRENALINE_GAIN: "gain", ADRENALINE_CLEAR: "clear",
                                   ADRENALINE_SPEND: "spend"}[op]] += 1
                    continue
                if op == ADRENALINE_GAIN and int(v[1]) == me:
                    s["gain"] += 1
                    s["strike" if int(v[2]) == STRIKE_UNITS else "sub"] += 1
                elif op == ADRENALINE_CLEAR and int(v[1]) == me:
                    s["clear"] += 1
                elif op == ADRENALINE_SPEND and int(v[1]) == me:
                    s["spend"] += 1
                elif op in DAMAGE_OPS and int(v[1]) in DAMAGE_PROPS + (LIFE_DRAIN_PROP,):
                    if is_damage_to(op, v, me):
                        s["damage_taken"] += 1
                    # only 0x00A3 names a source, so only it can say who landed
                    # -- and a 55 is not a weapon hit, so it is not one here
                    if (op == PROP_FLOAT_TARGET and int(v[3]) == me
                            and int(v[1]) in DAMAGE_PROPS):
                        s["hits_landed"] += 1
                elif (op == PROP_INT and len(v) > 2
                        and int(v[1]) == PROP_MELEE_FINISHED and int(v[2]) == me):
                    s["melee_finished"] += 1

            # THE JOIN IS BY BATCH, and a batch is an identical timestamp. The
            # gain and its damage ride one batch -- gain FIRST, 601 of 663
            # by the following message (test_adrenwire 7).
            batches = collections.defaultdict(list)
            for i, (t, op, v) in enumerate(msgs):
                batches[t].append((i, op, v))
            for t, items in batches.items():
                dmg = [(i, int(v[1]),
                        int(v[3]) if op == PROP_FLOAT_TARGET else None,
                        f32(v[4] if op == PROP_FLOAT_TARGET else v[3]))
                       for i, op, v in items
                       if is_damage_to(op, v, me)]
                sub = [(i, int(v[2])) for i, op, v in items
                       if op == ADRENALINE_GAIN and int(v[1]) == me
                       and int(v[2]) != STRIKE_UNITS]
                if not dmg:
                    continue
                # A BATCH WITH n DAMAGE AND n IDENTICAL GAINS ATTRIBUTES BY
                # SYMMETRY, and refusing to is over-caution that costs rows.
                # The two batches this covers each carry two 6.0417% hits and
                # two 6-unit gains: every assignment gives the same pair, so
                # there is nothing to get wrong. Anything else -- unequal
                # counts, unequal values -- stays ambiguous and is REPORTED,
                # never attributed to whichever damage sorted first.
                symmetric = (len(dmg) == len(sub) and len(sub) > 0
                             and len({u for _i, u in sub}) == 1
                             and len({round(d[3], 9) for d in dmg}) == 1)
                clean = len(dmg) == 1 or symmetric
                for di, prop, src, val in dmg:
                    rows.append({
                        "capture": stamp, "connection": conn, "arm": arm,
                        "index": di, "t": t, "prop": prop, "source": src,
                        "max_health": whose_max_health(msgs, me, di),
                        "value": val, "pct": abs(val) * 100.0,
                        "units": (sub[0][1] if sub and clean else None),
                        "ambiguous": not clean,
                        "adrenal_on_bar": adrenal,
                    })
    return {"captures": captures, "arms": stats}, rows, skipped


def fits(rows):
    """floor / ceil / round, counted over the unambiguous rows that granted."""
    out = collections.Counter()
    for r in rows:
        if r["ambiguous"] or r["units"] is None:
            continue
        pct = r["pct"]
        out["n"] += 1
        for name, val in (("floor", math.floor(pct)),
                          ("ceil", math.ceil(pct)),
                          ("round", int(math.floor(pct + 0.5 + 1e-9)))):
            if val == r["units"]:
                out[name] += 1
    return out


def _ids_from_words(words):
    """A 128-dword unlock bitmap back to skill ids (skillunlock.ids_from_words,
    copied rather than imported so this scanner stays a leaf of tape + codec)."""
    out = []
    for wi, w in enumerate(words):
        w, b = int(w), 0
        while w:
            if w & 1:
                out.append(wi * 32 + b)
            w >>= 1
            b += 1
    return out


def _auth_summaries(cap):
    """appearance dword -> (level, profession, secondary) from the capture's
    AUTH channel (CHARACTER_INFO's summary blobs, s2c), or {} when the capture
    has no auth tape or none decodes. The join key is the appearance dword,
    which 0x0059 carries on the GAME channel for the same character."""
    try:
        import charsummary as cs
        import summarycensus
    except Exception:                                          # noqa: BLE001
        return {}
    out = {}
    for name in sorted(os.listdir(cap)):
        if not (name.startswith("auth-") and name.endswith(".jsonl")):
            continue
        try:
            with open(os.path.join(cap, name), encoding="utf-8") as fh:
                for line in fh:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    if e.get("kind") != "frame" or e.get("direction") != "s2c":
                        continue
                    for blob in summarycensus.find_summaries(e["plain"]):
                        try:
                            f = cs.decode(blob)
                        except cs.Malformed:
                            continue
                        out[int(f["appearance"])] = (
                            int(f["level"]), int(f["profession"]),
                            int(f["secondary"]))
        except OSError:
            continue
    return out


def by_connection(costs=None):
    """One row per usable GAME connection: who the character is, from the wire.

    THE QUESTION THIS ANSWERS (studies/skills 34.5 / 34.11). The corpus split
    ARMED/DARK on the bar, and 34.5 said every dark connection was ALSO a
    non-Warrior -- read off the bar's skills, not off the character. This
    reads the character: 0x00B7's primary/secondary for the observer's own
    agent, the 0x0059 appearance nibble, the level at 0x003A dword 9, and --
    where the capture carries its auth tape -- the CHARACTER_INFO summary's
    level and profession joined on the appearance dword. Two witnesses for
    each of profession and level, from two channels.

    THE THIRD RIVAL, named by the fidelity judge before anything is called
    corroborated: "the character's LEARNED set holds an adrenal skill". The
    account library (0x001D) and the character library (0x00DB) are two
    different sets (skills 47.1, neither contains the other), so both are
    decoded and every adrenal id in either is listed per connection.

    THE BAR IS A TIMELINE, not a set. 0x00DA is the whole bar and 0x00D9 is an
    in-game slot write; the row records whether the bar's ARMED-ness ever
    flipped inside one connection and, if it did, how much fighting happened
    on each side of the flip -- that is the only place a dark-to-armed
    transition could be OBSERVED, and `flips` says whether the corpus holds
    one. A hero's bar (JARIN) is not the observer's and is not read here.

    READ-ONLY, like everything else in this module.
    """
    costs = adrenal_costs() if costs is None else costs
    live = vaultpath.require_dir("captures", "live",
                                 why="the per-connection census")
    codec = Codec()
    rows = []
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        summaries = None
        cap_rows = []
        # the ACCOUNT library, wherever in this capture it was sent
        cap_account = None
        for chan in tape.channel_files(cap):
            conn = chan["connection"]
            try:
                _info, events = tape.load_tape(cap, conn)
                msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                                  # noqa: BLE001
                continue
            me = whose_agent(msgs)
            if me is None:
                continue
            r = {"capture": stamp, "connection": conn, "agent": me,
                 "messages": len(msgs),
                 "span_s": (round(float(msgs[-1][0]) - float(msgs[0][0]), 1)
                            if msgs else 0.0),
                 "bars": [], "flips": [], "profession": None,
                 "secondary": None, "profession_59": None, "level": None,
                 "appearance": None, "summary_level": None,
                 "summary_profession": None, "summary_secondary": None,
                 # the ACCOUNT set: on THIS connection, and anywhere in the
                 # capture (it rides once per session, see ACCOUNT_LIBRARY)
                 "account_adrenal": None, "account_n": None,
                 "account_adrenal_capture": None,
                 "character_adrenal": None, "character_n": None,
                 "gain": 0, "clear": 0, "spend": 0, "hits_landed": 0,
                 "melee_finished": 0, "damage_taken": 0, "deaths": 0,
                 # fighting on each side of the bar's state, IN ORDER; a hit
                 # before the first own 0x00DA is "before_bar", not dark
                 "hits_dark": 0, "hits_armed": 0, "hits_before_bar": 0,
                 "family_dark": 0, "family_before_bar": 0}
            bar, armed = [], None          # None until the first own 0x00DA
            for i, (_t, op, v) in enumerate(msgs):
                if op == SKILLBAR_UPDATE and len(v) > 2 and int(v[1]) == me:
                    bar = [int(x) for x in v[2]]
                    if bar not in r["bars"]:
                        r["bars"].append(list(bar))
                elif (op == SKILLBAR_UPDATE_SKILL and len(v) > 3
                      and int(v[1]) == me):
                    slot = int(v[2])
                    while len(bar) <= slot:
                        bar.append(0)
                    bar[slot] = int(v[3])
                    if bar not in r["bars"]:
                        r["bars"].append(list(bar))
                if r["bars"]:
                    now_armed = any(costs.get(s, 0) > 0 for s in bar if s)
                    if armed is not None and now_armed != armed:
                        r["flips"].append({"index": i,
                                           "to": "armed" if now_armed else "dark"})
                    armed = now_armed
                side = ("before_bar" if armed is None
                        else "armed" if armed else "dark")
                if op == AGENT_PROFESSIONS and len(v) > 3 and int(v[1]) == me:
                    r["profession"], r["secondary"] = int(v[2]), int(v[3])
                elif op == PLAYER_INFO and len(v) > 3 and int(v[2]) == me:
                    r["appearance"] = int(v[3])
                    r["profession_59"] = (int(v[3]) >> PROFESSION_SHIFT) & 0xF
                elif (op == PROP_INT and len(v) > 3 and int(v[1]) == PROP_LEVEL
                      and int(v[2]) == me):
                    r["level"] = int(v[3])
                elif op == ACCOUNT_LIBRARY and len(v) > 1:
                    ids = _ids_from_words(v[1])
                    r["account_n"] = len(ids)
                    r["account_adrenal"] = sorted(
                        s for s in ids if costs.get(s, 0) > 0)
                    cap_account = r["account_adrenal"]
                elif op == CHARACTER_LIBRARY and len(v) > 1:
                    ids = _ids_from_words(v[1])
                    r["character_n"] = len(ids)
                    r["character_adrenal"] = sorted(
                        s for s in ids if costs.get(s, 0) > 0)
                elif (op in (ADRENALINE_GAIN, ADRENALINE_CLEAR, ADRENALINE_SPEND)
                      and int(v[1]) == me):
                    r[{ADRENALINE_GAIN: "gain", ADRENALINE_CLEAR: "clear",
                       ADRENALINE_SPEND: "spend"}[op]] += 1
                    if side == "dark":
                        r["family_dark"] += 1
                    elif side == "before_bar":
                        r["family_before_bar"] += 1
                elif (op == AGENT_UPDATE_FLAGS and len(v) > 2 and int(v[1]) == me
                      and int(v[2]) == PLAYER_DEAD_FLAG):
                    r["deaths"] += 1
                elif op in DAMAGE_OPS and int(v[1]) in DAMAGE_PROPS + (LIFE_DRAIN_PROP,):
                    if is_damage_to(op, v, me):
                        r["damage_taken"] += 1
                    if (op == PROP_FLOAT_TARGET and int(v[3]) == me
                            and int(v[1]) in DAMAGE_PROPS):
                        r["hits_landed"] += 1
                        r["hits_" + side] += 1
                elif (op == PROP_INT and len(v) > 2
                        and int(v[1]) == PROP_MELEE_FINISHED and int(v[2]) == me):
                    r["melee_finished"] += 1
            on_bar = {s for b in r["bars"] for s in b if s}
            r["adrenal_on_bar"] = sorted(s for s in on_bar if costs.get(s, 0) > 0)
            r["arm"] = "armed" if r["adrenal_on_bar"] else "dark"
            if r["appearance"] is not None:
                if summaries is None:
                    summaries = _auth_summaries(cap)
                hit = summaries.get(r["appearance"])
                if hit:
                    (r["summary_level"], r["summary_profession"],
                     r["summary_secondary"]) = hit
            cap_rows.append(r)
        for r in cap_rows:
            r["account_adrenal_capture"] = cap_account
        rows.extend(cap_rows)
    return rows


def print_by_connection(rows):
    """The per-connection table and the dark side's summary."""
    print("arm    gain clr spd  hits melee dmg  dth  prof  lvl  "
          "bar(s) / adrenal on bar / adrenal LEARNED (acct | char)")
    print("-" * 100)
    for r in sorted(rows, key=lambda r: (r["arm"], r["capture"], r["connection"])):
        prof = (f"{r['profession']}/{r['secondary']}"
                if r["profession"] is not None else "?")
        if r["profession_59"] is not None and r["profession_59"] != r["profession"]:
            prof += f"(59:{r['profession_59']})"
        lvl = str(r["level"]) if r["level"] is not None else "?"
        if r["summary_level"] is not None:
            lvl += ("" if r["summary_level"] == r["level"]
                    else f"(sum:{r['summary_level']})")
        bars = " | ".join(str(b) for b in r["bars"]) or "(no own bar)"
        print(f"{r['arm']:5} {r['gain']:5} {r['clear']:3} {r['spend']:3} "
              f"{r['hits_landed']:5} {r['melee_finished']:5} "
              f"{r['damage_taken']:4} {r['deaths']:3}  {prof:6} {lvl:5} "
              f"{r['capture']} {r['connection']}  "
              f"({r['messages']} msgs, {r['span_s']} s)")
        print(f"       bars {bars}")
        acct = (f"{r['account_adrenal']} ({r['account_n']})"
                if r["account_n"] is not None
                else f"{r['account_adrenal_capture']} (from the capture)")
        print(f"       adrenal on bar {r['adrenal_on_bar']}   learned adrenal "
              f"acct {acct} | char {r['character_adrenal']} "
              f"({r['character_n']})")
        if r["flips"] or r["hits_before_bar"] or r["family_before_bar"]:
            print(f"       flips {r['flips']}; hits landed before the bar "
                  f"{r['hits_before_bar']} / dark {r['hits_dark']} / armed "
                  f"{r['hits_armed']}; family messages while dark "
                  f"{r['family_dark']}, before the bar {r['family_before_bar']}")
    dark = [r for r in rows if r["arm"] == "dark"]
    armed = [r for r in rows if r["arm"] == "armed"]
    print()
    print(f"{len(armed)} armed, {len(dark)} dark connections")
    profs = collections.Counter((r["profession"], r["level"]) for r in dark)
    print(f"DARK by (primary profession, level): "
          f"{dict(sorted(profs.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))))}")
    warriors = [r for r in dark if r["profession"] == 1 or r["secondary"] == 1]
    print(f"DARK connections whose character is a Warrior (primary or "
          f"secondary): {len(warriors)}")
    for r in warriors:
        print(f"   {r['capture']} {r['connection']}  prof {r['profession']}/"
              f"{r['secondary']}  level {r['level']}  hits {r['hits_landed']}  "
              f"melee {r['melee_finished']}  gains {r['gain']}  bars {r['bars']}")

    def _learned(r):
        acct = (r["account_adrenal"] if r["account_n"] is not None
                else r["account_adrenal_capture"])
        return bool(acct) or bool(r["character_adrenal"])
    learned = [r for r in dark if _learned(r)]
    print(f"DARK connections whose LEARNED set (account, this capture's, or "
          f"character) holds an adrenal skill: {len(learned)} of {len(dark)}; "
          f"of those, with a landed hit: "
          f"{sum(1 for r in learned if r['hits_landed'])}, gains on them "
          f"{sum(r['gain'] for r in learned)}")
    for r in learned:
        if not r["hits_landed"]:
            continue
        acct = (r["account_adrenal"] if r["account_n"] is not None
                else f"{r['account_adrenal_capture']} (capture)")
        print(f"   {r['capture']} {r['connection']}  acct {acct}"
              f"  char {r['character_adrenal']}  hits {r['hits_landed']}  "
              f"melee {r['melee_finished']}  gains {r['gain']}")
    flips = [r for r in rows if r["flips"]]
    print(f"connections whose bar's armed-ness FLIPPED mid-connection: "
          f"{len(flips)}; hits landed before any own bar arrived: "
          f"{sum(r['hits_before_bar'] for r in rows)}; family messages while "
          f"the bar was dark: {sum(r['family_dark'] for r in rows)}, before "
          f"the bar: {sum(r['family_before_bar'] for r in rows)}")
    disagree = [r for r in rows if r["summary_level"] is not None
                and r["summary_level"] != r["level"]]
    joined = [r for r in rows if r["summary_level"] is not None]
    print(f"level cross-check property 36 vs CHARACTER_INFO summary: "
          f"{len(joined)} joined, {len(disagree)} disagree; connections with "
          f"no property 36 for the observer: "
          f"{sum(1 for r in rows if r['level'] is None)}")
    pdis = [r for r in rows if r["profession_59"] is not None
            and r["profession"] is not None
            and r["profession_59"] != r["profession"]]
    print(f"profession cross-check 0x00B7 vs 0x0059 nibble: "
          f"{sum(1 for r in rows if r['profession_59'] is not None and r['profession'] is not None)} "
          f"joined, {len(pdis)} disagree")
    sdis = [r for r in rows if r["summary_profession"] is not None
            and r["summary_profession"] != r["profession"]]
    print(f"profession cross-check 0x00B7 vs summary: "
          f"{sum(1 for r in rows if r['summary_profession'] is not None)} "
          f"joined, {len(sdis)} disagree")
    print(f"deaths on dark connections: {sum(r['deaths'] for r in dark)}; "
          f"0x00D0 clears on those: {sum(r['clear'] for r in dark)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true",
                    help="print every damage-to-self row, sorted by percentage")
    ap.add_argument("--bars", action="store_true",
                    help="print every connection's OWN 0x00DA bar (see bars())")
    ap.add_argument("--by-connection", action="store_true",
                    help="one row per connection: profession and level from the "
                         "wire, the learned sets' adrenal ids, the bar timeline, "
                         "and the family counts (see by_connection())")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.by_connection:
        found = by_connection()
        if args.json:
            print(json.dumps(found, indent=2))
            return 0
        print_by_connection(found)
        return 0

    if args.bars:
        found = bars()
        if args.json:
            print(json.dumps(found, indent=2))
            return 0
        for b in found:
            print(f"{b['capture']}  {b['connection']}  agent {b['agent']:4}  "
                  f"{b['bar']}")
        print(f"\n{len(found)} own-agent bar updates")
        return 0

    stats, rows, skipped = scan()
    if args.json:
        print(json.dumps({"stats": {k: dict(v) for k, v in stats["arms"].items()},
                          "captures": stats["captures"],
                          "rows": rows, "skipped": skipped}, indent=2))
        return 0

    print(f"captures {stats['captures']}   skipped (no unique self agent) "
          f"{len(skipped)}")
    for s in skipped:
        print(f"   {s['capture']}  {s['connection']}")
    print()
    for arm in ("armed", "dark"):
        d = stats["arms"][arm]
        label = ("ARMED -- at least one adrenal skill on the bar" if arm == "armed"
                 else "DARK  -- no adrenal skill, ever, on the bar")
        print(f"{label}")
        print(f"   {d['connections']:3} connections, {d['messages']:6} messages")
        print(f"   0x00CF gain  {d['gain']:5}  ({d['strike']} at {STRIKE_UNITS}, "
              f"{d['sub']} below)")
        print(f"   0x00D0 clear {d['clear']:5}      0x00D2 spend {d['spend']:5}")
        print(f"   damage taken {d['damage_taken']:5}   hits landed "
              f"{d['hits_landed']:5}   melee finished {d['melee_finished']:5}")
        print()

    for arm in ("armed", "dark"):
        mine = [r for r in rows if r["arm"] == arm and not r["ambiguous"]]
        gained = [r for r in mine if r["units"] is not None]
        none = [r for r in mine if r["units"] is None]
        print(f"{arm.upper():6} damage-to-self, unambiguous batches {len(mine):3}"
              f"   granted {len(gained):3}   granted nothing {len(none):3}")
        if mine:
            print(f"       percentage range "
                  f"{min(r['pct'] for r in mine):.9f} .. "
                  f"{max(r['pct'] for r in mine):.9f}")
            band = [r for r in mine if 0.5 <= r["pct"] < 1.0]
            print(f"       in the band where round and ceil DISAGREE "
                  f"[0.5%, 1.0%): {len(band)} rows"
                  + (f" -- {[round(r['pct'], 9) for r in band]}" if band else ""))
        if gained:
            f = fits(mine)
            print(f"       over {f['n']} joined rows: floor {f['floor']}, "
                  f"ceil {f['ceil']}, round {f['round']}")
            units = collections.Counter(r["units"] for r in gained)
            print(f"       units granted {dict(sorted(units.items()))}")
        print()

    if args.rows:
        print("       pct        units  floor ceil round  maxH  prop  arm   capture")
        print("   " + "-" * 76)
        for r in sorted(rows, key=lambda r: (r["arm"], r["pct"])):
            pct = r["pct"]
            print(f"   {pct:12.9f} {str(r['units']):>6}  "
                  f"{math.floor(pct):5} {math.ceil(pct):4} "
                  f"{int(math.floor(pct + 0.5 + 1e-9)):5}  "
                  f"{str(r['max_health']):>4}  {r['prop']:4}  "
                  f"{r['arm']:5}  {r['capture']}"
                  + ("  AMBIGUOUS" if r["ambiguous"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
