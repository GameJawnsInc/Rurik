"""kbdclickjoin.py -- does retail answer a click that lands inside OUR keyboard latch?

    python toolkit/authsrv/kbdclickjoin.py

THE QUESTION (MOVECODE-1z-ds.18). Our router drops a click (`kbd-drop`) while the keyboard
latch is armed -- a moving 0x003D at most GRANT_LOCAL_WINDOW = 3.0 s old. In the owner's runs
all three drops came after a press that had handed the body to OUR follow. Does ArenaNet's
server answer such clicks, and does an attack press between the walk and the click change
that?

OUR LATCH, reproduced from the c2s stream: armed by a 0x003D whose movementType (values[4])
is non-zero, cleared by a 0x0047 or a 0x003D with movementType 0. A 0x003E or a 0x0026 does
not clear it. Per c2s 0x003E on every live connection (livewire.decode_conn; the observer by
property 41):
  IN-LATCH -- our router would drop it. C1: nothing between the walk and the click; C2: an
              earlier click between; P: a 0x0026 press between, split by its own answer within
              0.25 s -- P-STOP (a 0x0028 [me]), P-FOLLOW (a 0x002A [me]), P-OTHER.
  OUT      -- the latch clear or older than 3 s: the base rate.
THE ANSWER: the first s2c 0x0029 [me] after the click and BEFORE the next c2s movement input
(so a keyboard lead cannot be mistaken for it), within 1 s; its delay and its distance from
the click's own point (0 = a verbatim echo).

MEASURED 2026-10-02 over the live corpus (122 connections with an observer, 160 clicks):
IN-LATCH 34, answered 34 (p50 0.041 s, max 0.062 s; 21 verbatim): C1 16/16, C2 17/17, P 1/1
(P-FOLLOW, 20260914T180058 202.187, verbatim at +31 ms -- a click -> press -> follow -> click
shape; key -> press -> follow -> click has n=0), P-STOP n=0. OUT 126, answered 125 (the 126th
preempted by the next input). Read-only; standard library only; refuses non-live captures by
construction (livewire.live_connections). Promoted from the 1z-ds.13 pass's lane B script.
"""
import collections
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

REPORT, CLICK, STOP_RPT, PRESS = 0x003D, 0x003E, 0x0047, 0x0026
GRANT, HALT, FOLLOW, POS = 0x0029, 0x0028, 0x002A, 0x002C
WINDOW = 3.0
ANSWER_WINDOW = 1.0
PRESS_ANSWER = 0.25


def _mine(v, me):
    return len(v) > 1 and isinstance(v[1], int) and int(v[1]) == me


def press_answer(merged, pj, me):
    """(halt_delay, follow_delay, swing_delay) of my own answers within PRESS_ANSWER s."""
    tp = merged[pj][0]
    halt = follow = swing = None
    for k in range(pj + 1, len(merged)):
        tk, dk, opk, vk = merged[k]
        if tk - tp > PRESS_ANSWER:
            break
        if dk != "s2c":
            continue
        if opk == 0x00A0 and len(vk) > 3 and int(vk[1]) == 4 and int(vk[2]) == me and swing is None:
            swing = tk - tp
        if not _mine(vk, me):
            continue
        if opk == HALT and halt is None:
            halt = tk - tp
        if opk == FOLLOW and follow is None:
            follow = tk - tp
    return halt, follow, swing


def after_press(merged, i, me):
    """The click whose LAST c2s input (0x003D/0x0047/0x003E/0x0026) is a press <= 3 s old,
    latch or no latch: retail's answer to a click after its own press-answer."""
    t = merged[i][0]
    for j in range(i - 1, -1, -1):
        tj, dj, opj, _vj = merged[j]
        if t - tj > WINDOW:
            return None
        if dj == "c2s" and opj in (REPORT, STOP_RPT, CLICK, PRESS):
            if opj != PRESS:
                return None
            h, f, s = press_answer(merged, j, me)
            return ("AP-STOP" if h is not None else "AP-FOLLOW" if f is not None
                    else "AP-SWING" if s is not None else "AP-NONE"), round(t - tj, 3)
    return None


