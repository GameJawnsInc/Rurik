r"""The assembly resolver: wire -> file closure, and the COMPOSITED rule
derived rather than assumed.

    python toolkit/mapdata/test_unitassembly.py

THE HEADLINE IS THE ACCEPTANCE NUMBER: the three keyed live captures' 54
pooled definitions ALL resolve to closed, geometry-complete file sets
through the committed resolver -- every referenced id addressable via
`file_id_table(raw=True)`, every walked container decoded, 1,393 distinct
files. Closure is OUR assertion (the client tolerates what the resolver
refuses to pass over), so 54 green resolutions are 54 real checks.

THE CHECK THAT EARNED THE RUNG is the COMPOSITED cross-check, measured from
the archive bit against wire presence of 0x0057 -- every count TRI-VALUED
(with FA0 / without / unreadable), all three measured in one tuple check
per population, because the first version printed its "reversed rule" as
f-string arithmetic that was 0 by construction and wrong exactly when
has_geometry is None; the U4 review caught it. Capture 20260807T143055
alone: 8/8 0x0056-only shells CARRY geometry (measured reverse 0,
unreadable 0), 36/36 with-0x0057 shells LACK it (reverse 0), 33/33
distinct model ids carry it. Pooled over three captures: 11/11, 43/43
per-definition, 40/40 distinct -- and `needs_body` equals wire 0x0057
presence on all 54, which is the only check covering the seven
needs_body definitions outside 143055. The unitmodels SS5.4 triple
8/8-36/36-43/43 is reproduced with its populations NAMED: the first two
are capture 143055; the third counted DEFINITIONS pooled, not model ids
-- its noun was wrong, and this file is where the reconciliation is
pinned. Independently, the FA1 flag bit agrees with FA0-absence on all
161 FA1 carriers the closures touch (`composited_violations()` empty; U1
measured the same equivalence at 14,571/14,571 archive-wide).

THE VISITED SET has its own fixture, because the corpus cannot exercise
it: the live units' FA8 graph is acyclic and every chain terminates at
depth 1, so recursion-with-visited and an unguarded walk are green-
indistinguishable on real data (the review mutation-tested it). Section
0b feeds the resolver a synthetic A<->B link cycle with a self-loop
through a pre-filled facts cache under a call budget: remove the visited
set and the budget turns the hang into a red check.

THE ORIGIN GATE is proved in both directions on synthetic capture
directories: two live-stamped-and-corroborated captures pool (positive
control), a live+ours mix REFUSES naming both origins, ours-only against a
live expectation refuses, and UNKNOWN refuses (it is not a synonym for
either -- `origin.py`'s whole point). And npcdefs' 0x0057-disagreement
refusal is FIRED on purpose through the decode seam: an injected
conflicting repeat must make `read()` refuse naming the definition and
both lists.

THE NAMED FIRST CASE: the hatcher pair (definition 1471 = shell 116228 +
body 116703) with its full 232-file resolved set pinned id-by-id, the worm
(1442 = 116366, 0x0056-only) beside it at 75 files -- and the content-row
entry (`content/npcs.toml` `npc.hatcher` / `npc.lakeside_worm`) must
resolve to the IDENTICAL sets through the same path, which is what lets our
server serve a definition whose ids come from content rows.

Sections 2-4 need the vault (study archive; live captures); each declares
its skips and the floor takes a vault-less run red -- a resolver checked
against nothing is the failure checks.py exists for.
"""

import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
import checks  # noqa: E402
from mapchunks import dependency_pair  # noqa: E402
import mdlrefs  # noqa: E402
import origin  # noqa: E402
import unitassembly  # noqa: E402  (for the _Facts fixture in section 0b)
from unitassembly import (AssemblyError, Resolver, UnitDef,  # noqa: E402
                          definitions_from_captures, require_one_origin,
                          ROLE_LINK, MODEL_ROLES, ALL_ROLES)

# ---------------------------------------------------------------------------
# Pinned literals. MEASURED 2026-08-16 through the committed module against
# the study archive (build 38797) and the three keyed live captures; written
# as literals rather than computed, because a symbol appearing in a test
# file is not a check (the test_agentlife section-9 lesson).
# ---------------------------------------------------------------------------

