"""What may be spawned into an area, and at what coordinates a body may stand.

GEOMETRY AND VALIDATION, NO SENDS. Nothing here opens a socket, names an opcode
or touches `state["agents"]`: the spawn messages themselves live beside the other
sends in `authsrv.py` (`spawn_enemy`, `spawn_population`, `create_agent_world`).
What this module owns is the part that answers a question before any of that runs
-- is this probe pairing the one the run means to measure, and is the ground under
this coordinate ground at all.

WHY IT IS A MODULE. Both halves are pure functions over a navmesh and a pair of
numbers, and both are exercised offline: `test_population.py` builds its own
`PathingMap`-shaped object and never launches anything, `test_agentlife.py` calls
`spawn_probe_warning` four times with no server at all. They were sitting in the
middle of the send path, which is the one place a reader looking for "where does
the body end up" would not think to look.

WHAT STAYED BEHIND, because the referents of several comments here are there:

  * `ENEMY_OFFSET` (`authsrv.py:10790`) and `PROF_WARRIOR` (`:2594`) -- both are
    read from `content/world.toml` at import time and both are read as
    `authsrv.<NAME>` by tests, so they stay at module scope in `authsrv.py` and
    arrive here as keyword arguments AT CALL TIME. They are threaded with no
    default value on purpose: a default is evaluated at `def` time and would
    freeze the value a test had rebound, which is the exact failure the
    forwarding wrappers exist to prevent.
  * `ENEMY_COUNT` / `ENEMY_COUNT_MAX` (`authsrv.py:19647-19657`) and `AREA_NAME`
    (`:19673`) -- `--enemies N` and `--area` are `main()`-plumbed flags.
  * `area_population`, `PopulationError` and `spawn_population` -- the set checks
    over an area's spawn rows stay in `authsrv.py`. `toolkit/mapdata/deploy.py`'s
    `spawn_row_count` is a deliberate SECOND reader of `area_population`'s two
    filter predicates, and `test_deploy.py:618` proves the two agree by finding
    the `area_population` FunctionDef in `authsrv.py`'s own syntax tree and
    asserting `'area'` and `'enabled'` appear in its body. A forwarding shim has
    neither literal in it, so that check cannot follow the function out of the
    file without being re-aimed first.

Standard library only, and no import of the server: this module must not import
`authsrv`, which runs as `__main__` and would be loaded a second time.
"""
import math

# How far from its declared spot a body may be nudged to find ground, and how
# fine the search is. A NUDGE IS REPORTED, NEVER SILENT: an author who wrote a
# coordinate deserves to know it was not usable, and "it appeared 400 units
# from where I put it" is otherwise indistinguishable from a placement bug.
PLACE_SEARCH_RADIUS = 480.0
PLACE_SEARCH_STEP = 48.0


def spawn_probe_warning(probe, spawn_set, spawn_out_of_band=False, *, PROF_WARRIOR):
    """profession_spawn without --spawn-profession measures the wrong thing.

    The probe's question is what the skills panel does when a custom
    profession arrived IN the burst; without the flag the session spawns at
    the default (profession 1), which run 2 already measured. A warning, not
    a refusal -- and it must NOT fire when the flag is given, because a
    warning that fires either way is noise (same rule as the enemy warning).
    """
    if probe == "profession_spawn" and not spawn_set:
        return ("WARNING: --probe profession_spawn without --spawn-profession: "
                f"this session spawns at the default profession {PROF_WARRIOR}, "
                "which run 2 already measured. The probe's question needs "
                "--spawn-profession 12, with a control session at "
                "--spawn-profession 3 first (studies/profession/RUNS.md s8).")
    # profession_panel exists BECAUSE 0x00B7 cannot carry a custom id. Pairing
    # it with an out-of-band --spawn-profession puts exactly that message in
    # the burst, so the client dies at map load ~3.4 s in and the probe's own
    # steps never run -- a whole session spent re-measuring a result we have
    # twice. Refused rather than warned: there is no reading of that pair that
    # answers the probe's question.
    if probe == "profession_panel" and spawn_out_of_band:
        raise SystemExit(
            "--probe profession_panel with an out-of-band --spawn-profession "
            "is refused. The burst's 0x00B7 would carry the custom id and the "
            "client asserts `profession < arrsize(s_profChapter)` "
            "(ConstChar.cpp:1296) ON ARRIVAL -- MEASURED twice, at +3.42 s and "
            "+3.39 s, both dead before any UI action. This probe delivers the "
            "custom id on 0x00A6 itself, which lands silently; run it with no "
            "--spawn-profession at all (studies/profession/RUNS.md s10.5).")
    return None


def enemy_spots(state, ox, oy, n, *, ENEMY_OFFSET):
    """`n` distinct spots near the player, walkable ones first -- the eight
    compass points at ENEMY_OFFSET's distance, then the same eight at one and
    a half times it. The plain offset when there is no navmesh (a normal
    outcome: the archive is the player's own install). Never fewer than `n`
    points: a spot the mesh refuses is still returned, last, and the spawn
    line says so."""
    d = ENEMY_OFFSET[0]
    ring = [(d, 0), (0, d), (-d, 0), (0, -d), (d, d), (-d, d), (d, -d), (-d, -d)]
    cands = [(ox + dx, oy + dy) for dx, dy in ring] + \
            [(ox + 1.5 * dx, oy + 1.5 * dy) for dx, dy in ring]
    pm = state.get("pathmap")
    if pm is None:
        return cands[:n]
    good = [c for c in cands if pm.walkable(c[0], c[1])]
    bad = [c for c in cands if not pm.walkable(c[0], c[1])]
    return (good + bad)[:n]


def place_on_mesh(pm, x, y, what):
    """The nearest spot the navmesh calls ground, or None, and how far it moved.

    Returns `(x, y, moved)`. This exists because of rung (I): until 2026-08-13
    the server on an authored map held either ArenaNet's geometry for the same
    map id or no mesh at all, so a placement check here would have been
    measuring the wrong map or nothing. With the mesh actually loaded, an
    authored area can be sparse -- the sculpt map is 1.2% walkable by area --
    and a coordinate an author picked off a Blender screenshot very often is
    not standable.

    None means REFUSE. A body placed off-mesh stands somewhere the server's own
    collision says does not exist, and everything downstream reasons about it
    wrongly; a missing NPC is a smaller lie than a present one nobody can reach.
    """
    if pm is None:
        return x, y, 0.0                       # no mesh: nothing to check against
    if pm.walkable(x, y):
        return x, y, 0.0
    step = PLACE_SEARCH_STEP
    r = step
    while r <= PLACE_SEARCH_RADIUS:
        n = max(8, int(2 * math.pi * r / step))
        for i in range(n):
            a = 2.0 * math.pi * i / n
            cx, cy = x + r * math.cos(a), y + r * math.sin(a)
            if pm.walkable(cx, cy):
                return cx, cy, r
        r += step
    return None
