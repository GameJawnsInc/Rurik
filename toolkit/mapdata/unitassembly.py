r"""The assembly resolver: a unit definition -> the closed archive file set.
READ ONLY.

Rung U4 of `studies/unitmodels/PLAN.md`: given a unit definition -- the
GAME_SMSG `0x0056` file id plus the `0x0057` body model ids, from a live
capture via `toolkit/authsrv/npcdefs.py` or from a `content/*.toml` row --
resolve every archive file the client's loaders would reach for it, with a
role label and the measured facts per file. Nothing here writes a file or
emits a byte of ArenaNet data; the output is ids, roles and counts.

    r = Resolver(archive_)
    res = r.resolve(UnitDef.from_content_row("hatcher", row))
    res.closed, res.needs_body, res.geometry_complete
    res.role_counts()                 # {"shell": 1, "body": 1, "link": 15, ...}

THE CLIENT'S OWN MECHANISM this replicates (SOURCE-CODE, build 38797; the
derivations live in `studies/mdlrefs/FINDINGS.md` and
`studies/unitmodels/FINDINGS.md` SS3/SS5, cited per claim in `mdlrefs.py` /
`skelfile.py` -- this module deliberately re-reads nothing from the binary):

  * models load through ONE cached by-id loader (`0x00794260`, cache global
    `0xF26F10`); FA8 links are resolved AT LOAD by the recursion loop
    `0x00794850-0x0079492D` through that cache, each link required to be a
    skeleton object with `m_seqCount != 0` (`0x00794917`). The visited-set
    walk below is that cache's closure, computed instead of cached.
  * the five reference lists land at measured object offsets: FA5 textures
    (A+0xC0), FAD (A+0xFC), FA6 sound cues = ArenaNet's `m_soundPaths`
    (B+0x80, consumer MdlAnim:2040 at `0x00780D55`), FA8 links (B+0x10C),
    FAE (B+0x9C). An FA6 target is an ffna type-8 sound descriptor whose
    own chunk-0x1 list names the audio payloads (the type-8 hop,
    `mdlrefs.type8_deps`).
  * the wire half: `0x0056` names the definition's file, `0x0057` supplies
    geometry-bearing bodies. Which definitions need one is NOT taken from
    the wire here -- it is DERIVED from the archive, twice over (below).

THE ROLES, and what walks vs. what terminates:

  shell      the 0x0056 file id                       walked (type-2 model)
  body       a 0x0057 model id                        walked
  link       an FA8 target, RECURSIVE                 walked
  fae_model  an FAE target, recursive                 walked
  texture    an FA5 target                            terminal
  sound      an FA6 target (ffna type-8)              read for its chunk-0x1
  audio      a type-8 chunk-0x1 target                terminal
  fad        an FAD target                            terminal

A file can hold several roles (five of the 54-definition corpus's 1,393
files do -- shells that are other definitions' FA8 links). Model-role files
are walked once per resolution; every referenced id must resolve in
`file_id_table(raw=True)` -- client addressability, never our convenience
table -- and every walked container must decode, or the resolution records
a named problem. CLOSURE IS OUR ASSERTION, the same posture `skelfile.py`
and `mdlrefs.py` take: the client silently tolerates what we refuse to
pass over, so `closed` is a claim the artifact can refute.

TWO ROLES RIDE ON WEAKER EVIDENCE THAN THE REST, included and labeled
rather than silently dropped or silently kept:

  * `fad`: the FAD list is parsed into the geometry object (A+0xFC) but its
    consumer is unread (`studies/mdlrefs/FINDINGS.md` SS8.1) -- whether the
    client ever FETCHES the targets is UNVERIFIED. They are in the closure
    under their own role so a caller can filter.
  * `fae_model`: FAE is the n3E timed model-load event table's file list
    (U2, `studies/anim/FINDINGS.md`) -- a RUNTIME load, not a load-time
    one, so recursing into the targets is RECONSTRUCTION from "the same
    loader will be handed this id". Population 6 archive-wide; MEASURED
    2026-08-16: ZERO occur in the 54 live-capture closures.

THE COMPOSITED RULE IS DERIVED HERE, NOT ASSUMED. `needs_body` reads the
ARCHIVE -- the shell carries no 0xFA0 geometry chunk -- and the skeleton's
own flag (bit 0 = MODEL_SKELETON_FLAG_COMPOSITED, MdlBuild:1556, via
`skelfile.Skeleton.composited`) is measured independently per file;
`composited_violations()` lists every file where the two disagree
(MEASURED: 0 of 161 FA1 carriers across the 54 closures; 0 of 14,571
archive-wide in U1). The wire cross-check -- a definition gets a 0x0057
exactly when its shell needs one -- is `test_unitassembly.py`'s corpus
section: capture 20260807T143055 alone: 8/8 0x0056-only shells CARRY
geometry, 36/36 with-0x0057 shells LACK it; pooled over the three live
captures: 43/43 definitions with a 0x0057 have every body carrying
geometry (the study triple's third figure -- unitmodels SS5.4's "43/43" is
this pooled per-definition population, not a per-capture distinct-model
count; those are 33/33 and 40/40, also green).

ORIGIN DISCIPLINE. `definitions_from_captures` refuses to pool capture
directories whose `wire.jsonl` origins differ or are not the wanted one
(`toolkit/origin.py`, three-valued; UNKNOWN is not a synonym for either).
A closure figure pooled over our own server's captures and ArenaNet's
would be about neither -- same rule as every other pooled consumer.

MEASURED 2026-08-16 over the three keyed live captures (the U4 corpus run;
artifacts in `vault/research/unitassembly/2026-08-16-u4/`): 54/54 pooled
definitions resolve to closed, geometry-complete file sets -- 1,393
distinct files, set sizes 3 to 233 per definition (median 158), deep walk
~60 s. Per-role distinct: shell 32, body 40, link 134, texture 113,
sound 241, audio 830, fad 8, fae_model 0.

    python toolkit/mapdata/unitassembly.py --content hatcher
    python toolkit/mapdata/unitassembly.py --captures                # all 54
    python toolkit/mapdata/unitassembly.py --captures --definition 1471
    python toolkit/mapdata/unitassembly.py --file-id 116228 --model-id 116703
"""

