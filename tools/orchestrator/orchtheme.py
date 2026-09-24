r"""The run orchestrator's look: two palettes, the tokens derived from them, the
stylesheet, and the checks that keep them honest. Standard library only -- no
Qt import -- so the contrast audit runs on a bare machine:

    python tools/orchestrator/orchtheme.py          # audit both palettes, exit 1 on a failure

WHERE THE RULES COME FROM. Dream-World-IX, the owner's other project, spent
twelve rounds on its PySide6 workspace (`studies/gui-aesthetics/`,
`ff9mapkit/workspace/style.py`, `editor/theme.py`). What is borrowed here is
the part that fits a four-tab tool -- the rules, and a few small helpers
rewritten here (the colour mix and contrast walk, the selection tint, the
content-addressed image cache). Dream-World-IX is MIT and the same owner's:

  * ONE loud object. The accent is a FILL spent on the verb you press --
    Launch -- and nowhere else: not on a checked box, not on a selected row
    (a selection TINTS toward the accent), not on prose.
  * Every colour that carries text is WALKED to a contrast floor, never
    hand-picked and hoped: 4.5:1 for text, 3.0:1 for a focus ring or a status
    mark. `audit()` measures every pair that is actually painted together,
    against the ground it is actually painted on (a tint solved against one
    ground does not transfer to another).
  * Depth without box-shadow (QSS has none): a raised control gets a lit top
    edge and a shaded foot mixed from `border`; a well (an input) gets the
    inverse. EDGE_T is DWIX's measured 0.14 -- 0.18 grew a second edge.
  * The QSS traps DWIX paid for and `lint()` refuses: a pseudo-class before a
    sub-control (`X:focus::indicator` matches in EVERY state), and a `$` token
    left unsubstituted.

The type ramp is 12 / 14 / 18 px (caption / body / head): 12 is what Windows
itself resolves Segoe UI 9pt to, and each step is at least 1.15x so it reads
as a step. Segoe UI has no true Medium -- 500 renders as 400 -- so emphasis is
600 or nothing.
"""
import hashlib
import os
import re
import sys
from string import Template

# ---------------------------------------------------------------- palettes

# Authored by hand. Everything else is derived from these by derive().
# `field` is a WELL: inputs sit below the card they are on (cut, not raised).
DARK = {
    "dark": True,
    "bg": "#14161a",
    "surface": "#1c1f24",
    "surface_btn": "#272b32",
    "field": "#111317",
    "text": "#e8e4da",
    "muted": "#a0a7b1",
    "accent": "#e2ae4c",
    "accent_fg": "#1a1305",
    "border": "#30353d",
    "hover": "#2c3139",
    "pressed": "#363c45",
    "log_bg": "#0f1114",
    "log_fg": "#cfd4da",
    "success": "#5cc98a",
    "warn": "#f0904e",
    "error": "#ff6b6b",
}

LIGHT = {
    "dark": False,
    "bg": "#ebe8e1",
    "surface": "#f7f5f0",
    "surface_btn": "#fdfcfa",
    "field": "#ffffff",
    "text": "#1d1b17",
    "muted": "#5b574f",
    "accent": "#94620f",
    "accent_fg": "#ffffff",
    "border": "#cfcabf",
    "hover": "#ebe7de",
    "pressed": "#e0dbd0",
    "log_bg": "#fbfaf7",
    "log_fg": "#2a2824",
    "success": "#1d8a52",
    "warn": "#b35a10",
    "error": "#c0392b",
}

PALETTES = {"dark": DARK, "light": LIGHT}
BASE_KEYS = tuple(DARK)

TEXT_FLOOR = 4.5            # WCAG AA, normal text
MARK_FLOOR = 3.0            # WCAG 1.4.11: a focus ring, a status mark, a check
EDGE_T = 0.14               # the lit/shaded edge mix (DWIX: 0.18 grew a bevel)
SELECTION_FLOOR = 20        # raw RGB channel distance a selection keeps from hover

