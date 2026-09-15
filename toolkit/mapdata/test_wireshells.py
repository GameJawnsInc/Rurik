r"""The wire-derived shell index: per-connection sightings, the corpus stamp,
and the composited equivalence re-measured over every keyed live tape.

    python toolkit/mapdata/test_wireshells.py

THE HEADLINE IS A CHECK THE ARCHIVE COULD REFUTE, AT CORPUS SCALE. The
unitmodels arc measured on three tapes that a shell given a `0x0057` body has
no geometry of its own (36/36) and a shell given none carries it (8/8).
Section 2 re-measures that over the whole index through `modelcatalog`'s
kinds -- every body a `model` head, every dressed shell a `skel` head, every
undressed shell a `model` -- and prints any disagreement BY ID. Fractions are
refused; a shell that the wire sometimes dressed and sometimes did not is
listed as inconsistent rather than rounded.

THE SLOT FINDING IS PINNED. A definition index is not a global name: 332 of
333 indices name one shell across every connection, and 7809 names two (a
level-5 creature on shell 141285 in one tape, a level-20 one on shell 16271
in another) -- which is why this index keys sightings by (capture,
connection, definition) and why `npcdefs.read`'s pooled-by-index reading
refuses the 19-tape corpus. Section 0 drives that on synthetic message lists -- a repeat
inside ONE connection must agree (refused otherwise), a repeat across two
connections may differ -- and section 2 pins the real 7809.

CONTENT ROWS ARE A SUBSET OF THE WIRE, BY CONSTRUCTION, AND THE TEST SAYS SO.
Every `content/npcs.toml` row's (shell, body) pair was compiled from a
capture, so every one must appear in the index: 40 pairs and 9 shell-only
rows. A row the index lacks would mean a row rests on a tape the vault no
longer holds, and that is worth a red.
"""

import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import wireshells as ws  # noqa: E402
import modelcatalog as mc  # noqa: E402
import vaultpath  # noqa: E402
import checks  # noqa: E402

LEDGER = checks.Ledger("wire shell index", floor=33)
check = checks.adopt(LEDGER)

HATCHER_SHELL, HATCHER_BODY, WORM = 116228, 116703, 116366


# ---------------------------------------------------------------------------
# 0. collect_connection on synthetic messages
# ---------------------------------------------------------------------------

def _declare(index, shell, level=1, name="ab", prof=3, flags=0x20C, scale=0x64000000):
    return (0.0, ws.NPC_PROPERTIES, [0, index, shell, 0, scale, 0, flags, prof, level, name])


def _composite(index, bodies):
    return (0.0, ws.MONSTER_COMPOSITE, [0, index, list(bodies)])


def _create(index, agent=5):
    return (0.0, ws.CREATE_AGENT, [0, agent, (ws.NPC_CLASS_TAG << 28) | index] + [0] * 10)


def section0():
    print("\n0. collect_connection")
    msgs = [_declare(7, 116228), _composite(7, [116703]), _create(7), _create(7),
            _declare(9, 116366), _create(9),
            (0.0, ws.CREATE_AGENT, [0, 77, (0x1 << 28) | 7] + [0] * 10)]   # a player create
    out = ws.collect_connection(msgs, "capA", "game-1")
    check(set(out) == {7, 9}, "one slot per declared definition; a player create adds none")
    s = out[7]
    check(s["shell"] == 116228 and s["bodies"] == [116703] and s["creates"] == 2
          and s["name"] == [97, 98] and s["level"] == 1 and s["declared"] and s["composite"],
          "a dressed slot carries shell, bodies, creates and the name's string ids")
    check(out[9]["bodies"] == [] and out[9]["composite"] is False and out[9]["creates"] == 1,
          "an undressed slot has an empty body list and says no 0x0057 came")
    out = ws.collect_connection([_declare(7, 116228), _declare(7, 116228)], "c", "g")
    check(out[7]["shell"] == 116228, "a byte-identical repeat inside a connection is accepted")
    try:
        ws.collect_connection([_declare(7, 116228), _declare(7, 141285, level=5)], "c", "g")
        ok = False
    except ws.WireShellsError as exc:
        ok = "ONE connection" in str(exc)
    check(ok, "a DIFFERENT repeat inside one connection is refused, not merged")
    try:
        ws.collect_connection([_composite(7, [1]), _composite(7, [2])], "c", "g")
        ok = False
    except ws.WireShellsError:
        ok = True
    check(ok, "two different 0x0057 lists for one slot in one connection are refused")
    a = ws.collect_connection([_declare(7809, 141285, level=5)], "capA", "g1")
    b = ws.collect_connection([_declare(7809, 16271, level=20)], "capB", "g2")
    idx = ws.Index({"captures": ["capA", "capB"], "channels": 2, "skipped": [],
                    "sha256": "0" * 64}, list(a.values()) + list(b.values()), 2)
    check(len(idx.shells) == 2 and idx.summary()["declared"] == 2,
          "the SAME index in two connections is two sightings of two shells -- "
          "slots are per session, never pooled by number")
    out = ws.collect_connection([_create(3)], "c", "g")
    check(out[3]["shell"] is None and out[3]["creates"] == 1,
          "a created-but-never-declared slot is kept with shell None")


