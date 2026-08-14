"""What a map file is made of: chunk ids, the two MFT rows behind every map, and
the dependency lists that name the files a map needs.

This is the layer under every other map tool. `pathmap.py` and the terrain codec
each know one chunk; nothing until now knew what the *container* is -- which
chunk ids are legal, which of them the client would jump to address zero on, that
a map is two MFT rows rather than one, or how to turn a Dependencies chunk into
the file ids it references. Those are the facts an authoring pass has to get
right before any single chunk's bytes matter.

It also carries rung A0: a per-map chunk INDEX, cached in the vault. A corpus
pass over 349 maps costs about seven minutes because `Archive.read()`
decompresses, and a check that costs seven minutes is a check that gets run once.
The cache stores offsets and sizes only -- never payload bytes -- so a warm run
answers "which chunks does every map carry, in what order, at what size" in about
a second, and the expensive read only happens for the checks that actually need
the bytes.

WHERE THE LAYOUT COMES FROM.

  * The id decomposition `(stage << 28) | (chunkType << 24) | baseId` and the
    23-slot name table are SOURCE-CODE, from studies/customarea/FINDINGS.md §3:
    `s_stageText` @ 0xBF7128 and `s_typeText` @ 0xBF7134 are the client's own
    UTF-16 strings, and `s_chunkInfo` @ 0x00A6CF78 is 23 records x 40 bytes with
    a UTF-16 name at +36. The `chunkType << 24` term is INFERRED there -- the
    composition site only ORs a constant -- and it is corroborated here by the
    archive's own bit-24 histogram.
  * The four NULL-load slots (0x01, 0x05, 0x0B, 0x0D) are SOURCE-CODE:
    MapData:4415 asserts `id < arrsize(s_chunkInfo)` and MapData:4417 asserts
    `info.load != NULL`, and those four are exactly the four the archive never
    uses. Authoring one is not a parse error, it is a jump to address 0.
  * The MFT `alloc` byte split is SOURCE-CODE, from FINDINGS §17.4/§18:
    ArenaNet's own asserts at ExeArchive:1418/1419/1421/1422 name `alloc.flags`
    (+0x0E, bit 0 USED, bit 1 FIRST_STREAM), `alloc.stream` (+0x0F) and
    `alloc.nextStream` (+0x10).
  * The Dependencies record `{u16 id0, u16 id1, u16 pad}` and the file id formula
    `(id0 - 0xFF00FF) + id1 * 0xFF00` are UPSTREAM (FINDINGS §3), and are
    MEASURED here -- see below. Upstream is GuildWarsMapBrowser
    (`MapFileRef`/`MapFileRefPadded` in its ImHex FFNA pattern, and the same
    expression in `SourceFiles/animation_state.cpp`); its licence is not MIT and
    wants visible credit, so the derivation is registered in `PLAN.md` §6.1 and
    the module is named in `THIRD-PARTY-NOTICES.md`. Nothing else here is theirs:
    the signature `0x29939830`, the `(size - 5) % 6` law and the aliasing
    correction below are ours, and GWMB has none of them.

WHAT MAKES IT EVIDENCE ANYWAY. Each of these is a claim the archive can refute,
and the numbers are from this machine's study copy (177,342 entries):

  * MEASURED, 349/349: every `alloc.flags == 3, alloc.stream == 1` row resolves
    its `nextStream` to a real MFT row, all 349 partners are `(1, 0)`, all 349
    partners are distinct, and every partner's own `nextStream` is 0 -- chain
    depth is exactly 1, never 0 and never 2.
  * MEASURED, 349/349: the file-id table names every head row exactly twice and
    names ZERO of the 349 partners. A partner is reachable only by walking the
    chain, which is why a writer must not register one.
  * MEASURED over all 698 files of all 349 map pairs: 16,094 chunk ids, every one
    decomposing into a named stage, a named chunkType and one of the 23 slots;
    19 distinct slots occupied and the four unoccupied ones are exactly the four
    NULL-load slots; 0 occurrences of a NULL-load id; heads all stage Bloated and
    partners all stage Stripped with 0 misfiled; Header present in 698/698; Map
    Parameters at chunk index 1 and before Terrain in 349/349; and 0 files
    carrying a Dependencies list for a chunk kind they do not also carry as Data.
  * MEASURED: the whole `(alloc.flags, alloc.stream)` census of the archive is
    {(3,0): 110852, (1,0): 21769, (3,2): 21421, (1,11): 21420, (1,1): 1118,
    (1,12): 393, (3,1): 349, (0,0): 12, (3,255): 7}. The map heads are the entire
    (3,1) bucket. Reading `flags` as one opaque u16 gives the same 349 rows, but
    it cannot tell you that 21,421 other rows are also FIRST_STREAM.
  * MEASURED over all 349 maps: 2,252 Dependencies lists holding 134,290
    references, 0 refused by the header gate, 0 unresolved through the archive's
    own file-id table, `(size - 5) % 6 == 0` everywhere, and the third u16 zero
    in 134,290 of 134,290 entries. That the third u16 is *padding* rather than a
    field nobody uses is INFERRED, exactly as FINDINGS §3 has it. Those two
    counts reproduce §3's independently, from a walker that shares no code with
    the one that produced them.
    Re-encoding each chunk from the decoded triples reproduces its bytes exactly,
    so the record framing is checked against ArenaNet's encoder rather than
    against our own decoder. The resolution number is only worth having because
    it is exhaustive: §3 measured that a random id in range resolves 45% of the
    time, and a radix of 0xFF01 instead of 0xFF00 still resolves 1,546 of 2,865
    sampled references here. One reference resolving proves nothing.
  * The corpus-wide `id1` census is {0x100: 58,277, 0x101: 17,544, 0x102: 19,512,
    0x103: 21,990, 0x104: 16,112, 0x105: 855} -- six values, so a file id in this
    archive never needs more than 21 bits.

WHERE THE SOURCE IS WRONG, and what deriving the inverse turned up.

**The dependency pair encoding is not one-to-one, and ArenaNet's own writer uses
both forms.** `id0` is a u16 but the radix is `0xFF00`, so the 256 values
`id0 >= 0xFF00` alias onto `(id0 - 0xFF00, id1 + 1)` and name exactly the same
file id. MEASURED over all 349 maps: **85 aliased entries, in 84 of the 2,252
Dependencies chunks, spread over 76 maps** -- 0.06% of references, which is
exactly the density at which a sampled test passes and a corpus pass does not.
Row 34243's Environment list stores `(0xFF02, 0x0100)` where the canonical pair
is `(0x0002, 0x0101)`; both decode to file id `0xFE03`, which resolves. Nothing
upstream mentions this, because nobody upstream wrote the inverse -- FINDINGS §3
states the decode only, and this fell out of writing one so the round-trip could
be run against real bytes. The consequence is concrete:
`encode_dependencies(file_ids)` is a left inverse of the decode ON FILE IDS and
NOT ON BYTES, so a tool that rewrites a chunk from ids alone will silently change
bytes on 76 maps, and `encode_dependency_entries` is what a byte-preserving pass
must call. MEASURED, and this is the part that says nothing ELSE is being missed
-- stated per RECORD rather than per chunk, because a per-chunk rule would excuse
84 chunks wholesale: of the 134,290 records, every one re-encodes byte-identically
when its stored pair is canonical and every one comes back CHANGED when it is
aliased. **0 records break that rule in either direction.**

`toolkit/mapdata/archive.py` names two MFT fields
after what an early pass guessed they were: `Entry.counter` is not a counter, it
is `alloc.nextStream`, an MFT row index; and `Entry.flags` is not one field, it
is the two independent bytes `alloc.flags` and `alloc.stream`. That file is owned
by another session and is not renamed here, so this module exposes correctly
named accessors over it -- `alloc_flags()`, `alloc_stream()`, `next_stream()` --
and every caller in the map layer should go through them. `entry.flags == 259` is
not wrong today; it is one number standing in for two facts, and a writer that
treats it as one field has no way to emit a partner correctly.

WHAT THIS MODULE DOES NOT KNOW. Nothing here parses a chunk PAYLOAD except
Dependencies. The chunk index is offsets and sizes; the names are labels. A row
index is only meaningful against the archive copy it was measured on (file ids
are the portable key), which is why the cache stamps the copy it was built from
and refuses to be read against a different one.

    python toolkit/mapdata/mapchunks.py                  # id table + row census
    python toolkit/mapdata/mapchunks.py --row 46196      # one map's chunk index
    python toolkit/mapdata/mapchunks.py --deps 46196     # its dependency lists
    python toolkit/mapdata/mapchunks.py --build          # warm the vault cache
    python toolkit/mapdata/mapchunks.py --build --partners
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, ffna_type, file_id_table  # noqa: E402
from archive import DEFAULT_DAT, FILE_ID_TABLE_ROW  # noqa: E402
import vaultpath  # noqa: E402


# ---------------------------------------------------------------- chunk ids

STAGE_RAW = 0
STAGE_STRIPPED = 1
STAGE_BLOATED = 2
STAGE_NAMES = ("Raw", "Stripped", "Bloated")        # s_stageText @ 0xBF7128

TYPE_DATA = 0
TYPE_DEPENDENCIES = 1
TYPE_NAMES = ("Data", "Dependencies")               # s_typeText @ 0xBF7134

STAGE_SHIFT = 28
TYPE_SHIFT = 24
BASE_MASK = 0x00FFFFFF

# s_chunkInfo @ 0x00A6CF78 is 23 records of 40 bytes; the name is the UTF-16
# string at +36. The stride is refutable and was refuted the other way: 40 bytes
# decodes 23/23 as clean UTF-16 where 32/36/44/48 give 0/3/3/4.
#
# UNVERIFIED, and deliberately flagged: slots 0x01/0x0D and 0x05/0x0B carry the
# same two names twice ("Editor", "Obsolete"). The parenthetical suffixes below
# are FINDINGS §3's disambiguation for the reader, not extra bytes in the client.
CHUNK_NAMES = (
    "Header",           # 0x00  the only slot with a NULL +0x00 -- must be present
    "Editor (old)",     # 0x01  NULL load
    "Terrain",          # 0x02
    "Zones",            # 0x03
    "Props",            # 0x04
    "Obsolete (1)",     # 0x05  NULL load
    "Water",            # 0x06
    "Mission",          # 0x07
    "Path",             # 0x08
    "Environment",      # 0x09
    "Locations",        # 0x0A
    "Obsolete (2)",     # 0x0B  NULL load
    "Map Parameters",   # 0x0C
    "Editor",           # 0x0D  NULL load
    "Collision",        # 0x0E
    "Light",            # 0x0F
    "Shore",            # 0x10
    "Sight",            # 0x11
    "Sound",            # 0x12
    "CubeMap",          # 0x13
    "VisData",          # 0x14
    "Occluders",        # 0x15
    "PathEngine",       # 0x16
)
# arrsize(s_chunkInfo). MapData:4415 asserts id < this, and the fetch that
# follows runs past the table anyway when the assert is compiled out.
MAX_BASE_ID = len(CHUNK_NAMES)                       # 23 == 0x17

# The four slots whose `load` pointer is NULL. The loader does NOT null-check the
# pointer it fetches, so authoring one of these is a call to address 0 -- not a
# rejected chunk. Never emit them. (SOURCE-CODE, FINDINGS §3/§17.5.)
NULL_LOAD_BASE_IDS = frozenset({0x01, 0x05, 0x0B, 0x0D})

BASE_HEADER = 0x00
BASE_TERRAIN = 0x02
BASE_ZONES = 0x03
BASE_PROPS = 0x04
BASE_PATH = 0x08
BASE_MAP_PARAMETERS = 0x0C


class ChunkId:
    """One decomposed chunk id. Immutable, cheap, and prints as itself."""

    __slots__ = ("value", "stage", "chunk_type", "base_id")

    def __init__(self, value, stage, chunk_type, base_id):
        self.value = value
        self.stage = stage
        self.chunk_type = chunk_type
        self.base_id = base_id

    @property
    def name(self):
        return CHUNK_NAMES[self.base_id]

    @property
    def stage_name(self):
        return STAGE_NAMES[self.stage]

    @property
    def type_name(self):
        return TYPE_NAMES[self.chunk_type]

    @property
    def null_load(self):
        """True if the client's handler slot for this kind is a NULL pointer."""
        return self.base_id in NULL_LOAD_BASE_IDS

    def __eq__(self, other):
        return isinstance(other, ChunkId) and other.value == self.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return (f"<0x{self.value:08X} {self.stage_name} {self.type_name} "
                f"{self.name}>")

    def __str__(self):
        return f"{self.stage_name} {self.type_name} {self.name}"


