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

LEDGER = checks.Ledger("reskin", floor=24)


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


def main():
    print("Reskin patcher: structural location, edits, and refusals.")
    section_locator()
    section_edits()
    section_output_guards()
    section_real_client()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
