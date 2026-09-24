r"""Rurik run orchestrator -- the vertical slice as a practice sandbox, from a
window. PySide6; nothing here knows the archive, the wire or the rules.

    python tools/orchestrator/orchestrator.py                    # the window, the slice loaded
    python tools/orchestrator/orchestrator.py --spec my.toml     # open a saved spec
    python tools/orchestrator/orchestrator.py --smoke DIR        # drive every panel once, exit
    python tools/orchestrator/orchestrator.py --snap DIR         # render every surface to PNG, exit
    pythonw apps/orchestrator.pyw                                # double-click launcher

WHY THIS LIVES UNDER `tools/` AND NOT `toolkit/`. `CLAUDE.md` pins `toolkit/`
to the standard library; PySide6 is not that. So the split is the one
`tools/viewer/` already made: every fact -- what a spec may say, where a
group stands, which ids are reserved, what the gamesrv is told -- is
`toolkit/harness/sandbox.py`'s (stdlib, `test_sandbox.py`), the content is
`toolkit/content.py`'s, and every NAME on screen is resolved at run time from
the owner's own archive through `toolkit/clientscan/textrec.py`. This file
holds widgets; `orchui.py` the helpers they are built from; `orchtheme.py`
(stdlib) the palettes, the stylesheet and their contrast audit. If a run is
wrong, the question is for the compiler.

WHAT THE WINDOW IS. A header over four tabs, all over one spec:
  header   the spec's name, open / save / load the slice, a one-line summary
           of the spec, and the three verbs -- Compile, LAUNCH (the one accent
           in the window: the verb you are here to press), Stop
  Skills   the ACCOUNT library -- which skills are unlocked, account-wide
           (0x001D). The character's own bar and every hero's draw on it;
           a hero's usable library is its own list plus this
           (herolib.hero_library).
  Party    the character to play (profession pair, level, hands) and which
           heroes are unlocked -- each with a profession and a body. Bars
           and attribute ranks are NOT here (2026-09-22, the owner): the
           in-game Skills and Attributes panels set them, for the character
           and for each hero, and `--persist` keeps what they set from one
           run to the next.
  Enemies  up to four groups of up to four hostiles, one of them the boss:
           the groups and hostiles as a list on the left, the selected
           hostile's template, weapon, bar and ranks on the right (a
           filterable picker for these is the next step, SANDBOX-N1)
  Run      the launch options; the stored character and its reset; the
           compiled result (the overlay and the command, shown before
           anything runs, with what the character store already holds); the
           harness's output, streamed
The operator plays; closing the game client ends the run and the servers.

NAMES. Skill names come off the pinned client's own skill table (the record's
name string id, `skilltable.parse_record`) and the archive's text files; hero
names off the extracted hero table's string ids; attribute names likewise.
None of it is stored anywhere -- the spec on disk carries ids -- and a
machine with no client shows ids. That is the provenance gate's "commit the
id, resolve the string at run time", one more time.

THE LOOK is Dream-World-IX's rules at the size of this tool (`orchtheme.py`
says which and why): one accent, spent on Launch; cards with real titles in
place of group boxes; a sentence goes under a control, never inside it; ids
and citations on hover, not on the surface; every colour walked to its
contrast floor. `--smoke` checks those as laws, not as intentions.
"""
import argparse
import ast
import inspect
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for p in (os.path.join(ROOT, "toolkit"), os.path.join(ROOT, "toolkit", "harness"),
          os.path.join(ROOT, "toolkit", "clientscan"), os.path.join(ROOT, "toolkit", "mapdata"),
          os.path.join(ROOT, "toolkit", "authsrv")):
    if p not in sys.path:
        sys.path.insert(0, p)

import sandbox        # noqa: E402  (toolkit/harness/sandbox.py)
import checks         # noqa: E402  (toolkit/checks.py: the smoke's verdict, floored)
import content        # noqa: E402
import vaultpath      # noqa: E402

try:
    from PySide6.QtCore import (QElapsedTimer, QEvent, QPoint, QPointF, QProcess,
                                QProcessEnvironment, QRect, Qt, QTimer, Signal)
    from PySide6.QtGui import (QColor, QFont, QIcon, QImage, QKeyEvent, QPainter,
                               QTextCharFormat, QTextCursor, QWheelEvent)
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication,
                                   QBoxLayout, QCheckBox, QComboBox,
                                   QCompleter, QFileDialog, QFormLayout, QFrame,
                                   QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                                   QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                                   QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                                   QStatusBar, QStyle, QStyleOption, QStyleOptionButton,
                                   QStyleOptionComboBox, QStyleOptionFrame, QStyleOptionViewItem,
                                   QDoubleSpinBox, QSplitter, QStackedWidget,
                                   QTableWidget, QTableWidgetItem, QTabWidget, QToolButton,
                                   QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"the run orchestrator needs PySide6 (py -m pip install PySide6): {exc}")

import orchtheme      # noqa: E402  (tools/orchestrator: palettes, sheet, audit)
import orchui         # noqa: E402  (tools/orchestrator: the widget helpers)
from orchui import (ROLE_ID, ROLE_PARTS, ROLE_ROSTER, button, caption, card, chip,  # noqa: E402
                    overline, role_label, set_chip)


# ---------------------------------------------------------------- names

class Names:
    """Every label the window shows, resolved from the owner's own client and
    archive at start. Falls back to ids, and says why, when it cannot."""

    def __init__(self, world, resolve=True):
        self.world = world
        self.skill, self.hero, self.attr = {}, {}, {}
        self.why = None
        self.heroes = sandbox.hero_catalogue()
        if resolve:
            try:
                self._resolve()
            except Exception as exc:                    # noqa: BLE001
                self.why = f"Names unresolved ({type(exc).__name__}: {exc}); ids shown"

    def _resolve(self):
        import pinned            # toolkit/clientscan
        import skilltable
        import textrec
        exe, _why = pinned.find()
        with open(exe, "rb") as fh:
            data = fh.read()
        base, count, _score = skilltable.locate_table(data)
        with textrec.TextIndex(exe) as ix:
            for k in self.world.rows("skills"):
                sid = int(k)
                if sid < count:
                    nid = skilltable.parse_record(data, base, sid).get("name_id")
                    text = ix.get(int(nid)) if nid else None
                    if text:
                        self.skill[sid] = text
            for idx, nid in self.heroes:
                text = ix.get(int(nid))
                if text:
                    self.hero[idx] = text
            for k, r in self.world.rows("attribute").items():
                text = ix.get(int(r.get("name_string_id", 0) or 0))
                if text:
                    self.attr[int(k)] = text

    def skill_profession(self, sid):
        row = self.world.rows("skills").get(str(sid)) or {}
        return int(row.get("profession", 0) or 0)

    def skill_grade(self, sid):
        """'hand' (a HAND [skill_effect.*] row), 'label' (SKILLS-LT: acts
        through a label parsed from the client's own description template)
        or None (draws and times, does nothing)."""
        return "hand" if sid in self.modelled else ("label" if sid in self.labelled else None)

    def skill_parts(self, sid):
        """(name, meta, grade) -- what a skill row draws, kept apart so the list
        can set each in its own register; slot_label joins them as the text the
        filters match."""
        row = self.world.rows("skills").get(str(sid)) or {}
        prof = sandbox.ABBREV.get(int(row.get("profession", 0) or 0), "-")
        attr = self.attr.get(int(row.get("attribute", -1)), "")
        meta = f"{sid}  {prof}" + (f"  {attr}" if attr else "")
        return (self.skill.get(sid, f"skill {sid}"), meta, self.skill_grade(sid))

    def slot_label(self, sid):
        """A skill as a bar slot's picker shows it, and as the Skills list's
        item text (what its filter matches and a screen reader says): the grade
        in the same words as the pills, right after the name, so a narrow slot
        clips the id and attribute before it clips the grade, and 'modelled'
        typed into either filter finds the modelled rows. The id and attribute
        stay in the text because both filter on it (type '322')."""
        name, meta, grade = self.skill_parts(sid)
        word = {"hand": "  · modelled", "label": "  · label"}.get(grade, "")
        return f"{name}{word}  [{meta.replace('  ', ' ')}]"

    def skill_tip(self, sid):
        name, meta, grade = self.skill_parts(sid)
        return f"{name}   {meta.replace('  ', ' · ')}\n{GRADE_TIP[grade]}"

    def hero_name(self, idx):
        return self.hero.get(idx, f"hero {idx}")

    def hero_label(self, idx):
        return f"{self.hero_name(idx)}  [{idx}]"

    def attr_label(self, aid):
        return self.attr.get(aid, f"Attribute {aid}")

    @property
    def modelled(self):
        if not hasattr(self, "_modelled"):
            self._modelled = set(sandbox.modelled_skills(self.world))
        return self._modelled

    @property
    def labelled(self):
        if not hasattr(self, "_labelled"):
            self._labelled = set(sandbox.label_skills(self.world))
        return self._labelled


# each a sentence, the grade its first word: capitalised, as every sentence on
# hover is (the pills themselves stay lower-case)
GRADE_TIP = {"hand": "Modelled: this server acts it from a hand-verified [skill_effect] row",
             "label": ("Label: acts through a label parsed from the client's own description "
                       "template, not a hand-verified row (SKILLS-LT); the gamesrv log says so "
                       "at every cast"),
             None: "Draws and times correctly; this server does nothing more with it"}


# ---------------------------------------------------------------- pieces

class Picker(QComboBox):
    """A combo whose items carry a value, type-to-filter.

    Sized from a character count, not from its longest item (that is how the
    old window grew 1,250 px combos), and it shows the START of its text: an
    editable combo narrower than its text used to scroll to the end, so a
    skill read 'V Strength] *'. The full text is on hover, and the popup is
    as wide as its longest row."""

    def __init__(self, parent=None, chars=24):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(chars)
        comp = self.completer()
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.popup().setProperty("role", "popup")
        self.tips = {}
        self.currentIndexChanged.connect(self._show_start)

    def _show_start(self, *_a):
        le = self.lineEdit()
        if le is not None:
            le.setCursorPosition(0)
        self.setToolTip(self.tips.get(self.currentData(), self.currentText()))

    def set_choices(self, pairs, keep=None, parts=None, tips=None):
        """pairs: [(label, value)]. Keeps the current value when it is still
        offered. `parts` ({value: (name, meta, grade)}) makes the drop-down draw
        its rows the way the Skills list does; `tips` gives each its hover."""
        current = keep if keep is not None else self.value()
        self.blockSignals(True)
        self.clear()
        for label, value in pairs:
            self.addItem(label, value)
            if parts and value in parts:
                self.setItemData(self.count() - 1, parts[value], ROLE_PARTS)
        self.blockSignals(False)
        self.tips = dict(tips or {})
        if parts:
            # the drop-down AND the type-to-filter popup (the completer's own
            # view, which draws plain text unless told): the same rows in one
            # style, their pills in one column
            for view in (self.view(), self.completer().popup()):
                if not isinstance(view.itemDelegate(), orchui.SkillDelegate):
                    view.setItemDelegate(orchui.SkillDelegate(view))
                view.itemDelegate().set_column(parts.values())
        fm = self.fontMetrics()
        widest = max((fm.horizontalAdvance(label) for label, _v in pairs), default=0)
        self.view().setMinimumWidth(min(widest + 48, 760))
        self.set_value(current)

    def value(self):
        return self.currentData()

    def set_value(self, value):
        for i in range(self.count()):
            if self.itemData(i) == value:
                self.setCurrentIndex(i)
                self._show_start()
                return True
        if self.count():
            self.setCurrentIndex(0)
        self._show_start()
        return False


def skill_choices(names, professions, empty=True):
    ids = sandbox.default_unlocks(names.world, professions)
    pairs = sorted(((names.slot_label(s), s) for s in ids), key=lambda p: p[0].lower())
    return ([("(empty)", 0)] if empty else []) + pairs


class Bar(QWidget):
    """Eight skill slots, two columns of four (the Enemies tab's; the party's
    bars are in-game) -- one column of eight when the bar is too narrow for
    two to hold the widest label among the choices it holds NOW."""

    changed = Signal()                          # a slot edited

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        self.need = 0                           # the widest choice, px (set_professions)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(8)
        self.slots = []
        self.nums = []
        for i in range(sandbox.BAR_SLOTS):
            num = role_label(str(i + 1), "slot")
            num.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            num.setFixedWidth(14)
            pk = Picker(chars=16)
            pk.setAccessibleName(f"Skill slot {i + 1}")
            num.setBuddy(pk)
            pk.currentIndexChanged.connect(lambda _i: self.changed.emit())
            self.slots.append(pk)
            self.nums.append(num)
        self.columns = 0
        self._arrange(2)

    def _arrange(self, columns):
        """Two columns of four, or one of eight."""
        if columns == self.columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        per = sandbox.BAR_SLOTS // columns
        for i, (num, pk) in enumerate(zip(self.nums, self.slots)):
            row, col = i % per, (i // per) * 3
            self.grid.addWidget(num, row, col)
            self.grid.addWidget(pk, row, col + 1)
        self.grid.setColumnMinimumWidth(2, 16 if columns == 2 else 0)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(4, 1 if columns == 2 else 0)

    def _columns(self):
        """Two while each slot's field would hold the widest choice, else one.
        Two columns give a slot (bar - 166) / 2 px: 2 x 14 of numbers, 4 x 10
        of spacing, the 16 px gutter and 41 of each combo's own chrome
        (measured 356 / 371 / 416 / 516 at bars of 878 / 908 / 998 / 1198).
        A threshold fitted to ONE list -- 840, the Warrior's 335 px -- cut a
        Monk's 371 ('… [307 Mo Protection Prayers]') mid-word at the default
        1,280, on the example's own second hostile."""
        return 2 if (self.width() - 166) // 2 >= self.need else 1

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._arrange(self._columns())

    def set_professions(self, professions):
        pairs = skill_choices(self.names, professions)
        parts = {s: self.names.skill_parts(s) for _l, s in pairs if s}
        tips = {s: self.names.skill_tip(s) for s in parts}
        for pk in self.slots:
            pk.set_choices(pairs, parts=parts, tips=tips)
        fm = self.slots[0].fontMetrics()
        self.need = max((fm.horizontalAdvance(label) for label, _s in pairs), default=0)
        self._arrange(self._columns())          # a template change, at one width

    def values(self):
        return [int(pk.value() or 0) for pk in self.slots]

    def set_values(self, ids):
        ids = list(ids or []) + [0] * sandbox.BAR_SLOTS
        for pk, sid in zip(self.slots, ids):
            pk.set_value(int(sid))


class Ranks(QWidget):
    """One spin box per attribute of the given professions, two to a row, and
    the budget as a chip (the Enemies tab's; the party's ranks are in-game).
    The chip is the NOTICE; `hint`, a caption under the grid, stays the HINT,
    so an over-budget spend never erases the sentence saying what a valid one
    is. Ranks lays the hint out ITSELF, under the grid set_professions wipes:
    the first cut left that to the card, which forgot, and a label shown with
    no parent is a top-level window of its own -- one per hostile, and the
    app no longer quit when the main window closed."""

    changed = Signal()                          # a rank edited (never a rebuild)

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        self.rules = sandbox.attribute_rules(names.world)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)
        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)
        outer.addLayout(self.grid)
        self.spins = {}
        # housed HERE from birth (a card's `trailing` re-homes it in its own
        # header): set_professions shows it, and shown with no parent it would
        # be a window of its own -- the hint's trap, one widget over
        self.chip = chip("", "info")
        self.chip.setParent(self)
        self.label = self.chip
        self.hint = caption("")
        outer.addWidget(self.hint)
        self.level = 3
        self.professions = ()

    def _clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def set_professions(self, professions, level):
        keep = self.ranks()
        self._clear()
        self.spins = {}
        self.professions = tuple(int(p) for p in professions if p)
        self.level = int(level)
        if self.rules is None:
            self.grid.addWidget(caption("No attribute table, so ranks cannot be edited here.",
                                        tip="vault/content/attributes.toml is missing."),
                                0, 0, 1, 6)
            self.chip.hide()
            self.hint.hide()
            return
        self.chip.show()
        self.hint.show()
        n = 0
        for aid, row in sorted(self.rules.attributes.items()):
            if row["profession"] not in self.professions:
                continue
            if row["is_primary"] and row["profession"] != self.professions[0]:
                continue                       # the secondary's primary attribute: never spendable
            sp = QSpinBox()
            sp.setRange(0, self.rules.rank_max)
            sp.setValue(dict(keep).get(aid, 0))
            sp.setFixedWidth(92)
            sp.valueChanged.connect(self._budget)
            sp.valueChanged.connect(lambda _v: self.changed.emit())
            name = self.names.attr_label(aid)
            lab = QLabel(name + (f'  <span style="color:{orchui.PAL["muted"]}">primary</span>'
                                 if row["is_primary"] else ""))
            lab.setToolTip(f"Attribute {aid}" + (" — the primary's own attribute"
                                                 if row["is_primary"] else ""))
            lab.setBuddy(sp)
            sp.setAccessibleName(name)
            r, c = n // 2, (n % 2) * 3
            self.grid.addWidget(lab, r, c)
            self.grid.addWidget(sp, r, c + 1)
            self.spins[aid] = sp
            n += 1
        if not n:
            self.grid.addWidget(caption("This template's profession has no spendable "
                                        "attributes."), 0, 0, 1, 6)
        self.grid.setColumnMinimumWidth(2, 24)
        self.grid.setColumnStretch(5, 1)
        self._budget()

    def _budget(self):
        if self.rules is None:
            return
        spent = self.rules.total_spent({a: s.value() for a, s in self.spins.items()})
        budget = sandbox.budget_for_level(self.level)   # 0 at level 0: the spin offers it
        self.hint.setText(f"A level-{self.level} hostile has {budget} points to spend; the "
                          f"compiler refuses more.")
        self.hint.setToolTip("Attribute points by level, as GWW gives them.")
        if spent > budget:
            set_chip(self.chip, f"{spent} of {budget} points — over budget", "crit")
        else:
            set_chip(self.chip, f"{spent} of {budget} points",
                     "good" if spent == budget else "info")

    def set_level(self, level):
        self.level = int(level)
        self._budget()

    def ranks(self):
        return [[a, s.value()] for a, s in self.spins.items() if s.value()]

    def set_ranks(self, pairs):
        for a, r in pairs or []:
            if int(a) in self.spins:
                self.spins[int(a)].setValue(int(r))
        self._budget()


def profession_picker(none=False, short=False):
    """`short` drops the '(W)' -- for the heroes table, whose column already
    says Profession and has no room for the abbreviation."""
    pk = QComboBox()
    pk.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    pk.setMinimumContentsLength(10 if short else 14)
    if none:
        pk.addItem("(none)", 0)
    for pid, name in sandbox.PROFESSIONS.items():
        pk.addItem(name if short else f"{name} ({sandbox.ABBREV[pid]})", pid)
    # the popup is a list, not a menu (the sheet), and a list shows ten rows:
    # '(none)' makes eleven, and the eleventh scrolled
    pk.setMaxVisibleItems(pk.count())
    pk.currentIndexChanged.connect(lambda _i: pk.setToolTip(pk.currentText()))
    pk.setToolTip(pk.currentText())
    return pk


def set_combo(combo, value):
    for i in range(combo.count()):
        if combo.itemData(i) == value:
            combo.setCurrentIndex(i)
            return


def template_choices(world, bodies_only=True):
    out = []
    for key, name, prof, level, has_body in sandbox.templates(world):
        if bodies_only and not has_body:
            continue
        label = f"{name or key}  [{sandbox.ABBREV.get(prof, '-')} L{level}]"
        if not name:
            label += "  (unwatched)"
        out.append((label, key))
    out.sort(key=lambda p: (not p[0][0].isupper(), p[0].lower()))
    return out


def weapon_keys(world):
    armour = ("_body", "_boots", "_legs", "_gloves", "_head", "backpack", "costume")
    return [k for k in sorted(world.rows("item")) if not any(w in k for w in armour)]


def form_layout():
    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(10)
    return form


# ---------------------------------------------------------------- Skills

class SkillsTab(QWidget):
    """The ACCOUNT library: every player-usable skill, ticked = unlocked."""
    changed = Signal()

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        outer = orchui.page_layout(self)
        head = QHBoxLayout()
        head.addWidget(role_label("Skill library", "title"))
        head.addStretch(1)
        self.count = chip("", "info")
        head.addWidget(self.count)
        outer.addLayout(head)
        outer.addWidget(caption(
            "Unlocked account-wide; the character's bar and every hero's are filled in game "
            "from these.",
            tip="The account's unlock set (0x001D). A hero's usable library is its own list "
                "plus this one (herolib.hero_library)."))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter by name or id")
        self.filter.setToolTip("Matches a skill's name, id, profession or attribute, or its "
                               "grade in the pills' words (modelled, label).")
        self.filter.setClearButtonEnabled(True)
        self.filter.addAction(orchui.tinted_icon("search"), QLineEdit.LeadingPosition)
        self.filter.setAccessibleName("Filter skills")
        self.prof = QComboBox()
        self.prof.setAccessibleName("Profession filter")
        self.prof.addItem("Every profession", 0)
        for pid, name in sandbox.PROFESSIONS.items():
            self.prof.addItem(f"{name} ({sandbox.ABBREV[pid]})", pid)
        self.prof.addItem("Common (no profession)", -1)
        self.prof.setMaxVisibleItems(self.prof.count())      # twelve rows, none scrolled
        # named with the pills' own two words: the filter keeps BOTH grades, and a
        # label row must never read as modelled (deskwork D4 step 4)
        self.modelled_only = QCheckBox("Modelled or label")
        self.modelled_only.setToolTip("Only the skills this server acts: a hand-verified row "
                                      "(modelled) or a parsed label (label).")
        self.all_b = button("Unlock shown", "quiet",
                            tip="Unlock every skill the filter shows.")
        self.none_b = button("Lock shown", "quiet",
                             tip="Lock every skill the filter shows.")
        self.party_b = button("Unlock party only", "quiet",
                              tip="Unlock the character's and the heroes' professions plus the "
                                  "common skills, and lock every other skill, including ones "
                                  "the filter hides.")
        # the filter takes the row's slack first and the spacer what is left
        # (stretched 3 : 1 : 1 against the combo and the spacer, the row's one
        # text input was 176 px at 1,000 px, its placeholder elided, beside
        # 68 px of nothing) -- so the split between the filters and the bulk
        # verbs is a fixed 16 px past the row's own 8, not the spacer's: the
        # filter reaches its cap only from 1,250 px, and below that the spacer
        # had nothing, so 'Modelled or label' stood 9 px from 'Unlock shown'
        # and 12 from its own filters, as one of the verbs
        self.filter.setMaximumWidth(480)
        row.addWidget(self.filter, 1)
        row.addWidget(self.prof, 0)
        row.addWidget(self.modelled_only)
        row.addSpacing(16)
        row.addStretch(0)
        for b in (self.all_b, self.none_b, self.party_b):
            row.addWidget(b)
        outer.addLayout(row)
        self.list = orchui.PlaceholderList("No skill matches this filter.")
        self.delegate = orchui.SkillDelegate(self.list)
        self.list.setItemDelegate(self.delegate)
        self.list.setUniformItemSizes(True)
        self.list.setAccessibleName("Skills")
        outer.addWidget(self.list, 1)
        # the key shows the pills themselves, each with a few words
        key = QHBoxLayout()
        key.setSpacing(8)
        for grade, kind, gloss in (("hand", "good", "a hand-verified row"),
                                   ("label", "info", "a parsed label, not hand-verified")):
            key.addWidget(chip(orchui.GRADE_TEXT[grade], kind, tip=GRADE_TIP[grade]))
            key.addWidget(role_label(gloss, "caption"))
            key.addSpacing(12)
        key.addWidget(role_label("unmarked: draws and times, does nothing more", "caption",
                                 tip=GRADE_TIP[None]))
        key.addStretch(1)
        outer.addLayout(key)
        self.party_professions = set()
        every = sorted(int(k) for k in names.world.rows("skills"))
        for sid in sorted(every, key=lambda s: names.slot_label(s).lower()):
            it = QListWidgetItem(names.slot_label(sid))
            it.setData(ROLE_ID, sid)
            it.setData(ROLE_PARTS, names.skill_parts(sid))
            it.setToolTip(names.skill_tip(sid))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.list.addItem(it)
        self.delegate.set_column(it.data(ROLE_PARTS) for it in self._items())
        self.filter.textChanged.connect(self._filter)
        self.prof.currentIndexChanged.connect(self._filter)
        self.modelled_only.toggled.connect(self._filter)
        self.all_b.clicked.connect(lambda: self._set_shown(True))
        self.none_b.clicked.connect(lambda: self._set_shown(False))
        self.party_b.clicked.connect(self.unlock_party)
        self.list.itemChanged.connect(lambda _it: self._count())
        self._filter()

    def _items(self):
        return [self.list.item(i) for i in range(self.list.count())]

    def _filter(self, *_a):
        text = self.filter.text().lower()
        prof = int(self.prof.currentData() or 0)
        only = self.modelled_only.isChecked()
        for it in self._items():
            sid = int(it.data(ROLE_ID))
            sp = self.names.skill_profession(sid)
            hide = ((text and text not in it.text().lower())
                    or (prof > 0 and sp != prof) or (prof == -1 and sp != 0)
                    or (only and sid not in self.names.modelled
                        and sid not in self.names.labelled))
            it.setHidden(bool(hide))
        self.list.viewport().update()
        self._count(emit=False)                 # a view of the same spec: nothing changed

    def _count(self, emit=True):
        """The chip; and `changed`, which the header summary and the Run tab's
        'Changed since compile' read -- so only when the UNLOCKS moved, never
        when a filter did (ids() reads hidden rows the same as shown ones)."""
        n = sum(1 for it in self._items() if it.checkState() == Qt.Checked)
        total = self.list.count()
        shown = self.list.visible_count()
        tail = f"  ·  {shown:,} shown" if shown != total else ""
        set_chip(self.count, f"{n:,} of {total:,} unlocked{tail}", "info" if n else "warn")
        if emit:
            self.changed.emit()

    def _bulk(self, write, emit=None):
        """One write of many boxes is ONE count and ONE `changed`: the list's
        signals are held while `write` runs. Per item, each of the ~985 boxes
        a party-only unlock flips ran the O(n) count and marked the compile
        stale -- 18 s for the button, and a failed Open blocked the window
        56 s doing it twice. `emit` None says the signal only when the
        unlocks moved, so a click that changes nothing leaves a fresh
        'Compiled' green; the view repaints off the model either way."""
        before = self.ids() if emit is None else None
        self.list.blockSignals(True)
        try:
            write()
        finally:
            self.list.blockSignals(False)
        self._count(emit=emit if emit is not None else self.ids() != before)

    def _set_shown(self, on):
        def write():
            for it in self._items():
                if not it.isHidden():
                    it.setCheckState(Qt.Checked if on else Qt.Unchecked)
        self._bulk(write)

    def set_party_professions(self, profs):
        self.party_professions = set(int(p) for p in profs if p)

    def unlock_party(self):
        want = self.party_professions | {0}

        def write():
            for it in self._items():
                sp = self.names.skill_profession(int(it.data(ROLE_ID)))
                it.setCheckState(Qt.Checked if sp in want else Qt.Unchecked)
        self._bulk(write)

    def ids(self):
        return sorted(int(it.data(ROLE_ID)) for it in self._items()
                      if it.checkState() == Qt.Checked)

    def set_ids(self, ids):
        want = set(int(s) for s in ids)

        def write():
            for it in self._items():
                it.setCheckState(Qt.Checked if int(it.data(ROLE_ID)) in want else Qt.Unchecked)
        self._bulk(write, emit=True)            # a load is a change, moved or not


