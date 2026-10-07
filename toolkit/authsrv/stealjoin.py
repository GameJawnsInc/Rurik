r"""Life steal on retail's wire: the observer's OWN steals, and a hostile's AT the observer.

    python toolkit/authsrv/stealjoin.py            # every live capture

CHAN55, studies/skills/FINDINGS.md section 68.3 (SKILLS-CH3). A life steal moves ONE
amount: the target loses it, the caster gains it. On the wire both halves ride property
55 of 0x00A3 [prop, target, cause, f32] -- the loss NEGATIVE, the gain POSITIVE and
self-directed -- and this tool reads the two shapes the corpus holds.

OWN. For every 0x00E5 [observer, S, ...] (the observer's own skill completing), its
batch (healjoin.batches) is searched for the first [55, obs, obs, +h] and the first
[55, X, obs, -d] (X != obs) after it. A row records both fractions, each multiplied by
its agent's LAST property-42 maximum on the wire before the word (None when the wire
never declared one), whether a [10] or a 16 / 17 from the observer sits between the E5
and the damage word, and what lies between the heal and the word.

HOSTILE. For every 0x009F [10, observer, S] followed in its batch by [55, obs, C, -d]
(the named word, spellhitjoin.named_words' rule), the batch BEFORE the [10] is searched
for the caster's own [55, C, C, +h] and the observer's gain 0x00CF [obs, n]. A row is
STEAL-SHAPED when the caster's heal is there.

Every number printed is an id, a property, an index, a fraction or a point count --
no template text, no decoded content list. The gapped connection the capture's own
manifest declares (20260928T103123 :65009) is set aside by name, as every iterator does.
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import healjoin         # noqa: E402
import livewire         # noqa: E402
import spellhitjoin     # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_INT = 0x009F           # [prop, agent, value]
OP_FLOAT_TARGET = 0x00A3  # [prop, target, cause, f32]
OP_RECHARGE = 0x00E5      # [agent, skill, copy, seconds]: the skill completed
OP_GAIN = 0x00CF          # [agent, units]
PROP_SKILL_DAMAGE = 10
PROP_MAX = 42
PROP_55 = 55
PROP_DAMAGE = (16, 17)


def f32(dword):
    return struct.unpack("<f", struct.pack("<I", int(dword) & 0xFFFFFFFF))[0]


def _maxima(seq):
    """[(index, agent, max)] of every property-42 declaration, in wire order."""
    return [(i, v[2], v[3]) for i, _t, op, v in seq
            if op == OP_INT and len(v) > 3 and v[1] == PROP_MAX]


def _max_before(maxima, agent, index):
    best = None
    for i, a, m in maxima:
        if i >= index:
            break
        if a == agent:
            best = m
    return best


def own_steals(seq, obs, heal_first=True):
    """[row] for every observer E5 whose batch holds the heal-then-damage pair; and the
    Counter of every observer E5 by skill (so a caller can see completions WITHOUT it).
    `heal_first=False` is the KNOWN-BAD reader: it wants the damage word FIRST and the
    heal after it, and finding none on the tape is what makes the order a measurement."""
    maxima = _maxima(seq)
    rows, completions = [], collections.Counter()
    for batch in healjoin.batches(seq):
        for k, (i, t, op, v) in enumerate(batch):
            if op != OP_RECHARGE or len(v) < 3 or v[1] != obs:
                continue
            completions[v[2]] += 1
            rest = batch[k + 1:]

            def is_heal(o, w):
                return (o == OP_FLOAT_TARGET and w[1] == PROP_55 and w[2] == obs
                        and w[3] == obs and not (w[4] & 0x80000000))

            def is_word(o, w):
                return (o == OP_FLOAT_TARGET and w[1] == PROP_55 and w[3] == obs
                        and w[2] != obs and (w[4] & 0x80000000))
            first, second = (is_heal, is_word) if heal_first else (is_word, is_heal)
            a = next(((j, w) for j, (_i, _t, o, w) in enumerate(rest) if first(o, w)), None)
            if a is None:
                continue
            b = next(((j, w) for j, (_i, _t, o, w) in enumerate(rest)
                      if j > a[0] and second(o, w)), None)
            if b is None:
                continue
            heal, word = (a, b) if heal_first else (b, a)
            upto = rest[:max(heal[0], word[0])]
            hi, wi = rest[heal[0]][0], rest[word[0]][0]
            hf, df = f32(heal[1][4]), f32(word[1][4])
            hmax, dmax = _max_before(maxima, obs, hi), _max_before(maxima, word[1][2], wi)
            rows.append({
                "skill": v[2], "t": t, "foe": word[1][2], "heal_frac": hf, "dmg_frac": df,
                "heal_pts": None if hmax is None else round(hf * hmax, 3),
                "dmg_pts": None if dmax is None else round(-df * dmax, 3),
                "named": [w[3] for _i, _t, o, w in upto
                          if o == OP_INT and len(w) > 3 and w[1] == PROP_SKILL_DAMAGE],
                "damage_16": [w[1] for _i, _t, o, w in upto
                              if o == OP_FLOAT_TARGET and w[1] in PROP_DAMAGE and w[3] == obs],
                "between": [(o, w[1]) for _i, _t, o, w
                            in rest[min(heal[0], word[0]) + 1:max(heal[0], word[0])]]})
    return rows, completions


def hostile_steals(seq, obs):
    """[row] for every [10, obs, S] followed in its batch by [55, obs, C, -d]."""
    rows = []
    for batch in healjoin.batches(seq):
        for k, (i, t, op, v) in enumerate(batch):
            if op != OP_INT or len(v) < 4 or v[1] != PROP_SKILL_DAMAGE or v[2] != obs:
                continue
            nxt = next(((j, w) for j, (_i, _t, o, w) in enumerate(batch[k + 1:], k + 1)
                        if o == OP_FLOAT_TARGET), None)
            if nxt is None or nxt[1][1] != PROP_55 or nxt[1][2] != obs \
                    or not (nxt[1][4] & 0x80000000):
                continue
            cause = nxt[1][3]
            before = batch[:k]
            heal = [j for j, (_i, _t, o, w) in enumerate(before)
                    if o == OP_FLOAT_TARGET and w[1] == PROP_55 and w[2] == cause
                    and w[3] == cause and not (w[4] & 0x80000000)]
            gain = [j for j, (_i, _t, o, w) in enumerate(before)
                    if o == OP_GAIN and len(w) > 2 and w[1] == obs]
            rows.append({
                "skill": v[3], "t": t, "cause": cause, "dmg_frac": f32(nxt[1][4]),
                "heal_frac": f32(before[heal[-1]][3][4]) if heal else None,
                "steal": bool(heal),
                # the order inside the batch: gain < heal < [10] < word, by index
                "order": (gain[-1] if gain else None, heal[-1] if heal else None, k, nxt[0])})
    return rows


def census(stamps=None, codec=None):
    """{"own", "completions", "hostile", "set_aside", "word_first"}: own_steals and
    hostile_steals over every live connection that frames whole, each row stamped with
    its capture and connection; "word_first" is the known-bad reader's rows
    (own_steals(heal_first=False)). A connection the capture's own manifest declares
    gapped is set aside by name; any other refusal RAISES (a refused connection is not
    a skipped one)."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live", why="stealjoin reads live captures")
    own, hostile, set_aside, word_first = [], [], [], []
    completions = collections.Counter()
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap) or (stamps is not None and stamp not in stamps):
            continue
        declared = livewire.declared_gaps(cap)
        for ch in tape.channel_files(cap):
            if ch["connection"] in declared:
                set_aside.append((stamp, ch["connection"]))
                continue
            seq = deepwoundjoin.sequence(cap, ch["connection"], codec)
            obs = spellhitjoin.player_of(seq, spellhitjoin.c2s_of(cap, ch["file"]))
            if obs is None:
                continue
            rows, comp = own_steals(seq, obs)
            completions.update(comp)
            for r in rows:
                r.update(capture=stamp, connection=ch["connection"])
                own.append(r)
            for r in hostile_steals(seq, obs):
                r.update(capture=stamp, connection=ch["connection"])
                hostile.append(r)
            word_first.extend(own_steals(seq, obs, heal_first=False)[0])
    return {"own": own, "completions": completions, "hostile": hostile,
            "set_aside": set_aside, "word_first": word_first}


