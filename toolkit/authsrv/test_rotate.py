"""GAME_CMSG 0x0040 is ROTATE_PLAYER, and this is the check that can take the name back.

The opcode sat unnamed for days behind one bad inference. Its field 1 is +/-infinity most
of the time, and `schema/overrides.json` reasoned that "+/-inf rules out an angle in
radians while fitting a ratio that crosses vertical". That is backwards. The infinities
are a literal SENTINEL -- the client loads them from two .rdata constants -- and the finite
values are exactly the angle. The wire had been saying so since 2026-08-04: every finite
value in the vault lies inside +/-pi, which 163 arbitrary dwords do not do.

So this file asserts the three legs the name rests on, in increasing order of how badly
they would hurt to lose:

  1. THE CATALOG. The name resolves, and both payload fields are still `dword`. That
     second half is not decoration -- the values are IEEE-754 floats and the field type
     was very nearly "fixed" to `float` on that basis. The client's own SEND table says
     u32, so a well-meaning correction there would silently break decoding of a message
     we now understand. This check exists to make that edit go red.

  2. THE CLIENT'S OWN VOCABULARY. Two constants and two strings, read out of the vaulted
     build with the standard library. The name is not ours: build 38797 range-checks the
     argument against the assert text `(rotation >= -1.0f) && (rotation <= 1.0f)` before
     sending it. If those bytes are not where we say they are, the naming evidence is
     gone and this file should say so rather than the schema quietly keeping the name.

  3. THE WIRE. Invariants over every 0x0040 in the vault, three of which the artifact can
     genuinely refute: field 2 never below the client's own 0.1 send gate, field 1 never
     NaN and never outside +/-pi when finite, and finite field-1 values agreeing with
     atan2 of a nearby 0x003D direction vector far more often than chance. The last one
     is scored against a null model computed from this same corpus, so it cannot be
     satisfied by the corpus merely being large.

WHAT THIS FILE DELIBERATELY DOES NOT CHECK. Which sign of the rotation is a left turn.
The bracketing evidence is 121/189 and 106/169 -- real, but far too weak to write down,
and a test that pinned it would be pinning a coin flip. `overrides.json` makes no
left/right claim either. One labelled run with the operator told to turn a named
direction settles it; until then it stays unwritten.

FREQUENCIES ARE NOT ASSERTED, on purpose. 536 of the 559 samples come from
`drive_client.py` clicking fixed window fractions, so the 70.8% infinity rate is a fact
about our harness and not about a player. The checks below are all invariants -- things
true of every sample -- plus one floor on the corpus size, which exists so that a capture
tree that quietly shrinks is noticed rather than making the test easier to pass.
"""
import glob
import json
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
from codec import Codec  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

ROTATE = 0x0040
HEADING = 0x003D
# 0x003D is [msg_header, vec2 POSITION, dword, vec2 DIRECTION, dword]. The two vec2s are
# easy to confuse and confusing them is silent: a position also has an atan2. Pinned by a
# check in check_catalog so a schema edit cannot move it out from under this.
HEADING_DIR = 3
CMSG_MASK = 0x8000

# The client's own send gate: it computes a turn amount and refuses to send below this.
# Measured minimum on the wire is 0.10133, just above it.
SEND_GATE = 0.1

# Two .rdata constants and two strings in build 38797. Located by searching the image for
# 0x7F800000 / 0xFF800000 and by following the assert helper's arguments -- not copied
# from any upstream. Nothing of the client's is stored here beyond these addresses and
# the short strings they point at, which is the same practice studies/srvtree already uses.
CLIENT_BUILD = "2026-07-29_221c13772c7a"
PLUS_INF_VA = 0x00948654
MINUS_INF_VA = 0x0094E538
SRCFILE_VA = 0x00A94D2C
ASSERT_VA = 0x00A95260
SRCFILE_TEXT = r"P:\Code\Gw\Char\Cli\ChCliApi.cpp"
ASSERT_TEXT = "(rotation >= -1.0f) && (rotation <= 1.0f)"

# Set from the green run of 2026-08-10 against 559 samples in 55 streams. The corpus can
# only grow (captures are append-only and never deleted), so a run finding fewer than this
# is reading less than the vault holds -- which is the failure this number exists to catch,
# not a reason to lower it.
MIN_SAMPLES = 500
MIN_STREAMS = 40
# 16 of 162 finite values matched to 1e-3 rad on 2026-08-10. Held at 10 so that ordinary
# corpus churn does not go red, while a decoder change that broke the correspondence
# entirely still would.
MIN_EXACT_MATCHES = 10

