# The Isle of the Nameless: what it is, what it can measure, and the order to do it in

**2026-08-16.** Written in worktree `combat-end-to-end-a2242b` at `826b39b`
(`git rev-parse --show-toplevel` → `C:/gd/Rurik/.claude/worktrees/combat-end-to-end-a2242b`;
`git log --oneline -1` → `826b39b studies/combat 19: the player windup anomaly was skill
damage all along`). Method: a workflow of four parallel surveys (client statics, the
content/spawn pipeline, the server's combat ledger, the capture corpus), four instrument
designs each attacked by an independent skeptic on five axes, and one completeness critic.
Standing order from the owner for this arc: **verbatim/stock behaviour confirmed first,
before inventing structures from memory; a new capture run is an acceptable cost.**

Labels per [studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM,
RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. **Every wiki fact in this
file is UPSTREAM and carries its page's last-edited date**, because GWW is
community-authored and is a *prediction* a capture confirms or refutes, never a
measurement.

**On the numbers below.** Almost every count in this document was produced by one of the
survey or skeptic agents, and the command is quoted where the number is used. The author
of this file re-ran only a spot-check set: `content.py:75/104/125/138/145`,
`authsrv.py:110/119/145-147/1770/2273/3704`, `agents.py:75/117/628/789/805/808`,
`npcdefs.py:40-42/397`, `livesession.py:1741`, `test_content.py:130`, and
`RUNBOOK.md:1205-1208`. All held except one: **`content.py`'s `"capture"` source is line
75, not 76** (`grep -n '"capture":' toolkit/content.py` → `75:    "capture":`). Numbers
neither re-run nor first-hand here are marked as such at the call site. **No Isle capture
exists**, so nothing in this file is a measurement *of the Isle*; it is a measurement of
what we hold, what the client holds, and what the wiki claims.

---

## 1. What the Isle is, and why it is a north star

**The thesis.** The Isle of the Nameless is ArenaNet's own calibration range: a private
explorable instance whose population is not scenery but *instruments*. Practice dummies
stand at the exact boundary of the range they are named for. Three armour suits of stated,
different ratings stand next to each other so a player can hit them with one weapon. Ten
Students carry one condition each and a single self-heal, so the condition is isolated.
Masters demonstrate one mechanic apiece — interrupts, blocking, knockdown, energy denial,
enchantment, hexes, spirits — and resurrect on a deterministic timer so trials repeat.
Every constant this repo currently *invents* (`HIT_FRACTION`, `ATTACK_RANGE`,
`ENEMY_MELEE_RANGE`, `AGGRO_RANGE`, `REVIVE_AFTER`, `ENEMY_SKILL_RANK`) has a named,
stationary oracle standing on that island, and the oracles are placed by the **server**,
which means one capture of one map yields a dozen constants at once instead of a dozen
sessions each yielding one.

**Where the thesis is weakest, and it is weak in four places.**

1. **The labels are on the SCREEN, not on the wire.** OBSERVED (S4, `<scratchpad>/s4_props.py`
   over all three usable live captures, 22,524 GAME_SMSG): an NPC's name rides
   `0x0056 NPC_UPDATE_PROPERTIES` field 9 as an **EncString** — 126 of 126 samples have
   every code unit ≥ 0x100 — while a *player* character name at `0x0059` field 7 is pure
   printable ASCII in 145 of 146 samples. The wire distinguishes sharply: players
   self-label, NPCs do not. And this repo **cannot decode an NPC EncString**
   (NOT FOUND: `studies/textrec/FINDINGS.md:53-58` — the RC4 key is an 8-byte pair the
   caller obtained by parsing the coded string, and where it lives is *not established*).
   S4 attempted four rival (id, key-pair) arrangements and **refuted its own hypothesis**:
   all 13 apparent hits were PLAIN records needing no key, so the key argument was inert
   and the decoded strings were a skill description, a country name and an armour item.
   **So the corrected thesis is: a capture is self-describing up to a stable JOIN KEY**
   (`enc_name` tuple + model id + definition slot + spawn coordinate), not up to a human
   name. Which body is the Suit of 80 comes from the operator's marks ordinals, or from
   rendering the EncString on a client we control (the `hatcher` precedent,
   `content/npcs.toml:90-97`).
2. **The x-axis is a fifteen-year-old wiki page.** The 60/80/100 armour ratings are
   UPSTREAM from GWW "Master of Combat", **edited 2010-02-06** (`gww-facts.md:85-90`). Any
   design that treats them as measured is jointly testing the 2010 labels *and* the 2025
   formula, and a failure cannot be attributed to either. §3.1 states the fix.
3. **Two of the four instrument families rest on opcodes ArenaNet has never been observed
   to send.** OBSERVED (completeness critic, decoding all 12 live game connections,
   22,524 GAME_SMSG, 155 distinct opcodes, every connection framing to its final byte):
   `0x0042` = **0**, `0x0043` = 0, `0x0044` = 0, `0x003F` = 0, `0x0040` = 0,
   `0x005F` = **0**; only `0x0041` = 4. The conditions family's whole instrument and the
   armour family's own refutation oracle are both in that list.
4. **Rurik is not trying to be ArenaNet's server, and today it has nowhere to put the
   answer.** OBSERVED: `authsrv.py:2273` is
   `dealt = agent["max_health"] * HIT_FRACTION + bonus_damage` with `HIT_FRACTION = 0.15`
   at `:1770` — a fraction of the *target's own* health, with no armour term, no weapon
   term and no level term. Measuring retail's armour curve perfectly does not make our
   server correct; it replaces one invention with a better-sourced one, in a file whose
   own block header (`:1719-1729`) reads *"EVERY PACKET BELOW IS PROVEN; EVERY NUMBER BELOW
   IS INVENTED."*

None of the four kills the thesis. Taken together they change the *order of work*: the
first hour goes to the checks that can cancel the plan, not to the science. §6 is built on
that.

---

## 2. Which map, and how we know

**The answer is 280, and two witnesses that do not share a method agree.**

- OBSERVED (ours, S1, direct read of the pinned pristine exe:
  `python -c "...pinned.find()...0x0096DE38, 888 rows of 124 bytes..."` against
  `vault/client/2026-07-29_221c13772c7a/Gw.exe`, build 38797): row **280** =
  `{"campaign":0,"continent":3,"region":21,"type":2,"flags":0x420000,
  "thumbnail_id":167881,"file_id":0,"name_id":2972,"description_id":2973}`, and
  `python toolkit/clientscan/textrec.py 2972` resolves 2972 → `Isle of the Nameless`
  out of the owner's own archive.
- UPSTREAM (GWW infobox `game link num 0`, `gww-facts.md:18`): **280**. That number is
  authored by players reading the client's own `/wiki` chat output; ours came from a
  structural scan of the 124-byte `AreaInfo` stride. Independent methods, same answer.
- OBSERVED: row **784** = `Isle of the Nameless (PvP)`, `type=11`, `flags=0x40000`,
  `name_id=82827`, same `thumbnail_id`.

**Use 280, not 784.** UPSTREAM (GWW "Isle of the Nameless (PvP)", edited **2018-06-23**,
`gww-facts.md:39-42`): both Isles "use identical layouts and include identical NPCs", but
in the PvP one all skills are converted to PvP versions and **the Flux is in effect**. A
rotating global modifier is a confound on every damage number.

**CONTESTED, and the recon file loses.** `gww-facts.md:43` claims the shared
`thumbnail_id` corroborates "identical layouts" from our side. OBSERVED (S1,
`python -c "...[i for i,w in L if w[5]==167881]"`): 167881 is shared by **eight** rows —
248, 280, 784, 883, 884, 885, 886, 887 — and 883-887 sit in region 27. A shared loading
screen is a shared *picture*, shared across a content group. What actually corroborates
identical layouts is geometric: rows 248, 280 and 784 carry the **identical footprint
rect (544, 640)–(896, 960) at both +0x48 and +0x58** — not the same size, the same
absolute placement — which is 352 × 320 terrain cells at the measured 96.0 pitch.

**Which map FILE, and the caveat that matters more than the answer.** OBSERVED: 352 × 320
is unique in the archive (`vault/areatable/maprows.json` row `"21641"` =
`{"dims":[352,320],"rival_rows":1,"map_ids":[248,280,784],"exact":true}`), and MFT row
21641 is a real map — `Archive(DEFAULT_DAT)` → `flags=259`, magic `ffna`, 1,516,583 bytes
decompressed, 25 chunks, binding file ids **380638 and 165811**. The low id is the one a
server sends (`studies/mapdata/FORMAT.md:319-333`, measured 397-for-397 against upstream's
`map_file_id`).
**RECONSTRUCTION, and this is the whole limit:** the join is on SIZE, not identity. It
cannot separate 248 (Great Temple of Balthazar) from 280 from 784, and same-size is
necessary, not sufficient. Worse, the row NUMBER is a property of one archive copy —
`studies/maprows/FINDINGS.md:235-242` records a file id binding to different MFT rows in
different copies. **Carry the file id 165811 downstream, never the row number.**
What settles it: `GAME_SMSG 0x0195` field 1 on an instance load. Pre-register **165811**
as the prediction. **And pre-register the third branch the design omitted** (OBSERVED, F2
skeptic, `<scratchpad>/v_ids.py`): across 8 live game connections `0x0195` field 1 reads
**113021 in 8 of 8** while `0x0199` field 2 reads three *distinct* map ids (148, 146, 164).
The corpus therefore contains zero evidence that field 1 varies with the map, and
`studies/maprows/FINDINGS.md:245-247` concedes the many-to-one is real on ArenaNet's own
traffic. If the Isle reads 113021 too, the field is not a per-map file id in the sense the
prediction assumes.

**There is no static route from a map id to its geometry, and that is REFUTED three ways
rather than merely unfound.** OBSERVED, `studies/maprows/FINDINGS.md:72-174`: a scan of
every dword at every alignment in all five sections of the 10,483,904-byte image found 21
map-head hits against a null control mean of 21.4 (p = 0.354); the file id reaching the
archive layer has exactly two sources, both network (`0x0195` msg+0x04, `0x01A4`
msg+0x1C); and a census of 698 map payloads / 16,094 chunks tops out at 232 of the 349 a
real table would need. Corroborated from the other side by
`studies/areatable/FINDINGS.md:106-134`: 157 of 888 rows carry a non-zero `file_id` and
**157 of 157 decompress to magic ATEX** — `AreaInfo.file_id` is a loading-screen texture,
not a map. Row 280's `thumbnail_id` 167881 likewise resolves to MFT row 71636, flags 3,
43,784 bytes, magic `ATEX`.

**What the type and region fields mean is NOT FOUND in the client's own words.**
`python toolkit/clientscan/asserts.py --grep "AREA_" --unique` → 0 sites; same for
`GM_MAP`, `CONTINENT`, `explorable`, `arena`, `ARENA_`. The single `REGION` hit is
`UiCtlDistrict:581 DISTRICT_REGIONS != selectedRegion`, the district selector — a different
thing. The tool prints its own floor: 19,758 sites read plus 3 named unreadable against
20,131 call sites, so this is "not named where we can read", not "not named".
Do **not** substitute the client's real map-kind enum: `MISSION_MAP_OUTPOST == 0`,
`MISSION_MAP_GAME == 1`, `MISSION_MAPS == 2` are OBSERVED in asserts
(`QuestLog:261`, `MsCliApi:251`, `MsCliMan:486`) but that is a **two-valued runtime** enum
at `missionContext+0x238`, not the 22-valued static field at `AreaInfo+0x0C`.

What *can* be measured is a clean structural partition. OBSERVED (S1,
`python -c "...collections.Counter(w[3] for i,w in L if w[4]>>17&1)..."`): flag bit 17 is
set on exactly types {2,5,6,8,9,14,18} = 588 rows; bit 18 on exactly {0,1,3,7,11,12,15,16}
= 137 rows; **no row carries both**; the remainder is exactly {4,10,13,17,19,21} = 163
rows. It is 321/321 on type 2 and 17/17 on type 11. **280 (0x420000) and 784 (0x40000)
share ZERO flag bits** — `R[280][4] & R[784][4]` = 0. RECONSTRUCTION on the reading: bit 17
is the co-operative/PvE instance family (it holds Lakeside County, which the wire
independently shows as an explorable instance, and Isle of the Nameless), bit 18 the
competitive family (Zaishen Challenge, Isle of the Nameless (PvP)), outposts and towns in
neither. That corroborates GWW's "Explorable area" for 280 from our side. RECONSTRUCTION
also: bit 22 is set on exactly four rows — 148, 280, 416, 514 — the arrival areas for the
three campaign starts plus the PvP-only character start, across four different type values,
so the bit cuts across type; nobody has found its reader. Region 21 is 16 rows, all on
continent 3, and its membership is the PvP hub; calling it "the Battle Isles" is a reading
of that list, not a client word.

---

## 3. The instruments

Each family below was designed, then attacked by an independent skeptic on five axes
(factual, wiki currency, discrimination, confounds, feasibility). **Where a skeptic refuted
something, it is stated here rather than quietly deleted.** A design that was attacked and
survived is worth more than one that was never attacked, and a reader six weeks from now
needs to see which is which.

### 3.1 Armour and damage magnitude — the Suits, the Master of Damage

**Verdict: SURVIVES WITH CORRECTIONS.** The central instrument is sound; three of its
supporting predictions were individually refuted.

**What stands there.** UPSTREAM (GWW "Master of Combat", edited **2010-02-06**,
`gww-facts.md:85-90`): the Master of Combat "is surrounded by **two** Suits of 60 Armor, a
Suit of 80 Armor and a Suit of 100 Armor where players can test their damage." All level
20. UPSTREAM (GWW "Master of Damage", edited **2017-10-27**, `gww-facts.md:99-108`): 590
health, 30 energy, 60 armour rating, level 20, does not attack, "says every five seconds
the average damage you do per second to him", and after `/bow` reports total damage, total
time, average DPS, highest damage in one second, shortest time to kill.

**What it measures.** The armour term, which is NOT MODELLED anywhere:
`grep -in 'armou\?r' toolkit/authsrv/authsrv.py` returns 5 hits, all in unrelated comments,
and none in `hit_enemy`/`land_swing`/`land_skill`; `npcdefs.py:40-42` records that **no
property id for armour appears in any channel across 22,524 messages**. Also weapon damage
range (NOT FOUND — `content/items.toml:22` holds `modifiers = [0x24B80000, 0xA4880503]`
and `:38-42` says nobody in this repo has decoded a single one of those words), criticals
(`GV_CRITICAL = 17` at `agents.py:789`, defined and never sent) and the absolute
denominator (`ENEMY_MAX_HEALTH = 100` is a placeholder, `content/world.toml:13`).

**Procedure.** One uncustomised weapon at a known attribute rank; auto-attack only; blocks
of ~50 swings against each Suit in a pre-registered marks order; read the float on
`0x00A3` property 16.

**The falsifiable prediction, restated after the skeptic.** UPSTREAM (GWW "Damage
calculation", edited **2025-08-01**, and "Armor rating", edited **2026-01-28**;
`gww-facts.md:250-266`): every +40 armour halves armour-respecting damage, so the ratio
across 60/80/100 is **1 : 0.7071 : 0.5000**. The 0.707 step is a signature that linear,
percentage and subtractive models cannot produce by accident. **SURVIVED**: the skeptic
re-ran the simulation independently and got a *larger* separation than the design claimed —
3.2σ / 4.5σ / 6.3σ at n = 25/50/100. The ratio is genuinely scale-free: it needs no health
number from anywhere and is immune to customisation, inscriptions and an unmet weapon
requirement, all of which scale both numerator and denominator.
**CORRECTION the skeptic forced:** state it as a **one-parameter fit**, not a pass/fail
against the 2010 labels. Recover the divisor **D** jointly from `r80 = 2^(-20/D)` and
`r100 = 2^(-40/D)`, report D and the consistency of the two estimates. That tests the
exponential *form* without depending on numbers from a page edited sixteen years ago; then
report separately whether D = 40 *given* those labels.

**What the skeptic refuted outright, and must not be quietly restored:**

- **The Master of Damage's periodic announcement is a RATE, not a running total.**
  `gww-facts.md:102` says "the average damage you do per second" — the design reasoned about
  it as a cumulative sum and built its headline check ("`slot − our_running_sum` is the
  SAME CONSTANT in all ~36 messages") on that. The residual of a rate is `sum(t)/t`, which
  is neither constant nor monotone. The cumulative total arrives **once**, in the `/bow`
  report. Re-state as `slot_k ≈ our_sum(t_k)/(t_k − t_engage)` plus one exact cumulative
  check.
- **And the oracle is probably unreadable with today's tools.** OBSERVED (completeness
  critic): `0x005F CHAT_MESSAGE_NPC` occurs **zero times** in the whole live corpus, and
  `codec.fields_for("GAME_SMSG", 0x5F)` is `[msg_header, agent_id, byte, string16[8]]` —
  an 8-code-unit EncString, not free text. Combined with the EncString refutation in §1,
  the one "check that cannot be forced true" on this island may not be legible at all.
  **Confirm this offline before the damage session, not after** (rung 3).
- **The design's crit test self-refuted on its own corpus.** "REFUTED IF any property-17
  co-occurs with a property-16 on the same target within one swing interval" is *already
  true today*: `p17(target 48, cause 46) @ t=22.768` and `p16(target 48, cause 47) @
  t=23.352`, 584 ms apart. Scope every damage aggregation to **(target, cause)**, not
  target. Scoped that way the evidence is *stronger* than the design claimed: p17 sits
  exactly on the attacker's own melee-finish, in the slot that attacker's p16 occupies in
  an otherwise clean ~1.9 s cadence.
- **"Property 17 replaces 16" is CONTESTED, not OBSERVED.** The design cited
  `studies/agentprops/FINDINGS.md:70-79` for the three-kinds dispatch and skipped `:81-82`,
  which reads that 17 does not modify the health record but does raise a damage
  notification. Under "17 replaces 16" a body hit only by 17s never loses health on the
  client. Settle it on **loopback** at zero cost: send a lone property 17 to our own client
  and watch the bar.
- **`GV_CRITICAL = 17` is UPSTREAM from one lineage** (Py4GW; `agents.py:590-597` says so
  in its own words). The corpus establishes only "17 is a damage kind occupying a swing
  slot" — blocked, glancing and a bonus-damage kind all produce the same capture, and the
  one p17 *smaller* than its pair's max p16 (agent 278: 8 vs 25) is what a glancing blow
  would look like. **The sharp free test the skeptic supplied:** UPSTREAM
  (`gww-facts.md:220-221, 279`) a critical always uses the **maximum** base damage, so
  against one (target, cause) the property-17 population must have **variance zero** while
  property-16 is a spread. The corpus already shows both p17s against agent 48 as the
  identical dword; one differing p17 in the same block refutes "17 = critical" outright.
  Costs nothing (rung 3).
- **The overkill fix was aimed at the wrong line.** OBSERVED, re-verified here:
  `_damage_fraction` already clamps at `authsrv.py:146-147` (`if frac > 1.0: frac = 1.0`)
  *before* calling `_fraction`, and every damage send routes through it. The server can
  emit an overkill crit today — as −1.0. The real finding the design walked past is that
  ArenaNet's observed **−1.125 refutes the premise quoted at `authsrv.py:124`**, "the wire's
  floor for it is −1.0" (studies/combat amendment C4).
- **Circular discriminator.** The design listed "damage magnitude" as one of three ways to
  tell the Suits apart, then reported the damage ratio. Strike it; the marks ordinals plus
  spawn coordinate carry the identification.

**Confounds, with the ones the skeptic added marked.**

| Confound | Control | Source |
|---|---|---|
| Weapon customisation +20% base | uncustomised weapon, or record it | UPSTREAM, `gww-facts.md:276` |
| Inscriptions +10–20% conditional | record the weapon | UPSTREAM, `:277` |
| Unmet weapon requirement → 1/3 damage | record the requirement and the rank | UPSTREAM, `:278` |
| Criticals are a **mixture** in any sample | separate, never average; use the variance test | UPSTREAM, `:279-281` |
| Attack-skill bonus is armour-IGNORING and rides the same packet | auto-attack only, no skills | UPSTREAM, `:282-286` |
| Reforged Mode ≈ 20% stat delta, no wire mark | `--mode` declared, and see §5 gap 5 | `content.py:138-139` |
| Death penalty −15%/death, cap −60%, moves max health — the denominator of every fraction | no deaths in this session; deliberate deaths go LAST, in a different one | UPSTREAM, `:389-390`, `:400-402` |
| **The Suits DIE** (added by skeptic) | budget in **swings**, not wall-clock; the 60 AR block dies fastest and it is the denominator of both ratios; aggregate on (definition slot, spawn coordinate), not agent id | UPSTREAM, `:192`, `:319-320` (GWW "Practice target", edited **2014-02-07**) |
| **Two Suits of 60** (added by skeptic) | name which body in the plan; the pair is a *better* control than the design realised — it bounds body-to-body variance directly | UPSTREAM, `:89-90` |
| **`--minutes` defaults to 10** (added by skeptic) | pass `--minutes 45`; the protocol is ~25 min | OBSERVED, `livesession.py:1741` |
| **The player's agent id is not `player_id`** (added by skeptic) | `tape.client_version`'s `player_id` is a per-connection 32-bit handle (3426761088, 669793701, …) while the in-instance agent id is 31; identify the player from the `0x009F` property-42 `1`-then-`100` pair at t < 1 s | OBSERVED |
| **A single unknown opcode discards the rest of the capture** (added by skeptic) | decode with `strict=False` and assert on the receipt; a new map brings new opcodes, and `tape.decode_all(strict=True)` raises on the first `Undecodable` (`codec.py:134`, `tape.py:53-59`) | OBSERVED |

### 3.2 Range constants from marker coordinates

**Verdict: the RUN survives; the ANALYSIS as designed was REFUTED.** This is the family
where the skeptic did the most damage, and the correction is worth more than the original.

**What stands there.** UPSTREAM (GWW "Range", edited **2026-02-09**, `gww-facts.md:53-73`):
`Short Bow Target` at 1004 gwinches — "maximum range for a Shortbow, measured **from the
marked firing spot**"; `Recurve Target` 1273; `Longbow Target` 1498; casting range 1248 (no
marker); touch/melee 144; compass 5020. Markers `Adjacent`, `Adjacent to Foe`, `Nearby`,
`In the Area` exist **and the wiki gives no numeric value for adjacent, nearby or in the
area** — it illustrates them with a screenshot. Those three are exactly what the Isle can
measure and the wiki cannot tell us; that is the highest-value gap on the page.

**What it measures.** `ATTACK_RANGE = 1500.0` (`authsrv.py:1888`, whose own comment reads
"units. Ours entirely; nothing measured it"); `ENEMY_MELEE_RANGE = 150.0` (`:1991`, "ALL
THREE NUMBERS ARE OURS", and already refuted from both directions — `studies/monsterai`
measured ~65 / ~599 / ~706 units for three models); `AGGRO_RANGE = 1200.0` (`:1907`); AoE
radii, which are modelled *nowhere* (`land_skill` is SINGLE TARGET, ALWAYS,
`authsrv.py:3025-3033`); and the unit question — whether 1 wire unit == 1 gwinch is
**UNVERIFIED**.

**Procedure.** Read the markers' spawn coordinates out of one capture. They are stationary,
so **no combat is required** — this is the cheapest deliverable on the island and it rides
free on the roster pass (rung 6).

**REFUTED: the scale-free three-marker fit has ZERO degrees of freedom.** The objective
`Σᵢ (dᵢ/d₁ − rᵢ/r₁)²` has its i=1 term identically zero, leaving 2 residuals against 2
unknowns; geometrically it is two Apollonius circles, so 0 or 2 intersections and never a
fit with a spare constraint. Measured (`<scratchpad>/v_geom2.py`): on a true star it returns
two solutions, `k=1.0000 eps=1.1e-13` and a **phantom at `k=0.9374`**; on **arbitrarily
placed** markers, **139 of 200 random triples admit an exact-ratio solution**. So the
design's headline outputs `k` and `ε` were produced by an arithmetic that cannot fail, and
`ε` — which the design called "the instrument's own error bar" — is ~1e-13 regardless of
truth, which would score every AoE radius REFUTED.

**What replaces it.** Fix the origin from the wire and make the absolute method primary.
**The design rated the exact-position oracle "UNVERIFIED as to which input produces it",
and this tree names it:** OBSERVED, `authsrv.py:1444`
`GAME_CMSG_LAST_POS_BEFORE_MOVE_CANCELED = 0x0047`; `test_cmsgnames.py:301-302` pins
"0x0047 reports where the player IS; 0x003E names somewhere else";
`studies/movement/FINDINGS.md:52` records the client volunteering its own final position on
cancel. **The trigger is a movement cancel, which the operator can produce on demand.** Add
a plan step that cancels a move while standing on the firing spot, and demote the ratio fit
to a consistency check it can actually fail.
The alternative oracle is not good enough on its own: OBSERVED (`<scratchpad>/v_cmsg2.py`),
`0x003D` n=430, successive-pair **median displacement 144.23 units** at median dt 0.501 s —
±14% on `k` against d ≈ 1004, which cannot distinguish `k = 1.000` from `k = 0.8964`.

**Other corrections that stand:**

- **"All three bow markers share one firing spot" is UNVERIFIED, not an inference.** Only
  the Short Bow row carries "measured from the marked firing spot" (`gww-facts.md:61`); the
  "center target" language belongs to the AoE circles (GWW "Master of Area Effects", edited
  **2010-12-18**), a different origin on a different part of the island. It is the
  load-bearing assumption of the whole fit and the fit cannot test it.
- **The `nearby` prediction must be `{252, 240}`, not 252.**
  `studies/monsterai/FINDINGS.md:763` reads adjacent **166**, nearby **252** (240 for a
  named anomaly set), in the area **322**, from GWW "Area of effect" rev 2685457, edited
  **2023-03-31**. A measured 240 would otherwise be scored REFUTED against a source that
  permits it.
- **The step billed as measuring the SERVER's range test measures the CLIENT's.**
  Auto-walk-into-range is a client decision, and the driver by design emits no input
  (`livesession.py:1161-1167`), so no passive live capture can produce an out-of-range
  attack. Relabel it.
- **Provenance trap.** A `[range.*]` row with `source = "capture"` whose gwinch value came
  from dividing a measured wire distance by a wiki-derived `k` is a wiki number wearing a
  measurement's provenance, and `content.py` cannot catch it (`:382` strips only
  `provenance` and keeps every other key verbatim). Report wire-unit distances as
  `capture`; report the gwinch radii as `wiki` with a `page`. See §8.