def classify(merged, i, me):
    t = merged[i][0]
    latch_t = None          # time of the 0x003D that armed the latch (None = clear)
    presses = []            # c2s 0x0026 times since the latch's report
    clicks = 0              # c2s 0x003E since the latch's report
    for j in range(i):
        tj, dj, opj, vj = merged[j]
        if dj != "c2s":
            continue
        if opj == REPORT:
            mt = int(vj[4]) if len(vj) > 4 else 0
            latch_t = tj if mt else None
            presses = []
            clicks = 0
        elif opj == STOP_RPT:
            latch_t = None
            presses = []
            clicks = 0
        elif opj == PRESS and latch_t is not None:
            presses.append(j)
        elif opj == CLICK and latch_t is not None:
            clicks += 1
    if latch_t is None or t - latch_t > WINDOW:
        return "OUT", latch_t, None
    if not presses:
        return ("C2" if clicks else "C1"), latch_t, None
    # the LAST press between the walk and the click decides the sub-cell
    pj = presses[-1]
    tp = merged[pj][0]
    halt = follow = None
    for k in range(pj + 1, len(merged)):
        tk, dk, opk, vk = merged[k]
        if tk - tp > PRESS_ANSWER:
            break
        if dk != "s2c" or not _mine(vk, me):
            continue
        if opk == HALT and halt is None:
            halt = tk - tp
        if opk == FOLLOW and follow is None:
            follow = tk - tp
    sub = "P-STOP" if halt is not None else ("P-FOLLOW" if follow is not None else "P-OTHER")
    return sub, latch_t, dict(press_age=round(t - tp, 3), halt=halt, follow=follow,
                              n_press=len(presses))


def answer(merged, i, me):
    t, _d, _op, v = merged[i]
    dest = v[1] if len(v) > 1 else None
    for k in range(i + 1, len(merged)):
        tk, dk, opk, vk = merged[k]
        if tk - t > ANSWER_WINDOW:
            return None
        if dk == "c2s" and opk in (REPORT, STOP_RPT, CLICK, PRESS):
            return ("preempted", round(tk - t, 3))
        if dk == "s2c" and opk == GRANT and _mine(vk, me):
            off = None
            if isinstance(dest, (list, tuple)) and isinstance(vk[2], (list, tuple)):
                off = round(math.hypot(vk[2][0] - dest[0], vk[2][1] - dest[1]), 1)
            return ("grant", round(tk - t, 3), off)
    return None


def main():
    rows = []
    n_conn = n_conn_me = n_click = 0
    for capdir, gf in livewire.live_connections():
        n_conn += 1
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        n_conn_me += 1
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op != CLICK:
                continue
            n_click += 1
            cell, latch_t, extra = classify(merged, i, me)
            ans = answer(merged, i, me)
            ap = after_press(merged, i, me)
            rows.append(dict(cap=os.path.basename(capdir), t=round(t, 3), cell=cell,
                             kage=(None if latch_t is None else round(t - latch_t, 3)),
                             extra=extra, ans=ans, ok=ok, ap=ap))
    print(f"live connections {n_conn}; with an identified observer {n_conn_me}; clicks {n_click}")
    by = collections.defaultdict(list)
    for r in rows:
        if r["cell"] == "OUT":
            by["OUT"].append(r)
        else:
            by["IN"].append(r)
            by[r["cell"]].append(r)
            if r["cell"].startswith("P"):
                by["P"].append(r)
            else:
                by["C"].append(r)
        if r["ap"] is not None:
            by["AFTER-PRESS"].append(r)
            by[r["ap"][0]].append(r)
    for cell in ("OUT", "IN", "C", "C1", "C2", "P", "P-STOP", "P-FOLLOW", "P-OTHER",
                 "AFTER-PRESS", "AP-STOP", "AP-FOLLOW", "AP-SWING", "AP-NONE"):
        rs = by.get(cell, [])
        g = [r for r in rs if r["ans"] and r["ans"][0] == "grant"]
        pre = [r for r in rs if r["ans"] and r["ans"][0] == "preempted"]
        none = [r for r in rs if not r["ans"]]
        dl = sorted(r["ans"][1] for r in g)
        verb = sum(1 for r in g if r["ans"][2] is not None and r["ans"][2] < 1.0)
        line = (f"  {cell:9s} n={len(rs):4d}  answered by a 0x0029 [me] {len(g)}, preempted by the "
                f"next input {len(pre)}, unanswered in {ANSWER_WINDOW:g} s {len(none)}")
        if dl:
            line += (f"; delay min {dl[0]:.3f} p50 {statistics.median(dl):.3f} max {dl[-1]:.3f} s"
                     f", within 0.25 s {sum(x <= 0.25 for x in dl)}; verbatim echo {verb}")
        print(line)
    print("IN-LATCH rows:")
    for r in rows:
        if r["cell"] == "OUT":
            continue
        print(f"  {r['cap']} {r['t']:9.3f} {r['cell']:8s} latch {r['kage']:.3f}s {r['extra']} "
              f"answer {r['ans']} ok={r['ok']}")
    print("AFTER-PRESS rows (the click's last c2s input is a press <= 3 s old):")
    for r in rows:
        if r["ap"] is None:
            continue
        print(f"  {r['cap']} {r['t']:9.3f} {r['ap'][0]:9s} press {r['ap'][1]:.3f}s before; latch "
              f"{r['cell']} {r['kage']}; answer {r['ans']}")


if __name__ == "__main__":
    main()
