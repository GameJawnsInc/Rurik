"""test_chan55 -- an armour-ignoring, non-attack skill's damage word rides property 55
(CHAN55, studies/skills/FINDINGS.md section 68, SKILLS-CH1; CASTAI-ZF31), 2026-10-07.

    python toolkit/authsrv/test_chan55.py

WHAT RETAIL SENDS (OBSERVED). The wire names the observer's damage ahead of its word
with 0x009F [10, observer, skill] (spellhitjoin.named_words). Over the whole live corpus
(127 connections; 20260928T103123 :65009, gapped by its own manifest, set aside by name)
the named skills split with NO overlap: property 55 with a NEGATIVE fraction for exactly
{102: 1, 133: 1, 143: 3, 251: 6, 272: 64, 302: 11, 2809: 8} -- 94 words -- and property
16 / 17 for 20 others. The client's own description templates type the 55 side SHADOW
(102, 133), a life-steal slot (143), HOLY (251, 272, 302) and untyped DAMAGE (2809, the
PvP split of 219); the 16 / 17 side FIRE, LIGHTNING, and ATTACK skills (type 14, 399's
untyped DAMAGE among them). So the rule is "armour-ignoring damage on a non-attack", and a
rule keyed on "holy" fails on 4 of the 7. Section 8b re-derives every census number from
the bytes and 8c the templates; this server sent every skill's word on 16 until today
(Holy Strike 312, Banish 252).

Section 1 is the helper on the rows; 2 a hostile's Holy Strike and Banish onto the player
through the real land_skill (the gain, [10, player, skill], the 55 word, no 16); 3 the
known-bad arm (--no-armour-ignoring-on-55 reproduces 16); 4 the controls that must NOT
move (Flare, Lightning Orb, an attack's exact word, a "+ Damage" non-attack); 5 a lethal
Holy Strike (one word, one death, one kill); 6 the bodies (a party Banish onto a hostile
through hurt_agent_row, its kill paying; a hostile's onto a party body), the player's own
Holy Strike and Banish through handle_skill_press + cast_tick (55, the first-word [42]
rule intact), and an area's tick on the same rule; 7 the flag, main()'s wiring and the
call sites in the source; 8 the live corpus. Sections 9-11 are LIFE STEAL (SKILLS-CH3):
9 the server's three doors, 10 the flag and the rows, 11 stealjoin over the corpus.

THE BARE MACHINE. Sections 1-7 run on RECORD below plus the tracked skills rows (they
REPLACE the vault's skills table for those sections, so a vault run takes the bare path);
section 8a holds RECORD to the vault's own rows column for column and declares a skip on
a machine with no vault/content DIRECTORY; section 8b reads the live corpus and declares a
skip with no vault/captures/live directory; section 8c re-reads the client's templates
and declares a skip with no vault/client directory. A directory that exists and fails to
load is a FAIL, never a skip.
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

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import vaultpath                                               # noqa: E402

HAVE_VAULT_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_LIVE_CORPUS = os.path.isdir(vaultpath.vault_path("captures", "live"))
HAVE_CLIENT = os.path.isdir(vaultpath.vault_path("client"))
# THE FLOOR IS PER MACHINE, decided on DIRECTORIES and never on what loaded. Each number is
# a green run's count, MEASURED 2026-10-07 in the desk-chan55 tree: 39 with RURIK_VAULT at an
# empty directory and at a nonexistent path alike (sections 1-7, 9, 10; 8a-8c and 11
# declared skips); 49 on the owner's vault -- 8a's 1 (vault/content), 8b's 3 + 11's 4
# (vault/captures/live), 8c's 2 (vault/client), each section's own count on that run.
# (Commit 1 of the lane, the channel alone: 25 bare, 30 vault; commit 2: 36 / 44; the
# review fixes -- 9c2, 9i, 10d bare; 11d, 8c2 on the vault -- 39 / 49.)
FLOOR_BARE = 39
FLOOR_8A, FLOOR_8B, FLOOR_8C = 1, 7, 2
LEDGER = checks.Ledger("armour-ignoring damage rides property 55", floor=(
    FLOOR_BARE + FLOOR_8A * HAVE_VAULT_CONTENT + FLOOR_8B * HAVE_LIVE_CORPUS
    + FLOOR_8C * HAVE_CLIENT))
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
HOSTILE, ALLY = agents.ALLEGIANCE_HOSTILE, agents.ALLEGIANCE_PLAYER
FLOAT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
GAIN = authsrv.AGENT_ADRENALINE_GAIN
STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
KILL_REWARD = authsrv.GAME_SMSG_AGENT_KILL_REWARD
P55, P16, P17 = agents.GV_ARMOR_IGNORING, agents.PROP_DAMAGE, agents.GV_CRITICAL
P10, P42, P20 = agents.GV_SKILL_DAMAGE, agents.PROP_HEALTH_MAX, agents.GV_EFFECT_ON_TARGET
HOLY_STRIKE, BANISH, FLARE, ORB, DSHOT, STEAL = 312, 252, 194, 229, 399, 153
HATCHER, MONK, FOE = 10, 200, 11


def _record(activation, aftercast, recharge, energy, attribute, profession, type_code,
            target, skill_arguments, scale, duration=(0, 0), bonus_scale=(0, 0),
            adrenaline=(0, 0), weapon_req=0, aoe_range=0.0, projectile=2077,
            impact_visual=2077, touch_range=False):
    return {"activation": activation, "aftercast": aftercast, "recharge": recharge,
            "energy": energy, "adrenaline": adrenaline[0],
            "adrenaline_units": adrenaline[1], "attribute": attribute,
            "profession": profession, "type_code": type_code, "target": target,
            "combo": 0, "combo_req": 0, "weapon_req": weapon_req, "aoe_range": aoe_range,
            "skill_arguments": skill_arguments, "duration0": duration[0],
            "duration15": duration[1], "scale0": scale[0], "scale15": scale[1],
            "bonus_scale0": bonus_scale[0], "bonus_scale15": bonus_scale[1],
            "projectile": projectile, "impact_visual": impact_visual,
            "touch_range": touch_range, "half_range": False}


# skilltable.py's records as vault/content/skills.toml holds them, build 38974 (measured
# numbers -- CLAUDE.md's gate), copied 2026-10-07; 312, 194 and the default bar 316-323
# equal test_skilldamage's RECORD. Section 8a holds every one to the vault's row.
RECORD_BUILD = 38974
RECORD = {
    "153": _record(1.0, 0.75, 8, 10, 4, 4, 5, 5, 2, (18, 60)),    # Vampiric Gaze, the steal
    "194": _record(1.0, 0.75, 0, 5, 10, 6, 5, 5, 2, (20, 65), bonus_scale=(1800, 1800),
                   aoe_range=156.0, projectile=343, impact_visual=344),   # Flare, fire
    "229": _record(2.0, 0.75, 5, 10, 8, 6, 5, 5, 2, (10, 100), bonus_scale=(1800, 1800),
                   projectile=403, impact_visual=404),            # Lightning Orb, lightning
    "252": _record(1.0, 0.75, 10, 5, 14, 3, 5, 5, 2, (20, 65)),   # Banish, holy
    "312": _record(0.75, 0.75, 8, 5, 14, 3, 10, 5, 6, (10, 55), bonus_scale=(10, 55),
                   touch_range=True),                             # Holy Strike, holy touch
    "316": _record(0.0, 0.0, 10, 5, 21, 1, 15, 0, 7, (10, 60), duration=(10, 20),
                   bonus_scale=(1, 6), aoe_range=1000.0),         # the default bar
    "317": _record(0.0, 0.0, 0, 0, 17, 1, 3, 0, 1, (33, 33), duration=(5, 20),
                   adrenaline=(4, 80)),                           # ARMS the default bar
    "318": _record(0.0, 0.0, 0, 0, 17, 1, 16, 0, 7, (90, 300), duration=(20, 20),
                   bonus_scale=(1, 10), adrenaline=(5, 120), aoe_range=20.0),
    "319": _record(0.0, 0.0, 0, 0, 17, 1, 3, 0, 1, (25, 25), duration=(8, 20),
                   adrenaline=(4, 80)),
    "320": _record(0.0, 0.0, 10, 5, 20, 1, 14, 5, 4, (0, 0), bonus_scale=(3, 15),
                   weapon_req=128),
    "321": _record(0.0, 0.0, 8, 5, 51, 1, 14, 5, 0, (0, 0), weapon_req=185),
    "322": _record(0.0, 0.0, 3, 5, 17, 1, 14, 5, 2, (10, 40), weapon_req=185),
    "323": _record(0.0, 0.0, 7, 5, 21, 1, 14, 5, 2, (10, 40), duration=(2, 2),
                   weapon_req=185),
    "399": _record(0.5, 1.5, 10, 5, 23, 2, 14, 5, 2, (1, 16), bonus_scale=(20, 20),
                   weapon_req=2, projectile=728, impact_visual=729),   # Distracting Shot, an ATTACK
}


@contextlib.contextmanager
def _tables(**replace):
    tables = agents.WORLD.tables
    kept = {k: tables[k] for k in replace if k in tables}
    tables.update(replace)
    try:
        yield
    finally:
        for k in replace:
            if k in kept:
                tables[k] = kept[k]
            else:
                del tables[k]


_TRACKED = []


def carried():
    """The skills table as a BARE machine holds it (the tracked rows alone) plus RECORD's."""
    if not _TRACKED:
        _TRACKED.append(agents.content.load(vault_dir="", extra_dirs=[]).rows("skills"))
    table = {k: dict(v) for k, v in RECORD.items()}
    table.update(_TRACKED[0])
    return _tables(skills=table)


