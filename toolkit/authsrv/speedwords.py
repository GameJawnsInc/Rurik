r"""Movement speed on retail's wire: every 0x0027 joined to the episode change that sent it.

    python toolkit/authsrv/speedwords.py            # every live capture
    python toolkit/authsrv/speedwords.py --rows     # one line per speed word
    python toolkit/authsrv/speedwords.py --json     # stdout is the JSON alone

THE CHANNEL. `GAME_SMSG 0x0027 AGENT_UPDATE_SPEED_BASE [agent, f32 u/s]` is the
maxSpeed store at agent+0x5C (agtrack_mirror), and it is the ONLY channel a
movement-speed modifier rides: 0x002B's float is asserted into [0.01, 1.0]
(test_familyrate) and cannot carry a buff. The server's own writer is
`authsrv.push_speed`; this is its reader, written first, the way `bufflog.py`
preceded `effects.py` and `deepwoundjoin.py` preceded the Deep Wound batch.

THE PREDICTIONS, stated before the scan (studies/slice/FINDINGS.md SLICE-F48
carries the numbers the first run produced; a later corpus that stops agreeing
goes red in test_speedwords.py rather than drifting):

  P1  a 0x0042 apply of skill 160 (Windborne Speed) or 364 ("Charge!") on an
      agent with NO boost open is joined, in the same batch, by a 0x0027 at
      exactly base x 1.33 -- GWW's "move 33% faster" for both skills;
  P2  a 0x0042 apply of 481 (Crippled) is joined by a 0x0027 at base x 0.5 --
      GWW "Crippled": "you move 50% slower";
  P3  Crippled OVER an open 33% boost reads base x 0.665 = 1.33 x 0.5: the
      condition MULTIPLIES the boosted rate (an additive reading, 1 + 0.33 -
      0.5 = 0.83, is refuted by every such row);
  P4  a second 33% boost applied over an open one reads base x 1.34, not 1.33
      (a "largest applies" rule) and not 1.77 (uncapped): GWW "Speed boost"
      (rev. 2020-05-09): boosts "can be stacked, but movement rate is capped
      at 34% faster than normal";
  P5  the "Charge!" cure batch carries TWO speed words -- the shout's apply
      over the still-open Crippled (x 0.665) and then the cure's restore
      (x 1.33) -- so retail re-declares at EVERY episode change, not once per
      net change;
  P6  a body's base is what its restores return to, and it is not one number:
      288.0 for the player and most bodies, 300.0 for some hostiles.

SLICE-F48b (2026-10-07): AN OVER-CAP SNARE OVER A BOOST. Added after a triage
survey of the corpus had already seen the words, so these are the reader's
predictions, not blind ones -- each was written down (the session's notes)
before this reader's own run, and each can go red on a corpus that disagrees:

  P7  a 75% snare reads base x 0.25 EXACTLY: skill 493's own 0x0042 apply (the
      client table, build 38797: type 5, scale 75/75, duration 5/5) on an
      agent with no slow open is joined by a 0x0027 at base x 0.25 (P7a), and
      every word in the x0.25 CLASS (within 0.02 of it) is exactly a quarter of
      its base -- 72.0 on 288, 75.0 on 300. Scoped to the class, not to "every
      word under x0.3": a deeper slow that is not 75% (Crippled over a 66
      override, 0.17; a 90 snare, 0.10) contradicts nothing here, and is
      printed as an unscored census line rather than counted a miss;
  P7j (a census, not a prediction) which x0.25 words the wire ATTRIBUTES to
      493 -- a 493 0x0042, or an 0x0043 EFFECT_RENEWED of a buff a 493 apply
      opened, on ANY agent within the batch shoulder. On the corpus 9 of 14
      are (1 apply, 8 renewals of the observer's buff 63); the other 5, both
      of P9's witnesses among them, have no source on the wire at all;
  P8  a boost (160 / 364) applied to -- or ending on -- an agent whose last
      word is an OVER-CAP snare (below base x 0.5) sends NO 0x0027 for it,
      while the same batch MOVES another agent's word with the boost (P8b, the
      control: the boost did reach the wire -- up at its apply, down at its
      end, from and to at or above x0.5, so a snared foe's onset or restore in
      the same batch is not mistaken for it), and the same boost on an
      UNSLOWED agent is worded (P8c, the walker's own control);
  P9  the over-cap snare's END on a boosted body restores the PRE-snare boosted
      word -- the boost was suppressed, not cancelled. The ratio is OBSERVED;
      WHICH snare it was is not (P7j: neither witness is joined to 493);
  and the two rules the corpus would have shown instead are scored against
  the same exposure, expected 0: MULTIPLICATIVE (GWW "Effect stacking"'s
  Flail example: a boosted onset at b x s, a word at every boost change) and
  ADDITIVE (b - (1 - s), the bundle row's arithmetic, slice F48.3). What the
  corpus says instead is an OVERRIDE: past the -50 cap the single snare's
  number IS the factor and the boosts are dropped (episodemods.
  SNARE_OVERRIDES_BOOST, studies/slice/FINDINGS.md F48.7).

WHAT `base` IS HERE. The per-(connection, agent) value the agent is RESTORED
to -- the most common of {288, 300} among its speed words. An agent that never
shows a plain base (one word, e.g. a Crippled body created mid-episode) gets
`base = None` and a `ratio = None`; it is counted, never scored.

Standard library only. Reads the vault through `vaultpath`, refuses a partial
tape the way bufflog does. A connection the capture's OWN manifest declares
gapped (capgaps.py: 20260928T103123 :65009) is set aside BY NAME through
`tape.whole_channels`; any other refusal raises out of the walk (until
2026-10-07 an `except` here dropped :65009 with nothing said -- measured then,
it was the only connection of 128 the clause ever caught). The set-aside line
is printed; under `--json` it goes to stderr, so stdout stays parseable.
"""
import argparse
import bisect
import collections
import contextlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import bufflog      # noqa: E402  (BuffLogError, Codec)
import tape         # noqa: E402
import vaultpath    # noqa: E402

