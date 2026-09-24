r"""The wire-derived shell index: which skeleton every live tape dressed with
which bodies, keyed per connection, stamped by the corpus. READ ONLY.

    python toolkit/mapdata/wireshells.py --build          # decode every keyed tape
    python toolkit/mapdata/wireshells.py --shell 116228   # one shell's bodies
    python toolkit/mapdata/wireshells.py --body 116703    # one body's shells
    python toolkit/mapdata/wireshells.py --summary

WHY THE WIRE. `Gw.dat` never pairs a creature shell with the body that dresses
it -- `modelcatalog`'s docstring records the two archive-side tells that were
tried and refuted (the COMPOSITED flag, FA8 linkage). The client learns the
pairing per definition from two messages: `0x0056 NPC_UPDATE_PROPERTIES`
names the definition's shell file (plus its scale, flags, profession, level
and the string ids of its name), and `0x0057 MONSTER_COMPOSITE` names the
body files that dress it. Those messages exist only in captures, and the
owner's live tapes hold every definition ArenaNet's server declared during
those sessions. This module is that corpus, inverted: shell -> bodies, with
every sighting's capture and connection kept, so a reader can see how often
and where a pairing was observed rather than take a count on faith.

KEYED PER CONNECTION, BECAUSE A DEFINITION INDEX IS NOT A GLOBAL NAME --
MEASURED 2026-09-14, the first time the whole 19-tape corpus was pooled.
`npcdefs.read` pools captures by definition index and refuses when one index
is declared with two payloads; on the three-tape corpus that never fired
(126/126), so the index looked global. Over 19 tapes it fires: definition
7809 is a level-5 creature on shell 141285 in one session and a level-20 one
on shell 16271 in another. The corpus says how close to global the slots
are -- 332 of 333 indices name ONE shell across every connection they appear
in, so the table is stable across sessions of the same content and the one
exception is two different maps sharing a number -- and one exception is
enough: a pooled-by-index reading is a 332/333 approximation, and this
module does not take it. (CORRECTED 2026-09-24, DESKWORK-Q1: the exception is
a CROSS-BUILD drift, not two maps -- 7809 is the level-5 creature in the
2026-07-29 client build and the level-20 one in the 2026-09-01 build, each
capture's build read off its own manifest exe; SUITE-FIXES, 2026-09-16,
`npcdefs.capture_build`. The keying below is right either way.) A SIGHTING is (capture, connection, index), and the
pairing it records is the shell and bodies declared FOR THAT SLOT IN THAT
CONNECTION. Within one connection a repeat declaration must still agree
byte-for-byte -- the refusal `npcdefs` carries, kept, because a slot that
changes mid-connection would be a real finding and not something to average.

WHAT THE INDEX ASSERTS AND WHAT THE ARCHIVE CAN REFUTE. Every shell that was
ever given a 0x0057 should be a geometry-less head in the archive, and every
shell declared WITHOUT one should carry its own geometry -- the composited
equivalence the unitmodels arc measured on 8/8 and 36/36 definitions, now
re-measurable over the whole corpus through `modelcatalog`'s kinds
(`crosscheck`). Every body should be a `model` head. `test_wireshells.py`
pins these as N-of-N checks; a disagreement is a finding about the wire or
the archive, and it is printed by shell id rather than averaged away.

THE CORPUS IS STAMPED. The index is a JSON file under
`vault/cache/modelcatalog/`, keyed by a digest over every keyed tape's name,
connection files and their sizes. A new tape, or a re-keyed one, changes the
digest and the stale index is refused and rebuilt (the `modelcatalog` /
`refindex` rule). Tapes with NO decrypted game channel are listed by name in
`skipped` so the count of what the index rests on is never silently smaller
than the vault. Origin is gated: every tape must classify `live`
(`unitassembly.require_one_origin`) -- our own server's captures pair shells
with bodies WE chose, and an index that mixed them would be citing ourselves.

WHAT IS RECORDED PER SHELL: bodies (file id -> sightings), the name string-id
tuples the wire attached (ids only, never text -- CLAUDE.md's rule; the
client resolves them at run time), professions, levels, flags, scale words,
how many creates each connection spawned of it. Names are how a reader joins
a shell to a `content/npcs.toml` row that a client run has already named.
"""

