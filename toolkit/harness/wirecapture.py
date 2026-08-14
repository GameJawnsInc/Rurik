"""Capture a live session's ciphertext off the wire, so replay.py can decrypt it offline.

    python toolkit/harness/wirecapture.py --pid <client> --server <ip:port> [--seconds N]
    python toolkit/harness/wirecapture.py --ports 6112,6601 --out live.jsonl   # live: any host

The ciphertext half of the R0b live-capture driver (route C, studies/livekey/CAPTURE.md).
Our own server is not in a live session, so nothing on our side sees the bytes; a network
tap does. This reads the client's TCP stream from outside the process with WinDivert in
SNIFF mode -- it observes and never alters, so the live connection is not perturbed -- and
records each TCP segment with its sequence number. The session key comes separately from
keytap.py (the code cave), and replay.py reassembles and decrypts offline.

WHY THE HANDSHAKE IS CAPTURABLE TOO. ARC4 begins only after the key is derived, so the DH
exchange -- VERSION, CLIENT_SEED (the client public A), SERVER_SEED -- crosses the wire in
the clear. A wire capture therefore contains A and the server seed directly, which is what
lets an offline reader split the plaintext prefix from the ciphertext and (with the tapped
key) decrypt the rest. Both directions are recorded; direction is decided by which endpoint
is the server, not by WinDivert's version-specific address struct, so this does not break
across WinDivert releases.

DEPENDENCY. WinDivert (LGPLv3, called via ctypes; PLAN.md §6.1) -- the CLAUDE.md carve-out,
scoped to this driver only, never the server path, never the suite. Opening the handle
needs an elevated shell (it loads a kernel driver); absent or unelevated, this refuses with
the install step rather than proceeding. The parsing and reassembly below are pure and are
what test_wirecapture.py exercises without the driver.

standard library only apart from the carved-out WinDivert DLL.
"""
import argparse
import json
import os
import socket
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import origin  # noqa: E402
import tcptable  # noqa: E402

C2S = "c2s"
S2C = "s2c"


# ------------------------------------------------------------- packet parsing --
def parse_ipv4_tcp(pkt):
    """{'src','dst','sport','dport','seq','flags','payload'} for an IPv4/TCP packet, else None.

    Pure and total: any malformed or non-TCP/non-IPv4 packet returns None rather than
    raising, because a sniff sees everything the filter let through plus the occasional
    runt, and a capture loop that dies on one bad packet loses the session.
    """
    if len(pkt) < 20:
        return None
    ver_ihl = pkt[0]
    if ver_ihl >> 4 != 4:
        return None
    ihl = (ver_ihl & 0x0F) * 4
    if ihl < 20 or len(pkt) < ihl:
        return None
    proto = pkt[9]
    if proto != 6:                       # TCP
        return None
    total_len = struct.unpack_from(">H", pkt, 2)[0]
    # Trust the smaller of captured length and the IP header's claim.
    end = min(len(pkt), total_len) if total_len >= ihl else len(pkt)
    src = socket.inet_ntoa(pkt[12:16])
    dst = socket.inet_ntoa(pkt[16:20])
    if end < ihl + 20:
        return None
    tcp = pkt[ihl:end]
    sport, dport, seq = struct.unpack_from(">HHI", tcp, 0)
    data_off = (tcp[12] >> 4) * 4
    if data_off < 20 or len(tcp) < data_off:
        return None
    flags = tcp[13]
    payload = tcp[data_off:]
    return {"src": src, "dst": dst, "sport": sport, "dport": dport,
            "seq": seq, "flags": flags, "payload": payload}


def direction_of(pkt, server_ip, server_ports):
    """C2S if the packet is heading to the server, S2C if coming from it, else None.

    Decided from the endpoints, not from any capture-time metadata, so a replay of the
    same packets classifies identically and the direction survives a WinDivert upgrade.

    `server_ip=None` means "any host on these ports", which is what a LIVE capture needs:
    the sniff has to be running BEFORE the client connects (the DH handshake is the first
    thing on the wire and it is the plaintext half we cannot lose), and at that moment
    nobody knows which of ArenaNet's addresses it will pick. The well-known port then
    decides which end is the server, which is sound because the other end is an ephemeral
    port -- 49152+ on Windows, never 6112 or 6601. If BOTH ends or NEITHER end holds a
    server port the direction is genuinely undecidable, and this returns None rather than
    picking: a misfiled segment lands in the wrong direction's stream and desyncs a
    keystream, which surfaces far from here as "the decrypt is garbage".
    """
    if server_ip is None:
        to_srv = pkt["dport"] in server_ports
        from_srv = pkt["sport"] in server_ports
        if to_srv == from_srv:
            return None
        return C2S if to_srv else S2C
    if pkt["dst"] == server_ip and pkt["dport"] in server_ports:
        return C2S
    if pkt["src"] == server_ip and pkt["sport"] in server_ports:
        return S2C
    return None


