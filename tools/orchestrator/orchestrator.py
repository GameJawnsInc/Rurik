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
  Player   the profession pair, the level, the bar, the ranks, the hands, the
           account library (which skills are UNLOCKED -- 0x001D; a hero's own
           library is its bar plus this, herolib.hero_library)
  Heroes   up to seven, each a catalogue row (its name from the archive), a
           profession, a body, a level, a bar, ranks and a weapon class
  Enemies  up to four groups of up to four hostiles, one of them the boss
  Run      the spec's name; save and load; COMPILE (the overlay and the
           command, shown before anything runs); LAUNCH, which starts the
           harness on the slice archive and streams its output here
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
          os.path.join(ROOT, "toolkit", "clientscan"), os.path.join(ROOT, "toolkit", "mapdata")):
    if p not in sys.path:
        sys.path.insert(0, p)

import sandbox        # noqa: E402  (toolkit/harness/sandbox.py)
import content        # noqa: E402
import vaultpath      # noqa: E402

try:
    from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer
    from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QCompleter,
                                   QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                                   QLabel, QLineEdit, QListWidget, QListWidgetItem,
                                   QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
                                   QScrollArea, QSpinBox, QDoubleSpinBox, QTabWidget,
                                   QVBoxLayout, QWidget)
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
    """Eight skill slots."""

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
    """One spin box per attribute of the given professions, with the budget."""

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


# ---------------------------------------------------------------- Player

class PlayerTab(QWidget):
    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.names = names
        world = names.world
        outer = QVBoxLayout(self)
        form = QFormLayout()
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
        outer.addLayout(form)
        outer.addWidget(QLabel("skill bar (* = a skill this server models beyond its icon)"))
        self.bar = Bar(names)
        outer.addWidget(self.bar)
        box = QGroupBox("attribute ranks")
        self.ranks = Ranks(names)
        QVBoxLayout(box).addWidget(self.ranks)
        outer.addWidget(box)
        ub = QGroupBox("account library: skills UNLOCKED for the character and the heroes "
                       "(a bar skill outside it draws, then asserts the client on a drag)")
        ul = QVBoxLayout(ub)
        row = QHBoxLayout()
        self.unlock_filter = QLineEdit()
        self.unlock_filter.setPlaceholderText("filter")
        all_b, none_b = QPushButton("all"), QPushButton("none")
        row.addWidget(self.unlock_filter)
        row.addWidget(all_b)
        row.addWidget(none_b)
        ul.addLayout(row)
        self.unlocks = QListWidget()
        ul.addWidget(self.unlocks)
        outer.addWidget(ub)
        all_b.clicked.connect(lambda: self._check_all(True))
        none_b.clicked.connect(lambda: self._check_all(False))
        self.unlock_filter.textChanged.connect(self._filter)
        self.primary.currentIndexChanged.connect(self.refresh)
        self.secondary.currentIndexChanged.connect(self.refresh)
        self.level.valueChanged.connect(self.ranks.set_level)
        self.hero_professions = set()
        self.refresh()

    def professions(self):
        return (int(self.primary.currentData()), int(self.secondary.currentData() or 0))

    def refresh(self):
        prim, sec = self.professions()
        self.bar.set_professions((prim, sec))
        self.ranks.set_professions((prim, sec), self.level.value())
        self.refresh_unlocks()

    def refresh_unlocks(self):
        prim, sec = self.professions()
        profs = {prim, sec} | set(self.hero_professions)
        checked = {int(it.data(Qt.UserRole)) for it in self._items() if it.checkState() == Qt.Checked}
        was_empty = self.unlocks.count() == 0
        self.unlocks.clear()
        for label, sid in skill_choices(self.names, profs, empty=False):
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, sid)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if (was_empty or sid in checked) else Qt.Unchecked)
            self.unlocks.addItem(it)
        self._filter(self.unlock_filter.text())

    def set_hero_professions(self, profs):
        self.hero_professions = set(int(p) for p in profs if p)
        self.refresh_unlocks()

    def _items(self):
        return [self.unlocks.item(i) for i in range(self.unlocks.count())]

    def _check_all(self, on):
        for it in self._items():
            if not it.isHidden():
                it.setCheckState(Qt.Checked if on else Qt.Unchecked)

    def _filter(self, text):
        text = (text or "").lower()
        for it in self._items():
            it.setHidden(bool(text) and text not in it.text().lower())

    def to_spec(self):
        prim, sec = self.professions()
        unl = [int(it.data(Qt.UserRole)) for it in self._items() if it.checkState() == Qt.Checked]
        return {"profession": prim, "secondary": sec, "level": self.level.value(),
                "skills": self.bar.values(), "attributes": self.ranks.ranks(),
                "weapon": self.weapon.value() or None, "offhand": self.offhand.value() or None,
                "unlocks": unl}

    def from_spec(self, p):
        set_combo(self.primary, int(p.get("profession", 1)))
        set_combo(self.secondary, int(p.get("secondary", 0)))
        self.level.setValue(int(p.get("level", 3)))
        self.refresh()
        self.bar.set_values(p.get("skills"))
        self.ranks.set_ranks(p.get("attributes"))
        prim = int(p.get("profession", 1))
        w, o = sandbox.PLAYER_ITEMS_BY_PROFESSION.get(prim, ("starter_sword", "starter_shield"))
        self.weapon.set_value(p.get("weapon") or w)
        self.offhand.set_value(p.get("offhand") or o or "")
        if p.get("unlocks"):
            want = set(int(s) for s in p["unlocks"])
            for it in self._items():
                it.setCheckState(Qt.Checked if int(it.data(Qt.UserRole)) in want else Qt.Unchecked)


