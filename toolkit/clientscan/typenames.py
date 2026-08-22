r"""What the client calls each skill `type_code` -- from the client's own switch.

    python toolkit/clientscan/typenames.py            # the table, resolved
    python toolkit/clientscan/typenames.py --walk     # the switch, as arithmetic
    python toolkit/clientscan/typenames.py --ids      # ids only, no archive

WHAT THIS CLOSES. `studies/presearing/MANIFEST.md` 8 named ten of the client's
skill type codes by Rosetta stone -- pick skills whose type is independently
known, read their `+0x0C`, and take the majority. Eleven were left UNKNOWN, and
`PLAN.md` 8 item 5 singled out **16** because it sits on this server's own
default skillbar and is named nowhere. Naming them by Rosetta stone needs two
or three known skills per code and an outside source for every one.

It was not necessary. **The client names its own types, in a single switch.**

    0x004F9BF0   the namer.  mov eax,[edi+0x0C]      <- the type_code field
                             cmp eax,0x0E            <- type 14 leaves here
                             ...                     <- 17, 18, 22 leave here
                             push eax ; call 0x004F9DD0
    0x004F9DD0   mov eax,[ebp+8] ; dec eax ; cmp eax,0x1C
                 ja 0x004FA7A0                       <- the default arm
                 jmp [eax*4 + 0x004FA7BC]            <- 29 entries

So the jump-table index is `type_code - 1`, and every case body computes a
STRING ID. The default arm logs ArenaNet's own sentence, which is the single
strongest piece of evidence that this switch is the type namer and not some
other switch on some other field:

    "There is no string to describe skill %u's type."     .rdata 0x0094E614

THE CONTROL, AND IT IS THE WHOLE ARGUMENT. The index base is the only free
parameter, and one step in either direction breaks every known code at once.
With `type_code - 1`, all ten codes `MANIFEST.md` named independently land on
the right word: 3 -> "Stance", 4 -> "Hex Spell", 5 -> "Spell", 6 ->
"Enchantment Spell", 7 -> "Signet", 8 -> "Condition", 10 -> "Skill", 12 ->
"Glyph", 15 -> "Shout", 19 -> "Preparation". Ten of ten, against names derived
years apart by a completely different method. `test_typenames.py` runs it.

AND THE ANSWER TO ITEM 5 IS A GENUINE ODDITY. **Type 16 displays as "Skill" --
and so does type 10, from a DIFFERENT string record.** 942 and 960 are two
rows of the archive that carry the same English word (and the same word in
French, German and Italian). They are two enum values ArenaNet chose to label
identically, not an alias and not a decoder collision. The bodies differ:
type 10 has touch and half-range variants; type 16 has none and instead
ASSERTS both flags are clear -- two `GmSkHelpers.cpp:139` sites at
0x004FA30B..0x004FA34B. Why the engine needs the distinction is NOT ANSWERED
here; only what it is called.

IDS, NOT WORDS, IS WHAT THIS FILE STORES. CLAUDE.md's rule for authored text is
"commit the id, resolve the string at run time from the owner's own archive",
which `mapbuild.py` already proves. So the table below is integers measured out
of the image, each carrying the address that produced it, and the words come
from `textrec.py` against the owner's `Gw.dat` when you ask for them. A machine
without the archive still gets the ids.

ADDRESSES ARE BUILD 38797 AND DO NOT SURVIVE A REBUILD. String ids do.
`pinned.find()` refuses an unknown build rather than reading whatever else is
mapped there.

READ-ONLY. The client is opened, never launched and never written. Python 3
standard library only -- no capstone here, on purpose: the byte patterns are
fixed and this must keep working on a bare machine, which is the same rule
`asserts.py` and `msgshape.py` are held to.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

import pinned                                        # noqa: E402
from gwpe import PE                                  # noqa: E402

# The namer, its switch, and the two constants the switch is built from.
VA_NAMER = 0x004F9BF0            # reads [skillRecord+0x0C] and dispatches
VA_TYPE_FIELD_READ = 0x004F9C48  # mov eax,[edi+0x0C]
VA_TYPE14_TEST = 0x004F9C4B      # cmp eax,0x0E   -- attacks leave here
VA_SWITCH = 0x004F9DD0           # the switch itself
VA_JUMP_TABLE = 0x004FA7BC       # 29 dwords
VA_DEFAULT_ARM = 0x004FA7A0      # ja lands here
SWITCH_BOUND = 0x1C              # cmp eax,0x1C -> 29 cases, index = code - 1
SWITCH_INDEX_BIAS = 1            # `dec eax` before the bound check
VA_NO_STRING_MSG = 0x0094E614    # "There is no string to describe skill %u's type."

# THE TABLE. type_code -> (case body VA, base string id, elite string id or None).
#
# MEASURED, one case body at a time, from the addresses named. Codes whose case
# body computes only a constant have no elite form and carry None. The four
# codes NOT here (14, 17, 18, 22) never reach the switch -- see SPECIAL below.
#
# Each id is the UNFLAGGED name. Five codes (4, 5, 6, 7, 10) also carry
# flag-conditioned variants -- "Touch Hex Spell", "Flash Enchantment Spell" and
# so on -- and those are deliberately NOT in this table: the variant strings are
# reachable from those case bodies (observed) but WHICH flag bit selects which
# was not verified, and a mapping nobody checked is the thing this repo keeps
# getting burned by. `--walk` prints the extra ids it finds.
TYPE_STRING_ID = {
    1:  (0x004F9E37, 34036, None),
    2:  (0x004F9F3C,   931, None),
    3:  (0x004FA4F7,   956,   957),
    4:  (0x004F9E95,   948,   949),
    5:  (0x004FA401,   946,   947),
    6:  (0x004FA1BF,   950,   951),
    7:  (0x004FA211,   936,   937),
    8:  (0x004FA35D,   940,   941),
    9:  (0x004FA74E, 32224, 32225),
    10: (0x004FA654,   960,   961),
    11: (0x004FA6FC, 32222, 32223),
    12: (0x004FA4A5,   952,   953),
    13: (0x004FA59B, 52243, None),
    15: (0x004FA3AF,   944,   945),
    16: (0x004FA30B,   942,   943),
    19: (0x004F9DE9,   923,   924),
    20: (0x004FA2B9,   938,   939),
    21: (0x004FA602,   958,   959),
    23: (0x004FA100, 32219, None),
    24: (0x004F9FA3, 32220, 32221),
    25: (0x004FA549,   954,   955),
    26: (0x004FA167, 38863, 39729),   # NOT base+1; `and eax,0x362; add eax,0x97CF`
    27: (0x004F9FF5, 36382, 36383),
    28: (0x004FA0AE, 18450, 18451),
    29: (0x004FA047, 51773, None),
}

# THE FOUR THAT NEVER REACH THE SWITCH, and each is a different reason.
SPECIAL = {
    14: "intercepted at 0x004F9C4B (`cmp eax,0x0E`) and tail-called to "
        "0x004FAE60 with the weapon and combo fields, because an attack's "
        "displayed name depends on the weapon and the chain slot -- 'Sword "
        "Attack', 'Off-Hand Attack'. Its jump-table slot is the default arm.",
    17: "short-circuited in the namer (`sub ecx,0x11; je 0x004F9DAB`) to "
        "return string id 1, which resolves to the null record. The client "
        "deliberately gives this type NO type word.",
    18: "short-circuited the same way, one `sub ecx,1` later. Also id 1.",
    22: "handled in the namer rather than the switch, because its name is NOT "
        "a constant: title track (+0x2A) == 0x28 gives one string, else "
        "profession (+0x28) 2 gives another and 8 a third. ArenaNet's own word "
        "for the family, from its failure log at 0x0094E728, is 'global "
        "skill'.",
}
# 22's three arms, measured at 0x004F9C67..0x004F9D9A.
TYPE22_ARMS = {("title_track", 0x28): 73526,
               ("profession", 2): 932,
               ("profession", 8): 934}

# The ten `studies/presearing/MANIFEST.md` 8 named independently, and the words
# it named them with. This is the control: it is not used to BUILD anything.
ROSETTA = {3: "Stance", 4: "Hex Spell", 5: "Spell", 6: "Enchantment Spell",
           7: "Signet", 8: "Condition", 10: "Skill", 12: "Glyph",
           15: "Shout", 19: "Preparation"}

NULL_STRING_ID = 1


class Image:
    """The pinned client's bytes. Same shape as `test_adrenwire.Image`."""

    def __init__(self):
        self.path, self.why = pinned.find()
        self.pe = PE(self.path)
        self.base = self.pe.image_base

    def read(self, va, n):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            raise ValueError(f"0x{va:08x} is not backed by file bytes")
        return self.pe.data[off:off + n]

    def u32(self, va):
        return struct.unpack("<I", self.read(va, 4))[0]


