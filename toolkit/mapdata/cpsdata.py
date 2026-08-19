r"""The composite table: Gw.dat file `0x33EA`, where a PLAYER's file ids live.

    python toolkit/mapdata/cpsdata.py                 # the table, summarised
    python toolkit/mapdata/cpsdata.py --shells        # the twenty player shells
    python toolkit/mapdata/cpsdata.py --manifest 0 1  # one (group, profession)

Rung U10 of `studies/unitmodels/PLAN.md`; the derivation, the five readings
that produced it and the five attacks on them are
[studies/playercomposite/FINDINGS.md](../../studies/playercomposite/FINDINGS.md).
READ ONLY -- this module opens the archive and never writes a byte.

WHY THIS EXISTS, and it starts with a wrong answer. `unitassembly.py` resolves
a wire definition to a complete file set for MONSTERS -- 0x0056 names a shell,
0x0057 names its bodies, 54/54 pooled definitions close. Players are not on
that path (`CpsMonster` vs `CpsPlayer`, ArenaNet's own vocabulary), so the
question "which files would the client load for THIS character?" had no answer
at all, and the named suspect was `ConstComposite`'s two 132-entry pointer
tables in `Gw.exe`. **They are texture-atlas rectangles.** 359/359 of their
records satisfy `0 <= left < right <= W` and `0 <= top < bottom <= H` against
their own blitId's `s_dims`, where the rival readings fail 269/359 (XYWH) and
284/359 (LRTB), and the complete value set across every record is
`{0, 128, 256, 384, 448, 512}`. There is no file id in either table at any
depth. That path is closed and this one is open instead.

WHAT THE FILE IS. `push 0x33EA; call 0x00833540` at `0x0082D420` is the
loader's only caller and it asserts `CpsData:622 Failed to open composite data
file`. In the study archive that id is MFT row 71, 105,531 bytes, and it holds
two halves:

  * **section 1** -- `u8 nGroup`, then `nGroup * 11 * 20` length-prefixed u16
    id lists. The 11 and the 20 are ArenaNet's own bounds (`CpsData:392/393`);
    in memory the same data is `s_type[race] = {u16 count[11][20]; u16
    offset[11][20]}`, which is why the on-disk form is count-then-ids.
  * **section 2** -- one record per id: `u32 header`, then one `u32` file id
    per SET BIT of `header & 0x7FF`. `type = header >> 22`.

THE CLOSURE IS OURS, NOT THE CLIENT'S -- AND THE OBVIOUS ONE IS NEARLY
VACUOUS, which is worth stating before anyone leans on it. Nothing in the file
states a record count and nothing compares a cursor to the end; section 2 is
terminated by the payload running out, so `cursor == len` looks like the
closure. It is not, for section 2: **every record consumes 4 + 4*popcount
bytes, so ANY dword-consuming parser lands exactly on the end.** Reading the
slot mask 9, 10, 12 or 13 bits wide all give residue 0 -- measured, that is why
this paragraph exists. Residue only catches a truncation that is not a multiple
of four.

WHAT ACTUALLY PINS THE RECORD FRAMING is that the file says the same thing
twice in halves that must agree:

  * **`len(records) == the number of ids in section 1`.** Enforced in `decode`,
    because a framing that disagrees here has mis-parsed, not found a variant.
    At an 11-bit mask this is 3,803 == 3,803; at 9, 10, 12 and 13 bits it is
    3,992 / 3,858 / 3,795 / 3,752 against the same 3,803.
  * **cross-half type agreement** -- 3803/3803 at the true framing, and
    591 / 1,256 / 876 / 728 at those same four rivals. A mis-framed walk
    produces records, and this is what refuses them.

Three further closures could each have failed and did not. They are exposed as
methods rather than baked in, so a future build can move them without this
module lying about it:

  * `partition_violations()` -- every record referenced by exactly ONE section-1
    cell. Measured `{1: 3803}`: a partition, not a pool. Note this is strictly
    stronger than the count equality `decode` enforces -- equal counts with a
    record used twice and another never is arithmetically possible.
  * `type_disagreements()` -- each id's section-1 TYPE AXIS equals that
    record's own `header >> 22`. **3803/3803**, across disjoint halves of the
    file, so it is two encodings of the same fact agreeing.
  * `unresolved_refs(id_table)` -- **20,238 of 20,238** file references live in
    the archive's id table.

WHAT A SLOT IS, DERIVED HERE RATHER THAN ASSUMED. The eleven slots split by
kind, and this module MEASURES the split instead of importing the client's
`s_fileFlags`: slots **{0, 5, 10}** carry `ffna` model containers (6,703 refs,
zero exceptions) and the other eight carry `ATEX` textures (13,535 refs, zero
exceptions). Sex selects the half -- `file[0]` when `sex == 0`, `file[5]`
otherwise (`CpsPlayer 0x008315DB/0x008315E0`) -- so slots {0..4} are one sex,
{5..9} the other, and slot 10 is shared. THAT SEX 0 IS MALE IS NOT ESTABLISHED
(RECONSTRUCTION); this module says `sex 0` and lets the caller name it.

THE HEADER'S MIDDLE IS UNNAMED. Bits 0--10 are the slot mask and bits 22--26
carry the type (5 bits is all 0..19 needs; bits 27--31 are never set). Bits
11--21 are a field we have not decoded -- occupancy over the 3,803 records is
bit 11: 155, bits 12/13: 0, bit 14: 50, bit 15: 50, bit 16: 98, **bit 17: 0**,
bits 18--21: 1,924 / 1,881 / 1,606 / 862. Recorded because a reading of the
manifest walk claims bit 17 (`0x20000`) skips a record: it may well, but **no
retail record sets it**, so that behaviour is unreachable on this data and
must not be cited as observed. `Record.hdr` keeps the raw dword.

THE TWO-WITNESS JOIN is the reason to trust any of this, and `shells()` is the
call that runs it. Resolving composite type 1 across every `(group,
profession)` cell and taking slots 0 and 5 yields **exactly the twenty shells
an independent FFNA walk over the archive names, in the same sex pairing**, all
twenty composited (FA1 present, FA0 absent). Type 2 is a second twenty on
element-for-element identical node counts with sequence counts of 10--17
against type 1's 220--289 -- the same skeletons with almost no animation. The
two witnesses share no method: one parses a client data file off disk, the
other walks chunk tables in the archive. `test_cpsdata.py` pins it, and its
sharpest sabotage is that the hatcher shell 116228 IS composited and DOES
walk -- only this table can reject it, and it does: 116228, 116703, 116377 and
116366 are all absent from the 16,567 distinct file ids here.

WHICH TYPE IS WHICH is not settled and is the top blocker on authoring:
`CpsPlayer` picks type 1 vs type 2 on bit 0 of its constructor's `arg0`
(`and eax,1; inc eax`, `0x008315B5`), and what `arg0` is has NOT been found.
Authoring against the wrong twenty produces a character that cannot animate.
"""

