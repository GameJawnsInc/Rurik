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
  8  STORED state (the character store is shared by every build): a
     temp-dir store holding 3446 in its player bar, account library,
     learned library and a hero's bar and skills, read in a THREAD as a
     connection reads it. Under 38797 3446 is not sent and each source
     names it once, 3442 still is, nothing raises (0d89fdcc: SystemExit,
     swallowed by threading), the store on disk keeps 3446, an in-game edit
     elsewhere on the bar keeps it, a grant of it is refused; under 38888
     all of it is sent (bare machine). 8b drives _handle_request_players and
     reads the wire (skips by name without the attribute cost rows).

Imports authsrv (no socket, no client). Floor 55: the green BARE run
(RURIK_VAULT=C:/nonexistent-vault, 2026-09-28), sections 5, 6 and 8b skipping
by name; 63 with the vault, 70 with the vault and the staged 38888 overlay.
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

LEDGER = checks.Ledger("the client-build skill guard", floor=55)   # the bare run, 2026-09-28 (28 + section 7's 9 + section 8's 18)
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
    saved_leaf_build = getattr(skillunlock, "SKILL_TABLE_BUILD", None)
    authsrv.agents.WORLD = world

    def restore():
        (authsrv.agents.WORLD, authsrv.SKILL_TABLE_ROWS,
         skillunlock.SKILL_TABLE_ROWS, authsrv.SKILL_TABLE_BUILD) = saved
        if saved_leaf_build is not None:
            skillunlock.SKILL_TABLE_BUILD = saved_leaf_build
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

print("\n8. STORED state is bounded by the SERVED build, where it is read")
# The review's blocking item (2026-09-28): the character store is one per
# account and shared by EVERY build, so a 38888 session (bound 3,476) can
# leave 3446 in a bar or a library, and the next 38797 session reads it back.
# On 0d89fdcc the stored bar went out as stored, and a stored library reached
# words_from_ids' SystemExit inside the connection thread -- which threading
# swallows, so the connection died at the instance load with nothing printed.
# Each read below runs in a THREAD for that reason: a raise there is scored,
# not lost. A temp-dir store, no vault.
import shutil  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402
import charstore  # noqa: E402

UUID8, EMAIL8, HERO8 = "88888888888888888888888888888888", "skillbound@rurik.invalid", 6
PAST, KEPT = 3446, 3442                  # past 38797's 3,443 records / its last id
LIB8 = [1, 2, KEPT, PAST]
BAR8 = [PAST, KEPT, 0, 0, 0, 0, 0, 0]
HBAR8 = [KEPT, PAST, 0, 0, 0, 0, 0, 0]
HSKILLS8 = [KEPT, PAST]
SOURCES8 = ("stored account library", "stored character library", "stored player bar",
            f"stored hero {HERO8} bar", f"stored hero {HERO8} skills")
tmp8 = tempfile.mkdtemp(prefix="skillbound-store-")
saved_bar8, saved_store_dir8 = list(authsrv.SKILLBAR), charstore.store_dir


def open8():
    with contextlib.redirect_stdout(io.StringIO()):
        return charstore.Store.open(EMAIL8, base=tmp8)


def write8():
    for f in os.listdir(tmp8):
        os.remove(os.path.join(tmp8, f))
    st = open8()
    with contextlib.redirect_stdout(io.StringIO()):
        row = st.ensure_character(UUID8, "Bound Test")
        row["skillbar"] = list(BAR8)
        row["learned_skills"] = list(LIB8)
        st.account()["unlocked_skills"] = list(LIB8)
        h = st.ensure_hero(UUID8, HERO8)
        h["skillbar"], h["skills"] = list(HBAR8), list(HSKILLS8)
        st.save()


def on_disk8():
    st = open8()
    return (st.account_unlocked_skills(), st.character_learned_skills(UUID8),
            st.character_skillbar(UUID8), (st.hero_row(UUID8, HERO8) or {}).get("skillbar"),
            (st.hero_row(UUID8, HERO8) or {}).get("skills"))


