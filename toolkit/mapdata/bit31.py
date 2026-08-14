"""Census the bit-31 file ids -- the rows whose replacement the client is waiting for.

WHAT BIT 31 IS, and it is not a spelling. Read out of the client and recorded at
`archive.py`:487: `FcArchive` binds `id | 0x80000000` to a row and DELETES the
plain name when it has requested a replacement (`0x007D7B70`); `DnArchive`
re-links the plain id once the replacement is installed (`0x004766F0`). So a
bit-31 id means *this row's replacement is pending*, and the plain id genuinely
stops resolving until it lands.

WHY IT IS WORTH A TOOL. The population is small, it MOVES, and it moves under
our own content. Two of `content/maps.toml`'s rows are recorded under
`file_id = 0x8001B97D`, and row 7982 -- which every `content/areas.toml` row
borrows from as `donor_row` -- is named by two bit-31 ids. `test_contentids.py`
exists because `vault/run-live/` binds `0x1B97D` PLAINLY, to a different row: a
file id recorded anywhere is archive STATE, not a property of the map
(`studies/maprows/FINDINGS.md` section 8). This is the instrument that says which
state a copy is in.

MEASURED 2026-08-14 across all ten vault copies, and the population is not
constant:

    copies                                          bit-31   pairs     rows
    client/2026-07-29 (pristine), run/main,             29   171,025   177,335
      run/-probe, run/reskin-roster
    dat_study, dat_c2, dat_durability, run/-c2          25   171,025   177,342
    client/2026-04-30                                   25   170,999   177,311
    run-live                                             9   171,138   177,476

    install -> study     4 cleared, over TWO rows each named twice (11957,
                         177254). Neither is a map row.
    install -> run-live  20 cleared, including BOTH of row 7982's ids.

Rows named by more than one bit-31 id: **11** in the install copy, 9 in the
study copy, 2 in run-live -- the difference being exactly the two rows the
install->study transition resolves, each of which was named twice.

THE LOAD-BEARING DESIGN DECISION IS THAT `diff` COMPARES SETS, NOT COUNTS, and
it is not a stylistic preference. A 900 s loopback session on 2026-08-14 reported
"29 -> 29, no change", and that reading is only worth anything because the two
SETS were compared: four ids clearing while four others were newly set is an
equal count and a completely different archive. The count is reported for a
human -- `len(cen["bit31"])`, printed by `format_census` -- and is never what
`changed()` consults.

    python toolkit/mapdata/bit31.py --dat <archive>
    python toolkit/mapdata/bit31.py --dat <archive> --json before.json
    python toolkit/mapdata/bit31.py --dat <archive> --diff before.json

Exit codes follow `datcheck.py`, because the two get run side by side: 0 nothing
changed, 1 the population or a row it names CHANGED (a result, not an error),
2 refused or unreadable. **The direction of error that matters is 2 leaking out
as 1**: a census that could not be taken must never be read as "it changed", so
every refusal is decided BEFORE anything is written and the catch is broad
rather than a list of the exceptions that happened to occur in testing.

Reads the archive 'rb' and nothing else. `--json` refuses the owner's install,
the `dat_study` snapshot and every checkout of this repo -- a census is derived
from the owner's archive, so it belongs in the vault or a scratch directory.
"""

import argparse
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, FILE_ID_HIGH_BIT,        # noqa: E402
                     FILE_ID_TABLE_ROW)
from mapchunks import MAP_HEAD_FLAGS_U16               # noqa: E402
# The worktree walk is imported rather than copied: it is subtle -- a git
# worktree's repo root is NOT the main checkout's, and `mapbuild.py` MEASURED a
# write from a worktree landing in `<main>/toolkit/` -- and it is already
# duplicated in five modules. `_inside` is NOT imported, because importing a
# private name across modules is a coupling that breaks silently; it is four
# lines and is spelled out below, with realpath, which atex's does not do.
from atex import Refused, working_tree_roots, LIVE_INSTALL   # noqa: E402
import vaultpath                                       # noqa: E402

FORMAT_VERSION = 1