# ---------------------------------------------------------------------------
# 1. the Index, its inversions, and the cache
# ---------------------------------------------------------------------------

def section1():
    print("\n1. Index and cache")
    a = ws.collect_connection([_declare(1, 100), _composite(1, [200, 201]), _create(1),
                               _declare(2, 300), _create(2), _create(2)], "capA", "g1")
    b = ws.collect_connection([_declare(5, 100), _composite(5, [200]), _create(5)], "capB", "g1")
    stamp = {"captures": ["capA", "capB"], "channels": 2, "skipped": ["capC"], "sha256": "ab" * 32}
    idx = ws.Index(stamp, list(a.values()) + list(b.values()), 2)
    sh = idx.shells[100]
    check(list(sh.bodies) == [200, 201] and len(sh.bodies[200]) == 2 and len(sh.bodies[201]) == 1
          and sh.captures == {"capA", "capB"} and sh.creates == 2 and sh.needs_body is True,
          "a shell record pools its bodies across sightings with per-body sighting lists")
    check(idx.shells[300].needs_body is False and idx.shells[300].without_body == 1,
          "a shell never dressed reads needs_body False")
    check(idx.body_shells == {200: {100}, 201: {100}} and idx.pairs() == [(100, 200), (100, 201)],
          "body -> shells and the distinct pair list invert the sightings")
    s = idx.summary()
    check(s == {"captures": 2, "skipped": 1, "connections": 2, "sightings": 3, "declared": 3,
                "with_bodies": 2, "shells": 2, "pairs": 2, "bodies": 2},
          "summary counts", repr(s))
    back = ws.Index.from_dict(json.loads(json.dumps(idx.to_dict())))
    check(back.summary() == s and back.pairs() == idx.pairs() and back.stamp == stamp,
          "the index round-trips through JSON")
    inside = os.path.join(HERE, "should_never_exist.wireshells.json")
    try:
        ws.save(idx, inside)
        refused = False
    except ws.Refused:
        refused = True
    check(refused and not os.path.exists(inside), "save() refuses the working tree")
    with tempfile.TemporaryDirectory() as tmp:
        p = ws.save(idx, os.path.join(tmp, "w.json"))
        check(ws.load(p).summary() == s, "load() reads it back")
        check(ws.load(p, stamp).summary() == s, "load() with the matching stamp accepts")
        other = dict(stamp, sha256="cd" * 32, channels=3)
        try:
            ws.load(p, other)
            ok = False
        except ws.Refused as exc:
            ok = "different corpus" in str(exc)
        check(ok, "load() REFUSES an index built over another corpus")
    mixed = ws.collect_connection([_declare(1, 100), _composite(1, [200])], "capA", "g1")
    plain = ws.collect_connection([_declare(1, 100)], "capB", "g1")
    idx2 = ws.Index(stamp, list(mixed.values()) + list(plain.values()), 2)
    check(idx2.shells[100].needs_body is None,
          "a shell dressed in one sighting and not another reads needs_body None -- "
          "inconsistent is a value, not an average")


# ---------------------------------------------------------------------------
# 2. the vault corpus
# ---------------------------------------------------------------------------

