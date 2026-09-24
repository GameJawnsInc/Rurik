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
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import orchtheme  # noqa: E402  (tools/orchestrator, stdlib)

from PySide6.QtCore import QEvent, QMimeData, QObject, QPoint, QRect, QSize, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QDrag, QFont, QFontMetrics, QIcon, QImage,  # noqa: E402
                           QPainter, QPalette, QPixmap)
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QFrame,  # noqa: E402
                               QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
                               QPushButton, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                               QVBoxLayout, QWidget)

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
    not reach -- a message box's body, a native dialog's controls, text
    selection in a widget no rule names."""
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
            # as tall as a chip, so two cards side by side -- one with a chip in
            # its head, one without -- start their bodies on the same line
            box.title_label.setMinimumHeight(chip("0").sizeHint().height())
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
    For an unfocused one the event is IGNORED and eaten here: Qt then carries
    the original, spontaneous wheel on up the parent chain to whatever scrolls
    -- a table's viewport, a page's scroll area, at any depth. A focused one
    still takes it.

    Dream-World-IX's guard is exactly this. The first cut here forwarded a new
    event to the parent instead, and Qt never propagates a synthesized wheel,
    so the hostile pages stopped scrolling wherever the pointer crossed a combo.

    The second cut asked hasFocus() and nothing else, and in an ACTIVE window
    that is always True: a combo or spin box is born WheelFocus, and
    QApplication::notify gives the hovered widget focus by that policy BEFORE
    any application filter sees the wheel. So every guarded widget is moved to
    StrongFocus (Tab and click, no wheel) as it is polished -- the Polish event
    reaches this filter for the ones add_member and add_group build later too
    -- and a wheel can no longer create the focus this filter then asks about."""
    GUARDED = (QComboBox, QAbstractSpinBox)

    def eventFilter(self, obj, ev):
        kind = ev.type()
        if kind == QEvent.Polish and isinstance(obj, self.GUARDED) \
                and obj.focusPolicy() == Qt.WheelFocus:
            obj.setFocusPolicy(Qt.StrongFocus)
        elif kind == QEvent.Wheel and isinstance(obj, self.GUARDED) and not obj.hasFocus():
            ev.ignore()
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


# Data roles the delegates read (the item's own text stays the full line: it
# is what the filter matches and what a screen reader says).
ROLE_ID = Qt.UserRole
ROLE_PARTS = Qt.UserRole + 1
ROLE_ROSTER = Qt.UserRole + 2                   # (name, facts) of a group's roster row
ROLE_FULL = Qt.UserRole + 3                     # a Picker row's label whole, where the shown one is elided
ROLE_SLOT = Qt.UserRole + 4                     # a Skill bar cell's (slot index, line 2, off-profession abbreviation)

GRADE_TEXT = {"hand": "modelled", "label": "label"}
# A skill dragged between the Skill bar's strip and its library: 'sid' from
# the library, 'sid,slot' from a strip cell. Any other mime is ignored.
MIME_SKILL = "application/x-rurik-skill"


def skill_mime(sid, from_slot=None):
    md = QMimeData()
    md.setData(MIME_SKILL, (f"{int(sid)}" if from_slot is None
                            else f"{int(sid)},{int(from_slot)}").encode("ascii"))
    return md


def parse_skill_mime(md):
    """(sid, from_slot or None), or None when the mime is not a skill's."""
    if md is None or not md.hasFormat(MIME_SKILL):
        return None
    try:
        parts = bytes(md.data(MIME_SKILL)).decode("ascii").split(",")
        return int(parts[0]), (int(parts[1]) if len(parts) > 1 else None)
    except (ValueError, IndexError):
        return None


def elide_rank_line(fm, text, width):
    """A cell's line 2 ('Protection Prayers 1', 'Mo · Healing Prayers 0') made
    to fit `width`: the RANK -- the number the line exists to show -- stays
    whole and the attribute's name before it is what elides. Eliding from the
    right took the digits first."""
    if fm.horizontalAdvance(text) <= width:
        return text
    head, sep, tail = text.rpartition(" ")
    if not sep or not tail.isdigit():
        return fm.elidedText(text, Qt.ElideRight, width)
    tail = " " + tail
    return fm.elidedText(head, Qt.ElideRight, max(0, width - fm.horizontalAdvance(tail))) + tail


