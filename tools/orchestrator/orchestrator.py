r"""Rurik run orchestrator -- the vertical slice as a practice sandbox, from a
window. PySide6; nothing here knows the archive, the wire or the rules.

    python tools/orchestrator/orchestrator.py                    # the window, the slice loaded
    python tools/orchestrator/orchestrator.py --spec my.toml     # open a saved spec
    python tools/orchestrator/orchestrator.py --smoke DIR        # drive every panel once, exit
    pythonw apps/orchestrator.pyw                                # double-click launcher

WHY THIS LIVES UNDER `tools/` AND NOT `toolkit/`. `CLAUDE.md` pins `toolkit/`
to the standard library; PySide6 is not that. So the split is the one
`tools/viewer/` already made: every fact -- what a spec may say, where a
group stands, which ids are reserved, what the gamesrv is told -- is
`toolkit/harness/sandbox.py`'s (stdlib, `test_sandbox.py`), the content is
`toolkit/content.py`'s, and every NAME on screen is resolved at run time from
the owner's own archive through `toolkit/clientscan/textrec.py`. This file
holds widgets. If a run is wrong, the question is for the compiler.

WHAT THE WINDOW IS. Four tabs over one spec:
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
  Enemies  up to four groups of up to four hostiles, one of them the boss,
           each with its bar and ranks (a filterable picker for these is the
           next step, SANDBOX-N1)
  Run      the spec's name; save and load; COMPILE (the overlay and the
           command, shown before anything runs, with what the character
           store already holds); LAUNCH, which starts the harness on the
           slice archive and streams its output here; RESET, which clears
           the stored character so the next login starts clean
The operator plays; closing the game client ends the run and the stack.

NAMES. Skill names come off the pinned client's own skill table (the record's
name string id, `skilltable.parse_record`) and the archive's text files; hero
names off the extracted hero table's string ids; attribute names likewise.
None of it is stored anywhere -- the spec on disk carries ids -- and a
machine with no client shows ids. That is the provenance gate's "commit the
id, resolve the string at run time", one more time.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "toolkit"), os.path.join(ROOT, "toolkit", "harness"),
          os.path.join(ROOT, "toolkit", "clientscan"), os.path.join(ROOT, "toolkit", "mapdata"),
          os.path.join(ROOT, "toolkit", "authsrv")):
    if p not in sys.path:
        sys.path.insert(0, p)

import sandbox        # noqa: E402  (toolkit/harness/sandbox.py)
import content        # noqa: E402
import vaultpath      # noqa: E402

try:
    from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer
    from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QCompleter,
                                   QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                                   QHeaderView, QLabel, QLineEdit, QListWidget,
                                   QListWidgetItem, QMainWindow, QMessageBox,
                                   QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                                   QDoubleSpinBox, QTableWidget, QTableWidgetItem,
                                   QTabWidget, QVBoxLayout, QWidget)
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"the run orchestrator needs PySide6 (py -m pip install PySide6): {exc}")


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

    def skill_label(self, sid):
        row = self.world.rows("skills").get(str(sid)) or {}
        prof = sandbox.ABBREV.get(int(row.get("profession", 0) or 0), "-")
        attr = self.attr.get(int(row.get("attribute", -1)), "")
        mark = " *" if sid in self.modelled else ""
        return f"{self.skill.get(sid, f'skill {sid}')}  [{sid} {prof}{(' ' + attr) if attr else ''}]{mark}"

    def hero_label(self, idx):
        return f"{self.hero.get(idx, f'hero {idx}')}  [{idx}]"

    def attr_label(self, aid):
        return self.attr.get(aid, f"attribute {aid}")

    @property
    def modelled(self):
        if not hasattr(self, "_modelled"):
            self._modelled = set(sandbox.modelled_skills(self.world))
        return self._modelled


# ---------------------------------------------------------------- pieces

class Picker(QComboBox):
    """A combo whose items carry a value, type-to-filter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        comp = self.completer()
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setCaseSensitivity(Qt.CaseInsensitive)

    def set_choices(self, pairs, keep=None):
        """pairs: [(label, value)]. Keeps the current value when it is still offered."""
        current = keep if keep is not None else self.value()
        self.blockSignals(True)
        self.clear()
        for label, value in pairs:
            self.addItem(label, value)
        self.blockSignals(False)
        self.set_value(current)

    def value(self):
        return self.currentData()

    def set_value(self, value):
        for i in range(self.count()):
            if self.itemData(i) == value:
                self.setCurrentIndex(i)
                return True
        if self.count():
            self.setCurrentIndex(0)
        return False