CAPTURES = ("20260807T133758", "20260807T143055", "20260810T235916")
POOLED_DEFS = 54
POOLED_FILES = 1393
POOLED_ROLES = {"shell": 32, "body": 40, "link": 134, "texture": 113,
                "sound": 241, "audio": 830, "fad": 8}
MULTI_ROLE = (16271, 116225, 116227, 116228, 128436)   # shells that are
#                                                        also FA8 links
SIZE_MIN, SIZE_MED, SIZE_MAX = (3, 1400), (158, 1470), (233, 1482)
POOLED_NULL_SLOTS = 2
FA1_CARRIERS = 161
LINKS_DISTINCT = 134

# capture 20260807T143055 alone (the unitmodels SS5.4 first two figures)
C55_DEFS, C55_ONLY56, C55_WITH57, C55_MODELS = 44, 8, 36, 33
# pooled (the third figure's real population, plus its distinct-model form)
POOLED_ONLY56, POOLED_WITH57, POOLED_MODELS = 11, 43, 40
TWO_BODY_DEFS = {1496: (116759, 116760), 1497: (116759, 116760)}

HATCHER_DEF, HATCHER_SHELL, HATCHER_BODY = 1471, 116228, 116703
WORM_DEF, WORM_SHELL = 1442, 116366
HATCHER_ROLES = {"shell": 1, "body": 1, "link": 15, "texture": 3,
                 "sound": 44, "audio": 168}
WORM_ROLES = {"shell": 1, "texture": 5, "sound": 16, "audio": 53}
HATCHER_IDS = (
    8197, 15018, 27951, 27952, 27953, 27954, 27956, 27957, 27958, 27959,
    27961, 27962, 27963, 27964, 27966, 27967, 27968, 27969, 27971, 27972,
    27973, 27974, 27976, 27977, 27978, 27979, 28291, 28292, 28293, 28294,
    28296, 28297, 28298, 28299, 28301, 28302, 28303, 28304, 28306, 28307,
    28308, 28309, 28311, 28312, 28313, 28314, 28316, 28317, 28318, 28319,
    29055, 29056, 29057, 29058, 29060, 29061, 29062, 29063, 39848, 39849,
    39850, 39851, 41510, 41511, 41512, 41513, 41515, 41516, 41517, 41518,
    41520, 41521, 41522, 41523, 41525, 41526, 41527, 41528, 41530, 41531,
    41532, 41533, 41535, 41536, 41537, 41538, 41540, 41541, 41542, 41543,
    41545, 41546, 41547, 41548, 52176, 52518, 53607, 66614, 73940, 81578,
    81579, 81580, 81581, 81582, 81584, 81585, 81586, 81587, 81588, 81589,
    81590, 81591, 81592, 81593, 81594, 81595, 81596, 81597, 81598, 81602,
    81603, 81604, 81605, 81608, 81609, 81610, 81611, 81613, 85790, 85791,
    85794, 85795, 85797, 85798, 85801, 85802, 85803, 85804, 85805, 85806,
    85832, 85833, 85836, 85837, 86308, 87242, 87333, 91509, 91510, 91511,
    91512, 91514, 91515, 91516, 91517, 91582, 91583, 91584, 91585, 91588,
    91589, 96978, 106310, 106311, 107184, 107185, 107186, 107187, 107188,
    107189, 107190, 107191, 107192, 107193, 107220, 107221, 107222, 107223,
    107224, 107225, 107226, 107227, 108085, 109464, 116228, 116699, 116701,
    116703, 117797, 158828, 169533, 192861, 192862, 192863, 192864, 192865,
    192866, 192867, 192868, 192869, 192870, 192871, 192872, 192873, 192874,
    192875, 192876, 192877, 192878, 192879, 192880, 192881, 192882, 192883,
    192884, 192885, 192886, 192887, 192888, 192889, 192890, 192891, 202023,
    222933, 222934, 222935, 222936, 222949, 283676, 283677, 283678, 283680,
)
WORM_IDS = (
    8399, 9484, 42816, 51649, 72048, 79810, 79811, 79812, 79813, 79814,
    79823, 79824, 79825, 79826, 79827, 79829, 79830, 79831, 79832, 79834,
    79835, 79836, 79837, 79838, 80399, 80400, 80401, 80402, 80403, 83206,
    87264, 87265, 87266, 87267, 87268, 89724, 89725, 89726, 89727, 89728,
    96711, 96712, 96713, 96714, 96715, 96717, 96718, 96719, 96723, 96724,
    96725, 96726, 96727, 96728, 96729, 96730, 96731, 96732, 96733, 96734,
    96735, 97695, 116363, 116365, 116366, 141231, 141232, 141233, 141234,
    141235, 141236, 141237, 285588, 285589, 285590,
)


