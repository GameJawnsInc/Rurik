"""sandbox.py: the orchestrator's compiler, offline.

WHAT THIS IS REALLY CHECKING. The compiler stands between a window full of
spin boxes and a client launch, and every refusal it holds was paid for by a
run once: a definition worn by two templates puts one body in another's model
(area_population), a bar skill outside the character's professions is refused
by the client's own template rule, an agent id the errand rows already use
co-loads on the same process. So the fixture is a FAKE world with the smallest
tables that can express each of those, and each refusal is provoked on purpose
beside its accepting twin -- a gate that refuses the legitimate case too is an
outage, not a gate.

The geometry is ours and is checked as a set of invariants rather than against
a literal: every member on the floor, members of one group inside the first's
aggro of the player, no two groups inside each other's, the boss at the north
end. The overlay is checked the way it is used: parsed by tomllib, loaded by
toolkit/content.py from a temp directory, and every row must carry provenance.

No vault, no client, no server. Needs the repo's content only for one section
(the example spec against the tracked npc and item rows), and declares a skip
when even that is absent.
"""
import os
import re
import sys
import tempfile
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import checks   # noqa: E402
import content  # noqa: E402
import sandbox  # noqa: E402

led = checks.Ledger("sandbox", floor=158)     # 88 from the green run 2026-09-20; +19 SANDBOX-B7 (2026-09-22); +2 SKILLS-LT sec.5, the hand / label split (2026-09-23); +2 the fix pass (one LABEL_TIER, gamesrv_args); +1 budget_for_level (2026-09-24); +4 a hostile's ranks checked (2026-09-24); +7 the pre-merge pass: a hostile's level range, the no-level fallback told from 2 and 20, no npc rows (2026-09-24); +4 hostiles exempt from the budget, the owner's ruling: two budget refusals inverted, three kept rules and a hero's budget as controls, the no-level fallback re-witnessed on spawn_rows and validate's level range (2026-09-24); +2 the verifier's fixes: a malformed pair and an id outside the table on a hostile, the two kept rules with no hostile witness (2026-09-24); +10 the hostile caps lifted, the owner's ruling: rank 13 and 21 accepted, 22 refused, a level-255 hostile accepted and 24 too, 256 refused, the player's and a hero's rank 13 and level 21 refused (four controls that did not exist), HOSTILE_LEVEL_MAX tied to 0x0056's byte in the schema and to the codec's raise, a definition per (template, level) with its ids in range (2026-09-24); +1 the lift's verifier's fix: one member past both caps refused for both (`if tmpl:`, the elif hid the rank reason) (2026-09-24); +10 SANDBOX-N1 sec. 6: the rank a hostile's skill acts at (effective_rank, skill_attribute, UNRANKED_SKILL_RANK) and the text locks to authsrv.py (2026-09-24); +6 the repair (2026-09-24): a hostile's nine skills refused, skill_varies twice, spawn_rows' [] -> None, the locks re-pointed at the create path's fallback and agent_attributes' contiguous block (+2 net); +2 the heroless party (2026-09-25): a heroless spec's overlay loads with `heroes = []`, and a hero's overlay writes none


# ---------------------------------------------------------------- the fixture

class FakeWorld:
    def __init__(self, tables):
        self.tables = tables

    def rows(self, kind):
        return self.tables.get(kind, {})

    def get(self, kind, key):
        return self.tables[kind][key]


def skill(profession, activation=1.0, recharge=4):
    return {"profession": profession, "activation": activation, "recharge": recharge}


# The real s_attribPoints (attribpoints.py, build 38797): 97 points to reach 12.
COSTS = {str(r): {"points": p} for r, p in
         zip(range(1, 13), (1, 2, 3, 4, 5, 6, 7, 9, 11, 13, 16, 20))}
ATTRS = {"13": {"profession": 3, "is_primary": False},   # Healing Prayers
         "14": {"profession": 3, "is_primary": False},   # Smiting
         "15": {"profession": 3, "is_primary": False},   # Protection
         "16": {"profession": 3, "is_primary": True},    # Divine Favor
         "17": {"profession": 1, "is_primary": True},    # Strength
         "19": {"profession": 1, "is_primary": False},   # Hammer
         "20": {"profession": 1, "is_primary": False},   # Swordsmanship
         "21": {"profession": 1, "is_primary": False}}   # Tactics
WORLD = FakeWorld({
    "skills": {"1": skill(1, 2.0, 4), "2": dict(skill(0, 3.0, 20), attribute=51),
               "322": dict(skill(1, 0.0, 3), attribute=17),
               "382": skill(1, 0.0, 6), "281": dict(skill(3, 1.0, 8), attribute=13),
               "276": skill(3, 0.75, 2),
               "252": skill(3, 1.0, 10), "323": dict(skill(1, 0.0, 6), attribute=21),
               "170": skill(6, 2.0, 5),
               # three NO-attribute rows whose progression pairs vary (skill_varies):
               # Elementalist, as 170 is, so the Warrior/Monk unlock sets below stay
               "9001": dict(skill(6, 1.0, 5), attribute=51, scale0=55, scale15=80),
               "9002": dict(skill(6, 1.0, 5), attribute=51, bonus_scale0=1, bonus_scale15=3),
               "9003": dict(skill(6, 1.0, 5), attribute=51, duration0=5, duration15=10),
               "9004": dict(skill(6, 1.0, 5), attribute=51, scale0=7, scale15=7)},
    "skill_effect": {"1": {}, "281": {}, "322": {}},
    "npc": {"bandit_raider": {"name": "Bandit Raider", "profession": 1, "level": 2,
                              "file_id": 141267, "model_id": 116647},
            "academy_monk": {"name": "Academy Monk", "profession": 3, "level": 5,
                             "file_id": 116225, "model_id": 116741},
            "hatcher": {"name": "Hatcher [Collector]", "profession": 3, "level": 1,
                        "file_id": 116228, "model_id": 116703},
            "def_1442": {"profession": 1, "level": 2, "file_id": 116366},
            "lakeside_worm": {"profession": 1, "level": 1, "file_id": 116366,
                              "model_id": 1}},
    "item": {"starter_sword": {"item_type": 27}, "starter_shield": {"item_type": 24},
             "starter_hammer": {"item_type": 15}, "caster_staff": {"item_type": 26}},
    "weapon_type": {"sword": {"item_type": 27, "attribute": 20, "rate": "sword"},
                    "hammer": {"item_type": 15, "attribute": 19, "rate": "hammer"},
                    "staff": {"item_type": 26, "rate": "staff"}},
    "attack_speed": {"rates": {"sword": 1.33, "hammer": 1.75, "staff": 1.75,
                               "daggers": 1.33, "shortbow": 2.025}},
    "attribute_cost": COSTS, "attribute": ATTRS,
})


def spec(**over):
    s = sandbox.example_spec()
    s.update(over)
    return s


def problems(s):
    return sandbox.validate(s, WORLD)


def refuses(s, fragment):
    ps = problems(s)
    hit = [p for p in ps if fragment in p]
    return bool(hit), (hit[0] if hit else ("; ".join(ps) or "accepted"))


# ---------------------------------------------------------------- 0. arithmetic

led.ok([sandbox.points_for_level(l) for l in (1, 2, 3, 10, 15, 20)]
       == [0, 5, 10, 45, 95, 170],
       "points_for_level reproduces the four points the party rows cite (5 at 2, "
       "10 at 3, 45 at 10, 170 at 20) and 0 at level 1")
try:
    sandbox.points_for_level(21)
    led.ok(False, "level 21 is refused")
except ValueError:
    led.ok(True, "level 21 is refused (1..20)")
