r"""Run the opcode sweep until it stops making progress, one client at a time.

The sweep dies at the first opcode that asserts the client, and there is one of those
roughly every eighteen (measured: 18 rows for one assert). Clearing 306 opcodes by hand
is seventeen launch/score/replan cycles, which is not hard, only long. This is that loop.

    python toolkit/authsrv/sweeploop.py --rounds 20
    python toolkit/authsrv/sweeploop.py --rounds 1 --dry-run    # print, launch nothing

Each round is exactly what an operator would type, in order:

    smsgsweep.py --plan --resume --seen <observed>      # what is left
    session.py --game-args "--probe smsgsweep --ping-seconds 0.5 --no-enemy" ...
    smsgsweep.py --from-report <that run's report> --record

**Loopback only.** Every launch goes through `session.py`, which goes through
`cage.assert_launch_safe`: an ours-DH client may only be aimed at our own server, and a
stock-DH build is refused outright. This module adds no launch path of its own and must
never grow one -- it shells out precisely so the gate stays in the one place that is
tested (`toolkit/clientpatch/test_cage.py`).

THREE THINGS EVERY ROUND PASSES, and none of them is optional:

  --no-enemy       The default world spawns a hostile that kills the player at t=7.4 and
                   revives at t=17.4, forever. Every sweep reading taken between those is
                   a measurement of a corpse, and `smsgsweep.record` REFUSES such a run.
                   Passing it here rather than leaving it to the operator is the point:
                   a loop that fails this way fails seventeen times in a row.
  --ping-seconds   The client's reply is the only proof its message pump is running, and
                   at ArenaNet's 5.000 s cadence a crash localises to twelve opcodes. At
                   0.5 s it localises to one, which is what makes the loop CONVERGE --
                   an unlocalised crash records nothing and the next round replans it.
  --probe          Without it the client just stands there and the round measures nothing.

WHEN IT STOPS, and why each is a stop rather than a retry:

    plan empty          nothing left. The only good ending.
    planner refused     it exited non-zero, or it wrote no plan. `load_plan()` reads a
                        file out of the vault and cannot tell this round's plan from the
                        last one's, so a refusal used to leave the loop holding a STALE
                        plan and launching a real client against it -- measuring one set
                        of opcodes and recording them as another. See `accept_plan`.
    no new rows twice   the sweep is stuck. Two rounds in a row that record nothing means
                        the crash is not being localised -- raise --ping-seconds or widen
                        the dwell -- and a third round would only burn another client.
    round failed        the harness itself did not reach the map. That is a broken stack,
                        not a sweep result, and looping over it hides the breakage.
    --rounds reached    a ceiling, so an unattended run cannot spin forever.

WHAT IT DOES NOT DO. It does not bisect. A round that ends with two or more suspects
records nothing and prints the `--only` line to run by hand, because choosing which half
to try first is a judgement about what the opcodes are, and the loop has no view of that.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import vaultpath  # noqa: E402
import smsgsweep  # noqa: E402
from codec import Codec  # noqa: E402

TOOLKIT = os.path.dirname(HERE)
SESSION = os.path.join(TOOLKIT, "harness", "session.py")
SWEEP = os.path.join(HERE, "smsgsweep.py")

# Passed to authsrv on EVERY round. See the docstring -- each one is load-bearing and
# leaving any to the operator is how a loop fails identically seventeen times.
GAME_ARGS = "--probe smsgsweep --ping-seconds 0.5 --no-enemy"
PING_SECONDS = 0.5

# `smsgsweep --plan`'s ONE non-zero exit that still leaves a plan behind: "NOTHING TO
# SEND", written and empty. Every other non-zero is a refusal that writes nothing.
PLAN_EMPTY_RC = 1


def decide(planned, recorded, dry_rounds, failed, rounds_left):
    """(go, why) -- whether to run another round. Pure, so it can be tested.

    Kept apart from the subprocess work on purpose: every stop condition here is a
    judgement about when to stop burning clients, and a rule that only runs when a client
    is up is a rule nobody can check.
    """
    if failed:
        return False, ("the harness did not reach the map. That is a broken stack, not a "
                       "sweep result -- looping over it would hide the breakage")
    if not planned:
        return False, "nothing left to plan. The sweep is complete"
    if dry_rounds >= 2:
        return False, (f"two rounds in a row recorded nothing (last: {recorded}). The "
                       f"crash is not being localised -- raise --ping-seconds or widen "
                       f"the dwell, and bisect the suspects by hand with --only")
    if rounds_left <= 0:
        return False, "the round ceiling was reached"
    return True, ""


def accept_plan(rc, moved, err=""):
    """(ok, why) -- whether the plan on disk is THIS round's. Pure, so it can be tested.

    `load_plan()` reads a file out of the vault and answers just as confidently from the
    PREVIOUS round's plan as from this one's. `smsgsweep --plan` exits 2 WITHOUT writing
    one on all three refusals in the tree on 2026-08-13 -- `--set` without `--only`, a
    `check_sets` disagreement, any ValueError out of `plan()` -- so the loop was launching
    a real client against a stale plan and recording what it measured under this round's
    opcodes. That failure is silent from the inside: the plan parses, the client runs, the
    ledger grows. The gate below is written against the CLASS rather than that list, which
    is the point: a refusal added later (an unmigrated ledger under `--resume` was on its
    way when this was written) needs no line here.

    Two signals, because each covers a hole in the other. The exit code alone misses a
    planner that dies after its own checks or a future refusal that forgets to exit 2 --
    "it refused and the file did not move" is the shape of the whole failure, so the file
    is what gets asked. The stamp alone would stop without naming a reason.

    And `rc != 0` is wrong in the other direction: exit 1 is "NOTHING TO SEND", which
    WRITES an empty plan and is the sweep's only good ending. Reporting it here would
    rename completion as breakage; it belongs to `decide`, which stops on an empty plan.
    """
    if rc not in (0, PLAN_EMPTY_RC):
        tail = " ".join((err or "").split())[:300] or "(it printed nothing on stderr)"
        return False, (f"the planner exited {rc} and wrote no plan, so the file in the "
                       f"vault is an earlier round's and a client launched against it "
                       f"would measure opcodes nobody planned this round. Its stderr: "
                       f"{tail}")
    if not moved:
        return False, (f"the planner exited {rc} but the plan file did not move, so "
                       f"whatever `load_plan()` would answer with was written by an "
                       f"earlier round. Nothing launches on a plan this round did not "
                       f"produce")
    return True, ""


def plan_stamp():
    """(mtime_ns, size) of the plan file, or None when there is none.

    The freshness probe, and it is deliberately of the FILE rather than of its contents:
    the question is whether the planner wrote this round, not whether it changed its mind.
    Two rounds are a client launch apart, so no clock granularity here can make two real
    writes look like one.
    """
    try:
        st = os.stat(smsgsweep.plan_path())
    except OSError:
        return None
    return st.st_mtime_ns, st.st_size


def plan_round(seen, limit, dwell, sweep=None):
    """(plan, why) -- this round's plan, or (None, why to stop) with nothing launched.

    `sweep` names the planner so a test can point the loop at one that refuses; the loop
    itself always uses `SWEEP`.
    """
    before = plan_stamp()
    rc, out, err = run([sys.executable, sweep or SWEEP, "--plan", "--resume",
                        "--seen", seen, "--limit", str(limit), "--dwell", str(dwell)])
    if out.strip():
        print("    " + "\n    ".join(out.strip().splitlines()[:4]), flush=True)
    ok, why = accept_plan(rc, plan_stamp() != before, err)
    if not ok:
        return None, why
    return smsgsweep.load_plan() or {}, ""


def newest_report(before):
    """The harness run directory that appeared during this round, by NAME not by mtime.

    The set difference is the check: exactly one new directory, or we do not know which
    run we just did and scoring the wrong one would write another run's results into the
    ledger under this round's opcodes.
    """
    after = set(glob.glob(os.path.join(vaultpath.vault_path("captures", "harness"), "*")))
    fresh = sorted(after - before)
    if len(fresh) != 1:
        raise RuntimeError(f"expected exactly 1 new harness run directory, saw "
                           f"{len(fresh)}: {[os.path.basename(f) for f in fresh]}")
    report = os.path.join(fresh[0], "report.json")
    if not os.path.isfile(report):
        raise RuntimeError(f"{fresh[0]} has no report.json -- the run did not finish")
    return report


def run(cmd, echo=True):
    """(rc, both streams, stderr alone).

    Kept apart because a refusal's REASON arrives on stderr and the loop has to name it:
    a stop that says only "exit 2" sends the operator back to the planner to find out
    what it already said.
    """
    if echo:
        print("    $ " + " ".join(os.path.basename(c) if c.endswith(".py") else c
                                  for c in cmd[1:]), flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or ""), (p.stderr or "")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=10, help="ceiling on client launches")
    ap.add_argument("--limit", type=int, default=80,
                    help="opcodes planned per round. A round ends at the first assert, "
                         "so a large limit costs nothing but a longer hold")
    ap.add_argument("--dwell", type=float, default=0.8,
                    help="seconds between sends. ABOVE --ping-seconds means every opcode "
                         "gets its own proof of life and a crash names one opcode")
    ap.add_argument("--hold", type=float, default=0.0,
                    help="seconds to hold the session; 0 computes it from the plan")
    ap.add_argument("--seen", default=None,
                    help="observed-opcode file; defaults to the vault's")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan and print, launch nothing")
    a = ap.parse_args()

    if a.dwell <= PING_SECONDS:
        print(f"REFUSING: --dwell {a.dwell} is not above the {PING_SECONDS}s heartbeat, "
              f"so a crash cannot be pinned to one opcode and every round that crashes "
              f"would record nothing. The loop would spin.", file=sys.stderr)
        return 2

    seen = a.seen or os.path.join(vaultpath.vault_path("probes"), smsgsweep.SEEN_NAME)
    if not os.path.isfile(seen):
        print(f"REFUSING: no observed-opcode file at {seen}. Build it with "
              f"`smsgsweep.py --write-seen` -- without it the sweep would replan the "
              f"155 opcodes ArenaNet has already shown us.", file=sys.stderr)
        return 2

    codec = Codec()
    dry_rounds, done_before = 0, len(smsgsweep.load_ledger())
    stop_rc = 0
    for i in range(1, a.rounds + 1):
        print(f"\n=== round {i}/{a.rounds} " + "=" * 46, flush=True)
        plan, why = plan_round(seen, a.limit, a.dwell)
        if plan is None:
            # Before the launch, deliberately: this is the one stop whose whole point is
            # that the client must not go up. Non-zero out of an unattended run, because a
            # round that planned nothing did not do what it was asked.
            print(f"  STOP: {why}", flush=True)
            stop_rc = 2
            break
        planned = plan.get("rows") or []
        go, why = decide(planned, 0, dry_rounds, False, a.rounds - i + 1)
        if not go:
            print(f"  STOP: {why}", flush=True)
            break
        if a.dry_run:
            print(f"  --dry-run: would launch a client for {len(planned)} opcode(s)",
                  flush=True)
            break

        hold = a.hold or (plan["settle"] + plan["control"]
                          + a.dwell * len(planned) + 20.0)
        before = set(glob.glob(os.path.join(
            vaultpath.vault_path("captures", "harness"), "*")))
        rc, out, _ = run([sys.executable, SESSION, "--game-args", GAME_ARGS,
                          "--keep-open", "--hold", f"{hold:.0f}"])
        for line in out.splitlines():
            if "Assertion" in line or "RUN VERDICT" in line or "ERROR DIALOG" in line:
                print("    " + line.strip(), flush=True)
        failed = rc != 0 or "RUN VERDICT: PASS" not in out
        try:
            report = newest_report(before)
        except RuntimeError as exc:
            print(f"  STOP: {exc}", flush=True)
            break

        rc, out, _ = run([sys.executable, SWEEP, "--from-report", report, "--record"])
        for line in out.splitlines():
            if any(k in line for k in ("SUSPECT", "REPLIED", "UNDECODABLE", "recorded",
                                       "REFUSING", "NOT QUIET", "stimulated")):
                print("    " + line.strip(), flush=True)
        after = len(smsgsweep.load_ledger())
        gained = after - done_before
        print(f"  ledger: {after} measured (+{gained} this round)", flush=True)
        dry_rounds = dry_rounds + 1 if gained == 0 else 0
        done_before = after
        go, why = decide(planned, gained, dry_rounds, failed, a.rounds - i)
        if not go:
            print(f"  STOP: {why}", flush=True)
            break

    print()
    # The report still prints -- the ledger is what earlier rounds bought -- but a refusal
    # keeps the exit code, so an unattended run cannot end 0 having stopped early.
    return smsgsweep.print_report(smsgsweep.load_ledger(), codec) or stop_rc


if __name__ == "__main__":
    sys.exit(main())
