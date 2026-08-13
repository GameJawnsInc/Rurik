"""Reskin a shipped profession: repoint its identity string ids, out of place.

studies/profession/RESKIN.md is the route decision this implements. The short
version: do NOT add a twelfth profession. Every profession-keyed table in the
image is packed flush against the next live datum (zero slack in `.rdata`), and
seven of them are not data at all but `mov imm32` ladders inside a function with
36 callers -- so widening the profession axis is code generation. Repurposing a
SHIPPED id is five same-length dwords and cannot trip a single bound check,
because the id never leaves 0..10.

WHAT THIS TOUCHES, and it is deliberately the smallest useful set:

  s_charProfession[N]        the profession's name, everywhere the client
                             writes it in world
  s_charProfessionAbbrev[N]  the short form (nameplate, party window)
  picker[N]                  the character-creation list label
  data_names[N]              a fifth table in `.data`, read at 0x004D128E with
                             NO BOUND CHECK AT ALL -- invisible to every assert
                             census this project ran, because they all keyed on
                             `cmp reg, 0x0b`

Every one holds a STRING ID, not text. So this tool moves numbers, never
ArenaNet's words, and the client resolves them from the owner's own archive at
run time -- the same "commit the id, resolve the string at run time" pattern
`mapbuild.py` uses for FINDINGS 14's constants.

LOCATED STRUCTURALLY, NEVER BY ADDRESS. Build-specific addresses are not part
of any file format and must not be carried between builds. Each `.rdata` table
is found by the assert expression the compiler emitted immediately after it --
each occurring exactly ONCE in the image -- and then corroborated by shape: the
first nine entries must be consecutive ascending ids. Both must agree or the
tool refuses. The `.data` table has no string of its own and is found by its
VALUES matching the located name table, which is structure borrowed from a
table we did locate rather than an address we remembered.

READ-ONLY ON THE SOURCE, ALWAYS OUT OF PLACE. It refuses to write into `C:\\gw`
(the owner's install), refuses to write over its own input, and refuses to
write anywhere inside a checkout of this repository -- a patched client is a
derived ArenaNet artifact and the provenance gate keeps those out of the tree.
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "clientscan"))
sys.path.insert(0, os.path.join(HERE, ".."))

import pinned                                                  # noqa: E402
import vaultpath                                               # noqa: E402

PROFESSIONS = 11               # ids 0..10; the compiled array dimension
ROW = 4                        # every table here is u32
SPAN = PROFESSIONS * ROW

# The expression the compiler emitted immediately AFTER each table. Each occurs
# exactly once in the image -- asserted, not assumed (see check below). This is
# ArenaNet's own text used as a LOCATOR, which is the same use `repoint_skill.py`
# makes of `ConstSkill.cpp`: a single citation, not a bulk dump.
ANCHORS = {
    "name":   b"profession < arrsize(s_charProfession)\x00",
    "abbrev": b"profession < arrsize(s_charProfessionAbbrev)\x00",
    "picker": b"id < 8\x00",
}
TABLES = ("name", "abbrev", "picker", "data")

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))


def working_tree_roots():
    """Every checkout of this repo, so --out cannot land in version control.

    A git worktree's root is NOT the main checkout's, and until `mapbuild.py`
    learned this the same class of tool wrote a derived artifact straight into
    another tree. Both are refused.
    """
    roots = set()
    here = os.path.abspath(os.path.join(HERE, "..", ".."))
    roots.add(os.path.normcase(here))
    common = os.path.join(here, ".git")
    if os.path.isfile(common):                      # a worktree: .git is a file
        try:
            with open(common, encoding="utf-8") as f:
                gitdir = f.read().strip().split(":", 1)[1].strip()
            main = os.path.abspath(os.path.join(gitdir, "..", "..", ".."))
            roots.add(os.path.normcase(main))
        except (OSError, IndexError):
            pass
    return roots


def consecutive_head(vals):
    """Do the first nine entries ascend by one? The shape half of the check."""
    return all(vals[i + 1] == vals[i] + 1 for i in range(8))


def locate(data):
    """{table: (file_offset, values)} or SystemExit explaining the refusal."""
    found = {}
    for name, anchor in ANCHORS.items():
        hits = data.count(anchor)
        if hits != 1:
            raise SystemExit(
                f"anchor for {name!r} occurs {hits} times, expected exactly 1. "
                f"Refusing to guess which table it names -- re-derive the "
                f"layout for this build before trusting anything here.")
        at = data.find(anchor)
        base = at - SPAN
        if base < 0:
            raise SystemExit(f"{name}: anchor at {at:#x} has no room before it")
        vals = struct.unpack_from("<11I", data, base)
        if not consecutive_head(vals):
            raise SystemExit(
                f"{name}: the 11 dwords before its anchor are {list(vals)}, "
                f"whose first nine are not consecutive. The anchor and the "
                f"shape disagree, so one of the two assumptions is wrong for "
                f"this build. Refusing.")
        found[name] = (base, list(vals))

    # The `.data` table has no anchor of its own. Find it by its VALUES: its
    # entries 1..8 equal the name table's, while entry 0 differs (it is a
    # separate "any profession" id). That is structure borrowed from a table we
    # located, not an address we remembered.
    want = struct.pack("<8I", *found["name"][1][1:9])
    hits = []
    start = 0
    while True:
        i = data.find(want, start)
        if i < 0:
            break
        base = i - ROW
        if base >= 0 and base != found["name"][0]:
            hits.append(base)
        start = i + 1
    if len(hits) != 1:
        raise SystemExit(
            f"the .data name table matched {len(hits)} candidate(s), expected "
            f"1. It is the unguarded one (read with no bound check), so a "
            f"wrong guess here is the most dangerous edit in the file. Refusing.")
    found["data"] = (hits[0], list(struct.unpack_from("<11I", data, hits[0])))
    return found


# The attribute definition table. 51 rows of 20 bytes, immediately followed by
# its own source path -- the same locator shape the name tables use.
ATTR_ANCHOR = b"P:\\Code\\Gw\\Const\\ConstAttrib.cpp\x00"
ATTR_ROWS = 51
ATTR_ROW = 20
ATTR_OWNER, ATTR_ID, ATTR_NAME, ATTR_DESC, ATTR_PRIMARY = 0x00, 0x04, 0x08, 0x0C, 0x10
SPARE_OWNER = 11               # rows parked on the reserved profession


def locate_attrib(data):
    """(file_offset, [row dicts]) for s_attrib, or SystemExit."""
    hits = data.count(ATTR_ANCHOR)
    if hits != 1:
        raise SystemExit(f"the s_attrib anchor occurs {hits} times, expected 1")
    base = data.find(ATTR_ANCHOR) - ATTR_ROWS * ATTR_ROW
    if base < 0:
        raise SystemExit("s_attrib anchor has no room for the table before it")
    rows = []
    for i in range(ATTR_ROWS):
        o = base + i * ATTR_ROW
        owner, aid, name, desc, primary = struct.unpack_from("<5I", data, o)
        rows.append({"row": i, "off": o, "owner": owner, "id": aid,
                     "name": name, "desc": desc, "primary": primary})
    # Shape check, independent of the anchor: attribute ids are 0..50 in order,
    # and every owner is a legal profession or the reserved 11.
    if [r["id"] for r in rows] != list(range(ATTR_ROWS)):
        raise SystemExit(
            "s_attrib's id column is not 0..50 in order. The anchor and the "
            "shape disagree, so one assumption is wrong for this build.")
    if any(r["owner"] > SPARE_OWNER for r in rows):
        raise SystemExit(
            f"s_attrib has an owner above {SPARE_OWNER}: "
            f"{sorted({r['owner'] for r in rows})}. Refusing.")
    return base, rows


def attrib_edits(data, rows, renames=(), owners=(), primaries=()):
    """Apply attribute edits. Same-length by construction, like the names.

    Three verbs, because they are three different claims about the client:
      rename  -- row+0x08, the name string id: does the panel read THIS row?
      owner   -- row+0x00, the profession: is the panel's attribute list
                 DERIVED from this field rather than from a per-profession
                 table? Nine rows sit on profession 11 with zero skills, so
                 there is somewhere to take one FROM.
      primary -- row+0x10, which of a profession's attributes is primary.
    """
    out = bytearray(data)
    log = []
    by_id = {r["id"]: r for r in rows}
    for aid, sid in renames:
        r = _row(by_id, aid)
        struct.pack_into("<I", out, r["off"] + ATTR_NAME, sid)
        log.append(("attr-name", aid, r["name"], sid))
    for aid, prof in owners:
        if not 0 <= prof <= SPARE_OWNER:
            raise SystemExit(
                f"attribute owner {prof} outside 0..{SPARE_OWNER}. The reskin "
                f"premise is that every id stays legal.")
        r = _row(by_id, aid)
        struct.pack_into("<I", out, r["off"] + ATTR_OWNER, prof)
        log.append(("attr-owner", aid, r["owner"], prof))
    for aid, flag in primaries:
        if flag not in (0, 1):
            raise SystemExit(f"--attr-primary wants ATTR=0 or ATTR=1, got {flag}")
        r = _row(by_id, aid)
        struct.pack_into("<I", out, r["off"] + ATTR_PRIMARY, flag)
        log.append(("attr-primary", aid, r["primary"], flag))
    return bytes(out), log


def _row(by_id, aid):
    if aid not in by_id:
        raise SystemExit(f"no attribute with id {aid} (0..{ATTR_ROWS - 1})")
    return by_id[aid]


def parse_pairs(specs, what):
    """['32=2092', ...] -> [(32, 2092), ...]"""
    out = []
    for spec in specs or ():
        head, _, tail = spec.partition("=")
        if not tail:
            raise SystemExit(f"--{what} wants ID=VALUE, got {spec!r}")
        try:
            out.append((int(head, 0), int(tail, 0)))
        except ValueError:
            raise SystemExit(f"--{what} {spec!r}: both sides must be numbers")
    return out


def refuse_bad_output(src, out):
    """Out of place, outside C:\\gw, and outside every checkout of this repo."""
    out_abs = os.path.normcase(os.path.abspath(out))
    if out_abs == os.path.normcase(os.path.abspath(src)):
        raise SystemExit(
            f"--out is the input. This tool never patches in place: the "
            f"pristine copy is the only reference for every future scan.")
    if out_abs == LIVE_INSTALL or out_abs.startswith(LIVE_INSTALL + os.sep):
        raise SystemExit(
            f"Refusing to write into the owner's install at {LIVE_INSTALL}. "
            f"That copy is read-only to this project, always.")
    # THE VAULT IS THE INTENDED DESTINATION, and it sits INSIDE the checkout.
    # The first version of this guard refused it -- while its own message told
    # the operator to write there -- so the tool could not perform the one job
    # it exists for. The vault is gitignored (that is the whole reason derived
    # ArenaNet artifacts live in it), so it is checked FIRST and allowed.
    try:
        vault = os.path.normcase(os.path.abspath(vaultpath.vault_root()))
        if out_abs == vault or out_abs.startswith(vault + os.sep):
            return
    except SystemExit:
        pass                        # no vault configured; fall through to refuse
    for root in working_tree_roots():
        if out_abs == root or out_abs.startswith(root + os.sep):
            raise SystemExit(
                f"Refusing to write a patched client into a checkout of this "
                f"repository ({root}). A patched client is a derived ArenaNet "
                f"artifact and the provenance gate keeps those out of the tree. "
                f"Write it under the vault instead: {vaultpath.vault_root()}")


def apply_edits(data, found, profession, edits):
    """Return (new_bytes, [(table, offset, old, new)]) -- same length, always."""
    if not 0 <= profession < PROFESSIONS:
        raise SystemExit(
            f"profession {profession} outside 0..{PROFESSIONS - 1}. The whole "
            f"point of a reskin is that the id stays LEGAL, so no bound check "
            f"can fire; an out-of-range host would defeat it.")
    out = bytearray(data)
    log = []
    for table, sid in edits.items():
        base, vals = found[table]
        off = base + profession * ROW
        old = struct.unpack_from("<I", out, off)[0]
        struct.pack_into("<I", out, off, sid)
        log.append((table, off, old, sid))
    return bytes(out), log


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", help="client to read; default is the pinned pristine copy")
    ap.add_argument("--out", help="where to write the patched copy (out of place)")
    ap.add_argument("--profession", type=int, default=8,
                    help="the shipped id to repurpose (default 8, Ritualist -- "
                         "chosen because all its identity string ids live in ONE "
                         "archive text file, where other professions straddle 2-4)")
    ap.add_argument("--show", action="store_true",
                    help="print the located tables and exit")
    for t in TABLES:
        ap.add_argument(f"--{t}", type=int, metavar="STRING_ID",
                        help=f"new string id for the {t} table")
    ap.add_argument("--attr-name", action="append", metavar="ATTR=STRING_ID",
                    help="rename an attribute (row+0x08). Repeatable.")
    ap.add_argument("--attr-owner", action="append", metavar="ATTR=PROFESSION",
                    help="reassign which profession owns an attribute "
                         "(row+0x00). Nine rows sit on profession 11 with zero "
                         "skills and are the natural donors. Repeatable.")
    ap.add_argument("--attr-primary", action="append", metavar="ATTR=0|1",
                    help="set or CLEAR an attribute's primary marker "
                         "(row+0x10). Symmetric on purpose: a profession has "
                         "exactly one primary, so moving it means clearing the "
                         "old one, and a set-only verb would leave two. "
                         "Repeatable.")
    ap.add_argument("--attrs", action="store_true",
                    help="print the attribute table grouped by profession")
    a = ap.parse_args(argv)

    src, why = (a.exe, "given with --exe") if a.exe else pinned.find()
    if not os.path.isfile(src):
        raise SystemExit(f"Not found: {src}")
    if os.path.normcase(os.path.abspath(src)).startswith(LIVE_INSTALL):
        print(f"reading (read-only) the live install: {src}")
    data = open(src, "rb").read()
    print(f"client: {src}\n        ({why})")

    found = locate(data)
    print(f"located {len(found)} profession name tables, structurally:")
    for t in TABLES:
        base, vals = found[t]
        mark = " <- UNGUARDED (no bound check at its read site)" if t == "data" else ""
        print(f"  {t:7s} file 0x{base:08X}  {vals}{mark}")

    abase, arows = locate_attrib(data)
    print(f"located s_attrib at file 0x{abase:08X}, {len(arows)} rows")
    if a.attrs:
        groups = {}
        for r in arows:
            groups.setdefault(r["owner"], []).append(r)
        for prof in sorted(groups):
            tag = "  <- SPARE (reserved)" if prof == SPARE_OWNER else ""
            ids = [(r["id"], r["name"], "P" if r["primary"] else "")
                   for r in groups[prof]]
            print(f"  prof {prof:>2}: {ids}{tag}")

    renames = parse_pairs(a.attr_name, "attr-name")
    owners = parse_pairs(a.attr_owner, "attr-owner")
    primaries = parse_pairs(a.attr_primary, "attr-primary")
    edits = {t: getattr(a, t) for t in TABLES if getattr(a, t) is not None}
    if a.show or a.attrs or not (edits or renames or owners or primaries):
        if not (a.show or a.attrs):
            print("\nnothing to do: pass at least one of "
                  + ", ".join(f"--{t} ID" for t in TABLES)
                  + ", --attr-name, --attr-owner, --attr-primary")
        return 0
    if not a.out:
        raise SystemExit("--out is required when writing. This tool never "
                         "patches in place.")
    refuse_bad_output(src, a.out)

    patched, log = apply_edits(data, found, a.profession, edits)
    if renames or owners or primaries:
        patched, alog = attrib_edits(patched, arows, renames, owners, primaries)
        log += [(t, off, old, new) for t, off, old, new in alog]
    assert len(patched) == len(data), "a reskin is same-length by construction"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(patched)
    changed = sum(1 for x, y in zip(data, patched) if x != y)
    print(f"\nprofession {a.profession}, {len(log)} edit(s):")
    for table, where, old, new in log:
        # An attribute edit's second element is an ATTRIBUTE ID, not a file
        # offset. Printing it as `file 0x...` reads as an address and is wrong
        # in exactly the way an operator would act on -- attribute 32 showed as
        # `file 0x00000020`.
        loc = (f"attr {where:<4}" if str(table).startswith("attr-")
               else f"file 0x{where:08X}")
        print(f"  {table:12s} {loc}  {old} -> {new}")
    # "at most", not "expected": a dword write disturbs only the bytes that
    # actually differ, so 2 changed bytes for 2 edits is correct when both ids
    # share their high bytes (2048 -> 2092 is 00 08 -> 2C 08). The invariant
    # worth printing is CONTAINMENT, which the count alone cannot show.
    print(f"wrote {a.out}\n  {changed} byte(s) differ, at most {len(log) * ROW} "
          f"possible for {len(log)} dword edit(s); length unchanged at "
          f"{len(patched):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
