r"""Rung 7's consumer: damage events out of a capture, scoped the way the design
demands, with the armour-divisor fit, the crit variance law, H recovery, and the
Master of Damage's chat numbers -- built and proven BEFORE the live session.

WHY THIS EXISTS. `studies/isle/PLAN.md` §6 rung 7 measures the armour term by
auto-attacking the Suits and fitting the divisor D jointly from
r80 = 2^(-20/D) and r100 = 2^(-40/D). Its §7 names the arc's real risk: "a
beautifully-instrumented campaign producing a folder of well-labelled numbers
that no line of the server ever reads" -- four designs specify what to measure
and none who CONSUMES it. This module is the consumer, written first so the live
capture lands in an instrument instead of a folder. Nothing else in `toolkit/`
reads a damage event out of a capture: the B9 bench's decoder was session
scratch in `vault/research/`, and `behaviourrun.py` reads fights, not floats.

WHAT A DAMAGE EVENT IS. GAME_SMSG `0x00A3` `[prop, target, cause, f32]` -- the
float channel (`agents.py:124`). Three kinds land damage-shaped:
  16  debits fraction x target max (client and server ledger agree, rung 4 R4-3)
  17  debits and REPLACES 16 for its swing (B6: a lone p17 kills; crit is the
      lean and rung 7's variance law is the test)
  18  notifies only -- the bar does not move (R4-3, refuting its own prediction)
The value is a FRACTION of the target's max health, negative for damage, and
UNCLAMPED (ArenaNet's own -1.125, B6).

THE SCOPING RULE, inherited from B6 and not optional: aggregate on
**(target, cause, swing-kind)** -- kind IS part of the key. The 8-vs-25
"counterexample" to crit was a scope error that dissolved under this key, and
`studies/isle/FINDINGS.md` B6 records the rule as the one rung 7 must inherit.
The target half of the key is a STATION (definition slot, model, position,
plane) when the create in effect is an NPC -- §3.1's own confound table says
"aggregate on (definition slot, spawn coordinate), not agent id", because the
Suits DIE and respawn under fresh agent ids -- and a per-body key otherwise (a
moving player is many stations, which is the other half of the same trap).
When a sealed plan's mark windows exist the plan STEP joins the key too: the
rank-sweep extension re-engages one Suit at five different attribute ranks,
and without the block dimension those blocks pool into one group whose mean
is a number about nothing.

JOINING TARGETS: the create IN EFFECT AT THE EVENT'S TIMESTAMP, never the
agent's last create -- agent ids are recycled (`npcdefs.py`'s interval rule; 19
of 45 ids re-created in one tape). An event whose target has no create yet goes
in an `unjoined` bucket that is REPORTED, never guessed into a station.

H RECOVERY. B9: the wire fraction is an integer divided by target max health,
49/49 known-H events exact to f32 epsilon. So the fraction grid gives H back:
the minimal H whose grid every event of a group sits on, bitwise as f32. Every
multiple of a fitting H also fits (f32(kn/kH) == f32(n/H) -- the same real
number), so the result is a FAMILY {k*H0}; the fit reports H0 and whether a
predicted H (590 for the Master of Damage, GWW) is in the family. Small samples
fit many grids; n is reported so nobody reads H0 off two events.

WHAT THIS DELIBERATELY DOES NOT DO. It does not name a body (`enc_name` render
is the only naming route -- the withdrawn agent-28 claim is the standing
warning); it does not decode the PROSE of `0x5D` chat (ids only -- provenance:
the id is a measurement, the string is ArenaNet's expression); and it does not
label a group with an armour rating by ITSELF -- AR labels come exclusively
from the sealed plan's own step text (`AR=NN` in a mark window), so the binding
is pre-registered rather than inferred after the fact.

    python toolkit/authsrv/damagepass.py --capture 20260817T231139
    python toolkit/authsrv/damagepass.py --capture STAMP --connection PORT
"""
import argparse
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
import agentroster  # noqa: E402
import codedstr  # noqa: E402
import tape  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