def compose(stage, chunk_type, base_id):
    """Build a chunk id. Refuses anything the client's table cannot hold."""
    if not 0 <= stage < len(STAGE_NAMES):
        raise ValueError(f"stage {stage} is not one of {STAGE_NAMES}")
    if not 0 <= chunk_type < len(TYPE_NAMES):
        raise ValueError(f"chunkType {chunk_type} is not one of {TYPE_NAMES}")
    if not 0 <= base_id < MAX_BASE_ID:
        raise ValueError(
            f"baseId 0x{base_id:X} is outside s_chunkInfo's {MAX_BASE_ID} slots; "
            "the client asserts and then indexes past the table anyway")
    return (stage << STAGE_SHIFT) | (chunk_type << TYPE_SHIFT) | base_id


def decompose(value):
    """Split a chunk id into (stage, chunkType, baseId), or refuse it.

    Deliberately stricter than the client: an id the client would crash on is an
    id this raises on. Stage Raw (0) is accepted because it is a real stage the
    client names -- it just never ships.
    """
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"chunk id {value} is not a u32")
    stage = (value >> STAGE_SHIFT) & 0xF
    chunk_type = (value >> TYPE_SHIFT) & 0xF
    base_id = value & BASE_MASK
    if stage >= len(STAGE_NAMES):
        raise ValueError(f"chunk id 0x{value:08X}: stage nibble {stage} is not "
                         f"one of {STAGE_NAMES}")
    if chunk_type >= len(TYPE_NAMES):
        raise ValueError(f"chunk id 0x{value:08X}: chunkType {chunk_type} is not "
                         f"one of {TYPE_NAMES}")
    if base_id >= MAX_BASE_ID:
        raise ValueError(f"chunk id 0x{value:08X}: baseId 0x{base_id:X} is "
                         f"outside s_chunkInfo's {MAX_BASE_ID} slots")
    return ChunkId(value, stage, chunk_type, base_id)


