"""The SERVER side of a MOVECODE-K1 arm: did the keep-alive actually run?

    python toolkit/clientscan/movehook/keepalivelog.py
    python toolkit/clientscan/movehook/keepalivelog.py --log PATH

WHY THIS IS A FILE AND NOT A LINE IN THE RUNSHEET. It was a `python -c` one-liner,
and the runsheet's other one-liners were bash (`mkdir -p`, `cp a b dir/`) which is not
the shell this project is driven from -- the owner hit `Copy-Item : A positional
parameter cannot be found` on the first arm. A runsheet command that only works in
the author's shell is a runsheet command that does not work. `python …` lines run in
any shell, which is what CLAUDE.md already says, so the fragile parts move here.

WHAT IT ANSWERS, and both are EXPOSURE questions rather than results. RUN-K1.md
pre-registers them because zero exposure is not a null:

  * did the flag FIRE at all? `keepalive_verdict` rows with `fired: true`. None means
    the treatment arm never ran and measures nothing -- and the `reason` census then
    says which gate refused, because each names a different thing to fix.
  * how many grants went out, against run 5's 51 -- the number the whole arc is about.

It also prints the click-refusal census, because FINDINGS §1i.5 found those split
into two unrelated defects (13 staleness, 4 geometry) and the split is worth watching
across arms.

Stdlib only. Read-only: it opens one log and prints.
"""

import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLKIT)

GRANT_OPCODE = 41                      # 0x0029 AGENT_MOVE_TO_POINT
TICK_OPCODE = 30                       # 0x001E WORLD_SIMULATION_TICK


def newest_log():
    """The most recent gamesrv connection log, or None.

    Newest by MTIME and not by name. `sorted(...)[-1]` on a filename is the trap this
    repo has hit three times in three files, and these names are timestamped so it
    would *usually* work -- which is exactly what makes it worth not relying on.
    """
    try:
        import vaultpath
        base = vaultpath.require_dir("captures", "gamesrv", why="the K1 arm readout")
    except Exception:
        base = os.path.join("vault", "captures", "gamesrv")
    hits = glob.glob(os.path.join(base, "authsrv-*-c*.jsonl"))
    return max(hits, key=os.path.getmtime) if hits else None


