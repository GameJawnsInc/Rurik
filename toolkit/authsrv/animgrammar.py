"""ANIMREF-R1: the retail attack/cast episode grammar, read off the live corpus.

The referent the arc exists to build (`studies/animref/PLAN.md` SS3 R1): every
cast episode and every auto-attack swing in every LIVE capture, extracted as a
typed, ordered, timed record -- so that our own emitter can be diffed against
the population instead of tuned by eye. The movement arc's lesson, ported:
north-star replication before synthetic tuning.

PREDICTIONS, stated before the first full run (house rule -- a probe with no
stated expectation can be rationalised into agreeing with anything):

  P-CTRL   On the two castmech captures (20260807T143055, 20260810T235916)
           this tool reproduces castgaps.py's pinned overlap figures exactly:
           7 self cast-cycles (6 complete + 1 E2-terminated), the four spell
           E5->E3 gaps in 0.74-0.77 s, the two attack-skill E5->E3 gaps at
           0.000. Run with --control to enforce; a mismatch is a defect in
           THIS tool, not news about the corpus.
  P-WINDUP Swing windup / declared interval concentrates in the 0.44-0.47
           band wherever a 0x0035 declared the attacker's speed
           (studies/combat/PLAN.md SS17b/SS19: NPC 0.4540 n=41, player n=2,
           Power Shot 0.4601/0.4595). The bench capture (20260818T132739)
           should move the PLAYER population from n=2 to n=dozens
           (CASTMECH-P6, answered from disk if the events are there).
  P-ZEROGAP Landed swings carry same-instant damage (prop 16/17, source ==
           attacker) at the FINISHED instant -- 40/40 in the measured subset;
           the corpus-wide rate is reported with its denominator, not assumed.
  EXPLORATORY (no prediction, the point is to LOOK): the other-agents' cast
           burst grammar (ANIMREF-Q1 -- does retail's non-self property-60
           carry a target? is there an 8-bracket?), death-terminated casts
           (ANIMREF-Q2), and every property id outside the known register --
           printed, never filtered (safety filters drop the anomalies).

FIELD INDEXING uses `decode_all`'s convention: THE OPCODE IS AT INDEX 0, so a
0x009F reads v[0]=159, v[1]=property, v[2]=agent, v[3]=value -- same as
adrenjoin.py, NOT the same as moralescan.py (which slices the opcode off
first; both are correct, see adrenjoin.py's block comment before "correcting"
either). 0x00A3 is [op, prop, VICTIM, SOURCE, f32] -- the victim first
(adrenjoin's reading, re-confirmed on the 2026-08-07 capture: the FINISHED
agent appears in the SOURCE slot of the same-instant damage row).

READ-ONLY over the corpus. Writes nothing unless --write, and then only under
`vault/research/animref/`. Standard library only. Times are connection-local
tape times, the same clock castgaps.py and every castmech citation use.

Origins are never pooled: this tool walks `captures/live/` ONLY. The ours-side
extraction (ANIMREF-R2, the gamesrv .jsonl corpus) is a separate entry point
that stamps its rows `ours`; a diff consumes both files and refuses two inputs
claiming the same origin root.
"""
import argparse
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

import tape          # noqa: E402
import vaultpath     # noqa: E402
from codec import Codec        # noqa: E402
from adrenjoin import whose_agent  # noqa: E402  -- prop-41 self rule, no fallback

PROP_INT = 0x009F           # [op, prop, agent, value]
PROP_INT_TARGET = 0x00A0    # [op, prop, agent, target, value]
PROP_FLOAT = 0x00A2         # [op, prop, agent, f32dw]
PROP_FLOAT_TARGET = 0x00A3  # [op, prop, victim, source, f32dw]
ATTACK_SPEED = 0x0035       # [op, agent, base_f32dw, modifier_f32dw]
AGENT_STATUS = 0x00F1       # [op, agent, status] -- death/life transitions
E_SERIES = {0x00E2: "E2", 0x00E3: "E3", 0x00E4: "E4",
            0x00E5: "E5", 0x00E6: "E6"}