import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, ffna_type, \
    file_id_table  # noqa: E402
import mdlrefs  # noqa: E402
import origin  # noqa: E402
import skelfile  # noqa: E402

# Roles. MODEL_ROLES get the full container walk (the cached loader's
# closure); the rest are terminals of the reference graph.
ROLE_SHELL = "shell"
ROLE_BODY = "body"
ROLE_LINK = "link"
ROLE_FAE = "fae_model"
ROLE_TEXTURE = "texture"
ROLE_SOUND = "sound"
ROLE_AUDIO = "audio"
ROLE_FAD = "fad"

MODEL_ROLES = frozenset((ROLE_SHELL, ROLE_BODY, ROLE_LINK, ROLE_FAE))
ALL_ROLES = MODEL_ROLES | frozenset(
    (ROLE_TEXTURE, ROLE_SOUND, ROLE_AUDIO, ROLE_FAD))

MODEL_FFNA_TYPE = mdlrefs.MODEL_FFNA_TYPE       # 2
SOUND_FFNA_TYPE = mdlrefs.SOUND_FFNA_TYPE       # 8


class AssemblyError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


class UnitDef:
    """One unit definition: the ids the wire (or a content row) declares.

    `file_id` is the 0x0056 shell file; `model_ids` the 0x0057 bodies (empty
    for a 0x0056-only definition such as the worm). `definition` is the
    slot index when known; `source` says where the ids came from, for
    reports -- it is a label, never a join key.
    """

    __slots__ = ("definition", "file_id", "model_ids", "source")

    def __init__(self, file_id, model_ids=(), definition=None, source="?"):
        if not isinstance(file_id, int):
            raise AssemblyError(
                f"a UnitDef needs an integer shell file id, got {file_id!r} "
                f"(source {source!r}). A definition without its 0x0056 file "
                f"id has nothing to resolve.")
        self.file_id = file_id
        self.model_ids = tuple(model_ids)
        self.definition = definition
        self.source = source

    @classmethod
    def from_content_row(cls, key, row):
        """From a `content/*.toml` npc row -- `file_id` required, `model_id`
        optional, exactly the split `content/npcs.toml` already ships (the
        worm has no model_id ON PURPOSE and inventing one is the guess its
        comment warns about)."""
        fid = row.get("file_id")
        if fid is None:
            raise AssemblyError(
                f"content row {key!r} has no file_id; nothing to resolve")
        models = (row["model_id"],) if row.get("model_id") is not None else ()
        return cls(fid, models, definition=row.get("definition"),
                   source=f"content:{key}")

    @classmethod
    def from_npcdef(cls, d):
        """From an `npcdefs.Definition` (the capture compiler's typed row).
        Uses the FULL 0x0057 list (`model_ids`), not just the first entry --
        two pooled definitions (1496/1497) carry two bodies each."""
        if not d.declared:
            raise AssemblyError(
                f"definition {d.index} was never declared by 0x0056 -- "
                f"created only; it has no file id to resolve")
        return cls(d.payload[0], tuple(d.model_ids or ()),
                   definition=d.index, source="capture")


