r"""A player identity -> the closed archive file set the client would load.

    python toolkit/mapdata/playerassembly.py --group 0 --prof 1 --sex 0
    python toolkit/mapdata/playerassembly.py --census      # the 40 identities

The playercomposite arc's P3 rung (studies/playercomposite/FINDINGS.md 5, 8).
`cpsdata.CompositeTable` decodes the composite data file and names the record
picks; `unitassembly.Resolver` owns the closure walk (FA5/FAD terminals, the
FA6 -> ffna-type-8 -> chunk-0x1 audio hop, FA8 links, null-slot accounting --
all seed-independent since the `resolve_seeds` split). This module supplies
what is PLAYER-specific: which of a cell's records one identity picks, and
which file slots of each record belong to that identity.

THE RECORD PICKS, per FINDINGS 2C -- each is a (type, group, profession) cell,
first record:

    shell        type 1 in-world (the authoring target: arg0 bit 0 = 0 for
                 every in-world agent, FINDINGS 7) or 2 UI-preview
    face         type 11 for sex 0, 10 for sex 1 (sex-keyed pair)
    hair         type 13 for sex 0, 12 for sex 1
    base pieces  types 3, 4, 5, 6 (chest/feet/hands/legs -- NAMES are
                 RECONSTRUCTION, claim 23)
    unknown      type 9 (component 7; never worn) -- included because the
                 client's own base lookup includes it; drop with
                 include_type9=False

THE SLOT SPLIT, per FINDINGS 1.15/1.16: `cpsdata.SEX_BASE_SLOT` is (0, 5) and
`SHARED_SLOT` is 10; slots {0..4} are one sex, {5..9} the other, 10 shared;
{0, 5, 10} are geometry (ffna), the rest textures (ATEX). One player's set is
its sex's half plus slot 10. Which sex is which WORD is RECONSTRUCTION.

EQUIPMENT: an equipped composite item's `ItemData.fileId` indexes the same
records (FINDINGS 2E). `assemble(..., equipped=[record indices])` adds their
sex-half slots. The base piece the item replaces stays in the set -- the
closure is about what must EXIST in the archive, and per-component replacement
is display logic this module does not model (named gap).

EMPTY CELLS REFUSE FOR THE SHELL, are recorded for the rest: a profession
looked up outside its home group has no base identity (FINDINGS 1.24 -- what
the client's availability sweep exists for), and a manifest on a missing shell
is a character that cannot exist.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import cpsdata       # noqa: E402
import unitassembly  # noqa: E402

MANIFEST_SKIP_BIT = 0x20000        # header bit 17 (FINDINGS 2F; no retail
                                   # record sets it, so this is a guard for a
                                   # behaviour that is unreachable on this data)
SHELL_TYPE_WORLD = 1               # arg0 bit 0 = 0, the authoring target
SHELL_TYPE_UI = 2
FACE_TYPE = {0: 11, 1: 10}
HAIR_TYPE = {0: 13, 1: 12}
BASE_PIECE_TYPES = (3, 4, 5, 6)
TYPE_UNKNOWN9 = 9
GEOMETRY_SLOTS = frozenset(cpsdata.SEX_BASE_SLOT) | {cpsdata.SHARED_SLOT}

# Bit 31 of a Gw.dat file id is RESERVED -- the client asserts
# `!(id & FILE_ID_RESERVED_BIT)` on the ordinary-id path, twice: CpsData:468
# (0x008332ac) and CpsData:484 (0x008334c5), each `shr eax,0x1f; not eax;
# test al,1`. Both routines are pure asserts (every exit `xor eax,eax`), so
# they gate AUTHORING, not runtime filtering. MEASURED 2026-08-22
# (studies/playercomposite 4.3): the bit marks a DISTINCT id namespace --
# 25 ids in the study archive's raw file-id table carry it (max 0x8005E728),
# mapping to real MFT rows and disjoint from the ordinary space -- so an
# authored file id must keep bit 31 clear or it collides with the client's
# reserved references. All 16,567 composite file ids do (max 375,810), so
# authoring a player from the composite table never trips it; a mint that
# ever set the bit would, and `manifest` refuses one before it reaches a seed.
FILE_ID_RESERVED_BIT = 0x80000000


class PlayerAssemblyError(Exception):
    """A refusal: the identity does not resolve to a buildable manifest."""


class PlayerDef:
    """The identity a Resolution carries. `file_id` is the shell geometry."""

    __slots__ = ("group", "profession", "sex", "shell_type", "file_id",
                 "equipped")

    def __init__(self, group, profession, sex, shell_type=SHELL_TYPE_WORLD,
                 equipped=()):
        self.group, self.profession, self.sex = group, profession, sex
        self.shell_type = shell_type
        self.equipped = tuple(equipped)
        self.file_id = None

    def __repr__(self):
        return (f"PlayerDef(group={self.group}, prof={self.profession}, "
                f"sex={self.sex}, type={self.shell_type})")


def sex_slots(sex):
    """The file slots one sex's assembly reads: its half plus shared 10."""
    half = range(0, 5) if sex == 0 else range(5, 10)
    return tuple(half) + (cpsdata.SHARED_SLOT,)


def _pick(table, type_, group, prof, what, absences):
    """A cell's first record, or None with the absence recorded."""
    rec = table.record(group, prof, type_)
    if rec is None:
        absences.append((type_, what, "empty cell"))
        return None
    if rec.hdr & MANIFEST_SKIP_BIT:
        absences.append((type_, what, "record carries the manifest-skip bit"))
        return None
    return rec


