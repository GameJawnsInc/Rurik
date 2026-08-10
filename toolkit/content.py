"""The content store: world facts as data, loaded at startup, with provenance per row.

WHY THIS EXISTS. Every fact about the game world was a Python literal compiled into
`authsrv.py` and `agents.py` -- seven maps in `MAP_STATIC_CONFIG`, the Hatcher, the
starter hammer, the player's health and energy, where the test enemy stands. R5's
acceptance criterion is "a new zone authored in TOML, hot-reloaded, walked", and that
presupposes a store which did not exist; R4c would have minted fifty more literals
before anyone noticed.

The comparable is the MaNGOS -> TrinityCore -> AzerothCore lineage, where content
(creatures, spawns, loot, quests) lives in a versioned world database shipped separately
from the engine, and the server binary contains zero creatures. They learned it the hard
way: ScriptDev2 put creature stats in C++, so retuning a boss meant a recompile, and
migrating out took years and is still incomplete.

WHAT IS CONTENT AND WHAT IS NOT. The line this module draws:

  * CONTENT is a fact about the world. Which file a map loads, where you arrive, what
    a Hatcher's model is, how much health the player starts with. It goes here.
  * PROTOCOL VOCABULARY is a fact about the client. `ALLEGIANCE_ENEMY = 3`,
    `PROP_HEALTH_MAX = 42`, `GV_SKILL_ACTIVATED = 60`. Those were read out of the
    client's own code, they are what the wire MEANS, and they stay in `agents.py`.
    Moving them here would be a category error -- they are not authorable.

TWO RULES ENFORCED AT LOAD, NOT ASSERTED IN PROSE

1. EVERY ROW CARRIES PROVENANCE. A row without a `source` from the vocabulary below
   does not load. The house rule is that a claim without a label is a defect; a content
   row IS a claim -- "map 148 loads file 0x8001B97D" is exactly as falsifiable as
   anything in `studies/`, and it was previously recorded only as a Python comment
   that no tool could read.

2. AN UNLICENSED UPSTREAM MUST BE VERIFIED, NOT COPIED. `gw-preservation/*` and
   `Py4GW_Reforged` carry no licence, i.e. all rights reserved, and PLAN.md section 1.1
   says of them: "read them, learn from them, cite them -- never copy from them."
   `studies/enemy/PLAN.md` section 5 raised the question and left it to the owner.
   Owner's ruling, 2026-08-06: verified-only. So a row citing one of those sources
   MUST carry a non-empty `verified` string saying what we checked it against in OUR
   OWN artifacts, and a row that merely cites them is REFUSED with the rule quoted.
   That converts "never copy from them" from a sentence in a plan into a load error.

WHERE ROWS LIVE, and why there are two places. Owner's ruling, 2026-08-06:
hand-sized rows in the repo, bulk extraction in the vault.

  * `content/*.toml` (tracked) holds rows we verified individually -- today seven maps,
    one NPC, one item, the player's defaults. These are already in git; this moves them
    out of `.py` and does not change what is committed.
  * `vault/content/*.toml` (gitignored) is for anything machine-extracted or bulk: the
    397-map table, ~1,300 skills, the area table. It is merged OVER the repo rows by
    key, so the vault can extend or correct without editing tracked files.

The gate keeps its evidentiary value that way: "no extracted table was ever committed,
prove it with one git command" stays literally true, which is the whole reason PLAN.md
section 7 Q3 was answered "keep the absolute gate" rather than softening it.

    python toolkit/content.py            # load everything and print a census
    python toolkit/content.py --explain 148

Proved by `toolkit/test_content.py`, which checks the refusals actually refuse.
"""
import os
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vaultpath  # noqa: E402

REPO_CONTENT = os.path.join(os.path.dirname(HERE), "content")

# Where a value came from. Every row states one.
SOURCES = {
    "measured":        "read or checked against our own artifacts on this machine",
    "client-table":    "extracted from the pinned client's own static tables",
    "capture":         "observed on the wire in one of our captures",
    "gw-preservation": "gw-preservation/server -- NO LICENCE, verification required",
    "opentyria":       "ldufr/OpenTyria -- public domain (Unlicense)",
    "headquarter":     "ldufr/Headquarter -- MIT",
    "wiki":            "the official Guild Wars wiki",
    "invented":        "ours, chosen rather than observed. Says so out loud.",
}

# Sources whose upstream grants us no licence. A row citing one of these must record
# what we independently verified, or it does not load. See rule 2 above.
UNLICENSED = {"gw-preservation"}

RULE_1_1 = ('PLAN.md section 1.1: gw-preservation and Py4GW_Reforged "carry no license '
            'at all, which means all rights reserved: read them, learn from them, cite '
            'them -- never copy from them."')


class ContentError(Exception):
    """A row that does not load. Never a warning -- the house rule is refuse to guess."""


class Row(dict):
    """A content row. A dict, so existing call sites that index it keep working."""

    def __init__(self, mapping, kind, key, provenance):
        super().__init__(mapping)
        self.kind = kind
        self.key = key
        self.provenance = provenance

    def why(self):
        p = self.provenance
        out = [f"{self.kind}.{self.key}  source={p['source']}"]
        if p.get("verified"):
            out.append(f"  verified: {p['verified']}")
        if p.get("note"):
            out.append("  " + p["note"].strip().replace("\n", "\n  "))
        return "\n".join(out)


