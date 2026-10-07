r"""Trigger-on-cast payoffs on retail's wire: Aura of Restoration 180 heals its bearer per spell.

    python toolkit/authsrv/trigjoin.py              # every live capture: the predictions, PASS/FAIL
    python toolkit/authsrv/trigjoin.py --rows       # plus one line per bearer cast end
    python toolkit/authsrv/trigjoin.py --json
    python toolkit/authsrv/trigjoin.py --stamp 20260817T231139   # one capture

WHY THIS EXISTS. SKILLS-CT (studies/skills/FINDINGS.md 69, DESKWORK pass 9): the largest
unbuilt skill family is the event-triggered effect (~106 rows, ~5 modelled), and the
strongest retail evidence for any of it is Aura of Restoration (180, an Elementalist
enchantment, 5 energy, 0.25 s, 60 s at every rank, scale 200..500 %): while it is up, the
bearer's every spell completion carries a self-heal word. Before a server line was written
for it, the triage's scratch census was re-derived here so the server's `on_cast_triggers`
rests on a committed reader that can go red. test_trigcast.py section 6 locks what it
prints.

METHOD. Captures and connections are `hexjoin.census()`'s -- livewire.live_captures
(origin LIVE only), deepwoundjoin.sequence (a connection that does not frame whole is
REFUSED, counted), each connection scored on ITS OWN build's skill table
(hexjoin.build_table, the vault's pristine image of that build), and the one
manifest-declared gapped connection (20260928T103123 :65009) set aside by name. Every
agent's casts are read in WIRE ORDER (`casts_in_order`): an announce (0x00A0 / 0x009F
props 60 / 50 / 48) is closed by the agent's first end word (0x009F 58 finished; 59 / 45 /
35 stopped) after it and outside the announce's own instant; a newer announce first
supersedes it.

THE EPISODE. A 180 episode opens at its own [58, b, 0] and is LIVE until, in wire order,
the first of: [7, b, 13] -- the shared 'enchanted' class marker withdrawn, so NO
enchantment is left on b (ENCH_CLASS_VISUAL, MEASURED in
studies/monsterai/review/zaishenrun.py on 20260929T100038; [6, b, 11] rides beside it on an
Elementalist and is not read); b's death bit (0x00F1 0x10); the arena round's end (0x0181,
hexjoin G4r); the next 180 completion (a refresh); or 60 s (the record's duration, 60 / 60,
`EPISODE_S`, no tolerance). A strip that leaves ANOTHER enchantment on b withdraws no
marker and is invisible -- such a completion stays LIVE here, and a missing word on it is
printed as a miss beside the Drain Enchantment 68 completions onto b since the episode
opened (the only explanation P1c accepts), never dropped.

THE PREDICTIONS, exactly as REGISTERED 2026-10-07 before this reader's first run (the
priors: the triage's scratch census -- a 60 s window from each 180 ANNOUNCE, no strip
reading -- and its example 20260817T231139 :54071 611.361):
  P1  ORDER. Under a LIVE 180 episode every completion ([58, b, 0]) of the bearer's SPELL
      (combatmath.is_spell_type -- the server's own predicate) carries exactly one
      0x00A3 [55, b, b, +f], and it is the FIRST b-word of the completion batch, AHEAD of
      [58, b, 0]. The triage's lead: >= 244 of 249 on the captures other than
      20260929T100038.
  P2  AMOUNT. f x max == round(paid energy x interp(scale0, scale15, rank) / 100); the
      bearer's max is not on the wire for most bodies, so the max-free test is the RATIO: a
      bearer's cost-10 word is exactly twice its cost-5 word (2.000 to f32 precision).
      The triage's lead: cost 5 -> 0.04144, cost 10 -> 0.08288 on a 555-max bearer.
  P3  STRIPS. On 20260929T100038 (the triage's 69 of 119 without a word) the completions
      with no word are completions where 180 is no longer LIVE (Drain Enchantment 68
      stripped it): every miss on a live episode is explained, and a completion under no
      live episode carries no word.
  KNOWN-BAD ARMS the reader must redden on: ARM-FIXED, a fixed heal per spell (the
  bearer's first word for every cost) -- breaks P2's ratio; ARM-AFTER58, the payoff
  emitted AFTER the [58] -- breaks P1's order.
REGISTERED AS QUESTIONS, no prediction: Q4 does a 180 completing under a live 180 (a
refresh) carry the word; Q5 does a NON-spell completion (a signet) under a live 180 carry
one; Q6 does a STOPPED cast's end batch carry one.

WHAT THE FIRST RUN SHOWED (registered after it; the predictions above are NOT re-worded):
  P1 FAILED AS REGISTERED, on its "FIRST b-word" clause only: on a MIXED instant another
  event naming b shares the completion's instant ahead of the word (b's own Fire Storm
  tick, a foe's announce onto b, b's [57]) -- `p1_mixed`. Every word the corpus holds sits
  IMMEDIATELY ahead of [58, b, 0], the message right before it. P1c, the corrected
  reading with no free parameter: exactly one [55, b, b, +f] ahead of the [58] and it is
  the message immediately before it; a live completion with no word is a miss unless a
  Drain Enchantment completed onto b since the episode opened (P3's strip the marker
  could not show) -- and 0 unexplained misses. The first run's EPISODE_TOL of 0.05 s
  called a completion at age 60.031 live (no word): the tolerance is now 0, the record's
  60 s.
  P2 FAILED AS REGISTERED on one bearer, 20260928T103123's Zaishen Mage (agent 9): six
  words of 0.08132 / 0.03956 beside its clean 0.08288 / 0.04144 -- every one with the
  bearer's 0x00F1 carrying 0x20 (effects.STATUS_DEEP_WOUND; set 162.940..182.928 on
  :50061, clean words on both sides). 0.08132 x 455 = 37 and 0.03956 x 455 = 18, where
  455 = deepwoundjoin.predicted_max(555): DEEP WOUND CUTS THE 180 HEAL (it is healing,
  not a health gain) and the maximum with it. P2c: the ratio holds on every word with the
  bit clear; under the bit the word is round(0.8 x h) over predicted_max(M), (M, rank)
  being the bearer's own clean fit -- 37 is round(36.8), NOT floor: ARM-TRUNC (the
  server's heal_agent today truncates after the Deep Wound cut, HEAL-INT) predicts 36 and
  reddens. Which rounding (half-up of 0.8 h, or h less round(0.2 h)) is UNDISCRIMINATED.
  Q4 0 of 2 refresh completions carry a word; Q5 0 of 5 Resurrection Signets (type 7, a
  signet); Q6 0 of 13 stopped casts.
  THE TRIAGE'S COUNTS (294 of 368; 5 of 249; 69 of 119) were read per 180 ANNOUNCE over a
  59 s window, so a completion inside two overlapping windows counted twice and a
  completion after a strip counted as a miss; read per episode the corpus holds the
  `p1_n` live completions and `p3_not_live` not-live ones printed below.

Corpus totals are FLOORS (a later capture is confirming evidence, never a red);
per-capture counts are printed. Standard library only; reads the vault through
`vaultpath` (via hexjoin).
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import combatmath       # noqa: E402  (is_spell_type: the server's own spell predicate)
import deepwoundjoin    # noqa: E402  (predicted_max: the Deep Wound maximum, capped at 100)
import hexjoin          # noqa: E402  (census, build_table, _f32, Conn)

AURA_OF_RESTORATION = 180
DRAIN_ENCHANTMENT = 68
ENCH_CLASS_VISUAL = 13      # [6 / 7, b, 13]: the shared 'enchanted' marker (zaishenrun, MEASURED)
EPISODE_S = 60.0            # 180's duration, 60 / 60 at every rank (the record)
EPISODE_TOL = 0.0           # s; the first run's 0.05 called an age-60.031 completion live
BATCH = hexjoin.BATCH       # 0.05 s: the words of a completion's batch
INSTANT = 0.002             # s; "the same instant" for P1's FIRST clause (one segment)
RATIO_TOL = 1e-4            # P2: relative, a f32 ratio of two whole-point heals over one max
WHOLE_TOL = 0.002           # points; f x M whole (f32 carries ~7 digits)
DEEP_WOUND_BIT = 0x20       # effects.STATUS_DEEP_WOUND
DEEP_WOUND_HEAL = 0.8       # WIKI (GWW "Deep Wound"): 20 % less benefit from healing
PROP_HEALTH_MAX = 42        # 0x009F [42, agent, max]: a body's maximum, when declared
DEAD_BIT = hexjoin.DEAD_BIT
OP_INT, OP_INT_TARGET, OP_FLOAT_TARGET = hexjoin.OP_INT, hexjoin.OP_INT_TARGET, hexjoin.OP_FLOAT_TARGET
OP_STATUS, OP_ROUND_END, OP_SIM_TICK = hexjoin.OP_STATUS, hexjoin.OP_ROUND_END, hexjoin.OP_SIM_TICK
ANNOUNCE_PROPS, END_PROPS = hexjoin.ANNOUNCE_PROPS, hexjoin.END_PROPS
PROP_FINISHED, PROP_HEAL = hexjoin.PROP_FINISHED, hexjoin.PROP_HEALTH_GAIN
PROP_REMOVE = hexjoin.PROP_REMOVE_EFFECT
SET_APART = "20260929T100038"   # the capture the triage set apart (its Drain Enchantment strips)


def _int(x, default=-1):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def interp_half_up(lo, hi, rank):
    """The client's scaler (skillread.skill_scale_value's formula), half-up."""
    exact = float(lo) + (float(hi) - float(lo)) * rank / 15.0
    return max(0, int(exact + 0.5))


def heal_points(energy, percent):
    """P2's amount: `percent` of the paid `energy`, whole points, half-up."""
    return int(float(energy) * float(percent) / 100.0 + 0.5)


