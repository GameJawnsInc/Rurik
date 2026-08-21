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

SECTIONS 8-10 ARE THE ATTRIBUTE BONUS, found by a different route: not by
reading templates but by asking which handlers RESOLVE AN ATTRIBUTE NAME
through `s_attrib`. Fourteen do -- against the two an assert-derived count
claimed -- and the two that render `<attribute> +N` are 542 (Non-stacking) and
543 (Stacking). Section 9 composes 543's word from the four fields plus the
three bits the walker never reads, and requires it to equal ArenaNet's own
dword; section 10 replays all 26 the live corpus holds and measures the
constant-prefix fact the composer rests on.

SECTIONS 12-14 ARE WHAT MAKES "NOTHING READS 617" A MEASUREMENT. Section 6's
negative rested on two searches coming back empty, which is worth little on its
own -- `studies/enemy` 6o closed a question for a session on exactly that shape
of evidence and was wrong. Section 12 bounds it instead: to read an identifier
the client must isolate bits 29-20, x86 leaves two ways to do it, and an
exhaustive scan of .text finds SIXTEEN such sites in the whole image. Section
13 repeats that on all three builds. Section 14 supplies the positive half,
because a finding that is only an absence is hard to build on: 617 is a
per-MODEL constant, 71/71, with the file id as the control that does NOT
determine it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import itemmods  # noqa: E402
import pinned  # noqa: E402

