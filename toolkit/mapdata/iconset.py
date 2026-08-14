r"""Arm every icon row of one profession with icons we drew.

    python toolkit/mapdata/iconset.py --dat <archive> --plan
    python toolkit/mapdata/iconset.py --dat <archive> --arm --journal icons.journal

WHAT THIS IS. `glyphs.py` draws 132 pictures; `atex.py` wraps one in a container;
`datwrite.py` puts one in a row. This is the thing that does it 132 times against
the rows a profession's skills ACTUALLY point at, which is a join across two very
different sources -- the client's `s_skill` table in the executable, and the
archive's file-id table -- and getting that join wrong is how you overwrite
someone else's art.

WHY IT PLANS BEFORE IT WRITES. Every refusal below is a thing that has already
gone wrong somewhere in this project:

  * A row whose reservation is too small is a RELOCATION, not a replacement, and
    `datwrite` refuses it -- but it refuses it on row 87 of 132, after 86 rows
    are already written. So the whole plan is checked first and nothing is
    written unless all of it fits.
  * A file id is ARCHIVE STATE, not a property of the skill (`contentids.py`).
    The same icon is a different row in a different copy, so the ids are resolved
    against the archive being armed and never against a remembered table.
  * `Archive.entries` is POSITIONAL and `file_id_table` returns ROW NUMBERS.
    Indexing `entries[row]` reads the row BEFORE the one you named. That cost
    two arms written into the wrong rows on 2026-08-14; this uses `.row()`.
  * Some icons are SHARED with another profession's skills -- 7 of profession
    8's 132. Overwriting those changes a bar we were not asked to touch, so they
    are reported and skipped unless `--allow-shared` says otherwise.

WRITE GUARDS. Refuses `C:\gw` (the owner's install, read-only forever) and
`vault/dat_study` (the reference copy every measurement in `studies/` was taken
against). `datwrite` refuses the first independently; this refuses both before
opening anything, because the point of a guard is that the tool never gets far
enough to be interesting.

PROVENANCE: the pictures are arithmetic. Nothing here reads an ArenaNet asset.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))

from mapdata import archive as arch                              # noqa: E402
from mapdata import atex, datwrite, dxt1, glyphs                 # noqa: E402
import repoint_skill                                             # noqa: E402
from gwpe import PE                                              # noqa: E402

BLOCK = 512
ICON_FIELD = 0x90          # the field the SKILLBAR draws; +0x8c is the 64x64 DXTL
SKILL_PROF = 0x28
DEFAULT_EXE = r"C:\gd\Rurik\vault\run\reskin-roster\Gw.exe"
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
                "measurement in studies/ was taken against. Arm a run-dir "
                "copy instead." % path)
    return p


def reservation(n):
    return (n + BLOCK - 1) // BLOCK * BLOCK


def roster(pe, profession):
    """Distinct `+0x90` icon ids for one profession, and who else uses each."""
    table, count, _section = repoint_skill.find_table(pe)
    icon_of, prof_of = {}, {}
    for sid in range(count):
        prof_of[sid] = pe.data[table + sid * repoint_skill.REC + SKILL_PROF]
        icon_of[sid] = repoint_skill.row_values(pe.data, table, sid)["icon2"]
    users = {}
    for sid in range(count):
        users.setdefault(icon_of[sid], set()).add(prof_of[sid])
    mine = sorted({icon_of[s] for s in range(count) if prof_of[s] == profession})
    skills = sum(1 for s in range(count) if prof_of[s] == profession)
    return mine, users, skills


def plan(dat, exe, profession, allow_shared):
    pe = PE(exe)
    mine, users, skills = roster(pe, profession)
    a = arch.Archive(dat)
    try:
        ids = arch.file_id_table(a)
        rows, skipped, toosmall = [], [], []
        for k, fid in enumerate(mine):
            row = ids.get(fid)
            if row is None:
                skipped.append((fid, None, "unresolved in this archive"))
                continue
            shared = users[fid] - {profession}
            if shared and not allow_shared:
                skipped.append((fid, row, "shared with profession(s) %s"
                                % sorted(shared)))
                continue
            # .row(), NEVER entries[row] -- see the module docstring.
            have = reservation(a.row(row).size)
            rows.append((fid, row, have))
        need = reservation(12 + 8 + (64 // 4) * (64 // 4) * 8)
        toosmall = [(f, r, h) for f, r, h in rows if h < need]
    finally:
        a.close()
    return mine, skills, rows, skipped, toosmall, need


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="Archive to arm. A run-dir copy.")
    ap.add_argument("--exe", default=DEFAULT_EXE,
                    help="Client whose s_skill table names the icon ids.")
    ap.add_argument("--profession", type=int, default=8)
    ap.add_argument("--plan", action="store_true",
                    help="Report what would be written and exit. Writes nothing.")
    ap.add_argument("--arm", action="store_true", help="Actually write.")
    ap.add_argument("--journal", default=None,
                    help="Journal path. Required with --arm.")
    ap.add_argument("--allow-shared", action="store_true",
                    help="Also overwrite icons another profession's skills use.")
    ap.add_argument("--dim", type=int, default=64,
                    help="Texture size. 64 fits every row in place; 128 does not.")
    a = ap.parse_args()

    if not (a.plan or a.arm):
        raise SystemExit("pass --plan or --arm")
    if a.arm and not a.journal:
        raise SystemExit("--arm needs --journal: an unjournalled 132-row write "
                         "is not revertible, and the client moves the MFT")
    guard(a.dat)
    if not os.path.exists(a.dat):
        raise SystemExit("not found: %s" % a.dat)

    mine, skills, rows, skipped, toosmall, need = plan(
        a.dat, a.exe, a.profession, a.allow_shared)

    print("profession %d: %d skills, %d distinct +0x%02X icons"
          % (a.profession, skills, len(mine), ICON_FIELD))
    print("armable rows: %d   skipped: %d" % (len(rows), len(skipped)))
    for fid, row, why in skipped[:10]:
        print("  skip id %d%s -- %s"
              % (fid, "" if row is None else " row %d" % row, why))
    if len(skipped) > 10:
        print("  ... and %d more" % (len(skipped) - 10))
    if toosmall:
        print("\nREFUSING: %d row(s) reserve less than the %d B a %dx%d icon "
              "needs. That is a relocation, not a replacement."
              % (len(toosmall), need, a.dim, a.dim))
        for fid, row, have in toosmall[:6]:
            print("  id %d row %d reserves %d" % (fid, row, have))
        return 2
    print("every armable row reserves at least the %d B needed" % need)

    if a.plan:
        print("\n--plan: nothing written.")
        return 0

    print("\ndrawing %d icons and writing them..." % len(rows))
    w = datwrite.Writer(a.dat, a.journal)
    try:
        for k, (fid, row, _have) in enumerate(rows):
            rgb = glyphs.icon(k % glyphs.COUNT, a.dim)
            blob = atex.build_image(rgb, a.dim, a.dim, levels=1,
                                    layout=dxt1.PLANAR)
            w.replace(row, blob)
            if k % 20 == 0 or k == len(rows) - 1:
                print("  %3d/%d  id %d -> row %d  (%d B)"
                      % (k + 1, len(rows), fid, row, len(blob)))
    finally:
        w.close()
    print("\njournal: %s" % a.journal)
    print("REVERT BEFORE YOU LAUNCH ANYTHING ELSE -- the client moves the MFT "
          "and a journal expires the moment it does (crossbuild FINDINGS 4c).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
