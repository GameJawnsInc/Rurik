"""timingjoin.py -- every timed quantity around an attacker, retail beside ours.

    python toolkit/authsrv/timingjoin.py                          # newest of ours vs the dagger tapes
    python toolkit/authsrv/timingjoin.py --capture 20260917T224104 --ours <authsrv-...-c1.jsonl>
    python toolkit/authsrv/timingjoin.py --capture 20260917T160915 --swings     # one row per swing

THE METHOD THAT FOUND SLICE-F49, F50 AND F51 (studies/slice/FINDINGS.md): take
one retail tape and one of OUR OWN recorder captures (vault/captures/gamesrv,
written by every harness run), decode both through the same codec, run the SAME
joins over both, and read the two columns side by side. A server timer that is
wrong shows as a row whose columns disagree; nothing here knows what the right
number is. Three defects sat in plain sight for weeks because each side had only
ever been measured alone.

THE ROWS, all s2c, all on one connection's own clock, all about the OBSERVER
(the agent whose self-scoped property 41 opens the connection -- adrenjoin's
rule; agent 1 on ours):

  swing start->start     consecutive 0x00A0 [4, me, T, 0] with no skill between,
                         split by whether the NEXT swing double strikes -- a
                         doubling swing opens an eighth of the interval early
                         (DAGGERS-F20), so the two rows differ by that eighth
  swing start->word      a start to the observer's next damage word (0x00A3
                         property 16 / 17) or fail word (0x00A0 property 38)
  double gap             0x009F [2, me, 0] behind the word before it
  dual gap               0x009F [47, me, 0] behind its skill's 0x00E5
  debit->E5 <skill>      the energy debit (0x00A2 property 62) to the landing
  E5->E3 <skill>         the landing to 0x00E3
  E5->E6 <skill>         the landing to the recharge's end, beside the recharge
  E5->next swing         the landing to the next plain swing's start
  chain set->0           the last nonzero 0x005C on a target to its 0
  effect <skill>         0x0042 apply to the 0x0044 that removes that instance

Every row is split PLAIN / BOOSTED: boosted is "inside an episode of a skill
whose content row says Attack speed increase" (the 0x0042 to its 0x0044, or the
0x0042's own duration). A row with n = 0 on one side is printed, never dropped.

Standard library only. The retail side needs the vault; the pure functions
(`census`, `swings`) take a decoded message list and are tested without one.
"""
import argparse
import collections
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402

DAGGER_TAPES = ("20260917T160915", "20260917T224104")
E3, E5, E6 = 0x00E3, 0x00E5, 0x00E6
PINT, PINT_T, PFLOAT, PFLOAT_T = 0x009F, 0x00A0, 0x00A2, 0x00A3
COMBO, APPLY, REMOVE = 0x005C, 0x0042, 0x0044
SAME = 0.02