def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded, and REALPATH'd.

    The realpath matters on Windows and atex's version does not do it: a
    junction or a symlink pointing into the working tree defeats a pure
    `abspath` compare, and this guard's whole job is to keep derived bytes out
    of version control.
    """
    path = os.path.normcase(os.path.realpath(path))
    root = os.path.normcase(os.path.realpath(root))
    return path == root or path.startswith(root + os.sep)


def resolve_out(path):
    """Where a census may be written. Raises `Refused` otherwise.

    THE ORDER IS LOAD-BEARING and the first version of this function got it
    wrong in the most embarrassing way available: it refused checkouts only, so
    `--json C:\\gw\\Gw.dat` was ALLOWED and `open(out, "w")` would have
    truncated the owner's 4.2 GB archive. That is the identical defect
    `atex.py --make` shipped with, reintroduced in a new module three days
    later, which is the argument for these refusals being a list somebody can
    read rather than a habit.

    `vault/dat_study` and `C:\\gw` are refused BEFORE the vault is allowed,
    because `dat_study` is inside the vault and the allow would swallow it.
    """
    full = os.path.abspath(path)
    parts = os.path.normcase(os.path.realpath(full)).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise Refused(
            f"refusing to write a census to {full}\n"
            f"  vault/dat_study is the SOURCE snapshot every other archive in "
            f"the vault is cut from. Write to a scratch directory instead.")
    if _inside(full, LIVE_INSTALL):
        raise Refused(
            f"refusing to write a census to {full}\n"
            f"  That is the owner's own install at {LIVE_INSTALL}, which is "
            f"read-only to this project, permanently (CLAUDE.md). Writing "
            f"there would TRUNCATE whatever file is named.")
    if os.path.isdir(full):
        raise Refused(f"refusing to write a census to {full}\n"
                      f"  That is a directory. Name the file.")
    # THE VAULT IS THE INTENDED DESTINATION and it normally sits INSIDE the main
    # checkout (`<main>/vault`), gitignored, which is exactly why derived data
    # goes there -- so it is allowed by name before the tree test below.
    #
    # `vaultpath.vault_root()` honours RURIK_VAULT unconditionally, so the one
    # case worth refusing is that variable naming a checkout ROOT, which would
    # turn the whole tree into an allowed destination. A vault that merely lives
    # inside a checkout is the normal configuration and must keep working; a
    # RURIK_VAULT pointed at some other source subdirectory is an operator
    # sabotaging their own environment and is out of scope, which is stated
    # rather than quietly assumed.
    try:
        vault = vaultpath.vault_root()
        if _inside(full, vault) and not any(
                _inside(vault, root) and _inside(root, vault)
                for root in working_tree_roots()):
            return full
    except SystemExit:
        pass                            # no vault resolvable; fall through
    for root in working_tree_roots():
        if _inside(full, root):
            raise Refused(
                f"refusing to write a census to {full}\n"
                f"  That is inside a checkout of this repository ({root}). A "
                f"census is derived from the owner's own archive: it belongs "
                f"under vault/ or in a scratch directory, never in version "
                f"control.")
    return full


def census(path):
    """Every bit-31 file id in one archive, with the row it names.

    Reads the file-id table with its own `struct` walk rather than through
    `archive.file_id_table`, and that is deliberate: `file_id_table` registers a
    bit-31 id under BOTH its raw and its masked form as a convenience for
    finding rows, so it cannot answer "is the masked form separately present?"
    -- the two are indistinguishable once merged. `archive.py`:477 states that
    for none of the 25 is the masked form also present; a census built on that
    function could never refute it.

    Every failure here is a `Refused`, never an escape, because this module's
    one unacceptable answer is exit 1 -- "the population changed" -- on an
    archive it could not read.
    """
    out = {"format_version": FORMAT_VERSION, "archive": os.path.abspath(path),
           "archive_bytes": os.path.getsize(path)}
    with Archive(path) as ar:
        out["row_count"] = ar.row_count
        out["mft_offset"] = ar.mft_offset
        out["block_size"] = ar.block_size
        try:
            blob = ar.read(ar.row(FILE_ID_TABLE_ROW))
        except Exception as exc:                           # noqa: BLE001
            raise Refused(
                f"{path} has no readable file-id table at MFT row "
                f"{FILE_ID_TABLE_ROW}: {type(exc).__name__}: {exc}")
        if len(blob) % 8:
            raise Refused(
                f"the file-id table in {path} is {len(blob)} bytes, which is "
                f"not a whole number of 8-byte (id, row) pairs. Refusing to "
                f"walk it rather than report a census off a misread table.")
        out["file_id_pairs"] = len(blob) // 8

        plain, high = set(), []
        for i in range(len(blob) // 8):
            fid, row = struct.unpack_from("<II", blob, i * 8)
            (high.append((i, fid, row)) if fid & FILE_ID_HIGH_BIT
             else plain.add(fid))

        rows = {}
        for slot, fid, row in high:
            masked = fid & ~FILE_ID_HIGH_BIT
            rec = rows.get(fid)
            if rec is not None:
                # The same id twice in the table. Nothing says it cannot happen
                # and a dict would silently keep one -- record the extra slot so
                # `slots` differs and the diff can see it.
                rec["slots"].append(slot)
                continue
            rec = {"slots": [slot], "masked": masked,
                   "masked_also_binds": masked in plain, "row": row}
            rows[fid] = rec
            try:
                e = ar.row(row)
            except Exception as exc:                       # noqa: BLE001
                # A bit-31 id naming a row this archive does not have is a real
                # possible state and must be reported, not raised: the whole
                # point of the tool is to describe a copy we did not make.
                rec["unresolved"] = f"{type(exc).__name__}: {exc}"
                continue
            if e.offset + e.size > out["archive_bytes"]:
                # A corrupt u32 size would otherwise ask for gigabytes and then
                # be hashed and filed as healthy.
                rec["unresolved"] = (
                    f"extent 0x{e.offset:X}+{e.size} runs past EOF "
                    f"({out['archive_bytes']} bytes)")
                continue
            ar.fh.seek(e.offset)
            stored = ar.fh.read(e.size)
            if len(stored) != e.size:
                rec["unresolved"] = (f"short read: {len(stored)} of {e.size} "
                                     f"bytes at 0x{e.offset:X}")
                continue
            rec.update(offset=e.offset, size=e.size, crc=e.crc, flags=e.flags,
                       compression=e.compression, counter=e.counter,
                       is_map_row=(e.flags == MAP_HEAD_FLAGS_U16),
                       sha256=hashlib.sha256(stored).hexdigest())
        out["bit31"] = {str(f): r for f, r in sorted(rows.items())}
    return out


def aliases(cen):
    """{row: [file ids]} for every row named by MORE THAN ONE bit-31 id.

    ELEVEN rows are named twice in the pristine install and nine in the study
    copy -- the two that stop being is exactly the pair install->study resolves,
    each of which carried two names. `datwrite`'s account of that update calls
    the second of each pair an alias it saw zeroed; grouping them is what makes
    "4 ids cleared" legible as "2 rows resolved".
    """
    by_row = {}
    for fid, rec in cen["bit31"].items():
        by_row.setdefault(rec["row"], []).append(int(fid))
    return {r: sorted(v) for r, v in sorted(by_row.items()) if len(v) > 1}


def map_rows(cen):
    """The bit-31 ids whose row carries the map head flags. Four, on retail."""
    return sorted(int(f) for f, r in cen["bit31"].items() if r.get("is_map_row"))


# Fields of a bit-31 row that a diff reports individually.
#
# `slots` is in here because the file-id table is an array and an id moving
# within it is a rewrite of the table. `counter` is `alloc.nextStream`, the
# sibling link: a relink leaves the payload, the size and the crc untouched, so
# without it a map row's partner being repointed prints "NO CHANGE" -- and
# sibling relink is one of the four shapes FINDINGS 18.5's Tier 1 table names.
# `offset` alone is a ROW RELOCATION, which is what `datmove.py` performs and
# what FINDINGS 4c measured the client doing unprompted.
#
# EVERY key a census record can carry must appear here or in DERIVED below, and
# `test_bit31.py` asserts that union against a live census -- a field added to
# the record and forgotten here is invisible to every diff, which is the defect
# this tuple shipped with (`counter` was censused and never compared).
ROW_FIELDS = ("row", "slots", "offset", "size", "crc", "compression", "flags",
              "counter", "sha256", "masked_also_binds", "unresolved")

# Recorded, but never diffed on purpose: `masked` is a pure function of the id
# (which is the dict key, so it cannot move without the id moving) and
# `is_map_row` is a pure function of `flags`, which IS diffed.
DERIVED = ("masked", "is_map_row")

SCALARS = ("row_count", "mft_offset", "file_id_pairs", "archive_bytes",
           "block_size")


def diff(before, after):
    """Structured changes between two censuses. A list; empty means identical.

    NEVER CONSULTS THE COUNT. `len(bit31)` is a summary, and four ids clearing
    while four others are newly set leaves it unchanged while describing a
    different archive. The sets are compared directly, and the count is derived
    for the report afterwards.
    """
    out = []
    for k in SCALARS:
        if before.get(k) != after.get(k):
            out.append({"kind": "scalar", "field": k,
                        "before": before.get(k), "after": after.get(k)})

    ka = {int(f) for f in before["bit31"]}
    kb = {int(f) for f in after["bit31"]}
    for fid in sorted(ka - kb):
        rec = before["bit31"][str(fid)]
        out.append({"kind": "cleared", "file_id": fid, "row": rec["row"],
                    "masked": rec["masked"],
                    "is_map_row": rec.get("is_map_row")})
    for fid in sorted(kb - ka):
        rec = after["bit31"][str(fid)]
        out.append({"kind": "newly_set", "file_id": fid, "row": rec["row"],
                    "masked": rec["masked"],
                    "is_map_row": rec.get("is_map_row")})
    for fid in sorted(ka & kb):
        ra, rb = before["bit31"][str(fid)], after["bit31"][str(fid)]
        for f in ROW_FIELDS:
            if ra.get(f) != rb.get(f):
                out.append({"kind": "row_field", "file_id": fid, "field": f,
                            "before": ra.get(f), "after": rb.get(f)})
    return out


def changed(before, after):
    """Did anything move? The predicate `--diff`'s exit code is built on."""
    return bool(diff(before, after))