def pill_font():
    f = QFont("Segoe UI")
    f.setPixelSize(orchtheme.TYPE["caption"] - 1)
    f.setWeight(QFont.DemiBold)
    return f


def pill_size(grade, font=None):
    """The grade pill's (w, h); (0, 0) for a grade that has none."""
    if grade not in GRADE_TEXT:
        return 0, 0
    fm = QFontMetrics(font or pill_font())
    return fm.horizontalAdvance(GRADE_TEXT[grade]) + 14, fm.height() + 4


def paint_pill(p, x, cy, grade, font=None):
    """ONE grade pill for every delegate that draws one (the Skills list's
    rows and the Skill bar's cells): its left edge at `x`, centred on `cy`,
    the chip tokens of its kind. Returns the rect it painted, or None."""
    if grade not in GRADE_TEXT:
        return None
    font = font or pill_font()
    kind = "good" if grade == "hand" else "info"
    w, h = pill_size(grade, font)
    pill = QRect(x, cy - h // 2, w, h)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(PAL[f"chip_{kind}_edge"]))
    p.setBrush(QColor(PAL[f"chip_{kind}_bg"]))
    p.drawRoundedRect(pill.adjusted(0, 0, -1, -1), h / 2, h / 2)
    p.setFont(font)
    p.setPen(QColor(PAL[f"chip_{kind}_fg"]))
    p.drawText(pill, Qt.AlignCenter, GRADE_TEXT[grade])
    p.restore()
    return pill


class SkillDelegate(QStyledItemDelegate):
    """One skill row: the name at body size, then its id, profession and
    attribute in a quiet mono, then a small grade pill in ONE column just past
    the widest name and meta (set_column) -- instead of all of it jammed into
    one string with a trailing asterisk. Flush right, the pill sat 940 px from
    the row it graded with no rule or stripe to carry the eye across; in a
    column it still scans as a column and stays within about 130 px of its
    name. A row too narrow for the column keeps the pill at its right edge."""

    PAD_V = 12
    PILL_GAP = 12                               # past the widest name + meta

    def __init__(self, parent=None):
        super().__init__(parent)
        self.meta_font = mono_font(orchtheme.TYPE["caption"])
        self.pill_font = pill_font()
        self.column = None                      # px from the text's left; None: flush right

    def set_column(self, parts):
        """Put the pill column just past the widest (name, meta) among `parts`
        ((name, meta, grade) triples, as ROLE_PARTS holds them)."""
        fm, mfm = QFontMetrics(QApplication.font()), QFontMetrics(self.meta_font)
        widest = max((fm.horizontalAdvance(name) + 12 + mfm.horizontalAdvance(meta)
                      for name, meta, _g in parts), default=0)
        self.column = widest + self.PILL_GAP

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
            w, _h = pill_size(grade, self.pill_font)
            x = right - w if self.column is None else min(r.left() + self.column, right - w)
            pill = paint_pill(p, x, r.center().y(), grade, self.pill_font)
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


class RosterDelegate(QStyledItemDelegate):
    """A group's roster row: the hostile's name in a column, its facts in the
    muted ink past it -- so every row's facts start at ONE x. As one string,
    'Bandit Raider — L2 …' and 'Academy Monk — L2 …' began their facts 14 px
    apart, a ragged edge in a two-row list. The column is the widest name
    (set_column) with 4 px to spare: at exactly its advance 'Academy Monk'
    elided."""

    GAP = 24                                    # from the column to the facts

    def __init__(self, parent=None):
        super().__init__(parent)
        self.column = 0

    def set_column(self, names):
        fm = QFontMetrics(QApplication.font())
        self.column = max((fm.horizontalAdvance(n) for n in names), default=0) + 4

    def paint(self, p, opt, idx):
        parts = idx.data(ROLE_ROSTER)
        if not parts:
            return super().paint(p, opt, idx)
        name, facts = parts
        o = QStyleOptionViewItem(opt)
        self.initStyleOption(o, idx)
        o.text = ""
        widget = o.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, o, p, widget)
        r = style.subElementRect(QStyle.SE_ItemViewItemText, o, widget).adjusted(4, 0, -8, 0)
        fm = QFontMetrics(o.font)
        p.save()
        p.setFont(o.font)
        p.setPen(QColor(PAL["text"] if o.state & QStyle.State_Enabled else PAL["disabled_fg"]))
        p.drawText(QRect(r.left(), r.top(), self.column, r.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, fm.elidedText(name, Qt.ElideRight, self.column))
        x = r.left() + self.column + self.GAP
        if facts and x < r.right():
            p.setPen(QColor(PAL["muted"]))
            p.drawText(QRect(x, r.top(), r.right() - x, r.height()),
                       Qt.AlignVCenter | Qt.AlignLeft,
                       fm.elidedText(facts, Qt.ElideRight, r.right() - x))
        p.restore()


# ---------------------------------------------------------------- the Skill bar's strip and library

class SlotStrip(QListWidget):
    """Eight skill slots as a grid of wells: four to a row while the viewport
    can hold four cells a name can live in, else two (derived from its OWN
    width in resizeEvent, never from its content -- a bar whose shape followed
    its content was the 840-constant defect). Exactly eight items from birth,
    drawn by SlotDelegate; the item's text is the cell in words ('Slot 3:
    Power Attack …'), for a screen reader and the smoke. The strip does its
    own drags (a cell onto another swaps, a cell onto the library clears, a
    library row onto a cell places) through MIME_SKILL, and hands every drop
    to `on_drop(slot, sid, from_slot)`: the bar owns the model.

    The grid is a QListWidget's own (IconMode, LeftToRight, wrapping): the
    item rects ARE the grid cells and the arrows move by visual grid --
    measured before this was written (proto_strip.py: Right 0->1, Down 1->5,
    Left 5->4, Up 4->0), and the cell width that wraps to exactly N columns is
    (viewport - 1) // N; (viewport) // N wraps to one."""

    CELL_H = 56                                 # the cell: a 50 px well and 6 of gap
    INSET = 3                                   # the well inside its cell, every side
    PAD = 6                                     # inside the well
    NUM_W = 16                                  # the slot number's column
    WIDE_FROM = 624                             # four columns from this viewport width (name room 145+)
    SLOTS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("role", "flat")
        self.setViewMode(QListView.IconMode)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setSpacing(0)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSelectionRectVisible(False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragEnabled(False)              # the strip's own press-and-move below
        self.setAcceptDrops(True)
        # ...on the VIEWPORT too: a drop is delivered to the first widget under
        # the pointer that accepts drops, and a scroll area's frame refuses
        # drag events (they are the viewport's) -- measured: with the frame
        # alone accepting, a synthetic drop reached nothing (proto_drop.py)
        self.viewport().setAcceptDrops(True)
        self.setAccessibleName("Skill bar slots")
        self.on_drop = None                     # callable(slot, sid, from_slot)
        self.cell = QSize(200, self.CELL_H)
        self.columns = 0
        for i in range(self.SLOTS):
            it = QListWidgetItem(f"Slot {i + 1}: empty")
            it.setData(ROLE_SLOT, (i, "", ""))
            self.addItem(it)
        self._press = None
        self._relayout()

    # ---- geometry

    def _columns(self):
        return 4 if self.viewport().width() >= self.WIDE_FROM else 2

    def _relayout(self):
        cols = self._columns()
        cell = QSize(max(40, (self.viewport().width() - 2) // cols), self.CELL_H)
        if cell == self.cell and cols == self.columns:
            return
        self.cell, self.columns = cell, cols
        self.setGridSize(cell)
        self.doItemsLayout()
        rows = self.SLOTS // cols
        self.setFixedHeight(rows * self.CELL_H + 2 * self.frameWidth())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._relayout()

    def cell_rect(self, i):
        return self.visualItemRect(self.item(i))

    @classmethod
    def layout(cls, cell, parts, *, body_fm=None, meta_fm=None, pfont=None):
        """The rects a cell is drawn from and measured with: (well, number,
        name, line 2, pill or None). Line 1 is the number and the name at body
        size; line 2 the attribute and rank in the mono caption with the grade
        pill at the right; `parts` is the cell's (name, meta, grade) or None."""
        body_fm = body_fm or QFontMetrics(QApplication.font())
        meta_fm = meta_fm or QFontMetrics(mono_font(orchtheme.TYPE["caption"]))
        well = cell.adjusted(cls.INSET, cls.INSET, -cls.INSET, -cls.INSET)
        inner = well.adjusted(cls.PAD, cls.PAD, -cls.PAD, -cls.PAD)
        grade = parts[2] if parts else None
        pw, ph = pill_size(grade, pfont)
        l1 = body_fm.height()
        band = max(meta_fm.height(), ph)
        num = QRect(inner.left(), inner.top(), cls.NUM_W, l1)
        name = QRect(inner.left() + cls.NUM_W + 4, inner.top(), inner.width() - cls.NUM_W - 4, l1)
        y2 = inner.bottom() + 1 - band
        pill = None
        right = inner.right() + 1
        if pw:
            pill = QRect(right - pw, y2 + (band - ph) // 2, pw, ph)
            right = pill.left() - 8
        # line 2 runs from the well's inner left, under the number: at 1,280
        # px a four-column cell is 218 px and a Monk's 'Protection Prayers 1'
        # needs 144 of the 131 it gets even so (measured; the rank is kept
        # whole by elide_rank_line, the whole line is the item's text)
        meta = QRect(inner.left(), y2, max(0, right - inner.left()), band)
        return well, num, name, meta, pill

    # ---- the strip's own drag (a cell), and every drop

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        it = self.itemAt(ev.position().toPoint())
        self._press = (ev.position().toPoint(), self.row(it)) if it is not None else None

    def mouseMoveEvent(self, ev):
        if self._press is not None and ev.buttons() & Qt.LeftButton:
            at, row = self._press
            if (ev.position().toPoint() - at).manhattanLength() >= QApplication.startDragDistance():
                sid = int(self.item(row).data(ROLE_ID) or 0)
                self._press = None
                if sid:
                    drag = QDrag(self)
                    drag.setMimeData(skill_mime(sid, row))
                    drag.exec(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)
                return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._press = None
        super().mouseReleaseEvent(ev)

    def dragEnterEvent(self, ev):
        if parse_skill_mime(ev.mimeData()) is not None:
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragMoveEvent(self, ev):
        if parse_skill_mime(ev.mimeData()) is not None and self.itemAt(ev.position().toPoint()):
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dropEvent(self, ev):
        got = parse_skill_mime(ev.mimeData())
        it = self.itemAt(ev.position().toPoint())
        if got is None or it is None:
            ev.ignore()
            return
        ev.acceptProposedAction()
        if self.on_drop is not None:
            self.on_drop(self.row(it), got[0], got[1])


class SlotDelegate(QStyledItemDelegate):
    """A Skill bar cell: a well (the field fill, the border edge; the
    selection fill when selected, the focus ink on its edge while the strip
    has focus), the slot number and the skill's name on line 1, the attribute
    and the rank it ACTS at on line 2 with the grade pill at the right -- the
    same pill the Skills list draws (paint_pill). An empty cell says 'empty'
    in the muted ink. Everything is painted here, from the tokens: the sheet's
    item rules never run for a cell."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.meta_font = mono_font(orchtheme.TYPE["caption"])
        self.pill_font = pill_font()

    def sizeHint(self, opt, idx):
        return self.view.cell

    def paint(self, p, opt, idx):
        parts = idx.data(ROLE_PARTS)
        slot = idx.data(ROLE_SLOT) or (idx.row(), "", "")
        body_fm, meta_fm = QFontMetrics(opt.font), QFontMetrics(self.meta_font)
        well, num_r, name_r, meta_r, pill_r = SlotStrip.layout(
            opt.rect, parts, body_fm=body_fm, meta_fm=meta_fm, pfont=self.pill_font)
        selected = bool(opt.state & QStyle.State_Selected)
        focused = selected and self.view.hasFocus()
        r = orchtheme.RADIUS["md"]
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(PAL["focus"] if focused else PAL["border"]))
        p.setBrush(QColor(PAL["selection_bg"] if selected else PAL["field"]))
        p.drawRoundedRect(well.adjusted(0, 0, -1, -1), r, r)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setFont(self.meta_font)
        p.setPen(QColor(PAL["muted"]))
        p.drawText(num_r, Qt.AlignRight | Qt.AlignVCenter, str(slot[0] + 1))
        if not parts:
            p.setFont(opt.font)
            p.drawText(name_r, Qt.AlignLeft | Qt.AlignVCenter, "empty")
            p.restore()
            return
        name, _meta, grade = parts
        p.setFont(opt.font)
        p.setPen(QColor(PAL["text"] if opt.state & QStyle.State_Enabled else PAL["disabled_fg"]))
        p.drawText(name_r, Qt.AlignLeft | Qt.AlignVCenter,
                   body_fm.elidedText(name, Qt.ElideRight, name_r.width()))
        if pill_r is not None:
            paint_pill(p, pill_r.left(), pill_r.center().y(), grade, self.pill_font)
        line2 = slot[1]
        if line2 and meta_r.width() > 0:
            p.setFont(self.meta_font)
            p.setPen(QColor(PAL["muted"]))
            p.drawText(meta_r, Qt.AlignLeft | Qt.AlignVCenter,
                       elide_rank_line(meta_fm, line2, meta_r.width()))
        p.restore()


class SkillLibrary(PlaceholderList):
    """The Skill bar's inline library: checkable rows (ticked = on the bar),
    a row draggable onto the strip (MIME_SKILL, the id alone), and a strip
    cell dropped on it clears that slot (`on_clear(slot)`). The wheel needs
    nothing here: a QListWidget scrolls under it while its bar can move and
    leaves the event unaccepted at its end, so a spontaneous wheel goes on to
    the page (measured before this was written: list at 0, the list moves
    and the page stays; list at its end, the page moves)."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self.on_clear = None                    # callable(slot)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)    # the strip's note: the viewport is the target
        self.setDefaultDropAction(Qt.CopyAction)

    def startDrag(self, actions):
        it = self.currentItem()
        sid = int(it.data(ROLE_ID) or 0) if it is not None else 0
        if not sid:
            return
        drag = QDrag(self)
        drag.setMimeData(skill_mime(sid))
        drag.exec(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)   # never super(): a Move would
        # clear the source row (QAbstractItemView's own clearOrRemove)

    def dragEnterEvent(self, ev):
        got = parse_skill_mime(ev.mimeData())
        if got is not None and got[1] is not None:
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragMoveEvent(self, ev):
        self.dragEnterEvent(ev)

    def dropEvent(self, ev):
        got = parse_skill_mime(ev.mimeData())
        if got is None or got[1] is None:
            ev.ignore()
            return
        ev.acceptProposedAction()
        if self.on_clear is not None:
            self.on_clear(got[1])

    def check_rect(self, it):
        """Where a row's check box is painted: a double-click there is Qt's
        own toggle, not a second one."""
        opt = QStyleOptionViewItem()
        opt.initFrom(self)
        opt.rect = self.visualItemRect(it)
        opt.features |= QStyleOptionViewItem.HasCheckIndicator
        return self.style().subElementRect(QStyle.SE_ItemViewItemCheckIndicator, opt, self)

    def mouseDoubleClickEvent(self, ev):
        self.dbl_at = ev.position().toPoint()
        super().mouseDoubleClickEvent(ev)


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