# The cast/attack lifecycle register as castmech SS3c + skillcast SS15 settled
# it. Everything ELSE seen on the wire lands in the unknown-census -- printed,
# never dropped.
KNOWN_PROPS = {
    1: "melee_finished", 3: "attack_stopped", 4: "attack_started",
    6: "add_effect", 7: "remove_effect",
    8: "action_hold", 16: "damage", 17: "crit_damage", 20: "effect_on_target",
    21: "effect_on_agent", 22: "apply_animation", 23: "anim_param",
    28: "apply_animation_loop", 34: "health", 35: "interrupted",
    41: "max_energy", 42: "max_health", 44: "health_regen",
    45: "prop45", 46: "attack_skill_finished",
    48: "instant_skill", 49: "attack_skill_stopped",
    50: "cast_attack_skill", 55: "health_gain", 58: "skill_finished",
    59: "skill_stopped", 60: "cast_skill", 62: "energy_spent",
    63: "knocked_down",
}
CAST_OPEN = (60, 50)        # spell family / attack-skill family
SWING_DAMAGE = (16, 17)
CAST_TIMEOUT = 30.0         # an episode with no close inside this is censored


def f32(dw):
    """A dword reinterpreted as the float it is on the wire."""
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


def prop_events(msgs):
    """Normalise the four property channels + 0x0035 + 0x00F1 + E-series.

    Yields dicts, one per message, in stream order (which within one tape
    timestamp IS the batch order -- the decode preserves it).
    """
    for t, op, v in msgs:
        if op == PROP_INT and len(v) >= 4:
            yield {"t": t, "kind": "prop", "prop": int(v[1]),
                   "agent": int(v[2]), "target": None, "value": int(v[3])}
        elif op == PROP_INT_TARGET and len(v) >= 5:
            yield {"t": t, "kind": "prop", "prop": int(v[1]),
                   "agent": int(v[2]), "target": int(v[3]), "value": int(v[4])}
        elif op == PROP_FLOAT and len(v) >= 4:
            yield {"t": t, "kind": "prop", "prop": int(v[1]),
                   "agent": int(v[2]), "target": None, "value": f32(v[3])}
        elif op == PROP_FLOAT_TARGET and len(v) >= 5:
            # victim in the agent slot, source in the target slot -- KEEP IT.
            yield {"t": t, "kind": "prop", "prop": int(v[1]),
                   "agent": int(v[2]), "target": int(v[3]), "value": f32(v[4])}
        elif op == ATTACK_SPEED and len(v) >= 4:
            yield {"t": t, "kind": "speed", "agent": int(v[1]),
                   "base": f32(v[2]), "modifier": f32(v[3])}
        elif op == AGENT_STATUS and len(v) >= 3:
            yield {"t": t, "kind": "status", "agent": int(v[1]),
                   "value": int(v[2])}
        elif op in E_SERIES and len(v) >= 3:
            yield {"t": t, "kind": E_SERIES[op], "agent": int(v[1]),
                   "skill": int(v[2]),
                   "copy": int(v[3]) if len(v) > 3 else 0}


def token(ev):
    """One event as a compact signature token, e.g. '8:0', '60T', 'E4', 'dmg'.

    Cast opens carry a channel mark: '60T' means the property arrived on the
    TARGETED channel (0x00A0) with a non-zero target, '60' means untargeted --
    ANIMREF-Q1 is exactly whether retail's other-agent cast bursts name a
    target, so the signature must not erase the distinction.
    """
    if ev["kind"] == "prop":
        p = ev["prop"]
        if p == 8:
            return f"8:{int(ev['value'])}"
        if p in SWING_DAMAGE:
            return "dmg" if p == 16 else "crit"
        if p in CAST_OPEN and ev.get("target"):
            return f"{p}T"
        return str(p)
    if ev["kind"] == "speed":
        return "atkspeed"
    if ev["kind"] == "status":
        return f"status:{ev['value']}"
    return ev["kind"]           # E2..E6


