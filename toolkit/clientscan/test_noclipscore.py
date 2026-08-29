"""`noclipscore.py` -- and specifically the blind spot that cost it two no-clips.

WHY THIS FILE EXISTS. `noclipscore.py` was built from the obstacle dig
(FINDINGS §1x) and validated against r4a, where it reproduced the arc's numbers.
It then read **section A: 0 off-mesh** on `r5bridge` -- a capture the operator
took specifically because they had just walked under a bridge twice. Section A
asks `containing(x, y)`, which UNIONS ALL 68 PLANES, so a body on a bridge DECK
and a body on the ground UNDER it are the same query and both score on-mesh.

FINDINGS §1w.7 had established that plane-blindness is irrelevant to a carved
HOLE -- which is true, and is exactly what made this look settled. A bridge is
the other case, and there it is the entire question. `m_point` has carried the
plane the whole time: `float x, float y, int plane, int`.

So section C exists, and this file holds it to three properties, each of which
the old code would have failed:

  1. a body declaring a plane the mesh does not offer at its (x, y) is REPORTED;
  2. section A stays blind to that same sample -- proving the two sections
     measure different things rather than one restating the other;
  3. a run with NO stacked geometry anywhere reports ZERO EXPOSURE in those
     words, and does not read as a clean result. That distinction is the whole
     lesson of the R5 bridge episode.

The fixtures are synthetic captures over the REAL map-280 mesh, built from
`readhook._LAYOUTS` so the fixture and the parser share one description of the
record (the same discipline as test_movehook.py §11).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (TOOLKIT, HERE, os.path.join(HERE, "movehook"),
           os.path.join(TOOLKIT, "mapdata")):
    sys.path.insert(0, _p)

import checks                                                  # noqa: E402
import readhook                                                # noqa: E402

LEDGER = checks.Ledger("noclipscore", floor=8)
check = checks.adopt(LEDGER)

MAP_FID = 0x287B3

# Two real positions out of the r5bridge capture, where the mesh offers exactly
# one plane and the body declared the OTHER one. Coordinates and planes are
# measurements, not inventions -- see FINDINGS §1z-c.
DECK_OVER_GROUND = (-2821.9, 6404.3, 0, 37)     # body says 0, mesh offers [37]
GROUND_UNDER_DECK = (-1031.5, 6282.8, 37, 0)    # body says 37, mesh offers [0]


def _synth(recs, sites_hits, base=0x00400000, ver=None):
    """A capture exactly as movehook.c writes one (test_movehook.py's shape)."""
    ver = ver or max(readhook._LAYOUTS)
    spec = readhook._LAYOUTS[ver]
    fmt = "<" + "I" * sum(c for _n, c in spec)
    out = bytearray(b"MVHK")
    out += struct.pack("<IIIII", ver, base, len(sites_hits),
                       struct.calcsize(fmt), len(recs))
    for rva, hits in sites_hits:
        out += struct.pack("<II", rva, hits)
    for r in recs:
        r = dict(r)
        r.setdefault("tick", 1000 + r.get("seq", 0))
        vals = []
        for name, count in spec:
            v = r.get(name, 0 if count == 1 else (0,) * count)
            vals.extend([v] if count == 1 else list(v))
        out += struct.pack(fmt, *vals)
    return bytes(out)


def _f2i(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _capture(tmp, name, samples):
    """samples: [(x, y, plane)] -> a v6 capture on one agent, site `setter`."""
    import gensites
    # gensites.rows() returns (dict_by_name, ...) -- the DLL's SITES order is
    # that dict's order, and the capture's site INDEX is a position in it, so
    # the fixture has to build its site table the same way round.
    rows = gensites.rows()[0]
    names = list(rows)
    site = names.index("setter")
    sites_hits = [(rows[n]["rva"], 1) for n in names]
    recs = []
    for i, (x, y, plane) in enumerate(samples):
        recs.append({
            "seq": i, "tick": 100000 + i * 100, "site": site,
            "ecx": 0x0BAD0000, "have_agent": 1, "id": 1, "world": 1,
            "ptime": 5000 + i * 100,
            "point": (_f2i(x), _f2i(y), plane, 0),
        })
    path = os.path.join(tmp, name)
    with open(path, "wb") as fh:
        fh.write(_synth(recs, sites_hits))
    return path


def _run(path):
    """noclipscore's stdout for one capture."""
    import io
    import contextlib
    import noclipscore
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        noclipscore.main(["--bin", path, "--map-fid", hex(MAP_FID)])
    return buf.getvalue()


def section(text, letter):
    """The block of the report starting `<letter>. `."""
    i = text.find(f"\n{letter}. ")
    if i < 0:
        return ""
    j = text.find("\n\n", i + 1)
    return text[i:j if j > 0 else len(text)]


def main():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="noclipscore-test-")

    try:
        import gensites                                        # noqa: F401
        import pathmap
        pm = pathmap.PathingMap.load(MAP_FID)
    except Exception as ex:                                     # noqa: BLE001
        LEDGER.skip("the whole file", f"needs the archive and sites.h: {ex}")
        return LEDGER.verdict()

    # ---- FIRST: the fixtures must actually BE what they claim -------------
    # A test whose premise is wrong proves nothing, and these coordinates came
    # out of a capture rather than out of the mesh.
    for (x, y, declared, offered) in (DECK_OVER_GROUND, GROUND_UNDER_DECK):
        got = sorted({t.plane for t in pm.containing(x, y)})
        check(got == [offered],
              f"fixture ({x:.1f},{y:.1f}) really offers only plane {offered}",
              f"the mesh offers {got} there, so this fixture does not exercise "
              f"what it claims")
        check(declared not in got,
              f"and the declared plane {declared} really is absent there",
              f"mesh offers {got}")

    # ---- 1. an anomalous sample is REPORTED ------------------------------
    p = _capture(tmp, "anomaly.bin", [
        (DECK_OVER_GROUND[0], DECK_OVER_GROUND[1], DECK_OVER_GROUND[2]),
        (GROUND_UNDER_DECK[0], GROUND_UNDER_DECK[1], GROUND_UNDER_DECK[2]),
    ])
    out = _run(p)
    c = section(out, "C")
    check("declaring a plane the mesh does NOT offer:  2" in c
          or "does NOT offer:  2" in c,
          "section C reports both plane anomalies",
          f"section C said:\n{c}")

    # ---- 2. ...AND SECTION A STAYS BLIND TO IT ---------------------------
    # This is the check that proves the two sections are not one measurement
    # twice. If section A could see these, section C would be redundant; it
    # cannot, which is why r5bridge read 0 off-mesh with two no-clips in it.
    a = section(out, "A")
    check("OFF-MESH 0" in a,
          "2D coverage is BLIND to the same sample -- the sections measure "
          "different things",
          f"section A said:\n{a}")

    # ---- 3. zero exposure must not read as a clean result ----------------
    # A position with exactly one plane everywhere near it.
    p2 = _capture(tmp, "noexposure.bin", [(-6036.0, -2519.0, 0)] * 3)
    out2 = _run(p2)
    c2 = section(out2, "C")
    check("ZERO" in c2.upper() and "EXPOSURE" in c2.upper(),
          "a run with no stacked geometry says ZERO EXPOSURE in those words",
          f"section C said:\n{c2}  -- 'no anomalies' from a run that never met "
          f"the condition is the zero-exposure trap, not a measurement")
    check("declaring a plane the mesh does NOT offer:  0" in c2
          or "does NOT offer:  0" in c2,
          "CONTROL: and it does report zero for that run",
          f"section C said:\n{c2}")

    # ---- 4. CONTROL: the detector is not simply always positive ----------
    # Same mesh, same code path, a body on the plane the mesh DOES offer.
    p3 = _capture(tmp, "onplane.bin", [
        (DECK_OVER_GROUND[0], DECK_OVER_GROUND[1], DECK_OVER_GROUND[3]),
    ])
    c3 = section(_run(p3), "C")
    check("does NOT offer:  0" in c3,
          "CONTROL: a body on the plane the mesh DOES offer is NOT flagged",
          f"a detector that fires on the correct plane too would report every "
          f"run as a no-clip:\n{c3}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
