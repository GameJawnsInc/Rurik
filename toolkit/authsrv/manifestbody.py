"""The manifest family, read whole: what `0x0196` carries, what `0x0197 [3]`'s dword is,
and the client-side record `0x019F`'s hashes are compared against.

    python toolkit/authsrv/manifestbody.py                 # the corpus census
    python toolkit/authsrv/manifestbody.py --chain         # the cache chain on run-live/2026-09-01

Divergence D13 (studies/divergence/FINDINGS.md) named the family to the request and left
three things open in D13.3; D13.4 settles them, and this module is that settlement in a
form a test can re-run. Labels per studies/character/FINDINGS.md.

THE BODY (`0x0196`). RECONSTRUCTION from our own disassembly of the pinned 38797 image,
then OBSERVED on every live tape. `0x0198 [phase]` (handler 0x0084EE10 -> 0x008522C0)
frees and restarts one of TWO per-phase buffers (MsCliMan:472, phase < 2); each `0x0196`
(0x0084EDB0 -> 0x00852000) appends its bytes to the current one (MsCliMan:457, no body
outside a bracket); `0x0197` (0x0084EDE0 -> 0x00852040, MsCliMan:487, kind < 4) parses
BOTH buffers with 0x00851A60 and frees them. Each buffer is one list:

    u16 count, u32 first id, then one delta per further id, UNTIL THE BUFFER ENDS:
        byte b < 0xFE        delta = b + 1
        0xFE, u16 w          delta = w + 0xFF       (MsCliMan:101)
        0xFF, u32 d          delta = d              (MsCliMan:107)

-- a strictly ascending list of u32 file ids. The loop ends on the BUFFER, not the count
(the count only reserves), so "count == ids decoded" is a check the bytes can fail.
OBSERVED: 646 of 646 buffers over every live tape close to the exact byte with count ==
ids, and `encode_list` reproduces all 646 byte for byte (2026-10-07).

THE HASH (`0x0197 [3, map, dword]`). OBSERVED, 219 of 219 kind-3 replies:
`manifest_hash(p0, p1) = crc32(p1) ^ ((crc32(p0) << 1) & 0xFFFFFFFF)`, zlib's CRC-32
over the RAW buffers. The confirmed core is "CRC-32 of the phase-1 body" (193 of 193
replies have no phase-0 body); the phase-0 term is a FITTED relation over four distinct
phase-0 bodies (26 replies), stated as a fit and never built on. The corpus does
discriminate a shift from a rotate (two of the four crc32(P0) have bit 31 set). The
client never computes it: 0x00852040 stores the dword at ctx+0x130 and the map at
ctx+0x134, and the completion callback 0x00852560 writes that pair into the cache --
RECONSTRUCTION, a static read whose callees 0x0082D7D0 / 0x0082D900 / 0x008340C0 are unread.

THE CACHE (why a session asks for the maps it asks for). Gw.dat MFT file id 5 is an FFNA
type-4 record, loaded by 0x00851CE0 (RECONSTRUCTION, 38797): chunk 0 is 12 bytes (a
FILETIME and the map count, which must equal the build's MISSIONS or the record is not
taken), chunk 1 the mission mask (`mask_bytes(count)`: 112 on 38797, 116 on 38888/38974),
chunk 2 one u32 hash per map. `0x019F`'s handler 0x00852320 compares cache[map] to each
named hash: equal -> 0x008524A0 (sets the mask bit), different -> the map is QUEUED, and
the queue is drained one `0x0093` at a time (sender 0x008529A0). OBSERVED: chained from
the vault snapshot the 2026-09-13 session started from, `predicted_requests` names every
`0x0093` of every connection on that run directory exactly (17 of 17, `replay`), with two
update rules: a kind-3 DONE writes its (map, dword) into the table, and a kind-0 DONE does
the same ONLY when its dword is non-zero (the client's gate, [ctx+0x238] == 1 at
0x008525E0, is unread -- the non-zero dword is the observed proxy, 17 of 17 with it,
12 of 17 without the kind-0 write, 2 of 17 writing every kind-0).

The loader's staleness rule -- a record older than STALE_AFTER (24 h) has its MASK zeroed
and re-stamped; the TABLE survives -- is UNVERIFIED: read from the disassembly only, with
its two helpers (0x0046DBF0, 0x0046B740) identified by argument shape, not by reading.

PROVENANCE. Nothing here commits a decoded list, a hash table, or file id 5's stamp and
mask (owner play state): the functions read the vault at run time and the test asserts
shapes, counts and relations. Opcodes are resolved BY NAME through the codec, and tapes
decode through `tape.load_tape` / `livewire`, which carry each connection's build, so a
38974 tape (GAME_SMSG renumbered from 0x0194 up) reads in its own numbering.

The wire half (`decode_list`, `encode_list`, `manifest_hash`, `parse_cache`,
`predicted_requests`, `apply_done`) is standard library only with no repo imports, so a
future server arm can take it without loading the corpus readers; `read_cache` and the
corpus walkers import `archive`, `tape`, `livewire` and `vaultpath` when called.
"""
import collections
import ntpath
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))

