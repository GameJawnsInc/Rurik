r"""The client's static composite tables, read out of Gw.exe and verified shut.

    python toolkit/clientscan/composite.py                 # summary
    python toolkit/clientscan/composite.py --json
    python toolkit/clientscan/composite.py --emit-content vault/content/composite.toml

The playercomposite arc (studies/playercomposite/FINDINGS.md) established what
these tables are; this module is the P2 rung -- the extraction, promoted from
one-off reads to an anchored, refusing extractor. Stdlib only, and that is a
bare-machine REQUIREMENT, not a preference: every claim in the study was made
with bytes.find/struct.unpack_from, and this module must keep working where no
disassembler exists (CLAUDE.md carve-out (1) is scoped to two named files and
this is not one of them).

WHAT IS EXTRACTED, each with the anchor that verifies it:

  * `s_components` (20 dwords) and `s_format` (6 dwords) -- located from the
    `ConstComposite.cpp` __FILE__ string they tile up against: s_format ends
    24 bytes before it, s_components 104. FINDINGS 1.6's closure, run in
    reverse.
  * The ConstComposite CSR/rect pair -- TABLE_A and TABLE_B (132 pointers
    each), located from the ACCESSOR'S OWN INSTRUCTIONS: the `push 0x1CC;
    mov edx, <file-string>` of ConstComposite:460 finds the function, whose
    `mov eax,[edx*4+B]` / `add eax,[edx*4+A]` operands carry both bases
    (0x005AE29D/0x005AE2B4 on 38797). Verified A + 528 == B, every B cell a
    9-dword non-decreasing prefix array, every A record a well-formed rect
    against its blitId's own dims (FINDINGS 1.3/1.4).
  * `s_dims` (6 pairs) -- the first record array minus 48 (FINDINGS 1.6).
  * `s_fileFlags` (11 dwords) -- 44 bytes before the `CpsData.cpp` __FILE__
    string (FINDINGS 1.15). Geometry slots are the clear bits: {0, 5, 10}.
  * The base-piece types (4 dwords) -- 16 bytes before the string
    `race < CHAR_APPEARANCE_RACES` (FINDINGS claim 23).
  * `s_appearanceSlot` (8 rows of {self, shift, width}) -- located from the
    `slot < arrsize(s_appearanceSlot)` assert's own code, then verified by
    the table's SELF-CLOSURE: every row's first dword equals its own index
    and the eight (shift, width) fields tile all 32 bits with no gap and no
    overlap (FINDINGS 1.11). The closure picks the base among candidates;
    zero or two candidates is a refusal, never a guess.
  * The ITEM-TYPE ATTACH CLASSIFIER (FINDINGS 9.2) -- CpsBase's only reader
    of the wire item type: `movzx type; dec; cmp <max>; ja` into a byte
    class table and a case switch whose non-fail cases each write one
    attach code. Located from the `GetSlotItemData(slot).fileId` assert
    the classifier itself raises, then parsed from its own instructions
    (the cmp bound, the class-table operand, the jump-table operand) --
    never from a hardcoded address. Exactly one image-wide parse or a
    refusal; exactly one fail case; distinct attach codes.

EVERY MISS REFUSES, NAMING THE BUILD. The addresses above are 38797's; the
DISCOVERY is by string and instruction anchor, so on another build the
extractor either closes on that build's own addresses or raises CompositeError
saying which anchor failed on which build -- never silently returns 38797's
numbers (FINDINGS 5's sabotage 7; `genericvalue.py` on 38833 is the failure
this rule is about).

Emission: `--emit-content` writes `vault/content/composite.toml` with
`source = "client-table"`, the extractor named and the build recorded PER ROW
(`content.py` enforces both; `attribtable.py --emit-content` is the
precedent). NOT tracked content -- these are the client's own layout, not
authorable world facts.
"""
import argparse
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import pinned  # noqa: E402

IMAGE_BASE = 0x400000

