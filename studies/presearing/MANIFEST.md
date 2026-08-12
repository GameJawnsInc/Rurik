# Pre-Searing Ascalon — Content Manifest

*Build 38797. Written 2026-08-06 from five parallel research passes plus one reconciliation pass that re-measured every CLIENT claim against `vault/areatable/full.json` and `vault/research/2026-08-06/*.json`.*

> **REVISION, 2026-08-11 — R0b exists, and every "until R0b" in this document is spent.**
> The body below is left as written because it is the 2026-08-06 record and §8 already
> half-caught this. What changed: the vault holds **three keyed live captures** — 22,524
> GAME_SMSG over twelve connections, 758.0 s, 155 opcodes, twelve of twelve framing clean —
> so the phrases *"there is no recording"* (§"Why this exists"), *"R0b blocks roughly one
> third of R4c"* (§893), *"stays at 0 and is reported as blocked until R0b exists"* (§960)
> and *"returns as a fidelity check only once R0b exists"* (§962) are all discharged.
> **§8 was right and was righter than it knew**: R4c-2 is not blocked, and beyond the
> published health and armour it flagged, the *join* is now measured — the definition slot
> in `WORLD_CREATE_AGENT` field[2] is a stable server-side key across sessions
> ([studies/reconstruction/FINDINGS.md](../reconstruction/FINDINGS.md) §6.1). What limits
> R4c-2 today is **corpus coverage — four kills of three species — not the instrument.**
> Two caveats this document could not have carried: **Reforged Mode is recorded nowhere**
> and scales enemy health ~20%, so every monster number is base or base × 0.8 with nothing
> on this machine able to say which (§7.6); and the WIKI figures below still carry the
> weakness §"Why this exists" admits — they came through search-engine prose rather than
> page reads and have not been re-derived.

---

## Why this exists

R4c's acceptance criterion was *"an area populates and plays like the recording."* There is no recording — R0b was deprioritised, so the criterion referenced an artifact that does not exist. R4b's was *"one skill from each mechanical family resolves correctly,"* and "mechanical family" is enumerated nowhere in this repo. HANDOFF.md answered *"what is done?"* with a region name rather than a content list, so "is v1 finished" has been a judgement call every time it was asked.

This document is the count. It enumerates what Pre-Searing Ascalon actually contains — zones, monsters, quests, skills, items, NPCs, services — marks each number exact or approximate, marks which parts cannot be extracted from the client at all, and states the delta against what the repo holds today. After this, "is v1 finished" is `n of N`.

---

## Revision, 2026-08-11 — the WIKI half re-read from real pages

*Item 3 of "What this manifest does not know" said every WIKI claim here came through
`WebSearch` prose rather than a page read, and named what to re-read first. This section is
that pass. **It is partial** — 7 pages/categories, not the whole list — and it is recorded
here rather than folded silently into the tables above, because three of the corrections
below are corrections to *method*, not just to numbers.*

**How the bytes were got, and why that is not the documented route.** The browser MCP is
still down (`list_connected_browsers` → `[]`, twice, and `tabs_context_mcp` reports the
extension not installed/signed in). But the **scripted route worked** — 7 live requests,
**zero 403s**, where `browse-gw-wiki`'s `access.md` measures "the first five consecutively,
then hard 403 for the rest". That is a real disagreement with a five-day-old measurement and
it is logged as such: **UNVERIFIED whether the quota lifted or the bucket merely happened to
be full.** Do not plan a campaign on it; access.md's "a handful of requests may succeed,
which is worse than none succeeding" still stands. `gwwiki.py` gained a `category`
subcommand for this pass (one request per 500 members, reports `truncated` rather than
silently short-listing).

### 1. The #1 ranked unknown is SETTLED: the four new zones are opt-in content

WIKI (GWW, *Reforged Mode*, read 2026-08-11): Reforged Mode is "an experimental optional
game mode currently in Beta testing", opted into at character creation and toggleable
afterwards at a Shrine to Godly Accoutrements. Under **§Pre-Searing Ascalon** it grants
"Access to the *A Bastion In the North* quest chain in the Northlands, **which unlocks: the
Piken Square outpost, the Forsaken Tunnels dungeon**, Devona as a pre-searing hero."

So rows **779, 780, 877, 878 are gated behind an opt-in mode.** Their *existence* was already
CLIENT-settled; their *availability* now is too. The competing readings in the old item 1 are
both resolved: the pass that asserted from WebSearch prose that Reforged Mode is "only an
opt-in XP/gold buff and the zones are ordinary content" is **REFUTED on both halves**, and
`vault/research/2026-08-04/presearing-scope.md` §0's "opt-in alpha" is **confirmed as to
opt-in and updated as to status** — alpha 2025-12-18, **beta 2026-05-27**.

**Scope consequence, for the owner's decision in §"One scope decision":** if v1 means
Pre-Searing playable in *normal* mode, the region is **15 rows, not 19**, and #1–#6 all move.
If v1 includes Reforged, it inherits a Beta whose content ArenaNet is still changing.

### 2. A capture-campaign hazard nobody has recorded

WIKI (GWW, *Reforged Mode* §Pre-Searing Ascalon): "**Enemy health is reduced by 20%** for all
enemies, including hostile charmable animals. **Enemy armor is reduced by roughly 20%** for
most foes."

PLAN.md §1.7 puts absolute monster HP/armor in the four genuinely server-only things, and
R4c-2 grades on them. **The same monster has two stat blocks depending on a mode flag the
capture does not record.** A live capture taken in Reforged Mode yields HP numbers 20% off
base and perfectly self-consistent — the failure shape this repo keeps paying for. **Any
monster-stat capture must record the character's Reforged Mode state**, and `toolkit/origin.py`
stamping *whose server* is not enough to disambiguate it. Flagged here; it belongs in R0b's
procedure, not only in this manifest.

### 3. #16 is no longer a BOUND: 70 EXACT, with the roster

`Category:Ascalon (pre-Searing) quests` holds **71 members: 70 in ns 0, plus one
subcategory** (`Category:Vanguard quests`). The old entry's reasoning — "includes list pages,
redirects and talk pages alongside real quests, so 70 is an upper bound" — is **REFUTED**:
there are no talk pages (ns 1 absent), no list pages, and every ns-0 title is a quest article.
**#16 becomes 70, EXACT**, and the delta row "Quests 0 → 2 mandatory / ≤70 total" becomes
2 / 70.

Two counts fall out of the roster, both previously APPROX:

- **Profession Test quests: 6 of 6 confirmed by name** — Warrior, Ranger, Monk, Necromancer,
  Mesmer, Elementalist Test. #19 was EXACT on WebSearch prose; it is now EXACT on a member
  list. There is also a parallel set of six *A New \<Profession\> Trainer* quests that no pass
  saw and that this manifest cannot yet place in the chain — **do not assume they are the
  *A Second Profession* branches**; the old §Quests names only two branch titles by name
  (*The Elementalist Experiment*, *A Mesmer's Burden*), both present in the roster, and
  guessing the other four from title shape is exactly what this repo's method forbids.
- **Vanguard quests: exactly 9**, and all nine named — Annihilation ×3 (Bandits, Charr,
  Undead), Bounty ×3 (Blazefiend Griefblade, Countess Nadya, Utini Wupwup), Rescue ×3
  (Farmer Hamnet, Footman Tate, Save the Ascalonian Noble). **#14 conflated two things**: it
  reads "Vanguard-quest bosses: 3 named of ~9", but the ~9 is the *quest* count and only the
  three **Bounty** quests name a boss. On this evidence Vanguard bosses are **3 of 3, all
  named** — not 3 of 9. The remaining Vanguard quests are kill-count and rescue content with
  no boss to miss.

### 4. A misattributed citation, caught by reading the page

#13 cites *"WIKI (The Searing): 'the altar is guarded by 30 Charr (including Smokeskin and
three other bosses)'"* and builds the four-Charr-boss row on it. **That sentence is not on
that page.** GWW's *The Searing* is 27 lines of pure lore — zero occurrences of "Smokeskin",
"guarded by", or "30 Charr"; it names only *Vatlaaw Doomtooth* and the shaman *Bonfaaz
Burntfur*, the latter a name no pass recorded.

The quote may well exist on some page — a mission or bestiary article — but **the citation as
written is wrong**, so #13's "6 named bosses, one unresolved" now rests on an unverified
source rather than on a weak one. The fourth name stays unresolved, and **Jaw Smokeskin,
Scarl the Slicer and Red Eye the Unholy drop from "confirmed"/"agreed across two searches"
to UNVERIFIED pending a page that actually contains them.** This is the manifest's own
warning about WebSearch prose ("It can drop or paraphrase a number") landing on it.

### 5. The Northlands roster is contaminated with Reforged-only content

WIKI (GWW, *Reforged Mode*): "**Additional enemies appear in the Northlands**: Groups of grawl
including the stronger **Grawl Crones and Grawl Fighters**; Groups of Oakhearts including the
stronger **Ironhearts**; Two groups of Charr at each of the two gates of the Great Wall. The
gates are also closed now."

§Monsters' per-zone roster lists "Grawl Crone, Grawl Fighter, … Charr" for The Northlands as
though they were base content. **They are Reforged-mode additions**, and *Ironheart* is a
creature the passes never recorded at all. The faction-conditional aggro note kept for AI
design ("Crones/Fighters hostile to other Grawl and Oakhearts") therefore describes
**Reforged** content. Every per-zone roster in §Monsters should be assumed mode-ambiguous
until re-read; this is the one case measured.

### 6. The NPC categories do fold roles together — measured, and the hostile rosters are worse than feared

`Category:Regent Valley (pre-Searing) NPCs` holds **39 members** (ns 0), against the old
"~40 reported by the search backend" — the estimate was good. What it settles is the
*composition* question #29 raised as a hypothesis: the category mixes **~23 hostile creatures
with ~16 service and quest NPCs**, exactly as suspected, so **the ~40/~23 category counts
cannot be read as service-NPC template counts** and the "plausible ceiling 60–100 template
rows" keeps its reasoning but loses these two numbers as support.

The sharper result is against §Monsters. This manifest lists **9** creatures for Regent Valley;
the category carries roughly **23** — adding Bandit Blood Sworn / Firestarter / Raider /
Ringleader, Carrion Devourer, Lash Devourer, Melandru's Stalker, Grawl (pre-Searing), Grawl
Longspear, Grawl Shaman, Skale Broodcaller, Aloe Husk and Aloe Seed. **#10's "35–40, likely an
undercount" is confirmed as an undercount from the one zone that has been checked**, and the
true figure is plausibly well above 40. Note also that *Bandit Raider* and *Bandit Raider
(Vanguard quest)* are **separate articles** — Vanguard variants are distinct creature entries,
which matters because each distinct definition needs its own row under the client's
`index < m_count` constraint.

**One thing this does not settle.** *Hatcher* and *Varis* are categorised under **Regent
Valley**, while §NPCs places both in Fort Ranik. That is consistent rather than contradictory
— the zone table already records 162 (Regent Valley) and 166 (Fort Ranik) **sharing archive
row 44202** — but it is still two documents agreeing offline. **It does not move §NPCs' "On
our Hatcher" verdict one inch**, for the reason given there: neither witness observed our
client standing anywhere.