# 28, counted from the green run of 2026-08-20 -- set from the run and not
# from a guess, which is how this file learned the number: 14 was declared,
# 12 executed, and the ledger refused the run rather than passing it. Sections
# 6 and 7 took it from 12 to 19 , sections 8-10 to 28, 11 to 30, and 12-14 to 37;
# each time the number was read off the run rather than predicted.
LEDGER = checks.Ledger("item modifiers", floor=37)


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

    print("\n8. the ATTRIBUTE BONUS: found by who resolves an attribute NAME")
    acc = itemmods.attribute_name_accessor(img)
    fam = itemmods.attribute_identifiers(img)
    LEDGER.ok(sorted(acc["fields"]) == [0, 8, 12, 16],
              "s_attrib's four field accessors are located by their shape",
              f"base {acc['base']:#010x}, fields at +0 +8 +12 +16 -- the "
              f"lowest displacement IS the base, so the name-id accessor "
              f"(base+8) is found without knowing the table's address on any "
              f"particular build")
    LEDGER.ok(len(fam) == 14 and {1, 542, 543, 577} <= set(fam),
              "and FOURTEEN handlers resolve an attribute name, not two",
              f"{sorted(fam)}. This is a correction: studies/itemmods said "
              f"'exactly two handlers treat their argument as an attribute "
              f"index, 1 and 14', a number taken from the two asserts naming "
              f"`attrib < CHAR_ATTRIBS` -- and asserts.py says in its own "
              f"output that its module lists are a FLOOR, not a census")
    v542 = vocab[542]["text_ids"]
    v543 = vocab[543]["text_ids"]
    LEDGER.ok(2482 in v542 and 2481 in v543 and 2436 in v542,
              "542 and 543 are one line differing by ONE word",
              f"542 {v542} carries 2482 (Non-stacking), 543 {v543} carries "
              f"2481 (Stacking), and both format 2436 `%str1% +%num1%` with "
              f"the attribute NAME as the string and arg2 as the number")

    print("\n9. the composed word is ArenaNet's word, byte for byte")
    LEDGER.ok(itemmods.attribute_bonus_word(20, 1) == 0x21F81401,
              "attribute_bonus_word(20, 1) == 0x21F81401",
              "the exact dword on 26 retail headpieces in the live corpus -- "
              "identifier 543, attribute 20, +1, AND the three bits the "
              "walker never reads (31, 30, 19). Compose from the four fields "
              "alone and you get 0x21F01401, which is not what retail sends")
    try:
        itemmods.attribute_bonus_word(itemmods.ATTRIBUTES, 1)
        refused = False
    except ValueError:
        refused = True
    LEDGER.ok(refused,
              f"and it REFUSES an attribute outside s_attrib",
              f"attribute {itemmods.ATTRIBUTES} is CHAR_ATTRIBS itself -- the "
              f"client asserts on it, so composing one would build a word "
              f"that trips ItemName:1202 rather than one that renders")

    if live is None:
        LEDGER.skip("the live corpus is not reachable, so the 26 retail "
                    "attribute-bonus words cannot be replayed and the "
                    "constant-prefix measurement the composer rests on cannot "
                    "be taken")
    else:
        print("\n10. CORPUS: 543's real words, and the prefix the composer uses")
        bonus_words, kinds, with_armour = [], set(), 0
        prefix = {}
        exceptions = []
        for stamp in sorted(os.listdir(live)):
            try:
                got = cmsgstream.timed(stamp, "s2c", "game")
            except Exception:
                continue
            for _t, _c, op, v in got:
                if op != 0x161 or not v or not isinstance(v[-1], list):
                    continue
                head = [x for x in v if not isinstance(x, list)]
                ws = [e[0] if isinstance(e, (list, tuple)) else e
                      for e in v[-1]]
                ws = [x for x in ws if isinstance(x, int)]
                for x in ws:
                    dd = itemmods.decode(x)
                    if dd["skipped_high"] or dd["skipped_bit18"]:
                        continue
                    key = ((x >> 30) & 3, (x >> 19) & 1)
                    seen_pfx = prefix.setdefault(dd["identifier"], key)
                    if seen_pfx != key:
                        exceptions.append((dd["identifier"], seen_pfx, key))
                for b in itemmods.attribute_bonuses(ws):
                    bonus_words.append((b, ws))
                    if len(head) > 3:
                        kinds.add(head[3])
                    if any(itemmods.decode(x)["identifier"] == 572 for x in ws):
                        with_armour += 1
        LEDGER.ok(len(bonus_words) == 26
                  and all(b["identifier"] == 543 and b["stacking"]
                          and b["attribute"] == 20 and b["amount"] == 1
                          for b, _ in bonus_words),
                  "every attribute bonus ArenaNet sent us is 543, attr 20, +1",
                  f"{len(bonus_words)} of them, and attribute 20 resolves "
                  f"through s_attrib to a Warrior weapon attribute -- on "
                  f"items that also carry an armour rating (572) and a "
                  f"'+20 vs. physical' (527). A headpiece, which is exactly "
                  f"what a STACKING attribute bonus belongs on")
        LEDGER.ok(len(kinds) == 1 and with_armour == len(bonus_words),
                  "and they are all ONE item type, all of them armour",
                  f"item type field {kinds}, {with_armour}/{len(bonus_words)} "
                  f"carrying an armour rating -- a bonus scattered across "
                  f"weapon types would refute the reading")
        LEDGER.ok(all(itemmods.attribute_bonus_word(b["attribute"],
                                                    b["amount"]) == w
                      for b, ws in bonus_words
                      for w in ws
                      if itemmods.decode(w)["identifier"] == 543),
                  "the composer reproduces each of those words exactly",
                  "26 chances for a wrong prefix or a swapped field to show")
        LEDGER.ok(not exceptions and len(prefix) > 30,
                  "bits 31, 30 and 19 are CONSTANT per identifier",
                  f"{len(prefix)} identifiers over the whole corpus, 0 "
                  f"exceptions -- which is why they are a fixed prefix of the "
                  f"encoding and why the composer can carry them. A single "
                  f"identifier whose prefix varied would mean they are a "
                  f"payload and the composer is wrong"
                  if not exceptions else f"VARIES: {exceptions[:6]}")

    print("\n11. our own content: the declared bonus and the WORD agree")
    try:
        import content as contentmod
        world = contentmod.load()
        items = world.rows("item")
    except Exception as exc:
        items = None
        LEDGER.skip(f"content/items.toml is not loadable ({exc}), so the one "
                    f"guard standing between a declared attribute_bonus and "
                    f"the modifier word that now says the same thing cannot "
                    f"run")

    if items is not None:
        def declared(row):
            return {(int(a), int(n)) for a, n in row.get("attribute_bonus", [])}

        def encoded(row):
            return {(b["attribute"], b["amount"])
                    for b in itemmods.attribute_bonuses(row.get("modifiers", []))
                    if b["identifier"] in itemmods.ATTRIBUTE_BONUS}

        disagree = [(k, declared(r), encoded(r)) for k, r in items.items()
                    if declared(r) != encoded(r)]
        carriers = [k for k, r in items.items() if declared(r) or encoded(r)]
        LEDGER.ok(carriers and not disagree,
                  "every item's attribute_bonus matches its modifier words",
                  f"{len(carriers)} item(s) carry one ({carriers}), 0 "
                  f"disagreements. Two places now hold the same fact -- the "
                  f"field drives the server's 0x003B effective column, the "
                  f"word drives what the CLIENT draws -- and 34.5 of "
                  f"studies/pvpui is about exactly this shape of bug. This is "
                  f"the guard that keeps it from being one"
                  if not disagree else f"DISAGREE: {disagree}")
        bent = dict(items["starter_hammer"])
        bent["attribute_bonus"] = [[19, 2]]
        LEDGER.ok(declared(bent) != encoded(bent),
                  "CONTROL: bending the declared field to +2 breaks the check",
                  "a guard that cannot go red is not a guard, and this one "
                  "exists only because the duplication was introduced on "
                  "purpose")

    print("\n12. the extraction CENSUS: what bounds the negative on 617")
    cen = itemmods.identifier_sites(img)
    named = sorted({r["names"] for r in cen["named"]})
    LEDGER.ok(cen["total"] < 40 and len(cen["named"]) > 5
              and cen["parametric"] and cen["dispatch"],
              "the WHOLE image isolates a modifier identifier in 16 places",
              f"{cen['total']} sites: {len(cen['named'])} naming a literal, "
              f"{len(cen['parametric'])} comparing a register, "
              f"{len(cen['dispatch'])} routing through the jump table. A "
              f"reader must isolate bits 29-20 to exist and x86 leaves two "
              f"ways to do it, so this is a bounded total rather than two "
              f"searches that came back empty -- which is the difference "
              f"studies/enemy 6o paid for")
    LEDGER.ok(cen["not_modifier"] > 50,
              "and the census separates the float band from item code",
              f"{cen['not_modifier']} further sites match the same mask and "
              f"are NOT modifier reads -- 0x3ff00000 is also a double's "
              f"exponent mask. Counting them is what makes this a census of "
              f"the instruction rather than a census of what we hoped to find")
    LEDGER.ok(633 in named and 617 not in named,
              "633 is named by a literal; 617 is named by nothing",
              f"identifiers named anywhere in the image: {named}. The control "
              f"is inside the check: the same scan that cannot find 617 finds "
              f"633 at two sites and nine other identifiers besides")

    print("\n13. and the census says the same on ALL THREE builds")
    across = {}
    for b in pinned.BUILDS:
        try:
            exe_b, _why = pinned.find(build=b.number)
        except SystemExit:
            continue
        c = itemmods.identifier_sites(itemmods.Image(exe_b))
        across[b.number] = (c["total"], tuple(sorted({r["names"]
                                                      for r in c["named"]})))
    if len(across) < 2:
        LEDGER.skip("fewer than two builds are in the vault, so the "
                    "out-of-sample half of the 617 negative cannot run")
    else:
        vals = set(across.values())
        LEDGER.ok(len(vals) == 1,
                  f"identical census on {len(across)} builds",
                  f"{ {k: v[0] for k, v in across.items()} } sites and the "
                  f"same eleven identifiers each time -- including 1, which "
                  f"shares 633's mask and is named eight bytes later, so a "
                  f"census stopping at the first compare would miss it. A "
                  f"negative that held "
                  f"on one build could be a quirk of that build; holding "
                  f"across 38519, 38797 and 38833 is a property of the client"
                  if len(vals) == 1 else f"DIFFER: {across}")
        LEDGER.ok(all(617 not in v[1] for v in across.values()),
                  "617 is named on none of them",
                  "and 633 is named on all of them, which is the control "
                  "riding along with the claim")

    if live is None:
        LEDGER.skip("the live corpus is not reachable, so 617's one positive "
                    "property -- that it is a per-MODEL constant -- cannot "
                    "be measured, and the arc would rest on the negative alone")
    else:
        print("\n14. CORPUS: 617 is a constant of the item's MODEL")
        by_model, by_file = {}, {}
        seen617 = 0
        for stamp in sorted(os.listdir(live)):
            try:
                got = cmsgstream.timed(stamp, "s2c", "game")
            except Exception:
                continue
            for _t, _c, op, v in got:
                if op != 0x161 or not v or not isinstance(v[-1], list):
                    continue
                head = [x for x in v if not isinstance(x, list)]
                if len(head) < 11:
                    continue
                val = None
                for e in v[-1]:
                    x = e[0] if isinstance(e, (list, tuple)) else e
                    if not isinstance(x, int):
                        continue
                    dd = itemmods.decode(x)
                    if (dd["identifier"] == 617 and not dd["skipped_high"]
                            and not dd["skipped_bit18"]):
                        val = dd["arg2"]
                if val is None:
                    continue
                seen617 += 1
                by_model.setdefault(head[10], set()).add(val)
                by_file.setdefault(head[2], set()).add(val)
        split_model = [k for k, s2 in by_model.items() if len(s2) > 1]
        split_file = [k for k, s2 in by_file.items() if len(s2) > 1]
        LEDGER.ok(seen617 > 300 and by_model and not split_model,
                  "one 617 value per model id, over the whole corpus",
                  f"{seen617} words across {len(by_model)} model ids, "
                  f"{len(by_model)}/{len(by_model)} single-valued. So the "
                  f"client already knows this number from the model -- which "
                  f"is CONSISTENT with nothing reading it, though it does not "
                  f"prove that is the reason")
        LEDGER.ok(split_file,
                  "CONTROL: the item's FILE id does not determine it",
                  f"{len(split_file)} of {len(by_file)} file ids carry more "
                  f"than one 617 value. Without this the model result would "
                  f"be unreadable -- any field with small enough groups looks "
                  f"deterministic, and this is the field that does not"
                  if split_file else
                  "file id determines it too, so the model result says nothing")

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
