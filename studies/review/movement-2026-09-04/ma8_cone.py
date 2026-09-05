#!/usr/bin/env python3
"""READ-ONLY: score the follower-in-cone predicate at the gate2 re-pin (the park)
and at the next key press, on the six locked runs' agenttap tapes."""
import json, math, os

PAIRS = [  # (gamesrv tag, agenttap tag)
    ('20260903T191320', '20260903T191321'),
    ('20260903T195931', '20260903T195932'),
    ('20260903T200621', '20260903T200621'),
    ('20260903T202121', None),
    ('20260903T215027', '20260903T215028'),
    ('20260904T110025', '20260904T110026'),
]

def caprows(tag):
    p = 'vault/captures/gamesrv/authsrv-%s-c1.jsonl' % tag
    out = []
    for line in open(p, encoding='utf-8', errors='replace'):
        line = line.strip()
        if line:
            try: out.append(json.loads(line))
            except Exception: pass
    return out

def taperows(tag):
    p = 'vault/research/animref/agenttap-%s.jsonl' % tag
    if not os.path.exists(p): return None, None
    head, samples = None, []
    for line in open(p, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        if r.get('kind') == 'head': head = r
        elif r.get('kind') == 'sample': samples.append(r)
    return head, samples

def nearest(samples, t):
    best = None
    for s in samples:
        d = abs(s['t'] - t)
        if best is None or d < best[0]: best = (d, s)
    return best

for captag, tapetag in PAIRS:
    rs = caprows(captag)
    t0 = None
    for r in rs:
        if r.get('kind') == 'origin': t0 = r['wall_unix'] - r['t']
    g2 = [r for r in rs if r.get('kind') == 'agtrack_repin_fire' and r.get('why') == 'gate2-offmesh']
    g2v = [r for r in rs if r.get('kind') == 'agtrack_guard' and r.get('why') == 'gate2-offmesh']
    ev = g2[0] if g2 else (g2v[0] if g2v else None)
    print('==', captag, 'tape', tapetag, 'fired' if g2 else ('veto-only' if g2v else 'NONE'))
    if tapetag is None:
        print('   NO AGENTTAP TAPE'); continue
    head, samples = taperows(tapetag)
    if head is None:
        print('   tape missing'); continue
    dt = head['t0'] - t0        # tape_t = cap_t - dt
    if ev is None: continue
    tt = ev['t'] - dt
    for label, ttt in (('-0.20s', tt - 0.20), ('at re-pin', tt), ('+0.20s', tt + 0.20), ('+1.0s', tt + 1.0)):
        d, s = nearest(samples, ttt)
        a1 = s['agents'].get('1', {}).get('async', {})
        a10 = s['agents'].get('10', {}).get('async', {})
        if not a1 or not a10: continue
        rel = (a10['x'] - a1['x'], a10['y'] - a1['y'])
        dist = math.hypot(*rel)
        v = (a1['vx'], a1['vy']); sp = math.hypot(*v)
        cos = None
        if sp > 1e-6 and dist > 1e-6:
            cos = (rel[0] * v[0] + rel[1] * v[1]) / (dist * sp)
        print('   %-10s tape_t=%7.3f (dt %.3f) body=(%.1f,%.1f) v=(%.0f,%.0f)|%.0f| foll=(%.1f,%.1f) d=%.1f cos=%s'
              % (label, s['t'], d, a1['x'], a1['y'], v[0], v[1], sp, a10['x'], a10['y'], dist,
                 ('%.2f' % cos) if cos is not None else 'n/a'))
