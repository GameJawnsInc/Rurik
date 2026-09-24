r"""tools/orchestrator/orchtheme.py: the run orchestrator's palettes, stylesheet and
their contrast audit, checked on a bare machine.

    python toolkit/test_orchtheme.py

WHY A GUI MODULE HAS A TEST UNDER `toolkit/`. The orchestrator is PySide6 and lives
under `tools/`, outside the suite, which only discovers `toolkit/`. Its look is
checked by `--smoke`, which needs PySide6 and the vault. But `orchtheme.py` is
standard-library Python on purpose, so the part of the look that is arithmetic --
every text colour clears 4.5:1 on the ground it is painted on, the sheet carries
none of the faults Qt's parser accepts silently -- can run here, on any machine,
the way `test_blenderimport.py` reaches into `tools/blender/` without importing
`bpy`. This file imports orchtheme by path and nothing from Qt.

A CHECK THAT CANNOT FAIL IS NOT A CHECK. The first review of the beautification
found `lint()` blind to the negated form of the fault it exists for
(`X:!checked::indicator`, which Qt matches in every state, like the plain form),
and `audit()` missing a pair the sheet paints (the danger button's hover ink,
4.22:1 in light) while printing "clean". So section 2 plants each fault in a
sheet and requires the lint to go red on it, with a known-good control that must
stay clean; section 3 walks a colour the audit must refuse and requires that it
does; section 4 pins the pairs the review found missing.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import checks  # noqa: E402

LEDGER = checks.Ledger("orchtheme", floor=25)
ORCHTHEME = os.path.join(os.path.dirname(HERE), "tools", "orchestrator", "orchtheme.py")


def load():
    spec = importlib.util.spec_from_file_location("orchtheme", ORCHTHEME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    print("1. both palettes, both sheets")
    t = load()
    LEDGER.ok("PySide6" not in sys.modules, "orchtheme imports nothing from Qt",
              "it must run where the suite runs")
    for name, pal in t.PALETTES.items():
        LEDGER.ok(set(pal) == set(t.BASE_KEYS), f"{name}: the palette has exactly the base keys",
                  f"{sorted(set(pal) ^ set(t.BASE_KEYS)) or 'same'}")
        bad = t.failures(pal)
        LEDGER.ok(not bad, f"{name}: every audited pair clears its floor", f"{bad or 'clean'}")
        sheet = t.qss(pal, {k: f"/{k}.svg" for k in t.asset_svgs(pal)})
        LEDGER.ok(not t.lint(sheet), f"{name}: the real sheet lints clean", f"{t.lint(sheet)}")
        LEDGER.ok(t.derive(t.derive(pal)) == t.derive(pal), f"{name}: derive() is idempotent")
        roles = t.styled_roles(sheet)
        LEDGER.ok({"card", "primary", "quiet", "danger", "chip", "flat", "popup"} <= roles,
                  f"{name}: the sheet styles the roles the window stamps",
                  f"{sorted(roles)}")

    print("\n2. the lint goes red on every planted fault, and not on the control")
    planted = {
        "pseudo-class before a sub-control": "QCheckBox:focus::indicator { a: b; }",
        "the negated form": "QCheckBox:!checked::indicator { a: b; }",
        "after an attribute selector": 'X[role="a"]:hover::indicator { a: b; }',
        "chained pseudo-classes": "QCheckBox:checked:focus::indicator { a: b; }",
        "an unsubstituted token": "X { color: $tok; }",
        "unbalanced braces": "X { a: b; ",
        "a relative font size": "X { font-size: 1em; }",
    }
    for label, sheet in planted.items():
        LEDGER.ok(bool(t.lint(sheet)), f"red on {label}", f"{sheet!r} -> {t.lint(sheet)}")
    for sheet in ("QCheckBox::indicator:!checked { a: b; }",
                  "QCheckBox::indicator:checked:focus { a: b; }",
                  "/* X:focus::indicator is a comment */ Y { a: b; }"):
        LEDGER.ok(not t.lint(sheet), f"clean on the right order {sheet[:40]!r}", f"{t.lint(sheet)}")

    print("\n3. the audit can refuse")
    broken = dict(t.DARK, muted="#3a3f47")               # a grey that fails on the card
    fails = [label for label, _g, _f in t.failures(broken)]
    LEDGER.ok(any(label.startswith("muted on") for label in fails),
              "a muted grey that fails 4.5:1 is refused", f"{fails[:3]}")
    same = dict(t.DARK, hover=t.DARK["surface_btn"])     # hover identical to rest
    fails = [label for label, _g, _f in t.failures(same)]
    LEDGER.ok("hover differs from a button at rest" in fails,
              "a hover identical to its rest state is refused", f"{fails[:3]}")

    print("\n4. the pairs the first review found missing")
    for name, pal in t.PALETTES.items():
        labels = {label for label, _g, _f in t.audit(pal)}
        LEDGER.ok({"danger text on its hover and press", "muted on selection_bg",
                   "check mark on a hovered checked box"} <= labels,
                  f"{name}: the danger hover, muted-on-selection and checked-hover pairs are "
                  f"audited")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
