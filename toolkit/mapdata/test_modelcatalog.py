r"""The model catalog behind `tools/viewer/modelviewer.py`: the prefix
classifier, the stamped cache, the de-indexed build, and the template closure.

    python toolkit/mapdata/test_modelcatalog.py

THE HEADLINE IS THE SHORTCUT, AND THE CHECK IS THE ONE THAT COULD REFUTE IT.
`modelcatalog.scan` classifies every head from its first chunk header
alone, on the strength of a 400-head measurement that a geometry chunk is
always FIRST when present. Section 2 re-walks a strided sample of the
archive's heads IN FULL -- every chunk id, through `archive.ffna_chunks` --
and asserts that the prefix verdict agrees with the whole list on every one:
`kind == "model"` exactly when 0xFA0 is anywhere in the file. A head whose
FA0 sat second would redden this, and the catalog would then be filing a
model as a shell. The counts read off the prefix (FA0's `num_models` and
`collision_count`, FA1's sequence/node counts and COMPOSITED flag) are
compared against the same fields read from the FULL payload, so a wrong
offset cannot agree with itself.

THE BUILD IS CHECKED AGAINST THE BYTES, NOT AGAINST `modelfile`. The
de-indexed corner positions of every anchor sub-model are re-derived here by
`struct.unpack_from` over the sub-model's own interleaved `vertex_data` at
the stride the client's table gives, gathered through its own index list --
so a build that skipped, duplicated or reordered a corner cannot match. The
UV set the build carries is checked the same way at the field offset.

THE DIFFUSE PICK HAS AN INDEPENDENT WITNESS: `studies/unitexport/FINDINGS.md`
sec 5 named the hatcher's diffuse as FA5 slot 1 (`tex_1C7DB`, the "eraser")
and slot 2 as a cutout BEFORE this module existed, from Blender renders. The
build must land on the same slot and the same alpha classes.

Anchors: 116703 (hatcher body: 4 sub-models, no FA1), 116366 (worm: FA0 +
20-node FA1), 116228 (hatcher shell: FA6 + FA1 + FA8, COMPOSITED, no FA0).
Needs the vault's study archive; sections 0 and 1 are bare-machine safe and
the rest declare a LEDGER.skip without it (which fails the floor, as it
should -- the suite runs where the vault is).
"""

import collections
import json
import os
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, DEFAULT_DAT, ffna_chunks, \
    file_id_table  # noqa: E402
import modelcatalog as mc  # noqa: E402
import modelfile  # noqa: E402
import skelfile  # noqa: E402
import checks  # noqa: E402

LEDGER = checks.Ledger("model catalog", floor=75)
check = checks.adopt(LEDGER)

HATCHER_BODY = 116703
HATCHER_SHELL = 116228
WORM = 116366
STRIDE = 50            # every 50th head of the archive, ~430 full decodes


# ---------------------------------------------------------------------------
# 0. the prefix classifier, on bytes this file builds
# ---------------------------------------------------------------------------

def _ffna(chunk_id, payload, ftype=2):
    return b"ffna" + bytes([ftype]) + struct.pack("<II", chunk_id,
                                                  len(payload)) + payload


def _fa0_payload(num_models, collision):
    p = bytearray(0x54)
    struct.pack_into("<I", p, 0, modelfile.GEOMETRY_VERSION)
    struct.pack_into("<I", p, modelfile.NUM_MODELS_AT, num_models)
    struct.pack_into("<H", p, modelfile.COLLISION_COUNT_AT, collision)
    return bytes(p)


def _fa1_payload(seqs, nodes, flags):
    p = bytearray(0x58)
    struct.pack_into("<I", p, 0, skelfile.SKELETON_VERSION)
    p[skelfile.HDR["flags"]] = flags
    struct.pack_into("<I", p, skelfile.HDR["n18"], seqs)
    struct.pack_into("<I", p, skelfile.HDR["n2C"], nodes)
    return bytes(p)


