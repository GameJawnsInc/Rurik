r"""The player files round-trip through our writers -- BY NAME, not anonymously.

    python toolkit/mapdata/test_playerwrite.py     (~3 min: 40 closures + 180 containers)

studies/playercomposite FINDINGS 4.4 carried "no player component file has
ever been walked, let alone re-emitted" -- and the premise was STALE: U6/U8
ran the writers over the complete flags=515 population archive-wide, so every
player file already round-tripped as an anonymous member of those sweeps.
What no one had done is the JOIN: prove the 40 identities' closure geometry
actually lives inside those proven populations, walk it by name, and make the
identity informative on THESE files with a mutation each way. That is this
file. The delivery wall is untouched and stated: a modified shell 15018 still
cannot be written into the archive (row 11196, compression 8, a 1,029,632 B
reservation) -- the round trip is the WRITERS' half, not the shipping half.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks          # noqa: E402
import cpsdata         # noqa: E402
import playerassembly  # noqa: E402
import unitassembly    # noqa: E402

# Floor set from a real green run (15 checks, 2026-08-23).
LEDGER = checks.Ledger("player write round-trip", floor=15)
check = checks.adopt(LEDGER)

try:
    import archive
    import vaultpath
    import skelfile
    import skelwrite
    import modelwrite
    ar = archive.Archive(vaultpath.vault_path("dat_study", "Gw.dat"))
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("everything", f"study archive unavailable: {exc}")
    sys.exit(LEDGER.verdict())

table = cpsdata.CompositeTable.load(ar)
idt = archive.file_id_table(ar, raw=True)
resolver = unitassembly.Resolver(ar, table=idt)
FA0, FA1 = 0xFA0, 0xFA1
GEOM_ROLES = (unitassembly.ROLE_SHELL, unitassembly.ROLE_BODY)

# ---------------------------------------------------------------- section 1
print("== 1. the 40 closures' geometry, collected by role ==")
geom = set()
shells = {}
closed = 0
for ty in cpsdata.SHELL_TYPES:
    for g in range(table.n_groups):
        for prof in range(cpsdata.PROFESSIONS):
            for sex in (0, 1):
                try:
                    res, _a = playerassembly.assemble(resolver, table, g,
                                                      prof, sex,
                                                      shell_type=ty)
                except playerassembly.PlayerAssemblyError:
                    continue
                closed += res.closed
                for fid, info in res.files.items():
                    if any(r in info.roles for r in GEOM_ROLES):
                        geom.add(fid)
                        if unitassembly.ROLE_SHELL in info.roles:
                            shells.setdefault(fid, ty)
check(closed == 40, "all 40 resolvable identities close (test_playerassembly "
                    "owns the walk; this file consumes it)", f"closed={closed}")
check(len(geom) == 180 and len(shells) == 40,
      "the closures reference 180 distinct geometry files, 40 of them shells",
      f"geometry={len(geom)} shells={len(shells)}")

# ---------------------------------------------------------------- section 2
print("== 2. the population join: every file IS in the writers' proven class ==")
rows = {fid: ar.row(idt[fid]) for fid in geom}
off = [(fid, r.flags) for fid, r in rows.items() if r.flags != 515]
check(not off,
      "all 180 resolve to flags=515 MFT rows -- the exact population U6/U8's "
      "archive-wide sweeps ran over, so those greens already covered these "
      "files ANONYMOUSLY (FINDINGS 4.4's 'never been walked' was stale)",
      f"off-population: {off}")
data = {}
bad_magic = []
for fid in sorted(geom):
    d = bytes(ar.read(rows[fid]))
    if d[:4] != archive.FFNA_MAGIC:
        bad_magic.append(fid)
        continue
    data[fid] = d
check(not bad_magic,
      "every container opens as ffna -- the flags=515 anomaly (row 8316, "
      "28 B, no ffna) is not among the player files", f"bad: {bad_magic}")

kinds = {}
for fid, d in data.items():
    ch = {cid for cid, _o, _s in archive.ffna_chunks(d)}
    kinds[fid] = (FA0 in ch, FA1 in ch)
check(all(kinds[fid] == (False, True) for fid in shells),
      "all 40 shells carry FA1 and NO FA0 -- the composited <=> no-FA0 rule, "
      "previously archive-wide, now holds BY NAME on the player set")
comps = [fid for fid in data if fid not in shells]
check(all(kinds[fid] == (True, False) for fid in comps),
      "all 140 components carry FA0 and NO FA1 -- the mesh pieces bring no "
      "skeleton of their own; the shell's is the only one",
      f"components={len(comps)}")

# ---------------------------------------------------------------- section 3
print("== 3. the named round trip: both writers, every file ==")
fa1_id = sum(skelwrite.rebuild_container(data[fid]) == data[fid]
             for fid in shells)
check(fa1_id == 40,
      "skelwrite re-emits all 40 shell containers byte-identically -- the "
      "FA1 re-derived from typed values, not carried",
      f"{fa1_id}/40")
fa0_id = sum(modelwrite.rebuild_container(data[fid]) == data[fid]
             for fid in comps)
check(fa0_id == 140,
      "modelwrite re-emits all 140 component containers byte-identically",
      f"{fa0_id}/140")

# ---------------------------------------------------------------- section 4
print("== 4. the typed layer re-measures the study's own numbers ==")
seqs = {fid: skelfile.Skeleton.from_container(data[fid]) for fid in shells}
check(all(sk.composited for sk in seqs.values()),
      "all 40 shells set MODEL_SKELETON_FLAG_COMPOSITED")
t1 = sorted(sk.seq_count for fid, sk in seqs.items() if shells[fid] == 1)
t2 = sorted(sk.seq_count for fid, sk in seqs.items() if shells[fid] == 2)
check(len(t1) == 20 and t1[0] == 220 and t1[-1] == 289,
      "type-1 sequence counts span exactly 220..289 (FINDINGS 1.22), read "
      "through the WRITER-facing decoder -- a second witness by other code",
      f"{t1}")
check(len(t2) == 20 and t2[-1] == 115 and all(10 <= n <= 17 for n in t2[:-1]),
      "type-2: nineteen shells in 10..17 plus the ONE 115 outlier the "
      "2026-08-22 correction named -- reproduced, not just remembered",
      f"{t2}")

# ---------------------------------------------------------------- section 5
print("== 5. identity is informative: one mutation each way, on player files ==")
SHELL = 15018            # group 0 / prof 1 / sex 0 -- the archivewrite wall
t = skelwrite.extract(skelfile.Skeleton.from_container(data[SHELL]))
orig_payload = skelwrite.encode(t)
changed = skelwrite.scale_sequence_keytimes(t, 16, 2)
out = skelwrite.encode(t)
check(changed and out != orig_payload and len(out) == len(orig_payload),
      f"shell {SHELL}: scaling sequence 16's key times x2 changes "
      f"{len(changed)} key(s), length-preserving -- the U7 seam fires on a "
      f"PLAYER shell", f"changed={changed[:6]}")
# Re-decode through the public path: encode -> decode -> the scaled values.
sk2 = skelfile.Skeleton.decode(out)
tt = skelwrite.extract(sk2)
check(all(tt["key_times"][k] == 2 * skelwrite.extract(
          skelfile.Skeleton.decode(orig_payload))["key_times"][k]
          for k in changed),
      "and a fresh decode of the emitted bytes reads back exactly the "
      "doubled times -- the change is IN the bytes, not in the object")

# Atomicity: a refusal leaves the representation still encoding the source.
t3 = skelwrite.extract(skelfile.Skeleton.decode(orig_payload))
nz = [k for k in range(t3["sequences"][16]["lo"], t3["sequences"][16]["hi"])
      if t3["key_times"][k] % 7919]
if nz:
    try:
        skelwrite.scale_sequence_keytimes(t3, 16, 1, 7919)
        check(False, "an inexact retime must refuse")
    except skelwrite.Unwritable:
        check(skelwrite.encode(t3) == orig_payload,
              "an inexact retime REFUSES atomically -- t still encodes to "
              "the source bytes, no half-experiment left behind")
else:
    LEDGER.skip("atomicity control", "sequence 16's keys all divide 7919")

COMP = min(comps)
fa0_off, fa0_size = next((o, s) for cid, o, s
                         in archive.ffna_chunks(data[COMP]) if cid == FA0)
tm = modelwrite.extract(data[COMP][fa0_off:fa0_off + fa0_size])
import modelfile                                            # noqa: E402
before = list(tm["submodels"][0]["verts"][modelfile.FIELD_POSITION])
n = modelwrite.scale_positions(tm, 2.0)
out0 = modelwrite.encode(tm)
tm2 = modelwrite.extract(out0)
after = tm2["submodels"][0]["verts"][modelfile.FIELD_POSITION]
check(n > 0 and all(b == tuple(c * 2.0 for c in a)
                    for a, b in zip(before, after)),
      f"component {COMP}: scaling positions x2 moves {n} vertices and a "
      f"fresh decode reads back exactly the doubled coordinates",
      f"first vert {before[0]} -> {after[0]}")

sys.exit(LEDGER.verdict())
