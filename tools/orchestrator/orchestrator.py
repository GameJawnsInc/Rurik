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
import content        # noqa: E402
import vaultpath      # noqa: E402

try:
    from PySide6.QtCore import (QElapsedTimer, QEvent, QPoint, QPointF, QProcess,
                                QProcessEnvironment, Qt, QTimer, Signal)
    from PySide6.QtGui import (QColor, QFont, QImage, QKeyEvent, QPainter, QTextCharFormat,
                               QTextCursor, QWheelEvent)
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication,
                                   QBoxLayout, QCheckBox, QComboBox,
                                   QCompleter, QFileDialog, QFormLayout, QFrame,
                                   QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                                   QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                                   QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                                   QStyle, QStyleOptionButton, QStyleOptionComboBox,
                                   QDoubleSpinBox, QSplitter, QStackedWidget,
                                   QTableWidget, QTableWidgetItem, QTabWidget,
                                   QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"the run orchestrator needs PySide6 (py -m pip install PySide6): {exc}")

import orchtheme      # noqa: E402  (tools/orchestrator: palettes, sheet, audit)
import orchui         # noqa: E402  (tools/orchestrator: the widget helpers)
from orchui import (ROLE_ID, ROLE_PARTS, button, caption, card, chip,  # noqa: E402
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
                self.why = f"names unresolved ({type(exc).__name__}: {exc}); ids shown"

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
        return self.attr.get(aid, f"attribute {aid}")

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


GRADE_TIP = {"hand": "modelled: this server acts it from a hand-verified [skill_effect] row",
             "label": ("label: acts through a label parsed from the client's own description "
                       "template, not a hand-verified row (SKILLS-LT); the gamesrv log says so "
                       "at every cast"),
             None: "draws and times correctly; this server does nothing more with it"}


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
        if parts and not isinstance(self.view().itemDelegate(), orchui.SkillDelegate):
            self.view().setItemDelegate(orchui.SkillDelegate(self.view()))
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
    bars are in-game). Wide enough for a whole skill label."""

    changed = Signal()                          # a slot edited

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.slots = []
        for i in range(sandbox.BAR_SLOTS):
            row, col = i % 4, (i // 4) * 3
            num = role_label(str(i + 1), "slot")
            num.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            num.setFixedWidth(14)
            pk = Picker(chars=16)
            pk.setAccessibleName(f"Skill slot {i + 1}")
            num.setBuddy(pk)
            pk.currentIndexChanged.connect(lambda _i: self.changed.emit())
            grid.addWidget(num, row, col)
            grid.addWidget(pk, row, col + 1)
            self.slots.append(pk)
        grid.setColumnMinimumWidth(2, 16)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)

    def set_professions(self, professions):
        pairs = skill_choices(self.names, professions)
        parts = {s: self.names.skill_parts(s) for _l, s in pairs if s}
        tips = {s: self.names.skill_tip(s) for s in parts}
        for pk in self.slots:
            pk.set_choices(pairs, parts=parts, tips=tips)

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
        self.chip = chip("", "info")
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
            lab.setToolTip(f"attribute {aid}" + (" — the primary's own attribute"
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
            "Unlocked account-wide. The character's bar and every hero's are filled in game "
            "from these; a hero may also use its own list.",
            tip="The account's unlock set (0x001D). A hero's usable library is its own list "
                "plus this one (herolib.hero_library)."))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter by name, id or attribute")
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
        row.addWidget(self.filter, 3)
        row.addWidget(self.prof, 1)
        row.addSpacing(4)
        row.addWidget(self.modelled_only)
        row.addStretch(1)
        for b in (self.all_b, self.none_b, self.party_b):
            row.addWidget(b)
        outer.addLayout(row)
        self.list = orchui.PlaceholderList("No skill matches this filter.")
        self.list.setItemDelegate(orchui.SkillDelegate(self.list))
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

    def _set_shown(self, on):
        for it in self._items():
            if not it.isHidden():
                it.setCheckState(Qt.Checked if on else Qt.Unchecked)

    def set_party_professions(self, profs):
        self.party_professions = set(int(p) for p in profs if p)

    def unlock_party(self):
        want = self.party_professions | {0}
        for it in self._items():
            sp = self.names.skill_profession(int(it.data(ROLE_ID)))
            it.setCheckState(Qt.Checked if sp in want else Qt.Unchecked)

    def ids(self):
        return sorted(int(it.data(ROLE_ID)) for it in self._items()
                      if it.checkState() == Qt.Checked)

    def set_ids(self, ids):
        want = set(int(s) for s in ids)
        for it in self._items():
            it.setCheckState(Qt.Checked if int(it.data(ROLE_ID)) in want else Qt.Unchecked)
        self._count()


# ---------------------------------------------------------------- Party

class PartyTab(QWidget):
    """The character, and which heroes are unlocked (each with a profession
    and a body). No bars, no ranks: those are the in-game panels' job."""

    COLS = ("", "#", "Hero", "Profession", "Body", "Level")
    # Below this width the Character card goes ABOVE the table, as main laid it
    # out: side by side, the table cannot hold a whole profession, a whole body
    # and a readable name beside a 320 px card (measured: 1,114 px needed).
    STACK_BELOW = 1120
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
        self.outer.addWidget(cc, 0)

        self.count = chip("", "info")
        hc = card("Heroes", trailing=self.count)
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
        # Profession and Body are sized for their longest item (a cell widget
        # takes the cell's width whatever its hint, so a guess clips); the hero's
        # NAME is what yields, as a text item with an honest ellipsis.
        for col, mode, width in ((0, QHeaderView.Fixed, 32), (1, QHeaderView.Fixed, 40),
                                 (2, QHeaderView.Stretch, 0), (3, QHeaderView.Fixed, 150),
                                 (4, QHeaderView.Fixed, 256), (5, QHeaderView.Fixed, 88)):
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
            num.setToolTip(f"hero index {idx}: what a spec's `hero = {idx}` names")
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
        self._count()

    def _arrange(self, stacked):
        """Side by side (a 320 px card, five form rows) or stacked (a full-width
        card, the form in two columns so it stays short)."""
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
                r, c = (i, 0) if i < 3 else (i - 3, 2)
                self.cgrid.addWidget(lab, r, c)
                self.cgrid.addWidget(w, r, c + 1)
            self.cgrid.setColumnStretch(1, 1)
            self.cgrid.setColumnStretch(3, 1)
        else:
            self.outer.setDirection(QBoxLayout.LeftToRight)
            cc.setFixedWidth(self.CARD_W)
            for i, (lab, w) in enumerate(self.fields):
                self.cgrid.addWidget(lab, i, 0)
                self.cgrid.addWidget(w, i, 1)
            self.cgrid.setColumnStretch(1, 1)
            self.cgrid.setColumnStretch(3, 0)

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
        return {"profession": prim, "secondary": sec, "level": self.level.value(),
                "weapon": self.weapon.value() or None, "offhand": self.offhand.value() or None}

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
        self.offhand.set_value(player.get("offhand") or o or "")
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


