"""LANE H core loader (my own decode): the seven owner tapes and the retail cache, as one
normalized event stream each, in STREAM order (file order for ours; merged decode order for
retail).

Event = dict(t, i, d, k, a, b, lab)
  c2s:  P press(a=target)  K skill press(a=target, b=skill)  M moving 0x3D(a=mt, b=pos)
        M0 0x3D mt 0  STOP 0x47(b=pos)  CLK 0x3E(b=pos)  CAN 0x28 (cancel action)
        INT 0x39  ROT 0x40
  s2c (me): S4 attack_started(a=target)  S50 attack-skill start(a=target, b=skill)
        S60 spell start  H prop 8 (a=value)  ST3 [3, me] (a=value)  LAND [1, me]
        F46 [46, me]  F49 [49, me]  F59 [59, me]  L 0xA4 launch  F 0x2A follow(a=target, b=xy)
        HALT 0x28  LEAD 0x29(b=xy)  PIN 0x2C(b=xy)  E3 0x00E3 (own skill activated)
  s2c (any agent): DEAD a=agent whose 0x00F1 word newly carries the dead bit 0x10
  ours only: ev rows (kind in EVROWS) as k="EV:<kind>", a=record

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); the loader behind `h_retail_death.py` and
`h_ours_deaths.py` (FINDINGS 1z-ds.31 "Recorded, not changed"). retail() now reads `retail_conns.conns()` (byte-identical
to the scratchpad's `live_cache.pkl`); the seven owner tapes (TAPES) are read from the vault's captures/gamesrv via
toolkit/vaultpath.py.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
sys.path.insert(0, HERE)

import retail_conns  # noqa: E402
import vaultpath  # noqa: E402

GS = vaultpath.vault_path("captures", "gamesrv")
TAPES = [
    ("194258", "authsrv-20261001T194336-c1.jsonl"),
    ("201800", "authsrv-20261001T201838-c1.jsonl"),
    ("005405", "authsrv-20261002T005448-c1.jsonl"),
    ("122114", "authsrv-20261002T122155-c1.jsonl"),
    ("124708", "authsrv-20261002T124744-c1.jsonl"),
    ("141035", "authsrv-20261002T141118-c1.jsonl"),
    ("200929", "authsrv-20261002T201011-c1.jsonl"),
]
DEAD_BIT = 0x10
EVROWS = ("press_stop", "press_verdict", "follow_swing", "walk_start", "router_route",
          "fence", "grant_verdict", "swing_verdict", "approach", "chain_pause")


def _c2s(t, i, op, v):
    e = dict(t=t, i=i, d="c2s", k=None, a=None, b=None, lab="")
    if op == 0x26:
        e.update(k="P", a=int(v[1]) if len(v) > 1 else None)
    elif op in (0x27, 0x46):
        e.update(k="K", a=int(v[3]) if len(v) > 3 else None, b=int(v[1]) if len(v) > 1 else None)
    elif op == 0x3D:
        mt = int(v[4]) if len(v) > 4 else 0
        pos = tuple(v[1]) if len(v) > 1 and isinstance(v[1], (list, tuple)) else None
        e.update(k="M" if mt else "M0", a=mt, b=pos)
    elif op == 0x47:
        pos = tuple(v[1]) if len(v) > 1 and isinstance(v[1], (list, tuple)) else None
        e.update(k="STOP", b=pos)
    elif op == 0x3E:
        pos = tuple(v[1]) if len(v) > 1 and isinstance(v[1], (list, tuple)) else None
        e.update(k="CLK", b=pos)
    elif op == 0x28:
        e.update(k="CAN")
    elif op == 0x39:
        e.update(k="INT", a=int(v[1]) if len(v) > 1 else None)
    elif op == 0x40:
        e.update(k="ROT")
    else:
        return None
    return e


def _s2c(t, i, op, v, me, words, lab=""):
    e = dict(t=t, i=i, d="s2c", k=None, a=None, b=None, lab=lab)
    if op == 0xA0 and len(v) > 3 and int(v[2]) == me:
        p = int(v[1])
        if p == 4:
            e.update(k="S4", a=int(v[3]))
        elif p == 50:
            e.update(k="S50", a=int(v[3]), b=int(v[4]) if len(v) > 4 else None)
        elif p == 60:
            e.update(k="S60", a=int(v[3]), b=int(v[4]) if len(v) > 4 else None)
        else:
            return None
    elif op == 0x9F and len(v) > 3:
        p, ag, val = int(v[1]), int(v[2]), int(v[3])
        if ag != me:
            return None
        k = {8: "H", 3: "ST3", 1: "LAND", 46: "F46", 49: "F49", 59: "F59"}.get(p)
        if k is None:
            return None
        e.update(k=k, a=val)
    elif op == 0xA4 and len(v) > 1 and int(v[1]) == me:
        e.update(k="L")
    elif op == 0x2A and len(v) > 1 and int(v[1]) == me:
        e.update(k="F", a=int(v[5]) if len(v) > 5 and v[5] is not None else None,
                 b=tuple(v[2]) if isinstance(v[2], (list, tuple)) else None)
    elif op == 0x28 and len(v) > 1 and int(v[1]) == me:
        e.update(k="HALT")
    elif op == 0x29 and len(v) > 1 and int(v[1]) == me:
        e.update(k="LEAD", b=tuple(v[2]) if isinstance(v[2], (list, tuple)) else None)
    elif op == 0x2C and len(v) > 1 and int(v[1]) == me:
        e.update(k="PIN", b=tuple(v[2]) if isinstance(v[2], (list, tuple)) else None)
    elif op == 0xE3 and len(v) > 1 and int(v[1]) == me:
        e.update(k="E3")
    elif op == 0xF1 and len(v) > 2:
        ag, w = int(v[1]), int(v[2])
        prev = words.get(ag, 0)
        words[ag] = w
        if (w & DEAD_BIT) and not (prev & DEAD_BIT):
            e.update(k="DEAD", a=ag)
        else:
            return None
    else:
        return None
    return e


def _plain_values(op, plain):
    b = bytes.fromhex(plain)
    try:
        if op == 0x9F:
            _o, p, ag, val = struct.unpack_from("<HIII", b, 0)
            return [op, p, ag, val]
        if op == 0xA0:
            _o, p, ag, tg, ex = struct.unpack_from("<HIIII", b, 0)
            return [op, p, ag, tg, ex]
        if op == 0xF1:
            _o, ag, w = struct.unpack_from("<HII", b, 0)
            return [op, ag, w]
        if op in (0x28, 0xA4):
            _o, ag = struct.unpack_from("<HI", b, 0)
            return [op, ag]
        if op in (0x29, 0x2C):
            _o, ag, x, y = struct.unpack_from("<HIff", b, 0)
            return [op, ag, (x, y), 0, 0]
        if op == 0x2A:
            _o, ag, x, y = struct.unpack_from("<HIff", b, 0)
            tgt = struct.unpack_from("<I", b, len(b) - 4)[0] if len(b) >= 22 else None
            return [op, ag, (x, y), 0, 0, tgt]
        if op == 0xE3:
            _o, ag = struct.unpack_from("<HI", b, 0)
            return [op, ag]
    except struct.error:
        return None
    return None


def ours(name):
    """(events, flags) for one owner tape, in FILE order (the send order)."""
    fn = dict(TAPES)[name]
    ev, words, flags = [], {}, {}
    i = 0
    for line in open(os.path.join(GS, fn), encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        k, t = r.get("kind"), r.get("t")
        if k == "flags":
            flags = r
        if not isinstance(t, (int, float)):
            continue
        i += 1
        if k == "decoded":
            e = _c2s(t, i, r["opcode"], r.get("values") or [])
            if e is not None:
                ev.append(e)
        elif k == "sent":
            op = r.get("opcode")
            if r.get("plain"):
                v = _plain_values(op, r["plain"])
                if v is not None:
                    e = _s2c(t, i, op, v, 1, words, r.get("label", ""))
                    if e is not None:
                        ev.append(e)
        elif k in EVROWS:
            ev.append(dict(t=t, i=i, d="ev", k="EV:" + k, a=r, b=None, lab=""))
    return ev, flags


def retail():
    """[(name, events)] for every cached live connection with an observer (vlive cache)."""
    cs = retail_conns.conns()
    res = []
    for c in cs:
        me, ev, words = c["me"], [], {}
        for i, (t, d, op, v) in enumerate(c["merged"]):
            if d == "c2s":
                e = _c2s(t, i, op, v)
            else:
                e = _s2c(t, i, op, v, me, words)
            if e is not None:
                ev.append(e)
        res.append((f"{c['cap']} {c['gf'][5:30]}", ev))
    return res


def hold_state_before(ev, j):
    """prop-8 state just before stream position j (0 when never set)."""
    s = 0
    for e in ev[:j]:
        if e["k"] == "H":
            s = e["a"]
    return s


def build_state(ev):
    """List of the prop-8 state AFTER each event index."""
    out, s = [], 0
    for e in ev:
        if e["k"] == "H":
            s = e["a"]
        out.append(s)
    return out
