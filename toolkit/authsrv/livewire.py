"""Read a capture's game connections back as decoded message streams.

RETHINK instrument #2 (studies/movement/RETHINK.md sec.4; mistakes-review
class 8). Every retail-contract number this campaign leans on -- the verbatim
click echo, the late-answer and re-click semantics (sec.0.15 S2), the D2 clip
geometry (Q7), the click-walk report-silence census (sec.0.18/R2a) -- was
measured by one-off scripts living in a session scratchpad, hardcoded to a
worktree that no longer exists. The campaign's referee was not in the repo. A
cold session could not re-run any of it without first re-deriving the wire
decode. This module IS that recipe, committed: reassemble a connection's
plaintext from its capture, prove the byte-closure, and decode both
directions through the tracked schema.

The recipe is the one `s2_d2_geo.py` proved over 20 live captures (3,072
heading-paired rows) and the R2a cadence census re-proved over 11
connections: per direction, the `game-*.jsonl` file's `frame` rows carry the
decrypted plaintext IN ORDER but without wire timing, and `wire.jsonl`
carries the timing but ciphertext; `tape._segments` aligns the two, the
handshake prefix is skipped, and the byte counts must CLOSE exactly --
`wire_bytes - handshake == len(plain)` -- or the connection is refused
loudly (`length-mismatch`), never decoded partially. A decode whose receipt
does not consume every byte is flagged, not trusted.

ORIGIN DISCIPLINE (toolkit/origin.py's own rule): every capture is stamped
ours/live/unknown and consumers must never pool origins. This loader EXPOSES
the origin of everything it opens; `live_connections()` is the gated
iterator the retail-contract work uses, and it refuses a capture whose
origin is not LIVE rather than silently including it.

Usage:
    python toolkit/authsrv/livewire.py --list
    python toolkit/authsrv/livewire.py --capture 20260817T231139
    python toolkit/authsrv/livewire.py --capture 20260817T231139 \
        --conn game-10.0.0.210_52092-to-3.228.147.153_80.jsonl
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import tape                                                    # noqa: E402
import codec as codecmod                                       # noqa: E402
import origin as originmod                                     # noqa: E402
import vaultpath                                               # noqa: E402

# The game channel's framing constants, from the recipe that measured them
# (s2_d2_geo.py over 20 captures; every connection's byte closure proves them
# again on every load -- a wrong constant here fails length-mismatch on the
# first capture, it cannot silently mis-decode).
CMSG_MASK = 0x8000
HANDSHAKE_C2S_GAME = 130
HANDSHAKE_S2C = 22

# One codec for the module: the schema is tracked in git and immutable at
# runtime, so sharing it is safe and saves the JSON parse per connection.
_CODEC = None


def _get_codec():
    global _CODEC
    if _CODEC is None:
        _CODEC = codecmod.Codec()
    return _CODEC


def captures_root():
    """The live-capture directory. May not exist on a bare machine."""
    return vaultpath.vault_path("captures", "live")


def capture_origin(capdir):
    """(who, why) for a capture directory, via its wire.jsonl."""
    wire = os.path.join(capdir, "wire.jsonl")
    if not os.path.exists(wire):
        return None, "no wire.jsonl"
    return originmod.origin_of(wire)


def connections(capdir):
    """Sorted game-connection basenames in one capture directory."""
    try:
        names = os.listdir(capdir)
    except OSError:
        return []
    return sorted(n for n in names
                  if n.startswith("game-") and n.endswith(".jsonl"))


def build_events(capdir, conn_file, direction):
    """(conn, [(t, plaintext_chunk)], err) for one direction of one connection.

    err is None only when the byte accounting CLOSES: the sum of the wire
    segments minus the handshake prefix equals the frame rows' plaintext
    exactly, and every plaintext byte is covered by a timed segment. Any
    shortfall refuses the whole connection -- a partially-timed stream would
    let a consumer date a message with another message's clock.
    """
    path = os.path.join(capdir, conn_file)
    conn = None
    plain = b""
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if r.get("kind") == "version" and r.get("connection"):
            conn = r["connection"]
        elif r.get("kind") == "frame" and r.get("direction") == direction:
            plain += bytes.fromhex(r.get("plain") or "")
    if not conn or not plain:
        return conn, None, "no-plain"
    left, right = conn.split("->")
    segs = tape._segments(os.path.join(capdir, "wire.jsonl"),
                          (left, right), direction)
    if not segs:
        return conn, None, "no-wire-segs"
    wire_bytes = sum(len(p) for _s, _t, p in segs)
    handshake = HANDSHAKE_C2S_GAME if direction == "c2s" else HANDSHAKE_S2C
    if wire_bytes - handshake != len(plain):
        return conn, None, ("length-mismatch", wire_bytes, handshake,
                            len(plain))
    events, off, skip = [], 0, handshake
    for _seq, t, payload in segs:
        if skip:
            take = min(skip, len(payload))
            payload, skip = payload[take:], skip - take
            if not payload:
                continue
        events.append((t, plain[off:off + len(payload)]))
        off += len(payload)
    if off != len(plain):
        return conn, None, ("coverage-mismatch", off, len(plain))
    return conn, events, None


def decode_conn(capdir, conn_file):
    """(conn, merged, ok) -- both directions of one connection, decoded.

    merged is [(t, "c2s"|"s2c", opcode, values)] in time order (c2s first on
    a tie, matching the send-before-answer reality of a request). ok is False
    when EITHER direction's receipt failed to consume every byte -- the
    stream is still returned so a consumer can look at what decoded, but a
    census built on ok=False data must say so.
    """
    conn, c2s_events, _c2s_err = build_events(capdir, conn_file, "c2s")
    _, s2c_events, _s2c_err = build_events(capdir, conn_file, "s2c")
    merged = []
    ok = True
    cod = _get_codec()
    if c2s_events:
        msgs, receipt = tape.decode_all(c2s_events, cod, channel="GAME_CMSG",
                                        mask=CMSG_MASK, strict=False)
        for t, op, vals in msgs:
            merged.append((t, "c2s", op, vals))
        if receipt.err is not None or receipt.consumed != receipt.total:
            ok = False
    else:
        ok = False
    if s2c_events:
        msgs, receipt = tape.decode_all(s2c_events, cod, channel="GAME_SMSG",
                                        mask=0, strict=False)
        for t, op, vals in msgs:
            merged.append((t, "s2c", op, vals))
        if receipt.err is not None or receipt.consumed != receipt.total:
            ok = False
    else:
        ok = False
    merged.sort(key=lambda r: (r[0], 0 if r[1] == "c2s" else 1))
    return conn, merged, ok


def live_connections(root=None):
    """Yield (capdir, conn_file) for every game connection in every capture
    whose origin is LIVE. Skips non-live captures LOUDLY via the returned
    skip list only when asked -- use live_captures() for the census."""
    for capdir, _who in live_captures(root):
        for gf in connections(capdir):
            yield capdir, gf


def live_captures(root=None):
    """[(capdir, who)] for origin=LIVE captures under the live root, sorted.

    Non-live and unstamped directories are EXCLUDED here; the caller that
    wants to know what was excluded calls capture_origin per directory. This
    is origin.py's refuse-to-mix rule applied at the loader: an `ours`
    capture filed under live/ must never leak into a retail census.
    """
    root = root or captures_root()
    out = []
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return out
    for name in entries:
        capdir = os.path.join(root, name)
        if not os.path.isdir(capdir):
            continue
        who, _why = capture_origin(capdir)
        if who == originmod.LIVE:
            out.append((capdir, who))
    return out


def _main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true",
                    help="census the live captures and their connections")
    ap.add_argument("--capture", help="capture dir name (under captures/live)"
                                      " or absolute path")
    ap.add_argument("--conn", help="one game-*.jsonl to decode fully")
    args = ap.parse_args()
    if args.list:
        caps = live_captures()
        print(f"live captures: {len(caps)} under {captures_root()}")
        for capdir, _who in caps:
            print(f"  {os.path.basename(capdir)}: "
                  f"{len(connections(capdir))} game connection(s)")
        return 0
    if not args.capture:
        ap.print_help()
        return 2
    capdir = (args.capture if os.path.isabs(args.capture)
              else os.path.join(captures_root(), args.capture))
    who, why = capture_origin(capdir)
    print(f"{capdir}: origin={who} ({why})")
    conns = [args.conn] if args.conn else connections(capdir)
    for gf in conns:
        conn, merged, ok = decode_conn(capdir, gf)
        n_c = sum(1 for r in merged if r[1] == "c2s")
        n_s = sum(1 for r in merged if r[1] == "s2c")
        print(f"  {gf}: conn={conn} ok={ok} c2s={n_c} s2c={n_s} "
              f"total={len(merged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
