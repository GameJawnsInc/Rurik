"""Rung E3: make the client compile a map, and find out whether it ever does.

    python toolkit/mapdata/rebloat.py --dat COPY --plan   --file-id 0x287D3
    python toolkit/mapdata/rebloat.py --dat COPY --arm    --file-id 0x287D3 --confirm
    python toolkit/mapdata/rebloat.py --dat COPY --verify --file-id 0x287D3 \
        --baseline vault/research/<arc>/baseline.json

THE QUESTION, and it is the largest open one in the custom-area arc. FINDINGS 34
established what the compiler READS -- terrain and props as hard gates, out of a
converter-local `state` -- entirely by reading x86. What no one has established
is that **the shipped client ever runs the converter at all**. All 349 retail
maps ship with BOTH streams already built, so stage 2 may always be pre-baked by
ArenaNet's own tool with `0x00713630` dead weight in the retail image. If it is
dead weight, rung E3 collapses: authoring a Stripped map buys nothing and the
only route is authoring the Bloated stream directly, which `mapbuild.py` already
does.

**This is the first experiment in the arc that can come back "no", and that is
the point of running it.**

HOW IT PROVOKES THE COMPILER. FINDINGS 17.1 traced the bloat driver's only
load-path caller to a failure branch, and named three triggers, cheapest first:
a **zero-length** stream-1 payload (the loader's `size == 0` branch at
`0x00707749` falls straight through to the re-bloat with no parse attempted), a
stream-1 payload that is not `ffna`/type 3, and a structurally valid payload
with a wrong chunk magic. **The third is REFUTED** -- C2's arm 3b fed the client
a corrupt Bloated chunk and got an access violation, no `Creating default map`
line and no re-bloat attempt (FINDINGS 20.3). So this tool writes the FIRST one,
which is a different failure mode: the corrupt-chunk crash happened during
parsing, and a zero-length payload is never parsed.

WHAT ZEROING A ROW ACTUALLY COSTS, measured here rather than assumed:

  * **It is legal.** MEASURED 2026-08-12 on an archive built by
    `test_datcheck.build_archive`: after `datwrite.Writer.replace(row, b"")` all
    ten of the client's open-time rules still pass and the row reads back as
    0 bytes. So the trigger survives the archive's own gates.
  * **It RELEASES THE ROW'S BLOCKS.** A reservation is `ceil(size/512)*512`
    derived from the size field, so setting the size to 0 reserves nothing and
    the client's MFT-derived coalescing free map is entitled to hand those
    blocks to somebody else (FINDINGS 18.11). **So `verify` must re-resolve the
    file id and must not assume the row**, and the archive must be a copy that
    is thrown away afterwards. `datwrite.replace` journals the whole prior
    reservation, which is what makes `--revert` honest here.

SAFETY. This tool writes. It refuses any path under `C:\\gw` (the owner's
install, permanently read-only to this project) and any path under
`vault/dat_study` (the SOURCE snapshot, never a write target -- every other
archive in the vault is cut from it). `--arm` additionally requires `--confirm`,
because a run that armed the wrong archive is not recoverable by re-reading
this docstring.

WHAT THE OUTCOMES MEAN, decided before the run rather than after:

  REBUILT       the head row holds an `ffna` type-3 map with a Path chunk again.
                The client compiles. E3 lives, and the next question is whether
                the mesh follows terrain WE authored.
  UNCHANGED     still zero length. Either the client never loaded the map, or it
                does not re-bloat -- and those two are told apart by whether
                `Gw.log` shows the map being reached at all, NOT by this tool.
  WRITTEN       something is there but it is not a map. Report it verbatim;
                do not interpret.
  RELOCATED     the file id resolves to a different row than it did. Expected,
                given the released reservation, and NOT a failure by itself.

THE CONTROL THAT MAKES A "REBUILT" WORTH ANYTHING. The baseline records
ArenaNet's own trapezoid and plane counts for the map. A rebuilt mesh that
matches them means the compiler is deterministic and reproduces the shipped
result from the Stripped stream alone; one that differs is just as interesting
and must be reported as a number, not as a pass. Without the baseline, "a Path
chunk exists" is satisfied by the bytes we did not actually delete.

standard library only.
"""

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
import datwrite  # noqa: E402
import mapchunks  # noqa: E402
from mapfile import MapFile  # noqa: E402
from pathchunk import (PathChunk, StrippedPath, PATHING_CHUNK,  # noqa: E402
                       STRIPPED_PATHING_CHUNK)

