"""Decode the client's ITEM MODIFIER format and its identifier vocabulary.

    python toolkit/clientscan/itemmods.py --summary
    python toolkit/clientscan/itemmods.py --decode 0xA3C81900
    python toolkit/clientscan/itemmods.py --readers
    python toolkit/clientscan/itemmods.py --reads 633
    python toolkit/clientscan/itemmods.py --emit-content vault/content/item_modifiers.toml

THE HOLE THIS FILLS. Every item on the wire carries a list of 32-bit modifier
words -- `0x0161 CREATE_NAMED_ITEM`'s trailing array, and `content/items.toml`
has carried literal ones since the character arc. An item's armour rating, its
damage range, its attribute requirement and every "+15% while..." line live in
them, and until 2026-08-20 nobody in this repo had decoded a single one.
`studies/character/FINDINGS.md` called it "the largest hole" three times.

THE FORMAT, read out of the client's own parser rather than guessed. The walker
steps a dword array and does exactly this to each word:

    mov  ebx, [edx]                  ; the modifier
    shr  ecx, 0x1e / cmp ecx, 3      ; bits 31..30 == 3        -> skip it
    test ebx, 0x40000                ; bit 18 set              -> skip it
    shr  eax, 0x14 / and eax, 0x3ff  ; bits 29..20 = IDENTIFIER
    cmp  eax, 0x201 / ja / je        ; >513 generic, ==513 special
    dec eax / cmp eax, 0x13 / ja     ; 1..20 -> the special table
    jmp  [eax*4 + <table1>]
    ...
    sub eax, 0x202 / cmp eax, 0x88   ; 514..650
    jmp  [eax*4 + <table2>]

and the handlers read their operands back out of the same word:

    shr ebx, 8 / and ebx, 0x3ff      ; bits 17..8  = ARGUMENT (10 bits)
    movzx eax, byte ptr [edx]        ; bits  7..0  = a second value

So: `{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}`, with two skip
predicates above them. That layout is confirmed against items whose rendering
this repo has already SEEN on screen: the starter armour's `0xA3C81900` is
identifier 572 argument 25, and the client drew "Armor: 25"; `0xA0F81400` is
527/20 and drew "Armor +20 (vs. physical damage)"; the Backpack's `0x24481400`
is 580/20 and the Backpack holds twenty items.

WHAT EACH IDENTIFIER MEANS COMES FROM ARENANET'S OWN WORDS, not from a guess.
Every handler formats its line through TextApi, and the string id it passes is
the template: 572 pushes 2438 `'%str1%: %num1%'` with 2372 `'Armor'`, and 580
pushes 2464 `'Holds %num1% items'`. This tool walks each handler and records
those ids. It emits the IDS, never the resolved English -- "commit the id,
resolve the string at run time", the rule `mapbuild.py` already proves -- and
`--summary` resolves a few through `textrec` for reading, which is measurement
cited as evidence rather than a bulk dump.

WHO READS WHAT, which is a different question from what renders. `ItemName.cpp`
is the name and tooltip builder, and 21 of its 157 dispatch slots go to the
walker's loop tail -- it draws nothing for them, on purpose. Eight of those 21
are read somewhere else: `ItCliApi.cpp` names 633 with its own `cmp`, and its
two by-argument accessors are asked for seven more. `--readers` maps all of it
and prints the bound its own absences carry; `--reads N` answers for one
identifier. That is how 633 was identified as the item's ATTRIBUTE REQUIREMENT
(and 617 as read by nothing at all) -- studies/itemmods/FINDINGS.md sec 4.

LOCATED STRUCTURALLY. The dispatch is found by its own instruction bytes, not
by an address: build-specific VAs are not part of any file format and must not
be carried between builds. `--all-builds` is the out-of-sample check.

Read-only. Standard library only; no disassembler dependency -- the patterns
here are fixed byte sequences, which is what keeps this tool working on a bare
machine (CLAUDE.md carve-out (1) scopes capstone to two named files, and this
is not one of them).
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinned  # noqa: E402

# The dispatch preamble: shr eax,0x14 ; and eax,0x3ff ; cmp eax,0x201
DISPATCH = bytes.fromhex("c1e81425ff0300003d01020000")
JMP_TABLE = bytes.fromhex("ff2485")          # jmp dword ptr [eax*4 + disp32]
CALL = 0xE8
PUSH_IMM32 = 0x68

SPECIAL_FIRST, SPECIAL_COUNT = 1, 20         # after `dec eax; cmp eax,0x13`
GENERIC_FIRST = 0x202                        # after `sub eax,0x202; cmp eax,0x88`

# TextApi entry points, themselves identified by their asserts (TextApi:71 etc).
TEXT_ONE_ID = 0x007C93F0     # (stringId) -> a formatted string
TEXT_FORMAT = 0x007C9600     # (buf, templateId, type, value, ...) -> a line
ASSERT = 0x00487BC0


class Image:
    def __init__(self, path):
        self.path = str(path)
        self.data = Path(path).read_bytes()
        d = self.data
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        nsec = struct.unpack_from("<H", d, pe + 6)[0]
        optsz = struct.unpack_from("<H", d, pe + 20)[0]
        self.base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
        self.secs = []
        for i in range(nsec):
            off = pe + 24 + optsz + i * 40
            name = d[off:off + 8].rstrip(b"\0").decode(errors="replace")
            vsz, va, rsz, raw = struct.unpack_from("<IIII", d, off + 8)
            self.secs.append((name, self.base + va, vsz, raw, rsz))

    def off(self, va):
        for _n, sva, vsz, raw, rsz in self.secs:
            if sva <= va < sva + max(vsz, rsz):
                return raw + (va - sva)
        return None

    def va_of(self, off):
        for _n, sva, vsz, raw, rsz in self.secs:
            if raw <= off < raw + rsz:
                return sva + (off - raw)
        return None

    def u32(self, va):
        o = self.off(va)
        return struct.unpack_from("<I", self.data, o)[0] if o is not None else None

    def text(self):
        for n, sva, vsz, raw, rsz in self.secs:
            if n == ".text":
                return raw, rsz, sva
        raise NotFound("no .text section")


class NotFound(Exception):
    pass


def build_of(data: bytes):
    """The build of this exact image from its own bytes, or None.

    Same rule as attribtable/skilltable: a stamp nothing checks is an
    unfalsifiable self-declaration.
    """
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    for b in pinned.BUILDS:
        if digest == b.pristine:
            return b.number
    return None


def locate(img: Image):
    """Find both dispatch tables from the parser's own instruction bytes."""
    raw, size, _sva = img.text()
    hit = img.data.find(DISPATCH, raw, raw + size)
    if hit < 0:
        raise NotFound(
            "the modifier dispatch preamble (shr eax,0x14; and eax,0x3ff; "
            "cmp eax,0x201) is not in this image. It is the anchor for "
            "everything here, so refusing rather than reporting an empty "
            "vocabulary that would read as 'this build has no modifiers'.")
    if img.data.find(DISPATCH, hit + 1, raw + size) >= 0:
        raise NotFound("the dispatch preamble matches more than once; the "
                       "anchor is meant to be unique and is not, so the table "
                       "it picks would be a coin toss.")
    tables = []
    scan = hit
    while len(tables) < 2 and scan < hit + 0x800:
        j = img.data.find(JMP_TABLE, scan, hit + 0x800)
        if j < 0:
            break
        tables.append(struct.unpack_from("<I", img.data, j + 3)[0])
        scan = j + 1
    if len(tables) != 2:
        raise NotFound(f"expected two `jmp [eax*4+disp32]` dispatches after "
                       f"the preamble, found {len(tables)}")
    return {"anchor_va": img.va_of(hit),
            "special_table": tables[0], "generic_table": tables[1]}