def _f32(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def ias_skills():
    """Skill ids whose content row says they raise attack speed; {} on failure."""
    try:
        import agents
        rows = agents.WORLD.rows("skill_effect")
    except Exception:                                           # noqa: BLE001
        return set()
    return {int(k) for k, row in rows.items()
            if str(k).isdigit() and row.get("scale_means") == "Attack speed increase"}


def observer_of(s2c):
    for _t, op, v in s2c:
        if op == PINT and len(v) > 3 and v[1] == 41:
            return v[2]
    return None


def load_retail(stamp):
    """[(label, s2c, observer)] for every swinging connection of one live capture."""
    out = []
    for capdir, gf in livewire.live_connections():
        if os.path.basename(capdir) != stamp:
            continue
        try:
            _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        except Exception:                                       # noqa: BLE001
            continue
        s2c = [(t, op, list(v)) for t, d, op, v in merged if d == "s2c"]
        me = observer_of(s2c)
        if me is not None and any(op == PINT_T and v[1] == 4 and v[2] == me
                                  for _t, op, v in s2c):
            out.append((f"{stamp} {gf[5:26]}", s2c, me))
    return out


OUR_PLAYER = 1          # agents.PLAYER_AGENT_ID; ours announces the HERO's property
                        # 41 first, so adrenjoin's rule would name the wrong agent


def load_ours(path, observer=OUR_PLAYER):
    """(label, s2c, observer) for one of our own recorder captures."""
    events = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") == "sent" and r.get("plain"):
            events.append((r["t"], bytes.fromhex(r["plain"])))
    msgs, _receipt = livewire.tape.decode_all(events, livewire._get_codec(),
                                              channel="GAME_SMSG", mask=0,
                                              strict=False)
    s2c = [(t, op, list(v)) for t, op, v in msgs]
    return os.path.basename(path), s2c, observer


def newest_ours():
    root = os.path.join(os.path.dirname(livewire.captures_root()), "gamesrv")
    files = glob.glob(os.path.join(root, "authsrv-*-c1.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def boost_windows(s2c, me, ias):
    """[(from, to)] the observer spends under an attack-speed skill."""
    out = []
    removes = [(t, v[2]) for t, op, v in s2c if op == REMOVE and v[1] == me]
    for t, op, v in s2c:
        if op != APPLY or v[1] != me or v[2] not in ias:
            continue
        inst = v[4] if len(v) > 4 else None
        dur = _f32(v[5]) if len(v) > 5 else 8.0
        gone = [x for x, i in removes if x > t and i == inst]
        out.append((t, min(gone[0], t + dur) if gone else t + dur))
    return out


def swings(s2c, me, ias=()):
    """One dict per PLAIN swing of the observer's, in order.

    t, target, boosted, to_next (start to the next start, None when a skill or
    a gap sits between), to_word, critical, doubled, after_skill (seconds since
    the observer's last skill landing, None if over 3 s)."""
    windows = boost_windows(s2c, me, set(ias))
    boosted = lambda t: any(a <= t < b for a, b in windows)
    starts = [(t, v[3]) for t, op, v in s2c
              if op == PINT_T and v[1] == 4 and v[2] == me]
    words = [(t, v[1]) for t, op, v in s2c
             if (op == PFLOAT_T and v[1] in (16, 17) and v[3] == me and _f32(v[4]) <= 0)
             or (op == PINT_T and v[1] == 38 and v[3] == me)]
    seconds = [t for t, op, v in s2c if op == PINT and v[1] == 2 and v[2] == me]
    lands = [t for t, op, v in s2c                  # a stance's E5 is no landing
             if op == E5 and v[1] == me and v[4] and v[2] not in set(ias)]
    rows = []
    for i, (t, target) in enumerate(starts):
        nxt = starts[i + 1][0] if i + 1 < len(starts) else None
        between = nxt is not None and any(t < x <= nxt for x in lands)
        word = next(((x, p) for x, p in words if 0 < x - t < 1.5
                     and (nxt is None or x < nxt + SAME)), None)
        prior = [x for x in lands if x <= t]
        rows.append({
            "t": t, "target": target, "boosted": boosted(t),
            "to_next": (nxt - t if nxt is not None and not between
                        and nxt - t < 4.0 else None),
            "to_word": word[0] - t if word else None,
            "critical": bool(word and word[1] == 17),
            "doubled": bool(word and any(0 < s - word[0] < 0.75 for s in seconds)),
            "after_skill": (t - prior[-1] if prior and t - prior[-1] < 3.0 else None),
        })
    return rows


def census(s2c, me, ias=()):
    """{row name: [seconds]} -- see the module docstring for the rows."""
    ias = set(ias)
    windows = boost_windows(s2c, me, ias)
    tag = lambda t: "boosted" if any(a <= t < b for a, b in windows) else "plain"
    rows = collections.defaultdict(list)
    sw = swings(s2c, me, ias)
    for i, r in enumerate(sw):
        if r["to_next"] is not None and r["after_skill"] is None                 and tag(r["t"]) == tag(r["t"] + r["to_next"]):
            # an interval that STRADDLES an episode's edge is neither regime's
            into = (", the next DOUBLES"
                    if i + 1 < len(sw) and sw[i + 1]["doubled"] else "")
            rows[f"swing start->start {tag(r['t'])}{into}"].append(r["to_next"])
        if r["to_word"] is not None:
            rows[f"swing start->word {tag(r['t'])}"].append(r["to_word"])
    starts = [r["t"] for r in sw]
    words = [t for t, op, v in s2c
             if op == PFLOAT_T and v[1] in (16, 17) and v[3] == me and _f32(v[4]) <= 0]
    for t, op, v in s2c:
        if op == PINT and v[2] == me and v[1] == 2:
            prev = [w for w in words if w < t - SAME]
            if prev and t - prev[-1] < 0.75:
                rows[f"double gap {tag(prev[-1])}"].append(t - prev[-1])
    e5 = [(t, v[2], v[4]) for t, op, v in s2c if op == E5 and v[1] == me]
    e6 = [(t, v[2]) for t, op, v in s2c if op == E6 and v[1] == me]
    e3 = [(t, v[2]) for t, op, v in s2c if op == E3 and v[1] == me]
    marks47 = [t for t, op, v in s2c if op == PINT and v[1] == 47 and v[2] == me]
    debits = [t for t, op, v in s2c if op == PFLOAT and v[1] == 62 and v[2] == me]
    for t, sid, recharge in e5:
        if not recharge:
            continue
        side = tag(t)
        prior = [d for d in debits if 0 <= t - d < 2.0]
        if prior and sid not in ias:
            rows[f"debit->E5 {sid} {side}"].append(t - prior[-1])
        done = [x for x, s in e3 if s == sid and x >= t - SAME]
        if done and sid not in ias:
            rows[f"E5->E3 {sid} {side}"].append(max(0.0, done[0] - t))
        ready = [x for x, s in e6 if s == sid and x > t]
        if ready and ready[0] - t < recharge + 1.0:
            rows[f"E5->E6 {sid} (recharge {recharge})"].append(ready[0] - t)
        second = [x for x in marks47 if 0 < x - t < 0.75]
        if second:
            rows[f"dual gap {side}"].append(second[0] - t)
        if sid in ias:
            continue
        nxt = [x for x in starts if x > t + SAME]
        later = [x for x, s, r in e5 if x > t and r and s not in ias]
        if nxt and nxt[0] - t < 1.6 and not (later and later[0] < nxt[0]):
            rows[f"E5->next swing {side}"].append(nxt[0] - t)
    last = {}
    for t, op, v in s2c:
        if op == COMBO and v[1] == me:
            if v[3]:
                last[v[2]] = t
            elif v[2] in last:
                rows["chain set->0"].append(t - last.pop(v[2]))
    removes = [(t, v[2]) for t, op, v in s2c if op == REMOVE and v[1] == me]
    for t, op, v in s2c:
        if op == APPLY and v[1] == me and len(v) > 4:
            gone = [x for x, i in removes if x > t and i == v[4]]
            if gone:
                rows[f"effect {v[2]}"].append(gone[0] - t)
    return dict(rows)


def _cell(xs):
    if not xs:
        return "n=0"
    xs = sorted(xs)
    return "n=%-3d p50 %.3f  [%.3f .. %.3f]" % (len(xs), xs[len(xs) // 2], xs[0], xs[-1])


def report(retail, ours):
    """Print the two censuses side by side; returns the row names compared."""
    names = sorted(set(retail) | set(ours))
    print("%-34s | %-38s | %s" % ("row", "RETAIL", "OURS"))
    for name in names:
        print("%-34s | %-38s | %s" % (name, _cell(retail.get(name)), _cell(ours.get(name))))
    return names


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--capture", action="append", metavar="STAMP",
                    help="a live capture (repeatable); default: the two dagger tapes")
    ap.add_argument("--ours", metavar="JSONL",
                    help="one of our recorder captures; default: the newest")
    ap.add_argument("--observer", type=int, default=OUR_PLAYER, metavar="AGENT",
                    help="whose clock to read on OUR side (default 1, the player; "
                         "200 is the first hero)")
    ap.add_argument("--swings", action="store_true",
                    help="print one row per plain swing of the retail side instead")
    a = ap.parse_args(argv)
    ias = ias_skills()
    retail = collections.defaultdict(list)
    for stamp in a.capture or DAGGER_TAPES:
        for label, s2c, me in load_retail(stamp):
            if a.swings:
                print(f"# {label} observer {me}")
                for r in swings(s2c, me, ias):
                    print("%9.3f tgt %-4s %-7s next %-6s word %-6s %s%s after_skill %s" % (
                        r["t"], r["target"], "boosted" if r["boosted"] else "plain",
                        "-" if r["to_next"] is None else "%.3f" % r["to_next"],
                        "-" if r["to_word"] is None else "%.3f" % r["to_word"],
                        "C" if r["critical"] else ".", "D" if r["doubled"] else ".",
                        "-" if r["after_skill"] is None else "%.3f" % r["after_skill"]))
                continue
            for name, xs in census(s2c, me, ias).items():
                retail[name] += xs
    if a.swings:
        return 0
    path = a.ours or newest_ours()
    ours = {}
    if path:
        label, s2c, me = load_ours(path, a.observer)
        print(f"# ours: {label} (observer {me}); retail: {', '.join(a.capture or DAGGER_TAPES)}")
        ours = census(s2c, me, ias)
    else:
        print("# no recorder capture of ours found -- the retail column alone")
    report(dict(retail), ours)
    return 0


if __name__ == "__main__":
    sys.exit(main())
