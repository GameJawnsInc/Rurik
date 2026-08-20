r"""Rung 8's consumer: the effect channel read as EPISODES -- apply, expiry or
strip, and what carried them -- built and proven on retail bytes before the
live session, the way rung 7's `damagepass.py` was.

WHY THIS EXISTS. `studies/isle/PLAN.md` §3.3 names "the `bufflog.py` §3.3 needs"
as unwritten, and rung 8 is the effects pass. Nothing in this repo reads an
effect out of a capture: `authsrv.py` knows only `EFFECT_DEAD` and
`EFFECT_TRANSITION`, and conditions, hexes and enchantments are modelled in no
form at all.

THE HEADLINE THIS MODULE WAS BUILT ON, and it changes rung 8's design before a
minute is spent. §3.3's central worry was that `0x0042`'s layout comes from our
own loopback plus disassembly, with **ZERO ArenaNet witnesses**, so "conditions
ride some other channel" was the likely outcome. **That is now settled offline:
the live corpus holds 97 `0x0042` applies and 88 `0x0044` removals**, carrying
condition skill ids among others -- they arrived in the rung-6 capture's PvP
arena detour and in the east run's Pin Down episode, neither of which set out to
measure an effect. The channel question rung 8 was going to spend its first two
minutes on is ANSWERED. What is not answered is everything downstream, and that
is what the plan should buy.

WHAT AN EPISODE IS. `0x0042` `[target, skill, field3, buff_id, f32 duration]`
opens one; `0x0044` `[target, buff_id]` closes it. MEASURED over the whole
corpus: the removal lands at **apply + duration**, 57 of 88 within 5 ms and 83
of 88 within 50 ms. So an episode closes one of three ways and the module never
conflates them:
  * EXPIRED  -- residual ~ 0: the effect ran its stated duration.
  * STRIPPED -- removed EARLY: something cut it short. All four in the corpus
                are one stance in a PvP arena, cut by 3.6-8.7 s. A cure, a
                death or an overwrite looks like this and an expiry does not.
  * OPEN     -- no removal before the capture ends. Nine of these, every one an
                effect still live at the last byte. Never scored as expired.

THE ATTRIBUTION RULE, and it is a refusal. **`0x0042` has NO source-agent
field** -- `studies/skillcast/FINDINGS.md`:900-902, and the catalog agrees. So
"who applied this" is not on the wire, and the only handle is the sealed plan's
mark window. An episode whose apply time falls outside every window is emitted
**unattributed**; it is never assigned to the nearest step. §3.3 wrote that rule
and this module enforces it.

THE DURATION FIELD IS A FLOAT IN A DWORD SLOT. `schema/messages.json` types it
`dword` and the client does `fld` on it, so every reader must reinterpret. A
consumer that compares the raw integer sees ~1.09e9 and fails every time.

FIELD 3 IS NOT THE DURATION, and the corpus says so specifically. Per skill:
480 -> (3, 3.0) and (9, 9.0); 481 -> (13, 13.0); but 160 -> (15, 13.0),
179 -> (13, 3.0), 364 -> (10, 10.0) and (13, 12.0), 984/998 -> (0, 30.0). The
removal follows the FLOAT, not field 3 (checked on skill 364's (13, 12.0): the
removal lands at +12.0). The two skills where they agree are the two CONDITIONS
in the corpus, which is the shape of a real finding and is rung 8's registered
discriminator -- see `field3_report`.

    python toolkit/authsrv/bufflog.py --capture 20260817T231139
    python toolkit/authsrv/bufflog.py --census        # the whole live corpus
"""
import argparse
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agentroster  # noqa: E402
import damagepass  # noqa: E402
import tape  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

OP_EFFECT_APPLY = 0x0042    # [target, skill, field3, buff_id, f32 duration]
OP_EFFECT_REMOVE = 0x0044   # [target, buff_id]
OP_EFFECT_41 = 0x0041       # [agent, agent, word, dword, dword] -- see below
OP_FLOAT_NOTARGET = 0x00A2  # [prop, agent, f32] -- property 44 rides here
OP_INT_NOTARGET = 0x009F    # [prop, agent, value] -- PROP_HEALTH_MAX

PROP_REGEN = 44             # net regen RATE, max-health fractions per second
PROP_HEALTH_MAX = 42