def section0():
    print("\n0. classify_prefix on synthetic bytes")
    c = mc.classify_prefix(_ffna(0xFA0, _fa0_payload(7, 3)))
    check(c["kind"] == mc.KIND_MODEL and c["first_chunk"] == 0xFA0,
          "an FA0-first file classifies as a model", repr(c["kind"]))
    check(c["num_models"] == 7 and c["collision_count"] == 3,
          "FA0 counts are read off the prefix", f"{c['num_models']}/{c['collision_count']}")
    c = mc.classify_prefix(_ffna(0xFA1, _fa1_payload(242, 86, 0x01)))
    check(c["kind"] == mc.KIND_SKEL and c["composited"] is True
          and c["seq_count"] == 242 and c["node_count"] == 86,
          "an FA1-first file classifies as a COMPOSITED shell with its counts",
          repr({k: c[k] for k in ("composited", "seq_count", "node_count")}))
    c = mc.classify_prefix(_ffna(0xFA1, _fa1_payload(1, 2, 0x06)))
    check(c["composited"] is False and c["kind"] == mc.KIND_SKEL,
          "an FA1-first file is a skeleton whatever the flag says (the flag "
          "cannot tell a shell from an anim file -- module docstring)")
    c = mc.classify_prefix(_ffna(0xFA6, b"\0" * 32))
    check(c["kind"] == mc.KIND_OTHER and c["seq_count"] is None and c["problem"]
          and c["first_size"] == 32,
          "an FA6-first head is UNRESOLVED by the first prefix and says why")
    two = _ffna(0xFA6, b"\0" * 32) + struct.pack("<II", 0xFA1, 0x58) \
        + _fa1_payload(30, 86, 0x01)
    c2 = mc.classify_chain(two, mc.PAYLOAD_AT + 32)
    check(c2["kind"] == mc.KIND_SKEL and c2["composited"] is True
          and (c2["seq_count"], c2["node_count"]) == (30, 86),
          "classify_chain reads the FA1 header past the sound list")
    three = _ffna(0xFA6, b"\0" * 32) + struct.pack("<II", 0xFAE, 12) + b"\0" * 12 \
        + struct.pack("<II", 0xFA1, 0x58) + _fa1_payload(3, 9, 0x01)
    c2 = mc.classify_chain(three, mc.PAYLOAD_AT + 32)
    check(c2["kind"] == mc.KIND_SKEL and (c2["seq_count"], c2["node_count"]) == (3, 9),
          "...and past an FAE list too (FA6, FAE, FA1 -- 6 heads in the archive)")
    late = _ffna(0xFA6, b"\0" * 32) + struct.pack("<II", 0xFA0, 0x54) + _fa0_payload(1, 0)
    c2 = mc.classify_chain(late, mc.PAYLOAD_AT + 32)
    check(c2["kind"] == mc.KIND_OTHER and "NOT first" in c2["problem"],
          "a geometry chunk found LATE is reported as a refutation, never filed as a model")
    long = _ffna(0xFA6, b"\0" * 8) + b"".join(struct.pack("<II", 0xFAE, 8) + b"\0" * 8
                                                for _ in range(mc.MAX_CHAIN))
    c2 = mc.classify_chain(long, mc.PAYLOAD_AT + 8)
    check(c2["kind"] == mc.KIND_OTHER and "within" in c2["problem"],
          f"a chain longer than MAX_CHAIN={mc.MAX_CHAIN} is a named problem")
    c2 = mc.classify_chain(_ffna(0xFA6, b"\0" * 32), mc.PAYLOAD_AT + 32)
    check(c2["problem"] and "ends before" in c2["problem"],
          "a head that ends after its FA6 is a named problem")
    c = mc.classify_prefix(b"ATEX" + b"\0" * 40)
    check(c["problem"] is not None and c["kind"] == mc.KIND_OTHER,
          "a non-ffna prefix records a problem", c["problem"])
    c = mc.classify_prefix(_ffna(0xFA0, _fa0_payload(1, 0), ftype=3))
    check("type 3" in (c["problem"] or ""), "a map (type 3) is refused by name",
          c["problem"])
    c = mc.classify_prefix(_ffna(0xFA0, b"\0" * 8))
    check(c["kind"] == mc.KIND_MODEL and c["num_models"] is None
          and c["problem"], "a short FA0 payload keeps the kind and names the shortfall",
          c["problem"])
    bad = bytearray(_fa1_payload(1, 1, 0))
    struct.pack_into("<I", bad, 0, 0x25)
    c = mc.classify_prefix(_ffna(0xFA1, bytes(bad)))
    check(c["seq_count"] is None and "version" in c["problem"],
          "an FA1 with the wrong version yields no counts", c["problem"])
    c = mc.classify_prefix(b"ffna\x02\x00")
    check(c["problem"] and c["first_chunk"] is None,
          "a prefix too short for a chunk header is a recorded problem")