TYPE = {"caption": 12, "body": 14, "head": 18, "mono": 13}
SPACE = {"s1": 4, "s2": 8, "s3": 12, "s4": 16, "s6": 24}
RADIUS = {"sm": 4, "md": 6, "lg": 8}
FONT_UI = '"Segoe UI", "Segoe UI Variable Text", sans-serif'
FONT_MONO = '"Cascadia Mono", "Cascadia Code", "Consolas", monospace'

CHIP_KINDS = ("info", "good", "warn", "crit")

# ---------------------------------------------------------------- colour maths


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def mix(a, b, t):
    """a moved a fraction t of the way to b, both #rrggbb."""
    ca, cb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(ca[i] + (cb[i] - ca[i]) * t):02x}" for i in range(3))


def luminance(h):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def distance(a, b):
    """Largest raw channel difference -- what tells a tint from its neighbour
    when a luminance ratio cannot (a hue shift at equal lightness)."""
    return max(abs(x - y) for x, y in zip(_rgb(a), _rgb(b)))


def _far_ink(ground):
    """The extreme a colour walks toward to gain contrast on this ground."""
    return "#ffffff" if luminance(ground) < 0.18 else "#000000"


def walk(colour, grounds, floor, step=0.04):
    """Move `colour` toward the far ink until it clears `floor` on EVERY ground.
    Starts on the colour itself, so a hue that already passes is returned as is."""
    grounds = [grounds] if isinstance(grounds, str) else list(grounds)
    ink = _far_ink(grounds[0])
    out, t = colour, 0.0
    while min(contrast(out, g) for g in grounds) < floor and t < 1.0:
        t = min(1.0, t + step)
        out = mix(colour, ink, t)
    return out


# ---------------------------------------------------------------- derive


def derive(pal):
    """The base palette plus every derived token. Idempotent."""
    if "focus" in pal:
        return pal
    missing = [k for k in BASE_KEYS if k not in pal]
    if missing:
        raise KeyError(f"palette lacks {missing}")
    p = dict(pal)
    white, black = "#ffffff", "#000000"
    # the primary button's own ladder: both states step AWAY from the ink, so
    # neither can lose contrast against it (light's bronze darkens, dark's gold
    # brightens -- the one rule serves both)
    away = black if luminance(p["accent_fg"]) > 0.5 else white
    p["accent_hover"] = mix(p["accent"], away, 0.10)
    p["accent_pressed"] = mix(p["accent"], away, 0.20)
    # INTAGLIO: one light source, one lever
    for k in ("border", "accent"):
        p[f"{k}_lit"] = mix(p[k], white, EDGE_T)
        p[f"{k}_shade"] = mix(p[k], black, EDGE_T)
    # a control's edge you can find by eye; a hovered field edge
    p["border_strong"] = mix(p["border"], p["text"], 0.22)
    p["border_hover"] = mix(p["border"], p["text"], 0.32)
    # selection TINTS toward the accent -- never the accent's own fill -- and is
    # solved against hover, the state it is confused with
    t = 0.16
    sel = mix(p["surface"], p["accent"], t)
    while (distance(sel, p["hover"]) < SELECTION_FLOOR
           or contrast(p["text"], sel) < TEXT_FLOOR) and t < 0.6:
        t += 0.02
        sel = mix(p["surface"], p["accent"], t)
    p["selection_bg"] = sel
    # a focus ring clears 3:1 on every ground a focusable control sits on
    p["focus"] = walk(p["accent"], [p["surface"], p["field"], p["bg"]], MARK_FLOOR)
    # a status hue keeps its mark job at 3:1; TEXT in that hue gets its own token
    grounds = [p["surface"], p["bg"], p["field"], p["log_bg"]]
    for k in ("success", "warn", "error"):
        p[f"{k}_text"] = walk(p[k], grounds, TEXT_FLOOR)
    # chips: a tinted fill with its ink solved against THAT fill (fill and ink
    # travel together -- DWIX's 1.12:1 chip shipped because they did not)
    hues = {"good": p["success"], "warn": p["warn"], "crit": p["error"]}
    p["chip_info_bg"] = p["surface_btn"]
    p["chip_info_fg"] = walk(p["muted"], p["surface_btn"], TEXT_FLOOR)
    for kind, hue in hues.items():
        bg = mix(p["surface"], hue, 0.16)
        p[f"chip_{kind}_bg"] = bg
        p[f"chip_{kind}_fg"] = walk(hue, bg, TEXT_FLOOR)
        p[f"chip_{kind}_edge"] = mix(bg, hue, 0.45)
    p["chip_info_edge"] = p["border"]
    # a checked box is neutral ink, not the accent (1,333 gold boxes would make
    # the list the loudest thing on screen)
    p["check_bg"] = p["text"]
    p["check_fg"] = p["surface"]
    # a checked box under the pointer shifts its FILL (a ring on the pale fill
    # reads as the box shrinking)
    p["check_hover"] = mix(p["check_bg"], p["surface"], 0.14)
    # disabled: legible, plainly not live (WCAG exempts inactive controls)
    p["disabled_fg"] = mix(p["muted"], p["surface"], 0.35)
    p["disabled_bg"] = mix(p["field"], p["surface"], 0.5)
    # scrollbars
    p["scroll"] = mix(p["border"], p["text"], 0.16)
    p["scroll_hover"] = mix(p["border"], p["text"], 0.34)
    # a danger button's edge and hover
    p["danger_edge"] = mix(p["border"], p["error"], 0.45)
    return p


