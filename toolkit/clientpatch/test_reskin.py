"""The profession reskin patcher: structural location, and the refusals.

studies/profession/RESKIN.md chose this route because a SHIPPED profession id
can be repurposed with same-length dword writes that no bound check can see.
That makes the patcher's correctness almost entirely about two things: does it
find the right bytes without being told an address, and does it refuse to write
where a patched client must never go.

Sections 0-2 build their own buffers and need NO vault and NO client, because a
locator defect is not a property of any one binary. Section 3 needs the vaulted
client and declares a skip without it.
"""

import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import checks                                                  # noqa: E402
import reskin                                                  # noqa: E402
import vaultpath                                               # noqa: E402

# MEASURED 2026-08-14: 68, and 68 again with RURIK_VAULT pointed at an empty
# directory -- which is worth a line, because this file's entry in CLAUDE.md says
# section 3 "skips without one" and no skip was declared on that run. Either
# `pinned.find()` does not honour RURIK_VAULT or it found a client another way;
# the claim is UNTESTED rather than false, and is left as found rather than
# asserted here, since it belongs to `pinned.py` and not to the reskin verb this
# commit adds.
LEDGER = checks.Ledger("reskin", floor=68)


def synth(name_ids=None, abbrev_ids=None, picker_ids=None, data_ids=None,
          extra=b""):
    """A buffer shaped like the parts of the client this tool reads.

    Deliberately not a PE: the locator works on raw bytes by anchor and shape,
    so a fixture that reproduced the PE would be testing the wrong thing.
    """
    name_ids = name_ids or list(range(2040, 2049)) + [31548, 31549]
    abbrev_ids = abbrev_ids or list(range(2049, 2058)) + [31553, 31554]
    picker_ids = picker_ids or list(range(2058, 2067)) + [31556, 34524]
    data_ids = data_ids or [57818] + name_ids[1:]
    out = bytearray(b"\x00" * 64)
    for ids, key in ((name_ids, "name"), (abbrev_ids, "abbrev"),
                     (picker_ids, "picker")):
        out += struct.pack("<11I", *ids) + reskin.ANCHORS[key] + b"\x00" * 3
    out += b"\x00" * 32 + struct.pack("<11I", *data_ids) + b"\x00" * 32
    return bytes(out + extra)


def section_locator():
    print("\n0. the locator, on buffers this test builds")
    found = reskin.locate(synth())
    LEDGER.ok(sorted(found) == ["abbrev", "data", "name", "picker"],
              "all four tables are located from anchors and shape alone",
              f"{sorted(found)} -- no address is ever hard-coded, because a "
              f"build-specific address is not part of any file format")
    LEDGER.ok(found["name"][1][0] == 2040 and found["abbrev"][1][0] == 2049,
              "and each anchor names the table that precedes it, not a neighbour",
              f"name[0]={found['name'][1][0]}, abbrev[0]={found['abbrev'][1][0]}")
    LEDGER.ok(found["data"][1][0] == 57818 and found["data"][1][1:9] == found["name"][1][1:9],
              "the unguarded .data table is found by VALUE against the located "
              "name table",
              f"{found['data'][1][:3]}... -- entry 0 differs while 1..8 match, "
              f"which is what distinguishes it from the name table itself")

    # Negative controls. Each breaks ONE assumption and must be refused ALONE.
    dup = synth() + reskin.ANCHORS["name"]
    LEDGER.ok(_refuses(dup, "occurs 2 times"),
              "a DUPLICATED anchor is refused rather than resolved",
              "two candidates and no way to choose is exactly when a patcher "
              "must stop, not guess")
    bad_shape = bytearray(synth())
    at = bad_shape.find(reskin.ANCHORS["name"])
    struct.pack_into("<I", bad_shape, at - reskin.SPAN + 8, 9999)
    LEDGER.ok(_refuses(bytes(bad_shape), "not consecutive"),
              "an anchor whose table is the WRONG SHAPE is refused",
              "the anchor and the shape are two independent witnesses; when "
              "they disagree one assumption is wrong for this build")
    twin = synth()
    twin = twin + struct.pack("<11I", *([57818] + list(range(2041, 2049)) + [31548, 31549]))
    LEDGER.ok(_refuses(twin, "candidate"),
              "an AMBIGUOUS .data match is refused",
              "it is the table read with no bound check at all, so a wrong "
              "guess there is the most dangerous edit this tool can make")
    missing = synth().replace(reskin.ANCHORS["picker"], b"id < 9\x00")
    LEDGER.ok(_refuses(missing, "occurs 0 times"),
              "and a MISSING anchor is refused, not silently skipped",
              "a tool that patched three of four tables would leave the "
              "profession half-renamed, which reads as a client bug")


