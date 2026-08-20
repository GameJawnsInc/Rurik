# Isle rung 3 — the offline bench: every question answered before a live minute

**2026-08-16**, worktree `combat-end-to-end-a2242b` at `c83a7cc` (after the merge of
`main`'s `65d803a`). Method: eight parallel bench agents, one per rung-3 item, then
independent skeptics on the three load-bearing verdicts (B1 gwinch, B8 chat oracle,
B9 formula). Skeptic corrections are folded in below **with attribution** — where a
skeptic refuted something the bench claimed, both halves are stated. Labels per
[studies/character/FINDINGS.md](../character/FINDINGS.md). Scratch scripts live under
the session scratchpad and `vault/research/isle-nameless-2026-08-16/bench/`; every
number quotes its command in the per-item write-ups archived there.

**Rung 3's exit criterion — each item ANSWERED or declared unreachable offline — is
met.** The table, then the detail:

| # | Item | Verdict |
|---|---|---|
| B1 | gwinch ladder | **ANSWERED, inverted**: the float-immediate lead was a coincidence; the radii are in `s_skill +0x6C` |
| B2 | `s_charDamage` | **ANSWERED**: 14 rows read; UI-only; damage type is not on the wire; inert for the Isle |
| B3 | `s_effect` | **ANSWERED**: it is the skill-VFX asset table; the "condition rows" premise dissolves |
| B4 | property 44 | **CONFIRMED offline**: net regen rate, quanta of 2/H — and it rides `0x00A2`, not `0x009F` |
| B5 | `0x00A4` | **ANSWERED**: shooter + target-position + flight-time-in-seconds; combat F9's CONTESTED resolved |
| B6 | property 17 crit | **still CONTESTED, materially moved toward crit**; the counterexample dissolved; a lone p17 kills |
| B7 | `behaviourrun` v[3:5] | **FIXED on `main`** (`c8c9c32`, another session) — delegated, not re-derived here |
| B8 | `0x005F` readability | **READABLE-NUMBERS-ONLY guaranteed** (as candidates — see the correction); rung 7 is unblocked |
| B9 | wiki formula vs corpus | **term-by-term**: quantization CORROBORATED 49/49; skill-base exact at rank 0; the armor exponent NOT REACHED |

---

## B1. The AoE radii are statically pinned — in `s_skill`, not in float immediates

**PLAN.md §3.2's "free static lead" is REFUTED as read, and replaced by something
better.** Skeptic verdict: SURVIVES WITH CORRECTIONS.

The refutation first, because §3.2 planned a disassembly of nothing: the f32 hits at
`0x5fb83e/0x5fbcba/0x5fc136` (252.0/322.0/624.0) are **.rdata byte-straddles inside
the `s_skill` table itself** — each "float" is two zero bytes plus the low 16 bits of
a name string id at record +0x98, and the 0x47C stride is 7 × 0xA4 (the skill record
size). Falsifiable form, 13/13: `f32((name_id & 0xFFFF) << 16) == ladder value` with
`u32@+0x94 == 0`. The ladder was monotone because string ids are allocated
monotonically. The 166.0 hits are ASCII `&C` from menu accelerators; the 1012.0 hits
are instruction-stream tails; the 5020.0 is a misaligned packed array. The skeptic
measured the coincidence rather than arguing it: strides 1×/2×/3×/5×0xA4 each "find" a
clean 10-12-value ladder, so the stride finds nothing.
**Skeptic correction kept:** ONE hit was genuine all along — 144.0 at `0x59ea78` IS
`s_skill[567].+0x6C` (Spontaneous Combustion), the very field below; and the "all
VA≡2 mod 4" claim is scoped to the four straddle sites only.

**The real find — CLIENT-DATA, `s_skill` field +0x6C** (in `skilltable.py`'s unparsed
gap), f32, 60 distinct values over 3443 rows:

| stored +0x6C | n | reading (RECONSTRUCTION via bucket names) | GWW measured |
|---|---|---|---|
| 144.0 | 1 | touch | **144** (exact) |
| 156.0 | 246 | **adjacent** | 166 |
| 240.0 | 183 | **nearby** | 252 (240 for an anomaly set — matches verbatim) |
| 312.0 | 144 | **in the area** | 322 |
| 1000.0 | 161 | earshot / party | 1012 |
| 2500.0 | 28 | binding-ritual spirit | 2512 |
| 3500.0 | 26 | nature-ritual greater | **3500** (exact) |
| 5000.0 | 79 | compass-wide | 5020 |

Bucket semantics were fixed by resolving member skill names against GWW's own range
wording (156 holds Epidemic/Death Nova/Chaos Storm; 240 holds Energy Surge/Eruption;
312 holds the four Wells and both Wards; 2500 holds Union/Shadowsong; 3500 is 26/26
Nature-Ritual-family — the skeptic re-resolved **all 573 names** of the 156/240/312
buckets with zero cross-bucket leaks). The table is owned by ArenaNet's own
`ConstSkill.cpp` (assert `index < arrsize(s_skill)` at the getter `0x005A88B0`; the
skeptic's bonus check: table base + 0xD73·0xA4 lands exactly on ConstSkill's string
pool).

**The pattern that matters for the Isle:** every GWW figure that is round (144, 240,
1000, 3500) matches the stored value exactly; every measured-looking one (166, 252,
322, 1012, 2512, 5020) sits 10-20 above it. UNVERIFIED hypothesis, and the Isle's AoE
markers are the instrument that tests it: **effective radius on the wire = stored
+0x6C + target bounding radius.** (`AgAgent.cpp`'s `m_boundingRadius` machinery is
what the assert sweep surfaced.)

**Who reads +0x6C: NOT FOUND in the client image**, with honest scope (101 getter
call sites' dataflow windows, every `fld/push [reg+0x6C]` in .text enumerated, the
candidates disassembled to other structs). RECONSTRUCTION: the radius test is
server-side; the client ships the table because client and server compile the same
Const data. **Bow ranges 1004/1273/1498: NOT FOUND four ways** (f32, f64, +0x6C
population, full-record sweep — the u32 "hits" are linked-skill ids). The bow
constants are capture-only; the AoE constants no longer are. §3.2's asymmetry claim
inverts cleanly.

## B2. `s_charDamage` — read, UI-only, inert for the Isle

OBSERVED: 14 rows at `0x6375CC..0x637604`, string ids 2001-2013 resolving to
Blunt/Piercing/Slashing/Icy/Shocking/Fiery/Chaotic/Unholy/Holy/Wooden/Sacrificial/
Ebon/Magical — 13 distinct, **row 13 duplicates Unholy** (why: UNVERIFIED, and
nothing reads it). Count confirmed two independent ways: anchor-string geometry
closes at exactly 56 bytes, and the accessor's own `cmp esi, 0xe`.

**Exactly one reader** (`codescan --xrefs`): accessor `0x005AAB70`, called once, from
`ItemName.cpp`'s description formatter — the tooltip's "Damage Type" line.
**Damage type is not on the wire**: schema types every damage-family field generic,
and the corpus enumeration (1242 × `0x009F`, 74 × `0x00A0`, 61 × `0x00A3`) contains
no field ranging over 0-13 or 2001-2013. CORROBORATED (schema + corpus agree).
Consequence: damage type is a display attribute resolved client-side from item data.
Nothing in the Isle plan depends on it; the armor test holds type constant by design.

## B3. `s_effect` is the skill-VFX asset table — and §3.3's premise dissolves

OBSERVED, and it retires two readings PLAN.md §3.3 carried:

- **Column +0x04 is a `Gw.dat` archive file id, not a string id** — 2076/2076
  nonzero values bind in the archive's own file-id table (control: 0/2000 random ids
  bind), and all 68 probed decompress to FFNA type 2, the **model** type.
  `consttable.py`'s `name_id` naming and docstring are wrong (repo fix owed —
  tracked separately; the bench was read-only). +0x08 is an alternate file id on 6
  rows behind a global toggle; +0x0C is constant.
