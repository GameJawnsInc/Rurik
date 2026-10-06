#!/usr/bin/env python3
"""DEATHWALK-E5's scorer: every death of the player's chain TARGET on our own tapes, by cell,
and whether the hold's release came the way DEATHWALK-D4 says it must.

    python studies/movecode/review/e5_score.py STAMP [STAMP ...]   # gamesrv capture stamps (all -cN files)
    python studies/movecode/review/e5_score.py path/to/authsrv-...-c1.jsonl
    python studies/movecode/review/e5_score.py --check STAMP       # between launches: exit 3 = STOP
    python studies/movecode/review/e5_score.py --selftest          # no run needed; ~5 s

THE RULE BEING SCORED (FINDINGS 1z-ds.50 / 1z-ds.52). At the chain target's death nothing is
released. With the player's swing IN FLIGHT the release is [8, me, 0] then [3, me, 0] in one
batch at the swing's due landing, and the swing's landing never comes. Otherwise it is
[8, me, 0] alone at the chain's next due start. An input before then releases through its own
door. The known-bad arm (`--target-death-releases-now`, and every build before D4) sends
[8, me, 0] on the next tick with no [3].

THE CELL IS READ OFF THE WIRE, not off our own labels. Our tape is the send order:
  start   = sent 0x00A0 [4, 1, T]          the chain's target is the last start's T
  landing = sent 0x009F [1, 1, *] or 0x00A4 [1]
  stop    = sent 0x009F [3, 1, 0]
  hold    = sent 0x009F [8, 1, v]
  death   = sent 0x00F1 [A, word], the word GAINING 0x10
  inputs  = decoded c2s 0x26 0x27 0x46 0x3D(moving) 0x3E 0x47 0x28 0x39
A death is IN FLIGHT when the chain's last start has no landing and no stop before it. The
EXPECTED instant is computed from the wire too: the start plus the windup this chain's own
previous swing showed (else the tape's median windup); or the last start plus the chain's own
start-to-start gap (else the tape's median gap). Never before the death itself. Our own rows
(`swing_verdict` held_to / lands_in, `target_death_release`) are printed beside the verdict
as a cross-check, and are only an expectation's source when the wire has none ("row").

THE ARM IS READ OFF THE TAPE: the `flags` row's TARGET_DEATH_HOLDS (true = D4, false = the
known-bad arm, absent = a build before D4). A label on the command line cannot mislabel a tape.

VERDICTS, one per chain-target death:
  PASS / FAIL         D4 arm: the batch is right ([8, 0] then [3] in flight; [8, 0] alone
                      otherwise), no landing after the death, and the release within TOL of
                      its expected instant
  old-shape           known-bad or pre-D4 arm: [8, 0] within TOL of the death, no [3]
  UNEXPECTED          known-bad or pre-D4 arm, anything else
  input-first         an input came between the death and the release: that door's release,
                      reported and not judged (retail's third cell)
  hold-down           the hold was already down at the death: nothing to release (D4 keeps
                      the old silent drop; RECONSTRUCTION)
  NO-RELEASE          no [8, 0] within 4 s

FLOORS (E5, registered in RUN-DEATHWALK): 5 in-flight and 5 next-start deaths per arm. An arm
below its floor is UNEXPOSED, not a null. TOL = 0.06 s: the world tick is 50 ms, and the D4
release rides the combat-deadline pass, so it should land well inside it.
"""
import glob
import shutil
import json
import os
import re
import statistics
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
sys.path.insert(0, HERE)
import vaultpath  # noqa: E402

ME = 1
OP_INT, OP_INT_TARGET, OP_LAND, OP_STATUS = 0x9F, 0xA0, 0xA4, 0xF1
P_LAND, P_STOP, P_START, P_HOLD = 1, 3, 4, 8
DEAD_BIT = 0x10
C2S = {0x26: "press", 0x27: "skill", 0x46: "skill", 0x3D: "move", 0x3E: "click",
       0x47: "stop", 0x28: "cancel", 0x39: "interact"}
TOL = 0.06          # s: "at its instant"
BATCH = 0.005       # s: one batch
HORIZON = 4.0       # s: look this far past a death for its release
FLOOR = 5           # per cell per arm
OPRE = re.compile(r'"opcode": (\d+)')