def _refuses(data, needle):
    try:
        reskin.locate(data)
    except SystemExit as ex:
        return needle in str(ex)
    return False


def section_edits():
    print("\n1. the edits are same-length and land where they say")
    data = synth()
    found = reskin.locate(data)
    out, log = reskin.apply_edits(data, found, 8, {"name": 777, "abbrev": 888})
    LEDGER.ok(len(out) == len(data),
              "a reskin is SAME-LENGTH by construction",
              f"{len(out)} vs {len(data)} -- any length change would relocate "
              f"every datum after it, which is the whole cost this route avoids")
    diff = [i for i, (x, y) in enumerate(zip(data, out)) if x != y]
    name_off = found["name"][0] + 8 * reskin.ROW
    abbrev_off = found["abbrev"][0] + 8 * reskin.ROW
    windows = range(name_off, name_off + reskin.ROW), range(abbrev_off, abbrev_off + reskin.ROW)
    LEDGER.ok(diff and all(any(i in w for w in windows) for i in diff),
              "every changed byte lies inside one of the two intended dwords",
              f"{len(diff)} byte(s) -- counting them instead would be wrong: a "
              f"dword write disturbs only the bytes that actually differ, which "
              f"is how the real-client check first went red")
    LEDGER.ok(struct.unpack_from("<I", out, name_off)[0] == 777
              and struct.unpack_from("<I", out, found["name"][0])[0] == 2040,
              "the edit lands on entry 8 and leaves entry 0 alone",
              "an off-by-one here reskins a profession nobody asked for -- the "
              "costing's own first draft put the creation icon on Paragon")
    LEDGER.ok(all(t in ("name", "abbrev") for t, _, _, _ in log)
              and {t for t, _, _, _ in log} == {"name", "abbrev"},
              "and the log names exactly the tables that were touched",
              f"{[t for t, _, _, _ in log]}")
    refused = None
    try:
        reskin.apply_edits(data, found, 12, {"name": 1})
    except SystemExit as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None and "LEGAL" in refused,
              "an out-of-range host profession is REFUSED",
              f"{refused!r} -- the entire premise is that the id stays legal so "
              f"no bound check can fire; id 12 would defeat it and index past "
              f"an 11-entry table")