# ---------------------------------------------------------------------------
# 1. the cache: round trip, and where it may not go
# ---------------------------------------------------------------------------

def section1():
    print("\n1. the catalog cache")
    recs = []
    for row, kind in ((10, mc.KIND_MODEL), (11, mc.KIND_SKEL), (12, mc.KIND_OTHER)):
        r = mc.HeadRecord(row, [row * 100, row * 100 + 1], 4096)
        r.kind = kind
        r.first_chunk = 0xFA0 if kind == mc.KIND_MODEL else 0xFA1
        r.num_models = 2 if kind == mc.KIND_MODEL else None
        r.composited = True if kind == mc.KIND_SKEL else None
        recs.append(r)
    stamp = {"archive": "synthetic", "size_on_disk": 1, "mft_offset": 2,
             "mft_size": 3, "row_count": 4, "block_size": 512,
             "mft_sha256": "ab" * 32}
    cat = mc.Catalog(stamp, recs)
    back = mc.Catalog.from_dict(json.loads(json.dumps(cat.to_dict())))
    check([r.to_dict() for r in back.records] == [r.to_dict() for r in recs],
          "to_dict/from_dict round-trips every record field through JSON")
    check(back.by_fid[1101].row == 11 and back.by_row[10].kind == mc.KIND_MODEL,
          "every spelling of a row resolves through by_fid; by_row is keyed by row")
    check(back.census() == {"model": 1, "skel": 1, "other": 1}
          and len(back.models()) == 1 and len(back.skeletons()) == 1,
          "census/models/skeletons partition the records", repr(back.census()))
    check(recs[0].fid == 1000, "the reported id is the smallest plain spelling")

    inside = os.path.join(HERE, "should_never_exist.catalog.json")
    try:
        mc.save(cat, inside)
        refused = False
    except mc.Refused:
        refused = True
    check(refused and not os.path.exists(inside),
          "save() REFUSES a path inside the working tree and writes nothing")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sub", "cat.json")
        out = mc.save(cat, path)
        check(os.path.isfile(out), "save() writes outside both trees, creating the directory")
        again = mc.load(out)
        check(again.stamp == stamp and len(again.records) == 3,
              "load() without an archive returns the saved catalog")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"format_version": 99}, fh)
        try:
            mc.load(out)
            ok = False
        except mc.Refused:
            ok = True
        check(ok, "load() refuses a foreign format_version")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        try:
            mc.load(out)
            ok = False
        except mc.Refused:
            ok = True
        check(ok, "load() refuses unreadable JSON with the reason")


# ---------------------------------------------------------------------------
# 2. the shortcut against the whole file, on a strided sample
# ---------------------------------------------------------------------------

