r"""test_bodywindup -- CASTAI-ZF16: a BODY's attack skill with a listed activation lands
(a bow: launches) at the windup of that activation (2026-09-28; studies/monsterai
FINDINGS 18.2, studies/weapons PLAN 44).

    python toolkit/authsrv/test_bodywindup.py

WHAT IT IS REALLY CHECKING. Retail launches a body's bow ATTACK skill that carries a
table activation swing_windup(activation x the 0x0035 modifier) after its [50]
announcement, OBSERVED 18 of 18 (WITNESS below): Distracting Shot 399 and Savage Shot
426 (0.5) at 0.1377 .. 0.1674 s, 1197 (0.75) at 0.2681 .. 0.2865 s. That is SLICE-F51's
law for the player (authsrv.attack_skill_clock). Both body loops -- enemy_attack_tick
for a hostile, ally_cast_tick for a party body -- armed the landing at the RAW
activation, 0.5 / 0.75 s. They now call authsrv.body_attack_skill_clock, behind
BODY_ATTACK_ACTIVATION_WINDUP (--no-body-attack-activation-windup reverts).

  1  the clock on literals: 0.5 -> 0.15, 0.75 -> 0.275, activation 0 -> the windup of
     the interval (F24, untouched), the revert -> the raw activation; the body's own
     duration factor scales the activation (the player's law carried over: every
     activated row on tape is at modifier 1.0, so that term is UNVERIFIED on bodies).
  2  THE SENDER, a hostile archer through the real enemy_attack_tick on a fake clock
     stepped 1 ms: [50, it, player, skill] then one 0x00A4; the gap between them lies
     inside the span of that skill's retail witnesses, for 399, 426 and 1197. The
     KNOWN-BAD arm (the flag off) launches at the raw activation, outside every one.
  3  the same through ally_cast_tick: a party archer at the leader's target.
  4  the control: Power Shot 394 (table activation 0) launches at the windup of the
     body's interval under both arms -- F24's branch is not this change's.
  5  source: the flag in serverargs and flipped in main(); both loops call the clock;
     the press handler's comment no longer calls the law UPSTREAM.
  6  the vault: WITNESS re-derived from the two captures (weaponcensus.skill_shots),
     and the carried skill rows against the vault's table. Skips ONLY when a capture
     directory / the vault's skills table is absent.

The skill rows are carried (skilltable.py's record, build 38797 -- measured numbers,
CLAUDE.md's gate) and REPLACE the table for the driven sections, so a vault run takes
exactly the bare path (test_weapons' pattern).
"""
import contextlib
import io
import os
import sys

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

# Floor from the BARE-MACHINE green run (RURIK_VAULT at a nonexistent path),
# 2026-09-28, MEASURED: 21 -- sections 1-5 (4 + 6 + 4 + 1 + 6), section 6 skipping
# by name. A vault run adds section 6's two checks: 23.
LEDGER = checks.Ledger("body attack-skill windup (CASTAI-ZF16)", floor=21)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
LAUNCH = authsrv.GAME_SMSG_AGENT_PROJECTILE_LAUNCHED
HOSTILE, HERO = 10, 200
DISTRACTING, SAVAGE, ACT_075, POWER_SHOT = 399, 426, 1197, 394
LONGBOW = 2.475                      # retail's 0x0035 base for both witnessed archers
STEP = 0.001
T0 = 1_000_000.0

# THE WITNESSES, per shot: [50] -> 0x00A4 seconds, every body bow ATTACK skill with a
# table activation on the live corpus (test_weaponcensus's slow_kind, whose
# _fast_launch_witness pins each shot's (port, t)). All at 0x0035 modifier 1.0, base
# 2.475. Section 6 re-derives these from the captures.
WITNESS = {
    ("20260928T103123", 6): {        # the Degeneration Ranger, :50061 and :58544
        DISTRACTING: [0.1418, 0.1480, 0.1511, 0.1518, 0.1674],
        SAVAGE: [0.1377, 0.1465, 0.1472, 0.1503, 0.1552, 0.1589],
    },
    ("20260819T132414", 28): {       # :52606
        ACT_075: [0.2681, 0.2765, 0.2774, 0.2837, 0.2839, 0.2852, 0.2865],
    },
}
SPAN = {sk: (min(v), max(v)) for per in WITNESS.values() for sk, v in per.items()}