# The five chunk kinds FINDINGS 34 says the Path builder reads. Their STRIPPED
# ids, because that is the stream the compiler would be handed.
COMPILER_INPUTS = {
    0x10000002: "Terrain (hard gate)",
    0x10000004: "Props (hard gate)",
    0x10000003: "Zones",
    0x1000000E: "Collision",
    0x1000000C: "Map Parameters",
}
# The two whose absence means no Path chunk is produced at all -- 0x00712671 and
# 0x00712678 are unguarded `je`s to `return 0`.
HARD_GATES = (0x10000002, 0x10000004)

FFNA_MAP_TYPE = 3

REBUILT, UNCHANGED, WRITTEN, MISSING = "REBUILT", "UNCHANGED", "WRITTEN", "MISSING"


class Refused(SystemExit):
    """A guard said no. Always names the path and the rule."""


def guard_target(path):
    """Refuse the two archives this project may never write to.

    `datwrite` refuses both too; this repeats them rather than relying on it,
    because the message a person needs is about WHICH archive they pointed at,
    and because refusing early means the plan never runs on a path the write
    would reject.

    *This docstring used to say datwrite refused `C:\\gw` and that this "adds"
    `dat_study`. The second half was false for two days: `datwrite.guard()`
    tested only the live install, and datwrite is the tool that opens the
    archive `r+b`, so the gap sat in front of the only write path in the repo
    while this sentence said it was covered. Closed 2026-08-12 by
    `datwrite.guard_source()`, which is on `Writer.__init__` rather than in
    `guard()` because `revert()` shares `guard()` and reverting is the one
    legitimate write to `dat_study`. `test_datwrite.py` section 0b pins all
    three facts.*
    """
    full = os.path.normcase(os.path.abspath(path))
    parts = full.replace("\\", "/").split("/")
    if full.startswith(os.path.normcase(r"C:\gw")):
        raise Refused(
            f"refusing to write to {path}\n"
            f"  That is the owner's own install and is read-only to this "
            f"project, permanently (CLAUDE.md).")
    if "dat_study" in parts:
        raise Refused(
            f"refusing to write to {path}\n"
            f"  vault/dat_study is the SOURCE snapshot every other copy is cut "
            f"from. Work on a copy: cut one, then point --dat at it.")
    return full


# ------------------------------------------------------------------ baseline

def resolve(ar, file_id):
    """`(head, partner)` MFT entries for a map file id. Raises if either is absent."""
    row = file_id_table(ar).get(file_id)
    if row is None:
        raise Refused(f"no file id 0x{file_id:X} in {ar.path}")
    by_row = {e.index: e for e in ar.entries}
    head = by_row.get(row)
    if head is None:
        raise Refused(f"file id 0x{file_id:X} names row {row}, which is absent")
    partner = by_row.get(mapchunks.next_stream(head))
    if partner is None:
        raise Refused(
            f"row {row} has no Stripped partner via alloc.nextStream. The "
            f"re-bloat reads stream 0, so without one there is nothing to "
            f"compile from and this experiment cannot run on this map.")
    return head, partner