import argparse
import collections
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
for _p in (PARENT, os.path.join(PARENT, "authsrv"), os.path.join(PARENT, "schema")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import vaultpath  # noqa: E402
import origin  # noqa: E402

NPC_PROPERTIES = 0x0056         # npcdefs.NPC_PROPERTIES -- the definition itself
MONSTER_COMPOSITE = 0x0057      # npcdefs.MONSTER_COMPOSITE -- its body files
CREATE_AGENT = 0x0020           # npcdefs.CREATE_AGENT
NPC_CLASS_TAG = 0x2             # npcdefs.NPC_CLASS_TAG (field 2's top nibble)
DEFINITION_MASK = 0xFFFF

FORMAT_VERSION = 1


class WireShellsError(Exception):
    """A refusal with its reason; never a silent partial index."""


class Refused(SystemExit):
    """A cache that must not be used."""


# ---------------------------------------------------------------------------
# one connection -> sightings (pure over a decoded message list)
# ---------------------------------------------------------------------------

def collect_connection(msgs, capture, connection):
    """`[(t, opcode, values)]` -> `{index: sighting dict}` for ONE connection.

    A sighting carries the 0x0056 payload split into named fields, the
    0x0057 body list (empty when none was sent), and the create count. A
    second 0x0056 or 0x0057 for the same index inside the connection must
    agree byte-for-byte or this refuses -- `npcdefs.declare`'s posture.
    Pure: no I/O, so the test drives it on lists it builds.
    """
    out = {}

    def slot(index):
        return out.setdefault(index, {
            "capture": capture, "connection": connection, "definition": index,
            "shell": None, "bodies": [], "scale": None, "flags": None,
            "profession": None, "level": None, "name": None, "creates": 0,
            "declared": False, "composite": False})

    for _t, opcode, values in msgs:
        if opcode == NPC_PROPERTIES:
            # [definition, file_id, 0, scale, 0, flags, profession, level, name]
            index = values[1]
            payload = {"shell": values[2], "scale": values[4], "flags": values[6],
                       "profession": values[7], "level": values[8],
                       "name": [ord(ch) for ch in values[9]]}
            s = slot(index)
            if s["declared"]:
                prev = {k: s[k] for k in payload}
                if prev != payload:
                    raise WireShellsError(
                        f"{capture} {connection}: definition {index} declared twice "
                        f"with different payloads inside ONE connection:\n  {prev}\n"
                        f"  {payload}\nA slot changing mid-connection is a finding, "
                        f"not a merge conflict -- do not pick one.")
                continue
            s.update(payload)
            s["declared"] = True
        elif opcode == MONSTER_COMPOSITE:
            index = values[1]
            models = list(values[2]) if isinstance(values[2], list) else [values[2]]
            s = slot(index)
            if s["composite"] and s["bodies"] != models:
                raise WireShellsError(
                    f"{capture} {connection}: definition {index} given two different "
                    f"0x0057 lists ({s['bodies']}, {models}) inside one connection.")
            s["bodies"] = models
            s["composite"] = True
        elif opcode == CREATE_AGENT:
            tagged = values[2]
            if (tagged >> 28) != NPC_CLASS_TAG:
                continue
            slot(tagged & DEFINITION_MASK)["creates"] += 1
    # a slot that was only created, never declared, names no shell -- it is
    # kept (its creates say the session used it) but carries shell None
    return out


# ---------------------------------------------------------------------------
# the corpus
# ---------------------------------------------------------------------------

def keyed_tapes():
    """`(with_channels, without)` -- every live capture directory, split by
    whether a decrypted game channel exists in it. Both lists, always: the
    ones without are what the index does NOT rest on, and they are named."""
    root = vaultpath.require_dir("captures", "live",
                                 why="the wire-derived shell index reads live tapes")
    with_ch, without = [], []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if any(f.startswith("game-") and f.endswith(".jsonl") for f in os.listdir(path)):
            with_ch.append(path)
        else:
            without.append(name)
    return with_ch, without


def corpus_stamp(capture_dirs, skipped):
    """The corpus identity: every keyed tape's channel files and sizes."""
    h = hashlib.sha256()
    rows = []
    for cd in capture_dirs:
        for f in sorted(os.listdir(cd)):
            if f.startswith("game-") and f.endswith(".jsonl"):
                size = os.path.getsize(os.path.join(cd, f))
                rows.append((os.path.basename(cd), f, size))
    for name, f, size in rows:
        h.update(f"{name}/{f}:{size}\n".encode())
    return {"captures": [os.path.basename(cd) for cd in capture_dirs],
            "channels": len(rows), "skipped": list(skipped),
            "sha256": h.hexdigest()}


def build(capture_dirs=None, skipped=None, progress=None):
    """Decode every keyed live tape, per connection, into an `Index`.

    `skipped` names the tapes WITHOUT a decrypted channel so the stamp can
    carry them; when `capture_dirs` is None both come from `keyed_tapes()`.
    """
    import unitassembly                  # noqa: E402  (origin gate, lazy)
    import tape                          # noqa: E402  (authsrv)
    from codec import Codec              # noqa: E402  (schema)
    if capture_dirs is None:
        capture_dirs, skipped = keyed_tapes()
    skipped = list(skipped or [])
    unitassembly.require_one_origin(capture_dirs, want=origin.LIVE)
    codec = Codec()
    sightings = []
    connections = 0
    for n, cd in enumerate(capture_dirs, 1):
        if progress:
            progress(n, len(capture_dirs), os.path.basename(cd))
        for row in tape.channel_files(cd):
            connection = row["connection"]
            info, events = tape.load_tape(cd, connection)
            capture = info.get("capture") or os.path.basename(cd)
            msgs, (consumed, total, err) = tape.decode_all(events, codec, "GAME_SMSG", 0)
            if err is not None or consumed != total:
                raise WireShellsError(
                    f"{capture} {connection} did not frame to its final byte "
                    f"({consumed}/{total}, {err}); a partial decode would drop every "
                    f"definition after the break and nothing would say so.")
            connections += 1
            sightings.extend(collect_connection(msgs, capture, connection).values())
    return Index(corpus_stamp(capture_dirs, skipped), sightings, connections)


class Index:
    """Every sighting, and the shell -> bodies / body -> shells inversions."""

    def __init__(self, stamp, sightings, connections):
        self.stamp = stamp
        self.sightings = list(sightings)
        self.connections = connections
        self.shells = {}                  # shell fid -> ShellRecord
        self.body_shells = {}             # body fid -> set(shell fid)
        for s in self.sightings:
            if s["shell"] is None:
                continue
            rec = self.shells.setdefault(s["shell"], ShellRecord(s["shell"]))
            rec.add(s)
            for b in s["bodies"]:
                self.body_shells.setdefault(b, set()).add(s["shell"])

    def declared(self):
        return [s for s in self.sightings if s["shell"] is not None]

    def pairs(self):
        """Every distinct (shell, body) the wire ever declared together."""
        return sorted({(s["shell"], b) for s in self.declared() for b in s["bodies"]})

    def summary(self):
        d = self.declared()
        return {"captures": len(self.stamp["captures"]),
                "skipped": len(self.stamp["skipped"]),
                "connections": self.connections,
                "sightings": len(self.sightings), "declared": len(d),
                "with_bodies": sum(1 for s in d if s["bodies"]),
                "shells": len(self.shells), "pairs": len(self.pairs()),
                "bodies": len(self.body_shells)}

    def to_dict(self):
        return {"format_version": FORMAT_VERSION, "stamp": self.stamp,
                "connections": self.connections, "sightings": self.sightings}

    @classmethod
    def from_dict(cls, d):
        return cls(d["stamp"], d["sightings"], d["connections"])


class ShellRecord:
    """One shell as the wire used it, across every sighting."""

    def __init__(self, fid):
        self.fid = fid
        self.sightings = []
        self.bodies = collections.OrderedDict()   # body fid -> [sightings]
        self.names = collections.Counter()        # tuple of string ids -> count
        self.professions = collections.Counter()
        self.levels = collections.Counter()
        self.captures = set()
        self.creates = 0
        self.without_body = 0

    def add(self, s):
        self.sightings.append(s)
        self.captures.add(s["capture"])
        self.creates += s["creates"]
        self.names[tuple(s["name"])] += 1
        self.professions[s["profession"]] += 1
        self.levels[s["level"]] += 1
        if s["bodies"]:
            for b in s["bodies"]:
                self.bodies.setdefault(b, []).append(s)
        else:
            self.without_body += 1

    @property
    def needs_body(self):
        """True when every sighting brought a 0x0057, False when none did,
        None when the wire was inconsistent about it (a finding)."""
        with_b = sum(1 for s in self.sightings if s["bodies"])
        if with_b == len(self.sightings):
            return True
        if with_b == 0:
            return False
        return None

    def describe(self, names_of=None):
        lines = [f"shell {self.fid} (0x{self.fid:X}): {len(self.sightings)} sighting(s) "
                 f"in {len(self.captures)} capture(s), {self.creates} create(s), "
                 f"needs_body={self.needs_body}"]
        for b, ss in self.bodies.items():
            caps = sorted({s['capture'] for s in ss})
            tag = f"  body {b} (0x{b:X}): {len(ss)} sighting(s), {len(caps)} capture(s)"
            if names_of:
                nm = names_of(b)
                if nm:
                    tag += f"  = {nm}"
            lines.append(tag)
        lines.append(f"  names (string ids): {len(self.names)} distinct; professions "
                     f"{dict(self.professions)}; levels {dict(self.levels)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------

def cache_path(stamp):
    return os.path.join(vaultpath.vault_path("cache", "modelcatalog"),
                        f"wireshells-{stamp['sha256'][:16]}.json")


def save(index, path=None):
    path = path or cache_path(index.stamp)
    try:
        out = vaultpath.resolve_out(path, what="the wire shell index")
    except ValueError as exc:
        raise Refused(str(exc))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(index.to_dict(), fh)
    os.replace(tmp, out)
    return out


def load(path, stamp=None):
    """Read an index; with `stamp`, refuse one built from another corpus."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"could not read {path}: {type(exc).__name__}: {exc}")
    if not isinstance(doc, dict) or doc.get("format_version") != FORMAT_VERSION:
        raise Refused(f"{path} is not a format_version {FORMAT_VERSION} wire index")
    try:
        idx = Index.from_dict(doc)
    except (KeyError, TypeError, ValueError) as exc:
        raise Refused(f"{path} is malformed: {type(exc).__name__}: {exc}")
    if stamp is not None and idx.stamp.get("sha256") != stamp["sha256"]:
        raise Refused(
            f"REFUSING the wire index {path}: built over a different corpus\n"
            f"  index: {len(idx.stamp.get('captures', []))} tapes, "
            f"{idx.stamp.get('channels')} channels, {idx.stamp.get('sha256', '')[:16]}\n"
            f"  vault: {len(stamp['captures'])} tapes, {stamp['channels']} channels, "
            f"{stamp['sha256'][:16]}\n  Rebuild:  python toolkit/mapdata/wireshells.py --build")
    return idx


def open_index(progress=None, rebuild=False):
    """The cached index for the vault's current keyed tapes, or a fresh build."""
    with_ch, without = keyed_tapes()
    stamp = corpus_stamp(with_ch, without)
    path = cache_path(stamp)
    if not rebuild and os.path.isfile(path):
        try:
            return load(path, stamp), path, False
        except Refused:
            pass
    idx = build(with_ch, skipped=without, progress=progress)
    return idx, save(idx, path), True


# ---------------------------------------------------------------------------
# the archive cross-check
# ---------------------------------------------------------------------------

def crosscheck(index, catalog):
    """The composited equivalence over the whole corpus, through the catalog.

    Returns a dict of lists: `body_ok`/`body_bad` (every body fid must be a
    `model` head), `shell_skel_ok`/`shell_skel_bad` (a shell that was ever
    given a 0x0057 must be geometry-less), `shell_geom_ok`/`shell_geom_bad`
    (a shell never given one must carry geometry), `unresolved` (ids the
    archive's table does not hold), `inconsistent` (shells the wire sometimes
    dressed and sometimes did not). Each `bad` entry names the id and what
    the catalog says, so a disagreement is a line, not a fraction.
    """
    import modelcatalog as mc
    out = collections.defaultdict(list)
    for body in sorted(index.body_shells):
        rec = catalog.by_fid.get(body)
        if rec is None:
            out["unresolved"].append(("body", body))
        elif rec.kind == mc.KIND_MODEL:
            out["body_ok"].append(body)
        else:
            out["body_bad"].append((body, rec.kind))
    for fid, sh in sorted(index.shells.items()):
        rec = catalog.by_fid.get(fid)
        if rec is None:
            out["unresolved"].append(("shell", fid))
            continue
        nb = sh.needs_body
        if nb is None:
            out["inconsistent"].append(fid)
        elif nb:
            (out["shell_skel_ok"] if rec.kind == mc.KIND_SKEL
             else out["shell_skel_bad"]).append(fid if rec.kind == mc.KIND_SKEL
                                                else (fid, rec.kind))
        else:
            (out["shell_geom_ok"] if rec.kind == mc.KIND_MODEL
             else out["shell_geom_bad"]).append(fid if rec.kind == mc.KIND_MODEL
                                                else (fid, rec.kind))
    return dict(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true", help="decode every keyed tape and (re)write the cache")
    ap.add_argument("--shell", default=None, help="one shell file id")
    ap.add_argument("--body", default=None, help="one body file id")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--crosscheck", action="store_true",
                    help="the composited equivalence through the model catalog")
    args = ap.parse_args(argv)

    t0 = time.time()
    idx, path, fresh = open_index(
        progress=lambda n, t, name: print(f"  {n}/{t} {name}"), rebuild=args.build)
    print(f"wire index: {'built' if fresh else 'loaded'} in {time.time() - t0:.1f} s -> {path}")
    if args.summary or args.build:
        print(f"  {idx.summary()}")
        print(f"  skipped (no decrypted game channel): {idx.stamp['skipped']}")
    if args.shell:
        fid = int(args.shell, 0)
        sh = idx.shells.get(fid)
        print(sh.describe() if sh else f"shell {fid}: never declared on the wire")
    if args.body:
        fid = int(args.body, 0)
        print(f"body {fid}: shells {sorted(idx.body_shells.get(fid, ()))}")
    if args.crosscheck:
        from archive import Archive
        import modelcatalog as mc
        with Archive() as ar:
            cat, _p, _f = mc.open_catalog(ar)
        cc = crosscheck(idx, cat)
        for k in sorted(cc):
            v = cc[k]
            print(f"  {k:16} {len(v)}" + (f"  {v[:6]}" if k.endswith("bad") or k in
                                          ("unresolved", "inconsistent") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
