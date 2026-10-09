# RANGERPRE — a casual Reforged pre-Searing run, and what it said about our server

*2026-09-29. One owner-driven live capture, `vault/captures/live/20260929T150923`, read by an
eleven-agent analysis workflow (seven lanes, one blind replication, three refuters) and then an
eleven-spec design workflow with a cross-spec critic. Written by the orchestrator: the lanes
returned data, this document is the judgement. Raw lane output stays in the session's task files;
every number below was re-derived by at least one refuter or the blind lane, and where a refuter
WEAKENED a claim, its corrected form is what is written here.*

**Identifiers.** `RANGERPRE-F<n>` = findings from the capture. `RANGERPRE-S<n>` = server-diff
build steps, in the critic's landing order (§4). The item column's words (`MAXHP-1`, `LOOT-1`,
`ROUTE-A`, `QUESTFLOW-H4`, `WEAPONREFUSE-B`, ...) are the design specs' item names, and §4's
rows define them. `RANGERLOOP-F<n>` = findings from the 2026-09-30 loopback runs, registered in
[CONFIRM-2026-09-30.md](CONFIRM-2026-09-30.md). Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

## 0. The run

- **Build 38888**, client dir `run-live/2026-09-01_44fbd68767a8`, secondary account, one client,
  human cadence. `livesession.py --mode reforged --plan ranger_presearing_roam.txt` — plan sealed
  before launch, both seals AGREE, 12 of 12 connections decrypted, 26 marks bound on wire time with
  0.0 ms two-clock drift.