# 16 is what a green run executes here on 2026-08-10: 6 catalog + 3 image + 7 wire. It is
# set to the FULL count rather than to a mandatory core, following test_codec.py's stated
# position -- the vault is this test's ground truth and its absence is a failure, not a
# note. The skip below is still declared and printed; it just drops the run under the
# floor, which is the correct outcome, because without the client image the NAME's primary
# evidence went unchecked and a green exit code would be claiming otherwise.
LEDGER = checks.Ledger("ROTATE_PLAYER -- GAME_CMSG 0x0040", floor=16)


# ---------------------------------------------------------------- the client image
def _sections(data):
    """(image_base, [(name, vaddr, vsize, raw_ptr, raw_size)]) -- stdlib PE walk.

    Deliberately not pefile. CLAUDE.md scopes the capstone/pefile carve-out to exactly
    two files in clientscan/, and this is neither; a suite test must keep working on a
    bare machine. Reading four fixed addresses does not need a PE library.
    """
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    secs, off = [], pe + 24 + optsz
    for _ in range(nsec):
        name = data[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", data, off + 8)
        secs.append((name, va, vsz, ptr, rsz))
        off += 40
    return base, secs


def _read_va(data, base, secs, va, n):
    """`n` bytes at virtual address `va`, or None if it falls outside every section."""
    rva = va - base
    for _name, sva, vsz, ptr, rsz in secs:
        if sva <= rva < sva + max(vsz, rsz):
            start = ptr + (rva - sva)
            return data[start:start + n]
    return None


def check_client_image():
    try:
        exe = vaultpath.vault_path("client", CLIENT_BUILD, "Gw.exe")
    except Exception:
        exe = None
    if not exe or not os.path.exists(exe):
        LEDGER.skip("the client's own vocabulary",
                    f"no vaulted build {CLIENT_BUILD} on this machine -- the NAME's "
                    "primary evidence was not re-read this run")
        return

    data = open(exe, "rb").read()
    base, secs = _sections(data)

    pinf = _read_va(data, base, secs, PLUS_INF_VA, 4)
    minf = _read_va(data, base, secs, MINUS_INF_VA, 4)
    LEDGER.ok(pinf == b"\x00\x00\x80\x7f" and minf == b"\x00\x00\x80\xff",
              "the two infinity constants the sender loads are still at their addresses",
              f"0x{PLUS_INF_VA:08X}=+inf 0x{MINUS_INF_VA:08X}=-inf -- this is WHY field 1 "
              "is infinite: a sentinel the client stores, not a ratio it computed")

    for va, want, what in ((SRCFILE_VA, SRCFILE_TEXT, "source file"),
                           (ASSERT_VA, ASSERT_TEXT, "assertion text")):
        raw = _read_va(data, base, secs, va, len(want) + 8) or b""
        got = raw.split(b"\0")[0].decode("ascii", "replace")
        LEDGER.ok(got == want,
                  f"the client's own {what} is where the naming evidence says",
                  got if got == want else f"got {got!r}, wanted {want!r}")


# ---------------------------------------------------------------- the wire
def game_c2s_streams(codec):
    """[(label, [(index, opcode, values), ...]), ...] for every game-channel c2s stream.

    Two capture shapes, because they were written by different tools:
      * our own server logs one `decoded` record per client message it framed;
      * a live capture is decrypted plaintext in `frame` records and has to be framed
        here, which is also a standing check that the catalog still frames ArenaNet's
        own bytes.
    A capture is only taken as game-channel when it SAYS so -- the `version` record's
    channel field, or a `game-` filename under live/. Guessing from content would let an
    auth stream's opcode 0x40 (a different message entirely) into the corpus.
    """
    root = vaultpath.require_dir(
        "captures", why="0x0040's wire evidence is this test's ground truth")
    out = []
    for path in sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)):
        name = os.path.basename(path)
        is_live_game = os.sep + "live" + os.sep in path and name.startswith("game-")
        channel, decoded, frames = None, [], []
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue          # a capture truncated mid-write; skip the line
                    kind = e.get("kind")
                    if kind == "version":
                        channel = e.get("channel")
                    elif kind == "decoded":
                        decoded.append(e)
                    elif kind == "frame" and e.get("direction") == "c2s":
                        frames.append(e.get("plain") or "")
        except OSError:
            continue

        msgs = []
        if channel == "game" and decoded:
            for i, e in enumerate(decoded):
                op = e.get("opcode")
                if isinstance(op, int):
                    msgs.append((i, op & ~CMSG_MASK, e.get("values") or []))
        elif is_live_game and frames:
            blob = b"".join(bytes.fromhex(h) for h in frames if h)
            got, _consumed, _err = codec.decode_stream("GAME_CMSG", blob,
                                                       mask=CMSG_MASK)
            msgs = [(i, op, vals) for i, (op, vals) in enumerate(got)]
        if msgs:
            out.append((name, msgs))
    return out