_MISSING = object()


@contextlib.contextmanager
def flags(**kw):
    """authsrv's module flags set for the block and put back -- a name the server does
    not have (a tree before the change) is created and removed, so the check behind it
    reports red instead of the file dying here."""
    saved = {k: getattr(authsrv, k, _MISSING) for k in kw}
    try:
        for k, v in kw.items():
            setattr(authsrv, k, v)
        yield
    finally:
        for k, v in saved.items():
            if v is _MISSING:
                authsrv.__dict__.pop(k, None)
            else:
                setattr(authsrv, k, v)


def visual_row(sid):
    """The loaded skill_visual row as a dict, or {} when there is none (so a missing row
    reds the check that reads it by name rather than raising out of its section)."""
    try:
        return dict(agents.WORLD.get("skill_visual", str(sid)))
    except Exception:                                          # noqa: BLE001
        return {}


def prop_of(sid):
    """spell_damage_prop, or None on a server without it (a tree before CHAN55)."""
    fn = getattr(authsrv, "spell_damage_prop", None)
    return None if fn is None else fn(sid)


@contextlib.contextmanager
def effect_rows(**rows):
    """skill_effect rows added or replaced for the block (a synthetic control)."""
    tab = agents.WORLD.tables["skill_effect"]
    kept = {k: tab[k] for k in rows if k in tab}
    tab.update(rows)
    try:
        yield
    finally:
        for k in rows:
            if k in kept:
                tab[k] = kept[k]
            else:
                del tab[k]


def f32(d):
    return struct.unpack("<f", struct.pack("<I", int(d) & 0xFFFFFFFF))[0]


def f32r(x):
    """x as the wire carries it (an f32), back as a float."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def words(sent, *props):
    """[(prop, target, source, fraction)] of every 0x00A3 on `props` (negative 55 only:
    a positive 55 is a heal)."""
    out = []
    for op, v in sent:
        if op != FLOAT_T or v[0] not in props:
            continue
        fr = f32(v[3])
        if v[0] == P55 and not (v[3] & 0x80000000):
            continue
        out.append((v[0], v[1], v[2], fr))
    return out


def heals(sent):
    return [(v[1], v[2], f32(v[3])) for op, v in sent
            if op == FLOAT_T and v[0] == P55 and not (v[3] & 0x80000000)]


def recorder():
    sent = []
    return sent, (lambda op, vals, label="", quiet=False: sent.append((op, list(vals))))


def body(name, allegiance, pos, health=100.0, max_health=100.0, **extra):
    row = {"name": name, "dead": False, "died_at": 0.0, "last_hit": 0.0,
           "max_health": max_health, "health": health, "pos": pos, "plane": 0,
           "allegiance": allegiance, "attack_speed": 1.75, "effects": 0,
           "attacks_back": False, "skills": (), "skill_ready": [],
           "npc": {"profession": 3, "level": 5}}
    row.update(extra)
    return row


def body_cast(sid, caster_allegiance=HOSTILE, cast_target=None, player_health=None,
              foe_health=100.0, monk_health=100.0, hatcher_health=100.0, deep_wound=None):
    """A body's skill `sid` landing through the REAL land_skill: the Hatcher (hostile, 10)
    or the Monk (party, 200) casting at `cast_target` (None: the player). `deep_wound`
    is state's {agent: ...} set (heal_agent reads membership). Returns (state, sent)."""
    st = {"agents": {}, "pos": (0.0, 0.0)}
    if player_health is not None:
        st["player_health"] = player_health
    if deep_wound is not None:
        st["deep_wound"] = dict(deep_wound)
    caster_id = HATCHER if caster_allegiance == HOSTILE else MONK
    st["agents"][HATCHER] = body("hatcher", HOSTILE, (60.0, 0.0), health=hatcher_health)
    st["agents"][MONK] = body("monk", ALLY, (0.0, 60.0), health=monk_health, party_slot=0)
    st["agents"][FOE] = body("foe", HOSTILE, (60.0, 60.0), health=foe_health)
    caster = st["agents"][caster_id]
    caster.update(casting=0, skills=((sid, 1.0, 0.0),), skill_ready=[0.0],
                  cast_target=cast_target)
    sent, send = recorder()
    with flags(ENEMY_SKILL_RANK=0):
        authsrv.land_skill(send, st, caster_id, caster, 0)
        for shot in st.get("body_projectiles") or ():     # a projectile spell's word rides
            shot["arrives_at"] -= 30.0                     # the flight (studies/weapons 37)
        authsrv.projectile_tick(send, st, 0)
    return st, sent


