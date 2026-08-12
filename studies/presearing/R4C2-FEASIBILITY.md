# R4c-2 feasibility: can 35-40 monster types with real stats and skill bars be built?

*2026-08-11. Produced by a six-agent census (client tables, ArenaNet's recorded traffic, GWW,
the criterion itself, the content machinery) plus one synthesis told to answer honestly in
whichever direction the evidence pointed. The owner's instruction was "build it if it looks
good"; this document is the "if".*

**Answer: no, and one of the four clauses is not fixable by any amount of work.**

**Two load-bearing claims were re-measured independently by the orchestrator before this was
written**, because a feasibility verdict is exactly where a wrong number costs a session:

- `GAME_SMSG 0x00DA` occurs **11 times in 22,524** messages, and **0 of 11 target a `mon1`
  or `band` agent** (8 of the 11 target agents their connection did create via `0x0020`).
  So the skill-bar message is never sent for a hostile creature. Re-run:
  build `agent -> {class tags}` from every `0x0020`'s field[1]/field[12] per connection,
  then intersect `0x00DA`'s field[1] against it.
- The hostile definition slots are exactly **{1346, 1420, 1421, 1431, 1432, 1434, 1442} = 7**,
  from field[2] masked `& 0xffff` on creates whose field[12] tag is `mon1` or `band`.
  Class-tag census over the canonical 12 connections: `play` 405, `nonc` 244, `mon1` 233,
  zero-tag 117, `band` 37, `anim` 32.

Everything below is the synthesis as returned. Where it says "I re-measured", that is the
synthesis agent's own reader, which is a third independent pass over the same corpus.

---

R4c-2 is **not buildable today** — not as written, and not with a re-specification that keeps its shape. The measurement that decides it: ArenaNet's own recorded traffic contains **7 hostile creature types** (5 `mon1` + 2 `band`; 8 if the one `anim` slot counts), all from one 568-second visit to one map, against a criterion of 35–40 — and the second clause is worse than under-sampled, it is **structurally unreachable**: `GAME_SMSG 0x00DA` is the skill-bar message, it occurs 11 times in 22,524 messages, and **11 of 11 name a player agent**. A skill bar for a non-player agent is never sent to the client, so no capture campaign of any length produces one.

I re-measured the corpus independently rather than pooling the five censuses. 12 connections, 22,524 GAME_SMSG, 155 opcodes, 12/12 clean receipts. Everything below is from that run unless labelled otherwise.

---

## 1. The verdict

**Not buildable today.** Three of the four clauses fail, for three different reasons, and only one of the three is fixable by spending sessions:

| Clause | Status | Why |
|---|---|---|
| "35–40 monster types" | **coverage-blocked** | 7 in the corpus. Fixable by capture — a live campaign, one short session per explorable zone. |
| "real stats" | **partially instrument-blocked** | health: 3 of 7 types, and mode-ambiguous. Energy: 0 on the wire. **Armour: no property id exists in any channel** — not fixable by any authorized instrument. |
| "and skill bars" | **structurally blocked** | 0x00DA never names an NPC. 0 monster casts in 22,524 messages. Not a sampling shortfall. |
| "graded on types, never on spawn instances" | **survives, and should be strengthened** | Slot 1442 alone takes 202 of 585 monster-class creates. |

And a fifth defect nobody put on the rung: **numerator and denominator are counted in different units.** The wire's unit of a type is a definition slot; the wiki's is a page. 54 slots resolve to 32 distinct file ids, and slots 1431/1432/1434 are one model (file 82023) at declared levels 1/2/0 — one wiki page, three slots. "n of 91" is not evaluable in either direction and can exceed 1.0.

---

## 2. The honest count — what could get a row today

**8 rows, at capture strength, none of them named.** Full split, all measured this session:

