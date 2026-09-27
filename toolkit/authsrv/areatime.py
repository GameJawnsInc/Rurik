"""An area over TIME -- the predicate and the schedule, pure (DESKWORK-D6 step 2,
studies/weapons/PLAN.md 42; the tape read is 41).

Fire Storm (197) is the witness: 17 casts on the live tape `20260817T231139`,
read by `aotjoin.py` with the predictions stated first (P1-P9, all PASS).
What this leaf holds is the part of that mechanism that is a number in and a
number out -- which record rows ARE an area over time, and WHEN an opened
area does something. Everything that sends, reads a taker's armour or walks
`state` stays in `authsrv.py` (`open_area`, `area_tick`), which re-exports
these three names at its section-42 site.

  * `area_over_time_row(row)` -- the record's shape: target byte 16, a Spell
    (type 5), no projectile of its own, a duration on either endpoint, and an
    `aoe_range` above 0. OBSERVED on the pinned skills table (build 38797):
    exactly the FOURTEEN rows aotjoin.classify names (weapons 41). It is
    deliberately NOT `spell_burst` widened: that predicate REFUSES a duration
    (`spell_burst(197) is None` is locked in test_weapons 28 and
    test_skilldamage), and a burst and an area over time are two wire shapes.
    The duration returned is the row's larger endpoint -- the predicate's
    witness that the row lasts; the duration AT A RANK is the caller's, through
    the server's one duration rule (`effects.resolve_duration`), never a second
    interpolation here.
  * `tick_instants(t0, duration, period)` -- the instants the area strikes:
    `t0 + k * period` for k = 1 .. floor(duration / period). OBSERVED for Fire
    Storm (period 1.0, duration 10): ticks at the completion + 1 .. + 10, NO
    tick at the completion itself and none at + 11 (79 tick instants on the
    tape, phase within 0.020 s of the whole second). ALWAYS from `t0`, never
    previous + period: a tick served late (the world tick's 50 ms grid under
    --no-combat-deadlines, or a busy slice) is late by that much and the NEXT
    one is back on the second -- the phase never drifts.
  * `visual_instants(t0, duration, period, tail)` -- when the ground effect is
    (re-)drawn: `t0 + j * period` while `j * period <= duration - tail`. Fire
    Storm: 0, 3, 6 (OBSERVED 17/17: the 350 in the completion batch, re-sent at
    + 3.0 and + 6.0, none at + 9, no end marker). The 3 s period and the 4 s
    tail are FITTED to that one skill's duration of 10 -- one witness, so for
    any other duration this is RECONSTRUCTION (d = 9 gives [0, 3]; d = 5 gives
    [0]), said here and at the call site.

  * `area_hex_row(row)` -- the AREA HEX's shape (DESKWORK-D6 step 4, weapons
    43): target byte 16, a Hex (type 4), an `aoe_range` above 0. OBSERVED on
    the pinned skills table: exactly the SEVEN rows aotjoin.classify names
    (52, 56, 108, 136, 204, 211, 234). The radius is the record's own; the
    duration and every per-wearer number are the server's readers'.

Standard library only, and no import of the server -- test_weapons sections 30
and 31 drive all four with no vault.
"""
import math

NO_PROJECTILE = (0, 2077)       # the record's "the weapon's own" values (authsrv SKILL_NO_PROJECTILE)
AREA_TARGET = 16                # the record's target byte for "target foe and the foes around it"
SPELL_TYPE = 5                  # the record's type byte for a Spell
HEX_TYPE = 4                    # the record's type byte for a Hex Spell (effects.EFFECT_TYPES)


def area_over_time_row(row, projectile_none=NO_PROJECTILE):
    """(radius, duration) when the RECORD row is an area over time -- target 16,
    type 5, no own projectile, a duration on either endpoint, a radius -- else
    None. Pure: a dict in, a pair or None out; `duration` is the larger
    endpoint (the rank's is the caller's, see the module docstring)."""
    if not isinstance(row, dict):
        return None
    try:
        if int(row.get("target", -1)) != AREA_TARGET:
            return None
        if int(row.get("type_code", -1)) != SPELL_TYPE:
            return None
        own = row.get("projectile")
        if own is not None and int(own) not in projectile_none:
            return None
        lo = int(row.get("duration0", 0) or 0)
        hi = int(row.get("duration15", 0) or 0)
        radius = float(row.get("aoe_range", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if max(lo, hi) <= 0 or radius <= 0.0:
        return None
    return radius, float(max(lo, hi))


def area_hex_row(row):
    """The radius when the RECORD row is an AREA HEX -- target 16, type 4, an
    `aoe_range` above 0 -- else None. Pure: a dict in, a float or None out.
    The duration is NOT read here (a hex's is `effects.resolve_duration`'s,
    per wearer at the caster's rank), and a projectile is not refused: no
    hex row carries one, and a hex that did would still be a hex."""
    if not isinstance(row, dict):
        return None
    try:
        if int(row.get("target", -1)) != AREA_TARGET:
            return None
        if int(row.get("type_code", -1)) != HEX_TYPE:
            return None
        radius = float(row.get("aoe_range", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    return radius if radius > 0.0 else None


def tick_instants(t0, duration, period=1.0):
    """The absolute instants an area opened at `t0` strikes: t0 + k * period
    for k = 1 .. floor(duration / period) -- never at t0, always from t0."""
    t0, duration, period = float(t0), float(duration), float(period)
    if period <= 0.0 or duration <= 0.0:
        return []
    n = int(math.floor(duration / period + 1e-9))
    return [t0 + k * period for k in range(1, n + 1)]


def visual_instants(t0, duration, period=3.0, tail=4.0):
    """The absolute instants the ground effect is drawn: t0 + j * period for
    j >= 0 while j * period <= duration - tail (Fire Storm: t0, t0 + 3, t0 + 6
    -- OBSERVED; the period and the tail are fitted to duration 10, so any
    other duration is RECONSTRUCTION)."""
    t0, duration, period = float(t0), float(duration), float(period)
    if period <= 0.0:
        return [t0]
    out, j = [], 0
    while j * period <= duration - float(tail) + 1e-9:
        out.append(t0 + j * period)
        j += 1
    return out or [t0]