def skill_choices(names, professions, empty=True):
    ids = sandbox.default_unlocks(names.world, professions)
    pairs = sorted(((names.skill_label(s), s) for s in ids), key=lambda p: p[0].lower())
    return ([("(empty)", 0)] if empty else []) + pairs


class Bar(QWidget):
    """Eight skill slots (the Enemies tab's; the party's bars are in-game)."""

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.slots = []
        for i in range(sandbox.BAR_SLOTS):
            pk = Picker()
            pk.setMinimumWidth(110)
            lay.addWidget(pk)
            self.slots.append(pk)

    def set_professions(self, professions):
        pairs = skill_choices(self.names, professions)
        for pk in self.slots:
            pk.set_choices(pairs)

    def values(self):
        return [int(pk.value() or 0) for pk in self.slots]

    def set_values(self, ids):
        ids = list(ids or []) + [0] * sandbox.BAR_SLOTS
        for pk, sid in zip(self.slots, ids):
            pk.set_value(int(sid))


class Ranks(QWidget):
    """One spin box per attribute of the given professions, with the budget
    (the Enemies tab's; the party's ranks are in-game)."""

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        self.rules = sandbox.attribute_rules(names.world)
        self.form = QFormLayout(self)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.spins = {}
        self.label = QLabel("")
        self.level = 3
        self.professions = ()

    def set_professions(self, professions, level):
        keep = self.ranks()
        while self.form.rowCount():
            self.form.removeRow(0)          # deletes the row's widgets, the label included
        self.label = QLabel("")
        self.spins = {}
        self.professions = tuple(int(p) for p in professions if p)
        self.level = int(level)
        if self.rules is None:
            self.form.addRow(QLabel("no attribute table (vault/content/attributes.toml): "
                                    "ranks cannot be edited here"))
            return
        for aid, row in sorted(self.rules.attributes.items()):
            if row["profession"] not in self.professions:
                continue
            if row["is_primary"] and row["profession"] != self.professions[0]:
                continue                       # the secondary's primary attribute: never spendable
            sp = QSpinBox()
            sp.setRange(0, self.rules.rank_max)
            sp.setValue(dict(keep).get(aid, 0))
            sp.valueChanged.connect(self._budget)
            self.spins[aid] = sp
            self.form.addRow(f"{self.names.attr_label(aid)} [{aid}]"
                             + (" (primary)" if row["is_primary"] else ""), sp)
        self.form.addRow("points", self.label)
        self._budget()

    def _budget(self):
        if self.rules is None:
            return
        spent = self.rules.total_spent({a: s.value() for a, s in self.spins.items()})
        budget = sandbox.points_for_level(self.level)
        self.label.setText(f"{spent} of {budget} spent"
                           + ("  -- OVER: the compiler will refuse this" if spent > budget else ""))

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


def profession_picker(none=False):
    pk = QComboBox()
    if none:
        pk.addItem("(none)", 0)
    for pid, name in sandbox.PROFESSIONS.items():
        pk.addItem(f"{name} ({sandbox.ABBREV[pid]})", pid)
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


# ---------------------------------------------------------------- Skills

