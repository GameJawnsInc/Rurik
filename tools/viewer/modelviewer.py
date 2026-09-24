r"""Rurik model viewer -- browse every model in the owner's `Gw.dat`, textured,
from a local window. PySide6 + OpenGL; nothing here knows the archive.

    python tools/viewer/modelviewer.py                       # the app
    python tools/viewer/modelviewer.py --file-id 116703      # open on one model
    python tools/viewer/modelviewer.py --template hatcher    # open on a template
    python tools/viewer/modelviewer.py --file-id 116703 --skeleton-from 116228 \
        --shot out.png --size 512                            # one frame, no window kept

WHY THIS LIVES UNDER `tools/` AND NOT `toolkit/`. `CLAUDE.md` pins `toolkit/`
to the standard library; PySide6 is not that. So the split is the one
`tools/blender/` already made: every archive fact -- what a head is, what a
sub-model's diffuse is, where a skeleton node sits -- comes from
`toolkit/mapdata/modelcatalog.py`, which is stdlib and tested in the suite,
and this file only draws what that module hands it. If a picture here looks
wrong, the question is for the catalog (or the decoder under it), never for
this file's idea of the format, because it has none.

WHAT IT DRAWS, AND WHAT IT DOES NOT CLAIM. The mesh is the FA0 geometry AS
STORED: a flat placement, no node transform applied to any vertex, which
`tools/blender/import_gwunit.py` established is the bind pose (every keyed
node base sits inside the mesh's own box). The skeleton overlay is the blk2C
rest positions joined along the measured link hierarchy -- for a template,
the SHELL's skeleton over the BODY's mesh, which is the composite the client
assembles. Animation is not played: the channels are decoded but nobody has
yet driven vertices through them and checked the result against the client,
so a still frame is what this viewer can stand behind. The texture on a
surface is the material's diffuse under the Blender importer's measured rule
(first layer sampling a stored UV set); the other layers are listed in the
info pane and are not blended, because which is detail/lightmap/specular is
still open (models FINDINGS §6.1).

CONVENTIONS, restated from `modelcatalog` where they are sourced: model -z is
world-up, so the scene applies a z-flip and the camera's up is +z; UVs are
Direct3D's and are used unchanged (MEASURED 2026-09-14: Qt's texture upload
puts image row 0 at v = 0 on both upload paths, so no flip is needed);
"erases" textures are drawn opaque, "cutout" textures alpha-tested, blended
materials blended -- each toggleable, because the alpha semantics are a
finding, not a rule.

WHERE FILES GO. Thumbnails and screenshots are ArenaNet's expression rendered,
so they go through `vaultpath.resolve_out`: the vault cache or a scratch
directory, never the working tree. Exports call `modelexport`/`unitexport`,
which refuse the tree themselves.
"""

import argparse
import math
import os
import sys
import time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "toolkit"), os.path.join(ROOT, "toolkit", "mapdata")):
    if p not in sys.path:
        sys.path.insert(0, p)

import modelcatalog as mc  # noqa: E402
import wireshells as ws  # noqa: E402
from archive import Archive, DEFAULT_DAT, file_id_table  # noqa: E402
import vaultpath  # noqa: E402

try:
    from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QPoint, \
        QSize, QTimer, QSortFilterProxyModel
    from PySide6.QtGui import QAction, QColor, QIcon, QImage, QKeySequence, \
        QMatrix4x4, QPixmap, QSurfaceFormat, QVector3D, QVector4D
    from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLFramebufferObject, \
        QOpenGLShader, QOpenGLShaderProgram, QOpenGLTexture, \
        QOpenGLVertexArrayObject
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, \
        QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListView, \
        QListWidget, QListWidgetItem, QMainWindow, QMessageBox, \
        QPlainTextEdit, QProgressDialog, QPushButton, QStatusBar, \
        QTabWidget, QVBoxLayout, QWidget
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"the model viewer needs PySide6 (py -m pip install PySide6): {exc}")

# OpenGL enums the portable QOpenGLFunctions subset needs; named here rather
# than pulled from a binding, because there is no binding.
GL_LINES = 0x0001
GL_TRIANGLES = 0x0004
GL_DEPTH_BUFFER_BIT = 0x0100
GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_FLOAT = 0x1406

STRIDE_FLOATS = 8                 # pos3 nrm3 uv2
STRIDE_BYTES = STRIDE_FLOATS * 4

VERT_SRC = """#version 120
attribute vec3 a_pos;
attribute vec3 a_nrm;
attribute vec2 a_uv;
uniform mat4 u_mvp;
uniform mat3 u_nrm;
varying vec3 v_nrm;
varying vec2 v_uv;
void main() {
    gl_Position = u_mvp * vec4(a_pos, 1.0);
    v_nrm = u_nrm * a_nrm;
    v_uv = a_uv;
}
"""

FRAG_SRC = """#version 120
uniform sampler2D u_tex;
uniform int u_textured;
uniform int u_alpha_test;
uniform int u_lit;
uniform int u_blend;
uniform vec4 u_color;
varying vec3 v_nrm;
varying vec2 v_uv;
void main() {
    vec4 c = u_color;
    if (u_textured == 1) {
        c = texture2D(u_tex, v_uv);
        if (u_alpha_test == 1 && c.a < 0.5) discard;
    }
    float l = 1.0;
    if (u_lit == 1) {
        vec3 n = normalize(v_nrm);
        // a headlight: the light sits at the eye, so a surface facing the
        // camera is bright and a silhouette edge is dim
        l = 0.30 + 0.70 * abs(n.z);
    }
    // An OPAQUE draw writes alpha 1: the hatcher's body texture is DXT5 with
    // alpha ~0 everywhere (an "eraser", unitexport sec 5), and passing that
    // alpha through left the framebuffer transparent where the body was --
    // white in a PNG, the window background on screen. Only a blended
    // material keeps the texture's alpha.
    gl_FragColor = vec4(c.rgb * l, u_blend == 1 ? c.a : 1.0);
}
"""

FLAT_COLOR = QVector4D(0.62, 0.62, 0.66, 1.0)
WIRE_COLOR = QVector4D(0.05, 0.05, 0.05, 1.0)
COLLISION_COLOR = QVector4D(1.0, 0.45, 0.0, 1.0)
BONE_COLOR = QVector4D(0.1, 0.9, 0.3, 1.0)
ROOT_COLOR = QVector4D(1.0, 0.2, 0.9, 1.0)
CLEAR = (0.17, 0.18, 0.21, 1.0)


# ---------------------------------------------------------------------------
# GPU-side scene
# ---------------------------------------------------------------------------

def interleave(sub):
    """`SubMesh` -> one float array, 8 floats per corner, zeros where absent."""
    n = len(sub.pos) // 3
    out = array("f", bytes(STRIDE_BYTES * n))
    out[0::8] = sub.pos[0::3]
    out[1::8] = sub.pos[1::3]
    out[2::8] = sub.pos[2::3]
    if sub.nrm is not None:
        out[3::8] = sub.nrm[0::3]
        out[4::8] = sub.nrm[1::3]
        out[5::8] = sub.nrm[2::3]
    if sub.uv is not None:
        out[6::8] = sub.uv[0::2]
        out[7::8] = sub.uv[1::2]
    return out


