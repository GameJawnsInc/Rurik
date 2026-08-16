r"""The skeleton/animation chunk: read ffna type 2 chunk `0xFA1`. READ ONLY.

Rung U1 of `studies/unitmodels/PLAN.md`: the layout the 2026-08-16 recon
derived from the client and verified at full population, promoted from the
session walker (`vault/research/unitmodels/2026-08-16-recon/verify/fa1walk.py`)
to committed code. Nothing here writes a file or emits a byte of ArenaNet
data; the writer is rung U6 and does not exist.

    sk = Skeleton.load(116366, archive)      # the burrowing worm
    sk.seq_count                             # ArenaNet's m_seqCount
    sk.key_times_s()                         # key times in seconds (x 1e-5)
    sk.composited                            # MODEL_SKELETON_FLAG_COMPOSITED

WHAT THE CHUNK IS. `0x00000FA1` is fetched by `MdlLoad.cpp` at `0x00794827`
(get-chunk helper `0x00907C70`), gated on size >= 4 and `u32@0 == 0x26`
(`0x0079494C`/`0x0079495D`), and parsed at `0x00796310` into the object
`MdlSeq.cpp` itself calls `m_skel` (`MdlSeq:300` `seqIndex <
m_skel->m_seqCount` reads the +0x6C the parser writes at `0x007964DB`).
It is the ANIMATION side of a model: sequence records selecting spans of a
key-time table, two large gated animation payloads, and a flag byte whose
bit 0 is ArenaNet's `MODEL_SKELETON_FLAG_COMPOSITED` (`MdlBuild:1556`) —
set exactly when the enclosing file carries no `0xFA0` geometry chunk and
its body must arrive from elsewhere (GAME_SMSG 0x0057 on the wire).
SOURCE-CODE + MEASURED, build 38797; the full derivation, the corpus
censuses and every correction are `studies/unitmodels/FINDINGS.md`.

WHY CLOSURE IS A REAL ASSERTION HERE, unlike the geometry chunk's. The
client does NOT compare its cursor to the chunk's end when it finishes —
the success path at `0x00796905` returns 0 unconditionally (verified
independently twice) — so `cursor == len(payload)` is a check WE impose and
the artifact can refute. The derived walk closes on the exact final byte for
**14,571 of 14,571 FA1 chunks — the complete flags=515 population of the
study archive, 371,998,300 bytes, zero failures** (MEASURED 2026-08-16).
The client's own bounds gates are refutable in the other direction: every
advance is checked `cursor + n <= end` (take helper `0x00794B20`, array
helper `0x00794C40`), so a wrong stride dies at a NAMED gate, and the gate
name is the diagnostic `walk()` reports.

WHAT CLOSURE DOES NOT PROVE, so nobody over-reads 14,571: the order of two
adjacent FIXED-size blocks (closure tests the sum; order is pinned only
where a block reads a count out of the stream — blk2C, blk48 and the five
var-arrays, which are most of the format by byte count on unit files); the
CONTENTS of any element; and the strides of blocks the corpus never fires
(`n56`: 0 of 14,571 — its stride is disasm-only, UNVERIFIED, and only the
synthetic fixture in `test_skelfile.py` exercises it).

WHAT IS DECODED, and what stays bytes:

  * The 0x58-byte header: every count the parser reads, at the offsets in
    `HDR`. Fields with no consumer stay unnamed (`u0C`, `f20`, `i30`, ...)
    — naming from size alone is this repo's recorded mistake.
  * The SEQUENCE records (`n18` @ +0x18 = m_seqCount): 0x17 bytes each,
    copied by the client to a 32-byte in-memory record at
    `0x007965A0-0x007965DD`. Only `lo`/`hi` (+0x0D/+0x0E) are named — they
    select `keys[lo:hi]` from the key table, and they earned the name by a
    refutable prediction: `lo <= hi <= n3C` held on 50,127 records with the
    key array located independently, and cannot be forced by this decoder.
    The other six fields are carried raw.
  * The KEY TABLE (`n3C` @ +0x3C) is STRUCTURE-OF-ARRAYS: n3C int32 times,
    then n3C tag bytes — the AoS reading is wrong (the SoA loop is at
    `0x00796540-0x0079656C`). Times are in units of 1e-5 s (qword constant
    at `0x00A571B0`); 99.95% of non-zero corpus times are exact multiples
    of 1/30 s. Within a sequence's span the times are NON-DECREASING
    (9,321/9,321 spans) but NOT strictly increasing (10 corpus files carry
    one exact duplicate each) — ArenaNet's own `MdlAnim:367`
    `keyTimes[lo+1]>keyTimes[lo]` reads a DIFFERENT array (a stride-4
    `fild` int32 array, not these 8-byte records), so strictness is not
    asserted here. Ordering ACROSS sequences is local, not global: only
    79 of 913 multi-key corpus files are globally sorted.
  * The two ANIMATION PAYLOADS — blk2C (n2C @ +0x2C, asserted `animCount`
    at MdlLoad:373) and blk48 (n48 @ +0x48, ALSO asserted `animCount` at
    MdlLoad:432, and INDEPENDENT of n2C: equal on 242 of 971 files where
    both fire; the shared assert name is a helper parameter, not equality)
    — are carried as OPAQUE byte spans. Their strides are byte-exact;
    their element contents are NOT DECODED (a unit-quaternion reading was
    REFUTED at 4/19,460, median norm 6.07).
  * `n2C == 0` is the client's own HARD REJECT (error 12, `0079644E`), not
    a stride failure — and it never occurs in the corpus (0/14,571).
  * Every block's byte span is recorded in `.spans`, in stream order,
    tiling the payload exactly — that is what a re-serializer (rung U6)
    preserves verbatim, the same posture `modelfile.py` takes with vertex
    bits 1/3.

THE FLAG BYTE (+0x08) is a redundant presence bitmap (MEASURED per-row over
all 14,571): bit 0 <=> the file has no 0xFA0 chunk (COMPOSITED); bits
3/5/6/7 <=> n34/n48/n50/n38 non-zero, 14,571/14,571 each. The parser itself
reads only bits 0-2; bits 1 and 2 have NO corpus correlate and are the
arc's open question #2. `flags_presence()` returns the testable pairs.

Every stride below carries the VA of the instruction it was read from, and
sabotage in `test_skelfile.py` works by cloning `TERMS` and changing ONE
key — a term whose mutation closure survives was not being measured.
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

SKELETON_CHUNK = 0x00000FA1
GEOMETRY_CHUNK = 0x00000FA0          # for the COMPOSITED cross-check; same
                                     # value as modelfile.GEOMETRY_CHUNK,
                                     # kept literal so this module's only
                                     # dependency stays archive.py
MODEL_FFNA_TYPE = 2

SKELETON_VERSION = 0x26              # 0x0079495D  cmp dword ptr [ecx], 0x26
KEYTIME_SCALE = 1e-5                 # qword const 0x00A571B0, used 0x00796559-64

#: MODEL_SKELETON_FLAG_COMPOSITED, ArenaNet's name (MdlBuild:1556); the
#: parser sets m_skeletonFlags bit 2 (value 4) from header bit 0 at
#: 0x00796857/0x0079685D. In THIS module the bit is header +0x08 bit 0.
FLAG_COMPOSITED = 0x01

# ---------------------------------------------------------------------------
# Derived terms. Every value carries the VA it was read from (build 38797).
# Sabotage clones this dict and changes ONE key.
# ---------------------------------------------------------------------------
TERMS = {
    "hdr":            0x58,   # 0079632C  lea ecx, [ebx + 0x58]
    "n14_elem":       0x10,   # 00796345  shl eax, 4
    "n34_elem":       24,     # 007963FC lea eax,[eax+eax*2] / 007963FF shl eax,3
    # blk2C (helper 0x00796AD0, assert MdlLoad:373 'animCount')
    "b2c_fixed":      0x10,   # 00796AF9  shl ecx, 4
    "b2c_sub":        6,      # 00796B24  lea edx, [esi + 6]
    "b2c_m04":        16,     # 00796B47  shl ecx, 4        (w0+w4)*16
    "b2c_m20":        20,     # 00796B4A/4D lea,lea         w2*20
    # n38 var-array (helper 0x00794C40, tail cb 0x00797120)
    "n38_elem":       0x0C,   # 00796482  push 0xc
    "n38_cnt_at":     4,      # 0079712B  mov eax,[eax+4]
    "n38_mult":       4,      # 0079712E  lea eax,[edx+eax*4]
    # n3C structure-of-arrays (n3C int32 then n3C bytes)
    "n3c_elem":       5,      # 007964BA  lea ecx, [eax+eax*4]
    # n18 sequence records (m_seqCount, m_skel+0x6C)
    "n18_elem":       0x17,   # 007964D8  imul eax, edx, 0x17
    # n52 var-array (tail cb 0x00796FD0 -- count at rec+0xC, not +4)
    "n52_elem":       0x10,   # 00796614  push 0x10
    "n52_cnt_at":     0x0C,   # 00796FDB  mov eax,[eax+0xc]
    "n52_mult":       4,      # 00796FDE  lea eax,[edx+eax*4]
    "n40_elem":       0x16,   # 00796650  imul ecx, ecx, 0x16
    "n44_elem":       12,     # 00796653/56 lea,lea
    # blk48 (helper 0x00796970, assert MdlLoad:432 'animCount')
    "b48_fixed":      20,     # 00796997 lea eax,[ebx+ebx*4] / 0079699F shl
    "b48_sub":        4,      # 007969D0  lea edx, [esi + 4]
    "b48_m":          16,     # 007969F1  shl esi, 4        (w0+w2)*16
    # five 8-byte var-arrays differing only in tail callback
    "n50_elem":       8,      # 007966E9  push 8   cb 0x00796F80
    "n50_cnt_at":     4,
    "n50_mult":       8,      # 00796F8E  lea eax,[edx+eax*8]
    "n54_elem":       8,      # 00796724  push 8   cb 0x00796F80
    "n54_cnt_at":     4,
    "n54_mult":       8,
    "n55_elem":       8,      # 0079675F  push 8   cb 0x00796F80 (NOT 0x796FA0)
    "n55_cnt_at":     4,
    "n55_mult":       8,
    "n56_elem":       8,      # 0079679A  push 8   cb 0x00796E60   UNVERIFIED:
    "n56_cnt_at":     4,      #   fires on 0 of 14,571 corpus chunks; only the
    "n56_mult":       5,      #   synthetic fixture exercises it. 00796E6F/72
    "n57_elem":       8,      # 007967D5  push 8   cb 0x00796FA0
    "n57_cnt_at":     4,
    "n57_mult":       20,     # 00796FAE/B1 lea,lea  (VERIFIED: 135 files)
    # n3E two raw arrays (VERIFIED: 6 files, sabotage 0/6)
    "n3e_a":          4,      # 0079680B  shl eax, 2
    "n3e_b":          8,      # 00796825  shl eax, 3
}

#: Header offsets, exactly the fields the parser reads (plus the two it
#: provably never reads, u04/u4C, both 0 on 14,571/14,571). u32 unless noted.
HDR_U16 = ("n3C", "n3E", "n50", "n52")
HDR_U8 = ("n54", "n55", "n56", "n57", "flags")
HDR_F32 = ("f20", "f28")
HDR_I32 = ("i30",)
HDR = {
    "ver": 0x00, "u04": 0x04, "flags": 0x08, "u0C": 0x0C, "u10": 0x10,
    "n14": 0x14, "n18": 0x18, "u1C": 0x1C, "f20": 0x20, "u24": 0x24,
    "f28": 0x28, "n2C": 0x2C, "i30": 0x30, "n34": 0x34, "n38": 0x38,
    "n3C": 0x3C, "n3E": 0x3E, "n40": 0x40, "n44": 0x44, "n48": 0x48,
    "u4C": 0x4C, "n50": 0x50, "n52": 0x52, "n54": 0x54, "n55": 0x55,
    "n56": 0x56, "n57": 0x57,
}


class Undecodable(ValueError):
    """A gate fired. `gate` names it; `cursor`/`want`/`end` locate it."""

    def __init__(self, gate, cursor, want, end):
        super().__init__(f"{gate} at +0x{cursor:X} (want {want}, end {end})")
        self.gate, self.cursor, self.want, self.end = gate, cursor, want, end


def read_header(p):
    """The 0x58-byte header, or raise at the client's pre-parse gates."""
    n = len(p)
    if n < 4:
        raise Undecodable("G00_size4", 0, 4, n)        # 00794958 cmp eax,4
    ver = struct.unpack_from("<I", p, 0)[0]
    if ver != SKELETON_VERSION:
        raise Undecodable("G01_version", 0, SKELETON_VERSION, ver)  # 0079495D
    if n < 0x58:
        raise Undecodable("G02_header", 0, 0x58, n)    # 0079632C/2F
    h = {}
    for k, off in HDR.items():
        if k in HDR_U16:
            h[k] = struct.unpack_from("<H", p, off)[0]
        elif k in HDR_U8:
            h[k] = p[off]
        elif k in HDR_F32:
            h[k] = struct.unpack_from("<f", p, off)[0]
        elif k in HDR_I32:
            h[k] = struct.unpack_from("<i", p, off)[0]
        else:
            h[k] = struct.unpack_from("<I", p, off)[0]
    return h


