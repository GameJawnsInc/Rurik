r"""SANDBOX-B2: the run orchestrator's compiler -- a run SPEC in; a content
overlay, the gamesrv flags and the harness command out.

    python toolkit/harness/sandbox.py --example                  # the slice, as a spec
    python toolkit/harness/sandbox.py --spec my.toml             # compile and print
    python toolkit/harness/sandbox.py --spec my.toml --write     # ...and write vault/sandbox/<name>/
    python toolkit/harness/sandbox.py --spec my.toml --launch    # ...and run it

WHAT A SPEC IS. One TOML file naming the PLAYER (profession pair, level, bar,
unlocks, weapon), the HEROES (up to seven, each its own catalogue index, body,
profession, bar, level and ranks) and the GROUPS (up to four, up to four hostiles
each, exactly one of them the boss). `--example` prints the vertical slice written
that way -- `[party.slice]` and the five `[spawn.corridor_*]` rows of
content/world.toml, spelled as a spec -- so the empty window starts from a run
that is known to play.

WHAT COMES OUT, and why each half goes where it goes:

  * an OVERLAY, one TOML file with a `[party.sandbox]` row (plus one
    `[[party.sandbox.heroes]]` table per hero) and one `[spawn.sandbox_*]` row per
    hostile, `area = "sandbox"`, on the corridor's map. It is written under
    vault/sandbox/<name>/ and handed to the server through RURIK_CONTENT_EXTRA
    (content.py, SANDBOX-B1), so it is merged over the tree for THIS launch and
    no other. Every row says `source = "invented"` and names the spec, because a
    generated row is a claim like any other and the reader of a gamesrv log
    deserves to know where it came from.
  * the GAMESRV FLAGS the existing server already takes: `--party sandbox`
    (SLICE-H2), `--area errand,sandbox` (SLICE-B8: the town's quest giver and
    the corridor's population on one process), `--unlocks <ids>` (the account
    library, 0x001D), `--spawn-profession` and `--spawn-secondary` (the roster
    on the auth channel must agree with the avatar, runargs.spawn_profession_args).
  * the HARNESS COMMAND: session.py on the slice archive's run directory, with
    RURIK_DAT pointing the server at the same Gw.dat the client draws (the
    corridor exists only there, compose.toml [compose.slice]).

THE GEOMETRY IS OURS, said once here. The corridor is 32 x 128 cells, floor x
768..2304 and y 384..11904, the player arriving at (1536, 1536) at the south
end and leaving by the portal 736 u behind that point (content/areas.toml,
content/world.toml). Groups sit on the long axis, evenly spaced from y 3900 to
the boss at 10400 -- the slice's own hand-placed rows are at 4600 / 7600 / 10400
and this reproduces them within a few hundred units for two groups and a boss.
Members stand 470 u apart inside a group (the slice's raider and monk), which is
inside the first member's 1012 u aggro of the player (AGGRO_RANGE, WIKI and
OBSERVED n=1), so a group pulls together; groups are never nearer than 2,100 u,
so no group is inside another's aggro when the player reaches it.

IDS. Agent ids run from 110 and definitions from 60, one definition per
(template, LEVEL) -- a definition is a raw array index on the client and two
rows sharing one must name the same body (area_population); and since GAME_SMSG
0x0056 carries the level inside the definition and is re-sent on every create,
two members of one template at different levels sharing a slot would overwrite
each other's byte (OBSERVED: the server re-sends the definition per create), and
the client would then show one level for both -- RECONSTRUCTION, UNVERIFIED on
the client: the recon read the definition-slot getter, and that a body's
displayed level (AvChar +0x110) is copied from the slot at create is inferred,
not witnessed (retail declares each definition exactly once per connection:
2,748 of 2,748 on the owner's tapes; a slot per level is our RECONSTRUCTION of
how retail would carry two levels of one body, 2026-09-24). Members of one
template at one level still share a slot. At most sixteen members, so
definitions 60..75; both ranges are clear of the errand rows the same process
serves (agents 98 / 99, definitions 50 / 51) and of the party's reserve
(player 1, henchman 30, heroes 200..206, definitions 9..16), which
area_population refuses at startup rather than at the fourth body.

WHAT THIS MODULE REFUSES, before a client is launched, because each of these
was found by a run once: a bar skill outside the character's own professions
(the client's own template rule, skilltemplate.validate); a hero body the
content does not know; a fifth member or a fifth group; an eighth hero (the
client's cap, PtPlayer:332); a boss that is not in the last group, or two of
them, or none (the quest's kill objective binds ONE spawn key); ranks the
player's or a hero's level cannot pay for (a hostile is exempt, the owner's
ruling 2026-09-24 -- retail foes and bosses exceed a player's budget; its ranks
are held to validity alone); a hostile rank outside 0..HOSTILE_RANK_MAX (21) or
a hostile level outside 0..HOSTILE_LEVEL_MAX (255) -- the owner's second ruling
the same day, "lift the rank and level caps for hostiles too", the ceilings
being where the wire and our formulas stop carrying the number (the constants
say which); a weapon key the rates table lacks. The player's and a hero's level
1..20 and ranks 0..12 stay: 0x003A / 0x003B carry theirs and the client asserts
at CharData.cpp(202) on a base rank of 13 or more.

Standard library only. Loads content through toolkit/content.py; runs nothing
unless --launch.
"""
import argparse
import os
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (TOOLKIT, os.path.join(TOOLKIT, "authsrv")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import content      # noqa: E402  (toolkit/content.py)
import vaultpath    # noqa: E402
import attribspend  # noqa: E402  (toolkit/authsrv/attribspend.py, a leaf)
import morale       # noqa: E402  (toolkit/authsrv/morale.py, base_health)


class SpecError(Exception):
    """A spec this compiler will not turn into a run. The message lists WHY,
    every reason at once, so one fix does not reveal the next."""


# ---------------------------------------------------------------- the labels
# Profession names are the game's public nouns and stand as LABELS (PLAN.md
# section 7 Q17: a short proper noun used as a label is not authored text).
PROFESSIONS = {1: "Warrior", 2: "Ranger", 3: "Monk", 4: "Necromancer",
               5: "Mesmer", 6: "Elementalist", 7: "Assassin", 8: "Ritualist",
               9: "Paragon", 10: "Dervish"}
ABBREV = {1: "W", 2: "R", 3: "Mo", 4: "N", 5: "Me", 6: "E", 7: "A", 8: "Rt",
          9: "P", 10: "D"}

# Base energy and pips per profession. WIKI (GWW "Energy"), and READ FROM
# MEMORY on 2026-09-20 for every row but two: the Assassin's 25 / 4 is
# OBSERVED on the owner's own wire ([party.daggers20]'s note, pools.py on
# 20260817T183756) and 25 / 3 is a Ranger's on retail's wire ([player.defaults]'s
# note, moralescan.py --pips). Until the page is read back these are DEFAULTS
# the window shows and the operator may change, not facts this repo asserts.
ENERGY_BY_PROFESSION = {1: (20, 2), 2: (25, 3), 3: (30, 4), 4: (30, 4),
                        5: (30, 4), 6: (30, 4), 7: (25, 4), 8: (30, 4),
                        9: (25, 3), 10: (25, 4)}

# What each profession holds by default: the content item keys the player's
# hands take (WEAPONS-W1) and the attack_speed rates key a party body swings at
# (SLICE-H4's PARTY_WEAPON_BY_PROFESSION). A Warrior's sword and shield are the
# slice's own (SLICE-H9).
PLAYER_ITEMS_BY_PROFESSION = {
    1: ("starter_sword", "starter_shield"), 2: ("starter_bow", None),
    3: ("caster_staff", None), 4: ("caster_staff", None),
    5: ("caster_staff", None), 6: ("caster_staff", None),
    7: ("starter_daggers", None), 8: ("caster_staff", None),
    9: ("starter_spear", "starter_shield"), 10: ("starter_scythe", None)}
HERO_WEAPON_BY_PROFESSION = {1: "sword", 2: "shortbow", 3: "staff", 4: "staff",
                             5: "staff", 6: "staff", 7: "daggers", 8: "staff",
                             9: "spear", 10: "scythe"}
# The five armour keys in STARTER_ARMOUR's slot order, where a set exists. The
# Warrior fixture is worn when a row says nothing; the Assassin set is DAGGERS's.
PLAYER_ARMOUR_BY_PROFESSION = {
    7: ["assassin_body", "assassin_boots", "assassin_legs", "assassin_gloves",
        "assassin_head"]}
# The Starter Holy Rod's 3-5 (WIKI, GWW "Starter Holy Rod"), the slice hero's
# swing (SLICE-H8): a caster hero's damage when the spec gives none.
CASTER_DAMAGE = (3, 5)
CASTER_WEAPONS = {"staff", "wand"}
HERO_ARMOR_DEFAULT = 25.0     # a starter set's rating; the slice's, OURS (SLICE-H8)

# ---------------------------------------------------------------- the bounds
HEROES_MAX = 7                # PtPlayer:332 / GmHeroCommander:214, both cmp 7
HERO_INDEX_MAX = 39           # s_heroClientData is 40 rows, row 0 HERO_UNUSED
GROUPS_MAX = 4
GROUP_SIZE_MAX = 4
BAR_SLOTS = 8
LEVEL_MAX = 20                # the PLAYER's and a HERO's (points_for_level's table
                              # ends there; 0x003A / 0x003B carry their ranks and the
                              # client asserts at CharData.cpp(202) on a base rank
                              # >= 13). NOT a hostile's: the two constants below are.
# A HOSTILE's level: the owner's ruling, 2026-09-24 ("lift the rank and level
# caps for hostiles too"). 255 is the WIRE -- GAME_SMSG 0x0056's level field is
# a `byte` (schema/overrides.json "86"; test_sandbox ties this constant to that
# width), and our codec raises struct.error at 256 or -1 inside send(), which
# drops the connection mid-population; the client's displayed level is a u8
# store too (AvChar +0x110, movzx at 0x007DF7D2, build 38797). OBSERVED /
# MEASURED, the recon of 2026-09-24. Retail's tapes show hostiles 0..20
# (non-combatants 24); armour (3L + bonus) and the strike level (3L)
# extrapolate linearly past 20 with no crash -- the operator's to use.
HOSTILE_LEVEL_MAX = 255
# A HOSTILE's rank: 21 is where retail and our own formulas agree. WIKI (GWW,
# "Attribute" §Notes, rev. 2026-09-02, revid 2739369; the owner's reading,
# 2026-09-24): "Attributes are capped at rank 20, the maximum that can be
# reached through runes and skill effects", and items with a 20% chance of +1
# can pass that cap -- so 21. Player-visible, the wiki's strong kind (it was
# first cited here from search summaries of talk / template pages, which said
# the same: foes up to 20, +1 from skills). And MEASURED on
# our side: the client is witnessed handling an NPC rank of 15 (0x0042 field 3,
# Windborne Speed on map 280), every server consumer carries 0..21 without a
# raise, and past 22.5 our formulas go wrong (Frenzy, 346, turns from double
# damage into damage reduction; strength penetration hits 100 % at 100). The
# player's and a hero's ranks keep rules.rank_max (12, the cost table's last
# row): the client asserts past it.
HOSTILE_RANK_MAX = 21
GLOW_MAX = 10                 # ConstGlow.cpp(42): the client asserts past it
DEFAULT_GLOW = 5              # SLICE-F2's red, the slice boss's own

# ---------------------------------------------------------------- the world
TOWN_MAP = 148                # Ascalon City: the errand's giver, the west portal
CORRIDOR_MAP = 168            # [area.corridor], explorable, in the slice archive
FLOOR_X = (768.0, 2304.0)
FLOOR_Y = (384.0, 11904.0)
CENTRE_X = 1536.0
FIRST_GROUP_Y = 3900.0
BOSS_Y = 10400.0
MEMBER_OFFSETS = ((-235.0, -50.0), (235.0, 50.0), (-235.0, 250.0), (235.0, -250.0))
BOSS_OFFSETS = ((0.0, 0.0), (-300.0, -140.0), (300.0, -140.0), (0.0, 280.0))
AGGRO_RANGE = 1012.0          # authsrv.AGGRO_RANGE: WIKI 1012, OBSERVED n=1
AGENT_ID_FIRST = 110
DEFINITION_FIRST = 60
RESERVED_AGENTS = frozenset({1, 30, 98, 99} | set(range(200, 207)))
RESERVED_DEFINITIONS = frozenset({9, 50, 51} | set(range(10, 17)))
PARTY_KEY = "sandbox"
AREA_KEY = "sandbox"
TOWN_AREA = "errand"
BOSS_SPAWN_KEY = "corridor_boss"   # [quest.rurik_bandits].objective_kill binds it
RUN_DIR = "slice"                  # vault/run/slice: the archive the corridor is in


# ---------------------------------------------------------------- arithmetic

def points_for_level(level):
    """Attribute points a character of `level` has to spend.

    WIKI (GWW "Attribute point"): 5 a level from 2 to 10, then 10 a level to 15,
    then 15 a level to 20 -- 5 at 2, 10 at 3, 45 at 10, 95 at 15, 170 at 20,
    and 200 only with the two attribute quests, which this sandbox does not
    grant. The four points the party rows already cite (5, 10, 45, 170) are
    reproduced by the rule, which is the check a rule can offer.
    """
    level = int(level)
    if not 1 <= level <= LEVEL_MAX:
        raise ValueError(f"level {level} is outside 1..{LEVEL_MAX}")
    return sum(5 if lv <= 10 else 10 if lv <= 15 else 15
               for lv in range(2, level + 1))


def budget_for_level(level):
    """The points the PLAYER and a HERO of `level` may spend: points_for_level
    inside 1..LEVEL_MAX and 0 outside it -- the compiler's own rule
    (_check_ranks, with a level). A HOSTILE is exempt, the owner's ruling
    (2026-09-24, PLAN-LOG): retail foes and bosses exceed a player's budget,
    so a member's ranks are checked for validity (_check_ranks with no level)
    and never for points -- the window's Attributes card counts what is spent
    and reads no budget. Total outside 1..20 so a caller may pass a level the
    window's spin offers (0) without a raise."""
    level = int(level)
    return points_for_level(level) if 1 <= level <= LEVEL_MAX else 0


def group_positions(n_groups, sizes, boss_group):
    """[(x, y)] per member, group by group, on the corridor's long axis.

    `sizes` is the member count per group, `boss_group` the index of the group
    that holds the boss (its first member is the boss and stands at the group's
    centre). Groups are evenly spaced from FIRST_GROUP_Y to BOSS_Y; a lone group
    IS the boss's and sits at BOSS_Y.
    """
    if n_groups < 1:
        raise ValueError("no groups")
    if n_groups == 1:
        centres = [BOSS_Y]
    else:
        step = (BOSS_Y - FIRST_GROUP_Y) / (n_groups - 1)
        centres = [FIRST_GROUP_Y + i * step for i in range(n_groups)]
    out = []
    for gi, size in enumerate(sizes):
        offsets = BOSS_OFFSETS if gi == boss_group else MEMBER_OFFSETS
        for mi in range(size):
            dx, dy = offsets[mi]
            out.append((CENTRE_X + dx, centres[gi] + dy))
    return out


def check_population(rows):
    """area_population's two set rules, offline: no agent id twice, and one
    definition never worn by two DIFFERENT templates; plus the reserves.
    Returns the problems (strings), empty when the set is sound."""
    problems, seen_agent, seen_def = [], {}, {}
    for key, row in rows:
        aid, d, npc = row["agent_id"], row["definition"], row["npc"]
        if aid in seen_agent:
            problems.append(f"{key} and {seen_agent[aid]} share agent_id {aid}")
        seen_agent[aid] = key
        if d in seen_def and seen_def[d][1] != npc:
            problems.append(f"{key} ({npc}) and {seen_def[d][0]} ({seen_def[d][1]}) "
                            f"share definition {d}")
        seen_def[d] = (key, npc)
        if aid in RESERVED_AGENTS:
            problems.append(f"{key} claims reserved agent_id {aid}")
        if d in RESERVED_DEFINITIONS:
            problems.append(f"{key} claims reserved definition {d}")
    return problems


# ---------------------------------------------------------------- content

def _rows(world, kind):
    try:
        return world.rows(kind)
    except Exception:                                    # noqa: BLE001
        return {}


def skill_row(world, sid):
    return _rows(world, "skills").get(str(int(sid)))


def has_skill_table(world):
    return bool(_rows(world, "skills"))


def skill_owned(world, sid, professions):
    """Is skill `sid` one of `professions`' own (or common, profession 0)?
    None when the table is absent -- unknown, not refused."""
    row = skill_row(world, sid)
    if row is None:
        return None
    return int(row.get("profession", 0)) in set(int(p) for p in professions) | {0}


def skill_triple(world, sid):
    """[id, activation, recharge] from the client's own table (the shape a
    spawn row's `skills` carries); zeros, when the table is absent, the way
    authsrv.skill_timing falls back."""
    row = skill_row(world, sid)
    if row is None:
        return [int(sid), 0.0, 0.0]
    return [int(sid), float(row.get("activation", 0.0)),
            float(row.get("recharge", 0))]


def default_unlocks(world, professions):
    """Every player-usable skill of these professions, plus the common ones."""
    want = set(int(p) for p in professions) | {0}
    return sorted(int(k) for k, r in _rows(world, "skills").items()
                  if int(r.get("profession", 0)) in want)


LABEL_TIER = content.LABEL_TIER    # one definition; `import content` is above


def skill_tiers(world):
    """{id: "hand" | "label"} for every [skill_effect.*] row: hand-verified, or
    generated from the client's description templates (SKILLS-LT, the tier
    field on the row)."""
    return {int(k): (LABEL_TIER if r.get("tier") == LABEL_TIER else "hand")
            for k, r in _rows(world, "skill_effect").items()}


def modelled_skills(world):
    """Ids with a HAND [skill_effect.*] row: the ones this server resolves beyond
    their icon from a hand-verified row (studies/skills). The label tier is
    `label_skills`: those act too, through a parsed label, and the grade must
    say so rather than read as modelled (deskwork D4 step 4's condition)."""
    return sorted(k for k, t in skill_tiers(world).items() if t == "hand")


def label_skills(world):
    """Ids whose only [skill_effect.*] row is a tier = "label" one (SKILLS-LT)."""
    return sorted(k for k, t in skill_tiers(world).items() if t == LABEL_TIER)


def templates(world):
    """[(key, name or None, profession, level, has_body)] -- every npc row.
    A row with a `name` was put on a nameplate by a client run (RUN-PARADE);
    one without is loadable but unwatched, and the window says so."""
    out = []
    for key, row in sorted(_rows(world, "npc").items()):
        out.append((str(key), row.get("name"), int(row.get("profession", 0) or 0),
                    int(row.get("level", 0) or 0), bool(row.get("model_id"))))
    return out


def hero_catalogue(vault_dir=None):
    """[(index, name_string_id)] from the vault's heroes.toml, or [] when the
    table has not been extracted (heroes_table.py --toml). Row 0 is left out:
    HERO_UNUSED, ChCliApi:4447."""
    try:
        path = os.path.join(vault_dir or vaultpath.vault_path("content"), "heroes.toml")
    except Exception:                                    # noqa: BLE001
        return []
    if not os.path.isfile(path):
        return []
    with open(path, "rb") as fh:
        table = tomllib.load(fh)
    return [(int(h["index"]), int(h["name_string_id"]))
            for h in table.get("hero", []) if int(h.get("index", 0)) != 0]


def attribute_rules(world):
    """attribspend.AttributeRules from the vault's two tables, or None."""
    costs = _rows(world, "attribute_cost")
    attrs = _rows(world, "attribute")
    if not costs or not attrs:
        return None
    return attribspend.AttributeRules(
        {int(k): int(r["points"]) for k, r in costs.items()},
        {int(k): {"profession": int(r["profession"]),
                  "is_primary": bool(r["is_primary"])} for k, r in attrs.items()})


def weapon_rate_for_item(world, item_key):
    """The attack_speed rate (seconds) of a content item, by its item_type's
    [weapon_type.*] row; None when unknown."""
    item = _rows(world, "item").get(item_key)
    if not item:
        return None
    for _k, wt in _rows(world, "weapon_type").items():
        if int(wt.get("item_type", -1)) == int(item.get("item_type", -2)):
            rates = (_rows(world, "attack_speed").get("rates") or {})
            r = rates.get(wt.get("rate"))
            return float(r) if r is not None else None
    return None


def weapon_attribute_for_key(world, rate_key):
    """[weapon_type.KEY].attribute, or None."""
    wt = _rows(world, "weapon_type").get(rate_key)
    return int(wt["attribute"]) if wt and wt.get("attribute") is not None else None


# ---------------------------------------------------------------- the example

def example_spec():
    """The vertical slice as a spec: [party.slice] and the corridor's five rows
    (content/world.toml, SLICE-H8 / H9 / H11), so the window's first run is
    the one the owner already played through."""
    raider = {"npc": "bandit_raider", "level": 2, "health": 120, "skills": [322],
              "attributes": [[19, 2], [17, 1], [21, 1]], "damage": [6, 10],
              "weapon_attribute": 19, "weapon_item": "starter_hammer",
              "attack_speed": 1.75}
    monk = {"npc": "academy_monk", "level": 2, "health": 120,
            "skills": [281, 252, 276], "attributes": [[13, 2], [14, 1], [15, 1]],
            "damage": [3, 5], "weapon_attribute": 14}
    boss = dict(raider, boss=True, health=160, skills=[322, 323], damage=[8, 14],
                glow=DEFAULT_GLOW)
    return {
        "name": "slice",
        "player": {"profession": 1, "secondary": 0, "level": 3,
                   "skills": [382, 384, 385, 322, 346, 1, 2, 380],
                   "attributes": [[20, 3], [17, 2], [21, 1]],
                   "weapon": "starter_sword", "offhand": "starter_shield"},
        "heroes": [{"hero": 3, "profession": 3, "body": "academy_monk",
                    "level": 3, "skills": [281, 276, 2],
                    "attributes": [[13, 3], [16, 2], [15, 1]], "weapon": "staff"}],
        "groups": [{"members": [dict(raider), dict(monk)]},
                   {"members": [dict(raider), dict(monk)]},
                   {"members": [boss]}],
    }


def load_spec(path):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------- validation

def _ints(seq):
    return [int(v) for v in (seq or ())]


def validate(spec, world):
    """Every reason this spec cannot run, as a list of strings. Empty = sound."""
    p = []
    player = spec.get("player") or {}
    heroes = list(spec.get("heroes") or [])
    groups = list(spec.get("groups") or [])
    rules = attribute_rules(world)
    npcs = _rows(world, "npc")
    items = _rows(world, "item")
    rates = (_rows(world, "attack_speed").get("rates") or {})

    # -- the player
    prim = int(player.get("profession", 1))
    sec = int(player.get("secondary", 0))
    if prim not in PROFESSIONS:
        p.append(f"player.profession {prim} is not 1..10")
    if sec and sec not in PROFESSIONS:
        p.append(f"player.secondary {sec} is not 0 (none) or 1..10")
    if sec and sec == prim:
        p.append(f"player.secondary {sec} equals the primary (GmDeckBuilder:2321)")
    level = int(player.get("level", 3))
    if not 1 <= level <= LEVEL_MAX:
        p.append(f"player.level {level} is outside 1..{LEVEL_MAX}")
    bar = _ints(player.get("skills"))
    if len(bar) > BAR_SLOTS:
        p.append(f"player.skills has {len(bar)} ids; the bar is {BAR_SLOTS} wide")
    for sid in bar:
        if sid and skill_owned(world, sid, (prim, sec)) is False:
            row = skill_row(world, sid)
            p.append(f"player.skills: skill {sid} belongs to profession "
                     f"{int(row.get('profession', 0))} "
                     f"({PROFESSIONS.get(int(row.get('profession', 0)), '?')}), "
                     f"not the character's {ABBREV.get(prim)}/"
                     f"{ABBREV.get(sec, '-')} -- the client's own template rule refuses it")
    for key, slot in ((player.get("weapon"), "weapon"), (player.get("offhand"), "offhand")):
        if key and items and key not in items:
            p.append(f"player.{slot} {key!r} is not a content item")
    _check_ranks(p, "player", player.get("attributes"), (prim, sec), rules, level=level)

    # -- the heroes
    if len(heroes) > HEROES_MAX:
        p.append(f"{len(heroes)} heroes; the client's cap is {HEROES_MAX} "
                 f"(PtPlayer:332, GmHeroCommander:214)")
    seen = set()
    for i, h in enumerate(heroes, 1):
        idx = int(h.get("hero", 0))
        if not 1 <= idx <= HERO_INDEX_MAX:
            p.append(f"hero {i}: catalogue index {idx} is not 1..{HERO_INDEX_MAX}")
        if idx in seen:
            p.append(f"hero {i}: catalogue index {idx} is used twice; each 0x0074 "
                     f"record is keyed by it")
        seen.add(idx)
        body = h.get("body")
        if not body:
            p.append(f"hero {i}: no body template")
        elif npcs and body not in npcs:
            p.append(f"hero {i}: body {body!r} is not an npc template")
        hp = int(h.get("profession") or (npcs.get(body) or {}).get("profession") or 0)
        if hp not in PROFESSIONS:
            p.append(f"hero {i}: profession {hp} is not 1..10 (give the hero one, "
                     f"or a body whose template carries one)")
        hbar = _ints(h.get("skills"))
        if len(hbar) > BAR_SLOTS:
            p.append(f"hero {i}: {len(hbar)} skills; the bar is {BAR_SLOTS} wide")
        for sid in hbar:
            if sid and skill_owned(world, sid, (hp,)) is False:
                p.append(f"hero {i}: skill {sid} is not a {PROFESSIONS.get(hp)} skill")
        hl = int(h.get("level", level))
        if not 1 <= hl <= LEVEL_MAX:
            p.append(f"hero {i}: level {hl} is outside 1..{LEVEL_MAX}")
        wkey = h.get("weapon") or HERO_WEAPON_BY_PROFESSION.get(hp)
        if rates and wkey and wkey not in rates:
            p.append(f"hero {i}: weapon {wkey!r} is not an [attack_speed.rates] key")
        _check_ranks(p, f"hero {i}", h.get("attributes"), (hp,), rules, level=hl)

    # -- the groups
    if not groups:
        p.append("no groups: the corridor needs at least the boss")
    if len(groups) > GROUPS_MAX:
        p.append(f"{len(groups)} groups; the corridor holds {GROUPS_MAX}")
    bosses = []
    for gi, g in enumerate(groups, 1):
        members = list(g.get("members") or [])
        if not members:
            p.append(f"group {gi}: no members")
        if len(members) > GROUP_SIZE_MAX:
            p.append(f"group {gi}: {len(members)} members; the most is {GROUP_SIZE_MAX}")
        for mi, m in enumerate(members, 1):
            who = f"group {gi} member {mi}"
            npc = m.get("npc")
            if not npc:
                p.append(f"{who}: no npc template")
            elif npcs and npc not in npcs:
                p.append(f"{who}: {npc!r} is not an npc template")
            elif npcs and not npcs[npc].get("model_id"):
                p.append(f"{who}: {npc!r} has no body (no model_id)")
            if m.get("boss"):
                bosses.append((gi, mi))
                glow = int(m.get("glow", DEFAULT_GLOW))
                if not 0 <= glow <= GLOW_MAX:
                    p.append(f"{who}: glow {glow} is outside 0..{GLOW_MAX} "
                             f"(ConstGlow.cpp:42 asserts past it)")
            wi = m.get("weapon_item")
            if wi and items and wi not in items:
                p.append(f"{who}: weapon_item {wi!r} is not a content item")
            # its level is one the window's spin offers, 0..HOSTILE_LEVEL_MAX
            # (content rows default to 0; the ceiling is the wire's byte, said
            # at the constant -- NOT the player's LEVEL_MAX, the owner's ruling
            # of 2026-09-24), read where spawn_rows reads it: the member's,
            # else its template's. Its ranks are checked for VALIDITY only --
            # well-formed pairs, a real attribute of the template's own
            # profession, each rank 0..HOSTILE_RANK_MAX -- and never against a
            # point budget: a hostile is EXEMPT, the owner's ruling (2026-09-24,
            # PLAN-LOG), since retail foes and bosses exceed a player's budget;
            # the player's and a hero's ranks keep theirs. (The budget was
            # checked here for one day, as the window's hint had promised, and
            # 'level 24 has 0' named the ranks when the level was the fault.)
            # No template, no check: an unknown one is refused above, and with
            # no npc rows at all the rest of this loop is unchecked too (in
            # profession 0 every rank read 'not to []'). The ranks are checked
            # whether or not the level passed -- `if`, not `elif`: the elif
            # was the budget's (a level past the cap priced the ranks at 0),
            # and with no budget it only hid a rank reason behind a level
            # reason, so a member at level 300 with a rank of 22 was refused
            # for one and the window clamped both, saying '1 change'
            tmpl = npcs.get(npc) or {}
            lvl = int(m.get("level", tmpl.get("level", 0) or 0))
            if not 0 <= lvl <= HOSTILE_LEVEL_MAX:
                p.append(f"{who}: level {lvl} is outside 0..{HOSTILE_LEVEL_MAX}")
            if tmpl:
                _check_ranks(p, who, m.get("attributes"),
                             (int(tmpl.get("profession") or 0),), rules)
            if int(m.get("health", 1)) < 1:
                p.append(f"{who}: health below 1")
    if len(bosses) != 1:
        p.append(f"{len(bosses)} bosses; exactly one row may be the quest's kill "
                 f"objective ({BOSS_SPAWN_KEY})")
    elif bosses[0][0] != len(groups):
        p.append(f"the boss is in group {bosses[0][0]} of {len(groups)}; the boss's "
                 f"group must be the LAST one, at the corridor's north end")
    return p


def _check_ranks(p, who, pairs, professions, rules, level=None):
    """Append to `p` every reason `pairs` ([attribute, rank] rows) cannot stand
    on a row of `professions` (the primary first). With a `level` the ranks go
    against that level's point budget too, and each rank against the cost
    table's rules.rank_max (the player's and a hero's rule: the client asserts
    past 12); None is no budget at all and the ceiling is HOSTILE_RANK_MAX --
    a hostile's ranks are validity-checked only, the owner's rulings
    (2026-09-24, PLAN-LOG: exempt from the budget; the caps lifted)."""
    if not pairs:
        return
    ranks = {}
    for pair in pairs:
        try:
            a, r = int(pair[0]), int(pair[1])
        except (TypeError, ValueError, IndexError):
            p.append(f"{who}.attributes: {pair!r} is not [attribute, rank]")
            continue
        if a in ranks:
            p.append(f"{who}.attributes: attribute {a} twice")
        ranks[a] = r
    if rules is None:
        return                                  # no vault tables: unchecked, said by the caller
    want = set(int(x) for x in professions if x)
    rank_max = rules.rank_max if level is not None else HOSTILE_RANK_MAX
    for a, r in ranks.items():
        row = rules.attributes.get(a)
        if row is None:
            p.append(f"{who}.attributes: {a} is not an attribute id (s_attrib 0..50)")
            continue
        if row["profession"] not in want:
            p.append(f"{who}.attributes: attribute {a} belongs to profession "
                     f"{row['profession']}, not to {sorted(want)}")
        elif row["is_primary"] and row["profession"] != professions[0]:
            p.append(f"{who}.attributes: attribute {a} is profession {row['profession']}'s "
                     f"PRIMARY attribute, spendable only as a primary")
        if not 0 <= r <= rank_max:
            p.append(f"{who}.attributes: rank {r} on {a} is outside 0..{rank_max}")
    if level is None:
        return                                  # a hostile: no budget, by the owner's ruling
    budget = budget_for_level(level)
    spent = rules.total_spent({a: min(r, rules.rank_max) for a, r in ranks.items()})
    if spent > budget:
        p.append(f"{who}.attributes spend {spent} points; level {level} has {budget}")


# ---------------------------------------------------------------- compile

def _toml(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(float(v))
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml(x) for x in v) + "]"
    raise TypeError(f"no TOML for {type(v).__name__}: {v!r}")


def _emit(lines, table, prov_note, prefix):
    for k, v in table.items():
        if v is None:
            continue
        lines.append(f"{k} = {_toml(v)}")
    lines.append(f"[{prefix}.provenance]")
    lines.append('source = "invented"')
    lines.append(f"note = {_toml(prov_note)}")
    lines.append("")


def hero_table(h, world, fallback_level):
    """One [[party.KEY.heroes]] table from a spec hero."""
    npcs = _rows(world, "npc")
    body = h["body"]
    prof = int(h.get("profession") or (npcs.get(body) or {}).get("profession") or 1)
    level = int(h.get("level", fallback_level))
    energy, _pips = ENERGY_BY_PROFESSION.get(prof, (30, 4))
    wkey = h.get("weapon") or HERO_WEAPON_BY_PROFESSION.get(prof, "staff")
    damage = h.get("damage")
    if damage is None and wkey in CASTER_WEAPONS:
        damage = list(CASTER_DAMAGE)
    wattr = h.get("weapon_attribute")
    if wattr is None:
        wattr = weapon_attribute_for_key(world, wkey) or None
    if wattr is None and h.get("attributes"):
        # A caster weapon's type row names no attribute; the slice's hero
        # swings its Holy Rod at its first listed rank (SLICE-H8: 13, Healing
        # Prayers), so the first pair stands in.
        wattr = int(h["attributes"][0][0])
    return {
        "hero": int(h["hero"]), "profession": prof, "body": body,
        # An absent bar or rank list is an EMPTY one, on purpose: the in-game
        # panels fill them and --persist keeps what they wrote (SANDBOX-B7).
        "skills": _ints(h.get("skills")), "level": level,
        "health": int(h.get("health", morale.base_health(level))),
        "energy": int(h.get("energy", energy)), "weapon": wkey,
        "attributes": [[int(a), int(r)] for a, r in (h.get("attributes") or [])],
        "points": int(h.get("points", points_for_level(level))),
        "armor": float(h.get("armor", HERO_ARMOR_DEFAULT)),
        "damage": [int(damage[0]), int(damage[1])] if damage else None,
        "weapon_attribute": int(wattr) if wattr is not None else None,
    }


def party_row(spec, world):
    """The [party.sandbox] row's fields (heroes as a list under 'heroes')."""
    player = spec.get("player") or {}
    prim = int(player.get("profession", 1))
    sec = int(player.get("secondary", 0))
    level = int(player.get("level", 3))
    energy, pips = ENERGY_BY_PROFESSION.get(prim, (25, 3))
    weapon, offhand = PLAYER_ITEMS_BY_PROFESSION.get(prim, ("starter_sword", "starter_shield"))
    heroes = [hero_table(h, world, level) for h in (spec.get("heroes") or [])]
    row = {
        "player_profession": prim,
        "player_secondary": sec if sec else None,
        "player_level": level,
        "player_health": int(player.get("health", morale.base_health(level))),
        "player_energy": int(player.get("energy", energy)),
        "player_pips": int(player.get("pips", pips)),
        "player_attributes": [[int(a), int(r)] for a, r in (player.get("attributes") or [])],
        "player_points": int(player.get("points", points_for_level(level))),
        "player_weapon": player.get("weapon", weapon),
        "player_offhand": player.get("offhand", offhand) or None,
        "player_armour": player.get("armour") or PLAYER_ARMOUR_BY_PROFESSION.get(prim),
        # Always written, empty included: an empty bar is the panel's to fill
        # and empty ranks are every point unspent (SANDBOX-B7); the server
        # keeps the fixture's only when the field is ABSENT.
        "player_skills": _ints(player.get("skills")),
    }
    # The single-hero fields carry the FIRST hero, so a server that predates
    # per-hero rows (or a site that still reads the globals) sees a sane party.
    if heroes:
        first = heroes[0]
        row.update({"hero": [h["hero"] for h in heroes], "body": first["body"],
                    "skills": first["skills"], "level": first["level"],
                    "health": first["health"], "energy": first["energy"],
                    "weapon": first["weapon"], "attributes": first["attributes"],
                    "armor": first["armor"], "damage": first["damage"],
                    "weapon_attribute": first["weapon_attribute"]})
    row["heroes"] = heroes
    return row


def spawn_rows(spec, world):
    """[(key, row)] -- one per hostile, positioned, with ids allocated."""
    groups = list(spec.get("groups") or [])
    sizes = [len(g.get("members") or []) for g in groups]
    boss_group = next((gi for gi, g in enumerate(groups)
                       if any(m.get("boss") for m in (g.get("members") or []))), len(groups) - 1)
    # The boss stands first in its group so it takes the centre offset.
    ordered = []
    for gi, g in enumerate(groups):
        members = list(g.get("members") or [])
        if gi == boss_group:
            members.sort(key=lambda m: 0 if m.get("boss") else 1)
        ordered.append(members)
    positions = group_positions(len(groups), sizes, boss_group)
    npcs = _rows(world, "npc")
    rows, defs, aid, pi = [], {}, AGENT_ID_FIRST, 0
    for gi, members in enumerate(ordered, 1):
        for mi, m in enumerate(members, 1):
            npc = m["npc"]
            template = npcs.get(npc) or {}
            level = int(m.get("level", template.get("level", 0) or 0))
            # a definition per (template, LEVEL), the docstring's IDS paragraph:
            # 0x0056 carries the level in the definition and is re-sent on
            # every create, so one slot for an L3 and an L24 of one body held
            # whichever was declared last (RECONSTRUCTION, 2026-09-24)
            if (npc, level) not in defs:
                defs[npc, level] = DEFINITION_FIRST + len(defs)
            x, y = positions[pi]
            pi += 1
            wi = m.get("weapon_item")
            speed = m.get("attack_speed")
            if speed is None and wi:
                speed = weapon_rate_for_item(world, wi)
            row = {
                "area": AREA_KEY, "map": CORRIDOR_MAP, "npc": npc,
                "agent_id": aid, "definition": defs[npc, level],
                "x": float(x), "y": float(y),
                "allegiance": "hostile", "attacks_back": True,
                "max_health": int(m.get("health", 120)), "level": level,
                "skills": [skill_triple(world, s) for s in _ints(m.get("skills"))],
                "attributes": [[int(a), int(r)] for a, r in (m.get("attributes") or [])] or None,
                "damage": [int(m["damage"][0]), int(m["damage"][1])] if m.get("damage") else None,
                "weapon_attribute": (int(m["weapon_attribute"])
                                     if m.get("weapon_attribute") is not None else None),
                "weapon_item": wi or None,
                "attack_speed": float(speed) if speed is not None else None,
                "passive": True if m.get("passive") else None,
                "group": f"g{gi}",
                "enabled": True,
            }
            key = f"sandbox_g{gi}_m{mi}"
            if m.get("boss"):
                row["glow"] = int(m.get("glow", DEFAULT_GLOW))
                key = BOSS_SPAWN_KEY
            rows.append((key, row))
            aid += 1
    return rows


def overlay_text(spec, world):
    """The overlay file, as text. Loads through toolkit/content.py."""
    name = str(spec.get("name") or "sandbox")
    note = (f"Ours: generated by toolkit/harness/sandbox.py from the sandbox spec "
            f"{name!r} (SANDBOX-B2). Every number is the spec's; the geometry and "
            f"the ids are the compiler's, said in its docstring.")
    lines = [f"# GENERATED by toolkit/harness/sandbox.py from spec {name!r} -- do not hand-edit.",
             "# Merged over the tree for ONE launch through RURIK_CONTENT_EXTRA (SANDBOX-B1).",
             "", f"[party.{PARTY_KEY}]"]
    prow = party_row(spec, world)
    heroes = prow.pop("heroes")
    _emit(lines, prow, note, f"party.{PARTY_KEY}")
    for h in heroes:
        lines.append(f"[[party.{PARTY_KEY}.heroes]]")
        for k, v in h.items():
            if v is not None:
                lines.append(f"{k} = {_toml(v)}")
        lines.append("")
    for key, row in spawn_rows(spec, world):
        lines.append(f"[spawn.{key}]")
        _emit(lines, row, note, f"spawn.{key}")
    return "\n".join(lines)


def party_professions(spec, world):
    """The character's pair and every hero's profession."""
    player = spec.get("player") or {}
    prim = int(player.get("profession", 1))
    sec = int(player.get("secondary", 0))
    profs = {prim} | ({sec} if sec else set())
    for h in spec.get("heroes") or []:
        hp = h.get("profession") or (_rows(world, "npc").get(h.get("body")) or {}).get("profession")
        if hp:
            profs.add(int(hp))
    return profs


def unlocks_for(spec, world):
    """The ACCOUNT library this run sends as --unlocks (0x001D): the spec's
    top-level `unlocks` (the window's Skills tab), else `player.unlocks`,
    else every skill of the party's professions; the bars' own ids always."""
    player = spec.get("player") or {}
    given = spec.get("unlocks")
    if given is None:
        given = player.get("unlocks")
    unlocks = set(_ints(given)) if given is not None else set(
        default_unlocks(world, party_professions(spec, world)))
    unlocks |= set(s for s in _ints(player.get("skills")) if s)
    for h in spec.get("heroes") or []:
        unlocks |= set(s for s in _ints(h.get("skills")) if s)
    return sorted(unlocks)


def game_args(spec, world):
    """The gamesrv's flags. `--map` and `--area` are the harness's too
    (session.served_maps, the pre-flight). `--persist` always: the bars and
    ranks are the in-game panels' to set, and the character store is what
    keeps them from one run to the next (SANDBOX-B7)."""
    player = spec.get("player") or {}
    prim = int(player.get("profession", 1))
    sec = int(player.get("secondary", 0))
    unlocks = unlocks_for(spec, world)
    args = ["--map", str(TOWN_MAP), "--party", PARTY_KEY,
            "--area", f"{TOWN_AREA},{AREA_KEY}",
            "--spawn-profession", str(prim)]
    if sec:
        args += ["--spawn-secondary", str(sec)]
    if unlocks:
        args += ["--unlocks", ",".join(str(s) for s in unlocks)]
    if spec.get("persist", True):
        args.append("--persist")
    # SKILLS-LT: `gamesrv_args = ["--no-skill-labels"]` is how a spec runs the
    # label tier's CONTROL arm (studies/skills 55.5's runsheet); any gamesrv
    # flag passes through, last, so it can override the fixed ones above.
    args += [str(x) for x in (spec.get("gamesrv_args") or [])]
    return args


# ---------------------------------------------------------------- the store

def store_email():
    """The loopback run's account, which names the character store file."""
    try:
        import accounts                       # toolkit/harness/accounts.py
        return accounts.synthetic()["email"]
    except Exception:                         # noqa: BLE001
        return None


def store_path(email=None):
    try:
        import charstore                      # toolkit/authsrv/charstore.py
        return charstore.path_for(email or store_email())
    except Exception:                         # noqa: BLE001
        return None


def store_state(email=None):
    """What the character store holds for the loopback account, or None:
    {"path", "account_unlocked", "characters": {name: {"level", "skillbar",
    "attributes", "kicked_heroes", "heroes": {index: {"skillbar",
    "attributes", "attribute_points"}}}}}. Read-only, stdlib (json).
    `kicked_heroes` (SANDBOX-N2) is what an in-game kick under --persist
    holds: those heroes stay OWNED but out of the party on every later run
    until `--reset-hero-kicks` (or the ADD, when it ships) puts them back."""
    import json
    path = store_path(email)
    if not path or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    chars = {}
    for _uuid, row in (data.get("characters") or {}).items():
        chars[str(row.get("name", _uuid))] = {
            "level": row.get("level"), "skillbar": row.get("skillbar"),
            "attributes": row.get("attributes"),
            "kicked_heroes": list(row.get("kicked_heroes") or []),
            "heroes": {int(k): {"skillbar": v.get("skillbar"),
                                "attributes": v.get("attributes"),
                                "attribute_points": v.get("attribute_points")}
                       for k, v in (row.get("heroes") or {}).items()}}
    return {"path": path,
            "account_unlocked": (data.get("account") or {}).get("unlocked_skills"),
            "characters": chars}


def store_warnings(spec, world, st):
    """What a previous run's edits mean for THIS spec, as lines. The store
    wins at load under --persist, so a bar or a rank it holds outlives the
    spec that first wrote them."""
    if not st:
        return []
    out = []
    unlocks = set(unlocks_for(spec, world))
    if st.get("account_unlocked") is not None:
        out.append(f"the store holds an ACCOUNT library of {len(st['account_unlocked'])} "
                   f"skills, which wins over the Skills tab's --unlocks (charstore.py "
                   f"--set-unlocked, or reset the store)")
    # The CHARACTER's own pair: a hero's profession makes nothing spendable
    # or slottable for the character.
    player = spec.get("player") or {}
    profs = {int(player.get("profession", 1))}
    if int(player.get("secondary", 0)):
        profs.add(int(player["secondary"]))
    rules = attribute_rules(world)
    party = {int(h["hero"]) for h in spec.get("heroes") or [] if h.get("hero") is not None}
    for name, c in st["characters"].items():
        bar = [s for s in (c.get("skillbar") or []) if s]
        unbacked = [s for s in bar if s not in unlocks]
        if unbacked:
            out.append(f"{name}'s stored bar carries {unbacked}, outside this run's "
                       f"unlocks: they draw, and dragging one asserts the client")
        if bar:
            foreign = [s for s in bar if skill_owned(world, s, profs) is False]
            if foreign:
                out.append(f"{name}'s stored bar carries {foreign}, skills of a profession "
                           f"this character is not")
        if rules and c.get("attributes"):
            off = [a for a, _r in c["attributes"]
                   if rules.attributes.get(int(a), {}).get("profession") not in profs]
            if off:
                out.append(f"{name}'s stored ranks include attributes {off} of another "
                           f"profession; the panel will carry them")
        for idx, h in (c.get("heroes") or {}).items():
            if idx in party and h.get("skillbar"):
                out.append(f"hero {idx} keeps its stored bar {[s for s in h['skillbar'] if s]} "
                           f"(the store wins over the spec)")
    return out


def reset_store(email=None):
    """Delete the loopback account's store file so the next login re-seeds
    it: a fresh character, no bars, no ranks, no hero builds. Returns the
    path removed, or None when there was none. The vault's own scratch
    state, never anything under the tree."""
    path = store_path(email)
    if path and os.path.isfile(path):
        os.remove(path)
        return path
    return None


def run_paths(vault_root=None):
    """(exe, dat) of the slice archive's run directory, or a SpecError saying
    what to build."""
    base = os.path.join(vault_root or vaultpath.vault_root(), "run", RUN_DIR)
    exe, dat = os.path.join(base, "Gw.exe"), os.path.join(base, "Gw.dat")
    if not (os.path.isfile(exe) and os.path.isfile(dat)):
        raise SpecError(f"no slice run directory at {base}: the corridor lives only "
                        f"in that archive. Build it with `python toolkit/mapdata/"
                        f"compose.py --name slice --build` (RUNBOOK.md, SLICE-B9)")
    return exe, dat


def launch_command(args, exe, hold=None, warn=3, replace=True):
    """session.py's argv: the stack, the client, held until the client closes."""
    cmd = [sys.executable, "-u", os.path.join(HERE, "session.py")]
    if replace:
        cmd.append("--replace")
    cmd += ["--keep-open", "--warn", str(int(warn))]
    if hold:
        cmd += ["--hold", str(int(hold))]
    cmd += ["--exe", exe, "--game-args", " ".join(args)]
    return cmd


def compile_spec(spec, world, out_dir, exe=None, dat=None, hold=None, store=None):
    """Everything a launch needs, or SpecError. Writes nothing.

    `store` is a store_state() result to warn against (default: the loopback
    account's, read now; pass {} for none). Returns {"name", "overlay_dir",
    "overlay_path", "overlay", "args", "command", "env", "spawn_rows",
    "party_row", "notes", "store_warnings"}."""
    problems = validate(spec, world)
    if problems:
        raise SpecError("the spec cannot run:\n  - " + "\n  - ".join(problems))
    rows = spawn_rows(spec, world)
    pop = check_population(rows)
    if pop:
        raise SpecError("the population is unsound:\n  - " + "\n  - ".join(pop))
    name = str(spec.get("name") or "sandbox")
    overlay_dir = os.path.join(out_dir, name)
    args = game_args(spec, world)
    if exe is None or dat is None:
        exe, dat = run_paths()
    env = {"RURIK_DAT": dat, "RURIK_CONTENT_EXTRA": overlay_dir}
    try:
        st = store_state() if store is None else store
    except Exception as exc:                  # noqa: BLE001
        st = None
        store_notes = [f"the character store could not be read ({exc})"]
    else:
        store_notes = []
    return {
        "name": name, "overlay_dir": overlay_dir,
        "overlay_path": os.path.join(overlay_dir, "world.toml"),
        "overlay": overlay_text(spec, world), "args": args,
        "command": launch_command(args, exe, hold=hold), "env": env,
        "spawn_rows": rows, "party_row": party_row(spec, world),
        "notes": ([] if has_skill_table(world) else
                  ["no skills table (vault/content/skills.toml): skill ownership and "
                   "timing were NOT checked; every activation and recharge is 0"])
                 + store_notes,
        "store_warnings": store_warnings(spec, world, st),
    }


def write_overlay(compiled):
    os.makedirs(compiled["overlay_dir"], exist_ok=True)
    with open(compiled["overlay_path"], "w", encoding="utf-8") as fh:
        fh.write(compiled["overlay"])
    return compiled["overlay_path"]


def launch(compiled, cwd=None):
    """Start the harness with the overlay in force. The caller waits."""
    env = dict(os.environ)
    env.update(compiled["env"])
    return subprocess.Popen(compiled["command"], cwd=cwd or os.path.dirname(TOOLKIT),
                            env=env)


def summary(compiled):
    """Lines a human reads before pressing the button."""
    prow = compiled["party_row"]
    out = [f"spec {compiled['name']!r}",
           f"  player: {ABBREV.get(prow['player_profession'], '?')}"
           f"/{ABBREV.get(prow.get('player_secondary') or 0, '-')} level "
           f"{prow['player_level']}, bar {prow.get('player_skills')}, "
           f"{prow['player_weapon']}" + (f" + {prow['player_offhand']}" if prow.get('player_offhand') else "")]
    for h in prow["heroes"]:
        out.append(f"  hero {h['hero']}: {ABBREV.get(h['profession'], '?')} in "
                   f"{h['body']!r}, level {h['level']}, bar {h['skills']}, {h['weapon']}")
    for key, row in compiled["spawn_rows"]:
        out.append(f"  {key}: {row['npc']} level {row['level']} {row['max_health']} hp "
                   f"at ({row['x']:.0f}, {row['y']:.0f}) group {row['group']}"
                   + (f" BOSS glow {row['glow']}" if "glow" in row else ""))
    out.append("  gamesrv: " + " ".join(compiled["args"]))
    out.append("  env: " + ", ".join(f"{k}={v}" for k, v in compiled["env"].items()))
    out += [f"  NOTE: {n}" for n in compiled.get("notes", [])]
    out += [f"  STORE: {n}" for n in compiled.get("store_warnings", [])]
    return out


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", default=None, help="the spec TOML")
    ap.add_argument("--example", action="store_true",
                    help="print the vertical slice as a spec and exit")
    ap.add_argument("--out", default=None,
                    help="where overlays go (default vault/sandbox)")
    ap.add_argument("--write", action="store_true", help="write the overlay")
    ap.add_argument("--launch", action="store_true",
                    help="write the overlay and run the harness on it")
    ap.add_argument("--hold", type=int, default=None,
                    help="end the run after N seconds instead of when the client closes")
    a = ap.parse_args(argv)
    if a.example:
        print(example_toml())
        return 0
    if not a.spec:
        ap.error("--spec or --example")
    spec = load_spec(a.spec)
    world = content.load()
    out_dir = a.out or vaultpath.vault_path("sandbox")
    try:
        compiled = compile_spec(spec, world, out_dir, hold=a.hold)
    except SpecError as exc:
        print(exc)
        return 2
    for line in summary(compiled):
        print(line)
    if a.write or a.launch:
        print(f"overlay: {write_overlay(compiled)}")
    else:
        print("\n" + compiled["overlay"])
    print("command: " + " ".join(compiled["command"]))
    if a.launch:
        proc = launch(compiled)
        return proc.wait()
    return 0


def spec_toml(spec, header=None):
    """A spec as TOML text -- the shape the window saves and this CLI reads.
    Keys whose value is None are left out."""
    lines = list(header or ["# A sandbox spec. Run with",
                            "#   python toolkit/harness/sandbox.py --spec this.toml --launch"])
    lines += [f"name = {_toml(spec.get('name') or 'sandbox')}"]
    if spec.get("unlocks") is not None:
        lines.append(f"unlocks = {_toml(_ints(spec['unlocks']))}")
    if spec.get("persist") is not None:
        lines.append(f"persist = {_toml(bool(spec['persist']))}")
    lines += ["", "[player]"]
    for k, v in (spec.get("player") or {}).items():
        if v is not None:
            lines.append(f"{k} = {_toml(v)}")
    for h in spec.get("heroes") or []:
        lines += ["", "[[heroes]]"] + [f"{k} = {_toml(v)}" for k, v in h.items()
                                       if v is not None]
    for g in spec.get("groups") or []:
        lines += ["", "[[groups]]"]
        if g.get("name"):
            lines.append(f"name = {_toml(g['name'])}")
        for m in g.get("members") or []:
            lines += ["", "[[groups.members]]"] + [f"{k} = {_toml(v)}" for k, v in m.items()
                                                   if v is not None]
    return "\n".join(lines) + "\n"


def example_toml():
    """The example spec as TOML text."""
    return spec_toml(example_spec(),
                     ["# A sandbox spec: the vertical slice. Edit and run with",
                      "#   python toolkit/harness/sandbox.py --spec this.toml --launch"])


if __name__ == "__main__":
    sys.exit(main())