def cut_points(points, rule="round"):
    """A heal under Deep Wound: 0.8 x points, rounded (P2c) or truncated (ARM-TRUNC)."""
    x = float(points) * DEEP_WOUND_HEAL
    return int(x + 0.5) if rule == "round" else int(x)


def casts_in_order(cc):
    """Every agent's casts in WIRE ORDER: [{agent, skill, target, i, t, end, end_i, end_t}],
    `end` 58 (completed), 59 / 45 / 35 (stopped), "superseded" or None."""
    open_ = {}
    out = []
    for i, t, op, v in cc.seq:
        if op == OP_INT_TARGET and len(v) > 4 and v[1] in ANNOUNCE_PROPS:
            who, sk, tg = v[2], v[4], v[3]
        elif op == OP_INT and len(v) > 3 and v[1] in ANNOUNCE_PROPS:
            who, sk, tg = v[2], v[3], None
        elif op == OP_INT and len(v) > 3 and v[1] in END_PROPS:
            c = open_.get(v[2])
            if c is not None and t > c["t"] + 1e-6:        # never the announce's own instant
                c["end"], c["end_i"], c["end_t"] = v[1], i, t
                del open_[v[2]]
            continue
        else:
            continue
        prev = open_.get(who)
        if prev is not None:
            prev["end"] = "superseded"
        c = {"agent": who, "skill": sk, "target": tg, "i": i, "t": t,
             "end": None, "end_i": None, "end_t": None}
        open_[who] = c
        out.append(c)
    return out