class _StubDef:
    """The npcdefs.Definition surface from_npcdef reads, built locally so
    section 0 runs without the vault or the authsrv import."""

    def __init__(self, index, file_id, model_ids, declared=True):
        self.index = index
        self.payload = (file_id, 0, 0x64000000, 0, 8, 1, 0, ()) \
            if declared else None
        self.model_ids = model_ids

    @property
    def declared(self):
        return self.payload is not None


def section0(check):
    print("\n== section 0: UnitDef construction (no vault) ==")
    check(MODEL_ROLES < ALL_ROLES and len(MODEL_ROLES) == 4
          and len(ALL_ROLES) == 8,
          "four walked roles inside eight total")

    u = UnitDef.from_content_row(
        "hatcher", {"file_id": 116228, "model_id": 116703})
    check(u.file_id == 116228 and u.model_ids == (116703,)
          and u.source == "content:hatcher",
          "a content row with file_id + model_id becomes shell + one body")
    u = UnitDef.from_content_row("worm", {"file_id": 116366})
    check(u.model_ids == (),
          "a row without model_id resolves 0x0056-only -- the worm's "
          "deliberate absence is preserved, never invented")
    try:
        UnitDef.from_content_row("broken", {"model_id": 5})
        check(False, "refusal: a row without file_id")
    except AssemblyError:
        check(True, "refusal: a row without file_id")
    try:
        UnitDef(None)
        check(False, "refusal: a non-integer shell file id")
    except AssemblyError:
        check(True, "refusal: a non-integer shell file id")

    u = UnitDef.from_npcdef(_StubDef(1471, 116228, (116703,)))
    check(u.definition == 1471 and u.file_id == 116228
          and u.model_ids == (116703,),
          "from_npcdef takes payload[0] and the FULL model_ids list")
    u = UnitDef.from_npcdef(_StubDef(1442, 116366, None))
    check(u.model_ids == (),
          "from_npcdef: model_ids None (no 0x0057 ever seen) becomes ()")
    try:
        UnitDef.from_npcdef(_StubDef(9, 1, (), declared=False))
        check(False, "refusal: an undeclared definition has no file id")
    except AssemblyError:
        check(True, "refusal: an undeclared definition has no file id")


def _model_facts(links, has_geometry):
    """A synthetic model-file _Facts: type-2, one sequence, FA8 links only."""
    f = unitassembly._Facts()
    f.size, f.ffna = 64, 2
    f.has_geometry = has_geometry
    f.composited = not has_geometry
    f.seq_count = 1
    f.refs = ({mdlrefs.LINK_CHUNK:
               mdlrefs.RefList([dependency_pair(l) for l in links])}
              if links else {})
    return f


class _BoundedResolver(Resolver):
    """No archive underneath: the table and the facts cache ARE the
    fixture. The call budget is what turns 'the visited set is gone' into
    a red check instead of a hung suite."""

    def __init__(self, facts_map, budget=50):
        self.ar = None
        self.table = {fid: fid for fid in facts_map}
        self._facts = dict(facts_map)
        self._budget = budget

    def facts(self, fid):
        self._budget -= 1
        if self._budget < 0:
            raise AssemblyError(
                "the walk exceeded its call budget -- unguarded recursion")
        return super().facts(fid)


def section0b(check):
    print("\n== section 0b: the visited set, on a synthetic FA8 cycle ==")
    # The corpus CANNOT exercise this: the 54 live closures' FA8 graph is
    # acyclic and every chain terminates at depth 1 (FINDINGS SS6), so the
    # review's mutation test removed the visited set and the suite stayed
    # green. This fixture is the discriminator: A links B and ITSELF, B
    # links back to A.
    A, B = 900001, 900002
    r = _BoundedResolver({A: _model_facts((B, A), True),
                          B: _model_facts((A,), False)})
    try:
        res = r.resolve(UnitDef(A))
        check(res.closed and set(res.files) == {A, B},
              "an A<->B link cycle with a self-loop terminates and closes "
              "on exactly {A, B} -- remove the visited set and the budget "
              "reddens this instead of hanging the suite")
        check(res.files[A].roles == {"shell", "link"}
              and res.files[B].roles == {"link"},
              "roles accumulate across the cycle: A is shell AND its own "
              "link target")
    except AssemblyError as e:
        check(False, "the cycle walk terminates", str(e))
        check(False, "roles accumulate across the cycle", "walk never "
              "finished")


