"""Checks for sessionscore.py's WARP ROW (DESKWORK-D10 step 2 / MOVECODE-1z-do).

sessionscore is the movement regression scorecard (studies/movecode/review). Every
metric it prints has had a per-arc scorer and a test EXCEPT the warp row, which is why
four post-ship hard jumps on 09-13 sat unread for eleven days: the file had no hard/warp
row at all, and its capture discovery globbed only `-c1.jsonl` so it could not even open the
`-c4`/`-c5` connections the corner regime lives in.

This file gives the warp row its first test. Sections 1-4 are BARE-MACHINE -- synthetic
`movesync`-format wire rows written to a temp file, no vault -- and drive every rule:
  1. the two-arm bar is REUSED (a planted 600 u/0.1 s jump is caught; a 100 u walk is not);
  2. attribution is a SUSPECT (nearest preceding PLAYER send within 3 s -- a hero/creature
     0x0029 is excluded; a wall-slide re-grant in that window flagged separately, because an
     ordinary lead can be nearer in time);
  3. the traps the arc paid for: a jump landing ON a point we granted BEFORE the landing is
     `on_grant` (the client obeying, not a separation snap), while a grant sent AFTER the
     landing that echoes it (our STOP-ECHO) is NOT -- the known-bad arm behind WARP-R1; and
     a between-frame move under 299.33 u reads `under_gate1`, an ANNOTATION, not the gate;
  4. the KNOWN-BAD ARM -- with the re-grant removed the same jump keeps its nearest send but
     loses `regrant_before`, and a clean walk reads n = 0 (the vacuity guard); and the report
     verdict itself -- n>0 is RED, a warp that could not run is RED, a refusal keeps the count.
Section 5 runs the three REAL controls when the vault is present: the 09-13 corner
captures (`c4`, `c5`) each read 2 hard rows with the attribution 1z-do adjudicates (the
server's own drift and gate1-red carried per row), and a 09-12 capture reads 0 -- a positive
control that fires on the known-bad session and a negative that does not, so a warp row that
passed the corner captures would be measuring nothing; plus the glob now reaches `-c4`/`-c5`.

Read-only. Stdlib only. Sections 1-4 need no vault; section 5 declares a skip without it.
"""
import copy
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

# Floor from the green run measured 2026-09-24 in this worktree (fix pass): 37 checks with the
# vault present, 28 bare (section 5's nine real controls are the difference and declare a skip).
# The floor is the WEAKEST healthy configuration's count -- a skip does not lower a floor
# (checks.py counts executed checks) -- so it is the bare count, 28.
LEDGER = checks.Ledger("sessionscore warp row", floor=28)
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

# KNOWN-BAD ARM for the bar: a plain 150 u/s walk (walk() steps 30 u every 0.2 s). It must
# NOT be caught -- the vacuity guard, so the bar is discriminating and not always-red.
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

# a NON-player 0x0029 (a hero FORMATION order, aid != 1) NEARER in time than the player's
# lead must NOT become the nearest send -- attribution filters to the player, as load_grants
# does. This is the c4 t=118.41 bug: the nearest send was agent 200's formation grant.
hero = base + [
    grant_row(1.45, 9000.0, 9000.0, "KBD LEAD (9000,9000) plane 0", aid=1),          # player, 0.05 s
    grant_row(1.48, 3000.0, 3000.0, "FORMATION: agent 200 -> slot (3000,3000)", aid=200),  # hero, 0.02 s (nearer)
]
hero.sort(key=lambda r: r["t"])
path = write_cap(hero)
wh = S.warp_rows(path, hero)
os.unlink(path)
check(wh["rows"][0]["nearest_send"] is not None and wh["rows"][0]["nearest_send"]["tag"] == "kbd-lead",
      "2h. a hero 0x0029 (aid=200) nearer in time is EXCLUDED; nearest is the player lead",
      "%s" % wh["rows"][0]["nearest_send"])

# ---------------------------------------------------------------------------
# 3. THE TRAPS THE ARC PAID FOR: on_grant (before vs after the landing), and under_gate1.
# ---------------------------------------------------------------------------
# a jump LANDING on a point we granted 0.2 s BEFORE is the client obeying, not a snap.
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

# KNOWN-BAD ARM (WARP-R1/ENG-1): a grant sent AT/AFTER the landing that REPEATS the landing
# point -- our STOP-ECHO echoes the client's stop 0.6 ms later -- must NOT read on_grant. A
# window reaching past the landing counted it and booked every stop-report jump as "obeying".
# The jump is report 7 (t=1.4) -> report 8 (t=1.5); the echo grant lands at t=1.51 on the point.
echo = base + [grant_row(1.51, land_x, land_y, "KBD STOP-ECHO (%d,%d)" % (land_x, land_y))]
echo.sort(key=lambda r: r["t"])
path = write_cap(echo)
wecho = S.warp_rows(path, echo)
os.unlink(path)
check(wecho["rows"][0]["on_grant"] is False,
      "3c'. KNOWN-BAD ARM: a grant sent AFTER the landing that echoes it is NOT on_grant",
      "on_grant=%s" % wecho["rows"][0]["on_grant"])
