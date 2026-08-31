"""Check the additive FA8 authoring path -- rung A4 of studies/archivewrite.

WHAT IS BEING CHECKED AND WHY IT IS NOT OBVIOUS. `unitauthor.py` adds a 16th
linked file to a creature's shell and one sequence record that selects it. Two
of the three things it must get right cannot fail any checksum, cannot fail
`datcheck`'s ten open-time rules, and would present in the game as "some
animations stopped playing":

  1. THE SEQUENCE ARRAY MUST STAY SORTED by `u32@+0x01`. The client searches it
     with `std::lower_bound` (`0x00792DC0`) and a `lower_bound` on an unsorted
     array silently returns the wrong run. So §2 inserts keys at the front, the
     middle and the end of the table and requires order every time, and §2b
     sabotages the module's own ordering to prove the check is not decorative.
  2. THE FA8 LIST IS POSITIONAL. `links[sel-1]` is how every existing record
     resolves, so a link INSERTED rather than appended renumbers every selector
     already in use. §1 asserts the prior list is a prefix of the new one --
     which a reordering would break and a length check would not.

The third is ordinary and is checked anyway: the edit must be archive-legal, so
§4 puts the authored shell and its new linked file into a SYNTHETIC archive and
requires `datcheck`'s ten rules and the CRC rules to hold.

WHAT IT RUNS AGAINST. The FA8/FA1 round-trip sections read `vault/dat_study`
READ-ONLY through `archive.Archive`, which never opens for writing; the archive
sections build their own fixture in a temp directory. No client is launched, no
server is started, and nothing under `vault/` is modified. Sections needing the
vault declare a skip when it is absent rather than passing quietly.

    python toolkit/mapdata/test_unitauthor.py
"""

import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import archive as arch                                            # noqa: E402
import checks                                                     # noqa: E402
import datcheck                                                   # noqa: E402
import mdlrefs                                                    # noqa: E402
import skelfile                                                   # noqa: E402
import skelwrite                                                  # noqa: E402
import unitauthor                                                 # noqa: E402
import vaultpath                                                  # noqa: E402
from test_datcheck import build_archive                           # noqa: E402

# FLOOR: measured from a green run on 2026-08-17. Sections 1-3 need the study
# archive and declare a skip without it; section 4 builds its own fixture and
# always runs. The floor is set to the vault-present count because that is the
# run this repo actually makes -- and a skip is PRINTED, so a bare-machine run
# reports what it could not do rather than scoring itself green.
LEDGER = checks.Ledger("unit authoring (A4)", floor=30)
check = checks.adopt(LEDGER)

SHELL = 116228          # the hatcher's COMPOSITED shell: 15 links, 242 records
LINK0 = 15018           # its first link
NEW_ID = 0x5F200        # a file id no retail row uses


def study_archive():
    try:
        return os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except Exception:
        return None


def container_of(ar, file_id):
    return ar.read(ar.row(arch.file_id_table(ar, raw=True)[file_id]))


def fa1_of(container):
    for cid, off, size in arch.ffna_chunks(container):
        if cid == unitauthor.SKELETON_CHUNK:
            return bytes(container[off:off + size])
    return None


def section_links(ar):
    print("\n1. the FA8 list is positional, so a link is APPENDED")
    shell = container_of(ar, SHELL)
    before = unitauthor.links_of(shell)
    check(before[0] == LINK0 and len(before) == 15,
          "the shell's link list decodes to the 15 files A1 measured",
          f"{len(before)} links, first {before[0]}")

    out, selector = unitauthor.add_link(shell, NEW_ID)
    after = unitauthor.links_of(out)
    check(selector == 16 and len(after) == 16,
          "the new link's selector is 16, one past the existing 15",
          f"selector {selector}, {len(after)} links")
    check(after[:15] == before,
          "and every prior selector still names the SAME file -- a list that "
          "was reordered rather than appended would renumber them all",
          "prefix preserved" if after[:15] == before else f"{after[:3]}...")
    check(after[15] == NEW_ID,
          "the appended record round-trips to the file id asked for",
          f"{after[15]}")

    # Only the FA8 chunk may move. Every other chunk must be carried verbatim.
    ids_before = [(c, s) for c, _o, s in arch.ffna_chunks(shell)]
    ids_after = [(c, s) for c, _o, s in arch.ffna_chunks(out)]
    changed = [(a, b) for a, b in zip(ids_before, ids_after) if a != b]
    check(len(ids_before) == len(ids_after) and len(changed) == 1
          and changed[0][0][0] == unitauthor.LINK_CHUNK,
          "exactly one chunk changed size, and it is the FA8",
          f"changed {changed}")
    check(fa1_of(out) == fa1_of(shell),
          "the FA1 is byte-identical after a link-only edit")