def section_helper():
    print("\n1. spell_damage_prop on the rows (bare: RECORD + the tracked rows)")
    got = {s: prop_of(s) for s in (HOLY_STRIKE, BANISH, FLARE, ORB, DSHOT)}
    check(got == {HOLY_STRIKE: P55, BANISH: P55, FLARE: P16, ORB: P16, DSHOT: P16},
          "1a. Holy Strike 312 (holy, a touch skill) and Banish 252 (holy, a spell) ride 55; "
          "Flare 194 (fire) and Lightning Orb 229 (lightning) ride 16; Distracting Shot 399 -- "
          "\"Armor-ignoring damage\" on an ATTACK -- rides 16 (retail: 1 of 1 at the observer)",
          got)
    with flags(ARMOUR_IGNORING_ON_55=False):
        off = {s: prop_of(s) for s in (HOLY_STRIKE, BANISH)}
    check(off == {HOLY_STRIKE: P16, BANISH: P16},
          "1b. --no-armour-ignoring-on-55: both holy skills back on 16 (the known-bad arm)", off)
    # KEYED ON THE ROW, not on the id and not on a word in a label: the same id under a
    # fire row is 16, an untyped "Armor-ignoring damage" non-attack (2809's shape) is 55,
    # "+ Damage" on a non-attack is 16 (additive, never standalone), and a skill with no
    # skills row cannot say "not an attack" and keeps 16.
    synth_skill = dict(RECORD["252"])
    with effect_rows(**{"252": {"scale_means": "Fire damage"},
                        "90001": {"scale_means": "Armor-ignoring damage"},
                        "90002": {"scale_means": "+ Damage"},
                        "90003": {"scale_means": "Holy damage"}}), \
            _tables(skills=dict(agents.WORLD.tables["skills"], **{
                "90001": synth_skill, "90002": synth_skill})):
        synth = {s: prop_of(s) for s in (BANISH, 90001, 90002, 90003)}
    check(synth == {BANISH: P16, 90001: P55, 90002: P16, 90003: P16},
          "1c. keyed on the LOADED ROW: Banish's id under a fire row rides 16; an untyped "
          "\"Armor-ignoring damage\" non-attack rides 55; a \"+ Damage\" non-attack rides 16; a "
          "holy row whose skill has NO skills row keeps 16 (the type is unknown)", synth)
    check(prop_of(None) == P16 and prop_of(0) == P16,
          "1d. no skill (a plain swing's caller) keeps 16")


def section_hostile_at_player():
    print("\n2. a hostile's Holy Strike and Banish onto the PLAYER through land_skill")
    for sid, amount in ((HOLY_STRIKE, 10.0), (BANISH, 20.0)):
        st, sent = body_cast(sid)
        pool = authsrv.player_max_health(st)
        w55, w16 = words(sent, P55), words(sent, P16, P17)
        ops = [(op, v[0] if op in (INT, FLOAT_T) else None) for op, v in sent]
        i_gain = next((i for i, (op, _p) in enumerate(ops) if op == GAIN), None)
        i_10 = next((i for i, (op, v) in enumerate(sent) if op == INT and v[0] == P10
                     and v[1] == PLAYER and v[2] == sid), None)
        i_w = next((i for i, (op, v) in enumerate(sent) if op == FLOAT_T and v[0] == P55
                    and v[1] == PLAYER), None)
        want = f32r(-amount / pool)
        check(w55 == [(P55, PLAYER, HATCHER, want)] and w16 == []
              and None not in (i_gain, i_10, i_w) and i_gain < i_10 and i_w == i_10 + 1
              and abs(st["player_health"] - (pool - amount)) < 1e-6,
              f"2{'a' if sid == HOLY_STRIKE else 'b'}. skill {sid}: the gain, [10, player, {sid}], "
              f"then 0x00A3 [55, player, hatcher, -{amount:.0f}/{pool:.0f}] right behind it, and "
              f"NO 16 word; the pool takes {amount:.0f}",
              (w55, w16, i_gain, i_10, i_w, st["player_health"]))


def section_known_bad():
    print("\n3. the known-bad arm: --no-armour-ignoring-on-55")
    with flags(ARMOUR_IGNORING_ON_55=False):
        st, sent = body_cast(HOLY_STRIKE)
    pool = authsrv.player_max_health(st)
    check(words(sent, P16) == [(P16, PLAYER, HATCHER, f32r(-10.0 / pool))]
          and words(sent, P55) == [],
          "3a. under the flag the same Holy Strike reproduces the old word: [16, player, "
          "hatcher, -10/max] and no 55 (every session before 2026-10-07)",
          (words(sent, P16), words(sent, P55)))
    with flags(ARMOUR_IGNORING_ON_55=False):
        st, sent = body_cast(BANISH, caster_allegiance=ALLY, cast_target=FOE)
    check(words(sent, P16) == [(P16, FOE, MONK, f32r(-20.0 / 100.0))] and words(sent, P55) == [],
          "3b. and a party Banish onto a hostile through hurt_agent_row: [16, foe, monk, -0.2]",
          (words(sent, P16), words(sent, P55)))


def section_controls():
    print("\n4. the controls that must NOT move")
    for sid, name in ((FLARE, "Flare 194, fire"), (ORB, "Lightning Orb 229, lightning")):
        st, sent = body_cast(sid)
        w16, w55 = words(sent, P16, P17), words(sent, P55)
        check(len(w16) == 1 and w16[0][:3] == (P16, PLAYER, HATCHER) and w55 == [],
              f"4. {name}: its word stays [16, player, hatcher, ...] with no 55 -- an "
              f"armour-respecting label (retail: 4 of 4 / 21 of 21 named on 16)", (w16, w55))
    # an ATTACK's exact word (the block punishment's shape) and an attack named as the
    # spell: both 16. 399 is "Armor-ignoring damage" -- the rule's attack exclusion.
    st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0))}, "pos": (0.0, 0.0)}
    sent, send = recorder()
    authsrv.hit_enemy(send, st, FOE, 0, exact=8.0, swing=False, armed=True,
                      label="399-shaped", spell_skill=DSHOT)
    authsrv.hit_enemy(send, st, FOE, 0, exact=8.0, swing=False, armed=True,
                      label="no spell named")
    check(words(sent, P16) == [(P16, FOE, PLAYER, f32r(-0.08))] * 2 and words(sent, P55) == [],
          "4c. hit_enemy's exact word for a 399-shaped ATTACK (\"Armor-ignoring damage\", type "
          "14) and for an exact with no spell named (the hex end, the block punishment) "
          "stay on 16", words(sent, P16, P55))
    synth_skill = dict(RECORD["252"])
    with effect_rows(**{"90002": {"scale_means": "+ Damage"}}), \
            _tables(skills=dict(agents.WORLD.tables["skills"], **{"90002": synth_skill})):
        st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0))}, "pos": (0.0, 0.0)}
        sent, send = recorder()
        authsrv.hit_enemy(send, st, FOE, 0, exact=8.0, swing=False, armed=True,
                          label="+ Damage non-attack", spell_skill=90002)
    check(words(sent, P16) == [(P16, FOE, PLAYER, f32r(-0.08))] and words(sent, P55) == [],
          "4d. a \"+ Damage\" non-attack named as the spell stays on 16", words(sent, P16, P55))


def section_lethal():
    print("\n5. a LETHAL Holy Strike: one word, one death, one kill")
    calls = []
    real = authsrv.kill_player

    def counting(*a, **k):
        calls.append(a[3] if len(a) > 3 else k.get("why"))
        return real(*a, **k)
    authsrv.kill_player = counting
    try:
        st, sent = body_cast(HOLY_STRIKE, player_health=5.0)
    finally:
        authsrv.kill_player = real
    deaths = [v for op, v in sent if op == STATUS and v[0] == PLAYER
              and v[1] & agents.EFFECT_DEAD]
    w55 = words(sent, P55)
    pool = authsrv.player_max_health(st)
    check(len(w55) == 1 and w55[0][3] == f32r(-10.0 / pool) and words(sent, P16, P17) == []
          and len(calls) == 1 and len(deaths) == 1 and st["player_dead"]
          and st["player_health"] == 0.0,
          "5. Holy Strike's 10 into 5 left: ONE 55 word carrying the raw 10 (retail puts the "
          "raw overkill on the wire, _damage_fraction's census), ONE kill_player, ONE death "
          "status word, the player dead at 0 -- the same door the 16 word used",
          (w55, len(calls), deaths, st["player_dead"], st["player_health"]))


