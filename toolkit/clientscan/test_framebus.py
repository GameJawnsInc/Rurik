#!/usr/bin/env python3
"""Check the frame-bus scanner, and the quest pairing eleven names now rest on.

    python toolkit/clientscan/test_framebus.py

WHAT EARNS THIS FILE. `schema/overrides.json` gained twelve quest names on
2026-08-16 (rung Q1) and the evidence carrying most of them is one sentence:
"this handler body posts frame id N, and module M subscribes to N". That
sentence was produced by a scratch script. `studies/quests/FINDINGS.md` §7.9
already names that exact shape as debt -- a measurement reproducible only by
rewriting the thing that made it -- so the scan is now `framebus.py` and this is
what can turn it red.

TWO SECTIONS, AND THE SPLIT IS THE POINT.

§1 runs on a BARE MACHINE against a synthetic PE. `framebus.py` is a
fixed-byte-pattern tool, and `CLAUDE.md`'s carve-out (1) is scoped to two named
files precisely so tools like this keep working with no vault and no
disassembler. A planted image also lets the scan be tested on cases the real
client does not conveniently contain -- a subscribe that must NOT be counted as
a post, an out-of-band id that must be ignored, and the two window boundaries.

§2 runs against the pinned client if the vault is here and SKIPS loudly if it is
not. It asserts the pairing, including the two SHARED ids, which is the part a
coincidence would not produce.

THE REGRESSION THIS FILE EXISTS FOR is the call window. The `push imm32` and the
`call` that consumes it are not adjacent -- the body stages the frame payload in
between -- and a window that is too short does not error. It returns a confident
short list. §1.6's own scan used 6 bytes and silently missed two sites; 24 bytes
silently missed `0x0050`'s, whose call sits at +29. §1 plants a call at exactly
that distance and at both edges of `CALL_WINDOW`, so shrinking the constant goes
red instead of quietly un-measuring an opcode.
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks     # noqa: E402
import framebus   # noqa: E402

# MEASURED from the first green run: §1 is 14 unconditional checks, §2 is 4.
# The floor is 14 -- §1 alone -- and NOT 18, because §2 needs the vault and a
# floor above what a bare machine produces would make "the client is not here"
# indistinguishable from "the scan broke". §2 declares a skip instead, which
# checks.py prints and never scores green.
LEDGER = checks.Ledger("framebus: the quest frame-bus pairing", floor=14)
check = checks.adopt(LEDGER)

IMAGE_BASE = 0x00400000
TEXT_RVA, TEXT_OFF, TEXT_SIZE = 0x1000, 0x400, 0x400
TEXT_VA = IMAGE_BASE + TEXT_RVA
_TMP = []


def build_image(text: bytes) -> str:
    """A minimal PE32 with one .text, written to a temp file.

    `framebus.Image` walks a real section table, so the fixture has to be a real
    image -- a bag of bytes would exercise a different path from the one that
    runs on the client.
    """
    e = 0x80
    hdr = bytearray(b"\x00" * TEXT_OFF)
    hdr[0:2] = b"MZ"
    struct.pack_into("<I", hdr, 0x3C, e)
    hdr[e:e + 4] = b"PE\x00\x00"
    struct.pack_into("<H", hdr, e + 4, 0x014C)       # machine: x86
    struct.pack_into("<H", hdr, e + 6, 1)            # one section
    struct.pack_into("<H", hdr, e + 20, 0xE0)        # optional header size
    struct.pack_into("<H", hdr, e + 24, 0x010B)      # PE32
    struct.pack_into("<I", hdr, e + 52, IMAGE_BASE)
    o = e + 24 + 0xE0
    hdr[o:o + 5] = b".text"
    struct.pack_into("<I", hdr, o + 8, TEXT_SIZE)
    struct.pack_into("<I", hdr, o + 12, TEXT_RVA)
    struct.pack_into("<I", hdr, o + 16, TEXT_SIZE)
    struct.pack_into("<I", hdr, o + 20, TEXT_OFF)
    body = bytearray(hdr) + b"\x00" * TEXT_SIZE
    body[TEXT_OFF:TEXT_OFF + len(text)] = text
    fd, path = tempfile.mkstemp(suffix=".exe", prefix="framebus_")
    os.write(fd, bytes(body))
    os.close(fd)
    _TMP.append(path)
    return path


def push_call(frame_id, target, at_va, gap=0):
    """`push imm32` + `gap` filler + `call rel32`, assembled for VA `at_va`.

    The filler stands in for the real body's payload stores. `gap` is measured
    from the END of the push, so gap=0 puts the call at +5.
    """
    out = bytearray(b"\x68" + struct.pack("<I", frame_id))
    out += b"\x90" * gap
    call_va = at_va + len(out)
    out += b"\xE8" + struct.pack("<i", target - (call_va + 5))
    return bytes(out)


def main():
    print("1. the scanner, on a planted image (no vault, no client)")

    # Six planted sites, each 0x40 apart so they cannot bleed into each other.
    # ids are inside QUEST_BAND except where the case is "must be ignored".
    W = framebus.CALL_WINDOW
    plan = [
        (0x1000014E, framebus.POST,      0,      "post, call adjacent"),
        (0x1000014F, framebus.POST,      24,     "post, call at +29 -- 0x0050's real shape"),
        (0x10000151, framebus.SUBSCRIBE, 0,      "subscribe, must NOT count as a post"),
        (0x10000152, framebus.POST,      W - 6,  "post, call at the last byte inside the window"),
        (0x10000153, framebus.POST,      W,      "post, call just outside -- must read 'none'"),
        (0x20000000, framebus.POST,      0,      "out of band, must be invisible"),
    ]
    text = bytearray(b"\x00" * TEXT_SIZE)
    sites = []
    for i, (fid, tgt, gap, _why) in enumerate(plan):
        at = TEXT_VA + i * 0x40
        blob = push_call(fid, tgt, at, gap)
        text[i * 0x40:i * 0x40 + len(blob)] = blob
        sites.append(at)
    img = framebus.Image(build_image(bytes(text)))

    found = framebus.publishes(img, TEXT_VA, TEXT_VA + 0x180)
    by_id = {f: (kind, pv) for f, kind, pv, _cv in found}

    check(0x20000000 not in by_id,
          "an id outside the band is not reported",
          f"found {[hex(f) for f in by_id]} -- a scan that widened its own band "
          f"would turn every unrelated push into a frame-bus claim")
    check(len(found) == 5,
          "and the five in-band sites are all found", f"{len(found)}")
    check(by_id.get(0x1000014E) == ("post", sites[0]),
          "an adjacent push/call reads as a post")
    check(by_id.get(0x1000014F) == ("post", sites[1]),
          "a call 29 bytes past the push still reads as a post",
          "this is 0x0050's real shape and a 24-byte window missed it -- the "
          "scan returned a short list rather than an error, which is why the "
          "case is planted rather than trusted")
    check(by_id.get(0x10000151)[0] == "subscribe",
          "a call to the SUBSCRIBE helper is classified apart from a post",
          f"{by_id.get(0x10000151)} -- publishing to a band you also subscribe "
          f"to would mean something quite different, so collapsing the two to a "
          f"boolean would make the tool unable to say which it saw")
    check(by_id.get(0x10000152)[0] == "post",
          f"a call at the last byte inside CALL_WINDOW ({W}) is still found")
    check(by_id.get(0x10000153)[0] == "none",
          "and one just outside reads 'none' rather than being dropped",
          f"{by_id.get(0x10000153)} -- the boundary is asserted from BOTH "
          f"sides, so CALL_WINDOW cannot be shrunk without going red")

    posts = [f for f, kind, _p, _c in found if kind == "post"]
    check(sorted(posts) == [0x1000014E, 0x1000014F, 0x10000152],
          "so 'posts' means posts: 3 of the 5 in-band sites",
          f"{[hex(p) for p in posts]}")

    empty = framebus.publishes(img, TEXT_VA + 0x200, TEXT_VA + 0x280)
    check(empty == [],
          "a body with no bus traffic returns empty rather than raising",
          "the two measured negatives (0x004A, 0x004B) depend on this being a "
          "real answer and not a swallowed error")

    try:
        img.offset(0x7F000000)
        bad = False
    except ValueError:
        bad = True
    check(bad, "a VA in no section raises rather than returning a wrong offset",
          "silently resolving to offset 0 would make every assertion behind it "
          "a claim about the DOS header")

    check(framebus.QUEST_EXPECTED[0x0049] == framebus.QUEST_EXPECTED[0x0050],
          "the recorded pairing gives both ADDs the same frame id",
          "0x0049 and 0x0050 sharing 0x1000014E is the structural claim; if a "
          "future edit splits them, the naming argument for 0x0050 is gone")
    check(framebus.QUEST_EXPECTED[0x004C] == framebus.QUEST_EXPECTED[0x0054],
          "and both log-text messages the same one",
          "0x004C and 0x0054 share 0x1000014F")
    marker_ops = [framebus.QUEST_EXPECTED[o] for o in (0x004D, 0x0051, 0x0053)]
    check(len({tuple(m) for m in marker_ops}) == 3,
          "while the three marker ops -- one shared payload layout -- do NOT",
          f"{[[hex(x) for x in m] for m in marker_ops]}. The payload cannot "
          f"tell 0x004D, 0x0051 and 0x0053 apart; the frame id can, and that "
          f"is the whole naming argument for those three")
    check(framebus.QUEST_EXPECTED[0x004E] == [0x10000155],
          "and 0x004E posts into GmQuestComplete's band",
          "the join that renamed it from VICTORY_BANNER and retired FINDINGS "
          "7.6's 'nothing static will substitute'")

    print("\n2. the pinned client, if it is here")
    try:
        real = framebus.Image()
        have = real.pinned
        why = "" if have else f"{real.path} is not the pinned build {framebus.pinned.BUILD}"
    except Exception as exc:                                    # noqa: BLE001
        have, why = False, f"{type(exc).__name__}: {exc}"
    if not have:
        LEDGER.skip("the quest family against the real image", why or "no client")
    else:
        got = framebus.quest_family(real)
        want = {o: sorted(v) for o, v in framebus.QUEST_EXPECTED.items()}
        check(got == want,
              "all eleven quest handler bodies post what overrides.json says",
              "\n".join(f"    0x{o:04X} got {[hex(x) for x in got[o]]} "
                        f"want {[hex(x) for x in want[o]]}"
                        for o in sorted(want) if got.get(o) != want[o])
              or "n/a")
        check(got[0x0049] == got[0x0050] == [0x1000014E],
              "the two ADDs really do share an id on the client's own bytes",
              f"{got[0x0049]} / {got[0x0050]}")
        check(got[0x004A] == [] and got[0x004B] == [],
              "and the two measured negatives are still negative",
              f"0x004A {got[0x004A]}, 0x004B {got[0x004B]} -- these carry "
              f"0x004A's 'medium' confidence: the absence is what separates it "
              f"from 0x0052 QUEST_REMOVE")
        band_lo, band_hi = framebus.QUEST_BAND
        stray = framebus.publishes(real, 0x0080F250, 0x0080F290,
                                   (band_lo, band_hi))
        check(stray == [],
              "CONTROL: the negative is measured over the same window as the "
              "positives, not a narrower one",
              f"{stray} -- a negative produced by a smaller scan than the "
              f"positives would be an artefact of the scan")

    for p in _TMP:
        try:
            os.unlink(p)
        except OSError:
            pass
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
