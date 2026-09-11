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

AND THEN THIS FILE DID IT ANYWAY, FOR TWO DAYS. The paragraph above was written
on 2026-08-11 and the code under it picked the catalog from DIRECTION alone --
`"GAME_CMSG" if want_dir == "c2s" else "GAME_SMSG"` -- so the `channel` argument
it accepts, documents and refuses to default was used to FILTER connections and
never to choose the tables. Asking for the auth channel got you the auth
connection decoded as GAME_CMSG: exactly the two fictitious opcodes the docstring
warns about, delivered by the function whose docstring warns about them. It was
invisible because the failure is quiet -- 2 messages come back instead of 17, a
plausible-looking number, and the framing simply stops. `CATALOGS` below is the
fix and `frame_report()` is what makes it checkable: with the right tables all
four auth connections frame to residual **0** in both directions (78 c2s / 4,075 B,
91 s2c / 3,939 B, 8 of 8 clean), and with the GAME tables **0 of 8** survive, each
dying within 3-9 bytes. That two-sided figure is the measurement; "the auth stream
decodes" on its own would also be true of a decoder that frames anything.

THE MASK IS NOT PART OF THE DIFFERENCE, which is worth stating because it looks
like it should be. `AUTH_CMSG_MASK` (authsrv.py:112) and the game channel's mask
are both 0x8000, and the four auth connections confirm it from the wire: every
c2s raw header has bit 0x8000 set, every s2c header has it clear. Only the
catalog differs -- which is also what `authsrv.py`'s own framing comment says at
its `frame_pending` call site.

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
import vaultpath  # noqa: E402
import wirecapture  # noqa: E402
# `wiresplit`, not `livesession`. All three names used below -- split_c2s, split_s2c,
# decrypt_stream -- are pure bytes-in/bytes-out, and this module is imported by nine
# analysis modules; importing the live driver to reach them loaded `accounts`, `marks`
# and the whole orchestration onto every one of them, and pushed `clientpatch` and
# `mapdata` onto `sys.path` behind them. MEASURED after this line changed: `import
# cmsgstream` loads none of those four and neither directory is on `sys.path`.
# `livesession` re-exports the same three, so either spelling works and this one is
# cheaper. `SplitError` identity is not load-bearing here: both call sites below are
# wrapped in `except Exception`.
import wiresplit  # noqa: E402
from codec import Codec  # noqa: E402

CMSG_MASK = 0x8000

# Which message catalog a (channel, direction) pair is written in.
#
# This table exists so the choice cannot be made from direction alone, which is
# how the auth channel spent two days being read as GAME_CMSG (see the module
# docstring). A dict rather than a conditional because the missing case is then
# a KeyError with all four keys in it, not a silent fall-through to the game
# tables -- and falling through to the game tables is the entire defect.
CATALOGS = {
    ("game", "c2s"): "GAME_CMSG",
    ("game", "s2c"): "GAME_SMSG",
    ("auth", "c2s"): "AUTH_CMSG",
    ("auth", "s2c"): "AUTH_SMSG",
}

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


def catalog_for(channel, want_dir):
    """The message catalog for one (channel, direction). Refuses to guess.

    Raises on any pair `CATALOGS` does not name, rather than returning a default:
    a wrong catalog does not error at decode time, it invents, so the only place
    this can fail safely is here.
    """
    try:
        return CATALOGS[(channel, want_dir)]
    except KeyError:
        raise ValueError(
            f"no catalog for channel={channel!r} dir={want_dir!r}; "
            f"known: {sorted(CATALOGS)}")


def _streams(cap_dir, want_dir, channel):
    """Yield (conn, plain, handshake, marks) for every keyed stream on `channel`.

    ONE preparation path, shared by `timed` and `frame_report`. Two copies of
    reassemble-split-decrypt would be two chances to disagree about what the
    bytes even are, which would make a residual measured by one and a message
    list produced by the other incomparable.

    `marks` is [(stream offset, wire time)] for the segments that carried
    payload, so a plaintext offset can be dated: ARC4 runs continuously over the
    stream, so plaintext offset P sits at stream offset P + `handshake`.
    """
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

    for conn, rows in segs.items():
        if chan.get(conn) != channel:
            continue                      # wrong channel, or not a keyed stream
        stream, _gaps = wirecapture.reassemble([(q, p) for q, _t, p in rows])
        if not stream:
            continue
        try:
            if want_dir == "c2s":
                _a, cipher = wiresplit.split_c2s(stream)
            else:
                _seed, cipher = wiresplit.split_s2c(stream)
        except Exception:
            continue
        key = _key_for(cap_dir, conn)
        if not key:
            continue
        plain = wiresplit.decrypt_stream(cipher, key)
        handshake = len(stream) - len(cipher)
        origin = min(q for q, _t, _p in rows)
        marks = sorted(((q - origin) & 0xFFFFFFFF, t) for q, t, p in rows if p)
        yield conn, plain, handshake, marks


def _t_at(marks, off):
    """The wire time of the segment that carried stream offset `off`."""
    best = marks[0][1]
    for o, t in marks:
        if o <= off:
            best = t
        else:
            break
    return best