# Gw.dat's file id for MsCliMan's cache record. RECONSTRUCTION (38797): the loader
# 0x00851CE0 opens it with `push 5` and refuses anything but FFNA type 4. OBSERVED on all
# six vault/client snapshots (2026-04-30 .. 2026-09-30): it binds plainly, to MFT row 8315.
CACHE_FILE_ID = 5
CACHE_FFNA_TYPE = 4
CACHE_CHUNK_IDS = (0, 1, 2)          # header, mission mask, per-map hash table
CACHE_HEADER_BYTES = 12              # FILETIME (u64) + map count (u32); 0x00851D50 cmp 0xC
# 0x00851E26..0x00851E30: now - stamp compared, high dword 0xC9 then low 0x2A69C000.
# 0xC92A69C000 = 864,000,000,000 x 100 ns = 86,400 s = 24 h exactly. UNVERIFIED (above).
STALE_AFTER = 0xC92A69C000

# 0x0197's kinds. RECONSTRUCTION: MsCliMan:487 "type < MANIFEST_TYPES" (cmp kind, 4).
# OBSERVED on retail: 0 = the instance's own map (every load), 2 = the list-open with the
# MAP_ID_COUNT sentinel (every load, dword 0), 3 = the reply to a 0x0093. Kind 1: unseen.
KIND_INSTANCE, KIND_LIST_OPEN, KIND_REPLY = 0, 2, 3
MANIFEST_TYPES = 4
PHASE_COUNT = 2                      # MsCliMan:472 "Invalid manifest phase" (phase < 2)

# THE ONE RUN DIRECTORY WHOSE STARTING ARCHIVE IS IN THE VAULT. `make_run_dir.py` copies
# Gw.dat from C:\gw, not from a snapshot, so a chain needs a snapshot taken from the same
# source moments before the directory was assembled. CORROBORATED for this one only:
# vault/client/2026-09-01_44fbd68767a8's MANIFEST.json says snapshot_utc
# 2026-09-14T01:02:29Z with Gw.dat verified against C:\gw (whose copy was last written at
# 00:53Z), run-live/2026-09-01_44fbd68767a8/Gw.exe was written at 01:03Z, and the first
# capture on it, 20260913T210901, sealed its plan at 01:08:45Z. Every other run-live
# directory either predates its snapshot (2026-07-29, 2026-08-20) or has been rewritten
# (2026-08-13, by the updater -- RUNBOOK.md), and 2026-09-30 has no capture yet.
CHAIN_RUN_DIR = "2026-09-01_44fbd68767a8"
CHAIN_FIRST_CAPTURE = "20260913T210901"

NAMES = {                            # resolved through the codec, never hardcoded
    "phase": ("GAME_SMSG", "INSTANCE_MANIFEST_PHASE"),
    "body": ("GAME_SMSG", "INSTANCE_MANIFEST_BODY"),
    "done": ("GAME_SMSG", "INSTANCE_MANIFEST_DONE"),
    "versions": ("GAME_SMSG", "MAP_MANIFEST_VERSIONS"),
    "request": ("GAME_CMSG", "MAP_MANIFEST_REQUEST"),
}