def _rel32(img, off):
    return img.va_of(off) + 5 + struct.unpack_from("<i", img.data, off + 1)[0]


def handler_strings(img: Image, handler_va: int, limit=0x180):
    """The text ids a handler passes to TextApi.

    `text_ids` is the ORDERED, complete list and is what the content rows
    carry. `labels` and `templates` split it by which TextApi entry point
    consumed each id -- labels become `%str1%`/`%str2%`, a template is the
    line's shape -- and that split is BEST EFFORT by design: several handlers
    branch or loop before formatting, so a linear walk cannot always pair a
    push with its call. When the split is empty and `text_ids` is not, the
    ordered list is still complete; do not read an empty `templates` as "this
    identifier renders nothing" (`--summary` counts on `text_ids` for exactly
    that reason).

    Assert line numbers are dropped: an assert pushes its line and then calls
    the assert routine, so the push is filtered by what follows it.
    """
    o = img.off(handler_va)
    if o is None:
        return {"text_ids": [], "labels": [], "templates": []}
    ordered, labels, templates, pending = [], [], [], []
    for step in range(limit):
        p = o + step
        b = img.data[p]
        if b == PUSH_IMM32:
            v = struct.unpack_from("<I", img.data, p + 1)[0]
            pending.append((v, len(ordered)))
            ordered.append(v)
        elif b == CALL:
            target = _rel32(img, p)
            if target == ASSERT and pending:
                v, idx = pending.pop()          # that push was the assert line
                if ordered and ordered[idx] == v:
                    ordered[idx] = None
            elif target == TEXT_ONE_ID and pending:
                labels.append(pending.pop()[0])
            elif target == TEXT_FORMAT and pending:
                templates.append(pending.pop(0)[0])
                pending.clear()
        elif b == 0xE9:                          # jmp rel32 back to the loop tail
            break
    keep = lambda v: v is not None and 0x100 <= v <= 0xFFFF      # noqa: E731
    return {"text_ids": [v for v in ordered if keep(v)],
            "labels": [v for v in labels if keep(v)],
            "templates": [v for v in templates if keep(v)]}