class SkillsTab(QWidget):
    """The ACCOUNT library: every player-usable skill, ticked = unlocked."""

    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("Unlocked skills, ACCOUNT-wide (0x001D). The character's bar "
                               "and every hero's bar are filled in-game from these; a hero "
                               "may also use its own list. * = a skill this server models "
                               "beyond its icon."))
        row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("filter by name, id or attribute")
        self.prof = QComboBox()
        self.prof.addItem("every profession", 0)
        for pid, name in sandbox.PROFESSIONS.items():
            self.prof.addItem(f"{name} ({sandbox.ABBREV[pid]})", pid)
        self.prof.addItem("common (no profession)", -1)
        self.modelled_only = QCheckBox("modelled only")
        row.addWidget(self.filter, 2)
        row.addWidget(self.prof, 1)
        row.addWidget(self.modelled_only)
        outer.addLayout(row)
        row2 = QHBoxLayout()
        self.all_b = QPushButton("unlock all shown")
        self.none_b = QPushButton("lock all shown")
        self.party_b = QPushButton("the party's professions")
        self.count = QLabel("")
        for b in (self.all_b, self.none_b, self.party_b):
            row2.addWidget(b)
        row2.addWidget(self.count)
        row2.addStretch(1)
        outer.addLayout(row2)
        self.list = QListWidget()
        outer.addWidget(self.list, 1)
        self.party_professions = set()
        every = sorted(int(k) for k in names.world.rows("skills"))
        for sid in sorted(every, key=lambda s: names.skill_label(s).lower()):
            it = QListWidgetItem(names.skill_label(sid))
            it.setData(Qt.UserRole, sid)
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
            sid = int(it.data(Qt.UserRole))
            sp = self.names.skill_profession(sid)
            hide = ((text and text not in it.text().lower())
                    or (prof > 0 and sp != prof) or (prof == -1 and sp != 0)
                    or (only and sid not in self.names.modelled))
            it.setHidden(bool(hide))
        self._count()

    def _count(self):
        n = sum(1 for it in self._items() if it.checkState() == Qt.Checked)
        self.count.setText(f"{n} of {self.list.count()} unlocked")

    def _set_shown(self, on):
        for it in self._items():
            if not it.isHidden():
                it.setCheckState(Qt.Checked if on else Qt.Unchecked)

    def set_party_professions(self, profs):
        self.party_professions = set(int(p) for p in profs if p)

    def unlock_party(self):
        want = self.party_professions | {0}
        for it in self._items():
            sp = self.names.skill_profession(int(it.data(Qt.UserRole)))
            it.setCheckState(Qt.Checked if sp in want else Qt.Unchecked)

    def ids(self):
        return sorted(int(it.data(Qt.UserRole)) for it in self._items()
                      if it.checkState() == Qt.Checked)

    def set_ids(self, ids):
        want = set(int(s) for s in ids)
        for it in self._items():
            it.setCheckState(Qt.Checked if int(it.data(Qt.UserRole)) in want else Qt.Unchecked)
        self._count()


# ---------------------------------------------------------------- Party