def wire_corners(sub):
    """Every triangle's three edges as line corners (pos only, padded)."""
    p = sub.pos
    n = len(p) // 9
    out = array("f", bytes(STRIDE_BYTES * 6 * n))
    k = 0
    for t in range(n):
        a = p[9 * t:9 * t + 3]
        b = p[9 * t + 3:9 * t + 6]
        c = p[9 * t + 6:9 * t + 9]
        for u, v in ((a, b), (b, c), (c, a)):
            out[k:k + 3] = u
            out[k + 8:k + 11] = v
            k += 16
    return out


def lines_to_corners(flat):
    """A flat xyz line-corner array -> stride-8 padded corners."""
    n = len(flat) // 3
    out = array("f", bytes(STRIDE_BYTES * n))
    out[0::8] = flat[0::3]
    out[1::8] = flat[1::3]
    out[2::8] = flat[2::3]
    return out


def skeleton_corners(nodes, cross):
    """Bone lines parent->child, and a small cross at every node."""
    bones = array("f")
    crosses = array("f")
    for n in nodes:
        if n.link != n.index and 0 <= n.link < len(nodes):
            bones.extend(nodes[n.link].base)
            bones.extend(n.base)
        x, y, z = n.base
        for d in ((cross, 0, 0), (0, cross, 0), (0, 0, cross)):
            crosses.extend((x - d[0], y - d[1], z - d[2]))
            crosses.extend((x + d[0], y + d[1], z + d[2]))
    return lines_to_corners(bones), lines_to_corners(crosses)


class GpuBuffer:
    def __init__(self, data):
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.vbo.create()
        self.vbo.bind()
        raw = data.tobytes()
        self.vbo.allocate(raw, len(raw))
        self.vbo.release()
        self.count = len(data) // STRIDE_FLOATS

    def destroy(self):
        self.vbo.destroy()


class GpuMesh:
    __slots__ = ("sub", "tris", "wire", "texture", "lit")

    def __init__(self, sub, tris, wire, texture, lit):
        self.sub = sub
        self.tris = tris
        self.wire = wire
        self.texture = texture
        self.lit = lit


def make_texture(tex):
    """Raw RGBA8 upload; row 0 lands at v = 0 (MEASURED, see module doc)."""
    t = QOpenGLTexture(QOpenGLTexture.Target2D)
    t.setFormat(QOpenGLTexture.RGBA8_UNorm)
    t.setSize(tex.width, tex.height)
    t.setMipLevels(t.maximumMipLevels())
    t.allocateStorage()
    t.setData(QOpenGLTexture.RGBA, QOpenGLTexture.UInt8, tex.rgba)
    t.generateMipMaps()
    t.setMinMagFilters(QOpenGLTexture.LinearMipMapLinear, QOpenGLTexture.Linear)
    t.setWrapMode(QOpenGLTexture.Repeat)       # retail UVs run to +-520
    return t


class Scene:
    """One `ModelView` on the GPU. Create and destroy with a current context."""

    def __init__(self, view):
        self.view = view
        self.meshes = []
        self.textures = {}
        self.collision = None
        self.bones = None
        self.crosses = None
        for fid, tex in view.textures.items():
            self.textures[fid] = make_texture(tex)
        for sub in view.submeshes:
            self.meshes.append(GpuMesh(
                sub, GpuBuffer(interleave(sub)), GpuBuffer(wire_corners(sub)),
                self.textures.get(sub.texture_fid), sub.nrm is not None))
        if view.collision is not None and len(view.collision):
            self.collision = GpuBuffer(lines_to_corners(view.collision))
        if view.skeleton:
            bones, crosses = skeleton_corners(view.skeleton, view.radius() * 0.015)
            self.bones = GpuBuffer(bones) if bones.count else None
            self.crosses = GpuBuffer(crosses) if crosses.count else None

    def destroy(self):
        for m in self.meshes:
            m.tris.destroy()
            m.wire.destroy()
        for t in self.textures.values():
            t.destroy()
        for b in (self.collision, self.bones, self.crosses):
            if b is not None:
                b.destroy()
        self.meshes = []
        self.textures = {}


class Camera:
    def __init__(self):
        self.yaw = 35.0
        self.pitch = 20.0
        self.dist = 100.0
        self.target = QVector3D(0, 0, 0)
        self.fov = 45.0

    def fit(self, view):
        cx, cy, cz = view.centre()
        self.target = QVector3D(cx, cy, -cz)          # the z-flip
        self.dist = view.radius() * 2.6 / math.tan(math.radians(self.fov) / 2) * 0.5
        self.dist = max(self.dist, 1.0)

    def eye(self):
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        d = self.dist
        return self.target + QVector3D(d * math.cos(pitch) * math.cos(yaw),
                                       d * math.cos(pitch) * math.sin(yaw),
                                       d * math.sin(pitch))

    def matrices(self, w, h):
        proj = QMatrix4x4()
        near = max(self.dist * 0.01, 0.05)
        proj.perspective(self.fov, max(w, 1) / max(h, 1), near, self.dist * 20 + 1000)
        look = QMatrix4x4()
        look.lookAt(self.eye(), self.target, QVector3D(0, 0, 1))
        model = QMatrix4x4()
        model.scale(1.0, 1.0, -1.0)                  # model -z is world-up
        return proj, look, model


class Options:
    def __init__(self):
        self.textures = True
        self.lighting = True
        self.wireframe = False
        self.collision = True
        self.skeleton = True
        self.alpha = True           # honour cutout/blend classes
        self.force_slot = None      # an FA5 slot to put on every surface


# ---------------------------------------------------------------------------
# The GL widget
# ---------------------------------------------------------------------------