def section2(ar):
    print(f"\n2. prefix verdicts against full chunk walks, every {STRIDE}th head")
    rows = mc.head_rows(ar)[::STRIDE]
    t0 = time.time()
    cat = mc.scan(ar, rows=rows)
    check(len(cat.records) == len(rows) >= 400,
          f"the sample is {len(rows)} heads (>= 400)", f"scan {time.time() - t0:.2f} s")
    kinds_ok = first_ok = fa0_ok = fa1_ok = 0
    fa0_n = fa1_n = 0
    seen = collections.Counter()
    disagreements = []
    t0 = time.time()
    for rec in cat.records:
        if rec.problem and rec.first_chunk is None:
            continue
        data = ar.read(ar.row(rec.row))
        walk = list(ffna_chunks(data))
        ids = [cid for cid, _, _ in walk]
        has_fa0 = modelfile.GEOMETRY_CHUNK in ids
        fa1 = next(((off, size) for cid, off, size in walk
                    if cid == skelfile.SKELETON_CHUNK), None)
        h = skelfile.read_header(data[fa1[0]:fa1[0] + fa1[1]]) if fa1 else None
        # THE EXPECTED KIND FROM THE WHOLE FILE, independent of any prefix
        if has_fa0:
            want = mc.KIND_MODEL
        elif h is not None:
            want = mc.KIND_SKEL
        else:
            want = mc.KIND_OTHER
        seen[want] += 1
        if rec.kind == want:
            kinds_ok += 1
        else:
            disagreements.append((rec.row, rec.kind, want, [hex(i) for i in ids]))
        if rec.first_chunk == ids[0]:
            first_ok += 1
        cid, off, size = walk[0]
        if cid == modelfile.GEOMETRY_CHUNK:
            fa0_n += 1
            nm = struct.unpack_from("<I", data, off + modelfile.NUM_MODELS_AT)[0]
            cc = struct.unpack_from("<H", data, off + modelfile.COLLISION_COUNT_AT)[0]
            if (rec.num_models, rec.collision_count) == (nm, cc):
                fa0_ok += 1
        elif h is not None:
            # every non-model with an FA1 -- FA1-first AND FA6-first -- must
            # carry the header's counts, the second read included
            fa1_n += 1
            if (rec.seq_count, rec.node_count, rec.composited) == (
                    h["n18"], h["n2C"], bool(h["flags"] & skelfile.FLAG_COMPOSITED)):
                fa1_ok += 1
    n = len(cat.records)
    check(kinds_ok == n and not disagreements,
          f"kind agrees with the FULL file on {kinds_ok}/{n} heads: model <=> FA0 "
          f"present, skel <=> an FA1 and no FA0",
          f"{time.time() - t0:.1f} s; {dict(seen)}; disagreements: {disagreements[:3]}")
    flagged = sum(1 for r in cat.records if r.kind == mc.KIND_SKEL and r.composited)
    check(seen[mc.KIND_SKEL] >= 6 and flagged == seen[mc.KIND_SKEL],
          f"every skeleton head in the sample carries the COMPOSITED flag, "
          f"{flagged}/{seen[mc.KIND_SKEL]} -- the flag means 'no geometry', so it "
          f"cannot separate shells from anim files (module docstring)")
    check(first_ok == n, f"first chunk id agrees on {first_ok}/{n}")
    check(fa0_n >= 300 and fa0_ok == fa0_n,
          f"FA0 num_models/collision_count agree on {fa0_ok}/{fa0_n} (>= 300)")
    check(fa1_n >= 6 and fa1_ok == fa1_n,
          f"FA1 seq/node/composited agree on {fa1_ok}/{fa1_n} skeleton heads (>= 6), "
          f"the FA6-first ones included")
    both = sum(1 for r in cat.records if r.kind == mc.KIND_MODEL)
    check(both >= 0.9 * n, f"models are the bulk of the sample: {both}/{n}")
    return cat


