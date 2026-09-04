#!/usr/bin/env python3
"""Does PRESS ENDS THE WALK's 0x002C harm the DRAWN body? The tape answers.

    python studies/movecode/review/pressharm.py            # the 08:46 specimen
    python studies/movecode/review/pressharm.py <gamesrv-capture.jsonl>

WHY THIS EXISTS AND WHY IT IS NOT repincheck.py. `repincheck.py` scores the
AGTRACK RE-PIN, whose payload is the client's OWN last accepted report -- so its
harm is `RUN_SPEED * age` and its two decoded gates (report age, distance
between the last two accepted reports) ARE the harm predictors. A sweep with
that rule incidentally lights up PRESS ENDS THE WALK: on `authsrv-20260903T-
084616-c1` five of its 0x002Cs carry a last accepted report 5.6-13.5 s stale
with the previous two reports 12.7 u apart -- which, for the re-pin, would be a
body that had MOVED, the warp `AgMsg.cpp` 584 makes possible.

BUT PRESS ENDS THE WALK DOES NOT SEND THE REPORT. Its payload is
`_click_leg_start`'s MODEL of where the body is now (the click leg lerped to the
press, else the report, else the placement), and the sender calls
`_forget_client_position` in the same breath -- it drops the stale report rather
than sending it. So `age` and `prev_d` describe a report the pin never touches;
they measure the wrong quantity for this arm, exactly as they would if you
scored a RESYNC by a click's licensing rule.

THE QUANTITY THAT MATTERS is `|pin - the DRAWN body|`, because a 0x002C
SetPositions the async (rendered) twin too. The wire cannot see the drawn body,
so this joins the gamesrv capture to its `agenttap` partner -- the async copy
read live out of the client through its own `position_at` accessor (clamp and
all, via `w0score.live`) -- and prints, per press pin, how far the rendered body
had to jump. A body that was really parked there jumps 0 u; a yank shows as a
large residual, and its sign (is the next drawn sample AHEAD of or BEHIND the
pin) says forward-nudge vs backward-warp.

This is a one-specimen instrument: the 08:46 session is the only capture in the
corpus that has both PRESS ENDS THE WALK 0x002Cs AND an agenttap tape spanning
them (the two senders shipped after the last movetap/agenttap campaign; 1z-aa).
It refuses rather than flatters when no tape partner is found -- zero exposure is
not a pass.

Read-only over JSONLs already on disk; stdlib only; the vault is found through
vaultpath.
"""
import argparse
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "clientscan"))

# The one capture in the corpus with both press pins and a tape over them.
SPECIMEN = "authsrv-20260903T084616-c1.jsonl"
# R_MATCH, the client's own "close enough" reprieve radius (agtrack_mirror.py:51,
# f32 @0x00946560): a correction under this is one the client itself forgives.
R_MATCH = 100.0


def newest_with_press():
    """Newest gamesrv capture that actually sent a PRESS ENDS THE WALK 0x002C."""
    import vaultpath
    hits = sorted(glob.glob(os.path.join(
        vaultpath.vault_path("captures", "gamesrv"), "authsrv-*-c1.jsonl")))
    for p in reversed(hits):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if "PRESS ENDS THE WALK" in line and '"sent"' in line:
                    return p
    raise SystemExit("no PRESS ENDS THE WALK 0x002C anywhere in the corpus")


def decode_point(plain):
    """(x, y) from a 0x002C payload's hex: u16 opcode, u32 agent, f32 x, f32 y."""
    try:
        b = bytes.fromhex(plain)
    except (ValueError, TypeError):
        return None
    if len(b) < 14:
        return None
    return struct.unpack_from("<ff", b, 6)


def find_tap(cap_path, rows):
    """The agenttap tape whose t0 falls inside this capture's wall span.

    agenttap writes to vault/research/animref/agenttap-<stamp>.jsonl and stamps
    its head with `t0` (wall_unix); the harness launches it just after the
    gamesrv listener, so its t0 sits a few seconds into the capture."""
    import vaultpath
    w0 = rows[0]["wall_unix"]
    w1 = rows[-1]["wall_unix"]
    best = None
    for p in sorted(glob.glob(os.path.join(
            vaultpath.vault_path("research", "animref"), "agenttap-*.jsonl"))):
        try:
            with open(p, encoding="utf-8") as fh:
                head = json.loads(fh.readline())
        except (OSError, ValueError):
            continue
        t0 = head.get("t0")
        if t0 is not None and w0 <= t0 <= w1:
            best = (p, head)
    return best


def load_tap(path):
    from w0score import load
    return load(path)


