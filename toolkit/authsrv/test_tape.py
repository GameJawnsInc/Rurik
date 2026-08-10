"""Prove a tape is the recorded stream, whole, in order, and only from a live capture.

R1.5's loader half. The player needs a client; this does not, and this is where a
wrong tape would live -- a tape that drops, duplicates or misorders bytes plays a
stream that frames into plausible nonsense, and the failure would surface as a client
assert with nothing pointing back here.

THE LOAD-BEARING PROPERTY is byte accounting. Timestamps come from the WIRE (per TCP
segment) and bytes come from the DECRYPTED channel file, so the tape only works if
the segments, minus the 22-byte SERVER_SEED handshake, account for exactly the
plaintext. One byte out and every event after it carries the wrong bytes at the right
time. load_tape refuses rather than reporting that at the end, and section 2 proves
the refusal fires.

AND ONLY FROM A LIVE CAPTURE. A tape of our own server played back to our own client
proves nothing -- it is our reconstruction on both sides of the check, which is the
exact defect CLAUDE.md names as "offline agreement between two of our own components".

standard library only.

    python toolkit/authsrv/test_tape.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import origin  # noqa: E402
import tape  # noqa: E402
import vaultpath  # noqa: E402

LEDGER = checks.Ledger("tape", floor=8)

LIVE_CAPTURE = "20260807T143055"


def write_capture(root, *, who=origin.LIVE, s2c_pieces=(), handshake=b"\x01\x16" + b"S" * 20,
                  short_by=0):
    """A minimal capture directory: wire.jsonl plus one decrypted game channel."""
    os.makedirs(root, exist_ok=True)
    conn = "10.0.0.9:5000->3.65.1.1:80"
    left, right = conn.split("->")
    lh, lp = left.split(":")
    rh, rp = right.split(":")
    with open(os.path.join(root, "wire.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(origin.record("test_tape.py", who)) + "\n")
        fh.write(json.dumps({"kind": "wire_meta", "client": left, "server": right,
                             "pid": 0, "server_ports": [80]}) + "\n")
        seq = 1000
        for i, piece in enumerate((handshake,) + tuple(s2c_pieces)):
            fh.write(json.dumps({"kind": "wire", "dir": "s2c", "seq": seq,
                                 "t": 10.0 + i * 0.25, "payload": piece.hex(),
                                 "src": rh, "sport": int(rp),
                                 "dst": lh, "dport": int(lp)}) + "\n")
            seq += len(piece)
    plain = b"".join(s2c_pieces)
    if short_by:
        plain = plain[:-short_by]
    with open(os.path.join(root, "game-x.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(origin.record("test_tape.py", who)) + "\n")
        fh.write(json.dumps({"kind": "version", "channel": "game",
                             "connection": conn}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                             "plain": plain.hex()}) + "\n")
    return conn


def main():
    # ---- 1. synthetic: the tape is the stream, whole and in order ---------------
    print("1. a tape reproduces the recorded stream exactly")
    pieces = [b"AAAA", b"BBBBBB", b"C", b"DDDDDDDD"]
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "cap")
        conn = write_capture(root, s2c_pieces=pieces)
        info, events = tape.load_tape(root)
        LEDGER.ok(b"".join(b for _t, b in events) == b"".join(pieces),
                  "the concatenated events ARE the plaintext, nothing lost or doubled",
                  f"{len(events)} events, {info['bytes']}B")
        LEDGER.ok(len(events) == len(pieces),
                  "one event per wire segment, and the handshake is not one of them",
                  "the 22-byte SERVER_SEED precedes the keystream and our own session "
                  "has already sent its own")
        LEDGER.ok([t for t, _b in events] == sorted(t for t, _b in events),
                  "events are in time order")
        LEDGER.ok(events[0][0] == 0.0,
                  "and the first event is t=0 -- the tape is relative, so it can be "
                  "played into a session that starts whenever", str(events[0][0]))

    # ---- 2. THE REFUSALS -------------------------------------------------------
    print("\n2. a tape that could play the wrong bytes is refused, not reported")
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "short")
        write_capture(root, s2c_pieces=pieces, short_by=3)
        try:
            tape.load_tape(root)
            why = ""
        except tape.TapeError as ex:
            why = str(ex)
        LEDGER.ok(bool(why) and "plaintext" in why,
                  "wire bytes that do not account for the plaintext are REFUSED",
                  "one byte out and every later event carries the wrong bytes at the "
                  "right time -- a stream that frames into plausible nonsense")

    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "ours")
        write_capture(root, who=origin.OURS, s2c_pieces=pieces)
        try:
            tape.load_tape(root)
            why2 = ""
        except tape.TapeError as ex:
            why2 = str(ex)
        LEDGER.ok(bool(why2) and "not live" in why2,
                  "a capture of OUR OWN server is refused as a tape source",
                  "our reconstruction on both sides of the check proves nothing")

    # ---- 3. the real tape, which is the one that will be played ----------------
    print("\n3. the Ascalon City tape from the first live capture")
    try:
        cap = vaultpath.vault_path("captures", "live", LIVE_CAPTURE)
        have = os.path.isdir(cap)
    except SystemExit:
        have = False
    if not have:
        LEDGER.skip("real tape", f"no live capture {LIVE_CAPTURE} in this vault")
    else:
        info, events = tape.load_tape(cap)
        LEDGER.ok(info["origin"] == origin.LIVE and info["bytes"] == 74319,
                  "the default tape is Ascalon City: 74,319 B of ArenaNet plaintext",
                  f"{info['connection']} -- {info['events']:,} events, "
                  f"{info['seconds']:.1f}s")
        burst = sum(len(b) for t, b in events if t <= 0.79)
        LEDGER.ok(0.30 <= burst / info["bytes"] <= 0.38,
                  "and its instance load really is a burst: ~34% of bytes in 0.79s",
                  f"{burst:,} of {info['bytes']:,} = {100 * burst / info['bytes']:.1f}% "
                  f"-- a player that spaces messages evenly would get this wrong")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