def bearer_events(cc, b):
    """Wire indices for agent `b`: [7, b, 13] markers, death-bit 0x00F1 words, 0x0181
    round ends; [(i, max)] of 0x009F [42, b, max]; [(i, word)] of every 0x00F1 for b."""
    markers, deaths, rounds, maxima, status = [], [], [], [], []
    for i, _t, op, v in cc.seq:
        if op == OP_INT and len(v) > 3 and v[2] == b:
            if v[1] == PROP_REMOVE and _int(v[3]) == ENCH_CLASS_VISUAL:
                markers.append(i)
            elif v[1] == PROP_HEALTH_MAX:
                maxima.append((i, _int(v[3])))
        elif op == OP_STATUS and len(v) > 2 and v[1] == b:
            status.append((i, _int(v[2], 0)))
            if _int(v[2], 0) & DEAD_BIT:
                deaths.append(i)
        elif op == OP_ROUND_END:
            rounds.append(i)
    return markers, deaths, rounds, maxima, status


def _first_after(idx, lo, hi):
    for i in idx:
        if lo < i < hi:
            return i
    return None


def _last_before(pairs, i_lim):
    got = None
    for j, val in pairs:
        if j >= i_lim:
            break
        got = val
    return got


def batch_words(cc, b, t58, i58):
    """The [55, b, b, +f] words within BATCH of the 58 (raw f32): (before, after,
    immediately, first) -- `before` / `after` by wire index; `immediately` the message right
    before the 58 (sim ticks skipped) is a word; `first` no other message naming b
    (v[1..3]) comes ahead of the first word in the same INSTANT."""
    before, after = [], []
    batch = [x for x in cc.span(t58 - BATCH, t58 + BATCH) if x[2] != OP_SIM_TICK]
    for i, _t, op, v in batch:
        if op == OP_FLOAT_TARGET and len(v) > 4 and v[1] == PROP_HEAL and v[2] == b and v[3] == b:
            f = hexjoin._f32(v[4])
            if f <= 0:
                continue
            (before if i < i58 else after).append((i, f))
    prev = [x for x in batch if x[0] < i58]
    immediately = bool(prev) and bool(before) and prev[-1][0] == before[-1][0]
    first = False
    if before:
        w = before[0][0]
        first = not any(b in list(v[1:4]) for i, t, _op, v in batch
                        if i < w and abs(t - t58) <= INSTANT)
    return [f for _i, f in before], [f for _i, f in after], immediately, first


