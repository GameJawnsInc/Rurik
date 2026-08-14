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


def attrib_edits(data, rows, renames=(), owners=(), primaries=(), descs=()):
    """Apply attribute edits. Same-length by construction, like the names.

    Four verbs, because they are four different claims about the client:
      rename  -- row+0x08, the name string id: does the panel read THIS row?
      owner   -- row+0x00, the profession: is the panel's attribute list
                 DERIVED from this field rather than from a per-profession
                 table? Nine rows sit on profession 11 with zero skills, so
                 there is somewhere to take one FROM.
      primary -- row+0x10, which of a profession's attributes is primary.
      desc    -- row+0x0C, the DESCRIPTION string id.

    `desc` is the field this module parsed from the first day and never wrote,
    and the gap was visible in game: RESKIN.md 19.7 shipped a profession whose
    attribute rendered our authored name `Storm Calling` above string 2147, which
    begins "For each rank of Spawning Power you have..." -- ArenaNet's text,
    describing an inherent effect our profession does not have. An attribute is
    its name AND what the tooltip claims it does; only the first half was ours.

    It matters more than it looks. The primary-attribute passive turns out to be
    SERVER work (RESKIN.md 20), so the description is the ONLY place a custom
    passive is ever announced to the player, and the only part of one that lives
    in the client at all.
    """
    out = bytearray(data)
    log = []
    by_id = {r["id"]: r for r in rows}
    for aid, sid in renames:
        r = _row(by_id, aid)
        struct.pack_into("<I", out, r["off"] + ATTR_NAME, sid)
        log.append(("attr-name", aid, r["name"], sid))
    for aid, sid in descs:
        r = _row(by_id, aid)
        struct.pack_into("<I", out, r["off"] + ATTR_DESC, sid)
        log.append(("attr-desc", aid, r["desc"], sid))
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


def load_recipe(path):
    """A profession design as a versioned file, not eleven command-line flags.

    Returns (host, {table: sid}, renames, owners, primaries, skill_profs,
    skill_attrs). Every value is a NUMBER -- profession, attribute, skill and
    string ids -- so a recipe carries no ArenaNet text and the client resolves
    every string from the owner's own archive at run time.

    tomllib is standard library from 3.11, so this adds no dependency.
    """
    import tomllib                                             # noqa: E402
    with open(path, "rb") as f:
        doc = tomllib.load(f)
    prof = doc.get("profession") or {}
    host = prof.get("host")
    if host is None:
        raise SystemExit(f"{path}: [profession] needs a host id")
    names = {t: prof[t] for t in TABLES if t in prof}
    renames, owners, primaries, descs = [], [], [], []
    for row in doc.get("attribute", ()):
        if "id" not in row:
            raise SystemExit(f"{path}: every [[attribute]] needs an id")
        aid = row["id"]
        if "name" in row:
            renames.append((aid, row["name"]))
        if "desc" in row:
            descs.append((aid, row["desc"]))
        if "owner" in row:
            owners.append((aid, row["owner"]))
        if "primary" in row:
            primaries.append((aid, 1 if row["primary"] else 0))
    skill_profs, skill_attrs = [], []
    for row in doc.get("skill", ()):
        if "id" not in row:
            raise SystemExit(f"{path}: every [[skill]] needs an id")
        sid = row["id"]
        if "profession" in row:
            skill_profs.append((sid, row["profession"]))
        if "attribute" in row:
            skill_attrs.append((sid, row["attribute"]))
    return (host, names, renames, owners, primaries, descs,
            skill_profs, skill_attrs)


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


# The skill table. Located by skilltable.py's own structural scan rather than
# a second implementation -- it already refuses on a non-unique candidate, and
# two locators for one table is two things to keep in step.
SKILL_PROF, SKILL_ATTR = 0x28, 0x29
NO_ATTRIBUTE = 51              # the client's own "no attribute" marker


def locate_skills(data):
    """(file_offset, count, stride) for s_skill."""
    import skilltable                                          # noqa: E402
    base, count, _score = skilltable.locate_table(data)
    return base, count, skilltable.RECORD_SIZE


def skill_edits(data, base, count, stride, profs=(), attrs=()):
    """Reassign skills. Two SINGLE-BYTE fields, so same-length is trivial here.

    profs -- row+0x28, which profession owns the skill
    attrs -- row+0x29, which attribute it scales with. This is the one the
             Skills panel groups by, so it is the field with a countable
             visible consequence: move N skills and the two group headers
             must move by N in opposite directions.
    """
    out = bytearray(data)
    log = []
    for sid, prof in profs:
        _check_skill(sid, count)
        if not 0 <= prof <= SPARE_OWNER:
            raise SystemExit(f"skill profession {prof} outside 0..{SPARE_OWNER}")
        off = base + sid * stride + SKILL_PROF
        log.append(("skill-prof", sid, out[off], prof))
        out[off] = prof
    for sid, attr in attrs:
        _check_skill(sid, count)
        if not 0 <= attr <= NO_ATTRIBUTE:
            raise SystemExit(
                f"skill attribute {attr} outside 0..{NO_ATTRIBUTE} "
                f"({NO_ATTRIBUTE} is the client's own no-attribute marker)")
        off = base + sid * stride + SKILL_ATTR
        log.append(("skill-attr", sid, out[off], attr))
        out[off] = attr
    return bytes(out), log