led.ok([sandbox.budget_for_level(l) for l in (0, 1, 2, 20, 21)] == [0, 0, 5, 170, 0],
       "budget_for_level is the compiler's rule for the player and a hero (a hostile is exempt, "
       "the owner's ruling 2026-09-24): points_for_level inside 1..20 and 0 outside, raising "
       "nowhere a spin can reach")

# ---------------------------------------------------------------- 1. geometry
pos = sandbox.group_positions(3, [2, 2, 1], 2)
led.ok(len(pos) == 5, "three groups of 2 + 2 + 1 give five positions", pos)
led.ok(all(sandbox.FLOOR_X[0] < x < sandbox.FLOOR_X[1] and
           sandbox.FLOOR_Y[0] < y < sandbox.FLOOR_Y[1] for x, y in pos),
       "every member stands inside the corridor's floor")
led.ok(pos[4] == (sandbox.CENTRE_X, sandbox.BOSS_Y),
       "the lone boss stands at the group's centre at the north end", pos[4])
led.ok(abs(pos[0][1] - 3900.0) < 1e-6 + 50 and abs(pos[2][1] - 7150.0) < 1e-6 + 50,
       "two groups before the boss sit near y 3900 and 7150 -- within a few hundred "
       "units of the slice's hand-placed 4600 and 7600", (pos[0], pos[2]))
d01 = ((pos[0][0] - pos[1][0]) ** 2 + (pos[0][1] - pos[1][1]) ** 2) ** 0.5
led.ok(abs(d01 - 480.4) < 1.0,
       "members of one group stand 480 u apart -- the slice's raider/monk spacing, "
       "inside the first's 1012 u aggro so the group pulls together", f"{d01:.1f}")
pos4 = sandbox.group_positions(4, [4, 4, 4, 4], 3)
gaps = [pos4[(g + 1) * 4][1] - pos4[g * 4][1] for g in range(3)]
led.ok(all(gap > 2 * sandbox.AGGRO_RANGE for gap in gaps),
       "four groups of four: consecutive groups are more than twice the aggro "
       "range apart, so no group is inside another's", [round(g) for g in gaps])
led.ok(all(sandbox.FLOOR_X[0] < x < sandbox.FLOOR_X[1] and
           sandbox.FLOOR_Y[0] < y < sandbox.FLOOR_Y[1] for x, y in pos4),
       "and all sixteen are on the floor")
within = []
for g in range(4):
    grp = pos4[g * 4:(g + 1) * 4]
    within.append(max(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                      for a in grp for b in grp))
led.ok(max(within) < sandbox.AGGRO_RANGE,
       "the widest pair inside any group is inside one aggro range",
       [round(w) for w in within])
led.ok(sandbox.group_positions(1, [1], 0) == [(sandbox.CENTRE_X, sandbox.BOSS_Y)],
       "one group is the boss's, at the north end")
try:
    sandbox.group_positions(0, [], 0)
    led.ok(False, "zero groups refused")
except ValueError:
    led.ok(True, "zero groups is refused")

# ---------------------------------------------------------------- 2. the example compiles
S = spec()
led.ok(problems(S) == [], "the example spec (the slice) validates", problems(S))
rows = sandbox.spawn_rows(S, WORLD)
led.ok([k for k, _ in rows] == ["sandbox_g1_m1", "sandbox_g1_m2", "sandbox_g2_m1",
                                "sandbox_g2_m2", "corridor_boss"],
       "five spawn rows, the boss keyed corridor_boss so [quest.rurik_bandits]'s "
       "kill objective binds it", [k for k, _ in rows])
led.ok([r["agent_id"] for _, r in rows] == [110, 111, 112, 113, 114],
       "agent ids run from 110", [r["agent_id"] for _, r in rows])
led.ok([r["definition"] for _, r in rows] == [60, 61, 60, 61, 60],
       "one definition per (template, level) -- raider 60, monk 61, every member at level 2 -- "
       "shared by rows naming the same body at one level: retail's own shape",
       [r["definition"] for _, r in rows])
led.ok(sandbox.check_population(rows) == [], "the set checks pass")
boss = dict(rows[4][1])
led.ok(boss["glow"] == 5 and boss["max_health"] == 160 and boss["group"] == "g3",
       "the boss carries its glow (SLICE-F2's 5), its health and its group")
led.ok(rows[0][1]["skills"] == [[322, 0.0, 3.0]] and
       rows[1][1]["skills"] == [[281, 1.0, 8.0], [252, 1.0, 10.0], [276, 0.75, 2.0]],
       "a member's bar is [[id, activation, recharge]] from the table -- the "
       "shape spawn_population reads", rows[1][1]["skills"])
led.ok(rows[0][1]["attack_speed"] == 1.75 and rows[0][1]["weapon_item"] == "starter_hammer",
       "the raider swings its hammer at the hammer rate")
led.ok(rows[1][1]["attack_speed"] is None and rows[1][1].get("weapon_item") is None,
       "the monk names no weapon item and no rate (the server's default applies)")
led.ok(all(r["area"] == "sandbox" and r["map"] == 168 and r["allegiance"] == "hostile"
           and r["attacks_back"] and r["enabled"] for _, r in rows),
       "every row is a hostile on the corridor's map in area 'sandbox'")

prow = sandbox.party_row(S, WORLD)
led.ok(prow["player_profession"] == 1 and prow.get("player_secondary") is None,
       "a Warrior with no secondary writes no player_secondary")
led.ok((prow["player_level"], prow["player_health"], prow["player_points"]) == (3, 140, 10),
       "level 3: health 140 (WIKI 100 + 20/level), 10 points (WIKI)",
       (prow["player_level"], prow["player_health"], prow["player_points"]))
led.ok((prow["player_energy"], prow["player_pips"]) == (20, 2),
       "a Warrior's 20 energy at 2 pips (the WIKI-recalled table)")
led.ok(prow["player_weapon"] == "starter_sword" and prow["player_offhand"] == "starter_shield",
       "the sword and shield")
led.ok(prow.get("player_armour") is None, "no armour row for a Warrior (the fixture's)")
led.ok(len(prow["heroes"]) == 1 and prow["hero"] == [3] and prow["body"] == "academy_monk",
       "one hero; the single-hero fields carry it for a server that predates the list")
h = prow["heroes"][0]
led.ok((h["profession"], h["level"], h["health"], h["energy"], h["weapon"]) == (3, 3, 140, 30, "staff"),
       "the Monk hero: profession 3, level 3, 140 health, 30 energy, a staff", h)
led.ok(h["damage"] == [3, 5] and h["weapon_attribute"] == 13 and h["armor"] == 25.0,
       "a caster hero swings the Holy Rod's 3-5 at its first listed attribute (13) "
       "with the starter armour rating", (h["damage"], h["weapon_attribute"], h["armor"]))

args = sandbox.game_args(S, WORLD)
led.ok(args[:6] == ["--map", "148", "--party", "sandbox", "--area", "errand,sandbox"],
       "the gamesrv flags: the town, the party row, the errand + sandbox populations",
       args[:6])
led.ok("--spawn-profession" in args and args[args.index("--spawn-profession") + 1] == "1"
       and "--spawn-secondary" not in args,
       "the primary is passed for the roster (runargs forwards it); no secondary flag")
unl = args[args.index("--unlocks") + 1].split(",")
led.ok(set(unl) == {"1", "2", "322", "382", "323", "281", "276", "252",
                    "384", "385", "346", "380"},
       "--unlocks is every Warrior and Monk skill of the table plus the common one, "
       "the heroes' profession counted (the hero library is own + ACCOUNT), plus the "
       "bar's own ids whether or not the table knows them (an unbacked bar skill "
       "asserts GmSkSlot.cpp:206 on a drag)", unl)
