# Quests — handoff to a cold session

**Written 2026-08-17.** **This is NOT a status document.** `PLAN.md` §3 is the status
authority and `PLAN.md` §8's *Quests* block is the live next-actions list; this file
deliberately does not restate either, because `CLAUDE.md` opens with what happened the
last time three documents each held a copy of the status and the newest was 40 hours
stale. What is here is the stuff that is *not* recoverable from the code: the traps, the
shape of the work, and the things a cold session predictably gets wrong.

**Read in this order.** `PLAN.md` §8 *Quests* (where it is) → `AUTHORING.md` §4 (the
ladder, with per-rung status) → `FINDINGS.md` §0 (what the arc settled) → the killed
answers and open questions of whichever of the two you are acting on. The two files
number those differently: in `FINDINGS.md`, §6 is killed and §7 is open questions; in
`AUTHORING.md`, §7 is killed and §6 is the blocked-vs-expensive triage — it has no
open-questions section of its own. (This sentence used to assert one shared §6/§7
layout, which sent readers of `AUTHORING.md` to the wrong sections.) `FINDINGS.md`
is ~1,200 lines; do not read it front to back to start work.

---

## 1. The one-paragraph state

A quest we authored is **offered, accepted, tracked, advanced and turned in at a real
retail client**, with a reward line on both screens and the marker moving between two
NPCs. The protocol underneath it is named in `schema/overrides.json` with evidence
chains. What is *not* done is the tail: no reward is actually granted, quest names are
still ArenaNet's string ids, and two known bugs are open by the owner's decision.

## 2. What will bite you, in the order it will bite