class PartyTab(QWidget):
    """The character, and which heroes are unlocked (each with a profession
    and a body). No bars, no ranks: those are the in-game panels' job."""

    COLS = ("unlocked", "hero", "profession", "body", "level")

    def __init__(self, names, on_change, parent=None):
        super().__init__(parent)
        self.names = names
        self.on_change = on_change
        world = names.world
        outer = QVBoxLayout(self)
        box = QGroupBox("the character")
        form = QFormLayout(box)
        self.primary = profession_picker()
        self.secondary = profession_picker(none=True)
        self.level = QSpinBox()
        self.level.setRange(1, sandbox.LEVEL_MAX)
        self.level.setValue(3)
        items = sorted(world.rows("item"))
        armour_words = ("_body", "_boots", "_legs", "_gloves", "_head", "backpack", "costume")
        weapons = [k for k in items if not any(w in k for w in armour_words)]
        self.weapon = Picker()
        self.weapon.set_choices([(k, k) for k in weapons])
        self.offhand = Picker()
        self.offhand.set_choices([("(none)", "")] + [(k, k) for k in weapons
                                                     if "shield" in k or "focus" in k])
        form.addRow("primary", self.primary)
        form.addRow("secondary", self.secondary)
        form.addRow("level", self.level)
        form.addRow("weapon", self.weapon)
        form.addRow("off hand", self.offhand)
        form.addRow("", QLabel("bar and attribute ranks: the in-game K and skill panels; "
                               "--persist keeps them. The level sets the points and health."))
        outer.addWidget(box)
        hb = QGroupBox("the heroes -- tick to unlock (they join the party); up to 7")
        hl = QVBoxLayout(hb)
        self.count = QLabel("")
        hl.addWidget(self.count)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        hl.addWidget(self.table, 1)
        outer.addWidget(hb, 1)
        self.rows = {}                         # hero index -> (check, prof, body, level)
        cat = names.heroes or [(i, 0) for i in range(1, sandbox.HERO_INDEX_MAX + 1)]
        bodies = template_choices(world)
        for idx, _nid in cat:
            r = self.table.rowCount()
            self.table.insertRow(r)
            chk = QCheckBox()
            prof = profession_picker()
            body = Picker()
            body.set_choices(bodies)
            body.set_value("hatcher")
            lvl = QSpinBox()
            lvl.setRange(1, sandbox.LEVEL_MAX)
            lvl.setValue(3)
            name = QTableWidgetItem(names.hero_label(idx))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.table.setCellWidget(r, 0, chk)
            self.table.setItem(r, 1, name)
            self.table.setCellWidget(r, 2, prof)
            self.table.setCellWidget(r, 3, body)
            self.table.setCellWidget(r, 4, lvl)
            chk.toggled.connect(lambda on, i=idx: self._toggled(i, on))
            prof.currentIndexChanged.connect(lambda _i, i=idx: self._prof_changed(i))
            body.currentIndexChanged.connect(lambda _i, i=idx: self._body_changed(i))
            self.rows[idx] = (chk, prof, body, lvl)
        self.primary.currentIndexChanged.connect(lambda _i: self.on_change())
        self.secondary.currentIndexChanged.connect(lambda _i: self.on_change())
        self._count()

    def unlocked(self):
        return [i for i, (chk, _p, _b, _l) in self.rows.items() if chk.isChecked()]

    def _toggled(self, idx, on):
        if on and len(self.unlocked()) > sandbox.HEROES_MAX:
            self.rows[idx][0].setChecked(False)
            self.count.setText(f"the client's cap is {sandbox.HEROES_MAX} heroes "
                               f"(PtPlayer:332) -- unlock one fewer first")
            return
        self._count()
        self.on_change()

    def _count(self):
        self.count.setText(f"{len(self.unlocked())} of {sandbox.HEROES_MAX} unlocked")

    def _prof_changed(self, idx):
        if self.rows[idx][0].isChecked():
            self.on_change()

    def _body_changed(self, idx):
        # A body carries a profession byte; offer it as the default, never force it.
        chk, prof, body, _l = self.rows[idx]
        row = self.names.world.rows("npc").get(body.value()) or {}
        if row.get("profession") in sandbox.PROFESSIONS and not getattr(body, "_touched", False):
            set_combo(prof, int(row["profession"]))

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
        self._count()
        self.on_change()


# ---------------------------------------------------------------- Enemies

