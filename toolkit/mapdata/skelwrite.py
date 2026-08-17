r"""Write the skeleton/animation chunk back: the U6 re-serializer.

Rung U6 of `studies/unitmodels/PLAN.md`: an FA1 writer whose UNMODIFIED
re-serialization is byte-identical to the source, a container writer that
re-emits the whole ffna type-2 file the same way, and the modification seam
U7 will fire (but this module never deploys anything -- no run directory, no
client, no live archive; writes are refused outside the vault from birth).

    sk = Skeleton.decode(payload)
    t = extract(sk)                     # the TYPED representation
    encode(t) == payload                # the rung's criterion, byte for byte

WHY THE WRITER REBUILDS FROM TYPED VALUES AND NEVER FROM `.spans`. A writer
that concatenates the reader's `.spans` verbatim passes identity vacuously --
that is the memcpy-loader defect class (`studies/models/FINDINGS.md` §4.5: a
loader that stashes the source block passes every oracle while decoding
nothing). Identity is only INFORMATIVE if the bytes are re-derived from the
decoded values, because then it proves the typed layer is COMPLETE -- nothing
the decoder names is lossy. So `extract()` deliberately returns a structure
with NO reference to the source payload: typed regions exist only as numbers
(header fields, sequence records, key times/tags, blk2C/blk48 records and
their channel arrays, the n40 sound events' named fields, n3E event track),
and bytes survive only where the typed layer is genuinely opaque:

  * the n14/n34 fixed-stride records and the n38/n52/n50/n54/n55/n56/n57
    var-arrays (elements NOT DECODED -- `skelfile.py`'s posture, kept);
  * the n44 tail of the n40n44 region (n44's 12-byte records are not
    decoded);
  * the 10-byte `raw_tail` of EACH n40 sound-event body -- a body is 8
    typed bytes ({i32 time; u32 path_index}) plus 10 the typed layer has
    not named, so on an n40-heavy file the raw tails dominate the carry
    (the shell: 620 of its 1,179 carried bytes are 62 raw tails);
  * header bytes +0x09..+0x0B -- the parser provably never reads them
    (`studies/unitmodels/FINDINGS.md` §3.3) and U6's first measurement is
    that they are NOT zero (0x42 on the hatcher shell, 0x07 on the worm),
    so a writer that zero-filled them would fail identity on nearly every
    file. They are carried as the 3-byte `pad09` field, opaque and honest.

FLOAT ROUND-TRIPPING. Header f20/f28, sequence f32_13, record base vectors
and every channel value pass through Python floats. f32 -> f64 -> f32 is
bit-exact for every finite value, and the corpus's channel values are all
finite (`studies/anim/FINDINGS.md` P5: 0 non-finite in 16.2M); a non-finite
anywhere else would be CAUGHT by the identity run, which is the point of
running it at full population rather than asserting the law from a sample.

WHY IDENTITY AND NOT RE-PARSE EQUIVALENCE (the rung's stated rationale,
exhibited by `test_skelwrite.py`'s order control): two of the layout's zones
are UNVERIFIED -- n56's stride fires on 0 of 14,571 corpus files, and the
order of adjacent FIXED-size blocks is pinned by nothing the walk can refute
(closure tests the sum). A writer that emitted n34 before n14 would produce
output that re-parses green -- header intact, every gate passes, closure
exact -- and is byte-different from every real file. Only identity catches
it, so identity is the criterion.

THE U7 SEAM -- BUILT, NOT FIRED. `scale_sequence_keytimes()` retimes one
sequence by scaling its span of the key table: pure int32 arithmetic on
MEASUREMENT-side values, refusing inexact division and overflow. It returns
the key indices whose value changed so a caller can PREDICT the byte diff
before serializing -- `test_skelwrite.py` asserts the modified output
differs from the source at exactly those bytes and nowhere else. Nothing
here writes to a run directory, launches a client, or touches an archive
outside the vault: the loopback deployment is U7, owner-driven.

Provenance: this module emits bytes DERIVED from the owner's archive at run
time; every disk write below routes through `resolve_outdir`, which refuses
the working tree with no override (delegated to `mapexport.resolve_outdir`,
the same single copy of the rule `modelexport.py` and `unitexport.py` use).
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, FFNA_MAGIC, ffna_chunks, ffna_type,  # noqa: E402
                     file_id_table)
from skelfile import (Skeleton, HDR, HDR_U16, HDR_U8, HDR_F32,  # noqa: E402
                      HDR_I32, TERMS, SKELETON_CHUNK, MODEL_FFNA_TYPE)
import mapexport  # noqa: E402

#: The blocks whose ELEMENTS stay undecoded (skelfile's posture) and are
#: therefore carried as bytes. Everything else is re-derived from typed
#: values. n40n44 is split: n40's part is typed, n44's tail is opaque.
OPAQUE_BLOCKS = ("n14", "n34", "n38", "n52", "n50", "n54", "n55", "n56", "n57")

#: Var-array shape per opaque block: (elem, cnt_at, mult), read from
#: skelfile.TERMS so a term correction there is automatically the writer's
#: too. `None` means fixed-stride (length must equal count * elem).
_VAR = {k: (TERMS[k + "_elem"], TERMS[k + "_cnt_at"], TERMS[k + "_mult"])
        for k in ("n38", "n52", "n50", "n54", "n55", "n56", "n57")}
_FIXED = {"n14": TERMS["n14_elem"], "n34": TERMS["n34_elem"]}


class Unwritable(ValueError):
    """A typed representation this writer refuses to serialize, by name."""


def _need(cond, what):
    if not cond:
        raise Unwritable(what)


def extract(sk):
    """Skeleton -> the typed representation `encode` serializes.

    Every typed region leaves as VALUES (through skelfile's own accessors --
    one decoder, never a private re-parse); every opaque region leaves as
    bytes. The result holds no reference to `sk` or its payload.
    """
    h = dict(sk.header)
    t = {
        "header": h,
        "pad09": bytes(sk.payload[0x09:0x0C]),
        "sequences": sk.sequences(),
        "key_times": list(sk.key_times_raw()),
        "key_tags": list(sk.key_tags()),
        "anims": sk.anims(),
        "tracks": sk.tracks(),
        "event_track": sk.event_track(),
        "opaque": {},
    }
    for name in OPAQUE_BLOCKS:
        b = sk.block_bytes(name)
        t["opaque"][name] = bytes(b) if b is not None else b""
    # sound_events() returns [] itself on the n40 == n44 == 0 majority
    # since the U6 review's scoped skelfile fix; only the n44 tail's slice
    # still needs the span guard (no span, no tail).
    t["sound_events"] = sk.sound_events()
    blob = sk.block_bytes("n40n44")
    t["opaque"]["n44_tail"] = bytes(blob[h["n40"] * TERMS["n40_elem"]:]) \
        if blob is not None else b""
    return t


def _channel_bytes(ch, vfmt, what):
    """One times-prefix SoA channel back to bytes: N int32 times, N values."""
    times, vals = ch
    _need(len(times) == len(vals),
          f"{what}: {len(times)} times vs {len(vals)} values")
    out = bytearray(struct.pack(f"<{len(times)}i", *times))
    for v in vals:
        out += struct.pack(vfmt, *v)
    # No length re-check here: the output's size is entailed by the two
    # packs above, so asserting it was a check that cannot fail (review).
    return bytes(out)


def _check_var_block(name, count, data):
    """An opaque var-array block must TILE under its own terms -- the same
    record walk the reader does, so a truncated or padded representation is
    refused by name instead of serializing an unclosable payload."""
    elem, cnt_at, mult = _VAR[name]
    c, n = 0, len(data)
    for _ in range(count):
        _need(c + max(elem, cnt_at + 4) <= n, f"opaque {name}: truncated record")
        c += elem + struct.unpack_from("<I", data, c + cnt_at)[0] * mult
    _need(c == n, f"opaque {name}: {n} bytes, records tile {c}")


def encode(t):
    """The typed representation back to FA1 chunk bytes.

    Emission order is the parser's stream order (`skelfile._walk_spans`).
    Counts are taken from the HEADER and checked against every list they
    must agree with -- a modification that changed a length without
    updating the header is refused by name, never serialized wrong.
    """
    h = t["header"]

    # -- header: every named field packed at its HDR offset; the one unnamed
    #    3-byte region comes from pad09. Nothing else exists in 0x58 bytes.
    _need(len(t["pad09"]) == 3, f"pad09 must be 3 bytes, got {len(t['pad09'])}")
    hdr = bytearray(0x58)
    for k, off in HDR.items():
        if k in HDR_U16:
            struct.pack_into("<H", hdr, off, h[k])
        elif k in HDR_U8:
            hdr[off] = h[k]
        elif k in HDR_F32:
            struct.pack_into("<f", hdr, off, h[k])
        elif k in HDR_I32:
            struct.pack_into("<i", hdr, off, h[k])
        else:
            struct.pack_into("<I", hdr, off, h[k])
    hdr[0x09:0x0C] = t["pad09"]
    out = bytearray(hdr)

    # -- 1./2. n14, n34: fixed-stride opaque records
    for name in ("n14", "n34"):
        data = t["opaque"][name]
        _need(len(data) == h[name] * _FIXED[name],
              f"opaque {name}: {len(data)} bytes for count {h[name]}")
        out += data

    # -- 3. blk2C from the typed records
    anims = t["anims"]
    _need(len(anims) == h["n2C"], f"n2C {h['n2C']} vs {len(anims)} anim records")
    _need(h["n2C"] > 0, "n2C == 0 is the client's own hard reject (error 12)")
    var = bytearray()
    for i, a in enumerate(anims):
        out += struct.pack("<3fI", *a["base"], a["flags"])
        w0 = len(a["trans"][0]) if a["trans"] else 0
        w2 = len(a["rot"][0]) if a["rot"] else 0
        w4 = len(a["aux"][0]) if a["aux"] else 0
        var += struct.pack("<3H", w0, w2, w4)
        if w0:
            var += _channel_bytes(a["trans"], "<3f", f"anim {i} trans")
        if w2:
            var += _channel_bytes(a["rot"], "<4f", f"anim {i} rot")
        if w4:
            var += _channel_bytes(a["aux"], "<3f", f"anim {i} aux")
    out += var

    # -- 4. n38 var-array (opaque, tiling-checked)
    _check_var_block("n38", h["n38"], t["opaque"]["n38"])
    out += t["opaque"]["n38"]

    # -- 5. the key table, structure-of-arrays: n3C int32 times, n3C tags
    times, tags = t["key_times"], t["key_tags"]
    _need(len(times) == h["n3C"] and len(tags) == h["n3C"],
          f"n3C {h['n3C']} vs {len(times)} times / {len(tags)} tags")
    if times:
        out += struct.pack(f"<{len(times)}i", *times)
        out += bytes(tags)

    # -- 6. the n18 sequence records: 0x17 bytes, every field typed
    seqs = t["sequences"]
    _need(len(seqs) == h["n18"], f"n18 {h['n18']} vs {len(seqs)} sequences")
    for i, s in enumerate(seqs):
        _need(s["start"] == s["u32_05"] and s["end"] == s["u32_09"],
              f"sequence {i}: start/end aliases diverged from u32_05/u32_09")
        rec = bytearray(TERMS["n18_elem"])
        rec[0x00] = s["u8_00"]
        struct.pack_into("<I", rec, 0x01, s["u32_01"])
        struct.pack_into("<I", rec, 0x05, s["u32_05"])
        struct.pack_into("<I", rec, 0x09, s["u32_09"])
        rec[0x0D], rec[0x0E] = s["lo"], s["hi"]
        struct.pack_into("<I", rec, 0x0F, s["u32_0F"])
        struct.pack_into("<f", rec, 0x13, s["f32_13"])
        out += rec

    # -- 7. n52 var-array (opaque)
    _check_var_block("n52", h["n52"], t["opaque"]["n52"])
    out += t["opaque"]["n52"]

    # -- 8. n40/n44: n40 typed (seq-index array then 18-byte bodies), n44 raw
    ev = t["sound_events"]
    _need(len(ev) == h["n40"], f"n40 {h['n40']} vs {len(ev)} sound events")
    for e in ev:
        out += struct.pack("<I", e["seq"])
    for i, e in enumerate(ev):
        _need(len(e["raw_tail"]) == 10, f"sound event {i}: raw_tail size")
        out += struct.pack("<iI", e["time"], e["path_index"]) + e["raw_tail"]
    tail = t["opaque"]["n44_tail"]
    _need(len(tail) == h["n44"] * TERMS["n44_elem"],
          f"n44 tail: {len(tail)} bytes for count {h['n44']}")
    out += tail

    # -- 9. blk48 from the typed records
    tracks = t["tracks"]
    _need(len(tracks) == h["n48"], f"n48 {h['n48']} vs {len(tracks)} tracks")
    var = bytearray()
    for i, r in enumerate(tracks):
        out += struct.pack("<3fII", *r["base"], r["flags"], r["u10"])
        w0 = len(r["ch0"][0]) if r["ch0"] else 0
        w2 = len(r["ch1"][0]) if r["ch1"] else 0
        var += struct.pack("<2H", w0, w2)
        if w0:
            var += _channel_bytes(r["ch0"], "<3f", f"track {i} ch0")
        if w2:
            var += _channel_bytes(r["ch1"], "<3f", f"track {i} ch1")
    out += var

    # -- 10..14. the five 8-byte var-arrays (opaque)
    for name in ("n50", "n54", "n55", "n56", "n57"):
        _check_var_block(name, h[name], t["opaque"][name])
        out += t["opaque"][name]

    # -- 15. n3E: times array, then {type, param} records
    etimes, erecs = t["event_track"]
    _need(len(etimes) == h["n3E"] and len(erecs) == h["n3E"],
          f"n3E {h['n3E']} vs {len(etimes)} times / {len(erecs)} records")
    if etimes:
        out += struct.pack(f"<{len(etimes)}i", *etimes)
        for r in erecs:
            out += struct.pack("<II", *r)

    return bytes(out)


def roundtrip_fa1(payload):
    """decode -> extract -> encode. Byte-identical to `payload` iff the typed
    layer is complete -- U6's criterion, and the caller compares."""
    return encode(extract(Skeleton.decode(payload)))


