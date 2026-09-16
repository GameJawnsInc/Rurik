"""charsummary: the character summary blob, decoded the way the client packs it.

WHAT THIS IS. `CHARACTER_INFO`'s trailing `array8(64)` and `UPDATE_CHARACTER_
SETTINGS`'s payload are the same record: the client's own character summary,
packed by `0x009273B0` and unpacked by `0x009274D0` (build 38797, read with
`toolkit/clientscan/codescan.py --dis`, studies/heroes/RUN-HEROLIB.md §22).
The server stores it verbatim (`charstore.py`, `settings_blob`) and never
needed to parse it; this module exists because §21.4 asked which of its bytes
the client COMPARES before deciding to send, and the answer is a byte map.

THE LAYOUT, as the packer writes it (OBSERVED, every offset from the packer;
the names are the ones `authsrv.py`'s version-6 literal already carried from
upstream, kept where the census corroborates them and replaced where it does
not):

  bytes   width  field           packer source (the 0x7C-byte struct S)
  0-1     u16    version         constant 8
  2-3     u16    last_outpost    S+0x5C <- summary+0x2C, the map id the client
                                 was in when it packed (UPSTREAM name; every one
                                 of 184 served values in the vault is an outpost)
  4-7     u32    tag             S+0x60 <- summary+0x30. NOT a time: upstream
                                 called it `last_time_played`, and the live census
                                 reads it as a four-character C multichar
                                 constant -- 'newb' (the client's own default for
                                 a fresh record, 0x6e657762), 'tuto', 'lake',
                                 'vale', 'plai', 'basi', 'op1', or the DECIMAL
                                 map id of the outpost ('0164', '0449', ...)
  8-11    u32    appearance      S+0x00 <- summary+0x00, the 0x0059 appearance
                                 dword; profession nibble at bits 20-23
  12-27   16B    guild_hall_id   S+0x08..0x14 <- summary+0x08..0x14, fetched
                                 from the guild module (0x0083FC00); UPSTREAM
                                 name, zero in every blob we hold
  28-31   u32    flags           bit-packed, see FLAG_BITS; bits 18-31 UNWRITTEN
  32      u8     count           S+0x18, the number of composite items, <= 5
                                 (upstream: number_of_pieces)
  33-36   --     UNWRITTEN       the packer never touches these four bytes, and
                                 the unpacker never reads them (upstream:
                                 "trailing dword, believed unread")
  37+5i   u16    item[i].a       S+0x1C+4i  the composite item id (CpsApi
                                 summary, `Character summary item invalid`)
  39+5i   u16    item[i].b       S+0x30+4i
  41+5i   u8     item[i].c       S+0x44+4i

  total = 0x25 + 5 * count: 37 for no items, 62 for five.

THE FLAGS DWORD (bytes 28-31), bit fields in the order the packer merges them:

  bits    field       summary   where the dispatcher (0x004A8AD0) reads it
  0-3     campaign    +0x04     ChCliApi 0x00815CF0: player+0x688 (UPSTREAM
                                name; 1 for every pre-Searing character in the
                                live census, 0 for the level-20 ones)
  4-8     level       +0x28     0x0080D5E0(agent): the agent table entry +0x2C
                                (3 for our level-3 loopback character; 1, 2, 3
                                and 20 for the owner's, in the live census)
  9       is_pvp      +0x34     ChCliApi 0x00815FF0 (UPSTREAM name, GmChar.h
                                via studies/character/FINDINGS.md; set on
                                exactly the level-20, campaign-0 characters
                                in the live census, 19 + 8 of them)
  10-13   secondary   +0x38     AvApi 0x007DF810's second out-value (UPSTREAM
                                name: the secondary profession; 7 and 4 on
                                level-20 characters, 0 on the pre-Searing ones)
  14      helm_shown  +0x3C     ChCliApi 0x00815EA0(3): CHAR_STATS_VIS bit 3
                                (upstream's `helm_status:2` is bits 14-15; the
                                packer fills them from two different reads --
                                1 on every live summary, 0 on our loopback one)
  15      pflag0      +0x40     the player's ChCliApi entry +0x34, bit 0 (the
                                other half of upstream's helm pair)
  16      pflag2      +0x44     ... bit 2 (upstream names neither of these)
  17      pflag1      +0x48     ... bit 1
  18-31   UNWRITTEN             the packer read-modify-writes the dword and
                                never assigns these; the unpacker reads only
                                bits 0-17

WHICH FIELDS THE DIRTY CHECK COMPARES (0x008711E0, RUN-HEROLIB.md §19/§22):

  always:      appearance, level, campaign, is_pvp, secondary, pflag0, pflag1, pflag2,
               count, and every item's a, b, c
  only in-map: last_outpost, tag, guild_hall_id (the dispatcher's in-map flag)
  never:       helm_shown, the four unwritten bytes, flag bits 18-31

So two blobs that differ ONLY in never-compared positions are the same summary
to the client, and it will not send. That is exactly what RUN-HEROLIB-G saw:
the stored blob carried `ed 00 00 dc` at 33-36 (whatever the output buffer
held when run A's client packed it) where G's client wrote zeros, and runs E
and F sent nothing; one byte of item[4].b changed and the send fired. Retail's
own served blobs show the same shape from the other side: 92 of 161 carry
0xDD allocator fill in exactly bytes 33-36 and flag bits 18-31, nowhere else.

VERSIONS. Every blob a client SENT is version 8 (525 of 525 ours, 23 of 23
live). `authsrv.py`'s literal is version 6 and the client accepts it through
its converter (0x005EAFA0, a descriptor table at 0xBCB3D8, unread here), then
sends version 8 back. Only version 8 is decoded; older ones are refused rather
than guessed at.

Stdlib only, no vault, no client: a leaf.
"""

