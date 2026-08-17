r"""The U6 writer: typed re-serialization identity, the order control, the
datwrite round trip, and the U7 seam.

    python toolkit/mapdata/test_skelwrite.py          # synthetics + anchors +
                                                      #   stride-89 corpus +
                                                      #   the datwrite half
    python toolkit/mapdata/test_skelwrite.py --all    # the complete flags=515
                                                      #   population (slow)

WHAT IDENTITY PROVES HERE, AND WHAT WOULD MAKE IT VACUOUS. `skelwrite.encode`
rebuilds the chunk from TYPED VALUES -- header fields, sequence records, key
times/tags, blk2C/blk48 records and channels, n40 events, n3E track -- and
carries bytes only where `skelfile`'s layer is genuinely opaque. Byte-identity
then proves the typed layer is COMPLETE (nothing decoded is lossy). A writer
that concatenated the reader's `.spans` would pass the same comparison while
proving nothing -- the memcpy-loader defect class (`studies/models/FINDINGS.md`
§4.5) -- so this file pins the property three independent ways:

  1. **The hand-built representation** (section 0): a typed repr assembled
     from THIS FILE'S literals, never decoded from any payload, must encode
     to the same bytes `test_skelfile.synth_anim()` builds from ITS literals.
     A spans-concatenating encoder cannot run at all on an input that has no
     spans; two builders meeting byte-for-byte is the same two-derivations
     discipline `test_skelfile` uses for the walk.
  2. **The opaque-byte pins** (section 1): on the anchors the representation's
     total carried bytes are pinned at their measured values (worm 823 of
     82,169; shell 559 of 29,495 -- about 1%). A rewrite that quietly carried
     a typed region as bytes moves a number two files must agree on.
  3. **The U7 seam** (sections 0b and 1): a modification made to TYPED VALUES
     must land in the output at the predicted bytes. An encoder that copied
     stored bytes would emit the unmodified original and the byte-diff check
     goes red.

THE ORDER CONTROL, writer-side, and why the criterion is identity rather than
re-parse equivalence (the rung's stated rationale, exhibited): the walk pins
the order of adjacent fixed-size blocks NOWHERE -- closure tests their sum --
so `swap_n14_n34()` below is a deliberately wrong writer variant that emits
n34 before n14. Its output RE-PARSES GREEN (header intact, every gate passes,
closure exact, the typed layer decodes without complaint) and is byte-
different from the source exactly inside the two blocks. Both halves are
asserted, on a synthetic with distinct block content (synth()'s uniform 0xAA
fill would make the swap invisible, so the test plants its own bytes) and on
the worm, whose n14/n34 contents are measured distinct.

THE DATWRITE HALF states its identity levels PLAINLY:

  * serialized FA1 chunk bytes: EXACT (sections 0-2);
  * whole-container bytes: EXACT (sections 0-2);
  * decompressed row payload read back out of the rebuilt archive: EXACT
    (section 3);
  * the STORED form: legitimately DIFFERENT -- the source row is
    compression 8 (90,616 B) and the written row is stored/uncompressed
    (129,368 B), because the established write path writes uncompressed and
    no compression-8 encoder exists (`studies/datwrite/FINDINGS.md`, blocker
    2). That is also why the verb is `datmove`: the recorded wall is that
    `datwrite --replace` will not relocate, and an uncompressed payload
    rarely fits a compressed row's reservation. The wall is EXHIBITED
    (replace refuses, naming relocation) beside the succeeding move.

The rebuilt archive is a 3-row REBUILD carrying the worm's real chain rows
byte-verbatim (root flags=515 -> mid flags=1 -> tail flags=2817, the
`alloc.nextStream` chain `studies/datwrite/FINDINGS.md` measured), laid out
by this file with its own literals at loader-legal indices (>= 16), plus a
free run sized for the moved payload -- the same fixture discipline as
`test_datmove.py`, with real payloads where that test uses patterns. It
lives under the vault (never the repo), and the full-scale precedent -- a
1.6 GB move on the real 4.2 GB archive that the retail client then read,
compiled from, and left byte-identical across a play session -- is
`test_datmove.py` / FINDINGS 39's, cited rather than repeated. U7's kill/keep
names the untouched mid/tail rows as the prime suspect if the client rejects,
so the chain check here is load-bearing: after the move the root's nextStream
still names the mid, the mid's the tail, and both partners are byte-identical
-- with a corrupted-chain control proving the checker can report.

DEGRADATION, measured like `test_unitexport.py` documents: a vault-less run
executes sections 0/0b/0c only -- MEASURED 32 checks plus a declared skip,
RED on the floor by design (plumbing verified, nothing about ArenaNet's
bytes). A full green run executes 66.
"""

