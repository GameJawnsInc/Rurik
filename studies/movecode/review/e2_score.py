#!/usr/bin/env python3
"""DEATHWALK-E2's scorer: after the player RISES IN PLACE, does the first attack press re-pin the
body on the walk the death cut short? (SHRINEWARP 1z-dp.4 / 1z-dp.5, RISE_ENDS_LEGS;
`--rise-keeps-legs` reverts.)

    python studies/movecode/review/e2_score.py STAMP [STAMP ...]   # gamesrv capture stamps (all -cN)
    python studies/movecode/review/e2_score.py --corpus            # every tape since 2026-09-20
    python studies/movecode/review/e2_score.py --selftest          # no run needed; ~3 s

THE DEFECT. A corpse sends no movement report, so the click latch and leg a walk left behind
outlive the death. When a hero's signet or the timer stands the player up WHERE IT FELL, the
first client press (0x0026) reaches `_press_supersedes` / `_press_stops_body`, finds a click "in
flight" and re-pins the body on the stale leg: a player 0x002C labelled `PRESS ENDS THE WALK` or
`PRESS STOP PIN`. That is a warp of the leg's remainder, zero if the leg had arrived; the 0x002C is
on the wire either way. D3's fix retires the latch at the rise, so the press finds nothing in flight.

ONLY A CLIENT PRESS EXERCISES IT. The harness's `attack:N` mailbox calls `begin_attack` alone and
never `_press_supersedes`, so a run scored here must press on the client (C + space), and a rise
counts only when a decoded c2s 0x0026 follows it.

READ OFF THE TAPE, per rise:
  rise     = sent 0x00F1 [1, word], the word LOSING 0x10
  shrine   = a player 0x002C labelled "the wipe:" within 1 s before it (the wipe's placement,
             fixed separately by 1z-dp.3) -- reported, not judged
  window   = from the rise to the first client movement report (decoded c2s 0x003D, 0x0047 or
             0x003E -- any one ends the latch), the next death, or 30 s
  exposed  = a client press (decoded c2s 0x0026) inside the window
  re-pin   = a player 0x002C labelled PRESS ENDS THE WALK / PRESS STOP PIN after that press, in it

THE ARM IS READ OFF THE TAPE: flags RISE_ENDS_LEGS true = "fixed", false = "known-bad", absent =
a build before D3 ("pre-D3", the known-bad behaviour).

VERDICTS, one per exposed in-place rise:
  fixed            PASS if no re-pin, FAIL if one
  known-bad/pre-D3 old-shape if a re-pin, no-repin if none (the latch was not set: no exposure
                   to the defect itself)
FLOORS (E2): 5 exposed in-place rises on the fixed arm; on the known-bad arm, 5 exposed and at
least one old-shape (the positive control that the plan reaches the defect).
"""
import glob
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import vaultpath  # noqa: E402

ME = 1
OP_STATUS, OP_POS = 0xF1, 0x2C
C_PRESS = 0x26
C_MOVE = (0x3D, 0x47, 0x3E)
DEAD_BIT = 0x10
WINDOW = 30.0
FLOOR = 5
STALE = ("PRESS ENDS THE WALK", "PRESS STOP PIN")
OPRE = re.compile(r'"opcode": (\d+)')


def load(path):
    """(flags, events): t, k in DEAD / RISE / WIPE / REPIN / PRESS / MOVE."""
    ev, flags, word = [], {}, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not flags and '"kind": "flags"' in line:
                try:
                    flags = json.loads(line)
                except ValueError:
                    flags = {}
                continue
            m = OPRE.search(line)
            if not m:
                continue
            op = int(m.group(1))
            if '"kind": "sent"' in line and op in (OP_STATUS, OP_POS):
                r = json.loads(line)
                b = bytes.fromhex(r.get("plain") or "")
                lab = r.get("label") or ""
                try:
                    if op == OP_STATUS:
                        _o, ag, w = struct.unpack_from("<HII", b, 0)
                        if ag == ME:
                            if (w & DEAD_BIT) and not (word & DEAD_BIT):
                                ev.append({"t": r["t"], "k": "DEAD"})
                            elif (word & DEAD_BIT) and not (w & DEAD_BIT):
                                ev.append({"t": r["t"], "k": "RISE"})
                            word = w
                    else:
                        _o, ag = struct.unpack_from("<HI", b, 0)
                        if ag == ME:
                            if lab.startswith("the wipe:"):
                                ev.append({"t": r["t"], "k": "WIPE"})
                            elif lab.startswith(STALE):
                                ev.append({"t": r["t"], "k": "REPIN", "lab": lab[:80]})
                except struct.error:
                    continue
            elif '"kind": "decoded"' in line and (op == C_PRESS or op in C_MOVE):
                r = json.loads(line)
                ev.append({"t": r["t"], "k": "PRESS" if op == C_PRESS else "MOVE"})
    ev.sort(key=lambda e: e["t"])
    return flags, ev