import argparse
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table, DEFAULT_DAT  # noqa: E402

#: The composite data file. `push 0x33EA` at `0x0082D420`, asserted open by
#: `CpsData:622`.
COMPOSITE_FILE_ID = 0x33EA

#: ArenaNet's own section-1 bounds, `CpsData:392/393`. NOT guesses from the
#: data: the arithmetic `1 + nGroup*11*20*2 + total_ids*2` closing exactly on
#: the measured section-1 end is what tests them (9,367 in the study archive).
PROFESSIONS = 11
TYPES = 20

#: Section-2 record header. Bits 0..10 select which of the eleven file slots
#: are present; bits 22.. carry the type. Bits 11..21 are UNDECODED.
SLOTS = 11
SLOT_MASK = 0x7FF
TYPE_SHIFT = 22

#: Sex selects the slot half -- `CpsPlayer 0x008315DB/0x008315E0`. Slot 10 is
#: shared by both. "sex 0" is deliberately not called "male" (RECONSTRUCTION).
SEX_BASE_SLOT = (0, 5)
SHARED_SLOT = 10

#: The shell/skeleton composite types. `(arg0 & 1) + 1` at `0x008315B5`, so
#: exactly these two, and which one a character gets is NOT FOUND.
SHELL_TYPES = (1, 2)