class MemberEditor(QGroupBox):
    def __init__(self, names, on_remove, parent=None):
        super().__init__("hostile", parent)
        self.names = names
        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.template = Picker()
        self.template.set_choices(template_choices(names.world))
        self.level = QSpinBox()
        self.level.setRange(0, sandbox.LEVEL_MAX)
        self.level.setValue(2)
        self.health = QSpinBox()
        self.health.setRange(1, 10000)
        self.health.setValue(120)
        self.boss = QCheckBox("the BOSS (the quest's kill; glows)")
        self.glow = QSpinBox()
        self.glow.setRange(0, sandbox.GLOW_MAX)
        self.glow.setValue(sandbox.DEFAULT_GLOW)
        self.weapon_item = Picker()
        items = sorted(k for k in names.world.rows("item")
                       if not any(w in k for w in ("_body", "_boots", "_legs", "_gloves",
                                                   "_head", "backpack", "costume")))
        self.weapon_item.set_choices([("(none: the template's swing)", "")] + [(k, k) for k in items])
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.0, 5.0)
        self.speed.setSingleStep(0.05)
        self.speed.setSpecialValueText("(the weapon's)")
        self.dlo, self.dhi = QSpinBox(), QSpinBox()
        for s in (self.dlo, self.dhi):
            s.setRange(0, 200)
        self.dhi.setValue(0)
        form.addRow("template", self.template)
        form.addRow("level", self.level)
        form.addRow("health", self.health)
        form.addRow("", self.boss)
        form.addRow("glow (boss only, 0..10)", self.glow)
        form.addRow("weapon item", self.weapon_item)
        form.addRow("attack interval s", self.speed)
        dmg = QHBoxLayout()
        dmg.addWidget(self.dlo)
        dmg.addWidget(QLabel("to"))
        dmg.addWidget(self.dhi)
        dmg.addWidget(QLabel("(0-0 = the item's own range)"))
        form.addRow("damage", dmg)
        outer.addLayout(form)
        outer.addWidget(QLabel("skill bar (the template's profession and the common skills)"))
        self.bar = Bar(names)
        outer.addWidget(self.bar)
        self.ranks = Ranks(names)
        outer.addWidget(self.ranks)
        rm = QPushButton("remove this hostile")
        rm.clicked.connect(lambda: on_remove(self))
        outer.addWidget(rm)
        self.template.currentIndexChanged.connect(self._template)
        self.level.valueChanged.connect(self.ranks.set_level)
        self._template()

    def profession(self):
        row = self.names.world.rows("npc").get(self.template.value()) or {}
        return int(row.get("profession", 0) or 0)

    def _template(self):
        prof = self.profession()
        self.bar.set_professions((prof,))
        self.ranks.set_professions((prof,), max(1, self.level.value()))
        self.setTitle(f"hostile -- {sandbox.PROFESSIONS.get(prof, 'no profession')}")

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


class GroupEditor(QGroupBox):
    def __init__(self, names, index, on_remove, parent=None):
        super().__init__(f"group {index}", parent)
        self.names = names
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.add = QPushButton("add a hostile")
        self.add.clicked.connect(lambda: self.add_member())
        self.count = QLabel("")
        rm = QPushButton("remove this group")
        rm.clicked.connect(lambda: on_remove(self))
        top.addWidget(self.add)
        top.addWidget(self.count)
        top.addStretch(1)
        top.addWidget(rm)
        outer.addLayout(top)
        self.lay = QHBoxLayout()
        outer.addLayout(self.lay)
        self.members = []
        self._count()

    def add_member(self, spec=None):
        if len(self.members) >= sandbox.GROUP_SIZE_MAX:
            return None
        ed = MemberEditor(self.names, self.remove)
        if spec:
            ed.from_spec(spec)
        self.lay.addWidget(ed)
        self.members.append(ed)
        self._count()
        return ed

    def remove(self, ed):
        self.members.remove(ed)
        ed.setParent(None)
        ed.deleteLater()
        self._count()

    def _count(self):
        self.count.setText(f"{len(self.members)} of {sandbox.GROUP_SIZE_MAX}")
        self.add.setEnabled(len(self.members) < sandbox.GROUP_SIZE_MAX)

    def to_spec(self):
        return {"members": [m.to_spec() for m in self.members]}

    def from_spec(self, g):
        for m in list(self.members):
            self.remove(m)
        for m in g.get("members") or []:
            self.add_member(m)


class EnemiesTab(QWidget):
    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.add = QPushButton("add a group")
        self.add.clicked.connect(lambda: self.add_group())
        self.count = QLabel("")
        top.addWidget(self.add)
        top.addWidget(self.count)
        top.addWidget(QLabel("groups stand along the corridor south to north; the LAST "
                             "group holds the boss at the north end"))
        top.addStretch(1)
        outer.addLayout(top)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.lay = QVBoxLayout(self.inner)
        self.lay.addStretch(1)
        scroll.setWidget(self.inner)
        outer.addWidget(scroll)
        self.groups = []
        self._count()

    def add_group(self, spec=None):
        if len(self.groups) >= sandbox.GROUPS_MAX:
            return None
        ed = GroupEditor(self.names, len(self.groups) + 1, self.remove)
        if spec:
            ed.from_spec(spec)
        else:
            ed.add_member()
        self.lay.insertWidget(self.lay.count() - 1, ed)
        self.groups.append(ed)
        self._count()
        return ed

    def remove(self, ed):
        self.groups.remove(ed)
        ed.setParent(None)
        ed.deleteLater()
        for i, g in enumerate(self.groups, 1):
            g.setTitle(f"group {i}")
        self._count()

    def _count(self):
        self.count.setText(f"{len(self.groups)} of {sandbox.GROUPS_MAX}")
        self.add.setEnabled(len(self.groups) < sandbox.GROUPS_MAX)

    def to_spec(self):
        return [g.to_spec() for g in self.groups]

    def from_spec(self, groups):
        for g in list(self.groups):
            self.remove(g)
        for g in groups or []:
            self.add_group(g)


