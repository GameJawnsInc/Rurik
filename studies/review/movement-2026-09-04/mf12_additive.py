"""M-F12 re-derivation (READ-ONLY): re-run the 1z-s.3 retrodiction with the
guard at HEAD and add the class the record never states -- the ADDITIVE arm's
own share: a warp whose window held a REPIN_DUE sample (the only thing the
shipped arm can act on), split by whether pre_emit also VETOed.

Copies replay_policy's loop verbatim (agtrack_replay.py:367-500) because that
function returns per-step classes but not the timeline.  Prints only.
"""
import os, sys, json, glob
T = r"C:/gd/Rurik/toolkit"
for p in (T, os.path.join(T, "clientscan"), os.path.join(T, "authsrv"),
          os.path.join(T, "mapdata")):
    sys.path.insert(0, p)
import agtrack_replay as ar
import agtrack_guard as ag
import vaultpath

def run(path, mesh):
    events, fid = ar.load_events(path)
    reports, _w, _s = ar.movesync.load_wire_reports(path)
    refused_ts = set()
    pc_reports, _s, _e, _f = ar.pc.read_capture(path)
    for r in pc_reports:
        if r.get("accepted") is False:
            refused_ts.add(round(r["t"], 3))
    guard = ag.AgTrackGuard(mesh=mesh)
    timeline = []
    seeded = False
    last_t = None
    n_grants = n_veto = 0
    for t, kind, data in events:
        if last_t is not None:
            step = last_t + ar.TICK_MS / 1000.0
            while step <= t:
                guard.tick(step)
                code, why = guard.repin_state(step)
                timeline.append((step, code, why, False))
                step += ar.TICK_MS / 1000.0
        if kind == "grant":
            x, y, pa, pb, op = data
            vetoed = False
            if seeded:
                n_grants += 1
                gv = guard.pre_emit(x, y, pa, pb, t)
                if gv.code == ag.VETO:
                    n_veto += 1
                    vetoed = True
                timeline.append((t, gv.repin, gv.why, vetoed))
            guard.on_emit(op, x, y, pa, pb, t)
        elif kind == "setpos":
            x, y, plane = data
            guard.on_emit(0x2C, x, y, plane, None, t)
        elif kind == "speed":
            guard.on_speed(data, t)
        elif kind == "heading":
            x, y, plane, hx, hy, mt = data
            if not seeded:
                guard.on_placement(x, y, plane, t); seeded = True
            guard.on_report(x, y, plane, ("head", round(hx, 1), round(hy, 1), mt),
                            t, accepted=round(t, 3) not in refused_ts)
        elif kind == "stop":
            x, y, plane = data
            if not seeded:
                guard.on_placement(x, y, plane, t); seeded = True
            guard.on_report(x, y, plane, ("stop",), t,
                            accepted=round(t, 3) not in refused_ts)
        elif kind == "click":
            x, y, dp = data
            if seeded:
                guard.on_click(x, y, dp, t)
        last_t = t
    steps = ar.hard_steps(reports)
    out = []
    for (t0, t1, d, p0, p1) in steps:
        lo = t0 - 5.0
        win = [r for r in timeline if lo <= r[0] <= t1]
        veto = any(r[3] for r in win)
        due = any(r[1] == ag.REPIN_DUE for r in win)
        blocked = any(r[1] == ag.REPIN_BLOCKED for r in win)
        if veto: rec = "pre-empted-veto"
        elif due: rec = "pre-empted-repin"
        elif blocked: rec = "blocked"
        else: rec = "unseen"
        # additive arm: only DUE can fire
        add = "additive-fires" if due else ("veto-but-blocked" if (veto and blocked)
               else ("veto-no-due-no-block" if veto else rec))
        out.append({"t0": round(t0, 3), "dist": round(d, 1), "record": rec, "additive": add})
    return {"capture": os.path.basename(path), "fid": fid, "grants": n_grants,
            "vetoes": n_veto, "steps": out}

def main():
    vault = vaultpath.vault_root()
    rows = ar.scoreable_captures(vault)
    upto = sys.argv[1] if len(sys.argv) > 1 else None   # e.g. 20260830T235959
    if upto:
        rows = [r for r in rows if os.path.basename(r[0])[8:23] <= upto]
    meshes = ar._Meshes()
    res = []
    for (p, fid, n) in rows:
        try:
            mesh = meshes.get(fid)
            res.append(run(p, mesh))
        except Exception as e:
            res.append({"capture": os.path.basename(p), "error": repr(e), "steps": []})
    tot = {}
    tot_rec = {}
    nsteps = 0
    for r in res:
        for s in r["steps"]:
            nsteps += 1
            tot[s["additive"]] = tot.get(s["additive"], 0) + 1
            tot_rec[s["record"]] = tot_rec.get(s["record"], 0) + 1
    print(json.dumps({"captures": len(res), "errors": sum(1 for r in res if "error" in r),
                      "grants": sum(r.get("grants", 0) for r in res),
                      "hard_steps": nsteps, "record_classes": tot_rec,
                      "additive_classes": tot}, indent=1))
    # (the review copy prints only; the panel's original also wrote a JSON beside itself)

if __name__ == "__main__":
    main()
