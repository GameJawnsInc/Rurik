r"""An authored area's POPULATION: the rows, the set rules, and the placement.

R5's criterion is "a new zone in TOML, hot-reloaded, walked". The toolkit could
author the GROUND of a zone long before it could author anything standing on it,
and an area with a tree in it and nothing alive is a diorama. `--area NAME`
serves the `content/world.toml` spawn rows bound to that area.

WHY THIS COULD NOT HAVE BEEN WRITTEN BEFORE RUNG (I). The load-bearing rule here
is that a body is placed only where the navmesh says there is ground -- and
until 2026-08-13 the server on an authored map held either ArenaNet's geometry
for the same map id or no mesh at all (FINDINGS 59), so this check would have
been measuring the wrong map or nothing. It matters because an authored area can
be sparse: the sculpt map is 1.2% walkable by area, so a coordinate picked by eye
is ground about one time in eighty.

WHAT IS ACTUALLY CHECKED, and it is mostly refusals with positive controls
beside them, because a rule that refuses everything protects nothing and a rule
that refuses nothing is not a rule:

  * the set rules, which exist because their cost is a WASTED CLIENT RUN --
    `create_agent_world` already refuses a duplicate id, but by then half the
    population is in the world;
  * that a shared `definition` is ALLOWED within one npc template and REFUSED
    across two, which is the distinction retail itself draws;
  * that placement nudges and REPORTS, or refuses, and never silently invents;
  * that an area REPLACES the global test enemy rather than adding to it.

NO VAULT, NO SOCKET, NO CLIENT. The mesh is `pathchunk.minimal()`, a mesh
authored from nothing, so the placement half needs no archive.

    python toolkit/authsrv/test_population.py
"""

import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import authsrv  # noqa: E402
import checks  # noqa: E402
import content as content_mod  # noqa: E402
import pathchunk  # noqa: E402
from codec import Codec  # noqa: E402
import pathmap  # noqa: E402

# FLOOR: 51, MEASURED from a green run 2026-08-17 (43 + section 5's
# party-reserved ids, studies/unitsetup/FINDINGS.md 8 Q9). Every section is
# synthetic -- no vault, no socket, no client -- so there is nothing here that
# may skip.
LEDGER = checks.Ledger("test_population", floor=116)  # SANDBOX-N1 repair 2026-09-24 +2 (section 6: a template's ranks in both shapes reach the body); R-SANDBOX 2026-09-24 +30 (section 8: the level guard) then +8 (the verifier's fixes: a --probe's own 0x0056 steps, the last line's tail), from the green run; SLICE-H11 +2 (section 7: the held weapon); SLICE-B2 +7, SLICE-B6 glow +4 (section 6)
check = checks.adopt(LEDGER)

AREA = "sculpt"

_AUTHSRV_SOURCE = {}


def authsrv_source():
    """authsrv.py's text and its AST, parsed ONCE per run. Sections 3 and 8
    both ask the syntax tree, and one parse of a 39k-line file is seconds; the
    verifier of 2026-09-24 timed section 8's second parse at most of its 5.7 s."""
    if not _AUTHSRV_SOURCE:
        src = open(authsrv.__file__, encoding="utf-8").read()
        _AUTHSRV_SOURCE["src"], _AUTHSRV_SOURCE["tree"] = src, ast.parse(src)
    return _AUTHSRV_SOURCE["src"], _AUTHSRV_SOURCE["tree"]


def rows_for(area, table):
    """`area_population` against a table we built, not the live store.

    Takes the table so a sabotage can be a dict rather than an edit to
    `content/`, which is what lets every refusal below be exercised on data
    designed to break exactly one rule.
    """
    saved = authsrv.agents.WORLD
    try:
        authsrv.agents.WORLD = table
        return authsrv.area_population(area)
    finally:
        authsrv.agents.WORLD = saved


class FakeWorld:
    """Just enough of content.World for area_population: rows() and get().

    The npc table is the REAL store's, captured at construction (while the
    real store is still in place), with `npc` overriding by key: the level
    guard (section 8) reads a row's template, so a synthetic template at level
    300 needs a home, and every earlier section's rows name real templates.
    """

    def __init__(self, spawn, npc=None):
        self._spawn = spawn
        self._npc = dict(authsrv.agents.WORLD.rows("npc"))
        self._npc.update(npc or {})

    def rows(self, kind):
        if kind == "spawn":
            return dict(self._spawn)
        if kind == "npc":
            return dict(self._npc)
        return {}

    def get(self, kind, key):
        if kind == "npc":
            return self._npc[key]
        return self._spawn[key]


def row(**kw):
    base = {"area": AREA, "npc": "hatcher", "agent_id": 20, "definition": 5,
            "x": 0.0, "y": 0.0, "enabled": True}
    base.update(kw)
    return base


def accepts(spawn, npc=None):
    """The accepted keys, or None if the population was refused.

    EVERY call in this file goes through here or `refuses`, and that is not
    style. A positive control that calls `area_population` directly turns a
    sabotage which refuses too much into an uncaught PopulationError -- bare
    traceback, no verdict banner, no ledger. That is exactly what the
    "refuse ANY shared definition" sabotage did to the first version of this
    file: 0 checks reported, which reads as a broken test rather than as a
    caught defect.
    """
    try:
        return [k for k, _ in rows_for(AREA, FakeWorld(spawn, npc))]
    except authsrv.PopulationError:
        return None


def refuses(spawn, why):
    """True iff area_population refuses this table."""
    return accepts(spawn) is None


def refusal(spawn, npc=None):
    """The refusal's TEXT, or None if the population was accepted -- section 8
    reads the message, because a guard that refuses without naming the row,
    the level and the reason costs the operator the same hunt it exists to
    spare."""
    try:
        rows_for(AREA, FakeWorld(spawn, npc))
        return None
    except authsrv.PopulationError as exc:
        return str(exc)


def section0():
    print("\n0. the rows load, and an area's population is BOUND to that area")
    world = content_mod.load(vault_dir="")
    spawn = world.rows("spawn")
    check(bool(spawn), "content carries a spawn table", f"{len(spawn)} row(s)")

    mine = {k: v for k, v in spawn.items() if v.get("area") == AREA}
    check(len(mine) >= 3,
          f"area {AREA!r} declares at least three bodies -- a population of two "
          f"is satisfied by code that handles exactly two",
          f"{sorted(mine)}")

    # THE LEGACY ROW MUST NOT BE IN ANY POPULATION. It is placed by offset from
    # the player, so serving it inside an authored zone drops a body in the
    # middle of somebody's arrangement.
    globals_ = [k for k, v in spawn.items() if v.get("area") is None]
    check(globals_ == ["test_enemy"],
          "the one area-less spawn row is the legacy global enemy",
          f"{globals_}")
    # CATCH IT. A PopulationError here is a FAIL, not a crash: the sabotage that
    # refuses any shared `definition` makes the REAL rows unloadable (all three
    # sculpt bodies are hatchers sharing index 5), and the first version of this
    # let that escape -- bare traceback, no verdict banner, 0 checks reported.
    # Same trap `vaultpath.require_dir` set for test_stripbuild: a caught defect
    # that prints no verdict reads as a broken test rather than a caught defect.
    try:
        got = [k for k, _ in rows_for(AREA, world)]
        loaded = True
    except authsrv.PopulationError as exc:
        got, loaded = [], False
        print(f"       PopulationError: {exc}")
    check(loaded, "the SHIPPED rows in content/world.toml load as a set -- if "
                  "this is red the rules and the content disagree and every "
                  "check below is measuring the wrong thing")
    check(loaded and "test_enemy" not in got,
          "and the global enemy is NOT returned as part of an area's population",
          f"{got}")
    check(loaded and sorted(got) == sorted(mine),
          "while every row that names the area IS", f"{sorted(got)}")

    for key, r in sorted(mine.items()):
        check(r.provenance["source"] == "invented",
              f"placement {key!r} is provenance 'invented' -- ours, chosen "
              f"rather than observed", r.provenance["source"])
        check(r["npc"] in world.rows("npc"),
              f"and names a real npc template", r["npc"])


