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
           hostile's template, weapon, bar and ranks on the right. The bar
           (SANDBOX-N1) is eight wells over an inline, filterable library
           -- the template's profession and the common skills by default,
           every profession on request, flagged and never refused, since
           the compiler accepts any skill on a hostile -- and each cell
           says the rank the server will ACT at; the ranks are one
           attribute to a row, each row a bar skill uses counting them
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
import math
import os
import re
import subprocess
import sys
import textwrap
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
import childjob       # noqa: E402  (toolkit/harness/childjob.py: Stop's tree kill)
import checks         # noqa: E402  (toolkit/checks.py: the smoke's verdict, floored)
import content        # noqa: E402
import vaultpath      # noqa: E402

try:
    from PySide6.QtCore import (QElapsedTimer, QEvent, QMimeData, QPoint, QPointF, QProcess,
                                QProcessEnvironment, QRect, Qt, QTimer, Signal)
    from PySide6.QtGui import (QCloseEvent, QColor, QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent,
                               QDropEvent, QEnterEvent, QFont, QFontMetrics, QFontMetricsF, QIcon,
                               QImage, QKeyEvent, QMouseEvent, QPainter, QTextCharFormat,
                               QTextCursor, QWheelEvent)
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
from orchui import (ROLE_FULL, ROLE_ID, ROLE_PARTS, ROLE_ROSTER, ROLE_SLOT, button,  # noqa: E402
                    caption, card, chip, overline, role_label, set_chip)


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

class _Completer(QCompleter):
    """The Picker's type-to-filter. It matches on ROLE_FULL -- a row's label
    whole, where the shown one is elided (template_label) -- so a word from
    the middle of a long name finds its row after the ellipsis has taken it
    off the surface; and it completes with the SHOWN text, since pathFromIndex
    is what the completer puts in the line edit and emits as activated(str).
    Qt's own returns the match role's text, which would leave the field
    holding a label wider than any row it offers."""

    def pathFromIndex(self, index):
        return str(index.data(Qt.EditRole) or "")


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
        comp = _Completer(self.model(), self)
        comp.setCompletionRole(ROLE_FULL)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(comp)
        comp.popup().setProperty("role", "popup")
        self.tips = {}
        self.currentIndexChanged.connect(self._show_start)

    def _show_start(self, *_a):
        le = self.lineEdit()
        if le is not None:
            le.setCursorPosition(0)
        self.setToolTip(self.tips.get(self.currentData(), self.currentText()))

    def set_choices(self, pairs, keep=None, tips=None, full=None):
        """pairs: [(label, value)]. Keeps the current value when it is still
        offered. `tips` gives each its hover; `full` ({value: the label
        whole}) is what the type-to-filter matches where the shown label is
        elided, and the row's own hover there. (A `parts` argument once drew
        the rows with SkillDelegate for the skill Pickers; the Skill bar's
        strip replaced them, SANDBOX-N1, and no caller passed it since.)"""
        current = keep if keep is not None else self.value()
        self.blockSignals(True)
        self.clear()
        for label, value in pairs:
            self.addItem(label, value)
            i = self.count() - 1
            whole = (full or {}).get(value, label)
            self.setItemData(i, whole, ROLE_FULL)
            if whole != label:
                self.setItemData(i, whole, Qt.ToolTipRole)
        self.blockSignals(False)
        self.tips = dict(tips or {})
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


class SkillBar(QWidget):
    """A hostile's eight skill slots as a strip of wells over an inline,
    filterable library (SANDBOX-N1, the owner's ask: "a better/filterable
    skill/attribute selector"). The model is `ids`, eight ints in slot
    order, 0 for empty; the strip and the library are views of it, and
    EVERY write goes through set_slot / swap / set_values / untick, each
    emitting `changed` exactly once and re-syncing the cells, the library's
    checks and the chip. A filter, the offered-set combo or the checkbox
    never emits: a view of the same spec (the Skills tab's law).

    THE RANGE IS THE COMPILER'S. validate never checks a hostile's skills
    against its profession, so the library offers the template's profession
    plus the common skills BY DEFAULT and every other profession on request,
    flagged and never refused; and a file is HELD VERBATIM -- an id of another
    profession, an id the table lacks, a duplicate, a 0 (an empty slot, held
    in place and dropped on save) -- where the eight Pickers this replaces
    landed on '(empty)' in silence with the bar saying 'Opened X' alone (the
    same false word the level and rank lifts removed). A ninth id is the
    compiler's to refuse (validate, the bar is 8 wide), so Open says so. The
    one-copy rule governs the window's own writes only.

    WHAT A CELL SAYS is the rank the server will ACT AT
    (sandbox.effective_rank, the mirror of the area create path's fallback +
    authsrv.agent_skill_rank): a hostile with no ranks casts every skill at
    12 (a stand-in, OURS); with any rank set, an attribute its ranks omit --
    another profession's included, which its ranks can never hold -- acts at
    0. Rank Hammer Mastery and forget Strength, and Power Attack drops from
    12 to 0: the cell says so at once, the Attributes row chip too. A skill
    with NO attribute whose numbers still vary (sandbox.skill_varies: Light of
    Deldrimor, 55..80) is scaled by the same rule at the no-attribute id --
    0 with any rank set, 12 with none -- and its cell says that rank; only a
    row with nothing varying says nothing scales.

    The chip (the card's trailing NOTICE), Clear slot (beside it in the
    card's head, so the filter row keeps its search box wide enough for a
    typed query at 1,000 px: measured 2026-09-24, 122 px with the button in
    the row against the ~135 a 12-character query needs, 234 without) and
    the hint (the caption under the library) are housed HERE from birth:
    shown with no parent, a label is a window of its own (the Ranks trap,
    twice over)."""

    changed = Signal()                          # a slot written (never a filter)
    ROWS = 6                                    # the library's visible rows

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        self.world = names.world
        self.ids = [0] * sandbox.BAR_SLOTS
        self.professions = ()
        self.ranks_pairs = []
        self.template_pairs = []
        self._every = sorted(int(k) for k in self.world.rows("skills"))
        self.has_table = sandbox.has_skill_table(self.world)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        # housed from birth (a card's `trailing` re-homes both in its own header)
        self.chip = chip("", "info")
        self.chip.setParent(self)
        self.clear_b = button("Clear slot", "quiet", tip="Empty the selected slot.")
        self.clear_b.setParent(self)
        self.clear_b.clicked.connect(lambda: self.clear_slot(self.current_slot()))

        self.strip = orchui.SlotStrip()
        self.strip.setItemDelegate(orchui.SlotDelegate(self.strip))
        self.strip.on_drop = self._dropped
        self.strip.installEventFilter(self)
        self.strip.currentRowChanged.connect(self._selection)
        outer.addWidget(self.strip)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.filter = QLineEdit()
        # the placeholder 'Find a skill' whole (72 px); a typed query's room
        # comes from Clear slot living in the card's head, not this row
        self.filter.setMinimumWidth(96)
        self.filter.setPlaceholderText("Find a skill")
        self.filter.setToolTip("Matches a skill's name, id, profession abbreviation (W, Mo …) or "
                               "attribute, or its grade in the pills' words (modelled, label). "
                               "Return puts the first shown skill on the bar; Down moves to the "
                               "list; Escape clears.")
        self.filter.setClearButtonEnabled(True)
        self.filter.addAction(orchui.tinted_icon("search"), QLineEdit.LeadingPosition)
        self.filter.setAccessibleName("Find a skill for the bar")
        self.filter.setMaximumWidth(480)
        self.filter.installEventFilter(self)
        self.prof = QComboBox()
        self.prof.setAccessibleName("Skills offered")
        self.prof.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.prof.setMinimumContentsLength(14)
        self.prof.addItem("Common", -2)
        self.prof.addItem("Every profession", 0)
        for pid, name in sandbox.PROFESSIONS.items():
            self.prof.addItem(f"{name} ({sandbox.ABBREV[pid]})", pid)
        self.prof.addItem("Common (no profession)", -1)
        self.prof.setMaxVisibleItems(self.prof.count())    # every row, none scrolled (the census)
        # a plain combo CLIPS a text wider than its field, with no ellipsis
        # (the first cut showed 'Warrior and common' with its tail cut, in
        # --snap): sized to the widest label row 0 can ever carry
        self.prof.ensurePolished()
        fm = self.prof.fontMetrics()
        widest = max(fm.horizontalAdvance(self.row0_label(p)) for p in list(sandbox.PROFESSIONS) + [0])
        widest = max(widest, max(fm.horizontalAdvance(self.prof.itemText(i))
                                 for i in range(self.prof.count())))
        self.prof.setMinimumWidth(widest + 44)          # the field's padding and the arrow
        self.prof.setToolTip("Which skills the list offers: the template's profession and the "
                            "common skills, or every profession, or one. The compiler accepts any "
                            "skill on a hostile; its ranks must be its template's profession's, so "
                            "a skill in another profession's attribute acts at rank 0 once any "
                            "rank is set, at 12 with none (one with no attribute loses nothing).")
        # named with the pills' own two words, as the Skills tab's; TICKED here:
        # eight slots, and a skill this server does nothing with is a wasted one
        self.acts = QCheckBox("Modelled or label")
        self.acts.setChecked(True)
        self.acts.setToolTip("Only the skills this server acts: a hand-verified row (modelled) or "
                             "a parsed label (label). Untick to see every skill offered.")
        row.addWidget(self.filter, 1)
        row.addWidget(self.prof, 0)
        row.addWidget(self.acts)
        row.addStretch(0)
        outer.addLayout(row)

        self.list = orchui.SkillLibrary("No skill matches this filter.")
        self.delegate = orchui.SkillDelegate(self.list)
        self.list.setItemDelegate(self.delegate)
        self.list.setUniformItemSizes(True)
        self.list.setAccessibleName("Skills to slot")
        self.list.on_clear = self.clear_slot
        self.list.strip_token = self.strip.token    # only THIS strip's cells clear a slot here
        self.list.installEventFilter(self)          # Return / Enter on a row toggles it
        self.list.itemChanged.connect(self._box_moved)
        self.list.itemDoubleClicked.connect(self._double)
        # the pill column set ONCE from every skill's parts, so it never jumps
        # between templates or filters
        self.delegate.column = self._pill_column()
        fm = self.list.fontMetrics()
        self.list.setFixedHeight(self.ROWS * (fm.height() + orchui.SkillDelegate.PAD_V)
                                 + 2 * self.list.frameWidth() + 2)
        outer.addWidget(self.list)
        self.hint = caption("Tick or double-click a skill to fill the selected slot, or the first "
                            "empty one; drag to place or reorder.")
        outer.addWidget(self.hint)
        if not self.has_table:
            self.list.placeholder = "No skill table, so skills cannot be picked here."
            self.list.setToolTip("vault/content/skills.toml is missing.")
            for w in (self.filter, self.prof, self.acts):
                w.setEnabled(False)
        self.filter.textChanged.connect(self._filter)
        self.prof.currentIndexChanged.connect(self._populate)
        self.acts.toggled.connect(self._filter)
        self.strip.setCurrentRow(0)
        self._populate()
        self._sync()

    def _pill_column(self):
        cache = getattr(self.names, "_pill_column", None)
        if cache is None:
            self.delegate.set_column(self.names.skill_parts(s) for s in self._every)
            cache = self.names._pill_column = self.delegate.column
        return cache

    # ---- the model, and the ONE write path

    def values(self):
        return list(self.ids)

    def current_slot(self):
        return max(0, self.strip.currentRow())

    def select_slot(self, i):
        self.strip.setCurrentRow(int(i))

    def set_values(self, ids):
        """A load: HELD VERBATIM -- an off-profession id, an unknown id, a
        duplicate -- padded to eight; the one-copy rule is for the window's
        own writes. Emits once when anything moved."""
        want = [int(s) for s in (ids or [])][:sandbox.BAR_SLOTS]
        want += [0] * (sandbox.BAR_SLOTS - len(want))
        if want != self.ids:
            self.ids = want
            self._wrote()

    def set_slot(self, i, sid):
        """Slot `i` takes `sid` (0 clears), replacing what it held; a skill
        already on the bar elsewhere MOVES (its old slot empties: one copy for
        the window's own writes). No change, no signal."""
        i, sid = int(i), int(sid)
        if self.ids[i] == sid:
            return
        if sid:
            for j, other in enumerate(self.ids):
                if other == sid and j != i:
                    self.ids[j] = 0
        self.ids[i] = sid
        self._wrote()

    def clear_slot(self, i):
        self.set_slot(i, 0)

    def swap(self, i, j):
        i, j = int(i), int(j)
        if i == j or self.ids[i] == self.ids[j]:
            return
        self.ids[i], self.ids[j] = self.ids[j], self.ids[i]
        self._wrote()

    def tick(self, sid):
        """The library's tick: already on the bar -> nothing; else the selected
        slot if empty, else the first empty, else (bar full) the selected slot
        REPLACED; then the selection moves to the next empty slot after it."""
        sid = int(sid)
        if not sid or sid in self.ids:
            self._sync_checks()
            return
        cur = self.current_slot()
        empties = [i for i, s in enumerate(self.ids) if not s]
        target = cur if not self.ids[cur] else (empties[0] if empties else cur)
        self.set_slot(target, sid)
        after = [i for i in list(range(target + 1, sandbox.BAR_SLOTS)) + list(range(0, target))
                 if not self.ids[i]]
        if after:
            self.select_slot(after[0])

    def untick(self, sid):
        """Clears EVERY slot holding `sid` (a file may carry a duplicate)."""
        sid = int(sid)
        if sid not in self.ids:
            self._sync_checks()
            return
        self.ids = [0 if s == sid else s for s in self.ids]
        self._wrote()

    def _wrote(self):
        self._sync()
        self.changed.emit()

    # ---- what the template gives: the offered set, the ranks in view

    def set_professions(self, professions):
        """A template change: the bar's ids are KEPT (they may now be another
        profession's: the chip warns, the cells say so, a Delete each removes
        them), combo row 0 is relabelled and re-selected, the search cleared,
        the checkbox kept, the library repopulated. Never emits."""
        self.professions = tuple(int(p) for p in professions if p)
        prof0 = self.professions[0] if self.professions else 0
        self.prof.blockSignals(True)
        self.prof.setItemText(0, self.row0_label(prof0))
        # a template with no profession the table knows (five profession-11
        # bodies) offers the common skills on row 0 already, so the last row,
        # 'Common (no profession)', would offer the same 59 twice: it comes
        # off while row 0 stands for it, and back with a known profession
        last = self.prof.count() - 1
        if sandbox.PROFESSIONS.get(prof0) is None and self.prof.itemData(last) == -1:
            self.prof.removeItem(last)
        elif sandbox.PROFESSIONS.get(prof0) is not None and self.prof.itemData(last) != -1:
            self.prof.addItem("Common (no profession)", -1)
        self.prof.setMaxVisibleItems(self.prof.count())
        self.prof.setCurrentIndex(0)
        self.prof.blockSignals(False)
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.blockSignals(False)
        self._populate()
        self._sync()

    @staticmethod
    def row0_label(prof):
        """Combo row 0, the template's profession and the common skills:
        'Warrior and common'; a template with no profession (or one the table
        lacks) offers the common skills alone, and then the 'Common (no
        profession)' row is dropped (set_professions) rather than offered
        twice."""
        name = sandbox.PROFESSIONS.get(int(prof or 0))
        return f"{name} and common" if name else "Common"

    def set_ranks_view(self, pairs, template_pairs=None):
        """The ranks each cell's line 2 reads (the member's; the template's as
        the fallback, as the server reads them). Never emits."""
        self.ranks_pairs = [[int(a), int(r)] for a, r in (pairs or [])]
        if template_pairs is not None:
            self.template_pairs = list(template_pairs or [])
        self._sync_cells()

    def off_profession(self, sid):
        """A skill of neither the template's profession nor common: its
        attribute is one this hostile's ranks can never hold."""
        if not sid or sandbox.skill_row(self.world, sid) is None:
            return False
        return self.names.skill_profession(sid) not in set(self.professions) | {0}

    def _offered(self):
        sel = int(self.prof.currentData() if self.prof.currentData() is not None else -2)
        prof = self.names.skill_profession
        if sel == -2:
            want = set(self.professions) | {0}
            return [s for s in self._every if prof(s) in want]
        if sel == 0:
            return list(self._every)
        if sel == -1:
            return [s for s in self._every if prof(s) == 0]
        return [s for s in self._every if prof(s) == sel]

    def _items(self):
        return [self.list.item(i) for i in range(self.list.count())]

    def _populate(self, *_a):
        """The library for the offered set, sorted as the Skills tab sorts;
        ~200 rows for a profession and common, every one (1,333) only when
        chosen. Check states follow the bar; nothing emits."""
        self.list.blockSignals(True)
        try:
            self.list.clear()
            on = set(self.ids)
            for sid in sorted(self._offered(), key=lambda s: self.names.slot_label(s).lower()):
                it = QListWidgetItem(self.names.slot_label(sid))
                it.setData(ROLE_ID, sid)
                it.setData(ROLE_PARTS, self.names.skill_parts(sid))
                it.setToolTip(self.names.skill_tip(sid))
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                it.setCheckState(Qt.Checked if sid in on else Qt.Unchecked)
                self.list.addItem(it)
        finally:
            self.list.blockSignals(False)
        self._filter()

    def _filter(self, *_a):
        text = self.filter.text().lower()
        only = self.acts.isChecked()
        acting = self.names.modelled | self.names.labelled
        matching = 0
        for it in self._items():
            sid = int(it.data(ROLE_ID))
            hit = not text or text in it.text().lower()
            matching += hit
            it.setHidden(not hit or (only and sid not in acting))
        if self.has_table:
            if only and matching and not self.list.visible_count():
                self.list.placeholder = self.untick_sentence(matching)
            else:
                self.list.placeholder = "No skill matches this filter."
        self.list.viewport().update()

    @staticmethod
    def untick_sentence(matching):
        """The placeholder's way out when the box hides every match: 'to see
        it' for one, 'to see all N' for more (never 'all 1')."""
        return (f"No acting skill matches; untick Modelled or label to see "
                f"{'it' if matching == 1 else f'all {matching}'}.")

    def visible_ids(self):
        return [int(it.data(ROLE_ID)) for it in self._items() if not it.isHidden()]

    # ---- the views, re-derived from the model

    def _sync(self):
        self._sync_cells()
        self._sync_checks()
        self._chip()
        self._selection()

    def _sync_checks(self):
        on = set(self.ids)
        self.list.blockSignals(True)
        try:
            for it in self._items():
                want = Qt.Checked if int(it.data(ROLE_ID)) in on else Qt.Unchecked
                if it.checkState() != want:
                    it.setCheckState(want)
        finally:
            self.list.blockSignals(False)
        self.list.viewport().update()

    def rank_line(self, sid):
        """(line 2, its hover sentence, the off-profession abbreviation or '')
        for a slotted skill: the attribute and the rank it ACTS at."""
        row = sandbox.skill_row(self.world, sid)
        if row is None:
            return f"{sid}  -", "Not in the skill table; the compiler passes the id through.", ""
        sp = self.names.skill_profession(sid)
        off = self.off_profession(sid)
        abbr = sandbox.ABBREV.get(sp, "-") if off else ""
        head = f"{abbr} · " if off else ""
        attr = sandbox.skill_attribute(self.world, sid)
        ranked = bool(self.ranks_pairs or self.template_pairs)
        if attr is None:
            if not sandbox.skill_varies(self.world, sid):
                return head + "No attribute", "No attribute: nothing about it scales with a rank.", abbr
            # no attribute, but its numbers move with a rank: the server
            # scales it by the same rule at the no-attribute id -- 0 while
            # any rank is set, 12 with none (Light of Deldrimor: 55 or 75)
            rank = sandbox.effective_rank(self.ranks_pairs, self.template_pairs, sandbox.NO_ATTRIBUTE)
            tip = (f"No attribute, but its numbers vary with a rank, and the server scales it at "
                   f"{rank}: " + ("0 while any rank is set on this hostile or its template"
                                  if ranked else
                                  f"{sandbox.UNRANKED_SKILL_RANK} with no rank set anywhere, this "
                                  f"server's stand-in for a foe's ranks") + ".")
            return head + f"No attribute {rank}", tip, abbr
        rank = sandbox.effective_rank(self.ranks_pairs, self.template_pairs, attr)
        label = self.names.attr_label(attr)
        if off:
            tip = (f"{label} is a {sandbox.PROFESSIONS.get(sp, 'profession-' + str(sp))} attribute "
                   f"this hostile's ranks cannot hold: acts at {rank} "
                   + ("while any rank is set." if ranked
                      else f"with no rank set ({sandbox.UNRANKED_SKILL_RANK}, this server's "
                           f"stand-in for a foe's ranks)."))
        elif not ranked:
            tip = (f"No rank set on this hostile or its template: acts at "
                   f"{sandbox.UNRANKED_SKILL_RANK}, this server's stand-in for a foe's ranks.")
        elif not self.ranks_pairs:
            tip = f"{label} {rank} on this hostile, its template's own rank."
        else:
            tip = f"{label} {rank} on this hostile."
        return head + f"{label} {rank}", tip, abbr

    def _sync_cells(self):
        for i, sid in enumerate(self.ids):
            it = self.strip.item(i)
            if not sid:
                it.setData(ROLE_ID, 0)
                it.setData(ROLE_PARTS, None)
                it.setData(ROLE_SLOT, (i, "", ""))
                it.setText(f"Slot {i + 1}: empty")
                it.setToolTip("An empty slot.")
                continue
            parts = self.names.skill_parts(sid)
            line2, why, abbr = self.rank_line(sid)
            it.setData(ROLE_ID, sid)
            it.setData(ROLE_PARTS, parts)
            it.setData(ROLE_SLOT, (i, line2, abbr))
            it.setText(f"Slot {i + 1}: {self.names.slot_label(sid)}, {line2}")
            known = sandbox.skill_row(self.world, sid) is not None
            it.setToolTip((self.names.skill_tip(sid) if known else f"Skill {sid}") + "\n" + why)
        self.strip.viewport().update()

    def _chip(self):
        """'N of 8 slots'; WARN with '· K of another profession' and/or '· J
        not in the skill table' after it. The hover's cost sentence is
        conditional on the skills that CARRY an attribute -- 102 profession
        skills have none, and for those nothing is lost (the verifier's c5)."""
        n = sum(1 for s in self.ids if s)
        off = [s for s in self.ids if self.off_profession(s)]
        unknown = sum(1 for s in self.ids if s and sandbox.skill_row(self.world, s) is None)
        text = f"{n} of {sandbox.BAR_SLOTS} slots"
        if off or unknown:
            parts, tips = [text], []
            if off:
                parts.append(f"{len(off)} of another profession")
                with_attr = [s for s in off if sandbox.skill_attribute(self.world, s) is not None]
                if with_attr:
                    tips.append(f"A skill of another profession in that profession's attribute "
                                f"({len(with_attr)} of {len(off)} here): one this hostile's ranks "
                                f"cannot hold (the compiler refuses the rank), so it acts at rank 0 "
                                f"while any rank is set, at 12 with none.")
                else:
                    tips.append("A skill of another profession with no attribute: nothing about it "
                                "scales with a rank this hostile could hold, so no rank is lost.")
                tips.append("The compiler accepts the skill.")
            if unknown:
                parts.append(f"{unknown} not in the skill table")
                tips.append(f"{n_of(unknown, 'id')} the skill table lacks: the compiler passes "
                            f"{'it' if unknown == 1 else 'them'} through unexamined, and the "
                            f"gamesrv would try to cast {'it' if unknown == 1 else 'each'}.")
            set_chip(self.chip, "  ·  ".join(parts), "warn", tip=" ".join(tips))
        else:
            set_chip(self.chip, text, "info",
                     tip="Up to eight skills, in slot order; a hostile with none only swings.")

    def _selection(self, *_a):
        self.clear_b.setEnabled(bool(self.ids[self.current_slot()]))
        self.strip.viewport().update()

    # ---- the library's own paths, and a drop

    def _box_moved(self, it):
        sid = int(it.data(ROLE_ID))
        if it.checkState() == Qt.Checked:
            self.tick(sid)
        else:
            self.untick(sid)

    def _double(self, it):
        at = getattr(self.list, "dbl_at", None)
        if at is not None and self.list.check_rect(it).contains(at):
            return                              # Qt's own toggle on the box; not a second one
        self._toggle(it)

    def _dropped(self, slot, sid, from_slot):
        # from_slot is THIS strip's (parse_skill_mime keeps it only under the
        # strip's own token and inside 0..7); anything else is a place of sid
        if from_slot is not None and 0 <= int(from_slot) < sandbox.BAR_SLOTS:
            self.swap(from_slot, slot)          # a cell onto another cell
        else:
            self.set_slot(slot, sid)            # a library row (or another window's cell): placed, or MOVED

    def _tick_first_shown(self):
        for it in self._items():
            if not it.isHidden() and it.checkState() != Qt.Checked:
                self.tick(int(it.data(ROLE_ID)))
                return True
        return False

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress:
            key, mods = ev.key(), ev.modifiers()
            if obj is self.filter:
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self._tick_first_shown()
                    return True
                if key == Qt.Key_Escape:
                    self.filter.clear()
                    return True
                if key == Qt.Key_Down:
                    first = next((it for it in self._items() if not it.isHidden()), None)
                    if first is not None:
                        self.list.setCurrentItem(first)
                        self.list.setFocus(Qt.TabFocusReason)
                    return True
            elif obj is self.strip:
                cur = self.current_slot()
                if Qt.Key_1 <= key <= Qt.Key_8 and not mods & (Qt.ControlModifier | Qt.AltModifier):
                    self.select_slot(key - Qt.Key_1)
                    return True
                if key in (Qt.Key_Delete, Qt.Key_Backspace):
                    self.clear_slot(cur)
                    return True
                if key in (Qt.Key_Left, Qt.Key_Right) and mods & Qt.ControlModifier:
                    to = cur + (1 if key == Qt.Key_Right else -1)
                    if 0 <= to < sandbox.BAR_SLOTS:
                        self.swap(cur, to)
                        self.select_slot(to)
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    self.filter.setFocus(Qt.TabFocusReason)
                    return True
            elif obj is self.list and key in (Qt.Key_Return, Qt.Key_Enter):
                # DESIGN s2: Space AND Return toggle a focused row (Qt gives
                # Return to `activated` and ticks nothing; the verifier's a5)
                it = self.list.currentItem()
                if it is not None and not it.isHidden():
                    self._toggle(it)
                return True
        return super().eventFilter(obj, ev)

    def _toggle(self, it):
        sid = int(it.data(ROLE_ID))
        if sid in self.ids:
            self.untick(sid)
        else:
            self.tick(sid)


