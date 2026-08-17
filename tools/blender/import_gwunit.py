"""Build a Blender scene from a UNIT body export and MEASURE it headless.

    blender --background --factory-startup --python-exit-code 66 \
        --python tools/blender/import_gwunit.py -- \
        unit_<id>.gwmodel.json [--dump summary.json] [--render PREFIX]
        [--out scene.blend] [--clear] [--no-textures] [--no-nodes]

Rung U5 of `studies/unitmodels/PLAN.md`: the unit half of what
`import_gwmap.py` does for maps. A unit export IS a `.gwmodel` (rung M3's
interchange, plus a `skeleton` block), so the mesh path here is the map
importer's own -- `load_gwmodel` / `gwmodel_materials` / `gwmodel_mesh` are
IMPORTED from `import_gwmap.py`, not copied, and every convention they state
(the MEASURED model-space z negation, the D3D v flip, unnormalised
texcoords) applies unchanged.

WHAT "POSED" MEANS HERE, stated so a render is read for what it is. The body
is the FA0 geometry AS STORED -- a FLAT placement, no node transform applied
to any vertex. That is the honest choice, not the cheap one: the worm anchor
has 20 skeleton nodes and 3 sub-models, no measured binding between them,
and the per-vertex node-index candidate (`dat_fvf` bit 1) is UNNAMED -- so
any per-node posing of vertices would be invention. What makes the flat
placement the BIND POSE rather than a guess is measured and pinned by
`test_unitexport.py`: every channel-carrying node's base position falls
INSIDE the mesh's own bounding box -- the stored vertices already stand
around their skeleton.

THE SKELETON IS SHOWN, NOT APPLIED: one empty per blk2C node at its base
position (z negated, the mesh's own convention), parented along the measured
link hierarchy with world positions kept. Whether a base is parent-relative
or absolute is NOT MEASURED (`skelfile.py`), so nothing here accumulates
one node's base into another's -- the empties sit at the RAW bases and the
parent links carry the hierarchy.

THE RENDER IS AN INSTRUMENT, NOT A PICTURE. `--render P` writes two PNGs
from a fixed orthographic camera on the +y axis (screen x = model x,
screen y = model world-up): `P.body.png` with the body visible and
`P.empty.png` with every object render-hidden -- the control that proves
the coverage measurement can read zero. Film is transparent, so the body's
silhouette is exactly the alpha channel; `--dump` records the camera's
ortho scale and resolution so a checker outside Blender can PREDICT the
silhouette's pixel extents from the export's own bounding box and compare.
Cycles, few samples: silhouette alpha is hit-or-miss per pixel and does not
need converged shading.

Everything the dump reports is read back off the BUILT scene (`foreach_get`
on the evaluated mesh, object matrices, material node trees), never off the
lists handed to `from_pydata` -- the same rule as `mesh_summary` in the map
importer, so anything Blender did to the data on the way in shows up.
"""

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    import bpy
except ImportError:                                          # pragma: no cover
    bpy = None

from import_gwmap import (load_gwmodel, gwmodel_materials,  # noqa: E402
                          gwmodel_mesh, _script_argv)