def section1():
    print("\n1. the set rules, checked before a single body goes out")
    ok = {"a": row(agent_id=20, definition=5),
          "b": row(agent_id=21, definition=6, npc="lakeside_worm")}
    check(accepts(ok) == ["a", "b"],
          "POSITIVE CONTROL: a well-formed population of two is accepted -- "
          "without this every refusal below is satisfied by refusing all input")

    check(refuses({"a": row(agent_id=20), "b": row(agent_id=20, definition=6)},
                  "dup id"),
          "two rows sharing an agent_id are REFUSED -- one agent's state under "
          "another's name is a collision the wire cannot express")

    # THE ASYMMETRY IS THE POINT, and both halves must hold.
    same = {"a": row(agent_id=20, definition=5, npc="hatcher"),
            "b": row(agent_id=21, definition=5, npc="hatcher")}
    check(accepts(same) == ["a", "b"],
          "two rows of the SAME npc may share a definition -- it is per-instance "
          "and outlives its agents (ArenaNet: one 0x0056 for 140 re-creates), so "
          "demanding one each would invent a rule retail does not follow")
    diff = {"a": row(agent_id=20, definition=5, npc="hatcher"),
            "b": row(agent_id=21, definition=5, npc="lakeside_worm")}
    check(refuses(diff, "dup def across templates"),
          "but two DIFFERENT npcs sharing one are REFUSED -- the definition "
          "array is a raw index, so the second silently overwrites the first "
          "and a body wears the wrong model")

    for field in ("agent_id", "definition"):
        bad = {"a": row(**{field: None})}
        check(refuses(bad, f"missing {field}"),
              f"a row with no {field} is REFUSED rather than allocated -- this "
              f"server does not invent ids")

    off = {"a": row(enabled=False), "b": row(agent_id=21, definition=6,
                                             npc="lakeside_worm")}
    check(accepts(off) == ["b"],
          "a disabled row is left out without disturbing the rest")

    other = {"a": row(area="somewhere_else")}
    check(accepts(other) == [],
          "and a row naming a DIFFERENT area is not this area's problem")


def mesh(rect=(0.0, 0.0, 3072.0, 3072.0)):
    """A one-trapezoid mesh covering `rect`, authored from nothing."""
    return pathmap.PathingMap.from_chunk(
        pathchunk.PathChunk.minimal(rect=rect).encode())


def section2():
    print("\n2. placement: on the mesh, nudged onto it, or refused")
    pm = mesh()
    inside = (1536.0, 1536.0)
    check(pm.walkable(*inside),
          "POSITIVE CONTROL: the synthetic mesh calls its own middle ground -- "
          "otherwise every refusal below is refusing a broken fixture",
          f"{inside}")

    x, y, moved = authsrv.place_on_mesh(pm, *inside, "probe")
    check((x, y) == inside and moved == 0.0,
          "a point already on the mesh is left exactly where the author put it",
          f"moved {moved}")

    # JUST OUTSIDE: must be nudged ON, and the distance REPORTED. A search that
    # only ever answers "fine" or "refused" has never been shown to work.
    near = (-24.0, 1536.0)
    got = authsrv.place_on_mesh(pm, *near, "probe")
    check(got is not None and got[2] > 0.0 and pm.walkable(got[0], got[1]),
          "a point just off the mesh is nudged ONTO it, and the move is a "
          "non-zero distance the caller can report",
          f"{near} -> {None if got is None else (round(got[0]), round(got[1]), got[2])}")

    far = (-100000.0, -100000.0)
    check(authsrv.place_on_mesh(pm, *far, "probe") is None,
          "a point nowhere near the mesh is REFUSED, not placed -- a body where "
          "the server's own collision says nothing exists makes everything "
          "downstream reason about it wrongly")

    # THE SEARCH IS BOUNDED, and the bound is asserted against a LITERAL written
    # HERE. The first version computed its probe point as
    # `-(PLACE_SEARCH_RADIUS + 2*PLACE_SEARCH_STEP)` -- so raising the radius to
    # 100,000 moved the probe with it and the check stayed GREEN. A symbol
    # appearing in a test file is not a check; that is the same defect
    # test_agentlife records, where twelve of fourteen combat constants could be
    # set to a wrong value with all 125 checks passing, because every section
    # computed its expectation FROM the symbol under test.
    check(authsrv.PLACE_SEARCH_RADIUS == 480.0,
          "the search radius is 480 units", f"{authsrv.PLACE_SEARCH_RADIUS}")
    check(authsrv.PLACE_SEARCH_STEP == 48.0,
          "and the search step is 48", f"{authsrv.PLACE_SEARCH_STEP}")
    check(authsrv.place_on_mesh(pm, -600.0, 1536.0, "probe") is None,
          "and a point 600 units off the mesh is REFUSED -- a body found "
          "thousands of units from where it was written is not that body, so "
          "the bound must hold rather than widen until something is found")

    check(authsrv.place_on_mesh(None, 7.0, 9.0, "probe") == (7.0, 9.0, 0.0),
          "with NO mesh at all the point is passed through unchanged -- an "
          "archive is not required to be present, and refusing every body on a "
          "machine without one would be worse than placing them on trust")


def section2b():
    """Every shipped row must produce a message the codec will actually ENCODE.

    THIS IS THE SECTION THE FIRST RUN NEEDED AND DID NOT HAVE. Sections 0-2
    check which rows are selected and where a body may stand -- neither touches
    the ENTRY, so `spawn_population` reaching for `WORLD.get("npc", ...)`
    instead of `agents.npc_template(...)` sailed through all of them. The raw
    content row carries `enc_name` as a list of 16-bit string ids rather than an
    encoded string, so `npc_properties` built a message the codec refused with
    `string of 28 code units exceeds cap 8`.

    What made it expensive is where the throw landed: inside instance bring-up,
    on the connection thread, AFTER the map had loaded. The harness reported
    PASS, `deploy`'s readback was green on all six map checks -- correctly, they
    are about the map -- the serve check matched the navmesh, and the command
    exited 0. The only evidence was a traceback in the gamesrv log and three
    bodies that were not there. A run that reports success while doing nothing
    is the failure mode this repo keeps paying for.

    Encoding is the strongest thing checkable without a client: the codec is the
    same one the server sends through, so a row that encodes here is a row that
    goes on the wire.
    """
    print("\n2b. every shipped row builds a message the codec will encode")
    codec = Codec()
    world = content_mod.load(vault_dir="")
    try:
        rows = rows_for(AREA, world)
    except authsrv.PopulationError:
        rows = []
    check(bool(rows), "there are rows to encode", f"{len(rows)}")

    for key, r in rows:
        npc = None
        try:
            npc = authsrv.agents.npc_template(r["npc"])
            props = authsrv.agents.npc_properties(int(r["definition"]), npc)
            blob = codec.encode("GAME_SMSG",
                                authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES, props)
            ok, why = len(blob) > 0, f"{len(blob)} B"
        except Exception as exc:                              # noqa: BLE001
            ok, why = False, f"{type(exc).__name__}: {exc}"
        check(ok, f"{key!r} encodes an NPC definition", why)

    # NEGATIVE CONTROL: the exact mistake, reproduced. A template taken straight
    # from the content store must FAIL to encode -- otherwise this section is
    # green against both the fix and the bug and proves nothing.
    key, r = rows[0]
    raw = world.get("npc", r["npc"])
    try:
        codec.encode("GAME_SMSG", authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES,
                     authsrv.agents.npc_properties(int(r["definition"]), raw))
        caught = False
    except Exception:                                         # noqa: BLE001
        caught = True
    check(caught,
          "and the RAW content row -- the bug, reproduced -- is refused by the "
          "codec, so this section can tell the fix from the defect")


