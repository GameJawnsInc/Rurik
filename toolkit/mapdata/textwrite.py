#!/usr/bin/env python3
"""Write authored strings into an archive text file.

    python toolkit/mapdata/textwrite.py --dat <archive> --skill-names --plan
    python toolkit/mapdata/textwrite.py --dat <archive> --skill-names --arm \
        --journal names.journal

WHAT THIS IS. `textrec.encode_file` has existed since the text arc and has
exactly ONE caller in this repo -- its own test, with two strings. Every string
this project has put on a retail screen was written by an ad-hoc script that was
never committed, which is why `studies/profession/RESKIN.md` can quote the words
but not the arithmetic. This is that step, committed.

THE DESIGN IS A MERGE, NOT A REBUILD, and that is the whole safety argument.
`encode_file` takes TEXT and re-encodes every record, so rebuilding file 98 from a
table of strings means the 12 records already on screen survive only if that table
is complete and correct -- and it is not: 8 of the 12 are written down in
RESKIN.md and 4 are not recorded anywhere. So `merge` keeps every untouched
record's PAYLOAD BYTES verbatim out of the archive and only encodes the ones being
added. An empty merge is a byte-for-byte identity, which the test asserts, because
a merge that quietly re-encoded everything would look identical until it met a
record whose encoding it could not reproduce.

THE ROW IS RESOLVED, NEVER REMEMBERED. `RESKIN.md` says row 8295 and that is true
of one copy: a file id is archive STATE (`toolkit/contentids.py`,
`studies/maprows/FINDINGS.md` 8), so the row comes from the client's own text
pointer table via `textrec.TextIndex.archive_id`, and the id from that resolved
against the archive being written.

IN PLACE OR RELOCATED. Row 8295 currently holds 7,134 B in a 7,168 B reservation
-- 34 bytes of headroom, 17 characters. So anything past one short name is a
`datmove` relocation rather than a `datwrite --replace`, and the tool says which
before it does either. It never guesses: under the reservation is a replace, over
it is a move, and a move needs a free run the planner has to find.

WRITE GUARDS, each with the reason it exists somewhere in this repo's history:
refuses `C:\\gw` (the owner's install, read-only forever) and `vault/dat_study`
(the reference copy every measurement in `studies/` was taken against).
`datwrite` refuses the first independently; this refuses both before opening
anything, because the point of a guard is that the tool never gets far enough to
be interesting.

PROVENANCE. The strings are ours. Nothing here reads ArenaNet's text, and the
existing records it preserves are ones we wrote.
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

from mapdata import archive as arch                              # noqa: E402
from mapdata import datmove, datwrite                            # noqa: E402
import textrec                                                   # noqa: E402
import vaultpath                                                 # noqa: E402

FILE_INDEX = 98            # the spare file ArenaNet ships as 1,024 EMPTY records
RECORDS_PER_FILE = textrec.RECORDS_PER_FILE

# Records 0-11 are the IDENTITY tier already on screen: profession name and
# abbreviation, five attribute names, five attribute descriptions
# (studies/profession/RESKIN.md 19.5). Skill names start after them, and the
# module refuses to write below this line without --allow-identity, because
# clobbering record 3 renames the profession and nothing would say so.
FIRST_FREE_RECORD = 12

FORBIDDEN = (os.path.normcase(os.path.abspath(r"C:\gw")),)
FORBIDDEN_PARTS = ("dat_study",)


class Refused(SystemExit):
    pass


def guard(path):
    p = os.path.normcase(os.path.abspath(path))
    for root in FORBIDDEN:
        if p == root or p.startswith(root + os.sep):
            raise Refused("Refusing to write inside the owner's install: %s" % path)
    parts = p.replace("\\", "/").split("/")
    for bad in FORBIDDEN_PARTS:
        if bad in parts:
            raise Refused(
                "Refusing to write %s: that is the reference copy every "
                "measurement in studies/ was taken against. Write a run-dir "
                "copy instead." % path)
    return p


def merge(blob, strings, allow_identity=False):
    """A new file-98 payload: `blob`'s records, with `strings` written over them.

    `strings` maps RECORD INDEX -> text. Every record not named keeps its existing
    bytes exactly -- header and payload -- so this is an identity when `strings`
    is empty. Returns the new blob.
    """
    recs, tail, tiled = textrec.walk(blob)
    if not tiled or len(recs) != RECORDS_PER_FILE:
        raise ValueError(
            "refusing to merge into a file that does not tile: %d records, "
            "tiled=%s. Our own TextIndex would reject the result before the "
            "client ever saw it." % (len(recs), tiled))
    for idx in strings:
        if not 0 <= idx < RECORDS_PER_FILE:
            raise ValueError("record index %d outside 0..%d"
                             % (idx, RECORDS_PER_FILE - 1))
        if idx < FIRST_FREE_RECORD and not allow_identity:
            raise ValueError(
                "record %d is the IDENTITY tier (profession name, abbreviation, "
                "attribute names and descriptions -- RESKIN.md 19.5). Writing it "
                "renames something already on screen. Pass --allow-identity if "
                "that is the intent." % idx)
    out = []
    for i, (bits, base, payload) in enumerate(recs):
        if i in strings:
            out.append(textrec.encode_record(strings[i]))
        else:
            # VERBATIM -- the record's own payload, base and bits, not a decode
            # and re-encode. See the module docstring: 4 of the 12 records
            # already on screen are written down nowhere, so re-deriving them
            # from text is a way to lose them silently.
            out.append(textrec.encode_record(payload=payload, base=base,
                                             bits=bits))
    return b"".join(out) + tail


def resolve_row(exe, dat, file_index=FILE_INDEX):
    """(file id, MFT row, current payload) for one text file, resolved."""
    with textrec.TextIndex(exe, dat) as ti:
        fid = ti.archive_id(file_index)
        row = ti.file_ids.get(fid)
        if row is None:
            raise Refused(
                "text file %d resolves to file id 0x%X, which this archive does "
                "not bind. A file id is archive STATE -- the client and the "
                "server must be reading the same copy (contentids.py)."
                % (file_index, fid))
        blob = ti.archive.read(ti._rows[row])
    return fid, row, blob


def plan(dat, exe, strings, allow_identity=False):
    """What writing `strings` would do. Opens nothing for writing."""
    fid, row, blob = resolve_row(exe, dat)
    new = merge(blob, strings, allow_identity)
    a = arch.Archive(dat)
    try:
        entry = a.row(row)          # .row(), NEVER entries[row]
        have = entry.size
        reserved = (have + 511) // 512 * 512
        need = len(new)
        move = need > reserved
        placement, refusal = None, None
        if move:
            # plan_move RAISES rather than returning None -- including for "it
            # fits where it is", which cannot happen on this branch but would be
            # reported as a placement failure if it did.
            try:
                placement = datmove.plan_move(a, row, need)
            except datmove.Refused as exc:
                refusal = str(exc)
    finally:
        a.close()
    return {"file_id": fid, "row": row, "old": len(blob), "stored": have,
            "reserved": reserved, "new": need, "relocate": move,
            "placement": placement, "refusal": refusal, "blob": new}


def name_assignment(profession=8, exe=None, dat=None, first=FIRST_FREE_RECORD):
    """[(skill id, record index, name)], in skill-id order.

    THE ONE PLACE THE TWO HALVES OF THIS RUNG AGREE. The archive gets a string
    at a record; the client gets that record's string ID in the skill's row+0x98.
    Nothing joins them at run time -- the client just reads whatever number is in
    the row -- so if the two sides disagree about which record holds which skill's
    name, every skill on the bar is labelled with some other skill's name and
    nothing anywhere reports it. `--emit-recipe` and `skill_name_strings` are
    both views of THIS list rather than two walks that happen to sort the same
    way, which is what `iconset.armable` had to be extracted for one module over.
    """
    sys.path.insert(0, HERE)
    import iconset                                               # noqa: E402
    import skillnames                                            # noqa: E402
    mapping = iconset.skill_glyphs(profession, exe, dat)
    named = skillnames.assign(mapping)
    return [(sid, first + n, named[sid]) for n, sid in enumerate(sorted(named))]


def skill_name_strings(profession=8, exe=None, dat=None, first=FIRST_FREE_RECORD):
    """{record index: name} -- the archive side of `name_assignment`."""
    return {rec: nm for _sid, rec, nm in
            name_assignment(profession, exe, dat, first)}


def emit_recipe(rows, profession=8):
    """The `[[skill]]` fragment `reskin.py` needs -- the client side.

    Emitted rather than hand-written because it is 188 rows of pure arithmetic,
    and emitted as NUMBERS ONLY: the name is a comment for a human reading the
    diff, and the recipe carries no text into the tree. The provenance gate's
    "commit the id, resolve the string at run time" pattern, one more time.
    """
    out = ["# GENERATED by textwrite.py --emit-recipe. Do not hand-edit.",
           "#",
           "# %d skill name ids for profession %d, records %d..%d of text file"
           % (len(rows), profession, rows[0][1], rows[-1][1]),
           "# %d. The names are comments; every VALUE here is a number."
           % FILE_INDEX,
           "# The record order is skill id ascending and is defined once, in",
           "# textwrite.name_assignment -- nothing joins these at run time, so a",
           "# disagreement labels every skill with another skill's name silently.",
           "#",
           "# It carries its own [profession] host because every recipe must:",
           "# reskin.py refuses one without a host, and it cannot re-patch its",
           "# own output (RESKIN.md 19.6), so this layers alongside the design",
           "# recipe in ONE run rather than in a second pass.",
           "",
           "[profession]",
           "host = %d" % profession,
           ""]
    for sid, rec, nm in rows:
        out.append("[[skill]]")
        out.append("id   = %d" % sid)
        out.append("name = %d    # record %d -- %s" % (string_id(rec), rec, nm))
        out.append("")
    return "\n".join(out)


def string_id(record):
    """Record index -> string id. id = file_index * 1024 + record."""
    return FILE_INDEX * RECORDS_PER_FILE + record


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="Archive to write. A run copy.")
    ap.add_argument("--exe", default=None,
                    help="Client whose pointer table resolves the text file's id.")
    ap.add_argument("--skill-names", action="store_true",
                    help="Source the strings from skillnames.py.")
    ap.add_argument("--profession", type=int, default=8)
    ap.add_argument("--plan", action="store_true",
                    help="Report what would be written and exit. Writes nothing.")
    ap.add_argument("--arm", action="store_true", help="Actually write.")
    ap.add_argument("--journal", default=None, help="Journal path. Needs --arm.")
    ap.add_argument("--allow-identity", action="store_true",
                    help="Permit writing records 0..%d." % (FIRST_FREE_RECORD - 1))
    ap.add_argument("--emit-recipe", metavar="PATH",
                    help="Write the matching [[skill]] fragment for reskin.py "
                         "and exit. The client half of the same assignment.")
    a = ap.parse_args()

    if a.emit_recipe:
        exe = a.exe or str(vaultpath.vault_path("run", "reskin-roster", "Gw.exe"))
        rows = name_assignment(a.profession, exe, a.dat)
        text = emit_recipe(rows, a.profession)
        # The fragment is NUMBERS, so it may live in the tree -- but it is still
        # a generated file and must not be written over a hand-authored recipe.
        if os.path.exists(a.emit_recipe):
            with open(a.emit_recipe, encoding="utf-8") as f:
                if "GENERATED by textwrite.py" not in f.read(200):
                    raise Refused(
                        "%s exists and is not a generated fragment. Refusing to "
                        "overwrite a hand-authored recipe with 188 rows of "
                        "arithmetic." % a.emit_recipe)
        with open(a.emit_recipe, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %d [[skill]] row(s) to %s" % (len(rows), a.emit_recipe))
        print("string ids %d..%d, records %d..%d"
              % (string_id(rows[0][1]), string_id(rows[-1][1]),
                 rows[0][1], rows[-1][1]))
        return 0

    if not (a.plan or a.arm):
        raise SystemExit("pass --plan or --arm")
    if a.arm and not a.journal:
        raise SystemExit("--arm needs --journal: an unjournalled text write is "
                         "not revertible, and the client moves the MFT")
    if not a.skill_names:
        raise SystemExit("nothing to write: pass --skill-names")
    guard(a.dat)
    if not os.path.exists(a.dat):
        raise SystemExit("not found: %s" % a.dat)
    exe = a.exe or str(vaultpath.vault_path("run", "reskin-roster", "Gw.exe"))

    strings = skill_name_strings(a.profession, exe, a.dat)
    p = plan(a.dat, exe, strings, a.allow_identity)

    print("text file %d -> file id 0x%X -> MFT row %d"
          % (FILE_INDEX, p["file_id"], p["row"]))
    print("records to write: %d  (%d..%d -> string ids %d..%d)"
          % (len(strings), min(strings), max(strings),
             string_id(min(strings)), string_id(max(strings))))
    print("payload: %d B -> %d B   stored %d B in a %d B reservation"
          % (p["old"], p["new"], p["stored"], p["reserved"]))
    if p["relocate"]:
        if p["placement"] is None:
            print("\nREFUSING: %d B does not fit the reservation and datmove "
                  "will not place it: %s" % (p["new"], p["refusal"]))
            return 2
        print("RELOCATION: %d B is past the %d B reservation." % (p["new"], p["reserved"]))
        p["placement"].show()
    else:
        print("IN PLACE: fits the existing reservation, datwrite --replace")

    sample = sorted(strings)[:3]
    for r in sample:
        print("   record %d = id %d = %r" % (r, string_id(r), strings[r]))

    if a.plan:
        print("\n--plan: nothing written.")
        return 0

    if p["relocate"]:
        n = datmove.move(a.dat, p["row"], p["blob"], a.journal)
        print("\nrelocated: %s" % (n,))
    else:
        w = datwrite.Writer(a.dat, a.journal)
        try:
            w.replace(p["row"], p["blob"])
        finally:
            w.close()
    print("journal: %s" % a.journal)
    print("REVERT BEFORE YOU LAUNCH ANYTHING ELSE -- the client moves the MFT "
          "and a journal expires the moment it does (crossbuild FINDINGS 4c).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