def rows_of(conns):
    """One row per END of a 180 bearer's cast (completed or stopped), every connection
    carrying a 180 completion, with the episode state at that end."""
    out = []
    for cc in conns:
        every = casts_in_order(cc)
        bearers = sorted({c["agent"] for c in every
                          if c["skill"] == AURA_OF_RESTORATION and c["end"] == PROP_FINISHED})
        drains = [c for c in every if c["skill"] == DRAIN_ENCHANTMENT and c["end"] == PROP_FINISHED]
        for b in bearers:
            markers, deaths, rounds, maxima, status = bearer_events(cc, b)
            ep = None           # (start_i, start_t)
            for c in [c for c in every if c["agent"] == b and c["end_i"] is not None]:
                i_end, t_end = c["end_i"], c["end_t"]
                live, why, age = False, "none yet", None
                if ep is not None:
                    age = round(t_end - ep[1], 3)
                    cut = None
                    for name, idx in (("stripped", markers), ("dead", deaths), ("round end", rounds)):
                        j = _first_after(idx, ep[0], i_end)
                        if j is not None and (cut is None or j < cut[1]):
                            cut = (name, j)
                    if cut is not None:
                        why = cut[0]
                    elif t_end - ep[1] > EPISODE_S + EPISODE_TOL:
                        why = "expired"
                    else:
                        live, why = True, "live"
                r = cc.table.get(c["skill"], {})
                ty = _int(r.get("type_code"))
                before, after, imm, first = batch_words(cc, b, t_end, i_end)
                word = _last_before(status, i_end - 0) if status else None
                out.append({"capture": cc.stamp, "port": cc.port, "build": cc.build,
                            "bearer": b, "skill": c["skill"], "type": ty,
                            "spell": combatmath.is_spell_type(ty),
                            "energy": _int(r.get("energy"), 0), "end": c["end"], "t": t_end,
                            "i": i_end, "live": live, "why": why, "age": age,
                            "before": before, "after": after, "immediately": imm, "first": first,
                            "max": _last_before(maxima, i_end),
                            "deep_wound": bool(word is not None and word & DEEP_WOUND_BIT),
                            "drained": [round(d["end_t"], 3) for d in drains if ep is not None
                                        and d["target"] == b and ep[0] < d["end_i"] < i_end]})
                if c["skill"] == AURA_OF_RESTORATION and c["end"] == PROP_FINISHED:
                    ep = (i_end, t_end)
    out.sort(key=lambda r: (r["capture"], r["port"], r["bearer"], r["i"]))
    return out


