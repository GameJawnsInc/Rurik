r"""The model's reference-list chunks: read `0xFA5/0xFA6/0xFA8/0xFAD/0xFAE`.
READ ONLY.

Rung U3 of `studies/unitmodels/PLAN.md`: the five small list chunks a model
file carries next to its geometry (0xFA0) and skeleton (0xFA1), decoded under
the client's own record rule. Nothing here writes a file or emits a byte of
ArenaNet data.

    refs = ref_lists(data)                      # whole ffna type-2 container
    refs[SOUND_CHUNK].file_ids()                # FA6 -> sound-cue file ids
    RefList.decode(payload).records             # one chunk, raw records

WHAT THE CHUNKS ARE (build 38797; derivation and censuses in
`studies/unitmodels/FINDINGS.md` §5 and `studies/mdlrefs/FINDINGS.md`).
All five go through ONE generic reader in the client -- wrapper `0x00796DE0`
-> per-list `0x00794B70` -> per-record scanner `0x00908260`, all in
ArenaNet's `Base\Services\Riff.cpp` / `MdlLoad.cpp` (TU identity via the
assert at MdlLoad:107 inside the shared array helper's error path). The
wrapper has EXACTLY five direct call sites, one per chunk id, each naming
the model-object field the list lands in (all re-read from the binary for
this module, 2026-08-16):

  id     call site    object offsets        what the list is
  0xFA5  0x00794540   +0xC0/+0xC4          texture list (models arc §6.1)
  0xFAD  0x0079455B   +0xFC/+0x100         unnamed; 6-byte records
  0xFA6  0x007947BD   +0x80/+0x84          SOUND CUES -- MdlAnim:2040
                                            `pathIndex<m_skel->m_soundPathCount`
                                            reads +0x80 and indexes the +0x84
                                            array (consumer disassembled at
                                            0x00780D55-0x00780D80), so this
                                            list IS ArenaNet's m_soundPaths
  0xFA8  0x007947D6   +0x10C/+0x110        LINKED MODELS, resolved recursively
                                            at load (loop 0x00794850-0x0079492D
                                            through the cached by-id loader
                                            0x00794260, resolved objects into a
                                            fresh count*4 array at +0x114)
  0xFAE  0x00794815   +0x9C/+0xA0          unnamed; population EXACTLY 6
                                            chunks / 22 records, and every
                                            target is a complete geometry-
                                            bearing model (FA0+FA1+FA5+FAD)
                                            -- the inverse of FA8's targets

THE RECORD RULE, read from the scanner at `0x00908260` (an 11-instruction
scan body -- the U3 review re-counted it):
a chunk is `u32 count` then `count` records, each a run of u16 words ENDED BY
THE FIRST ZERO WORD (terminator consumed, `cmp word ptr [eax], 0` at
0x00908274). Records are VARIABLE length. ArenaNet's own name for a record is
`pathName` (MdlLoad:2201 `PathIsRelative(pathName)` guards the FA8 loop at
0x00794883): a record is a NUL-terminated wide string, and a 2-wchar one is
the file-id spelling `mapchunks.dependency_file_id` decodes (CpsData:468/469
FILE_ID_RESERVED_BIT / FILE_ID_MAX_PATH). In the study archive every FA6/FA8/
FAD record observed is exactly 2 wchars; FA5 additionally carries 0-wchar
NULL SLOTS -- which is what refutes the rival fixed-6-byte framing (it
mis-frames the first null slot). MEASURED at FULL POPULATION, 2026-08-16,
through this module over every flags=515 head (30,722 chunks, zero decode
failures; `studies/mdlrefs/FINDINGS.md`): FA5 20,661 chunks / 5,393 with
null slots / 11,894 slots; FA6 3,734; FA8 252; FAD 6,069; FAE 6. Record
lengths OTHER than 0 and 2 wchars occur NOWHERE in that population; a
non-2-wchar record would be an actual path string, which `record_text`
exposes.

EDGE SEMANTICS, replicated exactly from the scanner: the word at byte p is
readable only while `p < len - 1` (the scanner decrements its end bound
before the loop, 0x0090826B), so an odd trailing byte is unreachable and a
record with no zero word before the bound is a REFUSAL (the client returns
NULL at 0x00908283 and the whole list comes back empty). Two checks here are
OURS and deliberately stricter than the client, the same posture
`skelfile.py` takes: (1) the client silently yields an empty list on a
malformed record (error path 0x00794C27 returns 0 with no assert) where this
module raises `Undecodable` -- an unreadable list is a finding, not an
absence; (2) the client never compares its final cursor to the chunk's end
(0x00794B70 copies exactly the consumed bytes, no closure test), so
`cursor == len(payload)` is an assertion the artifact can refute, and the
full-population closure counts in the study doc are real checks.

THE TYPE-8 HOP (`type8_deps`): an FA6 record's file id resolves to an ffna
TYPE-8 sound descriptor whose chunk 0x1 is a further dependency list --
COUNT-LESS, `len % 6 == 0` (MEASURED 60/60 + every sampled descriptor;
the client-side reader for it has not been disassembled, so the framing
choice count-less-fixed-6 is MEASURED shape, not SOURCE-CODE rule). Its
targets are the audio payloads; `mpeg_frame_header` validates one as an
MPEG-1 Layer III frame header BY FIELD VALUES ONLY -- it copies nothing --
which is the oracle that separates "sound-cue list" from "a list that
happens to resolve" (231/231 in the study; re-pinned by `test_mdlrefs.py`).

This module deliberately does NOT re-implement the map-side sound chain:
`soundchunk.py` owns the map's ambient-emitter chunk and its dependency
indices; the convergence point (both reach ffna type-8 descriptors) is
documented there and in the study docs.
"""