def _capture_fixture(root, name, lines):
    d = os.path.join(root, name)
    os.makedirs(d)
    with open(os.path.join(d, "wire.jsonl"), "w", encoding="utf-8") as fh:
        for rec in lines:
            fh.write(json.dumps(rec) + "\n")
    return d


def section1(check):
    print("\n== section 1: the origin gate, both directions (no vault) ==")
    with tempfile.TemporaryDirectory() as tmp:
        live_a = _capture_fixture(tmp, "live_a", [
            {"kind": "origin", "origin": "live", "produced_by": "test"},
            {"kind": "segment", "src": "10.0.0.210:63155",
             "dst": "54.164.212.177:6112"}])
        live_b = _capture_fixture(tmp, "live_b", [
            {"kind": "origin", "origin": "live", "produced_by": "test"},
            {"kind": "segment", "src": "10.0.0.210:49155",
             "dst": "54.164.212.177:6112"}])
        ours = _capture_fixture(tmp, "ours", [
            {"kind": "origin", "origin": "ours", "produced_by": "test"},
            {"kind": "key_exchange_ok", "peer": "127.0.0.1:6112"}])
        unknown = _capture_fixture(tmp, "unknown", [{"kind": "note"}])

        # the fixtures must classify as intended, or every check below is
        # about the wrong thing
        kinds = [origin.origin_of(os.path.join(d, "wire.jsonl"))[0]
                 for d in (live_a, live_b, ours, unknown)]
        check(kinds == [origin.LIVE, origin.LIVE, origin.OURS,
                        origin.UNKNOWN],
              "the four fixtures classify live/live/ours/unknown",
              f"got {kinds}")

        check(require_one_origin([live_a, live_b]) == origin.LIVE,
              "POSITIVE CONTROL: two corroborated live captures pool")
        check(require_one_origin([ours], want=origin.OURS) == origin.OURS,
              "and the gate is about agreement with `want`, not a "
              "hardcoded live")
        try:
            require_one_origin([live_a, ours])
            check(False, "refusal: pooling live with ours")
        except AssemblyError as e:
            check("live" in str(e) and "ours" in str(e)
                  and "REFUSING" in str(e),
                  "refusal: pooling live with ours names both origins")
        try:
            require_one_origin([ours])
            check(False, "refusal: an ours capture against a live want")
        except AssemblyError:
            check(True, "refusal: an ours capture against a live want")
        try:
            require_one_origin([live_a, unknown])
            check(False, "refusal: UNKNOWN never pools")
        except AssemblyError:
            check(True, "refusal: UNKNOWN never pools -- it is not a "
                        "synonym for either origin")