**Tier A — capture-sourced identity (`source = "capture"`), 8 of 8 slots.** The 7 hostile (1346, 1420, 1421, 1431, 1432, 1434, 1442) plus `anim` 1343. Per row: `definition`, `file_id`, `scale`, `flags`, profession byte, level byte, `enc_name`, `move_speed`. Evidence: 126 × 0x0056 over 54 slots, **zero payload disagreements anywhere**, 38 slots declared in more than one capture, 48 of 54 instantiated, **0 created-never-declared** (which is what the client's own `index < m_count` assert forces).

`move_speed` is a new result from this pass and it is 8 of 8: create field 9 is single-valued per slot at n = 7 to 202 creates — 1346 360.0, 1420/1421/1434 288.0, 1431/1432 300.0, 1442 **12.0 in 202 of 202**, which independently reproduces `content/npcs.toml`'s hand-written `speed = 12.0`. Create field 10 is *not* a type property: it takes two values inside slots 1420, 1421 and 1343.

**Tier B — capture-sourced but partial:**
- `model_id` (0x0057): **3 of 8** — 1346, 1420, 1421. The other five are 0x0056-only and the field must stay absent, as `lakeside_worm` already does.
- `attack_interval` / `attack_modifier` (0x0035): **4 of 8** — 1346 = (2.0, 1.0); 1421, 1434, 1442 = (1.75, 1.0). Both fields are marshalled as dwords holding float32 bit patterns.
- `max_health` (0x009F property 42): **3 of 8** — 1346 = 96 (n=1), 1434 = 8 (n=2, two captures three days apart, two characters, two agent ids), 1442 = 40 (n=2, same agent). Five NPC events in the whole corpus; the other 23 prop-42 rows are the local player's `1` then `100`.

**Tier C — zero, from every source this project may use:** energy (0 NPC observations; published nowhere on the wiki either), armour (**no armour-shaped property id in any channel**; wiki armour is player-inferred back-computation and goes negative), skill bar (0 wire, and the wiki's Pre-Searing bars are event- and tier-contaminated — one agent reproduced §7's exact parsing error in its own parser and moved 15 rows when it fixed it), name (**0 of 8**).

**Types meeting R4c-2 as written — stats *and* a skill bar — today: 0. And 0 after any number of capture sessions**, because the bar is not on the wire.

**The denominator is CONTESTED between our own two wiki passes and I decline to pick.** MANIFEST §11: 91 hostile / 83 base-mode, from 206 pages. This session's fresh raw-wikitext read: 111 hostile / 60 base-ambient, from 225 pages. That is 22% apart on the total and 28% apart on base-mode, between two browser-route reads of the same wiki. Also structural and decisive: **`{{NPC infobox}} has no health key, no armour key and no energy key.** Health exists only as `==Notes==` prose written when the value is exceptional — 17 of 111. Armour reaches 37 of 111; both together, 10 of 111. So "wiki-seed the stats" is not a bulk route in the first place.

---

## 3. Re-specification, in §3.2's style

> **R4c-2 — split into three, because the roster, the stats and the name join are reached by different instruments and one number hides which is failing.** The old criterion — *"35–40 monster types with real stats and skill bars"* — cannot be evaluated: its denominator was superseded inside its own source and is now contested between two of our own wiki passes (91 vs 111 total, 83 vs 60 base-mode ambient); its "real stats" bundles a field with no instrument (armour) with one that has three observations (health); and **its "skill bars" clause grades a message ArenaNet never sends** — `0x00DA` occurs 11 times in the corpus and 11 of 11 name a player.
>
> **R4c-2a — the roster, *n* of 35 hostile definition slots.** A slot counts when (i) its `0x0056` payload is byte-identical across at least **two independent connections**, (ii) it has been created at least once under a non-player, non-noncombatant allegiance, and (iii) the row records `capture`, `connection`, `map_id`, `build`, `origin` and `mode`. **Today n = 7** (`mon1` ∪ `band`: 1346, 1420, 1421, 1431, 1432, 1434, 1442); the `anim` slot 1343 is reported beside it and not counted, because `anim` also carries the corpus's only NPC-versus-NPC combat and the token's meaning is not settled. Graded in **slots, not names** — the wire's unit is an array index and one wiki page can be three slots (1431/1432/1434 share file 82023 at levels 1/2/0). **35 and not 91 or 111** because those denominators count wiki pages, which this rung cannot count; the original 35–40 survives as a *slot* target and is reachable by capture at roughly one explorable zone per session.
>
> **R4c-2b — per-row evidence, *n* of R4c-2a's n.** A row is **VERIFIED** when every field the wire carries is read from ArenaNet's own bytes, joined **time-ordered** to the create in effect at that timestamp, and each field carries its own source. Otherwise it is **SEEDED**: it loads, it says so, and it is never counted. **Armour is struck from the criterion, not deferred** — 0 property ids across 22,524 messages, and a deferred column reads as "not done yet" and invites a session that cannot succeed. **Energy is struck** — 0 NPC observations, and published nowhere. **Health is gated on two prior settlements**, both cheap and neither live: property 42's *unit* (absolute or fraction — the player reads exactly 100, which is both "level-1 absolute health" and "what a percentage looks like"; settle it against our own client at a known value), and the mode stamp. Until both, health carries `mode = "unrecorded"` and may never be promoted. **Today: 3 rows, all unrecorded-mode, all of unsettled unit.**
>
> **R4c-2c — the name join, *k* named types.** Met when k definition slots have had their four `enc_name` words rendered by a client we control and the resulting English name matches a GWW-published creature. **Today k = 0**, and this is the clause that gates every wiki comparison: without it no capture row can be checked against any published level, health or armour, in either direction. k is stated as a small explicit number, not a fraction of 91 or 111, because that denominator is contested by 22% between our own passes.
>
> **"Uses a bar" replaces "skill bars", graded on named exemplars.** Met when k named types have been OBSERVED activating at least one skill on the wire. **Today k = 0** — 6 SKILL_ACTIVATED messages in the corpus, all the player; the single NPC cast belongs to a `nonc` noncombatant. Carried on the rung: a bar can only ever be *inferred from casts*, never read, because 0x00DA is not sent for non-player agents.
>
> **What a green R4c-2 would NOT prove**, carried rather than buried: (1) that any creature *behaves* like the retail one — AI as a mechanism is not recoverable and the numbers in `authsrv.py` are the wrong shape, not merely unmeasured; (2) that the health numbers are in the right units, unless 42 is settled; (3) that they are base-mode numbers, unless the mode was stamped; (4) that any creature uses a skill; (5) that armour is anything at all; (6) that spawn placement is right — types, not instances, by construction; (7) that the roster is complete, since our own two readings of the denominator disagree by a quarter.

---

## 4. Build plan for what is reachable today

**Write one extractor: `toolkit/authsrv/npcdefs.py`.** Stdlib only. No existing tool turns a capture into content rows; this is the whole gap and it is small.

- **Reads:** `vault/captures/live/<stamp>` via `vaultpath.require_dir` (never `../../vault`), decoded with `tape.channel_files` → `tape.load_tape` → `tape.decode_all(events, cod, "GAME_SMSG", 0)`. Refuses to pool captures whose `origin.origin_of` disagrees.
- **The one non-obvious piece:** a per-connection **interval map** `agent → [(t_create, t_remove, model, allegiance)]`, resolving every property message to the create *in effect at that timestamp*. A last-create-wins map is wrong on this corpus (below).
- **Emits:** `vault/content/npcs.toml` (bulk, gitignored, already merged over `content/` by `content.py`'s overlay), plus `--promote <key>` for one hand-reviewed row into the tracked file.
- **Fields and sources**, all `source = "capture"` under the 2026-08-11 ruling (measurement, not expression; `enc_name` is exactly the commit-the-id pattern): `definition`, `file_id`, `scale`, `flags`, `profession`, `level`, `enc_name`, `move_speed`; `model_id` where 0x0057 exists; `attack_interval`/`attack_modifier` where 0x0035 exists; `max_health` where prop 42 exists, carrying `mode`. `label` is `source = "invented"`. **No `armor`, no `energy`, no `name`, no `allegiance`** (slot 1480 is created 49× `nonc` and 9× `play` from a byte-identical declaration — hostility is a spawn fact), **no create field 10**.

**Three small changes to `toolkit/content.py`**, and they are the ruling's own conditions applied to the source that needs them most. All three gaps are verified, not asserted — I ran them:

1. `source = "capture"` requires **nothing at all** today: `_check_provenance('npc','x',{'health':999,'provenance':{'source':'capture'}})` **loads**. Add `capture`, `connection`, `map_id`, `build`, `origin` as required keys, and `mode` for any row carrying a combat-derived field. Capture rows are the *only* kind whose value depends on an unrecorded session property, and they are the only kind with no enforced conditions — exactly backwards.
2. `source = "wiki"` with a fabricated `health = 999` **loads**. Require `page`, `revision`, and which template field the value came from (an infobox key and a Notes prose bullet are not equal strength).
3. **`source = "measured"` is an escape hatch that makes the ruling's conditions opt-in by word choice** — it is defined as "read or checked against our own artifacts on this machine", which covers reading a table out of the vaulted client, and it triggers neither the extractor condition nor the build condition. Add it to `EXTRACTED` or narrow its definition so it cannot name ArenaNet's artifact.

**Test: `toolkit/authsrv/test_npcdefs.py`**, added to CLAUDE.md's suite list in the same commit, floor set from a real green run. Assertions the artifact can refute: 12/12 clean receipts; 126 × 0x0056 over 54 slots with zero payload disagreements; 48 instantiated, 0 created-never-declared; the hostile partition is exactly `{1346,1420,1421,1431,1432,1434,1442}` with 1343 `anim` apart; slot 1480 is the *only* slot under two allegiance tokens and the emitted rows carry no allegiance key; prop 42 yields exactly 5 NPC events over 3 slots {1346:96, 1434:8, 1442:40}.

**The sabotage that must go red — and it is live today, verified this session.** Replace the interval join with last-create-wins and the health reading for **agent 38 at t=18.169 in `20260807T143055`, connection `10.0.0.210:62994->54.198.7.73:80`** moves from slot **1434** to slot **1343** (agent 38 is re-created under a different model at t=74.779). The test must assert **both** directions: that the interval join gives 1434, *and* that the naive join gives 1343 — so if the two ever agree the control has gone vacuous and the test says so rather than passing. That is **1 of the 5 monster health readings in existence**, it is green on 99.8% of creates, and the error has now been made three times: by a skeptic on 2026-08-11, by one of the five census agents, and by my own first pass this session.

Three more sabotages: reading 0x0035's fields as `float` instead of as dwords-holding-floats (1073741824 read as a float is 2.5e-39, not 2.0 — the ROTATE_PLAYER trap); writing `move_speed` from create field 10 instead of field 9 (field 10 is per-instance for 3 of 8 slots); emitting `max_health` with no `mode` and having `content.py` accept it.

**Genuinely blocked, and on what — not padding:**

- **The name join.** Offline resolution from the owner's archive is blocked on a key we do not have: `textrec.py` reads the text format all the way down, but only **28.0% of language-0 records are plain** (`base == 0`, `bits == 0x10`); the other 72% are RC4 ciphertext with a caller-supplied key, entropy 8.000 bits/byte over 4.9 MB, 17 readings of "the key is a function of the record's identity" refuted at scale. **The census finding that "creature names are NOT in the archive" must not be carried forward as stated** — its own decode rate (26,705 of 101,376 = 26%) *is* the encryption rate, so it is a floor on a 26% sample, not a census. The Hatcher is the live counterexample: our client rendered "Hatcher [Collector]" from four words that same search does not find.
- The cheap route is the **loopback nameplate run**, and it is not desk work: send each of the 8 definitions with `agents.npc_properties` to our own client, stand next to it, read the plate. Ours-DH build, verified cage, one operator, zero ArenaNet contact. Prediction stated first: 8 of 8 render English names. Refuted if the client renders empty plates for a server-supplied EncString whose text file it holds encrypted — which is the real risk and the run's entire point.
- **Everything past 7 slots is blocked on coverage, and coverage is a live capture campaign** — one short session per explorable, human cadence. Seven hostile types came from 568 seconds of one zone; the manifest puts that zone alone at 30 foe pages.

---

## 5. Reforged Mode

Every health number this rung would produce is base or base × 0.8 and nothing on this machine can say which. The corpus cannot even be interrogated about it: 0 of 12 connections load a Reforged-only map (the map ids are 0, 146, 148, 164), and slot 1434 reads 8 in **both** captures three days apart — internally consistent, which is precisely what a systematically biased corpus looks like.

**What must change before one health row is written, and it is four small pieces:**

1. `toolkit/harness/livesession.py:810` builds `manifest.json`; add `reforged_mode`.
2. **A manifest field with a default is a wish.** Make it a required argument with no default, the way `--confirm` already is at `:620` and `:1024` — `--mode base|reforged`, run refuses without it, and `test_livesession.py` gains the refusal beside the three guards it already proves.
3. `origin.record()` takes `**extra`, so the value rides into `wire.jsonl` without a schema change — but **`origin.py` must not be taught to infer it.** Origin's design is derive-from-the-endpoint-never-self-declare; mode has no endpoint. It is an operator declaration and must be labelled as one. The one derivable witness (a Reforged-only map id on the wire) is one-directional and should be wired as a corroboration that can *contradict* the declaration, the same shape as `origin_of` refusing a `live` stamp on an all-loopback file.
4. `content.py` requires `mode` on any capture row carrying a combat-derived field, with a refusal in `test_content.py`.

Cost: one required flag, one manifest key, two refusal tests, one required-key check. **Hours, not a session** — and it must land *before* the next live run, so that the campaign's first capture is the first one that can be graded. `toolkit/harness/marks.py`, which two studies specify as where the flag belongs, **does not exist in this tree** — the stamp has an unbuilt dependency, and putting it in `livesession.py`'s manifest instead sidesteps that.

Retrospectively: the three health values in hand become `mode = "unrecorded"` — kept, never deleted, never promoted. `origin.py`'s three-valued ours/live/unknown is the precedent; `unknown` exists so a file is not forced into a claim it cannot support.

---

## 6. What would be dishonest to do

Named so the next session does not do them:

1. **Copying the wiki's 111-type roster into `content/npcs.toml` with `source = "wiki"`.** This is the single easiest green R4c-2 and it produces zero knowledge. It also *works today*: a row with `source = "wiki"` and a fabricated `health = 999` loads clean — I ran it. 35 rows in twenty minutes, every one of them a guess wearing a citation.
2. **Counting the 54 declared definitions, or the 48 instantiated ones, as "monster types."** 30 are `nonc`, 11 are `play`. Seven are hostile. Six are declared and never created at all.
3. **Counting spawn instances.** Slot 1442 is 202 of 585 creates. An instance count moves with session length, not content coverage — and "an instance" is not even well-defined, since agent ids are recycled.
4. **Promoting the `level` byte on the strength of generic-value 36.** The cross-check is *forced*: every NPC sample of property 36 is 1, so agreement and disagreement are both artefacts. Two studies predicted a future dive would run this check, see 8-for-8 on the non-zero subset, and promote the field. Do not.
5. **Calling the profession byte a profession.** It reads 11 on five definitions against `CHAR_PROFESSIONS_MAX = 6`, and it reads 1 ("Warrior") on a burrowing worm.
6. **Naming a creature by zone plausibility** — "the worm in Lakeside must be a Plague Worm." A name comes from a rendered nameplate or it does not exist. `lakeside_worm`'s own row already says this about itself.
7. **Writing an `armor` field of any provenance.** No wire instrument, and wiki armour is back-computed from observed damage — so fitting a damage formula to it closes the loop on itself.
8. **Quoting the wiki's skill bars without qualifier and tier handling.** A fresh parse this session moved 15 rows once `;`-qualified event bars were separated from base bars, and at least three entries in the manifest's own exemplar list are wrong in the same direction (Alain 7→0, both event-only; Grawl Crone 10→3, a union across level tiers).
9. **Reporting "n of 35" or "n of 91" as if the denominator were settled.** Our own two wiki passes disagree by 22%, and the wire counts slots while the wiki counts pages.
10. **Using `source = "measured"` to carry a client-extracted table past the extractor and build conditions.** The word choice currently decides whether the ruling's conditions apply. Fix the loader before anyone discovers it by accident.
11. **Calling the three health numbers base-mode.** They are 96/8/40 or 120/10/50 and this machine cannot say which.

**The one session that changes this**, and it needs no owner go-ahead and no ArenaNet contact: write `npcdefs.py` with the interval join and its sabotage test, close the three `content.py` enforcement gaps with refusals tested, make `--mode` a required argument, and do the loopback nameplate run on the 8 definitions already in the vault. That converts R4c-2 from ungradeable to merely unstarted, and it turns 8 opaque slots into 8 rows a wiki row can finally be checked against.