# The ten condition skill ids, MEASURED from the client's own skill table
# (`skilltable type_code == 8` selects exactly these; rung 3's B-bench, and
# `studies/isle/FINDINGS.md` R4-2 corroborated 478 and 480 on a rendered
# client). Ordinals follow `s_charCondition`'s own order.
CONDITION_SKILLS = {
    478: "bleeding", 479: "blind", 480: "burning", 481: "crippled",
    482: "deep_wound", 483: "disease", 484: "poison", 485: "dazed",
    486: "weakness", 2077: "cracked_armor",
}

# Residual bands for classifying a close. 50 ms is the corpus's own 83/88
# shoulder; beyond it the corpus's only cases are cut by SECONDS, not by jitter.
EXPIRY_TOLERANCE = 0.05


class BuffLogError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


# ---------------------------------------------------------------------------
# reading

def read_effects(capture_dir, connection, codec=None):
    """Effect-channel events of one game connection, on the CAPTURE clock.

    Returns {capture, connection, origin, map_id, applies, removes, regen,
    health_max, creates}. Times are rebased by `info["t0"]` -- the trap rung 7
    paid for: tape times are connection-local and plan marks are capture-global,
    and skipping the bridge mislabels blocks SILENTLY rather than erroring.
    """
    codec = codec or Codec()
    info, events = tape.load_tape(capture_dir, connection)
    t_base = info.get("t0") or 0.0
    events = [(round(t + t_base, 6), payload) for t, payload in events]
    msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
    consumed, total, err = receipt
    if err is not None or consumed != total:
        raise BuffLogError(
            f"{capture_dir} {connection} did not frame to its final byte "
            f"({consumed}/{total}, {err}). Refusing a partial effect log: the "
            f"tail is exactly where the un-expired episodes live.")
    try:
        map_id = tape.client_version(capture_dir, connection)["map_id"]
    except tape.TapeError:
        map_id = None

    out = {"capture": info.get("capture") or os.path.basename(capture_dir),
           "connection": connection, "origin": info.get("origin", "unknown"),
           "map_id": map_id, "applies": [], "removes": [], "regen": [],
           "health_max": [], "other41": [], "creates": []}
    for t, opcode, v in msgs:
        if opcode == OP_EFFECT_APPLY:
            out["applies"].append({
                "t": t, "target": v[1], "skill": v[2], "field3": v[3],
                "buff": v[4], "duration": _f32(v[5])})
        elif opcode == OP_EFFECT_REMOVE:
            out["removes"].append({"t": t, "target": v[1], "buff": v[2]})
        elif opcode == OP_EFFECT_41:
            out["other41"].append({"t": t, "values": list(v[1:])})
        elif opcode == OP_FLOAT_NOTARGET and v[1] == PROP_REGEN:
            out["regen"].append({"t": t, "agent": v[2], "rate": _f32(v[3])})
        elif opcode == OP_INT_NOTARGET and v[1] == PROP_HEALTH_MAX:
            out["health_max"].append({"t": t, "agent": v[2], "value": v[3]})
        elif opcode == agentroster.npcdefs.CREATE_AGENT:
            out["creates"].append(agentroster.create_row(
                t, v, out["capture"], connection))
    return out


# ---------------------------------------------------------------------------
# episodes

def episodes(ev):
    """Pair applies to removals: [{apply fields, close_t, residual, state}].

    Pairing is per (target, buff_id), earliest unused removal at or after the
    apply. `state` is "expired" | "stripped" | "open".

    WHY THE BUFF ID ALONE IS NOT THE KEY. Ids are reused within a session (the
    corpus reuses 53, 61, 71 repeatedly), so a global map would pair an apply
    with a LATER episode's removal and report a wild residual. Pairing in time
    order per target is what keeps that honest, and the residual is reported
    rather than assumed -- an early close is a finding (a cure, a death, an
    overwrite), not noise to absorb.
    """
    removes = [dict(r, used=False) for r in sorted(ev["removes"],
                                                   key=lambda r: r["t"])]
    out = []
    for a in sorted(ev["applies"], key=lambda a: a["t"]):
        match = None
        for r in removes:
            if r["used"] or r["target"] != a["target"] or r["buff"] != a["buff"]:
                continue
            if r["t"] < a["t"] - 1e-6:
                continue
            match = r
            break
        row = dict(a)
        if match is None:
            row.update(close_t=None, residual=None, state="open")
        else:
            match["used"] = True
            residual = (match["t"] - a["t"]) - a["duration"]
            row.update(close_t=match["t"], residual=residual,
                       state=("expired" if abs(residual) <= EXPIRY_TOLERANCE
                              else "stripped"))
        out.append(row)
    return out


