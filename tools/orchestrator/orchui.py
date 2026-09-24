r"""Widgets and helpers for the run orchestrator's window. PySide6; no Rurik
knowledge -- the tokens are `orchtheme.py`'s, the facts are the compiler's.

Every helper stamps a `role` (and for a chip a `kind`) property and lets the
stylesheet do the rest; nothing here calls setStyleSheet on a widget, because a
widget-level sheet out-ranks the application's whatever its specificity, and a
selector-less one cascades into every child. The patterns are Dream-World-IX's
(`ff9mapkit/workspace/widgets.py`), rewritten small: `card()` is its
`section()`, `WheelGuard` its wheel guard, the icons its inline-SVG family --
drawn fresh here, so no one else's glyphs are copied.
"""
import os
import tempfile

import orchtheme

from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QSize, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QImage, QPainter,
                           QPalette, QPixmap, QWheelEvent)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QFrame,
                               QHBoxLayout, QLabel, QListWidget, QPushButton, QStyle,
                               QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout,
                               QWidget)

# The palette in force, derived; set by apply_theme(). Painting code (the
# skill delegate, the log's registers) reads colours from here, never literals.
PAL = orchtheme.derive(orchtheme.DARK)
THEME = "dark"


# ---------------------------------------------------------------- theme

def resolve_theme(app, requested="auto"):
    """'dark' or 'light'. 'auto' follows the OS the way the stock style did."""
    if requested in orchtheme.PALETTES:
        return requested
    try:
        scheme = app.styleHints().colorScheme()
        return "light" if scheme == Qt.ColorScheme.Light else "dark"
    except AttributeError:                                  # Qt < 6.5
        return "dark"


def apply_theme(app, requested="auto"):
    """Fusion + a palette from the tokens + the sheet. Returns the theme name.

    Fusion, not the native windows11 style: that style draws its own rounded
    fills and a sheet over it half-applies. The QPalette covers what QSS does
    not reach (the completer's popup, a message box's body, text selection)."""
    global PAL, THEME
    THEME = resolve_theme(app, requested)
    PAL = orchtheme.derive(orchtheme.PALETTES[THEME])
    app.setStyle("Fusion")
    pal = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.WindowText, "text"),
                      (QPalette.Base, "field"), (QPalette.AlternateBase, "surface"),
                      (QPalette.Text, "text"), (QPalette.Button, "surface_btn"),
                      (QPalette.ButtonText, "text"), (QPalette.ToolTipBase, "surface_btn"),
                      (QPalette.ToolTipText, "text"), (QPalette.Highlight, "selection_bg"),
                      (QPalette.HighlightedText, "text"), (QPalette.PlaceholderText, "muted"),
                      (QPalette.Link, "focus"), (QPalette.Mid, "border"),
                      (QPalette.Dark, "border_shade"), (QPalette.Light, "border_lit")):
        pal.setColor(role, QColor(PAL[key]))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(PAL["disabled_fg"]))
    app.setPalette(pal)
    font = QFont("Segoe UI")
    font.setPixelSize(orchtheme.TYPE["body"])
    app.setFont(font)
    assets = orchtheme.write_assets(orchtheme.PALETTES[THEME],
                                    os.path.join(tempfile.gettempdir(), "rurik-orchestrator"))
    app.setStyleSheet(orchtheme.qss(orchtheme.PALETTES[THEME], assets))
    install_wheel_guard(app)
    return THEME


def repolish(w):
    """A selector-affecting property changed: make Qt re-read the sheet. Without
    this a setProperty() changes nothing on screen."""
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def mono_font(px=None):
    f = QFont("Cascadia Mono")
    f.setStyleHint(QFont.Monospace)
    f.setFamilies(["Cascadia Mono", "Cascadia Code", "Consolas"])
    f.setPixelSize(px or orchtheme.TYPE["mono"])
    return f


# ---------------------------------------------------------------- labels

def role_label(text="", role="caption", *, wrap=False, tip=None):
    lab = QLabel(text)
    lab.setProperty("role", role)
    lab.setWordWrap(wrap)
    if tip:
        lab.setToolTip(tip)
    if text:
        lab.setAccessibleName(text)
    return lab


def caption(text, *, tip=None):
    """A sentence UNDER a control, never inside it (a checkbox does not wrap, so
    a sentence in its label becomes its minimum width)."""
    return role_label(text, "caption", wrap=True, tip=tip)


def overline(text):
    """A small tracked-caps section name. Qt's QSS has no text-transform, so
    the case is set here."""
    lab = role_label(text.upper(), "overline")
    f = lab.font()
    f.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
    lab.setFont(f)
    lab.setAccessibleName(text)
    return lab


def chip(text="", kind="info", *, tip=None):
    lab = role_label(text, "chip", tip=tip)
    lab.setProperty("kind", kind)
    lab.setAccessibleName(f"{kind}: {text}")
    return lab