def arm_of(flags):
    if "RISE_ENDS_LEGS" not in flags:
        return "pre-D3"
    return "fixed" if flags["RISE_ENDS_LEGS"] else "known-bad"


def rises(ev):
    """[{t, shrine, exposed, repin}] per rise."""
    out = []
    for j, e in enumerate(ev):
        if e["k"] != "RISE":
            continue
        shrine = any(x["k"] == "WIPE" and 0.0 <= e["t"] - x["t"] <= 1.0 for x in ev[max(0, j - 40):j])
        press_t, repin = None, None
        for x in ev[j + 1:]:
            if x["t"] - e["t"] > WINDOW or x["k"] in ("MOVE", "DEAD"):
                break
            if x["k"] == "PRESS" and press_t is None:
                press_t = x["t"]
            elif x["k"] == "REPIN" and press_t is not None and repin is None:
                repin = (round(x["t"] - press_t, 3), x["lab"])
        out.append({"t": e["t"], "shrine": shrine, "exposed": press_t is not None,
                    "press_after": None if press_t is None else round(press_t - e["t"], 3),
                    "repin": repin})
    return out


def verdict(r, arm):
    if r["shrine"]:
        return "shrine"
    if not r["exposed"]:
        return "unexposed"
    if arm == "fixed":
        return "FAIL" if r["repin"] else "PASS"
    return "old-shape" if r["repin"] else "no-repin"


def tapes_for(arg):
    if os.path.isfile(arg):
        return [arg]
    return sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", f"authsrv-{arg}-c*.jsonl")))


def corpus_paths():
    return sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", "authsrv-202609[23]*-c*.jsonl"))
                  + glob.glob(vaultpath.vault_path("captures", "gamesrv", "authsrv-202610*-c*.jsonl")))


def score(paths, quiet=False):
    by = {}
    for p in paths:
        flags, ev = load(p)
        arm = arm_of(flags)
        for r in rises(ev):
            v = verdict(r, arm)
            by.setdefault(arm, []).append((p, r, v))
            if not quiet and v not in ("unexposed",):
                print(f"  {os.path.basename(p)} rise t={r['t']:.3f} [{arm}] "
                      f"{'SHRINE' if r['shrine'] else 'in place'} press +{r['press_after']} "
                      f"-> {v}" + (f"  re-pin +{r['repin'][0]}s: {r['repin'][1]}" if r["repin"] else ""))
    return by


def summary(by):
    lines = []
    for arm, rows in sorted(by.items()):
        vs = {}
        for _p, _r, v in rows:
            vs[v] = vs.get(v, 0) + 1
        exposed = sum(n for v, n in vs.items() if v in ("PASS", "FAIL", "old-shape", "no-repin"))
        short = exposed < FLOOR or (arm != "fixed" and not vs.get("old-shape"))
        lines.append(f"[{arm}] rises {len(rows)}, exposed in place {exposed}"
                     + (f" (UNEXPOSED: floor {FLOOR}" + ("" if arm == "fixed" else ", and >= 1 old-shape")
                        + ")" if short else "") + f"  {vs}")
    return "\n".join(lines)