# ---------------------------------------------------------------- Heroes

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


class HeroEditor(QGroupBox):
    def __init__(self, names, on_remove, on_change, parent=None):
        super().__init__("hero", parent)
        self.names = names
        self.on_change = on_change
        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.catalogue = Picker()
        cat = names.heroes or [(i, 0) for i in range(1, sandbox.HERO_INDEX_MAX + 1)]
        self.catalogue.set_choices([(names.hero_label(i), i) for i, _n in cat])
        self.profession = profession_picker()
        self.body = Picker()
        self.body.set_choices(template_choices(names.world))
        self.level = QSpinBox()
        self.level.setRange(1, sandbox.LEVEL_MAX)
        self.level.setValue(3)
        self.weapon = Picker()
        rates = sorted((names.world.rows("attack_speed").get("rates") or {}))
        self.weapon.set_choices([("(the profession's)", "")] + [(k, k) for k in rates])
        form.addRow("hero", self.catalogue)
        form.addRow("profession", self.profession)
        form.addRow("body", self.body)
        form.addRow("level", self.level)
        form.addRow("weapon class", self.weapon)
        outer.addLayout(form)
        outer.addWidget(QLabel("skill bar"))
        self.bar = Bar(names)
        outer.addWidget(self.bar)
        self.ranks = Ranks(names)
        outer.addWidget(self.ranks)
        rm = QPushButton("remove this hero")
        rm.clicked.connect(lambda: on_remove(self))
        outer.addWidget(rm)
        self.profession.currentIndexChanged.connect(self._prof)
        self.level.valueChanged.connect(self.ranks.set_level)
        self.body.currentIndexChanged.connect(self._body)
        self._prof()

    def _prof(self):
        prof = int(self.profession.currentData())
        self.bar.set_professions((prof,))
        self.ranks.set_professions((prof,), self.level.value())
        self.setTitle(f"hero -- {sandbox.PROFESSIONS[prof]}")
        self.on_change()

    def _body(self):
        # A body carries a profession byte; offer it as the default, never force it.
        row = self.names.world.rows("npc").get(self.body.value()) or {}
        if row.get("profession") in sandbox.PROFESSIONS and not getattr(self, "_touched", False):
            set_combo(self.profession, int(row["profession"]))

    def to_spec(self):
        return {"hero": int(self.catalogue.value()), "profession": int(self.profession.currentData()),
                "body": self.body.value(), "level": self.level.value(),
                "skills": [s for s in self.bar.values()],
                "attributes": self.ranks.ranks(), "weapon": self.weapon.value() or None}

    def from_spec(self, h):
        self.body.set_value(h.get("body"))
        self._touched = True
        prof = int(h.get("profession") or (self.names.world.rows("npc").get(h.get("body")) or {}).get("profession") or 1)
        set_combo(self.profession, prof)
        self.catalogue.set_value(int(h.get("hero", 1)))
        self.level.setValue(int(h.get("level", 3)))
        self._prof()
        self.bar.set_values(h.get("skills"))
        self.ranks.set_ranks(h.get("attributes"))
        self.weapon.set_value(h.get("weapon") or "")