# ---------------------------------------------------------------------------- reading a tape
def load(path):
    """(flags, events) from one gamesrv capture. events: dicts with t, k, a, lab (and row)."""
    ev, words, flags = [], {}, None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if flags is None and '"kind": "flags"' in line:
                try:
                    flags = json.loads(line)
                except ValueError:
                    flags = {}
                continue
            if '"kind": "swing_verdict"' in line or '"kind": "target_death_release"' in line:
                r = json.loads(line)
                ev.append({"t": r["t"], "k": "SV" if r["kind"] == "swing_verdict" else "TDR",
                           "a": None, "lab": "", "row": r})
                continue
            m = OPRE.search(line)
            if not m:
                continue
            op = int(m.group(1))
            if '"kind": "sent"' in line:
                if op not in (OP_INT, OP_INT_TARGET, OP_LAND, OP_STATUS):
                    continue
                r = json.loads(line)
                e = decode_sent(op, bytes.fromhex(r.get("plain") or ""), words)
                if e is not None:
                    e.update(t=r["t"], lab=r.get("label") or "")
                    ev.append(e)
            elif '"kind": "decoded"' in line and op in C2S:
                r = json.loads(line)
                if r.get("dir", "c2s") != "c2s":
                    continue
                v = r.get("values") or []
                if C2S[op] == "move" and not (len(v) > 4 and v[4]):
                    continue          # a still heading report is not an input
                ev.append({"t": r["t"], "k": "IN", "a": C2S[op], "lab": ""})
    ev.sort(key=lambda e: e["t"])
    return flags or {}, ev


def decode_sent(op, b, words):
    try:
        if op == OP_INT:
            _o, p, ag, val = struct.unpack_from("<HIII", b, 0)
            if ag == ME and p in (P_LAND, P_STOP, P_HOLD):
                return {"k": {P_LAND: "LAND", P_STOP: "ST3", P_HOLD: "H"}[p], "a": val}
        elif op == OP_INT_TARGET:
            _o, p, ag, tg = struct.unpack_from("<HIII", b, 0)
            if ag == ME and p == P_START:
                return {"k": "S4", "a": tg}
        elif op == OP_LAND:
            _o, ag = struct.unpack_from("<HI", b, 0)
            if ag == ME:
                return {"k": "LAND", "a": None}
        elif op == OP_STATUS:
            _o, ag, w = struct.unpack_from("<HII", b, 0)
            prev = words.get(ag, 0)
            words[ag] = w
            if (w & DEAD_BIT) and not (prev & DEAD_BIT):
                return {"k": "DEAD", "a": ag}
    except struct.error:
        return None
    return None


def arm_of(flags):
    if "TARGET_DEATH_HOLDS" not in flags:
        return "pre-D4"
    return "D4" if flags["TARGET_DEATH_HOLDS"] else "known-bad"


# ---------------------------------------------------------------------------- the deaths
def tape_medians(ev):
    """(median windup, median start-to-start gap) over the whole tape, or None each."""
    winds, gaps, last, prev_t = [], [], None, None
    for e in ev:
        if e["k"] == "S4":
            if prev_t is not None and 0.3 < e["t"] - prev_t < 3.0:
                gaps.append(e["t"] - prev_t)
            prev_t = e["t"]
            last = e["t"]
        elif e["k"] == "LAND" and last is not None:
            if 0.05 < e["t"] - last < 2.0:
                winds.append(e["t"] - last)
            last = None
    return (statistics.median(winds) if winds else None,
            statistics.median(gaps) if gaps else None)