def selftest():
    import authsrv
    import leadgeom
    bad = 0

    def ck(ok, what, detail=""):
        nonlocal bad
        print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
        bad += 0 if ok else 1

    print("== 1. the opcodes are the server's ==")
    ck(authsrv.GAME_SMSG_AGENT_UPDATE_STATUS == OP_STATUS
       and authsrv.GAME_SMSG_AGENT_UPDATE_POSITION == OP_POS
       and authsrv.GAME_CMSG_ATTACK_AGENT == C_PRESS and authsrv.agents.EFFECT_DEAD == DEAD_BIT,
       "0xF1 / 0x2C, c2s 0x0026 and the dead bit match authsrv")

    print("== 2. synthetic events ==")
    base = [{"t": 0.0, "k": "DEAD"}, {"t": 10.0, "k": "RISE"}, {"t": 12.0, "k": "PRESS"}]
    r = rises(base + [{"t": 12.001, "k": "REPIN", "lab": "PRESS ENDS THE WALK"}])[0]
    ck(r["exposed"] and r["repin"] and verdict(r, "fixed") == "FAIL" and verdict(r, "pre-D3") == "old-shape",
       "an in-place rise, a press, a stale re-pin: fixed FAIL, pre-D3 old-shape")
    r = rises(base)[0]
    ck(verdict(r, "fixed") == "PASS" and verdict(r, "known-bad") == "no-repin",
       "no re-pin after the press: fixed PASS, known-bad no-repin")
    r = rises([{"t": 0.0, "k": "DEAD"}, {"t": 10.0, "k": "RISE"}, {"t": 11.0, "k": "MOVE"},
               {"t": 12.0, "k": "PRESS"}, {"t": 12.001, "k": "REPIN", "lab": "PRESS ENDS THE WALK"}])[0]
    ck(not r["exposed"] and verdict(r, "fixed") == "unexposed",
       "a movement report before the press ends the window (the client re-stamped the latch)")
    r = rises([{"t": 9.95, "k": "WIPE"}, {"t": 10.0, "k": "RISE"}, {"t": 12.0, "k": "PRESS"}])[0]
    ck(r["shrine"] and verdict(r, "fixed") == "shrine", "a wipe's placement just before the rise: shrine")
    r = rises([{"t": 10.0, "k": "RISE"}, {"t": 11.0, "k": "REPIN", "lab": "PRESS STOP PIN"},
               {"t": 12.0, "k": "PRESS"}])[0]
    ck(r["repin"] is None, "a re-pin BEFORE the client's press is not the press's")

    print("== 3. tapes written by the REAL revive_player and the REAL press path, both arms ==")
    tmp = tempfile.mkdtemp(prefix="e2score-")
    saved = authsrv.RISE_ENDS_LEGS
    out = {}
    try:
        for conn, on in ((71, True), (72, False)):
            authsrv.RISE_ENDS_LEGS = on
            rec = authsrv.Recorder(tmp, conn)
            seq = [0]

            def send(op, vals, label="", quiet=False, rec=rec, seq=seq):
                seq[0] += 1
                rec.event("sent", seq=seq[0], opcode=op, label=label,
                          plain=authsrv.codec.encode("GAME_SMSG", op, vals).hex())
            now = time.time()
            leg = leadgeom._leg_record((0.0, 0.0), (1000.0, 0.0), now - 20.0, 288.0)
            foe = {"name": "raider", "dead": False, "died_at": 0.0, "health": 3000.0,
                   "max_health": 3000.0, "last_hit": 0.0, "pos": (1300.0, 0.0), "plane": 0,
                   "allegiance": authsrv.agents.ALLEGIANCE_HOSTILE, "effects": 0,
                   "attacks_back": True, "skills": (), "skill_ready": [],
                   "npc": {"level": 10, "profession": 1}}
            st = {"agents": {110: foe}, "pos": (288.0, 0.0), "plane": 0, "dest": None,
                  "click_moving_at": leg["t0"], "click_leg": leg, "client_pos": (0.0, 0.0),
                  "client_plane": 0, "client_pos_at": now - 20.5, "player_health": 100.0}
            authsrv.kill_player(send, st, 0)                     # the death, on the wire
            authsrv.revive_player(send, st, 0, why=" (a hero's signet)")   # in place
            rec.event("decoded", opcode=C_PRESS, name="ATTACK_AGENT", values=[C_PRESS, 110])
            authsrv._press_supersedes(send, st, 0, 110)          # the 0x0026 arm's call
            rec.meta.close()
            rec.raw.close()
            flags, ev = load(rec.meta.name)
            rs = rises(ev)
            out[conn] = (arm_of(flags), [(rr["shrine"], rr["exposed"], bool(rr["repin"]),
                                          verdict(rr, arm_of(flags))) for rr in rs])
    finally:
        authsrv.RISE_ENDS_LEGS = saved
        shutil.rmtree(tmp, ignore_errors=True)
    ck(out[71] == ("fixed", [(False, True, False, "PASS")]),
       "fixed arm: a mid-walk death, the rise in place, a client press -> no stale 0x002C, PASS",
       str(out[71]))
    ck(out[72] == ("known-bad", [(False, True, True, "old-shape")]),
       "known-bad arm (--rise-keeps-legs): the press re-pins on the stale leg -> old-shape", str(out[72]))

    print("== 4. the real corpus: pre-D3 rises read the old shape where the defect was reachable ==")
    paths = corpus_paths()
    if not paths:
        print("  [SKIP] no gamesrv corpus (bare machine)")
    else:
        by = score(paths, quiet=True)
        pre = by.get("pre-D3", [])
        vs = {}
        for _p, _r, v in pre:
            vs[v] = vs.get(v, 0) + 1
        ck(len(pre) >= 75 and vs.get("FAIL", 0) == 0 and vs.get("PASS", 0) == 0,
           "every pre-D3 rise is shrine / unexposed / old-shape / no-repin -- never judged as the fixed "
           "arm (the census: 81 rises)", f"{len(pre)} rises, {vs}")
    print("SELFTEST", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return selftest()
    if argv[0] == "--corpus":
        print(summary(score(corpus_paths(), quiet=False)))
        return 0
    paths = [p for a in argv for p in tapes_for(a)]
    if not paths:
        print("no tapes for", argv)
        return 2
    print(summary(score(paths)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