# ---------------------------------------------------------------- audit


def audit(pal):
    """[(label, measured, floor)] for every pair painted together. A FAILURE is
    measured < floor. The pairs are the real neighbours, not neighbouring keys.

    The list is written by hand, and a hand list can miss a pair: the first
    review found the danger button's hover (its ink over the chip fill, 4.22:1
    in light) missing, with this function printing "clean". So a state rule
    that changes a FILL names its ink here, and the smoke renders a hovered
    danger button and measures the painted pixels as well.

    The primary button's focus ring is drawn INSIDE its own fill (an outline in
    accent_fg), so it is measured by 'accent_fg on accent'; its outer edge on
    the header is exempt by design -- a gold ring on a gold edge cannot show."""
    p = derive(pal)
    rows = []

    def need(label, a, b, floor):
        rows.append((label, round(contrast(a, b), 2), floor))

    for g in ("bg", "surface", "surface_btn", "field", "hover", "pressed", "selection_bg"):
        need(f"text on {g}", p["text"], p[g], TEXT_FLOOR)
    for g in ("bg", "surface", "field", "surface_btn", "hover", "selection_bg", "log_bg"):
        need(f"muted on {g}", p["muted"], p[g], TEXT_FLOOR)
    for g in ("accent", "accent_hover", "accent_pressed"):
        need(f"accent_fg on {g}", p["accent_fg"], p[g], TEXT_FLOOR)
    need("log_fg on log_bg", p["log_fg"], p["log_bg"], TEXT_FLOOR)
    need("log_fg on selection_bg", p["log_fg"], p["selection_bg"], TEXT_FLOOR)
    for k in ("success", "warn", "error"):
        for g in ("surface", "bg", "field", "log_bg"):
            need(f"{k}_text on {g}", p[f"{k}_text"], p[g], TEXT_FLOOR)
        need(f"{k} mark on surface", p[k], p["surface"], MARK_FLOOR)
    for kind in CHIP_KINDS:
        need(f"chip {kind} ink on its fill", p[f"chip_{kind}_fg"], p[f"chip_{kind}_bg"], TEXT_FLOOR)
    for g in ("surface", "field", "bg"):
        need(f"focus ring on {g}", p["focus"], p[g], MARK_FLOOR)
    need("check mark on its fill", p["check_fg"], p["check_bg"], MARK_FLOOR)
    need("checked box on field", p["check_bg"], p["field"], MARK_FLOOR)
    need("accent fill on bg", p["accent"], p["bg"], MARK_FLOOR)
    need("danger text on its hover and press", p["chip_crit_fg"], p["chip_crit_bg"], TEXT_FLOOR)
    need("check mark on a hovered checked box", p["check_fg"], p["check_hover"], MARK_FLOOR)
    # interactive states must be DIFFERENT, measurably (DWIX: hover was byte-
    # identical to rest in 4 of 8 palettes and nobody saw it for rounds)
    rows.append(("hover differs from a button at rest",
                 distance(p["hover"], p["surface_btn"]), 6))
    rows.append(("hover differs from a list at rest",
                 distance(p["hover"], p["surface"]), 6))
    rows.append(("pressed differs from hover", distance(p["pressed"], p["hover"]), 6))
    rows.append(("selection differs from hover", distance(p["selection_bg"], p["hover"]),
                 SELECTION_FLOOR))
    rows.append(("a hovered checked box differs from one at rest",
                 distance(p["check_hover"], p["check_bg"]), 6))
    rows.append(("a card differs from the page", distance(p["surface"], p["bg"]), 6))
    rows.append(("a well differs from its card", distance(p["field"], p["surface"]), 6))
    return rows