def chunk_label(value):
    """A printable name for a chunk id, falling back to hex when it is illegal."""
    try:
        return str(decompose(value))
    except ValueError:
        return f"0x{value:08X} (undecodable)"


# ------------------------------------------------------- the MFT alloc bytes

# archive.py packs +0x0E and +0x0F into one u16 it calls `flags`. They are two
# independent bytes; see the module docstring.
FLAG_USED = 0x01
FLAG_FIRST_STREAM = 0x02

MAP_HEAD_ALLOC_FLAGS = FLAG_USED | FLAG_FIRST_STREAM     # 3
MAP_HEAD_STREAM = 1                                      # Bloated
MAP_PARTNER_ALLOC_FLAGS = FLAG_USED                      # 1
MAP_PARTNER_STREAM = 0                                   # Stripped

# What `entry.flags == 259` means when read as one number. Kept so the identity
# is asserted somewhere rather than assumed at 40 call sites.
MAP_HEAD_FLAGS_U16 = (MAP_HEAD_STREAM << 8) | MAP_HEAD_ALLOC_FLAGS      # 259
MAP_PARTNER_FLAGS_U16 = (MAP_PARTNER_STREAM << 8) | MAP_PARTNER_ALLOC_FLAGS  # 1


def alloc_flags(entry):
    """`alloc.flags` (+0x0E): bit 0 USED, bit 1 FIRST_STREAM."""
    return entry.flags & 0xFF