class ManifestError(ValueError):
    """A body, a bracket sequence or a cache record that does not have the layout.
    Raised, never stepped past: the client asserts on every one of these."""


# ---------------------------------------------------------------- the body ----------

def decode_list(buf):
    """(count word, [file ids]) for one phase buffer, read the way 0x00851A60 reads it.

    An empty buffer is no list (the parser returns on size 0); a count of 0 returns
    before reading on, as the client does. Otherwise the loop runs to the END OF THE
    BUFFER and the count is returned beside the ids, not used to stop -- so a caller can
    hold the two against each other. Raises ManifestError where the client would assert:
    a header short of six bytes (MsCliMan:76/:88) or an escape running past the end
    (:101/:107)."""
    buf = bytes(buf)
    if not buf:
        return 0, []
    if len(buf) < 2:
        raise ManifestError(f"{len(buf)}-byte buffer: shorter than its count word")
    count = struct.unpack_from("<H", buf, 0)[0]
    if count == 0:
        return 0, []
    if len(buf) < 6:
        raise ManifestError(f"{len(buf)}-byte buffer: no room for the first id")
    ids = [struct.unpack_from("<I", buf, 2)[0]]
    p, end = 6, len(buf)
    while p < end:
        b = buf[p]
        p += 1
        if b < 0xFE:
            delta = b + 1
        elif b == 0xFE:
            if p + 2 > end:
                raise ManifestError(f"word escape at {p - 1} runs past the {end}-byte buffer")
            delta = struct.unpack_from("<H", buf, p)[0] + 0xFF
            p += 2
        else:
            if p + 4 > end:
                raise ManifestError(f"dword escape at {p - 1} runs past the {end}-byte buffer")
            delta = struct.unpack_from("<I", buf, p)[0]
            p += 4
        ids.append((ids[-1] + delta) & 0xFFFFFFFF)
    return count, ids


def encode_list(ids):
    """`decode_list`'s inverse: the narrowest form for each gap. A strictly ascending,
    non-empty list of u32 ids; an empty list is the empty buffer. OBSERVED: this is
    ArenaNet's encoder too -- 646 of 646 corpus buffers re-encode byte for byte."""
    ids = list(ids)
    if not ids:
        return b""
    if len(ids) > 0xFFFF:
        raise ManifestError(f"{len(ids)} ids do not fit the u16 count")
    out = bytearray(struct.pack("<HI", len(ids), ids[0]))
    for a, b in zip(ids, ids[1:]):
        d = b - a
        if d < 1 or b > 0xFFFFFFFF:
            raise ManifestError(f"ids must be strictly ascending u32s ({a} then {b})")
        if d <= 0xFE:
            out.append(d - 1)
        elif d <= 0xFFFF + 0xFF:
            out.append(0xFE)
            out += struct.pack("<H", d - 0xFF)
        else:
            out.append(0xFF)
            out += struct.pack("<I", d)
    return bytes(out)


def crc32(data):
    """zlib's CRC-32 (ISO-HDLC) of `data`, unsigned. crc32(b"") is 0."""
    return zlib.crc32(bytes(data)) & 0xFFFFFFFF


def manifest_hash(p0, p1):
    """The dword retail's `0x0197 [3, map, dword]` carries for a reply whose phase
    buffers are `p0` and `p1` (raw bytes; b"" for a phase with no body).

    OBSERVED 219 of 219: crc32(p1) alone on the 193 replies with no phase-0 body (the
    confirmed core), and crc32(p1) ^ (crc32(p0) << 1) on the 26 that carry one -- that
    second term is a FIT over four distinct phase-0 bodies. Since crc32(b"") is 0 the
    one formula covers both. The client stores this value and never recomputes it
    (RECONSTRUCTION), so it is retail's convention for a server, not a client check."""
    return crc32(p1) ^ ((crc32(p0) << 1) & 0xFFFFFFFF)


# ---------------------------------------------------------------- the cache ---------