def failures(pal):
    return [(label, got, floor) for label, got, floor in audit(pal) if got < floor]


# ---------------------------------------------------------------- assets

_CHECK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
          '<path d="M3.5 8.4 6.6 11.3 12.6 4.9" fill="none" stroke="{ink}" '
          'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
_CHEVRON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path d="{d}" fill="none" stroke="{ink}" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')
_DOWN, _UP = "M4.5 6.5 8 10 11.5 6.5", "M4.5 9.5 8 6 11.5 9.5"


def asset_svgs(pal):
    """The four images QSS cannot draw itself, tinted for this palette."""
    p = derive(pal)
    return {
        "check": _CHECK.format(ink=p["check_fg"]),
        "check_disabled": _CHECK.format(ink=p["surface"]),
        "down": _CHEVRON.format(d=_DOWN, ink=p["muted"]),
        "up": _CHEVRON.format(d=_UP, ink=p["muted"]),
        "down_disabled": _CHEVRON.format(d=_DOWN, ink=p["disabled_fg"]),
        "up_disabled": _CHEVRON.format(d=_UP, ink=p["disabled_fg"]),
    }


def write_assets(pal, directory):
    """Write each image under a name derived from its CONTENT and return
    {name: path}. Qt caches images by path, so an overwritten fixed name would
    keep serving the old tint; a content address cannot go stale."""
    os.makedirs(directory, exist_ok=True)
    out = {}
    for name, svg in asset_svgs(pal).items():
        digest = hashlib.sha1(svg.encode("utf-8")).hexdigest()[:12]
        path = os.path.join(directory, f"{name}-{digest}.svg")
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(svg)
        out[name] = path.replace("\\", "/")
    return out


# ---------------------------------------------------------------- the sheet
#
# A string.Template, so QSS's braces need no escaping. It substitutes inside
# /* comments */ too, so no comment below names a token with a dollar sign.