def main():
    got = census()
    own, completions, hostile = got["own"], got["completions"], got["hostile"]
    print(f"set aside by manifest: {got['set_aside']}")
    print(f"known-bad reader (the word FIRST, then the heal): {len(got['word_first'])} rows")
    by_skill = collections.Counter(r["skill"] for r in own)
    print(f"OWN steal-shaped completions by skill: {dict(by_skill)}; "
          f"completions of those skills: { {s: completions[s] for s in by_skill} }")
    for r in own:
        print(f"  {r['capture']} {r['connection'].split('->')[0]} t={r['t']:.3f} skill {r['skill']}"
              f" foe {r['foe']}: +{r['heal_frac']:.5f} ({r['heal_pts']}) then "
              f"{r['dmg_frac']:.5f} ({r['dmg_pts']}); [10] {r['named']}, 16/17 {r['damage_16']},"
              f" between {r['between']}")
    steals = [r for r in hostile if r["steal"]]
    print(f"HOSTILE named 55 words at the observer: {len(hostile)}; steal-shaped "
          f"{len(steals)} {dict(collections.Counter(r['skill'] for r in steals))}")
    for r in steals:
        print(f"  {r['capture']} {r['connection'].split('->')[0]} t={r['t']:.3f} skill "
              f"{r['skill']} cause {r['cause']}: heal +{r['heal_frac']:.5f}, word "
              f"{r['dmg_frac']:.5f}, order (gain, heal, [10], word) = {r['order']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