import argparse
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, ffna_type, \
    file_id_table  # noqa: E402
from mapchunks import dependency_file_id  # noqa: E402

#: The five list-chunk ids, in the loader's own fetch order for the
#: FA6/FA8/FAE group (0x00794780) and the FA5/FAD group (0x00794520).
TEXTURE_CHUNK = 0x00000FA5      # -> +0xC0/+0xC4   (modelfile.TEXNAME_CHUNK_B)
SOUND_CHUNK = 0x00000FA6        # -> +0x80/+0x84   m_soundPaths (MdlAnim:2040)
LINK_CHUNK = 0x00000FA8         # -> +0x10C/+0x110 linked models, recursive
FAD_CHUNK = 0x00000FAD          # -> +0xFC/+0x100  unnamed
FAE_CHUNK = 0x00000FAE          # -> +0x9C/+0xA0   unnamed, population 6

REF_CHUNKS = (TEXTURE_CHUNK, SOUND_CHUNK, LINK_CHUNK, FAD_CHUNK, FAE_CHUNK)

MODEL_FFNA_TYPE = 2
SOUND_FFNA_TYPE = 8             # FA6 targets: ffna type-8 sound descriptors
TYPE8_DEP_CHUNK = 0x00000001    # the descriptor's own count-less dep list


class Undecodable(ValueError):
    """The bytes refuse the record rule. `gate` names the refusal."""

    def __init__(self, gate, detail):
        super().__init__(f"{gate}: {detail}")
        self.gate = gate


def decode_records(payload):
    """The generic list chunk: u32 count, then `count` null-word-terminated
    records. Returns a list of tuples of u16 words (terminators dropped).

    Replicates the client's scanner `0x00908260` exactly -- a word at byte p
    is readable only while p < len-1, a record with no terminator in bounds
    is a refusal -- plus OUR closure check (cursor == len), which the client
    does not perform (see module docstring).
    """
    n = len(payload)
    if n < 4:
        # The client's wrapper skips a sub-4-byte chunk silently
        # (0x00796E1C..0x00796E1E ja); occurs on 0 corpus chunks, so the
        # honest reading of one would be nothing to decode. We refuse.
        raise Undecodable("G00_count", f"{n} bytes is under the 4-byte count")
    count, = struct.unpack_from("<I", payload, 0)
    c = 4
    records = []
    for i in range(count):
        # 0x00908270: record may not start at/after len-1.
        words = []
        terminated = False
        while c < n - 1:                       # 0x0090827F  cmp eax, end-1
            w, = struct.unpack_from("<H", payload, c)
            c += 2
            if w == 0:                         # 0x00908274  cmp word [eax], 0
                terminated = True
                break
            words.append(w)
        if not terminated:
            # The client returns NULL here (0x00908283) and the whole list
            # loads empty; we name the record instead.
            raise Undecodable(
                "G01_terminator",
                f"record {i} of {count} has no zero word before byte {n - 1}")
        records.append(tuple(words))
    if c != n:
        # OUR closure check; the client never does this (0x00794B70).
        raise Undecodable(
            "G02_close", f"{count} records end at byte {c} of {n}")
    return records


def record_file_id(rec):
    """A record's file id, or None.

    A 2-wchar pathName is the file-id spelling (dependency-pair formula);
    a 0-wchar record is a NULL SLOT (observed only on FA5). Any other
    length is a real path string, not a file id -- `record_text` reads it.
    """
    if len(rec) == 2:
        return dependency_file_id(rec[0], rec[1])
    return None


def record_text(rec):
    """The record as the wide string the client's pathName reading implies."""
    return b"".join(struct.pack("<H", w) for w in rec).decode(
        "utf-16-le", "replace")