class GLView(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.scene = None
        self.pending = None
        self.camera = Camera()
        self.options = Options()
        self.prog = None
        self.vao = None
        self.last = None
        self.on_status = None

    # -- lifecycle ----------------------------------------------------------

    def initializeGL(self):
        f = self.context().functions()
        f.glClearColor(*CLEAR)
        f.glEnable(GL_DEPTH_TEST)
        self.prog = QOpenGLShaderProgram()
        ok = (self.prog.addShaderFromSourceCode(QOpenGLShader.Vertex, VERT_SRC)
              and self.prog.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAG_SRC)
              and self.prog.link())
        if not ok:
            raise SystemExit(f"shader build failed: {self.prog.log()}")
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()
        self.a_pos = self.prog.attributeLocation("a_pos")
        self.a_nrm = self.prog.attributeLocation("a_nrm")
        self.a_uv = self.prog.attributeLocation("a_uv")
        if self.pending is not None:
            self.scene = Scene(self.pending)
            self.pending = None

    def set_view(self, view):
        """Show `view`; safe before the context exists."""
        self.camera.fit(view)
        if not self.isValid():
            self.pending = view
            return
        self.makeCurrent()
        if self.scene is not None:
            self.scene.destroy()
        self.scene = Scene(view)
        self.doneCurrent()
        self.update()

    def fit(self):
        if self.scene is not None:
            self.camera.fit(self.scene.view)
            self.update()

    # -- drawing ------------------------------------------------------------

    def _uniform_int(self, name, value):
        if hasattr(self.prog, "setUniformValue1i"):
            self.prog.setUniformValue1i(name, int(value))
        else:
            self.prog.setUniformValue(name, int(value))

    def _bind_buffer(self, buf):
        buf.vbo.bind()
        self.prog.enableAttributeArray(self.a_pos)
        self.prog.setAttributeBuffer(self.a_pos, GL_FLOAT, 0, 3, STRIDE_BYTES)
        self.prog.enableAttributeArray(self.a_nrm)
        self.prog.setAttributeBuffer(self.a_nrm, GL_FLOAT, 12, 3, STRIDE_BYTES)
        self.prog.enableAttributeArray(self.a_uv)
        self.prog.setAttributeBuffer(self.a_uv, GL_FLOAT, 24, 2, STRIDE_BYTES)

    def _draw_lines(self, f, buf, color):
        self._uniform_int("u_textured", 0)
        self._uniform_int("u_lit", 0)
        self._uniform_int("u_blend", 0)
        self.prog.setUniformValue("u_color", color)
        self._bind_buffer(buf)
        f.glDrawArrays(GL_LINES, 0, buf.count)
        buf.vbo.release()

    def draw_scene(self, f, w, h, scene=None, camera=None, options=None):
        scene = scene or self.scene
        camera = camera or self.camera
        opt = options or self.options
        f.glViewport(0, 0, w, h)
        f.glClearColor(*CLEAR)
        f.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if scene is None:
            return
        proj, look, model = camera.matrices(w, h)
        mv = look * model
        self.prog.bind()
        self.vao.bind()
        self.prog.setUniformValue("u_mvp", proj * mv)
        self.prog.setUniformValue("u_nrm", mv.normalMatrix())
        self._uniform_int("u_tex", 0)
        forced = None
        if opt.force_slot is not None and 0 <= opt.force_slot < len(scene.view.texture_ids):
            forced = scene.textures.get(scene.view.texture_ids[opt.force_slot])
        opaque = [m for m in scene.meshes if not (opt.alpha and m.sub.blend)]
        blended = [m for m in scene.meshes if opt.alpha and m.sub.blend]
        for group, blend in ((opaque, False), (blended, True)):
            if blend:
                f.glEnable(GL_BLEND)
                f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                f.glDepthMask(False)
            for m in group:
                tex = forced if forced is not None else m.texture
                textured = opt.textures and tex is not None and m.sub.uv is not None
                self._uniform_int("u_textured", 1 if textured else 0)
                alpha_test = (opt.alpha and textured and m.sub.alpha == "cutout"
                              and forced is None)
                self._uniform_int("u_alpha_test", 1 if alpha_test else 0)
                self._uniform_int("u_lit", 1 if (opt.lighting and m.lit) else 0)
                self._uniform_int("u_blend", 1 if blend else 0)
                self.prog.setUniformValue("u_color", FLAT_COLOR)
                if textured:
                    tex.bind(0)
                self._bind_buffer(m.tris)
                f.glDrawArrays(GL_TRIANGLES, 0, m.tris.count)
                m.tris.vbo.release()
                if textured:
                    tex.release(0)
            if blend:
                f.glDisable(GL_BLEND)
                f.glDepthMask(True)
        if opt.wireframe:
            for m in scene.meshes:
                self._draw_lines(f, m.wire, WIRE_COLOR)
        if opt.collision and scene.collision is not None:
            self._draw_lines(f, scene.collision, COLLISION_COLOR)
        if opt.skeleton:
            if scene.bones is not None:
                self._draw_lines(f, scene.bones, BONE_COLOR)
            if scene.crosses is not None:
                self._draw_lines(f, scene.crosses, ROOT_COLOR)
        self.vao.release()
        self.prog.release()

    def paintGL(self):
        f = self.context().functions()
        ratio = self.devicePixelRatioF()
        self.draw_scene(f, int(self.width() * ratio), int(self.height() * ratio))

    def render_image(self, view, size=256, options=None):
        """Draw `view` to an offscreen framebuffer and return a QImage.

        Uploads its own `Scene`, so the on-screen one is untouched; the
        camera is a fresh fit of `view` at the default orbit.
        """
        self.makeCurrent()
        f = self.context().functions()
        scene = Scene(view)
        cam = Camera()
        cam.fit(view)
        fbo = QOpenGLFramebufferObject(
            QSize(size, size), QOpenGLFramebufferObject.CombinedDepthStencil)
        fbo.bind()
        f.glEnable(GL_DEPTH_TEST)
        self.draw_scene(f, size, size, scene=scene, camera=cam, options=options)
        img = fbo.toImage()
        fbo.release()
        QOpenGLFramebufferObject.bindDefault()
        scene.destroy()
        self.doneCurrent()
        return img

    # -- mouse --------------------------------------------------------------

    def mousePressEvent(self, ev):
        self.last = ev.position()

    def mouseMoveEvent(self, ev):
        if self.last is None:
            return
        d = ev.position() - self.last
        self.last = ev.position()
        if ev.buttons() & Qt.LeftButton:
            self.camera.yaw -= d.x() * 0.4
            self.camera.pitch = max(-89.0, min(89.0, self.camera.pitch + d.y() * 0.4))
        elif ev.buttons() & (Qt.RightButton | Qt.MiddleButton):
            # pan in the view plane
            yaw = math.radians(self.camera.yaw)
            right = QVector3D(-math.sin(yaw), math.cos(yaw), 0.0)
            up = QVector3D(0, 0, 1)
            k = self.camera.dist * 0.0015
            self.camera.target += right * (-d.x() * k) + up * (d.y() * k)
        self.update()

    def wheelEvent(self, ev):
        steps = ev.angleDelta().y() / 120.0
        self.camera.dist *= 0.9 ** steps
        self.camera.dist = max(self.camera.dist, 0.05)
        self.update()

    def mouseDoubleClickEvent(self, ev):
        self.fit()


# ---------------------------------------------------------------------------
# The catalog list
# ---------------------------------------------------------------------------