def player_cast(sid, st):
    """The player presses `sid` at FOE and the cast completes (handle_skill_press, every
    timer moved 30 s back, cast_tick). skill_cost is stubbed for the PRESS ONLY -- the
    channel, not the price -- and put back BEFORE cast_tick, so the gain's bar gate
    (bar_holds_adrenal, which reads skill_cost) sees the default bar's real adrenal costs
    there: a stub left in place through cast_tick read the bar DARK, and 9b's "no gain"
    could not fail (the review's CD-2; an injected gain stayed green)."""
    sent, send = recorder()
    st["cast_busy_until"] = 0.0
    saved_cost = authsrv.skill_cost
    authsrv.skill_cost = lambda _sid: (0, 0)
    try:
        authsrv.handle_skill_press([0, sid, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
    finally:
        authsrv.skill_cost = saved_cost
    sent.clear()
    for cast in st.get("pending_casts") or ():
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            if k in cast and cast[k] is not None:
                cast[k] -= 30.0
    authsrv.cast_tick(send, st, 1)
    for cast in list(st.get("pending_casts") or ()):
        st["pending_casts"].remove(cast)
    return sent


def section_bodies_and_own():
    print("\n6. the bodies, the player's own cast, an area's tick")
    st, sent = body_cast(BANISH, caster_allegiance=ALLY, cast_target=FOE, foe_health=0.5)
    ops = [op for op, _v in sent]
    check(words(sent, P55) == [(P55, FOE, MONK, f32r(-20.0 / 100.0))]
          and words(sent, P16, P17) == [] and st["agents"][FOE]["dead"] and KILL_REWARD in ops,
          "6a. a PARTY Banish onto a hostile through hurt_agent_row: [55, foe, monk, -0.2], no "
          "16, and its kill pays the reward (land_skill's allegiance rule, unchanged)",
          (words(sent, P55, P16), st["agents"][FOE]["dead"], [hex(o) for o in ops]))
    st, sent = body_cast(BANISH, cast_target=MONK)
    check(words(sent, P55) == [(P55, MONK, HATCHER, f32r(-20.0 / 100.0))]
          and words(sent, P16, P17) == [] and not any(op == INT and v[0] == P10 for op, v in sent),
          "6b. a hostile's Banish onto a PARTY body: [55, monk, hatcher, -0.2], no 16, and no "
          "[10] (the observer's naming is for the observer's own damage)",
          words(sent, P55, P16))
    # the player's own casts: Banish and Holy Strike at a hostile whose maximum the client
    # has not been told (the create marks it stale: max_declared_on_hit None)
    for sid, amount in ((BANISH, 20.0), (HOLY_STRIKE, 10.0)):
        st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0), health=480.0,
                                   max_health=480.0, max_declared_on_hit=None)},
              "pos": (0.0, 0.0)}
        sent = player_cast(sid, st)
        sent2 = player_cast(sid, st)
        i_w = next((i for i, (op, v) in enumerate(sent) if op == FLOAT_T and v[0] == P55), None)
        decl = i_w is not None and i_w > 0 and sent[i_w - 1] == (INT, [P42, FOE, 480])
        check(words(sent, P55) == [(P55, FOE, PLAYER, f32r(-amount / 480.0))]
              and words(sent, P16, P17) == [] and decl
              and words(sent2, P55) == [(P55, FOE, PLAYER, f32r(-amount / 480.0))]
              and not any(op == INT and v[0] == P42 for op, v in sent2)
              and not any(op == INT and v[0] == P10 for op, v in sent + sent2),
              f"6{'c' if sid == BANISH else 'd'}. the player's OWN skill {sid} through "
              f"handle_skill_press + cast_tick: [55, foe, player, -{amount:.0f}/480] with the "
              f"first-word [42, foe, 480] immediately ahead (MAXHP-1), none on the second "
              f"cast, no 16, no [10] (RECONSTRUCTION by the rule; the corpus's own-cast witness "
              f"is the steal 153)", (words(sent, P55, P16), decl, words(sent2, P55)))
        with flags(ARMOUR_IGNORING_ON_55=False):
            st["agents"][FOE]["health"] = 480.0
            sent3 = player_cast(sid, st)
        check(words(sent3, P16) == [(P16, FOE, PLAYER, f32r(-amount / 480.0))]
              and words(sent3, P55) == [],
              f"6{'c' if sid == BANISH else 'd'}2. and the revert arm puts the own cast back on "
              f"16", words(sent3, P16, P55))
    # an AREA's tick on the same rule, both casters (a holy row under a synthetic area).
    # RECONSTRUCTION, like 6c / 6d: no armour-ignoring area over time is on any tape; the
    # rule is carried over from retail's periodic split by type (study section 68.2).
    for caster_kind in ("player", "body"):
        st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0)),
                         HATCHER: body("hatcher", HOSTILE, (0.0, 300.0)),
                         MONK: body("monk", ALLY, (0.0, 60.0), party_slot=0)},
              "pos": (0.0, 0.0)}
        authsrv.player_pools(st)
        caster = PLAYER if caster_kind == "player" else HATCHER
        area = {"id": 1, "skill_id": BANISH, "caster": caster, "caster_kind": caster_kind,
                "hostile": caster_kind == "body", "rank": 0, "amount": 20.0,
                "point": (60.0, 0.0) if caster_kind == "player" else (0.0, 30.0),
                "radius": 100.0, "t0": time.time(), "k": 1, "n": 3,
                "knocks_down": False, "condition": None,
                "caster_row": dict(st["agents"][HATCHER])}
        sent, send = recorder()
        authsrv._area_strike(send, st, 0, area, time.time())
        w55, w16 = words(sent, P55), words(sent, P16, P17)
        want = ([(P55, FOE, PLAYER, f32r(-0.2))] if caster_kind == "player"
                else [(P55, PLAYER, HATCHER, f32r(-20.0 / authsrv.player_max_health(st))),
                      (P55, MONK, HATCHER, f32r(-0.2))])
        check(w55 == want and w16 == [],
              f"6e. an area's tick ({caster_kind} caster) takes the cast's rule: a holy row's "
              f"ticks ride 55 (RECONSTRUCTION: no armour-ignoring area over time is on tape; "
              f"retail's periodic damage splits by type: 272's pulses 64/64 on 55, Fire Storm "
              f"197's ticks 12/12 on 16)", (w55, w16))