# ---------------------------------------------------------------- Run

class RunTab(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit("slice")
        form.addRow("spec name", self.name)
        self.hold = QSpinBox()
        self.hold.setRange(0, 7200)
        self.hold.setSpecialValueText("until the client closes")
        form.addRow("end after (s)", self.hold)
        outer.addLayout(form)
        row = QHBoxLayout()
        self.save_b, self.load_b = QPushButton("save spec"), QPushButton("load spec")
        self.example_b = QPushButton("load the slice")
        self.compile_b = QPushButton("COMPILE")
        self.launch_b = QPushButton("LAUNCH")
        self.stop_b = QPushButton("stop")
        self.reset_b = QPushButton("reset the stored character")
        self.stop_b.setEnabled(False)
        for b in (self.save_b, self.load_b, self.example_b, self.compile_b, self.launch_b,
                  self.stop_b, self.reset_b):
            row.addWidget(b)
        outer.addLayout(row)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumBlockCount(4000)
        outer.addWidget(QLabel("compiled: what the server is told, what the store already "
                               "holds, then the overlay"))
        outer.addWidget(self.summary, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(20000)
        outer.addWidget(QLabel("the run's output (session.py)"))
        outer.addWidget(self.log, 2)
        self.save_b.clicked.connect(self.save)
        self.load_b.clicked.connect(self.load)
        self.example_b.clicked.connect(lambda: self.window.from_spec(sandbox.example_spec()))
        self.compile_b.clicked.connect(self.compile)
        self.launch_b.clicked.connect(self.launch)
        self.stop_b.clicked.connect(self.stop)
        self.reset_b.clicked.connect(self.reset)
        self.proc = None
        self.compiled = None

    def specs_dir(self):
        d = vaultpath.vault_path("sandbox")
        os.makedirs(d, exist_ok=True)
        return d

    def save(self, path=None):
        spec = self.window.to_spec()
        if not path:
            path, _f = QFileDialog.getSaveFileName(
                self, "save the spec", os.path.join(self.specs_dir(), f"{spec['name']}.toml"),
                "TOML (*.toml)")
        if not path:
            return None
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(sandbox.spec_toml(spec))
        self.status.setText(f"saved {path}")
        return path

    def load(self, path=None):
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "load a spec", self.specs_dir(),
                                                   "TOML (*.toml)")
        if not path:
            return
        self.window.from_spec(sandbox.load_spec(path))
        self.status.setText(f"loaded {path}")

    def compile(self):
        spec = self.window.to_spec()
        self.compiled = None
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
            self.summary.setPlainText(str(exc))
            self.status.setText("REFUSED -- fix the spec")
            return None
        lines = sandbox.summary(self.compiled)
        lines += ["", "command: " + " ".join(self.compiled["command"]), "",
                  "--- overlay ---", self.compiled["overlay"]]
        self.summary.setPlainText("\n".join(lines))
        self.status.setText(missing or
                            f"compiled; the overlay goes to {self.compiled['overlay_path']}"
                            + (f"; {len(self.compiled['store_warnings'])} note(s) about the "
                               f"stored character above" if self.compiled["store_warnings"] else ""))
        return self.compiled

    def launch(self):
        if self.proc is not None:
            return
        if self.compile() is None:
            return
        try:
            sandbox.run_paths()
        except sandbox.SpecError as exc:
            QMessageBox.warning(self, "no slice archive", str(exc))
            return
        sandbox.write_overlay(self.compiled)
        self.log.clear()
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        for k, v in self.compiled["env"].items():
            env.insert(k, v)
        self.proc.setProcessEnvironment(env)
        self.proc.setWorkingDirectory(ROOT)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        cmd = self.compiled["command"]
        self.proc.start(cmd[0], cmd[1:])
        self.launch_b.setEnabled(False)
        self.stop_b.setEnabled(True)
        self.status.setText("running: the game client is coming up. Play; closing it ends "
                            "the run and the stack. Hands off the keyboard while the harness "
                            "logs in (it says when).")

    def _read(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.appendPlainText(data.rstrip("\n"))

    def _done(self, code, _status):
        self.log.appendPlainText(f"\n[session.py exited with code {code}]")
        self.status.setText(f"the run ended (exit {code}); the report is under "
                            f"vault/captures/harness/")
        self.proc = None
        self.launch_b.setEnabled(True)
        self.stop_b.setEnabled(False)

    def stop(self):
        if self.proc is not None:
            self.proc.kill()
            self.status.setText("killed the harness; its servers are stopped by --replace "
                                "on the next launch if any survived")

    def reset(self, confirm=True):
        path = sandbox.store_path()
        if not path or not os.path.isfile(path):
            self.status.setText("no stored character to reset")
            return False
        if confirm:
            ok = QMessageBox.question(
                self, "reset the stored character",
                f"Delete {path}?\n\nThe next login starts a fresh character: an empty bar, "
                f"every attribute point unspent, no hero builds. The spec is untouched.")
            if ok != QMessageBox.Yes:
                return False
        removed = sandbox.reset_store()
        self.status.setText(f"removed {removed}; the next login re-seeds the character")
        return True


# ---------------------------------------------------------------- the window

class Window(QMainWindow):
    def __init__(self, world, names):
        super().__init__()
        self.world, self.names = world, names
        self.setWindowTitle("Rurik run orchestrator")
        self.resize(1280, 860)
        self.tabs = QTabWidget()
        self.skills = SkillsTab(names)
        self.party = PartyTab(names, self._party_changed)
        self.enemies = EnemiesTab(names)
        self.run = RunTab(self)
        self.tabs.addTab(self.skills, "Skills")
        self.tabs.addTab(self.party, "Party")
        self.tabs.addTab(self.enemies, "Enemies")
        self.tabs.addTab(self.run, "Run")
        self.setCentralWidget(self.tabs)
        msg = names.why or "names resolved from the owner's archive"
        self.statusBar().showMessage(msg)

    def _party_changed(self):
        prim, sec = self.party.professions()
        self.skills.set_party_professions({prim, sec} | set(self.party.hero_professions()))

    def to_spec(self):
        return {"name": self.run.name.text().strip() or "sandbox",
                "unlocks": self.skills.ids(),
                "player": self.party.player_spec(), "heroes": self.party.heroes_spec(),
                "groups": self.enemies.to_spec()}

    def from_spec(self, spec):
        self.run.name.setText(str(spec.get("name") or "sandbox"))
        self.party.from_spec(spec.get("player") or {}, spec.get("heroes"))
        unl = spec.get("unlocks")
        if unl is None:
            unl = (spec.get("player") or {}).get("unlocks")
        if unl is not None:
            self.skills.set_ids(unl)
        else:
            self.skills.set_ids(int(k) for k in self.world.rows("skills"))
        self.enemies.from_spec(spec.get("groups"))


# ---------------------------------------------------------------- smoke

def smoke(win, app, out_dir):
    """`--smoke`: drive every panel once with the window up, then exit.

    A window nobody has clicked through is a window that may not open; this
    runs the click path in code so a refactor cannot leave a dead tab behind
    a green suite. Writes a screenshot and prints one line per check; exits
    non-zero on any failure. Never writes into the working tree."""
    out_dir = vaultpath.resolve_out(out_dir, what="smoke output")
    os.makedirs(out_dir, exist_ok=True)
    fails = []

    def check(cond, label):
        print(f"  [{'ok' if cond else 'FAIL'}] {label}")
        if not cond:
            fails.append(label)

    win.show()
    app.processEvents()
    win.from_spec(sandbox.example_spec())
    app.processEvents()
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
    for i, tab in enumerate((win.skills, win.party, win.enemies, win.run)):
        win.tabs.setCurrentIndex(i)
        app.processEvents()
    # the Skills tab: filter, lock, the party's professions
    win.skills.prof.setCurrentIndex(3)              # Monk
    app.processEvents()
    shown = [it for it in win.skills._items() if not it.isHidden()]
    check(shown and all(win.names.skill_profession(int(it.data(Qt.UserRole))) == 3 for it in shown),
          f"filtering by Monk shows Monk skills only ({len(shown)})")
    win.skills.none_b.click()
    check(all(it.checkState() == Qt.Unchecked for it in shown), "lock all shown locks them")
    win.skills.prof.setCurrentIndex(0)
    win.skills.party_b.click()
    ids = set(win.skills.ids())
    check(ids and all(win.names.skill_profession(s) in {0, 1, 3} for s in ids)
          and any(win.names.skill_profession(s) == 3 for s in ids),
          "'the party's professions' unlocks Warrior, Monk and common skills only")
    # the Party tab: a secondary, a second hero, the cap
    set_combo(win.party.secondary, 6)
    app.processEvents()
    check(6 in win.skills.party_professions, "the secondary reaches the Skills tab's party set")
    chk6, prof6, body6, _l = win.party.rows[6]
    chk6.setChecked(True)
    set_combo(prof6, 1)
    body6.set_value("bandit_raider")
    check(len(win.party.unlocked()) == 2 and win.to_spec()["heroes"][1]["profession"] == 1,
          "a second hero (index 6) unlocked as a Warrior in the raider's body")
    for idx in (1, 2, 4, 5, 7, 8):
        win.party.rows[idx][0].setChecked(True)
    check(len(win.party.unlocked()) == 7 and not win.party.rows[8][0].isChecked(),
          "the eighth hero is refused (the client's cap of 7)")
    for idx in (1, 2, 4, 5, 7):
        win.party.rows[idx][0].setChecked(False)
    # the Enemies tab
    g = win.enemies.groups[0]
    g.add_member()
    g.add_member()
    check(len(g.members) == 4 and not g.add.isEnabled(), "a group fills to four and the add stops")
    compiled = win.run.compile()
    check(compiled is not None, "the changed spec COMPILES")
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
    path = win.run.save(os.path.join(out_dir, "smoke_spec.toml"))
    check(path and os.path.isfile(path), "the spec saves")
    if path:
        back = sandbox.load_spec(path)
        check(back["player"]["secondary"] == 6 and len(back["heroes"]) == 2
              and len(back["unlocks"]) == len(ids), "and loads back with its unlocks")
    win.run.name.setText("smoke-bad")
    win.enemies.groups[0].members[0].boss.setChecked(True)
    check(win.run.compile() is None and "bosses" in win.run.summary.toPlainText(),
          "two bosses are REFUSED at compile, and the reason is shown")
    win.enemies.groups[0].members[0].boss.setChecked(False)
    shot = os.path.join(out_dir, "smoke_screen.png")
    win.grab().save(shot)
    check(os.path.isfile(shot), f"screenshot {shot}")
    print(f"smoke: {len(fails)} failure(s)")
    return 1 if fails else 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", default=None, help="a saved spec to open")
    ap.add_argument("--smoke", default=None, metavar="DIR",
                    help="drive every panel once, write a screenshot there, exit")
    ap.add_argument("--no-names", action="store_true",
                    help="skip resolving names from the archive (ids only; faster)")
    args = ap.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    t0 = time.perf_counter()
    world = content.load()
    names = Names(world, resolve=not args.no_names)
    print(f"content and names loaded in {time.perf_counter() - t0:.1f} s"
          + (f" -- {names.why}" if names.why else ""))
    win = Window(world, names)
    if args.spec:
        win.from_spec(sandbox.load_spec(args.spec))
    else:
        win.from_spec(sandbox.example_spec())
    if args.smoke:
        rc = smoke(win, app, args.smoke)
        QTimer.singleShot(0, app.quit)
        app.exec()
        return rc
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