def check_wire(codec):
    try:
        streams = game_c2s_streams(codec)
    except FileNotFoundError as ex:
        # Not a skip. test_codec.py made this call first and its reasoning applies
        # unchanged: a fixture the docstring calls primary is not optional, and a run
        # that never consulted it has not verified anything about this opcode.
        LEDGER.ok(False, "the vault has captures to measure 0x0040 against", str(ex))
        return

    samples = []          # (stream, index, angle, rate)
    headings = []         # every 0x003D angle in the corpus, for the null model
    per_stream_headings = {}
    hit_streams = set()
    for label, msgs in streams:
        hs = []
        for i, op, vals in msgs:
            if op == HEADING and len(vals) > HEADING_DIR:
                # vals[1] is the POSITION and vals[3] is the DIRECTION. Pairing against
                # vals[1] is a mistake that costs nothing visible -- map coordinates
                # produce a perfectly plausible atan2 -- and it scored 0 of 163 here
                # before the field list was read properly. The layout is
                # [msg_header, vec2 pos, dword, vec2 dir, dword].
                d = vals[HEADING_DIR]
                if isinstance(d, (list, tuple)) and len(d) == 2:
                    x, y = float(d[0]), float(d[1])
                    if x or y:
                        a = math.atan2(y, x)
                        hs.append((i, a))
                        headings.append(a)
            elif op == ROTATE and len(vals) >= 3:
                try:
                    angle = struct.unpack("<f", struct.pack("<I", int(vals[1])))[0]
                    rate = struct.unpack("<f", struct.pack("<I", int(vals[2])))[0]
                except (struct.error, ValueError, TypeError):
                    continue
                samples.append((label, i, angle, rate))
                hit_streams.add(label)
        per_stream_headings[label] = hs

    LEDGER.ok(len(samples) >= MIN_SAMPLES and len(hit_streams) >= MIN_STREAMS,
              "the corpus is at least the size the name was measured on",
              f"{len(samples)} samples in {len(hit_streams)} streams "
              f"(floor {MIN_SAMPLES}/{MIN_STREAMS}); {len(headings)} headings")
    if not samples:
        return

    rates = [r for _s, _i, _a, r in samples]
    LEDGER.ok(all(0.0 < r <= 1.0 for r in rates),
              "every turn amount is in (0, 1] -- the range the client asserts",
              f"min {min(rates):.8f} max {max(rates):.8f}")
    LEDGER.ok(all(r >= SEND_GATE for r in rates),
              "and none is below the client's own send gate of 0.1",
              f"min {min(rates):.8f}; the client compares against a 0.1 constant and "
              "returns without sending, so a sample under it would mean we are decoding "
              "the wrong field")

    angles = [a for _s, _i, a, _r in samples]
    LEDGER.ok(not any(math.isnan(a) for a in angles),
              "field 1 is never NaN",
              f"{sum(1 for a in angles if math.isinf(a))} infinite of {len(angles)}")
    finite = [a for a in angles if math.isfinite(a)]
    LEDGER.ok(finite and all(abs(a) <= math.pi for a in finite),
              "and every FINITE value lies inside +/-pi, as an angle in radians must",
              f"{len(finite)} finite, max |v| = {max(abs(a) for a in finite):.6f} "
              f"vs pi = {math.pi:.6f}")

    # The correspondence. For each finite angle, the nearest 0x003D in the same stream.
    exact, near, paired = 0, 0, 0
    for label, i, a, _r in samples:
        if not math.isfinite(a):
            continue
        hs = per_stream_headings.get(label) or []
        if not hs:
            continue
        _d, h = min(((abs(j - i), h) for j, h in hs), key=lambda t: t[0])
        paired += 1
        delta = abs((a - h + math.pi) % (2 * math.pi) - math.pi)
        if delta <= 1e-3:
            exact += 1
        if delta <= 0.05:
            near += 1

    LEDGER.ok(exact >= MIN_EXACT_MATCHES,
              "finite values match atan2 of a nearby heading to float32 round-off",
              f"{exact} of {paired} within 1e-3 rad (floor {MIN_EXACT_MATCHES}) -- "
              "this is the check that says field 1 IS the angle rather than merely "
              "being angle-shaped")

    # The null model, from this same corpus: pair each finite angle with a heading drawn
    # at random. Fixed seed so the number is reproducible; the point is only that the
    # real count must beat what shuffling produces.
    rng = random.Random(0x0040)
    trials = []
    for _ in range(200):
        n = 0
        for a in finite:
            h = rng.choice(headings)
            if abs((a - h + math.pi) % (2 * math.pi) - math.pi) <= 0.05:
                n += 1
        trials.append(n)
    trials.sort()
    p95 = trials[int(0.95 * (len(trials) - 1))]
    LEDGER.ok(near > p95,
              "and it beats a null model built by shuffling this same corpus",
              f"{near} within 0.05 rad vs a shuffled 95th percentile of {p95} "
              f"(median {trials[len(trials) // 2]}) -- so the agreement is not an "
              f"artifact of there being {len(headings)} headings to match against")