# --------------------------------------------------------------- reassembly ----
def reassemble(segments):
    """Ordered payload bytes for one direction, from [(seq, payload), ...].

    TCP sequence numbers order the stream and wrap at 2**32. We anchor on the first
    segment's seq as the stream origin, place every later segment at (seq - origin) mod
    2**32, and drop pure-duplicate retransmits. Gaps are left as they fall -- a live tap
    can miss a segment, and a decryptor must see the gap (its keystream desyncs there)
    rather than have it silently closed. Returns (bytes, gaps) where gaps is a list of
    (offset, length) holes.
    """
    if not segments:
        return b"", []
    # Anchor on the LOWEST sequence number, not the first-arrived segment: WinDivert hands
    # us packets in arrival order, and if a later segment arrives first, anchoring on it
    # would push every real byte to a near-2**32 offset and blow the stream up. Within a
    # single session the seqs do not wrap, so min() is the true stream origin.
    origin_seq = min(seq for seq, _ in segments)
    placed = {}
    for seq, payload in segments:
        if not payload:
            continue
        off = (seq - origin_seq) & 0xFFFFFFFF
        # A retransmit of already-seen bytes is fine; a conflicting overwrite is noted by
        # keeping the first. Loopback and a quiet LAN rarely reorder, but be correct.
        placed.setdefault(off, payload)
    if not placed:
        return b"", []
    out = bytearray()
    gaps = []
    cursor = 0
    for off in sorted(placed):
        if off > cursor:
            gaps.append((cursor, off - cursor))
            out.extend(b"\x00" * (off - cursor))
        elif off < cursor:
            # Overlap: only append the part beyond the cursor.
            overlap = cursor - off
            if overlap >= len(placed[off]):
                continue
            out.extend(placed[off][overlap:])
            cursor += len(placed[off]) - overlap
            continue
        out.extend(placed[off])
        cursor = off + len(placed[off])
    return bytes(out), gaps