class StatWorld:
    """Synthetic spawn rows over the REAL npc table.

    `spawn_population` needs both halves -- the rows it places, and
    `npc_template`'s lookup for each row's template. Faking the npc half too
    would mean faking `enc_name`, which is the thing section 2b exists to keep
    honest, so this delegates everything that is not a spawn row.
    """

    def __init__(self, spawn, real, npc=None):
        self._spawn, self._real, self._npc = spawn, real, dict(npc or {})

    def rows(self, kind):
        if kind == "spawn":
            return dict(self._spawn)
        if kind == "npc" and self._npc:
            return dict(self._real.rows(kind), **self._npc)
        return self._real.rows(kind)

    def get(self, kind, key):
        if kind == "spawn":
            return self._spawn[key]
        if kind == "npc" and key in self._npc:
            return self._npc[key]
        return self._real.get(kind, key)


def place(spawn, sent=None, npc=None):
    """Run `spawn_population` over a synthetic table; return state['agents'].

    `sent`, when given, collects every (opcode, values, label) the placement
    put on the wire -- the glow arm reads it. `npc` overrides templates by
    key (section 8's level-300 template).
    """
    saved = authsrv.agents.WORLD
    state = {"agents": {}, "pos": (0.0, 0.0), "pathmap": None}
    sent = [] if sent is None else sent
    try:
        authsrv.agents.WORLD = StatWorld(spawn, saved, npc)
        authsrv.spawn_population(
            lambda op, vals, label="", **kw: sent.append((op, vals, label)),
            state, (0.0, 0.0, 0), 0, area=AREA)
    finally:
        authsrv.agents.WORLD = saved
    return state["agents"]


def section6():
    """SLICE-B2: the stat block is PER ROW, and the defaults are today's.

    Every check here is paired with the thing it has to differ from. A row that
    sets a bar proving it carries that bar says nothing on its own -- the global
    might simply happen to match -- so each positive is read against a row in
    the SAME table that did not set it.
    """
    print("\n6. SLICE-B2: skills, attack speed and armour come from the ROW")

    # The no-regression half FIRST: a row that says nothing must spawn exactly
    # what it spawned before B2 existed.
    bare = place({"a": row(agent_id=20, definition=5)})[20]
    check(tuple(bare["skills"]) == tuple(authsrv.ENEMY_SKILLS)
          and bare["attack_speed"] == authsrv.ENEMY_ATTACK_SPEED,
          "a row declaring no stats still takes the module defaults -- so "
          "--enemy-skills keeps reaching every row that does not override it",
          f"{[s[0] for s in bare['skills']]} @ {bare['attack_speed']}")

    # ARMOUR: absent entirely before B2, which is the defect. `taker_damage`
    # reads agent.get("armor_rating"), so a missing key meant the player's
    # swing ran with no armour term and nothing said so.
    check(bare.get("armor_rating") is not None,
          "and it now carries an armor_rating at all -- the key was ABSENT on "
          "this path, so every swing against an area body ran with no armour "
          "term", f"{bare.get('armor_rating')}")

    # DERIVED, not defaulted: level and profession drive it, and a row may
    # override. Two levels in one table, so the formula is what differs.
    two = place({"lo": row(agent_id=20, definition=5, level=1),
                 "hi": row(agent_id=21, definition=5, level=10)})
    check(two[21]["armor_rating"] > two[20]["armor_rating"],
          "armour is DERIVED from the row's level, not a constant: a level-10 "
          "body out-armours a level-1 one in the same table",
          f"lvl1={two[20]['armor_rating']} lvl10={two[21]['armor_rating']}")
    over = place({"a": row(agent_id=20, definition=5, level=1,
                           armor_rating=99)})[20]
    check(over["armor_rating"] == 99.0,
          "and an explicit armor_rating overrides the formula, because the "
          "wiki's own page says many PvE creatures do not follow it")

    # THE ARCHETYPE CASE: two rows, one table, different bars and speeds. This
    # is the whole point of B2 -- before it, both would have been clones.
    pair = place({
        "warrior": row(agent_id=20, definition=5, attack_speed=1.5,
                       skills=[[322, 0.0, 4.0]]),
        "monk": row(agent_id=21, definition=5, attack_speed=2.5,
                    skills=[[276, 0.75, 2.0]]),
    })
    check([s[0] for s in pair[20]["skills"]] == [322]
          and [s[0] for s in pair[21]["skills"]] == [276]
          and pair[20]["attack_speed"] == 1.5
          and pair[21]["attack_speed"] == 2.5,
          "TWO ARCHETYPES IN ONE AREA: different bars and different swing "
          "speeds, which is what B2 is for -- before it both rows took the "
          "one global bar and were clones",
          f"{[s[0] for s in pair[20]['skills']]}@{pair[20]['attack_speed']} vs "
          f"{[s[0] for s in pair[21]['skills']]}@{pair[21]['attack_speed']}")
    check(len(pair[20]["skill_ready"]) == 1
          and len(pair[21]["skill_ready"]) == 1,
          "and each gets its OWN recharge vector, sized to its own bar -- "
          "per SLOT, never per id, so a bar carrying one skill twice does not "
          "share a cooldown")

    # An EMPTY bar is a real answer and must not fall through to the global.
    # This is the check the `is None` test exists for; `if not bar` would fail.
    quiet = place({"a": row(agent_id=20, definition=5, skills=[])})[20]
    check(tuple(quiet["skills"]) == ()
          and tuple(authsrv.ENEMY_SKILLS) != (),
          "an EMPTY skills list means this body casts nothing -- it does NOT "
          "fall through to the global, and the second conjunct proves the "
          "global was non-empty so the check could have failed",
          f"{quiet['skills']} vs global {len(authsrv.ENEMY_SKILLS)}")

    # THE RANKS a body carries are the ROW's, else its TEMPLATE's, in EITHER
    # shape a TOML row can write (SANDBOX-N1's verifier, 2026-09-24): the
    # create path iterated a dict-shaped template's KEYS, so `{"13" = 9}`
    # reached the body as {1: 3} and Orison acted at rank 0 while the
    # orchestrator's cell said 9. Two templates, one dict-shaped and one
    # list-shaped, and a row with ranks of its own on the dict-shaped one.
    tmpl = dict(authsrv.agents.WORLD.get("npc", "hatcher"))   # the RAW row: the template table's shape
    ranked = place({"d": row(agent_id=20, definition=5, npc="tmpl_dict"),
                    "l": row(agent_id=21, definition=6, npc="tmpl_list"),
                    "own": row(agent_id=22, definition=5, npc="tmpl_dict",
                               attributes=[[17, 4]])},
                   npc={"tmpl_dict": dict(tmpl, attributes={"13": 9}),
                        "tmpl_list": dict(tmpl, attributes=[[13, 9]])})
    check(ranked[20]["attributes"] == {13: 9} == ranked[21]["attributes"]
          and authsrv.agent_skill_rank(ranked[20], 281) == 9,
          "a row with no ranks takes its TEMPLATE's, whether the template writes "
          "them {a = r} or [[a, r]] -- {13: 9} on the body either way, and Orison "
          "(attribute 13) acts at 9 (the dict shape reached the body as {1: 3})",
          f"dict {ranked[20]['attributes']}, list {ranked[21]['attributes']}")
    check(ranked[22]["attributes"] == {17: 4}
          and authsrv.agent_skill_rank(ranked[22], 281) == 0,
          "and a row's OWN ranks win over its template's outright -- {17: 4}, "
          "under which Orison acts at 0 (the template's 13 is not merged in)",
          f"{ranked[22]['attributes']}")

    # THE BOSS AURA (SLICE-B6 / SLICE-F1): one int property 29 after the
    # create, and never for a row that does not ask.
    sent = []
    place({"boss": row(agent_id=20, definition=5, glow=5),
           "mook": row(agent_id=21, definition=5)}, sent=sent)
    glows = [(v[1], v[2]) for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and v[0] == authsrv.agents.GV_GLOW]
    check(glows == [(20, 5)],
          "a row with glow = 5 sends int property 29 [agent, 5] for THAT body "
          "and the plain row beside it sends none",
          f"{glows} of {len(sent)} messages")
    creates = [i for i, (op, v, _l) in enumerate(sent)
               if op == authsrv.GAME_SMSG_WORLD_CREATE_AGENT and v[0] == 20]
    props = [i for i, (op, v, _l) in enumerate(sent)
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and v[0] == authsrv.agents.GV_GLOW]
    check(creates and props and creates[0] < props[0],
          "and the property goes out AFTER the body's create -- the setter "
          "looks the agent up and returns silently if it is not there yet",
          f"create at {creates[:1]}, glow at {props[:1]}")
    try:
        place({"boss": row(agent_id=20, definition=5, glow=11)})
        refused = False
    except authsrv.PopulationError as exc:
        refused = "s_glow" in str(exc)
    check(refused,
          "glow = 11 is REFUSED at load, naming s_glow's 11 rows -- the "
          "client's own answer would be an assert at ConstGlow.cpp(42)")