class CatalogModel(QAbstractListModel):
    """The list behind the Models tab, with thumbnails rendered LAZILY.

    A row's decoration is the PNG under the thumbs cache when one exists.
    When none does and a `renderer` was given, the row is queued and a
    zero-interval timer renders ONE per event-loop turn, so scrolling asks
    for exactly the rows that came into view and the window stays live
    between renders (~50-150 ms each). Rows that raise are remembered in
    `failed` and never re-queued; a render that returns None (the GL context
    not ready) is simply not remembered, so the next paint asks again.
    Before 2026-09-24 thumbnails existed only through the menu action that
    renders every listed model behind a progress dialog (still there).
    """

    def __init__(self, records, thumbs, shells=None, renderer=None, parent=None):
        super().__init__(parent)
        self.records = records
        self.thumbs = thumbs
        self.shells = shells or {}       # shell fid -> the SHELL tag to show
        self.icons = {}
        self.renderer = renderer         # fid -> QImage | None
        self.pending = []                # fids a paint asked for, FIFO
        self.queued = set()
        self.failed = set()
        self.rendered = 0                # lazily rendered this session
        self.row_of = {r.fid: i for i, r in enumerate(records)}
        self.timer = QTimer(self)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._render_one)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.records)

    def data(self, index, role=Qt.DisplayRole):
        rec = self.records[index.row()]
        if role == Qt.DisplayRole:
            fid = rec.fid
            if rec.kind == mc.KIND_MODEL:
                what = (f"{rec.num_models} sub" if rec.num_models is not None else "?")
                if rec.collision_count:
                    what += f", {rec.collision_count} coll"
            elif rec.kind == mc.KIND_SKEL:
                what = "skeleton"
                if rec.seq_count is not None:
                    what += f", {rec.seq_count} seq, {rec.node_count} nodes"
                tag = self.shells.get(rec.fid) if self.shells else None
                if tag:
                    what += "  · " + tag
            else:
                what = rec.problem or "?"
            return f"{fid:>7}  0x{fid:05X}   {what}   {rec.size // 1024} KB"
        if role == Qt.DecorationRole:
            path = self.thumbs.path_for(rec.fid)
            if rec.fid in self.icons:
                return self.icons[rec.fid]
            if os.path.isfile(path):
                icon = QIcon(path)
                self.icons[rec.fid] = icon
                return icon
            if (self.renderer is not None and rec.kind == mc.KIND_MODEL
                    and rec.fid not in self.failed and rec.fid not in self.queued):
                self.queued.add(rec.fid)
                self.pending.append(rec.fid)
                if not self.timer.isActive():
                    self.timer.start()
            return None
        if role == Qt.UserRole:
            return rec
        return None

    def _render_one(self):
        if not self.pending:
            self.timer.stop()
            return
        fid = self.pending.pop(0)
        self.queued.discard(fid)
        if os.path.isfile(self.thumbs.path_for(fid)):
            img = False                      # rendered meanwhile (the menu action)
        else:
            try:
                img = self.renderer(fid)
            except Exception as exc:                        # noqa: BLE001
                self.failed.add(fid)
                print(f"thumbnail 0x{fid:X}: {type(exc).__name__}: {exc}")
                return
            if img is None:
                return                       # not ready; the next paint asks again
            self.thumbs.save(fid, img)
            self.rendered += 1
        self.icons.pop(fid, None)
        row = self.row_of.get(fid)
        if row is not None:
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, [Qt.DecorationRole])

    def set_records(self, records):
        self.beginResetModel()
        self.records = records
        self.row_of = {r.fid: i for i, r in enumerate(records)}
        self.pending.clear()
        self.queued.clear()
        self.endResetModel()

    def forget_icon(self, fid):
        self.icons.pop(fid, None)


class Thumbs:
    """Where thumbnails live: under the vault cache, keyed by archive stamp."""

    def __init__(self, stamp):
        self.dir = os.path.join(mc.cache_dir(), "thumbs", stamp["mft_sha256"][:16])

    def path_for(self, fid):
        return os.path.join(self.dir, f"{fid}.png")

    def save(self, fid, image):
        out = vaultpath.resolve_out(self.path_for(fid), what="a model thumbnail")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        image.save(out, "PNG")
        return out


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------