def read8(build):
    """Serve `build`, then read the store as a connection does, in a thread.
    Returns ({read: value or ('RAISED', repr)}, log lines, state)."""
    write8()
    store = open8()
    state = {"char_uuid": UUID8, "charstore_game": store}
    got, out = {}, io.StringIO()

    def attempt(name, fn):
        try:
            got[name] = fn()
        except BaseException as e:                          # noqa: BLE001 -- SystemExit is the defect
            got[name] = ("RAISED", f"{type(e).__name__}: {e}")

    def connection():
        # with the per-connection `seen` the load passes, where the tree has it
        kw = ({"seen": state.setdefault("skills_withheld", set())}
              if "seen" in inspect.signature(skillunlock.resolve_library).parameters else {})
        attempt("library", lambda: skillunlock.resolve_library(
            store, UUID8, authsrv.UNLOCKED, "flag", **kw))
        attempt("bar", lambda: authsrv.player_bar_at_load(state))
        attempt("hero", lambda: authsrv.hero_build(state, HERO8))
        attempt("usable", lambda: authsrv.player_usable_library(state))
        attempt("hero_usable", lambda: authsrv.hero_usable_library(state, HERO8, [KEPT]))
    restore = swap(fresh_world({}))
    try:
        with contextlib.redirect_stdout(out):
            authsrv.serve_client_skill_table(build)
            t = threading.Thread(target=connection)
            t.start()
            t.join()
    finally:
        restore()
    return got, out.getvalue().splitlines(), state


def raised(v):
    return isinstance(v, tuple) and len(v) == 2 and v[0] == "RAISED"


def bits8(words):
    return set(authsrv.ids_from_words(words))