def set_chip(lab, text, kind=None, *, tip=None):
    """Change a chip's words and (optionally) its kind. Fill and ink travel
    together in the sheet, so a kind is the only colour lever there is."""
    lab.setText(text)
    if kind and lab.property("kind") != kind:
        lab.setProperty("kind", kind)
        repolish(lab)
    if tip is not None:
        lab.setToolTip(tip)
    lab.setAccessibleName(f"{lab.property('kind')}: {text}")


# ---------------------------------------------------------------- cards

def card(title=None, *, trailing=None, margins=(16, 12, 16, 16), spacing=10):
    """A QFrame card, the replacement for QGroupBox: QSS can colour a group
    box's title and nothing else (no size, no weight), and the title sits ON
    the border. Here the title is a real label inside the fill, with real
    padding. Returns the frame; fill `frame.body` (a QVBoxLayout)."""
    box = QFrame()
    box.setProperty("role", "card")
    outer = QVBoxLayout(box)
    outer.setContentsMargins(*margins)
    outer.setSpacing(spacing)
    box.title_label = None
    if title or trailing is not None:
        head = QHBoxLayout()
        head.setSpacing(8)
        if title:
            box.title_label = overline(title)
            head.addWidget(box.title_label)
        head.addStretch(1)
        if trailing is not None:
            head.addWidget(trailing)
        outer.addLayout(head)
    box.body = QVBoxLayout()
    box.body.setContentsMargins(0, 0, 0, 0)
    box.body.setSpacing(8)
    outer.addLayout(box.body)
    if title:
        box.setAccessibleName(title)
    return box


def button(text, role=None, *, icon=None, tip=None, name=None):
    b = QPushButton(text)
    if role:
        b.setProperty("role", role)
    if tip:
        b.setToolTip(tip)
    b.setAccessibleName(name or text.rstrip("…. "))
    if icon:
        b.setIcon(tinted_icon(icon, role))
        b.setIconSize(QSize(16, 16))
    return b


def set_button_icon(b, icon):
    b.setIcon(tinted_icon(icon, b.property("role")))


# ---------------------------------------------------------------- icons
#
# 24x24 strokes, drawn for this file (simple geometry -- nobody's icon set).
# QtSvg does not resolve currentColor, so the ink is substituted as text.

_ICONS = {
    "play": '<path d="M8 5.5v13l10.5-6.5z" fill="INK" stroke="none"/>',
    "stop": '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5" fill="INK" stroke="none"/>',
    "compile": '<path d="M4.5 7h9M4.5 12h9M4.5 17h5"/><path d="M14.5 16.5l2.5 2.5 4.5-4.5"/>',
    "open": '<path d="M3.5 7.5a2 2 0 0 1 2-2h3.6l2 2h7.4a2 2 0 0 1 2 2v7.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    "save": ('<path d="M5.5 4.5h10.5l3.5 3.5v10.5a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1z"/>'
             '<path d="M8.5 4.5v4.5h6.5v-4.5M8 19.5v-5.5h8v5.5"/>'),
    "reset": '<path d="M5 12a7 7 0 1 0 2.1-5"/><path d="M5 4.5v4h4"/>',
    "plus": '<path d="M12 5.5v13M5.5 12h13"/>',
    "remove": '<path d="M7 7l10 10M17 7 7 17"/>',
    "trash": '<path d="M5 7h14M10 7V5h4v2M7 7l1 12.5h8L17 7"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M15.5 15.5 19.5 19.5"/>',
}
_PIX = {}


