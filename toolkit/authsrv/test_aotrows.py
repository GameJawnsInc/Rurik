"""test_aotrows.py -- five more areas over time go live (studies/weapons/PLAN.md 45).

Breath of Fire 1094, Snow Storm 2222, Ray of Judgment 830, Spirit Rift 910 and
Savannah Heat 1380 carried no skill_effect row and were inert (weapons 42). They
carry CLIENT-TABLE rows now (content/world.toml, after 167's): the record's numbers
and the client's own description-template labels (skilldesc.py over the pinned 38797
client, read as a tool). 1094 and 2222 are rows only; 830's Burning rides EVERY tick
(Eruption's shape); 910's `tick_period` is its 3 s, so it strikes ONCE at +3.0 and
applies Cracked Armor; 1380's `tick_ramp = "elapsed"` makes tick k deal k x its scale
(authsrv.area_tick_ramp, areatime.tick_amount; --no-area-tick-ramp reverts). NONE was
ever cast on a live tape, so the wire is Fire Storm's OBSERVED shape reused --
RECONSTRUCTION -- and what this file locks is that the server produces it from the rows.

And the caster's death (weapons 45): the area OUTLIVES it, OBSERVED n = 1 on the
second Zaishen tape (20260929T100038 :51199, the Fire Storm announced at 562.188: the
caster dead at completion + 8.487, a clean tick at + 9.989 on foes 4 and 6). Section 6
re-derives that witness with aotjoin and holds the server's locked behaviour against it.

    python toolkit/authsrv/test_aotrows.py

THE BARE MACHINE. The `skills` table is vault-only, so the record rows the sections
read are CARRIED here (RECORD, build 38797's own rows, identical on 38888 and 38974 for
these ids) and REPLACE the table for each block -- a vault run takes exactly the bare
path. Section 1b checks the carried rows against the vault's, and section 6 reads the
live corpus; both skip on an absent vault DIRECTORY (vaultpath.require_dir) and never
on an empty result. The skill_effect rows are repo content and always load.

CROSS-LANE (2026-10-07): desk-chan55 moves armour-ignoring spell damage (830's Holy
damage among it) from property 16 to property 55 this pass. Every check here reads a
damage word on ANY damage channel (16 / 17, or 55 with a negative fraction) EXCEPT the
one check in section 3 that pins 830's channel, which says so and is the orchestrator's
to re-point at merge.
"""
import argparse
import ast
import contextlib
import io
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks  # noqa: E402
import agents  # noqa: E402
import authsrv  # noqa: E402
import areatime  # noqa: E402
import vaultpath  # noqa: E402

# The floor is decided on the vault's DIRECTORIES, never on what loaded (the house
# rule, test_agentlife's FLOOR_VAULT / FLOOR_BARE): a vault whose tables did not load
# still owes the vault floor and goes red.
# MEASURED 2026-10-07: 24 checks bare (RURIK_VAULT at a nonexistent path AND at an
# empty directory, both green with 2 declared skips), 28 on the vault (24 + section
# 1b's 1 + section 6's 3). Each vault directory adds the checks its section runs.
HAVE_VAULT_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_LIVE = os.path.isdir(vaultpath.vault_path("captures", "live"))
FLOOR_BARE = 24
FLOOR = FLOOR_BARE + (1 if HAVE_VAULT_CONTENT else 0) + (3 if HAVE_LIVE else 0)
LEDGER = checks.Ledger("areas over time: five client-table rows and the caster's death "
                       "(weapons 45)", floor=FLOOR)
check = LEDGER.ok

PLAYER, FOE, HERO = 1, 10, 200
A1 = 0x00A1
FIVE = (1094, 2222, 830, 910, 1380)


def _record(activation, recharge, energy, attribute, profession, target, aoe_range,
            skill_arguments, duration, scale, bonus_scale, impact_visual=2077,
            type_code=5, adrenaline=(0, 0)):
    return {"activation": activation, "aftercast": 0.75, "recharge": recharge,
            "energy": energy, "adrenaline": adrenaline[0], "adrenaline_units": adrenaline[1],
            "attribute": attribute, "profession": profession, "type_code": type_code,
            "target": target, "combo": 0, "combo_req": 0, "weapon_req": 0,
            "aoe_range": aoe_range, "skill_arguments": skill_arguments,
            "duration0": duration[0], "duration15": duration[1], "scale0": scale[0],
            "scale15": scale[1], "bonus_scale0": bonus_scale[0],
            "bonus_scale15": bonus_scale[1], "projectile": 2077,
            "impact_visual": impact_visual, "touch_range": False, "half_range": False}