def _check_skill(sid, count):
    if not 0 < sid < count:
        raise SystemExit(
            f"skill id {sid} outside 1..{count - 1}. Id 0 is not a skill -- "
            f"setting its bit in the unlock bitmap is what asserted the client "
            f"for seven sessions (studies/profession/RUNS.md s10).")


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
    ap.add_argument("--profession", type=int, default=None,
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
    ap.add_argument("--attr-desc", action="append", metavar="ATTR=STRING_ID",
                    help="repoint an attribute's DESCRIPTION (row+0x0C). The "
                         "field this tool parsed and never wrote: a reskin that "
                         "renames an attribute but not its description ships our "
                         "word above ArenaNet's explanation of an effect the "
                         "profession does not have. Repeatable.")
    ap.add_argument("--attr-primary", action="append", metavar="ATTR=0|1",
                    help="set or CLEAR an attribute's primary marker "
                         "(row+0x10). Symmetric on purpose: a profession has "
                         "exactly one primary, so moving it means clearing the "
                         "old one, and a set-only verb would leave two. "
                         "Repeatable.")
    ap.add_argument("--skill-attr", action="append", metavar="SKILL=ATTR",
                    help="reassign which attribute a skill scales with "
                         "(row+0x29). The Skills panel groups by this, so it "
                         "is the field with a countable visible effect. "
                         "Repeatable.")
    ap.add_argument("--skill-prof", action="append", metavar="SKILL=PROFESSION",
                    help="reassign which profession owns a skill (row+0x28). "
                         "Repeatable.")
    ap.add_argument("--recipe", metavar="FILE.toml",
                    help="apply a profession design from a file. Everything a "
                         "recipe holds is a number (profession, attribute, "
                         "skill and string ids), so it carries no ArenaNet "
                         "text. See recipes/ritualist-demo.toml.")
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

    sbase, scount, sstride = locate_skills(data)
    print(f"located s_skill at file 0x{sbase:08X}, {scount} rows, "
          f"stride 0x{sstride:X}")
    skill_profs = parse_pairs(a.skill_prof, "skill-prof")
    skill_attrs = parse_pairs(a.skill_attr, "skill-attr")
    renames = parse_pairs(a.attr_name, "attr-name")
    owners = parse_pairs(a.attr_owner, "attr-owner")
    primaries = parse_pairs(a.attr_primary, "attr-primary")
    descs = parse_pairs(a.attr_desc, "attr-desc")
    edits = {t: getattr(a, t) for t in TABLES if getattr(a, t) is not None}
    if a.recipe:
        # A recipe is the base; explicit flags layer on top, so a design can be
        # versioned and still tweaked for one run without editing the file.
        (rhost, rnames, rren, rown, rpri,
         rdescs, rsprof, rsattr) = load_recipe(a.recipe)
        # Precedence, stated rather than implied: an explicit --profession
        # beats the recipe's host, so a versioned design can be aimed at a
        # different host for one run without editing the file.
        if a.profession is None:
            a.profession = rhost
        edits = {**rnames, **edits}
        renames, owners, primaries = rren + renames, rown + owners, rpri + primaries
        descs = rdescs + descs
        skill_profs, skill_attrs = rsprof + skill_profs, rsattr + skill_attrs
        print(f"recipe {a.recipe}: host profession {rhost}, "
              f"{len(rnames)} name(s), "
              f"{len(rren) + len(rown) + len(rpri) + len(rdescs)} "
              f"attribute edit(s), {len(rsprof) + len(rsattr)} skill edit(s)")
    if a.show or a.attrs or not (edits or renames or owners or primaries
                                 or descs or skill_profs or skill_attrs):
        if not (a.show or a.attrs):
            print("\nnothing to do: pass at least one of "
                  + ", ".join(f"--{t} ID" for t in TABLES)
                  + ", --attr-name, --attr-desc, --attr-owner, "
                    "--attr-primary")
        return 0
    if not a.out:
        raise SystemExit("--out is required when writing. This tool never "
                         "patches in place.")
    refuse_bad_output(src, a.out)

    if a.profession is None:
        a.profession = 8            # Ritualist: the owner's chosen host
    patched, log = apply_edits(data, found, a.profession, edits)
    if renames or owners or primaries or descs:
        patched, alog = attrib_edits(patched, arows, renames, owners,
                                     primaries, descs)
        log += alog
    if skill_profs or skill_attrs:
        patched, slog = skill_edits(patched, sbase, scount, sstride,
                                    skill_profs, skill_attrs)
        log += slog
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
        loc = (f"skill {where:<5}" if str(table).startswith("skill-")
               else f"attr {where:<4}" if str(table).startswith("attr-")
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
