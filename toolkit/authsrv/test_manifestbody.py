"""test_manifestbody.py -- divergence D13.4: the manifest body's layout, the hash its
DONE carries, and the client's cache record that decides which maps a session asks for.

Section 1 is bare-machine: hand-built bodies with every escape form at its boundary, the
CRC variant pinned by its standard check value, a synthetic cache record and its four
refusals, the bracket bookkeeping and its three client asserts, the request prediction
and the kind-0 rule, and the 38974 numbering trap (the same bytes read through the wrong
build's codec must NOT rebuild the same reply). Sections 2-4 read the vault at run time
and commit nothing out of it -- no decoded list, no hash table, no stamp or mask:

  2  every DONE on every live tape: both phase buffers close to the exact byte with the
     count word == ids decoded, re-encode byte for byte, and every kind-3 dword is
     manifest_hash(p0, p1) -- counted PER ARM so a vacuous arm fails; KNOWN-BAD: one
     flipped body bit reddens the hash, a buffer one byte short reddens the layout.
  3  file id 5 in every vault/client snapshot parses with its build's map count
     (authsrv.MAP_ID_COUNT_BY_BUILD, keyed by buildid.of_image of the snapshot's own
     Gw.exe) and a stamp that is a FILETIME before the snapshot; KNOWN-BAD: the record
     read with the wrong build's count is refused.
  4  the join: every chain connection's s2c, read in WIRE order, closes each manifest
     bracket (KNOWN-BAD: re-sorted by segment clock, one does not); 20260913T210901's
     0x0093 set is EXACTLY the maps whose 0x019F hash differs from the snapshot's table
     (5 of 142), and carried forward over every capture on that run directory the
     prediction is exact on every connection; KNOWN-BAD: an all-zero table, the chain
     without the kind-0 write, and the chain writing EVERY kind-0.

Each vault section SKIPS, printed, when the vault directory it reads is absent; a
present directory that will not load is a failure, never a skip.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import checks  # noqa: E402
import manifestbody as mb  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR: two shapes, test_bit31's arrangement, both from green runs on 2026-10-07 with
# zero headroom. FLOOR_BARE is section 1 alone, measured with RURIK_VAULT pointed at an
# empty directory (23, three declared skips); FLOOR_VAULT is the vaulted total (45:
# section 2 has 10, section 3 has 4, section 4 has 8 -- the wire-order bracket check and
# its segment-clock KNOWN-BAD arm joined it after review RV-2), raised in main() once all
# three vault sections ran, so no vaulted check is slack.
FLOOR_BARE = 23
FLOOR_VAULT = 45
LEDGER = checks.Ledger("manifest body, hash and cache (divergence D13.4)", floor=FLOOR_BARE)
check = LEDGER.ok


def raises(fn, *args, **kw):
    try:
        fn(*args, **kw)
    except mb.ManifestError:
        return True
    return False


def ffna(type_byte, chunks):
    out = bytearray(b"ffna" + bytes([type_byte]))
    for cid, payload in chunks:
        out += struct.pack("<II", cid, len(payload)) + payload
    return bytes(out)


def record(count, stamp=0x01DC000000000000, mask=None, table=None, type_byte=4,
           mask_len=None, table_len=None):
    mask = mask if mask is not None else bytes(mb.mask_bytes(count) if mask_len is None else mask_len)
    table = table if table is not None else bytes(4 * count if table_len is None else table_len)
    return ffna(type_byte, [(0, struct.pack("<QI", stamp, count)), (1, mask), (2, table)])


# ---------------------------------------------------------------- 1: bare ----------

def section_bare():
    print("1. the layout, the hash, the record and the bookkeeping -- known answers")
    # Every gap form at both edges of its range: 1 and 254 by byte, 255 and 65790 by
    # word escape, 65791 by dword escape. The bytes are written out by hand.
    ids = [100, 101, 355, 610, 610 + 65790, 610 + 65790 + 65791]
    want = (struct.pack("<HI", 6, 100) + bytes([0x00, 0xFD])
            + b"\xfe" + struct.pack("<H", 0) + b"\xfe" + struct.pack("<H", 0xFFFF)
            + b"\xff" + struct.pack("<I", 65791))
    check(mb.encode_list(ids) == want,
          "encode_list writes each gap in the narrowest form: 1/254 by byte, 255/65790 "
          "by 0xFE+word, 65791 by 0xFF+dword", f"got {mb.encode_list(ids).hex()}")
    check(mb.decode_list(want) == (6, ids),
          "decode_list reads the hand-built buffer back: count 6, the six ids")
    # A buffer one byte short: an escape that runs off the end is the client's assert.
    check(raises(mb.decode_list, want[:-1]),
          "a dword escape one byte short raises (MsCliMan:107's assert)")
    check(raises(mb.decode_list, want[:6] + b"\xfe\x00"),
          "a word escape one byte short raises (MsCliMan:101's assert)")
    # ...and one whose last delta is a plain byte still DECODES -- to one id fewer than
    # its count word, which is why section 2 holds the count against the ids.
    short = mb.encode_list([5, 6, 7])[:-1]
    check(mb.decode_list(short) == (3, [5, 6]),
          "a byte-delta buffer one byte short decodes to count 3 but 2 ids -- the loop "
          "ends on the buffer, so count == ids is a check the bytes can fail")
    # The other direction, and the one that tells "ends on the buffer" from "ends on the
    # count": a byte PAST the count is read as one more id, as 0x00851A60 reads it.
    check(mb.decode_list(mb.encode_list([5, 6]) + b"\x00") == (2, [5, 6, 7]),
          "a byte past the count is read as one more id (count 2, 3 ids) -- the client's "
          "loop stops on the buffer, never on the count word")
    check(mb.decode_list(b"") == (0, []) and mb.decode_list(b"\x00\x00\xff") == (0, [])
          and mb.encode_list([]) == b"",
          "an empty buffer and a zero count are no list (the parser returns), and back")
    check(raises(mb.encode_list, [5, 5]) and raises(mb.encode_list, [6, 5]),
          "encode_list refuses ids that are not strictly ascending")
    # The CRC variant: zlib's CRC-32 (ISO-HDLC), pinned by its published check value.
    check(mb.crc32(b"123456789") == 0xCBF43926 and mb.crc32(b"") == 0,
          "crc32 is CRC-32/ISO-HDLC (check value 0xCBF43926) and crc32(b'') is 0")
    p1, p0 = b"\x01\x00\x07\x00\x00\x00", b"\x02\x00\x09\x00\x00\x00\x03"
    check(mb.manifest_hash(b"", p1) == zlib.crc32(p1)
          and mb.manifest_hash(p0, p1) == zlib.crc32(p1) ^ ((zlib.crc32(p0) << 1) & 0xFFFFFFFF),
          "manifest_hash: crc32(P1) with no phase-0 body, crc32(P1) ^ (crc32(P0) << 1) with one")
    hi = next(bytes([i]) for i in range(256) if zlib.crc32(bytes([i])) >> 31)
    rotl = ((zlib.crc32(hi) << 1) | (zlib.crc32(hi) >> 31)) & 0xFFFFFFFF
    check(mb.manifest_hash(hi, p1) != zlib.crc32(p1) ^ rotl,
          "and it SHIFTS, it does not rotate: a phase-0 body whose crc has bit 31 set "
          "tells the two apart")
    # The record.
    rec = mb.parse_cache(record(888, table=struct.pack("<888I", *range(888))), missions=888)
    check(rec.count == 888 and len(rec.mask) == 112 and rec.table[887] == 887
          and rec.stamp == 0x01DC000000000000,
          "parse_cache reads a 38797-shaped record: 888 maps, a 112-byte mask, the table, the stamp")
    check(mb.mask_bytes(888) == 112 and mb.mask_bytes(897) == 116 and mb.mask_bytes(898) == 116
          and mb.mask_bytes(883) == 112,
          "mask_bytes: 112 for 883/888, 116 for 897/898 (the 0x0092 row's widths)")
    check(raises(mb.parse_cache, record(888), missions=897),
          "a record counting another build's maps is refused (the loader does not take it)")
    check(raises(mb.parse_cache, record(888, type_byte=3))
          and raises(mb.parse_cache, record(888, mask_len=116))
          and raises(mb.parse_cache, record(888, table_len=4 * 887)),
          "and so is the wrong FFNA type, a mask of the wrong width, a table of the wrong length")
    check(mb.STALE_AFTER == 24 * 3600 * 10 ** 7 and mb.is_stale(0, mb.STALE_AFTER + 1)
          and not mb.is_stale(0, mb.STALE_AFTER),
          "0xC92A69C000 FILETIME ticks is 24 h exactly; strictly older is stale")
    # The bracket bookkeeping, through the codec's own numbering.
    from codec import Codec
    codec = Codec()
    ops = mb.opcodes(codec)
    P, B, D = ops["phase"], ops["body"], ops["done"]
    msgs = [(0, P, [P, 0]), (0, B, [B, b"ab"]), (0, B, [B, b"cd"]), (0, P, [P, 1]),
            (0, B, [B, b"ef"]), (0, 0x1E, [0x1E, 1]), (0, D, [D, 3, 7, 9]),
            (0, P, [P, 1]), (0, B, [B, b"gh"]), (0, D, [D, 2, 888, 0])]
    got = mb.rebuild(msgs, ops)
    check([(d.kind, d.map, d.dword, d.p0, d.p1) for d in got]
          == [(3, 7, 9, b"abcd", b"ef"), (2, 888, 0, b"", b"gh")],
          "rebuild: chunks concatenate per phase, DONE closes and frees BOTH buffers, "
          "an unbracketed phase is b''")
    check(raises(mb.rebuild, [(0, B, [B, b"x"])], ops)
          and raises(mb.rebuild, [(0, P, [P, 2])], ops)
          and raises(mb.rebuild, [(0, D, [D, 4, 1, 0])], ops),
          "rebuild refuses a body outside a bracket (MsCliMan:457), phase 2 (:472), kind 4 (:487)")
    # The prediction and the update rules.
    table = [0] * 10
    table[3] = 0xAA
    check(mb.predicted_requests(table, [(3, 0xAA), (4, 0xBB), (5, 0)]) == {4}
          and mb.predicted_requests(table, {3: 0xAB}) == {3},
          "predicted_requests: a map is queued exactly when the named hash differs from the table")
    # Every entry is SEEDED non-zero first: a zero written over a zero entry is invisible,
    # and that is how this check once stayed green with kind 0 writing its zero dwords
    # (review RV-1) -- the one rule D13.4.3's 17 of 17 rests on, unguarded off the vault.
    table[6], table[7], table[8], table[9] = 0xEE, 0xEF, 0xF0, 0xF1
    mb.apply_done(table, 0, 6, 0)
    mb.apply_done(table, 2, 7, 5)
    mb.apply_done(table, 0, 8, 0xCC)
    mb.apply_done(table, 3, 9, 0xDD)
    check(table[6] == 0xEE and table[7] == 0xEF and table[8] == 0xCC and table[9] == 0xDD,
          "apply_done: kind 3 writes, kind 0 writes only a non-zero dword (a zero one leaves "
          "the entry alone), kind 2 never",
          f"got {[hex(x) for x in table[6:10]]}")
    # THE NUMBERING TRAP. 38974 moved every GAME_SMSG from 0x0194 up by one, so the
    # manifest family's wire opcodes differ by build; a tape carries its build and the
    # reply must rebuild from the bytes only through THAT build's codec.
    import tape
    c38974 = codec.for_build(38974)
    body = mb.encode_list([4, 9, 300])
    wire = (c38974.encode("GAME_SMSG", P, [1]) + c38974.encode("GAME_SMSG", B, [body])
            + c38974.encode("GAME_SMSG", D, [3, 242, mb.manifest_hash(b"", body)]))
    check(c38974.wire_opcode("GAME_SMSG", B) == B + 1,
          "38974 puts INSTANCE_MANIFEST_BODY on the wire one above the schema's opcode")
    ev = tape.Events([(0.0, wire)])
    ev.build = 38974
    msgs, _r = tape.decode_all(ev, codec, "GAME_SMSG", 0)
    got = mb.rebuild(msgs, ops)
    check(len(got) == 1 and got[0][1:] == (3, 242, mb.manifest_hash(b"", body), b"", body),
          "a 38974 stream rebuilds through the tape's own build: one reply, its body, its hash")
    try:
        wrong = mb.rebuild(tape.decode_all([(0.0, wire)], codec, "GAME_SMSG", 0)[0], ops)
    except Exception:      # noqa: BLE001 -- any refusal at all is the expected outcome
        wrong = None
    check(wrong is None or [d[1:] for d in wrong] != [d[1:] for d in got],
          "KNOWN-BAD: the same bytes read in the schema's numbering do NOT rebuild that reply")


# ---------------------------------------------------------------- 2: corpus --------

def section_corpus():
    print("\n2. every DONE on every live tape")
    live = vaultpath.vault_path("captures", "live")
    if not os.path.isdir(live):
        LEDGER.skip("2. the live corpus", f"no live-capture directory at {live}")
        return False
    import capgaps
    import tape
    set_aside = []
    replies = list(mb.corpus_replies(set_aside, root=live))
    capdirs = [os.path.join(live, s) for s in sorted(os.listdir(live))
               if os.path.isdir(os.path.join(live, s))]
    ok, detail = capgaps.audit(set_aside, capdirs, tape.refuses)
    check(ok, "the only connection stepped past is the one its manifest declares gapped "
              "(capgaps.KNOWN_GAPPED), and it still refuses", detail)
    by_kind = {k: [r for r in replies if r.kind == k] for k in (0, 2, 3)}
    # Floors per kind from the 2026-10-07 corpus: a walk that quietly loses tapes reds.
    check(len(by_kind[3]) >= 219 and len(by_kind[0]) >= 121 and len(by_kind[2]) >= 121
          and len(replies) == sum(len(v) for v in by_kind.values()),
          "219+ kind-3 replies, 121+ kind-0 and 121+ kind-2 DONEs, and no other kind",
          f"got {[(k, len(v)) for k, v in by_kind.items()]} of {len(replies)}")
    bufs = [b for r in replies for b in (r.p0, r.p1) if b]
    closed, mismatched = 0, []
    for b in bufs:
        count, ids = mb.decode_list(b)
        if count == len(ids) and all(x < y for x, y in zip(ids, ids[1:])):
            closed += 1
        else:
            mismatched.append((count, len(ids)))
    check(len(bufs) >= 646 and closed == len(bufs),
          f"(a) every phase buffer of every DONE closes to the exact byte with its count "
          f"word == the ids decoded, strictly ascending: {closed} of {len(bufs)}",
          f"first mismatches {mismatched[:3]}")
    rt = sum(mb.encode_list(mb.decode_list(b)[1]) == b for b in bufs)
    check(rt == len(bufs), f"(b) encode(decode(b)) == b on {rt} of {len(bufs)} buffers")
    single = [r for r in by_kind[3] if not r.p0]
    double = [r for r in by_kind[3] if r.p0]
    s_ok = sum(mb.manifest_hash(r.p0, r.p1) == r.dword for r in single)
    d_ok = sum(mb.manifest_hash(r.p0, r.p1) == r.dword for r in double)
    check(len(single) >= 193 and s_ok == len(single),
          f"(c) the CORE: crc32(P1) is the dword on {s_ok} of {len(single)} replies with no "
          f"phase-0 body")
    check(len(double) >= 26 and d_ok == len(double) and len({r.p0 for r in double}) >= 4,
          f"(c) the FIT: crc32(P1) ^ (crc32(P0) << 1) on {d_ok} of {len(double)} replies "
          f"carrying one of {len({r.p0 for r in double})} phase-0 bodies")
    concat = sum(mb.crc32(r.p0 + r.p1) == r.dword or mb.crc32(r.p1) == r.dword for r in double)
    top = [r for r in double if mb.crc32(r.p0) >> 31]
    rot = sum(mb.crc32(r.p1) ^ (((mb.crc32(r.p0) << 1) | (mb.crc32(r.p0) >> 31)) & 0xFFFFFFFF)
              == r.dword for r in top)
    check(concat == 0 and top and rot == 0,
          f"CONTROLS: crc32(P0+P1) or crc32(P1) alone fits {concat} two-body replies; a "
          f"rotate fits {rot} of the {len(top)} whose crc32(P0) has bit 31 set")
    flipped = 0
    for r in by_kind[3]:
        p1 = bytearray(r.p1)
        p1[len(p1) // 2] ^= 0x10
        flipped += mb.manifest_hash(r.p0, bytes(p1)) != r.dword
    check(flipped == len(by_kind[3]),
          f"KNOWN-BAD (c): one flipped body bit breaks the hash on {flipped} of "
          f"{len(by_kind[3])} replies")
    short_red = 0
    for b in bufs:
        try:
            count, ids = mb.decode_list(b[:-1])
            short_red += count != len(ids)
        except mb.ManifestError:
            short_red += 1
    check(short_red == len(bufs),
          f"KNOWN-BAD (a): every buffer one byte short fails the layout check "
          f"({short_red} of {len(bufs)})")
    check(all(r.dword == 0 for r in by_kind[2]),
          f"the list-open (kind 2) carries no hash on all {len(by_kind[2])}")
    return True


# ---------------------------------------------------------------- 3: the record ----

def section_cache():
    print("\n3. file id 5 in every vault/client snapshot")
    root = vaultpath.vault_path("client")
    if not os.path.isdir(root):
        LEDGER.skip("3. the cache records", f"no client-snapshot directory at {root}")
        return False
    import datetime
    import json
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid
    import authsrv
    epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
    snaps = sorted(s for s in os.listdir(root) if os.path.isfile(os.path.join(root, s, "Gw.dat")))
    rows = []
    for s in snaps:
        build, _why = buildid.of_image(os.path.join(root, s, "Gw.exe"))
        missions = authsrv.MAP_ID_COUNT_BY_BUILD.get(build)
        rec = mb.read_cache(os.path.join(root, s, "Gw.dat"), missions=missions)
        with open(os.path.join(root, s, "MANIFEST.json"), encoding="utf-8") as fh:
            taken = datetime.datetime.strptime(json.load(fh)["snapshot_utc"],
                                               "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        stamped = epoch + datetime.timedelta(microseconds=rec.stamp // 10)
        rows.append((s, build, missions, rec, stamped <= taken
                     and taken - stamped < datetime.timedelta(days=400)))
    check(len(rows) >= 6 and all(r[2] is not None and r[3].count == r[2] for r in rows),
          f"(d) every snapshot's record parses (type 4; 12 / mask / 4 x count) with its OWN "
          f"build's map count: {[(r[1], r[3].count) for r in rows]}")
    check({r[3].count for r in rows} >= {883, 888, 897, 898},
          "four generations of the record are on disk: 883, 888, 897 and 898 maps")
    check(all(r[4] for r in rows),
          "chunk 0's first u64 is a FILETIME: every stamp lands in the 400 days before its "
          "snapshot was taken")
    s, build, missions, rec, _ = rows[-1]
    check(raises(mb.read_cache, os.path.join(root, s, "Gw.dat"), missions=missions + 1),
          f"KNOWN-BAD: {s}'s record read as a build with {missions + 1} maps is refused")
    return True


# ---------------------------------------------------------------- 4: the join ------

def section_join():
    print("\n4. which maps a session asks for: the cache join and its chain")
    live = vaultpath.vault_path("captures", "live")
    snap = vaultpath.vault_path("client", mb.CHAIN_RUN_DIR)
    if not os.path.isdir(live) or not os.path.isdir(snap):
        LEDGER.skip("4. the cache join", f"no {live} or no {snap}")
        return False
    import capgaps
    import livewire
    from codec import Codec
    ops = mb.opcodes(Codec())
    rec = mb.read_cache(os.path.join(snap, "Gw.dat"))
    stamps = mb.captures_on(mb.CHAIN_RUN_DIR, root=live)
    set_aside = []
    streams = mb.chain_streams(stamps, set_aside, root=live)
    capdirs = [os.path.join(live, s) for s in stamps]
    ok, detail = capgaps.audit(set_aside, capdirs, livewire.refuses)
    check(ok, "the chain steps past only the declared gapped connection, which still refuses",
          detail)
    # (f)'s premise: replay reads each connection's s2c in WIRE order, so every manifest
    # bracket on the chain must close the way the client's bookkeeping closes it. Review
    # RV-2: chain_streams once handed over livewire.decode_conn's merge, sorted by SEGMENT
    # TIME, and the segment clock runs backwards in places -- the KNOWN-BAD arm below is
    # that order, and on this chain it puts a 0x0196 ahead of its 0x0198. (decode_conn
    # itself keeps wire order since WIREORDER-A1, 2026-10-07; the arm re-sorts by itself.)
    refused = []
    for st in streams:
        try:
            mb.rebuild(st.s2c, ops)
        except mb.ManifestError as exc:
            refused.append((st.capture, st.connection, str(exc)))
    check(len(streams) >= 66 and not refused,
          f"every manifest bracket on all {len(streams)} chain connections closes in wire order "
          f"(rebuild refuses none)", f"{refused[:2]}")
    clock = []
    for st in streams:
        try:
            mb.rebuild(sorted(st.s2c, key=lambda m: m[0]), ops)
        except mb.ManifestError:
            clock.append((st.capture, st.connection))
    check(len(clock) >= 1,
          f"KNOWN-BAD: the same s2c re-sorted by segment clock (decode_conn's old merge) breaks a "
          f"bracket on {len(clock)} connection(s) -- the order is not decoration", f"{clock[:2]}")
    first = [st for st in streams if st.capture == mb.CHAIN_FIRST_CAPTURE]
    head = mb.replay(list(rec.table), first, ops)
    named = [k for k in head if k.named]
    check(stamps[:1] == [mb.CHAIN_FIRST_CAPTURE] and len(named) == 1
          and named[0].named == 142 and len(named[0].asked) == 5
          and named[0].predicted == set(named[0].asked),
          f"(f) {mb.CHAIN_FIRST_CAPTURE}, the first session on {mb.CHAIN_RUN_DIR}: the maps "
          f"whose 0x019F hash differs from the snapshot's table ARE the 0x0093 set, exactly "
          f"-- 5 of 142",
          f"{[(k.connection, k.named, len(k.predicted), len(k.asked)) for k in named]}")
    zero = mb.replay([0] * rec.count, first, ops)
    check(any(k.predicted != set(k.asked) for k in zero),
          "KNOWN-BAD: the same join over an all-zero table predicts every named map and goes red",
          f"{[(len(k.predicted), len(k.asked)) for k in zero]}")
    links = mb.replay(list(rec.table), streams, ops)
    exact = sum(k.predicted == set(k.asked) for k in links)
    asked = sum(len(k.asked) for k in links)
    check(len(stamps) >= 18 and len(links) >= 17 and exact == len(links) and asked >= 37,
          f"(f) carried forward over {len(stamps)} captures (kind-3 DONEs and non-zero kind-0 "
          f"DONEs write the table), every connection's 0x0093 set is predicted exactly: "
          f"{exact} of {len(links)}, {asked} requests",
          f"{[(k.capture, len(k.predicted), len(k.asked)) for k in links if k.predicted != set(k.asked)]}")
    for arm, what in (("none", "without the kind-0 write"),
                      ("all", "writing EVERY kind-0 DONE, zero dwords too")):
        bad = mb.replay(list(rec.table), streams, ops, kind0=arm)
        n = sum(k.predicted == set(k.asked) for k in bad)
        check(n < len(bad), f"KNOWN-BAD: the chain {what} is exact on only {n} of {len(bad)}")
    return True


def guarded(fn):
    """Run a section; a crash becomes a NAMED failing check rather than a traceback
    that never reaches the verdict (test_bit31's rule). Returns the section's value,
    or False after a crash."""
    try:
        return fn()
    except Exception as exc:      # noqa: BLE001 -- reported, never swallowed
        check(False, f"{fn.__name__} ran to its end",
              f"CRASHED: {type(exc).__name__}: {exc}")
        return False


def main():
    guarded(section_bare)
    vaulted = [guarded(section_corpus), guarded(section_cache), guarded(section_join)]
    if all(vaulted):
        LEDGER.floor = FLOOR_VAULT
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
