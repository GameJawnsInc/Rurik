# `tools/orchestrator/` — the run orchestrator

A window that turns the vertical slice into a practice sandbox. A **header** over four
tabs holds the spec's name (Open…, Save…, Load slice), a one-line summary of the spec, and
the three verbs — **Compile**, **Launch** (the one accent in the window) and **Stop** —
reachable from every tab. **Skills**: which skills are unlocked, account-wide. **Party**: the
character to play (profession pair, level, hands) and which heroes are unlocked, each with a
profession, a body and a level. **Enemies**: up to four groups of up to four hostiles, one
the boss — the groups and hostiles as a list on the left, the selected one's template,
weapon, bar and ranks on the right — added from the list's **+ Group** and **+ Hostile**, each
removed by the labelled **Remove** on its own page (a group holding hostiles asks first).
**Run**: the launch options, the stored character and its reset, the compiled result and the
harness's output. The quest is the slice's own —
Fisk in Ascalon City, the west portal into the corridor, the groups, the boss, the portal
back, the turn-in — and everything else is yours to change.

**Bars and attribute ranks for the character and the heroes are set IN GAME**, on the
Skills panel (K), the attribute panel and each hero's own panel, exactly as on retail:
the server answers every slot write, swap, raise and lower for the character and for
each hero, and `--persist` (always on for a sandbox run) keeps what you set from one run
to the next in `vault/state/characters/`. A new spec starts the character with an empty
bar and every point unspent, and each hero the same with its level's points. **Reset the
stored character…** on the Run tab wipes that state; the spec is untouched.

```
python tools/orchestrator/orchestrator.py                  # the window, the slice loaded
python tools/orchestrator/orchestrator.py --spec my.toml   # open a saved spec
python tools/orchestrator/orchestrator.py --smoke C:\scratch\out   # every panel once, and the look's laws
python tools/orchestrator/orchestrator.py --snap C:\scratch\out    # every surface to a PNG, never on screen
python tools/orchestrator/orchestrator.py --theme light            # dark / light / auto (follows the OS)
python tools/orchestrator/orchtheme.py                             # the contrast audit, no Qt needed
pythonw apps/orchestrator.pyw                              # double-click launcher
```

Without the window, the same run from a spec file:

```
python toolkit/harness/sandbox.py --example > vault\sandbox\mine.toml   # the slice as a spec
python toolkit/harness/sandbox.py --spec vault\sandbox\mine.toml         # compile, print
python toolkit/harness/sandbox.py --spec vault\sandbox\mine.toml --launch
```

## What a launch does

**Compile** turns the spec into a content overlay — a `[party.sandbox]` row with one
`[[party.sandbox.heroes]]` table per hero, and one `[spawn.sandbox_*]` row per hostile on the
corridor's map, the boss keyed `corridor_boss` so the quest's kill objective binds it — and
shows the overlay and the command before anything runs. **Launch** writes the overlay under
`vault/sandbox/<name>/`, points the server at it (`RURIK_CONTENT_EXTRA`, merged last over
the tree for this launch only) and at the slice archive (`RURIK_DAT`), and starts the usual
harness: `session.py --replace --keep-open` on `vault/run/slice/Gw.exe` with
`--game-args "--map 148 --party sandbox --area errand,sandbox --unlocks … --spawn-profession N"`.
The harness logs the client in (hands off the keyboard while it says so), and then the run
is yours. **Closing the game client ends the run and the servers.** The report and the server
logs land in `vault/captures/harness/<stamp>/` as for every harness run. How the run ended is
read off what the harness printed: a closed client is **client closed** (the harness retracts
its PASS by design, so the exit code alone would paint every session amber), a captured crash
dialog is **the client crashed** whatever the exit code — a timed hold whose client asserted
exits 0 — with the dialog's own line on the chip's hover, and a harness that could not start
says so and gives the verbs back. The verdict stays on the chip through the edits you make
next; the status line notes that the spec has changed since.