try:
    charstore.store_dir = lambda: tmp8
    got, log8, st8 = read8(PIN)
    lib = got.get("library")
    check(lib is not None and not raised(lib),
          f"{PIN}: a stored library holding {PAST} is READ in the connection thread "
          f"without raising (0d89fdcc: words_from_ids' SystemExit, swallowed by threading)",
          f"{lib[1]!r} / {lib[3]!r}" if (lib is not None and not raised(lib)) else repr(lib))
    ok_lib = lib is not None and not raised(lib)
    check(ok_lib and KEPT in bits8(lib[0]) and PAST not in bits8(lib[0]),
          f"{PIN}: 0x001D (the account library) carries {KEPT} and not {PAST}",
          f"{sorted(bits8(lib[0]))} ({lib[1]})" if ok_lib else repr(lib))
    check(ok_lib and KEPT in bits8(lib[2]) and PAST not in bits8(lib[2]),
          f"{PIN}: 0x00DB (the character library) carries {KEPT} and not {PAST}",
          f"{sorted(bits8(lib[2]))} ({lib[3]})" if ok_lib else repr(lib))
    check(got.get("bar") == [0, KEPT, 0, 0, 0, 0, 0, 0],
          f"{PIN}: the stored player bar {BAR8} goes out as [0, {KEPT}, 0, ...] -- "
          f"its slot EMPTY, the other slots in place", repr(got.get("bar")))
    hero = got.get("hero")
    check(not raised(hero) and hero is not None
          and list(hero[1]) == [KEPT, 0, 0, 0, 0, 0, 0, 0] and list(hero[0]) == [KEPT],
          f"{PIN}: the stored hero {HERO8} bar {HBAR8} is [{KEPT}, 0, ...] and its skill "
          f"list (0x0073) is [{KEPT}] -- hero_build, which every hero consumer reads",
          repr(hero))
    usable, hero_usable = got.get("usable"), got.get("hero_usable")
    check(not raised(usable) and not raised(hero_usable)
          and KEPT in usable and PAST not in usable
          and KEPT in hero_usable and PAST not in hero_usable,
          f"{PIN}: the 0x005C referees (player's and hero's library) hold {KEPT}, not {PAST}",
          f"{usable!r} / {hero_usable!r}")
    for src in SOURCES8:
        want = (f"[skills] {src}: {PAST} is past build {PIN}'s skill table "
                f"({authsrv.SKILL_RECORD_COUNT_BY_BUILD[PIN]:,} records): not sent")
        n_src = sum(ln.startswith(want) for ln in log8)
        check(n_src == 1,
              f"{PIN}: '{src}' names {PAST}, the build and the count, ONCE per connection",
              f"{n_src} line(s)" + ("" if n_src == 1 else ": " + " | ".join(
                  ln for ln in log8 if "past build" in ln)))
    check(on_disk8() == (LIB8, LIB8, BAR8, HBAR8, HSKILLS8),
          f"{PIN}: the store on disk still holds {PAST} in all five (bounded what is SENT, "
          f"not what is KEPT)", repr(on_disk8()))

    # an in-game edit under the lower build keeps what the player could not see
    edit = getattr(authsrv, "handle_skillbar_skill_set", None)
    sent8 = []

    class _Rec:
        def event(self, *a, **k):
            pass
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            edit([0x5C, authsrv.PLAYER_AGENT_ID, 2, 1, 0],
                 lambda op, v, label=None: sent8.append((op, v)), st8, 0, _Rec())
            e1 = None
        except BaseException as e:                          # noqa: BLE001
            e1 = e
    check(e1 is None and open8().character_skillbar(UUID8) == [PAST, KEPT, 1, 0, 0, 0, 0, 0],
          f"{PIN}: a 0x005C into slot 2 stores [{PAST}, {KEPT}, 1, ...] -- the withheld "
          f"{PAST} stays in slot 0 for the build that has it",
          f"{open8().character_skillbar(UUID8)} {e1!r}")
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            edit([0x5C, authsrv.PLAYER_AGENT_ID, 0, 2, 0],
                 lambda op, v, label=None: sent8.append((op, v)), st8, 0, _Rec())
            e2 = None
        except BaseException as e:                          # noqa: BLE001
            e2 = e
    check(e2 is None and open8().character_skillbar(UUID8) == [2, KEPT, 1, 0, 0, 0, 0, 0],
          f"{PIN}: ...and a 0x005C INTO that slot replaces it: the player's choice wins",
          f"{open8().character_skillbar(UUID8)} {e2!r}")

    # a grant of a past-table skill is refused, not sent and not learned
    gsent = []
    gout = io.StringIO()
    with contextlib.redirect_stdout(gout):
        try:
            gslot = authsrv.grant_skill(lambda op, v, label=None: gsent.append((op, v)),
                                        st8, PAST, 0)
            ge = None
        except BaseException as e:                          # noqa: BLE001
            gslot, ge = None, e
    check(ge is None and gslot is None and not gsent
          and open8().character_learned_skills(UUID8) == LIB8
          and f"grant of skill {PAST} REFUSED: past build {PIN}" in gout.getvalue(),
          f"{PIN}: grant_skill({PAST}) sends nothing, learns nothing, and says so",
          f"slot {gslot}, sent {gsent}, {ge!r}, log {gout.getvalue().strip()[-160:]}")

    # the control: the build that HAS the record is sent it
    got, log8, _st = read8(NEWER)
    lib = got.get("library")
    ok_lib = lib is not None and not raised(lib)
    check(ok_lib and PAST in bits8(lib[0]) and PAST in bits8(lib[2])
          and got.get("bar") == BAR8
          and not raised(got.get("hero")) and got.get("hero") is not None
          and list(got["hero"][1]) == HBAR8 and list(got["hero"][0]) == HSKILLS8
          and PAST in (got.get("usable") or ()),
          f"CONTROL {NEWER}: the same store is sent whole -- {PAST} in 0x001D, 0x00DB, the "
          f"player bar, the hero bar, its skill list and the referee",
          (f"0x001D {sorted(bits8(lib[0]))}, 0x00DB {sorted(bits8(lib[2]))}" if ok_lib
           else repr(lib)) + f"; bar {got.get('bar')}; hero {got.get('hero')!r}")
    check(not any("is past build" in ln for ln in log8),
          f"CONTROL {NEWER}: and nothing is named withheld",
          "\n".join(ln for ln in log8 if "past build" in ln))

    # the real instance load, when the content it needs is present
    print("  8b. the instance load itself (_handle_request_players)")
    HERO_RIG = {"OUTPOST": True, "EXPLORABLE": False, "HERO": HERO8, "HERO_IDS": [HERO8],
                "HERO_AGENT_ID": 200,
                "HERO_ROWS": {HERO8: {"hero": HERO8, "body": "academy_monk",
                                      "profession": 3}},
                "HERO_BODY": True, "HERO_BODY_NPC": "academy_monk", "HERO_ACTIVATE": True,
                "HERO_PIPELINE_FIRST": True, "HERO_CHAR": True, "HERO_INVENTORY": 2,
                "HERO_BAGS": True, "HERO_RIG_RETAIL": True, "PERSIST": True}
    saved_rig = {k: getattr(authsrv, k) for k in HERO_RIG}
    skip_load = None
    try:
        for k, v in HERO_RIG.items():
            setattr(authsrv, k, v)
        for build in (PIN, NEWER):
            write8()
            with contextlib.redirect_stdout(io.StringIO()):
                world = content.load()
            restore = swap(world)
            wire, lout = [], io.StringIO()
            try:
                with contextlib.redirect_stdout(lout):
                    authsrv.serve_client_skill_table(build)
                    try:
                        authsrv._handle_request_players(
                            lambda op, v, label=None: wire.append((op, v)),
                            {"agents": {}, "char_uuid": UUID8, "map_id": 148}, 0,
                            threading.Event(), _Rec())
                        lerr = None
                    except BaseException as e:              # noqa: BLE001
                        lerr = e
            finally:
                restore()
            if isinstance(lerr, ValueError) and "attribute cost rows" in str(lerr):
                skip_load = "no attribute cost rows in the content (bare machine)"
                break

            def of(op, agent=None):
                return [v for o, v in wire if o == op
                        and (agent is None or (v and v[0] == agent))]
            acct, char = of(0x001D), of(0x00DB)
            pbar = of(authsrv.GAME_SMSG_SKILLBAR_UPDATE, authsrv.PLAYER_AGENT_ID)
            hbar = of(authsrv.GAME_SMSG_SKILLBAR_UPDATE, 200)
            hinfo = [v for o, v in wire if o == 0x0073 and v and v[0] == HERO8]
            seen = (acct and char and pbar and hbar and hinfo) and (
                PAST in bits8(acct[-1][0]), PAST in bits8(char[-1][0]),
                PAST in pbar[-1][1], PAST in hbar[-1][1], PAST in hinfo[-1][6])
            want = (False,) * 5 if build == PIN else (True,) * 5
            check(lerr is None and seen == want,
                  f"{build}: the load's wire -- {PAST} in (0x001D, 0x00DB, player 0x00DA, "
                  f"hero 0x00DA, 0x0073) is {want}",
                  f"{seen} {lerr!r}")
            if build == PIN:
                check(bool(acct and pbar and hbar) and KEPT in bits8(acct[-1][0])
                      and pbar[-1][1] == [0, KEPT, 0, 0, 0, 0, 0, 0]
                      and hbar[-1][1] == [KEPT, 0, 0, 0, 0, 0, 0, 0],
                      f"{PIN}: and {KEPT} still goes out, in its own slot",
                      f"{acct[-1:] and sorted(bits8(acct[-1][0]))[-3:]} "
                      f"{pbar[-1:]} {hbar[-1:]}")
    finally:
        for k, v in saved_rig.items():
            setattr(authsrv, k, v)
    if skip_load:
        LEDGER.skip("the instance load's wire with a stored 3446", skip_load)
finally:
    charstore.store_dir = saved_store_dir8
    authsrv.SKILLBAR[:] = saved_bar8
    shutil.rmtree(tmp8, ignore_errors=True)
check(authsrv.SKILL_TABLE_ROWS == skillunlock.SKILL_TABLE_ROWS
      == authsrv.SKILL_RECORD_COUNT_BY_BUILD[authsrv.CLIENT_BUILD],
      "section 8 put the served bound back")

sys.exit(LEDGER.verdict())
