"""The E3 driver: its guards, its refusals, and the arm/revert cycle.

    python toolkit/mapdata/test_rebloat.py

`rebloat.py` is the only tool in this project that deliberately DESTROYS a
payload -- it zeroes a map's Bloated stream so the client is forced down the
re-bloat path -- so almost everything worth testing here is a refusal.

WHAT THIS FILE IS FOR, and it is not the happy path. The experiment itself
cannot be tested without a client; what CAN be tested offline is everything that
stops the experiment being run against the wrong archive, on a map that cannot
answer the question, or in a state that cannot be undone. Those are the parts
that would cost a 4 GB re-extraction or a wasted client session.

THE ARM/REVERT CYCLE IS THE ONE POSITIVE CLAIM. Section 3 zeroes a row in an
archive this file builds and requires `datwrite --revert` to put it back
BYTE-IDENTICALLY, including the whole reservation -- because a zero-length
replace sets the size field to 0, and a reservation is `ceil(size/512)*512`, so
the row's blocks are released to the client's free map. That is the hazard
FINDINGS 18.11 names, and a revert that restored only the payload would look
like a success and leave the archive wrong.

SECTIONS 0-3 NEED NO VAULT. Section 4 reads `vault/dat_study/Gw.dat` READ-ONLY
and pins the two maps the harness can actually reach; without it the run scores
short and goes red, because every refusal above is ours against ours and only
the archive can say the plan describes a real map.
"""

import hashlib
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
import datcheck  # noqa: E402
import datwrite  # noqa: E402
import rebloat  # noqa: E402
from test_datcheck import build_archive  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# The two maps `content/maps.toml` can send the client to, pinned by FILE ID --
# ids travel between copies of the archive, rows do not. MEASURED 2026-08-12 on
# vault/dat_study/Gw.dat.
MAP_143 = 0x287D3          # C2's target; the smaller Bloated payload
MAP_143_ROW = 71496
MAP_143_BLOAT = 9284
MAP_143_TRAPS = 27
MAP_144 = 0x5D037          # E1's target
MAP_144_ROW = 26209
MAP_144_TRAPS = 26

# FLOOR: 28 from a real green run, 2026-08-12. Sections 0-3 alone score 22 --
# MEASURED with RURIK_VAULT pointed at nothing, not counted by eye; the first
# guess written here was 18 -- so a vault-less run lands 6 short and goes red.
# Everything above section 4 is this file's own logic judged by itself; only the
# archive can say the plan describes a map that exists.
FLOOR = 28

LEDGER = checks.Ledger("rebloat driver", floor=FLOOR)
check = checks.adopt(LEDGER)