led.ok("170" not in unl, "and no Elementalist skill")

cmd = sandbox.launch_command(args, r"X:\run\slice\Gw.exe")
led.ok(cmd[0] == sys.executable and cmd[2].endswith("session.py") and "--replace" in cmd
       and "--keep-open" in cmd and "--hold" not in cmd
       and cmd[cmd.index("--exe") + 1] == r"X:\run\slice\Gw.exe"
       and cmd[-2] == "--game-args" and cmd[-1] == " ".join(args),
       "the harness command: session.py --replace --keep-open, held until the client "
       "closes, --game-args as ONE argument", cmd)
led.ok("--hold" in sandbox.launch_command(args, "x", hold=90),
       "a hold, when asked for")

with tempfile.TemporaryDirectory() as tmp:
    compiled = sandbox.compile_spec(S, WORLD, tmp, exe=r"X:\Gw.exe", dat=r"X:\Gw.dat")
    led.ok(compiled["env"] == {"RURIK_DAT": r"X:\Gw.dat",
                               "RURIK_CONTENT_EXTRA": os.path.join(tmp, "slice")},
           "the environment: the archive and the overlay directory", compiled["env"])
    path = sandbox.write_overlay(compiled)
    led.ok(os.path.isfile(path) and path.endswith("world.toml"),
           "the overlay is written under <out>/<name>/world.toml", path)
    parsed = tomllib.loads(compiled["overlay"])
    led.ok(set(parsed) == {"party", "spawn"}, "the overlay parses: party and spawn tables",
           sorted(parsed))
    led.ok(len(parsed["party"]["sandbox"]["heroes"]) == 1 and
           parsed["party"]["sandbox"]["heroes"][0]["hero"] == 3,
           "[[party.sandbox.heroes]] carries the hero")
    world2 = content.load(repo_dir=tmp, vault_dir="", overrides_dir=os.path.join(tmp, "none"),
                          extra_dirs=[compiled["overlay_dir"]])
    led.ok(world2.get("party", "sandbox")["player_level"] == 3 and
           world2.get("spawn", "corridor_boss")["glow"] == 5,
           "content.load takes the overlay as an EXTRA dir -- the row the server reads")
    led.ok(all(world2.get("spawn", k).provenance.get("source") == "invented"
               for k, _ in rows),
           "every generated row carries invented provenance")
    with_env = content.load(repo_dir=tmp, vault_dir="", overrides_dir=os.path.join(tmp, "none"),
                            extra_dirs=content.extra_dirs_from_env(
                                {"RURIK_CONTENT_EXTRA": compiled["overlay_dir"]}))
    led.ok(with_env.get("party", "sandbox")["hero"] == [3],
           "and RURIK_CONTENT_EXTRA is the same door, read by extra_dirs_from_env")
    led.ok(content.extra_dirs_from_env({}) == [] and
           content.extra_dirs_from_env({"RURIK_CONTENT_EXTRA": ""}) == [],
           "unset or empty means no extra dir -- the old load, byte for byte")
    two = content.extra_dirs_from_env({"RURIK_CONTENT_EXTRA": os.pathsep.join(["a", "b"])})
    led.ok(two == ["a", "b"], "several directories split on os.pathsep")
    lines = sandbox.summary(compiled)
    led.ok(any("corridor_boss" in ln and "BOSS" in ln for ln in lines) and
           any("player: W/-" in ln for ln in lines),
           "the summary names the boss and the player's pair")

# THE HEROLESS PARTY (harness 20260925T161150). TOML has no empty
# array-of-tables: zero [[party.sandbox.heroes]] headers wrote no `heroes` key,
# and the gamesrv read the row as the single-hero shape and died on `hero`. The
# party_row check in sec. 3 read the dict, which had `heroes = []` all along --
# the list was lost in overlay_text, between the dict and the file, so this
# reads the FILE the way the server does. (main()'s side: test_partyrow.py.)
with tempfile.TemporaryDirectory() as tmp:
    bare = sandbox.compile_spec(spec(name="heroless", heroes=[]), WORLD, tmp,
                                exe=r"X:\Gw.exe", dat=r"X:\Gw.dat", store={})
    sandbox.write_overlay(bare)
    w0 = content.load(repo_dir=tmp, vault_dir="", overrides_dir=os.path.join(tmp, "none"),
                      extra_dirs=[bare["overlay_dir"]])
    row0 = w0.get("party", "sandbox")
    led.ok(row0.get("heroes") == [] and "hero" not in row0
           and "[[party.sandbox.heroes]]" not in bare["overlay"],
           "a heroless spec's overlay loads through content.py with `heroes = []` and no "
           "single-hero field -- the SANDBOX-B3 empty list the gamesrv reads as the "
           "player alone", sorted(row0))
led.ok(sandbox.overlay_text(S, WORLD).count("heroes = []") == 0,
       "...and its twin: a party with a hero writes no `heroes = []` beside its "
       "[[party.sandbox.heroes]] table (TOML would refuse the key twice)")

# ---------------------------------------------------------------- 3. refusals, each beside its twin
ok, why = refuses(spec(player=dict(S["player"], skills=[281])), "belongs to profession 3")
led.ok(ok, "a Monk skill on a Warrior with no secondary is REFUSED (the client's "
           "template rule)", why)
led.ok(problems(spec(player=dict(S["player"], secondary=3, skills=[281]))) == [],
       "...and accepted once Monk is the secondary")
ok, why = refuses(spec(player=dict(S["player"], secondary=1)), "equals the primary")
led.ok(ok, "secondary == primary is refused (GmDeckBuilder:2321)", why)
ok, why = refuses(spec(player=dict(S["player"], profession=11)), "not 1..10")
led.ok(ok, "profession 11 is refused", why)
ok, why = refuses(spec(player=dict(S["player"], skills=list(range(1, 10)))), "the bar is 8 wide")
led.ok(ok, "nine bar skills are refused", why)
# ...and on a HOSTILE (the verifiers' a3/c1, 2026-09-24): the gamesrv round-robins
# over the whole list and the window holds eight, so a ninth was dropped on
# Open with 'Opened X' alone; eight, and eight with a 0 (an empty slot), pass
_raider9 = dict(S["groups"][0]["members"][0], skills=list(range(1, 10)))
_raider8 = dict(S["groups"][0]["members"][0], skills=[322, 0, 323, 1, 2, 382, 0, 380])
ok, why = refuses(spec(groups=[{"members": [_raider9]}] + S["groups"][1:]), "the bar is 8 wide")
led.ok(ok and why == "group 1 member 1: 9 skills; the bar is 8 wide"
       and not [q for q in problems(spec(groups=[{"members": [_raider8]}] + S["groups"][1:]))
                if "the bar is" in q],
       "nine skills on a HOSTILE are refused naming the member and the count, as the "
       "player's and a hero's are; eight with a 0 inside (an empty slot) pass", why)
ok, why = refuses(spec(player=dict(S["player"], attributes=[[20, 12], [17, 12]])), "spend")
led.ok(ok, "ranks a level-3 character cannot pay for are refused (194 of 10)", why)
ok, why = refuses(spec(player=dict(S["player"], attributes=[[13, 1]])), "belongs to profession 3")
led.ok(ok, "a Monk attribute on a W/- is refused", why)
ok, why = refuses(spec(player=dict(S["player"], secondary=3, attributes=[[16, 1]])),
                  "PRIMARY attribute")
led.ok(ok, "Divine Favor (Monk's primary) on a W/Mo is refused -- spendable only as a "
           "primary", why)