import argparse
import contextlib
import copy
import io
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
from skelfile import Skeleton, walk, SKELETON_CHUNK  # noqa: E402
import skelwrite  # noqa: E402
from skelwrite import (extract, encode, roundtrip_fa1,  # noqa: E402
                       rebuild_container, scale_sequence_keytimes,
                       Unwritable)
import datmove  # noqa: E402
import datwrite  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402
# One copy of each instrument: the synthetic builders are test_skelfile's
# (their literals are independent of skelfile.TERMS *and* of skelwrite),
# exactly as test_unitexport imports them.
from test_skelfile import (synth, synth_anim, FULL_KW,  # noqa: E402
                           HEAD_FLAGS, STRIDE, ALL_FA1, ALL_HEADS,
                           ANOMALY_ROW)

ANCHOR_SHELL = 116228
ANCHOR_WORM = 116366
ANCHOR_BODY = 116703

#: MEASURED 2026-08-16 through skelwrite.extract on the study archive: the
#: bytes the representation carries opaque (pad09 + n14/n34 + var-arrays +
#: n44 tail). Pinned so a writer that regresses to carrying a typed region
#: as bytes moves a number this file must agree on.
WORM_OPAQUE = 823
WORM_FA1 = 82169
SHELL_OPAQUE = 559
SHELL_FA1 = 29495

#: MEASURED 2026-08-16: the parser-unread header bytes +0x09..+0x0B are NOT
#: zero -- U6's first finding, and why pad09 is carried rather than assumed.
WORM_PAD09 = bytes.fromhex("070000")
SHELL_PAD09 = bytes.fromhex("420000")

#: The worm's chain and container, MEASURED (probe 2026-08-16): row sizes and
#: flags as the study archive stores them.
WORM_CONTAINER = 129368
WORM_STORED = 90616
CHAIN_FLAGS = (515, 1, 2817)

#: The U7 seam target, MEASURED: worm sequence 2 spans keys[2:3) = [200000]
#: (the only key its span holds); x2 -> [400000], so exactly key index 2
#: changes. Sequence 4 spans [86666], and 86666/4 is not an integer -- the
#: deterministic inexactness refusal.
SEAM_SEQ, SEAM_KEY, SEAM_OLD, SEAM_NEW = 2, 2, 200000, 400000
INEXACT_SEQ, INEXACT_DEN = 4, 4

# -- the mini-archive layout (this file's own literals; test_datmove's shape,
#    loader-legal chain indices >= 16) ---------------------------------------
BLOCK = 512
ENTRY_SIZE = 24
ENTRY_COUNT = 19
ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_ROOT, ROW_MID, ROW_TAIL = 16, 17, 18
FREE_BLOCKS = 253                 # >= ceil(129368/512) = 253