def section3():
    print("\n3. an area REPLACES the global enemy; the wiring is not optional")
    src, tree = authsrv_source()

    # The call site: `if AREA_NAME: spawn_population(...) elif SPAWN_ENEMY: ...`
    # Both firing would drop the offset-placed test enemy into the middle of an
    # authored arrangement. Asked of the syntax tree because "the enemy is in
    # the else" is invisible to a grep.
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not (isinstance(node.test, ast.Name) and node.test.id == "AREA_NAME"):
            continue
        calls = {getattr(n.func, "id", "") for n in ast.walk(node)
                 if isinstance(n, ast.Call)}
        orelse = {getattr(n.func, "id", "") for e in node.orelse
                  for n in ast.walk(e) if isinstance(n, ast.Call)}
        found.append((calls, orelse))
    check(len(found) == 1, "there is exactly one `if AREA_NAME:` spawn branch",
          f"{len(found)}")
    calls, orelse = found[0] if found else (set(), set())
    check("spawn_population" in calls,
          "it calls spawn_population when an area is named")
    check("spawn_enemy" in orelse,
          "and the global enemy is in its ELSE, so the two can never both fire")

    # NEGATIVE CONTROL: make them siblings rather than alternatives, which is
    # the shape of the bug, and require the check to notice.
    # The indentation is part of the pattern, so this literal is pinned to
    # where the branch lives: it moved from inside handle()'s 0x0090 arm (24
    # columns) to module scope inside _handle_request_players() (4) when that
    # arm's body was hoisted, and the replace stopped matching until re-aimed.
    broken = src.replace("    elif SPAWN_ENEMY:",
                         "    if SPAWN_ENEMY:")
    ok = False
    if broken != src:
        for node in ast.walk(ast.parse(broken)):
            if (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                    and node.test.id == "AREA_NAME"):
                ok = not any(
                    getattr(n.func, "id", "") == "spawn_enemy"
                    for e in node.orelse for n in ast.walk(e)
                    if isinstance(n, ast.Call))
    check(ok, "and turning that elif into a second `if` makes the check go red "
              "-- both bodies would then spawn and nothing would say so")

    # The set rules must run at STARTUP, not at instance load: a run that dies
    # on the fourth of five bodies has already put three in the world.
    main_fn = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    check(any(isinstance(n, ast.Call)
              and getattr(n.func, "id", "") == "area_population"
              for n in ast.walk(main_fn)),
          "main() resolves the population at startup, so a bad row costs a "
          "refusal rather than a client run")


def section4():
    """A vault-emitted def_NNNN row -- no name, by design -- SPAWNS.

    npcdefs.py deliberately never emits a name ("a name comes from a rendered
    nameplate or it does not exist"), and until 2026-08-16 the spawn path
    indexed `npc["name"]` bare, so every vault row threw inside instance
    bring-up -- where the harness still reported PASS and the map readback
    stayed green, the exact silent shape section 2b documents
    (studies/isle/PLAN.md gap 2). The fallback label is the npc row's own key:
    commit the id, resolve the string at run time.
    """
    print("\n4. a nameless def_NNNN row spawns, labelled by its own key")
    # Shaped exactly like npcdefs.to_toml's output: ids and numbers, no name.
    NPC_KEY = "def_1470"
    npc_row = {"definition": 1470, "file_id": 116698, "model_id": 116698,
               "scale": 0x3F800000, "flags": 0, "profession": 5, "level": 20,
               "move_speed": 1.0, "enc_name": [0x0101, 0x0102, 0x0103]}
    spawn_row = {"area": AREA, "npc": NPC_KEY, "agent_id": 21, "definition": 1470,
                 "x": 7.0, "y": 9.0, "enabled": True, "max_health": 96}
    check("name" not in npc_row,
          "the row truly has no name -- so this section can tell the fix "
          "from a fixture that smuggled one in")

    class TwoTables:
        def rows(self, kind):
            return {"s": dict(spawn_row)} if kind == "spawn" else {}

        def get(self, kind, key):
            if kind == "npc" and key == NPC_KEY:
                return dict(npc_row)
            if kind == "spawn":
                return dict(spawn_row)
            raise KeyError((kind, key))

    sent = []

    def send(op, values, why=""):
        sent.append((op, values))

    state = {}
    saved = authsrv.agents.WORLD
    try:
        authsrv.agents.WORLD = TwoTables()
        placed = authsrv.spawn_population(send, state, (0.0, 0.0, 0), conn_id=0,
                                          area=AREA)
    finally:
        authsrv.agents.WORLD = saved

    check(placed == 1, "the body is placed", f"{placed}")
    entry = state.get("agents", {}).get(21)
    check(entry is not None and entry["name"] == NPC_KEY,
          "and its label is the npc key, never a KeyError",
          f"name={entry and entry['name']!r}")
    ops = [op for op, _v in sent]
    check(authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES in ops
          and authsrv.GAME_SMSG_WORLD_CREATE_AGENT in ops,
          "definition and create both went out",
          f"{len(sent)} messages")
    # Section 2b's rule, applied here: encoding through the real codec is the
    # strongest thing checkable without a client, because it is the same codec
    # the server sends through. Every message the spawn emitted must encode.
    codec = Codec()
    bad = []
    for op, values in sent:
        try:
            codec.encode("GAME_SMSG", op, values)
        except Exception as exc:                              # noqa: BLE001
            bad.append((hex(op), str(exc)[:50]))
    check(not bad, "and every emitted message ENCODES through the real codec",
          str(bad) if bad else f"all {len(sent)}")


def section7():
    """SLICE-H11: a spawn row's `weapon_item` is declared and named on the body.

    Retail's create batch gives EVERY body its weapons -- 0x0161 per item and
    a 0x006D [agent, leadhand, offhand] -- not only a henchman's (3,016
    non-party 0x006D across the live corpus; F35). A row without the key
    sends neither, so every earlier fixture is unchanged.
    """
    print("\n7. SLICE-H11: a row's weapon_item rides the body's create as "
          "0x0161 + 0x006D")
    sent = []
    bodies = place({"bare": row(agent_id=20, definition=5),
                    "armed": row(agent_id=21, definition=5,
                                 weapon_item="starter_hammer")}, sent=sent)
    items = [v for op, v, _l in sent if op == authsrv.GAME_SMSG_CREATE_NAMED_ITEM]
    hands = [v for op, v, _l in sent if op == authsrv.GAME_SMSG_NPC_UPDATE_WEAPONS]
    wid = authsrv.SPAWN_WEAPON_ITEM_ID + 21
    check(len(items) == 1 and items[0][0] == wid
          and items[0][1] == authsrv.agents.item_template("starter_hammer")["file_id"]
          and hands == [[21, wid, 0]]
          and bodies[21].get("weapon_item") == "starter_hammer"
          and bodies[20].get("weapon_item") is None,
          "the armed row gets ONE 0x0161 (item id = the base + its agent id, "
          "the hammer's file) and ONE 0x006D [agent, that item, 0]; the bare "
          "row gets neither and carries no weapon_item",
          f"items {[(v[0], v[1]) for v in items]}, hands {hands}")
    codec = Codec()
    bad = []
    for op, values, _l in sent:
        if op in (authsrv.GAME_SMSG_CREATE_NAMED_ITEM,
                  authsrv.GAME_SMSG_NPC_UPDATE_WEAPONS):
            try:
                codec.encode("GAME_SMSG", op, values)
            except Exception as exc:                          # noqa: BLE001
                bad.append((hex(op), str(exc)[:60]))
    check(not bad, "and both encode through the real codec",
          str(bad) if bad else "both encode")


def section5():
    """The party co-loads with every area, so its ids are reserved.

    studies/unitsetup/FINDINGS.md 8 Q9: the set checks of section 1 are
    per-area, and nothing guarded an area row against the ids the PARTY brings
    into the same instance -- player 1, henchman 30/definition 9, hero bodies
    200..206/definitions 10..16. `--area sculpt --hero 1,2,3` is a legal
    command line, and before this guard it was a client run wasted at best and
    a body silently wearing a hero's model at worst. The test enemy's ids are
    the deliberate NON-example: an area REPLACES it (section 3's AST proof),
    so refusing agent 10 or definition 3 would invent a rule.
    """
    print("\n-- section 5: party-reserved ids, the cross-load collision --")

    for a in sorted({r.get("area")
                     for r in content_mod.load().rows("spawn").values()
                     if r.get("area")}):
        rows = authsrv.area_population(a)
        check(rows is not None and len(rows) > 0,
              f"the REAL store's area {a!r} clears the party-reservation "
              f"guard, so the guard guards without refusing what exists",
              f"{len(rows)} rows")

    for kw, why in (
            (dict(agent_id=authsrv.PLAYER_AGENT_ID), "the player's agent id"),
            (dict(agent_id=authsrv.HENCHMAN_AGENT_ID), "the henchman's"),
            (dict(agent_id=authsrv.HERO_AGENT_ID), "the first hero body's"),
            (dict(agent_id=authsrv.HERO_AGENT_ID + 6), "the seventh hero's"),
            (dict(definition=authsrv.HENCHMAN_DEFINITION),
             "the henchman's definition"),
            (dict(definition=authsrv.HERO_DEFINITION + 2),
             "a mid-range hero definition"),
    ):
        check(refuses({"s": row(**kw)}, why),
              f"a row claiming {why} ({kw}) is REFUSED at load, not at spawn")

    got = accepts({"s": row(agent_id=10, definition=3)})
    check(got == ["s"],
          "and the TEST ENEMY's ids are accepted -- an area replaces it, so "
          "reserving agent 10 / definition 3 would refuse a collision that "
          "cannot happen", got)


class Globals:
    """Set authsrv module globals for one block and restore them, whatever
    happens -- `fixture_level_guards` reads the flags main() sets, so section
    8 sets every flag it reads explicitly rather than trusting import-time
    state (SPAWN_ENEMY, for one, is read out of content at import)."""

    def __init__(self, **kw):
        self.kw, self.saved = kw, {}

    def __enter__(self):
        self.saved = {k: getattr(authsrv, k) for k in self.kw}
        for k, v in self.kw.items():
            setattr(authsrv, k, v)

    def __exit__(self, *_exc):
        for k, v in self.saved.items():
            setattr(authsrv, k, v)


PLAIN = dict(AREA_NAME=None, SPAWN_ENEMY=True, PROBE_NAME=None, HENCHMAN=None,
             HENCHMAN_BODY=False, HERO_BODY=False, HERO_IDS=[], HERO_ROWS={},
             HERO_LEVEL=None, HERO_BODY_NPC="hatcher")   # `python authsrv.py`, no flags


def fixture_guard(world=None, hatcher=None, **flags):
    """Run `fixture_level_guards` under PLAIN + `flags`, with `world` as the
    content store and `hatcher` as agents.HATCHER when given. Returns
    ("ok", [(who, level)]) or ("refused", text)."""
    saved_world, saved_hatcher = authsrv.agents.WORLD, authsrv.agents.HATCHER
    try:
        if world is not None:
            authsrv.agents.WORLD = world
        if hatcher is not None:
            authsrv.agents.HATCHER = hatcher
        with Globals(**dict(PLAIN, **flags)):
            try:
                return "ok", authsrv.fixture_level_guards()
            except authsrv.PopulationError as exc:
                return "refused", str(exc)
    finally:
        authsrv.agents.WORLD, authsrv.agents.HATCHER = saved_world, saved_hatcher


