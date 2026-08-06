"""The content store: that it loads, that the rows are the ones we migrated, and --
the part that matters -- that its two refusals actually refuse.

A loader with a provenance rule nobody has watched reject anything is a comment with
extra steps. So most of this file constructs rows that SHOULD be rejected and asserts
they are: a row with no provenance, a row with an invented source, and a row citing an
all-rights-reserved upstream with nothing recorded about what we verified. That last
one is the licence rule from PLAN.md section 1.1 turned into a load error, and it is
the reason this store can be trusted to grow.

The other half is a regression gate on the migration itself. `content/*.toml` replaced
Python literals on 2026-08-06, and the failure mode of that kind of move is a value
quietly changing. The expected numbers below were read off the pre-migration modules,
so a wrong edit to the TOML reddens here rather than at the client.

    python toolkit/test_content.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "authsrv"))
import checks  # noqa: E402
import content  # noqa: E402

# 4 load + 5 migration + 7 refusal + 3 overlay + 2 shape = 21, measured from a
# real green run. Every section runs unconditionally; nothing here is fixture-dependent
# beyond content/ itself, which is tracked.
LEDGER = checks.Ledger("content store", floor=21)


def write(dirpath, name, text):
    with open(os.path.join(dirpath, name), "w", encoding="utf-8") as fh:
        fh.write(text)
    return dirpath


def refuses(toml_text, because):
    """Load a one-file store and return the ContentError message, or None."""
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml", toml_text)
        try:
            content.load(repo_dir=tmp, vault_dir="")
        except content.ContentError as exc:
            return str(exc)
        return None


GOOD_PROV = '[thing.a.provenance]\nsource = "measured"\n'


def main():
    world = content.load()

    # --- it loads, and it loaded the tables we expect ------------------------
    LEDGER.ok(world.census().get("map", 0) == 8,
              "eight maps load", f"{world.census().get('map')}")
    LEDGER.ok(all(world.census().get(k) for k in
                  ("npc", "item", "spawn", "player", "attack_speed")),
              "every table has at least one row", str(world.census()))
    LEDGER.ok(all(r.provenance.get("source") in content.SOURCES
                  for kind in world.tables for r in world.rows(kind).values()),
              "every row in the shipped store carries a known source")
    unlicensed = [(k, key) for k in world.tables
                  for key, r in world.rows(k).items()
                  if r.provenance["source"] in content.UNLICENSED]
    LEDGER.ok(all(str(world.get(k, key).provenance.get("verified") or "").strip()
                  for k, key in unlicensed),
              "every row citing an unlicensed upstream records what we verified",
              f"{len(unlicensed)} such row(s)")

    # --- the migration did not change a value --------------------------------
    # Read off the pre-migration authsrv.py / agents.py, 2026-08-06.
    msc = world.map_static_config()
    LEDGER.ok(msc[148] == (0x8001B97D, (9826.0, 8077.0), 0, False),
              "map 148 is byte-for-byte what MAP_STATIC_CONFIG held", str(msc[148]))
    LEDGER.ok(msc[449] == (0x345CC, (-9067.0, 13218.0), 0, False),
              "map 449 (the fallback) is unchanged", str(msc[449]))
    LEDGER.ok(len(msc) == 8 and set(msc) == {148, 146, 449, 194, 55, 474, 558, 90},
              "the same eight map ids, no more and no fewer")

    hatcher = world.get("npc", "hatcher")
    LEDGER.ok((hatcher["file_id"], hatcher["model_id"], hatcher["flags"],
               hatcher["scale"], hatcher["profession"], hatcher["level"]) ==
              (116228, 116703, 0x20C, 0x64000000, 3, 1),
              "the Hatcher's six numeric fields are unchanged")
    LEDGER.ok(hatcher["enc_name"] == [0x328A, 0xE3B9, 0xAA36, 0x2E69],
              "and its EncString words are unchanged -- these cannot be invented")

    # --- REFUSAL 1: a row with no provenance ---------------------------------
    msg = refuses('[thing.a]\nvalue = 1\n', "no provenance")
    LEDGER.ok(msg is not None, "a row with no provenance is REFUSED")
    LEDGER.ok(msg and "provenance.source" in msg,
              "and the error names what is missing", (msg or "")[:60])

    # --- REFUSAL 2: a source outside the vocabulary --------------------------
    msg = refuses('[thing.a]\nvalue = 1\n[thing.a.provenance]\nsource = "vibes"\n',
                  "unknown source")
    LEDGER.ok(msg is not None, "a row with an unknown source is REFUSED")
    LEDGER.ok(msg and "vibes" in msg, "and the error quotes the bad source")

    # --- REFUSAL 3: the licence rule, which is the reason this file exists ----
    msg = refuses('[thing.a]\nvalue = 1\n'
                  '[thing.a.provenance]\nsource = "gw-preservation"\n',
                  "unlicensed, unverified")
    LEDGER.ok(msg is not None,
              "a row citing an all-rights-reserved upstream with no `verified` "
              "is REFUSED")
    LEDGER.ok(msg and "never copy from them" in msg,
              "and the error quotes the rule it is enforcing",
              "PLAN.md section 1.1")

    # ...but the same row WITH a verification loads. A gate that refuses the
    # legitimate case too is not a gate, it is an outage.
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml",
              '[thing.a]\nvalue = 1\n[thing.a.provenance]\n'
              'source = "gw-preservation"\nverified = "resolves to MFT row 7982"\n')
        ok = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(ok.get("thing", "a")["value"] == 1,
              "the same row WITH a verification loads normally")

    # --- an empty store is refused, not defaulted ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        try:
            content.load(repo_dir=tmp, vault_dir="")
            empty_refused = False
        except content.ContentError:
            empty_refused = True
    LEDGER.ok(empty_refused,
              "an empty store is REFUSED rather than falling back to something "
              "invented")

    # --- the vault overlay -----------------------------------------------------
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as vault:
        write(repo, "a.toml",
              '[thing.a]\nvalue = 1\n' + GOOD_PROV +
              '[thing.b]\nvalue = 2\n[thing.b.provenance]\nsource = "measured"\n')
        write(vault, "a.toml",
              '[thing.b]\nvalue = 22\n[thing.b.provenance]\nsource = "capture"\n'
              '[thing.c]\nvalue = 3\n[thing.c.provenance]\nsource = "capture"\n')
        merged = content.load(repo_dir=repo, vault_dir=vault)
    LEDGER.ok(merged.get("thing", "a")["value"] == 1,
              "a repo row the vault does not mention survives the overlay")
    LEDGER.ok(merged.get("thing", "b")["value"] == 22,
              "a vault row overrides the repo row of the same key")
    LEDGER.ok(merged.get("thing", "c")["value"] == 3,
              "and the vault may add rows the repo does not have")

    # --- an unknown key is an error, not a None ------------------------------
    try:
        world.get("map", 99999)
        raised = False
    except content.ContentError:
        raised = True
    LEDGER.ok(raised, "asking for a row that does not exist raises rather than "
                      "returning None for something downstream to misread")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
