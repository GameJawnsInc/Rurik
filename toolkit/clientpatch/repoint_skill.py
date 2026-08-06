"""Repoint one skill's name, description and icon ids at another skill's.

The cheapest real test of Route 4 in studies/datwrite/FINDINGS.md, and the only
one that needs no archive write, no injected DLL and no new content: every value
we write already exists in the client, so the client can definitely resolve it.
If skill A starts drawing skill B's icon and tooltip, then the PE row is what
drives rendering and a re-skinned skill can borrow art and text today.

It also settles a CONTESTED item. studies/skills/FINDINGS.md records a three-way
disagreement about which of +0x8c / +0x90 / +0x94 is the high-resolution icon:
Tyria-Extractor says 0x8c standard and 0x90 hi-res with nothing at 0x94; GWCA
names 0x94 icon_file_id_hi_res; GWToolbox is not self-consistent across its own
three call sites. studies/datwrite/FINDINGS.md measured that +0x8c and +0x90 are
populated in ~3,439 of 3,443 rows and pair strictly one-to-one, while +0x94 is
populated in only 86. Repointing ONE field at a time and looking at the bar is
what turns that from a population count into an answer.

    python toolkit/clientpatch/repoint_skill.py --target 320 --donor 322
    python toolkit/clientpatch/repoint_skill.py --target 320 --donor 322 \
        --fields icon
    python toolkit/clientpatch/repoint_skill.py --show 320

FINDING THE TABLE. Structurally, never by address, because the address moves with
every build: row 0 has id 0, the u32 at row-0 +0x2c holds the record count, and
the first 64 ids equal their own index. That last clause is load-bearing -- a
first version of this scan omitted it and returned SIX candidates in .rdata, all
coincidences, because two adjacent dwords reading 0 then 1 is common in a 10 MB
data section. With it, exactly one candidate survives on this build.

The result is then cross-checked against ArenaNet's own text: the table's tail
abuts P:\\Code\\Gw\\Const\\ConstSkill.cpp and its own assertion strings, and
`arrsize(s_skill)` appears three times in that block. That check can fail, which
is the point of having it -- a table found by shape alone could be the wrong
array, but the wrong array does not have ConstSkill.cpp bolted to its end.

NEVER writes in place and never touches C:\\gw. It reads one exe and writes
another, defaulting to a sibling with a suffix, exactly like make_custom_client.py.
"""

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gwpe import PE  # noqa: E402

REC = 0xA4
OFF_ID = 0x00
OFF_COUNT = 0x2C          # on row 0 only; the PvP twin id on every other row

# The fields worth borrowing. Everything else in the row is a stat, and stats are
# a separate experiment -- changing a cost or a recharge proves something about
# the client's arithmetic, not about its asset resolution.
FIELDS = {
    "icon":    0x8C,
    "icon2":   0x90,
    "icon_hi": 0x94,
    "name":    0x98,
    "concise": 0x9C,
    "desc":    0xA0,
}
DEFAULT_FIELDS = ["name", "concise", "desc", "icon", "icon2", "icon_hi"]

# ArenaNet's own text, immediately after the table. Used as a corroborating
# check on the structural scan, never as the way the table is found.
ANCHORS = (b"ConstSkill.cpp", b"arrsize(s_skill)")

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))


def find_table(pe):
    """The unique candidate, or an explanation of why there isn't one."""
    d = pe.data
    hits = []
    for s in pe.sections:
        base, size = s["rawptr"], s["rawsize"]
        if not size:
            continue
        end = base + size - REC * 2
        off = base
        while off < end:
            if struct.unpack_from("<I", d, off + OFF_ID)[0] == 0:
                count = struct.unpack_from("<I", d, off + OFF_COUNT)[0]
                if 500 <= count <= 20000 and off + count * REC <= base + size:
                    n = min(count, 64)
                    if all(struct.unpack_from("<I", d, off + i * REC)[0] == i
                           for i in range(n)):
                        hits.append((off, count, s["name"]))
            off += 4
    if not hits:
        raise SystemExit(
            "No skill table found. The row layout may have changed with the "
            "build; re-derive it before trusting anything else in this file.")
    if len(hits) > 1:
        raise SystemExit(
            f"{len(hits)} candidate tables, expected 1. Refusing to guess:\n  " +
            "\n  ".join(f"file 0x{o:08X} count={c} section {s}"
                        for o, c, s in hits))
    return hits[0]


def check_anchor(pe, off, count):
    """Does ArenaNet's own text sit where it should? Reports; does not gate."""
    tail = off + count * REC
    window = pe.data[tail:tail + 512]
    found = [a.decode() for a in ANCHORS if a in window]
    return found, tail


def row_values(d, table, sid):
    r = table + sid * REC
    return {k: struct.unpack_from("<I", d, r + o)[0] for k, o in FIELDS.items()}


