#!/usr/bin/env python3
"""The LEASH RETURN and the CASTER OPENING, read off the aggro tapes for the server to
copy (monsterai §11 N9 / N4 / §12.8; DESKWORK-D8 steps 3 and 4).

    python studies/monsterai/review/leashreturn.py                    # defs 1397, 1432, 4440
    python studies/monsterai/review/leashreturn.py --defs 1397        # one definition
    python studies/monsterai/review/leashreturn.py --since 20260915   # captures from a stamp

Prints, per engagement of the player by a listed definition, everything noticeradius.py
summarises into one row of N9's table, at the resolution the server needs:

  ANCHOR    the 0x0020 create position (the stander's home), and the notice position.
  CHASE     every order the hostile took from the notice to its give-up, with each point's
            distance from the anchor and from the player's newest self-report; every
            combat word the hostile sourced meanwhile (attack_started [4], the damage words
            [16]/[17], a skill activation 0x00A0 [60|50]) -- and for each attack_started the
            order before it and the order after it, with their gaps, so the swing's place in
            the chase (after a halt? between two follows?) is read, not assumed.
  GIVE-UP   the last chase order: its time from the notice, its point's distance from the
            anchor and from the notice position, and the PLAYER's distance from the anchor
            at that instant (the newest self-report).
  RETURN    every 0x002B and 0x0029 after the give-up until the hostile stands: the speed
            fraction, each leg's gap from the previous leg and its point's distance from
            the anchor; the last leg's endpoint distance from the anchor is the return's
            end. HOME when that is within HOME_RADIUS (noticeradius's own bound).
  OPENING   the burst before the first act (orders with gaps), the first act's kind and
            skill id, and the hostile's distance from the player at the first act
            (OBSERVED when the hostile's position is a wire number, else RECON).

Every position rule is noticeradius.py's (imported, not copied): a hostile position is a
wire number only when nothing is in flight; a dead-reckoned one prints as RECON. Read-only.
Stdlib only. Needs the vault's live captures.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/schema",
            "studies/npctrack/review", "studies/monsterai/review"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import chasercensus                                            # noqa: E402
import noticeradius as nr                                      # noqa: E402

DEFAULT_DEFS = (1397, 1432, 4440)
GV_SKILL_ACTIVATED = 60
GV_ATTACK_SKILL_ACTIVATED = 50
STAND_GAP = 6.0        # s without an order after the last return leg: the hostile stands
OP_NAMES = {nr.S2C_LEG: "leg", nr.S2C_FOLLOW: "follow", nr.S2C_SPEED: "speed",
            nr.S2C_FACING: "facing", nr.S2C_HALT: "halt", nr.S2C_MOVE_DIR: "dir"}


def d(a, b):
    return nr.d(a, b)


def order_words(stream, t_lo, t_hi):
    """[(t, op, point-or-None, speed-or-None)] the hostile's own orders in [t_lo, t_hi]."""
    out = []
    for (t, op, v) in stream:
        if t < t_lo or t > t_hi or op not in nr.ORDER_OPS:
            continue
        pt = tuple(v[2]) if op in (nr.S2C_LEG, nr.S2C_FOLLOW) and len(v) >= 3 else None
        sp = float(v[2]) if op == nr.S2C_SPEED and len(v) >= 3 else None
        out.append((t, op, pt, sp))
    return out


def combat_words(merged, pid, a, t_lo, t_hi):
    """[(t, kind, skill)] the hostile SOURCED on the player in [t_lo, t_hi]: attack_started,
    damage, or a skill activation (60 spell / 50 attack skill, the skill id in field 4)."""
    out = []
    for (t, dr, op, v) in merged:
        if t < t_lo or t > t_hi or dr != "s2c":
            continue
        if op in (nr.S2C_GV_TARGET, nr.S2C_GV_FLOAT_TARGET) and len(v) >= 4:
            gv = v[1]
            if gv in nr.GV_COMBAT and {v[2], v[3]} == {pid, a} and nr.combat_source(v) == a:
                out.append((t, "attack_started" if gv == nr.GV_ATTACK_STARTED else "damage", None))
            elif gv in (GV_SKILL_ACTIVATED, GV_ATTACK_SKILL_ACTIVATED) and v[2] == a and len(v) >= 5:
                out.append((t, "spell" if gv == GV_SKILL_ACTIVATED else "attack-skill", v[4]))
    return sorted(out)


def fmt_pt(p):
    return f"({p[0]:.0f},{p[1]:.0f})" if p else "--"


