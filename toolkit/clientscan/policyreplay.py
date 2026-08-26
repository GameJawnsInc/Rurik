"""Replay a gamesrv log's click channel through a candidate server policy.

RETHINK instrument #3 (studies/movement/RETHINK.md sec.4). The one
fix-refutation of 2026-08-26 that cost zero owner minutes was an offline
counterfactual: the sec.0.16 literal candidate hold was replayed against the
113824 log's own event stream and only 2 of 24 real click answers survived
it -- refuted BEFORE it shipped (REALFIX sec.0.17), where every previous
candidate had to die in a live run. That replay was a scratchpad one-off
(skeptic_sim.py). This module is it, promoted: any gamesrv jsonl, any
registered policy, the same engine.

WHAT IS REPLAYED AND WHAT IS EXOGENOUS. The engine replays the click
channel's REPORT-DRIVEN policy surface: the rate floor, the hold machinery
(pending, newest-wins, expiry), the flush (pre-batch ordering, quiet-tick
polls at the recv loop's own 1.0 s timeout), the 0x003D eager void, and the
shared grant clock (zero-lead fires advance it exogenously). Rule 1
(locally-moving) is EXOGENOUS: the keyboard latch's state rides key
transitions the log does not carry, so the REAL row's own reason decides it
-- the replay never re-litigates rule 1, it re-litigates everything after
it. The sec.0.17 leg bound is modelled (chained-dest, 288 u/s straight
line); that is an APPROXIMATION of the world tick's integrator and the
fidelity gate is its referee.

THE FIDELITY GATE, before any counterfactual is quotable: replaying the
policy a log actually shipped under must reproduce that log's own recorded
fires 1:1 (and its pending-expiries in count). A replay that cannot
reproduce reality has no standing to predict an alternative -- grantsim's
own C3 anti-paraphrase discipline, applied here as a hard gate. The same
discipline demands the gate CAN fail: test_policyreplay.py perturbs the
rate floor and requires the gate to go red.

NEVER A RANKING. Output is survive/suppress/new counts with per-click
fates. "Suppresses more" is not "better" without the retail-contract
cross-check (livewire.py's corpus); grantsim's C5 lesson, kept.

Usage:
    python toolkit/clientscan/policyreplay.py --log vault/captures/gamesrv/authsrv-20260826T113824-c1.jsonl --policy sec015
    python toolkit/clientscan/policyreplay.py --list
"""

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

# The click channel's constants, imported from the policy's own module so a
# shipped change moves the replay with it (the grantsim precedent: run THIS
# decision, not a paraphrase that agrees by construction). authsrv's import
# is heavy but proven -- grantsim has imported it since C3.
import authsrv                                                 # noqa: E402

GRANT_MIN = authsrv.GRANT_MIN_INTERVAL
MAX_AGE = authsrv.GRANT_PENDING_MAX_AGE
# The recv loop's socket timeout -- the quiet-tick cadence the flush rides.
# A literal at the recv site (authsrv sock timeout, sec.0.13's REV-2 move);
# the real-log fidelity checks are the guard on this staying true.
QUIET_TICK = 1.0
RUN_SPEED = 288.0


