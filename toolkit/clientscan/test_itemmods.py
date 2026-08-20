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
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import itemmods  # noqa: E402
import pinned  # noqa: E402

# 12, counted from the green run of 2026-08-20 -- set from the run and not
# from a guess, which is how this file learned the number: 14 was declared,
# 12 executed, and the ledger refused the run rather than passing it.
LEDGER = checks.Ledger("item modifiers", floor=12)


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