def section_output_guards():
    print("\n2. where a patched client may NOT be written")
    src = os.path.join(tempfile.gettempdir(), "rurik-reskin-src.bin")
    LEDGER.ok(_out_refused(src, src),
              "writing IN PLACE is refused",
              "the pristine copy is the only reference every future structural "
              "scan has")
    LEDGER.ok(_out_refused(src, r"C:\gw\Gw.exe"),
              "writing into the owner's install is refused",
              "C:\\gw is read-only to this project, always")
    tree = os.path.abspath(os.path.join(HERE, "..", ".."))
    LEDGER.ok(_out_refused(src, os.path.join(tree, "Gw.exe")),
              "writing into a checkout of this repo is refused",
              "a patched client is a derived ArenaNet artifact and the "
              "provenance gate keeps those out of the tree")
    roots = reskin.working_tree_roots()
    LEDGER.ok(len(roots) >= 1 and all(os.path.isabs(r) for r in roots),
              f"and the refusal covers {len(roots)} checkout root(s), not just this one",
              f"{sorted(roots)} -- a git worktree's root is not the main "
              f"checkout's, and both must be refused")
    # POSITIVE CONTROL: a guard that refuses everything protects nothing,
    # because the tool would never run.
    ok_path = os.path.join(tempfile.gettempdir(), "rurik-reskin-out.bin")
    LEDGER.ok(not _out_refused(src, ok_path),
              "while an ordinary path OUTSIDE all of them is allowed",
              f"{ok_path} -- the tool has to be usable or the guards are just "
              f"a way of never shipping")
    # THE CONTROL THAT ACTUALLY MATTERED, and the first version did not have it:
    # the vault is INSIDE the checkout, so the repo-tree refusal swallowed the
    # one destination the tool exists to write to -- while its own error message
    # named that destination. Caught by running the tool, not by this file.
    try:
        vault_out = os.path.join(vaultpath.vault_root(), "client-reskin", "Gw.exe")
    except SystemExit:
        LEDGER.skip("the vault-destination control", "no vault configured")
    else:
        LEDGER.ok(not _out_refused(src, vault_out),
                  "and the VAULT is allowed even though it sits inside the checkout",
                  f"{vault_out} -- it is gitignored, which is precisely why "
                  f"derived ArenaNet artifacts live there; a guard that refused "
                  f"it made the tool unable to do its only job")


def _out_refused(src, out):
    try:
        reskin.refuse_bad_output(src, out)
    except SystemExit:
        return True
    return False


def section_real_client():
    print("\n3. the real client (needs the vault)")
    try:
        import pinned
        path, _why = pinned.find()
    except SystemExit as ex:
        LEDGER.skip("the real-client half",
                    f"no client to read: {str(ex).splitlines()[0]}")
        return
    data = open(path, "rb").read()
    found = reskin.locate(data)
    LEDGER.ok(len(found) == 4,
              "all four tables locate in the pinned client",
              f"{ {t: hex(o) for t, (o, _) in found.items()} }")
    LEDGER.ok(found["name"][1][:9] == list(range(2040, 2049)),
              "the name table's nine shipped ids are consecutive from 2040",
              f"{found['name'][1]} -- ids 9 and 10 are the Factions/Nightfall "
              f"professions and sit apart, which is the shape the locator uses")
    LEDGER.ok(found["data"][1][1:9] == found["name"][1][1:9]
              and found["data"][0] != found["name"][0],
              "and the unguarded .data table is a DIFFERENT table with the "
              "same ids 1..8",
              f"name 0x{found['name'][0]:08X} vs data 0x{found['data'][0]:08X}")
    out, log = reskin.apply_edits(data, found, 8, {"name": 2041})
    diff = [i for i, (x, y) in enumerate(zip(data, out)) if x != y]
    off = found["name"][0] + 8 * reskin.ROW
    # NOT "exactly 4 bytes differ" -- that was this check's first version and it
    # went red for the right reason: 2048 -> 2041 is 00 08 -> F9 07, so the two
    # high bytes are zero in BOTH values and only 2 bytes move. How many bytes a
    # dword write disturbs depends on the values. The invariant that actually
    # matters is CONTAINMENT: every changed byte inside the intended dword, and
    # the dword reading back as asked.
    LEDGER.ok(diff and all(off <= i < off + reskin.ROW for i in diff)
              and len(out) == len(data),
              "a real reskin changes bytes ONLY inside the intended dword",
              f"{len(diff)} byte(s) at {[hex(i) for i in diff]} against the "
              f"dword at 0x{off:08X} -- everything else in 10 MB is "
              f"byte-identical, which is what makes this route auditable")
    LEDGER.ok(struct.unpack_from("<I", out, off)[0] == 2041,
              "and that dword reads back as the requested id",
              f"{struct.unpack_from('<I', out, off)[0]} -- containment alone "
              f"would also pass a write that changed nothing")
    LEDGER.ok(all(old != new for _, _, old, new in log),
              "and the log shows a real change, not a no-op",
              f"{log}")