def analyse(stamp, gf, merged, defs):
    pid, _c61 = chasercensus.player_of(merged)
    if pid is None:
        return
    creates = nr.creates_of(merged)
    reports = nr.player_reports(merged)
    npc_ids = {aid for aid, cs in creates.items() if any(c[2] == nr.KIND_NPC for c in cs)}
    for a in sorted(npc_ids):
        stream = nr.agent_stream(merged, a)
        acts = nr.hostile_acts(merged, stream, pid, a)
        if not acts:
            continue
        for eng in nr.engagements(acts):
            c = nr.create_before(creates, a, eng["t_first"])
            if c is None or c[2] != nr.KIND_NPC or c[4] not in defs:
                continue
            t_c, anchor = c[0], c[1]
            t_n = max(nr.burst_start(stream, eng["t_first"]), t_c)
            track = nr.HostileTrack(stream, c)
            npos, nobs, _m, _n = track.pos_at(t_n)
            print(f"\n=== {stamp} {gf}  agent {a}  def {c[4]}  token {c[3]}  base {c[5]:.0f} u/s x {c[6]:.2f} ===")
            print(f"ANCHOR  create at {t_c:.1f} s {fmt_pt(anchor)}; notice at {t_n:.1f} s, hostile "
                  f"{fmt_pt(npos)} {'OBSERVED' if nobs else 'RECON'} ({d(npos, anchor):.0f} u from the anchor)")
            # ---- the opening: the burst before the first act
            first_t = eng["t_first"]
            burst = order_words(stream, t_n, first_t)
            words = combat_words(merged, pid, a, t_n, first_t + 0.05)
            r = nr.report_at(reports, first_t)
            hpos, hobs, _m2, _n2 = track.pos_at(first_t)
            first = words[0] if words else (first_t, eng["first_kind"], None)
            print(f"OPENING first act at {first_t:.1f} s: {first[1]}"
                  + (f" skill {first[2]}" if first[2] is not None else "")
                  + f"; burst before it ({first_t - t_n:.1f} s): "
                  + " + ".join(f"{OP_NAMES[op]}{'=%.2f' % sp if sp is not None else ''}@{t - t_n:.1f}s"
                               for (t, op, pt, sp) in burst)
                  + (f"; hostile {d(hpos, r[1]):.0f} u from the player's report ({first_t - r[0]:.1f} s old)"
                     f" {'OBSERVED' if hobs else 'RECON'}" if r else ""))
            # ---- the chase
            prof = nr.chase_profile(stream, eng, reports, track, t_n, c)
            if not prof:
                print("CHASE   none (no follow and no leg toward the player)")
                continue
            t_give = prof["t_give"]
            orders = order_words(stream, t_n, t_give)
            print(f"CHASE   {prof['n_follows']} follows + {prof['n_legs']} legs, {prof['chase_secs']:.1f} s "
                  f"({prof['duration']:.1f} s from the notice); gave up on a {prof['give_kind']} "
                  f"{prof['leash']:.0f} u from the notice position{'' if prof['leash_obs'] else ' (recon)'}")
            for (t, op, pt, sp) in orders:
                r = nr.report_at(reports, t)
                line = f"        {t - t_n:6.1f} s  {OP_NAMES[op]:6}"
                if pt:
                    line += f" {fmt_pt(pt):16} {d(pt, anchor):5.0f} u from anchor"
                    if r:
                        line += f", {d(pt, r[1]):4.0f} u from the player's report ({t - r[0]:.1f} s old)"
                if sp is not None:
                    line += f" = {sp:.2f}"
                print(line)
            words = combat_words(merged, pid, a, t_n, t_give)
            for (t, kind, sk) in words:
                before = [o for o in orders if o[0] <= t]
                after = [o for o in orders if o[0] > t]
                b = before[-1] if before else None
                n = after[0] if after else None
                print(f"        {t - t_n:6.1f} s  {kind}{' skill %d' % sk if sk is not None else ''}"
                      + (f" -- {t - b[0]:.2f} s after a {OP_NAMES[b[1]]}" if b else " -- no order before it")
                      + (f", {n[0] - t:.2f} s before a {OP_NAMES[n[1]]}" if n else ", no order after it"))
            r = nr.report_at(reports, t_give)
            last_pt = [o for o in orders if o[2]][-1][2]
            print(f"GIVE-UP {t_give - t_n:.1f} s after the notice: point {d(last_pt, anchor):.0f} u from the anchor, "
                  f"{d(last_pt, npos):.0f} u from the notice position"
                  + (f"; the player's report {d(r[1], anchor):.0f} u from the anchor ({t_give - r[0]:.1f} s old)" if r else ""))
            # ---- the return
            ret = order_words(stream, t_give + 1e-6, t_give + 120.0)
            legs, prev_t, end_pt = [], None, None
            print("RETURN")
            for (t, op, pt, sp) in ret:
                if legs and t - prev_t > STAND_GAP:
                    break
                if op == nr.S2C_SPEED:
                    print(f"        {t - t_give:6.1f} s after the give-up  speed = {sp:.2f} ({c[5] * sp:.0f} u/s)")
                elif op == nr.S2C_LEG:
                    gap = f"{t - prev_t:.2f} s after the previous leg" if prev_t is not None else "first leg"
                    print(f"        {t - t_give:6.1f} s after the give-up  leg -> {fmt_pt(pt):16} "
                          f"{d(pt, anchor):5.0f} u from the anchor  ({gap})")
                    legs.append((t, pt))
                    end_pt = pt
                elif op == nr.S2C_FOLLOW:
                    print(f"        {t - t_give:6.1f} s after the give-up  FOLLOW -> {fmt_pt(pt)} (a re-notice?)")
                    break
                else:
                    print(f"        {t - t_give:6.1f} s after the give-up  {OP_NAMES[op]}")
                prev_t = t
            if legs:
                gaps = [legs[i][0] - legs[i - 1][0] for i in range(1, len(legs))]
                print(f"        {len(legs)} legs over {legs[-1][0] - legs[0][0]:.1f} s; gaps "
                      + (f"min {min(gaps):.2f} p50 {nr.q(gaps, .5):.2f} max {max(gaps):.2f} s" if gaps else "--")
                      + f"; END {d(end_pt, anchor):.0f} u from the anchor -> "
                      + ("HOME" if d(end_pt, anchor) <= nr.HOME_RADIUS else "not home"))
            else:
                print("        no legs")


def main(argv):
    import livewire
    since = argv[argv.index("--since") + 1] if "--since" in argv else None
    defs = (tuple(int(x) for x in argv[argv.index("--defs") + 1].split(","))
            if "--defs" in argv else DEFAULT_DEFS)
    seen = 0
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        if since and stamp < since:
            continue
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        if not ok or not merged:
            continue
        seen += 1
        analyse(stamp, gf, merged, defs)
    if not seen:
        print("no decodable live connections -- nothing observed")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
