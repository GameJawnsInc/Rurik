"""The whole map file: read an `ffna` map container apart and write it back.

`terrain.py` reproduces ONE chunk of a map byte for byte. This module is the
container around it -- the four magic bytes, the type byte, and the ordered list
of `{u32 id, u32 size}` chunks that fills the rest of the file. Reproducing that
exactly is the rung between "we can read a terrain chunk" and "we can emit a map
the client will open", because a map an authoring pass writes has to be a whole
file and not a chunk.

    data = archive.read(entry)       # a decompressed map file
    mf   = MapFile.decode(data)
    assert mf.encode() == data       # 349 of 349 Bloated, 349 of 349 Stripped

**THE CHUNK TABLE'S `size` IS RE-DERIVED, NEVER STORED.** `Chunk` has no size
field to replay: `encode()` asks each chunk for its payload and writes
`len(payload)`. This is the difference between a codec and a memcpy with extra
steps -- an encoder that writes back a stored size round-trips every file it can
walk, including ones it understood nothing about, and the 349/349 would be
measuring `bytes == bytes`. `test_mapfile.py` proves the derivation happens by
mutating a decoded chunk until its encoded length changes and requiring the
emitted table entry to move with it.

WHAT IS RECONSTRUCTED AND WHAT IS CARRIED. This split is the honest half of the
result and it is stated in bytes, because the chunk COUNT flatters it (2 of 19
kinds reconstructed sounds worse than it is) and the byte count does not.
MEASURED on `vault/dat_study/Gw.dat` on 2026-08-11 by decoding and re-encoding
all 698 files of all 349 maps -- 16,094 chunks, 964,291,436 bytes, 738 s:

  Bloated stream, 723,597,618 B over 349 files, 8,047 chunks
    container framing         66,121 B   0.01%  magic, type byte, chunk table
    Terrain, reconstructed 335,105,844 B  46.31%  through `terrain.Terrain`
    Terrain, carried       136,087,682 B  18.81%  inside terrain.py, see below
    Dependencies               817,000 B   0.11%  through `mapchunks`, from the
                                                  stored triples
    other chunks, carried  251,520,971 B  34.76%  17 kinds, opaque `bytes`

  Stripped stream, 240,693,818 B over 349 files, 8,047 chunks
    container framing         66,121 B   0.03%
    Dependencies             817,000 B   0.34%  byte-identical to Bloated's
    other chunks, carried 239,810,697 B  99.63%  including Stripped terrain
                                                 0x10000002, a DIFFERENT
                                                 encoding that `terrain.py`
                                                 refuses by id -- so the whole
                                                 Stripped stream is 99.6% bytes
                                                 this module does not read

  Whole corpus: 336,739,844 B (34.92%) reconstructed from typed values,
  627,419,350 B (65.07%) carried, 132,242 B (0.01%) framing.

Two of those totals are predicted by FINDINGS 3, measured by a different pass,
and land: terrain's 335,105,844 + 136,087,682 = 471.2 MB is the census's Bloated
Terrain figure to the tenth of a megabyte, and the Dependencies total is exactly
`134,290 x 6 + 2,252 x 5 = 817,000` -- the reference and chunk counts 3 reports.
Neither is a check this module could force.

The terrain line is not this module's own measurement of terrain, and it is NOT
`terrain.py`'s classification either -- it is deliberately STRICTER than that
module's, and the difference is worth 60.5 MB. `terrain.py` calls a record
carried only where the bytes are an array whose meaning is NOT FOUND: tag 3's
bit field and tag 9's shade bytes. This census also counts tag 2's tile indices
and tags 4/5's two table bodies, which that module lists under FULLY SEMANTIC,
because they still reach the encoder as a `bytes` object it emits without
transforming. Tag 7's shadow bitmaps are rebuilt from typed values and are
counted as reconstructed by both. The 136,087,682 B splits (DERIVED from the
dims size laws, which are MEASURED 349/349, plus FINDINGS 4's 17,089 table slot
uses): tiles 60,468,224 + shade 60,468,224 + bits 15,117,056 + tables 34,178.

So the split below UNDERSTATES how much is decoded. On `terrain.py`'s own
reckoning the corpus is 41.20% reconstructed and 58.79% carried, not 34.92% /
65.07%. The conservative pair is the one reported everywhere in this module, and
the majority-carried claim holds either way. See `terrain.py`'s own docstring
for why the distinction is load-bearing: **a round-trip over carried bytes
compares a value with itself.**

So the honest reading of 698/698 is: **the container framing is proven, the
Dependencies framing is proven, terrain is proven to the extent terrain.py
claims, and 65.07% of the corpus by weight is bytes this module moved without
understanding.** Every one of those 17 carried kinds is a rung of its own, and
the two biggest are named: Path (156.5 MB Bloated) and Sight (29.9 MB).

WHAT IS DISPATCHED, precisely:

  * `0x20000002` -- Bloated Data Terrain -- `terrain.Terrain`. The Stripped
    partner `0x10000002` is NOT terrain in a different frame; it is a different
    encoding (bit-packed through `TrnCodecHeight`) and is carried.
  * any chunkType 1 -- Dependencies, either stage, all seven kinds --
    `mapchunks.decode_dependencies` / `encode_dependency_entries`.
  * everything else -- carried as `bytes`.

**Dependencies must be encoded from the stored triples, and this is a trap with
a corpus behind it.** The pair encoding aliases: `id0 >= 0xFF00` names the same
file id as `(id0 - 0xFF00, id1 + 1)`, and ArenaNet's own writer emits both forms
-- 85 entries in 84 of the 2,252 Bloated Dependencies chunks, across 76 maps
(MEASURED, `mapchunks.py`). So `encode_dependencies(chunk.file_ids)` is a left
inverse on FILE IDS and not on BYTES, and a container codec built on it would
lose 76 maps' bytes while looking correct on any sampled test. This module calls
`encode_dependency_entries` with the triples exactly as decoded.

BOTH STAGES GO THROUGH THE SAME CODE, and that was checked rather than assumed.
The framing INSIDE some Stripped chunks differs from its Bloated partner's
(FINDINGS 17.4: Stripped sub-records are `u8 tag` with no size field, and the
Stripped terrain chunk is 2,123 bytes where the Bloated one is 7,165) -- but the
CONTAINER is the same four-byte magic, the same type byte and the same
`{u32 id, u32 size}` table, so a codec that carries those chunks opaquely should
not care. `test_mapfile.py` section 5 is that check: 349 Stripped files
round-trip through the identical path, with the Stripped chunk ids (stage nibble
1) recognised and the Stripped terrain chunk carried rather than mis-parsed.

TRAPS.

  * `ffna_chunks()` is a GENERATOR and raises unless the walk lands exactly on
    the final byte. Consuming it twice yields nothing the second time; that bug
    has already silently zeroed one corpus script in this repo. It is listed
    once here, in `decode`.
  * A map file is two MFT rows, not one. `MapFile.load(file_id)` gives you the
    Bloated head; the Stripped partner is reachable only through
    `mapchunks.MapIndex`, never through the file-id table, which names ZERO of
    the 349 partners.
  * Chunk ids are not unique by construction. `find()` returns the first match
    and `chunks` is a LIST, because the file's order is what has to be
    reproduced -- FINDINGS 3 measured a single total order with 0 contradictory
    pairs, but this module preserves what the file says rather than imposing it.

SCOPE. Nothing here opens a file for writing, and nothing here places bytes in
an archive -- that is `datplan.py` and `datwrite.py`, and a separate rung.

    python toolkit/mapdata/mapfile.py                        # Kamadan
    python toolkit/mapdata/mapfile.py --file-id 0x22E2C      # smallest map
    python toolkit/mapdata/mapfile.py --row 46196 --stripped
    python toolkit/mapdata/mapfile.py --row 46196 --census
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, ffna_chunks, ffna_type,  # noqa: E402
                     file_id_table, DEFAULT_DAT, FFNA_MAGIC)
import mapchunks  # noqa: E402
from mapchunks import (MapIndex, TYPE_DEPENDENCIES, chunk_label,  # noqa: E402
                       decode_dependencies, encode_dependency_entries,
                       decompose)
from terrain import Terrain, TERRAIN_CHUNK, STRIPPED_TERRAIN_CHUNK  # noqa: E402

MAP_FFNA_TYPE = 3                       # FINDINGS 3: a map file is type 3
CHUNK_HEADER = struct.Struct("<II")     # {u32 id, u32 size} -- the size is
                                        # DERIVED on the way out, never stored
FFNA_HEADER_LEN = 5                     # magic(4) + type(1)

# How a chunk's payload is held. The names are the vocabulary the CLI, the
# census and the test all report in, so they are defined once here.
FORM_TERRAIN = "terrain"
FORM_DEPENDENCIES = "dependencies"
FORM_OPAQUE = "opaque"
RECONSTRUCTED_FORMS = (FORM_TERRAIN, FORM_DEPENDENCIES)


class Chunk:
    """One entry of the chunk table: an id and a value that can re-emit itself.

    **There is deliberately no `size` attribute.** The table's size field is
    `len(self.payload())` at encode time and nothing else. A stored size would
    make the round-trip a memcpy, which would pass over every chunk kind this
    module does not understand -- and it does not understand seventeen of them.

    `note` is set only when a chunk that COULD have been decoded was carried
    anyway, i.e. when `MapFile.decode(..., strict=False)` swallowed a decoder
    error. It is None on every corpus chunk; a non-None note is a decode this
    module failed and must be reported rather than counted as a round-trip.
    """

    __slots__ = ("chunk_id", "value", "form", "note")

    def __init__(self, chunk_id, value, form, note=None):
        self.chunk_id = chunk_id
        self.value = value
        self.form = form
        self.note = note

    @property
    def reconstructed(self):
        """True if the payload is rebuilt from typed values rather than copied."""
        return self.form in RECONSTRUCTED_FORMS

    @property
    def label(self):
        return chunk_label(self.chunk_id)

    def payload(self):
        """The chunk's bytes, rebuilt. The only source of the table's size."""
        if self.form == FORM_OPAQUE:
            return bytes(self.value)
        if self.form == FORM_TERRAIN:
            return self.value.encode()
        if self.form == FORM_DEPENDENCIES:
            return encode_dependency_entries(self.value.entries,
                                             version=self.value.version,
                                             signature=self.value.signature)
        raise ValueError(f"chunk 0x{self.chunk_id:08X}: no encoder for form "
                         f"{self.form!r}")

    def __repr__(self):
        return f"<Chunk 0x{self.chunk_id:08X} {self.form} {self.label}>"


def chunk_form(chunk_id):
    """Which codec a chunk id dispatches to. Pure, and the only dispatch rule.

    Terrain is matched by the FULL id, not by baseId: `0x10000002` is the
    Stripped terrain chunk and a different encoding entirely, so it falls
    through to opaque. Dependencies is matched by chunkType, which is stage-
    independent -- FINDINGS 3 measured all seven Dependencies kinds
    byte-identical between a map's two stages.
    """
    if chunk_id == TERRAIN_CHUNK:
        return FORM_TERRAIN
    if chunk_id == STRIPPED_TERRAIN_CHUNK:
        # Spelled out rather than left to fall through: this is a DECISION, and
        # `terrain.from_chunk` refuses this id for the same reason.
        return FORM_OPAQUE
    try:
        kind = decompose(chunk_id)
    except ValueError:
        # An id outside the client's own 23-slot table. We do not invent a
        # meaning for it; we carry it and the CLI prints it as undecodable.
        return FORM_OPAQUE
    if kind.chunk_type == TYPE_DEPENDENCIES:
        return FORM_DEPENDENCIES
    return FORM_OPAQUE


def decode_chunk(chunk_id, payload, strict=True):
    """One chunk's bytes to a `Chunk`. Raises unless `strict` is False."""
    form = chunk_form(chunk_id)
    if form == FORM_OPAQUE:
        return Chunk(chunk_id, bytes(payload), FORM_OPAQUE)
    try:
        if form == FORM_TERRAIN:
            return Chunk(chunk_id, Terrain.decode(payload), FORM_TERRAIN)
        return Chunk(chunk_id, decode_dependencies(payload), FORM_DEPENDENCIES)
    except (ValueError, KeyError, IndexError, struct.error) as exc:
        if strict:
            raise ValueError(f"chunk 0x{chunk_id:08X} ({chunk_label(chunk_id)}) "
                             f"is a {form} chunk and would not decode: "
                             f"{exc}") from exc
        return Chunk(chunk_id, bytes(payload), FORM_OPAQUE,
                     note=f"{form} decode failed: {exc}")