def synth_attrib(owners=None, names=None):
    """A buffer shaped like s_attrib: 51 rows, then its own source path.

    Row layout: +0x00 owner, +0x04 attribute id, +0x08 name, +0x0C desc,
    +0x10 primary. ids are 0..50 in order, which is the shape check.
    """
    owners = owners or ([5] * 4 + [4] * 4 + [8] * 4 + [11] * 39)
    names = names or [2000 + i for i in range(reskin.ATTR_ROWS)]
    out = bytearray(b"\x00" * 32)
    for i in range(reskin.ATTR_ROWS):
        out += struct.pack("<5I", owners[i], i, names[i], names[i] + 1,
                           1 if i == 3 else 0)
    return bytes(out + reskin.ATTR_ANCHOR + b"\x00" * 8)


def section_attributes():
    print("\n4. the attribute table")
    data = synth_attrib()
    base, rows = reskin.locate_attrib(data)
    LEDGER.ok(len(rows) == 51 and [r["id"] for r in rows] == list(range(51)),
              "s_attrib locates from its own source-path anchor, 51 rows",
              f"base 0x{base:X} -- same locator shape as the name tables, and "
              f"the id column is the shape check")
    spare = [r["id"] for r in rows if r["owner"] == reskin.SPARE_OWNER]
    LEDGER.ok(len(spare) == 39 and 8 in {r["owner"] for r in rows},
              "and the reserved-profession rows are visible as spares",
              f"{len(spare)} rows on profession {reskin.SPARE_OWNER} -- the "
              f"real client has nine, which is the room a custom profession "
              f"has for attributes of its own")

    # Shape and range refusals, each breaking ONE assumption.
    scrambled = bytearray(data)
    struct.pack_into("<I", scrambled, 32 + 5 * reskin.ATTR_ROW + reskin.ATTR_ID, 99)
    LEDGER.ok(_attr_refuses(bytes(scrambled), "not 0..50"),
              "an out-of-order id column is REFUSED",
              "the anchor and the shape are two witnesses; disagreement means "
              "one assumption is wrong for this build")
    bad_owner = bytearray(data)
    struct.pack_into("<I", bad_owner, 32 + 2 * reskin.ATTR_ROW + reskin.ATTR_OWNER, 12)
    LEDGER.ok(_attr_refuses(bytes(bad_owner), "owner above"),
              "and an owner above the reserved profession is REFUSED",
              "a reskin's whole premise is that every id stays legal")

    out, log = reskin.attrib_edits(data, rows, renames=[(0, 777)],
                                   owners=[(50, 8)], primaries=[(3, 0), (0, 1)])
    LEDGER.ok(len(out) == len(data),
              "attribute edits are SAME-LENGTH too", f"{len(out)}")
    _, rows2 = reskin.locate_attrib(out)
    LEDGER.ok(rows2[0]["name"] == 777 and rows2[50]["owner"] == 8,
              "a rename lands on +0x08 and an owner change on +0x00",
              f"name {rows2[0]['name']}, owner of 50 = {rows2[50]['owner']}")
    LEDGER.ok(rows2[3]["primary"] == 0 and rows2[0]["primary"] == 1,
              "and the primary marker MOVES -- cleared here, set there",
              "a set-only verb would leave two primaries on one profession, "
              "which is a state the client never ships")
    LEDGER.ok(all(rows2[i]["owner"] == rows[i]["owner"]
                  for i in range(reskin.ATTR_ROWS) if i != 50),
              "and no other row's owner moved",
              "the edit must be surgical; a table-wide rewrite would pass a "
              "spot check and corrupt every other profession")
    refused = None
    try:
        reskin.attrib_edits(data, rows, owners=[(0, 12)])
    except SystemExit as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None and "legal" in refused.lower(),
              "assigning an attribute to an out-of-range profession is REFUSED",
              f"{refused!r}")