def deaths(ev):
    """One dict per death of the chain target, with its cell, expectation and observation."""
    med_wind, med_gap = tape_medians(ev)
    out, hold, cur, chain = [], 0, None, {}
    for j, e in enumerate(ev):
        k = e["k"]
        if k == "H":
            hold = e["a"]
        elif k == "S4":
            prev = cur if (cur is not None and cur["tgt"] == e["a"]) else None
            cur = {"t": e["t"], "tgt": e["a"], "closed": None, "scored": False,
                   "gap": (e["t"] - prev["t"]) if prev and 0.3 < e["t"] - prev["t"] < 3.0
                   else chain.get(e["a"], {}).get("gap"),
                   "wind": chain.get(e["a"], {}).get("wind")}
        elif k in ("LAND", "ST3") and cur is not None and cur["closed"] is None:
            cur["closed"] = k
            if k == "LAND":
                chain.setdefault(cur["tgt"], {})["wind"] = e["t"] - cur["t"]
            if cur.get("gap"):
                chain.setdefault(cur["tgt"], {})["gap"] = cur["gap"]
        if k != "DEAD" or cur is None or e["a"] != cur["tgt"] or cur["scored"]:
            continue
        cur["scored"] = True
        t = e["t"]
        in_flight = cur["closed"] is None
        if in_flight:
            wind, src = ((cur["wind"], "chain") if cur["wind"] else
                         (med_wind, "tape") if med_wind else (None, None))
            exp = None if wind is None else cur["t"] + wind
        else:
            gap, src = ((cur["gap"], "chain") if cur["gap"] else
                        (med_gap, "tape") if med_gap else (None, None))
            exp = None if gap is None else cur["t"] + gap
        d = {"t": t, "tgt": e["a"], "hold": hold, "in_flight": in_flight,
             "into": round(t - cur["t"], 3), "exp": exp, "exp_src": src,
             "rel": None, "batch": [], "inp": None, "land_after": False,
             "sv": None, "tdr": None}
        for e2 in ev[j + 1:]:
            if e2["t"] - t > HORIZON:
                break
            if e2["k"] == "SV" and d["sv"] is None and e2["t"] - t <= 0.1:
                d["sv"] = e2["row"]
            if e2["k"] == "TDR" and d["tdr"] is None:
                d["tdr"] = e2["row"]
            if d["rel"] is None:
                if e2["k"] == "IN" and d["inp"] is None:
                    d["inp"] = (e2["a"], round(e2["t"] - t, 3))
                if e2["k"] == "LAND":
                    d["land_after"] = True
                if e2["k"] == "H" and e2["a"] == 0:
                    d["rel"] = e2["t"]
            if d["rel"] is not None and abs(e2["t"] - d["rel"]) <= BATCH and e2["k"] in ("H", "ST3"):
                d["batch"].append(f"{e2['k']}:{e2['a']}")
        if d["exp"] is None and d["sv"] and d["in_flight"] and d["sv"].get("lands_in") is not None:
            d["exp"], d["exp_src"] = d["sv"]["t"] + float(d["sv"]["lands_in"]), "row"
        if d["exp"] is not None:
            d["exp"] = max(t, d["exp"])
        out.append(d)
    return out


def verdict(d, arm):
    if d["hold"] != 1:
        return "hold-down"
    if d["inp"] is not None:
        return "input-first"
    if d["rel"] is None:
        return "NO-RELEASE"
    stop = "ST3:0" in d["batch"]
    if arm != "D4":
        return "old-shape" if (d["rel"] - d["t"] <= TOL and not stop) else "UNEXPECTED"
    if d["exp"] is None:
        return "FAIL"
    on_time = abs(d["rel"] - d["exp"]) <= TOL
    if d["in_flight"]:
        ok = on_time and d["batch"][:2] == ["H:0", "ST3:0"] and not d["land_after"]
    else:
        ok = on_time and not stop
    return "PASS" if ok else "FAIL"


def cell(d):
    return "in-flight" if d["in_flight"] else "next-start"


# ---------------------------------------------------------------------------- the report
def tapes_for(arg):
    if os.path.isfile(arg):
        return [arg]
    return sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", f"authsrv-{arg}-c*.jsonl")))


