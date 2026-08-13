r"""Check the Sound codec: decode a retail `0x10000012`, encode it back.

THE HEADLINE IS 349 OF 349 BYTE-IDENTICAL, and on its own it proves little: the
record is a fixed 24 bytes, so a codec that kept each record's raw slice would
round-trip every file and understand nothing. The count `k` is the one thing the
codec must re-derive rather than replay, so section 2 BUILDS the saboteur that
stashes `k` and replays it, runs it, and requires it to pass the round trip while
FAILING the mutation control that appends an emitter and demands the emitted
`k`@14 and the payload length move with it -- read back by a walker written here
out of `int.from_bytes`, importing nothing from the module under test.

THE ORACLE COMES FROM A CHUNK THIS CODEC NEVER READS. Every emitter's `(x, y)`
must land inside the map rect, which lives in Map Parameters `0x1000000C`. If the
record layout were off by any amount the coordinates would be garbage. Section 4
measures it against the archive; a shifted read is the control that must collapse.

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-2 run without an archive,
but a run with no vault has measured nothing about ArenaNet's format, and the
floor turns that into the FAIL it is.

    python toolkit/mapdata/test_soundchunk.py
    python toolkit/mapdata/test_soundchunk.py --sample 40
    python toolkit/mapdata/test_soundchunk.py --all      # all 349 maps
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
from mapchunks import MapIndex  # noqa: E402
import mapbuild  # noqa: E402
import mapfile as mfile  # noqa: E402
import soundchunk as snd  # noqa: E402
from soundchunk import (SoundChunk, Emitter, Undecodable,  # noqa: E402
                        SIGNATURE, VERSION, TERMINATOR, NONE,
                        HEADER_SIZE, RECORD_SIZE)
import checks  # noqa: E402
import vaultpath  # noqa: E402

SOUND_CHUNK = 0x10000012
MAP_PARAMS_CHUNK = 0x1000000C

# MEASURED 2026-08-13 over vault/dat_study/Gw.dat, all 349 maps. Population
# assertions, not decoration: they stop an empty sample or a bad row filter from
# printing "8 of 8" green.
CORPUS_MAPS = 349
CORPUS_EMITTERS = 318           # records across the 101 record-carrying maps
CORPUS_MAX_K = 16
CORPUS_EMPTY = 20               # maps whose (idx_a, idx_b) == (NONE, NONE)
CORPUS_IN_RECT = 318            # emitters landing inside their own map rect

# FLOOR: 21, MEASURED from a green default run 2026-08-13 (which executes 23; a
# --all run executes 27, adding three corpus-total checks). Sections 0-2 score 18
# and need no vault, so a vault-less run stops at 18 and the floor turns that into
# the FAIL it is -- it has checked the codec against chunks this file wrote and
# nothing about ArenaNet's bytes. The floor sits above 18 to force the vault and
# below the 23 a sampled run produces.
LEDGER = checks.Ledger("test_soundchunk", floor=21)
check = checks.adopt(LEDGER)


def refuses(blob, why):
    try:
        SoundChunk.decode(blob)
        return False
    except Undecodable:
        return True
    except Exception:  # noqa: BLE001
        return False


class Sabotage(SoundChunk):
    """A codec that STORES k and replays it -- the memcpy this file must catch.

    It round-trips every real file (k always matches the record list on a decoded
    chunk) and only diverges when the record list is mutated without touching the
    stashed count, which is exactly the mutation control below.
    """

    __slots__ = ("_stored_k",)

    @classmethod
    def decode(cls, blob):
        base = SoundChunk.decode(blob)
        obj = cls(base.version, base.idx_a, base.idx_b, base.emitters)
        obj._stored_k = struct.unpack_from("<H", blob, 14)[0]
        return obj

    def encode(self):
        out = bytearray(struct.pack("<IIBHHBH", SIGNATURE, self.version, 0,
                                    self.idx_a, self.idx_b, 1, self._stored_k))
        for e in self.emitters:
            out += e.pack()
        out.append(TERMINATOR)
        return bytes(out)


def walk_k(blob):
    """The declared record count, read independently of the module."""
    return int.from_bytes(blob[14:16], "little")


def section0():
    """Refusals: the framer must reject what it does not understand."""
    print("\n-- 0. refusals --")
    good = snd.empty().encode()
    check(SoundChunk.decode(good).emitters == [], "empty chunk decodes")
    check(refuses(b"\x00\x01\x02\x03" + good[4:], "bad signature"),
          "bad signature refused")
    check(refuses(good[:-1], "no terminator / short"),
          "truncated chunk refused")
    # a size that disagrees with the declared k
    bad = bytearray(good)
    bad[14] = 5                 # claims 5 records, but the bytes hold none
    check(refuses(bytes(bad), "k disagrees with length"),
          "declared-k vs length mismatch refused")
    # wrong interior tag byte
    bad = bytearray(good)
    bad[8] = 9
    check(refuses(bytes(bad), "wrong tag0"), "wrong interior tag refused")


def section1():
    """Build from nothing, round-trip, and read the fields back."""
    print("\n-- 1. authored round trip --")
    e0 = Emitter(dep_a=2, dep_b=NONE, x=100, y=-250, r_lo=300, r_hi=1200,
                 r_mid=700)
    e1 = Emitter(dep_a=0, dep_b=1, x=-40, y=60, r_lo=50, r_hi=99, r_mid=75)
    sc = SoundChunk(VERSION, idx_a=0, idx_b=1, emitters=[e0, e1])
    blob = sc.encode()
    check(len(blob) == HEADER_SIZE + 2 * RECORD_SIZE + 1,
          "authored size is 17 + 24*2", f"{len(blob)} B")
    back = SoundChunk.decode(blob)
    check(back.encode() == blob, "authored chunk round-trips")
    check(back.emitters[0].x == 100 and back.emitters[0].y == -250,
          "emitter position read back")
    check(back.emitters[0].r_lo == 300 and back.emitters[0].r_hi == 1200
          and back.emitters[0].r_mid == 700, "emitter radii read back")
    check(walk_k(blob) == 2, "independent walker reads k == 2")
    check(snd.empty().encode() == bytes.fromhex(
        "646e736d0200000000ffffffff010000ff"),
        "empty() matches the 20 retail silent chunks byte-for-byte")


def section2():
    """The memcpy saboteur and the mutation control that catches it."""
    print("\n-- 2. saboteur vs mutation control --")
    sc = SoundChunk(VERSION, 0, 1, [
        Emitter(2, NONE, 10, 20, 100, 400, 250),
        Emitter(3, NONE, -30, 40, 50, 200, 120)])
    blob = sc.encode()

    sab = Sabotage.decode(blob)
    check(sab.encode() == blob, "saboteur passes the round trip (as designed)")

    # grow both codecs by one emitter; the real one must move k, the saboteur not
    grow = SoundChunk.decode(blob)
    grow.emitters.append(Emitter(4, NONE, 0, 0, 10, 20, 15))
    real = grow.encode()
    check(len(real) == len(blob) + RECORD_SIZE, "real codec grows by 24 B")
    check(walk_k(real) == 3, "real codec re-derives k == 3")

    sab_grow = Sabotage.decode(blob)
    sab_grow.emitters.append(Emitter(4, NONE, 0, 0, 10, 20, 15))
    sab_out = sab_grow.encode()
    check(walk_k(sab_out) == 2,
          "saboteur replays the stale k == 2 -- the bug the control exposes")
    check(walk_k(real) != walk_k(sab_out),
          "the mutation control SEPARATES the real codec from the memcpy")

    # mutate one field: exactly the field's bytes move, terminator stays
    mut = SoundChunk.decode(blob)
    mut.emitters[0].x = 0x1234
    mut_out = mut.encode()
    diffs = [i for i in range(len(blob)) if blob[i] != mut_out[i]]
    check(diffs == [HEADER_SIZE + 4, HEADER_SIZE + 5],
          "changing emitter[0].x moves exactly its 2 low bytes",
          f"diffs={diffs}")
    check(mut_out[-1] == TERMINATOR, "terminator intact after mutation")


def read_corpus(ar, mi, picks):
    out = []
    for head in picks:
        m = mfile.MapFile.decode(ar.read(mi.partner(head)), strict=False)
        rect = mapbuild.decode_map_parameters(
            m.find(MAP_PARAMS_CHUNK).payload())[0]
        out.append((mi.partner(head).index, m.find(SOUND_CHUNK).payload(), rect))
    return out


def section3(corpus):
    """The sweep: byte-identity plus the population it was measured over."""
    print(f"\n-- 3. {len(corpus)} retail maps: decode, re-encode, compare --")
    same = diff = 0
    n_emit = n_empty = 0
    max_k = 0
    versions = set()
    for _row, blob, _rect in corpus:
        sc = SoundChunk.decode(blob)
        if sc.encode() == blob:
            same += 1
        else:
            diff += 1
        versions.add(sc.version)
        n_emit += len(sc.emitters)
        max_k = max(max_k, len(sc.emitters))
        if sc.idx_a == NONE and sc.idx_b == NONE:
            n_empty += 1
    check(diff == 0, f"{same} of {len(corpus)} re-encode byte-identically",
          f"{diff} differ")
    check(versions == {VERSION}, "every version is 2", f"{sorted(versions)}")
    complete = len(corpus) == CORPUS_MAPS
    if complete:
        check(n_emit == CORPUS_EMITTERS,
              f"corpus emitter total == {CORPUS_EMITTERS}", f"{n_emit}")
        check(max_k == CORPUS_MAX_K, f"max k == {CORPUS_MAX_K}", f"{max_k}")
        check(n_empty == CORPUS_EMPTY,
              f"{CORPUS_EMPTY} maps carry the silent chunk", f"{n_empty}")
    else:
        LEDGER.skip("corpus population totals",
                    f"sample of {len(corpus)} < {CORPUS_MAPS}; run --all")
    return complete


def section4(corpus, complete):
    """The oracle: emitter (x, y) lands in the map rect, and a shift breaks it."""
    print("\n-- 4. cross-chunk oracle: emitters inside the Map Parameters rect --")
    in_rect = shifted_in = total = 0
    ordered = 0
    for _row, blob, rect in corpus:
        x0, y0, x1, y1 = rect
        for e in SoundChunk.decode(blob).emitters:
            total += 1
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                in_rect += 1
            # the control: read x from one byte later -- must miss
            sx = struct.unpack_from("<i", e.pack(), 5)[0]
            if x0 <= sx <= x1:
                shifted_in += 1
            if e.r_lo <= e.r_mid <= e.r_hi:
                ordered += 1
    if total == 0:
        LEDGER.skip("emitter oracle", "no emitters in this sample")
        return
    check(in_rect == total,
          f"{in_rect} of {total} emitters land inside their map rect")
    check(shifted_in < in_rect,
          "a 1-byte-shifted read of x lands in-rect far less often "
          "-- the layout is measured, not chosen",
          f"shifted {shifted_in} vs aligned {in_rect}")
    check(ordered == total,
          f"{ordered} of {total} emitters satisfy r_lo <= r_mid <= r_hi "
          "(the client's own load-time invariant)")
    if complete:
        check(in_rect == CORPUS_IN_RECT,
              f"whole-corpus in-rect count == {CORPUS_IN_RECT}", f"{in_rect}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    section0()
    section1()
    section2()

    try:
        dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except SystemExit:
        LEDGER.skip("corpus sweep + oracle",
                    "no vault/dat_study/Gw.dat; the floor turns this into a FAIL")
        return LEDGER.verdict()

    with Archive(dat) as ar:
        mi = MapIndex(ar)
        heads = [h for h, _p in mi.pairs]
        picks = heads if args.all else heads[::max(1, len(heads) // args.sample)]
        corpus = read_corpus(ar, mi, picks)
    complete = section3(corpus)
    section4(corpus, complete)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