OP_SPEED = 0x0027
OP_APPLY = 0x0042
OP_REMOVE = 0x0044
OP_RENEW = 0x0043         # EFFECT_RENEWED [agent, u32, buff, duration] (studies/skills' table);
                          # field 3 is the buff a 0x0042 opened -- OBSERVED: 33 of 33 renewals
                          # on 103123 :50295 name 493's buff 63 with its 5.0 s duration
OP_STATUS = 0x00F1
OP_ITEM = 0x006F
BATCH_S = 0.060          # the corpus's own batch shoulder, as deepwoundjoin uses it
BASES = (288.0, 300.0)   # P6: the two restore values the corpus shows
BOOST_SKILLS = (160, 364)
CRIPPLED = 481
PLAYER_INFO = 0x0059
SNARE_75 = 493            # P7: the one over-cap snare whose own 0x0042 is on tape
P7_CLASS = 0.02           # P7: the x0.25 class -- |ratio - 0.25| below this
OVERCAP = 0.5             # P8/P9: a word below base x 0.5 is a snare past the -50 cap
SNARE_CLASSES = (0.25, 0.34)   # the over-cap ratios seen UNBOOSTED: P7's 75, Teinai's 66
BOOST_PCT = 0.33          # 160's and 364's own 33 (P1), the boost P8's events carry


def f32(v):
    if isinstance(v, float):
        return v
    return struct.unpack("<f", struct.pack("<I", int(v) & 0xFFFFFFFF))[0]


def sequence(capture_dir, connection, codec):
    """[(t, op, values)] for one game connection, framed once, whole."""
    info, events = tape.load_tape(capture_dir, connection)
    t0 = info.get("t0") or 0.0
    # Events.of keeps the tape's build through the rebase (WIREORDER-B1).
    events = tape.Events.of([(round(t + t0, 6), p) for t, p in events], events)
    msgs, (consumed, total, err) = tape.decode_all(events, codec, "GAME_SMSG", 0)
    if err is not None or consumed != total:
        raise bufflog.BuffLogError(
            f"{capture_dir} {connection} framed {consumed}/{total}: {err}")
    return msgs


