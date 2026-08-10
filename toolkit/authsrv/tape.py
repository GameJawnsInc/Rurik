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