- **The "condition rows are the prize" premise DISSOLVES.** `s_effect`'s index space
  is its own: skills reference rows via **six previously-unparsed dword slots at
  `s_skill +0x74..+0x88`**, null sentinel 2077. The ten condition skills have all
  six slots at sentinel — conditions own zero effect rows. Effect rows 478-486
  belong to consecutive Monk spells (Amity through Balthazar's Aura); the numeric
  collision with the condition skill-id block 478-486 was the whole illusion.
- **The hole is the engine's own null, not Cracked Armor.** Row 2036 holds 2077 =
  arrsize = the sentinel every slot uses. Zero slots reference 2036; Cracked Armor's
  record holds no 2036 anywhere. §3.3's "row 2036 holds 2077, which is exactly the
  Cracked Armor skill id" is numerology — retired.

Reader at `0x008EDED0` (`shl esi,4`, bound 0x81D, ConstEffect.cpp assert) — direct
indexing, 27 call sites, all cosmetic-loader paths. What §3.3 gains is a correction
plus one lead: the six effect slots are new structure `skilltable.parse_record` stops
short of, and `+0x8C/+0x90` look like the skill-icon string/file ids (UNVERIFIED).

## B4. Property 44 CONFIRMED: net health-regeneration rate, quantised at 2/H — on `0x00A2`

**Correction to PLAN.md §3.3 first: properties 44, 34 and 43 ride `0x00A2`**
(GAME_SMSG 162, the no-target float twin of `0x009F`), not `0x009F`. The value
census matches §3.3 exactly; the opcode did not.

The confirmation, where §3.4's skeptic had said no overlap existed: **the overlap is
the player.** The skeptic's "no agent with a measured max health carries a prop-44"
was true of NPC-interval-joined agents only — agent 31 is tag-3, invisible to an
NPC-keyed join. The player carries prop-42 = 100 AND prop-44 = 0.02/0.04 in two
captures: 1×2/100 and 2×2/100, exact in f32, twice. Dynamic check: integrating agent
50's rate ladder (1/48 → 2/48) across its two health-fraction snapshots predicts a
rise of 0.0680 vs 0.067688 observed — **0.5%**. Structural split: on-create prop-44s
are spawn state; mid-life ones fire when the rate *changes* (the player's regen ramp
starts ~5-6 s after last damage, stepping +1 quantum per ~2 s). The lone negative
(−1/90, spawn-time) is a net-degeneration spawn state; passive ticks are never
streamed, so its zero co-occurring health loss is expected, not damning.

**Still UNVERIFIED**: that one 2 hp/s step equals one HUD pip (needs a screen, not
the wire), and the H behind the on-create constants. The Isle closes both with zero
free parameters: a player at a known-pip Student, same connection streaming H —
prop 44 must step to (natural − condition) × 2/H at apply time.

## B5. `0x00A4` decoded: shooter, aim point, and flight time in seconds

**Resolves [studies/combat/PLAN.md](../combat/PLAN.md) F9's CONTESTED row** — GWCA's
name and monsterai's positional-oracle reading were two halves of one message.
OBSERVED across all 13 corpus samples:

- `v[1]` = the **shooter** (three independent confirmations; 12/13 are the player,
  the 13th is the `~706-unit` burrower — and 13/13 are ranged attackers).
- `v[2]` = the **target's position at the shot** (bit-identical to a stationary
  target's create position across three shots; tracks whichever party v[1] is not).
- `v[4]` as f32 = **flight time in seconds**: adding it to the launch timestamp
  predicts the subsequent damage arrival with mean |err| 9.3 ms, max 21 ms, 13/13.
  Implied projectile speed is per-weapon/creature (the NPC's one shot: 706.2 u /
  0.5885 s = 1200.0 u/s dead round; player shots ~2700-2900 u/s).
- `v[5]` as a skill id: **REFUTED** (a Necromancer id on a Ranger's auto-shots);
  reads like a per-shot correlation handle. `v[7]`: 0 in the wand session, 1 in the
  bow session — CONTESTED between weapon-class flag and per-session constant, and
  it is exactly what one melee comparison shot in the Isle session discriminates.
- Launch timing sits in the **same 0.44-0.47 windup band** measured for melee
  swing-to-landing — `0x00A4` is the ranged counterpart of the release instant.

Pre-registered Isle bow prediction: one `0x00A4` per shot at ~`base × 0.44-0.47`
after ATTACK_STARTED; `vec2` static at the dummy's spawn position; damage at
`t + v[4]` ± 20 ms; known marker distance / `v[4]` = a second, clean measurement of
arrow speed per bow.

## B6. Property 17: still CONTESTED, materially moved toward "critical" — and a lone p17 kills

The registered zero-variance test **cannot run on this corpus**: zero (target, cause)
groups hold ≥ 2 p17s — the apparent pair against agent 48 splits across causes 46 and
47 (same slot 1421; the two ARE bit-identical, which is the outcome crit predicts,
but it is not the registered test). What moved:

- **The 8-vs-25 counterexample DISSOLVED as a scope error.** Both 25s are skill-394
  hits; the 8 is the only auto-swing damage agent 278 ever took. Scoped by
  **(target, cause, swing-kind)** — the rule rung 7 must inherit — zero p17 sits
  below its p16 max anywhere, and the "glancing blow" reading loses its only
  evidence.
- Both well-sampled ratios land on `floor(1.414 × max p16)` exactly (4 = floor(1.414
  × 3), twice). CORROBORATED-leaning at n=2 groups; thin, and said so.
- **New OBSERVED fact:** agent 38 died of a lone p17 (9 damage on a 3/8 body, death
  markers 244 ms later, nothing between). **p17 debits the authoritative health
  ledger and REPLACES p16 for its swing** — refining `studies/agentprops` §1's
  client-side "does not modify the health record", and refuting "17 is an annotation
  riding a 16". This also settles §3.1's CONTESTED "17 replaces 16" from the corpus
  side; the rung-4 loopback render remains the cheap presentation check.
- The corpus's overkill (−1.125 on a 0.375 body) confirms the wire carries unclamped
  damage — amendment C4's premise "the wire's floor is −1.0" stays refuted.

Cheapest settler: rung 4's lone-p17 render probe; rung 7 runs the variance law
properly at n≥2 per scoped group.

## B7. `behaviourrun.py` v[3:5] — fixed elsewhere, recorded here

Fixed on `main` by the zealous-mahavira session (`c8c9c32`, merged `65d803a`,
merged into this branch as `2a2bd54`); PLAN.md §3.2 carries the full correction
block including the no-tainted-numbers audit. Not re-derived by this bench.

## B8. The chat oracle: the NUMBERS are extractable without any key

Skeptic verdict: SURVIVES WITH CORRECTIONS. **Verdict for rung 7:
READABLE-NUMBERS-ONLY guaranteed; likely fully READABLE; which of the two is
UNDECIDABLE offline solely because `0x005F` has zero corpus samples.**

The chain, with the skeptic's corrections applied:

1. **The schema shape is CORROBORATED, not UPSTREAM-only**: `0x5F` is among the
   744/748 messages where build 38797's own format tables agree with the import
   (`msgshape.py 0x005F` → `[agent_id, u8, string16(8)]`, RECV handler
   `0x0091dfa0`).
2. **`0x5F`'s string16 is a coded string** — its handler validates through the same
   EncString validator the NPC-name path uses (the client's own diagnostic names it),
   so the *prose* has the same decode problem as NPC names.
3. **But numeric arguments in coded strings are cleartext varints** — base-0x7F00
   accumulation at `TextParser.cpp 0x7ccd2a`, **no RC4 step on the argument path**
   (RC4 touches only the text record a sid points at). OBSERVED on real bytes twice
   independently: the quests arc's 66/66 re-encode, and this bench's direct decode of
   the 50 live `0x5D` messages — a plain "level up" template carrying args
   [13, 51, 1, 17]; encrypted templates still exposing clear args (1, 100, 2498, 10).
4. **Skeptic correction that changes the wording, kept:** encrypted-template
   messages ALSO interleave huge key-material varints, so a raw extractor returns a
   **mixed candidate list** — "yields X and Y" overstates; it yields cleartext
   candidates *among which* are X and Y, and binding number→role needs the template
   (if plain) or marker-structure separation. Rung 4's probe now includes
   round-tripping our own encode and the role-binding check. And the transfer from
   `0x5D` (observed) to a never-observed MoD announcement is **RECONSTRUCTION** —
   grounded structurally: per-session dynamic numbers cannot pre-exist in the static
   archive, so they must arrive as wire arguments, which are cleartext on every
   sourced path.
5. The two-channel mapping: the 5-number `/bow` report cannot fit `0x5F`'s 8 code
   units and would ride `0x5D` — **the channel that is present and decodable in the
   corpus today.** One captured announcement resolves plain-vs-encrypted; the numbers
   are already known-extractable either way.

The skeptic also extended the census: the other three live capture directories
decode zero game connections, so "three captures" is the complete decodable corpus —
a scope hole that closes in the finding's favor.

## B9. The wiki formula, term by term, against the corpus we hold

Skeptic verdict: SURVIVES WITH CORRECTIONS (all load-bearing numbers reproduced from
an independently-written decoder). The structural finding everything stands on:
**the wire fraction is an integer divided by target max health — 49/49 known-H
events exact to f32 epsilon.** Damage is computed in integer points, then
normalised. (H(1421) = 96·k from 5/96-irreducible, RECONSTRUCTION.)

| Formula term | Verdict | Evidence |
|---|---|---|
| Integer damage, fraction = n/H | **CORROBORATED 49/49** | quantization check; not forceable (random f32 passes at p≈0.1/event) |
| Skill base = stated value at rank 0 | **×1 clean, ×2 conditional** (skeptic's rewording) | 153 → 18 exact, both halves, armor-free; 394 → 25 and 105 → 30-pre-armor each need one assumption |
| Armor-ignoring vs armor-respecting is per-skill | **CORROBORATED** | 153 unattenuated vs 105 attenuated, same caster/target/minute |
| An armor attenuation exists | **CORROBORATED, one sample** | 105: 22 = 30 × 0.733 |
| The 2^(Δ/40) form specifically | **NOT REACHED** | one attenuation fits any monotone curve — needs the Suits' multi-AR ladder |
| Creature AR = 3·level + bonus | **FAILS TO DISCRIMINATE**, and the one sample needs bonus ≈ +15-18 on a level-2 beast (conditional on r_Death = 0, UNVERIFIED — skeptic) | Test A: 0.76 obs vs 0.90 wiki vs 1.00 null, noise > gap |
| Weapon SL = 5·rank, threshold | **NOT REACHED** | no rank on any wire |
| Crit = max base, AR−20 | **CONSISTENT, not probative** | see B6 |
| Rank-12/L20/AR-60 identity point | **STRUCTURALLY UNREACHABLE** | the corpus never leaves Pre-Searing |

Side findings kept: two same-slot attacker instances produce **byte-identical damage
multisets** against one target (per-type deterministic distributions); **the corpus
Wolf is level 2, not the Isle's level-15 Elder Wolf** — gww-facts §6's aside is
answered, a fresh capture is needed; **equipment changed between captures**
(ENERGY_MAX 30 → 25 on the four in-map connections per capture) while the item wire
stays undecoded, so no cross-capture damage comparison is ever same-weapon; E5's
trailing field equals the skill's client-table recharge (skeptic's bonus, an
independent no-rank-on-the-wire witness); and 153's rank pin — 18 + 2.8r = 18 →
**Blood Magic rank 0**, the damage itself as the rank instrument.

**What the Isle adds that this corpus structurally cannot** (now sharpened): a
target whose AR is stated by the instrument rather than inferred through the formula
under test; same attacker, three targets differing only in AR; H = 590 denominators
(at H ≤ 100 the integer step is 2-13% relative error — the size of the effects being
tested); the announced-total cross-check; a rank-controlled level-20 caster; a
recorded weapon.

---

## What this bench changes in the ladder

- **Rung 4 (loopback) grows two items and sharpens one**: the coded-string
  round-trip + role-binding probe (B8); the lone-p17 render keeps its slot with the
  corpus half already settled (B6: 17 replaces 16 on the ledger — the render answers
  presentation); the `0x0042` condition probe stands unchanged.
- **Rung 6 (roster pass)**: unchanged, still the first live session; the range star
  now has a static PREDICTION per marker (stored +0x6C + bounding radius?) instead
  of an open scan — the markers test the +10/12 hypothesis.
- **Rung 7 (damage pass)**: unblocked by B8; inherits B6's scoping rule — aggregate
  on **(target, cause, swing-kind)**, never (target, cause); expects `0x00A4` per
  bow shot with a per-bow flight-speed measurement for free (B5).
- **PLAN.md corrections landed with this commit**: §3.2's static lead annotated
  (refuted-as-read, replaced by `s_skill +0x6C`); §3.3's `0x009F` → `0x00A2` for
  props 44/34/43; §3.3's s_effect readings retired (B3); combat PLAN F9 marked
  resolved (B5).
- **Repo defect surfaced, not fixed here** (bench was read-only):
  `consttable.py`'s `s_effect` docstring/field naming calls +0x04 `name_id`; it is
  an archive file id (B3, 2076/2076 vs 0/2000 control). Tracked as a spawn chip.

---

# Rung 4 — the loopback probes: four runs, four measurements, one long detour

**2026-08-16/17, operator watching throughout.** The detour first, because its lesson
is a harness fact every future session needs: **`--hold` without `--keep-open` is
silently inert** — `session.py:1272` runs `hold_open` only under `a.keep_open`, so a
`--hold`-only session tears down at the verdict, ~4 s after spawn, closing a healthy
client whose orderly exit (game `0x0008`, auth `0x0009 UPDATE_CHARACTER_SETTINGS`,
status→Offline) reads exactly like a client-side death. (**FIXED on main
2026-08-17, `34091f5`**: `--hold` now implies `--keep-open` —
`hold_implies_keep_open()` in `session.py`, with the flag interaction and its
call site pinned in `test_harness.py`. The present tense above describes the
harness as it was during this rung.) Fourteen launches were
autopsied as deaths before the missing flag was found; the elimination matrix that
exonerated code, archives (to the point of a pristine restore), maps, flags and the
vault is preserved in PLAN.md's rung-4 status note as a monument. The 38797-default
config's separate pre-spawn failure is the archive-family issue
`studies/character/RUNS.md` already documents. Two keepers came out of the detour:
the `0x0009 UPDATE_CHARACTER_SETTINGS` ack arm (`6ce3875` — the message is departure
courtesy, not a blocked request), and the focus-sampler pattern for separating "the
client died" from "the harness closed it".

## R4-1. `encname_render` — the naming route is PROVEN, and the station has a name

OPERATOR-CONFIRMED RENDER: the body spawned 150u out wearing the outfitter/merchant
model (matched by the operator against Gelsan the Outfitter's family on GWW), carried
a readable red **"Outfitter"** nameplate, and despawned clean. The captured
`enc_name` tuple `[3943, 39638, 36630, 30448]` → readable text via our server and our
client, no RC4 key anywhere — the exact route rung 6's roster identification depends
on. Bonus: `agentroster.py`'s cross-session station (slot 1470, model 116698,
map 148, pos 8436,4819) is now **named**: the Ascalon City outfitter. One bound
recorded en route: declaring at index 1470 vs index 25 made no difference to the
detour-era teardown — the small-index note in the probe stands as caution, unproven
either way.

## R4-2. `condition_render` — 478=Bleeding, 480=Burning, and degen is the server's job

OPERATOR-CONFIRMED: skill 478 rendered the **Bleeding** condition and 480
**Burning**, classified as conditions on the operator's own character. Two points
landing exactly in `s_charCondition`'s order move the id→condition mapping
UNVERIFIED → **CORROBORATED**: 478 Bleeding, 479 Blind, 480 Burning, 481 Crippled,
482 Deep Wound, 483 Disease, 484 Poison, 485 Dazed, 486 Weakness (+2077 Cracked
Armor, step unobserved — still open). And the operator's "they did no damage" is the
third measurement: **the client renders a condition and does not self-apply its
degeneration** — health stays server-authoritative, so rung 8's server-side condition
model must send the degen itself, which is precisely what B4's `0x00A2` property-44
rate (quanta of 2/H) provides the mechanism for.

## R4-3. `lone_p17` — the three damage kinds separate on screen, and the prediction lost

Measured off the harness screenshots (bar values legible): **100 → 90** on the
property-16 control, **90 → 80 on the LONE property 17** — the orb moved, refuting
this probe's own stated prediction — and **80 → 80 on property 18**. So:

| kind | client bar | server ledger (B6) |
|---|---|---|
| 16 | debits | debits |
| 17 | **debits** | **debits — a lone 17 kills** |
| 18 | does not move | (never observed live) |

`studies/agentprops`' "raises the notification, skips the health record" was right
about the mechanism and wrong about the id — it belongs to **18**. Client and server
agree on 17: it is a full damage kind, and "17 replaces 16" is settled on both
halves. What 17 *means* (critical is still the lean, per B6's floor(1.414·max) fits)
remains rung 7's variance test.

## R4-4. `coded_chat` — the tag is required, the numbers render, and two hazards have names

Three sessions, operator watching:

- **Bare `0x5D` renders NOTHING and is silently held** — no refusal, no display.
  Live traffic never sends it bare; paired verbatim with its captured `0x5E [51, 10]`
  channel tag, the control **rendered**: the operator read *"is now level 17!"* in
  chat — ArenaNet's level-up template with its numeric argument displayed **in the
  clear**. The announcement-number path rung 7's Master of Damage reading depends on
  is now proven on a real render, not just a decode.
- **Both our-argument variants were refused** (`Invalid coded string` ×2), and the
  cause is sharper than the varint rule: our arg value **7** encodes to `0x107`,
  which is the **literal-run marker record** (`questdefs.LITERAL_MARK`). The
  0x100-biased value range **contains control ids**, and 7 collides. ArenaNet's own
  args 13/51/1/17 (0x10D/0x133/0x101/0x111) pass, so the collision set is specific,
  not the whole low range. The multi-word varint encode therefore remains
  UNEXERCISED — the refused lines never got as far as judging it.
- **`0x5F` with a bare non-chat sid CRASHED the client** — `c0000005`, memory at
  0x00000000 could not be read, no assert text — after rendering nothing. The
  overhead-text path dereferences something our bare-sid message does not provide.
  **Never send `0x5F` with an arbitrary record**, and the overhead half of the
  oracle stays unproven; the `/bow` report rides `0x5D` anyway (B8), which is the
  half that now works.

Next iteration (cheap, no session needed to design): args chosen outside the control-id
range, no `0x5F`, and one step isolating the multi-word varint.

## Rung 4 verdict

Every probe produced a measurement; three of four settled their question outright and
the fourth proved the load-bearing half of its channel while naming two real hazards.
The rung's exit criterion — each named question resolved with an operator-confirmed
render — is met for R4-1/2/3 and met-with-residuals for R4-4 (the varint and the
overhead channel carry to the next loopback pass; neither blocks rung 6 or rung 7's
chat-log half).

## Rung 6 prep: what a live pass actually has to DO (measured, not assumed)

The first draft of the rung-6 plan was 70 steps — target every body on the island once,
in a pre-registered order. The owner's reaction ("70 steps is a lot") was correct, and
checking it against the corpus rather than defending it showed the targeting buys **none**
of rung 6's stated exit criteria. Three measurements, all from captures already in the
vault, `toolkit/authsrv/agentroster.py` doing the reading.

**1. Names arrive unprompted, without exception. OBSERVED.** Every NPC definition slot
referenced by a `0x0020` create also arrived carrying its `enc_name` on `0x0056` —
**246 of 246**, across 8 distinct maps (146, 148, 164, 212, 238, 242, 416) and three
sessions (`20260807T143055`, `20260810T235916`, and today's four). Not one miss. The
run that produced today's captures carried a 13-step plan with no systematic targeting,
so this is not an artifact of the operator having clicked things: the server volunteers
the definition, and the definition carries the name.

**2. Position, slot, model and allegiance also arrive unprompted.** They are fields of the
create itself (`v[2]` tagged ref, `v[5]` pos, `v[6]` plane, `v[12]` allegiance), so the
agent-id ↔ definition-slot ↔ model-id ↔ `enc_name` ↔ coordinate table — rung 6's entire
exit — is a *consequence of being in the instance*, not of interacting with anything.
`20260817T183756` alone yields 97 creates (53 NPC, 29 item, 15 player) and 42 named
definitions from a session that never set out to census anything.

**3. What delivery IS gated on is DISTANCE, not attention. OBSERVED.** Splitting map 242's
NPC creates at 5 s after the first:

| connection | early n | early mean d | early max d | late n | late mean d | **late min d** |
|---|---|---|---|---|---|---|
| `:60966` | 32 | 2590 | 4463 | 21 | 4786 | **3117** |
| `:58389` | 21 | 3243 | 5418 | 24 | 7553 | **5136** |

The two populations are nearly disjoint in distance from the player's own create, and the
late arrivals run out to 108 s. That is a proximity-streaming signature: the instance sends
what is near you at load and the rest as you approach. **So the roster is completed by
WALKING, and a body never approached is a body never sent** — which is the real failure
mode a rung-6 plan has to defend against, and it is not the one the 70-step draft was
defending against.

**Consequence for the plan.** Coverage replaces enumeration: stand still through the load
burst, then walk the island so that every region comes within streaming distance, and
spend a handful of steps on spot checks rather than sixty on a census the wire performs by
itself. The trimmed plan is `vault/plans/isle_rung6_roster.txt`. The spot checks are kept
deliberately — they are the one thing targeting still buys, a human-witnessed link between
what the screen displays and the `enc_name` id we recorded, which is a check that can fail.

**Not established, and left alone:** *why* the late creates are late. Proximity is the
reading the distances support, but scripted spawns and respawns produce late creates too,
and map 242 is not the Isle. The plan does not depend on the distinction — walking is the
cheap insurance under every reading.

## Rung 6, LIVE #1: the run happened, and the capture nearly lost its best connection

The run went off-plan in four ways the operator reported honestly (a quest detour into four
PvP arenas mid-step-2, a mixed-up leg, four spot checks whose targets went unrecorded, and a
substituted position on the docks leg). None of them is what nearly cost the session.

**What nearly cost it: two connections did not decrypt, and the bigger one was the whole
walk.** `livesession` pairs tapped keys to connections with `key_fits`, a TWO-BYTE test —
direction bit set, opcode within the catalog. Capture `20260817T231139` had fifteen
connections and fifteen keys; thirteen paired cleanly and the last two formed a perfect 2×2,
each remaining key passing the two-byte test on each remaining connection. The driver
refused, correctly — writing under a wrong key produces noise that reads like a capture —
and the refusal was recorded as `"2 different keys all fit; refusing to choose"` in a
manifest field nothing was looking at. The lost connection was **port 63805, 122,432 bytes,
map 280, wire time 882→1484 s — every walking leg and all four spot checks.** Steps 0–2 were
in earlier connections, so the capture looked plausible: three Isle visits, a roster, no
error anywhere on screen.

**The fix is a second question, asked only when the first fails to separate:** does the whole
s2c stream frame to its FINAL byte under this key? ARC4 is wrong for every byte after the
first message and the framer walks off lengths it reads from the plaintext, so noise cannot
walk 122 KB and land exactly on the end. **OBSERVED: 100.0% against 0.01%, and 100.0%
against 0.11%** — not a close call. Re-assembly now reports **15/15 connections decrypted**,
plan seal AGREE. `livesession._frames_completely` + `test_livesession` §13, commit `46a7ea6`.
An independent witness agrees and was not used to decide: every connection's key is tapped
**~8.7 s before** it opens, and the two leftovers pair that way too.

**A caution for anyone reading a capture by hand.** Reassembling a connection by
concatenating `wire.jsonl` payloads *in file order* rather than TCP **sequence** order
produces a stream that decrypts, frames 108 messages, and then dissolves into garbage — a
convincing impersonation of a wrong key or a mid-stream re-key. It cost an hour here. Use
`wirecapture.load_connections`, which orders by sequence; there were **no TCP holes and no
retransmits** in this capture.

### What the recovered connection holds

| | creates | NPC creates | definitions | stations |
|---|---|---|---|---|
| **63805 (recovered)** | **426** | **332** | **32** | **109** |
| 52318 | 182 | 135 | 28 | 94 |
| 62134 | 79 | 59 | 15 | 66 |
| 52099 | 47 | 36 | 11 | 47 |

Across the four Isle visits: **110 distinct stations, 32 definition slots, and 32 of 32
carrying `enc_name`** — the 246/246 result above extends to 278/278 with no exception.
Note creates ≫ stations (426 → 109): a body is **re-created when the player re-enters its
streaming radius**, so creates count arrivals, not bodies. Station is the unit; any count of
"how many X are on the Isle" taken from create counts is wrong by a factor of four here.

Also recovered: port 52447, **map 281** — a map id that appears in no other capture we hold.

### The forgotten spot-check targets are recoverable, and were recovered

The operator noted only that the Suit was "Suit of 60 Armor" and the Master was "Master of
Combat". The wire holds which BODY was clicked. The client stream frames 100% (17,180 bytes,
898 messages, mask `0x8000` — `cmsgstream.py`'s `CMSG_MASK`, not the `1` a first pass used),
and each click appears as a continuous cursor-tracking stream (`0x00C1`) plus a discrete
commit (`0x0026` or `0x0039`). Both carry `agent_id` as their first field **per the
catalog's own field types**, not per our reading of the bytes.

**CORRECTION, from adversarial review — these are NOT two independent witnesses.** This
section first called them "two independent opcodes naming the same agent at the same
instant". They are one UI event emitting two adjacent messages: for steps 14, 15 and 16 the
pair sits **in a single TCP segment, ten bytes apart**, and `tape.py` timestamps per
segment by construction, so "the same instant" is arithmetic rather than agreement. Only
step 13's pair straddles segments. The recovery is unaffected — every number below
reproduced independently, 21 of 21 — but it rests on one witness, not two.

| plan step | t (wire) | commit | agent | definition slot | model | level | prof |
|---|---|---|---|---|---|---|---|
| 13 — a range marker | 1418.3 | `0x0026` | 36 | 155 | 170342 | 20 | 4 |
| 14 — a Suit of Armor | 1430.3 | `0x0026` | 29 | 152 | 170342 | 20 | 4 |
| 15 — a named Master | 1441.2 | `0x0039` | 28 | 142 | 155687 | 20 | 1 |
| 16 — a Student | 1459.0 | `0x0039` | 93 | 162 | 158806 | 20 | 4 |

Each falls inside its own step's mark window. **The spot checks do not need repeating** —
which body was clicked is settled for all four.

**Which body it WAS is not settled, and the operator's recollection is in tension with the
geometry rather than confirming it.** Agent 28 (step 15, the "named Master") stands at the
centre of the four Suits; agent **27** — clicked three times during step 2 — stands at the
centre of the eleven slot-155 range markers. By the sealed plan's own labels ("the
practice-target star (Master of Combat / Practice Target)", "the armor bench (the Suits,
Master of Damage)") that reading makes **27** the Master of Combat and 28 the Master of
Damage, contradicting the recollection. But 28 cannot simply be relabelled either: slot 142
is profession **1 = Warrior**, and GWW makes the Master of Damage an Elementalist. No
`PROP_HEALTH_MAX` was observed for agent 28 in the whole connection, so there is no third
datum. **The name is NOT RECOVERABLE from this capture** — it needs the `enc_name`
(slot 142 → `[3046, 51807, 63827, 4654]`) rendered on a client we control, which is the
method `studies/isle/PLAN.md` already ruled on.

The opcode *meanings* stay **UNVERIFIED**: `schema/messages.json` carries no name for
`0x0026`, `0x0039` or `0x00C1`. What is OBSERVED is the field type, the timing, and the
agreement of two opcodes; naming them is a separate job.

### What the detour cost, and what it bought

It cost the plan's cadence and it is why step 2 carries a 612-second gap (wire t 230→842)
and two F10 repeats. It cost nothing in the Isle data, because the arenas are different map
ids on different connections and separate cleanly. What it bought is in the same capture:
**maps 309, 310, 311, 312** — four PvP arenas with bot opponents — and five visits to map
248 carrying 28–31 *players* each, which is the largest population of real player agents in
the corpus. Whether that is a usable damage or roster corpus is being assessed separately;
what is certain is that it is not contamination.

### Coverage: the west is closed, the east was never walked

Six agents (four analysts, two skeptics, ~1.2M tokens) went over the recovered capture.
What survived attack:

**The two deviations the operator worried about cost essentially nothing, and that is
measured rather than reassuring.** The mixed-up leg (step 3, the range line) produced
**zero creates** — the entire range ladder had already been delivered during step 2, in
both the second and fourth visits, at byte-identical positions fitting to ±12.4 u. Ten
rungs. **Closed; do not re-walk it.** The substituted docks position likewise: steps 5, 7,
8, 9, 10 and 11 each yielded **zero new stations**, because those bodies were already in
the roster from earlier legs. And the four spot checks yielded **0 new stations out of 95
creates**, which is the trimmed plan's own premise confirmed from the other side —
targeting buys a name link, not a roster.

**The real gap is spatial and it is the east.** The last productive leg was step 12 ("walk
the remaining perimeter"): six new bodies streamed in between wire t 1333.8 and 1358.9, and
the operator turned around 13 seconds later, **while bodies were still arriving**. Only 7
of 108 bodies were ever delivered from ≥5,000 u, and the far-east group sits at 2,852–7,581 u
— at the edge of the streaming envelope, so what lies beyond is simply unmeasured.
Everything east of x ≈ 2100 is unwalked, plus the NE corner around x[1000,3000] y[6000,8000],
skirted at 3,494 u. West and centre (x −11314…+2100) were walked at a median 255 u from
every body in them: empty cells there are **evidence of absence**.

**A second visit is therefore worth taking, and it is short.** Walk east past x = 2076 to
the map edge along two y-lines, pausing 20 s every ~2,000 u, to reach the six bodies already
glimpsed out there and whatever sits between them; get slots **129** and **135** above n = 1
create (one create cannot distinguish a fixed station from a spawn); and reach the far NE
corner and the lone NW station at (−10951, 7649). It settles a stated question: definition
indices are a **global** space (slot 111 is byte-identical across maps 248/280/309–312), and
of the Isle block 129–165, **ten indices — 130, 131, 132, 133, 136, 137, 138, 139, 140,
146 — have never appeared in any capture we hold.** If the east leg produces them the roster
is closed; if a full east walk does not, they belong to another map and the Isle roster is
27 types, which is itself a result.

**The strongest positive result of the run is the Students**, and it is strong because it
could have failed: **ten bodies over ten consecutive definition slots (156–165), split
exactly 5 allegiance-`play` / 5 `mon1`**, against a pre-registered wiki claim of ten
Students of whom five are allies. It could have come out 6/4, or n ≠ 10, and did not.
(By contrast the Suits' 2/1/1 arrangement was reported as tight confirmation and is not —
four bodies over three slots can only land 2/1/1, 2/2, 3/1 or 4, so it carries about one bit.)

## Rung 6b — the east line (capture `20260818T094648`, 5/5 decrypted, seals AGREE)

The east leg was taken 2026-08-18 on the same 38833 build, `game_mode base`,
`exe_unchanged: true`. Every prediction the sealed plan made resolved, and the east turned
out to hold the half of the island that matters most for the rungs after this one.

**The four pre-registered predictions. All OBSERVED, none fudged.**

| prediction | result |
|---|---|
| `0x0195` field 1 == 165811 again | **confirmed**, both map-280 loads — now 6 for 6 |
| field 2 == `(-6036.0, -2519.0)`, byte-identical | **confirmed**, both loads, fifth and sixth time |
| slot 129: same coordinate ⇒ fixed station; different ⇒ spawn | **fixed station** — one create per run, `(6521, 1628)` in both, two independent sessions |
| an item-tagged body near the far east edge | **confirmed** — `(9298, -39)` in both runs, same coordinate |

**Seven of the ten pre-registered missing definition indices were exactly where the gap
argument said they would be.** 131, 132, 133, 136, 137, 138 and 140 all appeared, all in
the east, all level 20, all foe-allegiance. **130, 139 and 146 remain unseen anywhere.**
That is the strongest coverage result the arc has: the ten indices were named *before* the
run as the concrete candidates for bodies the first pass never reached, and seven of them
turned up in the region the first pass never walked.

**The east is now bounded, which is a stronger claim than "walked".** The track ran to
x = 13,325 and spanned y −7,010 … 10,920, while the easternmost station sits at x = 9,937
and the station envelope is y −7,008 … 9,687. **The walk encloses every body we found on
every side.** Coverage inside the line is deliberately looser than the first pass (median
station→track distance 2,928 u against the west's 255 u, and 60 of 94 stations were never
within 2,000 u) because this leg was bought for REACH, not proximity — and reach is what
the missing indices needed.

### What the east actually holds: the skill-bar foes, with their summons

Three positions carry more than one body, and the co-location is the finding.

| position | body | level | profession | allegiance | reading |
|---|---|---|---|---|---|
| (3363, −7008) | slot 136 | 20 | **2 Ranger** | `mon1` | owner |
| | slot 1387 | **15** | 2 | **`anim`** | its pet |
| (7856, −1950) | slot 132 | 20 | **5 Mesmer** | `mon1` | owner |
| | slot 2937 | **0** | 2 | `mon1` | a spirit — no model, and it is re-created under **agent ids 118, 123 and 158** at the one position |
| (3049, −2902) | slot 138 | 20 | **8 Ritualist** | `mon1` | owner |
| | slots 4274, 4264 | **0** | 2 | `mon1` | two spirits |

**These match three separate wiki claims that were written down before the run, on axes
that could each have come out wrong.** `gww-facts.md` records a Master of Interrupts who is
**R**/Me and carries a **level 15** Elder Wolf — we measured a level-20 **Ranger** with a
**level-15 `anim`-allegiance** body at its feet, three independent agreements. It records a
Master of Energy Denial who is **Me**/R and casts **Quickening Zephyr**, a nature ritual —
we measured a level-20 **Mesmer** with a level-0, model-less body respawning under fresh
agent ids beside it, which is what a spirit looks like on the wire. And it records a Master
of Spirits who is **Rt** — we measured a level-20 **Ritualist** with **two** such bodies.

**Label these RECONSTRUCTION, not identification.** No name was read off the wire, and the
`enc_name` route (`studies/isle/PLAN.md`'s ruling) is still the only thing that can name a
body. The reason to trust this more than the withdrawn "agent 28 = Master of Combat" claim
is that it is not a lone coincidence: profession, level, allegiance class and summon
structure agree simultaneously, per body, across three bodies.

**Level 0 + no model + churning agent ids + co-located with an owner is a SUMMON**, and it
is a shape the roster reader should learn: `stations()` keys on position, so a spirit
re-created three times at one spot inflates the station count and looks like three bodies.

### Two corrections to how these plans get written

**The island's axes are not the plan's compass directions.** Walking "east" from the spawn
lands at the **north-east corner** — world +x and +y are both involved, so a plan that says
"east" and then "along the eastern edge, north then south" describes a rectangle the island
does not have. In practice steps 5 and 6 sent the operator **back and forth along one line**.
Write the next plan in terms of *landmarks and screen-relative headings from a named start*,
or in terms of "until X sits at the compass edge" — never in world-axis compass words, which
only the capture can see.

**"Walk one compass length" understated it badly.** The operator reports the real east leg
took "a very far duration" of running, and the track bears that out: 13,325 u of x against a
plan that budgeted ~2 compass radii (10,000 u) for the whole line. The Isle is much larger
than the first pass's west-and-centre extent suggested.

# Rung 7 prep — the consumer built first, and the corpus paid twice (2026-08-18)

§7's named risk for this arc is a campaign whose numbers no line ever reads, so the
damage pass's consumer was built and proven BEFORE its live session:
`toolkit/authsrv/damagepass.py` + `test_damagepass.py` (44 checks, floor 44, entry in
`TESTS.md` same commit). It reads a capture's `0x00A3` p16/17/18 events, joins each to
the create in effect at its timestamp, scopes on **(target-station, cause, swing-kind,
plan-step)** — B6's rule plus the block dimension, because the rank sweep re-engages ONE
Suit at five ranks and without the step those blocks pool into a mean about nothing —
recovers H from the fraction grid (bitwise f32, family semantics: every multiple of a
fitting H also fits), fits the armour divisor D from r80/r100 separately and jointly per
§3.1's one-parameter correction, runs the p17 variance law per block, extracts `0x5D`
cleartext varint candidates (B8's path), and binds AR/RANK labels ONLY from the sealed
plan's own step text read out of `plan_marks.jsonl` windows. Conflicting labels refuse.

**The rung-6 detour's PvP arenas turn out to hold the largest damage corpus in the
vault, and it proved the analyzer the useful way — by showing the confounds are real.**
Maps 310/311/312 carry 641 p16 + 119 p17 events (553 on map 310 alone, zero unjoined).
Run over them, OBSERVED: **10 of 11 arena p17 groups at n≥2 have nonzero variance** —
the attack-skill packet (§3.1's confound: armour-ignoring bonus riding the same
message) measured in bulk, and the reason rung 7 is auto-attack only. A player-class
target's fraction grid recovers the **480 family — level-20 base health** — out of raw
bytes; several bot groups come back "H unfit", consistent with death penalty moving max
health mid-session (RECONSTRUCTION; DP is §3.1's own confound and the arenas were full
of deaths). The level-up `0x5D`'s cleartext args [13, 51, 1, 17] are pinned as the test
of the announcement path.

**The armor bench geometry, recovered from both rung-6 captures** (merged definitions,
`agentroster`): the four Suits are a row — slots **152 at (-5915, 2079)**, **153 at
(-5768, 1978)**, **154 at (-5618, 1864)**, **152 again at (-5483, 1751)** — all model
170342, level 20, `mon1`, with the slot-142 Master (**Warrior**, model 155687, `nonc`)
at (-5832, 1761). The two slot-152 bodies are the row's ENDS, so if GWW's 2/1/1 holds,
the 60-Armor pair is the ends — a pre-registered nameplate prediction in the plan, not
an assignment. The island's profession-6 (Elementalist — GWW's Master of Damage)
candidates are **slot 145 at (-5033, 2970)** (`nonc`, near the bench) and **slot 144 at
(-2000, 3233)** (`mon1`); slot 142 at the bench middle is predicted NOT to be the MoD.
Which body carries which name stays for the nameplate, per the standing ruling.

**The no-combat east run carried one combat episode, and it answered rung 8's channel
question early.** OBSERVED in `20260818T094648` (the operator reported it live —
"got hit with Pin Down by I believe the Master of Survival", OPERATOR-RECALLED names):
agent 103 = **slot 137** (east foe, level 20, profession 2 **Ranger** — corroborating
the recollection on the axis the wire can see) shot the passing player once. The tick
at t=183.755 holds, together: `0x00A3 [16, 25, 103, -0.0270833]` (13 points on the
**480** grid — the PvP character's level-20 base health, measured in passing),
**`0x0042 [25, 481, 13, 95, 13.0f]`** — **481 = Crippled in B4's condition mapping,
arriving on `0x0042` from ArenaNet's own server**, with a trailing float that reads as
a duration (Pin Down cripples up to ~13 s, UPSTREAM) — and `0x0027 [25, 144.0]`: the
player's move speed **halved from 288, server-side** (the same server-owns-the-effect
shape as R4-2's degen result). The attacker's wind-up named **skill 392** twice
independently (`0x00A0 [50, 103, 25, 392]` at draw, `0x009F [10, 25, 392]` at impact
— the Pin Down id candidate), the arrow flew as `0x00A4` (shooter 103, ~1.0 s flight),
and the operator's answer — skill **364**, cast five times — rides the same channel as
a self-effect: `0x0042 [25, 364, 10, 96, 10.0f]` with `0x0027` speeds 383.04 = 288 ×
1.33 (and 191.52 = its crippled half): a +33% speed stance. **Consequence for rung 8:
the channel assumption is no longer only an assumption — condition application has now
been OBSERVED on `0x0042` on retail traffic, once.** Torches-first stays (a gadget's
application may differ from an attack's, and n=1), but the two-minute refutation branch
is now unlikely. Honest note for rung 6b's record: the east run's "no skills" rule was
broken under fire, five casts, all after the hit; nothing in the roster data is touched
by it.

**The plan ran the same day — see "Rung 7, LIVE #2" below.** It is staged at
`vault/plans/isle_rung7_damage.txt`, and the ruling §6 required before sealing landed
the same day it was raised. The behavioural cap
(`studies/monsterai/FINDINGS.md:1121`, 3 approaches per creature type per session) was
**STRUCK ENTIRELY by the owner 2026-08-18** — `PLAN.md` §7 Q7: *"as long as the runs are
human-driven it's not suspicious at all to kill the same enemies over and over"* — the
same treatment its unmeasured day-spacing sibling received in monsterai §7.7.2. The
plan is unblocked; livesession seals it at launch.
Two design notes folded in from the owner mid-prep: weapons have damage RANGES — p16
spreads over the rolled range while a crit pins to its maximum, which is stated in the
plan's predictions and printed as a per-block integer band by the analyzer — and the
rank-sweep prediction BRANCHES on the recorded weapon type (wand/staff: flat, caster
weapons scale with character level only; martial: the 283%/293% kink), pre-registered
both ways in the `weapon` step.

---

# Rung 7, LIVE #2 — the damage pass: the formula came out whole, and one term of it is wrong

**Capture `20260818T132739`, 2026-08-18.** 38833 build, `game_mode base`,
`exe_unchanged: true`, **9/9 connections decrypted**, plan seals AGREE on a 22-step
sealed plan. Operator: a PvP-only **Warrior**, level 20, 480 health, PvP Sword
(`Slashing Dmg: 15-22`, `Requires 9 Swordsmanship`, `Damage +20%`, no inscription,
customized) and a PvP Tactics Shield. Auto-attack only; every prediction below was
sealed before the client launched.

Everything here was re-derived by five independent agents — one blind, one sourcing
GWW, two adversarial, one on the chat oracle — and then adjudicated. **Three of the
seven claims the first pass wrote down came back corrected, one came back refuted as
an inference, and one sub-claim came back plainly wrong.** All of that is recorded
rather than smoothed over, because the corrections are the more useful half.

## The measurement chain, before any claim rests on it

| | |
|---|---|
| damage events | **495** — p16 **395**, p17 **100**, **p18 zero** |
| distinct `cause` | **{25}**, all 495 — one attacker, nothing hits back |
| unjoined to a create | **0 / 495** |
| outside a mark window | **0 / 495**; non-engagement steps carry **0** |
| `points/H` bitwise-exact as f32 | **495 / 495** |
| median inter-hit gap | **1.330 s in all ten blocks** |
| casts / projectiles inside an engagement block | **0 / 0** |

**H is measured twice by unrelated routes and they agree.** An exhaustive bitwise scan
of the fraction grid gives family `{480k}` for all four Suits and `{590k}` for the
Master of Damage; the wire's own `PROP_HEALTH_MAX` (`0x009F` prop 42) independently
names **480** and **590**. CORROBORATED, not assumed.

**The rank labels are OBSERVED, not operator-declared** — see §8. `0x003B` fires in
every "set the panel" step and in **no** engagement step.

| step | label | slot | H | n16 | band | mean16 | n17 | crit |
|---|---|---|---|---|---|---|---|---|
| 4 | AR=60 | 152 (−5915, 2079) | 480 | 23 | 19..27 | 23.435 | 12 | 39 |
| 5 | AR=80 | 153 | 480 | 50 | 13..19 | 15.880 | 7 | 27 |
| 6 | AR=100 | 154 | 480 | 61 | 9..14 | 11.393 | 15 | 19 |
| 7 | AR=60 | 152 (−5483, 1751) | 480 | 44 | 19..27 | 22.523 | 13 | 39 |
| 9 | **H=590 only** | 144 | 590 | 42 | 19..27 | 23.548 | 13 | 39 |
| 12 | AR=60 RANK=11 | 152 | 480 | 35 | 17..24 | 19.800 | 8 | 34 |
| 14 | AR=60 RANK=12 | 152 | 480 | 29 | 18..26 | 22.069 | 9 | 37 |
| 16 | AR=60 RANK=13 | 152 | 480 | 23 | 19..27 | 23.087 | 12 | 39 |
| 18 | AR=60 RANK=9 | 152 | 480 | 43 | 14..20 | 17.442 | 8 | 29 |
| 20 | AR=60 RANK=8 | 152 | 480 | 45 | 4..6 | 5.067 | 3 | **8** |

Step 9's plan text is `[H=590]` and carries **no `AR=` tag** — it is correctly outside
the armour pool, and putting it back on the strength of GWW's "60 armor rating" would
be RECONSTRUCTION, not measurement.

## 1. The armour term: the exponential form CONFIRMED, and the divisor is 40

**The bench came out in the operator's own reading order — 60 / 80 / 100 / 60** — so the
pre-registered slot-152 prediction (the two same-slot bodies are the row's ENDS) held,
and slots 153 and 154 are the 80 and the 100.

OBSERVED, H=480 points: AR60 **22.836** (n=67), AR80 **15.880** (n=50), AR100 **11.393**
(n=61). Ratios **r80 = 0.6954** and **r100 = 0.4989** against GWW's 0.7071 / 0.5000.

**CORRECTION, and it is the most important one in this document. Do not quote
D = 38.16 / 39.88 / 39.52 bare.** Those read as "D is not 40" and the opposite is true:
bootstrap 95% intervals are r80 **[0.6666, 0.7254]** and r100 **[0.4799, 0.5187]**, both
containing the wiki value, at **−0.79σ** and **−0.11σ**; D_joint's interval is
**[37.30, 42.00]**, containing 40. `divisor_fit` now returns n, sem, a per-AR interval
and the σ-distance of 40, and its printout says outright that the mean-ratio fit is the
weaker witness.

**What actually pins D = 40 is the BAND test, which the first pass never made and which
has NO free parameter.** With D = 40 and round-to-nearest, AR60's support {19..27} fixes
the scale and the other two follow with nothing left to tune: AR80 → {13..19} ✔,
AR100 → {9..14} ✔. `floor` is refuted outright by the two 14s at AR100.

**Label-swap control passes decisively:** as labelled, D = 38.16 / 39.88 (spread 1.72);
with the 80/100 nameplates swapped, D = 19.93 / 76.33 (spread 56.4).

**Error budget the first pass omitted.** The two 60-Suits differ by **+0.912 ± 0.708
(1.29σ)** — not significant, identical bands, identical crit — but the 95% bound on
body-to-body variance is ≈ ±6% of the AR60 mean, while the r80 deficit under discussion
is 1.7%. **AR80 and AR100 rest on one body each.** A replication with ≥2 bodies per AR
is what would separate body variance from the ratio.

## 2. The whole damage formula, and the one term that is REFUTED

The model that reproduces every band endpoint, with zero free parameters:

```
points = round( roll × 1.20 × 2^((SL − AR)/40) )
SL     = 5 × rank            for rank ≤ 12
       = 60 + 2 × (rank−12)  above 12
roll   drawn from the weapon's stated 15..22
```

**WIKI** (GWW "Damage calculation", rev. 2025-08-01, carrying its own `{{unofficial}}`
banner — player reverse-engineering, so agreement is corroboration between two
independent observers rather than confirmation against a primary source) states each
term separately: the `2^((SL−AR)/40)` form, `5×rank`, the threshold at `(level+4)/2` = 12
at level 20, and `+2` per rank above it. Wire and wiki agree from opposite directions.

**Corrections.** The "10 of 10 blocks" is **7 distinct (AR, rank) conditions** — steps
4, 7, 9 and 16 all predict and observe 19..27. And one of the seven passed on luck: at
rank 11, `15 × 1.10040 = 16.5061` against a rounding threshold of 16.5, a margin of
**0.037%**, which discriminates nothing.

**The `/3` for an unmet weapon requirement is REFUTED at 3.5%.** The rank-8 band alone
is fine (4..6 admits scale ∈ [0.25000, 0.29545), and the model's 0.28284 is inside). It
dies when the crit is added: crit = 8 requires scale ∈ [0.24106, 0.27320), so jointly
**[0.25000, 0.27320)** and 0.28284 is past the ceiling. **The data cannot say which term
is wrong and no replacement may be published**: holding SL=40, the divisor lies in
**(3.106, 3.394]** — 3 is excluded, 10/3 is not; holding ÷3, SL₈ lies in **[32.9, 38.0)**
— 40 is excluded, 35 is not. GWW itself says "**approximately** two-thirds"; the exact
1/3 was our hardening of a hedged source. **Do not cite GWW's worked example as support**
— "a sword that deals 11-22 will do 5-8 (11 on critical)" is internally inconsistent.

## 3. The roll is finer-grained than the stated integer range

**The model-free argument, which is the decisive one:** AR60/rank13 pooled (n=132) shows
**9 distinct point values, 19..27.** An integer roll over 15..22 is 8 values, and any
deterministic map of 8 values yields at most 8 outputs. That kills the entire
rounding-rule family at once, without fitting anything.

**CORRECTION — "continuous" over-claims.** Against uniform K-step grids, K=8 is
impossible, K=9..30 disfavoured, and **K ≥ 40 is indistinguishable from continuous**.
The defensible claim is **"finer-grained than the stated integer range, at least ~40
steps"**.

**CORRECTION — the strongest rival is refuted by exactly two events, and this belongs in
these words.** An integer roll over the *customized* range 18..26 reproduces
AR60/rank13's support exactly and fits its **shape slightly better** than continuous
(χ² 5.18 vs 6.13, 8 df). It dies on one thing only: at AR100 it caps at 13, and **14 was
observed twice** — t=750.678 and t=765.382, both p16, both slot 154, both bitwise-exact
on `14/480`. Two events carry the whole refutation. A replication should pick an AR where
the two candidate supports differ by more than one bin, so the discrimination does not
rest on the tail.

**WIKI: NOT FOUND** on both halves — GWW says only "a random value in the weapon's
range", never uniform, never integer-vs-continuous. **The measurement stands alone.**

## 4. Property 17 IS the critical hit — the strongest result of the run

Pre-registered and met: **10/10 blocks single-valued, 100/100 events, variance zero.**

**One parameter fits nine numbers.** The nine requirement-met blocks pin the crit
multiplier to **c ∈ [1.40866, 1.42045)** — a 0.83% window — and **√2 = 1.41421 is
inside**. (Correction: "at AR−20" and "×1.414" are *the same statement*, since
2^(20/40) = √2; the first pass presented one rule as two agreeing facts. And the data
pins √2 only to ±0.8% — 1.41 and 1.42 also fit.)

**Two witnesses the first pass did not have:**
- **p16 + p17 = 495 = one event per swing**, at a 1.330 s median gap in every block. So
  p17 **replaces** p16 — what a critical does and what a bonus would not.
- **Crit rate rises monotonically with effective rank on one body at one AR**: 6.25%
  (r8), 15.69% (r9), 18.60% (r11), 23.68% (r12), 34.29% (r13). GWW says crit chance
  depends on attribute rank; a damage cap or a fixed bonus has no reason to do this.

**THE RANK-8 CRITICAL IS A DISJOINTNESS, NOT A ROUNDING NEAR-MISS**, and the first pass's
"observed 8 against a predicted 8.8 → 9" understated it badly. The rank-8 block admits
**c ∈ [1.20530, 1.36600)** while the met blocks require **c ≥ 1.40866**. The intervals do
not touch. No single crit multiplier fits all ten blocks and no rounding rule rescues it
— `floor` fixes rank 8 and breaks AR60/r13 (38 vs 39) and rank 9 (28 vs 29). **The defect
is not in the crit rule; it is the same unmet-requirement term §2 gets wrong, and this is
its sharpest expression.** It stays unexplained and it stays visible.

## 5. The Master of Damage oracle — and the check that could have failed

**Slot 144 at (−2000, 3233), profession 6 Elementalist, level 20, health 590.** GWW's
Master of Damage is a level-20 Elementalist with 590 health. The operator's independent
report — "far away next to two targets of their own" — matches its position between two
slot-155 target stations. The pre-registered prediction that the bench-middle body (slot
142, a **Warrior**) is NOT the Master of Damage held. Still RECONSTRUCTION under the
standing ruling: no name was rendered.

**The oracle breaks the H family, which is the point.** The fraction grid alone gives a
family `{590k}` and cannot choose within it. The announced total is **1496**; H=1180
would make it 2992 and H=1770 would make it 4488. **Only 590 gives 1496**, and 1496 is
exactly our independently summed integer points (989 from p16 + 507 from p17). A check
that could have failed and did not.

**REFUTED — "the `/bow` report at t=1117.57".** Verified from both directions: the line
carrying 1496 is at **t=1117.574**, and the c2s command `0x0064 [.., '/bow']` is at
**t=1122.037**, **4.46 s later**. The 1496 line is an **end-of-combat auto-report** ~5.8 s
after the last hit. Its three arguments read as **(1496 total damage, 73 seconds,
20 average DPS)** — and 1496/73 = 20.5 → 20, which closes internally. The genuine `/bow`
responses are the two later lines at t=1123.572 (39, 9) and t=1126.572 (31).

**REFUTED — the periodic tick as a running average.** N steps **20 → 26 → 21** across
consecutive 5.00 s ticks while the cumulative total only rises; a running average over
65 s of accumulated data cannot do that. The *direction* (a rate, not a total) is
CONFIRMED — N stays in [17, 26] while the sum runs 92 → 1496.

**The residual is OPEN and was sharpened rather than closed.** `floor(D₅/5)` scores
11/15; a sweep over window width ∈ [3,12] s × offset ∈ [−3,+3] s × {floor, round} ×
divisor {5, W} tops out at **12/15**. **New structure: every miss is a window holding
fewer than 4 swings, and the deficit is exactly +4 per missing swing.** That is why
"sum of the last 4 swings ÷ 5" also scores 12/15 — the server may be averaging over a
fixed *number of attacks* rather than a fixed wall clock. Three ticks stay unexplained
and the 12/15 fit is **not adopted**.

**Argument encoding, OBSERVED and simpler than the varint story suggested:** every
argument word is literally `0x100 + n`, alternating slot index and value. The
end-of-combat line is `0x101 0x6d8 │ 0x102 0x149 │ 0x103 0x114` = slots (1,2,3) carrying
(1496, 73, 20). This reproduces all 18 lines. The absolute template-id framing stays
UNVERIFIED.

**`damagepass`'s "0x5D renders only with its 0x5E tag" was over-read and is corrected.**
This capture holds 21 chat lines: **3 with `0x5E`** and **18 with `0x5F`**, the latter
naming agent 100 — the Master of Damage itself. So `0x5E` tags a channel-addressed line
and `0x5F` an agent-addressed one; what rung 4 actually established is that a bare `0x5D`
with **neither** renders nothing.

## 6. The rank kink: the inference is REFUTED, and what replaces it is better

Means confirmed exactly: **19.800** (r11, n=35), **22.069** (r12, n=29), **23.087**
(r13, n=23); steps **+2.269** and **+1.018**, ratio **2.229** against GWW's 2.4.

**That ratio is worthless and must be dropped.** Bootstrap over 200k resamples: 68% CI
**[0.91, 4.89]**, 95% CI **[−17.29, 23.53]**, **P(ratio < 0) = 6.9%**, and **9.4% of
resamples land within 10% of 2.4 by chance.** The denominator is 1.44σ from zero, so the
statistic is Cauchy-tailed and cannot distinguish 2.4 from 1.0 or from 5.0. The kink
itself is only **1.15σ** from absent. The plan's pre-registered MARTIAL branch is
**consistent with** the data, **not confirmed by** it.

**Use ratios of means instead, which are sound:** r11/r12 = **0.8972 ± 0.0243** vs the
mechanism's 0.9170 (**−0.81σ**); r13/r12 = **1.0461 ± 0.0325** vs 1.0353 (**+0.33σ**).
The monotone rise r11 → r13 is **+3.287 ± 0.682 = 4.82σ**. And the **bands** are
integer-exact where the threshold rule actually shows: **17..24 / 18..26 / 19..27**. The
crit-rate ladder in §4 is a second independent witness.

**Open residual, no mechanism.** The rank-12 block: value **24 never observed** (3.45
expected) while **23 appears 9 times**, χ² = 15.74 on 8 df, p ≈ 0.046, n=29.
Time-ordered halves show no drift, and an integer roll would forbid the four observed
21s, so that escape is closed too. Unexplained.

## 7. The unmet-requirement step: the naive 1/3 is excluded, and so is our fix

r8 = **5.067** (n=45), r9 = **17.442** (n=43), ratio **0.29049**, bootstrap 95% CI
**[0.2769, 0.3048]**. **The naive 1/3 sits at −6.05σ and is excluded** — that is this
step's real contribution and it holds.

**But our own corrected prediction is excluded too.** With the strike-level drop 45→40
the model predicts **0.3057**, and the observed value is **−2.18σ** below it, with the
95% CI not containing it. Both blocks push the same way. **This is an unexplained ~5%
residual and is recorded as one**, not as a resolution. It is the same defect as §2's and
§4's.

**Block cleanliness verified**: the two blocks are on different connections, bands are
disjoint (14..20 vs 4..6), and the wire's attribute ledger sets effective rank 8 at
t=1650.409 — 10.6 s after the last rank-9 hit and 19.1 s before the first rank-8 hit.
No leakage either way.

## 8. The attribute channel — gate 1's ask, and no capture had ever carried it

The operator had to zone to the Great Temple of Balthazar to *lower* attributes (the game
refuses to lower them in an explorable area), and that detour produced the traffic
`PLAN.md` §7's gate 1 has wanted for months. **Four SMSG identifications, all OBSERVED,
none previously named in this repo:**

| opcode | shape | when |
|---|---|---|
| `0x0037` | `[agent, unspent, 200]` | instance load |
| `0x003A` | `[agent, ids │ base ranks │ effective ranks]` | instance load, **column-major** |
| `0x003B` | `[agent, attribute, base, effective]` | one per change, mid-instance |
| `0x0038` | `[agent, unspent]` | the change's cost, debited |

**The +1 bonus is visible on the wire.** `0x003A`'s two rank columns differ on
Swordsmanship alone — base 12, effective 13 — and all 14 changes carry effective =
base + 1. **Damage uses the EFFECTIVE rank**: the bands fit it at all five ranks, and
base is refuted because adjacent blocks have distinct bands that do not swap. Effective
14 is refuted too — SL(14) = 64 predicts a band reaching 28, and 28 never appears in 132
events.

**The point budget closes two unrelated ways.** The first `0x0037` reads **5 unspent
against a budget of 200**, matching the operator's own screenshot before any arithmetic.
Three equations over four instance loads then give **cum(8) = 37, cum(10) = 61,
cum(12) = 97 attribute points** with no cost table assumed — and **97 is the number GWW
publishes for rank 12**. Independently, the sweep connection's own debits (41 → 25 → 5)
reproduce the same 36 while *splitting* it into **rank 11 = 16 points, rank 12 = 20**,
which the load readings alone cannot separate.

## 9. What this run leaves open

1. **Which term of the unmet-requirement rule is wrong?** A rank-7 or rank-6 block, or a
   second weapon with a different requirement, separates {divisor, strike-level drop,
   crit rule}. **The highest-value next measurement** — it closes the one defect shared
   by §2, §4 and §7.
2. **Is the Master of Damage's tick a fixed-attack-count average rather than a fixed
   window?** Every miss is a sub-4-swing window with a +4-per-missing-swing deficit. A
   deliberately slower weapon separates the two readings.
3. **What is the true grain of the roll?** K ≥ 40 is indistinguishable from continuous
   here; a block at high AR and low rank magnifies quantization.
4. **Why is 24 absent from the rank-12 block** while 23 appears 9 times (p ≈ 0.046)?
5. **What closes the 11-point gap** in the Master of Damage's closing health
   (`prop 55 = 300/590` against our ledger's 289)?
6. **What is skill 364**, cast once by the player at t=1008.125 in a *walking* step? No
   measurable effect on the block that follows, but it is an uncontrolled input.
7. **`parse_coded` returned a 13.8-trillion "string id"** for a `0x5F` blob without
   complaint. That deserves a guard.

## 10. Scope, and one methodological note

The armour ratio is measured against **one body per AR** at 80 and 100. The whole run is
n=1 session, one character, one weapon, one level, one mode — §7's pessimistic case still
applies, and the honest scope of "the damage formula is confirmed" is *for a customized
martial weapon, at level 20, against stationary level-20 targets, on one character*.

**Methodological note worth keeping.** Two of this run's three biggest corrections came
from statistics the first pass simply did not compute (an interval on D; a bootstrap on
the kink ratio), and the third from a timestamp it did not check (`/bow` at t=1122
against the report at t=1117). None of the three needed new data. The band test — which
turned out to be the strongest evidence in the whole run — was available from the first
minute and was not made until an adversary asked what pinned D.

---

# Rung 8 prep — the effects pass mostly answered itself from the vault (2026-08-18)

**Rung 8's stated exit criterion was met before the session was designed**, and
the three biggest questions in §3.3 went with it. This is the rung-6-prep pattern
for the second time: check the corpus before writing the plan, and the plan gets
much shorter and much better aimed.

## 1. `0x0042` is NOT witness-free, and the effect lifecycle is exact

§3.3's central worry: *"The instrument's opcode has ZERO ArenaNet witnesses …
that makes the **refutation branch** — that conditions ride some other channel —
the likely outcome."* **OBSERVED, and it is wrong**: the live corpus holds **97
`0x0042` applies and 88 `0x0044` removals**. They arrived in the rung-6 capture's
PvP arena detour and in the east run's Pin Down episode — neither of which set out
to measure an effect, which is the third time this arc's incidental traffic has
outvalued its deliberate traffic.

**The lifecycle closes to the millisecond.** `0x0044 [target, buff_id]` closes
`0x0042 [target, skill, field3, buff_id, f32 duration]` at **apply + duration**:
57 of 88 within 5 ms, 83 of 88 within 50 ms. So an episode ends one of three ways
and `bufflog.py` never conflates them — **EXPIRED** (residual ≈ 0), **STRIPPED**
(early), **OPEN** (still live at the last byte, and never scored as expired).

**A CURE is on record, the first in this repo, and it is fully explained.** The
Isle's Crippled episode does not expire: it is removed **11.2 s early**, and
another skill's apply carries the **identical timestamp** as that removal. That
skill is **364 = `"Charge!"`**, whose WIKI text (GWW, rev. as fetched 2026-08-18)
reads *"Allies in earshot lose the Crippled condition"*. The whole episode closes
from four directions at once: Pin Down applies Crippled; `0x0027` halves the
player's move speed 288 → 144; `"Charge!"` fires and the `0x0044` lands in the
same millisecond; and the `0x0027` speeds that follow read **383.04 = 288 × 1.33**,
which is `"Charge!"`'s own *"move 33% faster"*. **A cure closes a condition
through the same `0x0044` an expiry uses, and only the residual separates them.**

## 2. FIELD 3 IS THE APPLIER'S ATTRIBUTE RANK — settled offline, four ways

The catalog calls field 3 `u32 unnamed`. The corpus's two conditions (480 Burning,
481 Crippled) have `field3 == duration`, which made "field 3 is duration-shaped"
tempting. **It is arithmetic accident.** Field 3 is the rank at which the skill's
progression was evaluated, and the float duration is the *result*:

| skill | wire | identified as (WIKI) | progression | at that rank |
|---|---|---|---|---|
| 160 | `f3=15, dur=13.0` | **Windborne Speed**, E/Air Magic | 5 s at 0 → 13 s at 15 | 15 → **13** ✔ |
| 364 | `f3=10, dur=10.0` | **`"Charge!"`**, W/Tactics (elite shout) | 5 → 13 | 10 → 10.33 → **10** ✔ |
| 364 | `f3=13, dur=12.0` | same | 5 → 13 | 13 → 11.93 → **12** ✔ |
| 481 | `f3=13, dur=13.0` | **Crippled**, applied by **Pin Down** | 3 → 15 | 13 → 13.4 → **13** ✔ |
| 984 / 998 | `f3=0, dur=30.0` | **Torch Enchantment / Torch Hex** | none (environment) | 0 → fixed **30** ✔ |

The Windborne Speed row is the cleanest: GWW's **Master of Winds** page states
*"15 Air Magic"* and the skill lasts 13 s at rank 15 — an independent source
supplying both the rank and the duration, and the wire carrying exactly those two
numbers. That the operator's own **Tactics 10** (visible in their attribute
screenshot) reproduces `"Charge!"`'s 10 s is a second, self-owned confirmation.

**This is CORROBORATION in the strong sense**: the wiki and the wire share no
author, code or ancestry, and they agree on five values across four skills.

## 3. Hexes and enchantments were never missing — they were unidentified

§3.3 calls hexes and enchantments *"the largest single miss across all four
families"*, with *"no instrument at all"*. **Both are already in the vault**, on
the Isle, from the rung-6 roster run:

- **`0x0042` skill 984, duration 30.0** = **Torch Enchantment** (WIKI: effect id
  **984**, Core, *"For 30 seconds, you are under the effect of an enchantment
  spell"*, *"only used by the Torch of Enchanting … on the Isle of the Nameless"*).
- **`0x0042` skill 998, duration 30.0** = **Torch Hex** (WIKI: effect id **998**,
  *"For 30 seconds, you suffer from the effects of a hex spell"*, *"only used by
  the Torch of Hexes"*).

Id and duration match on the nose, from two independent directions. **The third
torch is the one gap**: **Torch Degeneration Hex, effect id 999**, *"For 10
seconds, you suffer -1 Health degeneration"* — never captured, and the only route
in this corpus to seeing degeneration applied on retail traffic. That is what
rung 8's leg A is now for.

**A procedural correction the wiki supplied and the draft plan had wrong:** the
torches are **not clicked**. All three pages carry *"reapplied approximately every
2 seconds if still standing adjacent to the torch"*. The measurement is where the
operator stands and for how long, not an interaction.

## 4. The material is located, and one constraint is measured rather than assumed

From the three Isle captures, merged:

- **The Master of Magic's circle**: an Elementalist (**slot 145**, level 20,
  `nonc`) at **(−5033, 2970)**, ringed by **three gadget-class (tag-0) bodies** at
  198.7 / 202.9 / 376.9 units — plus one at his exact position. GWW says three
  Torches surround him; the geometry agrees.
- **The ten Students are a straight north-south line** along the far west edge,
  x ≈ −10,850, y from **1173 to 3422**, spaced ~250 u — slots 156-165.
- **The ally/foe split is 5/5 and is now per-body**: foes (`mon1`) are slots
  **157, 160, 161, 163, 165**; allies (`play`) are **156, 158, 159, 162, 164**.
  §3.3 flagged the ally/foe split as *"the family's largest risk"* and it is now
  concrete: **only five Students can attack, so at most five conditions arrive by
  being hit**, and any plan promising a ten-condition map from combat alone is
  over-promising by half.
- **SLOT ORDER IS NOT POSITION ORDER, and the operator navigates by position.**
  The line is walked south→north; the slot numbers are not. A rung-8 study sheet
  built from the slot list alone would send the operator to the wrong bodies, so
  the mapping is recorded here rather than re-derived per session:

  | # from south | y | slot | model | side |
  |---|---|---|---|---|
  | 1 | 1173 | 161 | 130065 | **FOE** |
  | 2 | 1424 | 160 | 130098 | **FOE** |
  | 3 | 1680 | 163 | 116661 | **FOE** |
  | 4 | 1918 | 162 | 158806 | ally |
  | 5 | 2165 | 157 | 130065 | **FOE** |
  | 6 | 2422 | 159 | 129922 | ally |
  | 7 | 2686 | 158 | 116718 | ally |
  | 8 | 2945 | 156 | 129922 | ally |
  | 9 | 3193 | 164 | 129922 | ally |
  | 10 | 3422 | 165 | 130065 | **FOE** |

  So the five foes are positions **1, 2, 3, 5 and 10** — three together at the
  south end, one past a single ally, then a ~1,250 u walk north to the last.
  **Four allies sit between foes 5 and 10; the fifth (position 4) sits between
  foes 3 and 5**, which is the trap in routing the `cracked` step off the walk
  back south: stopping at foe 5 leaves one ally unvisited.
- **Corroboration is uneven along the line, and the north end is the thin part.**
  Slots **156-163 have two independent witnesses** — `20260817T231139` and
  `20260818T132739` — agreeing on position to the byte and on allegiance. Slots
  **164 and 165 have one** (`20260817T231139` only); the rung-7 run never went far
  enough north to bring them into compass range. Position 10, the northernmost
  foe, is therefore the least-corroborated body on the island's west edge, and its
  absence on the day would be a **thin observation**, not a navigation error.

## 5. Degeneration, with the numbers sourced rather than recalled

**WIKI** (GWW, "Health degeneration", fetched 2026-08-18): *"each pip represents a
loss of two health per second"*, capped at 10 pips; **Bleeding 3, Burning 7,
Disease 4, Poison 4**. An earlier draft of the rung-8 plan asserted "Bleeding −1
and Poison −1" from memory and was wrong on both — caught only because the
pre-registration was checked against the source before sealing. On the operator's
480-health pool the property-44 rate should move by `pips × 2 / 480`: −0.0125
(bleeding), −0.0167 (poison/disease), −0.0292 (burning), −0.0042 (torch degen hex).

## 6. What rung 8's session is now for

Four things, none of which the corpus can supply:

1. **Skill 999**, the degeneration torch — the only unseen torch effect, and the
   only route to degeneration on retail traffic.
2. **Which condition skill id each of the five foe Students applies.**
3. **Degeneration in pips**, against the published numbers above.
4. **The rank ladder** (effective 5/6/7/8 at the armour bench), which closes
   rung 7's one open defect — three separate rung-7 results fail at the
   unmet-requirement term and this ladder separates its candidate causes. Bands
   discriminate at ranks 5 and 6 with no free parameter; rank 7 cannot
   discriminate on the band and is carried for its mean, which the plan says
   outright so nobody later reads its agreement as evidence it cannot be.

The plan is sealed at `vault/plans/isle_rung8_effects.txt`, 27 steps, and the
consumer (`toolkit/authsrv/bufflog.py`, 36 checks) was built and proven on the
97 existing witnesses before the plan was written — rung 7's discipline, kept.