def _check_provenance(kind, key, row):
    prov = row.get("provenance")
    if not isinstance(prov, dict) or not prov.get("source"):
        raise ContentError(
            f"{kind} row {key!r} has no provenance.source. Every content row is a "
            f"claim about the world and carries its label, same as a study does. "
            f"One of: {', '.join(sorted(SOURCES))}")
    source = prov["source"]
    if source not in SOURCES:
        raise ContentError(
            f"{kind} row {key!r} claims source {source!r}, which is not a known "
            f"source. One of: {', '.join(sorted(SOURCES))}")
    verified = prov.get("verified")
    if source in UNLICENSED and not (isinstance(verified, str) and verified.strip()):
        had = "" if verified is None else f" (it is {verified!r}, not descriptive text)"
        raise ContentError(
            f"{kind} row {key!r} cites {source!r} with no descriptive `verified` "
            f"field{had}. A bare `true` or a number satisfies nothing -- the field "
            f"exists to record WHAT was checked, so it must be non-empty text.\n"
            f"{RULE_1_1}\n"
            f"Owner's ruling 2026-08-06: verified-only. Record what this row was "
            f"checked against in OUR OWN artifacts -- an archive row, a parsed mesh, "
            f"a capture -- or derive the value independently. Citing them is reading; "
            f"a row with no verification is transcription.")
    return prov


def _load_file(path):
    if not os.path.isfile(path):
        return {}
    with open(path, "rb") as fh:
        try:
            return tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ContentError(f"{path}: {exc}") from exc


def _merge(base, overlay):
    """Overlay wins per top-level key. Used to let the vault extend the repo."""
    out = dict(base)
    for section, rows in overlay.items():
        if isinstance(rows, dict) and isinstance(out.get(section), dict):
            merged = dict(out[section])
            merged.update(rows)
            out[section] = merged
        else:
            out[section] = rows
    return out


class World:
    """Everything loaded, indexed. Built once at startup."""

    def __init__(self, tables, sources):
        self.tables = tables
        self.sources = sources

    def rows(self, kind):
        return self.tables.get(kind, {})

    def get(self, kind, key):
        table = self.tables.get(kind, {})
        if key not in table:
            raise ContentError(
                f"no {kind} row {key!r}. Known: {', '.join(map(str, sorted(table, key=str)))}")
        return table[key]

    def map_static_config(self):
        """The shape `authsrv.py` has always used: id -> (file_id, spawn, plane, explorable).

        Kept deliberately identical so this change is only about WHERE the data lives.
        Restructuring the eight call sites is a separate change with its own test.
        """
        return {int(k): (r["file_id"], (float(r["spawn_x"]), float(r["spawn_y"])),
                         int(r["plane"]), bool(r["explorable"]))
                for k, r in self.rows("map").items()}

    def census(self):
        return {kind: len(rows) for kind, rows in sorted(self.tables.items())}


def load(repo_dir=None, vault_dir=None, require_vault=False):
    """Load every content table. Repo first, then the vault merged over it."""
    repo_dir = repo_dir or REPO_CONTENT
    if vault_dir is None:
        try:
            vault_dir = vaultpath.vault_path("content")
        except Exception:
            vault_dir = None
    if require_vault:
        vault_dir = vaultpath.require_dir("content", why="content overlay")

    raw, sources = {}, []
    for directory, label in ((repo_dir, "repo"), (vault_dir, "vault")):
        if not directory or not os.path.isdir(directory):
            continue
        files = sorted(f for f in os.listdir(directory) if f.endswith(".toml"))
        for name in files:
            raw = _merge(raw, _load_file(os.path.join(directory, name)))
        if files:
            sources.append(f"{label}:{directory} ({len(files)} file(s))")

    if not raw:
        raise ContentError(
            f"no content loaded. Looked in {repo_dir!r}"
            + (f" and {vault_dir!r}" if vault_dir else "")
            + ". A server with no world is not a server; refusing to start with an "
              "empty store rather than falling back to something invented.")

    tables = {}
    for kind, rows in raw.items():
        if not isinstance(rows, dict):
            continue
        out = {}
        for key, row in rows.items():
            if not isinstance(row, dict):
                continue
            prov = _check_provenance(kind, key, row)
            body = {k: v for k, v in row.items() if k != "provenance"}
            out[key] = Row(body, kind, key, prov)
        tables[kind] = out
    return World(tables, sources)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--explain", metavar="KEY",
                    help="print the provenance of every row with this key")
    args = ap.parse_args()

    world = load()
    for s in world.sources:
        print(f"loaded  {s}")
    print()
    for kind, n in world.census().items():
        print(f"  {kind:14s} {n} row(s)")

    if args.explain:
        print()
        hit = False
        for kind in world.tables:
            for key, row in world.rows(kind).items():
                if str(key) == args.explain:
                    print(row.why())
                    print()
                    hit = True
        if not hit:
            print(f"no row keyed {args.explain!r}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
