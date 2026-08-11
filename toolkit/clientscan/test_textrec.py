#!/usr/bin/env python3
r"""Check the text-record codec against the client's own code and its own data.

    python toolkit/clientscan/test_textrec.py

Every section below states its oracle, and every one of them can fail:

  1. The escape table is located by ArenaNet's assert path string and is
     bounded on BOTH sides -- padding and a known string above it, its own
     zero slot below. An array that merely "looks long enough" proves nothing.
  2. The client's own file walker rejects any record whose width byte exceeds
     0x10 (Gw.exe 0x7ca382). Real data must satisfy the client's own gate, and
     the byte above that field must be zero. Nothing in our decoder forces it.
  3. `base == 0` must imply `bits == 0x10`. The client's verbatim path tests
     BOTH (0x7cb16a), so a record with a zero base and a narrow width would be
     decoded as raw UTF-16 by the client and as symbols by us. There are none.
  4. THE ORACLE FOR "bits IS A WIDTH, NOT A KIND": the same record index in a
     wide-script language must need more bits than in English. A type tag has
     no reason to correlate with the writing system; a bit width must.
  5. The key-derivation hash on this path is the one the game channel already
     uses. Checked by computing arc4_hash's folded round constants from its
     specification and finding them as immediates in the image. If the text
     path used a different hash these would not be there.
  6. Encrypted payloads must be indistinguishable from random and plain ones
     must not. This is what makes "we cannot read them" a measurement.
  7. The refuted key readings, kept as a live check so the next session does
     not spend an afternoon re-refuting them.
  8. Plain decode still lands on real place names.

Sections 4 and 8 name a few real place names and one Korean map name as the
decode oracle. Without a concrete expected string a decode test cannot tell
correct text from convincing garbage, and these are names the game puts on
screen, not extracted assets.
"""

import collections
import math
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))

import checks                                       # noqa: E402
import textrec                                      # noqa: E402
import skilltable                                   # noqa: E402
from gwpe import PE                                 # noqa: E402
from gwcrypto import arc4_hash, ARC4                # noqa: E402

# (string id, expected text) in language 0. Ids come from the area table.
ORACLE = [
    (10478, "Ascalon City"),
    (10464, "Lakeside County"),
    (10362, "Lion's Arch"),
]

# Language 1 is Korean; record 470 of file 10 is the Guild Practice Arena.
WIDE_LANGUAGE = 1
WIDE_SAMPLE = (10, 470, "길드")     # the decode must start "길드"

# The languages section 4 compares against English. Polish is the load-bearing
# one: Latin script, but diacritics outside Latin-1.
SCRIPTS = ((1, "Korean"), (2, "French"), (9, "Polish"))

MAX_PLAIN_ENTROPY = 5.0     # plain UTF-16LE English is nowhere near uniform
MIN_CIPHER_ENTROPY = 7.8    # 8.000 measured; the margin is for short widths
KEY_PROBE_RECORDS = 400

# The floor counts a real green run of 2026-08-06, section by section: 6 escape
# table + 3 file-walk gate + 2 zero-base + 7 width-vs-script + 3 key hash + 2
# entropy + 7 refuted keys + 4 plain decode + 1 skill-id sweep = 35. Nothing here
# is optional and nothing is fixture-dependent -- every section reads the same
# Gw.exe, so the count only moves when SCRIPTS, `schemes` or ORACLE gain an
# entry, which can only push it up. A run that lands under 35 has had a section
# stop executing, which is exactly the failure this file could not previously
# report: sections 4 and 7 loop over dicts, and a loop over an empty dict prints
# a heading, asserts nothing and looks identical to a pass.
LEDGER = checks.Ledger("text records", floor=35)
check = checks.adopt(LEDGER)


def entropy(counter):
    n = sum(counter.values())
    if not n:
        return 0.0
    return -sum((v / n) * math.log2(v / n) for v in counter.values())


