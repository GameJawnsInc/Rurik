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

    edits = {t: getattr(a, t) for t in TABLES if getattr(a, t) is not None}
    if a.show or not edits:
        if not a.show:
            print("\nnothing to do: pass at least one of "
                  + ", ".join(f"--{t} ID" for t in TABLES))
        return 0
    if not a.out:
        raise SystemExit("--out is required when writing. This tool never "
                         "patches in place.")
    refuse_bad_output(src, a.out)

    patched, log = apply_edits(data, found, a.profession, edits)
    assert len(patched) == len(data), "a reskin is same-length by construction"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(patched)
    changed = sum(1 for x, y in zip(data, patched) if x != y)
    print(f"\nprofession {a.profession}, {len(log)} table(s):")
    for table, off, old, new in log:
        print(f"  {table:7s} file 0x{off:08X}  {old} -> {new}")
    print(f"wrote {a.out}\n  {changed} byte(s) differ, {len(log) * ROW} expected; "
          f"length unchanged at {len(patched):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