# ---------------------------------------------------------------- Enemies

def scrolled(widget):
    """A page that scrolls when the window is short, with no frame of its own."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(widget)
    return area


class MemberEditor(QWidget):
    """One hostile: its body, its weapon, its bar, its ranks -- one page of the
    Enemies tab's detail pane."""

    def __init__(self, names, on_remove, on_change=None, parent=None):
        super().__init__(parent)
        self.names = names
        self.on_change = on_change or (lambda _ed: None)
        self.where = (1, 1)
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

        top = QHBoxLayout()
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
        self.speed.setSpecialValueText("the weapon's")
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
        for w in (self.health, self.glow, self.speed, self.dlo, self.dhi):
            w.valueChanged.connect(lambda *_a: self._changed())
        self.weapon_item.currentIndexChanged.connect(lambda _i: self._changed())
        self.bar.changed.connect(self._changed)
        self.ranks.changed.connect(self._changed)
        self._template()
        self._boss(self.boss.isChecked())

    def profession(self):
        row = self.names.world.rows("npc").get(self.template.value()) or {}
        return int(row.get("profession", 0) or 0)

    def display_name(self):
        return self.template.currentText().split("  [")[0] or "hostile"

    def set_where(self, group, member):
        self.where = (group, member)
        self._titles()

    def _titles(self):
        prof = sandbox.PROFESSIONS.get(self.profession(), "no profession")
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
        # 8 + the 12 px a hostile page's scroll bar takes, so both kinds of page
        # share one right edge
        page.setContentsMargins(0, 0, 20, 0)
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
        self.remove_b = button("Remove group", "danger", icon="trash")
        self.remove_b.clicked.connect(lambda: owner.remove(self))
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
        self.roster.setAccessibleName("This group's hostiles")
        self.roster.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.roster.itemClicked.connect(self._pick)
        self.roster.itemActivated.connect(self._pick)
        box.body.addWidget(self.roster)
        row = QHBoxLayout()
        self.add = button("Add hostile", icon="plus")
        self.add.clicked.connect(lambda: owner.select(self.add_member()))
        row.addWidget(self.add)
        row.addStretch(1)
        box.body.addLayout(row)
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
        for ed in self.members:
            boss = "Boss  ·  " if ed.boss.isChecked() else ""
            it = QListWidgetItem(f"{boss}{ed.display_name()}   —   {ed.summary()}")
            it.setData(Qt.UserRole, ed)
            it.setToolTip("Select to edit this hostile.")
            self.roster.addItem(it)
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
        self.members.remove(ed)
        self.owner._detach(ed)
        for m, e in enumerate(self.members, 1):
            e.set_where(self.index, m)
        self._count()
        self.owner._structure_changed(select=self if not self.members else self.members[0])

    def _count(self):
        n = len(self.members)
        empty = "An empty group can't run. Add a hostile or remove the group."
        set_chip(self.count, f"{n} of {sandbox.GROUP_SIZE_MAX}",
                 "warn" if not n else "info", tip=empty if not n else "")
        self.hint.setText(empty if not n else
                          "A group spawns together. Select a hostile to edit it.")
        self.add.setEnabled(n < sandbox.GROUP_SIZE_MAX)
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
        # icon-only: three labelled buttons do not fit the list's width, and the
        # group and hostile pages carry a labelled Remove of their own
        self.remove_b = button("", "quiet", icon="remove", name="Remove the selection",
                               tip="Remove the selected hostile, or the selected group "
                                   "with its hostiles.")
        self.add.clicked.connect(lambda: self.select(self.add_group()))
        self.add_member_b.clicked.connect(self._add_member_here)
        self.remove_b.clicked.connect(self._remove_selected)
        for b in (self.add, self.add_member_b, self.remove_b):
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

    def remove(self, ed):
        for m in list(ed.members):
            self._detach(m)
        self.groups.remove(ed)
        self._detach(ed)
        self._renumber()
        self._structure_changed(select=(self.groups[-1] if self.groups else None))

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

    def _remove_selected(self):
        cur = self.current()
        if isinstance(cur, MemberEditor):
            g = self._group_of(cur)
            if g:
                g.remove(cur)
        elif isinstance(cur, GroupEditor):
            self.remove(cur)

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
                        + ("\nthe boss: the quest's kill objective" if ed.boss.isChecked() else ""))

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
        self.remove_b.setEnabled(cur is not None)

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
# What the harness prints that decides how a run ENDED (session.py, runwatch.py).
RUN_MARKS = {"retracted": "RUN VERDICT RETRACTED", "crash": "ERROR DIALOG captured",
             "fail": "RUN VERDICT: FAIL"}
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