def rebuild_container(data, fa1=None):
    """Re-emit a whole ffna type-2 file: magic and type from parsed values,
    every chunk header re-packed from its parsed (id, size), the FA1 payload
    re-serialized through the typed layer, every other chunk's payload
    carried verbatim (their decoders are other modules' rungs).

    `fa1=None` round-trips the FA1 unmodified; passing bytes substitutes
    them (the U7 seam at container level -- the chunk's size field follows).
    A file with no FA1 chunk re-emits whole (`fa1` given raises, so a caller
    cannot believe it modified a file it did not).
    """
    ftype = ffna_type(data)
    if ftype != MODEL_FFNA_TYPE:
        raise Unwritable(f"ffna type {ftype}, not the model type "
                         f"{MODEL_FFNA_TYPE} the FA1 chunk lives in")
    out = bytearray(FFNA_MAGIC)
    out.append(ftype)
    saw_fa1 = False
    for cid, off, size in ffna_chunks(data):
        payload = bytes(data[off:off + size])
        if cid == SKELETON_CHUNK and not saw_fa1:
            saw_fa1 = True
            payload = roundtrip_fa1(payload) if fa1 is None else bytes(fa1)
        out += struct.pack("<II", cid, len(payload))
        out += payload
    if fa1 is not None and not saw_fa1:
        raise Unwritable("fa1 bytes were given but this container carries no "
                         "0xFA1 chunk -- refusing to pretend it was modified")
    return bytes(out)


