"""risejoin.py -- does retail's server walk a risen player before the player's own input?

    python toolkit/authsrv/risejoin.py          # the census over the live corpus
    python toolkit/authsrv/risejoin.py --rows   # every rise

THE QUESTION (MOVECODE-1z-ds.15). 20261002T124708: a c2s 0x0026 handled in the killing-blow
instant set our `attacking` on a corpse, the order outlived the death, and 0.055 s after the
shrine rise our tick sent a 2325 u follow -- the risen body walked ~982 u before the owner's
first key. Does any order survive a death on retail? And does retail's client press while
dead at all (whether a dead press should be refused or queued)?

THE JOIN, per live connection (livewire.decode_conn; the observer by property 41): the
observer's 0x00F1 status word gaining the dead bit (16) is a death, losing it a rise. From
each rise, within 15 s: the first c2s input of the observer (0x0026 / 0x003D / 0x003E /
0x0047 / 0x0027 / 0x0046 / 0x0040) and the first s2c 0x002A / 0x0029 naming it. A server
walk first is a surviving order. A rise with neither in 15 s is the discriminating row --
a kept order would have walked. Separately, every c2s 0x0026 between a death and its rise.

MEASURED 2026-10-02 over the live corpus: 26 observer deaths, 23 rises; a server walk
before the observer's own first input on 0 of 23; 3 rises with neither for 15 s. c2s
0x0026 while dead: 0 -- retail's client does not press while dead, so refuse-vs-queue has
no witness on the wire. Read-only; standard library only; refuses non-live captures by
construction (livewire.live_connections).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

STATUS = 0x00F1
INPUT = (0x0026, 0x003D, 0x003E, 0x0047, 0x0027, 0x0046, 0x0040)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true", help="every rise")
    a = ap.parse_args()
    deaths = rises = walked_first = quiet = dead_presses = 0
    rows = []
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        dead = False
        for i, (t, d, op, v) in enumerate(merged):
            if dead and d == "c2s" and op == 0x0026:
                dead_presses += 1
            if d != "s2c" or op != STATUS or len(v) < 3:
                continue
            try:
                ag, word = int(v[1]), int(v[2])
            except (TypeError, ValueError):
                continue
            if ag != me:
                continue
            if word & 16 and not dead:
                dead = True
                deaths += 1
            elif not (word & 16) and dead:
                dead = False
                rises += 1
                first_in = first_walk = None
                for j in range(i + 1, len(merged)):
                    tj, dj, opj, vj = merged[j]
                    if tj - t > 15.0:
                        break
                    if dj == "c2s" and opj in INPUT and first_in is None:
                        first_in = (round(tj - t, 2), hex(opj))
                    if (dj == "s2c" and opj in (0x002A, 0x0029) and len(vj) > 1
                            and isinstance(vj[1], int) and vj[1] == me and first_walk is None):
                        first_walk = (round(tj - t, 2), hex(opj))
                    if first_in and first_walk:
                        break
                first = first_walk is not None and (first_in is None or first_walk[0] < first_in[0])
                walked_first += first
                quiet += first_in is None and first_walk is None
                rows.append((os.path.basename(capdir), round(t, 2), first_in, first_walk, first))
    print(f"observer deaths {deaths}, rises {rises}; a server walk to me BEFORE my first input: "
          f"{walked_first}; rises with neither input nor walk for 15 s: {quiet}")
    print(f"c2s 0x0026 presses while dead: {dead_presses}")
    if a.rows:
        for r in rows:
            print("   ", r)


if __name__ == "__main__":
    main()