def load_log(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip():
                r = json.loads(line)
                r["_line"] = i + 1
                rows.append(r)
    return rows


def build_streams(rows):
    """The four event streams + the log's own recorded outcomes."""
    gv = [r for r in rows if r.get("kind") == "grant_verdict"]
    dec = [r for r in rows if r.get("kind") == "decoded"]
    cv_lines = sorted(r["_line"] for r in rows
                      if r.get("kind") == "click_verdict")
    clicks = [r for r in dec if r.get("opcode") == 62]
    imm = [r for r in gv if r.get("deferred") is False
           and r.get("arm") in ("click-d1", "click")]
    # pair each decoded click with its immediate-site verdict row, in order,
    # and mark whether the GEOMETRY branch ran for it (a click_verdict row
    # between the decoded click and its grant row). This matters because the
    # geometry branch executes `state["dest"] = None` BEFORE falling through
    # (authsrv :15853) -- so the sec.0.17 leg bound reads a cleared dest on
    # every geometry-flagged click and cannot engage. A fact this tool's own
    # fidelity gate DISCOVERED (the P-17 log: 126 of 179 paired clicks
    # geometry-flagged -- 87/87 in the first 496s the owner's cells cover --
    # 64 fires, zero answer-outstanding rows: irreproducible until the
    # clear was modelled); recorded in REALFIX sec.0.19.
    pairs, j = [], 0
    for c in clicks:
        while j < len(imm) and imm[j]["_line"] < c["_line"]:
            j += 1
        if j < len(imm):
            geo = any(c["_line"] < ln < imm[j]["_line"] for ln in cv_lines)
            pairs.append((c, imm[j], geo))
            j += 1
    reports = [r for r in rows if r.get("kind") == "position_report"
               and r.get("accepted")]
    zl = [r for r in gv if r.get("arm") == "zero-lead" and r.get("fired")]
    real_fired = ([r for r in imm if r.get("fired")]
                  + [r for r in gv if r.get("deferred") and r.get("fired")])
    real_expired = [r for r in gv if r.get("reason") == "pending-expired"]
    return {"pairs": pairs, "reports": reports, "zl_fires": zl,
            "real_fired": real_fired, "real_expired": real_expired}


# ---------------------------------------------------------------- policies
# A policy is PURE decision logic over the engine's state dict:
#   on_click(st, t)          -> "fire" | "hold"     (rule 1 already handled)
#   flush_ok(st, t, pending) -> True to let the held item fire now
# st carries: pos_seen, answered, grant_at, leg_until (the sec.0.17
# chained-dest model's arrival time for the last click fire).

def _since(st, t):
    return None if st["grant_at"] is None else t - st["grant_at"]


def _outstanding(st):
    return st["answered"] > st["pos_seen"]


class PolicySec015:
    """sec.0.15's shipped shape: rate floor at the immediate site, the bare
    outstanding hold at the FLUSH only (the 113824-era policy)."""
    name = "sec015"

    def on_click(self, st, t):
        s = _since(st, t)
        if s is not None and s < GRANT_MIN:
            return "hold"
        return "fire"

    def flush_ok(self, st, t, pending):
        if _outstanding(st):
            return False
        s = _since(st, t)
        return s is None or s >= GRANT_MIN


class PolicySec017(PolicySec015):
    """sec.0.17's shipped shape: sec015 plus the LEG-BOUNDED outstanding
    hold at the immediate site (hold only while the modelled click leg is
    still in flight)."""
    name = "sec017"

    def on_click(self, st, t):
        s = _since(st, t)
        if s is not None and s < GRANT_MIN:
            return "hold"
        if _outstanding(st) and t < st["leg_until"]:
            return "hold"
        return "fire"


class PolicyBareHold(PolicySec015):
    """The REFUTED sec.0.16 literal candidate (the flush's bare predicate
    copied to the immediate site) -- kept as the registry's negative
    control: replaying it against 113824 must suppress 22 of 24."""
    name = "bare-hold"

    def on_click(self, st, t):
        s = _since(st, t)
        if s is not None and s < GRANT_MIN:
            return "hold"
        if _outstanding(st):
            return "hold"
        return "fire"


POLICIES = {p.name: p for p in (PolicySec015(), PolicySec017(),
                                PolicyBareHold())}


# ------------------------------------------------------------------ engine

def replay(streams, policy):
    """Run one policy over the log's event stream. Returns the outcome dict.

    Event order per instant mirrors the recv thread (sec.0.13 REV-2): the
    flush polls BEFORE a batch's own message lands, so a clearing report is
    invisible to that tick's poll -- "void wins", never fire-then-void.
    """
    events = []
    for c, g, geo in streams["pairs"]:
        events.append((c["t"], 2, "click", (c, g, geo)))
    for r in streams["reports"]:
        events.append((r["t"], 1, "report", r))
    for r in streams["zl_fires"]:
        events.append((r["t"], 0, "zl_fire", r))
    events.sort(key=lambda e: (e[0], e[1]))
    polls = set()
    ts = sorted(e[0] for e in events)
    for a, b in zip(ts, ts[1:]):
        t = a + QUIET_TICK
        while t < b:
            polls.add(round(t, 3))
            t += QUIET_TICK
    merged = sorted([(t, -1, "poll", None) for t in polls] + events,
                    key=lambda e: (e[0], e[1]))

    st = {"pos_seen": 0.0, "answered": 0.0, "grant_at": None,
          "leg_until": 0.0, "pending": None, "last_pos": None}
    out = {"fired": [], "fired_late": [], "voided": [], "expired": [],
           "overwritten": [], "cleared_lm": []}

    def leg_arm(t, dest):
        origin = st["last_pos"] if st["last_pos"] is not None else dest
        st["leg_until"] = t + math.hypot(dest[0] - origin[0],
                                         dest[1] - origin[1]) / RUN_SPEED
        st["last_pos"] = dest

    def fire(t, dest, late_from=None):
        st["pending"] = None
        st["grant_at"] = t
        st["answered"] = t
        leg_arm(t, dest)
        if late_from is None:
            out["fired"].append((round(t, 6), dest))
        else:
            out["fired_late"].append((round(late_from, 6), round(t, 6),
                                      dest))

    def flush_poll(t):
        p = st["pending"]
        if p is None:
            return
        if t - p["at"] > MAX_AGE:
            st["pending"] = None
            out["expired"].append((p["at"], round(p["at"] + MAX_AGE, 3),
                                   p["dest"]))
            return
        if policy.flush_ok(st, t, p):
            fire(t, p["dest"], late_from=p["at"])

    for t, _pri, typ, payload in merged:
        if typ == "poll":
            flush_poll(t)
        elif typ == "report":
            flush_poll(t)                       # pre-batch: void wins
            st["pos_seen"] = t
            st["last_pos"] = tuple(payload["reported"])
            if (payload.get("source") == "0x003D"
                    and st["pending"] is not None):
                out["voided"].append((st["pending"]["at"], round(t, 3),
                                      st["pending"]["dest"]))
                st["pending"] = None
        elif typ == "zl_fire":
            flush_poll(t)
            st["grant_at"] = t                  # the shared clock
        elif typ == "click":
            flush_poll(t)                       # pre-batch
            c, g, geo = payload
            dest = tuple(g.get("dest"))
            if geo:
                # the geometry branch cleared state["dest"] before the
                # verdict (authsrv :15853) -- the leg model is gone for
                # this evaluation whatever its ETA said.
                st["leg_until"] = 0.0
            if g.get("reason") == "locally-moving":
                # EXOGENOUS rule 1: the latch's state is the real row's.
                if st["pending"] is not None:
                    out["cleared_lm"].append((st["pending"]["at"],
                                              round(t, 3)))
                st["pending"] = None
                continue
            act = policy.on_click(st, t)
            if act == "fire":
                fire(t, dest)
            else:
                if st["pending"] is not None:
                    out["overwritten"].append((st["pending"]["at"],
                                               round(t, 3),
                                               st["pending"]["dest"]))
                st["pending"] = {"at": t, "dest": dest}
    return out


# ---------------------------------------------------------------- verdicts

def fidelity(streams, out, t_tol=0.05, dest_tol=0.5, exp_tol=1.2):
    """(ok, detail): does the replay reproduce the log's own record?

    Fires must match 1:1 on (t, dest); pending-expiries must match in count
    with each sim expiry within exp_tol of a real one (the sim's synthetic
    quiet ticks approximate the real poll instants). t_tol exists because
    the sim fires at the decoded CLICK's timestamp while the real row is
    stamped ~0.5 ms later inside the handler; 50 ms is an order of
    magnitude under the 0.5 s floor, so it cannot alias two decisions.
    """
    real = [(r["t"], tuple(r["dest"])) for r in streams["real_fired"]]
    sim = ([(t, d) for t, d in out["fired"]]
           + [(t, d) for _h, t, d in out["fired_late"]])
    missing, extra = [], list(sim)
    for rt, rd in real:
        hit = next((s for s in extra
                    if abs(s[0] - rt) <= t_tol
                    and math.hypot(s[1][0] - rd[0], s[1][1] - rd[1])
                    <= dest_tol), None)
        if hit is None:
            missing.append((round(rt, 3), rd))
        else:
            extra.remove(hit)
    real_exp = sorted(r["t"] for r in streams["real_expired"])
    sim_exp = sorted(e for _h, e, _d in out["expired"])
    exp_ok = (len(real_exp) == len(sim_exp)
              and all(abs(a - b) <= exp_tol
                      for a, b in zip(real_exp, sim_exp)))
    ok = not missing and not extra and exp_ok
    return ok, {"missing": missing, "extra": [(round(t, 3), d)
                                              for t, d in extra],
                "real_expired": len(real_exp), "sim_expired": len(sim_exp)}


def counterfactual(streams, out):
    """survive/suppress/new against the log's own fires. Never a ranking."""
    real = [(r["t"], tuple(r["dest"])) for r in streams["real_fired"]]
    sim_all = ([(t, d) for t, d in out["fired"]]
               + [(t, d) for _h, t, d in out["fired_late"]])
    survive, suppressed = [], []
    pool = list(sim_all)
    for rt, rd in real:
        hit = next((s for s in pool
                    if abs(s[0] - rt) <= 0.05
                    and math.hypot(s[1][0] - rd[0], s[1][1] - rd[1])
                    <= 0.5), None)
        if hit is None:
            suppressed.append((round(rt, 3), rd))
        else:
            survive.append((round(rt, 3), rd))
            pool.remove(hit)
    new = [(round(t, 3), d) for t, d in pool]
    return {"survive": survive, "suppressed": suppressed, "new": new}


def _main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", help="a gamesrv jsonl capture")
    ap.add_argument("--policy", help="registered policy name")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list or not (args.log and args.policy):
        print("policies:", ", ".join(sorted(POLICIES)))
        return 0 if args.list else 2
    policy = POLICIES[args.policy]
    streams = build_streams(load_log(args.log))
    out = replay(streams, policy)
    ok, detail = fidelity(streams, out)
    print(f"log: {args.log}")
    print(f"policy: {policy.name}")
    print(f"real fires: {len(streams['real_fired'])}  "
          f"real expiries: {len(streams['real_expired'])}")
    print(f"replay fires: {len(out['fired'])} immediate "
          f"+ {len(out['fired_late'])} late; expiries {len(out['expired'])}; "
          f"voided {len(out['voided'])}; overwritten {len(out['overwritten'])}")
    print(f"FIDELITY vs this log's own record: {'PASS' if ok else 'FAIL'}"
          f" {'' if ok else detail}")
    cf = counterfactual(streams, out)
    print(f"counterfactual: survive {len(cf['survive'])} / "
          f"suppressed {len(cf['suppressed'])} / new {len(cf['new'])}")
    if cf["suppressed"]:
        print("  suppressed:", cf["suppressed"])
    if cf["new"]:
        print("  new:", cf["new"])
    print("(counts, not a ranking -- a policy that suppresses more is not "
          "better without the retail-contract cross-check)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