class RefList:
    """One decoded reference-list chunk."""

    __slots__ = ("records",)

    def __init__(self, records):
        self.records = records

    @classmethod
    def decode(cls, payload):
        return cls(decode_records(payload))

    def __len__(self):
        return len(self.records)

    def file_ids(self):
        """One entry per record: an int file id, or None for a null slot or
        a non-2-wchar record (none of the latter exist in the study archive).
        """
        return [record_file_id(r) for r in self.records]

    def null_slots(self):
        """How many records are empty (terminator-only). FA5's are why the
        fixed-6 rival framing is wrong; 0 on every observed FA6/FA8/FAD."""
        return sum(1 for r in self.records if not r)


def ref_lists(data):
    """Every reference-list chunk of an ffna type-2 container, as
    {chunk_id: RefList}. Ids absent from the file are absent from the dict.
    """
    t = ffna_type(data)
    if t != MODEL_FFNA_TYPE:
        raise ValueError(f"ffna type {t}, not the model type "
                         f"{MODEL_FFNA_TYPE} these chunks live in")
    out = {}
    for cid, off, size in ffna_chunks(data):
        if cid in REF_CHUNKS:
            out[cid] = RefList.decode(bytes(data[off:off + size]))
    return out


def load(file_id, archive_):
    """ref_lists() for an archive file id."""
    table = file_id_table(archive_)
    row = table.get(file_id)
    if row is None:
        raise KeyError(f"file id {file_id} not in the archive's id table")
    return ref_lists(archive_.read(archive_.row(row)))


# ---------------------------------------------------------------------------
# The type-8 hop and the MPEG oracle (see docstring).
# ---------------------------------------------------------------------------

def type8_deps(payload):
    """File ids of an ffna type-8 descriptor's chunk 0x1 dependency list.

    COUNT-LESS: `len % 6 == 0`, each entry `{u16 id0, u16 id1, u16 0}`
    (MEASURED shape; the client-side reader is not disassembled). A length
    not divisible by 6 is a refusal, not a truncation.
    """
    n = len(payload)
    if n % 6:
        raise Undecodable("G03_type8mod6", f"{n} bytes is not a multiple of 6")
    out = []
    for i in range(n // 6):
        id0, id1, term = struct.unpack_from("<HHH", payload, i * 6)
        if term != 0:
            raise Undecodable(
                "G04_type8term",
                f"entry {i} ends 0x{term:04X}, not the zero terminator")
        out.append(dependency_file_id(id0, id1))
    return out


#: MPEG-1 Layer III frame-header tables, from the MPEG-1 audio spec
#: (ISO/IEC 11172-3) -- public format constants, not client data.
_MPEG1_L3_BITRATE = (None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
                     224, 256, 320, None)
_MPEG1_SAMPLERATE = (44100, 48000, 32000, None)


def mpeg_frame_header(b):
    """Parse 4 bytes as an MPEG-1 Layer III frame header, or return None.

    Field-validity only -- sync 0x7FF, version MPEG-1, layer III, a real
    bitrate, a real sample rate. Copies no audio. This is the oracle behind
    "FA6 is the sound-cue list": a wrong pair formula does not produce runs
    of consecutive valid headers (231/231 in the study).
    """
    if len(b) < 4:
        return None
    h, = struct.unpack(">I", b[:4])
    if (h >> 21) & 0x7FF != 0x7FF:
        return None
    if (h >> 19) & 3 != 3:          # 3 = MPEG-1
        return None
    if (h >> 17) & 3 != 1:          # 1 = Layer III
        return None
    bitrate = _MPEG1_L3_BITRATE[(h >> 12) & 0xF]
    samplerate = _MPEG1_SAMPLERATE[(h >> 10) & 3]
    if bitrate is None or samplerate is None:
        return None
    return {"bitrate_kbps": bitrate, "samplerate": samplerate}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=None, help="archive path; default: "
                    "the study archive via vaultpath")
    ap.add_argument("--file-id", type=int, required=True,
                    help="decode one file id's reference-list chunks")
    args = ap.parse_args(argv)
    if args.dat is None:
        import vaultpath
        args.dat = os.path.join(
            vaultpath.require_dir("dat_study", why="mdlrefs CLI"), "Gw.dat")
    names = {TEXTURE_CHUNK: "FA5 textures", SOUND_CHUNK: "FA6 soundPaths",
             LINK_CHUNK: "FA8 links", FAD_CHUNK: "FAD (unnamed)",
             FAE_CHUNK: "FAE (unnamed)"}
    with Archive(args.dat) as ar:
        refs = load(args.file_id, ar)
        if not refs:
            print("no reference-list chunks in this file")
            return 1
        table = file_id_table(ar, raw=True)
        for cid in REF_CHUNKS:
            if cid not in refs:
                continue
            rl = refs[cid]
            print(f"{names[cid]}: {len(rl)} record(s), "
                  f"{rl.null_slots()} null slot(s)")
            for rec in rl.records:
                fid = record_file_id(rec)
                if fid is None:
                    print(f"  {'<null slot>' if not rec else record_text(rec)}")
                else:
                    print(f"  file id {fid}"
                          f"  (row {table.get(fid, '-- not addressable')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
