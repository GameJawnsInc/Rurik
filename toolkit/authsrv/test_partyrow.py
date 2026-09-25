"""The [party.KEY] row's hero shapes, as main() reads them -- the heroless
party's crash (harness 20260925T161150, DESKWORK pass 7's client runs).

    python toolkit/authsrv/test_partyrow.py

THE DEFECT. A sandbox spec with no heroes compiled to an overlay whose
[party.sandbox] row had no `heroes` key: sandbox.overlay_text wrote one
`[[party.sandbox.heroes]]` table per hero, and TOML has no empty
array-of-tables, so zero heroes wrote NOTHING. main() read the missing list as
the SLICE-H2 single-hero shape and died on `_prow["hero"]` (KeyError) before
the server opened a socket. Two fixes, one per side: the compiler now writes
`heroes = []` (test_sandbox.py pins that), and main() reads its row through
`party_heroes`, which takes a row with NEITHER `heroes` nor `hero` as the
player alone -- the class, since any writer of that table (a hand-written
content row included) produces the same absence.

WHAT THIS PINS.

  * §1 `party_heroes`, in process: a `heroes` list comes back as dict copies,
    `heroes = []` as [], a row with neither as [] (the defect's row), the
    single-hero shape as None -- and the tree's own [party.slice] too. A row
    with a single-hero field but no `hero` is REFUSED (SystemExit naming the
    fields), each of the ten fields alone: that is a hero with its index
    missing, and reading it as heroless would drop the hero silently.
  * §2 LOCKS: main() calls it, once, and no longer reads `_prow.get("heroes")`
    itself; every key main()'s party block reads off the row or the first hero
    is in PARTY_SINGLE_HERO_FIELDS -- so a field added to the single-hero
    branch without joining the refusal's list goes red here.
  * §3 main() END TO END. `authsrv.py --party KEY --list-probes` runs the whole
    party block and returns before any socket (the capture-path refusal and the
    probe list sit between them), so the real startup is driven, not a copy:
    (A) a heroless spec compiled by sandbox.compile_spec, (B) the same overlay
    with its `heroes = []` line removed -- the defect's exact TOML, proven to
    carry neither key -- and (C) [party.slice], the single-hero shape, as the
    positive control. Each must exit 0 with no traceback, print its PARTY line
    and reach the probe list. Reverting main()'s fix turns (B) red with the
    original KeyError; (A) and (C) stay green, which is what localises it.

No client, no socket. §3 spawns three servers at once (~8 s wall each, run
concurrently); it needs the tree's npc rows for the example spec, and declares
a skip if the compiler refuses. Floor from the green run (see the ledger line).
"""
import ast
import os
import subprocess
import sys
import tempfile
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
HARNESS = os.path.join(os.path.dirname(HERE), "harness")
if HARNESS not in sys.path:
    sys.path.insert(0, HARNESS)
import checks                                                # noqa: E402
import agents                                                # noqa: E402
import authsrv                                               # noqa: E402
import sandbox                                               # noqa: E402

led = checks.Ledger("party row (the heroless party)", floor=15)   # 2026-09-25, from the first green run: 8 + 3 + 4

SRC_PATH = os.path.join(HERE, "authsrv.py")
SRC = open(SRC_PATH, encoding="utf-8").read()
party_heroes = getattr(authsrv, "party_heroes", None)
FIELDS = tuple(getattr(authsrv, "PARTY_SINGLE_HERO_FIELDS", ()))