def _record(activation, aftercast, recharge, energy, attribute, target, aoe_range,
            skill_arguments, scale, bonus_scale, projectile, impact_visual):
    """test_weapons' _record shape, for a Ranger (2) bow attack (type 14, weapon_req 2)."""
    return {"activation": activation, "aftercast": aftercast, "recharge": recharge,
            "energy": energy, "adrenaline": 0, "adrenaline_units": 0,
            "attribute": attribute, "profession": 2, "type_code": 14, "target": target,
            "combo": 0, "combo_req": 0, "weapon_req": 2, "aoe_range": aoe_range,
            "skill_arguments": skill_arguments, "duration0": 0, "duration15": 0,
            "scale0": scale[0], "scale15": scale[1], "bonus_scale0": bonus_scale[0],
            "bonus_scale15": bonus_scale[1], "projectile": projectile,
            "impact_visual": impact_visual, "touch_range": False, "half_range": False}


# skilltable.py's record, build 38797 (the vault's content/skills.toml; section 6
# checks each row against it).
RECORD = {
    "394": _record(0.0, 0.0, 3, 10, 25, 5, 0.0, 2, (25, 50), (0, 0), 680, 2077),
    "399": _record(0.5, 1.5, 10, 5, 23, 5, 0.0, 2, (1, 16), (20, 20), 728, 729),
    "426": _record(0.5, 1.5, 5, 10, 25, 5, 0.0, 2, (13, 28), (0, 0), 2077, 2077),
    "1197": _record(0.75, 0.6, 4, 5, 25, 5, 4800.0, 4, (50, 50), (10, 30), 2077, 2077),
}

FLAGS = ("BODY_ATTACK_ACTIVATION_WINDUP", "ENERGY", "NPC_FOLLOW", "EFFECTS",
         "NPC_ATTACK_SKILL_SWINGS", "INSTANT_ANNOUNCE")


class Clock:
    """A fake `time` module for authsrv: the ticks read `time.time()`."""

    def __init__(self, t):
        self.t = t

    def time(self):
        return self.t

    def __getattr__(self, name):
        import time as _real
        return getattr(_real, name)


@contextlib.contextmanager
def arm(clock, **flags):
    """The carried rows as the skills table, the named flags and the fake clock for
    the block; all restored after."""
    saved = {k: getattr(authsrv, k) for k in FLAGS}
    saved_time = authsrv.time
    tables = agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    base = {"BODY_ATTACK_ACTIVATION_WINDUP": True, "ENERGY": False, "NPC_FOLLOW": False,
            "EFFECTS": True, "NPC_ATTACK_SKILL_SWINGS": True, "INSTANT_ANNOUNCE": True}
    base.update(flags)
    for k, v in base.items():
        setattr(authsrv, k, v)
    authsrv.time = clock
    tables["skills"] = {k: dict(v) for k, v in RECORD.items()}
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(authsrv, k, v)
        authsrv.time = saved_time
        if had:
            tables["skills"] = kept
        else:
            del tables["skills"]


def _body(skill, allegiance, pos):
    sid = str(skill)
    return {"name": "archer", "dead": False, "died_at": 0.0, "health": 1e6,
            "max_health": 1e6, "last_hit": 0.0, "pos": pos, "plane": 0,
            "allegiance": allegiance, "attack_speed": LONGBOW, "effects": 0,
            "attacks_back": allegiance == agents.ALLEGIANCE_HOSTILE,
            "weapon_item": "hostile_bow", "npc": {"profession": 2, "level": 5},
            "skills": ((skill, float(RECORD[sid]["activation"]),
                        float(RECORD[sid]["recharge"])),),
            "skill_ready": [0.0]}


def _world():
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 1e9, "player_dead": False}
    authsrv.effect_table(st)
    return st


def _drive(st, tick, caster, secs=1.0):
    """Run `tick` every STEP for `secs` on the fake clock (authsrv.time must be a
    Clock). Returns (announce t, [launch t], log): the caster's [50] and its 0x00A4s."""
    sends = []

    def send(op, vals, label="", quiet=False):
        sends.append((authsrv.time.t, op, list(vals)))

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for i in range(int(round(secs / STEP)) + 1):
            authsrv.time.t = T0 + i * STEP
            st["player_health"] = 1e9
            tick(send, st, 0)
    ann = [t for t, op, v in sends if op == INT_T and v[:2] == [agents.GV_ATTACK_SKILL_ACTIVATED,
                                                                caster]]
    launches = [t for t, op, v in sends if op == LAUNCH and v[0] == caster]
    return (ann[0] if ann else None), launches, out.getvalue()


def hostile_shot(skill, windup=True, secs=1.0):
    """A hostile archer 600 u from the player fires `skill`; (gap, launches, log)."""
    with arm(Clock(T0), BODY_ATTACK_ACTIVATION_WINDUP=windup):
        st = _world()
        st["agents"][HOSTILE] = _body(skill, agents.ALLEGIANCE_HOSTILE, (600.0, 0.0))
        ann, launches, log = _drive(st, authsrv.enemy_attack_tick, HOSTILE, secs)
    return (None if ann is None or not launches else launches[0] - ann), launches, log