# ---------------------------------------------------------------- Party

class PartyTab(QWidget):
    """The character, and which heroes are unlocked (each with a profession
    and a body). No bars, no ranks: those are the in-game panels' job."""

    COLS = ("", "#", "Hero", "Profession", "Body", "Level")
    # Below STACK_BELOW the Character card goes ABOVE the table, as main laid
    # it out: side by side, the table cannot hold a whole profession, a whole
    # body and a whole hero name beside a 320 px card. _fit_columns derives
    # the width from what the row holds (a constant 1,120, "1,114 measured",
    # outlived the columns it was measured with: from 1,120 to 1,129 px, side
    # by side, 11 of 39 names elided).
    CARD_W = 320

    def __init__(self, names, on_change, parent=None):
        super().__init__(parent)
        self.names = names
        self.on_change = on_change
        world = names.world
        self.outer = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.outer.setContentsMargins(16, 16, 16, 12)
        self.outer.setSpacing(16)
        self.stacked = None

        self.character = cc = card("Character")
        self.primary = profession_picker()
        self.secondary = profession_picker(none=True)
        self.level = QSpinBox()
        self.level.setRange(1, sandbox.LEVEL_MAX)
        self.level.setValue(3)
        self.level.setToolTip("Sets the attribute points and the health.")
        weapons = weapon_keys(world)
        self.weapon = Picker(chars=12)
        self.weapon.set_choices([(k, k) for k in weapons])
        self.offhand = Picker(chars=12)
        self.offhand.set_choices([("(none)", "")] + [(k, k) for k in weapons
                                                     if "shield" in k or "focus" in k])
        self.fields = []
        for text, w in (("Primary", self.primary), ("Secondary", self.secondary),
                        ("Level", self.level), ("Weapon", self.weapon),
                        ("Off-hand", self.offhand)):
            lab = QLabel(text)
            lab.setBuddy(w)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.fields.append((lab, w))
        self.cgrid = QGridLayout()
        self.cgrid.setHorizontalSpacing(14)
        self.cgrid.setVerticalSpacing(10)
        cc.body.addLayout(self.cgrid)
        cc.body.addSpacing(4)
        cc.body.addWidget(caption(
            "Bars and ranks are set in game (K) and kept between runs.",
            tip="The Skills panel (K), the attribute panel and each hero's own panel. Every "
                "sandbox run passes --persist; the store is vault/state/characters/."))
        cc.body.addStretch(1)
        # top-aligned: a card stretched to the table's height was 58 % empty
        self.outer.addWidget(cc, 0, Qt.AlignTop)

        self.count = chip("", "info")
        self.heroes_card = hc = card("Heroes", trailing=self.count)
        hc.body.addWidget(caption(
            f"Tick a hero to unlock them and add them to the party, up to "
            f"{sandbox.HEROES_MAX}.",
            tip=f"The client's cap is {sandbox.HEROES_MAX} heroes (PtPlayer:332). Their bars "
                f"and ranks are set in game too."))
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setProperty("role", "flat")
        self.table.setHorizontalHeaderLabels(self.COLS)
        hh = self.table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setHighlightSections(False)
        self.table.horizontalHeaderItem(1).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # Profession and Body are sized for their widest item once the rows are
        # built (_fit_columns: a cell widget takes the cell's width whatever its
        # hint, so a guess clips); the hero's NAME is what yields, as a text
        # item with an honest ellipsis.
        for col, mode, width in ((0, QHeaderView.Fixed, 32), (1, QHeaderView.Fixed, 40),
                                 (2, QHeaderView.Stretch, 0), (3, QHeaderView.Fixed, 0),
                                 (4, QHeaderView.Fixed, 0), (5, QHeaderView.Fixed, 88)):
            hh.setSectionResizeMode(col, mode)
            if width:
                self.table.setColumnWidth(col, width)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAccessibleName("Heroes")
        hc.body.addWidget(self.table, 1)
        self.outer.addWidget(hc, 1)
        self._arrange(False)

        self.rows = {}                         # hero index -> (check, prof, body, level)
        self.name_items = {}
        cat = names.heroes or [(i, 0) for i in range(1, sandbox.HERO_INDEX_MAX + 1)]
        bodies = template_choices(world)
        for idx, _nid in cat:
            r = self.table.rowCount()
            self.table.insertRow(r)
            hero = names.hero_name(idx)
            chk = QCheckBox()
            chk.setAccessibleName(f"Add {hero} to the party")
            prof = profession_picker(short=True)
            prof.setAccessibleName(f"{hero}'s profession")
            body = Picker(chars=20)
            body.set_choices(bodies)
            body.set_value("hatcher")
            body.setAccessibleName(f"{hero}'s body")
            lvl = QSpinBox()
            lvl.setRange(1, sandbox.LEVEL_MAX)
            lvl.setValue(3)
            lvl.setAccessibleName(f"{hero}'s level")
            num = QTableWidgetItem(str(idx))
            num.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            num.setFont(orchui.mono_font(orchtheme.TYPE["caption"]))
            num.setForeground(QColor(orchui.PAL["muted"]))
            num.setFlags(Qt.ItemIsEnabled)
            num.setToolTip(f"Hero index {idx}: what a spec's `hero = {idx}` names")
            name = QTableWidgetItem(hero)
            name.setFlags(Qt.ItemIsEnabled)
            self.table.setCellWidget(r, 0, orchui.centered(chk))
            self.table.setItem(r, 1, num)
            self.table.setItem(r, 2, name)
            self.table.setCellWidget(r, 3, prof)
            self.table.setCellWidget(r, 4, body)
            self.table.setCellWidget(r, 5, lvl)
            chk.toggled.connect(lambda on, i=idx: self._toggled(i, on))
            prof.currentIndexChanged.connect(lambda _i, i=idx: self._prof_changed(i))
            body.currentIndexChanged.connect(lambda _i, i=idx: self._body_changed(i))
            lvl.valueChanged.connect(lambda _v, i=idx: self._prof_changed(i))
            self.rows[idx] = (chk, prof, body, lvl)
            self.name_items[idx] = name
            self._style_row(idx)
        self.primary.currentIndexChanged.connect(lambda _i: self.on_change())
        self.secondary.currentIndexChanged.connect(lambda _i: self.on_change())
        self.level.valueChanged.connect(lambda _v: self.on_change())
        self.weapon.currentIndexChanged.connect(lambda _i: self.on_change())
        self.offhand.currentIndexChanged.connect(lambda _i: self.on_change())
        self._fit_columns()
        self._count()

    def _fit_columns(self):
        """Profession and Body take their widest item plus the chrome a cell
        puts round a combo, read off the style rather than guessed: a literal
        256 held the common bodies and clipped 17 of 48 mid-word, the
        '(unwatched)' tail gone with no ellipsis. The chrome is the style's own
        edit-field inset (frame, padding, the arrow and the cell's combo
        margin: 54 under this sheet), the line edit's 2 px text margins, and
        the item padding the table's delegate keeps clear of a cell widget."""
        _c, prof, body, _l = next(iter(self.rows.values()))
        self.table.ensurePolished()             # the sheet's ::item padding, before any show
        vopt = QStyleOptionViewItem()
        vopt.rect = QRect(0, 0, 100, 40)
        cell = 100 - self.table.style().subElementRect(QStyle.SE_ItemViewItemText, vopt,
                                                       self.table).width()
        for col, combo in ((3, prof), (4, body)):
            combo.ensurePolished()
            fm = combo.fontMetrics()
            need = max(fm.horizontalAdvance(combo.itemText(i)) for i in range(combo.count()))
            opt = QStyleOptionComboBox()
            combo.initStyleOption(opt)
            opt.rect = QRect(0, 0, 100, opt.rect.height())
            field = combo.style().subControlRect(QStyle.CC_ComboBox, opt,
                                                 QStyle.SC_ComboBoxEditField, combo).width()
            self.table.setColumnWidth(col, need + (100 - field) + 4 + cell)
        # ...and the stack edge from what the row now needs: the page margins,
        # the card and the gap to it, the heroes card's chrome, the fixed
        # columns, the widest hero name in its cell, and the table's bar (39
        # rows of 40 px scroll at any height). Measured: the first width with
        # no name elided, to the pixel
        widest = max(self.table.fontMetrics().horizontalAdvance(it.text())
                     for it in self.name_items.values())
        self.heroes_card.ensurePolished()       # the sheet's 1 px border, before any show
        m, cm = self.outer.contentsMargins(), self.heroes_card.layout().contentsMargins()
        self.STACK_BELOW = (m.left() + m.right() + self.CARD_W + self.outer.spacing()
                            + cm.left() + cm.right() + 2 * self.heroes_card.frameWidth()
                            + sum(self.table.columnWidth(c) for c in (0, 1, 3, 4, 5))
                            + widest + cell + self.table.verticalScrollBar().sizeHint().width())

    def _arrange(self, stacked):
        """Side by side (a 320 px card, five form rows) or stacked (a full-width
        card, the form three to a row so it stays short: two rows, not the
        three that left a 39-row table 4.9 rows at 1,000 x 720)."""
        if stacked == self.stacked:
            return
        self.stacked = stacked
        while self.cgrid.count():
            self.cgrid.takeAt(0)
        cc = self.character
        if stacked:
            self.outer.setDirection(QBoxLayout.TopToBottom)
            cc.setMinimumWidth(0)
            cc.setMaximumWidth(16777215)
            for i, (lab, w) in enumerate(self.fields):
                r, c = divmod(i, 3)
                self.cgrid.addWidget(lab, r, 2 * c)
                self.cgrid.addWidget(w, r, 2 * c + 1)
            for c in (1, 3, 5):
                self.cgrid.setColumnStretch(c, 1)
            # a label after the first in its row belongs to the field on its
            # RIGHT: its column holds 16 px more than its widest label, and
            # right alignment puts the room on the far side (the grid's one
            # 14 px spacing had 'Secondary' 15 px from Primary's field and 14
            # from its own -- label, field, label, field, with no pairs)
            for c in (2, 4):
                widest = max(lab.sizeHint().width() for i, (lab, _w) in enumerate(self.fields)
                             if 2 * (i % 3) == c)
                self.cgrid.setColumnMinimumWidth(c, widest + 16)
        else:
            self.outer.setDirection(QBoxLayout.LeftToRight)
            cc.setFixedWidth(self.CARD_W)
            for i, (lab, w) in enumerate(self.fields):
                self.cgrid.addWidget(lab, i, 0)
                self.cgrid.addWidget(w, i, 1)
            self.cgrid.setColumnStretch(1, 1)
            for c in (3, 5):
                self.cgrid.setColumnStretch(c, 0)
            for c in (2, 4):
                self.cgrid.setColumnMinimumWidth(c, 0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._arrange(self.width() < self.STACK_BELOW)

    def unlocked(self):
        return [i for i, (chk, _p, _b, _l) in self.rows.items() if chk.isChecked()]

    def _style_row(self, idx):
        """A locked hero's row is quiet and its editors off: what the spec will
        carry is exactly what reads as live."""
        chk, prof, body, lvl = self.rows[idx]
        on = chk.isChecked()
        for w in (prof, body, lvl):
            w.setEnabled(on)
        self.name_items[idx].setForeground(QColor(orchui.PAL["text" if on else "muted"]))
        f = self.name_items[idx].font()
        f.setWeight(QFont.DemiBold if on else QFont.Normal)
        self.name_items[idx].setFont(f)

    def _toggled(self, idx, on):
        if on and len(self.unlocked()) > sandbox.HEROES_MAX:
            self.rows[idx][0].setChecked(False)
            set_chip(self.count, f"{sandbox.HEROES_MAX} of {sandbox.HEROES_MAX} in the party "
                                 f"— the client's cap", "warn",
                     tip=f"The client allows {sandbox.HEROES_MAX} heroes (PtPlayer:332).")
            win = self.window()
            if isinstance(win, QMainWindow):
                win.statusBar().showMessage(
                    f"The client allows {sandbox.HEROES_MAX} heroes in the party — untick one "
                    f"first.", 6000)
            return
        self._style_row(idx)
        self._count()
        self.on_change()

    def _count(self):
        n = len(self.unlocked())
        set_chip(self.count, f"{n} of {sandbox.HEROES_MAX} in the party", "info",
                 tip=f"The client's cap is {sandbox.HEROES_MAX} heroes (PtPlayer:332).")

    def _prof_changed(self, idx):
        if self.rows[idx][0].isChecked():
            self.on_change()

    def _body_changed(self, idx):
        # A body carries a profession byte; offer it as the default, never force it.
        chk, prof, body, _l = self.rows[idx]
        row = self.names.world.rows("npc").get(body.value()) or {}
        if row.get("profession") in sandbox.PROFESSIONS and not getattr(body, "_touched", False):
            set_combo(prof, int(row["profession"]))
        self._prof_changed(idx)                 # the body is in the spec whether or not the
                                                # profession moved with it

    def professions(self):
        return (int(self.primary.currentData()), int(self.secondary.currentData() or 0))

    def hero_professions(self):
        return [int(self.rows[i][1].currentData()) for i in self.unlocked()]

    def player_spec(self):
        prim, sec = self.professions()
        # '(none)' is an off-hand of "" and is WRITTEN: TOML has no null, so a
        # None key would leave the file, and a missing key is the profession's
        # default (a shield, for a Warrior) to the compiler and to from_spec
        return {"profession": prim, "secondary": sec, "level": self.level.value(),
                "weapon": self.weapon.value() or None, "offhand": self.offhand.value() or ""}

    def heroes_spec(self):
        out = []
        for idx in self.unlocked():
            chk, prof, body, lvl = self.rows[idx]
            out.append({"hero": idx, "profession": int(prof.currentData()),
                        "body": body.value(), "level": lvl.value()})
        return out

    def from_spec(self, player, heroes):
        set_combo(self.primary, int(player.get("profession", 1)))
        set_combo(self.secondary, int(player.get("secondary", 0)))
        self.level.setValue(int(player.get("level", 3)))
        prim = int(player.get("profession", 1))
        w, o = sandbox.PLAYER_ITEMS_BY_PROFESSION.get(prim, ("starter_sword", "starter_shield"))
        self.weapon.set_value(player.get("weapon") or w)
        # a key that is PRESENT and empty is no off-hand, as party_row reads it;
        # only a missing key is the profession's default (an `or` here read
        # both the same way, and a failed Open's restore re-armed the shield)
        self.offhand.set_value((player["offhand"] if "offhand" in player else o) or "")
        for idx, (chk, _p, _b, _l) in self.rows.items():
            chk.setChecked(False)
        for h in heroes or []:
            idx = int(h.get("hero", 0))
            if idx not in self.rows:
                continue
            chk, prof, body, lvl = self.rows[idx]
            body.set_value(h.get("body") or "hatcher")
            body._touched = True
            hp = int(h.get("profession") or
                     (self.names.world.rows("npc").get(h.get("body")) or {}).get("profession") or 1)
            set_combo(prof, hp)
            lvl.setValue(int(h.get("level", 3)))
            chk.setChecked(True)
        for idx in self.rows:
            self._style_row(idx)
        self._count()
        self.on_change()

    def row_values(self):
        """Every hero row's editors, ticked or not -- what to_spec does not
        carry and a load writes only for the heroes it names, so a row the
        failed file wrote would keep its level after the restore."""
        return {i: (prof.currentData(), body.value(), getattr(body, "_touched", False),
                    lvl.value()) for i, (_c, prof, body, lvl) in self.rows.items()}

    def set_row_values(self, values):
        for i, (pd, bv, touched, lv) in values.items():
            _c, prof, body, lvl = self.rows[i]
            body.set_value(bv)                  # reads _touched: put that back after
            body._touched = touched
            set_combo(prof, pd)
            lvl.setValue(lv)


# ---------------------------------------------------------------- Enemies

def scrolled(widget):
    """A page that scrolls when the window is short, with no frame of its own.

    The page's right margin is its gutter; while the page does NOT scroll, the
    bar's width is added to it, so a group page and a hostile page share one
    right edge whether or not the hostile's bar is showing. (A fixed 20 on the
    group page matched only while the hostile page scrolled; from about 960 px
    tall -- a maximized 1080p window -- the 12 px jump came back reversed. A
    bar always on would hold the edge and paint a full-length handle over
    nothing.) The bar's width is its size hint: the sheet's 12, where the
    style's metric still answers Fusion's 16."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(widget)
    vb, lay = area.verticalScrollBar(), widget.layout()
    gutter, bar = lay.contentsMargins().right(), vb.sizeHint().width()

    def follow(_lo=0, hi=None):
        hi = vb.maximum() if hi is None else hi
        m = lay.contentsMargins()
        lay.setContentsMargins(m.left(), m.top(), gutter + (0 if hi > 0 else bar), m.bottom())

    vb.rangeChanged.connect(follow)
    follow()
    return area


class MemberEditor(QWidget):
    """One hostile: its body, its weapon, its bar, its ranks -- one page of the
    Enemies tab's detail pane. Narrow, the Body and Weapon cards stack and the
    bar's slots go to one column, so no picker clips (at 1,000 px two columns
    cut a skill id through its last digit and the weapon's '(none…)' row)."""

    # Below this width (the editor's own) the Body and Weapon cards' pickers
    # cannot hold the widest template (202 px) or the weapon's '(none: the
    # template's swing)' (174): measured fields of 159 and 127 at 640 px, and
    # each grows 1 px per 2 of the editor. The bar sets its own threshold.
    STACK_BELOW = 740

    def __init__(self, names, on_remove, on_change=None, parent=None):
        super().__init__(parent)
        self.names = names
        self.on_change = on_change or (lambda _ed: None)
        self.where = (1, 1)
        self.stacked = None
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 8, 0)
        page.setSpacing(12)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = role_label("", "title")
        self.subtitle = role_label("", "subtitle")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles)
        head.addStretch(1)
        self.remove_b = button("Remove hostile", "danger", icon="trash")
        self.remove_b.clicked.connect(lambda: on_remove(self))
        head.addWidget(self.remove_b, 0, Qt.AlignTop)
        page.addLayout(head)

        self.top = top = QBoxLayout(QBoxLayout.LeftToRight)
        top.setSpacing(12)
        body = card("Body")
        form = form_layout()
        self.template = Picker(chars=10)
        self.template.set_choices(template_choices(names.world))
        self.level = QSpinBox()
        self.level.setRange(0, sandbox.LEVEL_MAX)
        self.level.setValue(2)
        self.health = QSpinBox()
        self.health.setRange(1, 10000)
        self.health.setValue(120)
        self.health.setSuffix(" hp")
        self.boss = QCheckBox("Boss")
        self.boss.setToolTip("The quest's kill objective (corridor_boss). Exactly one hostile, "
                             "in the last group.")
        self.glow = QSpinBox()
        self.glow.setRange(0, sandbox.GLOW_MAX)
        self.glow.setValue(sandbox.DEFAULT_GLOW)
        self.glow.setToolTip(f"0..{sandbox.GLOW_MAX}; the client asserts past "
                             f"{sandbox.GLOW_MAX} (ConstGlow.cpp:42). Boss only.")
        form.addRow("Template", self.template)
        form.addRow("Level", self.level)
        form.addRow("Health", self.health)
        form.addRow("", self.boss)
        form.addRow("Glow", self.glow)
        body.body.addLayout(form)
        body.body.addWidget(caption("The boss is the quest's kill, and it glows."))
        body.body.addStretch(1)

        weapon = card("Weapon")
        wform = form_layout()
        self.weapon_item = Picker(chars=10)
        self.weapon_item.set_choices([("(none: the template's swing)", "")]
                                     + [(k, k) for k in weapon_keys(names.world)])
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.0, 5.0)
        self.speed.setSingleStep(0.05)
        self.speed.setSuffix(" s")
        self.speed.setSpecialValueText("The weapon's")
        self.speed.setMinimumWidth(120)
        self.dlo, self.dhi = QSpinBox(), QSpinBox()
        for s in (self.dlo, self.dhi):
            s.setRange(0, 200)
            s.setMinimumWidth(72)
        self.dlo.setAccessibleName("Damage, low")
        self.dhi.setAccessibleName("Damage, high")
        self.dhi.setValue(0)
        dmg = QHBoxLayout()
        dmg.setSpacing(8)
        dmg.addWidget(self.dlo, 1)
        dmg.addWidget(role_label("to", "caption"))
        dmg.addWidget(self.dhi, 1)
        wform.addRow("Weapon item", self.weapon_item)
        wform.addRow("Attack interval", self.speed)
        wform.addRow("Damage", dmg)
        weapon.body.addLayout(wform)
        weapon.body.addWidget(caption("An interval of 0 uses the weapon's own; damage 0 to 0 "
                                      "uses the item's own range."))
        weapon.body.addStretch(1)
        top.addWidget(body, 1)
        top.addWidget(weapon, 1)
        page.addLayout(top)

        bar = card("Skill bar")
        bar.body.addWidget(caption("From the template's profession and the common skills."))
        self.bar = Bar(names)
        bar.body.addWidget(self.bar)
        page.addWidget(bar)

        self.ranks = Ranks(names)
        ranks = card("Attributes", trailing=self.ranks.chip)
        ranks.body.addWidget(self.ranks)
        page.addWidget(ranks)
        page.addStretch(1)

        self.template.currentIndexChanged.connect(self._template)
        self.level.valueChanged.connect(self.ranks.set_level)
        self.level.valueChanged.connect(lambda _v: self._changed())
        self.boss.toggled.connect(self._boss)
        # every input to_spec reads, not only the three the list shows: the
        # group's roster line, the header summary and the Run tab's 'Changed
        # since compile' all hang off this one path
        for w in (self.health, self.glow, self.speed, self.dhi):
            w.valueChanged.connect(lambda *_a: self._changed())
        # the low bound is in the spec only with a high one: typed first (the
        # natural order) it changes nothing, and must not paint the chip amber
        self.dlo.valueChanged.connect(lambda *_a: self._changed() if self.dhi.value() else None)
        self.weapon_item.currentIndexChanged.connect(lambda _i: self._changed())
        self.bar.changed.connect(self._changed)
        self.ranks.changed.connect(self._changed)
        # the two forms' labels, right-aligned as labels (the form right-aligns
        # the CELL, and a label widened past its text -- _arrange, stacked --
        # would fall back to its own left alignment, 72 px from its field)
        self._labels = [f.itemAt(r, QFormLayout.LabelRole).widget()
                        for f in (form, wform) for r in range(f.rowCount())
                        if f.itemAt(r, QFormLayout.LabelRole) is not None]
        for lab in self._labels:
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._template()
        self._boss(self.boss.isChecked())
        self._arrange(False)

    def _arrange(self, stacked):
        """The Body and Weapon cards side by side, or one above the other --
        and stacked, the two forms share one label column, so their inputs
        start at one x: each form sizes its column to its own widest label
        ('Template' against 'Attack interval'), and two cards in one column
        had ragged input edges 32 px apart. Side by side each keeps its own,
        so the Template field keeps the width the fit law needs at 1,120."""
        if stacked == self.stacked:
            return
        self.stacked = stacked
        self.top.setDirection(QBoxLayout.TopToBottom if stacked else QBoxLayout.LeftToRight)
        for lab in self._labels:
            lab.setMinimumWidth(0)
            # QLabel caches a hint with the minimum width in it, and clearing
            # the width leaves the hint: re-polished while stacked (a sheet
            # change), the fields sat at the stacked x side by side
            lab.setIndent(lab.indent())
        if stacked:
            widest = max(lab.sizeHint().width() for lab in self._labels)
            for lab in self._labels:
                lab.setMinimumWidth(widest)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._arrange(self.width() < self.STACK_BELOW)

    def profession(self):
        row = self.names.world.rows("npc").get(self.template.value()) or {}
        return int(row.get("profession", 0) or 0)

    def display_name(self):
        return self.template.currentText().split("  [")[0] or "hostile"

    def set_where(self, group, member):
        self.where = (group, member)
        self._titles()

    def _titles(self):
        prof = sandbox.PROFESSIONS.get(self.profession(), "No profession")
        g, m = self.where
        self.title.setText(self.display_name())
        self.subtitle.setText(f"{prof}  ·  group {g}, hostile {m}"
                              + ("  ·  the boss" if self.boss.isChecked() else ""))

    def _template(self):
        prof = self.profession()
        self.bar.set_professions((prof,))
        self.ranks.set_professions((prof,), self.level.value())
        self._changed()

    def _boss(self, on):
        self.glow.setEnabled(bool(on))
        self._changed()

    def _changed(self):
        self._titles()
        self.on_change(self)

    def to_spec(self):
        m = {"npc": self.template.value(), "level": self.level.value(),
             "health": self.health.value(),
             "skills": [s for s in self.bar.values() if s],
             "attributes": self.ranks.ranks() or None,
             "weapon_item": self.weapon_item.value() or None,
             "attack_speed": self.speed.value() or None,
             "damage": [self.dlo.value(), self.dhi.value()] if self.dhi.value() else None}
        if self.boss.isChecked():
            m["boss"] = True
            m["glow"] = self.glow.value()
        return m

    def summary(self):
        """One line the group page lists: what the tree beside it does not say."""
        k = sum(1 for s in self.bar.values() if s)
        bits = [f"L{self.level.value()}", f"{self.health.value()} hp",
                f"{k} of {sandbox.BAR_SLOTS} skills"]
        if self.ranks.rules is not None:
            spent = self.ranks.rules.total_spent({a: s.value() for a, s in self.ranks.spins.items()})
            bits.append(f"{spent} of {sandbox.budget_for_level(self.ranks.level)} points")
        bits.append(self.weapon_item.value() or "the template's swing")
        return "  ·  ".join(bits)

    def from_spec(self, m):
        self.template.set_value(m.get("npc"))
        self._template()
        self.level.setValue(int(m.get("level", 2)))
        self.health.setValue(int(m.get("health", 120)))
        self.boss.setChecked(bool(m.get("boss")))
        self.glow.setValue(int(m.get("glow", sandbox.DEFAULT_GLOW)))
        self.weapon_item.set_value(m.get("weapon_item") or "")
        self.speed.setValue(float(m.get("attack_speed") or 0.0))
        d = m.get("damage") or [0, 0]
        self.dlo.setValue(int(d[0]))
        self.dhi.setValue(int(d[1]))
        self.bar.set_values(m.get("skills"))
        self.ranks.set_ranks(m.get("attributes"))
        self._changed()


