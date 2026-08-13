"""Run the SILENT opcodes one per client, screenshotting, so a person can name them.

`smsgsweep` scores an opcode by the client's REPLY, and 239 rows came back SILENT --
which means *no c2s message*, not *nothing happened*. Four of four SILENT opcodes
re-sent with a meaningful payload were opening windows and printing chat. This loop is
the conversion: one opcode, one fresh client, screenshots through the hold, next.

    python toolkit/authsrv/shotloop.py --limit 5          # a pilot
    python toolkit/authsrv/shotloop.py                    # the whole 239
    python toolkit/authsrv/shotloop.py --dry-run          # print, launch nothing

ONE OPCODE PER CLIENT LAUNCH, AND THAT IS THE WHOLE DESIGN. Owner's call, 2026-08-13,
and it costs about 40 s per opcode -- roughly two and a half hours for the set, taken
deliberately rather than batched. Batching breaks the readout in two ways that no
amount of scoring fixes: a window an earlier opcode opened is STILL ON SCREEN when the
next one lands, so it sits inside the next opcode's baseline frame; and an opcode may
only do anything BECAUSE of state a previous one left, which reports a joint effect
under one name. `shotlabel.score_run` refuses a run with more than one send outright,
so this is enforced at the readout and not only here.

**Loopback only.** Every launch goes through `session.py` and therefore through
`cage.assert_launch_safe`: an ours-DH client may only be aimed at our own server, and
a stock-DH build is refused. This module adds no launch path of its own and must never
grow one.

THE THREE ARGUMENTS EVERY RUN PASSES, unchanged from `sweeploop` and for the same
reasons: `--no-enemy` (the default world's hostile kills the player at t=7.4, and
sixteen SILENT readings once meant "silent on a corpse"), `--ping-seconds 0.5`, and
`--probe smsgsweep`. Added here: `--shots`, because a run with no screenshots measures
exactly what the sweep already measured.

THE LEDGER IS NOT TOUCHED. This loop re-sends opcodes that are already MEASURED, to
read a different channel, so it writes its own state file and never calls `--record`.
Folding these into the sweep's ledger would overwrite a wire result with a screen one.

WHAT IT DOES NOT DO. It does not name anything and it does not judge a picture. It
produces runs; `shotlabel.py` builds the page; a person reads it.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import vaultpath   # noqa: E402
import smsgsweep   # noqa: E402
import shotlabel   # noqa: E402

TOOLKIT = os.path.dirname(HERE)
SESSION = os.path.join(TOOLKIT, "harness", "session.py")
SWEEP = os.path.join(HERE, "smsgsweep.py")

GAME_ARGS = "--probe smsgsweep --ping-seconds 0.5 --no-enemy"
SHOTS = 1.0        # seconds between screenshots
HOLD = 22.0        # seconds of hold; the single send lands ~13 s in
STATE = "shotloop-state.json"

# A run that fails is a broken stack, not a result about the opcode. Two in a row is
# the stop: one can be a stale listener or a client that missed the map, and stopping
# at one would end most loops early -- `sweeploop.decide` learned the same lesson.
MAX_CONSECUTIVE_FAILURES = 2


def state_path():
    return os.path.join(vaultpath.vault_path("probes"), STATE)


def load_state():
    p = state_path()
    if not os.path.isfile(p):
        return {"done": {}}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(st):
    p = state_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)


def silent_opcodes():
    """The SILENT rows of the sweep ledger, in catalogue order.

    Read from the LEDGER rather than from a list in a file somebody made once, for the
    reason `smsgsweep --write-seen` rebuilds its observed set from the tapes: a list
    written by hand goes stale the moment the sweep records another row.
    """
    led = smsgsweep.load_ledger()
    return sorted(int(k, 16) for k, v in led.items() if v.get("effect") == "SILENT")


def remaining(st, opcodes):
    done = set(st.get("done", {}))
    return [o for o in opcodes if f"0x{o:04X}" not in done]


def run(cmd, echo=True):
    if echo:
        print("    $ " + " ".join(os.path.basename(c) if c.endswith(".py") else c
                                  for c in cmd[1:]), flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def newest_report(before):
    """The run directory that appeared, by NAME not by mtime -- exactly one, or stop.

    Same check and same reason as `sweeploop.newest_report`: if two appeared we do not
    know which run we just did, and attributing the wrong one files another opcode's
    screenshots under this one.
    """
    after = set(glob.glob(os.path.join(vaultpath.vault_path("captures", "harness"), "*")))
    fresh = sorted(after - before)
    if len(fresh) != 1:
        raise RuntimeError(f"expected exactly 1 new harness run directory, saw "
                           f"{len(fresh)}: {[os.path.basename(f) for f in fresh]}")
    return fresh[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="stop after N opcodes")
    ap.add_argument("--only", default=None,
                    help="comma-separated opcodes instead of the SILENT set")
    ap.add_argument("--shots", type=float, default=SHOTS)
    ap.add_argument("--hold", type=float, default=HOLD)
    ap.add_argument("--redo", action="store_true", help="ignore the state file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.only:
        opcodes = [int(x, 0) for x in a.only.replace(" ", "").split(",") if x]
    else:
        opcodes = silent_opcodes()
        if not opcodes:
            print("no SILENT rows in the ledger -- nothing to name")
            return 2
    st = {"done": {}} if a.redo else load_state()
    todo = opcodes if a.only else remaining(st, opcodes)
    if a.limit:
        todo = todo[:a.limit]

    print(f"{len(opcodes)} SILENT opcode(s); {len(todo)} to run this pass "
          f"(~{len(todo) * 38 / 60.0:.0f} min at ~38 s each)", flush=True)
    if a.dry_run:
        print("  --dry-run: would run " + " ".join(f"0x{o:04X}" for o in todo[:20])
              + (" ..." if len(todo) > 20 else ""))
        return 0

    fails, started = 0, time.time()
    for i, op in enumerate(todo, 1):
        key = f"0x{op:04X}"
        print(f"\n[{i}/{len(todo)}] {key}  "
              f"({(time.time() - started) / 60.0:.0f} min elapsed)", flush=True)
        rc, out = run([sys.executable, SWEEP, "--plan", "--only", key, "--encstring"])
        if rc != 0:
            print(f"  plan refused {key}: " + out.strip().splitlines()[-1][:160])
            st["done"][key] = {"run": None, "note": "plan refused"}
            save_state(st)
            continue
        before = set(glob.glob(os.path.join(
            vaultpath.vault_path("captures", "harness"), "*")))
        rc, out = run([sys.executable, SESSION, "--game-args", GAME_ARGS,
                       "--keep-open", "--shots", f"{a.shots:g}",
                       "--hold", f"{a.hold:.0f}"])
        ok = rc == 0 and "RUN VERDICT: PASS" in out
        for line in out.splitlines():
            if "Assertion" in line or "ERROR DIALOG" in line:
                print("    " + line.strip(), flush=True)
        try:
            rundir = newest_report(before)
        except RuntimeError as exc:
            print(f"  STOP: {exc}", flush=True)
            return 1
        shots = len(glob.glob(os.path.join(rundir, "hold*.png")))
        # THE HARNESS VERDICT IS NOT ENOUGH, and this check is here because its
        # absence cost three runs on 2026-08-13. `session.py` judges "did the client
        # reach the map", which it did -- while the gamesrv sat wedged on a blocked
        # print and the probe sent NOTHING (see session.Stack._pump). The run reported
        # RUN VERDICT: PASS, the capture filled with world ticks, and three opcodes
        # were marked done having never been sent. So the state file records an opcode
        # only when this run's OWN capture holds its send: the same rule `smsgsweep`
        # applies with UNREACHED, which is deliberately not a measurement.
        sends, why = shotlabel.sweep_sends(rundir)
        got = [o for o, _, _ in (sends or [])]
        sent_ok = got == [op]
        if not sent_ok:
            print(f"  NO SEND in the capture ({why or 'saw ' + str([hex(g) for g in got])})"
                  f" -- not recording {key}", flush=True)
        print(f"  {'PASS' if ok and sent_ok else 'FAIL'}  {os.path.basename(rundir)}  "
              f"{shots} shot(s)", flush=True)
        if ok and sent_ok:
            st["done"][key] = {"run": os.path.basename(rundir), "ok": True,
                               "shots": shots}
            save_state(st)
        fails = fails + 1 if not (ok and sent_ok) else 0
        if fails >= MAX_CONSECUTIVE_FAILURES:
            print(f"\nSTOP: {fails} runs in a row did not reach the map. That is a "
                  f"broken stack, not a result about these opcodes.", flush=True)
            return 1

    print(f"\ndone: {len(st['done'])} opcode(s) have a run. Build the page with:\n"
          f"  python toolkit/authsrv/shotlabel.py --scan <date prefix>", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