def icon_pixmap(name, ink, size=16, dpr=None):
    if dpr is None:
        app = QApplication.instance()
        dpr = app.devicePixelRatio() if app else 1.0
    key = (name, ink.lower(), size, dpr)
    if key in _PIX:
        return _PIX[key]
    body = _ICONS[name].replace("INK", ink)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{ink}" stroke-width="2" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    side = max(1, round(size * dpr))
    img = QImage(side, side, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(svg.encode("utf-8")).render(p)
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    _PIX[key] = pm
    return pm


def tinted_icon(name, role=None):
    """An icon whose ink matches the button tier it sits on, with its own
    disabled ink (an icon that stays bright on a dead button lies)."""
    ink = {"primary": PAL["accent_fg"], "danger": PAL["error_text"]}.get(role, PAL["text"])
    ic = QIcon()
    ic.addPixmap(icon_pixmap(name, ink), QIcon.Normal)
    ic.addPixmap(icon_pixmap(name, PAL["disabled_fg"]), QIcon.Disabled)
    return ic


# ---------------------------------------------------------------- wheel guard

class WheelGuard(QObject):
    """A hovered combo or spin box changes value under the wheel even without
    focus, so scrolling a table of them edits whatever the cursor crosses.
    Unfocused ones pass the wheel to their parent instead (the table or the
    scroll area scrolls); a focused one still takes it."""
    GUARDED = (QComboBox, QAbstractSpinBox)

    def eventFilter(self, obj, ev):
        if (ev.type() == QEvent.Wheel and isinstance(obj, self.GUARDED)
                and not obj.hasFocus()):
            parent = obj.parentWidget()
            if parent is not None:
                pos = obj.mapTo(parent, ev.position().toPoint())
                QApplication.sendEvent(parent, QWheelEvent(
                    QPointF(pos), ev.globalPosition(), ev.pixelDelta(), ev.angleDelta(),
                    ev.buttons(), ev.modifiers(), ev.phase(), ev.inverted()))
            return True
        return False


def install_wheel_guard(app):
    guard = app.findChild(WheelGuard)
    if guard is None:
        guard = WheelGuard(app)
        app.installEventFilter(guard)
    return guard


# ---------------------------------------------------------------- lists

class PlaceholderList(QListWidget):
    """A list that says so when a filter hides every row, instead of a void."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.placeholder = placeholder

    def visible_count(self):
        return sum(1 for i in range(self.count()) if not self.item(i).isHidden())

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if self.placeholder and self.visible_count() == 0:
            p = QPainter(self.viewport())
            p.setPen(QColor(PAL["muted"]))
            p.drawText(self.viewport().rect().adjusted(24, 24, -24, -24),
                       Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.placeholder)


# Data roles the skill delegate reads (the item's own text stays the full
# label: it is what the filter matches and what a screen reader says).
ROLE_ID = Qt.UserRole
ROLE_PARTS = Qt.UserRole + 1

GRADE_TEXT = {"hand": "modelled", "label": "label"}


class SkillDelegate(QStyledItemDelegate):
    """One skill row: the name at body size, then its id, profession and
    attribute in a quiet mono, then a small grade pill at the right edge --
    instead of all of it jammed into one string with a trailing asterisk."""

    PAD_V = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.meta_font = mono_font(orchtheme.TYPE["caption"])
        self.pill_font = QFont("Segoe UI")
        self.pill_font.setPixelSize(orchtheme.TYPE["caption"] - 1)
        self.pill_font.setWeight(QFont.DemiBold)

    def sizeHint(self, opt, idx):
        base = super().sizeHint(opt, idx)
        return QSize(base.width(), max(base.height(), QFontMetrics(opt.font).height() + self.PAD_V))

    def paint(self, p, opt, idx):
        parts = idx.data(ROLE_PARTS)
        if not parts:
            return super().paint(p, opt, idx)
        name, meta, grade = parts
        o = QStyleOptionViewItem(opt)
        self.initStyleOption(o, idx)
        o.text = ""
        widget = o.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, o, p, widget)
        r = style.subElementRect(QStyle.SE_ItemViewItemText, o, widget).adjusted(4, 0, -8, 0)
        p.save()
        # the grade pill first, so the text knows where to stop
        right = r.right()
        if grade in GRADE_TEXT:
            kind = "good" if grade == "hand" else "info"
            label = GRADE_TEXT[grade]
            fm = QFontMetrics(self.pill_font)
            w, h = fm.horizontalAdvance(label) + 14, fm.height() + 4
            pill = QRect(right - w, r.center().y() - h // 2, w, h)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QColor(PAL[f"chip_{kind}_edge"]))
            p.setBrush(QColor(PAL[f"chip_{kind}_bg"]))
            p.drawRoundedRect(pill.adjusted(0, 0, -1, -1), h / 2, h / 2)
            p.setFont(self.pill_font)
            p.setPen(QColor(PAL[f"chip_{kind}_fg"]))
            p.drawText(pill, Qt.AlignCenter, label)
            right = pill.left() - 10
        fm = QFontMetrics(o.font)
        p.setFont(o.font)
        p.setPen(QColor(PAL["text"] if o.state & QStyle.State_Enabled else PAL["disabled_fg"]))
        name_rect = QRect(r.left(), r.top(), max(0, right - r.left()), r.height())
        shown = fm.elidedText(name, Qt.ElideRight, name_rect.width())
        p.drawText(name_rect, Qt.AlignVCenter | Qt.AlignLeft, shown)
        x = r.left() + fm.horizontalAdvance(shown) + 12
        if meta and x < right:
            p.setFont(self.meta_font)
            p.setPen(QColor(PAL["muted"]))
            mfm = QFontMetrics(self.meta_font)
            meta_rect = QRect(x, r.top(), right - x, r.height())
            p.drawText(meta_rect, Qt.AlignVCenter | Qt.AlignLeft,
                       mfm.elidedText(meta, Qt.ElideRight, meta_rect.width()))
        p.restore()


# ---------------------------------------------------------------- misc

def centered(widget):
    """A widget centred in a transparent host (a checkbox in a table cell)."""
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addStretch(1)
    lay.addWidget(widget)
    lay.addStretch(1)
    return host


def page_layout(widget, margins=(16, 16, 16, 12), spacing=12):
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay
