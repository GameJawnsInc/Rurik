"""Prove the hero-table extractor reads the HERO table, and refuses when it cannot.

`s_titleClientData` sits SIX INSTRUCTIONS from `s_heroClientData` -- accessor
`0x005A9350` (`cmp esi,0x30`, stride 12) versus `0x005A9380` (`cmp esi,0x28`,
stride 24) -- and this arc lost a contested reading to exactly that adjacency
until the client's own assert strings settled it
(`studies/heroes/FINDINGS.md` 2). A structural locator that closes on the wrong
anchor still closes, so the danger here is not an error: it is a clean,
plausible, wrong table of numbers presented as heroes.

  1 the geometry is the hero table's, and it CLOSES at its own anchor
  2 the index column agrees with the row number on every row
  3 the wrong geometry is REFUSED, not emitted -- the title-table trap
  4 every emitted row passes content.py's real provenance gate, and the gate
    is shown able to refuse
  5 a bulk `--resolve` is refused; ids only is the gate, not a style choice

Needs the vault. Skips with its reason rather than passing vacuously.

    python toolkit/clientscan/test_heroes_table.py
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, HERE)
import checks           # noqa: E402
import content          # noqa: E402
import pinned           # noqa: E402
import vaultpath        # noqa: E402

# 10, from a real green run. Guessed at 9 first and the count came back
# higher; the floor is set from what a healthy run produces, never from
# the guess that preceded it.
LEDGER = checks.Ledger("heroes_table", floor=10)


def main():
    try:
        import heroes_table
        pe, table = heroes_table.load()
    except Exception as ex:
        LEDGER.skip("the whole file", f"needs the vaulted client: {ex}")
        return LEDGER.verdict()

    # ---- 1. the geometry, and the closure ------------------------------------
    print("1. it is the hero table")
    LEDGER.ok(table.stride == 24, "stride 24", f"{table.stride}")
    LEDGER.ok(table.count == 40,
              "40 rows -- ChCliApi:4446 `hero < HEROES`, `cmp esi,0x28`",
              f"{table.count}")
    # The check the artifact can refute: the table must END exactly where its
    # anchor string begins. A base or stride that is off by one row does not
    # close here.
    LEDGER.ok(table.base + table.count * table.stride == table.anchor_off,
              "and it closes on the byte: base + 40*24 == the anchor offset",
              f"0x{table.base:06X} + 960 vs anchor 0x{table.anchor_off:06X}")

    # ---- 2. the index column -------------------------------------------------
    print("\n2. the index column")
    rows = heroes_table.rows(pe, table)
    LEDGER.ok(all(r["index"] == r["row"] for r in rows),
              "every row's index field equals its row number",
              "this column is what identifies the table; a mismatch means the "
              "base or the stride is wrong")
    LEDGER.ok(not heroes_table.check(rows),
              "and the module's own closure checks are silent",
              f"{heroes_table.check(rows)}")

    # ---- 3. THE TRAP: wrong geometry is refused -------------------------------
    print("\n3. the s_titleClientData trap")
    import consttable
    real = consttable.table_for

    class Fake:                     # the title table's geometry, near enough
        stride, count, base = 12, 48, 0x634B80
    try:
        consttable.table_for = lambda pe_, sym: Fake()
        try:
            heroes_table.load()
            LEDGER.ok(False, "48 x 12 is refused",
                      "IT WAS ACCEPTED -- the extractor would emit the title "
                      "table's numbers as heroes")
        except heroes_table.WrongTable as ex:
            LEDGER.ok("s_titleClientData" in str(ex),
                      "48 x 12 is refused, and the message names the trap",
                      str(ex)[:110])
    finally:
        consttable.table_for = real
    # ...and the refusal is not simply always-on.
    LEDGER.ok(heroes_table.load() is not None,
              "while the real table still loads",
              "otherwise section 3 proves only that load() always raises")

    # ---- 4. the provenance gate, both directions -----------------------------
    print("\n4. content.py's real gate")
    out = subprocess.run([sys.executable, os.path.join(HERE, "heroes_table.py"),
                          "--toml"], capture_output=True, text=True)
    import tomllib
    emitted = tomllib.loads(out.stdout)["hero"]
    accepted = 0
    for i, r in enumerate(emitted):
        content._check_provenance("hero", str(i), r)
        accepted += 1
    LEDGER.ok(accepted == len(emitted) == 40,
              f"all {accepted} emitted rows pass _check_provenance",
              "per-row provenance is condition 3 of the owner's ruling and the "
              "one content.py cannot infer")
    stripped = dict(emitted[1])
    stripped["provenance"] = {k: v for k, v in emitted[1]["provenance"].items()
                              if k != "extractor"}
    try:
        content._check_provenance("hero", "1", stripped)
        LEDGER.ok(False, "and the gate refuses a row with no extractor",
                  "IT ACCEPTED ONE -- the gate is vacuous and the check above "
                  "proves nothing")
    except content.ContentError:
        LEDGER.ok(True, "and the gate refuses a row with no extractor",
                  "so the 40/40 above is a result rather than a tautology")

    # The build a row records must be the build it was READ ON. Added
    # 2026-08-17: it was `pinned.BUILD`, so rows emitted from any client
    # claimed 38797 and the gate above passed them all -- `_check_provenance`
    # asks that a build be PRESENT, not that it be true. `--exe` at a second
    # real client is the only thing that can tell the two apart.
    others = [b for b in pinned.BUILDS if b.number != pinned.BUILD]
    have = [(b, p) for b, p in ((b, os.path.join(vaultpath.vault_root(), "client",
                                                 b.stamp, "Gw.exe")) for b in others)
            if os.path.isfile(p)]
    stamped = {r["provenance"]["build"] for r in emitted}
    LEDGER.ok(stamped == {pinned.BUILD},
              f"the default emit records build {pinned.BUILD}", str(stamped))
    if not have:
        LEDGER.skip("the wrong-build stamp", "only the pinned client is vaulted")
    else:
        other, other_path = have[-1]
        r2 = subprocess.run([sys.executable, os.path.join(HERE, "heroes_table.py"),
                             "--exe", other_path, "--toml"],
                            capture_output=True, text=True)
        got = {row["provenance"]["build"]
               for row in tomllib.loads(r2.stdout)["hero"]}
        LEDGER.ok(got == {other.number} and other.number != pinned.BUILD,
                  f"and `--exe` at the build-{other.number} client records "
                  f"{other.number}, not {pinned.BUILD}",
                  f"{got} -- a build stamped from a constant passes the gate "
                  f"and is still a provenance misreport, because the row is "
                  f"what gets committed and re-derived")

    # ---- 5. no bulk resolution ------------------------------------------------
    print("\n5. ids only")
    r = subprocess.run([sys.executable, os.path.join(HERE, "heroes_table.py"),
                        "--resolve"], capture_output=True, text=True)
    LEDGER.ok(r.returncode == 2 and "refuses" in (r.stdout + r.stderr),
              "`--resolve` with no rows is refused",
              "a committed column of resolved English is the bulk expression "
              "the provenance gate refuses; a row or two is a measurement")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
