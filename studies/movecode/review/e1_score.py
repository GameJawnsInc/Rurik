#!/usr/bin/env python3
"""DEATHWALK-E1's scorer: a death of the PLAYER with its own swing in flight carries
GV_ATTACK_STOPPED [3, me, 0] in the death's batch, and a death with no swing in flight does not.
(MOVECODE-1z-ds.27, DEATH_STOPS_WINDUP; `--death-keeps-windup` reverts.)

    python studies/movecode/review/e1_score.py STAMP [STAMP ...]   # gamesrv capture stamps (all -cN)
    python studies/movecode/review/e1_score.py --corpus            # every tape since 2026-09-20 (09-20..09-30 and October)
    python studies/movecode/review/e1_score.py --selftest          # no run needed; ~3 s

RETAIL (1z-ds.27, OBSERVED): every death with the dier's windup open carries [3, A, 0] after the
dead-bit status, 30 of 30; deaths with no windup open carry none, 0 of 155.

READ OFF THE WIRE (our tape is the send order):
  death   = sent 0x00F1 [1, word], the word GAINING 0x10
  start   = sent 0x00A0 [4, 1, T];  landing = sent 0x009F [1, 1, *] / 0x00A4 [1]
  stop    = sent 0x009F [3, 1, 0]
The swing is OPEN at the death when the player's last start has no landing and no stop before it
(a door's [3] already on the wire closes it: 1z-ds.33's one [3] per windup). The death's BATCH is
every send within 5 ms after the KILL status.

THE ARM IS READ OFF THE TAPE: flags DEATH_STOPS_WINDUP true = "fixed", false = "known-bad",
absent = a build before 1z-ds.27 ("pre-fix", the known-bad behaviour).

VERDICTS, one per player death:
  open windup     fixed: PASS if the batch carries [3, 1, 0], else FAIL
                  known-bad / pre-fix: old-shape if it carries none, else UNEXPECTED
  no open windup  every arm: control-ok if the batch carries no [3], else CONTROL-FAIL
FLOOR (E1): 5 open-windup deaths on the fixed arm; below that it is UNEXPOSED.
"""
import glob
import json
import os
import re
import struct
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import vaultpath  # noqa: E402

ME = 1
OP_INT, OP_INT_TARGET, OP_LAND, OP_STATUS = 0x9F, 0xA0, 0xA4, 0xF1
P_LAND, P_STOP, P_START = 1, 3, 4
DEAD_BIT = 0x10
BATCH = 0.005
FLOOR = 5
OPRE = re.compile(r'"opcode": (\d+)')


def load(path):
    """(flags, events): t, k in S4 / LAND / ST3 / DEAD / RISE."""
    ev, flags, word = [], {}, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not flags and '"kind": "flags"' in line:
                try:
                    flags = json.loads(line)
                except ValueError:
                    flags = {}
                continue
            if '"kind": "sent"' not in line:
                continue
            m = OPRE.search(line)
            if not m or int(m.group(1)) not in (OP_INT, OP_INT_TARGET, OP_LAND, OP_STATUS):
                continue
            r = json.loads(line)
            op, b, t = r["opcode"], bytes.fromhex(r.get("plain") or ""), r["t"]
            try:
                if op == OP_INT:
                    _o, p, ag, val = struct.unpack_from("<HIII", b, 0)
                    if ag == ME and p == P_LAND:
                        ev.append({"t": t, "k": "LAND"})
                    elif ag == ME and p == P_STOP and val == 0:
                        ev.append({"t": t, "k": "ST3"})
                elif op == OP_INT_TARGET:
                    _o, p, ag, _tg = struct.unpack_from("<HIII", b, 0)
                    if ag == ME and p == P_START:
                        ev.append({"t": t, "k": "S4"})
                elif op == OP_LAND:
                    _o, ag = struct.unpack_from("<HI", b, 0)
                    if ag == ME:
                        ev.append({"t": t, "k": "LAND"})
                elif op == OP_STATUS:
                    _o, ag, w = struct.unpack_from("<HII", b, 0)
                    if ag == ME:
                        if (w & DEAD_BIT) and not (word & DEAD_BIT):
                            ev.append({"t": t, "k": "DEAD"})
                        elif (word & DEAD_BIT) and not (w & DEAD_BIT):
                            ev.append({"t": t, "k": "RISE"})
                        word = w
            except struct.error:
                continue
    return flags, ev


