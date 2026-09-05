"""Where can the stationary waiver's KEPT branch actually fire, and what is under it? (PLAN Q15,
MOVECODE-1z-bs)

sec.1z-br closed the keyboard path -- a parked body restarts with the refused pair -- and named
the CLICK path as the one route left, on a count ("124 of 180 stale coincident {0x003D->0x003D}
pairs had a click in flight") that was a classification of the REPORT STREAM.  The guard has its
own notion of a click in flight, and the waiver reads it first:

    stationary():  if not STATIONARY_WAIVER or self.async_dest is not None: return False

`async_dest` is set by on_click (every client 0x003E) and cleared by on_report (every
0x003D/0x0047, accepted or not).  So the waiver is DEAD by construction for as long as a click
is pending, and can be live on a click-driven pair only after the client has spoken again.
Three questions, all answerable from the corpus, all joined on the guard's own state:

  1. In every coincident pair's REAL stale window -- (t_b + REPIN_MAX_REPORT_AGE, the next
     ACCEPTED report), not the pair's own gap -- how many seconds is the waiver actually live?
  2. Did the guard ever WANT a re-pin (due, or blocked with a risk `why`) inside a kept
     window?  `agtrack_repin` rows are 2 Hz transitions, so the standing state at an instant
     is the last row at or before it (sample-and-hold), and that is what is joined -- never a
     time window (sec.1z-br.5).  Two of the three re-pin call sites fire at report age ~0, so
     only the sampled tick can ever be waiver-load-bearing, and its transition log is a
     complete record of that sampler: the scan enumerates the sampled instants, it does not
     sample them.
  3. What does the body do AFTER a coincident kept pair -- the displacement to the next
     accepted report, sec.1z-bq.2's arithmetic on the founding specimen -- split by the pair's
     ORDERING and by whether the waiver was live for the whole window?

The third question found what the click framing hid.  The two kept orderings are opposites:
where the newest report is a STOP the next report finds the body at the same point every time;
where the newest is a WALK-START the body is walking on in one window of six, at the
client's own movement speeds.  That is 1z-bn's argument applied to the newer member alone, and
it is what the NEWEST-IS-A-STOP clause (agtrack_guard.WAIVER_NEWEST_MUST_BE_STOP) ships.

THE TWO KNOBS, stated because three lanes of one fan-out produced three "different" counts
from one population by varying them: this file scores CLOSED windows only (a next accepted
report exists; an open-ended last pair has no aftermath to measure) and reads WALL_UNIX rows
only (captures whose rows carry only `t` predate the guard's telemetry: they hold zero
agtrack_repin rows and zero fires, and admitting them via `t` adds ~40 refused and ~15 kept
windows and the corpus's two >500 u kept-branch cases).  A displacement here is the chord to
the next REPORT -- an upper bound on where the body was at any decision instant inside the
window, not a `w0score` live-column reading.

Read-only.  Stdlib only.  Whole corpus.  --list prints the kept windows carrying a want;
--movers prints the double-walk-start specimens the keyboard produced.
"""
import argparse
import bisect
import collections
import glob
import json
import math
import os
import sys

# Resolve the tree from THIS FILE, never from a hardcoded absolute path: a git worktree
# has its own copy of toolkit/, and a hardcoded "C:/gd/Rurik" would silently read main's
# while the shell sits in the worktree -- the stale-tree trap CLAUDE.md opens with.
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for sub in (("studies", "movecode", "review"), ("toolkit",),
            ("toolkit", "mapdata"), ("toolkit", "authsrv")):
    sys.path.insert(0, os.path.join(ROOT, *sub))
import agtrack_guard as ag      # noqa: E402
import agtrack_mirror as am     # noqa: E402

GATE, ZERO = ag.REPIN_MAX_REPORT_AGE, am.ZERO_DIST_SQ
RISK = ("arrival-risk", "budget-red", "gate1-red", "gate2-offmesh")
REFUSED = "0x0047->0x003D"
OP_CLICK, OP_HEADING = 0x3E, 0x3D
MT_JOIN_S = 0.002      # a report row and its decoded 0x003D row are separate time.time() calls
# The client's movement families, measured on the corpus (RUN-1zBO/1zBP legs; d2 lane of the
# 1z-bs fan-out): forward, backward, sideways.  A displacement whose implied speed sits within
# a few percent of one of these is a walking leg, not noise -- the positive control.
FAMILIES_U_PER_S = (284.96, 187.89, 215.0)