def decode(word: int):
    """One modifier word -> its fields, by the parser's own arithmetic."""
    return {
        "word": word,
        "identifier": (word >> 20) & 0x3FF,
        "arg": (word >> 8) & 0x3FF,
        "arg2": word & 0xFF,
        "skipped_high": ((word >> 30) & 3) == 3,
        "skipped_bit18": bool((word >> 18) & 1),
    }


def vocabulary(img: Image):
    """{identifier: {handler, labels, templates}} over both dispatch tables."""
    at = locate(img)
    out = {}
    for table, first, count in (
            (at["special_table"], SPECIAL_FIRST, SPECIAL_COUNT),
            (at["generic_table"], GENERIC_FIRST, 0x89)):
        for i in range(count):
            handler = img.u32(table + i * 4)
            if handler is None:
                continue
            out[first + i] = {"identifier": first + i, "handler": handler}
    # One walk per DISTINCT handler: 157 slots share 133 bodies, and several
    # identifiers deliberately land on the same one.
    seen = {}
    for ident, rec in out.items():
        h = rec["handler"]
        if h not in seen:
            seen[h] = handler_strings(img, h)
        rec.update(seen[h])
    return at, out


def emit_content(vocab, at, build, exe, out_path) -> int:
    """One row per identifier: the ids it renders through, never the English."""
    lines = [
        "# GENERATED -- do not hand-edit. "
        "toolkit/clientscan/itemmods.py --emit-content",
        f"# exe: {exe}",
        f"# build: {build} (derived from the image's own sha256 via "
        f"clientscan/pinned.py, never typed in)",
        f"# rows: {len(vocab)} -- the client's whole item-modifier identifier "
        f"space.",
        "# A modifier word is {identifier: bits 29-20, arg: bits 17-8, arg2:",
        "# bits 7-0}. `templates` and `labels` are TEXT STRING IDS: the line the",
        "# handler formats and the nouns it drops into it. Ids, not words --",
        "# the English resolves at run time from the owner's own archive.",
        "# An identifier with no template renders nothing and is listed so that",
        "# 'this one is inert' is a recorded fact rather than a gap.",
        "",
    ]
    for ident in sorted(vocab):
        rec = vocab[ident]
        lines.append(f"[item_modifier.{ident}]")
        lines.append(f"text_ids = {rec['text_ids']}")
        lines.append(f"templates = {rec['templates']}")
        lines.append(f"labels = {rec['labels']}")
        lines.append(f"[item_modifier.{ident}.provenance]")
        lines.append('source = "client-table"')
        lines.append('extractor = "toolkit/clientscan/itemmods.py"')
        lines.append(f"build = {build}")
        lines.append("")
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    return len(vocab)