_QSS = Template("""
* { outline: 0; }
QWidget { color: $text; font-family: $font_ui; font-size: ${body}px; }
QMainWindow, QDialog, QMessageBox { background: $bg; }

/* ---- structure */
QFrame[role="card"] { background: $surface; border: 1px solid $border; border-radius: ${r_lg}px; }
QFrame[role="header"] { background: $surface; border: none; border-bottom: 1px solid $border; }
QLabel { background: transparent; }
QLabel[role="title"] { font-size: ${head}px; font-weight: 600; color: $text; }
QLabel[role="subtitle"] { font-size: ${caption}px; color: $muted; }
QLabel[role="overline"] { font-size: ${caption}px; font-weight: 600; color: $muted; }
QLabel[role="caption"] { font-size: ${caption}px; color: $muted; }
QLabel[role="slot"] { font-family: $font_mono; font-size: ${caption}px; color: $muted; }
QLabel[role="empty_title"] { font-size: ${head}px; font-weight: 600; color: $text; }
QLabel[role="chip"] { font-size: ${caption}px; font-weight: 600; border-radius: 10px; padding: 2px 9px; }
QLabel[role="chip"][kind="info"] { background: $chip_info_bg; color: $chip_info_fg; border: 1px solid $chip_info_edge; }
QLabel[role="chip"][kind="good"] { background: $chip_good_bg; color: $chip_good_fg; border: 1px solid $chip_good_edge; }
QLabel[role="chip"][kind="warn"] { background: $chip_warn_bg; color: $chip_warn_fg; border: 1px solid $chip_warn_edge; }
QLabel[role="chip"][kind="crit"] { background: $chip_crit_bg; color: $chip_crit_fg; border: 1px solid $chip_crit_edge; }

/* ---- buttons: default (raised), primary (the one accent), quiet, danger.
   Every tier restates every state: a property selector out-ranks the generic
   pseudo-state rules, and a state it does not restate simply does nothing. */
QPushButton {
    background: $surface_btn; color: $text;
    border: 1px solid $border; border-top-color: $border_lit; border-bottom-color: $border_shade;
    border-radius: ${r_md}px; padding: 6px 14px; min-height: 20px;
}
QPushButton:hover { background: $hover; }
QPushButton:pressed { background: $pressed; border-top-color: $border_shade; border-bottom-color: $border_lit; }
QPushButton:focus { border: 1px solid $focus; }
QPushButton:disabled { background: $surface; color: $disabled_fg; border: 1px solid $border; }
QPushButton:pressed:focus { border: 1px solid $border; border-top-color: $border_shade; border-bottom-color: $border_lit; }

QPushButton[role="primary"] {
    background: $accent; color: $accent_fg; font-weight: 600;
    border: 1px solid $accent; border-top-color: $accent_lit; border-bottom-color: $accent_shade;
    padding: 6px 18px;
}
QPushButton[role="primary"]:hover { background: $accent_hover; }
QPushButton[role="primary"]:pressed { background: $accent_pressed; border-top-color: $accent_shade; border-bottom-color: $accent_lit; }
QPushButton[role="primary"]:focus {
    border: 1px solid $accent; border-top-color: $accent_lit; border-bottom-color: $accent_shade;
    outline: 1px solid $accent_fg;
}
QPushButton[role="primary"]:pressed:focus { border: 1px solid $accent; border-top-color: $accent_shade; border-bottom-color: $accent_lit; }
QPushButton[role="primary"]:disabled { background: $surface_btn; color: $disabled_fg; border: 1px solid $border; }

QPushButton[role="quiet"] { background: transparent; color: $text; border: 1px solid $border; }
QPushButton[role="quiet"]:hover { background: $hover; }
QPushButton[role="quiet"]:pressed { background: $pressed; }
QPushButton[role="quiet"]:focus { border: 1px solid $focus; }
QPushButton[role="quiet"]:disabled { background: transparent; color: $disabled_fg; border: 1px solid $border; }
QPushButton[role="quiet"]:pressed:focus { border: 1px solid $border_strong; }

QPushButton[role="danger"] { background: transparent; color: $error_text; border: 1px solid $danger_edge; }
QPushButton[role="danger"]:hover { background: $chip_crit_bg; color: $chip_crit_fg; }
QPushButton[role="danger"]:pressed { background: $chip_crit_bg; color: $chip_crit_fg; border-color: $error; }
QPushButton[role="danger"]:focus { border: 1px solid $focus; }
QPushButton[role="danger"]:disabled { background: transparent; color: $disabled_fg; border: 1px solid $border; }
QPushButton[role="danger"]:pressed:focus { border: 1px solid $error; }

/* ---- wells: inputs are cut into the card (shade on top, lit foot) */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: $field; color: $text;
    border: 1px solid $border; border-top-color: $border_shade; border-bottom-color: $border_lit;
    border-radius: ${r_md}px; padding: 4px 8px; min-height: 22px;
    selection-background-color: $selection_bg; selection-color: $text;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border: 1px solid $border_hover; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid $focus; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background: $disabled_bg; color: $disabled_fg; border: 1px solid $border;
}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 24px; border: none; }
QComboBox::down-arrow { image: url($img_down); width: 14px; height: 14px; }
QComboBox::down-arrow:disabled { image: url($img_down_disabled); }
QComboBox QLineEdit { background: transparent; border: none; padding: 0; min-height: 0; }
QComboBox QAbstractItemView, QComboBox QAbstractItemView:focus,
QListView[role="popup"], QListView[role="popup"]:focus {
    background: $surface; color: $text; border: 1px solid $border_strong; border-radius: 0;
    padding: 4px; selection-background-color: $selection_bg; selection-color: $text; outline: 0;
}
QSpinBox, QDoubleSpinBox { padding-right: 22px; }
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; width: 20px; border: none; background: transparent;
}
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-position: top right; margin: 2px 2px 0 0; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-position: bottom right; margin: 0 2px 2px 0; }
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: $hover; border-radius: 3px; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url($img_up); width: 12px; height: 12px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url($img_down); width: 12px; height: 12px; }
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::up-arrow:off, QDoubleSpinBox::up-arrow:off { image: url($img_up_disabled); }
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled,
QSpinBox::down-arrow:off, QDoubleSpinBox::down-arrow:off { image: url($img_down_disabled); }

/* ---- check indicators, every state (once QSS touches an indicator Qt paints
   none of it natively). Sub-control BEFORE pseudo-class, always. */
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox:disabled { color: $disabled_fg; }
QCheckBox::indicator, QAbstractItemView::indicator {
    width: 16px; height: 16px; border-radius: ${r_sm}px;
    background: $field; border: 1px solid $border_strong;
}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover { border: 1px solid $border_hover; }
QCheckBox::indicator:focus { border: 1px solid $focus; }
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {
    background: $check_bg; border: 1px solid $check_bg; image: url($img_check);
}
QCheckBox::indicator:checked:hover, QAbstractItemView::indicator:checked:hover {
    background: $check_hover; border: 1px solid $check_hover;
}
QCheckBox::indicator:checked:focus { border: 1px solid $focus; }
QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled { background: $disabled_bg; border: 1px solid $border; }
QCheckBox::indicator:checked:disabled, QAbstractItemView::indicator:checked:disabled {
    background: $disabled_fg; border: 1px solid $disabled_fg; image: url($img_check_disabled);
}

/* ---- views */
QListView, QTreeView, QTableView {
    background: $surface; color: $text; border: 1px solid $border; border-radius: ${r_lg}px;
    padding: 4px; outline: 0;
    selection-background-color: $selection_bg; selection-color: $text;
}
QListView:focus, QTreeView:focus, QTableView:focus { border: 1px solid $focus; }
QListView::item { padding: 4px 6px; border-radius: ${r_sm}px; }
/* a tree row spans columns: a rounded cell would split its selection in two */
QTreeView::item { padding: 4px 6px; border-radius: 0; }
QListView::item:hover, QTreeView::item:hover { background: $hover; }
QListView::item:selected, QTreeView::item:selected { background: $selection_bg; color: $text; }
QTreeView::branch { background: transparent; }
/* a view inside a card is part of the card: no second box, no second fill */
QListView[role="flat"], QTreeView[role="flat"], QTableView[role="flat"] {
    background: transparent; border: none; padding: 0;
}
QListView[role="flat"], QTreeView[role="flat"] { border: 1px solid transparent; }
QListView[role="flat"]:focus, QTreeView[role="flat"]:focus, QTableView[role="flat"]:focus {
    border: 1px solid $focus;
}
QTableView { gridline-color: $surface; }
QTableView QComboBox, QTableView QSpinBox { margin: 4px 6px; }
QTableView::item { padding: 0 6px; border: none; }
QTableView::item:selected { background: $selection_bg; color: $text; }
QHeaderView { background: transparent; }
QHeaderView::section {
    background: $surface; color: $muted; font-size: ${caption}px; font-weight: 600;
    border: none; border-bottom: 1px solid $border; padding: 6px 8px;
}
QTableCornerButton::section { background: $surface; border: none; }

/* ---- logs: a deeper well, a mono face, family only on the body */
QPlainTextEdit {
    background: $log_bg; color: $log_fg; font-family: $font_mono; font-size: ${mono}px;
    border: 1px solid $border; border-radius: ${r_lg}px; padding: 6px;
    selection-background-color: $selection_bg; selection-color: $log_fg;
}
QPlainTextEdit:focus { border: 1px solid $focus; }

/* ---- tabs: the selected tab is underlined, not boxed */
QTabWidget::pane { border: none; border-top: 1px solid $border; top: -1px; background: $bg; }
QTabWidget::tab-bar { left: 12px; }
QTabBar { background: transparent; }
QTabBar::tab {
    background: transparent; color: $muted; border: none; border-bottom: 2px solid transparent;
    padding: 9px 18px 8px 18px; margin-right: 2px;
}
QTabBar::tab:hover { color: $text; }
QTabBar::tab:selected { color: $text; border-bottom: 2px solid $accent; }
QTabBar::tab:selected:focus { background: $hover; }

/* ---- scrolling */
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:horizontal { background: $scroll; border-radius: 4px; min-width: 28px; }
QScrollBar::handle:hover { background: $scroll_hover; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: none; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QAbstractScrollArea::corner { background: transparent; border: none; }

QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background: $border; }
QStatusBar { background: $surface; color: $muted; border-top: 1px solid $border; }
QStatusBar::item { border: none; }
QStatusBar QLabel { color: $muted; font-size: ${caption}px; }
QToolTip { background: $surface_btn; color: $text; border: 1px solid $border_strong; padding: 6px 8px; }
QMenu { background: $surface; border: 1px solid $border_strong; padding: 4px; }
QMenu::item { padding: 5px 22px 5px 12px; border-radius: ${r_sm}px; }
QMenu::item:selected { background: $selection_bg; color: $text; }
QMenu::item:disabled { color: $disabled_fg; }
QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }
""")