def reservation(size):
    return -(-size // BLOCK) * BLOCK


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def swap_n14_n34(payload):
    """The deliberately wrong WRITER variant: n34 emitted before n14.

    Arithmetic owned by this file (header counts via struct, strides 16/24
    as literals) -- no skelwrite internals. The blocks are adjacent and
    fixed-size, which is exactly the zone the walk cannot pin.
    """
    a = struct.unpack_from("<I", payload, 0x14)[0] * 16
    b = struct.unpack_from("<I", payload, 0x34)[0] * 24
    lo = 0x58
    return (payload[:lo] + payload[lo + a:lo + a + b]
            + payload[lo:lo + a] + payload[lo + a + b:])


def diff_offsets(a, b):
    """Every byte offset where two equal-length byte strings differ."""
    return [i for i in range(len(a)) if a[i] != b[i]]


def refuses(fn, *args, **kw):
    """True iff fn raises Unwritable. Any OTHER exception propagates -- a
    guard that swallowed everything would hide a crash as a pass."""
    try:
        fn(*args, **kw)
        return False
    except Unwritable:
        return True


# ---------------------------------------------------------------------------

def section0(check):
    print("\n== 0. synthetics: identity, refusals, the order control "
          "(no vault) ==")

    # -- round trips on both builders' fixtures. FULL_KW fires EVERY block,
    #    including n56 (0 of 14,571 corpus files -- only a synthetic can put
    #    the writer's n56 arithmetic under test) and the opaque var-arrays;
    #    synth_anim carries real typed content in every decoded region.
    full = synth(**FULL_KW)
    check(roundtrip_fa1(full) == full,
          "the full-options fixture round-trips byte-identically -- "
          "including the n56 var-array no corpus file can exercise")
    anim = synth_anim()
    check(roundtrip_fa1(anim) == anim,
          "the typed-content fixture round-trips byte-identically")
    mine = synth(n14=1, n34=2, b2c=((1, 0, 1),), n38=(2,),
                 keys=((0, 1), (5000, 3)), seqs=((0, 2),),
                 n52=(1,), n40=2, n44=1, b48=((0, 2),),
                 n50=(2,), n54=(1,), n55=(3,), n56=(2, 0, 4), n57=(2,),
                 n3e=1)
    check(roundtrip_fa1(mine) == mine,
          "this file's own all-blocks fixture (distinct literals, second "
          "n56 shape) round-trips byte-identically")

    # -- the hand-built representation: typed values from THIS FILE's
    #    literals, never decoded from any payload. It must meet synth_anim's
    #    bytes exactly -- an encoder that copies source spans cannot run here.
    hdr = {k: 0 for k in ("ver", "u04", "flags", "u0C", "u10", "n14", "n18",
                          "u1C", "f20", "u24", "f28", "n2C", "i30", "n34",
                          "n38", "n3C", "n3E", "n40", "n44", "n48", "u4C",
                          "n50", "n52", "n54", "n55", "n56", "n57")}
    hdr.update(ver=0x26, flags=0x30, n18=1, n2C=1, n3C=2, n3E=2, n40=1,
               n44=1, n48=1, f20=0.0, f28=0.0)
    hand = {
        "header": hdr, "pad09": b"\x00\x00\x00",
        "sequences": [{"u8_00": 7, "u32_01": 42, "u32_05": 0, "start": 0,
                       "u32_09": 100000, "end": 100000, "lo": 0, "hi": 2,
                       "u32_0F": 0, "f32_13": 1.0}],
        "key_times": [0, 100000], "key_tags": [2, 6],
        "anims": [{"base": (1.5, 2.5, 3.5), "flags": 0x10000000,
                   "trans": ([0, 100000], [(0.0, 0.0, 0.0),
                                           (10.0, 20.0, 30.0)]),
                   "rot": ([0, 100000], [(0.0, 0.0, 0.0, 1.0),
                                         (1.0, 0.0, 0.0, 0.0)]),
                   "aux": None}],
        "tracks": [{"base": (0.0, 0.0, 0.5), "flags": 0x08000000, "u10": 9,
                    "ch0": ([0, 200000], [(0.0, 0.0, 1.0), (0.0, 0.0, 2.0)]),
                    "ch1": None}],
        "sound_events": [{"seq": 0, "time": 50000, "path_index": 0,
                          "raw_tail": bytes(10)}],
        "event_track": ([0, 50000], [(0, 0), (1, 5)]),
        "opaque": {n: b"" for n in skelwrite.OPAQUE_BLOCKS},
    }
    hand["opaque"]["n44_tail"] = bytes(range(12))
    check(encode(hand) == anim,
          "a typed repr HAND-BUILT from this file's literals encodes to "
          "synth_anim()'s exact bytes -- the encoder ran with no source "
          "payload in sight, which a spans-concatenating writer cannot")

    # -- refusals, each by name, each beside the passing encode above
    t = extract(Skeleton.decode(anim))
    t["header"]["n18"] = 2
    check(refuses(encode, t), "a count/list mismatch is refused (n18=2 over "
                              "1 sequence), never serialized wrong")
    t = extract(Skeleton.decode(anim))
    t["sequences"][0]["start"] = 999
    check(refuses(encode, t),
          "diverged start/u32_05 aliases are refused by name")
    t = extract(Skeleton.decode(full))
    t["opaque"]["n38"] = t["opaque"]["n38"][:-1]
    check(refuses(encode, t),
          "a truncated opaque var-array fails its tiling walk and is refused")
    t = extract(Skeleton.decode(anim))
    t["pad09"] = b"\x00"
    check(refuses(encode, t), "a wrong-size pad09 is refused")
    t = extract(Skeleton.decode(anim))
    t["header"]["n2C"] = 0
    t["anims"] = []
    check(refuses(encode, t),
          "n2C == 0 is refused -- the client's own hard reject (error 12)")

    # -- the container writer on synthetics
    cont = b"ffna" + bytes([2]) + struct.pack("<II", SKELETON_CHUNK,
                                              len(anim)) + anim \
        + struct.pack("<II", 0xFA6, 4) + b"\xDE\xAD\xBE\xEF"
    check(rebuild_container(cont) == cont,
          "a synthetic two-chunk container re-emits byte-identically "
          "(FA1 through the typed layer, the other chunk verbatim)")
    new = bytearray(anim)
    struct.pack_into("<i", new, len(anim) - 24, 999)   # arrA time of n3E
    sub = rebuild_container(cont, fa1=bytes(new))
    check(sub != cont and len(sub) == len(cont)
          and Skeleton.from_container(sub).payload == bytes(new),
          "fa1= substitutes exactly the FA1 payload (the U7 seam at "
          "container level)")
    nofa1 = b"ffna" + bytes([2]) + struct.pack("<II", 0xFA6, 4) + b"\x00" * 4
    check(rebuild_container(nofa1) == nofa1,
          "a container with no FA1 re-emits whole")
    check(refuses(rebuild_container, nofa1, fa1=b"x"),
          "fa1= against a no-FA1 container is refused -- a caller cannot "
          "believe it modified a file it did not")
    check(refuses(rebuild_container, b"ffna" + bytes([3]) + cont[5:]),
          "an ffna type other than 2 is refused")

    # -- the order control, writer-side. Distinct block content is planted
    #    (synth()'s uniform fill would make a swap invisible = a control
    #    that cannot fail).
    p = bytearray(synth(n14=1, n34=1, keys=((0, 1),), seqs=((0, 1),)))
    p[0x58:0x68] = bytes(range(0x10, 0x20))            # n14 record, distinct
    p = bytes(p)
    check(roundtrip_fa1(p) == p,
          "the straight writer is identical on the order-control fixture "
          "(the positive control the swap is judged against)")
    swapped = swap_n14_n34(p)
    r = walk(swapped)
    check(r["ok"], "the BLOCK-SWAPPED writer variant's output RE-PARSES "
                   "GREEN -- header intact, every gate passes, closure exact")
    check(swapped != p, "...and fails byte-identity, which is therefore the "
                        "criterion re-parse equivalence cannot replace")
    d = diff_offsets(p, swapped)
    check(d and all(0x58 <= i < 0x58 + 40 for i in d),
          "...with the diff confined to the two swapped fixed-size blocks "
          "(the exact zone closure cannot pin)",
          f"{len(d)} bytes in [{hex(min(d))}, {hex(max(d))}]" if d else "")


def section0b(check):
    print("\n== 0b. the U7 seam on synthetics (no vault) ==")
    anim = synth_anim()
    src = Skeleton.decode(anim)
    keys_off = dict((n, o) for n, o, s in src.spans)["keys"]

    t = extract(src)
    changed = scale_sequence_keytimes(t, 0, 2)
    check(changed == [1],
          "scaling seq 0 x2 changes exactly key 1 (key 0 is time 0)")
    mod = encode(t)
    d = set(diff_offsets(anim, mod))
    check(d and d <= set(range(keys_off + 4, keys_off + 8)),
          "the modified output differs from the source ONLY inside the "
          "predicted key-time bytes (key 1's int32 slot)",
          f"diff at {sorted(hex(i) for i in d)}")
    sk2 = Skeleton.decode(mod)
    check(sk2.key_times_raw() == [0, 200000],
          "re-decoding the modified output yields the scaled times")

    t = extract(src)
    try:
        scale_sequence_keytimes(t, 0, 1, 3)
        check(False, "inexact division is refused (100000/3)")
    except Unwritable:
        check(True, "inexact division is refused (100000/3)")
    check(refuses(scale_sequence_keytimes, extract(src), 0, 2 ** 20),
          "int32 overflow is refused, not wrapped")
    check(refuses(scale_sequence_keytimes, extract(src), 5, 2),
          "an out-of-range sequence index is refused")
    check(refuses(scale_sequence_keytimes, extract(src), 0, 1.5),
          "a non-integer factor is refused -- key times are int32 "
          "measurements")


def section_outdir(check, tmp):
    print("\n== 0c. the write path refuses the repo from birth ==")
    tree = os.path.dirname(os.path.dirname(HERE))

    def raises(fn, *a):
        try:
            fn(*a)
            return False
        except ValueError:
            return True

    for target in (tree, HERE, os.path.join(tree, "studies")):
        check(raises(skelwrite.resolve_outdir, target),
              f"refuses {os.path.relpath(target, tree) or 'the tree root'}")
    vault_out = vaultpath.vault_path("exports")
    check(skelwrite.resolve_outdir(None) == os.path.abspath(vault_out),
          "the default destination is vault/exports")
    check(skelwrite.resolve_outdir(tmp) == os.path.abspath(tmp),
          "a scratch directory outside the tree is allowed (positive "
          "control -- a guard that refuses everything proves nothing)")
    import mapexport
    check(skelwrite.resolve_outdir.__module__ == "skelwrite"
          and "mapexport.resolve_outdir" in
          (skelwrite.resolve_outdir.__doc__ or "")
          and raises(mapexport.resolve_outdir, tree),
          "the guard delegates to mapexport's single copy of the rule, "
          "which refuses the same tree")
    p = skelwrite.write_bytes(b"selftest", "selftest.bin", tmp)
    check(os.path.isfile(p) and open(p, "rb").read() == b"selftest",
          "write_bytes writes through the resolved directory")


def section1(check, ar, idt):
    print("\n== 1. the anchors ==")
    shell = bytes(ar.read(ar.row(idt[ANCHOR_SHELL])))
    worm = bytes(ar.read(ar.row(idt[ANCHOR_WORM])))
    body = bytes(ar.read(ar.row(idt[ANCHOR_BODY])))

    for name, data in (("116228 (hatcher shell, COMPOSITED)", shell),
                       ("116366 (worm)", worm),
                       ("116703 (hatcher body, container-only)", body)):
        check(rebuild_container(data) == data,
              f"{name}: container re-emits byte-identically "
              f"({len(data):,} B)")

    for name, data, size, opq, pad in (
            ("shell", shell, SHELL_FA1, SHELL_OPAQUE, SHELL_PAD09),
            ("worm", worm, WORM_FA1, WORM_OPAQUE, WORM_PAD09)):
        sk = Skeleton.from_container(data)
        t = extract(sk)
        check(encode(t) == sk.payload and len(sk.payload) == size,
              f"{name}: FA1 rebuilt from typed values is byte-identical "
              f"({size:,} B)")
        carried = len(t["pad09"]) + sum(len(v) for v in t["opaque"].values())
        check(carried == opq,
              f"{name}: the repr carries exactly {opq} opaque bytes of "
              f"{size:,} ({opq / size:.1%}) -- the pin that catches a "
              f"writer regressing toward spans-concatenation",
              f"got {carried}")
        check(t["pad09"] == pad,
              f"{name}: header bytes +0x09..+0x0B are {pad.hex()} -- "
              "NOT zero; the parser never reads them and the typed layer "
              "carries them opaque (U6's measured finding)")

    # the order control on real bytes: worm n14/n34 both fire, contents
    # measured distinct, so the swap is non-vacuous
    sk = Skeleton.from_container(worm)
    check(sk.header["n14"] == 2 and sk.header["n34"] == 10
          and sk.block_bytes("n14")[:16] != sk.block_bytes("n34")[:16],
          "worm fires n14 AND n34 with distinct content -- the swap below "
          "is judged on a non-vacuous case")
    swapped = swap_n14_n34(sk.payload)
    r = walk(swapped)
    d = diff_offsets(sk.payload, swapped)
    check(r["ok"] and swapped != sk.payload
          and d and all(0x58 <= i < 0x58 + 32 + 240 for i in d),
          "worm: the block-swapped variant re-parses green, fails identity, "
          "diff confined to n14+n34 -- a wrong fixed-block order survives "
          "re-parse but not identity, which is why identity is the criterion")

    # the U7 seam on the worm, byte-diff predicted before serializing
    t = extract(sk)
    changed = scale_sequence_keytimes(t, SEAM_SEQ, 2)
    check(changed == [SEAM_KEY]
          and t["key_times"][SEAM_KEY] == SEAM_NEW,
          f"worm: scaling sequence {SEAM_SEQ} x2 changes exactly key "
          f"{SEAM_KEY} ({SEAM_OLD} -> {SEAM_NEW})")
    keys_off = dict((n, o) for n, o, s in sk.spans)["keys"]
    predicted = set(range(keys_off + 4 * SEAM_KEY, keys_off + 4 * SEAM_KEY + 4))
    mod = encode(t)
    d = set(diff_offsets(sk.payload, mod))
    check(d and d <= predicted,
          "worm: the modified FA1 differs from the source only at the "
          "predicted key-time bytes",
          f"diff {sorted(hex(i) for i in d)} predicted "
          f"{sorted(hex(i) for i in predicted)}")
    check(Skeleton.decode(mod).key_times_raw()[SEAM_KEY] == SEAM_NEW,
          "worm: re-decoding the modification yields the scaled time")
    modcont = rebuild_container(worm, fa1=mod)
    fa1_off = next(off for cid, off, _s in ffna_chunks(worm)
                   if cid == SKELETON_CHUNK)
    dc = set(diff_offsets(worm, modcont))
    check(len(modcont) == len(worm) and dc == {fa1_off + i for i in d},
          "worm: at container level the same modification lands at the "
          "same offsets shifted by the FA1 payload's position, and "
          "nowhere else")
    check(refuses(scale_sequence_keytimes, extract(sk), INEXACT_SEQ, 1,
                  INEXACT_DEN),
          f"worm: sequence {INEXACT_SEQ}'s 86666 / {INEXACT_DEN} is "
          "inexact and refused -- the seam never rounds a measurement")


def section2(check, ar, stride):
    print(f"\n== 2. corpus, stride {stride} ==")
    t0 = time.time()
    heads = [e.index for e in ar.entries if e.flags == HEAD_FLAGS]
    sample = heads[::stride]
    cont_n = cont_ok = fa1_n = fa1_ok = nonffna = 0
    n48_seen = pad_nonzero = 0
    fails = []
    for row in sample:
        data = bytes(ar.read(ar.row(row)))
        if data[:4] != b"ffna":
            nonffna += 1
            if stride == 1:
                check(row == ANOMALY_ROW,
                      "the single non-ffna head is the known row 8316",
                      f"row {row}")
            continue
        cont_n += 1
        try:
            if rebuild_container(data) == data:
                cont_ok += 1
            else:
                fails.append(("container", row))
        except Exception as e:                            # noqa: BLE001
            # guarded: a crash is a named FAIL below, never a dead run
            fails.append(("container-raise", row, repr(e)))
        fa1 = None
        for cid, off, size in ffna_chunks(data):
            if cid == SKELETON_CHUNK:
                fa1 = bytes(data[off:off + size])
                break
        if fa1 is None:
            continue
        fa1_n += 1
        try:
            t = extract(Skeleton.decode(fa1))
            if encode(t) == fa1:
                fa1_ok += 1
            else:
                fails.append(("fa1", row))
            if t["header"]["n48"]:
                n48_seen += 1
            if t["pad09"] != b"\x00\x00\x00":
                pad_nonzero += 1
        except Exception as e:                            # noqa: BLE001
            fails.append(("fa1-raise", row, repr(e)))
    print(f"  {len(sample)} rows -> {cont_n} containers, {fa1_n} FA1 "
          f"carriers, {nonffna} non-ffna; pad09 nonzero on "
          f"{pad_nonzero}/{fa1_n}; n48 fires on {n48_seen} "
          f"({time.time() - t0:.0f}s)")
    check(cont_n > 0 and fa1_n > 0,
          "the sample is non-empty -- identity over zero files would pass "
          "vacuously", f"{cont_n} containers, {fa1_n} FA1s")
    if stride == 1:
        check(cont_n == ALL_HEADS - 1 and fa1_n == ALL_FA1,
              f"full population: {ALL_HEADS - 1} containers, {ALL_FA1} FA1s",
              f"got {cont_n}, {fa1_n}")
    check(cont_ok == cont_n,
          f"container identity {cont_ok}/{cont_n}",
          f"failures: {fails[:5]}" if fails else "")
    check(fa1_ok == fa1_n,
          f"FA1 typed-repack identity {fa1_ok}/{fa1_n}",
          f"failures: {fails[:5]}" if fails else "")
    check(n48_seen > 0,
          f"blk48's typed repack was exercised on real data ({n48_seen} "
          "carriers in the sample) -- the deterministic stride makes this "
          "stable, and the synthetic covers the shape regardless")


# ---------------------------------------------------------------------------
# 3. the datwrite half: a rebuilt archive carrying the worm's real chain.
# ---------------------------------------------------------------------------

def build_rebuilt_archive(path, rows):
    """A loader-shaped mini archive from this file's own literals.

    `rows` is {row_index: (stored_bytes, compression, flags, next_stream)}.
    Layout: header b0, id table b1, chain rows from b2 (whole-block
    reservations, in index order), FREE_BLOCKS of zeros, MFT last.
    """
    import binascii
    offs, cur = {}, 2 * BLOCK
    for row in sorted(rows):
        offs[row] = cur
        cur += reservation(len(rows[row][0]))
    free_at = cur
    mft_off = cur + FREE_BLOCKS * BLOCK
    total = mft_off + reservation(ENTRY_COUNT * ENTRY_SIZE)
    buf = bytearray(total)

    idtable = struct.pack("<II", ANCHOR_WORM, ROW_ROOT)
    buf[BLOCK:BLOCK + len(idtable)] = idtable
    for row, (data, _c, _f, _n) in rows.items():
        buf[offs[row]:offs[row] + len(data)] = data

    head = bytearray(32)
    head[0:4] = b"3AN\x1a"
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, mft_off)
    struct.pack_into("<I", head, 0x18, ENTRY_COUNT * ENTRY_SIZE)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(ENTRY_COUNT * ENTRY_SIZE)
    mft[0:4] = b"Mft\x1a"
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    entries = {ROW_HEADER: (0, 32, 0, 3, 0, 0),
               ROW_IDTABLE: (BLOCK, len(idtable), 0, 3, 0,
                             binascii.crc32(idtable)),
               ROW_SELF: (mft_off, ENTRY_COUNT * ENTRY_SIZE, 0, 3, 0, 0)}
    for row, (data, comp, flags, nxt) in rows.items():
        entries[row] = (offs[row], len(data), comp, flags, nxt,
                        binascii.crc32(data))
    for row, e in entries.items():
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE, *e)
    acc = binascii.crc32(bytes(mft[:ROW_SELF * ENTRY_SIZE]))
    self_crc = binascii.crc32(bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:]), acc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + 0x14, self_crc)
    buf[mft_off:mft_off + len(mft)] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return free_at


