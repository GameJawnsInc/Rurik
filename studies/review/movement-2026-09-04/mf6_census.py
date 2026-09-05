"""Read-only. For every lead-ON harness capture on 09-03/04: gate2-offmesh re-pin fires
(time relative to the first S press), whether the drawn body was parked BEFORE the S press
(tape), the first full-length lead (>=299 u) and its leg, and the critics' lock signature.
Prints only."""
import json, glob, os, math, datetime as dt
V = 'C:/gd/Rurik/vault'
tapes = sorted(glob.glob(V + '/research/animref/agenttap-2026090[34]T*.jsonl'))
caps = sorted(glob.glob(V + '/captures/gamesrv/authsrv-2026090[34]T*-c1.jsonl'))
def stamp(p, pre): return os.path.basename(p)[len(pre):len(pre) + 15]
def T(s): return dt.datetime.strptime(s, '%Y%m%dT%H%M%S')
harn = {}
for rp in glob.glob(V + '/captures/harness/*/report.json'):
    try:
        rep = json.load(open(rp, encoding='utf-8'))
    except Exception:
        continue
    for c in rep.get('captures') or []:
        b = os.path.basename(c)
        if b.startswith('authsrv-') and 'gamesrv' in c.replace('\\', '/'):
            harn[b[8:23]] = (os.path.basename(os.path.dirname(rp)), rep)

def load_cap(c):
    origin = None; flags = None; rows = []
    for l in open(c, encoding='utf-8', errors='replace'):
        try:
            r = json.loads(l)
        except Exception:
            continue
        k = r.get('kind')
        if k == 'origin': origin = r['wall_unix']
        elif k == 'flags': flags = r
        elif k in ('position_report', 'agtrack_repin_fire', 'kbd_leg', 'agtrack_guard', 'grant_verdict'):
            rows.append(r)
    return origin, flags, rows

def legs_score(walk, reps):
    legs = [w for w in walk if w.get('kind') == 'key' and w.get('key') in ('W', 'S', 'Q', 'E')]
    stops = [r['wall_unix'] for r in reps if r.get('source') == '0x0047']
    sig = ''
    for w in legs:
        rel = w['ended_unix']
        sig += 'Y' if any(rel - 0.2 <= s <= rel + 1.5 for s in stops) else '.'
    trailing = len(sig) - len(sig.rstrip('.'))
    return sig, trailing, legs

print('capture         harn   | S1 cap_t | g2 fires (t rel S1)        | parked under W (tape v @S1-2.5) | 1st >=299u lead: leg,t-rel-legstart | vetoes g2 | sig      lock')
tot = dict(lock=0, nolock=0, lock_g2pre=0, nolock_g2pre=0, lock_parked=0, nolock_parked=0)
for c in caps:
    cs = stamp(c, 'authsrv-')
    origin, flags, rows = load_cap(c)
    if not flags or not flags.get('KBD_SYNC_LEAD_ON') or cs not in harn:
        continue
    hname, rep = harn[cs]
    walk = rep.get('walk') or []
    s_legs = [w for w in walk if w.get('kind') == 'key' and w.get('key') == 'S']
    if not s_legs:
        continue
    reps = [r for r in rows if r['kind'] == 'position_report']
    sig, trailing, legs = legs_score(walk, reps)
    lock = trailing >= 2
    press = s_legs[0]['started_unix']
    fires = [(r['wall_unix'] - press, r.get('why')) for r in rows if r['kind'] == 'agtrack_repin_fire']
    g2 = [round(t, 2) for t, w in fires if w == 'gate2-offmesh']
    g2pre = any(-6 <= t <= 0 for t in g2)
    vet = sum(1 for r in rows if r['kind'] == 'agtrack_guard' and r.get('code') == 'veto' and r.get('why') == 'gate2-offmesh')
    # first full-length lead
    lead = '-'
    for r in rows:
        if r['kind'] == 'kbd_leg' and r.get('act') == 'arm' and r.get('src') == 'kbd':
            # reach from the report the leg was armed on: use grant_verdict? use dest vs prior position_report
            pass
    gv = [r for r in rows if r['kind'] == 'grant_verdict' and r.get('lead_src') == 'kbd' and r.get('fired')]
    # reach: distance from the last position_report before the row to dest
    for r in gv:
        prior = [p for p in reps if p['wall_unix'] <= r['wall_unix']]
        if not prior: continue
        p = prior[-1]
        rp = p.get('reported')
        if not rp: continue
        px, py = rp[0], rp[1]
        d = math.hypot(r['dest'][0] - px, r['dest'][1] - py)
        if d >= 299:
            # which leg
            lg = '?'
            for i, w in enumerate(legs):
                if w['started_unix'] - 0.3 <= r['wall_unix'] <= w['ended_unix'] + 1.5:
                    lg = f"{i+1}{w['key']}"; break
            lead = f"{lg} +{r['wall_unix'] - (legs[int(lg[0])-1]['started_unix'] if lg != '?' else press):.2f}s {d:.0f}u"
            break
    tp = None
    for t in tapes:
        dd = (T(stamp(t, 'agenttap-')) - T(cs)).total_seconds()
        if -5 <= dd <= 90:
            tp = t; break
    parked = 'no tape'
    if tp:
        trows = [json.loads(l) for l in open(tp, encoding='utf-8', errors='replace')]
        t0 = trows[0]['t0']; best = None
        for r in trows[1:]:
            if r.get('kind') != 'sample': continue
            wt = t0 + r['t']
            if best is None or abs(wt - (press - 2.5)) < abs(best[0] - (press - 2.5)): best = (wt, r)
        pa = (best[1]['agents'].get('1') or {}).get('async') or {}
        v = math.hypot(pa.get('vx', 0.0), pa.get('vy', 0.0))
        parked = f"v={v:5.1f} {'PARKED' if v < 1 else 'moving'}"
    key = 'lock' if lock else 'nolock'
    tot[key] += 1
    if g2pre: tot[key + '_g2pre'] += 1
    if parked.endswith('PARKED'): tot[key + '_parked'] += 1
    print(f"{cs} {hname[9:15]} | {press-origin:6.2f} | {str(g2):26s} | {parked:30s} | {lead:32s} | {vet:2d} | {sig:8s} {'LOCK' if lock else 'no'}")
print(tot)