def _walk_spans(p, T, h, fired=None):
    """ONE implementation of the layout: advance the cursor exactly as the
    parser at 0x00796310 does, recording each block's (offset, size) span.

    Raises Undecodable at the first gate that fires. Returns (spans, fired):
    `spans` is a list of (name, offset, size) in stream order that tiles
    `p[T['hdr']:cursor]` with no gaps; `fired` is the set of optional terms
    the payload actually exercised (a sabotage variant is scored only over
    files that fired its term -- crediting it with survivals it never faced
    is the recorded mistake). Pass a set as `fired` to keep what accumulated
    up to a death point -- `walk()` does, so a failed walk still reports
    which terms it exercised before dying, matching the research walker.
    """
    n = len(p)
    spans = [("header", 0, T["hdr"])]
    fired = set() if fired is None else fired
    # n14 and n18 are unconditional blocks whose counts are header-known, so
    # they are pre-added the way the verified research walker did it -- a
    # death before their blocks still reports them as exercised.
    if h["n14"]:
        fired.add("n14")
    if h["n18"]:
        fired.add("n18")
    c = T["hdr"]
    u16 = lambda o: struct.unpack_from("<H", p, o)[0]
    u32 = lambda o: struct.unpack_from("<I", p, o)[0]

    def take(nbytes, gate):
        nonlocal c
        if nbytes < 0 or c + nbytes > n:
            raise Undecodable(gate, c, nbytes, n)
        c += nbytes

    def span(name, gate, nbytes):
        at = c
        take(nbytes, gate)
        spans.append((name, at, nbytes))

    def var_array(name, count, elem, cnt_at, mult, gate):
        """helper 0x00794C40: per record take(elem), then take(u32@rec+cnt_at * mult)."""
        at = c
        for _ in range(count):
            rec = c
            take(elem, gate)
            if rec + cnt_at + 4 > n:
                raise Undecodable(gate + "_cnt", rec, cnt_at + 4, n)
            take(u32(rec + cnt_at) * mult, gate)
        spans.append((name, at, c - at))

    # ---- 1. n14 records ------------------------------------------ 00796342
    if h["n14"]:
        fired.add("n14")
    span("n14", "G03_n14", h["n14"] * T["n14_elem"])
    # ---- 2. n34 records ------------------------------------------ 007963EF
    if h["n34"]:
        fired.add("n34")
        span("n34", "G04_n34", h["n34"] * T["n34_elem"])
    # ---- 3. blk2C ------------------------------------------------ 0079645A
    if h["n2C"] == 0:
        # 0079644E je -> return 12: the client's own hard reject, 0/14,571.
        raise Undecodable("G05_n2C_zero", c, 1, n)
    at = c
    take(h["n2C"] * T["b2c_fixed"], "G06_blk2C_fixed")
    for _ in range(h["n2C"]):
        sub = c
        take(T["b2c_sub"], "G07_blk2C_sub")
        # The 6-byte read below is only covered by the take when b2c_sub is
        # its real value -- under a sabotaged smaller b2c_sub the read could
        # run past the end, so the walker guards it separately (as the
        # verified research walker did) rather than letting struct.error
        # escape the Undecodable protocol.
        if sub + 6 > n:
            raise Undecodable("G07_blk2C_sub", sub, 6, n)
        w0, w2, w4 = u16(sub), u16(sub + 2), u16(sub + 4)
        if w0 + w4:
            fired.add("b2c_w04")
        if w2:
            fired.add("b2c_w2")
        take((w0 + w4) * T["b2c_m04"] + w2 * T["b2c_m20"], "G08_blk2C_payload")
    spans.append(("blk2C", at, c - at))
    # ---- 4. n38 var-array ---------------------------------------- 00796470
    if h["n38"]:
        fired.add("n38")
        var_array("n38", h["n38"], T["n38_elem"], T["n38_cnt_at"],
                  T["n38_mult"], "G09_n38")
    # ---- 5. n3C key table, structure-of-arrays ------------------- 007964AA
    if h["n3C"]:
        fired.add("n3C")
    span("keys", "G10_n3C", h["n3C"] * T["n3c_elem"])
    # ---- 6. n18 sequence records --------------------------------- 007964D5
    if h["n18"]:
        fired.add("n18")
    span("seqs", "G11_n18", h["n18"] * T["n18_elem"])
    # ---- 7. n52 var-array ---------------------------------------- 00796601
    if h["n52"]:
        fired.add("n52")
        var_array("n52", h["n52"], T["n52_elem"], T["n52_cnt_at"],
                  T["n52_mult"], "G12_n52")
    # ---- 8. n40 / n44 -------------------------------------------- 0079663C
    if h["n40"] or h["n44"]:
        for k in ("n40", "n44"):
            if h[k]:
                fired.add(k)
        span("n40n44", "G13_n40n44",
             h["n40"] * T["n40_elem"] + h["n44"] * T["n44_elem"])
    # ---- 9. blk48 ------------------------------------------------ 007966A0
    if h["n48"]:
        fired.add("n48")
        at = c
        take(h["n48"] * T["b48_fixed"], "G14_blk48_fixed")
        for _ in range(h["n48"]):
            sub = c
            take(T["b48_sub"], "G15_blk48_sub")
            if sub + 4 > n:          # same guard rationale as blk2C's
                raise Undecodable("G15_blk48_sub", sub, 4, n)
            w0, w2 = u16(sub), u16(sub + 2)
            if w0 + w2:
                fired.add("b48_w")
            take((w0 + w2) * T["b48_m"], "G16_blk48_payload")
        spans.append(("blk48", at, c - at))
    # ---- 10..14. five 8-byte var-arrays ---------------------------------
    for key, gate in (("n50", "G17_n50"), ("n54", "G18_n54"),
                      ("n55", "G19_n55"), ("n56", "G20_n56"),
                      ("n57", "G21_n57")):
        if h[key]:
            fired.add(key)
            var_array(key, h[key], T[key + "_elem"], T[key + "_cnt_at"],
                      T[key + "_mult"], gate)
    # ---- 15. n3E two raw arrays ---------------------------------- 007967FD
    if h["n3E"]:
        fired.add("n3E")
        span("n3E_a", "G22_n3E_a", h["n3E"] * T["n3e_a"])
        span("n3E_b", "G23_n3E_b", h["n3E"] * T["n3e_b"])

    if c != n:
        # OUR closure check. The client does NOT do this (0x00796905).
        raise Undecodable("G24_CLOSE_SHORT", c, n - c, n)
    return spans, fired


