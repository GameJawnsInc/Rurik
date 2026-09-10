r"""The parked copy, asked of retail: after a grant the client's body SLID PAST, does ArenaNet's
copy of the player advance before the client's next report -- or park on the grant as ours does?

    python studies/movecode/review/parkedcopy.py

THE QUESTION (MOVECODE-1z-dh, registered in FINDINGS 1z-dd.8). RUN-1zDB leg 4: our clip cut a
lead at 6 u (the mesh edge), world-0 walked to the grant and parked, the body slid 93 u along the
wall and the client then sent nothing for 14.6 s; the follow parked the Hatcher 74 u from the copy
= 161 u from the body. The grant matches retail's measured rule (the first split vertex, 1z-ce),
so the divergence is not the grant. What retail's COPY does in the silence after a client slide
decides the lever: if it advances past the grant before the next report, retail's server
integrates the slide and server-side slide integration is the fix; if it parks, retail's copy
parks as ours does and the class is the client's own silence.

TWO INSTRUMENTS, both on the live corpus, both reading things retail sends:
  (1) a non-player agent's 0x002A naming the player carries the server's copy of the player at
      the send (NPCTRACK F16, chasercensus.py). In the window between a grant the body slid past
      and the client's next report, is any such point BEYOND the grant along the body's travel?
  (2) 0x0029 grants to the player that answer NO report -- the nearest preceding report older
      than 0.6 s. A server that acts in the client's silence re-grants on its own tick.

PREDICTION, stated before the run: retail's copy LAGS and never leads (1z-cq.3: 0 of 44 follows
past 288 u/s x the report's age), so (1) reads ~0 advanced of N and (2) reads ~0 unprompted
grants. Fewer than 5 slid-past windows with a follow inside is NOT FOUND for (1).

Standard library only; livewire's connection walk; the player named by whose 0x0029 grants answer
the c2s headings (swingcensus._player_of).
"""
import bisect
import collections
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", HERE):
    sys.path.insert(0, os.path.join(ROOT, _sub))

import swingcensus as SC          # noqa: E402

C2S_HEADING, C2S_STOP = 0x3D, 0x47
S2C_LEG, S2C_FOLLOW = 0x29, 0x2A
SLID_MARGIN = 20.0       # u the body travelled beyond the grant to count as "slid past"
ADVANCE_TOL = 10.0       # u beyond the grant, along the travel, for a follow point to count as advanced
SHORT_GRANT = 600.0      # a wall-cut grant; the full chord is ~766
UNPROMPTED_S = 0.6       # a grant with no report this recent answers nothing


def _pt(v):
    return (float(v[0]), float(v[1]))


