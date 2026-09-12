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
LEDGER = checks.Ledger("test_population", floor=69)   # SLICE-B2 +7 (section 6); from the green run
check = checks.adopt(LEDGER)

AREA = "sculpt"


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
    """Just enough of content.World for area_population: rows() and get()."""

    def __init__(self, spawn):
        self._spawn = spawn

    def rows(self, kind):
        return dict(self._spawn) if kind == "spawn" else {}

    def get(self, kind, key):
        return self._spawn[key]


def row(**kw):
    base = {"area": AREA, "npc": "hatcher", "agent_id": 20, "definition": 5,
            "x": 0.0, "y": 0.0, "enabled": True}
    base.update(kw)
    return base


def accepts(spawn):
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
        return [k for k, _ in rows_for(AREA, FakeWorld(spawn))]
    except authsrv.PopulationError:
        return None


def refuses(spawn, why):
    """True iff area_population refuses this table."""
    return accepts(spawn) is None


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

    def __init__(self, spawn, real):
        self._spawn, self._real = spawn, real

    def rows(self, kind):
        return dict(self._spawn) if kind == "spawn" else self._real.rows(kind)

    def get(self, kind, key):
        if kind == "spawn":
            return self._spawn[key]
        return self._real.get(kind, key)


def place(spawn):
    """Run `spawn_population` over a synthetic table; return state['agents']."""
    saved = authsrv.agents.WORLD
    sent, state = [], {"agents": {}, "pos": (0.0, 0.0), "pathmap": None}
    try:
        authsrv.agents.WORLD = StatWorld(spawn, saved)
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


def section3():
    print("\n3. an area REPLACES the global enemy; the wiring is not optional")
    src = open(authsrv.__file__, encoding="utf-8").read()
    tree = ast.parse(src)

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
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