class Ranks(QWidget):
    """One spin box per attribute of the given professions, ONE to a row --
    the label column fixed from the widest attribute label over EVERY
    profession, measured once at build, so the spins stand at one x for every
    template and Tab order is reading order -- with a ROW CHIP on each row a
    bar skill uses ('N on the bar'; WARN 'N on the bar, at rank 0' while its
    rank is 0 and any rank is set, since the server acts it at 0; 'N on the
    bar, acting at 12' with no rank anywhere, member or template: the
    stand-in). set_bar(ids) recounts and never emits `changed` (a count, not
    an edit). And the points spent as a chip (the Enemies tab's; the party's
    ranks are in-game). A hostile is EXEMPT from a player's point budget -- the owner's
    ruling, 2026-09-24 (PLAN-LOG): retail foes and bosses exceed it -- so the
    chip counts and never judges (never crit, never 'over budget'), and the
    compiler holds a hostile's ranks to validity alone: each rank
    0..sandbox.HOSTILE_RANK_MAX (the spin's own range; 21, retail's ceiling,
    the owner's second ruling of the day lifting the caps for hostiles) in the
    template's profession (the only attributes offered). The cost table stops
    at 12 (its 13th row is the client's cap sentinel), so the chip prices the
    ranks to 12 and says how many stand past it, unpriced -- a figure past 12
    has no source, and attribspend saturates there in silence. The chip is
    the NOTICE; `hint`, a caption under the grid, stays the HINT, the
    sentence saying what is and is not checked.
    Ranks lays the hint out ITSELF, under the grid set_professions wipes:
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
        self.row_chips = {}                     # aid -> the 'N on the bar' chip (SANDBOX-N1)
        self.counts = {}                        # aid -> bar skills using it
        self.bar_ids = []
        self.template_pairs = []                # the template's own ranks, the server's fallback
        # housed HERE from birth (a card's `trailing` re-homes it in its own
        # header): set_professions shows it, and shown with no parent it would
        # be a window of its own -- the hint's trap, one widget over
        self.chip = chip("", "info")
        self.chip.setParent(self)
        self.label = self.chip
        self.hint = caption("")
        outer.addWidget(self.hint)
        self.professions = ()
        self.label_col = self._label_column()

    def _clear(self):
        """Hidden BEFORE it is un-parented: a widget the grid queued a show
        for (addWidget on a visible Ranks) and that a second set_professions
        in the same turn un-parents first is shown by that queued call as a
        window of its own -- ten on the desktop, one per label and spin, with
        the keyboard focus in one of them (--smoke's long-name law found it:
        a visible editor's from_spec to a different template runs
        set_professions twice in one turn). hide() sets the explicit flag the
        queued show respects; setParent(None) alone does not."""
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _label_text(self, aid, primary):
        return self.names.attr_label(aid) + (
            f'  <span style="color:{orchui.PAL["muted"]}">primary</span>' if primary else "")

    def _label_column(self):
        """The widest attribute label over EVERY profession, in the label's own
        font: one column width for every template, so the spins never move
        between a Ranger's and a Warrior's."""
        if self.rules is None:
            return 0
        probe = QLabel(self)
        widest = 0
        for aid, row in self.rules.attributes.items():
            probe.setText(self._label_text(aid, row["is_primary"]))
            widest = max(widest, probe.sizeHint().width())
        probe.hide()
        probe.deleteLater()
        return widest

    def set_professions(self, professions, template_pairs=None):
        keep = self.ranks()
        self._clear()
        self.spins = {}
        self.row_chips = {}
        self.professions = tuple(int(p) for p in professions if p)
        if template_pairs is not None:
            self.template_pairs = list(template_pairs or [])
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
            sp.setRange(0, sandbox.HOSTILE_RANK_MAX)     # NOT the table's 12: the compiler's cap
            sp.setValue(dict(keep).get(aid, 0))
            sp.setFixedWidth(92)
            sp.valueChanged.connect(self._spent)
            sp.valueChanged.connect(lambda _v: self.changed.emit())
            name = self.names.attr_label(aid)
            lab = QLabel(self._label_text(aid, row["is_primary"]))
            lab.setToolTip(f"Attribute {aid}" + (" — the primary's own attribute"
                                                 if row["is_primary"] else ""))
            lab.setBuddy(sp)
            sp.setAccessibleName(name)
            # the row chip: hidden EXPLICITLY before the grid takes it, so the
            # grid's queued show (addWidget on a visible Ranks) leaves it be;
            # set_bar shows the rows a bar skill uses
            rc = chip("", "info")
            rc.hide()
            self.grid.addWidget(lab, n, 0)
            self.grid.addWidget(sp, n, 1)
            self.grid.addWidget(rc, n, 2, Qt.AlignLeft | Qt.AlignVCenter)
            self.spins[aid] = sp
            self.row_chips[aid] = rc
            n += 1
        if not n:
            self.grid.addWidget(caption("This template's profession has no spendable "
                                        "attributes."), 0, 0, 1, 4)
        self.grid.setColumnMinimumWidth(0, self.label_col)
        self.grid.setColumnStretch(3, 1)
        self._spent()

    def set_bar(self, ids):
        """The bar's ids (MemberEditor wires bar.changed here): recounts the
        row chips. Never emits -- a count, not an edit."""
        self.bar_ids = [int(s) for s in (ids or []) if s]
        self.counts = {}
        for sid in self.bar_ids:
            a = sandbox.skill_attribute(self.names.world, sid)
            if a is not None:
                self.counts[a] = self.counts.get(a, 0) + 1
        self._row_chips()

    def effective(self, aid):
        """The rank a skill in `aid` acts at on this hostile: the spins' if any
        is set, else the template's own, else the stand-in (sandbox.effective_rank)."""
        return sandbox.effective_rank(self.ranks(), self.template_pairs, aid)

    def _row_chips(self):
        ranked = bool(self.ranks() or self.template_pairs)
        for aid, rc in self.row_chips.items():
            n = self.counts.get(aid, 0)
            if not n:
                rc.hide()
                continue
            using = ", ".join(self.names.skill_parts(s)[0] for s in self.bar_ids
                              if sandbox.skill_attribute(self.names.world, s) == aid)
            label, rank = self.names.attr_label(aid), self.effective(aid)
            if not ranked:
                set_chip(rc, f"{n} on the bar, acting at {sandbox.UNRANKED_SKILL_RANK}", "info",
                         tip=f"No rank set on this hostile or its template, so every skill acts "
                             f"at {sandbox.UNRANKED_SKILL_RANK}, this server's stand-in for a "
                             f"foe's ranks: {using}.")
            elif rank == 0:
                set_chip(rc, f"{n} on the bar, at rank 0", "warn",
                         tip=f"{label} is 0 while another rank is set, so the server acts these "
                             f"at rank 0: {using}.")
            else:
                set_chip(rc, f"{n} on the bar", "info",
                         tip=f"{label} {rank}"
                             + (" (the template's own rank)" if not self.ranks() else "")
                             + f": {using}.")
            rc.show()

    def spend(self):
        """(points, past): what the ranks cost by the table, and how many of
        them stand past its last row (rules.rank_max, 12). The table has no
        row past 12 -- attribspend.spent_on adds only the ranks it holds, so
        12, 15 and 21 all price at 97 -- and a figure past it has no source:
        the count is the true part, and it is said as a count. Neither is a
        verdict."""
        vals = {a: s.value() for a, s in self.spins.items()}
        return (self.rules.total_spent(vals),
                sum(1 for v in vals.values() if v > self.rules.rank_max))

    def spent(self):
        """The points the ranks cost, by the table (to its last row) -- a
        count, not a verdict."""
        return self.spend()[0]

    def spent_text(self):
        """The chip's words, and the roster line's: 'N points' while every
        rank is in the table; past it, 'N points to 12; K ranks past it, not
        priced' -- never a number the table did not give."""
        pts, past = self.spend()
        if not past:
            return n_of(pts, "point")
        return (f"{n_of(pts, 'point')} to {self.rules.rank_max}; {n_of(past, 'rank')} past it, "
                f"not priced")

    def _spent(self):
        if self.rules is None:
            return
        self.hint.setText(f"Not held to a player's point budget; each rank "
                          f"0..{sandbox.HOSTILE_RANK_MAX}, in the template's profession.")
        self.hint.setToolTip(f"A hostile is exempt from the attribute points a level grants a "
                             f"player (the owner's ruling, 2026-09-24): retail foes and bosses "
                             f"exceed them, and its ranks reach retail's own ceiling "
                             f"({sandbox.HOSTILE_RANK_MAX}: foes' attributes up to 20, one more "
                             f"from skills).\nThe compiler still refuses a rank past "
                             f"{sandbox.HOSTILE_RANK_MAX} and an attribute of another "
                             f"profession, neither of which this card can hold.")
        set_chip(self.chip, self.spent_text(), "info",
                 tip=f"What these ranks would cost a player, by the attribute table. The table "
                     f"stops at {self.rules.rank_max} (its next row is the client's cap "
                     f"sentinel), so a rank past {self.rules.rank_max} is priced to "
                     f"{self.rules.rank_max} and counted as past it.")
        self._row_chips()                       # a rank edit changes what a row chip says

    def ranks(self):
        return [[a, s.value()] for a, s in self.spins.items() if s.value()]

    def set_ranks(self, pairs):
        for a, r in pairs or []:
            if int(a) in self.spins:
                self.spins[int(a)].setValue(int(r))
        self._spent()


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


# The most a template's label may measure, px in the picker's own font. Content
# is the operator's and a row may carry any name (desk-hench put three 60-
# character descriptions in content/npcs.toml; a mod row may carry 200), and
# every width this window derives from its labels -- the heroes table's Body
# column, the stack edge under it, the hostile page's 740 px edge -- would
# follow the longest one: those three stacked the Character card at 1,280 px
# and cut two Template rows mid-glyph. So the label is bounded and the widths
# stay derived. The budget is the widest label the fields were fitted to
# before those rows landed (4e93a581): 'def_2037  [Mo L10]  (unwatched)', 202
# px in Segoe UI at 14 px, the window's font -- so no label that fitted then is
# elided now, and the Body column, the 1,140 px stack edge and the 1,000 /
# 1,120 / 1,280 px layouts are where they were. A label over it shows its name
# elided ("…"), its tag whole (the fact the operator picks by), the label whole
# on hover and in the type-to-filter (ROLE_FULL).
TEMPLATE_LABEL_PX = 202


def template_label(name, key, prof, level, fm=None):
    """(shown, whole) for one template row: 'name  [ABBR Ln]', '  (unwatched)'
    after it for a row with no name (the key stands in). `fm`, the picker's
    QFontMetrics, bounds the shown label to TEMPLATE_LABEL_PX -- the name
    elided, the tag kept; None leaves it whole (a caller with no widget)."""
    tag = f"  [{sandbox.ABBREV.get(prof, '-')} L{level}]" + ("" if name else "  (unwatched)")
    head = name or key
    whole = head + tag
    if fm is None or fm.horizontalAdvance(whole) <= TEMPLATE_LABEL_PX:
        return whole, whole
    room = TEMPLATE_LABEL_PX - fm.horizontalAdvance(tag)
    shown = fm.elidedText(head, Qt.ElideRight, room) + tag
    while room > 0 and fm.horizontalAdvance(shown) > TEMPLATE_LABEL_PX:   # kerning over the join
        room -= 1
        shown = fm.elidedText(head, Qt.ElideRight, room) + tag
    return shown, whole