def section8():
    """R-SANDBOX (2026-09-24): a content row whose level 0x0056 cannot carry is
    refused at LOAD, not inside send().

    GAME_SMSG 0x0056's level field is a `byte`; the codec raises struct.error
    at 256 or -1 inside send(), handle() catches only the socket errors, and
    the client's session drops partway through the population. The compiler
    (sandbox.HOSTILE_LEVEL_MAX) refuses such a spec, but a hand-written row --
    content/*.toml or a vault overlay -- never met the compiler, and until this
    guard nothing at server load read a level. The range is the WIRE's, read
    off the schema by the server, and pinned here three ways: to the schema
    read independently, to the codec's own width table, and to the compiler's
    constant (the server must not import the harness, so that equality lives
    here). The served-area half sits inside area_population; the fixture half
    (the test enemy, every 0x0056 step of a --probe built as it will fire, the
    henchman's and each hero's body) is fixture_level_guards, which main()
    calls once every flag is final; the last line is create_agent_world's
    ValueError at the send.
    """
    print("\n8. R-SANDBOX: a level past 0x0056's field is refused at load, "
          "naming the row, the level, the range and why")
    lo, hi = authsrv.NPC_LEVEL_RANGE

    # THE RANGE, three ways. (1) the schema read INDEPENDENTLY of the server,
    # and the bound as a LITERAL written here (section 2's rule: a symbol in a
    # test is not a check).
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "schema",
                           "overrides.json"), encoding="utf-8") as fh:
        fields = json.load(fh)["channels"]["GAME_SMSG"]["86"]["fields"]
    payload = [f["type"] for f in fields if f["type"] != "msg_header"]
    check(payload[7] == "byte" and (lo, hi) == (0, 255),
          "0x0056's level field (the eighth payload field) is a `byte` in "
          "schema/overrides.json, and the guard's range is 0..255 -- the literal",
          f"{payload[7]}, {(lo, hi)}")
    # (2) the width through the codec's own table -- red if the schema widens
    # the field and the server does not follow, or the server's range moves
    # while the schema does not.
    from codec import FIXED  # noqa: E402
    check(authsrv.NPC_LEVEL_WIDTH == FIXED[payload[7]]
          and (lo, hi) == (0, (1 << (8 * FIXED[payload[7]])) - 1),
          "the guard's range is that field's width through the codec's FIXED "
          "table: 0..2^(8*width)-1 -- so the schema width and the range cannot "
          "disagree without this going red",
          f"width {authsrv.NPC_LEVEL_WIDTH}, {(lo, hi)}")
    # (3) the compiler's constant. The server never imports toolkit/harness.
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
    import sandbox  # noqa: E402
    check((lo, hi) == (0, sandbox.HOSTILE_LEVEL_MAX),
          "the server's range EQUALS the compiler's HOSTILE_LEVEL_MAX "
          "(toolkit/harness/sandbox.py), so the two cannot drift -- the "
          "equality lives here because the server does not import the harness",
          f"{(lo, hi)} vs 0..{sandbox.HOSTILE_LEVEL_MAX}")
    # THE MECHANISM the guard pre-empts: the same codec the server sends
    # through packs the cap and raises one past it. Every encode here goes
    # through `packs`, which returns the frame or the exception's NAME, so a
    # plant that widens the range makes a check red rather than a traceback
    # with no verdict (this file's own section 0 lesson).
    codec = Codec()
    npc = authsrv.agents.npc_template("hatcher")
    LEVEL_BYTE = 2 + 6 * 4 + 1          # header, six dwords, the profession byte

    def packs(values):
        try:
            return codec.encode("GAME_SMSG",
                                authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES, values)
        except Exception as exc:                              # noqa: BLE001
            return type(exc).__name__

    # LITERALS, not `hi`, wherever a label says 255 or 256 (the verifier's nit
    # of 2026-09-24: two positive controls said '255' and tested the symbol,
    # so a range narrowed to 0..254 left them green under labels that lied).
    at_cap = packs(authsrv.agents.npc_properties(5, dict(npc, level=255)))
    past = packs(authsrv.agents.npc_properties(5, dict(npc, level=256)))
    check(isinstance(at_cap, bytes) and at_cap[LEVEL_BYTE] == 255 and past == "error",
          "the codec packs level 255 with the byte in place and raises "
          "struct.error at 256 -- inside send(), the drop the guard exists to "
          "pre-empt", f"at the cap: {at_cap if not isinstance(at_cap, bytes) else at_cap[LEVEL_BYTE]}, "
                      f"past it: {past}")

    # A SERVED ROW: at the cap accepted; one past it and -1 refused, and the
    # refusal NAMES the row, the level, the range and why.
    check(accepts({"a": row(agent_id=20, definition=5, level=255)}) == ["a"],
          "a served row at 255 (the literal) is ACCEPTED -- the cap is "
          "inclusive, the positive control every refusal below needs")
    msg = refusal({"a": row(agent_id=20, definition=5, level=hi + 1)})
    check(msg is not None and "'a'" in msg and "256" in msg and "0..255" in msg
          and "0x0056" in msg and "send()" in msg
          and "from its template" not in msg,
          "a served row at 256 is REFUSED at load, naming the row, the level, "
          "the range 0..255, 0x0056 and the send() drop -- and not a template, "
          "since the level is the row's own", msg)
    msg = refusal({"a": row(agent_id=20, definition=5, level=-1)})
    check(msg is not None and "'a'" in msg and "-1" in msg and "0..255" in msg,
          "...and at -1 (the codec packs the byte unsigned)", msg)
    # NOT AN INTEGER: the codec's '<B' raises on 20.0 exactly as on 256, so
    # the guard refuses it too, and says which fault it is.
    float_past = packs(authsrv.agents.npc_properties(5, dict(npc, level=20.0)))
    msg = refusal({"a": row(agent_id=20, definition=5, level=20.0)})
    check(float_past == "error" and msg is not None and "not an integer" in msg,
          "a level of 20.0 is refused as 'not an integer' -- the codec raises "
          "struct.error on a float too", f"codec: {float_past}; {msg}")

    # THE TEMPLATE FALLBACK: the create path sends
    # `row.get("level", npc.get("level", 0))`, so a row with NO level takes its
    # template's, and the guard computes the same expression -- a template at
    # 300 refuses the row NAMING the template; the row's own valid level wins.
    tall = {"tall": dict(authsrv.agents.WORLD.get("npc", "hatcher"), level=300)}
    msg = refusal({"a": row(agent_id=20, definition=5, npc="tall")}, npc=tall)
    check(msg is not None and "'a'" in msg and "300" in msg
          and "from its template 'tall'" in msg,
          "a row with NO level whose template sits at 300 is REFUSED naming "
          "the template -- the effective level is the create path's own "
          "expression, the row's else its template's", msg)
    check(accepts({"a": row(agent_id=20, definition=5, npc="tall", level=20)},
                  npc=tall) == ["a"],
          "...and a row's own valid level WINS over its template's 300 -- "
          "accepted, so the fallback is a fallback and not a second bound")
    msg = refusal({"a": row(agent_id=20, definition=5, npc="nobody")})
    check(msg is not None and "'a'" in msg and "'nobody'" in msg,
          "a row naming a template the store does not carry is refused at "
          "load naming it -- spawn_population would have raised inside "
          "instance bring-up, where the harness reports PASS with the body "
          "absent (section 2b's shape)", msg)
    # The guard sits INSIDE area_population, which spawn_population calls
    # before its first send: the create path refuses with nothing on the wire.
    sent = []
    try:
        place({"a": row(agent_id=20, definition=5, npc="tall")}, sent=sent, npc=tall)
        outcome = "accepted"
    except authsrv.PopulationError:
        outcome = "PopulationError"
    except Exception as exc:                                  # noqa: BLE001
        outcome = type(exc).__name__     # the last line's ValueError, under a plant
    check(outcome == "PopulationError" and sent == [],
          "spawn_population over that row refuses at LOAD (PopulationError) "
          "before its FIRST send -- nothing reached the wire",
          f"{outcome}, {len(sent)} sent")

    # THE FIXTURE PATHS, the other half: what a plain `python authsrv.py`
    # declares (the test enemy = agents.HATCHER), a --probe's hatcher, the
    # henchman's body, each hero's body. Every flag read is set explicitly.
    hatcher = authsrv.agents.WORLD.get("npc", "hatcher")
    kind, got = fixture_guard()
    check(kind == "ok" and len(got) == 1 and "test enemy" in got[0][0]
          and got[0][1] == hatcher["level"],
          "a plain server (no area, enemy on, no probe, no henchman, no hero "
          "body) checks exactly ONE path, the test enemy's, at the hatcher "
          "template's level", f"{kind}: {got}")
    kind, got = fixture_guard(hatcher=dict(hatcher, level=300))
    check(kind == "refused" and "test enemy" in got and "300" in got
          and "'hatcher'" in got,
          "the test enemy's template at 300 is REFUSED naming the test enemy "
          "and the hatcher template -- the legacy global spawn sends "
          "agents.HATCHER, whatever the spawn row's `npc` says", got)
    kind, got = fixture_guard(hatcher=dict(hatcher, level=300), AREA_NAME=AREA)
    check(kind == "ok" and got == [],
          "...but with an --area named (and no probe) that same 300 checks "
          "NOTHING: an area replaces the test enemy, and the guard covers "
          "what will be sent, not what exists", f"{kind}: {got}")
    kind, got = fixture_guard(hatcher=dict(hatcher, level=300), SPAWN_ENEMY=False)
    check(kind == "ok" and got == [],
          "...and --no-enemy checks nothing either", f"{kind}: {got}")

    # A --PROBE'S OWN 0x0056 STEPS. The probe modules write raw Step lists from
    # whatever each step names -- the hatcher, a vault def_NNNN row, a literal
    # -- and none passes through create_agent_world, so the guard BUILDS the
    # named probe as run_probe will and checks each sending 0x0056 step's
    # level slot. The verifier's finding of 2026-09-24: until then this branch
    # checked agents.HATCHER alone under any --probe, and main()'s startup line
    # said quest_giver_def's "fixture" fit while its def_1480 sat at 300 in an
    # overlay -- the same mid-session struct.error the guard exists to pre-empt.
    import probes  # noqa: E402
    import probequest  # noqa: E402
    from probebase import Probe, Step  # noqa: E402

    def synthetic(*steps):
        return lambda agent_id, origin: Probe("q?", "p.", list(steps))

    def with_probes(extra, **kw):
        """fixture_guard with `extra` {name: factory} registered in
        probes.PROBES for the call, and probequest's vault-row cache cleared
        before and after so a synthetic template never outlives its check."""
        probequest._VAULT_NPC_CACHE.clear()
        probes.PROBES.update(extra)
        try:
            return fixture_guard(**kw)
        finally:
            for k in extra:
                del probes.PROBES[k]
            probequest._VAULT_NPC_CACHE.clear()

    def step56(values, label="0x0056 step", **kw):
        return Step(0.0, authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES, values, label,
                    "watch", **kw)

    # The positive control on a REAL probe: 'death' (probecombat) declares the
    # hatcher once; under --area the test enemy is not checked, so the walk's
    # line is the only one, at the hatcher's own level.
    kind, got = fixture_guard(AREA_NAME=AREA, PROBE_NAME="death")
    mine = [(w, lv) for w, lv in got if "probe 'death' step " in w]
    check(kind == "ok" and len(got) == 1 and len(mine) == 1
          and mine[0][1] == hatcher["level"] and "/" in mine[0][0],
          "--probe death under --area BUILDS the probe and checks its one "
          "0x0056 step at the hatcher's own level, naming the probe and the "
          "step (index/count) -- the guard reads the step the probe will send",
          f"{kind}: {got}")
    # Both paths when no area is named: the test enemy AND the probe's step --
    # the instance load's `elif SPAWN_ENEMY` never reads PROBE_NAME.
    kind, got = fixture_guard(PROBE_NAME="death")
    check(kind == "ok" and len(got) == 2
          and any("test enemy" in w for w, _l in got)
          and any("probe 'death' step " in w for w, _l in got),
          "...and with no area named, --probe death checks BOTH the test "
          "enemy's hatcher and the probe's own step: a probe does not replace "
          "the test enemy", f"{kind}: {got}")
    # probes.py:359's shape -- a raw literal list, the level a bare number at
    # the eighth slot -- at 300: refused naming the probe, the step and its
    # label, the level and the range.
    raw300 = [25, 116227, 0, 1677721600, 0, 524, 3, 300, "ཧ"]
    kind, got = with_probes(
        {"_lvl_raw": synthetic(step56(raw300, "declare def 25, level 300"),
                                Step(0.0, 0x0057, [25, [116698]], "model", "w"))},
        AREA_NAME=AREA, PROBE_NAME="_lvl_raw")
    check(kind == "refused" and "probe '_lvl_raw' step 1/2" in got
          and "'declare def 25, level 300'" in got and "300" in got
          and "0..255" in got and "refused at load" in got,
          "a probe whose 0x0056 step is a raw literal list with 300 in the "
          "level slot (probes.py:359's shape) is REFUSED at startup naming the "
          "probe, step 1/2, its label, 300 and 0..255", got)
    # At 255 through npc_properties (the other shape): accepted, the log line
    # carrying the literal.
    kind, got = with_probes(
        {"_lvl_cap": synthetic(step56(
            authsrv.agents.npc_properties(5, dict(npc, level=255)), "def 5 at 255"))},
        AREA_NAME=AREA, PROBE_NAME="_lvl_cap")
    check(kind == "ok" and [lv for w, lv in got if "probe '_lvl_cap'" in w] == [255],
          "...and one built by npc_properties at 255 is accepted, the startup "
          "line naming the probe at 255", f"{kind}: {got}")
    # A declared REFUSAL (sends=False) sends nothing, so its level is not
    # checked: the guard covers what will be sent (probebase.Step's flag).
    kind, got = with_probes(
        {"_lvl_ref": synthetic(step56(raw300, "no plan", sends=False))},
        AREA_NAME=AREA, PROBE_NAME="_lvl_ref")
    check(kind == "ok" and got == [],
          "...a step declared sends=False at 300 is NOT checked: a refusal "
          "puts nothing on the wire", f"{kind}: {got}")
    # A probe that cannot be BUILT here (the vault-row shape check_encodable
    # skips) is refused now, naming the error, not at the fire.

    def boom(agent_id, origin):
        raise RuntimeError("no npc row 'def_9999'")
    kind, got = with_probes({"_lvl_boom": boom}, AREA_NAME=AREA,
                            PROBE_NAME="_lvl_boom")
    check(kind == "refused" and "probe '_lvl_boom' cannot be built here" in got
          and "RuntimeError: no npc row 'def_9999'" in got,
          "...a probe whose build raises is REFUSED at startup naming the "
          "probe and the error -- run_probe builds it inside the instance load, "
          "after the client run", got)
    # THE VERIFIER'S REPRODUCTION: quest_giver_def's giver is def_1480, a vault
    # row read at build time through probequest._vault_npc -> npc_template ->
    # agents.WORLD. A store carrying def_1480 at 300 (the hatcher's row
    # re-keyed, so a bare machine has one too) is refused naming the probe and
    # the step; the same row at 20 is accepted at 20.
    for lvl, want in ((300, "refused"), (20, "ok")):
        world1480 = FakeWorld({}, npc={"def_1480": dict(hatcher, level=lvl)})
        kind, got = with_probes({}, world=world1480, AREA_NAME=AREA,
                                PROBE_NAME="quest_giver_def")
        if want == "refused":
            check(kind == "refused" and "probe 'quest_giver_def' step 1/" in got
                  and "def 1480" in got and "300" in got,
                  "quest_giver_def with the store's def_1480 at 300 is REFUSED "
                  "at startup naming the probe, step 1 and 300 -- the vault "
                  "template the old hatcher rule never read", got)
        else:
            check(kind == "ok"
                  and [lv for w, lv in got if "probe 'quest_giver_def'" in w] == [20],
                  "...and at 20 it is accepted at 20, the startup line naming "
                  "the probe's own step rather than a fixture it never sends",
                  f"{kind}: {got}")
    # The henchman's body: its template's own level.
    world = FakeWorld({}, npc=tall)
    kind, got = fixture_guard(world=world, HENCHMAN="tall", HENCHMAN_BODY=True)
    check(kind == "refused" and "henchman" in got and "'tall'" in got and "300" in got,
          "--henchman tall --henchman-body with tall at 300 is REFUSED naming "
          "the henchman's body and its template", got)
    kind, got = fixture_guard(world=world, HENCHMAN="tall", HENCHMAN_BODY=False)
    check(kind == "ok" and not [w for w, _l in got if "henchman" in w],
          "...and --henchman tall WITHOUT --henchman-body checks no henchman "
          "(no body, no 0x0056; the roster row's level is another message's)",
          f"{kind}: {got}")
    kind, got = fixture_guard(world=world, HENCHMAN="hatcher", HENCHMAN_BODY=True)
    check(kind == "ok" and [lv for w, lv in got if "henchman" in w] == [hatcher["level"]],
          "...and the hatcher's body is accepted at its own level",
          f"{kind}: {got}")
    # Each hero's body: the party row's level, else --hero-level, else the
    # body template's -- hero_body_create's own expression.
    kind, got = fixture_guard(world=world, HERO_BODY=True, HERO_IDS=[1],
                              HERO_ROWS={1: {"level": 300}})
    check(kind == "refused" and "hero 1" in got and "300" in got
          and "from its template" not in got,
          "--hero 1 --hero-body with the party row's level at 300 is REFUSED "
          "naming hero 1 (the row's own level, so no template named)", got)
    kind, got = fixture_guard(world=world, HERO_BODY=True, HERO_IDS=[1],
                              HERO_ROWS={}, HERO_LEVEL=300)
    check(kind == "refused" and "hero 1" in got and "300" in got,
          "...--hero-level 300 with no row is refused too (it feeds the body's "
          "0x0056 as well as prop 36)", got)
    kind, got = fixture_guard(world=world, HERO_BODY=True, HERO_IDS=[1],
                              HERO_ROWS={1: {"level": 20}}, HERO_LEVEL=300)
    check(kind == "ok" and [lv for w, lv in got if "hero 1" in w] == [20],
          "...the party row's 20 WINS over --hero-level 300: accepted at 20",
          f"{kind}: {got}")
    kind, got = fixture_guard(world=world, HERO_BODY=True, HERO_IDS=[1],
                              HERO_ROWS={}, HERO_LEVEL=None, HERO_BODY_NPC="tall")
    check(kind == "refused" and "hero 1" in got and "from its template 'tall'" in got,
          "...and with neither, the body template's 300 is refused naming the "
          "template", got)
    kind, got = fixture_guard(world=world, HERO_BODY=False, HERO_IDS=[1],
                              HERO_ROWS={1: {"level": 300}})
    check(kind == "ok" and not [w for w, _l in got if "hero" in w],
          "...and without --hero-body a hero at 300 is not checked: no body, "
          "no 0x0056 (0x003A/0x003B carry its ranks under their own bound)",
          f"{kind}: {got}")

    # THE LAST LINE: create_agent_world refuses a level past the field with a
    # ValueError naming the agent, the definition and the level, before the
    # send -- and at the cap it sends the byte in place.
    sent = []
    try:
        bodies = place({"a": row(agent_id=20, definition=5, level=255)}, sent=sent)
        placed = "placed"
    except Exception as exc:                                  # noqa: BLE001
        # A range narrowed below 255 refuses the positive control at load;
        # that is a RED check here, never a bare traceback with no verdict.
        bodies, placed = {}, f"{type(exc).__name__}: {exc}"
    props = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES]
    blob = packs(props[0]) if props else "no definition sent"
    check(placed == "placed" and len(props) == 1 and props[0][7] == 255
          and isinstance(blob, bytes) and blob[LEVEL_BYTE] == 255,
          "a body at 255 (the literal) goes out through create_agent_world "
          "with the level byte in place -- nothing changes for a level that fits",
          f"{placed}; {len(props)} definition(s), level {props and props[0][7]}, "
          f"packed: {blob if not isinstance(blob, bytes) else blob[LEVEL_BYTE]}")
    late, why = [], None
    if 20 in bodies:
        entry = dict(bodies[20], npc=dict(bodies[20]["npc"], level=256))
        try:
            authsrv.create_agent_world(
                lambda op, vals, label="", **kw: late.append((op, vals)),
                {"agents": {}}, 20, entry, "probe")
        except ValueError as exc:
            why = str(exc)
    check(why is not None and "agent 20" in why and "definition 5" in why
          and "256" in why and late == [],
          "the same entry at 256 raises ValueError from create_agent_world "
          "naming the agent, the definition and the level, with NOTHING sent "
          "-- the codec's bare struct.error inside send() named none of them",
          f"{why!r}; {len(late)} sent")
    # ...and its tail names the MOMENT: the startup guards' text ends "refused
    # at load instead", which printed mid-population would name the wrong one
    # (the verifier's nit of 2026-09-24).
    check(why is not None and "refused at the send" in why
          and "refused at load" not in why,
          "the last line's text says it fired AT THE SEND with nothing sent, "
          "not 'refused at load instead' -- the startup guards' tail, which is "
          "false by the time create_agent_world runs", why)

    # STRUCTURAL: the served-area half is INSIDE area_population (so main()'s
    # startup call, section 3, runs it), main() calls the fixture half, and
    # the create path holds the last line. Section 3's AST idiom, on section
    # 3's own parse.
    _src, tree = authsrv_source()
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    def calls(fn, name):
        return any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == name
                   for n in ast.walk(fns[fn]))
    check(calls("area_population", "wire_level_problem"),
          "area_population itself calls wire_level_problem -- the served-area "
          "half sits beside the other set checks main() runs at startup")
    check(calls("main", "fixture_level_guards"),
          "main() calls fixture_level_guards, so the fixture paths are refused "
          "at startup and not at the first client's spawn")
    check(calls("create_agent_world", "wire_level_problem"),
          "and create_agent_world holds the last line")


def main():
    print("=" * 70)
    print("POPULATION -- what lives in an authored area")
    print("=" * 70)
    section0()
    section1()
    section2()
    section2b()
    section3()
    section4()
    section5()
    section6()
    section7()
    section8()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