led.ok(problems(spec(player=dict(S["player"], secondary=3, attributes=[[13, 1]]))) == [],
       "...but Healing Prayers on a W/Mo is accepted")
ok, why = refuses(spec(player=dict(S["player"], weapon="excalibur")), "not a content item")
led.ok(ok, "an unknown weapon is refused", why)

hero = S["heroes"][0]
ok, why = refuses(spec(heroes=[dict(hero, hero=i) for i in range(1, 9)]), "cap is 7")
led.ok(ok, "eight heroes are refused (the client's cap)", why)
led.ok(problems(spec(heroes=[dict(hero, hero=i) for i in range(1, 8)])) == [],
       "...seven are accepted")
ok, why = refuses(spec(heroes=[hero, dict(hero)]), "used twice")
led.ok(ok, "one catalogue index twice is refused", why)
ok, why = refuses(spec(heroes=[dict(hero, hero=40)]), "not 1..39")
led.ok(ok, "index 40 is refused (HEROES == 40, row 0 unused)", why)
ok, why = refuses(spec(heroes=[dict(hero, body="nobody")]), "not an npc template")
led.ok(ok, "a body the content lacks is refused", why)
ok, why = refuses(spec(heroes=[dict(hero, skills=[322])]), "not a Monk skill")
led.ok(ok, "a Warrior skill on a Monk hero is refused", why)
led.ok(problems(spec(heroes=[dict(hero, profession=1, skills=[322],
                                  attributes=[[17, 2], [20, 1]])])) == [],
       "...and accepted when the hero is declared a Warrior in the same body "
       "(SANDBOX-U3: the profession is the row's, the body cosmetic)")
ok, why = refuses(spec(heroes=[dict(hero, weapon="lance")]), "not an [attack_speed.rates] key")
led.ok(ok, "a weapon key the rates table lacks is refused", why)
warrior_hero = {k: v for k, v in hero.items() if k != "weapon"}
warrior_hero.update(profession=1, body="hatcher", skills=[322],
                    attributes=[[17, 2], [20, 1]])
hp = sandbox.party_row(spec(heroes=[warrior_hero]), WORLD)["heroes"][0]
led.ok(hp["weapon"] == "sword" and hp["weapon_attribute"] == 20 and hp["damage"] is None,
       "a Warrior hero with no weapon named defaults to a sword, Swordsmanship as its "
       "weapon attribute, and no damage row (the held item's range)", hp)
hp2 = sandbox.party_row(spec(heroes=[dict(warrior_hero, weapon="staff")]), WORLD)["heroes"][0]
led.ok(hp2["weapon"] == "staff" and hp2["damage"] == [3, 5] and hp2["weapon_attribute"] == 17,
       "...and a spec that names a staff for it gets the staff, the Holy Rod's range "
       "and its first attribute -- the spec wins over the profession default", hp2)

groups = S["groups"]
raider = groups[0]["members"][0]
ok, why = refuses(spec(groups=[{"members": [dict(raider)] * 5}] + groups[1:]), "the most is 4")
led.ok(ok, "five members in a group are refused", why)
led.ok(problems(spec(groups=[{"members": [dict(raider)] * 4}] + groups[1:])) == [],
       "...four are accepted")
ok, why = refuses(spec(groups=[{"members": [dict(raider)]}] * 5), "the corridor holds 4")
led.ok(ok, "five groups are refused", why)
# a hostile is EXEMPT from the point budget -- the owner's ruling (2026-09-24,
# PLAN-LOG): retail foes and bosses exceed a player's. Its ranks are still
# held to VALIDITY (a real attribute of the template's profession, each rank
# 0..HOSTILE_RANK_MAX), and the player's and a hero's ranks keep their budget.
# (For one day validate refused a hostile past its budget, as the window's
# hint had promised; these two checks are that rule's, inverted.)
hot = dict(raider, attributes=[[17, 12], [19, 12], [20, 12], [21, 12]])
ps = problems(spec(groups=[{"members": [hot]}] + groups[1:]))
led.ok(ps == [], "a hostile's ranks past its level's budget are ACCEPTED (388 points at level "
                 "2, where a player has 5) -- a hostile is exempt, the owner's ruling", ps)
ps = problems(spec(groups=[{"members": [dict(raider, level=0, attributes=[[17, 1]])]}]
                   + groups[1:]))
led.ok(ps == [], "a level-0 hostile with a rank is accepted (no budget to be 0)", ps)
led.ok(problems(spec(groups=[{"members": [dict(raider, level=0, attributes=None)]}]
                     + groups[1:])) == [],
       "...and with none it is accepted (content rows default to level 0)")
# ...the KEPT rules, on a hostile: validity, which the owner did not rule on
ok, why = refuses(spec(groups=[{"members": [dict(raider, attributes=[[13, 1]])]}] + groups[1:]),
                  "attribute 13 belongs to profession 3, not to [1]")
led.ok(ok, "a Monk attribute on a Warrior hostile is still refused (the template's profession)",
       why)
# ...the rank cap LIFTED for a hostile -- the owner's second ruling of the day,
# "lift the rank and level caps for hostiles too": 0..HOSTILE_RANK_MAX (21,
# retail's ceiling: foes' attributes reach 20, +1 from skills; the client is
# witnessed at an NPC rank of 15 and our formulas hold to 21). This check read
# "rank 13 ... is outside 0..12" for a hostile until then, and is inverted
ps = problems(spec(groups=[{"members": [dict(raider, attributes=[[17, 13], [20, 21]])]}]
                   + groups[1:]))
led.ok(ps == [] and sandbox.HOSTILE_RANK_MAX == 21,
       "a hostile's rank 13 (past the cost table's 12) and rank 21 (HOSTILE_RANK_MAX) are "
       "ACCEPTED -- the caps lifted for a hostile, the owner's ruling", ps)
ok, why = refuses(spec(groups=[{"members": [dict(raider, attributes=[[17, 22]])]}] + groups[1:]),
                  "rank 22 on 17 is outside 0..21")
led.ok(ok, "...and rank 22 on a hostile is refused past HOSTILE_RANK_MAX (21), named in the "
           "reason", why)
# ...the PLAYER's and a HERO's ranks keep the table's 12 (0x003A / 0x003B carry
# theirs; the client asserts at CharData.cpp(202) on a base rank >= 13) -- the
# controls the lift needs, since _check_ranks serves all three roles and a
# naive bump of one shared ceiling would have lifted theirs unseen
ok, why = refuses(spec(player=dict(S["player"], level=20, attributes=[[20, 13]])),
                  "player.attributes: rank 13 on 20 is outside 0..12")
led.ok(ok, "the PLAYER's rank 13 is still refused past the table's 12 (at level 20, where the "
           "budget alone would not refuse it)", why)
ok, why = refuses(spec(heroes=[dict(hero, level=20, attributes=[[13, 13]])]),
                  "hero 1.attributes: rank 13 on 13 is outside 0..12")
led.ok(ok, "...and a HERO's rank 13 is still refused past the table's 12 (at level 20)", why)
ok, why = refuses(spec(groups=[{"members": [dict(raider, attributes=[[17, 1], [17, 2]])]}]
                       + groups[1:]), "attribute 17 twice")
led.ok(ok, "one attribute twice on a hostile is still refused", why)
# ...the two kept rules that had no hostile witness (the verifier's plants
# skipped each for a hostile alone and nothing went red): a pair that is not
# [attribute, rank], and an id the table lacks
ok, why = refuses(spec(groups=[{"members": [dict(raider, attributes=[["x", 1]])]}] + groups[1:]),
                  "is not [attribute, rank]")
