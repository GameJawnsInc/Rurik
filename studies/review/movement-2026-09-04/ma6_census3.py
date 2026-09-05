import json,glob,collections,struct,math,re
fs=sorted(glob.glob("C:/gd/Rurik/vault/captures/gamesrv/authsrv-*-c1.jsonl"))
walking=collections.Counter(); halt=collections.Counter(); cont=collections.Counter(); parked=collections.Counter(); other=collections.Counter()
senders=collections.defaultdict(list)
for f in fs:
    rows=[]
    for line in open(f,encoding="utf-8",errors="replace"):
        try: rows.append(json.loads(line))
        except: pass
    flags=next((r for r in rows if r.get("kind")=="flags"),{})
    lead=flags.get("KBD_SYNC_LEAD_ON"); ks=flags.get("KBD_SYNC"); en=flags.get("ENEMY", flags.get("NO_ENEMY"))
    stamp=f[-24:-9]
    for i,r in enumerate(rows):
        if r.get("kind")=="sent" and r.get("opcode")==44:
            lab=r.get("label",""); sender=lab.split(" 0x002C")[0].split(":")[0].split(" #")[0]
            senders[sender].append((stamp,ks,lead))
            if not lab.startswith("AGTRACK RE-PIN"): continue
            m=re.search(r"predicted snap \((.*?)\)",lab); why=m.group(1)
            b=bytes.fromhex(r["plain"]); _o,ag,x,y,p=struct.unpack_from("<HIffH",b)
            prev=None;prev2=None
            for j in range(i-1,-1,-1):
                q=rows[j]
                if q.get("kind")=="position_report" and q.get("accepted"):
                    if prev is None: prev=q
                    else: prev2=q;break
            nxt=None
            for j in range(i+1,len(rows)):
                q=rows[j]
                if q.get("kind")=="position_report" and q.get("accepted"): nxt=q;break
            age=r["t"]-prev["t"] if prev else 9e9
            pd=math.hypot(prev["reported"][0]-prev2["reported"][0],prev["reported"][1]-prev2["reported"][1]) if prev and prev2 else None
            isw = prev is not None and prev.get("source")=="0x003D" and age<0.5 and (pd is None or pd>1.0)
            key=(why,lead)
            if isw:
                walking[key]+=1
                if nxt:
                    nd=math.hypot(nxt["reported"][0]-x,nxt["reported"][1]-y); dt=nxt["t"]-r["t"]
                    if nxt.get("source")=="0x0047" and nd<1.0 and dt<2.5: halt[key]+=1
                    elif nd>20: cont[key]+=1
                    else: other[key]+=1
                else: other[key]+=1
            else:
                parked[key]+=1
print("walking-signature fires (why,LEAD):",dict(walking))
print("  halt signature (next=0x0047 at <1 u within 2.5 s):",dict(halt))
print("  walk continued (next >20 u away):",dict(cont))
print("  other:",dict(other))
print("non-walking (at a stop report / waiver retract on measured-stationary):",dict(parked))
for s,l in senders.items():
    c=collections.Counter((x[1],x[2]) for x in l); caps=sorted(set(x[0] for x in l))
    print(s,len(l),"by (KBD_SYNC,LEAD):",dict(c),"captures:",caps[:3],"..",caps[-2:], "n_caps",len(caps))