import struct

VERSION = 8
HEADER = 0x25          # bytes before the first item
ITEM = 5               # bytes per item
MAX_ITEMS = 5          # the unpacker refuses count > 5
UNWRITTEN = range(33, 37)      # bytes the packer never assigns
FLAGS_WRITTEN_MASK = 0x3FFFF   # bits 0-17; 18-31 are never assigned

# (name, shift, width) -- the order the packer merges them into the dword.
FLAG_BITS = (
    ("campaign", 0, 4),
    ("level", 4, 5),
    ("is_pvp", 9, 1),
    ("secondary", 10, 4),
    ("helm_shown", 14, 1),
    ("pflag0", 15, 1),
    ("pflag2", 16, 1),
    ("pflag1", 17, 1),
)

# What 0x008711E0 compares, by decoded key. `items` covers every (a, b, c).
COMPARED_ALWAYS = frozenset((
    "appearance", "level", "campaign", "is_pvp", "secondary",
    "pflag0", "pflag1", "pflag2", "count", "items",
))
COMPARED_IN_MAP = frozenset(("last_outpost", "tag", "guild_hall_id"))
NEVER_COMPARED = frozenset(("helm_shown", "unwritten", "flags_unwritten"))

# Layout order, for differing().
FIELD_ORDER = ("version", "last_outpost", "tag", "appearance", "guild_hall_id",
               "campaign", "level", "is_pvp", "secondary", "helm_shown", "pflag0",
               "pflag2", "pflag1", "flags_unwritten", "count", "unwritten",
               "items")

APPEARANCE_PROFESSION_SHIFT = 20   # the nibble, studies/profession/MODDABLE.md
FRESH_TAG = 0x6e657762             # 'newb', what 0x00870F90 writes for a new record


class Malformed(ValueError):
    """The blob is not one the unpacker (0x009274D0) would accept, or is a
    version this module does not read."""


def length_for(count):
    return HEADER + ITEM * count


def tag_text(tag):
    """A tag as the C multichar constant it is: 0x6e657762 -> 'newb'."""
    raw = int(tag).to_bytes(4, "big").lstrip(b"\x00")
    if not raw:
        return None
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    return text if text.isprintable() else None