def refuses(fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except SystemExit:
        return True
    except Exception:                                         # noqa: BLE001
        return False


def fake_base(bloat_size=9284, strip_size=4544, traps=27, gates=True,
              bloat_row=71496):
    """A baseline dict shaped like `rebloat.baseline`'s, with no archive."""
    bloated = {"row": bloat_row, "size": bloat_size, "reservation": 9728,
               "offset": 0x1000, "compression": 0, "crc": 1,
               "state": "map" if bloat_size else "zero length",
               "chunk_count": 9}
    if bloat_size and traps is not None:
        bloated.update(trapezoids=traps, planes=1, boundary_points=1,
                       path_sequence=94, sha256="a" * 64)
    stripped = {"row": bloat_row + 1, "size": strip_size, "reservation": 4608,
                "offset": 0x4000, "compression": 0, "crc": 2,
                "state": "stripped map", "hard_gates_present": gates}
    return {"archive": "X", "archive_bytes": 1, "file_id": "0x287D3",
            "block_size": 512, "entry_count": 99, "mft_offset": 0,
            "bloated": bloated, "stripped": stripped}


def main():
    # ---- 0. the write guards ------------------------------------------------
    print("0. the two archives this tool may never write to")
    check(refuses(rebloat.guard_target, r"C:\gw\Gw.dat"),
          "C:\\gw is refused -- the owner's install is read-only, permanently")
    check(refuses(rebloat.guard_target, r"C:\GW\Gw.dat"),
          "and the refusal is case-insensitive, because Windows is",
          "an all-caps path is the same path")
    check(refuses(rebloat.guard_target,
                  r"C:\gd\Rurik\vault\dat_study\Gw.dat"),
          "vault/dat_study is refused -- it is the SOURCE every copy is cut "
          "from")
    check(refuses(rebloat.guard_target,
                  r"C:\gd\Rurik\vault\dat_study\sub\Gw.dat"),
          "and so is anything BELOW it, not just the file itself")
    # THE POSITIVE CONTROL. Without it a guard that refused everything would
    # score the four checks above and protect nothing, because the tool would
    # simply never run.
    ok = os.path.join(tempfile.gettempdir(), "rurik_copy", "Gw.dat")
    check(not refuses(rebloat.guard_target, ok),
          "but an ordinary copy is ALLOWED -- a guard that refuses everything "
          "is not a guard", ok)
    check(not refuses(rebloat.guard_target,
                      r"C:\gd\Rurik\vault\dat_c2\Gw.dat"),
          "and so is another vault copy, which is where the experiment runs")

    # ---- 1. the outcomes, decided before the run ---------------------------
    print("\n1. the four outcomes are told apart")
    zero = {"size": 0, "state": "zero length"}
    rebuilt = {"size": 9284, "state": "map", "trapezoids": 27}
    written = {"size": 12, "state": "DOES NOT DECODE: ValueError: nope"}
    nopath = {"size": 9284, "state": "map WITHOUT a pathing chunk"}
    check(rebloat.classify(None, zero) == rebloat.UNCHANGED,
          "a still-zero stream is UNCHANGED, not a failure")
    check(rebloat.classify(None, rebuilt) == rebloat.REBUILT,
          "a decodable map WITH a pathing chunk is REBUILT")
    check(rebloat.classify(None, written) == rebloat.WRITTEN,
          "bytes that do not decode are WRITTEN, and are not called a rebuild")
    check(rebloat.classify(None, nopath) == rebloat.WRITTEN,
          "and a map WITHOUT a pathing chunk is NOT a rebuild either -- the "
          "chunk is the whole point of the experiment")
    check(rebloat.classify(None, None) == rebloat.MISSING,
          "an unresolvable stream is MISSING")

    # ---- 2. maps that cannot answer the question ---------------------------
    print("\n2. the plan refuses a map that could not answer the question")
    check(rebloat.problems_with(fake_base()) == [],
          "a healthy map produces no problems -- the positive control for the "
          "four refusals below")
    p = rebloat.problems_with(fake_base(bloat_size=0))
    check(any("ALREADY zero" in x for x in p),
          "an already-armed archive is refused, not armed twice", str(p)[:80])
    p = rebloat.problems_with(fake_base(strip_size=0))
    check(any("nothing to compile" in x for x in p),
          "a zero-length Stripped stream is refused -- there is no input")
    p = rebloat.problems_with(fake_base(gates=False))
    check(any("hard gates" in x for x in p),
          "a Stripped stream missing Terrain or Props is refused: FINDINGS 34's "
          "unguarded `je`s mean NO Path chunk is produced even if the client "
          "does compile, so the run could not distinguish that from a client "
          "that never compiles", str(p)[:80])
    p = rebloat.problems_with(fake_base(traps=None))
    check(any("no baseline mesh" in x for x in p),
          "and a Bloated stream with no pathing chunk is refused -- without a "
          "baseline, 'a Path chunk exists' is satisfied by bytes we did not "
          "delete")

    # ---- 3. the arm/revert cycle, on an archive this file builds -----------
    print("\n3. arming is reversible, byte for byte (no vault)")
    tmp = tempfile.mkdtemp(prefix="rurik_rebloat_")
    try:
        path = os.path.join(tmp, "Gw.dat")
        build_archive(path)
        pristine = os.path.join(tmp, "pristine.dat")
        shutil.copyfile(path, pristine)
        before_sha = hashlib.sha256(open(path, "rb").read()).hexdigest()

        pre, _extra = datcheck.preflight(path)
        check(all(c.ok for c in pre) and len(pre) >= 10,
              "the fixture archive passes every open-time rule to begin with",
              f"{len(pre)} checks")

        with Archive(path) as ar:
            row = max((e.index for e in ar.entries if e.size > 0))
            before_size = ar.entries[row - 1].size
        journal = os.path.join(tmp, "j.json")
        writer = datwrite.Writer(path, journal)
        try:
            writer.replace(row, b"")
        finally:
            writer.close()

        with Archive(path) as ar:
            e = ar.entries[row - 1]
            check(e.size == 0 and e.compression == 0 and e.crc == 0,
                  f"row {row} is zero length, uncompressed, crc 0",
                  f"size={e.size} comp={e.compression} crc=0x{e.crc:08X}")
            check(len(ar.read(e)) == 0,
                  "and it READS BACK as zero bytes rather than erroring")

        # THE GATE THIS WHOLE TRIGGER RESTS ON. FINDINGS 17.1 picks the
        # zero-length payload as the cheapest provocation; if the archive's own
        # open-time rules rejected a zero-size row, the trigger would be
        # unusable and the experiment would need a different one.
        post, _extra = datcheck.preflight(path)
        bad = [c.name for c in post if not c.ok]
        check(not bad,
              "AND ALL TEN OPEN-TIME RULES STILL PASS with a zero-length row -- "
              "which is what makes this trigger usable at all",
              ", ".join(bad) if bad else f"{len(post)} checks green")

        datwrite.revert(journal, force=True)
        after_sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        check(after_sha == before_sha,
              "and --revert restores the archive BYTE-IDENTICALLY, whole "
              "reservation included",
              f"{before_sha[:16]} vs {after_sha[:16]}")
        with Archive(path) as ar:
            check(ar.entries[row - 1].size == before_size,
                  f"row {row}'s size field is back to {before_size}",
                  f"{ar.entries[row - 1].size}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- 4. the real archive, READ-ONLY ------------------------------------
    dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("4. the two reachable maps",
                    f"no archive at {dat} (vault resolved to "
                    f"{vaultpath.vault_root()}, {vaultpath.vault_why()})")
    else:
        print("\n4. the maps the harness can actually reach (read-only)")
        base = rebloat.baseline(dat, MAP_143)
        b, s = base["bloated"], base["stripped"]
        check(b["row"] == MAP_143_ROW and b["size"] == MAP_143_BLOAT,
              f"map 143 (0x{MAP_143:X}) is row {MAP_143_ROW}, "
              f"{MAP_143_BLOAT} B Bloated",
              f"row {b['row']}, {b['size']} B")
        check(b.get("trapezoids") == MAP_143_TRAPS,
              f"its shipped navmesh is {MAP_143_TRAPS} trapezoids -- the "
              f"baseline a rebuild is judged against",
              f"{b.get('trapezoids')}")
        check(s["hard_gates_present"] is True,
              "and its Stripped stream carries BOTH hard gates, so this map "
              "CAN answer the question")
        check(rebloat.problems_with(base) == [],
              "so the plan accepts it", str(rebloat.problems_with(base))[:100])

        base144 = rebloat.baseline(dat, MAP_144)
        check(base144["bloated"]["row"] == MAP_144_ROW
              and base144["bloated"].get("trapezoids") == MAP_144_TRAPS,
              f"map 144 (0x{MAP_144:X}) is row {MAP_144_ROW} with "
              f"{MAP_144_TRAPS} trapezoids -- the fallback target",
              f"row {base144['bloated']['row']}, "
              f"{base144['bloated'].get('trapezoids')} traps")
        # A read-only tool must not have touched anything.
        check(rebloat.baseline(dat, MAP_143)["bloated"]["sha256"]
              == b["sha256"],
              "and reading the baseline twice gives the same payload digest, "
              "so --plan really is read-only")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