def involves(ev, agent):
    """Does this event belong to `agent`'s episode signature?"""
    return ev.get("agent") == agent or ev.get("target") == agent


def swing_episodes(events):
    """The auto-attack state machine, per attacker.

    prop 4 opens; prop 1 closes LANDED (same-instant prop-16/17 rows whose
    SOURCE slot names the attacker are the paired damage); prop 3 closes
    STOPPED; a second prop 4 with one open closes the first REOPENED; the
    stream's end closes CENSORED. Windup ratios use the attacker's last
    declared 0x0035 (interval = base * modifier, SS17d's own arithmetic).
    """
    evs = list(events)
    by_t = collections.defaultdict(list)
    for ev in evs:
        by_t[ev["t"]].append(ev)
    speed = {}
    open_swing = {}
    out = []

    def close(attacker, t, how, damage=()):
        sw = open_swing.pop(attacker)
        sw["t_close"], sw["close"] = t, how
        sw["dt"] = None if t is None else round(t - sw["t0"], 6)
        sw["damage"] = list(damage)
        base_mod = speed.get(attacker)
        if base_mod and sw["dt"] is not None:
            interval = base_mod[0] * base_mod[1]
            sw["interval"] = round(interval, 6)
            sw["ratio"] = round(sw["dt"] / interval, 6) if interval > 0 else None
        else:
            sw["interval"] = sw["ratio"] = None
        out.append(sw)

    for ev in evs:
        if ev["kind"] == "speed":
            speed[ev["agent"]] = (ev["base"], ev["modifier"])
            continue
        if ev["kind"] != "prop":
            continue
        a = ev["agent"]
        if ev["prop"] == 4:
            if a in open_swing:
                close(a, ev["t"], "reopened")
            open_swing[a] = {"attacker": a, "victim": ev.get("target"),
                             "t0": ev["t"]}
        elif ev["prop"] == 1 and a in open_swing:
            dmg = [(d["agent"], round(d["value"], 6))
                   for d in by_t[ev["t"]]
                   if d["kind"] == "prop" and d["prop"] in SWING_DAMAGE
                   and d.get("target") == a]
            close(a, ev["t"], "landed", dmg)
        elif ev["prop"] == 3 and a in open_swing:
            close(a, ev["t"], "stopped")
    for a in list(open_swing):
        close(a, None, "censored")
    return out