led.ok(ok, "a malformed pair on a hostile is still refused (['x', 1] is not [attribute, rank])",
       why)
ok, why = refuses(spec(groups=[{"members": [dict(raider, attributes=[[99, 1]])]}] + groups[1:]),
                  "99 is not an attribute id")
led.ok(ok, "an id outside the table on a hostile is still refused (99 is not an attribute id)",
       why)
# ...and the budget itself, still the player's (sec. 3's 194-of-10 above) and a hero's
ok, why = refuses(spec(heroes=[dict(hero, attributes=[[13, 12], [14, 12]])]),
                  "hero 1.attributes spend 194 points; level 3 has 10")
led.ok(ok, "a hero's ranks past its level's budget are still refused (194 of 10 at level 3)", why)
# a member with no level is at its TEMPLATE's, where spawn_rows and validate
# both read it (the window's old constant 2 opened a level-10 template at 2).
# Three templates at 2, 5 and 1 tell the fallback from 0, from 2 and from 20
nolevel = [{k: v for k, v in m.items() if k != "level"}
           for m in (raider, groups[0]["members"][1],
                     {"npc": "hatcher", "health": 120, "skills": [281], "attributes": [[13, 1]]})]
led.ok([r["level"] for _, r in sandbox.spawn_rows(spec(groups=[{"members": nolevel}]
                                                        + groups[1:]), WORLD)][:3] == [2, 5, 1],
       "a member with no level spawns at its TEMPLATE's level -- the raider's 2, the monk's 5, "
       "the hatcher's 1 -- not at 0, at the window's old 2, or at 20",
       [r["level"] for _, r in sandbox.spawn_rows(spec(groups=[{"members": nolevel}]
                                                        + groups[1:]), WORLD)][:3])
# ...and validate reads the same level: a template past the cap fails a member
# with no level for ITS level, and a member's own level wins over it. The cap
# is HOSTILE_LEVEL_MAX (255, the wire's byte -- the owner's ruling of
# 2026-09-24 lifted it from the player's 20), so the template is planted one
# past it, where 24 stood
past = sandbox.HOSTILE_LEVEL_MAX + 1
elder = FakeWorld(dict(WORLD.tables, npc=dict(WORLD.tables["npc"],
                                              elder={"profession": 1, "level": past,
                                                     "file_id": 116366, "model_id": 1})))
ps = sandbox.validate(spec(groups=[{"members": [{"npc": "elder", "health": 120}]}] + groups[1:]),
                      elder)
led.ok(ps == [f"group 1 member 1: level {past} is outside 0..255"] and past == 256,
       "a member with no level on a level-256 template is refused for the TEMPLATE's level (the "
       "fallback validate reads)", ps)
ps = sandbox.validate(spec(groups=[{"members": [{"npc": "elder", "health": 120, "level": 3}]}]
                           + groups[1:]), elder)
led.ok(ps == [], "...and its own level 3 wins over the template's 256", ps)
# a hostile past HOSTILE_LEVEL_MAX is refused for its LEVEL, the reason the
# window acts on (its spin clamps 256 to 255), never for its ranks ('level 24
# has 0' once pointed the operator at ranks it may keep)
for m, tag in ((dict(raider, level=256), "with its 5 points"),
               (dict(raider, level=256, attributes=None), "with no ranks")):
    ps = problems(spec(groups=[{"members": [m]}] + groups[1:]))
    led.ok(ps == ["group 1 member 1: level 256 is outside 0..255"],
           f"a level-256 hostile {tag} is refused for its level, the one reason, never 'has 0'", ps)
led.ok(problems(spec(groups=[{"members": [dict(raider, level=255)]}] + groups[1:])) == [],
       "...and at 255, the cap (the 0x0056 level byte's last value), the raider's 5 points are "
       "accepted")
led.ok(problems(spec(groups=[{"members": [dict(raider, level=24)]}] + groups[1:])) == [],
       "...and at 24 -- refused as 'outside 0..20' until the ruling; the highest level on the "
       "owner's retail tapes -- it is accepted")
ok, why = refuses(spec(groups=[{"members": [dict(raider, level=-1)]}] + groups[1:]),
                  "level -1 is outside 0..255")
led.ok(ok, "...a level below 0 is refused by the same rule, the reason naming 0..255", why)
# ...and a member past BOTH caps is refused for both: the ranks are checked
# whether or not the level passed (`if tmpl:`, not `elif`). The elif was the
# budget's -- a level past the cap priced the ranks at 0 and 'level 24 has 0'
# named the wrong fault -- and with no budget it only hid the rank reason: a
# level-300 member with a rank of 22 was refused for the level alone, and the
# window clamped both and said '1 change' (the verifier's plant, 2026-09-24)
ps = problems(spec(groups=[{"members": [dict(raider, level=300, attributes=[[17, 22]])]}]
                   + groups[1:]))
led.ok(ps == ["group 1 member 1: level 300 is outside 0..255",
              "group 1 member 1.attributes: rank 22 on 17 is outside 0..21"],
       "ONE member at level 300 with a rank of 22 is refused for BOTH, the level first (the "
       "elif hid the rank behind the level)", ps)
# ...the PLAYER's and a HERO's level keep 1..20 (points_for_level's table ends
# there, and 0x003A / 0x003B carry their ranks): the controls the lift needs,
# since sandbox.LEVEL_MAX served all three roles and a naive bump would have
# lifted theirs -- no check ran validate on a player or hero at 21 before this
ok, why = refuses(spec(player=dict(S["player"], level=21)), "player.level 21 is outside 1..20")
led.ok(ok, "the PLAYER at level 21 is still refused (1..20)", why)
ok, why = refuses(spec(heroes=[dict(hero, level=21)]), "hero 1: level 21 is outside 1..20")
led.ok(ok, "...and a HERO at level 21 is still refused (1..20)", why)
# HOSTILE_LEVEL_MAX is the WIRE, tied to it here so the constant cannot drift
# from the schema: GAME_SMSG 0x0056's level field (the eighth after the header:
# def, file, 0, scale, 0, flags, profession, LEVEL, name) is a `byte` in
# schema/overrides.json, and the codec that builds the frame encodes the cap
# and raises one past it -- the raise that would drop a live connection
# mid-population, which is why validate refuses first
import json
with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "schema", "overrides.json"),
          encoding="utf-8") as fh:
    _fields = json.load(fh)["channels"]["GAME_SMSG"]["86"]["fields"]
_payload = [f["type"] for f in _fields if f["type"] != "msg_header"]
led.ok(_payload[7] == "byte" and sandbox.HOSTILE_LEVEL_MAX == (1 << 8) - 1 == 255,
       "HOSTILE_LEVEL_MAX is the width of 0x0056's level field in the schema: a byte, so 255",
       (_payload, sandbox.HOSTILE_LEVEL_MAX))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import codec    # noqa: E402  (toolkit/schema/codec.py)
import agents   # noqa: E402  (toolkit/authsrv/agents.py, on sandbox's path)
_codec = codec.Codec()
_npc = {"file_id": 1, "scale": 0x64000000, "flags": 0x20C, "profession": 1, "enc_name": "脁"}
_at_cap = _codec.encode("GAME_SMSG", 0x0056,
                        agents.npc_properties(60, dict(_npc, level=sandbox.HOSTILE_LEVEL_MAX)))
try:
    _codec.encode("GAME_SMSG", 0x0056,
                  agents.npc_properties(60, dict(_npc, level=sandbox.HOSTILE_LEVEL_MAX + 1)))
    _past = "encoded"
except Exception as exc:                        # noqa: BLE001
    _past = type(exc).__name__
