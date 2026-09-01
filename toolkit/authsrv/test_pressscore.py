"""pressscore.py is the instrument section 36's rule needs -- "measure the
symptom on the wire in their post-fix capture before writing the word
fixed" -- so this file checks the instrument before anyone trusts a number
it prints about a run.

Two halves. The BARE half builds a synthetic capture in memory (a click, a
press, the world ticks, and the wire's own attack_started) and drives the
scorer through it: the last-input classifier, the leg model's arithmetic,
and the three bounds on the click latch forked at the press -- the constant
holds the swing to click + 3.0 s, the leg bound opens it on the first tick
after the leg ends, and "the press ends the leg" opens it while the modelled
body is still walking (the bad arm the scorer must flag). The VAULT half
re-runs the section 36 headline on the three 2026-09-01 captures and
requires the replay control to close on each -- the positive control that
the transcribed rules are the rules that ran -- and is a declared skip on a
machine without them.

Floor: the bare half, measured. The vault checks are extra when present.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402
import vaultpath  # noqa: E402
import pressscore  # noqa: E402

# FLOOR 14: the bare synthetic half, from the green run of 2026-09-01 that
# created the file (20 with the vault: the vault half adds 3 x 2 checks when
# the three captures are present and declares a skip otherwise -- exercised
# both ways that day, RURIK_VAULT pointed at an empty directory for the bare
# one).
LEDGER = checks.Ledger("press scorer", floor=14)
check = LEDGER.ok


def _c2s(t, i, opcode, name, values):
    return (t, i, "c2s", {"opcode": opcode, "name": name, "values": values,
                          "kind": "decoded", "t": t})


def synthetic(click_t, click_dest, press_t, wire_started_t, t_end=5.0):
    """One click, one press on agent 10, ticks every 50 ms, and the wire's
    attack_started where the capture under test would have put it. Ends at
    5.0 s so a swing opened at click + 3.0 s has no second beat (interval
    1.75 s) before the tape runs out -- one wire start, one replayed start."""
    evs = []
    i = 0
    t = 0.0
    while t <= t_end:
        evs.append((round(t, 3), i, "tick", None))
        i += 1
        t += 0.05
    evs.append(_c2s(click_t, i, 62, "MOVE_TO_COORD",
                    [32768, list(click_dest), 0]))
    evs.append(_c2s(press_t, i + 1, 38, "ATTACK", [32769, 10, 0]))
    evs.append((wire_started_t, i + 2, "wire_started",
                "attack_started: player swings at 10"))
    evs.sort(key=lambda e: (e[0], e[1]))
    return evs


def section_bare():
    print("\n1. the synthetic capture: one click, one press, the bounds forked")
    spawns = {1: (0.0, 0.0), 10: (100.0, 0.0)}
    quiet = []
    say = quiet.append
    # a 86.4 u click at t=1.0 is a 0.3 s leg; the press lands at 1.5, after
    # the leg ended; under the 3.0 s constant the wire's swing came at 4.0.
    flags = {"SWING_HOLDS_WALK_GATE": False}      # a section 34/35 capture
    evs = synthetic(1.0, (86.4, 0.0), 1.5, 4.0)
    r = pressscore.score(flags, evs, spawns, say=say, verbose=True)
    check(r["mode"] == "window",
          "a capture whose flags carry SWING_HOLDS_WALK_GATE and no "
          "CLICK_LATCH_LEG_ETA is scored under the 3.0 s constant it ran",
          f"mode={r['mode']}")
    check(r["CLICK"] == (1, 1) and r["presses"] == 1,
          "the press's last movement input is the CLICK, and the wire's "
          "swing at +2.5 s counts as answered within the 3.0 s window",
          f"CLICK={r['CLICK']}")
    row = r["rows"][0]
    check(abs(row["leg_u"] - 86.4) < 1e-6 and abs(row["eta"] - 0.3) < 1e-9
          and row["fl"] is False,
          "the leg model: 86.4 u at 288 u/s is 0.3 s, and at the press "
          "(0.5 s after the click) the leg has ARRIVED",
          f"leg_u={row['leg_u']:.1f} eta={row['eta']:.3f} fl={row['fl']}")
    c = r["control"]
    check(c[0] == 1 and c[1] == 1 and c[2] == 1,
          "REPLAY CONTROL closes: the transcribed rules put the swing where "
          "the wire has it (click + 3.0 s under the constant)",
          f"control={c}")
    cf = row["cf"]
    check(cf["P0"] is not None and abs(cf["P0"] - 4.0) < 0.06,
          "P0 (the constant) opens the swing at click + 3.0 s -- the "
          "operator's bug: 2.5 s on a parked body",
          f"P0 opens at {cf['P0']}")
    check(cf["P1"] is not None and abs(cf["P1"] - 1.5) < 0.06,
          "P1 (the leg bound) opens on the first tick after the press, the "
          "leg having ended at 1.3 s",
          f"P1 opens at {cf['P1']}")
    check(row["cf_fl"]["P1"] is False and row["cf_fl"]["P0"] is False,
          "and neither opened while the modelled leg was walking",
          f"bad P0={row['cf_fl']['P0']} P1={row['cf_fl']['P1']}")
    s = r["scores"]
    check(s["P0"][0] == 1 and s["P1"][0] == 1 and s["P1"][2] == 0
          and s["P1"][3] == 0,
          "scores both directions: P1 newly answers 0 (the wire answered "
          "it, late) and newly refuses 0",
          f"scores={s['P0']} {s['P1']}")
    check(r["signature"] == 1,
          "the wire signature of a constant bound is counted: one swing "
          "opening 3.00..3.06 s after a click that was the last input",
          f"signature={r['signature']}")

    # the KNOWN-BAD arm: a press 0.5 s into a 1.0 s leg. P2 (the press ends
    # the leg) opens mid-leg and the scorer must say so; P1 waits.
    evs2 = synthetic(1.0, (288.0, 0.0), 1.5, 4.0)
    r2 = pressscore.score(flags, evs2, spawns, say=say, verbose=True)
    row2 = r2["rows"][0]
    check(row2["fl"] is True and abs(row2["eta"] - 1.0) < 1e-9,
          "a 288 u click is a 1.0 s leg and the press at +0.5 s is IN FLIGHT",
          f"eta={row2['eta']:.3f} fl={row2['fl']}")
    check(row2["cf"]["P2"] is not None and row2["cf"]["P2"] < 2.0
          and row2["cf_fl"]["P2"] is True,
          "P2 opens the swing while the modelled body is still walking and "
          "the scorer flags it as the bad arm",
          f"P2 opens at {row2['cf']['P2']} bad={row2['cf_fl']['P2']}")
    check(row2["cf"]["P1"] is not None and abs(row2["cf"]["P1"] - 2.0) < 0.06
          and row2["cf_fl"]["P1"] is False,
          "P1 waits for the leg's end (click + 1.0 s) and opens there",
          f"P1 opens at {row2['cf']['P1']}")
    # a section 37 capture is scored under the leg bound by its own flags.
    r3 = pressscore.score({"CLICK_LATCH_LEG_ETA": True}, evs2, spawns,
                          say=say, verbose=True)
    check(r3["mode"] == "leg" and r3["control"][0] == 0,
          "a capture stamped CLICK_LATCH_LEG_ETA=True is replayed under the "
          "leg bound -- and this synthetic wire (a constant-bound swing at "
          "+3.0 s) then FAILS the replay control, which is the tool refusing "
          "to score a capture its rules did not produce",
          f"mode={r3['mode']} control={r3['control']}")
    check(any("CONTROL DOES NOT CLOSE" in line for line in quiet),
          "and it says so in words",
          "banner present")


def section_vault():
    print("\n2. the section 36 headline, reproduced from the vault")
    root = vaultpath.vault_path("captures", "gamesrv")
    missing = [f for _t, f, _h in pressscore.SECTION36
               if not os.path.exists(os.path.join(root, f))]
    if missing:
        LEDGER.skip("section 36 headline",
                    f"captures not in this vault: {missing} "
                    f"({vaultpath.vault_why()})")
        return
    quiet = []
    for tag, fname, exp in pressscore.SECTION36:
        flags, evs, spawns = pressscore.load(os.path.join(root, fname))
        r = pressscore.score(flags, evs, spawns, say=quiet.append)
        got = (r["CLICK"][0], r["CLICK"][1], r["STOP"][0], r["STOP"][1],
               r["WASD"][0], r["WASD"][1])
        check(got == exp,
              f"{tag}: the section 36 headline reproduces "
              "(CLICK/STOP/WASD answered/n)",
              f"got {got} expected {exp}")
        c = r["control"]
        check(c[0] == c[1] == c[2] and c[3] == c[4],
              f"{tag}: the replay control closes -- every attack_started "
              "and attack_stopped on the wire has a replayed twin within "
              "0.12 s, so the transcribed rules are the rules that ran",
              f"control={c}")


def main():
    section_bare()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