def reservation(ar, entry):
    block = ar.block_size
    return -(-entry.size // block) * block


def describe(ar, entry, want_bloated):
    """What one stream holds. Never raises -- an unreadable stream is a finding."""
    out = {"row": entry.index, "size": entry.size,
           "reservation": reservation(ar, entry), "offset": entry.offset,
           "compression": entry.compression, "crc": entry.crc}
    if entry.size == 0:
        out["state"] = "zero length"
        return out
    try:
        data = ar.read(entry)
    except Exception as exc:                                  # noqa: BLE001
        out["state"] = f"UNREADABLE: {type(exc).__name__}: {exc}"
        return out
    out["sha256"] = hashlib.sha256(bytes(data)).hexdigest()
    out["bytes"] = len(data)
    try:
        mf = MapFile.decode(data)
        out["ffna_type"] = mf.ffna_type
        out["chunk_count"] = len(mf)
    except Exception as exc:                                  # noqa: BLE001
        out["state"] = f"DOES NOT DECODE: {type(exc).__name__}: {exc}"
        return out
    out["chunk_ids"] = ["0x%08X" % cid for cid, _o, _s in ffna_chunks(data)]
    ids = {cid for cid, _o, _s in ffna_chunks(data)}
    if want_bloated:
        out["state"] = "map"
        if PATHING_CHUNK in ids:
            pc = PathChunk.from_map(data)
            out["trapezoids"] = len(pc.trapezoids)
            out["planes"] = len(pc.planes)
            out["boundary_points"] = len(pc.boundary)
            out["path_sequence"] = pc.sequence
        else:
            out["state"] = "map WITHOUT a pathing chunk"
    else:
        out["state"] = "stripped map"
        # What the compiler needs, named per FINDINGS 34.
        out["compiler_inputs"] = {
            name: ("0x%08X" % cid) in out["chunk_ids"]
            for cid, name in COMPILER_INPUTS.items()}
        out["hard_gates_present"] = all(cid in ids for cid in HARD_GATES)
        if STRIPPED_PATHING_CHUNK in ids:
            blob = next(bytes(data[o:o + s]) for c, o, s in ffna_chunks(data)
                        if c == STRIPPED_PATHING_CHUNK)
            sp = StrippedPath.from_chunk(blob)
            out["stripped_path_bytes"] = len(blob)
            out["stripped_boundary_points"] = len(sp.boundary)
            out["stripped_path_sequence"] = sp.sequence
    return out


def baseline(path, file_id):
    """Everything `verify` will need, from a read-only open. Returns a dict."""
    with Archive(path) as ar:
        head, partner = resolve(ar, file_id)
        return {
            "archive": os.path.abspath(path),
            "archive_bytes": os.path.getsize(path),
            "file_id": "0x%X" % file_id,
            "block_size": ar.block_size,
            "entry_count": ar.entry_count,
            "mft_offset": ar.mft_offset,
            "bloated": describe(ar, head, True),
            "stripped": describe(ar, partner, False),
        }


# --------------------------------------------------------------------- plan

def problems_with(base):
    """Why this map cannot answer the question. `[]` means it can.

    Split out from `plan` so the refusals can be tested against a baseline dict
    without building a whole archive -- these are the checks that decide whether
    a run is worth a client launch, and a refusal nobody can exercise is a
    refusal nobody trusts.
    """
    b, s = base["bloated"], base["stripped"]
    problems = []
    if b["size"] == 0:
        problems.append("the Bloated stream is ALREADY zero length -- this "
                        "archive is armed, or a previous run left it so")
    if s["size"] == 0:
        problems.append("the Stripped stream is zero length; there is nothing "
                        "to compile from")
    if not s.get("hard_gates_present", False):
        problems.append("the Stripped stream is missing Terrain or Props, "
                        "which FINDINGS 34 shows are unguarded hard gates -- "
                        "the client would produce no Path chunk even if it "
                        "does run the compiler, so this map cannot answer the "
                        "question")
    if "trapezoids" not in b:
        problems.append("the Bloated stream has no pathing chunk, so there is "
                        "no baseline mesh to compare a rebuild against")
    return problems


def plan(path, file_id):
    """Read-only. Say exactly what arming would do, and refuse if it cannot."""
    base = baseline(path, file_id)
    b, s = base["bloated"], base["stripped"]
    print(f"archive   {base['archive']}")
    print(f"file id   {base['file_id']}")
    print(f"BLOATED   row {b['row']}  {b['size']} B  reservation "
          f"{b['reservation']}  at 0x{b['offset']:X}   [{b['state']}]")
    if "trapezoids" in b:
        print(f"          BASELINE MESH: {b['trapezoids']} trapezoids, "
              f"{b['planes']} plane(s), {b['boundary_points']} boundary pt(s), "
              f"sequence {b['path_sequence']}")
    print(f"STRIPPED  row {s['row']}  {s['size']} B  reservation "
          f"{s['reservation']}  at 0x{s['offset']:X}   [{s['state']}]")
    if "compiler_inputs" in s:
        print("          compiler inputs (FINDINGS 34):")
        for name, present in s["compiler_inputs"].items():
            mark = "yes" if present else "NO"
            print(f"            {name:<22} {mark}")
        print(f"          stripped path chunk: {s.get('stripped_path_bytes')} B, "
              f"{s.get('stripped_boundary_points')} boundary point(s)")

    problems = problems_with(base)
    print()
    if problems:
        print("REFUSED -- this map cannot answer the question:")
        for p in problems:
            print(f"  * {p}")
        return base, problems
    print(f"ARMING WOULD: replace row {b['row']} ({b['size']} B) with a "
          f"ZERO-LENGTH payload,")
    print(f"  zeroing its whole {b['reservation']}-byte reservation, setting "
          f"size 0, compression 0, crc 0,")
    print("  and journalling every byte first so --revert restores it.")
    print()
    print("  NOTE the reservation is DERIVED from the size field, so a "
          "zero-length row reserves")
    print("  nothing and the client's free map may take those blocks. "
          "Re-resolve by file id after")
    print("  the run; do not assume the row. Work on a COPY you can throw "
          "away.")
    return base, []


# ---------------------------------------------------------------------- arm

def arm(path, file_id, journal_path, confirm=False):
    """Write the zero-length Bloated payload. Refuses without `confirm`."""
    guard_target(path)
    base, problems = plan(path, file_id)
    if problems:
        raise Refused("refusing to arm: the plan above found "
                      f"{len(problems)} problem(s)")
    if not confirm:
        raise Refused(
            "\nrefusing to arm without --confirm.\n"
            "  This writes to the archive. Re-run with --confirm once you have "
            "read the plan above and are pointed at a COPY.")
    row = base["bloated"]["row"]
    print(f"\narming: row {row} -> zero length")
    writer = datwrite.Writer(path, journal_path)
    try:
        writer.replace(row, b"")
    finally:
        writer.close()
    print(f"\njournal: {journal_path}")
    print("revert with:  python toolkit/mapdata/datwrite.py --dat "
          f"{path} --revert {journal_path}")
    return base


# ------------------------------------------------------------------- verify

def classify(before, after):
    """What happened to the Bloated stream. One of the four documented outcomes."""
    if after is None:
        return MISSING
    if after["size"] == 0:
        return UNCHANGED
    if after.get("state") == "map" and "trapezoids" in after:
        return REBUILT
    return WRITTEN


def verify(path, file_id, base):
    """Compare the archive now against the baseline. Returns (outcome, report)."""
    now = baseline(path, file_id)
    b0, b1 = base["bloated"], now["bloated"]
    outcome = classify(b0, b1)

    print(f"archive   {now['archive']}")
    print(f"file id   {now['file_id']}")
    print(f"          {base['archive_bytes']} B before, "
          f"{now['archive_bytes']} B now")
    relocated = b1["row"] != b0["row"]
    print(f"BLOATED   row {b0['row']} -> {b1['row']}"
          f"{'   RELOCATED' if relocated else ''}")
    print(f"          {b0['size']} B -> {b1['size']} B   "
          f"[{b0['state']}] -> [{b1['state']}]")

    print(f"\nOUTCOME: {outcome}")
    if outcome == REBUILT:
        print(f"  THE CLIENT COMPILED THE MAP. It wrote {b1['size']} bytes "
              f"holding {b1['chunk_count']} chunks,")
        print(f"  including a pathing chunk with {b1['trapezoids']} "
              f"trapezoids over {b1['planes']} plane(s).")
        want = b0.get("trapezoids")
        if want is not None:
            same = b1["trapezoids"] == want
            print(f"  ArenaNet's own build of this map had {want}. "
                  f"{'IDENTICAL COUNT.' if same else 'DIFFERENT COUNT.'}")
            print("  Note a matching COUNT is not a matching mesh -- compare "
                  "the payloads before claiming")
            print("  the compiler is deterministic.")
        if b1.get("sha256") == b0.get("sha256"):
            print("  AND THE PAYLOAD IS BYTE-IDENTICAL to what was there "
                  "before. Treat that with suspicion:")
            print("  it is also what a failed arm looks like. Check the "
                  "journal actually applied.")
    elif outcome == UNCHANGED:
        print("  The Bloated stream is still zero length. The client did not "
              "write it back.")
        print("  THIS TOOL CANNOT TELL YOU WHY. Two very different things look "
              "identical here:")
        print("    - the client never loaded the map at all")
        print("    - the client loaded it and does not re-bloat")
        print("  `Gw.log` and the gamesrv log are what separate those. Read "
              "them before concluding")
        print("  anything about the compiler.")
    elif outcome == WRITTEN:
        print(f"  Something was written but it is not a decodable map: "
              f"{b1['state']}")
        print("  Report this verbatim rather than interpreting it.")
    else:
        print("  The file id no longer resolves to a readable stream.")
    return outcome, now


# ------------------------------------------------------------------- the CLI

def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="the archive COPY to work on")
    ap.add_argument("--file-id", required=True,
                    help="map file id, e.g. 0x287D3")
    ap.add_argument("--plan", action="store_true",
                    help="read-only: what arming would do")
    ap.add_argument("--arm", action="store_true",
                    help="write the zero-length Bloated payload")
    ap.add_argument("--verify", action="store_true",
                    help="compare against --baseline after a client run")
    ap.add_argument("--baseline", default=None,
                    help="where the baseline JSON is written (--plan/--arm) "
                         "or read from (--verify)")
    ap.add_argument("--journal", default=None,
                    help="journal path for --arm (default: beside --baseline)")
    ap.add_argument("--confirm", action="store_true",
                    help="required by --arm; it writes to the archive")
    args = ap.parse_args(argv)

    file_id = int(args.file_id, 0)
    modes = [args.plan, args.arm, args.verify]
    if sum(bool(m) for m in modes) != 1:
        ap.error("give exactly one of --plan, --arm and --verify")

    if args.verify:
        if not args.baseline or not os.path.isfile(args.baseline):
            ap.error("--verify needs --baseline pointing at the JSON written "
                     "by --plan or --arm")
        with open(args.baseline, "r", encoding="utf-8") as fh:
            base = json.load(fh)
        outcome, _now = verify(args.dat, file_id, base)
        return 0 if outcome in (REBUILT, UNCHANGED, WRITTEN) else 1

    if args.arm:
        journal = args.journal
        if journal is None:
            journal = os.path.join(
                os.path.dirname(os.path.abspath(args.baseline or args.dat)),
                "rebloat_journal.json")
        base = arm(args.dat, file_id, journal, confirm=args.confirm)
    else:
        base, problems = plan(args.dat, file_id)
        if problems:
            return 1

    if args.baseline:
        with open(args.baseline, "w", encoding="utf-8") as fh:
            json.dump(base, fh, indent=2)
            fh.write("\n")
        print(f"\nbaseline: {args.baseline}")
    else:
        print("\n(no --baseline given, so nothing was recorded for --verify "
              "to compare against)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
