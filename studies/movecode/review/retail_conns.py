"""Every LIVE (retail) connection that has an observer, decoded once through livewire.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0): `wf-verify-D-sweep/vlive.py`, the
verifier's retail loader behind `live_cache.pkl`. It is the retail half of the scorers of record
`c_retail_sametick.py` (1z-ds.36), `r_windup_follow.py` (1z-ds.28), `r_death_any.py` (1z-ds.27) and
`h_retail_death.py` (1z-ds.31), through `rlib.py` and `h_core.py`.

The original cached the decode in a pickle inside the session's scratchpad. This copy decodes from the
vault each time (livewire's own loader, origin LIVE only, the toolkit's refuse-to-mix rule) and caches
ONLY when told where: set RURIK_LIVE_CACHE to a pickle path OUTSIDE the checkout (the first run writes
it, later runs read it). Each connection is a dict(cap, gf, ok, me, merged); `merged` is livewire's
[(t, 'c2s'|'s2c', opcode, values)] in stream order and `me` is the observing player's agent id
(pressstopjoin.whose_agent: NO FALLBACK -- a connection without exactly one is skipped, as it was).

Read-only. Stdlib only. Needs the vault (captures, the owner's own live captures).

    python studies/movecode/review/retail_conns.py        # prints the connection census
"""
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
sys.path.insert(0, HERE)

import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

CACHE = os.environ.get("RURIK_LIVE_CACHE")
_C = None


def conns():
    global _C
    if _C is not None:
        return _C
    if CACHE and os.path.exists(CACHE):
        with open(CACHE, "rb") as f:
            _C = pickle.load(f)
        return _C
    out = []
    n_all = 0
    for capdir, gf in livewire.live_connections():
        n_all += 1
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        out.append(dict(cap=os.path.basename(capdir), gf=gf, ok=ok, me=me, merged=merged))
    print(f"[retail_conns] live connections {n_all}, with an observer {len(out)}", file=sys.stderr, flush=True)
    if CACHE:
        with open(CACHE, "wb") as f:
            pickle.dump(out, f)
    _C = out
    return out


if __name__ == "__main__":
    cs = conns()
    print(len(cs), sum(1 for c in cs if c["ok"]), "ok")
    print(sum(sum(1 for r in c["merged"] if r[1] == "c2s" and r[2] == 0x26) for c in cs), "presses")