def census(stamps=None):
    """hexjoin's census cut to the connections that announce a 180."""
    c = hexjoin.census(stamps=stamps)
    keep = [cc for cc in c["conns"]
            if any(sk == AURA_OF_RESTORATION for lst in cc.announces.values()
                   for (_t, sk, _g, _f) in lst)]
    return dict(c, conns=keep)


def bearer_fit(words, lo, hi):
    """Every (M, ranks) -- M a denominator 1..2000 over which every clean word (cost, f) is
    whole AND equal to heal_points(cost, interp(lo, hi, rank)) for each rank in `ranks`
    (0..21). M and the rank TRADE OFF where the words reduce (25 / 480 = 5 / 96: 192 at
    rank 0, ..., 480 at 15), so a bearer has one fit only when its words are irreducible
    over its maximum (23 / 555) -- a declared [42] max must be among the fits."""
    fits = []
    for m in range(1, 2001):
        pts = []
        for cost, f in words:
            x = f * m
            if abs(x - round(x)) > WHOLE_TOL:
                break
            pts.append((cost, int(round(x))))
        else:
            ranks = [k for k in range(0, 22)
                     if all(heal_points(cost, interp_half_up(lo, hi, k)) == p for cost, p in pts)]
            if ranks:
                fits.append((m, ranks))
    return fits