def section_source():
    print("\n7. the flag, main()'s wiring, the call sites")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parsed = (ap.parse_args([]).no_armour_ignoring_on_55,
                      ap.parse_args(["--no-armour-ignoring-on-55"]).no_armour_ignoring_on_55)
    except (SystemExit, AttributeError) as exc:
        parsed = ("refused", repr(exc))
    gate = getattr(authsrv, "ARMOUR_IGNORING_ON_55", "absent")
    check(parsed == (False, True) and gate is True,
          "7a. --no-armour-ignoring-on-55 parses (default off) and the channel ships ON",
          (parsed, gate))
    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
              and isinstance(n.test, ast.Attribute) and n.test.attr == "no_armour_ignoring_on_55"]
    flipped = {}
    for flag in (True, False):
        saved = authsrv.ARMOUR_IGNORING_ON_55
        try:
            mod = ast.Module(body=wiring, type_ignores=[])
            ast.fix_missing_locations(mod)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(mod, authsrv.__file__, "exec"),            # noqa: S102
                     authsrv.__dict__, {"a": argparse.Namespace(no_armour_ignoring_on_55=flag)})
            flipped[flag] = authsrv.ARMOUR_IGNORING_ON_55
        finally:
            authsrv.ARMOUR_IGNORING_ON_55 = saved
    check(len(wiring) == 1 and flipped == {True: False, False: True},
          "7b. main()'s `if a.no_armour_ignoring_on_55:` block, lifted and RUN against "
          "authsrv's globals, flips the module bool (a block without its `global` would leave "
          "it True) and leaves it alone when the flag is off", (len(wiring), flipped))

    def spell_kw(fn):
        out = []
        for n in ast.walk(funcs[fn]):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                    and n.func.id == "hit_enemy":
                kws = {k.arg for k in n.keywords}
                out.append(("exact" in kws, "spell_skill" in kws))
        return out
    threaded = {fn: spell_kw(fn) for fn in (
        "land_player_spell_shot", "land_player_spell_area", "burst_player_spell",
        "adjacent_player_spell", "_area_strike", "burst_player_caster_area", "cast_tick")}
    n_threaded = sum(1 for v in threaded.values() for e, s in v if e and s)
    unthreaded = {fn: spell_kw(fn) for fn in ("hex_end_burst", "hit_enemy")}
    check(n_threaded == 8
          and all(s for v in threaded.values() for e, s in v if e)
          and all(e and not s for v in unthreaded.values() for e, s in v),
          "7c. every exact hit_enemy call in the seven player-spell functions names its spell "
          "(8 sites: the projectile, its area, the burst, Mind Burn's two, an area's tick, the "
          "caster burst, cast_tick's one-target word); hex_end_burst's and the block "
          "punishment's do not (they stay 16 by the rule anyway: fire, an attack)",
          (threaded, unthreaded))
    bsw = ast.get_source_segment(open(authsrv.__file__, encoding="utf-8").read(),
                                 funcs["body_spell_word"])
    check("prop = spell_damage_prop(skill_id)" in bsw and "prop=prop" in bsw
          and "[prop, PLAYER_AGENT_ID, agent_id, frac]" in bsw,
          "7d. body_spell_word routes both branches through spell_damage_prop (the player's "
          "word and hurt_agent_row's `prop`)")


# The client's own labels (skilldesc.py's parse, OUR names for the template slots -- no
# template text) and type codes for every skill the corpus names, build 38797; 2809 is not
# in the player corpus and reads through its parent 219 (CASTAI-ZF6). Section 8c re-derives
# them from the client when it is present.
CENSUS_LABELS = {
    102: (5, ("LIFE_STEAL", "SHADOW_DAMAGE")), 133: (5, ("SHADOW_DAMAGE",)),
    143: (5, ("COUNT", "LIFE_STEAL")), 251: (4, ("HOLY_DAMAGE",)), 272: (6, ("HOLY_DAMAGE",)),
    302: (5, ("HOLY_DAMAGE",)), 219: (5, ("DAMAGE",)),
    179: (4, ("CONDITION_DURATION", "DURATION", "FIRE_DAMAGE")),
    185: (5, ("CONDITION_DURATION", "FIRE_DAMAGE")), 186: (5, ("FIRE_DAMAGE",)),
    194: (5, ("FIRE_DAMAGE",)), 197: (5, ("FIRE_DAMAGE",)),
    222: (4, ("DURATION", "LIGHTNING_DAMAGE")), 229: (5, ("LIGHTNING_DAMAGE",)),
    230: (5, ("LIGHTNING_DAMAGE",)), 271: (6, ("ENERGY_LOSS", "FIRE_DAMAGE")),
    322: (14, ("PLUS_DAMAGE",)), 327: (14, ("DAMAGE", "PLUS_DAMAGE")),
    334: (14, ("PLUS_DAMAGE",)), 336: (14, ("PLUS_DAMAGE",)),
    338: (14, ("CONDITION_DURATION", "PLUS_DAMAGE")), 340: (14, ()),
    341: (14, ("DAMAGE", "PLUS_DAMAGE")), 392: (14, ("CONDITION_DURATION",)),
    393: (14, ("CONDITION_DURATION",)), 399: (14, ("DAMAGE",)), 426: (14, ("PLUS_DAMAGE",)),
}
SPLIT_PARENT = {2809: 219}
ON55 = {102: 1, 133: 1, 143: 3, 251: 6, 272: 64, 302: 11, 2809: 8}
IGNORING = {"HOLY_DAMAGE", "SHADOW_DAMAGE", "LIFE_STEAL", "DAMAGE"}
RESPECTING = {"FIRE_DAMAGE", "COLD_DAMAGE", "LIGHTNING_DAMAGE", "EARTH_DAMAGE"}


def rule_55(sid):
    tc, labels = CENSUS_LABELS[SPLIT_PARENT.get(sid, sid)]
    return (tc != authsrv.ATTACK_TYPE_CODE and bool(IGNORING & set(labels))
            and not (RESPECTING & set(labels)))


def holy_key(sid):
    return "HOLY_DAMAGE" in CENSUS_LABELS[SPLIT_PARENT.get(sid, sid)][1]


def section_vault_rows():
    print("\n8a. RECORD against the vault's own skills rows")
    if not HAVE_VAULT_CONTENT:
        LEDGER.skip("8a. RECORD against the vault", "no vault/content directory")
        return
    vault = agents.WORLD.tables["skills"]
    off = {k: sorted(c for c in v if vault.get(k, {}).get(c) != v[c])
           for k, v in RECORD.items() if k not in _TRACKED[0]}
    off = {k: v for k, v in off.items() if v}
    check(off == {},
          f"8a. every RECORD row not tracked in the repo is the vault's own, column for column "
          f"(RECORD copied from {RECORD_BUILD}; a regenerated table that moves a carried column "
          f"reds this, and the fix is to re-copy the row with its build)", off)