class HeroesTab(QWidget):
    def __init__(self, names, on_change, parent=None):
        super().__init__(parent)
        self.names = names
        self.on_change = on_change
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.add = QPushButton("add a hero")
        self.add.clicked.connect(lambda: self.add_hero())
        self.count = QLabel("")
        top.addWidget(self.add)
        top.addWidget(self.count)
        top.addStretch(1)
        outer.addLayout(top)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.lay = QVBoxLayout(self.inner)
        self.lay.addStretch(1)
        scroll.setWidget(self.inner)
        outer.addWidget(scroll)
        self.editors = []
        self._count()

    def add_hero(self, spec=None):
        if len(self.editors) >= sandbox.HEROES_MAX:
            return None
        ed = HeroEditor(self.names, self.remove, self.on_change)
        if spec:
            ed.from_spec(spec)
        else:
            used = {e.catalogue.value() for e in self.editors}
            for i in range(ed.catalogue.count()):
                if ed.catalogue.itemData(i) not in used:
                    ed.catalogue.setCurrentIndex(i)
                    break
        self.lay.insertWidget(self.lay.count() - 1, ed)
        self.editors.append(ed)
        self._count()
        self.on_change()
        return ed

    def remove(self, ed):
        self.editors.remove(ed)
        ed.setParent(None)
        ed.deleteLater()
        self._count()
        self.on_change()

    def _count(self):
        self.count.setText(f"{len(self.editors)} of {sandbox.HEROES_MAX}")
        self.add.setEnabled(len(self.editors) < sandbox.HEROES_MAX)

    def professions(self):
        return [int(e.profession.currentData()) for e in self.editors]

    def to_spec(self):
        return [e.to_spec() for e in self.editors]

    def from_spec(self, heroes):
        for e in list(self.editors):
            self.remove(e)
        for h in heroes or []:
            self.add_hero(h)


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
        self.stop_b.setEnabled(False)
        for b in (self.save_b, self.load_b, self.example_b, self.compile_b, self.launch_b, self.stop_b):
            row.addWidget(b)
        outer.addLayout(row)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumBlockCount(4000)
        outer.addWidget(QLabel("compiled: what the server is told (then the overlay)"))
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
        except sandbox.SpecError as exc:
            exe, dat = "(no slice run directory)", "(no slice run directory)"
            self.status.setText(str(exc))
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
        if not self.status.text().startswith("no slice"):
            self.status.setText(f"compiled; the overlay goes to {self.compiled['overlay_path']}")
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


# ---------------------------------------------------------------- the window