def load_baseline(path):
    """A census read back off disk, or `Refused`.

    Every shape check here is one an exit code depends on: an unvalidated
    baseline reached `diff` and raised `KeyError`, which left the CLI at exit 1
    -- and 1 is this tool's word for "the population CHANGED".
    """
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"could not read {path}: {type(exc).__name__}: {exc}")
    if not isinstance(doc, dict):
        raise Refused(f"{path} is a {type(doc).__name__}, not a census object")
    if doc.get("format_version") != FORMAT_VERSION:
        raise Refused(
            f"{path} is format_version {doc.get('format_version')!r}, this "
            f"tool writes {FORMAT_VERSION}. Re-take the baseline rather than "
            f"compare across formats.")
    if not isinstance(doc.get("bit31"), dict):
        raise Refused(f"{path} has no 'bit31' object; it is not a census")
    for k in SCALARS:
        if k not in doc:
            raise Refused(f"{path} is missing the scalar {k!r}; it is not a "
                          f"complete census")
    for fid, rec in doc["bit31"].items():
        if not isinstance(rec, dict):
            raise Refused(f"{path}: entry {fid!r} is not an object")
        try:
            int(fid)
        except (TypeError, ValueError):
            raise Refused(f"{path}: {fid!r} is not a file id")
    return doc


