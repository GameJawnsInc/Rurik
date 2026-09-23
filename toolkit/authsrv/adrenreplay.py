r"""Replay the client's own adrenaline slots over each live connection and score
retail's accept/refuse answer to every adrenal press against the replayed pool.

    python toolkit/authsrv/adrenreplay.py            # the score, and every disagreement
    python toolkit/authsrv/adrenreplay.py --presses  # every adrenal press, one line each
    python toolkit/authsrv/adrenreplay.py --json

THE PREDICTION, STATED BEFORE THE SCAN (DESKWORK-D5 step 6, 2026-09-22).
animref FINDINGS 19 measured that retail's 43 refused skill presses sit on
exactly four adrenal skills (382 / 384 / 385 / 780) and called the discriminator
"a per-skill charge gate", but left it RECONSTRUCTION because "units since the
last press of this skill" overlapped between accepted and refused presses and
"the right denominator needs a per-bar simulation with cross-drain". skills 38
then read the refusal's reason string off the wire: id 1960 -- the adrenaline
refusal -- on every channel-7 line but one. This module is the per-bar
simulation, with the client's own rules and NO free parameter:

    P1  every press the server REFUSED with reason 1960 finds the replayed slot
        BELOW the skill's cost at the moment of the press;
    P2  every ACCEPTED press of an adrenal skill finds the slot AT OR ABOVE it;
    P3  a refusal whose reason is not 1960, or of a skill with no adrenaline
        cost, is a DIFFERENT gate and is counted apart, never fitted.

A disagreement is printed with its capture, connection, time, skill, slot and
cost. It is a finding about the model, not a row to be fitted away.

WHAT IT FOUND (2026-09-22, the whole live corpus, 86 adrenal presses on the
one tape that presses them, 20260817T231139 -- the census animref 19 made by
hand, 382 22/20, 384 14/13, 385 8/8, to the press):

    P2 HOLDS, 45 of 45: every accepted adrenal press found its slot full.
    P1 SPLITS, 19 of 39: nineteen 1960-refusals found the slot short, and
       TWENTY found it EXACTLY AT COST -- the same value every accepted press
       carries. So the replayed pool cannot be what separates those twenty,
       and they are a SECOND GATE behind the same reason string, named here
       and not fitted: no one-bit change to the arithmetic reaches them
       without breaking accepted presses (--drain-at e3: 6 accepts broken;
       --drain-at both: 12; --drain-units 50: 12; --own-hit-gain none: 17;
       --own-hit-gain self: 12), and neither the time since the observer's
       last completion, activation, spend, gain or refusal, nor a spent skill
       still in flight, nor the press opcode or its target separates them
       from the 44 accepted presses at the same full slot (the `since` and
       `in_flight` columns of --json). The two reason-less 384 declines skills
       38.8 recorded sit at a full slot too (P3, 2 of 2).
    OURS: `pools.AdrenalinePool` IS the client's rules (grant capped, use
       drains the others 25 at the spend, a recharging slot skips), so our
       `refuse_press` agrees with retail on 45 of 45 accepts and 19 of 39
       refusals and would ACCEPT the twenty. What the second gate is has no
       desk answer in this corpus; the row list is where the next question
       starts.

THE RULES ARE THE CLIENT'S, each one an instruction pair in skills 26.2 and
test_adrenwire 9, so this is a replay of what the client itself would hold:

  0x00CF [me, units]          every slot: skip if RECHARGING (0x00E5 .. 0x00E6
                              for that skill), skip if EMPTY, skip if the skill
                              costs 0; else slot = min(cost, slot + units)
  0x00D0 [me]                 every slot -> 0
  0x00D1 [me, skill, copy, u] that slot = u   (sent 0 times in the corpus)
  0x00D2 [me, skill, copy]    that slot -> 0; every OTHER occupied slot loses
                              25, floored at 0 (0x008219xx: cmp esi,0x19 / jbe
                              / add esi,-0x19)
  0x00DA / 0x00D9             the bar, whole or one slot; a slot that changes
                              skill starts at 0 (the client's slot store is
                              keyed on the skill id it holds)

A connection's slots start at 0: adrenaline does not survive a zone. The
first press on a fresh connection is therefore the one most exposed to that
assumption, and a disagreement there would be the place to look first.

WHAT IT READS. Both directions of every live game connection, through
`livewire.decode_conn`, which refuses a connection whose byte accounting does
not close (reported as skipped, never silently). The observer is
`adrenjoin.whose_agent` on the s2c half -- property 41, self-scoped, no
fallback. The refusal's reason is the coded string of the 0x005D immediately
before the 0x00E2 in the same batch, decoded with `clientscan/codedstr`.

READ-ONLY. Standard library only.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
_CLIENTSCAN = os.path.join(os.path.dirname(HERE), "clientscan")
if _CLIENTSCAN not in sys.path:
    sys.path.insert(0, _CLIENTSCAN)

import adrenjoin                                               # noqa: E402
import chatdefs                                                # noqa: E402
import codedstr                                                # noqa: E402
import livewire                                                # noqa: E402

# BOTH presses decode as [skill, copy, target, byte] after the header -- READ
# OFF THE CORPUS, not off the schema's field types: 0x0027's first field is
# typed agent_id there, and a first cut of this module read the skill from the
# second field because of it, found ONE adrenal press in 321 and nearly
# reported a corpus that never presses an adrenal skill. `[32807, 384, 0, 3,
# 0]` is a Gash press at target 3; `handle_skill_press` reads the same slots.
CMSG_ATTACK_SKILL = 0x0027     # (authsrv 10265)
CMSG_USE_SKILL = 0x0046        # (authsrv 10237)
SMSG_SKILL_REFUSED = 0x00E2    # [agent, skill, copy]          (skills 38.1)
SMSG_SKILL_ACTIVATED = 0x00E3  # [agent, skill, copy] -- the cast/swing COMPLETES
SMSG_SKILL_ACTIVATED_BROADCAST = 0x00E4   # [agent, skill, copy] -- E4 fires when the press is ACCEPTED
SMSG_SKILL_RECHARGE = 0x00E5   # [agent, skill, copy, recharge_s]
SMSG_SKILL_RECHARGED = 0x00E6  # [agent, skill, copy]
SMSG_CHAT_CORE = 0x005D        # [coded string]
ADRENALINE_SET = 0x00D1        # [agent, skill, copy, units]
SPEND_STRIKE = 25
REASON_ADRENALINE = chatdefs.REFUSE_NOT_ENOUGH_ADRENALINE      # 1960

# the three rules read off the client's charging and spend workers (26.2, 9)
CLIENT_RULES = ("skip_recharging", "cap", "spend_drain")
DEFAULT_RULES = {"skip_recharging": True, "cap": True, "spend_drain": True,
                 # WHEN the other slots lose their strike. "d2" is the CLIENT's
                 # order (the 0x00D2 handler drains at the message, which
                 # retail sends at cast-begin, 39 of 39 before the naming
                 # property); "e3" drains when that skill's 0x00E3 completion
                 # arrives -- AFTER the landing hit's own 0x00CF in the same
                 # batch. Two arms of one bit, scored against each other.
                 "drain_at": "d2",
                 # how much the OTHER slots lose at a spend (the client: 25)
                 "drain_units": SPEND_STRIKE,
                 # whether the 0x00CF that rides a SPENT skill's own 0x00E3
                 # completion (its landing hit) is booked at all; the client
                 # books every 0x00CF it is sent
                 "own_hit_gain": True}


def _words(v):
    """The u16 words of a decoded string16, whatever the codec handed back."""
    if isinstance(v, str):
        return [ord(c) for c in v]
    return [int(x) for x in v]


def _reason_ids(words):
    """Every string id a coded string carries (markers skipped)."""
    out, i = [], 0
    while i < len(words):
        w = words[i]
        if w < codedstr.BIAS:
            i += 1
            continue
        try:
            sid, used = codedstr.decode_id(words[i:])
        except Exception:                                      # noqa: BLE001
            break
        out.append(sid)
        i += max(1, used)
    return out


class Slots:
    """The client's eight slots, replayed by its own rules."""

    def __init__(self, costs, rules):
        self.costs = costs
        self.rules = rules
        self.skill = [0] * 8
        self.units = [0] * 8
        self.recharging = set()          # skill ids between their E5 and E6
        self.pending_drain = set()       # spent skills whose E3 has not come

    def set_bar(self, skills):
        for i, s in enumerate(list(skills)[:8]):
            self.set_slot(i, int(s))

    def set_slot(self, i, s):
        while len(self.skill) <= i:
            self.skill.append(0)
            self.units.append(0)
        if self.skill[i] != s:
            self.skill[i] = s
            self.units[i] = 0

    def cost(self, s):
        return int(self.costs.get(int(s), 0))

    def slot_of(self, s):
        try:
            return self.skill.index(int(s))
        except ValueError:
            return None

    def gain(self, units, only=None):
        for i, s in enumerate(self.skill):
            if not s or (only is not None and s not in only):
                continue
            c = self.cost(s)
            if c <= 0:
                continue
            if self.rules["skip_recharging"] and s in self.recharging:
                continue
            new = self.units[i] + int(units)
            self.units[i] = min(c, new) if self.rules["cap"] else new

    def clear(self):
        self.units = [0] * len(self.units)

    def set_units(self, s, u):
        i = self.slot_of(s)
        if i is not None:
            self.units[i] = int(u)

    def spend(self, s):
        """0x00D2: the used skill's slot to 0; the others lose a strike now
        (drain_at d2) or when the skill's 0x00E3 arrives (drain_at e3)."""
        i = self.slot_of(s)
        if i is not None:
            self.units[i] = 0
        if self.rules["drain_at"] in ("e3", "both"):
            self.pending_drain.add(int(s))
        if self.rules["drain_at"] in ("d2", "both"):
            self.drain_others(i)

    def drain_others(self, i):
        for j, sk in enumerate(self.skill):
            if not sk or j == i:
                continue
            if self.rules["spend_drain"]:
                self.units[j] = max(0, self.units[j] - int(self.rules["drain_units"]))

    def completed(self, s):
        """0x00E3 for skill s: the deferred drain, if one is owed."""
        if int(s) in self.pending_drain:
            self.pending_drain.discard(int(s))
            self.drain_others(self.slot_of(s))

    def held(self, s):
        i = self.slot_of(s)
        return None if i is None else self.units[i]


