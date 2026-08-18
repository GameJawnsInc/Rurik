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
  * MEASURED 2026-08-18 -- the FIELD OF VIEW, at last. Read out of a running
    client at default settings: **exactly 75.000 degrees**
    (1.3089969158172607 rad), and the far plane the client's own frustum
    builder uses is **48000** units. `studies/terrain/FINDINGS.md` section 10.
    The read self-validates -- the camera `target` beside it equalled the
    map's known spawn point, a number the reader was never given.
  * MEASURED TOO -- the AXIS. The 75 degrees is the HORIZONTAL field of
    view, settled two independent ways (FINDINGS section 11): the client's
    own projection scales sit as ADJACENT floats with cot(75/2) as the
    SMALLER of the pair, which is the x scale; and a geometric check against
    a screenshot refutes the vertical reading outright, because it would put
    the character's feet 55 units BELOW the terrain they stand on. The
    VERTICAL field therefore depends on the render aspect and is 43.6 degrees
    at 16:9-ish. `--fov-axis` remains, now as an override rather than a
    guess.

The pitch and distance defaults come from matching screenshots by eye and are
in the same category: adjustable, not authoritative.
"""
import math
import sys

import bpy


CELL_PITCH = 96.0          # MEASURED, T3

#: MEASURED 2026-08-18 off a running client at default settings, read from the
#: field-of-view global the frustum builder is handed (FINDINGS section 10).
#: Exactly 75 degrees -- 1.3089969158172607 rad, which is 75 * pi/180 to the
#: last bit, so it is an authored round number and not an artefact.
GW_FOV_DEG = 75.0
#: MEASURED 2026-08-18 (FINDINGS section 11): the axis is HORIZONTAL. The
#: client's projection holds cot(75/2) as the SMALLER of an adjacent pair whose
#: ratio is the render aspect -- i.e. the x scale -- and the vertical reading is
#: refuted geometrically (it would bury the character 55 units under the
#: ground). NOTE this disagrees with ArenaNet's own 2018 patch note, which
#: describes a "vertical calculation"; the disagreement is recorded, not
#: resolved. Override with --fov-axis.
GW_FOV_AXIS = "horizontal"
#: MEASURED: the literal the client's own frustum builder loads (0x00946EBC).
GW_FAR_PLANE = 48000.0


def _args(argv):
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(argv) < 2:
        raise SystemExit("usage: gwcam.py -- <world_x> <world_y> "
                         "[--dist D] [--pitch DEG] [--yaw DEG] "
                         "[--fov DEG] [--fov-axis vertical|horizontal|diagonal]")
    x, y = float(argv[0]), float(argv[1])
    opt = {"dist": 1100.0, "pitch": 32.0, "yaw": 215.0, "fov": GW_FOV_DEG}
    for k in list(opt):
        flag = "--" + k
        if flag in argv:
            opt[k] = float(argv[argv.index(flag) + 1])
    axis = GW_FOV_AXIS
    if "--fov-axis" in argv:
        axis = argv[argv.index("--fov-axis") + 1]
    if axis not in ("vertical", "horizontal", "diagonal"):
        raise SystemExit("--fov-axis must be vertical, horizontal or diagonal")
    opt["axis"] = axis
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
    # The field of view is set as an ANGLE on a named axis rather than as a
    # focal length, because a lens in millimetres only means something once the
    # sensor and its fit are pinned too -- and the fit is exactly the part that
    # is assumed here. Blender's `angle_y`/`angle_x` want the matching
    # `sensor_fit`, so set the fit FIRST.
    fov = math.radians(opt["fov"])
    if opt["axis"] == "vertical":
        cam.sensor_fit = "VERTICAL"
        cam.angle_y = fov
    elif opt["axis"] == "horizontal":
        cam.sensor_fit = "HORIZONTAL"
        cam.angle_x = fov
    else:
        # A diagonal field has no direct Blender setter: convert it to the
        # vertical one for the render's own aspect, which is what the camera
        # actually needs.
        r = bpy.context.scene.render
        aspect = (r.resolution_x * r.pixel_aspect_x) / max(
            r.resolution_y * r.pixel_aspect_y, 1e-9)
        cam.sensor_fit = "VERTICAL"
        cam.angle_y = 2.0 * math.atan(math.tan(fov / 2.0)
                                      / math.hypot(aspect, 1.0))
    cam.clip_start = CELL_PITCH          # a cell: never clips what you stand on
    # The client's own far plane, MEASURED, when it covers the map; otherwise
    # the map's extent, because a 48000 far plane cannot show a 40 km map whole.
    cam.clip_end = max(GW_FAR_PLANE, diag * 2.0, 10000.0)
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
    print("  fov %.3f deg on the %s axis (both MEASURED 2026-08-18)"
          % (opt["fov"], opt["axis"]))
    print("  -> lens %.2f mm at sensor %.1f mm, pitch %.0f deg, dist %.0f units"
          % (cam.lens, cam.sensor_height if cam.sensor_fit == "VERTICAL"
             else cam.sensor_width, opt["pitch"], d))
    print("  clip %.0f .. %.0f  (ratio %.0f -- Blender's default is 1e8)"
          % (cam.clip_start, cam.clip_end, cam.clip_end / cam.clip_start))
    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
        print("  saved into %s" % bpy.data.filepath)


main()
