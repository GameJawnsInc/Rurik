"""The CLIENT half of a live capture, decoded and timed.

    python toolkit/authsrv/cmsgstream.py 20260810T235916

WHY THIS EXISTS. Until 2026-08-11 nobody had read the client-to-server side of a
live capture at all, and two things were in the way.

FIRST, THE OPCODES CARRY BIT 0x8000. MsgConn's send computes the wire opcode as
`((conn+0x54) != 0 ? 0x8000 : 0) | msg[0]`, so on the game channel every opcode
the client transmits has that bit set. Without masking it off, nothing decodes --
not one message. With it, both live captures decode to their exact byte count.
This is also where `studies/divergence` D4's mysterious client reply `0x8009`
came from: it is GAME_CMSG 0x0009 with the bit.

SECOND, THE ASSEMBLED CAPTURE HAS NO TIMES. `livesession.assemble` writes one
c2s blob per connection, so message ORDER survives and timing does not. Timing is
what lets a narrated session be used as a labelled run -- the operator writes
down what they did, the server's own messages date the map transfers and the
kills, and every client message can then be matched to an action. So this rebuilds
it: the wire log has a timestamp per TCP segment, segments reassemble in seq
order, and ARC4 runs continuously over the result -- therefore plaintext offset P
sits at stream offset P + len(handshake), and the segment covering that offset
carries its time.

THE AUTH CHANNEL IS A DIFFERENT CHANNEL and must not be decoded as GAME_CMSG.
Getting this wrong is not loud: the first scratchpad version of this reader fed
the auth connection through the GAME_CMSG tables and produced two confident
"opcodes" (0x0001, 0x0005) that are not GAME_CMSG messages at all. They reached a
naming pass as real opcodes and were only caught because a reviewer checked which
connection they came from. Connections are filed by channel here, from the
capture's own file names, and `timed()` refuses to guess.

READ ONLY. Opens vault captures for reading and writes nothing.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import livesession  # noqa: E402
import vaultpath  # noqa: E402
import wirecapture  # noqa: E402
from codec import Codec  # noqa: E402

CMSG_MASK = 0x8000
_CODEC = None


def codec():
    global _CODEC
    if _CODEC is None:
        _CODEC = Codec(overrides=os.path.join(
            os.path.dirname(os.path.dirname(HERE)), "schema", "overrides.json"))
    return _CODEC


def capture_dir(stamp):
    return os.path.join(str(vaultpath.require_dir()), "captures", "live", stamp)


def _channels(cap_dir):
    """{connection: 'game'|'auth'}, from the capture's own file names.

    The assembled files are named `game-<a>_<p>-to-<b>_<q>.jsonl`, which is the
    capture's own record of which channel a connection carried. Deriving it any
    other way -- by port, by guessing -- is what produced two fictitious opcodes.
    """
    out = {}
    for fn in os.listdir(cap_dir):
        if not fn.endswith(".jsonl"):
            continue
        kind = fn.split("-", 1)[0]
        if kind not in ("game", "auth"):
            continue
        body = fn[len(kind) + 1:-len(".jsonl")]
        try:
            a, b = body.split("-to-")
            src, sport = a.rsplit("_", 1)
            dst, dport = b.rsplit("_", 1)
        except ValueError:
            continue
        out[f"{src}:{sport}->{dst}:{dport}"] = kind
    return out


def _key_for(cap_dir, conn):
    for fn in os.listdir(cap_dir):
        if not fn.endswith(".jsonl"):
            continue
        want = conn.replace(":", "_").replace("->", "-to-")
        if want not in fn:
            continue
        for line in open(os.path.join(cap_dir, fn), encoding="utf-8"):
            r = json.loads(line)
            if r.get("kind") == "session_key":
                return bytes.fromhex(r["arc4_key"])
    return None


def timed(stamp, want_dir="c2s", channel="game"):
    """[(t, conn, opcode, values), ...] on ONE clock, for one channel.

    `channel` is not optional and defaults to the game channel on purpose: an
    auth connection decoded against the GAME_CMSG tables yields plausible
    garbage rather than an error.
    """
    cap_dir = capture_dir(stamp)
    chan = _channels(cap_dir)
    segs = collections.defaultdict(list)
    for line in open(os.path.join(cap_dir, "wire.jsonl"),
                     encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(r, dict) or r.get("kind") != "wire":
            continue
        if r.get("dir") != want_dir:
            continue
        segs[str(wirecapture.conn_key(r))].append(
            (int(r["seq"]), float(r["t"]), bytes.fromhex(r.get("payload", ""))))

    ch_name = "GAME_CMSG" if want_dir == "c2s" else "GAME_SMSG"
    mask = CMSG_MASK if want_dir == "c2s" else 0
    out = []
    for conn, rows in segs.items():
        if chan.get(conn) != channel:
            continue                      # wrong channel, or not a keyed stream
        stream, _gaps = wirecapture.reassemble([(q, p) for q, _t, p in rows])
        if not stream:
            continue
        try:
            if want_dir == "c2s":
                _a, cipher = livesession.split_c2s(stream)
            else:
                _seed, cipher = livesession.split_s2c(stream)
        except Exception:
            continue
        key = _key_for(cap_dir, conn)
        if not key:
            continue
        plain = livesession.decrypt_stream(cipher, key)
        handshake = len(stream) - len(cipher)

        origin = min(q for q, _t, _p in rows)
        marks = sorted(((q - origin) & 0xFFFFFFFF, t) for q, t, p in rows if p)

        def t_at(off, _m=marks):
            best = _m[0][1]
            for o, t in _m:
                if o <= off:
                    best = t
                else:
                    break
            return best

        off = 0
        while off < len(plain):
            try:
                op, vals, nxt = codec().decode_one(ch_name, plain, off, mask)
            except Exception:
                break
            out.append((t_at(handshake + off), conn, op, vals))
            off = nxt
    out.sort(key=lambda r: r[0])
    return out


def main():
    stamp = sys.argv[1] if len(sys.argv) > 1 else "20260810T235916"
    ov = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                     "schema", "overrides.json"),
                        encoding="utf-8"))["channels"]["GAME_CMSG"]
    c2s = timed(stamp, "c2s")
    hist = collections.Counter(op for _t, _c, op, _v in c2s)
    print(f"{stamp}: {len(c2s)} GAME_CMSG over "
          f"{len({c for _t, c, _o, _v in c2s})} game connection(s), "
          f"{len(hist)} distinct opcodes")
    for op, n in hist.most_common():
        rec = ov.get(str(op))
        print(f"  0x{op:04X}  x{n:<5} {rec['name'] if rec and 'name' in rec else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