- **`Terrain.height_at(gx, gy)` takes GRID coordinates** (`terrain.py:491-492`) and the
  create carries WORLD coordinates; the world→grid transform (Map Parameters chunk
  `0x2000000C`, `studies/customarea/FINDINGS.md:325`) must be named, and "terrain height is
  in the same unit as world XY" is **UNVERIFIED** before any height threshold uses it.
- **`0x00C1` is c2s** and needs `cmsgstream.timed(stamp, "c2s", "game")`, not
  `tape.decode_all`, which returns s2c plaintext only (`tape.py:280-296`).
- **Marks and tape events share an axis but not an origin.** `marks.bind()` is
  capture-relative (`marks.py:101-104`); `load_tape`'s events are relative to that
  connection's first s2c segment, `info["t0"]` (`tape.py:171-175`). Add the offset or every
  mark lands on the wrong window.

**The free static lead this family turned up, and it inverts the priority.** OBSERVED
(`<scratchpad>/v_const.py` against `pinned.find()` → build 38797): as float32 bit patterns
`144.0` n=5, `166.0` n=4, `252.0` n=1 (0x5fb83e), `322.0` n=1 (0x5fbcba), `624.0` n=1
(0x5fc136), `1012.0` n=3, `5020.0` n=1 — while `1004.0`, `1248.0`, `1273.0`, `1498.0`,
`2512.0`, `2508.0` are **absent** as float32. RECONSTRUCTION: 252/322/624 sit at a constant
0x47C stride, and walking that stride gives `74, 84.5, 127, 150, 175, 185, 252, 322, 624,
684, 768, 852` — a monotone ladder consistent with repeated code blocks each carrying a
radius immediate. **The asymmetry is the finding: the AoE radii the wiki cannot give us
look statically recoverable, and the bow ranges it can give us do not.** Disassembling the
readers at those addresses is permitted under CLAUDE.md carve-out (1) for `codescan.py`.
Do this before spending a live session on `k`.

