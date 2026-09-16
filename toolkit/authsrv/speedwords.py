r"""Movement speed on retail's wire: every 0x0027 joined to the episode change that sent it.

    python toolkit/authsrv/speedwords.py            # every live capture
    python toolkit/authsrv/speedwords.py --rows     # one line per speed word
    python toolkit/authsrv/speedwords.py --json

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

WHAT `base` IS HERE. The per-(connection, agent) value the agent is RESTORED
to -- the most common of {288, 300} among its speed words. An agent that never
shows a plain base (one word, e.g. a Crippled body created mid-episode) gets
`base = None` and a `ratio = None`; it is counted, never scored.

Standard library only. Reads the vault through `vaultpath`, refuses a partial
tape the way bufflog does.
"""
import argparse
import collections
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
OP_STATUS = 0x00F1
OP_ITEM = 0x006F
BATCH_S = 0.060          # the corpus's own batch shoulder, as deepwoundjoin uses it
BASES = (288.0, 300.0)   # P6: the two restore values the corpus shows
BOOST_SKILLS = (160, 364)
CRIPPLED = 481
PLAYER_INFO = 0x0059


def f32(v):
    if isinstance(v, float):
        return v
    return struct.unpack("<f", struct.pack("<I", int(v) & 0xFFFFFFFF))[0]


def sequence(capture_dir, connection, codec):
    """[(t, op, values)] for one game connection, framed once, whole."""
    info, events = tape.load_tape(capture_dir, connection)
    t0 = info.get("t0") or 0.0
    events = [(round(t + t0, 6), p) for t, p in events]
    msgs, (consumed, total, err) = tape.decode_all(events, codec, "GAME_SMSG", 0)
    if err is not None or consumed != total:
        raise bufflog.BuffLogError(
            f"{capture_dir} {connection} framed {consumed}/{total}: {err}")
    return msgs


def speed_rows(msgs):
    """Every 0x0027 in a decoded connection, with its batch companions.

    `apply`/`remove`/`status`/`item` are the same-agent companions within
    BATCH_S either side; `words_in_batch` counts the speed words this agent
    received in that shoulder (P5's two); `prev` is the agent's previous word.
    """
    player = next((v[1] for _t, op, v in msgs if op == PLAYER_INFO and len(v) > 1),
                  None)
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
                     "words_in_batch": near["words"] + 1})
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


def census(codec=None):
    """Every live capture, every game connection holding a speed word."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="speedwords reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for row in tape.channel_files(cap_dir):
            try:
                msgs = sequence(cap_dir, row["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
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
    return out


def score(rows):
    """The predictions against the rows. Returns {name: (hits, misses, detail)}.

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
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true", help="one line per speed word")
    args = ap.parse_args()
    rows = census()
    if args.json:
        print(json.dumps(rows, default=str))
        return
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
    for name, (hit, miss, detail) in score(rows).items():
        print(f"  {name}: {hit} / {miss}  ({detail})")


if __name__ == "__main__":
    main()
