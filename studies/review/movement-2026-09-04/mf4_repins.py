import json, glob, os, re, math, collections
caps = sorted(glob.glob('C:/gd/Rurik/vault/captures/gamesrv/authsrv-2026090[34]T*-c*.jsonl'))
rows=[]
for f in caps:
    recs=[]
    flags={}
    for line in open(f,encoding='utf-8',errors='replace'):
        try: d=json.loads(line)
        except Exception: continue
        if d.get('kind')=='flags': flags=d
        recs.append(d)
    lead=flags.get('KBD_SYNC_LEAD_ON'); waiver=flags.get('STATIONARY_WAIVER', flags.get('REPIN_STATIONARY_WAIVER'))
    for i,d in enumerate(recs):
        if d.get('kind')=='sent' and d.get('opcode')==44 and d.get('plain','').startswith('2c0001000000') and 'AGTRACK RE-PIN' in d.get('label',''):
            m=re.search(r'predicted snap \((.*?)\)',d['label']); why=m.group(1) if m else '?'
            t=d['t']
            m2=re.search(r'at \((-?\d+),(-?\d+)\)',d['label']); pin=(float(m2.group(1)),float(m2.group(2)))
            # previous position report
            prev=[r for r in recs[:i] if r.get('kind')=='position_report']
            pr=prev[-1] if prev else None
            age=round(t-pr['t'],3) if pr else None
            # was body walking: last decoded movement opcode before pin
            mv=[r for r in recs[:i] if r.get('kind')=='decoded' and r.get('name') in ('MOVE_SET_HEADING','MOVE_STOP','MOVE_TO_COORD','MOVE_TO_COORD_CLICK') or (r.get('kind')=='decoded' and r.get('opcode') in (61,71,62))]
            last_mv=mv[-1] if mv else None
            lm=(last_mv['name'] if last_mv else None, round(t-last_mv['t'],3) if last_mv else None)
            # heading speed in last 0x003D
            spd=None
            if last_mv and last_mv.get('opcode')==61:
                v=last_mv['values'][3]; spd=round(math.hypot(*v),1)
            # next reports
            nxt=[r for r in recs[i+1:] if r.get('kind')=='position_report'][:2]
            nx=[]
            for r in nxt:
                p=r['reported']; nx.append((round(r['t']-t,3), round(math.hypot(p[0]-pin[0],p[1]-pin[1]),1), r.get('source')))
            # next decoded movement opcode after the pin
            nmv=[r for r in recs[i+1:] if r.get('kind')=='decoded' and r.get('opcode') in (61,71,62)][:1]
            nm=(nmv[0].get('name'), round(nmv[0]['t']-t,3)) if nmv else None
            rows.append((os.path.basename(f)[8:22], lead, why, age, lm, spd, nx, nm))
c=collections.Counter((r[1],r[2]) for r in rows)
print('re-pins by (lead_on, reason):', dict(c))
for r in rows:
    print(r)