def run(verbose=True):
    import livewire
    windows, honoured, unprompted, conns = [], [], [], 0
    n_grants = n_follows = 0
    for capdir, cf in livewire.live_connections():
        try:
            _c, merged, ok = livewire.decode_conn(capdir, cf)
        except Exception:                                   # noqa: BLE001
            continue
        if not ok or not merged:
            continue
        conns += 1
        pid = SC._player_of(merged)
        if pid is None:
            continue
        R, G, F = [], [], []
        for (t, dr, op, v) in merged:
            if dr == "c2s" and op == C2S_HEADING and len(v) >= 2:
                R.append((t, _pt(v[1]), "h"))
            elif dr == "c2s" and op == C2S_STOP and len(v) >= 2:
                R.append((t, _pt(v[1]), "s"))
            elif dr == "s2c" and op == S2C_LEG and len(v) >= 3 and v[1] == pid:
                G.append((t, _pt(v[2])))
            elif (dr == "s2c" and op == S2C_FOLLOW and len(v) >= 6
                  and v[1] != pid and v[5] == pid):
                F.append((t, _pt(v[2]), v[1]))
        R.sort(); G.sort(); F.sort()
        n_grants += len(G); n_follows += len(F)
        gt = [g[0] for g in G]
        ft = [f[0] for f in F]
        rt = [r[0] for r in R]
        # (2) unprompted grants: no report within UNPROMPTED_S before the grant
        for t, p in G:
            i = bisect.bisect_right(rt, t)
            age = (t - rt[i - 1]) if i > 0 else None
            if age is None or age > UNPROMPTED_S:
                unprompted.append((os.path.basename(capdir), cf, round(t, 3),
                                   None if age is None else round(age, 2)))
        # (1) windows: a heading report answered by a grant, then the next report
        for i in range(len(R) - 1):
            t1, r1, k1 = R[i]
            if k1 != "h":
                continue
            t2, r2, _k2 = R[i + 1]
            dt = t2 - t1
            if not (0.05 < dt <= 3.0):
                continue
            j = bisect.bisect_left(gt, t1 - 0.05)
            if not (j < len(G) and G[j][0] <= t1 + 0.4):
                continue
            tg, g = G[j]
            Lg = math.hypot(g[0] - r1[0], g[1] - r1[1])
            Lb = math.hypot(r2[0] - r1[0], r2[1] - r1[1])
            if Lb < 5.0:
                continue
            u = ((r2[0] - r1[0]) / Lb, (r2[1] - r1[1]) / Lb)
            sg = (g[0] - r1[0]) * u[0] + (g[1] - r1[1]) * u[1]
            fi, fj = bisect.bisect_right(ft, tg + 0.02), bisect.bisect_left(ft, t2)
            pts = [(F[k][0], F[k][1]) for k in range(fi, fj)]
            rec = {"cap": os.path.basename(capdir), "conn": cf, "t": round(t1, 3),
                   "Lg": round(Lg, 1), "Lb": round(Lb, 1), "dt": round(dt, 2),
                   "follows": len(pts), "sf": [], "adv": 0}
            for _tf, f in pts:
                sf = (f[0] - r1[0]) * u[0] + (f[1] - r1[1]) * u[1]
                rec["sf"].append(round(sf - sg, 1))
                if sf > sg + ADVANCE_TOL:
                    rec["adv"] += 1
            if Lg < SHORT_GRANT and Lb > Lg + SLID_MARGIN:
                windows.append(rec)
            elif Lb <= Lg + 5.0:
                honoured.append(rec)
    if verbose:
        print(f"retail, {conns} connections: grants to the player {n_grants}, "
              f"follows naming the player {n_follows}")
        exp = [w for w in windows if w["follows"]]
        print(f"\n(1) SLID-PAST windows (short grant, body travelled > grant + {SLID_MARGIN:.0f} u): "
              f"{len(windows)}, with a follow inside: {len(exp)}")
        adv = sum(1 for w in exp if w["adv"])
        allsf = [s for w in exp for s in w["sf"]]
        print(f"    windows where a follow point ADVANCED past the grant (> {ADVANCE_TOL:.0f} u along the travel): "
              f"{adv} of {len(exp)}")
        if allsf:
            print(f"    follow point minus grant, along the travel: n={len(allsf)} p50 {st.median(allsf):.1f} u, "
                  f"max {max(allsf):.1f}, min {min(allsf):.1f}")
        for w in sorted(exp, key=lambda w: -w["Lb"] + w["Lg"])[:12]:
            print("     ", w)
        hexp = [w for w in honoured if w["follows"]]
        hadv = sum(1 for w in hexp if w["adv"])
        print(f"\n    CONTROL, grants the body honoured (travel <= grant): {len(honoured)}, with a follow: "
              f"{len(hexp)}, advanced past the grant: {hadv}")
        print(f"\n(2) UNPROMPTED grants (no report within {UNPROMPTED_S} s before): {len(unprompted)} of {n_grants}")
        for u in unprompted[:10]:
            print("     ", u)
    return windows, honoured, unprompted, conns


if __name__ == "__main__" and "--silences" not in sys.argv:
    run()


# ------------------------------------------------------------ refinements
C2S_MOVE_OPS = {0x3D, 0x3E, 0x3F, 0x40, 0x47}   # heading, click, and the family's other orders


