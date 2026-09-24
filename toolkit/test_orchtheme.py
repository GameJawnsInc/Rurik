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
does; section 4 pins the pairs the review found missing -- and for the danger
button's hover reads the SHEET, because the audit measures tokens and a row
naming the right pair stayed green with the sheet's ink put back to 4.22:1
(the verify round found that, and a `derive()` idempotence check that could
not fail either: derive() hands a derived palette straight back).
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import checks  # noqa: E402

LEDGER = checks.Ledger("orchtheme", floor=31)
ORCHTHEME = os.path.join(os.path.dirname(HERE), "tools", "orchestrator", "orchtheme.py")


def load():
    spec = importlib.util.spec_from_file_location("orchtheme", ORCHTHEME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def real_sheet(t, pal):
    return t.qss(pal, {k: f"/{k}.svg" for k in t.asset_svgs(pal)})


def rule(sheet, selector):
    """{property: value} of the sheet's rule for exactly `selector` (a rule
    whose selector goes on, `:hover` or `:focus`, is another rule)."""
    m = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", sheet)
    if not m:
        return {}
    return {k.strip(): v.strip() for k, v in
            (d.split(":", 1) for d in m.group(1).split(";") if ":" in d)}


def danger_pairs(sheet):
    """[(state, ink, fill)] the resolved sheet paints for the danger button's
    :hover and :pressed. A state rule that sets no colour keeps the base rule's
    -- which is how the first cut painted error_text on the chip fill."""
    base = rule(sheet, 'QPushButton[role="danger"]')
    out = []
    for state in (":hover", ":pressed"):
        r = rule(sheet, f'QPushButton[role="danger"]{state}')
        ink = r.get("color", base.get("color"))
        fill = r.get("background", base.get("background"))
        if ink and fill and fill.startswith("#"):
            out.append((state, ink, fill))
    return out


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
        sheet = real_sheet(t, pal)
        LEDGER.ok(not t.lint(sheet), f"{name}: the real sheet lints clean", f"{t.lint(sheet)}")
        odd = [k for k, v in t.derive(pal).items()
               if isinstance(v, str) and not re.fullmatch(r"#[0-9a-f]{6}", v)]
        LEDGER.ok(not odd, f"{name}: every derived token is a #rrggbb colour", f"{odd or 'all'}")
        roles = t.styled_roles(sheet)
        LEDGER.ok({"card", "primary", "quiet", "danger", "chip", "flat", "popup"} <= roles,
                  f"{name}: the sheet styles the roles the window stamps",
                  f"{sorted(roles)}")
    try:                       # log_fg: a key derive() never reads, so only the guard can refuse
        t.derive({k: v for k, v in t.DARK.items() if k != "log_fg"})
        refused = False
    except KeyError:
        refused = True
    LEDGER.ok(refused, "derive() refuses a palette missing a base key")

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

    print("\n4. the pairs the reviews found missing -- the danger hover read off the sheet")
    for name, pal in t.PALETTES.items():
        labels = {label for label, _g, _f in t.audit(pal)}
        LEDGER.ok({"muted on selection_bg", "check mark on a hovered checked box",
                   "tab focus fill differs from the page"} <= labels,
                  f"{name}: the muted-on-selection, checked-hover and tab-focus pairs are audited")
        pairs = danger_pairs(real_sheet(t, pal))
        LEDGER.ok(len(pairs) == 2 and all(t.contrast(ink, fill) >= t.TEXT_FLOOR
                                          for _s, ink, fill in pairs),
                  f"{name}: the danger button's :hover and :pressed rules paint an ink that "
                  f"clears {t.TEXT_FLOOR}:1 on their fill",
                  f"{[(s, ink, fill, round(t.contrast(ink, fill), 2)) for s, ink, fill in pairs]}")
        # one field height: a spin box's edit sub-control is 25 px tall to a
        # combo's 22 of content, so the spins' max-height (a contents height,
        # as QSS measures both) must be the wells' min-height -- read off the
        # sheet; --smoke measures the rendered heights
        wells = rule(real_sheet(t, pal), "QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox")
        spins = rule(real_sheet(t, pal), "QSpinBox, QDoubleSpinBox")
        LEDGER.ok(spins.get("max-height") == wells.get("min-height") == "22px",
                  f"{name}: the spin boxes' max-height is the wells' min-height (one field height)",
                  f"spins {spins.get('max-height')}, wells {wells.get('min-height')}")
    # the known-bad sheet: the first cut's hover, a fill change with the base
    # rule's ink kept (4.22:1 in light), must be refused
    light = real_sheet(t, t.LIGHT)
    prefix = re.sub(r'(QPushButton\[role="danger"\]:hover \{[^}]*?) color: #[0-9a-f]{6};',
                    r"\1", light, count=1)
    pairs = danger_pairs(prefix)
    LEDGER.ok(prefix != light and pairs
              and any(t.contrast(ink, fill) < t.TEXT_FLOOR for _s, ink, fill in pairs),
              "a hover rule that changes the fill and keeps the base ink is refused",
              f"{[(s, ink, fill, round(t.contrast(ink, fill), 2)) for s, ink, fill in pairs]}")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