def switch_shape(img):
    """The switch prologue, read as bytes rather than described.

    Returns (index_bias, bound, table_va, default_va). Every one is computed
    from the instruction encodings, so a wrong address gives a wrong number
    rather than agreeing with the label we chose for it.
    """
    d = img.read(VA_SWITCH, 32)
    bias = 1 if b"\x8b\x45\x08\x48" in d[:8] else None   # mov eax,[ebp+8]; dec
    i = d.find(b"\x83\xf8")                              # cmp eax,imm8
    bound = d[i + 2] if i >= 0 else None
    j = d.find(b"\x0f\x87")                              # ja rel32
    default = (VA_SWITCH + j + 6
               + struct.unpack("<i", d[j + 2:j + 6])[0]) if j >= 0 else None
    k = d.find(b"\xff\x24\x85")                          # jmp [eax*4+imm32]
    table = struct.unpack("<I", d[k + 3:k + 7])[0] if k >= 0 else None
    return bias, bound, table, default


def case_targets(img, table_va=VA_JUMP_TABLE, n=None):
    """type_code -> case body VA, straight out of the jump table."""
    n = (SWITCH_BOUND + 1) if n is None else n
    return {k + SWITCH_INDEX_BIAS: img.u32(table_va + 4 * k) for k in range(n)}