CONSTCOMPOSITE_FILE = b"P:\\Code\\Gw\\Const\\Tool\\ConstComposite.cpp\x00"
CPSDATA_FILE = b"P:\\Code\\Gw\\Composite\\Data\\CpsData.cpp\x00"
RACE_BOUND_EXPR = b"race < CHAR_APPEARANCE_RACES\x00"
APPEARANCE_EXPR = b"slot < arrsize(s_appearanceSlot)\x00"
SLOT_ITEM_EXPR = b"GetSlotItemData(slot).fileId\x00"

N_CELLS = 132        # blitId + 6*sex + 12*profession: 6 * 2 * 11
N_COMPONENTS = 8
N_BLITS = 6
N_PROF = 11
N_FILE_SLOTS = 11


class CompositeError(Exception):
    """A refusal: an anchor or closure failed. Never a warning."""


class _Image:
    """A minimal PE reader. Sections only; no imports, no relocs."""

    def __init__(self, path):
        self.path = path
        self.data = open(path, "rb").read()
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        nsec = struct.unpack_from("<H", self.data, pe + 6)[0]
        opt = struct.unpack_from("<H", self.data, pe + 20)[0]
        s0 = pe + 24 + opt
        self.sections = []
        for i in range(nsec):
            off = s0 + i * 40
            vsize, va, rsize, raw = struct.unpack_from("<IIII", self.data,
                                                       off + 8)
            self.sections.append((va, max(vsize, rsize), rsize, raw))

    def read(self, va, n):
        """Bytes at a VA -- with the virtual zero-fill TAIL MODELLED.

        A section's virtual size can exceed its raw size; the loader
        zero-fills the difference. A reader that slices the file past the
        raw end returns the NEXT section's bytes wearing this section's
        address -- which is exactly how the 88 degenerate ConstComposite
        cells (whose shared record lives in .data's zero tail, FINDINGS
        1.7) first read as garbage rects.
        """
        rva = va - IMAGE_BASE
        for sva, vsize, rsize, raw in self.sections:
            if sva <= rva < sva + vsize:
                off = rva - sva
                filed = self.data[raw + off:raw + min(rsize, off + n)]
                return filed + b"\x00" * (n - len(filed))
        raise CompositeError(f"VA 0x{va:08X} maps to no section")

    def va_of(self, blob, what):
        """The unique VA of a byte string, or a refusal naming it."""
        first = self.data.find(blob)
        if first < 0:
            raise CompositeError(f"anchor NOT FOUND in the image: {what}")
        if self.data.find(blob, first + 1) >= 0:
            raise CompositeError(f"anchor is AMBIGUOUS in the image: {what}")
        for sva, _vsize, rsize, raw in self.sections:
            if raw <= first < raw + rsize:
                return IMAGE_BASE + sva + (first - raw)
        raise CompositeError(f"anchor outside every section: {what}")

    def dwords(self, va, n):
        return list(struct.unpack_from("<%dI" % n, self.read(va, 4 * n), 0))


def build_of(data):
    """The build number from the image's own hash, or None. Never a stamp."""
    digest = hashlib.sha256(data).hexdigest()
    for b in pinned.BUILDS:
        if digest == b.pristine:
            return b.number
    return None


def _accessor_tables(img, file_str_va, build):
    """(TABLE_A, TABLE_B) bases from the accessor's own instructions."""
    # ConstComposite:460 is `push 0x1CC; mov edx, <file string>`.
    sig = b"\x68\xCC\x01\x00\x00\xBA" + struct.pack("<I", file_str_va)
    pos = img.data.find(sig)
    if pos < 0 or img.data.find(sig, pos + 1) >= 0:
        raise CompositeError(
            f"the ConstComposite:460 assert site is not uniquely locatable "
            f"on build {build}; the accessor cannot be found")
    window = img.data[pos:pos + 0x120]
    b_off = window.find(b"\x8B\x04\x95")        # mov eax, [edx*4 + B]
    a_off = window.find(b"\x03\x04\x95")        # add eax, [edx*4 + A]
    if b_off < 0 or a_off < 0:
        raise CompositeError(
            f"the accessor's table loads are missing on build {build} -- "
            f"the compiler idiom changed; re-derive before trusting anything")
    table_b = struct.unpack_from("<I", window, b_off + 3)[0]
    table_a = struct.unpack_from("<I", window, a_off + 3)[0]
    if table_a + N_CELLS * 4 != table_b:
        raise CompositeError(
            f"TABLE_A + 528 != TABLE_B (0x{table_a:08X} vs 0x{table_b:08X}) "
            f"on build {build} -- the two-table layout does not close")
    return table_a, table_b