def n_of(n, word, plural=None):
    """'1 note', '2 notes': the count with its noun, never 'note(s)'."""
    return f"{n} {word if n == 1 else (plural or word + 's')}"


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
    # not). Count the lines about to go, in the bar's own units.
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
        bar.setValue(bar.value() - lost)


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
        self.hold.setSpecialValueText("until the client closes")
        self.hold.setFixedWidth(220)
        form.addRow("End after", self.hold)
        opts.body.addLayout(form)
        self.hold.valueChanged.connect(self.mark_stale)
        opts.body.addWidget(caption("Closing the game client ends the run and the servers."))
        opts.body.addStretch(1)
        store = card("Stored character")
        store.body.addWidget(caption(
            "What you set in game (bars, ranks, hero builds) carries to the next run. "
            "A reset makes the next login start fresh; the spec is untouched.",
            tip="Every sandbox run passes --persist; the store is vault/state/characters/."))
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
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(20000)
        self.log.setAccessibleName("Run output")
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
        self._say(f"Saved {path}")
        return path

    def load(self, path=None):
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "Open a spec", self.specs_dir(),
                                                   "TOML (*.toml)")
        if not path:
            return
        prev = self.window.to_spec()
        spec = None
        try:
            spec = sandbox.load_spec(path)       # a TOML error leaves the tabs untouched...
            self.window.from_spec(spec)
        except Exception as exc:                 # noqa: BLE001 -- said, not swallowed
            why = f"{type(exc).__name__}: {exc}"
            if spec is None:
                self._say(f"Could not open {os.path.basename(path)}: {why}", 15000)
                return
            # ...but a row that raises inside from_spec does not: the name, the
            # party and the unlocks were written and the encounter torn down
            # before it, so the message would be false, and Save would default
            # to the file that failed. Put the previous spec back (to_spec's
            # own shape, so it cannot raise).
            self.window.from_spec(prev)
            self._say(f"Could not open {os.path.basename(path)} ({why}); your spec is "
                      f"unchanged", 15000)
            return
        self._say(f"Opened {path}")

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
            self.status.setToolTip(f"{BUILD_SLICE}\n\n{missing}")
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
        if line.strip().startswith(">>> "):      # the dialog's own line, for the chip's hover
            self._assert = line.strip()[4:]

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
        removed = sandbox.reset_store()
        self._say(f"Removed {removed}; the next login re-seeds the character.", 8000)
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