def walk(p, T=TERMS):
    """Diagnostic walk: never raises for format reasons.

    Returns {ok, gate, cur, size, fired, hdr}: `ok` means closed on the
    exact final byte; otherwise `gate` names the death point -- the useful
    diagnostic, and what the study histogrammed (the histogram was empty).
    """
    n = len(p)
    try:
        h = read_header(p)
    except Undecodable as d:
        return {"ok": False, "gate": d.gate, "cur": d.cursor, "size": n,
                "fired": set(), "hdr": None}
    fired = set()
    try:
        spans, fired = _walk_spans(p, T, h, fired)
    except Undecodable as d:
        # `fired` keeps what accumulated up to the death point -- the
        # research walker's semantics, and what a scorer that pools by
        # exercised term needs from a failed variant walk.
        return {"ok": False, "gate": d.gate, "cur": d.cursor, "size": n,
                "fired": fired, "hdr": h}
    return {"ok": True, "gate": "G24_CLOSE", "cur": n, "size": n,
            "fired": fired, "hdr": h}


class Skeleton:
    """One decoded 0xFA1 chunk. Typed where a name was earned, bytes elsewhere."""

    __slots__ = ("header", "spans", "fired", "payload")

    def __init__(self, header, spans, fired, payload):
        self.header = header
        self.spans = spans
        self.fired = fired
        self.payload = payload

    @classmethod
    def decode(cls, payload):
        h = read_header(payload)
        spans, fired = _walk_spans(payload, TERMS, h)
        return cls(h, spans, fired, payload)

    @classmethod
    def from_container(cls, data):
        """From a whole ffna file. Returns None if the file has no FA1 chunk."""
        t = ffna_type(data)
        if t != MODEL_FFNA_TYPE:
            raise ValueError(f"ffna type {t}, not the model type "
                             f"{MODEL_FFNA_TYPE} this chunk lives in")
        for cid, off, size in ffna_chunks(data):
            if cid == SKELETON_CHUNK:
                return cls.decode(bytes(data[off:off + size]))
        return None

    @classmethod
    def load(cls, file_id, archive_):
        table = file_id_table(archive_)
        row = table.get(file_id)
        if row is None:
            raise KeyError(f"file id {file_id} not in the archive's id table")
        return cls.from_container(archive_.read(archive_.row(row)))

    # -- the named layer ----------------------------------------------------

    @property
    def seq_count(self):
        """ArenaNet's m_seqCount (MdlSeq:300), header +0x18."""
        return self.header["n18"]

    @property
    def flags(self):
        return self.header["flags"]

    @property
    def composited(self):
        """MODEL_SKELETON_FLAG_COMPOSITED: geometry arrives from elsewhere."""
        return bool(self.header["flags"] & FLAG_COMPOSITED)

    def _span(self, name):
        for nm, off, size in self.spans:
            if nm == name:
                return off, size
        return None

    def sequences(self):
        """The n18 records: lo/hi named (span selectors), the rest raw.

        lo/hi earned their names by the refutable span-binding prediction
        `lo <= hi <= n3C` (50,127/50,127); the six other fields are carried
        under offset names because nothing has earned more.
        """
        off, _ = self._span("seqs")
        p, out = self.payload, []
        for i in range(self.header["n18"]):
            o = off + i * TERMS["n18_elem"]
            out.append({
                "u8_00": p[o],
                "u32_01": struct.unpack_from("<I", p, o + 1)[0],
                "u32_05": struct.unpack_from("<I", p, o + 5)[0],
                "u32_09": struct.unpack_from("<I", p, o + 9)[0],
                "lo": p[o + 0x0D], "hi": p[o + 0x0E],
                "u32_0F": struct.unpack_from("<I", p, o + 0x0F)[0],
                "f32_13": struct.unpack_from("<f", p, o + 0x13)[0],
            })
        return out

    def key_times_raw(self):
        """n3C int32 key times, units of 1e-5 s. SoA: times first, tags after."""
        off, _ = self._span("keys")
        n = self.header["n3C"]
        return list(struct.unpack_from(f"<{n}i", self.payload, off)) if n else []

    def key_tags(self):
        off, _ = self._span("keys")
        n = self.header["n3C"]
        return list(self.payload[off + 4 * n: off + 5 * n])

    def key_times_s(self):
        return [t * KEYTIME_SCALE for t in self.key_times_raw()]

    def block_bytes(self, name):
        """An opaque block's raw bytes (e.g. 'blk2C', 'blk48'), or None."""
        s = self._span(name)
        if s is None:
            return None
        off, size = s
        return self.payload[off:off + size]

    def flags_presence(self):
        """The four testable (bit, block-nonzero) pairs of the +0x08 bitmap.

        MEASURED 14,571/14,571 each; bit 4 <=> n18 is vacuous in the corpus
        (both sides always true) and is deliberately absent. Bit 0 needs the
        CONTAINER's chunk table (no-FA0), so it is checked by callers who
        have one, not here.
        """
        h = self.header
        return [(3, bool(h["flags"] & 8), bool(h["n34"])),
                (5, bool(h["flags"] & 0x20), bool(h["n48"])),
                (6, bool(h["flags"] & 0x40), bool(h["n50"])),
                (7, bool(h["flags"] & 0x80), bool(h["n38"]))]