def section_corpus():
    print("\n8b. the live corpus: the named census (spellhitjoin.census)")
    if not HAVE_LIVE_CORPUS:
        LEDGER.skip("8b. the named census", "no vault/captures/live directory")
        return
    import spellhitjoin
    named, set_aside, refused = [], [], []
    with contextlib.redirect_stdout(io.StringIO()):
        spellhitjoin.census(named=named, set_aside=set_aside, refused=refused)
    tot = {}
    for _stamp, _conn, d in named:
        for k, n in d.items():
            tot[k] = tot.get(k, 0) + n
    on55 = {s: n for (s, p), n in tot.items() if p == P55}
    on16 = {s for (s, p) in tot if p in (P16, P17)}
    check(on55 == ON55 and sum(on55.values()) == 94 and len(on16) >= 20
          and not (set(on55) & on16) and [c for _s, c, _w in set_aside] == [
              "10.0.0.210:65009->98.95.137.136:80"] and refused == [],
          "8b. the wire's own naming over the whole corpus: the 55 side is EXACTLY "
          "{102: 1, 133: 1, 143: 3, 251: 6, 272: 64, 302: 11, 2809: 8} (94 words), the 16 / 17 "
          "side >= 20 skills, no skill on both; :65009 set aside by its manifest, nothing refused",
          (on55, sorted(on16), set_aside, refused))
    named_ids = set(on55) | on16
    unknown = sorted(s for s in named_ids if SPLIT_PARENT.get(s, s) not in CENSUS_LABELS)
    split_rule = {s for s in named_ids if s not in unknown and rule_55(s)}
    split_holy = {s for s in named_ids if s not in unknown and holy_key(s)}
    check(unknown == [] and split_rule == set(on55) and split_holy == {251, 272, 302}
          and sorted(set(on55) - split_holy) == [102, 133, 143, 2809],
          "8b2. the rule SEPARATES the census: \"armour-ignoring label on a non-attack\" "
          "predicts the 55 side exactly (7 of 7) and the 16 side exactly; a rule keyed on HOLY "
          "takes 251 / 272 / 302 and FAILS on 4 of the 7 (102, 133 shadow; 143 a steal; 2809 "
          "untyped)", (unknown, sorted(split_rule), sorted(split_holy)))
    # known-bad arm: the rule without its attack exclusion takes 399 (and 327 / 341) onto 55
    loose = {s for s in named_ids if bool(IGNORING & set(CENSUS_LABELS[SPLIT_PARENT.get(s, s)][1]))
             and not (RESPECTING & set(CENSUS_LABELS[SPLIT_PARENT.get(s, s)][1]))}
    check(loose - set(on55) == {327, 341, 399},
          "8b3. known-bad arm: drop the ATTACK exclusion and 327, 341 and 399 (untyped DAMAGE on "
          "an attack) are predicted on 55 where retail named all three on 16 / 17",
          sorted(loose - set(on55)))


def section_client_labels():
    print("\n8c. the client's templates re-read (skilldesc.py, labels only)")
    if not HAVE_CLIENT:
        LEDGER.skip("8c. the client's labels", "no vault/client directory")
        return
    sys.path.insert(0, os.path.join(PARENT, "clientscan"))
    import skilldesc
    with contextlib.redirect_stdout(io.StringIO()):
        records, texts, _ix, _exe, _why = skilldesc.load_corpus()
        rep = skilldesc.analyse(records, texts)
    got = {sid: (int(records[sid]["type_code"]),
                 tuple(sorted({s["label"] for s in rep["rows"][sid]["slots"]})))
           for sid in CENSUS_LABELS}
    diff = {k: (got[k], CENSUS_LABELS[k]) for k in CENSUS_LABELS if got[k] != CENSUS_LABELS[k]}
    check(diff == {} and 2809 not in records,
          "8c. CENSUS_LABELS is the client's own parse, skill for skill (type and label set); "
          "2809 is outside the player corpus (a PvP split, read through 219)", diff)
    rec = records.get(STEAL) or {}
    row_vis = visual_row(STEAL)
    check(rec.get("visual_recipient") == row_vis.get("recipient") == 276
          and rec.get("visual_caster") == 2077 and "caster" not in row_vis,
          "8c2. skill_visual.153 is the client's own row: +0x7c (the recipient) 276, +0x78 "
          "the 2077 no-visual default, so the content row carries no caster",
          ({k: rec.get(k) for k in ("visual_caster", "visual_recipient")}, dict(row_vis)))

