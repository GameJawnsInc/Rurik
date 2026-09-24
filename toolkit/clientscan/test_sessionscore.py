"""Checks for sessionscore.py's WARP ROW (DESKWORK-D10 step 2 / MOVECODE-1z-do).

sessionscore is the movement regression scorecard (studies/movecode/review). Every
metric it prints has had a per-arc scorer and a test EXCEPT the warp row, which is why
four post-ship hard jumps on 09-13 sat unread for eleven days: the file had no hard/warp
row at all, and its capture discovery only globs `-c1.jsonl` so it could not even open the
`-c4`/`-c5` connections the corner regime lives in.

This file gives the warp row its first test. Sections 1-4 are BARE-MACHINE -- synthetic
`movesync`-format wire rows written to a temp file, no vault -- and drive every rule:
  1. the two-arm bar is REUSED (a planted 600 u/0.1 s jump is caught; a 100 u walk is not);
  2. attribution is a SUSPECT (nearest preceding send within 3 s; a wall-slide re-grant in
     that window flagged separately, because an ordinary lead can be nearer in time);
  3. the traps the arc paid for: a jump landing ON a point we granted is `on_grant` (the
     client obeying, not a separation snap), and a magnitude under the 299.33 u gate reads
     `under_gate1`;
  4. the KNOWN-BAD ARM -- with the re-grant removed the same jump keeps its nearest send
     but loses `regrant_before`, and a clean walk reads n = 0 (the vacuity guard).
Section 5 runs the three REAL controls when the vault is present: the 09-13 corner
captures (`c4`, `c5`) each read 2 hard rows with the attribution 1z-do adjudicates, and a
09-12 capture reads 0 -- a positive control that fires on the known-bad session and a
negative that does not, so a warp row that passed the corner captures would be measuring
nothing.

Read-only. Stdlib only. Sections 1-4 need no vault; section 5 declares a skip without it.
"""
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                                       # toolkit/clientscan
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "studies", "movecode", "review"))

import checks                                                  # noqa: E402
import sessionscore as S                                       # noqa: E402
import movesync                                                # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run measured 2026-09-24 in this worktree: 28 checks with the vault
# present, 21 bare (section 5's seven real controls are the difference and declare a skip).
# The floor is the WEAKEST healthy configuration's count -- a skip does not lower a floor
# (checks.py counts executed checks) -- so it is the bare count, 21.
LEDGER = checks.Ledger("sessionscore warp row", floor=21)
check = checks.adopt(LEDGER)

T0 = 1_000_000_000.0          # a wall epoch no real capture overlaps


def report_row(t, x, y, plane=0, op=0x3D):
    """A movesync-format c2s self-report. `warpscan`/`load_wire_reports` read vals[1:3]."""
    return {"kind": "decoded", "opcode": op,
            "values": [32829, [float(x), float(y)], int(plane), [1.0, 0.0], 1],
            "t": t, "wall_unix": T0 + t}


def grant_row(t, x, y, label="KBD LEAD", aid=1):
    """A 0x0029 send. `load_grants` reads the agent id and xy from the packed bytes; the
    warp row's attribution reads the label."""
    plain = struct.pack("<HIffHH", 0x29, aid, float(x), float(y), 0, 0).hex()
    return {"kind": "sent", "opcode": 0x29, "plain": plain, "label": label,
            "t": t, "wall_unix": T0 + t}


def write_cap(rows):
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="sswarp_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


def walk(n=14, x0=1000.0, y0=1000.0, step=30.0, dt=0.2, t0=0.0, plane=0):
    """A plain walk: n reports, `step` u apart, `dt` s apart -- 150 u/s, under run speed."""
    out = []
    for i in range(n):
        out.append(report_row(round(t0 + i * dt, 3), x0 + i * step, y0, plane))
    return out


# ---------------------------------------------------------------------------
# 1. THE BAR IS REUSED, AND IT DISCRIMINATES.
# ---------------------------------------------------------------------------
# A 600 u displacement over 0.1 s is 6,000 u/s -- over the 400 u/s speed arm at dt >= 0.05 s.
rows = walk()
# insert a hard jump between report 7 (t=1.4) and 8 (t=1.5): move x by 600 in 0.1 s
jrows = walk(n=8) + [report_row(1.5, 1000.0 + 7 * 30 + 600.0, 1000.0)] + \
    [report_row(round(1.5 + 0.2 * i, 3), 1000.0 + 7 * 30 + 600.0 + 30 * i, 1000.0) for i in range(1, 6)]
