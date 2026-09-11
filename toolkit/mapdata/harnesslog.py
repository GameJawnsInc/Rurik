"""Which gamesrv log is ours, and the three words a serve run's verdict comes in.

TWO HALVES OF ONE READING. `log_source` and `newest_harness_log` pick the log a
run's verdict may be scored off -- which is not "the newest one", for the reason
`newest_harness_log`'s docstring records at length. `NAVMESH_RE`, `PLACED_RE`
and `UNPOPULATED_RE` are the log-line CONTRACT with `toolkit/authsrv/`: they
match lines the server builds, and a copy of one is a second thing to keep in
agreement with the first. `SERVE_PASS` / `SERVE_UNPOPULATED` / `SERVE_FAILED`
are the three words those matches resolve to.

POINTERS OUT, because several comments below name things that did not move:

  * `harness_source_dir` STAYS in `deploy.py`. It derives its answer from that
    file's own `__file__`, and its docstring says so; moving it would have made
    that docstring false about the file it landed in. `serve_run` passes its
    result in as `newest_harness_log(..., source=...)`.
  * `serve_run` and `main` stay in `deploy.py`; where a comment here says "the
    caller" or "`serve_run`", that is the file to look in.
  * `spawn_population` and the `[map] navmesh` print are `toolkit/authsrv/`'s.

Read by `deploy.py` (which re-exports all eight names, so `deploy.NAVMESH_RE`
and `deploy.newest_harness_log` still resolve -- `test_deploy.py` §13 stubs the
latter through `deploy`'s globals) and by `toolkit/harness/abrun.py`, whose
`COUNTERS` take `NAVMESH_RE` and `PLACED_RE` from here by import rather than by
copy. Standard library plus `vaultpath`; nothing here writes.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import vaultpath  # noqa: E402


def log_source(log, probe=8192):
    """The directory named by a gamesrv log's `source:` line, or None.

    Read from the HEAD of the file: the line is printed at start-up, and these
    logs run to megabytes.
    """
    try:
        with open(log, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(probe)
    except OSError:
        return None
    m = re.search(r"^source:\s+(.+?)\s*$", head, re.M)
    return os.path.normcase(os.path.abspath(m.group(1))) if m else None


def newest_harness_log(after, source=None):
    """The gamesrv log of the newest harness run started after `after`.

    `source`, when given, RESTRICTS the search to captures this tree produced.

    WHY, AND IT IS NOT HYPOTHETICAL. `vault/captures/harness/` is shared by
    every session on this machine, and on 2026-08-21 THREE were running at
    once. This function used to take the newest log by mtime across the whole
    directory, so a peer session's run that happened to land inside our window
    was indistinguishable from our own -- and `serve_run` would then score OUR
    verdict off THEIR navmesh line. That is not a far-fetched race: the same
    ambiguity misled a reader by hand the same day, and the fix they used by
    hand is the one applied here -- `authsrv` prints `source: <its directory>`,
    which names the worktree, and no two worktrees share one.

    Passing `source=None` restores the old behaviour deliberately, for callers
    with no tree to match against; it is not the default anywhere.
    """
    root = os.path.join(vaultpath.require_dir(), "captures", "harness")
    best, best_t, skipped = None, after, []
    for name in os.listdir(root):
        d = os.path.join(root, name)
        log = os.path.join(d, "gamesrv.log")
        if not os.path.isfile(log):
            continue
        t = os.path.getmtime(log)
        if t <= best_t:
            continue
        if source is not None:
            got = log_source(log)
            if got != source:
                skipped.append((name, got))
                continue
        best, best_t = log, t
    if best is None and skipped:
        # Say so. A silent None here reads as "the harness wrote nothing",
        # which is a different diagnosis with a different fix.
        print(f"  note: {len(skipped)} newer capture(s) skipped as another "
              f"tree's: " + ", ".join(f"{n} ({s})" for n, s in skipped[:3]))
    return best


NAVMESH_RE = re.compile(
    r"\[map\] navmesh 0x([0-9A-Fa-f]+): (\d+) planes, (\d+) trapezoids")

# `area 'sculpt': 3 of 3 placed`. Checked because the alternative was measured:
# on the first populated run `spawn_population` threw inside instance bring-up,
# every body was absent, and NOTHING said so -- harness rc 0, all six map
# readback checks green (correctly, they are about the map), the serve check
# matched the navmesh, exit 0. The only evidence was a traceback in a log
# nobody was reading.
PLACED_RE = re.compile(r"area '([^']+)': (\d+) of (\d+) placed")

# `area 'plaza': no population rows; the world is the player and the geometry`
# -- `spawn_population`'s OTHER legitimate exit, and it is a VERDICT rather than
# an absence. The distinction this pattern draws is the whole point: a server
# that threw on the way to placing bodies prints NEITHER line, so "no line at
# all" still means what it meant. This line is positive evidence the server
# reached spawn_population, evaluated the area and had nothing to place.
#
# It was scored as a serve FAILURE until 2026-08-20. Both arms of WORLDMAPS-W2
# hit it: the navmesh half of the check passed in each (55 trapezoids, the
# server's own number against the archive's), the map was correct, and deploy
# still exited 1 saying "the client walked on our map and the server did not" --
# which was false. `vault/research/worldmaps/WORLDMAPS-W2-RUN.md` RESULTS, P6.
UNPOPULATED_RE = re.compile(
    r"area '([^']+)': no population rows; the world is the player and the "
    r"geometry")

# The three verdicts a serve run can carry. UNPOPULATED is not a softened FAIL
# and not a quiet PASS: the mesh was served and proven, and the area is empty on
# purpose. It gets its own word so a transcript cannot be read either way.
SERVE_PASS = "PASS"
SERVE_UNPOPULATED = "SERVED-UNPOPULATED"
SERVE_FAILED = "FAILED"
