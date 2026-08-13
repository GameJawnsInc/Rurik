"""The screenshot readout for the SILENT opcodes, and the four defects it shipped with.

`shotlabel` joins a sweep run's ONE send to the hold screenshots that bracket it and
scores what changed on screen. Every headline number it can print is a number a broken
version also prints, so this file is mostly negative controls: each defect below was
made while writing the module, each printed a confident wrong answer rather than an
error, and each is REPRODUCED INLINE here so the passing number is a difference between
two live answers rather than a value the test asks the code to confirm about itself.

    python toolkit/authsrv/test_shotlabel.py

NO VAULT, NO SOCKET, NO CLIENT. The frames are drawn here with PIL: a "world" of
deterministic noise, an idle frame that differs from it the way a live client's water
and compass do, a "loading screen" that differs enormously, and a "window" pasted on
like the Message of the Day panel. A scoring defect is not a property of any one
capture, and building the fixture is what lets the load-screen and the ambiguous-second
cases exist at all -- neither occurs in a run anybody would keep.

THE FIVE DEFECTS. Four were measured against the four opcodes already named by eye
(`0x0033` Message of the Day, `0x009E` chat line, `0x00B9` framed callout, `0x00C0`
floating text), which is the only reason they could be caught; the fifth was measured
against six opcodes that all reported the SAME bounding box:

  1. THE JOIN WAS BY INDEX. "The send lands 13.3 s in, so shot 13.3/cadence is the
     baseline" reads the CAPTURE's clock, which starts at the server connection, not at
     the hold. `0x0033`'s 306x443 panel scored 0.00008 that way -- the baseline already
     had the window in it. Section 2.
  2. THE NOISE FLOOR SPANNED THE MAP LOAD. Measured over every pre-send pair it was
     64% of pixels, because the first hold frames are a loading screen, and at that
     floor ALL FOUR known positives read QUIET. Section 3.
  3. THE STAMP IS ONLY GOOD TO THE SECOND. A shot inside the send's second may serve as
     neither baseline nor after-frame; using it scored the same panel 0.37%. Section 4.
  4. A PAIR CANNOT SEE A TRANSIENT. `0x00C0`'s floating text rises and fades in about
     two seconds and at a 2.3 s cadence lands BETWEEN frames -- one pair scored it
     0.190%, BELOW the same run's idle noise. Section 5.
  5. THE FLOOR WAS MEASURED AT THE WRONG LAG. Idle noise was taken between ADJACENT
     frames ~1 s apart while every post-send frame was scored against a baseline up to
     9 s behind it, so a slowly drifting scene accumulated on one side only. Six
     consecutive opcodes -- 0x0016, 0x0032, 0x0034, 0x0036, 0x003D, 0x003F -- scored
     CHANGED at 0.37% against a 0.05% floor and every one reported the same bbox,
     (824, 491, 1113, ~724): the player standing in the middle of the screen
     breathing. The floor is now measured at MATCHING lags. Section 9.

AND THE ONE THAT WAS NOT IN THIS MODULE AT ALL, which is section 7: the harness's log
pump died on a cp1252 console, the gamesrv wedged on its next print, the probe sent
NOTHING, and the run reported RUN VERDICT: PASS. Three opcodes were marked done having
never been sent. `shotloop` therefore records an opcode only when the run's own capture
holds its send, and `score_run` refuses a multi-send run outright.
"""

import datetime
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                   # noqa: E402
import shotlabel                                                # noqa: E402

# 38 is what a green run executes today, MEASURED rather than guessed. Every section
# needs PIL; without it the whole file declares one skip and goes red, the way
# test_keytap.py does off Windows -- the fixture is drawn, not stored.
LEDGER = checks.Ledger("test_shotlabel", floor=38)
ok = LEDGER.ok

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------- fixture

