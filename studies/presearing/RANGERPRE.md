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
| RANGERPRE-S16 | ROUTE-A | attack-start batch after an approach | L | **landed** `c26ecec5`; **CONFIRMED** on the client **on the first approach** ([CONFIRM](CONFIRM-2026-09-30.md) §8); the re-approach missed Q1's and Q6's windows, halting late and 134 u inside range once the server's mirror had diverged (RANGERLOOP-F9, open) |
| RANGERPRE-S17 | ROUTE-B | interact served ~75 u, with the stop/serve slack fixed | L | **landed** `1c1bc840`; **CONFIRMED** on the client, n = 2 ([CONFIRM](CONFIRM-2026-09-30.md) §9) |
| RANGERPRE-S18 | QUESTFLOW-A | accept flags, marker on the objective, rewards on accept | D+L | **landed** `55f7d0fc`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §2) |
| RANGERPRE-S19 | SECONDARY-B | a content-authored dialog button grants a secondary | L | open: **not built**, it waits on the owner's `0x00B6` ruling (§5) |
| RANGERPRE-S20 | QUESTFLOW-H4 | reward item + quest-item removal via one shared grant helper | L | **landed** `1c512339`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §3) |
| RANGERPRE-S21 | WEAPONREFUSE-B | persist hand changes across loads (default ON since the run) | L | **landed** `3ab6b017`; **CONFIRMED** on the client ([CONFIRM](CONFIRM-2026-09-30.md) §1); the default flipped ON in `bc8f409b` |

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
- **Found by S14's reviewer, pre-existing:** `cast_tick` applies an attack skill's inflicted
  condition without checking the hit's result, so a missed or blocked Sever Artery still bleeds
  a fleshy foe (and, since S14, draws #1957 on a non-fleshy one). WIKI: the condition rides a
  hit only. Its own item; the repro is in the S14 review. Also open: IMMUNE-3, the #1957
  sentence on the ranged, area and burst sites (they refuse the condition silently).
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
  - **RANGERLOOP-F2**: quest-granted items draw an unresolved name. `content/items.toml`
    `starter_shield`'s "name id 8582" disagrees with `codedstr`'s 8326 for unit `0x2186`.
  - **RANGERLOOP-F3**: `'anim'` draws neutral, not WIKI's green (retail's colour is
    UNVERIFIED), and space on it sends ATTACK.
  - **RANGERLOOP-F5**: a flags-0 quest's log heading reads as its own name (which field is
    UNVERIFIED).
  - **RANGERLOOP-F6**: our accept re-unlocks skills the account holds, and the client shows a
    toast retail never draws.
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