def score(paths, quiet=False):
    """{arm: [(path, death, verdict)]}"""
    by_arm = {}
    for p in paths:
        flags, ev = load(p)
        arm = arm_of(flags)
        for d in deaths(ev):
            v = verdict(d, arm)
            by_arm.setdefault(arm, []).append((p, d, v))
            if not quiet:
                lag = None if d["rel"] is None else d["rel"] - d["t"]
                err = (None if d["rel"] is None or d["exp"] is None else d["rel"] - d["exp"])
                print(f"  {os.path.basename(p)} t={d['t']:.3f} tgt {d['tgt']} [{arm}] {cell(d):10s} "
                      f"into {d['into']:.3f} hold {d['hold']} -> {v:11s} "
                      f"lag {'-' if lag is None else f'{lag:.3f}'} "
                      f"err {'-' if err is None else f'{err:+.3f}'} ({d['exp_src']}) "
                      f"batch {d['batch']}"
                      + (f" input {d['inp']}" if d["inp"] else "")
                      + (f" | row held_to {d['sv'].get('held_to')}" if d["sv"] else "")
                      + (f" tdr {d['tdr'].get('cell')} late {d['tdr'].get('late')}" if d["tdr"] else ""))
    return by_arm


def summary(by_arm):
    lines = []
    for arm, rows in sorted(by_arm.items()):
        lines.append(f"[{arm}] chain-target deaths {len(rows)}")
        for c in ("in-flight", "next-start"):
            rs = [(d, v) for _p, d, v in rows if cell(d) == c]
            judged = [v for d, v in rs if v in ("PASS", "FAIL", "old-shape", "UNEXPECTED")]
            vs = {}
            for _d, v in rs:
                vs[v] = vs.get(v, 0) + 1
            errs = [d["rel"] - d["exp"] for d, v in rs if v in ("PASS", "FAIL")
                    and d["rel"] is not None and d["exp"] is not None]
            exposed = len(judged) >= FLOOR
            lines.append(f"   {c:10s} n {len(rs)}, judged {len(judged)} "
                         f"{'' if exposed else '(UNEXPOSED: floor ' + str(FLOOR) + ')'} {vs}"
                         + (f"  err p50 {statistics.median(errs):+.3f} max |{max(abs(x) for x in errs):.3f}|"
                            if errs else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------- the selftest
def _synth(events):
    return sorted(({"lab": "", **e} for e in events), key=lambda e: e["t"])


def selftest():
    import authsrv
    bad = 0

    def ck(ok, what, detail=""):
        nonlocal bad
        print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
        bad += 0 if ok else 1

    print("== 1. the scorer's opcodes and props are the server's ==")
    ck(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT == OP_INT
       and authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET == OP_INT_TARGET
       and authsrv.GAME_SMSG_AGENT_UPDATE_STATUS == OP_STATUS
       and authsrv.agents.GV_ATTACK_STOPPED == P_STOP and authsrv.agents.GV_DISABLED == P_HOLD
       and authsrv.agents.GV_ATTACK_STARTED == P_START
       and authsrv.agents.GV_MELEE_ATTACK_FINISHED == P_LAND
       and authsrv.agents.EFFECT_DEAD == DEAD_BIT,
       "0x9F / 0xA0 / 0xF1, props 1 / 3 / 4 / 8 and the dead bit match authsrv")

    print("== 2. synthetic events: every verdict reachable, each the right one ==")
    base = [{"t": 0.0, "k": "S4", "a": 10}, {"t": 0.001, "k": "H", "a": 1},
            {"t": 0.5, "k": "LAND", "a": 0}, {"t": 1.33, "k": "S4", "a": 10}]
    inflight = base + [{"t": 1.5, "k": "DEAD", "a": 10},
                       {"t": 1.83, "k": "H", "a": 0}, {"t": 1.831, "k": "ST3", "a": 0}]
    ds = deaths(_synth(inflight))
    ck(len(ds) == 1 and ds[0]["in_flight"] and abs(ds[0]["exp"] - 1.83) < 1e-9
       and ds[0]["exp_src"] == "chain" and verdict(ds[0], "D4") == "PASS",
       "in flight: expected at start + this chain's own windup (1.33 + 0.5), [8, 0] [3] -> PASS",
       str(ds and (ds[0]["exp"], ds[0]["batch"])))
    no3 = base + [{"t": 1.5, "k": "DEAD", "a": 10}, {"t": 1.83, "k": "H", "a": 0}]
    ck(verdict(deaths(_synth(no3))[0], "D4") == "FAIL", "in flight with no [3] -> FAIL")
    early = base + [{"t": 1.5, "k": "DEAD", "a": 10},
                    {"t": 1.55, "k": "H", "a": 0}, {"t": 1.551, "k": "ST3", "a": 0}]
    ck(verdict(deaths(_synth(early))[0], "D4") == "FAIL",
       "in flight released on the next tick (the old timing) under D4 -> FAIL")
    landed = base + [{"t": 1.5, "k": "DEAD", "a": 10}, {"t": 1.83, "k": "LAND", "a": 0},
                     {"t": 1.84, "k": "H", "a": 0}, {"t": 1.841, "k": "ST3", "a": 0}]
    ck(verdict(deaths(_synth(landed))[0], "D4") == "FAIL",
       "a landing after the death -> FAIL (retail: the [1] never comes)")
    gap = base[:3] + [{"t": 0.9, "k": "DEAD", "a": 10}, {"t": 1.33, "k": "H", "a": 0}]
    dg = deaths(_synth(gap))
    ck(len(dg) == 1 and not dg[0]["in_flight"] and dg[0]["exp"] is None,
       "not in flight with one start and no tape gap: no wire expectation", str(dg and dg[0]["exp"]))
    gap2 = [{"t": -1.33, "k": "S4", "a": 10}, {"t": -0.83, "k": "LAND", "a": 0}] + gap
    dg2 = deaths(_synth(gap2))
    ck(abs(dg2[0]["exp"] - 1.33) < 1e-9 and dg2[0]["exp_src"] == "chain"
       and verdict(dg2[0], "D4") == "PASS",
       "not in flight: expected at the last start + the chain's own gap -> [8, 0] alone PASS",
       str((dg2[0]["exp"], dg2[0]["batch"])))
    gap3 = gap2[:-1] + [{"t": 1.33, "k": "H", "a": 0}, {"t": 1.331, "k": "ST3", "a": 0}]
    ck(verdict(deaths(_synth(gap3))[0], "D4") == "FAIL", "not in flight WITH a [3] -> FAIL")
    old = base + [{"t": 1.5, "k": "DEAD", "a": 10}, {"t": 1.55, "k": "H", "a": 0}]
    ck(verdict(deaths(_synth(old))[0], "known-bad") == "old-shape"
       and verdict(deaths(_synth(inflight))[0], "known-bad") == "UNEXPECTED",
       "known-bad arm: the next tick's [8, 0] is old-shape; D4's shape there is UNEXPECTED")
    inp = base + [{"t": 1.5, "k": "DEAD", "a": 10}, {"t": 1.6, "k": "IN", "a": "move"},
                  {"t": 1.6, "k": "H", "a": 0}, {"t": 1.601, "k": "ST3", "a": 0}]
    ck(verdict(deaths(_synth(inp))[0], "D4") == "input-first", "a move before the release -> input-first")
    down = [{"t": 0.0, "k": "S4", "a": 10}, {"t": 0.2, "k": "DEAD", "a": 10}]
    ck(verdict(deaths(_synth(down))[0], "D4") == "hold-down", "the hold never raised -> hold-down")
    other = base + [{"t": 1.5, "k": "DEAD", "a": 99}]
    ck(deaths(_synth(other)) == [], "a death of an agent that is not the chain's target is not scored")
    none = base + [{"t": 1.5, "k": "DEAD", "a": 10}]
    ck(verdict(deaths(_synth(none))[0], "D4") == "NO-RELEASE", "no release within the horizon -> NO-RELEASE")

    print("== 3. real tapes written by the REAL server code, both arms ==")
    tmp = tempfile.mkdtemp(prefix="e5score-")
    saved = (authsrv.TARGET_DEATH_HOLDS, authsrv.ATTACK_APPROACH, authsrv.ATTACK_INTERVAL)
    authsrv.ATTACK_APPROACH = False
    authsrv.ATTACK_INTERVAL = 0.6          # a short chain, so the selftest takes seconds

    def tape(conn, on, kill_in_flight):
        authsrv.TARGET_DEATH_HOLDS = on
        rec = authsrv.Recorder(tmp, conn)
        seq = [0]

        def send(op, vals, label="", quiet=False):
            blob = authsrv.codec.encode("GAME_SMSG", op, vals)
            seq[0] += 1
            rec.event("sent", seq=seq[0], opcode=op, label=label, plain=blob.hex())
        agent = {"name": "target", "dead": False, "last_hit": 0.0, "max_health": 100.0,
                 "health": 100.0, "pos": (0.0, 0.0)}
        st = {"agents": {10: agent}, "pos": (0.0, 0.0)}
        authsrv.begin_attack(send, st, 10, 0)

        def run_until(pred, limit):
            end = time.time() + limit
            while time.time() < end:
                authsrv.attack_tick(send, st, 0, rec=rec)
                if pred():
                    return True
                time.sleep(0.005)
            return False
        run_until(lambda: st.get("player_swing") is not None, 0.5)          # start 1
        run_until(lambda: st.get("player_swing") is None, 1.0)              # landing 1
        run_until(lambda: st.get("player_swing") is not None, 1.0)          # start 2
        if not kill_in_flight:
            run_until(lambda: st.get("player_swing") is None, 1.0)          # landing 2
            time.sleep(0.1)
        else:
            time.sleep(0.08)
        authsrv.kill_agent(send, st, 10, agent, 0, time.time(), reward=False)
        released = run_until(lambda: st.get("target_death_release") is None
                             and st.get("action_hold") == 0, 1.5)
        rec.meta.close()
        rec.raw.close()
        return rec.meta.name, released

    try:
        p_in, ok_in = tape(91, True, True)
        p_gap, ok_gap = tape(92, True, False)
        p_bad, ok_bad = tape(93, False, True)
    finally:
        (authsrv.TARGET_DEATH_HOLDS, authsrv.ATTACK_APPROACH, authsrv.ATTACK_INTERVAL) = saved
    for path, want_arm, want_cell, want_v, done in (
            (p_in, "D4", "in-flight", "PASS", ok_in),
            (p_gap, "D4", "next-start", "PASS", ok_gap),
            (p_bad, "known-bad", "in-flight", "old-shape", ok_bad)):
        flags, ev = load(path)
        ds = deaths(ev)
        got = [(arm_of(flags), cell(d), verdict(d, arm_of(flags)), d["exp_src"], d["batch"],
                None if d["rel"] is None or d["exp"] is None else round(d["rel"] - d["exp"], 3))
               for d in ds]
        ck(done and len(ds) == 1 and got[0][:3] == (want_arm, want_cell, want_v)
           and got[0][3] == "chain",
           f"{want_arm} {want_cell}: the real code's tape scores {want_v}, its expectation off "
           f"the wire (this chain's own swing)", str(got))

    shutil.rmtree(tmp, ignore_errors=True)

    print("== 4. a REAL pre-D4 tape from the vault: the old shape, read off real bytes ==")
    ctl = vaultpath.vault_path("captures", "gamesrv", "authsrv-20261001T160802-c1.jsonl")
    if not os.path.isfile(ctl):
        print("  [SKIP] no vault tape authsrv-20261001T160802-c1 (bare machine)")
    else:
        flags, ev = load(ctl)
        ds = [d for d in deaths(ev) if abs(d["t"] - 111.051) < 0.01]
        ck(arm_of(flags) == "pre-D4" and len(ds) == 1 and verdict(ds[0], "pre-D4") == "old-shape"
           and 0.0 <= ds[0]["rel"] - ds[0]["t"] <= TOL and "ST3:0" not in ds[0]["batch"],
           "20261001T160802 t=111.051 (agent 111, DEATHWALK-D2's specimen): pre-D4, [8, 0] "
           "0.003 s after the death, no [3] -> old-shape",
           str([(round(d["rel"] - d["t"], 3), d["batch"]) for d in ds if d["rel"]]))
    print("SELFTEST", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return selftest()
    check = argv[0] == "--check"
    args = argv[1:] if check else argv
    paths = [p for a in args for p in tapes_for(a)]
    if not paths:
        print("no tapes for", args)
        return 2
    by_arm = score(paths, quiet=False)
    print(summary(by_arm))
    if check and not any(by_arm.values()):
        print("STOP: no death of the player's chain target in this launch -- the rig did not "
              "produce exposure (check the heroes engaged and the plan reached the groups)")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
