# Reproduction scripts for the 2026-09-04 movement review

Read-only census scripts written by the review's agents against the tree at `d0cc63c`,
kept so that the numbers in [../MOVEMENT-2026-09-04.md](../MOVEMENT-2026-09-04.md)
regenerate instead of rotting. **They are unpromoted**: no tests, no `TESTS.md` entry,
no floors; several hard-code `C:/gd/Rurik` and read the local vault through
`toolkit/vaultpath.py` or an absolute path. Run from the tree root with
`python studies/review/movement-2026-09-04/<script>.py`. Every one prints and writes nothing.
If one of these earns a place in the suite, promote it in the shape of
`toolkit/clientscan/test_planecensus.py` (re-derive both sides, assert the document
says the corpus's value) rather than pinning today's counts.

| Script | Backs | What it prints |
|---|---|---|
| `retail_2c_and_cruise.py` | Verdict fact 1; §1.2 | retail vs ours 0x003D cruise-pair gap and chord distributions over the 61 live connections; retail 0x002C to the player split by walking-body |
| `retail_report_gap.py` | §1.2, §3.10 | the raw retail inter-report gap census the cruise filter was built on |
| `a4_sep.py` | §1.1 | moving-only vs all-sample world-0 separation over the 09-04 default-configuration agenttap tapes |
| `warpcensus.py`, `bannercensus.py` | §1.4 | movesync two-arm hard bar per active minute grouped by each capture's own flags banner; harness join |
| `routerab.py` | §1.4 | the banner-labelled router-ON vs router-OFF head-to-head that does not reproduce 1.60/2.44 |
| `mf2_tapejumps_all.py`, `ma2_all41.py`, `ma2_wirevstape.py` | §1.4, §3.2 | per-sample drawn-body jumps on every agenttap tape joined to the wire bar's verdict on the same capture; the raw/live artifact split |
| `mf4_repins.py`, `ma6_census3.py`, `ma7_002c_census.py` | §1.5, §3.6 | every player 0x002C by sender and trigger, by capture flags; walking-body and halt-signature classification |
| `pinjoin2.py`, `selffulfil.py` | §1.5 | the press-pin tape join at the pre-set and post-set samples (§1z-ak.3 vs §1z-u.6) |
| `mf12_additive.py` | §1.6 | the §1z-s.3 retrodiction loop re-run with the HEAD guard; the shipped additive arm's own share |
| `ma3_corner_test.py`, `ma3_hausdorff.py` | §3.4 | the client's tier-3 waypoints against our trapezoid corners and edges; per-row Hausdorff vs `route()` on r7 |
| `f6_planelaw.py` | "What this arc does better" | the R7 plane law re-scored with the map-146 return-tap queries and the edge-rounding reading of the 17 off-mesh points |
| `mf6_census.py`, `ma8_cone.py` | §3.1 | the gate-2 fire vs park join and the follower-in-cone predicate over the taped lead runs |
| `f2_upstream_policy_sim.py` | §3.12 | OpenTyria's keyboard policy driven through `agtrack_mirror` |
| `tick_pairing_census.py` | §3.12 | retail 0x001E cadence and its pairing with movement messages |
| `threadwalk_cost.py` | §3.8 | the per-poll cost of `_threads_of()` |