The corridor lives only in the slice archive: `python toolkit/mapdata/compose.py --name slice
--build` makes it if `vault/run/slice/` is missing (`RUNBOOK.md`, SLICE-B9), and a NEW run
directory needs the elevated cage step once.

## What it refuses, and why

The compiler (`toolkit/harness/sandbox.py`, stdlib, 88 checks in `test_sandbox.py`) refuses
before a client is launched: a bar skill outside the character's own professions (the
client's template rule); a hero body the content lacks; an eighth hero (the client's cap);
a fifth member or group; no boss, two bosses, or a boss not in the last group; ranks the
level cannot pay for (GWW's attribute points by level); a weapon class the rates table
lacks. The window's pickers only offer what the pair or the profession owns, so most of
those cannot be reached from it; the level/ranks one can, and the reason is shown.

## Names, and the gate

Every name on screen is resolved when the window opens: skill names off the pinned client's
own skill table and the archive's text files (`toolkit/clientscan/textrec.py`), hero names off
the extracted hero table's string ids, attribute names likewise. Nothing is written anywhere;
the spec on disk carries ids. A machine with no client shows ids and says why in the status
bar. The Skills list marks a skill this server models beyond its icon from a HAND
`[skill_effect.*]` row with a green **modelled** pill, and a **label-only** skill (SKILLS-LT,
2026-09-23) with a grey **label** pill: it acts too, but through a label parsed from the
client's own description template (`vault/content/skill_labels.toml`, 47 rows on 38797; the
file's header says how many) rather than a hand-verified row, and the server's log says so at
every cast; `--no-skill-labels` on the gamesrv drops them. The Enemies tab's bar slots say
`· modelled` / `· label` after the name in the same words, the Skills list's item text (what
its filter matches and a screen reader says) carries the same words, so typing `modelled`
into either filter finds the modelled rows, and the list's checkbox filter is **Modelled or
label** because it keeps both. The rest draw and time correctly and do nothing.

Templates marked `(unwatched)` load closed but have never been seen rendering
(`studies/slice/RUN-PARADE.md` names the fifteen that have).

## Why `PySide6` is allowed here and nowhere under `toolkit/`

The split `tools/viewer/` made, one directory over: every fact — what a spec may say, where a
group stands, which ids are reserved, what the gamesrv is told — is `toolkit/harness/sandbox.py`'s
and `toolkit/content.py`'s, both stdlib and in the suite. `orchestrator.py` holds the widgets,
`orchui.py` the helpers they are built from, and `orchtheme.py` (stdlib, runnable bare as
`python tools/orchestrator/orchtheme.py`) the palettes, the stylesheet and their contrast
audit. PySide6 is LGPLv3, dynamic-linked, never vendored; its row is in `PLAN.md` §6.1 and
its credit in `THIRD-PARTY-NOTICES.md`.

## The look, and what checks it

The rules are Dream-World-IX's (the owner's own PySide6 workspace, `studies/gui-aesthetics/`,
`studies/gui-ux/`, `studies/gui-strings/`), taken at the size of this tool — the rules and a
few small helpers ported or rewritten here (`orchtheme.py`'s docstring says which), not its
framework:

- **One loud object.** The accent is a fill spent on Launch and nowhere else: a checked box
  is neutral ink, a selected row tints toward the accent, the tab underline is a thin mark.
- **Every colour that carries text is walked to its floor** (4.5:1 text, 3:1 a focus ring or
  a status mark) against the ground it is actually painted on, and a chip's ink is solved
  against its own fill.
- **Cards, not group boxes** — QSS can colour a group box's title and nothing else — and a
  view inside a card is part of it, not a box in a box.
- **A sentence goes under a control, never inside it**; ids, flags and citations go on hover.
- **Text fits or is sized to fit**: a combo is sized in characters and shows the start of its
  text; the heroes table's Profession and Body columns are sized to their widest item (measured,
  not guessed); below 1,120 px the Character card goes above the table, its five fields three to
  a row; and a narrow hostile page stacks its Body and Weapon cards and puts its bar in one
  column, so no picker clips.