led.ok(_at_cap[2 + 6 * 4 + 1] == 255 and _past == "error",
       "...and the codec packs a level-255 0x0056 with the byte in place and raises struct.error "
       "one past it (the drop validate exists to prevent)", (_at_cap[2 + 6 * 4 + 1], _past))
# a world with attribute tables and no npc rows: no template to check the
# ranks in, so they are unchecked, as the rest of validate treats an empty
# npc table (in profession 0 every rank read 'belongs to ..., not to []')
bare = FakeWorld(dict(WORLD.tables, npc={}))
led.ok(not [q for q in sandbox.validate(spec(groups=[{"members": [dict(raider)]}] + groups[1:]),
                                        bare) if ".attributes" in q],
       "with no npc rows a hostile's ranks are unchecked, not refused as another profession's")
ok, why = refuses(spec(groups=groups[:2]), "0 bosses")
led.ok(ok, "no boss is refused (the quest binds one kill)", why)
ok, why = refuses(spec(groups=[groups[2], groups[0]]), "must be the LAST")
led.ok(ok, "a boss not in the last group is refused", why)
ok, why = refuses(spec(groups=[groups[2], groups[2]]), "2 bosses")
led.ok(ok, "two bosses are refused", why)
glowy = sandbox.spawn_rows(spec(groups=[{"members": [dict(raider, glow=7),
                                                     dict(raider, boss=True)]}]), WORLD)
led.ok("glow" not in glowy[1][1] and glowy[0][1]["glow"] == sandbox.DEFAULT_GLOW,
       "a glow on a non-boss is dropped -- only the boss glows, and the boss with none "
       "named gets the default", [(k, r.get("glow")) for k, r in glowy])
ok, why = refuses(spec(groups=[{"members": [dict(raider, boss=True, glow=11)]}]), "outside 0..10")
led.ok(ok, "a boss glow past 10 is refused (ConstGlow.cpp:42)", why)
ok, why = refuses(spec(groups=[{"members": [dict(raider, npc="def_1442")]}] + groups[1:]),
                  "has no body")
led.ok(ok, "a template with no model_id is refused as a body", why)
ok, why = refuses(spec(groups=[{"members": [dict(raider, weapon_item="club")]}] + groups[1:]),
                  "not a content item")
led.ok(ok, "an unknown weapon item is refused", why)
ok, why = refuses(spec(groups=[]), "at least the boss")
led.ok(ok, "no groups is refused", why)

# The population set checks, provoked directly.
bad = [("a", {"agent_id": 110, "definition": 60, "npc": "x"}),
       ("b", {"agent_id": 110, "definition": 60, "npc": "y"}),
       ("c", {"agent_id": 99, "definition": 50, "npc": "x"})]
ps = sandbox.check_population(bad)
led.ok(any("share agent_id 110" in p for p in ps) and
       any("share definition 60" in p for p in ps) and
       any("reserved agent_id 99" in p for p in ps) and
       any("reserved definition 50" in p for p in ps),
       "check_population names a shared agent id, a definition worn by two templates, "
       "and the errand rows' reserved ids", ps)
four = spec(groups=[{"members": [dict(raider), dict(raider), dict(raider),
                                 dict(groups[0]["members"][1])]}] * 3 + [groups[2]])
rows4 = sandbox.spawn_rows(four, WORLD)
led.ok(len(rows4) == 13 and sandbox.check_population(rows4) == [] and
       max(r["agent_id"] for _, r in rows4) == 122 and
       {r["definition"] for _, r in rows4} == {60, 61},
       "twelve hostiles and a boss: ids 110..122, two definitions, no collision")
led.ok(rows4[-1][0] == "corridor_boss" and rows4[-1][1]["y"] == sandbox.BOSS_Y,
       "the boss is still last and still at the north end")
# a definition per (template, LEVEL): 0x0056 carries the level inside the
# definition and is re-sent on every create, so one slot for an L3 and an L24
# raider held whichever was declared last (OBSERVED on the server's sends) and
# the client would show one level for both (RECONSTRUCTION, unverified on the
# client -- sandbox's IDS paragraph; retail declares each definition once per
# connection, 2,748 of 2,748 on the owner's tapes; a slot per level is
# RECONSTRUCTION, 2026-09-24)
lv = sandbox.spawn_rows(spec(groups=[{"members": [dict(raider, level=3), dict(raider, level=24),
                                                  dict(raider, level=3)]}] + groups[1:]), WORLD)
lvd = [(r["level"], r["definition"]) for _, r in lv[:3]]
led.ok(lvd[0][1] != lvd[1][1] and lvd[0][0] == 3 and lvd[1][0] == 24,
       "two members of one template at L3 and L24 get TWO definitions, each carrying its own "
       "level (one slot showed the last-declared level for both)", lvd)
led.ok(lvd[0][1] == lvd[2][1] and sandbox.check_population(lv) == []
       and all(sandbox.DEFINITION_FIRST <= r["definition"] < sandbox.DEFINITION_FIRST + 16
               and r["definition"] not in sandbox.RESERVED_DEFINITIONS for _, r in lv),
       "...two at one level share one, and every definition sits in 60..75, clear of the reserves "
       "(check_population clean)", [r["definition"] for _, r in lv])

bossy = spec(groups=[{"members": [dict(raider), dict(raider, boss=True), dict(raider)]}])
rb = sandbox.spawn_rows(bossy, WORLD)
led.ok(rb[0][0] == "corridor_boss" and rb[0][1]["x"] == sandbox.CENTRE_X,
       "inside its group the boss is ordered first and takes the centre", [k for k, _ in rb])

sec = spec(player=dict(S["player"], secondary=3))
led.ok(sandbox.party_row(sec, WORLD)["player_secondary"] == 3 and
       "--spawn-secondary" in sandbox.game_args(sec, WORLD),
       "a secondary is written to the row and passed as --spawn-secondary")
led.ok(sandbox.party_row(spec(heroes=[]), WORLD)["heroes"] == [] and
       "hero" not in sandbox.party_row(spec(heroes=[]), WORLD),
       "no heroes: an empty list and no single-hero fields")
sin = spec(player=dict(S["player"], profession=7, weapon=None, offhand=None))
sin["player"].pop("weapon"); sin["player"].pop("offhand")
sin["player"]["attributes"] = []
pr = sandbox.party_row(sin, WORLD)
led.ok(pr["player_weapon"] == "starter_daggers" and pr["player_offhand"] is None and
       pr["player_armour"] == sandbox.PLAYER_ARMOUR_BY_PROFESSION[7] and
       (pr["player_energy"], pr["player_pips"]) == (25, 4),
       "an Assassin defaults to daggers, the Assassin armour and 25 energy at 4 pips "
       "(OBSERVED on the owner's wire)", pr)

with tempfile.TemporaryDirectory() as tmp:
    try:
        sandbox.compile_spec(spec(groups=[]), WORLD, tmp, exe="x", dat="y")
        led.ok(False, "compile_spec refuses a bad spec")
    except sandbox.SpecError as exc:
        led.ok("at least the boss" in str(exc), "compile_spec raises SpecError listing "
               "the problems", str(exc)[:80])

# ---------------------------------------------------------------- 3b. SANDBOX-B7: the in-game panels own the bars and ranks
bare = spec(player={"profession": 3, "secondary": 1, "level": 5},
            heroes=[{"hero": 6, "profession": 1, "body": "bandit_raider", "level": 4}])
led.ok(problems(bare) == [], "a spec with no bars and no ranks anywhere validates", problems(bare))
brow = sandbox.party_row(bare, WORLD)
led.ok(brow["player_skills"] == [] and brow["player_attributes"] == [] and
       brow["player_points"] == 20,
       "the character's bar and ranks are written EMPTY (an answer, not an absence) with the "
       "level's whole budget unspent -- the in-game panels fill them", brow)