def section2():
    print("\n2. the keyed live tapes")
    with_ch, without = ws.keyed_tapes()
    check(len(with_ch) >= 19 and len(without) >= 5,
          f"{len(with_ch)} tapes with a decrypted game channel, {len(without)} without "
          f"(floors 19 / 5)")
    t0 = time.time()
    idx, path, fresh = ws.open_index()
    s = idx.summary()
    check(s["captures"] == len(with_ch) and sorted(idx.stamp["skipped"]) == sorted(without),
          f"the index rests on every keyed tape and NAMES the {s['skipped']} it skipped",
          f"{'built' if fresh else 'loaded'} in {time.time() - t0:.1f} s")
    check(s["connections"] >= 73 and s["declared"] >= 1900 and s["shells"] >= 100
          and s["pairs"] >= 200 and s["bodies"] >= 200,
          "floors: >= 73 connections, >= 1,900 declared sightings, >= 100 shells, "
          ">= 200 pairs, >= 200 bodies", repr(s))
    check(s["declared"] == s["sightings"],
          "every sighting in the live corpus was declared by a 0x0056 (no create-only slots)")
    sh = idx.shells.get(HATCHER_SHELL)
    check(sh is not None and HATCHER_BODY in sh.bodies and len(sh.bodies) >= 8
          and sh.needs_body is True,
          f"the hatcher shell was dressed with {len(sh.bodies) if sh else 0} bodies, "
          f"116703 among them, and always dressed")
    worm = idx.shells.get(WORM)
    check(worm is not None and worm.needs_body is False,
          "the worm shell was never given a 0x0057 -- it carries its own geometry")

    # the slot finding, on the real corpus
    by_index = {}
    for x in idx.declared():
        by_index.setdefault(x["definition"], set()).add(x["shell"])
    multi = {i: v for i, v in by_index.items() if len(v) > 1}
    check(len(multi) >= 1 and by_index.get(7809) == {141285, 16271}
          and len(by_index) - len(multi) >= 300,
          f"a definition index is not a global name: {len(by_index) - len(multi)} of "
          f"{len(by_index)} indices name one shell everywhere, {len(multi)} name more; "
          f"7809 is {{141285, 16271}}")

    # content rows are a subset of the wire
    import content
    world = content.load()
    rows = world.rows("npc")
    pairs = set(idx.pairs())
    want_pairs = {(int(r["file_id"]), int(r["model_id"])) for r in rows.values()
                  if r.get("model_id") is not None}
    want_shells = {int(r["file_id"]) for r in rows.values() if r.get("model_id") is None}
    missing_p = sorted(want_pairs - pairs)
    missing_s = sorted(want_shells - set(idx.shells))
    check(len(want_pairs) >= 40 and not missing_p,
          f"every content (shell, body) pair is on the wire: {len(want_pairs) - len(missing_p)}"
          f"/{len(want_pairs)}", f"missing {missing_p[:5]}")
    check(len(want_shells) >= 9 and not missing_s,
          f"every content shell-only row's shell is on the wire: "
          f"{len(want_shells) - len(missing_s)}/{len(want_shells)}", f"missing {missing_s[:5]}")
    check(len(pairs) > 3 * len(want_pairs),
          f"the wire holds {len(pairs)} pairs against content's {len(want_pairs)} -- "
          f"what the index adds over the rows")

    # the composited equivalence, corpus-wide, through the catalog
    from archive import Archive, DEFAULT_DAT
    if not os.path.isfile(DEFAULT_DAT):
        LEDGER.skip("the archive cross-check", f"no study archive at {DEFAULT_DAT}")
        return
    with Archive(DEFAULT_DAT) as ar:
        cat, _p, _f = mc.open_catalog(ar)
    cc = ws.crosscheck(idx, cat)
    nb = len(cc.get("body_ok", [])) + len(cc.get("body_bad", []))
    check(nb == s["bodies"] and not cc.get("body_bad"),
          f"every body the wire ever named is a model head: {len(cc.get('body_ok', []))}/{nb}",
          repr(cc.get("body_bad", [])[:5]))
    ns = len(cc.get("shell_skel_ok", [])) + len(cc.get("shell_skel_bad", []))
    check(ns >= 80 and not cc.get("shell_skel_bad"),
          f"every shell ever DRESSED by a 0x0057 is geometry-less: "
          f"{len(cc.get('shell_skel_ok', []))}/{ns} (>= 80)", repr(cc.get("shell_skel_bad", [])[:5]))
    ng = len(cc.get("shell_geom_ok", [])) + len(cc.get("shell_geom_bad", []))
    check(ng >= 20 and not cc.get("shell_geom_bad"),
          f"every shell NEVER dressed carries its own geometry: "
          f"{len(cc.get('shell_geom_ok', []))}/{ng} (>= 20)", repr(cc.get("shell_geom_bad", [])[:5]))
    check(not cc.get("unresolved") and not cc.get("inconsistent"),
          "no wire id is missing from the archive and no shell was dressed inconsistently",
          repr((cc.get("unresolved", [])[:3], cc.get("inconsistent", [])[:3])))
    check(ns + ng == s["shells"], "the two shell classes partition every shell")


def main():
    section0()
    section1()
    try:
        vaultpath.require_dir("captures", "live", why="the wire index")
    except SystemExit as exc:
        LEDGER.skip("section 2", str(exc).splitlines()[0])
        return LEDGER.verdict()
    section2()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
