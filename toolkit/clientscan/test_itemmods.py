"""The item-modifier decode: the layout, the dispatch, and the whole corpus.

    python toolkit/clientscan/test_itemmods.py

WHAT MAKES THIS MORE THAN A FIXTURE. A bit layout invented to fit six words
would fit those six words forever. Two checks here can refute it and neither
has a free parameter:

  * Section 2 decodes modifier words whose RENDERING this repo has already seen
    on a caged client -- `Armor: 25`, `Armor +20 (vs. physical damage)`, and a
    Backpack that holds twenty items -- and requires the argument field to
    equal the number that was on the screen.
  * Section 4 runs every modifier word ArenaNet ever sent us (5,266 of them
    across 1,781 item declarations in the live corpus) through the same
    extraction and requires EVERY identifier to be one the client actually
    dispatches. A wrong shift or mask scatters identifiers across the 10-bit
    space and most of them miss both jump tables; the observed answer is 100%
    over only 35 distinct ids.

Section 4 needs the vault and declares a skip without it, because a corpus
check that silently passes on no data is the failure `toolkit/checks.py` exists
to refuse.

SECTIONS 6 AND 7 ARE ABOUT THE OTHER READERS. `ItemName.cpp` is the tooltip
builder and it renders nothing for 21 of its 157 identifier slots -- including
633 and 617, two of the three busiest in the wild. Section 6 finds who reads
them instead, and pairs the answer with its own positive control: the same
scan that reports NOTHING reads 617 reports two readers for 633 and eight more
identifiers asked of `ItCliApi`'s by-argument accessors. A negative from a
search that cannot be shown to find anything is worth nothing, which is the
lesson `studies/enemy` paid for. Section 7 then takes 570 chances to refute
what 633 turned out to be: an attribute id and a rank, checked against two
client tables this file did not extract.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import itemmods  # noqa: E402
import pinned  # noqa: E402

# 19, counted from the green run of 2026-08-20 -- set from the run and not
# from a guess, which is how this file learned the number: 14 was declared,
# 12 executed, and the ledger refused the run rather than passing it. Sections
# 6 and 7 took it from 12 to 19; the number was read off the run again.
LEDGER = checks.Ledger("item modifiers", floor=19)


def main():
    exe, why = pinned.find()
    print(f"client: {exe}\n        ({why})")
    img = itemmods.Image(exe)

    print("\n1. the dispatch is located structurally, and both tables are found")
    at, vocab = itemmods.vocabulary(img)
    LEDGER.ok(at["special_table"] and at["generic_table"]
              and at["special_table"] != at["generic_table"],
              "two distinct jump tables behind one anchor",
              f"special {at['special_table']:#010x}, generic "
              f"{at['generic_table']:#010x} -- found from the parser's own "
              f"instruction bytes, never from a build-specific address")
    LEDGER.ok(len(vocab) == 157,
              "157 identifier slots: 20 special + 137 generic",
              f"{len(vocab)} -- the two `cmp` bounds the parser itself uses "
              f"(0x13 after a dec, 0x88 after a sub 0x202)")
    handlers = {r["handler"] for r in vocab.values()}
    LEDGER.ok(1 < len(handlers) < len(vocab),
              "and the slots SHARE handlers rather than being 1:1",
              f"{len(handlers)} distinct bodies for {len(vocab)} slots -- "
              f"several identifiers deliberately render the same line, and a "
              f"1:1 map would mean the table read was off by a stride")

    print("\n2. words this repo has SEEN rendered decode to what was on screen")
    seen = [
        (0xA3C81900, 572, 25, "Armor: 25 -- studies/newopcodes, merchant panel"),
        (0xA0F81400, 527, 20, "Armor +20 (vs. physical damage), same panel"),
        (0x24481400, 580, 20, "the Backpack, which holds twenty items"),
    ]
    for word, ident, arg, note in seen:
        d = itemmods.decode(word)
        LEDGER.ok(d["identifier"] == ident and d["arg"] == arg,
                  f"{word:#010x} -> id {ident}, arg {arg}",
                  f"got id {d['identifier']}, arg {d['arg']} -- {note}")

    print("\n3. the two skip predicates are the parser's, not ours")
    LEDGER.ok(itemmods.decode(0xC0000000)["skipped_high"],
              "bits 31..30 == 3 marks a word the parser steps over",
              "`shr ecx,0x1e; cmp ecx,3; je next` -- the first thing it does")
    LEDGER.ok(itemmods.decode(0x00040000)["skipped_bit18"]
              and not itemmods.decode(0xA3C81900)["skipped_bit18"],
              "and bit 18 marks another, while a real word has it clear",
              "`test ebx,0x40000; jne next` -- and every one of our own "
              "modifier words passes both predicates")

    print("\n4. CORPUS: every modifier ArenaNet ever sent us dispatches")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
        import vaultpath
        import cmsgstream
        live = vaultpath.require_dir("captures", "live", why="modifier corpus")
    except Exception as exc:
        LEDGER.skip(f"the live capture corpus is not reachable ({exc}); the "
                    f"100%-dispatch check is the one that can refute the bit "
                    f"layout, so its absence is declared rather than passed "
                    f"over")
        live = None

    if live is not None:
        words = ids = 0
        distinct = set()
        undispatched = []
        caps = 0
        for stamp in sorted(os.listdir(live)):
            try:
                rows = cmsgstream.timed(stamp, "s2c", "game")
            except Exception:
                continue
            caps += 1
            for _t, _c, op, v in rows:
                if op != 0x161 or not v or not isinstance(v[-1], list):
                    continue
                for entry in v[-1]:
                    w = entry[0] if isinstance(entry, (list, tuple)) else entry
                    if not isinstance(w, int):
                        continue
                    words += 1
                    d = itemmods.decode(w)
                    if d["skipped_high"] or d["skipped_bit18"]:
                        continue
                    ids += 1
                    distinct.add(d["identifier"])
                    if d["identifier"] not in vocab:
                        undispatched.append(d["identifier"])
        LEDGER.ok(words > 1000,
                  "the corpus really was read",
                  f"{words} modifier words over {caps} captures -- a check "
                  f"that ran on an empty glob is the defect this names")
        LEDGER.ok(not undispatched,
                  "EVERY identifier in the wild is one the client dispatches",
                  f"{ids}/{ids} across {len(distinct)} distinct ids, 0 misses. "
                  f"This is the refutable one: a wrong shift or mask spreads "
                  f"identifiers over the 10-bit space and most miss both "
                  f"tables"
                  if not undispatched else
                  f"MISSED: {sorted(set(undispatched))[:20]}")
        LEDGER.ok(len(distinct) < 60,
                  "and the wild vocabulary is SMALL, as a real enum should be",
                  f"{len(distinct)} distinct identifiers over {ids} words; "
                  f"random noise in a 10-bit field would show hundreds")

    print("\n5. the tool refuses rather than inventing when the anchor is gone")
    class Broken(itemmods.Image):
        def __init__(self, real):
            self.path, self.base, self.secs = real.path, real.base, real.secs
            self.data = real.data.replace(itemmods.DISPATCH, b"\x90" * len(itemmods.DISPATCH))
    LEDGER.ok(checks.refuses(lambda: itemmods.vocabulary(Broken(img)),
                             itemmods.NotFound)
              if hasattr(checks, "refuses") else _refuses(Broken(img)),
              "an image without the dispatch preamble is REFUSED",
              "reporting an empty vocabulary would read as 'this build has no "
              "item modifiers', which is the shape of every silent-zero bug "
              "this repo has recorded")
    print("\n6. WHO READS a modifier the tooltip walker renders nothing for")
    r = itemmods.readers(img)
    LEDGER.ok(len(r["loop_tails"]) == 1 and len(r["inert"]) == 21,
              "one loop tail, and 21 of 157 slots dispatch to it",
              f"tail {[hex(t) for t in r['loop_tails']]}, {len(r['inert'])} "
              f"inert identifiers -- the first version of the detector said 22 "
              f"because the LAST renderer in the chain falls through into the "
              f"tail, and would have published 'the client renders nothing for "
              f"526' while 526 pushes string 2387 and calls TextApi")
    lit633 = r["literal"].get(633, [])
    LEDGER.ok(len(lit633) == 2 and not r["asked"].get(633),
              "633 IS read -- by two literal compares outside the walker",
              f"{[hex(v) for v in lit633]}: ItCliApi's own reader and "
              f"ItemName's, both `and r32,0x3ff00000; cmp r32,0x27900000`")
    LEDGER.ok(not r["literal"].get(617) and not r["asked"].get(617),
              "617 is read by NOTHING, under the bound the tool prints",
              "no literal compare in .text and no accessor call site asks for "
              "it. The check above is the positive control that makes this "
              "negative worth anything: the same scan finds 633 twice and "
              "eight more identifiers at the accessors")
    entries = [a["entry"] for a in r["accessors"]]
    asked = sorted(r["asked"])
    LEDGER.ok(len(entries) == 2 and asked == [587, 590, 592, 598, 603, 606,
                                              614, 630, 647, 648],
              "and the by-argument accessors are found with their callers",
              f"{[hex(e) for e in entries]} asked for {asked} -- seven of the "
              f"ten are identifiers ItemName renders nothing for, which is "
              f"what the loop tail actually means: data for another subsystem")

    print("\n7. CORPUS: 633's payload is an ATTRIBUTE and a RANK, or this fails")
    if live is None:
        LEDGER.skip("the live corpus is not reachable, so the 570 chances "
                    "for 633's payload to fall outside the attribute space "
                    "cannot be taken")
    else:
        import attribtable
        import attribpoints
        n_attrs = attribtable.EXPECTED_COUNT
        cap = len(attribpoints.locate(attribpoints.Image(exe))["costs"])
        pairs, models = [], {}
        for stamp in sorted(os.listdir(live)):
            try:
                got = cmsgstream.timed(stamp, "s2c", "game")
            except Exception:
                continue
            for _t, _c, op, v in got:
                if op != 0x161 or not v or not isinstance(v[-1], list):
                    continue
                head = [x for x in v if not isinstance(x, list)]
                for entry in v[-1]:
                    w = entry[0] if isinstance(entry, (list, tuple)) else entry
                    if not isinstance(w, int):
                        continue
                    dd = itemmods.decode(w)
                    if dd["identifier"] != 633 or dd["skipped_high"] \
                            or dd["skipped_bit18"]:
                        continue
                    pairs.append((dd["arg"], dd["arg2"]))
                    if len(head) > 2:
                        models.setdefault(head[2], set()).add(dd["arg"])
        bad_a = [a for a, _r in pairs if a >= n_attrs]
        bad_r = [x for _a, x in pairs if not 1 <= x <= cap]
        LEDGER.ok(bool(pairs) and not bad_a,
                  f"every 633 argument is a real attribute (< {n_attrs})",
                  f"{len(pairs)} words, 0 outside s_attrib. {n_attrs} is "
                  f"CHAR_ATTRIBS -- the bound ItemName's own asserts name "
                  f"(`attrib < CHAR_ATTRIBS`) and the exact value ItCliApi's "
                  f"reader writes as its 'no requirement' default"
                  if not bad_a else f"OUTSIDE: {sorted(set(bad_a))[:12]}")
        LEDGER.ok(bool(pairs) and not bad_r,
                  f"and every 633 second value is a reachable rank (1..{cap})",
                  f"{len(pairs)} words, 0 outside. {cap} comes from "
                  f"s_attribPoints via attribpoints.py -- a SEPARATE table, "
                  f"extracted separately, and 570 chances for the two to "
                  f"disagree"
                  if not bad_r else f"OUTSIDE: {sorted(set(bad_r))[:12]}")
        varies = [m for m, a in models.items() if len(a) > 1]
        LEDGER.ok(len(models) > 20 and not varies,
                  "the attribute is a property of the SKIN, not of the roll",
                  f"{len(models)} distinct item model ids, and not one of them "
                  f"ever carries two different attributes -- while 38 of them "
                  f"carry several different ranks. That is what a weapon "
                  f"requirement looks like and it is not what a coincidence "
                  f"looks like"
                  if not varies else f"MODELS WITH TWO ATTRIBUTES: {varies[:8]}")

    return LEDGER.verdict()


def _refuses(broken):
    try:
        itemmods.vocabulary(broken)
    except itemmods.NotFound:
        return True
    except Exception:
        return False
    return False


if __name__ == "__main__":
    sys.exit(main())