RENDER_SIZE = 256
#: ortho_scale = MARGIN * the larger projected extent, so the silhouette
#: never clips and its pixel size stays predictable from the bbox.
MARGIN = 1.1


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def build_unit(json_path, no_textures=False, no_nodes=False):
    """The body object and the node empties. Returns `(body, empties, meta)`."""
    meta, positions, idx, uvs = load_gwmodel(json_path)
    mdir = os.path.dirname(os.path.abspath(json_path))
    name = meta.get("name") or "unit"
    mats, sub_images = ({}, {})
    if not no_textures:
        mats, sub_images = gwmodel_materials(meta, mdir)
    mesh = gwmodel_mesh(meta, positions, idx, name, uvs=uvs,
                        materials=mats, sub_images=sub_images)
    body = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(body)
    body["gw_file_id"] = meta.get("source", {}).get("file_id", -1)
    skel = meta.get("skeleton") or {}
    body["gw_skeleton_present"] = bool(skel.get("present"))

    empties = []
    if not no_nodes and skel.get("present"):
        records = skel["nodes"]["records"]
        for i, rec in enumerate(records):
            x, y, z = rec["base"]
            emp = bpy.data.objects.new("%s.node%02d" % (name, i), None)
            emp.empty_display_type = "SPHERE"
            emp.empty_display_size = 2.0
            # z negated: the mesh's own MEASURED convention (import_gwmap
            # `gwmodel_mesh`), so a node sits where its body does.
            emp.location = (x, y, -z)
            emp["gw_link"] = rec["link"]
            bpy.context.scene.collection.objects.link(emp)
            empties.append(emp)
        # Evaluate BEFORE parenting: a just-created object's matrix_world
        # is still identity until the depsgraph runs, so an inverse taken
        # from it would ADD the parent's base into the child's -- which is
        # exactly what the placement check caught (2/20 empties where they
        # were measured to be).
        bpy.context.view_layer.update()
        for i, rec in enumerate(records):
            link = rec["link"]
            if link == i:
                continue                     # self-link: a root node
            parent = empties[link]
            empties[i].parent = parent
            # Keep the WORLD position: the raw base is the measurement,
            # the hierarchy is the display.
            empties[i].matrix_parent_inverse = \
                parent.matrix_world.inverted()
    return body, empties, meta


def unit_summary(body, empties, meta, json_path):
    # A parented object's matrix_world is computed by the dependency graph,
    # and in --background nothing has evaluated it yet: without this update
    # 18 of the worm's 20 empties read back at their PARENT-RELATIVE
    # positions and the placement check went red. Found by the check, which
    # is what it is for.
    bpy.context.view_layer.update()
    mesh = body.data
    n = len(mesh.vertices)
    co = [0.0] * (3 * n)
    mesh.vertices.foreach_get("co", co)
    xs, ys, zs = co[0::3], co[1::3], co[2::3]
    r2d = 0.0
    for i in range(n):
        h = xs[i] * xs[i] + ys[i] * ys[i]
        if h > r2d:
            r2d = h
    r2d = math.sqrt(r2d)

    images = sorted({node.image.name
                     for mat in mesh.materials if mat and mat.use_nodes
                     for node in mat.node_tree.nodes
                     if node.type == "TEX_IMAGE" and node.image})
    bound_faces = 0
    imaged_slots = set()
    for si, mat in enumerate(mesh.materials):
        if mat and mat.use_nodes and any(
                nd.type == "TEX_IMAGE" and nd.image
                for nd in mat.node_tree.nodes):
            imaged_slots.add(si)
    for poly in mesh.polygons:
        if poly.material_index in imaged_slots:
            bound_faces += 1

    nodes = []
    for emp in empties:
        loc = emp.matrix_world.translation
        nodes.append({"name": emp.name,
                      "link": emp["gw_link"],
                      "parent": emp.parent.name if emp.parent else None,
                      "location": [loc.x, loc.y, loc.z]})
    return {
        "format": meta.get("format"),
        "name": body.name,
        "source_json": os.path.abspath(json_path),
        "blender": bpy.app.version_string,
        "mesh": {
            "vertex_count": n,
            "face_count": len(mesh.polygons),
            "submodels": len(meta.get("submodels", [])),
            "bbox": {"min": [min(xs), min(ys), min(zs)],
                     "max": [max(xs), max(ys), max(zs)]},
            "max_2d_radius": r2d,
            "material_slots": len(mesh.materials),
            "images": images,
            "faces_with_image": bound_faces,
            "uv_layers": len(mesh.uv_layers),
        },
        "skeleton": {
            "present": bool(body.get("gw_skeleton_present")),
            "node_count": len(nodes),
            "roots": sum(1 for nd in nodes if nd["parent"] is None),
            "nodes": nodes,
        },
    }


