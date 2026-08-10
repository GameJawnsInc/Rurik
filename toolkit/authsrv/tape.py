"""Turn a recorded live session into a tape: server plaintext, at recorded timing.

R1.5. `studies/divergence/FINDINGS.md` §4 is the feasibility argument; this is the
loader half of it, and it is pure -- no socket, no client, no server.

WHAT A TAPE IS. One game connection's server->client plaintext, cut at the segment
boundaries the wire capture recorded, each piece carrying the timestamp at which
ArenaNet's server actually put it on the wire. Play those pieces into a live ARC4
keystream at those intervals and a client is walked through a map by a recording.

WHY THIS WORKS AT ALL, and it is worth stating because it sounds like it should not:
a tape needs NO SEMANTICS. We do not have to understand `0x015E` to send it. The
105-opcode gap this same study measured is irrelevant here, which is the whole
reason R1.5 is worth doing before that gap is closed.

THREE THINGS IT IS NOT.

  * It is not the auth channel. 18 of 22 AUTH_SMSG messages carry a client-chosen
    request id and the client's counter is not contiguous, so a verbatim auth
    replay answers the wrong questions. The auth channel stays synthesised by our
    own server, which already echoes req_id correctly.
  * It is not a world. The 987 move messages in the tape are answers to the
    RECORDED operator's clicks. On replay the avatar walks the recorded path
    whatever the new operator does. A tape can show a load and a populated,
    animated map; it cannot show control, and anything R1.5 claims about control
    is out of scope by construction.
  * It is not re-encrypted from the capture's key. The tape is PLAINTEXT. The
    player writes it through whatever ARC4 keystream the new session negotiated,
    in order, exactly as an ordinary send does -- which is why the recorded
    session's key never leaves the vault and is not needed to play a tape.

TIMING COMES FROM THE WIRE, NOT FROM THE MESSAGES. `wire.jsonl` timestamps each TCP
segment, so the tape's resolution is per segment: map 148 has 1,210 timing points
for 3,981 messages, a median inter-segment gap of 24.4 ms, and a load burst of 800
messages in the first 0.79 s. A player that honours segment boundaries reproduces
the observed cadence to ~25 ms; one that spaces messages evenly does not, and the
burst is exactly where evenly-spaced would look wrong.

standard library only.
"""
import json
import os
import socket
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import origin  # noqa: E402

# The s2c handshake our own server writes for itself: SERVER_SEED, u16 header plus a
# 20-byte seed. It is plaintext on the wire, it precedes the keystream, and it is
# NOT part of the tape -- the player's own session has already sent its own.
HANDSHAKE_S2C = 22

C2S, S2C = "c2s", "s2c"


class TapeError(Exception):
    """A capture that cannot be turned into a tape. Never guessed past."""


