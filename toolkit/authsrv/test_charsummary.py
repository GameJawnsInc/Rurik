"""charsummary: the character summary decoded the way the client packs it.

WHAT THIS IS REALLY CHECKING. RUN-HEROLIB-G (studies/heroes/RUN-HEROLIB.md
§21.4) found that the blob the client sent back differed from the one we
served in five bytes, four of which had NOT made it send in runs E and F. The
plausible wrong answer was "the client compares some fields and not others,
and which is which is unknowable without a run per byte". §22 read the packer
(0x009273B0), the unpacker (0x009274D0) and the dirty check (0x008711E0)
instead: the four bytes are positions the packer never writes, and the fifth
is item[4].b, which the dirty check compares. So the fixture here is the run's
OWN two blobs -- the one we served (run A's client packing, carrying residue
`ed 00 00 dc`) and the one G's client sent -- and the checks are the claims a
wrong byte map would redden:

  * the residue is reported as residue and NEVER as a field;
  * the G pair differs in exactly ['unwritten', 'items'] and the client's
    compare sees exactly ['items'];
  * a blob re-packed from its own fields (residue zeroed) is the SAME summary
    to the client -- the E/F null, with no free parameter;
  * every compared field is seen when its own bytes move, the helm bit is NOT,
    and the in-map trio is seen only in map;
  * every refusal the client's unpacker makes is made here.

No vault, no client, no server: charsummary is pure. The live corroboration
(161 retail-served summaries decoding with level 20 where the owner's
characters are level 20, and 0xDD allocator fill in exactly the unwritten
positions) is `summarycensus.py`'s and §22's, not repeated here -- live
bytes stay in the vault.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks  # noqa: E402
import charsummary as cs  # noqa: E402

led = checks.Ledger("charsummary: the byte map the dirty check reads",
                    floor=64)

# Our own loopback character's summary, as run A's client packed it and the
# store served it through runs E, F and G (RUN-HEROLIB.md §20.2; byte 59 was
# 0x0b before G flipped it). Bytes 33-36 are `ed 00 00 dc`: residue.
SERVED_A = bytes.fromhex(
    "0800940000000000000010000000000000000000000000000000000030000000"
    "05ed0000dc5d000b00135b000b00135c000b00135e000b00135a000b0013")
# What G served: byte 59, item[4].b, 0x0b -> 0x0c.
SERVED_G = bytearray(SERVED_A)
SERVED_G[59] = 0x0c
SERVED_G = bytes(SERVED_G)
# What G's client sent back (vault capture authsrv-20260916T002113-c1, the
# character_settings event at 04:21:41Z): residue zero, item[4].b back to 0x0b.
SENT_G = bytes.fromhex(
    "0800940000000000000010000000000000000000000000000000000030000000"
    "05000000005d000b00135b000b00135c000b00135e000b00135a000b0013")


def moved(offset, delta=1):
    b = bytearray(SERVED_A)
    b[offset] = (b[offset] + delta) & 0xff
    return bytes(b)


def main():
    print("charsummary: the byte map section 22 read out of the packer")

    # ---------------------------------------------------------------- §1
    print("\n§1  THE STORED BLOB DECODES TO WHAT THE RUN KNEW ABOUT IT")
    d = cs.decode(SERVED_A)
    led.ok(d["version"] == 8, "version word is 8")
    led.ok(d["length"] == 62 and d["surplus"] == 0,
           "62 bytes is exactly 0x25 + 5 * 5, no surplus")
    led.ok(d["count"] == 5, "five composite items")
    led.ok(d["last_outpost"] == 148,
           "bytes 2-3 are the map the client packed in -- our loopback "
           "outpost, 148", f"got {d['last_outpost']}")
    led.ok(d["profession"] == 1,
           "appearance nibble is Warrior, the spawn profession",
           d["profession"])
    led.ok(d["level"] == 3, "flag bits 4-8 equal the character's level, 3",
           d["level"])
    led.ok(d["items"] == [(0x5d, 0xb, 0x13), (0x5b, 0xb, 0x13),
                          (0x5c, 0xb, 0x13), (0x5e, 0xb, 0x13),
                          (0x5a, 0xb, 0x13)],
           "items are (u16, u16, u8) at 37 + 5i", d["items"])
    led.ok(d["unwritten"] == bytes.fromhex("ed0000dc"),
           "bytes 33-36 come back as residue, not as a field")
    led.ok(d["flags_unwritten"] == 0,
           "flag bits 18-31 are clear in this blob")
    led.ok(d["guild_hall_id"] == bytes(16) and d["tag"] == 0,
           "guild_hall_id and tag are zero for the loopback character")
    led.ok(d["tag_text"] is None, "a zero tag has no text")
    led.ok(cs.tag_text(cs.FRESH_TAG) == "newb",
           "the client's fresh-record tag reads as the multichar 'newb'")
    led.ok(cs.tag_text(0x30313634) == "0164",
           "a numeric tag reads as the decimal map id, '0164'")
    led.ok(all(d[k] == 0 for k in ("campaign", "is_pvp", "secondary", "helm_shown",
                                   "pflag0", "pflag1", "pflag2")),
           "every other flag bit is zero for the loopback character")
    led.ok(cs.length_for(0) == 37 and cs.length_for(5) == 62,
           "length_for: 37 for no items, 62 for five")

    # ---------------------------------------------------------------- §2
    print("\n§2  RUN G'S PAIR: WHAT DIFFERED, AND WHAT THE CLIENT COMPARED")
    led.ok(cs.differing(SERVED_G, SENT_G) == ["unwritten", "items"],
           "served-G vs sent-G differ in exactly residue and items",
           cs.differing(SERVED_G, SENT_G))
    led.ok(cs.compared_differing(SERVED_G, SENT_G) == ["items"],
           "the dirty check sees exactly ['items'] -- the byte-59 flip",
           cs.compared_differing(SERVED_G, SENT_G))
    led.ok(cs.decode(SERVED_G)["items"][4] == (0x5a, 0xc, 0x13)
           and cs.decode(SENT_G)["items"][4] == (0x5a, 0xb, 0x13),
           "byte 59 is item[4].b: served 0x0c, the client computed 0x0b")
    # The E/F null: the same served blob against the client's own re-packing
    # of it, which zeroes the residue. Nothing compared differs.
    led.ok(cs.differing(SERVED_A, SENT_G) == ["unwritten"],
           "A's served blob vs the client's packing differ ONLY in residue",
           cs.differing(SERVED_A, SENT_G))
    led.ok(cs.compared_differing(SERVED_A, SENT_G) == [],
           "so the dirty check sees NOTHING -- runs E and F sent no settings")
    led.ok(cs.compared_differing(SERVED_A, SENT_G, in_map=False) == [],
           "and nothing out of map either")
    # A residue-only difference is invisible whichever residue it carries --
    # retail's 0xDD fill included.
    noisy = bytearray(SERVED_A)
    noisy[33:37] = b"\xdd\xdd\xdd\xdd"
    noisy[30] |= 0xfc
    noisy[31] = 0xdd
    led.ok(cs.compared_differing(SERVED_A, bytes(noisy)) == [],
           "0xDD fill in bytes 33-36 and flag bits 18-31 is still the same "
           "summary")
    led.ok(cs.differing(SERVED_A, bytes(noisy)) == ["flags_unwritten",
                                                    "unwritten"],
           "and differing() names both residue positions",
           cs.differing(SERVED_A, bytes(noisy)))
    led.ok(cs.residue(bytes(noisy)) == {"unwritten": b"\xdd" * 4,
                                        "flags_unwritten": 0xddfc0000},
           "residue() reports exactly the unwritten bytes and bits",
           cs.residue(bytes(noisy)))

    # ---------------------------------------------------------------- §3
    print("\n§3  EVERY COMPARED FIELD IS SEEN WHEN ITS OWN BYTES MOVE")
    led.ok(cs.compared_differing(SERVED_A, moved(8)) == ["appearance"],
           "byte 8 is appearance")
    led.ok(cs.compared_differing(SERVED_A, moved(10, 0x10)) == ["appearance"]
           and cs.decode(moved(10, 0x10))["profession"] == 2,
           "byte 10's high nibble is the profession -- Warrior + 1 is 2")
    led.ok(cs.compared_differing(SERVED_A, moved(2)) == ["last_outpost"],
           "byte 2 is last_outpost, compared in map")
    led.ok(cs.compared_differing(SERVED_A, moved(2), in_map=False) == [],
           "... and NOT compared out of map")
    led.ok(cs.compared_differing(SERVED_A, moved(4)) == ["tag"],
           "byte 4 is the tag, compared in map")
    led.ok(cs.compared_differing(SERVED_A, moved(12)) == ["guild_hall_id"]
           and cs.compared_differing(SERVED_A, moved(27)) == ["guild_hall_id"],
           "bytes 12 and 27 bound guild_hall_id, compared in map")
    led.ok(cs.compared_differing(SERVED_A, moved(27), in_map=False) == [],
           "... and not out of map")
    led.ok(cs.compared_differing(SERVED_A, moved(28, 0x10)) == ["level"],
           "flag bit 4 is level")
    led.ok(cs.compared_differing(SERVED_A, moved(29, 0x01)) == ["level"],
           "flag bit 8 is still level -- five bits, room for 20")
    led.ok(cs.compared_differing(SERVED_A, moved(28, 0x01)) == ["campaign"],
           "flag bit 0 is campaign")
    led.ok(cs.compared_differing(SERVED_A, moved(29, 0x02)) == ["is_pvp"],
           "flag bit 9 is is_pvp")
    led.ok(cs.compared_differing(SERVED_A, moved(29, 0x04)) == ["secondary"],
           "flag bit 10 is secondary")
    led.ok(cs.compared_differing(SERVED_A, moved(29, 0x40)) == [],
           "flag bit 14 (helm_shown) moves and the dirty check does NOT see it")
    led.ok(cs.differing(SERVED_A, moved(29, 0x40)) == ["helm_shown"],
           "... though differing() names it")
    led.ok(cs.compared_differing(SERVED_A, moved(29, 0x80)) == ["pflag0"]
           and cs.compared_differing(SERVED_A, moved(30, 0x01)) == ["pflag2"]
           and cs.compared_differing(SERVED_A, moved(30, 0x02)) == ["pflag1"],
           "flag bits 15, 16, 17 are pflag0, pflag2, pflag1 -- the packer's "
           "order")
    led.ok(cs.compared_differing(SERVED_A, moved(30, 0x04)) == [],
           "flag bit 18 is unwritten and not compared")
    led.ok(cs.compared_differing(SERVED_A, moved(37)) == ["items"]
           and cs.compared_differing(SERVED_A, moved(41)) == ["items"],
           "bytes 37 and 41 are item[0].a and item[0].c")
    led.ok(cs.compared_differing(SERVED_A, moved(33)) == []
           and cs.compared_differing(SERVED_A, moved(36)) == [],
           "bytes 33 and 36 bound the unwritten four and are not compared")
    b = bytearray(SERVED_A)
    b[32] = 4
    led.ok(cs.compared_differing(SERVED_A, bytes(b)) == ["count", "items"],
           "count moving is seen, and the item list shrinks with it",
           cs.compared_differing(SERVED_A, bytes(b)))

    # ---------------------------------------------------------------- §4
    print("\n§4  ENCODE IS THE PACKER'S INVERSE, WITH THE RESIDUE ZERO")
    led.ok(cs.encode(cs.decode(SERVED_A)) == SENT_G,
           "re-packing A's blob yields exactly what G's client sent -- the "
           "residue is the only difference between them")
    led.ok(cs.encode(cs.decode(SENT_G)) == SENT_G,
           "a residue-free blob round-trips byte for byte")
    led.ok(len(cs.encode({"items": []})) == 37,
           "an empty record is 37 bytes, the count-0 shape 147 of our "
           "captures carry")
    led.ok(cs.encode({"level": 20, "is_pvp": 1})[28:32]
           == (20 << 4 | 1 << 9).to_bytes(4, "little"),
           "level 20 with is_pvp packs as the packer does")
    for name, shift, width in cs.FLAG_BITS:
        top = (1 << width) - 1
        led.ok(cs.decode(cs.encode({name: top}))[name] == top,
               f"{name}: the full {width}-bit value survives a round trip")
    try:
        cs.encode({"level": 32})
        led.ok(False, "level 32 does not fit five bits")
    except cs.Malformed as ex:
        led.ok("level=32" in str(ex), "level 32 is refused by name", str(ex))
    try:
        cs.encode({"guild_hall_id": b"\x00" * 15})
        led.ok(False, "a 15-byte guild_hall_id is refused")
    except cs.Malformed as ex:
        led.ok("15 bytes" in str(ex), "a 15-byte guild_hall_id is refused",
               str(ex))

    # ---------------------------------------------------------------- §5
    print("\n§5  THE UNPACKER'S REFUSALS ARE MADE HERE TOO")

    def refuses(blob, why):
        try:
            cs.decode(blob)
        except cs.Malformed as ex:
            led.ok(True, why, str(ex))
            return
        led.ok(False, why, "decoded without complaint")

    b = bytearray(SERVED_A); b[0] = 9
    refuses(bytes(b), "version 9 is above 8 (the unpacker's `ja`)")
    b = bytearray(SERVED_A); b[0] = 6
    refuses(bytes(b), "version 6 -- the server's own literal -- needs the "
            "client's converter and is refused rather than guessed at")
    b = bytearray(SERVED_A); b[32] = 6
    refuses(bytes(b), "count 6 is above the unpacker's 5")
    refuses(SERVED_A[:61], "61 bytes is short of 0x25 + 5 * 5")
    refuses(SERVED_A[:36], "36 bytes is short of the header")
    refuses(b"\x08", "one byte is short of the version word")
    b = bytearray(SERVED_A); b[32] = 4
    led.ok(cs.decode(bytes(b))["surplus"] == 5,
           "count 4 in a 62-byte blob decodes with 5 surplus bytes reported")

    sys.exit(led.verdict())


if __name__ == "__main__":
    main()