def alloc_stream(entry):
    """`alloc.stream` (+0x0F): which stream of the file this row holds.

    For a map, 1 is the Bloated head and 0 is the Stripped partner.
    """
    return (entry.flags >> 8) & 0xFF


def next_stream(entry):
    """`alloc.nextStream` (+0x10): the MFT row holding the file's next stream.

    archive.py calls this `counter`. It is not a counter. 0 terminates the chain.
    """
    return entry.counter


def is_map_head(entry):
    """A Bloated map head: the row a file id resolves to."""
    return (alloc_flags(entry) == MAP_HEAD_ALLOC_FLAGS
            and alloc_stream(entry) == MAP_HEAD_STREAM)


class MapIndex:
    """Every map's two MFT rows, resolved once.

    Costs one pass over the MFT (~0.2 s, no decompression). Everything the
    corpus checks need about row structure is here.
    """

    def __init__(self, archive):
        self.archive = archive
        self.by_row = {e.index: e for e in archive.entries}
        self.heads = [e for e in archive.entries if is_map_head(e)]
        self.pairs = []
        self.orphans = []           # heads whose nextStream names no row
        for h in self.heads:
            p = self.by_row.get(next_stream(h))
            if p is None:
                self.orphans.append(h)
            else:
                self.pairs.append((h, p))

    @property
    def partners(self):
        return [p for _h, p in self.pairs]

    def partner(self, head):
        """The Stripped row for a head, or None if the chain is broken."""
        return self.by_row.get(next_stream(head))

    def chain(self, entry):
        """Walk nextStream from `entry`. Returns the rows AFTER it, in order."""
        out = []
        seen = {entry.index}
        cur = entry
        while True:
            nxt = next_stream(cur)
            if nxt == 0 or nxt in seen:
                return out
            cur = self.by_row.get(nxt)
            if cur is None:
                return out
            seen.add(cur.index)
            out.append(cur)


