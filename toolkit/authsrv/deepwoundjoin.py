r"""Deep Wound on retail's wire: the 482 apply joined to the max-health message.

    python toolkit/authsrv/deepwoundjoin.py            # every live capture
    python toolkit/authsrv/deepwoundjoin.py --json

THE PREDICTION, stated before the numbers (studies/isle/FINDINGS.md 8.2 read
the one capture by eye; this mechanises it so a test can pin it):

  P1  every `0x0042` carrying skill 482 is joined by an int property 42
      (PROP_HEALTH_MAX, on 0x009F) addressed to the SAME agent, in the same
      batch -- within 50 ms, the corpus's own batch shoulder;
  P2  the joined value is the agent's previous maximum x 0.8, exactly, and
      the reduction is capped at 100 (WIKI, GWW "Deep Wound" sec. Game
      mechanics, rev. 2026-03-02: "never reduce your maximum health by more
      than 100 health, even if your maximum health was more than 500" --
      the cap does NOT bind on the corpus's 480-health witness, so P2's cap
      clause is carried, not tested, until a witness above 500 exists);
  P3  every `0x0044` closing a 482 episode is joined the same way by a
      property 42 restoring the previous maximum;
  P4  no OTHER property 42 moves inside a 482 episode's life (the other
      conditions live in the same captures are the control -- 2077 Cracked
      Armor sat live for 28.5 s beside an unmoved 480).

WHAT IS READ, NOT ASSUMED: the ORDER of the two messages inside the batch.
isle 8.2 says "on the same millisecond" and does not say which comes first;
the server's sender has to pick one, so this prints the wire's.

Standard library only. Reads the vault through `vaultpath` (worktree-safe);
refuses a tape that does not frame to its last byte, like `bufflog`.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import bufflog      # noqa: E402
import tape         # noqa: E402
import vaultpath    # noqa: E402

DEEP_WOUND = 482
BATCH = 0.050          # seconds; the corpus's batch shoulder
FRACTION = 0.8         # WIKI: maximum health reduced by 20%
CAP = 100              # WIKI: never by more than 100 health
OP_INT = bufflog.OP_INT_NOTARGET
OP_APPLY = bufflog.OP_EFFECT_APPLY
OP_REMOVE = bufflog.OP_EFFECT_REMOVE
PROP_HEALTH_MAX = bufflog.PROP_HEALTH_MAX


def predicted_max(previous):
    """The maximum under Deep Wound, from the one before it. WIKI rule."""
    return previous - min(CAP, round(previous * (1.0 - FRACTION)))


def sequence(capture_dir, connection, codec):
    """[(index, t, opcode, values)] for one connection, framed whole."""
    info, events = tape.load_tape(capture_dir, connection)
    t_base = info.get("t0") or 0.0
    events = [(round(t + t_base, 6), p) for t, p in events]
    msgs, (consumed, total, err) = tape.decode_all(events, codec, "GAME_SMSG", 0)
    if err is not None or consumed != total:
        raise bufflog.BuffLogError(
            f"{capture_dir} {connection}: framed {consumed}/{total} ({err})")
    return [(i, t, op, list(v)) for i, (t, op, v) in enumerate(msgs)]


def join(seq):
    """Every 482 apply and close in one sequence, joined to property 42.

    Returns {"applies": [...], "closes": [...], "stray": [...]} where each
    apply/close row names the joined prop-42 (or None), its batch offset in
    MESSAGES (negative = the prop-42 came FIRST) and seconds, the value before,
    the value on the wire and the prediction.
    """
    max_by_agent = {}          # running previous maximum per agent
    hm = [(i, t, v[2], v[3]) for i, t, op, v in seq
          if op == OP_INT and v[1] == PROP_HEALTH_MAX]
    applies, closes, stray = [], [], []
    live = {}                  # buff -> (agent, apply index)
    joined_hm = set()

    def nearest(i, t, agent):
        best = None
        for j, tj, aj, val in hm:
            if aj != agent or abs(tj - t) > BATCH or j in joined_hm:
                continue
            if best is None or abs(j - i) < abs(best[0] - i):
                best = (j, tj, val)
        return best

    for i, t, op, v in seq:
        if op == OP_INT and v[1] == PROP_HEALTH_MAX:
            continue
        if op == OP_APPLY and v[2] == DEEP_WOUND:
            agent = v[1]
            before = max_by_agent.get(agent)
            hit = nearest(i, t, agent)
            row = {"t": t, "agent": agent, "buff": v[4], "before": before,
                   "predicted": predicted_max(before) if before else None,
                   "wire": None, "order_msgs": None, "order_s": None}
            if hit:
                j, tj, val = hit
                joined_hm.add(j)
                row.update(wire=val, order_msgs=j - i, order_s=round(tj - t, 6))
                max_by_agent[agent] = val
            row["batch"] = [(hex(op2), v2[1:3]) for _i2, _t2, op2, v2
                            in seq[i:i + 4]]
            live[v[4]] = (agent, before)
            applies.append(row)
        elif op == OP_REMOVE and v[2] in live:
            agent, before = live.pop(v[2])
            hit = nearest(i, t, agent)
            row = {"t": t, "agent": agent, "buff": v[2], "restores_to": before,
                   "wire": None, "order_msgs": None, "order_s": None}
            if hit:
                j, tj, val = hit
                joined_hm.add(j)
                row.update(wire=val, order_msgs=j - i, order_s=round(tj - t, 6))
                max_by_agent[agent] = val
            row["batch"] = [(hex(op2), v2[1:3]) for _i2, _t2, op2, v2
                            in seq[i:i + 4]]
            closes.append(row)
    # The running maximum has to be seeded from the prop-42s that are NOT
    # joined to a 482 event -- spawn state, morale -- in wire order. Second
    # pass: rebuild `before` properly now that the joined ones are known.
    running = {}
    for i, t, op, v in seq:
        if op == OP_INT and v[1] == PROP_HEALTH_MAX:
            if i in joined_hm:
                continue
            agent, val = v[2], v[3]
            # a prop-42 MOVING while a 482 episode is live on this agent is P4's
            # counter-example; record it. A re-declaration of the value already
            # in force is not a move (RUN-SKILLS-RB 2026-09-16: a Reversal of
            # Fortune trigger re-declares the taker's 42, 384 inside the wound),
            # and "live" means THIS buff's apply..close, not any apply before
            # and any close after.
            moved = running.get(agent) is not None and val != running[agent]
            if moved:
                for row in applies:
                    if row["agent"] != agent or row["t"] >= t:
                        continue
                    close_t = next((c["t"] for c in closes
                                    if c["buff"] == row["buff"]), float("inf"))
                    if t < close_t:
                        stray.append({"t": t, "agent": agent, "value": val,
                                      "was": running[agent]})
                        break
            running[agent] = val
        elif op == OP_APPLY and v[2] == DEEP_WOUND:
            for row in applies:
                if row["t"] == t and row["agent"] == v[1] and row["buff"] == v[4]:
                    row["before"] = running.get(v[1])
                    row["predicted"] = (predicted_max(row["before"])
                                        if row["before"] else None)
                    if row["wire"] is not None:
                        running[v[1]] = row["wire"]
        elif op == OP_REMOVE:
            for row in closes:
                if row["t"] == t and row["agent"] == v[1] and row["buff"] == v[2]:
                    opened = [a for a in applies if a["buff"] == v[2]
                              and a["agent"] == v[1] and a["t"] < t]
                    if opened:
                        row["restores_to"] = opened[-1]["before"]
                    if row["wire"] is not None:
                        running[v[1]] = row["wire"]
    return {"applies": applies, "closes": closes, "stray": stray}


def census(codec=None):
    """Every live capture, every game connection holding a 482 apply."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="deepwoundjoin reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for row in tape.channel_files(cap_dir):
            try:
                seq = sequence(cap_dir, row["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            if not any(op == OP_APPLY and v[2] == DEEP_WOUND
                       for _i, _t, op, v in seq):
                continue
            j = join(seq)
            j.update(capture=stamp, connection=row["connection"])
            out.append(j)
    return out


CONDITION_IDS = (478, 479, 480, 481, 482, 483, 484, 485, 486, 2077)


OP_ATTRIBUTE = 0x003B       # [agent, attribute, base, effective]
WEAKNESS = 486


def weakness_attributes(codec=None):
    """Every Weakness apply and removal in the corpus, with the 0x003B rows of
    its own batch. SKILLS-WK: retail re-declares the agent's attributes one
    lower at the apply and restores them at the removal. A row: {"capture",
    "connection", "t", "kind" (apply / close), "agent", "attrs":
    [(attribute, base, effective)]}."""
    import vaultpath
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="deepwoundjoin reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = sequence(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            buffs = {}
            for i, t, op, v in seq:
                kind = agent = None
                if op == OP_APPLY and v[2] == WEAKNESS:
                    buffs[v[4]] = v[1]
                    kind, agent = "apply", v[1]
                elif op == OP_REMOVE and v[2] in buffs:
                    kind, agent = "close", buffs.pop(v[2])
                if kind is None:
                    continue
                attrs = [(w[2], w[3], w[4]) for _j, tj, opj, w in seq[i:i + 12]
                         if opj == OP_ATTRIBUTE and w[1] == agent
                         and abs(tj - t) <= BATCH]
                out.append({"capture": stamp, "connection": ch["connection"],
                            "t": t, "kind": kind, "agent": agent,
                            "attrs": attrs})
    return out


def score_weakness(rows):
    """WK1: every apply and every close carries its 0x003B rows; WK2: for each
    agent, each attribute's effective at the close is the apply's plus ONE and
    the base is the same at both."""
    applies = [r for r in rows if r["kind"] == "apply"]
    closes = [r for r in rows if r["kind"] == "close"]
    pairs = lifted = same_base = 0
    for a in applies:
        c = next((c for c in closes if c["capture"] == a["capture"]
                  and c["connection"] == a["connection"]
                  and c["agent"] == a["agent"] and c["t"] > a["t"]), None)
        if c is None:
            continue
        ca = {x[0]: x for x in c["attrs"]}
        for attr, base, eff in a["attrs"]:
            if attr in ca:
                pairs += 1
                lifted += ca[attr][2] - eff == 1
                same_base += ca[attr][1] == base
    return {"applies": len(applies), "closes": len(closes),
            "applies_declared": sum(1 for r in applies if r["attrs"]),
            "closes_declared": sum(1 for r in closes if r["attrs"]),
            "pairs": pairs, "lifted_by_one": lifted, "same_base": same_base,
            "zero_base_rows": sum(1 for r in rows for x in r["attrs"] if x[1] == 0)}


CONDITIONS = frozenset(range(478, 487)) | {2077}


def weakness_lifts(codec=None):
    """Every batch in the corpus that REMOVES Weakness and heals the same agent
    -- a cast that lifts the penalty and heals by an attribute in one stroke
    (RUN-SKILLS-WKL, studies/skills 52). A row: {"capture", "connection", "t",
    "agent", "others" (conditions still live on the agent after the removal),
    "points" (the 55 word in whole points of the running maximum, None with no
    maximum on the wire), "restored" ({attribute: the effective rank the batch
    restores}), "attrs_before_heal" (every 0x003B restore rides
    AHEAD of the 55 word)}."""
    import struct
    import vaultpath
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="deepwoundjoin reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = sequence(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            buffs, hmax = {}, {}        # buff id -> (agent, skill); agent -> [42]
            for i, t, op, v in seq:
                if op == 0x009F and v[1] == 42:
                    hmax[v[2]] = v[3]
                elif op == OP_APPLY and v[2] in CONDITIONS:
                    buffs[v[4]] = (v[1], v[2])
                elif op == OP_REMOVE and v[2] in buffs:
                    agent, skill = buffs.pop(v[2])
                    if skill != WEAKNESS:
                        continue
                    batch = [(j, w) for j, tj, _o, w in seq[i:i + 14]
                             if abs(tj - t) <= BATCH]
                    heal = next(((j, w) for j, w in batch
                                 if w[0] == 0x00A3 and w[1] == 55
                                 and w[2] == agent and w[3] == agent), None)
                    if heal is None:
                        continue
                    attrs = [j for j, w in batch
                             if w[0] == OP_ATTRIBUTE and w[1] == agent]
                    restored = {w[2]: w[4] for _j, w in batch
                                if w[0] == OP_ATTRIBUTE and w[1] == agent}
                    frac = struct.unpack(
                        "<f", struct.pack("<I", heal[1][4] & 0xFFFFFFFF))[0]
                    mx = hmax.get(agent)
                    out.append({
                        "capture": stamp, "connection": ch["connection"],
                        "t": t, "agent": agent,
                        "others": sum(1 for a, _s in buffs.values()
                                      if a == agent),
                        "points": None if not mx else round(frac * mx, 2),
                        "restored": restored,
                        "attrs_before_heal": bool(attrs)
                        and max(attrs) < heal[0]})
    return out


def status_census(codec=None):
    """Which `0x00F1` bits each effect apply SETS, from retail's own wire.

    For every `0x0042` in the live corpus, the first `0x00F1` to the same
    agent within the batch shoulder is read and its bits NEWLY SET against
    that agent's previous word are counted, keyed by skill id; shouts and the
    other no-bit families show up as `no_status` counts. `test_mechanics`
    pins the table `effects.status_word` was read from, so a corpus that
    stopped agreeing would go red there rather than drift silently.

    Returns {"set": {skill: {bits: n}}, "n": {skill: n}, "no_status": {skill: n}}.
    """
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="deepwoundjoin reads live captures")
    out = {"set": {}, "n": {}, "no_status": {}}
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for row in tape.channel_files(cap_dir):
            try:
                seq = sequence(cap_dir, row["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            status = {}
            for i, t, op, v in seq:
                if op == 0x00F1:
                    status[v[1]] = v[2]
                    continue
                if op != OP_APPLY:
                    continue
                agent, skill = v[1], v[2]
                prev = status.get(agent, 0)
                follow = [v2[2] for _j, t2, op2, v2 in seq[i + 1:i + 8]
                          if op2 == 0x00F1 and v2[1] == agent
                          and t2 - t <= BATCH]
                out["n"][skill] = out["n"].get(skill, 0) + 1
                if not follow:
                    out["no_status"][skill] = out["no_status"].get(skill, 0) + 1
                    continue
                bits = follow[0] & ~prev
                d = out["set"].setdefault(skill, {})
                d[bits] = d.get(bits, 0) + 1
    return out


def score(rows):
    """(n_applies, joined, exact, closes_joined, closes_exact, stray, orders)."""
    n = sum(len(r["applies"]) for r in rows)
    joined = sum(1 for r in rows for a in r["applies"] if a["wire"] is not None)
    exact = sum(1 for r in rows for a in r["applies"]
                if a["wire"] is not None and a["wire"] == a["predicted"])
    cj = sum(1 for r in rows for c in r["closes"] if c["wire"] is not None)
    ce = sum(1 for r in rows for c in r["closes"]
             if c["wire"] is not None and c["wire"] == c["restores_to"])
    stray = sum(len(r["stray"]) for r in rows)
    orders = sorted({a["order_msgs"] for r in rows for a in r["applies"]
                     if a["order_msgs"] is not None}
                    | {c["order_msgs"] for r in rows for c in r["closes"]
                       if c["order_msgs"] is not None})
    return n, joined, exact, cj, ce, stray, orders


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = census()
    if args.json:
        print(json.dumps(rows, default=str, indent=1))
        return
    sc = status_census()
    print("status bits newly SET by each apply (skill: {bits: n}), then applies with no 0x00F1:")
    for skill in sorted(sc["set"]):
        print(f"  {skill:>5}: " + ", ".join(f"0x{b:04X} x{n}" for b, n in sorted(sc["set"][skill].items()))
              + f"   (of {sc['n'][skill]})")
    print("  no status message: " + ", ".join(f"{k} x{v}" for k, v in sorted(sc["no_status"].items())))
    for r in rows:
        print(f"{r['capture']} {r['connection']}")
        for a in r["applies"]:
            print(f"  APPLY t={a['t']:9.3f} agent {a['agent']} buff {a['buff']:>3} "
                  f"max {a['before']} -> wire {a['wire']} (predicted "
                  f"{a['predicted']}) prop-42 at {a['order_msgs']:+d} msgs, "
                  f"{a['order_s']:+.3f} s" if a["wire"] is not None else
                  f"  APPLY t={a['t']:9.3f} agent {a['agent']} buff {a['buff']:>3} "
                  f"max {a['before']} -> NO prop-42 within {BATCH*1000:.0f} ms")
        for c in r["closes"]:
            print(f"  CLOSE t={c['t']:9.3f} agent {c['agent']} buff {c['buff']:>3} "
                  f"wire {c['wire']} (restores {c['restores_to']}) prop-42 at "
                  f"{c['order_msgs']:+d} msgs, {c['order_s']:+.3f} s"
                  if c["wire"] is not None else
                  f"  CLOSE t={c['t']:9.3f} agent {c['agent']} buff {c['buff']:>3} "
                  f"NO prop-42 within {BATCH*1000:.0f} ms")
        for a in r["applies"] + r["closes"]:
            print(f"      batch from the event: {a['batch']}")
        for s in r["stray"]:
            print(f"  STRAY prop-42 t={s['t']:9.3f} agent {s['agent']} = "
                  f"{s['value']} while a 482 episode was live (P4 miss)")
    n, joined, exact, cj, ce, stray, orders = score(rows)
    print(f"\n482 applies {n}: joined {joined}, exact x0.8 {exact}; "
          f"closes joined {cj}, exact restore {ce}; stray prop-42 {stray}; "
          f"prop-42 offsets in messages {orders}")


if __name__ == "__main__":
    main()