- **A hovered combo or spin box never changes under the wheel** unless it has focus; the wheel
  scrolls the page instead. (The wheel cannot GIVE it focus: Qt hands a hovered widget focus by
  its policy before any filter sees the event, so every combo and spin box is StrongFocus.)

`toolkit/test_orchtheme.py` (in the suite, bare) holds the arithmetic: both palettes clear every
audited pair, the sheet lints clean, the lint goes red on each planted fault, and the danger
button's hover and press rules, read off the sheet itself, paint an ink that clears 4.5:1 on
their fill (a planted hover that keeps the base ink is refused). `--smoke` holds the rest as
laws measured off rendered pixels — one accent and it renders gold, a checked box renders
neutral and shifts its fill under the pointer, a hovered danger button's painted ink clears
4.5:1 on its fill, a pressed button keeps its relief with focus on it, a log's scroll corner is
the log's own ground, a popup is one box in the popup edge with no row scrolled, the list
renders its pills and its empty-filter placeholder, focus shows on the list, the tab strip and
Launch (measured on grabs of the window: a widget's own grab is a transparent canvas on which
any fill counts), every profession fits its combo and every spin box shows its longest value at
1,280 and at 1,000 px, a real OS wheel over an unfocused combo scrolls the page and leaves the
combo alone with the window inactive and then active (where a focused one still takes it, and
an unlocked hero's Level spin scrolls the table), and no flag, file name, ident or hex id sits
on the visible surface. Layout and words have their own: every profession and every body fits
its heroes-table column and every choice in a hostile's slots, Template and Weapon fits its
field at 1,280, 1,120 and 1,000 px; the Character card is top-aligned beside the table and two
rows of three when stacked, its labels centred on their fields at the window's minimum height;
the Skills list's grade pills stand in one column near the name, not flush right; a group page
and a hostile page end at one right edge whether or not the hostile page scrolls; the tab
carries one labelled Remove per object (a group holding hostiles asks first) and no icon-only
verb; the status chip's right gap is the page gutter and the Run tab's COMPILED and OUTPUT
start at the card titles' x; every caption is one line, none says "the stack", the two Run wells
name what will appear, and every tooltip, special value and placeholder that is a sentence
starts with a capital. The window's STATE has laws of the same kind: the slice
opens one window and adding hostiles opens none (a label shown with no parent is a window of
its own), every input the compiler reads turns a fresh green **Compiled** into **Changed since
compile** while the Skills filters leave it green, a hostile's edit reaches its group's roster
line at once, a hostile at level 0 keeps that roster and the change signal, and a spec file
whose row fails inside the load leaves the spec as it was and says so. The Run tab's lifecycle
has its own: every line the end chip reads is one the harness still PRINTS (its print sites,
not its comments), a crash reads crit on exit 0 too, a run's verdict outlives the first edit
after it and an edit during the run is said when it ends, a harness that cannot start (the
real start path, a program that does not exist) leaves Launch enabled and the clock stopped,
the no-archive dialog's face is a sentence and the command with the citation behind Show
Details, the compiled status line names no path, the Compiled pane wraps, the live status
repeats no caption on the tab, and the Output log keeps a scrolled-back reader's line under
them at its block cap. `--snap` renders every surface to a PNG for a person to read; a visual
claim nobody looked at is a guess.

## Open on the client

What the retail client draws for a non-zero secondary on the player's own profession pair,
whether two heroes with different bodies both render and follow, and whether a character
and a hero built entirely in-game keep their build across a run, are SANDBOX-U1, U2 and U5
in [studies/sandbox/PLAN.md](../../studies/sandbox/PLAN.md), with their predictions
written before the run.

## Next

A filterable skill and attribute picker for the Enemies tab (SANDBOX-N1), and adding or
kicking heroes from the in-game party panel (SANDBOX-N2, whose client message is not yet
found).