# ------------------------------------------------------------- capture output --
def open_capture(path, client, server, pid, server_ports, clock, wall=time.time):
    """Start a live capture file: origin FIRST, then the wire metadata. Returns a writer.

    The origin record is written explicitly as LIVE -- origin.py never infers LIVE, by
    design, so a live capture that forgets to say so is UNKNOWN forever. `clock` is passed
    in (time.perf_counter) so the pure tests can supply a deterministic one, and `wall`
    (time.time) for the same reason.

    THE EPOCH, added 2026-08-11, and it is the fix for a real blocker rather than a
    nicety. Every segment is stamped `clock() - t0`, and `t0` is taken HERE -- inside the
    sniffer subprocess, after WinDivert opens. `perf_counter()`'s reference point is
    undefined by CPython's own contract: only differences taken within one call site are
    meaningful. So until now the `t` in a capture was an offset from an origin **no other
    process could name**, and the only other clock in the artifact was `manifest.json`'s
    `strftime`, taken in the PARENT before this subprocess was spawned. A narrated live
    session could therefore be aligned to its narration only post-hoc and only to within
    seconds, off server-side anchors -- which is precisely the gap-inference failure
    `labelrun.py` was written to end, and it would have made every behaviour-capture
    session un-analysable. studies/monsterai/FINDINGS.md §7.1.

    `t0_wall` is `time.time()` sampled adjacent to `t0`, so `t0_wall + t` is an absolute
    UTC timestamp for every segment. That IS a legitimate use of `perf_counter`: the
    subtraction stays inside this process, and the absolute clock only pins its origin.

    `t0_perf` IS THE RAW `perf_counter()` READING, and writing it down is what makes the
    paragraph above a measurement instead of a hope. Added 2026-08-13 for
    `toolkit/harness/marks.py`. On its own it is meaningless outside this process -- that
    is CPython's contract, only differences taken within one call site are defined -- and
    that is exactly why it is here: a mark taken in ANOTHER process carries its own
    `t_perf` and `t_wall`, so `marks.bind` can compute `t_perf - t0_perf` for the wire
    time AND check it against `t_wall - t0_wall`, refusing past 250 ms. Publishing only
    `t0_wall` left the cross-process comparability of `perf_counter` on Windows as an
    assumption nothing in the artifact could refute; publishing both makes it a claim the
    two clocks can contradict. It costs one number per capture.

    WRITTEN AFTER THE CLOCKS ARE TAKEN, which reorders two lines. `dryrun_keycapture.py`
    and `livesession.py` both use the PRESENCE of the `wire_meta` line as proof the sniff
    opened, and that still holds -- open_capture is only reached once WinDivert is up, so
    every write in it is after.

    It does NOT make the marks channel redundant. This binds the wire clock to absolute
    time; it says nothing about whether the operator's narration is bound to the same
    instant, and a single unchecked channel is what this project calls a fixture that
    resolves silently. `marks.jsonl` is the second witness and they are required to agree.
    """
    # The stamp is DERIVED from the endpoint being sniffed, not asserted. It used to be a
    # hardcoded origin.LIVE, which made every loopback dry-run capture claim to be live
    # traffic -- vault/dryrun/dryrun_wire.jsonl says `"origin": "live"` while every address
    # in it is 127.0.0.1. dryrun_keycapture.py's own comment shows the response to that was
    # to move the mislabelled files outside the directory the suite scans, which makes the
    # guard against a false LIVE stamp green by construction. Fixed at the source: a sniff
    # pinned to loopback cannot be talking to ArenaNet, and says OURS.
    #
    # An unpinned (port-only) sniff still declares LIVE, because that mode exists only for
    # the live driver -- but now the one case that was provably wrong is measured instead.
    who = origin.OURS if (server and origin.is_loopback(str(server).rsplit(":", 1)[0])) \
        else origin.LIVE
    fh = open(path, "w", encoding="utf-8")
    rec = origin.record("toolkit/harness/wirecapture.py", who,
                        note="off-wire ciphertext; key from keytap.py, decrypt with replay.py")
    fh.write(json.dumps(rec) + "\n")
    # The two clocks, sampled adjacently. Order matters only in that nothing may run
    # between them that could take measurable time.
    t0 = clock()
    t0_wall = wall()
    fh.write(json.dumps({"kind": "wire_meta", "client": client, "server": server,
                         "pid": pid, "server_ports": sorted(server_ports),
                         "t0_perf": t0, "t0_wall": t0_wall}) + "\n")
    fh.flush()

    def record(direction, seq, payload, pkt=None):
        """One TCP segment. `pkt` carries the endpoints, and it is not optional for a live
        capture: a real session opens SEVERAL connections (portal, auth, then the game
        server on a different address), and without the 4-tuple every segment of a
        direction reassembles into ONE stream by sequence number -- two unrelated TCP
        streams interleaved by seq is not a stream, it is noise that decrypts to nothing.
        It stays optional in the signature only so the pure tests can synthesise a
        single-connection capture the way they always have."""
        out = {"kind": "wire", "dir": direction, "seq": seq, "t": clock() - t0,
               "payload": payload.hex()}
        if pkt:
            out.update({"src": pkt["src"], "sport": pkt["sport"],
                        "dst": pkt["dst"], "dport": pkt["dport"]})
        fh.write(json.dumps(out) + "\n")
        fh.flush()

    return fh, record


def endpoints_of(rec):
    """((client_ip, client_port), (server_ip, server_port)) for a wire record, or None.

    None for a legacy record with no addresses. The client end is the source of a c2s
    segment and the destination of an s2c one, so this needs no port table and cannot
    disagree with the `dir` already recorded.
    """
    if "src" not in rec or "dst" not in rec:
        return None
    a = (rec["src"], rec["sport"])
    b = (rec["dst"], rec["dport"])
    return (a, b) if rec.get("dir") == C2S else (b, a)


def conn_key(rec):
    """A stable per-connection label, or None for a legacy addressless record."""
    ends = endpoints_of(rec)
    if not ends:
        return None
    (cip, cport), (sip, sport) = ends
    return f"{cip}:{cport}->{sip}:{sport}"