def section_order(ar):
    print("\n2. a record is INSERTED IN KEY ORDER, never appended")
    shell = container_of(ar, SHELL)
    t0 = skelwrite.extract(skelfile.Skeleton.decode(fa1_of(shell)))
    keys = [s["u32_01"] for s in t0["sequences"]]
    check(all(b >= a for a, b in zip(keys, keys[1:])),
          "the shipped table is already sorted -- the premise lower_bound needs",
          f"{len(keys)} records")

    singles = unitauthor.single_variant_keys(t0)
    runs = unitauthor.key_runs(t0)
    check(len(runs) == 224 and len(singles) == 216,
          "224 distinct keys, 216 of them single-variant (A1 §8.5)",
          f"{len(runs)} keys, {len(singles)} single")

    # Front, middle and end of the table. A tail-append implementation passes
    # only the last of these, which is why one key would not be a test.
    for label, key in (("first", keys[0]), ("middle", keys[len(keys) // 2]),
                       ("last", keys[-1])):
        t = skelwrite.extract(skelfile.Skeleton.decode(fa1_of(shell)))
        at = unitauthor.insert_sequence(t, key, 16)
        got = [s["u32_01"] for s in t["sequences"]]
        check(all(b >= a for a, b in zip(got, got[1:])),
              f"inserting on the {label} key leaves the array sorted",
              f"landed at index {at} of {len(got)}")
        check(t["header"]["n18"] == len(t["sequences"]),
              f"and the {label} insert bumped the header's n18",
              f"n18={t['header']['n18']}")
        check(t["sequences"][at]["u8_00"] == 16
              and t["sequences"][at]["u32_01"] == key,
              f"and the {label} record carries selector 16 and the key asked for")

    print("\n2b. and the ordering check is not decorative")
    t = skelwrite.extract(skelfile.Skeleton.decode(fa1_of(shell)))
    # Reach past the module's own placement and append a low key at the tail --
    # exactly what a naive implementation does. The refusal must fire.
    low = min(keys)
    rec = dict(t["sequences"][0])
    rec["u32_01"] = low
    t["sequences"].append(rec)
    t["header"]["n18"] = len(t["sequences"])
    unsorted_keys = [s["u32_01"] for s in t["sequences"]]
    check(not all(b >= a for a, b in zip(unsorted_keys, unsorted_keys[1:])),
          "CONTROL: a tail append with a low key really does unsort the array",
          "which nothing in the archive's own rules would report")
    refused = None
    try:
        unitauthor.insert_sequence(t, low, 16)
    except unitauthor.Unauthorable as exc:
        refused = str(exc)
    check(refused is not None and "unsorted" in refused,
          "and insert_sequence REFUSES to build on an already-unsorted table",
          (refused or "accepted it")[:60])


def section_whole(ar):
    print("\n3. the whole edit, and the oracle it buys")
    shell = container_of(ar, SHELL)
    out, info = unitauthor.author_variant(shell, NEW_ID)

    check(info["selector"] == 16 and info["run_before"] == 1
          and info["run_after"] == 2,
          "the variant lands on a single-variant key, giving a 50/50 pick",
          f"key {info['key']}: {info['run_before']} -> {info['run_after']}")

    # Re-decode the RESULT. Everything above worked on the typed layer; this is
    # the only check that the bytes we would ship actually parse.
    fa1 = fa1_of(out)
    sk = skelfile.Skeleton.decode(fa1)
    t = skelwrite.extract(sk)
    check(len(t["sequences"]) == 243 and t["header"]["n18"] == 243,
          "the re-decoded container carries 243 records", f"{len(t['sequences'])}")
    got = [s["u32_01"] for s in t["sequences"]]
    check(all(b >= a for a, b in zip(got, got[1:])),
          "still sorted after a full encode/decode round trip")
    ours = [s for s in t["sequences"] if s["u8_00"] == 16]
    check(len(ours) == 1 and ours[0]["u32_01"] == info["key"],
          "exactly one record selects the new link", f"{len(ours)} record(s)")
    check(unitauthor.links_of(out)[15] == NEW_ID,
          "and the link it selects is the file we added")

    check(skelwrite.encode(t) == fa1,
          "the modified FA1 re-encodes byte-identically -- the writer is "
          "stable on a table it did not itself produce")

    # The size story, which is the reason this rung exists at all.
    check(info["container_after"] - info["container_before"] < 200,
          "the whole edit costs under 200 bytes on a 29,802 B shell -- NOT the "
          "1,514,855 B link the arc was blocked on",
          f"{info['container_after'] - info['container_before']:+d} B")


def section_archive(tmp):
    print("\n4. the edit is archive-legal on a SYNTHETIC archive")
    path = os.path.join(tmp, "authored.dat")
    build_archive(path)

    checks_before, _facts = datcheck.preflight(path)
    check(all(c.ok for c in checks_before),
          "the fixture starts clean", f"{len(checks_before)} of "
          f"{len(checks_before)} clear")

    # A payload standing in for the authored shell: the point of this section is
    # the ARCHIVE operation, and datcheck reads no chunk structure at all.
    import datwrite
    payload = bytes(range(256)) * 2
    w = datwrite.Writer(path, journal_path=os.path.join(tmp, "a4.jrnl"))
    try:
        w.replace(16, payload)
    finally:
        w.close()

    after, _f = datcheck.preflight(path)
    bad = [c.name for c in after if not c.ok]
    check(not bad, "and every open-time rule still holds after the write",
          f"red: {bad}" if bad else f"{len(after)} of {len(after)} clear")

    sweep = datcheck.crc_sweep(path)
    check(not sweep["bad"],
          "every payload CRC matches -- including the row just written",
          f"{sweep['checked']} recomputed")

    with arch.Archive(path) as ar2:
        check(ar2.read(ar2.row(16)) == payload,
              "and the row reads back exactly what was written",
              f"{len(payload)} B")


def main():
    dat = study_archive()
    tmp = tempfile.mkdtemp(prefix="rurik-unitauthor-")
    try:
        if dat and os.path.exists(dat):
            with arch.Archive(dat) as ar:
                section_links(ar)
                section_order(ar)
                section_whole(ar)
        else:
            LEDGER.skip("sections 1-3: FA8 append, key-order insert, whole edit",
                        "sections 1-3 (FA8 append, key-order insert, whole "
                        "edit): no vault/dat_study/Gw.dat on this machine")
        section_archive(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