def score(c, arm=None):
    """The numbers the predictions are judged on. `arm` "fixed" / "after58" / "trunc"
    scores that known-bad model in place of the reading (the reader's own refutation)."""
    rows = rows_of(c["conns"])
    comp = [r for r in rows if r["end"] == PROP_FINISHED]
    live = [r for r in comp if r["spell"] and r["skill"] != AURA_OF_RESTORATION and r["live"]]
    if arm == "after58":
        p1c_ok = [r for r in live if len(r["after"]) == 1 and not r["before"]]
    else:
        p1c_ok = [r for r in live if len(r["before"]) == 1 and r["immediately"]]
    p1_ok = [r for r in live if len(r["before"]) == 1 and r["first"]]
    missed = [r for r in live if r not in p1c_ok]
    unexplained = [r for r in missed if not r["drained"]]
    by_cap = collections.defaultdict(lambda: [0, 0])
    for r in live:
        by_cap[r["capture"]][1] += 1
        by_cap[r["capture"]][0] += r in p1c_ok
    s = {"captures": len({cc.stamp for cc in c["conns"]}), "connections": len(c["conns"]),
         "refused": len(c["refused"]), "set_aside": [x[:2] for x in c.get("set_aside", ())],
         "builds": dict(collections.Counter(cc.build for cc in c["conns"])),
         "bearers": len({(r["capture"], r["port"], r["bearer"]) for r in rows}),
         "aura_completions": sum(1 for r in comp if r["skill"] == AURA_OF_RESTORATION),
         "p1_n": len(live), "p1_ok": len(p1_ok), "p1c_ok": len(p1c_ok),
         "p1_mixed": len([r for r in p1c_ok if not r["first"]]),
         "p1_by_capture": {k: tuple(v) for k, v in sorted(by_cap.items())},
         "p1_other_captures": [sum(v[0] for k, v in by_cap.items() if k != SET_APART),
                               sum(v[1] for k, v in by_cap.items() if k != SET_APART)],
         "misses": [(r["capture"], r["port"], r["bearer"], r["skill"], round(r["t"], 3), r["age"],
                     len(r["before"]), len(r["after"]), r["drained"]) for r in missed],
         "unexplained": len(unexplained)}
    # P2 as registered (every word) and P2c (the Deep Wound bit clear), by bearer and cost
    words = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in p1c_ok:
        f = (r["after"] if arm == "after58" else r["before"])[0]
        words[(r["capture"], r["port"], r["bearer"])][(r["energy"], r["deep_wound"])].add(f)

    def ratio_off(clean_only):
        n, off = 0, []
        for key, by in sorted(words.items()):
            costs = {}
            for (e, dw), fs in by.items():
                if clean_only and dw:
                    continue
                costs.setdefault(e, set()).update(fs)
            es = sorted(e for e in costs if e > 0)
            for i, lo in enumerate(es):
                for hi in es[i + 1:]:
                    for flo in costs[lo]:
                        for fhi in costs[hi]:
                            n += 1
                            got = 1.0 if arm == "fixed" else fhi / flo
                            want = float(hi) / float(lo)
                            if abs(got - want) > RATIO_TOL * want:
                                off.append((key, lo, hi, round(flo, 5), round(fhi, 5), round(got, 4)))
        return n, off

    s["p2_pairs"], s["p2_off"] = ratio_off(False)
    s["p2c_pairs"], s["p2c_off"] = ratio_off(True)
    s["p2_per_bearer"] = {f"{k[0]} :{k[1]} b{k[2]}": {f"{e}{' DW' if dw else ''}": sorted(round(x, 5) for x in v)
                                                     for (e, dw), v in sorted(by.items())}
                          for k, by in sorted(words.items())}
    # P2c's amount: each bearer's clean (M, rank) fit, then its Deep Wound words predicted
    fits, dw_rows, declared = {}, [], []
    tables = {}
    for key, by in sorted(words.items()):
        r0 = next(r for r in p1c_ok if (r["capture"], r["port"], r["bearer"]) == key)
        if r0["build"] not in tables:
            tables[r0["build"]] = hexjoin.build_table(r0["build"])[0].get(AURA_OF_RESTORATION, {})
        aura = tables[r0["build"]]
        lo, hi = _int(aura.get("scale0"), 0), _int(aura.get("scale15"), 0)
        clean = [(e, f) for (e, dw), fs in by.items() if not dw for f in fs]
        fit = bearer_fit(clean, lo, hi) if arm != "fixed" else bearer_fit(
            [(e, min(f for _e, f in clean)) for e, _f in clean], lo, hi)
        fits[key] = fit
        for r in p1c_ok:
            if (r["capture"], r["port"], r["bearer"]) != key:
                continue
            if r["max"]:
                declared.append((key, r["max"], [m for m, _k in fit]))
            if not r["deep_wound"]:
                continue
            if len(fit) != 1 or len(fit[0][1]) != 1:
                # a Deep Wound word is predicted only from a UNIQUE clean fit
                dw_rows.append((key, round(r["t"], 3), r["energy"], None, None, None, None, False))
                continue
            m, ranks = fit[0]
            h = heal_points(r["energy"], interp_half_up(lo, hi, ranks[0]))
            pts = cut_points(h, "trunc" if arm == "trunc" else "round")
            mm = deepwoundjoin.predicted_max(m)
            f = r["before"][0]
            dw_rows.append((key, round(r["t"], 3), r["energy"], h, pts, mm, round(f * mm, 3),
                            abs(f * mm - pts) <= WHOLE_TOL))
    s["p2c_fits"] = {f"{k[0]} :{k[1]} b{k[2]}": v for k, v in fits.items()}
    s["p2c_unfit"] = [k for k, v in fits.items() if not v]
    s["p2c_declared"] = sorted(set((k, mx, tuple(ms)) for k, mx, ms in declared))
    s["p2c_declared_off"] = [x for x in s["p2c_declared"] if x[1] not in x[2]]
    s["p2c_dw"] = dw_rows
    # P3: completions under NO live episode carry no word
    gone = [r for r in comp if r["spell"] and r["skill"] != AURA_OF_RESTORATION and not r["live"]
            and r["why"] != "none yet"]
    s["p3_not_live"] = len(gone)
    s["p3_not_live_by_why"] = dict(sorted(collections.Counter(r["why"] for r in gone).items()))
    s["p3_by_capture"] = dict(sorted(collections.Counter(r["capture"] for r in gone).items()))
    s["p3_with_word"] = [(r["capture"], r["port"], r["bearer"], r["skill"], round(r["t"], 3), r["why"])
                         for r in gone if r["before"] or r["after"]]
    s["before_first_aura"] = sum(1 for r in comp if r["why"] == "none yet" and r["spell"])
    s["before_first_aura_with_word"] = sum(1 for r in comp if r["why"] == "none yet"
                                           and (r["before"] or r["after"]))
    s["q4_refresh"] = [(len(r["before"]), len(r["after"])) for r in comp
                       if r["skill"] == AURA_OF_RESTORATION and r["live"]]
    s["q5_nonspell"] = [(r["skill"], r["type"], len(r["before"]), len(r["after"])) for r in comp
                        if not r["spell"] and r["live"]]
    s["q6_stopped"] = [(r["skill"], r["end"], len(r["before"]), len(r["after"])) for r in rows
                       if r["end"] != PROP_FINISHED and r["live"]]
    s["p1"] = bool(live) and len(p1_ok) == len(live)
    s["p1c"] = bool(live) and not unexplained and all(len(r["before"]) <= 1 for r in live)
    s["p2"] = s["p2_pairs"] > 0 and not s["p2_off"]
    s["p2c"] = (s["p2c_pairs"] > 0 and not s["p2c_off"] and not s["p2c_unfit"]
                and not s["p2c_declared_off"] and bool(dw_rows) and all(x[-1] for x in dw_rows))
    s["p3"] = s["p3_not_live"] > 0 and not s["p3_with_word"]
    s["q4"] = bool(s["q4_refresh"]) and all(x == (0, 0) for x in s["q4_refresh"])
    s["q5"] = bool(s["q5_nonspell"]) and all(x[2:] == (0, 0) for x in s["q5_nonspell"])
    s["q6"] = bool(s["q6_stopped"]) and all(x[2:] == (0, 0) for x in s["q6_stopped"])
    return s