def _attr_refuses(data, needle):
    try:
        reskin.locate_attrib(data)
    except SystemExit as ex:
        return needle in str(ex)
    return False


def section_skills():
    print("\n5. the skill roster (two single-byte fields)")
    stride, count = 0xA4, 40
    data = bytearray(b"\x00" * (stride * count))
    for i in range(count):
        data[i * stride + reskin.SKILL_PROF] = 8
        data[i * stride + reskin.SKILL_ATTR] = 32
    out, log = reskin.skill_edits(bytes(data), 0, count, stride,
                                 profs=[(3, 5)], attrs=[(4, 26), (5, 26)])
    LEDGER.ok(len(out) == len(data), "skill edits are same-length",
              f"{len(out)} -- two single-byte fields, so trivially so")
    LEDGER.ok(out[3 * stride + reskin.SKILL_PROF] == 5
              and out[4 * stride + reskin.SKILL_ATTR] == 26
              and out[5 * stride + reskin.SKILL_ATTR] == 26,
              "profession lands on +0x28 and attribute on +0x29",
              "the panel groups by the ATTRIBUTE byte, which is why that is "
              "the field with a countable visible effect")
    moved = {3 * stride + reskin.SKILL_PROF, 4 * stride + reskin.SKILL_ATTR,
             5 * stride + reskin.SKILL_ATTR}
    diff = {i for i, (x, y) in enumerate(zip(data, out)) if x != y}
    LEDGER.ok(diff == moved,
              "and NOTHING else in the table moves",
              f"{len(diff)} byte(s) changed, expected exactly the 3 targeted -- "
              f"a stride error would smear edits across neighbouring rows and "
              f"still look plausible on a spot check")
    for bad, needle in (((0, 5), "not a skill"), ((count, 5), "outside"),
                        ((1, 12), "outside 0..11")):
        sid, val = bad
        try:
            reskin.skill_edits(bytes(data), 0, count, stride, profs=[(sid, val)])
            ok = False
        except SystemExit as ex:
            ok = needle in str(ex)
        LEDGER.ok(ok, f"skill edit ({sid}, {val}) is REFUSED", needle)
    try:
        reskin.skill_edits(bytes(data), 0, count, stride, attrs=[(1, 52)])
        ok = False
    except SystemExit as ex:
        ok = "no-attribute marker" in str(ex)
    LEDGER.ok(ok, "and an attribute above the no-attribute marker is REFUSED",
              "51 is the client's own 'no attribute'; above it is not a value "
              "the client has a row for")

    # ---- the STRING verb (2026-08-14). Unlike the two above it writes a DWORD,
    # so it is the first thing in skill_edits that can disturb a byte outside the
    # field it names. The check that matters is CONTAINMENT: at a 0xA4 stride a
    # four-byte write at a wrong offset lands inside the NEXT skill's row, which
    # reads on screen as a different skill quietly changing its name -- and with
    # 188 rows nobody diffs it.
    import repoint_skill                                          # noqa: E402
    for field in reskin.SKILL_STRING_FIELDS:
        patched, log = reskin.skill_edits(bytes(data), 0, count, stride,
                                          strings=[(2, field, 100364)])
        off = 2 * stride + repoint_skill.FIELDS[field]
        got = struct.unpack_from("<I", patched, off)[0]
        LEDGER.ok(got == 100364, f"skill {field!r} writes the string id at +0x%02X"
                  % repoint_skill.FIELDS[field], f"{got}")
        moved = [i for i in range(len(data)) if data[i] != patched[i]]
        LEDGER.ok(moved and min(moved) >= off and max(moved) < off + 4,
                  f"and every changed byte for {field!r} is inside that dword",
                  f"{len(moved)} byte(s) at {moved[:4]}, field spans "
                  f"[{off}, {off + 4})")
        LEDGER.ok(len(patched) == len(data),
                  f"and the {field!r} edit is same-length", len(patched))
    # The three fields must be DISTINCT offsets, or one verb silently overwrites
    # another and a roster write loses every concise description.
    offs = {f: repoint_skill.FIELDS[f] for f in reskin.SKILL_STRING_FIELDS}
    LEDGER.ok(len(set(offs.values())) == len(offs),
              "the three text fields sit at three distinct offsets", offs)
    # ...and none of them may collide with the two BYTE fields this function
    # already writes, which would make an attribute edit clobber a name.
    LEDGER.ok(all(o >= 4 for o in offs.values())
              and reskin.SKILL_PROF not in range(min(offs.values()), stride)
              or all(o > reskin.SKILL_ATTR for o in offs.values()),
              "and all of them sit past the profession/attribute bytes",
              (reskin.SKILL_PROF, reskin.SKILL_ATTR, sorted(offs.values())))
    # Refusals.
    try:
        reskin.skill_edits(bytes(data), 0, count, stride,
                           strings=[(2, "icon", 1)])
        ok = False
    except SystemExit as ex:
        ok = "not one of" in str(ex)
    LEDGER.ok(ok, "a non-text field name is REFUSED",
              "icons belong to iconset.py; stats are a different experiment")
    try:
        reskin.skill_edits(bytes(data), 0, count, stride,
                           strings=[(2, "name", 1 << 33)])
        ok = False
    except SystemExit as ex:
        ok = "dword" in str(ex)
    LEDGER.ok(ok, "a string id too big for a dword is REFUSED")
    try:
        reskin.skill_edits(bytes(data), 0, count, stride,
                           strings=[(count, "name", 100364)])
        ok = False
    except SystemExit as ex:
        ok = "outside" in str(ex)
    LEDGER.ok(ok, "and a skill id past the table is REFUSED by the same "
                  "_check_skill the other two verbs use")