class FileEntry:
    """One file in a closure: its roles and the facts read off it.

    `ffna`/`size` are None when the file was not read (a terminal under
    `deep=False` -- membership and resolvability are still checked).
    `has_geometry`/`composited`/`seq_count` are model-file facts;
    `composited` is None when the file carries no FA1 chunk.
    """

    __slots__ = ("file_id", "roles", "size", "ffna", "has_geometry",
                 "composited", "seq_count", "read")

    def __init__(self, file_id):
        self.file_id = file_id
        self.roles = set()
        self.size = None
        self.ffna = None
        self.has_geometry = None
        self.composited = None
        self.seq_count = None
        self.read = False

    def to_dict(self):
        return {"file_id": self.file_id, "roles": sorted(self.roles),
                "size": self.size, "ffna": self.ffna,
                "has_geometry": self.has_geometry,
                "composited": self.composited, "seq_count": self.seq_count}


class Resolution:
    """The closure for one UnitDef: files, problems, and the derived facts."""

    __slots__ = ("unit", "files", "problems", "null_slots")

    def __init__(self, unit):
        self.unit = unit
        self.files = {}
        self.problems = []      # (file_id, role, why) -- named, never skipped
        self.null_slots = 0     # FA5 null slots seen across the walk

    @property
    def closed(self):
        """Every referenced id resolved AND every walked container decoded."""
        return not self.problems

    @property
    def shell(self):
        return self.files.get(self.unit.file_id)

    @property
    def needs_body(self):
        """DERIVED from the archive, not from the wire: the shell carries no
        0xFA0 geometry chunk, so its geometry must arrive from elsewhere --
        which is what a 0x0057 is for. None when the shell could not be
        read. The skeleton's own COMPOSITED bit is the independent second
        witness; `composited_violations()` is where they could disagree."""
        sh = self.shell
        if sh is None or sh.has_geometry is None:
            return None
        return not sh.has_geometry

    @property
    def geometry_complete(self):
        """Someone in this set carries the definition's geometry: the shell
        itself, or every declared body."""
        sh = self.shell
        if sh is None or sh.has_geometry is None:
            return False
        if sh.has_geometry:
            return True
        bodies = [self.files.get(m) for m in self.unit.model_ids]
        return bool(bodies) and all(
            b is not None and b.has_geometry for b in bodies)

    def composited_violations(self):
        """Files where the FA1 flag bit and the FA0 chunk disagree -- the
        COMPOSITED equivalence (U1: 14,571/14,571) re-measured on exactly
        this closure's population. MEASURED empty on all 54 corpus
        definitions; a member here is a finding."""
        return [(f.file_id, f.composited, f.has_geometry)
                for f in self.files.values()
                if f.composited is not None
                and f.composited != (not f.has_geometry)]

    def role_counts(self):
        """{role: distinct files carrying it} -- a file with two roles
        counts once under each."""
        out = collections.Counter()
        for f in self.files.values():
            for r in f.roles:
                out[r] += 1
        return dict(out)

    def file_ids(self):
        return sorted(self.files)

    def to_dict(self):
        return {"definition": self.unit.definition,
                "source": self.unit.source,
                "shell": self.unit.file_id,
                "bodies": list(self.unit.model_ids),
                "closed": self.closed,
                "needs_body": self.needs_body,
                "geometry_complete": self.geometry_complete,
                "null_slots": self.null_slots,
                "problems": [list(p) for p in self.problems],
                "files": [self.files[fid].to_dict()
                          for fid in sorted(self.files)]}


class _Facts:
    """What one archive read yields, cached across resolutions."""

    __slots__ = ("size", "ffna", "has_geometry", "composited", "seq_count",
                 "refs", "type8_deps", "err")

    def __init__(self):
        self.size = self.ffna = None
        self.has_geometry = self.composited = self.seq_count = None
        self.refs = None
        self.type8_deps = None
        self.err = None