def qss(pal, assets):
    """The stylesheet for a palette. `assets` is write_assets()'s {name: path}."""
    p = derive(pal)
    values = {k: v for k, v in p.items() if isinstance(v, str)}
    values.update({"font_ui": FONT_UI, "font_mono": FONT_MONO})
    values.update(TYPE)
    values.update({f"r_{k}": v for k, v in RADIUS.items()})
    values.update({f"img_{k}": v for k, v in assets.items()})
    return _QSS.substitute(values)


_BAD_ORDER = re.compile(r"(?:[A-Za-z_*][\w-]*|\])(?::!?[a-z-]+)+::[a-z-]+")
_ROLE_RULE = re.compile(r'\[role="([a-z_]+)"\]')


def lint(sheet):
    """Structural faults the Qt parser accepts silently. [] when clean."""
    out = []
    body = re.sub(r"/\*.*?\*/", "", sheet, flags=re.S)
    for m in _BAD_ORDER.finditer(body):
        out.append(f"pseudo-class before a sub-control (matches in every state): {m.group(0)}")
    if "$" in body:
        out.append("an unsubstituted token")
    if body.count("{") != body.count("}"):
        out.append(f"unbalanced braces ({body.count('{')} open, {body.count('}')} close)")
    for unit in re.findall(r"font-size:\s*[\d.]+(em|ex|%)", body):
        out.append(f"font-size in {unit} (Qt ignores it and falls back silently)")
    return out


def styled_roles(sheet):
    """Every role= value the sheet has a rule for (the call-site fence's half)."""
    return set(_ROLE_RULE.findall(sheet))


# ---------------------------------------------------------------- CLI


def main():
    bad = 0
    for name, pal in PALETTES.items():
        rows = audit(pal)
        fails = [r for r in rows if r[1] < r[2]]
        bad += len(fails)
        print(f"{name}: {len(rows) - len(fails)} of {len(rows)} pairs clear their floor")
        for label, got, floor in rows:
            mark = "FAIL" if got < floor else "ok"
            print(f"  [{mark:>4}] {label:<40} {got:>6} (floor {floor})")
        sheet = qss(pal, {k: f"/{k}.svg" for k in asset_svgs(pal)})
        for fault in lint(sheet):
            bad += 1
            print(f"  [FAIL] lint: {fault}")
    print("audit:", "clean" if not bad else f"{bad} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
