r"""What a skill row says, and who a cast lands on.

THE READERS ONLY. Nothing here sends a message, knows an opcode or holds a
connection. These five are pure reads -- two over the `skills` table in
`agents.WORLD`, three over the caster's own state dict -- and they are the half
of the skill path that runs with a bare state and no vault.

WHY A MODULE. The two scale readers carry the CLIENT's own interpolator and the
refusal rule that took three shapes before it settled; the three targeting
readers carry the client's target byte, whose ally/other-ally split closed on
2026-09-10. Their callers -- `skill_damage`, `skill_heal`, `glyph_energy_amount`,
`skill_condition`, `resolve_heal`, `enemy_attack_tick`, and the taker and
preparation modifiers in `episodemods.py` -- all decide something and several of
them send. The seam is between reading a row and doing anything about it.

WHAT STAYS IN `authsrv.py`, because a moved comment's referent has to be
findable from here:

  * `PLAYER_AGENT_ID` (authsrv.py:3022), the only module-level VALUE any of this
    code read. `allies_of` takes it as a parameter under that exact name, so the
    body travels verbatim and the value is read at the CALL -- never bound as a
    default, which would be evaluated once at `def` time and freeze it.
  * `ENEMY_SKILL_RANK`, the rank a monster casts at, which sat immediately above
    `skill_scale_value`.
  * `--enemies N`, the flag `allies_of`'s docstring names, and `land_skill` /
    `resolve_heal`, which turn `cast_recipient`'s verdict into a wire.

`skill_scale_value`'s `import math` is deliberately function-local: the
docstring's half-up rounding note is about that line.

Standard library only, and no import of the server: `authsrv.py` imports THIS
file, never the other way round, because `authsrv.py` runs as `__main__` and an
import back would load a second copy whose flags `main()` never set.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402
import effects  # noqa: E402


def skill_scale_value(skill_id, rank, which="scale"):
    """A skill's attribute-scaled value at `rank`, by the CLIENT's own formula.

    MEASURED, at 0x005A8920 -- one general-purpose interpolator the client uses
    for the scale, bonus-scale and duration sets alike (studies/combat 8c):

        value(rank) = max(0, round(lo + (hi - lo) * rank / 15.0))

    with the divisor a literal double 15.0 (verified by a stdlib read of
    0x0094B930: bytes 0000000000002e40) and NO upper clamp on rank, so ranks
    above 15 extrapolate rather than saturating. The floor at zero is
    ArenaNet's own assert, ConstSkill:3769 `(int)result >= 0`.

    THE BITFIELD IS HONOURED, and it is not optional. `skill_arguments` (+0x58)
    enables each set -- 1 duration, 2 scale, 4 bonus -- and a disabled set's
    slot can still hold a meaningful CONSTANT: Rush's scale slot holds 25, the
    "move 25% faster" in its description, with the bit clear. Reading endpoints
    without the bit invents a progression the game never draws, so a disabled
    set raises here rather than returning a plausible number.

    THE ROUNDING TIE-BREAK IS UNRESOLVED (studies/combat 8c): the client's CRT
    helper adjusts by +/-1.0 rather than the textbook +/-0.5 before truncating,
    and half-up vs half-even was not settled. Python's round() is half-EVEN, so
    this uses explicit half-up -- a choice, recorded here, and one that cannot
    currently bite: no skill this server resolves lands on a .5, which
    test_skilldamage asserts rather than leaves to luck.
    """
    import math
    row = agents.WORLD.get("skills", str(skill_id))
    bit = {"scale": 2, "bonus_scale": 4, "duration": 1}[which]
    if not int(row["skill_arguments"]) & bit:
        raise ValueError(
            f"skill {skill_id} has its {which} set DISABLED "
            f"(skill_arguments = {row['skill_arguments']}), so its "
            f"{which}0/{which}15 slots are not a progression. Rush's scale "
            f"slot holds 25 with this bit clear and the wiki lists no scale "
            f"progression for it; reading the endpoints anyway would invent "
            f"one. Refusing rather than returning a plausible number.")
    lo, hi = int(row[f"{which}0"]), int(row[f"{which}15"])
    exact = lo + (hi - lo) * rank / 15.0
    return max(0, int(math.floor(exact + 0.5)))


def skill_flat_constant(skill_id, which="scale"):
    """A skill's bit-clear FLAT constant, or a refusal. The other half of
    `skill_scale_value`'s rule.

    That function refuses any disabled set, which is right for a PROGRESSION --
    but a disabled slot with EQUAL endpoints is a different shape with real
    witnesses: Rush's scale holds 25/25 ("move 25% faster"), Frenzy's 33/33
    ("attack 33% faster"), Faintheartedness's 50/50 ("attack 50% slower"), the
    glyph's bonus 2/2 ("your next 2 spells") -- each a flat number from the
    skill's own description, sitting in a slot the bitfield does not enable
    because there is nothing to interpolate. `effects.resolve_duration` already
    honours the same shape for the duration slot, forced by retail (984/998).

    Refused: a bit-SET slot (that is a progression -- use skill_scale_value at
    a rank, not this) and bit-clear with DIFFERING endpoints (zero witnesses
    anywhere; the glyph's 10..18 scale is the canonical case and its amount
    enters through an explicit content field instead).
    """
    row = agents.WORLD.get("skills", str(skill_id))
    bit = {"scale": 2, "bonus_scale": 4, "duration": 1}[which]
    if int(row["skill_arguments"]) & bit:
        raise ValueError(
            f"skill {skill_id}'s {which} set is ENABLED -- it is a "
            f"progression, not a flat constant. skill_scale_value is the "
            f"reader for it.")
    lo, hi = int(row[f"{which}0"]), int(row[f"{which}15"])
    if lo != hi:
        raise ValueError(
            f"skill {skill_id}'s {which} slots differ ({lo} vs {hi}) with the "
            f"bit clear -- not a constant, not an enabled progression, and no "
            f"corpus witness says what such a pair means. Refusing.")
    return lo


def allies_of(state, caster_id, PLAYER_AGENT_ID):
    """Living agents allied with the caster, by id. A pure read.

    The player has none today -- no heroes, no henchmen, no party -- so the
    set is empty and every "other ally" spell the player casts has no legal
    recipient, which is what the client itself refuses. A hostile's allies are
    the other living agents carrying the same allegiance word (the spawn's own
    FourCC, `agents.ALLEGIANCE_HOSTILE`), which `--enemies N` produces.
    """
    if caster_id == PLAYER_AGENT_ID:
        return set()
    table = state.get("agents", {})
    me = table.get(caster_id)
    if not me:
        return set()
    return {aid for aid, a in table.items()
            if aid != caster_id and not a.get("dead")
            and a.get("allegiance") == me.get("allegiance")}


def skill_target_kind(skill_id):
    """'self' | 'ally' | 'other_ally' | 'foe' | None, from the client's byte.

    None for an unresolved code (1, 6, 14, 16) and for a skill with no content
    row -- the bare-machine case -- and both fall through to the caster's own
    choice, as `effects.effect_recipient` always has.
    """
    try:
        row = agents.WORLD.get("skills", str(skill_id))
    except Exception:                                          # noqa: BLE001
        return None
    return effects.TARGET_KINDS.get(int(row["target"]))


def cast_recipient(skill_id, caster_id, target_id, allies):
    """Who a cast lands on, or None when the client's target byte forbids it.

    self       -> the caster, whatever was selected (Healing Signet mid-fight).
    ally       -> the selected ally, else the caster: an ally spell aimed at a
                  foe lands on yourself, which is what the client does with the
                  press (RECONSTRUCTION of the client's auto-self; the wiki
                  rule is only that the caster IS a legal target).
    other_ally -> the selected ally and never the caster: no ally, no cast.
    foe / None -> the selected target, else the caster (the old fall-through).
    """
    kind = skill_target_kind(skill_id)
    if kind == "self":
        return caster_id
    if kind == "ally":
        return target_id if target_id in allies else caster_id
    if kind == "other_ally":
        if target_id in allies and target_id != caster_id:
            return target_id
        return None
    return target_id or caster_id