# and a grant at the same point sent 0.2 s BEFORE the same landing still reads on_grant -- so
# 3c' is the direction of the window, not the point (the fix is strictly-before, not exclude-point).
before = base + [grant_row(1.30, land_x, land_y, "KBD LEAD (%d,%d)" % (land_x, land_y))]
before.sort(key=lambda r: r["t"])
path = write_cap(before)
wbefore = S.warp_rows(path, before)
os.unlink(path)
check(wbefore["rows"][0]["on_grant"] is True,
      "3c''. CONTROL: the SAME point granted 0.2 s BEFORE the landing still reads on_grant",
      "on_grant=%s" % wbefore["rows"][0]["on_grant"])

# under_gate1: the 600 u jump is over 299.33; a 200 u jump at 0.03 s (distance arm needs
# >= 520, so use the SPEED arm: 200 u / 0.1 s = 2000 u/s) is under gate-1.
u1 = walk(n=8) + [report_row(1.5, 1000.0 + 7 * 30 + 200.0, 1000.0)] + \
    [report_row(round(1.5 + 0.2 * i, 3), 1000.0 + 7 * 30 + 200.0 + 30 * i, 1000.0) for i in range(1, 6)]
path = write_cap(u1)
wu1 = S.warp_rows(path, u1)
os.unlink(path)
check(wu1["n"] == 1 and wu1["rows"][0]["under_gate1"] is True,
      "3d. a 200 u between-frame move reads under_gate1 (an ANNOTATION: it did not travel 300 u; "
      "NOT the gate, which is the copy-to-body separation the server measures)",
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
# 4'. THE REPORT VERDICT is a check that can go red (ENG-5/ENG-6). warp_report_lines is
# the factored verdict, so the RED/OK, the silent-error trap and the refusal rule are
# testable without a whole-session fixture.
# ---------------------------------------------------------------------------
z = S.warp_report_lines({"n": 0, "refuse_all": False, "intervals": 30, "active_threshold": 1.0,
                         "mag_min": None, "mag_p50": None, "mag_max": None, "rate_active": 0.0,
                         "n_regrant": 0, "n_on_grant": 0, "n_under_gate1": 0, "n_gate1_red": 0,
                         "n_client_reseed": 0, "rows": []})
check(z and z[0][2].startswith("OK"), "4c. a clean warp row (n=0) reports OK", "%s" % (z[0][2] if z else None))
one = S.warp_report_lines({"n": 1, "refuse_all": False, "intervals": 30, "active_threshold": 1.0,
                           "mag_min": 649.0, "mag_p50": 649.0, "mag_max": 649.0, "rate_active": 1.5,
                           "n_regrant": 0, "n_on_grant": 0, "n_under_gate1": 0, "n_gate1_red": 1,
                           "n_client_reseed": 0,
                           "rows": [{"t": 1.0, "dist": 649.0, "dt": 0.07, "speed": 9553,
                                     "plane_flip": False, "nearest_send": None, "regrant_before": None,
                                     "on_grant": False, "under_gate1": False, "drift": 674.0,
                                     "gate1": {"budget": 336.5}, "gate1_red": True}]})
check(one[0][2].startswith("RED"), "4d. one hard row reports RED (band is 0)", "%s" % one[0][2])
# KNOWN-BAD ARM: a warp row that RAISED must print RED, never vanish (a run that measured
# nothing failed). Reproduces ENG-5: score_capture had wrapped warp_rows in a bare except and
# report() dropped the {'error': ...} without a line.
err = S.warp_report_lines({"error": "boom"})
check(len(err) == 1 and err[0][2].startswith("RED"),
      "4e. KNOWN-BAD ARM: a warp row that could not run reports RED, not nothing",
      str(err[0]) if err else "None")
# rule 7: a refusal withholds the RATE, but the COUNT is still shown (movesync header rule 7).
ref = S.warp_report_lines({"n": 1, "refuse_all": True, "intervals": 4, "active_threshold": None,
                           "mag_min": 540.0, "mag_p50": 540.0, "mag_max": 540.0, "rate_active": None,
                           "n_regrant": 0, "n_on_grant": 0, "n_under_gate1": 0, "n_gate1_red": 0,
                           "n_client_reseed": 0,
                           "rows": [{"t": 1.0, "dist": 540.0, "dt": 0.03, "speed": 18000,
                                     "plane_flip": False, "nearest_send": None, "regrant_before": None,
                                     "on_grant": False, "under_gate1": False, "drift": None,
                                     "gate1": None, "gate1_red": False}]})
check("1" in ref[0][1] and "not rated" in ref[0][3],
      "4f. rule 7: a refusal shows the COUNT and withholds only the rate", "%s | %s" % (ref[0][1], ref[0][3]))

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
        # the adjudicated rows (movecode 1z-do.3, corrected this pass):
        #   c5 172.59 -- re-grant walked the copy over the SEPARATION gate: the SERVER's own
        #     drift is over 299.33 u and its guard read gate1-red (under_gate1 is only a
        #     between-frame annotation, and it is True here for a jump that IS over the gate);
        #   c5 142.57 -- a 649 u snap-back, NOT on our grant (the point it matches is the
        #     STOP-ECHO we send AFTER the report; strictly-before clears it);
        #   c4 118.41 -- the nearest send is the PLAYER's lead, not a hero grant, and the
        #     server read gate1-red; a STRAIGHT wall, not the concave corner.
        r172 = next((r for r in c5["rows"] if abs(r["t"] - 172.59) < 0.1), None)
        r142 = next((r for r in c5["rows"] if abs(r["t"] - 142.57) < 0.1), None)
        check(r172 is not None and r172["regrant_before"] is not None
              and r172["plane_flip"] is True and r172["gate1_red"] is True
              and r172["drift"] is not None and r172["drift"] > S.GATE1_UNITS,
              "5d. c5 t=172.59: wall-slide re-grant before, plane flip, and the SERVER over the "
              "gate (drift > 299.33, gate1-red) -- 1z-do's mechanism witness, not 'under the gate'",
              "regrant=%s drift=%s gate1=%s" % (r172["regrant_before"], r172["drift"], r172["gate1"]) if r172 else "None")
        check(r142 is not None and r142["on_grant"] is False and r142["drift"] is not None
              and r142["drift"] > S.GATE1_UNITS,
              "5e. c5 t=142.57 (649 u): NOT on our grant (the STOP-ECHO is sent after the report), "
              "and the server drift is over the gate -- a real snap-back, suspect the click-drop",
              "on_grant=%s drift=%s" % (r142["on_grant"], r142["drift"]) if r142 else "None")
        r118 = next((r for r in c4["rows"] if abs(r["t"] - 118.41) < 0.1), None)
        check(r118 is not None and r118["nearest_send"] is not None
              and r118["nearest_send"]["tag"] == "kbd-lead"
              and r118["regrant_before"] is not None and r118["gate1_red"] is True
              and r118["under_gate1"] is False,
              "5f. c4 t=118.41 (439 u): nearest send is the PLAYER's lead (not a hero 0x0029), "
              "wall-slide re-grant 0.25 s before, gate1-red; a STRAIGHT wall not the concave corner",
              "nearest=%s regrant=%s gate1_red=%s" % (r118["nearest_send"], r118["regrant_before"], r118["gate1_red"]) if r118 else "None")
        # the negative has re-grants but no warp: re-grant is not sufficient for a warp.
        check(c4["n_regrant"] >= 1 and c5["n_regrant"] >= 1 and neg["n_regrant"] == 0,
              "5g. both 09-13 captures carry a re-grant-adjacent row; the 09-12 negative has none",
              "c4=%d c5=%d neg=%d" % (c4["n_regrant"], c5["n_regrant"], neg["n_regrant"]))
        # the glob reaches EVERY connection suffix (2333de81): --since must find -c4/-c5, which
        # the old -c1-only glob could not open -- half of why the rows sat unread (ENG-6).
        since = [os.path.basename(p) for p in S.captures(["--since", "20260913"])]
        check(any(p.endswith("-c4.jsonl") for p in since) and any(p.endswith("-c5.jsonl") for p in since),
              "5h. captures(--since 20260913) reaches the -c4/-c5 connections, not just -c1",
              "%d caps, has c4=%s c5=%s" % (len(since),
                                            any(p.endswith("-c4.jsonl") for p in since),
                                            any(p.endswith("-c5.jsonl") for p in since)))
        # a re-grant label WITHOUT [wall-slide] must NOT set regrant_before -- the flag is the
        # wall-slide clip, not any re-grant (ENG-6). Rewrite c5's wall-slide re-grants to [clear].
        cleared = copy.deepcopy(S.load_cap(os.path.join(CAPS, "authsrv-20260913T190815-c5.jsonl")))
        for r in cleared:
            if r.get("kind") == "sent" and r.get("opcode") == 0x29 and "[wall-slide]" in str(r.get("label", "")):
                r["label"] = str(r["label"]).replace("[wall-slide]", "[clear]")
        wcl = S.warp_rows(os.path.join(CAPS, "authsrv-20260913T190815-c5.jsonl"), cleared)
        check(wcl["n_regrant"] == 0 and all(r["regrant_before"] is None for r in wcl["rows"]),
              "5i. a re-grant labelled [clear] (not [wall-slide]) sets no regrant_before -- the "
              "flag is the wall-slide clip, not any re-grant",
              "n_regrant=%d" % wcl["n_regrant"])

sys.exit(LEDGER.verdict())