def render_silhouette(body, empties, prefix, size=RENDER_SIZE):
    """Two PNGs: the body's silhouette, and the hidden-everything control.

    Returns the camera block for the dump. Orthographic, on the +y axis
    looking back along -y at the mesh bbox's centre: screen x = model x,
    screen y = world z. `ortho_scale` covers the LARGER of the two projected
    extents times MARGIN, and the dump carries it so the checker can predict
    the silhouette's pixel width and height from the export's own bbox.
    """
    scene = bpy.context.scene
    mesh = body.data
    n = len(mesh.vertices)
    co = [0.0] * (3 * n)
    mesh.vertices.foreach_get("co", co)
    xs, ys, zs = co[0::3], co[1::3], co[2::3]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    cz = (min(zs) + max(zs)) / 2.0
    ext_x = max(xs) - min(xs)
    ext_y = max(ys) - min(ys)
    ext_z = max(zs) - min(zs)
    dist = max(ext_x, ext_y, ext_z) * 2.0 + 10.0

    cam_data = bpy.data.cameras.new("unitcam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = MARGIN * max(ext_x, ext_z)
    cam_data.clip_start = 0.1
    cam_data.clip_end = dist * 4.0
    cam = bpy.data.objects.new("unitcam", cam_data)
    # At -y of centre... no: on the -y SIDE is where the camera must STAND
    # to look +y. rotation (pi/2, 0, 0) turns the camera's -z onto +y.
    cam.location = (cx, cy - dist, cz)
    cam.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    scene.collection.objects.link(cam)
    scene.camera = cam

    sun_data = bpy.data.lights.new("unitsun", type="SUN")
    sun = bpy.data.objects.new("unitsun", sun_data)
    sun.location = (cx, cy - dist, cz + dist)
    sun.rotation_euler = (math.pi / 3.0, 0.0, 0.0)
    scene.collection.objects.link(sun)

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"

    body_png = os.path.abspath(prefix + ".body.png")
    empty_png = os.path.abspath(prefix + ".empty.png")
    scene.render.filepath = body_png
    bpy.ops.render.render(write_still=True)

    hidden = [body] + list(empties)
    for obj in hidden:
        obj.hide_render = True
    scene.render.filepath = empty_png
    bpy.ops.render.render(write_still=True)
    for obj in hidden:
        obj.hide_render = False

    return {"engine": scene.render.engine,
            "resolution": [size, size],
            "ortho_scale": cam_data.ortho_scale,
            "camera_axis": "+y",
            "screen_x": "model x", "screen_y": "world z (stored z negated)",
            "body_png": body_png, "empty_png": empty_png}


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="import_gwunit.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", help="the unit_<id>.gwmodel.json of a unit export")
    ap.add_argument("--dump", default=None,
                    help="write the built scene's summary here as JSON")
    ap.add_argument("--render", default=None, metavar="PREFIX",
                    help="write PREFIX.body.png and PREFIX.empty.png")
    ap.add_argument("--render-size", type=int, default=RENDER_SIZE)
    ap.add_argument("--out", default=None,
                    help="save the scene to this .blend when done")
    ap.add_argument("--clear", action="store_true",
                    help="empty the scene first (the startup cube and friends)")
    ap.add_argument("--no-textures", action="store_true",
                    help="build the mesh without materials or UVs -- the "
                         "control for the texture path")
    ap.add_argument("--no-nodes", action="store_true",
                    help="skip the skeleton empties")
    args = ap.parse_args(_script_argv(argv))

    if args.clear:
        clear_scene()
    body, empties, meta = build_unit(args.json, no_textures=args.no_textures,
                                     no_nodes=args.no_nodes)
    summary = unit_summary(body, empties, meta, args.json)
    if args.render:
        summary["render"] = render_silhouette(body, empties, args.render,
                                              size=args.render_size)

    m = summary["mesh"]
    print("imported %s" % os.path.basename(args.json))
    print("  mesh          %d vertices, %d faces, %d sub-models"
          % (m["vertex_count"], m["face_count"], m["submodels"]))
    print("  bbox min      %r" % (m["bbox"]["min"],))
    print("  bbox max      %r" % (m["bbox"]["max"],))
    print("  materials     %d slots, %d images, %d/%d faces bound"
          % (m["material_slots"], len(m["images"]), m["faces_with_image"],
             m["face_count"]))
    sk = summary["skeleton"]
    if sk["present"]:
        print("  skeleton      %d node empties (%d root(s)), raw bases, "
              "hierarchy by parent link" % (sk["node_count"], sk["roots"]))
    else:
        print("  skeleton      absent in the export")
    if args.render:
        print("  render        %s + control" % summary["render"]["body_png"])

    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
            fh.write("\n")
        print("  summary       %s" % args.dump)
    if args.out:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
        print("  saved         %s" % os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