def format_diff(changes):
    """The operator's page. Every line names the id or the field it is about."""
    if not changes:
        return ["  NO CHANGE: same bit-31 ids, same rows, same bytes"]
    lines = []
    for c in changes:
        if c["kind"] == "scalar":
            lines.append(f"  {c['field']}: {c['before']} -> {c['after']}")
            continue
        # Three states, not two: True, False, and None for a row we could not
        # read. A row that is unreadable must not be reported as "not a map row".
        mark = ("  <-- MAP ROW" if c.get("is_map_row") is True
                else "  (row unreadable)" if c.get("is_map_row") is None
                else "")
        if c["kind"] == "cleared":
            lines.append(f"  CLEARED   {c['file_id']:#010x} (row {c['row']}, "
                         f"plain {c['masked']:#x} should now resolve){mark}")
        elif c["kind"] == "newly_set":
            lines.append(f"  NEWLY SET {c['file_id']:#010x} (row {c['row']}, "
                         f"plain {c['masked']:#x} has stopped resolving){mark}")
        else:
            lines.append(f"  {c['file_id']:#010x} {c['field']}: "
                         f"{c['before']} -> {c['after']}")
    return lines


def format_census(cen):
    al, maps = aliases(cen), map_rows(cen)
    lines = [f"{cen['archive']}",
             f"  {len(cen['bit31'])} bit-31 id(s) of {cen['file_id_pairs']} "
             f"pairs, {cen['row_count']} rows, MFT at 0x{cen['mft_offset']:X}"]
    for fid, r in sorted(cen["bit31"].items(), key=lambda kv: int(kv[0])):
        if "unresolved" in r:
            lines.append(f"  {int(fid):#010x} -> row {r['row']:>7}  "
                         f"UNRESOLVED: {r['unresolved']}")
            continue
        lines.append(
            f"  {int(fid):#010x} -> row {r['row']:>7}  {r['size']:>9} B  "
            f"flags {r['flags']}"
            + ("  <-- MAP ROW" if r["is_map_row"] else "")
            + ("  masked ALSO binds" if r["masked_also_binds"] else ""))
    lines.append(f"  {len(al)} row(s) named by more than one id; "
                 f"{len(maps)} id(s) on map-flagged rows")
    return lines