class MapFile:
    """A decompressed `ffna` map file: magic, type byte, ordered chunks."""

    __slots__ = ("magic", "ffna_type", "chunks")

    def __init__(self, ffna_type_=MAP_FFNA_TYPE, chunks=(), magic=FFNA_MAGIC):
        self.magic = bytes(magic)
        self.ffna_type = ffna_type_
        self.chunks = list(chunks)

    # -- decoding --------------------------------------------------------

    @classmethod
    def decode(cls, data, strict=True):
        """Bytes to a container. Refuses anything it cannot account for.

        `ffna_chunks` is the walk, and it raises unless the chunk sizes consume
        the file to the exact final byte -- so a truncated file, a size field
        that is wrong, or a bad decompression is an exception here and never a
        short chunk list. It is a generator: it is listed ONCE, below.
        """
        data = bytes(data)
        if len(data) < FFNA_HEADER_LEN:
            raise ValueError(f"ffna file is {len(data)} bytes, shorter than its "
                             f"{FFNA_HEADER_LEN}-byte header")
        if data[:4] != FFNA_MAGIC:
            raise ValueError(f"not an ffna file: magic {data[:4]!r} "
                             f"(expected {FFNA_MAGIC!r})")
        chunks = [decode_chunk(cid, data[off:off + size], strict=strict)
                  for cid, off, size in ffna_chunks(data)]
        return cls(ffna_type(data), chunks, magic=data[:4])

    @classmethod
    def from_row(cls, row, archive, strict=True):
        """One MFT row, decompressed and decoded. Works for either stage."""
        entry = next((e for e in archive.entries if e.index == row), None)
        if entry is None:
            raise ValueError(f"MFT row {row} does not exist in {archive.path}")
        return cls.decode(archive.read(entry), strict=strict)

    @classmethod
    def load(cls, map_file_id, archive=None, table=None, strict=True):
        """Open a map by the file id a server hands the client.

        This is always the BLOATED head: the file-id table names zero of the 349
        Stripped partners (MEASURED, `mapchunks.py`). For the partner, resolve
        the head's row through `mapchunks.MapIndex.partner`.
        """
        own = archive is None
        ar = archive or Archive()
        try:
            table = table if table is not None else file_id_table(ar)
            row = table.get(map_file_id)
            if row is None:
                raise KeyError(f"no file id 0x{map_file_id:X} in the archive")
            return cls.from_row(row, ar, strict=strict)
        finally:
            if own:
                ar.close()

    # -- encoding --------------------------------------------------------

    def encode(self):
        """Container back to bytes. Every `size` here is derived, not replayed.

        The one line that matters is `CHUNK_HEADER.pack(c.chunk_id,
        len(payload))`: the payload is produced first and measured second, so a
        chunk whose typed value changed emits a size that changed with it. There
        is nowhere in this class for an original size to have been kept.
        """
        out = bytearray(self.magic)
        out.append(self.ffna_type)
        for c in self.chunks:
            payload = c.payload()          # bind once: terrain re-encodes on
            out += CHUNK_HEADER.pack(c.chunk_id, len(payload))   # every access
            out += payload
        return bytes(out)

    # -- inspection ------------------------------------------------------

    @property
    def ids(self):
        return [c.chunk_id for c in self.chunks]

    def find(self, chunk_id):
        """The first chunk with this id, or None. Order is what matters here."""
        for c in self.chunks:
            if c.chunk_id == chunk_id:
                return c
        return None

    def terrain(self):
        """The decoded Bloated terrain, or None. Never the Stripped chunk."""
        c = self.find(TERRAIN_CHUNK)
        return c.value if c is not None else None

    def dependencies(self):
        """Every Dependencies chunk, in file order, as (chunk_id, Dependencies)."""
        return [(c.chunk_id, c.value) for c in self.chunks
                if c.form == FORM_DEPENDENCIES]

    def failures(self):
        """Chunks a non-strict decode carried after its decoder refused them."""
        return [c for c in self.chunks if c.note is not None]

    def __len__(self):
        return len(self.chunks)

    def __repr__(self):
        rec = sum(1 for c in self.chunks if c.reconstructed)
        return (f"<MapFile ffna type {self.ffna_type}, {len(self.chunks)} "
                f"chunks, {rec} reconstructed>")