#: A hard sanity bound on a length-prefixed list, so a wrong cursor dies at a
#: named gate rather than allocating. No retail cell is anywhere near it.
MAX_LIST = 4096


class CpsDataError(ValueError):
    """The composite table refused to decode. Never decode past one."""


class Record:
    """One composite record: a header and its present file slots.

    `files` maps slot index -> Gw.dat file id, and carries ONLY the slots the
    header's mask declares; a missing slot is absent, never zero-filled, so
    `0 in rec.files` distinguishes "no geometry for this sex" from "geometry
    id 0".
    """

    __slots__ = ("index", "hdr", "files")

    def __init__(self, index, hdr, files):
        self.index = index
        self.hdr = hdr
        self.files = dict(files)

    @property
    def mask(self):
        return self.hdr & SLOT_MASK

    @property
    def type(self):
        return self.hdr >> TYPE_SHIFT

    @property
    def unnamed(self):
        """Header bits 11..21, the field we have not decoded."""
        return (self.hdr >> SLOTS) & ((1 << (TYPE_SHIFT - SLOTS)) - 1)

    def base_file(self, sex):
        """The geometry file for `sex`, or None.

        Falls back to the shared slot, which is what carries a record whose
        geometry does not vary by sex.
        """
        if sex not in (0, 1):
            raise CpsDataError(f"sex must be 0 or 1, not {sex!r}")
        got = self.files.get(SEX_BASE_SLOT[sex])
        return got if got is not None else self.files.get(SHARED_SLOT)

    def __repr__(self):
        return (f"Record(#{self.index} type={self.type} "
                f"slots={sorted(self.files)})")


