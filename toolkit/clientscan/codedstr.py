"""The coded string: markers, and 0x100-biased base-0x7F00 varints.

WHAT A CODED STRING IS. The client does not send text. It sends a sequence of
u16 words in which a word BELOW 0x100 is a marker from the client's own markup
alphabet, and a word at or above 0x100 opens a varint: base 0x7F00 digits, most
significant first, each biased by 0x100, with 0x8000 marking continuation. The
value is a string id, resolved against the archive by `textrec.py`.

WHY THIS FILE EXISTS. The rule was derived in `studies/textrec/FINDINGS.md` 4
from `TextParser.cpp`, and `studies/quests/FINDINGS.md` 3.2 then tested it
against a source that arc never had -- 66 quest name/NPC slots on ArenaNet's own
wire -- and got 66 of 66. That number was a paragraph in a document. Section 7.9
of the same file asked for it to become a test, in these words: "encode_id(sid)
/ parse_coded(words) are ~15 lines of stdlib, now verified 66/66 byte-identical
against ArenaNet's wire. Put them beside textrec.py with that 66/66 as a test --
it is refutable, cheap, and goes red the day the assumption breaks."

The assumption is load-bearing in both directions. Every authored quest string
this repo puts on the wire is built on it, and every string id it reads back out
of a capture is decoded with it. Until now the ENCODE half lived nowhere at all:
`questdefs.coded_literal` builds a literal run and never encodes an id, so the
66/66 could only be reproduced by rewriting the script that produced it.

    python toolkit/clientscan/codedstr.py 80660 15460
    python toolkit/clientscan/codedstr.py --parse 8102 3e14 e536 b7c0 576d

NOT A TEXT DECODER. This turns words into ids and back. Resolving an id to
words needs the owner's archive and is `textrec.py`'s job -- which is the same
split the provenance gate draws: the id is a measurement and may be committed,
the string is ArenaNet's expression and is resolved at run time.
"""
import argparse
import sys

# MEASURED. `studies/textrec/FINDINGS.md` 4 derived these from TextParser.cpp
# and the client asserts on the third one by name: a literal run must open with
# a word >= WORD_VALUE_BASE, and a 0x004C whose description began 'S' (0x53)
# killed a real client on
#     Assertion: (codedString[0] & ~WORD_BIT_MORE) >= WORD_VALUE_BASE
#     P:\Code\Engine\Text\TextApi.cpp(585)
# so the client's own words name both WORD_BIT_MORE (0x8000) and
# WORD_VALUE_BASE (0x100). See studies/quests/FINDINGS.md 3.2 and Q3.
BASE = 0x7F00        # digit radix
BIAS = 0x100         # WORD_VALUE_BASE: below this a word is a marker
CONT = 0x8000        # WORD_BIT_MORE: more digits follow


def encode_id(string_id):
    """The u16 words the client expects for `string_id`.

    Refuses a negative id rather than emitting something that decodes to
    nonsense: the digit loop below would happily produce words for one.
    """
    if string_id < 0:
        raise ValueError(f"string id {string_id} is negative; the wire form has "
                         f"no sign and would decode as a different number")
    digits, v = [], string_id
    while True:
        digits.append(v % BASE)
        v //= BASE
        if not v:
            break
    digits.reverse()
    return [d + BIAS | (CONT if i < len(digits) - 1 else 0)
            for i, d in enumerate(digits)]


def decode_id(words):
    """(string_id, words_consumed) for the varint at the head of `words`.

    Raises rather than guessing on the two ways this can be handed something
    that is not a varint. `CLAUDE.md`'s refuse-to-guess rule applies with force
    here: a silently wrong string id resolves to a DIFFERENT record and reads as
    a plausible answer, which is exactly how the rival raw-word reading survived
    as long as it did.
    """
    if not words:
        raise ValueError("empty word list has no id to decode")
    if words[0] < BIAS:
        raise ValueError(
            f"0x{words[0]:04X} is below WORD_VALUE_BASE (0x{BIAS:03X}), so it is "
            f"a MARKER, not the start of an id. Use parse_coded() to walk a "
            f"mixed sequence")
    v = 0
    for i, w in enumerate(words):
        v = v * BASE + ((w & ~CONT) - BIAS)
        if not w & CONT:
            return v, i + 1
    raise ValueError(
        f"continuation bit set on the last of {len(words)} words -- the id runs "
        f"off the end of the sequence, so the field was truncated or this is "
        f"not a coded string")


def parse_coded(words):
    """[('marker', value) | ('id', value), ...] for a whole coded sequence.

    Markers keep their RAW word; ids are decoded. Both are reported so a caller
    can tell the two apart, which the single-value helpers above cannot.
    """
    out, i = [], 0
    while i < len(words):
        if words[i] < BIAS:
            out.append(("marker", words[i]))
            i += 1
        else:
            sid, used = decode_id(words[i:])
            out.append(("id", sid))
            i += used
    return out


def from_wire(value):
    """Words from whatever `codec.py` handed us -- a str of code units or ints.

    `codec.py` decodes a string16 to a `str`, so a caller that forgets to map
    `ord` over it gets characters where it wanted numbers. That conversion is
    the trap `studies/quests/FINDINGS.md` 3.5 names, and it costs one line here
    rather than a wrong answer at every call site.
    """
    if isinstance(value, str):
        return [ord(c) for c in value]
    return list(value)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("values", nargs="*", help="string ids to encode")
    ap.add_argument("--parse", nargs="+", metavar="WORD",
                    help="hex words to parse as a coded sequence")
    args = ap.parse_args()

    if args.parse:
        words = [int(w, 16) for w in args.parse]
        print("  " + " ".join(f"{w:04X}" for w in words))
        for kind, v in parse_coded(words):
            if kind == "marker":
                print(f"  marker  0x{v:04X}")
            else:
                print(f"  id      {v}  (re-encodes to "
                      f"{' '.join(f'{w:04X}' for w in encode_id(v))})")
        return 0

    if not args.values:
        ap.error("give string ids to encode, or --parse WORDS")
    for raw in args.values:
        sid = int(raw, 0)
        words = encode_id(sid)
        back, used = decode_id(words)
        print(f"  {sid:>8}  ->  {' '.join(f'{w:04X}' for w in words):20}"
              f"  roundtrip {'ok' if back == sid and used == len(words) else 'FAILED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