def container_has_geometry(data):
    """Does an ffna type-2 file carry a 0xFA0 chunk? (The COMPOSITED bit's
    corpus-side equivalent: bit set <=> this is False, 14,571/14,571.)"""
    return any(cid == GEOMETRY_CHUNK for cid, _, _ in ffna_chunks(data))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=None, help="archive path; default: "
                    "the study archive via vaultpath")
    ap.add_argument("--file-id", type=int, help="decode one file id's FA1")
    ap.add_argument("--row", type=int, help="decode one MFT row's FA1")
    args = ap.parse_args(argv)

    if args.dat is None:
        import vaultpath
        args.dat = os.path.join(
            vaultpath.require_dir("dat_study", why="skelfile CLI"), "Gw.dat")
    ar = Archive(args.dat)
    if args.file_id is None and args.row is None:
        ap.error("--file-id or --row")
    if args.file_id is not None:
        data = ar.read(ar.row(file_id_table(ar)[args.file_id]))
    else:
        data = ar.read(ar.row(args.row))
    sk = Skeleton.from_container(data)
    if sk is None:
        print("no 0xFA1 chunk in this file")
        return 1
    h = sk.header
    print(f"FA1: {len(sk.payload)} bytes, flags 0x{h['flags']:02X}"
          f" (COMPOSITED={sk.composited}), seqs {sk.seq_count},"
          f" keys {h['n3C']}, n2C {h['n2C']}, n48 {h['n48']}")
    print(f"container has geometry: {container_has_geometry(data)}")
    for name, off, size in sk.spans:
        print(f"  {name:8s} +0x{off:06X}  {size:8d} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