def load_connections(root=None):
    """(conns, skipped): every live game connection decoded ONCE, both
    directions, with its observer -- so several rule arms can replay the same
    streams without paying the decode six times. conns is
    [(stamp, conn, merged, me)]."""
    conns, skipped = [], []
    for capdir, gf in livewire.live_connections(root):
        stamp = os.path.basename(capdir)
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        if not ok or not merged:
            skipped.append({"capture": stamp, "connection": conn, "file": gf})
            continue
        s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
        me = adrenjoin.whose_agent(s2c)
        if me is None:
            skipped.append({"capture": stamp, "connection": conn, "file": gf,
                            "why": "no unique self agent"})
            continue
        conns.append((stamp, conn, merged, me))
    return conns, skipped


def replay(rules=None, costs=None, root=None, conns=None):
    """(presses, skipped): one row per ADRENAL press, and the connections refused.

    `conns` from `load_connections` replays a cached decode; without it the
    corpus is decoded here."""
    rules = dict(DEFAULT_RULES, **(rules or {}))
    costs = adrenjoin.adrenal_costs() if costs is None else costs
    if conns is None:
        conns, skipped = load_connections(root)
    else:
        skipped = []
    presses = []
    for stamp, conn, merged, me in conns:
        slots = Slots(costs, rules)
        pending = {}          # skill -> the press row awaiting its answer
        last_core = None      # the most recent 0x005D, for the reason
        spent_open = set()    # skills spent (0x00D2) whose 0x00E3 has not come
        # context for the second-gate census: the observer's last own events
        last = {"e3": None, "e4": None, "spend": None, "gain": None,
                "refuse": None, "press": None}
        # the batches (one timestamp) that carry an own 0x00E3, for own_hit_gain
        e3_at = collections.defaultdict(set)
        for t, d, op, v in merged:
            if d == "s2c" and op == SMSG_SKILL_ACTIVATED and len(v) > 2 and int(v[1]) == me:
                e3_at[t].add(int(v[2]))
        for idx, (t, d, op, v) in enumerate(merged):
            if d == "c2s":
                if op in (CMSG_ATTACK_SKILL, CMSG_USE_SKILL) and len(v) > 3:
                    skill, copy, target = int(v[1]), int(v[2]), int(v[3])
                else:
                    continue
                c = slots.cost(skill)
                held = slots.held(skill)
                row = {"capture": stamp, "connection": conn, "t": t,
                       "index": idx, "opcode": op, "skill": skill,
                       "copy": copy, "target": target, "cost": c,
                       "held": held, "on_bar": held is not None,
                       "recharging": skill in slots.recharging,
                       "predicted": (None if c <= 0 or held is None
                                     else ("refuse" if held < c else "accept")),
                       "answer": None, "reason": None,
                       # the second-gate census: what else was true at the press
                       "in_flight": sorted(spent_open),
                       "since": {k: (None if last[k] is None
                                     else round(t - last[k], 3))
                                 for k in last}}
                if c > 0:
                    presses.append(row)
                pending[skill] = row
                last["press"] = t
                continue
            # s2c
            if op == SMSG_CHAT_CORE and len(v) > 1:
                last_core = (t, _reason_ids(_words(v[1])))
            elif op == adrenjoin.SKILLBAR_UPDATE and len(v) > 2 and int(v[1]) == me:
                slots.set_bar(v[2])
            elif (op == adrenjoin.SKILLBAR_UPDATE_SKILL and len(v) > 3
                  and int(v[1]) == me):
                slots.set_slot(int(v[2]), int(v[3]))
            elif op == adrenjoin.ADRENALINE_GAIN and int(v[1]) == me:
                # a gain in the same batch as a SPENT skill's own completion is
                # that skill's landing hit; `own_hit_gain` False leaves it
                # unbooked, "self" books it to the landing skill's slot alone
                landing = e3_at.get(t, set()) & spent_open
                if rules["own_hit_gain"] is True or not landing:
                    slots.gain(int(v[2]))
                elif rules["own_hit_gain"] == "self":
                    slots.gain(int(v[2]), only=landing)
                last["gain"] = t
            elif op == adrenjoin.ADRENALINE_CLEAR and int(v[1]) == me:
                slots.clear()
            elif op == ADRENALINE_SET and len(v) > 4 and int(v[1]) == me:
                slots.set_units(int(v[2]), int(v[4]))
            elif op == adrenjoin.ADRENALINE_SPEND and len(v) > 2 and int(v[1]) == me:
                slots.spend(int(v[2]))
                spent_open.add(int(v[2]))
                last["spend"] = t
            elif op == SMSG_SKILL_ACTIVATED and len(v) > 2 and int(v[1]) == me:
                slots.completed(int(v[2]))
                spent_open.discard(int(v[2]))
                last["e3"] = t
            elif op == SMSG_SKILL_RECHARGE and len(v) > 4 and int(v[1]) == me:
                if int(v[4]) > 0:
                    slots.recharging.add(int(v[2]))
            elif op == SMSG_SKILL_RECHARGED and len(v) > 2 and int(v[1]) == me:
                slots.recharging.discard(int(v[2]))
            elif op == SMSG_SKILL_REFUSED and len(v) > 2 and int(v[1]) == me:
                row = pending.pop(int(v[2]), None)
                if row is not None and row["answer"] is None:
                    row["answer"] = "refuse"
                    if last_core is not None and last_core[0] == t:
                        row["reason"] = last_core[1]
                last["refuse"] = t
            elif (op == SMSG_SKILL_ACTIVATED_BROADCAST and len(v) > 2
                  and int(v[1]) == me):
                row = pending.pop(int(v[2]), None)
                if row is not None and row["answer"] is None:
                    row["answer"] = "accept"
                last["e4"] = t
    return presses, skipped