class GroupEditor(QWidget):
    """One group: its page in the detail pane, and the owner of its hostiles."""

    def __init__(self, owner, index, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.names = owner.names
        self.index = index
        self.members = []
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 8, 0)     # scrolled() adds the bar's width when hidden
        page.setSpacing(12)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = role_label("", "title")
        self.subtitle = role_label("", "subtitle")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles)
        head.addStretch(1)
        # the one Remove for a group, and it asks first when the group holds
        # hostiles: this button sits at the same pixel on the next group's page,
        # and on the page every removal lands on
        self.remove_b = button("Remove group", "danger", icon="trash")
        self.remove_b.clicked.connect(lambda: owner.remove(self, confirm=True))
        head.addWidget(self.remove_b, 0, Qt.AlignTop)
        page.addLayout(head)
        self.note = chip("", "warn")
        self.note.hide()
        nrow = QHBoxLayout()
        nrow.addWidget(self.note)
        nrow.addStretch(1)
        page.addLayout(nrow)
        self.count = chip("", "info")
        box = card("Hostiles", trailing=self.count)
        self.hint = caption("")
        box.body.addWidget(self.hint)
        self.roster = QListWidget()
        self.roster.setProperty("role", "flat")
        self.delegate = orchui.RosterDelegate(self.roster)
        self.roster.setItemDelegate(self.delegate)
        self.roster.setAccessibleName("This group's hostiles")
        self.roster.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.roster.itemClicked.connect(self._pick)
        self.roster.itemActivated.connect(self._pick)
        box.body.addWidget(self.roster)
        page.addWidget(box)
        page.addStretch(1)
        self.set_index(index)
        self._count()

    def _pick(self, it):
        # the tree's selection is the one selection: a row left painted here
        # would read as a second one when the operator comes back to this page
        self.roster.clearSelection()
        self.owner.select(it.data(Qt.UserRole))

    def set_index(self, index):
        self.index = index
        self.title.setText(f"Group {index}")
        for m, ed in enumerate(self.members, 1):
            ed.set_where(index, m)
        self.refresh_note()

    def refresh_note(self):
        """Where the boss is, read off the MEMBERS: the first cut derived it from
        the group's position, so '+ Group' labelled a new, boss-less group
        'holds the boss' while the tree showed the boss in the group above."""
        groups = self.owner.groups
        last = not groups or self is groups[-1]
        has_boss = any(m.boss.isChecked() for m in self.members)
        n_boss = sum(1 for g in groups for m in g.members if m.boss.isChecked())
        where = f"{self.index} of {max(len(groups), self.index)} along the corridor, south to north"
        if has_boss and last:
            where += "  ·  holds the boss"
        elif last and not n_boss:
            where += "  ·  the boss belongs in this group"
        self.subtitle.setText(where)
        if has_boss and n_boss > 1:
            set_chip(self.note, "Only one hostile can be the boss", "warn",
                     tip="The compiler refuses two bosses: exactly one row is the quest's kill "
                         "objective.")
            self.note.show()
        elif has_boss and not last:
            set_chip(self.note, "The boss must be in the last group", "warn",
                     tip="The compiler refuses a boss outside the last group: the quest's kill "
                         "stands at the corridor's north end.")
            self.note.show()
        else:
            self.note.hide()

    def refresh_roster(self):
        self.roster.clear()
        names = []
        for ed in self.members:
            name = ("Boss  ·  " if ed.boss.isChecked() else "") + ed.display_name()
            # the whole line as the item's text (a screen reader's, and what
            # the change law reads); the delegate draws it in two columns
            it = QListWidgetItem(f"{name}   —   {ed.summary()}")
            it.setData(Qt.UserRole, ed)
            it.setData(ROLE_ROSTER, (name, ed.summary()))
            it.setToolTip("Select to edit this hostile.")
            self.roster.addItem(it)
            names.append(name)
        self.delegate.set_column(names)
        rows = max(1, self.roster.count())
        self.roster.setFixedHeight(rows * (self.roster.fontMetrics().height() + 12) + 4)
        self.roster.setVisible(bool(self.members))

    def setTitle(self, text):                 # the old QGroupBox call, kept for callers
        m = re.search(r"\d+", text)
        if m:
            self.set_index(int(m.group(0)))

    def add_member(self, spec=None):
        if len(self.members) >= sandbox.GROUP_SIZE_MAX:
            return None
        ed = MemberEditor(self.names, self.remove, self.owner._member_changed)
        if spec:
            ed.from_spec(spec)
        self.members.append(ed)
        ed.set_where(self.index, len(self.members))
        self.owner._attach(ed)
        self._count()
        self.owner._structure_changed()
        return ed

    def remove(self, ed):
        """Remove a hostile; the selection lands on ITS GROUP's page, never on
        the next hostile, whose unasking 'Remove hostile' sat under the same
        pixel: a hand that stayed there emptied the group, then the group
        itself, then the next -- eight clicks, the whole encounter, and no
        question. The group's Remove asks while it holds a hostile."""
        self.members.remove(ed)
        self.owner._detach(ed)
        for m, e in enumerate(self.members, 1):
            e.set_where(self.index, m)
        self._count()
        self.owner._structure_changed(select=self)

    def _count(self):
        n = len(self.members)
        empty = "An empty group can't run. Add a hostile (the list's + Hostile) or remove the group."
        set_chip(self.count, f"{n} of {sandbox.GROUP_SIZE_MAX}",
                 "warn" if not n else "info", tip=empty if not n else "")
        self.hint.setText(empty if not n else
                          "A group spawns together. Select a hostile to edit it.")
        self.refresh_roster()

    def to_spec(self):
        return {"members": [m.to_spec() for m in self.members]}

    def from_spec(self, g):
        for m in list(self.members):
            self.remove(m)
        for m in g.get("members") or []:
            self.add_member(m)


class EnemiesTab(QWidget):
    """The encounter as a list on the left and the selected group or hostile
    on the right. The old tab laid four hostile forms side by side in a
    scroll area, each ~940 px wide, so the second always ran off the edge."""
    changed = Signal()

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        self.groups = []
        self._pages = {}                        # editor -> its page in the stack
        self._building = False
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 12)
        outer.setSpacing(16)

        self.count = chip("", "info")
        left = card("Encounter", trailing=self.count)
        left.setFixedWidth(300)
        self.tree = QTreeWidget()
        self.tree.setProperty("role", "flat")
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setAccessibleName("Groups and hostiles")
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self._selected)
        left.body.addWidget(self.tree, 1)
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.add = button("Group", "quiet", icon="plus", name="Add a group",
                          tip=f"Add a group (up to {sandbox.GROUPS_MAX}).")
        self.add_member_b = button("Hostile", "quiet", icon="plus", name="Add a hostile",
                                   tip=f"Add a hostile to the selected group (up to "
                                       f"{sandbox.GROUP_SIZE_MAX}).")
        # one verb each: the adds live here, the Remove on the page of the thing
        # it removes (an unlabelled x here, 6 px from + Hostile, removed
        # whatever was selected without asking -- and the selection after a
        # removal was the next GROUP, so three clicks emptied the encounter)
        self.add.clicked.connect(lambda: self.select(self.add_group()))
        self.add_member_b.clicked.connect(self._add_member_here)
        for b in (self.add, self.add_member_b):
            btns.addWidget(b)
        btns.addStretch(1)
        left.body.addLayout(btns)
        left.body.addWidget(caption("Groups stand along the corridor, south to north. The "
                                    "last group holds the boss at the north end."))
        outer.addWidget(left)

        self.stack = QStackedWidget()
        self.empty = QWidget()
        ev = QVBoxLayout(self.empty)
        ev.addStretch(1)
        t = role_label("No hostile groups", "empty_title")
        t.setAlignment(Qt.AlignCenter)
        ev.addWidget(t)
        c = caption("A run needs at least one group, and the last group's boss is the "
                    "quest's kill.")
        c.setAlignment(Qt.AlignCenter)
        ev.addWidget(c)
        ev.addSpacing(12)                       # the verb stands apart from the sentence
        eb = QHBoxLayout()
        eb.addStretch(1)
        self.empty_add = button("Add a group", icon="plus")
        self.empty_add.clicked.connect(lambda: self.select(self.add_group()))
        eb.addWidget(self.empty_add)
        eb.addStretch(1)
        ev.addLayout(eb)
        ev.addStretch(2)
        self.stack.addWidget(self.empty)
        outer.addWidget(self.stack, 1)
        self._structure_changed()

    # ---- pages

    def _attach(self, ed):
        page = scrolled(ed)
        self._pages[ed] = page
        self.stack.addWidget(page)

    def _detach(self, ed):
        page = self._pages.pop(ed, None)
        if page is not None:
            self.stack.removeWidget(page)
            page.setParent(None)
            page.deleteLater()

    # ---- structure

    def add_group(self, spec=None):
        if len(self.groups) >= sandbox.GROUPS_MAX:
            return None
        building, self._building = self._building, True
        ed = GroupEditor(self, len(self.groups) + 1)
        self.groups.append(ed)
        self._attach(ed)
        try:
            if spec:
                ed.from_spec(spec)
            else:
                ed.add_member()
        finally:
            # restored on EVERY path: a malformed member row used to leave the
            # flag set, and the list, chips and summary froze for the session
            self._building = building
            self._renumber()
            self._structure_changed()
        return ed

    def remove(self, ed, confirm=False):
        """Remove a group. `confirm` (the click path) asks first when the group
        holds hostiles; the selection lands on the neighbouring GROUP's page,
        whose Remove asks while it holds one, so a click repeated at the same
        pixel meets a question. (It landed on the neighbour's first HOSTILE,
        whose Remove asks nothing: an emptied group went without a word, and
        the cascade crossed into the next.)"""
        if confirm and ed.members and not self.ask_remove(ed):
            return False
        at = self.groups.index(ed)
        for m in list(ed.members):
            self._detach(m)
        self.groups.remove(ed)
        self._detach(ed)
        self._renumber()
        near = self.groups[min(at, len(self.groups) - 1)] if self.groups else None
        self._structure_changed(select=near)
        return True

    def remove_box(self, ed):
        n = len(ed.members)
        box = QMessageBox(QMessageBox.Question, f"Remove group {ed.index}",
                          f"Remove group {ed.index} and {n_of(n, 'hostile')} with it?\n\n"
                          f"There is no undo; the spec on disk is untouched until you save.",
                          QMessageBox.Yes | QMessageBox.No, self)
        return box

    def ask_remove(self, ed):
        return self.remove_box(ed).exec() == QMessageBox.Yes

    def _renumber(self):
        for i, g in enumerate(self.groups, 1):
            g.set_index(i)

    def _group_of(self, ed):
        for g in self.groups:
            if ed is g or ed in g.members:
                return g
        return None

    def _add_member_here(self):
        g = self._group_of(self.current()) or (self.groups[-1] if self.groups else None)
        if g is None:
            g = self.add_group()
            self.select(g.members[0] if g and g.members else g)
            return
        self.select(g.add_member())

    # ---- the list

    def current(self):
        items = self.tree.selectedItems()
        return items[0].data(0, Qt.UserRole) if items else None

    def select(self, ed):
        if ed is None:
            return
        for item in self._walk():
            if item.data(0, Qt.UserRole) is ed:
                self.tree.setCurrentItem(item)
                return

    def place(self):
        """The selection as (group index, member index or None): the form
        that survives a rebuild of every editor, which a load is."""
        cur = self.current()
        for gi, g in enumerate(self.groups):
            if cur is g:
                return (gi, None)
            if cur in g.members:
                return (gi, g.members.index(cur))
        return None

    def select_place(self, place):
        if place is None or place[0] >= len(self.groups):
            return
        g, m = self.groups[place[0]], place[1]
        self.select(g if m is None or m >= len(g.members) else g.members[m])

    def _walk(self):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            yield top
            for j in range(top.childCount()):
                yield top.child(j)

    def _member_texts(self, ed):
        abbrev = sandbox.ABBREV.get(ed.profession(), "-")
        tail = f"{abbrev}  L{ed.level.value()}"
        return ed.display_name(), ("boss  ·  " + tail if ed.boss.isChecked() else tail)

    def _decorate(self, item, ed):
        a, b = self._member_texts(ed)
        item.setText(0, a)
        item.setText(1, b)
        item.setForeground(1, QColor(orchui.PAL["muted"]))
        f = item.font(0)
        f.setWeight(QFont.DemiBold if ed.boss.isChecked() else QFont.Normal)
        item.setFont(0, f)
        item.setToolTip(0, f"{ed.template.currentText()}"
                        + ("\nThe boss: the quest's kill objective" if ed.boss.isChecked() else ""))

    def _member_changed(self, ed):
        if self._building:
            return
        for item in self._walk():
            if item.data(0, Qt.UserRole) is ed:
                self._decorate(item, ed)
        for g in self.groups:
            g.refresh_note()
            if ed in g.members:
                g.refresh_roster()
        self.changed.emit()

    def _structure_changed(self, select=None):
        if self._building:
            return
        keep = select if select is not None else self.current()
        self.tree.blockSignals(True)
        self.tree.clear()
        for g in self.groups:
            top = QTreeWidgetItem([f"Group {g.index}", f"{len(g.members)} of "
                                                       f"{sandbox.GROUP_SIZE_MAX}"])
            top.setData(0, Qt.UserRole, g)
            f = top.font(0)
            f.setWeight(QFont.DemiBold)
            top.setFont(0, f)
            top.setForeground(1, QColor(orchui.PAL["muted"]))
            self.tree.addTopLevelItem(top)
            for ed in g.members:
                child = QTreeWidgetItem(["", ""])
                child.setData(0, Qt.UserRole, ed)
                self._decorate(child, ed)
                top.addChild(child)
            top.setExpanded(True)
        self.tree.blockSignals(False)
        set_chip(self.count, f"{len(self.groups)} of {sandbox.GROUPS_MAX} groups",
                 "warn" if not self.groups else "info")
        for g in self.groups:
            g.refresh_note()
        self.add.setEnabled(len(self.groups) < sandbox.GROUPS_MAX)
        alive = [x for g in self.groups for x in [g] + g.members]
        target = keep if keep in alive else (self.groups[0].members[0] if self.groups
                                             and self.groups[0].members else
                                             (self.groups[0] if self.groups else None))
        if target is not None:
            self.select(target)
        self._selected()
        self.changed.emit()

    def _selected(self):
        cur = self.current()
        page = self._pages.get(cur)
        self.stack.setCurrentWidget(page if page is not None else self.empty)
        g = self._group_of(cur)
        self.add_member_b.setEnabled(bool(self.groups) and
                                     (g is None or len(g.members) < sandbox.GROUP_SIZE_MAX))

    def to_spec(self):
        return [g.to_spec() for g in self.groups]

    def from_spec(self, groups):
        self._building = True
        try:
            for g in list(self.groups):
                for m in list(g.members):
                    self._detach(m)
                self._detach(g)
            self.groups = []
            for g in groups or []:
                self.add_group(g)
        finally:
            # whatever loaded is what the list shows, even when a row raised
            self._building = False
            self._renumber()
            self._structure_changed(select=None)


# ---------------------------------------------------------------- Run

LOG_ERROR = re.compile(r"^Traceback|\bERROR\b|\[FAIL\]|Error:|Exception\b")
# What the harness prints that decides how a run ENDED (session.py, runwatch.py),
# and how it prefixes the crash dialog's own line (the chip's hover).
RUN_MARKS = {"retracted": "RUN VERDICT RETRACTED", "crash": "ERROR DIALOG captured",
             "fail": "RUN VERDICT: FAIL"}
ASSERT_PREFIX = ">>> "
BUILD_SLICE = ("Build the slice archive with:  python toolkit/mapdata/compose.py --name slice "
               "--build   (RUNBOOK.md, SLICE-B9); a new run directory needs the elevated cage "
               "step once.")
# The one dialog: its own sentence and the command to type, nothing else on its
# face; the citation and the compiler's words sit behind Show Details.
NO_ARCHIVE = ("There is no slice archive yet, so this cannot launch. Build it with:\n\n"
              "python toolkit/mapdata/compose.py --name slice --build")
# What the Run tab says while the harness comes up. The closing fact is the
# Launch options caption's, on screen before, during and after the run, so it
# is not repeated here (--smoke: no run of four words shared with a caption).
LAUNCH_STATUS = ("The game client is coming up. Hands off the keyboard while the harness "
                 "logs in (it says when); then play.")
STALE_NOTE = "  The spec has changed since; Launch compiles again."
# What a reset says: the sentence, never the store's path (the confirm box
# shows that; the bar is scanned for lore, and a drive path is lore).
RESET_DONE = "Removed the stored character; the next login re-seeds it."


def n_of(n, word, plural=None):
    """'1 note', '2 notes': the count with its noun, never 'note(s)'."""
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def file_stem(path):
    """What the bar calls a spec file: its name, without the directory or the
    extension -- the path is lore, and it goes on a hover (the header's Open
    and Save buttons say where the last one went)."""
    return os.path.splitext(os.path.basename(path))[0]


def write_lines(view, lines):
    """Append [(text, kind)] to a plain-text view, one char format per line --
    never HTML, so a '<' in a process's output is a '<'. The registers are
    weight for structure and a state colour only where it is unambiguous."""
    pal = orchui.PAL
    doc = view.document()
    bar = view.verticalScrollBar()
    at_bottom = bar.value() >= bar.maximum() - 1
    # at the block cap the document trims the top as these go in, and the view
    # keeps its top block NUMBER, so a scrolled-back reader sees the text creep
    # up under them (appendPlainText moves its top block back; this cursor does
    # not). Count the lines about to go, in the bar's own units, and take them
    # off the value read NOW: after the edit the bar holds a value Qt re-derived
    # from the kept block number, which is the reader's only while no line
    # wraps (a log with every third line wrapped crept 2 rows in 10)
    v0 = bar.value()
    cap = doc.maximumBlockCount()
    new_blocks = len(lines) - (1 if doc.isEmpty() else 0)
    trimmed = max(0, doc.blockCount() + new_blocks - cap) if cap else 0
    lost = sum(doc.findBlockByNumber(i).lineCount() for i in range(trimmed))
    # a DETACHED cursor: the view's own cursor (and the operator's selection)
    # stays put, and the view follows new output only if it was at the bottom --
    # appendPlainText's behaviour, which the first cut lost
    cur = QTextCursor(doc)
    cur.beginEditBlock()
    cur.movePosition(QTextCursor.End)
    for text, kind in lines:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(pal[{"head": "text", "note": "warn_text", "error": "error_text",
                                      "quiet": "muted"}.get(kind, "log_fg")]))
        fmt.setFontWeight(QFont.DemiBold if kind in ("head", "echo") else QFont.Normal)
        if not doc.isEmpty():
            cur.insertBlock()
        cur.insertText(text, fmt)
    cur.endEditBlock()
    if at_bottom:
        bar.setValue(bar.maximum())
    elif lost:
        bar.setValue(max(0, v0 - lost))