def _run(args):
    """The body, with every refusal raised as `Refused`. Returns 0 or 1."""
    # EVERY REFUSAL IS DECIDED BEFORE ANYTHING IS WRITTEN. The first version
    # wrote --json and then refused the baseline, so a run that exited 2 had
    # already replaced the file; and `--json X --diff X` clobbered its own
    # baseline and then reported NO CHANGE against what it had just written.
    out = resolve_out(args.json) if args.json else None
    before = load_baseline(args.diff) if args.diff else None
    if out and args.diff and _inside(out, os.path.abspath(args.diff)):
        raise Refused(
            f"--json and --diff name the same file ({out}). Writing the new "
            f"census over the baseline first would compare it against itself "
            f"and always answer NO CHANGE.")

    cen = census(args.dat)
    print("\n".join(format_census(cen)))
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(cen, fh, indent=1)
        print(f"census -> {out}")

    if before is None:
        return 0
    print(f"\nagainst {args.diff}:")
    if before.get("archive") != cen["archive"]:
        # Legitimate -- comparing two copies is how the cross-copy table was
        # measured -- but it must be said, or a cross-copy diff reads as one
        # archive having changed under the operator.
        print(f"  NOTE: different archives. baseline is "
              f"{before.get('archive')!r}")
    print("\n".join(format_diff(diff(before, cen))))
    return 1 if changed(before, cen) else 0


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="the archive to read ('rb')")
    ap.add_argument("--json", metavar="FILE",
                    help="write the census here (never inside a checkout)")
    ap.add_argument("--diff", metavar="BEFORE",
                    help="compare --dat against this census; exits 1 if it "
                         "changed, which is a RESULT and not an error")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2
    except Exception as exc:                               # noqa: BLE001
        # BROAD ON PURPOSE. A narrow list lets struct.error, IndexError and
        # MemoryError escape to the interpreter, which exits 1 -- and 1 is this
        # tool's word for "the population CHANGED". A damaged archive reported
        # as a result is the one failure this module must not have.
        print(f"REFUSED: could not census {args.dat}: "
              f"{type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(_main())