# ---------------------------------------------------------------------------
# The U7 seam: a deliberate, minimal modification. Built here, fired by U7.
# ---------------------------------------------------------------------------

def scale_sequence_keytimes(t, seq_index, num, den=1):
    """Scale sequence `seq_index`'s span of the key table by num/den, in
    place on the typed representation. Pure int32 arithmetic -- inexact
    division and overflow are REFUSED, never rounded, because a retime that
    lands off the 1e-5 grid silently is a different experiment.

    Returns the sorted key-table indices whose VALUE changed, so the caller
    can predict the byte diff of the re-serialization before making it:
    exactly bytes [keys_off + 4*k, keys_off + 4*k + 4) per returned k, and
    nothing else. (Spans of different sequences may overlap -- the worm has
    10 sequences over 3 keys -- so a scaled key can be another sequence's
    too; the return names table slots, not ownership.)

    ATOMIC: the whole span is computed and validated BEFORE the
    representation changes, so a refusal leaves `t` exactly as it was and
    it still encodes to the source bytes. The first version wrote each key
    as it went, and the U6 review found the reachable half-retime: the
    shell's sequence 16 spans two keys [66666, 116666], and scaling by 1/3
    refused on the second with the first already rewritten -- a repr that
    still serialized, carrying half an experiment. This function is what
    U7 fires, so partial states are refused BY CONSTRUCTION, not by care.
    """
    if not (isinstance(num, int) and isinstance(den, int) and den > 0):
        raise Unwritable("num/den must be ints, den > 0 -- key times are "
                         "int32 measurements, not floats")
    seqs = t["sequences"]
    if not 0 <= seq_index < len(seqs):
        raise Unwritable(f"sequence {seq_index} of {len(seqs)}")
    lo, hi = seqs[seq_index]["lo"], seqs[seq_index]["hi"]
    staged, changed = [], []
    for k in range(lo, hi):
        v = t["key_times"][k]
        nv = v * num
        if nv % den:
            raise Unwritable(f"key {k}: {v} * {num}/{den} is not an integer "
                             f"-- refusing to round a measurement")
        nv //= den
        if not -0x80000000 <= nv <= 0x7FFFFFFF:
            raise Unwritable(f"key {k}: scaled time {nv} overflows int32")
        staged.append(nv)
        if nv != v:
            changed.append(k)
    t["key_times"][lo:hi] = staged      # every key validated; commit once
    return changed


