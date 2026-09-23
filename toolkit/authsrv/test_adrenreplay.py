"""test_adrenreplay -- the adrenaline slots replayed by the client's own rules, scored
press by press against retail's accept / refuse (DESKWORK-D5 step 6, 2026-09-22).

WHAT IT IS REALLY CHECKING. animref 19 measured that retail's refused skill presses
sit on four adrenal skills and called the discriminator a charge gate, but left it
RECONSTRUCTION for want of "a per-bar simulation with cross-drain". skills 38 read the
reason string off the wire (1960, the adrenaline refusal). `adrenreplay.py` is the
simulation, with the client's rules from skills 26.2 and test_adrenwire 9 and no free
parameter, and this file pins what it found:

  * the press census animref 19 made by hand is reproduced to the press;
  * P2 holds -- every ACCEPTED adrenal press finds its replayed slot at cost;
  * P1 splits -- 19 of the 39 reason-1960 refusals find the slot short, and 20 find
    it EXACTLY AT COST, which is a second gate behind the same reason string and is
    pinned as such (every disagreement at held == cost), not fitted away;
  * the five one-bit rivals to the arithmetic each break accepted presses, so the
    scoring can fail for the reason it claims (the known-bad arms);
  * OUR book -- `pools.AdrenalinePool`, the thing `refuse_press` reads -- holds the
    same number as the client-rule replay at every press, so "ours would accept
    those twenty" is measured rather than argued.

Section 1 is bare-machine (the slot arithmetic alone). Sections 2-3 need
`vault/captures/live/` and are declared as a skip without it; the corpus is decoded
ONCE and every arm replays the cached streams.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import adrenreplay as ar                                       # noqa: E402
import pools                                                   # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-22: 18 checks (the fixture-less section 1
# alone is 9; the corpus sections add 9). The floor is the bare-machine core,
# so a machine without the vault still measures the arithmetic.
LEDGER = checks.Ledger("the adrenaline replay", floor=9)
check = checks.adopt(LEDGER)

PVP_TAPE = "20260817T231139"
# animref 19's hand census of the adrenal presses on that tape, (skill, answer)
# -> count. A tape does not grow, so these are EXACT.
PVP_CENSUS = {(382, "accept"): 22, (382, "refuse"): 20, (384, "accept"): 14,
              (384, "refuse"): 13, (385, "accept"): 8, (385, "refuse"): 8}
PVP_REFUSE_SHORT = 19       # 1960-refusals the replayed slot explains
PVP_REFUSE_FULL = 20        # 1960-refusals at a FULL replayed slot: the second gate
PVP_OTHER_REASON = 2        # skills 38.8's two reason-less 384 declines
RIVALS = ({"drain_at": "e3"}, {"drain_at": "both"}, {"drain_units": 50},
          {"own_hit_gain": False}, {"own_hit_gain": "self"})


def section_slots():
    print("\n1. the slot arithmetic is the client's, rule by rule")
    costs = {382: 75, 384: 125, 385: 200, 364: 0, 1: 0}
    s = ar.Slots(costs, dict(ar.DEFAULT_RULES))
    s.set_bar([382, 384, 385, 364, 1, 0, 0, 2])
    for _ in range(4):
        s.gain(25)
    check(s.held(382) == 75 and s.held(384) == 100 and s.held(385) == 100,
          "four strikes: 382 CAPS at its 75, the others sit at 100",
          f"{list(zip(s.skill, s.units))} -- min(cost, slot + units), 26.2 rule 5")
    check(s.held(364) is not None and s.units[3] == 0 and s.held(1) == 0,
          "a zero-cost skill on the bar takes nothing (rule 4)",
          f"364 {s.units[3]}, 1 {s.units[4]}")
    s.recharging.add(384)
    s.gain(25)
    check(s.held(384) == 100 and s.held(385) == 125,
          "a RECHARGING slot skips the gain (rule 2) while its neighbour takes it",
          f"384 {s.held(384)}, 385 {s.held(385)}")
    s.recharging.discard(384)
    s.spend(382)
    check(s.held(382) == 0 and s.held(384) == 75 and s.held(385) == 100,
          "a spend zeroes the used skill and drains every OTHER occupied slot 25",
          f"{list(zip(s.skill, s.units))[:3]} -- test_adrenwire 9's cmp esi,0x19")
    s.units[1] = 10
    s.spend(385)
    check(s.held(384) == 0,
          "and the drain floors at zero", f"384 {s.held(384)} (was 10)")
    s.gain(25)
    s.clear()
    check(sum(s.units) == 0, "0x00D0 zeroes every slot", f"{s.units}")
    s.gain(50)
    s.set_slot(0, 348)
    check(s.skill[0] == 348 and s.units[0] == 0 and s.held(384) == 50,
          "a slot that changes skill starts at 0; the others keep theirs",
          f"{list(zip(s.skill, s.units))[:2]}")
    # THE KNOWN-BAD ARMS: the rules are switches, so a scan that reported the
    # client's numbers with a rule silently off would be caught here.
    bad = ar.Slots(costs, dict(ar.DEFAULT_RULES, cap=False))
    bad.set_bar([382, 384])
    for _ in range(4):
        bad.gain(25)
    nodrain = ar.Slots(costs, dict(ar.DEFAULT_RULES, spend_drain=False))
    nodrain.set_bar([382, 384])
    nodrain.gain(50)
    nodrain.spend(382)
    check(bad.held(382) == 100 and nodrain.held(384) == 50,
          "KNOWN-BAD ARMS: cap off overfills 382 to 100; drain off leaves 384 at 50",
          f"cap off {bad.held(382)}, drain off {nodrain.held(384)}")
    late = ar.Slots(costs, dict(ar.DEFAULT_RULES, drain_at="e3"))
    late.set_bar([382, 384])
    late.gain(50)
    late.spend(382)
    before = late.held(384)
    late.completed(382)
    check(before == 50 and late.held(384) == 25,
          "drain_at e3 defers the others' strike to the skill's completion",
          f"384 {before} at the spend, {late.held(384)} at the 0x00E3")


def section_corpus():
    print("\n2. retail's presses against the replayed slots")
    try:
        vaultpath.require_dir("captures", "live", why="the adrenaline replay")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        # require_dir raises SystemExit on a bare machine (test_srclint's rule)
        LEDGER.skip("2. retail's presses", str(exc))
        LEDGER.skip("3. our book against the client's rules", str(exc))
        return
    conns, skipped = ar.load_connections()
    presses, _ = ar.replay(conns=conns)
    tally, disagree = ar.score(presses)
    pvp = [r for r in presses if r["capture"] == PVP_TAPE and r["answer"]]
    census = {}
    for r in pvp:
        if r["skill"] in (382, 384, 385):
            census[(r["skill"], r["answer"])] = census.get((r["skill"], r["answer"]), 0) + 1
    check(len(presses) >= 86 and census == PVP_CENSUS,
          f"{len(presses)} adrenal presses; the PvP tape's census is animref 19's, "
          f"to the press",
          f"{dict(sorted(census.items()))} against {dict(sorted(PVP_CENSUS.items()))}"
          f" -- 382 22/20, 384 14/13, 385 8/8 (accepted/refused), read by hand on "
          f"2026-08-31 from the same tape; a tape does not grow, so EXACT")
    not_auth = [s for s in skipped
                if not str(s.get("connection", "")).rsplit(":", 1)[-1] == "6112"]
    check(not not_auth,
          f"the {len(skipped)} skipped connection(s) are 6112 auth channels",
          f"offenders {not_auth}")
    check(tally.get("accept_DISAGREE", 0) == 0 and tally.get("accept_agree", 0) >= 45,
          f"P2: every accepted adrenal press found its slot full "
          f"({tally.get('accept_agree', 0)} of {tally.get('accept_agree', 0)})",
          f"{dict(tally)} -- an accepted press at a short slot would refute the "
          f"replay's arithmetic outright")
    pvp_ref = [r for r in pvp if r["answer"] == "refuse"
               and r["reason"] and ar.REASON_ADRENALINE in r["reason"]]
    short = [r for r in pvp_ref if r["held"] < r["cost"]]
    full = [r for r in pvp_ref if r["held"] >= r["cost"]]
    check(len(short) == PVP_REFUSE_SHORT and len(full) == PVP_REFUSE_FULL,
          f"P1 SPLITS: {len(short)} reason-1960 refusals at a short slot, "
          f"{len(full)} at a FULL one",
          f"39 refusals carry 1960 on the tape; the replayed slot explains "
          f"{len(short)} and the other {len(full)} arrive with the slot at cost -- "
          f"EXACT, because the tape does not grow and a model change moves both")
    check(full and all(r["held"] == r["cost"] for r in full)
          and all(r["capture"] == PVP_TAPE for r in disagree)
          and len(disagree) == PVP_REFUSE_FULL,
          "and every one of them holds EXACTLY the cost -- the second gate's shape",
          f"{sorted({(r['skill'], r['held'], r['cost']) for r in full})} -- the same "
          f"value every accepted press carries, so the pool is not what separates "
          f"them; named as a second gate behind reason 1960, not fitted")
    others = [r for r in pvp if r["answer"] == "refuse"
              and not (r["reason"] and ar.REASON_ADRENALINE in r["reason"])]
    check(len(others) == PVP_OTHER_REASON
          and all(r["skill"] == 384 and r["held"] == r["cost"] for r in others),
          f"P3: {len(others)} refusals carry no reason -- skills 38.8's two silent "
          f"384 declines -- and both sit at a full slot too",
          f"{[(r['t'], r['skill'], r['held'], r['cost']) for r in others]}")
    # THE RIVALS, each a one-bit change to the arithmetic that fits the two
    # windows a reader traces by hand -- and each breaks accepted presses.
    broken = {}
    for rival in RIVALS:
        p2, _ = ar.replay(rules=rival, conns=conns)
        t2, _d = ar.score(p2)
        broken[str(rival)] = t2.get("accept_DISAGREE", 0)
    check(all(n > 0 for n in broken.values()) and len(broken) == len(RIVALS),
          f"KNOWN-BAD ARMS: all {len(RIVALS)} rivals break accepted presses",
          f"{broken} -- drain at the completion, at both, two strikes, the landing "
          f"gain unbooked or booked to the landing skill alone: each explains more "
          f"refusals and refutes itself on the accepts, which is why the client's "
          f"rules stay the model and the twenty stay a second gate")
    return conns


def section_ours(conns):
    print("\n3. our book against the client's rules, press by press")
    if conns is None:
        return
    # `pools.AdrenalinePool` fed the same events as the replay must hold the same
    # number at every press: it is what `refuse_press`'s gate reads, so this is
    # the measurement behind "ours would accept those twenty".
    costs = {sid: int(c) for sid, c in ar.adrenjoin.adrenal_costs().items()}
    agree = disagree = 0
    disagree_bad = 0
    for stamp, conn, merged, me in conns:
        if stamp != PVP_TAPE:
            continue
        for drain, bucket in ((25, "good"), (50, "bad")):
            slots = ar.Slots(costs, dict(ar.DEFAULT_RULES, drain_units=drain))
            pool = None
            bar = None
            for t, d, op, v in merged:
                if d == "c2s":
                    if op in (ar.CMSG_ATTACK_SKILL, ar.CMSG_USE_SKILL) and len(v) > 3:
                        sk = int(v[1])
                        if costs.get(sk, 0) > 0 and pool is not None:
                            same = pool.units.get(sk) == slots.held(sk)
                            if bucket == "good":
                                agree += same
                                disagree += not same
                            else:
                                disagree_bad += not same
                    continue
                # the opcode FIRST: 0x001D's v[1] is a bitmap list, and a
                # blanket int(v[1]) on every s2c message raised on it
                if op not in (ar.adrenjoin.SKILLBAR_UPDATE, ar.adrenjoin.ADRENALINE_GAIN,
                              ar.adrenjoin.ADRENALINE_CLEAR, ar.adrenjoin.ADRENALINE_SPEND,
                              ar.SMSG_SKILL_RECHARGE, ar.SMSG_SKILL_RECHARGED):
                    continue
                if len(v) < 2 or int(v[1]) != me:
                    continue
                if op == ar.adrenjoin.SKILLBAR_UPDATE and len(v) > 2:
                    bar = [int(x) for x in v[2]]
                    slots.set_bar(bar)
                    pool = pools.AdrenalinePool({s: costs.get(s, 0) for s in bar if s},
                                                recharging=lambda: set(slots.recharging))
                elif pool is None:
                    continue
                elif op == ar.adrenjoin.ADRENALINE_GAIN:
                    slots.gain(int(v[2]))
                    pool.grant(int(v[2]), t)
                elif op == ar.adrenjoin.ADRENALINE_CLEAR:
                    slots.clear()
                    pool.clear()
                elif op == ar.adrenjoin.ADRENALINE_SPEND and len(v) > 2:
                    slots.spend(int(v[2]))
                    pool.use(int(v[2]))
                elif op == ar.SMSG_SKILL_RECHARGE and len(v) > 4 and int(v[4]) > 0:
                    slots.recharging.add(int(v[2]))
                elif op == ar.SMSG_SKILL_RECHARGED and len(v) > 2:
                    slots.recharging.discard(int(v[2]))
    # 85, not 86: the corpus's 86th adrenal press (348, accepted) is on
    # 20260821T205552, the spend-clock capture, not on the PvP tape.
    check(agree >= 85 and disagree == 0,
          f"pools.AdrenalinePool holds the replay's number at all {agree} adrenal "
          f"presses on the tape",
          f"{disagree} disagreements. So `refuse_press` (charged = units >= cost) "
          f"agrees with retail on every accepted press and on 19 of the 39 "
          f"refusals, and would ACCEPT the twenty at a full slot -- measured on "
          f"the book itself, not inferred from its docstring")
    check(disagree_bad > 0,
          "KNOWN-BAD ARM: a two-strike replay parts from the book",
          f"{disagree_bad} presses differ -- the comparison can fail")


def main():
    section_slots()
    conns = section_corpus()
    section_ours(conns)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