def cast_episodes(events, me=None):
    """Cast episodes: SELF opens on E4 (the press-ack), OTHERS on prop 60/50.

    The split is structural, not cosmetic: the observer's own casts carry the
    E-series (E4 press, E5 cast-end, E3 aftercast-end, E6 recharge-end, E2
    refused/terminated), and a QUEUED cast that never begins gets an E4 and
    an E2 with NO animation property at all -- so an animation-property open
    would delete exactly the terminated family. Other agents' casts have no
    E-series; property 60/50 is their only open, 58 their only close.

    Self episodes are keyed (caster, skill) because retail interleaves two
    pending skills' cycles (castgaps.py's own grouping); other episodes are
    keyed by caster alone. Timing joins gate on t >= t0 -- an E-tag from an
    older cycle never reaches back. A 0x00F1 during an open episode is
    recorded, never a close by itself (ANIMREF-Q2 wants to SEE these).
    """
    evs = list(events)
    by_t = collections.defaultdict(list)
    for ev in evs:
        by_t[ev["t"]].append(ev)
    open_self = {}      # (caster, skill) -> episode
    open_other = {}     # caster -> episode
    out = []

    def sig_at(t, agent):
        return tuple(token(x) for x in by_t[t] if involves(x, agent))

    def close_self(key, t, how):
        ep = open_self.pop(key)
        ep["t_close"], ep["close"] = t, how
        if t is not None:
            ep["dt_close"] = round(t - ep["t0"], 6)
        out.append(ep)

    def close_other(caster, t, how):
        ep = open_other.pop(caster)
        ep["t_close"], ep["close"] = t, how
        if t is not None:
            ep["dt_close"] = round(t - ep["t0"], 6)
        out.append(ep)

    for ev in evs:
        t = ev["t"]
        if ev["kind"] == "E4" and me is not None and ev["agent"] == me:
            key = (me, ev["skill"])
            if key in open_self:
                done = "E6" in open_self[key]["e"] or "E2" in open_self[key]["e"]
                close_self(key, t, "complete" if done else "reopened")
            open_self[key] = {
                "caster": me, "skill": ev["skill"], "self": True,
                "family": None, "target": None,
                "t0": t, "open_sig": sig_at(t, me),
                "e": {"E4": 0.0}, "status_marks": [],
            }
        elif ev["kind"] in ("E2", "E3", "E5", "E6") and me is not None \
                and ev["agent"] == me:
            ep = open_self.get((me, ev["skill"]))
            if ep is not None and t >= ep["t0"]:
                ep["e"].setdefault(ev["kind"], round(t - ep["t0"], 6))
                if ev["kind"] == "E5":
                    ep["finish_sig"] = sig_at(t, me)
                elif ev["kind"] == "E2":
                    close_self((me, ev["skill"]), t, "refused_or_terminated")
                elif ev["kind"] == "E6":
                    close_self((me, ev["skill"]), t, "complete")
        elif ev["kind"] == "prop":
            a, p = ev["agent"], ev["prop"]
            if p in CAST_OPEN:
                fam = "spell" if p == 60 else "attack_skill"
                if me is not None and a == me:
                    # The begin instant of an already-open self episode
                    # (same batch as E4 for a free cast, later for a queued
                    # one). Attach to the newest open episode for the skill.
                    ep = open_self.get((me, int(ev["value"])))
                    if ep is not None and t >= ep["t0"]:
                        ep["family"] = fam
                        ep["target"] = ev.get("target")
                        ep.setdefault("t_anim", t)
                        ep.setdefault("dt_anim", round(t - ep["t0"], 6))
                        if t != ep["t0"]:
                            ep["begin_sig"] = sig_at(t, me)
                    continue
                if a in open_other:
                    close_other(a, t, "reopened")
                open_other[a] = {
                    "caster": a, "target": ev.get("target"),
                    "skill": int(ev["value"]), "family": fam, "self": False,
                    "t0": t, "open_sig": sig_at(t, a),
                    "e": {}, "status_marks": [],
                }
            elif p == 58:
                if me is not None and a == me:
                    continue        # self's 58 rides the E5 batch, already kept
                if a in open_other:
                    ep = open_other[a]
                    ep["dt_finish"] = round(t - ep["t0"], 6)
                    ep["finish_sig"] = sig_at(t, a)
                    close_other(a, t, "finished")
            elif p == 59:
                if me is not None and a == me:
                    for key, ep in list(open_self.items()):
                        if key[0] == a and "E5" not in ep["e"]:
                            ep["cancel_sig"] = sig_at(t, a)
                            close_self(key, t, "cancelled")
                elif a in open_other:
                    open_other[a]["cancel_sig"] = sig_at(t, a)
                    close_other(a, t, "cancelled")
        elif ev["kind"] == "status":
            a = ev["agent"]
            for key, ep in open_self.items():
                if key[0] == a:
                    ep["status_marks"].append((round(t, 6), ev["value"]))
            if a in open_other:
                open_other[a]["status_marks"].append((round(t, 6), ev["value"]))
        # stale-episode sweep: censor anything silent past the timeout
        for key in [k for k, ep in open_self.items()
                    if t - ep["t0"] > CAST_TIMEOUT and "E6" not in ep["e"]]:
            close_self(key, None, "timeout")
        for a in [a for a, ep in open_other.items()
                  if t - ep["t0"] > CAST_TIMEOUT]:
            close_other(a, None, "timeout")

    for key in list(open_self):
        done = "E6" in open_self[key]["e"]
        close_self(key, None, "complete" if done else "censored")
    for a in list(open_other):
        close_other(a, None, "censored")
    return out