def _appearance_slot(img, build):
    """The 8x{self, shift, width} rows, found by their own closure."""
    expr_va = img.va_of(APPEARANCE_EXPR, "the s_appearanceSlot assert expr")
    sig = b"\xB9" + struct.pack("<I", expr_va)     # mov ecx, <expr>
    pos = img.data.find(sig)
    if pos < 0:
        raise CompositeError(
            f"no site loads the s_appearanceSlot assert expression on build "
            f"{build}")
    # Scan the surrounding code for disp32 operands; the table's base is the
    # one candidate whose content SELF-CLOSES (self-index column == row
    # index, the eight (shift, width) pairs tile 32 bits exactly). Zero or
    # two closures is a refusal.
    window = img.data[max(0, pos - 0x80):pos + 0x80]
    candidates = set()
    for i in range(len(window) - 4):
        (va,) = struct.unpack_from("<I", window, i)
        if 0x400000 < va < 0x400000 + 0x1000000 and va % 4 == 0:
            candidates.add(va)
    closed = []
    for va in candidates:
        try:
            rows = [img.dwords(va + 12 * i, 3) for i in range(8)]
        except CompositeError:
            continue
        if all(rows[i][0] == i for i in range(8)):
            bits = set()
            for _self, shift, width in rows:
                if shift > 31 or width == 0 or width > 32:
                    break
                span = set(range(shift, shift + width))
                if bits & span:
                    break
                bits |= span
            else:
                if bits == set(range(32)):
                    closed.append(va)
    if len(closed) != 1:
        raise CompositeError(
            f"s_appearanceSlot: {len(closed)} candidate base(s) satisfy the "
            f"self-closure on build {build} (need exactly 1). Refusing.")
    return closed[0], [img.dwords(closed[0] + 12 * i, 3) for i in range(8)]