def read_chain(raw):
    """Rows 16..18 out of the MFT, by int.from_bytes -- no archive.py."""
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    out = {}
    for row in (ROW_ROOT, ROW_MID, ROW_TAIL):
        b = raw[mft_off + row * ENTRY_SIZE:mft_off + (row + 1) * ENTRY_SIZE]
        out[row] = {"offset": int.from_bytes(b[0:8], "little"),
                    "size": int.from_bytes(b[8:12], "little"),
                    "comp": int.from_bytes(b[12:14], "little"),
                    "flags": int.from_bytes(b[14:16], "little"),
                    "next": int.from_bytes(b[16:20], "little")}
    return out


def chain_problems(rows):
    """Everything wrong with the 515 -> 1 -> 2817 chain, by name."""
    bad = []
    if rows[ROW_ROOT]["next"] != ROW_MID:
        bad.append(f"root.next {rows[ROW_ROOT]['next']} != {ROW_MID}")
    if rows[ROW_MID]["next"] != ROW_TAIL:
        bad.append(f"mid.next {rows[ROW_MID]['next']} != {ROW_TAIL}")
    if rows[ROW_TAIL]["next"] != 0:
        bad.append(f"tail.next {rows[ROW_TAIL]['next']} != 0")
    for row, want in zip((ROW_ROOT, ROW_MID, ROW_TAIL), CHAIN_FLAGS):
        if rows[row]["flags"] != want:
            bad.append(f"row {row} flags {rows[row]['flags']} != {want}")
    return bad