OP_FLOAT_TARGET = 0xA3    # [prop, target, cause, f32] -- the damage channel
OP_INT_NOTARGET = 0x9F    # [prop, agent, value] -- PROP_HEALTH_MAX rides here
OP_CHAT_CODED = 0x5D      # [string16] coded chat; numeric args are cleartext
OP_CHAT_TAG = 0x5E        # [word, byte] -- ONE of 0x5D's two observed pairings.
# CORRECTED 2026-08-18. This line used to read "0x5D renders only with this
# tag", from rung 4's loopback probe where a bare 0x5D rendered nothing and the
# captured 0x5E made it render. The rung-7 capture refutes the "only": all 18
# Master-of-Damage lines carry NO 0x5E and are paired with 0x5F instead, which
# binds the speech to a speaking AGENT. So 0x5E is the channel tag for a
# channel-addressed line and 0x5F for an agent-addressed one; what rung 4
# actually established is that a bare 0x5D with NEITHER renders nothing.
OP_CAST_START = 0xE5      # [caster, skill, ...] -- the purity check reads this
OP_PROJECTILE = 0xA4      # [shooter, aim vec2, ...] -- one per wand/bow shot

PROP_HEALTH_MAX = 42
DAMAGE_KINDS = (16, 17, 18)

CRIT_RATIO = 1.414        # UPSTREAM gww-facts: crit = floor(1.414 x max base)


class DamagePassError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