def party_shot(skill, windup=True, secs=1.0):
    """A party archer 600 u from a hostile the leader just engaged fires `skill`."""
    with arm(Clock(T0), BODY_ATTACK_ACTIVATION_WINDUP=windup):
        st = _world()
        foe = _body(DISTRACTING, agents.ALLEGIANCE_HOSTILE, (600.0, 0.0))
        foe.update(skills=(), skill_ready=[], attacks_back=False)
        st["agents"][HOSTILE] = foe
        hero = _body(skill, agents.ALLEGIANCE_PLAYER, (0.0, 50.0))
        hero["party_slot"] = 0
        st["agents"][HERO] = hero
        st["leader_engaged"] = {"target": HOSTILE, "at": T0, "why": "swing"}
        ann, launches, log = _drive(st, authsrv.ally_cast_tick, HERO, secs)
    return (None if ann is None or not launches else launches[0] - ann), launches, log


def within(gap, skill):
    lo, hi = SPAN[skill]
    return gap is not None and lo <= gap <= hi


def fmt(gap):
    return "none" if gap is None else f"{gap:.4f} s"


# ---------------------------------------------------------------------------------
def section_clock():
    print("== 1. body_attack_skill_clock, on literals ==")
    clock, w = authsrv.body_attack_skill_clock, authsrv.swing_windup
    st = _world()
    saved = authsrv.BODY_ATTACK_ACTIVATION_WINDUP
    try:
        authsrv.BODY_ATTACK_ACTIVATION_WINDUP = True
        on = [clock(st, HOSTILE, a, LONGBOW) for a in (0.5, 0.75, 0.0)]
        authsrv.BODY_ATTACK_ACTIVATION_WINDUP = False
        off = [clock(st, HOSTILE, a, LONGBOW) for a in (0.5, 0.75, 0.0)]
    finally:
        authsrv.BODY_ATTACK_ACTIVATION_WINDUP = saved
    check(abs(on[0] - 0.15) < 1e-9 and abs(on[1] - 0.275) < 1e-9,
          "a listed activation is wound up: 0.5 -> 0.15, 0.75 -> 0.275 (half less 0.1)",
          f"{on}")
    check(abs(on[2] - w(LONGBOW)) < 1e-9 and abs(off[2] - w(LONGBOW)) < 1e-9,
          "  activation 0 is the windup of the INTERVAL under both arms (F24's branch)",
          f"on {on[2]} off {off[2]} windup {w(LONGBOW)}")
    check(off[:2] == [0.5, 0.75],
          "  the revert returns the raw activation (the pre-ZF16 landing)", f"{off}")
    real = authsrv.attack_interval_factor
    try:
        authsrv.attack_interval_factor = lambda state, aid: 1.5 if aid == HOSTILE else 1.0
        scaled = clock(st, HOSTILE, 0.5, LONGBOW * 1.5)
        other = clock(st, HERO, 0.5, LONGBOW)
    finally:
        authsrv.attack_interval_factor = real
    check(abs(scaled - w(0.75)) < 1e-9 and abs(other - 0.15) < 1e-9,
          "  the BODY's own duration factor scales the activation: 0.5 x 1.5 winds up to "
          "0.275; another body's factor is not read (the player's law; UNVERIFIED on "
          "bodies, every activated row on tape is at 1.0)", f"{scaled} {other}")


def section_hostile():
    print("== 2. the sender: a hostile archer through enemy_attack_tick ==")
    for skill in (DISTRACTING, SAVAGE, ACT_075):
        gap, launches, log = hostile_shot(skill)
        act = float(RECORD[str(skill)]["activation"])
        want = authsrv.swing_windup(act)
        check(len(launches) == 1 and within(gap, skill) and abs(gap - want) <= STEP + 1e-6,
              f"hostile {skill} (activation {act}): [50] -> 0x00A4 {fmt(gap)}, "
              f"swing_windup({act}) = {want:.3f}, inside retail's {len(WITNESS_OF[skill])} "
              f"witnesses {SPAN[skill][0]:.4f} .. {SPAN[skill][1]:.4f}",
              f"launches {len(launches)}; log tail {log[-400:]!r}")
        bad, _l, _log = hostile_shot(skill, windup=False)
        check(bad is not None and abs(bad - act) <= STEP + 1e-6 and not within(bad, skill),
              f"  the KNOWN-BAD arm launches at the raw {act} s ({fmt(bad)}) -- outside "
              f"every witness", f"{fmt(bad)}")