def resolve(ids, language=0):
    """string id -> the word, from the owner's own archive. Never bundled.

    Goes through `textrec.TextIndex`, which locates the pointer array
    structurally rather than by address, so this survives a rebuild even though
    every VA in this file does not.
    """
    sys.path.insert(0, os.path.join(ROOT, "toolkit", "mapdata"))
    import textrec
    exe, _why = textrec.find_exe()
    with textrec.TextIndex(exe, textrec.DEFAULT_DAT, language) as ix:
        return {sid: ix.get(sid) for sid in ids}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--walk", action="store_true",
                    help="walk the switch and print the case bodies")
    ap.add_argument("--ids", action="store_true",
                    help="ids only -- no archive, works on a bare machine")
    ap.add_argument("--language", type=int, default=0)
    args = ap.parse_args()

    img = Image()
    print(f"client: {img.path}")
    print(f"        ({img.why})\n")

    bias, bound, table, default = switch_shape(img)
    print(f"switch 0x{VA_SWITCH:08x}: index = type_code - {bias}, "
          f"bound {bound} ({bound + 1} cases), table 0x{table:08x}, "
          f"default 0x{default:08x}")
    print(f"default arm logs 0x{VA_NO_STRING_MSG:08x} "
          f'"There is no string to describe skill %u\'s type."\n')

    if args.walk:
        targets = case_targets(img, table)
        for code in sorted(targets):
            va = targets[code]
            mark = ""
            if va == default:
                mark = ("  DEFAULT ARM -- " + SPECIAL.get(code, "unexpected")
                        .split(",")[0])
            known = TYPE_STRING_ID.get(code)
            pinned_va = f"pinned 0x{known[0]:08x}" if known else ""
            agree = "" if not known else (
                "" if known[0] == va else "   ** DISAGREES WITH THE PIN **")
            print(f"  type {code:2}  -> 0x{va:08x}  {pinned_va}{agree}{mark}")
        print()

    rows = []
    for code, (va, base, elite) in sorted(TYPE_STRING_ID.items()):
        rows.append((code, va, base, elite))
    if args.ids:
        for code, va, base, elite in rows:
            print(f"  type {code:2}  0x{va:08x}  base {base:6}  "
                  f"elite {elite if elite is not None else '-':>6}")
        return 0

    wanted = sorted({i for _c, _v, b, e in rows for i in (b, e)
                     if i is not None})
    try:
        words = resolve(wanted, args.language)
    except Exception as ex:                                # noqa: BLE001
        print(f"the archive is not readable here ({ex}); "
              f"re-run with --ids for the integers alone")
        return 1
    for code, va, base, elite in rows:
        ctrl = ""
        if code in ROSETTA:
            got = words.get(base, "")
            ctrl = ("   CONTROL ok" if ROSETTA[code] in got
                    else f"   ** CONTROL FAILED, expected {ROSETTA[code]!r} **")
        print(f"  type {code:2}  0x{va:08x}  {base:6} {words.get(base, '?'):<28}"
              f"{('elite ' + str(elite)) if elite else '':<12}{ctrl}")
    print()
    for code, why in sorted(SPECIAL.items()):
        print(f"  type {code:2}  NOT IN THE SWITCH: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