bh = brow["heroes"][0]
led.ok(bh["skills"] == [] and bh["attributes"] == [] and bh["points"] == 15,
       "a hero row carries an empty bar, no ranks and `points` = its level's budget (15 at "
       "level 4), so its panel's plus buttons are live", bh)
bargs = sandbox.game_args(bare, WORLD)
led.ok("--persist" in bargs,
       "--persist is always passed: the store keeps what the panels set")
led.ok("--persist" not in sandbox.game_args(dict(bare, persist=False), WORLD),
       "...unless the spec says persist = false")
led.ok(set(sandbox.unlocks_for(bare, WORLD)) == {"1", "2", "322", "382", "323", "281", "276", "252"}
       or set(sandbox.unlocks_for(bare, WORLD)) == {1, 2, 322, 382, 323, 281, 276, 252},
       "with no unlocks named the account library is the party's professions' skills",
       sandbox.unlocks_for(bare, WORLD))
led.ok(sandbox.unlocks_for(dict(bare, unlocks=[170, 1]), WORLD) == [1, 170],
       "a top-level `unlocks` (the Skills tab) is the account library verbatim, whatever "
       "the professions -- account-wide means account-wide")
led.ok(sandbox.unlocks_for(dict(bare, player=dict(bare["player"], skills=[281, 322]),
                                unlocks=[1]), WORLD) == [1, 281, 322],
       "...plus any bar id the spec still names")
led.ok(sandbox.party_professions(bare, WORLD) == {1, 3},
       "party_professions: the pair and the heroes'")
txt = sandbox.spec_toml(dict(bare, unlocks=[1, 2]))
led.ok(tomllib.loads(txt)["unlocks"] == [1, 2] and "skills" not in tomllib.loads(txt)["player"],
       "spec_toml writes a top-level unlocks and no bar keys the spec lacks")

# the store: read, warned about, reset -- on a temp file, never the vault's
with tempfile.TemporaryDirectory() as tmp:
    import json
    stpath = os.path.join(tmp, "loopback_rurik.invalid.json")
    with open(stpath, "w", encoding="utf-8") as fh:
        json.dump({"email": "loopback@rurik.invalid", "version": 1,
                   "account": {"factions": {}},
                   "characters": {"1111": {"name": "Test Warrior", "level": 3,
                                           "skillbar": [382, 170, 0, 0, 0, 0, 0, 0],
                                           "attributes": [[13, 2], [17, 1]],
                                           "heroes": {"3": {"skillbar": [281, 0, 0, 0, 0, 0, 0, 0],
                                                            "attributes": [[13, 1]],
                                                            "attribute_points": 10}}}}}, fh)
    real_path = sandbox.store_path
    sandbox.store_path = lambda email=None: stpath
    try:
        st = sandbox.store_state()
        led.ok(st and st["characters"]["Test Warrior"]["skillbar"][:2] == [382, 170]
               and st["characters"]["Test Warrior"]["heroes"][3]["attribute_points"] == 10
               and st["account_unlocked"] is None,
               "store_state reads the character's bar, ranks and hero rows, and an absent "
               "account library as None", st)
        warn = sandbox.store_warnings(spec(unlocks=[382, 281]), WORLD, st)
        led.ok(any("[170]" in w and "outside this run's unlocks" in w for w in warn),
               "a stored bar skill outside the unlocks is warned about (it asserts on a drag)",
               warn)
        led.ok(any("[170]" in w and "profession this character is not" in w for w in warn),
               "...and one of a profession the character is not")
        led.ok(any("attributes [13]" in w for w in warn),
               "a stored rank in another profession's attribute is warned about")
        led.ok(any("hero 3 keeps its stored bar [281]" in w for w in warn),
               "a party hero's stored bar is said to win over the spec")
        led.ok(sandbox.store_warnings(spec(), WORLD, None) == [],
               "no store, no warnings")
        c = sandbox.compile_spec(spec(unlocks=[382]), WORLD, tmp, exe="x", dat="y", store=st)
        led.ok(c["store_warnings"] and any("STORE:" in ln for ln in sandbox.summary(c)),
               "compile_spec carries the store's warnings into the summary")
        led.ok(sandbox.compile_spec(spec(), WORLD, tmp, exe="x", dat="y", store={})["store_warnings"] == [],
               "...and an empty store passed in means none")
        removed = sandbox.reset_store()
        led.ok(removed == stpath and not os.path.exists(stpath) and sandbox.reset_store() is None,
               "reset_store removes the file once and answers None the second time")
    finally:
        sandbox.store_path = real_path

# ---------------------------------------------------------------- 4. the example against the TRACKED rows
try:
    real = content.load(vault_dir="")
except content.ContentError as exc:
    real = None
    led.skip("4. the example against the tracked rows", str(exc))
if real is not None:
    ps = sandbox.validate(sandbox.example_spec(), real)
    led.ok(ps == [], "the example spec validates against the repo's own npc and item "
                     "rows (skills and ranks unchecked without the vault)", ps)
    txt = sandbox.overlay_text(sandbox.example_spec(), real)
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "o.toml"), "w", encoding="utf-8") as fh:
            fh.write(txt)
        merged = content.load(extra_dirs=[tmp], vault_dir="")
    led.ok(merged.get("spawn", "corridor_boss")["area"] == "sandbox" and
           merged.get("spawn", "corridor_raider_a")["area"] == "corridor",
           "merged over the tree, the overlay's corridor_boss REPLACES the slice's (same "
           "key, area 'sandbox') and the slice's other rows keep area 'corridor' -- so "
           "--area errand,sandbox serves the sandbox and the stock corridor stays unserved")
    ex = sandbox.example_toml()
    led.ok(tomllib.loads(ex)["groups"][2]["members"][0]["boss"] is True,
           "--example prints TOML that parses back with the boss marked")

# ---------------------------------------------------------------- 5. SKILLS-LT: hand rows and label rows are two grades
# A generated `tier = "label"` skill_effect row (skilldesc.py --emit-labels)
# acts, but through a parsed label; the Skills tab must say "label-only", never
# "modelled" (deskwork D4 step 4's fidelity condition).
TIERED = FakeWorld({"skill_effect": {"1": {}, "281": {}, "322": {"scale_means": "+ Damage"},
                                     "784": {"scale_means": "Poison", "tier": "label"},
                                     "187": {"scale_means": "Fire damage", "tier": "label"}}})
led.ok(sandbox.modelled_skills(TIERED) == [1, 281, 322] and sandbox.label_skills(TIERED) == [187, 784],
       "modelled_skills is the HAND rows only; label_skills the label tier -- disjoint, both sorted",
       (sandbox.modelled_skills(TIERED), sandbox.label_skills(TIERED)))
led.ok(sandbox.skill_tiers(TIERED) == {1: "hand", 281: "hand", 322: "hand", 784: "label", 187: "label"}
       and sandbox.modelled_skills(WORLD) == [1, 281, 322] and sandbox.label_skills(WORLD) == [],
       "skill_tiers names each row's grade; a world with no label rows has the old modelled set and "
       "an empty label set")
led.ok(sandbox.LABEL_TIER is content.LABEL_TIER,
       "one definition of the tier string: sandbox reads content.LABEL_TIER (ENG-11)")