def _attach_class(img, build):
    """The item-type attach classifier: (class table, out-per-class, VAs).

    CpsBase's per-slot classifier is the composite module's ONLY reader of
    the wire item type (FINDINGS 9.2): it asserts `slot <
    arrsize(m_slotItemData)` and `GetSlotItemData(slot).fileId`, reads the
    cached type byte at m_slotItemData+0x04, and runs

        movzx eax, byte [slot_row + 0x28] ; dec eax
        cmp eax, MAX ; ja <fail>
        movzx eax, byte [eax + CLASS_TABLE]
        jmp [eax*4 + JUMP_TABLE]

    Every operand is parsed from the site itself. The anchor is the
    `GetSlotItemData(slot).fileId` assert-expression load (`mov ecx, imm`),
    because that expression names this function's own precondition; among
    its load sites, exactly ONE must carry the cmp/movzx/jmp tail, or the
    build gets a refusal.
    """
    expr_va = img.va_of(SLOT_ITEM_EXPR, "the GetSlotItemData(slot).fileId "
                        "assert expr")
    sig = b"\xB9" + struct.pack("<I", expr_va)          # mov ecx, <expr>
    parses = []
    pos = img.data.find(sig)
    while pos >= 0:
        w = img.data[pos:pos + 0x80]
        c = w.find(b"\x83\xF8")                          # cmp eax, imm8
        while c >= 0:
            max_m1 = w[c + 2]
            # ja rel8, then movzx eax, byte [eax+disp32], jmp [eax*4+disp32]
            if w[c + 3:c + 4] == b"\x77" and w[c + 5:c + 8] == b"\x0F\xB6\x80" \
                    and w[c + 12:c + 15] == b"\xFF\x24\x85":
                table_va = struct.unpack_from("<I", w, c + 8)[0]
                jt_va = struct.unpack_from("<I", w, c + 15)[0]
                parses.append((max_m1, table_va, jt_va))
                break
            c = w.find(b"\x83\xF8", c + 1)
        pos = img.data.find(sig, pos + 1)
    if len(parses) != 1:
        raise CompositeError(
            f"the attach classifier parsed at {len(parses)} site(s) on build "
            f"{build} (need exactly 1) -- the compiler idiom moved; re-derive "
            f"before trusting any attach class")
    max_m1, table_va, jt_va = parses[0]
    n_types = max_m1 + 1                                 # types 1..n_types
    class_of = list(img.read(table_va, n_types))
    n_class = max(class_of) + 1
    if sorted(set(class_of)) != list(range(n_class)):
        raise CompositeError(
            f"attach class table on build {build} skips a class: "
            f"{sorted(set(class_of))} -- the table read is misaligned")
    out_of = []
    fails = 0
    for i in range(n_class):
        case_va = struct.unpack_from("<I", img.read(jt_va + 4 * i, 4), 0)[0]
        body = img.read(case_va, 10)
        if body[:2] == b"\x33\xC0":                      # xor eax, eax
            out_of.append(None)
            fails += 1
        elif body[:5] == b"\x8B\x45\x0C\xC7\x00":        # mov eax,[ebp+0xc];
            out_of.append(struct.unpack_from("<i", body, 5)[0])   # mov [eax],i
        else:
            raise CompositeError(
                f"attach case {i} at 0x{case_va:08X} decodes to neither a "
                f"value write nor the fail return on build {build}")
    if fails != 1:
        raise CompositeError(
            f"{fails} fail classes in the attach switch on build {build} "
            f"(the classifier has exactly one 'no attach' answer)")
    real = [o for o in out_of if o is not None]
    if len(set(real)) != len(real):
        raise CompositeError(
            f"attach codes repeat across classes on build {build}: {out_of}")
    return class_of, out_of, {"attach_class": table_va, "attach_jump": jt_va}