def load(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else float("nan")


def fmt(xs, qs=(.5, .9)):
    return " / ".join("%.1f" % pct(xs, q) for q in qs) + " / %.1f" % (max(xs) if xs else float("nan"))


def nearest(times, vals, t):
    """The decoded 0x003D nearest to t within MT_JOIN_S, or None."""
    i = bisect.bisect_left(times, t)
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(times) and abs(times[j] - t) <= MT_JOIN_S:
            if best is None or abs(times[j] - t) < abs(times[best] - t):
                best = j
    return None if best is None else vals[best]


def scan(caps):
    over = collections.Counter()
    trans = collections.Counter()
    wants, fires, windows = [], [], []
    for c in caps:
        try:
            R = load(c)
        except Exception:
            continue
        name = os.path.basename(c)
        flags = next((r for r in R if r.get("kind") == "flags"), {})
        ev = []                    # (t, order, kind, data)
        ht, hv = [], []            # decoded 0x003D rows: times, (heading, movementType)
        for r in R:
            t, k = r.get("wall_unix"), r.get("kind")
            if t is None:
                continue
            if k == "position_report" and r.get("reported"):
                ev.append((t, 1, "report", (r.get("source"), tuple(r["reported"][:2]), bool(r.get("accepted")))))
            elif k == "decoded":
                v = r.get("values") or []
                if r.get("opcode") == OP_CLICK and len(v) >= 2 and isinstance(v[1], list):
                    ev.append((t, 0, "click", tuple(v[1][:2])))
                elif r.get("opcode") == OP_HEADING and len(v) >= 5:
                    ht.append(t)
                    hv.append((tuple(v[3]) if isinstance(v[3], list) else None, v[4]))
            elif k == "kbd_leg":
                ev.append((t, 0, "kbd", r.get("act")))
            elif k == "agtrack_repin":
                ev.append((t, 2, "repin", (r.get("code"), r.get("why"), r.get("blocked_by"))))
            elif k == "agtrack_repin_fire":
                ev.append((t, 3, "fire", r.get("why")))
        if not ev:
            continue
        ev.sort(key=lambda e: (e[0], e[1]))
        order = sorted(range(len(ht)), key=lambda i: ht[i])
        ht, hv = [ht[i] for i in order], [hv[i] for i in order]
        has = {k: any(e[2] == k for e in ev) for k in ("click", "kbd", "repin", "fire")}
        over["captures with movement events"] += 1
        over["  with clicks (0x003E)"] += has["click"]
        over["  with kbd_leg rows (lead armed)"] += has["kbd"]
        over["  with agtrack_repin rows"] += has["repin"]
        over["  with real re-pin fires"] += has["fire"]
        over["  with clicks AND agtrack_repin rows"] += (has["click"] and has["repin"])

        # ---- walk the feed with the guard's own click contract ----
        acc, reps, clicks, kbds, tr = [], [], [], [], []
        click_t, last_kbd = None, None
        for t, _o, kind, d in ev:
            if kind == "click":
                click_t = t
                clicks.append(t)
            elif kind == "report":
                src, pt, ok = d
                reps.append((t, src, pt, ok))
                click_t = None                     # the client spoke: async_dest clears
                if ok:
                    acc.append((t, src, pt))
            elif kind == "kbd":
                last_kbd = (t, d)
                kbds.append((t, d))
            elif kind in ("repin", "fire"):
                pair = d2 = age = None
                if len(acc) >= 2:
                    (ta, sa, pa), (tb, sb, pb) = acc[-2], acc[-1]
                    d2 = (pb[0] - pa[0]) ** 2 + (pb[1] - pa[1]) ** 2
                    age = t - tb
                    pair = "%s->%s" % (sa, sb)
                mover = ("click-pending" if click_t is not None else
                         ("kbd<3s" if last_kbd and t - last_kbd[0] < 3.0 else "neither"))
                row = dict(cap=name, t=t, pair=pair, coinc=(d2 is not None and d2 <= ZERO),
                           stale=(age is not None and age > GATE), age=age, mover=mover,
                           carried=(d2 is not None and d2 <= ZERO and age > GATE))
                if kind == "repin":
                    code, why, bb = d
                    trans[(code, why, bb)] += 1
                    tr.append((t, code, why, bb))
                    if code in ("due", "blocked"):
                        row.update(code=code, why=why, bb=bb)
                        wants.append(row)
                else:
                    row.update(why=d)
                    fires.append(row)

        # ---- every coincident consecutive ACCEPTED pair with a CLOSED real stale window ----
        for i in range(1, len(acc) - 1):
            (ta, sa, pa), (tb, sb, pb), nxt = acc[i - 1], acc[i], acc[i + 1]
            d2 = (pb[0] - pa[0]) ** 2 + (pb[1] - pa[1]) ** 2
            if d2 > ZERO:
                continue
            key = "%s->%s" % (sa, sb)
            w0, w1 = tb + GATE, nxt[0]
            if w1 <= w0:
                continue
            # waiver-live seconds: async_dest None AND nothing refused since b.  A click sets
            # async_dest until the next report of ANY kind; a refused report clears it but
            # blocks with "rejects" until the next accepted report, which ends the window.
            marks = sorted([(tc, "click") for tc in clicks if tb < tc < w1]
                           + [(r_[0], "reject") for r_ in reps if tb < r_[0] < w1 and not r_[3]])
            live, cur, pending, rej = 0.0, w0, False, False
            for tm, what in marks:
                if tm < w0:
                    pending, rej = (what == "click"), (what == "reject") or rej
                    continue
                if not pending and not rej:
                    live += tm - cur
                cur = tm
                if what == "click":
                    pending = True
                else:
                    pending, rej = False, True
            if not pending and not rej:
                live += w1 - cur
            prior = [x for x in tr if x[0] <= w0]
            standing0 = prior[-1] if prior else None
            inside = [x for x in tr if w0 < x[0] < w1]
            want_rows = [x for x in ([standing0] if standing0 else []) + inside
                         if x[1] in ("due", "blocked") and x[2] in RISK]
            ha, hb = nearest(ht, hv, ta), nearest(ht, hv, tb)
            turn = None
            if ha and hb and ha[0] and hb[0]:
                turn = (abs(ha[0][0] - hb[0][0]) > 1e-6 or abs(ha[0][1] - hb[0][1]) > 1e-6)
            any_click = any(tb <= tc < w1 for tc in clicks)
            windows.append(dict(
                cap=name, key=key, ta=ta, tb=tb, gap=tb - ta, w0=w0, w1=w1, span=w1 - w0, live=live,
                live_whole=(not any_click and not any(tb < r_[0] < w1 and not r_[3] for r_ in reps)),
                click_before=any(ta < tc <= tb for tc in clicks),
                click_in=any_click,
                pending_start=any(tb < tc <= w0 for tc in clicks),
                kbd=any(ta - 2.0 <= tk < w1 for tk, _a in kbds),
                disp=math.hypot(nxt[2][0] - pb[0], nxt[2][1] - pb[1]), dt=nxt[0] - tb, nxt_src=nxt[1],
                mt_a=(ha[1] if ha else None), mt_b=(hb[1] if hb else None), turn=turn,
                standing0=standing0, inside=inside, wants=want_rows,
                fires=sum(1 for f in fires if f["cap"] == name and w0 <= f["t"] < w1),
                has_repin_rows=has["repin"], guard_era=has["repin"],
                repin_on=bool(flags.get("AGTRACK_REPIN"))))
    return over, trans, wants, fires, windows


def family_match(disp, dt):
    """The implied speed's distance from the nearest movement family, as a fraction."""
    if dt <= 0 or disp <= 0:
        return None
    v = disp / dt
    return min(abs(v - f) / f for f in FAMILIES_U_PER_S)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="print every kept window carrying a want")
    ap.add_argument("--movers", action="store_true", help="print the kept-branch windows the body walked out of")
    a = ap.parse_args()

    # The vault via vaultpath.require_dir(), which RAISES -- never ROOT/"vault", which in a
    # worktree resolves to nothing, makes this glob return empty, and would have this file
    # confirm its own conclusion from an empty corpus.
    from vaultpath import require_dir
    caps = sorted(glob.glob(os.path.join(require_dir(), "captures", "gamesrv", "*.jsonl")))
    print("scanning %d gamesrv captures with the guard's own click contract ..." % len(caps))
    print("(closed windows only; wall_unix rows only; displacement = chord to the next report)\n")
    over, trans, wants, fires, windows = scan(caps)

    print("=" * 92)
    print("A. OVERVIEW  (gate %.6f s, coincident = d^2 <= %.1f)" % (GATE, ZERO))
    for k, v in over.items():
        print("  %-44s %6d" % (k, v))

    print("\n" + "=" * 92)
    print("B. RE-PIN WANTS (transitions to due/blocked) and FIRES, by the mover at the decision instant")
    print("   click-pending = a 0x003E after the last report: the guard's async_dest is SET and the")
    print("   waiver is refused by its first line whatever the pair says")
    for title, rows in (("wants", wants), ("fires", fires)):
        by = collections.Counter((r["mover"], r["pair"], "coinc" if r["coinc"] else "apart",
                                  "stale" if r["stale"] else "fresh",
                                  "CARRIED" if (title == "fires" and r["carried"]) else "-") for r in rows)
        print("  %s: %d" % (title, len(rows)))
        for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:12]:
            print("     %-72s %5d" % (str(k), v))
    carried = [f for f in fires if f["carried"]]
    print("  fires the waiver CARRIED: %d, on the refused pair: %d, on a kept pair: %d, with a click pending: %d"
          % (len(carried), sum(1 for f in carried if f["pair"] == REFUSED),
             sum(1 for f in carried if f["pair"] != REFUSED), sum(1 for f in carried if f["mover"] == "click-pending")))

    print("\n" + "=" * 92)
    print("C. COINCIDENT PAIRS WITH A REAL STALE WINDOW  (t_b + gate .. next ACCEPTED report)")
    byk = collections.defaultdict(list)
    for w in windows:
        byk[w["key"]].append(w)
    print("   {0x0047->0x0047}: %d  (a dead branch: two stops never coincide in this corpus)" % len(byk.get("0x0047->0x0047", [])))
    for key in sorted(byk, key=lambda k: -len(byk[k])):
        ws = byk[key]
        print("\n  %s  %s  n=%d" % (key, "REFUSED by 1z-bn" if key == REFUSED else "KEPT by 1z-bn", len(ws)))
        print("     window span s  p50/p90/max   %s" % fmt([w["span"] for w in ws]))
        print("     waiver-LIVE s  p50/p90/max   %s   (live for the WHOLE window: %d;  click pending at its start: %d;  a click lands inside: %d)"
              % (fmt([w["live"] for w in ws]), sum(1 for w in ws if w["live_whole"]),
                 sum(1 for w in ws if w["pending_start"]),
                 sum(1 for w in ws if w["click_in"] and not w["pending_start"])))
        print("     in captures with guard rows: %d;  with a re-pin WANT inside (sample-and-hold): %d;  with a FIRE inside: %d"
              % (sum(1 for w in ws if w["has_repin_rows"]), sum(1 for w in ws if w["wants"]), sum(1 for w in ws if w["fires"])))
        if a.list and key != REFUSED:
            for w in [w for w in ws if w["wants"]]:
                print("        %s tb=%.2f span=%.2f live=%.2f standing=%s inside=%s"
                      % (w["cap"][:34], w["tb"], w["span"], w["live"],
                         None if not w["standing0"] else (round(w["standing0"][0] - w["tb"], 2),) + tuple(w["standing0"][1:]),
                         [(round(x[0] - w["tb"], 2),) + tuple(x[1:]) for x in w["inside"]][:4]))

    print("\n" + "=" * 92)
    print("D. THE KEPT BRANCH BY ORDERING -- what the body does after the pair, WAIVER-LIVE windows only")
    print("   (no click and no refused report anywhere in the window, so the waiver could have fired throughout)")
    print("   %-16s %-9s %5s %7s   %-24s %6s %6s   %s" % ("ordering", "era", "n", "still", "disp u p50/p90/max", ">100u", ">500u", "walking-speed match (of >100 u)"))
    for key in ("0x003D->0x0047", "0x003D->0x003D"):
        for era in ("guard", "pre", "all"):
            ws = [w for w in byk.get(key, []) if w["live_whole"]
                  and (era == "all" or (w["guard_era"] == (era == "guard")))]
            if not ws:
                continue
            ds = [w["disp"] for w in ws]
            big = [w for w in ws if w["disp"] > 100.0]
            fm = [family_match(w["disp"], w["dt"]) for w in big]
            fm = [f for f in fm if f is not None]
            print("   %-16s %-9s %5d %7d   %-24s %6d %6d   %s"
                  % (key, era, len(ws), sum(1 for d in ds if d <= 1.0), fmt(ds, (.5, .9)),
                     len(big), sum(1 for d in ds if d > 500.0),
                     ("%d of %d within 5%%" % (sum(1 for f in fm if f <= 0.05), len(fm))) if fm else "-"))
    print("\n   click-pending kept windows (the waiver dead by construction), for contrast:")
    for key in ("0x003D->0x0047", "0x003D->0x003D"):
        ws = [w for w in byk.get(key, []) if not w["live_whole"]]
        if ws:
            ds = [w["disp"] for w in ws]
            print("   %-16s %-9s %5d %7d   %-24s %6d %6d" % (key, "pending", len(ws), sum(1 for d in ds if d <= 1.0),
                                                            fmt(ds, (.5, .9)), sum(1 for d in ds if d > 100), sum(1 for d in ds if d > 500)))

    print("\n" + "=" * 92)
    print("E. THE DOUBLE WALK-START -- {0x003D->0x003D} waiver-live windows by the pair's own gap and")
    print("   movementType transition (decoded 0x003D nearest each report within %.0f ms)" % (MT_JOIN_S * 1000))
    kb = [w for w in byk.get("0x003D->0x003D", []) if w["live_whole"]]
    print("   %-10s %5s %6s %8s   %s" % ("gap s", "n", "still", ">100 u", "mt a->b of the >100 u ones"))
    buckets = (("<0.05", 0, 0.05), ("0.05-0.2", 0.05, 0.2), ("0.2-1", 0.2, 1.0), ("1-2", 1.0, 2.0), (">2", 2.0, 1e9))
    for label, lo, hi in buckets:
        v = [w for w in kb if lo <= w["gap"] < hi]
        big = [w for w in v if w["disp"] > 100.0]
        mts = collections.Counter("%s->%s" % (w["mt_a"], w["mt_b"]) for w in big)
        print("   %-10s %5d %6d %8d   %s" % (label, len(v), sum(1 for w in v if w["disp"] <= 1.0), len(big),
                                              ", ".join("%s x%d" % kv for kv in mts.most_common(6)) or "-"))
    if a.movers:
        print("\n   the windows the body walked out of (>100 u to the next report), largest first:")
        for w in sorted([w for w in kb if w["disp"] > 100.0], key=lambda w: -w["disp"]):
            fmv = family_match(w["disp"], w["dt"])
            print("     %-34s tb=%.2f gap=%.3f mt %s->%s turn=%s next=%s disp=%.1f dt=%.2f v=%.0f u/s (%s) lead=%s guard=%s"
                  % (w["cap"][:34], w["tb"], w["gap"], w["mt_a"], w["mt_b"], w["turn"], w["nxt_src"], w["disp"], w["dt"],
                     w["disp"] / w["dt"], "family %.1f%%" % (100 * fmv) if fmv is not None else "-", w["kbd"], w["guard_era"]))

    print("\n" + "=" * 92)
    kept = [w for w in windows if w["key"] != REFUSED]
    stop_live = [w for w in byk.get("0x003D->0x0047", []) if w["live_whole"]]
    walk_live = kb
    print("  kept-pair closed stale windows: %d   waiver-live throughout: %d   with a want inside: %d   with a fire inside: %d"
          % (len(kept), sum(1 for w in kept if w["live_whole"]), sum(1 for w in kept if w["wants"]), sum(1 for w in kept if w["fires"])))
    print("  newest = STOP  ({0x003D->0x0047}, live): %d windows, %d still, max %.1f u"
          % (len(stop_live), sum(1 for w in stop_live if w["disp"] <= 1.0), max([w["disp"] for w in stop_live] or [0])))
    print("  newest = WALK  ({0x003D->0x003D}, live): %d windows, %d still, %d over 100 u, %d over 500 u, under the lead: %d"
          % (len(walk_live), sum(1 for w in walk_live if w["disp"] <= 1.0), sum(1 for w in walk_live if w["disp"] > 100),
             sum(1 for w in walk_live if w["disp"] > 500), sum(1 for w in walk_live if w["kbd"] and w["disp"] > 100)))
    print()
    print("  THE CLICK PATH: while a click is pending the waiver is refused by its own first line, so a")
    print("  click-pending window is waiver-dead by construction, and that is where the click path's big")
    print("  displacements sit.  THE KEPT BRANCH SPLITS BY ORDERING, not by mover: a pair whose newest")
    print("  report is a STOP is followed by a still body; a pair whose newest is a WALK-START is followed")
    print("  by a walking one often enough to be the 1z-bl defect's shape.  No kept window has ever met a")
    print("  re-pin want -- the branch is unexposed, not absent -- and the newest-is-a-stop clause (1z-bs)")
    print("  refuses the half that walks.  The waiver's surviving branch is {walk-start -> stop} alone.")


if __name__ == "__main__":
    main()