def section3(check, led, ar, idt):
    print("\n== 3. the datwrite half: the rebuilt archive round trip ==")
    root_e = ar.row(idt[ANCHOR_WORM])
    mid_e = ar.row(root_e.counter)
    tail_e = ar.row(mid_e.counter)
    check((root_e.flags, mid_e.flags, tail_e.flags) == CHAIN_FLAGS
          and tail_e.counter == 0,
          "the worm's rows in the STUDY archive are the recorded "
          "515 -> 1 -> 2817 nextStream chain, source of this rebuild")
    stored = {r: bytes(ar.raw(e)) for r, e in
              ((ROW_ROOT, root_e), (ROW_MID, mid_e), (ROW_TAIL, tail_e))}
    container = bytes(ar.read(root_e))
    check(len(container) == WORM_CONTAINER
          and len(stored[ROW_ROOT]) == WORM_STORED,
          f"measured sizes hold: container {WORM_CONTAINER:,} B from "
          f"{WORM_STORED:,} stored -- which CANNOT fit the row's "
          f"{reservation(WORM_STORED):,} B reservation uncompressed")

    outdir = os.path.join(skelwrite.resolve_outdir(None), "unitwrite")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "rebuilt_worm.dat")
    build_rebuilt_archive(path, {
        ROW_ROOT: (stored[ROW_ROOT], root_e.compression, root_e.flags,
                   ROW_MID),
        ROW_MID: (stored[ROW_MID], mid_e.compression, mid_e.flags, ROW_TAIL),
        ROW_TAIL: (stored[ROW_TAIL], tail_e.compression, tail_e.flags, 0),
    })
    with quiet():
        pre_bad = datwrite.verify(path) + datwrite.check_rows(
            path, [ROW_ROOT, ROW_MID, ROW_TAIL])
    check(pre_bad == 0, "the rebuilt archive verifies all three checksum "
                        "rules before any write")
    with Archive(path) as reb:
        check(bytes(reb.read(reb.row(ROW_ROOT))) == container,
              "the rebuilt archive's root row decompresses to the source "
              "container -- the rebuild carried the compressed row "
              "faithfully")

    rebuilt = rebuild_container(container)
    check(rebuilt == container,
          "the payload being written is the WRITER'S output, byte-identical "
          "to the source container (identity level: serialized bytes)")

    # THE RECORDED WALL, exhibited: --replace writes uncompressed and will
    # not move a row (studies/datwrite FINDINGS 38; datmove's docstring).
    try:
        w = datwrite.Writer(path, path + ".wall.journal.json")
        try:
            w.replace(ROW_ROOT, rebuilt)
            check(False, "datwrite.replace refuses the relocation")
        except SystemExit as e:
            check("relocation" in str(e),
                  "datwrite.replace refuses, naming the relocation -- the "
                  "recorded wall, exhibited beside the verb that succeeds",
                  str(e).splitlines()[0])
        finally:
            w.close()
    except SystemExit as e:
        check(False, "datwrite.replace refuses the relocation",
              f"Writer itself refused: {e}")

    journal = path + ".move.journal.json"
    try:
        with quiet():
            datmove.move(path, ROW_ROOT, rebuilt, journal, confirm=True)
        check(True, "datmove relocates the root row (the established verb "
                    "for a payload its reservation cannot hold)")
    except (datmove.Refused, SystemExit) as e:
        check(False, "datmove relocates the root row", repr(e))
        led.skip("post-move checks", "the move itself failed")
        return

    raw = open(path, "rb").read()
    rows = read_chain(raw)
    with Archive(path) as reb:
        got = bytes(reb.read(reb.row(ROW_ROOT)))
    check(got == container,
          "the row read back out of the rebuilt archive equals the source "
          "container (identity level: decompressed row payload, EXACT)")
    check(rows[ROW_ROOT]["comp"] == 0
          and rows[ROW_ROOT]["size"] == WORM_CONTAINER != WORM_STORED,
          "the STORED form legitimately differs: compression 8 x "
          f"{WORM_STORED:,} B became stored x {WORM_CONTAINER:,} B -- "
          "datwrite writes uncompressed and no compression-8 encoder "
          "exists (identity level: stored bytes, NOT claimed)")
    check(chain_problems(rows) == [],
          "the nextStream chain survives the move intact: root(515) -> "
          "mid(1) -> tail(2817) -> 0, flags preserved",
          "; ".join(chain_problems(rows)))
    check(raw[rows[ROW_MID]["offset"]:
              rows[ROW_MID]["offset"] + rows[ROW_MID]["size"]]
          == stored[ROW_MID]
          and raw[rows[ROW_TAIL]["offset"]:
                  rows[ROW_TAIL]["offset"] + rows[ROW_TAIL]["size"]]
          == stored[ROW_TAIL],
          "the mid and tail rows -- U7's prime suspects if the client "
          "rejects -- are byte-identical after the move")
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    idt_off = int.from_bytes(raw[mft_off + ROW_IDTABLE * ENTRY_SIZE:
                                 mft_off + ROW_IDTABLE * ENTRY_SIZE + 8],
                             "little")
    check(raw[idt_off:idt_off + 8] == struct.pack("<II", ANCHOR_WORM,
                                                  ROW_ROOT),
          "the file-id table still names the same row -- a move changes an "
          "offset, never an identity")
    with quiet():
        post_bad = datwrite.verify(path) + datwrite.check_rows(
            path, [ROW_ROOT, ROW_MID, ROW_TAIL])
    with Archive(path) as reb:
        overlaps = datmove.overlaps(reb)
    check(post_bad == 0 and overlaps == [],
          "all three checksum rules hold after the move and no two "
          "reservations intersect")

    # the checker's own failing control: a corrupted chain must be reported
    bad = copy.deepcopy(rows)
    bad[ROW_ROOT]["next"] = 9
    check(chain_problems(bad) != [],
          "CONTROL: the chain checker reports a corrupted nextStream -- a "
          "'0 problems' that has never reported one is not a check")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="identity over the complete flags=515 population "
                         "(slow, ~25-45 min)")
    args = ap.parse_args()

    # FLOOR: 66, MEASURED from the green default run of 2026-08-16 (stride
    # 89, the study archive). --all runs 68: section 2 adds its two
    # stride-1-only pins (the row-8316 anomaly check and the exact
    # 21,420/14,571 population counts). Vault-less runs execute sections
    # 0/0b/0c only -- MEASURED 32 checks, RED on the floor by design;
    # --no-vault does not exist, the shortfall IS the report.
    led = checks.Ledger("skeleton writer (U6)", floor=66)
    check = checks.adopt(led)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        section0(check)
        section0b(check)
        section_outdir(check, tmp)

        try:
            dat = os.path.join(
                vaultpath.require_dir("dat_study",
                                      why="the U6 identity corpus"),
                "Gw.dat")
        except (Exception, SystemExit) as e:              # noqa: BLE001
            # require_dir raises SystemExit, which `except Exception` does
            # not catch -- the first vault-less run of this file died with
            # no verdict banner, the exact unguarded-exception failure the
            # models-arc review named. The shortfall below IS the report.
            led.skip("sections 1-3", f"no study archive: {e}")
            sys.exit(led.verdict())

        with Archive(dat) as ar:
            idt = file_id_table(ar)
            section1(check, ar, idt)
            section2(check, ar, stride=1 if args.all else STRIDE)
            section3(check, led, ar, idt)

    sys.exit(led.verdict())


if __name__ == "__main__":
    main()