def extract(exe=None):
    """Read every table, verify every closure, return one dict. Or refuse."""
    if exe is None:
        exe, why = pinned.find()
        print(f"client: {exe}\n        ({why})", flush=True)
    img = _Image(exe)
    build = build_of(img.data)
    if build is None:
        raise CompositeError(
            f"{exe} matches no PRISTINE hash in pinned.BUILDS -- an unknown "
            f"image gets a refusal, not 38797's numbers")

    # -- s_components / s_format, off the __FILE__ string ------------------
    file_va = img.va_of(CONSTCOMPOSITE_FILE, "ConstComposite.cpp __FILE__")
    s_format_va = file_va - 24
    s_components_va = file_va - 104
    s_format = img.dwords(s_format_va, 6)
    s_components = img.dwords(s_components_va, 20)
    if not all(c <= 8 for c in s_components):
        raise CompositeError(
            f"s_components holds a value above 8 on build {build}: "
            f"{s_components} -- the anchor arithmetic is wrong for this build")

    # -- the CSR/rect pair, off the accessor's own operands ----------------
    table_a_va, table_b_va = _accessor_tables(img, file_va, build)
    ptrs_a = img.dwords(table_a_va, N_CELLS)
    ptrs_b = img.dwords(table_b_va, N_CELLS)

    cells = {}
    live_record_bases = []
    for idx in range(N_CELLS):
        prefix = img.dwords(ptrs_b[idx], 9)
        if any(prefix[i] > prefix[i + 1] for i in range(8)):
            raise CompositeError(
                f"cell {idx}: prefix array at 0x{ptrs_b[idx]:08X} is not "
                f"non-decreasing on build {build}: {prefix}")
        nrec = prefix[8]
        rects = []
        for r in range(nrec):
            rects.append(img.dwords(ptrs_a[idx] + 16 * r, 4))
        prof, rem = divmod(idx, 12)
        sex, blit = divmod(rem, 6)
        cells[(prof, sex, blit)] = {"prefix": prefix, "rects": rects}
        if nrec:
            live_record_bases.append(ptrs_a[idx])

    # -- s_dims: 48 bytes before the first record array --------------------
    s_dims_va = min(live_record_bases) - 48
    s_dims = [img.dwords(s_dims_va + 8 * i, 2) for i in range(6)]

    # Every LIVE rect must be a well-formed LTRB inside its blit's own dims
    # -- the check that killed XYWH and LRTB (FINDINGS 1.4). The 88
    # degenerate cells of blitIds 2-5 share one ALL-ZERO record (FINDINGS
    # 1.7); an empty rect is exempt from the ordering, counted apart, and
    # anything else that fails is a refusal.
    checked = bad = degenerate = 0
    for (prof, sex, blit), cell in cells.items():
        w, h = s_dims[blit]
        for left, top, right, bottom in cell["rects"]:
            if left == top == right == bottom == 0:
                degenerate += 1
                continue
            checked += 1
            if not (left < right <= w and top < bottom <= h):
                bad += 1
    if bad:
        raise CompositeError(
            f"{bad} of {checked} live rects violate LTRB-within-dims on "
            f"build {build} -- either the stride, the table roles or the "
            f"dims anchor is wrong (the deliberate A/B swap dies here)")

    # -- s_fileFlags, off the CpsData __FILE__ string ----------------------
    cps_va = img.va_of(CPSDATA_FILE, "CpsData.cpp __FILE__")
    s_file_flags = img.dwords(cps_va - 44, N_FILE_SLOTS)
    if any(f not in (0, 1) for f in s_file_flags):
        raise CompositeError(
            f"s_fileFlags is not a 0/1 array on build {build}: "
            f"{s_file_flags}")
    geometry_slots = [i for i, f in enumerate(s_file_flags) if f == 0]

    # -- the base-piece types, off the race-bound expression ---------------
    race_va = img.va_of(RACE_BOUND_EXPR, "race < CHAR_APPEARANCE_RACES")
    base_types = img.dwords(race_va - 16, 4)
    if not all(0 < t < 20 for t in base_types):
        raise CompositeError(
            f"base-piece types out of range on build {build}: {base_types}")

    # -- s_appearanceSlot, by its own closure ------------------------------
    app_va, app_rows = _appearance_slot(img, build)

    # -- the item-type attach classifier, off its own assert ---------------
    attach_class, attach_out, attach_vas = _attach_class(img, build)

    return {
        "exe": exe, "build": build,
        "vas": {"s_components": s_components_va, "s_format": s_format_va,
                "s_dims": s_dims_va, "table_a": table_a_va,
                "table_b": table_b_va, "s_file_flags": cps_va - 44,
                "base_types": race_va - 16, "s_appearance_slot": app_va,
                **attach_vas},
        "s_components": s_components, "s_format": s_format,
        "s_dims": s_dims, "s_file_flags": s_file_flags,
        "geometry_slots": geometry_slots, "base_types": base_types,
        "appearance_slot": app_rows,
        "attach_class": attach_class, "attach_out": attach_out,
        "cells": cells, "rects_checked": checked, "rects_degenerate": degenerate,
    }


