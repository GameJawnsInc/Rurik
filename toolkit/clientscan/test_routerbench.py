"""Checks for toolkit/clientscan/routerbench.py (ROUTER-B1).

Two layers, same shape as test_policyreplay.py:

  Section 1 -- synthetic, bare-machine: the pure helpers (player-agent
  voting, chain assembly and its three endings, leg-cadence math against the
  hand-verified 63805 numbers, the dead-reckoned origin model, the polyline
  distance, the wire map id, the heading-clip mesh check on a stub mesh).

  Sections 2-4 -- the real corpus (vault + dat; each skips LOUDLY when its
  input is absent): the FIDELITY GATE -- census() must reproduce the
  desk-skeptic's committed RETHINK-QB numbers from the same tapes (29
  clicks, 29/29 answered within one RTT, 16 verbatim / 13 part-way, 8
  superseded chains, the 63805 nine-grant monotone bit-exact-terminal
  chain); the meshcheck must reproduce Q7's independent numbers (the D1
  formula's bit-band rate and the map-280 clip-agreement fraction) on two
  immutable anchor connections; and section B's hard invariants must hold
  (every routed specimen's legs clip-clean and terminal exactly the click,
  every scoreable retail-verbatim click reproduced as our one-leg case).

  Corpus-level counts are locked as >= floors (the live corpus can only
  grow); bit-exact locks live on the two anchor connections, whose files are
  immutable vault captures.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)

import checks                                                  # noqa: E402
import routerbench as rb                                       # noqa: E402
import archive                                                 # noqa: E402

# Floor from the 2026-08-26 green run on the owner's machine (48 checks:
# 28 synthetic + 11 census + 2 meshcheck + 7 scoring). The vault-dependent
# sections skip loudly on a bare machine and the floor names the shortfall.
LEDGER = checks.Ledger("routerbench", floor=48)
check = checks.adopt_named(LEDGER)


# ---------------------------------------------------------------------------
# Section 1 -- synthetic, bare machine
# ---------------------------------------------------------------------------

def s2c_grant(t, agent, pt, pf=0, ps=0):
    return (t, "s2c", rb.OP_GRANT, [41, agent, pt, pf, ps])


def c2s_report(t, pt, plane=0, vec=(0.0, 765.0), mt=1):
    return (t, "c2s", rb.OP_REPORT, [32829, pt, plane, vec, mt])


def c2s_stop(t, pt, plane=0):
    return (t, "c2s", rb.OP_STOP, [32839, pt, plane])


def c2s_click(t, pt, plane=0):
    return (t, "c2s", rb.OP_CLICK, [32830, pt, plane])


def section1():
    print("== 1: synthetic helpers ==")

    # player_agent: agent 7's grants answer the headings, agent 9's do not.
    merged = []
    for i in range(5):
        merged.append(c2s_report(10.0 + i, (0.0, 0.0)))
        merged.append(s2c_grant(10.05 + i, 7, (1.0, 1.0)))
        merged.append(s2c_grant(10.5 + i, 9, (2.0, 2.0)))
    merged.sort(key=lambda r: r[0])
    agent, votes = rb.player_agent(merged)
    check("op61 vote picks the answering agent", agent == 7)
    check("vote landslide recorded", votes[7] == 5 and votes[9] == 0)

    # chain_for_click: terminal ending.
    click = (100.0, 100.0)
    merged = [c2s_click(20.0, click),
              s2c_grant(20.03, 7, (50.0, 50.0)),
              s2c_grant(21.0, 7, click)]
    grants, end = rb.chain_for_click(merged, 7, 20.0, click)
    check("terminal chain keeps both grants", len(grants) == 2)
    check("terminal ending named", end == "terminal")

    # superseded by a later click: the second click's answer is never ours.
    merged = [c2s_click(20.0, click),
              s2c_grant(20.03, 7, (50.0, 50.0)),
              c2s_click(21.0, (300.0, 300.0)),
              s2c_grant(21.03, 7, (300.0, 300.0))]
    grants, end = rb.chain_for_click(merged, 7, 20.0, click)
    check("supersession stops the chain", len(grants) == 1)
    check("supersession names the opcode", end == "superseded:62")

    # superseded by keyboard resume; and the open ending.
    merged = [c2s_click(20.0, click), s2c_grant(20.03, 7, (50.0, 50.0)),
              c2s_report(22.0, (55.0, 55.0))]
    _g, end = rb.chain_for_click(merged, 7, 20.0, click)
    check("keyboard supersession named", end == "superseded:61")
    merged = [c2s_click(20.0, click), s2c_grant(20.03, 7, (50.0, 50.0))]
    _g, end = rb.chain_for_click(merged, 7, 20.0, click)
    check("capture-end leaves the chain open", end == "open")

    # leg_speeds on the 63805 chain's own numbers (hand-verified before this
    # module existed: leg wp3->wp4 is 557u walked in 1.946s = 286 u/s, and
    # the desk-skeptic's committed eight-leg list starts 288.5, 282.8).
    origin = (-5150.20, 8126.20)
    chain = [(1103.622, (-4896.0, 7872.0), 0, 0),
             (1104.868, (-4860.0, 7688.0), 0, 0),
             (1105.531, (-4915.0, 7578.0), 0, 0),
             (1105.950, (-5469.0, 7518.0), 0, 0),
             (1107.897, (-5514.0, 7511.0), 0, 0),
             (1108.036, (-5654.0, 7456.0), 0, 0),
             (1108.578, (-5666.0, 7393.0), 0, 0),
             (1108.780, (-5824.36474609375, 6430.0), 0, 0),
             (1112.170, (-5842.87939453125, 6317.4130859375), 0, 0)]
    speeds = [s for _leg, _dt, s in rb.leg_speeds(origin, chain)]
    check("63805 has eight measurable legs", len(speeds) == 8)
    check("first leg speed is the committed 288.5",
                 abs(speeds[0] - 288.5) < 0.1)
    check("second leg speed is the committed 282.8",
                 abs(speeds[1] - 282.8) < 0.1)
    check("six of eight legs within 4pct of run speed",
                 sum(1 for s in speeds
                     if abs(s - rb.RUN_SPEED) <= 0.04 * rb.RUN_SPEED) == 6)

    # along_fraction: monotone on that same chain, 1.0 at the click.
    cpt = chain[-1][1]
    fracs = [rb.along_fraction(origin, cpt, g[1]) for g in chain]
    check("along-fraction monotone over the chain",
                 all(b > a for a, b in zip(fracs, fracs[1:])))
    check("terminal along-fraction is exactly 1.0",
                 abs(fracs[-1] - 1.0) < 1e-12)

    # modeled_origin: mid-leg, arrival clamp, report reset, age.
    merged = [c2s_stop(0.0, (0.0, 0.0)),
              s2c_grant(1.0, 7, (288.0, 0.0)),
              s2c_grant(10.0, 7, (288.0, 100.0))]
    pos, age = rb.modeled_origin(merged, 7, 1.5)
    check("dead-reckons mid-leg at run speed",
                 abs(pos[0] - 144.0) < 1e-9 and pos[1] == 0.0)
    pos, _age = rb.modeled_origin(merged, 7, 5.0)
    check("clamps at the granted point on arrival",
                 pos == (288.0, 0.0))
    pos, age = rb.modeled_origin(merged, 7, 10.2)
    check("second grant walks from the first's endpoint",
                 abs(pos[1] - 57.6) < 1e-9 and abs(pos[0] - 288.0) < 1e-9)
    check("age counts from the last report anchor",
                 abs(age - 10.2) < 1e-9)
    merged.append(c2s_report(11.0, (500.0, 500.0)))
    pos, age = rb.modeled_origin(merged, 7, 11.5)
    check("a report resets the model", pos == (500.0, 500.0)
                 and abs(age - 0.5) < 1e-9)
    check("no position source refuses",
                 rb.modeled_origin([s2c_grant(1.0, 7, (1.0, 1.0))], 9, 2.0)
                 is None)

    # _point_to_polyline: interior projection and endpoint clamp.
    line = [(0.0, 0.0), (10.0, 0.0)]
    check("polyline distance projects onto the segment",
                 abs(rb._point_to_polyline((5.0, 3.0), line) - 3.0) < 1e-9)
    check("polyline distance clamps at the endpoint",
                 abs(rb._point_to_polyline((13.0, 4.0), line) - 5.0) < 1e-9)

    # wire_map_id
    merged = [(1.0, "s2c", rb.OP_INSTANCE, [409, 1, 280, 1, 0, 0, 0])]
    check("wire map id read from op409", rb.wire_map_id(merged) == 280)
    check("no instance row -> None", rb.wire_map_id([]) is None)

    # heading_clip_agreement on a stub mesh: wall at x=200.
    class StubPM:
        def walkable(self, x, y):
            return x < 200.0

        def clip(self, x0, y0, x1, y1, step=16.0):
            # straight walk, stop before the wall (fine-grained).
            d = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(d / 2.0))
            best = (x0, y0)
            for i in range(1, n + 1):
                f = i / n
                p = (x0 + f * (x1 - x0), y0 + f * (y1 - y0))
                if not self.walkable(p[0], p[1]):
                    return best
                best = p
            return (x1, y1)

    pm = StubPM()
    vec = (765.0, 0.0)
    exp = (0.0 + 765.0 + 0.5, 0.0)   # the D1 prediction from (0,0)
    merged = [
        # pair 1: retail grants the exact prediction -> exact-D1.
        c2s_report(1.0, (0.0, 0.0), vec=vec), s2c_grant(1.05, 7, exp),
        # pair 2: retail clipped at the wall; our clip agrees within 3u.
        c2s_report(2.0, (0.0, 0.0), vec=vec), s2c_grant(2.05, 7, (199.0, 0.0)),
        # pair 3: retail clipped where our stub has no wall -> disagree.
        c2s_report(3.0, (0.0, 0.0), vec=vec), s2c_grant(3.05, 7, (90.0, 0.0)),
        # non-band vector: ignored.
        c2s_report(4.0, (0.0, 0.0), vec=(10.0, 0.0)),
        s2c_grant(4.05, 7, (10.0, 0.0)),
    ]
    r = rb.heading_clip_agreement(merged, 7, pm)
    check("clip check pairs only D1-band reports", r["n_pairs"] == 3)
    check("bit-band answer counted as exact-D1", r["n_exact"] == 1)
    check("agreeing truncation lands <=3u", r["agree3"] == 1)
    check("phantom truncation disagrees",
                 r["n_clipped"] == 2 and r["agree10"] == 1)


# ---------------------------------------------------------------------------
# Sections 2-4 -- the real corpus (vault + dat), each skipping loudly
# ---------------------------------------------------------------------------

# The corpus these locks were set from (2026-08-26). The live corpus can
# only grow; corpus-level counts below are >= floors, and the bit-exact
# locks are per-connection on immutable capture files.
ANCHOR_63805 = ("20260817T231139",
                "game-10.0.0.210_63805-to-52.3.40.244_80.jsonl")
ANCHOR_62994 = ("20260807T143055",
                "game-10.0.0.210_62994-to-54.198.7.73_80.jsonl")


def _have_corpus():
    root = rb.livewire.captures_root()
    return (os.path.isdir(os.path.join(root, ANCHOR_63805[0]))
            and os.path.isdir(os.path.join(root, ANCHOR_62994[0])))


def section2_census():
    print("== 2: the fidelity gate (census vs the committed QB numbers) ==")
    if not _have_corpus():
        LEDGER.skip("census fidelity", "live captures not on this machine")
        return None
    rows, skipped = rb.census()
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    within = sum(1 for r in rows
                 if r["first_dt"] is not None
                 and r["first_dt"] <= rb.RTT_WINDOW)
    superseded = sum(1 for r in rows if r["end"].startswith("superseded"))
    check("census finds the committed corpus (>=29 clicks)",
                 len(rows) >= 29, f"got {len(rows)}")
    check("every click answered within one RTT window",
                 within == len(rows), f"{within}/{len(rows)}")
    check("verbatim count at least the committed 16",
                 kinds.get("verbatim", 0) >= 16, f"got {kinds}")
    check("part-way count at least the committed 13",
                 kinds.get("part-way", 0) >= 13, f"got {kinds}")
    check("no unanswered class survives (QB-4's refutation)",
                 kinds.get("no-answer", 0) == 0, f"got {kinds}")
    check("the eight superseded chains found",
                 superseded >= 8, f"got {superseded}")
    # The anchor chain, bit-exact.
    chain = [r for r in rows
             if r["conn"] == ANCHOR_63805[1] and abs(r["t"] - 1103.590) < 0.01]
    check("63805 anchor click present", len(chain) == 1)
    if chain:
        r = chain[0]
        check("anchor chain has its nine grants",
                     r["n_grants"] == 9 and r["end"] == "terminal")
        check("anchor first answer within the observed band",
                     r["first_dt"] is not None and r["first_dt"] <= 0.065)
        origin = r["origin"]
        fr = [rb.along_fraction(origin, r["click"], g[1])
              for g in r["grants"]]
        check("anchor along-fraction monotone to 1.0",
                     all(b > a for a, b in zip(fr, fr[1:]))
                     and abs(fr[-1] - 1.0) < 1e-12)
        check("anchor terminal grant bit-exact",
                     r["grants"][-1][1] == r["click"])
    return rows


def section3_meshcheck():
    print("== 3: mesh-identity locks (heading-clip vs Q7's numbers) ==")
    if not _have_corpus():
        LEDGER.skip("meshcheck locks", "live captures not on this machine")
        return
    if not os.path.exists(archive.DEFAULT_DAT):
        LEDGER.skip("meshcheck locks", "no Gw.dat on this machine")
        return
    candidates = rb.mesh_candidates()
    root = rb.livewire.captures_root()
    for (cap, gf), want in [
        # (pairs, exact, clipped, agree3) measured on the immutable anchor
        # files, 2026-08-26. 63805's 65/209 is the terrain-edge+prop mix
        # Q7 measured (248/701 corpus-wide); 62994's 8/9 is the map-146
        # terrain-edge population.
        (ANCHOR_63805, (506, 297, 209, 65)),
        (ANCHOR_62994, (98, 89, 9, 8)),
    ]:
        capdir = os.path.join(root, cap)
        _conn, merged, ok = rb.livewire.decode_conn(capdir, gf)
        if not ok:
            check(f"{gf} decodes", False)
            continue
        agent, _v = rb.player_agent(merged)
        mid = rb.wire_map_id(merged)
        cand = candidates.get(str(mid))
        if cand is None:
            check(f"{gf} map {mid} in content", False)
            continue
        pm = rb._load_pm(cand[1])
        r = rb.heading_clip_agreement(merged, agent, pm)
        got = (r["n_pairs"], r["n_exact"], r["n_clipped"], r["agree3"])
        check(f"{cap}/{gf.split('_')[1].split('-')[0]} "
                     f"heading-clip numbers locked", got == want,
                     f"got {got} want {want}")


def section4_score(census_rows):
    print("== 4: route() vs retail -- hard invariants ==")
    if not _have_corpus():
        LEDGER.skip("route scoring", "live captures not on this machine")
        return
    if not os.path.exists(archive.DEFAULT_DAT):
        LEDGER.skip("route scoring", "no Gw.dat on this machine")
        return
    scored, refused = rb.score_corpus()
    check("scored the committed specimen count (>=26)",
                 len(scored) >= 26, f"got {len(scored)}")
    routed = [(row, s) for row, _m, _c in scored
              for s in [row["score"]] if s["routed"]]
    check("routed at least the committed 25",
                 len(routed) >= 25, f"got {len(routed)}")
    check("every routed specimen's legs clip-clean",
                 all(s["legs_clean"] for _r, s in routed))
    check("every routed terminal is exactly the click",
                 all(s["terminal_is_click"] for _r, s in routed))
    # The headline: every scoreable retail-VERBATIM click reproduces as our
    # one-leg case, bit-identically. Restricted to the anchor-era captures
    # so corpus growth cannot flip it silently; a new capture that breaks
    # the clause is a finding for the doc, not a regression here.
    era = {"20260807T143055", "20260817T231139", "20260817T183756",
           "20260818T132739", "20260821T163511", "20260824T074002"}
    verb = []
    rows_by_key = {}
    if census_rows:
        rows_by_key = {(r["cap"], r["conn"], round(r["t"], 3)): r
                       for r in census_rows}
    for row, _m, _c in scored:
        if row["cap"] not in era:
            continue
        cr = rows_by_key.get((row["cap"], row["conn"], round(row["t"], 3)))
        if cr is not None and cr["kind"] == "verbatim":
            verb.append(row["score"])
    check("all 13 scoreable verbatim clicks found",
                 len(verb) == 13, f"got {len(verb)}")
    check("verbatim class reproduces as the one-leg case",
                 all(s["routed"] and s["n_wp_ours"] == 1
                     and s["first_wp_dist"] == 0.0 for s in verb))
    check("refusals are all named", all(len(t) == 3 for t in refused))


def main():
    section1()
    rows = section2_census()
    section3_meshcheck()
    section4_score(rows)
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