def _pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def _world(seed=1, w=320, h=200):
    """A deterministic 'game frame'. Noise, so a diff is not trivially zero."""
    Image = _pil()
    im = Image.new("RGB", (w, h))
    px = im.load()
    s = seed
    for y in range(h):
        for x in range(w):
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            v = (s >> 16) & 0xFF
            px[x, y] = (v // 3, v // 2, v)
    return im


def _jitter(im, n=180):
    """The same world with a few pixels moved: water, torches, the compass sweep."""
    out = im.copy()
    px = out.load()
    s = 99
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        x = (s >> 8) % out.size[0]
        y = (s >> 20) % out.size[1]
        px[x, y] = (255, 255, 255)
    return out


def _drifted(im, k, w=60, h=80):
    """The world with a SOLID block standing k pixels along -- a character breathing.

    The point is that consecutive frames differ LITTLE while the distance from frame 0
    grows with the lag: a solid block shifted one pixel changes only its two edge
    columns, so neighbours differ by ~2 columns and frames eight apart by ~16. That is
    the shape `drift_floor` exists for.

    The block must be SOLID. The first version shifted a crop of the noise world, and
    noise decorrelates completely under a one-pixel shift -- adjacent frames differed
    6.27% and frames six apart 6.06%, so the curve did not rise with the lag at all
    and the fixture could not express the defect it was built for.
    """
    Image = _pil()
    out = im.copy()
    out.paste(Image.new("RGB", (w, h), (200, 40, 40)), (40 + k, 40))
    return out


def _with_window(im, box=(90, 50, 210, 150)):
    """The same world with a panel pasted on -- the Message of the Day shape."""
    Image = _pil()
    out = im.copy()
    out.paste(Image.new("RGB", (box[2] - box[0], box[3] - box[1]), (20, 20, 30)), box)
    return out


def _run_dir(tmp, name, frames, send_wall, opcode=0x0031, capture_rows=None):
    """A harness run directory: report.json, a gamesrv capture, and hold shots.

    `frames` is [(seconds_from_T0, image)]; the mtime is what the join reads, so it is
    set explicitly rather than left to whenever the file happened to be written.
    """
    d = os.path.join(tmp, name)
    os.makedirs(d, exist_ok=True)
    cap = os.path.join(d, "gamesrv-capture.jsonl")
    rows = capture_rows if capture_rows is not None else [
        {"kind": "sent", "opcode": opcode, "t": 13.3,
         "label": f"PROBE[smsgsweep] [1/1] 0x{opcode:04X} (FORWARDER)",
         "wall": send_wall.strftime("%Y-%m-%dT%H:%M:%SZ")}]
    with open(cap, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    with open(os.path.join(d, "report.json"), "w", encoding="utf-8") as fh:
        json.dump({"captures": [cap], "passed": True}, fh)
    for i, (dt, im) in enumerate(frames, 1):
        p = os.path.join(d, f"hold{i:03d}.png")
        im.save(p)
        t = (T0 + datetime.timedelta(seconds=dt)).timestamp()
        os.utime(p, (t, t))
    return d


def _standard(tmp, name, send_at=9.5):
    """The shape of a real run: load frames, idle frames, then a window that stays.

    Frames 1-2 are the LOADING SCREEN (a different image entirely), 3-5 are idle world
    frames, and every frame from 6 on carries the window -- which is what a panel does,
    as against a transient.

    THE HOLD CLOCK AND THE CAPTURE CLOCK ARE DELIBERATELY OFFSET, because that offset
    IS defect 1. The capture stamps this send `t = 13.3` (its clock starts at the
    server connection) while the shot that precedes it sits 9.0 s into the hold. A
    reader who divides 13.3 by the cadence lands two frames late, on a pair that
    ALREADY has the window in both halves -- which is how a 306x443 panel scored
    0.00008. A fixture without the offset cannot fail that way, and the first version
    of this file did not have it: the index join and the clock join picked the same
    pair and agreed to three decimal places.
    """
    world = _world(1)
    load = _world(77)
    frames = [(0.0, load), (2.0, load),
              (3.0, _jitter(world, 121)), (4.5, _jitter(world, 122)),
              (6.0, _jitter(world, 123)), (7.5, _jitter(world, 124)),
              (9.0, _jitter(world, 125))]
    for i, t in enumerate((11.3, 13.6, 15.9, 18.2, 20.5)):
        frames.append((t, _with_window(_jitter(world, 130 + i))))
    return _run_dir(tmp, name, frames, T0 + datetime.timedelta(seconds=send_at))


# ---------------------------------------------------------------- sections

def section_1_reading(tmp):
    print("\n1. a run is read from its own report, and only hold frames count")
    d = _standard(tmp, "r1")
    sends, err = shotlabel.sweep_sends(d)
    ok(err is None and len(sends) == 1 and sends[0][0] == 0x0031,
       "the sweep send is found through the report's capture",
       f"{[hex(s[0]) for s in (sends or [])]}")
    # final.png is taken AFTER the probe finishes and would give the last opcode a
    # baseline from a different phase; 1-play.png brackets the run rather than sampling.
    _pil().new("RGB", (320, 200)).save(os.path.join(d, "final.png"))
    _pil().new("RGB", (320, 200)).save(os.path.join(d, "1-play.png"))
    shots = shotlabel.hold_shots(d)
    ok(len(shots) == 12 and all("hold" in os.path.basename(p) for p, _ in shots),
       "only hold*.png is sampled -- final.png and the action shots are not",
       f"{len(shots)} frame(s)")
    ok([t for _, t in shots] == sorted(t for _, t in shots),
       "and they come back in time order")


def section_2_join_by_clock(tmp):
    print("\n2. the join is by wall clock -- DEFECT 1, which scored a 306x443 panel 0.00008")
    d = _standard(tmp, "r2")
    res = shotlabel.score_run(d)
    row = res["rows"][0]
    ok(row["verdict"] == "CHANGED",
       "the panel is seen", f"peak {row['peak']*100:.2f}% vs flag {res['flag_at']*100:.2f}%")
    # The defect, reproduced: pick the baseline by dividing the CAPTURE's t by the shot
    # cadence. That clock starts at the server connection, not at the hold, so it lands
    # two frames late -- on a pair that already has the window in BOTH halves.
    shots = shotlabel.hold_shots(d)
    idx = int(13.3 // 2.3)                      # what the first version computed
    wrong, _ = shotlabel.diff_score(shots[idx][0], shots[idx + 1][0])
    right = row["peak"]
    ok(wrong is not None and right > wrong * 100,
       "and the index join is REPRODUCED and misses the panel entirely",
       f"by index {wrong*100:.4f}%  vs by clock {right*100:.3f}%")
    ok(shotlabel.STAMP_GRAN == 1.0,
       "the ambiguous second is a named constant, not a rounding accident")


def section_3_floor(tmp):
    print("\n3. the noise floor excludes the map load -- DEFECT 2, which read 64%")
    d = _standard(tmp, "r3")
    res = shotlabel.score_run(d)
    floor = res["floor"]
    ok(floor is not None and floor < 0.05,
       "the floor is the idle window only", f"{floor*100:.2f}% over "
                                            f"{res['floor_pairs']} pair(s)")
    # The defect: every pre-send pair, which reaches back into the loading screen.
    shots = shotlabel.hold_shots(d)
    allpairs = [shotlabel.diff_score(shots[i - 1][0], shots[i][0])[0]
                for i in range(1, len(shots))]
    naive = max(v for v in allpairs if v is not None)
    ok(naive > floor * 5,
       "and the all-pairs floor is REPRODUCED and is enormous",
       f"all-pairs {naive*100:.1f}%  vs idle-window {floor*100:.2f}%")
    ok(naive * shotlabel.NOISE_MULT > res["rows"][0]["peak"],
       "at that floor the panel would have been called QUIET -- which is what "
       "happened to all four known positives")
    # THE MEDIAN IS THE LOAD-BEARING CHOICE, and this is the check that says so: the
    # window here HOLDS a load transition (the send is 9.5 s in and the window opens
    # at 1.5 s), so the max reading is contaminated and puts the flag above 100%,
    # where nothing can ever be CHANGED.
    inwin = [v for v in allpairs[:6] if v is not None]
    ok(max(inwin) > 0.5 and floor < 0.05,
       "the window CONTAINS a load pair and the median ignores it",
       f"max-in-window {max(inwin)*100:.1f}%  median {floor*100:.2f}%")
    ok(max(inwin) * shotlabel.NOISE_MULT > 1.0,
       "and by max the threshold would exceed every possible score",
       f"flag would be {max(inwin)*shotlabel.NOISE_MULT*100:.0f}%")
    # Both bounds are load-bearing, so the window must refuse when it is too thin.
    lonely = _run_dir(tmp, "r3b", [(0.0, _world(1)), (30.0, _world(2))],
                      T0 + datetime.timedelta(seconds=13.5))
    res2 = shotlabel.score_run(lonely)
    ok(res2["rows"][0]["verdict"] == "NO_FLOOR",
       "a run with no idle pair in the window is REFUSED, not given a constant",
       res2["rows"][0]["verdict"])
    # Two pairs is not enough for a median to mean anything -- see MIN_FLOOR_PAIRS.
    w = _world(1)
    thin = _run_dir(tmp, "r3c",
                    [(5.5, _jitter(w, 1)), (7.0, _jitter(w, 2)), (8.5, _jitter(w, 3)),
                     (11.0, _with_window(_jitter(w, 4))),
                     (13.0, _with_window(_jitter(w, 5)))],
                    T0 + datetime.timedelta(seconds=9.5))
    res3 = shotlabel.score_run(thin)
    ok(res3["rows"][0]["verdict"] == "NO_FLOOR" and res3["floor_pairs"] == 2,
       "and TWO pairs is refused too -- a median of two is their mean",
       f"{res3['floor_pairs']} pair(s) -> {res3['rows'][0]['verdict']}")


def section_4_ambiguous_second(tmp):
    print("\n4. a frame inside the send's second plays no role -- DEFECT 3")
    # The send is stamped :13 and a shot lands at 13.7 -- after the stamp, unknown
    # side of the send. Using it as the after-frame scored the panel 0.37%.
    world = _world(1)
    frames = [(6.0, _jitter(world, 8)), (7.5, _jitter(world, 9)),
              (9.0, _jitter(world, 11)), (11.0, _jitter(world, 12)),
              (12.8, _jitter(world, 13)),                    # last clean baseline
              (13.7, _jitter(world, 14)),                    # INSIDE the second
              (15.5, _with_window(_jitter(world, 15))),
              (17.5, _with_window(_jitter(world, 16))),
              (19.5, _with_window(_jitter(world, 17)))]
    d = _run_dir(tmp, "r4", frames, T0 + datetime.timedelta(seconds=13))
    res = shotlabel.score_run(d)
    row = res["rows"][0]
    ok(row["verdict"] == "CHANGED", "the panel is still seen",
       f"peak {row['peak']*100:.2f}%")
    shots = shotlabel.hold_shots(d)
    ok(os.path.basename(row["before"]) == "hold005.png",
       "the baseline is the last frame STRICTLY BEFORE the stamped second",
       os.path.basename(row["before"]))
    ok(all(os.path.basename(f["path"]) != "hold006.png" for f in row["strip"]),
       "and the frame inside that second is in neither role")
    # Reproduce the defect: take hold004 as the after-frame.
    wrong, _ = shotlabel.diff_score(shots[4][0], shots[5][0])
    ok(wrong < row["peak"] / 3,
       "the ambiguous pairing is REPRODUCED and misses the panel",
       f"ambiguous {wrong*100:.3f}%  vs correct {row['peak']*100:.3f}%")


def section_5_transient(tmp):
    print("\n5. a STRIP, not a pair -- DEFECT 4, floating text between two frames")
    world = _world(1)
    # The effect exists in exactly ONE frame and is gone by the next, which is what
    # 0x00C0's floating text does. A pair whose after-frame is the LAST one sees
    # nothing at all.
    frames = [(6.0, _jitter(world, 8)), (7.5, _jitter(world, 9)),
              (9.0, _jitter(world, 11)), (11.0, _jitter(world, 12)),
              (12.8, _jitter(world, 13)),
              (15.5, _with_window(_jitter(world, 15))),      # the transient
              (17.5, _jitter(world, 16)), (19.5, _jitter(world, 17))]
    d = _run_dir(tmp, "r5", frames, T0 + datetime.timedelta(seconds=13.5))
    res = shotlabel.score_run(d)
    row = res["rows"][0]
    ok(row["verdict"] == "CHANGED", "the transient is caught by peak",
       f"peak {row['peak']*100:.2f}%")
    ok(len(row["strip"]) == 3, "every frame after the send is scored, not just one",
       f"{len(row['strip'])} frame(s)")
    ok(row["sustained"] is not None and row["sustained"] < row["peak"] / 3,
       "and sustained separates a transient from a panel that STAYS",
       f"peak {row['peak']*100:.2f}%  sustained {row['sustained']*100:.2f}%")
    # The control: the same strip for a PERSISTENT effect must NOT decay, or
    # `sustained` would just be measuring the last frame's noise.
    res2 = shotlabel.score_run(_standard(tmp, "r5b"))
    row2 = res2["rows"][0]
    ok(row2["sustained"] > row2["peak"] * 0.8,
       "CONTROL: a panel that stays reads sustained ~= peak",
       f"peak {row2['peak']*100:.2f}%  sustained {row2['sustained']*100:.2f}%")


def section_6_refusals(tmp):
    print("\n6. the refusals, and each is a run that cannot be honestly scored")
    world = _world(1)
    # NO_BASELINE: every frame is after the send.
    d = _run_dir(tmp, "r6a", [(20.0, _jitter(world, 1)), (22.0, _jitter(world, 2)),
                              (24.0, _jitter(world, 3))],
                 T0 + datetime.timedelta(seconds=13.5))
    ok(shotlabel.score_run(d)["rows"][0]["verdict"] == "NO_BASELINE",
       "no frame before the send is NO_BASELINE")
    # NO_AFTER: the hold ended before the effect could land.
    d = _run_dir(tmp, "r6b", [(9.0, _jitter(world, 1)), (11.0, _jitter(world, 2)),
                              (13.0, _jitter(world, 3))],
                 T0 + datetime.timedelta(seconds=13.5))
    ok(shotlabel.score_run(d)["rows"][0]["verdict"] == "NO_AFTER",
       "no frame after it is NO_AFTER")
    # A batched run is NOT scored badly -- it is not scored. Owner's call 2026-08-13.
    rows = [{"kind": "sent", "opcode": op, "t": 13.3 + i,
             "label": f"PROBE[smsgsweep] [{i+1}/2] 0x{op:04X} (FORWARDER)",
             "wall": (T0 + datetime.timedelta(seconds=13.5 + i * 4)).strftime(
                 "%Y-%m-%dT%H:%M:%SZ")}
            for i, op in enumerate((0x0031, 0x0058))]
    d = _run_dir(tmp, "r6c", [(9.0, _jitter(world, 1)), (11.0, _jitter(world, 2)),
                              (13.0, _jitter(world, 3)), (15.5, _jitter(world, 4)),
                              (19.5, _jitter(world, 5)), (21.5, _jitter(world, 6))],
                 T0, capture_rows=rows)
    res = shotlabel.score_run(d)
    ok(res["rows"] == [] and res["error"] and "STACK" in res["error"].upper(),
       "TWO sends in one run is refused outright -- UI effects stack",
       (res["error"] or "")[:60])
    ok("0x0031" in (res["error"] or "") and "0x0058" in (res["error"] or ""),
       "and the refusal NAMES both, so the re-run is obvious")
    # A size change is reported, never resized away: a resize puts a real difference
    # on every pixel and would read as a total redraw.
    big = _pil().new("RGB", (400, 260), (10, 10, 10))
    d = _run_dir(tmp, "r6d", [(6.0, _jitter(world, 8)), (7.5, _jitter(world, 9)),
                              (9.0, _jitter(world, 1)), (11.0, _jitter(world, 2)),
                              (12.8, _jitter(world, 3)), (15.5, big), (17.5, big)],
                 T0 + datetime.timedelta(seconds=13.5))
    row = shotlabel.score_run(d)["rows"][0]
    ok(row["verdict"] == "UNSCORABLE",
       "a frame that changed SIZE is UNSCORABLE, not resized", row["verdict"])


def section_7_no_send_is_not_a_result(tmp):
    print("\n7. a run whose probe never sent is not a measurement of anything")
    # The 2026-08-13 false green: session.py reported RUN VERDICT: PASS while the
    # gamesrv sat wedged on a blocked print and the probe sent nothing. The capture
    # was full of world ticks, so "the capture has events" proves nothing.
    ticks = [{"kind": "sent", "opcode": 0x1E, "t": 7.0 + i * 0.05,
              "label": "WORLD_SIMULATION_TICK",
              "wall": T0.strftime("%Y-%m-%dT%H:%M:%SZ")} for i in range(400)]
    world = _world(1)
    d = _run_dir(tmp, "r7", [(9.0, _jitter(world, 1)), (11.0, _jitter(world, 2)),
                             (13.0, _jitter(world, 3)), (15.5, _jitter(world, 4))],
                 T0, capture_rows=ticks)
    res = shotlabel.score_run(d)
    ok(res["rows"] == [] and "no sweep sends" in (res["error"] or ""),
       "400 world ticks and no sweep send scores NOTHING",
       (res["error"] or "")[:50])
    sends, _ = shotlabel.sweep_sends(d)
    ok(sends == [], "and sweep_sends is what shotloop gates its state file on",
       f"{len(sends)} send(s)")
    # The pump fix itself: a line the console cannot encode must not kill the reader,
    # because that reader is the only one draining the server's pipe.
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
    import session as sess
    src = open(sess.__file__, encoding="utf-8").read()
    body = src.split("def _pump(", 1)[1].split("\n    def ", 1)[0]
    ok('"replace"' in body and "except Exception" in body,
       "session._pump degrades an unencodable character and never stops reading")
    ok("errors=\"replace\"" in src.split("subprocess.Popen", 1)[1][:400],
       "and the pipe itself is already read with errors=replace")


def section_8_provenance(tmp):
    print("\n8. the page holds frames of the retail client, so it stays in the vault")
    roots = shotlabel.working_tree_roots()
    ok(len(roots) >= 1 and all(os.path.isabs(r) for r in roots),
       "every checkout of this repo is known", f"{len(roots)} tree(s)")
    refused = 0
    for root in roots:
        try:
            shotlabel.resolve_out(os.path.join(root, "toolkit", "page"))
        except ValueError:
            refused += 1
    ok(refused == len(roots),
       "and writing the page into ANY of them is refused -- including the main "
       "checkout this worktree shares a repository with", f"{refused}/{len(roots)}")
    import vaultpath
    v = os.path.join(vaultpath.vault_root(), "labelling", "x")
    ok(shotlabel.resolve_out(v) == os.path.abspath(v),
       "CONTROL: the vault is allowed -- a guard that refuses everything protects "
       "nothing, because the tool never runs")


def section_9_drift(tmp):
    print("\n9. the floor is measured at the SAME LAG as the score -- DEFECT 5")
    # THE DEFECT THAT SIX OPCODES FOUND. The floor was measured between ADJACENT idle
    # frames (~1 s apart) while every post-send frame was scored against ONE baseline
    # up to 9 s behind it. A scene that drifts slowly is nearly still between
    # neighbours and far from a fixed baseline, so the difference was charged to the
    # opcode: 0x0016, 0x0032, 0x0034, 0x0036, 0x003D and 0x003F all scored CHANGED at
    # 0.37% against a 0.05% adjacent-pair floor -- and all six reported the SAME
    # bounding box, (824, 491, 1113, ~724), which is the player standing in the middle
    # of the screen breathing.
    world = _world(1)
    frames, t = [], 1.0
    for k in range(12):                       # steady drift, NOTHING else happens
        frames.append((t, _drifted(world, k)))
        t += 1.2
    d = _run_dir(tmp, "r9", frames, T0 + datetime.timedelta(seconds=8.5))
    res = shotlabel.score_run(d)
    row = res["rows"][0]
    ok(row["verdict"] == "QUIET",
       "a scene drifting on its own is QUIET -- no opcode did that",
       f"excess {row['peak']*100:.3f}%  raw {row['raw_peak']*100:.3f}%  "
       f"flag {res['flag_at']*100:.2f}%")
    ok(row["raw_peak"] > res["flag_at"],
       "and the RAW score alone would have cleared the flag, which is the defect",
       f"raw {row['raw_peak']*100:.3f}% > {res['flag_at']*100:.2f}%")
    # The adjacent-pair floor, REPRODUCED: it is small because neighbours barely move.
    shots = shotlabel.hold_shots(d)
    adj = [shotlabel.diff_score(shots[i - 1][0], shots[i][0])[0] for i in range(1, 6)]
    adj = [v for v in adj if v is not None]
    ok(max(adj) * shotlabel.NOISE_MULT < row["raw_peak"],
       "the adjacent-pair floor is REPRODUCED and cannot see the drift",
       f"adjacent max {max(adj)*100:.3f}%  vs raw peak {row['raw_peak']*100:.3f}%")
    # And the curve must actually rise with the lag, or it is not measuring drift.
    pairs, _n = shotlabel.drift_floor(
        shots, T0 + datetime.timedelta(seconds=8.5))
    lo_lag, hi_lag = 1.2, 6.0
    lo_v = shotlabel.floor_at(pairs, lo_lag, window=0.3)
    hi_v = shotlabel.floor_at(pairs, hi_lag, window=0.3)
    ok(lo_v is not None and hi_v is not None and hi_v > lo_v * 2,
       "the drift curve RISES with the lag -- which is the whole claim",
       f"{lo_v*100:.3f}% at {lo_lag:.1f}s -> {hi_v*100:.3f}% at {hi_lag:.1f}s")
    # CONTROL: a real window on top of the same drift must still be seen, or the fix
    # is just a way of never reporting anything.
    frames2 = []
    t = 1.0
    for k in range(12):
        im = _drifted(world, k)
        frames2.append((t, _with_window(im) if k >= 7 else im))
        t += 1.2
    d2 = _run_dir(tmp, "r9b", frames2, T0 + datetime.timedelta(seconds=8.5))
    row2 = shotlabel.score_run(d2)["rows"][0]
    ok(row2["verdict"] == "CHANGED",
       "CONTROL: a real panel on top of the same drift is still CHANGED",
       f"excess {row2['peak']*100:.3f}%")


def main():
    if _pil() is None:
        LEDGER.skip("every section", "PIL is missing -- the fixture is drawn with it, "
                                     "and drive_client already needs it for --shots")
        return LEDGER.verdict()
    with tempfile.TemporaryDirectory() as tmp:
        section_1_reading(tmp)
        section_2_join_by_clock(tmp)
        section_3_floor(tmp)
        section_4_ambiguous_second(tmp)
        section_5_transient(tmp)
        section_6_refusals(tmp)
        section_7_no_send_is_not_a_result(tmp)
        section_8_provenance(tmp)
        section_9_drift(tmp)
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