def attribute(eps, windows):
    """Attach the sealed plan's step to each episode, or None. NEVER the nearest.

    `0x0042` carries no source agent, so attribution is the mark window and
    nothing else. An episode outside every window keeps `step = None` and is
    reported as unattributed -- §3.3's own rule, written because assigning it
    to the closest step is exactly how a wrong answer gets manufactured.
    """
    for e in eps:
        w = damagepass.window_at(windows, e["t"]) if windows else None
        e["step"] = w[0] if w else None
        e["step_text"] = w[1] if w else None
    return eps


def condition_map(eps):
    """{skill_id: {name, n, durations, field3s, states}} for CONDITION skills.

    Only ids in `CONDITION_SKILLS` -- everything else is reported separately by
    `field3_report`, because calling an arbitrary skill id a condition is the
    guess this module exists to refuse.
    """
    out = {}
    for e in eps:
        if e["skill"] not in CONDITION_SKILLS:
            continue
        row = out.setdefault(e["skill"], {
            "name": CONDITION_SKILLS[e["skill"]], "n": 0, "durations": {},
            "field3s": {}, "states": {}})
        row["n"] += 1
        row["durations"][e["duration"]] = row["durations"].get(
            e["duration"], 0) + 1
        row["field3s"][e["field3"]] = row["field3s"].get(e["field3"], 0) + 1
        row["states"][e["state"]] = row["states"].get(e["state"], 0) + 1
    return out


def field3_report(eps):
    """Per skill, the (field3, duration) pairs seen and whether they agree.

    RUNG 8'S REGISTERED DISCRIMINATOR, AND IT IS SETTLED -- 2026-08-20, WITHOUT
    THE SESSION. This docstring used to end "the answer is one session away and
    the prediction is on record before the run". The answer was ZERO sessions
    away: the discriminator was already in the vault, and what it needed was
    the client's skill table on the other side of the join.

    The two readings were (a) field3 is the applying skill's ATTRIBUTE RANK,
    and (b) field3 is a duration-shaped field that non-conditions use
    otherwise. Predict each apply's wire duration from the applying skill's own
    `duration0`/`duration15` endpoints at rank = field3, using the client's own
    two-point scaler:

        interp(duration0, duration15, field3) == the f32 duration

    holds for 96 of 96 NON-CONDITION applies with no misses. No free parameter:
    the endpoints are ArenaNet's, the formula was measured at 0x005A8920 for
    the damage scale, and field3 and the duration are retail's own bytes.
    Reading (a) CONFIRMED, reading (b) REFUTED -- skill 160 carries field3 = 15
    against a duration of 13.0, and skill 364 appears at two field3 values (10
    and 13) producing two durations (10.0 and 12.0), both predicted exactly.

    The conditions stay the named exception and are counted separately, because
    a condition's duration comes from the skill that INFLICTED it rather than
    from its own row: 480 has endpoints 3/3 and appears on the wire at 9.0.
    The ten-Student experiment above would still separate what sets a
    CONDITION's duration; it is no longer needed for field3 itself.

    See `effects.py`, which is the writer this settled, and
    `test_effects.py` section 2, which re-runs the whole check every suite.
    """
    per = {}
    for e in eps:
        per.setdefault(e["skill"], {}).setdefault(
            (e["field3"], e["duration"]), 0)
        per[e["skill"]][(e["field3"], e["duration"])] += 1
    out = {}
    for skill, pairs in sorted(per.items()):
        agree = all(f3 == dur for (f3, dur) in pairs)
        out[skill] = {
            "is_condition": skill in CONDITION_SKILLS,
            "name": CONDITION_SKILLS.get(skill),
            "pairs": {f"{f3}/{dur}": n for (f3, dur), n in sorted(pairs.items())},
            "field3_equals_duration": agree,
            "n": sum(pairs.values()),
        }
    return out


def regen_during(ev, eps, agent=None):
    """Property-44 samples with the effects live on that target at the time.

    The degeneration half of rung 8. `studies/isle/FINDINGS.md` B4 measured
    property 44 as the NET regen rate in max-health fractions per second,
    quantised in units of 2 hp/s (one HUD pip) -- so a condition's pip cost is
    (rate_before - rate_during) * max_health / 2. This routine only JOINS; it
    does not compute pips, because the corpus has no non-player max-health to
    divide by and inventing one is how a check that cannot fail gets built.
    """
    out = []
    for r in sorted(ev["regen"], key=lambda r: r["t"]):
        if agent is not None and r["agent"] != agent:
            continue
        live = [e for e in eps
                if e["target"] == r["agent"] and e["t"] <= r["t"]
                and (e["close_t"] is None or r["t"] <= e["close_t"])]
        hmax = None
        for h in ev["health_max"]:
            if h["agent"] == r["agent"] and h["t"] <= r["t"]:
                hmax = h["value"]
        out.append({"t": r["t"], "agent": r["agent"], "rate": r["rate"],
                    "health_max": hmax,
                    "live": [(e["skill"], e["buff"]) for e in live],
                    "pips": (r["rate"] * hmax / 2.0) if hmax else None})
    return out


