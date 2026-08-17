"""`s_heroClientData` as content rows: ids and costs, never resolved text.

THE PROVENANCE RULING THIS EXISTS UNDER. `CLAUDE.md`'s gate permits measured
facts in bulk -- "levels, bounds, counts, strides, ids, offsets, addresses,
layouts" -- on three conditions: the extractor is in this repo and the row
names it, the row records the build, and provenance is per row. This table is
six numeric dwords per hero: a self-referential index, an unlock cost, one
unresolved constant, and three STRING IDS. Ids are the permitted noun, and the
ids are all that ships. `content.py` enforces conditions 1 and 2 for
`source = "client-table"`; condition 3 is spelled on every row here because
that is the one it cannot check.

**The English never ships.** A hero's name, epithet and biography stay as
string ids and the CLIENT resolves them from the owner's own archive at render
time -- the same "commit the id, resolve at run time" pattern `mapbuild.py`
proves and `0x01BF` proves on the wire. `--resolve` exists for eyeballing a
row or two during analysis and REFUSES to write a file, because a committed
column of resolved names is exactly the bulk expression the gate refuses.

ANCHORING, AND THE TRAP. `s_titleClientData` sits **six instructions** from
`s_heroClientData` in `ConstChar`-adjacent code -- accessor `0x005A9350`
(`cmp esi,0x30`, stride 12, base `0xA35B80`) versus `0x005A9380`
(`cmp esi,0x28`, stride 24, base `0xA35E08`) -- and this arc lost a contested
reading to exactly that adjacency before the client's own assert strings
settled it (`studies/heroes/FINDINGS.md` 2). So this module does not carry an
address at all: it locates by `consttable`'s structural anchor
(`P:\\Code\\Gw\\Const\\ConstHero.cpp`) and then REFUSES anything whose geometry
is not the hero table's.

    python toolkit/clientscan/heroes_table.py                 # summary
    python toolkit/clientscan/heroes_table.py --toml          # content rows
    python toolkit/clientscan/heroes_table.py --resolve 1 2   # ANALYSIS ONLY

Standard library only, except the read-only client analysis carve-out
`consttable` already takes.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import buildid               # noqa: E402
import consttable            # noqa: E402
import pinned                # noqa: E402

SYMBOL = "s_heroClientData"
# What the hero table IS, from the client's own bounds. Not a preference: the
# refusal below is the whole defence against the title table next door.
EXPECT_STRIDE = 24
EXPECT_COUNT = 40           # ChCliApi:4446 `hero < HEROES`, `cmp esi,0x28`
HERO_UNUSED = 0             # ChCliApi:4447, fires only on `test esi,esi`

FIELDS = ("index", "unlock_cost", "unk8",
          "name_string_id", "epithet_string_id", "bio_string_id")


class WrongTable(Exception):
    """The located table is not the hero table. Refuse rather than emit."""


def load(exe_path=None):
    """(pe, table) for s_heroClientData, or raise WrongTable."""
    if exe_path is None:
        exe_path, _why = consttable.find_exe()
    pe = consttable.PE(exe_path)
    table = consttable.table_for(pe, SYMBOL)
    if table.stride != EXPECT_STRIDE or table.count != EXPECT_COUNT:
        raise WrongTable(
            f"located {SYMBOL} as {table.count} x {table.stride} B at file "
            f"0x{table.base:06X}, but the client's own bounds say "
            f"{EXPECT_COUNT} x {EXPECT_STRIDE}. s_titleClientData is 48 x 12 "
            f"and sits six instructions away -- refusing rather than emitting "
            f"the wrong table's numbers as heroes")
    return pe, table


def rows(pe, table):
    """One dict per hero. Six dwords, every one a measurement."""
    out = []
    for i in range(table.count):
        vals = struct.unpack("<6I", table.record(pe, i))
        row = dict(zip(FIELDS, vals))
        row["row"] = i
        out.append(row)
    return out


def check(rows_):
    """[complaint] -- closure checks the artifact can refute, not decoration."""
    bad = []
    off = [r for r in rows_ if r["index"] != r["row"]]
    if off:
        bad.append(f"the index column disagrees with the row number on "
                   f"{len(off)} row(s): {[r['row'] for r in off][:6]} -- this "
                   f"column is what identifies the table, so a mismatch means "
                   f"the base or stride is wrong")
    placeholder = rows_[HERO_UNUSED]
    if placeholder["name_string_id"] == 0:
        bad.append("row 0's name id is 0; it is expected to be a real id that "
                   "resolves to the EMPTY string, which is a different fact")
    live = [r for r in rows_[1:] if r["name_string_id"] == 0]
    if live:
        bad.append(f"{len(live)} hero row(s) past the reserved slot carry no "
                   f"name id: {[r['row'] for r in live][:6]}")
    return bad


def toml(pe, table, rows_, exe_path):
    """`vault/content/heroes.toml`, provenance per row, ids only.

    The build is MEASURED from `exe_path` and an image that will not name its
    build is REFUSED. It was `pinned.BUILD` until 2026-08-17 -- see
    `consttable.effect_toml`, which had the identical defect for the identical
    reason, and `pinned.identify_build` for the other two.
    """
    build, how = buildid.of_image(exe_path)
    if build is None:
        raise pinned.WrongBuild(
            f"REFUSING to emit hero rows read from {exe_path}\n"
            f"  {how}\n"
            f"  The row must record the build it was derived on (condition 2);\n"
            f"  writing {pinned.BUILD} on an unidentified image is the misreport\n"
            f"  that condition exists to prevent.")
    head = [
        "# s_heroClientData, read out of the client's own static table.",
        "#",
        f"#   client   {exe_path}",
        f"#   build    {build}  ({how})",
        f"#   table    file 0x{table.base:06X} .. 0x{table.end:06X}, "
        f"{table.count} x {table.stride} B",
        f"#   anchor   file 0x{table.anchor_off:06X}, ConstHero.cpp",
        f"#   witness  count from the {table.count_from}; "
        f"{table.refs} code reference(s) to the base",
        "#",
        "# IDS ONLY, and that is the gate rather than a style choice: the name,",
        "# epithet and biography are STRING IDS the client resolves from the",
        "# owner's own archive at render time. No English is committed here.",
        "# Row 0 is the HERO_UNUSED placeholder (ChCliApi:4447) and is kept so",
        "# the table's own indexing is preserved rather than silently rebased.",
        "",
    ]
    prov = ('{ source = "client-table", '
            'extractor = "toolkit/clientscan/heroes_table.py", '
            f'build = {build}, '
            f'note = "%s[%d]; table at file 0x{table.base:06X}, stride '
            f'{table.stride}, {table.count} records, located by the anchor '
            f'\\"ConstHero.cpp\\" at file 0x{table.anchor_off:06X}" }}')
    body = []
    for r in rows_:
        body.append(f"[[hero]]")
        for f in FIELDS:
            body.append(f"{f} = {r[f]}")
        body.append("provenance = " + (prov % (SYMBOL, r["row"])))
        body.append("")
    return "\n".join(head + body)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=None, help="client; default is the pin")
    ap.add_argument("--toml", action="store_true",
                    help="emit content rows (ids only) on stdout")
    ap.add_argument("--resolve", nargs="*", type=int, metavar="ROW",
                    help="ANALYSIS ONLY: resolve the name ids of a few named "
                         "rows through the owner's archive and print them. "
                         "Refuses without explicit rows -- a whole resolved "
                         "column is the bulk expression the gate refuses.")
    a = ap.parse_args(argv)

    exe, why = ((a.exe, "given on the command line") if a.exe
                else consttable.find_exe())
    try:
        pe, table = load(exe)
    except WrongTable as ex:
        print(f"REFUSING: {ex}")
        return 2
    rs = rows(pe, table)
    complaints = check(rs)

    if a.toml:
        if complaints:
            print("REFUSING to emit: " + "; ".join(complaints), file=sys.stderr)
            return 2
        sys.stdout.write(toml(pe, table, rs, exe))
        return 0

    print(f"client: {exe}")
    print(f"        ({why})")
    print()
    print(f"{SYMBOL}: {table.count} x {table.stride} B at file "
          f"0x{table.base:06X}, anchor 0x{table.anchor_off:06X} (ConstHero.cpp)")
    _b, _how = buildid.of_image(exe)
    print(f"  build {_b if _b is not None else 'UNKNOWN'}   {table.refs} "
          f"reference(s) to the base")
    print(f"        ({_how})")
    print(f"  closure: base + {table.count}*{table.stride} == "
          f"0x{table.base + table.count * table.stride:06X}")
    for c in complaints:
        print(f"  [WARN] {c}")
    if not complaints:
        print("  index column agrees with the row number on every row")
    print(f"\n  {'row':>4} {'unlock':>8} {'unk8':>8} {'name':>8} "
          f"{'epithet':>8} {'bio':>8}")
    for r in rs:
        print(f"  {r['row']:>4} {r['unlock_cost']:>8} {r['unk8']:>8} "
              f"{r['name_string_id']:>8} {r['epithet_string_id']:>8} "
              f"{r['bio_string_id']:>8}")

    if a.resolve is not None:
        if not a.resolve:
            print("\n--resolve needs explicit row numbers. Resolving the whole "
                  "column is the bulk expression the provenance gate refuses; "
                  "a row or two as evidence for a claim is a measurement.")
            return 2
        sys.path.insert(0, HERE)
        import textrec
        print()
        for i in a.resolve:
            if not 0 <= i < len(rs):
                print(f"  row {i} is outside 0..{len(rs) - 1}")
                continue
            nid = rs[i]["name_string_id"]
            print(f"  row {i:>3} name id {nid} -> {textrec.resolve(nid)!r}"
                  if hasattr(textrec, "resolve")
                  else f"  row {i:>3} name id {nid} "
                       f"(run textrec.py {nid} to resolve)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