def timed(stamp, want_dir="c2s", channel="game", catalog=None):
    """[(t, conn, opcode, values), ...] on ONE clock, for one channel.

    `channel` is not optional and defaults to the game channel on purpose: an
    auth connection decoded against the GAME_CMSG tables yields plausible
    garbage rather than an error. Until 2026-08-13 that promise was not kept --
    the catalog came from `want_dir` and `channel` only filtered connections, so
    `channel="auth"` returned 2 fictitious GAME_CMSG messages where the stream
    holds 17 real AUTH_CMSG ones. See the module docstring.

    `catalog` OVERRIDES that choice and exists for one caller: the negative
    control in `test_cmsgnames.py`, which has to reproduce the wrong-catalog
    decode on purpose. Before the fix that control got its mis-decode for free
    from the defect; with the defect gone it has to ask, or it would go green
    for a new reason -- "the auth stream decodes correctly" is not evidence that
    decoding it wrongly invents. Nothing else should pass this.
    """
    ch_name = catalog or catalog_for(channel, want_dir)
    mask = CMSG_MASK if want_dir == "c2s" else 0
    out = []
    for conn, plain, handshake, marks in _streams(
            capture_dir(stamp), want_dir, channel):
        # `decode_stream_at`, never a decode_one loop of our own: codec.py calls
        # it "the one framing loop", and a second one here would be a second
        # chance to disagree about where a message ends.
        msgs, _consumed, _err = codec().decode_stream_at(ch_name, plain, mask)
        for off, op, vals in msgs:
            out.append((_t_at(marks, handshake + off), conn, op, vals))
    out.sort(key=lambda r: r[0])
    return out


def frame_report(stamp, want_dir="c2s", channel="game", catalog=None):
    """Per-connection framing ARITHMETIC: does this catalog account for the bytes?

    One row per keyed connection:
        {conn, catalog, plain, consumed, residual, messages, opcodes, headers, error}

    `residual` is the load-bearing field and the reason this is separate from
    `timed`. `timed` returns whatever it managed to frame and says nothing about
    what it left on the floor, so a catastrophically wrong catalog and a correct
    one both come back as "a list of messages" -- which is precisely how the auth
    channel read as 2 GAME_CMSG messages for two days without anyone noticing.
    A residual of 0 over a whole decrypted stream is a claim the bytes can
    refute: every message's declared shape has to consume exactly its own bytes,
    all the way to the last one, with nothing left over.

    `headers` is the set of RAW header words, before masking, so a caller can
    check the mask against the wire rather than against our own constant.
    """
    ch_name = catalog or catalog_for(channel, want_dir)
    mask = CMSG_MASK if want_dir == "c2s" else 0
    rows = []
    for conn, plain, _hs, _marks in _streams(
            capture_dir(stamp), want_dir, channel):
        msgs, consumed, err = codec().decode_stream_at(ch_name, plain, mask)
        rows.append({
            "conn": conn,
            "catalog": ch_name,
            "plain": len(plain),
            "consumed": consumed,
            "residual": len(plain) - consumed,
            "messages": len(msgs),
            "opcodes": sorted({op for _o, op, _v in msgs}),
            "headers": sorted({v[0] for _o, _op, v in msgs if v}),
            "error": err,
        })
    return rows


def main():
    """python toolkit/authsrv/cmsgstream.py [stamp] [game|auth]

    Prints the residual per connection first. That is not decoration: a catalog
    that cannot frame a stream still returns a message list, and the histogram
    of a mis-framed stream looks exactly like the histogram of a real one. The
    residual is the only line here that can say the run is wrong.
    """
    stamp = sys.argv[1] if len(sys.argv) > 1 else "20260810T235916"
    channel = sys.argv[2] if len(sys.argv) > 2 else "game"
    ch_name = catalog_for(channel, "c2s")
    ov = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                     "schema", "overrides.json"),
                        encoding="utf-8"))["channels"].get(ch_name, {})
    for row in frame_report(stamp, "c2s", channel):
        flag = "clean" if row["residual"] == 0 else f"RESIDUAL {row['residual']} B"
        print(f"  {row['conn']}  {row['messages']} msg / "
              f"{row['consumed']} of {row['plain']} B  {flag}"
              + (f"  {row['error']}" if row["error"] else ""))
    c2s = timed(stamp, "c2s", channel)
    hist = collections.Counter(op for _t, _c, op, _v in c2s)
    print(f"{stamp}: {len(c2s)} {ch_name} over "
          f"{len({c for _t, c, _o, _v in c2s})} {channel} connection(s), "
          f"{len(hist)} distinct opcodes")
    for op, n in hist.most_common():
        rec = ov.get(str(op))
        # The AUTH catalogs carry layouts and no names in overrides.json. Blank
        # is the honest print: borrowing a name from the other channel, where
        # the numbers collide and mean other things, is the mistake this whole
        # module exists to stop making.
        print(f"  0x{op:04X}  x{n:<5} {rec['name'] if rec and 'name' in rec else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