def template_choices(world, fm=None, bodies_only=True):
    """([(shown label, key)] sorted, {key: the label whole}) -- the pairs a
    Picker offers and the `full` (and `tips`) it takes with them."""
    pairs, full = [], {}
    for key, name, prof, level, has_body in sandbox.templates(world):
        if bodies_only and not has_body:
            continue
        shown, whole = template_label(name, key, prof, level, fm)
        pairs.append((shown, key))
        full[key] = whole
    pairs.sort(key=lambda p: (not p[0][0].isupper(), p[0].lower()))
    return pairs, full


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
    # by side, 11 of 39 names elided; the widest name in the table's font
    # against the text inset alone gave 1,130 and left 'Master of Whisp…' on
    # screen to 1,136 -- the cell paints the name DemiBold when its row is
    # unlocked, at a fractional advance, inside the delegate's own margins).
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
        bodies = full = None
        for idx, _nid in cat:
            r = self.table.rowCount()
            self.table.insertRow(r)
            hero = names.hero_name(idx)
            chk = QCheckBox()
            chk.setAccessibleName(f"Add {hero} to the party")
            prof = profession_picker(short=True)
            prof.setAccessibleName(f"{hero}'s profession")
            body = Picker(chars=20)
            if bodies is None:
                # the labels bounded in the combo's own font (the sheet's,
                # before any show), the font _fit_columns measures them in
                body.ensurePolished()
                bodies, full = template_choices(world, body.fontMetrics())
            body.set_choices(bodies, tips=full, full=full)
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
        # columns, the widest hero name AS ITS CELL PAINTS IT, and the table's
        # bar (39 rows of 40 px scroll at any height). The name: DemiBold, the
        # weight _style_row gives an unlocked row (any row can be), its
        # fractional advance rounded up, plus the delegate's own text margin
        # either side (PM_FocusFrameHMargin + 1) inside the SE inset -- the
        # integer table-font advance against the inset alone said 1,130 and
        # elided two names to 1,136 px, three ticked to 1,139. Measured: the
        # first width with no name elided, the widest names ticked, to the
        # pixel (--smoke compares each cell's pixels with a wide column's)
        bold = QFont(self.table.font())
        bold.setWeight(QFont.DemiBold)
        widest = math.ceil(max(QFontMetricsF(bold).horizontalAdvance(it.text())
                               for it in self.name_items.values()))
        margin = 2 * (self.table.style().pixelMetric(QStyle.PM_FocusFrameHMargin, None,
                                                     self.table) + 1)
        self.heroes_card.ensurePolished()       # the sheet's 1 px border, before any show
        m, cm = self.outer.contentsMargins(), self.heroes_card.layout().contentsMargins()
        self.STACK_BELOW = (m.left() + m.right() + self.CARD_W + self.outer.spacing()
                            + cm.left() + cm.right() + 2 * self.heroes_card.frameWidth()
                            + sum(self.table.columnWidth(c) for c in (0, 1, 3, 4, 5))
                            + widest + cell + margin
                            + self.table.verticalScrollBar().sizeHint().width())

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
            # a hero with no level is at the player's, as hero_table and
            # validate read it (a constant 3 gave the file another verdict
            # after Open than the CLI's)
            lvl.setValue(int(h.get("level", player.get("level", 3))))
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
    Enemies tab's detail pane. Narrow, the Body and Weapon cards stack (so no
    picker clips: at 1,000 px two columns cut the weapon's '(none…)' row) and
    the Skill bar's strip goes from four cells a row to two."""

    # Below this width (the editor's own) the Body and Weapon cards' pickers
    # cannot hold the widest template (TEMPLATE_LABEL_PX, 202: a label is
    # bounded to it, so this edge holds for any content) or the weapon's
    # '(none: the template's swing)' (174): measured fields of 159 and 127 at
    # 640 px, and each grows 1 px per 2 of the editor. The bar sets its own
    # threshold.
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
        self.template.ensurePolished()          # the sheet's font, the labels' bound
        pairs, full = template_choices(names.world, self.template.fontMetrics())
        self.template.set_choices(pairs, tips=full, full=full)
        self.level = QSpinBox()
        # a HOSTILE's range, not the player's LEVEL_MAX: 0..255, the 0x0056
        # level byte (the owner's ruling, 2026-09-24; sandbox.HOSTILE_LEVEL_MAX
        # says why), and the same constant validate reads, so a file's value
        # the spin cannot hold is one the compiler refuses and Open says so
        self.level.setRange(0, sandbox.HOSTILE_LEVEL_MAX)
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

        self.bar = SkillBar(names)
        bar = card("Skill bar", trailing=(self.bar.clear_b, self.bar.chip))
        bar.body.addWidget(self.bar)
        page.addWidget(bar)
        # what a file says that this page does not edit -- weapon_attribute
        # (the example raider's 19, the monk's 14: the swing rank), passive --
        # is HELD from from_spec and written back by to_spec; dropping it
        # moved the monk's swing rank from 1 to 2 through the window (the
        # verifier's a8, 2026-09-24)
        self.held = {}

        self.ranks = Ranks(names)
        ranks = card("Attributes", trailing=self.ranks.chip)
        ranks.body.addWidget(self.ranks)
        page.addWidget(ranks)
        page.addStretch(1)

        self.template.currentIndexChanged.connect(self._template)
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
        # the bar and the ranks read each other, one signal each way: a slot
        # write recounts the Attributes row chips, a rank edit rewrites each
        # cell's line 2 (the rank the server will act at) at once
        self.bar.changed.connect(lambda: self.ranks.set_bar(self.bar.values()))
        self.bar.changed.connect(self._changed)
        self.ranks.changed.connect(self._ranks_moved)
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
        """The template's name as the field shows it -- bounded (template_label),
        so the page title and the group's roster never outgrow a long name."""
        return self.template.currentText().split("  [")[0] or "hostile"

    def template_full(self):
        """The template's label whole: the hover's, where the shown is elided."""
        return self.template.tips.get(self.template.value(), self.template.currentText())

    def set_where(self, group, member):
        self.where = (group, member)
        self._titles()

    def _titles(self):
        prof = sandbox.PROFESSIONS.get(self.profession(), "No profession")
        g, m = self.where
        self.title.setText(self.display_name())
        self.subtitle.setText(f"{prof}  ·  group {g}, hostile {m}"
                              + ("  ·  the boss" if self.boss.isChecked() else ""))

    def template_pairs(self):
        """The template's own ranks (an npc row's `attributes`, if any): the
        server's fallback for a member with none (authsrv.agent_attributes)."""
        row = self.names.world.rows("npc").get(self.template.value()) or {}
        pairs = row.get("attributes") or []
        return [[int(a), int(r)] for a, r in (pairs.items() if isinstance(pairs, dict) else pairs)]

    # the member keys this page EDITS; every other key a file carries is held
    # (self.held) and written back, so Save never loses what Open read
    EDITED = frozenset(("npc", "level", "health", "skills", "attributes", "weapon_item",
                        "attack_speed", "damage", "boss", "glow"))

    def _template(self):
        prof = self.profession()
        tp = self.template_pairs()
        self.bar.set_professions((prof,))       # the bar's ids are KEPT
        self.ranks.set_professions((prof,), tp)
        self.bar.set_ranks_view(self.ranks.ranks(), tp)
        self.ranks.set_bar(self.bar.values())
        # a held weapon_attribute of another profession than the new
        # template's is dropped: the compiler would never see it ranked
        # (validate holds a hostile's ranks to its template's profession)
        wa = self.held.get("weapon_attribute")
        rules = self.ranks.rules
        if wa is not None and rules is not None:
            owner = (rules.attributes.get(int(wa)) or {}).get("profession")
            if owner is not None and owner != prof:
                del self.held["weapon_attribute"]
        self._changed()

    def _ranks_moved(self):
        self.bar.set_ranks_view(self.ranks.ranks())
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
        m.update({k: v for k, v in self.held.items() if k not in self.EDITED})
        return m

    def summary(self):
        """One line the group page lists: what the tree beside it does not say."""
        k = sum(1 for s in self.bar.values() if s)
        bits = [f"L{self.level.value()}", f"{self.health.value()} hp",
                f"{k} of {sandbox.BAR_SLOTS} skills"]
        if self.ranks.rules is not None:
            bits.append(self.ranks.spent_text())    # the chip's words; a hostile has no budget
        bits.append(self.weapon_item.value() or "the template's swing")
        return "  ·  ".join(bits)

    def from_spec(self, m):
        self.held = {}                          # the file's template is not a CHANGE of template
        self.template.set_value(m.get("npc"))
        self._template()
        self.held = {k: v for k, v in m.items() if k not in self.EDITED}
        # a member with no level is at its TEMPLATE's, the level spawn_rows
        # and validate give the row: the spawn row's level and the
        # 0..HOSTILE_LEVEL_MAX range (a level-300 template opened at a
        # constant 2 would compile here and be refused by the CLI -- one
        # file, two verdicts, the way the constant once opened a level-10
        # template over a budget a hostile no longer has; and the spin's
        # range is validate's, so a template past it clamps AND is said)
        tmpl = self.names.world.rows("npc").get(m.get("npc")) or {}
        self.level.setValue(int(m.get("level", tmpl.get("level", 0) or 0)))
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
        item.setToolTip(0, ed.template_full()
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
        """Open a spec into the window. True once the file is held (whole, or
        with what the window could not hold said in the bar), False when it
        could not be opened -- the command line's --spec reads the answer,
        since the bar is the only other place it is said. None: no file."""
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "Open a spec", self.specs_dir(),
                                                   "TOML (*.toml)")
        if not path:
            return None
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
                return False
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
                return False
            self._stale = words[0]
            set_chip(self.state, words[1], words[2], tip=words[3])
            self.status.setText(words[4])
            self.status.setToolTip(words[5])
            win.enemies.select_place(place)
            self._say(f"Could not open {file_stem(path)} ({why}); your spec is unchanged",
                      15000)
            return False
        win.header.open_b.setToolTip(f"Open a saved spec (TOML).\nLast opened {path}")
        # what the window holds is what Save writes: a fifth group or hostile
        # is dropped at the cap and a template the content lacks becomes the
        # first on the list, without a raise -- so a file the compiler refuses
        # opens as one it accepts, and 'Opened' alone would be the same false
        # word as 'unchanged' above, reached without an exception
        held = set(sandbox.validate(win.to_spec(), win.world))
        try:
            lost = [q for q in sandbox.validate(spec, win.world) if q not in held]
        except Exception as exc:                 # noqa: BLE001 -- a field the window never reads
            # validate int()s what the window dropped on the way in (a hero's
            # bar written as a string, a scalar `attributes`): the file is
            # held, as it was before this check existed, and the raise is
            # what the window could not hold -- not a traceback after the
            # tabs were rewritten and the bar left blank
            lost = [f"{type(exc).__name__}: {exc}"]
        if lost:
            self._say(f"Opened {file_stem(path)}, but the window could not hold all of it "
                      f"({n_of(len(lost), 'change')}: {lost[0]}). Save as a new file to keep "
                      f"the original.", 20000)
            return True
        self._say(f"Opened {file_stem(path)}")
        return True

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

    def stop(self, wait_ms=0):
        """Kill the run's whole tree: session.py, its servers and the client.

        QProcess.kill() alone is TerminateProcess on session.py, whose own
        teardown then never runs; on 2026-09-24 that left two authsrv.py
        processes holding 6112 for hours after the window closed, and every
        other worktree's launch was refused behind them. The servers now die
        with session.py however it ends (its kill-on-close job, childjob.py);
        the tree kill here is what also takes the CLIENT, which session.py
        would have closed itself. It runs while session.py is alive, because
        taskkill finds children by their parent's pid. The old message
        promised the next launch would replace any server left -- true only
        from this worktree. `wait_ms` lets a closing window see `finished`
        before it goes."""
        if self.proc is None:
            return
        self._marks.add("stopped")
        pid = self.proc.processId()
        ok, detail = childjob.kill_tree(pid) if pid else (True, "no pid: not started")
        self.proc.kill()
        if wait_ms:
            self.proc.waitForFinished(wait_ms)
        if ok:
            self._say("Stopped the harness, its servers and the client.", 8000)
        else:
            # the servers still die with the harness (its job); only the
            # client can be left, and the reason goes to the run's log
            write_lines(self.log, [(f"[the tree kill failed: {detail}]", "error")])
            self._say("Stopped the harness and its servers; the client may still be open. "
                      "Close it yourself.", 15000)

    def stop_for_close(self):
        """The window is closing: stop a live run first, and wait for it."""
        if self.proc is not None:
            self.stop(wait_ms=3000)

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
        self.stop_b = button("Stop", "quiet", icon="stop",
                             tip="Stop the run: the harness, its servers and the client.")
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
    was. A line wider than its room is painted elided, never sliced at the
    chip (QStatusBar clips; at 1,000 px the over-cap Open's 'Save as a new
    file to keep the original.' ended at 'keep ' with no mark), and the whole
    line is the bar's hover while it shows."""

    GUTTER = 16                                 # the page's own left gutter

    def __init__(self, parent=None):
        super().__init__(parent)
        self.messageChanged.connect(self.setToolTip)

    def message_rect(self):
        """Where the message is painted: the gutter to QStatusBar's own bound,
        or to the first visible chip (read by --smoke too, so the law and the
        paint share one room)."""
        right = self.width() - 12
        for w in self.findChildren(QWidget, "", Qt.FindDirectChildrenOnly):
            if w.isVisible():
                right = min(right, w.x() - 2)
        return QRect(self.GUTTER, 0, right - self.GUTTER, self.height())

    def paintEvent(self, ev):
        p = QPainter(self)
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_PanelStatusBar, opt, p, self)
        msg = self.currentMessage()
        if msg:
            r = self.message_rect()
            p.setPen(self.palette().windowText().color())
            p.drawText(r, Qt.AlignLeading | Qt.AlignVCenter | Qt.TextSingleLine,
                       self.fontMetrics().elidedText(msg, Qt.ElideRight, r.width()))


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

    def closeEvent(self, event):
        """Closing the window stops the run it launched -- the whole tree.

        Without this the QProcess destructor killed session.py ALONE, which
        is how the servers of 2026-09-24 outlived the window (RunTab.stop)."""
        self.run.stop_for_close()
        super().closeEvent(event)

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


def source_calls(fn):
    """Every call in `fn`'s body, in source order, read off the syntax tree
    for the same reason as printed_strings: a text match over the source
    took the old line kept in a comment for the say site, and a rewrite that
    said a path after the sentence, or appended to the constant in a later
    call, kept the lock green."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return sorted((n for n in ast.walk(tree) if isinstance(n, ast.Call)),
                  key=lambda n: (n.lineno, n.col_offset))


def dotted(node):
    """'self.status.setText' for a call's callee; '' for one that is not a
    name or a chain of attributes on one (a call on a call, a subscript)."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _is_name(node, ident):
    return isinstance(node, ast.Name) and node.id == ident


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
# exempt hostile's compile, its roster line and the kept rules' refusal 3 (an
# attribute table), the lifted caps' four -- the Ranks spins' 0..21, the chip
# telling 12 from 15, a level-28 rank-16 file held whole, a level-300 rank-22
# file refused and said -- 4 (the same table), the encounter list's focus 1,
# Launch's ring and the tab strip's cue 3, the active-window wheel 4 (the
# Skill bar's nested wheel among them, SANDBOX-N1; the one skip line names
# all four), the four popups 4, and the Skill bar's own (SANDBOX-N1,
# 2026-09-24): the strip's pills 2 (the render and the grade: a hand and a
# label row among the Warrior's and common), the search box's and the
# strip's keyboard 2 (focus), the placeholder's way out 1 (an unmarked
# Warrior skill), the Attributes row chips 3 (the count, the rank, the
# template's own ranks planted in memory) and the widest label at 1,000 px 1
# (the attribute table; a body of the widest profession), line 2 painted
# through elide_rank_line 1 (a Monk cell that elides at 1,280), a
# no-attribute skill that varies and the chip's conditional hover 2 (the
# table's rows), the hostile page not scrolling at its own height 1 (an OS
# that lets a hidden window outgrow the screen) -- 38 of the green run's
# 208, dark and light (195 with 33 gated before the repair of 2026-09-24,
# which added thirteen laws, five of them gated: the pill's grade, the
# library's fixed height, the selected well's fill, the hover fill, the
# drop-target edge, the drag sources' mime and pixmap, the Pickers' start of
# text, line 2 through the helper, the template's own ranks, the varying
# no-attribute skill and the chip's hover, a nine-skill file said, the held
# weapon_attribute; 177 with 24 gated before the Skill bar: two Picker laws
# retired, the slot arms of the fit laws rewritten for the strip, and TWENTY
# laws added, net +18 -- the strip's pills, housing, columns and height at
# three widths, the offered set and the spins' one x across one body per
# profession, ticks, drops, the keyboard twice, a 200-character skill name,
# the placeholder, the row chips twice, the widest label, the nested wheel,
# the write paths' one signal, Open holding what the compiler accepts and a
# template change keeping the bar, the tall arm of the right-edge law; 174
# before Stop's three ungated laws, 2026-09-24: Stop
# kills the run's tree, the kill()-alone control orphans a child, the
# window's close kills the tree; 165 before the lifted caps'
# nine: those four and the five ungated -- the party's Level spins pinned at
# 20, the hostile's at 255, the hostile page's spins fitting '255' and '21'
# at three widths; 164 before the roster-line law; 163 before the kept-rules
# law; 159 before the long-name laws: the bounded label, its hover, its
# filter, the no-stray restore). A gated law
# that skips is printed in the verdict; a run short of the floor is a FAIL
# naming the shortfall, which "0 failure(s)" never was. What the floor cannot
# see: on a machine where every gated law runs, up to 38 mandatory laws could
# stop before it names one -- so no mandatory law sits behind a STATE gate. A
# precondition is a law of its own (`if m0.stacked:` once held the stacked
# label law with no else, and the law vanished unnamed when the stack was
# planted away, the re-polish law after it passing over no re-polish; the
# library's fixed height is a law of its own for the same reason, since the
# nested-wheel law sits behind `lbar.maximum() > 0`).
SMOKE_FLOOR = 170

# --smoke's own npc row: the content of tomorrow. The fit laws iterate the
# content of today, which is how desk-hench's three 60-character names stacked
# the Character card at 1,280 px and cut two Template rows mid-glyph with every
# law green until the merge. A 200-character name, planted in the loaded world
# IN MEMORY before the window builds its choices (main, under --smoke only;
# never --snap, never content/ or the vault), so every law after it sees the
# label bound (template_label) working on a name no field was fitted to. A
# profession the example already offers (Warrior), so the one-body-per-
# profession law keeps its rows; a level of its own; a model id, so it is a
# body. The word 'gravelbeard' sits past where the ellipsis falls, for the
# type-to-filter law.
SMOKE_LONG_KEY = "smoke_long_name"
SMOKE_LONG_NAME = ("Tomorrow's hostile, whose name runs far past any field the window fits: a "
                   "row an operator may write, its label elided by the window, its tag kept "
                   "whole, the name whole on hover, and found by gravelbeard from its middle")


# ...and a skill's: the same idea for the Skill bar's cells, planted into the
# names IN MEMORY by the smoke itself for one law and put back (never the
# vault, never content/), 'gravelbeard' past where the cell's ellipsis falls.
SMOKE_LONG_SKILL = ("Tomorrow's skill, whose name runs far past any cell the strip draws: a name "
                    "an operator's mod row may carry, elided by the cell, the whole on hover, and "
                    "found by gravelbeard from its middle, typed into the bar's own search box")


def plant_long_template(world):
    """Put SMOKE_LONG_KEY into `world`'s npc table (in memory) and return its row."""
    row = content.Row({"name": SMOKE_LONG_NAME, "profession": 1, "level": 5, "model_id": 1},
                      "npc", SMOKE_LONG_KEY, {"source": "smoke"})
    world.tables.setdefault("npc", {})[SMOKE_LONG_KEY] = row
    return row


