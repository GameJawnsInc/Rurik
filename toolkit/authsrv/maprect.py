"""The map's rect, for an instance served with NO navmesh -- NOMESH-RECT.

WHAT IT BOUNDS. With a mesh loaded every lead is clipped to walkable ground
(`_a2_clip_lead_ray` in `authsrv.py`) and the map's edge is never reached.
With no mesh that clip's door returned the ray UNCHANGED, and the 1z-di
arrival re-grant then walked the player's copy one 520 u chord per arrival
along the held heading with nothing to stop it. Harness run
`20260925T083808` (loopback, build 38797, main 069635de) is the specimen:

  * the player backpedalled into `ascalon_to_corridor`, zoned to map 168,
    and map 168's file 0x5F0B3 is in neither archive that run held;
  * the client said so in its own log, OBSERVED (report.json `gw_log`):
    `Map '0x05f0b3' failed to load`, then `Creating default map`;
  * a W hold armed a lead at (2056, 1536) and eight re-grants followed it
    east, 2576 -> 6216, the client silent throughout;
  * the body crossed x = 3072 walking RE-GRANT 3's chord and the client
    logged `MapQueryAltitude() invalid params point=(3073.6,1536,0)
    mapRect=(-3072,-3072,3072,3072)` on 108 consecutive frames, to x = 3580.8;
  * RE-GRANT 4 at (4136, 1536) went out at 12:39:14.75 UTC and the client
    died the same second on `pos.x <= worldDims.x1`, agint.h(929) -- IN THE
    0x0029 HANDLER, with esi pointing at the float pair 0x45814000,
    0x44C00000 = (4136.0, 1536.0): the grant's own point (crash-dialog.txt,
    the Trace frame whose argument is 0x29).

A SECOND WITNESS of the same default map, and of what else it breaks:
harness `20260914T085004` reached map 168 the same way, logged the same
`Creating default map`, and died on `pos.y <= worldDims.y1`, agint.h(929),
creating `corridor_boss` at (1536, 10400) -- an agent CREATE, not a grant.

So the client checks a grant's point against the map, and a map it could not
load is a small default one. Two numbers follow and both are stated with
their label:

  * `CLIENT_DEFAULT_MAP_RECT` = (-3072, -3072, 3072, 3072), OBSERVED: the
    client printed it, verbatim, in every MapQueryAltitude line of the
    083808 run after `Creating default map`.
  * where the ASSERT sits is only bracketed: RE-GRANT 3's x = 3616 was
    accepted and RE-GRANT 4's x = 4136 asserted, so `worldDims.x1` lies in
    [3616, 4136). That is MORE than the rect, which is why the rect is the
    bound used here -- the rect is the tighter of the two things the client
    enforces, and past it the client already logs an error every frame.

`NO_MESH_RECT_INSET` is RECONSTRUCTION: 32 u inside the rect, five times the
largest per-frame step the 083808 log shows the body taking at 288 u/s (108
consecutive MapQueryAltitude x values, 4.03-5.76 u apart), so a copy arriving
on the bound never samples past the edge. Nothing measured says the edge
itself is unsafe; the inset is margin, not a finding.

When the file IS in the archive and only the mesh is missing, the rect is the
file's own Map Parameters rect -- the client copies those four floats
verbatim (studies/customarea/FINDINGS.md, "Map Parameters -- 0x2000000C":
"Copied verbatim. Zero x87 instructions in the whole function"). `authsrv.py`
reads it beside `load_pathmap`, because this file must never import the
archive -- the try/except around that import is what keeps a bare machine
working (castpolicy.py's docstring has the same rule).

Standard library only, no import of the server. `test_nomeshrect.py`
exercises every function here with no vault, no client and no socket.
"""

#: OBSERVED, harness 20260925T083808's client log: the rect of the map the
#: client builds when a map file will not load ("Creating default map").
CLIENT_DEFAULT_MAP_RECT = (-3072.0, -3072.0, 3072.0, 3072.0)

#: RECONSTRUCTION: how far inside the rect a no-mesh grant may land. See the
#: module docstring for why 32 and not 0.
NO_MESH_RECT_INSET = 32.0

#: The words `rect_source` takes, and what each means. A consumer prints the
#: word; the sentence is here so it is written once.
RECT_SOURCES = {
    "client-default": "the map's file is not in this archive, so the client "
                      "builds its DEFAULT map (OBSERVED 20260925T083808 and "
                      "20260914T085004)",
    "map-params": "the file's own Map Parameters rect, which the client "
                  "copies verbatim",
}


def inset_rect(rect, inset=NO_MESH_RECT_INSET):
    """(x0, y0, x1, y1) shrunk by `inset` on every side. Pure.

    Raises on a rect too small to hold any point after the inset, rather than
    returning an inverted box that every containment test would silently fail.
    """
    x0, y0, x1, y1 = (float(v) for v in rect)
    bx0, by0, bx1, by1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    if bx0 > bx1 or by0 > by1:
        raise ValueError(f"rect {tuple(rect)} holds nothing once inset by "
                         f"{inset} u")
    return bx0, by0, bx1, by1


def inside(point, box):
    """Is `point` within the (already inset) box, edges included? Pure."""
    x, y = float(point[0]), float(point[1])
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def clamp_point(point, rect, inset=NO_MESH_RECT_INSET):
    """([x, y], moved) -- `point` clamped per axis into the inset rect. Pure.

    The send-side backstop's answer: whatever named the point, the wire gets
    the nearest point the client's map holds. A point already inside comes
    back equal and `moved` is False.
    """
    bx0, by0, bx1, by1 = inset_rect(rect, inset)
    x, y = float(point[0]), float(point[1])
    cx = min(max(x, bx0), bx1)
    cy = min(max(y, by0), by1)
    return [cx, cy], (cx != x or cy != y)


def clip_ray(origin, dest, rect, inset=NO_MESH_RECT_INSET):
    """([x, y], clipped) -- the ray origin -> dest stopped at the inset rect.

    Pure. The lead's answer, and it keeps the ray's HEADING: a per-axis clamp
    would slide a diagonal lead along the edge, turning a walk the player aimed
    into one they did not. The ray stops where it first leaves the box.

    An origin outside the box -- a report the client made past our bound --
    gets the per-axis clamp of the origin itself: the nearest point inside,
    never a point further out. That is the one case the answer is not on the
    ray, and it is named by `clipped` like any other.
    """
    box = inset_rect(rect, inset)
    ox, oy = float(origin[0]), float(origin[1])
    dx, dy = float(dest[0]) - ox, float(dest[1]) - oy
    if not inside((ox, oy), box):
        return clamp_point((ox, oy), rect, inset)[0], True
    t = 1.0
    for o, d, lo, hi in ((ox, dx, box[0], box[2]), (oy, dy, box[1], box[3])):
        if d > 0.0 and o + d > hi:
            t = min(t, (hi - o) / d)
        elif d < 0.0 and o + d < lo:
            t = min(t, (lo - o) / d)
    if t >= 1.0:
        return [float(dest[0]), float(dest[1])], False
    return [ox + dx * t, oy + dy * t], True