def section2(check, r, world):
    print("\n== section 2: the anchors, from content rows ==")
    t0 = time.time()
    hat = r.resolve(UnitDef.from_content_row(
        "hatcher", world.get("npc", "hatcher")))
    check(hat.closed and not hat.problems,
          "the hatcher pair resolves CLOSED from the shipped content row")
    check(hat.needs_body is True,
          "needs_body is DERIVED from the archive: shell 116228 carries no "
          "FA0, so geometry must arrive from elsewhere")
    check(hat.shell.composited is True,
          "and the skeleton's own COMPOSITED bit says the same thing -- "
          "the second, independent witness")
    check(hat.geometry_complete,
          "the declared body completes the geometry")
    body = hat.files[HATCHER_BODY]
    check(body.has_geometry is True and body.composited is None,
          "body 116703 carries FA0 and NO FA1 at all -- the composite "
          "mechanism's other half")
    check(tuple(hat.file_ids()) == HATCHER_IDS,
          f"the full resolved set is the pinned {len(HATCHER_IDS)} ids",
          f"got {len(hat.files)} files")
    check(hat.role_counts() == HATCHER_ROLES,
          f"hatcher roles: {HATCHER_ROLES}", f"got {hat.role_counts()}")
    links = [f for f in hat.files.values() if ROLE_LINK in f.roles]
    check(len(links) == 15 and all(
        f.ffna == 2 and not f.has_geometry and f.composited
        and f.seq_count for f in links),
          "all 15 FA8 links are FA0-less COMPOSITED skeletons with "
          "sequences -- the client's own per-link gate (0x00794917)")
    check(hat.composited_violations() == [],
          "COMPOSITED bit <-> FA0 absence agrees on every hatcher file")

    worm = r.resolve(UnitDef.from_content_row(
        "lakeside_worm", world.get("npc", "lakeside_worm")))
    check(worm.closed and worm.needs_body is False
          and worm.geometry_complete,
          "the worm resolves CLOSED and self-contained: its shell carries "
          "its own FA0, and the content row's missing model_id needs no "
          "invention")
    check(worm.shell.composited is False,
          "worm shell FA1 flag bit 0 is CLEAR -- with the hatcher's set "
          "bit pinned above, the anchors sit on opposite sides of the "
          "rule and the derivation discriminates on this pair. (A "
          "separate hat != worm check was removed by the U4 review: "
          "entailed by these two, it could never fail independently)")
    check(tuple(worm.file_ids()) == WORM_IDS,
          f"the worm's full set is the pinned {len(WORM_IDS)} ids",
          f"got {len(worm.files)} files")
    check(worm.role_counts() == WORM_ROLES,
          f"worm roles: {WORM_ROLES}", f"got {worm.role_counts()}")

    shallow = Resolver(r.ar, table=r.table).resolve(
        UnitDef(HATCHER_SHELL, (HATCHER_BODY,)), deep=False)
    check(set(shallow.files) == set(hat.files),
          "deep=False yields the IDENTICAL file set (facts elided, "
          "membership and closure unchanged)")

    # controls that fail
    bogus = max(r.table) + 1
    res = r.resolve(UnitDef(bogus))
    check(not res.closed and res.problems
          and "unresolved" in res.problems[0][2],
          "CONTROL (must fail): an id outside file_id_table(raw=True) "
          "leaves the set OPEN with the problem named")
    map_fid = sorted(row["file_id"]
                     for row in world.rows("map").values())[0]
    res = r.resolve(UnitDef(map_fid))
    check(not res.closed and any("not the model type" in p[2]
                                 for p in res.problems),
          "CONTROL (must fail): a map file (ffna type 3) as shell is "
          "refused, not walked",
          f"file {map_fid}: {res.problems[:1]}")
    print(f"  ({time.time() - t0:.0f}s)")