# -------------------------------------------------------------- readers ----
# `ItemName.cpp` is the NAME AND TOOLTIP builder, not every consumer of a
# modifier. Twenty-one identifiers dispatch to the walker's own loop tail --
# it renders nothing for them, deliberately -- and two of those are the
# busiest in the wild. So "who else reads identifier N" is a real question,
# and this section answers it exhaustively rather than by inspection.
#
# There are exactly two ways the image can name an identifier:
#
#   LITERAL   `and r32,0x3ff00000` then `cmp r32,<id << 20>` -- a reader that
#             knows which one it wants. This is how `ItCliApi.cpp` reads 633
#             and how `ItemName.cpp` special-cases 8, 542, 556, 572, ...
#   PARAMETRIC  `shr eax,0x14 ; and eax,0x3ff ; cmp eax,edx` inside a helper
#             that walks `[this+0x10]` to the 0xC0000000 terminator and takes
#             the identifier as an ARGUMENT. The identifier then appears at
#             the CALL SITE as a pushed immediate.
#
# Both are found by their own instruction bytes over the whole of .text, so
# neither can desync, and an identifier absent from both is absent under a
# stated bound rather than "nowhere" -- which is the distinction
# studies/enemy lost when it reported a field as having no writer.

# `shr eax,0x14 ; and eax,0x3ff ; cmp eax,edx`
ACCESSOR = bytes.fromhex("c1e81425ff0300003bc2")
# the identifier field masked in place: the tail of `and r32,0x3ff00000`
IDMASK = bytes.fromhex("0000f03f")
PROLOGUE = bytes.fromhex("558bec")            # push ebp ; mov ebp,esp
TERMINATOR = 0xC0000000                       # the modifier array's end word
# How far after the mask the naming `cmp` may be scheduled. Named because it
# is exactly what an empty answer from `literal_readers` is bounded by.
CMP_WINDOW = 16


def _all(data, pat, lo, hi):
    out, i = [], data.find(pat, lo, hi)
    while i >= 0:
        out.append(i)
        i = data.find(pat, i + 1, hi)
    return out


def _cmp_imm32(data, off):
    """The imm32 of a `cmp r32, imm32` at off, or None."""
    if data[off] == 0x3D:                                  # cmp eax, imm32
        return struct.unpack_from("<I", data, off + 1)[0]
    if data[off] == 0x81 and 0xF8 <= data[off + 1] <= 0xFF:  # cmp r32, imm32
        return struct.unpack_from("<I", data, off + 2)[0]
    return None


def literal_readers(img: Image):
    """{identifier: [VA of the compare]} -- every site that names ONE id."""
    raw, size, _sva = img.text()
    d = img.data
    starts = [(o, 5) for o in _all(d, bytes([0x25]) + IDMASK, raw, raw + size)]
    for m in range(0xE0, 0xE8):
        starts += [(o, 6) for o in
                   _all(d, bytes([0x81, m]) + IDMASK, raw, raw + size)]
    out, seen = {}, set()
    for off, ln in sorted(starts):
        for step in range(CMP_WINDOW):
            p = off + ln + step
            val = _cmp_imm32(d, p)
            if val is None or val & 0xFFFFF or (val >> 20) > 0x3FF:
                continue
            if p in seen:
                continue
            seen.add(p)
            out.setdefault(val >> 20, []).append(img.va_of(p))
    return out


def _call_index(img: Image):
    """{target VA: [call site file offsets]} for every `call rel32` in .text."""
    raw, size, _sva = img.text()
    d = img.data
    idx, end = {}, raw + size - 5
    i = d.find(bytes([0xE8]), raw, end)
    while i >= 0:
        t = img.va_of(i) + 5 + struct.unpack_from("<i", d, i + 1)[0]
        idx.setdefault(t, []).append(i)
        i = d.find(bytes([0xE8]), i + 1, end)
    return idx


def _asked_identifier(img: Image, call_off):
    """The identifier (and default) a call site pushes, or None.

    Shape: `push <default> ; push <identifier> ; mov ecx,<reg> ; call`. When
    the immediate is not there the site is reported with its raw bytes rather
    than dropped, because a caller this cannot read is a hole in the census
    and must be visible as one.
    """
    d = img.data
    p = call_off
    if d[p - 2] == 0x8B and 0xC8 <= d[p - 1] <= 0xCF:      # mov ecx, r32
        p -= 2
    if d[p - 5] != 0x68:
        return None
    ident = struct.unpack_from("<I", d, p - 4)[0]
    default = None
    if d[p - 7] == 0x6A:                                   # push imm8
        default = d[p - 6]
    elif d[p - 10] == 0x68:                                # push imm32
        default = struct.unpack_from("<I", d, p - 9)[0]
    return ident, default