def source_times(msgs, skill):
    """The instants `skill` is on the wire in one decoded connection, on ANY agent: its
    0x0042 applies, and every 0x0043 renewal of a buff such an apply opened, until that
    buff's 0x0044 (P7j). Sorted, since `msgs` is."""
    buffs, out = set(), []
    for t, op, v in msgs:
        if op == OP_APPLY and len(v) > 4:
            if v[2] == skill:
                buffs.add((v[1], v[4]))
                out.append(t)
            else:
                buffs.discard((v[1], v[4]))
        elif op == OP_RENEW and len(v) > 3 and (v[1], v[3]) in buffs:
            out.append(t)
        elif op == OP_REMOVE and len(v) > 2:
            buffs.discard((v[1], v[2]))
    return out


def _near(times, t):
    """True when a sorted `times` holds an instant within BATCH_S of `t`."""
    i = bisect.bisect_left(times, t - BATCH_S)
    return i < len(times) and times[i] <= t + BATCH_S


def speed_rows(msgs):
    """Every 0x0027 in a decoded connection, with its batch companions.

    `apply`/`remove`/`status`/`item` are the same-agent companions within
    BATCH_S either side; `words_in_batch` counts the speed words this agent
    received in that shoulder (P5's two); `prev` is the agent's previous word;
    `joined_493` says the shoulder holds 493 on ANY agent (`source_times`, P7j).
    """
    player = next((v[1] for _t, op, v in msgs if op == PLAYER_INFO and len(v) > 1),
                  None)
    src = source_times(msgs, SNARE_75)
    rows, last = [], {}
    idx = [i for i, (_t, op, _v) in enumerate(msgs) if op == OP_SPEED]
    for i in idx:
        t, _op, v = msgs[i]
        agent, val = v[1], f32(v[2])
        near = {"apply": [], "remove": [], "status": [], "item": 0, "words": 0}
        j = i - 1
        while j >= 0 and t - msgs[j][0] <= BATCH_S:
            _collect(msgs[j], agent, near)
            j -= 1
        j = i + 1
        while j < len(msgs) and msgs[j][0] - t <= BATCH_S:
            _collect(msgs[j], agent, near)
            j += 1
        rows.append({"t": round(t, 3), "agent": agent, "is_player": agent == player,
                     "val": round(val, 4), "prev": last.get(agent),
                     "apply": near["apply"], "remove": near["remove"],
                     "status": near["status"], "item_change": near["item"],
                     "words_in_batch": near["words"] + 1, "joined_493": _near(src, t)})
        last[agent] = round(val, 4)
    return rows


def _collect(msg, agent, near):
    _t, op, v = msg
    if len(v) < 2 or v[1] != agent:
        return
    if op == OP_APPLY:
        near["apply"].append(v[2])
    elif op == OP_REMOVE:
        near["remove"].append(v[2])
    elif op == OP_STATUS:
        near["status"].append(v[2])
    elif op == OP_ITEM:
        near["item"] += 1
    elif op == OP_SPEED:
        near["words"] += 1


def with_bases(rows):
    """Attach `base` (P6) and `ratio` per agent, in place; returns rows."""
    by_agent = collections.defaultdict(list)
    for r in rows:
        by_agent[r["agent"]].append(r["val"])
    base = {}
    for a, vals in by_agent.items():
        c = collections.Counter(v for v in vals if v in BASES)
        base[a] = c.most_common(1)[0][0] if c else None
    for r in rows:
        b = base[r["agent"]]
        r["base"] = b
        r["ratio"] = round(r["val"] / b, 4) if b else None
    return rows