def section3(check, r, caps):
    print("\n== section 3: the 54-definition corpus ==")
    t0 = time.time()
    defs = definitions_from_captures(caps)
    check(len(defs) == POOLED_DEFS,
          f"the three captures pool to {POOLED_DEFS} declared definitions",
          f"got {len(defs)}")
    check(all(defs[i].model_ids == TWO_BODY_DEFS[i] for i in TWO_BODY_DEFS),
          "1496/1497 carry TWO bodies each (116759+116760) -- the full "
          "0x0057 list, which model_id alone under-described")

    results = {i: r.resolve(defs[i], deep=False) for i in sorted(defs)}
    n_closed = sum(res.closed for res in results.values())
    check(n_closed == POOLED_DEFS,
          f"THE ACCEPTANCE: {POOLED_DEFS}/{POOLED_DEFS} definitions "
          f"resolve to CLOSED file sets",
          f"{n_closed} closed; open: "
          f"{[(i, res.problems[:2]) for i, res in results.items() if not res.closed][:3]}")
    n_geo = sum(res.geometry_complete for res in results.values())
    check(n_geo == POOLED_DEFS,
          f"and {POOLED_DEFS}/{POOLED_DEFS} are geometry-complete "
          f"(shell or bodies carry the FA0)")

    pooled = {}
    for res in results.values():
        for fid, e in res.files.items():
            pooled.setdefault(fid, set()).update(e.roles)
    check(len(pooled) == POOLED_FILES,
          f"the closures pool to {POOLED_FILES} distinct archive files",
          f"got {len(pooled)}")
    per_role = {role: sum(1 for ro in pooled.values() if role in ro)
                for role in ALL_ROLES}
    check({k: v for k, v in per_role.items() if v} == POOLED_ROLES,
          f"per-role distinct files: {POOLED_ROLES} -- fae_model absent "
          f"from the pinned dict IS the zero-FAE fact (the archive-wide "
          f"population of 6 never intersects these units; a separate "
          f"FAE==0 check was removed by the U4 review as entailed)",
          f"got {per_role}")
    multi = tuple(sorted(f for f, ro in pooled.items() if len(ro) > 1))
    check(multi == MULTI_ROLE,
          "five files carry two roles: shells that are other definitions' "
          "FA8 links", f"got {multi}")

    sizes = sorted((len(res.files), i) for i, res in results.items())
    got = (sizes[0], sizes[len(sizes) // 2], sizes[-1])
    check(got == (SIZE_MIN, SIZE_MED, SIZE_MAX),
          f"set sizes (files, definition): min {SIZE_MIN}, median "
          f"{SIZE_MED}, max {SIZE_MAX}", f"got {got}")
    nulls = sum(res.null_slots for res in results.values())
    check(nulls == POOLED_NULL_SLOTS,
          f"exactly {POOLED_NULL_SLOTS} FA5 null slots across all 54 walks")

    links = sorted(fid for fid, ro in pooled.items() if ROLE_LINK in ro)
    clean = sum(1 for l in links
                if r.facts(l).ffna == 2 and not r.facts(l).has_geometry
                and r.facts(l).composited and r.facts(l).seq_count)
    check(len(links) == LINKS_DISTINCT and clean == LINKS_DISTINCT,
          f"{LINKS_DISTINCT}/{LINKS_DISTINCT} distinct FA8 link targets "
          f"are FA0-less COMPOSITED skeletons with sequences",
          f"{clean} of {len(links)}")

    carriers = violations = 0
    for fid in pooled:
        f = r.facts(fid)
        if f is not None and f.composited is not None:
            carriers += 1
            violations += f.composited != (not f.has_geometry)
    check(carriers == FA1_CARRIERS and violations == 0,
          f"the COMPOSITED bit <-> FA0 absence equivalence holds on all "
          f"{FA1_CARRIERS} FA1 carriers the closures touch",
          f"{carriers} carriers, {violations} violations")

    # the named first case, wire side, and the content-row equivalence
    check(defs[HATCHER_DEF].file_id == HATCHER_SHELL
          and defs[HATCHER_DEF].model_ids == (HATCHER_BODY,),
          f"wire definition {HATCHER_DEF} is the hatcher pair "
          f"{HATCHER_SHELL}+{HATCHER_BODY}")
    check(tuple(results[HATCHER_DEF].file_ids()) == HATCHER_IDS,
          "and its wire-side closure equals the content-row set EXACTLY -- "
          "one resolution path, two id sources")
    check(defs[WORM_DEF].file_id == WORM_SHELL
          and defs[WORM_DEF].model_ids == ()
          and tuple(results[WORM_DEF].file_ids()) == WORM_IDS,
          f"wire definition {WORM_DEF} is the 0x0056-only worm, closure "
          f"equal to the content-row set")

    # The pooled needs_body <-> wire equivalence, as a CHECK rather than a
    # study-doc assertion (the U4 review found it stated in FINDINGS and
    # summary.json but verified for only 47 of 54: the seven with-0x0057
    # definitions outside capture 143055 -- 272, 326, 378, 391, 398, 1484,
    # 1498 -- had needs_body=True asserted nowhere, geometry_complete
    # being satisfiable either way).
    agree = sum(res.needs_body == bool(defs[i].model_ids)
                for i, res in results.items())
    check(agree == POOLED_DEFS,
          f"needs_body (derived from the shell's FA0 alone) equals wire "
          f"0x0057 presence on {POOLED_DEFS}/{POOLED_DEFS} definitions -- "
          f"both directions, including the seven outside capture 143055",
          f"{agree} agree")

    # npcdefs' 0x0057-disagreement refusal, FIRED on purpose (the review
    # found the new guard untested): append a conflicting repeat through
    # the decode seam; read() must refuse naming the definition and BOTH
    # lists, and the seam is restored whatever happens.
    import npcdefs
    import tape
    one = [d for d in caps if d.endswith(CAPTURES[1])]
    real = tape.decode_all

    def sabotaged(events, codec_obj, channel="GAME_SMSG", mask=0,
                  strict=True):
        msgs, receipt = real(events, codec_obj, channel, mask, strict)
        return (msgs + [(0.0, npcdefs.MONSTER_COMPOSITE,
                         [0x57, HATCHER_DEF, [999999]])], receipt)

    refused = None
    tape.decode_all = sabotaged
    try:
        try:
            npcdefs.read(one)
        except npcdefs.NpcDefsError as e:
            refused = str(e)
    finally:
        tape.decode_all = real
    check(refused is not None and str(HATCHER_DEF) in refused
          and "999999" in refused and str(HATCHER_BODY) in refused,
          "CONTROL: an injected disagreeing 0x0057 repeat makes "
          "npcdefs.read REFUSE, naming the definition and both lists",
          f"{(refused or 'NO REFUSAL')[:120]}")

    print(f"  ({time.time() - t0:.0f}s)")
    return defs


def _geo(r, fid):
    """has_geometry, tri-valued and guarded: True/False for a readable
    model container, None when the id does not resolve or the file is no
    model. Counted explicitly in section 4 so a regression FAILS by name
    instead of raising AttributeError off a None facts()."""
    f = r.facts(fid)
    return None if f is None else f.has_geometry


def section4(check, r, caps, defs):
    print("\n== section 4: the COMPOSITED rule, derived and cross-checked ==")
    c55 = [d for d in caps if d.endswith(CAPTURES[1])]
    d55 = definitions_from_captures(c55)
    check(len(d55) == C55_DEFS,
          f"capture {CAPTURES[1]} alone declares {C55_DEFS} definitions",
          f"got {len(d55)}")
    only56 = sorted(i for i, u in d55.items() if not u.model_ids)
    with57 = sorted(i for i, u in d55.items() if u.model_ids)
    check((len(only56), len(with57)) == (C55_ONLY56, C55_WITH57),
          f"split {C55_ONLY56} 0x0056-only / {C55_WITH57} with-0x0057",
          f"got {len(only56)}/{len(with57)}")

    # Every count below is tri-valued and MEASURED -- with FA0 / without /
    # unreadable -- in ONE tuple check per population. The first version
    # printed its "reversed rule" as f-string arithmetic (C55_ONLY56 - a),
    # which is 0 by construction whenever the forward check passes and
    # wrong exactly when has_geometry is None; the U4 review caught it.
    # The complements are not split into second checks the first would
    # entail -- that is the recorded defect class from the other side.
    g = [_geo(r, d55[i].file_id) for i in only56]
    got = (sum(x is True for x in g), sum(x is False for x in g),
           sum(x is None for x in g))
    check(got == (C55_ONLY56, 0, 0),
          f"0x0056-only shells: {C55_ONLY56}/{C55_ONLY56} CARRY FA0; the "
          f"measured reverse (lacking FA0) is 0; unreadable 0",
          f"(with, without, unreadable) = {got}")
    g = [_geo(r, d55[i].file_id) for i in with57]
    got = (sum(x is False for x in g), sum(x is True for x in g),
           sum(x is None for x in g))
    check(got == (C55_WITH57, 0, 0),
          f"with-0x0057 shells: {C55_WITH57}/{C55_WITH57} LACK FA0; the "
          f"measured reverse (carrying FA0) is 0; unreadable 0",
          f"(without, with, unreadable) = {got}")
    models = sorted({m for u in d55.values() for m in u.model_ids})
    g = [_geo(r, m) for m in models]
    got = (len(models), sum(x is True for x in g),
           sum(x is False for x in g), sum(x is None for x in g))
    check(got == (C55_MODELS, C55_MODELS, 0, 0),
          f"{C55_MODELS}/{C55_MODELS} distinct 0x0057 model ids carry FA0 "
          f"(measured reverse 0; unreadable 0)",
          f"(distinct, with, without, unreadable) = {got}")

    # pooled: the SS5.4 triple's third figure, population named
    onlyp = sorted(i for i, u in defs.items() if not u.model_ids)
    withp = sorted(i for i, u in defs.items() if u.model_ids)
    check((len(onlyp), len(withp)) == (POOLED_ONLY56, POOLED_WITH57),
          f"pooled split {POOLED_ONLY56} 0x0056-only / {POOLED_WITH57} "
          f"with-0x0057")
    g = [_geo(r, defs[i].file_id) for i in onlyp]
    got = (sum(x is True for x in g), sum(x is False for x in g),
           sum(x is None for x in g))
    check(got == (POOLED_ONLY56, 0, 0),
          f"pooled 0x0056-only shells: {POOLED_ONLY56}/{POOLED_ONLY56} "
          f"carry FA0 (measured reverse 0; unreadable 0)",
          f"(with, without, unreadable) = {got}")
    per = [[_geo(r, m) for m in defs[i].model_ids] for i in withp]
    got = (sum(all(x is True for x in gs) for gs in per),
           sum(any(x is False for x in gs) for gs in per),
           sum(any(x is None for x in gs) for gs in per))
    check(got == (POOLED_WITH57, 0, 0),
          f"{POOLED_WITH57}/{POOLED_WITH57} pooled definitions with a "
          f"0x0057 have EVERY body carrying FA0 (bodies lacking it 0; "
          f"unreadable 0) -- unitmodels SS5.4's '43/43', whose noun was "
          f"wrong: it counted these DEFINITIONS pooled, not model ids",
          f"(all-with, any-without, any-unreadable) = {got}")
    modelsp = sorted({m for u in defs.values() for m in u.model_ids})
    g = [_geo(r, m) for m in modelsp]
    got = (len(modelsp), sum(x is True for x in g),
           sum(x is False for x in g), sum(x is None for x in g))
    check(got == (POOLED_MODELS, POOLED_MODELS, 0, 0),
          f"{POOLED_MODELS}/{POOLED_MODELS} pooled distinct model ids "
          f"carry FA0 -- the same rule at distinct-model granularity",
          f"(distinct, with, without, unreadable) = {got}")


def main():
    # Floor 57 = the real green run of the review-fixes commit exactly
    # (8 construction + 2 cycle + 6 origin-gate + 16 anchors + 16 corpus +
    # 9 cross-check; the first run's comment mis-stated its own breakdown
    # as 18+14 -- the review counted 17+15, and two entailed checks have
    # since been removed and four added). Nothing here legitimately varies
    # with the sample -- every section either runs whole or declares its
    # vault skip -- so the floor IS the count, and a run that loses even
    # one check is incomplete, not passing.
    led = checks.Ledger("unit assembly: wire -> file closure", floor=57)
    check = checks.adopt(led)

    section0(check)
    section0b(check)
    section1(check)

    import vaultpath
    try:
        dat = os.path.join(
            vaultpath.require_dir("dat_study", why="the assembly corpus"),
            "Gw.dat")
    except SystemExit:
        dat = None
    if dat is None:
        for why in ("the anchors", "the 54-definition corpus",
                    "the COMPOSITED cross-check"):
            led.skip(why, "no study archive in the vault")
        return led.verdict()

    sys.path.insert(0, os.path.dirname(HERE))
    import content
    world = content.load()
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "authsrv"))
    import npcdefs
    # SELECTED BY NAME, not pooled -- and this file already had the constant to
    # do it with (it reaches for CAPTURES[1] in two places). Until 2026-08-17
    # this was the unfiltered glob gated on `len(caps) != 3`, which is the time
    # bomb `npcdefs.live_captures` documents in its own docstring: "the day a
    # FOURTH keyed capture lands, every unfiltered pin goes red at once". It
    # landed that day -- a live Factions capture, the first new keyed capture
    # in a week -- and the prediction was exactly right, in the good way:
    # MEASURED before this fix was kept, by running the old form against the
    # four-capture vault, the file goes RED and names the shortfall --
    #
    #   ONLY 32 OF A DECLARED FLOOR OF 57 CHECKS RAN -- 25 did not execute,
    #   so this run is incomplete rather than passing
    #
    # -- because a declared skip does NOT exempt the floor (checks.py's
    # `ran < floor`). So the guard worked; what was wrong was this call site
    # asking a question whose answer changes when the vault grows. Every number
    # section3 and section4 pin is a fact about THESE THREE captures, so name
    # them: a fourth capture is new evidence for a new check, never a reason
    # for an old one to stop running -- nor to redden a file it says nothing
    # about.
    try:
        caps = npcdefs.live_captures(names=CAPTURES)
    except SystemExit:
        caps = []

    with Archive(dat) as ar:
        r = Resolver(ar)
        section2(check, r, world)
        if len(caps) != len(CAPTURES):
            for why in ("the 54-definition corpus",
                        "the COMPOSITED cross-check"):
                led.skip(why, f"{len(caps)} of {len(CAPTURES)} named "
                              f"capture(s) present")
        else:
            defs = section3(check, r, caps)
            section4(check, r, caps, defs)

    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