def section_steal_server():
    print("\n9. LIFE STEAL on the server (SKILLS-CH3): Vampiric Gaze 153 both directions")
    steal = getattr(authsrv, "skill_steal", lambda *_a: "absent")
    amt = (steal(STEAL, 0), steal(STEAL, 10))
    with flags(LIFE_STEAL=False):
        off = steal(STEAL, 10)
    check(amt == (18, 46) and off is None and authsrv.skill_damage(STEAL, 0) is None
          and authsrv.skill_heal(STEAL, 0) is None and prop_of(STEAL) == P55,
          "9a. the row reads as a STEAL, not as damage or a heal: 18 at rank 0 and 46 at rank "
          "10 -- the tape's two amounts through our own interpolator (the ranks are "
          "RECONSTRUCTION) -- None under --no-life-steal, and its word's property is 55",
          (amt, off, prop_of(STEAL)))
    # (b) the player's OWN steal on a hurt foe whose maximum the client has not been told
    st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0), health=300.0, max_health=480.0,
                               max_declared_on_hit=None)},
          "pos": (0.0, 0.0)}
    authsrv.player_pools(st)
    pool = authsrv.player_max_health(st)
    st["player_health"] = pool - 50.0
    sent = player_cast(STEAL, st)
    e5 = next((i for i, (op, v) in enumerate(sent) if op == authsrv.GAME_SMSG_SKILL_RECHARGE
               and v[1] == STEAL), None)
    shape = [(op, v[0], v[1], v[2]) for op, v in sent[(e5 or 0):]
             if (op == FLOAT_T and v[0] in (P55, P16, P17)) or (op == INT and v[0] in (P42, P10))
             or (op == INT_T and v[0] == P20)]
    want = [(INT_T, P20, FOE, PLAYER), (INT, P42, PLAYER, int(pool)),
            (FLOAT_T, P55, PLAYER, PLAYER), (INT, P42, FOE, 480), (FLOAT_T, P55, FOE, PLAYER)]
    vis = [v for op, v in sent if op == INT_T and v[0] == P20]
    hl, wd = heals(sent), words(sent, P55, P16, P17)
    check(e5 is not None and shape == want and vis == [[P20, FOE, PLAYER, 276]]
          and hl == [(PLAYER, PLAYER, f32r(18.0 / pool))]
          and wd == [(P55, FOE, PLAYER, f32r(-18.0 / 480.0))]
          and not any(op == GAIN for op, _v in sent)
          and st["player_health"] == pool - 32.0 and st["agents"][FOE]["health"] == 282.0,
          "9b. the player's OWN 153 through handle_skill_press + cast_tick, behind its E5: "
          "the visual [20, foe, me, 276] (skill_visual.153; retail 13 of 13), [42, me, max] "
          "(the FIXTURE's never-told maximum -- declare_player_max's moved-only rule; retail "
          "re-declares an UNCHANGED one on 7 of 13, CONTESTED, studies/skills 68.4), the heal "
          "[55, me, me, +18/max], the foe's first-word [42, foe, 480], the word [55, foe, me, "
          "-18/480] -- the order of retail's :58544 593.854 batch -- no [10], no 16 / 17, no "
          "gain (the bar's real adrenal costs gate it); the player +18, the foe -18",
          (e5, shape, vis, hl, wd, st["player_health"], st["agents"][FOE]["health"]))
    # (c) Deep Wound does not cut a steal's heal (WIKI, GWW "Deep Wound" rev. 2026-03-02)
    st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0), health=300.0, max_health=480.0)},
          "pos": (0.0, 0.0), "deep_wound": {PLAYER: 20.0}}
    authsrv.player_pools(st)
    pool = authsrv.player_max_health(st)
    st["player_health"] = pool - 50.0
    sent = player_cast(STEAL, st)
    check(heals(sent) == [(PLAYER, PLAYER, f32r(18.0 / pool))]
          and st["player_health"] == pool - 32.0,
          "9c. under a Deep Wound the steal's heal is NOT cut: +18 lands whole (healing=False; "
          "a heal would be cut to 14)", (heals(sent), pool, st["player_health"]))
    # (c2) the BODY door's heal, the same rule (the review's CD-3): a Deep-Wounded Hatcher
    # at 50 steals 18 from the player through land_skill -> body_life_steal
    st, sent = body_cast(STEAL, hatcher_health=50.0, deep_wound={HATCHER: 20.0})
    pool = authsrv.player_max_health(st)
    check(heals(sent) == [(HATCHER, HATCHER, f32r(0.18))]
          and st["agents"][HATCHER]["health"] == 68.0
          and words(sent, P55, P16, P17) == [(P55, PLAYER, HATCHER, f32r(-18.0 / pool))],
          "9c2. and through the BODY door: a Deep-Wounded hostile's 153 at the player heals "
          "the caster the whole 18 (50 -> 68, +0.18; healing=True would send +0.14 and leave "
          "it at 64)", (heals(sent), st["agents"][HATCHER]["health"], words(sent, P55)))
    # (d) a hostile's 153 at the PLAYER through the real land_skill: retail's 143 tail
    st, sent = body_cast(STEAL)
    pool = authsrv.player_max_health(st)
    i_w = next((i for i, (op, v) in enumerate(sent) if op == FLOAT_T and v[0] == P55
                and v[1] == PLAYER), None)
    four = sent[i_w - 3:i_w + 1] if i_w is not None and i_w >= 3 else []
    ok_shape = (len(four) == 4 and four[0][0] == GAIN and four[0][1][0] == PLAYER
                and four[1][0] == FLOAT_T and four[1][1][:3] == [P55, HATCHER, HATCHER]
                and not (four[1][1][3] & 0x80000000)
                and four[2] == (INT, [P10, PLAYER, STEAL])
                and four[3][1][:3] == [P55, PLAYER, HATCHER] and bool(four[3][1][3] & 0x80000000))
    check(ok_shape and heals(sent) == [(HATCHER, HATCHER, f32r(18.0 / 100.0))]
          and words(sent, P55, P16, P17) == [(P55, PLAYER, HATCHER, f32r(-18.0 / pool))]
          and st["player_health"] == pool - 18.0,
          "9d. a hostile's 153 at the PLAYER through land_skill ends in retail's 143 tail, "
          "message for message: 0x00CF [me, n], the caster's [55, hatcher, hatcher, +18/100], "
          "[10, me, 153], [55, me, hatcher, -18/max] (20260916T213125 :57894, 3 of 3); one "
          "word, the player -18", [(hex(op), v) for op, v in four])
    # (e) a hostile's steal on a party body
    st, sent = body_cast(STEAL, cast_target=MONK, monk_health=50.0)
    hi = next((i for i, (op, v) in enumerate(sent) if op == FLOAT_T and v[0] == P55
               and not (v[3] & 0x80000000)), None)
    wi = next((i for i, (op, v) in enumerate(sent) if op == FLOAT_T and v[0] == P55
               and (v[3] & 0x80000000)), None)
    check(heals(sent) == [(HATCHER, HATCHER, f32r(0.18))]
          and words(sent, P55, P16, P17) == [(P55, MONK, HATCHER, f32r(-0.18))]
          and None not in (hi, wi) and hi < wi
          and not any(op == INT and v[0] == P10 for op, v in sent)
          and st["agents"][MONK]["health"] == 32.0,
          "9e. a hostile's 153 on a PARTY body: the caster's heal, then [55, monk, hatcher, "
          "-0.18], no [10]; the monk 50 -> 32 (RECONSTRUCTION: no body-on-body steal is "
          "ordered on tape; the own steal's heal-first order is used)",
          (heals(sent), words(sent, P55, P16), hi, wi, st["agents"][MONK]["health"]))
    # (f) a party body's lethal steal on a hostile: the kill pays
    st, sent = body_cast(STEAL, caster_allegiance=ALLY, cast_target=FOE, foe_health=10.0,
                         monk_health=50.0)
    check(heals(sent) == [(MONK, MONK, f32r(0.18))]
          and words(sent, P55, P16, P17) == [(P55, FOE, MONK, f32r(-0.18))]
          and st["agents"][FOE]["dead"] and KILL_REWARD in [op for op, _v in sent]
          and st["agents"][MONK]["health"] == 68.0,
          "9f. a PARTY body's 153 on a hostile at 10: the monk heals 18 (50 -> 68), the word "
          "carries the raw 18, the hostile dies and the kill pays the reward",
          (heals(sent), words(sent, P55, P16), st["agents"][FOE]["dead"],
           st["agents"][MONK]["health"]))
    # (g) a lethal hostile steal at the player
    calls = []
    real = authsrv.kill_player

    def counting(*a, **k):
        calls.append(1)
        return real(*a, **k)
    authsrv.kill_player = counting
    try:
        st, sent = body_cast(STEAL, player_health=5.0)
    finally:
        authsrv.kill_player = real
    deaths = [v for op, v in sent if op == STATUS and v[0] == PLAYER and v[1] & agents.EFFECT_DEAD]
    check(len(words(sent, P55)) == 1 and len(heals(sent)) == 1 and len(calls) == 1
          and len(deaths) == 1 and st["player_dead"],
          "9g. a LETHAL steal at the player: one heal to the caster, one word, one kill, one "
          "death word", (words(sent, P55), heals(sent), len(calls), deaths))
    # (h) the known-bad arm: --no-life-steal -- the energy for nothing, both directions
    with flags(LIFE_STEAL=False):
        st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0), health=300.0,
                                   max_health=480.0)}, "pos": (0.0, 0.0)}
        authsrv.player_pools(st)
        own = player_cast(STEAL, st)
        _, hostile = body_cast(STEAL)
    vis_off = [v for op, v in own + hostile
               if (op == INT_T and v[0] == P20 and v[3] == 276)
               or (op == INT and v[0] == agents.GV_EFFECT_ON_AGENT and v[2] == 276)]
    check(heals(own) == [] and words(own, P55, P16, P17) == [] and heals(hostile) == []
          and words(hostile, P55, P16, P17) == [] and st["agents"][FOE]["health"] == 300.0
          and vis_off == [],
          "9h. --no-life-steal: the own 153 and a hostile's resolve to NOTHING -- no heal, no "
          "word, and no 276 visual (skill_visual.153 is marked since = CHAN55; every session "
          "before 2026-10-07 had no row; retail moves the amount 13 of 13 and 3 of 3)",
          (heals(own), words(own, P55), heals(hostile), words(hostile, P55), vis_off))
    # (i) the CHANNEL flag does not split the steal (the review's EV-4): under
    # --no-armour-ignoring-on-55 the own steal's word and a hostile's both keep 55 --
    # the steal's channel is OBSERVED and its revert is --no-life-steal -- while the
    # holy words the rule routes go back to 16
    with flags(ARMOUR_IGNORING_ON_55=False):
        st = {"agents": {FOE: body("foe", HOSTILE, (60.0, 0.0), health=300.0,
                                   max_health=480.0)}, "pos": (0.0, 0.0)}
        authsrv.player_pools(st)
        own = player_cast(STEAL, st)
        sth, hostile = body_cast(STEAL)
        props = (prop_of(STEAL), prop_of(HOLY_STRIKE))
    pool = authsrv.player_max_health(sth)
    check(words(own, P55, P16, P17) == [(P55, FOE, PLAYER, f32r(-18.0 / 480.0))]
          and words(hostile, P55, P16, P17) == [(P55, PLAYER, HATCHER, f32r(-18.0 / pool))]
          and props == (P55, P16),
          "9i. --no-armour-ignoring-on-55 leaves the steal on 55 at BOTH doors (the own "
          "cast's hit_enemy word and a hostile's armour_ignoring_damage word) and moves Holy "
          "Strike to 16 -- one flag never splits the steal's channel",
          (words(own, P55, P16, P17), words(hostile, P55, P16, P17), props))