def parametric_readers(img: Image):
    """The by-argument accessors and, per accessor, what each caller asks for.

    [{'entry', 'sites', 'callers': [{'va', 'identifier', 'default'}],
      'unreadable': [VA]}]
    """
    raw, size, _sva = img.text()
    d = img.data
    entries = {}
    for o in _all(d, ACCESSOR, raw, raw + size):
        j = d.rfind(PROLOGUE, o - 0x40, o)
        if j < 0:
            continue
        entries.setdefault(img.va_of(j), []).append(img.va_of(o))
    idx = _call_index(img)
    out = []
    for entry, sites in sorted(entries.items()):
        callers, unreadable = [], []
        for off in idx.get(entry, []):
            got = _asked_identifier(img, off)
            if got is None:
                unreadable.append(img.va_of(off))
            else:
                callers.append({"va": img.va_of(off),
                                "identifier": got[0], "default": got[1]})
        out.append({"entry": entry, "sites": sites,
                    "callers": callers, "unreadable": unreadable})
    return out


def loop_tail(img: Image, at, vocab):
    """The dispatch slots that ARE the walker's loop tail: 'render nothing'.

    Identified structurally: a handler that reaches a backward branch into the
    few dozen bytes ahead of the dispatch anchor WITHOUT calling anything or
    pushing an immediate on the way. Both halves matter. Reaching the branch
    alone is not enough -- the last renderer in the chain FALLS THROUGH into
    the tail, so on build 38797 identifier 526 (which pushes string 2387 and
    calls TextApi eight bytes into its body) was reported inert by the first
    version of this, and would have been published as "the client renders
    nothing for it" when the client plainly does.

    The scan is byte-level and assumes no instruction boundaries, so a 0xE8 or
    0x68 appearing inside an operand can disqualify a real tail. That error
    direction is deliberate: it shows up as "no loop tail found", which is
    visible, rather than as an identifier silently added to the inert list.

    Returns the list rather than one address so that "more than one qualified"
    stays visible instead of being silently resolved.
    """
    d = img.data
    anchor = at["anchor_va"]
    tails = []
    for h in {r["handler"] for r in vocab.values()}:
        o = img.off(h)
        if o is None:
            continue
        for step in range(0x60):
            p = o + step
            if d[p] in (0xE8, 0x68):          # a call or a pushed immediate:
                break                          # this body renders something
            if d[p] == 0x0F and d[p + 1] == 0x85:
                t = img.va_of(p) + 6 + struct.unpack_from("<i", d, p + 2)[0]
            elif d[p] == 0x75:
                t = img.va_of(p) + 2 + struct.unpack_from("<b", d, p + 1)[0]
            else:
                continue
            if anchor - 0x80 <= t < anchor:
                tails.append(h)
                break
    return sorted(set(tails))


def readers(img: Image):
    """Who reads which item-modifier identifier, outside the tooltip walker."""
    at, vocab = vocabulary(img)
    tails = loop_tail(img, at, vocab)
    inert = sorted(i for i, r in vocab.items() if r["handler"] in tails)
    lit = literal_readers(img)
    par = parametric_readers(img)
    asked = {}
    for acc in par:
        for c in acc["callers"]:
            asked.setdefault(c["identifier"], []).append(
                {"via": acc["entry"], "at": c["va"], "default": c["default"]})
    return {"anchor": at, "vocab": vocab, "loop_tails": tails, "inert": inert,
            "literal": lit, "accessors": par, "asked": asked}