def arm_of(flags):
    if "DEATH_STOPS_WINDUP" not in flags:
        return "pre-fix"
    return "fixed" if flags["DEATH_STOPS_WINDUP"] else "known-bad"


def deaths(ev):
    """[{t, open, stop_in_batch}] for every player death."""
    out, last_start, closed = [], None, True
    for j, e in enumerate(ev):
        if e["k"] == "S4":
            last_start, closed = e["t"], False
        elif e["k"] in ("LAND", "ST3") and last_start is not None:
            closed = True
        elif e["k"] == "DEAD":
            batch = [x["k"] for x in ev[j + 1:] if x["t"] - e["t"] <= BATCH]
            out.append({"t": e["t"], "open": (last_start is not None and not closed),
                        "into": None if last_start is None else round(e["t"] - last_start, 3),
                        "stop": "ST3" in batch})
            closed = True            # the corpse's swing is over either way
    return out


def verdict(d, arm):
    if not d["open"]:
        return "control-ok" if not d["stop"] else "CONTROL-FAIL"
    if arm == "fixed":
        return "PASS" if d["stop"] else "FAIL"
    return "old-shape" if not d["stop"] else "UNEXPECTED"


def tapes_for(arg):
    if os.path.isfile(arg):
        return [arg]
    return sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", f"authsrv-{arg}-c*.jsonl")))


def score(paths, quiet=False):
    by = {}
    for p in paths:
        flags, ev = load(p)
        arm = arm_of(flags)
        for d in deaths(ev):
            v = verdict(d, arm)
            by.setdefault(arm, []).append((p, d, v))
            if not quiet:
                print(f"  {os.path.basename(p)} t={d['t']:.3f} [{arm}] "
                      f"{'OPEN windup' if d['open'] else 'no windup  '} into {d['into']} "
                      f"[3] in batch {d['stop']} -> {v}")
    return by


def summary(by):
    lines = []
    for arm, rows in sorted(by.items()):
        vs = {}
        for _p, _d, v in rows:
            vs[v] = vs.get(v, 0) + 1
        n_open = sum(1 for _p, d, _v in rows if d["open"])
        lines.append(f"[{arm}] player deaths {len(rows)}, open windup {n_open}"
                     + ("" if arm != "fixed" or n_open >= FLOOR else f" (UNEXPOSED: floor {FLOOR})")
                     + f"  {vs}")
    return "\n".join(lines)