def compiled_lines(compiled):
    """The compiler's summary, reflowed for reading: each gamesrv flag on its
    own line, the store's notes in the warning register. Nothing is dropped."""
    out = []
    for i, ln in enumerate(sandbox.summary(compiled)):
        s = ln.strip()
        if s.startswith("gamesrv:"):
            out.append(("  gamesrv", "head"))
            flag = []
            for tok in compiled["args"]:
                if tok.startswith("--") and flag:
                    out.append(("    " + " ".join(flag), "body"))
                    flag = []
                flag.append(tok)
            if flag:
                out.append(("    " + " ".join(flag), "body"))
        elif s.startswith(("NOTE:", "STORE:")):
            out.append((ln, "note"))
        else:
            out.append((ln, "head" if i == 0 else "body"))
    out += [("", "body"), ("command", "head"), ("  " + " ".join(compiled["command"]), "body"),
            ("", "body"), (f"overlay  ->  {compiled['overlay_path']}", "head")]
    for ln in compiled["overlay"].splitlines():
        out.append((ln, "quiet" if ln.lstrip().startswith("#") else "body"))
    return out


class RunTab(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        outer = orchui.page_layout(self)
        top = QHBoxLayout()
        top.setSpacing(16)
        opts = card("Launch options")
        form = form_layout()
        self.hold = QSpinBox()
        self.hold.setRange(0, 7200)
        self.hold.setSuffix(" s")
        self.hold.setSpecialValueText("None (until the client closes)")
        self.hold.setFixedWidth(240)            # the special value, whole (175 px measured)
        form.addRow("Time limit", self.hold)
        opts.body.addLayout(form)
        self.hold.valueChanged.connect(self.mark_stale)
        opts.body.addWidget(caption("Closing the game client ends the run and the servers."))
        opts.body.addStretch(1)
        store = card("Stored character")
        # one line down to the window's minimum width (943 px): three words
        # longer, 'fresh.' stood alone on a second line there
        self.stored_cap = caption(
            "What you set in game carries to the next run; a reset starts it fresh.",
            tip="Bars, ranks and hero builds. Every sandbox run passes --persist; the store is "
                "vault/state/characters/. A reset leaves the spec untouched.")
        store.body.addWidget(self.stored_cap)
        self.reset_b = button("Reset stored character…", "danger", icon="trash",
                              name="Reset the stored character")
        row = QHBoxLayout()
        row.addWidget(self.reset_b)
        row.addStretch(1)
        store.body.addLayout(row)
        store.body.addStretch(1)
        top.addWidget(opts, 1)
        top.addWidget(store, 1)
        outer.addLayout(top)

        srow = QHBoxLayout()
        srow.setSpacing(10)
        self.state = chip("Not compiled", "info")
        self.status = QLabel("Compile shows the overlay and the command before anything runs.")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        srow.addWidget(self.state, 0, Qt.AlignTop)
        srow.addWidget(self.status, 1)
        outer.addLayout(srow)

        split = QSplitter(Qt.Vertical)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(10)
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumBlockCount(4000)
        # wraps (main's behaviour): unwrapped, the command and --unlocks are
        # 45,000 px wide, and a horizontal bar sized by those two lines moved
        # 39 px of text per pixel of thumb for the six that overflow by 254
        self.summary.setAccessibleName("Compiled spec")
        self.summary.setPlaceholderText("Compile to see what the server is told.")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(20000)
        self.log.setAccessibleName("Run output")
        self.log.setPlaceholderText("Launch streams the harness output here.")
        for title, note, tip, view in (
                ("Compiled", "what the server is told, what the store holds, then the overlay",
                 None, self.summary),
                ("Output", "streamed from the harness", "session.py's merged output", self.log)):
            pane = QWidget()
            pv = QVBoxLayout(pane)
            pv.setContentsMargins(0, 0, 0, 0)
            pv.setSpacing(6)
            ph = QHBoxLayout()
            # the card titles above sit inside a 16 px margin and a 1 px border
            ph.setContentsMargins(17, 0, 0, 0)
            ph.setSpacing(10)
            ph.addWidget(overline(title))
            ph.addWidget(role_label(note, "caption", tip=tip))
            ph.addStretch(1)
            pv.addLayout(ph)
            pv.addWidget(view, 1)
            split.addWidget(pane)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        outer.addWidget(split, 1)

        self.reset_b.clicked.connect(self.reset)
        self.proc = None
        self.compiled = None
        self._stale = False
        self._ended = False        # a run's verdict is on the chip, not a compile's
        self._partial = ""
        self._marks = set()
        self._assert = None        # the '>>> Assertion:' line of a captured crash
        self.clock = QElapsedTimer()
        self.ticker = QTimer(self)
        self.ticker.setInterval(1000)
        self.ticker.timeout.connect(self._tick)
        self.compile_b = self.launch_b = self.stop_b = None

    def bind(self, compile_b, launch_b, stop_b):
        """The verbs live in the window's header, reachable from every tab."""
        self.compile_b, self.launch_b, self.stop_b = compile_b, launch_b, stop_b
        compile_b.clicked.connect(self.compile)
        launch_b.clicked.connect(self.launch)
        stop_b.clicked.connect(self.stop)
        stop_b.setEnabled(False)

    def _say(self, text, ms=6000):
        self.window.statusBar().showMessage(text, ms)

    def specs_dir(self):
        d = vaultpath.vault_path("sandbox")
        os.makedirs(d, exist_ok=True)
        return d

    def save(self, path=None):
        spec = self.window.to_spec()
        if not path:
            path, _f = QFileDialog.getSaveFileName(
                self, "Save the spec", os.path.join(self.specs_dir(), f"{spec['name']}.toml"),
                "TOML (*.toml)")
        if not path:
            return None
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(sandbox.spec_toml(spec))
        self._say(f"Saved {file_stem(path)}")
        self.window.header.save_b.setToolTip(f"Save this spec as TOML.\nLast saved to {path}")
        return path

    def load(self, path=None):
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "Open a spec", self.specs_dir(),
                                                   "TOML (*.toml)")
        if not path:
            return
        win = self.window
        prev = win.to_spec()
        # ...and what to_spec does not carry, for the restore below: this
        # tab's words (a from_spec marks the compile stale, and a restore is
        # two of them over a spec that did not change), the operator's place
        # in the encounter, and the hero rows a load leaves as it found them
        words = (self._stale, self.state.text(), self.state.property("kind"),
                 self.state.toolTip(), self.status.text(), self.status.toolTip())
        place = win.enemies.place()
        rows = win.party.row_values()
        spec = None
        try:
            spec = sandbox.load_spec(path)       # a TOML error leaves the tabs untouched...
            win.from_spec(spec)
        except Exception as exc:                 # noqa: BLE001 -- said, not swallowed
            why = f"{type(exc).__name__}: {exc}"
            if spec is None:
                self._say(f"Could not open {file_stem(path)}: {why}", 15000)
                return
            # ...but a row that raises inside from_spec does not: the name, the
            # party and the unlocks were written and the encounter torn down
            # before it, so the message would be false, and Save would default
            # to the file that failed. Put the previous spec back (to_spec's
            # own shape, so it cannot raise), and say 'unchanged' only once
            # the window agrees.
            win.from_spec(prev)
            win.party.set_row_values(rows)
            if win.to_spec() != prev:
                self._say(f"Could not open {file_stem(path)} ({why}), and your spec could not "
                          f"be put back whole: check every tab before you save", 15000)
                return
            self._stale = words[0]
            set_chip(self.state, words[1], words[2], tip=words[3])
            self.status.setText(words[4])
            self.status.setToolTip(words[5])
            win.enemies.select_place(place)
            self._say(f"Could not open {file_stem(path)} ({why}); your spec is unchanged",
                      15000)
            return
        win.header.open_b.setToolTip(f"Open a saved spec (TOML).\nLast opened {path}")
        # what the window holds is what Save writes: a fifth group or hostile
        # is dropped at the cap and a template the content lacks becomes the
        # first on the list, without a raise -- so a file the compiler refuses
        # opens as one it accepts, and 'Opened' alone would be the same false
        # word as 'unchanged' above, reached without an exception
        held = set(sandbox.validate(win.to_spec(), win.world))
        lost = [q for q in sandbox.validate(spec, win.world) if q not in held]
        if lost:
            self._say(f"Opened {file_stem(path)}, but the window could not hold all of it "
                      f"({n_of(len(lost), 'change')}: {lost[0]}). Save as a new file to keep "
                      f"the original.", 20000)
            return
        self._say(f"Opened {file_stem(path)}")

    def compile(self):
        spec = self.window.to_spec()
        self.compiled = None
        self._stale = self._ended = False
        try:
            exe, dat = sandbox.run_paths()
            missing = None
        except sandbox.SpecError as exc:
            exe, dat = "(no slice run directory)", "(no slice run directory)"
            missing = str(exc)
        try:
            self.compiled = sandbox.compile_spec(spec, self.window.world, self.specs_dir(),
                                                 exe=exe, dat=dat,
                                                 hold=self.hold.value() or None)
        except sandbox.SpecError as exc:
            self.summary.clear()
            text = str(exc).splitlines() or ["refused"]
            write_lines(self.summary, [(text[0], "head")] + [(t, "error") for t in text[1:]])
            set_chip(self.state, "Refused", "crit", tip="")
            self.status.setText("The compiler refused the spec; the reasons are below. Fix "
                                "them and compile again.")
            self.status.setToolTip("")
            self.window.tabs.setCurrentWidget(self)      # ...so the bar need not say where
            self._say(f"Refused: {n_of(max(1, len(text) - 1), 'reason')}.")
            return None
        self.summary.clear()
        write_lines(self.summary, compiled_lines(self.compiled))
        self.summary.moveCursor(QTextCursor.Start)
        notes = len(self.compiled["store_warnings"])
        about = f"; {n_of(notes, 'note')} about the stored character" if notes else ""
        here = self.window.tabs.currentWidget() is self
        if missing:
            set_chip(self.state, "Compiled — no slice archive", "warn", tip="")
            self.status.setText("There is no slice archive yet, so this cannot launch. Build "
                                "it first (hover here for how).")
            # the compiler's sentence, a paragraph of its own on hover
            self.status.setToolTip(f"{BUILD_SLICE}\n\n{missing[:1].upper()}{missing[1:]}")
            self._say("Compiled, but there is no slice archive yet"
                      + ("." if here else "; the Run tab says how to build it."))
        else:
            set_chip(self.state, "Compiled", "good", tip="")
            # the path is the pane's (its 'overlay ->' line) and the hover's,
            # not the status line's
            self.status.setText(f"The overlay and the command are below{about}.")
            self.status.setToolTip(f"The overlay goes to {self.compiled['overlay_path']}")
            self._say(f"Compiled{about}"
                      + ("." if here else "; the overlay and the command are on the Run tab."))
        return self.compiled

    def mark_stale(self, *_a):
        """The spec changed after a compile: the pane shows the OLD result, and
        a green 'Compiled' would say otherwise. Launch always compiles again.
        A run's verdict is not a compile's: it stays on the chip, with a note
        on the status line; an edit DURING a run is remembered and said when
        the run ends (the first cut let the first keystroke after a crash paint
        'Changed since compile' over 'the client crashed')."""
        if self._stale or self.state.text() == "Not compiled":
            return
        self._stale = True
        if self.proc is not None:
            return
        if self._ended:
            self.status.setText(self.status.text() + STALE_NOTE)
            return
        was = self.state.text()
        set_chip(self.state, "Changed since compile", "warn")
        if was == "Refused":
            self.status.setText("The reasons below are from the previous compile; Launch "
                                "compiles again.")
        elif was.endswith("no slice archive"):    # the build hint stays on hover
            self.status.setText("There is still no slice archive (hover here for how), and "
                                "the pane below shows the previous compile; Launch compiles "
                                "again.")
            return
        else:
            self.status.setText("The pane below shows the previous compile; Launch compiles "
                                "again.")
        self.status.setToolTip("")

    def no_archive_box(self, exc):
        """The dialog a launch with no archive shows (built, not shown: --smoke
        reads its face). One sentence and the command; the citation and the
        compiler's own words behind Show Details."""
        box = QMessageBox(QMessageBox.Warning, "No slice archive", NO_ARCHIVE, parent=self)
        box.setDetailedText(f"{BUILD_SLICE}\n\n{exc}")
        return box

    def launch(self):
        if self.proc is not None:
            return
        if self.compile() is None:
            return
        try:
            sandbox.run_paths()
        except sandbox.SpecError as exc:
            self.no_archive_box(exc).exec()
            return
        sandbox.write_overlay(self.compiled)
        self._start(self.compiled["command"], self.compiled["env"])

    def _start(self, cmd, env):
        """Arm the run's state, switch to the tab, THEN start the harness. On
        Windows a start that fails emits errorOccurred INSIDE start(), so
        _done's cleanup has to be the last thing that runs, not the first:
        the first cut started first and then re-armed the clock and the verbs
        over a harness that never ran, and Stop could not undo it."""
        self.log.clear()
        self._partial = ""
        self._marks = set()
        self._assert = None
        write_lines(self.log, [("$ " + " ".join(cmd), "echo")])
        self.proc = QProcess(self)
        penv = QProcessEnvironment.systemEnvironment()
        for k, v in env.items():
            penv.insert(k, v)
        self.proc.setProcessEnvironment(penv)
        self.proc.setWorkingDirectory(ROOT)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        self.proc.errorOccurred.connect(self._proc_error)
        self._busy(True)
        self.clock.start()
        self.ticker.start()
        self._tick()
        self.window.tabs.setCurrentWidget(self)
        self.status.setText(LAUNCH_STATUS)
        self.status.setToolTip("")
        self.proc.start(cmd[0], cmd[1:])

    def _busy(self, on):
        """Mirror the run onto the verbs that started it: a re-click on a
        running Launch used to vanish without a word."""
        self.launch_b.setEnabled(not on)
        self.launch_b.setText("Running…" if on else "Launch")
        self.compile_b.setEnabled(not on)
        self.stop_b.setEnabled(on)

    def _tick(self):
        secs = self.clock.elapsed() // 1000
        set_chip(self.state, f"Running  {secs // 60}:{secs % 60:02d}", "info")

    def _mark(self, line):
        for key, needle in RUN_MARKS.items():
            if needle in line:
                self._marks.add(key)
        if line.strip().startswith(ASSERT_PREFIX):   # the dialog's own line, for the chip's hover
            self._assert = line.strip()[len(ASSERT_PREFIX):]

    def _read(self):
        data = self._partial + bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        lines = data.replace("\r\n", "\n").split("\n")
        self._partial = lines.pop()
        for ln in lines:
            self._mark(ln)
        write_lines(self.log, [(ln, "error" if LOG_ERROR.search(ln) else "body") for ln in lines])

    def end_state(self, code):
        """(chip text, kind) for a finished run. A hold-until-close run ends
        with a non-zero code when the operator closes the client -- the
        harness retracts its PASS, deliberately -- so the code alone would
        paint every normal session amber. A captured crash outranks exit 0:
        a timed hold whose client asserted ends PASS, exit 0, with the dialog
        captured and nothing retracted (runwatch.hold_open's timer branch)."""
        m = self._marks
        if "stopped" in m:
            return "Stopped", "info"
        if "no start" in m:
            return "Did not start", "crit"
        if "crash" in m:
            return "Ended  ·  the client crashed", "crit"
        if code == 0:
            return "Ended  ·  exit 0", "good"
        if "retracted" in m:
            return "Ended  ·  client closed", "good"
        if "fail" in m:
            return "Ended  ·  the run failed", "warn"
        return f"Ended  ·  exit {code}", "warn"

    def _done(self, code, _status):
        if self._partial:
            self._mark(self._partial)
            write_lines(self.log, [(self._partial, "error" if LOG_ERROR.search(self._partial)
                                    else "body")])
            self._partial = ""
        never_ran = "no start" in self._marks
        if not never_ran:                        # nothing exited: the log already says why
            write_lines(self.log, [("", "body"), (f"[session.py exited with code {code}]",
                                                  "echo")])
        self.ticker.stop()
        text, kind = self.end_state(code)
        set_chip(self.state, text, kind, tip=self._assert if "crash" in self._marks else "")
        self.status.setText("The harness did not start; the reason is in the log below."
                            if never_ran else
                            "The run ended; the report and the server logs are under "
                            "vault/captures/harness/.")
        if self._stale:                          # edited during the run: say it now
            self.status.setText(self.status.text() + STALE_NOTE)
        self.status.setToolTip("")
        self._ended = True
        self.proc = None
        self._busy(False)

    def _proc_error(self, err):
        """A harness that never started emits no `finished`, so Launch stayed
        disabled beside a live-looking clock."""
        if err == QProcess.FailedToStart and self.proc is not None:
            write_lines(self.log, [(f"[the harness did not start: {self.proc.errorString()}]",
                                    "error")])
            self._marks.add("no start")
            self._done(-1, None)

    def stop(self):
        if self.proc is not None:
            self._marks.add("stopped")
            self.proc.kill()
            self._say("Stopped the harness. The next launch replaces any server still running.",
                      8000)

    def reset(self, confirm=True):
        path = sandbox.store_path()
        if not path or not os.path.isfile(path):
            self._say("No stored character to reset.")
            return False
        if confirm:
            ok = QMessageBox.question(
                self, "Reset the stored character",
                f"Delete {path}?\n\nThe next login starts a fresh character: an empty bar, "
                f"every attribute point unspent, no hero builds. The spec is untouched.")
            if ok != QMessageBox.Yes:
                return False
        sandbox.reset_store()
        self._say(RESET_DONE, 8000)
        return True


# ---------------------------------------------------------------- the window

class Header(QFrame):
    """The spec and the verbs, above the tabs so Launch is one click from
    anywhere. Launch is the window's only accent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("role", "header")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(overline("Spec"))
        self.name = QLineEdit("slice")
        self.name.setPlaceholderText("Spec name")
        self.name.setFixedWidth(220)
        self.name.setAccessibleName("Spec name")
        self.name.setToolTip("Names the overlay's directory, vault/sandbox/<name>/, and the "
                             "saved file.")
        row.addWidget(self.name)
        row.addSpacing(4)
        self.open_b = button("Open…", "quiet", icon="open", tip="Open a saved spec (TOML).",
                             name="Open a spec")
        self.save_b = button("Save…", "quiet", icon="save", tip="Save this spec as TOML.",
                             name="Save the spec")
        self.slice_b = button("Load slice", "quiet", icon="reset",
                              tip="Replace every tab with the vertical slice's own setup.")
        for b in (self.open_b, self.save_b, self.slice_b):
            row.addWidget(b)
        row.addStretch(1)
        left.addLayout(row)
        self.summary = role_label("", "subtitle")
        self.summary.setAccessibleName("Spec summary")
        left.addWidget(self.summary)
        lay.addLayout(left, 1)
        verbs = QHBoxLayout()
        verbs.setSpacing(8)
        self.compile_b = button("Compile", icon="compile",
                                tip="Compile the spec. The overlay and the command show on the "
                                    "Run tab before anything runs; a refusal opens it.")
        self.launch_b = button("Launch", "primary", icon="play",
                               tip="Compile, write the overlay and start the harness on the "
                                   "slice archive.")
        self.launch_b.setMinimumWidth(116)
        self.stop_b = button("Stop", "quiet", icon="stop", tip="Kill the harness.")
        for b in (self.compile_b, self.launch_b, self.stop_b):
            verbs.addWidget(b)
        right = QVBoxLayout()
        right.addLayout(verbs)
        right.addStretch(1)
        lay.addLayout(right)


class GutterStatusBar(QStatusBar):
    """A status bar whose message starts at the page gutter. QStatusBar paints
    showMessage's text 6 px in, a number of its own (messageRect) that no
    margin and no sheet moves, while the header, every page and the names
    chip sit at 16 -- the one left edge in the window that did not. Only
    the painting is here; showMessage, currentMessage and the timeout are
    QStatusBar's, so every say site and every law reading the bar is as it
    was."""

    GUTTER = 16                                 # the page's own left gutter

    def paintEvent(self, ev):
        p = QPainter(self)
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_PanelStatusBar, opt, p, self)
        msg = self.currentMessage()
        if msg:
            right = self.width() - 12           # QStatusBar's own bound, then the chip
            for w in self.findChildren(QWidget, "", Qt.FindDirectChildrenOnly):
                if w.isVisible():
                    right = min(right, w.x() - 2)
            p.setPen(self.palette().windowText().color())
            p.drawText(QRect(self.GUTTER, 0, right - self.GUTTER, self.height()),
                       Qt.AlignLeading | Qt.AlignVCenter | Qt.TextSingleLine, msg)


class Window(QMainWindow):
    def __init__(self, world, names):
        super().__init__()
        self.world, self.names = world, names
        self.setWindowTitle("Rurik run orchestrator")
        self.resize(1280, 860)
        self.setStatusBar(GutterStatusBar())
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.header = Header()
        v.addWidget(self.header)
        self.tabs = QTabWidget()
        self.skills = SkillsTab(names)
        self.party = PartyTab(names, self._party_changed)
        self.enemies = EnemiesTab(names)
        self.run = RunTab(self)
        self.tabs.addTab(self.skills, "Skills")
        self.tabs.addTab(self.party, "Party")
        self.tabs.addTab(self.enemies, "Enemies")
        self.tabs.addTab(self.run, "Run")
        v.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.run.bind(self.header.compile_b, self.header.launch_b, self.header.stop_b)
        self.header.open_b.clicked.connect(lambda: self.run.load())
        self.header.save_b.clicked.connect(lambda: self.run.save())
        self.header.slice_b.clicked.connect(lambda: self.from_spec(sandbox.example_spec()))
        if names.why:
            names_chip = chip("Ids only — names unresolved", "warn", tip=names.why)
        else:
            names_chip = chip("Names from your client", "info",
                              tip="Skill, hero and attribute names are read from the pinned "
                                  "client at start; the spec on disk carries ids.")
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        sb.setContentsMargins(0, 0, 16, 3)       # the page's own right gutter
        sb.addPermanentWidget(names_chip)
        self.names_chip = names_chip
        self._summary_timer = QTimer(self)
        self._summary_timer.setSingleShot(True)
        self._summary_timer.setInterval(50)
        self._summary_timer.timeout.connect(self._refresh_summary)
        for sig in (self.skills.changed, self.enemies.changed, self.header.name.textChanged):
            sig.connect(self._summary_timer.start)
            sig.connect(self.run.mark_stale)
        self._refresh_summary()

    def _party_changed(self):
        prim, sec = self.party.professions()
        self.skills.set_party_professions({prim, sec} | set(self.party.hero_professions()))
        self._summary_timer.start()
        if hasattr(self, "run"):
            self.run.mark_stale()

    def spec_summary(self, spec=None):
        spec = spec or self.to_spec()
        p = spec["player"]
        pair = sandbox.PROFESSIONS.get(p["profession"], "?") + (
            "/" + sandbox.PROFESSIONS.get(p["secondary"], "?") if p["secondary"] else "")
        nh = len(spec["heroes"])
        groups = spec["groups"]
        nm = sum(len(g["members"]) for g in groups)
        return (f"{pair}, level {p['level']}   ·   {nh} hero{'es' if nh != 1 else ''}   ·   "
                f"{len(groups)} group{'s' if len(groups) != 1 else ''}, "
                f"{nm} hostile{'s' if nm != 1 else ''}   ·   "
                f"{len(spec['unlocks']):,} of {self.skills.list.count():,} skills unlocked")

    def _refresh_summary(self):
        self.header.summary.setText(self.spec_summary())

    def to_spec(self):
        return {"name": self.header.name.text().strip() or "sandbox",
                "unlocks": self.skills.ids(),
                "player": self.party.player_spec(), "heroes": self.party.heroes_spec(),
                "groups": self.enemies.to_spec()}

    def from_spec(self, spec):
        self.header.name.setText(str(spec.get("name") or "sandbox"))
        self.party.from_spec(spec.get("player") or {}, spec.get("heroes"))
        unl = spec.get("unlocks")
        if unl is None:
            unl = (spec.get("player") or {}).get("unlocks")
        if unl is not None:
            self.skills.set_ids(unl)
        else:
            self.skills.set_ids(int(k) for k in self.world.rows("skills"))
        self.enemies.from_spec(spec.get("groups"))
        self._refresh_summary()


# ---------------------------------------------------------------- smoke

def _pixel(widget, x, y):
    return widget.grab().toImage().pixelColor(x, y).name()


def _near(a, b, tol=14):
    return orchtheme.distance(a, b) <= tol


def _count_near(img, colour, tol=24, box=None):
    """Pixels of `img` within `tol` (raw channel distance) of `colour`."""
    x0, y0, x1, y1 = box or (0, 0, img.width(), img.height())
    target = orchtheme._rgb(colour)
    n = 0
    for y in range(max(0, y0), min(img.height(), y1)):
        for x in range(max(0, x0), min(img.width(), x1)):
            c = img.pixelColor(x, y)
            if max(abs(c.red() - target[0]), abs(c.green() - target[1]),
                   abs(c.blue() - target[2])) <= tol:
                n += 1
    return n


def _diff(a, b):
    w, h = min(a.width(), b.width()), min(a.height(), b.height())
    return sum(1 for y in range(h) for x in range(w) if a.pixelColor(x, y) != b.pixelColor(x, y))


def _moved(win, widget, before, after, rect=None):
    """The largest channel distance any pixel of `widget` (or `rect` in its
    coordinates) moved between two grabs of the WINDOW. A grab of the widget
    alone is a transparent canvas, and on it any fill at all counts as a
    change -- the light tab strip's focus fill sat 3 from the page and counted
    3,000 px; measured on the ground it is painted on, it moved 3."""
    r = rect or widget.rect()
    at = widget.mapTo(win, r.topLeft())
    worst = 0
    for y in range(at.y(), min(before.height(), after.height(), at.y() + r.height())):
        for x in range(at.x(), min(before.width(), after.width(), at.x() + r.width())):
            a, b = before.pixelColor(x, y), after.pixelColor(x, y)
            if a != b:
                worst = max(worst, orchtheme.distance(a.name(), b.name()))
    return worst


def _shifted(win, widget, before, after, rect=None):
    """The highest CONTRAST any pixel of `widget` (or `rect`) makes against
    what it was, between two grabs of the WINDOW. A focus cue is a mark, and
    the theme holds a mark to MARK_FLOOR on its ground; the distance _moved
    reads told a fill from the page (17 in light) that was 1.13:1 to the eye."""
    r = rect or widget.rect()
    at = widget.mapTo(win, r.topLeft())
    best = 1.0
    for y in range(at.y(), min(before.height(), after.height(), at.y() + r.height())):
        for x in range(at.x(), min(before.width(), after.width(), at.x() + r.width())):
            a, b = before.pixelColor(x, y), after.pixelColor(x, y)
            if a != b:
                best = max(best, orchtheme.contrast(a.name(), b.name()))
    return best


def _best_contrast(img, ground, inset=3):
    """The highest contrast any pixel of `img`, `inset` px in from its edges,
    makes against `ground`: a glyph's core ink, whatever the sheet names it."""
    best = 0.0
    for y in range(inset, img.height() - inset):
        for x in range(inset, img.width() - inset):
            best = max(best, orchtheme.contrast(img.pixelColor(x, y).name(), ground))
    return best