def main():
    t0 = time.perf_counter()
    pe = PE(textrec.find_exe()[0])

    print("\n1. the escape table is bounded at both ends")
    off = textrec.find_escape_table(pe)
    va = pe.off_to_rva(off) + pe.image_base
    check(True, "located from the TextDecode.cpp assert anchor", f"VA 0x{va:08x}")
    table = textrec.escape_table(pe)
    check(len(table) == textrec.ESCAPE_COUNT, "entry count",
          str(len(table)))
    check(table[0] == 0, "slot 0 is the unused NUL slot the decoder skips")
    check(len(set(table[1:])) == textrec.ESCAPE_COUNT - 1,
          "the other 31 entries are distinct")
    # Bounded above: the bytes after the table are padding, then the anchor.
    after = pe.data[off + 2 * textrec.ESCAPE_COUNT:]
    pad = 0
    while struct.unpack_from("<H", after, pad)[0] == 0:
        pad += 2
    check(after[pad:].startswith(textrec.TEXTDECODE_CPP),
          "the table runs up to the assert string, with only padding between",
          f"{pad} pad bytes")
    # Bounded below: the word before slot 0 is not another plausible entry.
    check(struct.unpack_from("<H", pe.data, off - 2)[0] not in range(0x20, 0x7F),
          "the word below the table is not another character")

    with textrec.TextIndex(textrec.find_exe()[0]) as ix:
        print("\n2. every record satisfies the client's own file-walk gate")
        widths = collections.Counter()
        bad_width = bad_pad = 0
        for fi in range(textrec.FILES_PER_LANGUAGE):
            blob_recs = ix.records(fi)
            for bits, base, _p in blob_recs:
                widths[bits] += 1
                if not 1 <= bits <= textrec.MAX_BITS:
                    bad_width += 1
                if bits >> 8:
                    bad_pad += 1
        total = sum(widths.values())
        check(total == textrec.FILES_PER_LANGUAGE * textrec.RECORDS_PER_FILE,
              "record count", f"{total}")
        check(bad_width == 0,
              "every width is inside the client's own 1..0x10 range check",
              f"{bad_width} outside")
        check(bad_pad == 0, "the byte above the width field is always zero",
              f"{bad_pad} non-zero")

        print("\n3. a zero base implies the 16-bit verbatim form")
        offenders = 0
        plain = 0
        for fi in range(textrec.FILES_PER_LANGUAGE):
            for bits, base, _p in ix.records(fi):
                if base == 0 and bits != textrec.MAX_BITS:
                    offenders += 1
                if textrec.is_plain(bits, base):
                    plain += 1
        check(offenders == 0,
              "no record has a zero base with a narrow width", f"{offenders}")
        check(plain == 28407, "records the client copies out verbatim",
              f"{plain}")

        print("\n4. width tracks the writing system, which a type tag would not")

        def survey(index):
            """(set of encrypted slots, wide share of them) for one language."""
            slots, wide = set(), 0
            for fi in range(textrec.FILES_PER_LANGUAGE):
                for ri, (bits, base, _p) in enumerate(index.records(fi)):
                    if not textrec.is_plain(bits, base):
                        slots.add((fi, ri))
                        if bits > 8:
                            wide += 1
            return slots, wide / max(len(slots), 1)

        eng_slots, eng_wide = survey(ix)
        shares = {"English": eng_wide}
        for lang, name in SCRIPTS:
            with textrec.TextIndex(textrec.find_exe()[0], language=lang) as other:
                slots, share = survey(other)
                shares[name] = share
                # Which slots are encrypted is a property of the SLOT, not of
                # the language. Set equality, not just equal counts.
                check(slots == eng_slots,
                      f"{name} encrypts exactly the same slots as English",
                      f"{len(slots)} vs {len(eng_slots)}")
                if lang == WIDE_LANGUAGE:
                    bits, base, payload = other.records(
                        WIDE_SAMPLE[0])[WIDE_SAMPLE[1]]
                    got = textrec.decode(bits, base, payload, other.escape)
                    check(got is not None and got.startswith(WIDE_SAMPLE[2]),
                          "and that language really is the one we think",
                          repr(got))
        for name, share in shares.items():
            print(f"        {name:9} {share:6.1%} of encrypted records use "
                  f"more than 8 bits")
        check(shares["English"] < 0.01 and shares["French"] < 0.01,
              "Latin-script languages almost never need a wide symbol")
        check(shares["Korean"] > 0.90,
              "the Korean text does, nearly always", f"{shares['Korean']:.1%}")
        # The one that no 'kind is a type tag' reading survives: Polish is a
        # Latin script, so a tag would put it with French. Its diacritics sit
        # outside Latin-1, which a CONTIGUOUS base window cannot cover -- so a
        # width must rise. It does, by three orders of magnitude over French.
        check(shares["Polish"] > 0.50,
              "Polish is Latin-script yet wide, which only a width explains",
              f"{shares['Polish']:.1%} vs French {shares['French']:.1%}")

        print("\n5. this path's key hash is the game channel's key hash")
        # arc4_hash folds a fixed SHA-1 IV, so its first two round constants
        # are compile-time values. They must appear as immediates in the image.
        M = 0xFFFFFFFF
        A, B, C, D, E = (0x67452301, 0xEFCDAB89, 0x98BADCFE,
                         0x10325476, 0xC3D2E1F0)

        def rol(x, n):
            return ((x << n) | ((x & M) >> (32 - n))) & M

        c1 = (E + rol(A, 5) + (D ^ (B & (C ^ D))) + 0x5A827999) & M
        brot = rol(B, 30)
        c2 = (D + (C ^ (A & (brot ^ C))) + 0x5A827999) & M
        for name, c in (("round 1", c1), ("round 2", c2)):
            hits = pe.find(struct.pack("<I", c))
            check(len(hits) > 0,
                  f"arc4_hash's folded {name} constant is in the image",
                  f"0x{c:08X} x{len(hits)}")
        # And the primitive still round-trips, so the import is live.
        probe = textrec.record_key((1, 2))
        check(len(probe) == 20 and ARC4(probe).crypt(b"\0" * 4) != b"\0" * 4,
              "record_key produces a live 20-byte ARC4 key")

        print("\n6. encrypted payloads are random and plain ones are not")
        by_form = {}
        for fi in range(textrec.FILES_PER_LANGUAGE):
            for bits, base, p in ix.records(fi):
                by_form.setdefault(textrec.is_plain(bits, base),
                                   collections.Counter()).update(p)
        e_plain = entropy(by_form[True])
        e_ciph = entropy(by_form[False])
        check(e_plain < MAX_PLAIN_ENTROPY, "plain payload entropy is low",
              f"{e_plain:.3f} bits/byte")
        check(e_ciph > MIN_CIPHER_ENTROPY, "non-plain payload entropy is flat",
              f"{e_ciph:.3f} bits/byte")

        print("\n7. the refuted key readings stay refuted")
        sample = []
        for fi in range(textrec.FILES_PER_LANGUAGE):
            aid = ix.archive_id(fi)
            for ri, (bits, base, p) in enumerate(ix.records(fi)):
                if bits == 7 and len(p) >= 24:
                    sample.append((fi, ri, base, aid, p))
            if len(sample) >= KEY_PROBE_RECORDS:
                break
        sample = sample[:KEY_PROBE_RECORDS]
        raw = collections.Counter()
        for _fi, _ri, _b, _a, p in sample:
            raw.update(textrec.unpack_symbols(7, p))
        base_e = entropy(raw)
        check(base_e > 6.9, "undecrypted control is uniform over 128 symbols",
              f"{base_e:.3f}")
        schemes = {
            "sid,0":    lambda fi, ri, b, a: (fi * 1024 + ri, 0),
            "0,sid":    lambda fi, ri, b, a: (0, fi * 1024 + ri),
            "ri,lang":  lambda fi, ri, b, a: (ri, 0),
            "fi,ri":    lambda fi, ri, b, a: (fi, ri),
            "aid,ri":   lambda fi, ri, b, a: (a, ri),
            "sid,base": lambda fi, ri, b, a: (fi * 1024 + ri, b),
        }
        for name, fn in schemes.items():
            pool = collections.Counter()
            for fi, ri, b, a, p in sample:
                key = textrec.record_key(fn(fi, ri, b, a))
                pool.update(textrec.unpack_symbols(7, ARC4(key).crypt(p)))
            e = entropy(pool)
            # If one of these ever DROPS, the key is found and this must fail
            # loudly rather than pass quietly.
            check(e > 6.9, f"'{name}' still yields nothing but noise",
                  f"{e:.3f}")

        print("\n8. plain decode still lands on real names")
        for sid, want in ORACLE:
            check(ix.get(sid) == want, f"string {sid}", repr(ix.get(sid)))
        check(ix.needs_key(ORACLE[0][0]) is False, "and reports needing no key")

        print("\n9. every string id a Gw.exe table points at is readable")
        data = pe.data
        base_off, count, _ = skilltable.locate_table(data)
        rows = [skilltable.parse_record(data, base_off, i) for i in range(count)]
        ids = [r[f] for r in rows for f in ("name_id", "concise_id",
                                            "description_id") if r[f]]
        need = [sid for sid in ids if ix.needs_key(sid)]
        dead = {r["id"] for r in rows
                if r["linked_id"] >= count and r["energy"] == 0
                and r["recharge"] == 0 and r["activation"] == 0.0}
        from_dead = [sid for sid in need
                     if any(sid in (r["name_id"], r["concise_id"],
                                    r["description_id"])
                            for r in rows if r["id"] in dead)]
        check(len(need) == len(from_dead),
              "every skill id needing a key belongs to a dead row",
              f"{len(need)} need a key, {len(from_dead)} from dead rows, "
              f"{len(ids)} ids total")

    dt = time.perf_counter() - t0
    print(f"\nread the image and all four languages in {dt:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