def section2b(ar):
    print("\n2b. the vault cache for this archive")
    t0 = time.time()
    cat, path, fresh = mc.open_catalog(ar)
    census = cat.census()
    check(cat.scanned_rows == len(mc.head_rows(ar)),
          f"the cache covers every head: {cat.scanned_rows}",
          f"{'fresh scan' if fresh else 'loaded'} in {time.time() - t0:.1f} s from {path}")
    check(census.get("model", 0) >= 20000 and census.get("skel", 0) >= 700,
          "floors: >= 20,000 models and >= 700 skeleton heads", repr(census))
    chained = [r for r in cat.skeletons() if r.first_chunk != skelfile.SKELETON_CHUNK]
    check(len(chained) >= 300 and all(r.seq_count is not None for r in chained),
          f"every one of the {len(chained)} skeleton heads whose FA1 is not first "
          f"resolved its header through the chain (>= 300; FA6-first is half the class)")
    probs = [r for r in cat.records if r.problem]
    check(len(probs) <= 1 and all(r.row == 8316 for r in probs),
          "at most one head carries a problem, and it is the known row-8316 anomaly "
          "(unitmodels FINDINGS: a flags-515 head that is not an ffna file)",
          repr([(r.row, r.problem) for r in probs]))
    for fid, kind in ((HATCHER_BODY, mc.KIND_MODEL), (WORM, mc.KIND_MODEL),
                      (HATCHER_SHELL, mc.KIND_SKEL)):
        rec = cat.by_fid.get(fid)
        check(rec is not None and rec.kind == kind,
              f"anchor {fid} is catalogued as a {kind}")
    rec = cat.by_fid[HATCHER_SHELL]
    check(rec.first_chunk == mc.SOUND_CHUNK and rec.composited is True
          and (rec.seq_count, rec.node_count) == (242, 86) and rec.problem is None,
          "the hatcher shell is FA6-first and the chain resolves it: "
          "composited, 242 sequences, 86 nodes, no problem left")
    fae = [r for r in cat.skeletons() if r.first_chunk == mc.SOUND_CHUNK
           and r.fids and cat.by_fid[r.fids[0]] is r and r.row in (18731, 136755, 150245, 150389)]
    check(len(fae) == 4 and all(r.seq_count is not None for r in fae),
          "the four FA6, FAE, FA1 heads the first cut could not read are resolved")
    check(cat.by_fid[HATCHER_BODY].num_models == 4
          and cat.by_fid[WORM].num_models == 3,
          "FA0 sub-model counts off the prefix: hatcher 4, worm 3")
    stale = dict(cat.stamp)
    stale["mft_sha256"] = "0" * 64
    with tempfile.TemporaryDirectory() as tmp:
        p = mc.save(mc.Catalog(stale, cat.records[:3]), os.path.join(tmp, "c.json"))
        try:
            mc.load(p, ar)
            ok = False
        except mc.Refused as exc:
            ok = "different archive state" in str(exc)
        check(ok, "a cache stamped from another archive state is REFUSED against this one")


# ---------------------------------------------------------------------------
# 3. the build against the archive's own vertex bytes
# ---------------------------------------------------------------------------

def _corners_from_bytes(sm, field_off, width):
    fmt = f"<{width}f"
    out = []
    for i in sm.indices:
        out.extend(struct.unpack_from(fmt, sm.vertex_data, i * sm.stride + field_off))
    return out