def _ink_pixels(img, ground, floor, inset=3):
    """How many pixels of `img`, `inset` px in, clear `floor` on `ground`: the
    glyphs' own count, which a best-pixel reading cannot give (one pixel of
    the right ink passes it)."""
    return sum(1 for y in range(inset, img.height() - inset) for x in range(inset, img.width() - inset)
               if round(orchtheme.contrast(img.pixelColor(x, y).name(), ground), 2) >= floor)


def _ink_span(img, rect, ground, tol=40):
    """(first, last) column of `rect` (in `img`, a grab of the window) holding a
    pixel `tol` or more from `ground`: where painted text starts and ends."""
    g = orchtheme._rgb(ground)
    cols = []
    for x in range(max(0, rect.left()), min(img.width(), rect.right() + 1)):
        for y in range(max(0, rect.top()), min(img.height(), rect.bottom() + 1)):
            c = img.pixelColor(x, y)
            if max(abs(c.red() - g[0]), abs(c.green() - g[1]), abs(c.blue() - g[2])) > tol:
                cols.append(x)
                break
    return (cols[0], cols[-1]) if cols else (None, None)


def _spin_field(sp):
    """A spin box's line edit (QAbstractSpinBox.lineEdit() is protected)."""
    return sp.findChild(QLineEdit)


def _within(widget, cls):
    """Whether `widget` sits under a `cls` (a cell widget under its table)."""
    p = widget.parent()
    while p is not None:
        if isinstance(p, cls):
            return True
        p = p.parent()
    return False


def _field_width(combo):
    """The px a combo's text actually gets: the edit field, or its line edit."""
    if combo.isEditable() and combo.lineEdit() is not None:
        return combo.lineEdit().width() - 4
    opt = QStyleOptionComboBox()
    combo.initStyleOption(opt)
    return combo.style().subControlRect(QStyle.CC_ComboBox, opt,
                                        QStyle.SC_ComboBoxEditField, combo).width()


def _fits(combo, text):
    return combo.fontMetrics().horizontalAdvance(text) <= _field_width(combo)


def used_roles(win):
    # every widget, not only the window's children: a completer's popup is a
    # top-level of its own
    return {str(w.property("role")) for w in QApplication.allWidgets()
            if w.property("role") is not None}


SURFACE_LORE = re.compile(r"--[a-z]|\.py\b|\.md\b|\.toml\b|\b[A-Za-z]:[\\/]|`|\b[A-Z]{3,}-[A-Z0-9]+\b"
                          r"|\b0x[0-9A-Fa-f]+\b")
# The most a caption may run to: one constraint and one pointer, two clauses
# (the research's measure is 74 characters a line; the longest kept here is
# under 100). A 209-character legend and a 137-character two-sentence card
# caption were what the rule is for.
CAPTION_MAX = 110


def surface_lore(win):
    """Visible words that belong on hover: flags, file names and drive paths,
    idents, hex ids."""
    out = []
    for w in win.findChildren(QWidget):
        if not w.isVisibleTo(win) or isinstance(w, QPlainTextEdit):
            continue
        text = w.text() if isinstance(w, (QLabel, QPushButton, QCheckBox)) else ""
        if text and SURFACE_LORE.search(text):
            out.append(text[:80])
    msg = win.statusBar().currentMessage()
    if msg and SURFACE_LORE.search(msg):
        out.append(msg[:80])
    return out


def printed_strings(path):
    """Every string a print() call in the file at `path` can put on a line:
    the constants inside the call, an f-string's literal parts among them.
    Read through the syntax tree, so a comment or a docstring quoting an old
    line is not a print site (a regex over the text took a commented-out
    print for one)."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
            out += [c.value for c in ast.walk(node)
                    if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    return out


def _real_wheel(win, widget, delta=-120):
    """A spontaneous wheel, the way the OS sends one (Windows): Qt never
    propagates a synthesized wheel, so sendEvent cannot test the guard's
    scrolling half. False when this platform cannot send one."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    local = widget.mapTo(win, QPoint(widget.width() // 2, widget.height() // 2))
    dpr = win.devicePixelRatioF()
    pt = wintypes.POINT(int(local.x() * dpr), int(local.y() * dpr))
    hwnd = wintypes.HWND(int(win.winId()))
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    lparam = ((pt.y & 0xFFFF) << 16) | (pt.x & 0xFFFF)
    user32.SendMessageW(hwnd, 0x020A, wintypes.WPARAM((delta & 0xFFFF) << 16),
                        wintypes.LPARAM(lparam))
    return True


# The laws a healthy --smoke executes, less the ones behind a declared skip --
# set from a green run of this tree, never from a wish (toolkit/checks.py:
# "set the floor to its mandatory core and let the optional sections declare
# skips"). The gated laws, by gate: the grade marks 5 (a vault overlay with
# label rows), the inactive real wheel 1 (Windows, a page that scrolls), the
# over-budget hostile 1 (an attribute table), the encounter list's focus 1,
# Launch's ring and the tab strip's cue 3, the active-window wheel 3, the
# four popups 4 -- 18 of the green run's 150. A gated law that skips is
# printed in the verdict; a mandatory law that stops running is a FAIL naming
# the shortfall, which "0 failure(s)" never was.
SMOKE_FLOOR = 132


