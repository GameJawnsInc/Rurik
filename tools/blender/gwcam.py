"""Put a Guild-Wars-shaped camera in an imported map.

    blender scene.blend --python tools/blender/gwcam.py -- -9067 13218
    blender scene.blend --python tools/blender/gwcam.py -- -9067 13218 --dist 900

WHY A SCRIPT AND NOT ADVICE. A 40 km map with Blender's default clip range
(0.01 m to 1,000,000 m) is a depth ratio of 1e8, and the depth buffer has
nowhere near that precision -- coplanar terrain and its overlays z-fight, and
distant geometry stipples. The clip planes here are DERIVED from the map's own
extent rather than typed in: near is one cell pitch (96 units, so nothing you
would stand next to is clipped), far is twice the map diagonal.

WHAT IS MEASURED HERE AND WHAT IS NOT, because the difference matters:

  * MEASURED -- the world scale. Cell pitch is 96 units (T3), maps are tens of
    thousands of units across, and a character occupies a couple of hundred.
    Every distance below is expressed in those units and is checkable.
  * NOT MEASURED -- the LENS. Guild Wars' field of view is not read out of the
    client anywhere in this repo; the client has an `oldfov` command-line flag
    (studies/datwrite) which says the value exists and changed, and nobody has
    gone and got it. `--lens` defaults to 28 mm because a third-person chase
    camera is wide, and that is a STARTING POINT, not a finding. If the framing
    matters to a conclusion, measure the FOV first.

The pitch and distance defaults come from matching screenshots by eye and are
in the same category: adjustable, not authoritative.
"""
import math
import sys

import bpy


CELL_PITCH = 96.0          # MEASURED, T3


def _args(argv):
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(argv) < 2:
        raise SystemExit("usage: gwcam.py -- <world_x> <world_y> "
                         "[--dist D] [--pitch DEG] [--yaw DEG] [--lens MM]")
    x, y = float(argv[0]), float(argv[1])
    opt = {"dist": 1100.0, "pitch": 32.0, "yaw": 215.0, "lens": 28.0}
    for k in list(opt):
        flag = "--" + k
        if flag in argv:
            opt[k] = float(argv[argv.index(flag) + 1])
    return x, y, opt


def ground_z(x, y):
    """Height of the nearest terrain vertex, so the camera frames the ground."""
    best = None
    for ob in bpy.data.objects:
        if ob.type != "MESH" or len(ob.data.vertices) < 10000:
            continue                       # the terrain is the big mesh
        m = ob.matrix_world
        for v in ob.data.vertices:
            w = m @ v.co
            d = (w.x - x) ** 2 + (w.y - y) ** 2
            if best is None or d < best[0]:
                best = (d, w.z)
        break
    return 0.0 if best is None else best[1]


def main():
    x, y, opt = _args(sys.argv)
    z0 = ground_z(x, y)

    # Far plane from the map's own extent, near from one cell.
    lo = [1e18] * 3
    hi = [-1e18] * 3
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            w = ob.matrix_world @ __import__("mathutils").Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    diag = math.dist(lo, hi) if lo[0] < 1e17 else 40000.0

    cam = bpy.data.cameras.new("gw_cam")
    cam.lens = opt["lens"]
    cam.clip_start = CELL_PITCH          # a cell: never clips what you stand on
    cam.clip_end = max(diag * 2.0, 10000.0)
    ob = bpy.data.objects.new("gw_cam", cam)
    bpy.context.scene.collection.objects.link(ob)

    pitch = math.radians(opt["pitch"])
    yaw = math.radians(opt["yaw"])
    d = opt["dist"]
    ob.location = (x - d * math.cos(pitch) * math.sin(yaw),
                   y - d * math.cos(pitch) * math.cos(yaw),
                   z0 + d * math.sin(pitch))
    # look at a point a little above the ground, where a character's chest is
    ob.rotation_euler = (math.pi / 2 - pitch, 0.0, yaw)
    bpy.context.scene.camera = ob

    print("gw_cam at (%.0f, %.0f, %.0f) looking at (%.0f, %.0f, %.0f)"
          % (ob.location[0], ob.location[1], ob.location[2], x, y, z0))
    print("  lens %.0f mm (NOT MEASURED), pitch %.0f deg, dist %.0f units"
          % (opt["lens"], opt["pitch"], d))
    print("  clip %.0f .. %.0f  (ratio %.0f -- Blender's default is 1e8)"
          % (cam.clip_start, cam.clip_end, cam.clip_end / cam.clip_start))
    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
        print("  saved into %s" % bpy.data.filepath)


main()