# The record's rows, skilltable.py on build 38797 (RECORD_BUILD) -- measured numbers,
# CLAUDE.md's gate. 1094 / 2222 / 830 / 910 / 1380 are identical on 38888 and 38974
# (compared 2026-10-07 against vault/research's two snapshots and the 38974 overlay).
RECORD = {
    "1094": _record(2.0, 10, 5, 10, 6, 16, 156.0, 3, (5, 5), (10, 40), (0, 0)),
    "2222": _record(1.0, 10, 10, 51, 0, 16, 156.0, 3, (5, 5), (30, 40), (0, 0)),
    "830": _record(1.0, 15, 10, 14, 3, 16, 156.0, 7, (5, 5), (10, 50), (1, 3),
                   impact_visual=1019),
    "910": _record(2.0, 5, 10, 34, 8, 16, 156.0, 7, (3, 3), (25, 125), (1, 20)),
    "1380": _record(2.0, 25, 5, 10, 6, 16, 240.0, 7, (5, 5), (5, 20), (5, 20)),
    "197": _record(2.0, 20, 10, 10, 6, 16, 156.0, 2, (10, 10), (5, 35), (33, 33),
                   impact_visual=351),                                   # Fire Storm
    "317": dict(_record(0.0, 0, 0, 17, 1, 0, 0.0, 1, (5, 20), (33, 33), (0, 0), type_code=3,
                        adrenaline=(4, 80)), aftercast=0.0),   # the default bar's adrenal stance
}
RECORD_BUILD = 38797
# The ranks the player is handed: 12 in each of the five's attributes -- Fire Magic
# 10, Smiting Prayers 14, Channeling Magic 34, and 51 (2222's: no attribute; a player
# never holds a rank in it, so this is the test reading the interpolator at 12, said).
PLAYER_RANKS = ((10, 12), (14, 12), (34, 12), (51, 12))
RANK = 12


@contextlib.contextmanager
def _carried():
    """WORLD's skills table REPLACED by RECORD for the block, then put back."""
    tables = agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    tables["skills"] = {k: dict(v) for k, v in RECORD.items()}
    try:
        yield
    finally:
        if had:
            tables["skills"] = kept
        else:
            del tables["skills"]


@contextlib.contextmanager
def _row(sid, row):
    """skill_effect `sid` REPLACED by `row` (None: deleted) for the block."""
    table = agents.WORLD.tables.setdefault("skill_effect", {})
    had, kept = str(sid) in table, table.get(str(sid))
    if row is None:
        table.pop(str(sid), None)
    else:
        table[str(sid)] = row
    try:
        yield
    finally:
        if had:
            table[str(sid)] = kept
        else:
            table.pop(str(sid), None)


def _f(word):
    if isinstance(word, float):
        return word
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def words(batch):
    """Damage words on ANY damage channel: 16 / 17, or 55 with a NEGATIVE fraction
    (desk-chan55's armour-ignoring channel) -- [prop, taker, cause, frac]."""
    return [v for op, v in batch if op == 0x00A3
            and (v[0] in (16, 17) or (v[0] == 55 and _f(v[3]) < 0.0))]


def grounds(batch):
    return [v for op, v in batch if op == A1]


def fin58(batch):
    return [v for op, v in batch if op == 0x009F and v[0] == 58]


def impacts(batch):
    return [v for op, v in batch if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]


def arrivals(batch):
    return [v for op, v in batch if op == 0x00A7]


def ops(batch):
    return [op for op, _v in batch]


def clean(batch):
    """A tick's batch as the tape has it: no 58, no [20], no 0x00A7 (weapons 41)."""
    return not fin58(batch) and not impacts(batch) and not arrivals(batch)