class Window(QMainWindow):
    def __init__(self, world, names):
        super().__init__()
        self.world, self.names = world, names
        self.setWindowTitle("Rurik run orchestrator")
        self.resize(1280, 860)
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


def _best_contrast(img, ground, inset=3):
    """The highest contrast any pixel of `img`, `inset` px in from its edges,
    makes against `ground`: a glyph's core ink, whatever the sheet names it."""
    best = 0.0
    for y in range(inset, img.height() - inset):
        for x in range(inset, img.width() - inset):
            best = max(best, orchtheme.contrast(img.pixelColor(x, y).name(), ground))
    return best


def _spin_field(sp):
    """A spin box's line edit (QAbstractSpinBox.lineEdit() is protected)."""
    return sp.findChild(QLineEdit)


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


def smoke(win, app, out_dir):
    """`--smoke`: drive every panel once with the window up, then exit.

    A window nobody has clicked through is a window that may not open; this
    runs the click path in code so a refactor cannot leave a dead tab behind
    a green suite. Writes a screenshot and prints one line per check; exits
    non-zero on any failure. Never writes into the working tree.

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
    [skip] when it cannot have that. The window is native but never on the
    screen (WA_DontShowOnScreen, as --snap renders)."""
    out_dir = vaultpath.resolve_out(out_dir, what="smoke output")
    os.makedirs(out_dir, exist_ok=True)
    fails = []
    pal = orchui.PAL

    def check(cond, label):
        print(f"  [{'ok' if cond else 'FAIL'}] {label}")
        if not cond:
            fails.append(label)

    def skip(label, why):
        print(f"  [skip] {label} -- {why}")

    def settle(n=3):
        for _ in range(n):
            app.processEvents()

    def focus(w):
        w.setFocus(Qt.TabFocusReason)
        settle()
        return win.isActiveWindow() and w.hasFocus()

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
        pill_px = {}
        for grade in ("hand", "label"):
            item = next((it for it in win.skills._items() if not it.isHidden()
                         and it.data(ROLE_PARTS)[2] == grade
                         and vp.rect().contains(lst.visualItemRect(it))), None)
            if item is None:
                continue
            r = lst.visualItemRect(item)
            band = r.adjusted(r.width() - 160, 0, 0, 0)
            parts = item.data(ROLE_PARTS)
            with_pill = vp.grab(band).toImage()
            item.setData(ROLE_PARTS, (parts[0], parts[1], None))
            settle()
            without = vp.grab(band).toImage()
            item.setData(ROLE_PARTS, parts)
            pill_px[grade] = _diff(with_pill, without)
        check(pill_px.get("hand", 0) > 40 and pill_px.get("label", 0) > 40,
              f"the list RENDERS a pill for each grade (pixels a row loses without it: {pill_px})")
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
    win.skills.party_b.click()
    ids = set(win.skills.ids())
    check(ids and all(win.names.skill_profession(s) in {0, 1, 3} for s in ids)
          and any(win.names.skill_profession(s) == 3 for s in ids),
          "'Unlock party only' unlocks Warrior, Monk and common skills only")

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
    for w, h, want in ((1280, 860, False), (1000, 720, True)):
        win.resize(w, h)
        settle(6)
        _c, prof3, body3, _lv = win.party.rows[3]
        profs = [prof3.itemText(i) for i in range(prof3.count())]
        clipped = [t for t in profs if not _fits(prof3, t)]
        bodies = [body3.itemText(i) for i in range(body3.count())
                  if body3.itemData(i) in ("hatcher", "academy_monk", "bandit_raider")]
        bclipped = [t for t in bodies if not _fits(body3, t)]
        check(win.party.stacked is want and not clipped and bodies and not bclipped,
              f"at {w} px the Character card is {'stacked above' if want else 'beside'} the "
              f"table, every profession fits its combo ({len(profs)}; clipped {clipped}) and "
              f"the common bodies fit theirs (clipped {bclipped})")
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
    win.resize(size)
    settle(6)

    # ---- the Enemies tab
    en = win.enemies
    g = en.groups[0]
    g.add_member()
    g.add_member()
    check(len(g.members) == 4 and not g.add.isEnabled(), "a group fills to four and the add stops")
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
    check(isinstance(pk.view().itemDelegate(), orchui.SkillDelegate),
          "and its drop-down draws rows the way the Skills list does")
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
    en.remove(g4)
    settle()
    check("holds the boss" in g3.subtitle.text() and g3.note.isHidden(),
          "and removing it puts the note back")
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
    t_end = time.perf_counter() + 2.0            # the summary is debounced: let it land
    while win._summary_timer.isActive() and time.perf_counter() < t_end:
        settle(1)
        time.sleep(0.01)
    check("2 heroes" in win.header.summary.text() and "7 hostiles" in win.header.summary.text(),
          f"the header's summary follows the spec ({win.header.summary.text()!r})")
    path = win.run.save(os.path.join(out_dir, "smoke_spec.toml"))
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
        # a rank, and a rank on the spins a template change REBUILDS
        def rank():
            sp = next(iter(m0.ranks.spins.values()))
            sp.setValue(sp.value() + 1)
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
    # leaves the spec as it was: the message says nothing opened, so nothing may
    # have -- and Save must not default to the file that failed
    broken = os.path.join(out_dir, "smoke_broken.toml")
    with open(broken, "w", encoding="utf-8") as fh:
        fh.write('name = "smoke-broken"\n\n[player]\nprofession = 1\nlevel = 7\n\n[[groups]]\n\n'
                 '[[groups.members]]\nnpc = "bandit_raider"\ndamage = [6]\n')
    before = win.to_spec()
    win.run.load(broken)
    settle()
    msg = win.statusBar().currentMessage()
    check(win.to_spec() == before and msg.startswith("Could not open") and "unchanged" in msg,
          f"a spec file whose row fails to load leaves the spec unchanged, and says so "
          f"({msg!r})")
    check(not strays(), f"and after every load, still one window ({len(strays())} stray)")
    # how a run ended is read from what the harness PRINTS -- print sites, not
    # the source whole: the same files quote the old lines in comments
    harness = ""
    for name in ("session.py", "runwatch.py"):
        with open(os.path.join(ROOT, "toolkit", "harness", name), encoding="utf-8") as fh:
            harness += fh.read()
    printed = {key: bool(re.search(r"print\([^\n]*" + re.escape(needle), harness))
               for key, needle in RUN_MARKS.items()}
    check(all(printed.values()),
          f"every line the end-of-run chip reads is one the harness still PRINTS ({printed})")
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
    # cannot be had from the pointer here)
    def painted(b, state, control=QStyle.CE_PushButton):
        opt = QStyleOptionButton()
        b.initStyleOption(opt)
        opt.state |= state
        img = QImage(b.size(), QImage.Format_ARGB32)
        img.fill(QColor(pal["surface"]))
        painter = QPainter(img)
        b.style().drawControl(control, opt, painter, b)
        painter.end()
        return img, opt

    # a hovered danger button: the CONTRAST of its painted ink on the fill it is
    # painted on, the measure with no tolerance to get wrong -- a count of pixels
    # near the right token gave the same number to the old ink, 7 away
    rb = win.run.reset_b
    img, _o = painted(rb, QStyle.State_MouseOver)
    fill = _count_near(img, pal["chip_crit_bg"], 6)
    ink = round(_best_contrast(img, pal["chip_crit_bg"]), 2)
    check(fill > 100 and ink >= orchtheme.TEXT_FLOOR,
          f"a hovered danger button paints an ink that clears {orchtheme.TEXT_FLOOR}:1 on its "
          f"hover fill ({fill} px fill, {ink}:1)")
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
    win.activateWindow()
    win.raise_()
    settle(5)
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
        n = _moved(win, tb, before_tab, win.grab().toImage(), tb.tabRect(tb.currentIndex()))
        check(tb.hasFocus() and n >= orchtheme.TAB_FOCUS_FLOOR,
              f"Tab from Launch lands on the tab strip, and the strip SHOWS it on the page "
              f"(a pixel of the tab moved {n}; the floor is {orchtheme.TAB_FOCUS_FLOOR})")
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
    if win.isActiveWindow() and sys.platform == "win32" and bar.maximum() > 0 and focus(en.tree):
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
        skip("the wheel in the active window", lost if not win.isActiveWindow()
             else "the page does not scroll at this size, or this is not Windows")
    # a popup keeps its own edge: a non-editable combo's (the profession pickers
    # -- Fusion's menu mode framed the view a second time, top and bottom, and
    # the list mode shows ten rows unless told the count), a Picker's, and the
    # completer's, each opened hidden with the focus a real one has
    win.tabs.setCurrentWidget(win.party)
    settle()
    popups = {}
    for tag, combo in (("profession", win.party.secondary), ("Picker", win.party.weapon)):
        holder = combo.view().window()
        holder.setAttribute(Qt.WA_DontShowOnScreen, True)
        combo.showPopup()
        settle(5)
        v = combo.view()
        img = holder.grab().toImage()
        rim = [img.pixelColor(x, y).name()
               for x, y in ((0, 0), (img.width() - 1, 0), (0, img.height() - 1),
                            (img.width() - 1, img.height() - 1), (img.width() // 2, 0),
                            (img.width() // 2, img.height() - 1))]
        popups[tag] = (v.hasFocus(), v.geometry() == holder.rect(),
                       all(_near(c, pal["border_strong"], 6) for c in rim),
                       not v.verticalScrollBar().isVisible() or combo.isEditable(),
                       f"{holder.width()}x{holder.height()} view {v.geometry().getRect()} "
                       f"rim {rim[0]}/{rim[4]}")
        combo.hidePopup()
        settle()
    pop = win.party.weapon.completer().popup()
    pop.setAttribute(Qt.WA_DontShowOnScreen, True)
    focus(win.party.weapon)                      # the popup's focus is its line edit's, by proxy
    win.party.weapon.completer().setCompletionPrefix("s")
    win.party.weapon.completer().complete()
    settle(5)
    img = pop.grab().toImage()
    rim = [img.pixelColor(x, y).name() for x, y in ((0, 0), (img.width() - 1, img.height() - 1))]
    popups["completer"] = (pop.hasFocus(), True, all(_near(c, pal["border_strong"], 6) for c in rim),
                           True, f"{pop.width()}x{pop.height()}")
    pop.hide()
    settle()
    if all(p[0] for p in popups.values()):
        check(all(p[1] and p[2] and p[3] for p in popups.values()),
              f"a focused popup is one box in the popup edge, the view filling it, its rows "
              f"unscrolled ({ {k: v[4] for k, v in popups.items()} })")
    else:
        skip("a focused popup is one box in the popup edge",
             f"a popup opened without focus ({ {k: v[0] for k, v in popups.items()} })")
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        settle()
        w = win.minimumSizeHint().width()
        check(w <= 1180, f"tab {win.tabs.tabText(i)!r}: nothing floors the window wider than "
                         f"1180 px ({w})")
    win.tabs.setCurrentIndex(0)
    settle()
    shot = os.path.join(out_dir, "smoke_screen.png")
    win.grab().save(shot)
    check(os.path.isfile(shot), f"screenshot {shot}")
    print(f"smoke: {len(fails)} failure(s)")
    return 1 if fails else 0


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
    grab("enemies_empty")
    win.enemies.from_spec(saved)
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
    if args.spec:
        win.from_spec(sandbox.load_spec(args.spec))
    else:
        win.from_spec(sandbox.example_spec())
    if args.smoke or args.snap:
        rc = smoke(win, app, args.smoke) if args.smoke else snap(win, app, args.snap, theme)
        QTimer.singleShot(0, app.quit)
        app.exec()
        return rc
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