class Window(QMainWindow):
    def __init__(self, world, names):
        super().__init__()
        self.world, self.names = world, names
        self.setWindowTitle("Rurik run orchestrator")
        self.resize(1280, 860)
        self.tabs = QTabWidget()
        self.player = PlayerTab(names)
        self.heroes = HeroesTab(names, self._heroes_changed)
        self.enemies = EnemiesTab(names)
        self.run = RunTab(self)
        self.tabs.addTab(self.player, "Player")
        self.tabs.addTab(self.heroes, "Heroes")
        self.tabs.addTab(self.enemies, "Enemies")
        self.tabs.addTab(self.run, "Run")
        self.setCentralWidget(self.tabs)
        msg = names.why or "names resolved from the owner's archive"
        self.statusBar().showMessage(msg)

    def _heroes_changed(self):
        self.player.set_hero_professions(self.heroes.professions())

    def to_spec(self):
        return {"name": self.run.name.text().strip() or "sandbox",
                "player": self.player.to_spec(), "heroes": self.heroes.to_spec(),
                "groups": self.enemies.to_spec()}

    def from_spec(self, spec):
        self.run.name.setText(str(spec.get("name") or "sandbox"))
        self.heroes.from_spec(spec.get("heroes"))
        self.player.from_spec(spec.get("player") or {})
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
          "the slice loads into the Player tab")
    check(spec["player"]["skills"][:3] == [382, 384, 385], "the bar round-trips")
    check(spec["player"]["attributes"] == [[17, 2], [20, 3], [21, 1]] or
          sorted(spec["player"]["attributes"]) == [[17, 2], [20, 3], [21, 1]],
          f"the ranks round-trip ({spec['player']['attributes']})")
    check(len(spec["heroes"]) == 1 and spec["heroes"][0]["hero"] == 3
          and spec["heroes"][0]["profession"] == 3, "the Monk hero loads")
    check(len(spec["groups"]) == 3 and spec["groups"][2]["members"][0].get("boss"),
          "three groups, the boss last")
    for i, tab in enumerate((win.player, win.heroes, win.enemies, win.run)):
        win.tabs.setCurrentIndex(i)
        app.processEvents()
    # every knob the ask names, changed at once
    set_combo(win.player.secondary, 3)
    app.processEvents()
    check(any(win.player.bar.slots[0].itemData(i) == 281 for i in range(win.player.bar.slots[0].count())),
          "a Monk secondary offers Monk skills on the bar")
    ed = win.heroes.add_hero()
    check(ed is not None and len(win.heroes.editors) == 2, "a second hero is added")
    set_combo(ed.profession, 1)
    ed.body.set_value("bandit_raider")
    app.processEvents()
    check(1 in win.player.hero_professions, "the account library follows the heroes' professions")
    g = win.enemies.groups[0]
    g.add_member()
    g.add_member()
    check(len(g.members) == 4 and not g.add.isEnabled(), "a group fills to four and the add stops")
    win.enemies.add_group()
    check(len(win.enemies.groups) == 4 and not win.enemies.add.isEnabled(),
          "a fourth group and the add stops")
    win.enemies.remove(win.enemies.groups[-1])
    for _ in range(6):
        win.heroes.add_hero()
    check(len(win.heroes.editors) == 7 and not win.heroes.add.isEnabled(), "seven heroes cap")
    for e in list(win.heroes.editors[2:]):
        win.heroes.remove(e)
    compiled = win.run.compile()
    check(compiled is not None, "the changed spec COMPILES")
    if compiled:
        check("--spawn-secondary 3" in " ".join(compiled["args"]), "the secondary reaches the flags")
        check(len(compiled["party_row"]["heroes"]) == 2, "two hero rows in the party row")
        check(len(compiled["spawn_rows"]) == 7, f"seven hostiles ({len(compiled['spawn_rows'])})")
    path = win.run.save(os.path.join(out_dir, "smoke_spec.toml"))
    check(path and os.path.isfile(path), "the spec saves")
    if path:
        back = sandbox.load_spec(path)
        check(back["player"]["secondary"] == 3 and len(back["heroes"]) == 2, "and loads back")
    win.run.name.setText("smoke-bad")
    set_combo(win.player.secondary, 0)
    app.processEvents()
    check(not win.player.bar.slots[0].set_value(281),
          "with the secondary gone the bar no longer OFFERS a Monk skill (the window's "
          "own gate, ahead of the compiler's)")
    win.player.level.setValue(1)
    check(win.run.compile() is None and "spend" in win.run.summary.toPlainText(),
          "level 1 with level-3 ranks is REFUSED at compile, and the reason is shown")
    win.player.level.setValue(3)
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