def player_body(sample):
    """The DRAWN (async, world-1) copy of the player, live through the client's
    own position_at accessor -- agent id 1, as our server numbers it."""
    from w0score import live
    a = (sample.get("agents") or {}).get("1") or {}
    ay = a.get("async")
    if not ay or "x" not in ay:
        return None
    return live(ay, sample.get("clock1"))


def hyp(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def check(cap_path, verbose=True):
    rows = [json.loads(l) for l in open(cap_path, encoding="utf-8") if l.strip()]
    pins = [r for r in rows if r.get("kind") == "sent" and r.get("opcode") == 0x2C
            and "PRESS ENDS THE WALK" in str(r.get("label", ""))]
    if verbose:
        print("capture  %s  --  %d PRESS ENDS THE WALK 0x002C"
              % (os.path.basename(cap_path), len(pins)))
    if not pins:
        if verbose:
            print("  no press pins in this capture -- nothing to score\n")
        return 0, 0, 0

    tap = find_tap(cap_path, rows)
    if tap is None:
        if verbose:
            print("  NO agenttap tape spans this capture: the drawn body cannot "
                  "be read, so the harm is UNMEASURED here -- not zero.\n")
        # Exposure, not a pass: report the pins we could not score.
        return len(pins), 0, 0
    tap_path, head = tap
    _h, samples = load_tap(tap_path)
    if verbose:
        print("tape     %s  (t0 = capture wall + %.3f s, %d samples)"
              % (os.path.basename(tap_path), head["t0"] - rows[0]["wall_unix"],
                 len(samples)))
        print("\n%-8s %11s %8s %8s  %s"
              % ("t", "pin", "resid", "next", "reading"))

    t0 = rows[0]["t"]
    scored = 0
    worst = 0.0
    for r in pins:
        pin = decode_point(r.get("plain", ""))
        if pin is None:
            continue
        W = r["wall_unix"]
        before = [s for s in samples if head["t0"] + s["t"] <= W]
        after = [s for s in samples if head["t0"] + s["t"] > W]
        body = player_body(before[-1]) if before else None
        nxt = player_body(after[0]) if after else None
        if body is None:
            if verbose:
                print("%-8.3f %11s %8s %8s  no drawn-body sample straddling it"
                      % (r["t"] - t0, "(%.0f,%.0f)" % pin, "--", "--"))
            continue
        resid = hyp(body, pin)
        # Where the drawn body goes NEXT relative to the pin: closer than it was
        # (walking toward/through the pin, a forward nudge) or further (yanked).
        nd = hyp(nxt, pin) if nxt is not None else None
        scored += 1
        worst = max(worst, resid)
        if resid <= 1.0:
            reading = "on the drawn body (0 u)"
        elif nd is not None and nd < resid:
            reading = ("%.1f u, body walking TOWARD it (next %.1f u) -- forward "
                       "nudge, not a yank" % (resid, nd))
        else:
            reading = "%.1f u correction" % resid
        if resid > R_MATCH:
            reading = "** %.1f u OVER R_MATCH -- a visible warp **" % resid
        if verbose:
            print("%-8.3f %11s %8.1f %8s  %s"
                  % (r["t"] - t0, "(%.0f,%.0f)" % pin, resid,
                     "%.1f" % nd if nd is not None else "--", reading))
    if verbose:
        print("\n%d of %d pins scored against the drawn body; worst residual "
              "%.1f u (R_MATCH = %.0f u).\n" % (scored, len(pins), worst, R_MATCH))
    over = 1 if worst > R_MATCH else 0
    return len(pins), scored, over


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", nargs="?", default=None,
                    help="gamesrv capture (default: the 08:46 specimen, else "
                         "the newest capture that sent a press pin)")
    a = ap.parse_args()

    if a.capture:
        path = a.capture
    else:
        import vaultpath
        path = os.path.join(vaultpath.vault_path("captures", "gamesrv"), SPECIMEN)
        if not os.path.exists(path):
            path = newest_with_press()

    pins, scored, over = check(path)
    if over:
        print("A press pin jumped the DRAWN body more than R_MATCH. PRESS ENDS "
              "THE WALK needs a harm bound after all -- see FINDINGS sec.1z-ak.")
        return 1
    if scored == 0:
        print("Nothing measured: no drawn-body tape over the press pins. This is "
              "zero exposure, NOT a clean result.")
        return 1
    print("Every press pin landed on the rendered body within the client's own "
          "R_MATCH reprieve radius: no harm bound is needed (FINDINGS sec.1z-ak).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