# The stand-in harness Stop's laws launch: one child of its own, its pid said
# on a line the laws read out of the Run tab's log, then both sleep until
# killed. No job anywhere, so only a tree kill can reach the child.
STANDIN_TREE = ("import subprocess, sys, time\n"
                "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])\n"
                "print('TREE', c.pid, flush=True)\n"
                "time.sleep(600)\n")


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
                and "point budget" in h.text())

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
            # and 14 from its own, and 'Level' 15 from both). The ink is read off
            # the rendered window, as label_edges reads a hostile's: the label's
            # rect less its advance is where a RIGHT-aligned label's ink starts,
            # and stayed at the same numbers with the labels planted left (the
            # ink then 14 px from the field before and 30 from its own)
            img = win.grab().toImage()
            gaps = []
            for i, (lab, wdg) in enumerate(win.party.fields):
                if i % 3:
                    prev = win.party.fields[i - 1][1]
                    first, last = _ink_span(img, QRect(lab.mapTo(win, QPoint(0, 0)), lab.size()),
                                            pal["surface"])
                    wx = wdg.mapTo(win, QPoint(0, 0)).x()
                    px = prev.mapTo(win, QPoint(0, 0)).x() + prev.width()
                    gaps.append((lab.text(), None if last is None else wx - last - 1,
                                 None if first is None else first - px))
            check(len(gaps) == 3 and all(own is not None and before is not None
                                         and own * 2 < before for _t, own, before in gaps),
                  f"stacked, each label after the first in its row is under half as far from its "
                  f"own field as from the field before it, its ink read off the window (own, "
                  f"before: {gaps})")
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
    # by side from 1,120 to 1,129 -- the squeeze the stack exists to avoid).
    # Whole is read off the PIXELS: each name cell at the edge against the
    # same cell with the column made wide in place, the three widest names
    # ticked first so they are painted DemiBold -- the derivation's own model
    # (the integer table-font advance against the SE inset) re-read here
    # certified 1,130 with 'Master of Whisp…' on screen to 1,136
    edge = win.party.STACK_BELOW
    tbl, hh = win.party.table, win.party.table.horizontalHeader()
    bold = QFont(tbl.font())
    bold.setWeight(QFont.DemiBold)
    widest = sorted(win.party.name_items, key=lambda i: -QFontMetricsF(bold).horizontalAdvance(
        win.party.name_items[i].text()))[:3]
    ticked = [i for i in widest if not win.party.rows[i][0].isChecked()]
    for i in ticked:
        win.party.rows[i][0].setChecked(True)

    def name_cell(it):
        tbl.scrollToItem(it)
        settle(2)
        return tbl.viewport().grab(tbl.visualItemRect(it)).toImage()

    got = {}
    for w in (edge, edge - 1):
        win.resize(w, 800)
        settle(8)
        colw = tbl.columnWidth(2)
        if win.party.stacked:
            got[win.width()] = (True, colw, None)
            continue
        narrow = {i: name_cell(it) for i, it in win.party.name_items.items()}
        hh.setSectionResizeMode(2, QHeaderView.Interactive)
        tbl.setColumnWidth(2, colw + 300)
        settle(4)
        cut = [it.text() for i, it in win.party.name_items.items()
               if narrow[i] != name_cell(it).copy(0, 0, narrow[i].width(), narrow[i].height())]
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        settle(4)
        got[win.width()] = (False, colw, cut[:3])
    for i in ticked:
        win.party.rows[i][0].setChecked(False)
    check(got.get(edge, (True,))[0] is False and got[edge][2] == [] and got.get(edge - 1, (False,))[0]
          and len(ticked) >= 2,
          f"at the stack edge ({edge} px) the card is beside the table and every hero name cell "
          f"is painted as in a wide column, the widest ticked (DemiBold), and one pixel under it "
          f"the card stacks (width: stacked, Hero column, cut = {got})")
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
    lone.set_professions((1,))
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
    # emptying the roster and losing the signal), and the Attributes card
    # reads no budget off the level -- a hostile has none (the owner's ruling,
    # 2026-09-24): its chip counts what is spent, its hint says so
    m1 = en.groups[1].members[0]
    emits = []
    en.changed.connect(lambda: emits.append(1))
    m1.level.setValue(0)
    settle()
    spent1 = n_of(m1.ranks.spent(), "point") if m1.ranks.rules is not None else None
    check(en.groups[1].roster.count() == len(en.groups[1].members) and emits
          and spent1 is not None and m1.ranks.chip.text() == spent1
          and m1.ranks.chip.property("kind") == "info"
          and "point budget" in m1.ranks.hint.text() and "0 points" not in m1.ranks.hint.text(),
          f"a hostile at level 0 keeps its group's roster ({en.groups[1].roster.count()} of "
          f"{len(en.groups[1].members)} rows), emits the change ({len(emits)}), its chip counts "
          f"the spend ({m1.ranks.chip.text()!r}, {m1.ranks.chip.property('kind')}) and its hint "
          f"reads no budget off the level")
    m1.level.setValue(2)
    settle()
    # the PLAYER's and every hero's Level spin keep the player's 1..20, and no
    # rank spin is theirs (their ranks are the in-game panels': 0x003A /
    # 0x003B carry them and the client asserts at CharData.cpp(202) past 12).
    # The hostile's lift (255 / 21, the owner's ruling of 2026-09-24) went
    # through constants of its own, and nothing before this law pinned these
    # maxima: sandbox.LEVEL_MAX bumped would have lifted the three spins with
    # the fit law green (any two digits fit). The literal 20, on purpose
    lvls = [win.party.level] + [lv for _c, _p, _b, lv in win.party.rows.values()]
    check(len(lvls) >= 2 and all(s.maximum() == 20 and s.minimum() == 1 for s in lvls)
          and sandbox.LEVEL_MAX == 20 and not win.party.findChildren(Ranks),
          f"the character's and every hero's Level spin is 1..20 ({len(lvls)} spins), and the "
          f"Party tab has no rank spin (the panels' job, held to the table's 12 by the client)")
    # ...while a hostile's Level spin is 0..255 -- sandbox.HOSTILE_LEVEL_MAX,
    # the 0x0056 level byte, lifted from 20 by the ruling
    check(m1.level.maximum() == 255 and m1.level.minimum() == 0
          and sandbox.HOSTILE_LEVEL_MAX == 255,
          f"a hostile's Level spin is 0..255 (HOSTILE_LEVEL_MAX, the 0x0056 level byte), "
          f"lifted from the player's 20 by the owner's ruling")
    # ---- the Skill bar (SANDBOX-N1): eight wells over an inline library.
    # The strip RENDERS its pills through SlotDelegate and the one painter the
    # Skills list uses (paint_pill): treatment and control on the SAME cell --
    # painted with its grade, then with the grade taken away -- off grabs of the
    # WINDOW (a widget's own grab is a transparent canvas); an empty cell loses
    # nothing when its (absent) grade is taken away
    m0 = en.groups[0].members[0]
    en.select(m0)
    settle(4)
    bar0 = m0.bar
    keep_ids = bar0.values()
    hand_w = next((s for s in sorted(win.names.modelled) if win.names.skill_profession(s) in (0, 1)), None)
    label_w = next((s for s in sorted(win.names.labelled) if win.names.skill_profession(s) in (0, 1)), None)
    if hand_w and label_w:
        bar0.set_values([hand_w, label_w, 0])
        bar0.select_slot(3)                     # the measured cells keep the field fill
        settle(4)
        lost = {}
        real_pill = orchui.paint_pill

        def no_pill(_p, x, cy, grade, font=None):
            """paint_pill's rect without its paint (the Skills list's delegate,
            painted in the same grab, reads the rect back)."""
            if grade not in orchui.GRADE_TEXT:
                return None
            w, h = orchui.pill_size(grade, font)
            return QRect(x, cy - h // 2, w, h)

        grade_px = {}
        for i, tag in ((0, "modelled"), (1, "label"), (2, "empty")):
            it = bar0.strip.item(i)
            cell = bar0.strip.cell_rect(i)
            # the CONTROL is the same cell with the one painter made a no-op --
            # not the grade taken away, which also widens line 2 (a cell then
            # changed for another reason, and a delegate that skipped the
            # pill passed); measured inside the pill's own rect
            pill_r = orchui.SlotStrip.layout(cell, it.data(ROLE_PARTS))[4]
            box_r = pill_r if pill_r is not None else cell
            at = bar0.strip.viewport().mapTo(win, box_r.topLeft())
            box = QRect(at, box_r.size())
            with_pill = win.grab().toImage().copy(box)
            # ...and the pill's GRADE, told by its INK: a modelled cell's pill
            # writes its word in the good chip's ink and none of the info
            # chip's, a label cell's the reverse -- the loss below is blind to
            # the grade (every pill painted 'label' passed it; the verifier's
            # b3, 2026-09-24). The ink, not the fill: in dark the good fill
            # sits 10 from the info edge and 15 from the info fill (measured),
            # while the two inks are 68 apart in both palettes
            grade_px[tag] = (_count_near(with_pill, pal["chip_good_fg"], 12),
                             _count_near(with_pill, pal["chip_info_fg"], 12))
            orchui.paint_pill = no_pill
            bar0.strip.viewport().update()
            settle(3)
            without = win.grab().toImage().copy(box)
            orchui.paint_pill = real_pill
            bar0.strip.viewport().update()
            settle(2)
            lost[tag] = _diff(with_pill, without)
        check(lost["modelled"] > 40 and lost["label"] > 40 and lost["empty"] == 0,
              f"the strip RENDERS a grade pill in a modelled skill's cell and a label skill's, and "
              f"none in an empty one (pixels a cell's pill rect loses with paint_pill made a no-op: "
              f"{lost})")
        check(grade_px["modelled"][0] >= 15 and grade_px["modelled"][1] <= 2
              and grade_px["label"][1] >= 10 and grade_px["label"][0] <= 2,
              f"and the pill tells the GRADES apart: the modelled cell's pill writes its word in the "
              f"good chip's ink and none of the info chip's, the label cell's the reverse (good, "
              f"info ink px: {grade_px})")
        bar0.set_values(keep_ids)
        settle()
    else:
        skip("the strip renders its pills", f"hand {hand_w} / label {label_w}: no Warrior or common "
                                            f"row of each grade in the table")
        skip("the pill tells the grades apart", "the same")
    # ...and a SkillBar built by any caller houses its chip and its hint from
    # birth (a card re-homes the chip; shown with no parent, a label is a window
    # of its own -- the Ranks trap, twice over), and every hostile's are children
    # of its page
    lone_bar = SkillBar(win.names)
    lone_bar.set_professions((1,))
    lone_bar.set_values([322])
    settle()
    housed = [(ed.bar.chip.window() is win and ed.bar.clear_b.window() is win
               and ed.bar.hint.isVisibleTo(en._pages[ed])
               and "slot" in ed.bar.hint.text()) for gg in en.groups for ed in gg.members]
    check(not strays() and lone_bar.chip.parentWidget() is lone_bar
          and lone_bar.clear_b.parentWidget() is lone_bar
          and lone_bar.hint.parentWidget() is lone_bar and all(housed),
          f"a Skill bar on its own houses its chip, its Clear slot and its hint ({len(strays())} "
          f"stray), and every hostile's are children of its page ({sum(housed)} of {len(housed)})")
    lone_bar.deleteLater()
    # the library is ROWS rows tall and SCROLLS on the template's own set --
    # ungated, because the nested-wheel law below sits behind `lbar.maximum()
    # > 0`, a property of the code under test: with the height regressed to
    # every row that law became a declared skip and the verdict stayed green
    # (the verifier's b8, 2026-09-24). Only the OS gate stays on that law.
    lib, lbar = bar0.list, bar0.list.verticalScrollBar()
    rows_fit = lib.viewport().height() / max(1, lib.sizeHintForRow(0))
    check(SkillBar.ROWS in (6, 7) and abs(rows_fit - SkillBar.ROWS) < 0.5
          and lib.minimumHeight() == lib.height() == lib.maximumHeight()
          and lib.visible_count() > SkillBar.ROWS and lbar.maximum() > 0,
          f"the library is a fixed {SkillBar.ROWS} rows tall ({lib.height()} px: {rows_fit:.2f} rows "
          f"of {lib.sizeHintForRow(0)} in its viewport) and scrolls on the Warrior-and-common set "
          f"({lib.visible_count()} rows shown, {lbar.maximum()} px to scroll)")
    # the SELECTED well is filled in the selection tint and never the accent
    # (the one-accent law is a census of button roles, and the strip paints
    # its own fills: a well filled PAL['accent'] passed it -- the verifier's
    # c2 plant, 2026-09-24); the well under the POINTER takes the hover fill
    # every list row has from the sheet, the strip painting its own (c7); and
    # the well a DRAG is over takes the focus edge -- the ring a rounded 1 px
    # pen leaves is the 50 % blend of the ink and the ground it crosses, so
    # the count is of pixels near mix(focus, field) and mix(focus, surface)
    vp = bar0.strip.viewport()
    bar0.select_slot(0)
    settle(3)

    def well_box(i):
        well = orchui.SlotStrip.layout(bar0.strip.cell_rect(i), None)[0]
        return QRect(vp.mapTo(win, well.topLeft()), well.size())

    def fill_px(i, key, img=None):
        b = well_box(i)
        img = img or win.grab().toImage()
        return _count_near(img, pal[key], 6, (b.left() + 4, b.top() + 4, b.right() - 3, b.bottom() - 3))

    def edge_px(i, ink, img=None):
        b = well_box(i)
        img = img or win.grab().toImage()
        ring = lambda colour: (_count_near(img, colour, 12, (b.left(), b.top(), b.right() + 1, b.bottom() + 1))  # noqa: E731
                               - _count_near(img, colour, 12, (b.left() + 3, b.top() + 3, b.right() - 2, b.bottom() - 2)))
        return ring(orchtheme.mix(pal[ink], pal["field"], 0.5)) + ring(orchtheme.mix(pal[ink], pal["surface"], 0.5))

    sel = (fill_px(0, "selection_bg"), fill_px(0, "accent"), fill_px(5, "field"))
    check(sel[0] > 1000 and sel[1] == 0 and sel[2] > 1000,
          f"the selected well is filled in the selection tint and holds no accent pixel, an "
          f"unselected one in the field fill (selection, accent, field px: {sel})")
    c5, c6 = bar0.strip.cell_rect(5).center(), bar0.strip.cell_rect(6).center()
    QApplication.sendEvent(vp, QEnterEvent(QPointF(c5), QPointF(vp.mapToGlobal(c5)), QPointF(vp.mapToGlobal(c5))))
    QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseMove, QPointF(c5), QPointF(vp.mapToGlobal(c5)),
                                           Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    settle(3)
    hov = [fill_px(5, "hover"), fill_px(5, "field"), fill_px(6, "hover")]
    QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseMove, QPointF(c6), QPointF(vp.mapToGlobal(c6)),
                                           Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    settle(3)
    hov += [fill_px(5, "hover"), fill_px(6, "hover")]
    QApplication.sendEvent(vp, QEvent(QEvent.Leave))
    settle(3)
    hov.append(fill_px(6, "hover"))
    check(hov[0] > 1000 and hov[1] == 0 and hov[2] == 0 and hov[3] == 0 and hov[4] > 1000 and hov[5] == 0,
          f"the well under the pointer takes the hover fill and its neighbour does not, the fill "
          f"following the pointer and leaving with it (hover px on 5, field on 5, hover on 6; then "
          f"on 5, on 6; after leave on 6: {hov})")
    c3 = bar0.strip.cell_rect(3).center()
    md3 = orchui.skill_mime(next(s for s in sorted(win.names.modelled)
                                 if win.names.skill_profession(s) == 1 and s not in bar0.values()))
    before_edge = (edge_px(3, "focus"), edge_px(3, "border"))
    QApplication.sendEvent(vp, QDragEnterEvent(c3, Qt.CopyAction, md3, Qt.LeftButton, Qt.NoModifier))
    QApplication.sendEvent(vp, QDragMoveEvent(c3, Qt.CopyAction, md3, Qt.LeftButton, Qt.NoModifier))
    settle(3)
    under = (bar0.strip.drop_row, edge_px(3, "focus"), edge_px(3, "border"), edge_px(2, "focus"))
    QApplication.sendEvent(vp, QDragLeaveEvent())
    settle(3)
    after_edge = (bar0.strip.drop_row, edge_px(3, "focus"), bar0.values())
    check(before_edge[0] == 0 and before_edge[1] > 200 and under[0] == 3 and under[1] > 200
          and under[2] < before_edge[1] // 4 and under[3] == 0 and after_edge == (-1, 0, keep_ids),
          f"the well a drag is over takes the focus edge (its border ring gone but for the corners) "
          f"and its neighbour keeps the border, and the edge leaves with the drag, nothing written "
          f"(focus / border ring px before {before_edge}, under the drag {under[1:]} on row "
          f"{under[0]}, after {after_edge[:2]})")
    # the drag SOURCES: what each builds is read here without a QDrag.exec (a
    # nested event loop) -- a library row's mime carries the id ALONE, so the
    # strip PLACES it (one carrying a slot made every place a swap, the
    # verifier's b9 plant, 2026-09-24); a cell's carries its id, its slot and
    # THIS strip's token; an empty cell drags nothing; and each drag's pixmap
    # is the cell or the row itself, so the skill travels with the cursor
    lib_row = next(it for it in bar0._items() if not it.isHidden())
    src = (orchui.parse_skill_mime(orchui.SkillLibrary.drag_mime(lib_row), bar0.strip.token),
           orchui.parse_skill_mime(bar0.strip.drag_mime(0), bar0.strip.token),
           orchui.parse_skill_mime(bar0.strip.drag_mime(0), "another strip's token"),
           bar0.strip.drag_mime(5),
           bar0.strip.drag_pixmap(0).size() == bar0.strip.cell_rect(0).size(),
           bar0.list.drag_pixmap(lib_row).size() == bar0.list.visualItemRect(lib_row).size())
    check(src[0] == (int(lib_row.data(ROLE_ID)), None) and src[1] == (keep_ids[0], 0)
          and src[2] == (keep_ids[0], None) and src[3] is None and src[4] and src[5],
          f"a library row's drag carries its id and no slot, a cell's its id, its slot and the "
          f"strip's own token (read under another token, a place), an empty cell drags nothing, "
          f"and each pixmap is the cell or row itself ({src})")
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
        for tag, combo in (("Template", ed.template), ("Weapon", ed.weapon_item),
                           ("Skills offered", ed.bar.prof)):
            for i in range(combo.count()):
                if not _fits(combo, combo.itemText(i)):
                    cut.append((ed.template.value(), tag, combo.itemText(i)[:40],
                                _field_width(combo)))
        return cut

    meta_fm = QFontMetrics(orchui.mono_font(orchtheme.TYPE["caption"]))

    def cut_cells(ed):
        """Every filled cell of the strip whose NAME neither fits its name rect
        nor is whole on the cell's hover, whose rank line is not whole in the
        item's text, or whose pill or rects leave the cell -- through
        SlotStrip.layout on the rect the view reports, the delegate's own."""
        cut = []
        st = ed.bar.strip
        fm = st.fontMetrics()
        for i, sid in enumerate(ed.bar.values()):
            if not sid:
                continue
            it = st.item(i)
            parts = it.data(ROLE_PARTS)
            cell = st.cell_rect(i)
            _well, num_r, name_r, meta_r, pill_r = orchui.SlotStrip.layout(
                cell, parts, body_fm=fm, meta_fm=meta_fm)
            name, line2 = parts[0], it.data(ROLE_SLOT)[1]
            if fm.horizontalAdvance(name) > name_r.width() and name not in it.toolTip():
                cut.append((ed.template.value(), f"slot {i + 1}", name[:40], name_r.width()))
            if line2 and line2 not in it.text():
                cut.append((ed.template.value(), f"slot {i + 1} line 2", line2[:40]))
            for tag, r in (("number", num_r), ("name", name_r), ("line 2", meta_r), ("pill", pill_r)):
                if r is not None and not cell.contains(r):
                    cut.append((ed.template.value(), f"slot {i + 1} {tag} leaves the cell",
                                r.getRect(), cell.getRect()))
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

    def query_room(ed, text):
        """(the px the search box gives its text, the px `text` needs) with
        `text` typed -- the Skills filter's own measure (SE_LineEditContents
        less the visible tool buttons), the clear button counted since a
        typed query shows it."""
        fl = ed.bar.filter
        fl.setText(text)
        settle(3)
        opt = QStyleOptionFrame()
        fl.initStyleOption(opt)
        room = (fl.style().subElementRect(QStyle.SE_LineEditContents, opt, fl).width()
                - sum(b.width() for b in fl.findChildren(QToolButton) if b.isVisibleTo(fl)) - 4)
        want = fl.fontMetrics().horizontalAdvance(text)
        fl.setText("")
        settle(2)
        return room, want

    for w, h in ((1280, 860), (1120, 760), (1000, 720)):
        win.resize(w, h)
        settle(8)
        cut, cols, heights, fits2, rooms = [], {}, {}, {}, {}
        for n_ed, ed in enumerate(eds):
            en.select(ed)
            settle(4)
            cut += cut_choices(ed) + cut_cells(ed)
            cols[ed.template.value()] = ed.bar.strip.columns
            heights[ed.template.value()] = ed.bar.strip.height()
            # a typed 12-character query whole in the search box (at 1,000 px
            # the box was 122 px with Clear slot in its row and showed the
            # last seven characters of 'gravelbeard'; the verifier's c4)
            rooms[n_ed] = query_room(ed, "gravelbeard ")
            # line 2 whole in its rect at 1,000 (two columns); at 1,280 and
            # 1,120 a Monk's 'Protection Prayers 1' (144 px, measured) elides
            # in a 131 px room, so there the RANK must survive the elision --
            # the delegate's own rule (elide_rank_line), the whole line being
            # the item's text (checked by cut_cells)
            for i, sid in enumerate(ed.bar.values()):
                if sid:
                    it = ed.bar.strip.item(i)
                    r = orchui.SlotStrip.layout(ed.bar.strip.cell_rect(i), it.data(ROLE_PARTS),
                                                body_fm=ed.bar.strip.fontMetrics(), meta_fm=meta_fm)[3]
                    line2 = it.data(ROLE_SLOT)[1]
                    shown2 = orchui.elide_rank_line(meta_fm, line2, r.width())
                    fits2[(ed.template.value(), i)] = (
                        meta_fm.horizontalAdvance(line2) <= r.width(),
                        shown2.split(" ")[-1] == line2.split(" ")[-1]
                        and meta_fm.horizontalAdvance(shown2) <= r.width())
        narrow_q = {k: v for k, v in rooms.items() if v[0] < v[1]}
        check(not cut and all(ed.weapon_item.itemText(0).startswith("(none") for ed in eds)
              and len(rooms) == len(eds) and not narrow_q,
              f"at {w} px every choice in each example hostile's Template, Weapon and Skills "
              f"offered combos fits its field, every slotted skill's name fits its cell, its "
              f"rank line whole in the cell's text and its pill inside the cell, and the search "
              f"box holds a typed 12-character query whole (the strips {cols} cells a row, the "
              f"cards {'stacked' if m0.stacked else 'side by side'}; cut: {cut[:2] or 'none'}; "
              f"query room, need: {next(iter(rooms.values()))}; short: {narrow_q or 'none'})")
        # the strip's columns come off its OWN width (four while the viewport
        # holds four cells a name can live in, else two), never off its content
        # -- the 840-constant defect -- so every hostile's strip is one shape
        # at one width; its height is the rows' and no more
        st = m0.bar.strip
        want_cols = 4 if w > 1000 else 2
        rows_ = sandbox.BAR_SLOTS // want_cols
        whole2 = sum(1 for wh, _k in fits2.values() if wh)
        check(set(cols.values()) == {want_cols} and len(set(heights.values())) == 1
              and st.height() == rows_ * st.CELL_H + 2 * st.frameWidth()
              and st.cell.width() * want_cols <= st.viewport().width()
              and all(kept for _wh, kept in fits2.values()) and (w != 1000 or whole2 == len(fits2)),
              f"at {w} px the strip is {want_cols} cells a row for every hostile ({rows_} rows, "
              f"{st.height()} px tall, cells {st.cell.width()} px in a {st.viewport().width()} px "
              f"viewport); every cell's rank survives its line's elision, and the line is whole "
              f"{'as it must be at two columns' if w == 1000 else 'where it fits'} ({whole2} of "
              f"{len(fits2)} whole)")
        # stacked, the Body and Weapon cards' inputs start at one x, their
        # labels right-aligned up to it (each form sized its own label column:
        # 'Template' and 'Attack interval' put the two cards' inputs 32 px
        # apart in one column); side by side each form keeps its own column
        en.select(m0)
        settle(4)
        edges[w] = (m0.template.mapTo(win, QPoint(0, 0)).x(), m0.template.width(),
                    m0.weapon_item.mapTo(win, QPoint(0, 0)).x())
        # ...and the hostile page's spins show their longest value whole:
        # '255' in the Level spin and '21' in each Ranks spin, measured off
        # the line edit as the Party tab's spin law measures (that law stops
        # at its own tab, and the lift put a third digit in a field fitted
        # to two). The value each spin is measured at is PINNED here too --
        # the Level spin's at '255' and every Ranks spin's at '21' -- and the
        # label prints the maxima measured, not the constants: with the Ranks
        # spins planted back to 0..12 this law passed while printing "its
        # '21'", having measured '12' (the verifier's plant, 2026-09-24)
        hsp = [m0.level] + list(m0.ranks.spins.values())
        rmax = sorted({s.textFromValue(s.maximum()) for s in m0.ranks.spins.values()})
        hnarrow = [(s.accessibleName() or "Level", _spin_field(s).width(),
                    s.fontMetrics().horizontalAdvance(s.textFromValue(s.maximum())))
                   for s in hsp
                   if _spin_field(s).width() - 4
                   < s.fontMetrics().horizontalAdvance(s.textFromValue(s.maximum()))]
        check(m0.level.textFromValue(m0.level.maximum()) == "255"
              and rmax == [str(sandbox.HOSTILE_RANK_MAX)] and not hnarrow
              and all(s.isVisibleTo(win) for s in hsp),
              f"at {w} px the hostile page's Level spin shows its maximum "
              f"'{m0.level.textFromValue(m0.level.maximum())}' whole and each of its "
              f"{len(hsp) - 1} Ranks spins its maximum {rmax} (the constants say '255' and "
              f"'{sandbox.HOSTILE_RANK_MAX}'; too narrow: {hnarrow[:3] or 'none'})")
        # the stack itself is a law, never a gate: behind `if m0.stacked:` the
        # two laws below vanished unnamed when the stack was planted away, and
        # the re-polish law after them passed over no re-polish
        check(m0.stacked is (w == 1000),
              f"at {w} px the hostile page's cards are "
              f"{'stacked' if w == 1000 else 'side by side'} (the editor {m0.width()} px "
              f"against its edge of {m0.STACK_BELOW})")
        if w == 1000:
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
    # width: the Template and Weapon choices fit, the strip's columns do NOT
    # move with the template (the old bar re-picked them from each list, and
    # a threshold fitted to one list cut another's), the library OFFERS that
    # profession's acting skills plus the common ones with the box ticked and
    # all of them unticked, combo row 0 names the profession as the template's,
    # the search is cleared, and the Attributes spins stand at ONE x whatever
    # the profession's widest label (the label column is measured over every
    # profession once, not per template)
    m0_spec = m0.to_spec()
    rows = win.names.world.rows("npc")
    byprof = {}
    for i in range(m0.template.count()):
        k = m0.template.itemData(i)
        byprof.setdefault(int((rows.get(k) or {}).get("profession", 0) or 0), k)
    acting = win.names.modelled | win.names.labelled
    cut, cols, offered, spin_x = [], {}, {}, {}
    for p, k in sorted(byprof.items()):
        # the search AND the combo disturbed before each change, so the reset
        # of both is observable (the combo left at row 0 made its reset arm
        # unfalsifiable: the verifier's b5 plant, 2026-09-24)
        m0.bar.filter.setText("heal")
        set_combo(m0.bar.prof, 0)
        settle()
        m0.template.set_value(k)
        settle(4)
        cols[p] = m0.bar.strip.columns
        cut += cut_choices(m0) + cut_cells(m0)
        want = sandbox.default_unlocks(win.names.world, (p,))
        ticked = m0.bar.visible_ids()
        m0.bar.acts.setChecked(False)
        settle()
        untied = m0.bar.visible_ids()
        m0.bar.acts.setChecked(True)
        settle()
        pname = sandbox.PROFESSIONS.get(p)      # a template may carry a profession the table lacks (11)
        label0 = f"{pname} and common" if pname else "Common"
        # ...and a template with no known profession, whose row 0 is the
        # common skills already, offers no 'Common (no profession)' row (the
        # same 59 twice: the verifier's c11); every known profession keeps it
        datas = [m0.bar.prof.itemData(i) for i in range(m0.bar.prof.count())]
        offered[p] = (sorted(ticked) == sorted(s for s in want if s in acting),
                      sorted(untied) == sorted(want), m0.bar.prof.itemText(0) == label0,
                      m0.bar.prof.currentIndex() == 0, m0.bar.filter.text() == "",
                      (-1 in datas) is (pname is not None),
                      m0.bar.prof.maxVisibleItems() == m0.bar.prof.count())
        spin_x[p] = sorted({s.mapTo(win, QPoint(0, 0)).x() for s in m0.ranks.spins.values()})
    swing = []
    for k in ("bandit_raider", "academy_monk", "bandit_raider"):
        m0.template.set_value(k)
        settle(4)
        swing.append(m0.bar.strip.columns)
    m0.from_spec(m0_spec)
    settle(4)
    bad_offer = {p: v for p, v in offered.items() if not all(v)}
    check(len(byprof) >= 6 and not cut and swing == [4, 4, 4] and not bad_offer
          and m0.to_spec() == m0_spec and 11 in byprof,
          f"at 1,280 px a hostile in any of {len(byprof)} professions' bodies fits its Template and "
          f"Weapon choices and every slotted name, the strip keeps four cells a row (Warrior, "
          f"Monk, Warrior: {swing}), and the library offers that profession's acting skills plus "
          f"the common ones (all of them unticked), combo row 0 named as the template's with the "
          f"combo and the search RESET to it, and the 'Common (no profession)' row offered for a "
          f"known profession only (a profession-11 body among them: {11 in byprof}; wrong: "
          f"{bad_offer or 'none'}; cut: {cut[:2] or 'none'})")
    check(len(spin_x) >= 6 and all(len(v) == 1 for v in spin_x.values())
          and len({v[0] for v in spin_x.values()}) == 1,
          f"the Attributes spins stand at ONE x across one body per profession, one attribute to "
          f"a row (spin x by profession: {spin_x})")
    # ...and a label no field was fitted to: --smoke's own row (SMOKE_LONG_NAME,
    # planted by main), 200 characters against a budget of TEMPLATE_LABEL_PX.
    # The three fit laws above iterate today's content; this row is tomorrow's.
    # Shown elided -- the name ending in an ellipsis, the tag whole -- it fits
    # the Template field and the Body combo at each width, and no label in
    # either picker measures over the budget in the picker's own font
    long_i = m0.template.findData(SMOKE_LONG_KEY)
    body3 = win.party.rows[3][2]
    long_b = body3.findData(SMOKE_LONG_KEY)
    long_full = m0.template.itemData(long_i, ROLE_FULL) if long_i >= 0 else ""
    fit, over = {}, []
    for w, h in ((1280, 860), (1120, 760), (1000, 720)):
        win.resize(w, h)
        settle(8)
        en.select(m0)
        settle(4)
        shown = m0.template.itemText(long_i)
        head = shown.rsplit("  [", 1)[0]
        fit[w] = (head.endswith("…"), shown.endswith("  [W L5]"), _fits(m0.template, shown),
                  body3.itemText(long_b) == shown, _fits(body3, shown))
    for picker in (m0.template, body3):
        over += [picker.itemText(i)[:30] for i in range(picker.count())
                 if picker.fontMetrics().horizontalAdvance(picker.itemText(i)) > TEMPLATE_LABEL_PX]
    check(long_i >= 0 and long_b >= 0 and len(SMOKE_LONG_NAME) >= 200
          and long_full == SMOKE_LONG_NAME + "  [W L5]" and all(all(v) for v in fit.values())
          and not over,
          f"a {len(SMOKE_LONG_NAME)}-character template name (--smoke's own row) is shown with "
          f"its name elided and its tag whole, and fits the Template field and the Body combo at "
          f"1,280, 1,120 and 1,000 px (elided, tag, fits, the same in Body, fits: {fit}); no "
          f"label in either picker is over {TEMPLATE_LABEL_PX} px ({over[:2] or 'none'})")
    # ...the label whole is the row's hover in the drop-down, the field's once
    # picked, and the encounter row's; picked into a hostile, the elided name
    # is the page title and the group roster's name, and the page floors the
    # window no wider than the raider's did
    win.resize(1280, 860)
    settle(8)
    floor_before = win.minimumSizeHint().width()
    m0.template.set_value(SMOKE_LONG_KEY)
    settle(4)
    shown = m0.template.itemText(long_i)
    head = shown.rsplit("  [", 1)[0]
    row_tip = next((it.toolTip(0) for it in en._walk() if it.data(0, Qt.UserRole) is m0), "")
    roster_name = en.groups[0].roster.item(0).data(ROLE_ROSTER)[0]
    floor_after = win.minimumSizeHint().width()
    check(m0.template.itemData(long_i, Qt.ToolTipRole) == long_full
          and m0.template.toolTip() == long_full and row_tip.startswith(long_full)
          and m0.title.text() == head and roster_name == head and "gravelbeard" not in head
          and floor_after <= floor_before,
          f"the long label whole is the row's hover, the picked field's and the encounter row's "
          f"({len(long_full)} characters); the elided name is the page title and the roster's "
          f"({head[-12:]!r}), and the page floors the window no wider ({floor_after} of "
          f"{floor_before})")
    # ...and the type-to-filter matches the label WHOLE: a word the ellipsis
    # took off the surface, typed, finds that row alone and completes with the
    # shown label (Qt's own completer matched the shown text, and completed
    # with the match role's); a word in no name finds none
    comp = m0.template.completer()
    comp.setCompletionPrefix("gravelbeard")
    hits, hit = comp.completionCount(), comp.currentCompletion()
    hit_key = comp.currentIndex().data(ROLE_ID) if hits else None
    comp.setCompletionPrefix("gravelbeard-of-no-row")
    none = comp.completionCount()
    comp.setCompletionPrefix("")
    check(m0.template.lineEdit().completer() == comp and hits == 1 and hit_key == SMOKE_LONG_KEY
          and hit == shown and "gravelbeard" in long_full and "gravelbeard" not in shown
          and none == 0,
          f"typing a word from the middle of the long name into the Template picker's filter "
          f"finds that row alone by its label whole (the shown one lost the word to the "
          f"ellipsis) and completes with the shown label ({hits} hit, {hit[-16:]!r}; a word in "
          f"no name: {none})")
    # ...and a Picker shows the START of its text -- the field's cursor at 0
    # once a value is picked, never scrolled to the end (a skill once read
    # 'V Strength] *') -- on the long template's bounded label and on the
    # Weapon picker, at each of the three widths. The law that held this was
    # retired with the skill Pickers and the behaviour lives on in the two
    # that remain (the verifier's b4, 2026-09-24). Measured on the way: no
    # label is wider than its field today (the Template field is 299 / 219 /
    # 449 px, stacked at 1,000; the bounded label 199), so the cursor is the
    # whole of what a scrolled field would show
    starts = {}
    for w, h in ((1280, 860), (1120, 760), (1000, 720)):
        win.resize(w, h)
        settle(8)
        en.select(m0)
        settle(4)
        m0.template.set_value(SMOKE_LONG_KEY)
        m0.weapon_item.set_value(m0.weapon_item.itemData(1))
        settle(4)
        starts[w] = (m0.template.lineEdit().cursorPosition(), m0.weapon_item.lineEdit().cursorPosition(),
                     m0.template.fontMetrics().horizontalAdvance(m0.template.currentText()),
                     _field_width(m0.template))
    win.resize(1280, 860)                       # m0 stays on the long template: the restore law's subject
    settle(8)
    check(len(starts) == 3 and all(c == 0 and wc == 0 for c, wc, _a, _f in starts.values()),
          f"the Template picker shows the START of the long label and the Weapon picker its own at "
          f"1,280, 1,120 and 1,000 px (cursor, weapon cursor, label px, field px: {starts})")
    # ...and the restore, a VISIBLE editor's from_spec to a different template
    # (set_professions twice in one turn), opens no window of its own: the
    # first turn's Attributes widgets, un-parented before the grid's queued
    # show fired, were shown as ten windows with the keyboard focus in one --
    # which also took the OS wheel law below it (Ranks._clear hides first)
    m0.from_spec(m0_spec)
    settle(4)
    check(m0.to_spec() == m0_spec and not strays(),
          f"a visible hostile's from_spec to a different template (its ranks rebuilt twice in "
          f"one turn, its library repopulated) opens no window of its own ({len(strays())} stray)")

    # ---- the Skill bar's own laws (SANDBOX-N1): one write path, and every
    # view of the model -- the strip, the library's checks, the chip, the
    # Attributes row chips -- re-derived from it
    def drop_on(view, sid, from_slot, at, token=None):
        """A drop as the OS delivers one: enter, then drop, on the VIEWPORT
        (a scroll area refuses drag events on its frame), carrying the bar's
        own mime -- a cell's under the strip's own token unless another is
        given (a cell from ANOTHER window's strip)."""
        md = orchui.skill_mime(sid, from_slot, bar0.strip.token if token is None else token)
        QApplication.sendEvent(view.viewport(), QDragEnterEvent(at, Qt.CopyAction, md, Qt.LeftButton,
                                                                Qt.NoModifier))
        QApplication.sendEvent(view.viewport(), QDropEvent(QPointF(at), Qt.CopyAction, md,
                                                           Qt.LeftButton, Qt.NoModifier))

    def key_on(w, key, mods=Qt.NoModifier):
        QApplication.sendEvent(w, QKeyEvent(QEvent.KeyPress, key, mods))

    bar0 = m0.bar
    hits = []                                    # NOT `emits`: the level-0 law's lambda still
    tally = lambda: hits.append(1)               # noqa: E731 -- appends to `emits` (late binding)
    bar0.changed.connect(tally)
    acting_w = [s for s in sorted(win.names.modelled) if win.names.skill_profession(s) == 1
                and s != 322]
    # TICKS: a tick fills the selected slot if empty, else the first empty, and
    # the selection moves on to the next empty slot; with the bar full it
    # REPLACES the selected slot; a tick of an id already on the bar changes
    # nothing and emits nothing; an untick clears EVERY slot holding the id (a
    # file may carry a duplicate); and to_spec is the slot order with the gaps
    # collapsed -- the file format the compiler reads, unchanged
    a_w, b_w, c_w = acting_w[:3]
    bar0.set_values([322])
    bar0.select_slot(0)
    del hits[:]
    # the first tick through the library row's BOX -- setCheckState, the
    # itemChanged path Qt's own click takes -- not the model method (the
    # verifier's b2: the box's branch made dead left every law green)
    next(it for it in bar0._items() if int(it.data(ROLE_ID)) == a_w).setCheckState(Qt.Checked)
    settle()
    step1 = (bar0.values(), bar0.current_slot(), len(hits))
    bar0.select_slot(4)
    del hits[:]
    bar0.tick(b_w)
    step2 = (bar0.values()[4], bar0.current_slot(), len(hits))
    del hits[:]
    bar0.tick(322)
    step3 = (bar0.values()[:2], len(hits))
    bar0.set_values([322, 322])
    del hits[:]
    bar0.untick(322)
    step4 = (bar0.values(), len(hits))
    full = acting_w[:8]
    bar0.set_values(full)
    bar0.select_slot(2)
    del hits[:]
    bar0.tick(acting_w[8])
    step5 = (bar0.values()[2] == acting_w[8], sorted(bar0.values()) == sorted(full[:2] + full[3:] + [acting_w[8]]),
             len(hits))
    bar0.set_values([322, 0, 323])
    saved = m0.to_spec()["skills"]
    check(len(acting_w) >= 9 and step1 == ([322, a_w, 0, 0, 0, 0, 0, 0], 2, 1) and step2 == (b_w, 5, 1)
          and step3 == ([322, a_w], 0) and step4 == ([0] * 8, 1) and step5 == (True, True, 1)
          and saved == [322, 323],
          f"a tick fills the selected slot if empty, else the first empty, and moves the selection "
          f"on ({step1[1:]}; slot 5 selected: {step2[1:]}); an id already on the bar ticks to "
          f"nothing ({step3[1]} signals); an untick clears both copies of a planted duplicate "
          f"({step4}); a full bar's tick replaces the selected slot ({step5}); and to_spec collapses "
          f"the gaps ({saved})")
    # DROPS (the Guild Wars idiom), as synthetic enter+drop events carrying the
    # bar's mime: a library row onto a cell places it, replacing; a skill
    # already on the bar MOVES (one copy); a cell onto another cell SWAPS; a
    # cell onto the library clears its slot; a foreign mime is ignored
    bar0.set_values([322, 0, 323])
    del hits[:]
    drop_on(bar0.strip, a_w, None, bar0.strip.cell_rect(3).center())
    d1 = (bar0.values()[3] == a_w, len(hits))
    drop_on(bar0.strip, 322, None, bar0.strip.cell_rect(5).center())
    d2 = (bar0.values()[0] == 0 and bar0.values()[5] == 322, len(hits))
    drop_on(bar0.strip, 323, 2, bar0.strip.cell_rect(5).center())
    d3 = (bar0.values()[2] == 322 and bar0.values()[5] == 323, len(hits))
    drop_on(bar0.list, 323, 5, QPoint(20, 20))
    d4 = (bar0.values()[5] == 0, len(hits))
    md = QMimeData()
    md.setText("hello")
    at = bar0.strip.cell_rect(0).center()
    QApplication.sendEvent(bar0.strip.viewport(), QDragEnterEvent(at, Qt.CopyAction, md, Qt.LeftButton,
                                                                  Qt.NoModifier))
    QApplication.sendEvent(bar0.strip.viewport(), QDropEvent(QPointF(at), Qt.CopyAction, md,
                                                             Qt.LeftButton, Qt.NoModifier))
    d5 = (bar0.values(), len(hits))
    # ...a cell mime naming a slot the strip has not (a crafted '322,12' once
    # raised inside dropEvent, '322,-1' swapped with slot 8) changes nothing;
    # and a cell from ANOTHER strip (its token, not this one's) is a PLACE of
    # its skill on the target, this strip's own slot 1 untouched -- not a
    # swap of this strip's two slots (the verifier's a9, 2026-09-24)
    raised = []
    for bad in (12, -1):
        try:
            drop_on(bar0.strip, 322, bad, bar0.strip.cell_rect(1).center())
        except Exception as exc:                 # noqa: BLE001
            raised.append(type(exc).__name__)
    d6 = (bar0.values(), len(hits), raised or None)
    drop_on(bar0.strip, b_w, 1, bar0.strip.cell_rect(6).center(), token="another window's strip")
    d7 = (bar0.values(), len(hits))
    check(d1 == (True, 1) and d2 == (True, 2) and d3 == (True, 3) and d4 == (True, 4)
          and d5 == ([0, 0, 322, a_w, 0, 0, 0, 0], 4) and d6 == ([0, 0, 322, a_w, 0, 0, 0, 0], 4, None)
          and d7 == ([0, 0, 322, a_w, 0, 0, b_w, 0], 5),
          f"a library row dropped on a cell is placed ({d1}), one already on the bar MOVES "
          f"({d2}), a cell on a cell swaps ({d3}), a cell on the library clears ({d4}), a "
          f"foreign mime changes nothing ({d5[1]} signals), a cell mime naming slot 12 or -1 "
          f"changes nothing and raises nothing ({d6[1:]}), and a cell from ANOTHER strip is a "
          f"place of its skill, not a swap ({d7[0]}, {d7[1]} signals); each write one signal")
    # the KEYBOARD path, which needs focus (a declared skip when the window
    # cannot hold it): Return in the search fills the first shown unticked row
    # and keeps the text and the focus, so Return again takes the next; Escape
    # clears; Down moves to the list, where Space toggles; on the strip 1..8
    # select, Delete clears, Ctrl+Right swaps, Return goes to the search
    no_focus = "the window could not hold keyboard focus"
    activate()
    bar0.set_values([])
    bar0.select_slot(0)
    bar0.filter.setText("")
    bar0.acts.setChecked(True)
    settle()
    if focus(bar0.filter):
        QTest.keyClicks(bar0.filter, "power att")
        QTest.keyClick(bar0.filter, Qt.Key_Return)
        settle()
        k1 = (bar0.values()[0], bar0.filter.text(), bar0.filter.hasFocus(), bar0.current_slot())
        bar0.filter.setText("")
        settle()
        expect = [s for s in bar0.visible_ids() if s != 322][:2]
        QTest.keyClick(bar0.filter, Qt.Key_Return)
        QTest.keyClick(bar0.filter, Qt.Key_Return)
        settle()
        k2 = bar0.values()[1:3]
        QTest.keyClicks(bar0.filter, "xyz")
        QTest.keyClick(bar0.filter, Qt.Key_Escape)
        k3 = bar0.filter.text()
        QTest.keyClick(bar0.filter, Qt.Key_Down)
        settle()
        first_row = next((it for it in bar0._items() if not it.isHidden()), None)
        k4 = (bar0.list.hasFocus(), bar0.list.currentItem() is first_row)
        QTest.keyClick(bar0.list, Qt.Key_Space)
        settle()
        k5 = int(first_row.data(ROLE_ID)) in bar0.values() if first_row is not None else None
        # ...and RETURN toggles the focused row too (DESIGN s2: Space / Return;
        # Qt gives Return to `activated` and ticked nothing -- the verifier's
        # a5), each press one signal
        del hits[:]
        QTest.keyClick(bar0.list, Qt.Key_Return)
        settle()
        k6 = (int(first_row.data(ROLE_ID)) in bar0.values(), len(hits))
        QTest.keyClick(bar0.list, Qt.Key_Return)
        settle()
        k6 += (int(first_row.data(ROLE_ID)) in bar0.values(), len(hits))
        check(k1 == (322, "power att", True, 1) and k2 == expect and k3 == "" and k4 == (True, True)
              and k5 is False and k6 == (True, 1, False, 2),
              f"Return in the search fills the first shown skill and keeps the text and the focus "
              f"({k1}), Return again takes the next two ({k2} = {expect}), Escape clears "
              f"({k3!r}), Down moves to the list's first shown row ({k4}) where Space unticks it "
              f"({k5}) and Return ticks it again and unticks it, one signal each ({k6})")
    else:
        skip("the search box's Return, Escape and Down", no_focus)
    bar0.set_values([322, 0, 323, a_w])
    if focus(bar0.strip):
        QTest.keyClick(bar0.strip, Qt.Key_3)
        s1 = bar0.current_slot()
        QTest.keyClick(bar0.strip, Qt.Key_Right, Qt.ControlModifier)
        s2 = (bar0.values(), bar0.current_slot())
        QTest.keyClick(bar0.strip, Qt.Key_Delete)
        s3 = bar0.values()
        QTest.keyClick(bar0.strip, Qt.Key_Return)
        settle()
        s4 = bar0.filter.hasFocus()
        check(s1 == 2 and s2 == ([322, 0, a_w, 323, 0, 0, 0, 0], 3) and s3 == [322, 0, a_w, 0, 0, 0, 0, 0]
              and s4,
              f"on the strip 3 selects slot 3 ({s1 + 1}), Ctrl+Right swaps it with slot 4 and follows "
              f"it ({s2}), Delete empties it ({s3}) and Return moves to the search ({s4})")
    else:
        skip("the strip's 1..8, Delete, Ctrl+Right and Return", no_focus)
    # A 200-CHARACTER SKILL NAME, planted in memory (--smoke only, restored
    # after): tomorrow's content, which the fit laws over today's cannot see.
    # It draws elided in its cell -- the ink stops inside the name rect, read
    # off the window -- the strip's height unchanged, the whole on the cell's
    # hover and the library row's, and a word from its middle finds the row
    keep_name = win.names.skill.get(322)
    win.names.skill[322] = SMOKE_LONG_SKILL
    bar0.set_values([322])
    bar0.select_slot(1)
    bar0.set_professions((1,))                   # the library's rows carry the planted name
    settle(4)
    h_before = bar0.strip.height()
    it0 = bar0.strip.item(0)
    parts0 = it0.data(ROLE_PARTS)
    cell0 = bar0.strip.cell_rect(0)
    _w0, _n, name0, _m, _p = orchui.SlotStrip.layout(cell0, parts0, body_fm=bar0.strip.fontMetrics(),
                                                     meta_fm=meta_fm)
    # elided, not CLIPPED: drawText clips to its rect, so the ink of an unelided
    # name ends inside the rect too. The cell painted with the long name must
    # equal, pixel for pixel, the cell painted with its elided string -- the
    # ellipsis, where a clipped name shows a cut glyph
    box = QRect(bar0.strip.viewport().mapTo(win, name0.topLeft()), name0.size())
    long_img = win.grab().toImage().copy(box)
    shown0 = bar0.strip.fontMetrics().elidedText(SMOKE_LONG_SKILL, Qt.ElideRight, name0.width())
    it0.setData(ROLE_PARTS, (shown0, parts0[1], parts0[2]))
    settle(3)
    elided_img = win.grab().toImage().copy(box)
    it0.setData(ROLE_PARTS, parts0)
    settle(2)
    same = _diff(long_img, elided_img)
    # ...with a POSITIVE floor: a blank name rect equals a blank name rect (0
    # px apart), so the equality alone passed a delegate that painted no name
    # (the verifier's b1, 2026-09-24) -- the rect must carry the glyphs' ink
    name_ink = _ink_pixels(long_img, pal["field"], orchtheme.TEXT_FLOOR)
    lib_row = next((it for it in bar0._items() if int(it.data(ROLE_ID)) == 322), None)
    bar0.filter.setText("gravelbeard")
    settle()
    found = bar0.visible_ids()
    bar0.filter.setText("")
    check(len(SMOKE_LONG_SKILL) >= 200 and same == 0 and name_ink > 60 and shown0.endswith("…")
          and shown0 != SMOKE_LONG_SKILL and bar0.strip.height() == h_before
          and SMOKE_LONG_SKILL in it0.toolTip()
          and lib_row is not None and SMOKE_LONG_SKILL in lib_row.toolTip() and found == [322],
          f"a {len(SMOKE_LONG_SKILL)}-character skill name draws ELIDED in its cell (painted as its "
          f"elided string is, {same} px apart, {name_ink} px of ink; {shown0[-8:]!r}), the strip's "
          f"height unchanged ({bar0.strip.height()}), the whole name on the cell's and the library "
          f"row's hover, and 'gravelbeard' typed into the search finds that row alone ({found})")
    # LINE 2 off the pixels, the pill law's treatment and control: the meta
    # rect loses ink when orchui.elide_rank_line answers '' (so the painter
    # draws line 2 THROUGH the helper: a delegate painting no line 2 passed
    # every law, the verifier's b1); and on the Monk's 'Protection Prayers 1'
    # -- 141 px in a 131 px room at 1,280, measured -- the painted rect
    # EQUALS the rect painted with the helper's own output as the line (a
    # string that fits, so the helper leaves it), and DIFFERS from the rect
    # painted with the right-elided string: the rank the cell shows is the
    # one law 2 scores, not a right elision that took the digits
    m1 = en.groups[0].members[1]
    en.select(m1)
    settle(4)
    bar1 = m1.bar
    monk_i = next((i for i, s in enumerate(bar1.values())
                   if s and meta_fm.horizontalAdvance(bar1.strip.item(i).data(ROLE_SLOT)[1])
                   > orchui.SlotStrip.layout(bar1.strip.cell_rect(i), bar1.strip.item(i).data(ROLE_PARTS),
                                             body_fm=bar1.strip.fontMetrics(), meta_fm=meta_fm)[3].width()),
                  None)
    if monk_i is not None:
        it1 = bar1.strip.item(monk_i)
        slot1, parts1 = it1.data(ROLE_SLOT), it1.data(ROLE_PARTS)
        meta1 = orchui.SlotStrip.layout(bar1.strip.cell_rect(monk_i), parts1,
                                        body_fm=bar1.strip.fontMetrics(), meta_fm=meta_fm)[3]
        mbox = QRect(bar1.strip.viewport().mapTo(win, meta1.topLeft()), meta1.size())
        painted = win.grab().toImage().copy(mbox)
        real_elide = orchui.elide_rank_line
        orchui.elide_rank_line = lambda _fm, _t, _w: ""
        bar1.strip.viewport().update()
        settle(3)
        blank = win.grab().toImage().copy(mbox)
        orchui.elide_rank_line = real_elide
        kept = real_elide(meta_fm, slot1[1], meta1.width())
        it1.setData(ROLE_SLOT, (slot1[0], kept, slot1[2]))
        settle(3)
        as_kept = win.grab().toImage().copy(mbox)
        it1.setData(ROLE_SLOT, (slot1[0], meta_fm.elidedText(slot1[1], Qt.ElideRight, meta1.width()), slot1[2]))
        settle(3)
        as_right = win.grab().toImage().copy(mbox)
        it1.setData(ROLE_SLOT, slot1)
        settle(2)
        l2 = (_diff(painted, blank), _diff(painted, as_kept), _diff(painted, as_right),
              kept.split(" ")[-1] == slot1[1].split(" ")[-1], kept != slot1[1])
        check(l2[0] > 60 and l2[1] == 0 and l2[2] > 20 and l2[3] and l2[4],
              f"line 2 is painted through elide_rank_line: the Monk's {slot1[1]!r} loses {l2[0]} px "
              f"of ink with the helper answering '', and the painted rect equals one painted with "
              f"the helper's own {kept!r} ({l2[1]} px apart) and differs from a right elision "
              f"({l2[2]} px) -- the rank on screen is the one the fit law scores")
    else:
        skip("line 2 is painted through elide_rank_line", "no Monk cell whose line 2 elides at 1,280")
    en.select(m0)
    settle(4)
    if keep_name is None:
        del win.names.skill[322]
    else:
        win.names.skill[322] = keep_name
    bar0.set_professions((1,))
    # the empty-filter PLACEHOLDER names the way out: with the box ticked and a
    # search matching no acting row but some unmarked one, the untick sentence
    # with the count (the rows the search matches with the box off), rendered;
    # unticked, the rows show; a search matching nothing, the plain sentence
    unmarked = next((s for s in sandbox.default_unlocks(win.names.world, (1,))
                     if s not in acting and win.names.skill.get(s)
                     and list(win.names.skill.values()).count(win.names.skill[s]) == 1), None)
    if unmarked:
        bar0.acts.setChecked(True)
        bar0.filter.setText(win.names.skill_parts(unmarked)[0])
        settle(3)
        vp = bar0.list.viewport()
        ph_text, ph_shown = bar0.list.placeholder, bar0.list.visible_count()
        ph_px = _count_near(vp.grab().toImage(), pal["muted"], 24, (0, 0, vp.width(), 60))
        bar0.acts.setChecked(False)
        settle()
        n_off = bar0.list.visible_count()
        bar0.filter.setText("no skill is called this")
        settle()
        ph_none = bar0.list.placeholder
        bar0.filter.setText("")
        bar0.acts.setChecked(True)
        settle()
        # ...'to see it' for one match, 'to see all N' for more (never 'all 1':
        # the verifier's c10); the one-match arm searched by the row's exact
        # name, the item text's 'name  [' prefix
        bar0.acts.setChecked(True)
        bar0.filter.setText(win.names.skill_parts(unmarked)[0] + "  [")
        settle(3)
        bar0.acts.setChecked(False)
        settle()
        one = (bar0.list.visible_count(), None)
        bar0.acts.setChecked(True)
        settle()
        one = (one[0], bar0.list.placeholder)
        bar0.filter.setText("")
        settle()
        sentence = lambda n: f"No acting skill matches; untick Modelled or label to see {'it' if n == 1 else f'all {n}'}."  # noqa: E731
        check(ph_shown == 0 and n_off >= 1 and ph_text == sentence(n_off)
              and ph_px > 30 and ph_none == "No skill matches this filter."
              and one == (1, sentence(1)) and one[1].endswith("to see it.")
              and SkillBar.untick_sentence(3).endswith("to see all 3."),
              f"with the box ticked and a search matching only unmarked rows the library paints "
              f"the way out ({ph_text!r}, {ph_px} px of it; unticked shows {n_off}), 'to see it' "
              f"for one match ({one}), and a search matching nothing the plain sentence "
              f"({ph_none!r})")
    else:
        skip("the placeholder names the way out", "no unmarked Warrior or common skill with a name")
    # the ATTRIBUTES ROW CHIPS count the bar and say the rank the server acts
    # at: the raider [322] gives Strength '1 on the bar' and no other chip, the
    # boss [322, 323] Strength and Tactics; no example chip is WARN (every used
    # attribute is ranked: the control); clearing the slot removes it; every
    # spin at 0 (a template with no ranks) gives 'acting at 12' and
    # sandbox.effective_rank agrees; then Hammer Mastery 3 alone turns
    # Strength's chip WARN 'at rank 0' and the cell's line 2 'Strength 0' --
    # the trap worth showing; and a rank edit updates line 2 at once
    bar0.changed.disconnect(tally)
    m0.from_spec(m0_spec)
    settle(4)
    if m0.ranks.spins:
        boss0 = en.groups[2].members[0]
        rows_of = lambda ed: {a: (rc.text(), rc.property("kind")) for a, rc in ed.ranks.row_chips.items()  # noqa: E731
                              if not rc.isHidden()}       # the flag: a page off the stack is not visible
        raider_chips, boss_chips = rows_of(m0), rows_of(boss0)
        no_warn = all(kind == "info" for ed in eds for _t, kind in rows_of(ed).values())
        one_per_row = len({m0.ranks.grid.getItemPosition(m0.ranks.grid.indexOf(sp))[0]
                           for sp in m0.ranks.spins.values()}) == len(m0.ranks.spins)
        m0.bar.clear_slot(0)
        settle()
        after_clear = rows_of(m0)
        m0.bar.set_values([322])
        for sp in m0.ranks.spins.values():
            sp.setValue(0)
        settle()
        at12 = (rows_of(m0), m0.bar.strip.item(0).data(ROLE_SLOT)[1],
                sandbox.effective_rank([], m0.template_pairs(), 17))
        m0.ranks.spins[19].setValue(3)
        settle()
        at0 = (rows_of(m0), m0.bar.strip.item(0).data(ROLE_SLOT)[1])
        m0.ranks.spins[17].setValue(5)
        settle()
        at5 = (m0.bar.strip.item(0).data(ROLE_SLOT)[1], m0.bar.strip.item(0).text())
        # ...and the TEMPLATE's own ranks as the fallback: no content npc row
        # carries `attributes` (the `attributes =` lines in world.toml are
        # spawn rows), so the only state the smoke reached was 'no ranks
        # anywhere' and template_pairs answering [] passed every law (the
        # verifier's b7). Planted IN MEMORY on the raider's template row and
        # put back: with every spin at 0 the cell reads the template's rank,
        # the row chip counts with no WARN, and sandbox.effective_rank agrees
        tmpl_row = win.names.world.rows("npc")["bandit_raider"]
        kept_attrs = tmpl_row.get("attributes", None)      # None: no such key today (0 of 63 rows)
        tmpl_row["attributes"] = [[17, 4]]
        m0.from_spec(dict(m0_spec, attributes=None))
        settle(4)
        for sp in m0.ranks.spins.values():
            sp.setValue(0)
        settle()
        via_tmpl = (rows_of(m0), m0.bar.strip.item(0).data(ROLE_SLOT)[1],
                    sandbox.effective_rank([], m0.template_pairs(), 17), m0.template_pairs(),
                    m0.bar.strip.item(0).toolTip().splitlines()[-1])
        if kept_attrs is None:
            del tmpl_row["attributes"]
        else:
            tmpl_row["attributes"] = kept_attrs
        m0.from_spec(m0_spec)
        settle(4)
        check(raider_chips == {17: ("1 on the bar", "info")}
              and boss_chips == {17: ("1 on the bar", "info"), 21: ("1 on the bar", "info")}
              and no_warn and one_per_row and after_clear == {},
              f"the Attributes row chips count the bar, one attribute to a row: the raider's "
              f"Strength '1 on the bar' and no other ({raider_chips}), the boss's Strength and "
              f"Tactics ({boss_chips}), none WARN on the example (the control), and clearing the "
              f"slot removes it ({after_clear})")
        check(at12 == ({17: ("1 on the bar, acting at 12", "info")}, "Strength 12", 12)
              and at0 == ({17: ("1 on the bar, at rank 0", "warn")}, "Strength 0")
              and at5 == ("Strength 5", f"Slot 1: {win.names.slot_label(322)}, Strength 5"),
              f"with every rank at 0 Strength's chip reads 'acting at 12' and the cell 'Strength "
              f"12' as sandbox.effective_rank says ({at12}); Hammer Mastery 3 alone turns it WARN "
              f"'at rank 0' and the cell 'Strength 0' ({at0}); Strength 5 rewrites line 2 at once "
              f"({at5[0]!r})")
        check(via_tmpl[:4] == ({17: ("1 on the bar", "info")}, "Strength 4", 4, [[17, 4]])
              and "template's own rank" in via_tmpl[4] and m0.template_pairs() == [],
              f"with every spin at 0 and `attributes = [[17, 4]]` planted on the raider's TEMPLATE "
              f"(in memory, put back), the cell reads 'Strength 4', the row chip '1 on the bar' "
              f"with no WARN, the hover says it is the template's, and sandbox.effective_rank "
              f"agrees ({via_tmpl[:3]}; the template's ranks after the restore: {m0.template_pairs()})")
        # ...and the label column holds the widest label of any profession the
        # content offers a BODY for whole at 1,000 px -- today the
        # Elementalist's 'Energy Storage  primary' (145 px, measured). The
        # widest label over EVERY profession is the Ritualist's 'Spawning
        # Power  primary' (154 px, the column's own width), and no template
        # has a Ritualist body; the column's floor covers it all the same
        # (the verifiers' b11 / c3: this comment once named the Ranger's
        # 'Wilderness Survival', neither the widest nor a primary)
        probe = QLabel(m0.ranks)
        by_prof = {}
        for aid, arow in m0.ranks.rules.attributes.items():
            probe.setText(m0.ranks._label_text(aid, arow["is_primary"]))
            by_prof.setdefault(arow["profession"], []).append((probe.sizeHint().width(), aid))
        probe.deleteLater()
        widest_p = max((p for p in byprof if p in by_prof), key=lambda p: max(by_prof[p]), default=None)
        if widest_p is not None:
            want_w, want_aid = max(by_prof[widest_p])
            win.resize(1000, 720)
            settle(8)
            m0.template.set_value(byprof[widest_p])
            settle(4)
            en.select(m0)
            settle(4)
            labs = [m0.ranks.grid.itemAtPosition(r, 0).widget() for r in range(len(m0.ranks.spins))]
            widest = max(labs, key=lambda lab: lab.sizeHint().width())
            whole = [(lab.text()[:24], lab.width(), lab.sizeHint().width()) for lab in labs
                     if lab.width() < lab.sizeHint().width()]
            over_all = max(w for rows_ in by_prof.values() for w, _a in rows_)
            check(not whole and widest.sizeHint().width() == want_w and win.names.attr_label(want_aid)
                  in widest.text() and widest.width() >= widest.sizeHint().width()
                  and m0.ranks.label_col >= over_all,
                  f"at 1,000 px the widest attribute label among the bodies the content offers "
                  f"({widest.text()[:30]!r}, {want_w} px, {sandbox.PROFESSIONS.get(widest_p)}) "
                  f"stands whole in the {m0.ranks.label_col} px column, which is measured over "
                  f"every profession ({over_all} px; cut: {whole or 'none'})")
            m0.from_spec(m0_spec)
            win.resize(1280, 860)
            settle(8)
        else:
            skip("the widest attribute label at 1,000 px", "no profession body among the templates")
    else:
        skip("the Attributes row chips count the bar", "no attribute table, so no ranks")
        skip("the row chips say the rank the server acts at", "no attribute table, so no ranks")
        skip("a template's own ranks are the cell's fallback", "no attribute table, so no ranks")
        skip("the widest attribute label at 1,000 px", "no attribute table, so no ranks")
    en.select(m0)
    settle(4)
    # a skill with NO attribute whose numbers still VARY with a rank (Light of
    # Deldrimor 2212: 55..80 Holy damage, attribute 51; four acting rows) is
    # scaled by the server at the no-attribute id -- 0 with any rank set, 12
    # with none -- and its cell says that rank, where 'nothing about it
    # scales' was a false sentence over a 55-or-75 (the verifier's a2); a
    # no-attribute skill with nothing varying keeps that sentence; and the
    # chip's hover claims 'rank 0' only for an off-profession skill that
    # CARRIES an attribute -- 102 profession skills have none (c5)
    varying = next((s for s in sorted(acting) if sandbox.skill_attribute(win.world, s) is None
                    and sandbox.skill_varies(win.world, s) and win.names.skill_profession(s) in (0, 1)), None)
    flat = next((s for s in sorted(acting) if sandbox.skill_attribute(win.world, s) is None
                 and not sandbox.skill_varies(win.world, s) and win.names.skill_profession(s) in (0, 1)), None)
    off_noattr = next((s for s in sorted(win.world.rows("skills"), key=int)
                       if win.names.skill_profession(int(s)) not in (0, 1)
                       and sandbox.skill_attribute(win.world, int(s)) is None), None)
    if varying and flat and off_noattr and m0.ranks.spins:
        m0.bar.set_values([322, varying, flat])
        settle()
        cells = lambda: (m0.bar.strip.item(1).data(ROLE_SLOT)[1], m0.bar.strip.item(1).toolTip().splitlines()[-1],  # noqa: E731
                         m0.bar.strip.item(2).data(ROLE_SLOT)[1], m0.bar.strip.item(2).toolTip().splitlines()[-1])
        ranked_c = cells() + (sandbox.effective_rank(m0.ranks.ranks(), m0.template_pairs(), sandbox.NO_ATTRIBUTE),)
        for sp in m0.ranks.spins.values():
            sp.setValue(0)
        settle()
        none_c = cells() + (sandbox.effective_rank(m0.ranks.ranks(), m0.template_pairs(), sandbox.NO_ATTRIBUTE),)
        m0.bar.set_values([322, int(off_noattr)])
        settle()
        tip_noattr = (m0.bar.chip.text(), m0.bar.chip.toolTip())
        m0.bar.set_values([322, 281])
        settle()
        tip_attr = (m0.bar.chip.text(), m0.bar.chip.toolTip())
        m0.from_spec(m0_spec)
        settle(4)
        check(ranked_c[0] == "No attribute 0" and "scales it at 0" in ranked_c[1] and ranked_c[4] == 0
              and none_c[0] == "No attribute 12" and "scales it at 12" in none_c[1] and none_c[4] == 12
              and ranked_c[2] == "No attribute" == none_c[2]
              and ranked_c[3] == "No attribute: nothing about it scales with a rank." == none_c[3],
              f"a no-attribute skill that VARIES (skill {varying}) reads 'No attribute 0' with the "
              f"raider's ranks set and 'No attribute 12' with none, its hover saying the server "
              f"scales it so, as sandbox.effective_rank at NO_ATTRIBUTE says ({ranked_c[4]}, "
              f"{none_c[4]}); a flat one (skill {flat}) reads 'No attribute' and 'nothing scales' "
              f"either way ({ranked_c[0]!r}, {none_c[0]!r}, {ranked_c[2]!r})")
        check(tip_noattr[0].endswith("1 of another profession") and "no rank is lost" in tip_noattr[1]
              and "rank 0" not in tip_noattr[1]
              and tip_attr[0].endswith("1 of another profession") and "acts at rank 0" in tip_attr[1],
              f"the chip's hover claims rank 0 only for an off-profession skill that carries an "
              f"attribute (Orison: {tip_attr[1][:60]!r}); for one with none (skill {off_noattr}) "
              f"it says no rank is lost ({tip_noattr[1][:70]!r})")
    else:
        skip("a no-attribute skill that varies shows the rank the server scales it at",
             f"no such rows in the table (varying {varying}, flat {flat}, off-profession "
             f"no-attribute {off_noattr}) or no ranks")
        skip("the chip's hover claims rank 0 only for a skill with an attribute", "the same")
    # a group page and a hostile page share one right edge whether or not the
    # hostile's page scrolls: at 860 tall it does, and at its OWN height plus
    # the window's chrome it does not (the inline library made the page taller
    # than a 1080p screen, so the no-scroll arm is run at the height the page
    # fits: a hidden window resizes past the screen here -- measured -- and a
    # machine whose OS clamps it declares the skip); a fixed reserve matched
    # only the first
    page0 = en._pages[m0]
    win.resize(1280, 860)
    settle(8)
    en.select(m0)
    settle(4)
    tall = page0.widget().sizeHint().height() + (win.height() - page0.viewport().height()) + 8
    edges = {}
    for h in (860, tall):
        win.resize(1280, h)
        settle(8)
        got = []
        for ed in (g, m0):
            en.select(ed)
            settle(4)
            got.append(ed.remove_b.mapTo(win, QPoint(ed.remove_b.width(), 0)).x())
        edges[h] = (got[0], got[1], page0.verticalScrollBar().maximum() > 0, win.height())
    check(edges[860][0] == edges[860][1] and edges[860][2],
          f"a group page's Remove and a hostile page's end at one x at 860 tall, the hostile page "
          f"scrolling (group, hostile, scrolls: {edges[860][:3]})")
    if edges[tall][3] >= tall:
        check(edges[tall][0] == edges[tall][1] and not edges[tall][2],
              f"...and at the hostile page's own height ({tall} px) they end at one x with the "
              f"page NOT scrolling (group, hostile, scrolls: {edges[tall][:3]})")
    else:
        skip("the two pages end at one x with the hostile page not scrolling",
             f"the OS clamped the hidden window to {edges[tall][3]} px of the {tall} the page needs")
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
    pk = en.groups[0].members[0].weapon_item      # a Picker on the page (the slots are cells now)
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
    # LAUNCH_STATUS and nothing appended (a launch is not driven here) -- the
    # LAST setText on the status, off the syntax tree, so neither the old
    # line kept in a comment nor a later call appending to it passes
    sets = [c for c in source_calls(RunTab._start) if dotted(c.func) == "self.status.setText"]
    check(bool(sets) and len(sets[-1].args) == 1 and _is_name(sets[-1].args[0], "LAUNCH_STATUS"),
          f"and the launch's say site puts that constant on the line, whole: the last setText "
          f"in _start is the name alone ({len(sets)} setText call(s), read off the syntax tree)")
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

    # five acting Warrior skills not on the raider's bar, for the bar's edits
    spare_w = [s for s in sorted(win.names.modelled) if win.names.skill_profession(s) == 1
               and s not in m0.bar.values()][:5]
    bar_emits = []
    m0.bar.changed.connect(lambda: bar_emits.append(1))

    def lib_item(sid):
        return next(it for it in m0.bar._items() if int(it.data(ROLE_ID)) == sid)

    def os_double_click(where, sid):
        """A double-click as Windows delivers one -- press, release, double-
        click, release -- on the row's TEXT (past the box) or on its BOX, sent
        to the library's viewport; QTest.mouseDClick sends the double-click
        alone, which is not the owner's sequence (the verifiers' a6 / c6)."""
        it = lib_item(sid)
        m0.bar.list.scrollToItem(it)
        settle(2)
        r = m0.bar.list.visualItemRect(it)
        pos = QPoint(r.right() - 40, r.center().y()) if where == "text" else m0.bar.list.check_rect(it).center()
        vp = m0.bar.list.viewport()
        g = vp.mapToGlobal(pos)
        for kind, buttons in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton),
                              (QEvent.MouseButtonDblClick, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
            QApplication.sendEvent(vp, QMouseEvent(kind, QPointF(pos), QPointF(g), Qt.LeftButton, buttons,
                                                   Qt.NoModifier))
        settle(2)
    edits = [("party weapon", lambda: turn(win.party.weapon)),
             ("party off-hand", lambda: turn(win.party.offhand, skip_first=True)),
             ("a hero's body", lambda: win.party.rows[3][2].set_value("hatcher")),
             ("health", lambda: m0.health.setValue(m0.health.value() + 1)),
             ("weapon item", lambda: turn(m0.weapon_item)),
             ("attack interval", lambda: m0.speed.setValue(1.25)),
             ("damage high", lambda: m0.dhi.setValue(40)),
             ("damage low", lambda: m0.dlo.setValue(7)),
             ("skill slot 8", lambda: m0.bar.set_slot(7, spare_w[0])),
             # the owner's MOUSE paths, as Qt delivers them -- the row's box
             # through setCheckState (itemChanged, exactly as a click), a
             # double-click on the row's text, and one on its box (Qt's own
             # toggle, which _double must not double: a net single toggle) --
             # not the model method, which left both paths' wiring unread
             # (the verifiers' b2 / a6 / c6, 2026-09-24)
             ("a tick of a library row's box", lambda: lib_item(spare_w[1]).setCheckState(Qt.Checked)),
             ("a double-click on a library row's text", lambda: os_double_click("text", spare_w[3])),
             ("a double-click on a library row's box", lambda: os_double_click("box", spare_w[4])),
             ("Clear slot", lambda: (m0.bar.select_slot(7), m0.bar.clear_b.click())),
             ("a slot swap", lambda: m0.bar.swap(0, 1)),
             ("a drop on slot 3", lambda: drop_on(m0.bar.strip, spare_w[2], None,
                                                  m0.bar.strip.cell_rect(2).center())),
             ("Delete on the strip", lambda: (m0.bar.select_slot(2), key_on(m0.bar.strip, Qt.Key_Delete))),
             ("the boss's glow", lambda: boss.glow.setValue(boss.glow.value() + 1)),
             ("hold", lambda: win.run.hold.setValue(30)),
             ("template", lambda: m0.template.set_value("academy_monk"))]
    BAR_EDITS = {"skill slot 8", "a tick of a library row's box", "a double-click on a library row's text",
                 "a double-click on a library row's box", "Clear slot", "a slot swap", "a drop on slot 3",
                 "Delete on the strip"}
    took = {}                                    # what each double-click wrote (a tick, never two)
    if m0.ranks.spins:
        # a rank, and a rank on the spins a template change REBUILDS -- down
        # where it can, up from 0 (either is an edit; a hostile has no budget
        # for one more point to breach)
        def rank():
            sp = next(iter(m0.ranks.spins.values()))
            sp.setValue(sp.value() - 1 if sp.value() else 1)
        edits.insert(9, ("attribute rank", rank))
        edits.append(("attribute rank after the template change", rank))
    stayed, stale_rows, twice = [], [], []
    for label, edit in edits:
        win.run.compile()
        fresh = win.run.state.text().startswith("Compiled")
        del bar_emits[:]
        edit()
        settle()
        if not (fresh and win.run.state.text() == "Changed since compile"):
            stayed.append(label)
        if label not in ("party weapon", "party off-hand", "a hero's body", "hold") \
                and not g0.roster.item(0).text().endswith(m0.summary()):
            stale_rows.append(label)
        if label in BAR_EDITS and len(bar_emits) != 1:
            twice.append((label, len(bar_emits)))
        if label.startswith("a double-click"):
            took[label] = (spare_w[3] if label.endswith("text") else spare_w[4]) in m0.bar.values()
    check(not stayed, f"each of {len(edits)} spec inputs turns a fresh 'Compiled' into 'Changed "
                      f"since compile' (left green: {stayed or 'none'})")
    check(not stale_rows, f"and a hostile's edit reaches its roster line at once "
                          f"(stale after: {stale_rows or 'none'})")
    check(len(spare_w) == 5 and not twice and len(took) == 2 and all(took.values()),
          f"and each of the Skill bar's {len(BAR_EDITS)} write paths -- a slot set, a row's box "
          f"ticked, a double-click on a row's text and on its box, Clear slot, a swap, a drop, "
          f"Delete -- emits `changed` exactly once, each double-click a single tick (not once: "
          f"{twice or 'none'}; ticked: {took})")
    win.run.hold.setValue(0)
    # a view of the same spec is not an edit: the Skills filters leave the chip
    # green, and so do the Skill bar's search, offered-set combo and checkbox
    # (and none of them emits the bar's `changed`), while an unlock still turns it
    win.tabs.setCurrentWidget(win.skills)
    turned = []
    for label, act in (("filter text", lambda: win.skills.filter.setText("heal")),
                       ("profession filter", lambda: win.skills.prof.setCurrentIndex(1)),
                       ("'modelled or label'", lambda: win.skills.modelled_only.setChecked(True)),
                       ("the Skill bar's search", lambda: m0.bar.filter.setText("heal")),
                       ("the Skill bar's offered set", lambda: set_combo(m0.bar.prof, 0)),
                       ("the Skill bar's 'Modelled or label'", lambda: m0.bar.acts.setChecked(False))):
        win.run.compile()
        before = win.to_spec()
        del bar_emits[:]
        act()
        settle()
        if not win.run.state.text().startswith("Compiled") or win.to_spec() != before or bar_emits:
            turned.append(label)
    win.skills.filter.setText("")
    win.skills.prof.setCurrentIndex(0)
    win.skills.modelled_only.setChecked(False)
    m0.bar.filter.setText("")
    set_combo(m0.bar.prof, -2)
    m0.bar.acts.setChecked(True)
    settle()
    win.run.compile()
    first = next(it for it in win.skills._items() if not it.isHidden())
    first.setCheckState(Qt.Unchecked if first.checkState() == Qt.Checked else Qt.Checked)
    settle()
    unlock_turned = win.run.state.text() == "Changed since compile"
    first.setCheckState(Qt.Unchecked if first.checkState() == Qt.Checked else Qt.Checked)
    settle()
    check(not turned and unlock_turned,
          f"the Skills filters and the Skill bar's search, offered set and checkbox leave a fresh "
          f"'Compiled' green and emit no change (turned it: {turned or 'none'}), and one unlock "
          f"turns it")
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
    # a hostile is EXEMPT from a player's point budget (the owner's ruling,
    # 2026-09-24, PLAN-LOG: retail foes and bosses exceed it): ranks past its
    # level's budget COMPILE, the chip counts the spend and never judges it,
    # and the hint claims no refusal. (For one day this law read the reverse,
    # the rule the hint had promised before validate had it.)
    if m0.ranks.spins:
        sp = next(iter(m0.ranks.spins.values()))
        keep = sp.value()
        sp.setValue(sp.maximum())
        win.run.compile()
        chip_said = (m0.ranks.chip.text(), m0.ranks.chip.property("kind"), win.run.state.text())
        over = m0.ranks.spent() > sandbox.budget_for_level(m0.level.value())
        compiled = (win.run.compiled is not None and chip_said[2].startswith("Compiled")
                    and "points; level" not in win.run.summary.toPlainText())
        hint = m0.ranks.hint.text()
        settle()
        line, summ = g0.roster.item(0).text(), m0.summary()
        said = n_of(m0.ranks.spent(), "point")
        sp.setValue(keep)
        # the spin's maximum is past the cost table (21 against 12), so the
        # chip's words at it are the priced part and the count past the
        # table; the 12-against-15 law below pins the wording
        at_max = m0.ranks.rules.total_spent(
            {a: (sp.maximum() if a == next(iter(m0.ranks.spins)) else s.value())
             for a, s in m0.ranks.spins.items()})
        check(over and compiled and chip_said[1] == "info" and "over budget" not in chip_said[0]
              and chip_said[0].startswith(n_of(at_max, "point")) and "past it, not priced" in chip_said[0]
              and "refuse" not in hint and "point budget" in hint,
              f"a hostile's ranks past its level's budget COMPILE (a hostile is exempt), the chip "
              f"counts the spend without judging it ({chip_said[0]!r}, {chip_said[1]}; "
              f"{chip_said[2]!r}) and the hint claims no refusal")
        # ...and the group's roster line says the same: the spend alone, the
        # exact n_of token, never 'N of B points' (the budget form the line
        # had; the change law above compares the line with summary() itself,
        # so it could not tell a count from a budget put back)
        check(over and said in summ and line.endswith(summ)
              and re.search(r"\d+ of \d+ points?", line) is None,
              f"...and its roster line carries the spend alone ({said!r}), never 'N of B "
              f"points' -- a hostile has no budget to be 'of' ({summ!r})")
        # ...and the KEPT rules still refuse a hostile's ranks at compile: a
        # file whose first hostile carries an attribute of another profession
        # and a rank past HOSTILE_RANK_MAX (22: the cap is 21 since the lift,
        # no longer the table's 12) opens (the card offers neither -- the
        # foreign id is dropped, the rank clamped by the spin), and the bar
        # says what the compiler refused, so the exemption opened nothing else
        rules = m0.ranks.rules
        foreign = next(a for a, row in sorted(rules.attributes.items())
                       if row["profession"] not in m0.ranks.professions and not row["is_primary"])
        mine = next(iter(m0.ranks.spins))
        held_spec = win.to_spec()
        g1 = held_spec["groups"][0]
        bad = dict(held_spec, name="smoke-hostileranks",
                   groups=[dict(g1, members=[dict(g1["members"][0],
                                                  attributes=[[foreign, 1],
                                                              [mine, sandbox.HOSTILE_RANK_MAX + 1]])]
                                + g1["members"][1:])] + held_spec["groups"][1:])
        bad_path = os.path.join(out_dir, "smoke_hostileranks.toml")
        with open(bad_path, "w", encoding="utf-8") as fh:
            fh.write(sandbox.spec_toml(bad))
        kept = [q for q in sandbox.validate(bad, win.world) if "member 1.attributes" in q]
        win.run.load(bad_path)
        settle()
        msg = win.statusBar().currentMessage()
        held_now = win.to_spec()
        check(len(kept) == 2 and any("belongs to profession" in q for q in kept)
              and any(f"outside 0..{sandbox.HOSTILE_RANK_MAX}" in q for q in kept)
              and not sandbox.validate(held_now, win.world)
              and held_now["groups"][0]["members"][0]["level"] == held_spec["groups"][0]["members"][0]["level"]
              and msg.startswith("Opened smoke_hostileranks, but the window could not hold all of "
                                 "it (2 changes: "),
              f"...and a hostile's ranks are still held to VALIDITY: a file with an attribute of "
              f"another profession and a rank past {sandbox.HOSTILE_RANK_MAX} on one hostile is "
              f"refused for both at compile, the card holds neither, and the bar says so "
              f"({msg[:88]!r})")
        win.from_spec(held_spec)
        settle()
    else:
        skip("an over-budget hostile compiles (exempt)", "no attribute table, so no ranks")
        skip("a hostile's roster line counts, never 'of'", "no attribute table, so no ranks")
        skip("the kept rules still refuse a hostile's ranks", "no attribute table, so no ranks")
    # the hostile caps LIFTED -- the owner's second ruling of 2026-09-24, "lift
    # the rank and level caps for hostiles too": the Ranks spins 0..21
    # (sandbox.HOSTILE_RANK_MAX, retail's ceiling) and the Level spin 0..255
    # (HOSTILE_LEVEL_MAX, the 0x0056 level byte), the same constants validate
    # reads, so Open holds a high file WHOLE and says what it cannot hold.
    # The editors are rebuilt by every from_spec, so m0 is re-fetched after
    # each load
    m0 = en.groups[0].members[0]
    if m0.ranks.spins:
        rules = m0.ranks.rules
        check(all(s.maximum() == 21 and s.minimum() == 0 for s in m0.ranks.spins.values())
              and sandbox.HOSTILE_RANK_MAX == 21 and "0..21" in m0.ranks.hint.text()
              and "0..12" not in m0.ranks.hint.text(),
              f"every Ranks spin on the hostile page is 0..21 (HOSTILE_RANK_MAX, lifted from the "
              f"table's 12) and the hint says so ({m0.ranks.hint.text()!r})")
        # ...and the chip tells rank 12 from rank 15, which the cost table
        # cannot: attribspend prices both at the same points (no row past 12,
        # the 13th is the client's cap sentinel), so a chip reading
        # n_of(total_spent) alone said one figure for 12, 15 and 21 -- a
        # number with no source past 12. Past the table the chip keeps the
        # priced part, COUNTS the ranks past it, and the roster line follows
        sp = next(iter(m0.ranks.spins.values()))
        keep = sp.value()
        sp.setValue(rules.rank_max)
        settle()
        at12, pts12 = m0.ranks.chip.text(), m0.ranks.spent()
        sp.setValue(rules.rank_max + 3)
        settle()
        at15, pts15, summ15 = m0.ranks.chip.text(), m0.ranks.spent(), m0.summary()
        tip15 = m0.ranks.chip.toolTip()
        sp.setValue(keep)
        settle()
        check(pts12 == pts15 and at12 == n_of(pts12, "point")
              and at15 == f"{n_of(pts12, 'point')} to {rules.rank_max}; 1 rank past it, not priced"
              and at15 in summ15 and str(rules.rank_max) in tip15,
              f"the chip tells rank {rules.rank_max} from rank {rules.rank_max + 3}, which the "
              f"table prices alike ({pts12} = {pts15}): {at12!r} against {at15!r} -- the priced "
              f"part and the count past the table, never a figure the table lacks -- and the "
              f"roster line follows it ({summ15!r})")
        # ...and a file with a level-28 boss-grade hostile carrying a rank of
        # 16 opens WHOLE: compiles, the bar says 'Opened' alone, the spins
        # hold 28 and 16 (Qt clamped a level-24 template to 20 in silence
        # before the ruling, and 'Opened X' alone was the same false word)
        mine = next(iter(m0.ranks.spins))
        held_spec = win.to_spec()
        g1 = held_spec["groups"][0]
        high = dict(held_spec, name="smoke-hostilehigh",
                    groups=[dict(g1, members=[dict(g1["members"][0], level=28,
                                                   attributes=[[mine, 16]])]
                                 + g1["members"][1:])] + held_spec["groups"][1:])
        high_path = os.path.join(out_dir, "smoke_hostilehigh.toml")
        with open(high_path, "w", encoding="utf-8") as fh:
            fh.write(sandbox.spec_toml(high))
        win.run.load(high_path)
        settle()
        msg = win.statusBar().currentMessage()
        m0 = en.groups[0].members[0]
        got = win.to_spec()["groups"][0]["members"][0]
        check(not sandbox.validate(high, win.world) and msg == "Opened smoke_hostilehigh"
              and got["level"] == 28 and [mine, 16] in (got.get("attributes") or [])
              and m0.level.value() == 28 and m0.ranks.spins[mine].value() == 16,
              f"a spec with a level-28 hostile carrying a rank of 16 compiles and opens WHOLE: "
              f"the bar says {msg!r}, the window holds level {m0.level.value()} and rank "
              f"{m0.ranks.spins[mine].value()} (a level-24 template clamped to 20 in silence "
              f"before the ruling)")
        # ...while a file past the new caps -- level 300 AND rank 22 on ONE
        # hostile -- is refused for both at compile, the spins hold 255 and
        # 21 (their ranges ARE the compiler's), and the bar says so, '2
        # changes'. Both on one member, because that is the case the compiler
        # once hid: its `elif` checked the ranks only when the level had
        # passed, so this member was refused for the level alone and the bar
        # said '1 change' while the window clamped both (this law had put the
        # two values on two members and could not see it; the verifier's
        # plant, 2026-09-24)
        over = dict(held_spec, name="smoke-hostileover",
                    groups=[dict(g1, members=[dict(g1["members"][0], level=300,
                                                   attributes=[[mine, 22]])]
                                 + g1["members"][1:])] + held_spec["groups"][1:])
        over_path = os.path.join(out_dir, "smoke_hostileover.toml")
        with open(over_path, "w", encoding="utf-8") as fh:
            fh.write(sandbox.spec_toml(over))
        refused = [q for q in sandbox.validate(over, win.world) if q.startswith("group 1 member")]
        win.run.load(over_path)
        settle()
        msg = win.statusBar().currentMessage()
        held_now = win.to_spec()
        now = held_now["groups"][0]["members"]
        m0 = en.groups[0].members[0]
        check(refused == ["group 1 member 1: level 300 is outside 0..255",
                          f"group 1 member 1.attributes: rank 22 on {mine} is outside 0..21"]
              and not sandbox.validate(held_now, win.world)
              and now[0]["level"] == 255 and [mine, 21] in (now[0].get("attributes") or [])
              and m0.level.value() == 255 and m0.ranks.spins[mine].value() == 21
              and msg.startswith("Opened smoke_hostileover, but the window could not hold all of "
                                 "it (2 changes: "),
              f"...and a file with level 300 AND rank 22 on ONE hostile is refused for BOTH at "
              f"compile ({refused}), the window holds 255 and 21, and the bar says '2 changes' "
              f"({msg[:86]!r})")
        win.from_spec(held_spec)
        settle()
    else:
        skip("the Ranks spins are 0..21 and the hint says so", "no attribute table, so no ranks")
        skip("the chip tells rank 12 from rank 15", "no attribute table, so no ranks")
        skip("a level-28, rank-16 hostile opens whole", "no attribute table, so no ranks")
        skip("a level-300, rank-22 file is refused and said", "no attribute table, so no ranks")
    # OPEN HOLDS WHAT THE COMPILER ACCEPTS (SANDBOX-N1): validate never checks a
    # hostile's skills against its profession, so a file with a Monk skill on
    # the Warrior raider, and one with an id the table lacks, both pass it --
    # and both open WHOLE with the bar saying 'Opened X' alone, to_spec carrying
    # them back. (The eight Pickers landed on '(empty)' in silence and said
    # 'Opened' all the same: measured on the tree before this, [322] held.)
    # A template change then KEEPS the bar: the chip warns 'of another
    # profession' and the cell's line 2 begins with the abbreviation
    held_spec = win.to_spec()
    g1 = sandbox.example_spec()["groups"][0]       # the raider's group, whatever the window holds now
    got = {}
    paths = {}
    for tag, sid in (("offprof", 281), ("unknown", 99999)):
        f = dict(held_spec, name=f"smoke-{tag}",
                 groups=[dict(g1, members=[dict(g1["members"][0], skills=[322, sid])]
                              + g1["members"][1:])] + sandbox.example_spec()["groups"][1:])
        paths[tag] = os.path.join(out_dir, f"smoke_{tag}.toml")
        with open(paths[tag], "w", encoding="utf-8") as fh:
            fh.write(sandbox.spec_toml(f))
        accepted = not sandbox.validate(f, win.world)
        win.run.load(paths[tag])
        settle()
        m0 = en.groups[0].members[0]
        got[tag] = (accepted, win.statusBar().currentMessage(),
                    win.to_spec()["groups"][0]["members"][0]["skills"], m0.bar.values()[:3],
                    m0.bar.strip.item(1).data(ROLE_SLOT)[1], m0.bar.chip.text(), m0.bar.chip.property("kind"))
    o, u = got["offprof"], got["unknown"]
    check(o[0] and u[0] and o[1] == "Opened smoke_offprof" and o[2] == [322, 281] and o[3] == [322, 281, 0]
          and o[4].startswith("Mo · ") and o[4].endswith(" 0") and o[6] == "warn"
          and o[5] == "2 of 8 slots  ·  1 of another profession"
          and u[1] == "Opened smoke_unknown" and u[2] == [322, 99999] and u[4] == "99999  -"
          and u[5] == "2 of 8 slots  ·  1 not in the skill table" and u[6] == "warn",
          f"a file with a Monk skill on the Warrior raider and one with an id the table lacks both "
          f"pass validate and open WHOLE, 'Opened' alone, to_spec carrying them, the chip counting "
          f"each (Monk: {o[1]!r}, {o[2]}, the cell {o[4]!r}, the chip {o[5]!r} {o[6]}; unknown: "
          f"{u[1]!r}, {u[2]}, the cell {u[4]!r}, the chip {u[5]!r} {u[6]})")
    # ...while a NINTH skill is the compiler's to refuse (validate: 'the bar
    # is 8 wide', the player's and a hero's rule), so a nine-skill file opens
    # holding eight and the bar SAYS so -- it said 'Opened X' alone and Save
    # wrote eight (the verifiers' a3 / c1, 2026-09-24); a 0 inside a file's
    # list is an empty slot, held in place and dropped on save
    nine = [322, 323, 0] + [s for s in sorted(win.names.modelled)
                            if win.names.skill_profession(s) == 1 and s not in (322, 323)][:6]
    f9 = dict(held_spec, name="smoke-nine",
              groups=[dict(g1, members=[dict(g1["members"][0], skills=nine)] + g1["members"][1:])]
              + sandbox.example_spec()["groups"][1:])
    p9 = os.path.join(out_dir, "smoke_nine.toml")
    with open(p9, "w", encoding="utf-8") as fh:
        fh.write(sandbox.spec_toml(f9))
    refused9 = sandbox.validate(f9, win.world)
    win.run.load(p9)
    settle()
    m0 = en.groups[0].members[0]
    said9 = win.statusBar().currentMessage()
    held9 = (m0.bar.values(), win.to_spec()["groups"][0]["members"][0]["skills"])
    check(len(nine) == 9 and refused9 == ["group 1 member 1: 9 skills; the bar is 8 wide"]
          and said9.startswith("Opened smoke_nine, but the window could not hold all of it (1 change: "
                               "group 1 member 1: 9 skills; the bar is 8 wide)")
          and held9[0] == nine[:8] and held9[1] == [s for s in nine[:8] if s],
          f"a file with NINE skills on the raider is refused by validate ({refused9}) and opens "
          f"holding eight with the bar saying so ({said9[:80]!r}); the 0 inside is held as an "
          f"empty slot and dropped by to_spec ({held9})")
    # ...and what a file says that the page does not edit rides through Open
    # and Save: the example raider's weapon_attribute 19 and the monk's 14
    # (the swing rank; dropped, the monk swung at rank 2 instead of 1 -- the
    # verifier's a8), while a template change to another PROFESSION drops a
    # weapon_attribute that profession's ranks could never hold
    pex = os.path.join(out_dir, "smoke_example.toml")
    with open(pex, "w", encoding="utf-8") as fh:
        fh.write(sandbox.spec_toml(dict(sandbox.example_spec(), name="smoke-example")))
    win.run.load(pex)
    settle()
    psaved = win.run.save(os.path.join(out_dir, "smoke_example_saved.toml"))
    back = sandbox.load_spec(psaved)["groups"][0]["members"]
    m0 = en.groups[0].members[0]
    wa_before = m0.to_spec().get("weapon_attribute")
    m0.template.set_value("academy_monk")
    settle(4)
    wa_after = m0.to_spec().get("weapon_attribute")
    m0.template.set_value("bandit_raider")
    settle(4)
    check([m.get("weapon_attribute") for m in back] == [19, 14] and wa_before == 19 and wa_after is None
          and "weapon_attribute" not in MemberEditor.EDITED,
          f"the example opened and saved keeps the raider's weapon_attribute 19 and the monk's 14 "
          f"({[m.get('weapon_attribute') for m in back]}), and a template change to the Monk drops "
          f"the Warrior's ({wa_before} -> {wa_after})")
    win.run.load(paths["offprof"])
    settle()
    m0 = en.groups[0].members[0]
    m0.template.set_value("academy_monk")
    settle(4)
    kept = (m0.bar.values()[:2], m0.bar.chip.text(), m0.bar.chip.property("kind"),
            m0.bar.strip.item(0).data(ROLE_SLOT)[1], m0.bar.prof.itemText(0))
    check(kept[0] == [322, 281] and kept[2] == "warn" and kept[1].endswith("1 of another profession")
          and kept[3].startswith("W · Strength ") and kept[4] == "Monk and common",
          f"a template change to the Monk KEEPS the bar, the chip warning of the Warrior skill now "
          f"of another profession and its cell's line 2 beginning with the abbreviation ({kept})")
    win.from_spec(held_spec)
    settle()
    m0 = en.groups[0].members[0]
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
    # ...and the bar SHOWS a line it cannot hold whole elided, never sliced
    # at the chip: at 1,000 px this message lost 'the original.' with no
    # mark (QStatusBar clips), and the instruction is why the message exists.
    # Read as pixels: the bar showing the long line must paint exactly what
    # it paints showing the elided line itself, and the whole line is on hover
    sb, size = win.statusBar(), win.size()
    win.resize(1000, 720)
    settle(8)
    room = sb.message_rect().width()
    sb.showMessage(msg, 20000)
    settle(4)
    tip, whole = sb.toolTip(), sb.grab().toImage()
    short = sb.fontMetrics().elidedText(msg, Qt.ElideRight, room)
    sb.showMessage(short, 20000)
    settle(4)
    cut = sb.grab().toImage()
    adv = sb.fontMetrics().horizontalAdvance(msg)
    check(adv > room and short != msg and whole == cut and tip == msg,
          f"at 1,000 px a bar message wider than its room ({adv} of {room} px) is painted elided "
          f"-- as the bar paints the elided line itself, pixel for pixel -- and the whole line is "
          f"its hover (the same {whole == cut}; hover is the line {tip == msg})")
    sb.clearMessage()
    win.resize(size)
    settle(8)
    # a file whose field the window never reads is malformed (a hero's bar as
    # a string): validate int()s it AFTER the tabs were rewritten, and the
    # raise left the window changed with the bar blank -- opened and said, as
    # a file the window could not hold whole, and load answers True
    strbar = os.path.join(out_dir, "smoke_strbar.toml")
    with open(strbar, "w", encoding="utf-8") as fh:
        fh.write(sandbox.spec_toml(dict(before, name="smoke-strbar"))
                 .replace("[[heroes]]\nhero = 3\n", "[[heroes]]\nhero = 3\nskills = \"281, 276\"\n", 1))
    try:
        answer, raised = win.run.load(strbar), None
    except Exception as exc:                                # noqa: BLE001
        answer, raised = None, f"{type(exc).__name__}: {exc}"
    settle()
    msg = win.statusBar().currentMessage()
    check(raised is None and answer is True and "281, 276" in open(strbar, encoding="utf-8").read()
          and win.header.name.text() == "smoke-strbar"
          and msg.startswith("Opened smoke_strbar, but the window could not hold all of it (1 change: "
                             "ValueError"),
          f"a file with a hero's bar written as a string opens, load answers True, and the bar "
          f"says what the window could not hold (raised {raised}; {msg[:100]!r})")
    # a file that cannot be opened at all: load answers False and the spec
    # stands (the command line reads the answer)
    missing = os.path.join(out_dir, "no_such_spec.toml")
    answer = win.run.load(missing)
    settle()
    msg = win.statusBar().currentMessage()
    check(answer is False and msg.startswith("Could not open no_such_spec")
          and win.header.name.text() == "smoke-strbar",
          f"a file that is not there: load answers False, the bar says so, the window keeps "
          f"what it held ({answer}; {msg[:60]!r})")
    win.from_spec(before)
    settle()
    # ...and the command line's --spec goes through that Open: a file it
    # could not open is said on stderr and, with nothing to show it in (a
    # --snap), the process ends 1 before any render -- rc 0 with the example
    # rendered as the file and nothing on the console was the route. Driven
    # as a process, since main() is not reached from here; --no-names keeps
    # it to a content load and the window
    cli_out = os.path.join(out_dir, "cli_snap")
    run = subprocess.run([sys.executable, os.path.abspath(__file__), "--spec", missing, "--snap",
                          cli_out, "--theme", "dark", "--no-names"],
                         capture_output=True, text=True, timeout=180)
    check(run.returncode == 1 and "Could not open no_such_spec" in run.stderr
          and not os.path.exists(cli_out),
          f"--spec on a file that cannot be opened is said on stderr and, with --snap, the "
          f"process ends 1 with nothing rendered (rc {run.returncode}; stderr "
          f"{run.stderr.strip()[-70:]!r})")
    # a member with no level, and a hero with none, open at the level the
    # compiler gives them (the template's; the player's) -- a constant 2 put
    # a level-10 template over its budget on the way in, and one file got
    # one verdict from the CLI and another after Open
    npc_rows = win.names.world.rows("npc")
    tkey = max((k for k, r in npc_rows.items() if r.get("model_id")
                and int(r.get("level", 0) or 0) > 2),
               key=lambda k: int(npc_rows[k].get("level", 0) or 0), default=None)
    nolevel = dict(before, name="smoke-nolevel", player=dict(before["player"], level=10),
                   heroes=[{k: v for k, v in before["heroes"][0].items() if k != "level"}],
                   groups=[{"members": [{"npc": tkey, "health": 120}]}] + before["groups"][1:])
    nolevel_path = os.path.join(out_dir, "smoke_nolevel.toml")
    with open(nolevel_path, "w", encoding="utf-8") as fh:
        fh.write(sandbox.spec_toml(nolevel))
    win.run.load(nolevel_path)
    settle()
    held = win.to_spec()
    want = (sandbox.spawn_rows(nolevel, win.world)[0][1]["level"],
            sandbox.party_row(nolevel, win.world)["heroes"][0]["level"])
    got = (held["groups"][0]["members"][0]["level"], held["heroes"][0]["level"])
    check(tkey is not None and want[0] > 2 and want[1] == 10 and want == got
          and win.statusBar().currentMessage() == "Opened smoke_nolevel",
          f"a member and a hero with no level open at the level the compiler gives them "
          f"({tkey}'s template level and the player's: {want}; the window holds {got})")
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
    # Stop and the window's close take the run's WHOLE tree (2026-09-24: two
    # authsrv.py outlived a closed window by hours, holding 6112, because the
    # QProcess destructor and the old Stop killed session.py alone). A stand-in
    # harness with one child of its own, through the real start path; the
    # middle law is the control -- kill() alone, the old Stop, must ORPHAN the
    # child, or the laws either side of it could pass on a child that died of
    # something else.
    def tree_run():
        rt._start([sys.executable, "-u", "-c", STANDIN_TREE], {})
        child, t_end = None, time.perf_counter() + 15.0
        while child is None and rt.proc is not None and time.perf_counter() < t_end:
            settle(1)
            time.sleep(0.02)
            m = re.search(r"^TREE (\d+)$", rt.log.toPlainText(), re.M)
            child = int(m.group(1)) if m else None
        return child, (rt.proc.processId() if rt.proc is not None else 0)

    def run_ended(secs=10.0):
        t_end = time.perf_counter() + secs
        while rt.proc is not None and time.perf_counter() < t_end:
            settle(1)
            time.sleep(0.01)
        settle(3)

    child, root = tree_run()
    rt.stop()
    run_ended()
    said = win.statusBar().currentMessage()
    gone = bool(child and root) and not childjob.alive(child) and not childjob.alive(root)
    check(gone and rt.proc is None and rt.state.text() == "Stopped"
          and said == "Stopped the harness, its servers and the client.",
          f"Stop kills the harness AND its child, and says so (child {child} "
          f"{'dead' if child and not childjob.alive(child) else 'ALIVE'}, {rt.state.text()!r}, "
          f"{said!r})")
    childjob.kill_tree(child or 0)
    child, root = tree_run()
    if rt.proc is not None:
        rt.proc.kill()
    run_ended()
    orphan = bool(child) and childjob.alive(child)
    check(orphan, f"the control: kill() alone -- the old Stop -- leaves the child running "
                  f"(child {child} {'alive' if orphan else 'DEAD'})")
    childjob.kill_tree(child or 0)
    child, root = tree_run()
    win.closeEvent(QCloseEvent())           # the override, not a close: the smoke goes on
    closed = bool(child and root) and not childjob.alive(child) and not childjob.alive(root)
    check(closed and rt.proc is None,
          f"closing the window kills the run's tree before the window goes (child {child} "
          f"{'dead' if child and not childjob.alive(child) else 'ALIVE'}, harness "
          f"{'ended' if rt.proc is None else 'STILL RUNNING'})")
    childjob.kill_tree(child or 0)
    if rt.proc is not None:
        rt.proc.kill()
        run_ended()
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
    # a QMessageBox.warning with the old face would pass the law above) --
    # an exec() on the box, and no QMessageBox call of launch's own, off the
    # syntax tree (a text match took the old call in a comment for the site)
    lcalls = source_calls(RunTab.launch)
    shown = any(isinstance(c.func, ast.Attribute) and c.func.attr == "exec"
                and isinstance(c.func.value, ast.Call)
                and dotted(c.func.value.func) == "self.no_archive_box" for c in lcalls)
    own = [dotted(c.func) for c in lcalls if dotted(c.func).startswith("QMessageBox")]
    check(shown and not own,
          f"and Launch shows that dialog, not one of its own (no_archive_box().exec() {shown}; "
          f"its own boxes: {own or 'none'}; read off the syntax tree)")
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
    # vault's store), read at its say site: the sentence, never the store's
    # path -- every _say in reset says a name or a literal (never an f-string
    # or a join), one of them RESET_DONE, off the syntax tree: the old line
    # in a comment or a docstring, or the path said after the sentence, is
    # not a say site
    says = [c for c in source_calls(RunTab.reset) if dotted(c.func) == "self._say"]
    check(not SURFACE_LORE.search(RESET_DONE)
          and any(c.args and _is_name(c.args[0], "RESET_DONE") for c in says)
          and all(c.args and (isinstance(c.args[0], ast.Name)
                              or (isinstance(c.args[0], ast.Constant)
                                  and isinstance(c.args[0].value, str))) for c in says),
          f"what a reset says is its sentence, never the store's path (the confirm box shows it): "
          f"{len(says)} say site(s), each a name or a literal, read off the syntax tree")
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
    # measured on grabs of the WINDOW, not of the widget (see _moved). First,
    # reachable by Tab at all: focus() forces focus with setFocus(), which a
    # NoFocus policy does not refuse, so the ring laws show the ring once
    # focus is forced, not that the keyboard can put it there
    check(bool(lb.focusPolicy() & Qt.TabFocus) and bool(en.tree.focusPolicy() & Qt.TabFocus),
          f"Launch and the encounter list take keyboard focus by Tab (their policies "
          f"{lb.focusPolicy()!s}, {en.tree.focusPolicy()!s})")
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
    page, bar, pk = en._pages[m0], en._pages[m0].verticalScrollBar(), m0.weapon_item
    scrolls = sys.platform == "win32" and bar.maximum() > 0
    if scrolls and focus(en.tree):
        rolled = []
        for tag, w, value in (("Weapon picker", pk, pk.currentIndex), ("Level", m0.level, m0.level.value)):
            bar.setValue(0)
            settle()
            v0 = value()
            _real_wheel(win, w)
            settle(5)
            rolled.append((tag, bar.value(), v0, value(), w.hasFocus()))
        check(all(px > 0 and v0 == v1 and not took for _t, px, v0, v1, took in rolled),
              f"in the ACTIVE window a real wheel over an unfocused Weapon picker and Level spin "
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
        # the NESTED wheel: the Skill bar's library scrolls under the wheel
        # while its bar can move that way and the page stays; at the list's
        # end the same wheel goes on to the page (Qt's own chaining: a list
        # leaves an unchanged wheel unaccepted, measured before the library
        # was written -- so this law guards that nobody "fixes" it by
        # accepting the wheel, and that the list is not guarded like a combo)
        lib, lbar = m0.bar.list, m0.bar.list.verticalScrollBar()
        page.ensureWidgetVisible(lib, 0, 0)
        settle(4)
        p0 = bar.value()
        lbar.setValue(0)
        settle()
        if lbar.maximum() > 0 and page.viewport().rect().contains(
                lib.mapTo(page.viewport(), QPoint(lib.width() // 2, lib.height() // 2))):
            _real_wheel(win, lib)
            settle(5)
            first_arm = (lbar.value(), bar.value())
            lbar.setValue(lbar.maximum())
            settle()
            _real_wheel(win, lib)
            settle(5)
            second_arm = (lbar.value(), bar.value())
            check(first_arm[0] > 0 and first_arm[1] == p0 and second_arm[0] == lbar.maximum()
                  and second_arm[1] > p0,
                  f"a real wheel over the Skill bar's library scrolls the LIST and not the page "
                  f"(list, page: {first_arm}, the page at {p0}), and at the list's end the same "
                  f"wheel scrolls the page ({second_arm})")
            lbar.setValue(0)
        else:
            skip("the nested wheel over the Skill bar's library",
                 f"the library does not scroll ({lbar.maximum()}) or is not in the viewport")
        bar.setValue(0)
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
        # one gate, four laws: each named, so a skipped run says what it
        # did not measure (one line stood for all four, the nested wheel
        # among them: the verifier's b10)
        why = lost if scrolls else "the page does not scroll at this size, or this is not Windows"
        skip("the wheel in the active window over an unfocused picker and spin", why)
        skip("a focused combo takes the wheel", why)
        skip("the nested wheel over the Skill bar's library", why)
        skip("a real wheel over a hero's Level spin scrolls the heroes table", why)
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

    def bar_surface(tag):
        """The boss's page scrolled to its Skill bar card, 'ham' in the
        search, the card WHOLE: at 1,000 px the card (a four-row strip over
        the library) is taller than a 720 px window's viewport, so scrolling
        to its foot cut the title and the chip (the verifier's c13) -- the
        window is grown to hold the card, as the right-edge law's tall arm
        grows it, and put back."""
        boss = win.enemies.groups[-1].members[0]
        win.enemies.select(boss)
        boss.bar.filter.setText("ham")
        page = win.enemies._pages[boss]
        card_w = boss.bar.parentWidget()
        for _ in range(3):
            app.processEvents()
        size = win.size()
        need = card_w.height() + (win.height() - page.viewport().height()) + 48
        if win.height() < need:
            win.resize(win.width(), need)
            for _ in range(6):
                app.processEvents()
        page.ensureWidgetVisible(card_w, 0, 24)
        grab(tag)
        boss.bar.filter.setText("")
        page.verticalScrollBar().setValue(0)
        win.resize(size)
        for _ in range(3):
            app.processEvents()

    if win.enemies.groups:
        win.enemies.select(win.enemies.groups[-1].members[0] if win.enemies.groups[-1].members
                           else win.enemies.groups[-1])
        grab("enemies_boss")
        if win.enemies.groups[-1].members:
            bar_surface("enemies_bar")
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
    if win.enemies.groups and win.enemies.groups[-1].members:
        win.tabs.setCurrentWidget(win.enemies)
        bar_surface("narrow_enemies_bar")
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
    if args.smoke:
        plant_long_template(world)      # the smoke's own row, in memory: tomorrow's content
    names = Names(world, resolve=not args.no_names)
    print(f"content and names loaded in {time.perf_counter() - t0:.1f} s ({theme} theme)"
          + (f" -- {names.why}" if names.why else ""))
    win = Window(world, names)
    win.from_spec(sandbox.example_spec())
    if args.spec and not win.run.load(args.spec):
        # the header's Open: said in the bar, what the window could not hold
        # too -- and a file it could not open said on the console as well,
        # since the window then holds the example and a bar message is all
        # the route left (rc 0, nothing printed, the example rendered as the
        # file); with no window for anyone to read, the process ends 1
        print(f"--spec {args.spec}: {win.statusBar().currentMessage()}", file=sys.stderr)
        if args.smoke or args.snap:
            return 1
    if args.smoke or args.snap:
        rc = smoke(win, app, args.smoke) if args.smoke else snap(win, app, args.snap, theme)
        QTimer.singleShot(0, app.quit)
        app.exec()
        return rc
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