class CompositeTable:
    """Gw.dat file `0x33EA`, decoded. `lists` and `records` are the two halves."""

    def __init__(self, n_groups, lists, records, section1_end, size):
        self.n_groups = n_groups
        self.lists = lists              # (group, profession, type) -> (id, ...)
        self.records = records          # index-aligned with the section-1 ids
        self.section1_end = section1_end
        self.size = size

    # -- decoding ---------------------------------------------------------

    @classmethod
    def decode(cls, payload):
        payload = bytes(payload)
        if not payload:
            raise CpsDataError("composite table is empty")
        cur = 0
        n_groups = payload[cur]
        cur += 1
        if not 1 <= n_groups <= 64:
            raise CpsDataError(
                f"nGroup is {n_groups}; the file declares its own group count "
                f"in its first byte and no plausible value is outside 1..64")

        lists, total_ids = {}, 0
        for g in range(n_groups):
            for prof in range(PROFESSIONS):
                for ty in range(TYPES):
                    if cur + 2 > len(payload):
                        raise CpsDataError(
                            f"section 1 ran off the payload at group {g}, "
                            f"profession {prof}, type {ty} (offset {cur} of "
                            f"{len(payload)})")
                    n, = struct.unpack_from("<H", payload, cur)
                    cur += 2
                    if n > MAX_LIST:
                        raise CpsDataError(
                            f"id list at ({g}, {prof}, {ty}) declares {n} "
                            f"entries, over the {MAX_LIST} sanity bound -- the "
                            f"cursor is wrong, not the file")
                    if cur + 2 * n > len(payload):
                        raise CpsDataError(
                            f"id list at ({g}, {prof}, {ty}) wants {n} ids but "
                            f"only {(len(payload) - cur) // 2} words remain")
                    lists[(g, prof, ty)] = struct.unpack_from(
                        "<%dH" % n, payload, cur)
                    cur += 2 * n
                    total_ids += n
        section1_end = cur

        predicted = 1 + n_groups * PROFESSIONS * TYPES * 2 + total_ids * 2
        if predicted != section1_end:
            raise CpsDataError(
                f"section-1 arithmetic does not close: 1 + "
                f"{n_groups}*{PROFESSIONS}*{TYPES}*2 + {total_ids}*2 = "
                f"{predicted}, cursor at {section1_end}")

        records = []
        while cur < len(payload):
            if cur + 4 > len(payload):
                raise CpsDataError(
                    f"record {len(records)} header wants 4 bytes, "
                    f"{len(payload) - cur} remain")
            hdr, = struct.unpack_from("<I", payload, cur)
            cur += 4
            files = {}
            for slot in range(SLOTS):
                if not (hdr >> slot) & 1:
                    continue
                if cur + 4 > len(payload):
                    raise CpsDataError(
                        f"record {len(records)} slot {slot} wants 4 bytes, "
                        f"{len(payload) - cur} remain")
                files[slot], = struct.unpack_from("<I", payload, cur)
                cur += 4
            records.append(Record(len(records), hdr, files))

        # Residue. Weak on its own -- see the docstring: every record is a
        # whole number of dwords, so any dword-consuming parser lands here.
        # It catches a truncation that is not a multiple of four, no more.
        if cur != len(payload):
            raise CpsDataError(
                f"composite table does not close: cursor {cur} of "
                f"{len(payload)} bytes, {len(payload) - cur} left over")

        # THE REAL FRAMING CHECK. Section 1 counted the records before section 2
        # framed them, in a disjoint half of the file, so this is two witnesses
        # and a mis-parse cannot satisfy it: the four neighbouring slot widths
        # give 3,992 / 3,858 / 3,795 / 3,752 against section 1's 3,803.
        if len(records) != total_ids:
            raise CpsDataError(
                f"section 2 framed {len(records)} records but section 1 names "
                f"{total_ids} ids; the record walk is mis-framed (residue is 0 "
                f"either way -- every record is a whole number of dwords)")

        return cls(n_groups, lists, records, section1_end, len(payload))

    @classmethod
    def load(cls, archive_, file_id=COMPOSITE_FILE_ID):
        table = file_id_table(archive_, raw=True)
        if file_id not in table:
            raise CpsDataError(
                f"file id {file_id} (0x{file_id:X}) is not in this archive's "
                f"id table; the composite table cannot be read")
        return cls.decode(archive_.read(archive_.row(table[file_id])))

    # -- the closures, as questions rather than assumptions ----------------

    def partition_violations(self):
        """Record indices referenced by other than exactly one section-1 cell.

        Returns `{index: count}` for every offender, so `{}` is the measured
        `{1: 3803}` partition. NOT enforced in `decode`: a build that pooled a
        record across two cells would be a finding about the format, not a
        corrupt file.
        """
        seen = Counter(i for ids in self.lists.values() for i in ids)
        bad = {i: n for i, n in seen.items() if n != 1}
        for i in range(len(self.records)):
            if i not in seen:
                bad[i] = 0
        return bad

    def type_disagreements(self):
        """Cells whose type axis disagrees with the record's own `hdr >> 22`.

        Returns `[(cell, record_index, axis_type, record_type), ...]`. The two
        are encoded in disjoint halves of the file, so agreement is two
        witnesses, not one restated.
        """
        out = []
        for cell, ids in sorted(self.lists.items()):
            ty = cell[2]
            for i in ids:
                if i >= len(self.records):
                    out.append((cell, i, ty, None))
                elif self.records[i].type != ty:
                    out.append((cell, i, ty, self.records[i].type))
        return out

    def unresolved_refs(self, id_table):
        """File references that are not in the archive's id table."""
        return [(r.index, slot, fid)
                for r in self.records
                for slot, fid in sorted(r.files.items())
                if fid not in id_table]

    # -- accessors ---------------------------------------------------------

    def ids(self, group, profession, type_):
        return self.lists.get((group, profession, type_), ())

    def record(self, group, profession, type_):
        """The FIRST record of a cell, or None. Cells are 0- or 1-deep in
        retail; a caller that needs the rest walks `ids()` itself."""
        got = self.ids(group, profession, type_)
        return self.records[got[0]] if got else None

    def file_refs(self):
        for r in self.records:
            for slot, fid in sorted(r.files.items()):
                yield r.index, slot, fid

    def distinct_file_ids(self):
        return {fid for _, _, fid in self.file_refs()}

    def slot_kinds(self, archive_, id_table):
        """Measure, do not assume, which slots carry geometry.

        Returns `{slot: Counter(magic)}` over every reference. The client's own
        `s_fileFlags` says slots {0, 5, 10}; this derives the same split from
        the archive so the module owes `Gw.exe` nothing.
        """
        out = {}
        for _, slot, fid in self.file_refs():
            row = id_table.get(fid)
            if row is None:
                continue
            magic = bytes(archive_.magic(archive_.row(row), 4))
            out.setdefault(slot, Counter())[magic] += 1
        return out

    def shells(self, type_, sexes=(0, 1)):
        """`{(group, profession): {sex: file_id}}` for a shell composite type.

        This is the player-side seed set: run it at type 1 and 2 and every file
        it names should be a COMPOSITED shell (FA1 present, FA0 absent), which
        is the two-witness closure the rung is accepted on.
        """
        out = {}
        for (g, prof, ty), ids in sorted(self.lists.items()):
            if ty != type_ or not ids:
                continue
            rec = self.records[ids[0]]
            got = {sex: rec.base_file(sex) for sex in sexes}
            got = {s: f for s, f in got.items() if f is not None}
            if got:
                out[(g, prof)] = got
        return out

    def manifest(self, group, profession):
        """Every `(type, slot, file_id)` a cell's records reference.

        `CpsApi 0x0082D7D0` walks each record's eleven slots and appends every
        non-zero id; this is the archive-side equivalent for one cell.
        """
        out = []
        for ty in range(TYPES):
            for i in self.ids(group, profession, ty):
                for slot, fid in sorted(self.records[i].files.items()):
                    out.append((ty, slot, fid))
        return out

    def __repr__(self):
        return (f"CompositeTable(groups={self.n_groups}, "
                f"cells={len(self.lists)}, records={len(self.records)}, "
                f"{self.size} B)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=None,
                    help="archive to read (default: the study archive)")
    ap.add_argument("--shells", action="store_true",
                    help="print the shell composite types' file ids")
    ap.add_argument("--manifest", nargs=2, type=int, metavar=("GROUP", "PROF"),
                    help="print every (type, slot, file id) of one cell")
    args = ap.parse_args(argv)

    dat = args.dat
    if dat is None:
        import vaultpath
        dat = os.path.join(
            vaultpath.require_dir("dat_study", why="the composite table"),
            os.path.basename(DEFAULT_DAT))

    with Archive(dat) as ar:
        idt = file_id_table(ar, raw=True)
        t = CompositeTable.load(ar)
        print(t)
        refs = list(t.file_refs())
        print(f"  section 1 ends {t.section1_end}, {len(refs)} file refs, "
              f"{len(t.distinct_file_ids())} distinct")
        print(f"  partition violations: {len(t.partition_violations())}")
        print(f"  type disagreements:   {len(t.type_disagreements())}")
        print(f"  unresolved refs:      {len(t.unresolved_refs(idt))}")
        kinds = t.slot_kinds(ar, idt)
        geo = sorted(s for s, c in kinds.items()
                     if c.most_common(1)[0][0] == b"ffna")
        print(f"  geometry slots (measured): {geo}")

        if args.shells:
            for ty in SHELL_TYPES:
                print(f"\ncomposite type {ty}:")
                for (g, prof), bysex in sorted(t.shells(ty).items()):
                    cols = "  ".join(f"sex{s}={f}" for s, f in sorted(bysex.items()))
                    print(f"  group {g} profession {prof:<2}  {cols}")

        if args.manifest:
            g, prof = args.manifest
            rows = t.manifest(g, prof)
            print(f"\nmanifest for group {g}, profession {prof}: "
                  f"{len(rows)} references")
            for ty, slot, fid in rows:
                print(f"  type {ty:<2} slot {slot:<2} file {fid}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
