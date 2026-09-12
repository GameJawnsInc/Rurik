# RUN-PARADE — what does each creature shell actually draw?

Registered 2026-09-11, **before the run**. Settles [PLAN.md](PLAN.md) SLICE-U2. Owner's
decision the same day: the parade, rather than picking ids off a table.

## 1. The question, and why the desk cannot answer it

`content/npcs.toml`'s own header says it: `enc_name` is "a list of 16-bit GW string ids,
not text… These can be copied and cannot be invented." We hold 56 NPC templates with
`file_id`, `model_id`, `profession` and `level` — and for all but **one** of them, nobody
has ever seen what the client draws. The single exception is the hatcher, and it is the
exception precisely because somebody watched it: its four words came back as
"Hatcher [Collector]" in English, which is a thing that was watched happen.

**The parade answers TWO questions in one frame, and the second is the one that makes it
worth a run.** The body tells us what it looks like; **the nameplate tells us what it is
called**, because the client resolves `enc_name` against its own string table and draws
the result. We do not name these creatures — the client does. That is the same route the
hatcher row was named by, and it keeps the provenance story unchanged: the ids are
committed, the string is resolved at run time.

**The profession byte is not a shortcut.** `studies/monsterai` measured it reading
"Ranger" on a melee-closing model and "Warrior" on a legless worm. It is in the roster
below as a column to be *checked against the picture*, never as the answer.

## 2. The roster — derived, not guessed

Every row below was resolved against the archive by
`python toolkit/mapdata/unitassembly.py --captures --definition <n> --shallow`, which
closed **266 of 266** captured definitions. `needs_body` is the structural fact that
decides whether a `0x0057 MONSTER_COMPOSITE` must accompany the definition: a shell whose
FA1 carries the composited flag has no geometry of its own, and withholding its body draws
**a solid white untextured box**. That failure mode is the parade's built-in positive
control (§4).

**Tier A — the Pre-Searing hostiles.** These are what the slice's two monster types should
come from.

| template | shell | body | needs_body | prof | lvl | wire notes |
|---|---|---|---|---|---|---|
| `def_1421` | 141267 | 116647 | yes | 1 | 2 | allegiance **band**, 26 creates, attack (1.75, 1.0) — the warrior-shaped candidate |
| `def_1420` | 116226 | 116642 | yes | 6 | 1 | allegiance **band**, 11 creates. **Resolves to only 5 files** — by far the smallest closure in the set, so this is the row most likely to look wrong |
| `def_1346` | 128483 | 129929 | yes | 2 | 2 | speed 360, health 96, attack (2.0, 1.0) — the only Tier A row with a full stat line |
| `def_1431` | 82023 | — | **no** | 6 | 1 | one shell at three levels |
| `def_1434` | 82023 | — | **no** | 6 | 0 | health 8, attack (1.75, 1.0) |
| `def_1442` | 116366 | — | **no** | 1 | 0 | the burrowing worm, already `lakeside_worm`; the one body whose behaviour is known |

**Tier B — the human shells.** Three shells carry 20 bodies between them (116228 × 8,
116227 × 7, 116225 × 5). These are the Ascalon crowd, levels 1–10, and they are where a
quest giver and a distinct-looking humanoid come from. Parade a sample of eight:
`def_1458`, `def_1465`, `def_1470`, `def_1473`, `def_1486`, `def_1490`, `def_1510`,
`def_2133`. All `needs_body = yes`.

`def_1473` is a known quantity and belongs in the frame as an anchor: `content/quests.toml`
already uses it as the quest guard, chosen because it looked different from `def_1471`.

## 3. Method

- One map, one area, bodies in a line at a fixed spacing, all `allegiance = "noncombatant"`
  and `attacks_back = false`. Nothing in this run fights.
- The harness drives it: spawn, then camera zoom/pitch/yaw and screenshots on a cadence.
  **No aiming is involved**, which is what makes this agent-pilotable rather than an
  owner-driven run — the boundary is aiming, and there is none here.
- Each body gets its own screenshot at a fixed camera, plus one wide frame of the whole
  line for scale comparison.

**One wrinkle to settle before the run, and it is a known defect class.** The `def_*`
templates live in the **gitignored vault overlay**, not in `content/npcs.toml`. A spawn row
in the tracked `content/world.toml` naming `npc = "def_1421"` therefore loads here and
fails on a bare machine — exactly `project-rurik-bare-machine-defect-class`. Either the
parade's spawn rows go in the vault overlay too, or the templates the parade PROMOTES get
copied into the tracked file with their provenance. The second is the point of the run, so
the first is the right shape for the run itself.

## 4. Pre-registered questions, and the exposure floor

Asked now, literally, because a question invented after the frames is a question the
frames can always answer (`feedback-ask-run-questions-before-the-run`).

1. For each of the 14 bodies: **does it render a creature, a white box, or nothing?**
2. For each: **what does the nameplate say?** (Verbatim. This is the deliverable.)
3. **Which two are the best warrior-type / monk-type pair** — most visually distinct from
   each other, both humanoid, both plausible as Pre-Searing hostiles?
4. Does `def_1420`'s 5-file closure render like the others, or is the small closure
   visible? (Registered as a specific suspicion, not a general worry.)
5. Do the three `82023` levels (`def_1431`, `def_1432`, `def_1434`) draw the same body at
   different sizes, or different bodies?

**The positive control.** One Tier B body is spawned **deliberately without its `0x0057`**.
It must draw the white box. If it does not, the run cannot distinguish "rendered wrong"
from "rendered fine" and the whole parade is unscoreable — this is the arm that proves the
instrument can see the failure mode.

**Exposure floor, and the abort.** A null here would be worthless without one
(`feedback-zero-exposure-is-not-a-null`). The run scores only if **at least 12 of the 14
bodies produce a legible frame** and **the control draws its white box**. Below that, the
verdict is ABORT — fix the harness and re-run — and specifically NOT "the shells do not
render".

## 5. What the run does not settle

- **Species identity beyond the nameplate.** If a nameplate reads as a generic label, the
  creature is named and still not identified. That is a result, not a failure.
- **Anything about behaviour.** No stats, no bar, no AI. The parade is a look-up table
  from `(shell, body)` to a picture and a name, and nothing else.
- **Whether these are the right creatures for the slice.** Question 3 asks for a
  recommendation; the choice is the owner's.