path = write_cap(jrows)
w = S.warp_rows(path, jrows)
os.unlink(path)
check(not w["refuse_all"], "1a. enough intervals to rate (vacuity guard)",
      "%d intervals >= %d" % (w["intervals"], movesync.MIN_INTERVALS))
check(w["n"] == 1, "1b. the planted 600 u / 0.1 s jump is caught by the two-arm bar",
      "n=%d" % w["n"])
check(w["rows"] and abs(w["rows"][0]["dist"] - 600.0) < 1.0,
      "1c. the row carries the displacement, not the implied speed",
      "dist=%s" % (w["rows"][0]["dist"] if w["rows"] else None))
check(w["mag_max"] is not None and abs(w["mag_max"] - 600.0) < 1.0,
      "1d. mag_max is the magnitude", "%s" % w["mag_max"])

# KNOWN-BAD ARM for the bar: a 100 u step at the same 0.1 s is 1,000 u/s -- wait, that IS
# over 400. Use 0.5 s so 100 u / 0.5 s = 200 u/s, a walk. It must NOT be caught.
clean = walk(n=14)
path = write_cap(clean)
wc = S.warp_rows(path, clean)
os.unlink(path)
check(not wc["refuse_all"] and wc["n"] == 0,
      "1e. KNOWN-BAD ARM: a pure 150 u/s walk scores ZERO hard rows",
      "n=%d over %d intervals" % (wc["n"], wc["intervals"]))
check(wc["rate_active"] == 0.0, "1f. a clean session's active-minute rate is 0", "%s" % wc["rate_active"])

# a jump that clears the DISTANCE arm below the dt floor: 540 u over 0.03 s (>= 520 u, dt < 0.05).
drows = walk(n=8) + [report_row(1.43, 1000.0 + 7 * 30 + 540.0, 1000.0)] + \
    [report_row(round(1.43 + 0.2 * i, 3), 1000.0 + 7 * 30 + 540.0 + 30 * i, 1000.0) for i in range(1, 6)]
path = write_cap(drows)
wd = S.warp_rows(path, drows)
os.unlink(path)
check(wd["n"] == 1 and wd["rows"][0]["dt"] < movesync.HARD_JUMP_MIN_DT,
      "1g. the DISTANCE arm fires below the dt floor (>= 520 u, dt < 0.05 s)",
      "n=%d dt=%.3f" % (wd["n"], wd["rows"][0]["dt"] if wd["rows"] else -1))

# ---------------------------------------------------------------------------
# 2. ATTRIBUTION IS A SUSPECT: nearest preceding send, and a wall-slide re-grant flagged.
# ---------------------------------------------------------------------------
# jump at t=1.5; a wall-slide re-grant sent at t=0.9 (1.06 s... use 0.6 s before), a plain
# lead at t=1.45 (nearer). The nearest SEND must be the plain lead; the re-grant must be
# flagged separately.
base = walk(n=8) + [report_row(1.5, 1000.0 + 7 * 30 + 600.0, 1000.0)] + \
    [report_row(round(1.5 + 0.2 * i, 3), 1000.0 + 7 * 30 + 600.0 + 30 * i, 1000.0) for i in range(1, 6)]
attr = base + [
    grant_row(0.9, 5000.0, 5000.0, "KBD LEAD RE-GRANT 1 (5000,5000) from (1,1) plane 0 [wall-slide] the copy arriving"),
    grant_row(1.45, 2000.0, 1000.0, "KBD LEAD (2000,1000) from (1,1) plane 0 [dir zero-lead]"),
]
attr.sort(key=lambda r: r["t"])
path = write_cap(attr)
wa = S.warp_rows(path, attr)
os.unlink(path)
r0 = wa["rows"][0]
check(r0["nearest_send"] is not None and r0["nearest_send"]["tag"] == "kbd-lead",
      "2a. nearest preceding SEND is the plain lead (0.05 s), not the re-grant (0.60 s)",
      "%s" % r0["nearest_send"])
check(r0["regrant_before"] is not None,
      "2b. a wall-slide re-grant within 3 s is flagged SEPARATELY from the nearest send",
      "regrant %s s before" % r0["regrant_before"])
check(wa["n_regrant"] == 1, "2c. the summary counts the re-grant-adjacent row", "%d" % wa["n_regrant"])

# KNOWN-BAD ARM: remove the re-grant. The nearest send is unchanged; regrant_before clears.
attr2 = [r for r in attr if "RE-GRANT" not in str(r.get("label", ""))]
path = write_cap(attr2)
wa2 = S.warp_rows(path, attr2)
os.unlink(path)
check(wa2["rows"][0]["regrant_before"] is None,
      "2d. KNOWN-BAD ARM: with no re-grant in the window, regrant_before is None",
      "%s" % wa2["rows"][0]["regrant_before"])
check(wa2["rows"][0]["nearest_send"]["tag"] == "kbd-lead",
      "2e. ...and the nearest send is still the plain lead (attribution is independent)",
      "%s" % wa2["rows"][0]["nearest_send"])
check(wa2["n_regrant"] == 0, "2f. the re-grant-adjacent count drops to 0", "%d" % wa2["n_regrant"])

# a send OUTSIDE the 3 s window is not attributed.
far = base + [grant_row(-2.0, 2000.0, 1000.0, "KBD LEAD (2000,1000) plane 0")]
far.sort(key=lambda r: r["t"])
path = write_cap(far)
wf = S.warp_rows(path, far)
os.unlink(path)
check(wf["rows"][0]["nearest_send"] is None,
      "2g. a send older than the 3 s window is not attributed",
      "%s" % wf["rows"][0]["nearest_send"])

# ---------------------------------------------------------------------------
# 3. THE TRAPS THE ARC PAID FOR: on_grant, and under_gate1.
# ---------------------------------------------------------------------------
# a jump LANDING on a point we granted 0.2 s earlier is the client obeying, not a snap.
land_x, land_y = 1000.0 + 7 * 30 + 600.0, 1000.0
og = base + [grant_row(1.3, land_x, land_y, "AGENT_MOVE_TO_POINT ROUTER one leg")]
og.sort(key=lambda r: r["t"])
path = write_cap(og)
wog = S.warp_rows(path, og)
os.unlink(path)
check(wog["rows"][0]["on_grant"] is True,
      "3a. a jump landing on a point we granted in the last 1 s is on_grant (obeying, not a snap)",
      "on_grant=%s" % wog["rows"][0]["on_grant"])
check(wog["n_on_grant"] == 1, "3b. the summary books the on-grant landing", "%d" % wog["n_on_grant"])
# the plain jump (no grant at the landing) is NOT on_grant -- the control for 3a.
check(wa["rows"][0]["on_grant"] is False,
      "3c. CONTROL: a jump NOT landing on a grant is not on_grant",
      "on_grant=%s" % wa["rows"][0]["on_grant"])

# under_gate1: the 600 u jump is over 299.33; a 200 u jump at 0.03 s (distance arm needs
# >= 520, so use the SPEED arm: 200 u / 0.1 s = 2000 u/s) is under gate-1.
u1 = walk(n=8) + [report_row(1.5, 1000.0 + 7 * 30 + 200.0, 1000.0)] + \
    [report_row(round(1.5 + 0.2 * i, 3), 1000.0 + 7 * 30 + 200.0 + 30 * i, 1000.0) for i in range(1, 6)]
path = write_cap(u1)
wu1 = S.warp_rows(path, u1)
os.unlink(path)
check(wu1["n"] == 1 and wu1["rows"][0]["under_gate1"] is True,
      "3d. a 200 u jump reads under_gate1 (a 'snap' cannot be the 299.33 u gate)",
      "dist=%s under=%s" % (wu1["rows"][0]["dist"], wu1["rows"][0]["under_gate1"]))
check(w["rows"][0]["under_gate1"] is False,
      "3e. CONTROL: the 600 u jump is NOT under gate-1", "%s" % w["rows"][0]["under_gate1"])

# ---------------------------------------------------------------------------
# 4. score_capture threads cap_path through, and a missing cap_path is tolerated.
# ---------------------------------------------------------------------------
check("warp" not in S.score_capture([], None, None),
      "4a. score_capture with no cap_path omits the warp row (a rows-only caller still works)")
