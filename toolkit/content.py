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
  * `content/overrides/*.toml` (tracked) is merged LAST, over the vault: rows verified
    individually on a NEWER build than the vault's bulk table (2026-09-14, SLICE-H17b:
    fourteen skills whose adrenaline moved on 38888 while the vault's table is the pin's).
    Without this layer a tracked row could never correct a bulk one -- the vault's
    row-level `update` replaced it wholesale -- and the only way to take one build's
    number was to regenerate the whole table on that build.
  * `RURIK_CONTENT_EXTRA` (os.pathsep-separated directories, unset by default) is
    merged LAST of all, for rows that belong to ONE RUN rather than to this machine:
    the orchestrator's generated party and spawn rows (SANDBOX-B1, 2026-09-20,
    `toolkit/harness/sandbox.py`). The vault overlay is read by every process on the
    machine, so a per-launch row there would leak into the next unrelated run.
  * THE LABEL TIER SITS UNDER EVERYTHING (2026-09-23, SKILLS-LT, DESKWORK-D4 step 4).
    A row carrying `tier = "label"` -- `vault/content/skill_labels.toml`, the
    `skill_effect` rows `toolkit/clientscan/skilldesc.py --emit-labels` generates from
    the client's own description templates -- NEVER replaces a row without that tier,
    whichever layer either came from. The layer order above says "later wins"; this
    is the one exception, and it is by TIER rather than by layer because a generated
    row must lose to a hand-verified one even when the hand row is in the repo (the
    lowest layer) and the label row in the vault (above it). `_merge` enforces it;
    `test_content.py` proves it with the plain-merge known-bad arm. The emitter also
    skips hand-row ids, but the load rule is the guarantee. `World.drop_tier` is how
    `--no-skill-labels` makes the server forget the tier entirely. The tier values are
    a CLOSED set (`TIERS`): a `tier` outside it is refused at load, because the rule
    compares the string exactly and a near-miss would load as a hand row
    (`_check_tier`). A client-table row with NO tier is a hand row (world.toml's 346).
    And a label row whose `tier_detail` carries a mark this tree does not know
    (`LABEL_DETAILS_KNOWN`) is DROPPED at load and named in `World.dropped`, because
    the mark may name a consumer this tree lacks and the vault is machine-wide
    (SKILLS-LU's fix pass; `authsrv.main` prints the drops at startup).

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

# Sources that are EXTRACTED rather than reasoned: the row is a fact read out of
# ArenaNet's own artifact by our own tool. Owner's ruling 2026-08-11 (PLAN.md section 7
# Q3) permits these IN BULK, which is a loosening, on three conditions -- and two of the
# three are enforced here rather than asserted in a document, because the permission is
# the loosening direction and section 1.1's lesson is that a rule nothing checks is a wish.
#
# The boundary that ruling draws is MEASUREMENT versus EXPRESSION, not bulk versus single
# and not data versus code. A level, a bound, a stride, an id, an offset: facts about a
# system, permitted. Asset bytes, decompiled bodies and BULK DUMPS of assert strings:
# ArenaNet's expression, still refused, and no `extractor` field makes them loadable --
# this check cannot see them, which is why the ruling names them explicitly and why the
# third condition (per-row provenance) is the one a human still has to read.
#
# CORRECTED 2026-08-16, and the paragraph above was itself the defect. It used to end
# "...and verbatim assert expressions with their source path and line", which reads as a
# blanket refusal of the citation form every evidence chain in this repo is BUILT ON.
# CLAUDE.md's REFINED 2026-08-12 clause reverses exactly that, and it was written because a
# session read the old wording literally, rewrote 46 citations across sixteen documents, and
# had all 46 reverted. The boundary has a SIZE term and a SOURCE term: a SINGLE assert cited
# as the evidence for ONE claim is a MEASUREMENT -- keep it, with its file and line, because
# the quote is what lets a reader audit the claim without owning the binary -- and the crash
# dialog is not extraction, since `Assertion: X / File.cpp(N)` is text the retail client
# shows any player who crashes. Only the BULK DUMP is refused.
#
# This file was the last place still carrying the old wording, four days after CLAUDE.md
# fixed it, and it is the file a cold session reads FIRST when it wants to know what the
# gate refuses -- so the over-refusal had a live route back in. `studies/quests/FINDINGS.md`
# section 7.9 caught it; seven recon lanes before that did not. The direction of error in
# this repo is over-refusal, and a comment is how it propagates.
#
# Names and authored text are the deliberate middle: commit the id, resolve the string at
# run time from the owner's own archive. That is not a compromise invented for the ruling,
# it is what mapbuild.py already does with FINDINGS 14's five mandatory chunks.
EXTRACTED = {"client-table", "measured"}

# ...and `measured` is in that set because of a hole found the same day the ruling landed.
# The ruling's conditions were attached to the TOKEN `client-table`, so `measured` -- defined
# as "read or checked against our own artifacts on this machine", which covers reading a
# table out of the vaulted client -- performed the identical act and triggered nothing.
# **The conditions were opt-in by word choice.** That is the same shape as the defect the
# ruling exists to fix, one level down, and it was found by asking what a row could get away
# with rather than by reading the rule: `source = "measured"` with no extractor LOADED.
#
# `build` is required only for `client-table`, and the asymmetry is deliberate rather than
# lazy. A table read out of `Gw.exe` is a fact about THAT BUILD and moves when ArenaNet
# ships -- 38797 today. A value measured in an archive or a mesh is a fact about an
# ARTIFACT, which the row's `verified` text identifies; forcing a build number onto it would
# buy a field that is either guessed or meaningless, and a guessed field is worse than an
# absent one. What both need is the EXTRACTOR, because "measured" with no named tool is
# unfalsifiable in exactly the way this store exists to prevent.
NEEDS_BUILD = {"client-table"}

# A capture row's value depends on session properties that no later reader can recover, so
# the row must name the session.
NEEDS_CAPTURE = {"capture"}

# ...and for the fields Reforged Mode moves, it must name the MODE. That mode scales enemy
# health and armour ~20%, leaves no mark on the recorded stream, and is unrecoverable
# afterwards, so an unstamped stat is base or base x 0.8 forever -- at a size that reads as
# a plausible base value rather than an obvious error, which is why it is caught here rather
# than left to a reader's judgement.
#
# `livesession.py --mode base|reforged` has been REQUIRED since 2026-08-11, so a capture
# taken from now on can answer this. Captures taken before it cannot, and the honest value
# for those is the literal string "unrecorded" -- which this check ACCEPTS. That is
# deliberate and is `origin.py`'s three-valued precedent: `unknown` exists so a file is
# never forced into a claim it cannot support. What is refused is SILENCE, not ignorance.
MODE_SENSITIVE = ("health", "max_health", "armor", "armour", "energy", "max_energy")
KNOWN_MODES = ("base", "reforged", "unrecorded")

# GWW is a fine source for a published constant and a terrible one for an unsourced number,
# and the difference is whether the row says WHERE. Until this check existed, a row with
# `source = "wiki"` and a fabricated `health = 999` loaded clean -- which is the single
# cheapest way to fake a green content rung, 35 rows of guesses wearing citations.
NEEDS_PAGE = {"wiki"}

RULE_1_1 = ('PLAN.md section 1.1: gw-preservation and Py4GW_Reforged "carry no license '
            'at all, which means all rights reserved: read them, learn from them, cite '
            'them -- never copy from them."')

# The generated tier (WHERE ROWS LIVE, last bullet). A row whose body says
# `tier = "label"` is machine-derived from a parse and sits UNDER every hand row.
LABEL_TIER = "label"
# The CLOSED set of tier values a row may carry. `_merge` and `drop_tier` compare
# the string exactly, so a near-miss spelling ("Label", "labels", "label ") would
# load as a HAND row: it would replace the real hand row, survive --no-skill-labels
# and grade "modelled" (reviewer ENG-6). Refused at load instead.
TIERS = frozenset({LABEL_TIER})
# THE MARKS A LABEL ROW MAY CARRY AND THIS TREE KNOWS (SKILLS-LU's fix pass, 2026-09-23,
# skills 59.7; reviewer ENG-D4C-2). A label row names the machinery it rides in
# `tier_detail` -- AREA_CASTER, HEAL_PARTY, CHAIN_GATED are CONSUMER marks: without
# that consumer the row falls through to the one-target path, which is the very
# over-application the gate's exclusion refused. The vault is machine-wide, so a
# regenerated overlay reaches every tree at once, merged or not -- and the tree that
# lacks the consumer cannot know which new token names one. So a label row carrying
# ANY token outside this set is DROPPED at load (named in `World.dropped`, never
# served), which is the pre-consumer state for that row and self-heals when the tree
# merges. The set is `skilldesc`'s whole `tier_detail` vocabulary (DETAILS +
# AREA_WORDING + the target flags), pinned equal to it by `test_skilldesc` so a new
# mark lands in both files in one commit; `content.py` cannot import `skilldesc` (the
# server path stays free of clientscan), hence the copy.
LABEL_DETAILS_KNOWN = frozenset({
    "ALL_ALLIES", "ALL_FOES", "AREA_ADJACENT", "AREA_BURST", "AREA_CASTER", "AREA_EARSHOT",
    "AREA_IN_THE_AREA", "AREA_NEAR", "AREA_NEARBY", "AREA_ONE_TARGET", "CHAIN_GATED",
    "CHAIN_STEP_ADVANCES", "CHAIN_STEP_NOT_ADVANCED", "CLAUSE_ALSO_CASTER", "CLAUSE_CAST_SPEED",
    "CLAUSE_DISABLE", "CLAUSE_DOUBLE_DAMAGE", "CLAUSE_INTERRUPT", "CLAUSE_KNOCKDOWN",
    "CLAUSE_MOVE_SPEED", "CLAUSE_RANGE", "CLAUSE_REMOVAL", "CLAUSE_REVEAL", "CLAUSE_SHADOW_STEP",
    "CONDITION_BIT_CLEAR_REFUSED", "CONDITION_UNNUMBERED", "DURATION_UNMODELLED", "HEAL_PARTY",
    "INDETERMINATE_SLOT", "LITERAL_DROPPED", "SECOND_CONDITION_DROPPED", "TARGET_ALLY",
    "TARGET_FOE", "TOUCH",
})
# (A client-table skill_effect row with NO tier is a legitimate HAND row -- world.toml's
# 346 measures its number from the client's table and is hand-placed -- so the other
# direction, "an extracted row must carry a tier", is NOT a rule; the emitter's own
# checker guarantees its rows carry one.)


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


def _check_mode(kind, key, row, prov):
    """A capture row carrying a Reforged-sensitive stat must say which mode produced it."""
    moved = sorted(f for f in row if f in MODE_SENSITIVE)
    if not moved:
        return
    mode = prov.get("mode")
    if mode not in KNOWN_MODES:
        raise ContentError(
            f"{kind} row {key!r} is a capture row carrying {', '.join(moved)} and its "
            f"`mode` is {mode!r}, not one of {', '.join(KNOWN_MODES)}.\n"
            f"Reforged Mode scales enemy health and armour by roughly 20% and leaves no "
            f"mark on the recorded stream, so an unstamped stat is base or base x 0.8 "
            f"and nothing can ever say which -- at a size that reads as a plausible base "
            f"value rather than an obvious error.\n"
            f"`livesession.py --mode` has been required since 2026-08-11, so a capture "
            f"taken since then can answer this. For an older one the honest value is "
            f"\"unrecorded\", which loads: what is refused here is SILENCE, not ignorance.")


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
    if source in EXTRACTED:
        _check_extracted(kind, key, prov)
    if source in NEEDS_CAPTURE:
        _need(kind, key, prov, "capture",
              "which capture this was read out of -- the vault stamp, e.g. "
              "'20260807T143055'. A capture row's value depends on session properties "
              "no later reader can recover, so the row names the session or it is not a "
              "capture row.")
        _need(kind, key, prov, "origin",
              "whose server produced it: 'live' or 'ours'. toolkit/origin.py is "
              "three-valued and refuses to pool them, and a statistic about ArenaNet's "
              "behaviour computed over our own server's traffic is not weaker evidence, "
              "it is different evidence.")
        _check_mode(kind, key, row, prov)
    if source in NEEDS_PAGE:
        _need(kind, key, prov, "page",
              "the wiki page and section the value came from, and when it was read. "
              "A number with no page cannot be re-read or refuted, and 'the wiki says "
              "so' is UPSTREAM rather than a fact about retail Guild Wars.")
    return prov


def _need(kind, key, prov, field, why):
    """Require a non-empty provenance field, naming what it is for."""
    v = prov.get(field)
    if not (isinstance(v, (str, int)) and str(v).strip()):
        had = "" if v is None else f" (it is {v!r})"
        raise ContentError(
            f"{kind} row {key!r} has source {prov['source']!r} and no `{field}`{had}. "
            f"{why}")


def _check_tier(kind, key, row, prov):
    """A `tier`, when present, is one of TIERS or the row is refused. The tier rule
    in `_merge` compares the string exactly, so a row that misses the comparison
    would be promoted to a hand row by silence (ENG-6)."""
    tier = row.get("tier")
    if tier is not None and tier not in TIERS:
        raise ContentError(
            f"{kind} row {key!r} carries tier {tier!r}, which is not one of "
            f"{sorted(TIERS)}. A row whose tier misses the exact spelling would load as "
            f"a HAND row -- replacing the real one, surviving --no-skill-labels and grading "
            f"\"modelled\" -- so the set is closed and a near-miss is refused, not promoted.")


def _check_extracted(kind, key, prov):
    """Conditions 1 and 2 of the owner's 2026-08-11 ruling, enforced from the row.

    A fact extracted from ArenaNet's own artifact is permitted in bulk BECAUSE it
    regenerates from the owner's install -- that is the whole basis of the permission
    (`.gitignore`'s header: "Everything derived regenerates from the owner's own legally
    purchased install via a documented extraction step"). A row that does not name the
    tool, or names one that is not in this repo, does NOT regenerate, and the permission
    it is claiming does not cover it.

    The extractor path is resolved and required to EXIST. Requiring a non-empty string
    would be satisfiable by anything; requiring the file makes it a check that can fail,
    and it fails exactly when the tool is deleted, renamed or was never committed -- which
    is the state the condition exists to catch.
    """
    extractor = prov.get("extractor")
    if not (isinstance(extractor, str) and extractor.strip()):
        raise ContentError(
            f"{kind} row {key!r} cites an extracted source with no `extractor`. "
            f"Owner's ruling 2026-08-11 (PLAN.md section 7 Q3) permits bulk extraction "
            f"from the client on three conditions, and the first is that the tool that "
            f"produced the row is IN THIS REPO and named by the row. Without it the "
            f"artifact does not regenerate, which is the entire basis of the permission.")
    path = os.path.join(os.path.dirname(HERE), *extractor.replace("\\", "/").split("/"))
    if not os.path.exists(path):
        raise ContentError(
            f"{kind} row {key!r} names extractor {extractor!r}, which does not exist in "
            f"this checkout (looked at {path}). A named tool that is not here regenerates "
            f"nothing. If it moved, update the row; if it was never committed, the row is "
            f"a transcription wearing a citation.")
    if prov["source"] not in NEEDS_BUILD:
        return
    build = prov.get("build")
    if not (isinstance(build, (str, int)) and str(build).strip()):
        raise ContentError(
            f"{kind} row {key!r} cites an extracted source with no `build`. Condition 2: "
            f"a number read out of a client is a number about THAT client -- 38797 today. "
            f"Without the build it can be neither re-derived nor refuted, and ArenaNet's "
            f"tables move between builds.")


def _load_file(path):
    if not os.path.isfile(path):
        return {}
    with open(path, "rb") as fh:
        try:
            return tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ContentError(f"{path}: {exc}") from exc


def _is_label_row(row):
    return isinstance(row, dict) and row.get("tier") == LABEL_TIER


def _merge(base, overlay, tier_aware=True):
    """Overlay wins per top-level key -- EXCEPT a `tier = "label"` row, which never
    replaces a row without that tier (WHERE ROWS LIVE, last bullet). Used to let
    the vault extend the repo. `tier_aware=False` is the plain update this was
    until 2026-09-23, kept as test_content's known-bad arm: under it a generated
    row keyed on a hand row's id would win."""
    out = dict(base)
    for section, rows in overlay.items():
        if isinstance(rows, dict) and isinstance(out.get(section), dict):
            merged = dict(out[section])
            for key, row in rows.items():
                if (tier_aware and _is_label_row(row) and key in merged
                        and not _is_label_row(merged[key])):
                    continue
                merged[key] = row
            out[section] = merged
        else:
            out[section] = rows
    return out


def _unknown_label_details(row):
    """The `tier_detail` tokens of a label row this tree does not know, or []."""
    if not _is_label_row(row):
        return []
    return [str(t) for t in (row.get("tier_detail") or ()) if str(t) not in LABEL_DETAILS_KNOWN]


class World:
    """Everything loaded, indexed. Built once at startup. `dropped` names the
    label rows the load refused to serve (an unknown mark), one line each."""

    def __init__(self, tables, sources, dropped=()):
        self.tables = tables
        self.sources = sources
        self.dropped = list(dropped)

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

    def drop_tier(self, kind, tier):
        """Remove every `kind` row whose body says `tier = <tier>`, in place, and
        return them ({key: Row}) so a caller can put them back. `--no-skill-labels`
        (authsrv) drops the label tier this way: the consumers then see exactly the
        hand rows, which is the server as it was before 2026-09-23."""
        table = self.tables.get(kind, {})
        gone = {k: r for k, r in table.items() if r.get("tier") == tier}
        for k in gone:
            del table[k]
        return gone


def extra_dirs_from_env(env=None):
    """The directories `RURIK_CONTENT_EXTRA` names, in order, or [].

    SANDBOX-B1 (2026-09-20): a RUN may carry rows the tree does not -- the
    orchestrator writes a `[party.sandbox]` row and its `[spawn.sandbox_*]`
    rows for one launch -- and the vault overlay is the wrong place for them,
    because every process on this machine reads it. So a launch names its own
    directory (os.pathsep-separated for several), merged LAST, after
    `overrides/`. An empty or unset variable is exactly the old load.
    """
    raw = (os.environ if env is None else env).get("RURIK_CONTENT_EXTRA", "")
    return [d for d in raw.split(os.pathsep) if d.strip()]


def load(repo_dir=None, vault_dir=None, require_vault=False, overrides_dir=None,
         extra_dirs=None):
    """Load every content table. Repo first, then the vault merged over it, then
    the repo's `overrides/` merged over both (see WHERE ROWS LIVE), then any
    `extra_dirs` (default: `RURIK_CONTENT_EXTRA`, see extra_dirs_from_env)."""
    repo_dir = repo_dir or REPO_CONTENT
    if overrides_dir is None:
        overrides_dir = os.path.join(repo_dir, "overrides")
    if vault_dir is None:
        try:
            vault_dir = vaultpath.vault_path("content")
        except Exception:
            vault_dir = None
    if require_vault:
        vault_dir = vaultpath.require_dir("content", why="content overlay")
    if extra_dirs is None:
        extra_dirs = extra_dirs_from_env()

    raw, sources = {}, []
    for directory, label in ((repo_dir, "repo"), (vault_dir, "vault"),
                             (overrides_dir, "overrides"),
                             *((d, "extra") for d in extra_dirs)):
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

    tables, dropped = {}, []
    for kind, rows in raw.items():
        if not isinstance(rows, dict):
            continue
        out = {}
        for key, row in rows.items():
            if not isinstance(row, dict):
                continue
            prov = _check_provenance(kind, key, row)
            _check_tier(kind, key, row, prov)
            unknown = _unknown_label_details(row)
            if unknown:
                # SKILLS-LU's fix pass: a mark this tree does not know may name a
                # consumer it lacks -- the row is not served (LABEL_DETAILS_KNOWN)
                dropped.append(f"{kind} {key}: label row carries tier_detail "
                               f"{' '.join(unknown)} this tree does not know -- DROPPED, not "
                               f"served (merge main, or regenerate the overlay on this tree)")
                continue
            body = {k: v for k, v in row.items() if k != "provenance"}
            out[key] = Row(body, kind, key, prov)
        tables[kind] = out
    return World(tables, sources, dropped)


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