# ---------------------------------------------------------------------------
# Disk. Refused outside the vault FROM BIRTH.
# ---------------------------------------------------------------------------

def resolve_outdir(outdir=None):
    """Where a write may land. Delegates to `mapexport.resolve_outdir` --
    one copy of the provenance rule, exactly as `modelexport.py` and
    `unitexport.py` do -- so the refusal (working tree, no override) and the
    default (`vault/exports`) cannot drift from the rest of the toolkit."""
    return mapexport.resolve_outdir(outdir)


def write_bytes(data, name, outdir=None):
    """Write `data` under the resolved (vault-only) directory. Returns path."""
    outdir = resolve_outdir(outdir)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=None, help="archive; default: the study "
                    "archive via vaultpath")
    ap.add_argument("--file-id", type=int, required=True)
    ap.add_argument("--out", default=None, help="destination directory "
                    "(must resolve under the vault; default vault/exports)")
    ap.add_argument("--write", action="store_true",
                    help="write the rebuilt container; default only verifies")
    args = ap.parse_args(argv)

    if args.dat is None:
        import vaultpath
        args.dat = os.path.join(
            vaultpath.require_dir("dat_study", why="skelwrite CLI"), "Gw.dat")
    with Archive(args.dat) as ar:
        data = ar.read(ar.row(file_id_table(ar)[args.file_id]))
    rebuilt = rebuild_container(data)
    same = rebuilt == bytes(data)
    print(f"file {args.file_id}: container {len(data)} B, rebuilt "
          f"{len(rebuilt)} B, byte-identical: {same}")
    if args.write:
        path = write_bytes(rebuilt, f"unit_{args.file_id}.rebuilt.ffna",
                           args.out)
        print(f"wrote {path}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