# --------------------------------------------------------------- the census

# What `terrain.py` holds as a `bytes` object and emits without transforming.
# NOT the same set as its docstring's "carried" heading, which is only `bits`
# (tag 3) and `shade` (tag 9) -- it calls tags 2, 4 and 5 FULLY SEMANTIC. Those
# three are counted here anyway, which over-counts carried by 60,502,402 B and
# is the conservative direction. See this module's docstring.
TERRAIN_CARRIED_FIELDS = ("tiles", "bits", "shade", "table_a", "table_b")


def terrain_carried_bytes(trn):
    """How many bytes of a terrain chunk reach the encoder as an opaque `bytes`.

    NOT this module's own measurement of the terrain format, and not terrain.py's
    classification either -- it is stricter, per `TERRAIN_CARRIED_FIELDS`. If
    that module ever gives tags 2, 3, 4, 5 or 9 a typed representation, this
    number is stale and the docstring above with it.
    """
    return sum(len(getattr(trn, f)) for f in TERRAIN_CARRIED_FIELDS)


def byte_census(mf):
    """Where one file's bytes go: framing, reconstructed, carried.

    Returns a dict of byte counts that sums to `len(mf.encode())`. `carried` is
    the number this module is answerable for -- bytes it reproduced without
    understanding -- and it is reported at two levels because the container and
    the terrain codec carry for different reasons.
    """
    out = {"total": 0, "framing": FFNA_HEADER_LEN, "terrain_reconstructed": 0,
           "terrain_carried": 0, "dependencies": 0, "opaque": 0, "chunks": 0}
    for c in mf.chunks:
        n = len(c.payload())
        out["chunks"] += 1
        out["framing"] += CHUNK_HEADER.size
        if c.form == FORM_TERRAIN:
            carried = terrain_carried_bytes(c.value)
            out["terrain_carried"] += carried
            out["terrain_reconstructed"] += n - carried
        elif c.form == FORM_DEPENDENCIES:
            out["dependencies"] += n
        else:
            out["opaque"] += n
    out["total"] = (out["framing"] + out["terrain_reconstructed"]
                    + out["terrain_carried"] + out["dependencies"]
                    + out["opaque"])
    out["reconstructed"] = out["terrain_reconstructed"] + out["dependencies"]
    out["carried"] = out["terrain_carried"] + out["opaque"]
    return out