def _segments(wire_path, conn, direction):
    """[(seq, t, payload)] for one connection and direction, in sequence order.

    Deduplicated by TCP seq, keeping the FIRST arrival: a retransmit carries the
    same bytes and a later timestamp, and taking the later one would invent a delay
    the client never experienced.
    """
    seen, out = set(), []
    with open(wire_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(r, dict) or r.get("kind") != "wire":
                continue
            if r.get("dir") != direction:
                continue
            if f"{r.get('src')}:{r.get('sport')}" != conn[1] and \
               f"{r.get('dst')}:{r.get('dport')}" != conn[1]:
                continue
            if f"{r.get('src')}:{r.get('sport')}" != conn[0] and \
               f"{r.get('dst')}:{r.get('dport')}" != conn[0]:
                continue
            seq = r.get("seq")
            if seq in seen:
                continue
            seen.add(seq)
            out.append((seq, float(r.get("t", 0.0)), bytes.fromhex(r.get("payload") or "")))
    out.sort(key=lambda s: s[0])
    return out


def channel_files(capture_dir):
    """The decrypted game-channel files in a capture, largest s2c first."""
    out = []
    for f in sorted(os.listdir(capture_dir)):
        if not f.startswith("game-") or not f.endswith(".jsonl"):
            continue
        path = os.path.join(capture_dir, f)
        conn, plain = None, b""
        for line in open(path, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if r.get("kind") == "version" and r.get("connection"):
                conn = r["connection"]
            elif r.get("kind") == "frame" and r.get("direction") == S2C:
                plain += bytes.fromhex(r.get("plain") or "")
        if conn and plain:
            out.append({"file": f, "path": path, "connection": conn, "s2c": plain})
    out.sort(key=lambda d: len(d["s2c"]), reverse=True)
    return out


def load_tape(capture_dir, connection=None):
    """(info, events) -- events is [(t_seconds, plaintext_bytes)] in wire order.

    `connection` selects one game channel by its "client->server" string; omitted,
    the one with the most server plaintext wins, which for the 2026-08-07 capture is
    Ascalon City (map 148).

    The correctness property, and it is checked rather than assumed: the wire
    segments for this connection, minus the handshake, must account for EXACTLY the
    decrypted plaintext -- same total length, no more and no less. If they do not,
    the byte offsets that map timestamps onto plaintext are wrong, every event after
    the discrepancy carries the wrong bytes, and the tape would play a stream that
    frames into plausible nonsense. That is a failure this refuses rather than
    reports at the end.
    """
    who, why = origin.origin_of(os.path.join(capture_dir, "wire.jsonl"))
    if who != origin.LIVE:
        raise TapeError(
            f"refusing to build a tape from a capture that is not live: {who} ({why}). "
            f"A tape of our own server played back to our own client proves nothing -- "
            f"it is our reconstruction on both sides of the check.")

    chans = channel_files(capture_dir)
    if not chans:
        raise TapeError(f"no decrypted game channel in {capture_dir}")
    if connection:
        chans = [c for c in chans if c["connection"] == connection]
        if not chans:
            raise TapeError(f"no game channel for connection {connection!r}")
    chan = chans[0]

    left, right = chan["connection"].split("->")
    segs = _segments(os.path.join(capture_dir, "wire.jsonl"), (left, right), S2C)
    if not segs:
        raise TapeError(f"no s2c wire segments for {chan['connection']}")

    wire_bytes = sum(len(p) for _s, _t, p in segs)
    plain = chan["s2c"]
    if wire_bytes - HANDSHAKE_S2C != len(plain):
        raise TapeError(
            f"{chan['connection']}: {wire_bytes} wire bytes minus a {HANDSHAKE_S2C}-byte "
            f"handshake is {wire_bytes - HANDSHAKE_S2C}, but the decrypted plaintext is "
            f"{len(plain)}. The timestamp-to-byte mapping would be wrong from the first "
            f"discrepancy onward, so this is refused rather than played.")

    events, off, skip, t0 = [], 0, HANDSHAKE_S2C, None
    for _seq, t, payload in segs:
        if skip:
            take = min(skip, len(payload))
            payload, skip = payload[take:], skip - take
            if not payload:
                continue
        if t0 is None:
            t0 = t
        events.append((round(t - t0, 6), plain[off:off + len(payload)]))
        off += len(payload)
    if off != len(plain):
        raise TapeError(f"tape covered {off} of {len(plain)} plaintext bytes")

    info = {
        "capture": os.path.basename(capture_dir),
        "connection": chan["connection"],
        "file": chan["file"],
        "events": len(events),
        "bytes": len(plain),
        "seconds": events[-1][0] if events else 0.0,
        "origin": who,
    }
    return info, events


# The two messages that end a tape by taking the client OUT of the map.
#
#   0x01A5  a 24-byte blob that is a sockaddr_in: family 2, port 6112 big-endian,
#           then the IPv4 address. OBSERVED 2026-08-10 and CHECKED AGAINST THE
#           CAPTURE ITSELF -- Ascalon's names 54.198.7.73 and the capture's next
#           connection is to 54.198.7.73; Lakeside #1's names 52.3.40.244 and the
#           next is 52.3.40.244; Ashford's names 54.198.7.73 and so is the next.
#           Three for three, from a witness we did not consult to make the claim.
#   0x0099  MAP_UPDATE_CURRENT, whose field 1 is the destination map id, agreeing
#           with the map id in the next connection's own c2s VERSION every time.
#
# A tape carrying these will make a real client dial ArenaNet, and the cage will
# refuse it. That is the correct end of a replay -- but it is fatal to anything
# meant to happen AFTER the tape, which is what a labelled run is.
# ONLY 0x01A5. `0x0099 MAP_UPDATE_CURRENT` is NOT a transfer marker and treating it as
# one truncated the Ascalon tape at byte 962 of 74,319 -- one event out of 1,209 -- because
# the client is also told its CURRENT map during the instance load, with the same opcode.
# The destination reading is only correct for the copy that follows 0x01A5. 0x01A5 itself
# appears exactly once per tape, at message 3,979 of 3,981 / 2,629 of 2,633 / 724 of 726,
# and not at all in the tape that does not leave its map. Cutting at it drops the trailing
# 0x0099 as well, because that one comes after.
TRANSFER_OPCODES = (0x01A5,)

# sizeof(sockaddr), the blob 0x01A5 carries. Same field as AUTH_SMSG 0x0009's.
SOCKADDR_LEN = 24
# What we WRITE into a rewritten handoff. The client is OBSERVED to ignore the
# advertised port on the auth-channel handoff and dial <host>:6112 -- three
# discriminating loopback runs, studies/handshake/PLAN.md §10 -- and the whole harness
# is built around that. Note what is NOT established: that observation is of the AUTH
# channel, and 0x01A5 is the GAME channel. Every recorded 0x01A5 advertises 6112, which
# is also the hardcoded value, so the live capture CANNOT tell the two apart. Hops are
# therefore separated by 127.x ALIAS rather than by port, which is correct either way;
# `--tape-rewrite-next host:port` exists so one run can settle it.
TRANSFER_PORT = 6112
# Bytes of a client's first game-channel frame needed to reach the VERSION fields:
# 4-byte header + 5 dwords (build, unk, world_id, map_id, player_id).
VERSION_HEAD = 24


def stop_before_transfer(events, codec_obj):
    """(events, dropped, why) -- the tape truncated before it leaves the map.

    Deliberately opt-in. `tape.py` is otherwise semantics-free by design (see the
    module docstring: a tape needs no semantics, which is why the 105-opcode gap does
    not block it). This is the one place semantics are needed, and they are needed
    only to decide where to STOP -- never to decide what to send.

    Truncates at EVENT granularity, dropping the whole wire segment that carries the
    transfer. Splitting it would be possible and is not worth it: the alternative is a
    partial segment whose timing no longer matches anything recorded.
    """
    off, cut = 0, None
    blob = b"".join(b for _t, b in events)
    while off < len(blob):
        try:
            op, _vals, nxt = codec_obj.decode_one("GAME_SMSG", blob, off)
        except Exception:
            break
        if op in TRANSFER_OPCODES:
            cut = off
            break
        off = nxt
    if cut is None:
        return events, 0, "no transfer in this tape"
    seen, keep = 0, []
    for t, b in events:
        if seen + len(b) > cut:
            break
        keep.append((t, b))
        seen += len(b)
    dropped = len(events) - len(keep)
    return keep, dropped, (f"cut at byte {cut:,} of {len(blob):,}, dropping the last "
                           f"{dropped} event(s) -- they hand the client to another "
                           f"server and the cage will refuse the dial")


def transfer_of(events, codec_obj):
    """The handoff message in this tape, decoded, or None if it does not leave the map.

    Returns {"offset", "host", "port", "world_id", "map_id", "player_id", "raw"}.

    0x01A5 is the GAME-channel twin of `AUTH_SMSG 0x0009 GAME_SERVER_INFO`, and that
    is a stronger claim than "it carries an address". OBSERVED: its tail carries the
    next instance's `world_id`, `map_id` and `player_id`, and all three equal what the
    NEXT connection then sends in its own c2s VERSION frame -- three hops, three for
    three, twelve fields including the address. `chain()` below re-derives that rather
    than trusting it, which is the point: the witness is the client's own next
    handshake, and it was not consulted to make the claim.

    Layout, message-relative (OBSERVED on the real bytes; the 39-byte total is
    `schema/overrides.json` GAME_SMSG[421]'s correction to the imported 38, taken from
    the client's own cmds[] table and now corroborated by ArenaNet's own stream --
    every one of the three ends exactly 39 bytes later):

        +0  u16   opcode
        +2  blob[24]  sockaddr_in: family u16 LE, port u16 BE, IPv4[4], 16 zero bytes
        +26 u32   world_id
        +30 u8
        +31 u16   map_id
        +33 u8    1, 0, 1 across the three hops (dest map 146, 164, 146). UNVERIFIED.
        +34 u32   player_id
        +38 u8
    """
    blob = b"".join(b for _t, b in events)
    off = 0
    while off < len(blob):
        try:
            op, vals, nxt = codec_obj.decode_one("GAME_SMSG", blob, off)
        except Exception:
            break
        if op in TRANSFER_OPCODES:
            sock = vals[1]
            if not isinstance(sock, bytes) or len(sock) != SOCKADDR_LEN:
                raise TapeError(
                    f"0x{op:04X} at byte {off} does not carry a {SOCKADDR_LEN}-byte "
                    f"blob where the schema says one is: got {type(sock).__name__} "
                    f"of {len(sock) if hasattr(sock, '__len__') else '?'}")
            return {
                "offset": off,
                "host": socket.inet_ntoa(sock[4:8]),
                # Family is LITTLE-endian and port is BIG-endian, in the same struct.
                # Reading the port the other way round yields a plausible number
                # thousands away from the real one, and the only symptom is a
                # connection that never arrives -- test_codec.py section 4 exists
                # because that already happened once.
                "family": struct.unpack_from("<H", sock, 0)[0],
                "port": struct.unpack_from(">H", sock, 2)[0],
                "world_id": vals[2], "map_id": vals[4], "player_id": vals[6],
                "raw": blob[off:nxt],
            }
        off = nxt
    return None


def rewrite_transfer(events, codec_obj, host, port=TRANSFER_PORT):
    """(events, changed, why) -- the handoff repointed at a server we control.

    The sibling of `stop_before_transfer`, not a replacement: truncating is still the
    right answer for a labelled run, which needs the client to stay put.

    THIS DELETES THE ONLY CONTROL THAT HAS EVER CAUGHT THIS MISTAKE, and that is why
    the checks below are not hygiene. Today an un-truncated tape fails CLOSED: the
    client dials ArenaNet, `cage.assert_launch_safe` refuses, and the client says
    `Code=005` out loud -- which is exactly what happened on 2026-08-10. After a
    rewrite, a wrong address is a dead connection and nothing says why. So the
    assertion has to happen HERE, offline, before the run, because during the run
    there is no signal left to read.

    Refuses a non-loopback host for the same reason. Without that refusal this
    function is a general-purpose "aim a client at an arbitrary server", written into
    ArenaNet's own recorded plaintext, which is the one thing `CLAUDE.md`'s launch
    rule exists to prevent.

    LENGTH-PRESERVING BY CONSTRUCTION, which is what keeps the tape's accounting
    intact. `load_tape` checks that the wire segments account for exactly the
    plaintext, and it runs before this on the untouched capture; re-cutting on the
    ORIGINAL event lengths is exact only because the byte count cannot change.
    """
    if not origin.is_loopback(host):
        raise TapeError(
            f"refusing to rewrite a tape's handoff to {host}: it is not a loopback "
            f"address. A rewritten tape is ArenaNet's own recorded bytes with a "
            f"destination of our choosing -- pointed off this machine that is a "
            f"client aimed at an arbitrary server by a file, which is what the "
            f"launch rule in CLAUDE.md exists to refuse. 127/8 only.")

    found = transfer_of(events, codec_obj)
    if found is None:
        return events, 0, "no transfer in this tape"

    blob = bytearray(b"".join(b for _t, b in events))
    before = bytes(blob)
    at = found["offset"] + 2
    new = (struct.pack("<H", socket.AF_INET) + struct.pack(">H", port)
           + socket.inet_aton(host) + b"\x00" * 16)
    if len(new) != SOCKADDR_LEN:
        raise TapeError(f"built a {len(new)}-byte sockaddr, wanted {SOCKADDR_LEN}")
    blob[at:at + SOCKADDR_LEN] = new
    after = bytes(blob)

    # Three self-checks the artifact can refute, all of them cheap and all of them
    # aimed at the failure that is otherwise silent.
    if len(after) != len(before):
        raise TapeError(
            f"the rewrite changed the tape's length ({len(before)} -> {len(after)}), "
            f"which would invalidate every event boundary after it")
    differing = [i for i in range(len(before)) if before[i] != after[i]]
    if differing and not (at <= min(differing) and max(differing) < at + SOCKADDR_LEN):
        raise TapeError(
            f"the rewrite touched bytes outside the sockaddr at "
            f"[{at}, {at + SOCKADDR_LEN}): {differing[:8]}")
    check = transfer_of([(0.0, after)], codec_obj)
    if check is None or check["host"] != host or check["port"] != port:
        raise TapeError(
            f"the rewritten tape does not read back as {host}:{port} -- got "
            f"{check and (check['host'], check['port'])}. Refusing to hand a client "
            f"a tape whose destination we cannot prove offline.")

    # Re-cut on the ORIGINAL event lengths. Exact because nothing moved.
    out, seen = [], 0
    for t, b in events:
        out.append((t, after[seen:seen + len(b)]))
        seen += len(b)
    return out, len(differing), (
        f"0x{TRANSFER_OPCODES[0]:04X} at byte {found['offset']:,} now names "
        f"{host}:{port} instead of {found['host']}:{found['port']} "
        f"({len(differing)} byte(s) changed of {len(before):,}); "
        f"destination map {found['map_id']}")


def client_version(capture_dir, connection):
    """{"build", "world_id", "map_id", "player_id"} from a connection's c2s VERSION.

    The decrypted `game-*.jsonl` does NOT carry these -- its `version` record holds
    only the connection string and which tap supplied the key -- so `wire.jsonl` is
    the only source, and this is deliberately parsed from the CLIENT's own first
    bytes rather than from anything we wrote.

    That independence is the whole value: it is what lets `chain()` confirm a link
    instead of assuming one.
    """
    wire = os.path.join(capture_dir, "wire.jsonl")
    conn = tuple(connection.split("->"))
    if len(conn) != 2:
        raise TapeError(f"not a connection string: {connection!r}")
    segs = _segments(wire, conn, C2S)
    if not segs:
        raise TapeError(f"no client bytes recorded for {connection}")
    head = b"".join(p for _s, _t, p in segs)[:VERSION_HEAD]
    if len(head) < VERSION_HEAD:
        raise TapeError(
            f"{connection}: only {len(head)} client bytes, need {VERSION_HEAD} to "
            f"read the VERSION frame. _segments sorts by raw TCP seq with no wrap "
            f"handling; a stream this short should never have wrapped, so this is a "
            f"truncated capture rather than an ordering problem.")
    build, _unk, world_id, map_id, player_id = struct.unpack_from("<5I", head, 4)
    return {"build": build, "world_id": world_id, "map_id": map_id,
            "player_id": player_id}


def chain(capture_dir):
    """[connection] in play order -- the hops of one recorded session, PROVEN.

    Follows each tape's 0x01A5 to the next connection and then REFUSES to accept the
    link unless the next connection's own VERSION frame carries the same `world_id`,
    `map_id` and `player_id` the handoff named. Ordering by timestamp would have been
    easier and would have been a guess; this is a claim the capture can refute.

    Raises rather than reporting, because a mis-ordered chain plays one map's
    recording into another map's client and the symptom is an assert with no obvious
    cause.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
    from codec import Codec
    codec_obj = Codec()

    chans = {c["connection"]: c for c in channel_files(capture_dir)}
    versions = {}
    for conn in chans:
        try:
            versions[conn] = client_version(capture_dir, conn)
        except TapeError:
            versions[conn] = None

    links, heads = {}, dict.fromkeys(chans, True)
    for conn in chans:
        _info, events = load_tape(capture_dir, conn)
        found = transfer_of(events, codec_obj)
        if found is None:
            continue
        want = (found["world_id"], found["map_id"], found["player_id"])
        matched = [c for c, v in versions.items()
                   if v and c != conn
                   and (v["world_id"], v["map_id"], v["player_id"]) == want
                   and c.split("->")[1].split(":")[0] == found["host"]]
        if len(matched) != 1:
            raise TapeError(
                f"{conn}'s handoff names {found['host']} / world {found['world_id']} "
                f"/ map {found['map_id']} / player {found['player_id']}, and "
                f"{len(matched)} recorded connection(s) match it. A chain is only a "
                f"chain if the next hop's own VERSION agrees -- refusing to guess an "
                f"order from timestamps.")
        links[conn] = matched[0]
        heads[matched[0]] = False

    starts = [c for c, is_head in heads.items() if is_head and c in links]
    if not starts:
        return []
    if len(starts) != 1:
        raise TapeError(f"{len(starts)} connections start a chain: {sorted(starts)}")
    order, seen = [starts[0]], {starts[0]}
    while order[-1] in links:
        nxt = links[order[-1]]
        if nxt in seen:
            raise TapeError(f"the chain loops back to {nxt}")
        order.append(nxt)
        seen.add(nxt)
    return order


def gaps(events):
    """[(index, seconds)] inter-event gaps, for reporting cadence honestly."""
    return [(i, round(events[i][0] - events[i - 1][0], 6))
            for i in range(1, len(events))]


def main():
    import argparse
    sys.path.insert(0, os.path.dirname(HERE))
    import vaultpath
    ap = argparse.ArgumentParser(description="Inspect a tape without playing it.")
    ap.add_argument("capture", nargs="?", help="capture dir; default: newest live")
    ap.add_argument("--connection", default=None)
    a = ap.parse_args()
    cap = a.capture
    if not cap:
        root = vaultpath.require_dir("captures", "live", why="listing tapes")
        dirs = [os.path.join(root, d) for d in os.listdir(root)
                if os.path.isdir(os.path.join(root, d))]
        cap = max(dirs, key=os.path.getmtime)
    for chan in channel_files(cap):
        try:
            info, events = load_tape(cap, chan["connection"])
        except TapeError as ex:
            print(f"  {chan['connection']}: REFUSED -- {ex}")
            continue
        g = sorted(s for _i, s in gaps(events))
        med = g[len(g) // 2] if g else 0.0
        print(f"  {info['connection']}")
        print(f"     {info['events']:,} events, {info['bytes']:,} B, "
              f"{info['seconds']:.1f}s, median gap {med * 1000:.1f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