def boost_events(msgs, rows):
    """P8's exposure: every boost APPLY (0x0042 of 160 / 364) and boost END (the
    0x0044 closing a buff such an apply opened) in one decoded connection, with
    the agent's speed state around it. Only an agent whose effects reach this
    client as 0x0042 / 0x0044 -- the observer -- can appear: a body's boost is
    visible only as its word, so a silent body would prove nothing (earshot).

    `prev` is the agent's last word before the batch (more than BATCH_S before
    the event), `own` its words inside the shoulder, `others` every other
    agent's words inside it, and `others_moved` the other agents whose word the
    batch MOVED WITH THE BOOST (P8b): up at an apply, down at an end, from a last
    word at or above base x OVERCAP to a word at or above it. A snared agent's
    onset or restore in the same shoulder is a word, but not this boost's."""
    base = {r["agent"]: r["base"] for r in rows}
    words = [(t, v[1], round(f32(v[2]), 4)) for t, op, v in msgs
             if op == OP_SPEED and len(v) > 2]

    def last_before(agent, t):
        prev = None
        for tw, a, val in words:
            if tw >= t - BATCH_S:
                break
            if a == agent:
                prev = val
        return prev

    def moved(agent, val, t, up):
        b, p = base.get(agent), last_before(agent, t)
        if not b or p is None or p / b < OVERCAP or val / b < OVERCAP:
            return False
        return val > p if up else val < p
    buffs, out = {}, []
    for t, op, v in msgs:
        if op == OP_APPLY and len(v) > 4:
            buffs[(v[1], v[4])] = v[2]
            if v[2] not in BOOST_SKILLS:
                continue
            kind, agent, skill, buff = "apply", v[1], v[2], v[4]
        elif op == OP_REMOVE and len(v) > 2:
            skill = buffs.pop((v[1], v[2]), None)
            if skill not in BOOST_SKILLS:
                continue
            kind, agent, buff = "end", v[1], v[2]
        else:
            continue
        prev = last_before(agent, t)
        near = [(a, val) for tw, a, val in words if abs(tw - t) <= BATCH_S]
        b = base.get(agent)
        others = [(a, val) for a, val in near if a != agent]
        out.append({"t": round(t, 3), "kind": kind, "agent": agent, "skill": skill,
                    "buff": buff, "base": b, "prev": prev,
                    "prev_ratio": round(prev / b, 4) if (b and prev is not None) else None,
                    "own": [val for a, val in near if a == agent],
                    "others": others,
                    "others_moved": sorted({a for a, val in others
                                            if moved(a, val, t, kind == "apply")})})
    return out