def prop_census(events):
    """Every property id seen, with counts -- the unknowns are the point."""
    c = collections.Counter(ev["prop"] for ev in events if ev["kind"] == "prop")
    return {int(p): {"n": n, "name": KNOWN_PROPS.get(p, "UNKNOWN")}
            for p, n in sorted(c.items())}


def scan_live(stamps=None):
    """Walk the live corpus. Returns (meta, connections) -- nothing written."""
    live = vaultpath.require_dir("captures", "live",
                                 why="the ANIMREF episode grammar")
    codec = Codec()
    meta = {"root": live, "origin": "live", "captures": 0,
            "connections": 0, "decoded": 0, "refused_partial": []}
    conns = []
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        if stamps and stamp not in stamps:
            continue
        meta["captures"] += 1
        for chan in tape.channel_files(cap):
            conn = chan["connection"] if isinstance(chan, dict) else chan
            meta["connections"] += 1
            try:
                _info, tape_events = tape.load_tape(cap, conn)
            except tape.TapeError as exc:
                meta["refused_partial"].append(
                    {"capture": stamp, "connection": conn,
                     "why": f"TapeError: {exc}"})
                continue
            msgs, (consumed, total, err) = tape.decode_all(
                tape_events, codec, "GAME_SMSG", 0)
            if err is not None or consumed != total:
                # A partial frame invents opcodes; refuse the connection and
                # SAY so -- a silent drop here is the outcome-selection defect.
                meta["refused_partial"].append(
                    {"capture": stamp, "connection": conn,
                     "why": f"partial decode {consumed}/{total} ({err})"})
                continue
            meta["decoded"] += 1
            evs = list(prop_events(msgs))
            if not evs:
                continue
            me = whose_agent(msgs)
            conns.append({
                "capture": stamp, "connection": conn, "me": me,
                "events": evs,
                "swings": swing_episodes(evs),
                "casts": cast_episodes(evs, me=me),
                "props": prop_census(evs),
            })
    return meta, conns