_ctl = sandbox.game_args({"player": {"profession": 1}, "gamesrv_args": ["--no-skill-labels"]}, WORLD)
_plain = sandbox.game_args({"player": {"profession": 1}}, WORLD)
led.ok(_ctl[-1] == "--no-skill-labels" and _ctl[:-1] == _plain and "--no-skill-labels" not in _plain,
       "gamesrv_args passes a flag through to the gamesrv, LAST -- the label tier's control arm "
       "(skills 55.5's runsheet: --no-skill-labels) -- and adds nothing by default (ENG-8)",
       (_ctl, _plain))

# ---------------------------------------------------------------- 6. SANDBOX-N1: the rank a hostile's skill ACTS at
# The orchestrator's Skill bar says the number the server will use, so the
# rule is mirrored here in stdlib and TEXT-LOCKED to the server: read as text,
# not imported (authsrv.py binds content at import). Without the lock the
# window's "12" would be a number our own tool produced.
led.ok(sandbox.effective_rank([], [], 17) == 12 == sandbox.UNRANKED_SKILL_RANK,
       "a hostile with no ranks of its own and none on its template acts at UNRANKED_SKILL_RANK, 12")
led.ok(sandbox.effective_rank([[19, 2]], [], 17) == 0,
       "...with ANY rank set, an attribute the ranks omit acts at 0 (Hammer Mastery ranked, "
       "Strength forgotten: Power Attack drops from 12 to 0)")
led.ok(sandbox.effective_rank([[17, 4], [19, 2]], [], 17) == 4,
       "...and a ranked attribute acts at its rank")
led.ok(sandbox.effective_rank([], [[17, 3]], 17) == 3
       and sandbox.effective_rank([], [[19, 3]], 17) == 0,
       "a member with no ranks takes its TEMPLATE's (agent_attributes' fallback), 0 for one "
       "the template omits")
led.ok(sandbox.effective_rank([[19, 1]], [[17, 3]], 17) == 0
       and sandbox.effective_rank({19: 1}, None, 19) == 1
       and sandbox.effective_rank(None, {"17": 5}, 17) == 5,
       "the member's ranks win over the template's when it has any, and both shapes "
       "agent_attributes reads ([[a, r]] and {a: r}) are read here")
led.ok(sandbox.skill_attribute(WORLD, 322) == 17 and sandbox.skill_attribute(WORLD, 281) == 13,
       "skill_attribute reads the row's attribute (Power Attack 17, Orison 13)")
led.ok(sandbox.skill_attribute(WORLD, 2) is None and sandbox.skill_attribute(WORLD, 382) is None
       and sandbox.skill_attribute(WORLD, 99999) is None and sandbox.NO_ATTRIBUTE == 51,
       "...and None for a no-attribute row (51, the table's own value), a row with no key, "
       "and an id with no row")
# a NO-attribute skill can still VARY with a rank (Light of Deldrimor 2212: Holy
# damage 55..80, attribute 51; four acting rows in the table), and the server
# scales it at the rank agent_skill_rank gives -- 0 while any rank is set, 12
# with none -- so the window's cell shows that rank, never 'nothing scales'
# (the verifier's a2, 2026-09-24)
led.ok([sandbox.skill_varies(WORLD, s) for s in (9001, 9002, 9003)] == [True] * 3
       and sandbox.SKILL_SCALE_PAIRS == ("scale", "bonus_scale", "duration"),
       "skill_varies is True for a no-attribute row whose scale, bonus_scale or duration pair "
       "differs at rank 0 and 15 (one row each)")
led.ok([sandbox.skill_varies(WORLD, s) for s in (9004, 2, 382, 99999)] == [False] * 4
       and sandbox.effective_rank([[19, 2]], [], sandbox.NO_ATTRIBUTE) == 0
       and sandbox.effective_rank([], [], sandbox.NO_ATTRIBUTE) == 12,
       "...and False for a flat pair, a row with none of the six keys, a row with no key at "
       "all and an id with no row; and effective_rank at NO_ATTRIBUTE is 0 with any rank set, "
       "12 with none (what the server passes such a skill)")
# spawn_rows writes a member's EMPTY ranks as None: the step that makes the
# create path's `or` fall to the template exactly where effective_rank does
# (the verifier's b6, 2026-09-24) -- a member with none, one with [], one with
# ranks, side by side
_r3 = sandbox.spawn_rows(spec(groups=[{"members": [dict(S["groups"][0]["members"][0], attributes=None),
                                                   dict(S["groups"][0]["members"][0], attributes=[]),
                                                   dict(S["groups"][0]["members"][0])]}]
                              + S["groups"][1:]), WORLD)
led.ok([r["attributes"] for _k, r in _r3[:3]] == [None, None, [[19, 2], [17, 1], [21, 1]]],
       "spawn_rows writes None for a member with no ranks AND for one with [] (so the create "
       "path's `or` and agent_attributes' `is None` fall to the template alike), and a member's "
       "own pairs verbatim", [r["attributes"] for _k, r in _r3[:3]])
_authsrv = os.path.join(os.path.dirname(HERE), "authsrv", "authsrv.py")
with open(_authsrv, encoding="utf-8") as fh:
    _src = fh.read()
_m = re.search(r"^ENEMY_SKILL_RANK = (\d+)$", _src, re.M)
led.ok(_m is not None and int(_m.group(1)) == sandbox.UNRANKED_SKILL_RANK,
       "UNRANKED_SKILL_RANK is authsrv.ENEMY_SKILL_RANK, read out of authsrv.py as text "
       "(one choice, said twice)", _m.group(0) if _m else "no ENEMY_SKILL_RANK line")


def _body(name):
    m = re.search(rf"^def {name}\(.*?(?=^def |\Z)", _src, re.M | re.S)
    return m.group(0) if m else ""


_attrs, _rank, _pairs = _body("agent_attributes"), _body("agent_skill_rank"), _body("rank_pairs")
# the CONTIGUOUS block, not three lines found anywhere in the body: a fallback
# kept on its line but made dead (`if ranks is None and False:`) passed a lock
# that looked for each line alone (the verifier's b6, 2026-09-24)
led.ok('    ranks = agent.get("attributes")\n    if ranks is None:\n'
       '        ranks = (agent.get("npc") or {}).get("attributes")\n'
       '    return rank_pairs(ranks)\n' in _attrs,
       "agent_attributes still reads the spawn row's ranks, else the template's, through "
       "rank_pairs -- the contiguous block, locked to the source")
led.ok("    if not pairs:\n        return {}\n" in _pairs
       and "pairs.items() if isinstance(pairs, dict) else pairs" in _pairs,
       "rank_pairs still answers {} for none and reads BOTH shapes ([[a, r]] and {a: r}), "
       "the two shapes effective_rank reads")
# the OPERATIVE fallback for an area body is the CREATE PATH's, not
# agent_attributes' (an area entry is always a dict, so `is None` never runs
# there): the row's ranks, else its template's, through rank_pairs -- exactly
# once in the source. Dropping `or npc.get("attributes")` there left
# test_sandbox green while a member with no ranks acted at 12 on a template
# with ranks (the verifier's a1 plant, 2026-09-24)
_create = 'rank_pairs(row.get("attributes") or npc.get("attributes"))'
led.ok(_src.count(_create) == 1,
       "the area create path reads the spawn row's ranks, else its npc template's, through "
       "rank_pairs (the operative fallback for every body this compiler emits; effective_rank's "
       "`or` mirrors it), locked to the source", _src.count(_create))
led.ok("if not ranks:\n        return ENEMY_SKILL_RANK" in _rank
       and 'return ranks.get(int(row.get("attribute", -1)), 0)' in _rank,
       "agent_skill_rank still acts at ENEMY_SKILL_RANK with no ranks and at "
       "ranks.get(attribute, 0) with any (the two lines the window's cell text rests on)")

sys.exit(led.verdict())