def load_connections(path):
    """Read a wire capture into (meta, {conn_key: {C2S: bytes, S2C: bytes, 'gaps': ...}}).

    This is the live-shaped reader: one entry per TCP connection, each reassembled on its
    own sequence space. Addressless legacy records are grouped under the key None so an
    older capture still reads back.
    """
    meta = None
    segs = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(r, dict):
                continue
            if r.get("kind") == "wire_meta":
                meta = r
            elif r.get("kind") == "wire" and r.get("dir") in (C2S, S2C):
                key = conn_key(r)
                bucket = segs.setdefault(key, {C2S: [], S2C: []})
                bucket[r["dir"]].append((r["seq"], bytes.fromhex(r.get("payload", ""))))
    conns = {}
    for key, bucket in segs.items():
        entry = {"gaps": {}}
        for d in (C2S, S2C):
            entry[d], entry["gaps"][d] = reassemble(bucket[d])
        conns[key] = entry
    return meta, conns


def capture_epoch(meta):
    """The absolute UTC time a capture's `t = 0` corresponds to, or None.

    None means the capture predates the epoch record (2026-08-11) and its segment
    timestamps CANNOT be placed on any clock but their own. Returning None rather than
    guessing is the whole point: a caller that silently substituted `manifest.json`'s
    stamp would be off by however long it took to spawn the sniffer subprocess and open
    WinDivert, which is exactly the error nobody would see.
    """
    if not isinstance(meta, dict):
        return None
    t0 = meta.get("t0_wall")
    return float(t0) if isinstance(t0, (int, float)) else None


def wall_of(meta, t):
    """A segment's `t` as absolute UTC, or None when the capture carries no epoch."""
    t0 = capture_epoch(meta)
    return None if t0 is None else t0 + t


MARKS_NAME = "marks.jsonl"


def write_mark(fh, n, label, wire_t, clock=time.perf_counter, wall=time.time,
               at_wall=None, at_perf=None):
    """One operator mark: the SECOND witness to the wire clock.

    Each mark carries three numbers and the redundancy is the design:

      * `wall`      -- absolute UTC, the same clock `t0_wall` is on. This is what
                       actually binds a narration step to the capture.
      * `perf`      -- the PARENT's own perf_counter. Useless across processes on its
                       own, which is why it is not the binding; it is here so a
                       mark-to-mark INTERVAL can be checked against the wall-clock
                       interval, catching a wall clock that jumped (NTP, DST, a manual
                       change) mid-session.
      * `wire_t`    -- the `t` of the last record then present in the capture, read from
                       the file. This is the independent channel. If wall-clock
                       arithmetic and the capture's own progress disagree, one of them is
                       wrong and the analyser must say so rather than average them.

    A single channel would be unchecked, and this project's rule is that a fixture which
    silently resolves to the wrong thing turns every assertion behind it into a no-op.

    A MARK'S TIME IS WHEN IT WAS TAKEN, NOT WHEN IT WAS NOTICED, and `at_wall`/`at_perf`
    are how a caller says so. The driver picks marks up by POLLING a file and its loop
    waits 5 s between passes, so a mark stamped at pickup is late by up to five seconds
    -- coarser than the alignment this whole mechanism exists to provide, and a defect
    that would have made the first session's marks useless without ever looking wrong.
    `narrate` records the instant it writes the MARK file and the driver carries that
    through. `pickup_lag` keeps the latency VISIBLE instead of letting it vanish into
    the timestamp: a lag near the poll interval on every mark is worth seeing.
    """
    w = wall() if at_wall is None else at_wall
    p = clock() if at_perf is None else at_perf
    rec = {"kind": "mark", "n": n, "label": label, "wall": w, "perf": p,
           "wire_t": wire_t}
    if at_wall is not None:
        rec["pickup_lag"] = round(wall() - at_wall, 3)
    fh.write(json.dumps(rec) + "\n")
    fh.flush()


def last_wire_t(path):
    """The `t` of the last wire record in a capture, or None if there is none yet.

    Reads the file rather than sharing state with the sniffer, because the sniffer is a
    SUBPROCESS -- there is no shared state to have. Cheap enough at human cadence: a mark
    happens once per narration step, not per packet.
    """
    t = None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"wire"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(r, dict) and r.get("kind") == "wire" and "t" in r:
                    t = r["t"]
    except OSError:
        return None
    return t


def read_marks(path):
    """[{n, label, wall, perf, wire_t}, ...] in file order. [] when there is no file."""
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(r, dict) and r.get("kind") == "mark":
                    out.append(r)
    except OSError:
        return []
    return out


