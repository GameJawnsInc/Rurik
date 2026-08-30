"""`planecensus.py` -- and the four ways this census can lie without going red.

WHY THIS FILE EXISTS. The census made two wrong turns on its way to a number,
and both LOOKED RIGHT and produced a confident percentage:

  1. It scored the plane_echo tripwire from `grant_verdict.plane_dest` at
     `grant_verdict.dest` -- structurally reasonable, and refuted only because a
     control against the live tripwire's own three sessions read 0/0/5 against a
     logged 4/30/9.
  2. It then read 0x0029's trailing dword as ONE u32 plane and published 15.29%.
     The dword is TWO u16s; the tell was "we emit plane 1703962", which is
     0x001A001A -- the label's own "26->26".

Neither is caught by reading the diff. Both are caught by a control that can go
red, so the controls are what this file pins.

  §1  THE MESH PIN IS IN BAND AND TOTAL. Every position_report is attributable
      to a file id from the capture's own opcode-405 load message, no capture
      names two, and the `version` record's map_id is NOT that id. If a future
      change reintroduces map_id as the pin, §1 goes red.
  §2  THE WIRE FIELD IS THE ONE THE TRIPWIRE SCORES, held by reproducing the
      live tripwire exactly. This is the control that refuted take 1 and take 2,
      so it is the check that must never become vacuous -- it asserts the row
      count FIRST, because `all([])` is True and this arc has already shipped a
      no-collapse control that judged zero rows.
  §3  THE REPLAY STILL MATCHES `authsrv.plane_repair_track`. The trigger is
      MIRRORED here, not imported (importing authsrv.py opens sockets), so it
      can go stale silently. §3 re-reads authsrv.py's own constants and clause
      strings and fails if they have drifted.
  §6  THE PUBLISHED FIGURES ARE STILL RE-DERIVABLE, and the identities hold.
      FIVE denominator or population errors have now been shipped in FINDINGS
      1z-n/1z-o and caught only afterwards. The last one is why this section
      exists: a capture COUNT was left at 30 after the rate it shares a
      population with had been corrected to 282/7,543. **A population fix
      propagates to every figure drawn from that population**, and nothing was
      checking the rest. §6 pins the identities (on-mesh == AGREE + DISAGREE,
      and the direction classes partitioning DISAGREE) plus the ten headline
      figures, so a drift lands here instead of in a reader's quotation.
  §7  THE PROSE FIGURES ARE TIED TO THE CORPUS. §6 pins totals and identities
      and would NOT have caught the eight defects a denominator audit found in
      1z-n -- every one lived in a SENTENCE: a ratio quoted mid-paragraph, a
      histogram in a table, a claim about what one trace shows. Prose is where
      the errors survive. §7 re-derives each such figure and asserts THE
      DOCUMENT SAYS IT, the discipline `test_probedoc.py` applies to
      PROBE-GATEFIRE. Two of its checks are pure ARITHMETIC on the prose --
      the distance buckets must sum to DISAGREE, the bimodality buckets to the
      clean scoreable count -- which is free and catches a stale population
      without recomputing anything.
  §4  A STUB MESH IS NOT A FINDING. 0x287D3 decodes to 27 trapezoids in
      dat_study, and folding it into the headline reports 61.3% OFF-MESH about a
      client that did nothing unusual. §4 pins that stub reports are excluded
      from the headline and still visible per-mesh.

Everything here runs off the real corpus, so it is a live-fire test: it needs
`vault/captures/gamesrv/` and an archive that binds 0x287B3. Both are declared
skips if absent, and a skip that drops the run under the floor is a failure.
"""
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (TOOLKIT, HERE, os.path.join(TOOLKIT, "mapdata")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import checks                                              # noqa: E402
import planecensus as pc                                   # noqa: E402

LEDGER = checks.Ledger("planecensus", floor=54)
check = checks.adopt(LEDGER)

# The vault via vaultpath (a worktree has no vault of its own); the documents
# under test from THIS tree, so a worktree session tests its own prose.
VAULT = pc.default_vault()
CORPUS = os.path.join(VAULT, "captures", "gamesrv")
AUTHSRV = os.path.join(TOOLKIT, "authsrv", "authsrv.py")
FINDINGS = os.path.join(os.path.dirname(TOOLKIT), "studies", "movecode",
                        "FINDINGS.md")

# The live tripwire's own sessions, and what it logged in each. This is the
# control: any change to the wire decode must still reproduce these three.
TRIPWIRE_TRUTH = {
    "authsrv-20260829T132441-c1.jsonl": 4,
    "authsrv-20260829T142904-c1.jsonl": 30,
    "authsrv-20260829T163930-c1.jsonl": 9,
}


def main():
    if not os.path.isdir(CORPUS):
        LEDGER.skip("corpus", f"no capture corpus at {CORPUS}")
        return LEDGER.verdict()

    # ---- §1 the pin is in band, and it is total ----------------------
    labels, unlabelled, cross = pc.label_captures(VAULT, 600.0)
    check(bool(labels), "captures with reports carry an in-band file id",
          f"labelled {len(labels)}, unlabelled {len(unlabelled)}")
    check(not unlabelled,
          "EVERY capture carrying reports names its own mesh",
          f"these carry reports but no opcode-405 row: {unlabelled[:5]}")
    check(cross["capture declares MORE THAN ONE file id"] == 0,
          "no capture names two meshes, so one mesh per capture is sound",
          f"multi-id captures: {cross['capture declares MORE THAN ONE file id']}")
    check(cross["harness DISAGREES"] == 0,
          "the two independent witnesses to the mesh agree EXACTLY",
          f"disagreements {cross['harness DISAGREES']}, agreements "
          f"{cross['harness AGREES']}. This read 1 until the harness reader's "
          f"4 KB window was widened -- 15 logs print their navmesh line past "
          f"byte 4000, and the lone 'disagreement' was that truncation, not a "
          f"mispair. Any non-zero here means one of the two witnesses drifted.")
    check(cross["harness AGREES"] > 100,
          "the cross-check is not vacuous: most captures HAVE both witnesses",
          f"agreements {cross['harness AGREES']}, no-witness "
          f"{cross['no harness witness']} -- if the harness reader silently "
          f"stopped matching, 'DISAGREES == 0' would pass over an empty set")

    fids = {v["fid"] for v in labels.values()}
    check(len(fids) > 1,
          "the corpus spans MORE THAN ONE mesh, which map_id 148 denies",
          f"file ids seen: {sorted(hex(f) for f in fids)}")

    # A capture with SENDS but no position_reports must still be labelled.
    # `label_captures` used to `continue` on `not reports`, which is right for
    # the census (it scores reports) and WRONG for --echo (it scores sends).
    # The corpus has exactly one such capture and it is not a curiosity: it
    # holds the corpus's ONLY 0x002A send, and that send is a TRIP. The bug
    # published 281/7,542 where the truth is 282/7,543.
    sendonly = []
    for f in sorted(glob.glob(os.path.join(CORPUS, "*.jsonl"))):
        reports, sends, _e, fids2 = pc.read_capture(f)
        if sends and not reports and fids2:
            sendonly.append(os.path.basename(f))
    if not sendonly:
        LEDGER.skip("send-only captures",
                    "this corpus has no capture with sends but no reports")
    else:
        check(all(n in labels for n in sendonly),
              "a capture with SENDS but no position_reports is still labelled",
              f"send-only captures: {sendonly}; missing from labels: "
              f"{[n for n in sendonly if n not in labels]} -- dropping these "
              f"silently shrinks --echo's denominator")

    # the version record is the trap this instrument exists to avoid
    sample = next(iter(labels.values()))
    vmap = _version_map_id(sample["path"])
    check(vmap is None or 0x1B97D not in fids or vmap == 148,
          "the version record's map_id is the login constant, not the pin",
          f"version map_id={vmap}; the pin for this capture is "
          f"0x{sample['fid']:X}")

    # ---- §2 the wire field, held by the live tripwire ----------------
    meshes = pc.Meshes()
    present = [c for c in TRIPWIRE_TRUTH if c in labels]
    if not present:
        LEDGER.skip("tripwire control",
                    "none of the tripwire's own sessions are in this corpus")
    else:
        # ASSERT THE ROW COUNT FIRST. A control that judged zero rows is how
        # this repo shipped a vacuous no-collapse check; `all([])` is True.
        check(len(present) == len(TRIPWIRE_TRUTH),
              "all three tripwire sessions are present to control against",
              f"present: {present}")
        agreed = 0
        for cap in present:
            lab = labels[cap]
            pm = meshes.get(lab["fid"])
            if pm is None:
                continue
            _r, sends, logged, _f = pc.read_capture(lab["path"])
            trips = sum(1 for s in sends
                        if _offers(pm, s) and s["plane"] not in _offers(pm, s))
            check(logged == TRIPWIRE_TRUTH[cap],
                  f"{cap[-26:]}: the capture still holds its logged echoes",
                  f"logged {logged}, expected {TRIPWIRE_TRUTH[cap]}")
            check(trips == TRIPWIRE_TRUTH[cap],
                  f"{cap[-26:]}: planeA@14 reproduces the live tripwire",
                  f"recomputed {trips}, live {TRIPWIRE_TRUTH[cap]} -- if this "
                  f"went red the wire decode drifted; planeB@16 reads 237 "
                  f"corpus-wide against a true 43")
            agreed += trips == TRIPWIRE_TRUTH[cap]
        check(agreed == len(present),
              "the wire decode is pinned by a control, not by inference",
              f"{agreed} of {len(present)} sessions reproduced")

        # the discriminating power of that control: if the two u16s never
        # differed, reproducing 4/30/9 would prove nothing about WHICH field.
        differ = 0
        for cap in present:
            lab = labels[cap]
            _r, sends, _l, _f = pc.read_capture(lab["path"])
            differ += sum(1 for s in sends if s["plane"] != s["plane_b"])
        check(differ > 0,
              "the two plane words DO differ, so the control discriminates",
              f"planeA != planeB in {differ} sends across the control "
              f"sessions; at zero the control would be vacuous")

    # ---- §3 the mirrored trigger has not drifted ---------------------
    if not os.path.isfile(AUTHSRV):
        LEDGER.skip("trigger mirror", "authsrv.py not present")
    else:
        src = open(AUTHSRV, encoding="utf-8", errors="replace").read()
        for name, val in (("PLANE_REPAIR_HOLD", pc.HOLD),
                          ("PLANE_REPAIR_GAP", pc.GAP),
                          ("PLANE_REPAIR_MIN_INTERVAL", pc.MIN_INTERVAL)):
            m = re.search(rf"^{name} = ([0-9.]+)", src, re.M)
            check(m is not None and float(m.group(1)) == val,
                  f"{name} still matches the mirrored copy",
                  f"authsrv says {m.group(1) if m else 'MISSING'}, "
                  f"planecensus mirrors {val}")
        # every disarm string the replay reproduces must still exist upstream
        for clause in ("plane-legal", "off-mesh", "ambiguous", "arming",
                       "stale-stream", "holding", "rate-limited"):
            check(f'"{clause}"' in src,
                  f"the trigger still has a {clause!r} clause",
                  "the replay mirrors authsrv's clause set; a rename here "
                  "means the replay is scoring a trigger that no longer exists")

    # ---- §5 the headline does not depend on which archive -----------
    # THE ARCHIVE IS PART OF THE ANSWER for two meshes and irrelevant for the
    # rest, and that asymmetry is the whole reason the headline is quotable.
    # 0x287D3 decodes to 27 / 55 / 2 / 64 trapezoids across the vaulted
    # archives; the meshes that actually carry the corpus do not move at all.
    # If that ever stops being true the headline becomes archive-scoped and
    # every number in FINDINGS §1z-n needs an archive named beside it.
    alt = os.path.join(VAULT, "run",
                       "2026-07-29_221c13772c7a-probe", "Gw.dat")
    if not os.path.isfile(alt):
        LEDGER.skip("archive invariance", "the -probe archive is not vaulted")
    else:
        try:
            other = pc.Meshes(alt)
        except Exception as exc:
            LEDGER.skip("archive invariance", f"-probe unreadable: {exc!r}")
            other = None
        if other is not None:
            carriers = [f for f in fids
                        if meshes.get(f) is not None
                        and not meshes.is_stub(f)]
            check(len(carriers) >= 3,
                  "there ARE non-stub meshes to compare across archives",
                  f"carriers: {[hex(f) for f in carriers]} -- with none, the "
                  f"invariance check below would judge zero rows")
            moved = []
            for f in carriers:
                a, b = meshes.get(f), other.get(f)
                if b is None or (len(a.trapezoids) != len(b.trapezoids)
                                 or len(a.planes) != len(b.planes)):
                    moved.append(hex(f))
            check(not moved,
                  "every mesh that CARRIES the corpus decodes identically in "
                  "both archives",
                  f"moved: {moved} -- the headline is only archive-independent "
                  f"while this holds")
            stub_moved = [hex(f) for f in fids
                          if meshes.get(f) is not None
                          and other.get(f) is not None
                          and meshes.is_stub(f)
                          and len(meshes.get(f).trapezoids)
                          != len(other.get(f).trapezoids)]
            check(bool(stub_moved),
                  "and a STUB mesh really does move between archives, so the "
                  "invariance above is a finding rather than a tautology",
                  f"moved stubs: {stub_moved} -- if nothing moved, this test "
                  f"could not tell an archive-independent corpus from one "
                  f"where both archives are the same file")

    # ---- §4 a stub mesh is excluded, not averaged in -----------------
    stubs = [f for f in fids if meshes.get(f) is not None and meshes.is_stub(f)]
    if not stubs:
        LEDGER.skip("stub guard", "this archive binds no stub mesh")
    else:
        tot, bymap, _pc, _oh, _d, _rows = pc.census(labels, meshes)
        stub_reports = tot["reports on a STUB mesh (excluded from headline)"]
        check(stub_reports > 0,
              "stub-mesh reports are counted and named, not silently dropped",
              f"{stub_reports} reports sit on {len(stubs)} stub mesh(es)")
        headline = tot["reports"]
        check(headline + stub_reports <= sum(v["n"] for v in labels.values()),
              "the headline denominator EXCLUDES the stub reports",
              f"headline {headline}, stub {stub_reports}")
        check(any(meshes.key(f) in bymap for f in stubs),
              "the stub still appears per-mesh, so it can be seen",
              f"stub keys: {[meshes.key(f) for f in stubs]}")

    # ---- §6 THE PUBLISHED FIGURES ARE STILL RE-DERIVABLE --------------
    # WHY THIS SECTION EXISTS. Five denominator or population errors have now
    # been shipped in FINDINGS 1z-n/1z-o and caught only afterwards: a
    # compression priced off 549 reports while its "hidden" count came off the
    # 474 the trigger evaluates; an echo rate that omitted a send-only capture;
    # "5 of 35 rows" quoted where the evaluation denominator gives 1.9%; a
    # client-side rate that included SNAP-site samples; and -- the one this
    # section was written for -- a capture COUNT left at 30 after the rate it
    # shares a population with was corrected to 282/7,543. A population fix
    # propagates to EVERY figure drawn from that population, and nothing was
    # checking the others.
    #
    # These are identities and headline figures, not prose. A red check here
    # means either the corpus changed (then update the record) or a number
    # drifted (then fix it) -- the message says which figures to look at.
    tot = collections.Counter()
    pts, percap, trip_caps = set(), collections.Counter(), set()
    for name, lab in sorted(labels.items()):
        pm = meshes.get(lab["fid"])
        if pm is None or meshes.is_stub(lab["fid"]):
            continue
        reports, sends, _e, _f = pc.read_capture(lab["path"])
        for r in reports:
            off = frozenset(t.plane for t in pm.containing(r["x"], r["y"]))
            tot["scored"] += 1
            if not off:
                tot["off-mesh"] += 1
                continue
            tot["on-mesh"] += 1
            if r["plane"] in off:
                tot["agree"] += 1
                continue
            tot["disagree"] += 1
            percap[name] += 1
            pts.add((name, round(r["x"], 3), round(r["y"], 3)))
            if r["plane"] != 0 and off == frozenset({0}):
                tot["N->0"] += 1
            elif r["plane"] == 0 and 0 not in off:
                tot["0->N"] += 1
            else:
                tot["dir-other"] += 1
        for s in sends:
            off = frozenset(t.plane for t in pm.containing(s["x"], s["y"]))
            if not off:
                continue
            tot["sends-on-mesh"] += 1
            if s["plane"] not in off:
                tot["trips"] += 1
                trip_caps.add(name)

    check(tot["on-mesh"] == tot["agree"] + tot["disagree"],
          "IDENTITY: on-mesh == AGREE + DISAGREE",
          f"{tot['on-mesh']} vs {tot['agree']} + {tot['disagree']}")
    check(tot["scored"] == tot["on-mesh"] + tot["off-mesh"],
          "IDENTITY: scored == on-mesh + off-mesh",
          f"{tot['scored']} vs {tot['on-mesh']} + {tot['off-mesh']}")
    check(tot["disagree"] == tot["N->0"] + tot["0->N"] + tot["dir-other"],
          "IDENTITY: the direction classes partition DISAGREE",
          f"{tot['disagree']} vs {tot['N->0']}/{tot['0->N']}/"
          f"{tot['dir-other']} -- if these stop summing, one class is being "
          f"double-counted or dropped")

    PUBLISHED = [
        ("scored reports", 11754, tot["scored"], "1z-n.2"),
        ("off-mesh", 670, tot["off-mesh"], "1z-n.2"),
        ("DISAGREE", 259, tot["disagree"], "1z-n.2 / 1z-n.3"),
        ("distinct disagreeing points", 123, len(pts), "1z-n.6"),
        ("captures carrying a disagreement", 17, len(percap), "1z-n.6"),
        ("direction N->0", 208, tot["N->0"], "1z-n.2"),
        ("direction 0->N", 51, tot["0->N"], "1z-n.2"),
        ("echo denominator (on-mesh sends)", 7543, tot["sends-on-mesh"],
         "1z-n.5 / 1z-o.11"),
        ("echo trips", 282, tot["trips"], "1z-n.5 / 1z-o.11"),
        ("captures with an echo trip", 31, len(trip_caps), "1z-o.11"),
    ]
    for what, pub, got, where in PUBLISHED:
        check(pub == got,
              f"FINDINGS {where} still holds: {what} == {pub}",
              f"record says {pub}, corpus gives {got}. A population fix "
              f"propagates to every figure drawn from it -- if you just "
              f"changed how captures or reports are selected, check the "
              f"OTHER figures in {where} too.")

    # ---- §7 THE PROSE FIGURES, TIED TO THE CORPUS --------------------
    # §6 pins totals and identities. It would NOT have caught the eight
    # defects a denominator audit found in 1z-n, because every one lived in a
    # SENTENCE: a ratio quoted mid-paragraph, a histogram in a table, a claim
    # about what one trace shows. Prose is where the errors survive, so this
    # section re-derives each figure from the corpus and asserts THE DOCUMENT
    # SAYS IT -- the discipline `test_probedoc.py` applies to PROBE-GATEFIRE.
    # Red here means the corpus moved (update the prose) or the prose is
    # wrong (fix it); the message says which value the corpus gives.
    if not os.path.isfile(FINDINGS):
        LEDGER.skip("prose figures", f"no {FINDINGS}")
    else:
        doc = open(FINDINGS, encoding="utf-8", errors="replace").read()

        # (a) the stub mesh's off-mesh rate -- read 69% for a week, is 61.3%
        stub_rep = stub_off = 0
        for name, lab in sorted(labels.items()):
            pm = meshes.get(lab["fid"])
            if pm is None or not meshes.is_stub(lab["fid"]):
                continue
            if (lab["fid"] & 0x7FFFFFFF) != 0x287D3:
                continue
            reports, _s, _e, _f = pc.read_capture(lab["path"])
            for r in reports:
                stub_rep += 1
                if not pm.containing(r["x"], r["y"]):
                    stub_off += 1
        if stub_rep:
            pctv = f"{100.0 * stub_off / stub_rep:.1f}"
            check(f"{pctv}% OFF-MESH" in doc and
                  f"{stub_off} of {stub_rep}" in doc,
                  "the stub mesh's OFF-MESH rate in the prose matches the "
                  "corpus",
                  f"corpus gives {stub_off} of {stub_rep} = {pctv}%; the "
                  f"document must say both. It said 69% until 2026-08-30.")

        # (b) the harness cross-check count
        check(f"{cross['harness AGREES']} of {cross['harness AGREES']} agree"
              in doc,
              "the harness-agreement count in the prose matches the corpus",
              f"corpus gives {cross['harness AGREES']}; this read 172 after "
              f"the send-only fix admitted a capture")

        # (c) visited stacking, on the NON-STUB on-mesh denominator
        stacked = sum(1 for _ in ())  # placeholder, computed below
        stacked = 0
        for name, lab in sorted(labels.items()):
            pm = meshes.get(lab["fid"])
            if pm is None or meshes.is_stub(lab["fid"]):
                continue
            reports, _s, _e, _f = pc.read_capture(lab["path"])
            for r in reports:
                if len(frozenset(t.plane
                                 for t in pm.containing(r["x"], r["y"]))) >= 2:
                    stacked += 1
        want = f"{stacked}/{tot['on-mesh']:,} = 1.75%"
        check(want in doc or f"{stacked}/{tot['on-mesh']:,}" in doc,
              "visited stacking is quoted on the NON-STUB on-mesh denominator",
              f"corpus gives {stacked}/{tot['on-mesh']} ; the document said "
              f"194/11,208 until 2026-08-30, dividing by a population the "
              f"headline excludes")

        # (d) the distance histogram's own arithmetic. Recomputing nearest-edge
        # distance over every disagreement is far too slow for the suite -- but
        # the failure was a STALE POPULATION, and that is catchable for free:
        # the four buckets must sum to DISAGREE. The bad version summed to 237.
        m7 = re.search(r"Run over all \*\*(\d+)\*\* disagreements it puts\s*\n?"
                       r"\*\*(\d+) in 50", doc)
        buckets = re.findall(r"\*\*(\d+) clearly stale \(>1,000 u\) and (\d+) "
                             r"clearly underfoot", doc)
        m8 = re.search(r"and 100 in 200", doc)
        if m7 and buckets and m8:
            total, b50 = int(m7.group(1)), int(m7.group(2))
            stale, foot = int(buckets[0][0]), int(buckets[0][1])
            check(total == tot["disagree"],
                  "the distance histogram is scored on the CURRENT corpus",
                  f"it says {total} disagreements, the corpus has "
                  f"{tot['disagree']} -- it was stuck on a pre-fix 237 "
                  f"until 2026-08-30")
            check(b50 + 100 + stale + foot == total,
                  "and its four buckets SUM to that total",
                  f"{foot} + {b50} + 100 + {stale} = "
                  f"{foot + b50 + 100 + stale}, claimed {total}")
        else:
            LEDGER.skip("distance histogram",
                        "the histogram's sentence shape changed; re-anchor it")

        # (e) the bimodality population. SCOREABLE, not "carries reports":
        # 40 captures sit on a stub or unbound mesh and CANNOT disagree, and
        # folding them into the clean pile is what made two earlier drafts of
        # this histogram sum to 155 and then 157. Zero exposure is not a null.
        scoreable = [n for n, lb in labels.items()
                     if meshes.get(lb["fid"]) is not None
                     and not meshes.is_stub(lb["fid"])
                     and pc.read_capture(lb["path"])[0]]
        clean = [n for n in scoreable if not percap.get(n)]
        check(0 < len(clean) < len(scoreable),
              "there ARE both clean and disagreeing scoreable captures",
              f"scoreable {len(scoreable)}, clean {len(clean)} -- with either "
              f"side empty the bucket check below would judge nothing")
        mb = re.findall(r"\*\*(\d+) has zero on-mesh reports, (\d+) have "
                        r"1[–-]4, (\d+) have 5[–-]19, (\d+) have\s*\n?"
                        r"20[–-]99, (\d+) have", doc)
        if mb:
            parts = [int(x) for x in mb[0]]
            check(sum(parts) == len(clean),
                  "the bimodality buckets SUM to the CLEAN SCOREABLE count",
                  f"buckets {parts} sum to {sum(parts)}; the corpus has "
                  f"{len(clean)} clean scoreable captures of "
                  f"{len(scoreable)}. Drafts summing to 155 and 157 were "
                  f"counting unscoreable captures as clean.")
            check(f"17 of {len(scoreable)}" in doc,
                  "and the headline rate uses the SCOREABLE denominator",
                  f"the document must say 17 of {len(scoreable)}, not 17 of "
                  f"174 -- 40 captures cannot disagree at all")
        else:
            LEDGER.skip("bimodality buckets",
                        "the bucket sentence shape changed; re-anchor it")

    return LEDGER.verdict()


def _offers(pm, s):
    return sorted({t.plane for t in pm.containing(s["x"], s["y"])})


def _version_map_id(path):
    import json
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"version"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "version":
                return r.get("map_id")
    return None


if __name__ == "__main__":
    sys.exit(main())