def print_readers(img: Image, only=None):
    r = readers(img)
    tails = ", ".join(f"{t:#010x}" for t in r["loop_tails"])
    print(f"dispatch anchor {r['anchor']['anchor_va']:#010x}; "
          f"walker loop tail {tails}")
    print(f"{len(r['inert'])} of {len(r['vocab'])} identifiers dispatch to the "
          f"loop tail -- ItemName renders NOTHING for them:")
    print(f"  {r['inert']}")
    print("\nby-argument accessors (walk [this+0x10] to the "
          f"{TERMINATOR:#010x} terminator, identifier from the caller):")
    for acc in r["accessors"]:
        print(f"  {acc['entry']:#010x}  compare at "
              f"{', '.join(hex(s) for s in acc['sites'])}  "
              f"{len(acc['callers'])} caller(s)"
              + (f", {len(acc['unreadable'])} UNREADABLE "
                 f"{[hex(u) for u in acc['unreadable']]}"
                 if acc["unreadable"] else ""))
        for c in sorted(acc["callers"], key=lambda x: x["identifier"]):
            print(f"      id {c['identifier']:>4}  asked at {c['va']:#010x}  "
                  f"default {c['default']}")
    want = sorted(set(r["literal"]) | set(r["asked"])) if only is None else only
    print("\nwho reads which identifier:")
    for ident in want:
        rec = r["vocab"].get(ident)
        rendered = ("INERT (loop tail)" if rec and rec["handler"] in r["loop_tails"]
                    else f"renders {rec['text_ids']}" if rec else "NOT DISPATCHED")
        lit = r["literal"].get(ident, [])
        ask = r["asked"].get(ident, [])
        print(f"  id {ident:>4}  ItemName: {rendered}")
        for va in lit:
            print(f"           named by a literal compare at {va:#010x}")
        for a in ask:
            print(f"           asked of accessor {a['via']:#010x} at "
                  f"{a['at']:#010x} (default {a['default']})")
        if not lit and not ask:
            print("           NO reader: named by no literal compare in "
                  ".text and asked of no accessor")
    print("\nNOT SEARCHED, and an empty answer above means only this much: an "
          "identifier reached through a register or a table rather than an "
          "immediate; a compare scheduled more than "
          f"{CMP_WINDOW} bytes after its mask; an accessor whose body differs "
          "from the two byte patterns above; and anything the SERVER does "
          "with the same word.")
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default=None)
    ap.add_argument("--summary", action="store_true",
                    help="resolve a few templates through textrec and print "
                         "the vocabulary for reading")
    ap.add_argument("--decode", metavar="WORD",
                    help="decode one modifier word, e.g. 0xA3C81900")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit-content", metavar="PATH", default=None)
    ap.add_argument("--readers", action="store_true",
                    help="who reads which identifier OUTSIDE the tooltip "
                         "walker: literal compares, by-argument accessors, "
                         "and the identifiers ItemName renders nothing for")
    ap.add_argument("--reads", metavar="ID", default=None,
                    help="answer --readers for one identifier only")
    ap.add_argument("--all-builds", action="store_true")
    a = ap.parse_args(argv)

    targets = []
    if a.all_builds:
        for b in pinned.BUILDS:
            try:
                targets.append(pinned.find(build=b.number))
            except SystemExit as exc:
                print(f"build {b.number}: {exc}", file=sys.stderr)
    else:
        targets.append((a.exe, "given on the command line") if a.exe
                       else pinned.find())

    rc = 0
    for exe, why in targets:
        print(f"client: {exe}\n        ({why})", file=sys.stderr)
        img = Image(exe)
        try:
            at, vocab = vocabulary(img)
        except NotFound as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            rc = 2
            continue

        if a.readers or a.reads is not None:
            only = [int(a.reads, 0)] if a.reads is not None else None
            print_readers(img, only=only)
            continue

        if a.decode:
            d = decode(int(a.decode, 0))
            rec = vocab.get(d["identifier"])
            d["text_ids"] = rec["text_ids"] if rec else []
            d["templates"] = rec["templates"] if rec else []
            d["labels"] = rec["labels"] if rec else []
            d["dispatched"] = rec is not None
            print(json.dumps(d, indent=1))
            continue

        if a.emit_content:
            build = build_of(img.data)
            if build is None:
                print("REFUSED: this exe matches no PRISTINE build in "
                      "clientscan/pinned.py, so no honest `build` stamp "
                      "exists.", file=sys.stderr)
                return 2
            n = emit_content(vocab, at, build, exe, a.emit_content)
            print(f"wrote {a.emit_content}: {n} identifier rows, build {build}",
                  file=sys.stderr)
            continue

        if a.json:
            print(json.dumps({"anchors": at,
                              "vocabulary": {str(k): v
                                             for k, v in vocab.items()}},
                             indent=1))
            continue

        live = [i for i, r in vocab.items() if r["text_ids"]]
        print(f"anchor {at['anchor_va']:#010x}  special table "
              f"{at['special_table']:#010x}  generic table "
              f"{at['generic_table']:#010x}")
        print(f"{len(vocab)} identifier slots, "
              f"{len({r['handler'] for r in vocab.values()})} distinct "
              f"handlers, {len(live)} that render a line")
        if a.summary:
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                import textrec
                resolver = textrec.Resolver(exe) if hasattr(textrec, "Resolver") else None
            except Exception:
                resolver = None
            for ident in sorted(live)[:200]:
                r = vocab[ident]
                print(f"  id {ident:>4}  text {r['text_ids']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