CacheRecord = collections.namedtuple("CacheRecord", "stamp count mask table")


def mask_bytes(count):
    """The mission mask's width for a map count: whole dwords, one bit per map
    (112 for 888, 116 for 897 and 898 -- the 0x0092 row's MISSION_MASK_BYTES)."""
    return -(-count // 32) * 4


def _chunks(data):
    """[(chunk id, offset, size)] of an FFNA file, walked to the exact byte. The same
    walk as mapdata/archive.ffna_chunks, repeated here so the wire half stays free of
    repo imports; `read_cache`'s test holds the two against each other."""
    if data[:4] != b"ffna":
        raise ManifestError(f"not an FFNA file: {bytes(data[:4])!r}")
    out, pos = [], 5
    while pos + 8 <= len(data):
        cid, size = struct.unpack_from("<II", data, pos)
        if pos + 8 + size > len(data):
            raise ManifestError(f"chunk {cid} at {pos} claims {size} bytes past the end")
        out.append((cid, pos + 8, size))
        pos += 8 + size
    if pos != len(data):
        raise ManifestError(f"chunk walk ended at {pos} of {len(data)} bytes")
    return out


def parse_cache(data, missions=None):
    """CacheRecord(stamp, count, mask, table) from file id 5's decompressed bytes.

    Asserts the shape the loader 0x00851CE0 asserts (RECONSTRUCTION, 38797): FFNA type
    4, chunks 0/1/2 in that order, chunk 0 twelve bytes, chunk 1 `mask_bytes(count)`,
    chunk 2 four bytes per map. `missions`, when given, is the client build's map count,
    which the loader requires chunk 0's count to equal -- a record written by another
    build is NOT TAKEN, and a client without its record asks for every named map."""
    data = bytes(data)
    if len(data) < 5 or data[4] != CACHE_FFNA_TYPE:
        raise ManifestError(f"FFNA type {data[4] if len(data) > 4 else None}, "
                            f"want {CACHE_FFNA_TYPE}")
    ch = _chunks(data)
    if tuple(c for c, _o, _s in ch) != CACHE_CHUNK_IDS:
        raise ManifestError(f"chunk ids {[c for c, _o, _s in ch]}, want {list(CACHE_CHUNK_IDS)}")
    (_, o0, s0), (_, o1, s1), (_, o2, s2) = ch
    if s0 != CACHE_HEADER_BYTES:
        raise ManifestError(f"header chunk is {s0} bytes, want {CACHE_HEADER_BYTES}")
    stamp, count = struct.unpack_from("<QI", data, o0)
    if missions is not None and count != missions:
        raise ManifestError(f"record counts {count} maps; this build has {missions}")
    if s1 != mask_bytes(count):
        raise ManifestError(f"mask chunk is {s1} bytes, want {mask_bytes(count)} for {count} maps")
    if s2 != 4 * count:
        raise ManifestError(f"table chunk is {s2} bytes, want {4 * count} for {count} maps")
    return CacheRecord(stamp, count, data[o1:o1 + s1],
                       list(struct.unpack_from(f"<{count}I", data, o2)))


def is_stale(stamp, now):
    """True when the loader would zero the mask: now - stamp > 24 h (FILETIME ticks).
    UNVERIFIED -- see the module docstring."""
    return now - stamp > STALE_AFTER


def predicted_requests(table, named):
    """The maps a client holding `table` QUEUES for `0x0093` when `0x019F` names `named`
    ({map: hash} or [(map, hash)]): every one whose cached hash differs. 0x00852320's
    compare (RECONSTRUCTION), 17 of 17 connections on the chain (OBSERVED).

    THE HAZARD FOR A SERVER THAT SENDS 0x019F (DESKWORK-D3): naming a hash that differs
    from the run directory's own record queues that map, and the client asks for it.
    Name the record's own values, or send no 0x019F."""
    pairs = named.items() if isinstance(named, dict) else named
    return {m for m, h in pairs if m >= len(table) or table[m] != h}


def apply_done(table, kind, map_id, dword):
    """Update `table` (in place) the way a completed DONE does: kind 3 writes (map,
    dword) -- 0x00852560 -> 0x008524A0 (RECONSTRUCTION); kind 0 writes it only when the
    dword is non-zero (OBSERVED proxy for the unread [ctx+0x238] == 1 gate)."""
    if kind == KIND_REPLY or (kind == KIND_INSTANCE and dword):
        table[map_id] = dword


# ---------------------------------------------------------------- the wire ----------

def opcodes(codec):
    """{key: SCHEMA opcode} for NAMES, looked up by name in `codec`. `tape.decode_all`
    hands back the schema's numbering for every build (codec.GAME_SMSG_RENUMBER), so a
    consumer compares against these whatever build the tape is."""
    out = {}
    for key, (chan, name) in NAMES.items():
        hits = [int(k) for k, m in codec.channels[chan]["messages"].items()
                if m.get("name") == name]
        if len(hits) != 1:
            raise ManifestError(f"{chan} names {name} {len(hits)} times, want 1")
        out[key] = hits[0]
    return out


Done = collections.namedtuple("Done", "index kind map dword p0 p1")


def rebuild(msgs, ops):
    """[Done] for one connection's decoded s2c messages ([(t, opcode, values)] in
    order, values[0] the header): each DONE with the two phase buffers it closed.

    The client's own bookkeeping (RECONSTRUCTION): PHASE restarts one buffer and makes
    it current, BODY appends to the current one, DONE consumes and frees both -- so a
    phase the server never bracketed reads as b"". Refuses (ManifestError) what the
    client asserts on: a body with no open phase (MsCliMan:457), a phase >= 2 (:472),
    a kind >= 4 (:487)."""
    bufs = {0: bytearray(), 1: bytearray()}
    phase = None
    out = []
    for i, (_t, op, v) in enumerate(msgs):
        if op == ops["phase"]:
            if v[1] >= PHASE_COUNT:
                raise ManifestError(f"message {i}: phase {v[1]} (MsCliMan:472)")
            phase = v[1]
            bufs[phase] = bytearray()
        elif op == ops["body"]:
            if phase is None:
                raise ManifestError(f"message {i}: a body with no open phase (MsCliMan:457)")
            bufs[phase] += v[1]
        elif op == ops["done"]:
            if v[1] >= MANIFEST_TYPES:
                raise ManifestError(f"message {i}: kind {v[1]} (MsCliMan:487)")
            out.append(Done(i, v[1], v[2], v[3], bytes(bufs[0]), bytes(bufs[1])))
            bufs = {0: bytearray(), 1: bytearray()}
            phase = None
    return out


Reply = collections.namedtuple("Reply", "capture connection build kind map dword p0 p1")


def _repo_paths():
    for d in (HERE, os.path.dirname(HERE), os.path.join(os.path.dirname(HERE), "schema"),
              os.path.join(os.path.dirname(HERE), "mapdata")):
        if d not in sys.path:
            sys.path.insert(0, d)


def read_cache(dat_path, missions=None):
    """`parse_cache` of file id 5 in the archive at `dat_path`, opened READ-ONLY.

    Resolves the id through the client's own view (`file_id_table(raw=True)`: the id
    verbatim, no bit-31 alias). Point it at a vault/client snapshot -- never at a run
    directory a client may be writing, and never at C:\\gw."""
    _repo_paths()
    import archive
    with archive.Archive(dat_path) as ar:
        row = archive.file_id_table(ar, raw=True).get(CACHE_FILE_ID)
        if row is None:
            raise ManifestError(f"{dat_path}: file id {CACHE_FILE_ID} does not bind")
        data = ar.read(ar.row(row))
    if [c[:3] for c in archive.ffna_chunks(data)] != _chunks(data):
        raise ManifestError(f"{dat_path}: archive.ffna_chunks and this module's walk disagree")
    return parse_cache(data, missions)


def corpus_replies(set_aside, root=None, codec=None):
    """Every DONE on every live game connection, as Reply rows, in capture order.

    Iterates `tape.whole_channels` -- the ONE set-aside, a connection its capture's own
    manifest declares gapped, printed and appended to `set_aside` -- and decodes each
    through `tape.load_tape` / `decode_all`, which carry the connection's build. Any
    other refusal raises."""
    _repo_paths()
    import tape
    import vaultpath
    from codec import Codec
    codec = codec or Codec()
    ops = opcodes(codec)
    root = root or vaultpath.require_dir("captures", "live", why="manifestbody reads live captures")
    for stamp in sorted(os.listdir(root)):
        capdir = os.path.join(root, stamp)
        if not os.path.isdir(capdir):
            continue
        for ch in tape.whole_channels(capdir, set_aside):
            info, events = tape.load_tape(capdir, ch["connection"])
            msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            for d in rebuild(msgs, ops):
                yield Reply(stamp, ch["connection"], info["build"], d.kind, d.map, d.dword,
                            d.p0, d.p1)


def captures_on(run_tag, root=None):
    """The live captures whose own manifest says the client ran from
    vault/run-live/<run_tag>/, sorted by stamp."""
    _repo_paths()
    import json
    import vaultpath
    root = root or vaultpath.require_dir("captures", "live", why="manifestbody reads live captures")
    out = []
    for stamp in sorted(os.listdir(root)):
        mf = os.path.join(root, stamp, "manifest.json")
        if not os.path.isfile(mf):
            continue
        with open(mf, encoding="utf-8") as fh:
            exe = json.load(fh).get("exe") or ""
        run_dir = ntpath.dirname(exe.replace("/", "\\"))
        if (ntpath.basename(run_dir) == run_tag
                and ntpath.basename(ntpath.dirname(run_dir)) == "run-live"):
            out.append(stamp)
    return out


Link = collections.namedtuple("Link", "capture connection named predicted asked")
Stream = collections.namedtuple("Stream", "capture connection s2c c2s")


def chain_streams(stamps, set_aside, root=None, codec=None):
    """[Stream(stamp, connection, s2c, c2s)] for every game connection of `stamps`,
    each DIRECTION decoded on its own in WIRE order -- `livewire.build_events` (TCP
    sequence order, the build carried) then `tape.decode_all`, the path `corpus_replies`
    takes through `load_tape` -- as [(t, opcode, values)] in the schema's numbering.
    Connections are put in capture-clock order by their earliest message.

    NOT `livewire.decode_conn`'s merged stream, and this is why (review RV-2,
    2026-10-07): that one WAS SORTED BY SEGMENT TIME, and a capture's segment clock runs
    backwards in places (on 41 of 127 live game connections' s2c, measured 2026-10-07), so
    the merge was not wire order.
    On two connections of this chain it moved the manifest family itself -- a `0x0196`
    ahead of its `0x0198`, a kind-0 DONE ahead of the kind-2 bracket -- which `rebuild`
    refuses (MsCliMan:457). decode_conn keeps each direction in wire order since
    WIREORDER-A1 (studies/tape/WIREORDER.md, the same day), and `test_livewire.py` section
    6 holds both connections to it; this reader still keeps the two directions apart,
    because `replay` needs the s2c order of DONE against `0x019F` and nothing of the
    c2s/s2c interleaving.

    A connection that will not decode in BOTH directions to the last byte RAISES unless
    its capture's manifest declares it gapped -- then it is set aside by name into
    `set_aside` (the same refusal `decode_conn`'s ok flag made)."""
    _repo_paths()
    import capgaps
    import livewire
    import tape
    import vaultpath
    from codec import Codec
    codec = codec or Codec()
    root = root or vaultpath.require_dir("captures", "live", why="manifestbody reads live captures")
    ways = (("s2c", "GAME_SMSG", 0), ("c2s", "GAME_CMSG", livewire.CMSG_MASK))
    out = []
    for stamp in stamps:
        capdir = os.path.join(root, stamp)
        gaps = capgaps.declared_gaps(capdir)
        conns = []
        for gf in livewire.connections(capdir):
            if gaps and capgaps.set_aside(capdir, gf, gaps, set_aside):
                continue
            got, conn = {}, None
            for way, chan, mask in ways:
                conn, events, err = livewire.build_events(capdir, gf, way)
                if err is not None:
                    raise ManifestError(f"{stamp} {gf} {way}: {err}, and its manifest "
                                        f"declares no gap")
                msgs, receipt = tape.decode_all(events, codec, chan, mask, strict=False)
                if receipt.err is not None or receipt.consumed != receipt.total:
                    raise ManifestError(f"{stamp} {gf} {way}: decoded {receipt.consumed} of "
                                        f"{receipt.total} bytes ({receipt.err}), and its "
                                        f"manifest declares no gap")
                got[way] = msgs
            times = [t for msgs in got.values() for t, _op, _v in msgs]
            if times:
                conns.append((min(times), conn, got["s2c"], got["c2s"]))
        conns.sort(key=lambda c: c[0])
        out += [Stream(stamp, conn, s2c, c2s) for _t0, conn, s2c, c2s in conns]
    return out


def replay(table, streams, ops, kind0="nonzero"):
    """Carry a cache `table` forward over `streams` (`chain_streams` of the captures on
    ONE run directory), predicting each connection's `0x0093` set from the table as it
    stands when `0x019F` names each map. [Link] for every connection that named a map
    or asked for one; `table` is mutated.

    Per s2c message in WIRE order: a `0x019F` entry is compared to the table
    (`predicted_requests`), a DONE updates it; the connection's c2s `0x0093`s are what
    it asked. `kind0` picks the kind-0 rule: "nonzero" (`apply_done`, the observed one)
    and two KNOWN-BAD arms a test holds red, "none" (kind 3 only) and "all" (every
    kind-0 DONE written, zero dwords too)."""
    if kind0 not in ("nonzero", "none", "all"):
        raise ValueError(f"kind0={kind0!r}")
    links = []
    for st in streams:
        named, predicted = 0, set()
        for _t, op, v in st.s2c:
            if op == ops["versions"]:
                named += len(v[1])
                predicted |= predicted_requests(table, v[1])
            elif op == ops["done"]:
                kind, m, dword = v[1], v[2], v[3]
                if kind0 == "nonzero":
                    apply_done(table, kind, m, dword)
                elif kind == KIND_REPLY or (kind0 == "all" and kind == KIND_INSTANCE):
                    table[m] = dword
        asked = [v[1] for _t, op, v in st.c2s if op == ops["request"]]
        if named or asked:
            links.append(Link(st.capture, st.connection, named, predicted, asked))
    return links


# ---------------------------------------------------------------- CLI ---------------

def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chain", action="store_true",
                    help="predict every 0x0093 on run-live/2026-09-01 from its snapshot")
    args = ap.parse_args(argv)
    _repo_paths()
    import vaultpath
    set_aside = []
    if args.chain:
        from codec import Codec
        tag = CHAIN_RUN_DIR
        rec = read_cache(os.path.join(vaultpath.require_dir("client", why="the snapshot"),
                                      tag, "Gw.dat"))
        links = replay(list(rec.table), chain_streams(captures_on(tag), set_aside),
                       opcodes(Codec()))
        exact = sum(1 for k in links if k.predicted == set(k.asked))
        for k in links:
            print(f"  {k.capture} {k.connection}: named {k.named}, predicted "
                  f"{len(k.predicted)}, asked {len(k.asked)}"
                  f"{'' if k.predicted == set(k.asked) else '  DIFFERS'}")
        print(f"{exact} of {len(links)} connections exact, "
              f"{sum(len(k.asked) for k in links)} requests")
        return 0 if exact == len(links) else 1
    by_kind = collections.Counter()
    bad = 0
    for r in corpus_replies(set_aside):
        by_kind[r.kind] += 1
        for buf in (r.p0, r.p1):
            if buf:
                count, ids = decode_list(buf)
                bad += count != len(ids) or encode_list(ids) != buf
        if r.kind == KIND_REPLY:
            bad += manifest_hash(r.p0, r.p1) != r.dword
    print(f"DONEs by kind {dict(sorted(by_kind.items()))}; {bad} disagreement(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_main())