**And a real bug this family found, worth landing on its own:** OBSERVED,
`toolkit/authsrv/behaviourrun.py:255` is `"pos": tuple(v[3:5])`, but a create is 24 fields
with the opcode at index 0 and the position a **tuple at `v[5]`** — reproduced:
`RAW create len 24  v[0..6] = [32, 1, 18, 3, 0, (12169.0, 3222.0), 21]`, confirmed against
`agents.py:529-541`. Today the analyser reads agent 278's position as `(1, 9)`. The test
passes because `test_behaviourrun.py:140-141` uses a hand-made 5-field fixture that has
never existed on any wire.

### 3.3 Conditions, isolated one per NPC — the ten Students

**Verdict: SURVIVES WITH CORRECTIONS, and its most likely outcome is a refutation.** Say
that out loud before the run.

**What stands there.** UPSTREAM (GWW roster, `gww-facts.md:125-136`): ten Students, one
condition each — Bleeding, Poison, Burning, Blind, Dazed, Cracked Armor, Weakness, Disease,
Crippled, Deep Wound — every one level 20, each carrying a single self-heal so the
condition is isolated. UPSTREAM (GWW "Student of Cracked Armor", edited **2012-02-24**,
`:141-144`): standing near the circle around him inflicts Cracked Armor — a
proximity-triggered application with an observable radius.
**Internal inconsistency in the recon file, flagged rather than resolved:** `:138-139`
gives an ally/foe split naming **nine** Students; Student of Burning appears only in the
roster at `:184`.