class Resolver:
    """Resolves UnitDefs against one archive, caching reads by file id --
    the same shape as the client's cached by-id loader (`0x00794260`)."""

    def __init__(self, archive_, table=None):
        self.ar = archive_
        # raw=True: what the CLIENT can address, never our dual-registered
        # convenience table -- the three-failure lesson in archive.py.
        self.table = table if table is not None else file_id_table(
            archive_, raw=True)
        self._facts = {}

    # -- one archive read, cached -------------------------------------------
    def facts(self, fid):
        """The measured facts for one file id, or None if the id does not
        resolve in `file_id_table(raw=True)`."""
        if fid in self._facts:
            return self._facts[fid]
        row = self.table.get(fid)
        if row is None:
            self._facts[fid] = None
            return None
        data = self.ar.read(self.ar.row(row))
        f = _Facts()
        f.size = len(data)
        f.ffna = ffna_type(data) if bytes(data[:4]) == b"ffna" else None
        if f.ffna == MODEL_FFNA_TYPE:
            try:
                f.has_geometry = skelfile.container_has_geometry(data)
                sk = skelfile.Skeleton.from_container(data)
                if sk is not None:
                    f.composited = sk.composited
                    f.seq_count = sk.seq_count
                f.refs = mdlrefs.ref_lists(data)
            except ValueError as e:      # skelfile/mdlrefs Undecodable too
                f.err = f"{type(e).__name__}: {e}"
        elif f.ffna == SOUND_FFNA_TYPE:
            try:
                deps = []
                for cid, off, size in ffna_chunks(data):
                    if cid == mdlrefs.TYPE8_DEP_CHUNK:
                        deps += mdlrefs.type8_deps(bytes(data[off:off + size]))
                f.type8_deps = deps
            except ValueError as e:
                f.err = f"{type(e).__name__}: {e}"
        self._facts[fid] = f
        return f

    # -- the closure walk ----------------------------------------------------
    def resolve(self, unit, deep=True):
        """The closed file set for one UnitDef.

        `deep=False` skips READING pure terminals (texture/audio/fad) --
        membership and id-resolvability are still checked, so `closed` means
        the same thing in both modes and the file SET is identical; what a
        shallow entry lacks is its size/ffna facts. Sound descriptors are
        always read (their chunk-0x1 is part of the closure); model-role
        files are always read (the walk needs their chunks).
        """
        seeds = [(unit.file_id, ROLE_SHELL)]
        seeds += [(m, ROLE_BODY) for m in unit.model_ids]
        return self.resolve_seeds(unit, seeds, deep=deep)

    def resolve_seeds(self, unit, seeds, deep=True):
        """The same walk from an EXPLICIT seed list of (file_id, role).

        Split out (behaviour-neutrally -- `resolve` above builds the exact
        queue it always built) so `playerassembly.py` can drive the identical
        closure from a CpsData manifest instead of a wire unit: the FA5/FAD
        terminals, the FA6 -> ffna-type-8 -> chunk-0x1 audio hop, the FA8
        links with the visited set, FAE and the null-slot accounting are all
        seed-independent; only WHO seeds the queue is monster-specific.
        `unit` is whatever the caller wants the Resolution to carry.

        A seed whose role is ROLE_TEXTURE or ROLE_FAD is a TERMINAL exactly
        as a chunk-referenced texture is: membership and id-resolvability
        checked, read under `deep`, never walked as a model. `resolve` never
        seeds one (shell and bodies are model roles), so unit resolution is
        byte-identical to the pre-split walk -- a player manifest seeds its
        record's ATEX slots this way. A ROLE_SOUND or ROLE_AUDIO seed is
        REFUSED rather than half-walked: the sound closure needs the FA6 hop
        that starts from a MODEL, and a caller seeding one directly is
        holding the walk wrong.
        """
        res = Resolution(unit)
        for _fid, role in seeds:
            if role in (ROLE_SOUND, ROLE_AUDIO):
                raise ValueError(
                    f"a {role!r} seed cannot be walked from here -- the "
                    f"audio closure hangs off a model's FA6 chunk; seed the "
                    f"model instead")
        queue = collections.deque(seeds)
        walked = set()

        def touch(fid, role, read):
            """Record fid under role; return its facts (None: unresolved)."""
            ent = res.files.get(fid)
            if ent is None:
                ent = res.files[fid] = FileEntry(fid)
            ent.roles.add(role)
            if fid not in self.table:
                res.problems.append(
                    (fid, role, "unresolved in file_id_table(raw=True)"))
                return None
            if not read:
                return True                       # resolvable, unread
            f = self.facts(fid)
            ent.read = True
            ent.size, ent.ffna = f.size, f.ffna
            ent.has_geometry = f.has_geometry
            ent.composited = f.composited
            ent.seq_count = f.seq_count
            return f

        while queue:
            fid, role = queue.popleft()
            if role in (ROLE_TEXTURE, ROLE_FAD):
                touch(fid, role, read=deep)   # a terminal seed: never walked
                continue
            f = touch(fid, role, read=True)
            if f is None:
                continue
            if fid in walked:
                continue          # the cache hit: roles recorded, walk once
            # Judged once too: a bad file queued under two roles must not
            # name its problem twice (the U4 review's dead-code sweep
            # caught the duplicate append the old ordering allowed).
            walked.add(fid)
            if f.ffna != MODEL_FFNA_TYPE:
                res.problems.append(
                    (fid, role, f"ffna type {f.ffna}, not the model type "
                                f"{MODEL_FFNA_TYPE}"))
                continue
            if f.err is not None:
                res.problems.append((fid, role, f.err))
                continue
            refs = f.refs
            for cid, trole in ((mdlrefs.TEXTURE_CHUNK, ROLE_TEXTURE),
                               (mdlrefs.FAD_CHUNK, ROLE_FAD)):
                if cid in refs:
                    for t in refs[cid].file_ids():
                        if t is None:
                            res.null_slots += 1
                            continue
                        touch(t, trole, read=deep)
            if mdlrefs.SOUND_CHUNK in refs:
                for s in refs[mdlrefs.SOUND_CHUNK].file_ids():
                    if s is None:
                        res.null_slots += 1
                        continue
                    sf = touch(s, ROLE_SOUND, read=True)
                    if sf is None:
                        continue
                    if sf.ffna != SOUND_FFNA_TYPE:
                        res.problems.append(
                            (s, ROLE_SOUND,
                             f"ffna type {sf.ffna}, not the sound-descriptor "
                             f"type {SOUND_FFNA_TYPE}"))
                        continue
                    if sf.err is not None:
                        res.problems.append((s, ROLE_SOUND, sf.err))
                        continue
                    for a in sf.type8_deps:
                        touch(a, ROLE_AUDIO, read=deep)
            if mdlrefs.LINK_CHUNK in refs:
                for l in refs[mdlrefs.LINK_CHUNK].file_ids():
                    if l is None:
                        res.null_slots += 1
                    else:
                        queue.append((l, ROLE_LINK))
            if mdlrefs.FAE_CHUNK in refs:
                for m in refs[mdlrefs.FAE_CHUNK].file_ids():
                    if m is None:
                        res.null_slots += 1
                    else:
                        queue.append((m, ROLE_FAE))
        return res