def shape(row, key="k"):
    """party_heroes' answer, or ('SystemExit', message), or ('raised', repr)."""
    try:
        return party_heroes(row, key)
    except SystemExit as exc:
        return ("SystemExit", str(exc))
    except Exception as exc:                  # noqa: BLE001 -- the defect WAS a KeyError
        return ("raised", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- 1. party_heroes
print("\n1. party_heroes: the row's hero list, [] for the player alone, None for "
      "the single-hero shape")
led.ok(callable(party_heroes) and "hero" in FIELDS and "body" in FIELDS,
       "authsrv.party_heroes exists and PARTY_SINGLE_HERO_FIELDS names the hero and "
       "its body", f"party_heroes={party_heroes!r}, fields={FIELDS}")
if callable(party_heroes):
    listed = {"heroes": [{"hero": 3, "body": "academy_monk"}], "player_level": 3}
    got = shape(listed)
    led.ok(got == [{"hero": 3, "body": "academy_monk"}]
           and got[0] is not listed["heroes"][0],
           "a `heroes` list comes back as dict COPIES (main() keys HERO_ROWS by them)", got)
    led.ok(shape({"heroes": [], "player_level": 3}) == [],
           "`heroes = []` is the player alone: []")
    player_only = {"player_profession": 1, "player_level": 3, "player_skills": [1, 2]}
    led.ok(shape(player_only) == [],
           "a row with NEITHER `heroes` nor `hero` is the player alone too -- the "
           "heroless sandbox overlay's row, which died on KeyError: 'hero'",
           shape(player_only))
    led.ok(shape({"hero": 3, "body": "academy_monk", "skills": [281]}) is None,
           "a row with `hero` is the SLICE-H2 single-hero shape: None")
    slice_row = agents.WORLD.get("party", "slice")
    led.ok(shape(slice_row) is None,
           "and the tree's own [party.slice] reads as that shape",
           shape(slice_row))
    stray = shape({"body": "academy_monk", "skills": [281], "player_level": 3}, "x")
    led.ok(isinstance(stray, tuple) and stray[0] == "SystemExit"
           and "--party 'x'" in stray[1] and "body, skills" in stray[1]
           and "no `hero`" in stray[1],
           "a hero's fields WITHOUT `hero` are refused naming the row and the fields, "
           "not read as heroless (that would drop the hero) and not a KeyError", stray)
    lone = {f: shape({f: 1, "player_level": 3}) for f in FIELDS if f != "hero"}
    led.ok(len(lone) == 10 and all(isinstance(v, tuple) and v[0] == "SystemExit"
                                   and f in v[1] for f, v in lone.items()),
           "each of the ten single-hero fields alone is refused by name",
           {f: v for f, v in lone.items() if not (isinstance(v, tuple) and v[0] == "SystemExit")})

# ---------------------------------------------------------------- 2. locks
print("\n2. LOCKS: main() reads its row through party_heroes, and the refusal's "
      "field list covers every key the party block reads")
led.ok(SRC.count("_pheroes = party_heroes(_prow, a.party)") == 1
       and '_prow.get("heroes")' not in SRC,
       "LOCK: main() calls party_heroes(_prow, a.party) once and no longer reads "
       "_prow.get(\"heroes\") itself")
TREE = ast.parse(SRC)
main_fn = next((n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
party_if = None
if main_fn is not None:
    party_if = next((n for n in main_fn.body if isinstance(n, ast.If)
                     and isinstance(n.test, ast.Attribute) and n.test.attr == "party"
                     and isinstance(n.test.value, ast.Name) and n.test.value.id == "a"), None)
read = set()
if party_if is not None:
    for n in ast.walk(party_if):
        if (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                and n.value.id in ("_prow", "_first")
                and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)):
            read.add(n.slice.value)
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "get" and isinstance(n.func.value, ast.Name)
              and n.func.value.id in ("_prow", "_first")
              and n.args and isinstance(n.args[0], ast.Constant)):
            read.add(n.args[0].value)
led.ok({"hero", "body", "skills", "weapon", "level"} <= read,
       "the scan sees main()'s party block reading the single-hero fields (a scan "
       "that finds nothing would pass the next check vacuously)", sorted(read))
led.ok(read and read <= set(FIELDS),
       "LOCK: every key main()'s party block reads off the row or the first hero is "
       "in PARTY_SINGLE_HERO_FIELDS -- a new single-hero field joins the refusal",
       sorted(read - set(FIELDS)))

# ---------------------------------------------------------------- 3. main() end to end
print("\n3. main() end to end: authsrv.py --party KEY --list-probes, three arms at once")


def launch(party, extra):
    env = dict(os.environ)
    env["RURIK_CONTENT_EXTRA"] = extra        # "" = no extra dir (content.extra_dirs_from_env)
    return subprocess.Popen([sys.executable, SRC_PATH, "--party", party, "--list-probes"],
                            cwd=os.path.dirname(os.path.dirname(HERE)), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")


with tempfile.TemporaryDirectory() as tmp:
    spec = dict(sandbox.example_spec(), name="heroless", heroes=[])
    try:
        compiled = sandbox.compile_spec(spec, agents.WORLD, os.path.join(tmp, "a"),
                                        exe="X", dat="X", store={})
    except sandbox.SpecError as exc:
        compiled = None
        led.skip("3. main() end to end", f"the example spec does not compile against "
                 f"this tree's content: {exc}")
    if compiled is not None:
        sandbox.write_overlay(compiled)
        # (B): the defect's TOML -- the same overlay as the compiler wrote it
        # before the fix, with no heroes line at all
        text_b = "\n".join(ln for ln in compiled["overlay"].split("\n")
                           if ln.strip() != "heroes = []")
        dir_b = os.path.join(tmp, "b", "heroless")
        os.makedirs(dir_b)
        with open(os.path.join(dir_b, "world.toml"), "w", encoding="utf-8") as fh:
            fh.write(text_b)
        row_b = tomllib.loads(text_b)["party"]["sandbox"]
        led.ok("heroes" not in row_b and "hero" not in row_b
               and "heroes = []" in compiled["overlay"],
               "arm (B) is the defect's row: the compiled overlay says `heroes = []`, "
               "and without that line the row carries neither `heroes` nor `hero`",
               sorted(row_b))
        arms = {
            "A": ("sandbox", compiled["overlay_dir"],
                  "PARTY 'sandbox': NO heroes -- the player alone"),
            "B": ("sandbox", dir_b, "PARTY 'sandbox': NO heroes -- the player alone"),
            "C": ("slice", "", "PARTY 'slice': hero 3 in the body of 'academy_monk'"),
        }
        procs = {k: launch(p, d) for k, (p, d, _) in arms.items()}
        outs = {}
        for k, pr in procs.items():
            try:
                out, _ = pr.communicate(timeout=180)
            except subprocess.TimeoutExpired:
                pr.kill()
                out, _ = pr.communicate()
                out = (out or "") + "\n[TIMEOUT after 180 s]"
            outs[k] = (pr.returncode, out or "")
        what = {"A": "(A) a heroless spec compiled by sandbox.compile_spec",
                "B": "(B) the same overlay without `heroes = []` (the defect's TOML)",
                "C": "(C) [party.slice], the single-hero shape (positive control)"}
        for k, (_p, _d, want) in arms.items():
            rc, out = outs[k]
            good = (rc == 0 and "Traceback" not in out and want in out
                    and "Probes -- scripted one-packet experiments" in out)
            tail = "\n".join(out.strip().split("\n")[-6:])
            led.ok(good, f"{what[k]}: main() exits 0, prints {want!r}, and reaches "
                   f"the probe list past the party block",
                   f"rc={rc}" if good else f"rc={rc}\n{tail}")

sys.exit(led.verdict())