**What it measures.** Conditions, hexes and enchantments, which are NOT MODELLED IN ANY
FORM: `grep -n 'EFFECT_' toolkit/authsrv/authsrv.py` returns only `EFFECT_DEAD` and
`EFFECT_TRANSITION`. Only `0x0041` of the six EFFECT_* opcodes has ever been observed live
(4 times, all payload `[65, 31, 0, 3434, 0, 1]`, all on map 146).

**Static groundwork, and it re-measured clean under attack (OBSERVED, skeptic's own runs):**
`python toolkit/clientscan/consttable.py --table s_charCondition --rows 40` →
`file 0x637580..0x6375A4, 9 × 4`, string ids 24968…24984; `textrec` resolves them to
Bleeding/Blind/Burning/Crippled/Deep Wound/Disease/Poison/Dazed/Weakness. `skilltable`
`type_code == 8` selects **exactly 10** rows — ids 478–486 plus 2077 — `prof 0, attr 51,
flags 0x2000, target 1`, durations 25/10/3/15/20/15/15/20/20/20, scales
0/90/7/50/20/0/0/200/64/20. One caveat the tool prints itself and the design omitted:
`rival strides that also close: [12]`.

**Procedure.** Stand in each Student's application window, marked per event, with the
condition applied, allowed to expire, and reapplied. Deliverable: the condition → skill-id
map, the durations on the wire, the `+0x04` discriminant and the buffId allocation pattern.

**The falsifiable prediction.** The ten `0x0042` episodes carry skill ids **478–486 plus
2077**. Contiguity is the discriminator: any real applying skill would be scattered, and an
`s_charCondition` ordinal would come back as 0–8.

**What the skeptic refuted or forced:**

- **The instrument's opcode has ZERO ArenaNet witnesses** (§1, item 3). `0x0042`'s layout
  comes from our own loopback plus client disassembly (`studies/skillcast`), not retail
  traffic. That does not make the family wrong; it makes the **refutation branch** — that
  conditions ride some other channel — the likely outcome. That is still worth having, but
  it is one deliverable, not seven.
- **Two of the predictions cannot discriminate, and the fix costs zero live minutes.**
  `studies/skillcast/FINDINGS.md:975-979`: the client stamps its own clock at apply time and
  owns the countdown; the client's own `s_skill` row already carries the magnitude and
  duration. So "no message" is the expected observation under *both* the mechanic-exists
  and mechanic-does-not-exist hypotheses. Corroborating: 28 `0x009F` property-42 messages
  in the whole corpus, **22 at t ≤ 1.0 s**, and the single late one repeats a value already
  set — the live corpus contains **zero observations of a player's max health changing
  mid-session**. **`toolkit/authsrv/probes.py:1962` (`_buff_type_steps`) already sends
  `0x0042 [agent, skill, field3, buffId, f32(duration)]`.** Substitute skill 478/480/482,
  watch our own client, and the live session stops asking three questions it cannot answer.
- **The Blind block is procedurally impossible as written.** It needs ≥40 blinded swings;
  Blind's `duration0` is 10 s and `ATTACK_INTERVAL = 1.75` (`authsrv.py:1887`), so one
  window is 6–7 swings and 40 needs ≥6 re-applications inside a 4-minute block. Attack the
  Student of Blind *himself* — the measurement is a rate, so target armour is irrelevant
  and the blind is continuously re-applied.
- **`0x0042` has NO source-agent field.** `studies/skillcast/FINDINGS.md:900-902`:
  `{ targetAgent; u16 skill; u32 unnamed; u32 buffId; float duration; }` — `sourceAgent` is
  structurally absent. Drop `source_agent` from the row schema; attribution rests entirely
  on the marks ordinal, so an episode whose apply time falls outside its mark window must be
  emitted **unattributed**, never assigned.
- **The duration field is typed `dword` in the catalog** (`schema/messages.json`
  GAME_SMSG 66) while the client does `fld` on it. Any reader must reinterpret with
  `struct.unpack('<f', struct.pack('<I', v))` or it will compare a large integer and always
  fail.
- **The `scale0`-as-pips reading is incoherent and its worked ratio was recalled, not
  derived.** Bleeding, Poison and Disease all have `scale0 = 0` and are three of the four
  degeneration conditions; the "Burning : Bleeding = 7 : 3" sub-prediction cannot come from
  a 0. **Replace it with a measured integer prediction:** OBSERVED, the corpus's property-44
  values are `0.2×24, 0.4×4, 0.02×2, 0.041667×2, 0.04, 0.020833, 0.0625, 0.083333,
  −0.011111`; agent 50's form a ladder `1/48, 2/48, 3/48, 4/48` and agent 40's max health is
  96 — i.e. **property 44 = (pips × 2 hp/s) / max_health, quantised per agent**. Closable
  offline today. Note also that the design's value list dropped the single **negative**
  sample, which is the corpus's only degeneration-shaped observation.
- **The ally/foe split is the family's largest risk and was disclosed and then not
  propagated.** Five of ten Students are allies, and no wiki text says an ally Student
  applies anything to a passing player — yet the design's cleanest number-vs-number check
  depends on Student of Deep Wounds, an ally. Check the five ally pages before authorising.
- **The proximity trigger is a PRECONDITION of a step, not a prediction**, and it rests on a
  page edited 2012-02-24. Time-box it: if the condition has not landed within 20 s of
  arrival, move on.
- **A correction to a claimed corroboration, and it matters beyond this family.** OBSERVED:
  `0x009F` property 43 occurs n=11 with values **0.044 ×4, 0.0396 ×4, 0.033 ×3**, sent once
  per game connection at t ≈ 0.6 s to one player agent — and it **changed between two of the
  owner's own sessions three days apart**. So `content/world.toml:230`'s 0.0396 from
  gw-preservation is one of three observed values, not a witness corroborating it.

**The offline half nobody has opened.** OBSERVED (completeness critic):
`python toolkit/clientscan/consttable.py --table s_effect` →
`0x7A2CA8..0x7AAE78, 2077 × 16`, index column at +0x00, with **one index hole at row 2036
holding 2077** — and 2077 is exactly the Cracked Armor skill id measured out of `s_skill`.
No tool in this repo reads it.

**And the largest single miss across all four families:** hexes and enchantments have **no
instrument at all**, while UPSTREAM (`gww-facts.md:385-388`) the Master of Magic is
surrounded by a **Torch of Enchanting**, a **Torch of Hexes** and a **Torch of Hexes
(degeneration)** — three interactive objects that apply an enchantment, a hex and a
degenerating hex **on demand, with no NPC AI in the way**. The recon file calls this cleaner
than any Master and it is right. What blocks it is our side, not theirs: OBSERVED,
`GAME_CMSG_INTERACT_AGENT = 0x0039` (`authsrv.py:1355`) arrives **29 times** in the live
corpus and the server's entire response is `state["interacting"] = values[1]`
(`:5102-5131`); `0x003B NPC_SERVICE_SELECT` arrives **22 times** unhandled; and there are
**117 tag-0 (item/gadget-class) creates over 32 distinct agents** in the corpus against a
server that defines exactly one agent type, `AGENT_TYPE_LIVING = 1` (`agents.py:75`).

### 3.4 Scripted behaviour — interrupts, blocking, healing, pets, respawn

**Verdict: SURVIVES WITH CORRECTIONS**, with three of nine predictions withdrawn or
re-based and the tooling estimate wrong by an engine.

**What stands there.** UPSTREAM, per-NPC GWW pages with dates: **Master of Interrupts**
(edited **2014-02-26**) R/Me — Charm Animal, Comfort Animal, Disrupting Lunge, Distracting
Shot, Punishing Shot (elite), Troll Unguent, Leech Signet; "tames a level 15 Elder Wolf as
soon as you approach him". **Master of Blocking** (**2010-12-18**) — page lists no skill
bar, which is a fact to check rather than an absence. **Master of Survival**
(**2022-08-30**) R/N — Dryder's Defenses, Melandru's Resilience (elite), Pin Down, Storm
Chaser, Troll Unguent, Parasitic Bond, Plague Touch; "will continually run around the hill".
**Master of Healing** (**2014-09-07**), **Master of Hammers** (**2010-12-20**) W/Mo with
five knockdown-adjacent skills. Universal on every Master's page: "will resurrect after two
minutes, with full health and energy, at the location he/she was defeated"
(`gww-facts.md:169-171`). Practice targets: **30 seconds** (GWW "Practice target", edited
**2014-02-07**, `:319-320`).

**What it measures.** `REVIVE_AFTER = 8.0` and `PLAYER_REVIVE_AFTER = 10.0`
(`authsrv.py:1771`, `:1926`, both ours — 120 s against 8 s is a factor of fifteen);
interrupts (`GV_INTERRUPTED = 35` occurs **zero times in 22,137 decoded GAME_SMSG** and is
never sent); blocking/evasion/misses (the corpus contains **zero observed misses** — all 42
`MELEE_ATTACK_FINISHED` are paired with damage, so nothing in the vault distinguishes
"cancelled" from "missed"); NPC skill selection (`pick_skill` is round robin and its own
docstring says "THIS IS A TESTING FUNCTION, NOT A DECISION ABOUT AI"); NPC aftercast
(RECONSTRUCTION — the NPC path arms recharge at cast *start* and never adds aftercast,
because no NPC in the corpus casts twice, so there is no cycle to tell start-triggered from
finish-triggered).

**What the skeptic refuted:**

- **The regeneration example was a check that could not fail.** The design read a pip ladder
  "against a 96-health pool" for agent 50 — but agent 50 is definition slot 1421 and has
  **no max-health reading anywhere**; the corpus's only non-player `PROP_HEALTH_MAX` values
  are agent 40 = 96 (slot 1346), 38 = 8, 43 = 8, 278 = 40, pinned at
  `test_npcdefs.py:78 HEALTH = {1346: 96, 1434: 8, 1442: 40}`. The 96 was back-solved, and
  for any value there is an H making it a multiple of 2/H. Worse: **no agent with a measured
  max health carries a single property-44 message.** Withdrawn.
- **The healing prediction's basis was spawn initialisation, not healing.** All four
  property-34 messages land on a `WORLD_CREATE_AGENT` for the same agent **within 1 ms**
  (agent 50 @153.7444 / create 153.7444; agent 50 @156.2470; agent 43 @79.1863; agent 278
  @17.9845). The corpus contains **zero observed heals**. Re-state the basis as "no witness
  either way" — which is the stronger position — and require the property-34 not to
  coincide with a create.
- **The respawn key is wrong, and the undercount hid it.** There are **three**
  death→re-create candidates, not one, and agent 38's re-creates are under a *different
  definition slot*: raw `0x2000059a` (slot 1434) at t=0.629, then `0x2000053f` (slot **1343**)
  at 74.779 and 132.002; agent 36 goes 1484 → 1484 → **1420**. Keyed on agent id, agent 38
  yields a 54.9 s "respawn" for a creature that never respawned. **Key on (definition slot,
  spawn position) with a preceding death bit required.** On a 60+ NPC public district the
  churn will be worse than Lakeside's.
- **The blocking test does not discriminate, and the design built the confound itself.** It
  identifies a block as "an `ATTACK_STARTED` with no property-16 damage within 4 s" while
  attacking the Master who "will continually run around the hill" — blocked and
  walked-out-of-melee-range are the same bytes. Use **Master of Blocking** (stationary,
  unclaimed by any family), score only inside marked stance windows, and state the expected
  blocked fraction so "all 15 paired" can distinguish the hypotheses.
- **The speed reading is confounded by a skill on the subject's own bar** — Storm Chaser is
  a movement-speed stance on the same three lines quoted for "runs around the hill".
  **Master of Winds** (E, Windborne Speed, `gww-facts.md:375`) does one thing and is
  unclaimed.
- **The interrupt confirmation is scoped narrower than its conclusion.** Absence across four
  generic-value channels does not establish absence across ~150 opcodes. Diff **all**
  opcodes in the interrupt window against a control window of a cast that completed, and
  rest the confirmation on an empty diff.
- **"A table, not an engine" is materially wrong.** OBSERVED: `behaviourrun.analyse()`
  (`:344-390`) calls **none** of `window_steps`, `control_verdict`, `encounters`,
  `separation`, `by_model` or `chat_marks`; their only callers in the tree are
  `test_behaviourrun.py`. The CLI does origin + framing + tick-drift + a marks count and
  stops. Every step here needs an analyser that does not exist. Cost it that way.
- **Name collision:** the proposed `toolkit/authsrv/agentlife.py` clashes with the existing
  `test_agentlife.py`.
- **Both "realistic" kill targets self-heal** (Troll Unguent on Interrupts; Troll Unguent +
  Melandru's Resilience + Dryder's Defenses on Survival), and Master of Interrupts' Elder
  Wolf is a **second attacker** in every window that includes him.
- **Visibility churn is the corpus's dominant pattern** — agent 50 cycles create/remove five
  times in 135 s — and it collides with the respawn, the property-34 and the movement-gap
  readings simultaneously. It belongs in the confound table, not as an aside.

**What survived.** The two-minute / thirty-second respawn split is genuinely deterministic
and scriptable, and the design's discipline of using every wiki number as a *prediction*
with a named refuter held on this axis with no exceptions the skeptic could find. So did
the confound table, which is the strongest single artefact any of the four families
produced: the PvP/784 control, the Reforged control, the death-penalty ordering argument,
the burrow control and the corpse-persistence-vs-respawn separation are all correct.

**One refutation the design made itself, and it was right to.** `studies/combat` records a
Wolf fight in our existing corpus and asked whether it is Master of Interrupts' Elder Wolf.
It is not: every live connection we hold is map 0/146/148/164.

### 3.5 The instruments no family claimed

The four families claim roughly 29 of ~50 bodies and **none of the seven interactive
objects**. Ranked by what they close, from the completeness critic:

| Unclaimed | Instrument for | Why it matters |
|---|---|---|
| Master of Magic + the three Torches | hex / enchantment application on demand | the single largest miss; see §3.3 |
| Six Zaishen Weapon Masters | known-stat weapons, free, in one place | the only cheap route to the two undecoded modifier dwords at `content/items.toml:22`; `itemprobe.py` already reads the equipped item record out of a running client |
| Master of Energy Denial | energy on the wire | closes a CONTESTED row nothing else touches |
| Master of Blocking | a **stationary** blocker | the fix §3.4's skeptic asked for |
| Master of Winds | a clean movement-speed subject | the fix for the Storm Chaser confound |
| Master of Enchantment | damage mitigation that is **not armour** | Protective Spirit caps damage at a fraction of max health — an armour-independent second test of §3.1's damage decode, which otherwise has one cross-check and §3.1 shows that one is probably unreadable |
| Master of Hammers | knockdown | `GV_KNOCKED_DOWN = 63` (`agents.py:808`) defined, never sent, never observed |
| Master of Resurrection | death penalty −15%/death, cap −60% | not merely unmeasured — it is a **confound on §3.1**, because DP moves max health, the denominator of every fraction |
| Guard of the Isles ×3 (W lvl 20, Defy Pain) | a live max-health change mid-fight | which S4 measured as absent from the entire corpus |
| Master of Paths | an explicit untargetable/invulnerable flag | `AGENT_UPDATE_FLAGS` goes out at `authsrv.py:3374` and no study names a single bit |
| Master of Spirits | server-created agents that are not the caster | "no agent can own another" today |
| Master of Lightning | incidentally, a **map discriminator** | Lightning Orb is UPSTREAM-stated as absent from the PvP Isle, so its presence witnesses 280 over 784 from the wire |
| Master of Items + lever/flag stands/repair kit | gadget *use* actions, and morale (+10% max health) | second-order for combat, first-order for the `0x0039`/`0x003B` channel |
| Churrhir Fields' 15/35/55 ladder (a different map) | **out-of-sample validation** | UPSTREAM, `gww-facts.md:308-315`: 20-point steps at a different absolute offset, so a curve fitted to 60/80/100 makes a *prediction* it never saw |

Genuinely irrelevant to Rurik, and named so nobody re-litigates them: The Guide and the
quest chain, the Canthan Ferry Captain (map travel is already nailed 3-for-3), Razah (a
hero, a party subsystem an order of magnitude larger than this arc), Master of Conditions
(dialogue only), Master of the Isle (ports to 784).

---

## 4. What we already hold

**The capture census.** OBSERVED (S4, `python toolkit/origin.py` and
`find C:/gd/Rurik/vault/captures -name "*.jsonl" | wc -l`): **3,125** `.jsonl` files —
by origin ours 2,069, live 27, unknown 1,020; by client build 38797 = 1,841, 38833 = 228,
unknown = 1,047; by directory portal 1,005, authsrv 1,002, gamesrv 735, selftest 339, live
27, patcher 15, portal80 1, raw 1. **It is a moving target**: two counts minutes apart
differed by 9 files because a parallel session was writing into the vault.

**Six live capture directories, three usable** — `20260807T133758`, `20260807T143055`,
`20260810T235916`. All build **38797**, the pinned build, so the live corpus has no
mixed-build problem. Map ids per connection, from the client's own VERSION frame
(`tape.client_version`, `tape.py:543-572`): **148, 146, 164 and 0**. **NO ISLE CAPTURE
EXISTS**, and nothing in the corpus is post-Searing.

**The decode chain works to the exact final byte on real ArenaNet bytes.** OBSERVED:
connection `:61193` of `20260810T235916` framed **111,179 of 111,179 s2c bytes** into 5,797
GAME_SMSG over 123 opcodes, no residual, no error; every connection of both larger captures
framed clean. The c2s half decodes too: `python toolkit/authsrv/cmsgstream.py 20260810T235916`
→ 500 GAME_CMSG over 5 game connections, 25 opcodes, residual 0.

**The capture→content pipeline exists and has already run.** OBSERVED:
`python toolkit/authsrv/npcdefs.py` → "3 capture(s), 54 definition(s) declared, 7 hostile /
with a model id: 43 / with an attack rate: 4 / with a health value: 3", written to
`vault/content/npcs.toml`; `python toolkit/content.py` loads **56 npc rows** (2 tracked + 54
vault). Of those 56, **44 carry a `model_id`, 56 carry a `level`, 3 carry a `max_health`,
and ZERO carry armour or coordinates.**

**Spawn geometry is reproducible across sessions.** OBSERVED, and this is the strongest
unplanned result in the survey: two independent live sessions **three days apart** on map
148 give byte-identical agent ids, definition slots, model ids and coordinates for the
static NPCs — e.g. agent 44, slot 1470, model 116698, pos (8436, 4819) in **both**. Only
the two wandering agents moved.

**What is on the wire and what is not.**

| Wanted | Status | Evidence |
|---|---|---|
| model id | **held today**, no code change | `0x0057`, 44 of 56 loaded rows carry one |
| name string ids (`enc_name`) | **held today** as a 4- or 5-word id tuple | `0x0056` field 9 |
| level | **held today** | `0x0056` field 7 (`agents.py:173`) |
| name as readable text | **NOT HELD** — EncString, no decoder | §1, `studies/textrec/FINDINGS.md:53-58` |
| world coordinates | **on the wire, discarded** | `WORLD_CREATE_AGENT` field 5 is a clean vec2; `npcdefs.read()` reads only values[1]/[2]/[9]/[12] (`npcdefs.py:265-288`) |
| max health | **on the wire but RARE** | 28 property-42 messages in 22,524; 23 are the player's own agent; five non-player readings (96, 8, 8, 40, 40), all arriving 2–3 s **before** that agent's `0x0035 ATTACK_RATE` — i.e. at combat engagement, not on spawn and not on targeting (UNVERIFIED at n=2 agents) |
| armour | **NOT ON THE WIRE AT ALL** | observed `0x009F` property ids are {1,3,8,11,12,13,20,22,23,28,30,32,36,37,41,42,45,58,60,64,66}; upstream's id 14 never occurs |

**The static side.** OBSERVED: all four Isle string ids resolve out of the owner's own
archive against the pinned build — `python toolkit/clientscan/textrec.py 2972 2973 82827
82828 167881` → 2972 `Isle of the Nameless`, 82827 `Isle of the Nameless (PvP)`, and 2973 /
82828 are a single 9-word authored sentence (the PvP row's with a `(PvP)` suffix). **That
sentence is ArenaNet's expression and is not quoted here or anywhere in the repo** — see
§8. 167881 returning `None` through `textrec` is not a failure: it is an archive **file
id**, not a string id, and it resolves to MFT row 71636, flags 3, 43,784 bytes, magic
`ATEX`.

**THE LOAD-BEARING NEGATIVE, and it is what makes this arc capture-only.** OBSERVED, HIGH
confidence, four independent lines from four directions:

1. The map file's chunk vocabulary is the client's own and **none of its 23 slots is an
   agent slot**: `s_chunkInfo` @ `0x00A6CF78`, 23 records of 40 bytes — Header, Editor
   (old), Terrain, Zones, Props, Obsolete (1), Water, Mission, Path, Environment,
   Locations, Obsolete (2), Map Parameters, Editor, Collision, Light, Shore, Sight, Sound,
   CubeMap, VisData, Occluders, PathEngine. All **16,094 chunks over all 698 map files**
   decompose into exactly these.
2. **Props is scenery, not agents**: `u16 model; f32 x,y,z; u8 rot[3]; u8 scale; u8 flags;
   u8 points; (i16 dx, i16 dy)*points` — a model index, a position and a ground outline. No
   health, level, profession, skill bar, allegiance or name string id. It round-trips
   **349 of 349** retail maps, so it is not a partial reading hiding an agent field.
3. The remaining per-map chunks are stubs or too small: Locations is 13 bytes in 349 of 349,
   Collision 9 bytes in 349 of 349 (and `MapData:2691` "Cannot bloat server collision data"
   says the client knows they are the server's). The one variable undecoded candidate is
   **Mission** (`0x20000007`), 56…1,226 bytes over 349 maps, 211 distinct sizes, and
   **391 bytes on row 21641**. UPSTREAM says 60+ NPCs stand on the Isle; 391 bytes cannot
   hold 60 agents with model and position, and the corpus **maximum** of 1,226 cannot hold a
   roster for any map. That is a bound, not a decode — see §5 gap 9.
4. **The positive experiment**, which is the strongest of the four: the client's NPC
   definition table is populated **from the wire** and indexed by the wire's own value.
   Creating a monster-class agent whose definition was never sent **crashes the client** on a
   dense-array bounds check — the client's own crash text, `Assertion: index < m_count /
   P:\Code\Base\rtl\Array.h(587) / Build: 38797`, with our index in the trace arguments and
   the crash timestamp equal to the packet's send timestamp (`studies/enemy/PLAN.md:443-460`).
   A client carrying a static per-map roster would not need the server to define types
   before spawning them, and would not die when the server forgets.

**Consequence, stated plainly:** everything sections 2–7 of `gww-facts.md` claim about the
Isle — marker coordinates, the three Suits, the Master of Damage's 590 health, the Students'
conditions, the Masters' skill bars — is **UNVERIFIABLE from `Gw.exe` and `Gw.dat`**. The
map file gives terrain, props, paths and collision; the server gives every agent.

---

## 5. The gap list — what code would have to exist

Ordered by what unblocks the most.

1. **A per-agent reader.** NOT FOUND: no committed tool emits agent rows with coordinates.
   `WORLD_CREATE_AGENT` field 5 is a clean world vec2 and `npcdefs.read()` reads only
   values[1]/[2]/[9]/[12] (`npcdefs.py:265-288`). S4 proved a ~40-line version works and it
   produced the cross-session-stable table in §4. **It unblocks every family's analysis and
   the entire range star.** It must partition on the class tag before masking (tag 2 = NPC,
   low 16 bits are the definition slot; tag 3 = player; tag 0 = item/gadget —
   `npcdefs.py:83-88` warns that applying the mask to a player create yields a meaningless
   definition). Add its `TESTS.md` row in the same commit (`test_srclint.py` §7 checks both
   directions and can go red). **Do not name it `agentlife.py`** — `test_agentlife.py`
   exists.
2. **The name default.** OBSERVED: `authsrv.py:3704` is `"name": npc["name"],` with no
   `.get`, while `npcdefs.py:43-44` deliberately never emits a name and
   `test_npcdefs.py:229` asserts its absence. **A vault-emitted `def_NNNN` row cannot be
   spawned at all.** And the failure is silent in the worst way: `agents.py:52-63` records
   that when this happened, the throw was inside instance bring-up, so the harness still
   reported PASS and the map readback was still green — every body was simply absent.
3. **The damage model.** `authsrv.py:2273` with `HIT_FRACTION = 0.15` at `:1770`. No armour
   term, no weapon term, no level term, no critical, no strike-level formula. Without this,
   §3.1 can measure the curve perfectly and it lands nowhere.
4. **A capture selector for `npcdefs.live_captures()`.** It globs the whole directory
   (`:368-386`) and `main()` has no filter (`:404-405`), so dropping a fourth live capture
   into the vault turns `test_npcdefs.py` **RED on six pinned counts** (`:76-79`, and the
   assertions at `:98-158`). That is the test doing its job, but it must be planned for in
   the same change.
5. **`--mode` propagation.** `livesession.py:1460` writes `game_mode` into the capture
   manifest as an operator declaration; `tape.load_tape`'s info dict does not surface it
   (`tape.py:232-247`); `npcdefs.py:397-401` takes `--mode` from its own CLI and **defaults
   to `"unrecorded"`**. A capture correctly taken with `--mode base` still emits
   `mode = "unrecorded"` on every stat row unless the operator repeats the flag.
6. **A spawn-row compiler.** Coordinates belong in the `spawn` table (`content/world.toml`),
   not `npc`, and **no tool in this repo emits spawn rows from a capture**. Three content
   emitters exist — `npcdefs.py` → npc, `attribtable.py` → attribute, `skilltable.py` →
   skills — and none writes a spawn.
7. **`map.280` in `content/maps.toml`.** Ten map rows exist (148, 146, 449, 194, 55, 474,
   558, 143, 90, 144); an eleventh reddens `test_content.py:130`
   (`world.census().get("map", 0) == 10`). And `contentids.preflight` refuses the launch
   outright if the client's archive cannot bind the file id, since "a file id is archive
   STATE, not a property of the map" (`contentids.py:228-234`, `:286-313`).
8. **EncString → readable name.** NOT ESTABLISHED (§1). Two routes: (a) the Hatcher
   precedent — send a captured `enc_name` from our own server to our own client and read the
   rendered nameplate, which costs one loopback session; (b) find where the client obtains
   the 8-byte RC4 key pair — `textrec.record_key` (`textrec.py:368`) already implements the
   hash once the pair is known. Until then a capture identifies NPCs by an opaque tuple plus
   model id, level, allegiance and position, which **is** a stable join key across sessions,
   just not a human-readable one.
9. **The Mission chunk decode.** UNDECODED in this repo; ruled out as an NPC roster **by
   size alone**, which is a bound and not a decode. Its first dwords read neither as world
   floats (12 of 96 plausible) nor as small integers (0 of 95 under 1000). What would close
   it: decode across the 349-map corpus the way `props.py` was done, or find its load
   handler off `s_chunkInfo` at `0x00A6CF78 + 7*40`.
10. **An effect/condition reader.** NOT FOUND: no committed tool reads the buff family out of
    a capture; the `bufflog.py` §3.3 needs is unwritten.

---

## 6. The ladder

Numbered rungs, one exit criterion each. **Rung 1 needs no operator.** Rung 2 is the one
that can cancel the whole plan and should be requested from the owner the same day, in
parallel with rung 1.

**Rung 1 — the per-agent reader, proved against captures we already hold.** No operator, no
client, no ArenaNet.
*Exit:* a committed tool that reproduces S4's map-148 cross-session table (agent 44, slot
1470, model 116698, pos (8436, 4819) in both sessions), partitioning on the class tag, with
its `TESTS.md` row in the same commit.

**Rung 2 — the cancellation check: does the capture account own a character that can reach
map 280?** OBSERVED: every decrypted live game connection is map 0/146/148/164 and the
player's `PROP_HEALTH_MAX` reads 100 in all of them — consistent with a Pre-Searing
character, which cannot reach the Battle Isles. **UNVERIFIED** whether the account has
another character; what confirms it is one login and a look at the character-select list.
Three of the four skeptics found this independently and none of the four designs asked it.
*Exit:* the character that will play is named in the plan file with its level, profession
and route to 280 — or the first deliverable of this arc is a character, not a capture.

**Rung 3 — the offline bench.** No client. Runs in parallel with everything above.
Contents, each already named and none of them run: the gwinch float32 scan and a
disassembly of the readers at `0x5fa8de`–`0x5fc136` (carve-out (1), `codescan.py`);
`s_charDamage` (14 × 4 at `0x6375CC..0x637604`, string ids 2001–2013 → Blunt/Piercing/
Slashing/…/Sacrificial, **unread by anything**, and damage *type* is modelled nowhere);
`s_effect` (§3.3); the property-44 pip quantum; the `0x00A4` projectile cross-check against
the 13 samples already in the vault; the property-17 zero-variance test; the
`behaviourrun.py:255` `v[3:5]` bug; **whether `0x005F` is readable at all**, which decides
whether §3.1 has a cross-check; and testing the wiki damage formula against the 22,524
messages we already hold, which S3's own gap list flags as a free falsification nobody has
attempted.
*Exit:* each item ANSWERED or explicitly declared unreachable offline, written into
`studies/isle/FINDINGS.md`, **before any live minute is spent**.

**Rung 4 — the loopback probes.** Our server, our client, no ArenaNet.
The `0x0042` condition render via `probes.py:1962` with skills 478/480/482; the lone
property-17 render (settles the CONTESTED "17 replaces 16"); the energy drain-pool probe
with a positive control; the EncString render probe (the Hatcher precedent). Each of these
answers a question a live session cannot.
*Exit:* each named question resolved on our own client with an operator-confirmed render,
per the repo's rendered-acceptance rule.

**Rung 5 — the plumbing.** Gaps 2, 4, 5, 7 of §5.
*Exit:* a vault-emitted `def_NNNN` row spawns on loopback, and dropping a synthetic fourth
capture directory into the vault does not redden `test_npcdefs.py`.

**Rung 6 — LIVE #1, the roster pass.** ~20 minutes, **no combat, no deaths, no `/bow`**.
Walk the island, target every body once in a pre-registered F9 order. It carries none of the
confounds that make the others fragile: no death penalty moving the denominator, no Reforged
question on stats we are not reading, no respawn fragmenting agent ids, no crit mixture, no
30-second Suit deaths. **The entire range star rides free here**, because the markers are
stationary and their coordinates *are* the constants.
*Exit:* the agent-id ↔ definition-slot ↔ model-id ↔ `enc_name` ↔ spawn-coordinate table for
the roster and the gadgets; every range marker's coordinate; and `0x0195` field 1 recorded
against the pre-registered prediction 165811 with the third branch (113021 / a shared id)
pre-registered too.

**Rung 7 — LIVE #2, the damage pass.** Only after rung 6 names the bodies and rung 1 proves
the reader. One uncustomised weapon, auto-attack only, `--minutes 45`, budgeted in **swings**.
*Exit:* D recovered jointly from `r80` and `r100` with the consistency of the two estimates
reported, aggregated on (definition slot, spawn coordinate), and the property-17 population's
variance reported against the crit prediction.

**Rung 8 — LIVE #3, the effects pass**, ordered by how little AI is in the way: **Torches
first** (a gadget applies one effect on click, with no bar, no aftercast, no allegiance),
then the five **foe** Students, then Master of Energy Denial, then Master of Blocking. Order
matters: if the Torch's application does not arrive on `0x0042`, the channel assumption is
refuted in the first two minutes and the rest of the session can be redirected instead of
wasted.
*Exit:* the channel question answered — either the episodes carry 478–486/2077 on `0x0042`,
or the refutation branch names what channel they do ride.

**Rung 9 — LIVE #4, the scripted pass.** Respawn timers (30 s targets, 120 s Masters),
Master of Interrupts, Master of Hammers for knockdown, **deliberate deaths LAST** because
death penalty moves the denominator of every fraction measured earlier in the same session.
*Exit:* respawn intervals keyed on (definition slot, spawn position) with a preceding death
bit required; an interrupt window diffed against a completed-cast control window across
**all** opcodes.

**Rung 10 — Churrhir Fields.** The 15/35/55 ladder as an out-of-sample prediction from rung
7's fitted curve.
*Exit:* the curve predicts 15/35/55, or it does not — either is a result.

**Rung 11 — land it.** Merge at the tested milestone; `PLAN.md` §3 and §8 updated, dated,
commit-stamped. An unmerged branch means §3 is stale for everyone else.

**One cross-cutting question that must be settled BEFORE a plan file is written, not during
a run.** `studies/monsterai/FINDINGS.md:1119` sets a hard behavioural cap: *"no more than 3
approaches on the same creature type per session, no repeated visits to one spawn point."*
The conditions protocol alone is five approaches to one Student at one fixed spawn point,
and the Blind fix pushes it further. The Isle is a training area and the rule may reasonably
be scoped narrower there — but that is an owner ruling, and none of the four designs raised
it.

---

## 7. What this does not settle, and the honest pessimistic case

**Rows no Isle body can close, with what would close them instead:**

- **`ENEMY_SKILL_RANK = 12`.** Monster skill bars are STRUCTURALLY UNREACHABLE — ArenaNet
  never sends them (`studies/combat/PLAN.md:246-250`). Record it as OURS permanently, or
  infer it by fitting a known NPC's observed damage against its published skill and level.
- **The SERVER's skill range check.** The driver sends no input by design
  (`livesession.py:1161-1167`), so a passive live capture cannot emit an out-of-range
  attack. Only a loopback probe separates client-side auto-walk from a server test, and even
  that measures *our* client.
- **Attribute ranks, `0x003A` column 3, `0x0037` points, the point budget.** These need a
  character with nonzero ranks, **wearing runes**, with unspent points, and the Skills &
  Attributes panel on camera. That is a login-and-open-a-panel session, and it is a
  **precondition** of the rank curve, not a peer of it.
- **The rank → damage curve and its 11/12/13 kink.** `gww-facts.md:247` says outright it
  "does not need the Isle at all — it needs attribute ranks."
- **Character level as a damage term.** One session at one level cannot produce it.
- **Aggro range, leash, spawn anchor, call-to-arms.** Every Isle body is stationary and
  scripted, which makes it the **worst** aggro instrument in the game. `behaviourrun.py`'s
  existing campaign on a normal explorable is the right apparatus.
- **`KILL_REWARD_VALUE = 26` and "attr 0 = experience".** The Isle is actively hostile to
  this: UPSTREAM, killing practice targets yields no experience or loot **by design**
  (`gww-facts.md:324`). Needs several different-level creatures in a normal explorable.
- **Enemy swing damage.** Correctly dropped: UPSTREAM (`:291-296`), inbound damage strikes
  one of five armour pieces (chest 3/8, legs 2/8, head/hands/feet 1/8) so it is a mixture.
  Measure outbound. If nobody ever measures inbound, say so and leave it OURS.

**The pessimistic case, and it deserves to be read before the enthusiasm.**

The Isle measures **ArenaNet's server**, and Rurik is not trying to be ArenaNet's server.
Learning that retail's armour curve is `2^(−ΔAR/40)` does not make our server correct; it
replaces one invention with a better-sourced one, in a file where `dealt = agent
["max_health"] * HIT_FRACTION` has no term to put it in and where a `def_NNNN` row from a
capture cannot even be spawned. Four designs specify what to measure; none specifies who
**consumes** it, and the consumption is several files of work per family that nobody has
costed. The real risk is a beautifully-instrumented campaign producing a folder of
well-labelled numbers that no line of the server ever reads — the same failure mode as the
40-hour-stale status table at the top of `CLAUDE.md`, arriving through a different door.

The measurements are also thinner than they look: n=1 session, one character, one weapon,
one attribute rank, one level, one mode, one district — a single point in a space the wiki's
own formula says has at least four dimensions. The repo's history is not encouraging here.
`SWING_WINDUP_RATIO` is n=42 across two declared speeds with a confound the file names
itself, and the player's own windup was n=4 and turned out to be **contaminated by skill
damage**, discovered nineteen study sections later. The island's apparent advantage is fifty
instruments in one place, and the behavioural cap forbids exploiting exactly that.
Meanwhile the labels the whole armour family is indexed by come from a page edited
2010-02-06: we would measure a ratio precisely and attach it to x-values we never measured.

And the most uncomfortable part: **the Isle is designed for a human with a HUD.** Its entire
premise — the Master of Damage announcing your DPS, the markers named on your screen, the
Suits labelled in your target window — is *read the number the game shows you*. The one
thing this pipeline cannot do is read the HUD. Strip the display away and the island
degrades toward "a map with a lot of stationary level-20 bodies", which is worth something
but is worth less than a normal explorable capture on a post-Searing character — which would
yield the same combat channels **plus** item drops, party traffic, map content, and the
attribute-rank and EncString data that gate 1 and the naming problem actually need. Set
against a plan that currently cannot confirm the capture account owns a character able to
walk there, the honest summary is: **good science aimed slightly to one side of the critical
path, resting on a precondition nobody has checked, feeding a server that cannot currently
hold the answer.**

The counterweight is real and should not be understated. The armour ratio is genuinely
scale-free and genuinely discriminating; the range markers are constants ArenaNet placed for
us that need no decoding at all; spawn geometry is reproducible across sessions; and **25 of
29 generic-value ids have never been seen on any wire**, so almost any capture of the effect
channel is new information. But the first hour goes to the cancellation tests, not the
science.

---

## 8. Provenance note — what may be recorded from an Isle capture, and in what form

Per CLAUDE.md's boundary, which is **measurement vs expression**, not bulk vs single and not
data vs code.

**Permitted, in bulk, from an Isle capture:** agent ids, definition slots, model ids, file
ids, levels, professions, move speeds, attack intervals, flags, scale, allegiance tokens,
world coordinates, string **ids**, property ids and their observed float/int values, opcode
counts, timings, and every count and offset in this document. These are facts we measured
about what the service sent us. The precedent is explicit and recent: the owner's ruling of
2026-08-10 recorded at `content/npcs.toml:47-54` holds that an NPC definition read off a live
capture is *documentation of an observed fact rather than a reproduction of binary data —
nine integers describing what the service sent us*, and `lakeside_worm` is the row that
arrived under it.

**Still refused:** asset bytes, `Gw.dat` chunks, textures, audio, model data, decompiled
bodies, and bulk dumps of assert strings. A **single** assert cited as the evidence for a
claim is a measurement — keep it with its file and line, as §4 does for
`Array.h(587)` — and the crash dialog is not extraction, because it is text the retail
client shows any player who crashes.

**Authored text is expression, and this arc touches it twice.** String ids 2973 and 82828
resolve to a single 9-word authored sentence telling the player to practise before combat.
**The ids travel; the sentence does not.** This document deliberately describes it rather
than quoting it. The same applies to any NPC dialogue an Isle capture picks up.

**NPC names: commit the id, resolve the string at run time.** This is the rule and it is
also, conveniently, the only thing we can currently do. Concretely, an Isle-derived NPC row
carries:

```
[npc.def_<slot>]
definition = <slot>          # the wire's own index
model_id   = <id>
enc_name   = [w0, w1, w2, w3]   # the 16-bit words off 0x0056 field 9 -- IDS, never text
level      = <n>
```

and **never** an English string. Where a human-readable name is wanted, it is resolved at
run time from the owner's own archive, exactly as `mapbuild.py` already proves with FINDINGS
14's five mandatory chunks. Until a client we control renders an `enc_name` and a person
reads the nameplate, any name we attach is OURS and UNVERIFIED —
`content/npcs.toml:90-97` says this about itself, and the `hatcher` row is named the way it
is *because* its four words came back as `Hatcher [Collector]` on our own client.

**The source vocabulary, and the two traps in it.**

- An Isle-derived row is `source = "capture"` with `capture` (the vault stamp) and `origin`
  (`"live"`), plus `mode` for any of `health`, `max_health`, `armor`, `armour`, `energy`,
  `max_energy` (`content.py:138`). `"unrecorded"` is **accepted** — what `content.py`
  refuses is silence, not ignorance.
- **Trap 1:** `"capture"` is **not** in `EXTRACTED` (`content.py:104`), so it does not
  require an `extractor` field. A hand-written Isle table with `source = "capture"` and no
  tool behind it loads clean — the same shape of hole `content.py:106-112` describes for
  `measured`. Emit rows from a tool, and record the tool voluntarily the way
  `npcdefs.py:355` already does.
- **Trap 2, and it is the one this arc will actually hit:** the armour ratings 60/80/100 are
  a **wiki label attached to a body**, not a measurement off the wire — nothing on the wire
  carries an armour number. Such a row is `source = "wiki"` with a `page`
  (`content.py:145`), **never** `source = "capture"`. The same applies to any gwinch radius
  obtained by dividing a measured wire distance by a wiki-derived scale factor: the wire
  units are `capture`, the gwinch value is `wiki`. `content.py` cannot catch this for you —
  `:382` strips only `provenance` and keeps every other key verbatim, so there is no field
  schema standing between a wiki number and a measurement's provenance except the person
  writing the row.

**`gww-facts.md` itself stays in the vault**, gitignored, on purpose. It is a research
pull, and facts that graduate to `content/` must be re-derived from our capture and carry
their own per-row provenance rather than being copied across.