def section3(ar, table):
    print("\n3. build_view on the anchors")
    cache = mc.TextureCache(ar, table)
    t0 = time.time()
    view = mc.build_view(ar, table, HATCHER_BODY, textures=cache)
    dt = time.time() - t0
    mf = modelfile.ModelFile.load(HATCHER_BODY, ar, table)
    geo = mf.geometry()
    check(len(view.submeshes) == 4 == len(geo.submodels),
          "the hatcher body builds 4 sub-meshes", f"{dt:.2f} s")
    pos_ok = uv_ok = 0
    for sub, sm in zip(view.submeshes, geo.submodels):
        if len(sub.pos) == 9 * sub.ntri == 3 * len(sm.indices) and \
                list(sub.pos) == _corners_from_bytes(sm, 0, 3):
            pos_ok += 1
        off = sm.fields.get(modelfile.FIELD_TEXCOORD_BITS[sub.uv_set])
        if sub.uv is not None and list(sub.uv) == _corners_from_bytes(sm, off, 2):
            uv_ok += 1
    check(pos_ok == 4, f"de-indexed corner positions equal the vertex BYTES gathered "
          f"through the index list, {pos_ok}/4 sub-models")
    check(uv_ok == 4, f"the carried UV set equals the bytes at its field offset, {uv_ok}/4")
    slots = [s.texture_slot for s in view.submeshes]
    fids = [s.texture_fid for s in view.submeshes]
    check(slots == [1, 1, 2, 2] and fids == [0x1C7DB, 0x1C7DB, 0x1C7DD, 0x1C7DD],
          "the diffuse pick is FA5 slot 1 for the body and 2 for the trim -- "
          "unitexport FINDINGS sec 5's independent verdict", repr(slots))
    alphas = [s.alpha for s in view.submeshes]
    check(alphas == ["erases", "erases", "cutout", "cutout"],
          "alpha classes: slot 1 ERASES, slot 2 is a cutout (unitexport sec 5 table)",
          repr(alphas))
    tex = view.textures[0x1C7DB]
    check(tex.width == 512 and tex.height == 512 and len(tex.rgba) == 512 * 512 * 4,
          "the 512x512 diffuse decodes to exactly w*h*4 RGBA bytes")
    check(view.skeleton is None and view.composited is None and not view.sequences,
          "a body with no FA1 reports no skeleton rather than an empty one")
    check(view.bounds[0][2] < view.bounds[1][2] <= 0.5
          and view.radius() > 30,
          "the body stands in model-space -z (world-up) below its origin",
          repr(view.bounds))
    check(not view.problems, "no problem recorded", repr(view.problems))
    check(cache.get(0x1C7DB) is tex, "the texture cache returns the same object twice")

    view = mc.build_view(ar, table, WORM, textures=cache)
    check(len(view.submeshes) == 3 and view.skeleton is not None
          and len(view.skeleton) == 20 and view.composited is False,
          "the worm builds 3 sub-meshes and a 20-node, non-composited skeleton")
    check(len(view.sequences) == 10, "the worm's 10 sequences are carried")
    check(all(n.link <= n.index for n in view.skeleton),
          "every node links to an earlier node (topological order)")
    lo, hi = view.bounds
    inside = sum(1 for n in view.skeleton if n.keyed
                 and all(lo[k] - 1e-3 <= n.base[k] <= hi[k] + 1e-3 for k in range(3)))
    keyed = sum(1 for n in view.skeleton if n.keyed)
    check(keyed >= 1 and inside == keyed,
          f"every channel-carrying node base lies inside the mesh box, {inside}/{keyed} "
          f"(unitexport sec 3's bind-pose fact, re-measured)")
    check([s.texture_fid for s in view.submeshes] == [0x1C68B] * 3
          and [s.texture_slot for s in view.submeshes] == [4] * 3,
          "the worm's three sub-models all pick FA5 slot 4")
    sk = skelfile.Skeleton.load(WORM, ar)
    anims = sk.anims()
    check([n.base for n in view.skeleton] == [a["base"] for a in anims]
          and [n.link for n in view.skeleton] == [a["link"] for a in anims],
          "skeleton_nodes agrees with Skeleton.anims() on every base and link")
    check([n.keyed for n in view.skeleton] ==
          [bool(a["trans"] or a["rot"] or a["aux"]) for a in anims],
          "and on which nodes carry keys")
    check(view.collision is None and view.collision_tris == 0,
          "the worm has no collision mesh and says so")

    view = mc.build_view(ar, table, HATCHER_SHELL, textures=cache)
    check(not view.submeshes and view.skeleton is not None and len(view.skeleton) == 86
          and view.composited is True and len(view.sequences) == 242,
          "the shell builds no geometry, an 86-node COMPOSITED skeleton, 242 sequences")
    check([c for c, _ in view.chunks] == [0xFA6, 0xFA1, 0xFA8],
          "its chunk list is FA6, FA1, FA8", repr(view.chunks))
    check(view.bounds[0] != view.bounds[1], "bounds fall back to the skeleton's extent")

    view = mc.build_view(ar, table, HATCHER_BODY, textures=None, skeleton_fid=HATCHER_SHELL)
    check(len(view.submeshes) == 4 and view.skeleton is not None
          and len(view.skeleton) == 86 and view.skeleton_from == HATCHER_SHELL,
          "a body drawn with its shell's skeleton carries both, and names the source")
    check(not view.textures and all(s.alpha is None for s in view.submeshes),
          "textures=None decodes nothing and leaves alpha unclassified")
    try:
        mc.build_view(ar, table, 0x7FFFFFF0)
        ok = False
    except KeyError:
        ok = True
    check(ok, "an unknown file id raises rather than returning an empty view")

    # a prop with collision, from the exported corpus: 0x102DB has cidx/cpos
    view = mc.build_view(ar, table, 0x102DB, textures=cache)
    check(view.collision is not None and view.collision_tris > 0
          and len(view.collision) == view.collision_tris * 18,
          f"prop 0x102DB carries {view.collision_tris} collision tri(s) as 6 line "
          f"corners each")
    check(view.submeshes and all(s.uv_sets >= 1 for s in view.submeshes),
          "and its sub-models carry UV sets")


