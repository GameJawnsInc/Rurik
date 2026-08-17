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
status→Offline) reads exactly like a client-side death. Fourteen launches were
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