def buff_id_report(eps):
    """How the server allocates buff ids -- the pattern §3.3 asked for.

    Reports the id range, how many ids are reused, and the maximum number of
    episodes live at once (which bounds what an id space has to cover).
    """
    if not eps:
        return {"n": 0}
    ids = [e["buff"] for e in eps]
    events = []
    for e in eps:
        events.append((e["t"], +1))
        events.append((e["close_t"] if e["close_t"] is not None else math.inf,
                       -1))
    events.sort(key=lambda x: (x[0], -x[1]))
    live = peak = 0
    for _t, d in events:
        live += d
        peak = max(peak, live)
    return {"n": len(ids), "min": min(ids), "max": max(ids),
            "distinct": len(set(ids)),
            "reused": len(ids) - len(set(ids)), "peak_concurrent": peak}


# ---------------------------------------------------------------------------
# report

def report(capture_dir, connection, codec=None):
    ev = read_effects(capture_dir, connection, codec)
    windows = damagepass.mark_windows(capture_dir)
    eps = attribute(episodes(ev), windows)
    states = {}
    for e in eps:
        states[e["state"]] = states.get(e["state"], 0) + 1
    resid = [abs(e["residual"]) for e in eps if e["residual"] is not None]
    resid.sort()
    return {
        "capture": ev["capture"], "connection": connection,
        "origin": ev["origin"], "map_id": ev["map_id"],
        "counts": {"applies": len(ev["applies"]),
                   "removes": len(ev["removes"]),
                   "regen": len(ev["regen"]),
                   "op41": len(ev["other41"]),
                   "unattributed": sum(1 for e in eps if e["step"] is None)},
        "states": states,
        "residual_median": resid[len(resid) // 2] if resid else None,
        "residual_max": resid[-1] if resid else None,
        "conditions": condition_map(eps),
        "field3": field3_report(eps),
        "buff_ids": buff_id_report(eps),
        "episodes": eps,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", help="stamp under captures/live")
    ap.add_argument("--connection", help="one connection (default: all game)")
    ap.add_argument("--census", action="store_true",
                    help="every live capture")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.capture and not args.census:
        ap.error("give --capture STAMP or --census")
    live = vaultpath.require_dir("captures", "live",
                                 why="bufflog reads live captures")
    stamps = ([args.capture] if args.capture
              else sorted(d for d in os.listdir(live)
                          if os.path.isdir(os.path.join(live, d))))
    codec = Codec()
    for stamp in stamps:
        cap_dir = os.path.join(live, stamp)
        conns = ([{"connection": args.connection}] if args.connection
                 else tape.channel_files(cap_dir))
        for row in conns:
            try:
                rep = report(cap_dir, row["connection"], codec)
            except (BuffLogError, tape.TapeError) as exc:
                if args.capture:
                    print(f"{stamp} {row['connection']}: {exc}")
                continue
            if not rep["counts"]["applies"] and not rep["counts"]["regen"]:
                continue
            if args.json:
                print(json.dumps(rep, default=str))
                continue
            c = rep["counts"]
            print(f"{rep['capture']} {rep['connection']} map={rep['map_id']} "
                  f"origin={rep['origin']}")
            print(f"  applies {c['applies']} removes {c['removes']} "
                  f"regen {c['regen']} 0x0041 {c['op41']}  states={rep['states']}"
                  f"  unattributed {c['unattributed']}")
            if rep["residual_median"] is not None:
                print(f"  close residual: median "
                      f"{rep['residual_median']*1000:.1f} ms, max "
                      f"{rep['residual_max']:.3f} s")
            for skill, f in sorted(rep["field3"].items()):
                tag = f" CONDITION {f['name']}" if f["is_condition"] else ""
                print(f"    skill {skill:>5} n={f['n']:<3} "
                      f"field3/duration {f['pairs']} "
                      f"agree={f['field3_equals_duration']}{tag}")
            b = rep["buff_ids"]
            if b["n"]:
                print(f"    buff ids: {b['min']}..{b['max']}, "
                      f"{b['distinct']} distinct, {b['reused']} reused, "
                      f"peak concurrent {b['peak_concurrent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
