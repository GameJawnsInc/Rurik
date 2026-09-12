"""Check the archive COMPOSER, `compose.py` -- SLICE-B9's one archive.

WHAT THIS FILE IS FOR. `compose.py` is an orchestrator over two client-proven
writers (`textwrite.py`, `deploy.py`) and writes nothing itself, so this does
not re-check either of them. It checks the things that are only true of the
composition:

  * **The record a string goes in is DERIVED from its consumer's wire words**,
    never typed. Section 1 drives that derivation over a synthetic world and
    requires it to refuse every shape that is not one authored record in our
    file: a retail name (several ids), an id in ArenaNet's own file, the
    identity tier, a consumer that does not exist, two consumers disagreeing
    about one record.
  * **The shipped manifest loads from the repo alone.** Section 2 loads
    `content/compose.toml` with the vault overlay OFF and derives its records,
    because a manifest that only resolves against a vault row dies on a bare
    machine -- the same check `test_quests` §21 makes of the giver's template.
  * **The launch recipe points BOTH halves at the composed archive.** Section 3
    reads the recipe text for `RURIK_DAT` and for the exe beside the archive,
    the two facts `deploy.launch`'s comment says a run cannot do without.
  * **`--fresh` removes exactly what a build leaves.** Section 4 checks the
    product list is by NAME -- the area's four files and this tool's own
    journals -- and nothing else in the directory.

No vault, no archive, no client.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (HERE, TOOLKIT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import checks                                                    # noqa: E402
import compose                                                   # noqa: E402
import content as content_mod                                    # noqa: E402
import codedstr                                                  # noqa: E402
import textwrite                                                 # noqa: E402

# MEASURED from a green run, 2026-09-12. No optional section, so one number.
LEDGER = checks.Ledger("archive composer", floor=24)
check = checks.adopt(LEDGER)


class FakeWorld:
    def __init__(self, tables):
        self._t = tables

    def get(self, kind, key):
        try:
            return self._t[kind][key]
        except KeyError:
            raise KeyError(f"no {kind} row {key!r}")

    def rows(self, kind):
        return dict(self._t.get(kind, {}))


def refused(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except compose.Refused as exc:
        return str(exc)
    return None


def section1():
    print("\n1. the record is DERIVED from the consumer's enc_name")
    lo = compose.FILE_LO
    world = FakeWorld({
        "quest": {
            "ours": {"enc_name": codedstr.encode_id(lo + 200)},
            "retail": {"enc_name": [0x3D64]},            # 'Ascalon', file 15
            "nameless": {"enc_name": []},
        },
        "npc": {
            "boss": {"enc_name": codedstr.encode_id(lo + 201)},
            "fisk": {"enc_name": [3914, 61387, 52282, 21632]},
            "identity": {"enc_name": codedstr.encode_id(lo + 3)},
        },
        "area": {}, "map": {},
    })
    recs = compose.string_records(world, {"strings": [
        {"quest": "ours", "text": "A First Errand"},
        {"npc": "boss", "text": "The Plague Worm"},
    ]})
    check([(r.record, r.text) for r in recs]
          == [(200, "A First Errand"), (201, "The Plague Worm")],
          "a quest and an npc each land on the record their OWN enc_name "
          "denotes -- 200 and 201, from the words, not from the manifest",
          [(r.record, r.string_id) for r in recs])
    check(recs[0].string_id == lo + 200
          and codedstr.encode_id(recs[0].string_id) == world.get("quest", "ours")["enc_name"],
          "and the string id round-trips to the exact words the server sends")

    why = refused(compose.string_records, world,
                  {"strings": [{"npc": "fisk", "text": "Somebody Else"}]})
    check(why and "RETAIL" in why,
          "a RETAIL name -- four opaque ids -- is REFUSED, not overwritten",
          (why or "")[:90])
    why = refused(compose.string_records, world,
                  {"strings": [{"quest": "retail", "text": "x"}]})
    check(why and "text file 15" in why,
          "an id in ArenaNet's own text file (0x3D64 -> file 15) is refused: "
          "textwrite only writes file 98", (why or "")[:90])
    why = refused(compose.string_records, world,
                  {"strings": [{"npc": "identity", "text": "x"}]})
    check(why and "IDENTITY" in why,
          "the identity tier (records 0..%d) is refused by name"
          % (textwrite.FIRST_FREE_RECORD - 1), (why or "")[:90])
    why = refused(compose.string_records, world,
                  {"strings": [{"quest": "no_such", "text": "x"}]})
    check(why and "does not exist" in why,
          "a consumer nothing defines is refused: a string with no consumer is "
          "one nothing will ever send", (why or "")[:90])
    why = refused(compose.string_records, world,
                  {"strings": [{"quest": "nameless", "text": "x"}]})
    check(why and "no enc_name" in why,
          "a consumer with no enc_name is refused -- there is no record to derive")
    why = refused(compose.string_records, world,
                  {"strings": [{"quest": "ours", "npc": "boss", "text": "x"}]})
    check(why and "exactly one consumer" in why,
          "an entry naming two consumers is refused rather than picking one")
    why = refused(compose.string_records, world,
                  {"strings": [{"quest": "ours", "text": "A"},
                               {"quest": "ours", "text": "B"}]})
    check(why and "different text" in why,
          "two entries at one record with DIFFERENT text are refused")
    recs = compose.string_records(world, {"strings": [
        {"quest": "ours", "text": "A"}, {"quest": "ours", "text": "A"}]})
    check(len(recs) == 1 and "quest.ours + quest.ours" in recs[0].consumer,
          "but two entries agreeing on one record collapse to one write, "
          "with both consumers named", recs[0].consumer)
    why = refused(compose.string_records, world,
                  {"strings": [{"quest": "ours", "text": "   "}]})
    check(why and "empty" in why, "empty text is refused")


def section2():
    print("\n2. the shipped manifest resolves from the REPO ALONE")
    world = content_mod.load(vault_dir="")
    row = compose.manifest(world, "slice")
    recs = compose.string_records(world, row)
    check(recs and all(r.record >= textwrite.FIRST_FREE_RECORD for r in recs),
          "[compose.slice] derives %d record(s), every one above the identity "
          "tier, with the vault overlay OFF" % len(recs),
          [(r.record, r.text, r.consumer) for r in recs])
    q = world.get("quest", "rurik_first_errand")
    sid, used = codedstr.decode_id(list(q["enc_name"]))
    check(any(r.string_id == sid for r in recs),
          "and the first errand's committed varint names one of them -- the "
          "manifest and quests.toml agree because the manifest READS it",
          sid)
    for a in row.get("areas") or []:
        area = world.get("area", a)
        m = world.get("map", str(int(area["map_id"])))
        check(bool(m.get("created")),
              f"area {a!r} rides a CREATED map row ({area['map_id']}), so a "
              f"build allocates rather than displacing a retail map",
              hex(int(m["file_id"])))
    why = refused(compose.manifest, world, "no_such_composition")
    check(why and "no [compose.no_such_composition]" in why,
          "an unknown composition is refused by name")


def section3():
    print("\n3. the launch recipe points BOTH halves at the composed archive")
    world = content_mod.load(vault_dir="")
    row = compose.manifest(world, "slice")
    recs = compose.string_records(world, row)
    lines = compose.launch_recipe(world, "slice", row, recs)
    dat = compose.dat_path("slice")
    exe = compose.exe_path("slice")
    check(any("RURIK_DAT" in ln and dat in ln for ln in lines),
          "the recipe sets RURIK_DAT to THIS archive, so the server paths "
          "against the mesh the client draws", lines[0])
    check(all(exe in ln for ln in lines if "session.py" in ln),
          "and every launch line names the exe BESIDE that archive -- the "
          "client that owns it, per deploy.py's first-run defect")
    check(os.path.dirname(dat) == os.path.dirname(exe)
          and os.path.basename(os.path.dirname(dat)) == "slice",
          "exe and archive share the run directory vault/run/slice",
          os.path.dirname(dat))
    check(all("--area " in ln and "--map " in ln for ln in lines
              if "session.py" in ln),
          "each area's line pins the run to its map AND names the area, so "
          "the zone is populated rather than empty ground")


def section4():
    print("\n4. --fresh removes exactly what a build leaves, by name")
    row = {"areas": ["frontier"]}
    names = [os.path.basename(p) for p in compose.products("slice", row)]
    want = ["frontier.bin", "frontier_alloc.json", "frontier_baseline.json",
            "frontier_rebloat.json"]
    check(names[:4] == want,
          "an area's four build products are listed by name", names[:4])
    check(all(n.startswith("slice_text_") and n.endswith(".journal")
              for n in names[4:]),
          "and anything else listed is this tool's own text journal",
          names[4:])
    check("Gw.exe" not in names and "Gw.dat" not in names,
          "the client and the archive are NOT products -- --fresh re-copies "
          "the archive on its own line and never touches the exe")
    why = refused(compose.manifest, FakeWorld({"compose": {
        "a/b": {"dat_source": "x", "areas": []}}}), "a/b")
    check(why and "directory name" in why,
          "a composition name with a path separator is refused: the run "
          "directory is vault/run/<name> and nothing outside it")
    why = refused(compose.manifest, FakeWorld({"compose": {
        "nosrc": {"areas": []}}}), "nosrc")
    check(why and "dat_source" in why,
          "a row without dat_source is refused -- the pristine archive is "
          "named, never assumed")


def main():
    section1()
    section2()
    section3()
    section4()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
