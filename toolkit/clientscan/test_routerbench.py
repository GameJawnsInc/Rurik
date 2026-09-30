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
# 2026-09-30: 50 -> 58 from the green run, the action hold's five synthetic
# checks and section 2's three (33 synthetic + 16 census + 2 + 7).
LEDGER = checks.Ledger("routerbench", floor=58)
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


def s2c_hold(t, agent, value):
    return (t, "s2c", rb.OP_PROP_INT, [159, rb.PROP_HOLD, agent, value])


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

    # hold_at / hold_verdict (2026-09-30): the action hold's four outcomes,
    # every answer known by construction -- including the one retail has not
    # been seen to do, which must NOT read as any of the other three.
    P, B = 7, 8
    merged = [
        s2c_hold(1.0, P, 1), s2c_hold(1.1, B, 0),          # another body's
        c2s_click(1.5, (100.0, 0.0)),                      # A: in the hold
        s2c_hold(2.0, P, 0), s2c_grant(2.0, P, (40.0, 0.0)),   # release == grant
        c2s_click(3.0, (100.0, 0.0)),                      # B: free
        s2c_grant(3.03, P, (100.0, 0.0)),
        s2c_hold(5.0, P, 1), s2c_hold(5.1, P, 1),          # a re-arm
        c2s_click(5.2, (200.0, 0.0)),                      # C: superseded ...
        c2s_click(5.4, (300.0, 0.0)),                      # D: ... by D
        s2c_hold(6.0, P, 0), s2c_grant(6.0, P, (250.0, 0.0)),
        s2c_hold(8.0, P, 1),
        c2s_click(8.1, (400.0, 0.0)),                      # E: the bad arm
        s2c_grant(8.15, P, (400.0, 0.0)),                  # a grant IN the hold
        s2c_hold(9.0, P, 0),
    ]
    rows = {t: rb.click_row(merged, P, t, pt) for t, pt, _pl in rb.click_rows(merged)}
    v = {t: rb.hold_verdict(r) for t, r in rows.items()}
    check("hold_at: set, released at the first clear, a re-arm is not a release, "
          "another body's clear is not this one's",
          rb.hold_at(merged, P, 1.5) == (True, 2.0)
          and rb.hold_at(merged, P, 5.2) == (True, 6.0)
          and rb.hold_at(merged, P, 3.0) == (False, None)
          and rb.hold_at(merged, B, 1.5) == (False, None))
    check("a click inside a hold answered at the release reads answered-at-release, "
          "and its first grant is 0.5 s late -- past one RTT",
          v[1.5] == "answered-at-release" and rows[1.5]["kind"] == "no-answer",
          f"{v[1.5]}, {rows[1.5]['kind']}")
    check("a click outside one reads free",
          v[3.0] == "free" and rows[3.0]["kind"] == "verbatim")
    check("a held click superseded before the release reads superseded-in-hold, and "
          "the release answers the click that superseded it",
          v[5.2] == "superseded-in-hold" and v[5.4] == "answered-at-release",
          f"{v[5.2]}, {v[5.4]}")
    check("the known-bad arm: a grant INSIDE the hold reads held-other, not "
          "answered-at-release", v[8.1] == "held-other", v[8.1])


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
# The first click the census found unanswered (2026-09-30): RANGERPRE's tape,
# 0.44 s into the player's hold after a pickup's arrival (0x009F [8, 9, 1],
# 0x0159, 0x0028), superseded by a second click at +0.482, which the release at
# +0.552 answered. It is also the pin: every click before this capture was
# answered within one RTT.
HOLD_WITNESS = ("20260929T150923", "_53756-", 1126.006)


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
    # RE-SCOPED 2026-09-30, not loosened. RETHINK-QB's "every click answered
    # within one RTT" held on 148 clicks and then met a click sent INSIDE the
    # player's action hold (RANGERPRE's tape, HOLD_WITNESS): no grant for
    # 0.55 s, then superseded. animref FINDINGS 30.4 had already measured the
    # law: under property 8 retail grants nothing, and the release and the
    # grant are one event. The corpus holds four held clicks. Three were
    # answered AT the release, and it came inside one RTT only because they
    # were sent late in their holds. So the RTT contract is about FREE clicks,
    # and a held click owes something stricter: the release instant exactly.
    free = [r for r in rows if not r["held"]]
    within_free = sum(1 for r in free
                      if r["first_dt"] is not None
                      and r["first_dt"] <= rb.RTT_WINDOW)
    pre = [r for r in rows if r["cap"] < HOLD_WITNESS[0]]
    within_pre = sum(1 for r in pre
                     if r["first_dt"] is not None
                     and r["first_dt"] <= rb.RTT_WINDOW)
    held = {}
    for r in rows:
        if r["held"]:
            held.setdefault(rb.hold_verdict(r), []).append(r)
    check("every click outside an action hold answered within one RTT window",
                 within_free == len(free),
                 f"{within_free}/{len(free)} free; {within}/{len(rows)} "
                 f"of all clicks, {len(rows) - len(free)} inside a hold")
    check(f"and before {HOLD_WITNESS[0]}, every click at all -- QB's claim "
          f"exact on the captures it was pinned on",
                 len(pre) >= 29 and within_pre == len(pre),
                 f"{within_pre}/{len(pre)}")
    check("a click inside a hold is answered AT the release, to the "
          "microsecond (animref 30.4's one event), or superseded before it",
                 "held-other" not in held
                 and len(held.get("answered-at-release", ())) >= 3,
                 str({k: [(r["cap"], round(r["t"], 3)) for r in v]
                      for k, v in sorted(held.items())}))
    check("verbatim count at least the committed 16",
                 kinds.get("verbatim", 0) >= 16, f"got {kinds}")
    check("part-way count at least the committed 13",
                 kinds.get("part-way", 0) >= 13, f"got {kinds}")
    unanswered = [r for r in rows if r["kind"] == "no-answer"]
    check("no unanswered class survives outside a hold (QB-4's refutation): "
          "every no-answer is a click superseded inside its hold",
                 all(rb.hold_verdict(r) == "superseded-in-hold"
                     for r in unanswered),
                 f"got {kinds}; "
                 f"{[(r['cap'], round(r['t'], 3), rb.hold_verdict(r)) for r in unanswered]}")
    wit = [r for r in rows
           if r["cap"] == HOLD_WITNESS[0] and HOLD_WITNESS[1] in r["conn"]
           and abs(r["t"] - HOLD_WITNESS[2]) < 0.01]
    nxt = [r for r in rows
           if wit and r["conn"] == wit[0]["conn"]
           and r["t"] > wit[0]["t"]][:1]
    check("the witness: RANGERPRE's pickup-hold click is superseded inside "
          "its hold, and the release answers the click that superseded it",
                 len(wit) == 1 and rb.hold_verdict(wit[0]) == "superseded-in-hold"
                 and len(nxt) == 1
                 and rb.hold_verdict(nxt[0]) == "answered-at-release",
                 f"{[(round(r['t'], 3), rb.hold_verdict(r), r['release_dt']) for r in wit + nxt]}")
    check("the eight superseded chains found",
                 superseded >= 8, f"got {superseded}")
    # The two-controlled-agents click (20260914T180058, conn 55087). Its
    # connection votes 206:6 vs 538:4 for the player, but 206 does not move
    # until t=82s and the click at t=42.4 is answered bit-exact by 538 at +46ms.
    # answering_agent() attributes it to 538 by the server's own answer; before
    # that fix it was the corpus's lone false no-answer. Pinned so a change to
    # the fallback reddens with the reason rather than reopening the red.
    two_agent = [r for r in rows
                 if r["cap"] == "20260914T180058"
                 and "55087" in r["conn"] and abs(r["t"] - 42.392) < 0.01]
    check("the two-controlled-agents click is present", len(two_agent) == 1,
                 f"got {len(two_agent)}")
    if two_agent:
        r = two_agent[0]
        check("it is attributed to the answering agent 538, not the vote-winner "
              "206, and reads verbatim",
                     r["agent"] == 538 and r["kind"] == "verbatim"
                     and r["first_dt"] is not None and r["first_dt"] <= rb.RTT_WINDOW,
                     f"agent {r['agent']}, {r['kind']}, first_dt {r['first_dt']}")
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
    # 13 UNTIL 2026-08-28, and the 14th is confirming evidence rather than
    # drift: content/maps.toml gained rows for maps 242, 248 and 310
    # (studies/movecode/FINDINGS.md 1p.10 item 4), and map 310's click
    # 20260817T231139/_54071 t=672.403 -- inside the era set already, refused
    # before only because `score_corpus` could not name its mesh -- entered the
    # scored set and reproduced as the one-leg case like the other 13. The pin
    # was re-scanned AS OF ITS OWN VALUE first: on the commit before those rows
    # this expression returned exactly 13, so the whole delta is the content
    # change and none of it is a moved constant. Held as a FLOOR from here, per
    # the house rule about counts that redden on confirming evidence -- the
    # direction that must still go red is LOSING verbatim rows, and the check
    # below is the strict one, since it must hold for every row found.
    check("at least the 14 scoreable verbatim clicks found (13 before the "
          "2026-08-28 content rows)",
                 len(verb) >= 14, f"got {len(verb)}")
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