class Viewer(QMainWindow):
    def __init__(self, ar, catalog, catalog_path):
        super().__init__()
        self.ar = ar
        self.table = file_id_table(ar)
        self.catalog = catalog
        self.textures = mc.TextureCache(ar, self.table)
        self.thumbs = Thumbs(catalog.stamp)
        self.templates = None
        self.maps = None
        self.map_filter = None
        self.map_filter_name = ""
        self.current = None
        self.current_template = None
        self.setWindowTitle(f"Rurik model viewer -- {os.path.basename(ar.path)}")
        self.resize(1400, 860)

        self.gl = GLView(self)
        self.setCentralWidget(self.gl)
        self._build_left()
        self._build_right()
        self._build_menu()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        c = catalog.census()
        self.status.showMessage(
            f"{ar.path}  |  {c.get('model', 0)} models, {c.get('skel', 0)} skeletons "
            f"(no geometry), {c.get('other', 0)} other  |  catalog {catalog_path}")

    # -- panels -------------------------------------------------------------

    def _build_left(self):
        dock = QDockWidget("Browse", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        tabs = QTabWidget()

        models = QWidget()
        lay = QVBoxLayout(models)
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("file id (dec or 0x..), row N, or text")
        self.search.textChanged.connect(self.refilter)
        self.kind = QComboBox()
        self.kind.addItems(["Models", "Skeletons (no geometry)",
                            "Skeletons the wire names as creature shells",
                            "Models with collision", "Everything"])
        self.kind.currentIndexChanged.connect(self.refilter)
        row.addWidget(self.search)
        row.addWidget(self.kind)
        lay.addLayout(row)
        self.shell_rows = mc.shell_templates()
        self.wire = self._open_wire()
        self.shell_labels = self._shell_labels()
        self.list_model = CatalogModel(self.catalog.models(), self.thumbs,
                                       self.shell_labels, renderer=self._thumb_renderer)
        self.list = QListView()
        self.list.setModel(self.list_model)
        self.list.setIconSize(QSize(64, 64))
        self.list.setUniformItemSizes(True)
        self.list.selectionModel().currentChanged.connect(self.on_pick)
        lay.addWidget(self.list)
        self.count_label = QLabel()
        lay.addWidget(self.count_label)
        tabs.addTab(models, "Models")

        tpl = QWidget()
        tlay = QVBoxLayout(tpl)
        self.tpl_list = QListWidget()
        self.tpl_list.currentItemChanged.connect(self.on_pick_template)
        tlay.addWidget(self.tpl_list)
        tlay.addWidget(QLabel("content/npcs.toml rows; the body is drawn with the\n"
                              "shell's skeleton (the client's composite)"))
        tabs.addTab(tpl, "Templates")

        maps = QWidget()
        mlay = QVBoxLayout(maps)
        self.map_list = QListWidget()
        self.map_list.currentItemChanged.connect(self.on_pick_map)
        mlay.addWidget(self.map_list)
        mlay.addWidget(QLabel("content/maps.toml rows; picking one filters the\n"
                              "Models tab to the props that map references"))
        tabs.addTab(maps, "Maps")
        tabs.currentChanged.connect(self.on_tab)
        self.tabs = tabs

        dock.setWidget(tabs)
        dock.setMinimumWidth(420)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.refilter()

    def _thumb_renderer(self, fid):
        """One 96 px thumbnail for the lazy list, or None before the GL context
        exists. Raises on a model that will not build, which the model
        remembers as failed."""
        if not self.gl.isValid():
            return None
        view = mc.build_view(self.ar, self.table, fid, textures=self.textures)
        return self.gl.render_image(view, 96)

    def _open_wire(self):
        """The wire-derived shell index, or None with the reason printed."""
        try:
            idx, path, fresh = ws.open_index()
        except SystemExit as exc:                     # no live tapes in this vault
            print(f"wire shell index unavailable: {exc}")
            return None
        s = idx.summary()
        print(f"wire index: {'built' if fresh else 'loaded'} -- {s['shells']} shells, "
              f"{s['pairs']} pairs, {s['captures']} tapes ({path})")
        return idx

    def _names_for(self, shell, body=None):
        """Content-row names for a shell (or a shell+body pair): what a client
        run has already put on a nameplate; [] when no row names it."""
        out = []
        for t in self.shell_rows.get(shell, []):
            if body is None or t.get("model_id") == body:
                out.append(t["name"])
        return out

    def _shell_labels(self):
        """shell fid -> the list's `SHELL ...` tag, from the wire first."""
        labels = {}
        if self.wire is not None:
            for fid, rec in self.wire.shells.items():
                if rec.needs_body is False:
                    continue                          # it draws itself; no tag needed
                names = self._names_for(fid)
                tag = f"SHELL · {len(rec.bodies)} bodies · {len(rec.captures)} tapes"
                if names:
                    tag += " · " + ", ".join(sorted(set(names))[:2])
                labels[fid] = tag
        for fid, rows in self.shell_rows.items():
            if fid not in labels and any(t.get("model_id") is not None for t in rows):
                labels[fid] = "SHELL of " + ", ".join(t["name"] for t in rows[:2])
        return labels

    def _build_right(self):
        dock = QDockWidget("Model", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        w = QWidget()
        lay = QVBoxLayout(w)
        opt = self.gl.options

        def toggle(label, attr, checked):
            cb = QCheckBox(label)
            cb.setChecked(checked)

            def on(state, attr=attr):
                setattr(opt, attr, bool(state))
                self.gl.update()
            cb.stateChanged.connect(on)
            lay.addWidget(cb)
            return cb

        toggle("Textures", "textures", opt.textures)
        toggle("Lighting (headlight)", "lighting", opt.lighting)
        toggle("Wireframe", "wireframe", opt.wireframe)
        toggle("Collision mesh (orange)", "collision", opt.collision)
        toggle("Skeleton (green bones, magenta nodes)", "skeleton", opt.skeleton)
        toggle("Honour alpha classes (cutout test, blend)", "alpha", opt.alpha)
        row = QHBoxLayout()
        row.addWidget(QLabel("Skeleton head: draw a body the wire paired with it:"))
        self.body_box = QComboBox()
        self.body_box.addItem("(none -- skeleton only)")
        self.body_box.currentIndexChanged.connect(self.on_body)
        row.addWidget(self.body_box)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("Texture on every surface:"))
        self.slot_box = QComboBox()
        self.slot_box.addItem("material diffuse (measured rule)")
        self.slot_box.currentIndexChanged.connect(self.on_slot)
        row.addWidget(self.slot_box)
        lay.addLayout(row)

        btns = QHBoxLayout()
        b = QPushButton("Fit view")
        b.clicked.connect(self.gl.fit)
        btns.addWidget(b)
        b = QPushButton("Export to vault")
        b.clicked.connect(self.on_export)
        btns.addWidget(b)
        b = QPushButton("Screenshot…")
        b.clicked.connect(self.on_screenshot)
        btns.addWidget(b)
        lay.addLayout(btns)

        self.info = QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setLineWrapMode(QPlainTextEdit.NoWrap)
        lay.addWidget(self.info, 1)
        dock.setWidget(w)
        dock.setMinimumWidth(460)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _build_menu(self):
        m = self.menuBar().addMenu("&File")
        a = QAction("Re-scan the catalog", self)
        a.triggered.connect(self.on_rescan)
        m.addAction(a)
        a = QAction("Render thumbnails for the listed models…", self)
        a.triggered.connect(self.on_thumbnails)
        m.addAction(a)
        m.addSeparator()
        a = QAction("Quit", self)
        a.setShortcut(QKeySequence.Quit)
        a.triggered.connect(self.close)
        m.addAction(a)

    # -- browsing -----------------------------------------------------------

    def filtered_records(self):
        which = self.kind.currentIndex()
        cat = self.catalog
        if which == 0:
            recs = cat.models()
        elif which == 1:
            recs = cat.skeletons()
        elif which == 2:
            recs = [r for r in cat.skeletons() if any(f in self.shell_labels for f in r.fids)]
        elif which == 3:
            recs = [r for r in cat.models() if r.collision_count]
        else:
            recs = list(cat.records)
        if self.map_filter is not None:
            recs = [r for r in recs if any(f in self.map_filter for f in r.fids)]
        text = self.search.text().strip()
        if text:
            fid = None
            try:
                fid = int(text, 0)
            except ValueError:
                pass
            if text.lower().startswith("row "):
                try:
                    row = int(text[4:])
                    recs = [r for r in recs if r.row == row]
                except ValueError:
                    recs = []
            elif fid is not None:
                recs = [r for r in recs if fid in r.fids
                        or f"{fid:X}".lower() in f"{r.fid:X}".lower()
                        or str(fid) in str(r.fid)]
            else:
                t = text.lower()
                recs = [r for r in recs if t in f"{r.fid} 0x{r.fid:x} {r.kind} "
                        f"{r.problem or ''}".lower()]
        return sorted(recs, key=lambda r: r.fid or 0)

    def refilter(self, *_):
        recs = self.filtered_records()
        self.list_model.set_records(recs)
        suffix = f" in map {self.map_filter_name}" if self.map_filter is not None else ""
        self.count_label.setText(f"{len(recs)} listed{suffix}")

    def on_tab(self, index):
        if index == 1 and self.templates is None:
            self.templates = mc.templates()
            for t in self.templates:
                item = QListWidgetItem(f"{t['name']}   ({t['key']})  shell {t['file_id']}"
                                       + (f" body {t['model_id']}" if t['model_id'] else ""))
                item.setData(Qt.UserRole, t)
                self.tpl_list.addItem(item)
        if index == 2 and self.maps is None:
            self.setCursor(Qt.WaitCursor)
            t0 = time.time()
            try:
                self.maps, problems = mc.content_map_models(self.ar, self.table)
            finally:
                self.unsetCursor()
            self.status.showMessage(f"maps: {len(self.maps)} read in "
                                    f"{time.time() - t0:.1f} s through the map index "
                                    f"cache ({mc.map_index_path(self.ar)})")
            item = QListWidgetItem("(all models)")
            item.setData(Qt.UserRole, None)
            self.map_list.addItem(item)
            for key, (name, ids) in sorted(self.maps.items(), key=lambda kv: kv[1][0]):
                item = QListWidgetItem(f"{name}  ({key}) -- {len(ids)} models")
                item.setData(Qt.UserRole, (key, name, ids))
                self.map_list.addItem(item)
            for key, why in problems:
                item = QListWidgetItem(f"map {key}: could not read -- {why}")
                item.setFlags(Qt.NoItemFlags)
                self.map_list.addItem(item)

    def on_pick(self, current, _previous):
        if not current.isValid():
            return
        rec = self.list_model.data(current, Qt.UserRole)
        if rec.fid is None:
            return
        self.load(rec.fid)

    def on_pick_template(self, item, _prev):
        if item is None:
            return
        t = item.data(Qt.UserRole)
        self.setCursor(Qt.WaitCursor)
        try:
            r = mc.resolve_template(self.ar, self.table, t)
        except Exception as exc:                            # noqa: BLE001
            self.unsetCursor()
            QMessageBox.warning(self, "template", f"{t['key']}: {type(exc).__name__}: {exc}")
            return
        self.unsetCursor()
        self.current_template = (t, r)
        if r["draw"] is None:
            self.info.setPlainText(
                f"{t['name']} ({t['key']})\n\nshell {t['file_id']} is COMPOSITED and the "
                f"row declares no body:\nthere is no geometry to draw. On the client this "
                f"is the solid white box (RUN-PARADE §4).\n\n{r}")
            return
        self.load(r["draw"], skeleton_fid=t["file_id"], header=(
            f"TEMPLATE {t['name']} ({t['key']}): shell {t['file_id']}, body "
            f"{t['model_id']}, needs_body={r['needs_body']}, closed={r['closed']}, "
            f"roles {r['roles']}"))

    def on_pick_map(self, item, _prev):
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if data is None:
            self.map_filter = None
        else:
            key, name, ids = data
            self.map_filter = set(ids)
            self.map_filter_name = f"{name} ({key})"
        self.refilter()

    def load(self, fid, skeleton_fid=None, header=None):
        self.setCursor(Qt.WaitCursor)
        t0 = time.time()
        try:
            view = mc.build_view(self.ar, self.table, fid, textures=self.textures,
                                 skeleton_fid=skeleton_fid)
        except Exception as exc:                            # noqa: BLE001
            self.unsetCursor()
            self.info.setPlainText(f"file {fid} (0x{fid:X}) did not build:\n"
                                   f"{type(exc).__name__}: {exc}")
            return
        dt = time.time() - t0
        self.current = view
        self.gl.set_view(view)
        self.unsetCursor()
        text = mc._describe(view)
        if header:
            text = header + "\n\n" + text
        if view.textures:
            text += "\n  textures " + ", ".join(
                f"0x{t.fid:X} {t.width}x{t.height} {t.kind} {t.alpha}"
                for t in view.textures.values())
        for sub in view.submeshes:
            if sub.layers:
                text += f"\n  sub {sub.index} layers: " + ", ".join(
                    f"tex {l['texpath']} uv {l['uv']} flags 0x{l['flags']:X}"
                    for l in sub.layers)
        if view.sequences:
            text += "\n  sequences (start..end s):"
            for i, s in enumerate(view.sequences[:40]):
                text += (f"\n    {i:3} {s['start'] / 1e5:8.3f}..{s['end'] / 1e5:8.3f}"
                         f"  lo/hi {s['lo']}/{s['hi']}")
            if len(view.sequences) > 40:
                text += f"\n    ... {len(view.sequences) - 40} more"
        text += f"\n\n  built in {dt:.2f} s"
        self.info.setPlainText(text)
        self.body_box.blockSignals(True)
        while self.body_box.count() > 1:
            self.body_box.removeItem(1)
        if not view.submeshes and view.skeleton is not None and skeleton_fid is None:
            rec = self.wire.shells.get(fid) if self.wire is not None else None
            if rec is not None:
                # most-seen first; the count is how often the wire dressed
                # this shell with that body, across how many tapes
                for body, ss in sorted(rec.bodies.items(), key=lambda kv: -len(kv[1])):
                    names = self._names_for(fid, body)
                    caps = len({x["capture"] for x in ss})
                    label = f"body {body}  · {len(ss)} sightings / {caps} tapes"
                    if names:
                        label += "  = " + ", ".join(sorted(set(names))[:2])
                    self.body_box.addItem(label, body)
                text += "\n\n" + rec.describe(lambda b: ", ".join(self._names_for(fid, b)))
            else:
                bodies = {}
                for t in self.shell_rows.get(fid, []):
                    if t["model_id"] is not None:
                        bodies.setdefault(t["model_id"], []).append(t["name"])
                for body, names in sorted(bodies.items()):
                    self.body_box.addItem(f"body {body}  ({', '.join(names[:3])})", body)
                if not bodies:
                    self.body_box.addItem("(no tape ever dressed this skeleton -- unknown: "
                                          "an unspawned shell or an anim file)")
            self.info.setPlainText(text)
        self.body_box.setCurrentIndex(0)
        self.body_box.blockSignals(False)
        self.slot_box.blockSignals(True)
        while self.slot_box.count() > 1:
            self.slot_box.removeItem(1)
        for i, t in enumerate(view.texture_ids):
            self.slot_box.addItem(f"FA5 slot {i}: " + ("null" if t is None else f"0x{t:X}"))
        self.slot_box.setCurrentIndex(0)
        self.gl.options.force_slot = None
        self.slot_box.blockSignals(False)
        self.status.showMessage(f"0x{fid:X} ({fid}): {view.vertices} v, {view.triangles} "
                                f"tri, {len(view.textures)} texture(s) -- {dt:.2f} s")

    def on_body(self, index):
        body = self.body_box.itemData(index) if index > 0 else None
        if body is None or self.current is None:
            return
        shell = self.current.fid
        self.load(body, skeleton_fid=shell, header=(
            f"BODY {body} drawn under skeleton {shell}: the pairing is the WIRE's "
            f"(0x0056 + 0x0057 in a capture, via content/npcs.toml), not the archive's"))

    def on_slot(self, index):
        if index <= 0:
            self.gl.options.force_slot = None
        else:
            slot = index - 1
            view = self.current
            fid = view.texture_ids[slot] if view else None
            if fid is not None and fid not in view.textures:
                try:
                    view.textures[fid] = self.textures.get(fid)
                    self.gl.set_view(view)
                except Exception as exc:                    # noqa: BLE001
                    self.status.showMessage(f"slot {slot}: {type(exc).__name__}: {exc}")
            self.gl.options.force_slot = slot
        self.gl.update()

    # -- actions ------------------------------------------------------------

    def on_export(self):
        if self.current is None:
            return
        import modelexport
        import unitexport
        fid = self.current.fid
        try:
            if self.current.skeleton is not None and self.current.skeleton_from == fid \
                    and self.current.submeshes:
                path = unitexport.export_unit(fid, self.ar, table=self.table)
            elif self.current.submeshes:
                path = modelexport.export_file_id(fid, self.ar, table=self.table)
            else:
                QMessageBox.information(self, "export", "A shell without geometry has "
                                        "nothing to export; pick its body.")
                return
        except Exception as exc:                            # noqa: BLE001
            QMessageBox.warning(self, "export", f"{type(exc).__name__}: {exc}")
            return
        self.status.showMessage(f"exported {path}")

    def on_screenshot(self):
        if self.current is None:
            return
        start = vaultpath.vault_path("research", "modelviewer")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save screenshot", os.path.join(start, f"model_{self.current.fid}.png"),
            "PNG (*.png)")
        if not path:
            return
        try:
            out = vaultpath.resolve_out(path, what="a model screenshot")
        except ValueError as exc:
            QMessageBox.warning(self, "refused", str(exc))
            return
        os.makedirs(os.path.dirname(out), exist_ok=True)
        self.gl.grabFramebuffer().save(out, "PNG")
        self.status.showMessage(f"saved {out}")

    def on_rescan(self):
        dlg = QProgressDialog("Scanning every model head…", "Cancel", 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.show()

        def progress(n, total):
            dlg.setValue(int(100 * n / max(total, 1)))
            QApplication.processEvents()
        cat, path, _ = mc.open_catalog(self.ar, progress=progress, rescan=True)
        dlg.close()
        self.catalog = cat
        self.refilter()
        self.status.showMessage(f"re-scanned {cat.scanned_rows} heads -> {path}")

    def on_thumbnails(self):
        recs = [r for r in self.list_model.records if r.kind == mc.KIND_MODEL
                and not os.path.isfile(self.thumbs.path_for(r.fid))]
        if not recs:
            self.status.showMessage("every listed model already has a thumbnail")
            return
        dlg = QProgressDialog(f"Rendering {len(recs)} thumbnails…", "Stop", 0, len(recs), self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.show()
        done = failed = 0
        for i, rec in enumerate(recs):
            if dlg.wasCanceled():
                break
            dlg.setValue(i)
            dlg.setLabelText(f"{i + 1}/{len(recs)}  0x{rec.fid:X}")
            QApplication.processEvents()
            try:
                view = mc.build_view(self.ar, self.table, rec.fid, textures=self.textures)
                img = self.gl.render_image(view, 128)
                self.thumbs.save(rec.fid, img)
                self.list_model.forget_icon(rec.fid)
                done += 1
            except Exception as exc:                        # noqa: BLE001
                failed += 1
                print(f"thumbnail 0x{rec.fid:X}: {type(exc).__name__}: {exc}")
        dlg.close()
        self.list_model.layoutChanged.emit()
        self.status.showMessage(f"thumbnails: {done} rendered, {failed} failed -> "
                                f"{self.thumbs.dir}")

    def select_fid(self, fid):
        rec = self.catalog.by_fid.get(fid)
        if rec is None:
            self.load(fid)
            return
        for i, r in enumerate(self.list_model.records):
            if r is rec:
                self.list.setCurrentIndex(self.list_model.index(i))
                return
        self.load(fid)


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def open_catalog_with_progress(ar, app):
    dlg = None
    t0 = time.time()

    def progress(n, total):
        nonlocal dlg
        if dlg is None:
            dlg = QProgressDialog("First run: scanning every model head in the "
                                  "archive (about 15 s)…", None, 0, 100)
            dlg.show()
        dlg.setValue(int(100 * n / max(total, 1)))
        app.processEvents()
    cat, path, fresh = mc.open_catalog(ar, progress=progress)
    if dlg is not None:
        dlg.close()
    print(f"catalog: {cat.scanned_rows} heads {'scanned' if fresh else 'loaded'} in "
          f"{time.time() - t0:.1f} s ({path})")
    return cat, path


def shot(win, args):
    """`--shot`: one offscreen frame of the requested model, then exit."""
    fid = int(args.file_id, 0) if args.file_id else None
    skel = int(args.skeleton_from, 0) if args.skeleton_from else None
    header = None
    if args.template:
        t = next((t for t in mc.templates() if t["key"] == args.template), None)
        if t is None:
            sys.exit(f"no template {args.template!r}")
        r = mc.resolve_template(win.ar, win.table, t)
        if r["draw"] is None:
            sys.exit(f"template {args.template} draws nothing (composited, no body)")
        fid, skel = r["draw"], t["file_id"]
    if fid is None:
        sys.exit("--shot needs --file-id or --template")
    out = vaultpath.resolve_out(args.shot, what="a model screenshot")
    view = mc.build_view(win.ar, win.table, fid, textures=win.textures, skeleton_fid=skel)
    img = win.gl.render_image(view, args.size)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    ok = img.save(out, "PNG")
    # the measurement a caller can check: how much of the frame the body covers
    covered = sum(1 for y in range(img.height()) for x in range(img.width())
                  if img.pixelColor(x, y).name() != QColor.fromRgbF(*CLEAR[:3]).name())
    print(f"shot 0x{fid:X}" + (f" + skeleton 0x{skel:X}" if skel else "")
          + f" -> {out} ({'ok' if ok else 'FAILED'}); {view.vertices} v, "
          f"{view.triangles} tri, {len(view.textures)} tex; coverage "
          f"{covered / (img.width() * img.height()):.4f}")
    print(mc._describe(view))
    return 0 if ok else 1


def smoke(win, app, out_dir):
    """`--smoke`: drive every panel once with the window up, then exit.

    Not a suite test (PySide6 is not bare-machine); a hand-run check that the
    tabs, the template and map joins, the list filters, the on-screen frame
    and the thumbnail path all work after a change. Prints one line per step
    and exits non-zero on the first failure. `out_dir` receives the on-screen
    grab and three thumbnails and must be outside the working tree.
    """
    fails = []

    def step(cond, label):
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
        if not cond:
            fails.append(label)
        app.processEvents()

    out_dir = vaultpath.resolve_out(out_dir, what="smoke output")
    os.makedirs(out_dir, exist_ok=True)
    n_models = len(win.catalog.models())
    step(win.list_model.rowCount() == n_models, f"Models tab lists every model ({n_models})")

    win.tabs.setCurrentIndex(1)
    app.processEvents()
    step(win.tpl_list.count() >= 50, f"Templates tab lists {win.tpl_list.count()} rows")
    for i in range(win.tpl_list.count()):
        if win.tpl_list.item(i).data(Qt.UserRole)["key"] == "hatcher":
            win.tpl_list.setCurrentRow(i)
            break
    app.processEvents()
    step(win.current is not None and win.current.fid == 116703
         and win.current.skeleton is not None and len(win.current.skeleton) == 86,
         "picking the hatcher template draws body 116703 under the 86-node shell skeleton")
    step(win.slot_box.count() == 4, "the slot override lists the body's 3 FA5 slots")
    win.slot_box.setCurrentIndex(1)
    app.processEvents()
    step(win.gl.options.force_slot == 0 and 0x2005 in win.current.textures,
         "forcing slot 0 decodes and binds its texture")
    win.slot_box.setCurrentIndex(0)

    win.tabs.setCurrentIndex(2)
    t0 = time.time()
    app.processEvents()
    maps_secs = time.time() - t0
    step(win.maps is not None and "449" in win.maps,
         f"Maps tab reads the content maps ({maps_secs:.1f} s; warm through the "
         f"map index cache, cold ~20 s)")
    for i in range(win.map_list.count()):
        d = win.map_list.item(i).data(Qt.UserRole)
        if d and d[0] == "449":
            win.map_list.setCurrentRow(i)
            break
    app.processEvents()
    listed = win.list_model.rowCount()
    step(0 < listed <= len(win.maps["449"][1]),
         f"picking Kamadan filters the Models tab to {listed} of its "
         f"{len(win.maps['449'][1])} referenced ids")
    win.map_list.setCurrentRow(0)
    app.processEvents()
    step(win.list_model.rowCount() == n_models, "'(all models)' clears the map filter")

    win.tabs.setCurrentIndex(0)
    win.search.setText("116366")
    app.processEvents()
    step(win.list_model.rowCount() == 1, "searching a decimal id lists exactly one row")
    win.list.setCurrentIndex(win.list_model.index(0))
    app.processEvents()
    step(win.current is not None and win.current.fid == 116366
         and len(win.current.skeleton or ()) == 20, "selecting it loads the worm with its skeleton")
    win.search.setText("")
    win.kind.setCurrentIndex(1)
    app.processEvents()
    step(win.list_model.rowCount() == len(win.catalog.skeletons()),
         f"the skeletons filter lists {win.list_model.rowCount()} geometry-less heads")
    win.list.setCurrentIndex(win.list_model.index(0))
    app.processEvents()
    step(win.current is not None and not win.current.submeshes
         and win.current.composited is True,
         "a skeleton head loads with no geometry, flagged composited, and draws")
    win.kind.setCurrentIndex(2)
    app.processEvents()
    named = win.list_model.rowCount()
    dressed = sum(1 for r in win.wire.shells.values() if r.needs_body) if win.wire else 0
    step(win.wire is not None and named == dressed >= 80,
         f"the wire-named filter lists {named} skeleton heads the tapes dressed "
         f"(index: {dressed} dressed shells)")
    win.search.setText(str(116228))
    app.processEvents()
    win.list.setCurrentIndex(win.list_model.index(0))
    app.processEvents()
    want = len(win.wire.shells[116228].bodies) if win.wire else 0
    step(win.current is not None and win.current.fid == 116228
         and win.body_box.count() - 1 == want >= 30,
         f"the hatcher shell offers {win.body_box.count() - 1} wire-paired bodies "
         f"(index says {want}), most-seen first")
    step("Hatcher" in win.body_box.itemText(1) or any(
        "Hatcher" in win.body_box.itemText(i) for i in range(1, win.body_box.count())),
         "a content-named body carries its nameplate text in the picker")
    win.body_box.setCurrentIndex(1)
    app.processEvents()
    step(win.current is not None and win.current.submeshes
         and win.current.skeleton_from == 116228,
         f"picking one draws body {win.current.fid} under the shell's skeleton")
    win.search.setText("")
    win.kind.setCurrentIndex(0)
    win.search.setText("0x1C7DF")
    app.processEvents()
    win.list.setCurrentIndex(win.list_model.index(0))
    app.processEvents()
    app.processEvents()
    img = win.gl.grabFramebuffer()
    path = os.path.join(out_dir, "smoke_screen.png")
    img.save(path, "PNG")
    bg = QColor.fromRgbF(*CLEAR[:3]).name()
    covered = sum(1 for y in range(0, img.height(), 4) for x in range(0, img.width(), 4)
                  if img.pixelColor(x, y).name() != bg)
    frac = covered / ((img.width() // 4) * (img.height() // 4))
    step(0.02 < frac < 0.9, f"the on-screen frame draws the hatcher body: coverage {frac:.3f} -> {path}")

    thumbs = Thumbs(win.catalog.stamp)
    thumbs.dir = os.path.join(out_dir, "thumbs")
    done = 0
    for rec in win.catalog.models()[:3]:
        view = mc.build_view(win.ar, win.table, rec.fid, textures=win.textures)
        thumbs.save(rec.fid, win.gl.render_image(view, 96))
        done += os.path.isfile(thumbs.path_for(rec.fid))
    step(done == 3, f"three thumbnails rendered offscreen into {thumbs.dir}")

    # LAZY thumbnails: point the list's cache at an empty directory outside
    # the tree, show the Models tab, and let the event loop run -- the rows in
    # view are queued by their own paint and rendered one per turn. Then
    # scroll to the end and the rows there arrive too, without a menu action.
    lazy = Thumbs(win.catalog.stamp)
    lazy.dir = os.path.join(out_dir, "thumbs-lazy")
    win.list_model.thumbs = lazy
    win.list_model.icons.clear()
    win.list_model.failed.clear()
    win.search.setText("")
    win.kind.setCurrentIndex(0)
    app.processEvents()
    win.list_model.set_records(win.filtered_records())
    deadline = time.time() + 30
    while time.time() < deadline and (len(os.listdir(lazy.dir)) < 3
                                      if os.path.isdir(lazy.dir) else True):
        app.processEvents()
    first_batch = len(os.listdir(lazy.dir)) if os.path.isdir(lazy.dir) else 0
    step(first_batch >= 3 and win.list_model.rendered >= 3,
         f"the Models tab renders thumbnails for the rows in view on its own: "
         f"{first_batch} PNGs in {lazy.dir} without the menu action")
    win.list.scrollToBottom()
    before = win.list_model.rendered
    deadline = time.time() + 30
    while time.time() < deadline and win.list_model.rendered < before + 3:
        app.processEvents()
    step(win.list_model.rendered >= before + 3,
         f"scrolling to the end queues the rows that came into view: "
         f"{win.list_model.rendered - before} more rendered")
    while win.list_model.pending and time.time() < deadline:
        app.processEvents()
    print(f"smoke: {len(fails)} failure(s)")
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None)
    ap.add_argument("--skeleton-from", default=None,
                    help="draw this shell's skeleton over --file-id's body")
    ap.add_argument("--template", default=None, help="a content/npcs.toml row key")
    ap.add_argument("--shot", default=None, metavar="PNG",
                    help="render one frame offscreen to PNG and exit")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--smoke", default=None, metavar="DIR",
                    help="drive every panel once, write a screen grab and three "
                         "thumbnails into DIR (outside the tree), exit")
    args = ap.parse_args(argv)

    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication(sys.argv[:1])
    if not os.path.isfile(args.dat):
        sys.exit(f"no archive at {args.dat}; pass --dat or set RURIK_DAT")
    ar = Archive(args.dat)
    cat, path = open_catalog_with_progress(ar, app)
    win = Viewer(ar, cat, path)
    win.show()
    # the GL context exists only once the widget has been exposed; wait for it
    deadline = time.time() + 10
    while not win.gl.isValid() and time.time() < deadline:
        app.processEvents()
    if not win.gl.isValid():
        sys.exit("the OpenGL widget never acquired a context")
    if args.shot:
        rc = shot(win, args)
        win.close()
        return rc
    if args.smoke:
        rc = smoke(win, app, args.smoke)
        win.close()
        return rc
    if args.template:
        win.tabs.setCurrentIndex(1)
        for i in range(win.tpl_list.count()):
            if win.tpl_list.item(i).data(Qt.UserRole)["key"] == args.template:
                win.tpl_list.setCurrentRow(i)
                break
    elif args.file_id:
        win.select_fid(int(args.file_id, 0))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