def mark_skew(meta, marks):
    """Per-mark skew in seconds between the two channels, and the order check.

    Returns `(rows, problems)`. A row is `(n, label, wall_t, wire_t, skew)` where
    `wall_t` is the mark's absolute time converted into capture-relative seconds via the
    epoch, and `skew = wall_t - wire_t`. A perfectly bound capture has every skew equal to
    the same small constant -- NOT zero, because `wire_t` is the last segment SEEN, which
    is always a little behind the instant the mark was taken.

    So the number that matters is the SPREAD, not the offset. `problems` names what could
    not be checked or what disagrees:

      * no epoch in the capture (pre-2026-08-11) -- nothing can be bound, say so
      * marks out of order on either channel -- the two disagree about what happened
        first, which no averaging can fix
      * a wall-clock interval and a perf interval that disagree by more than a second --
        the wall clock moved under us
    """
    t0 = capture_epoch(meta)
    problems = []
    if t0 is None:
        return [], ["the capture carries no t0_wall: its timestamps cannot be placed on "
                    "any clock but their own, so no binding is possible"]
    rows = []
    for m in marks:
        w, wt = m.get("wall"), m.get("wire_t")
        if not isinstance(w, (int, float)) or not isinstance(wt, (int, float)):
            problems.append(f"mark {m.get('n')} is missing a channel")
            continue
        rel = w - t0
        rows.append((m.get("n"), m.get("label"), rel, wt, rel - wt))

    for a, b in zip(rows, rows[1:]):
        if b[2] < a[2]:
            problems.append(f"marks {a[0]} and {b[0]} are out of order on the wall clock")
        if b[3] < a[3]:
            problems.append(f"marks {a[0]} and {b[0]} are out of order on the wire clock")

    for a, b in zip(marks, marks[1:]):
        pa, pb = a.get("perf"), b.get("perf")
        # A MISSING FIELD IS NOT A MOVED CLOCK, and the first version of this said it was.
        # Defaulting the absent perf to 0 made `dp` the difference of two zeros, so any
        # real elapsed wall time exceeded the threshold and the operator was told their
        # clock had jumped. A wrong diagnosis sends someone hunting an NTP event that
        # never happened; say what is actually true instead.
        if not isinstance(pa, (int, float)) or not isinstance(pb, (int, float)):
            problems.append(
                f"marks {a.get('n')} and {b.get('n')}: no perf clock, so a wall-clock "
                f"jump between them cannot be ruled out either way")
            continue
        dw = b.get("wall", 0) - a.get("wall", 0)
        dp = pb - pa
        if abs(dw - dp) > 1.0:
            problems.append(
                f"between marks {a.get('n')} and {b.get('n')} the wall clock advanced "
                f"{dw:.3f}s but perf_counter advanced {dp:.3f}s -- the wall clock moved")
    return rows, problems


class MultiConnectionError(Exception):
    """A capture holds more than one TCP connection, so there is no single stream to read.

    Raised rather than papered over: reassemble() anchors on the lowest sequence number it
    sees, so merging two connections places one of them at an arbitrary offset in the
    other's stream. The result is a plausible-looking byte string that decrypts to nothing,
    which is the worst failure shape available -- it looks like a crypto bug.
    """


def load_wire(path):
    """Read a SINGLE-connection wire capture into (meta, {C2S, S2C}, gaps). For replay.

    Refuses a multi-connection capture by name; use load_connections() for those.
    """
    meta, conns = load_connections(path)
    if len(conns) > 1:
        raise MultiConnectionError(
            f"{os.path.basename(path)} holds {len(conns)} TCP connections "
            f"({', '.join(str(k) for k in sorted(conns, key=str))}). "
            f"Reassembling them as one stream would interleave two sequence spaces. "
            f"Use load_connections(), or pick one with pick_connection().")
    entry = next(iter(conns.values()), None)
    if entry is None:
        return meta, {C2S: b"", S2C: b""}, {C2S: [], S2C: []}
    return meta, {C2S: entry[C2S], S2C: entry[S2C]}, entry["gaps"]


# ------------------------------------------------------------ WinDivert layer --
class WinDivertError(SystemExit):
    """The driver could not be used. Never a silent no-op -- a capture that records
    nothing must say why, or a live run looks like it worked and produced an empty file."""