mini = write_cap(jrows)
# score_capture reads the gamesrv stream via w0score.load_gamesrv; a synthetic file of
# decoded rows loads with no reports/grants of the other kinds, and the warp row still runs.
try:
    sc = S.score_capture(S.load_cap(mini), None, mini)
    ran = "warp" in sc and "error" not in sc["warp"]
except Exception as e:                                          # noqa: BLE001
    ran = False
    print("  [note] score_capture on synthetic: %s" % e)
os.unlink(mini)
check(ran, "4b. score_capture computes the warp row when cap_path is given")

# ---------------------------------------------------------------------------
# 5. THE REAL CONTROLS (vault-gated): the 09-13 corner captures and a 09-12 negative.
# ---------------------------------------------------------------------------
CAPS = None
try:
    # require_dir raises SystemExit (not Exception) when the vault is absent, so a
    # bare-machine run declares the skip rather than dying without a verdict.
    CAPS = vaultpath.require_dir("captures", "gamesrv", why="the warp row's real controls")
except SystemExit:
    LEDGER.skip("5. real 09-13/09-12 controls", "no gamesrv captures (bare machine)")
except Exception as e:                                          # noqa: BLE001
    LEDGER.skip("5. real 09-13/09-12 controls", "no gamesrv captures: %s" % e)

if CAPS is not None:
    def real(name):
        p = os.path.join(CAPS, name)
        if not os.path.exists(p):
            return None
        return S.warp_rows(p, S.load_cap(p))

    c5 = real("authsrv-20260913T190815-c5.jsonl")
    c4 = real("authsrv-20260913T174629-c4.jsonl")
    neg = real("authsrv-20260912T151709-c2.jsonl")
    if c5 is None or c4 is None or neg is None:
        LEDGER.skip("5. real 09-13/09-12 controls", "one of c4/c5/09-12 is not in the vault")
    else:
        # POSITIVE: the two 09-13 corner captures each read exactly 2 hard rows.
        check(c5["n"] == 2, "5a. POSITIVE: 190815-c5 reads 2 hard rows", "n=%d" % c5["n"])
        check(c4["n"] == 2, "5b. POSITIVE: 174629-c4 reads 2 hard rows", "n=%d" % c4["n"])
        # NEGATIVE: a 09-12 capture with 29 re-grants reads 0 -- re-grants are not warps.
        check(neg["n"] == 0,
              "5c. NEGATIVE: 151709-c2 (29 re-grants) reads 0 hard rows -- a metric that "
              "passed the corner captures would be measuring nothing", "n=%d" % neg["n"])
        # the adjudicated rows: c5 t=172.59 is re-grant-adjacent, under gate-1, plane flip;
        # c5 t=142.57 lands ON our grant; c4 t=118.41 is re-grant-adjacent, over gate-1.
        r172 = next((r for r in c5["rows"] if abs(r["t"] - 172.59) < 0.1), None)
        r142 = next((r for r in c5["rows"] if abs(r["t"] - 142.57) < 0.1), None)
        check(r172 is not None and r172["regrant_before"] is not None
              and r172["under_gate1"] is True and r172["plane_flip"] is True,
              "5d. c5 t=172.59: wall-slide re-grant before, under gate-1, plane flip (1z-do)",
              "%s" % (r172))
        check(r142 is not None and r142["on_grant"] is True,
              "5e. c5 t=142.57 (649 u) lands ON our grant -- the client obeying, not a snap",
              "on_grant=%s" % (r142["on_grant"] if r142 else None))
        r118 = next((r for r in c4["rows"] if abs(r["t"] - 118.41) < 0.1), None)
        check(r118 is not None and r118["regrant_before"] is not None
              and r118["under_gate1"] is False,
              "5f. c4 t=118.41 (439 u): wall-slide re-grant 0.25 s before, OVER gate-1 -- "
              "the strongest suspect, on a STRAIGHT wall not the concave corner",
              "%s" % (r118))
        # the negative has re-grants but no warp: re-grant is not sufficient for a warp.
        check(sum(1 for r in [c4, c5] if r["n_regrant"] >= 1) == 2,
              "5g. both 09-13 captures carry a re-grant-adjacent row; the 09-12 negative has none")

sys.exit(LEDGER.verdict())