def smoke(win, app, out_dir):
    """`--smoke`: drive every panel once with the window up, then exit.

    A window nobody has clicked through is a window that may not open; this
    runs the click path in code so a refactor cannot leave a dead tab behind
    a green suite. Writes a screenshot and prints one line per check, and
    rules through the house ledger (toolkit/checks.py): a law that cannot run
    declares a skip, printed in the verdict, and a run that executes fewer
    laws than SMOKE_FLOOR fails naming the shortfall -- "0 failure(s)" once
    said nothing about whether 124 or 115 laws had run. Never writes into
    the working tree.

    The LOOK is checked here too, as laws rather than intentions (Dream-
    World-IX: "a law in a docstring is a wish"): both palettes clear their
    contrast floors, the sheet has none of the silent QSS faults, every role
    the window uses is styled and every styled role is used, there is exactly
    one accent, text fits the combos and spin boxes that hold it, and the
    accent, a checked box (at rest and hovered), a well, a hovered danger
    button's ink, a pressed button's relief, a log's scroll corner, a popup's
    edge, the list's pills and its placeholder are what the tokens say --
    measured off the rendered pixels, because a property is not a rendered
    colour, and focus off grabs of the WINDOW, because a widget's own grab is
    a transparent canvas on which any fill counts. The wheel is sent as the
    OS sends it, with the window inactive and then ACTIVE (the regime in use,
    where Qt hands a hovered combo focus before any filter runs). Each law
    was a finding of a review that came after the first cut, or after the
    fix pass; a check that needs keyboard focus, or a real OS wheel, says
    [SKIP] when it cannot have that. The window is native but never on the
    screen (WA_DontShowOnScreen, as --snap renders). One palette a process:
    --theme auto follows the OS, so a law red in one palette only is seen by
    running both."""
    out_dir = vaultpath.resolve_out(out_dir, what="smoke output")
    os.makedirs(out_dir, exist_ok=True)
    led = checks.Ledger("orchestrator --smoke", floor=SMOKE_FLOOR)
    pal = orchui.PAL

    def check(cond, label):
        led.ok(cond, label)

    def skip(label, why):
        led.skip(label, why)

    def settle(n=3):
        for _ in range(n):
            app.processEvents()

    def focus(w):
        w.setFocus(Qt.TabFocusReason)
        settle()
        return win.isActiveWindow() and w.hasFocus()

    def activate():
        """The window active, waited for rather than assumed: the OS hands
        activation back on its own clock, and five turns of the loop once
        left a popup law skipped whole while the laws before it had run."""
        win.activateWindow()
        win.raise_()
        t_end = time.perf_counter() + 2.0
        while not win.isActiveWindow() and time.perf_counter() < t_end:
            settle(1)
            time.sleep(0.01)
        return win.isActiveWindow()

    def strays():
        """Windows of their own besides this one (a hidden completer popup is
        not one): a label shown with no parent becomes one, and the review
        found five on the desktop -- one per hostile -- keeping the app alive
        after the main window closed."""
        return [w for w in QApplication.topLevelWidgets()
                if w is not win and w.isVisible() and w.property("role") != "popup"]

    def hint_housed(ed):
        """The Attributes hint lives in the hostile's own page, with words."""
        h = ed.ranks.hint
        return (h.window() is win and h.isVisibleTo(win.enemies._pages[ed])
                and "points to spend" in h.text())

    # native, but never on the screen: nothing flashes on a shared desktop, and
    # no other window can take keyboard focus away in the middle of a run
    win.setAttribute(Qt.WA_DontShowOnScreen, True)
    win.show()
    settle()
    win.from_spec(sandbox.example_spec())
    settle()
    m0 = win.enemies.groups[0].members[0]
    check(not strays() and hint_housed(m0),
          f"the slice opens ONE window: every hostile's Attributes hint is a child of its page "
          f"({len(strays())} stray top-level widget(s))")
    spec = win.to_spec()
    check(spec["player"]["profession"] == 1 and spec["player"]["level"] == 3,
          "the slice loads into the Party tab")
    check("skills" not in spec["player"] and "attributes" not in spec["player"],
          "the character carries NO bar and NO ranks (the in-game panels' job)")
    check(len(spec["heroes"]) == 1 and spec["heroes"][0]["hero"] == 3
          and spec["heroes"][0]["profession"] == 3 and spec["heroes"][0]["body"] == "academy_monk"
          and "skills" not in spec["heroes"][0], "the Monk hero is unlocked with its body, no bar")
    check(len(spec["groups"]) == 3 and spec["groups"][2]["members"][0].get("boss"),
          "three groups, the boss last")
    n_all = win.skills.list.count()
    check(n_all >= 1000 and len(spec["unlocks"]) == n_all,
          f"the Skills tab lists every player-usable skill ({n_all}), all unlocked by default")
    seen_roles = set()
    lore = []
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        settle()
        seen_roles |= used_roles(win)
        lore += surface_lore(win)

    # ---- the Skills tab's GRADES (SKILLS-LT): the pills' own words find their
    # rows through the filter, and the "modelled or label" filter keeps both
    # and nothing else
    listed = {int(it.data(ROLE_ID)) for it in win.skills._items()}
    hand_ids, label_ids = win.names.modelled & listed, win.names.labelled & listed
    win.tabs.setCurrentWidget(win.skills)
    settle()
    if hand_ids and label_ids:
        h0, l0 = sorted(hand_ids)[0], sorted(label_ids)[0]
        found = {}
        for word in ("modelled", "label"):
            win.skills.filter.setText(word)
            settle()
            found[word] = {int(it.data(ROLE_ID)) for it in win.skills._items() if not it.isHidden()}
        win.skills.filter.setText("")
        settle()
        check(found["modelled"] == hand_ids and found["label"] == label_ids
              and not any("modelled" in it.text() for it in win.skills._items()
                          if int(it.data(ROLE_ID)) in label_ids),
              f"typing a pill's word into the filter finds that tier and nothing else "
              f"('modelled' {len(found['modelled'])} of {len(hand_ids)}, 'label' "
              f"{len(found['label'])} of {len(label_ids)}), and no label row reads as modelled")
        sh, sl = win.names.slot_label(h0), win.names.slot_label(l0)
        check("· modelled" in sh and "· label" in sl and "modelled" not in sl,
              "a bar slot names the grade in the pills' words, and a label row never "
              "reads as modelled")
        win.skills.modelled_only.setChecked(True)
        settle()
        shown_ids = {int(it.data(ROLE_ID)) for it in win.skills._items() if not it.isHidden()}
        check(shown_ids == hand_ids | label_ids,
              f"'modelled or label' shows the hand rows and the label rows and nothing else "
              f"({len(hand_ids)} + {len(label_ids)})")
        # treatment and control on the SAME row: painted with its grade, then
        # with the grade taken away. A colour count cannot do this -- in dark,
        # the label pill's edge sits 4 from the hover fill.
        lst, vp = win.skills.list, win.skills.list.viewport()
        pill_px, pill_x = {}, {}
        for grade in ("hand", "label"):
            item = next((it for it in win.skills._items() if not it.isHidden()
                         and it.data(ROLE_PARTS)[2] == grade
                         and vp.rect().contains(lst.visualItemRect(it))), None)
            if item is None:
                continue
            r = lst.visualItemRect(item)
            parts = item.data(ROLE_PARTS)
            with_pill = vp.grab(r).toImage()
            item.setData(ROLE_PARTS, (parts[0], parts[1], None))
            settle()
            without = vp.grab(r).toImage()
            item.setData(ROLE_PARTS, parts)
            pill_px[grade] = _diff(with_pill, without)
            # where the pill starts, from the row's left: the first column of
            # pixels the row loses without it
            pill_x[grade] = next((x for x in range(with_pill.width())
                                  if any(with_pill.pixelColor(x, y) != without.pixelColor(x, y)
                                         for y in range(with_pill.height()))), None)
        check(pill_px.get("hand", 0) > 40 and pill_px.get("label", 0) > 40,
              f"the list RENDERS a pill for each grade (pixels a row loses without it: {pill_px})")
        # ...in ONE column just past the widest name and meta, not 940 px from
        # the name at the row's right edge (the pill is the list's only tier
        # mark, and nothing carried the eye across an unstriped row)
        col = win.skills.delegate.column
        check(col is not None and all(x is not None for x in pill_x.values())
              and len(set(pill_x.values())) == 1 and max(pill_x.values()) < vp.width() // 2,
              f"the pills stand in one column near the name, not flush right ({col} px column; the "
              f"pills start at {pill_x}; half the {vp.width()} px row is {vp.width() // 2})")
        win.skills.modelled_only.setChecked(False)
        settle()
    else:
        skip("the grade marks", f"hand {len(hand_ids)} / label {len(label_ids)} rows listed; "
                                f"the vault overlay (skilldesc.py --emit-labels) puts label rows here")
    # the Skills tab: filter, lock, the party's professions
    win.skills.prof.setCurrentIndex(3)              # Monk
    settle()
    shown = [it for it in win.skills._items() if not it.isHidden()]
    check(shown and all(win.names.skill_profession(int(it.data(ROLE_ID))) == 3 for it in shown),
          f"filtering by Monk shows Monk skills only ({len(shown)})")
    win.skills.none_b.click()
    check(all(it.checkState() == Qt.Unchecked for it in shown), "lock all shown locks them")
    win.skills.filter.setText("no skill is called this")
    settle()
    vp = win.skills.list.viewport()
    with_ph = _count_near(vp.grab().toImage(), pal["muted"], 24, (0, 0, vp.width(), 90))
    keep_ph, win.skills.list.placeholder = win.skills.list.placeholder, ""
    vp.update()
    settle()
    without_ph = _count_near(vp.grab().toImage(), pal["muted"], 24, (0, 0, vp.width(), 90))
    win.skills.list.placeholder = keep_ph
    check(win.skills.list.visible_count() == 0 and with_ph > 30 and without_ph < 5,
          f"a filter that matches nothing RENDERS the placeholder, not a void "
          f"({with_ph} px with it, {without_ph} without)")
    win.skills.filter.setText("")
    win.skills.prof.setCurrentIndex(0)
    # one bulk write of the list -- this button's, a load's -- is ONE count and
    # ONE change signal however many boxes move (per item, each of ~985 flips
    # ran the O(n) count: 18 s for this click, and a failed Open blocked the
    # window 56 s doing it twice); the same click again moves nothing and
    # says nothing, and a load says it once whether or not anything moved
    emits, counts = [], []
    tally = lambda: emits.append(1)              # noqa: E731
    win.skills.changed.connect(tally)
    real_count = win.skills._count
    win.skills._count = lambda *a, **k: (counts.append(1), real_count(*a, **k))[1]
    n_all_on = len(win.skills.ids())
    win.skills.party_b.click()
    ids = set(win.skills.ids())
    moved, first = n_all_on - len(ids), (len(emits), len(counts))
    del emits[:], counts[:]
    win.skills.party_b.click()
    again = (len(emits), len(counts))
    del emits[:], counts[:]
    win.skills.set_ids(ids)
    load_said = (len(emits), len(counts))
    win.skills.changed.disconnect(tally)
    del win.skills._count
    check(ids and all(win.names.skill_profession(s) in {0, 1, 3} for s in ids)
          and any(win.names.skill_profession(s) == 3 for s in ids),
          "'Unlock party only' unlocks Warrior, Monk and common skills only")
    check(moved > 500 and first == (1, 1) and again == (0, 1) and load_said == (1, 1),
          f"one bulk write of the list is one count and one change signal ({moved} boxes "
          f"moved: {first} signals, counts; the same click again {again}; a load of the same "
          f"set {load_said})")
    # the words themselves, which the two checks above never read: the filter
    # box is named with both pills' words, the party button with its verb
    words = (win.skills.modelled_only.text(), win.skills.party_b.text(),
             win.skills.filter.toolTip())
    check(all(w in words[0].lower() and w in words[2] for w in orchui.GRADE_TEXT.values())
          and words[1].startswith("Unlock"),
          f"the filter box is named with the pills' own words, the text filter's hover says it "
          f"matches them, and the party button has its verb ({words[:2]})")
    # the filter keeps its placeholder whole down to the window's minimum width
    # (the row's one text input gave up width before an empty spacer did), and
    # the row keeps its two halves apart there: the checkbox sits with its
    # filters, twice as far from the bulk verbs as from the profession combo
    # -- the spacer had nothing to give until the filter reached its cap at
    # 1,250 px, and below that 'Modelled or label' stood 9 px from 'Unlock
    # shown' and 12 from its own filters, as one of the verbs
    size = win.size()
    fl, pf, cb, ub = win.skills.filter, win.skills.prof, win.skills.modelled_only, win.skills.all_b
    row = {}
    for w in (win.minimumSizeHint().width(), 1000, 1120):
        win.resize(w, 720)
        settle(8)
        # the clear button fades for ~140 ms after the text above was cleared,
        # and takes the placeholder's room while it does: wait for the search
        # icon to be the one button left
        t_end = time.perf_counter() + 1.0
        while sum(1 for b in fl.findChildren(QToolButton) if b.isVisibleTo(fl)) > 1 \
                and time.perf_counter() < t_end:
            settle(1)
            time.sleep(0.01)
        opt = QStyleOptionFrame()
        fl.initStyleOption(opt)
        room = (fl.style().subElementRect(QStyle.SE_LineEditContents, opt, fl).width()
                - sum(b.width() for b in fl.findChildren(QToolButton) if b.isVisibleTo(fl)) - 4)
        want = fl.fontMetrics().horizontalAdvance(fl.placeholderText())
        row[win.width()] = (room, want, cb.x() - (pf.x() + pf.width()), ub.x() - (cb.x() + cb.width()))
    check(len(row) == 3 and all(room >= want and apart >= 2 * near for room, want, near, apart in row.values()),
          f"down to the window's minimum width the Skills filter shows its whole placeholder and "
          f"its checkbox stands twice as far from the bulk verbs as from its filters (width: room, "
          f"placeholder, to the combo, to Unlock shown = {row})")
    win.resize(size)
    settle(8)

    # ---- the Party tab: a secondary, a second hero, the cap, and text that fits
    set_combo(win.party.secondary, 6)
    settle()
    check(6 in win.skills.party_professions, "the secondary reaches the Skills tab's party set")
    chk6, prof6, body6, _l = win.party.rows[6]
    check(not prof6.isEnabled() and not body6.isEnabled(),
          "a locked hero's editors are off (what reads as live is what the spec carries)")
    chk6.setChecked(True)
    set_combo(prof6, 1)
    body6.set_value("bandit_raider")
    check(prof6.isEnabled() and body6.isEnabled(), "and unlocking the hero turns them on")
    check(len(win.party.unlocked()) == 2 and win.to_spec()["heroes"][1]["profession"] == 1,
          "a second hero (index 6) unlocked as a Warrior in the raider's body")
    for idx in (1, 2, 4, 5, 7, 8):
        win.party.rows[idx][0].setChecked(True)
    check(len(win.party.unlocked()) == 7 and not win.party.rows[8][0].isChecked(),
          "the eighth hero is refused (the client's cap of 7)")
    check(win.party.count.property("kind") == "warn",
          "and the refusal is said, in the warning register")
    for idx in (1, 2, 4, 5, 7):
        win.party.rows[idx][0].setChecked(False)
    win.tabs.setCurrentWidget(win.party)
    size = win.size()
    cc = win.party.character
    for w, h, want in ((1280, 860, False), (1000, 720, True)):
        win.resize(w, h)
        settle(6)
        _c, prof3, body3, _lv = win.party.rows[3]
        profs = [prof3.itemText(i) for i in range(prof3.count())]
        clipped = [t for t in profs if not _fits(prof3, t)]
        # EVERY body, not the three common ones the first law sampled: the
        # 43 unnamed '(unwatched)' rows are the wide ones, and 17 were cut
        bodies = [body3.itemText(i) for i in range(body3.count())]
        bclipped = [t for t in bodies if not _fits(body3, t)]
        check(win.party.stacked is want and not clipped and len(bodies) > 3 and not bclipped,
              f"at {w} px the Character card is {'stacked above' if want else 'beside'} the "
              f"table, every profession fits its combo ({len(profs)}; clipped {clipped}) and "
              f"every body fits theirs ({len(bodies)}; clipped {bclipped[:2]})")
        rows = win.party.table.viewport().height() / win.party.table.rowHeight(0)
        if want:
            # stacked, the form is two rows of three: the card no taller than its
            # own height-for-width, and the table keeps most of the page
            check(cc.height() <= cc.heightForWidth(cc.width()) and rows >= 5.5,
                  f"stacked, the Character card is its own height ({cc.height()} of "
                  f"{cc.heightForWidth(cc.width())}) and the heroes table shows {rows:.1f} rows")
            # ...and a label after the first in its row reads as its own field's:
            # under half as far from that field as from the one before it (the
            # grid's one 14 px spacing had 'Secondary' 15 px from Primary's field
            # and 14 from its own, and 'Level' 15 from both)
            gaps = []
            for i, (lab, wdg) in enumerate(win.party.fields):
                if i % 3:
                    prev = win.party.fields[i - 1][1]
                    ink = lab.x() + lab.width() - lab.fontMetrics().horizontalAdvance(lab.text())
                    gaps.append((lab.text(), wdg.x() - (lab.x() + lab.width()),
                                 ink - (prev.x() + prev.width())))
            check(len(gaps) == 3 and all(own * 2 < before for _t, own, before in gaps),
                  f"stacked, each label after the first in its row is under half as far from its "
                  f"own field as from the field before it (own, before: {gaps})")
        else:
            check(cc.height() <= cc.sizeHint().height() < win.party.table.height(),
                  f"beside the table, the Character card hugs its form ({cc.height()} px; hint "
                  f"{cc.sizeHint().height()}, the table {win.party.table.height()})")
        # ...and every spin box on the tab holds its longest value, measured off
        # its line edit: the heroes' Level field was 10 px, and a level-20 hero
        # read '2' (the sheet reserved the buttons' width twice)
        spins = [s for s in win.findChildren(QAbstractSpinBox) if s.isVisibleTo(win)]
        narrow = [(s.accessibleName() or "spin", _spin_field(s).width(),
                   s.fontMetrics().horizontalAdvance(s.textFromValue(s.maximum())))
                  for s in spins
                  if _spin_field(s).width() - 4
                  < s.fontMetrics().horizontalAdvance(s.textFromValue(s.maximum()))]
        check(len(spins) == len(win.party.rows) + 1 and not narrow,
              f"at {w} px every spin box on the tab shows its longest value whole ({len(spins)} "
              f"spins for {len(win.party.rows)} heroes and the character; too narrow: "
              f"{narrow[:3] or 'none'})")
    # the stack edge is where the row stops fitting, read off the fitted
    # columns and the widest hero name: at that width, side by side, every
    # name is whole, and one pixel narrower the card stacks (a constant 1,120,
    # "1,114 measured" before the columns were fitted, elided 11 names side
    # by side from 1,120 to 1,129 -- the squeeze the stack exists to avoid)
    edge = win.party.STACK_BELOW
    got = {}
    for w in (edge, edge - 1):
        win.resize(w, 800)
        settle(8)
        tbl = win.party.table
        colw = tbl.columnWidth(2)
        vopt = QStyleOptionViewItem()
        vopt.rect = QRect(0, 0, 100, 40)
        inset = 100 - tbl.style().subElementRect(QStyle.SE_ItemViewItemText, vopt, tbl).width()
        elided = [it.text() for it in win.party.name_items.values()
                  if tbl.fontMetrics().horizontalAdvance(it.text()) > colw - inset]
        got[win.width()] = (win.party.stacked, colw, len(elided))
    check(got.get(edge, (True,))[0] is False and got[edge][2] == 0 and got.get(edge - 1, (False,))[0],
          f"at the stack edge ({edge} px) the card is beside the table and every hero name is "
          f"whole, and one pixel under it the card stacks (width: stacked, Hero column, elided = "
          f"{got})")
    # at the window's minimum height the squeeze lands on the scroll area, not
    # inside the form: three rows of form wanted 531 px of 424 and Qt evened
    # the cards out at 190 each, every label 3 px above its field
    win.resize(1000, 480)
    settle(8)
    off = [(lab.text(), lab.mapTo(win, QPoint(0, lab.height() // 2)).y()
            - wdg.mapTo(win, QPoint(0, wdg.height() // 2)).y()) for lab, wdg in win.party.fields]
    check(win.height() > 480 and win.party.stacked and all(abs(d) <= 1 for _t, d in off),
          f"at the window's minimum height ({win.height()}) every Character label is centred "
          f"on its field (off by {[d for _t, d in off]})")
    hdr = win.party.table.horizontalHeaderItem(1)
    check(hdr.textAlignment() & Qt.AlignRight,
          "the heroes table's '#' header is right-aligned over its right-aligned numbers")
    win.resize(size)
    settle(6)

    # ---- the Enemies tab (current, so the geometry laws below read a laid-out
    # detail pane and not a hidden tab's stale widths)
    en = win.enemies
    win.tabs.setCurrentWidget(en)
    settle()
    g = en.groups[0]
    g.add_member()
    g.add_member()
    check(len(g.members) == 4 and not en.add_member_b.isEnabled(),
          "a group fills to four and the add stops")
    n_items = sum(1 for _ in en._walk())
    check(n_items == 3 + 7, f"the encounter list holds 3 groups and 7 hostiles ({n_items} rows)")
    boss = en.groups[2].members[0]
    en.select(boss)
    settle()
    check(en.stack.currentWidget() is en._pages[boss], "selecting a hostile shows its editor")
    boss_rows = [it for it in en._walk() if it.data(0, Qt.UserRole) is boss]
    check(boss_rows and boss_rows[0].text(1).startswith("boss"), "the boss is marked in the list")
    check(en.groups[0].roster.count() == 4, "a group's page lists its hostiles, one line each")
    check(not strays() and all(hint_housed(m) for m in g.members),
          f"adding hostiles opens no window of its own ({len(strays())} stray)")
    # ...nor does a Ranks built by any caller: its chip is housed from birth (a
    # card re-homes it; shown with no parent, it was the hint's trap one over)
    lone = Ranks(win.names)
    lone.set_professions((1,), 5)
    settle()
    check(not strays() and lone.chip.parentWidget() is lone,
          f"a Ranks on its own houses its chip ({len(strays())} stray)")
    lone.deleteLater()
    # a real click on a roster row selects that hostile; back on the group's
    # page, the row is not left painted as a second selection
    en.select(g)
    settle()
    row1 = g.roster.item(1)
    QTest.mouseClick(g.roster.viewport(), Qt.LeftButton, Qt.NoModifier,
                     g.roster.visualItemRect(row1).center())
    settle()
    picked = en.current()
    en.select(g)
    settle()
    check(picked is row1.data(Qt.UserRole) and picked is g.members[1]
          and not g.roster.selectedItems(),
          "a click on a roster row selects that hostile, and leaves no row painted selected "
          "on the group's page")
    # the roster's facts start at ONE x on every row, past the widest name: as
    # one string per row, 'Bandit Raider — …' and 'Academy Monk — …' began
    # their facts 14 px apart. Measured off the rows: the first column a row
    # loses when its facts are taken away
    vp, starts, names = g.roster.viewport(), [], []
    for i in range(g.roster.count()):
        it = g.roster.item(i)
        r, parts = g.roster.visualItemRect(it), it.data(ROLE_ROSTER)
        with_facts = vp.grab(r).toImage()
        it.setData(ROLE_ROSTER, (parts[0], ""))
        settle(2)
        without = vp.grab(r).toImage()
        it.setData(ROLE_ROSTER, parts)
        starts.append(next((x for x in range(with_facts.width())
                            if any(with_facts.pixelColor(x, y) != without.pixelColor(x, y)
                                   for y in range(with_facts.height()))), None))
        names.append(g.roster.fontMetrics().horizontalAdvance(parts[0]))
    check(len(starts) == 4 and None not in starts and len(set(starts)) == 1
          and len(set(names)) > 1 and starts[0] > max(names),
          f"a group's roster starts every row's facts at one x, past its widest name (facts at "
          f"{starts}; names {names} px wide)")
    # level 0 is a value the spin offers and the compiler accepts: the roster
    # and the change signal survive it (the fix pass's summary() raised there,
    # emptying the roster and losing the signal)
    m1 = en.groups[1].members[0]
    emits = []
    en.changed.connect(lambda: emits.append(1))
    m1.level.setValue(0)
    settle()
    check(en.groups[1].roster.count() == len(en.groups[1].members) and emits
          and "level-0" in m1.ranks.hint.text() and " 0 points" in m1.ranks.hint.text(),
          f"a hostile at level 0 keeps its group's roster ({en.groups[1].roster.count()} of "
          f"{len(en.groups[1].members)} rows), emits the change ({len(emits)}) and its hint "
          f"says 0 points")
    m1.level.setValue(2)
    settle()
    pk = en.groups[0].members[0].bar.slots[0]
    check(pk.lineEdit().cursorPosition() == 0, "a skill slot shows the start of its label")
    check(isinstance(pk.view().itemDelegate(), orchui.SkillDelegate)
          and isinstance(pk.completer().popup().itemDelegate(), orchui.SkillDelegate),
          "and its drop-down and its type-to-filter popup draw rows the way the Skills list does")
    # the hostile page at three widths, for EVERY hostile in the example: every
    # choice in every slot, the Template and the Weapon (the '(none: the
    # template's swing)' row every new hostile starts with among them) fits its
    # field -- two columns of slots cut a skill id through its last digit at
    # 1,000 px, and 20 attribute names at 1,120; the Encounter card keeps its
    # 300 px, the page reflows. Every hostile, because the bar's two-column
    # threshold was a constant fitted to the first one's list (a Warrior's,
    # 335 px), and the second's -- a Monk's, 371 -- was cut mid-word at the
    # default 1,280 while this law, reading the first alone, stayed green
    m0 = en.groups[0].members[0]
    eds = [m for gg in en.groups for m in gg.members]
    edges = {}

    def cut_choices(ed):
        cut = []
        for tag, combo in ([(f"slot {i + 1}", pk) for i, pk in enumerate(ed.bar.slots)]
                           + [("Template", ed.template), ("Weapon", ed.weapon_item)]):
            for i in range(combo.count()):
                if not _fits(combo, combo.itemText(i)):
                    cut.append((ed.template.value(), tag, combo.itemText(i)[:40],
                                _field_width(combo)))
        return cut

    def label_edges(ed):
        """(label, its ink's last column, its field's first) per labelled form
        row, in window x: right-aligned, a label's ink ends a bearing short of
        its field less the form's 14 px spacing."""
        img = win.grab().toImage()
        out = []
        for f in ed.findChildren(QFormLayout):
            for r in range(f.rowCount()):
                li, fi = f.itemAt(r, QFormLayout.LabelRole), f.itemAt(r, QFormLayout.FieldRole)
                if li is None or li.widget() is None or fi is None:
                    continue
                lab = li.widget()
                at = lab.mapTo(win, QPoint(0, 0))
                _l, ink = _ink_span(img, QRect(at, lab.size()), pal["surface"])
                out.append((lab.text(), ink, f.parentWidget().mapTo(win, fi.geometry().topLeft()).x()))
        return out

    for w, h in ((1280, 860), (1120, 760), (1000, 720)):
        win.resize(w, h)
        settle(8)
        cut, cols = [], {}
        for ed in eds:
            en.select(ed)
            settle(4)
            cut += cut_choices(ed)
            cols[ed.template.value()] = ed.bar.columns
        check(not cut and all(ed.weapon_item.itemText(0).startswith("(none") for ed in eds),
              f"at {w} px every choice in each example hostile's eight slots, its Template and "
              f"its Weapon fits its field (the bars in {cols} column(s), the cards "
              f"{'stacked' if m0.stacked else 'side by side'}; cut: {cut[:2] or 'none'})")
        # stacked, the Body and Weapon cards' inputs start at one x, their
        # labels right-aligned up to it (each form sized its own label column:
        # 'Template' and 'Attack interval' put the two cards' inputs 32 px
        # apart in one column); side by side each form keeps its own column
        en.select(m0)
        settle(4)
        edges[w] = (m0.template.mapTo(win, QPoint(0, 0)).x(), m0.template.width(),
                    m0.weapon_item.mapTo(win, QPoint(0, 0)).x())
        if m0.stacked:
            labs = label_edges(m0)
            check(edges[w][0] == edges[w][2] and len(labs) >= 7
                  and all(ink is not None and 0 <= fx - 14 - ink <= 3 for _t, ink, fx in labs),
                  f"at {w} px the stacked Body and Weapon cards start their inputs at one x "
                  f"({edges[w][0]} and {edges[w][2]}), every label's ink ending at its field less "
                  f"the form's spacing ({[(t, fx - 14 - (ink or 0)) for t, ink, fx in labs]})")
            # a sheet change while stacked (the labels re-polished) must not
            # leave the shared width behind when the cards go side by side
            for lab in m0._labels:
                lab.style().unpolish(lab)
                lab.style().polish(lab)
            settle(4)
    win.resize(1280, 860)
    settle(8)
    back = (m0.template.mapTo(win, QPoint(0, 0)).x(), m0.template.width(),
            m0.weapon_item.mapTo(win, QPoint(0, 0)).x())
    check(m0.stacked is False and back == edges[1280] and back[0] != back[2],
          f"back at 1,280 px after a re-polish while stacked, the Template field is where and as "
          f"wide as it was, the Weapon's in its own card (x, width, weapon x: {back} was "
          f"{edges[1280]})")
    # ...and one body per profession the Template picker offers, at the default
    # width: the bar picks its columns from the list a template gives it, at a
    # constant width -- Warrior 2, Monk 1, Warrior 2 (a threshold read only on
    # resize would hold the Warrior's columns for the Monk's list)
    m0_spec = m0.to_spec()
    rows = win.names.world.rows("npc")
    byprof = {}
    for i in range(m0.template.count()):
        k = m0.template.itemData(i)
        byprof.setdefault(int((rows.get(k) or {}).get("profession", 0) or 0), k)
    cut, cols = [], {}
    for p, k in sorted(byprof.items()):
        m0.template.set_value(k)
        settle(4)
        cols[p] = m0.bar.columns
        cut += cut_choices(m0)
    swing = []
    for k in ("bandit_raider", "academy_monk", "bandit_raider"):
        m0.template.set_value(k)
        settle(4)
        swing.append(m0.bar.columns)
    m0.from_spec(m0_spec)
    settle(4)
    check(len(byprof) >= 6 and not cut and swing == [2, 1, 2] and m0.to_spec() == m0_spec,
          f"at 1,280 px a hostile in any of {len(byprof)} professions' bodies fits every slot "
          f"choice, the bar re-picking its columns from each list at one width (by profession "
          f"{cols}; Warrior, Monk, Warrior: {swing}; cut: {cut[:2] or 'none'})")
    # a group page and a hostile page share one right edge whether or not the
    # hostile's page scrolls: at 860 tall it does, at 1080 (a maximized 1080p
    # window) it does not, and a fixed reserve matched only the first
    edges = {}
    for h in (860, 1080):
        win.resize(1280, h)
        settle(8)
        got = []
        for ed in (g, m0):
            en.select(ed)
            settle(4)
            got.append(ed.remove_b.mapTo(win, QPoint(ed.remove_b.width(), 0)).x())
        edges[h] = (got[0], got[1], en._pages[m0].verticalScrollBar().maximum() > 0)
    check(all(v[0] == v[1] for v in edges.values()) and edges[860][2] and not edges[1080][2],
          f"a group page's Remove and a hostile page's end at one x, the hostile page scrolling "
          f"and not (group, hostile, scrolls: {edges})")
    win.resize(size)
    settle(8)
    # one verb each on the tab: the adds on the list, ONE labelled Remove on the
    # page of the thing it removes (an icon-only x beside + Hostile removed
    # whatever was selected, and the selection after a removal was a group)
    verbs = {}
    for tag, ed in (("hostile", m0), ("group", g)):
        en.select(ed)
        settle()
        shown = [b for b in en.findChildren(QPushButton) if b.isVisibleTo(en)]
        verbs[tag] = (sorted(b.accessibleName() for b in shown if b.accessibleName().startswith("Remove")),
                      sorted(b.accessibleName() for b in shown if b.accessibleName().startswith("Add")),
                      [b for b in shown if not b.text()])
    check(all(len(v[0]) == 1 and v[1] == ["Add a group", "Add a hostile"] and not v[2]
              for v in verbs.values())
          and verbs["hostile"][0] == ["Remove hostile"] and verbs["group"][0] == ["Remove group"],
          f"on a hostile's page and on a group's, the tab shows one labelled Remove and the two "
          f"adds, no icon-only verb ({ {k: (v[0], v[1], len(v[2])) for k, v in verbs.items()} })")
    # the wheel: never edits an unfocused combo, and still scrolls the page
    win.tabs.setCurrentWidget(en)
    en.select(en.groups[0].members[0])
    settle()
    before = pk.currentIndex()
    ev = QWheelEvent(QPointF(10, 10), QPointF(pk.mapToGlobal(QPoint(10, 10))), QPoint(0, 0),
                     QPoint(0, -120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(pk, ev)
    settle()
    check(pk.currentIndex() == before, "the wheel over an unfocused combo does not change it")
    page = en._pages[en.groups[0].members[0]]
    bar = page.verticalScrollBar()
    control = en.groups[0].members[0].subtitle
    if bar.maximum() > 0 and sys.platform == "win32":
        bar.setValue(0)
        settle()
        _real_wheel(win, control)
        settle(5)
        moved_control = bar.value()
        if moved_control <= 0:
            skip("a real wheel over a combo scrolls the page",
                 "the OS wheel did not reach the window (control over a caption: 0 px)")
        else:
            bar.setValue(0)
            pk.clearFocus()
            settle()
            _real_wheel(win, pk)
            settle(5)
            check(bar.value() > 0 and pk.currentIndex() == before,
                  f"a real wheel over an unfocused combo scrolls the page ({bar.value()} px; the "
                  f"control over a caption scrolled {moved_control}) and leaves the combo alone "
                  f"-- the window inactive; the active window's law is below")
            bar.setValue(0)
    else:
        skip("a real wheel over a combo scrolls the page",
             "the page does not scroll at this size, or this is not Windows")
    # the boss note is read off the members, not the position
    g4 = en.add_group()
    settle()
    g3 = en.groups[2]
    check(g4 is not None and "holds the boss" not in g4.subtitle.text()
          and not g3.note.isHidden(),
          "a group added after the boss's group is not labelled as holding it, and the boss's "
          "group warns that it must be last")
    # the page's Remove group ASKS while the group holds a hostile, and a No
    # removes nothing; a Yes removes it and lands the selection on the
    # neighbour GROUP's page, whose Remove (at the same pixel) asks in turn
    en.select(g4)
    settle()
    asked = []
    en.ask_remove = lambda ed: (asked.append(("no", ed)), False)[1]
    g4.remove_b.click()
    settle()
    kept = g4 in en.groups and en.current() is g4
    en.ask_remove = lambda ed: (asked.append(("yes", ed)), True)[1]
    g4.remove_b.click()
    settle()
    del en.ask_remove
    check(asked == [("no", g4), ("yes", g4)] and kept and g4 not in en.groups
          and en.current() is g3,
          f"Remove group asks first, a No keeps the group, a Yes removes it and selects the "
          f"neighbour group (asked {[a for a, _ in asked]}, now {type(en.current()).__name__})")
    check("holds the boss" in g3.subtitle.text() and g3.note.isHidden(),
          "and removing it puts the note back")
    box_text = en.remove_box(g3).text()
    check(f"group {g3.index}" in box_text and f"{n_of(len(g3.members), 'hostile')} with it" in box_text,
          f"the box names the group and how many hostiles go with it ({box_text.splitlines()[0]!r})")
    # a click repeated at ONE window pixel -- a double-click, a hand that stays
    # -- takes at most one hostile and then meets a question: every removal
    # lands on a GROUP page, whose Remove asks while the group holds one.
    # (Landing on the next hostile put its unasking 'Remove hostile' under the
    # pixel: eight clicks emptied the encounter, and nothing asked.) Clicks go
    # through the window, to whatever is under the pointer, as a hand's do
    saved = en.to_spec()
    series = {}
    for tag, pick in (("group 1's first hostile", lambda: en.groups[0].members[0]),
                      ("the last group's sole hostile", lambda: en.groups[-1].members[-1])):
        ed = pick()
        en.select(ed)
        settle(4)
        n0 = (sum(len(gg.members) for gg in en.groups), len(en.groups))
        asked = []
        en.ask_remove = lambda e: (asked.append(e.index), False)[1]
        b = ed.remove_b
        at = b.mapTo(win, QPoint(b.width() // 2, b.height() // 2))
        for _ in range(6):
            before = (sum(len(gg.members) for gg in en.groups), len(en.groups))
            QTest.mouseClick(win.windowHandle(), Qt.LeftButton, Qt.NoModifier, at)
            settle(4)
            if (sum(len(gg.members) for gg in en.groups), len(en.groups)) == before:
                break
        del en.ask_remove
        n1 = (sum(len(gg.members) for gg in en.groups), len(en.groups))
        series[tag] = (n0[0] - n1[0], n0[1] - n1[1], len(asked), type(en.current()).__name__)
    check(len(series) == 2 and all(hostiles <= 1 and asks >= 1 and now == "GroupEditor"
                                   for hostiles, _groups, asks, now in series.values()),
          f"a click repeated at one pixel from a hostile's Remove takes at most that hostile and "
          f"then meets a question (hostiles gone, groups gone, asks, the page now: {series})")
    en.from_spec(saved)
    settle()
    g3 = en.groups[2]
    seen_roles |= used_roles(win)

    # ---- compile
    win.tabs.setCurrentWidget(win.skills)
    win.statusBar().clearMessage()
    win.header.compile_b.click()
    settle()
    compiled = win.run.compiled
    check(compiled is not None, "the changed spec COMPILES (pressed from the header)")
    check(win.tabs.currentWidget() is win.skills and bool(win.statusBar().currentMessage()),
          f"a compile pressed on another tab is answered in the status bar and keeps the tab "
          f"({win.statusBar().currentMessage()!r})")
    if compiled:
        args = " ".join(compiled["args"])
        check("--spawn-secondary 6" in args and "--persist" in args,
              "the secondary and --persist reach the flags")
        check(len(compiled["party_row"]["heroes"]) == 2 and
              compiled["party_row"]["heroes"][1]["points"] == 10 and
              compiled["party_row"]["heroes"][1]["skills"] == [],
              "two hero rows, each with an empty bar and the level's points budget")
        check(compiled["party_row"]["player_skills"] == [] and
              compiled["party_row"]["player_attributes"] == [],
              "the character's bar and ranks are written EMPTY for the panels")
        check(len(compiled["spawn_rows"]) == 7, f"seven hostiles ({len(compiled['spawn_rows'])})")
        text = win.run.summary.toPlainText()
        check(all(tok in text for tok in compiled["args"]) and compiled["overlay"].strip() in text,
              "the compiled pane drops nothing: every gamesrv argument and the whole overlay")
    # the Run tab in its COMPILED state, which no scan saw before (a compile
    # keeps the tab it was pressed on): the status line names no path, the bar
    # points at the tab only from elsewhere and counts in words, and the pane
    # wraps -- unwrapped, two lines are 45,000 px wide and the horizontal bar
    # they size is useless for the rest
    rt = win.run
    away = win.statusBar().currentMessage()      # pressed from Skills, above
    win.tabs.setCurrentWidget(rt)
    settle()
    lore += surface_lore(win)
    rt.compile()                                 # pressed here
    here = win.statusBar().currentMessage()
    check(not SURFACE_LORE.search(rt.status.text()) and "overlay goes to" in rt.status.toolTip(),
          f"the compiled status line names no path; the overlay's is on hover "
          f"({rt.status.text()!r})")
    check("Run tab" in away and "Run tab" not in here and "(s)" not in away + here + rt.status.text(),
          f"the bar points at the Run tab only from another tab, and counts in words ({here!r})")
    rt.summary.moveCursor(QTextCursor.End)       # lays the widest lines out
    settle()
    hmax = rt.summary.horizontalScrollBar().maximum()
    rt.summary.moveCursor(QTextCursor.Start)
    check(hmax == 0, f"the Compiled pane wraps: nothing to scroll sideways ({hmax} px)")
    # the live status says nothing a Run-tab caption already says: the closing
    # fact is the Launch options caption's, on screen throughout

    def shingles(text, n=4):
        words = re.findall(r"[a-z']+", text.lower())
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}

    caps = [w.text() for w in rt.findChildren(QLabel)
            if w.property("role") == "caption" and w.isVisibleTo(rt)]
    shared = sorted(s for c in caps for s in shingles(c) & shingles(LAUNCH_STATUS))
    check(caps and not shared,
          f"the live status repeats no Run-tab caption ({len(caps)} captions; a run of four "
          f"words shared: {shared[:2] or 'none'})")
    # ...read at the constant, so the say site is locked to it: _start says
    # LAUNCH_STATUS and nothing appended (a launch is not driven here)
    check("self.status.setText(LAUNCH_STATUS)" in inspect.getsource(RunTab._start),
          "and the launch's say site puts that constant on the line, whole")
    t_end = time.perf_counter() + 2.0            # the summary is debounced: let it land
    while win._summary_timer.isActive() and time.perf_counter() < t_end:
        settle(1)
        time.sleep(0.01)
    check("2 heroes" in win.header.summary.text() and "7 hostiles" in win.header.summary.text(),
          f"the header's summary follows the spec ({win.header.summary.text()!r})")
    path = win.run.save(os.path.join(out_dir, "smoke_spec.toml"))
    lore += surface_lore(win)                    # 'Saved …': the name, not the path
    check(path and os.path.isfile(path), "the spec saves")
    if path:
        back = sandbox.load_spec(path)
        check(back["player"]["secondary"] == 6 and len(back["heroes"]) == 2
              and len(back["unlocks"]) == len(ids), "and loads back with its unlocks")
    was = win.run.state.text()
    win.header.name.setText("smoke-stale")
    check(was == "Compiled" and win.run.state.text() == "Changed since compile"
          and win.run.state.property("kind") == "warn",
          "an edit after a compile turns the green chip into 'Changed since compile'")
    # ...and so does EVERY input compile_spec reads, not only the ones the tree
    # shows (the review found eleven that left it green), each from a fresh
    # compile; a hostile's edit also reaches its group's roster line at once
    m0, g0 = en.groups[0].members[0], en.groups[0]
    boss = en.groups[2].members[0]

    def turn(combo, skip_first=False):
        n = combo.count() - (1 if skip_first else 0)
        combo.setCurrentIndex((combo.currentIndex() - (1 if skip_first else 0) + 1) % n
                              + (1 if skip_first else 0))

    edits = [("party weapon", lambda: turn(win.party.weapon)),
             ("party off-hand", lambda: turn(win.party.offhand, skip_first=True)),
             ("a hero's body", lambda: win.party.rows[3][2].set_value("hatcher")),
             ("health", lambda: m0.health.setValue(m0.health.value() + 1)),
             ("weapon item", lambda: turn(m0.weapon_item)),
             ("attack interval", lambda: m0.speed.setValue(1.25)),
             ("damage high", lambda: m0.dhi.setValue(40)),
             ("damage low", lambda: m0.dlo.setValue(7)),
             ("skill slot 8", lambda: m0.bar.slots[7].setCurrentIndex(1)),
             ("the boss's glow", lambda: boss.glow.setValue(boss.glow.value() + 1)),
             ("hold", lambda: win.run.hold.setValue(30)),
             ("template", lambda: m0.template.set_value("academy_monk"))]
    if m0.ranks.spins:
        # a rank, and a rank on the spins a template change REBUILDS -- down
        # where it can: this hostile stands at its budget, and one more point
        # is a spec the compiler refuses, which the next three edits would
        # then read as 'not fresh'
        def rank():
            sp = next(iter(m0.ranks.spins.values()))
            sp.setValue(sp.value() - 1 if sp.value() else 1)
        edits.insert(9, ("attribute rank", rank))
        edits.append(("attribute rank after the template change", rank))
    stayed, stale_rows = [], []
    for label, edit in edits:
        win.run.compile()
        fresh = win.run.state.text().startswith("Compiled")
        edit()
        settle()
        if not (fresh and win.run.state.text() == "Changed since compile"):
            stayed.append(label)
        if label not in ("party weapon", "party off-hand", "a hero's body", "hold") \
                and not g0.roster.item(0).text().endswith(m0.summary()):
            stale_rows.append(label)
    check(not stayed, f"each of {len(edits)} spec inputs turns a fresh 'Compiled' into 'Changed "
                      f"since compile' (left green: {stayed or 'none'})")
    check(not stale_rows, f"and a hostile's edit reaches its roster line at once "
                          f"(stale after: {stale_rows or 'none'})")
    win.run.hold.setValue(0)
    # a view of the same spec is not an edit: the Skills filters leave the chip
    # green, while an unlock still turns it
    win.tabs.setCurrentWidget(win.skills)
    turned = []
    for label, act in (("filter text", lambda: win.skills.filter.setText("heal")),
                       ("profession filter", lambda: win.skills.prof.setCurrentIndex(1)),
                       ("'modelled or label'", lambda: win.skills.modelled_only.setChecked(True))):
        win.run.compile()
        before = win.to_spec()
        act()
        settle()
        if not win.run.state.text().startswith("Compiled") or win.to_spec() != before:
            turned.append(label)
    win.skills.filter.setText("")
    win.skills.prof.setCurrentIndex(0)
    win.skills.modelled_only.setChecked(False)
    settle()
    win.run.compile()
    first = next(it for it in win.skills._items() if not it.isHidden())
    first.setCheckState(Qt.Unchecked if first.checkState() == Qt.Checked else Qt.Checked)
    settle()
    unlock_turned = win.run.state.text() == "Changed since compile"
    first.setCheckState(Qt.Unchecked if first.checkState() == Qt.Checked else Qt.Checked)
    settle()
    check(not turned and unlock_turned,
          f"the Skills filters leave a fresh 'Compiled' green (turned it: {turned or 'none'}), "
          f"and one unlock turns it")
    # the low damage bound with the high at 0 is not in the spec either: typed
    # first, the natural order, it painted a false amber
    m0.dhi.setValue(0)
    win.run.compile()
    before = win.to_spec()
    m0.dlo.setValue(m0.dlo.value() + 3)
    settle()
    check(win.to_spec() == before and win.run.state.text() == "Compiled",
          f"a low damage bound typed with the high at 0 changes no spec and leaves the chip "
          f"green ({win.run.state.text()!r})")
    win.header.name.setText("smoke-bad")
    win.enemies.groups[0].members[0].boss.setChecked(True)
    win.tabs.setCurrentWidget(win.enemies)
    settle()
    g3 = en.groups[2]
    check(not g0.note.isHidden() and not g3.note.isHidden()
          and g0.note.text() == g3.note.text() == "Only one hostile can be the boss",
          "a second boss is said on both groups' pages before any compile")
    win.header.compile_b.click()
    settle()
    check(win.run.compiled is None and "bosses" in win.run.summary.toPlainText(),
          "two bosses are REFUSED at compile, and the reason is shown")
    check(win.run.state.property("kind") == "crit" and win.tabs.currentWidget() is win.run,
          "and a refusal opens the Run tab, its chip saying Refused")
    msg = win.statusBar().currentMessage()
    check(re.fullmatch(r"Refused: \d+ reasons?\.", msg) is not None,
          f"the refusal's count is words, and it does not point at the tab it just opened "
          f"({msg!r})")
    win.enemies.groups[0].members[0].boss.setChecked(False)
    settle()
    check(g0.note.isHidden() and g3.note.isHidden(), "and unticking it clears both notes")
    # ranks past a hostile's budget are REFUSED at compile, as its Attributes
    # hint promises (validate checked the player's and the heroes' ranks and
    # never a member's, so the crit chip was the only sign)
    if m0.ranks.spins:
        sp = next(iter(m0.ranks.spins.values()))
        keep = sp.value()
        sp.setValue(sp.maximum())
        win.run.compile()
        chip_said = (m0.ranks.chip.text(), m0.ranks.chip.property("kind"), win.run.state.text())
        refused = (win.run.compiled is None and chip_said[2] == "Refused"
                   and "points; level" in win.run.summary.toPlainText())
        sp.setValue(keep)
        check(chip_said[1] == "crit" and "over budget" in chip_said[0] and refused,
              f"a hostile's ranks past its level's budget are refused at compile, as the hint "
              f"promises ({chip_said[0]!r}; {chip_said[2]!r})")
    else:
        skip("an over-budget hostile is refused at compile", "no attribute table, so no ranks")
    seen_roles |= used_roles(win)
    lore += surface_lore(win)
    # a malformed spec must not latch the Enemies tab dead
    saved = en.to_spec()
    raised = False
    try:
        en.from_spec([{"members": [{"npc": "bandit_raider", "damage": [6]}]}])
    except Exception:                                   # noqa: BLE001
        raised = True
    live = len(en.groups) + sum(len(x.members) for x in en.groups)
    rows = sum(1 for _ in en._walk())
    check(raised and not en._building and rows == live,
          f"a malformed hostile row raises, and the list still shows what loaded "
          f"({rows} rows for {live} editors)")
    # a saved level-0 hostile opens (its budget hint used to raise on the way in)
    try:
        en.from_spec([{"members": [{"npc": "bandit_raider", "level": 0}]}])
        opened = True
    except Exception:                                   # noqa: BLE001
        opened = False
    settle()
    check(opened and len(en.groups) == 1 and len(en.groups[0].members) == 1
          and en.groups[0].roster.count() == 1 and en.groups[0].members[0].level.value() == 0,
          f"a spec with a level-0 hostile opens ({opened}), and its group lists it")
    en.from_spec(saved)
    settle()
    # a file that fails INSIDE from_spec (well-formed TOML, a malformed row)
    # leaves the spec as it was -- a '(none)' off-hand included, which the
    # restore read as a missing key and handed back the profession's shield --
    # and the words with it: the message says nothing opened, so nothing may
    # have; Save must not default to the file that failed; the chip may not
    # read 'Changed since compile' beside a bar that says unchanged; the
    # operator's place in the encounter, and a hero row the failed file wrote
    # before its bad row, are put back
    win.party.offhand.set_value("")
    en.select(en.groups[1].members[0])
    rt.compile()
    settle()
    at, was_green, lvl5 = en.place(), rt.state.text() == "Compiled", win.party.rows[5][3].value()
    before = win.to_spec()
    broken = os.path.join(out_dir, "smoke_broken.toml")
    with open(broken, "w", encoding="utf-8") as fh:
        fh.write('name = "smoke-broken"\n\n[player]\nprofession = 1\nlevel = 7\n\n'
                 '[[heroes]]\nhero = 5\nbody = "hatcher"\nlevel = 9\n\n[[groups]]\n\n'
                 '[[groups.members]]\nnpc = "bandit_raider"\ndamage = [6]\n')
    win.run.load(broken)
    settle()
    msg = win.statusBar().currentMessage()
    lore += surface_lore(win)                    # 'Could not open …': the name, not the file
    check(was_green and before["player"]["offhand"] == "" and win.to_spec() == before
          and msg.startswith("Could not open") and "unchanged" in msg,
          f"a spec file whose row fails to load leaves the spec unchanged, a '(none)' off-hand "
          f"included, and says so ({msg!r})")
    check(rt.state.text() == "Compiled" and not rt._stale and at == (1, 0) == en.place()
          and win.party.rows[5][3].value() == lvl5 and not win.party.rows[5][0].isChecked(),
          f"and keeps the chip green, the selection and the hero row the file wrote "
          f"({rt.state.text()!r}, {en.place()} of {at}, hero 5 at level "
          f"{win.party.rows[5][3].value()} of {lvl5})")
    check(not strays(), f"and after every load, still one window ({len(strays())} stray)")
    # a spec saved with no off-hand comes back with none (the file says
    # offhand = ""; a MISSING key is the profession's default, to the compiler
    # and the window alike), and Save and Open say the file's name, not its path
    good = win.run.save(os.path.join(out_dir, "smoke_none.toml"))
    saved_said = win.statusBar().currentMessage()
    win.run.load(good)
    settle()
    msg = win.statusBar().currentMessage()
    lore += surface_lore(win)                    # 'Opened …'
    check(sandbox.load_spec(good)["player"].get("offhand") == "" and win.to_spec() == before
          and msg == "Opened smoke_none" and saved_said == "Saved smoke_none",
          f"a spec saved with no off-hand opens with none, and the bar says the name only "
          f"({saved_said!r}, {msg!r})")
    # a file the compiler would refuse -- a fifth group, a fifth hostile, a
    # template the content lacks, the boss not last -- opens as one it accepts:
    # what the window cannot hold is dropped or replaced on the way in, with
    # no raise, and the bar said 'Opened' and nothing else, so a Save
    # (defaulting to that file) wrote the trimmed encounter over the original
    plain = {k: v for k, v in before["groups"][1]["members"][0].items()
             if k not in ("boss", "glow")}
    over = dict(before, name="smoke-toomany",
                groups=[{"members": [dict(plain) for _ in range(5)]}, {"members": [dict(plain)]},
                        {"members": [dict(plain)]},
                        {"members": [dict(before["groups"][2]["members"][0])]},
                        {"members": [dict(plain)]}])
    over["groups"][0]["members"][1]["npc"] = "no_such_template"
    many = os.path.join(out_dir, "smoke_toomany.toml")
    with open(many, "w", encoding="utf-8") as fh:
        fh.write(sandbox.spec_toml(over))
    lost = sandbox.validate(over, win.world)
    win.run.load(many)
    settle()
    msg = win.statusBar().currentMessage()
    lore += surface_lore(win)                    # 'Opened …, but …'
    held = win.to_spec()
    shape = [len(g["members"]) for g in held["groups"]]
    check(len(lost) >= 4 and shape == [4, 1, 1, 1] and not sandbox.validate(held, win.world)
          and msg.startswith("Opened smoke_toomany, but the window could not hold")
          and f"{n_of(len(lost), 'change')}: {lost[0]}" in msg,
          f"a file the compiler refuses ({len(lost)} reasons) opens as one it accepts, and the "
          f"bar says what the window could not hold ({shape}; {msg[:96]!r})")
    win.from_spec(before)
    settle()
    # how a run ended is read from what the harness PRINTS -- print sites, read
    # off the syntax tree, not the source text: the same files quote the old
    # lines in comments, and a commented-out print fooled a regex. The crash
    # line's prefix is read the same way: the chip's hover is empty without it
    strs = []
    for name in ("session.py", "runwatch.py"):
        strs += printed_strings(os.path.join(ROOT, "toolkit", "harness", name))
    printed = {key: any(needle in s for s in strs)
               for key, needle in dict(RUN_MARKS, assert_line=ASSERT_PREFIX).items()}
    check(all(printed.values()),
          f"every line the end-of-run chip reads, and the crash line's prefix, is one the "
          f"harness still PRINTS ({printed})")
    table = ((set(), 0, "good"), ({"retracted"}, 1, "good"), ({"crash", "retracted"}, 1, "crit"),
             ({"crash"}, 0, "crit"), ({"fail"}, 1, "warn"), ({"stopped"}, 1, "info"),
             ({"no start"}, -1, "crit"), (set(), 1, "warn"))
    got = []
    for marks, code, want in table:
        rt._marks = set(marks)
        got.append(rt.end_state(code)[1] == want)
    rt._marks = set()
    check(all(got), "a closed client ends 'client closed' (not amber), a crash crit -- on exit "
                    f"0 too (a timed hold's) -- a failed run warn, Stop 'Stopped', no start crit "
                    f"({got})")
    # a run's verdict outlives the first edit after it, and an edit DURING the
    # run is said when it ends. A stand-in for proc: nothing is launched, and
    # _done never touches it
    win.tabs.setCurrentWidget(rt)
    rt.compile()
    rt.proc = object()
    for ln in ("  ERROR DIALOG captured -> smoke", "  >>> Assertion: smoke <= 1.0f",
               "RUN VERDICT: PASS  (target: map)"):
        rt._mark(ln)
    rt._done(0, None)
    ended, kind, tip = rt.state.text(), rt.state.property("kind"), rt.state.toolTip()
    win.header.name.setText("smoke-after-run")
    settle()
    check(ended == "Ended  ·  the client crashed" and kind == "crit" and rt.state.text() == ended
          and rt.state.property("kind") == "crit" and "vault/captures/harness" in rt.status.text()
          and "changed since" in rt.status.text() and rt.launch_b.isEnabled(),
          f"a crash captured on an exit-0 run reads crit, and the first edit after it keeps the "
          f"verdict and says the spec changed ({rt.state.text()!r})")
    check(tip == "Assertion: smoke <= 1.0f", f"the chip's hover is the dialog's own line ({tip!r})")
    rt.compile()
    rt._marks, rt._assert = set(), None
    rt.proc = object()
    win.header.name.setText("smoke-during-run")
    settle()
    unpainted = rt.state.text() == "Compiled" and rt._stale
    rt._done(0, None)
    check(unpainted and rt.state.text() == "Ended  ·  exit 0" and rt.state.toolTip() == ""
          and "changed since" in rt.status.text(),
          "an edit during a run is not painted over the clock, and is said when the run ends")
    # a harness that cannot start, through the real start path with a program
    # that does not exist (Windows emits FailedToStart inside start() itself,
    # so the cleanup has to be the last thing launch does)
    rt._start([os.path.join(out_dir, "no_such_harness.exe"), "--smoke"], {})
    t_end = time.perf_counter() + 3.0
    while rt.proc is not None and time.perf_counter() < t_end:
        settle(1)
        time.sleep(0.01)
    settle(5)
    log = rt.log.toPlainText()
    check(rt.proc is None and not rt.ticker.isActive() and rt.launch_b.isEnabled()
          and rt.launch_b.text() == "Launch" and rt.compile_b.isEnabled()
          and not rt.stop_b.isEnabled() and rt.state.text() == "Did not start"
          and rt.state.property("kind") == "crit" and "did not start" in rt.status.text()
          and "did not start" in log and "exited with code" not in log,
          f"a harness that cannot start leaves Launch enabled, the clock stopped, the chip "
          f"'Did not start' and no 'exited' line ({rt.state.text()!r}, Launch "
          f"{rt.launch_b.isEnabled()}, ticker {rt.ticker.isActive()})")
    # the no-archive dialog's face: one sentence and the command; the citation
    # and the compiler's words behind Show Details (a modal is no child the
    # lore scan can see, so its text is read here, unshown)
    try:
        sandbox.run_paths(os.path.join(out_dir, "no_vault"))
        exc = None
    except sandbox.SpecError as e:
        exc = e
    box = rt.no_archive_box(exc)
    face = [ln for ln in box.text().splitlines() if SURFACE_LORE.search(ln)]
    check(exc is not None and face == ["python toolkit/mapdata/compose.py --name slice --build"]
          and "RUNBOOK" not in box.text() and str(exc) in box.detailedText(),
          f"the no-archive dialog's face is a sentence and the command; the citation and the "
          f"compiler's words are behind Show Details ({face})")
    box.deleteLater()
    # ...and launch shows THAT box (the seam a law reads is not the call site:
    # a QMessageBox.warning with the old face would pass the law above)
    check("self.no_archive_box(exc).exec()" in inspect.getsource(RunTab.launch),
          "and Launch shows that dialog, not one of its own")
    # after a refusal, an edit says the pane holds REASONS; after a no-archive
    # compile, it keeps the build hint on hover
    win.enemies.groups[0].members[0].boss.setChecked(True)
    rt.compile()
    win.header.name.setText("smoke-stale-refused")
    settle()
    refused_words = rt.status.text()
    win.enemies.groups[0].members[0].boss.setChecked(False)
    real = sandbox.run_paths
    sandbox.run_paths = lambda *a, **k: real(os.path.join(out_dir, "no_vault"))   # raises
    try:
        rt.compile()
    finally:
        sandbox.run_paths = real
    win.header.name.setText("smoke-stale-noarchive")
    settle()
    check("reasons below" in refused_words and rt.state.text() == "Changed since compile"
          and "no slice archive" in rt.status.text() and "compose.py" in rt.status.toolTip(),
          f"the stale line says what the pane holds -- reasons after a refusal -- and keeps the "
          f"build hint on hover ({rt.status.text()[:40]!r})")
    # the log follows only from the bottom, and keeps a selection
    view = QPlainTextEdit()
    view.resize(400, 200)
    write_lines(view, [(f"line {i}", "body") for i in range(300)])
    cur = view.textCursor()
    cur.select(QTextCursor.Document)
    view.setTextCursor(cur)                      # (this scrolls to the cursor itself)
    view.verticalScrollBar().setValue(0)
    write_lines(view, [("one more", "body")])
    stayed = view.verticalScrollBar().value() == 0 and view.textCursor().hasSelection()
    view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())
    write_lines(view, [("and another", "body")])
    followed = view.verticalScrollBar().value() == view.verticalScrollBar().maximum()
    check(stayed and followed, "the log keeps the operator's place and selection, and follows "
                               "new output only from the bottom")
    view.deleteLater()
    # ...and at the block cap, the line under a scrolled-back reader stays there
    # (rendered: firstVisibleBlock needs a laid-out view)
    view = QPlainTextEdit()
    view.setAttribute(Qt.WA_DontShowOnScreen, True)
    view.resize(400, 200)
    view.setMaximumBlockCount(100)
    view.show()
    write_lines(view, [(f"row {i}", "body") for i in range(100)])
    view.verticalScrollBar().setValue(40)
    settle()
    top = view.firstVisibleBlock().text()
    write_lines(view, [(f"row {i}", "body") for i in range(100, 110)])
    settle()
    check(top == "row 40" and view.firstVisibleBlock().text() == top and view.blockCount() == 100,
          f"at the block cap the scrolled-back reader's line stays under them ({top!r} -> "
          f"{view.firstVisibleBlock().text()!r}, {view.blockCount()} blocks)")
    view.deleteLater()
    # ...and when lines WRAP: every third row too long for the view, the reader
    # on row 40 (the bar in visual lines, so the row's first line), ten rows in
    # -- the value read after the edit is Qt's from the kept block number, and
    # the trimmed rows' lines came off it twice (row 40 -> row 42)
    view = QPlainTextEdit()
    view.setAttribute(Qt.WA_DontShowOnScreen, True)
    view.resize(400, 200)
    view.setMaximumBlockCount(100)
    view.show()
    wrapped = [(f"row {i}" + (" wraps" * 60 if i % 3 == 0 else ""), "body") for i in range(100)]
    write_lines(view, wrapped)
    line40 = view.document().findBlockByNumber(40).firstLineNumber()   # > 40: rows wrapped above
    view.verticalScrollBar().setValue(line40)
    settle()
    top = view.firstVisibleBlock().text()
    write_lines(view, [(f"row {i}" + (" wraps" * 60 if i % 3 == 0 else ""), "body")
                       for i in range(100, 110)])
    settle()
    now = view.firstVisibleBlock().text()
    check(line40 > 40 and top.startswith("row 40") and now == top,
          f"at the block cap with every third row wrapped the reader's line stays under them "
          f"({top[:12]!r} -> {now[:12]!r}; row 40 began at visual line {line40})")
    view.deleteLater()

    # ---- the look, as laws
    for name, p in orchtheme.PALETTES.items():
        bad = orchtheme.failures(p)
        check(not bad, f"the {name} palette clears every contrast floor"
              + (f" -- {bad}" if bad else ""))
    sheet = app.styleSheet()
    check(not orchtheme.lint(sheet), f"the stylesheet has no silent QSS faults {orchtheme.lint(sheet)}")
    styled = orchtheme.styled_roles(sheet)
    unstyled = seen_roles - styled
    unused = styled - seen_roles
    check(not unstyled, f"every role the window uses has a rule ({sorted(unstyled) or 'all'})")
    check(not unused, f"every role the sheet styles is used somewhere ({sorted(unused) or 'all'})")
    check(not lore, f"no flag, file name, ident or hex id on the visible surface ({lore[:4]})")
    # ...the one bar message the smoke cannot provoke (a reset deletes the
    # vault's store), read at its say site: the sentence, never the store's path
    check(not SURFACE_LORE.search(RESET_DONE)
          and re.search(r"_say\(RESET_DONE\b", inspect.getsource(RunTab.reset)) is not None,
          "what a reset says is its sentence, never the store's path (the confirm box shows it)")
    # the words: a caption is one constraint and one pointer (the research's
    # 74 characters a line; two clauses here), never a legend or a run-on, and
    # 'the stack' is nowhere; the Run tab's two wells say what will appear
    caps = [(len(w.text()), w.text()) for w in win.findChildren(QLabel)
            if w.property("role") == "caption" and w.text()]
    long_caps = sorted((n, t[:50]) for n, t in caps if n > CAPTION_MAX)
    said = [w.text()[:50] for w in win.findChildren(QLabel) if "the stack" in w.text()]
    check(caps and not long_caps and not said,
          f"every caption is at most {CAPTION_MAX} characters ({len(caps)}; over: "
          f"{long_caps[:2] or 'none'}) and none says 'the stack' ({said or 'none'})")
    holders = (win.run.summary.placeholderText(), win.run.log.placeholderText())
    check(all(h and not SURFACE_LORE.search(h) for h in holders),
          f"the Compiled and Output wells say what will appear in them ({holders})")
    # a tooltip, a special value or a placeholder that is a sentence starts
    # with a capital, on EVERY line of it: 'attribute 13' and 'hero index 3: …'
    # did not, nor 'modelled: this server …' as a skill tip's second line (a
    # key such as starter_sword or def_2036 is not a sentence; the test is a
    # lower-case WORD then a space or a colon)
    lower = re.compile(r"[a-z]+[ :]")
    texts = []
    for w in win.findChildren(QWidget):
        texts += [("tip", w.toolTip())]
        if isinstance(w, QAbstractSpinBox):
            texts.append(("special", w.specialValueText()))
        if isinstance(w, QLineEdit):
            texts.append(("placeholder", w.placeholderText()))
    tbl = win.party.table
    texts += [("item tip", tbl.item(r, c).toolTip()) for r in range(tbl.rowCount())
              for c in range(tbl.columnCount()) if tbl.item(r, c) is not None]
    texts += [("row tip", it.toolTip(0)) for it in en._walk()]
    texts.append(("fallback", win.names.attr_label(-1)))
    low = sorted({(k, ln[:40]) for k, t in texts if t for ln in t.splitlines() if lower.match(ln)})
    check(len(texts) > 100 and not low,
          f"every tooltip, special value and placeholder that is a sentence starts with a "
          f"capital, every line of it ({len(texts)} read; lower-case: {low[:3] or 'none'})")
    hold, special = win.run.hold, win.run.hold.specialValueText()
    room, want = _spin_field(hold).width() - 4, hold.fontMetrics().horizontalAdvance(special)
    check(special[0].isupper() and room >= want,
          f"the time limit's 'none' value is a capitalised phrase that fits its field "
          f"({special!r}: {want} px of {room})")
    # the Stored character caption is one line down to the window's minimum
    # width (three words longer, 'fresh.' stood alone on a second line at 943
    # px, and the card grew 16 px for one word)
    size = win.size()
    win.tabs.setCurrentWidget(win.run)
    win.resize(win.minimumSizeHint().width(), 720)
    settle(8)
    cap = win.run.stored_cap
    need, room = cap.fontMetrics().horizontalAdvance(cap.text()), cap.contentsRect().width()
    check(need <= room, f"at the window's minimum width ({win.width()} px) the Stored character "
                        f"caption is one line ({need} px of {room})")
    win.resize(size)
    settle(8)
    # the empty state's verb stands apart from its sentence: the gap under the
    # caption is wider than the one over it
    saved = en.to_spec()
    en.from_spec([])
    win.tabs.setCurrentWidget(en)
    settle(4)
    labels = [w for w in en.empty.findChildren(QLabel)]
    title, cap = labels[0], labels[1]
    above = cap.y() - (title.y() + title.height())
    below = en.empty_add.mapTo(en.empty, QPoint(0, 0)).y() - (cap.y() + cap.height())
    check(en.stack.currentWidget() is en.empty and below >= 12 and below > above,
          f"the empty state's button stands apart from its caption ({below} px under it, "
          f"{above} between title and caption)")
    en.from_spec(saved)
    settle()
    primaries = [b for b in win.findChildren(QPushButton) if b.property("role") == "primary"]
    check(len(primaries) == 1 and primaries[0] is win.header.launch_b,
          f"exactly one accent in the window, and it is Launch ({len(primaries)})")
    lb = win.header.launch_b
    got = _pixel(lb, 5, lb.height() // 2)
    check(_near(got, pal["accent"]), f"Launch RENDERS in the accent ({got} vs {pal['accent']})")
    cb = QCheckBox("probe")
    cb.setParent(win.run)
    cb.move(0, 0)
    cb.show()
    settle()
    off = cb.grab().toImage()
    cb.setChecked(True)
    settle()
    on = cb.grab().toImage()
    diff = sum(1 for x in range(min(20, on.width())) for y in range(on.height())
               if on.pixelColor(x, y) != off.pixelColor(x, y))
    corner = on.pixelColor(3, on.height() // 2 - 5).name()
    check(diff > 20, f"a checked box renders differently from an unchecked one ({diff} px)")
    check(_near(corner, pal["check_bg"], 40),
          f"a checked box is the neutral ink, not the accent ({corner} vs {pal['check_bg']})")
    cb.setParent(None)
    cb.deleteLater()
    le = win.header.name
    got = _pixel(le, le.width() // 2, 4)
    check(_near(got, pal["field"], 10), f"a well renders as the field token ({got} vs {pal['field']})")
    # a button drawn in a state, as the style paints it (a hover and a press
    # cannot be had from the pointer here); without its icon on request, on
    # the OPTION only, so the button keeps it
    def painted(b, state, control=QStyle.CE_PushButton, icon=True):
        opt = QStyleOptionButton()
        b.initStyleOption(opt)
        opt.state |= state
        if not icon:
            opt.icon = QIcon()
        img = QImage(b.size(), QImage.Format_ARGB32)
        img.fill(QColor(pal["surface"]))
        painter = QPainter(img)
        b.style().drawControl(control, opt, painter, b)
        painter.end()
        return img, opt

    # a hovered danger button: the CONTRAST of its painted ink on the fill it is
    # painted on, the measure with no tolerance to get wrong -- a count of pixels
    # near the right token gave the same number to the old ink, 7 away. The TEXT
    # alone: the trash icon is tinted error_text at build time and keeps it on
    # hover, and in dark that is the hover ink's own colour at 4.72:1, so with
    # the icon in the picture the best pixel was the icon's whatever the words
    # got (invisible words passed at 4.72). And a COUNT of ink pixels, since
    # one pixel of the right colour passes a best-pixel reading
    rb = win.run.reset_b
    img, _o = painted(rb, QStyle.State_MouseOver, icon=False)
    ground = pal["chip_crit_bg"]
    fill = _count_near(img, ground, 6)
    ink = round(_best_contrast(img, ground), 2)
    core = _ink_pixels(img, ground, orchtheme.TEXT_FLOOR)
    check(fill > 100 and ink >= orchtheme.TEXT_FLOOR and core >= 20,
          f"a hovered danger button paints its words in an ink that clears "
          f"{orchtheme.TEXT_FLOOR}:1 on its hover fill ({fill} px fill, {core} px of ink, "
          f"the best {ink}:1; the icon left out of the picture)")
    # a press keeps its relief with focus on it: the shaded top and lit foot,
    # not the ring on every side (a tier's :focus rule out-ranked :pressed)
    edges = {}
    for tag, b, top, foot in (("default", win.header.compile_b, "border_shade", "border_lit"),
                              ("primary", lb, "accent_shade", "accent_lit")):
        img, _o = painted(b, QStyle.State_Sunken | QStyle.State_HasFocus)
        got_top = img.pixelColor(b.width() // 2, 0).name()
        got_foot = img.pixelColor(b.width() // 2, b.height() - 1).name()
        edges[tag] = (_near(got_top, pal[top], 6) and _near(got_foot, pal[foot], 6),
                      got_top, got_foot)
    check(all(v[0] for v in edges.values()),
          f"a pressed button with focus keeps its relief, default and primary "
          f"({ {k: (v[1], v[2]) for k, v in edges.items()} })")
    # a checked box under the pointer shifts its fill, off the token audited for it
    cb = QCheckBox("probe")
    cb.setParent(win.run)
    cb.move(0, 0)
    cb.setChecked(True)
    cb.show()
    settle()
    img, opt = painted(cb, QStyle.State_MouseOver, QStyle.CE_CheckBox)
    ind = cb.style().subElementRect(QStyle.SE_CheckBoxIndicator, opt, cb)
    hovered = img.pixelColor(ind.x() + 3, ind.center().y() - 5).name()     # off the tick
    check(_near(hovered, pal["check_hover"], 6)
          and orchtheme.distance(hovered, pal["check_bg"]) >= 6,
          f"a hovered checked box RENDERS the shifted fill ({hovered} vs {pal['check_hover']}; "
          f"at rest {pal['check_bg']})")
    cb.setParent(None)
    cb.deleteLater()
    # a log with both bars shows no square where they meet (the light theme
    # drew Fusion's bordered corner there)
    view = QPlainTextEdit()
    view.setAttribute(Qt.WA_DontShowOnScreen, True)
    view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    view.resize(300, 200)
    view.show()
    settle()
    img = view.grab().toImage()
    vb, hb = view.verticalScrollBar(), view.horizontalScrollBar()
    cx, cy = vb.mapTo(view, QPoint(0, 0)).x(), hb.mapTo(view, QPoint(0, 0)).y()
    corner = (cx, cy, cx + vb.width(), cy + hb.height())
    off = (vb.width() * hb.height()) - _count_near(img, pal["log_bg"], 3, corner)
    check(vb.isVisible() and hb.isVisible() and off == 0,
          f"where a log's two bars meet, the corner is the log's own ground ({off} px of "
          f"{vb.width()}x{hb.height()} are not)")
    view.deleteLater()
    # focus you can see, where keyboard focus needs the window to be active --
    # measured on grabs of the WINDOW, not of the widget (see _moved)
    activate()
    lost = "the window could not hold keyboard focus, so focus cannot be seen"
    win.tabs.setCurrentWidget(en)
    settle()
    if focus(en.add):
        rest = win.grab().toImage()
        if focus(en.tree):
            n = _moved(win, en.tree, rest, win.grab().toImage())
            check(n >= orchtheme.TAB_FOCUS_FLOOR,
                  f"the encounter list SHOWS keyboard focus (a pixel moved {n} on the page)")
        else:
            skip("the encounter list shows keyboard focus", lost)
    else:
        skip("the encounter list shows keyboard focus", lost)
    tb = win.tabs.tabBar()
    lb.clearFocus()
    settle()
    at_rest = win.grab().toImage()
    if focus(lb):
        n = _moved(win, lb, at_rest, win.grab().toImage())
        check(n >= orchtheme.TAB_FOCUS_FLOOR,
              f"Launch's focus ring shows inside its own fill (a pixel moved {n})")
        before_tab = win.grab().toImage()
        QApplication.sendEvent(lb, QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier))
        settle()
        after_tab, cur = win.grab().toImage(), tb.tabRect(tb.currentIndex())
        n = _moved(win, tb, before_tab, after_tab, cur)
        check(tb.hasFocus() and n >= orchtheme.TAB_FOCUS_FLOOR,
              f"Tab from Launch lands on the tab strip, and the strip SHOWS it on the page "
              f"(a pixel of the tab moved {n}; the floor is {orchtheme.TAB_FOCUS_FLOOR})")
        # ...and shows it as a MARK: the theme holds a focus ring to 3:1, and
        # the fill alone was 1.13:1 in light (17 from the page, faint) -- the
        # weakest focus cue in the app on the control that switches pages.
        # The focused tab's top edge is the ring's own ink; its contrast is
        # read against the pixels it replaced
        c = _shifted(win, tb, before_tab, after_tab, cur)
        check(c >= orchtheme.MARK_FLOOR,
              f"and the focused tab carries a cue in the focus ring's ink: a pixel of the tab "
              f"changed by {c:.2f}:1, against the ring floor of {orchtheme.MARK_FLOOR}:1")
    else:
        skip("Launch and the tab strip show keyboard focus", lost)
    # the wheel in the ACTIVE window, which is normal use: Qt gives a WheelFocus
    # widget focus BEFORE any filter sees the wheel, so the inactive law above
    # was green while every combo the pointer crossed took the wheel here
    wheelable = [w for w in win.findChildren(QComboBox) + win.findChildren(QAbstractSpinBox)
                 if w.focusPolicy() == Qt.WheelFocus]
    check(not wheelable, f"no combo or spin box can take focus from the wheel ({len(wheelable)} "
                         f"of {len(win.findChildren(QComboBox)) + len(win.findChildren(QAbstractSpinBox))})")
    m0 = en.groups[0].members[0]
    en.select(m0)
    settle()
    page, bar, pk = en._pages[m0], en._pages[m0].verticalScrollBar(), m0.bar.slots[0]
    scrolls = sys.platform == "win32" and bar.maximum() > 0
    if scrolls and focus(en.tree):
        rolled = []
        for tag, w, value in (("skill slot", pk, pk.currentIndex), ("Level", m0.level, m0.level.value)):
            bar.setValue(0)
            settle()
            v0 = value()
            _real_wheel(win, w)
            settle(5)
            rolled.append((tag, bar.value(), v0, value(), w.hasFocus()))
        check(all(px > 0 and v0 == v1 and not took for _t, px, v0, v1, took in rolled),
              f"in the ACTIVE window a real wheel over an unfocused skill slot and Level spin "
              f"scrolls the page and leaves both alone, unfocused ({rolled})")
        bar.setValue(0)
        if focus(pk):
            v0 = pk.currentIndex()
            _real_wheel(win, pk)
            settle(5)
            check(pk.currentIndex() != v0 and bar.value() == 0,
                  f"and a FOCUSED combo still takes the wheel, the page staying put "
                  f"({v0} -> {pk.currentIndex()}, {bar.value()} px)")
            pk.setCurrentIndex(v0)
        else:
            skip("a focused combo takes the wheel", lost)
        pk.clearFocus()
        win.tabs.setCurrentWidget(win.party)
        settle()
        tbar = win.party.table.verticalScrollBar()
        tbar.setValue(0)
        settle()
        lvl3 = win.party.rows[3][3]
        v0 = lvl3.value()
        _real_wheel(win, lvl3)
        settle(5)
        check(lvl3.isEnabled() and tbar.value() > 0 and lvl3.value() == v0,
              f"a real wheel over an unlocked hero's Level spin scrolls the heroes table "
              f"({tbar.value()} rows) and leaves the level at {v0}")
    else:
        skip("the wheel in the active window",
             lost if scrolls else "the page does not scroll at this size, or this is not Windows")
    # a popup keeps its own edge: a non-editable combo's (the profession pickers
    # and the Skills filter -- Fusion's menu mode framed the view a second
    # time, top and bottom, and the list mode shows ten rows unless told the
    # count), a Picker's, and the completer's, each opened hidden with the
    # focus a real one has. One arm each: an arm that opens without focus
    # skips itself, not the others (the completer's proxy focus, taken after a
    # fixed few turns while the combos had just handed activation back, once
    # skipped the whole law)
    def rim_of(img):
        return [img.pixelColor(x, y).name()
                for x, y in ((0, 0), (img.width() - 1, 0), (0, img.height() - 1),
                             (img.width() - 1, img.height() - 1), (img.width() // 2, 0),
                             (img.width() // 2, img.height() - 1))]

    activate()
    for tag, combo, page in (("profession", win.party.secondary, win.party),
                             ("Picker", win.party.weapon, win.party),
                             ("Skills filter", win.skills.prof, win.skills)):
        win.tabs.setCurrentWidget(page)
        settle()
        holder = combo.view().window()
        holder.setAttribute(Qt.WA_DontShowOnScreen, True)
        combo.showPopup()
        settle(5)
        v = combo.view()
        rim = rim_of(holder.grab().toImage())
        focused, filling = v.hasFocus(), v.geometry() == holder.rect()
        edged = all(_near(c, pal["border_strong"], 6) for c in rim)
        barred = v.verticalScrollBar().isVisible()
        said = (f"{holder.width()}x{holder.height()} view {v.geometry().getRect()} rim "
                f"{rim[0]}/{rim[4]}/{rim[5]}"
                + ("" if combo.isEditable() else f", {combo.count()} rows, a bar: {barred}"))
        combo.hidePopup()
        settle()
        if focused:
            # a Picker's list scrolls by design (its rows are many, its type-to-
            # filter the way through them); a plain combo's says its count
            check(filling and edged and (combo.isEditable() or not barred),
                  f"the focused {tag} popup is one box in the popup edge, the view filling it"
                  f"{'' if combo.isEditable() else ', its rows unscrolled'} ({said})")
        else:
            skip(f"the {tag} popup is one box in the popup edge", "it opened without focus")
    win.tabs.setCurrentWidget(win.party)
    settle()
    pop = win.party.weapon.completer().popup()
    pop.setAttribute(Qt.WA_DontShowOnScreen, True)
    focus(win.party.weapon)                      # the popup's focus is its line edit's, by proxy
    win.party.weapon.completer().setCompletionPrefix("s")
    win.party.weapon.completer().complete()
    settle(5)
    rim = rim_of(pop.grab().toImage())
    focused, edged = pop.hasFocus(), all(_near(c, pal["border_strong"], 6) for c in rim)
    pop.hide()
    settle()
    if focused:
        check(edged, f"the focused completer popup is one box in the popup edge (its rows scroll "
                     f"by design: {pop.width()}x{pop.height()}, rim {rim[0]}/{rim[4]}/{rim[5]})")
    else:
        skip("the completer popup is one box in the popup edge", "it opened without focus")
    # ...and the row limit itself, a census: a plain combo lists every row it
    # holds, so none scrolls (the Skills filter's twelve rows had no law, and
    # its limit undone hid Dervish and Common behind a bar with every law
    # green); the next combo built without one is named here
    plain = [c for c in win.findChildren(QComboBox) if not c.isEditable()]
    over = [(c.accessibleName() or c.toolTip()[:30] or "a combo", c.count(), c.maxVisibleItems())
            for c in plain if c.count() > c.maxVisibleItems()]
    check(len(plain) >= 20 and not over,
          f"every plain combo in the window lists all its rows without a bar ({len(plain)} combos; "
          f"over their limit: {over or 'none'})")
    heights = {}
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        settle()
        w = win.minimumSizeHint().width()
        check(w <= 1180, f"tab {win.tabs.tabText(i)!r}: nothing floors the window wider than "
                         f"1180 px ({w})")
        # one field height on the tab: a spin box's edit sub-control is 25 px
        # tall to a combo's 22 of content, so every spin stood 35 px beside
        # 32 px combos and line edits (the heroes table's cells have their own)
        for cls in (QComboBox, QAbstractSpinBox, QLineEdit):
            for f in win.findChildren(cls):
                if f.isVisibleTo(win) and not isinstance(f.parent(), (QComboBox, QAbstractSpinBox)) \
                        and not _within(f, QTableWidget):
                    heights.setdefault(type(f).__name__, set()).add(f.height())
    check(len(heights) >= 4 and len(set().union(*heights.values())) == 1,
          f"every combo, spin box and line edit on the four tabs is one height ({heights})")
    # the gutters: the status chip ends at the page's own right gutter, and the
    # Run tab's bare overlines (COMPILED, OUTPUT) start where the card titles
    # do -- the two fixes the fix pass made and never measured
    at = win.names_chip.mapTo(win, QPoint(0, 0))
    gap, gutter = win.width() - at.x() - win.names_chip.width(), win.party.outer.contentsMargins().right()
    check(gap == gutter, f"the status chip's right gap is the page gutter ({gap} of {gutter} px)")
    # ...and the bar's MESSAGE starts at the left one: QStatusBar paints it 6
    # px in, a number of its own that no margin moves, the one left edge in
    # the window off the gutter. Measured off the painted band, through the
    # code's own say path
    win.run._say("Compiled; 1 note about the stored character.")
    settle(4)
    sb = win.statusBar()
    band = QRect(0, sb.mapTo(win, QPoint(0, 0)).y() + 2, at.x() - 2, sb.height() - 2)
    ink, _r = _ink_span(win.grab().toImage(), band, pal["surface"])
    left = win.party.outer.contentsMargins().left()
    check(ink is not None and abs(ink - left) <= 1,
          f"the status bar's message starts at the page gutter (ink at {ink}, the gutter {left})")
    win.tabs.setCurrentWidget(win.run)
    settle()
    over = {w.text(): w.mapTo(win, QPoint(0, 0)).x() for w in win.run.findChildren(QLabel)
            if w.property("role") == "overline"}
    check({"LAUNCH OPTIONS", "COMPILED", "OUTPUT"} <= set(over)
          and over["COMPILED"] == over["OUTPUT"] == over["LAUNCH OPTIONS"],
          f"the Run tab's COMPILED and OUTPUT start at the card titles' x ({over})")
    win.tabs.setCurrentIndex(0)
    settle()
    shot = os.path.join(out_dir, "smoke_screen.png")
    win.grab().save(shot)
    check(os.path.isfile(shot), f"screenshot {shot}")
    return led.verdict()


# ---------------------------------------------------------------- snap

def snap(win, app, out_dir, theme):
    """`--snap`: every surface to a PNG, rendered on the NATIVE platform but
    never shown on screen -- the offscreen platform stubs the font database
    and lies about every width (Dream-World-IX measured 2-3x). Prints each
    surface's size and hints, the numbers sizing bugs live in. Read the PNGs;
    a visual claim nobody looked at is a guess."""
    out_dir = vaultpath.resolve_out(out_dir, what="snap output")
    os.makedirs(out_dir, exist_ok=True)
    win.setAttribute(Qt.WA_DontShowOnScreen, True)
    win.show()
    app.processEvents()

    def grab(tag, widget=None, scale=1):
        # the header's summary is debounced (50 ms): let it land, or the render
        # shows a state the operator never sees ('3 groups' over an empty list)
        t_end = time.perf_counter() + 2.0
        while win._summary_timer.isActive() and time.perf_counter() < t_end:
            app.processEvents()
            time.sleep(0.01)
        for _ in range(3):
            app.processEvents()
        w = widget or win
        img = w.grab().toImage()
        if scale > 1:
            img = img.scaled(img.width() * scale, img.height() * scale,
                             Qt.IgnoreAspectRatio, Qt.FastTransformation)
        path = os.path.join(out_dir, f"{tag}_{theme}.png")
        img.save(path)
        print(f"  {tag:<18} {w.width()}x{w.height()}  min {w.minimumSizeHint().width()}x"
              f"{w.minimumSizeHint().height()}  -> {path}")

    for i, tag in enumerate(("skills", "party", "enemies", "run")):
        win.tabs.setCurrentIndex(i)
        grab(tag)
    win.tabs.setCurrentWidget(win.enemies)
    if win.enemies.groups:
        win.enemies.select(win.enemies.groups[-1].members[0] if win.enemies.groups[-1].members
                           else win.enemies.groups[-1])
        grab("enemies_boss")
        win.enemies.select(win.enemies.groups[0])
        grab("enemies_group")
    win.tabs.setCurrentWidget(win.run)
    win.run.compile()
    grab("run_compiled")
    grab("header_x2", win.header, 2)
    win.tabs.setCurrentWidget(win.skills)
    win.skills.filter.setText("heal")
    grab("skills_filtered")
    win.skills.filter.setText("")
    saved = win.enemies.to_spec()
    win.enemies.from_spec([])
    win.tabs.setCurrentWidget(win.enemies)
    # the compile's message, six seconds long, over a spec that cannot compile
    # (no groups): the bar an operator sees here is empty
    win.statusBar().clearMessage()
    grab("enemies_empty")
    win.enemies.from_spec(saved)
    win.run.compile()                            # the round trip marked the compile stale
    win.resize(1000, 720)
    for i, tag in enumerate(("skills", "party", "enemies", "run")):
        win.tabs.setCurrentIndex(i)
        grab(f"narrow_{tag}")
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", default=None, help="a saved spec to open")
    ap.add_argument("--smoke", default=None, metavar="DIR",
                    help="drive every panel once, write a screenshot there, exit")
    ap.add_argument("--snap", default=None, metavar="DIR",
                    help="render every surface to PNGs there (never shown on screen), exit")
    ap.add_argument("--theme", default="auto", choices=("auto", "dark", "light"),
                    help="the palette (default: follow the OS)")
    ap.add_argument("--no-names", action="store_true",
                    help="skip resolving names from the archive (ids only; faster)")
    args = ap.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme = orchui.apply_theme(app, args.theme)
    t0 = time.perf_counter()
    world = content.load()
    names = Names(world, resolve=not args.no_names)
    print(f"content and names loaded in {time.perf_counter() - t0:.1f} s ({theme} theme)"
          + (f" -- {names.why}" if names.why else ""))
    win = Window(world, names)
    win.from_spec(sandbox.example_spec())
    if args.spec:
        win.run.load(args.spec)                  # the header's Open: said in the bar,
                                                 # what the window could not hold too
    if args.smoke or args.snap:
        rc = smoke(win, app, args.smoke) if args.smoke else snap(win, app, args.snap, theme)
        QTimer.singleShot(0, app.quit)
        app.exec()
        return rc
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