def score(presses):
    """The tallies P1-P3 read off, plus every disagreement by name."""
    out = collections.Counter()
    disagree = []
    for r in presses:
        adren_reason = bool(r["reason"]) and REASON_ADRENALINE in r["reason"]
        if r["answer"] is None:
            out["unanswered"] += 1
            continue
        if r["answer"] == "refuse" and not adren_reason:
            out["refused_other_reason"] += 1           # P3: a different gate
            continue
        if r["predicted"] is None:
            out["off_bar"] += 1
            continue
        key = f"{r['answer']}_{'agree' if r['predicted'] == r['answer'] else 'DISAGREE'}"
        out[key] += 1
        if r["predicted"] != r["answer"]:
            disagree.append(r)
    return out, disagree


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--presses", action="store_true",
                    help="print every adrenal press with its replayed slot")
    ap.add_argument("--json", action="store_true")
    for k in CLIENT_RULES:
        ap.add_argument(f"--no-{k.replace('_', '-')}", action="store_true",
                        help=f"replay WITHOUT the client's {k} rule (a known-bad arm)")
    ap.add_argument("--drain-at", choices=("d2", "e3", "both"), default="d2",
                    help="when the OTHER slots lose a strike: at the 0x00D2 (the "
                         "client's handler), at the skill's 0x00E3 completion, or "
                         "BOTH (one strike each time)")
    ap.add_argument("--drain-units", type=int, default=SPEND_STRIKE,
                    help="how much the OTHER slots lose at a spend (the client: 25)")
    ap.add_argument("--own-hit-gain", choices=("all", "none", "self"), default="all",
                    help="the 0x00CF that rides a spent skill's own 0x00E3: booked "
                         "to every slot (the client), to none, or to the landing "
                         "skill's slot only")
    args = ap.parse_args()
    rules = {k: not getattr(args, "no_" + k) for k in CLIENT_RULES}
    rules["drain_at"] = args.drain_at
    rules["drain_units"] = args.drain_units
    rules["own_hit_gain"] = {"all": True, "none": False,
                             "self": "self"}[args.own_hit_gain]

    presses, skipped = replay(rules)
    tally, disagree = score(presses)
    if args.json:
        print(json.dumps({"rules": rules, "tally": dict(tally),
                          "disagree": disagree, "presses": presses,
                          "skipped": skipped}, indent=2))
        return 0
    print("PREDICTION (stated first): P1 every 1960-refusal has slot < cost; "
          "P2 every accepted adrenal press has slot >= cost; P3 other reasons "
          "are a different gate and are counted apart.")
    print(f"rules {rules}")
    print(f"{len(presses)} adrenal presses over "
          f"{len({(r['capture'], r['connection']) for r in presses})} connections; "
          f"{len(skipped)} connection(s) skipped")
    for s in skipped:
        print(f"   skipped {s}")
    print()
    for k in ("refuse_agree", "refuse_DISAGREE", "accept_agree", "accept_DISAGREE",
              "refused_other_reason", "off_bar", "unanswered"):
        print(f"   {k:22} {tally.get(k, 0):4}")
    by_skill = collections.Counter((r["skill"], r["answer"]) for r in presses
                                   if r["answer"])
    print(f"   by skill (skill, answer): {dict(sorted(by_skill.items()))}")
    others = [r for r in presses if r["answer"] == "refuse"
              and not (r["reason"] and REASON_ADRENALINE in r["reason"])]
    if others:
        print("   refusals with another (or no) reason id:")
        for r in others:
            print(f"      {r['capture']} {r['connection']} t={r['t']:.3f} skill "
                  f"{r['skill']} held {r['held']} cost {r['cost']} recharging "
                  f"{r['recharging']} reason {r['reason']}")
    print()
    if disagree:
        print(f"{len(disagree)} DISAGREEMENT(S) -- named, not fitted:")
        for r in disagree:
            print(f"   {r['capture']} {r['connection']} t={r['t']:.3f} skill "
                  f"{r['skill']} predicted {r['predicted']} answer {r['answer']} "
                  f"held {r['held']} cost {r['cost']} recharging {r['recharging']}")
    else:
        print("0 disagreements")
    if args.presses:
        print()
        for r in presses:
            print(f"   {r['capture']} {r['connection']} t={r['t']:9.3f} "
                  f"{hex(r['opcode'])} skill {r['skill']:4} held {str(r['held']):>4} "
                  f"cost {r['cost']:4} -> {r['predicted']!s:7} answer {r['answer']!s:7} "
                  f"reason {r['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
