# `tools/orchestrator/` — the run orchestrator

A window that turns the vertical slice into a practice sandbox. **Skills**: which skills
are unlocked, account-wide. **Party**: the character to play (profession pair, level,
hands) and which heroes are unlocked, each with a profession, a body and a level.
**Enemies**: up to four groups of up to four hostiles, one the boss, each with its bar and
ranks. **Run**: compile, launch, reset. Then press **Launch**. The quest is the slice's own
— Fisk in Ascalon City, the west portal into the corridor, the groups, the boss, the
portal back, the turn-in — and everything else is yours to change.

**Bars and attribute ranks for the character and the heroes are set IN GAME**, on the
Skills panel (K), the attribute panel and each hero's own panel, exactly as on retail:
the server answers every slot write, swap, raise and lower for the character and for
each hero, and `--persist` (always on for a sandbox run) keeps what you set from one run
to the next in `vault/state/characters/`. A new spec starts the character with an empty
bar and every point unspent, and each hero the same with its level's points. **Reset the
stored character** on the Run tab wipes that state; the spec is untouched.

```
python tools/orchestrator/orchestrator.py                  # the window, the slice loaded
python tools/orchestrator/orchestrator.py --spec my.toml   # open a saved spec
python tools/orchestrator/orchestrator.py --smoke C:\scratch\out   # every panel once, no window kept
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
is yours. **Closing the game client ends the run and the stack.** The report and the server
logs land in `vault/captures/harness/<stamp>/` as for every harness run.

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
bar. A `*` after a skill marks one this server models beyond its icon from a HAND
`[skill_effect.*]` row; `~label` marks a **label-only** skill (SKILLS-LT, 2026-09-23): it acts
too, but through a label parsed from the client's own description template
(`vault/content/skill_labels.toml`, 47 rows on 38797; the file's header says how many) rather than a hand-verified row, and the
server's log says so at every cast; `--no-skill-labels` on the gamesrv drops them. The rest
draw and time correctly and do nothing.

Templates marked `(unwatched)` load closed but have never been seen rendering
(`studies/slice/RUN-PARADE.md` names the fifteen that have).

## Why `PySide6` is allowed here and nowhere under `toolkit/`

The split `tools/viewer/` made, one directory over: every fact — what a spec may say, where a
group stands, which ids are reserved, what the gamesrv is told — is `toolkit/harness/sandbox.py`'s
and `toolkit/content.py`'s, both stdlib and in the suite; this file holds widgets. PySide6 is
LGPLv3, dynamic-linked, never vendored; its row is in `PLAN.md` §6.1 and its credit in
`THIRD-PARTY-NOTICES.md`.

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