FILE_ID_RECORD = struct.Struct("<II")           # (file_id, row), MFT row 2


def stored_file_ids(archive):
    """row -> the file ids the archive's id table actually stores for it.

    Deliberately NOT built from `archive.file_id_table()`. That dict registers
    each of the 25 bit-31 ids under both its raw and its masked form, which is
    right for lookup and wrong for counting: it reports three ids for the two map
    rows behind a high-bit id, when the table stores two. This reads MFT row 2 as
    it sits, because the claim being checked is about what the archive holds.
    """
    blob = archive.read(archive.row(FILE_ID_TABLE_ROW))
    out = {}
    for i in range(len(blob) // FILE_ID_RECORD.size):
        fid, row = FILE_ID_RECORD.unpack_from(blob, i * FILE_ID_RECORD.size)
        out.setdefault(row, []).append(fid)
    return out


# ----------------------------------------------------------- dependencies

DEPENDENCY_SIGNATURE = 0x29939830
DEPENDENCY_VERSION = 1
DEPENDENCY_HEADER = struct.Struct("<IB")        # 5 bytes: u32 sig, u8 version
DEPENDENCY_ENTRY = struct.Struct("<HHH")        # 6 bytes: id0, id1, pad
DEPENDENCY_BIAS = 0xFF00FF
DEPENDENCY_RADIX = 0xFF00


def dependency_file_id(id0, id1):
    """The file id a `{u16 id0, u16 id1}` pair names.

    UPSTREAM formula (FINDINGS §3), MEASURED here: every id it produces resolves
    through the archive's own file-id table.
    """
    return (id0 - DEPENDENCY_BIAS) + id1 * DEPENDENCY_RADIX


def dependency_pair(file_id):
    """A `(id0, id1)` pair naming `file_id` -- the canonical one, `id0 < 0xFF00`.

    Derived rather than sourced: no upstream we have states the inverse, and
    deriving it is what let the decode be round-tripped against ArenaNet's bytes
    instead of against our own decoder. Doing that immediately produced the
    correction in the module docstring -- THE ENCODING IS NOT ONE-TO-ONE. `id0`
    is a u16 and the radix is 0xFF00, so the 256 values `id0 >= 0xFF00` alias
    onto `(id0 - 0xFF00, id1 + 1)`, and ArenaNet's own writer emits the aliased
    form sometimes. This function always returns the canonical member, which is
    correct for a writer and is NOT a way to reproduce an existing chunk's bytes;
    for that, carry the stored pairs and use `encode_dependency_entries`.
    """
    n = file_id + DEPENDENCY_BIAS
    if n < 0:
        raise ValueError(f"file id {file_id} has no representation "
                         f"(it is below the encoding's floor of "
                         f"{-DEPENDENCY_BIAS})")
    id1, id0 = divmod(n, DEPENDENCY_RADIX)
    if id1 > 0xFFFF:
        raise ValueError(f"file id {file_id} needs id1 0x{id1:X}, wider than u16")
    return id0, id1


def is_canonical_pair(id0, id1):
    """False for the aliased encoding `id0 >= 0xFF00`. See dependency_pair."""
    return dependency_pair(dependency_file_id(id0, id1)) == (id0, id1)


class Dependencies:
    """A decoded Dependencies chunk: the files one chunk kind of a map needs."""

    __slots__ = ("signature", "version", "entries")

    def __init__(self, signature, version, entries):
        self.signature = signature
        self.version = version
        self.entries = tuple(entries)           # (id0, id1, pad) triples

    @property
    def file_ids(self):
        return [dependency_file_id(a, b) for a, b, _pad in self.entries]

    @property
    def pads(self):
        return [pad for _a, _b, pad in self.entries]

    def __len__(self):
        return len(self.entries)

    def __repr__(self):
        return (f"<Dependencies v{self.version} {len(self.entries)} refs>")


def decode_dependencies(payload):
    """Parse a Dependencies chunk payload. Raises rather than guessing.

    `(len - 5) % 6 == 0` is the size law; a payload that does not satisfy it is
    refused, because the alternative is reading a partial trailing entry as if
    it were data.
    """
    if len(payload) < DEPENDENCY_HEADER.size:
        raise ValueError(f"dependency chunk is {len(payload)} bytes, shorter "
                         f"than its {DEPENDENCY_HEADER.size}-byte header")
    signature, version = DEPENDENCY_HEADER.unpack_from(payload, 0)
    if signature != DEPENDENCY_SIGNATURE:
        raise ValueError(f"dependency signature 0x{signature:08X}, expected "
                         f"0x{DEPENDENCY_SIGNATURE:08X}")
    if version != DEPENDENCY_VERSION:
        raise ValueError(f"dependency version {version}, expected "
                         f"{DEPENDENCY_VERSION}")
    body = len(payload) - DEPENDENCY_HEADER.size
    if body % DEPENDENCY_ENTRY.size:
        raise ValueError(
            f"dependency body is {body} bytes, not a whole number of "
            f"{DEPENDENCY_ENTRY.size}-byte entries "
            f"({body % DEPENDENCY_ENTRY.size} left over)")
    entries = [DEPENDENCY_ENTRY.unpack_from(
                   payload, DEPENDENCY_HEADER.size + i * DEPENDENCY_ENTRY.size)
               for i in range(body // DEPENDENCY_ENTRY.size)]
    return Dependencies(signature, version, entries)


def encode_dependency_entries(entries, version=DEPENDENCY_VERSION,
                              signature=DEPENDENCY_SIGNATURE):
    """Emit a Dependencies payload from stored `(id0, id1, pad)` triples.

    This is the one that can reproduce an existing chunk byte for byte, because
    it carries the pair the archive stored rather than re-deriving one -- and the
    encoding aliases, so re-derivation is not always the same bytes. Framing
    only: it decides nothing about which files a map needs.
    """
    out = bytearray(DEPENDENCY_HEADER.pack(signature, version))
    for id0, id1, pad in entries:
        out += DEPENDENCY_ENTRY.pack(id0, id1, pad)
    return bytes(out)


def encode_dependencies(file_ids, version=DEPENDENCY_VERSION,
                        signature=DEPENDENCY_SIGNATURE, pads=None):
    """Emit a Dependencies chunk payload naming `file_ids`. What a WRITER wants.

    Always emits the canonical `id0 < 0xFF00` pair, so it is a left inverse of
    the decode on file ids and NOT on bytes -- see `dependency_pair`. A map whose
    original chunk used the aliased form re-encodes to different bytes naming the
    same files.

    `pads` exists only so a round-trip against real bytes can carry the third
    u16 verbatim instead of assuming it is always 0. It is 0 in all corpus
    entries, and that it is *padding* is INFERRED, so a writer that invents a
    value there is guessing.
    """
    ids = list(file_ids)
    if pads is None:
        pads = [0] * len(ids)
    if len(pads) != len(ids):
        raise ValueError(f"{len(ids)} file ids but {len(pads)} pad values")
    return encode_dependency_entries(
        [dependency_pair(fid) + (pad,) for fid, pad in zip(ids, pads)],
        version=version, signature=signature)


# ------------------------------------------------- rung A0: the chunk index

CACHE_FORMAT = 1            # bump when the stored shape changes
CACHE_SUBDIR = ("cache", "mapchunks")


class RowIndex:
    """One MFT row's FFNA chunk table: ids, offsets and sizes, in file order.

    Offsets are into the DECOMPRESSED file, so they are only meaningful together
    with `archive.read()` of the same row. No payload bytes are held.
    """

    __slots__ = ("row", "ffna_type", "length", "chunks")

    def __init__(self, row, ffna_type_, length, chunks):
        self.row = row
        self.ffna_type = ffna_type_
        self.length = length
        self.chunks = tuple((int(c), int(o), int(s)) for c, o, s in chunks)

    @property
    def ids(self):
        return [c for c, _o, _s in self.chunks]

    def find(self, chunk_id):
        """(offset, size) for a chunk id, or None. First match wins."""
        for c, o, s in self.chunks:
            if c == chunk_id:
                return o, s
        return None

    def position(self, chunk_id):
        """Index of a chunk id in the chunk table, or None."""
        for i, (c, _o, _s) in enumerate(self.chunks):
            if c == chunk_id:
                return i
        return None

    def to_json(self):
        return {"type": self.ffna_type, "len": self.length,
                "chunks": [[f"0x{c:08X}", o, s] for c, o, s in self.chunks]}

    @classmethod
    def from_json(cls, row, obj):
        return cls(row, obj["type"], obj["len"],
                   [(int(c, 16), o, s) for c, o, s in obj["chunks"]])

    def __repr__(self):
        return (f"<RowIndex row {self.row} ffna type {self.ffna_type} "
                f"{self.length} B, {len(self.chunks)} chunks>")


def index_file(row, data):
    """Build a RowIndex from one decompressed file's bytes.

    `ffna_chunks` is a GENERATOR and raises unless the walk lands exactly on the
    final byte. Consuming it twice yields nothing the second time -- that bug has
    already silently zeroed one corpus script in this repo -- so it is listed
    once, here, and never re-iterated.
    """
    return RowIndex(row, ffna_type(data), len(data), list(ffna_chunks(data)))


def archive_stamp(archive):
    """The cheap validity stamp: three numbers no edit to the archive survives.

    Not a checksum -- a 4.2 GB CRC per run defeats the point of a cache. It
    catches the cases that actually happen: a different copy of Gw.dat, a client
    that appended rows, a rebuilt MFT.
    """
    return {"format": CACHE_FORMAT,
            "dat": os.path.abspath(archive.path),
            "dat_size": os.path.getsize(archive.path),
            "entry_count": archive.entry_count,
            "mft_offset": archive.mft_offset}


def cache_path_for(dat_path, root=None):
    """Where the index for one archive copy lives, inside the vault.

    Keyed by the archive's absolute path so two copies never share a file, and
    stamped inside so the same path pointing at different bytes is still caught.
    """
    if root is None:
        root = vaultpath.require_dir(
            why="mapchunks caches its per-map chunk index there; a corpus pass "
                "costs ~7 minutes cold and ~1 second warm")
    key = hashlib.sha1(os.path.abspath(dat_path).lower().encode("utf-8"))
    return os.path.join(root, *CACHE_SUBDIR,
                        f"chunkindex-{key.hexdigest()[:12]}.json")


class ChunkIndexCache:
    """row -> RowIndex, persisted in the vault, revalidated on every load.

    A stale cache is DROPPED, not repaired and not trusted: `stale_reason` names
    the field that disagreed and `rows` comes back empty, so the caller pays the
    decompression rather than reading offsets that belong to a different file.
    """

    def __init__(self, stamp, path, archive=None):
        self.stamp = dict(stamp)
        self.path = path
        self.archive = archive
        self.rows = {}
        self.stale_reason = None
        self.loaded = False
        self.hits = 0
        self.misses = 0
        self.dirty = False
        self._by_row = None

    @classmethod
    def open(cls, archive, path=None, root=None):
        """The normal entry point: stamp the archive, load whatever is valid."""
        c = cls(archive_stamp(archive),
                path or cache_path_for(archive.path, root=root),
                archive=archive)
        c.load()
        return c

    def load(self):
        """Adopt the cache file if it matches. Returns True if anything loaded."""
        self.rows = {}
        self.stale_reason = None
        self.loaded = False
        if not os.path.isfile(self.path):
            self.stale_reason = "no cache file yet"
            return False
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                blob = json.load(fh)
            stored = blob["stamp"]
            rows = blob["rows"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            # A truncated or hand-edited cache is the same as no cache. It must
            # never be an exception out of a corpus pass.
            self.stale_reason = f"unreadable ({type(exc).__name__}: {exc})"
            return False
        for field in ("format", "dat_size", "entry_count", "mft_offset"):
            if stored.get(field) != self.stamp.get(field):
                self.stale_reason = (
                    f"{field} differs: cache has {stored.get(field)!r}, "
                    f"archive has {self.stamp.get(field)!r}")
                return False
        try:
            self.rows = {int(r): RowIndex.from_json(int(r), obj)
                         for r, obj in rows.items()}
        except (ValueError, KeyError, TypeError) as exc:
            self.rows = {}
            self.stale_reason = f"row records unreadable ({exc})"
            return False
        self.loaded = True
        return True

    def index(self, row):
        """The RowIndex for a row, decompressing the file only on a miss."""
        hit = self.rows.get(row)
        if hit is not None:
            self.hits += 1
            return hit
        if self.archive is None:
            raise ValueError(f"row {row} is not cached and this cache has no "
                             "archive to read it from")
        if self._by_row is None:
            self._by_row = {e.index: e for e in self.archive.entries}
        entry = self._by_row.get(row)
        if entry is None:
            raise ValueError(f"MFT row {row} does not exist in "
                             f"{self.archive.path}")
        self.misses += 1
        built = index_file(row, self.archive.read(entry))
        self.rows[row] = built
        self.dirty = True
        return built

    def save(self, force=False):
        """Write the cache. Atomic: a crash mid-write leaves the old one intact."""
        if not self.dirty and not force:
            return False
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        blob = {"stamp": self.stamp,
                "rows": {str(r): ri.to_json() for r, ri in sorted(self.rows.items())}}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blob, fh, separators=(",", ":"))
        os.replace(tmp, self.path)
        self.dirty = False
        return True

    def __len__(self):
        return len(self.rows)


def read_chunk(archive, row, chunk_id, cache=None):
    """The raw bytes of one chunk of one row. Decompresses; the cache cannot help.

    Kept out of the cache on purpose: an index of offsets is metadata, a cache of
    payloads would be ArenaNet's bytes sitting in a file we wrote.
    """
    by_row = {e.index: e for e in archive.entries}
    entry = by_row[row]
    data = archive.read(entry)
    if cache is not None and row not in cache.rows:
        cache.rows[row] = index_file(row, data)
        cache.dirty = True
    for cid, off, size in ffna_chunks(data):
        if cid == chunk_id:
            return bytes(data[off:off + size])
    return None


# ------------------------------------------------------------------- CLI

def _print_id_table():
    print(f"chunk id = (stage << {STAGE_SHIFT}) | (chunkType << {TYPE_SHIFT}) "
          f"| baseId")
    print(f"  stages     {dict(enumerate(STAGE_NAMES))}")
    print(f"  types      {dict(enumerate(TYPE_NAMES))}")
    print(f"  {MAX_BASE_ID} slots, {len(NULL_LOAD_BASE_IDS)} of them NULL-load "
          f"(never author these)")
    for base, name in enumerate(CHUNK_NAMES):
        flag = "  <- NULL load" if base in NULL_LOAD_BASE_IDS else ""
        print(f"  0x{base:02X}  {name:<16} "
              f"Bloated Data 0x{compose(STAGE_BLOATED, TYPE_DATA, base):08X}  "
              f"Deps 0x{compose(STAGE_BLOATED, TYPE_DEPENDENCIES, base):08X}"
              f"{flag}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--row", type=int, help="print one MFT row's chunk index")
    ap.add_argument("--deps", type=int, help="decode one row's Dependencies")
    ap.add_argument("--build", action="store_true",
                    help="index every map head into the vault cache")
    ap.add_argument("--partners", action="store_true",
                    help="with --build, index the Stripped partners too")
    ap.add_argument("--ids", action="store_true", help="print the id table only")
    args = ap.parse_args(argv)

    if args.ids or not (args.row or args.deps or args.build):
        _print_id_table()
        if args.ids:
            return 0
        print()

    with Archive(args.dat) as ar:
        mi = MapIndex(ar)
        print(f"{os.path.basename(args.dat)}: {ar.entry_count} MFT rows, "
              f"{len(mi.heads)} map heads, {len(mi.pairs)} with a partner, "
              f"{len(mi.orphans)} orphaned")
        cache = ChunkIndexCache.open(ar)
        print(f"cache: {cache.path}")
        print(f"  {'loaded ' + str(len(cache)) + ' rows' if cache.loaded else 'cold: ' + str(cache.stale_reason)}")

        if args.row:
            ri = cache.index(args.row)
            print(f"\nrow {args.row}: {ri}")
            for i, (cid, off, size) in enumerate(ri.chunks):
                print(f"  {i:2d}  0x{cid:08X}  {size:>9} B  @{off:<9} "
                      f"{chunk_label(cid)}")
            cache.save()

        if args.deps:
            table = file_id_table(ar)
            data = ar.read(mi.by_row[args.deps])     # once, not once per chunk
            ri = cache.index(args.deps)
            print(f"\nrow {args.deps} dependencies")
            for cid, off, size in ri.chunks:
                try:
                    kind = decompose(cid)
                except ValueError:
                    continue
                if kind.chunk_type != TYPE_DEPENDENCIES:
                    continue
                dep = decode_dependencies(bytes(data[off:off + size]))
                ids = dep.file_ids
                miss = [i for i in ids if i not in table]
                alias = sum(1 for a, b, _p in dep.entries
                            if not is_canonical_pair(a, b))
                print(f"  0x{cid:08X} {kind.name:<16} {len(dep):>4} refs, "
                      f"{size} B, {len(miss)} unresolved, {alias} aliased")
            cache.save()

        if args.build:
            rows = [h.index for h in mi.heads]
            if args.partners:
                rows += [p.index for p in mi.partners]
            t0 = time.perf_counter()
            for n, row in enumerate(rows, 1):
                cache.index(row)
                if n % 25 == 0 or n == len(rows):
                    dt = time.perf_counter() - t0
                    print(f"  {n}/{len(rows)}  {cache.hits} hit "
                          f"{cache.misses} read  {dt:.1f}s")
            cache.save()
            print(f"cache holds {len(cache)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