def section_recipe():
    print("\n6. the recipe file -- a profession design, versioned")
    path = os.path.join(HERE, "recipes", "ritualist-demo.toml")
    if not os.path.isfile(path):
        LEDGER.skip("the recipe section", f"missing {path}")
        return
    (host, names, renames, owners, primaries, descs,
     sprof, sattr, sstr) = reskin.load_recipe(path)
    LEDGER.ok(host == 8,
              "the shipped demo recipe hosts on Ritualist (8)",
              f"host {host} -- the owner's chosen host, and the profession "
              f"whose identity strings all live in ONE archive text file")

    # The DESC verb, added 2026-08-13. `desc` (row+0x0C) was parsed from the
    # first day and never written, and the gap shipped: RESKIN.md 19.7 rendered
    # our authored attribute name above ArenaNet's string 2147, which explains an
    # inherent effect our profession does not have. The check is on EFFECT, not
    # on the flag existing -- `attrib_edits` must move the dword at +0x0C and
    # NOTHING else in the row, because a stride or offset slip here would smear
    # into `primary` at +0x10 and silently give a profession two primaries.
    dsyn = synth_attrib()
    rows_before = reskin.locate_attrib(dsyn)[1]
    target = rows_before[3]
    patched, log = reskin.attrib_edits(dsyn, rows_before, descs=[(target["id"], 4242)])
    rows_after = reskin.locate_attrib(patched)[1]
    after = rows_after[3]
    LEDGER.ok(after["desc"] == 4242,
              "--attr-desc writes the description string id",
              f"row {target['id']}: desc {target['desc']} -> {after['desc']}")
    LEDGER.ok(all(after[k] == target[k] for k in ("owner", "id", "name", "primary")),
              "and moves NOTHING else in the row",
              f"owner/id/name/primary unchanged -- a slip here would land on "
              f"primary at +0x10 and give the profession two primaries")
    LEDGER.ok(len(patched) == len(dsyn)
              and sum(1 for x, y in zip(dsyn, patched) if x != y) <= 4,
              "same length, and at most one dword differs",
              f"{sum(1 for x, y in zip(dsyn, patched) if x != y)} byte(s) -- "
              f"how many a dword write disturbs depends on the VALUES, so the "
              f"invariant is containment rather than a fixed 4")
    LEDGER.ok(set(names) <= set(reskin.TABLES) and "name" in names,
              "its name section maps onto the real tables",
              f"{sorted(names)} -- an unknown key here would be silently "
              f"ignored, so the set is checked against TABLES")
    LEDGER.ok(any(a == 26 for a, _ in owners) and any(a == 26 for a, _ in renames),
              "it claims a spare attribute row AND names it",
              f"owners {owners}, renames {renames} -- claiming without naming "
              f"would show an attribute with the reserved profession's word")
    LEDGER.ok(len(sattr) == 2 and all(t == 26 for _, t in sattr),
              "and moves two skills onto that row, which is section 10's "
              "countable check",
              f"{sattr}")
    everything = [v for _, v in renames] + [v for _, v in owners] + \
                 list(names.values()) + [v for _, v in sattr]
    LEDGER.ok(all(isinstance(v, int) for v in everything),
              "every value in a recipe is a NUMBER",
              "a recipe carries ids only -- no ArenaNet text enters the tree, "
              "and the client resolves each string from the owner's archive")
    for bad, needle in (("[profession]\nname = 1\n", "needs a host"),
                        ("[profession]\nhost = 8\n[[attribute]]\nname = 1\n",
                         "needs an id"),
                        ("[profession]\nhost = 8\n[[skill]]\nattribute = 1\n",
                         "needs an id")):
        tmp = os.path.join(tempfile.gettempdir(), "rurik-bad-recipe.toml")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(bad)
        try:
            reskin.load_recipe(tmp)
            ok = False
        except SystemExit as ex:
            ok = needle in str(ex)
        LEDGER.ok(ok, f"a recipe missing {needle!r} is REFUSED",
                  "a silently-skipped row is a design that half-applies, which "
                  "reads as a client bug rather than a typo")

    # UNKNOWN KEYS in [[skill]] (2026-08-14). They were dropped silently, which
    # is survivable with two skill rows and is not with 188: a typo'd `names =`
    # writes nothing, changes no byte, prints no warning, and the run reports
    # success. `[profession]` has had this check since it shipped -- the check
    # above at "its name section maps onto the real tables" is that one -- and
    # [[skill]] did not, which is the asymmetry the string verb made expensive.
    for bad, needle in (
            ("[profession]\nhost = 8\n[[skill]]\nid = 5\nnames = 100364\n",
             "unknown key"),
            ("[profession]\nhost = 8\n[[skill]]\nid = 5\nName = 100364\n",
             "unknown key")):
        tmp = os.path.join(tempfile.gettempdir(), "rurik-bad-skill.toml")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(bad)
        try:
            reskin.load_recipe(tmp)
            ok = False
        except SystemExit as ex:
            ok = needle in str(ex)
        LEDGER.ok(ok, f"a [[skill]] with an unknown key is REFUSED ({bad.splitlines()[-1]!r})",
                  "with 188 rows nobody reads the diff, so a no-op typo has to "
                  "be loud")
    # POSITIVE CONTROL: the four real keys are still accepted together, or the
    # refusal above just makes the verb unusable.
    good = ("[profession]\nhost = 8\n[[skill]]\nid = 5\nattribute = 26\n"
            "name = 100364\nconcise = 100365\ndesc = 100366\n")
    tmp = os.path.join(tempfile.gettempdir(), "rurik-good-skill.toml")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(good)
    got = reskin.load_recipe(tmp)
    LEDGER.ok(got[7] == [(5, 26)] and sorted(got[8]) == [
        (5, "concise", 100365), (5, "desc", 100366), (5, "name", 100364)],
        "and every real key is parsed -- the positive control",
        f"attrs {got[7]}, strings {sorted(got[8])}")


def main():
    print("Reskin patcher: structural location, edits, and refusals.")
    section_locator()
    section_edits()
    section_output_guards()
    section_real_client()
    section_attributes()
    section_skills()
    section_recipe()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
