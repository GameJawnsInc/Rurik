"""Lane S retail loader: the D-verifier's decoded live cache (read-only), plus helpers.

rows = [(t, dir, op, v)] in stream order; me = the observer (property 41).
The cache was built by vlive.py from livewire.decode_conn over livewire.live_connections().

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); the loader behind `r_windup_follow.py`
(FINDINGS 1z-ds.28) and `r_death_any.py` (1z-ds.27). conns() now comes from `retail_conns.py` (livewire decode of
the vault, byte-identical to the scratchpad's `live_cache.pkl` it replaces), not from a pickle.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retail_conns  # noqa: E402


def conns():
    return retail_conns.conns()


def i(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def f32(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def is_prop(r, op, prop, me, val=None):
    t, d, o, v = r
    if d != "s2c" or o != op or len(v) < 4:
        return False
    if i(v[1]) != prop or i(v[2]) != me:
        return False
    return val is None or i(v[3]) == val


def mine(r, me, ops):
    t, d, o, v = r
    return d == "s2c" and o in ops and len(v) > 1 and i(v[1]) == me


def xy(v):
    """(x, y) of a movement-family s2c / a c2s report."""
    try:
        if isinstance(v[1], list):
            return float(v[1][0]), float(v[1][1])
        if len(v) > 3:
            a, b = v[2], v[3]
            if isinstance(a, float) or isinstance(b, float):
                return float(a), float(b)
            return f32(a), f32(b)
    except (TypeError, ValueError, IndexError):
        pass
    return None


def name(c):
    return f"{c['cap']}"