def _f32(bits):
    """The f32 the wire carried, from the dword the codec handed us."""
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def _f32_of(x):
    """Python float -> the nearest f32 value, as a Python float."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


# ---------------------------------------------------------------------------
# reading one connection

def read_events(capture_dir, connection, codec=None):
    """Every rung-7-relevant event of one game connection, decoded and typed.

    Returns a dict: capture, connection, origin, map_id, creates (agentroster
    rows), damage [{t, kind, target, cause, frac}], health_max [{t, agent,
    value}], chat [{t, op, ...}], casts [{t, caster, skill}], projectiles
    [{t, shooter}].

    The whole tape must frame to its final byte -- same rule as
    `agentroster.read_roster`: a partial decode silently drops the tail, and a
    damage pass missing its last block reads as a smaller sample, not an error.
    """
    codec = codec or Codec()
    info, events = tape.load_tape(capture_dir, connection)
    # Tape timestamps are CONNECTION-LOCAL (t=0 at the first s2c segment);
    # plan marks are on the CAPTURE's wire clock. info["t0"] is the bridge,
    # and skipping it shifts every mark-window label by the connection's
    # opening offset -- measured on the rung-7 capture as the Master of
    # Damage's engage-block swings labelling to the WALK step, one ~60 s
    # offset. Everything this module stores is capture-global time.
    t_base = info.get("t0") or 0.0
    events = [(round(t + t_base, 6), payload) for t, payload in events]
    msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
    consumed, total, err = receipt
    if err is not None or consumed != total:
        raise DamagePassError(
            f"{capture_dir} {connection} did not frame to its final byte "
            f"({consumed}/{total}, {err}). Refusing a partial damage pass.")
    try:
        map_id = tape.client_version(capture_dir, connection)["map_id"]
    except tape.TapeError:
        map_id = None

    out = {
        "capture": info.get("capture") or os.path.basename(capture_dir),
        "connection": connection,
        "origin": info.get("origin", "unknown"),
        "map_id": map_id,
        "creates": [], "damage": [], "health_max": [],
        "chat": [], "casts": [], "projectiles": [],
    }
    for t, opcode, v in msgs:
        if opcode == OP_FLOAT_TARGET and v[1] in DAMAGE_KINDS:
            out["damage"].append({
                "t": t, "kind": v[1], "target": v[2], "cause": v[3],
                "frac": _f32(v[4])})
        elif opcode == OP_INT_NOTARGET and v[1] == PROP_HEALTH_MAX:
            out["health_max"].append({"t": t, "agent": v[2], "value": v[3]})
        elif opcode == OP_CHAT_CODED:
            words = codedstr.from_wire(v[1])
            try:
                parts = codedstr.parse_coded(words)
            except ValueError as exc:
                # A malformed coded string is a finding, not a crash: keep the
                # raw words and the reason, so the report can show it.
                parts = [("unparseable", str(exc))]
            out["chat"].append({"t": t, "op": OP_CHAT_CODED, "parts": parts})
        elif opcode == OP_CHAT_TAG:
            out["chat"].append({
                "t": t, "op": OP_CHAT_TAG, "channel": v[1], "byte": v[2]})
        elif opcode == OP_CAST_START:
            out["casts"].append({"t": t, "caster": v[1], "skill": v[2]})
        elif opcode == OP_PROJECTILE:
            out["projectiles"].append({"t": t, "shooter": v[1]})
        elif opcode == agentroster.npcdefs.CREATE_AGENT:
            out["creates"].append(agentroster.create_row(
                t, v, out["capture"], connection))
    return out


# ---------------------------------------------------------------------------
# joining and scoping

def join_targets(ev):
    """Attach to each damage row the create IN EFFECT at its timestamp.

    Mutates and returns `ev`; rows gain `target_row` (an agentroster create row,
    or None) and `ev` gains `unjoined` (count). The join is per-agent interval:
    the last create of that agent id at or before the event. An event before
    its target's first create is honest absence -- retail does send some
    properties ahead of the create (`agents.py` PROP_LEVEL, 344/366) -- so it
    is counted, reported, and never guessed into a station.
    """
    by_agent = {}
    for row in ev["creates"]:
        by_agent.setdefault(row["agent"], []).append(row)
    for rows in by_agent.values():
        rows.sort(key=lambda r: r["t"])
    unjoined = 0
    for d in ev["damage"]:
        cand, best = None, None
        for row in by_agent.get(d["target"], ()):
            if row["t"] <= d["t"] and (best is None or row["t"] > best):
                cand, best = row, row["t"]
        d["target_row"] = cand
        if cand is None:
            unjoined += 1
    ev["unjoined"] = unjoined
    return ev


def target_key(row):
    """The aggregation identity of a damage event's target.

    NPC and item creates key on the STATION (tag, definition, model, position,
    plane) -- `agentroster.stations()`'s key -- so a Suit that dies and
    respawns under a fresh agent id stays one group (§3.1's own control). A
    player keys per body-instance (agent id + create time), because a moving
    body at station granularity is many one-event groups, which is the same
    trap from the other side.
    """
    if row is None:
        return None
    if row["tag"] in (agentroster.TAG_NPC, agentroster.TAG_ITEM):
        return (row["tag"], row["definition"], row.get("model"),
                row["pos"], row["plane"])
    return ("agent", row["agent"], row["t"])


def scoped_groups(ev, windows=None):
    """{(target_key, cause, kind, step): [damage rows]} -- B6's rule plus the
    plan's own block structure.

    Kind is in the key (B6, not optional). STEP is in the key whenever a
    sealed plan's mark windows exist, because the rung-7 design re-engages the
    SAME Suit at different attribute ranks in different steps -- without the
    step, a rank-11 block and a rank-13 block against one station pool into a
    single group and the pooled mean is a number about nothing. With no
    windows (census mode, foreign captures) step is None and the key is B6's.
    """
    groups = {}
    for d in ev["damage"]:
        step = None
        if windows:
            w = window_at(windows, d["t"])
            step = w[0] if w else None
        key = (target_key(d.get("target_row")), d["cause"], d["kind"], step)
        groups.setdefault(key, []).append(d)
    return groups


# ---------------------------------------------------------------------------
# H recovery: the fraction grid gives max health back

def h_fit(fracs, hmax=2000):
    """Minimal H whose f32 grid every fraction sits on, or None.

    Returns (h0, points) where points[i] = round(|frac_i| * h0) >= 1, and every
    frac reproduces BITWISE as f32(points[i] / h0) -- B9's observed property
    (49/49 known-H events exact). Every multiple of h0 also fits, so h0 names a
    FAMILY {k*h0}; `h_family_contains` asks about a predicted member. A tiny
    sample fits many grids -- callers report n alongside h0, and two events
    "recovering" H is a number nobody should publish.
    """
    vals = [abs(f) for f in fracs]
    if not vals or any(v <= 0 for v in vals):
        return None
    for h in range(1, hmax + 1):
        pts = []
        for v in vals:
            n = round(v * h)
            if n < 1 or _f32_of(n / h) != _f32_of(v):
                pts = None
                break
            pts.append(n)
        if pts is not None:
            return h, pts
    return None


def h_family_contains(h0, predicted):
    """Is `predicted` in the family {k*h0}? The MoD prediction asks this of 590."""
    return predicted % h0 == 0


# ---------------------------------------------------------------------------
# the divisor fit -- rung 7's registered exit criterion

def divisor_fit(samples_by_ar, base_ar=60):
    """D from r80 and r100, separately and jointly, WITH ERROR BARS.

    `samples_by_ar` maps armour rating -> the list of per-hit values (points or
    fractions -- the ratio cancels any common scale, which is the design's
    whole point). A mapping to bare means is still accepted and then the
    uncertainty fields come back None, flagged by `n = None`.

    Returns {ratios, D_per_ar, D_joint, spread, means, n, sem, D_ci, sigma}.
    Raises when the base AR group is missing: without the 60-AR denominator
    there is no ratio to fit, and inventing a base would be the exact
    circularity §3.1 struck.

    WHY THE ERROR BARS ARE NOT OPTIONAL, and it is this repo's own rule from
    the other side. The rung-7 run fitted D = 38.16 (from r80) and 39.88 (from
    r100). Quoted bare, those two numbers read as "D is not 40" -- and the
    adversarial review found the opposite: the 95% bootstrap interval for the
    joint estimate is [37.30, 42.00] and contains 40 on both legs (-0.79 sigma
    and -0.11 sigma). A point estimate quoted past the precision its method
    supports is a check that cannot fail, wearing the costume of one that did.
    What actually pins D is the BAND test (`h_fit` supports against the
    predicted endpoints), which has no free parameter at all; this fit is the
    weaker witness and must present itself as such.

    The interval is the delta-method propagation of the per-AR standard error
    through D = -delta / log2(r), which is adequate here and is labelled
    approximate rather than bootstrapped, because a bootstrap belongs to the
    caller that holds the raw samples.
    The fit: r(AR) = 2^(-(AR-base)/D), so log2 r = -delta/D. Least squares
    through the origin over (delta, log2 r) gives 1/D; each AR also gives its
    own D so the report can show the two-estimate consistency the exit
    criterion names. A ratio >= 1 (no attenuation) has no finite D and reports
    None for that AR rather than a complex number.
    """
    if base_ar not in samples_by_ar:
        raise DamagePassError(
            f"no AR={base_ar} group: the divisor fit needs the base-AR "
            f"denominator, and substituting one would be §3.1's circularity")

    def _stat(v):
        """(mean, sem, n) from a sample list, or (value, None, None) from a mean."""
        if isinstance(v, (int, float)):
            return float(v), None, None
        vals = [float(x) for x in v]
        n = len(vals)
        mean = sum(vals) / n
        if n < 2:
            return mean, None, n
        var = sum((x - mean) ** 2 for x in vals) / (n - 1)
        return mean, math.sqrt(var / n), n

    stats = {ar: _stat(v) for ar, v in samples_by_ar.items()}
    base, base_sem, base_n = stats[base_ar]
    if base <= 0:
        raise DamagePassError(f"AR={base_ar} mean is {base}; ratios need a "
                              f"positive denominator")

    ratios, d_per, d_ci, sigma = {}, {}, {}, {}
    means = {ar: s[0] for ar, s in stats.items()}
    sems = {ar: s[1] for ar, s in stats.items()}
    ns = {ar: s[2] for ar, s in stats.items()}
    num = den = 0.0
    for ar in sorted(stats):
        if ar == base_ar:
            continue
        mean, sem, _n = stats[ar]
        delta = ar - base_ar
        r = mean / base
        ratios[ar] = r
        if r >= 1.0 or r <= 0.0:
            d_per[ar] = d_ci[ar] = sigma[ar] = None
            continue
        y = math.log2(r)
        d = -delta / y
        d_per[ar] = d
        num += delta * y
        den += delta * delta
        # Delta method: r's relative error propagates to D through log2.
        if sem is not None and base_sem is not None:
            rel = math.sqrt((sem / mean) ** 2 + (base_sem / base) ** 2)
            r_sem = r * rel
            # dD/dr = delta / (r * (ln2) * y^2)
            d_sem = abs(delta / (r * math.log(2) * y * y)) * r_sem
            d_ci[ar] = (d - 1.96 * d_sem, d + 1.96 * d_sem)
            # How many sigma is the wiki's D=40 from this estimate?
            sigma[ar] = (d - 40.0) / d_sem if d_sem else None
        else:
            d_ci[ar] = sigma[ar] = None

    d_joint = (-den / num) if num else None
    finite = [d for d in d_per.values() if d is not None]
    spread = (max(finite) - min(finite)) if len(finite) >= 2 else None
    return {"ratios": ratios, "D_per_ar": d_per, "D_joint": d_joint,
            "spread": spread, "means": means, "sem": sems, "n": ns,
            "D_ci": d_ci, "sigma_from_40": sigma}


# ---------------------------------------------------------------------------
# the crit variance law

def p17_report(groups):
    """Per scoped p17 group: n, the values, and the zero-variance verdict.

    The registered prediction (B6, gww-facts): a critical always uses the
    maximum base damage, so within one (target, cause) the p17 population has
    variance ZERO while p16 spreads. One differing p17 in a group refutes
    "17 = critical" outright. Also reports the floor(1.414 x max p16)
    cross-fit per (target, cause) where both kinds exist -- as a RATIO of
    fractions, so no H is needed.
    """
    out = []
    p16max = {}
    for (tkey, cause, kind, step), rows in groups.items():
        if kind == 16 and rows:
            p16max[(tkey, cause, step)] = max(abs(r["frac"]) for r in rows)
    for (tkey, cause, kind, step), rows in sorted(
            groups.items(), key=lambda kv: str(kv[0])):
        if kind != 17:
            continue
        vals = [abs(r["frac"]) for r in rows]
        distinct = sorted(set(vals))
        # The cross-fit compares within the SAME block: a rank-13 crit against
        # a rank-11 p16 max would test nothing but the pooling mistake.
        mx = p16max.get((tkey, cause, step))
        out.append({
            "target": tkey, "cause": cause, "step": step, "n": len(vals),
            "values": vals, "variance_zero": len(distinct) == 1,
            "p16_max": mx,
            "ratio_to_p16max": (distinct[-1] / mx) if mx else None,
        })
    return out


# ---------------------------------------------------------------------------
# mark windows: the sealed plan labels the blocks, nothing else does

AR_RE = re.compile(r"\bAR=(\d+)\b")
RANK_RE = re.compile(r"\bRANK=(\d+)\b")
H_RE = re.compile(r"\bH=(\d+)\b")


def mark_windows(capture_dir):
    """[(step, text, t0, t1)] in wire time, from plan_marks.jsonl.

    A window opens at the step's `advance` mark and closes at the next advance
    (the last runs to +inf). Repeats extend their own step, so they need no
    handling; a capture with no marks file returns [] -- census mode still
    works, labelling just cannot.
    """
    path = os.path.join(capture_dir, "plan_marks.jsonl")
    if not os.path.exists(path):
        return []
    advances = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("kind") == "mark" and rec.get("mark") == "advance":
                advances.append((rec["step"], rec.get("text", ""),
                                 rec["wire_t"]))
    windows = []
    for i, (step, text, t0) in enumerate(advances):
        t1 = advances[i + 1][2] if i + 1 < len(advances) else math.inf
        windows.append((step, text, t0, t1))
    return windows


def window_at(windows, t):
    """The (step, text, t0, t1) whose window holds `t`, or None."""
    for w in windows:
        if w[2] <= t < w[3]:
            return w
    return None


def label_groups(groups, windows):
    """{group_key: {"ar": int|None, "rank": int|None}} from the plan's own
    step text -- the ONLY place a label may come from (pre-registered, sealed).

    `AR=NN` names the target's armour rating as the operator's nameplate
    witnesses it; `RANK=NN` declares a rank-extension block, which the divisor
    fit must EXCLUDE (a rank change moves the numerator for reasons that are
    not armour). With step in the group key a group sits inside one window by
    construction; the multi-AR refusal is kept as a guard for step-less
    groups and repeat anomalies -- one body engaged under two labels is a run
    error to investigate, not a number to average.
    """
    labels = {}
    for key, rows in groups.items():
        ars, ranks = set(), set()
        for r in rows:
            w = window_at(windows, r["t"])
            if w:
                m = AR_RE.search(w[1])
                if m:
                    ars.add(int(m.group(1)))
                m = RANK_RE.search(w[1])
                if m:
                    ranks.add(int(m.group(1)))
        if len(ars) > 1 or len(ranks) > 1:
            raise DamagePassError(
                f"group {key} has events under {len(ars)} AR / {len(ranks)} "
                f"RANK labels ({sorted(ars)}, {sorted(ranks)}): one body "
                f"engaged under two labels is a run error to investigate, "
                f"not a number to average")
        labels[key] = {"ar": ars.pop() if ars else None,
                       "rank": ranks.pop() if ranks else None}
    return labels


# ---------------------------------------------------------------------------
# the assembled report

def report(capture_dir, connection, codec=None):
    """The full rung-7 readout for one connection: census + fits where possible."""
    ev = join_targets(read_events(capture_dir, connection, codec))
    windows = mark_windows(capture_dir)
    groups = scoped_groups(ev, windows)

    rep = {
        "capture": ev["capture"], "connection": connection,
        "origin": ev["origin"], "map_id": ev["map_id"],
        "counts": {
            "damage": len(ev["damage"]),
            "by_kind": {k: sum(1 for d in ev["damage"] if d["kind"] == k)
                        for k in DAMAGE_KINDS},
            "unjoined": ev["unjoined"],
            "health_max": len(ev["health_max"]),
            "chat_5d": sum(1 for c in ev["chat"] if c["op"] == OP_CHAT_CODED),
            "casts": len(ev["casts"]),
            "projectiles": len(ev["projectiles"]),
        },
        "groups": [], "p17": p17_report(groups), "divisor": None,
        "rank_curve": [],
    }

    labels = label_groups(groups, windows) if windows else {}
    means_by_ar, ar_basis = {}, {}
    for key, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
        tkey, cause, kind, step = key
        fracs = [r["frac"] for r in rows]
        fit = h_fit(fracs) if kind in (16, 17) else None
        lab = labels.get(key, {"ar": None, "rank": None})
        g = {"target": tkey, "cause": cause, "kind": kind, "step": step,
             "n": len(rows),
             "mean_frac": sum(abs(f) for f in fracs) / len(fracs),
             "h_fit": fit, "ar": lab["ar"], "rank": lab["rank"]}
        rep["groups"].append(g)
        if kind == 16 and g["ar"] is not None and g["rank"] is not None:
            # A rank-extension block: feeds the rank curve, NEVER the divisor
            # fit -- a rank change moves damage for non-armour reasons.
            rep["rank_curve"].append(g)
        elif kind == 16 and g["ar"] is not None:
            # Points when the grid gave H back, fractions otherwise; a mixed
            # basis across AR groups is refused at the fit below.
            if fit:
                h0, pts = fit
                means_by_ar.setdefault(g["ar"], []).extend(pts)
                ar_basis[g["ar"]] = "points"
            else:
                means_by_ar.setdefault(g["ar"], []).extend(
                    abs(f) for f in fracs)
                ar_basis[g["ar"]] = "fractions"

    if means_by_ar:
        if len(set(ar_basis.values())) > 1:
            raise DamagePassError(
                f"AR groups on mixed bases {ar_basis}: points and fractions "
                f"cannot share one ratio; either every group's H recovered or "
                f"none did")
        if 60 in means_by_ar and len(means_by_ar) >= 2:
            # RAW SAMPLES, not pre-averaged means: the fit needs the per-hit
            # spread to put an interval on D, and a bare D reads as a refutation
            # of 40 when it is nothing of the kind (see divisor_fit's docstring).
            rep["divisor"] = divisor_fit(means_by_ar)
            rep["divisor"]["basis"] = next(iter(set(ar_basis.values())))
            # Body count per AR: the ratio's real error budget includes
            # body-to-body variance, and an AR resting on ONE body cannot show
            # it. The rung-7 run had 2 bodies at AR60 and 1 each at 80/100.
            bodies = {}
            for g in rep["groups"]:
                if g["kind"] == 16 and g["ar"] is not None and g["rank"] is None:
                    bodies.setdefault(g["ar"], set()).add(g["target"])
            rep["divisor"]["bodies_per_ar"] = {
                ar: len(v) for ar, v in bodies.items()}
    return rep


def _fmt_target(tkey):
    if tkey is None:
        return "unjoined"
    if tkey[0] == "agent":
        return f"agent {tkey[1]} (player-class, created t={tkey[2]:.1f})"
    tag, definition, model, pos, plane = tkey
    return (f"{agentroster.TAG_NAMES[tag]} slot {definition} model {model} "
            f"pos {pos} plane {plane}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", required=True, help="stamp under captures/live")
    ap.add_argument("--connection", help="one connection (default: all game)")
    ap.add_argument("--json", action="store_true", help="machine output")
    args = ap.parse_args()

    cap_dir = vaultpath.require_dir(
        "captures", "live", args.capture,
        why="damagepass reads live captures from the vault")
    conns = ([{"connection": args.connection}] if args.connection
             else tape.channel_files(cap_dir))
    codec = Codec()
    for row in conns:
        rep = report(cap_dir, row["connection"], codec)
        if args.json:
            print(json.dumps(rep, default=str))
            continue
        c = rep["counts"]
        if not c["damage"] and not c["chat_5d"]:
            continue
        print(f"{rep['capture']} {rep['connection']} map={rep['map_id']} "
              f"origin={rep['origin']}")
        print(f"  damage {c['damage']} (16/17/18 = "
              f"{c['by_kind'][16]}/{c['by_kind'][17]}/{c['by_kind'][18]}), "
              f"unjoined {c['unjoined']}, hmax {c['health_max']}, "
              f"5D {c['chat_5d']}, casts {c['casts']}, "
              f"projectiles {c['projectiles']}")
        for g in rep["groups"]:
            if g["n"] < 2:
                continue
            if g["h_fit"]:
                h0, pts = g["h_fit"]
                # The band is the readable form of the weapon's damage range:
                # p16 spreads over the rolled range, a crit pins to its top.
                h = f"H0={h0} points {min(pts)}..{max(pts)}"
            else:
                h = "H unfit"
            ar = f" AR={g['ar']}" if g["ar"] is not None else ""
            rk = f" RANK={g['rank']}" if g["rank"] is not None else ""
            st = f" step={g['step']}" if g["step"] is not None else ""
            print(f"    kind {g['kind']} n={g['n']} mean|f|="
                  f"{g['mean_frac']:.5f} {h}{ar}{rk}{st} <- cause "
                  f"{g['cause']} vs {_fmt_target(g['target'])}")
        for p in rep["p17"]:
            if p["n"] >= 2:
                print(f"    p17 LAW n={p['n']} variance_zero="
                      f"{p['variance_zero']} values={p['values']} vs "
                      f"{_fmt_target(p['target'])}")
        if rep["divisor"]:
            d = rep["divisor"]
            print(f"    DIVISOR basis={d['basis']} "
                  f"bodies/AR={d.get('bodies_per_ar')}")
            for ar in sorted(d["ratios"]):
                sem = d["sem"].get(ar)
                ci = d["D_ci"].get(ar)
                sig = d["sigma_from_40"].get(ar)
                print(f"      AR={ar}: mean={d['means'][ar]:.4f}"
                      f"{f' +/- {sem:.4f}' if sem else ''} "
                      f"n={d['n'].get(ar)}  r={d['ratios'][ar]:.4f} "
                      f"(wiki {2 ** (-(ar - 60) / 40):.4f})  "
                      f"D={d['D_per_ar'][ar]:.2f}"
                      f"{f' 95% CI [{ci[0]:.2f}, {ci[1]:.2f}]' if ci else ''}"
                      f"{f'  {sig:+.2f} sigma from 40' if sig is not None else ''}")
            print(f"      joint D={d['D_joint']:.2f}  spread={d['spread']:.2f}"
                  if d["D_joint"] else "      joint D=None")
            print(f"      NOTE: the BAND test (per-group h_fit supports vs the "
                  f"predicted endpoints) is the stronger witness; this fit has "
                  f"a free parameter and these intervals are wide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