def _windivert_dir():
    """The vault home for the WinDivert binaries, if present. Kept out of the repo -- a
    third-party binary never enters git, only the vault (see tools/windivert/PROVENANCE)."""
    try:
        import vaultpath
        d = vaultpath.vault_path("tools", "windivert")
    except (ImportError, SystemExit):
        return None
    return d if os.path.isfile(os.path.join(d, "WinDivert.dll")) else None


def _load_windivert():
    import ctypes
    from ctypes import wintypes
    d = _windivert_dir()
    try:
        if d:
            # so the loader finds WinDivert64.sys sitting next to the DLL, and any deps.
            os.add_dll_directory(d)
            dll = ctypes.WinDLL(os.path.join(d, "WinDivert.dll"), use_last_error=True)
        else:
            dll = ctypes.WinDLL("WinDivert.dll", use_last_error=True)
    except OSError:
        raise WinDivertError(
            "WinDivert.dll not loadable. The off-wire capture needs it (CLAUDE.md carve-out,\n"
            "PLAN.md §6.1). Expected at vault/tools/windivert/ (WinDivert.dll +\n"
            "WinDivert64.sys), and the first capture must run from an ELEVATED shell -- the\n"
            "first WinDivertOpen loads a kernel driver. Source: the official\n"
            "github.com/basil00/WinDivert release (LGPLv3).")
    dll.WinDivertOpen.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int16,
                                  ctypes.c_uint64]
    dll.WinDivertOpen.restype = wintypes.HANDLE
    dll.WinDivertRecv.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_uint,
                                  ctypes.POINTER(ctypes.c_uint), ctypes.c_void_p]
    dll.WinDivertRecv.restype = wintypes.BOOL
    dll.WinDivertClose.argtypes = [wintypes.HANDLE]
    return dll, ctypes, wintypes


def _filter(server_ip, server_ports):
    # Parenthesised deliberately: WinDivert's `and` binds tighter than `or`, so without the
    # groups this would read as "(tcp and SrcAddr) or DstAddr" and sniff unrelated traffic.
    ports = " or ".join(f"tcp.SrcPort == {p} or tcp.DstPort == {p}"
                        for p in sorted(server_ports))
    if server_ip is None:
        # Port-only: the live case, where the address is not knowable until the client has
        # already connected -- and by then the plaintext handshake has been and gone.
        #
        # `ip or ipv6`, deliberately, even though parse_ipv4_tcp handles only IPv4. An
        # IPv6-only filter clause would drop those packets in the KERNEL, where nothing can
        # see them, and the symptom is a silent zero-byte capture indistinguishable from
        # "the client used another port" -- which is exactly the ambiguity that cost a
        # session on 2026-08-07. Received and then rejected by the parser, they show up in
        # the watchdog as recv > 0 with parsed == 0, which names the cause on the spot.
        # Building the v6 parser is then a known job rather than a guess.
        return f"(ip or ipv6) and tcp and ({ports})".encode()
    return (f"ip and tcp and (ip.SrcAddr == {server_ip} or ip.DstAddr == {server_ip}) "
            f"and ({ports})").encode()