def _world():
    """The player at the origin at level 20 (so 3 x level = 60 meets the suits' 60 at
    exactly x1 and a word carries the stated amount), the target hostile at 600 u."""
    entry = {"name": "suit", "dead": False, "died_at": 0.0,
             "health": 9000.0, "max_health": 9000.0, "last_hit": 0.0,
             "pos": (600.0, 0.0), "plane": 0, "armor_rating": 60.0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": False, "skills": (), "skill_ready": []}
    return {"agents": {FOE: entry}, "pos": (0.0, 0.0), "player_health": 480.0, "level": 20}


def _body_world(hostile_pos, **hostile):
    """A player at the origin, one hostile (agent 10) and one party caster (200) 110 u
    off the player -- test_weapons' _body_world, the monk made to outlive the area."""
    foe = {"name": "caster", "dead": False, "died_at": 0.0, "health": 200.0,
           "max_health": 200.0, "last_hit": 0.0, "pos": hostile_pos, "plane": 0,
           "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 1.75,
           "effects": 0, "attacks_back": True, "skills": (), "skill_ready": [],
           "npc": {"profession": 6, "level": 5}}
    foe.update(hostile)
    monk = {"name": "monk", "dead": False, "died_at": 0.0, "health": 9000.0,
            "max_health": 9000.0, "last_hit": 0.0, "pos": (0.0, 110.0), "plane": 0,
            "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0, "attack_speed": 1.75,
            "attacks_back": False, "skills": (), "skill_ready": [],
            "npc": {"profession": 3, "level": 5}, "party_slot": 0,
            "weapon_item": "caster_staff"}
    return {"agents": {FOE: foe, HERO: monk}, "pos": (0.0, 0.0),
            "player_health": 480.0, "player_dead": False}


def _advance(st, send, seconds):
    """Move every open area's clock back by `seconds` and serve through the REAL
    projectile_tick (test_weapons 30's _aot_advance)."""
    for area in st.get("areas") or ():
        area["t0"] -= seconds
        area["ticks"] = [t - seconds for t in area["ticks"]]
        area["visuals"] = [t - seconds for t in area["visuals"]]
    authsrv.projectile_tick(send, st, 1)


class _Patched:
    """The press path's neighbours pinned as test_weapons 30 pins them -- timing,
    cost, the weapon gate -- and NOT skill_damage: the amounts are the interpolator's."""

    def __enter__(self):
        self.saved = (authsrv.skill_timing, authsrv.skill_cost, authsrv.weapon_satisfies,
                      agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, agents.PLAYER_ATTRIBUTE_RANKS,
                      authsrv.apply_condition, authsrv.AREA_TICK_RAMP,
                      authsrv.AREAS_OVER_TIME, authsrv.SPELL_AREAS, authsrv.ATTACK_INTERVAL,
                      authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE)
        # recharge 5, not 0 (SLICE-F52 52.8): a 0-recharge completion sends no E5
        authsrv.skill_timing = lambda sid: (2.0, 0.75, 5.0)
        # Battle Rage (317, on the default bar) keeps its 80 raw units, so the bar reads
        # LIT and a body's tick on the player owes the 0x00CF gain (test_weapons 30 (d))
        authsrv.skill_cost = lambda sid: (0, 80) if sid == 317 else (0, 0)
        authsrv.weapon_satisfies = lambda sid: True
        authsrv.apply_party_character({"player_weapon": "starter_wand"})
        agents.PLAYER_ATTRIBUTE_RANKS = PLAYER_RANKS
        self.conds = []
        real = self.saved[6]

        def recording(send, state, target_id, condition_id, seconds, rank, *a, **kw):
            self.conds.append((target_id, condition_id, float(seconds)))
            return real(send, state, target_id, condition_id, seconds, rank, *a, **kw)
        authsrv.apply_condition = recording
        return self

    def __exit__(self, *exc):
        (authsrv.skill_timing, authsrv.skill_cost, authsrv.weapon_satisfies,
         agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, agents.PLAYER_ATTRIBUTE_RANKS,
         authsrv.apply_condition, authsrv.AREA_TICK_RAMP,
         authsrv.AREAS_OVER_TIME, authsrv.SPELL_AREAS, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE) = self.saved
        return False


def _outside(sid):
    """A hostile 44 u past the record's radius from the target -- outside every tick."""
    return (600.0 + float(RECORD[str(sid)]["aoe_range"]) + 44.0, 0.0)


def player_cast(sid, extra=None):
    """The player's cast of `sid` at FOE through the REAL press and E5, with three
    hostiles inside the radius (the target, 11 at 50 u, 13 at 100 u) and one outside
    (12). Returns (state, the E5 batch, send)."""
    st, sent = _world(), []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    for aid, pos in (extra or [(11, (650.0, 0.0)), (13, (600.0, 100.0)), (12, _outside(sid))]):
        st["agents"][aid] = dict(st["agents"][FOE], pos=pos)
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_skill_press([0, sid, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
    sent.clear()
    for cast in st["pending_casts"]:
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            cast[k] -= 30.0
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.cast_tick(send, st, 1)
    return st, list(sent), send, sent


def serve(st, sent, send, seconds, steps, mutate=None):
    """Serve `steps` instants `seconds` apart; per step (offset, [(taker, frac)],
    the batch). `mutate(st, k)` runs after step k (a known-bad arm's hook)."""
    out = []
    for i in range(1, steps + 1):
        sent.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            _advance(st, send, seconds)
        batch = list(sent)
        out.append((round(i * seconds, 6), [(v[1], _f(v[3])) for v in words(batch)], batch))
        if mutate is not None:
            mutate(st, i)
    return out


def expected_amount(sid):
    """The per-tick amount the area carries: the RECORD's scale at RANK through the
    client's own interpolator (skillread.skill_scale_value) -- never typed."""
    return float(authsrv.skill_scale_value(sid, RANK))


def schedule_ok(sid, st, e5, served, period, ramp=False, inside=(FOE, 11, 13)):
    """THE PREDICATE every arm is scored by: the E5 opens the area at the target's
    position with no word and no ground effect (no `area_visual` is known for any
    of the five); the ticks fall at exactly tick_instants(t0, duration, period) and
    nowhere else; each strikes exactly the hostiles inside the radius (never the one
    outside), clean (no 58, no [20], no 0x00A7), each word -amount / 9000 with the
    amount the interpolator's (x k under the ramp); the area closes after its last
    tick. Returns (ok, why)."""
    dur = float(RECORD[str(sid)]["duration15"])
    want_ticks = [round(t, 6) for t in areatime.tick_instants(0.0, dur, period)]
    amount = expected_amount(sid)
    if not (fin58(e5) == [[58, PLAYER, 0]] and not words(e5) and not grounds(e5)
            and not impacts(e5)):
        return False, f"the E5 batch: {[(hex(op), v) for op, v in e5]}"
    hit_at = [off for off, w, _b in served if w]
    if hit_at != want_ticks:
        return False, f"ticks at {hit_at}, want {want_ticks}"
    for k, (off, w, batch) in enumerate([s for s in served if s[1]], start=1):
        per = amount * k if ramp else amount
        if sorted(t for t, _fr in w) != sorted(inside):
            return False, f"tick {k} struck {w}"
        if any(abs(fr + per / 9000.0) > 1e-6 for _t, fr in w):
            return False, f"tick {k} fractions {w}, want {-per / 9000.0:.6f}"
        if not clean(batch):
            return False, f"tick {k} not clean"
    if st.get("areas"):
        return False, "the area is still open after the last instant"
    return True, f"ticks {hit_at}, {amount:g} a tick" + (" x k" if ramp else "")


def section_records():
    print("\n1. the five rows: the record's numbers through the server's readers at rank 12")
    with _carried():
        got = {}
        for sid in FIVE:
            got[sid] = (authsrv.area_over_time(sid, RANK), authsrv.skill_damage(sid, RANK),
                        authsrv.skill_condition(sid, RANK), authsrv.area_tick_period(sid),
                        authsrv.area_tick_ramp(sid), authsrv.spell_area_visual(sid),
                        authsrv.skill_knocks_down(sid), authsrv.spell_damage_type(sid))
        interp = {sid: authsrv.skill_scale_value(sid, RANK) for sid in FIVE}
        bonus = {sid: authsrv.skill_scale_value(sid, RANK, "bonus_scale") for sid in (830, 910)}
        check(all(got[s][1] == (interp[s], "standalone") for s in FIVE)
              and [interp[s] for s in FIVE] == [34, 38, 42, 105, 17],
              "each row's damage is the record's scale at rank 12 through the client's own "
              "interpolator, standalone -- 1094 34, 2222 38, 830 42, 910 105, 1380 17 (the "
              "numbers are the interpolator's output, printed; the check compares "
              "skill_damage to skill_scale_value, never to a typed amount)",
              str({s: (got[s][1], interp[s]) for s in FIVE}))
        check(got[1094][0] == (156.0, 5.0) and got[2222][0] == (156.0, 5.0)
              and got[830][0] == (156.0, 5.0) and got[910][0] == (156.0, 3.0)
              and got[1380][0] == (240.0, 5.0)
              and all(got[s][5] is None and got[s][6] is False for s in FIVE),
              "each is an area over time off the record (the radius and the rank's duration: "
              "156 u x 5 s, 910 156 x 3, 1380 240 x 5), with no ground effect id and no "
              "knock-down", str({s: got[s][0] for s in FIVE}))
        check(got[830][2] == (480, float(bonus[830])) and bonus[830] == 3
              and got[910][2] == (2077, float(bonus[910])) and bonus[910] == 16
              and all(got[s][2] is None for s in (1094, 2222, 1380)),
              "830 inflicts Burning (480) for its bonus slot at rank 12 (3 s) and 910 Cracked "
              "Armor (2077) for its (16 s); the other three no condition",
              str({s: got[s][2] for s in FIVE}))
        check(got[910][3] == 3.0 and all(got[s][3] == 1.0 for s in (1094, 2222, 830, 1380))
              and got[1380][4] == "elapsed" and all(got[s][4] is None for s in (1094, 2222, 830, 910))
              and [got[s][7] for s in FIVE] == [5, 3, 8, 4, 5],
              "910's period is its 3 s (the rest Fire Storm's 1.0); 1380 alone ramps "
              "('elapsed'); the damage types fire / cold / holy / lightning / fire "
              "([damage_type.table] 5 / 3 / 8 / 4 / 5)",
              str({s: (got[s][3], got[s][4], got[s][7]) for s in FIVE}))
    rows = {s: agents.WORLD.get("skill_effect", str(s)) for s in FIVE}
    provs = {s: getattr(rows[s], "provenance", {}) for s in FIVE}
    check(all(p.get("source") == "client-table" and int(p.get("build", 0)) == RECORD_BUILD
              and p.get("extractor") == "toolkit/clientscan/skilldesc.py"
              and "weapons/PLAN.md 45" in p.get("verified", "") for p in provs.values())
          and not any(r.get("tier") for r in rows.values())
          and not any(r.get("area_visual") for r in rows.values()),
          "the five are HAND rows in the repo (no tier), each client-table with the build "
          "(38797) and the extractor named (content.py enforces both), citing weapons 45; "
          "none names an area_visual", str({s: dict(p) for s, p in provs.items()}))
    # the leaf, pure
    check([areatime.tick_amount(17.0, k, "elapsed") for k in range(1, 6)] == [17.0, 34.0, 51.0, 68.0, 85.0]
          and [areatime.tick_amount(17.0, k) for k in range(1, 6)] == [17.0] * 5
          and areatime.tick_amount(17.0, 3, "nonsense") == 17.0
          and areatime.tick_amount(10.0, 2, "elapsed", period=3.0) == 60.0
          and areatime.TICK_RAMPS == ("elapsed",)
          and [round(t, 6) for t in areatime.tick_instants(0.0, 3.0, 3.0)] == [3.0]
          and [round(t, 6) for t in areatime.tick_instants(0.0, 3.0, 1.0)] == [1.0, 2.0, 3.0],
          "areatime: tick k of an 'elapsed' area deals k x the amount (x the period's "
          "seconds), any other ramp or none the flat amount; a 3 s area at a 3 s period "
          "ticks once at +3, at Fire Storm's 1 s three times")


def section_record_rows():
    print("\n1b. the rows this file carries for a bare machine, against the vault's own")
    try:
        vaultpath.require_dir("content", why="test_aotrows 1b")
    except (Exception, SystemExit) as e:                               # noqa: BLE001
        LEDGER.skip("section 1b", f"the vault's content directory is absent "
                    f"({type(e).__name__}) -- 1 check")
        return
    # the directory is here: a skills table that did not load is a FAILURE, not a skip
    skills = agents.WORLD.rows("skills")
    off, builds = {}, {}
    for k, row in RECORD.items():
        r = skills.get(k)
        if r is None:
            off[k] = "absent"
            continue
        builds[k] = int(getattr(r, "provenance", {}).get("build", 0))
        cols = [c for c, v in row.items() if r.get(c, "absent") != v]
        if cols:
            off[k] = cols
    check(not off and all(b in (38797, 38888, 38974) for b in builds.values()),
          "every carried row is the vault's own, column for column, "
          "on whichever build the vault holds (38797 / 38888 / 38974: identical for these "
          "ids, compared 2026-10-07) -- so the bare path is the vault's path",
          str((off, builds)))


def section_player_casts():
    print("\n2. the player's cast of each through the real press and E5: three hostiles "
          "inside, one outside, served a second at a time")
    with _carried(), _Patched() as P:
        results = {}
        for sid in (1094, 2222, 830):
            P.conds.clear()
            st, e5, send, sent = player_cast(sid)
            area = (st.get("areas") or [None])[0]
            served = serve(st, sent, send, 1.0, 6)
            results[sid] = (schedule_ok(sid, st, e5, served, 1.0), area, list(P.conds), served)
        for sid in (1094, 2222, 830):
            (ok, why), area, conds, served = results[sid]
            check(ok and area is not None and area["point"] == (600.0, 0.0)
                  and area["amount"] == expected_amount(sid) and area["rank"] == RANK
                  and area["n"] == 5 and area["visual"] is None,
                  f"{sid}: the E5 opens the area at the target's position (600, 0) with no "
                  f"word and no ground effect; ticks at +1 .. +5 strike the three inside and "
                  f"never the one {RECORD[str(sid)]['aoe_range'] + 44:.0f} u off, clean, each "
                  f"-amount/9000 with the amount the interpolator's at rank 12; nothing at "
                  f"+6 and the area closed", why)
        # 830: Burning on EACH struck foe at EVERY tick
        burns = [(t, c, s) for t, c, s in results[830][2] if c == 480]
        per_tick = _per_tick_conditions(results[830][3], burns)
        check(_burning_every_tick(per_tick, 3.0),
              "830: Burning (480) for 3 s on each of the three struck foes at EVERY tick -- "
              "15 applies over five ticks, none on the one outside (Eruption's shape)",
              str(per_tick))
        # CROSS-LANE PIN: 830's channel. desk-chan55 moves armour-ignoring spell damage
        # (Holy damage) to property 55 this pass; today the player's tick goes out on 16.
        # The orchestrator re-points THIS check at merge (55 with a negative fraction).
        props = sorted({v[0] for _o, _w, b in results[830][3] for v in words(b)})
        check(props == [16],
              "830's tick words ride property 16 today (CROSS-LANE: desk-chan55 re-points "
              "this one check to 55 at merge; every other check reads any damage channel)",
              str(props))
        # 910: ONE strike at +3.0, then Cracked Armor once per struck foe
        P.conds.clear()
        st, e5, send, sent = player_cast(910)
        area910 = (st.get("areas") or [None])[0]
        served = serve(st, sent, send, 1.0, 4)
        ok910, why910 = schedule_ok(910, st, e5, served, 3.0)
        cracked = sorted((t, s) for t, c, s in P.conds if c == 2077)
        check(ok910 and area910 is not None and area910["n"] == 1 and area910["period"] == 3.0
              and [o for o, w, _b in served if w] == [3.0]
              and cracked == [(FOE, 16.0), (11, 16.0), (13, 16.0)]
              and all(s[1] == [] for s in served if s[0] != 3.0),
              "910: the area opens with ONE tick due; nothing at +1 and +2, the three inside "
              "struck once at +3.0 for 105 each, then Cracked Armor (2077) 16 s on each, "
              "once; nothing at +4 and the area closed", f"{why910} {cracked}")
        # 1380: tick k deals k x 17 (the interpolator's 17), radius 240
        st, e5, send, sent = player_cast(1380)
        served = serve(st, sent, send, 1.0, 6)
        ok1380, why1380 = schedule_ok(1380, st, e5, served, 1.0, ramp=True)
        amts = [round(-fr * 9000.0, 3) for _o, w, _b in served for t, fr in w if t == FOE]
        check(ok1380 and amts == [expected_amount(1380) * k for k in range(1, 6)],
              "1380: five ticks inside 240 u, tick k deals k x the scale -- 17, 34, 51, 68, 85 "
              "on the target (the interpolator's 17 x k), the hostile 284 u off never",
              f"{why1380} {amts}")
    return results


def _per_tick_conditions(served, applies):
    """[(k, sorted takers struck, sorted (taker, seconds) conditions)] -- the condition
    applies are recorded in order and split by each tick's word count (one apply per
    struck living foe, behind the words: _area_strike's order)."""
    out, i = [], 0
    for off, w, _b in served:
        if not w:
            continue
        n = len(w)
        out.append((off, sorted(t for t, _fr in w), sorted((t, s) for t, _c, s in applies[i:i + n])))
        i += n
    return out


def _burning_every_tick(per_tick, seconds):
    return (len(per_tick) == 5
            and all(takers == [FOE, 11, 13] and conds == [(FOE, seconds), (11, seconds), (13, seconds)]
                    for _o, takers, conds in per_tick))


def section_known_bad():
    print("\n3. the known-bad arms: each mutation reddens the predicate it should")
    with _carried(), _Patched() as P:
        # (a) the row deleted: 1094 is inert again -- no area, no word, nothing hurt
        with _row(1094, None):
            st, e5, send, sent = player_cast(1094)
            served = serve(st, sent, send, 1.0, 6)
            bad, why = schedule_ok(1094, st, e5, served, 1.0)
        check(not bad and not st.get("areas") and not any(w for _o, w, _b in served)
              and all(a["health"] == 9000.0 for a in st["agents"].values()),
              "KNOWN-BAD ARM, the row deleted: 1094 opens nothing and words nobody (the "
              "pre-row shape) -- and the predicate refuses it", why)
        # (b) 910 without its tick_period: Fire Storm's 1 s -- three strikes
        r910 = dict(agents.WORLD.get("skill_effect", "910"))
        r910.pop("tick_period", None)
        with _row(910, r910):
            P.conds.clear()
            st, e5, send, sent = player_cast(910)
            served = serve(st, sent, send, 1.0, 4)
            bad, why = schedule_ok(910, st, e5, served, 3.0)
            three = [o for o, w, _b in served if w]
            n_cracked = sum(1 for _t, c, _s in P.conds if c == 2077)
        check(not bad and three == [1.0, 2.0, 3.0] and n_cracked == 9,
              "KNOWN-BAD ARM, 910 without tick_period: three strikes at +1 / +2 / +3 and "
              "Cracked Armor nine times -- the predicate (one strike at +3) refuses it",
              f"{why} {three} {n_cracked}")
        # (c) 1380 without its tick_ramp: a flat 17 a tick
        r1380 = dict(agents.WORLD.get("skill_effect", "1380"))
        r1380.pop("tick_ramp", None)
        with _row(1380, r1380):
            st, e5, send, sent = player_cast(1380)
            served = serve(st, sent, send, 1.0, 6)
            bad, why = schedule_ok(1380, st, e5, served, 1.0, ramp=True)
            flat = [round(-fr * 9000.0, 3) for _o, w, _b in served for t, fr in w if t == FOE]
        check(not bad and flat == [expected_amount(1380)] * 5,
              "KNOWN-BAD ARM, 1380 without tick_ramp: 17 at every tick -- the predicate "
              "(k x 17) refuses it", f"{why} {flat}")
        # (d) 830's Burning once instead of every tick
        P.conds.clear()

        def once(st, k):
            if k == 1:
                for area in st.get("areas") or ():
                    area["condition"] = None
        st, e5, send, sent = player_cast(830)
        served = serve(st, sent, send, 1.0, 6, mutate=once)
        burns = [(t, c, s) for t, c, s in P.conds if c == 480]
        per_tick = _per_tick_conditions(served, burns)
        check(not _burning_every_tick(per_tick, 3.0) and len(burns) == 3,
              "KNOWN-BAD ARM, 830's Burning on the first tick only: three applies, not "
              "fifteen -- the per-tick predicate refuses it", str(per_tick))


def section_hostile():
    print("\n4. a hostile's Breath of Fire through the real land_skill onto the player and "
          "a hero: the tape's tick shape")
    with _carried(), _Patched():
        st = _body_world((900.0, 0.0), skills=[[1094, 0.0, 20.0]], skill_ready=[0.0],
                         casting=0, cast_target=PLAYER)
        st["agents"][300] = dict(st["agents"][HERO], pos=(0.0, 400.0))   # outside 156 u
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        health, monk = st["player_health"], st["agents"][HERO]["health"]
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        area = (st.get("areas") or [None])[0]
        rank = authsrv.agent_skill_rank(st["agents"][FOE], 1094)
        amount = float(authsrv.skill_scale_value(1094, rank))
        check(sent and sent[0] == (0x009F, [58, FOE, 0]) and not grounds(sent) and not words(sent)
              and area is not None and area["caster"] == FOE and area["hostile"] is True
              and area["point"] == (0.0, 0.0) and area["n"] == 5
              and rank == authsrv.ENEMY_SKILL_RANK and area["amount"] == amount
              and st["player_health"] == health and st["agents"][HERO]["health"] == monk,
              "a hostile's 1094 completes: [58, it, 0], NO ground effect (none known), no "
              "word; the area at the player's position, 5 ticks, at the body's rank "
              "(ENEMY_SKILL_RANK) through the interpolator", str([(hex(op), v) for op, v in sent]))
        ar = authsrv.spell_armour_for(1094)
        want = authsrv._whole_points(amount * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        sent.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            _advance(st, send, 1.0)
        i10 = next((i for i, (op, v) in enumerate(sent)
                    if op == 0x009F and v[:3] == [10, PLAYER, 1094]), None)
        cf = [v for op, v in sent if op == 0x00CF]
        check(i10 is not None and sent[i10 + 1][0] == 0x00A3
              and sent[i10 + 1][1][:3] == [16, PLAYER, FOE]
              and [v[1] for v in words(sent)] == [PLAYER, HERO]
              and clean(sent) and not grounds(sent)
              and st["player_health"] == health - want
              and st["agents"][HERO]["health"] < monk and st["agents"][300]["health"] == 9000.0
              and len(cf) == 1 and cf[0][0] == PLAYER and ops(sent).index(0x00CF) < i10,
              "k = 1: the adrenaline gain 0x00CF [me, n], then [10, me, 1094], then the word "
              "on the player (the interpolator's 34 against the pieces' spell armour at the "
              "caster's strike level) -- the tape's observer shape (weapons 41, 12/12) -- "
              "then the hero's word; the hero 400 u off untouched; clean",
              str([(hex(op), v) for op, v in sent]))
        hp1 = st["player_health"]
        for _ in range(4):
            with contextlib.redirect_stdout(io.StringIO()):
                _advance(st, send, 1.0)
        check(st["player_health"] == hp1 - 4 * want and not st.get("areas"),
              "and k = 2..5 the same on the player, then the area closes", str(st["player_health"]))


def section_revert():
    print("\n5. --no-area-tick-ramp: parsed, flipped by main() for real, and what it reverts")
    import serverargs                                                  # noqa: PLC0415
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    check(getattr(ap.parse_args([]), "no_area_tick_ramp", None) is False
          and getattr(ap.parse_known_args(["--no-area-tick-ramp"])[0], "no_area_tick_ramp",
                      None) is True,
          "--no-area-tick-ramp parses, default off")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()

    def flip(block_edit=None):
        """main()'s own `if a.no_area_tick_ramp:` block, lifted out of the source by the
        AST and RUN in authsrv's namespace (test_agtrack_guard 16l's pattern): without
        its `global` the assignment binds a local and the flag parses and does nothing."""
        tree = ast.parse(src)
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        node = next((n for n in ast.walk(main) if isinstance(n, ast.If)
                     and ast.unparse(n.test) == "a.no_area_tick_ramp"), None)
        if node is None:
            return "no block"
        body = node.body if block_edit is None else block_edit(node.body)
        fn = ast.FunctionDef(name="_aot_flip", args=ast.arguments(
            posonlyargs=[], args=[ast.arg(arg="a")], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=body, decorator_list=[], type_params=[])
        mod = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
        saved = authsrv.AREA_TICK_RAMP
        try:
            exec(compile(mod, "<main:no_area_tick_ramp>", "exec"), authsrv.__dict__)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.__dict__["_aot_flip"](argparse.Namespace(no_area_tick_ramp=True))
            return authsrv.AREA_TICK_RAMP
        finally:
            authsrv.AREA_TICK_RAMP = saved
            authsrv.__dict__.pop("_aot_flip", None)
    real = flip()
    no_global = flip(lambda body: [s for s in body if not isinstance(s, ast.Global)])
    check(real is False and no_global is True and authsrv.AREA_TICK_RAMP is True,
          "main()'s --no-area-tick-ramp block, EXECUTED, sets the module's AREA_TICK_RAMP to "
          "False; KNOWN-BAD ARM: the same block without its `global` leaves it True (a flag "
          "that parses and never takes effect); the default is on",
          f"real {real}, without the global {no_global}")
    with _carried(), _Patched():
        authsrv.AREA_TICK_RAMP = False
        st, e5, send, sent = player_cast(1380)
        served = serve(st, sent, send, 1.0, 6)
        flat = [round(-fr * 9000.0, 3) for _o, w, _b in served for t, fr in w if t == FOE]
        ramp_off = (authsrv.area_tick_ramp(1380), (st.get("areas") or [None]))
        authsrv.AREA_TICK_RAMP = True
        st2, e5b, send2, sent2 = player_cast(1380)
        served2 = serve(st2, sent2, send2, 1.0, 6)
        on = [round(-fr * 9000.0, 3) for _o, w, _b in served2 for t, fr in w if t == FOE]
        amt = expected_amount(1380)
    check(flat == [amt] * 5 and ramp_off[0] is None
          and on == [amt * k for k in range(1, 6)]
          and sum(flat) * 3 == sum(on),
          "--no-area-tick-ramp: 1380 deals the flat 17 at every tick (85 over the area) where "
          "the ramp deals 17 x k (255) -- the area, the radius and the instants unchanged",
          f"off {flat}, on {on}")
    check('"--no-area-tick-ramp"' in open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
          and "\nAREA_TICK_RAMP = True\n" in src
          and src.count("tick_amount(area[\"amount\"], k, area.get(\"ramp\"),") == 1
          and '"ramp": area_tick_ramp(skill_id),' in src,
          "the source: AREA_TICK_RAMP at column 0, open_area records the row's ramp, and "
          "_area_strike computes each tick's amount through areatime.tick_amount once, for "
          "the player's and a body's words alike")


def section_tape():
    print("\n6. the caster's death on the Zaishen tapes, and the server's locked behaviour")
    Z1, Z2 = "20260928T103123", "20260929T100038"
    try:
        vaultpath.require_dir("captures", "live", why="test_aotrows 6")
    except (Exception, SystemExit) as e:                               # noqa: BLE001
        LEDGER.skip("section 6", f"the live corpus is absent ({type(e).__name__}) -- 3 checks "
                    f"(the twenty Zaishen Fire Storms, cast #17's caster death, the server "
                    f"against it)")
        return
    # the directory is here: a reader failure is a FAILURE (it raises through)
    import aotjoin as aj                                               # noqa: PLC0415
    with contextlib.redirect_stdout(io.StringIO()):
        c = aj.census(stamps=(Z1, Z2))
        sc = aj.score(c)
    rows = c["casts"]
    ks = sorted({k for r in rows for k in r["tick_ks"]})
    per_stamp = {s: sum(1 for r in rows if r["capture"] == s) for s in (Z1, Z2)}
    check(per_stamp == {Z1: 8, Z2: 12} and ks == list(range(1, 11))
          and sc["p4"] and sc["p5r"] and sc["stray_r"] == []
          and sc["late_ticks"] == [(Z2, "51090", 390.03, 2.068, 2)]
          and sc["tick_instants"] == 97,
          "the twenty Zaishen Fire Storms (8 + 12): ticks only at k = 1..10 -- 97 tick "
          "instants within the reader's 0.05 s gate, and ONE late tick (51090 390.030 k = 2 "
          "at +2.068, P5r: inside the registered 0.100) -- the 350 at +0 / +3 / +6 on every "
          "cast; the server's schedule for 197 is k = 1..10 from its row",
          str((per_stamp, ks, sc["late_ticks"], sc["tick_instants"], sc["stray_r"])))
    r17 = [r for r in rows if r["capture"] == Z2 and r["port"] == "51199"
           and abs(r["announce_t"] - 562.188) < 0.01]
    tick10 = [x for x in (r17[0]["ticks"] if r17 else []) if x["k"] == 10]
    deaths = sorted((r["port"], round(r["announce_t"], 3), r["caster_deaths"], r["tick_ks"])
                    for r in rows if any(d for _t, d in r["caster_deaths"]))
    check(len(r17) == 1 and r17[0]["caster"] == 10 and r17[0]["caster_deaths"] == [(8.487, True)]
          and r17[0]["tick_ks"] == [1, 2, 3, 10] and len(tick10) == 1
          and tick10[0]["clean"] and abs(tick10[0]["off"] - 9.989) < 0.0015
          and sorted(w[0] for w in tick10[0]["fs_words"]) == [4, 6]
          and deaths == [("51199", 562.188, [(8.487, True)], [1, 2, 3, 10]),
                         ("58544", 597.109, [(8.05, True)], [1, 2, 3, 4])],
          "cast #17 (20260929T100038 :51199, announced 562.188 by agent 10): the caster DEAD "
          "at completion + 8.487 and a CLEAN tick at + 9.989 (k = 10) on foes 4 and 6 -- "
          "the area OUTLIVES its caster, OBSERVED n = 1; the only other caster death on these "
          "tapes (:58544, +8.05) ticked nobody after k = 4, inconclusive",
          str((deaths, tick10)))
    # The server against it: a hostile's Fire Storm, the caster killed between k = 8 and
    # k = 9 (the tape's +8.487), served to the end. The agreement: the tape ticks after
    # the death and every tape k after it is a k the server words after it. KNOWN-BAD
    # ARM: a server that ends the area with its caster (the area dropped at the death).
    def after_death(end_with_caster):
        with _carried(), _Patched():
            st = _body_world((900.0, 0.0), skills=[[197, 0.0, 20.0]], skill_ready=[0.0],
                             casting=0, cast_target=PLAYER)
            snd = lambda op, vals, label="", quiet=False: None   # noqa: E731
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.land_skill(snd, st, FOE, st["agents"][FOE], 1)
            out = []
            for k in range(1, 11):
                h0 = st["player_health"]
                with contextlib.redirect_stdout(io.StringIO()):
                    _advance(st, snd, 1.0)
                if st["player_health"] < h0 and st["agents"][FOE].get("dead"):
                    out.append(k)
                if k == 8:
                    st["agents"][FOE]["dead"], st["agents"][FOE]["died_at"] = True, time.time()
                    if end_with_caster:
                        st["areas"] = []
            return out
    tape_after = [k for k in (r17[0]["tick_ks"] if r17 else []) if k > 8]

    def agree(server_after):
        return bool(tape_after) and set(tape_after) <= set(server_after)
    ours, bad = after_death(False), after_death(True)
    check(agree(ours) and ours == [9, 10] and not agree(bad) and bad == [],
          "the server's locked behaviour agrees: its hostile Fire Storm, the caster killed "
          "after k = 8, still words the player at k = 9 and 10 (the tape's k = 10 after the "
          "death among them); KNOWN-BAD ARM: an area that ends with its caster words "
          "nobody after the death and the agreement refuses it",
          f"tape after the death {tape_after}, ours {ours}, the known-bad {bad}")


def main():
    section_records()
    section_record_rows()
    section_player_casts()
    section_known_bad()
    section_hostile()
    section_revert()
    section_tape()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