def decode(blob):
    """The blob's fields, keyed as in the module docstring. Refuses what the
    client's unpacker refuses -- a version above 8, a count above 5, a blob
    shorter than its count needs -- and a version below 8, which the client
    converts and this module does not."""
    b = bytes(blob)
    if len(b) < 2:
        raise Malformed(f"charsummary: {len(b)} bytes, the unpacker needs 2")
    version = struct.unpack_from("<H", b, 0)[0]
    if version > VERSION:
        raise Malformed(f"charsummary: version {version} > {VERSION}")
    if version != VERSION:
        raise Malformed(f"charsummary: version {version}, only {VERSION} is "
                        f"decoded here -- the client converts older ones")
    if len(b) < HEADER:
        raise Malformed(f"charsummary: {len(b)} bytes, the header is {HEADER}")
    count = b[32]
    if count > MAX_ITEMS:
        raise Malformed(f"charsummary: count {count} > {MAX_ITEMS}")
    need = length_for(count)
    if len(b) < need:
        raise Malformed(f"charsummary: {len(b)} bytes, count {count} needs "
                        f"{need}")
    flags = struct.unpack_from("<I", b, 28)[0]
    out = {
        "version": version,
        "last_outpost": struct.unpack_from("<H", b, 2)[0],
        "tag": struct.unpack_from("<I", b, 4)[0],
        "appearance": struct.unpack_from("<I", b, 8)[0],
        "guild_hall_id": b[12:28],
        "flags": flags,
        "flags_unwritten": flags & ~FLAGS_WRITTEN_MASK & 0xFFFFFFFF,
        "count": count,
        "unwritten": b[UNWRITTEN.start:UNWRITTEN.stop],
        "items": [],
        "length": len(b),
        "surplus": len(b) - need,
    }
    for name, shift, width in FLAG_BITS:
        out[name] = (flags >> shift) & ((1 << width) - 1)
    out["profession"] = (out["appearance"] >> APPEARANCE_PROFESSION_SHIFT) & 0xF
    out["tag_text"] = tag_text(out["tag"])
    for i in range(count):
        o = HEADER + ITEM * i
        a, bb = struct.unpack_from("<HH", b, o)
        out["items"].append((a, bb, b[o + 4]))
    return out


def encode(fields):
    """The packer's inverse for a decoded dict, with the unwritten positions
    zero. `decode(encode(decode(x)))` equals `decode(x)` in every compared
    field; it differs from x only where x carried residue."""
    items = list(fields.get("items", ()))
    if len(items) > MAX_ITEMS:
        raise Malformed(f"charsummary: {len(items)} items > {MAX_ITEMS}")
    flags = 0
    for name, shift, width in FLAG_BITS:
        v = int(fields.get(name, 0))
        if v >> width:
            raise Malformed(f"charsummary: {name}={v} does not fit {width} bits")
        flags |= v << shift
    guild = bytes(fields.get("guild_hall_id", b"\x00" * 16))
    if len(guild) != 16:
        raise Malformed(f"charsummary: guild_hall_id is {len(guild)} bytes, "
                        f"not 16")
    out = bytearray(length_for(len(items)))
    struct.pack_into("<HHII", out, 0, VERSION,
                     int(fields.get("last_outpost", 0)),
                     int(fields.get("tag", 0)),
                     int(fields.get("appearance", 0)))
    out[12:28] = guild
    struct.pack_into("<I", out, 28, flags)
    out[32] = len(items)
    for i, (a, bb, c) in enumerate(items):
        struct.pack_into("<HHB", out, HEADER + ITEM * i, a, bb, c)
    return bytes(out)


def differing(x, y):
    """The decoded keys where two blobs differ, in layout order. Byte-level
    residue shows up as 'unwritten' / 'flags_unwritten', never as a field."""
    dx, dy = decode(x), decode(y)
    return [k for k in FIELD_ORDER if dx[k] != dy[k]]


def compared_differing(x, y, in_map=True):
    """The keys the client's dirty check would see as changed between a blob
    it holds and one it computes. Empty means: no UPDATE_CHARACTER_SETTINGS."""
    keys = COMPARED_ALWAYS | (COMPARED_IN_MAP if in_map else frozenset())
    return [k for k in differing(x, y) if k in keys]


def residue(blob):
    """The bytes and bits the packer never assigns, as the blob carries them.
    Non-zero here is whatever the packer's output buffer held, and it is
    harmless: the unpacker never reads these positions."""
    d = decode(blob)
    return {"unwritten": d["unwritten"], "flags_unwritten": d["flags_unwritten"]}


def summarize(blob):
    d = decode(blob)
    items = " ".join(f"{a}/{b}/{c}" for a, b, c in d["items"])
    tag = d["tag_text"] or f"{d['tag']:#x}"
    return (f"v{d['version']} outpost {d['last_outpost']} tag {tag!r} "
            f"prof {d['profession']} level {d['level']} "
            f"campaign {d['campaign']} is_pvp {d['is_pvp']} secondary {d['secondary']} "
            f"helm {d['helm_shown']} pflags {d['pflag0']}{d['pflag1']}"
            f"{d['pflag2']} guild {d['guild_hall_id'].hex()} "
            f"items[{d['count']}] {items} residue {d['unwritten'].hex()}/"
            f"{d['flags_unwritten']:#x} len {d['length']}")


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print(summarize(bytes.fromhex(arg)))