def emit_content(tables, out_path):
    """vault/content/composite.toml: the client's own layout, per-row sourced."""
    prov = ['source = "client-table"',
            'extractor = "toolkit/clientscan/composite.py"',
            f"build = {tables['build']}"]
    lines = [
        "# GENERATED -- do not hand-edit. "
        "toolkit/clientscan/composite.py --emit-content",
        f"# exe: {tables['exe']}",
        f"# build: {tables['build']} (derived from the image's own sha256; "
        f"a stamp nothing checks is a wish)",
        "# The composite pipeline's static tables. What each IS:",
        "# studies/playercomposite/FINDINGS.md.",
        "",
        "[composite.tables]",
        f"components = {tables['s_components']}",
        f"format = {tables['s_format']}",
        f"dims = {tables['s_dims']}",
        f"file_flags = {tables['s_file_flags']}",
        f"geometry_slots = {tables['geometry_slots']}",
        f"base_types = {tables['base_types']}",
        "[composite.tables.provenance]", *prov, "",
        "[item_attach.classifier]",
        "# class_of_type[i] is wire item type i+1's class; out_of_class is",
        "# the attach code each class writes, -99 standing for the fail case",
        "# (TOML has no null). studies/playercomposite/FINDINGS.md 9.2.",
        f"class_of_type = {tables['attach_class']}",
        f"out_of_class = "
        f"{[-99 if o is None else o for o in tables['attach_out']]}",
        "[item_attach.classifier.provenance]", *prov, "",
    ]
    for self_ix, shift, width in tables["appearance_slot"]:
        lines += [f"[appearance_slot.{self_ix}]",
                  f"shift = {shift}", f"width = {width}",
                  f"[appearance_slot.{self_ix}.provenance]", *prov, ""]
    for (prof, sex, blit), cell in sorted(tables["cells"].items()):
        live = [r for r in cell["rects"] if any(r)]
        if not live:
            continue
        key = f"p{prof}s{sex}b{blit}"
        lines += [f"[composite_atlas.{key}]",
                  f"profession = {prof}", f"sex = {sex}", f"blit = {blit}",
                  f"prefix = {cell['prefix']}",
                  f"rects = {live}",
                  f"[composite_atlas.{key}.provenance]", *prov, ""]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    return sum(1 for ln in lines if ln.startswith("["))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", help="client image; default: the pinned build")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit-content", metavar="PATH",
                    help="write the content rows (vault/content/composite.toml)")
    args = ap.parse_args()

    t = extract(args.exe)
    if args.json:
        out = dict(t)
        out["cells"] = {f"{p},{s},{b}": c
                        for (p, s, b), c in t["cells"].items()}
        print(json.dumps(out, indent=1))
        return 0

    print(f"build {t['build']}  ({t['exe']})")
    for name in ("s_components", "s_format", "s_file_flags", "base_types"):
        print(f"  {name:16} @0x{t['vas'][name if name != 's_file_flags' else 's_file_flags']:08X}  {t[name]}"
              if name != "base_types" else
              f"  {name:16} @0x{t['vas']['base_types']:08X}  {t[name]}")
    print(f"  s_dims           @0x{t['vas']['s_dims']:08X}  {t['s_dims']}")
    print(f"  geometry slots   {t['geometry_slots']}")
    print(f"  appearance rows  @0x{t['vas']['s_appearance_slot']:08X}")
    for self_ix, shift, width in t["appearance_slot"]:
        print(f"      slot {self_ix}: bits {shift}..{shift + width - 1}")
    live = sum(1 for c in t["cells"].values()
               if any(any(r) for r in c["rects"]))
    print(f"  atlas cells      {live} of {N_CELLS} content-bearing, "
          f"{t['rects_checked']} rects (+{t['rects_degenerate']} degenerate "
          f"zero-records), all LTRB-closed")
    by_class = {}
    for ty, cl in enumerate(t["attach_class"], start=1):
        by_class.setdefault(cl, []).append(ty)
    print(f"  attach classes   @0x{t['vas']['attach_class']:08X}  "
          f"(types 1..{len(t['attach_class'])})")
    for cl, out in enumerate(t["attach_out"]):
        print(f"      class {cl} -> {'FAIL' if out is None else out}: "
              f"types {by_class.get(cl, [])}")
    if args.emit_content:
        n = emit_content(t, args.emit_content)
        print(f"wrote {n} rows -> {args.emit_content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