### 7. The CONTESTED verdict on monster skill bars is itself refuted — in the reverse direction

§Monsters' subsection *"On 'Pre-Searing's monsters barely use skill bars'"* marks the review
panel specialist's claim **CONTESTED** and rests that on one load-bearing example: *"including
the melee baseline: plain Grawl, the most common early encounter, runs **Hammer Bash fuelled
by Frenzy**."*

**Neither skill is on the page.** GWW's *Grawl (pre-Searing)*, read in full, has a `==Skills==`
section containing **only** an event bar — "*During [[Annihilator 2: Searing Day]]*: Belly
Smash, Counter Blow, Endure Pain" — and no base bar at all. Hammer Bash and Frenzy appear
nowhere on it.

Three creature pages were read and **all three have no base skill bar**:

| Creature | Level | Base skills | Armor (all types) | Health |
|---|---|---|---|---|
| Restless Corpse | 1 (22), 15 | **`*''None''`**, explicitly | 30 @ L1 | **80** @ L1 |
| Grawl (pre-Searing) | 1, 18 | **none listed** (event bar only) | — | **80** @ L1, flagged as unusual |
| Skullreaver (boss) | 5 | **no `==Skills==` section at all** | 43 | — (+1 pip regen) |

Skullreaver is the region's **only non-Charr boss**, so this is not a sample of trash mobs. On
this evidence the specialist is **supported, not contested**, and the manifest's contrary
verdict was built on a Grawl bar that does not exist. The `≥9 creature types with a documented
≥2-skill bar` floor (#11) is **not** thereby refuted — the Undead Necromancer's seven skills
are quest-only content and were not re-read — but #11 and the CONTESTED verdict must now be
stated separately, because the quest-only undead were never the specialist's point. **Revert
the CONTESTED marking to the specialist's original claim** unless a page read produces the
melee baseline bar.

**A second contamination axis, alongside Reforged Mode.** Both creature pages carry bars that
apply *only during* **Annihilator 2: Searing Day**, an event. A roster assembled from prose
summary cannot tell an event bar from a base bar — which is very likely where "Hammer Bash
fuelled by Frenzy" came from. Treat any skill bar in §Monsters as mode- **and** event-ambiguous
until read from the page.

**One citation that does check out.** *Skullreaver*'s bounding quote is verbatim on the page:
"Skullreaver is the only non-Charr boss foe in pre-Searing, excluding bosses spawned by
Vanguard quests." (The giver's page title is *Lieutenant Langmar*, not "Lieutenant Samantha
Langmar" as §NPCs has it.)

### 8. Monster health and armor are published — R4c-2 is not wholly blocked on R0b

PLAN.md §1.7's **first** server-only item is "absolute monster HP, energy and armor", and
§"Capture-only" above inherits it: R4c-2 "stays at 0 and is reported as blocked until R0b
exists". **GWW publishes both numbers for Pre-Searing creatures.** Measured on three pages:
Restless Corpse L1 — 80 health, armor 30 against every damage type; Skullreaver L5 — armor 43
against every damage type; Grawl L1 — 80 health, with the page noting this is *unusual* for a
level 1 creature, which incidentally bounds the rest of the tier from above.

This does **not** refute §1.7. The client genuinely cannot read these — GWCA marks
`AgentLiving.hp` a percentage — and WIKI armor is player-inferred from damage, so by
`labeling.md`'s test it is mid-strength, not strong. What it changes is the **sequencing
claim**: monster stat rows can be *seeded* from WIKI today and verified against capture later,
which is exactly PLAN.md §A6's pattern ("seed from the dataset, cross-check every numeric
field, a row counts as verified only when the numbers agree"). The honest restatement is that
R4c-2's monster-stat rows are **capture-*verified*, not capture-*sourced***, and only spawn
placement and AI policy are truly capture-gated. §"Sequencing consequence"'s "R0b blocks
roughly one third of R4c" should be re-derived on that basis.

Drop *tables* are likewise published per-creature (Restless Corpse: Bone, Pile of Glittering
Dust, Skeletal Limb in the Catacombs; Skullreaver: Dead Bow, Sephis Axe, Skeletal Limb) while
drop *rates* remain absent everywhere — which is #33 exactly as written, and is the one row in
this area that survives untouched.

### 9. The per-zone NPC category convention is not universal

*Restless Corpse* carries only `[[Category:Drops bone]]` and `[[Category:Drops dust]]` — **no
zone category at all**, despite living in the Catacombs. So the `Category:<Zone> (pre-Searing)
NPCs` shape that worked for Regent Valley cannot be assumed for the other zones, and the plan
of enumerating rosters one category per zone will silently under-return rather than error.
`Category:Pre-Searing bestiary` returning 0 members is the same hazard from the other side.
**Find the convention from a page's own category tags before spending requests guessing names.**

### 10. The Catacombs undead, read in full — and #11's floor does not survive them

§Monsters said of this zone: *"The permanent residents returned no skill-bar page at all —
**UNKNOWN, not zero**."* All eight named residents plus the boss have now been read. It is
**zero**, and the distinction matters because UNKNOWN invites a capture and zero does not.

| Creature | Level | Prof | Base skill bar | Armor |
|---|---|---|---|---|
| Restless Corpse | 1 (22), 15 | W | **`*''None''`** | 30 @ L1 |
| Raging Cadaver | 3 (22), 15 | N | **`*''None''`** | 32 @ L3 |
| Deadly Crypt Spider | 2 | R | **`''None''`** | — |
| Diseased Devourer | **0** | — | **`''none''`** | 10 |
| Snapping Devourer | 2 | W | **`''None''`** | 10 |
| Crypt Fiend | 3 | N | **1** — Chilblains, at **0 Curses** | — |
| Tomb Nightmare | 4 | N | **1** — Chilblains, at **0 Curses** | — |
| Shatter Gargoyle | 3, 4 (22), 8 (23), 15 | Me | **1** — Backfire, at 3 Domination | 8 @ L3 |
| **Skullreaver** (boss) | 5 | W | **no `==Skills==` section** | 43 |

**Six of nine have no skills at all; the other three have exactly one; not one has a bar of
two.** Two of the three single-skill cases cast at **attribute rank 0**, so even that one skill
resolves at its floor value.

**#11 — "≥9 creature types with a documented ≥2-skill bar, FLOOR" — is not supported by this
zone**, which §Monsters' own roster makes the most skill-dense ambient area in the region. The
floor is carried entirely by **quest-only** content. The one pillar that *does* hold up is the
Undead Necromancer, confirmed verbatim: **7 skills** — Animate Bone Horror, Blood Renewal,
Deathly Swarm, Faintheartedness, Soul Barbs, Vampiric Gaze, Vampiric Touch — across **three
tiers** (L9/12/16) with a distinct attribute spread each. #11 should be restated as
*"≥N quest-only creature types"*, with N re-counted, because "the region contains creatures
with real bars" and "the region's ambient population has bars" are different claims and only
the first is true.

**The cleanest single piece of evidence in this whole question is the Shatter Gargoyle**, whose
page splits its bar by region on one page: **`===Pre-Searing===` gives it one skill (Backfire
at 3 Domination); `===Post-Searing===` gives it four** (Conjure Phantasm, Crippling Anguish,
Energy Tap, Imagined Burden). Same creature, same wiki page, same editors — so the comparison
controls for documentation quality, which is the objection that could otherwise be raised
against the whole table above. **The review specialist's recommendation to pick a post-Searing
encounter as the R4b/R4c oracle is supported by ArenaNet's own creature, documented both ways.**

**Armor, as a seeding range** (per Revision §8): the ambient Pre-Searing tier runs **8–32**
across every damage type, with the region's only non-Charr boss at **43**. Devourers sit at 10
and the Shatter Gargoyle at 8, so armor tracks type rather than level. Note *Diseased Devourer*
is **level 0** — a real value on the page, not a parse failure, and worth knowing before a
level field is validated as `>= 1`.

**A capture-side corroboration nobody was looking for.** The Undead Necromancer's bar contains
**Deathly Swarm and Vampiric Gaze** — the exact two skills the operator cast in tape run 2
(`studies/tape/FINDINGS.md` T1, skills 153 and 105). That is ArenaNet's own creature sharing a
skill set with our recorded session, and it means R4b's Hex exemplar **Faintheartedness 135**
is on a monster bar in the very zone R4c would populate.

### 11. The browser route opened — the whole region's NPC set, read at once

The Chrome extension connected on the eighth attempt (**a full Chrome restart after logging
out was the fix** — logging out and back in was not enough, the extension kept serving the old
account; recorded in `browse-gw-wiki/references/access.md`). That turns one page per request
into 50, and the region was read whole: **206 distinct NPC pages** across the 15 zone
categories, every page's wikitext and every page's category set.

**The category convention, which §9 said to find before guessing.** Zones with a post-Searing
counterpart use `Category:<Zone> (pre-Searing) NPCs` (Regent Valley, Fort Ranik, Ascalon City,
Piken Square); pre-Searing-only zones use plain `Category:<Zone> NPCs` (Lakeside County, The
Catacombs, The Northlands, Wizard's Folly, Green Hills County, Ashford Abbey, The Barradin
Estate, Foible's Fair, Ascalon Academy). There is also a region-wide
`Category:Ascalon (pre-Searing) wildlife` (40) that no pass found. `Category:Ascalon
(pre-Searing) NPCs` holds **only subcategories**, which is why a ns-0 query returns 0.

#### #10 is an undercount by more than double: **91 hostile types, not 35–40**

Classifying the 206 by the wiki's own faction categories (wildlife, Charr, Grawl, Elementals,
Undead, Skeletons, Devourers, Plants, Skale, Bandits, Arachnids, Beasts, Worms, Nightmares,
Gargoyles, Vanguard foes, …) and subtracting the friendly ones (quest givers, merchants,
collectors, henchmen, Ascalon Army, Ascalon Vanguard, royalty):

| | Count |
|---|---|
| **Distinct hostile creature types** | **91** |
| …in base mode | **83** |
| …Reforged-gated | 8 |
| …Vanguard-quest-only | 15 |
| Non-foe NPC pages | 175 |

**#10's "35–40, APPROX, likely undercount" was right to hedge and still low by 2.3×.** Its
three stated reasons all hold up, and the per-zone comparison shows exactly where:

| Zone | §Monsters roster | Actual foe pages |
|---|---|---|
| Wizard's Folly | 2 — *"almost certainly incomplete"* | **18** |
| Lakeside County | 6 | **30** |
| The Northlands | 7 | **26** |
| Regent Valley | 9 | **23** |
| Green Hills County | 9 | **18** |
| The Catacombs | ~13 | **16** |
| Ascalon Academy | 2 | 5 |

**A corroboration nobody was looking for:** all seven **outposts** — Fort Ranik, Ascalon City,
Piken Square, Ashford Abbey, The Barradin Estate, Foible's Fair — contribute **zero** foes.
§Monsters asserts "the seven outposts have no hostile spawns, by the rule every GW1 outpost
follows" from CLIENT type-code reasoning; the wiki's own rosters agree independently.

#### Correcting Revision §10: #11's floor **does** hold, region-wide

**§10 above over-generalised from one zone and this supersedes it.** Of the 91 foes,
**49 have no base skill bar, 11 have exactly one, and 31 have two or more** (deepest bar: 10).
Splitting those 31:

- **13 are Vanguard-quest-only**, **2 are Reforged-gated**, and **16 are ambient base-mode
  content** — Carrion Devourer (6), Grawl Crone (10), Alain (7), Plague Devourer (4), Bandit
  Firestarter (4), Charr Chaot (4), River Drake (3), Grawl Shaman (3), Charr Blade Storm (3),
  Charr Hunter (3), Vatlaaw Doomtooth (3), and the Aloes.

So **#11's `≥9` floor is met by ambient content at 16**, and my §10 sentence "#11's floor is
not supported as stated" was **wrong as a region-wide claim**. What survives from §10 is
narrower and still true: *the Catacombs specifically* has no resident with a ≥2-skill bar, and
the Grawl bar §7 refuted really is absent from *Grawl (pre-Searing)*. The specialist's claim is
therefore neither cleanly supported nor cleanly refuted — **it is zone-dependent**, and the
Catacombs is the worst zone to build an R4b oracle in while the Northlands and Green Hills are
much better. That is a more useful answer than either verdict, and the headline table's #11 is
restored with a scope note rather than downgraded.

**Non-combatant does not mean skill-less.** #12's two confirmed non-combatants both carry
bars: *Aloe Husk* and *Aloe Seed* cast **Healing Breeze and Shielding Hands** at 0 Healing
Prayers / 0 Protection Prayers. They never attack — #12 stands — but "non-combatant" and "no
skills" are different properties and this manifest used them interchangeably.

#### #13 is closed: the fourth Charr boss is real, and there are seven

`Category:Charr bosses` over the region returns **7**: **Jaw Smokeskin, Scarl the Slicer, Red
Eye the Unholy, Blaze Bloodbane**, Blazefiend Griefblade, Vatlaaw Doomtooth, and **Ghast
Ashpyre** — the last a name no pass recorded at all.

**"Blaze Bloodbane" is a real, distinct page.** §Bosses guessed it "may be a conflation with
Blazefiend Griefblade" and **left the fourth name unresolved rather than picked**. The
conflation theory is refuted — both exist separately — so the pass that returned Blaze
Bloodbane was right, and the manifest's caution was still correct procedure: it declined to
guess and the guess it declined to make would have been right. Recorded because the lesson is
about method, not luck.

#### Service NPCs: #29's floor and ceiling both need restating

Of the 175 non-foes: **43 quest givers, 13 collectors, 10 merchants**. #30's "13 named or
role-confirmed service NPCs" lands **exactly** on the collector count, which suggests that row
was really counting collectors. #29's "≥15, plausibly 60–100 template rows" now has a measured
frame: 175 non-foe pages is the true ceiling for named NPCs, though many are one-off quest
characters rather than reusable archetypes.

**#35 needs a Reforged caveat.** Six pages in the region carry `Category:Prophecies henchmen` —
Devona, Cynn, Aidan, Orion, Mhenlo, Little Thom. That does **not** refute "henchmen: 0": these
are the same *characters* appearing pre-Searing as quest NPCs and trainers, not as hirable
henchmen. But Revision §1 records that Reforged Mode adds "**Devona** as a pre-searing hero",
so under Reforged the recruitable-companion surface is **not** zero.

**Reforged contamination, quantified:** **16 of the 206** region NPC pages carry
`Category:Reforged Mode content` (17 carry `Guild Wars Reforged content`). Revision §5 found
the contamination qualitatively in one zone; this is its size.

### 12. Forsaken Tunnels — from "zero names retrieved" to a full roster, and it is a different game

§Monsters recorded *"Forsaken Tunnels ×3 — **UNKNOWN — zero names retrieved**"*, and #10's
reason (c) named that hole. `Category:Forsaken Tunnels NPCs` holds **42 pages, 36 of them
foes**, of which **18 appear nowhere else in the region**. Every one of the 18 is **Charr**:

> Charr Ash Walker · Charr Ashen Lord · Charr Axe Lord · Charr Blade Lord · Charr Blade Warrior
> · Charr Fire Caller · Charr Flame Keeper · Charr Martyr · Charr Mind Lord · Charr Mind Spark
> · Charr Overseer · Charr Patrol Leader · Charr Patrol Stalker · Charr Shaman Lord · Charr
> Stalker · Charr Stalker Lord · **Maz Scourgeheart** · **Wyle Brimscourge**

Three carry a boss category: **Charr Patrol Leader, Maz Scourgeheart, Wyle Brimscourge**.

**The region's hostile-type count therefore becomes 109** — the 91 of Revision §11 plus these
18. Revision §11's 91 reproduced exactly on an independent recompute, which is worth stating
because both numbers came from the same method and a silent drift would have been invisible.

#### The level tier is the finding, not the roster

| | Classic Pre-Searing | Forsaken Tunnels |
|---|---|---|
| Levels | **0–5** (Diseased Devourer 0, Restless Corpse 1, Ice Elemental 3, Raging Cadaver 3, **Skullreaver, the boss, 5**) | **6–24** (Grawl Fighter 6, Charr Overseer 6, Cave Elemental 7/9, Ironheart 8, Wyle Brimscourge 14, **Charr Ashen Lord 24**) |
| Typical base skill bar | **0–1**, usually at attribute rank 0 | **2–4** |
| Deepest bar | Undead Necromancer 7 (quest-only) | **Maz Scourgeheart 23**, across six level tiers (12/14/16/18/20/22) |
| Sample armor | 8–32, boss 43 | Charr Overseer **20** (60 in Hard Mode) |

**This is not the same difficulty tier wearing a new hat — it is post-Searing-grade content
inside the Pre-Searing map graph.** A level-24 Charr in a region whose own boss is level 5 is a
five-fold jump, and the skill bars jump with it.

#### What that does to the scope decision

§"One scope decision the owner has to make" asks whether v1 stops at the Academy mission. **It
now has a second axis with real consequences, and this is the sharpest form of the Revision §1
question:**

- **Normal-mode v1** is levels 0–5, where **6 of 9** Catacombs residents have no skills at all
  and the three that do cast at rank 0. The review specialist's complaint — that Pre-Searing
  proves little about a skill engine — is *strongest* against exactly this scope.
- **Reforged v1** adds a 36-foe Charr dungeon at levels 6–24 with real multi-skill bars, which
  would exercise R4b properly — at the cost of taking a dependency on **opt-in Beta content
  ArenaNet is still changing**, and of roughly doubling the monster surface.

Neither is obviously right and no data settles it, which is why it stays the owner's call. But
the choice is no longer "4 zones in or out"; it is "does v1 contain any content that would
stress the combat engine at all".

#### A method correction: the Reforged category is not a mode discriminator

Only **14 foes** region-wide carry `Reforged Mode content` / `Guild Wars Reforged content`,
yet the **entire 36-foe Forsaken Tunnels roster is Reforged-gated** by Revision §1's own
evidence. The category is applied inconsistently on the wiki. **Use zone membership to decide
mode, never the Reforged category** — which also means Revision §11's "16 of 206 pages are
Reforged-flagged" is a floor on the contamination, not a measurement of it.

#### Two dungeons, confirmed from the category side

`Category:Forsaken Tunnels NPCs` (42) and `Category:Tunnels of the Forsaken NPCs` (47) both
exist and share only **10** pages. §"Four things the zone table settles" claimed these are
different dungeons from the CLIENT row ids; the wiki's own taxonomy agrees independently.

#### Ice Elemental (pre-Searing), the other named gap

**Level 3, armor 10 against blunt, one skill — Frozen Burst at 0 Water Magic.** §Monsters had
it as "lvl 3" with the roster "UNKNOWN — almost certainly incomplete". The level is confirmed;
the creature fits the classic-tier pattern exactly (one skill, rank 0), and Wizard's Folly's
real roster is **18 foes**, not the 2 recorded.

### What this pass did not reach

Unchanged from item 3's priority list, and still open: skill bars for the Catacombs'
permanent-resident undead; *Skullreaver* and *Ice Elemental (pre-Searing)*; any creature at
all in Forsaken Tunnels; the bestiary category for Wizard's Folly and The Northlands
(`Category:Pre-Searing bestiary` returned **0 members — the name is wrong**, and a
zero-member category is indistinguishable from a nonexistent one, which is why the
`category` command reports the count rather than an empty list); and the correct source for
#13's boss quote.

---

## Labels

Matching `studies/character/FINDINGS.md`'s vocabulary, narrowed to the four this manifest needs:

- **CLIENT** — read out of our own pinned build 38797 by a tool in `toolkit/`. The strongest evidence class here. Three times in the research passes CLIENT overruled a written source (Eastern Frontier, Fort Ranik, the dungeon rows); that is why CLIENT rows outrank WIKI rows in every table below.
- **WIKI** — the official wiki, wiki.guildwars.com, page title cited. **Every WIKI claim in this manifest came through `WebSearch` restricted to that host, not through the `browse-gw-wiki` skill's preferred browser route** — the Chrome MCP was not connected in any of the six passes (`list_connected_browsers` → `[]`), and `gwwiki.py` confirmed the documented 403 on the direct route. WebSearch returns a search backend's prose synthesis of a page, not raw wikitext or infobox JSON. It can drop or paraphrase a number. Treat exact figures sourced only to WIKI as approximate unless a CLIENT measurement backs them.
- **OURS** — already implemented or recorded in this repo, path cited.
- **UNKNOWN** — looked and could not settle it. Written in cells rather than filled with a plausible number.

Exactness markers used in the count columns: **EXACT** = cannot move without the client changing. **FLOOR** = a lower bound, true value ≥. **APPROX** = a range with real uncertainty. **BOUND** = an upper limit only.

---

## The headline table

| # | Quantity | Count | Exactness | Source |
|---|---|---|---|---|
| 1 | Map rows in the region (`continent==1`) | **19** | EXACT | CLIENT |
| 2 | …distinct places (dungeon's 3 levels = 1, Academy's 4 rows = 1) | **14** | EXACT | CLIENT |
| 3 | Outposts (`type 10`) — 143, 148, 163, 164, 165, 166, 779 | **7** | EXACT | CLIENT |
| 4 | Explorables (`type 2`) — 145, 146, 147, 151, 160, 161, 162 | **7** | EXACT | CLIENT |
| 5 | Arena rows (`type 1`) — 149, 150 | **2** | EXACT | CLIENT |
| 6 | Dungeon rows (`type 18`) — 780, 877, 878 = one 3-level dungeon | **3** | EXACT | CLIENT |
| 7 | Full-service town rows (`type 13`) in the region | **0** | EXACT | CLIENT |
| 8 | Zones where hostiles spawn | **9–10** | APPROX | CLIENT types + WIKI |
| 9 | One-way exits out of the region | **1** | EXACT | WIKI |
| 10 | Distinct hostile creature type names | ~~35–40~~ → **109** = 91 classic + **18 Forsaken-Tunnels-exclusive** (all Charr) | **EXACT-as-categorised**, Revision §11 and §12 — the old figure was low by ~3× | WIKI, all 225 region NPC pages read |
| 11 | …with a documented ≥2-skill bar | **31** of 91 — 16 ambient, 13 Vanguard, 2 Reforged | EXACT-as-categorised; the `≥9` floor **holds**, but it is **zone-dependent** — see Revision §11, which supersedes §10 | WIKI, pages read |
| 12 | …confirmed non-combatant | **2** (Aloe Husk, Aloe Seed) | EXACT-as-found — but they **do** carry skills (Healing Breeze, Shielding Hands at rank 0); non-combatant ≠ skill-less, Revision §11 | WIKI |
| 13 | Named bosses, non-Vanguard | **6** → **7 Charr bosses**, all named, Revision §11 | Jaw Smokeskin · Scarl the Slicer · Red Eye the Unholy · **Blaze Bloodbane** · Blazefiend Griefblade · Vatlaaw Doomtooth · **Ghast Ashpyre**. The fourth altar name is resolved; the "conflation" theory is refuted. §4's misattributed citation stands as a separate defect | WIKI, category read |
| 14 | Vanguard-quest bosses | ~~3 named of ~9~~ → **3 of 3, all named** | EXACT; Revision §3 — the "~9" was the *quest* count, and only the 3 Bounty quests name a boss | WIKI |
| 15 | Monster **AI archetypes** | **UNKNOWN** | — | server-only |
| 16 | Pages in `Category:Ascalon (pre-Searing) quests` | ~~≤70~~ → **70** | **EXACT** — 70 ns-0 articles + 1 subcategory, composition verified, Revision §3 | WIKI, member list read |
| 17 | Quests strictly required to leave the region | **2** | EXACT | WIKI |
| 18 | Skill quests | **36–43** | APPROX, client-bounded | CLIENT + WIKI |
| 19 | Profession-choice branches | **6** | EXACT | WIKI |
| 20 | Mechanical **verbs** all quests reduce to | **6** | EXACT over ~15–20 examined; APPROX over ≤70 | WIKI |
| 21 | Pre-Searing-reachable player skills | **44** | EXACT | CLIENT, id-resolved |
| 22 | …per profession | W7 R8 M8 N8 Me6 E6 + 1 any | EXACT | CLIENT |
| 23 | Skill `type_code`s in the full player corpus (1,333 skills) | **21** | EXACT | CLIENT |
| 24 | …reached by the 44 | **9 of 21** | EXACT | CLIENT |
| 25 | …distribution | Spell 12 · Attack 8 · Hex 7 · Ench 6 · Skill 4 · Signet 3 · Prep 2 · Stance 1 · Glyph 1 | EXACT | CLIENT |
| 26 | Effect-mechanism families exercised | **16–17 of ~24** | APPROX; the family list is RECONSTRUCTION | CLIENT + WIKI |
| 27 | Families with **zero** Pre-Searing exemplar | **5** (Shout, Interrupt, Well/Spirit/Trap/Ward, Block, Ritual) | EXACT given #26's list | CLIENT |
| 28 | Families with exactly one exemplar | **5** (Stance, energy-mgmt, armor-mod, movement-mod, Glyph) | EXACT | CLIENT |
| 29 | NPC template rows needed | **≥15**, plausibly **60–100** | FLOOR + APPROX | WIKI |
| 30 | …named or role-confirmed service NPCs | **13** | EXACT-as-found | WIKI |
| 31 | Named drop/trophy/material items | **10–12** | FLOOR | WIKI |
| 32 | Monster families implied as drop sources | **≥5** | FLOOR | WIKI |
| 33 | Drop *rates* known, for any item | **0** | EXACT | server-only |
| 34 | Services checked / present in retail | **8 / 4** | EXACT for the 8 | WIKI, CLIENT-corroborated by #7 |
| 35 | Henchmen available in the region | **0** (≤3 auto-fill on the exit mission only) | EXACT | WIKI |

**#24 is the number R4b should be graded on** — it is EXACT, CLIENT-derived, and every code has a named skill id attached. #26 is a secondary narrative: the ~24-family list is a reasonable taxonomy but nobody sourced it, so it is RECONSTRUCTION and should be labelled as such wherever it is used.

---

## Zones

**CLIENT method.** `python toolkit/clientscan/areatable.py --dat vault/dat_study/Gw.dat --names --rows 900`, build 38797, per `studies/areatable/FINDINGS.md`. Full 888-row dump at `vault/areatable/full.json` — gitignored, ArenaNet-derived, never committed. Only counts and structure come out of it into this document.

**The filter is `continent == 1`, and nothing narrower.** This is load-bearing and cost the research passes a contradiction: `continent==1 && region==7` returns 16 rows / 13 distinct name strings; the three Forsaken Tunnels rows sit at `region == 18` **and `campaign == 0`** while every other Pre-Searing row carries `campaign == 1`. Anyone re-deriving this table with `campaign==1` or `region==7` silently drops the dungeon. `continent == 1` alone yields exactly 19.

**Type codes.** 2 = explorable and 10 = outpost are OURS-established (`content/maps.toml`'s own note, cross-checked against gw-preservation's Explorable column). 1 and 18 arrived from one pass marked INFERRED-by-clustering and were **upgraded to CLIENT-corroborated** by the reconciliation: game-wide, type 18's cohort is exactly the EotN dungeon set (`Cathedral of Flames` + Levels 2/3, `Catacombs of Kathandrax` + Level 2, `Rragar's Menagerie` + Level 2) with the identical `…: Level N` naming Forsaken Tunnels uses; type 1's cohort is `Gladiator's Arena`, `D'Alessio Arena`, `Ascalon Arena`, `Shiverpeak Arena`. Type 5 = Prophecies mission and type 13 = full-service town, both established the same way.

| id | Name — CLIENT (WIKI page title) | kind (`type`) | `Gw.dat` file id | in OURS |
|---|---|---|---|---|
| 148 | Ascalon City (*Ascalon City (pre-Searing)*) | outpost (10) | `0x8001B97D` → MFT row 7982, CORROBORATED, shared | **yes** — `content/maps.toml [map.148]`, spawn walkability-verified |
| 146 | Lakeside County | explorable (2) | `0x8001B97D` → row 7982, shared | **yes** — `[map.146]`, but the spawn is Ascalon City's borrowed coordinate, flagged as such in our own file |
| 164 | Ashford Abbey | outpost (10) | `0x8001B97D` → row 7982, shared | no |
| 163 | The Barradin Estate | outpost (10) | `0x1BA26` → row 44199 | no |
| 165 | Foible's Fair | outpost (10) | `0x1BACB` → row 20444 | no |
| 166 | Fort Ranik (*Fort Ranik (pre-Searing)*) | outpost (10) | `0x1BB1D` → row 44202, shared with 162 | no |
| 162 | Regent Valley (*Regent Valley (pre-Searing)*) | explorable (2) | `0x1BB1D` → row 44202, shared with 166 | no |
| 145 | The Catacombs | explorable (2) — **not** dungeon-typed | `0x1C530` → row 20709; also MEASURED in `studies/enemy/PLAN.md` §5 at 51 planes / 5,246 trapezoids | no |
| 147 | The Northlands | explorable (2) | `0x1C539` → row 20118; pairing already recorded in `toolkit/mapdata/test_pathmap.py` | no |
| 160 | Green Hills County | explorable (2) | **UNKNOWN** | no |
| 161 | Wizard's Folly | explorable (2) | **UNKNOWN** | no |
| 143 | Ascalon Academy (staging) | outpost (10) | **UNKNOWN** | no |
| 149 | Ascalon Academy | arena (1) | **UNKNOWN** | no |
| 150 | Ascalon Academy | arena (1) | **UNKNOWN** | no |
| 151 | Ascalon Academy (the mission) | explorable (2) | **UNKNOWN** | no |
| 779 | Piken Square (*Piken Square (pre-Searing)*) | outpost (10) | **UNKNOWN** — postdates every mirror we hold | no |
| 780 | Forsaken Tunnels | dungeon (18) | **UNKNOWN** — same | no |
| 877 | Forsaken Tunnels: Level 2 | dungeon (18) | **UNKNOWN** — same | no |
| 878 | Forsaken Tunnels: Level 3 | dungeon (18) | **UNKNOWN** — same | no |

File ids are **not** `AreaInfo.file_id` — `studies/areatable/FINDINGS.md` §3 established that field resolves only to `ATEX` textures (0 of 157 hit a map row) and is 0 on every Pre-Searing row. Where an id appears above it is the archive/MFT id, sourced from `gw-preservation__server/gameservice/instance_definitions.go` (unlicensed mirror — read and cited, never copied) and independently re-resolved against our own `Gw.dat` via `toolkit/mapdata/archive.py:file_id_table()`, landing on a `flags==259` map-flagged row in every case. That second step is what promotes each id from UPSTREAM to CORROBORATED. **9 of 19 rows have an id from any source; 10 of 19 have none anywhere.**

### Four things the zone table settles that were previously assumed

**There are two dungeons, not one.** The Catacombs (145) is classic and carries `type 2`, not 18. **Forsaken Tunnels** (780/877/878) is a genuine 3-level `type 18` dungeon, entered from a cave north of Piken Square, gated on the quest *A Bastion In the North* — WIKI (*Forsaken Tunnels*, `Feedback:Game updates/20260401`). Its post-Searing counterpart *Tunnels of the Forsaken* is a **different** dungeon at rows 879–882, `continent 0 / region 18` — the same pre/post pattern as Ascalon City vs. Old Ascalon.

**Our pinned client carries content that postdates every mirror in `vault/mirrors/`.** Rows 779/780/877/878 carry `name_id` 79766 / 79868 / 79870 / 79872 against the classic Pre-Searing block's contiguous **10450–10478**. A ~69,000-id gap is appended-much-later, not renumbered. gw-preservation pins clientVersion 37600 and has *no rows at all* for these ids — which is consistent (it resolves 393 of 397 legacy ids cleanly), not wrong. **Existence of this content is settled by CLIENT alone; no wiki needed.** Whether it is gated behind an opt-in mode is a separate, unsettled question — see *What this manifest does not know*, item 1.

**There is no full-service town in the region.** Type 13's cohort game-wide is `Droknar's Forge`, `Henge of Denravi`, `Lion's Arch`, `Kaineng Center`, and post-Searing Ascalon City (rows 81, 811). Pre-Searing Ascalon City is row 148, `type 10`. Zero type-13 rows on `continent == 1`. This is independent CLIENT corroboration of the WIKI-only services finding below (no Xunlai, no armorer, no dye trader) — two evidence classes converging, the strongest cross-source agreement in this manifest.

**Pre-Searing Fort Ranik is its own outpost.** Post-Searing Fort Ranik is row 29, `continent 0 / region 2 / type 5` — a *mission*. Pre-Searing Fort Ranik is row 166, `type 10` — an *outpost*, distinct record, distinct name_id (10553 vs 10474). One pass had left "own map, or a named sub-area of Green Hills County?" as UNKNOWN; CLIENT answers it. This also confirms the WIKI text for *The True King*, which sends the player to Lord Darrin "in Fort Ranik" while still in Pre-Searing.

### The edge of the region

**Exactly one exit leaves the Pre-Searing map graph**, and it is not a normal zone transition: it is a one-way, one-time, scripted narrative gate through the Ascalon Academy cluster (143/149/150/151). WIKI (*Ascalon (pre-Searing)*): "Once a character enters the Ascalon Academy and the following Ascalon Academy mission, it leaves this region and cannot ever return." Every other connection WIKI describes stays inside the 19-row set.

CLIENT corroborates the closure structurally: `studies/mapdata/FORMAT.md` measured row 7982's intra-plane trapezoid graph at **91 disconnected components** before cross-plane portal pairing, dropping to **15** after — city, abbey, estate and fair are drawn as disconnected planes of one file, not one continuous walk.

**The region does not change in place after the Searing.** Post-Searing is a separately-mapped zone set: Old Ascalon (row 33) is its own archive file, not row 148 with a damage flag. Implementing "after the Searing" is a second region on the scale of this one, structurally out of scope for a "Pre-Searing playable solo end to end" v1.

### Where the passes disagreed

One pass reported 19 rows split "15 region-7 + 4 region-18"; the split is 16 + 3 (it counted three dungeon levels as four). One reported "13 distinct zone names, 16 records" — exactly right for region 7, and it simply never looked at region 18. One reported 12 zones (13 minus Piken Square). One, working from WIKI only and never opening the client, reported "8–10 named zones" — **discard that figure**; it is a wiki-derived zone count in a repo whose method is that the client overrules written sources, and it also produced a false claim about our own `content/maps.toml` (corrected in the gap section below).

---

## Monsters

**Nothing in this section is CLIENT.** `areatable.py` reads per-map metadata; `skilltable.py` reads the *player* skill table. No tool in `toolkit/` reaches monster spawn tables, monster stat blocks, or AI data, and PLAN.md §1.7 puts three of those four in the server-only set. Every level number, every skill bar, every creature name below is WIKI via WebSearch summary. This is the weakest-evidenced section of the manifest and the one most likely to move.

**Zones where hostiles appear: 9–10.** Six classic explorables (Green Hills County, Regent Valley, Wizard's Folly, Lakeside County, The Catacombs, The Northlands) + the Ascalon Academy mission map + the three Forsaken Tunnels levels. The seven outposts have no hostile spawns, by the rule every GW1 outpost follows — CLIENT-consistent with #7 above. One pass gave "7 hostile zones"; that predates the dungeon.

**Distinct hostile creature type names: 35–40.** A range, not a figure, and stated as a probable undercount for three specific reasons: (a) some names are level-variant reskins of one species — Undead Necromancer alone has three tiers at levels 9/12/16; (b) rosters for Wizard's Folly and The Northlands came back with one or two names each for full explorable maps, which is not credible; (c) **coverage of Forsaken Tunnels is zero** — no pass retrieved a single creature name for the new dungeon.

### Per-zone roster (WIKI, partial)

| Zone | Creatures named | Skill-bar evidence |
|---|---|---|
| Green Hills County | Grawl, Grawl Invader, Grawl Longspear, Grawl Shaman, Hulking Stone Elemental, Bandit Blood Sworn / Firestarter / Raider, Aloe Husk, Aloe Seed | Grawl: Hammer Bash + Frenzy. Grawl Shaman: Heal Area, Infuse Health. Aloe Husk/Seed: **explicitly non-combatant** — "never attacks, even in retaliation" |
| Regent Valley | Black Bear, Wolf, Giant Needle Spider, Giant Tree Spider, Moss Spider, Moa Bird, Oakheart, River Skale, Plague Worm (quest-only) | Oakheart: Healing Breeze (conditional), Unnatural Seed. Black Bear: Brutal Mauling only (standard charmable-animal pattern). Moss Spider: displays a profession, which is GW1's tell for a real bar |
| Wizard's Folly | Ice Elemental (pre-Searing) lvl 3, Rabbit | UNKNOWN — roster almost certainly incomplete |
| Lakeside County | Grawl line, River Skale Brood, Skale Broodcaller, Carrion Devourer, Warthog, Rabbit | River Skale Brood: Ice Spear. Skale Broodcaller: Elementalist-typed, unprovoked aggro |
| The Catacombs | Restless Corpse, Raging Cadaver, Crypt Fiend, Deadly Crypt Spider, Diseased Devourer, Snapping Devourer, Tomb Nightmare, Shatter Gargoyle, Skullreaver; quest-only: Undead Necromancer, Undead Illusionist, Blood Fanatic, Charr | Undead Necromancer: **7 skills**, three tiers. Undead Illusionist: **4 skills**, three tiers. Blood Fanatic: Vile Touch. **The permanent residents returned no skill-bar page at all** — UNKNOWN, not zero |
| The Northlands | Grawl Crone, Grawl Fighter, Grawl Longspear, Grawl Shaman, Charr, Oakheart, Warthog | Faction-conditional aggro documented (Crones/Fighters hostile to other Grawl and Oakhearts) — worth keeping for AI design; it makes "hostile" non-binary |
| Ascalon Academy mission | Grawl (reusing **post-Searing** level-4 warrior data, per WIKI), Vatlaaw Doomtooth | — |
| Forsaken Tunnels ×3 | **UNKNOWN — zero names retrieved** | — |

### Bosses

WIKI (*Skullreaver*), quoted directly because it bounds the whole roster: *"Skullreaver is the only non-Charr boss foe in pre-Searing, excluding bosses spawned by Vanguard quests."*

- **Skullreaver** — Catacombs, +1 natural health regen. Skill bar UNKNOWN.
- **Four Charr bosses at the Searing altar** — WIKI (*The Searing*): "the altar is guarded by 30 Charr (including Smokeskin and three other bosses)." **Jaw Smokeskin** confirmed, fought first. **Scarl the Slicer** and **Red Eye the Unholy** agreed across two independent searches. The fourth name came back inconsistently — one pass returned "Blaze Bloodbane," which may be a conflation with **Blazefiend Griefblade**, a different, Vanguard-quest-only Charr boss. **Left unresolved rather than picked.**
- **Vatlaaw Doomtooth** — Charr, boss of the Academy mission. UNKNOWN whether the wiki counts him as a fifth Charr boss or separately.
- **Vanguard-quest bosses** — spawn only while their quest is active. Named: Utini Wupwup (Grawl), Countess Nadya (Bandit), Blazefiend Griefblade (Charr). Reported ~9 Vanguard quests total; the other givers are UNKNOWN.

**Quest-only creature types: 6** — Plague Worm, Undead Necromancer, Undead Illusionist, Blood Fanatic, Catacombs Charr, plus every Vanguard boss.

### On "Pre-Searing's monsters barely use skill bars"

> ⚠️ **This whole subsection is REFUTED as of 2026-08-11 — see Revision §7.** Its
> load-bearing example, the Grawl's "Hammer Bash fuelled by Frenzy", **is not on the Grawl's
> page**; three creature pages read in full (Restless Corpse, Grawl, and Skullreaver — the
> region's only non-Charr boss) have **no base skill bar between them**. The specialist is
> supported rather than contested. The original text is kept below unedited, because how it
> went wrong is the more useful artifact: every sentence in it is plausible, specific, and
> derived from search-engine prose that could not distinguish an event-only bar from a base
> bar.

The review panel's specialist raised this (`studies/review/FINDINGS.md:474`, `:500`) as a reason to pick a post-Searing encounter as the R4b/R4c oracle. **The evidence gathered here leans against it, and the claim should be marked CONTESTED.** At least nine creature types have a wiki-documented bar of two or more skills, including the *melee baseline*: plain Grawl, the most common early encounter, runs Hammer Bash fuelled by Frenzy. Undead Necromancer carries seven skills across three tiers. The genuinely skill-less cases (Aloe Husk, Aloe Seed) are ones the wiki explicitly calls out as non-combatants, not a silent default.

Better statement: **Pre-Searing's ambient wildlife leans on single innate attacks or nothing, matching the rest of GW1's wildlife tier; Pre-Searing's actual threats carry real bars.** The claim is asymmetric — one documented 7-skill bar refutes "barely," and that bar's contents are too specific to be a summarization artifact — so believe it directionally while keeping it WIKI, never CLIENT.

**This does not move the capture requirement one inch.** Knowing a monster *has* Faintheartedness says nothing about *when it casts it*, and AI decision logic is §1.7's fourth server-only item. The specialist's operational recommendation survives its premise being wrong.

### Names supplied in task prompts that do not exist

Three example names arrived with the research briefs. All three were checked and all three failed:

- **"Ancient Skale"** — real, but it is a Fissure of Woe endgame necromancer, not Pre-Searing content. Pre-Searing's own tough Skale is the River Skale Brood, which is not a flagged boss.
- **"Resign"** — **NOT FOUND**. No creature by that name exists anywhere in Guild Wars; the only wiki hits are for the `/resign` command.
- **"Red Iron"** — no such item. Plausible referents are Red Iris Flower (a real Nicholas Sandford trophy) or Iron Ingot (a generic material). Not resolved, not guessed.

**Three for three.** Example names arriving in prompts have a perfect failure record in this campaign. Nothing in this manifest was seeded from one.

---

## Quests

### The chain that gates leaving

1. **Message from a Friend** — Sir Tydus, Ascalon City. WIKI: "the first quest of Guild Wars Prophecies," but explicitly **not required** to leave; skipping it costs only gold and XP.
2. **War Preparations** — Sir Tydus. Also explicitly skippable.
3. **`<Profession> Test`** — six pages, given by your own primary-profession trainer. Required before you may test a secondary profession.
4. **A Second Profession** — Armin Saberlin, branching to six NPCs. **This is the hard gate**: "you will need to complete this before being able to enter the Ascalon Academy."
5. **Ascalon Academy** — not itself a logged quest. Sir Tydus offers it only once a secondary profession exists. PvP trial + short mission with Rurik, Searing cutscene, irreversible.

**Exactly two quests are strictly required to leave the region**: the primary Profession Test, then any single branch of A Second Profession. Everything else in Pre-Searing is XP/reward-only optional content — including both quests the wiki flags as "primary." This is the cleanest number in the manifest for sizing R4c: the *mandatory* server-side quest surface is two dialogue-verb quests deep, not the ≤70-page catalog.

### Profession-choice branches (6)

| Profession | Branch giver | Zone |
|---|---|---|
| Warrior | Warmaster Grast | Green Hills County |
| Ranger | Master Ranger Nente | Regent Valley |
| Monk | Brother Mhenlo | Lakeside County |
| Elementalist | Elementalist Aziure — *The Elementalist Experiment* | Wizard's Folly |
| Necromancer | Necromancer Munne | The Catacombs |
| Mesmer | Lady Althea — *A Mesmer's Burden* | Ascalon City (theatre) |

Only two of the six branch page titles were confirmed by name; the other four are known by giver NPC only. Zones for Warrior/Ranger/Monk/Necromancer are inferred from profession theming, not read off a page.

### Volume

`Category:Ascalon (pre-Searing) quests` reportedly holds **70 pages** — WIKI, via the search backend's own category summary, **not verified by opening the page**. That number includes list pages, redirects and talk pages alongside real quests, so **70 is an upper bound on distinct playable quests, not the count**.

**Skill quests: 36–43.** One pass estimated "very roughly 20–40" from the wiki side. The client tightens it: there are 43 non-Resurrection-Signet Pre-Searing-reachable skills (see Skills below), Resurrection Signet is not quest-taught, and Halbrik only *sells* skills that are also obtainable by quest — so the count cannot exceed 43 and is plausibly in the high 30s. This is a client-anchored bound over a wiki guess, and it is the better number.

### Named side quests (sample, not census)

| Quest | Giver | Zone | Objective | Verbs |
|---|---|---|---|---|
| Unsettling Rumors | Devona | Lakeside County → Ashford Abbey | Speak to Meerak the Scribe, report to Armin Saberlin | dialogue, area-trigger |
| Charr at the Gate | Prince Rurik | Ascalon City (min level 2) | Follow Rurik's party, kill 4 Charr, return | escort, kill-count |
| Little Thom's Big Cloak | Alison the Tanner | Wizard's Folly / Regent Valley | Kill bears for pelts, return | kill-count, item-collect |
| The True King | Duke Barradin | The Barradin Estate | Deliver a message to Lord Darrin in Fort Ranik | dialogue, area-trigger |
| Warrior's Challenge | Duke Barradin | Green Hills County | Defeat Agnar the Foot (interrupting his Rage matters) | kill-count |
| The Wayward Wizard | Sandre Elek | → Foible's Fair | Directed to Foible's Fair | dialogue, area-trigger |

### Vanguard quests

WIKI: at least one for every Pre-Searing explorable **except Lakeside County** — 5 of the 6 classic explorables. Given by Lieutenant Samantha Langmar, repeatable, 1000 XP, and the active variant **rotates on a fixed 16:01 UTC daily schedule**. Purely kill-count content with a server-side reset clock, categorically distinct from the story quests.

### The six verbs

Every quest that could be pinned down — tutorial, profession, side, Vanguard — reduces to six server behaviours:

| Verb | Server behaviour | Example |
|---|---|---|
| **dialogue** | branch and track conversation state; gate an NPC's next line on quest-log state | every `<Profession> Test`; A Second Profession's branch selection |
| **kill-count** | count N kills of a type or a named boss, notify on completion | Warrior's Challenge; Charr at the Gate; every Vanguard quest |
| **item-collect** | count N of an item in inventory, or a drop-triggered counter | Little Thom's Big Cloak |
| **area-trigger** | detect map/region entry and advance quest state | Unsettling Rumors; entering the Academy trial |
| **escort** | spawn and path an NPC ally through hostile content, with a fail state if it dies | Charr at the Gate |
| **timer** | a server-side schedule independent of any one player's state | Vanguard dailies, fixed-UTC rotation |

**No quest examined needed a seventh verb** — no puzzle, no timed defence, no DPS race. That is consistent with a tutorial region, but the searches covered maybe 15–20 of ≤70 quests, so it is a partial-coverage claim, not a closed one. Marked EXACT over what was examined, APPROX over the whole catalog.

---

## Skills

**This is the best-evidenced section in the manifest**, and the only one where a WIKI claim was upgraded by CLIENT corroboration rather than merely cross-checked.

WIKI (*Guide to Ascalon (pre-Searing)*): "There are 6 to 8 skills available per profession, in addition to the Resurrection Signet." That roster was resolved name-by-name against our own client via `toolkit/clientscan/skilltable.py` + `textrec.py`, decoding `Gw.dat`'s own text records rather than trusting the wiki's spelling. **44 of 44 names resolved to exactly one client row each — zero collisions, zero misses.**

| Profession | Count | Skills (client id) |
|---|---|---|
| Warrior | **7** | Healing Signet (1), Cyclone Axe (330), Hammer Bash (331), Executioner's Strike (336), Frenzy (346), Sever Artery (382), Gash (384) |
| Ranger | **8** | Power Shot (394), Dual Shot (396), Point Blank Shot (407), Charm Animal (411), Ignite Arrows (431), Read the Wind (432), Comfort Animal (436), Troll Unguent (446) |
| Monk | **8** | Symbol of Wrath (247), Retribution (248), Banish (252), Orison of Healing (281), Healing Breeze (288), Bane Signet (296), Shielding Hands (299), Reversal of Fortune (307) |
| Necromancer | **8** | Animate Bone Horror (83), Soul Barbs (100), Deathly Swarm (105), Life Siphon (109), Blood Renewal (115), Faintheartedness (135), Vampiric Gaze (153), Vampiric Touch (156) |
| Mesmer | **6** | Empathy (26), Shatter Delusions (27), Backfire (28), Conjure Phantasm (31), Ether Feast (40), Imagined Burden (76) |
| Elementalist | **6** | Aura of Restoration (180), Flare (194), Fire Storm (197), Glyph of Lesser Energy (200), Blinding Flash (220), Lightning Javelin (230) |
| Any | **1** | Resurrection Signet (2) |
| **Total** | **44** | |

A 6/6/7/8/8/8 split — WIKI's "6 to 8 per profession" exactly, no rounding. The count is not a range: it is **44 named, id-tagged skills**.

### Skill types — a CLIENT taxonomy, not an invented one

The client's 164-byte skill record carries a `type_code` field at `+0x0C`, a raw enum ArenaNet never named in any source we hold. It was decoded by cross-referencing skills whose WIKI-stated type was independently confirmed against their CLIENT `type_code`, then applied across the full 1,333-skill player corpus.

| `type_code` | Skill type | Pre-Searing exemplar (id) | Pre-Searing / full corpus |
|---|---|---|---|
| 3 | Stance | Frenzy (346) | **1** / 76 |
| 4 | Hex Spell | Backfire (28) | **7** / 151 |
| 5 | Spell | Flare (194) | **12** / 287 |
| 6 | Enchantment Spell | Reversal of Fortune (307) | **6** / 227 |
| 7 | Signet | Healing Signet (1) | **3** / 66 |
| 10 | "Skill" (non-spell catch-all) | Charm Animal (411) | **4** / 55 |
| 12 | Glyph | Glyph of Lesser Energy (200) | **1** / 10 |
| 14 | Attack | Sever Artery (382) | **8** / 199 |
| 19 | Preparation | Ignite Arrows (431) | **2** / 14 |

Sums to 44. *(One research pass published 6/11/8/9 for codes 4/5/6/14, summing to 45 for a 44-skill roster; the reconciliation re-counted directly from that pass's own artifact `vault/research/2026-08-06/presearing-skill-rows.json` and the table above is the corrected distribution. A transcription slip, not a method failure — every other figure in that pass reproduced exactly.)*

**The full player corpus spans 21 distinct `type_code` values. Pre-Searing's 44 reach exactly 9 of them.** The other 12 (9, 11, 15, 16, 20, 21, 22, 24, 25, 26, 27, 28) are attested in the client and semantically UNKNOWN, with one exception: **`type_code 15` is Shout**, confirmed via skill id 316 "To the Limit!" — which WIKI confirms is a *post*-Searing reward, consistent with zero Shouts in the 44. Naming the remaining 11 is a bounded follow-up using the same Rosetta-stone method, and it does not change any scoping conclusion here since none of them appear in Pre-Searing.

### Effect-mechanism coverage

**The ~24-family list below is RECONSTRUCTION.** It was assembled from the research brief plus what surfaced during verification. It is a reasonable taxonomy and it is not sourced from anywhere. Any criterion that adopts it must say so.

| Family | In Pre-Searing? | Exemplar |
|---|---|---|
| Direct damage, spell | yes | Flare (194) |
| Direct damage, weapon attack | yes | Sever Artery (382), Gash (384) |
| AoE damage | yes | Symbol of Wrath (247), Fire Storm (197) |
| Damage over time / degeneration | yes | Faintheartedness (135), Life Siphon (109) |
| Conditions | **partial** — Bleeding, Deep Wound, Blindness only | Sever Artery, Gash, Blinding Flash (220) |
| Hexes | yes (7) | Backfire (28), Empathy (26) |
| Enchantments | yes (6) | Reversal of Fortune (307) |
| Healing | yes | Orison of Healing (281), Troll Unguent (446) |
| Life steal | yes | Vampiric Gaze (153), Vampiric Touch (156) |
| Signets | yes (3) | Healing Signet (1), Bane Signet (296) |
| Resurrection | yes | Resurrection Signet (2) |
| Minion summon | yes | Animate Bone Horror (83) |
| Pet management | yes | Charm Animal (411), Comfort Animal (436) |
| Touch-range targeting | yes | Vampiric Touch (156) — CLIENT `FLAG_TOUCH_RANGE` |
| Knockdown | yes | Hammer Bash (331) |
| Hex removal with a secondary effect | yes | Shatter Delusions (27) |
| Stances | **thin — exactly 1** | Frenzy (346) |
| Preparations | **thin — exactly 2** | Ignite Arrows (431), Read the Wind (432) |
| Energy management | **thin — exactly 1** | Glyph of Lesser Energy (200) |
| Armor modification | **thin — exactly 1, a self-debuff** | Healing Signet (1), −40 armor while using |
| Movement modification | **thin — exactly 1, enemy-only slow** | Imagined Burden (76) |
| Shouts | **no** | nearest miss "To the Limit!", post-Searing |
| Interrupts | **no** | Bane Signet checked and ruled out — damage + conditional knockdown |
| Wells / Spirits / Traps / Wards | **no** | no Ritualist, and core Ranger traps are absent from the 44 |
| Block / attack-avoidance | **no** | Shielding Hands is flat damage reduction, a different mechanic |

**16–17 of ~24 exercised; 5 cleanly absent** (Shout, Interrupt, Well/Spirit/Trap/Ward, Block, Ritual); **5 with exactly one exemplar** (Stance, Glyph, energy-mgmt, armor-mod, movement-mod).

This sharpens the review panel's caveat from the other side. The panel argued from the *monster* roster that Pre-Searing is a thin R4b oracle. The player-side result is stronger: **even the player's own reachable kit never touches Shout, Interrupt, Well/Spirit/Trap/Ward or attack-avoidance.** Engine code for those families would ship with zero in-scope acceptance skills to test it against, regardless of monster behaviour. An engine that only ever proves itself against Pre-Searing ships having never exercised roughly a fifth of what a GW1 skill engine must do.

### One trap for future readers

`studies/skills/FINDINGS.md`'s client experiments used skill ids 316–323 ("To the Limit!", Battle Rage, Defy Pain, Rush, Hamstring, Power Attack). **None of those is in the Pre-Searing 44.** They were picked as a convenient consecutive id run for validating opcode and rendering behaviour, not as content claims. "Skills our tooling has already touched" and "skills R4b should test" are two different sets, and this manifest is the first document to name the second one by id.

---

## Items and NPCs

### Items

**PLAN.md §1.7 names drop tables as one of the four genuinely server-only things, and nothing below is a drop table.** This is an inventory of what *kind* of thing drops, sourced entirely from twenty years of player observation on WIKI. The hole it measures is the gap between "these categories exist" and "we have one probability, one quantity, for any of them" — which is total.

- **No Armorer exists in Pre-Searing.** WIKI (*Guide to Ascalon (pre-Searing)*): "There is no Armorer. Collector armor may be acquired." Armor is collector-trade only, never crafted.
- **One Weaponsmith, deliberately weak.** The real weapon upgrades are quest Bonus rewards; all martial types are obtainable at max stats that way, "with the notable exception of axe."
- **Crafting materials barely function as a category.** Skeletons are the only foe that directly drops materials (Bone, Dust). Everything else comes from salvaging, and WIKI states outright there is "no actual use for them in pre-Searing" — no crafting NPC exists to spend them at.
- **Containers and salvage kits are drop-only and rare.** Merchants sell neither. The only forms in-region are the green 10-slot **Charr Bag** and the gold 5-use **Charr Salvage Kit**, which "rarely drop from the Charr bosses in The Northlands."
- **Nicholas Sandford** (Regent Valley, secret garden) trades 5 of a daily-rotating trophy for 1 Gift of the Huntsman, cap 5/account/day, rotating at 07:00 UTC. The three trophies: **Icy Lodestone, Charr Carving, Red Iris Flower**. A second server-side daily clock, distinct from the Vanguard 16:01 UTC one.

| Trophy | Traded to | For | Zone |
|---|---|---|---|
| Skeletal Limb ×3 | general collector | — | The Catacombs |
| Enchanted Lodestone ×3 | general collector | — | Wizard's Folly |
| Icy Lodestone ×3 | Savich | hand armor | Wizard's Folly |
| Unnatural Seed ×5 | Hatcher | chest armor | Fort Ranik |
| Spider Leg ×3 | Varis | leg armor | Fort Ranik |
| Red Iris Flower ×50 | Professor Yakkington | headgear | Regent Valley |
| Gargoyle Skull ×5 | Karleen | foot armor | The Catacombs |
| Baked Husk, Grawl Necklace | armor collector(s) | — | Lakeside County area |

Reconstructed across several search passes rather than read from one page: **directionally right, possibly incomplete**.

**Named drop/trophy/material items: 10–12, FLOOR.** They imply at least five distinct monster families as drop sources (skeletons, ice-associated creatures, spiders, Charr, Grawl). **UNKNOWN and structurally unknowable from the client**: every drop rate, gold-drop rates, whether ordinary non-boss non-skeleton monsters drop anything at all, and whether dye drops here.

### NPCs

**Named or role-confirmed service NPCs: 13.**

| NPC | Role | Zone |
|---|---|---|
| Halbrik | the only skill trainer in Pre-Searing | UNKNOWN zone |
| Nicholas Sandford | rotating trophy collector | Regent Valley, secret garden |
| Professor Yakkington | armor collector (head) | Regent Valley, secret garden |
| Karleen | armor collector (feet) | The Catacombs |
| Gwynn | collector, role unconfirmed | The Catacombs |
| Savich | armor collector (hands) | Wizard's Folly |
| Mindle | collector, role unconfirmed | Wizard's Folly |
| Hatcher | armor collector (chest) | Fort Ranik |
| Varis | armor collector (legs) | Fort Ranik |
| Warmaster / Sir Tydus | quest-giving officer | Ascalon City |
| Lieutenant Samantha Langmar | Vanguard daily officer | Ascalon City |
| Guild Registrar | forms guilds; no hall access from the mainland | Ascalon City |
| Ascalon Guard | recurring generic town guard | Ascalon City, likely others |

Plus an unnamed Merchant and an unnamed Weaponsmith, neither of which has an individual wiki page — **floor of 15 template rows**. GWW category counts (reported by the search backend, not verified by opening a page) suggest `Category:Regent Valley (pre-Searing) NPCs` alone holds ~40 pages and `Category:Ascalon City (pre-Searing) NPCs` ~23, which is the strongest sign that the wiki's NPC categories fold one-off named quest characters in with repeatable service archetypes. Since nothing in Guild Wars shares a template across differently-named unique characters — the definition index is a raw array index on the client, and creating an agent whose definition was never sent takes the client down on `index < m_count` (OURS, `content/npcs.toml`, OBSERVED) — **the plausible ceiling is 60–100 template rows.**

**On our Hatcher.** One pass noticed that WIKI's Fort Ranik armor collector is also named Hatcher and proposed that OURS `[npc.hatcher]` may be the genuine article rather than a placeholder. **Do not adopt this.** What we OBSERVED is that four EncString words rendered as "Hatcher [Collector]" — that proves the string ids, not the location. Its provenance is gw-preservation, which pins clientVersion 37600 and whose identifier `hatcher_collector` carries no region. Comparing our row to a wiki page is offline agreement between two things neither of which observed our client standing in Fort Ranik, which is exactly the failure mode CLAUDE.md names. **Keep the row's own label** — "a borrowed Ascalon collector standing in for a monster. It is not a Pre-Searing enemy." What would settle it is a live Pre-Searing capture showing this `file_id`, which is the capture campaign anyway.

**Henchmen: 0.** WIKI (*Ascalon (pre-Searing)*): "There are no henchmen in any of the outposts in pre-Searing Ascalon." Sole exception: the Ascalon Academy exit mission auto-fills an incomplete party with up to three level-3 henchmen. **The henchmen surface for v1's declared finish line is effectively zero** — a real, sourced simplification against what "a finished region" might imply.

---

## Services

| Service | Present? | Note | Source |
|---|---|---|---|
| Merchant buy/sell | **yes, limited** | no bags or containers, no Expert Salvage Kits | WIKI |
| Weaponsmith buy | **yes, limited** | "unremarkable"; real upgrades are quest Bonus rewards | WIKI |
| Collector trade — general trophies | **yes** | ≥3 general collectors | WIKI |
| Collector trade — armor | **yes** | ≥5 named armor collectors, roughly one per body slot | WIKI |
| Skill trainer | **yes, heavily restricted** | one NPC (Halbrik), level 10+, only teaches skills also quest-obtainable | WIKI |
| Storage (Xunlai) | **no** | neither agents nor chests appear in this part of Prophecies | WIKI |
| Armor crafting | **no** | "There is no Armorer" | WIKI |
| Dye trading | **no NPC** | player-to-player only | WIKI |
| Guild registration | **yes**, but no hall claiming from the mainland | Guild Registrar, Ascalon City | WIKI |
| Henchmen | **no**, except the exit-mission auto-fill | | WIKI |

**8 services checked, 4 present in some form.** CLIENT corroborates independently: zero `type 13` (full-service town) rows exist on `continent == 1`, so the client's own area typing says the region's hub is outpost-class. Two evidence classes, one conclusion.

**Net reading for the v1 question.** A genuinely playable Pre-Searing needs far fewer working services than the full game — no storage, no armor crafting, no dye trading, no henchmen UI. What it needs, and OURS has none of, is: a merchant buy/sell exchange, a collector-trade exchange in both flavours, and one restricted skill trainer.

---

## What is server-only, and therefore uncapturable from the client

Sorted against PLAN.md §1.7's four: **absolute monster HP/energy/armor · spawn placement · drop tables · AI decision logic.**

### Fully client-extractable — no capture, tooling exists today

| Manifest table | Route | Status |
|---|---|---|
| Zones, ids, types, party sizes (#1–7) | `toolkit/clientscan/areatable.py` | **done**, 19/19 rows |
| Walkable geometry, portals-as-planes | `toolkit/mapdata/` | done for row 7982 |
| The 44 skills: id, profession, attribute, energy, adrenaline, activation, aftercast, recharge, `type_code`, flags (#21–25) | `toolkit/clientscan/skilltable.py` | **done**, dumped to vault |
| Skill rank scaling (`scale0`/`scale15`, `duration0`/`duration15`) | same record, §1.7's own strongest example | not pulled, no blocker |
| NPC and item names as EncString word sets | `toolkit/clientscan/textrec.py` | can be copied, cannot be invented |

**Roughly 40% of this manifest by table count is already extracted or one tool-run away.** §1.7's thesis holds up well against a full content enumeration.

### WIKI-sufficient — not server-only, no capture needed

Quest givers, objectives, chains and required-vs-optional (#16–19); collector trade ratios, which are exact on the wiki; monster **levels**, which players see; monster **skill lists** as opposed to usage (#11); which services exist (#34). One lead nobody pursued: **quest text ships in `Gw.dat`** (Tyria-Extractor claims quest extraction), which would convert the largest WIKI-dependent table in this manifest into a CLIENT table dump. Worth one probe.

### Capture-only — the campaign this manifest sizes

| §1.7 item | Tables it gates | Size |
|---|---|---|
| **Spawn placement** | monster roster per zone (#8, #10) | **The largest hole, and N is not merely unknown but unstatable.** The manifest can enumerate 35–40 *types*; it cannot say how many bodies stand in Lakeside County. **R4c must be graded on types present, not spawn instances.** |
| **Drop tables** | items (#31–33) | **Smaller here than the general case.** No armorer, no crafting NPC, materials inert in-region. What is needed is ~10–12 trophies wired to collectors plus two Northlands boss drops — not a loot economy. |
| **AI decision logic** | monster behaviour, aggro, the ≥9 skill bars *in use* (#11, #15) | **Unbounded and uncountable.** WIKI gives the bar; nothing gives the policy. The one table where this manifest cannot produce an N at all, and R4c should not pretend otherwise. |
| **Absolute monster HP/energy/armor** | every monster row | Bounded and small — three numbers × 35–40 types. `content/world.toml`'s `max_health = 100` placeholder already says so in its own note. |

### Neither — must be invented, then verified against capture

- **Skill effect resolution.** The client has the numbers and the description string; the *semantics* of Faintheartedness are in neither client nor capture as data. A capture gives an **oracle** (what happened when it resolved), not a specification. **This is R4b's actual work, and §1.7 does not name it.**
- **Quest state machines.** The six verbs are ours to build.
- **Portal destination topology.** Which exit leads to which map id is a server decision, is not obviously in `AreaInfo`, and is not among §1.7's four. **Candidate fifth server-only item** — flagged rather than asserted.

### One correction to §1.7 itself

§1.7 asserts "NPC identity [is] likewise client-side." `studies/enemy/PLAN.md` §7.1 **CONTESTS this**: no complete static NPC-definition table has been confirmed in either archive or executable, and the extractor that has one recovers definitions by sniffing the live service. So monster identity is nominally client-side and **practically capture-gated today**. It belongs with the four, or §1.7 needs a caveat. This bears directly on the 15–100 NPC template rows — all of them blocked on the same thing.

### Sequencing consequence

**R0b blocks roughly one third of R4c — the monster tables — and none of R4b.** Zones, quests, NPC identities-as-names, services and all 44 skills are reachable without a single ArenaNet byte. R4b's `n of 9 families` is startable today. R4c should be split into a capture-free half (19 zones, ≤70 quests, ≥15 NPCs, 4 services) and a capture-gated half (spawn placement, drop tables, AI) that stays honestly at zero until R0b exists.

---

## The gap against what we have today

**OURS, read 2026-08-06.** `content/maps.toml` holds **8 map rows — 148, 146, 449, 194, 55, 474, 558, 90 — of which 2 are Pre-Searing** (146, 148). One research pass claimed the file covers "145, 146, 147, 148, 164"; ids 145, 147 and 164 **are not in it**. The task briefs' own framing ("8 maps, 4 in the Pre-Searing region") is also wrong. Every delta below is computed against **2**.

`content/npcs.toml` = 1 row (`hatcher`, self-labelled borrowed). `content/items.toml` = 1 row (`starter_hammer`, self-labelled NOT VERIFIED, from OpenTyria's table, no capture of ours has ever carried those bytes). `content/world.toml` = 1 spawn (`test_enemy`, `source = "invented"`, 300 units east of the player, with its own note saying there is no evidence anything stands there). No quest table and no quest logic anywhere in `toolkit/`. No merchant, collector or trainer code — `collector` appears twice in `toolkit/`, both times in comments about the Hatcher body.

| Table | Have | Need | **Delta** | Note |
|---|---|---|---|---|
| Map rows | **2** | 19 | **17** | 148's spawn is walkability-verified; 146's is Ascalon City's borrowed coordinate. **Correct arrival points: 1 of 19, delta 18.** |
| Maps with a resolved `Gw.dat` file id | 2 | 19 | **17** | 9 of 19 have an id from some source; 10 of 19 have none anywhere, including all 4 new rows |
| NPC templates | **1** | ≥15, plausibly 60–100 | **≥14, up to 99** | and the 1 is not established as Pre-Searing content — arguably delta 15 |
| Items | **1** | ≥10–12 named | **≥9–11** | plus 0 of N drop-table rows; N unstatable pre-capture |
| Spawns | **1** | UNKNOWN | **undefined** | the manifest cannot state N; R4c must count types, not instances |
| Monster types | **0** | 35–40 | **35–40** | no hostile definition exists anywhere in the repo; every published NPC definition we hold is a townsperson |
| Monster types with a working skill bar | **0** | ≥9 | **≥9** | |
| Quests | **0** | 2 mandatory / ≤70 total | **2** to **70** | |
| Quest verbs implemented | **0** | 6 | **6** | |
| Skills that resolve an effect | **0 of 44** | 44 | **44** | 8 skills draw on the bar with correct tooltips; none resolves |
| Skill type-code families resolving | **0 of 9** | 9 | **9** | **this is R4b's `n of N`. Today n = 0.** |
| Services | **0 of 4** | 4 | **4** | merchant, weaponsmith, collector trade ×2 flavours, restricted trainer |
| Agent table | **does not exist** | 1 | 1 | `studies/enemy/PLAN.md` §7.2; every later rung assumes it, and the player agent id is currently a module constant |

**Headline delta: 17 maps, ≥14 NPC templates, ≥9 items, 35–40 monster types, 2–70 quests, 6 verbs, 44 skills, 9 skill families, 4 services, 1 agent table.**

R4a's own status is honestly half, and PLAN.md already says so: the enemy dies convincingly and does not swing back.

---

## Proposed acceptance criteria for R4b and R4c

**These are proposals for the owner, not adopted criteria.** They are written to be countable against the tables above and to fail loudly rather than be argued about.

### R4b — the skill substrate

> **R4b is met when, for each of the 9 `type_code` families Pre-Searing's 44 skills reach, at least one named skill id resolves its effect correctly against the client. Stated as *n of 9*. Today n = 0.**
>
> The nine, each with the exemplar this manifest proposes:
> Stance (3) — Frenzy 346 · Hex Spell (4) — Faintheartedness 135 · Spell (5) — Flare 194 · Enchantment (6) — Reversal of Fortune 307 · Signet (7) — Healing Signet 1 · Skill (10) — Charm Animal 411 · Glyph (12) — Glyph of Lesser Energy 200 · Attack (14) — Sever Artery 382 · Preparation (19) — Ignite Arrows 431.
>
> "Resolves correctly" means the client's own state agrees with the server's after the cast — health, energy, condition and enchantment display, recharge — not that our server agrees with itself.
>
> **Secondary, and explicitly weaker:** effect-mechanism coverage, 16–17 of ~24. Report it as narrative, never as the pass/fail number, because the family list is RECONSTRUCTION and nobody sourced it.
>
> **Carried in the criterion, not hidden:** 5 real mechanical families (Shout, Interrupt, Well/Spirit/Trap/Ward, Block, Ritual) have **no** Pre-Searing exemplar. A green R4b does not mean the skill engine is general. If generality matters, that has to be a separate rung with a post-Searing exemplar per absent family, and it is out of scope for the declared v1 finish line.

Why 9 and not 21: the 12 unreached codes have no Pre-Searing content to test against. Grading against 21 would be grading v1 against non-v1 content.

### R4c — AI, spawns and quests

Split it. Half is startable today; half is blocked on a capture that does not exist. Reporting them as one number hides which.

> **R4c-1 (capture-free) is met when, stated as *n of N* per row:**
> - **19 of 19** map rows exist in `content/maps.toml` with a resolved `Gw.dat` file id and an arrival point that scores exactly 1 in the spawn-in-trapezoid test. *(Today: 2 rows, 1 verified arrival point.)*
> - **≥15 of ≥15** service NPC templates exist in `content/npcs.toml` with real EncString words. *(Today: 1, unverified as Pre-Searing.)*
> - **2 of 2** mandatory quests are completable end to end — primary Profession Test, then one A Second Profession branch. *(Today: 0. This is the smallest honest definition of "playable solo end to end.")*
> - **6 of 6** quest verbs are implemented as reusable server behaviours. *(Today: 0.)*
> - **4 of 4** services function — merchant, weaponsmith, collector trade, restricted trainer. *(Today: 0.)*
>
> **R4c-2 (capture-gated) is met when, stated as *n of N*:**
> - **35–40** hostile monster **types** exist as content rows with real definitions, HP/energy/armor from capture, and a skill bar. **Graded on types present, never on spawn instances** — spawn counts are unstatable from any source available to this project.
> - **≥9 of ≥9** monster types with a documented skill bar visibly use it in combat.
> - Drop tables exist for the 10–12 named trophies. **Drop *rates* are graded as present/absent, not as accuracy**, until a capture provides an oracle.
>
> **R4c-2 stays at 0 and is reported as blocked until R0b exists.** It is not a failure of R4c; it is a dependency, and the ladder should show it as one.

> **"Plays like the recording" returns as a fidelity check only once R0b exists.** Until then the count is the criterion, and the count is honest about which half of it a capture would move.

### One scope decision the owner has to make, which no data can

Does "Pre-Searing playable solo end to end" include resolving the Ascalon Academy mission cluster (143/149/150/151) and handing the player into post-Searing content, or does it stop at "the mission is completable" with no landing zone on the other side? CLIENT and WIKI cannot answer this. It matters because that cluster is simultaneously the last mile of the finish line, the part of the zone table with zero file ids, and the part where the relationship between its four rows is least understood.

---

## What this manifest does not know

Ranked by how much scope each moves.

1. ✅ **SETTLED 2026-08-11 — they are gated. See Revision §1.** *Reforged Mode* was read directly: it is an opt-in experimental **Beta** (alpha 2025-12-18, beta 2026-05-27), and *A Bastion In the North* is what unlocks Piken Square and the Forsaken Tunnels. The "only an opt-in XP/gold buff, zones are ordinary content" reading is REFUTED. **4 of 19 zones are opt-in content**, so a normal-mode v1 is a 15-row region — which turns this from an unknown into the owner's scope decision below. Still unread: `Feedback:Game updates/20260401`.
2. **File ids for 10 of 19 map rows** — 143, 149, 150, 151, 160, 161, 779, 780, 877, 878. **Settled by:** for the six legacy rows, a further bit-31 scan of the archive's 171,023-entry file-id table for candidates landing on unclaimed `flags==259` rows — the same method `studies/mapdata/FORMAT.md` used for the original two. For the four new rows, no mirror we hold predates them, so the only route is watching a live client load them (owner go-ahead required per CLAUDE.md).
3. 🔶 **PARTLY CLOSED 2026-08-11 — 7 pages/categories re-read, see the Revision section.** The Chrome MCP is *still* down, but the scripted route unexpectedly worked (7 requests, 0 blocks, against a documented allowance of ~5). That pass settled item 1, turned #16 into an EXACT roster, corrected #14, moved #13 to UNVERIFIED after catching a misattributed citation, and found §Monsters' Northlands roster contaminated with Reforged-only content. **Do not read the scripted route's success as the block lifting** — `access.md` measures a refilling bucket, and one good session is what that looks like. Still to re-read, unchanged in priority — skill bars for the Catacombs' permanent-resident undead (Restless Corpse, Raging Cadaver, Crypt Fiend, Deadly Crypt Spider, Diseased Devourer, Snapping Devourer, Tomb Nightmare, Shatter Gargoyle) and for Skullreaver and Ice Elemental (pre-Searing); the fourth Searing-altar Charr boss's name; the bestiary category pages for Wizard's Folly and The Northlands; any creature at all in Forsaken Tunnels; and the raw member list of `Category:Ascalon (pre-Searing) quests` so ≤70 becomes a real number.
4. **Whether `Gw.dat` carries quest text extractably.** If it does, the largest WIKI-dependent table in this manifest becomes a CLIENT table dump. **Settled by:** one probe against the archive, following Tyria-Extractor's claim.
5. **Whether Green Hills County (160) and Wizard's Folly (161) have their own archive files or live as unwalked planes inside row 7982.** Row 7982 already carries an unusually high 58 planes for one file. **Settled by:** the spawn-in-trapezoid check `content/maps.toml` already ran for Lakeside — testable today, blocked only on finding a plausible spawn coordinate for either zone.
6. **Whether Regent Valley (162) and Fort Ranik (166) genuinely share `0x1BB1D`, or that is upstream copy-paste.** `studies/mapdata/FORMAT.md` flags 101 file ids game-wide claimed by more than one map id as an open class; this is one instance. **Settled by:** the same spawn-in-trapezoid check against both zones' known spawns.
7. **Which of rows 149/150/151 is the PvP battle, which is the auto-skip case, and which is the escort mission proper.** WIKI describes a PvP stage that auto-loses if no other player is present, which fits two arena rows plus one mission row — but the client table alone cannot say which id is which.
8. **Whether our `npc.hatcher` is the real Fort Ranik collector or a same-named coincidence.** UNKNOWN, and the obvious test (compare our row to the wiki page) cannot settle it — that is offline agreement between two things neither of which observed our client in Fort Ranik. **Settled by:** a live Pre-Searing capture showing this `file_id`, which is the capture campaign anyway.
9. **Semantic names for 11 of the 21 client `type_code` values** (9, 11, 16, 20, 21, 22, 24, 25, 26, 27, 28). None appears in Pre-Searing, so this changes no scoping conclusion — but naming them completes the engine's type-dispatch table. **Settled by:** the same Rosetta-stone method used here, two or three known-name skills per code.
10. **Whether any Pre-Searing quest needs a seventh verb.** The six cover everything examined, but that was ~15–20 quests of ≤70. Absence of evidence.
11. **Drop rates, gold drops, and whether ordinary non-boss non-skeleton monsters drop anything at all.** Unknowable from any source available to this project, per PLAN.md §1.7. **Settled by:** capture, which is §1.7's stated position already.
12. **The `campaign` field's meaning on skill rows.** It takes both 0 and 1 across the 44 with no visible pattern tied to reachability. Not pursued, flagged rather than guessed at.