def verdicts(s, fx, af, tr):
    """The reading: P1 and P2 FAILED as registered, their corrected readings and P3 hold,
    the post-run questions read as stated, and every known-bad arm reddens."""
    return {"p1_failed_as_registered": not s["p1"], "p1c": s["p1c"],
            "p2_failed_as_registered": not s["p2"], "p2c": s["p2c"], "p3": s["p3"],
            "q4_q5_q6": s["q4"] and s["q5"] and s["q6"],
            "arm_fixed_reddens": not fx["p2c"], "arm_after58_reddens": not af["p1c"],
            "arm_trunc_reddens": not tr["p2c"]}


def _say(text):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


def _v(ok):
    return "PASS" if ok else "FAIL"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true", help="one line per bearer cast end")
    ap.add_argument("--stamp", action="append", default=None, help="only this capture (repeatable)")
    a = ap.parse_args()
    c = census(stamps=a.stamp)
    s = score(c)
    fx, af, tr = score(c, "fixed"), score(c, "after58"), score(c, "trunc")
    v = verdicts(s, fx, af, tr)
    if a.json:
        print(json.dumps({"score": s, "verdicts": v}, indent=1, default=str))
        return 0 if all(v.values()) else 1
    print(f"trigjoin: {s['captures']} captures / {s['connections']} connections announce a 180 "
          f"(census refused {s['refused']}, set aside {s['set_aside']}); builds {s['builds']}; "
          f"bearers {s['bearers']}; 180 completions {s['aura_completions']}")
    if a.rows:
        for r in rows_of(c["conns"]):
            _say(f"   {r['capture']} :{r['port']} b{r['bearer']} {r['t']:9.3f} skill {r['skill']} "
                 f"type {r['type']} e{r['energy']} end {r['end']} {r['why']} age {r['age']} "
                 f"before {[round(x, 5) for x in r['before']]} after {[round(x, 5) for x in r['after']]} "
                 f"imm {r['immediately']} first {r['first']} max {r['max']} dw {r['deep_wound']} "
                 f"drained {r['drained']}")
    print(f"[{_v(s['p1'])}] P1 AS REGISTERED (one word, the FIRST b-word of the instant, ahead of the "
          f"58): {s['p1_ok']} of {s['p1_n']} live spell completions -- FAILS on {s['p1_mixed']} MIXED "
          f"instants")
    print(f"[{_v(s['p1c'])}] P1c one word IMMEDIATELY ahead of [58, b, 0]: {s['p1c_ok']} of {s['p1_n']}; "
          f"per capture (ok, n) {s['p1_by_capture']}; the captures other than {SET_APART} "
          f"{s['p1_other_captures']}; unexplained misses {s['unexplained']}")
    for m in s["misses"]:
        _say(f"   miss (capture, port, bearer, skill, t, age, before, after, Drain onto the bearer "
             f"since the episode opened) {m}")
    print(f"[{_v(s['p2'])}] P2 AS REGISTERED (cost-10 word = 2 x cost-5 word, every word): pairs "
          f"{s['p2_pairs']}, off {len(s['p2_off'])} {s['p2_off'][:3]}")
    print(f"     per bearer, cost -> f32 ('DW' = the bearer's 0x00F1 carries 0x20): {s['p2_per_bearer']}")
    print(f"[{_v(s['p2c'])}] P2c clean ratio pairs {s['p2c_pairs']} off {s['p2c_off']}; (M, ranks) per "
          f"bearer {s['p2c_fits']} (no fit {s['p2c_unfit']}); a declared [42] max vs the fit "
          f"{s['p2c_declared']} (off {s['p2c_declared_off']}); Deep Wound words (bearer, t, cost, h, "
          f"round(0.8 h), predicted_max, f x max, whole) {s['p2c_dw']}")
    print(f"[{_v(s['p3'])}] P3 spell completions under NO live episode {s['p3_not_live']} "
          f"{s['p3_not_live_by_why']} per capture {s['p3_by_capture']}; with a word {s['p3_with_word']}; "
          f"before the bearer's first 180 {s['before_first_aura']} (with a word "
          f"{s['before_first_aura_with_word']})")
    print(f"[{_v(s['q4'])}] Q4 a 180 completing under a live 180 (before, after) {s['q4_refresh']}")
    print(f"[{_v(s['q5'])}] Q5 a non-spell completing under a live 180 (skill, type, before, after) "
          f"{s['q5_nonspell']}")
    print(f"[{_v(s['q6'])}] Q6 a stopped cast under a live 180 (skill, end, before, after) {s['q6_stopped']}")
    print(f"[{_v(v['arm_fixed_reddens'])}] ARM-FIXED (a fixed heal per spell) reddens P2c: off "
          f"{len(fx['p2c_off'])} of {fx['p2c_pairs']}, no fit {len(fx['p2c_unfit'])}")
    print(f"[{_v(v['arm_after58_reddens'])}] ARM-AFTER58 (the word after the 58) reddens P1c: "
          f"{af['p1c_ok']} of {af['p1_n']}")
    print(f"[{_v(v['arm_trunc_reddens'])}] ARM-TRUNC (heal_agent's truncation after the Deep Wound "
          f"cut) reddens P2c: {[x for x in tr['p2c_dw'] if not x[-1]]}")
    ok = all(v.values())
    print(f"trigjoin: {'THE READING HOLDS' if ok else 'THE READING FAILS'} -- {v}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