def capture_session(pid, server_ip, server_ports, out_path, seconds=0, clock=time.perf_counter):
    """Sniff the client's connection to the server and record it. Driver-dependent.

    Finds the client's own connection via tcptable to fill the capture's metadata, opens a
    WinDivert SNIFF handle filtered to the server endpoint, and records every TCP segment's
    payload with its sequence number and 4-tuple until `seconds` elapses.

    `server_ip=None` sniffs the given ports on ANY host -- the live mode. A live session
    opens several connections (portal, auth, and the game server on a different address),
    so every segment carries its endpoints and load_connections() separates them again.
    """
    dll, ctypes, _ = _load_windivert()
    # pid is optional: the filter is by endpoint, so a capture can start BEFORE the client
    # connects (which is how a dry-run catches the handshake). pid only labels the metadata.
    conns = ([c for c in tcptable.connections(pid)
              if server_ip is None or c["remote"].rsplit(":", 1)[0] == server_ip]
             if pid else [])
    client = conns[0]["local"] if conns else (f"pid{pid}" if pid else "unknown")
    server = (f"{server_ip}:{sorted(server_ports)[0]}" if server_ip
              else "*:" + ",".join(str(p) for p in sorted(server_ports)))

    INVALID = ctypes.c_void_p(-1).value
    handle = dll.WinDivertOpen(_filter(server_ip, server_ports), 0, 0, 0x0001)  # SNIFF
    if handle == INVALID or handle is None:
        err = ctypes.get_last_error()
        raise WinDivertError(
            f"WinDivertOpen failed (WinError {err}). The usual cause is a non-elevated\n"
            f"shell -- loading the driver needs admin. Re-run elevated.")

    fh, record = open_capture(out_path, client, server, pid, set(server_ports), clock)
    buf = (ctypes.c_char * 65535)()
    recv_len = ctypes.c_uint(0)
    addr = (ctypes.c_char * 64)()        # WINDIVERT_ADDRESS; contents unused (see docstring)
    deadline = clock() + seconds if seconds else None
    n = 0
    stats = {"recv": 0, "parsed": 0, "directed": 0, "recorded": 0}

    # A WATCHDOG, because WinDivertRecv BLOCKS with no timeout. If nothing ever matches the
    # filter this loop parks in the kernel forever: the `seconds` deadline is only tested at
    # the top, so it never fires either, and the process sits there looking healthy while
    # recording nothing. That is exactly what a live session did on 2026-08-07 -- ten
    # minutes, nine keys tapped, `wire: 0 KiB` throughout, and a post-mortem log that was
    # COMPLETELY EMPTY because nothing here ever writes unless a packet arrives.
    #
    # So a separate thread reports the counters on a timer, to stderr, which the driver
    # captures into wirecapture.log. Silence stops being ambiguous: either the log says
    # packets are arriving, or it says none are and names the filter.
    import threading
    stop_watch = threading.Event()

    def watch():
        quiet = 0
        while not stop_watch.wait(15):
            quiet += 15
            if stats["recv"] == 0:
                print(f"[watchdog] {quiet}s: WinDivertRecv has returned ZERO packets. The "
                      f"filter is {_filter(server_ip, server_ports).decode()!r} -- if the "
                      f"client is connected, it is not matching this (IPv6 is not covered "
                      f"by `ip and tcp`).", file=sys.stderr, flush=True)
            else:
                print(f"[watchdog] {quiet}s: recv={stats['recv']} parsed={stats['parsed']} "
                      f"directed={stats['directed']} recorded={stats['recorded']}",
                      file=sys.stderr, flush=True)
    threading.Thread(target=watch, daemon=True).start()
    try:
        while True:
            if deadline and clock() > deadline:
                break
            if not dll.WinDivertRecv(handle, buf, 65535, ctypes.byref(recv_len),
                                     ctypes.byref(addr)):
                continue
            stats["recv"] += 1
            pkt = parse_ipv4_tcp(bytes(buf[:recv_len.value]))
            if not pkt:
                continue
            stats["parsed"] += 1
            d = direction_of(pkt, server_ip, server_ports)
            if d is None:
                continue
            stats["directed"] += 1
            if pkt["payload"]:
                record(d, pkt["seq"], pkt["payload"], pkt)
                stats["recorded"] += 1
                n += 1
    finally:
        stop_watch.set()
        dll.WinDivertClose(handle)
        fh.close()
        print(f"[wirecapture] closed: recv={stats['recv']} parsed={stats['parsed']} "
              f"directed={stats['directed']} recorded={stats['recorded']}",
              file=sys.stderr, flush=True)
    return n, out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, default=0,
                    help="the client process (optional; only labels the metadata -- the "
                         "filter is by endpoint, so capture can start before it connects)")
    ap.add_argument("--server", default=None,
                    help="server ip:port to sniff. Omit for the LIVE case and pass --ports "
                         "instead: the address is unknown until the client connects, and by "
                         "then the plaintext handshake is already past")
    ap.add_argument("--ports", default="", help="server ports, comma-separated")
    ap.add_argument("--seconds", type=int, default=0, help="stop after N seconds (0 = until closed)")
    ap.add_argument("--out", required=True, help="capture file to write")
    a = ap.parse_args()
    ports = {int(p) for p in a.ports.split(",") if p.strip()}
    ip = None
    if a.server:
        ip, _, port = a.server.rpartition(":")
        ports |= {int(port)}
    if not ports:
        raise SystemExit("name the ports to sniff: --server <ip:port> and/or --ports 6112,6601")
    n, path = capture_session(a.pid, ip, ports, a.out, a.seconds)
    print(f"recorded {n} segments to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