def section_steal_source():
    print("\n10. --no-life-steal: the flag, main()'s wiring, the row")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parsed = (ap.parse_args([]).no_life_steal,
                      ap.parse_args(["--no-life-steal"]).no_life_steal)
    except (SystemExit, AttributeError) as exc:
        parsed = ("refused", repr(exc))
    check(parsed == (False, True) and getattr(authsrv, "LIFE_STEAL", "absent") is True,
          "10a. --no-life-steal parses (default off) and the steal ships ON", parsed)
    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
              and isinstance(n.test, ast.Attribute) and n.test.attr == "no_life_steal"]
    flipped = {}
    for flag in (True, False):
        saved = getattr(authsrv, "LIFE_STEAL", _MISSING)
        try:
            mod = ast.Module(body=wiring, type_ignores=[])
            ast.fix_missing_locations(mod)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(mod, authsrv.__file__, "exec"),            # noqa: S102
                     authsrv.__dict__, {"a": argparse.Namespace(no_life_steal=flag)})
            flipped[flag] = getattr(authsrv, "LIFE_STEAL", "absent")
        finally:
            if saved is _MISSING:
                authsrv.__dict__.pop("LIFE_STEAL", None)
            else:
                authsrv.LIFE_STEAL = saved
    check(len(wiring) == 1 and flipped == {True: False, False: True},
          "10b. main()'s `if a.no_life_steal:` block, lifted and RUN, flips the module bool",
          (len(wiring), flipped))
    bare = agents.content.load(vault_dir="", extra_dirs=[])
    row = bare.rows("skill_effect").get("153") or {}
    prov = getattr(row, "provenance", None) or {}
    check(row.get("scale_means") == "Life stealing" and prov.get("source") == "capture"
          and prov.get("origin") == "live" and prov.get("capture") == "20260929T100038",
          "10c. content/world.toml (tracked, a bare load) carries skill_effect.153 as a "
          "capture row (live, 20260929T100038) labelled \"Life stealing\"",
          (dict(row), {k: prov.get(k) for k in ("source", "origin", "capture")}))
    vis = bare.rows("skill_visual").get("153") or {}
    vprov = getattr(vis, "provenance", None) or {}
    check(vis.get("recipient") == 276 and "caster" not in vis and vis.get("since") == "CHAN55"
          and vprov.get("source") == "client-table" and vprov.get("build") == 38797
          and vprov.get("extractor") == "toolkit/clientscan/skilltable.py",
          "10d. and skill_visual.153: recipient 276, no caster visual, a client-table row "
          "(skilltable.py, build 38797) marked since = CHAN55 -- the [20] retail's own steal "
          "batch carries 13 of 13 (the review's EV-2: the first cut had no row)",
          (dict(vis), {k: vprov.get(k) for k in ("source", "build", "extractor")}))


def section_steal_corpus():
    print("\n11. the live corpus: stealjoin.py, both directions")
    if not HAVE_LIVE_CORPUS:
        LEDGER.skip("11. the steal corpus", "no vault/captures/live directory")
        return
    import collections
    import stealjoin
    got = stealjoin.census()
    own, hostile = got["own"], got["hostile"]
    amounts = collections.Counter(round(r["heal_pts"]) for r in own if r["heal_pts"] is not None)
    by_cap = collections.Counter(r["capture"] for r in own)
    check(collections.Counter(r["skill"] for r in own) == {STEAL: 13}
          and got["completions"][STEAL] == 13
          and all(r["named"] == [] and r["damage_16"] == [] for r in own)
          and all(r["heal_pts"] is not None and r["heal_pts"] == r["dmg_pts"] for r in own)
          and amounts == {18: 2, 46: 11}
          and by_cap == {"20260807T143055": 2, "20260928T103123": 5, "20260929T100038": 6}
          and len({r["connection"] for r in own}) == 7
          and all(set(r["between"]) <= {(0x009F, P42)} for r in own)
          and got["set_aside"] == [("20260928T103123", "10.0.0.210:65009->98.95.137.136:80")],
          "11a. OWN: every one of the observer's 13 Vampiric Gaze completions (7 connections, "
          "3 captures) carries the heal [55, me, me, +h] and then the word [55, foe, me, -d] "
          "with nothing but the foe's [42] between; |h| == |d| in points 13 of 13 (18 x 2, 46 "
          "x 11); no [10], no 16 / 17 -- and no 153 completion lacks the pair",
          (dict(amounts), dict(by_cap), got["completions"][STEAL]))
    check(got["word_first"] == [] and all(r["heal_frac"] > 0 > r["dmg_frac"] for r in own),
          "11b. known-bad reader: wanting the WORD first and the heal after it finds 0 of the "
          "13 -- the order is the tape's, not the search's", len(got["word_first"]))
    steals = [r for r in hostile if r["steal"]]
    check(collections.Counter(r["skill"] for r in steals) == {143: 3}
          and all(r["order"] == (r["order"][2] - 2, r["order"][2] - 1, r["order"][2],
                                 r["order"][2] + 1) for r in steals)
          and all(abs(r["heal_frac"] + r["dmg_frac"]) < 1e-6 for r in steals)
          and len(hostile) == 94,
          "11c. HOSTILE: of the 94 named 55 words at the observer, the steal-shaped ones are "
          "143 x 3, each the four consecutive messages gain, the caster's heal, [10], the word, "
          "heal fraction == word fraction (41 of 480; the caster's maximum is not on the wire)",
          [(r["skill"], r["order"], r["heal_frac"], r["dmg_frac"]) for r in steals])
    # (d) what rides AHEAD of the heal (the review's EV-1 and EV-2): the observer's own
    # [42, me] on 7 of 13, every one an UNCHANGED maximum re-declared -- so
    # declare_player_max's moved-only rule (0 of 13 in a seeded session) is CONTESTED --
    # and the recipient visual on 13 of 13, the tracked skill_visual.153's value
    ahead = [r for r in own if r["self_max"]]
    moved = [r for r in ahead if r["self_max"][-1] != r["self_max_prior"]]
    row_vis = visual_row(STEAL).get("recipient")
    check(len(ahead) == 7 and moved == [] and row_vis == 276
          and all(r["visual"] == [row_vis] for r in own)
          and sum(1 for r in own if r["between"]) == 2,
          "11d. ahead of the heal: [42, me] on 7 of the 13, and 0 of the 7 a MOVED maximum "
          "(each equals the last [42, me] before the E5 -- a re-declare our moved-only rule "
          "never sends, CONTESTED); the visual [20, foe, me, 276] on 13 of 13, skill_visual.153's "
          "value; the foe's [42] between the heal and the word on 2 of 13",
          ([(round(r["t"], 3), r["self_max"], r["self_max_prior"]) for r in ahead],
           sorted({tuple(r["visual"]) for r in own}), row_vis))


def guarded(section):
    """Run one section; an exception is a FAIL naming it (a server without the change
    raises on a keyword it does not take), never a crash that hides the other sections."""
    try:
        section()
    except Exception as exc:                                   # noqa: BLE001
        check(False, f"{section.__name__} RAISED -- the section did not run to its end",
              repr(exc)[:300])


def main():
    t0 = time.time()
    with carried():
        for section in (section_helper, section_hostile_at_player, section_known_bad,
                        section_controls, section_lethal, section_bodies_and_own,
                        section_steal_server):
            guarded(section)
    for section in (section_source, section_vault_rows, section_corpus,
                    section_client_labels, section_steal_source, section_steal_corpus):
        guarded(section)
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