def section_party():
    print("== 3. the sender: a party archer through ally_cast_tick ==")
    for skill in (DISTRACTING, ACT_075):
        gap, launches, log = party_shot(skill)
        act = float(RECORD[str(skill)]["activation"])
        want = authsrv.swing_windup(act)
        check(len(launches) == 1 and within(gap, skill) and abs(gap - want) <= STEP + 1e-6,
              f"party {skill} (activation {act}): [50] -> 0x00A4 {fmt(gap)}, inside "
              f"retail's {SPAN[skill][0]:.4f} .. {SPAN[skill][1]:.4f}",
              f"launches {len(launches)}; log tail {log[-400:]!r}")
        bad, _l, _log = party_shot(skill, windup=False)
        check(bad is not None and abs(bad - act) <= STEP + 1e-6 and not within(bad, skill),
              f"  the KNOWN-BAD arm launches at the raw {act} s ({fmt(bad)})", f"{fmt(bad)}")


def section_control():
    print("== 4. the control: Power Shot 394, activation 0 ==")
    want = authsrv.swing_windup(LONGBOW)
    got = {}
    for arm_on in (True, False):
        got[("hostile", arm_on)] = hostile_shot(POWER_SHOT, windup=arm_on, secs=1.5)[0]
        got[("party", arm_on)] = party_shot(POWER_SHOT, windup=arm_on, secs=1.5)[0]
    check(all(g is not None and abs(g - want) <= STEP + 1e-6 for g in got.values()),
          f"394 launches swing_windup({LONGBOW}) = {want:.4f} s after its [50] from a "
          f"hostile and a party body under BOTH arms -- the flag moves only a listed "
          f"activation", str({k: fmt(v) for k, v in got.items()}))


def section_source():
    print("== 5. source ==")
    with open(os.path.join(HERE, "serverargs.py"), encoding="utf-8") as fh:
        args = fh.read()
    with open(os.path.join(HERE, "authsrv.py"), encoding="utf-8") as fh:
        src = fh.read()
    check('"--no-body-attack-activation-windup"' in args,
          "serverargs defines --no-body-attack-activation-windup")
    check("if a.no_body_attack_activation_windup:\n"
          "        global BODY_ATTACK_ACTIVATION_WINDUP\n"
          "        BODY_ATTACK_ACTIVATION_WINDUP = False" in src,
          "main() flips BODY_ATTACK_ACTIVATION_WINDUP off under it")
    check("\nBODY_ATTACK_ACTIVATION_WINDUP = True\n" in src,
          "and the default is ON")

    def body_of(name):
        start = src.index(f"\ndef {name}(")
        end = src.index("\ndef ", start + 1)
        return src[start:end]
    for loop in ("enemy_attack_tick", "ally_cast_tick"):
        text = body_of(loop)
        check("body_attack_skill_clock(" in text and "else now + activation)" not in text,
              f"{loop} arms an attack skill's landing through body_attack_skill_clock, "
              f"never the raw activation")
    press = body_of("handle_skill_press") if "\ndef handle_skill_press(" in src else ""
    check(press and "UPSTREAM, no corpus cycle" not in press
          and "CASTAI-ZF16" in press,
          "the press handler's comment names the law OBSERVED (F51, ZF16), not UPSTREAM")


def section_vault():
    print("== 6. the vault: the witnesses and the carried rows ==")
    live = vaultpath.vault_path("captures", "live")
    dirs = [os.path.join(live, stamp) for stamp, _a in WITNESS]
    if not all(os.path.isdir(d) for d in dirs):
        LEDGER.skip("section 6 witnesses", "a witness capture directory is absent -- 1 check")
    else:
        import weaponcensus as wc                              # noqa: PLC0415
        got = {}
        for (stamp, agent), per in WITNESS.items():
            seen = {}
            for _name, _gf, s2c in wc.connections(stamp):
                for r in wc.skill_shots(s2c):
                    if r["agent"] == agent and not r["player"] and r["type"] == 5 \
                            and r["skill"] in per:
                        seen.setdefault(r["skill"], []).append(round(r["event_to_launch"], 4))
            got[(stamp, agent)] = {k: sorted(v) for k, v in seen.items()}
        check(got == WITNESS,
              "WITNESS is the captures' own: every body bow shot of 399 / 426 by agent 6 "
              "on 20260928T103123 and of 1197 by agent 28 on 20260819T132414, [50] -> "
              "0x00A4 to the tenth of a millisecond",
              f"{got}")
    path = vaultpath.vault_path("content", "skills.toml")
    if not os.path.isfile(path):
        LEDGER.skip("section 6 rows", "the vault's skills table is absent -- 1 check")
        return
    bad = {}
    for sid, row in RECORD.items():
        v = agents.WORLD.get("skills", sid)
        diff = {k: (x, v.get(k)) for k, x in row.items() if v.get(k) != x}
        if diff:
            bad[sid] = diff
    check(not bad, "the carried rows 394 / 399 / 426 / 1197 are the vault's own", str(bad))


WITNESS_OF = {sk: v for per in WITNESS.values() for sk, v in per.items()}


def main():
    section_clock()
    section_hostile()
    section_party()
    section_control()
    section_source()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