def rows(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                # A run killed mid-write leaves a torn last line. Dropped, and said
                # out loud below rather than silently -- a partial read reported as
                # a full one is this suite's oldest defect class.
                out.append(None)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=None,
                    help="the gamesrv jsonl to read; default is the newest by mtime")
    a = ap.parse_args(argv)

    path = a.log or newest_log()
    if not path or not os.path.isfile(path):
        print("no gamesrv log found. A run that produced no log is a run that did "
              "not happen -- check that the stack actually started.")
        return 2
    rs = rows(path)
    torn = sum(1 for r in rs if r is None)
    rs = [r for r in rs if r is not None]
    print(f"log: {path}")
    if torn:
        print(f"  !! {torn} unparseable line(s) dropped (a run killed mid-write "
              f"tears the last one)")

    span = None
    ts = [r["t"] for r in rs if isinstance(r.get("t"), (int, float))]
    if len(ts) > 1:
        span = max(ts) - min(ts)
        print(f"  span {span:.1f} s, {len(rs)} row(s)")

    ka = [r for r in rs if r.get("kind") == "keepalive_verdict"]
    fired = sum(1 for r in ka if r.get("fired"))
    print()
    print(f"KEEP-ALIVE: {len(ka)} verdict row(s), {fired} FIRED")
    if not ka:
        print("  no keepalive_verdict rows at all -- the flag was OFF for this run.")
        print("  (Expected for any capture before MOVECODE-K1 existed. For a K1 arm "
              "it means")
        print("   --keepalive-grant did not reach the GAME instance: check the "
              "[map] banner,")
        print("   and remember --game-args needs the = form for a value starting "
              "with a dash.)")
    else:
        for (reason, ok), n in collections.Counter(
                (r.get("reason"), bool(r.get("fired"))) for r in ka).most_common():
            print(f"  {reason:<16} fired={str(ok):<5} x{n}")
        seps = sorted(r["sep"] for r in ka
                      if isinstance(r.get("sep"), (int, float)))
        if seps:
            print(f"  separation at the verdict, n={len(seps)}: "
                  f"min {seps[0]:.0f}  p50 {seps[len(seps) // 2]:.0f}  "
                  f"max {seps[-1]:.0f} u")
        if not fired:
            print()
            print("  !! ZERO FIRED. This arm has NO EXPOSURE and its result is not a")
            print("     null -- RUN-K1.md pre-registers that. The reason census "
                  "above names")
            print("     which gate refused; each is a different thing to fix.")

    grants = sum(1 for r in rs
                 if r.get("kind") == "sent" and r.get("opcode") == GRANT_OPCODE)
    ticks = sum(1 for r in rs
                if r.get("kind") == "sent" and r.get("opcode") == TICK_OPCODE)
    print()
    print(f"GRANTS: {grants} x 0x0029 sent"
          + (f"  ({grants / span:.3f}/s)" if span else "")
          + "   [run 5 sent 51]")
    print(f"TICKS:  {ticks} x 0x001E"
          + (f"  ({ticks / span:.3f}/s)" if span else "")
          + "   [retail 5.822/s]")

    cv = [r for r in rs if r.get("kind") == "click_verdict"]
    # ANSWERED vs REFUSED, and the split is not cosmetic. Under MOVECODE-K2 a
    # `geo-stale` row can be ANSWERED (echoed) rather than dropped, so counting
    # every click_verdict row as a refusal -- which this did on K2's first arm --
    # reports 8 refusals for a run that refused none of them. `fired` is the
    # discriminator and the row has carried it since K2.
    echoed = [r for r in cv if r.get("click_echo")]
    refused = [r for r in cv if not r.get("fired")]
    print()
    print(f"CLICK VERDICTS: {len(cv)}   ANSWERED {len(cv) - len(refused)}"
          f"   REFUSED {len(refused)}")
    if echoed:
        print(f"  of the answered, {len(echoed)} were K2 ECHOES of a stale click")
        print(f"  (MOVECODE-K2's pre-registered exposure floor is 3 -- "
              f"FINDINGS sec.1m.4)")
    for reason, n in collections.Counter(
            (r.get("reason"), bool(r.get("fired"))) for r in cv).most_common():
        print(f"  {reason[0]:<16} answered={str(reason[1]):<5} x{n}")
    if refused:
        # The split FINDINGS §1i.5 found, and it is worth watching per arm: only the
        # geometry pair is the navmesh, and the two want different fixes.
        geo = sum(1 for r in refused
                  if r.get("reason") in ("geo-blocked", "geo-unplaced"))
        stale = sum(1 for r in refused if r.get("reason") == "geo-stale")
        print(f"  -> of the REFUSED: {stale} staleness, {geo} geometry.")
        print("     Different defects; only the second is the mesh. FINDINGS "
              "sec.1i.5.")

    # ROUTER rows, because a router run records NOTHING in click_verdict --
    # router_answer_click intercepts above the freshness block and returns True,
    # so the census above prints "CLICK VERDICTS: 0" for a run that answered every
    # click. That is exactly the shape of report this file exists to prevent.
    rr = [r for r in rs if str(r.get("kind", "")).startswith("router")]
    if rr:
        print()
        routes = [r for r in rr if r.get("kind") == "router_route"]
        print(f"ROUTER: {len(routes)} route(s) -- the click census above is BLIND "
              f"to these")
        for v, n in collections.Counter(
                r.get("verdict") for r in routes).most_common():
            print(f"  {str(v):<16} x{n}")
        wp = [r.get("n_wp") for r in routes
              if isinstance(r.get("n_wp"), int)]
        if wp:
            print(f"  waypoints per route: min {min(wp)}  max {max(wp)}")
        # THE ORIGIN IS THE ROUTER'S WEAK POINT and it is worth printing: it comes
        # from state["pos"], the integrator's belief, and during click-walking the
        # client sends no position to correct it (FINDINGS §1m.2).
        legs = [r for r in rr if r.get("kind") == "router_leg"
                and r.get("act") == "grant"]
        print(f"  first legs granted: {len(legs)}")
        firsts = collections.Counter(
            tuple(r["dest"]) for r in legs if isinstance(r.get("dest"), list))
        rep = [(d, n) for d, n in firsts.most_common() if n > 1]
        if rep:
            print("  !! a leg granted MORE THAN ONCE -- the route is being "
                  "recomputed and")
            print("     landing on the same waypoint, which drags the body "
                  "back to it each time:")
            for d, n in rep[:4]:
                print(f"       ({d[0]:.0f}, {d[1]:.0f})  x{n}")

    gv = [r for r in rs if r.get("kind") == "grant_verdict"]
    if gv:
        print()
        print(f"GRANT VERDICTS: {len(gv)}")
        for (reason, ok), n in collections.Counter(
                (r.get("reason"), bool(r.get("fired"))) for r in gv).most_common():
            print(f"  {reason:<16} fired={str(ok):<5} x{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