# ---------------------------------------------------------------------------
# The capture entry, behind the origin gate.
# ---------------------------------------------------------------------------

def require_one_origin(capture_dirs, want=origin.LIVE):
    """Every capture directory's wire.jsonl must classify as `want`, or
    refuse loudly. UNKNOWN is not a synonym for anything (`origin.py`), so
    an unclassifiable capture refuses too. Returns `want`.
    """
    got = []
    for cd in capture_dirs:
        who, why = origin.origin_of(os.path.join(cd, "wire.jsonl"))
        got.append((cd, who, why))
    kinds = {who for _cd, who, _why in got}
    if kinds != {want}:
        lines = [f"REFUSING to pool {len(capture_dirs)} capture(s) for an "
                 f"assembly figure: wanted origin {want!r}, found "
                 f"{sorted(kinds)}."]
        for cd, who, why in got:
            if who != want:
                lines.append(f"  {os.path.basename(cd)}: {who} -- {why}")
        lines.append("  A closure measured over two servers' captures is "
                     "about neither. Select one corpus explicitly.")
        raise AssemblyError("\n".join(lines))
    return want


def definitions_from_captures(capture_dirs, codec=None, want=origin.LIVE):
    """{definition index: UnitDef} from capture directories, pooled ONLY
    when every directory shares the wanted origin.

    The wire decode is `npcdefs.read` -- the committed extractor, with its
    interval join and its byte-exact framing refusals; this module adds
    nothing to the decode and takes the full 0x0057 list per definition
    (`Definition.model_ids`).
    """
    require_one_origin(capture_dirs, want=want)
    base = os.path.dirname(HERE)
    for sub in ("authsrv", "schema"):
        p = os.path.join(base, sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    import npcdefs                       # noqa: E402  (authsrv, lazy)
    if codec is None:
        from codec import Codec          # noqa: E402
        codec = Codec()
    defs, _intervals = npcdefs.read(capture_dirs, codec)
    return {i: UnitDef.from_npcdef(d)
            for i, d in defs.items() if d.declared}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_resolution(res, verbose=False):
    u = res.unit
    head = f"definition {u.definition}" if u.definition is not None else \
        f"file {u.file_id}"
    rc = res.role_counts()
    print(f"{head} ({u.source}): shell {u.file_id}"
          + (f" + bodies {list(u.model_ids)}" if u.model_ids else " (no 0x0057)")
          + f" -> {len(res.files)} files, "
          + ("CLOSED" if res.closed else f"{len(res.problems)} PROBLEM(S)")
          + f", needs_body={res.needs_body}"
          + f", geometry_complete={res.geometry_complete}")
    print("  roles: " + ", ".join(
        f"{r}:{rc[r]}" for r in ("shell", "body", "link", "fae_model",
                                 "texture", "sound", "audio", "fad")
        if rc.get(r)))
    for p in res.problems:
        print(f"  PROBLEM: file {p[0]} ({p[1]}): {p[2]}")
    bad = res.composited_violations()
    if bad:
        print(f"  COMPOSITED violations: {bad}")
    if verbose:
        for fid in res.file_ids():
            f = res.files[fid]
            facts = []
            if f.ffna is not None:
                facts.append(f"ffna {f.ffna}")
            if f.has_geometry is not None:
                facts.append("FA0" if f.has_geometry else "no FA0")
            if f.composited is not None:
                facts.append(f"COMPOSITED={f.composited}")
            print(f"    {fid:>9}  {','.join(sorted(f.roles)):<20} "
                  + (f"{f.size:>9} B  " if f.size is not None else
                     "   unread  ")
                  + " ".join(facts))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=None, help="archive path; default: the "
                    "study archive via vaultpath")
    ap.add_argument("--content", metavar="KEY",
                    help="resolve a content/*.toml npc row by key")
    ap.add_argument("--captures", action="store_true",
                    help="resolve every definition pooled from the keyed "
                         "live captures (origin-gated)")
    ap.add_argument("--definition", type=int, default=None,
                    help="with --captures: only this definition index, "
                         "verbose")
    ap.add_argument("--file-id", type=int, default=None,
                    help="resolve a raw shell file id")
    ap.add_argument("--model-id", type=int, action="append", default=[],
                    help="0x0057 body id(s) for --file-id; repeatable")
    ap.add_argument("--shallow", action="store_true",
                    help="do not read pure terminals (texture/audio/fad); "
                         "same file set, fewer facts")
    ap.add_argument("--dump", metavar="PATH",
                    help="write every resolution as JSONL (ids and counts "
                         "only -- measurements)")
    args = ap.parse_args(argv)

    units = []
    if args.content:
        sys.path.insert(0, os.path.dirname(HERE))
        import content                    # noqa: E402
        world = content.load()
        units.append(UnitDef.from_content_row(
            args.content, world.get("npc", args.content)))
    if args.file_id is not None:
        units.append(UnitDef(args.file_id, tuple(args.model_id),
                             source="cli"))
    if args.captures:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
        import npcdefs                    # noqa: E402
        defs = definitions_from_captures(npcdefs.live_captures())
        for i in sorted(defs):
            if args.definition is None or i == args.definition:
                units.append(defs[i])
    if not units:
        ap.error("nothing to resolve: pass --content, --captures or "
                 "--file-id")

    if args.dat is None:
        import vaultpath                  # noqa: E402
        args.dat = os.path.join(
            vaultpath.require_dir("dat_study", why="unitassembly CLI"),
            "Gw.dat")
    verbose = len(units) == 1
    dump = open(args.dump, "w", encoding="utf-8") if args.dump else None
    with Archive(args.dat) as ar:
        r = Resolver(ar)
        n_closed = 0
        for u in units:
            res = r.resolve(u, deep=not args.shallow)
            n_closed += res.closed
            _print_resolution(res, verbose=verbose)
            if dump:
                import json
                dump.write(json.dumps(res.to_dict()) + "\n")
    if dump:
        dump.close()
        print(f"wrote {args.dump}")
    print(f"\n{n_closed}/{len(units)} closed")
    return 0 if n_closed == len(units) else 1


if __name__ == "__main__":
    sys.exit(main())