def census(codec=None, events=None, set_aside=None):
    """Every live capture, every game connection holding a speed word.

    `events`, if a list, receives every connection's `boost_events` (P8);
    `set_aside`, if a list, receives every connection the capture's manifest
    declares gapped (capgaps.set_aside), for the caller's capgaps.audit."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="speedwords reads live captures")
    set_aside = [] if set_aside is None else set_aside
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for row in tape.whole_channels(cap_dir, set_aside):
            msgs = sequence(cap_dir, row["connection"], codec)
            rows = with_bases(speed_rows(msgs))
            if not rows:
                continue
            try:
                map_id = tape.client_version(cap_dir, row["connection"])["map_id"]
            except tape.TapeError:
                map_id = None
            for r in rows:
                r.update(capture=stamp, connection=row["connection"], map_id=map_id)
            out.extend(rows)
            if events is not None:
                for e in boost_events(msgs, rows):
                    e.update(capture=stamp, connection=row["connection"])
                    events.append(e)
    return out


def snare_episodes(rows):
    """Every over-cap snare episode in the rows: per (capture, connection, agent),
    a run of words below base x OVERCAP, with the word before it (`pre`) and the
    first word after it at or above OVERCAP (`restore`, None if the tape ends)."""
    seqs = collections.defaultdict(list)
    for r in rows:
        if r["ratio"] is not None:
            seqs[(r.get("capture"), r.get("connection"), r["agent"])].append(r)
    out = []
    for key, seq in seqs.items():
        seq.sort(key=lambda r: r["t"])
        for i, r in enumerate(seq):
            if not (0.0 < r["ratio"] < OVERCAP):
                continue
            if i and seq[i - 1]["ratio"] < OVERCAP:
                continue                     # inside a run, not its onset
            pre = seq[i - 1] if i else None
            restore = next((s for s in seq[i + 1:] if s["ratio"] >= OVERCAP), None)
            out.append({"key": key, "onset": r, "pre": pre, "restore": restore})
    return out


def score(rows, events=None):
    """The predictions against the rows. Returns {name: (hits, misses, detail)}.

    `events` is census()'s `boost_events` list (P8 and P10's event half); without
    it P8 is unexposed (0 / 0) and the P10 arms score the onsets alone.

    Each prediction is scored ONLY on the rows that expose it (a row with no
    base is never a miss), and the exposure count is what test_speedwords.py
    pins as a floor -- a corpus that lost its witnesses would go red there.
    """
    out = {}

    # P1: a 33% boost applied with none open -> x1.33.
    hit = miss = 0
    for r in rows:
        if r["ratio"] is None or not any(s in BOOST_SKILLS for s in r["apply"]):
            continue
        if r["prev"] is not None and r["prev"] > r["base"]:
            continue                 # a boost was already open: that is P4's row
        if r["prev"] is not None and r["prev"] < r["base"]:
            continue                 # applied over a snare: P3/P5's rows
        if r["ratio"] == 1.33:
            hit += 1
        else:
            miss += 1
    out["P1 boost x1.33"] = (hit, miss, "160/364 apply, nothing open")

    # P2: Crippled applied with nothing else -> x0.5.
    hit = miss = 0
    for r in rows:
        if r["ratio"] is None or CRIPPLED not in r["apply"]:
            continue
        if r["prev"] is not None and r["prev"] != r["base"]:
            continue
        if r["ratio"] == 0.5:
            hit += 1
        else:
            miss += 1
    out["P2 crippled x0.5"] = (hit, miss, "481 apply, nothing open")

    # P3: crippled over a boost, or a boost over crippled -> x0.665 (multiplicative).
    hit = miss = 0
    for r in rows:
        if r["ratio"] is None or r["prev"] is None:
            continue
        pr = round(r["prev"] / r["base"], 4)
        boost_over_cripple = (pr == 0.5 and any(s in BOOST_SKILLS for s in r["apply"]))
        cripple_over_boost = (pr == 1.33 and CRIPPLED in r["apply"])
        # the un-joined 0.665s (an 0x0027 with no same-batch apply, e.g. the
        # condition arrived on a body created mid-episode) score by value alone
        if not (boost_over_cripple or cripple_over_boost):
            continue
        if r["ratio"] == 0.665:
            hit += 1
        else:
            miss += 1
    out["P3 crippled x boost = x0.665"] = (hit, miss, "joined pairs only")
    n665 = sum(1 for r in rows if r["ratio"] == 0.665)
    n083 = sum(1 for r in rows if r["ratio"] == 0.83)
    out["P3b additive 0.83 never seen"] = (n665, n083, "x0.665 rows vs x0.83 rows")

    # P4: a second 33% boost over an open one -> x1.34, the cap.
    hit = miss = 0
    for r in rows:
        if r["ratio"] is None or r["prev"] is None:
            continue
        if round(r["prev"] / r["base"], 4) != 1.33:
            continue
        if not any(s in BOOST_SKILLS for s in r["apply"]):
            continue
        if r["ratio"] == 1.34:
            hit += 1
        else:
            miss += 1
    out["P4 second boost = x1.34 cap"] = (hit, miss, "160/364 apply over x1.33")

    # P5: the cure batch (364 apply + 481 remove in one batch) carries two words.
    hit = miss = 0
    for r in rows:
        if 364 not in r["apply"] or not r["remove"]:
            continue
        if r["ratio"] not in (0.665, 1.33):
            continue
        if r["words_in_batch"] >= 2:
            hit += 1
        else:
            miss += 1
    out["P5 cure batch has 2 words"] = (hit // 2, miss, "each pair counted once")

    # P6: bases are 288 or 300, and a restore returns exactly to them.
    bases = collections.Counter(r["base"] for r in rows if r["base"] is not None)
    out["P6 bases"] = (bases.get(288.0, 0), bases.get(300.0, 0), "words on 288 / on 300")

    # P7: the 75% snare is base x 0.25 exactly -- every word in the x0.25 class.
    # Scoped to the class (2026-10-07 review): a deeper slow that is not 75% is
    # not this prediction's to refute, and is listed unscored below instead.
    quarter = [r for r in rows if r["ratio"] is not None
               and abs(r["ratio"] - 0.25) < P7_CLASS]
    hit = sum(1 for r in quarter if r["val"] == r["base"] * 0.25)
    out["P7 75% snare = x0.25 exactly"] = (hit, len(quarter) - hit,
                                          f"every word within {P7_CLASS} of x0.25")
    deeper = sorted({r["ratio"] for r in rows if r["ratio"] is not None
                     and 0.0 < r["ratio"] < 0.3 and abs(r["ratio"] - 0.25) >= P7_CLASS})
    out["P7 census: other words under x0.3 (unscored)"] = (
        sum(1 for r in rows if r["ratio"] in deeper), 0, f"ratios {deeper}")
    # P7a: 493's own apply on an agent with no slow open (Crippled under it would
    # read 0.125 and refute nothing); a boosted agent IS exposed -- the override
    # says 0.25 there too, the product 0.3325.
    joined = [r for r in rows if SNARE_75 in r["apply"] and r["ratio"] is not None
              and (r["prev"] is None or r["prev"] >= r["base"])]
    out["P7a 493's own apply joined at x0.25"] = (
        sum(1 for r in joined if r["ratio"] == 0.25),
        sum(1 for r in joined if r["ratio"] != 0.25),
        "0x0042 493 + 0x0027 in one batch, no slow open")
    # P7j: which of the x0.25 words the wire attributes to 493 at all.
    out["P7j x0.25 words batch-joined to 493 (a census)"] = (
        sum(1 for r in quarter if r.get("joined_493")),
        sum(1 for r in quarter if not r.get("joined_493")),
        "joined / NO source on the wire: a 493 0x0042 or 0x0043 renewal, any agent")

    # P8: a boost applied to / ending on an over-cap-snared agent sends no word.
    ev = events or []
    snared = [e for e in ev if e["prev_ratio"] is not None and e["prev_ratio"] < OVERCAP]
    silent = [e for e in snared if not e["own"]]
    out["P8 boost under an over-cap snare is silent"] = (
        len(silent), len(snared) - len(silent), "160/364 apply or end, last word < x0.5")
    out["P8b control: the same batch words another agent"] = (
        sum(1 for e in snared if e["others_moved"]),
        sum(1 for e in snared if not e["others_moved"]),
        "another agent's word moves with the boost, unsnared before and after")
    plain = [e for e in ev if e["kind"] == "apply" and e["prev_ratio"] == 1.0]
    out["P8c control: a boost on an unslowed agent is worded"] = (
        sum(1 for e in plain if e["own"]), sum(1 for e in plain if not e["own"]),
        "160/364 apply, last word x1.0")

    # P9: a boosted body's over-cap snare ends back on its pre-snare boosted word.
    eps = snare_episodes(rows)
    boosted = [e for e in eps if e["pre"] is not None and e["pre"]["ratio"] > 1.0]
    n_src = sum(1 for e in boosted if e["onset"].get("joined_493"))
    out["P9 the snare's end restores the boost"] = (
        sum(1 for e in boosted if e["restore"] and e["restore"]["val"] == e["pre"]["val"]),
        sum(1 for e in boosted if not (e["restore"] and e["restore"]["val"] == e["pre"]["val"])),
        f"boosted onsets: the first word back at or above x0.5; {n_src} of "
        f"{len(boosted)} onsets batch-joined to 493 (P7j)")

    # The three rules over the SAME exposure: the boosted onsets (an onset at r
    # after a boosted b) and P8's snared events. An arm agrees with an onset if
    # SOME over-cap ratio seen unboosted (SNARE_CLASSES) explains r under it; with
    # a P8 event if the wire carries what it predicts -- override: no word; the
    # other two: a word at THEIR number, r0 x 1.33 / r0 + 0.33 at a boost's apply
    # over a snare read at r0, r0 / 1.33 / r0 - 0.33 at its end (both boosts are
    # 33%, P1).
    def onset_agrees(rule, b, r):
        for s in SNARE_CLASSES:
            want = {"override": s, "multiplicative": b * s, "additive": b - (1.0 - s)}[rule]
            if abs(r - round(want, 4)) < 1e-9:
                return True
        return False

    def event_agrees(rule, e):
        if rule == "override":
            return not e["own"]
        r0, up = e["prev_ratio"], e["kind"] == "apply"
        want = ((r0 * (1 + BOOST_PCT) if up else r0 / (1 + BOOST_PCT))
                if rule == "multiplicative" else
                (r0 + BOOST_PCT if up else r0 - BOOST_PCT))
        return any(abs(v / e["base"] - want) < 5e-4 for v in e["own"])
    for rule, label in (("override", "P10 OVERRIDE (shipped): an over-cap snare drops the boosts"),
                        ("multiplicative", "P10m MULTIPLICATIVE b x s (REFUTED)"),
                        ("additive", "P10a ADDITIVE b - (1 - s) (REFUTED)")):
        agree = sum(1 for e in boosted
                    if onset_agrees(rule, e["pre"]["ratio"], e["onset"]["ratio"]))
        agree += sum(1 for e in snared if event_agrees(rule, e))
        n = len(boosted) + len(snared)
        out[label] = (agree, n - agree, f"agree / disagree over {len(boosted)} boosted "
                                        f"onsets + {len(snared)} boost events under a snare")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true",
                    help="the rows as JSON on stdout, ALONE: the census's own lines "
                         "(capgaps' SET ASIDE) go to stderr")
    ap.add_argument("--rows", action="store_true", help="one line per speed word")
    args = ap.parse_args(argv)
    events = []
    if args.json:
        # The set-aside notice is still said, just not into the JSON stream (until
        # 2026-10-07's review it landed ahead of the '[' and json.load refused it).
        with contextlib.redirect_stdout(sys.stderr):
            rows = census(events=events)
        print(json.dumps(rows, default=str))
        return
    rows = census(events=events)
    if args.rows:
        for r in rows:
            print(f"{r['capture']} {r['connection']} t={r['t']:.3f} agent {r['agent']}"
                  f"{' (player)' if r['is_player'] else ''} {r['val']} "
                  f"base={r['base']} ratio={r['ratio']} apply={r['apply']} "
                  f"remove={r['remove']} status={[hex(s) for s in r['status']]}")
    caps = len(set(r["capture"] for r in rows))
    print(f"{len(rows)} speed words over {caps} captures")
    hist = collections.Counter((r["ratio"], tuple(r["apply"]), tuple(r["remove"]))
                               for r in rows)
    print("\nratio to the agent's own base, with the batch's applies / removes:")
    for (ratio, ap_, rm), n in sorted(hist.items(),
                                      key=lambda kv: (kv[0][0] is None, kv[0][0] or 0, -kv[1])):
        print(f"  {n:4d}  x{ratio}  apply={list(ap_)}  remove={list(rm)}")
    print("\npredictions:")
    for name, (hit, miss, detail) in score(rows, events).items():
        print(f"  {name}: {hit} / {miss}  ({detail})")
    if args.rows:
        print("\nboost events on an agent whose last word is below x0.5 (P8):")
        for e in events:
            if e["prev_ratio"] is not None and e["prev_ratio"] < OVERCAP:
                print(f"  {e['capture']} {e['connection']} t={e['t']:.3f} {e['kind']} "
                      f"{e['skill']} (buff {e['buff']}) on {e['agent']}, last word "
                      f"{e['prev']} (x{e['prev_ratio']}): own {e['own']}, others {e['others']}"
                      f", moved with the boost {e['others_moved']}")


if __name__ == "__main__":
    main()