def add_census(a, b):
    """Accumulate one census into another, in place. Corpus passes want this."""
    for k, v in b.items():
        a[k] = a.get(k, 0) + v
    return a


# ------------------------------------------------------------------- CLI

def _pct(n, d):
    return f"{100.0 * n / d:6.2f}%" if d else "     -"


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None,
                    help="map file id, e.g. 0x345CC (Kamadan, the default)")
    ap.add_argument("--row", type=int, default=None,
                    help="MFT row instead of a file id")
    ap.add_argument("--stripped", action="store_true",
                    help="the Stripped partner of that map instead of the head")
    ap.add_argument("--census", action="store_true",
                    help="byte accounting: reconstructed against carried")
    args = ap.parse_args(argv)

    with Archive(args.dat) as ar:
        if args.row is not None:
            row = args.row
        else:
            fid = int(args.file_id, 0) if args.file_id else 0x345CC
            row = file_id_table(ar).get(fid)
            if row is None:
                print(f"no file id 0x{fid:X} in {args.dat}")
                return 1
        if args.stripped:
            mi = MapIndex(ar)
            head = mi.by_row.get(row)
            partner = mi.partner(head) if head is not None else None
            if partner is None:
                print(f"row {row} has no Stripped partner "
                      f"(nextStream {mapchunks.next_stream(head) if head else '?'})")
                return 1
            row = partner.index

        t0 = time.perf_counter()
        entry = next(e for e in ar.entries if e.index == row)
        data = ar.read(entry)
        mf = MapFile.decode(data)
        t_dec = time.perf_counter() - t0
        t0 = time.perf_counter()
        out = mf.encode()
        t_enc = time.perf_counter() - t0

        ok = out == data
        print(f"row {row}: ffna type {mf.ffna_type}, {len(mf)} chunks, "
              f"{len(data)} bytes")
        print(f"  decode {t_dec:.2f}s   encode {t_enc:.2f}s   "
              f"round-trip {'BYTE-IDENTICAL' if ok else 'DIFFERS'}")
        if not ok:
            n = min(len(out), len(data))
            first = next((i for i in range(n) if out[i] != data[i]), n)
            print(f"  first difference at byte {first}; "
                  f"lengths {len(out)} vs {len(data)}")
        for c in mf.failures():
            print(f"  ! 0x{c.chunk_id:08X} {c.note}")

        print(f"\n  {'#':>3} {'chunk id':>10} {'size':>10}  how            name")
        for i, c in enumerate(mf.chunks):
            n = len(c.payload())
            how = ("RECONSTRUCTED" if c.reconstructed else "carried")
            extra = ""
            if c.form == FORM_TERRAIN:
                extra = f"  [{c.value.dim_x}x{c.value.dim_y}]"
            elif c.form == FORM_DEPENDENCIES:
                extra = f"  [{len(c.value)} refs]"
            print(f"  {i:3d} 0x{c.chunk_id:08X} {n:>10}  {how:<13}  "
                  f"{c.label}{extra}")

        if args.census:
            cen = byte_census(mf)
            tot = cen["total"]
            print(f"\n  byte census over {tot} bytes")
            for key in ("framing", "terrain_reconstructed", "terrain_carried",
                        "dependencies", "opaque"):
                print(f"    {key:<22} {cen[key]:>12}  {_pct(cen[key], tot)}")
            print(f"    {'-- reconstructed':<22} {cen['reconstructed']:>12}  "
                  f"{_pct(cen['reconstructed'], tot)}")
            print(f"    {'-- carried':<22} {cen['carried']:>12}  "
                  f"{_pct(cen['carried'], tot)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())