def refined(verbose=True):
    """(2) with EVERY movement order excluded, plus the surviving grants' geometry; and (3) the
    client's own silence after a short grant it slid past, which needs no follow to read."""
    import livewire
    unprompted, silences_short, silences_full, conns = [], [], [], 0
    n_grants = 0
    for capdir, cf in livewire.live_connections():
        try:
            _c, merged, ok = livewire.decode_conn(capdir, cf)
        except Exception:                                   # noqa: BLE001
            continue
        if not ok or not merged:
            continue
        conns += 1
        pid = SC._player_of(merged)
        if pid is None:
            continue
        M, R, G = [], [], []
        for (t, dr, op, v) in merged:
            if dr == "c2s" and op in C2S_MOVE_OPS:
                M.append(t)
                if op in (C2S_HEADING, C2S_STOP) and len(v) >= 2:
                    R.append((t, _pt(v[1]), "h" if op == C2S_HEADING else "s"))
            elif dr == "s2c" and op == S2C_LEG and len(v) >= 3 and v[1] == pid:
                G.append((t, _pt(v[2])))
        M.sort(); R.sort(); G.sort()
        n_grants += len(G)
        rt = [r[0] for r in R]
        for k, (t, p) in enumerate(G):
            i = bisect.bisect_right(M, t)
            age = (t - M[i - 1]) if i > 0 else None
            if age is not None and age <= UNPROMPTED_S:
                continue
            ri = bisect.bisect_right(rt, t)
            last = R[ri - 1] if ri > 0 else None
            d_last = math.hypot(p[0] - last[1][0], p[1] - last[1][1]) if last else None
            prev = G[k - 1] if k > 0 else None
            cont = None
            if prev is not None and last is not None:
                # is this point further along the PREVIOUS grant's direction from the last report?
                vx, vy = prev[1][0] - last[1][0], prev[1][1] - last[1][1]
                m = math.hypot(vx, vy)
                if m > 1.0:
                    cont = round(((p[0] - last[1][0]) * vx + (p[1] - last[1][1]) * vy) / m - m, 1)
            unprompted.append((os.path.basename(capdir), round(t, 3),
                               None if age is None else round(age, 2),
                               None if d_last is None else round(d_last, 1), cont))
        # (3) silence after a grant: the gap to the next report of either kind
        gt = [g[0] for g in G]
        for i in range(len(R) - 1):
            t1, r1, k1 = R[i]
            if k1 != "h":
                continue
            j = bisect.bisect_left(gt, t1 - 0.05)
            if not (j < len(G) and G[j][0] <= t1 + 0.4):
                continue
            g = G[j][1]
            Lg = math.hypot(g[0] - r1[0], g[1] - r1[1])
            t2, r2, _ = R[i + 1]
            Lb = math.hypot(r2[0] - r1[0], r2[1] - r1[1])
            gap = t2 - t1
            if Lg < SHORT_GRANT and Lb > Lg + SLID_MARGIN:
                silences_short.append(gap)
            elif Lg >= SHORT_GRANT:
                silences_full.append(gap)
    if verbose:
        print(f"\n(2, refined) grants answering NO movement order within {UNPROMPTED_S} s "
              f"(heading, click, stop, 0x3F, 0x40 all excluded): {len(unprompted)} of {n_grants}")
        dl = [u[3] for u in unprompted if u[3] is not None]
        ct = [u[4] for u in unprompted if u[4] is not None]
        if dl:
            print(f"    distance from the last report: p50 {st.median(dl):.1f} u, max {max(dl):.1f}")
        if ct:
            fwd = sum(1 for c in ct if c > 10.0)
            print(f"    beyond the PREVIOUS grant along its own direction (> 10 u): {fwd} of {len(ct)}; "
                  f"p50 {st.median(ct):.1f} u")
        for u in unprompted[:8]:
            print("     ", u)
        for name, s in (("after a SHORT grant the body slid past", silences_short),
                        ("after a FULL chord", silences_full)):
            if s:
                q = sorted(s)
                print(f"\n(3) next-report gap {name}: n={len(q)} p50 {st.median(q):.2f} s, "
                      f"p90 {q[len(q) * 9 // 10]:.2f}, > 3 s: {sum(1 for x in s if x > 3.0)}")
    return unprompted, silences_short, silences_full




# ------------------------------------------------- the corrected instrument
QUIET_OPS = {0x0009, 0x00C1}    # the latency reply and a target select: the client said nothing about moving