def show(pe, table, count, sid):
    v = row_values(pe.data, table, sid)
    print(f"  skill {sid}:")
    for k in DEFAULT_FIELDS:
        extra = ""
        if k in ("name", "concise", "desc") and v[k]:
            extra = f"   -> text file {v[k] // 1024}, record {v[k] % 1024}"
        print(f"    +0x{FIELDS[k]:02X} {k:<8} {v[k]}{extra}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default=r"C:\gd\Rurik\vault\run"
                                     r"\2026-07-29_221c13772c7a\Gw.exe",
                    help="Source executable. Read, never written.")
    ap.add_argument("--out", help="Destination. Default: <exe>.repoint.exe")
    ap.add_argument("--target", type=int, help="Skill id whose row is rewritten")
    ap.add_argument("--donor", type=int, help="Skill id whose values are copied")
    ap.add_argument("--fields", default=",".join(DEFAULT_FIELDS),
                    help="Comma-separated subset of: " + ", ".join(FIELDS) +
                         ". Use one at a time to find out which icon field the "
                         "skillbar actually draws.")
    ap.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE",
                    help="Write a raw value into a field instead of copying a "
                         "donor's. Repeatable. VALUE is a file id or string id, "
                         "NOT a skill id -- which is the only way to aim a row "
                         "at an asset no shipped skill points to.")
    ap.add_argument("--show", type=int, metavar="ID",
                    help="Print one row's ids and exit. Writes nothing.")
    ap.add_argument("--in-place", action="store_true",
                    help="Overwrite --exe itself. Refused for anything under "
                         "C:\\gw regardless.")
    a = ap.parse_args()

    src = os.path.abspath(a.exe)
    if os.path.normcase(src).startswith(LIVE_INSTALL):
        raise SystemExit(f"Refusing to read-and-rewrite the live install: {src}\n"
                         f"Pass the run-dir copy.")
    if not os.path.exists(src):
        raise SystemExit(f"Not found: {src}")

    pe = PE(src)
    table, count, section = find_table(pe)
    found, tail = check_anchor(pe, table, count)
    print(f"{os.path.basename(src)}")
    print(f"  skill table  file 0x{table:08X}  RVA 0x{pe.off_to_rva(table):08X}"
          f"  section {section}")
    print(f"  rows         {count}  (ids 0..{count - 1}), ends file 0x{tail:08X}")
    print(f"  anchor       {', '.join(found) if found else 'NOT FOUND -- the '
          'table was located by shape alone; treat the result with suspicion'}")
    print()

    if a.show is not None:
        if not 0 <= a.show < count:
            raise SystemExit(f"id {a.show} out of range 0..{count - 1}")
        show(pe, table, count, a.show)
        return 0

    if a.target is None or (a.donor is None and not a.set):
        raise SystemExit("need --target and either --donor or --set FIELD=VALUE "
                         "(or --show ID)")
    for sid in ([a.target] + ([a.donor] if a.donor is not None else [])):
        if not 0 <= sid < count:
            raise SystemExit(f"id {sid} out of range 0..{count - 1}")

    explicit = {}
    for spec in a.set:
        key, sep, raw = spec.partition("=")
        key = key.strip()
        if not sep or key not in FIELDS:
            raise SystemExit(f"--set wants FIELD=VALUE with FIELD one of "
                             f"{list(FIELDS)}; got {spec!r}")
        explicit[key] = int(raw, 0)

    if a.donor is not None:
        fields = [f.strip() for f in a.fields.split(",") if f.strip()]
        unknown = [f for f in fields if f not in FIELDS]
        if unknown:
            raise SystemExit(f"unknown field(s): {unknown}. Known: {list(FIELDS)}")
        dv = row_values(pe.data, table, a.donor)
    else:
        fields, dv = [], {}
    dv.update(explicit)
    fields += [k for k in explicit if k not in fields]

    print("before:")
    show(pe, table, count, a.target)
    if a.donor is not None:
        print(f"  donor {a.donor}:")
        for k in fields:
            if k not in explicit:
                print(f"    +0x{FIELDS[k]:02X} {k:<8} {dv[k]}")
    if explicit:
        print("  explicit (raw ids, no donor skill involved):")
        for k, v in explicit.items():
            print(f"    +0x{FIELDS[k]:02X} {k:<8} {v}")
    print()

    data = bytearray(pe.data)
    trow = table + a.target * REC
    for k in fields:
        off = trow + FIELDS[k]
        old = struct.unpack_from("<I", data, off)[0]
        struct.pack_into("<I", data, off, dv[k])
        print(f"  wrote +0x{FIELDS[k]:02X} {k:<8} {old} -> {dv[k]}  "
              f"(file 0x{off:08X})")

    dst = a.out or (src if a.in_place else
                    os.path.splitext(src)[0] + ".repoint.exe")
    dst = os.path.abspath(dst)
    if os.path.normcase(dst).startswith(LIVE_INSTALL):
        raise SystemExit(f"Refusing to write into the live install: {dst}")
    with open(dst, "wb") as f:
        f.write(data)
    print(f"\nwrote {dst}  ({len(data)} bytes)")

    # Read it back and confirm, rather than trusting the write.
    v = PE(dst)
    t2, c2, _ = find_table(v)
    if t2 != table or c2 != count:
        raise SystemExit("the table moved in the output -- something is wrong")
    after = row_values(v.data, t2, a.target)
    bad = [k for k in fields if after[k] != dv[k]]
    print("verify:", "OK, every repointed field reads back as the donor's"
          if not bad else f"MISMATCH on {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