# ---------------------------------------------------------------------------
# 4. templates and content maps
# ---------------------------------------------------------------------------

def section4(ar, table):
    print("\n4. templates and content maps")
    import content
    world = content.load()
    rows = [k for k, r in world.rows("npc").items() if r.get("file_id") is not None]
    tm = mc.templates(world)
    check(len(tm) == len(rows) >= 50 and [t["key"] for t in tm] == sorted(rows),
          f"templates() lists every npc row with a file_id, sorted: {len(tm)}")
    st = mc.shell_templates(world)
    check(HATCHER_SHELL in st and {t["key"] for t in st[HATCHER_SHELL]} >= {"hatcher", "lieutenant_fisk"}
          and sum(len(v) for v in st.values()) == len(tm),
          f"shell_templates joins every row onto its shell: {len(st)} shells named by the wire, "
          f"the hatcher shell by {len(st[HATCHER_SHELL])} rows")
    by = {t["key"]: t for t in tm}
    r = mc.resolve_template(ar, table, by["hatcher"])
    check(r["needs_body"] is True and r["closed"] and r["draw"] == HATCHER_BODY,
          "hatcher: composited shell, closed, draws its body", repr(r["roles"]))
    r = mc.resolve_template(ar, table, by["lakeside_worm"])
    check(r["needs_body"] is False and r["closed"] and r["draw"] == WORM,
          "lakeside_worm: draws the shell itself (it has geometry)")
    fake = {"key": "x", "file_id": HATCHER_SHELL, "model_id": None}
    r = mc.resolve_template(ar, table, fake)
    check(r["needs_body"] is True and r["draw"] is None,
          "a composited shell with no body draws NOTHING -- the parade's white box, "
          "never invented")
    t0 = time.time()
    maps, problems = mc.content_map_models(ar, table, world)
    check("449" in maps and len(maps["449"][1]) >= 50,
          f"Kamadan (map 449) references {len(maps.get('449', ('', []))[1])} models "
          f"(>= 50; M4 counted 86)", f"{time.time() - t0:.1f} s, {len(problems)} problem(s)")
    check(all(isinstance(f, int) for _n, ids in maps.values() for f in ids),
          "every referenced id is an int")


def main():
    section0()
    section1()
    if not os.path.isfile(DEFAULT_DAT):
        LEDGER.skip("sections 2-4", f"no study archive at {DEFAULT_DAT}")
        return LEDGER.verdict()
    with Archive(DEFAULT_DAT) as ar:
        table = file_id_table(ar)
        section2(ar)
        section2b(ar)
        section3(ar, table)
        section4(ar, table)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