def silences(verbose=True):
    """(2), done right, and the split that answers 1z-dd.8.

    TWO FALSE STARTS, kept as the record: `refined()` above defined a silence as "no
    heading/click/stop inside" and found 40 of 81 windows with grants inside -- but a
    0x0026 ATTACK or a 0x0027 interact hands the walk to the SERVER (the approach, the
    follow), the client is silent BY DESIGN, and the 0x0029s inside are the corridor's own
    legs (NPCTRACK F16). A true silence is the client sending NOTHING but heartbeats and
    target selects. Then: split each silence by the angle between the held heading and the
    body's actual travel to its next report -- STRAIGHT (< 10 deg) is a walk the grant
    under-covered, SLIDE (> 20 deg) is RUN-1zDB leg 4's class -- and read, per inside
    grant, its instant against the copy's arrival at the previous grant (Lg / 288 u/s).

    MEASURED 2026-09-10 (61 connections): 236 slid-past windows; 71 true silences, ALL
    straight, 0 slide-class; 46 of the 71 carry unprompted grants at p50 +0.09 s after the
    copy's arrival -- the previous point restated plus the next ~768 u chord along the held
    heading. Retail's server re-grants when its copy reaches the end of a grant; ours parks.
    """
    import livewire
    rows = []
    n_windows = 0
    for capdir, cf in livewire.live_connections():
        try:
            _c, merged, ok = livewire.decode_conn(capdir, cf)
        except Exception:                                   # noqa: BLE001
            continue
        if not ok or not merged:
            continue
        pid = SC._player_of(merged)
        if pid is None:
            continue
        R, G, C, F = [], [], [], []
        for (t, dr, op, v) in merged:
            if dr == "c2s":
                if op not in QUIET_OPS:
                    C.append(t)
                if op == C2S_HEADING and len(v) >= 4:
                    R.append((t, _pt(v[1]), _pt(v[3]), "h"))
                elif op == C2S_STOP and len(v) >= 2:
                    R.append((t, _pt(v[1]), None, "s"))
            elif dr == "s2c" and op == S2C_LEG and len(v) >= 3 and v[1] == pid:
                G.append((t, _pt(v[2])))
            elif (dr == "s2c" and op == S2C_FOLLOW and len(v) >= 6
                  and v[1] != pid and v[5] == pid):
                F.append((t, _pt(v[2])))
        R.sort(key=lambda r: r[0]); G.sort(); C.sort(); F.sort()
        gt = [g[0] for g in G]; ft = [f[0] for f in F]
        for i in range(len(R) - 1):
            t1, r1, hd, k1 = R[i]
            if k1 != "h" or hd is None:
                continue
            j = bisect.bisect_left(gt, t1 - 0.05)
            if not (j < len(G) and G[j][0] <= t1 + 0.4):
                continue
            tg, g = G[j]
            t2, r2, _hd2, _k2 = R[i + 1]
            Lg = math.hypot(g[0] - r1[0], g[1] - r1[1])
            Lb = math.hypot(r2[0] - r1[0], r2[1] - r1[1])
            if not (Lg < SHORT_GRANT and Lb > Lg + SLID_MARGIN):
                continue
            n_windows += 1
            gap = t2 - t1
            if gap <= 1.0:
                continue
            c0, c1 = bisect.bisect_right(C, t1 + 0.05), bisect.bisect_left(C, t2 - 0.01)
            if c1 > c0:
                continue
            hm = math.hypot(*hd)
            cosang = (hd[0] * (r2[0] - r1[0]) + hd[1] * (r2[1] - r1[1])) / (hm * Lb)
            ang = math.degrees(math.acos(max(-1.0, min(1.0, cosang))))
            k0, k1i = bisect.bisect_right(gt, tg + 0.3), bisect.bisect_left(gt, t2)
            inside = [(G[k][0] - t1, math.hypot(G[k][1][0] - r1[0], G[k][1][1] - r1[1]))
                      for k in range(k0, k1i)]
            f0, f1 = bisect.bisect_right(ft, tg + 0.02), bisect.bisect_left(ft, t2)
            rows.append({"cap": os.path.basename(capdir), "t": round(t1, 2), "gap": round(gap, 2),
                         "Lg": round(Lg, 1), "Lb": round(Lb, 1), "angle": round(ang, 1),
                         "inside": [(round(a, 2), round(d, 1)) for a, d in inside],
                         "arrive": round(Lg / 288.0, 2), "follows": f1 - f0})
    if verbose:
        print(f"slid-past windows: {n_windows}; TRUE silences (> 1 s, nothing from the client but "
              f"0x0009/0x00C1): {len(rows)}")
        for name, sel in (("STRAIGHT (< 10 deg)", [r for r in rows if r["angle"] < 10.0]),
                          ("SLIDE (> 20 deg)", [r for r in rows if r["angle"] > 20.0]),
                          ("between", [r for r in rows if 10.0 <= r["angle"] <= 20.0])):
            wg = [r for r in sel if r["inside"]]
            print(f"  {name}: {len(sel)}, with an unprompted grant inside: {len(wg)}, "
                  f"with an NPC follow inside: {sum(1 for r in sel if r['follows'])}")
            if wg:
                lag = [r["inside"][0][0] - r["arrive"] for r in wg]
                print(f"     first inside grant minus the copy's arrival: p50 {st.median(lag):+.2f} s "
                      f"(min {min(lag):+.2f}, max {max(lag):+.2f})")
                pairs = sum(1 for r in wg if len(r["inside"]) >= 2
                            and abs(r["inside"][1][0] - r["inside"][0][0]) < 0.1)
                print(f"     grants arriving as a same-instant PAIR (restated point + next chord): {pairs} of {len(wg)}")
    return rows


if __name__ == "__main__" and "--silences" in sys.argv:
    silences()