# ---------------------------------------------------------------- the catalog
def check_catalog(codec):
    LEDGER.ok(codec.name_for("GAME_CMSG", ROTATE) == "ROTATE_PLAYER",
              "the catalog carries the name",
              codec.name_for("GAME_CMSG", ROTATE))

    fields = codec.fields_for("GAME_CMSG", ROTATE)
    types = [f["type"] for f in fields]
    LEDGER.ok(types == ["msg_header", "dword", "dword"],
              "and both payload fields are still dword, NOT float",
              f"{types} -- the VALUES are float32, the WIRE TYPE is u32, and the "
              "client's own SEND table says u32. Changing this to float looks like a "
              "fix and is a decoding bug.")

    blob = codec.encode("GAME_CMSG", ROTATE, [0, 0], header_value=ROTATE | CMSG_MASK)
    LEDGER.ok(len(blob) == 10, "it encodes to the 10 bytes the client's table declares",
              f"{len(blob)} bytes")

    # Round-trip a real pair of values through the codec as floats-in-dwords, because
    # that is how every consumer of this message has to read it.
    angle, rate = 1.0821444988250732, 0.11885100603103638
    raw = [struct.unpack("<I", struct.pack("<f", v))[0] for v in (angle, rate)]
    wire = codec.encode("GAME_CMSG", ROTATE, raw, header_value=ROTATE | CMSG_MASK)
    got, consumed, err = codec.decode_stream("GAME_CMSG", wire, mask=CMSG_MASK)
    back = [struct.unpack("<f", struct.pack("<I", v))[0] for v in got[0][1][1:]] \
        if got else []
    LEDGER.ok(consumed == len(wire) and err is None and back == [angle, rate],
              "and a real observed (angle, rate) survives the round trip bit-exactly",
              f"{back} -- 1.08214450 rad is 62.0026 deg, the live sample, which is "
              "atan2 of the direction its own neighbouring headings carry")

    # The correspondence check below reads 0x003D's SECOND vec2. If the schema ever puts
    # a third one in, or reorders them, that check would go on comparing angles happily
    # against the wrong field and stay green -- so pin the layout here instead.
    head = [f["type"] for f in codec.fields_for("GAME_CMSG", HEADING)]
    LEDGER.ok(head == ["msg_header", "vec2", "dword", "vec2", "dword"]
              and head[HEADING_DIR] == "vec2",
              "MOVE_SET_HEADING's layout still puts the direction where we read it",
              f"{head}, direction at index {HEADING_DIR} -- index 1 is the POSITION, "
              "and pairing against it scores zero while looking entirely reasonable")

    LEDGER.ok(codec.name_for("GAME_SMSG", ROTATE) != "ROTATE_PLAYER",
              "and the name did not leak onto the server-to-client 0x0040",
              "GAME_SMSG 0x0040 is a different message ([agent_id, u32]); the two "
              "direction tables collide on this value and naming both would be wrong")


def main():
    codec = Codec()
    print("\n1. the catalog")
    check_catalog(codec)
    print("\n2. the client's own vocabulary (build 38797)")
    check_client_image()
    print("\n3. the wire")
    check_wire(codec)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