def selftest():
    import authsrv
    bad = 0

    def ck(ok, what, detail=""):
        nonlocal bad
        print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
        bad += 0 if ok else 1

    print("== 1. the opcodes and props are the server's ==")
    ck(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT == OP_INT
       and authsrv.GAME_SMSG_AGENT_UPDATE_STATUS == OP_STATUS
       and authsrv.agents.GV_ATTACK_STOPPED == P_STOP and authsrv.agents.GV_ATTACK_STARTED == P_START
       and authsrv.agents.GV_MELEE_ATTACK_FINISHED == P_LAND and authsrv.agents.EFFECT_DEAD == DEAD_BIT,
       "0x9F / 0xA0 / 0xF1, props 1 / 3 / 4 and the dead bit match authsrv")

    print("== 2. synthetic events ==")
    ev = [{"t": 0.0, "k": "S4"}, {"t": 0.3, "k": "DEAD"}, {"t": 0.3001, "k": "ST3"}]
    d = deaths(ev)[0]
    ck(d["open"] and d["stop"] and verdict(d, "fixed") == "PASS"
       and verdict(d, "pre-fix") == "UNEXPECTED", "open windup, [3] in the batch: fixed PASS")
    ev = [{"t": 0.0, "k": "S4"}, {"t": 0.3, "k": "DEAD"}]
    d = deaths(ev)[0]
    ck(verdict(d, "fixed") == "FAIL" and verdict(d, "known-bad") == "old-shape",
       "open windup, no [3]: fixed FAIL, known-bad old-shape")
    ev = [{"t": 0.0, "k": "S4"}, {"t": 0.5, "k": "LAND"}, {"t": 0.9, "k": "DEAD"}]
    d = deaths(ev)[0]
    ck(not d["open"] and verdict(d, "fixed") == "control-ok", "after the landing: no windup, control-ok")
    ev = [{"t": 0.0, "k": "S4"}, {"t": 0.2, "k": "ST3"}, {"t": 0.3, "k": "DEAD"}]
    ck(not deaths(ev)[0]["open"], "a door's [3] before the death closes the windup (one [3] per windup)")
    ev = [{"t": 0.0, "k": "S4"}, {"t": 0.3, "k": "DEAD"}, {"t": 0.31, "k": "ST3"}]
    ck(not deaths(ev)[0]["stop"], "a [3] 10 ms after the KILL is not in its batch")

    print("== 3. tapes written by the REAL kill_player, both arms ==")
    tmp = tempfile.mkdtemp(prefix="e1score-")
    saved = (authsrv.DEATH_STOPS_WINDUP, authsrv.ATTACK_APPROACH)
    authsrv.ATTACK_APPROACH = False
    out = {}
    try:
        for conn, on, in_windup in ((81, True, True), (82, False, True), (83, True, False)):
            authsrv.DEATH_STOPS_WINDUP = on
            rec = authsrv.Recorder(tmp, conn)
            seq = [0]

            def send(op, vals, label="", quiet=False, rec=rec, seq=seq):
                seq[0] += 1
                rec.event("sent", seq=seq[0], opcode=op, label=label,
                          plain=authsrv.codec.encode("GAME_SMSG", op, vals).hex())
            st = {"agents": {10: {"name": "t", "dead": False, "last_hit": 0.0, "max_health": 100.0,
                                  "health": 100.0, "pos": (0.0, 0.0)}},
                  "pos": (0.0, 0.0), "player_health": 100.0}
            authsrv.begin_attack(send, st, 10, 0)
            authsrv.attack_tick(send, st, 0)                    # the start: windup open
            if not in_windup:
                st["player_swing"]["lands_at"] = 0.0           # due: the next tick lands it
                authsrv.attack_tick(send, st, 0)
            authsrv.kill_player(send, st, 0)
            rec.meta.close()
            rec.raw.close()
            flags, ev = load(rec.meta.name)
            ds = deaths(ev)
            out[conn] = (arm_of(flags), [(dd["open"], dd["stop"], verdict(dd, arm_of(flags))) for dd in ds])
    finally:
        (authsrv.DEATH_STOPS_WINDUP, authsrv.ATTACK_APPROACH) = saved
        shutil.rmtree(tmp, ignore_errors=True)
    ck(out[81] == ("fixed", [(True, True, "PASS")]),
       "fixed arm, death in the windup: [3] in the KILL's batch -> PASS", str(out[81]))
    ck(out[82] == ("known-bad", [(True, False, "old-shape")]),
       "known-bad arm (--death-keeps-windup): no [3] -> old-shape", str(out[82]))
    ck(out[83] == ("fixed", [(False, False, "control-ok")]),
       "fixed arm, death after the landing: no [3] -> control-ok", str(out[83]))

    print("== 4. the real corpus: the pre-fix deaths are the old shape ==")
    paths = sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", "authsrv-202609[23]*-c*.jsonl"))
                   + glob.glob(vaultpath.vault_path("captures", "gamesrv", "authsrv-202610*-c*.jsonl")))
    if not paths:
        print("  [SKIP] no gamesrv corpus (bare machine)")
    else:
        by = score(paths, quiet=True)
        pre = by.get("pre-fix", [])
        vs = {}
        for _p, _d, v in pre:
            vs[v] = vs.get(v, 0) + 1
        n_open = sum(1 for _p, d, _v in pre if d["open"])
        ck(len(pre) >= 80 and n_open >= 1 and vs.get("UNEXPECTED", 0) == 0
           and vs.get("CONTROL-FAIL", 0) == 0,
           "every pre-fix player death since 09-20 is old-shape or a clean control (the census: 89 "
           "deaths on 33 tapes before 1z-ds.27)", f"{len(pre)} deaths, {n_open} open, {vs}")
    print("SELFTEST", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return selftest()
    if argv[0] == "--corpus":
        paths = sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", "authsrv-202609[23]*-c*.jsonl"))
                       + glob.glob(vaultpath.vault_path("captures", "gamesrv", "authsrv-202610*-c*.jsonl")))
        print(summary(score(paths, quiet=True)))
        return 0
    paths = [p for a in argv for p in tapes_for(a)]
    if not paths:
        print("no tapes for", argv)
        return 2
    print(summary(score(paths)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