**~~The two open bugs are ONE fix.~~ THEY WERE NEVER ONE FIX, and the walk is DONE
(2026-08-19).** This bullet used to say that tightening `INTERACT_RANGE` alone would make
the quest unplayable because clicking a distant NPC does not walk the player over. The
premise under it — that the *client* walks you over on its own, so the walk was out of
our reach — is refuted: 46 c2s INTERACTs in the corpus carry 0 movement orders, and the
walk is a **server** message, `0x002A AGENT_UPDATE_DESTINATION`, that this server had
never sent. It sends it now, and an out-of-range interact is **held** and served when the
client reports it arrived (ArenaNet answers late by the walk's own duration, not never).
So `INTERACT_RANGE = 250.0` is now a plain unmeasured constant you may tighten on its own
merits — nothing is chained to it. Keep the other half of the old warning though: a
smaller range with no walk WOULD be unplayable, so never remove the walk to "simplify".

**`0x004C` before `0x0054`, always.** The client gates the objectives line on a
description-filled flag. Send them the other way and the objectives line is a **silent
no-op** that looks exactly like the client ignoring you. ArenaNet trips its own gate
twice in the corpus, so *copying the capture verbatim reproduces a bug you can see*.
`_replay_quests` gets this right and `test_quests.py` §17 asserts it.

**Never bulk-restore with `0x0049`.** Its body writes `charContext+0x528`, so the last
quest pushed silently becomes the active one. Use `0x0050`. Asserted, §17.

**`desc_sent` must not survive a connection.** `QUEST_PROGRESS` deliberately carries only
`quests` and `objectives_done`. Carry `desc_sent` too and the replay skips the `0x004C`
that arms the flag above — and the breakage appears **only on the second map**. Asserted,
§18.

**A word and the string id it denotes are different numbers** (`id = word - 0x100`). This
has cost real time twice, most recently as a live comment in `questdefs.py` claiming
"archive id 263" where the id is 7. Use `toolkit/clientscan/codedstr.py`; it refuses
rather than guessing.

**A literal run must open with a word ≥ `0x100`.** A description beginning `'S'` killed a
real client on `TextApi.cpp:585`. `coded_literal` refuses to build one — do not route
around it.

**A literal that exactly fills its field is a silent client kill — MEASURED 2026-08-18,
the day after this file was written.** Filling a string16 field to exactly its declared
cap hung a real client instantly (Code=007, **no assert**) on `0x00F3`'s string16(8),
while 7 of 8 units passed (`studies/character/RUNS.md`, title_track runs 1-2; the note
lives in `coded_literal`'s docstring). `coded_literal`'s default `limit` is still the
FULL declared width (128 for `0x004C` descriptions, 122 for `0x0080` dialogue) and its
length guard is exclusive, so an at-cap line sails through to the wire. Pass
`limit = declared - 1` — but that rule is measured on one 8-unit field only, so treat
the quest fields' caps as unverified hazards, not boundaries that pass.

## 3. Things that are true and easy to disbelieve

- **The dialogue gate is open.** `0x0080`+`0x0081` opens an NPC window; this was recorded
  as a blocker for a long time and is not one. `FINDINGS.md` §2.5.
- **We can author quest text**, the log *section* (`flags = 32` → Primary Quests), and
  — since 2026-08-19, CLOSED both halves — the **name**: 'A First Errand' at string id
  100552 (`textwrite.py --set`, reskin-roster archive), committed as `[0x8103, 0x0CC8]`
  in `content/quests.toml`, and RENDERED in the tracker and the 'Quest Added' toast
  (probe `quest_name_authored`, harness `20260819T085654`). The trap that outlives the
  rung: only the reskin-roster archive holds record 200, so any run that must show the
  name uses THAT client. `textwrite.py` has 188 authored skill names plus this behind
  it; seven recon lanes missed that tool once — do not re-derive it.
- **The binary claims are re-checked on 38833** (what the owner runs) as of 2026-08-17 —
  bodies unmoved, 12 cited sites byte-identical, `CHALLENGES` still 1465. But the scope is
  *"nothing moved across the 15-day 38797→38833 patch"*, **not** "these addresses are
  stable": on the vaulted 38519 build, 0 of 12 sites match. `test_quests.py` §20 re-runs
  it and covers a fourth build with no edit.

## 4. Where the next real result probably is

**The `0x004E` loopback run HAPPENED (2026-08-19) and the three dwords are named:**
experience, gold, skill points — the panel's own toast read them back off sentinel
values. `FINDINGS.md` §9.6 is the record; the probe is `quest_panel`, kept runnable as
the completion-panel calibration. What the reward arc still does not have is a **grant**:
the toast is display, no client state moved, and the rest of the completion family
(`0x006C`, `0x0096`, `0x0097`, `0x00FB`) is 0-of-corpus — that half needs a narrated
live mission completion. **The publisher question is CLOSED (2026-08-19, §9.7): those
same four opcodes are the panel's other four publishers** — the five-id band and the
completion family close on each other, with a `0x0096`/`0x0097` frame-id swap that
`test_framebus.py` now asserts so nobody tidies it away. **The ladder over that family
RAN (2026-08-19, §9.8): `0x0096` is MISSION_COMPLETE** — one flag bit draws the whole 3D
scene, f1 is `completionFlagsGained` (bit0 mission / bit1 bonus, gate at :729), and
fields 3/4/5 are a reward triple that rendered "111 experience, 222 gold, 333 skill
points" (so f3=xp, f5=gold in the MIDDLE slot, f4=skill points). `0x0097` is a sub-panel
keyed by a u8 over state a PRIOR completion message stages — a cold fire asserts at :678.
Q2b is closed, both halves (§3 above). **Everything the wire governs on the completion
DISPLAY is now mapped** (`0x004E`+`0x0096` rendered from our server, `0x0097`'s gate
located, `0x006C`/`0x00FB` screen-name-only). What is left is not offline: the GRANT
(client state moving, live capture) and `0x0097`'s priming message.

## 5. Open, unmeasured, and deliberately not guessed

- **`MAP_ID_COUNT = 877` vs `NO_MARKER_MAP = 888`** in `authsrv.py`, both meaning "one past
  the last map" in different places. Either two quantities or one is wrong. 888 is
  re-derived from `areatable.py` by §19; 877 is not. **Do not quietly make them equal.**
- **Which quest is active on a fresh load.** We take the lowest held id and say so.
- **Giver/objective binding is by AGENT ID** (`giver_agent = 99`), which is per-connection
  and per-spawn — a probe-world binding, not a content one. R5's job.
- **`0x0011`, `0x0013`, `0x004B`** are unnamed *on purpose*, each with a row in
  `overrides.json` saying what would settle it. Do not name them from shape alone.

## 6. Working notes that will save you an hour

- **Q6's code is done; its verdict is not.** *Walk a portal, confirm the log survives*
  needs a client, and that is the owner's — see the memory note on who drives runs.
- **Run the affected tests, not the suite** (~40 min). The arc's are `test_quests.py` (77,
  floor 73), `test_codedstr.py`, `test_framebus.py`, `test_dispatch.py`,
  `test_derivlint.py`.
- **Patching Python through a bash heredoc eats `\n` escapes.** Build the backslash with
  `chr(92)`, and **assert every anchor before replacing** — CRLF/LF mismatches make
  `str.replace` match nothing silently, which once let a change be reported as landed when
  it had not been.
- **Naming an opcode makes `test_dispatch.py` §7 go red** until it has an arm or a
  `DROPPED_ON_PURPOSE` row. That is the rung working, not a break.
- **Adding an upstream to `toolkit/` makes `test_derivlint.py` go red** until it has a
  §6.1 row, a notice, or a `NO_DERIVATION` entry. It fired within a day of landing on a
  case its author did not anticipate.
