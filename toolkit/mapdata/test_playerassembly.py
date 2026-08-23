r"""The player-assembly rung: a player identity -> a closed archive file set.

    python toolkit/mapdata/test_playerassembly.py

`test_cpsdata.py` already owns the composite TABLE -- its decode closures, the
geometry/texture split, the two-witness shell join and the monster-shell
rejection. This file owns what sits ON it: `playerassembly.py`'s manifest and
the closure walk through `unitassembly.Resolver`, plus the exe-side
cross-witness (`clientscan/composite.py`) that the P2 rung added. The floors
are set from the green run they were measured on, never guessed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks        # noqa: E402
import cpsdata       # noqa: E402
import playerassembly  # noqa: E402
import unitassembly  # noqa: E402

# Floor set from a real green run (34 checks, 2026-08-22).
LEDGER = checks.Ledger("player assembly", floor=34)
check = checks.adopt(LEDGER)

MONSTER_SHELLS = (116228, 116703, 116377, 116366)   # FINDINGS 5 sabotage 5

# ---------------------------------------------------------------- section 1
print("== 1. the sex/slot split is the module's own, and it is disjoint ==")
check(playerassembly.GEOMETRY_SLOTS == {0, 5, 10},
      "geometry slots are {0,5,10} -- SEX_BASE_SLOT (0,5) plus SHARED_SLOT")
check(playerassembly.sex_slots(0) == (0, 1, 2, 3, 4, 10),
      "sex 0 reads its half {0..4} plus the shared slot 10")
check(playerassembly.sex_slots(1) == (5, 6, 7, 8, 9, 10),
      "sex 1 reads {5..9} plus 10 -- the two halves overlap ONLY at 10")
check(set(playerassembly.sex_slots(0)) & set(playerassembly.sex_slots(1))
      == {10}, "so a player's files are its sex's half and the shared slot, "
               "never the other sex's")
check(playerassembly.FACE_TYPE[0] != playerassembly.FACE_TYPE[1]
      and playerassembly.HAIR_TYPE[0] != playerassembly.HAIR_TYPE[1],
      "face and hair are sex-keyed type pairs (11/10, 13/12)")

# ---------------------------------------------------------------- the vault
try:
    import archive
    import vaultpath
    ar = archive.Archive(vaultpath.vault_path("dat_study", "Gw.dat"))
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("every vault section", f"study archive unavailable: {exc}")
    sys.exit(LEDGER.verdict())

table = cpsdata.CompositeTable.load(ar)
tbl = archive.file_id_table(ar, raw=True)
resolver = unitassembly.Resolver(ar, table=tbl)

# ---------------------------------------------------------------- section 2
print("== 2. the manifest picks the right records ==")
player = playerassembly.PlayerDef(0, 1, 0)
seeds, picks, absences = playerassembly.manifest(table, player)
whats = [w for w, _r in picks]
check("shell" in whats and player.file_id == 15018,
      "group 0 / prof 1 / sex 0: the shell record resolves to file 15018",
      f"file_id={player.file_id}")
check(sum(1 for w in whats if w.startswith("base piece")) == 4,
      "all four base pieces (types 3,4,5,6) are picked", f"whats={whats}")
check(any(w == "type 9 (component 7)" for w in whats),
      "type 9 is included by default")
seeds_no9, _p, _a = playerassembly.manifest(
    table, playerassembly.PlayerDef(0, 1, 0), include_type9=False)
check(len(seeds_no9) < len(seeds),
      "include_type9=False drops type 9's files from the seed set")
shell_seeds = [(f, r) for f, r in seeds if r == unitassembly.ROLE_SHELL]
check(len(shell_seeds) == 1 and shell_seeds[0][0] == 15018,
      "exactly one seed carries ROLE_SHELL, and it is the shell geometry")
tex = [f for f, r in seeds if r == unitassembly.ROLE_TEXTURE]
geom = [f for f, r in seeds
        if r in (unitassembly.ROLE_SHELL, unitassembly.ROLE_BODY)]
check(tex and geom and not (set(tex) & set(geom)),
      "texture seeds and geometry seeds are disjoint sets")

# ---------------------------------------------------------------- section 3
print("== 3. an identity CLOSES, and the walk is the monster walk ==")
res, absences = playerassembly.assemble(resolver, table, 0, 1, 0)
check(res.closed and res.unit.file_id == 15018,
      "group 0 / prof 1 / sex 0 closes on shell 15018 -- the archivewrite "
      "arc's hardest wall, resolved as a player identity",
      f"closed={res.closed} problems={res.problems[:3]}")
check(len(res.files) == 173,
      "the closure is 173 files (pinned; a change means manifest or walk "
      "moved)", f"files={len(res.files)}")
check(15018 in res.files
      and unitassembly.ROLE_SHELL in res.files[15018].roles,
      "the shell file carries ROLE_SHELL in the Resolution")

print("== 4. every resolvable identity closes; foreign groups refuse ==")
closed = notclosed = skipped = 0
for t in cpsdata.SHELL_TYPES:
    for g in range(table.n_groups):
        for prof in range(cpsdata.PROFESSIONS):
            for sex in (0, 1):
                try:
                    r, _a = playerassembly.assemble(resolver, table, g, prof,
                                                    sex, shell_type=t)
                except playerassembly.PlayerAssemblyError:
                    skipped += 1
                    continue
                closed += r.closed
                notclosed += not r.closed
check(closed == 40 and notclosed == 0,
      "40/40 resolvable identities close (2 types x 10 home cells x 2 sexes)",
      f"closed={closed} not={notclosed}")
check(skipped == 136,
      "the 136 foreign-group cells REFUSE (the home-group rule, not an error)",
      f"skipped={skipped}")

print("== 5. a monster shell cannot masquerade as a player identity ==")
distinct = table.distinct_file_ids()
for fid in MONSTER_SHELLS:
    check(fid not in distinct,
          f"{fid} is absent from the composite table's file ids",
          "116228 (the hatcher) IS composited and DOES walk, so only the "
          "table can reject it" if fid == 116228 else "")

print("== 6. the terminal-seed and refusal rules the split added ==")
try:
    resolver.resolve_seeds(None, [(15018, unitassembly.ROLE_SOUND)])
    check(False, "a ROLE_SOUND seed must refuse")
except ValueError:
    check(True, "a ROLE_SOUND seed refuses -- the audio closure hangs off a "
                "model's FA6, and a direct seed would half-walk it")
# A texture-role seed is a terminal: resolvable, never walked as a model.
tex_res = resolver.resolve_seeds(
    None, [(tex[0], unitassembly.ROLE_TEXTURE)])
check(tex_res.closed and tex[0] in tex_res.files,
      "a lone ROLE_TEXTURE seed closes -- it is checked and read, not walked "
      "as a model (which would fail its ffna-type gate)")

# ---------------------------------------------------------------- section 7
print("== 7. the exe-side cross-witness (clientscan/composite.py, P2) ==")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import composite
    t = composite.extract()
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("exe cross-witness", f"pinned client unavailable: {exc}")
else:
    check(set(t["geometry_slots"]) == playerassembly.GEOMETRY_SLOTS,
          "s_fileFlags' clear bits (exe) == the assembly's GEOMETRY_SLOTS "
          "(data file) -- disjoint sources, same split",
          f"exe={t['geometry_slots']}")
    check(t["s_components"] == [8, 8, 8, 3, 6, 4, 5, 7, 7, 7, 0, 0, 2, 2, 6,
                               3, 4, 2, 5, 1],
          "s_components is the study's byte-read (17/18 the killed transpose)")
    check(t["base_types"] == [3, 4, 5, 6],
          "the base-piece types match playerassembly.BASE_PIECE_TYPES",
          f"exe={t['base_types']} module={list(playerassembly.BASE_PIECE_TYPES)}")
    check(tuple(t["base_types"]) == playerassembly.BASE_PIECE_TYPES,
          "and they are the SAME four the manifest picks")
    check(t["rects_checked"] == 359 and t["rects_degenerate"] == 88,
          "359 live rects LTRB-closed, 88 degenerate zero-records apart "
          "(the .data zero-fill tail modelled, not mis-read)")
    widths = sorted(w for _s, _sh, w in t["appearance_slot"])
    check(widths == [1, 2, 4, 4, 5, 5, 5, 6],
          "the appearance bitfield tiles 32 bits in the study's widths")
    build = composite.build_of(open(t["exe"], "rb").read())
    check(build == 38797, "the extractor derived build 38797 from the hash, "
                          "never a typed stamp", f"build={build}")

print("== 8. FILE_ID_RESERVED_BIT (bit 31) gates authoring a file id ==")
check(playerassembly.FILE_ID_RESERVED_BIT == 0x80000000,
      "the reserved bit is 0x80000000 (bit 31) -- CpsData:468/:484's "
      "`shr eax,0x1f; not; test al,1`")
# Every composite file id an authored player could reference clears it, so
# authoring is safe by construction.
ids = table.distinct_file_ids()
reserved = [i for i in ids if i & playerassembly.FILE_ID_RESERVED_BIT]
check(not reserved and max(ids) < playerassembly.FILE_ID_RESERVED_BIT,
      "all composite file ids clear bit 31 -- authoring never trips the assert",
      f"n={len(ids)} max={max(ids)} reserved={len(reserved)}")
# But the archive's raw id table DOES carry reserved-bit ids: the bit is a
# real, distinct namespace, not merely hypothetical.
raw = archive.file_id_table(ar, raw=True)
raw_reserved = [i for i in raw if i & playerassembly.FILE_ID_RESERVED_BIT]
check(raw_reserved,
      "the raw file-id table carries reserved-bit ids -- a distinct id "
      "namespace the client's asserts guard the ordinary path against",
      f"{len(raw_reserved)} such ids, max 0x{max(raw_reserved):08X}")
res_rows = {raw[i] for i in raw_reserved}
ord_rows = {raw[i] for i in raw if not (i & playerassembly.FILE_ID_RESERVED_BIT)}
check(all(isinstance(raw[i], int) and raw[i] >= 0 for i in raw_reserved)
      and not (res_rows & ord_rows),
      "they resolve to real MFT rows DISJOINT from the ordinary id space -- a "
      "separate namespace, not aliases", f"e.g. row {raw[raw_reserved[0]]}")
# The authoring guard fires: a manifest whose record carries a reserved-bit
# file id is refused before it becomes a seed.
import cpsdata as _cps


class _FakeRec:
    def __init__(self):
        self.hdr = 0
        self.files = {0: 0x80001234, 5: 0x80001234, 10: 0}

    def base_file(self, sex):
        return self.files.get(_cps.SEX_BASE_SLOT[sex])


saved = table.record
try:
    table.record = lambda g, p, t: _FakeRec()  # every pick returns the reserved id
    raised = False
    try:
        playerassembly.manifest(table, playerassembly.PlayerDef(0, 1, 0))
    except playerassembly.PlayerAssemblyError as ex:
        raised = "reserved" in str(ex).lower()
    check(raised, "manifest REFUSES a record carrying a reserved-bit file id",
          "the tripwire for a corrupt table or a bad mint")
finally:
    table.record = saved

sys.exit(LEDGER.verdict())