def _stats(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return {"n": 0}
    mean = sum(xs) / n
    sd = (sum((x - mean) ** 2 for x in xs) / n) ** 0.5 if n > 1 else 0.0
    return {"n": n, "mean": round(mean, 4), "sd": round(sd, 4),
            "min": round(xs[0], 4), "max": round(xs[-1], 4)}


def census(meta, conns):
    """The printed referent: populations, signatures, distributions."""
    swings = [s for c in conns for s in c["swings"]]
    casts = [dict(ep, capture=c["capture"], connection=c["connection"])
             for c in conns for ep in c["casts"]]
    self_ids = {(c["capture"], c["connection"]): c["me"] for c in conns}

    def is_self(c, ep):
        return ep["self"]

    by_close = collections.Counter(s["close"] for s in swings)
    landed = [s for s in swings if s["close"] == "landed"]
    with_dmg = [s for s in landed if s["damage"]]
    ratios_all = [s["ratio"] for s in swings
                  if s["close"] == "landed" and s["ratio"] is not None]

    self_keyset = {k for k, v in self_ids.items() if v is not None}
    self_swing_ratios, other_swing_ratios = [], []
    by_interval = collections.defaultdict(list)
    for c in conns:
        for s in c["swings"]:
            if s["close"] != "landed" or s["ratio"] is None:
                continue
            (self_swing_ratios if s["attacker"] == c["me"]
             else other_swing_ratios).append(s["ratio"])
            by_interval[round(s["interval"], 3)].append(s["ratio"])

    open_sigs = collections.Counter()
    finish_sigs = collections.Counter()
    cancel_sigs = collections.Counter()
    fam_close = collections.Counter()
    status_marked_casts = []
    for ep in casts:
        who = "self" if ep["self"] else "other"
        fam = ep["family"] or "no_anim_prop"
        fam_close[(fam, who, ep["close"])] += 1
        open_sigs[(fam, who, ep["open_sig"])] += 1
        if "finish_sig" in ep:
            finish_sigs[(fam, who, ep["finish_sig"])] += 1
        if "cancel_sig" in ep:
            cancel_sigs[(fam, who, ep["cancel_sig"])] += 1
        if ep["status_marks"]:
            status_marked_casts.append(ep)

    props = collections.Counter()
    unknown = collections.Counter()
    for c in conns:
        for p, row in c["props"].items():
            props[p] += row["n"]
            if row["name"] == "UNKNOWN":
                unknown[p] += row["n"]

    return {
        "meta": {k: v for k, v in meta.items() if k != "refused_partial"},
        "refused": meta["refused_partial"],
        "swings": {
            "by_close": dict(by_close),
            "landed_with_same_instant_damage":
                {"n": len(with_dmg), "of": len(landed)},
            "ratio_all": _stats(ratios_all),
            "ratio_self": _stats(self_swing_ratios),
            "ratio_others": _stats(other_swing_ratios),
            "ratio_by_declared_interval":
                {str(iv): _stats(rs) for iv, rs in sorted(by_interval.items())},
        },
        "casts": {
            "by_family_who_close":
                {f"{f}/{w}/{cl}": n for (f, w, cl), n in sorted(fam_close.items())},
            "open_signatures":
                [{"family": f, "who": w, "sig": list(sig), "n": n}
                 for (f, w, sig), n in open_sigs.most_common()],
            "finish_signatures":
                [{"family": f, "who": w, "sig": list(sig), "n": n}
                 for (f, w, sig), n in finish_sigs.most_common()],
            "cancel_signatures":
                [{"family": f, "who": w, "sig": list(sig), "n": n}
                 for (f, w, sig), n in cancel_sigs.most_common()],
            "status_marked_casts":
                [{"capture": ep["capture"], "caster": ep["caster"],
                  "skill": ep["skill"], "t0": ep["t0"],
                  "status_marks": ep["status_marks"], "close": ep["close"]}
                 for ep in status_marked_casts],
        },
        "props": {str(p): {"n": n, "name": KNOWN_PROPS.get(p, "UNKNOWN")}
                  for p, n in sorted(props.items())},
        "unknown_props": {str(p): n for p, n in sorted(unknown.items())},
        "self_connections": len(self_keyset),
    }


def control(conns):
    """P-CTRL: the castmech-overlap figures, enforced. Returns exit code."""
    sys.path.insert(0, os.path.join(ROOT, "toolkit"))
    import checks
    led = checks.Ledger("animgrammar castmech overlap control", floor=7)
    both = [c for c in conns
            if c["capture"] in ("20260807T143055", "20260810T235916")]
    led.ok(len(both) >= 2, "both castmech captures present in the walk",
           f"got {sorted({c['capture'] for c in both})}")
    self_eps = [ep for c in both for ep in c["casts"] if ep["self"]]
    complete = [ep for ep in self_eps if "E5" in ep["e"] and "E3" in ep["e"]]
    led.ok(len(complete) == 6, "6 complete self cast-cycles",
           f"got {len(complete)}")
    spell_gaps = sorted(round(ep["e"]["E3"] - ep["e"]["E5"], 4)
                        for ep in complete if ep["family"] == "spell")
    led.ok(len(spell_gaps) == 4 and all(0.74 <= g <= 0.77 for g in spell_gaps),
           "four spell E5->E3 gaps in 0.74-0.77 s", f"{spell_gaps}")
    atk_gaps = [round(ep["e"]["E3"] - ep["e"]["E5"], 4)
                for ep in complete if ep["family"] == "attack_skill"]
    led.ok(len(atk_gaps) == 2 and all(g == 0.0 for g in atk_gaps),
           "two attack-skill E5->E3 gaps at 0.000", f"{atk_gaps}")
    terminated = [ep for c in both for ep in c["casts"]
                  if ep["close"] == "refused_or_terminated"]
    led.ok(len(terminated) == 1, "exactly one E2-terminated cast",
           f"got {len(terminated)}")
    e4e5 = sorted(round(ep["e"]["E5"] - ep["e"]["E4"], 4) for ep in complete
                  if "E4" in ep["e"] and ep["family"] == "attack_skill")
    led.ok(e4e5 == [1.1374, 1.1387],
           "Power Shot E4->E5 gaps reproduce castgaps to the 0.1 ms",
           f"{e4e5}")
    ratios = [round(ep["e"]["E5"] - ep["e"]["E4"], 4) / 2.475 for ep in complete
              if "E4" in ep["e"] and ep["family"] == "attack_skill"]
    led.ok(all(0.44 <= r <= 0.47 for r in ratios),
           "attack-skill E4->E5 over the 2.475 bow interval sits in the "
           "windup band", f"{[round(r, 4) for r in ratios]}")
    return led.verdict()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stamps", help="comma-separated capture stamps (default: all live)")
    ap.add_argument("--write", action="store_true",
                    help="write episodes + census JSON under vault/research/animref/")
    ap.add_argument("--control", action="store_true",
                    help="P-CTRL: enforce the castmech-overlap figures and exit")
    ap.add_argument("--json", action="store_true",
                    help="print the census as JSON instead of prose")
    args = ap.parse_args()

    stamps = set(args.stamps.split(",")) if args.stamps else None
    meta, conns = scan_live(stamps)
    if args.control:
        sys.exit(control(conns))
    cen = census(meta, conns)

    if args.write:
        outdir = os.path.join(vaultpath.require_dir(
            "research", why="the ANIMREF referent"), "animref")
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "episodes_live.jsonl"), "w",
                  encoding="utf-8") as fh:
            for c in conns:
                for kind, eps in (("swing", c["swings"]), ("cast", c["casts"])):
                    for ep in eps:
                        row = dict(ep, kind=kind, capture=c["capture"],
                                   connection=c["connection"], origin="live")
                        row.pop("open_sig", None) or None
                        row["open_sig"] = list(ep.get("open_sig", ()))
                        for k in ("finish_sig", "cancel_sig"):
                            if k in ep:
                                row[k] = list(ep[k])
                        fh.write(json.dumps(row) + "\n")
        with open(os.path.join(outdir, "census_live.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(cen, fh, indent=1)
        print(f"wrote {outdir}\\episodes_live.jsonl and census_live.json")

    if args.json:
        print(json.dumps(cen, indent=1))
        return

    m = cen["meta"]
    print(f"captures {m['captures']}  connections {m['connections']}  "
          f"decoded {m['decoded']}  refused {len(cen['refused'])}")
    for r in cen["refused"]:
        print(f"  REFUSED {r['capture']} {r['connection']}: {r['why']}")
    s = cen["swings"]
    print(f"\nswings by close: {s['by_close']}")
    d = s["landed_with_same_instant_damage"]
    print(f"landed with same-instant damage: {d['n']}/{d['of']}")
    for k in ("ratio_all", "ratio_self", "ratio_others"):
        print(f"windup {k}: {s[k]}")
    print(f"\ncast episodes by family/who/close: {cen['casts']['by_family_who_close']}")
    print("\nopen-burst signatures (most common first):")
    for row in cen["casts"]["open_signatures"][:20]:
        print(f"  {row['n']:4d}  {row['family']}/{row['who']}: {row['sig']}")
    print("\nfinish signatures:")
    for row in cen["casts"]["finish_signatures"][:12]:
        print(f"  {row['n']:4d}  {row['family']}/{row['who']}: {row['sig']}")
    print("\ncancel signatures:")
    for row in cen["casts"]["cancel_signatures"][:12]:
        print(f"  {row['n']:4d}  {row['family']}/{row['who']}: {row['sig']}")
    if cen["casts"]["status_marked_casts"]:
        print("\nSTATUS-MARKED CASTS (0x00F1 during the episode -- ANIMREF-Q2 leads):")
        for row in cen["casts"]["status_marked_casts"]:
            print(f"  {row}")
    if cen["unknown_props"]:
        print(f"\nproperty ids OUTSIDE the register (kept, not dropped): "
              f"{cen['unknown_props']}")


if __name__ == "__main__":
    main()