- The owner deleted an old character, created a new **Reforged** Ranger (only the Reforged box
  checked — owner's statement), played the tutorial into Lakeside County (map 146), took Warrior as
  secondary, and walked into Green Hills County (map 160). Maps 148 and 164 were outposts. 23 F11
  notes, annotated by ordinal in the capture's `notes.txt` (vault-local).
- The plan was deliberately free-roam: one pre-registered question, R4c-2 coverage. Every
  behaviour finding in §3 is incidental to it and is labelled by what it rests on.

## 1. Coverage — the pre-registered question (RANGERPRE-F1)

Sealed prediction, step `roam`: *each explorable is its own game connection; `npcdefs` over this
capture creates hostile slots on maps other than 146, some never seen; health readings appear only
on foes the player damaged.* **All three held** [OBSERVED].

| | before this capture | with it |
|---|---|---|
| hostile definition slots, 2026-09-01 build, pre-Searing maps (146/160) | 13 | **18** |
| of which also byte-identical `0x0056` across ≥ 2 **captures** | — | 14 |
| of which across ≥ 2 **connections** | — | 17 |

- This capture creates **15 hostile slots**: 12 on map 146 {1346, 1397, 1420, 1421, 1428, 1431,
  1432, 1433, 1434, 1437, 1438, 1442}, 5 on map 160 {1414, 1415, 1428, 1437, 1439}. The blind lane
  derived the same set from the create bytes without `npcdefs`' verdict.
- **New to the project: 1414, 1415, 1438, 1439.** **Recovered: 1434** — absent from every
  September tape, created 6 times here, byte-identical to its 2026-07-29-build declaration with the
  same max health 8. Not recurring here: 1405, 1409, 1411.
- Owner foe labels joined to slots (the mark sits 0.13–0.58 s after the player's first landed hit
  in 7 of 7 engagement notes): Bandit Firestarter 1420, Aloe Seed 1428, Grawl 1437, Rogue Bull
  1397, Wolf 1346, Strider 1343 (`anim`, not hostile at create), Grawl Longspear 1438, Stone
  Elemental 1414, Grawl Invader 1437. 1437/1438 share file 141274 and model 141908; 1439 is the
  exception (file 141276, model 141909) — the owner's "Grawl share a model, with exceptions".
- **Max health is declared on the player's first LANDED hit**, in that batch, immediately before
  the damage word: 12 of 12, and never on the 514 NPC creates the player never hit. An attack order
  with no hit draws none. This is also a server divergence (RANGERPRE-S10).
- **"Independent" is undefined in R4c-2a criterion (i).** Two connections of one session to the
  same host 4 s apart are what carry 1414 and 1439; whether that counts is an owner ruling, open.

## 2. Reforged Mode is on the wire (RANGERPRE-F2) — and every pre-Searing capture is Reforged

The `--mode` flag, `content.py`'s mode rule and [MANIFEST.md](MANIFEST.md) §2 all rest on
"nothing in the recorded stream says which mode produced it". **That premise is refuted.**

- **The character flag** [CORROBORATED]. `GAME_SMSG 0x003C PLAYER_UPDATE_FLAGS [player, value,
  7]`, bit 2 (value 4), **read for the OWN player** (`0x0199` field 1 — player 1 is somebody else
  in towns and misreads PvP map 248). The same bit is the summary blob's flag bit 16
  (`charsummary.py` "pflag2"). Client 38797: getter `0x00815A80` feeds `0x0091D6D0`, which picks
  the skill-trainer price table `0xBFF5E0` (50..1000) or `0xBFF638` (25..500); both rows match
  WIKI's normal and Reforged trainer prices entry by entry. Static reads are 38797; not re-read on
  38888.
- **The zone effect** [CORROBORATED]. `0x0041 BUFF_TARGET_ADD [player, 0, 3434, 0, 1]` once per
  Prophecies explorable load: 15 of 15 pre-Searing explorable connections, 0 of the 112 others.
  WIKI names 3434 the Reforged Mode effect (+5% gold and XP, whole party opted in); the 38888
  skill row reads scale 105.
- **The create commit.** `0x008B` ends with a dword built `q(8)→1 | q(4)→2 | q(0x10)→4`; every
  create in the corpus sent 1, and the owner confirms only Reforged was checked → **bit 0 is the
  Reforged box** [OBSERVED + owner]. Upstream's "Reforged = 2" is CONTESTED by that. The map-0
  creation preview body carries `0x003C` value 0 — a map-0 tape says nothing about the character.
- **The September pre-Searing Warrior is Reforged** — both witnesses on the wire, and the owner
  confirms the badge in game. Its four captures (20260914T180058, 20260915T155656,
  20260915T164906, 20260916T172025) are stamped `base` in their manifests: **wrong**. The two
  August pre-Searing captures (20260807T143055, 20260810T235916) are `unrecorded` and also carry
  3434. **So every pre-Searing health number in the vault is a Reforged number and there is no
  base-mode pre-Searing control.** Five slots read exactly 0.8 × (20L + 80) (1420, 1343 at L1 = 80;
  1346, 1432 at L2 = 96; 1438 at L3 = 112); Nightfall and PvP slots read the unscaled 20L + 80; six
  pre-Searing slots fit neither formula (UNVERIFIED why). 1437 reading 64 in a `base` and a
  `reforged` capture was never a contradiction — both were Reforged.
- **Consequence today:** `npcdefs.resolve_mode` refuses the 2026-09-01 pool (15 `base` + 1
  `reforged`). That refusal is the mislabel surfacing, not a mode mixture. Manifests are untouched;
  correcting them, or deriving mode from the wire in `resolve_mode` so a declaration can be
  contradicted (the shape `origin_of` already has), is open (§5).

## 3. What retail did that we do not (RANGERPRE-F3)

Only the load-bearing shape of each is here; the design specs carry the byte-level detail.

- **Projectile dodge** (note 6). Flare, skill 194, projectile 343 at **1800 u/s** on 13 of 13
  launches — the `content/world.toml` speed was RECONSTRUCTION and is now OBSERVED. 13 casts, 4 hits,
  9 misses; both wire shapes are ours already. Retail hits land 7.9–48 u from the aim (one at 80 u),
  misses at 71–101 u; our `DODGE_TOLERANCE` is 24 u. 11 of 12 scorable launches separate at a
  threshold in (48, 71) u, against ~18 u of dead-reckoning error — a band, not a derived constant.
- **Condition immunity** (note 21). Sever Artery (382) on the Stone Elemental: `0x005D` coded
  **#1957** + `0x005E [1,7]`, no status bit, no effect word, no regen. The same skill on a Grawl:
  `[6,T,23]`, `0x00F1 [T,3]`, `0x00A2 [44,T,-rate]`; expiry `[7,T,23]`, `0x00F1 [T,0]`,
  `[44,T,+0.0]` (561 of 561 retail zeros are +0.0; ours is −0.0). Gash's condition gate is judged
  at impact. WIKI: non-fleshy creatures are immune to Bleeding, Disease and Poison. We have no
  immunity model and send no `[6]`/`[7]` for a condition at all.
- **Deep Wound** 64 → 52 (−12); ours rounds 12.8 to 13 → 51. Bleeding's rate is re-divided by the
  wounded max (−6/52). The NPC witness is n = 1.
- **Approach at range** (notes 5, 11, pickups). Retail answers an out-of-reach interact, attack or
  pickup within ~33–49 ms with integer corner legs (`0x0029`, mostly on a 32 u lattice), then a
  `0x002A` follow; attack start is `[4,P,T,0]`, `[8,P,1]`, `0x0028 [P]`; a dialog opened ~75 u from
  the NPC against our 144 u. Ours walks a straight `0x002A`.
- **Provoked animal** (notes 12–13). Hitting the `anim` Strider rewrote its token to `anin` by
  `0x002F` (with `0x009F` prop 65 = 0, 44 of 44), and it fought back. Ours never sends `0x002F`.
- **Loot** (notes 8, 17). The whole drop → reserve → pickup chain, gold by its own declare opcode
  `0x0162` (not absent from the corpus, as an earlier study said: 9 sightings in 3 captures),
  `0x0135` assigning the drop to the player for 600 s. We have no drops at all.
- **Quests** (notes 5, 14, 15, 23). Note 14 is **not** the completion family (0 of 350,851 s2c
  still). The reward item arrives by declare-then-add into the cell the quest item vacated. The
  secondary profession was granted by a dialog button — a non-quest `0x003B` our server drops.
  Retail's accept `0x0049` carries flags 0 on 5 of 12 and puts the marker on the objective; ours
  always 32, at the player. Reward skills follow the xp and gold (n = 3); ours go first.
- **Kill experience** varies by foe (26, 84, 105, 126, 176), refuting our code comment; every death
  frame after the first carries `0x009C [player,100]` + `0x00EE [10,0]`.
- **Weapon-type refusal** (after note 19): a bow skill pressed with a sword drew #1985 + `0x005E
  [1,7]` + `0x00E2` — the first wire witness for our `REFUSE_WEAPON_TYPE`, whose chatdefs premise
  ("the client very likely never sends the press") it refutes. A hand change persists across the
  next map loads; ours does not. A shield raised the player's max health 120 → 135 in the equip
  tick; ours does not.
- **Load order.** Retail sends the bar `0x00DA` before the library `0x00DB` on 126 of 126 game
  connections; ours the reverse.
- Also first seen: `0x015F` declaring other players' gear (34 messages, one outpost connection;
  [studies/playercomposite/FINDINGS.md](../playercomposite/FINDINGS.md) had it NOT FOUND).
- **High ground** (note 9): NOT MEASURABLE — the wire carries no height.

## 4. The server-diff steps (RANGERPRE-S)

Order and the conflicts behind it are the critic's; D = desk-verifiable against the capture,
L = needs a loopback client run. Status is kept here until each lands, then in PLAN-LOG.
**2026-09-29: the eleven D steps landed, then S14** on branch `rangerpre`, each implemented in a lane
worktree and APPROVED by an independent reviewer who re-ran its tests and its
fails-without-fix check (PLAN-LOG "RANGERPRE"). The commit named is each step's first; its
review fixes follow it on the same lane.
**2026-09-30: S10, S12, S15-S18, S20 and S21 landed** the same way, on lanes `rp2-a`..`rp2-d`
merged at `e968131a` and `d2fc95e1`. S16's and S20's last review rounds changed only their run
sheets. A loopback session then ran each step's pre-registered card on our client, and checked
six of the shipped D steps beside them: [CONFIRM-2026-09-30.md](CONFIRM-2026-09-30.md)
(PLAN-LOG "RANGERPRE's loopback confirmation"). S21's hand restore became the default after its
run (`bc8f409b`). **S19 is not built.**

| step | item | what | D/L | status |
|---|---|---|---|---|
| RANGERPRE-S1 | DEEPWOUND | floor the reduction; `deepwoundjoin.predicted_max` | D | **landed** `e913db63` |
| RANGERPRE-S2 | WEAPONREFUSE-A | always send #1985 + `0x005E` + `0x00E2` | D | **landed** `959b21b5`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §6) |
| RANGERPRE-S3 | IMMUNE-2a | the +0.0 regen zero | D | **landed** `a20fd763`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §6) |
| RANGERPRE-S4 | SECONDARY-A | `0x00DA` before `0x00DB` at load | D | **landed** `fcc0ddff`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §6) |
| RANGERPRE-S5 | QUESTFLOW-H1 | reward skills after the gold | D | **landed** `3a0de649` |
| RANGERPRE-S6 | KILLXP-a | per-foe kill xp; Reforged +5% seam, Prophecies-scoped, off by default | D | **landed** `75629da9` |
| RANGERPRE-S7 | KILLXP-b | the since-load 75-xp morale tick (supersedes QUESTFLOW-H2) | D | **landed** `c5a9e972` |
| RANGERPRE-S8 | QUESTFLOW-H3 | `[20, own, 7]` after `0x004A` in a hand-in | D | **landed** `22ef7cc3`; **CONFIRMED** on the wire at the client's hand-in ([CONFIRM](CONFIRM-2026-09-30.md) §3); its look is for the owner's eyes |
| RANGERPRE-S9 | DODGE | the across/along hit test against the retail band | D | **landed** `55ce30e6` |
| RANGERPRE-S10 | MAXHP-1 | an NPC's max declared on the player's first landed hit | L | **landed** `316a026b`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §4) |
| RANGERPRE-S11 | MAXHP-2 | a held max-health modifier (the shield) moves the player's max | D | **landed** `0ed70713`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §6) |
| RANGERPRE-S12 | ANIMAL | `anim` spawn, `anin` on first hit, fights back | L | **landed** `3bce62ed`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §5) |
| RANGERPRE-S13 | IMMUNE-2b | condition `[6]`/`[7]` effect ids + the (agent, buff) re-key | D | **landed** `31112797`; **CONFIRMED** on the wire and the target bar ([CONFIRM](CONFIRM-2026-09-30.md) §6); the body visual is for the owner's eyes |
| RANGERPRE-S14 | IMMUNE-1 | immunity model + #1957, with a tracked capture row for definition 1414 | D | **landed** `ce895d98`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §6) |
| RANGERPRE-S15 | LOOT-1 | gold drop on kill, pickup, purse credit (straight walk) | L | **landed** `3e0851cf`; the drop **CONFIRMED** on the client; the pickup CONFIRMED only under `--no-model-avoid-halt`: **by default MOVECODE-1z-dj's avoid halt cancels it beside a standing NPC** (RANGERLOOP-F8, open) ([CONFIRM](CONFIRM-2026-09-30.md) §7) |
| RANGERPRE-S16 | ROUTE-A | attack-start batch after an approach | L | **landed** `c26ecec5`; **CONFIRMED** on the client **on the first approach** ([CONFIRM](CONFIRM-2026-09-30.md) §8); the re-approach missed Q1's and Q6's windows, halting late and 134 u inside range once the server's mirror had diverged (RANGERLOOP-F9: the divergence **fixed on the desk 2026-10-07**, client run owed; the late halt split out as RANGERLOOP-F11, [CONFIRM](CONFIRM-2026-09-30.md) §12) |
| RANGERPRE-S17 | ROUTE-B | interact served ~75 u, with the stop/serve slack fixed | L | **landed** `1c1bc840`; **CONFIRMED** on the client, n = 2 ([CONFIRM](CONFIRM-2026-09-30.md) §9) |
| RANGERPRE-S18 | QUESTFLOW-A | accept flags, marker on the objective, rewards on accept | D+L | **landed** `55f7d0fc`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §2) |
| RANGERPRE-S19 | SECONDARY-B | a content-authored dialog button grants a secondary | L | open: **not built**, it waits on the owner's `0x00B6` ruling (§5) |
| RANGERPRE-S20 | QUESTFLOW-H4 | reward item + quest-item removal via one shared grant helper | L | **landed** `1c512339`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §3) |
| RANGERPRE-S21 | WEAPONREFUSE-B | persist hand changes across loads (default ON since the run) | L | **landed** `3ab6b017`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §1); the default flipped ON in `bc8f409b` |
| RANGERPRE-S22 | CONDHIT | an attack skill's condition needs a landed strike (§5, found by S14's reviewer) | D | **landed** `4cd9172e` (2026-10-07, lane `desk-condhit`; §5); the client look is owed (a runsheet, not a run) |
| RANGERPRE-S23 | BLINDCLOSE | a body's Blind-missed attack skill closes with its own `[46]`, not the swing's `[1]` (§5, found by S22) | D | **landed** `4ab669e0` (2026-10-07; PLAN-LOG "RANGERPRE-S23 and S24"; §5); the client look is owed (a runsheet, not a run) |
| RANGERPRE-S24 | BODYBLIND | a Blinded body's attack skill on another body rolls Blind's miss (§5, found by S22) | D | **landed** `4ab669e0` (2026-10-07, with S23; §5); the client look is owed (the same runsheet) |

**Deferred, with reasons** (critic's DEFER list): ROUTE-C corner-leg routing (contests
MOVECODE-1z-dn.5's "no route" closure, conflicts with LOOT's pickup walk, and our A* picks a
different corridor on 2 of 7 presses); LOOT slice 2 (what selects the drop line is unknown);
QUESTFLOW-H2 (superseded by S7), H5, H6; the +5% on by default (needs the Reforged effect item,
§5); corpus-census test sections (each step's bare checks already fail with the change disabled).

## 5. Open

- **REFORGEDFX** (not yet a step): serve `0x0041 [own,0,3434,0,1]` at a Prophecies explorable
  load and set the zone state S6's +5% reads. L.
- **Mode from the wire**: a derived game_mode that can CONTRADICT a manifest declaration
  (`resolve_mode`), and whether the four September manifests are corrected or annotated — the
  owner's call; nothing has been edited.
- Retail's kill frame carries the quest-objective lines (`0x0054`, `0x0051`) before the death flags;
  ours after (n = 1, found in passing by the critic).
- R4c-2a's "independent connections" needs a ruling (§1).
- ~~**Found by S14's reviewer, pre-existing:** `cast_tick` applies an attack skill's inflicted
  condition without checking the hit's result, so a missed or blocked Sever Artery still bleeds
  a fleshy foe (and, since S14, draws #1957 on a non-fleshy one). WIKI: the condition rides a
  hit only. Its own item; the repro is in the S14 review.~~ **CLOSED 2026-10-07 as RANGERPRE-S22, `4cd9172e`
  (lane `desk-condhit`; `test_condhit.py`, `--no-condition-needs-hit` the known-bad arm).**
  It was four sites, not one: the player's melee strike in `cast_tick`, `land_player_skill_shot`,
  `land_body_skill_shot` and `land_skill`'s attack arm each gated the knock-down and the random
  condition on `res == "landed"` and the skill's own condition on nothing. Re-derived at
  `1a678280` before the change: a landed Sever Artery (382) on a fleshy body leaves Bleeding;
  a Blind-missed one (`[38, 22, 1, 3]`, no word) and a blocked one (`[38, 22, 1, 0]`) left it
  too. Now `attack_condition_lands` gates all four.
  **The rule is OBSERVED for the player's melee attack skill under Blind** (n = 1 against a
  3-of-3 same-tape control) **and WIKI everywhere else.** The witness is an event the repo
  already held: **DAGGERS-F16** (`studies/daggers/FINDINGS.md` §8, RUN-DAGGERS-2, 2026-09-17)
  read this batch and its three controls for the chain — a lead that does not land sets
  nothing, no `0x005C`, and the Fox Fangs behind it fails with reason 2 — and moved that label
  to OBSERVED. Its Bleeding half went unread, and the triage, reading the corpus's two Blind
  misses as "none with a condition", missed that Jagged Strike 782 inflicts Bleeding. Over the
  live corpus (127 decodable game connections, 20260928T103123 :65009 set aside as declared
  gapped), 569 attack-skill activations `[50, A, T, S]` resolve as 510 landed, 19 failed (17
  reason 2, the chain; 2 reason 3, Blind), 27 stopped, 9 superseded and 4 with no resolution in
  6 s. Exactly one FAILED activation is of a conditioned skill:
  **20260917T224104 :62557, t=348.996** — the observer (25), under a live Blind (347.485-356.488),
  presses Jagged Strike at agent 117, whose status word carries no bleeding bit. The completion
  batch at 349.147 is E5, `[46, 25, 0]`, `[38, 117, 25, 3]`, E3, and nothing in the following
  second puts a condition on 117 (no `[6, 117, 23]`, no `0x00F1` bleeding bit, no `[44]`). The
  same skill on the same foe at 357.240, 395.754 and 442.328, the Blind gone, lands the word with
  `[6, 117, 23]`, `0x00F1 [117, 0x83]` and `[44]`, 3 of 3. Corpus-wide, 116 landed activations
  of conditioned skills (320, 382, 384, 392, 782 by our rows) show **their own** condition (its
  `0x0042`, its `[6, T, id]`, or its own status bit newly set, within 0.5 s) 99 times; the 17
  without it are 7 Jagged Strikes on a foe already bleeding (status `0x3`), 3 Gashes on a foe
  not bleeding (its own gate), 1 Sever Artery on the non-fleshy 22 (#1957), and 6 Jagged
  Strikes by agent 30 on 20260819T132414 (235.143-261.798) onto definition 3113 bodies that
  never carry a condition bit on that tape (consistent with non-fleshy; UNVERIFIED). (The first
  count, 100 and 16, took ANY newly set status bit for evidence and so read 254.648's target
  dying — `0x00F1 [137, 0x10]` at 255.607 — as a Bleeding; corrected by the review.) **What the
  witness does NOT cover:** every attack-fail word in the corpus that joins to an attack-skill
  activation (24: 22 reason 2, 2 reason 3) is a melee dagger skill (775 / 780 / 782) pressed
  by the observer (25 on the two 20260917 tapes, 27 on 20260819T132414); no tape shows an attack skill blocked or dodged, a skill SHOT
  missed, or a body's attack skill missed. So **the block at every site, and the miss at the
  arrow's arrival and at both body sites, are WIKI**: GWW "Hit" (rev 2721374) — "Any time an
  attack is blocked or misses, there is no hit" — and each conditioned skill's own sentence
  ("If this attack hits", "Sever Artery" rev 2738479; "If Jagged Strike hits", rev 2731014).
  The repo already had the dodge (a dodged shot sends the word and nothing else, retail 7 of 7).
  A None result — a dead target, or `--legacy-attack-finish`'s interval-gated strike that never
  happened — inflicts nothing too: RECONSTRUCTION (no strike read as no hit). For the dead
  target the wire is unchanged (the apply refused a corpse already); the legacy arm's bytes do
  move, and `--legacy-attack-finish --no-condition-needs-hit` restores them (the review's
  29-scenario differential, re-run by the fixer: byte-identical to `1a678280`).
  **What it does not touch:** spells and non-attacks (Blind's 90 % miss and a block reach
  attacks only — WIKI "Blind" rev 2667383: a projectile spell may stray instead, which we do
  not model; "Block" rev 2740767: no effect against spells), Irresistible Blow's block
  punishment (the content's only `knocks_down_if_blocked` row), the hit-or-miss clauses
  (Desperation Blow's self knock-down, Final Thrust's wipe). No other rider had the ungated
  shape: in the loaded content no attack skill opens an episode through `apply_effect` (33
  attack skills with rows), and the knock-down, random condition, adjacent damage and chain
  step were already landed-gated. Our Blinded player's Jagged Strike now completes with
  retail's 349.147 tokens exactly, and unblinded on a body whose maximum is undeclared with
  retail's 357.240 tokens exactly — MAXHP-1's `[42, 117, 480]` included (`test_condhit` 2a, 2b).
  **Found in passing, NOT fixed (not this item):** (i) `land_swing`'s Blind arm closes a BODY's
  attack skill with `[1, body, 0]` where its block arm sends `[46, body, 0]` — retail's one
  attack-skill miss (above) carries `[46]`; (ii) `land_swing_on_body` never rolls Blind for an
  attack skill (`skill_id is None and blind_miss(...)`), so a Blinded body's attack skill on
  another body always lands. **Both FIXED 2026-10-07 as RANGERPRE-S23 and S24** (the item
  after the runsheet below). (The 357.240 `[42, 117, 480]` first listed here as a third is
  not a divergence: it is MAXHP-1 / RANGERPRE-S10, the maximum declared before the observer's
  first landed word on 117, which ours sends too. The chain half, listed as a fourth, is
  DAGGERS-F16's, above.)
  Also open, and NOT bundled: IMMUNE-3, the #1957 sentence on the ranged, area and burst sites
  (they refuse the condition silently).
- **RANGERPRE-S22's client look — a RUNSHEET, owed, the owner's; not run.** Loopback, ours-DH,
  caged; the owner drives; `--no-energy` only so Sever Artery (adrenal, 0 s recharge) can be
  pressed at will. Four launches, each `python toolkit/harness/session.py --keep-open --hold 240
  --enemy --game-args "--party slice --enemy-health 2000 --no-energy <ARM>"`, with `<ARM>`:
  (A) `--enemy-skills 220` (the hostile's Blind on the player, 7 s every 8 s; offline, its
  `land_skill` puts 479 on the player); (B) A plus `--no-condition-needs-hit`; (C)
  `--enemy-skills 380` (the hostile's Bonetti's Defense on itself, a 75 % block; offline,
  `block_chance` 0.75); (D) C plus `--no-condition-needs-hit`. In each, target the hostile and
  press Sever Artery (slot 1) about ten times. PREDICTED in A, on each press made while the
  Blind icon is up (about 9 in 10): the swing, a yellow "miss" over the hostile, no damage
  number, and NO Bleeding on it — no bleeding body visual, no degeneration arrows on its health
  bar; the gamesrv log prints `[RANGERPRE-S22] ... the strike missed -- no condition` for each.
  Presses with no Blind up are the control: a number and the Bleeding. In C, a yellow "block"
  and no Bleeding on about 3 presses in 4. In B and D the same miss or block words draw AND the
  hostile bleeds — the pre-fix look, which retail's 349.147 refutes. Floor: 5 gated presses per
  arm and 2 landed controls, counted off the tape as `[38, T, 1, 3]` (or 0) with no
  `[6, T, 23]` in its batch. What would refute the fix: a bleed drawn on a miss or block in A
  or C, or an assert. UNKNOWN going in: whether the hostile's AI casts 380 on itself at all; if
  C shows no "block" in 60 s, record C as unexposed. Not a test of anything retail-side.
  **2026-10-09, after CONFPASS-F4:** the hostile casts 380 at all only because it charges on its
  own hits, and at the default `--enemy-hit 0.10` those hits kill the 140-health player about
  once a stance cycle. So C and D add `--enemy-hit 0.008` (1-point hits), and so do A and B,
  whose Blind-casting Hatcher killed the player 8 times per run too. With the player up,
  the Hatcher's 1.33 s swing re-opens Bonetti's every 11.2 s, so the stance is up about 89 % of
  the time. With a 75 % block that puts about 67 % of presses blocked, close to the "about 3
  presses in 4" above (MEASURED on v1, `20261009T135431`: 20 of 29). The harness rows, their
  floors and v1's run are in [CONFIRM-2026-10-08](../deskwork/CONFIRM-2026-10-08.md) §4.
- **RANGERPRE-S23 and S24 (2026-10-07): a BODY's attack skill under Blind** — S22's two
  found-in-passing defects, fixed on the desk; the banner at `authsrv.BLIND_MISS_SKILL_CLOSE`.
  **S23, the close.** `land_swing`'s Blind arm closed a body's attack skill with the plain
  swing's `[1, body, 0]` where its block arm sends `[46, body, 0]`. **Retail's close follows
  the ACTION, not the outcome (OBSERVED):** over the live corpus (`missjoin.fails`, every
  `[38]` with its attacker's close in the batch; prediction stated first: `[1]` beside a plain
  swing, `[46]` beside an attack skill, no body attack-skill miss on tape), both attack-skill
  misses close `[46]` ahead of `[38, T, A, 3]` — 20260917T224104 :62557 349.147 (Jagged
  Strike, above) and 443.448 (the 775 dual's first strike, DAGGERS-F17) — and the other 55
  misses, every one a plain swing, close `[1]`: 29 the observer's under Blind, 26 a body's
  (agent 120 at the observer, 20260916T213125 :57894; bufflog reads no 479 on 120, so their
  cause is UNVERIFIED). On the witness connection alone the observer's four misses are
  349.147 `[46]`, 433.145 `[1]`, 434.310 `[1]`, 443.448 `[46]` (`test_condhit` 1d). **The
  body's `[46, body, 0]` then `[38, T, body, 3]` is RECONSTRUCTION**: both `[46]` misses are
  the observer's, and it is that shape on the body's own close, which is `[46]` on its landed
  attack skills (`land_skill`'s attack arm, SLICE-F24, 124 of 124 that closed) and `[1]` on
  its missed plain swings (the 26). A body's skill SHOT carries neither close
  (`_without_melee_close`), so its bytes do not move. The BLIND banner's "RECONSTRUCTION by
  analogy" for the plain swing's `[1]` is OBSERVED since, and says so.
  **S24, the roll.** `land_swing_on_body` rolled Blind only for a plain swing (`skill_id is
  None`, since SLICE-H4's first cut `652db099`, no reason written), so a Blinded body's
  attack skill on another body always landed — where the same skill at the player rolls
  (`land_swing`'s player branch) and the player's own does (`hit_enemy`). It now rolls for
  both, melee and the skill shot's arrival. **WIKI**: GWW "Blind" rev 2667383 (a 90 % chance
  to miss with attacks) and "Hit" rev 2721374 ("Any time an attack is blocked or misses, there
  is no hit" — so S22's gate keeps the condition off it too). No tape shows the case. An
  unblinded body draws no random number (`blind_miss` rolls only under a live 479), so nothing
  else moves.
  **Flags:** `--no-blind-miss-skill-close` (S23) and `--no-body-skill-blind` (S24), separate,
  the known-bad arms; together they restore every pre-2026-10-07 byte of both sites.
  **Tests:** `test_condhit` §1d (the evidence), §10 (the fix at the player and at a body, both
  directions, melee and the arrow, each beside its unblinded control), §11 (each flag as a
  differential against its own fix), §12 (bare: the flags, `main()`'s wiring, the two sites);
  floor 4 -> 7 bare, 38 with the vault. All nine §10-§12 checks are red on `ab39c182`; with
  S23 alone inverted 10a-10c and 11a redden, with S24 alone 10b-10d, 11a, 11b and 12c.
- **RANGERPRE-S23 / S24's client look — a RUNSHEET, owed, the owner's; not run.** Loopback,
  ours-DH, caged; the owner drives. The standing hostile is given Sever Artery and a sword and
  fights the slice's Monk hero (the softest body inside aggro, SLICE-H3's pick: AR 60 under
  the Warrior's 80); the player Blinds it with 167 (the CONFIRM-2026-09-24 III3 route: `Blind
  on agent 10: buff 1, 10.0s`); `--no-energy` lets the hostile's adrenal 382 fire every swing
  and 167 be re-pressed at will. Three launches, each `python toolkit/harness/session.py
  --keep-open --hold 240 --enemy --game-args "--party slice --enemy-health 2000 --no-energy
  --enemy-skills 382 --enemy-weapon starter_sword --skills 167 <ARM>"`, with `<ARM>`: (A)
  nothing; (B) `--no-body-skill-blind`; (C) `--no-blind-miss-skill-close`. In each, let the
  hostile engage the hero, target the hostile and press 167 (slot 1) whenever its Blind icon
  is down, for about 60 s. **PREDICTED in A**, on each Sever Artery the hostile completes on
  the hero under a live Blind (about 9 in 10): the swing, a yellow "miss" over the HERO, no
  damage number and NO Bleeding on the hero (no bleed visual, no degeneration arrows on its
  party-window bar); gamesrv.log prints `attack_skill_finished: agent 10's skill 382 misses`,
  `attack_fail: 10 -> <hero> miss (Blind)`, `agent 10 swung BLIND at agent <hero> and missed
  (skill 382)` and S22's `the strike missed -- no condition` line. Strikes with no Blind up are
  the control: a number and the Bleeding. **In B** the same strikes under Blind LAND — a number
  and the Bleeding, the pre-fix look the WIKI refutes. **In C** the misses come back with the
  swing's `[1]` (the log's `melee_attack_finished` where A printed `misses`). **UNKNOWN going
  in, and the reason C is launched:** what the client draws for a body whose attack-skill
  action never receives its `[46]`. For the PLAYER an un-sent `[46]` held the attack-skill
  action open — the movement lock `ATTACK_FINISH_BATCH`'s comment records — so watch the
  hostile after each missed strike in C against A: does it stand rooted, hold the skill pose,
  skip or delay its next swing? Floor: 5 Blind-missed strikes per arm and 2 landed controls,
  counted off the tape as `[38, H, 10, 3]` beside `[46, 10, 0]` (A; `[1, 10, 0]` in C) with no
  `[16, H, 10, ..]` and no `[6, H, 23]` in its batch, where H is the hero's agent id (the log's
  SLICE-H3 `targets` line). What would refute the fix: a number or a Bleeding drawn on the hero
  from a strike the log shows Blind-missed in A, or an assert on A's `[46]`-then-`[38]` — the
  body case is RECONSTRUCTION, and the client may reject it. UNKNOWN too: whether the hostile
  engages the hero before the player (if the log's pick names the player, record the arm as
  unexposed for S24 — it is then S23 at the player's site). Not a test of anything retail-side.
- ~~The five test reds this capture caused (test_wearmap, test_adrenwire, test_movesync,
  test_routerbench, test_weaponcensus; test_npcdefs §8 would add two) are all confirming evidence
  breaking exact pins; the owner chose server diffs first, and they stay open.~~
  **2026-09-30:** the three files main's corpus-reds landing classified (test_adrenwire,
  test_npcdefs, test_movesync) were classified per connection and repaired there (`05e9392a`,
  merge `a7086a94`, PLAN-LOG "RANGERPRE's corpus reds"; the bare-machine skip is `8061941b`),
  and `rangerpre` took them at `30923224`. **The other three are still red** on `rangerpre` at
  `41e5032a`, re-run for this record: test_wearmap (1 check: 34 worn items not declared first on
  their own connection), test_routerbench (2: one click of 149 unanswered) and
  test_weaponcensus (1: WEAPONS-Q8, bow intervals of 2.63-2.72 s beside the pinned 2.476).
  **test_wearmap's 34 all come from this tape**, `20260929T150923` :53880 (OBSERVED, a
  per-connection scan of the live corpus); all three are red on `main` too, re-run
  there at `75d6a1e3` with the same failures. test_routerbench and test_weaponcensus are
  unclassified, whether this tape is their cause is UNVERIFIED, and all three stay open.
  **2026-09-30, later: all three classified per tape and repaired on `main`** (PLAN-LOG
  "RANGERPRE's corpus reds, the other three"). All three come from this tape, all three are
  the tests: wearmap's 34 are declared by `0x015F`, which the census did not read.
  weaponcensus's off-mode bows are three HOSTILES (`0x006D`), WEAPONS-C5, while the tape's two
  PLAYER bows read 2.478 / 2.479. Routerbench's click was sent inside the player's action hold
  after a pickup and superseded before the release (animref FINDINGS 30.4's law).
- **RANGERPRE-S19** (SECONDARY-B) is not built. It waits on the owner's `0x00B6` ruling: the
  secondary-unlock mask, which we never send ([studies/profession/RUNS.md](../profession/RUNS.md)
  §13).
- **The hand restore ships ON** (S21; `bc8f409b`). The client accepted the doubled `0x0147` on
  three relaunch loads and two zone loads ([CONFIRM-2026-09-30.md](CONFIRM-2026-09-30.md) §1),
  so `HAND_RESTORE` defaults to True, and `--no-hand-restore` is the known-bad arm. The fallback,
  which refuses an item another set's record names, is not built. Still NOT OBSERVED: what
  retail does to set k's record when set k's item is equipped into set 0.
- **The loopback confirmation's findings** ([CONFIRM](CONFIRM-2026-09-30.md) §10), each OBSERVED
  on our client:
  - **RANGERLOOP-F8, a defect**: MOVECODE-1z-dj's avoid halt cancels an S15 pickup beside a
    standing NPC (3 of 3 by default) while the client walks on and reaches the pile; under
    `--no-model-avoid-halt` 2 of 2 serve. So S15's pickup fails by default near a standing
    body until this is fixed. A fix task is spawned.
  - **RANGERLOOP-F9**: after S16's halt the AgTrack mirror walks the follow in (it never sees
    the `0x0028`), and a re-approach then halts late and 134 u inside range, after a 688 u
    `APPROACH RE-PIN`. The link from the one to the other is RECONSTRUCTION, n = 1.
    **FIXED ON THE DESK 2026-10-07** ([CONFIRM](CONFIRM-2026-09-30.md) §12; `b5316ab2`,
    `e9df994a`): two server models missed our `0x0028`, the mirror (the flights) and the
    legacy sync model (the 688 u re-pin, replayed at 687.9 u), and both now park where they
    stand (`--no-mirror-stop`, `--no-legacy-stop` the known-bad arms). The client run is
    pre-registered in §12.3. The late halt was neither: it is **RANGERLOOP-F11**, the
    2026-09-30 swing clock (last start 16.882917 + 2.475 + the 2.137 charge = the halt's
    21.4949), gone since MOVECODE-1z-ds.11/13 for RUN-T's sequence. Its general shape -- the
    halt rides a start the clock may hold past the arrival -- is open, retail's order
    UNVERIFIED.
  - **RANGERLOOP-F2**: quest-granted items draw an unresolved name. `content/items.toml`
    `starter_shield`'s "name id 8582" disagrees with `codedstr`'s 8326 for unit `0x2186`.
    **2026-10-07, desk (RESIDUE; no wire byte changed):** the comment is corrected in every
    row that said it (17 sites in `content/items.toml`): `0x2186` is the coded WORD for
    string id **8326** (word - 0x100, `codedstr.decode_id([0x2186]) == (8326, 1)`), the
    generic name the client draws on henchman and other players' gear (`textrec.py` resolves
    it; the text is not committed); `textrec` reads no text at id 8582. So the name is not
    malformed: it is retail's own unit, OBSERVED on **1,480 of 4,817** `0x0161` declares in the
    live corpus (3,427 single-unit names), and `starter_sword` / `starter_shield` are the
    level-3 Warrior henchman's bytes, so the rows keep it. **What retail's quest sword is
    (OBSERVED):** q75's accept on 20260929T150923 :56064 921.1613 declares item 704 -- file
    `0x800024EE`, type 27, model 2982, a 4-unit keyed name `[0x2711, 0xBD98, 0xE24F, 0x7FAE]`,
    and modifiers `[0x24B80200, 0xA4880302]`, **exactly `starter_sword`'s two words** (so the
    row's range word, labelled composed, is retail's too) -- seen 4 times (:53753 993.353,
    :53756 997.659, :56064 921.161, :59427 1216.783). q62's reward shield (item 1607, :53880
    727.4875) is file `0x80002538`, type 24, model 2817, keyed `[0x2651, 0x8429, 0xD6A6,
    0x3237]`, modifiers `[0x21A83205, 0x23480F00, 0xA3C80400]` -- NOT stat-identical to
    `starter_shield` (armour 4, two more words). **Why no row takes the keyed name yet:**
    (1) a retail-exact sword row is unsafe to declare -- `archive.binds_plainly` finds
    `0x800024EE` in NONE of the run archives (`run/slice`, `2026-09-01_44fbd68767a8`,
    `2026-09-30_8e50edfb8351`); the plain `0x24EE` binds row 8447, and a bit-31 id is a
    pending replacement the client compares exactly (`archive.py`); the shield's
    `0x80002538` likewise (plain `0x2538` is row 23136). (2) NOT a reason, corrected at
    review the same day: no test locks the default character's weapon KEY. The draft said
    `[party.slice] player_weapon = "starter_sword"` was pinned by
    `toolkit/harness/test_sandbox.py:211`, but that check reads `sandbox.party_row`, the
    sandbox compiler's own Warrior default (`PLAYER_ITEMS_BY_PROFESSION`), not
    `[party.slice]`. The one test that reads `[party.slice]`'s weapon,
    `toolkit/authsrv/test_agentlife.py:9086-9101`, pins its VALUES -- item type 27, the 2-3
    swing at 1.33 s, Swordsmanship rank 3 -- which a row with `starter_sword`'s type and
    modifiers keeps. So the stop rests on (1) and (3) alone. (3) A hybrid --
    `starter_sword`'s bound file and model with item 704's name -- is a composed item with no
    retail witness, and whether a keyed name draws on our client is a client question. So
    F2's real fix is a ruling plus a run: either a player-only sword row on a bound file with
    the keyed name (RECONSTRUCTION, run-confirmed), or serving `0x800024EE` from an archive
    that binds it. Also seen in passing: `starter_hammer`'s `0x80009B60` binds in none of
    those three run archives either.
  - **RANGERLOOP-F3**: `'anim'` draws neutral, not WIKI's green (retail's colour is
    UNVERIFIED), and space on it sends ATTACK.
  - **RANGERLOOP-F5**: a flags-0 quest's log heading reads as its own name (which field is
    UNVERIFIED). **2026-10-07, desk -- shipped, client owed:** the field is the FIRST string
    slot (s1) of `0x0049` / `0x0050`, OBSERVED static (`0x0091DB70` -> `0x0080F0A0` ->
    record+8 -> `0x0080DB40` -> arm 3 at `0x0057DD77`, string 1125) and CORROBORATED on 137
    of 137 retail log rows (one region unit, never s2, constant per home map and per quest --
    no quest is homed on two maps, so the corpus does not say which decides; 146 / 148 /
    160 carry `0x3D64`). A quest row's `enc_region` goes in s1 (`questdefs.log_strings`), both
    shipped rows carry `[0x3D64]`, `--no-quest-region` is the known-bad arm. s3 NOT FOUND.
    [studies/quests/FINDINGS.md](../quests/FINDINGS.md) §13. **Runsheet** (loopback, the
    owner's; the slice exe and archive, as CONFIRM §1): a run-only overlay directory whose
    `quests.toml` is `[quest.rurik_first_errand]` copied whole (row and provenance; an
    overlay row replaces the row wholesale) plus `quest_log_flags = 0`, named by
    `$env:RURIK_CONTENT_EXTRA`; then `python toolkit/authsrv/authsrv.py --map 148 --party
    slice --area errand,corridor`. Accept the errand and open the quest log: PREDICT it is
    filed under the REGION's heading (string 1125 fed `0x3D64`), not under its own name.
    Then the same launch with `--no-quest-region`: PREDICT its own name + the suffix, the
    2026-09-30 heading, back. gamesrv.log's `QUEST_ADD[1463]` says log flags 0 in both.
  - **RANGERLOOP-F6**: our accept re-unlocks skills the account holds, and the client shows a
    toast retail never draws. **2026-10-07, desk -- shipped, client owed:** `grant_skill` now
    gates its `0x001C` on `account_skills_held` (the stored list, else the `--unlocks` bitmap
    the load's `0x001D` carried, plus `skills_known`); OBSERVED 19 of 19 retail grants
    (`0x001C` iff outside the library in force), `--no-account-unlock-gate` the known-bad arm.
    [studies/quests/FINDINGS.md](../quests/FINDINGS.md) §14. **Runsheet** (loopback, the
    owner's): the same kind of overlay giving `rurik_first_errand` `accept_skills = [332,
    331]`, and an account library that holds 332 but not 331 and keeps the slice bar --
    `python toolkit/authsrv/authsrv.py --map 148 --party slice --area errand,corridor
    --unlocks 382,384,385,322,346,1,2,380,332`. Accept: PREDICT one skill-unlocked toast, for
    331 only (gamesrv.log: `SKILL_UNLOCKED(skill 331)` and none for 332; the slice bar is full,
    so both are learned and not equipped). Then the same launch with
    `--no-account-unlock-gate`: PREDICT two toasts, 332's and 331's -- the 2026-09-30 symptom.
  - **RANGERLOOP-F1** (no backpack grid under `--party slice`) is CLOSED: HEROINV fixed it on
    `main` (`5960cc68`, CONFIRMED on the client), and `rangerpre` took it at `30923224`. F4 (the
    client's re-select follows an allegiance change, CORROBORATED) and F7 (no PARTYMAX display
    issue) close questions rather than open them.
- The owner's eyes are owed on S13's body visual and S8's quest-complete visual
  ([CONFIRM](CONFIRM-2026-09-30.md) §11).
- The step reviews' named follow-ups are listed in [CONFIRM](CONFIRM-2026-09-30.md) §11 and are
  not scheduled: PARTYMAX, the animal's create batch, speed and strike, the pickup mid-swing,
  the held interact's expiry, the replayed marker and `0x004D`, the weapon reward line, and the
  persisted quest item.
