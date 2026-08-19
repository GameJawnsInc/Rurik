r"""Write the 0xFA0 geometry chunk back: the mesh half of the round trip.

`skelwrite.py` (rung U6) made the FA1 skeleton writable and the archive-write
arc made a compressed row writable in place. This is the last unwritten layer
of a unit: after it, every part of a creature the client loads -- skeleton,
motion channels, link list, textures, archive row, and now the MESH -- can be
decoded to typed values, modified, and written back.

    g = ModelGeometry.decode(payload)
    t = extract(payload)                # the TYPED representation
    encode(t) == payload                # the criterion, byte for byte

WHY THIS COULD NOT HONESTLY BE WRITTEN UNTIL 2026-08-19. A vertex is an
interleaved record of fields named by `dat_fvf`, and until this morning `bit 1`
was "a small INDEX, purpose UNVERIFIED" -- so a writer had to carry four bytes
per vertex as opaque, which on a 1,148-vertex sub-model is most of what makes a
vertex a vertex. Bit 1 is now `GR_FVF_GROUP` (`modelfile.py`, `MdlCombine:2073`
and `GrGeo:738`), and with it EVERY byte of a retail vertex belongs to a named
field: MEASURED `stride - sum(named field sizes) == 0` on **1,618 of 1,618**
sub-models across all **14** distinct `dat_fvf` values in the archive. There is
no padding to carry and no unclaimed byte, so the vertex block is re-derived
field by field rather than copied.

THAT DISTINCTION IS THE WHOLE POINT, and it is `skelwrite.py`'s lesson repeated
rather than rediscovered. A writer that stashes the source block and hands it
back passes byte-identity vacuously -- the memcpy-loader defect
(`studies/models/FINDINGS.md` §4.5: a loader that keeps the source bytes passes
every oracle while decoding nothing). Identity is only INFORMATIVE when the
bytes are re-derived from decoded values, because then it proves the typed layer
is COMPLETE. So `extract()` returns a structure holding NO reference to the
source payload except through two regions named as opaque:

  * `head` -- the preamble: a 0x54 header plus six gated variable-length blocks
    that `modelfile.preamble_end()` walks but does not decode. Carried, and the
    two count fields inside it (`num_models` at 0x44, collisions at 0x4C) are
    RE-DERIVED from the typed lists on the way out, so a modification that added
    a sub-model without updating the header is refused rather than serialized
    wrong.
  * `tail` -- blocks H, I and J after the collision meshes
    (`modelfile.trailing_end()`; H fires on 0 of 20,661 chunks, I on 9,571).
    Their records are other rungs' work.

Everything else leaves as VALUES: the sub-model header fields, the triangle
indices, every named vertex field, the skin binding
(`groupTransformCount[]` + `transforms[]`), and the collision meshes' indices
and positions. The `u2` records are 12 bytes each of which only word 0 is
understood (a vertex index), so they are carried as bytes and NAMED as carried.

FLOAT ROUND-TRIPPING, and the same argument `skelwrite.py` makes: f32 -> f64 ->
f32 is bit-exact for every finite value, and a non-finite anywhere would be
CAUGHT by the identity run rather than assumed away -- which is why the census
runs at full population instead of asserting the law from a sample.

WHAT THIS MODULE DOES NOT DO. It does not build a mesh from nothing, it does not
re-index or weld vertices, and it does not touch the preamble's six blocks. It
is the round trip plus a seam; authoring on top of it is the next rung's work.

Provenance: this module emits bytes DERIVED from the owner's archive at run
time. The layout is `modelfile.py`'s, whose `PLAN.md` §6.1 register rows cover
it; nothing new is taken from any upstream here.
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
import modelfile  # noqa: E402
from modelfile import (COLLISION_COUNT_AT, COLLISION_HEADER,  # noqa: E402
                       FIELD_ORDER, FIELD_SIZE, GEOMETRY_CHUNK,
                       MODEL_FFNA_TYPE, NUM_MODELS_AT, POSITION,
                       SUBMODEL_HEADER, ModelGeometry, Undecodable,
                       field_offsets, preamble_end, trailing_end,
                       vertex_stride)
import mapexport  # noqa: E402

#: How many floats each named vertex field holds, keyed by `dat_fvf` bit.
#: Derived from `modelfile.FIELD_SIZE` rather than restated, so a correction
#: there is automatically this writer's too. Bit 1 is the ONE integer field.
FIELD_FLOATS = {b: FIELD_SIZE[b] // 4 for b in FIELD_ORDER}
INTEGER_FIELDS = (modelfile.FIELD_GROUP, modelfile.FIELD_DIFFUSE)


class Unwritable(ValueError):
    """A typed representation this writer refuses to serialize, by name."""


def _need(cond, what):
    if not cond:
        raise Unwritable(what)


# ---------------------------------------------------------------------------
# decode -> typed
# ---------------------------------------------------------------------------

def extract(payload):
    """0xFA0 chunk bytes -> the typed representation `encode` serializes.

    Every region this project has decoded leaves as numbers; the preamble and
    the H/I/J tail leave as bytes and are named as such. The result holds no
    other reference to `payload`.
    """
    payload = bytes(payload)
    geom = ModelGeometry.decode(payload)          # its gates, its closure
    start = preamble_end(payload)

    subs = []
    for sm in geom.submodels:
        u0, u1, u2 = sm.u_counts
        fields = field_offsets(sm.dat_fvf)
        named = sum(FIELD_SIZE[b] for b in FIELD_ORDER if sm.dat_fvf >> b & 1)
        _need(named == sm.stride,
              f"format 0x{sm.dat_fvf:X}: named fields total {named} bytes of a "
              f"{sm.stride}-byte stride, so {sm.stride - named} byte(s) belong "
              f"to no field this writer can re-derive")
        verts = {}
        for bit, off in fields.items():
            if bit in INTEGER_FIELDS:
                verts[bit] = [struct.unpack_from("<I", sm.vertex_data,
                                                 v * sm.stride + off)[0]
                              for v in range(sm.nv)]
            else:
                n = FIELD_FLOATS[bit]
                verts[bit] = [struct.unpack_from(f"<{n}f", sm.vertex_data,
                                                 v * sm.stride + off)
                              for v in range(sm.nv)]
        words = struct.unpack_from(f"<{u0 + u1}I", sm.trailing, 0) \
            if u0 + u1 else ()
        subs.append({
            "unk": sm.unk,
            "counts": tuple(sm.counts),
            "dat_fvf": sm.dat_fvf,
            "nv": sm.nv,
            "indices": tuple(sm.indices),
            "verts": verts,
            "group_counts": tuple(words[:u0]),
            "transforms": tuple(words[u0:u0 + u1]),
            # 12 bytes each; only word 0 (a vertex index) is understood, so
            # these are CARRIED and said to be carried rather than invented.
            "u2_records": bytes(sm.trailing[(u0 + u1) * 4:]),
        })

    colls = [{"indices": tuple(c.indices), "positions": [tuple(p) for p in c.positions]}
             for c in geom.collisions]

    # where the collision meshes end is where the H/I/J tail begins
    end = start
    for s in subs:
        end += _submodel_size(s)
    for c in colls:
        end += COLLISION_HEADER.size + len(c["indices"]) * 2 \
            + len(c["positions"]) * 12
    _need(trailing_end(payload, end) == len(payload),
          "the re-walked layout does not reach the end of the chunk")

    return {"head": bytes(payload[:start]), "submodels": subs,
            "collisions": colls, "tail": bytes(payload[end:])}


def _groups_of(s):
    """The per-group transform id tuples of one typed sub-model."""
    out, c = [], 0
    for n in s["group_counts"]:
        out.append(tuple(s["transforms"][c:c + n]))
        c += n
    return out


def _submodel_size(s):
    ti = len(s["indices"])
    nv = s["nv"]
    stride = vertex_stride(s["dat_fvf"])
    return (SUBMODEL_HEADER.size + ti * 2 + nv * stride
            + (len(s["group_counts"]) + len(s["transforms"])) * 4
            + len(s["u2_records"]))


# ---------------------------------------------------------------------------
# typed -> bytes
# ---------------------------------------------------------------------------

def encode(t):
    """The typed representation back to 0xFA0 chunk bytes.

    The two counts inside the carried preamble are RE-DERIVED from the typed
    lists, so they are the one part of `head` that is not merely carried: a
    caller who appended a sub-model gets a correct header or a refusal, never a
    header that disagrees with its own payload.
    """
    head = bytearray(t["head"])
    _need(len(head) >= modelfile.PREAMBLE_MIN,
          f"preamble is {len(head)} bytes, under {modelfile.PREAMBLE_MIN}")
    struct.pack_into("<I", head, NUM_MODELS_AT, len(t["submodels"]))
    struct.pack_into("<H", head, COLLISION_COUNT_AT, len(t["collisions"]))
    out = bytearray(head)

    for i, s in enumerate(t["submodels"]):
        stride = vertex_stride(s["dat_fvf"])
        fields = field_offsets(s["dat_fvf"])
        nv, ti = s["nv"], len(s["indices"])
        n0, n1, n2 = s["counts"]
        want = n0 + (n0 != n1) * n1 + (n1 != n2) * n2
        _need(want == ti,
              f"sub-model {i}: the counts {s['counts']} imply {want} indices, "
              f"not the {ti} present")
        _need(sum(s["group_counts"]) == len(s["transforms"]),
              f"sub-model {i}: group transform counts total "
              f"{sum(s['group_counts'])}, not the {len(s['transforms'])} "
              f"transforms present (MdlCombine:860)")
        # THE CLIENT'S OWN GROUP INVARIANTS, and note which one is NOT here.
        # `MAX_TRANSFORM_IDS` is 4 and a group is a duplicate-free set: both
        # hold on 14,660 of 14,660 retail groups (sizes 1:7,038 2:6,015
        # 3:1,466 4:141, zero duplicates), so both are refusals. The client
        # also treats a group as SORTED -- it interns them by hash, so on-disk
        # order is irrelevant at runtime -- and that is deliberately NOT
        # enforced: retail ships 1,064 of 14,660 groups (7.3%) in non-ascending
        # order, so a writer that required sorting would refuse ArenaNet's own
        # data. Measured before it was written, which is the only reason this
        # comment is not a bug.
        for gi, ids in enumerate(_groups_of(s)):
            _need(1 <= len(ids) <= 4,
                  f"sub-model {i} group {gi} binds {len(ids)} transforms; the "
                  f"client's own bound is 1..4 (MAX_TRANSFORM_IDS)")
            _need(len(set(ids)) == len(ids),
                  f"sub-model {i} group {gi} repeats a transform id: {ids}")
        _need(len(s["u2_records"]) % 12 == 0,
              f"sub-model {i}: the u2 block is {len(s['u2_records'])} bytes, "
              f"not a whole number of 12-byte records")
        out += SUBMODEL_HEADER.pack(
            s["unk"], n0, n1, n2, nv, s["dat_fvf"],
            len(s["group_counts"]), len(s["transforms"]),
            len(s["u2_records"]) // 12)
        out += struct.pack(f"<{ti}H", *s["indices"]) if ti else b""

        # THE VERTEX BLOCK IS RE-DERIVED, field by field, never copied.
        block = bytearray(nv * stride)
        for bit, off in fields.items():
            vals = s["verts"].get(bit)
            _need(vals is not None and len(vals) == nv,
                  f"sub-model {i}: format 0x{s['dat_fvf']:X} declares field "
                  f"{bit} and the typed layer has "
                  f"{'none' if vals is None else len(vals)} of {nv} values")
            if bit in INTEGER_FIELDS:
                for v, x in enumerate(vals):
                    struct.pack_into("<I", block, v * stride + off, x)
            else:
                fmt = f"<{FIELD_FLOATS[bit]}f"
                for v, x in enumerate(vals):
                    struct.pack_into(fmt, block, v * stride + off, *x)
        out += block

        if s["group_counts"] or s["transforms"]:
            out += struct.pack(f"<{len(s['group_counts'])}I", *s["group_counts"])
            out += struct.pack(f"<{len(s['transforms'])}I", *s["transforms"])
        out += s["u2_records"]

    for c in t["collisions"]:
        ni, nv = len(c["indices"]), len(c["positions"])
        out += COLLISION_HEADER.pack(ni, nv)
        out += struct.pack(f"<{ni}H", *c["indices"]) if ni else b""
        for p in c["positions"]:
            out += POSITION.pack(*p)

    out += t["tail"]
    return bytes(out)


def roundtrip(payload):
    """`encode(extract(payload))` -- the criterion, as one call."""
    return encode(extract(payload))


def rebuild_container(data, geometry=None):
    """Re-emit a whole ffna type-2 file with its 0xFA0 chunk re-serialized.

    The mesh sibling of `skelwrite.rebuild_container`, and deliberately the
    same shape: every chunk header re-packed from its parsed (id, size), the
    geometry payload through the typed layer, every other chunk carried
    verbatim. `geometry=None` round-trips it unmodified; passing bytes
    substitutes them. A container with no 0xFA0 re-emits whole, and passing
    bytes for one raises -- a caller must not believe it modified a file it
    did not.
    """
    ftype = ffna_type(data)
    if ftype != MODEL_FFNA_TYPE:
        raise Unwritable(f"ffna type {ftype}, not the model type "
                         f"{MODEL_FFNA_TYPE} the 0xFA0 chunk lives in")
    out = bytearray(FFNA_MAGIC)
    out.append(ftype)
    saw = False
    for cid, off, size in ffna_chunks(data):
        payload = bytes(data[off:off + size])
        if cid == GEOMETRY_CHUNK and not saw:
            saw = True
            payload = roundtrip(payload) if geometry is None else bytes(geometry)
        out += struct.pack("<II", cid, len(payload))
        out += payload
    if geometry is not None and not saw:
        raise Unwritable("geometry bytes were given but this container carries "
                         "no 0xFA0 chunk -- refusing to pretend it was modified")
    return bytes(out)


# ---------------------------------------------------------------------------
# the seam
# ---------------------------------------------------------------------------

def scale_positions(t, factor, submodel=None):
    """Scale vertex POSITIONS by `factor`. Returns how many vertices moved.

    The minimal modification this layer affords, and the mesh counterpart of
    `skelwrite.scale_sequence_keytimes`: length-preserving, touching one named
    field and nothing else, so a caller can predict the byte diff before
    serializing. `submodel=None` scales every one.

    NOTE WHAT IT DOES NOT DO. It does not touch the collision meshes, so a
    scaled render mesh keeps retail's collision hull -- which is a FEATURE for
    a visual probe (the change is provably in the render path) and a BUG for
    anything that expects to walk into it.
    """
    _need(factor != 0, "a zero scale collapses every vertex to the origin")
    n = 0
    for i, s in enumerate(t["submodels"]):
        if submodel is not None and i != submodel:
            continue
        pos = s["verts"].get(modelfile.FIELD_POSITION)
        _need(pos is not None, f"sub-model {i} declares no position field")
        s["verts"][modelfile.FIELD_POSITION] = [
            tuple(c * factor for c in p) for p in pos]
        n += len(pos)
    return n


# ---------------------------------------------------------------------------
# CLI: a round-trip census, and nothing that writes into the tree
# ---------------------------------------------------------------------------

def resolve_outdir(outdir=None):
    """Delegated to `mapexport`, the single copy of the rule: never the
    working tree without an explicit override."""
    return mapexport.resolve_outdir(outdir)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="round-trip the 0xFA0 geometry chunk and report identity")
    ap.add_argument("--dat", required=True)
    ap.add_argument("--file-id", type=int, action="append",
                    help="one model file id; repeatable. Default: a sample")
    ap.add_argument("--stride", type=int, default=97,
                    help="entry stride for the sample sweep")
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args(argv)

    ok = bad = skipped = 0
    worst = []
    with Archive(a.dat) as ar:
        if a.file_id:
            table = file_id_table(ar, raw=True)
            entries = [ar.row(table[f]) for f in a.file_id]
        else:
            entries = ar.entries[::a.stride]
        for e in entries:
            try:
                head = bytes(ar.magic(e, 5))
                if head[:4] != FFNA_MAGIC or head[4] != MODEL_FFNA_TYPE:
                    continue
                data = ar.read(e)
                chunk = next((bytes(data[o:o + s])
                              for c, o, s in ffna_chunks(data)
                              if c == GEOMETRY_CHUNK), None)
            except Exception:
                skipped += 1
                continue
            if chunk is None:
                continue
            try:
                same = roundtrip(chunk) == chunk
            except (Undecodable, Unwritable, ValueError, struct.error) as ex:
                skipped += 1
                worst.append((e.index, type(ex).__name__, str(ex)[:90]))
                continue
            ok += same
            bad += not same
            if not same:
                worst.append((e.index, "DIFFERS", f"{len(chunk)} bytes"))
            if ok + bad >= a.limit:
                break
    print(f"byte-identical {ok}/{ok + bad}, {skipped} not decodable")
    for row, kind, why in worst[:12]:
        print(f"    row {row}: {kind} -- {why}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
