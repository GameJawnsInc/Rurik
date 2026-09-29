"""The client-build skill guard: no skill past the served client's table.

    python toolkit/authsrv/test_skillbound.py

WHY. The content overlay is regenerated from the newest vaulted client (build
38888, 2026-09-28), whose skill table holds 3,476 records; the pin's -- and the
owner's loopback client's, vault/run/slice -- holds 3,443, so the 38888 player
corpus carries a skill (3446) that client has no record for. The server knows
which build it serves (CLIENT_BUILD, --client-build); this checks that it
(1) holds a MEASURED skill record count for every build it can be told,
(2) stops serving every skill-keyed content row at or past that count, naming
each, (3) refuses a bar or a content row that would still hand such an id to a
body, and (4) refuses a build with no count the way MAP_ID_COUNT refuses one.

WHAT CAN GO RED, section by section:
  1  the two per-build tables stop registering the same builds, or the
     module constant stops being the default build's row (bare machine)
  2  content.World.drop_past drops a row below the bound, keeps one at or
     past it, touches a kind that is not skill-keyed, or names nothing
     (synthetic content, bare machine)
  3  authsrv.serve_client_skill_table on a synthetic build: the rebind, the
     drop and its log line, the unlock gate following the rebind, and the
     refusal of a content row still naming a dropped id (bare machine)
  4  main() refusing a build with a MAP row and no SKILL row, in-process,
     before anything is bound -- a regression reaches serve_client_skill_table
     and KeyErrors instead, which is a FAIL here, never a socket (bare machine)
  5  the loaded content (RURIK_CONTENT_EXTRA's staged 38888 overlay, or the
     vault's once it merges): its rows past 38797's table are dropped and
     named for 38797 and served for 38888 (skips by name when the content
     has no such row -- today's 38797 vault)
  6  every vaulted client re-measured with skilltable.locate_table and
     buildid.read against SKILL_RECORD_COUNT_BY_BUILD (skips by name on a
     bare machine)
  7  main() stops calling serve_client_skill_table once, after --client-build
     and before every skill consumer, or drops the refusal of --skills,
     --hero-skills or --enemy-skills, or reads a flag's id with skill_timing
     ahead of its refusal (a source lock; bare machine)

Imports authsrv (no socket, no client). Floor 37: the green BARE run
(RURIK_VAULT unset to nothing, 2026-09-28), sections 5 and 6 skipping by name;
42 with the vault, 49 with the vault and the staged 38888 overlay.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (TOOLKIT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import checks  # noqa: E402
import content  # noqa: E402
import skillunlock  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import authsrv  # noqa: E402

LEDGER = checks.Ledger("the client-build skill guard", floor=37)   # the bare run, 2026-09-28 (28 + section 7's 9)
check = checks.adopt(LEDGER)

PIN = 38797
NEWER = 38888


def fresh_world(tables):
    return content.World({k: dict(v) for k, v in tables.items()}, [], [])


def swap(world):
    """Serve `world` through agents.WORLD; returns a restore callable that
    also puts back both SKILL_TABLE_ROWS bindings."""
    saved = (authsrv.agents.WORLD, authsrv.SKILL_TABLE_ROWS,
             skillunlock.SKILL_TABLE_ROWS, authsrv.SKILL_TABLE_BUILD)
    authsrv.agents.WORLD = world

    def restore():
        (authsrv.agents.WORLD, authsrv.SKILL_TABLE_ROWS,
         skillunlock.SKILL_TABLE_ROWS, authsrv.SKILL_TABLE_BUILD) = saved
    return restore


def serve(build):
    """serve_client_skill_table(build) with its log captured: (lines, loaded, exc)."""
    out = io.StringIO()
    loaded = exc = None
    with contextlib.redirect_stdout(out):
        try:
            loaded = authsrv.serve_client_skill_table(build)
        except (Exception, SystemExit) as e:                 # noqa: BLE001
            exc = e
    return out.getvalue().splitlines(), loaded, exc


print("1. one measured skill count per build the server can be told")
check(set(authsrv.SKILL_RECORD_COUNT_BY_BUILD) == set(authsrv.MAP_ID_COUNT_BY_BUILD),
      "SKILL_RECORD_COUNT_BY_BUILD registers exactly MAP_ID_COUNT_BY_BUILD's builds",
      f"skill {sorted(authsrv.SKILL_RECORD_COUNT_BY_BUILD)}, map "
      f"{sorted(authsrv.MAP_ID_COUNT_BY_BUILD)} -- a build --client-build accepts "
      f"must have both, or it is served one table's facts and the other's guess")
check(authsrv.SKILL_RECORD_COUNT_BY_BUILD is skillunlock.SKILL_RECORD_COUNT_BY_BUILD,
      "authsrv's name IS the leaf's table (a re-export, one table)")
check(authsrv.SKILL_TABLE_ROWS == skillunlock.SKILL_TABLE_ROWS
      == authsrv.SKILL_RECORD_COUNT_BY_BUILD[authsrv.CLIENT_BUILD],
      f"at import, SKILL_TABLE_ROWS is the default build's row "
      f"({authsrv.CLIENT_BUILD}: {authsrv.SKILL_RECORD_COUNT_BY_BUILD[authsrv.CLIENT_BUILD]:,})",
      f"authsrv {authsrv.SKILL_TABLE_ROWS}, skillunlock {skillunlock.SKILL_TABLE_ROWS}")
check(authsrv.SKILL_RECORD_COUNT_BY_BUILD[PIN] == 3443
      and authsrv.SKILL_RECORD_COUNT_BY_BUILD[NEWER] == 3476,
      "the pin holds 3,443 records and 38888 3,476 -- the gap that holds 3446",
      str(authsrv.SKILL_RECORD_COUNT_BY_BUILD))
check(skillunlock.ids_past_table([0, 1, 3442, 3443, 3446, 3446], 3443) == [3443, 3446],
      "ids_past_table: id >= the count, sorted, each once; 0 and 3442 kept",
      str(skillunlock.ids_past_table([0, 1, 3442, 3443, 3446, 3446], 3443)))

print("\n2. World.drop_past on synthetic content")
W = fresh_world({
    "skills": {"5": {"profession": 1}, "9": {"profession": 6},
               "10": {"profession": 6}, "12": {"profession": 6}},
    "skill_effect": {"9": {}, "10": {}},
    "skill_visual": {"4": {}},
    "effect": {"50": {"file_id": 1}},          # s_effect, NOT skill-keyed
    "npc": {"10": {"name": "a non-skill kind keyed 10"}},
})
lines = W.drop_past(content.SKILL_KEYED_KINDS, 10, "past build 1's skill table (10 records)")
check(sorted(W.rows("skills")) == ["5", "9"],
      "the rows below the bound (5, 9) are kept; 10 and 12 are gone",
      str(sorted(W.rows("skills"))))
check(sorted(W.rows("skill_effect")) == ["9"] and sorted(W.rows("skill_visual")) == ["4"],
      "every skill-keyed kind is bounded, not just `skills`",
      f"skill_effect {sorted(W.rows('skill_effect'))}, skill_visual "
      f"{sorted(W.rows('skill_visual'))}")
check("50" in W.rows("effect") and "10" in W.rows("npc"),
      "a kind that is not skill-keyed is untouched (effect 50, npc 10)")
check(lines == ["skills 10: past build 1's skill table (10 records) -- not served",
                "skills 12: past build 1's skill table (10 records) -- not served",
                "skill_effect 10: past build 1's skill table (10 records) -- not served"],
      "each dropped row is named once, by kind and id, with the build and count",
      str(lines))
check(W.dropped == lines, "and recorded in World.dropped, as a label row's drop is",
      str(W.dropped))
check("drop_past" in content.World.__dict__ and "skill_references" in content.__dict__,
      "the rule lives in content.py, where World.dropped is defined")

print("\n3. serve_client_skill_table on a synthetic build (count 10)")
authsrv.SKILL_RECORD_COUNT_BY_BUILD[1] = 10
try:
    W = fresh_world({"skills": {"3": {}, "9": {}, "11": {}},
                     "skill_effect": {"11": {}},
                     "spawn": {"s1": {"skills": [[3, 0.0, 1.0]]}},
                     "party": {"p1": {"player_skills": [9, 0]}}})
    W.dropped.append("a load-time line")
    restore = swap(W)
    try:
        log, loaded, exc = serve(1)
        check(exc is None, "served: no content row names a dropped id", repr(exc))
        check(authsrv.SKILL_TABLE_ROWS == 10 and skillunlock.SKILL_TABLE_ROWS == 10,
              "SKILL_TABLE_ROWS rebound in authsrv AND in the leaf that reads it",
              f"{authsrv.SKILL_TABLE_ROWS}, {skillunlock.SKILL_TABLE_ROWS}")
        check(sorted(W.rows("skills")) == ["3", "9"] and not W.rows("skill_effect"),
              "skill 11 and its skill_effect row are not served")
        check("CONTENT DROPPED: skills 11: past build 1's skill table (10 records) "
              "-- not served" in log
              and "CONTENT DROPPED: skill_effect 11: past build 1's skill table (10 "
                  "records) -- not served" in log,
              "each drop is printed by name", "\n".join(log))
        check(sum("skills 11:" in ln for ln in log) == 1,
              "and printed ONCE", "\n".join(log))
        check(any(ln.startswith("[skills] --client-build 1:") and "2 content row(s)" in ln
                  for ln in log),
              "one summary line names the build and how many rows it dropped",
              "\n".join(log))
        check(loaded == ["a load-time line"],
              "it returns the LOAD's drops only -- main() prints those, not these twice",
              str(loaded))
        try:
            skillunlock.words_from_ids([9], "t")
            gate9 = True
        except SystemExit:
            gate9 = False
        try:
            skillunlock.words_from_ids([10], "t")
            gate10 = False
        except SystemExit as e:
            gate10 = "(10 rows)" in str(e)
        check(gate9 and gate10,
              "the unlock gate follows the rebind: 9 unlockable, 10 refused",
              f"9 {gate9}, 10 {gate10}")
        try:
            authsrv.refuse_skills_past_table([3, 9], "--skills")
            ok_bar = True
        except SystemExit:
            ok_bar = False
        try:
            authsrv.refuse_skills_past_table([3, 11, 12], "--skills")
            bad_bar = ""
        except SystemExit as e:
            bad_bar = str(e)
        check(ok_bar, "a bar inside the table is served")
        check(bad_bar.startswith("--skills: skill 11, 12 is past build 1's skill table"),
              "a bar naming 11 and 12 is refused, by flag and by id", bad_bar)
    finally:
        restore()

    # the refusal: a content row still hands a body a dropped id
    for kind, row, where in (
            ("spawn", {"skills": [[3, 0.0, 1.0], [12, 1.0, 5.0]]}, "spawn.x.skills -> 12"),
            ("party", {"player_skills": [3, 12]}, "party.x.player_skills -> 12"),
            ("party", {"heroes": [{"skills": [9]}, {"skills": [12]}]},
             "party.x.heroes[2].skills -> 12"),
            ("player", {"skills": [12]}, "player.x.skills -> 12")):
        W = fresh_world({"skills": {"3": {}, "12": {}}, kind: {"x": row}})
        restore = swap(W)
        try:
            log, loaded, exc = serve(1)
        finally:
            restore()
        check(isinstance(exc, SystemExit) and where in str(exc),
              f"refused: {where}", repr(exc))
finally:
    del authsrv.SKILL_RECORD_COUNT_BY_BUILD[1]
check(authsrv.SKILL_TABLE_ROWS == skillunlock.SKILL_TABLE_ROWS
      == authsrv.SKILL_RECORD_COUNT_BY_BUILD[authsrv.CLIENT_BUILD]
      and authsrv.SKILL_TABLE_BUILD == authsrv.CLIENT_BUILD
      and 1 not in authsrv.SKILL_RECORD_COUNT_BY_BUILD,
      "the module state is put back (the rest of this run reads it)")

print("\n4. main() refuses a build with no SKILL_RECORD_COUNT row")
# A build given a MAP row and no SKILL row passes the first refusal and must
# stop at the second. Without it, main() reaches serve_client_skill_table and
# KeyErrors -- still before any socket -- which this scores as a FAIL.
authsrv.MAP_ID_COUNT_BY_BUILD[1] = 888
saved_argv, err = sys.argv, io.StringIO()
sys.argv = ["authsrv.py", "--client-build", "1"]
try:
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        try:
            authsrv.main()
            got = "returned"
        except SystemExit as e:
            got = f"SystemExit({e.code})"
        except Exception as e:                               # noqa: BLE001
            got = f"{type(e).__name__}: {e}"
finally:
    sys.argv = saved_argv
    del authsrv.MAP_ID_COUNT_BY_BUILD[1]
check(got == "SystemExit(2)" and "has no SKILL_RECORD_COUNT row" in err.getvalue(),
      "--client-build 1 (a MAP row, no SKILL row) is an argparse refusal naming the table",
      f"{got}; stderr: {err.getvalue().strip()[-200:]}")
check(authsrv.CLIENT_BUILD == PIN,
      "and CLIENT_BUILD was not rebound by the refused flag", str(authsrv.CLIENT_BUILD))

print("\n5. the loaded content, served to 38797 and to 38888")
with contextlib.redirect_stdout(io.StringIO()):
    probe = content.load()
past_pin = sorted(int(k) for k in probe.rows("skills")
                  if int(k) >= authsrv.SKILL_RECORD_COUNT_BY_BUILD[PIN])
print(f"  content sources: {'; '.join(probe.sources)}")
if not past_pin:
    LEDGER.skip("the loaded content served to 38797 and 38888",
                f"no skills row at or past {PIN}'s {authsrv.SKILL_RECORD_COUNT_BY_BUILD[PIN]:,} "
                f"records in this content (the 38797 overlay); set RURIK_CONTENT_EXTRA "
                f"to a 38888 emission to run it")
else:
    staged = any(os.path.isfile(os.path.join(d, "skills.toml"))
                 for d in content.extra_dirs_from_env())
    if staged:
        check(3446 in past_pin, "the staged 38888 overlay carries 3446 past the pin's table",
              str(past_pin))
    for build in (PIN, NEWER):
        with contextlib.redirect_stdout(io.StringIO()):
            world = content.load()
        n_before = len(world.rows("skills"))
        restore = swap(world)
        try:
            log, loaded, exc = serve(build)
        finally:
            restore()
        rows = authsrv.SKILL_RECORD_COUNT_BY_BUILD[build]
        want_gone = [s for s in past_pin if s >= rows]
        gone = [s for s in past_pin if str(s) not in world.rows("skills")]
        check(exc is None, f"{build}: served (no content row hands a body one)", repr(exc))
        check(gone == want_gone and len(world.rows("skills")) == n_before - len(want_gone),
              f"{build}: exactly the rows past {rows:,} are dropped "
              f"({want_gone or 'none'})", f"gone {gone}")
        if want_gone:
            check(all(any(f"CONTENT DROPPED: skills {s}: past build {build}'s skill "
                          f"table ({rows:,} records) -- not served" == ln for ln in log)
                      for s in want_gone),
                  f"{build}: and each is named in the log", "\n".join(log))
        else:
            check(all(str(s) in world.rows("skills") for s in past_pin)
                  and not any(ln.startswith("CONTENT DROPPED") for ln in log),
                  f"{build}: {past_pin} still served, and no drop line printed",
                  "\n".join(log))

print("\n6. every vaulted client re-measured")
measured, why_not = {}, "no vaulted client on this machine"
try:
    sys.path.insert(0, os.path.join(TOOLKIT, "clientscan"))
    import pinned as _pinned
    import skilltable as _st
    import buildid as _bid
    import vaultpath as _vp
    for b in _pinned.BUILDS:
        path = os.path.join(_vp.vault_root(), "client", b.stamp, "Gw.exe")
        if not os.path.exists(path):
            continue
        blob = open(path, "rb").read()
        _off, count, _score = _st.locate_table(blob)
        measured[b.number] = (count, _bid.read(path)[0], b.stamp)
except (Exception, SystemExit) as exc:                       # noqa: BLE001
    measured, why_not = {}, f"{type(exc).__name__}: {exc}"
if not measured:
    LEDGER.skip("the vaulted re-measure", why_not)
else:
    print("  " + "; ".join(f"{n} ({v[2]}): {v[0]:,}" for n, v in sorted(measured.items())))
    check(len(measured) >= 3, "at least three builds are readable",
          f"{sorted(measured)} -- with fewer, 'per build' has no span")
    check(all(v[1] == n for n, v in measured.items()),
          "each image's own build getter names the build it is filed under",
          str({n: v[1] for n, v in measured.items()}))
    check(all(n in authsrv.SKILL_RECORD_COUNT_BY_BUILD for n in measured),
          "every vaulted build HAS a row",
          f"missing {sorted(set(measured) - set(authsrv.SKILL_RECORD_COUNT_BY_BUILD))}")
    wrong = {n: (v[0], authsrv.SKILL_RECORD_COUNT_BY_BUILD.get(n))
             for n, v in measured.items()
             if authsrv.SKILL_RECORD_COUNT_BY_BUILD.get(n) != v[0]}
    check(not wrong,
          "locate_table's record count IS the table's row on every vaulted build",
          f"measured vs registered: {wrong}")
    check(len({v[0] for v in measured.values()}) >= 2,
          "and the count is NOT one constant across builds",
          str(sorted({v[0] for v in measured.values()})))

print("\n7. the guard is WIRED into main(): a source lock on the serve path")
# Sections 3-5 call serve_client_skill_table and refuse_skills_past_table
# directly, so a main() that stopped calling them stayed green (the review of
# 2026-09-28: replacing the serve call with the load's own drops, or deleting
# the SKILLBAR refusal, left sections 1-6 green unstaged and staged). main() is
# 3,000+ lines that end in a socket, so it is locked as TEXT, as ~40 other
# tests lock authsrv.py: the call's presence, its place, and one refusal per
# flag that hands a body skill ids.
import inspect  # noqa: E402
MAIN = inspect.getsource(authsrv.main)
SERVE = "_loaded_drops = serve_client_skill_table(CLIENT_BUILD)"
check(MAIN.count("serve_client_skill_table(") == 1 and MAIN.count(SERVE) == 1,
      f"main() calls serve_client_skill_table exactly once, as `{SERVE}`",
      f"{MAIN.count('serve_client_skill_table(')} call(s), "
      f"{MAIN.count(SERVE)} of that form")
at_serve, at_rebind = MAIN.find(SERVE), MAIN.find("CLIENT_BUILD = a.client_build")
check(0 <= at_rebind < at_serve,
      "after --client-build rebinds CLIENT_BUILD (else it bounds by the pin)",
      f"rebind at {at_rebind}, serve at {at_serve}")
CONSUMERS = ("if a.party:", "if a.hero_skills:", "if a.enemy_skills:",
             "SKILLBAR = (", "build_unlock_bitmap(a.unlocks)")
late = [c for c in CONSUMERS if not 0 <= at_serve < MAIN.find(c)]
check(at_serve >= 0 and not late,
      "and before every skill consumer (" + ", ".join(CONSUMERS) + ")",
      f"not after the serve call, or missing: {late}")
check(0 <= at_serve < MAIN.find("for _line in _loaded_drops"),
      "the load's own drops are still printed from what it returns")
# (block opener, the refusal, the line that binds the bar) -- the AUDIT of
# every main() block that parses skill ids from a flag into a body's bar. A
# party row reaches these through the flags it sets (a.hero_skills, and
# PARTY_SKILLBAR through default_skillbar into SKILLBAR); content rows are
# serve_client_skill_table's own refusal; --unlocks is words_from_ids' gate
# (a library, not a bar). --hero / --hero-chunk / --hero-bytes carry hero ids
# and raw bytes, not skill ids.
GUARDED = (
    ("--skills", "SKILLBAR = (", "refuse_skills_past_table(SKILLBAR, ",
     'print(f"skillbar: {SKILLBAR}")'),
    ("--hero-skills", "if a.hero_skills:", 'refuse_skills_past_table(_hids, "--hero-skills")',
     "HERO_SKILLS = tuple(_hbar)"),
    ("--enemy-skills", "if a.enemy_skills:", 'refuse_skills_past_table(_eids, "--enemy-skills")',
     "ENEMY_SKILLS = tuple(bar)"),
)
spans = []
for flag, opener, refusal, bind in GUARDED:
    o, r = MAIN.find(opener), MAIN.find(refusal)
    b = MAIN.find(bind, max(o, 0))
    check(MAIN.count(refusal) == 1 and 0 <= o < r < b,
          f"{flag}: its bar refused once, inside its block, before it is bound",
          f"{MAIN.count(refusal)} refusal(s); opener {o}, refusal {r}, bind {b}")
    spans.append((r, b))
check(MAIN.count("refuse_skills_past_table(") == len(GUARDED),
      f"main() refuses at exactly the {len(GUARDED)} audited sites -- a new "
      f"flag that hands a body skill ids adds its row to GUARDED here",
      f"{MAIN.count('refuse_skills_past_table(')} call(s)")
timing = []
i = MAIN.find("skill_timing(")
while i >= 0:
    timing.append(i)
    i = MAIN.find("skill_timing(", i + 1)
unguarded = [p for p in timing if not any(r < p < b for r, b in spans)]
check(timing and not unguarded,
      f"every skill_timing() main() calls on a flag's id ({len(timing)}) sits "
      f"AFTER its block's refusal -- none reads a dropped id first",
      f"unguarded at {unguarded} of {timing}")

sys.exit(LEDGER.verdict())