def manifest(table, player, include_type9=True):
    """(seeds, picks, absences) for one identity. Refuses a missing shell.

    `seeds` is the (file_id, role) list `unitassembly.resolve_seeds` takes:
    geometry files under model roles (the shell as ROLE_SHELL, other geometry
    as ROLE_BODY -- the walk reads and walks both), textures as ROLE_TEXTURE
    terminals.
    """
    group, prof, sex = player.group, player.profession, player.sex
    absences, picks = [], []
    wanted = [(player.shell_type, "shell"),
              (FACE_TYPE[sex], "face"), (HAIR_TYPE[sex], "hair")]
    wanted += [(t, f"base piece type {t}") for t in BASE_PIECE_TYPES]
    if include_type9:
        wanted.append((TYPE_UNKNOWN9, "type 9 (component 7)"))
    for type_, what in wanted:
        rec = _pick(table, type_, group, prof, what, absences)
        if rec is not None:
            picks.append((what, rec))

    shell_rec = next((r for w, r in picks if w == "shell"), None)
    if shell_rec is None:
        raise PlayerAssemblyError(
            f"{player!r}: no shell record -- the identity's base lives in "
            f"another group (the home-group rule, FINDINGS 1.24). "
            f"Absences: {absences}")
    shell_fid = shell_rec.base_file(sex)
    if shell_fid is None:
        raise PlayerAssemblyError(
            f"{player!r}: the shell record has no geometry for sex {sex}")
    player.file_id = shell_fid

    for idx in player.equipped:
        if not 0 <= idx < len(table.records):
            raise PlayerAssemblyError(
                f"{player!r}: equipped composite index {idx} outside "
                f"[0, {len(table.records)})")
        picks.append((f"equipped {idx}", table.records[idx]))

    seeds, seen = [], set()
    for _what, rec in picks:
        for slot in sex_slots(sex):
            fid = rec.files.get(slot)
            if not fid or fid in seen:
                continue
            if fid & FILE_ID_RESERVED_BIT:
                # The client asserts !(id & FILE_ID_RESERVED_BIT) on this path
                # (CpsData:468/:484); a reserved-bit id is a different id
                # namespace, not a file to seed. No composite id sets it, so
                # this is a tripwire for a corrupt table or a bad mint, not an
                # expected branch.
                raise PlayerAssemblyError(
                    f"{player!r}: file id 0x{fid:08X} has the reserved bit 31 "
                    f"set -- the client would assert !(id & FILE_ID_RESERVED_"
                    f"BIT). It is the client's own id namespace, not authorable.")
            seen.add(fid)
            if slot in GEOMETRY_SLOTS:
                role = (unitassembly.ROLE_SHELL if fid == shell_fid
                        else unitassembly.ROLE_BODY)
            else:
                role = unitassembly.ROLE_TEXTURE
            seeds.append((fid, role))
    return seeds, picks, absences


def assemble(resolver, table, group, prof, sex, shell_type=SHELL_TYPE_WORLD,
             equipped=(), include_type9=True, deep=True):
    """One identity -> (Resolution, absences). `res.closed` is the verdict,
    exactly as for a wire unit."""
    player = PlayerDef(group, prof, sex, shell_type, equipped)
    seeds, _picks, absences = manifest(table, player,
                                       include_type9=include_type9)
    return resolver.resolve_seeds(player, seeds, deep=deep), absences


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--group", type=int, default=0)
    ap.add_argument("--prof", type=int, default=1)
    ap.add_argument("--sex", type=int, default=0, choices=(0, 1))
    ap.add_argument("--type", type=int, default=1, choices=(1, 2),
                    help="shell type: 1 in-world (the authoring target), "
                         "2 UI preview")
    ap.add_argument("--census", action="store_true",
                    help="assemble every home-group identity, both types/sexes")
    args = ap.parse_args()

    import archive
    import vaultpath
    ar = archive.Archive(vaultpath.vault_path("dat_study", "Gw.dat"))
    table = cpsdata.CompositeTable.load(ar)
    resolver = unitassembly.Resolver(ar)

    if args.census:
        closed = notclosed = skipped = 0
        for t in cpsdata.SHELL_TYPES:
            for g in range(table.n_groups):
                for prof in range(cpsdata.PROFESSIONS):
                    for sex in (0, 1):
                        try:
                            res, _a = assemble(resolver, table, g, prof, sex,
                                               shell_type=t)
                        except PlayerAssemblyError:
                            skipped += 1
                            continue
                        if res.closed:
                            closed += 1
                        else:
                            notclosed += 1
                            print(f"NOT CLOSED t{t} g{g} p{prof} s{sex}: "
                                  f"{res.problems[:3]}")
        print(f"closed {closed}, not closed {notclosed}, "
              f"foreign-group (no shell) {skipped}")
        return 0 if notclosed == 0 else 1

    res, absences = assemble(resolver, table, args.group, args.prof, args.sex,
                             shell_type=args.type)
    print(f"{res.unit!r}  shell file {res.unit.file_id}")
    print(f"  files {len(res.files)}  closed={res.closed}  "
          f"null_slots={res.null_slots}")
    for fid, role, why in res.problems:
        print(f"  PROBLEM {fid} ({role}): {why}")
    for note in absences:
        print(f"  absent: {note}")
    return 0 if res.closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
