# What we actually know about skills

Ten reading tracks over eleven prior-art mirrors, our own capture vault and our own
schema, each then adversarially re-verified by a second reader who re-opened every
cited file and re-ran every generalising grep. This document records only what
survived verification, and labels everything.

No code was written and no client was launched for this pass. It is a study.

## Labels used throughout

| Label | Meaning |
|---|---|
| **OBSERVED** | We saw it ourselves, against our own client, in our own logs. |
| **CLIENT-DATA** | Read out of the shipped client — its PE tables, its `Gw.dat`, or its live memory layout — by a third-party tool whose code we have read. This is the strongest class of evidence in this pass, and it is still somebody else's reading. |
| **UPSTREAM** | A reimplementation's code says this, and a verifier confirmed the line. These are reconstructions; none is a fact about ArenaNet's server. |
| **RECONSTRUCTION** | The source signals it is guessing — offset-named field, placeholder magic, commented-out call, or the author saying so. |
| **CONTESTED** | Sources disagree, and this document does not pick a winner. |
| **UNVERIFIED** | Claimed by a track, and the verifier could not confirm it. Do not build on this. |
| **NOT FOUND** | We looked, and there is no answer in the sources we have. |
| **WIKI** | The official Guild Wars Wiki (`wiki.guildwars.com`) says this — twenty years of players documenting observed retail behaviour, cited by page and section. Its strength is **not uniform**: strong for player-visible values (a skill's displayed cost, recharge, description), because mass observation of the retail client beats any single reimplementation's reading; weak for internals (byte layouts, wire formats), which players inferred from outside. The test is *could a player have seen this from the game window?* It shares no author, code or ancestry with the §6 cluster, so wiki + a code lineage agreeing is real corroboration. |

**The single most important thing this pass learned about its own sources** is in
§6, and it is bad news: the "ldufr" and "GWCA" lineages, which the movement pass
treated as independent, are **not independent**. They share an author. Nine
separate repositories in our vault propagate one misspelling. Read §6 before
treating any two sources here as corroboration.

---

## The answer in one page

**The client already knows everything about every skill, and the server is not
told any of it.** A skill's name, description, icon, attribute, profession,
energy cost, cast time, aftercast, recharge, adrenaline, AoE range, rank-0/rank-15
scaling and animation ids all live in a fixed-width table compiled into the
client, indexed by numeric skill id. Nothing in any protocol message in any
direction carries a single one of those values. Every skill-related message in
the catalogue refers to a skill by a bare number.

This is the load-bearing finding of the pass. It is supported by four sources
using three different methods, two of which are outside the authorship cluster:

- **Fournux/Tyria-Extractor** parses the client PE and reads a `0xa4`-byte
  (164-byte) record per skill, addressed as `table_base + skill_id * 0xa4`
  (`doc/SKILL_EXTRACTION.md:23-30`). Its skill extraction command takes
  **only a `Gw.dat` path** — no packet log, no injected sniffer, no network
  (`src/cli.rs:41-44`). A tool that can produce the complete skill dataset from
  a disk file alone is a proof that no server tells the client any of it.
- **GWCA** declares the same record as a C++ struct, `sizeof == 0xa4`, and gets
  it by scanning the client binary
  (`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/GameEntities/Skill.h:14-87`).
- **The client's own assertion string**, recovered by GWCA's scanner, is
  `index < arrsize(s_skill)` (`gwdevhub__GWToolboxpp/tools/gw-update/anchor-index.json:1519-1520`).
  That is ArenaNet's text, naming a file-scope array `s_skill` and bounds-checking
  an index against it. It is the closest thing to a primary source in this pass.
- **GWLP-R**, an unrelated 2013 server lineage, designed a `skills` database table
  whose only columns are `ID`, `Name`, `Attribute` — no cost, no cast time, no
  recharge, no icon — and shipped it with **zero rows**
  (`database/src/main/sql/default_data.sql:86-102` region). A server project that
  got as far as a JPA entity and two join tables never modelled a single skill
  constant, because there was never any reason to.

Two independent measurements of how many skills exist land four apart:
Tyria-Extractor counts **1,333** base rows in a 2026-07-26 `Gw.exe`
(`GWDAT_INVESTIGATION_JOURNAL.md:128`); the Guild Wars wiki totals **1,329**
player skills (`vault/research/2026-08-04/skill-substrate.md:21-36`). Two
unrelated methods, 0.3% apart. That is the best corroboration anywhere in this
document, and it is better than anything the cluster's internal agreement can
offer.

**What this means for the two questions that actually matter:**

**Getting a real skill onto the bar is nearly free.** One message —
`GAME_SMSG_SKILLBAR_UPDATE`, opcode 218 / `0x00DA` — carries eight `uint32` skill
ids, and the client draws the icon, name, tooltip, cost and recharge from its own
table. We already send this message; we send eight zeros. Changing a zero to
`1954` is the whole of Q3. See §3 for the exact caveats, of which the real one is
that our opcode numbering has never been validated against our own client.

**Creating a genuinely new skill is a client-patching project, not a server
project.** The id *is* the row index into a compiled table whose length is stored
in the table itself. An id the client has never heard of has no row, no name
string, no icon file and no animation. Re-skinning an existing id with new
server-side behaviour, by contrast, requires **no client change at all** — and is
the only one of the two that is available to us today. See §5.

**Third, and unwelcome:** no prior server project in our vault has ever
implemented skill *execution*. Not OpenTyria, not GWLP-R, not the Go server. All
three send a skill bar at map load and stop. There is no reference implementation
of casting anywhere in our sources, and the client-to-server half of the protocol
is materially worse evidenced than the server-to-client half. See §4.

---

## 1. Where skill data lives

### The short version

| Component | Lives in | Addressed by | Label |
|---|---|---|---|
| Stats (costs, timings, attribute, profession, flags, scaling) | A fixed-width array **inside the client PE** | `skill_id` as the zero-based row index | CLIENT-DATA |
| Name, concise description, full description | **`Gw.dat` text resources** | three `uint32` **string ids** stored in the PE row | CLIENT-DATA |
| Icons (standard and high-res) | **`Gw.dat` textures** (ATEX/ATTX) | two-to-three `uint32` **dat file numbers** stored in the PE row | CLIENT-DATA |
| Cast animations | referenced by six `uint32` ids in the PE row | id → asset resolution **NOT FOUND** | CONTESTED (see below) |
| Which skill is in which bar slot | **the server** | `SKILLBAR_UPDATE` | UPSTREAM |
| Which skills are unlocked | **the server** | unlock bitmaps | UPSTREAM |
| Live recharge / cast / interrupt events | **the server**, by skill id | lifecycle messages | UPSTREAM |

The dividing line is clean and it is worth stating as a rule: **the server owns
which and when; the client owns what.**

### The skill record

164 bytes, `0xa4`. Two sources describe it and they were written independently.
Here is the 2026-era GWCA struct in full, because every offset in it is something
a private server does *not* get to choose
(`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/GameEntities/Skill.h:14-87`,
verbatim, abridged only of its predicate methods):

```c
struct Skill { // total : 0xA4/164
    /* +h0000 */ GW::Constants::SkillID skill_id;
    /* +h0004 */ uint32_t h0004;
    /* +h0008 */ GW::Constants::Campaign campaign;
    /* +h000C */ GW::Constants::SkillType type;
    /* +h0010 */ uint32_t special;              // flag bitfield
    /* +h0014 */ uint32_t combo_req;
    /* +h0018 */ uint32_t effect1;
    /* +h001C */ uint32_t condition;
    /* +h0020 */ uint32_t effect2;
    /* +h0024 */ uint32_t weapon_req;
    /* +h0028 */ GW::Constants::ProfessionByte profession;
    /* +h0029 */ GW::Constants::AttributeByte attribute;
    /* +h002A */ uint16_t title;
    /* +h002C */ GW::Constants::SkillID skill_id_pvp;
    /* +h0030 */ uint8_t combo;
    /* +h0031 */ uint8_t target;
    /* +h0032 */ uint8_t h0032;
    /* +h0033 */ uint8_t skill_equip_type;
    /* +h0034 */ uint8_t overcast;              // only if special flag has 0x000001 set
    /* +h0035 */ uint8_t energy_cost;
    /* +h0036 */ uint8_t health_cost;
    /* +h0037 */ uint8_t h0037;
    /* +h0038 */ uint32_t adrenaline;
    /* +h003C */ float activation;
    /* +h0040 */ float aftercast;
    /* +h0044 */ uint32_t duration0;
    /* +h0048 */ uint32_t duration15;
    /* +h004C */ uint32_t recharge;
    /* +h0050 */ uint16_t h0050[4];
    /* +h0058 */ uint32_t skill_arguments;      // 1 duration set, 2 scale set, 4 bonus scale set
    /* +h005C */ uint32_t scale0;
    /* +h0060 */ uint32_t scale15;
    /* +h0064 */ uint32_t bonusScale0;
    /* +h0068 */ uint32_t bonusScale15;
    /* +h006C */ float aoe_range;
    /* +h0070 */ float const_effect;
    /* +h0074 */ uint32_t caster_overhead_animation_id; //2077 == max == no animation
    /* +h0078 */ uint32_t caster_body_animation_id;
    /* +h007C */ uint32_t target_body_animation_id;
    /* +h0080 */ uint32_t target_overhead_animation_id;
    /* +h0084 */ uint32_t projectile_animation_1_id;
    /* +h0088 */ uint32_t projectile_animation_2_id;
    /* +h008C */ uint32_t icon_file_id;
    /* +h0090 */ uint32_t icon_file_id_2;
    /* +h0094 */ uint32_t icon_file_id_hi_res;
    /* +h0098 */ uint32_t name;                 // String id
    /* +h009C */ uint32_t concise;              // String id
    /* +h00A0 */ uint32_t description;          // String id
};
static_assert(sizeof(Skill) == 0xa4, "struct Skill has incorrect size");
```

Fournux/Tyria-Extractor documents 31 of those offsets from its own reading of the
PE (`doc/SKILL_EXTRACTION.md:23-76`) and agrees with GWCA on every one it covers,
**including the tail offsets and the total size**. That is a genuine cross-source
agreement: Tyria-Extractor is not in the authorship cluster (§6), and it arrived
at `0x98`/`0x9c`/`0xa0` for the three string ids on its own.

**Three things about that record a server implementer must not get wrong:**

1. **`energy_cost` at `+0x35` is an encoded byte, not an energy number.** Value 11
   means 15 energy; value 12 means 25 energy; everything else is literal. Both
   sources carry the same two special cases — GWCA as a `GetEnergyCost()` helper
   (`Skill.h:89-95` region), Tyria-Extractor as a documented rule
   (`doc/SKILL_EXTRACTION.md:43`). CLIENT-DATA, but see the caveat below.
2. **`adrenaline` at `+0x38` is a total in adrenaline units, and the displayed
   cost is `ceil(raw / 25)`** — not a plain division. **This document, not
   Tyria-Extractor, is what was wrong.** `doc/SKILL_EXTRACTION.md` §2.1 states
   the ceil formula explicitly, with a worked example (Gash stores 140 units,
   displays 6); only the one-line gloss in its offset table reads "25 units
   correspond to one displayed strike", and that gloss is what this document
   copied. Dividing gives 3.2 for Battle Rage and 4.8 for Defy Pain, which are
   not integers and are not what the client shows. Now verified against 115
   skills — see "The adrenaline field, measured and corrected".
3. **62 of the 164 bytes are undocumented by Tyria-Extractor** — `0x04-0x07`,
   `0x14-0x27`, `0x32`, `0x37`, `0x50-0x57`, `0x74-0x8b`, `0x94-0x97`. GWCA names
   some of those bytes (notably the whole animation block and
   `icon_file_id_hi_res`) but three of its own fields are still offset-named:
   `h0004`, `h0032`, `h0037`, `h0050[4]`. Nobody has fully reversed this record.

**Caveat on the energy encoding, and it is the field most likely to bite us.**
The 11→15 / 12→25 mapping has no disassembly address, no journal entry, and no
test in either source. Two special values is a suspiciously small set for a
hand-derived encoding. Mark it **CLIENT-DATA, uncorroborated by measurement** —
if Rurik ever serves energy costs, verify this one first.

### The adrenaline field, measured and corrected

**CORROBORATED — OBSERVED (ours) + WIKI (GWW), and it refutes the rule this
document shipped.** This is the only field in the 164-byte record we have taken
all the way from raw bytes to what the player sees.

We read `+0x38` out of the client's skill row and watched what the client
displayed:

| Skill | id | raw `+0x38` | client shows |
|---|---|---|---|
| Battle Rage | 317 | 80 | 4 |
| Rush | 319 | 80 | 4 |
| Defy Pain | 318 | 120 | 5 |

The inherited rule — raw ÷ 25 — gives 3.2, 3.2 and 4.8. None is an integer and
none matches. Three observations were not enough to choose between the two
obvious repairs, `ceil(raw/25)` and `floor(raw/25)+1`, since both fit all three.

The wiki supplied the mechanism, which decides it:

- **WIKI (GWW, "Adrenaline" §Gaining adrenaline):** "You gain 25 units of
  adrenaline (=one strike) each time you successfully hit an opponent with a
  weapon", plus 1 unit per 1% of maximum health lost, rounded down.
- **WIKI (GWW, "Battle Rage" §Notes; identical text on "Rush" §Notes):** "This
  skill exactly requires **80 units** of adrenaline to be fully charged, so 3
  strikes and 5 units."

Gain is a flat 25 per hit, so a skill's displayed cost is **the number of hits
needed to charge it**:

```
displayed_strikes = ceil(raw_units / 25)
```

Battle Rage's 80 units is three full strikes with 5 units owing; the fourth hit
covers them, so the client shows 4. `floor(raw/25)+1` is **refuted** — it
predicts 2 for a 25-unit skill, 5 for 100, 6 for 125, 7 for 150 and 9 for 200,
where the correct values are 1, 4, 5, 6 and 8. Any cost that is an exact
multiple of 25 separates the two rules.

Two things worth keeping beyond the formula:

- **GWW independently confirms the raw magnitude**, not just the displayed
  value. "80 units" is exactly our `+0x38`. That is a player-visible page
  agreeing with a byte we read out of the binary, from a source with no
  relationship to the §6 authorship cluster — the strongest corroboration in
  this section.
- **GWW skill pages carry ArenaNet's own skill `id`** in their infobox (Battle
  Rage 317, Defy Pain 318, Rush 319 — consecutive). That is a direct join key
  from a wiki page to a row in the client's skill table, and it makes
  wiki-vs-client cross-checking mechanical rather than manual. `Gw.exe` row
  count and wiki skill count already agree to 0.3% (§"The answer in one page");
  the `id` field is how that comparison could be done row by row.

### The row-by-row audit

**OBSERVED (ours), 2026-08-06.** `toolkit/clientscan/skilltable.py` is our own
stdlib-Python reader for `s_skill`. It locates the table structurally — never by
address — and dumps every row. Against `C:\gw\Gw.exe` (10,483,904 bytes) it
finds the table at file offset `5799632`, **3,443 rows**, of which **1,333** are
the player corpus (`equip_family == 1`, PvP flag clear).

**1,333 is exactly Tyria-Extractor's count.** That is a second implementation,
in a different language, written from the spec rather than the code, landing on
the same number — which is what makes the layout claim above CORROBORATED
rather than merely repeated.

The wiki's `id` field makes the join mechanical. Crawling the ten profession
categories plus Common skills via the MediaWiki API yields 1,788 pages, 1,564
carrying an infobox `id`. Joined against the client table:

| Field | Compared | Agree | Disagree |
|---|---|---|---|
| `adrenaline` → `ceil(units/25)` | 115 | **115** | **0** |
| energy encoding `11` → 15 | 104 | **104** | **0** |
| energy encoding `12` → 25 | 30 | **30** | **0** |
| `elite` flag | 307 client-corpus elites | **all** | **0** |

**Nothing disagreed.** Every gap resolved to a set-definition or coverage
difference, checked rather than assumed:

- 49 wiki-elite ids sit outside the client's corpus-elite set. Sampled 15: all
  15 are `pvp_only` rows with `equip_family == 0` whose `linked_id` points back
  at the base skill — precisely the reciprocal PvP relation
  `SKILL_EXTRACTION.md` §4 describes, and excluded from the corpus by design.
  The elite flag itself agrees on them.
- Ids `121` and `229` carry the encoded energy byte but appear nowhere in the
  crawl. They are not a conflict; the eleven categories walked do not cover
  every skill page. **UNVERIFIED** rather than clean.
- The wiki dump spans 1,564 ids against a 1,333-row corpus, so raw distribution
  totals differ. That is the PvP variants, not a discrepancy.

**This settles the energy encoding**, which this document flagged two sections
above as the field "most likely to bite us" — CLIENT-DATA with no disassembly
address, no journal entry and no test. It now has 134 independent confirmations
and zero exceptions: every skill the wiki shows at 15 energy stores `11`, every
skill it shows at 25 stores `12`. Promote it to **CORROBORATED**. The caveat
above is retained deliberately as a record of what the doubt was worth.

Incidental: the wiki lists exactly **1,329** skills carrying an energy cost —
the same 1,329 this document already cites for the wiki skill count, arrived at
by a different route.

**How to re-read the wiki.** `wiki.guildwars.com` gives a scripted client a
small burst of requests and then refuses it for a long while — MEASURED at 5
consecutive successes out of 20, then hard 403s, with a two-minute backoff not
restoring access. No User-Agent, header set or VPN change helps, and retrying
in a loop is what exhausts the allowance. Use the `browse-gw-wiki` skill in
`.claude/skills/`; a browser is unaffected, and the API *is* reachable from
inside a browser page context (`fetch('/api.php?...')` under `javascript_tool`),
which is how 1,788 pages were pulled here — far cheaper than one navigation per
page.

The occasional scripted success is a trap worth naming: it briefly made the
skill's own selftest report GWW as unblocked, because the check was reading a
cache entry written during a lucky window. A network check a cache can satisfy
is not a network check.

**Do not use the Fandom GuildWiki (`guildwars.fandom.com`) for skill values.**
Its skill templates were last edited 2008–2010 while ArenaNet still ships
balance updates. It lists Defy Pain at 130 units / 6 strikes against GWW's 5 and
our measured 120, and gives 20 seconds for out-of-combat adrenaline decay where
GWW gives 25. Neither page flags itself as uncertain. A frozen wiki does not
produce obvious garbage; it produces confidently wrong specifics that survive a
casual cross-check.

### Where the table itself sits

**CLIENT-DATA.** Tyria-Extractor obtains the client PE by reading it out of
`Gw.dat` as archive file id **4102** and parsing it as a PE32 image, falling back
to a `Gw.exe` on disk and then to a second `Gw.dat` in the parent directory
(`src/dat.rs:16`, `:350-399`). It then locates the skill table **structurally**,
not by address: it scans every PE section at 4-byte steps for a candidate where
row 0 has id 0, **the `u32` at row-0 offset `0x2c` equals the record count**, row
1 has id 1, and row 1's description id is row 0's plus one, then scores up to 256
further rows for plausibility (`src/skills/table.rs`).

That row-0 detail matters for §5: **the table stores its own length**, in the
field that is `skill_id_pvp` on every other row.

**Correction to a claim you may meet elsewhere in this repo: "file 4102 is
Gw.exe" is the tool author's naming, not a demonstrated fact.**
`const CLIENT_PE_FILE_ID: u32 = 4102;` is the only occurrence of 4102 in the
entire Tyria-Extractor tree; no comment, journal entry or commit message explains
how it was determined. What is sourced is "a `MZ`/PE32 image lives at dat file
4102 and the skill table is in it". RECONSTRUCTION on the identification.

GWCA's older forks locate the table differently — by scanning `.text` for the
byte pattern `8D 04 B6 C1 E0 05 05` (an `index * 5 * 32` = `index * 160` address
computation) and validating that the resulting pointer lies in the PE section
named `.rdata` (`GregLando113__GWCA/Source/SkillbarMgr.cpp:147`). **That code is
dead.** The stride it encodes is 160, which is the pre-2026 record size, and
GWToolbox's own generated anchor index shows the current GWCA finds the array via
the `index < arrsize(s_skill)` assertion string instead. Cite the `.rdata` gate
only as era-tagged corroboration for "compiled-in static array", never as a
current-build fact.

### Names and descriptions

**CLIENT-DATA.** They are not strings on the record; they are `uint32` string
ids. Two sources describe two halves of the same pipeline:

- **Tyria-Extractor** resolves a string id to a `Gw.dat` text resource by integer
  division: `file_index = string_id / 1024`, `record_index = string_id % 1024`.
  The `file_index` selects a slot in an **11 languages × 99 text files = 1,089
  pointer array that lives in the PE**; changing language changes only which row
  of that array is used, never the `(file_index, record_index)` pair. The array's
  virtual address is build-specific (`0x00BEF1B8` in one client, `0x00BF0210` in
  the 2026-07-26 client), so the tool locates it structurally as the unique run of
  1,089 backed pointers (`GWDAT_INVESTIGATION_JOURNAL.md:41-47`).
- **GWCA/GWToolbox** shows the *runtime* path: the id is converted to an encoded
  wide string (`GW::UI::UInt32ToEncStr`) and resolved through the client's own
  asynchronous, language-aware text decoder (`GW::UI::AsyncDecodeStr`).

**Descriptions are templates, not finished text.** The stored description carries
`%str1%` / `%str2%` / `%str3%` placeholders which the client fills from the
record's own `scale0`/`scale15`, `bonusScale0`/`bonusScale15` and
`duration0`/`duration15` pairs. Tyria-Extractor decoded 1,261 English templates
and found **only** those three placeholders, each with a non-zero corresponding
endpoint pair (`GWDAT_INVESTIGATION_JOURNAL.md:60-64`). GWToolbox independently
builds the same substitution with control codes `0x10A`/`0x10B`/`0x10C`. Two
lineages, same mechanism.

This retires an open question our own repo logged as unresolved:
`vault/research/2026-08-04/client-data-tables.md:300-310` records the encoded
string format as UNRESOLVED. Tyria-Extractor ships a format document and decoded
1,261 records with it.

**The client draws its own tooltips.** GWToolbox hooks a client function found by
the assertion string `GmTipSkill.cpp` / `"No valid case for switch variable
'm_powerType'"`, which takes `{frame_id, skill_id, ...}` and writes a skill
description into a UI frame. The client can render a complete tooltip **from a
skill id alone**. CLIENT-DATA, and directly load-bearing for Q3.

### Icons

**CLIENT-DATA, with an open disagreement.** The record holds raw `uint32` `Gw.dat`
file numbers. GWToolbox's `Resources::GetSkillImage` feeds `skill->icon_file_id`
straight into `GwDatModule::LoadTextureFromFileId`, which memory-maps the
client's own open `Gw.dat` handle, parses the MFT and decodes the ATEX/ATTX
texture. Tyria-Extractor resolves the same numbers through the dat hash lookup and
writes PNGs.

**CONTESTED — which slot is the high-resolution icon.** Tyria-Extractor documents
`0x8c` as standard and **`0x90` as "high-resolution icon file number in the
analyzed client table"**, and documents nothing at `0x94`. GWCA names `0x8c`
`icon_file_id`, `0x90` `icon_file_id_2`, and **`0x94` `icon_file_id_hi_res`**.
GWToolbox is not even self-consistent: its HD export prefers `icon_file_id_2`,
its listing draws `icon_file_id` first, and `Resources` treats
`icon_file_id_hi_res` as the hi-res one. Three readings of three fields. Do not
build on any of them without measuring.

A wiki-scraping path exists in GWToolbox (`Resources::GetSkillImageFromGWW`) and
in Py4GW (a bundled `skill_descriptions.json` of 1,488 entries plus scraped JPGs).
Neither is how the game renders skills — GWToolbox's wiki function has **zero call
sites in the entire mirror**, and Py4GW's bundles are a back-fill for its own
overlay. Mentioned only so nobody mistakes a scraped asset corpus for client data.

### Cast animations — the real gap

**CONTESTED, tending to NOT FOUND.** GWCA names six animation-id fields at
`+0x74`..`+0x88` (caster overhead/body, target body/overhead, two projectile
animations), with the comment `2077 == max == no animation`. Tyria-Extractor
leaves that entire byte range undocumented. So the *existence* of per-skill
animation ids is single-lineage (cluster) evidence.

Worse, **nothing anywhere resolves an animation id to an asset.** No GWCA or
GWToolbox code reads those six fields for any purpose. GuildWarsMapBrowser carries
a `Gw.exe`-derived animation-state table containing `"Skill Cast"`, `"Skill
Channel"`, `"Spell Cast"` and similar — but those are generic per-*model* states
keyed by hash, with no skill linkage, and the table is a poor source in its own
right: it contains six duplicated hash keys, two sentinel values and one entry the
author flags as invented. Treat it as low-confidence reconstruction.

If we ever need to know which animation a specific skill plays, no source we have
answers it.

### What the client holds at runtime, beyond the constants

**CLIENT-DATA**, all from the 2026 vendored GWCA:

```c
struct SkillbarSkill { // total: 0x14/20
    /* +h0000 */ uint32_t adrenaline_a;
    /* +h0004 */ uint32_t adrenaline_b;
    /* +h0008 */ uint32_t recharge;
    /* +h000C */ Constants::SkillID skill_id;
    /* +h0010 */ uint32_t event;
};
struct Skillbar { // total: 0xBC/188
    /* +h0000 */ uint32_t agent_id;
    /* +h0004 */ SkillbarSkill skills[8];
    /* +h00A4 */ uint32_t disabled;
    /* +h00A8 */ SkillbarCastArray cast_array;
    /* +h00B8 */ uint32_t h00B8;
};
```

`recharge` is an **absolute client timestamp**, not a remaining duration:
`GetRecharge()` returns `recharge - MemoryMgr::GetSkillTimer()`, and 0 means
ready (`GregLando113__GWCA/Source/Skill.cpp:9-12`). The cooldown countdown is
computed entirely client-side once the server has supplied the target tick — the
client never polls "is it ready yet".

Skill unlock state is likewise client-resident once delivered: account-level in
`AccountContext.unlocked_account_skills`, character-level in
`WorldContext.unlocked_character_skills`, both `uint32` bitfields indexed
`array[id/32] & (1 << (id%32))`.

**CONTESTED — the `Skillbar` tail.** The two current sources disagree. GWCA
(refreshed 2026-07-14) has `SkillbarCastArray cast_array` at `+0xA8`; apoguita's
Py4GW_Reforged_Native still carries the older `{h00A8[2], casting, h00B4[2]}`
layout, and their `SkillbarCast` element layouts also differ. Anything Rurik
writes about "the client's casting field" must pick a side and say which.

### Attributes

Attribute constant data is a **second** client-resident array — `AttributeInfo
{profession_id, attribute_id, name_id, desc_id, is_pve}`, `0x14` bytes, count
hardcoded `0x33` (51) in GWCA's scan pattern. Same pattern as skills: names are
string ids, the server sends only numbers.

**A settled correction, and one of the more useful results of this pass:
OpenTyria's attribute id space is wrong.** Three sources place Dagger Mastery at
**29**, leaving 26/27/28 unused, and Mysticism at **44**:

| Source | Dagger Mastery | Mysticism | 26/27/28 |
|---|---|---|---|
| ldufr **OpenTyria** `GmAttributes.h:30,45` | **26** | **41** | packed, no gap |
| ldufr **Headquarter** `include/client/constants.h:80,95` | 29 | 44 | unused |
| **GWLP-R** DB, `default_data.sql:102` | 29 | 44 | three `'Reserved'` rows |
| **GWCA** `AttributeByte` enum | 29 | — | explicit jump to 29 |

Headquarter's own template decoder independently hardcodes `ATTRIBUTE_MAX = 44`
(`code/client/skill.c:576-578`). OpenTyria is contradicted by its own author's
other project, by an unrelated 2013 lineage that shipped 45 populated rows, and
by GWCA. **Do not import OpenTyria's attribute enum.** Note also that GWLP-R's
own parallel Java enum omits the three Reserved slots and therefore diverges from
its own database ids above 25 — that enum is dead code and should not be used
either.

---

## 2. What the protocol says

Everything in this section is the ldufr wire catalogue unless marked otherwise.
Two facts about its provenance govern how much weight it can carry.

**First, the server-to-client half is machine-extracted and the client-to-server
half is not.** `msgdefs.info` is `msgdefs.c` plus one `// Handler Rva:` comment
per format table — and those annotations exist on **39/39 AUTH_SMSG and 487/487
GAME_SMSG tables, and on 0/57 AUTH_CMSG and 0/194 GAME_CMSG tables** (verifier's
own census). The SMSG shapes are anchored to real client dispatch addresses. The
CMSG shapes rest on unstated derivation. Weight them differently.

**Second, `schema/messages.json` is a byte-faithful import of this exact file.**
The verifier re-ran the diff across all four channels: **zero mismatches in field
type, length, count or declared size, over 777 tables**. Its agreement with
`msgdefs.c` is a tautology, never corroboration. It also carries
`"validated_against_build": null`, and `schema/overrides.json` holds exactly one
measured override — a GAME_CMSG entry. **No skill-related SMSG in this repo has
ever been checked against a real client.**

A note on a claim that circulated during this pass: it is *not* true that
`messages.json` has no skill entries. Every skill message's **shape** is there,
correctly, keyed by decimal opcode. What is missing is any **semantic name** —
the file has no name field for any opcode at all. You cannot tell from it that
`70` is `USE_SKILL`; that mapping has to come from `opcodes.h` by hand.

### Server → client

Sizes below are **wire** bytes computed from `msgpack.c`'s packer, which writes an
array count as `u16` on the wire while the struct holds it as `u32` — so a
variable message is exactly 2 bytes smaller per array than its declared size.

**The skill bar**

| Opcode | Name | Wire shape | Bytes | Sent by OpenTyria? |
|---|---|---|---|---|
| 217 / `0x00D9` | `SKILLBAR_UPDATE_SKILL` | agent_id, u8 slot, u16 skill_id, u32 | 13 | no |
| 218 / `0x00DA` | `SKILLBAR_UPDATE` | agent_id, array32[8] skills, array32[8] pvp_masks, u8 | 75 at 8/8 (declared 79) | **yes** |

`SKILLBAR_UPDATE` is the full-bar load and the single most important message in
this document. Its sender, verbatim (`ldufr__OpenTyria/code/GmPlayer.c:150-167`):

```c
void GameSrv_SendSkillbarUpdate(GameSrv *srv, GameConnection *conn, GmPlayer *player)
{
    GameSrvMsg *buffer = GameSrv_BuildMsg(srv, GAME_SMSG_SKILLBAR_UPDATE);
    GameSrv_SkillbarUpdate *msg = &buffer->skillbar_update;
    msg->agent_id = player->agent_id;
    msg->n_skills = 8;
    msg->skills[0] = player->character.skill1;
    /* ... skills[1..6] ... */
    msg->skills[7] = player->character.skill8;
    msg->n_pvp_masks = 8;
    msg->unk1 = 1;
    GameConnection_SendMessage(conn, buffer, sizeof(*msg));
}
```

Note what it does *not* do: it declares `n_pvp_masks = 8` and never writes
`pvp_masks[]`, so eight zero dwords go out from `BuildMsg`'s memset. And
`skill1..skill8` are SQLite columns that **default to 0 and are never assigned
anywhere in the codebase** — no `UPDATE` statement touches them, and no CMSG
handler exists to set them. UPSTREAM. The trailing `unk1 = 1` is uncited.

**The cast lifecycle** — all five defined, none ever sent by any reference server:

| Opcode | Name | Wire shape | Bytes |
|---|---|---|---|
| 226 / `0x00E2` | `SKILL_INTERUPTED` *(sic)* | agent_id, u16 skill_id, u32 | 12 |
| 227 / `0x00E3` | `SKILL_CANCEL` **and** `SKILL_ACTIVATED` | agent_id, u16 skill_id, u32 | 12 |
| 228 / `0x00E4` | `SKILL_ACTIVATE` | agent_id, u16 skill_id, u32 | 12 |
| 229 / `0x00E5` | `SKILL_RECHARGE` | agent_id, u16 skill_id, u32, u32 recharge | 16 |
| 230 / `0x00E6` | `SKILL_RECHARGED` | agent_id, u16 skill_id, u32 | 12 |

**Opcode 227 is defined twice, under two names, on consecutive lines of
`opcodes.h:266-267`.** The verifier's duplicate scan confirms it is the *only*
duplicated GAME_SMSG number in the file. This is not obviously a bug: the
extracted client dispatch table gives **226 and 227 the same handler RVA
`004E6610`** while their neighbours (225 → `004E65F0`, 228 → `004E6630`) differ,
and Headquarter's handler for `SKILL_ACTIVATED` declares its payload struct with
the name `SkillCancel` (`code/client/skill.c:133`). The author knew. Whether
cancel and activated are one context-dependent message or a copy-paste error is
**UNVERIFIED** — but anyone importing this table gets a silent collision.

GWCA's independent naming for the same numbers matches, and adds field names the
ldufr side lacks:

```c
struct SkillActivate  { uint32_t agent_id; uint32_t skill_id; uint32_t skill_instance; };
struct SkillRecharge  { uint32_t agent_id; uint32_t skill_id; uint32_t skill_instance; uint32_t recharge; };
struct SkillRecharged { uint32_t agent_id; uint32_t skill_id; uint32_t skill_instance; };
```

That third field, **`skill_instance`**, is the single most useful unknown in this
document for anyone building an execution engine. It appears in all three
lifecycle messages, recurs in GWLP-R's 2013 templates under the same name, and
has no counterpart in OpenTyria's structs. It reads as a cast-correlation handle.
Its semantics are NOT FOUND.

**Effects, conditions, enchantments** — six messages, 63-68, all defined, none
ever sent by any reference server:

| Opcode | Name | Wire shape | Bytes |
|---|---|---|---|
| 63 / `0x003F` | `EFFECT_UPKEEP_ADDED` | agent_id, agent_id, u16, u32, u32 | 20 |
| 64 / `0x0040` | `EFFECT_UPKEEP_REMOVED` | agent_id, u32 | 10 |
| 65 / `0x0041` | `EFFECT_UPKEEP_APPLIED` | agent_id, agent_id, u16, u32, u32 | 20 |
| 66 / `0x0042` | `EFFECT_APPLIED` | agent_id, u16, u32, u32, u32 | 20 |
| 67 / `0x0043` | `EFFECT_RENEWED` | agent_id, u32, u32, u32 | 18 |
| 68 / `0x0044` | `EFFECT_REMOVED` | agent_id, u32 | 10 |

There is **no message named CONDITION, ENCHANT, HEX, AURA or BUFF anywhere in the
GAME_SMSG list.** Conditions and enchantments ride the `EFFECT_*` family, tagged
by a type code. The only source that names the type codes is Headquarter:
`EFFECT_APPLIED` = `{agent_id, u16 skill_id, u32 effect_type, u32 effect_id, u32
duration-as-float}` with **0 = condition/shout, 8 = stance, 11 = maintained
enchantment, 14 = enchantment/nature ritual**. Single-source, uncited.
RECONSTRUCTION. GWCA corroborates only the field *shape*, naming the third field
`attribute_level` rather than `effect_type` — a **CONTESTED** field name in the
one message that would carry a condition.

**Energy, health, regeneration, and most of casting** are not dedicated messages
at all. They ride a generic property channel:

| Opcode | Name | Wire shape |
|---|---|---|
| 159 / `0x009F` | `AGENT_PROPERTY_UPDATE_INT` | **u32 prop_id first**, then agent_id, u32 value |
| 160 / `0x00A0` | `..._INT_TARGET` | prop_id, agent_id, agent_id, value |
| 161 / `0x00A1` | `AGENT_PROPERTY_PLAY_EFFECT` | Vec2, u16, agent_id, u16, u8, u8 |
| 162 / `0x00A2` | `AGENT_PROPERTY_UPDATE_FLOAT` | prop_id, agent_id, float |
| 163 / `0x00A3` | `..._FLOAT_TARGET` | prop_id, agent_id, agent_id, float |
| 164 / `0x00A4` | `AGENT_PROJECTILE_LAUNCHED` | agent_id, Vec2, u16, u32, u32, u32, u8 |

Note the field order: **`prop_id` comes before `agent_id` on the wire.**

The property vocabulary is a 66-entry enum (`GmAgentProperties.h`). The
skill-relevant entries:

```
Energy = 41    Health = 42    EnergyRegen = 43    HealthRegen = 44
CastSkill = 60    InterruptSkill = 59    CastAttackSkill = 50    CastTimeModifier = 61
SkillDamage = 10    ApplyAnimation = 22    ApplyAnimationLoop = 28
ApplyAura = 6    RemoveAura = 7    ApplyEffect1 = 20    ApplyEffect2 = 21
Knockdown1 = 35    Knockdown2 = 63    AttackFail = 38    InterruptAttack = 49
```

**This vocabulary is the one place in the whole pass where three lineages agree
across thirteen years.** GWLP-R's `GenericValue.java` (2013) lists Energy = 41,
Health = 42, EnergyRegen = 43, HealthRegen = 44, SkillDamage = 10, CastSkill = 60,
InterruptSkill = 59, CastAttackSkill = 50, CastTimeModifier = 61 — the same
ordinals, in an unrelated codebase, a decade earlier. GWCA's `GenericValueID`
adds `skill_finished = 58`, `energy_spent = 62`, `instant_skill_activated = 48`,
`attack_skill_activated = 50`, `attack_skill_finished = 46`, `knocked_down = 63`.
Both sources also flag their own ignorance honestly: 14 of GWLP-R's 66 ordinals
carry `// TODO: Generic Value missing!`, and 14 of OpenTyria's 66 are named only
by their number (`AgentPropertyValue_1`, `_Value13`, `_Value18`, …).

If Rurik ever builds a skill-effect oracle, **this enum is its vocabulary**, and
it is the best-corroborated thing in this document after the record layout.

**Account state**

| Opcode | Name | Shape | Wire max |
|---|---|---|---|
| 29 / `0x001D` | `PVP_UPDATE_UNLOCKED_SKILLS` | header + array32[128] | 516 bytes |
| 219 / `0x00DB` | `UPDATE_UNLOCKED_SKILLS` | header + array32[128] | 516 bytes |

Both are sent by OpenTyria, both read the **same** `unlocked_skills` bitmap —
that server draws no PvE/PvP distinction. Neither message carries an agent id.
128 dwords is **4,096 bits**, comfortably covering the ~3,443-entry id space.

**Do not copy OpenTyria's unlock path.** The verifier found five stacked defects:
`bitmap_length` passes a byte count where an element count is expected and reads
`bitmap[127]` out of bounds on a 32-element array; the returned value is a *bit*
index used as an *element* count; `_bitmap_bitlen` returns the index of the lowest
set bit rather than a bit length; `set_bit` assigns instead of OR-ing (destroying
31 bits); `clear_bit` assigns `~(1<<pos)` (setting 31 bits). None of it was ever
noticed because **`bitmap_set_bit` and `bitmap_clear_bit` have zero call sites in
the entire repository** — at the pinned commit, OpenTyria unlocks nothing at all.

**Unmapped protocol sitting inside the skill block.** 249 of the 487 GAME_SMSG
format tables have no name in `opcodes.h`. Ten of the unnamed ones sit inside or
beside the skill block, all with real client handler RVAs. Three are worth
flagging:

- **211** (`0x00D3`): `header + array32[128]`, declared 518 — **byte-identical in
  shape to both unlock-list messages**, three slots before `SKILLBAR_UPDATE_SKILL`.
  A third unlock-list-shaped message nobody has named.
- **231** (`0x00E7`) and **232** (`0x00E8`): sit immediately after
  `SKILL_RECHARGED` and share the lifecycle shape (231 is exactly
  `agent_id, u16, u32`). The best candidates for the "skill done" and "instant
  skill" messages the named catalogue lacks.

### Client → server

Weaker evidence — no RVAs, no C structs, and **not one of these is dispatched by
any reference server**.

| Opcode | Name | Wire shape | Bytes |
|---|---|---|---|
| 14 / `0x000E` | `ATTRIBUTE_DECREASE` **✓ CONFIRMED** | agent_id, **sequence**, **attribute** | 14 |
| 15 / `0x000F` | `ATTRIBUTE_INCREASE` **✓ CONFIRMED** | agent_id, **sequence**, **attribute** | 14 |
| 16 / `0x0010` | `ATTRIBUTE_LOAD` **✓** | agent_id, **ids[]**, **ranks[]** (16 max, not 64) | 142 decl. |
| 28 / `0x001C` | `HERO_USE_SKILL` | agent_id, u32, u32, agent_id | 18 |
| 41 / `0x0029` | `DROP_BUFF` | u32 | 6 |
| **70 / `0x0046`** | **`USE_SKILL`** | **u32, u32, agent_id, u8** | **15** |
| 92 / `0x005C` | `SKILLBAR_SKILL_SET` | agent_id, u32, u32, u32 | 18 |
| 93 / `0x005D` | `SKILLBAR_LOAD` | agent_id, array32[8] | 42 decl. |
| 94 / `0x005E` | `SKILLBAR_SKILL_REPLACE` | agent_id, u32 ×4 | 22 |
| 109 / `0x006D` | `TOME_UNLOCK_SKILL` | u32, u32 | 10 |

**The first three rows stopped being weak evidence on 2026-08-19** — see
[pvpui §32](../pvpui/FINDINGS.md). Both names *and* their direction assignment are
confirmed from the client's own senders (`0x00818A90` decrease, `0x00818CE0` increase,
each reached only from the attribute panel's own minus/plus button handler in
`AttribBtns.cpp`), and the two anonymous dwords are now named: a **sequence** and an
**attribute index**. The sequence is the handle of a client-side PREDICTION the server
retires with `0x0036`. Nine live rank transitions price out exactly against
`s_attribPoints`, in both directions, with no free parameter. `ATTRIBUTE_LOAD`'s declared
142 bytes also hide a client defect: the sender clamps to 64 entries and its buffer holds
16.

`USE_SKILL`'s four fields are **unnamed in every source we have**. Headquarter
emits it as `{i32 skill_id, i32 flags, AgentId target, u8}`; apoguita's packet
sniffer guesses `skill_id, type, target_id, flags`. Neither is corroborated.
The reading "first dword is the skill id" is inference, not a sourced fact.

**The `0x8000` CMSG mask is on the wire.** `GameSrv_GetMessages` masks the raw
header only to index the format array; the unmasked value is what lands in
`msg->header` and is compared against the mask-OR'd constants in the dispatch
switch. This corroborates the movement pass's own capture finding.

**OpenTyria dispatches zero skill-related client messages.** Its switch
(`GameSrv.c:1845-1901`) has exactly 16 cases: disconnect, heartbeat, two pings,
three instance-load requests, four character-creation messages, equipped colour,
chat, move-to-coord, cancel-movement, last-position. Everything else falls to a
`default` that logs a warning and returns `ERR_BAD_USER_DATA` — **a value the
sole call site discards uninspected**. A client can send `USE_SKILL` at this
server all day; nothing happens and nothing breaks.

### What actually reaches a client at map entry

**UPSTREAM**, verified call-chain, from `GameSrv_HandleInstanceLoadRequestPlayers`
(the reply to CMSG 144 / `0x0090`), in send order:

1. `PVP_UPDATE_UNLOCKED_SKILLS` (29) — `GameSrv.c:1460`
2. `AGENT_UPDATE_ATTRIBUTE_POINTS` (55) — hardcoded 50 unused / 50 used
3. `PLAYER_UPDATE_PROFESSION` (183)
4. `PLAYER_UPDATE_UNLOCKED_PROFESSIONS` (182)
5. `SKILLBAR_UPDATE` (218) — eight zeros
6. `UPDATE_UNLOCKED_SKILLS` (219) — empty
   *(2–6 are one function, `GameSrv_SendSkillsAndAttributes`, `GameSrv.c:1469`)*

Those are **upstream's own symbol names**, quoted as it writes them. In this
repo 183 is `AGENT_PROFESSIONS` and 182 is `AGENT_PROFESSION_BITS`, named
from the client instead — see the provenance stamp further down this file.
7. `AGENT_UPDATE_ATTRIBUTES` (58) — `GameSrv.c:1473`
8. two `AGENT_PROPERTY_UPDATE_INT` + one `_FLOAT` — energy, health, regen
9. `AGENT_INITIAL_EFFECTS` (240) — always zero

None of it is in the pre-request initial burst. **Correction to a claim made
during this pass:** the same five-message block *also* fires on the
character-creation path (`GameSrv.c:1549`), in a completely different surrounding
order. If Rurik replays map-entry ordering, note also that
`PLAYER_UPDATE_PROFESSION` is sent **twice** on the map-entry path — once inside
the block and again directly at `GameSrv.c:1476`.

Several of these are stubs, and the study should not mistake them for knowledge:
`AGENT_UPDATE_ATTRIBUTES` sets `data_len = 42` and **never writes `data_buf`**, so
42 zero dwords go out; attribute points are hardcoded 50/50 for a level-0
character; `energy_per_sec` is never assigned, so regen is always 0.0; and the
world tick's regeneration arithmetic integrates permanently-zero rates into
fields that are never transmitted.

`GameSrv.c:1467-1468` preserves a comment from a live packet capture that the
**real** server sends two messages, decimal 123 and 124, between `INSTANCE_LOADED`
and the skill block — messages OpenTyria does not implement. That gap sits exactly
where the skill block begins.

### The cast lifecycle, as the only source that models it describes it

**UPSTREAM, single-source.** Headquarter is a headless *client*, so what it
implements is evidence about what a client expects:

1. client sends CMSG `USE_SKILL` (70) and **optimistically** sets
   `skill->casting = true` and `agent->casting_skill_id`;
2. server sends `SKILL_ACTIVATE` (228) → `skill->casting_confirmed = true`;
3. server sends `SKILL_ACTIVATED`/`SKILL_CANCEL` (227) → both flags cleared,
   `casting_skill_id` reset to 0;
4. server sends `SKILL_RECHARGE` (229) → `recharging = true`;
5. server sends `SKILL_RECHARGED` (230) → `recharging = false`.

Every handler bails with `LogError` if the agent has no skillbar or the skill id
is not on the bar. Note the pattern in step 1: **the client acts first and waits
for confirmation.** It is the same architecture the movement pass found — the
client predicts, the server confirms.

`SKILL_RECHARGE`'s trailing dword is the only trailing dword anywhere in the
lifecycle that gets a name: Headquarter calls it `recharge_sec`
(`code/client/skill.c:187-220`). Single-source, uncited.

---

## 3. The minimum to get one real skill on the bar, drawn correctly

**One message, and we already send it.**

`GAME_SMSG_SKILLBAR_UPDATE`, opcode **218** (`0x00DA`), payload:

| Field | Type | Value |
|---|---|---|
| header | u16 | `218` little-endian |
| agent_id | u32 | the player's agent id |
| n_skills | u16 on the wire | `8` |
| skills[8] | u32 × 8 | the skill ids, `0` for an empty slot |
| n_pvp_masks | u16 on the wire | `8` |
| pvp_masks[8] | u32 × 8 | zeros are what upstream sends |
| unk1 | u8 | `1` (upstream's uncited constant) |

75 bytes at 8/8. That is the whole of Q3 **as far as any source we have can tell
us.** The client resolves the icon, the name, the concise and full descriptions,
the energy cost, the cast time and the recharge from its own table using the id.
Nothing else crosses the wire.

**Two things to send alongside, and why:**

- **An unlock bitmap** — `UPDATE_UNLOCKED_SKILLS` (219) and/or
  `PVP_UPDATE_UNLOCKED_SKILLS` (29), `header + u16 count + count × u32`, bit *n*
  of word *n/32* meaning skill *n* is unlocked. Whether the client *refuses to
  draw* a bar skill that is not unlocked is **NOT FOUND** — no source states it
  either way. The Go server side-steps the question by sending 128 words of
  `0xffffffff`, which is a usable experiment: blanket-unlock everything, see what
  draws.
- **`SKILLBAR_UPDATE_SKILL`** (217), 13 bytes, `{agent_id, u8 slot, u16 skill_id,
  u32}` — the cheap single-slot change once a bar exists. Headquarter's handler
  requires the skillbar to already exist, so send the full bar first.

**The caveats, in the order they are likely to bite:**

1. **Our opcode numbering has never been validated against our own client.**
   `messages.json` carries `validated_against_build: null`; the one measured
   override in the repo is for a different message. And there is a *known,
   dated* renumbering in exactly this range — see §6.
2. **The skill id must exist in the client's table.** Ids run 0..3442 in the
   2026-07-26 client, with 405 unused slots scattered through the range and the
   largest gap being ids 658–762. An id in a hole has a row, but its contents are
   whatever occupies that row.
3. **The client updates its own skillbar display without waiting for the
   server.** GWCA documents this explicitly, as a bug it has to work around, and
   names the responsible UI message `kUpdateSkillbar` (`0x1000005e`). So a
   "the bar drew correctly" observation is not by itself proof the server message
   was understood.
4. **Not every row in the table is a player skill.** GWCA's own header comment:
   *"Guild Wars uses the skill array to build mods for weapons, so stuff like runes
   are skills too"*. Row selection for real skills goes by the equip/use-family
   byte at `0x33` plus the PvP flag. Rows 3418–3421 carry a not-playable flag and
   the localized name `...`.
5. **`pvp_masks[]` is unexplained.** Upstream declares eight and sends zeros.
   Whether the client needs it populated is NOT FOUND.

**A concrete first experiment**, entirely within what this document supports:
pick a Pre-Searing skill id, put it in `skills[0]`, send 219 with a bitmap that
has that bit set, and look at the bar. If the icon and tooltip render, Q1 and Q3
are both confirmed against our own client in one shot, and every claim in §1
about client-side residency graduates from CLIENT-DATA to OBSERVED.

---

## 4. The minimum to cast it and see an animation

**This one is not answerable from our sources, and it is important to say so
plainly.** No reference server in our vault implements casting. OpenTyria: no cast
state, no cast timer, no interrupt, no recharge tracking, no damage — the whole
concept is absent from the agent struct. GWLP-R: defines the wire shapes and never
constructs a single one of them. The Go server: a repo-wide search for "cast"
matches only the word "broadcast".

What the sources *do* support is a **hypothesis with named messages**, which is
worth stating precisely because it is testable in one session:

1. The client sends CMSG `USE_SKILL` (70 / `0x0046`), 15 bytes,
   `{u32, u32, agent_id, u8}` — field meanings unnamed in every source.
   **The client will not send it if its own local state says the skill is still
   recharging or the target type is wrong**; both checks run purely on
   client-resident data before any packet leaves.
2. The server answers `SKILL_ACTIVATE` (228 / `0x00E4`), 12 bytes,
   `{agent_id, u16 skill_id, u32}` — GWCA names that third field `skill_instance`.
   **This is the message most likely to start the animation**, because it is the
   only thing the server sends between the request and the completion, and the
   client already holds the skill's six animation ids locally.
3. The server ends the cast with 227 (`SKILL_ACTIVATED`/`SKILL_CANCEL`), then
   brackets the cooldown with `SKILL_RECHARGE` (229, carrying the recharge value)
   and `SKILL_RECHARGED` (230).
4. Energy expenditure and cast timing ride the property channel, not dedicated
   messages: `energy_spent = 62`, `casttime = 61` ("non-standard cast time, value
   in seconds"), `skill_activated = 60`, `skill_finished = 58`,
   `instant_skill_activated = 48` on opcode 159/162.

**Why "will the animation play" is genuinely open.** The client holds
`caster_body_animation_id` and five siblings for every skill, and it certainly
does not need to be told which animation to use. But nothing in any source
identifies what triggers it. Three candidates, none confirmed:
`SKILL_ACTIVATE` (228) alone; `AgentProperty_ApplyAnimation` (22) or
`CastSkill` (60) over the property channel; or the client self-animating on
sending `USE_SKILL` and merely waiting for confirmation — which is exactly the
architecture the movement pass established for walking, and is therefore the
hypothesis I would test first.

GWToolbox supplies one useful sidelight: it can NOP out client-side skill warm-up
timing with a two-byte patch at a scanned site. **Some cast timing is enforced in
the client**, not only server-side.

**Two named messages that would matter and that nobody sends:** `SCREEN_SHAKE`
(70 / `0x0046` SMSG, distinct from the CMSG of the same number) and
`AGENT_PROPERTY_PLAY_EFFECT` (161), the only named message pairing a world
position with an effect payload; plus `AGENT_PROJECTILE_LAUNCHED` (164), which
GWCA documents as covering "martial weapons and projectile-launching skills".

---

## 5. New skill, or re-skinned id?

**Short answer: re-skin an existing id. It is available today, it needs zero
client changes, and it is a different project by an order of magnitude from adding
a new id.**

### What the server can freely choose

Everything about **behaviour**. Nothing on the server side constrains a skill id
to mean what ArenaNet meant. In OpenTyria, `skill1..skill8` are opaque `u32`
columns copied verbatim into the wire message, and the unlock bitmap is a raw bit
index. When the server decides that using id *N* deals 40 damage and applies
Burning for 3 seconds, no source we have suggests the client checks. The client
draws the id's shipped icon and tooltip, and the mechanical outcome is entirely
whatever the server says it is.

**The consequence worth stating out loud:** a re-skinned skill's tooltip will lie.
The client renders the *shipped* description from its own table, filled in from
the shipped `scale0`/`scale15` numbers. If our Fireball does something else, the
tooltip still describes ArenaNet's Fireball. That is a design constraint on
re-skinning, not a technical obstacle.

### What the server cannot touch

| Property | Where it lives | Can a server change it? |
|---|---|---|
| Name, concise, full description | dat text records, via string ids in the PE row | **No** |
| Icon (standard and hi-res) | dat ATEX/ATTX textures, via file numbers in the PE row | **No** |
| Energy, adrenaline, health cost | PE row `0x34-0x38` | **No** |
| Activation, aftercast, recharge | PE row `0x3c`, `0x40`, `0x4c` | **No** |
| Attribute, profession, type, elite flag | PE row `0x28`, `0x29`, `0x0c`, `0x10` | **No** |
| Rank-0/rank-15 scaling shown in the tooltip | PE row `0x44`-`0x68` | **Yes, 2026-08-14** — `skilltable.py`, whole window bar `+0x50` (§4 of the 2026-08-05 block) |
| Animation ids | PE row `0x74`-`0x88` | **No** |
| Whether the id exists at all | PE table length at row 0 `+0x2c` | **No** |

Nothing in any protocol message in either direction carries any of these. That
negative was checked three ways: the ldufr SMSG catalogue was walked end to end,
GWLP-R's 907-name packet catalogue was searched, and network-log-explorer's
build-38771 name table was enumerated. **NOT FOUND, three lineages deep.**

Two further pieces of evidence that the id space is the client's to define, not
the server's:

- **New ids arrive by the client's table growing.** GWCA's `SkillID` enum gained
  `Reforged_Mode = 0xD6A` and `Dhuums_Covenant_Broken = 0xD6B` in a dated commit
  (2025-12-19), moving `Count` from `0xD6A` to `0xD6C`. Tyria-Extractor
  independently measured **one appended row, id 3442**, in the 2026-07-26
  executable versus the earlier snapshot. When ArenaNet adds a skill, they ship a
  client.
- **GWLP-R's protocol says the same thing in prose.** Its `DialogButton` packet
  documents its `SkillID` field as *"the skill displayed if skill icon is used
  else its value: 0xFFFFFFFF"* — the server sends a bare id as an **icon
  selector**, and the client is expected to already own the art.

### What adding a genuinely new id would actually require

Four separate pieces of work, in dependency order:

1. **Grow the PE skill table.** Append a 164-byte row and update the record count
   stored at row 0's `+0x2c`. The id is the row index, so ids must stay dense.
2. **Add name and description records to a `Gw.dat` text file** at
   `(string_id / 1024, string_id % 1024)`, for as many of the 11 languages as you
   care about — and update the 1,089-pointer language table in the PE if the
   target text file does not already exist.
3. **Add ATEX/ATTX icon textures to `Gw.dat`** and wire their file numbers into
   the row. This means producing the container: 4-byte magic, FourCC, dimensions,
   data-range size, subcode bitfield, then the bitstream and planar tail — ATEX
   stores undecoded block components in separate planes rather than complete DXT
   blocks.
4. **Choose animation ids** from whatever the client already has, since nothing
   we have resolves an animation id to an asset.

> **SUPERSEDED 2026-08-14. Read this before costing anything below.** The blocker
> named in the next paragraph has FALLEN, and the paragraph is left standing only
> because the reasoning around it is still good. It says writing to `Gw.dat` is
> "not a demonstrated capability in our entire evidence base" — true of the
> *mirrors*, and no longer true of this repo:
>
> * **step 2 (text records) is done** — `toolkit/mapdata/textwrite.py` wrote 188
>   authored skill-name records into text file 98 and the retail client read them
>   back off the bar (`studies/profession/RESKIN.md` §24);
> * **step 3 (icon textures) is done** — `toolkit/mapdata/iconset.py` armed 125
>   ATEX rows with generated art, on screen since 2026-08-14;
> * **step 1 (grow the PE table)** this document already calls tractable, and the
>   repo now patches six tables in that image (`toolkit/clientpatch/reskin.py`).
>
> **Only step 4 is still open**, and it is the one this document independently
> flags as the real gap: nothing anywhere resolves an animation id to an asset
> (§"Cast animations"). That is now the binding constraint on a genuinely new
> skill id, not the archive.
>
> The §5 table above should be read the same way: its "Can a server change it?"
> column is about what a server can change **at run time over the wire**, and
> every "No" in it is still correct in that sense. Four of those rows have since
> been changed **out of band** — name, icon, attribute and profession — by
> patching the PE row and writing the archive. Do not read that column as "cannot
> be changed".

**The blocker is step 2 and step 3, and it is concrete: neither mirrored dat tool
can write.** Tyria-Extractor and GuildWarsMapBrowser both open the archive
strictly read-only. There is no repack, no MFT insert and no hash-row insert
anywhere in either codebase. Writing to `Gw.dat` is not a demonstrated capability
in our entire evidence base — it is unexplored territory, not a solved problem
someone else has tooling for.

Step 1 is comparatively tractable and, notably, **is a capability this project
already has**: we patch the client binary today for the DH key
(`toolkit/clientpatch/make_custom_client.py`), and `toolkit/gwpe.py` is a
dependency-free PE reader. Growing a table in a PE we already patch is a smaller
step than it sounds.

One inference, labelled as such: the client almost certainly executes the `Gw.exe`
on disk rather than the copy at dat file 4102 — Tyria-Extractor treats them as
interchangeable and falls back from one to the other — so a PE patch would target
the on-disk executable. **Unverified**; nothing in our sources states the
relationship between the two copies.

### The honest summary

| | Re-skin an existing id | Add a new id |
|---|---|---|
| Client binary changes | none | grow the PE skill table |
| `Gw.dat` changes | none | new text records **and** new ATEX icons |
| Tooling we have | all of it | PE patching only; **no dat writer exists anywhere** |
| Tooltip correctness | wrong (shows shipped text) | correct, if you author it |
| Available today | **yes** | no |

Repurposing is not a compromise, it is the whole of R4b as far as the client
cares: ~1,300 shipped ids, each with correct art and text, waiting for behaviour
that only we can supply. Adding an id is a client-modding project that should be
scoped separately and only if authoring genuinely new content becomes the goal.

---

## 6. How far to trust these sources

**The provenance finding of this pass, and it demotes the movement study's own
lineage table:** the "ldufr" and "GWCA" groups are **not independent**.

GWToolbox's own credits name three people as authors of "the GW API used"
(`gwdevhub__GWToolboxpp/README.md:93-104`): **KAOS** (GregLando113) as original
creator, and **Ziox** (github.com/reduf) and **Jon** (github.com/3vcloud) as
major contributors. The identity chain closes on three separate tokens:

```
git -C gwdevhub__GWToolboxpp log --format='%an <%ae>' | sort -u
  Ziox            <<one hotmail address, identical on all four lines>>
  reduf           <<one hotmail address, identical on all four lines>>
  Laurent Dufresne <<one hotmail address, identical on all four lines>>

git -C ldufr__OpenTyria log --format='%an <%ae>' | sort -u
  Laurent Dufresne <<one hotmail address, identical on all four lines>>      (all 180 commits)
```

A third project outside both confirms the handle:
`Jonathan-Greve__GuildWarsMapBrowser/README.md:64` thanks
*"[Laurent Dufresne](https://github.com/ldufr)"*. And Jon Riley plus Leo
Friedrichs appear as committers in **both** Headquarter and GWToolbox —
Headquarter has only eight distinct author identities in its entire history, and
half of them are that overlap.

**GWLP-R is in the cluster too**, as its ancestor. GWCA's own header credits
*"Most low level ground work of API via the GWCA and GWLP:R projects"*
(`GWCA.h:19-20`) and its `StoCMgr.h` points readers at GWLP-R's packet wiki.

**And gw-preservation, which this pass initially nominated as the strongest
independent candidate, is not independent either — for naming.** Its
`network-log-explorer/src/lib/Constants.ts` is a 340-entry opcode→name table that
matches OpenTyria's `opcodes.h` on **337 of 340 entries, on both number and
name** — including OpenTyria's misspelling:

```
Constants.ts:263   0x00E2: "SKILL_INTERUPTED",
opcodes.h:265      #define GAME_SMSG_SKILL_INTERUPTED   (GAME_SMSG_MASK | 0x00E2) // 226
```

One `R`, in both, 337 agreements deep, with OpenTyria's file predating it by ten
months. Convergent independent reverse engineering does not reproduce a typo. That
misspelling propagates through **nine repositories** in our vault: both GWCA
mirrors, the live vendored GWCA, GWToolbox, OpenTyria, Headquarter, all three
apoguita repos, and network-log-explorer. It is the cleanest single proof that
this is one corpus.

The earlier reasoning — "we grepped for citations and found none" — was the wrong
test. Absence of attribution is not absence of derivation; the right test is to
diff the corpus.

### What that leaves

| Claim type | Genuinely independent sources |
|---|---|
| Opcode **numbering and naming** | **None.** One corpus, nine repos. |
| Skill **record layout** | Two: the cluster (GWCA) and **Fournux/Tyria-Extractor** (partial — it cites GWToolbox and Py4GW as "conceptual references", and takes its FFNA file-reference formula from GuildWarsMapBrowser, but it also *corrects* GWCA, which is what real independence looks like). |
| Skill **count** | Two, by unrelated methods: Tyria-Extractor's PE measurement (1,333 base rows) and the Guild Wars wiki (1,329 player skills). |
| **`adrenaline` at `+0x38`** | Two, and one of them is ours: our own reader over `Gw.exe`, and GWW. 115 skills, zero disagreements. The wiki shares no author or code with this cluster. |
| **Energy encoding (`11`→15, `12`→25)** | Two: our own reader and GWW, 134 skills, zero exceptions. Was the weakest CLIENT-DATA claim in this document; now the best-tested one. |
| **Skill corpus size (1,333)** | Two implementations from the spec: Tyria-Extractor (Rust) and `toolkit/clientscan/skilltable.py` (ours, Python), same structural search, identical count. |
| Capture **methodology** | gw-preservation is genuinely independent here — its `annotate.py` decodes the client's *own* runtime field-descriptor bitfield rather than consulting a hand-maintained table, and its RC4 scan signatures appear nowhere else in the vault. |
| Attribute id space | Three against one (see §1). |

### The opcode drift, which is real and dated

The numbering in this document is **post-shift**, and the shift is documented:

- GWCA commit `933975a5` (2025-12-19) renumbered every SMSG at or above `0x003C`
  by **+1**. `SKILLBAR_UPDATE_SKILL` moved `0x00D8` → `0x00D9`; the `EFFECT_*`
  family moved `0x003E..0x0043` → `0x003F..0x0044`.
- apoguita's own files witness the same event from outside: a legacy file
  committed 2026-02-02 numbers every skill opcode exactly **one lower** than its
  current (2026-06-17) tables.
- The **Go server**, which enforces client build **37600**, implements
  structurally identical messages consistently one lower in the `0x9E`–`0xF1`
  neighbourhood (`0xD9` vs `0xDA`, `0xEF` vs `0xF0`, `0x9E` vs `0x9F`, `0xA1` vs
  `0xA2`) — while matching exactly at `0x0037`, proving the shift is **localized,
  not global**.

Since gw-preservation's opcode work is its own measurement even though its *names*
are borrowed, that last row is real corroboration that the shift happened between
build 37600 and build 38771. **Our client is 38797.** ldufr's numbering — which
is what `messages.json` imported — is post-shift and therefore the right side of
the drift. That is reassuring and it is not validation.

The practical consequence of getting this wrong is worse than a missing message:
under build 38771, the slot the Go server uses for energy updates (`0x009E`) is
`AGENT_DISPLAY_DIALOG`, and the slot it uses for floats (`0x00A1`) is
`AGENT_PROPERTY_PLAY_EFFECT`. An off-by-one here does not fail silently; it
delivers an energy value into a dialog box.

### Per-source currency, for skill claims specifically

| Source | Best-evidenced era | Use it for |
|---|---|---|
| **Our own captures** | build **38797**, 2026-08-05 | The only source measured against our client. Skill coverage: three account-disclosure messages, sent by *our* stub. |
| **Fournux/Tyria-Extractor** | **2026-07-26 `Gw.exe`** — three days before our snapshot | The skill record, the string pipeline, the icon pipeline, skill counts. The most build-current skill-data source we have. |
| **GWCA (live, vendored in GWToolbox 4.7.2.3)** | dependency refreshed **2026-07-14** | Struct layouts, StoC payload structs, the UI-message vocabulary. |
| **GWCA (frozen mirrors)** | GregLando 2023-11-14, JaborGW 2024-11-30 | Implementation code the live copy no longer ships. **Both still say the record is `0xA0`/160 — a pre-2026 figure.** |
| **apoguita / Py4GW** | code written 2026, knowledge **inherited from GWCA** | Its one genuinely independent contribution is a Ghidra-sourced doc (2026-06-01) confirming the `+0x98`/`+0x9C`/`+0xA0` string-id offsets. |
| **gw-preservation** | server active past our snapshot; logger tracks build eras | Methodology and the build-37600 comparison point. Not naming. |
| **ldufr (OpenTyria / Headquarter)** | OpenTyria last touched 2026-02-21, cosmetically | The wire catalogue, the map-entry order, the only cast-lifecycle model in existence. |
| **GWLP-R** | **2013 client** | The property-value vocabulary and the attribute table. Not opcode numbers. |

**Housekeeping consequence for our own repo:** `PLAN.md:239` and
`vault/research/2026-08-04/client-data-tables.md:92` both record `GW::Skill` as
160 bytes. That is the 2023 figure. The current client's record is **164**, and
the three string ids sit four bytes later than those documents say.

### One method not to reuse

`git log --reverse -1` does **not** return a repository's first commit — the `-1`
is applied before the reverse. Used on both GWCA mirrors during this pass, it made
each look like a single-day repository; GregLando's actually runs from 2015-10-03
across 1,555 commits. The staleness conclusions survived, the characterisation did
not. Correct form: `git log --reverse --format=... | head -1`.

---

## 7. What we own, and what we have actually seen

**OBSERVED, and it is a thin list.** Across 127 capture files and 603 distinct
message labels, exactly three skill-adjacent opcodes appear, all sent by **our own
stub server** to our patched client (build 38797) during the map-load handshake:

| Opcode | Label | Payload |
|---|---|---|
| 29 | `PVP_UNLOCKED_SKILLS` | 516 bytes: `1d00` `8000` then 128 zero dwords |
| 24 | `PVP_UNLOCKED_HEROES` | 36 bytes: opcode, count 8, then 8 × `0xffffffff` |
| 27 | `PVP_ITEM_STREAM_END` | 2 bytes, bare header |

Canonical instance: `vault/captures/authsrv/authsrv-20260805T104326-c13.jsonl:15-17`,
session 2026-08-05, recurring in 25 of the 127 files.

**A correction that matters, because it was wrong in the brief for this pass and
in our own notes:** opcode 29's payload is **not** "128 bytes of zero" and it is
not a bitmask *on the wire*. It is `u16 opcode` + `u16 count = 128` + **128 zero
`uint32` words** = 516 bytes. The count-then-array shape matches both OpenTyria's
`skills[]` array and the Go server's marshaller exactly. Anyone implementing
against "a 128-byte bitmask" would produce a malformed message.

**No skill-bar content, no skill use, no skill effect, and no cast has ever
crossed the wire in any session we have recorded** — in either direction. Our
character has an empty bar and every session ends during the early handshake. The
client, for its part, sends nothing skill-related either.

> **[Superseded 2026-08-20.** True when written — every session then ended in the
> early handshake. The live corpus has since grown to 14 captures, and it now
> holds **44 `USE_SKILL` (0x0046) episodes across 7 distinct skill ids**, with
> full activate/recharge/property bookkeeping — §16–§24 below are built on
> them. This sentence kept reading as current for ten days; the correction is
> dated so it cannot again.]

**A caveat on the OBSERVED tier itself.** The bytes in our captures are ours; the
*names* attached to them are OpenTyria's. Our label table matches ldufr's
`opcodes.h` precisely where ldufr disagrees with the rest of the cluster — our
captures label opcode 183 `PLAYER_UPDATE_PROFESSION`, which is OpenTyria's
number, while GWCA and Py4GW both put that message at 182. So "SMSG 29 =
PVP_UNLOCKED_SKILLS" is **observed bytes with a sourced name**, not an
independent observation. Worth stamping the label table with its provenance.

**Stamped, and the label lost, 2026-08-19.** `183` is `AGENT_PROFESSIONS` and
`182` is `AGENT_PROFESSION_BITS` in `schema/overrides.json`, both named from
the client's own code rather than from any lineage's header
([../pvpui/FINDINGS.md](../pvpui/FINDINGS.md) §30), and the server renamed
its constants to match. The OpenTyria names listed above are left as
written: they cite upstream's own source, and are not a claim about retail.

**Reusable infrastructure** for a skills experiment, all opcode-family-agnostic
and none of it skill-specific today: the capture and client-driving harness
(`toolkit/harness/drive_client.py`, `admin.py`, `rawlisten.py`, `tcptable.py`),
the patched-client builder (`toolkit/clientpatch/make_custom_client.py`,
`make_run_dir.py`), the schema importer (`toolkit/schema/import_msgdefs.py`), the
PE reader (`toolkit/gwpe.py`), and the binary scanner
(`toolkit/clientscan/protoscan.py`) — which has never been reported against
skill-related symbols and structurally could surface them.

**A provenance single point of failure worth fixing:** the binding between our
client's SHA-256 (`221c13772c7a`) and its numeric build number (38797) exists
only as prose in `studies/handshake/PLAN.md:82-88`. The snapshot `MANIFEST.json`
has no field for the ArenaNet build number at all.

---

## 8. Open questions

Ordered by how much they would change what we do next.

| Question | What would answer it |
|---|---|
| Does our client accept opcode 218 and draw a real skill? | Put one id in `skills[0]` and look. One session. This is the whole pass's headline experiment and it validates §1 and §3 at once. |
| Does the client require a skill to be unlocked before it will draw it on the bar? | Same session, twice: once with the unlock bit set, once without. NOT FOUND in every source. |
| ~~What actually triggers the cast animation — 228, a property update, or the client's own prediction?~~ | **ANSWERED 2026-08-15: AGENT PROPERTY 60.** And it was answered exactly the way this row said to — send each in isolation and watch. Two caged loopback runs on build 38833, identical in every respect (same bar, same map 90, same hold, the message under test firing at t≈10.85 in both) and differing ONLY in which message followed the bar: `cast_228_only` sent `0x00E4` at the local player and the operator saw **nothing**; `cast_prop60_only` sent property 60 with the same skill id and the operator saw **the cast sparkle on the weapon**. Captures `authsrv-20260815T184213-c1.jsonl` and `authsrv-20260815T184317-c1.jsonl`. So **228 is bookkeeping** — which is what its handler said statically (it compares the named agent against the local player and returns before reaching AgentView) and what the LIVE WIRE independently implied: all 7 `0x00E4` in the live corpus name the receiving connection's own player, so ArenaNet broadcasts it uniformly and relies on that discard (`studies/combat/PLAN.md` §6 step 0a, §16). Three witnesses — handler, wire, screen — agreeing. The row's own guess, client prediction, is refuted: the animation needs a message, and property 60 is it. |
| What is `skill_instance`, the third dword in all three lifecycle messages? | NOT FOUND in every lineage. Only a real capture of a real cast would settle it, and there is no real server. |
| Which of `0x90` and `0x94` is the high-resolution icon? | Tyria-Extractor and GWCA disagree. Decode both file numbers for one skill and compare dimensions. |
| Is the energy encoding really just 11→15 and 12→25? | Two sources assert it, neither measured it, neither tests it. Decode the `0x35` byte for a known 5-energy and a known 10-energy skill. |
| Are opcodes 231 and 232 the missing "skill done" / "instant skill" messages? | They sit immediately after `SKILL_RECHARGED` with the lifecycle shape and have real client handler RVAs. Nobody has named them. |
| What is opcode 211 — a third unlock-list-shaped message? | Same shape as both unlock messages, three slots before the skillbar block, unnamed in every source. |
| Do our client's opcode numbers match ldufr's post-shift table at all? | Only dumping the client's own packet-template table settles it. Everything in §2 is provisional until then. |
| What did the real server send at decimal 123 and 124 during map load? | OpenTyria preserves a capture-derived note that they exist and does not implement them. They sit exactly where the skill block begins. |
| Can `Gw.dat` be written at all? | No tool in our evidence base can. This gates the entire "new skill id" project and is unexplored. |
| Is the dat's file 4102 the same image as the `Gw.exe` we run? | Tyria-Extractor treats them as interchangeable and never says why. Compare hashes. |

The shape of this document is that **§1 is well-evidenced and §4 is not**. We know
where skill data lives with four sources and three methods behind us. We know what
the messages look like from one corpus wearing nine hats. We know how casting works
from a single headless client that models it and a single reference server that
does not implement it at all.

And the one thing we could check cheaply — whether our own client draws a real
skill when we send it opcode 218 — has never been tried.

**Four of these were answered on 2026-08-06 by reading the client's handlers.
See [studies/skillcast/FINDINGS.md](../skillcast/FINDINGS.md).** In short:
`skill_instance` is the bar slot's **copy index** and ArenaNet calls it `copy`
in a log string; **218's second array is not `pvp_masks`**, it fills that copy
field; **231 is "skill disabled" and 232 is a fractional recharge**, neither is
"skill done"; the **cast animation comes from agent property 60**, not opcode
228, whose handler does nothing at all when it names the local player; and
opcode 211 writes a bitmap nothing in the image reads. All of it is static —
SOURCED at best, never OBSERVED — and that study ends with six committed probes
that would settle it against a real client.

---

# OBSERVED, 2026-08-05: the first results measured against our own client

> **This block RESTARTS the section count at 1, so §1–§8 exist twice in this
> document — once above, once below.** Nothing else collides: §9 onward is a single
> run that never resets. **The resolver, and it is what the citations already do:
> a bare §1–§8 means the DESK pass above.** Every one of the nineteen citations
> from outside this document — `studies/profession` ×8, `studies/skillcast` ×4,
> `studies/combat/PLAN.md` ×3, `studies/profession/MODDABLE.md`,
> `WORKAROUNDS.md`, `studies/review` ×2 — resolves that way, and not one of them
> means a section of this block. **This block's own §1–§8 are cited as "§N of the
> 2026-08-05 block"** (or "of this section", which §10 already uses), and the four
> places that needed it now say so.
>
> The numbers themselves are NOT being migrated. `studies/idents/HANDOFF.md`'s
> ★ box rules on exactly this — *"a mass rename of existing tokens is out of scope
> and should be refused... the deliverable is a convention for NEW identifiers plus
> a resolver, not a migration"* — and section numbers here are load-bearing in
> commit messages (`Skills 32.8`, `Isle 8.6`, `§27.4` are all commit subjects).
> A renumber buys a cold reader a few seconds and costs everyone else their index.
>
> **Two bare references in this document are NOT covered by the rule, because the
> sweep could not settle them and guessing is worse than saying so.** §25's
> *"the answer to §8's question"* has three live candidates — this document's desk
> §8, `PLAN.md` §8's old heal-spam item, and `studies/isle` rung 8 — and the
> paragraph cites isle three lines earlier. §36's *"a scope error of exactly the
> kind [§4](#) warns about elsewhere"* was committed with an EMPTY href (`7496fc5`)
> and names no document; neither §4 in this file is about scope. Whoever wrote
> them can close them in a line; nobody else should.

Everything above this line was written without launching a client. This section
was produced by running §3's "concrete first experiment" and then a follow-up,
against build 38797 on our own server. It is the only part of this document
labelled **OBSERVED** — we watched it happen — and where it contradicts what is
above, the observation wins and the earlier text is left in place for the record.

Method: `toolkit/authsrv/authsrv.py` gained a skill block (opcodes 29, 219, 218)
sending eight real Warrior ids read out of this build's own table;
`toolkit/clientpatch/repoint_skill.py` rewrote individual fields of individual
skill rows in a copy of `Gw.exe`. Two launches, three screenshots each. The four
skills used, identified BY the experiment rather than assumed: **316 "To the
Limit!", 317 Battle Rage, 318 Defy Pain, 319 Rush.**

## 1. §3 was right, and its caveats did not bite

**One message put eight real skills on the bar, drawn correctly.** The client
rendered eight distinct icons with correct names, energy costs, adrenaline costs,
recharge times, skill types and attributes — from nothing but eight bare `uint32`
ids in a 75-byte message.

- **`GAME_SMSG_SKILLBAR_UPDATE` = 218 / `0x00DA` is correct for build 38797.**
  So are `UPDATE_UNLOCKED_SKILLS` = 219 and `PVP_UPDATE_UNLOCKED_SKILLS` = 29.
  §3's first caveat — "our opcode numbering has never been validated against our
  own client", `messages.json` carrying `"validated_against_build": null` — is
  now discharged for these three. It remains true for every other opcode.
- **The wire shape is exactly as computed**: 75 bytes at 8/8 against a declared
  79, the two-byte difference per array being the `u16` count the packer writes.
  516 bytes each for 29 and 219.
- **Unlock state was not a gate, or was satisfied.** We blanket-set 128 words of
  `0xFFFFFFFF` precisely so it could not be a confounder, so §3's open question —
  whether the client refuses to draw a locked skill — is still **NOT FOUND**. It
  is now cheap to answer: send the bar with an empty bitmap and look.
- **Ordering:** we sent the unlock lists BEFORE the bar, where upstream sends the
  bar first. It worked. Whether upstream's order also works is untested.

## 2. The icon question is settled, and every source we have is wrong

§1 recorded this as **CONTESTED**: Tyria-Extractor documents `+0x8c` as the
standard icon and `+0x90` as high-resolution; GWCA names `+0x8c` `icon_file_id`
and `+0x94` `icon_file_id_hi_res`; GWToolbox is not self-consistent across its
own three call sites.

**MEASURED: the skillbar draws `+0x90`.**

Three skills were repointed at Rush's art, one variable each, with real Rush in
the adjacent slot as the reference:

| Slot | Skill | Field changed | Result |
|---|---|---|---|
| 1 | 316 | `+0x8c` only | **unchanged** |
| 2 | 317 | `+0x90` only | **became Rush's icon** |
| 3 | 318 | both | became Rush's icon |
| 4 | 319 | none | reference |

The field every source calls the standard or primary icon has no effect on the
bar. An earlier, messier run agreed once the result is known: a slot with only
`+0x8c` changed did not move, and a slot with both changed did.

**What this does not say.** `+0x8c` is populated in 3,439 of 3,443 rows and pairs
one-to-one with `+0x90`, so it is certainly *something* — plausibly the icon used
somewhere we did not look (skill list, hero panel, a different UI scale). All
that is established is the bar, at this resolution. `+0x94` remains untested and
is populated in only 86 rows.

**Consequence for re-skinning: a borrowed icon needs `+0x90`, and repointing
`+0x8c` alone does nothing visible.**

## 3. Descriptions are templates, and the numbers come from the target row

§1 states this from two lineages; it is now watched. Skill 322 was given 318's
name/concise/description string ids and nothing else:

| | real Defy Pain (318) | 322 wearing Defy Pain's text |
|---|---|---|
| tooltip | Elite Skill. **(20 seconds.)** You have **+90** maximum Health, +20 armor, and take **-1** less damage. (Attrib: Strength) | Melee Attack. **(0 seconds.)** You have **+10** maximum Health, +20 armor, and take **-0** less damage. (Attrib: Strength) |

Same template, different numbers — the placeholders were filled from **322's own**
`duration`/`scale`/`bonusScale` fields, not the donor's. `+20 armor` is literal
text in the template and is identical in both, which is the control.

The same held for Rush: id 323 wearing Rush's text printed *(2 seconds)* from its
own `duration0 = 2`, where real Rush prints *(8 seconds)* from its own `8`. Its
attribute line read Tactics — 323's own `+0x29` — against Rush's Strength.

**So text and numbers are completely independent.** The skill type word ("Melee
Attack" vs "Elite Stance"), energy, adrenaline, recharge, attribute and every
scaling endpoint stayed with the target row while the prose came from the donor.

## 4. Which numbers render green, and why

The owner noticed that a cloned Defy Pain showed **one** attribute-scaled (green)
value where the real one shows **two**, and asked whether "number of raisable
values" is a skill property. It is, and it is `skill_arguments` at **`+0x58`** —
GWCA's comment reads "1 duration set, 2 scale set, 4 bonus scale set", and it is
a bitfield.

But the bit alone is not the rule. MEASURED:

| id | `args` | sets enabled | rank-0 → rank-15 | green |
|---|---|---|---|---|
| 318 Defy Pain | 7 | duration, scale, bonusScale | 20→20, 90→300, 1→10 | **2** |
| 322 clone | 2 | scale | 10→40 | **1** |
| 316 "To the Limit!" | 7 | duration, scale, bonusScale | 10→20, 10→60, 1→6 | **3** |
| 319 Rush | 1 | duration | 8→20 | **1** |

**A value renders green when its set is enabled AND its two endpoints differ.**
Defy Pain's duration is enabled but constant at 20→20, so it prints without being
green — which is exactly the missing second green number.

**[OBSERVED/CORROBORATED] 2026-08-14 — this table is now reproducible by a
script, and a third witness agrees with all of it.** For two days these four rows
were the only reading of `+0x44`..`+0x68` in the repo and **nothing here could
regenerate them**; `skilltable.py` decoded exactly one field inside the window
(recharge, `+0x4C`). It now decodes the whole window as u32 — `duration0/15`
(`+0x44`/`+0x48`), `skill_arguments` (`+0x58`), `scale0/15` (`+0x5C`/`+0x60`),
`bonus_scale0/15` (`+0x64`/`+0x68`) — and reproduces every number above
byte-exact (`test_skilltable.py` §7, which also asserts the green rule rather
than leaving it as prose). `+0x50` stays **NOT FOUND**: neither upstream source
names it and nothing here resolves it.

The third witness is GWW, crawled 2026-08-14, which shares no author, code or
ancestry with either the client binary or Tyria-Extractor's spec. Every endpoint
its `{{Skill progression}}` templates list matches (§8):
WIKI (GWW, "Defy Pain", rev. 2026-08-14) `+ Maximum health` 90→300 and
`Damage reduction` 1→10, with duration absent from the progression because the
description says a flat "For 20 seconds";
WIKI (GWW, `"To the Limit!"`) `Max foes` 1→6, `Duration` 10→20,
`+ Max health` 10→60; WIKI (GWW, "Power Attack") `+ Damage` 10→40;
WIKI (GWW, "Rush") `Duration` 8→20.

**Rush is the row that proves the bitfield is load-bearing.** Its scale slot
holds **25** — the constant in "move 25% faster" — with its scale bit CLEAR, and
the wiki lists no scale progression for it. A decode that read endpoints and
skipped `skill_arguments` would invent a green the game does not draw, so the
test checks both directions: every listed endpoint must match, and no unlisted
set may render.

## 5. Two corrections to §1

**The adrenaline conversion is not a division.** *(Superseded by §10 below, which
settles it as `ceil(raw/25)` and walks back the overstatement in this
paragraph's original heading — the 25-unit figure is correct and is corroborated
by an independent source; only the division was wrong. Left in place because the
reasoning here is what motivated the probe.)* §1 records, from
Tyria-Extractor and with a unit test behind it, that `adrenaline` at `+0x38` is in
internal units of 25 per displayed strike. Three observations refute the division:

| skill | raw `+0x38` | client displayed | raw/25 |
|---|---|---|---|
| Battle Rage (317) | 80 | **4** | 3.2 |
| Rush (319) | 80 | **4** | 3.2 |
| Defy Pain (318) | 120 | **5** | 4.8 |

Both `ceil(raw/25)` and `floor(raw/25)+1` fit all three; they diverge only on
exact multiples of 25 and none of these is one. The table holds 18 distinct
non-zero values (20, 25, 50, 60, 75, 80, 100, 120, 125, 130, 140, 150, 160, 175,
200, 220, 240, 250) and they are not all multiples of 25, so the clean-division
model was never going to hold. **One observation of a skill whose raw value is an
exact multiple of 25 would discriminate.** §1's own warning that this field is
"CLIENT-DATA, uncorroborated by measurement" was well placed.

**The elite border is `special` (+0x10) bit `0x4`, not part of the icon.** When
two elite skills had their icons repointed to a non-elite skill's, they kept
their golden borders. MEASURED: `special == 0x00000004` for Battle Rage and Defy
Pain, `0x00000000` for "To the Limit!" and Rush.

## 6. What this means for §5, "New skill, or re-skinned id?"

§5's honest summary says a re-skinned skill's tooltip "will lie, because the
client renders the shipped text", and lists name, description and icon under
"what the server cannot touch" with **No** in every row.

That is still true **of the server**. It is not true of the project, because we
already patch the client binary for the Diffie-Hellman key, and the same patcher
can repoint a skill row's string ids and icon file ids at any other skill's:

| Property | Server can change? | PE repoint can borrow? |
|---|---|---|
| Name | No | **Yes** — observed |
| Concise / full description | No | **Yes** — observed |
| Skillbar icon | No | **Yes**, via `+0x90` — observed |
| Energy, adrenaline, recharge, activation | No | yes, though untested here |
| Attribute, profession, type, elite flag | No | yes, though untested here |
| Numbers filling the description | No | they follow the row, not the text |

**A re-skinned skill's tooltip no longer has to lie.** Its name, its prose and its
bar icon can all be borrowed from any of the ~1,300 shipped skills, with no
`Gw.dat` write, no injected DLL and no new content — only the client patching this
project already performs. What cannot be borrowed is text that no shipped skill
contains, and that is where `studies/datwrite/FINDINGS.md` picks the story up.

## 7. Where this leaves the caveats §3 raised

| §3 caveat | Status |
|---|---|
| Opcode numbering never validated | **discharged** for 218/219/29 on build 38797 |
| Skill id must exist in the client's table | held; ids were read from the table itself |
| Client updates its own skillbar without waiting for the server | not contradicted, and not separable here — but the bar was empty until we sent 218, so the server message is doing the work |
| Not every row is a player skill | avoided by filtering on profession and icons |
| `pvp_masks[]` unexplained | still **NOT FOUND**; eight zeros worked |

## 8. Reproducing this

```bash
python toolkit/authsrv/authsrv.py --skills 316,317,318,319,320,321,322,323
python toolkit/clientpatch/repoint_skill.py --show 318
python toolkit/clientpatch/repoint_skill.py --target 316 --donor 319 --fields icon2
```

`repoint_skill.py` never writes in place by default, refuses anything under
`C:\gw`, locates the table structurally rather than by address, and cross-checks
the result against ArenaNet's own `ConstSkill.cpp` / `arrsize(s_skill)` strings
sitting immediately after the table. The run dir keeps `Gw.exe.pre-repoint` as
the pristine patched binary; the firewall cage is scoped to the literal path
`…\Gw.exe`, so a repointed build must be swapped over that name rather than run
under its own, or it runs uncaged.

## 9. The unlock bitmap gates the skill picker, not the skillbar

§3 left this **NOT FOUND**: *"Whether the client refuses to draw a bar skill that
is not unlocked is NOT FOUND — no source states it either way."* The first pass
side-stepped it by blanket-setting all 4,096 bits, exactly so it could not be a
confounder.

**Probe.** Same eight skills on the bar; unlock bitmap with **four** bits set —
316, 318, 320, 322, which are slots 1, 3, 5, 7. An alternating pattern was chosen
because it is unmistakable at a glance and cannot be confused with "the bar failed
to load".

**OBSERVED: all eight icons drew.** The unlock state did not suppress a single
one. What it did control was the **Skills and Attributes panel** (`K`), which
listed exactly the four unlocked skills and nothing else, grouped by attribute:

| Panel entry | shown cost | id | matches the row |
|---|---|---|---|
| Defy Pain (Strength) | 5 adrenaline | 318 | attr 17, adren 120 |
| Power Attack (Strength) | 5 energy / 3 recharge | 322 | attr 17, energy 5, recharge 3 |
| Hamstring (Swordsmanship) | 5 energy / 10 recharge | 320 | attr 20, energy 5, recharge 10 |
| "To the Limit!" (Tactics) | 5 energy / 10 recharge | 316 | attr 21, energy 5, recharge 10 |

**The division is clean and it is the useful one: bar contents are the server's,
the unlock list is the player's.** A server can place any skill on any bar
regardless of unlock state; the bitmap decides only what the player may pick for
themselves. For a private server this means the unlock list is optional
scaffolding, not a gate to be fought.

One inconsistency worth recording: the panel's own eight-slot strip along its top
rendered **empty** while the action bar below it was full. That widget filters by
unlock state and disagrees with the bar it is supposed to mirror.

> **Corroborated from the binary, 2026-09-19:
> [studies/templates/FINDINGS.md](../templates/FINDINGS.md) §5.** The template
> window's decoder (`0x0091CB90`) makes calls to exactly five functions in its
> whole body — the bit reader and three const-table getters — and neither it nor
> its closure reaches the thread-context getter, with a control that does. So
> "unlock state does not gate display" is now measured statically as well as on a
> live client, from a different path. What that decoder *does* gate on is a
> per-skill **loadable** byte (`s_skill + 0x33 == 1`) and profession membership,
> neither of which is account state; §47.3's `GmSkSlot` equip validator remains
> the one place the account unlock set is load-bearing.

**A free side effect: unlocking a skill names it.** The panel prints the resolved
name, cost and attribute for every unlocked id, which is a way to identify skills
without decoding a single text record. Four ids were named this way, and the
tooltips named three more: **316 "To the Limit!", 317 Battle Rage, 318 Defy Pain,
319 Rush, 320 Hamstring, 322 Power Attack.**

**Attribute bytes, MEASURED** from those four against `+0x29`: **17 = Strength,
20 = Swordsmanship, 21 = Tactics.** §1's warning against importing OpenTyria's
attribute enum stands; these three are ours.

---

## 10. The adrenaline field is a threshold, not a strike count

§1 records, from Tyria-Extractor and with a unit test behind it, that `adrenaline`
at `+0x38` is "in internal units, 25 per displayed strike". §5 of this section
earlier called that refuted. **That was an over-correction, and this is the
settled version.**

The **unit is right**. The Guild Wars Wiki's *Adrenaline* page states the mechanic
directly: *"You gain 25 units of adrenaline (=one strike) each time you
successfully hit an opponent with a weapon"*, and *"all other skills lose one
strike (25 units) of adrenaline"*.

What was wrong is treating it as division. **`+0x38` holds a threshold in units,
and the displayed cost is the number of strikes needed to reach it:**

```
displayed adrenaline cost = ceil(raw / 25)
```

That is why the field is not always a multiple of 25 — 11 of the 18 distinct
non-zero values in the table are not (20, 60, 75, 130, 140, 160, 220, 240 among
them). A threshold can sit anywhere; the strike count rounds up.

**The probe.** Both `ceil(raw/25)` and `floor(raw/25)+1` fit the three skills
observed in §5 of this block, because they diverge only on exact multiples of
25 and none of those three was one. A bar was built from four Warrior skills
whose raw values *are* exact multiples, so the two rules predict different
numbers in every slot:

| Slot | id | raw `+0x38` | `ceil` predicts | `floor+1` predicts | **OBSERVED** |
|---|---|---|---|---|---|
| 1 | 1142 | 25 | 1 | 2 | **1** |
| 2 | 357 | 100 | 4 | 5 | **4** |
| 3 | 329 | 150 | 6 | 7 | **6** |
| 4 | 336 | 200 | 8 | 9 | **8** |
| 5 | 317 Battle Rage | 80 | 4 | 4 | 4 |
| 6 | 318 Defy Pain | 120 | 5 | 5 | 5 |
| 7 | 319 Rush | 80 | 4 | 4 | 4 |

Four for four for `ceil`, and the three controls — where both rules agree —
reported unchanged, so nothing else moved between runs. `floor(raw/25)+1` is
dead.

**A note on the wiki as a source.** It does not fit this document's existing
labels. It is community documentation of observed retail behaviour, which for a
*player-visible* mechanic is strong evidence and is genuinely **a separate lineage
from every code source in `vault/mirrors/`** — unlike the ldufr/GWCA cluster,
which shares an author and counts once. For *internal* representation it is weak:
it says nothing about `+0x38` being a threshold, and it could not have. Here the
two halves are complementary rather than redundant — the wiki supplied the game
mechanic, the client supplied the encoding, and neither alone would have produced
`ceil(raw/25)`.

---

## 11. Everything §3 left open, as of this pass

| Question | Status |
|---|---|
| Are opcodes 218 / 219 / 29 right for our build? | **Answered** — yes, build 38797 |
| Does the client refuse to draw a locked skill? | **Answered** — no; unlocks gate the picker |
| Which of `+0x8c` / `+0x90` / `+0x94` does the bar draw? | **Answered** — `+0x90` |
| How does raw adrenaline map to the displayed cost? | **Answered** — `ceil(raw/25)` |
| Are descriptions templates filled from the row's own numbers? | **Answered** — yes |
| What decides how many values render green? | **Answered** — `args` (+0x58) ∩ endpoints differing |
| Where does the elite border come from? | **Answered** — `special` (+0x10) bit `0x4` |
| What is `pvp_masks[]` for? | still **NOT FOUND**; eight zeros worked throughout |
| What is `+0x94` for? | still **NOT FOUND**; 86 rows carry it, none tested |
| Does upstream's message ordering also work? | untested — we sent unlocks before the bar |

---

# OBSERVED, 2026-08-20: the DURATION slot, read because the server had to send one

The effect substrate (`toolkit/authsrv/effects.py`, R4b) needed one number the
table does not hand over cleanly: **how long does this skill's effect last?**
§4 of the 2026-08-05 block answered which values *render green*; this is about
which values are *real*, which turns out not to be the same question. Three
findings and one corroboration, all from the 1,333-skill player corpus plus
the 102 `0x0042` applies in the live captures.

## 12. `skill_arguments` bit 1 means the duration SCALES, not that the slot is meaningful

§4 of the 2026-08-05 block established that a value renders green when its
`args` bit is set **and** its endpoints differ, and that reading endpoints
without the bit invents a progression the game never draws — Rush's scale slot
holds a constant 25 with its bit clear. `authsrv.skill_scale_value` therefore
**raises** on a disabled set, which is right for the scale.

**It is too strong for the duration, and retail says so.** Skills **984 (Torch
Enchantment)** and **998 (Torch Hex)** have `skill_arguments = 0` — the duration
bit CLEAR — endpoints 30/30, and **ArenaNet sent `0x0042` with duration 30.0 for
both**. A server that honours the bit the strict way cannot reproduce two of
retail's own applies.

So the bit is about the **progression**, and the slot is about the **value**.
The two coincide for the scale (a scale with no progression has no meaning of
its own) and come apart for the duration (a fixed-duration skill still has a
duration). `effects.resolve_duration` splits them, and every branch it permits
names a retail witness while every branch it refuses names its zero:

| shape | n (of 1,333) | rule | witness |
|---|---|---|---|
| bit SET | 618 | interpolate `lo..hi` at the rank | 160, 364, 348, 814 |
| bit CLEAR, `lo == hi == 0` | 488 | no duration → `None` | — (nothing to send) |
| bit CLEAR, `lo == hi`, below the sentinel floor | 148 | the flat value | **984, 998 at 30.0** |
| bit CLEAR, `lo == hi`, at or above it | 30 | **REFUSE** | none — see §13 |
| bit CLEAR, `lo != hi` | 49 | **REFUSE** | **none, in 102 applies** |

The last row is the honest one. Forty-nine skills carry two differing endpoints
with the bit clear and **not one of them appears anywhere in the corpus**, so
there is no evidence for *either* reading — interpolate anyway, or take one
endpoint? The module raises rather than returning a plausible number.

## 13. The duration slot carries SENTINELS, and they are an enum in the high word

Of the 666 bit-clear skills with equal endpoints, **30 hold a value that is not a
second count**:

| value | hex | n | what they mostly are |
|---|---|---|---|
| 131,072 | `0x20000` | 22 | Enchantment |
| 196,608 | `0x30000` | 7 | Enchantment / Signet |
| 999,999 | — | 1 | Spell |

**24 of the 30 are Enchantments**, which is exactly where a *"maintained until
removed"* marker belongs — a maintained enchantment has no duration, so its slot
is free to carry something else. `0x20000` and `0x30000` are 2 and 3 in the high
word, i.e. an enum, not a magnitude; 999,999 is the other spelling of forever.

**Vital Blessing (289) is one of them, and it is on our own enemy's bar**, so
this refusal fires in every session this server runs. That is deliberate: the
alternative is putting **36 hours** on the wire as a duration. ~~What the enum
*means* is **NOT FOUND**~~ — **`0x20000` is now NAMED as energy upkeep, §13.1
below.** The module still keys on the SHAPE (high word set, floor `0x10000`)
rather than on the specific values, because the floor is what a server must
refuse to send as a duration whatever the value means.

**A follow-up with a clean answer available:** the client draws "Enchantment
Spell" and a maintained-enchantment tooltip from *somewhere*. Whatever reads
`0x20000` is the same kind of anchor `s_attrib`'s accessors were for the item
modifiers (`studies/itemmods` §2), and it would name the enum rather than leave
it as a floor.

### 13.1 The follow-up ran, and `0x20000` is ENERGY UPKEEP — ArenaNet's own word (2026-08-22)

The anchor is where §13 said it would be: the client reads the skill record's
duration slot and the tooltip control names the value. **OBSERVED, static, no
client launched.** `GmCtlSkCard.cpp` — the skill card — reads `[esi+0x44]`
(the duration slot; `esi` is a skill record, confirmed by the same function
testing its flags at `+0x10`) at `0x008CC4EC` and **exact-compares it to
`0x20000`** at `0x008CC4EF`. The branch's own assert is ArenaNet's word for
it: **`!(hasEnergyUpkeep && skillData.healthSacrifice)`** (`GmCtlSkCard:462`,
`0x008CC501`), with a second witness in `GmCtlSkListEntry.cpp`. So:

- **`0x20000` = energy upkeep** — a maintained enchantment, whose duration
  slot is free because it lasts until removed and drains energy per second
  instead. All **27** skills in the full 3,443-row table carrying `0x20000`
  are type 6 (Enchantment Spell), zero exceptions. This is the marker §13 was
  after. Its name in the repo is `effects.DURATION_ENERGY_UPKEEP` /
  `effects.sentinel_name`, and `resolve_duration`'s refusal now names it.
- **`0x30000` is NOT the other half of an enum.** §13 read "2 and 3 in the
  high word" from a 30-row corpus subset; the full table has **367** skills of
  **16 different type codes** carrying `0x30000`, mostly duration-bit-clear, and
  **none of the image's fifteen `0x30000` compares is fed by a `+0x44` read**.
  It is the duration slot's default filler for a skill with no fixed duration,
  not a marker the client branches on here.
- **`999999` is never compared anywhere in the image** — a "forever" magnitude
  the arithmetic passes through, confirming §13's "the other spelling of
  forever" and that it is not an enum value.

The refinement that matters: `0x20000` is a real, client-read marker (name it
upkeep); `0x30000`/`999999` are not, and the "high-word enum" framing was half
right. What upkeep MEANS for the server — a per-second energy drain until the
enchantment is cancelled, not a timed episode — is a mechanic for whenever
maintained enchantments are modelled, and the sentinel now carries its name to
that day. `toolkit/clientscan/test_skillsentinel.py` pins all of the above
against the client's own bytes.

## 14. `target` (+0x31) is a target-TYPE enum, and the type column corroborates two of its codes

The substrate needs to know whether a stance lands on the caster or on what the
caster is aiming at. `target` answers it, and the answer is checkable without
trusting any single skill, because `type_code` is an independent column:

| type | n | target distribution |
|---|---|---|
| Attack (14) | 199 | **5 → 199/199** |
| Stance (3) | 76 | **0 → 75/76** |
| Glyph (12), Preparation (19), type 16, 20, 21, 24, 26, 27 | 117 | **0 → 117/117** |
| Hex (4) | 151 | 5 → 140, then 0/1/16 |
| Enchantment (6) | 227 | 0 → 151, 3 → 52, then 1/4/5/6/14 |

An attack necessarily aims at a foe and a stance necessarily lands on the
caster, so **0 = self and 5 = the cast's target** is read off the type column
rather than asserted about any one skill. The one Stance at 5 and the three
Hexes at 0 are not explained here and are not needed.

**Codes 1, 3, 4, 6, 14 and 16 are UNRESOLVED.** ~~3 is plainly ally-shaped~~
**RESOLVED 2026-09-10 (SKILLS-RC, §45.3): 3 = ally (the caster is legal), 4 =
other ally (the caster is not), CORROBORATED on eleven skills against GWW's
targeting words; 1, 6, 14 and 16 stay unresolved.** The paragraph below stands
as written on 2026-08-20: 3 is plainly ally-shaped (52
Enchantments and Reversal of Fortune 307 carry it) and 4 is *also* ally-shaped
(Restore Condition 276), which is one distinction too many to guess at — so
`effects.effect_recipient` reads only 0 and lets everything else fall through to
what the caster aimed at. Known-wrong-but-bounded, rather than an invented enum.

## 15. And a corroboration of somebody else's finding, at corpus scale

`studies/isle/FINDINGS.md` rung-8 prep §2 settled **`0x0042`'s field 3 = the
applying skill's attribute RANK** on 2026-08-18, CORROBORATED against GWW across
five values and four skills. Running the same prediction over the **whole**
corpus with the client's table on the other side of the join:

> `interp(duration0, duration15, field3)` == the f32 duration on the wire, for
> **96 of 96 non-condition applies, 0 misses**.

No free parameter — the endpoints are ArenaNet's, the formula was measured at
`0x005A8920` for the *damage* scale, and field3 and the duration are retail's
bytes. This is not a new finding; it is that finding mechanised, in
`test_effects.py` §2, guarding a rule the server now depends on.

**Worth recording because of what it says about the repo rather than the game:**
`bufflog.field3_report`'s docstring still read *"the answer is one session away"*
for two days after the answer was written down in another study. That is the
fourth time in one week a measured number sat unread beside code using an
invented one — property 17, the rung-7 damage formula, the item modifiers, and
this — and all four failed the same way round: measured, written down, not
wired.

## 16. The client DRAWS them — run `20260820T174731`, and it types them itself

Everything above is offline. This is the client.

**The run.** Loopback, `--enemy --explorable`, the bar's slot 1 swapped to
**Frenzy 346** with the existing `--skills` flag (no code edit), one scripted
keypress on slot 1, 18 s of walk plan and a 60 s hold at a frame every 4 s.
`vault/captures/harness/20260820T174731`, contact sheets `hud-walk-frenzy.png`
and `hud-hold-hex.png`. **13 applies, 13 removals, zero client asserts, run
verdict PASS.**

**Both directions worked, and the whole chain is on record for the player's:**

```
key "1" -> c2s 0x8046 USE_SKILL -> 0x00E4 -> 0x00E5 (cast end)
        -> 0x0042 EFFECT_APPLY(stance 346 on agent 1, buff 3, 8.0s at rank 0)
        -> ... 8s ... -> 0x0044 EFFECT_REMOVE(buff 3, expired after 8.0s)
```

and the enemy's, needing no input at all:
`0x0042 EFFECT_APPLY(hex 253 on agent 1, buff 1, 18.0s at rank 12)`.

**THE CLIENT TYPES THE EFFECT ITSELF, FROM THE SKILL ID.** We send no colour,
no category and no art — `0x0042` carries `[target, skill, rank, buff,
duration]` and nothing else. The client drew Frenzy's own icon under a **GREEN**
border and Scourge Sacrifice's under a **MAGENTA** one, which are GW's stance
and hex colours. So the whole `type_code` taxonomy §14 reads out of the table is
something the client already knows per skill id, and a server that gets the id
right gets the category, the art and the tooltip for free.

**The timer bar is real and it drains on OUR number.** Frenzy is the row §12 is
about — `skill_arguments = 0`, endpoints 8/8, the duration bit CLEAR — so the
strict reading of the bitfield would have refused to send anything. Frames
`w002` (21:48:04) and `w003` (21:48:08) show its green bar shortening, and by
`w004` (21:48:11) **the icon is gone**: applied ~21:48:03, an 8-second
progression bar, gone at 8 seconds. The flat branch is right and the client
agrees with it on screen.

**Expiry lands inside retail's own band.** Our residuals were **+0.03, +0.05 and
+0.03 s** against the stated duration, on a world tick. The corpus's shoulder is
83 of 88 closes within 50 ms (`bufflog.EXPIRY_TOLERANCE`), so our lateness is
inside the spread retail itself produces.

**The death strip is visible.** `hold001` and `hold006` are the two death
frames: no icons at all, while `hold002`-`hold005` carry the hex with its bar
draining. Three episodes came off in one `stripped 3 effect(s)` and the client
took all three without complaint.

### 16.1 The run found a gap, the fix was wrong, and the corpus said so

**What the run showed.** The server opened **four concurrent episodes of skill
253 on the same agent** — the Hatcher re-casts every ~5 s and nothing stopped it
— and **the client never drew more than ONE hex icon.** A second run
(`20260820T175507`, frames every 2 s) pinned the client's side precisely: its
timer bar drains **monotonically** across three re-applications, from ~85% to
~28% over 8 seconds of an 18-second duration. **A repeat `0x0042` for a live
(agent, skill) is DISCARDED — no second icon, no reset.**

**The obvious fix was made and is now reverted.** Collapsing to one episode per
(agent, skill), refreshing in place, looked well-supported: the client's single
icon, plus `buff_id_report`'s peak of 2 concurrent episodes. A prediction was
stated before the run that tested it — *re-sending `0x0042` with the EXISTING
buff id resets the bar* — and it was **REFUTED**: the bar drained straight
through three same-id refreshes.

**Then the corpus refuted the collapse itself.** Asked directly whether retail
ever re-applies a live effect:

> **15 overlapping re-applications** across the live captures — a second
> `0x0042` for the same (target, skill) while the first is still live — and
> **every one carries a NEW buff id**: 120→121 at a 0.43 s gap, 110→114 at
> 0.50 s, 121→120 at 0.09 s. The first episode still closes `expired` against
> its own duration. Same-id repeats occur **only** after the previous one
> closed (51→51 at 14.98 s against a 13.0 s duration, five times over).

So ArenaNet's allocator is the plain one we already had, and collapsing would
have made our stream a shape retail never produces. `test_effects.py` §4b now
pins retail's rule instead of our fix.

**Which relocates the actual defect, and it is more interesting than a channel
bug.** Retail's fifteen overlaps are all **under 0.5 s** apart — same-instant
doubles, an AoE or a party-wide effect touching one target twice — and **not one
is a re-cast of a live effect.** Ours were five seconds apart. The thing no
monster in the corpus does is what *our* monster does:

> **our placeholder AI re-casts a hex the target already has.** `pick_skill`
> asks only whether a slot has recharged.

That is an **AI rule**, not a wire rule, and `pick_skill`'s own docstring
already says it is "a testing function, not a decision about AI" that "gets
replaced rather than extended". So it is recorded there and left alone. It also
lands exactly where `studies/heroes` §5.6 said this arc would end up: *"do not
use this skill if the target is already affected"* is precisely the sort of
condition GWW publishes **per skill**, which is R4c's open design question, not
a line to add to a round-robin selector.

**Left standing, and named:** how retail refreshes an effect at all is **NOT
FOUND**. Re-sending the apply does nothing (measured, both id choices).
`0x0044`-then-`0x0042` would certainly work and there is no evidence retail does
it. The question only becomes live when something in this server needs to extend
a running effect, and nothing does yet.

**NOT ANSWERED by this run, and named so it is not read as answered:**

1. **Whether an ADRENALINE skill can be pressed at all.** The default bar's two
   stances (Battle Rage 317, Rush 319) cost 4 adrenaline and nothing tells the
   client the player has any, so slot 1 was swapped to the 5-energy Frenzy to
   sidestep it. Whether the client greys an uncharged adrenaline skill and
   swallows the keypress is untested, and it is the cheapest reason to model
   adrenaline.
2. ~~**What the enchantment sentinel means** (§13).~~ **ANSWERED, §13.1: it is
   ENERGY UPKEEP** (`GmCtlSkCard.cpp`'s `hasEnergyUpkeep`). Vital Blessing
   refused on every cycle of this run, loudly, exactly as designed — and the
   refusal now names the value. Modelling upkeep (an energy drain until the
   enchantment is cancelled, not a timed episode) is the remaining work, and it
   is combat-mechanic work, not a naming gap.
3. **Whether the effect does anything.** Frenzy's icon appeared; Frenzy's
   *+33% attack speed and double damage taken* are not modelled, and neither is
   Scourge Sacrifice's. The channel is the substrate; the per-skill mechanics
   are the `scale_means` pattern again, one wiki-sourced row at a time.

---

# OBSERVED, 2026-08-20 (later): five more families, and three rules the wiki had all along

§16 left the substrate carrying icons with no consequences and five of the nine
R4b families unreached. This pass closed most of that. Everything below was
measured before it was built, and three of the five were then watched at a
client.

## 17. The type list is corroborated by the table, and Glyph joins it

Adding a `type_code` to the effect list is a claim about ArenaNet's taxonomy, so
it wants a check the table can refuse. Across the **478** corpus skills in the
five effect types:

| type | n | duration resolves | refuses (sentinel/unwitnessed) | **no duration** |
|---|---|---|---|---|
| Stance (3) | 76 | 74 | 2 | **0** |
| Glyph (12) | 10 | 9 | 1 | **0** |
| Preparation (19) | 14 | 13 | 1 | **0** |
| Hex (4) | 151 | 142 | 9 | **0** |
| Enchantment (6) | 227 | 194 | 33 | **0** |

**Not one of the 478 has nothing to time.** Meanwhile **488** corpus skills DO
carry 0/0 endpoints — attacks, signets, most spells — and **none** of them is in
these five types. If "this type IS a timed effect" were the wrong mapping, the
giveaway would be a type full of skills with no duration, and there is none.

## 18. THREE of the five types are ONE-AT-A-TIME, and two say so in the game's own words

This is the answer to §16.1's open question — *how does an effect get replaced* —
and it was sitting on GWW the whole time:

> **Stance** (rev. 2020-10-23), quoting **Isokeh, Expert Ranger**, in game:
> *"Only one Stance can be active at any time, so if you are under the effects
> of a Stance, using a new Stance will replace the previous one."*
> **Preparation** (rev. 2020-06-18): *"Only one preparation can be active at a
> time. Activating another preparation will override the previous one."*
> **Glyph** (rev. 2024): *"If a glyph is cast while another glyph is already
> active, the new one replaces the old one."*

The rule is per **TYPE** and per **AGENT** — any stance replaces any stance —
and hexes and enchantments carry no such rule, which is why they are not in it.

**On the wire a replacement is `0x0044` then `0x0042`.** That is forced rather
than chosen: §16.1 measured that re-sending the apply alone is discarded by the
client under either buff id, so a replacement the client can see has to close
and reopen. **WATCHED** (`20260820T190616`, `hud-stance-swap.png`): Rush's icon
became Frenzy's **in the same slot, under the same green stance border**, with a
fresh timer, and there was never a third icon.

## 19. Property 55 is the HEALING channel, and the client's own arithmetic agrees

The server had no way to make health go up that drew anything — `GV_HEALTH` is a
silent setter. Asked directly, the corpus answers in one pass over 2,007
property events on `0x00A3`:

| property | negative | positive | self-directed (`target == cause`) |
|---|---|---|---|
| 16 (damage) | **1251** | 0 | **0 of 1251** |
| 17 (critical) | **243** | 0 | **0 of 243** |
| 55 | 4 | **502** | **454 of 506** |

Damage always has a distinct attacker and victim and is always a negative
delta — `_damage_fraction` already sent `-frac`, which turns out to be retail's
convention 1,251 times over. **A positive, overwhelmingly self-inflicted health
delta on the damage channel is a heal.** GWCA's name `armor_ignoring` therefore
describes the *mechanism* (a health change armour has no say in) and not the
*direction*; the four negatives are consistent with a sacrifice and that reading
is UNVERIFIED.

**CONFIRMED AT THE CLIENT** (`20260820T190917`, `hud-heal-54-to-100.png`). The
client's own health readout reads **54 → 100 → 54 → 100** across three Healing
Signet casts, moving by exactly the **46** the server sent each time. The client
applies property 55 as a health gain and its arithmetic matches ours.

**And it draws no number for it** — a green-text scan over twenty frames
spanning three heals finds **0–8 saturated green pixels**, the 8 being frames
taken at the keypress instant before the cast completed. Damage on 16/17 *is*
drawn. So either retail annotates a heal through some other value id, or the
client simply does not, and this repo cannot yet say which. **OPEN**, and named
rather than assumed away.

## 20. A spell is not a swing, and a label does not say *when*

Two defects the tests could not have caught, both found by running it:

- **Casting a HEX made the player swing a hammer.** `cast_tick` dispatched on
  *"is there a target"*, so Faintheartedness produced
  `attack_started: player swings at 10` and five points of hammer damage.
- **Flare dealt that same five** instead of its own 20 fire damage, because
  only the `additive` mode was ever read and `standalone` fell on the floor.

Both are fixed by dispatching on `type_code`: **only type 14 rides a weapon
swing** (WIKI, GWW "Attack skill" — attack skills *are* attacks and use the
equipped weapon; all 199 in the corpus carry target byte 5). A spell deals its
own number with no roll, no armour exponent and no critical, and sends **one**
message — no `attack_started`, no `melee_attack_finished`, because it never
began a swing.

**And the label trap that would have shipped without the type column:** GWW
gives `Ignite Arrows` the variable **`Fire damage` 3..18** — the same label as
Flare's. It is a Preparation, and its fire damage rides the *next arrows*.
Nothing in the client's table separates them. So a skill that opens an episode
resolves no damage and no heal at cast: its scale describes what the effect does
while it is up.

## 21. Conditions: the join, and the rule that they never stack

`studies/isle` established that a condition's duration comes from the
**inflicting** skill (Burning's own endpoints are 3/3 and retail sends it at
9.0). The missing half was *which* condition and *from where*, and both are
per-skill data already carried:

> **GWW's progression variable NAMES it** — `Sever Artery` has exactly one
> variable and it is called `Bleeding` — and **the client's bonus slot carries
> the seconds**, 5..25, in the slot `skill_arguments = 4` names. **The bitfield
> picked the slot before the wiki was read.**

Sever Artery at Swordsmanship 3 resolves to **Bleeding (478) for 9 s**, and the
apply names the *condition's* id rather than the skill's — which is what retail
carries, since the corpus's six condition applies name 480 and 481 and never the
skill that caused them.

**Then a run put five Bleedings on the player at once.** With the enemy's Sever
Artery on a 0 s recharge (`20260820T191725`) the pips went 3 → 6 → 9 → **10, the
cap** — twenty health a second, and visibly absurd. The rule was on GWW:

> **WIKI (GWW, "Condition" §Notes):** *"Reapplied conditions will last the
> original time period, unless the reapplied duration is greater than the
> remaining amount of time."*

So one instance per (agent, condition), and a re-application is a **comparison**,
not an addition. A shorter one is a no-op on the wire as well as in the table —
nothing about the target changed. A longer one **extends** it, as `0x0044` then
`0x0042`, which is the one replacement shape the client honours.

## 22. What a condition DOES — property 44, and one clause of B4 closed

`studies/isle` B4 CONFIRMED property 44 as the net health-regeneration rate in
max-health fractions per second, quantised at 2/H, riding **`0x00A2`** — itself a
correction to `PLAN.md` §3.3, which had it on `0x009F` (*"the value census
matches §3.3 exactly; the opcode did not"*). It left exactly one clause open:

> *"Still UNVERIFIED: that one 2 hp/s step equals one HUD pip (needs a screen,
> not the wire)."*

The pips are GWW's — *"each pip represents a loss of two health per second"*,
**Bleeding 3, Burning 7, Disease 4, Poison 4**, capped at 10 — and the other six
conditions degenerate nothing, which is a fact rather than a gap. So Bleeding on
a 100-health player must be **exactly** `-3 × 2 / 100 = -0.06` per second, with
no free parameter on either side.

**CONFIRMED AT THE CLIENT** (`20260820T192221`, `hud-degen-three-pips.png`),
and it closes B4's clause. The client drew **exactly three `‹` arrows** on the
health bar, and its own displayed health fell **100 → 86 → 72 → 58 → 44** across
frames **2.32 s** apart — an implied **6.03 health/s against the 6.00 the server
sent**, three times over. Three pips asked for, three pips drawn; 0.5%
agreement on a rate neither side was tuned to.

**Health stays server-authoritative and the ticks are silent**, which is B4's
own conclusion: *"passive ticks are never streamed"*. The server sends the RATE
once, on change, and spends the health without a single property-16 message —
a tick that also sent damage would draw a stream of red numbers retail never
draws. The client's 6.03 is that animation, done by the client from one number.
The expiry sends the rate back to zero, which is the half a server is most
likely to forget: the icon goes and the arrows stay.

---

# OBSERVED, 2026-08-20 (third pass): ENERGY has a complete wire model — and ADRENALINE has no wire at all

The energy recon ran as five parallel read-only censuses over the 14-capture
live corpus (13,378 property-channel messages, 49 connections, every one
decoding to its final byte), the pinned build-38797 client table, and the
2026-08-20 harness frames. Everything below is theirs plus two checks run by
the orchestrator; scratch scripts are named in the session log.

## 23. Energy rides four properties, and its quantum is f32(0.33) — not one third

Energy has **no dedicated opcode**. It rides the same generic property channel
as health, on the **no-target** variants only (0x009F int, 0x00A2 float —
never once on 0x00A0/0x00A3, whose only populated float properties remain
{16, 17, 55}; energy bookkeeping has no victim field because it is always
self-directed):

| property | channel | n (live corpus) | what it is |
|---|---|---|---|
| **41** | 0x009F int | 97, values {20, 22, 25, 30} | **MAX energy**, sent as the same (1, real) on-create pair as health’s 42 |
| **43** | 0x00A2 float | 52 | **regen RATE**, fraction of max per second, sent once on change — never periodic |
| **62** | 0x00A2 float | 45, all negative | **discrete SPEND**: −(energy_cost / max), once per completed cast |
| **52** | 0x00A2 float | 1 | **discrete GAIN**: the one witness is a resurrect, value exactly 1.0 |
| 33 | any | **0** | the candidate absolute setter: **NOT FOUND**, positive control green (34/44/52/55/62 all found by the identical scan) |

**The rate’s quantum, settled bit-exactly.** The corpus carries exactly five
nonzero prop-43 values. Three candidate formulas were tested against the raw
f32 bit patterns; only one reproduces all five:

| observed f32 | = f32(f32(0.33)·pips/max) | GWW armor row |
|---|---|---|
| 0.032999999821186066 | 2 pips / 20 **or** 3 / 30 (degenerate) | Warrior base — or caster before armor |
| 0.03959999978542328 | 3 / 25 | Ranger (+1 pip, +5e) |
| 0.04400000348687172 | 4 / 30 | caster basic armor (+2, +10) |
| 0.052800003439188004 | 4 / 25 | Dervish/Assassin (+2, +5) |
| 0.06000000238418579 | 4 / 22 | 4 pips over a death-penalty max |

The nominal rule — WIKI (GWW, "Energy" §Regeneration, rev 2026-03-15): *"Each
pip of Energy regeneration generates 1 Energy every 3 seconds"* — predicts
p/(3m), which matches **zero of the five** bit patterns. The wire’s constant is
**0.33 held in single precision**, not one third: `f32(0.33) × pips ÷ max`,
rounded once more to f32. Same class of result as health’s 2/H quantum
(isle B4), and the (pips, max) pairs are **exactly GWW’s basic-armor table
rows** — an independent join nobody tuned.

**The denominator is the CURRENT max, and one agent proves it by dying.**
Capture `20260817T183756`, agent 27: max 25, rate 0.0528 (= 4 pips/25). At
t=353.299 one batch carries the death bit (0x00F1 effects=16), prop 41 re-sent
**22**, prop 42 re-sent **102** — 102 is 120 × 0.85 exactly, a death-penalty
hit to the maxima — and **prop 43 driven to 0.0**: regen stops at death. At
t=363.343, 10.044 s later: death bit clears, **prop 43 = 0.06 = the same 4 pips
over the NEW max 22**, **prop 52 = 1.0** and prop 55 = 1.0 — a resurrect
refilling both pools in one instant. Four properties, one mechanism, retail
bytes. (One recon agent initially read the 25→22 as a *current*-energy spend;
the 42=102 co-occurrence in the same death batch settles it as the maxima.)

**Prop 62 is −cost/max, validated against the client’s own table with zero
exceptions.** All **45** spends in the corpus, **8 distinct skills** (105, 153,
364, 394, 780, 783, 814, 858) over three pool sizes, every one predicted
exactly from `skills.toml`’s own energy column — skill 364 ("Charge!") alone
22 times across 6 connections, always −0.25 = 5e over max 20 (the control: a
fixed denominator of 20 misses 18 of 45 across the other pools). It fires
**once** per cast, 0.03–0.7 s after `USE_SKILL` (mostly ~0.05 s), and **the
spend precedes the property-60 that names the skill in the same batch, 45 of
45** — measured because a stream-order join first scored 18 of 45 by hanging
each spend on the previous cast. **Zero-cost casts send nothing** — 0 of the
observing agent’s 44 free casts carry one. **And prop 62 is scoped to the
agent whose orb is on screen**: a 2×2 with two empty cells — the observing
player’s agent spends on 45 of 45 paid casts and 0 of 44 free ones, while
**722 casts by OTHER agents (579 of them paid) carry not one spend** — so a
server must not emit 62 for its NPCs, and ours does not. The client sends
nothing energy-shaped in the other direction: `USE_SKILL`’s four payload
fields never carry a quantity. (An earlier count in this section read 44
episodes over five skills — that was the c2s `USE_SKILL` join, which sees only
connections whose client half decodes; the s2c activation join above is the
wider net and the shipped oracle enforces its numbers.)

**The client does not predict a deduction.** Two 2026-08-20 harness runs
(`20260820T190210`, `20260820T190917`): eight presses including Flare — 5e in
retail — and the energy bar sat at 25 in every frame while health visibly
re-rendered 54→100→54 in the same frames. Our server has never had a prop-62
call site (`GV_ENERGY_SPENT` defined, zero uses), so the flat bar is the
measurement: **energy display waits for the server**. The client does zero the
orb at death client-side — and leaves it 0 after revive, because our revive
path sends no energy property where retail sends 52=1.0 + 43=rate. That is a
falsifiable prediction for the next run: emit the resurrect pair and the orb
should refill.

**Closed in passing:** `studies/isle` §9 item 6’s "skill 364… no measurable
effect" — it had one, −0.25 max-energy on prop 62 at the exact flagged
timestamp (t=1008.125, capture `20260818T132739`), a channel damagepass.py
never reads. And `content/world.toml`’s `float_43 = 0.0396` — gw-preservation’s
"REVERSE THIS MORE" constant — is now **measured**: it is f32(0.33)·3/25, the
Ranger armor row, and the identical bit pattern appears in capture
`20260810T235916` on four connections. `studies/profession/RESKIN.md` §24.1’s
counts (52: never observed; 62: n=6) were true against its twelve-capture
corpus and are superseded by this one — addendum written there.

## 24. Adrenaline: the table carries the threshold, the wiki carries the rules, and the wire carries nothing anyone has named

**The client table’s +0x38 is raw units and it is the USE threshold.** §10
measured the field (80/120/80 for Battle Rage/Defy Pain/Rush, displayed
strikes = ceil(units/25)); GWW’s own "Battle Rage" Notes: *"exactly requires
80 units… 3 strikes and 5 units"*. `skills.toml` now carries it per row as
`adrenaline_units` (extractor extended this arc).

**The rules — WIKI (GWW, "Adrenaline", rev 2026-07-02), player-visible tier:**

- Gain **25 units (= one strike) per successful weapon hit** on an opponent —
  weapon hits, not spell damage. Multi-hit attack skills grant one per hit.
- Gain **1 unit per 1% of maximum health lost** to damage, **floored** (sub-1%
  grants nothing), counted before damage reduction.
- **Each adrenal skill has its own pool; all pools grow simultaneously.**
- On USE: the used skill’s pool resets to zero and **every other skill loses
  one strike (25 units)** — *"whether or not the skill is interrupted or it
  fails"*.
- **All adrenaline is lost on death, or after 25 seconds of non-combat** (no
  attack landed, no damage taken — zero damage does not count as combat).

~~**And the wire is silent.**~~ — **SUPERSEDED 2026-08-21 by §26: the wire was
never silent, it was UNNAMED.** Four GAME_SMSG opcodes carry adrenaline — 207,
208, 209, 210 (`0x00CF`–`0x00D2`) — and 724 of them are sitting in this same
live corpus. The paragraph below is kept verbatim because every sentence in it
is *true as written*, and the shape of the miss is the lesson: this section
searched the sources for the WORD, and no source anywhere has it, so a source
survey could not have found the channel and a corpus scan with no name to look
for did not either. The second horn of the disjunction below is the right one,
and what settled it was the client's own receive table, not any source.

**And the wire is silent.** `schema/messages.json` names no adrenaline message.
GWCA’s `Opcodes.h` names none. GWCA reads `adrenaline_a/b` out of **client
memory** (`SkillbarSkill`, +0x00/+0x04), not out of a packet it maps. The
warrior melee sessions in the live corpus surface no adrenaline-shaped
property. So either the client animates its own icons from combat it can
already see — it watches its hits land and its health drop, and it holds the
unit costs in its own table — or the channel hides in an unmapped opcode.
~~UNRESOLVED~~ — **answered the same evening, §25**: the harness put Sever
Artery on the bar, landed nine hits, and the icon never moved. The client
does not self-animate adrenaline; the display waits for a message nobody has
mapped. The server tracks the pools authoritatively regardless.

## 25. The client consumes all of it — four runs, 2026-08-20 evening

The substrate landed at `b7512bb` (gate, debit, regen, adrenaline pools,
death/revive emissions) and four loopback runs measured what the client does
with each message. Predictions were written before the first launch
(session scratchpad, `run-predictions.md`); every P below names its verdict.

**E1 (`20260820T230059`) — the debit and the climb.** The first property-62
any client has ever received from this server. Fifteen frames, every one
reconciled against the server's own logged pool plus 0.99 e/s times the gap:
**the client displays floor(its own integration of max + rate + debits)** —
including the two frames that discriminate floor from round (server 22.56 →
client **22**; 23.5 → **23**) — and the climb between messages runs at
exactly the prop-43 rate. Fourteen frames sit on exact press-time anchors;
the fifteenth (24 at ~+2 s) is consistent within the one press whose time is
estimated. P1 CONFIRMED, P2 CONFIRMED (the client animates the rate, as it
does for health). **And the energy bar draws THREE `›››` arrows — the 3-pip
rate, rendered** — with a control: at death (E3) the rate goes to 0.0 and the
orb empties outright. One pip-quantum, one arrow, the energy twin of isle
B4's health-pip result.

**E2 (`20260820T230849`) — the refusals, and the answer to §8's question.**
A 25-energy skill (863) drained the pool 25 → 0.00 in one cast, and the
recovery staircase came back **5 → 11 → 17 → 22 → 25** across ~6 s frames —
~1 e/s, the sent rate, from near-empty. Then the two refusals: with 7.70
energy the client **SENT** the 25-energy `USE_SKILL` anyway, and with 0
adrenaline it **SENT** the `0x8027` attack-skill press —

> **The client does not swallow an unaffordable press, and it does not grey
> the slot for affordability** (the darkening our first read saw was the
> SELECTED-SKILL gold border moving between slots). Against our server, the
> gate is the SERVER's, both halves. P3/P5 answered: no client-side gate
> fired. What retail's server answers a refused press with — ours answers
> with silence, and the client visibly re-animates the pressed slot for
> ~10 s afterwards — is a new open question; retail players see a "Not
> enough Energy" feedback that has to come from somewhere.

Also observed: the practice target died to THREE Power Attacks (they hit
for ~41, not the ~19 the walk plan assumed), which is why this run's Sever
charge stopped at 75 units — the fourth swing hit a corpse. And the
**25-second non-combat wipe fired live**: `the player's adrenaline is gone`.

**E3 (`20260820T231700`) — death and the resurrect pair.** The enemy killed
the player; the kill batch carried `energy regeneration stops` (43 = 0.0,
the retail death shape) and the client emptied the orb with the health. Ten
seconds later the revive sent the retail resurrect pair — **52 = 1.0 then
43 = rate** — and **the orb refilled on screen** (frame 23:17:44 empty,
23:17:50 full). Yesterday's runs left that orb at 0 forever; this was
property 52's first render on any client, ours or theirs. P8, P9 CONFIRMED.
Bonus: the post-revive Sever press was refused at **46 units accumulated
purely from taking hits** — the 1-unit-per-1%-health-lost rule visibly at
work with zero swings landed.

**E4 (`20260820T232138`) — the full adrenaline cycle.** Nine landed
auto-attack swings (each +25, pool capped at its 100-unit cost), then:
`skill 382 spends 100 adrenaline; every other pool loses a strike` →
`EFFECT_APPLY(Bleeding on agent 10, buff 1, 9.0s, inflicted by skill 382 at
rank 3)` — charge, spend, cross-pool tax and the condition landing through
the effect substrate, one unbroken chain. The immediate re-press proved the
reset: `needs 100, has 75` — exactly three post-spend swings' worth. P6
CONFIRMED.

**P7 REFUTED, and the negative is the finding: the client does NOT charge
the adrenal icon from observed combat.** (EXPLAINED in §26 and INVERTED
in §27: nothing was filling `adrenaline_b` because no `0x00CF` had ever been
sent. With one, the same rig fills the same slots and the controls stay at
zero. The refutation stands exactly as written — it was a true statement
about a client nobody had sent the message to.) At a server-side pool of 100 —
charged, accepted, spent — Sever's slot rendered pixel-identical to its
0-unit state (E4 frames w001 vs w002/w003; the gold ring in w004 is press
feedback, present for refused and accepted presses alike). The dark icon at
zero units matches GWW's description, but the flames-creeping-up display is
fed by the client's own adrenaline store (GWCA's `SkillbarSkill.adrenaline_a`,
+0x00) — and **no source anywhere maps the message that fills it**: not
schema/messages.json, not GWCA's `Opcodes.h` (GWCA reads it from client
MEMORY). Finding that opcode is now a named clientscan target: what writes
`SkillbarSkill.adrenaline_a`, and which RECV handler reaches it.

**ANSWERED 2026-08-21, §26 — and the refutation STANDS, now with a mechanism.**
Four RECV handlers write that store and nothing else does; our server sent none
of them, so there was nothing for the icon to draw. The target question was also
better than it knew: `adrenaline_a` (+0x00) is an ACCUMULATOR, and the icon does
not draw from it at all — it draws from `adrenaline_b` (+0x04), a deferred
commit of the first. Two things this run could not have known are now on record
for whoever re-runs it: the fill is drawn only while the map state is
`MISSION_MAP_GAME`, and the bar is a continuous fraction of the skill's RAW
cost, not a count of strikes.

# OBSERVED, 2026-08-21 (fourth pass): adrenaline HAS a wire — four opcodes

§25 ended with a named target: *what writes `SkillbarSkill.adrenaline_a`, and
which RECV handler reaches it.* This is the answer. It took the route every hard
question in this repo has taken — read the client's own receive table, then
check the reading against ArenaNet's own traffic — and it went to the binary
first precisely because §24 had already proved the sources were exhausted.

**What §24 got wrong, and it is worth naming before the evidence.** §24 searched
for the *word* and concluded the wire was silent. The word is not there: no
reimplementation in the vault names an adrenaline message, and the client itself
never names one either. But the channel was in `schema/messages.json` the whole
time, as four unnamed layouts. A survey keyed on a name cannot find a thing
nobody named. §24's second horn — *"or the channel hides in an unmapped
opcode"* — was the right one.

Static work is on the **pinned pristine build 38797**. No client was launched
for this pass, nothing was patched, and the live corpus was read and not written.

## 26. The adrenaline family: `0x00CF` gains, `0x00D0` clears, `0x00D1` sets, `0x00D2` spends

### 26.1 The four messages

MEASURED. Shapes are `msgshape.py`'s **recovered** descriptors, not
`msghandler.py --table`'s — the cmd slots in the static image read
`['0xcf', '0x0', '0x0']` because a load-time initializer fills them, and citing
the static view for a shape is how a reader gets a confidently wrong answer.
Every one of the four agrees byte-for-byte with the layout `schema/messages.json`
already carried, so naming them changed no field list; that is proved rather
than asserted in §26.10.

| opcode | hex | recovered shape | wire | worker | what the handler does | live |
|---|---|---|---|---|---|---|
| **207** | `0x00CF` | `[agent_id, u32]` | 10 B | `0x00821980` | adds `units` to every eligible slot, capped at that skill's cost | **663** |
| **208** | `0x00D0` | `[agent_id]` | 6 B | `0x00821B00` | zeroes both halves of all 8 slots | **22** |
| **209** | `0x00D1` | `[agent_id, u16, u32, u32]` | 16 B | `0x00821B70` | writes `units` to one slot, both halves | **0** |
| **210** | `0x00D2` | `[agent_id, u16, u32]` | 12 B | `0x00821C00` | used skill → 0, every other occupied slot −25 | **39** |

Names are in `schema/overrides.json` as `AGENT_ADRENALINE_GAIN` / `_CLEAR` /
`_SET` / `_SPEND`. **Every one of those names is INFERRED** — no ArenaNet string
names any of these four messages. What is SOURCED is the *store* they write
(§26.7); the verbs are our summary of what each handler does.

**The dispatch chains, and why they cannot be mis-read.** MEASURED, one link at
a time, `codescan.py --xrefs` on each:

```
  RECV table 0x00BC8F68
    207  stub 0x0091F3F0 -> thunk 0x00814500 -> worker 0x00821980
    208  stub 0x0091F410 -> thunk 0x00814520 -> worker 0x00821B00
    209  stub 0x0091F430 -> thunk 0x00814540 -> worker 0x00821B70
    210  stub 0x0091F460 -> thunk 0x00814570 -> worker 0x00821C00
```

Each of the eight downstream functions has **exactly one direct caller in the
image**, so there is no branch anywhere in the chain to have taken wrongly.
Every thunk does the same two things: `mov ecx,[eax+0x2C]` then `add ecx,0x6F0`
— the per-agent skill-bar container that ArenaNet's own assert calls
`hotKeyState` (`ChCliSkill.cpp:718`, the same container opcode 100's override
row already named). A record is 0xA4 bytes: eight slots of stride 0x14 starting
at record+4, ending at record+0xA4. The bound is SOURCED too —
`ChCliSkill.cpp:124` asserts `hotKey < arrsize(hotKeyState->hotKey)` on the
accessor's slot index.

Slot layout, as the four handlers use it:

| offset | field | who touches it |
|---|---|---|
| +0x00 | `adrenaline_a` — the accumulator | 207 adds, 210 decrements, the deferred commit reads |
| +0x04 | `adrenaline_b` — the display copy | 208/209/210 write; the commit writes; **the only half any accessor exposes** |
| +0x08 | recharge | 207 reads it as a gate |
| +0x0C | skill id | matched by 209 and 210 |
| +0x10 | skill copy | matched by 209 and 210 |

### 26.2 The charging loop, read instruction by instruction

MEASURED at `0x00821980`. Five rules, and each one is a single instruction pair
rather than an inference:

1. **Walk exactly eight slots.** `0x008219AD lea ebx,[eax+0xA4]` (the end) and
   `0x008219B5 lea esi,[eax+4]` (the first), stepped `0x008219F1 add esi,0x14`.
2. **Skip a RECHARGING slot.** `0x008219C0 cmp dword [esi+8],0 / jne` — a skill
   whose recharge is nonzero takes no adrenaline at all. This is a rule the wiki summary
   in §24 does not carry, and the client enforces it.
3. **Skip an EMPTY slot.** `0x008219C6 mov eax,[esi+0xC] / test eax,eax / je`.
4. **Skip a NON-ADRENAL skill.** `0x008219CE call 0x005A88B0` resolves the skill
   row (`imul eax,esi,0xA4` + base `0x00988ED0`, bound `0xD73` = 3443 rows), then
   `0x008219D6 movzx ecx,word [eax+0x38] / test cx,cx / je`. Zero cost, no charge.
5. **Add, then CAP at the skill's own cost.** `0x008219DF mov eax,[esi]` /
   `0x008219E1 add eax,[ebp+0xC]` / `0x008219E4 cmp ecx,eax / jb / mov ecx,eax` /
   `0x008219EA mov [esi],ecx`. That is `slot = min(cost, slot + units)`.

`0x008219EC mov edi,1` sets a *something-gained* flag, and **if no slot took the
units the handler returns having done nothing** — no event, no queue entry, no
repaint. Everything is UNSIGNED: `0x00CF` cannot express a loss, and a server
that wants one has to send `0x00D0` or `0x00D2`.

**The 25.0f is a constant, not the amount.** On any gain the handler posts UI
event `0x10000058` carrying `fld dword [0x009495B4]` — MEASURED as raw bytes
`0000c841` in `.rdata`, i.e. `25.0f`, a fixed literal. It is **not** the
message's `units` field. Anyone reading that `fld` as "the amount gained" would
get 25 for a 3-unit gain; the amount reaches the store through `[ebp+0xC]` and
nowhere else.

### 26.3 The deferred `a`→`b` commit, and why the split exists

MEASURED. After the loop, 207 appends the agent to the array at `ctx+0x6E0` and
schedules deferred task `0x00820DD0`. That task pops the front entry, re-finds
the record, and runs `0x00820E84 mov ecx,[eax]` / `0x00820E86 mov [eax+4],ecx`
across all eight slots — `adrenaline_a` → `adrenaline_b` — then posts
`0x10000059`, the repaint.

**This is a deferred-commit double buffer, and the asymmetry is the evidence.**
`+0x00` is written by the arithmetic and read by almost nothing; `+0x04` is
written by every handler that wants an immediate repaint and is the only half
the accessor exposes (§26.4). `0x00CF` alone routes through the queue — 208, 209
and 210 write **both** halves inline and repaint on the spot, which is exactly
what you do when the value is already final and you are not batching.

**How hard that claim was checked.** `codescan.py --xrefs 0x00820F10` says the
record lookup — the only direct path to a slot in the image — has **25 direct
call sites**, and every one falls inside a single contiguous stretch of `.text`,
`0x00820E6E`–`0x008230AB`, whose asserts are `ChCliSkill`'s. All 25 were
disassembled. Within that bound, a slot's `+0x00` is:

- **computed** at exactly four sites — `0x008219EA` (207's capped add),
  `0x00821B30` (208's zero), `0x00821BD7` (209's set), `0x00821C7E` (210's
  decrement);
- **cleared wholesale** by the skill-bar load path, which memsets the whole
  0x14-byte slot (`call 0x0046DBF0`, `ecx` = slot base, `edx` = 0x14) — so
  loading a bar drops adrenaline as a side effect;
- **moved wholesale** by two five-dword slot copies (`0x008224A4`,
  `0x00822861`), which relocate a slot without computing anything;
- and **read to compute with** at three sites only: 207's own `add`, the
  deferred commit, and 210's decrement.

That is a bounded search, not a census, and the bound is what makes it
refutable: anything reaching a slot without going through `0x00820F10` is
outside it. Naming the bound is deliberate — `studies/enemy/PLAN.md` §6o once reported a
scope-limited search as a global absence and closed a question for a session
with a false sentence.

**A FIFTH AND A SIXTH writer exist, and neither is one of these four.**
*(Corrected 2026-08-21: this said FIFTH. Opcode **229** `0x00E5`
SKILL_RECHARGE is a sixth — worker `0x00822B90`, reached via stub
`0x0091F690` and thunk `0x00814920`, whose matched-slot body zeroes both
halves at `0x00822C00`/`0x00822C06` in a sequence **byte-identical** to
231's before writing the recharge timestamp at `0x00822C41`. It was missed
here because this section's bounded search asked which sites COMPUTE a
value into `+0x00`, and a constant zero computes nothing. The bound was
stated honestly and still hid a writer — worth keeping as the example.)*

**And the fifth:** Opcode **231**
(`0x00E7`, `[agent_id, u16, u32]`, 12 B — the same shape as 210) reaches worker
`0x00822D10` via stub `0x0091F6E0` and thunk `0x00814980`, matches one slot, and
zeroes **both** adrenaline halves (`0x00822D7C`, `0x00822D82`) before setting the
recharge field to `0xFFFFFFFF` and posting a second event. It is almost
certainly a *skill disabled* message and this pass is **not naming it** — one
handler read is not enough, and 231 has its own evidence to gather. It is
recorded here because any model of this store that lists four writers is already
wrong.

### 26.4 The display path ends at an `fdiv` — and it is the RAW cost, with no quarters

MEASURED, and this is the correction §25 could not make.

`ChCliApi 0x00816EF0` is the adrenaline accessor. It returns
`[record + 0x14*slot + 8]` — computed as `lea eax,[esi+esi*4]` /
`mov eax,[edi+eax*4+8]` at `0x00821081`, which is slot base **+0x04**, the
display copy. It has **exactly one direct caller in the entire image**
(`codescan --xrefs`, zero aligned words holding the VA): `GmSkSlot 0x00542E78`.

That caller fetches the display half, fetches the cost beside it, and posts both
to one control:

```
00542E78  call 0x816EF0                  ; adrenaline_b for this slot
00542E7D  mov  [ebp-8], eax
00542E80  movzx eax, word ptr [esi+0x38] ; the skill row's adrenaline cost
00542E84  mov  [ebp-4], eax
00542E8D  push 0x59                      ; -> Controls::SkillImage, payload {b, cost}
```

`GmCtlSkImage 0x008C6112` receives message `0x59`, and its arithmetic is the
whole answer:

- `0x008C6140 cmp eax,ecx / jb` — if `adrenaline_b >= cost`, the fraction is
  never computed and a different, fully-charged visual is used;
- otherwise both values are converted as **unsigned** (`fild` plus the
  `fadd [0x93c1d8]` = `4294967296.0` fixup for a set sign bit) and
  `0x008C6188 fdiv` divides them;
- the quotient is forwarded as message `0x56`.

**So the fill is a continuous fraction of the RAW unit cost.** There is no
division by 25 anywhere on this path and no quantisation to quarters. A 3-unit
gain on a 100-unit skill sends the control `0.03`, not zero — what the control
then *draws* with that number is one hop further than this pass traced, and the
run in §26.11 item 6 is what would settle it. §10's `ceil(units/25)` is still
right for the *number printed on the skill card*; it has nothing to do with the
fraction on this path.

**And it corrects a claim of ours.** `PLAN.md` (~line 1384) says the display
store is `SkillbarSkill.adrenaline_a (+0x00)`. **That is wrong** — the display
store is `+0x04`. Note what is *not* being corrected: `Py4GW_Reforged` reads
`adrenaline_a` as the live value and that is also right, for a different
consumer. A bot wants the accumulator, which is current the instant the message
lands; the screen shows the committed copy, which lags by one deferred task.
The two readings are complementary, not contested.

### 26.5 What retail actually sends — the census

MEASURED by this session over the live corpus: `vault/captures/live` holds **14**
capture directories, **10** of which carry a decrypted game channel; those ten
hold **49 GAME_SMSG connections** and **114,985 messages**, every connection
decoding to its final byte with zero framing errors (`tape.decode_all` refuses a
partial decode, and the pooling rule refuses any connection whose `origin` is
not `live`).

| opcode | n | payload distribution |
|---|---|---|
| 207 | **663** | `25` ×631; sub-25 gains ×32: `{3:6, 4:12, 5:1, 6:5, 7:1, 8:3, 11:4}` |
| 208 | **22** | — |
| 209 | **0** | — |
| 210 | **39** | skill ids `{382: 20, 384: 11, 385: 8}` |

**Self-scoped, 9 of 9.** Every connection that carries a 207 names **exactly one
agent id**, and that id equals the same connection's own opcode-218
`SKILLBAR_UPDATE` agent. Zero mismatches, zero multi-agent connections. The nine
connections sit in three captures and show only four distinct ids —
`{7, 11, 13, 25}`, with two connections in one capture both naming `11` — which
is what a per-instance agent handle looks like, not four agents being tracked.

**This REFUTED an earlier draft of this same pass**, which read the four
distinct ids as evidence that retail broadcasts adrenaline for other agents'
bars. It does not. Adrenaline is scoped exactly like energy property 62
(§23): a server emits it only for the agent whose own UI shows the value, and
ours must not emit it for NPCs.

**Two amount populations, and only one of them has a reading with evidence.**
The `25`s are OBSERVED as a value, and 25 units per landed weapon hit is exactly
the first of the two WIKI gain rules §24 already records. The 32 sub-25 gains
are also OBSERVED as values, and the obvious reading is §24's second rule — one
unit per 1% of maximum health lost, floored — which would make
`{3,4,5,6,7,8,11}` percentages of a health bar.
**That reading is INFERRED and nothing joins it to health traffic yet.** The
join is cheap and specific and has not been run: for each sub-25 gain, find the
health property on the same agent within the same batch and test
`units == floor(100 · damage / max_health)`. Until somebody does that, the
population is a set of small integers that is *consistent with* a rule, which is
what coincidence also looks like.

**209's zero is a result, not a gap.** A fully implemented live handler that
retail never used in anything this repo has captured — the same shape of finding
as energy property 33 (§23), also implemented, also never sent. It is why 209 is
filed at `medium` while its three siblings are `high`.

### 26.6 The map-state gate, and what it does to probe design

MEASURED, and this changes how the next run must be set up.

`GmSkSlot 0x00542E43` calls `MissionCliGetMap` (`0x0084D9B0`, which returns
`missionCtx[+0x238]`), then `0x00542E48 cmp eax,1` / `0x00542E4B jne`. On the
`jne` path the control is sent message `0x59` with a **NULL payload**
(`0x00542E9F push 0 / push 0`) — the overlay is not merely left stale, it is
torn down.

The enum values are SOURCED from ArenaNet's own asserts and the branches they
guard, not guessed:

- `MsCliApi.cpp:251` asserts `context->map == MISSION_MAP_GAME` guarding
  `cmp dword [esi+0x238],1` → **`MISSION_MAP_GAME == 1`**;
- `QuestLog.cpp:261` asserts `MISSION_MAP_OUTPOST == MissionCliGetMap()`
  guarding `test eax,eax / je` → **`MISSION_MAP_OUTPOST == 0`**.

**So a perfectly correct 207 sent while the client sits in an OUTPOST produces a
pixel-identical icon.** Any probe of this family has to be in an explorable or a
mission, and a null from an outpost run means nothing at all — it is a check
that cannot fail, which is not a check. (This does **not** explain §25's P7:
that run's icon stayed dark because nothing had written the store at all, our
server having sent none of these four. The map gate is a *second* requirement
the next run has to satisfy, not a re-reading of the last one.)

### 26.7 ArenaNet's own words

SOURCED. Four assert sites carry the word, and two of them do real work:

| site | expression | what it settles |
|---|---|---|
| `ChCliSkill.cpp:84` @ `0x00820DEB` | `context->skillAdrenalineUpdateArray.Count()` | names the whole deferred chain **adrenaline** |
| `GmCtlSkCard.cpp:409` @ `0x008CC42D` | `!(energyCost && skillData.adrenaline)` | guards `cmp word [esi+0x38],0` |
| `GmCtlSkListEntry.cpp:185` @ `0x008D377A` | `!(energyCost && skillData.adrenaline)` | guards `cmp word [edi+0x38],0` |
| `GmCtlSkImage.cpp:1483` @ `0x008C61F4` | *"Clearing the adrenaline timer on a skill image is currently not supported. Bug Austin about this."* | the control drawing `0x59` is the adrenaline control, in ArenaNet's own words |

The middle two are the load-bearing pair. **`word[skillRow+0x38]` IS
`skillData.adrenaline`, at two independent sites in two different source
files** — which promotes `toolkit/clientscan/skilltable.py`'s `adrenaline_units`
from our name for the field to *the client's own*. §10 measured that field and
called it a threshold; ArenaNet calls it `adrenaline`, and both are true.

Two more entry-guard asserts pin field 2 of the two matching handlers as
`skill`: `ChCliSkill.cpp:442` at `0x00821B85` (209) and `ChCliSkill.cpp:463` at
`0x00821C16` (210), each guarding a `test` on that argument. The row lookup's
own bound assert is at `ConstSkill.cpp:3833`, and it names the table `s_skill`.

A caution the tooling itself prints: `asserts.py` reads 19,758 sites and knows
it is short by at least 373 more it cannot pattern-match, so **"no assert names
X" from that tool is a floor, not a census.** Nothing above depends on an
absence.

### 26.8 Adrenaline costs are NOT all multiples of 25

MEASURED over all **3,443** rows of build 38797's skill table (base VA
`0x00988ED0`, stride 0xA4). **151 rows carry a nonzero cost:**

```
20:1   25:2   50:6   60:1   75:10   80:20  100:24  120:20  125:2
130:5  140:5  150:20  160:5  175:5  200:21  220:1  240:2   250:1
```

Nine of the eighteen distinct values are **not** multiples of 25. So **the pool
must be modelled in raw units** — 25 is the gain per weapon strike, not the
quantum of the bar — which is what `pools.py` already does and what §26.4's
`fdiv` independently requires.

**A latent width disagreement, recorded before it bites.** The client reads
`+0x38` as `movzx WORD` at both `0x00542E80` and `0x008219D6` — 16 bits.
`skilltable.py` (~line 198) reads it as `u32`. On build 38797 the high word is
**0 on every one of the 3,443 rows** (measured), so nothing is wrong today and
nothing needs changing today. But the widths disagree, and if a future build
ever parks a flag in that high word, our decode silently inflates a cost by
65,536× while the client ignores it.

### 26.9 No upstream names any of this — with positive controls

**NOT FOUND**, and searched with a control green in every file so the negative
means something (`feedback: a negative needs a positive control`). Six opcode
tables across five lineages:

| lineage | file | `adrenalin` | `0x00CF`–`0x00D2` | control |
|---|---|---|---|---|
| GWCA (maintained, gwdevhub) | `Dependencies/GWCA/.../Opcodes.h` | 0 | none | `0x00D9` found |
| GWCA (GregLando113) | `Include/GWCA/Packets/Opcodes.h` | 0 | none | `0x00D9` found |
| GWCA (JaborGW) | `Include/GWCA/Packets/Opcodes.h` | 0 | none | `0x00D9` found |
| Headquarter | `code/client/opcodes.h` | 0 | none | `0x00D9` found |
| OpenTyria | `code/opcodes.h` | 0 | none | `0x00D9` found |
| Py4GW_Reforged_Native | `include/GW/common/opcodes.h` | 0 | none | `0x00D9` found |

The control matters: all six tables share build 38797's numbering (`0x00D9` /
`0x00DA` are the skillbar pair in every one, and our own census joined 207
against opcode 218 successfully), so their silence is silence about *these*
messages and not about some other build's.

**Three lineages DO carry the four shapes, and every one of them leaves the
messages unnamed.** This is the strongest corroboration in the section and it is
worth spelling out, because none of it was taken from anybody — the shapes were
derived from the client's own recovered descriptors and *then* compared:

- `gw-preservation/network-log-explorer` (`Constants.ts`) lists cmd arrays for
  `0x00cf`–`0x00d2` that match ours **cmd for cmd**: `[0x0010, 0x0404]`,
  `[0x0010]`, `[0x0010, 0x0204, 0x0404, 0x0404]`, `[0x0010, 0x0204, 0x0404]`.
  Its *name* map, in the same file, skips straight from `0x00CD` to `0x00D9`.
- **`sgwlpr` and `GWLP-R` predate this numbering, and finding them required
  correcting for the shift.** Their skill block sits **12 lower** than ours —
  GWLP-R has `P206_UpdateSkillBar` where we have 218, `P215_SkillActivated`
  where we have 227, `P217_SkillRecharge` / `P218_SkillRecharged` where we have
  229 / 230. At 207 − 12 = **195**, `sgwlpr`'s `PacketTemplates.xml` carries four
  consecutive packets whose fields are exactly ours:
  `195 = [agentid, int32]`, `196 = [agentid]`,
  `197 = [agentid, int16, int32, int32]`, `198 = [agentid, int16, int32]`.
  GWLP-R's `P195`–`P198` are the same four, and all four class names are
  `_Unknown`.

Four consecutive layouts matching across a build gap of a decade or more is
not something a coincidence produces, and it is a shape check with no free
parameter: the offset was fixed by three *other* messages before 195 was looked
at. Use of `gw-preservation` is confined to exactly this — verifying a value we
derived ourselves, the only thing that upstream's terms permit (`CLAUDE.md`,
second gate) — and nothing here takes a layout, an algorithm or a constant from
any of the three, so no derivation-register row is owed.

**So the four names are OURS** — and, worth saying plainly, the reason nobody
named them is not that they are obscure. They are four consecutive opcodes in
the middle of the skill block, 724 of them in this corpus. They went unnamed
because everyone who wanted adrenaline read it out of client memory instead,
where it is one `ReadProcessMemory` away.

### 26.10 What did not change, proved rather than argued

The codec reads only `fields`; the four override rows add none, so decoding
*cannot* change. That is exactly the sort of claim our own decoder can be made to
agree with, so it was checked the other way round: the **entire** live corpus was
decoded twice — once against the committed `overrides.json`, once against the
working tree's — and hashed.

```
committed overrides:    b11aba5b…  114,985 messages
working-tree overrides: b11aba5b…  114,985 messages
```

Identical SHA-256 over every decoded field of every message. The four
schema-reading tests were also re-run before and after and returned the same
counts: `test_codec.py` 29, `test_catalog.py` 13, `schema/test_smsgnames.py` 15,
`authsrv/test_smsgnames.py` 26 — all green, 83 checks.

### 26.11 Open

1. ~~**The recharge gate has never been seen live.**~~ — **SEEN 2026-08-21,
   §32, and it holds.** Two witnesses now stand behind it where there was one
   line of disassembly: the measurement (a 120-cost skill on a 12 s recharge
   ends at 40.4% against a predicted 41.7% for "4 gains skipped, 2 landed",
   versus 100% had none been skipped) and GWW's own *"recharging skills cannot
   rebuild adrenaline"*. Note the run's designed readout was confounded — the
   recharge SWEEP draws in the same rectangle as the fill — and the answer came
   from the residue after the sweep cleared. §32.2.
2. ~~**Are the sub-25 gains the health-loss rule?**~~ — **RUN 2026-08-21, and
   it CORRECTED the rule.** They are the health-loss rule: 31 of the 32 carry a
   same-batch `0x00A3` naming the gaining agent as its target, so each joins to
   the exact damage that produced it. **But the wiki's "floored" is wrong —
   the wire rounds.** floor fits 14/31, ceil 17/31, `floor(pct)+1` 17/31,
   **round 31/31**. The discriminating rows are |pct| 2.500, 2.708, 2.917 and
   3.542 granting 3, 3, 3 and 4 where flooring grants 2, 2, 2 and 3.
   `pools.damage_units` shipped the wiki's rule and was corrected; the reading
   is now OBSERVED rather than INFERRED. Two caveats kept: the sign is
   negative on the wire and the magnitude is what the rule reads (flooring the
   negative rounds away from zero and fits nothing — an arithmetic slip that
   made a correct hypothesis look 0-for-31), and the no-grant BOUNDARY moving
   from 1% to 0.5% is an extrapolation, since the corpus's smallest sample is
   2.5%.
3. ~~**What is 209 for?**~~ — **ANSWERED 2026-08-21: "nothing on retail" is
   now EARNED rather than assumed, and both named candidates died.** Verified
   CONFIRMED by an adversarial pass.
   **The hero/henchman push is REFUTED twice over.** Structurally: the worker
   has no hero-specific machinery its siblings lack — the record lookup
   `0x00820F10` is a plain binary search keyed on agent id with no comparison
   against the local player, so 207/208/210 would already serve a hero
   unchanged. And empirically: **heroes are absent from the corpus**
   (`0x01C2` PARTY_HERO_ADD = 0 of 114,985) — with a green positive control,
   since the identical scan finds `0x01BF` PARTY_HENCHMAN_ADD **21 times over 7
   connections**. Better still, those henchmen are the decisive datum:
   **companions demonstrably existed and retail pushed them no skill state at
   all** — zero 218/207/208/209/210/229/230/231 naming any of them.
   **The resync-after-drift story lost its mechanism.** It rested on 207's
   recharge skip (`0x008219C0`) being a client-side quirk the server might not
   share. It is not a quirk: GWW states *"recharging skills cannot rebuild
   adrenaline"*, so it is a GAME rule both sides implement and no drift arises
   from it.
   **What survives is narrower and unfalsified**: an absolute restore into a
   session whose state the server cannot derive from deltas — a reconnect or
   mid-instance resume. **And the corpus is silent on it for a MEASURED reason
   rather than a hopeful one:** all 48 skillbar pushes arrive 0.22–0.90 s into
   their connection, so every one of the 49 connections is a fresh instance
   entry and the corpus **contains no reconnect at all**. The one experiment
   that would settle it is named in §26.12.
   **Method note worth more than the answer**: "is this agent the observer" was
   checked with two independent routes — `0x017D` INSTANCE_LOAD_PLAYER_NAME and
   `0x0199` INSTANCE_LOAD_INFO's player number, each mapped through `0x0059`'s
   `(player_number, agent_id)` — agreeing on 40 of 40 resolvable connections
   and disagreeing on 0. The obvious shortcut fails hard: taking the FIRST
   `0x0059` as self is wrong on 20 of 44 connections, because `0x0059` is
   broadcast for every player in the instance. `toolkit/authsrv/moralescan.py`
   shipped that shortcut and was corrected the same day (§26.13).
4. ~~**Opcode 231 needs its own pass**~~ — **DONE 2026-08-21, §26.12.**
5. ~~**The `u16`/`u32` width disagreement at `+0x38`**~~ — **MEASURED on both
   builds 2026-08-21: still latent.** The high word is zero in **all 3,443
   rows on 38797 AND on 38833**, which also carry the same 151 nonzero costs
   over the same distinct set {20, 25, 50, 60, 75, 80, 100, 120, 125, 130, 140,
   150, 160, 175, 200, 220, 240, 250} — note 20, 60, 130, 140, 160, 175 and 220
   are not multiples of 25, which is §26.8's raw-units point from a second
   build. `skilltable.py` reading a dword where the client reads a word remains
   harmless, and is now harmless *across a build bump* rather than on one
   image. Worth aligning the widths anyway; no longer worth blocking on.
6. ~~**Nothing here has been sent to a client yet.**~~ — **DONE the same day,
   §27.** The run was made, the prediction it registered (`units/cost`, not a
   count of quarters) was CONFIRMED, and §26's central claim is no longer static
   plus wire: a client has now been made to draw this family. The two halves
   §27 did *not* reach — 210's on-screen reset and 208's wipe — are restated as
   open there rather than closed here.

## 27. E5 — the flames, on screen

**2026-08-21, run `20260821T125215`, loopback, build 38797, server at
`a0f4386`.** The fifth run of the series §25 opened, and the one that closes
§25's P7. Predictions were registered before the client launched
(session scratchpad, `e5-predictions.md`) and before the build workflow that
produced the sender had reported.

### 27.1 Why this run could be short

E5 is E4 **with one thing changed** — the server now sends `0x00CF` — so E4 is
its own control and was already collected. That is the whole design: §25 had
already established that at a server-side pool of 100 the icon rendered
pixel-identical to its 0-unit state, so any movement here is attributable to
the message rather than to the fight.

**The instrument is the DEFAULT bar**, which turned out to be better than the
single-skill rig §26.11 imagined. `[316, 317, 318, 319, 320, 321, 322, 323]`
carries three adrenal skills whose costs are *not* multiples of 25, and five
non-adrenal ones:

| slot | id | `adrenaline_units` |
|---|---|---|
| 1 | 316 | — (non-adrenal) |
| **2** | **317** | **80** |
| **3** | **318** | **120** |
| **4** | **319** | **80** |
| 5–8 | 320–323 | — (non-adrenal) |

So slots 1 and 5–8 are an **in-frame null control**: they sit in the same
screenshot, under the same lighting, through the same fight. This matters more
than it sounds — `studies/review`'s aggregate-diff lesson is that a
changed-pixel spike over a whole HUD finds tooltips and toasts, not findings.

### 27.2 What the server sent

Twelve gains, each `0x00CF, 10 B`, each emitted **before** its damage message —
retail's batch position, fixed the same morning after the skeptic pass caught
the sender shipping it last:

```
[c1] attacking agent 10 (Hatcher [Collector])
[c1] s2c adrenaline +25 (weapon hit on agent 10) (0x00cf, 10B)
[c1] hit agent 10: 93/100
[c1] s2c adrenaline +25 (weapon hit on agent 10) (0x00cf, 10B)
[c1] hit agent 10: 88/100
      … twelve in all
```

The first `0x00CF` any client has ever been sent by this server, or by any
server we have written.

### 27.3 P10 — the flames move. CONFIRMED

Fraction of each slot's pixels differing from the pre-attack baseline
(`walk2-shot.png`, every pool at 0), threshold 24/765:

| frame | slot 1 | **slot 2** | **slot 3** | **slot 4** | slot 5 | slot 6 | slot 7 | slot 8 |
|---|---|---|---|---|---|---|---|---|
| walk4 | 0.0% | **49.2%** | **23.8%** | **40.3%** | 0.0% | 0.0% | 0.0% | 0.0% |
| walk6 | 0.0% | **89.8%** | **89.0%** | **89.2%** | 0.0% | 0.0% | 0.0% | 0.0% |
| walk8 … walk16 | 0.0% | **89.8%** | **89.0%** | **89.2%** | 0.0% | 0.0% | 0.0% | 0.0% |

**The five control slots are at exactly 0.0% in all seven frames.** Not "close
to zero" — zero changed pixels, which is the same pixel-identity standard that
made §25's negative trustworthy, now producing a positive on the three slots
next to them. §25's P7 is not merely explained, it is inverted under the
identical rig.

### 27.4 P11 — a continuous fraction, not quarters. CONFIRMED

The whole-slot percentages above are **not comparable across slots** — they
depend on the icon art underneath. So the fill was measured the way the client
draws it: per row, bottom-up, counting rows that moved. On `walk4`, the one
frame that caught the bar mid-charge:

```
slot 1 (316, non-adrenal)   0/54 rows =  0.0%   ..................................
slot 2 (317,  80 units)    30/54 rows = 55.6%   ..##############################++
slot 3 (318, 120 units)    17/54 rows = 31.5%   ..#################+++............
slot 4 (319,  80 units)    26/54 rows = 48.1%   ..##########################++++++
slot 5 (320, non-adrenal)   0/54 rows =  0.0%   ..................................
```

**The fill rises from the bottom and stops at arbitrary heights.** Quarter-strike
quantisation on an 80-unit skill could only ever land on 31.25%, 62.5% or
93.75%; 55.6% and 48.1% are neither. This is the `fdiv` at `0x008C6188`
rendering — `adrenaline_b ÷ skillData.adrenaline` — and §26.11's registered
prediction, confirmed.

**And the denominator is the skill's own raw cost, visibly.** Slot 3 costs 120
where slots 2 and 4 cost 80. All three received identical grants, and slot 3
sits *lower* than both. A display keyed to strikes rather than to raw units
could not produce that, and it is the on-screen counterpart of §26.8's census
finding that 151 skills carry costs that are not multiples of 25.

**HONEST LIMIT — and it was mostly the METRIC, not the client. Re-measured
2026-08-21 after §29.4.** As first written this paragraph read: *"Slots 2 and 4
have the same cost and should therefore show the same fill; they read 55.6% and
48.1%. The likeliest reading is animation phase… until [a denser sample] exists
'the two 80-unit skills agree' is UNVERIFIED rather than confirmed."*

That 7.5-point gap came from the rows-over-30%-of-width statistic, which §29.4
showed is sensitive to the icon art *underneath* the fill. Re-measured with the
art-independent boundary criterion the whole series settled on, the same eight
frames give:

| frame | slot 2 (80) | slot 3 (120) | slot 4 (80) |
|---|---|---|---|
| w001 | 0.0% | 0.0% | 0.0% |
| **w002** | **21.2%** | 15.4% | **25.0%** |
| w003–w008 | 100.0% | 100.0% | 100.0% |

**The two 80-unit skills agree exactly in seven of the eight frames**, and in
the single mid-charge frame they differ by 3.8 points — about two rows of 52,
down from 7.5. **And the ORDER FLIPS**: the old statistic put slot 2 above slot
4, this one puts slot 4 above slot 2. A difference whose *sign* depends on the
statistic is a property of the measurement, not of the client.

What honestly remains is much smaller than the original caveat: a ~2-row
difference in one frame, which animation phase would explain and which the
metric's own boundary sensitivity would also explain, with nothing here able to
separate them. The claim "the two 80-unit skills agree" is CONFIRMED in seven
frames and unresolved at the two-row level in one — not the open question this
paragraph used to describe.

### 27.5 What E5 did NOT reach

Stated plainly, because a run that answers two of four questions and reports
four is how §25's own P7 nearly went unnoticed:

- ~~**P12, the spend's on-screen reset (`0x00D2`), is UNTESTED.**~~ — **DONE,
  §28: CONFIRMED**, the spent ring empties to 0.0%.
- ~~**P13, the cross-pool tax, is UNTESTED.**~~ — **DONE, §28: CONFIRMED**, and
  it settled the unit question — equal strikes, unequal rings. This is the half
  of GWW's on-use rule that no screen has ever shown, and the default bar's
  three adrenal skills at 80/120/80 are an unusually good instrument for it: one
  press should drop the other two by exactly one strike each, which at those
  costs is a *different* fraction of each ring.
- **P14, the outpost map-gate control, was not run.** §26.6's
  `MissionCliGetMap() == 1` gate therefore still rests on the disassembly alone.
- The **25 s wipe (`0x00D0`)** was not observed on screen either.

### 27.6 Two process notes worth keeping

**The first attempt failed for a reason the log stated in its second line.**
`--no-enemy` is the *harness's* default and the hostile needs `session.py
--enemy`; the run ordered an attack into an empty world, and `begin_attack`
returned silently because agent 10 did not exist. The server log said `NO ENEMY:
the world will contain the player and nothing else.` at line 2 and it was read
past. The harness's own verdict caught it (`RUN VERDICT RETRACTED`) rather than
letting eight screenshots of an unchanged bar be scored as a null result — which
is exactly what that retraction machinery is for, and the second time it has
paid for itself.

**`git add -A` in a shared worktree swept up another session's work.** Commit
`a0f4386` carries a peer session's `test_spawn_burst.py` repair and ~32 lines of
`TESTS.md` alongside the adrenaline arc, under a message describing only the
latter. Nothing was lost and nothing conflicted, but the commit is wrong about
its own contents. It was left un-split deliberately: `git rebase -i` is
unavailable in this environment, and by the time it was noticed the peer had
committed on top, so a rewrite would have rewritten their work too. Recorded
here and in the following commit's message instead — `git status` before
`git add -A` is the habit that prevents it.

## 28. E6 — the spend, and the tax that proves the unit

**2026-08-21, run `20260821T134216`, loopback, build 38797, server at
`7dec7c9`.** Closes the first two items §27.5 left open. Predictions registered
before the client launched (`e6-predictions.md`), including the numbers.

### 28.1 The rig, and why the default bar is the instrument

Nine landed hits capped every pool, then **`attack:0` broke off the swing** so
no further gain could reach the readout, then slot 2 was pressed. The server
log is the proof that the window is clean: nine `0x00CF`s, the `0x00D2`, and
**zero `0x00CF` after it**.

The bar makes the run discriminating for free. Slots 2 and 4 cost **80**, slot
3 costs **120**, and slots 1 and 5–8 are non-adrenal controls in the same
frame. So one press taxes two rings by the same 25 units against different
denominators — and if the display taxed by a *fraction* instead, both would
drop by the same visible amount.

### 28.2 Our own wire, in ArenaNet's order

```
c2s USE_SKILL
s2c SKILL_ACTIVATED_BROADCAST(skill 317 via USE_SKILL)   0x00E4
s2c adrenaline spend: skill 317 (copy 0)                 0x00D2   <-- between
s2c cast animation: player casts 317                     0x00A0
```

Which is the measured retail shape from §26: `0x00E4` precedes the spend 38 of
38, and the property naming the skill follows it 39 of 39. The sender was
built to that census rather than to symmetry with the energy debit, and this
is the first time it has been seen going out.

### 28.3 P12 — the spent ring empties. CONFIRMED

Slot 2 goes from a full ring to **0.0%** — every row indistinguishable from the
pre-charge empty icon. `0x00821C00` writes both halves of the matched slot to
zero and the screen agrees.

### 28.4 P13 — the tax is 25 UNITS, not a share of the ring. CONFIRMED

Fill measured as the first row from the top carrying any changed pixel against
the empty baseline — E5's own null standard, no tuned threshold:

| slot | skill | cost | charged | after the press | predicted |
|---|---|---|---|---|---|
| 2 | 317 | 80 | 100.0% | **0.0%** | 0.0% |
| 3 | 318 | **120** | 100.0% | **80.8%** | 79.2% |
| 4 | 319 | **80** | 100.0% | **67.3%** | 68.8% |

**CORRECTED 2026-08-21, an hour after this section was written — the point
estimates above are NOT good to 1.6 points, and this paragraph originally said
they were.** They depend on a free parameter I never swept: how many changed
pixels make a row "filled". At the setting used above (any single pixel) the
agreement is 1.6 points; swept from 1 to 40 pixels, slot 3 ranges 65.4–80.8%
and slot 4 ranges 42.3–67.3%. E7 then showed that the ≥1 setting is positively
UNSAFE — it reported a fully empty ring as 100% full off three stray pixels in
one row (§29.4). So the precision claim is withdrawn. **What survives the sweep
is the entire finding**, and it survives at every single threshold:

| minpx | 1 | 5 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|---|
| slot 3 (cost 120) drop | 19.2 | 19.2 | 19.2 | 21.2 | 25.0 | 34.6 |
| slot 4 (cost 80) drop | **32.7** | **36.5** | **36.5** | **42.3** | **44.2** | **57.7** |
| slot 2 (spent) | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Slot 4 loses more ring than slot 3 at every setting, and the spent ring reads
exactly zero at every setting. Those two statements have no free parameter in
them, and they are what the run is for. The discriminator:

```
slot 3 (cost 120):  ring dropped 19.2 points   (25/120 = 20.8%)
slot 4 (cost  80):  ring dropped 32.7 points   (25/ 80 = 31.2%)
```

**Both slots lost exactly one strike; they lost visibly different amounts of
ring — at every threshold, so the statement is parameter-free.** A proportional tax — a quarter off each, say — would have dropped them
by the same number of points, and it did not. This is `cmp esi,0x19 /
add esi,-0x19` at `0x00821C71` reaching the screen: the pool is carried in raw
units, 25 is the size of a strike, and the ring is `adrenaline_b ÷
skillData.adrenaline` with the skill's own raw cost underneath. §26.8's census
finding that 151 skills carry non-multiples of 25 is now visible rather than
tabular.

### 28.5 P14 — the controls hold. CONFIRMED

Slots 1 and 5–8 sit at **0 changed pixels** across the press, as they did
through all seven frames of E5. The tax reaches exactly the occupied adrenal
slots and nothing else, which is `0x00821C4C`'s `(skillId, skillCopy)` join
behaving.

### 28.6 The wipe is still unseen, and a near-miss worth recording

The 25 s timeout **did** fire on the wire — `adrenaline cleared: 25s out of
combat (0x00d0, 6B)` — about a second after the last scripted frame. The
teardown frame `final.png` is *not* evidence for it: measured against the empty
baseline it reads ~100% changed **on every slot including the two non-adrenal
controls**, so the whole frame is a different screen state and any adrenaline
reading taken from it would be an artifact. That is the aggregate-diff lesson
catching a false positive in the act, and the in-frame controls are what caught
it. ~~**`0x00D0` on screen remains open**, and wants a run that simply waits.~~ —
**DONE, §29.** The run that simply waited is below, and the artifact this
paragraph caught turned out to be the same class of error as the metric defect
§28.4 now carries.

### 28.7 Two measurement notes

**The first attempt (`20260821T133856`) was contaminated and the log said so.**
`S:0.5` does not break off an attack — the swing continued and two more gains
landed after the spend, which would have refilled the taxed pools and hidden
the very effect the run was for. `attack:0` is the clean stop: `begin_attack`
finds no agent 0 and clears `state["attacking"]`. The contamination was
detectable only because the server log lists every `0x00CF` in order; a
screenshot-only run would have shown two plausible rings and no way to know.

**Pixel-identity is too strict a null here, and E5's phrasing invited the
error.** The client re-renders with sub-threshold variation everywhere, so
"identical to the baseline" finds nothing empty even on a ring that is visibly
empty. E5's controls read 0.0% under a *threshold* of 24, not under equality;
this section uses the same threshold and says so. The intermediate attempt —
counting rows over a 30%-of-width threshold — is what produced §27.4's
unresolved discrepancy between two equal-cost skills, because that statistic is
sensitive to the icon art underneath the fill. **The boundary criterion (first
row carrying any change) is art-independent, and under it §27.4's anomaly does
not appear**: here the two 80-unit skills behave identically, one emptied to
0.0% and one taxed to 67.3% against a predicted 68.8%. §27.4's caveat should be
read as a defect of that metric rather than of the client.

## 29. E7 — the wipe, and a metric that lied

**2026-08-21, run `20260821T135905`, loopback, build 38797, server at
`4c004d7`.** The last screen-side item on this channel. Predictions in
`e7-predictions.md`, registered before launch.

The design is the whole point: charge every pool, break off with `attack:0`,
then **do nothing for thirty seconds**. The practice target never attacks, so
no damage re-anchors the clock — the only clock running is the one the last
`0x00CF` started.

### 29.1 The wire

Nine gains, then **exactly one** `0x00D0` and nothing after it:

```
[c1] s2c adrenaline cleared: 25s out of combat (0x00d0, 6B)
[c1] the player's adrenaline is gone: 25s out of combat
```

P18 CONFIRMED — `tick` drops the clock either way, so a wiped bar cannot
re-wipe, and one quiet period produced one message rather than a stream.

### 29.2 P15 and P16 — all three at once, and not early. CONFIRMED

Frames anchored by timestamp, never by filename. `attack:0` ran at 17:59:55, so
the last gain is at or just before it and the wipe is due ~18:00:20:

| frame | time | slot 2 (80) | slot 3 (120) | slot 4 (80) | controls |
|---|---|---|---|---|---|
| w003 | 18:00:08 | 100% | 100% | 100% | 0 |
| w004 | 18:00:16 | 100% | 100% | 100% | 0 |
| **w005** | **18:00:21** | **0.0%** | **0.0%** | **0.0%** | **0** |
| w006–w010 | 18:00:25–44 | 0.0% | 0.0% | 0.0% | 0 |

**The three rings empty together, in one frame step, with no intermediate
state anywhere in the run** — which is `0x00821B00` walking all eight slots and
firing the repaint once. Nothing drains gradually; there is no decay.

And the timing brackets the prediction from both sides: full at 18:00:16, empty
at 18:00:21, due at ~18:00:20. **No frame is empty before the 25 s mark**, which
is the half that matters — an early wipe would have meant the clock is anchored
somewhere other than the last gain.

### 29.3 P17 — the controls hold. CONFIRMED

Slots 1 and 5–8: **0 changed pixels in every one of the ten frames.** This is
the control §28.6 argued for after `final.png` read ~100% changed on every slot
including the non-adrenal ones. Here the wipe frame moves the three adrenal
rings and nothing else, so it is the wipe rather than a screen-state change.

### 29.4 The metric lied, and the controls are what caught it

The first pass over these frames reported **slot 2 back at 100% in the last
frame** — after a wipe, with nothing on the wire that could refill it. It was
not real. Slot 2's mean colour in that frame is the EMPTY value (110,80,35
against an empty baseline of 105,79,34; charged is 218,163,72). Three stray
pixels in the topmost row crossed the difference threshold, and the fill rule
in use — *the first row from the top carrying **any** changed pixel* — turned
three pixels into a full ring.

**That rule produced §28's numbers**, which is why §28.4 now carries a
correction rather than its original precision claim. Swept across sensible
settings the point estimates move by up to 25 points; the *findings* — a spent
ring at exactly zero, and unequal drops for equal strikes — hold at every
setting. E7 itself is immune because it contains no intermediate fill to
measure: 100% and 0% are threshold-independent, and the table above is
identical at minpx 10 and 25.

The general lesson is the one already in this repo's notes and freshly earned:
**a point estimate with an unswept free parameter gets over-read.** The check
worth running is the one with no free parameter in it, and where that is not
available, sweep the parameter and report what survives. Three runs in a row
have now had their headline numbers moved by a threshold choice — §27.4's
"anomaly" (a metric artifact), §28.4's precision (withdrawn), and this frame
(a false positive) — while every *qualitative* claim has survived untouched.

## 30. E8 — the outpost gate, and the overlay that is torn down

**2026-08-21, runs `20260821T140826` (outpost) and `20260821T141108`
(explorable), loopback, build 38797, server at `4e9d374`.** The last
screen-side item on this channel, and the only NEGATIVE in the series.
Predictions in `e8-predictions.md`.

### 30.1 The confound, named first and defeated

§26.6's claim is read off `0x00542E43` alone: the fill is drawn only when
`MissionCliGetMap() == MISSION_MAP_GAME`. Testing it means sending a correct
`0x00CF` to a client standing in a town — and there is a specific, known reason
the run could produce a worthless null: **an outpost forbids attacking**
(§25/E5). No attack, no hit, no gain, and "the ring did not fill" would be a
statement about the attack rule rather than the display gate.

**It did not fire, and the reason is structural.** The harness's `attack:10`
does not click — it calls `begin_attack` SERVER-side, the same entry the
`ATTACK_AGENT` arm uses, and our server does not consult the map type. So the
outpost arm put **9 gains on the wire, exactly as the explorable arm did**, and
that precondition was checked before a single pixel was measured.

### 30.2 The A/B

Same map (148), same bar, same walk, same nine gains. One flag differs:

| arm | slot | fill@10 | fill@25 | mean RGB before | mean RGB after |
|---|---|---|---|---|---|
| **A outpost** | 2 (317) | **0.0%** | **0.0%** | (197,122,48) | **(197,122,48)** |
| **A outpost** | 3 (318) | **0.0%** | **0.0%** | (154,111,52) | **(154,111,52)** |
| **A outpost** | 4 (319) | **0.0%** | **0.0%** | (137,85,33) | **(137,85,33)** |
| B explorable | 2 (317) | 100.0% | 100.0% | (103,64,27) | (220,143,58) |
| B explorable | 3 (318) | 100.0% | 100.0% | (82,59,29) | (177,134,63) |
| B explorable | 4 (319) | 100.0% | 100.0% | (72,46,20) | (158,102,40) |

**P19 CONFIRMED.** In the outpost the three rings do not move — and not merely
"below threshold": the mean colour of every adrenal slot is **byte-identical
before and after nine gains**. **P20 CONFIRMED**: the same rig, one flag
changed, fills all three. Non-adrenal controls sit at 0.0% in both arms.

### 30.3 The overlay is torn down, not merely unfilled — and the colours say so

The result is better than the null it was designed to produce. Compare the two
arms' *starting* states: an uncharged adrenal icon in an EXPLORABLE is **dark**
(103,64,27), while the same icon in an OUTPOST is **bright** (197,122,48) —
brighter than the explorable's fully-charged state is dark. So the outpost is
not showing an empty ring; it is showing **no ring at all**.

That is exactly what `0x00542E43`'s `jne` path does, and this is its first
confirmation from outside the disassembly: the branch sends msg `0x59` with a
NULL payload, `GmCtlSkImage` substitutes `{0,0}` and **destroys the overlay**
(`call 0x631220`). Three distinct on-screen states, all now observed:

| state | slot 2 mean RGB | what it is |
|---|---|---|
| outpost, any adrenaline | (197,122,48) | no overlay — the plain icon |
| explorable, 0 units | (103,64,27) | overlay present, ring empty |
| explorable, full | (220,143,58) | overlay present, ring full |

The darkening a player reads as "not ready yet" is therefore **part of the
adrenaline overlay**, not a property of the icon — which also retires, from the
other direction, §25's early guess that slot darkening might be an
affordability grey. It is neither affordability nor the selection border: it is
the empty state of a ring that only exists where the ring is drawn.

### 30.4 What this closes, and the one thing it does not

Every screen-side claim about this channel is now observed: the charge (§27),
the spend and the cross-pool tax (§28), the wipe (§29), and the map gate here.
**What is still static-only** is the *reason* for the gate — nothing observed
says why ArenaNet tears the overlay down in towns rather than leaving a stale
ring, and the disassembly does not say either. Not worth a probe; worth not
claiming.

## 31. E9 — the blink warning, and we were already producing it

**2026-08-21, run `20260821T141806`, loopback, build 38797, server at
`2f10ec5`.** Raised by the owner from GWW's Adrenaline page — *"A visual
warning appears, with partially filled skills will begin blinking"* — a
behaviour §§25–30 never tested and never mentioned. Predictions in
`e9-predictions.md`.

### 31.1 Why §29 was silent on it rather than negative

Two independent reasons, either sufficient. **E7 capped every pool**, and the
wiki's warning is for PARTIALLY filled skills, so nothing was eligible to
blink. And **E7's frames were 5–8 s apart** through the warning window, where a
blink is sub-second and aliases to nothing. A run can be clean, pass every
prediction, and still be blind to a whole behaviour — which is the argument for
reading the wiki against a finished result, not only before it.

### 31.2 The mechanism was already in §26, unrecognised

`0x00CF`'s handler fires UI event **`0x10000058`** carrying `{agent, f32}`,
the float loaded from `.rdata` `0x009495B4` — **MEASURED bytes `0000c841` =
25.0**, the timeout itself. `GmSkSlot` forwards it as msg `0x5A` to
`GmCtlSkImage`, whose own assert names it:

> `GmCtlSkImage:1483` — *"Clearing the adrenaline timer on a skill image is
> currently not supported. Bug Austin about this."*

The handler stores the float (`fstp [edx+0x10]`, `fstp [edx+0x14]`,
`mov [edx+0x18],0`) and never accumulates. **So the countdown is CLIENT-side
and armed by a message this server already sends.** §26 recorded that event as
"the strike flash" with the 25.0 noted only as a fixed constant; it is the
warning timer, and the constant is the timeout.

### 31.3 The measurement

Four gains left slot 3 **partial** (100/120) while slots 2 and 4 capped —
so one frame holds all three categories. Mean luminance, 26 frames ~1 s apart;
the wipe lands at `hold019`:

| slot | state | range | direction changes | verdict |
|---|---|---|---|---|
| 1 | non-adrenal | **0** | 0 | flat |
| 2 | **capped** | 87 | **1** (the wipe step) | flat |
| **3** | **PARTIAL** | **20** | **9** | **OSCILLATES** |
| 4 | **capped** | 61 | **1** (the wipe step) | flat |
| 5 | non-adrenal | **0** | 0 | flat |

**P21 CONFIRMED, P22 CONFIRMED** — the controls are flat to a range of *zero*,
so the oscillation is not a global flicker.

**And the blink goes fully OFF, not dim.** Slot 3's post-wipe luminance — ring
gone — is 62. During the warning window slot 3 hits exactly 62 at `hold015` and
`hold017` and returns to 74–75 between them. The warning hides the fill
entirely and restores it, a square wave aliased at 1 s sampling.

**A finding the wiki implies and this shows: capped skills do NOT blink.**
Slots 2 and 4 sit rock-flat at 156 and 111 through the entire warning window,
changing exactly once — at the wipe. Only the partially filled ring warns,
which is GWW's sentence read strictly.

### 31.4 Corroborated by the owner, watching

**OBSERVED, owner, live during this run: "i watched it blink, seemed good."**
That is worth more than it looks. Three times in this series a headline number
came from a pixel metric that turned out to be wrong (§27.4's phantom anomaly,
§28.4's withdrawn precision, §29.4's false 100%), and a human eye on the actual
screen is the one witness that shares none of those failure modes.

### 31.5 The answer to the question that prompted it

**Yes — we capture it, and we were capturing it before anyone asked.** No
server change was made for this section. The server sends nothing at all
between the last `0x00CF` and the `0x00D0` 25 s later; the blink is the
client's own timer, armed by the gain message, and it appeared the first time
anyone sampled fast enough to see it. **P23 CONFIRMED.**

Worth stating plainly because the opposite was equally possible: had the
warning ridden its own opcode, this channel would have been incomplete and
nothing in §§25–30 would have revealed it.

## 26.12 Opcode 231 — the recharge family's *indefinite* case

**Settled 2026-08-21** (§26.11 item 4), static plus corpus, verified CONFIRMED
by an adversarial re-derivation. §26.3 declined to name it on one handler read;
this is the evidence it asked for.

**The chain, each link with exactly one way in** (`codescan --xrefs`): RECV
table `0x00BC8F68` → stub `0x0091F6E0` (0 direct calls, 1 data word at
`0x00BC97E0`) → thunk `0x00814980` → worker `0x00822D10`. So the only path into
this worker is opcode 231 arriving off the wire; no client-side code disables a
skill through this door. Shape `[agent_id, u16 skillId, u32 skillCopy]`, 12 B,
from `msgshape.py` — **CORROBORATED by a lineage with no shared ancestry**,
gw-preservation's `network-log-explorer` typing `0x00e7` as the identical triple.

**What it does**, MEASURED with bytes:

```
00822D79  8b4604              mov eax,[esi+4]      ; SAVE the old adrenaline_b
00822D7C  c70600000000        mov [esi],0          ; adrenaline_a = 0
00822D82  c7460400000000      mov [esi+4],0        ; adrenaline_b = 0
00822D89  85c0 / 7419         test eax,eax / je    ; repaint only if there WAS any
00822D99  push 0x10000059     ;  the adrenaline repaint, payload {agent}
00822DA9  fld  [0x948654]     ;  +INFINITY (bytes 00 00 80 7f)
00822DC3  c74608ffffffff      mov [esi+8],0xFFFFFFFF   ; recharge = NEVER
00822DBB  push 0x1000005d     ;  {agent, skillId, skillCopy, +inf, +inf}
```

**CORRECTION to [studies/skillcast](../skillcast/FINDINGS.md) §5**, which reads
*"adrenaline_a = 0; if (adrenaline_b) fire 0x10000059; adrenaline_b = 0"*. The
image saves the old `adrenaline_b` **first** and zeroes **both** halves before
testing the saved value. The guard is on the previous adrenaline, and that
detail is what makes the next paragraph decidable.

### The zeroing is PURPOSEFUL — and NOT special to 231

The four recharge-family workers read side by side settle §26.3's question:

| opcode | what it means | touches adrenaline? |
|---|---|---|
| **229** `0x00E5` SKILL_RECHARGE | unavailability BEGINS, timed | **zeroes both halves** — `0x00822C00`/`0x00822C06`, a sequence **byte-identical** to 231's |
| **230** `0x00E6` SKILL_RECHARGED | unavailability ENDS | **no** — its entire matched body is `mov [ecx+8],0` |
| **231** `0x00E7` | unavailability BEGINS, indefinite | **zeroes both halves** |
| **232** `0x00E8` | describes a partial recharge | **no** |

**The rule is "when unavailability begins, the pool is dropped"**, and it is
229's rule as much as 231's — so any model treating adrenaline-clearing as a
property of *disabling* is wrong. **WIKI corroborates from outside the binary**:
GWW's Adrenaline page says *"Disabled skills also lose all their adrenaline
while recharging skills cannot rebuild adrenaline"* — both halves, matching both
workers.

### The name is NOT being promoted, and that is the finding

`studies/skillcast` §5 proposed **SKILL_DISABLED** (explicitly INFERRED). It is
defensible in meaning and **collides with a physically different channel**: the
client keeps a per-slot *disabled* bitmask at `HotKeyState+0xA4` (GWCA's
`Skillbar.disabled`), written by opcodes **100/101** (`bts`/`btr` at
`0x00822085`/`0x0082208A`; GWCA names them HERO_SKILL_STATUS /
HERO_SKILL_STATUS_BITMAP) and read by accessor `0x00816F40` — and **231 never
touches it**. "Disabled" also fails to separate 231 from 229, since GWW uses the
word for Dervish avatars being *"disabled for 45 seconds"*, which is a TIMED
disable and therefore 229's job.

`SKILL_RECHARGE_INDEFINITE` is proposed instead — it sits in the existing
register beside SKILL_RECHARGE/SKILL_RECHARGED, names the field 231 actually
writes, and carries the discriminating fact. **It stays INFERRED and out of
`schema/overrides.json`**: witness 1 (the handler) is strong, witness 2 (the
wire) is n=1, and that is below `studies/smsgnames`' two-witness bar. **No
ArenaNet string names this message** — the worker contains zero asserts and
pushes zero string pointers, and the positive control is green (the identical
grep finds `adrenalin`, `hotKeyState` and ChCliSkill's own asserts). No upstream
names it either: absent from the maintained GWCA, Headquarter, OpenTyria and
the network-log-explorer name map.

### The single wire witness

**Exactly one `0x00E7` in 114,985 live messages** — capture `20260817T231139`,
t=105.145, naming **skill 2**, which `textrec.py` resolves through the client's
own string table to **"Resurrection Signet"**. After it, skill 2 appears in no
message of any kind for the remaining **116 seconds** of the tape. That is
retail's one-use-per-morale-boost rule, and a signet that cannot come back until
a condition the server controls is exactly what an *indefinite* recharge is for.

**One honest wrinkle, flagged rather than smoothed:** the cast began
(`0x00E4`) at t=99.646 and the `0x00E7` landed at t=105.145 — 5.499 s, against
skill 2's own table activation of 3.0 s. A co-firing `0x00E3` supports "at cast
end", but the interval does not match the table and nothing here explains the
difference.

### Open

- **Does 231 make a skill uncastable, or only paint the slot?** The DISPLAY path
  is proved end to end — `GmSkSlot 0x00543181` calls the recharge accessor,
  recognises `INT_MAX`, and loads the same `+inf` constant, skipping the sweep
  arithmetic. The INPUT gate is untraced.
- **What re-enables it.** WIKI says a morale boost; which opcode carries that is
  unknown, and the observed connection never re-armed skill 2.
- **Opcode 232 has ZERO occurrences too** — a second fully-implemented,
  never-observed handler in this same family, alongside 209 and energy property
  33. Three now, which starts to look like a pattern rather than three accidents.

## 26.13 A tool defect found sideways: "which agent is me"

Recorded here because the adrenaline pass found it and in
[studies/morale](../morale/FINDINGS.md) because that is whose tool it is.

Establishing that no adrenaline message ever names a non-observer needed a
sound answer to *which agent is the observer*. The obvious shortcut —
**take the first `0x0059` and call its agent id ours** — is wrong, because
`0x0059` is `AGENT_CREATE_PLAYER` and the server broadcasts one for **every**
player in the instance: 16 to 56 of them in a busy outpost. The first is
whoever the server happened to send first.

`toolkit/authsrv/moralescan.py` shipped exactly that shortcut, with a comment
asserting *"field 2 is the receiving player's own agent id"*. **MEASURED against
the self-scoped anchor: the two rules agree on 24 connections and DISAGREE on
20 of 44** — 45% wrong — e.g. naming agent 16 where the observer is 767.

**The sound anchor is property 41 (MAX ENERGY)**, which §23 measured as
self-scoped across 97 sightings; an independent route (`0x0199`'s player number
mapped through `0x0059`'s pairs) agrees with it wherever both resolve, 40 of 40.
`moralescan.py` now uses property 41 and **does not fall back** to the old rule
— a connection with no property 41 leaves the flag unset, which is the honest
answer, where guessing would restore the 45%.

**Nothing published was wrong**, and that is worth stating precisely rather than
implying either more or less: `studies/morale`'s census claims count VALUES
across all agents ("the only non-zero `0x00EE` is −15", "the only `0x009C` that
is not 100 is 85") and never consult the flag. Re-running the census after the
fix reproduces both numbers exactly — 40 sightings, 83 sightings, same two
departures. So this is a **latent** defect corrected before it was relied on,
not a result being withdrawn.

The general shape is one this repo keeps meeting: a fixture that silently
resolves to the wrong thing turns every assertion behind it into a no-op, and
the defence is an anchor the artifact can refute rather than a plausible-looking
first element.

## 36. The client runs its OWN expiry timer — but it does not forget the effect (`--probe effect_silent_extend`, 2026-08-21)

> **Numbering note, 2026-08-21 — this section was written as §32, and so was
> §32 below.** Two `## 32.` headings collide as one markdown anchor, which made
> every cross-reference to "§32" ambiguous, including `PLAN.md` §8's adrenaline
> entry. **This** one moved, because §32 below is E10 and `§27`–`§32` = E5–E10 is
> a run `PLAN.md` cites by position. Old references resolve here: `studies/isle`
> §32/§32.7/§32.8 and `effects.EffectTable.apply`'s docstring now say §36. The
> section keeps its place in the file rather than moving to the end — this
> document is already non-monotonic (§26.12/§26.13 sit after §31) and a 248-line
> move is a worse diff than an out-of-order number.

**Answers the question `effects.EffectTable.apply` had left open** — its docstring
ended *"how retail refreshes one is NOT FOUND"*, and
[studies/isle §8.6](../isle/FINDINGS.md) had just answered the WIRE half: retail
refreshes by sending nothing and delaying the `0x0044`. A capture cannot see a
screen, so this probe read the other half. Run `20260821T173954`, verdict PASS,
all seven steps confirmed on the wire in `gamesrv.log` before any frame was
opened (`0x0042` 20 B, `0x0044` 10 B, three declared refusals silent).

**Design.** CONTROL: skill 478 for 10.0 s, removed at exactly `apply + duration`
— the shape our server emits today, which proves a removal removes. TREATMENT:
skill 480 for 10.0 s, then **25 seconds of server silence**, then a late
`0x0044`. Screenshots every ~2.35 s throughout.

### 36.1 The prediction was half right, and the half it got wrong is the finding

Pre-registered: *"the icon is STILL DRAWN at +13 s and +20 s with the timer bar
drained to empty, and it goes only when the late `0x0044` lands."* What happened:

- **The live icon vanished on the client's own timer, with no packet.** The
  Burning icon was gone roughly 15 seconds before the late `0x0044` was sent. The
  visible window was ~9 s against a 10.0 s stated duration, not the ~25 s the
  "waits to be told" reading requires. **The client owns the expiry.**
- **But the slot did not go empty.** Between self-expiry and the removal the
  client holds a **static, heavily faded ghost of the same icon** — an amplified
  diff reproduces the flame sprite's exact shape — and clears it the moment the
  `0x0044` arrives.

**Neither naive reading would have got this.** "Is the icon there?" answers *no*;
a pixel diff answers *yes*. The state is a third thing: **presented as expired,
still slotted.**

### 36.2 Why the ghost is a measurement and not my eye

| comparison | slot region | control region elsewhere on the same HUD row |
|---|---|---|
| consecutive frames, same state (6 pairs) | **0.000** | 0.000 |
| across the late removal (4 pairs) | **6.829** | **0.000** |

The noise floor is *exactly* zero — the camera is static, so same-state frames
are byte-identical. The change is **6.829 in the slot and 0.000 in a same-sized
control patch beside it**, which is what rules out lighting, animation and any
global render change. And the seven state-B frames spanning **+25.8 s to +39.9 s
are byte-identical to each other**, so this is a held static state, not a fade
still in progress.

### 36.3 What this decides for our own substrate

**`REMOVE-then-APPLY` is NOT required, and silence is NOT free.** The late
removal landed correctly on an effect the client had already expired visually —
no refusal, no desync — so the pair this table emits is not load-bearing for
correctness. But an effect held open by silence **stops being visible to the
player at its stated duration**. So:

- for anything the player must SEE for time T, the duration we send must cover T
  (or the effect must be re-applied); silence extends the server's bookkeeping,
  not the player's experience;
- `effects.py` is still not changed behaviourally on the strength of this — what
  changed is that the cost of each option is now measured rather than assumed.

### 36.4 The question this opens, and it is cheap

**Do retail players see the ghost too?** §8.6's Isle episodes ran +1.25 s to
+55.0 s past their stated durations on ONE apply each, so by this client's rule
the operator spent most of that time looking at a faded icon while the condition
still cost health — the Disease that killed them outlasted its 10.0 s duration
many times over. That is either a real quirk players live with, or retail sends
something we have not identified for environmental sources. **One screenshot of
a Student's ring taken 20 s after entry settles it**, and it costs nothing on the
next Isle trip. Until then, this section describes OUR client's response to OUR
messages, which is exactly what it was built to measure — and no further.

### 36.5 Does this apply to RETAIL? The message shapes are identical, and the only gap left is the build

§36.4 asked whether retail players see the ghost too, and said one live screenshot
would settle it. That overstated the cost: **most of it settles offline**, because
the client is the referee and the question is whether it can tell the two servers
apart.

Decoded with `bufflog` rather than by hand — a first pass scanning raw bytes for
`0x0044` found matches inside float payloads (`00803f` is `1.0f`) and was thrown
away:

| source | message |
|---|---|
| **retail**, Isle Students | `0x0042 [target 25, skill 482, field3 0, buff 117, duration 10.0]` |
| **retail**, Isle Students | `0x0042 [target 25, skill 2077, field3 0, buff 117, duration 10.0]` |
| **ours**, the probe | `0x0042 [25, 478, 0, 1, 10.0]` |
| **ours**, the probe | `0x0042 [25, 480, 0, 2, 10.0]` |

**Field for field the same shape** — same target slot, `field3 = 0` on both sides,
the same `10.0` f32 duration, and condition skill ids (type_code 8) in both. The
client has nothing in the message to distinguish our application from ArenaNet's,
so it should take the same path.

**THE ONE GAP IS THE BUILD, and it is worth naming rather than waving past.** The
retail capture is **38849**; the probe above ran on the loopback client, which was
**38797** — 52 builds apart. Effect rendering is unlikely to have moved, but
"unlikely" is not a measurement, and this repo has been wrong about a version
assumption before. **CLOSED in §36.7 by rebuilding the loopback client at 38849
and re-running: identical to three decimals.**

### 36.6 Closing the build gap meant building a 38849 loopback client, and a guard stopped the first attempt

**The gap was closeable offline** — the retail build is on disk, since the
operator's own install auto-updated to 38849 (`RUNBOOK` §"the build gate's
'service' is a proxy"). The loopback client was two builds behind the service
anyway, so rebuilding it is maintenance the runbook already prescribes after
every ArenaNet update rather than work invented for this question.

`dump_dh_params.py` on the 38849 install first, because that is the runbook's own
go/no-go: **`GO.`** — `g = 4`, 512-bit prime, struct at VA `0x00a910d8`, so the
crypto scheme did not move. Then `make_custom_client.py` + `make_run_dir.py`:
`B == g^b mod p -> True`, classified `ours`, updater killed, filed at
`vault/run/2026-08-20_21511009c460/`. `dhbuild.py` audits the whole vault clean.

**THE FIRST LAUNCH WAS REFUSED, AND THE GUARD WAS RIGHT.** `contentids`:

> `map 146 0x1B97D: the two archives bind this id to DIFFERENT FILES` — server
> row 7982 is 1,300,036 B crc `0xA0AE500A`, client row 177262 is 1,300,044 B crc
> `0x33F1A289`.

So **build 38849 changed map 146's geometry** — 8 bytes longer, different CRC —
and the server's study archive still holds the old one. Its own words for why
that matters: *"the server would path against geometry the client is not drawing,
and the run would look like it worked."* That is a silent-wrong-answer class of
failure caught before a single packet, and it is the second guard this week to
pay for itself.

**Resolved without touching anything shared.** `vault/dat_study/Gw.dat` is used by
other arcs and other sessions, so re-cutting it to 38849 is not a call this arc
makes alone. `RURIK_DAT` pointed at the 38849 client's OWN archive makes the pair
the same generation by construction — `test_contentids.py` §1 calls that *"the
only pairing in this vault that is coherent today"* and it is what the
2026-08-14 compass run used. **Recorded as owed maintenance:** the server's study
archive is now a build behind the client's, and every default-paired run inherits
that.

With that pairing the guard went green — **"content file ids: 12 of 12 map row(s)
agree across both archives"** — and the launch was then refused a SECOND time, by
a different guard and equally correctly:

> `REFUSING to launch ...6-08-20_21511009c460\Gw.exe` — *"no firewall cage
> names this binary at all. This client carries OUR Diffie-Hellman parameters."*

A newly built ours-DH binary is not in any cage rule, and `PLAN.md` §6.2 is
absolute that such a client must never reach the real service — it does not fail
cleanly, because Stage A completes first with whatever credential the client
autofills. Caging is an **elevated** step by design (`isolate_client.ps1`, no
arguments, which enumerates every client under `vault/run` rather than the single
hardcoded path that once left one uncaged for a day). **So the 38849 re-run is
staged and blocked on one elevated command, and the build gap in §36.5 stands
until it runs.** Everything else about the rebuild is done and verified.

### 36.7 The gap is CLOSED: 38849 behaves identically, so retail players see the ghost

Same probe, same plan, the **38849** loopback client — the exact build the Isle
capture came from. Run `20260821T180010`, verdict PASS, all seven steps confirmed
on the wire first.

| measurement | 38797 | **38849** |
|---|---|---|
| live-icon windows | 2 | 2 |
| treatment window | +16.5 .. +23.5 s | **+16.4 .. +23.4 s** |
| same-state frame noise floor | 0.000 | **0.000** |
| slot change across the late removal | 6.829 | **6.829** |
| control patch across the same removal | 0.000 | **0.000** |

**Identical to three decimal places on a different build.** In both, the live icon
dies ~16 s before the late `0x0044` is sent, and the faded ghost holds until it
arrives.

**So the chain closes without a live run**, and each link is measured rather than
assumed: retail's Student application and our probe's are field-for-field the same
`0x0042` (§36.5); the client cannot tell them apart; and the client's behaviour is
now measured on retail's own build. **A retail player standing in a Student's ring
sees a live condition icon for its stated ~10 s and a dead-looking faded one for
the rest of the stay, while the condition keeps costing health the whole time.**
The Disease that killed the operator in `20260821T152147` did most of its damage
behind an icon that had already visually expired.

*Label: OBSERVED for the client behaviour on both builds and for the message-shape
identity; RECONSTRUCTION for the retail player's experience, since we render our
own messages and not ArenaNet's.* **The one thing not excluded** is an unidentified
opcode that refreshes the client's timer — §8.6 found nothing on the effect channel
in those windows, and no other message is known to touch it, but "we did not find
one" is weaker than "there is none". A single retail screenshot 20 s into a ring
would convert the last link from inference to observation, and it is now worth
exactly that one frame and no more.

### 36.8 SCOPE CORRECTION: the silent extension is ENVIRONMENTAL-ONLY, and §36.3 overreached

**Raised by the owner, 2026-08-21: "any credence to thinking these condition
circles are some sort of hard-coded exception that combat doesn't follow?"**
There is, and checking it found an overreach in this arc's own handoff.

Every effect episode in the vault carrying a duration, scored by close residual
and partitioned by how it was applied:

| applied by | n | residual |
|---|---|---|
| **environmental** — the Isle's torches (984/998/999) and Students (479-486, 2077) | **15** | **LATE, +1.25 s to +55.0 s** |
| cast or attack — 160, 364, 348, 814, 179 | 78 | **never late.** Exact, or early (a cure) |

**All 15 late closures come from the two rung-8 runs** — the only sessions where
the operator deliberately stood in range. Not one cast- or attack-applied effect
has EVER closed late, across six captures and five skills.

**And the same environmental skills close exactly when nobody loiters**, which is
what rules out "those skill ids are special": skill 480 at `-0.00` and `+0.00`,
984 at `+0.00`, 998 at `-0.00` in the rung-6 roster run, and 998/999 at `-0.04`
in the rung-8 run itself once the operator had stepped away. **The variable is
standing in the source's radius, not the skill.**

**SO §36.3's HANDOFF WAS WRONG IN SCOPE.** It said this table "emits a shape
retail does not", reasoning from the silent extension to how our server should
refresh a cast effect. Those are two different mechanisms and the corpus separates
them cleanly. Worse, the cast side does not say what §36.3 implied either:
`effects.EffectTable.apply` already records that retail's 15 overlapping
re-applications are **all under 0.5 s — same-instant doubles, not re-casts** —
each carrying a NEW buff id while the first episode still closes on its own
duration. So retail **stacks** those; it does not extend them.

**The honest state, per mechanism:**

- **Environmental / persistent-area:** retail refreshes silently and delays the
  `0x0044`. OBSERVED, 15 episodes. Our server has no analogue of this source type,
  so there is nothing here to copy or to fix.
- **Cast or attack — WITNESSED 2026-09-17, §49.7:** a recast enchantment is a bare new `0x0042` with a new buff id beside the old one (which closes on its own clock, 3 of 3); a recast stance is `0x0044` then `0x0042` in one batch (3 of 3). Both are what this server already sends. The paragraph below is as written on 2026-08-21.** Retail had **no witnessed case of a live effect being
  deliberately extended at all.** Not silently, not by REMOVE-then-APPLY, not by a
  refreshing re-apply. The 15 overlaps are simultaneity, not extension. **Our
  REMOVE-then-APPLY is therefore unwitnessed either way — it is neither confirmed
  nor refuted**, and §36.3 should not have leaned on the Isle to judge it.

**And the Isle is a training area**, which is the general form of the owner's
point and worth carrying beyond this section: its torches and Students are
pedagogical props built to apply one condition on contact. Generalising from them
to combat is a scope error of exactly the kind [§4](#) warns about elsewhere, and
this section exists because it was made here.

**What survives unchanged.** §36.1-36.2's client behaviour (self-expiry at the
stated duration, then a held faded ghost until the removal) is a fact about the
CLIENT, which receives one `0x0042` and a late `0x0044` and cannot know what
applied them. §36.7's conclusion that a retail player in a Student's ring watches
a ghost also stands — that is the environmental case, measured on its own build.
Only the generalisation to combat is withdrawn.

### 36.9 The re-cast run ABORTED on a bad skill pick, and the pick was a scope error

Run `20260821T184758`, plan `isle_rung8d_recast.txt` (sha256 `beb5ba72...`), seals
AGREE, 3 keys, 2 connections. **Aborted by the operator at the tooltip step, and
correctly.** The plan named skill **348** as "a Warrior SHOUT, recharge 4 s against
a duration observed at 10.0 s ... already on the operator's bar". The bar skill is
**364 = `"Charge!"`**, and the operator read its tooltip: **5 energy, 20 s
recharge** against a 10-12 s duration. Recharge exceeds duration, so it can never
overlap itself and the block cannot run.

**THE ERROR IS WORTH MORE THAN THE RUN, and it is a scope error of the same family
as §36.8's.** The plan's basis for "already on the operator's bar" was that 348
appears three times in capture `20260819T132414`. **That capture is a TOWN
DISTRICT (map 238)**, where other players are casting constantly — an effect
landing in a capture means somebody nearby cast it, not that it is ours. The
capture cannot distinguish the two, and the plan treated an ambient observation as
a fact about our own character. *Appearing in a capture is not the same as being
on our bar*, and nothing in the effect channel carries a source agent to say
otherwise (§8.6's own premise, used here against itself).

**What the aborted run still banked.** Six `skill 160` episodes (Windborne Speed,
the Master of Winds control) and one `skill 364` at `field3 10 / dur 10.0`, all
closing exact — and the operator's tooltip read is the **first operator-confirmed
check of the `364 = "Charge!"` binding**, which [studies/isle §"Rung 8 prep"] had
from GWW alone. The energy column agrees at 5. The rank-13 damage block never ran.

**The requirement, stated mechanically so no one has to guess a name again.** The
block needs a **self-targeted effect whose RECHARGE is shorter than its DURATION**
— both numbers readable off the tooltip by the operator. Measured from the
client's own `s_skill` table via `toolkit/clientscan/skilltable.py`, **build
38849**, filtered to self-target (`target == 0`), profession common-or-Warrior,
playable:

| recharge | duration r0 → r15 | id | type | cost |
|---|---|---|---|---|
| 10 | 10 → 20 | **316** | **Shout** | 5 energy |
| 4 | 10 (flat) | **348** | **Shout** | 4 adrenaline |
| 4 | 1 → 15 | 366 | Shout | 4 adrenaline |
| 4 | 8 (flat) | 346 | Stance | 5 energy |
| 4 | 10 (flat) | 1701 | Stance | 5 energy |
| 2 | 8 (flat) | 1142 | Stance | 1 adrenaline |

**Prefer a SHOUT over a stance, and the reason is not aesthetic.** WIKI (GWW,
"Stance"): *"Only one Stance can be active at any time … using a new Stance will
replace the previous one."* Re-casting a stance is therefore governed by stance
exclusivity and would answer *"how does a stance replace itself"*, which is not
the question §36.8 left open. Shouts carry no such rule. **316** is the cleanest
candidate — energy cost, and at the operator's Tactics ~10 its duration is ~16-17 s
against a 10 s recharge. An adrenaline shout (348, 366) is also fine and has one
advantage: adrenaline charges by hitting, so the block can ride on top of the
rank-13 bench swings instead of needing its own setup.

**348 HAS A NAME as of the same day, from a different arc: it is
`"Watch Yourself!"`** (§33.6, reported by the operator after another run and
agreeing with the client's table on profession, attribute and every checkable
field). That makes it the strongest starting suggestion here — a core Warrior
Tactics shout, 10 s flat against a 4 s recharge, and its adrenaline cost is an
ADVANTAGE rather than a nuisance because the rank-13 bench block already has the
operator swinging: adrenaline charges by hitting, so the re-cast test can ride on
top of the swings instead of needing its own setup.

**But confirm it on the bar before sealing a plan around it** — that is the whole
point of this section, and 348 being named does not make it owned. **Which of
these the operator actually owns is not knowable from a capture.** The next plan
must be built around a skill the operator reads off their own bar, with the
tooltip's recharge and duration quoted back.

*(2026-08-22: what the bar held IS knowable from a capture — by a different
message than the one this section rightly refused. §36.10 reads it back, and it
settles the pick: 348, on the bar, in the newest capture, put there by the
operator themselves.)*

### 36.10 The bar READ FROM THE WIRE: the pick is measured, and the plan is re-staged

**2026-08-22.** §36.9 refused to infer the bar from ambient effect episodes, and
was right to — but retail sends one message that is *about* our own bar:
`0x00DA SKILLBAR_UPDATE`, **self-scoped** on live connections (measured 9/9 in
the `0x00CF` schema row: every connection's GAIN agent is that same connection's
own 0x00DA agent), with the observer resolved by `adrenjoin.whose_agent`'s
property-41 rule. An effect row is ambient; a 0x00DA naming our own agent is
not. The query is now `python toolkit/authsrv/adrenjoin.py --bars` — 58
own-agent bar updates across the corpus, one per census connection (36 ARMED +
22 DARK = 58, a cross-check against §34's own count).

**The readback doubles §36.9's refutation before repairing it:**

- The town capture the aborted plan leaned on, `20260819T132414`, shows its own
  character's bar as `[814, 783, 2, 858, 780, 952, 0, 0]` — **no 348 anywhere on
  it**. The three 348 episodes there were other players', exactly as §36.9
  argued; now measured rather than reasoned.
- Every Isle session from rung 6 through the 18:47 abort ran one Warrior bar,
  `[382, 384, 385, 364, 1, 0, 0, 2]` — three Swordsmanship attack skills
  (type 14), `"Charge!"`, Healing Signet, Resurrection Signet. **None of
  §36.9's six candidates was on it.** The abort was over-determined: 348 was
  not the bar's shout, and nothing else on the bar could have run the block
  either.
- **Capture `20260821T205552` — §33's spend-clock run, two hours *after* the
  abort — is the repair, and it was already in the vault.** Temple connection
  (map 248): the old bar. Isle connection (map 280):
  `[`**`348`**`, 384, 385, 364, 1, 0, 0, 2]`. The operator swapped slot 1
  (382 → 348) at the Temple to arm §33's spend — so the operator **owns**
  `"Watch Yourself!"`, can bar it at will, and had it on the bar in the most
  recent live session.

**The same capture already banks the single-press control.** §33's spend left
one 348 episode on the Isle connection: `field3 10 / dur 10.0`, closed
**expired**, residual under 14 ms (bufflog) — the first operator-cast 348
episode, closing exact at the table's flat 10 s, Tactics 10 in field 3.

**GWW cross-check, joined on ArenaNet's own `id` field**: WIKI (GWW,
`'"Watch Yourself!"'` infobox + §Note, rev. 2026-07-05): id **348**, Core
Warrior Tactics **Shout**, **adrenaline 4, recharge 4**, armor +5…25 **for 10
seconds**, *"exactly requires 80 units of adrenaline"* — agreeing with
CLIENT-DATA on every shared field, including the raw 80 at `+0x38`. **And it
carries one term the client record does not**: *"This shout ends after 10
incoming attacks"*, corrected by the page's own anomaly note to ten
**armor-respecting damage events on the ally**. That is the re-cast
experiment's one false-positive channel — an early `0x0044` from damage wears
exactly prediction (c)'s REPLACE signature — so it is pre-registered in the
plan: the Suits deal no damage, and an early close is attributable to damage
only if ≥ 10 hits landed on the operator inside that episode (countable on
`0x00A3` afterwards). A single stray hit ends nothing and voids nothing.

**Re-staged: `vault/plans/isle_rung8d_recast_v2.txt`**, sha256 `5821fa75…` as
staged (the binding seal is taken at launch), 9 steps. Two design changes from
the aborted file, both lessons paid for: the **rank-13 bench block comes
first**, so a skill surprise can never again zero the whole run; and the
re-cast block **rides the bench swings** — 348's adrenaline cost means every
press is its own `0x00D2` wire event (self-timestamping, independent of the
marks), and four hits (~6 s at sword speed) recharge it inside the 10 s
duration by construction. The tooltip step stays and gates only the re-cast
steps: this section says what the bar WAS on 2026-08-21, never what it is at
the next launch.

*Label: OBSERVED for every wire read (the bars, the 348 episode, the 58/58
cross-check); WIKI for the GWW fields; the ten-damage early end is WIKI only
until an episode shows it.*

## 32. E10 — the recharge gate, read from the residue

**2026-08-21, run `20260821T190847`, loopback, build 38797, server at
`a622237`.** §26.11 item 1, the last loopback-testable item on this channel.
Predictions in `e10-predictions.md`. **The run's designed readout failed and the
run still answers**, which is the part worth reading.

### 32.1 The rig

Bar `[316, **373**, 318, 319, 320, 321, 322, 323]`. Skill **373** costs 120
units and recharges **12 s**; **318** costs the identical 120 and recharges 0.
So treatment and matched control differ *only* in the recharge, and any
divergence cannot be a denominator artefact — the thing §28 showed matters.

The wire did exactly what the test needs: 9 gains capped everything, the spend
of 373, `SKILL_RECHARGE(skill 373, 12s)`, then **4 gains inside the window**,
`SKILL_RECHARGED`, then **2 gains after**. P26 met — the client was sent the
gains and does the per-slot application itself, so the gate under test is its own.

### 32.2 The designed readout is CONFOUNDED, and the data says so itself

| frame | time | s2 (373) | s3 (318) | s4 (319) |
|---|---|---|---|---|
| charged | 23:09:46 | 100.0% | 100.0% | 100.0% |
| post-spend | 23:09:52 | **100.0%** | 80.8% | 63.5% |
| in-window | 23:09:59 | **100.0%** | 100.0% | 100.0% |
| after expiry | 23:10:05 → 23:10:23 | **40.4%** | 100.0% | 100.0% |

**Slot 2 reads 100% immediately after being spent to zero** — and then *drops*
to 40.4% with no spend and no clear on the wire. Adrenaline cannot fall on its
own, so the 100% is not adrenaline: it is the **recharge sweep**, the overlay
`GmSkSlot` draws from the same accessor §26.12 traced, in the same rectangle as
the fill. The internal contradiction is the proof, and no external assumption is
needed for it.

**This is a design error, not a client behaviour.** Testing a *recharge* gate
required a skill with a recharge, which necessarily puts a recharge sweep on the
one slot being measured. E6 never hit it because 317 recharges in 0 s. The two
signals are confounded by construction, and any P24 verdict read off the
in-window frames — either way — would have been the sweep.

### 32.3 The residue answers it anyway

Once `SKILL_RECHARGED` clears the sweep, slot 2's pixels are the fill alone, and
the two hypotheses predict numbers three-fold apart:

| | 373's units | fill | measured |
|---|---|---|---|
| **gate HELD** — 4 skipped, 2 land | 0 + 50 | **41.7%** | **40.4%** ✓ |
| gate FAILED — all 6 land | 150 → capped 120 | 100.0% | — |

**40.4% is 21 of 52 rows; 41.7% is 21.7.** Within one row, and the same
1–2 point agreement E5–E9 produced. **P24 CONFIRMED** — the client skips a
recharging slot, so `0x008219C0`'s single line reaches the display. **P25
CONFIRMED**: the matched 120-cost control refilled 80.8% → 100% from those same
messages, so the skip is specific to the recharging slot and not a dead wire.
**P27 CONFIRMED**: the slot became eligible the moment the recharge expired.

Two independent witnesses now stand behind this rule — this measurement and
GWW's *"recharging skills cannot rebuild adrenaline"* (§26.11 item 3) — where
before there was one line of disassembly.

### 32.4 The lesson, which is the fourth of its kind here

E5 mis-measured on icon art, E6 on a too-strict null, E7 on a whole-frame state
change, and E10 on an overlay sharing the fill's rectangle. **Every one was
caught by an in-frame control or an internal contradiction, and none by
re-reading the code.** The rule this series keeps re-learning: when a readout is
visual, the thing that saves you is another region of the same frame that must
not move — and when a value moves in a direction the mechanic forbids, believe
the contradiction over the metric.

**Still open on this channel, and NOT loopback-testable:** whether a spend
restarts retail's 25 s clock (§26.11's divergence). Our server says no and the
corpus cannot arbitrate — no spend sits inside any of the 15 sampled clear
windows. That needs a **live** capture of a spend followed by 25 quiet seconds,
which is a human-driven run under `PLAN.md` §6.2, not a loopback one.

## 33. The timeout anchors on the last GAIN — a live capture, by 7 ms

**2026-08-21, capture `20260821T205552`, LIVE against the real service**, plan
`adren_spend_clock.txt` sealed before launch (sha `0e73d3ae…`, `plan_sealed:
true`, 3 keys tapped). The last question on this channel, and the only one a
loopback run could not answer.

### 33.1 The question, and why only a live run could settle it

Our server drops a charged bar 25 s after the last GAIN, and `AdrenalinePool.use`
deliberately does not restart that clock. GWW says adrenaline is lost after 25 s
"out of combat" and casting is plainly combat, so the rival reading was at least
as intuitive. **The corpus could not arbitrate**: not one of the 15 isolated
`0x00D0` clears had a `0x00D2` spend anywhere in its window. Only a session that
*creates* that case could decide it, and only retail's own server could be the
witness.

### 33.2 The design, and the one thing it had to avoid

The discriminator is a **gap between the last hit and the spend** — without it
both hypotheses predict the same instant and the run measures nothing. And the
trap: **the spend had to land no hit**, because a landed hit is +25 adrenaline
and would restart the very clock being timed. The plan called for a
self-targeted adrenal skill; the operator spent **skill 348** (type_code 15,
target 0, 80 units), and the wire confirms it worked — **zero `0x00CF` after the
spend**, so the interval is clean.

### 33.3 The measurement

```
last GAIN   t = 18.939
SPEND       t = 36.746      (17.807 s after the last gain)
CLEAR       t = 43.932
```

| anchor | predicts | Δ from measured |
|---|---|---|
| **the last GAIN** (our rule) | 43.939 | **−0.007 s** |
| the SPEND (the rival) | 61.746 | −17.814 s |

**Retail anchors on the last gain, by 7 milliseconds against an alternative
17.8 seconds away.** `AdrenalinePool.use` is correct as written and the
divergence is closed in our favour. n=1 — one episode — but the discrimination
is three orders of magnitude wider than the residual.

### 33.4 What the operator's experience says about the plan

The run worked; the *instructions* were poor, and the operator said so. Two real
defects, recorded because live sessions are expensive and the next plan should
not repeat them:

- **The plan never said the 25 s clock is already running during the pause.**
  From the operator's seat "wait 10 s, spend, now wait 40 more" reads as nonsense
  when the bar is visibly about to drop in 7. The 40 s instruction was
  *experimentally* right — it is what makes a clear at 43.9 meaningful, since a
  spend-anchored clock would not have fired until 61.7 — but an unexplained
  correct instruction is indistinguishable from a wrong one.
- **The pause eats the window, and the plan never bounded it.** The gap came out
  at 17.8 s of a 25 s budget. Eight seconds slower and the bar would have dropped
  *before* the spend and the run would have measured nothing. The plan should
  have said: keep the pause short enough that the spend lands with at least 5 s
  to spare, and if the bar drops first that is a failed attempt, not a result.

The irony worth keeping: the operator's "too slow" execution produced **better**
data than the plan asked for. 17.8 s of separation put the hypotheses nearly
18 s apart instead of 10.

### 33.5 What the same capture cost and gave elsewhere

**Gave, unasked:** the corpus grew 14 → 20 captures, and the energy oracle in
`test_pools` went red on it — correctly. A new property-43 rate,
`0.038823530077934265`, joins to **(2 pips, 17 max)**, and **17 = 20 × 0.85**: a
Warrior's base pool under a −15 death penalty, carrying its 2 pips unchanged.
That is a **second** death-penalty witness for the `f32(0.33)·pips ÷ max`
quantum, from a different capture and a different base than §23's original
(25 → 22), and it arrived *as a test failure* because the armour table had no
17-energy row. The table was too narrow and the model was right.

**Also gave:** a second property-52 resurrect witness, both exactly 1.0.

**And refuted one of our own claims.** `test_adrenwire` §7 asserted the spend's
follower is "always property 50, never 48 or 60", at delta exactly +1 — true of
every spend it had, all of them sword attack skills. Skill 348 follows with
**property 48** (`instant_skill_activated`) at delta **+2**. What survives, 40 of
40, is the half the sender actually needs: **the spend comes first**. The
follower's identity depends on the kind of skill and must not be keyed on.

**Cost, honestly:** the plan asked for light hits TAKEN as a free harvest, to put
a sample under 1% of maximum health and settle the boundary
`pools.damage_units` extrapolates. All 255 new gains carry exactly 25 — they are
landed hits, not damage taken. **The sub-1% boundary is still extrapolated**, and
it is now the cheapest open item on this channel.

### 33.6 Skill 348 is "Watch Yourself!" — and it checks our own `ceil`

**Reported by the operator after the run** (GWW, `"Watch Yourself!"`), and the
client's own table agrees on every field that can be checked:

| | client's record | GWW |
|---|---|---|
| profession | 1 (Warrior) | Warrior |
| attribute | 21 = **Tactics** (`test_attribspend.py:50`) | Tactics |
| displayed adrenaline | **4** | **4 Adrenaline** |
| activation / target | 0.0, target 0 | instant, non-targeted |

**And the displayed 4 is OURS, not the client's.** The record stores only the raw
**80** at `+0x38`; `skilltable.displayed_adrenaline` computes the 4 as
`ceil(80 / 25)`, a RECONSTRUCTION from "a strike is a flat 25, so the displayed
cost is the number of hits needed". GWW saying **4** is therefore an independent
check of that rule — **and on the case that discriminates**, since 80 is not a
multiple of 25 (80/25 = 3.2, where floor gives 3 and ceil gives 4). §26.8's
census found 151 adrenal skills and many of their costs are not multiples of 25;
this is the first time one of them has had its displayed value confirmed from
outside our own decode.

It also explains §33.5's refutation rather than leaving it as an oddity: a
**shout** (`type_code` 15, target 0, instant) is exactly the kind of skill whose
activation would be announced by property **48**, `instant_skill_activated`,
rather than 50, `attack_skill_activated`. The thing that broke the old claim and
the thing that made the run safe are the same property of the same skill —
picking a shout meant no hit could land, and a shout is not an attack skill.

## 34. SKILLS-B1 — the boundary the corpus cannot answer, and the gate it hid

**2026-08-21, no client launched.** `studies/skills` mints `SKILLS-` per
[studies/idents/CONVENTION.md](../idents/CONVENTION.md) §1 — the arc's own
`FINDINGS.md` takes the arc name. Predictions **P28–P31** were sealed before
any scan ran (session scratchpad, sha256 `0b3d6ee7…`); the extractor is
`toolkit/authsrv/adrenjoin.py` and the pins are `test_adrenwire.py` §12–§13.

### 34.1 The question, and why the evidence in hand could not answer it

§33 closed the adrenaline channel except for one line, which `PLAN.md` §8 called
the cheapest thing left: **where does the damage-taken rule stop granting?**
`pools.damage_units` grants `round(pct)` units for `pct` percent of maximum
health lost, and the rounding is measured — 32 sub-25 `0x00CF`s in the live
corpus, 31 joinable to their damage, round fits **31 of 31** where floor fits 14.
But the docstring's own last paragraph names the hole: "A hit for under 0.5% now
grants nothing (it rounds to zero) where the floored reading put that boundary
at 1%. Nothing in the corpus sits in that band."

**That population is selected on the outcome.** It starts from the gains and
looks back at the damage, so every row in it is a damage event that DID grant.
It cannot contain the band where the rule stops. The repair is obvious: run the
join the other way, from every `0x00A3` naming the observer as target, and the
no-gain rows arrive by construction.

### 34.2 The naive answer, and it is spectacularly wrong

Run that inverse census with no other thought and it is clean, large and
completely misleading:

```
damage-to-self events, unambiguous batches   64
  granted something                          32
  granted NOTHING                            32
  largest percentage that granted nothing   7.5000
  smallest percentage that granted           2.5000
```

Read at face value that says retail grants no adrenaline for a hit taking 7.5%
of maximum health — an order of magnitude above the wiki's 1% and above every
granting row in the same table. It also puts **2.5000% granting 3 units in one
row and nothing in another**, which is not a threshold at all: it means the
grant is not a function of the damage.

### 34.3 SKILLS-B1 — the split, and it is total. OBSERVED

The variable is one nobody had stratified on, and it has nothing to do with
adrenaline traffic: **does the observer's own `SKILLBAR_UPDATE` ever name a
skill with a non-zero `adrenaline_units`?**

| | connections | messages | `0x00CF` | `0x00D0` | `0x00D2` |
|---|---|---|---|---|---|
| **ARMED** — ≥1 adrenal skill on the bar | 36 | 98,338 | **918** | **27** | **40** |
| **DARK** — no adrenal skill, ever | 22 | 44,982 | **0** | **0** | **0** |

Not "few" — none. Across 44,982 messages the entire family is absent, spends
and clears included, which is self-consistent in a way that matters: no gain
means no 25-second clock means nothing to clear, and §33 measured that clock at
25.00 s after the last gain.

**The armed column reproduces §4's census exactly** — 918/27/40, and the 886/32
strike split too. That census counts opcodes over the whole corpus; this one
counts them per connection after a skillbar join. Two unrelated queries landing
on the same six numbers is the cross-check that says the stratifier did not
quietly drop traffic.

**Every one of §34.2's 32 no-gain rows is DARK.** Restrict to ARMED and there is
no no-gain row at all: 32 damage events, 32 grants.

### 34.4 The control, because a negative needs a positive

A filtered search that finds nothing proves nothing until it has found something
it should, and here the positive lives inside the negative population. **The
dark connections fought:**

```
DARK   hits landed (damage where the observer is the SOURCE)   45
       completed melee attacks (int property 1, self)          13
       damage taken                                            32
       0x00CF received                                          0
```

GWW's rule is 25 units per successful weapon hit. Thirteen completed melee
attacks earned **zero** messages. Compare the armed side, where the match is
one-for-one: capture `20260818T132739` carries 280 completed attacks and
**280** gains, `20260821T163511` 251 and **251**.

So the silence is a **gate**, not a quiet capture. That distinction is the whole
check — without §34.4 the claim in §34.3 is unfalsifiable.

### 34.5 The gate's variable is CONFOUNDED, and saying so is the finding's other half

Two rules fit all 58 connections identically:

- **Gate A** — the server sends `0x00CF` only when the observer's bar carries an
  adrenal skill.
- **Gate B** — the server sends `0x00CF` only for professions that use
  adrenaline.

Every dark connection is *also* a non-Warrior: bars of profession-7 skills
(814/783/858), profession-4 (153/105), profession-2 (394/446), and two empty
bars. Every armed connection is the *same* Warrior bar (382/384/385 + 364/1/2,
and 348 in the live run). The corpus holds one adrenaline-using character and
three that are not, so it cannot separate A from B and neither may be promoted.

**What separates them is one capture**: the Warrior, in an explorable, with
every adrenal skill taken off the bar, landing hits. Gate A predicts silence;
Gate B predicts 25s. It is a live run and it is cheap, but it is a run — this is
recorded as the experiment, not performed.

**SEPARATED 2026-09-22 without the run — §34.11.** The owner's September
sessions put a level-1 Warrior on [346, 1] and a level-20 A/W into the dark
population, fighting; Gate B is refuted and Gate A shipped. The profession
above was read off the bar's skills; §34.11 reads it off `0x00B7`.

### 34.6 Why nobody saw this from the screen. OBSERVED, from the bytes

The charge worker gates its own repaint on whether any slot actually moved, and
that is arithmetic on three addresses rather than a reading:

```
0x008219B3   33 ff                  xor edi,edi          ; before the loop
0x008219C0   ...                    loop top
0x008219EA   89 0e                  mov [esi],ecx        ; the only slot store
0x008219EC   bf 01 00 00 00         mov edi,1            ; INSIDE the loop
0x008219F6   75 c8                  jne 0x008219C0       ; back-edge
0x008219F8   85 ff                  test edi,edi
0x008219FA   0f 84 ed 00 00 00      je  0x00821AED       ; the shared exit
0x00821A03   d9 05 b4 95 94 00      fld dword [0x009495B4]   ; 25.0f
0x00821A12   68 58 00 00 10         push 0x10000058          ; the UI event
```

The flag starts clear, is set only where a slot is written, and is tested
**after** the loop — and the `je` lands past both the 25.0 and the UI event
push. So a `0x00CF` that no slot accepted repaints nothing, fires no
`0x10000058`, and arms no 25-second timer. §31's blink warning never starts.

It cuts both ways. It is why our own extra traffic is harmless on screen, and it
is why six captures of retail sending nothing at all sat unread for a day.

### 34.7 What this does to the sender: a divergence, deliberately not fixed

`authsrv.player_gains_adrenaline` decided this exact case, in writing:

> A GAIN THAT EVERY SLOT REFUSED STILL GOES OUT, though — full pools, **a bar
> with no adrenal skill on it**, everything recharging.

The argument for it is sound and is about our own clock. The **empirical
premise** underneath it is now measured false: retail does not send one. And
retail's silence is deeper than the gain — it sends no `0x00D0` either, so there
is no clock to keep honest, which is the half the docstring's reasoning could not
have known.

**The sender is NOT changed, and that is a ruling rather than an omission.**
Implementing Gate A means picking one side of §34.5's confound on zero evidence,
and the two errors are symmetric and both invisible: §34.6 shows the client
no-ops on an unaccepted 207, and §30 shows an unarmed bar has no overlay to
repaint. What lands is the record — the docstring now names the divergence, and
`test_adrenwire` §12 pins the measurement so the capture that separates A from B
goes red on the number it changes.

**SUPERSEDED 2026-09-22 — §34.11: the sender is changed.** The captures that
separate A from B arrived as ordinary play rather than as the staged run, and
the gate (Gate A, the current bar) ships behind `--no-adren-bar-gate`.

### 34.8 P28–P31, scored

- **P28 — "there exist damage-to-self events with no gain." CONFIRMED, wrong
  reason.** 32 of them, and not one is sub-threshold.
- **P29 — "a single threshold, `max(pct | no gain) < 0.5`." VOID.** The
  prediction assumed the population was homogeneous. It is two populations, and
  the "boundary" it would have reported is 7.5%. Worse for the prediction than
  that: §34.C shows the corpus does not pin the rule's FAMILY either, so 0.5
  was never the only candidate it was being scored against.
- **P30 — "`units == round(pct)` on every joined pair." CONFIRMED**, re-fitted
  on the armed rows alone: **round 32/32**, ceil 17, floor 15. The floor→round
  correction survives the stratification that destroyed the boundary claim, and
  the ledger closes: 886 strikes beside damage DEALT plus 32 grants beside
  damage TAKEN accounts for all 918 gains with no residue.
- **P31 — "1- and 2-unit gains exist if the corpus holds damage in
  [0.5, 2.5)." VACUOUS.** No armed row sits below 2.5000%. The armed range is
  2.50–11.04%.

**The sub-1% boundary therefore stays UNVERIFIED**, and now for a known reason
rather than an absence. It was called the cheapest open item on this channel; it
is not one — but it is now the best-specified one, because §34.C reduces it to
a single light hit with two named rules predicting opposite outcomes.

### 34.A The blind replication, and the two rows it recovered

Run as `studies/review`'s pattern: two agents over the same corpus, each handed
one rival hypothesis and told to **refute it**, neither shown the other's answer
or mine. One got `round`, cutoff 0.5%; one got `floor`, cutoff 1.0% — GWW's own
rule. The floor agent returned `hypothesis_survives: false` and reached the bar
gate independently, by its own route and with its own scanner: *"the split is
exact: 11/11 connections with an adrenal bar carry 207; 0/4 without one do, and
those 4 are where all 32 nulls sit."* Two derivations, no shared code.

It also found **two rows my scan lost**, and both are corrections to this
document rather than footnotes:

1. **Damage arrives on `0x00A2` as well as `0x00A3`.** The sourceless
   three-field float channel carries exactly ONE damage event at the observer in
   the whole corpus — a 6.25% hit granting 6 units. My scan read only `0x00A3`,
   which left that gain as an orphan with no damage anywhere near it. **My scan
   printed the orphan and I moved on.** The replication chased it instead, and
   that is the difference between 31 joined and 32.
2. **Two batches carry two identical hits and two identical gains.** I excluded
   them as ambiguous; identical values make every assignment the same pair, so
   they attribute by symmetry and excluding them was over-caution.

**The ledger closing is what says nothing else is left**: 886 + 32 = 918, every
gain in the corpus explained by exactly one partner, no residue.

One thing in its report is wrong and is worth naming rather than quietly
dropping: it proposed reading the rounding constant out of the client's charge
worker to promote the boundary from INFERRED to OBSERVED. There is no such
constant to read. `0x00CF` carries the units already computed, and the worker
does `add eax,[ebp+0xc]` — the message's own field (§26.2, `test_adrenwire` §9).
The damage→units conversion happens on ArenaNet's server, which we cannot
disassemble, and that is precisely why this question needs a capture.

### 34.B The check with no free parameter, which the replication supplied

Every one of the eleven distinct armed percentages is an exact integer over 480:

```
 2.500000037%  = 12/480      6.041666493%  = 29/480
 2.708333358%  = 13/480      6.250000000%  = 30/480
 2.916666679%  = 14/480      7.083333284%  = 34/480
 3.125000000%  = 15/480      8.124999702%  = 39/480
 3.541666642%  = 17/480     11.041666567%  = 53/480
 5.000000075%  = 24/480
```

**480 is the smallest denominator that does it** — searched 1..2000, and the
only others are 960, 1440 and 1920. And the observer's **int property 42**, its
maximum health, reads **480** on the same wire, from a message none of that
arithmetic touched. Two independent witnesses to the same number; a wrong
denominator has no reason to produce eleven integers.

**What it also bounds, honestly:** every granting row in the corpus is that one
character at 480 health. So the corpus cannot separate "one unit per 1% of
maximum health" from "one unit per 4.8 raw damage points" — the wire sends the
fraction, which makes the percentage reading natural, but that is an argument
and not a measurement. **Any second maximum health in a granting connection
settles it**, and that is a cheaper capture than the boundary one.

### 34.C The error bar, and the rival family that changes the experiment

Both agents fitted the rule as a FAMILY rather than testing two candidates,
which is the shape this repo asks for — and the second one found a survivor
neither I nor the first had considered. Re-derived here from the bytes rather
than taken on report, all three over the same 32 armed rows:

```
floor(pct.k) == units     k in [1.200000, 1.086792)     EMPTY
round(pct.k) == units     k in [1.000000, 1.040000)     survives
ceil (pct.k) == units     k in (0.905660, 0.960000]     survives
```

**The floor family is empty under EVERY rescale**, which is a much stronger
statement than "floor fits 15 of 32": no charging rule of the form
`floor(k x damage-fraction)` can produce this wire, whatever `k` is — so
"retail charges on pre-mitigation damage and then floors" is refuted too, not
just the plain reading. GWW is explicit and is outside it: *"rounded down, so
taking less than 1% of your maximum health causes you to gain no adrenaline"*
— **and the threshold in that sentence is a consequence of the rounding, so
with the rounding refuted the threshold cannot be imported either.**

**The two survivors disagree about exactly the thing we went looking for.**
`round` grants nothing below ~0.5%; `ceil` grants **one unit for any damage at
all**. Same 32 rows, opposite answers at the low end. Also surviving, and worth
naming because they read like the same rule and are not: `max(1, round(pct))`
and `max(3, round(pct))`.

**So the experiment is now one observation wide.** One point of damage on the
480-health character in the corpus is 0.208%:

| damage taken | `ceil` predicts | `round` predicts |
|---|---|---|
| 1 point (0.208%) | **1 unit** | **0 — no message at all** |
| 2 points (0.417%) | 1 unit | 0 |
| 4 points (0.833%) | 1 unit | 1 unit |

One light hit taken by a character carrying an adrenal skill separates them, and
a `0x00CF` either arrives or it does not. That is a far better-specified probe
than the one §33's live plan asked for — it said only "light hits taken", and
got 255 gains of exactly 25 — and it is what belongs in the next live plan.
`pools.damage_units` implements `round`; if `ceil` is right, our server is
silent where retail sends a unit.

### 34.D The skeptic pass, and the row the corpus nearly answered with

A third agent was given both derivations and told to break them, not to
summarise them. It re-ran the whole corpus itself. Both headline sets survived
— the census, the gate, the 32/32 fit, the self-identification — and it
corrected both agents on something neither had checked, then found the row that
matters most in this whole section.

**THE NEAR MISS.** The two surviving families disagree only below about 1%.
**Exactly one damage event in the entire corpus lands in that band** — capture
`20260810T235916`, connection `…:49163`, observer 31, one hit for 1 point of
100 maximum health — **and that observer's bar carries no adrenal skill**, so
there was nothing to charge. Every other damage-taken event anywhere in twenty
captures is at or above 2.5%. The corpus came within one connection of settling
the question and did not.

**And its value is 0.999999978%, not 1%.** The wire bits are `0xBC23D70A`,
which is `-0.009999999776482582`. At four decimal places it prints as
`1.0000` — *exactly the value where round and ceil agree*. From the bytes it
sits just below, where they do not. **Three independent readers printed it
rounded and all three read past it**: both replication agents, and my own
scanner, whose `%7.4f` did the hiding. `adrenjoin.py` now prints nine decimals
and calls the band out by name, and `test_adrenwire` §12 pins the row.

**A CORRECTION TO BOTH AGENTS, and it is a method note rather than a number.**
Both read the observer's maximum health as a *set* of the property-42 values in
the connection. Property 42 is re-sent **on change**, so the value in force at a
damage event is not the last one in the stream: connection `…:52294` fights its
whole session at **120** and receives 102 some 1,197 messages later, and
`…:52606` fights at 120 and receives 140 three thousand messages later. The
in-force set across the eight damage connections is **{100, 120, 480}**, not
the {100, 102, 120, 140, 480} one agent published — and that agent's own
integrality control is arithmetically impossible as stated (2.5% × 140 = 3.5
points). Re-run with the temporally correct denominator the control *holds*,
64 rows of 64. **Its conclusion survived; its stated evidence did not**, which
is a distinction worth keeping. Nothing in §34 moves: those rows are excluded
anyway, and all four ARMED connections carry only 480. `adrenjoin.whose_max_health`
now reads it temporally.

**THE SHARPEST THING IT SAID ABOUT §34.3's OWN LOGIC.** The bar split is
justified by an outcome-independent variable, and it is still true that *of the
64 damage rows the gate removes 32, and all 32 removed rows are nulls while 0
of the 32 kept rows are nulls.* A gate whose removals are 100% single-valued in
the outcome can only ever delete nulls and never grants — so **any boundary
read off the gated population is void by construction**, not merely
under-powered. §34 does not read one off it. That is the difference between a
declared limit and a concealed defect, and it is why the boundary line in
§34.8 says UNVERIFIED rather than a number.

**Two things it got wrong, checked from the bytes rather than taken on report.**
Its closing recommendation — and the first agent's too — was to read the
rounding constant out of the client's charge worker and promote the boundary to
OBSERVED without a capture. **There is no such constant.** `0x00CF` carries the
units already computed; the worker does `add eax,[ebp+0xc]`, the message's own
field (§26.2, `test_adrenwire` §9). The conversion happens on ArenaNet's server.
Two agents proposed it independently, which makes it worth writing down as a
dead end rather than leaving for a third to rediscover. And one agent's ceil
interval had both endpoints inverted, `[0.905660, 0.960000)` for
`(0.905660, 0.960000]`; the skeptic caught it and §34.C already has it right.

**One denominator worth stating so §34.3 is not over-read.** Of the 36 ARMED
connections, **25 saw no combat at all** — no damage dealt, none taken. The 918
gains come from 11. The split in §34.3 is a *bar* split over every usable
connection; the control in §34.4 is scoped to the 17 connections that fought,
where it is 11 armed with gains and 6 dark without, 17 of 17.

### 34.9 The lesson, which is the series' fourth of the same shape

§27, §28, §29 and §32 each caught a metric that lied, every time by an in-frame
control rather than by re-reading code. This is the fifth, and the first with no
pixels in it: **the stratifier was a variable the question never mentioned.**
The reading that survived was not the careful one — a careful reader gets 7.5%
and a clean-looking table of 59 rows — it was the one that noticed 2.5000%
appearing twice with two different answers and refused to average them.

Worth naming for the next session: the defence that worked here was **checking
whether the population could contain the answer at all** before believing what
it reported. `adrenjoin.whose_agent` carries the same rule one level down, and
the comment there is load-bearing: identifying the observer by "the agent a
`0x00CF` names" is right on every connection that has one, and would have
deleted the entire dark population from the denominator — hiding the finding
rather than producing a wrong number, which is worse.

**And a second lesson, which is mine to wear twice.** My scan printed an
unexplained row — one gain with no damage in its batch — and I read past it
because the finding I was chasing was already large. Then my scan printed the
single most decisive row in the corpus as `1.0000%`, at a precision that landed
it exactly on the value where the rival rules agree, and I read past that too.
**Neither was a reasoning error; both were display and scope choices made
before there was anything to see.** A scanner's output format is part of its
evidence. The blind replication chased it and
found a whole message channel. An orphan in a ledger is a lead, and the ledger
closing at 918 of 918 is the only thing that says there are no more.

### 34.10 Both experiments are staged (2026-08-22) — and §8's band was wrong

The two runs this section reduces to are written and waiting on an operator
live session: `vault/plans/adren_boundary.txt` (the sub-percent boundary) and
`vault/plans/adren_gate.txt` (Gate A vs Gate B). Neither has run; both go out
via RUNBOOK's live procedure with `--plan`, sealed at launch as usual.

Staging caught a defect worth its own paragraph: `PLAN.md` §8 specified the
boundary hit as "3 to 5 raw points on a 480-health warrior", and by §34.C's own
table that band is 0.63–1.04%, where **every surviving family answers
"1 unit"** — an operator collecting exactly what the plan asked for would have
measured nothing, and nothing on screen or in the log would have said so. The
discriminating band is **1–2 points at 480 health** — damage below 0.5% of
maximum under every surviving rescale (the round family's grant threshold is
0.4807% at its interval's worst k) — and 3-point hits only join it at 640+
maximum health. §8 is corrected in place, and the plan file carries the band as
a table over max health so a rune-swapped session computes its own.

The boundary plan folds in §34.B's rider — any granting hit at a maximum
health other than 480 separates "% of maximum health" from "per 4.8 raw
points", and a +health mitigation build may supply the second denominator for
free — and both plans carry an in-run positive control, because §34.4 is the
measurement that says silence without one is void.

**2026-09-22: the gate plan is WITHDRAWN UNRUN — §34.11. The corpus answered
its question without it. The boundary plan stands.**

### 34.11 The gate half, closed at the desk: the confound broken by tapes already on disk, the third rival read, Gate A shipped (2026-09-22)

**Desk work, no client launched — DESKWORK-D5 step 1
([studies/deskwork/PLAN.md](../deskwork/PLAN.md) §3 D5).** Extractor:
`toolkit/authsrv/adrenjoin.py --by-connection` (new this day); pins:
`test_adrenwire.py` §12 (six checks added, 77 → 83) and `test_pools.py` §11d3
(floor 132 → 136). The staged plan `vault/plans/adren_gate.txt` (sha256
`686e76a4…`) is **WITHDRAWN UNRUN**, recorded in `PLAN-LOG.md` the way
RUN-AGGRO-LAKESIDE-2 was; the file is left where it is, because editing it
would change the hash a seal compares.

#### 34.11.1 The corpus on 2026-09-22

`adrenjoin.py` reproduces the fidelity judge's run to the digit:

| | connections | messages | `0x00CF` | `0x00D0` | `0x00D2` | hits landed | melee finished | damage words | deaths |
|---|---|---|---|---|---|---|---|---|---|
| **ARMED** | 46 | 145,399 | **1,163** | 39 | 40 | 1,073 | 977 | 93 | **4** |
| **DARK** | 49 | 142,209 | **0** | **0** | **0** | 367 | 210 | 312 | **11** |

The armed side's four player deaths are three that cleared and one that did not;
see §34.11.4, where that one witness is the whole reason the death clear's cause
(the bar, or the charge held) stays CONTESTED.

§34.3's total split is unchanged in kind and eight times larger in the dark
side's fighting. What is new is who the dark characters are.

#### 34.11.2 The character, read off the wire and not off the bar — Gate B REFUTED

§34.5's "every dark connection is also a non-Warrior" was read from the
**bar's** profession bytes. `--by-connection` reads the **character**: `0x00B7
[agent, primary, secondary, flag]` for the observer's own agent, cross-checked
against the `0x0059` appearance nibble (90 of 90 connections agree) and against
the `CHARACTER_INFO` summary's profession on the capture's auth channel, joined
on the appearance dword (77 of 77 agree). The level is int property 36 for the
observer's agent (the summary agrees on 76 of 77; the one disagreement is
`20260819T132414`'s third connection reading 3 where the login summary said 2 —
a level-up inside the session). Five connections carry no property 36 for the
observer: four map-transfer stubs of 280–300 messages and the 6112 auth channel.

DARK by (primary, level): (1, 1) ×13, (2, 1) ×4, (2, 3) ×6, (4, 1) ×4, (5, 1)
×2, (5, 2), (7, 1) ×2, (7, 2) ×7, (7, 3), **(7, 20) ×4**, and 6 with no level
read. **Thirteen dark connections are a primary Warrior**, and four more carry
Warrior as the secondary. The ones that fought:

| capture | connection | `0x00B7` | level | bar | hits landed | melee finished | damage words | deaths | family |
|---|---|---|---|---|---|---|---|---|---|
| `20260914T180058` | `10.0.0.210:56301` | 1 / 0 | 1 | [346, 1] | 18 | 18 | 112 | 2 | 0 |
| `20260915T155656` | `10.0.0.210:51922` | 1 / 0 | 1 | [346, 1] | 17 | 17 | 24 | 0 | 0 |
| `20260915T164906` | `10.0.0.210:51282` | 1 / 0 | 1 | [346, 1] | 1 | 1 | 22 | 0 | 0 |
| `20260917T224104` | `10.0.0.210:62557` | 7 / 1 | 20 | [782, 780, 775, 781, 346] | 127 | 86 | 24 | 4 | 0 |

163 landed hits, 122 completed melee attacks, 182 damage words and 6 deaths by
characters who ARE Warriors, and not one message of the family — while the
primary Warrior (0x00B7 1 / 0) on [382, 384, 385, 364, 1, 2] at level 20
(`20260818T132739` `10.0.0.210:53202`, the same account) lands 280 hits and gets
280 gains. (The damage-words column supports no inference — Gate B rests on the
hits landed — and it was miscopied as 0 for `164906` and totalled 160; the
tool's `--by-connection` says 22 there and 182 across the four.) The
Frenzy-and-Healing-Signet bar costs 0 adrenaline in both slots, which is why a
Warrior can be dark at all. **Gate B is refuted at level 1 for a PRIMARY
Warrior and at level 20 for a SECONDARY one**, and the level caveat — "maybe a
level-1 character earns nothing" — dies on the second row. The corner no tape
covers is a *primary* Warrior above level 1 on a dark bar; said here rather than
assumed. (The A/W's other fighting tape, `20260917T160915` conn `52569`, reads
`0x00B7` 7 / 0 — no secondary yet — 127 hits, 0 gains: a dark Assassin, which
is why the pinned Warrior count is 4 and not 5.)

#### 34.11.3 The third rival — "the LEARNED set holds an adrenal skill" — REFUTED

Raised by the fidelity judge before any "corroborated" could be written, and
it needed **both** libraries, because §47.1 measured that the account set
(`0x001D`) and the character set (`0x00DB`) are different objects and neither
contains the other. `--by-connection` decodes both bitmaps to ids and joins
them to content's `adrenaline_units`. Two facts about how they ride first:
`0x00DB` is on every map connection; `0x001D` is sent **once per session** (1 of
the 8 usable connections on `20260818T132739` carries it), so it is read per
capture and labelled so in the report.

- **The account library carries 348 / 382 / 385 on every capture in the
  corpus** — the owner's account has three adrenal Warrior skills unlocked. So
  the account half of the rival is refuted on all 14 dark connections with a
  landed hit: 0 gains.
- **The A/W's CHARACTER library carries 348 / 382 / 385 too** (42 ids), on both
  of its fighting connections — `20260917T160915` and `20260917T224104`, 127
  hits each, 0 gains.

A character that has *learned* adrenal skills and does not have one *on the
bar* is sent nothing. OBSERVED, 2 connections for the character set and 14 for
the account set. (How an Assassin with no secondary holds Warrior skills in its
character library is not asked here; the wire says it does.)

#### 34.11.4 The clear is gated on the dark side (OBSERVED); its cause on the armed side is CONTESTED

Eleven player deaths on dark connections (`0x0026 [me, 4]`), zero `0x00D0`.
So retail's silence covers the death clear, not only the gain — which is what
puts the gate on `kill_player`'s clear and not only on the sender. That much is
OBSERVED, 11 of 11.

**But the armed side has a counter-witness, and it costs the "OBSERVED" this
paragraph used to claim for the whole rule.** The corpus holds four player
deaths on ARMED connections:

| capture | connection | gains before death | `0x00D0` at death |
|---|---|---|---|
| `20260917T090355` | `10.139.166.60:53310` | 19 | yes |
| `20260917T090355` | `10.139.166.60:53310` | 21 | yes |
| `20260917T090355` | `10.139.166.60:53310` | 26 | yes |
| `20260821T152147` | `10.0.0.210:63150` | **0** | **no** |

The three deaths on `20260917T090355` clear; the one on `20260821T152147` — an
armed bar `[382, 384, 385, 364, 1, 0, 0, 2]` that landed **0 hits on the whole
connection**, so its pool never charged — does not. Two rules fit the dark side
and split on that one row:

- **"clear when the bar is ARMED"** (what this server ships) fits **14 of 15**
  deaths — it mispredicts the armed-empty death, sending a `0x00D0` the tape did
  not.
- **"clear only when the pool HELD CHARGE"** fits **15 of 15**, and subsumes the
  dark observation (a dark bar never charges).

The charge rule is the better fit and the smaller claim, but the row that
separates them is **a single witness** — an armed bar that happened to land no
hits — and the corpus cannot tell "empty pool" from "no fight this life". So the
cause is **CONTESTED, n=1**, and nothing is reshipped on it: `kill_player` keeps
the bar gate (its dark half is OBSERVED, 11 of 11) and the armed-empty
divergence is recorded as an OPEN lead rather than fitted away
("refuse to guess"; "a negative needs a positive control").

#### 34.11.5 What stays UNOBSERVED, measured as such

- **The dark-to-armed transition.** The bar is a timeline (`0x00DA` whole,
  `0x00D9` per slot), and **no connection in the corpus flips its bar's
  armed-ness mid-connection — 0 of 95.** Bars are edited in outposts:
  `20260917T224104` conn `57677` goes [782, 780, 775, 781, 0, …] → [… 346 …]
  (dark → dark), `20260819T132414` conn `52606` adds 780 then 952 (dark →
  dark). 0 hits land before the observer's first own `0x00DA`; 0 family
  messages arrive while a bar is dark. So what retail sends on the first hit
  after an adrenal skill is dragged onto a dark bar *in an explorable* is
  unobserved. The gate reads the bar at gain time and starts sending on the
  next hit — the smaller claim, said at the call site, pinned in `test_pools`
  11d3 as the control.
- **A dark-bar hero.** Every hero that received a `0x00DA` in the corpus
  carries the same armed bar [1, 2, 322, 346, 348, 382, 385] — 4 of 4, on
  `20260914T005758` and `20260916T150306` — so no tape shows a dark-bar hero
  gaining or dying.
- **The rounding half's (0, 0.5 %) hit** — unchanged from §34.10; the
  boundary plan stands.

#### 34.11.6 What shipped, and what did not need to

- `authsrv.bar_holds_adrenal()` reads `SKILLBAR` **at call time** — the list
  `--skills` rebinds, the store rebinds at the instance load, and the `0x005C`
  handler rewrites in place on an in-game drag (SANDBOX-B7) — so the gate is
  on the CURRENT bar.
- `player_gains_adrenaline` returns before the grant and the send when the bar
  is dark, **the AD4 zero included**: the zero rides a damage word *to an
  adrenal bar* (§53.4); the dark side's 312 damage words carry none.
- `kill_player`'s `0x00D0` is gated on the same predicate (the book still
  clears). The other two clear sites need none and are left alone, said why:
  `energy_tick`'s 25 s clear cannot fire from a dark pool (`AdrenalinePool`
  keeps only slots with a cost and `tick` wipes only a bar that had charge),
  and `cast_tick`'s Final Thrust clear completes an adrenal skill cast FROM
  the bar, so the bar is armed by construction. That last site was guarded
  for an hour and `test_agentlife`'s Final Thrust fixture — which stubs
  `skill_cost` to (0, 0) — showed the guard reading the stub rather than the
  bar; the guard came out and the comment stayed. `0x00D2` is unreachable on
  a dark bar for the same reason.
- **The hero.** `hero_pool_gain` has read the row's bar since JARIN
  (2026-09-14) and `sync_hero_body_bar` rewrites that row on an edit, so its
  gain was already gated — the SKILLS-WK class ran the other way here: the
  rule reached the hero and not the player for eight days. `hero_pool_clear`
  now follows the same flag, labelled RECONSTRUCTION at the site (the player's
  half is OBSERVED, the hero's has no dark witness; silence is the smaller
  claim).
- `--no-adren-bar-gate` is the revert: the pre-2026-09-22 sender.
- **The client sees nothing either way** (§34.6's EDI flag; `test_adrenwire`
  §13). This is wire fidelity and one staged live run removed from the owner's
  queue, not something on screen.

#### 34.11.7 What this corrects

§34.5's "this corpus cannot separate them" was true of the corpus on
2026-08-21 and is dated now; §34.7's "deliberately not fixed" is superseded;
`player_gains_adrenaline`'s docstring carries the new paragraph in place of the
ruling. `PLAN.md` §8.2's SKILLS-B1 line keeps only the rounding half.

## 35. SKILLS-T1 — the client names its own skill types

**2026-08-21, no client launched, no wiki consulted.** Closes `PLAN.md` §8
item 5 and `studies/presearing/MANIFEST.md` §8's eleven-code follow-up.
Tool: `toolkit/clientscan/typenames.py`; pins: `test_typenames.py` (16 checks).

### 35.1 The question, and the method that was not needed

`MANIFEST.md` §8 named ten of the client's skill `type_code` values by **Rosetta
stone**: take skills whose type is independently known, read their `+0x0C`, take
the majority. It left **eleven UNKNOWN** — 9, 11, 16, 20, 21, 22, 24, 25, 26,
27, 28 — and called naming them "a bounded follow-up using the same method, two
or three known-name skills per code". `PLAN.md` §8 item 5 singled out **16**,
because it is on this server's own default bar and named nowhere.

That method would have worked, and it would have needed an outside source for
every code. It was not necessary. **The client names its own types**, in one
switch, and the whole derivation is arithmetic on its bytes.

```
0x004F9BF0   the namer     mov eax,[edi+0x0C]     <- the type_code field
                           cmp eax,0x0E           <- type 14 leaves here
                           ...                    <- 17, 18, 22 leave here
                           push eax ; call 0x004F9DD0
0x004F9DD0   the switch    mov eax,[ebp+8] ; dec eax ; cmp eax,0x1C
                           ja  0x004FA7A0         <- the default arm
                           jmp [eax*4+0x004FA7BC] <- 29 entries
```

Every case body computes a **string id**. And the default arm carries the single
strongest piece of evidence that this is the *type* namer rather than some other
switch on some other field — ArenaNet's own sentence, at `.rdata 0x0094E614`:

> "There is no string to describe skill %u's type."

### 35.2 The control, which is the whole argument

The jump-table index is `type_code - 1`, and **the bias is the only free
parameter in the entire derivation**. At that bias, all ten codes `MANIFEST.md`
named years earlier — by a completely different method, against outside sources
— resolve through the owner's archive to exactly the ten words it used:

```
 3 Stance      4 Hex Spell   5 Spell     6 Enchantment Spell   7 Signet
 8 Condition  10 Skill      12 Glyph    15 Shout             19 Preparation
```

**Ten of ten.** Then the same check is re-run at bias 0 and bias 2 and scores
**zero and zero**. That second half is what makes the first mean anything: one
step either way breaks every known code at once, so the agreements cannot be a
table of plausible words meeting plausible guesses.

**The exactness in that check is load-bearing, and it was learned by breaking
it.** The first cut asked `expected in got` — and "Spell" is a substring of
"Hex Spell", so the shifted control scored 1 instead of 0 and went red on its
own leak. A weaker comparison leaves the headline check looking fine while
quietly poisoning the control meant to falsify it.

### 35.3 The table. OBSERVED

Ids, with the case body that computes each. **The ids are what the repo commits;
the words are resolved at run time from the owner's own archive**, per
CLAUDE.md's rule for authored text.

| code | case body | base | elite | word | previously |
|---|---|---|---|---|---|
| 1 | `0x004F9E37` | 34036 | — | Blessing | not in our mirror |
| 2 | `0x004F9F3C` | 931 | — | Party Bonus | not in our mirror |
| 9 | `0x004FA74E` | 32224 | 32225 | **Well Spell** | UNKNOWN |
| 11 | `0x004FA6FC` | 32222 | 32223 | **Ward Spell** | UNKNOWN |
| 13 | `0x004FA59B` | 52243 | — | Title | not in our mirror |
| **16** | `0x004FA30B` | **942** | 943 | **Skill** | **UNKNOWN — item 5** |
| 20 | `0x004FA2B9` | 938 | 939 | **Pet Attack** | UNKNOWN |
| 21 | `0x004FA602` | 958 | 959 | **Trap** | UNKNOWN |
| 23 | `0x004FA100` | 32219 | — | Environment Effect | not in our mirror |
| 24 | `0x004F9FA3` | 32220 | 32221 | **Item Spell** | UNKNOWN |
| 25 | `0x004FA549` | 954 | 955 | **Weapon Spell** | UNKNOWN |
| 26 | `0x004FA167` | 38863 | **39729** | **Form** | UNKNOWN |
| 27 | `0x004F9FF5` | 36382 | 36383 | **Chant** | UNKNOWN |
| 28 | `0x004FA0AE` | 18450 | 18451 | **Echo** | UNKNOWN |
| 29 | `0x004FA047` | 51773 | — | Disguise | not in our mirror |

Type 26's elite is **not** base+1 — its body is `and eax,0x362; add eax,0x97CF`
rather than the usual `or imm; shr 2` — and the test pins that as the one
documented exception, so a later reader does not "fix" 39729 to 38864.

### 35.4 Item 5's answer is a genuine oddity

**`type_code` 16 is displayed as "Skill" — and so is `type_code` 10, from a
DIFFERENT string record.** 942 and 960 are two rows of the archive carrying the
same English word (and the same word in French, German and Italian). Two enum
values ArenaNet chose to label identically: not an alias, and not a collision in
our decode. The test asserts **both** halves, because either alone reads wrong.

The bodies differ, and that is where the distinction lives:

- **10** branches on the touch and half-range flags and has variant names for
  each.
- **16** has no variants and instead **asserts both flags are clear** — two
  `GmSkHelpers.cpp:139` sites at `0x004FA30B..0x004FA34B`.

~~**Why the engine needs two enum values for one word is NOT ANSWERED.** Nothing
here read the code that *consumes* the distinction, only the code that names it.
That is the honest residue of item 5, and it is a different and much smaller
question than the one that was open this morning.~~

**ANSWERED 2026-08-27 — see §40 (SKILLS-T2).** A caller of the row resolver at
`0x008CAF5D`, in `GmCtlSkList.cpp`, reads the type field and gives **type 16 its
own arm** alongside types 6, 14 and 22 — while **type 10 has no arm at all** and
falls to the same default as the rest of the enum. So they are not two labels for
one thing: 10 is the default and 16 is an exception carved out of it, which is
the shape this section's own structural profile predicted. Over the resolver's
101 call sites, 18 read the type field and exactly one compares against 10 or 16.
The bound is tight rather than closed, and §40.2 says why.

It also explains the structural profile that made 16 puzzling before the switch
turned up. Its 21 rows are **100% instant, 100% self-targeted, 100% carrying a
duration** — perfectly homogeneous, which is not what a catch-all looks like;
type 10's 55 rows are 13% / 31% / 38%, which is. Two "Skill" codes, one of them
the untargeted-self-buff case, fits both shapes.

### 35.5 What the client refuses to name, on purpose

Three refusals, each read from the bytes, and each recorded as a **fact** rather
than a gap in our work:

- **17 and 18** short-circuit in the namer (`sub ecx,0x11; je` then
  `sub ecx,1; je`) to string id 1, the null record. The client has **no word**
  for them. They are also the two largest populations in the full 3,443-row
  client table, so this is the largest thing still unnamed — and it is unnamed
  *by ArenaNet*, not by us.
- **14** never reaches the switch: `cmp eax,0x0E` intercepts it and tail-calls
  `0x004FAE60` with the weapon and combo fields, because an attack's displayed
  name depends on the weapon and the chain slot ("Sword Attack", "Off-Hand
  Attack"). Its jump-table slot is the default arm.
- **22**'s name is not a constant either. It is resolved in the namer from title
  track `+0x2A` and profession `+0x28`: `0x28` gives one string, else profession
  2 gives another and 8 a third, and anything else logs a failure at
  `0x0094E728` naming the family. ArenaNet's own internal word for it is
  **"global skill"**.

### 35.6 What is NOT promoted, and why

- **Type 2, "Party Bonus".** The image says it plainly and the constant is
  verified, but its members are not in our mirror and no second witness exists.
  The tool carries the id; nothing calls it settled.
- **The flag-conditioned variants** — "Touch Hex Spell", "Flash Enchantment
  Spell", "Half Range Spell". Those strings are reachable from the case bodies
  (OBSERVED) but **which flag bit selects which was not verified**, so
  `TYPE_STRING_ID` deliberately holds only the unflagged name. A mapping nobody
  checked is the thing this repo keeps getting burned by.
- **Type 14's weapon sub-table.** A second switch at `0x004FAE60` that nobody
  walked to the end. Treat any list of its returns as a floor.
- **`effects.py`'s `EFFECT_TYPES`.** Several newly-named codes — Well Spell,
  Ward Spell, Item Spell, Weapon Spell, Form, Chant, Echo — are plainly timed
  effects, and adding them is a *behaviour* change that needs its own evidence
  and its own run. Named here as a follow-on, not done.

### 35.7 How it was found, which is the transferable part

Three agents, three routes, none seeing the others: the image, the skill table's
structure calibrated on the ten known codes, and the live wire corpus. **The
image route won outright** — it went at the code rather than hunting for arrays,
found the accessor by cross-reference, and scanned for MSVC compressed switches
whose bound sits in 20..36. The structural route independently derived the
two-name split for type 22 from nothing but the corpus composition, which is the
strongest cross-route agreement in the set; the wire route contributed a witness
for 16 and a partition of the activation properties.

**And the judge caught the image route citing the wrong address for its own
correct conclusion** — `0x004FA2F9` where the arithmetic is at `0x004FA34B`;
the earlier address is the tail of the *type-20* case and holds `or esi,0x0EA8`
→ 938. The number was right, the citation was one case body early. That is
worth more than it looks: a wrong citation makes a later reader's audit fail and
look like the claim failed. Everything published here was re-read from the image
before it was written down, and the test pins `0x004FA34B` specifically.

## 38. SKILLS-R1 — what answers a refused press, on the wire and on screen

> **Numbering note, 2026-08-22 — this section was written as §36, and so was
> §36 above.** Two `## 36.` headings collide as one markdown anchor, which is
> the append collision `toolkit/seclint.py` was written for a day earlier — and
> it caught this one, red on `test_seclint.py`. **This** one moved, because §36
> above is the `effect_silent_extend` probe, which had ALREADY been renumbered
> once (out of its own `## 32.` collision) and is cited from `studies/isle`
> §36/§36.7/§36.8, `effects.EffectTable.apply`'s docstring and this file's
> own positive control. §38 is the next free number; §37 below is SKILLS-R2
> and keeps its number, so the R1/R2 pair reads 38 then 37 in file order — this
> document is already non-monotonic (§26.12/§26.13 and §36 all sit before
> §32) and renumbering a section that does NOT collide is churn with no gate
> behind it. Old references resolve here: `PLAN.md` §8 item 2 now says §38.

**2026-08-22.** Closes `PLAN.md` §8 item 2, which had been open since E2 on
2026-08-20. Three blind recon routes (image / corpus / our own catalog), a
judge, then a build and a loopback run: `20260822T105929`.

### 38.1 Retail's answer is three messages, not one

```
0x005D CHAT_MESSAGE_CORE    [coded string = the reason's string id]
0x005E CHAT_MESSAGE_SERVER  [playerId, channel 7]
0x00E2                      [agent, skill, copy]     <- releases the slot
```

**OBSERVED.** Of 143 skill presses in the 20-capture corpus, **43 are declined
and 43 are answered** — none is met with silence. 40 of 40 carry the full
batch in exactly that order with those exact neighbours; the other 3 send the
bare `0x00E2` with no sentence, so **the sentence and the release are
separable**.

I reproduced every number independently before writing any code: the `0x005E`
channel census `{6: 1, 7: 40, 10: 96}`, the 40/40 adjacency, `0x00E2` at 53
occurrences with third field 0 in **53/53**, and `codedstr.encode_id(1960)` =
`0x8A8`, matching the observed wire word bit for bit.

**Channel 7 is the warning panel, from two sides.** The image: GmView frame
`0x1000007F` dispatches to `0x004E4EFC`, whose first instruction is
`cmp dword ptr [edi],7` — channel 7 is the only value that body accepts, and
the panel is named `TxtError`. The wire: all 40 channel-7 tags sit in refusal
batches, while 96 channel-10 and 1 channel-6 tag in the same captures never do.
That contrast is the discriminating negative; a channel byte appearing in both
populations would have proved nothing.

**`0x00E2` cannot carry the reason, and that is measured.** It shares dispatch
stub `0x0091F650` with `0x00E3`, and the stub forwards three payload dwords and
**not the opcode** — the worker literally cannot tell them apart. So the reason
rides the chat line and the opcode only releases the slot. (`0x00E4` and
`0x00E5` have distinct stubs in the same table, which is the contrast proving
the sharing is real rather than an artifact of how we read the table.) Retail
answers a refusal with `0x00E2` **43 times** and with `0x00E3` **zero**.

`0x00E2` is unnamed in `messages.json`, in `overrides.json` and in GWCA's
`Opcodes.h`. It is named here as `GAME_SMSG_SKILL_REFUSED`.

### 38.2 The run. P19 and P20 CONFIRMED

Bar `317,863,318,319,320,321,322,323`. Skill 863 was chosen for one property:
**recharge 0**, which removes the recharge confound entirely.

| frame | press | server | on screen | orb |
|---|---|---|---|---|
| `2-key` | 317, adrenal, 0 units | REFUSED, #1960 | **"Not enough Adrenaline."** | 25 |
| `3-key` | 863, 25 energy, have 25 | **ACCEPTED** | "Order of Apostasy" cast bar, glyph, sparkles | **0** |
| `4-key` | 863, have 7.83 | REFUSED, #1961 | **"Not enough Energy."** | 8 |

**The middle row is the in-frame control and it is what makes the other two
interpretable** — it separates "presses are being seen" from "the refusal did
something", and it fired unambiguously.

**P20 is the one that mattered. 1961 was a RECONSTRUCTION and is now OBSERVED.**
The corpus contains **zero** energy refusals — all 43 declines are `0x0027`
attack-skill presses and 0 of 49 `0x0046` casts was ever refused, because the
operator never ran out of energy (as of that date: two later tapes, `20260914T005758` and
`20260916T213125`, carry 17 wire witnesses of #1961 — §57's fix-pass note). So 1961 rested
on the archive text plus its position one record after 1960's. A different sentence on
screen would have
refuted it. The right one appeared.

### 38.3 P21 REFUTED, and it is a real refinement

I predicted the sentence would appear **both** as a panel and as a chat-log
line. It does not. **The chat log is empty in all three frames** — the
channel-7 line renders only as the floating red text above the character and
never enters the log. So channel 7 is not "a chat channel that also draws a
panel"; it is a panel channel that the log ignores.

### 38.4 THE INSTRUMENT WOULD HAVE MISSED THIS ENTIRELY

The pre-registration named this as the trap most likely to kill the run, and it
was right. The refusal text renders at roughly **(880–1060, 520–540)** — and
the harness screenshot scorer masks the player-body rect
`~(850,300)-(1120,760)` to suppress idle animation. **The sentence lands dead
centre of the mask.**

Measured 2026-08-18 against the `0x00B9` callout, that mask ate 53% of a known
UI element's changed pixels and would have scored a lone banner at 95 scattered
anti-aliased pixels — noise under any threshold. Had this run been scored the
usual way it would have reported a null, and the null would have been read as
"the message does nothing."

**This is the fifth metric trap in this series and the first one caught in
advance** — §§27, 29, 30 and 32 each caught theirs with an in-frame control
*after* the fact. What caught this one was declining the instrument before the
run, on the strength of a measurement someone had already written down.

### 38.4b THE HARNESS RETRACTED THIS RUN'S VERDICT, and it is recorded here

`RUN VERDICT RETRACTED: the run passed its checkpoints, then the client died
during the hold.` The same machinery that voided E5 fired again, and a run whose
verdict was retracted must say so in its own write-up rather than in a summary
somewhere else.

**It does not touch the readings, and the timestamps are why:**

| | time |
|---|---|
| adrenaline refusal frame `2-key` | 11:00:26 |
| control frame `3-key` | 11:00:35 |
| energy refusal frame `4-key` | 11:00:43 |
| **94 further hold frames** | 11:00:44 → **11:04:19** |
| client exits, code **0**, no error dialog | ~11:04:20 |

The three measured frames precede the exit by about **three and a half
minutes**, the gamesrv log carries all three complete press/answer exchanges
before them, and the harness's own crash check says it plainly: *"no error
dialog within 12 s — the client exited WITHOUT one, which is a clean exit
rather than a silent crash."* The last frames before the exit are logged
`skipped: client not foreground`, so the window lost focus first.

**And it is worth stating what this rules out, because it is the obvious
worry:** the new messages did not destabilise the client. A client killed by a
malformed `0x00E2` or a bad coded string dies AT the press, with a dialog or a
nonzero code; this one drew both sentences correctly, kept running for 94 more
frames with normal effect traffic (`effect 863 on agent 1 expired, 5.03s of
5.0s`), and then exited cleanly.

**AND THE EXIT IS EXPLAINED — THE OPERATOR CLOSED IT, because I gave them no
reason not to.** This was written as "unexplained" for about ten minutes until
the owner said so: *"i exited since you left it on my screen without a timeout
or indication when it would finish."*

That is a defect in how the run was invoked, not in the client. `--keep-open`
**without `--hold`** means exactly this, and `session.py` says so in the flag's
own help — *"Without `--hold` it holds until you close the client."* So the run
parked a live game window on the owner's screen with no end condition and no
progress indication, and then the harness logged their reasonable response to
it as a client death. The retraction is real, its cause is a badly chosen flag,
and the lesson is that **an agent-driven run must bound its own hold**:
`--keep-open --hold N`, with N sized to the action script plus a margin.

This is the same failure as the live-capture plan of 2026-08-21 (§33.4), from a
different direction: **a wait that is not bounded and not announced.** Twice in
two days, once in prose and once in a flag.

**AND THERE WAS A FOURTH PRESS, THE OPERATOR'S — it is accounted for and it is
a free witness.** While the window sat open the owner pressed slot 2 once. The
log carries four `0x8046 USE_SKILL`, not three, and the extra one is at line
**214**, after every measured event (lines 141–169) and after frame `4-key`.
So the readings above are clean; this is stated because a run with unlogged
operator input is a run whose readings cannot be trusted, and the check is
cheap.

What it adds is worth more than the tidiness. That press was **ACCEPTED** —
energy had regenerated to 25 and the cast drained it to 0 again — and it came
**after two refusals on that same bar**. So a slot that has just been refused
still takes a fresh press: the `0x00E2` release does not leave the slot
unusable, and it is a HUMAN-driven confirmation rather than another
harness-scripted one. That is a small piece of evidence on §38.8's open
question about the ~10 s re-animation, and it arrived by accident.

### 38.5 Two corrections the routes needed

**The judge corrected the corpus route on the single anomalous line.** It had
filed the one non-1960 channel-7 message as a recharge refusal. Resolving the
text settles it the other way: that press is **the only one in the corpus with
target == 0** — 1 of 1 against 0 of 42 — and 1934 is *"Invalid attack target."*
The genuine recharge refusal is a **different** press 0.66 s earlier, and it is
**silent**; 1964 ("That skill is still recharging.") never appears on any wire
we hold. Neither route could have caught this alone — the corpus route
deliberately refused to resolve text, the image route had no wire.

**And the schema route had the right fact with the wrong conclusion.** It found
that 226 and 227 share a dispatch and concluded `0x00E2` was therefore
disqualified as a carrier of "refused". That sharing is exactly *why* the
design works, and its own standing warning — "a survey keyed on a name cannot
find a thing nobody named" — predicted the miss, because `0x00E2` is unnamed.

### 38.6 The code's own comment was wrong about itself

`authsrv.py`'s resource gate carried this, and both halves are now refuted:

> *"What retail's server does when a client presses an unaffordable skill is
> UNOBSERVED on our corpus: the client may well swallow the press itself and
> never send `0x0046` at all, in which case this branch is unreachable in a
> real session."*

It is observed, 43 times. And the branch is the hot path rather than a dead
one: E2 watched our client send a 25-energy press with 7.70 energy, and
retail's own clients send 43 declined presses — including one **inside a live
recharge window**, which also means `ChCliApiUseSkill`'s recharge bail does not
cover the attack-skill send path.

### 38.7 A third test that had grown up around our silence

Two `test_pools` checks asserted `sent == []` on a refusal. That was right about
the cast cycle and wrong about the wire. **This is the third time in this arc a
test defended a shape retail never produces** — the energy debit order and the
adrenaline gain order were the first two.

The intent survives and is sharper: not "nothing was sent" but "exactly the
refusal batch, and nothing from the cast cycle", with `cast_cycle_ops()` naming
what a refusal may never emit. Same argument as the other two: pin a shape
against a census, not against whatever the sender happened to do first.

### 38.8 What is still open

- **What ends the ~10 s slot re-animation E2 saw**, and whether ~10 s is real
  at all. The only release in the image is the `0x00E2` refcount decrement.
  Either there is an unread client-side timeout or 10 s is simply how long the
  operator watched. **NOT FOUND**; all three routes left it open.
- **The reason ids for the rest of the 1934–1993 block.** They live server-side
  and are not derivable from a client that only renders what it is handed.
- **Two silent skill-384 declines** (pool exactly == cost, no recharge window)
  may be a fourth refusal class. Recorded, not fitted. **2026-09-22:** the
  committed replay (`adrenreplay.py`, animref §19's note) finds them in
  company — 20 of the 39 reason-1960 refusals also arrive with the client-rule
  slot exactly at cost, while all 45 accepted presses do too; so the "exactly
  == cost" declines **may share a gate with** those twenty — a second gate of
  up to twenty-two behind reason 1960 — but the two 384 declines carry **no**
  reason string on the wire, so their membership is RECONSTRUCTION (inferred
  from the shared "full slot", not read), and the gate is unidentified either
  way.
- **String ids 1928–1933** are RC4-encrypted archive records and unreadable.

## 37. SKILLS-R2 — the "~10 second" re-animation is a 1-second loop that never stops

**2026-08-22.** §38.8's first open bullet, and the last thing `PLAN.md` §8
item 2 was waiting on. Two routes that share no method: an A/B loopback pair
(`20260822T114025` released, `20260822T114206` silent) and a static hunt through
the pinned image. **Both answer the same way, and the answer is a negative.**

### 37.1 The question, and why it was only answerable today

E2 (2026-08-20) watched a refused press re-animate its slot for *"about 10
seconds"* against a server that answered with nothing. Two candidates: **(a)** a
client-side timeout expires the pending-cast entry, or **(b)** nothing does, and
the ~10 s is something else.

Until 2026-08-22 our server *was* the silent case, so (b) had no contrast to be
measured against. §38 put `0x00E2` on the wire, and `--refusal-silent`
reproduces the old server exactly — **one flag, one difference**, which is the
arm the recon judge asked for and the only reason this is a measurement rather
than an argument.

### 37.2 The run. P22 and P23 CONFIRMED

One press per arm, identical scripts, 1.27 s frames, 39.2 s hold. Slot 1
changed-pixel count against the previous frame; slot 8 is an in-frame control
that was never pressed.

| | arm A, released | arm B, silent |
|---|---|---|
| slot 1, every frame after the press | **0** | **still animating at 39.2 s** |
| slot 8 control, all 32 frames | 0 | **0** |
| `0x8046` presses vs a 1-action script | 1 | 1 |

**Arm B was still changing in its final frame — the hold ended before the
animation did.** Nothing was observed to stop it.

**The cross-arm control is what makes this attributable.** Same slot, same
skill, same map, same script; the only difference is whether the release went
out. An idle shimmer in the icon art would have moved in arm A too, and arm A
is flat zero in all 32 frames. And `0x00E2` stopping it within a single frame is
an independent confirmation that the release does what §38 says.

### 37.3 The static route: (b), with a positive control that could have refuted it

Three structural facts, each re-read from the image by me before publication:

1. **The removal path has exactly one root.** Every link in the release chain
   has a single caller and zero data words holding its VA, closing to the RECV
   table: `0x00823090` ← `0x00822B70` ← `0x008148C0` ← stub `0x0091F650`, which
   both `0x00E2` and `0x00E3` resolve to. **Only a received message reaches the
   decrement.**
2. **The entry has nowhere to keep a deadline.** It is 8 bytes and both dwords
   are spoken for — `mov [eax+edi*8],ebx` writes the key
   `(skillId<<16)|copy` at +0, `mov [eax+edi*8+4],1` writes the refcount at +4.
   ArenaNet names the second itself: **`ChCliSkill:955  pending->refCount`**.
   No timestamp, no float, so a per-entry expiry is structurally impossible
   without a parallel store — and only three code sites in the whole image
   compute `&pendingSkills` (insert, release, and an `rtl::Array` destructor),
   none of them time-driven.
3. **The overlay loop has no terminating condition.** The casting overlay is
   created and destroyed solely by GmCtlSkImage msg `0x62`, whose value is the
   entry's existence copied verbatim through UI event `0x1000005B`. Its tick
   accumulates dt, advances a counter every **0.0625 s**
   (`.rdata 0x00951030 = 00 00 80 3d`) and **wraps at 16**
   (`0x008CF93B cmp eax,0x10`). No countdown, no self-destruction.

**THE POSITIVE CONTROL IS WHAT MAKES THE NEGATIVE WORTH ANYTHING.** A search
that has never found a timeout cannot be trusted to report their absence, so
the same method was pointed at a timer we already knew existed — and it
recovered the adrenaline blink end to end: the arm (`fld dword [0x009495B4]`,
raw `0000c841` = **25.0**, broadcast `0x10000058`), the route through
GmSkSlot to GmCtlSkImage msg `0x5A`, and the store's **per-frame float
subtraction** `fsub dword [edi]` with its latch at zero. That idiom is not a
wall-clock read at all, so it would have been invisible to a clock-xref sweep —
the method found it anyway, and applied to the pending array it returns nothing.

**A free correction to §31 came with it:** the blink window is the last
**4.0 seconds** (`.rdata 0x00941B98 = 00 00 80 40`), which is why §31.3 saw the
oscillation only near the end of the 25 s and never earlier.

### 37.4 The answer, and where the operator's number came from

**There is no client-side timeout. The "~10 seconds" is not a duration the
client enforces** — against a silent server the entry persists and the overlay
loops indefinitely. E2's number was how long the operator watched.

And both routes independently landed on the same explanation for *why ten*:
**the overlay loop is exactly 1.000 s** (16 × 0.0625). "About ten seconds" is
about ten cycles of a loop that looks the same every time — which is precisely
what a repeating animation with no endpoint looks like to someone deciding when
to stop watching. **Labelled RECONSTRUCTION**, because nobody asked the operator
to count cycles and the run cannot distinguish "watched ten loops" from "watched
for ten seconds".

### 37.5 MY MEASUREMENT WAS GARBAGE FIRST, AND ITS OUTPUT SAID SO

`png.read` returns `(pixels, width, height, COLOUR TYPE)` — the fourth value is
the PNG colour type, **not** the channel count. I used it as a stride, so a
truecolour image (type 2, three bytes a pixel) was read three bytes at a stride
of **two**: every index wrong, every comparison a comparison of overlapping
garbage.

**The tell was in the first output and I did not act on it.** Two *separate
runs* produced byte-identical numbers — 2906 and 3079, twice. Two independent
runs of a live game agreeing to the byte is not a result, it is a diagnostic,
and I read past it and went looking at the crop geometry instead. `png._CHANNELS`
is the real mapping.

**Its second effect was worse than the first**, and is the reason this is
written up rather than quietly fixed: with the wrong stride, *both arms read
zero for every frame*. That is a NULL — and it is the exact null the
pre-registration had named as "the rig is wrong, neither arm is interpretable."
The plan's own stopping rule caught it. Had the plan not named that null in
advance, "no change in either arm" is a perfectly publishable-looking finding
that would have said the opposite of the truth.

**A period claim was declined at the right moment, for the wrong reason.** After
the fix I measured the cycle at lag 11 (14.0 s) or lag 16 (20.3 s), both weak,
and refused to publish a period from 32 aliased samples. The static route then
gave the true period: **1.000 s.** I sampled a 1 s signal at 1.27 s — far past
Nyquist — so both candidates were aliasing artifacts. The refusal was correct;
the reason I gave for it ("the sampling cannot resolve it") happened to be
exactly right, which is luckier than it should have been.

### 37.6 What is still not established

- **The character's own cast animation in AgentView.** Property 60 queues action
  event kind `0x19` with two payload dwords and **no duration argument**; where
  its length comes from, and whether AvChar retires it independently, is
  **NOT FOUND**. If anything ends *visibly* on its own, this is where it lives.
- **A second path that could clear the overlay while the entry lives**, flagged
  and explicitly not settled: GmSkSlot's full refresh at `0x00543020` sends msg
  `0x62` with a hard-coded false when its cached slot pointer is null, without
  consulting `IsSlotCasting`. What would put a slot in that state is unknown.
  **UNVERIFIED**, and it is the one candidate that could still make a slot
  appear to stop on its own.


---

## 39. SKILLS-A1 — the enemy's skill damage ignores armour, and that is CORRECT for the bar it ships with

**A filed defect, REFUTED at a desk before it was built.** Reviewed 2026-08-27.
No client launched.

### 39.1 The asymmetry is real

`land_swing` scales incoming melee by the player's armour
(`authsrv.py:12133-12137` — `roll_hit_location`, `player_armour_at`,
`dealt *= armour_multiplier(armour)`). `land_skill` does not: it computes
`dealt = float(damage[0])` (`:12347`) and goes straight to `taker_damage`.
`armour_multiplier` has exactly two references in the whole server — its
definition and that one swing site.

Read alone, that looks like a hole with a one-line fix, and it was filed as one.
**Applying an armour term to skill damage would have made this server WRONG.**

### 39.2 What GW1 actually does — WIKI, and it is the opposite of the obvious guess

> **WIKI (GWW, "Damage" §Properties, rev. 2020-08-11):** "Skills dealing shadow
> damage, holy damage and damage without a specified type (skills with
> descriptions that state *"&lt;number&gt; damage"* or *"+&lt;number&gt;
> damage"*), ignore the target's armor and the skill deals exactly its stated
> amount of damage." And: *"+&lt;number&gt; damage"* always comes in addition to
> regular, armor-respecting, damage.

Corroborated on a second page, with a refinement that matters here:

> **WIKI (GWW, "Armor-ignoring damage" §Sources, rev. 2020-03-28):** typeless
> damage; shadow damage; **most holy damage** — "however, holy damage from
> **weapons** does not ignore armor (e.g. from wands, staves, or any weapon
> enchanted to deal holy damage)"; **bonus damage from attack skills**.

So armour-ignoring is a property of the DAMAGE TYPE and the source, not of
"skill versus swing". A blanket multiplier over `land_skill` would have applied
armour to three of the four kinds that must not have it.

### 39.3 Scored against our own content — 3 of 5 rows are already right

`content/world.toml` carries 20 `skill_effect` rows; five are damage-bearing,
and the type lives in the wiki-sourced `scale_means` prose:

| skill | `scale_means` | GW1 rule | our behaviour |
|---|---|---|---|
| 194 (Flare) | `Fire damage` | armour **applies** | **missing armour — the real gap** |
| 431 | `Fire damage` | armour **applies** | **missing armour — the real gap** |
| 312 | `Holy damage` | armour **ignored** (skill, not weapon) | ignores it — **CORRECT** |
| 322 | `+ Damage` | armour **ignored** (attack-skill bonus) | ignores it — **CORRECT** |
| 323 | `+ Damage` | armour **ignored** (attack-skill bonus) | ignores it — **CORRECT** |

**And the live scope is smaller still.** `land_skill` is the ENEMY's path, and
the default `ENEMY_SKILL_BAR` is `276, 253, 312, 289` (`authsrv.py:8210`). Of
those only **312** is damage-bearing, and 312 is one of the three that is
already correct. **On the shipped configuration the omission is not a defect at
all.** Flare reaches `land_skill` only when an operator passes
`--enemy-skills 194`.

### 39.4 CORRECTION to my own first pass — the structure already exists

The paragraph that stood here said the damage type "does not exist in a
structured form" and that a fix would need a new content column. **That is
wrong, and it understates what this server already models.**
`authsrv.py:2443` carries `SCALE_MEANS_DAMAGE`, which maps the wiki-sourced
prose key to a resolution mode:

```
SCALE_MEANS_DAMAGE = {"Holy damage": "standalone",
                      "Fire damage": "standalone",
                      "+ Damage":    "additive"}
```

And the `additive` half is **already right for the reason GWW gives**. An
attack-skill bonus rides its weapon swing — `cast_tick` calls
`hit_enemy(..., bonus_damage=bonus)` (`:10658`), so the swing under it takes the
normal armour-respecting path and only the bonus is added, which is exactly
GWW's *"+&lt;number&gt; damage always comes in addition to regular,
armor-respecting, damage."* The `standalone` half calls
`hit_enemy(..., exact=..., swing=False)`, and the parameter is named `exact`
precisely because it means "the stated amount, unscaled".

So the gap is **one missing distinction inside `standalone`**, not a missing
column: `Holy damage` is armour-ignoring and `Fire damage` is not, and the map
gives them the same value.

### 39.5 What is actually open, and the two directions differ

Verified by calling the server's own resolver at `ENEMY_SKILL_RANK = 12`:

```
default bar 276 -> None   253 -> None   312 -> (46, 'standalone')   289 -> None
194 -> (56, 'standalone')   431 -> None   322/323 -> (34, 'additive')
```

Two corrections to §39.3 fall out. **Skill 431 is not reachable as damage at
all** — it resolves to `None` despite carrying `scale_means = "Fire damage"` —
so the gap is **Flare (194) alone**, not two skills. And 312's 46 is the number
a filed report read as "the player took 46 a hit through AR 45": that is holy
damage correctly ignoring armour, not a defect.

**INCOMING (`land_skill`, the enemy casting at the player) is fixable.**
`player_armour_at` exists and `land_swing` already uses it, so a `Fire damage`
cast can be scaled. Reachable only under `--enemy-skills 194`.

**OUTGOING (`hit_enemy(exact=...)`, the player casting Flare at a creature) is
NOT, and the reason is a measurement rather than an oversight.**
[studies/presearing/R4C2-FEASIBILITY.md](../presearing/R4C2-FEASIBILITY.md)
records that **armour has no property id in any channel across 22,524 messages**
and rules that it be *struck, not deferred*. There is no creature armour value
to apply, so the outgoing side must stay unscaled until one exists — and writing
one from the wiki would close the loop on itself, since wiki armour is
back-computed from observed damage.

Three traps for whoever does it, all visible from the table above:

1. **Do not key on "is it a skill".** The rule is the damage type plus the
   source; `land_skill` is the wrong place to hang a blanket decision.
2. **`+ Damage` is not simply armour-ignoring** — the bonus ignores armour and
   the weapon hit under it does not. Our two rows model only the bonus, so they
   are right today; a future row that models the whole attack is not.
3. **Holy damage splits by SOURCE, not by type** — skill holy ignores armour,
   weapon holy does not. A column called `damage_type` alone cannot express that.

**Status: the filed item is REFUTED as filed.** What replaces it is narrower,
needs a content column rather than a code change, and is not on the default
path. `ARMOUR_TERM` and `armour_multiplier` are untouched and remain correct for
the swing path, which is where `studies/isle` rung 7 measured them.

### 39.6 Why the Flare fix is NOT made here — the armour VALUE is unsettled

> **SUPERSEDED 2026-09-09 by §43 (SKILLS-FA).** The probe this section proposes
> could not have answered the question — on loopback OUR server computes the
> number — and the corpus did: one caster, one skill, one target is one value on
> every pair (68 of 68 hits, the player's included). The term is shipped; the
> rest of this section is kept as the record of why it waited.

The type question is settled (§39.2): Fire is armour-respecting. **Which armour
number a spell scales against is not**, and GWW is genuinely ambiguous on it.

> **WIKI (GWW, "Armor rating", rev. as fetched 2026-08-27):** "Armor-respecting
> damage includes all damage from attacks and most spells dealing elemental
> damage. Exact armor depends on the damage type, but also in the player's and
> heroes' case, **on the piece of the armor that is hit**." — and then the
> per-location odds table is introduced as the chance "to be hit" by an
> **attack**, while a separate sentence says "the damage multiplier can also be
> found for ***non attack*** skills" via a formula that names no location.

So a spell may roll a body location like a swing, or may resolve against a
single rating. `land_swing` rolls one; copying that into `land_skill` would be
**inventing the answer**, and this project's rule is that an unmeasured choice
does not get made silently. Left unfixed, deliberately, with the residual
recorded rather than papered over.

**What would settle it, cheapest first.** One caged loopback run with
`--enemy-skills 194` and a DELIBERATELY LOPSIDED armour set — a very low head
piece against high everything else — casting Flare repeatedly. If the damage is
single-valued the spell resolves against one rating; if it comes in five
buckets in the 3/2/1/1/1 proportion, it rolls a location like a swing. That is
a HUD/number readout, not a model-appearance verdict, so it is agent-drivable.

### 39.7 What DID get confirmed: all three armour constants match the wiki

Checked while answering the above, and worth recording because it is the kind of
agreement nobody re-verifies:

| constant | ours | WIKI (GWW, "Armor rating") |
|---|---|---|
| `HIT_LOCATION_ODDS` | chest 3, legs 2, feet 1, hands 1, head 1 (of 8) | chest 3/8, legs 2/8, feet 1/8, hands 1/8, head 1/8 |
| `ARMOR_BASELINE` | `60.0` | "Having 60 armor rating is regarded as the baseline" |
| `ARMOUR_DIVISOR` | `40.0` | "every gain of 40 points of armor rating cuts 50%" |

And the divisor is independently CORROBORATED rather than merely copied:
`studies/isle` rung 7 fitted it from retail damage at **39.5, 95% CI
[37.30, 42.00]**, containing 40. Wiki and a measurement of our own agreeing,
from sources that share nothing.

---

## 40. SKILLS-T2 — §35.4's residue is ANSWERED: type 16 has a consumer, and type 10 is the default

**Desk only, 2026-08-27, pinned build 38797.** §35.4 closed with: *"Why the engine
needs two enum values for one word is NOT ANSWERED. Nothing here read the code
that CONSUMES the distinction, only the code that names it."* Something does
consume it.

### 40.1 The consumer, at `0x008CAF5D`

A caller of the id→`s_skill` row resolver reads the type field and branches:

```
008CAF5D  call 0x5a88b0          ; resolve the row -> eax
008CAF65  mov  ecx, [eax + 0xc]  ; ecx = type_code
008CAF68  cmp  ecx, 0x10         ; TYPE 16
008CAF6B  jne  0x8caf72
008CAF6D  lea  ecx, [edi + 0xa]  ;   <- its own arm
008CAF70  jmp  0x8caf99
008CAF72  cmp  ecx, 6      / je 0x8caf90
008CAF77  cmp  ecx, 0xe    / je 0x8caf87
008CAF7C  cmp  ecx, 0x16   / jne 0x8caf99
008CAF99  mov  edx, 0xb          ; the default everything else falls to
```

**Type 16 has an arm. Types 6, 14 and 22 have arms. Type 10 has none** — it
reaches `0x8caf99` with the rest of the enum. So the pair is not "two labels for
one thing": **10 is the default case and 16 is an exception carved out of it**,
which is exactly the shape §35.4 predicted from the structural profile (16's 21
rows are 100% instant / self-targeted / duration-carrying, 10's 55 rows are
13/31/38 — "two 'Skill' codes, one of them the untargeted-self-buff case").

**MODULE: `GmCtlSkList.cpp`**, the skills-list control — nearest assert site
`0x008cb0b1 GmCtlSkList:3294 title < TITLES`. **RECONSTRUCTION, not measured:**
the arms feed a value that is then packed by shifts
(`shl esi,0xc / add esi,edi / shl esi,8 / add esi,ecx / shl esi,8`), which reads
as a sort or grouping key for the list. Nothing here proves what the packed word
is used for.

### 40.2 The census, and its bound

`0x00988ED0`, the `s_skill` table base, has **0 rel32 references and exactly 2
words holding the VA** — `0x005A861C` (`mov eax,0x988ed0`) and `0x005A88DA`
(`add eax,0x988ed0`), both inside the resolver family at `0x005A88B0`, which has
**101 direct call sites**. Over those 101:

| | |
|---|---|
| read a `+0x0C` field within 96 bytes | **18** |
| compare against `0x0A` (10) or `0x10` (16) | **1** — and it is 16 |

**This is a TIGHT bound, NOT a closed one**, and the difference matters for how
much the "only one" is worth. `codescan` states its own limits: it cannot see
indirect calls, vtable dispatch, or an address the image computes rather than
stores. The 96-byte window misses a read that happens further out or through a
pointer spilled and reloaded — the first version of this scan matched only
`[eax+0x0C]` and found 3, until its own control showed the known namer reads
`[edi+0x0C]` and was invisible to it. **18 is a floor of a floor.** What the
result supports is *"the distinction is consumed, here"*, not *"nowhere else"*.

### 40.3 The control that earned its place

The first run of this scan reported a confident **"0 call sites read the type
field"** — because it called a PE method that does not exist, mapped every VA to
`None`, and searched empty windows. The positive control (require the KNOWN
namer's `mov eax,[edi+0x0C]` at `0x004F9C48` to be visible before believing any
zero) is what caught it, and it is why §40.2's numbers are worth reading at all.


## 41. SKILLS-DW — Deep Wound's maximum, and the status word every condition carries (2026-09-09)

**What this closes.** `effects.py` listed six of the ten conditions as
modelled-nothing; Deep Wound (482) comes off that list, and on the way the
census found a whole channel this server had never sent: the agent STATUS
WORD that rides behind every condition, hex and enchantment on retail's wire.
Both ship, each behind its own revert flag, with the probe that scores them
registered below before it ran.

### 41.1 The retail join, mechanised — OBSERVED

`studies/isle` §8.2 read the one capture with a Deep Wound by eye: property 42
moved 480 → 384 on the apply and back on the close, twice. `toolkit/authsrv/
deepwoundjoin.py` now does the join over the whole live corpus with the
prediction in its docstring (P1–P4), and `test_mechanics` §19 pins it with no
free parameter:

```
20260821T155022 10.0.0.210:59491->3.233.201.47:80
  APPLY t=80.424  agent 25 buff 117  max 480 -> wire 384 (predicted 384)  prop-42 at +2 msgs, +0.000 s
  APPLY t=150.696 agent 25 buff 113  max 480 -> wire 384 (predicted 384)  prop-42 at +2 msgs, +0.000 s
  CLOSE t=106.063 agent 25 buff 117  wire 480 (restores 480)              prop-42 at +2 msgs, +0.000 s
  CLOSE t=163.896 agent 25 buff 113  wire 480 (restores 480)              prop-42 at +2 msgs, +0.000 s
      batch: [0x42 (25, 482)] [0xF1 (25, 34)] [0x9F (42, 25)]      # apply
      batch: [0x44 (25, 117)] [0xF1 (25, 0)]  [0x9F (42, 25)]      # close
482 applies 2: joined 2, exact x0.8 2; closes 2/2 exact; stray prop-42 0; prop-42 offset [2]
```

The corpus is still **n = 2** for 482 (one capture; the census excludes
nothing). The WIKI cap — never more than 100 — cannot bind at 480 and is
carried as a rule, not a measurement. Rounding below a multiple of 5 is
UNVERIFIED (480 × 0.2 is exact); `deep_wound_reduction` rounds and says so.

### 41.2 The message in between is the STATUS WORD, and it is on every condition — OBSERVED

The `+2 msgs` offset is the finding. Retail's apply batch is not two messages
but three: `0x0042`, then **`0x00F1` [agent, word]**, then the maximum. `0x00F1`
is `GAME_SMSG_AGENT_UPDATE_STATUS` — the `m_status` word `ChCliInt.h:254`
tests for `CHAR_STATUS_DEAD` (schema/overrides.json 241) — and this server
had only ever sent it for death (0x10) and revive (0). Censused over every
`0x0042` in the live corpus (`deepwoundjoin.status_census`), reading the bits
NEWLY SET in the word that follows each apply against the agent's previous
word:

| skill | type | bits newly set | n | cleared at the remove |
|---|---|---|---|---|
| 478 Bleeding | condition | 0x03 | 1 | (remove not in capture) |
| 479 Blind, 485 Dazed, 486 Weakness, 2077 Cracked Armor | condition | 0x02 | 1, 1, 1, 2 | 0x02 |
| 480 Burning | condition | 0x02 × 5, **none × 2** | 7 | 0x02 × 5 |
| 481 Crippled | condition | 0x0A | 2 | 0x0A |
| 482 Deep Wound | condition | 0x22, then 0x20 alone (0x02 already up: 2077 was live) | 2 | 0x22 |
| 483 Disease, 484 Poison | condition | 0x42 | 1 each | 0x42 |
| 160, 814, 984 | enchantment | 0x80 | 57, 2, 2 | 0x80 (52, 2, 2) |
| 179, 998 | hex | 0x800 | 1, 3 | 0x800 |
| 364, 348 | shout | **no 0x00F1 at all** | 42, 4 | — |
| 999 (Isle) | ? | 0x400 / 0xC00 | 2 | same |

Three rules fall out and all three are in `effects.status_word`: the word is
the **OR of everything live** (482's second apply added only 0x20 because
0x02 was already set; the two Burning applies with no status message landed
while another condition was up, so the word had not changed); it is sent
**only on change**; and it has a bit per bar coloration — which is GWW's own
health-bar table (WIKI, "Health", rev. 2026-05-12: hexed, poison/disease,
bleeding, deep wound) plus crippled. 0x20 is therefore the grey 20 % of the
bar the Deep Wound page describes, and 0x800 is the hexed bar darkening this
server never produced. Bit 0x400 (skill 999) is recorded and not mapped.

### 41.3 What shipped — `authsrv.py`, `effects.py`, both flagged

- **`push_status`** recomputes the word from the live episodes plus death and
  sends `0x00F1` when it changes, right behind the `0x0042`/`0x0044`. The
  death and revive batches are untouched (measured to the message); the
  strip-at-death records the dead word so the book agrees with what the kill
  path sent. `--no-status-word` is the pre-today wire.
- **`deep_wound_open` / `deep_wound_close`**: on a 482 apply the maximum
  falls by `min(100, round(20 %))` and is sent as `0x009F 42` third in the
  batch; current health falls by the same amount in the server's book —
  **SIGNED and UNCLAMPED**, because the client's is (`--probe health_shrink`,
  studies/unitsetup §8 Q5: 25 + (50−100) = −25 in the store, 1 on the HUD, 25
  again on restore). `player_max_health` carries the reduction so every wire
  fraction divides by the number the client now holds; `player_full_max_health`
  is what the enemy's base hit scales from, so a wounded player is not hit
  softer. The close restores both, in retail's order; a death strip restores
  the book and sends **nothing** (the revive batch carries the maximum —
  a `0x009F 42` onto a corpse is the `Health non-zero on resurrect` class).
  `--no-deep-wound` leaves 482 an icon.
- **WIKI rules (GWW, "Deep Wound", rev. 2026-03-02), each a labelled line:**
  healing −20 % in `heal_agent` (`healing=False` exempts a health GAIN —
  Reversal of Fortune's description says the ally "gains that amount of
  Health", its concise text says "healing"; the long form's verb is used,
  UNVERIFIED); "can never kill you by itself" — no kill check on the apply,
  the next damage kills, and a heal that does not clear zero kills
  (`kill_agent` is factored out of `hit_enemy` to give the agent side the same
  door).
- **Content:** `skill_effect.337` (Dismember, Axe Attack, 120 adrenaline,
  `Deep Wound duration` 5..20 in the client's bonus slot) so
  `--enemy-skills 337` lands one from the standing Hatcher's own axe.
- **Tests:** `test_mechanics` §10–19, floor 39 → 99, both known-bad arms
  pinned and the fraction proven discriminating (0.25 reddens 12 checks).

### 41.4 What is registered, not settled

- The two Burning applies with no status message are explained by
  "unchanged word" on the census's own data; the two-condition close order
  (which bits clear when one of two conditions ends) is modelled as the OR
  and witnessed only at 482's second close (2077 gone 0.3 s earlier → 0).
- RoF as health gain vs healing — above.
- An extension of a live Deep Wound (`apply_condition`'s REMOVE-then-APPLY)
  leaves the maximum where it is; retail's shape for that is unwitnessed.
- `degen_tick` still does not kill an AGENT that bleeds out; pre-existing.
- 0x400 / skill 999.

### 41.5 The probe, registered before the run — `--probe deep_wound`

Three arms, read off the HUD orb's printed number (exact) and the bar's right
20 %: **A** the episode alone → icon, no grey, 100/100 (grey here means the
client types Deep Wound from the id and the status bit is redundant); **B**
the full batch on a full pool → grey at the status word, 80/80 at the
maximum, 100/100 at the close; **C** the full batch on 25/100 → **5**/80
(signed delta), 25/100 at the close. 20 or 25 in arm C refutes the delta for
this message pair.

Reproduce: `python toolkit/authsrv/deepwoundjoin.py` (the join and the bit
census); the E5→E3 census castmech §9 cites is the same decode with
`0x00E5`/`0x00E3` paired per (agent, skill).

### 41.6 The probe RAN, and arm C landed on 5 — OBSERVED (`20260909T144731`, agent-driven, loopback)

`session.py --keep-open --hold 75 --shots 1 --game-args "--probe deep_wound
--explorable"`, per-second screenshots. This is a fixed-position HUD readout,
not a world-anchored click, so it was agent-drivable (feedback: owner drives
world-anchored aiming, not fixed UI).

- **Arm C, the discriminator** (frames at the maximum=80 onto a damaged pool
  of 25): the health orb reads **5**, and the right ~20 % of the bar is
  **greyed** — the signed-delta prediction exactly, and the grey the wiki's
  own text describes. A fraction reading predicted 20 and "ignored" predicted
  25; both are refuted at a glance.
- **The close** (maximum back to 100): the orb reads **25** and the grey is
  gone — 25/100, the pool where the damage left it, the 20 returned with the
  maximum.
- Arm A / arm B ran first and are consistent (100/100 throughout arm A and at
  arm B's close; 80/80 at arm B's maximum). The grey-vs-episode question of
  arm A (does the icon alone grey the bar, or only the 0x20 status bit) is not
  separable at the frame cadence here and is left as the one open sub-clause;
  the shipped server sends the bit either way, so nothing downstream turns on
  it. Verdict PASS, `undecodable 0`.

## 42. SKILLS-HN — the heal number was in the frames all along (it is BLUE), and retail sends the overheal (2026-09-09)

**What this closes.** §19's last paragraph — *"And it draws no number for
it ... 0–8 saturated green pixels ... OPEN"* — carried for three weeks as
"the client applies property 55 and draws nothing". Both halves of that were
an instrument error: the scan looked for the wrong colour, and nobody looked
at the frame. The desk half of the closing brief (census every retail 55 for
a sibling property, the way the damage and Deep Wound batches were found)
ran first and found no candidate; the frames were then re-read and the
number was there, three times out of three. **No new run was needed.** On
the way, the census refuted a second claim the same paragraph's neighbour
carried into a test — that an overheal is silent.

### 42.1 The census, with its predictions registered first — OBSERVED

`toolkit/authsrv/healjoin.py` (P1–P4 in its docstring, pinned by
`test_mechanics` §20 as floors). Every property-55 event on `0x00A3` across
the 61 live game connections that frame whole, each with its batch — a
contiguous run with no gap above the 50 ms shoulder — and, for the control,
every 16/17 damage event the same way:

```
property-55 events 800: positive 796, self-directed 748; damage 16/17 events 1762
sibling on the same agent   heal batches   damage batches
  9F:58  skill_finished          746            17
  9F:21  caster visual           486            34
  A3:55  a second gain           451            17
  A0:20  recipient visual        104           224
  A3:16  damage                   46           238
  A2:44  regen                    19           149
  (nothing else above 15)
within the set this server already sends: 720 of 800; bare [58, 55]: 185
0x001E in the batch: heals 800/800, damage 1762/1762
```

Shapes, wire order, same agent: `58 21 21 55 55 ·1E` ×266, `58 55 ·1E`
×173, then the same two with a tick on either side. **Nothing rides beside a
heal that does not also ride beside damage** — 58 and 21 are the cast end
(castmech §3c, ANIMREF-R8), 20 is the recipient visual and is *commoner* on
damage, and `0x001E` is the world tick closing every batch of either kind, a
terminator this server has sent since the movement arc. 185 heals ride with
nothing but the 58. So whatever the client draws for a heal, it draws from
the 55 alone, and there is no candidate for a probe to test. (Count
reconciliation: §19 saw 506 events, ANIMREF §18 saw 861; the corpus grew,
and §18 grouped by (batch, agent) over both float channels. 800 is this
decode over `vault/captures/live/` as of today, and the test pins ≥ 800.)

### 42.2 The frames re-read: a pale blue "+46", 3 of 3 — OBSERVED (`20260820T190917`)

The run §19 cites is a walk run with per-second frames; the server capture
(`gamesrv/authsrv-20260820T190936-c1.jsonl`) puts the three heals at
t = 12.86, 21.56, 30.25 s and the four Holy Strike hits at 6.31, 15.51,
24.05, 33.25 s, and the frames' mtimes put `w007`, `w014` and `w021` at
+1.25, +1.17 and +0.98 s after each heal. Cropped to the screen centre and
looked at: **each carries a "+46" floating above the player**, rising with
the cast's pink Healing Signet burst below it; `w006` at +0.04 s has the
burst and no number yet; `w009` at +1.04 s after a hit carries the **"−46"**
damage number in the same place — the positive control §19 never ran.

The glyphs are sky blue on a white core — `(151,233,250)`, `(122,214,238)`,
`(57,183,217)` — and a box over them counts **178** pixels with
`b ≥ 150 and b > r + 20` against **6** in the same box one frame later.
§19's scan asked for *saturated green* (`g ≥ 160, g − max(r,b) ≥ 60`); a
first re-scan here asked for *saturated blue* (`b − max(r,g) ≥ 60`) and was
flat at 417 across all 45 frames, which is the HUD's own blue. Neither
threshold can see a pale glyph, and the 0–8 green pixels §19 reported were
the key-press frames' own noise (114 at each `key1` frame, 57 elsewhere).
**A colour-threshold null on a floating number is not a null until the frame
has been looked at**, and the number in it was legible at a glance.

WIKI agrees on the colour, and says one thing more — GWW, "Heal", rev.
2023-08-05: *"The healing player and healed player see blue numbers showing
the amount healed. Blue numbers are shown even when no health are actually
gained (usually because the character is at full health)."* The hosted
`hud-heal-54-to-100.png` in that run directory is a 1080×2424 phone capture
and carries no HUD pixels the scan can read; the CONFIRMED 54 → 100 readout
§19 built on stands on its own.

### 42.3 The overheal is on the wire — OBSERVED, and a RECONSTRUCTION retracted

`heal_agent`'s docstring and `test_skilldamage` §8 both said *"overheal is
silent in retail too — no green number appears when nothing was restored"*,
and the server sent nothing on a full pool and shrank a partial heal's wire
fraction to what landed. The wiki sentence above says the opposite, and the
client cannot print an amount it never received, so `healjoin` P4 asked the
corpus: a positive 55 on an agent that has taken **no health loss at all** on
its connection before it — no 16/17, no negative 44, no negative 55, no 34
setter — lands on a pool that is full by construction (agents spawn full,
agentprops 1). **46 such events**, values 0.0414 / 0.0829 / 0.18 / 0.3243,
never zero; and of the 750 heals on pools the ledger has seen damaged, **593
exceed the loss it still owes** — a floor, since the ledger credits no regen.
Retail sends the skill's own amount regardless of the pool; the client clamps
and draws it.

**Shipped (SKILLS-HN, default ON, revert `--no-overheal-number`).**
`heal_agent` now sends `min(amount, pool) / pool` — the amount, capped at the
whole pool because `_fraction` refuses above 1.0 (CharPool.cpp:84) and
retail's largest witness is 0.652, so a heal larger than the maximum has no
witness either way — and adds to the book only what fits. The partial case
(a 50 onto 70/100 sends 0.5, not 0.3) is RECONSTRUCTION: the corpus sees
that full pools get the amount, not what a half-full one gets. Pins:
`test_skilldamage` §8 (full pool sends 0.5 and moves nothing; partial sends
the amount; a 250 onto 100 caps at 1.0; both known-bad arms; floor 40 → 44),
`test_agentlife` (`dmg_floats` reads DAMAGE only, and the enemy's Restore
Condition on its own full pool now sends exactly one positive 55; floor
379 → 380), `test_mechanics` §20 (the census, floors; 99 → 106).

### 42.4 The probe, registered and NOT run — `--probe heal_number`

Arm A: damage −0.46 then heal +0.46 → the "+46" of §42.2, the control.
Arm B: +0.46 and then +0.10 onto the FULL pool → WIKI predicts "+46" and
"+10" with the orb unmoved; the retired rule predicted nothing to send. The
refutation that matters is an assert in arm B — retail's client takes 46 of
these in the corpus, but a `fraction <= 1.0f` dialog here would mean the
clamp is ours and the cap in §42.3 must tighten. It is a fixed-position
readout (the number floats from the player's own head at screen centre, ~1.5
s), so it is agent-drivable; it was not launched in this session because the
original question closed on existing frames and a launch is a shared-machine
event. `session.py --keep-open --hold 40 --shots 1 --game-args "--probe
heal_number --explorable"`, and read the frames, do not threshold them.

### 42.5 What is settled, and what is not

- SETTLED: the client annotates a heal from property 55 alone, in pale blue,
  3 of 3, with the damage number as the same-run control. §19's "draws no
  number" is RETRACTED as an instrument error, and `PLAN.md` §8's "worth one
  probe" item is closed without one.
- SETTLED (wire): retail sends the 55 on a full pool, 46 of 46 non-zero.
- OPEN: what OUR client draws on a full pool, and whether it asserts —
  §42.4. Also the four negative 55s (sacrifice, UNVERIFIED since §19), and
  the periodic 0.0414/0.0829 gains on agents 10/16 in `20260817T231139`
  (every ~2 s, never attributed to a cast — a regen-like effect riding the
  heal channel; not this section's question).

### 42.6 Blind replication by a parallel session, and two things it adds (2026-09-09, later)

A second session was handed the same brief the same afternoon and worked it
with neither side seeing the other (§42.1–42.5 landed at 15:28 while this one
was mid-census; the two were compared only afterwards). It is a replication
in the sense `feedback-blind-replication` asks for — independent decode,
independent batch definition, rival answer withheld — and it agrees.

**The census, replicated with a third column.** A ±50 ms window from each
anchor (§42.1 uses a contiguous run under the 50 ms shoulder) over the same
corpus: **796 positive 55s, 746 self-directed, 0 lone; int 58 value 0 on the
cause in 796 of 796; int 21 on the target in 484**; same-segment shape
`58 21 21 55 55` ×340 and `58 55` ×209 (the window is wider than §42.1's run,
so its shape counts are higher; the members are the same). The addition is a
**base-rate control** — the same labels beside every 97th message of the
corpus (1,542 anchors) — so a sibling can be read against "is it just always
there": 58-on-target reads 93.7 % beside heals, 0.8 % beside damage, **0.9 %
at base**; 21-on-target 60.8 % / 1.7 % / **1.3 %**; and **no other
target-addressed value clears 12 % of heals** (the next is `0x00F1` at 11.8 %,
which reads 6.8 % at base and 14.7 % beside damage — a status word, not a
number). Same conclusion as §42.1 from a second instrument: the batch carries
no number for the healed agent but 55 itself.

**The client half, which §42 did not need and records anyway.**
`avevents.py --id 55` (build 38797): property 55 queues AgentView **effect
event kind 0x0B** (`0x008131D7 → 0x007E0130 → 0x007F7580`), the kind that
property **52, energy gain**, queues; damage 16 and 17 queue **kind 0x02**
(`0x007DFB60 → 0x007F6E70`). So §19's implicit model — the number the client
draws for 16 should appear for 55 the same way — was pointed at the wrong
renderer from the start: a heal never enters the damage annotator. The
kind-0x0B builder reads a float pair from a per-selector table at
`[this+0x108]` (55 → row 0, 56 → row 1), keeps the larger, and allocates; its
consumer was not decoded, because §42.2's frames made that unnecessary.

**The scan, as an instrument with controls — `toolkit/harness/callouts.py`,
pinned by `test_callouts.py`.** §42.2 read the frames by eye and counted one
box by hand; this makes the count repeatable and gives it the two controls
§19 lacked. The glyph colour MEASURED off `w007.png` is RGB ≈ (96–144,
208–224, 224–240); the class `B > 190, G > 180, R < 160, B ≥ G, B − R > 70`
counts, in a fixed band where the number floated (`900–1000 × 445–485`):

| heal sent (UTC, server `sent` rows) | control frame | number frame | in-band pixels |
|---|---|---|---|
| 23:09:48.863 | `w006` +0.04 s: **0** | `w007` +1.25 s | **101** |
| 23:09:57.561 | `w013` −0.04 s: **0** | `w014` +1.17 s | **101** |
| 23:10:06.252 | `w020` −0.24 s: **0** | `w022` +2.20 s | **24** |

`w021` (+0.98 s) reads 0 in that band because its `+46` sits ~40 px lower —
the band is a screen position, and the frame shows the number at a glance —
which is why the tool prints the whole-frame bounding box for re-aiming
rather than pretending the band is the finding. Two wrong-colour detectors
are kept as checks that can go red: the 2026-08-20 green class reads 0 on a
block of the glyph colour and 100 on a green block, and a saturated-blue
class (`B > 170, G < 150`) reads a **constant 78 pixels in all 45 frames**,
every one of them the upper-left effect icon — the same shape as §42.2's
flat 417, from a different threshold. The synthetic positive control never
skips, so the test cannot go vacuously green on a bare machine.

Nothing here changes §42.3–42.5; the overheal finding is the peer's alone.

### 42.7 The probe RAN: the full-pool number draws, and nothing asserts — OBSERVED (`20260909T163556`, agent-driven, loopback)

`session.py --keep-open --hold 40 --shots 1 --game-args "--probe heal_number
--explorable"`, owner's go-ahead, frames every 1.28 s, four sends at
t = 6.81 / 9.82 / 13.82 / 17.84 s of the game capture. Read off the frames
(cropped and looked at, per §42.2), against §42.4's predictions:

| step | send | orb (HUD, exact) | what floated over the player |
|---|---|---|---|
| control | `[16, a, a, −0.46]` | **54** | a yellow **"−46"** (`hold004`, +1.5 s) |
| arm A | `[55, a, a, +0.46]` onto 54 | **100** | a pale blue **"+46"**, fading (`hold006`) |
| arm B | `[55, a, a, +0.46]` onto 100 | **100** | not caught — both neighbouring frames sit outside its ~1.5 s life |
| arm B′ | `[55, a, a, +0.10]` onto 100 | **100** | a pale blue **"+10"** (`hold013`, +0.7 s) |

- **The full-pool number draws, and it is the amount SENT.** "+10" over a
  pool that read 100 before and after — the wiki's sentence reproduced on
  our client from our own wire. So `heal_agent`'s new rule (§42.3) is what
  the client expects, and the number a player sees on an overheal is the
  skill's amount, not the zero that landed.
- **No assert.** The client took two positive 55s onto a full pool, kept
  running through the 40 s hold and the teardown (`RUN VERDICT: PASS`,
  `undecodable 0`; the only "assert" strings in the log are the probe's own
  prose). The `fraction <= 1.0f` cap in §42.3 therefore did not bind here
  and stays a cap with no witness on either side above 0.652.
- **Arm B's miss is cadence, not a null.** The number lives ~1.5 s and the
  frames are 1.28 s apart with ±1 s alignment on the capture's wall stamp,
  so each event is caught about half the time; arm B′ is the same condition
  (a 55 onto 100) and was caught. The peer's `callouts.py` band from the
  2026-08-20 run read 0 in every frame of this run because the number
  floated ~60 px lower here (bbox rows 498–636 against the band's 445–485);
  its `--bbox` mode found all three heal-coloured events and none after the
  damage send. Whole-frame bbox first, then crop; a band is per-run.

**SKILLS-HN is closed on every clause.** What remains open in §42.5 is the
four negative 55s and the periodic 0.04/0.08 gains, neither of which is the
heal number's question.

---

## 43. SKILLS-FA — the incoming fire spell's armour: ONE rating, elemental, no location roll — and the probe §39.6 registered could never have answered it

> **"ONE rating, no location roll" is REFUTED — 2026-09-17, §50 (SKILLS-LR).** A body with its head, hands and feet bare took the same Lightning Orb for 101 and for 286, 2^(60/40) apart; armoured, 101 four times of four. §43.4's caveat — eight arena characters in equal pieces cannot tell — was the whole story. The elemental rating, the armour-ignoring labels and the multiplier below all STAND; only the "no roll" half falls, and `--no-spell-location-roll` keeps it as the revert arm.

**Desk and corpus, 2026-09-09, pinned build 38797. No client run, and §43.1 says
why one would have measured nothing.** Closes §39.5's "INCOMING is fixable" and
§39.6's "the armour VALUE is unsettled". Shipped: `ARMOUR_RESPECTING_MEANS`,
`SPELL_ARMOUR`, `player_spell_armour`, `spell_armour_for` and the term in
`land_skill` (`toolkit/authsrv/authsrv.py`); `--no-spell-armour` reverts;
`toolkit/authsrv/spellhitjoin.py` is the instrument; `test_skilldamage` §11–§12,
floor 44 → 57.

### 43.1 The registered probe measures our own code, not retail

§39.6 proposed "one caged loopback run with `--enemy-skills 194` and a deliberately
lopsided armour set … if the damage is single-valued the spell resolves against one
rating; if it comes in five buckets it rolls a location". On loopback the number
in the property-16 packet is computed by `land_skill` — by us. Whatever rule we
wrote in would be the rule the run "found". That is the offline-agreement trap
`CLAUDE.md` names ("agreement between two of our own components proves
nothing"), and it is why this section is a corpus read and not a run. The client
draws whatever fraction arrives; it holds no opinion about armour.

### 43.2 The wiki, re-read: every hit-location sentence says "attack"

> **WIKI (GWW, "Armor rating", as fetched 2026-09-09):** "Exact armor depends on
> the damage type, but also in the player's and heroes' case, on the piece of the
> armor that is hit." … "Each location has different odds to be hit. The chest has
> the highest chances (three out of every eight **attacks**) …" … "The damage
> multiplier can also be found for *non attack* skills if the attacker is the same
> level as you with the equation" — and the equation names no location.

> **WIKI (GWW, "Damage calculation" §Hit locations, as fetched 2026-09-09):**
> "Any given **attack** on a player will hit one of these five locations, and only
> the armor rating of this location is considered." The §Skills formula that
> follows is `[Skill Damage] × 2^((3 × [Character Level] − 60)/40)` against a
> single armor level.

Ambiguous as §39.6 said, but leaning: the roll is described for attacks three
times and never once for a spell. The wiki is a player-observation source
(WIKI, strong for what a player sees); the instrument below is what a player
could not see — many casts from one caster onto one target, each packet read.

### 43.3 The instrument: `spellhitjoin.py`, predictions first — OBSERVED

The join is the cast announcement the wire already carries: `0x00A0 [60
SKILL_ACTIVATED, caster, target, skill]` (`agents.GV_SKILL_ACTIVATED`), then the
damage in the batch the caster's property-58 closes, one activation later. The
`age` column reproduces the wiki's activation times without being told them —
Mind Burn 0.991–1.017 s (GWW: 1), Fireball 1.488–1.55 s (GWW: 1½) — which is what
says the join is right. A Fire Storm tick shares batches with casts from the same
caster; a value that also occurs as a no-58 hit from the same cause onto the same
target within 5 s is set aside as a tick (12 of 103).

| | predicted | measured |
|---|---|---|
| P1 cast damage is announced by a property-60 inside 4 s | ≥ 95 % | **103 of 103** |
| P2 one caster + one skill + one target with ≥ 3 hits is ONE value | ≥ 10 pairs, ≥ 60 hits, 0 multi-valued | **11 pairs, 68 hits, 0 multi-valued** (all Mind Burn, skill 185) |
| — onto the connection's OWN player | one value | **4 of 4 at 0.06042 = 29 on a 480 pool** (agent 11, RA, `20260817T231139`) |
| P3 CONTROL: a swing pair with ≥ 10 hits shows ≥ 3 values | every pair | **18 of 18** (min 3 distinct) — the instrument sees a weapon's range where there is one |
| P4 Mind Burn's conditional second packet is a twin 16 in one batch | ≥ 10 | **39** |

P4 is a small wiki confirmation nobody asked for: GWW "Mind Burn" — "if you have
more Energy than target foe, that foe and all adjacent foes take an additional
15…60 fire damage" — and the wire carries it as a second identical packet, not a
doubled one. The eight bodies are the eight Random Arenas characters of the
2026-08-17 session (agents 7–14, two Elementalists casting); every one of the
eleven pairs reads one fraction for the whole fight, the player's included.

**What P2 says.** Under a 1-in-8 head roll on a set whose head differs from its
chest by ANY amount, the chance of 68 hits landing in one bucket across eleven
pairs is (7/8)^68 ≈ 1 × 10⁻⁴. So either spells resolve against one rating, or
every one of eight arena characters wore five pieces of equal elemental armour.

### 43.4 What the corpus cannot separate, said plainly

A PvP character's five pieces usually ARE equal — max-rating set, one insignia
throughout — and the arena characters' equipment is not on the wire (armour has
no property id, `studies/presearing/R4C2-FEASIBILITY.md`). P2 refutes a location
roll only *given* some per-piece difference, and that premise is unmeasured for
those eight bodies. What tips it is the shape of the wiki (three "attack"
sentences, a location-free spell formula) plus §43.5's simultaneity argument.
**Label: the single rating is CORROBORATED (wiki wording + 68/68 on the wire),
not OBSERVED against a known-lopsided set.** The one witness that would make it
OBSERVED is a live one: a character whose head piece is missing or weaker taking
a spell — Pre-Searing's starter set has no headgear, so the owner's first live
character was exactly that body, and nothing cast at it in `20260807T143055`.
An R0b runsheet line, human-driven; not scheduled here.

### 43.5 The one two-valued pair, and it argues the same way

`--pairs` lists one pair with two values at two hits — Fireball (186) from caster
10 onto agent 12: 0.17658 and 0.12973 (98 and 72 on 555). Read in context it is a
**mixed batch**, not a second bucket: caster 10 announced Incendiary Bonds (179) at
−3.985 s and Fireball at −1.753 s; Incendiary's 1 s cast ends at −2.985 and its
3 s hex ends at **+0.000**, which is exactly when the 72 lands; Fireball's 58 is at
−0.252 and its projectile's 98 lands 0.4 s later. Same shape at 744.453/744.568
and 752.803/752.846. The tool names these (`two_hit_two_valued`) and the test pins
the count at ≤ 1 by name, so a second such pair reddens rather than hides.

And the simultaneity is evidence on its own: at 744.45 the 98/61/53 packets land
on agents 12/11/13 in one instant and the 72/45/39 packets 115 ms later, **the same
0.735 ratio on three different bodies at once**. A per-hit location roll cannot
give three characters the same ratio in the same tick; a second skill's payoff
can. (Which rating puts Incendiary Bonds' 15…67 at 72 on that body is not
resolved — the caster's rank and the target's rating are both off the wire.)

### 43.6 Shipped, and the number it changes on our wire

- `ARMOUR_RESPECTING_MEANS = {"Fire damage"}` beside `SCALE_MEANS_DAMAGE` —
  §39.2's rule: the damage TYPE and its source decide, never "is it a skill".
  `Holy damage` (a skill's) and `+ Damage` stay armour-ignoring; §39.5's three
  traps hold.
- `player_spell_armour()` — the ELEMENTAL rating (`physical=False`): the pieces'
  `+20 vs. physical` does not reach a fire spell. Every piece this server equips
  reads 25 elemental / 45 physical, so today a single rating and a location roll
  are byte-identical on the wire; what is shipped is the claim. If the five ever
  disagree it takes the chest's and says so on stdout — UNVERIFIED which rating a
  lopsided set uses, and now impossible to ship silently.
- `land_skill`: `base *= armour_multiplier(spell_ar)` before `taker_damage`,
  GWW's order (the exponent is the damage calculation; Frenzy and a conversion
  are "taken into account at the end").
- **Flare at rank 12 on our AR-25 player is 56 × 2^((60−25)/40) = 102.7** — more
  than the stated amount, the wiki's "a target with net armor below 60 takes
  more" — and on a 100 pool that is an overkill the wire carries as 1.0. It used
  to land as exactly 56. `--no-spell-armour` restores that; `--no-armour-term`
  drops it with the swing's term.
- **Not modelled, named:** the caster's LEVEL term (`2^((3L−60)/40)` on skill
  damage). `ENEMY_SKILL_RANK = 12` stands in for a level-20 caster, and the
  Hatcher's level is a placeholder (`content/npcs.toml`); when a real level lands
  this is the next line.
- `test_skilldamage` §11 (7 checks: the ratings, the label gate, the 36.68, both
  reverts, the Holy control) and §12 (6: P1–P4, the player's pairs, the named
  two-hit exception). Floor 44 → 57. §12 skips by name without the vault.

### 43.7 Status

§39.5 INCOMING: **CLOSED, shipped.** §39.6's probe: **struck** — it could not
answer. The shape: **CORROBORATED** single elemental rating (§43.4's caveat is
the residual). OUTGOING (`hit_enemy(exact=…)`) is unchanged and still blocked on a
creature armour value that no channel carries.

### 43.8 SKILLS-OB — whose connection it is: the instrument's player rule was wrong, and four readers inherited it (2026-09-23)

**Desk work, no client launched.** `spellhitjoin.player_of` named the connection's own
agent as the agent of the FIRST `0x00E3` (SKILL_ACTIVATED), and `interruptjoin`,
`missjoin` and `rechargeprobe` all took their player from it. On the one tape with a hero,
`20260914T005758` conn `56011`, that first ack is the **hero's**: agent 30, a kind-9
create, holds 48 of the 54 acks (346 × 17, 322 × 11, 382 × 7, 348 × 7, 385 × 5, 2 × 1).
The player is agent **29**: the only kind-5 create, a property-41 agent (the hero gets
property 41 too — JARIN's "character block addressed to a second agent"), the owner of the
other 6 acks (394 × 2, 392, 433, 446, 455), and the agent whose `0x00E3` / `0x00E2` is the
next answer after **all 18** of the connection's c2s presses (`0x0027` / `0x0046`; 14
inside 0.3 s, 4 at 1.2–2.0 s). The corrected rule was already in the tree:
`adrenjoin.whose_agent` (property 41, self-scoped, §26.13's correction of the first-`0x0059`
rule, with the JARIN kind-5 tie-break). Branch `desk-d5c`'s `shoutjoin.observer_of`
(§56.8 there, not yet merged) cross-checks it against the press answers; this section is
the same rule applied to the older readers.

**Measured first, over all 96 live connections** (every one frames whole):

| the first-`0x00E3` rule against property 41 | connections |
|---|---|
| names the same agent | 25 |
| names a **different** agent | **1** — `20260914T005758` / `56011`: 30 (the hero) for 29 |
| names **nobody** (no `0x00E3`: the player never cast) while property 41 names the observer | **69** |
| neither answers | 1 — `20260807T133758` / `54560`, an 88-message stub with no property 41, no press, no announcement |

So the defect was two defects: a wrong agent on the hero tape, and a silent `None` on 69
connections that every consumer read as "no stop, swing or pair here is the player's".
The press vote agrees wherever it speaks: 26 connections carry presses (321), 159 are
answered inside 0.3 s on 19 connections, and all 19 votes are unanimous and equal to
property 41's agent. The rest are answered later (0.33–5.3 s — a press that walks into
range first), always by the same agent. **No connection has the two rules disagreeing.**

**The rule now** (`toolkit/authsrv/spellhitjoin.py`): `observer_of(seq, c2s)` returns
`(player, press_agent, why)` — property 41 cross-checked against the press vote (the next
`0x00E3` / `0x00E2` inside `PRESS_ANSWER_S` = 0.3 s after each c2s press, `c2s_of` reading
the client's own requests on the capture clock); the two disagreeing is **refused** (no
player named, the reason naming both, counted by every consumer), never settled by picking
one; neither answering names nobody and says so. `player_of` delegates. All four readers
pass their c2s; `rechargeprobe` excludes a refused connection (its "other agents" are
undefined), the others keep its rows with no player.

**What moved, re-derived on the corrected rule** (old → corrected; every verdict — P1–P4
here, `interruptjoin` P1–P5, `missjoin` P1/P2/P5, `rechargeprobe` P1–P3 and every
per-skill minimum — is player-independent and does not move):

| reader | the number | first-`0x00E3` rule | corrected | published where |
|---|---|---|---|---|
| `spellhitjoin` | §43.3's pair onto the connection's own player | 4 of 4 at 0.06042 (agent 11, RA) | **unchanged** — both rules name 11 there | §43.3 |
| `spellhitjoin` | pairs onto the connection's own player | `10 185 11`, `117 230 25`, **`54 222 30`** — the HERO's Frenzy pair (26 and 51 at 122, slice F47.2) | `10 185 11`, `117 230 25`, **`54 222 29`** (the Ranger's: 23 and 24 at 140, and hits at two later maxima) and **`48 222 29`** (LAKESIDE's penalty split, on a connection with no `0x00E3`) | `test_skilldamage` §12 only; the check passed both ways, so it could not see the swap |
| `interruptjoin` | stops on the observer / on another, per property | `[3]` 60 / 177, `[49]` 3 / 9, `[59]` 11 / 23 — own 74, 209 of 283 on others | `[3]` **72 / 165**, `[49]` 3 / 9, `[59]` **10 / 24** — own **85**, **198** of 283 on others | PLAN-LOG, the DESKWORK-D5 fix-pass entry, item (5) |
| `interruptjoin` | the observer's own cancels within 0.5 s of a c2s `0x0028` | 2 of 74 | **3 of 85** | same |
| `missjoin` | §44.2's "the player's own 399 swings all carried damage" (the §44 corpus, to 2026-09-10) | 399 | **865**, all with damage — 466 more on four connections that swung and never cast (`20260818T132739` 55252 / 65119 / 64640, `20260821T163511` 61106); P4 still cannot be scored on that corpus | §44.2 |
| `missjoin` | P4 on today's corpus (own swings / own no-damage / with a gain) | 663 / 30 / **2** | 1187 / 29 / **1** — the withdrawn one is the JARIN hero's missed swing, which the old rule called the player's | unpublished; §48.6's 27 of 27 is on `20260916T213125` and unchanged |
| `rechargeprobe` | other agents' announcements | 346 | **347** — the hero's one (skill 2) is an other agent's now; the player 29 announces nothing on that connection, so none of the player's casts was ever pooled; no pair, no minimum moves | PLAN-LOG, the DESKWORK-D5 step-4 entry |
| castmech §4 / animref D5 | "both `[35]` at the observer" | 25 on both witness connections | **unchanged** | castmech §4, animref D5 |

Where the stops moved: on `56011` the hero's `[3]` × 2 and `[59]` × 1 were the "observer's"
and the player's five `[3]` another agent's; `20260821T163511` 61106 (+1 `[3]`) and
`20260919T103604` 56576 (+8 `[3]`) had no player at all.

**Labels.** The observer rule: **OBSERVED** — property 41 is self-scoped on the wire, the
press answer is the client's own request met by its own ack, and the two agree 19 of 19
where both speak. The re-derived counts: **OBSERVED**, the same instruments on the
corrected operand. **Locks:** `test_skilldamage` §11b (bare machine: the JARIN shape with
the known-bad arm on the same fixture, the refusal, the fallbacks, the window) and §12 (the
census names 29 on `56011`; the pair onto the player is `54 222 29`, never `54 222 30`);
`test_interrupt` §2 (the dated split above, and on `56011` a stop is the observer's exactly
when it names 29). All seven are red with `observer_of` swapped back to the old rule.

**Method, for the next one.** A rule that answers `None` is a rule that answers — every
consumer here read it as "not the player" and scored on. The hero tape made the wrong
answer visible; the 69 silent ones were only found by counting the rule against a second
one on every connection, which is the check to run before trusting any "whose agent is
this" helper.

---

## 44. SKILLS-BL — Blind: the miss is the client's own attack-fail word, the rate is the wiki's, and the corpus holds no blinded swing to measure it on (2026-09-10)

**Desk, corpus and a static read of the pinned build 38797. No client run.**
Asked as SKILLS-DW's item (2) — "Blind, the cheapest remaining condition
mechanic (a labelled miss-roll on `land_swing`'s existing roll)". It was cheap;
what it was not was *known*: this server had never sent a swing that missed,
so before a roll could ship the question was **what a miss looks like on the
wire**, and the answer came from the client's own drain rather than from the
corpus, which turned out to carry exactly one attack that did not land.
Shipped: `BLIND`, `BLIND_MISS_CHANCE`, `blinded`, `blind_miss`, `attack_fails`
and the roll at both swing sites (`land_swing`, `hit_enemy`) in
`toolkit/authsrv/authsrv.py`; `agents.GV_ATTACK_FAIL` + `ATTACK_FAIL_REASONS`;
`--no-blind` reverts; `toolkit/authsrv/missjoin.py` is the instrument;
`test_mechanics` §21–§23, floor 106 → 129.

### 44.1 The rule, and the two questions it did not answer

WIKI (GWW, "Blind", rev. 2020-10-23): *"Your melee and missile attacks have a
90% chance to miss. Your projectile spells also have a greater chance to stray
from their intended target."* WIKI (GWW, "Miss", rev. 2019-12-30): *"After each
miss, the game displays a yellow 'miss' message beside the target"*, and
blocking, failing, straying, obstruction and dodging *"are not the same as
missing"*. So the rate is a published number, but a yellow word on the screen
needs a word on the wire, and nothing in `agents.py` named one. Two questions,
both answerable without inventing: (a) does retail's corpus carry a miss, and
(b) if it does not, what does the client draw the word FROM.

### 44.2 The corpus, predictions first — a miss is NOT in it

`missjoin.py` (docstring P1–P5) joins every retail swing close — `0x009F`
property 1, `GV_MELEE_ATTACK_FINISHED` — to its 50 ms batch, and every close to
whether the swinger sat inside a live 479 episode (`bufflog.episodes`):

| | closes | no damage in the batch |
|---|---|---|
| swinger not blind | 1,042 | **7** (0.67 %) |
| swinger under a live 479 | **0** | — |

**P1 holds** (floor 25 %, measured 0.67 %), and every one of the seven is a
dead or unreachable target rather than a miss: four are two swingers (29 and
58) closing on targets 137 and 194 in the same instants, two carry a
`0x009F 45` or a re-`4` beside them, one is a swinger yielding to a cast. **P2
has NO WITNESS**: not one of the 1,042 closes was swung blind, so the 90 % is
WIKI and stays WIKI until a blinded swing is captured (§44.6). The player's own
399 swings all carried damage (P4 cannot be scored). **(Corrected 2026-09-23,
§43.8: 865, all with damage. The 399 was taken on `spellhitjoin.player_of`'s
first-`0x00E3` rule, which named no player on four connections where the
player swung 466 times and never cast. P4 still cannot be scored here.)**

**P3 — the miss word by histogram — named nothing**, and that was the useful
null. So the swing was censused from the other end: for all **1,332** attack
starts (`0x00A0` property 4), the first message naming the attacker afterwards.
Property 1 closes 936; the damage comes first 133 times; property **8** closes
98 (the swing yielding to a cast — `[8, 3, 62, 60, 8]` in one batch); property
**3** closes 79 (a stop, 58 of them still followed by damage inside 4 s);
property **2** closes ONE (`[2, 30, 0]` + damage, an alternate close the
client's AvApi names `MeleeAttack`, action kind 0x01 — not a miss). **No
unnamed property ever closes a swing**, and the seven zero-valued property-16s
(agent 58's 0.0 hits on 137/144/194/217) are hits for zero, still on the damage
channel. A miss simply is not in this corpus, which is what a Pre-Searing
warrior's six sessions and one arena capture should look like.

### 44.3 The client's own word: property 38, and its reason table — OBSERVED

`avevents.py` lists the property ids that queue an AgentView event. Property
**38** queues **effect kind 0x07**, and the only lineage that names it calls it
`AttackFail` (OpenTyria `GmAgentProperties.h:42`; GWLP-R's enum agrees; GWCA
does not name it) — UPSTREAM for the name, and the name turned out to be right
for the wrong reason: it is not *the* miss, it is every way an attack fails.

Read out of the pinned build, `codescan.py --dis`:

* **The handler** `0x007DFE40` takes `(agent, a, b)`, resolves the AgentView of
  the FIRST agent (`0x00802160`) and queues kind 7 on it (`0x007F7230`) with
  `+0x1C = a` and `+0x20 = b`. So the wire is `0x00A0 [38, TARGET, attacker,
  reason]` — the word is drawn beside the first slot, which is where GWW puts
  the yellow 'miss'.
* **The drain** `0x007F9F70` (`cmp eax, 0x13` / `jmp [eax*4 + 0x007FA514]`, one
  entry per effect kind 0x00–0x13, calling the effect free at `0x007F5230`
  from `0x007FA4FA` — the free that asserts `effect->effectLink.IsLinked()`,
  AvChar.cpp:2433). **Kind 7's case is `0x007FA159`**: it looks the attacker
  up, plays one of eight sounds (`rand & 7` into `0x00A93EF0`), draws a
  formatted float over the target (`0x007EDC50`, coded template `3E45 0104` =
  string 15685 + a parameter — file 15 record 325, which `textrec.py` cannot
  resolve, its file lying outside the 11 × 99 language tables the tool walks;
  the reason is one of the template's parameters), and **when the attacker is
  the local player, switches on the reason** (`cmp eax, 5`, table
  `0x007FA574`) to a string id and posts it in colour `0xFFFFFF00` — yellow:

  | reason | string id | `textrec.py` (owner's archive, file 0) |
  |---|---|---|
  | 0 | 471 | block |
  | 1 | 473 | dodge |
  | 2 | 475 | fail |
  | **3** | **476** | **miss** |
  | 4 | 478 | obstructed |
  | 5 / default | 480 | stray |

  (474 'evade', 477 'miss' and 472/479 'block' sit in the same run of records
  and are not in this table — the float template may use them; not read.)

That is the enum, OBSERVED from the client's code and the owner's own archive,
and it is exactly GWW "Miss"'s list of things that are not a miss plus the
miss. **A Blind miss is reason 3.** `agents.py` carries it as
`GV_ATTACK_FAIL = 38`, `ATTACK_FAIL_REASONS`, `ATTACK_FAIL_MISS = 3`.

### 44.4 The one wire witness, and what it settles

`missjoin.py --fails` (P5): property 38 rides retail's wire **once** in the
whole live corpus — `20260819T132414`, `[38, 217, 27, 2]`: the player (27)
attacking a hostile (217), reason 2 'fail', in the same batch as the player's
own `0x009F 46` (attack_skill_finished, the close of attack skill 780 activated
0.17 s earlier) and **no damage from 27 onto 217** — the next thing 27 lands is
skill 858's hit 1.2 s later. So on retail the close goes out AND the word goes
out, in that order, and the damage does not; the attacker had no 479 on it
(an enchantment, 814), so this is a failed attack skill, not a Blind miss.

What it settles: the slot order (target first — the client's handler said the
same), that the word shares the batch with the attack's own close, and that the
word and the number are exclusive (P5, 1 of 1). What it does NOT settle: the
shape of a *plain swing's* miss. Retail's witness is an attack skill, whose
close is property 46; a plain swing's is property 1. That `[1, 38]` is the
shape is **RECONSTRUCTION by analogy**, said in the test's own words, and the
one check that would replace it is a captured blinded swing (§44.6).

### 44.5 Shipped

* `BLIND = True`, `BLIND_MISS_CHANCE = 0.90` (WIKI), beside the Deep Wound
  constants. `blinded(state, agent)` reads the live table for a 479;
  `blind_miss` rolls once per swing (`random.random() < 0.90`, strict, so 0.90
  itself lands); `attack_fails` sends `[38, target, attacker, reason]` with the
  client's slot order and names the reason in the log.
* `land_swing` (the hostile's swing): rolled after the corpse guard and before
  any arithmetic. On a miss: `melee_attack_finished`, then the word, then
  nothing — no gain, no damage, no pool movement, no location roll.
* `hit_enemy` (the player's swing and an attack skill's strike, `swing=True`
  and `exact is None`): rolled after the interval gate consumed the timer. On a
  miss the bracket the landing path would send still goes out (`attack_started`
  unless `armed`/`skill_strike`, `melee_attack_finished` unless `skill_strike`),
  then the word, then return: no adrenaline strike (WIKI "Adrenaline": per
  *successful* hit), no damage, no critical, no preparation bonus. A spell
  (`exact`, `swing=False`) never consults the roll — GWW says attacks. An attack
  skill's miss sends the word alone, its own 46 being the caller's: the `[46,
  38]` batch the witness carries.
* `--no-blind`: the known-bad arm, 479 an icon.
* `test_mechanics` §21 (hostile: control, miss, the one in ten, the 0.90
  boundary, a closed episode, the revert), §22 (player: wire shape, the timer
  spent, the one in ten, a spell landing blind, an attack skill's word-only
  batch, control), §23 (the corpus pinned as floors — ≥ 1,000 closes, no-damage
  under 2 %, **0 blinded closes** as the check that goes red the day the rate
  can be measured, ≥ 1 property 38 with reason 2, P5 exclusive, no reason-3
  witness). Floor 106 → 129. `test_agentlife` 380, `test_guards` 41,
  `test_skilldamage` 57, `test_effects` 74, `test_killwindow` 21,
  `test_playerswing` 173 green.

### 44.6 What it does NOT settle, and the one run that would

* **The rate is unmeasured.** ~~P2 NO WITNESS.~~ **MEASURED 2026-09-16, §48.6: 27 misses of 30 blinded closes on retail, 0.90 exactly, band [0.735, 0.979] — OBSERVED, and the Student of Blind's own swings add 26 of 28.** The route below is the one that ran. It was an
  R0b runsheet line, not scheduled: the secondary account's character swinging
  at the Isle's *Student of Blind* (isle §7.2 puts 479 on the player there)
  for twenty swings — twenty closes under a live 479 against a 90 % binomial
  band is enough to refute 50 % or 100 %. §23's `blind == 0` check is the alarm.
* **A plain swing's batch** is `[1, 38]` by analogy with `[46, 38]`. Same run.
* **What our client draws** on `[38, target, player, 3]` — the yellow word, the
  sound — is the one thing a loopback probe *can* answer about this item
  (the client's rendering of a shape it has never been sent by us), and it is
  the same class as `--probe heal_number` (§42.7): registered here as
  `--probe blind_miss` material, not built, because nothing shipped depends on
  it and the wire shape is the client's own.
* **Nothing inflicts Blind yet.** `skill_condition` reads the inflicting skill's
  `bonus_scale_means` (GWW's progression variable) and no content row says
  "Blind"; which Pre-Searing skills do was not checked. The mechanic is live
  the day a row does.
* **Ranged.** "Missile attacks" and the projectile stray are the same rule
  with no bow in content (§16's preparation gate, the same gap).
* **The condition tally:** Bleeding, Burning, Disease, Poison (degeneration,
  §22), Deep Wound (§41) and Blind (this) — **6 of 10 conditions do what they
  say**; Crippled, Dazed, Weakness and Cracked Armor do not, and the last three
  wait on the attack/armour fields §41 named.

---

## 45. SKILLS-RC — the "AI heals itself" item was a MECHANIC error: Restore Condition heals per condition removed, targets an OTHER ally, and the client's target byte 4 now resolves (2026-09-10)

**Desk and corpus, pinned build 38797. No client run.** Asked as SKILLS-DW's
item (1), "the AI-heals-itself item (`pick_skill` is a fixture, R4c's design
question)". It is not an AI question. `PLAN.md` §8's old item 4 read *"The enemy
AI now heals itself to full every few seconds, because Restore Condition finally
resolves … It is an AI rule"*, and the 08-20 pools entry said the energy pool
had "closed" it by pacing. Both missed the skill's own text. Shipped:
`CONDITION_HEAL_RULE`, `allies_of`, `skill_target_kind`, `cast_recipient`,
`remove_conditions`, `resolve_heal` and the cast site's target gate in
`toolkit/authsrv/authsrv.py`; `effects.ALLY_TARGET` / `OTHER_ALLY_TARGET` /
`TARGET_KINDS`; the `skill_effect.276` row; `--no-condition-heal-rule` reverts;
`test_mechanics` §24–§26, floor 129 → 153; `test_agentlife` and `test_pools`
fixtures given the ally the rule requires.

### 45.1 What the skill actually says

WIKI (GWW, "Restore Condition", text taken 2026-09-10 through the wiki's search
index — the page itself refused the fetcher, so the description's revision
date is not retrieved): *"Remove all conditions from target other ally. For each
condition removed, that ally is healed for 10...58...70 Health."* Elite spell,
Protection Prayers, 5 energy, ¾ s, 2 s recharge (the client's own row agrees:
`energy = 5`, `activation = 0.75`, `recharge = 2`, `scale 10→70`), and it
**cannot self-target**. Three facts, none of them modelled: the heal is *per
condition removed* (so a target with none is healed nothing), the spell
*removes* those conditions, and the caster is never a legal recipient.

What our server did: `land_skill` resolved the heal on `effect_recipient(row,
agent_id, agent_id)` — caster and target both the caster — for the flat scale
value, 58 at rank 12, whenever the pool could pay 5 energy. With 5 pips over 30
energy that is one full-strength self-heal every ~3 s, ~19 health a second,
against a hammer that lands ~5 per 1.75 s. Unwinnable, as the item said — and
the cause was the mechanic, not the selector.

### 45.2 The corpus cannot referee this one — and says so

`cast276` census over every cast announcement in the live corpus (`0x00A0`
properties 60/50, `0x009F` 60, `0x00E3`): **1,364 announcements across 53
skill ids, and skill 276 is not among them.** Nobody in six Pre-Searing sessions
and one arena capture cast Restore Condition. A secondary read — finish batches
carrying both a `0x0044` removal and a 55 heal — found five, all coincidences of
an ally heal (313, 184, 180) with an unrelated expiry, none a cure. So the wire
shape of a cure-and-heal is **RECONSTRUCTION**: removals first, then the heal,
in the description's own sentence order, and the test says so.

### 45.3 The client's target byte, resolved from an independent column — CORROBORATED

§14 read codes 0 (self) and 5 (foe) off the type column and refused to guess 3
against 4: *"3 is plainly ally-shaped … and 4 is also ally-shaped (Restore
Condition 276), which is one distinction too many to guess at."* The distinction
is the wiki's targeting sentence, and the wiki shares no author with the byte.
Names resolved through `skilltable.py` → `textrec.py` against the owner's own
archive, targeting words from GWW:

| byte | skill | GWW says |
|---|---|---|
| 4 | Heal Other 286 | target other ally, cannot self-target |
| 4 | Infuse Health 292 | target other ally, cannot self-target |
| 4 | Restore Condition 276 | target other ally, cannot self-target |
| 4 | Dwayna's Kiss 283 | (oc) — other ally |
| 4 | Draw Conditions 311 | (oc) — other ally |
| 4 | Convert Hexes 303 | (oc) — other ally |
| 3 | Mend Ailment 277 | target ally |
| 3 | Purge Conditions 278 | target ally |
| 3 | Word of Healing 282 | target ally |
| 3 | Remove Hex 301 | target ally |
| 3 | Reversal of Fortune 307 | target ally |

Eleven skills, zero disagreements: **3 = ally (the caster is legal), 4 = other
ally (the caster is not).** The table has 124 threes and 41 fours; eleven is a
sample, and `test_mechanics` §25 pins exactly these eleven bytes so the claim
stays checkable. Codes 1, 6, 14 and 16 remain UNRESOLVED and still fall through
to the caster's aim.

### 45.4 Shipped, and where the line between mechanic and AI sits

* **`skill_effect.276`** carries `removes_conditions = "all"` and
  `heal_per_condition_removed = true`, provenance in the row.
* **`resolve_heal`** serves BOTH cast paths (the player's `cast_tick` and the
  enemy's `land_skill`, which used to compute the recipient differently — the
  enemy's forced caster = target). The recipient is `cast_recipient`'s verdict
  from the client's byte: self → caster; ally → the selected ally, else the
  caster (an ally spell aimed at a foe lands on yourself — RECONSTRUCTION of the
  client's auto-self; the rule the wiki gives is only that the caster IS legal);
  other ally → the selected ally and never the caster, **None if there is
  none**; foe / unresolved → the old fall-through. A row with
  `removes_conditions` strips the recipient's condition episodes
  (`remove_conditions`: `0x0044` each, the Deep Wound's maximum back, the status
  word without the bits, the regen re-announced), and one with
  `heal_per_condition_removed` heals the scale **once per condition removed and
  nothing when none was**.
* **The cast site's target gate**, beside the resource gate and in its class:
  not *which* slot (that stays the round-robin fixture, owner's ruling) but
  *can this agent legally cast the slot it picked*. A code-4 skill with no other
  living ally is skipped and stays ready, exactly as an unpayable one is; among
  several legal allies the lowest id is taken — a fixture choice, said at the
  site so nobody reads it as a monster's preference. The cast announcement and
  the on-body visual name that ally (`cast_target`); everything not an ally
  spell aims at the player as before.
* **Consequences on the shipped default bar:** a lone Hatcher never casts 276
  (it swings, and cycles 253/312/289); with `--enemies N` each hostile casts it
  at the lowest-id other hostile, where it does nothing unless that body carries
  a condition — Sever Artery's Bleeding, say — in which case it cures it and
  heals 58 per condition. That is retail's own counterplay shape.
* **`--no-condition-heal-rule`**: the flat self-heal on any target, the
  pre-2026-09-10 wire.
* Tests: `test_mechanics` §24 (no condition → nothing; one → removal then 58;
  two incl. Deep Wound → both removed, the 20 back to the pool first, then 116
  sent and 70 landing; the revert), §25 (the eleven bytes; `cast_recipient` on
  every kind; `allies_of` excludes self, corpses and other allegiances; the
  player's 276 at a foe resolves nothing), §26 (the tick: alone → no cast, slot
  still ready, a swing instead; with an ally → `[60, 10, 11, 276]`, the landing
  58-led with no heal on an unconditioned ally, and a cure + 58 on a bleeding
  one; the revert). `test_agentlife`'s enemy-skill section and `test_pools`'
  enemy gate now stand an idle ally beside the caster, because a lone hostile
  cannot cast slot 1 any more; the two checks that described the flat
  self-overheal now assert its absence. Floor 129 → 153; agentlife 380, pools
  127, skilldamage 57, effects 74, guards 41, castcycle 35, killwindow 21,
  burrow 31, playerswing 173 green.

### 45.5 What it does NOT settle

* **The wire shape of a cure** — **WITNESSED 2026-09-17, §49.6: Mend Ailment, `0x0044` then the heal, 2 of 2, and no heal word when nothing remains.** It was: removal-then-heal — has no retail witness
  (§45.2). A live capture with any condition-removal heal (Mend Ailment, Mend
  Condition, Dismiss Condition are all common) would referee it; not scheduled.
* **Mend Ailment's own rule** ("for each REMAINING condition") is a different
  formula and is not modelled; the row shape here (`removes_conditions`,
  `heal_per_condition_removed`) does not express it.
* **Skill 276 is elite** (monsterai §5.1's error 1) and sits on a bar that
  claims "non-elite"; untouched here — the bar is a fixture.
* **The AI question is still open and still R4c's:** *when* a monster casts a
  cure is per-skill data (heroes §5.6, GWW's per-skill usage sections). What
  this section removes from that question is the part that was never AI — the
  skill's arithmetic and its legal targets.
* The old §8 item 4 is struck; the 08-20 "closed by a resource rule" sentence
  in the pools entry was a pacing, not a closure, and is annotated rather than
  rewritten.

---

## 46. SKILLS-MA — Mend Ailment: remove ONE condition (the most recently applied) and heal per condition REMAINING (2026-09-10)

**Desk, no run, no corpus witness.** Asked as §45.5's second item. The row
shape §45 introduced (`removes_conditions`, `heal_per_condition_removed`) could
not express this skill; it can now, with two generalisations and no new
machinery: `removes_conditions` is `"all"` or a **count**, and a second flag
`heal_per_condition_remaining` scales the heal by what is LEFT. Shipped in
`resolve_heal` / `remove_conditions` (`toolkit/authsrv/authsrv.py`), the
`skill_effect.277` row, `test_mechanics` §27 (floor 153 → 162); the
same `--no-condition-heal-rule` reverts it.

### 46.1 The rule

WIKI (GWW, "Mend Ailment", text taken 2026-09-10 through the wiki's search
index; the page refused the fetcher, revision date not retrieved): *"Removes
one condition ... from target ally. For each remaining Condition, that ally is
healed for 5...57...70 Health"* — and the wiki's own note that, despite the
concise text's "removal effect" wording, *"its healing effect only triggers for
each remaining condition"*. The client's row agrees on everything it can:
`scale 5→70` (57 at rank 12), `energy 5`, `activation 0.75`, `recharge 5`,
`target = 3` — ally, the caster legal (§45.3).

**Which condition goes** when the target carries several: WIKI (GWW, "Effect" /
"Cover"): *"when a skill removes one or multiple effects of a particular type
... the most recently applied effect is always the first one to be removed,
followed by the second most recently applied effect and so forth."* That is the
mechanic cover conditions exist to exploit, and it is a rule about ORDER that
our episode table can honour exactly: every episode carries `applied_at`
(§16's table, unchanged), so `remove_conditions(count=1)` sorts the agent's
conditions newest-first and takes the head.

### 46.2 Shipped

* `remove_conditions(..., count=None)`: candidates ordered by `applied_at`
  descending (buff id as the tie-break), `count` takes the head; `None` is the
  old "all". The wire per episode is unchanged.
* `resolve_heal`: `removes_conditions` may be `"all"` or a positive int (a
  bool is refused as a count); `heal_per_condition_remaining` multiplies the
  scale by the conditions still on the recipient after the removal, and heals
  nothing at zero. The return row carries `remaining` beside `removed`.
* `skill_effect.277`: `removes_conditions = 1`,
  `heal_per_condition_remaining = true`, provenance in the row.
* §27: no condition → nothing; ONE → removed and **nothing healed** (the whole
  difference from Restore Condition, which heals 58 here); Bleeding then Poison
  → the Poison goes, the Bleeding stays, one remaining heals 57 (40 landing);
  Bleeding, Poison, then Deep Wound → the Deep Wound goes (its open took the
  pool 10 → −10 signed, its close gives the 20 back), two remain, 114 sent, 90
  landing; the PLAYER casting it at a FOE lands on the player (target byte 3's
  caster fall-back) and cures the player's newest condition; the revert is a
  flat 57 with no cure.

### 46.3 What it does NOT settle

* **No retail witness for any cure's wire** (§45.2 stands): removal-then-heal
  is RECONSTRUCTION, and the newest-first rule is WIKI. One live capture with a
  Mend Ailment or Mend Condition cast onto a body carrying two conditions would
  referee both at once.
* **Mend Condition (275)** — "removes one condition; if a condition was
  removed, heals" — is a third shape (heal on removal, flat) and is not
  modelled; the row would need a `heal_if_removed` flag. Not on any bar here.
* **Nothing casts 277** on this server today: it is on neither bar. The row is
  live the day it is.

---

# OBSERVED, 2026-09-15: the skill library is TWO sets, and the client keeps them in two different objects

## 47. SKILLS-LIB — account-wide unlocks and per-character learned skills, separated

Opened on the owner's ask ("set up the player's available skill library; in stock
it's an account-wide listing, let's keep that"), and the first pass of it got the
scope wrong in the useful direction: the corpus was asked whether one account-wide
list was enough, and answered that retail keeps **two**. The owner's correction
("i want stock behavior, so if we need account-wide and per-character then let's
do that") is what this section builds.

Until today this server sent **one** bitmap — whatever `--unlocks` produced — in
**both** messages. That worked, and it modelled one library where the game has two.

### 47.1 The corpus: the two messages disagree, and neither contains the other

Measured with `toolkit/authsrv/livewire.py` over every `origin: live` capture,
decoding both directions and refusing any connection whose byte accounting does
not close.

| Message | Scope | What the corpus shows |
|---|---|---|
| `0x001D` `PVP_UPDATE_UNLOCKED_SKILLS` | **account** | byte-identical on every connection of one account, whichever character, whichever map |
| `0x00DB` `UPDATE_UNLOCKED_SKILLS` | **character** | varies per character on the same account |

The decisive row is capture **`20260817T231139`**, where one connection carries
both: the account set holds **19** ids and the character set holds **21**, of
which **19 are shared and 2 are not** (`364`, `384`). So a character can know a
skill the account has never unlocked, **neither set contains the other**, and one
bitmap cannot stand in for both. OBSERVED.

A second, independent witness for the same split sits in the write path. On the
Factions tutorial (`20260913T210901`, port 60877) the two Mantid grants each went
out as `0x00DC` + `0x00D9` + `0x001C`, while the quest reward's Resurrection
Signet went out as `0x00DC` + `0x00D9` and **no `0x001C`** — the owner's account
already held that skill. So:

* **`0x00DC SKILL_SET_COPIES` is "this CHARACTER learns it"** and fires every time.
* **`0x001C SKILL_UNLOCKED` is "this ACCOUNT unlocks it"** and fires only when the
  id is new to the account.

That is the same two-set model the load-time messages carry, seen from the delta
side. The quests arc already recorded both halves of this observation (its §10.2)
without naming the account/character split it implies.

### 47.2 The client keeps them in two different objects — OBSERVED, static, 38797

The wire split could have been a server-side bookkeeping detail that the client
flattened. It is not. Traced on the pinned pristine build:

```
0x00817080:  call 0x47f660 / mov ecx,[eax+0x2c] / add ecx,0x710   <- 0x00DB's container
0x00804840:  call 0x47f660 / mov ecx,[eax+0x28] / add ecx,0x124   <- 0x001D's container
```

Same TLS context getter, **different context member** — `+0x2C` is the character
context, `+0x28` the account context — **and** a different displacement. `0x001D`'s
handler `0x00804810` reaches an `AcctCliUnlock` object at `acctCtx[+0x28]+0xB4` and
fills the container at its `+0x70`, layout `{data +0, alloc +4, wordCount +8}`;
it broadcasts event `0x100000C4` where `0x00DB` broadcasts `0x1000005F`. Each
writer has exactly one direct caller — its own handler — and neither touches the
other's memory. **Two sets, in the client, not merely on the wire.**

This also sharpens `studies/profession/RUNS.md` §10.2, which proved `0x00DB` owns
`+0x710` by a single `add ecx,0x10`: the account container is a different object
entirely, not a rival reading of the same one.

### 47.3 The reader that makes the account set load-bearing, and it is not the panel

Three UI sites read the account container, each asserting it non-null:
`GmDeckBuilder` (`GmDeckBuilder.cpp:1275`), `GmSkTome` (`GmSkTome.cpp:125`) and
`GmSkSlot` (`GmSkSlot.cpp:204` and `:206`). The load-bearing one is the last:

> `unlockedSkills->BitTest(sourceSkillId)`
> — `GmSkSlot.cpp:206`

`GmSkSlot` is the **skill-slot equip/drag validator**, and it bit-tests the
**account** set. Joined with §9 — which measured that unlock state does **not** gate
whether a bar skill *draws* — this gives a delayed failure with a clean shape: a bar
carrying a skill outside the account library **renders perfectly** and then asserts
the moment the player drags that slot. The server now warns at load naming the
offending ids rather than letting anyone meet it as a dialog.

`GmDeckBuilder`'s refresh picks **which** set to enumerate at run time, from a
per-player flag (`test al, 2` on a flags dword from `0x00815A80`): clear takes the
account set, set takes the character set. **The flag's meaning is UNVERIFIED** —
the same word is tested by `VnLearnSkill`, the trainer — and the obvious reading
("is this a PvP character") is a guess this section does not make.

### 47.4 What shipped

Storage is the account store, because the library is account state living in the
vault rather than world content: `content/*.toml` rows are facts about the world
every operator shares, this is one person's account.

* **`charstore.py`** — `account.unlocked_skills` and `characters[uuid].learned_skills`,
  each an optional id list, validated at load (ints, `>= 1`, no duplicates) with
  id 0 refused by name for the reason `refuse_skill_zero` exists.
* **Absence is not emptiness**, and that is what keeps every pre-existing run
  byte-identical: an absent list means "not authored" and `--unlocks` still answers
  for that half; an empty list is an authored answer and is sent as an empty bitmap.
  The two halves fall back **independently**.
* **`skillunlock.resolve_library`** — the store-or-flag choice, lifted out of
  `handle_request_game_instance` so a test can reach it; `words_from_ids` /
  `ids_from_words` are the bitmap round trip, and `words_from_ids` is now the single
  site enforcing both client-killing rules (id 0, id past the build's table), which
  `build_unlock_bitmap` now calls rather than duplicating.
* **`grant_skill`** persists both halves, gating `0x001C` on the **account** set per
  §47.1 rather than on the per-connection set it used before.
* **A seed guard, and it is the subtle part.** With no stored list the flag is in
  force and may be sending 1,333 ids. Letting a quest reward create
  `unlocked_skills = [40]` would replace that library with a one-skill one at the
  next login, silently, discovered only when a player opened the panel. So the
  mutators **refuse to create a list** from a bare id: the caller hands over the set
  currently in force as a seed, and the stored list is that set plus the new id.
* **`python toolkit/authsrv/charstore.py`** is the operator's read/write surface
  (`--list`, `--show`, `--unlock`, `--lock`, `--learn`, `--unlearn`, `--set-*`),
  and it says out loud when adding one id would CREATE a list where none existed.

### 47.5 What this does NOT settle

* **No client session has been run against a store-driven library.** Everything
  above is the corpus, the disassembly and the test suite. The two bitmaps are
  proven to differ in `test_charstore.py`; that a retail client *shows* the
  difference — the picker listing the character set while the equip validator
  honours the account set — is UNVERIFIED on screen.
* **The `GmDeckBuilder` flag** (§47.3) is unread. Until it is, which set the deck
  builder shows for a given character is a guess.
* **Nothing writes either list from the client's side.** **One path answered 2026-09-16, §48.9: a Priest of Balthazar purchase is `0x003B` up and `0x00EE` (faction −1000) + `0x001C [skill, 0]` + `0x00DC [skill, 1]` down — the quest-reward grant — with NO `0x001D` re-sent; the next `0x00DB` carries the bit.** Skill trainers
  (`VnLearnSkill`), tomes (`GmSkTome`, `0x006D TOME_UNLOCK_SKILL`) and capture
  signets all exist in the client and none of them is answered here; a grant only
  happens because a quest reward row says so.
* **`0x00DC`'s copies field** is still 1 in every sighting, so "copies" above 1
  remains UNVERIFIED.

---

## 48. RUN-SKILLS-RB — REGISTERED 2026-09-16, not yet run: Reversal of Fortune and Blind on the Isle, three no-witness items in one eight-step owner-driven capture

**Why now.** The owner exchanged Imperial for Balthazar faction on 2026-09-16 and is
unlocking skills with it. Balthazar unlocks write the ACCOUNT set (§47.1, `0x001D`), which
is the set §47.3 says gates equipping, and the secondary account's PvP Warrior (the rung-7
and rung-8 character: level 20, 480 health, sword) can equip any unlocked Monk skill after a
free secondary change at the Great Temple's Profession Changer. That puts a prevention
enchantment on a body that can be hit, for the first time, and every open item below is one
whose closing line already reads "an R0b runsheet line, not scheduled".

Plan `vault/plans/skills_rof_blind.txt` (sha256 `7b001a77…` from `marks.py --check-plan`,
8 steps), sealed by `livesession.py --plan` at launch. **Eight steps, three questions, one
meaning for F11: "UNDER — it happened while the icon was on me."** The steps are bare
actions; every prediction lives in the plan's header (the 8b/8c lesson, §7.8) and is
restated here so the document carries it.

### 48.1 The three questions, and where each is open

| | open item | today's state | the step |
|---|---|---|---|
| Q1 | the account unlock on the wire | §47.5: nothing writes either list from the client side; priest, trainer and tome paths unanswered | `temple`: buy ONE unlock at the Priest of Balthazar with the tap running |
| Q2 | Blind's miss rate under a live 479 | §44 P2 NO WITNESS; `missjoin.py` carries it, not tests it | `blind`: ~25 swings at the Student of Blind from inside its ring |
| Q3 | the fully converted hit's damage word | slice F46.8: shipped by analogy, UNREAD on retail; the corpus holds no 307 and no prevention heal | `rof`: ~6 hits from the Master of Axes under Reversal of Fortune; `frenzy`: ~3 more with Frenzy also open |

### 48.2 Why the Isle carries all three — WIKI, fetched 2026-09-16

- WIKI (GWW, "Isle of the Nameless" §NPCs, raw fetched 2026-09-16): the **Student of Blind
  is listed under Foes** (level 20 Warrior), with the Masters of Axes, Hammers, Lightning and
  the rest; the practice Suits are foes too. So the Blind subject is attackable, and it
  stands inside its own ring — a swinger inside it is re-blinded while it swings. Our own
  rung-8 tape has its application: `0x0042` skill 479, duration **10.0** (`bufflog.py
  --capture 20260821T152147`), and the Students apply on proximity without attacking (§7).
- WIKI (GWW, "Student of Blind", raw fetched 2026-09-16): Zaishen Order, Warrior 20, one
  skill (Healing Signet); "inflicts blindness (unmodified) on nearby players for 10 seconds".
  Agrees with the tape's 10.0 — two witnesses of no shared ancestry.
- WIKI (GWW, "Reversal of Fortune", raw fetched 2026-09-16): id **307**, Monk, Protection
  Prayers, Enchantment Spell, 5 energy, ¼ s, 2 s recharge; *"For 8 seconds, the next time
  target ally would take damage or life steal, that ally gains that amount of Health
  instead, maximum 15…80"* (progression 15 at rank 0, 80 at 15). Notes: *"the healing
  occurs before damage"*; at rank 12 it negates up to 134 (67 reduced, 67 healed). Acquired
  from any Profession Changer including the Great Temple's, and — noted for a future
  pre-Searing witness — from Halbrik in pre-Searing Ascalon City.
- The foe Masters fight back (the Team Trials' opponents); the Students do not. That is what
  puts a hit under the enchantment on the same island as the Blind ring.

### 48.3 Predictions, stated before the launch

- **RB-P1 (Q1):** the purchase is a c2s message whose opcode is READ from the batch, not
  assumed; the reply carries a fresh `0x001D` with exactly ONE new bit and the character's
  `0x00DB` unchanged. Refuted if `0x00DB` moves, or if `0x001D` is not re-sent (then the
  account set is re-read only at the next load, and the `isle` step's load says which).
- **RB-P2 (§47.3):** the Isle load's `0x001D` is byte-identical to the post-purchase set,
  and the PvP character equips 307 with no refusal — the equip validator reads the account
  set. A refused equip refutes §47.3.
- **RB-P3 (Q2, §44 P2):** under a live 479, a swing close (property 1) is joined by
  `[38, target, player, 3 = miss]` and NO damage in ≥ 90 % of closes, and the miss carries
  no `0x00CF`. WIKI (GWW "Blind"): 90 %. Refuted if the two-sided 95 % binomial band on the
  closes excludes 0.90; twenty closes separate 0.90 from 0.50 and from 1.00. The `unblind`
  step is the same-tape control: zero `[38, …, 3]` on a practice Suit, every close with its
  damage.
- **RB-P4 (Q3, F46.8):** on the tick of a hit taken under an open 307: FIRST `[55, player,
  +h]` with h = min(hit, cap), THEN the damage word — **−0.0** when hit ≤ cap, −(hit − cap)
  when hit > cap — then `0x0044` stripping 307. F46.8's analogy predicts the −0.0; "no word
  at all" or "a heal with no damage word" refutes it and rewrites the server's converted
  arm. The cap is the tooltip number the owner F11-notes at `[PROT=8]` (WIKI ~50); rank 8
  sits where an axe hit lands on EITHER side of it, so both arms come from one block.
- **RB-P5 (the Frenzy arm):** with 346 also open, two candidates and the word pair decides:
  (a) heal = min(2·hit, cap) with the remainder from the doubled hit; (b) heal = min(hit,
  cap) with the remainder doubled. GWW "Order of damage modifiers" is cited after the tape
  is read, not before.

### 48.4 The floor

Pre-registered, so a thin tape is reported thin: **≥ 20 swing closes under a live 479**
(Q2); **≥ 3 hits under an open 307 with the heal word joined on the tick, of which ≥ 1 at
hit ≤ cap and ≥ 1 at hit > cap**, or that arm reports "not exposed" (Q3); ≥ 2 hits under
307 + 346 or "not exposed"; the `idle` control clean (zero 55, zero 38, zero `0x0042` on the
player over ~30 s); the purchase on tape or "not exposed" (Q1). Abort a step — F9 on — if
the Blind icon never appears inside the ring, the Master will not engage, or health falls
under a third (walk away and Healing Signet; no death is needed for anything here).

Scoring: `bufflog.py --capture <stamp>` (the 479 and 307 episodes), `missjoin.py --rows`
(P2's band, which today prints NO WITNESS), `healjoin.py` (the 55 words and what shares
their tick), joined by ordinal to `plan_marks.jsonl`; a `rofjoin.py` only if the hand read
of the RoF ticks is not enough. Launched exactly as the aggro runs (RUNBOOK §"Capturing a
live session"): the stock-DH key-tapped build `vault/run-live/2026-09-01_44fbd68767a8`
(`dhbuild.py` 2026-09-16: `stock`, every build where it belongs), account `capture`,
`--confirm --plan --minutes 30`, the marks shell before login. Human cadence, one client,
the PvE Isle (map 280), no arena, no trading.

**Before launch, outposts only:** secondary Monk at the Profession Changer; 307 and 346 on
the bar with Healing Signet; Protection Prayers at rank 8 and the tooltip maximum noted;
Balthazar faction in hand and Reversal of Fortune NOT yet bought if that can be helped — the
`temple` step buys one unlock inside the run so the purchase is on tape (if it is already
bought, any other single cheap skill serves Q1, named by F11-note).

**Status: RAN 2026-09-16 21:31 (`20260916T213125`, plan sealed, sha matches, exe unchanged,
3 keys tapped), scored below.** Eight of eight steps advanced; eleven F11 notes — one at the
purchase, one at the first blinded swing, six RoF hits, three Frenzy hits. The owner's
setup: Protection Prayers 8 (RoF tooltip **50**), Strength 8 (Frenzy 148 %). Owner's note
after the run: the Master of Axes carries Strip Enchantment, so several RoF casts were
stripped without firing; every F11 in steps 6–7 is a real RoF hit. That matches the tape —
13 casts of 307, 10 fired, and the strips are `0x0044` without a heal beside them.

### 48.5 The floor, and where the run stood against it

| floor | required | got | verdict |
|---|---|---|---|
| Q2 swing closes under a live 479 | ≥ 20 | **30** (221.5–261 s) | met |
| Q3 hits under an open 307, heal joined on the tick | ≥ 3, ≥ 1 each side of the cap | **10** — 7 at or under the cap, 3 over it | met |
| Frenzy arm, hits under 307 + 346 | ≥ 2 | **4** | met |
| `idle` control (164.9–190.9 s) | 0 × 55, 0 × 38, 0 × `0x0042` on the player | 0 / 0 / 0 | clean |
| Q1 the purchase on tape | on tape or "not exposed" | on tape at 124.4 s | met |

Every number below comes from `bufflog.py --capture 20260916T213125`, `missjoin.py --rows`
and `healjoin.py`'s new `conversions()` (P6), joined to `plan_marks.jsonl` by ordinal; the
tick reads are scratchpad `rb_score.py`.

### 48.6 Q2 — Blind misses 27 of 30, and the Student is blind too — OBSERVED

**RB-P3 CONFIRMED.** One `0x0042 [player, 479, 0, buff, 10.0]` at 221.502 s as the Warrior
stepped into the ring; **30 swing closes** (property 1) inside the episode; **27 carried
`[38, 120, player, 3 = miss]` and no damage, 3 landed** (24, 24, 24 points with a 25-unit
`0x00CF`). Rate **0.90**, Clopper–Pearson 95 % **[0.735, 0.979]**: holds the wiki's 0.90,
excludes 0.50 (P < 10⁻⁵ at n = 30) and 1.00. `missjoin.py` P2 now reads *27 of 30, band
[0.793, 1.000] → True* where it read NO WITNESS. The same-tape control (`unblind`, 10
swings on a Suit): 0 fail words, 10 with damage. A missed swing granted NO adrenaline, 27
of 27 (missjoin P4, first blinded witnesses). **The 90 % moves from WIKI to OBSERVED**
(§44 P2), and the miss's batch shape `[close, 0x00A0 [38, target, attacker, 3]]` this
server sends since SKILLS-BL is OBSERVED on retail 27 times, not reconstructed from reason 2.

Three things the plan did not predict:

- **The re-application is silent.** Bufflog shows ONE 479 apply and ONE `0x0044`, at
  269.0 s — 47.5 s after the apply against a declared 10.0 — while the owner stood in the
  ring for ~40 s. The ring refreshes the condition without a second `0x0042`; the
  duration on the wire is the duration of ONE application, and an "open" 47 s episode is
  a refreshed one. The rung-8 tape's n = 1 was the same thing. (The torches of §7 re-apply
  visibly every ~2 s; the Students' rings do not.)
- **The Student of Blind attacks, and it is blind.** Agent 120 swung at the player 28
  times inside its ring — 26 closed with `[38, player, 120, 3]`, 2 landed (24 points). GWW
  lists Healing Signet as its only skill, which is about its bar, not its auto-attack; the
  plan's "does not attack" was §7's reading of the ring mechanism and is corrected here.
  Its 26 of 28 = 0.93 is a second, independent blinded swinger at the wiki's rate — but
  other agents' conditions never ride `0x0042` (F46.8), so `missjoin` cannot know it is
  blind and had counted those 26 into P1's *unblinded* baseline (0.7 % → 2.9 %, red).
  P1 now counts the UNEXPLAINED no-damage closes — those without a fail word — which is
  what it was always about; a close with a 38 is a miss, a block or a dodge by name.
- **Dodge is on the wire:** 7 `[38, …, 1 = dodge]` words on this tape (the client's own
  reason name), none before it. Not read further here.

### 48.7 Q3 — the converted hit: heal first, strip, then a POSITIVE zero — OBSERVED

**RB-P4 CONFIRMED in shape, REFUTED in one bit.** All ten RoF hits (the F11-marked six in
step 6 and four in step 7) close on one tick with the same batch, in wire order:

```
0x00A0 [20, player, cause, 546]      the trigger's effect id
0x009F [42, player, max]             (4 of 10 — the first trigger after the max changed)
0x00A3 [55, player, player, +heal]   heal = min(hit, cap), cap = 50 at PROT 8
0x0044 [player, buff]                the enchantment stripped
0x009F [7, player, 13] / [7, player, 18]
0x00A3 [16, player, cause, word]     the damage word, LAST
```

| t (s) | step | heal (× 480 or × 384) | damage word | bits | reading |
|---|---|---|---|---|---|
| 397.162 | rof | 0.0292 = **14** | **+0.0** | `0x00000000` | full conversion |
| 400.203 | rof | 0.0312 = 15 | +0.0 | `0x00000000` | full |
| 402.881 | rof | 0.0208 = 10 | +0.0 | `0x00000000` | full |
| 406.040 | rof | 0.0229 = 11 | +0.0 | `0x00000000` | full |
| 408.693 | rof | 0.1042 = **50** | −0.01875 = **−9** | `0xBC99999A` | remainder: a 59-hit |
| 415.645 | rof | 0.0156 × 384 = 6 | +0.0 | `0x00000000` | full, under Deep Wound |
| 448.121 | frenzy | 0.0917 = 44 | +0.0 | `0x00000000` | full |
| 451.822 | frenzy | 0.0208 = 10 | +0.0 | `0x00000000` | full |
| 461.414 | frenzy | 0.1042 = 50 | −0.0396 = −19 | `0xBD222222` | remainder: 69 |
| 491.821 | frenzy | 0.1042 × 384 = 40 | −0.0156 × 384 = −6 | `0xBC800000` | remainder |

- **Heal before damage, 10 of 10** — WIKI's order, now on the wire. Heal = min(hit, cap)
  with cap = the tooltip's 50: three remainders at exactly 50 (40 at the wounded 384 — the
  heal word is a fraction of the CURRENT maximum, F46 again).
- **The zero is `0x00000000`, +0.0 — not the graze's −0.0 (`0x80000000`).** Seven of
  seven. F46.7's ten graze words are all `0x80000000`; retail spells the two zeros
  differently, and the analogy F46.8 shipped had picked the wrong one. **Shipped:**
  `land_swing` and `land_skill` send `+0.0` when a conversion left nothing
  (`frac = _f32(0.0)`), the remainder otherwise; `test_mechanics` §9's CONVWORD pin flips
  to `0x00000000` with the witness named; `healjoin.conversions()` / `score_conversions()`
  is the corpus read and `test_skilldamage` §13 locks it (P6: n ≥ 10, zeros all +0.0,
  never −0.0, heal first 10 of 10; floor 61 → 63). **The client draws a 0 on the converted hits** —
  the owner's on-screen observation after the run (OBSERVED, by eye, the same digit F46.9
  measured for −0.0), so the two zero words are drawn alike and differ only in their bit.
- **The trigger re-declares the taker's maximum, 4 of 10** — 397.2 (480), 415.6 (384,
  inside the Deep Wound), 448.1 (480), 491.8 (384): each is the first trigger after the
  maximum last changed, which is F46.10's shape (a moved maximum rides the next landed
  hit) seen from the taker's own side. Not pooled with F46.10; noted. It reddened
  `test_mechanics` §19's "no other prop-42 moves inside a Deep Wound episode" because
  `deepwoundjoin` counted a re-declaration of the SAME value as a move and joined any
  earlier apply to any later close — both the test, fixed by signature (a stray is a
  value that differs from the one in force, inside THIS buff's apply..close).
- **Coincident self-heals are a different thing.** `healjoin.conversions()` finds 20 more
  ticks in the corpus where a self-heal rides beside a hit (Healing Signets closing under
  fire); none carries a `0x0044`, 13 of 20 have the heal first, and none is a zero. The
  strip on the tick is the conversion's signature and the scorer keys on it.

### 48.8 The Frenzy arm — both readings survive; labelled UNSEPARATED

Four hits with 346 and 307 open: 44 and 10 fully converted, 69 and 46 (at 384) leaving
remainders of 19 and 6 against a cap of 50 / 40. Under candidate (a) — heal = min(1.48 ·
hit, cap), remainder from the frenzied hit — the 69 is a 46.6 base; under (b) — heal =
min(hit, cap), the remainder × 1.48 — it is a 63 base with a 13-point remainder frenzied to
19.2 → 19. Both fit every row because the base hit is not on the wire; the Master's plain
hits ran 9–47 unfrenzied. **Not separable on this tape.** What would: a hit of KNOWN size
under both (a fixed-damage source — a Torch, or the Master of Damage's stated numbers) or
a remainder that only one reading can produce (a total under the cap with a remainder).
The server keeps F45's order (Frenzy before the conversion, candidate (a)) as the shipped
reading, labelled by analogy with GWW "Order of damage modifiers", unchanged.

### 48.9 Q1 — the unlock is the quest-reward grant, not a bitmap re-send — OBSERVED

**RB-P1 REFUTED in its specific form, and the shape is better than predicted.** The
priest's purchase (skill **332**, the owner's "other cheap skill" — 307 was already in the
account set at login) is one game-channel click, `0x003B [0x1000014C]` at 124.402 s, and
the reply at 124.455 s is one batch:

```
0x00EE [11, 0xFFFFFC18]      = -1000: the faction balance moves
0x001C [332, 0]
0x00DC [332, 1]              the grant pair the MANTID quest reward used (quests §10)
0x00CC [16]  0x0081 [37]  0x009F [12, 37, 0]
```

No `0x001D` was re-sent — not on the purchase, not on the Isle load (that connection
carried `0x00DB` only). The character bitmap did move: `0x00DB` at the temple was the
account set plus two bits (364, 384), and on the Isle it was that plus **332**. So on a
PvP character the character set contains the account set (33 of 33 bits) and absorbs an
unlock at the next load, and the account set is re-read at login, not pushed. **RB-P2
holds** (307 was in both sets; the equip was never refused), with the note that on THIS
character the two sets cannot disagree about 307, so §47.3's "the validator reads the
account set" is still the disassembly's claim, not this tape's. §47.5's "nothing writes
either list from the client's side" now has one path answered: the priest writes through
`0x00DC`, and `0x001D` is not the message that carries it. Filed there.

The auth channel's `0x0021 [5, 384]` / `0x0020 [5, blob]` pair at 131.71 s is the
character-settings store (HEROLIB-STORE's dirty-check dispatch) firing on the map change
after the bar edit at 105.2 s (`0x005C [.., 6, 346, 0]`, Frenzy into slot 6) — not the
purchase. It arrived 41 ms before the Isle load's advance mark.

### 48.10 Labels, and what changed

Blind's miss rate **OBSERVED** (27 of 30, plus the Student's own 26 of 28); the miss's
batch shape **OBSERVED** (27). The converted hit's word **OBSERVED**: +0.0 for a full
conversion (7), the negative remainder otherwise (3), heal first (10 of 10), strip on
the tick (10 of 10). The Frenzy arm **UNSEPARATED**. The unlock **OBSERVED** (n = 1):
`0x00EE` + `0x001C`/`0x00DC`, no `0x001D`. The silent re-application **OBSERVED** (n = 2
tapes). Shipped: the +0.0 word (server, two sites); P1's baseline by fail word;
`deepwoundjoin`'s stray by signature; `healjoin.conversions()`. `test_mechanics` 228
(floor 228, three checks rewritten), `test_skilldamage` 63 (floor 61 → 63),
`test_agentlife` re-run for the join modules it reads.

---

## 49. RUN-SKILLS-RB2 — REGISTERED 2026-09-17, not yet run: Mend Ailment, a recast while live, and a lopsided armour set under a spell — and the attack-speed item dropped before registration because the corpus already held it

The second skill-unlock capture, the same character and island as §48. Plan
`vault/plans/skills_rb2.txt` (sha256 `7d9ec582…` from `marks.py --check-plan`, 8 steps),
sealed by `livesession.py --plan` at launch. **Eight steps, one meaning for F11:
"CAST-UNDER — I cast it while the icon(s) this step names were still up."** The owner will
unlock Mend Ailment for it (on tape, step 1) and can remove armour pieces through the
inventory, which is what makes the third question askable at all.

### 49.1 Mined first: the attack-speed windup is already in the corpus — OBSERVED, no run

Four items were candidates. The first — ANIMREF §17's "the IAS windup needs a live capture
with a stance running" — was written on 2026-08-31 against 62 `0x0035` declarations, all
modifier 1.0, **zero exposure**. The owner's Warrior tapes since changed the exposure and
nobody re-asked. `toolkit/authsrv/iaswindup.py` asks (predictions W1–W3 in its header,
stated before the numbers): 1,231 swings under a declared `0x0035`, 27 groups of ≥ 4, two
of them under Frenzy's 0.67 on two different bases:

| tape | agent | base | modifier | n | median windup | A `m·base/2 − 0.1` | B `m·base/2` |
|---|---|---|---|---|---|---|---|
| `20260914T005758` (JARIN's hero) | 30 | 1.33 | **0.67** | 41 | **0.346** | 0.346 | 0.446 |
| `20260914T005758` | 30 | 1.33 | 1.00 | 4 | 0.558 | 0.565 | 0.665 |
| `20260914T180058` (WARRIOR-PRE) | 31 | 1.75 | **0.67** | 8 | **0.483** | 0.486 | 0.586 |
| `20260914T180058` | 31 | 1.75 | 1.00 | 10 | 0.778 | 0.775 | 0.875 |

Every one of the 27 medians is within 7 ms of candidate A; candidate B misses every group
by 0.09–0.11 s. **The −0.1 is measured, not fitted, and the modifier multiplies the base
before the halving** — the law `attack_windup` has shipped since ANIMREF. `test_castcycle`
§11 locks W1–W3 (skips by name without the vault; 51 → 54 with it, bare-machine floor 49
unchanged). ANIMREF §17 and the two `PLAN.md` lines that called this "an R0b runsheet line"
are closed by pointer. The item is NOT in the plan.

### 49.2 The three questions that are in it

| | open item | today's state | the step |
|---|---|---|---|
| Q1 | a condition-removal heal's shape, and Mend Ailment's two rules | §45.5: "no retail witness"; §46: desk + WIKI only, shipped | `mend`: Weakness, then Poison, then Mend Ailment twice |
| Q2 | recasting an effect while it is live | §36: no witnessed deliberate extension; our REMOVE-then-APPLY neither confirmed nor refuted | `recast`: RoF ×3 at its recharge inside its 8 s; Frenzy ×2 |
| Q3 | one elemental rating or a location roll — and which rating | §43.4: CORROBORATED, never OBSERVED against a lopsided set | `armoured` then `stripped`: the Master of Lightning, five pieces on, then head/hands/feet off |
| — | the priest unlock, replicated | §48.9, n = 1 | `temple`: Mend Ailment bought on tape |

WIKI, fetched 2026-09-17 (raw): **"Mend Ailment"** — id **277**, Monk, Protection Prayers,
Spell, 5 energy, ¾ s, 5 s recharge; *"Remove one condition … from target ally. For each
remaining Condition, that ally is healed for 5…70 Health"* (5 at rank 0, 70 at 15; ~39–40
at 8). **"Master of Lightning"** — a foe, E/W 20, 15 Air Magic, bar: Lightning Javelin,
Lightning Orb (PvE Isle only), Blinding Flash, two attunements, Aura of Restoration,
Bonetti's Defense. Our own rung-8 tape has the Students' durations (`bufflog.py --capture
20260821T152147`): Weakness **20.0**, Poison **5.0**, Blind/Bleeding/Crippled/Dazed 10.0 —
which is why the plan takes Weakness first and Poison last, and avoids Dazed (it doubles
the cast and a foe Student's swing would interrupt it).

### 49.3 Predictions, stated before the launch

- **RB2-P1 (the unlock, DERIVED from §48.9 — a replication):** `0x003B` up; one batch down
  with `0x00EE [11, −cost]`, `0x001C [277, 0]`, `0x00DC [277, 1]`; no `0x001D`; the Isle
  load's `0x00DB` carries bit 277.
- **RB2-P2 (recast while live):** three candidates and the batch decides — (a) `0x0044`
  old buff then `0x0042` new, REMOVE-then-APPLY, what this server sends; (b) a bare
  `0x0042` with a new buff id, the old never removed; (c) nothing on the wire, the silent
  refresh §48.6 found for a ring. Frenzy asks the same of a stance.
- **RB2-P3 (Mend Ailment):** with Weakness (older) and Poison (newer) both live, the cast
  sends `0x0044` for **Poison's** buff, then `[55, player, player, +h]` with **h = 1 × the
  tooltip number**, removal BEFORE heal. The recast removes Weakness with nothing
  remaining: `0x0044` and **no heal word**. Refuted if Weakness goes first, if the first
  heal is 0 or 2×, or if the second cast heals.
- **RB2-P4 (the rating):** in the `stripped` block each of the Master's spells is STILL one
  value in whole points. Under a location roll, 3 of 8 rolls land on a bare piece (AR 0
  against 80 — about ×4), and ten hits all missing them has probability (5/8)¹⁰ = 0.9 %.
  **And which rating:** the value EQUALS the `armoured` block's if the rating is the
  chest's (§43.6, what ships); one value but shifted means an average over pieces; two
  buckets is a location roll and §43 reopens.

### 49.4 The floor

≥ 2 recasts of 307 while live and ≥ 1 of 346 (Q2); ≥ 1 Mend Ailment landing with both
conditions up and ≥ 1 with one (Q1); ≥ 6 hits of ONE spell in `armoured` and ≥ 10 of the
SAME spell in `stripped` (Q3), or that arm reports "not exposed"; the `idle` control
clean; the purchase on tape. Abort a step — F9 on — if the Master will not cast, or health
falls under a third. Scoring: `bufflog.py --capture`, `healjoin.py`, `spellhitjoin.py
--pairs` split at the step-7 mark, all in whole points of the maximum at the hit (F46).
Launched exactly as §48 (build `vault/run-live/2026-09-01_44fbd68767a8`, account `capture`,
`--confirm --plan --minutes 30`).

**Status: RAN 2026-09-17 09:03 (`20260917T090355`, plan sealed, sha matches, exe unchanged,
3 keys tapped), scored below.** Eight of eight steps advanced, ten F11 notes. The owner's
two notes from the `stripped` block, verbatim: *"i died at master of lightning, running
back"* and *"died again. big damage lightning spells kill me fast if they hit a bare body
part"* — which is RB2-P4's refutation, said by the operator before any scorer ran.

### 49.5 The floor

| floor | required | got | verdict |
|---|---|---|---|
| Q2 recasts while live | ≥ 2 of 307, ≥ 1 of 346 | **3 and 3**, every one F11-marked | met |
| Q1 Mend Ailment with both conditions up, and with one | ≥ 1 each | **2 and 2** | met |
| Q3 one spell, `armoured` / `stripped` | ≥ 6 / ≥ 10 | Lightning Orb **4 / 7**, Javelin **3 / 5** (two deaths cut the block) | not met as registered — and answered anyway: the refuting event needs one bare hit, and there are three |
| `idle` control | 0 × 55, 0 × `0x0042`, 0 × `0x0044` from a cast | clean (the Isle's periodic 160 aside) | clean |
| the purchase on tape | yes | yes, 77.12 s | met |

### 49.6 Q1 — Mend Ailment: the most recent goes, the heal counts what remains — OBSERVED, 2 of 2

Weakness (buff 112, 243.51 s) then Poison (buff 113, 244.21 s); the cast closes at 245.53 s
in one batch: `0x0044 [player, 113]` — **Poison, the most recent** — then `[42, player,
480]`, then `[55, player, player, +0.07292]` = **35 points**. The recast at 258.51 s:
`0x0044 [player, 112]` and **no heal word at all**. The F10 round repeats it to the digit
(274.63 s: Poison off, +35; 280.67 s: Weakness off, nothing). **RB2-P3 CONFIRMED on all
four clauses**: most recent first, one heal per REMAINING condition, removal before heal,
nothing at zero. §46's desk model and `heal_per_condition_remaining` stand as shipped, now
OBSERVED; §45.5's "the wire shape of a cure has no retail witness" is closed.

**And the 35 is a finding of its own.** The tooltip at Protection Prayers 8 is 40 (5…70).
The heal is 35 because the condition that REMAINS is Weakness: WIKI (GWW, "Weakness", raw
fetched 2026-09-17) — *"all of your attributes are reduced by 1"* — and 5 + 65 × 7 / 15 =
35.33, truncated to 35 (F46). So the heal is resolved at the caster's attributes as they
stand AFTER the removal and WITH the remaining condition's penalty. RECONSTRUCTION on the
wiki's rule, fitting 2 of 2 to the point. **Closed the same day as §51 (SKILLS-WK): the
penalty is on retail's WIRE, in the condition's own batch, and the server now does both
halves.**

One shipped-test consequence: Poison landing while Weakness was live newly set status bit
`0x40` alone (the generic `0x02` was already up), which reddened `test_mechanics` §19's
"483 and 484 set 0x42". The test, widened exactly the way its 482 neighbour is written.

### 49.7 Q2 — a recast while live: two shapes, by effect type, and the server already sends both — OBSERVED

| effect | what the wire carried at each recast | n |
|---|---|---|
| Reversal of Fortune (enchantment) | a **bare `0x0042` with a NEW buff id**; the older instance is NOT removed and closes on its own clock — 53: 161.10 → 169.10, 54: 163.83 → 171.83, 55: 167.92 → 175.92, each **8.000 s** | 3 |
| Frenzy (stance) | **`0x0044` then `0x0042` in one batch**, the freed buff id (53) handed straight back | 3 |

Candidate (b) for the enchantment, candidate (a) for the stance; (c), the ring's silent
refresh, is not how a CAST extends anything. `effects.EffectTable.open` has allocated a
new id per apply and let the older episode expire on its own duration since 2026-08-20,
and `exclusive_on` has closed a live stance before opening the next — so both shapes were
already ours. §36.8's "unwitnessed either way, neither confirmed nor refuted" is now
**CONFIRMED for both types**, and nothing ships. **The client drew ONE Reversal of Fortune
icon throughout the stack** (the owner, on screen) — §36's loopback finding, that a repeat
`0x0042` for a live (agent, skill) adds no second icon, holds on retail's own client against
retail's own traffic.

### 49.8 The unlock, replicated — RB2-P1 CONFIRMED, n = 2

`0x003B` at 77.119 s; at 77.170 s one batch: `0x00EE [11, −1000]`, `0x001C [277, 0]`,
`0x00DC [277, 1]`. No `0x001D` after it. The Isle load's `0x00DB` carries bit 277 (and
332, last night's); and this session's LOGIN `0x001D` had 34 bits where last night's had
33 — so the account set is re-read at login and that is when 332 reached it. §48.9's
shape holds to the message.

### 49.9 Q3 is its own section

The armour blocks refute SKILLS-FA's single rating. Scored and shipped as §50.

---

## 50. SKILLS-LR — a spell ROLLS A HIT LOCATION: §43's single elemental rating is REFUTED by a lopsided body, exactly where §43.4 said it could be (2026-09-17)

**One live tape, RUN-SKILLS-RB2's `armoured` and `stripped` blocks (`20260917T090355`), and
a server change.** §43 shipped "ONE rating, elemental, no location roll" on 68 of 68
single-valued Mind Burn hits, and §43.4 said plainly what that could not separate: eight
arena characters in five equal pieces. The owner took the head, hands and feet off a PvP
Warrior and stood in front of the Master of Lightning.

### 50.1 The measurement — OBSERVED

`spellhitjoin.location_buckets()` (new): projectile spell hits per (caster, skill, target)
in whole points of the maximum at the hit. Two filters, both measured here — the caster's
wand hits share the announcement window, so rows off the group's median flight time
(Lightning Orb 2.38–2.50 s, Javelin 1.57–1.77 s) are dropped; and a killing blow's batch
carries the death penalty's new `[42]` AHEAD of the damage word, so the word is read as
whole points of whichever maximum the target held makes it whole (F46).

| spell | `armoured` (five pieces) | `stripped` (chest + legs only) |
|---|---|---|
| Lightning Orb 229 (WIKI: 10…100, 25 % penetration) | **101 × 4** | **101 × 5, 286 × 2** |
| Lightning Javelin 230 (WIKI: 15…50, 25 % penetration) | **50 × 3** | 50 × 3, **140 × 1**, 45 × 1 |

- **286 / 101 = 2.832, and 2^(60/40) = 2.828.** A piece of AR 80 under 25 % penetration is
  an effective 60 — the baseline, ×1.0, which is why the armoured Orb reads its tooltip —
  and a bare piece is an effective 0. 140 / 50 = 2.80, the same step inside truncation.
  Both 286s are the two deaths the owner noted.
- **Bare hits 3 of 12** against the wiki's 3 of 8 for head + hands + feet: P(≤ 3 | 12,
  0.375) = 0.28. Consistent; the odds themselves stay WIKI.
- **Armoured, the same spells are single-valued** (4 of 4, 3 of 3) — so §43's 68 of 68 was
  measuring equal armour, not the absence of a roll. §43.4's caveat was the whole story.
- **One row is unexplained and named:** a Javelin for **45** at 530.80 s (flight 1.64 s, max
  336). It reads as an effective +8 armour at that instant (50 × 2^(−6/40) = 45.06). A
  differently rated PIECE is ruled out by the tape itself: every armour item it declares
  (`0x0161`) carries the single modifier 572/80 — Armor 80, no insignia, no bonus line
  — and the one other 572 on the tape is a shield (572/16) sitting in the inventory,
  which the armoured block's bare-tooltip 101 and 50 say was not worn. The owner does not
  recall the set, and nothing in the c2s stream between 517 s and 543 s is an equip. n = 1,
  UNEXPLAINED, not a claim.

**The single rating is REFUTED. Spells roll a hit location, as attacks do.** GWW's three
"attack" sentences (§43.2) describe where players noticed it, not where it stops.

### 50.2 Shipped

- `combatmath.player_spell_armour(..., location_key=None)`: with a key it returns THAT
  piece's elemental rating, and **0.0 for a location that wears nothing while others do**
  (what 286 / 101 says). `spell_armour_for` rolls `roll_hit_location()` — the wiki's
  3/2/1/1/1 of 8, already the swing's — under `SPELL_LOCATION_ROLL = True`.
- **`--no-spell-location-roll`** restores the chest's rating: the revert arm, REFUTED as a
  claim about retail. With five equal pieces (every set this server equips today) the two
  arms are byte-identical on the wire; what changed is the claim and what a lopsided
  content row will do.
- `test_skilldamage` §11 (+3: a bare roll resolves against 0 and a chest roll against the
  chest's; bare against baseline is 2^(60/40); the revert arm) and §12b (+1, the corpus
  lock: some projectile group holds two whole-point buckets within 1.5 % of 2^(60/40), ≥ 4
  and ≥ 2 hits — today Orb 101 × 9 / 286 × 2). Floor 63 → 67.

### 50.3 Labels, and what §43 keeps

The location roll for spells: **OBSERVED** (one caster, two spells, 3 bare hits of 12, one
tape). The ODDS per location: WIKI, consistent. §43's other halves stand untouched: the
rating is ELEMENTAL (`physical=False`), `Holy damage` and `+ Damage` ignore armour, the
multiplier is the wiki's `2^((60 − AR)/40)` — the armoured Orb at exactly its tooltip is a
fresh witness for that last one. §43.5's simultaneity argument (three bodies, one ratio,
one tick) was an argument about a second SKILL in the batch and still reads correctly; it
was never evidence against a roll on bodies in equal pieces.

---

## 51. SKILLS-WK — Weakness takes ONE off every attribute: retail says so on the wire, in the condition's own batch, and the server now does both halves (2026-09-17)

**Desk, on two tapes already in the vault. No new run.** Opened by §49.6: a Mend Ailment
cast at Protection Prayers 8 healed 35 where the tooltip said 40, and 35 is the rank-7
number. This server modelled Weakness's attack cut (SLICE-H12, `WEAKNESS_DAMAGE_FACTOR`)
and said in its own comment that the attribute half was not modelled.

### 51.1 The capture was asked first, and it answers more than the question — OBSERVED

The question was whether the penalty is server-side arithmetic only. It is not. The
Weakness apply's own batch on `20260917T090355` (243.513 s), in wire order:

```
0x0042 [player, 486, 0, buff 112, 20.0]
0x009F [6, player, 29]
0x00F1 [player, 0x02]                     the status word
0x003B [player, 15, 8, 7]                 Protection Prayers   base 8,  effective 7
0x003B [player, 17, 8, 7]                 Strength             base 8,  effective 7
0x003B [player, 20, 12, 12]               Swordsmanship        base 12, effective 12
0x003B [player, 21, 1, 0]                 Tactics              base 1,  effective 0
```

and the removal's batch (258.510 s, Mend Ailment's second cast) is its mirror: `0x0044`,
the status word, then `[15, 8, 8]`, `[17, 8, 8]`, `[20, 12, 13]`, `[21, 1, 1]`. `0x003B`
is `AGENT_UPDATE_ATTRIBUTE [agent, attribute, base, effective]`, the message this server
already sends for a spend. Four readings, all from the rows:

- **The BASE is not moved; the EFFECTIVE is, by one.** Swordsmanship is the discriminating
  row: base 12, effective 13 with the owner's +1, weakened to 12 — so the penalty comes off
  the effective rank, after the item bonus.
- **Every attribute with a base rank rides, and no rank-0 attribute does** — WIKI (GWW,
  "Weakness", raw fetched 2026-09-17): *"all of your attributes are reduced by 1 …
  Attributes at rank 0 are not affected"*. Zero rank-0 rows in 11 pairs.
- **It rides the condition's own batch, right behind the status word**, at the apply and at
  the removal — the position Deep Wound's `[42]` and Crippled's `0x0027` take (§41, F48).
- **The rung-8 tape has it too.** `deepwoundjoin.weakness_attributes()` finds three Weakness
  episodes in the corpus — two here, one on `20260821T152147` — and all three applies and
  all three removals carry the rows: **11 attribute pairs, 11 lifted by exactly one at the
  removal, 11 with the base unchanged.** It was on disk for four weeks; nobody had asked.

And the consumer side, §49.6's datum: the heal resolved at the weakened rank, 5 + 65 × 7/15
= 35.33 → **35**, on 2 of 2 casts. The wire half is **OBSERVED** (n = 3 episodes, 2 tapes);
the arithmetic half is OBSERVED on one skill and carried to the others by the wiki's rule.

### 51.2 Shipped

- `episodemods.weakened(state, agent)` and `weakened_rank(state, agent, rank)` — one lower
  under a live 486, never below zero, 0 and None untouched — with the flag
  `WEAKNESS_ATTRIBUTES` in the leaf (a leaf may not import its origin, and `taker_rank`
  needs it). Applied at every rank READ: the player's weapon rank at the swing, the attack
  skill's bonus, the press, the cast resolution; a body's skill rank in `land_skill`; and
  `taker_rank`, so a weakened Frenzy takes its percent at Strength − 1.
- `push_attributes(send, state, agent, conn)` — the `0x003B` burst, `[player, attribute,
  base, effective − 1]` for every attribute with a base rank, the mirror at the lift, one
  burst per CHANGE. Called beside `push_speed` at all seven sites that open or close an
  episode plus the tick, so no close path (expiry, cure, strip, death) can leave the
  client showing a rank the server stopped using. The player only: what retail tells an
  observer about ANOTHER agent's weakened ranks is unread.
- **`--no-weakness-attributes`** is the revert arm: no rank moves, no `0x003B`.
- `test_mechanics` §31 (10 checks: the rank rule and its three edges, the 35, the apply's
  batch and its order, the silent re-application, the expiry's restore, the revert arm) and
  §32 (2, the corpus lock WK1–WK2). Floor 228 → 240.

### 51.3 What it does not settle

- **CLOSED by §52 (RUN-SKILLS-WKL): BEFORE, 5 of 5, and ours already did.** ~~A cast that
  removes Weakness itself while another condition remains~~ — does the heal
  read the rank before or after the lift? Both Mend Ailment heals on the tape had Weakness
  as the REMAINING condition, so they cannot say. Ours reads the rank as the cast
  resolves, before its own effects: RECONSTRUCTION.
- **A rank-0 attribute boosted by a rune** is untouched per the wiki; this server keys on
  the rank it reads at each site, which for the player is the content rank. Unwitnessed.
- **Heroes and other bodies** get the arithmetic and no wire; retail's word for them is
  unread (other agents' conditions never ride `0x0042` either — F46.8).

---

## 52. RUN-SKILLS-WKL — the Weakness LIFT: a cast that removes Weakness heals at the rank BEFORE the lift — RAN AND SCORED, 5 of 5, the shipped read site CONFIRMED (2026-09-17)

**One owner-driven live capture, the Isle of the Nameless, the RB2 character.** Plan:
`vault/plans/skills_wkl.txt`, sha256 `c53ab93e861f…`, seven steps, F11 = ALL-UP. It is
§51.3's first open item and nothing else.

### 52.1 Mined first: zero exposures — OBSERVED

Three Weakness episodes in the corpus (§51.1). Two ended under Mend Ailment with Weakness as
the REMAINING condition and then alone; the August one ran out on its own. **No cast on any
tape removes Weakness while another condition is live**, so the corpus cannot say, and the
run is not a re-measurement of something on disk.

What the corpus DID give the plan is the row. The owner's position at each ring's apply on
`20260821T152147` and `20260917T090355` (c2s `0x003D`, the nearest send to each `0x0042`)
puts the Students along one line in the order **Disease – Dazed – Weakness – Poison – Blind –
Crippled – Burning – Bleeding**, 100–400 units apart, and RB2's Weakness→Poison applies
landed 0.7 s apart. Ring durations OBSERVED: Weakness 20 s, Blind / Crippled / Dazed /
Bleeding 10 s, Poison / Disease 5 s, Burning 3 s. Since Mend Ailment takes the most recent
condition (§49.6), **the order the rings are walked in is the experiment**: RB2 walked
Weakness→Poison; this run walks Poison→Weakness.

### 52.2 Predictions, stated before the launch

- **WKL-P1 (the question):** Poison then Weakness, Mend Ailment at once. The cast's batch
  names WEAKNESS's buff in its `0x0044`, Poison remains, and the heal is **35** — the rank
  read before the cast's own effects, which is what this server ships (RECONSTRUCTION).
  **The rival is 40**, and it is not a straw man: the heal's count is demonstrably taken
  after the removal (it counts what remains), so an engine reading the rank at that same
  moment gives the un-weakened number. A 40 refutes the shipped read site.
- **WKL-P2 (the wide arm):** Blind, Poison, Weakness last: **70** (or 35 if Poison's 5 s ran
  out) against the rival's 80 (or 40). No multiple of 35 is a multiple of 40 below eight
  conditions, so every outcome discriminates.
- **WKL-P3 (positive control):** Blind then Crippled, no Weakness: the heal is **40**. It
  shows the un-weakened number exists on the same day's wire, and it reads the rounding —
  5 + 65 × 8/15 = 39.67, so a ROUNDED 40 against a truncated 39, which RB2's 35.33 could
  not separate (`skillread.skill_scale_value` rounds, MEASURED from the client, combat 8c).
- **WKL-P4 (replication):** RB2's own walk heals **35** again, with the four `0x003B` rows of
  §51.1 in the apply's batch and their mirror at the second cast, which heals nothing.
- Recorded, not predicted: whether the `0x003B` restores ride ahead of the `55` word.

### 52.3 The floor and the abort

≥ 2 casts whose batch removes Weakness's buff with ≥ 1 other condition live (the TAPE
decides that; the F11 is the cross-check), ≥ 1 control heal, ≥ 1 replication heal, the idle
control clean. Under two exposures the question is reported "not exposed", never scored as
a null. Abort a step under a third health; nothing in the run hits hard.

### 52.4 The run — `20260917T124314`, floor met on every arm

Plan sha matched the seal; 18 marks, 6 notes, 0 refused. The idle control is clean (zero
`55`, `0x0042`, `0x0044`, `0x003B` on the player; the only player rows are the `0x00F1`
word's 0x80 bit toggling, which is not an effect). Maximum 480 throughout, so every heal
word below is whole points of 480 (F46). Eight Mend Ailment heals:

| walk | removed | remaining | heal word | points | |
|---|---|---|---|---|---|
| Blind → Crippled ×2 | Crippled | Blind | 0.083333 | **40** | WKL-P3 control |
| Blind → Poison (the owner's mis-walk, step 3) | Poison | Blind | 0.083333 | **40** | a third control, unplanned |
| Weakness → Poison | Poison | Weakness | 0.072917 | **35** | WKL-P4, RB2 replicated (n = 3 with RB2) |
| **Poison → Weakness ×3** | **Weakness** | Poison | 0.072917 | **35** | **WKL-P1** |
| **Blind → Poison → Weakness ×2** | **Weakness** | Blind, Poison | 0.145833 | **70** | **WKL-P2** |

### 52.5 WKL-P1 / P2 CONFIRMED — the rank is read BEFORE the cast's own removal, 5 of 5 — OBSERVED

Every cast whose batch names Weakness's buff in its `0x0044` healed **35 per remaining
condition**, the rank-7 number; the rival's 40 / 80 appears zero times in five, against
three 40s from the same bar minutes earlier. So the argued rival is REFUTED: the heal's
COUNT is taken after the removal and its RANK before it — they are not read at the same
moment. `resolve_heal` takes the rank its caller read as the cast resolved, which is this;
§51.3's first item is closed and nothing ships.

**The recorded order is the striking part.** All five lifting batches read

```
0x0044 [player, Weakness's buff]
0x00F1 status
0x003B x4                          the restores: [15,8,8] [17,8,8] [20,12,13] [21,1,1]
0x00A3 [55, player, player, 35/480]
```

— the restores ride AHEAD of the heal word, so the client's Attributes panel already reads
Protection 8 when the rank-7 number lands. Ours sends the same order (`remove_conditions`
closes the episode and `push_attributes` fires there, then `heal_agent`); `test_mechanics`
§33 pins it through the real path and WKL1–WKL2 pin the corpus. WKL1 is a SIGNATURE, not
the number 35: points = remaining × Mend Ailment's scale at one under the Protection rank
the batch's own `0x003B` restores, and never at the restored rank.

### 52.6 WKL-P3 CONFIRMED, and it reads the rounding — OBSERVED 3 of 3

The no-Weakness heals are **40**, not 39: 5 + 65 × 8/15 = 39.67 is ROUNDED, as
`skillread.skill_scale_value` does (combat 8c, MEASURED from the client's interpolator).
RB2's 35.33 could not separate round from truncate; this does. (The whole-points
truncation of F46 is a different step — it acts on the final amount, which is already an
integer here.)

### 52.7 Two suite reds from the owner's tapes, both the tests

- `test_mechanics` "481 sets 0x0A": Crippled landed while Blind was live, twice, so the
  generic 0x02 was already set and 481 newly set 0x08 alone — the 482 and 484 lines' own
  shape. Widened the same way, 0x0A kept REQUIRED as the positive control.
- `test_effects` "non-condition applies predicted exactly": from RB2's tape, not this one
  (the test was not in RB2's affected set — it should have been). Skill 475, a Ranger
  ritual (type_code 22), rode `0x0042` onto the owner at field3 7 with 46.0 once and
  10000.0 twice, each removed seconds later: a spirit's RANGE effect, whose clock is the
  spirit's — what is left of the rank's 50 s, or a sentinel — not a cast onto the agent.
  A named exception by signature with its own refutable check (never more than the rank's
  duration unless exactly the sentinel). What decides 46-vs-10000 is unread, n = 3.

## 53. SKILLS-AD — the damage-taken adrenaline rule, closed by two tapes made to be hit: ROUND is the only survivor, the denominator is the CURRENT maximum, there is no cap at 25, and a hit converted to nothing still gets a gain of 0 (2026-09-17)

**Status: MINED, nothing run and nothing shipped.** `test_adrenwire` was red on `main`; this
is what the red rows ARE. Both tapes already existed — RUN-SKILLS-RB (`20260916T213125`,
§48) and RUN-SKILLS-RB2 (`20260917T090355`, §50) — and neither run was about adrenaline.
They are the first tapes in the corpus where a character carrying adrenal skills stood and
was hit, which is the sample §34 said it lacked. Extractor: `toolkit/authsrv/adrenjoin.py`,
unchanged. Locks: `test_adrenwire` 4b and 12. `SKILLS-AD<n>` = a finding of this section.

**Located first.** A per-tape scan of `0x00CF` amounts: every stamp before `20260916T213125`
reproduces 4b's pinned multiset to the digit, so nothing drifted. `20260917T160915` and
`20260917T124314` carry no `0x00CF` at all. RB contributes 48 gains (13 at 25, seven at 0)
and RB2 26 (none at 25 — nobody swung — and six above it).

### 53.1 SKILLS-AD1 — CEIL is refuted; ROUND is the only family left — OBSERVED, 90 of 90

§34.C left two rounding families alive, `round(pct·k)` and `ceil(pct·k)`, and said one
light hit taken by an armed character would separate them. Solving for the `k` interval
over all 90 armed rows (32 old, 32 RB, 26 RB2):

```
floor(pct*k)   k in [1.280000, 1.012867)    EMPTY
round(pct*k)   k in [1.000000, 1.005429)    survives, and holds k = 1
ceil (pct*k)   k in [0.990210, 0.800000)    EMPTY
```

The two rows that close ceil: RB's 1.25 % hit (6 of 480) granted **1**, which ceil can only
reach with `k <= 0.8`; RB2's 59.58 % hit granted **60**, which needs `k > 0.990`. Round's
interval narrowed from `[1.0, 1.04)` and still contains 1 — the wire's own fraction,
unscaled. `pools.damage_units` implements round and was labelled provisional; it is now
right everywhere the corpus has looked, which is 0 % and 1.04 %..70.1 %. **Still NOT
OBSERVED:** a hit in (0, 0.5 %), and an exact .5 (half-up vs half-even).

### 53.2 SKILLS-AD2 — the denominator is the CURRENT maximum — OBSERVED, 11 of 11, rival 0 of 11

Every armed percentage is a whole number of points of **that row's own** property 42, which
now reads four maxima — 480, 408, 384, 336 (RB2's deaths took 480 to 408 to 336; what
made RB's 384 is unread) — where §34 had one. At 480 "one unit per 1 % of maximum" and "one
unit per 4.8 raw points" are the same number, and §34 said so. Against a moved maximum they
are not:

| maximum | points | units sent | round(% of current) | round(points / 4.8) |
|---|---|---|---|---|
| 408 | 286 | **70** | 70 | 60 |
| 408 | 140 | **34** | 34 | 29 |
| 336 | 101 (×3) | **30** | 30 | 21 |
| 336 | 50 | **15** | 15 | 10 |
| 336 | 45 | **13** | 13 | 9 |
| 384 | 39 | **10** | 10 | 8 |
| 384 | 31 | **8** | 8 | 6 |
| 384 | 7, 6 | **2**, **2** | 2, 2 | 1, 1 |

~~**Our server diverges here and it is recorded, not fixed:** both call sites compute
`pools.damage_units(dealt / float(agents.PLAYER_HEALTH))` while the damage word beside them
divides by `player_max_health(state)`. Under a death penalty or a Deep Wound the client is
told one fraction and granted the units of another. Open in `PLAN.md` §8.~~ **FIXED
2026-09-19, §53.6** — three sites divide by the current maximum. (The 384: it is 480 × 0.8
exactly, the size of a Deep Wound's reduction; arithmetic, not a read of the tape.)

### 53.3 SKILLS-AD3 — there is NO cap at 25 — OBSERVED, 6 of 6

`test_adrenwire` 4b read "no 207 exceeds 25 … 25 is a CEILING on one message". That is the
**strike** rule's ceiling stretched over the opcode. RB2 carries 30 ×3, 34, 60 and 70, each
in an unambiguous batch of one damage word and one gain, each `round(pct)`: the 60 is one
Lightning Orb on a stripped body (§50), 286 of 480. Nothing was summed — unlike JARIN's
three hero ticks (26, 29, 42), which are a strike plus a hit taken.

### 53.4 SKILLS-AD4 — a hit converted to NOTHING still gets its gain, and the gain carries 0 — OBSERVED, 7 of 7

RB's seven fully converted hits (§48.7: heal, strip, then a damage word of `+0.0`) are each
preceded by `0x00CF [25, 0]` in the gain's usual place in the batch. The seven zero-unit
gains and the seven zero-damage words are the same seven rows. So the gain is not sent
*because* something was gained: it rides every damage word to an adrenal bar and carries
`round(pct)`. This is the same shape as SLICE-F46's "a landed hit always gets its word".

`player_gains_adrenaline` returns on `units <= 0`, on the argument that such a message
"does nothing and … retail has no reason to produce". Retail produces it. The client's
arithmetic is unaffected (it adds 0 and, per `test_adrenwire` 13, repaints nothing), which
is why this is a recorded divergence rather than a defect. **What is NOT known** is whether
a zero gain re-arms retail's 25-second clear: every zero on RB sits inside a run of other
gains, so the tape cannot say. ~~That unknown is the reason it is not shipped.~~ (Shipped
2026-09-19 with the clock left untouched, §53.6.) It also turns
the (0, 0.5 %) prediction over: "no message" was round's prediction in §34.C; "a 207
carrying 0" is what this makes likelier. INFERRED until a row lands there.

### 53.5 What adrenjoin does not read — OBSERVED, 3 of 3, by hand

Three of RB's 35 sub-25 gains have no property-16/17 word in their batch. All three ride a
**property 55** word to the observer, `-0.0854167` (41 of 480), beside a `+` property-55 word
to the source (it reads as a life steal; INFERRED) — and all three grant **9** = `round(8.54)`. So property 55 damage
charges adrenaline too. `adrenjoin.DAMAGE_PROPS` does not include it, and must not be given
it naively: it takes `abs()`, and a positive property-55 word to self is a heal.

### 53.6 SHIPPED 2026-09-19 — AD2 at three sites, AD4's zero on the wire, the 55 rows in the census; what stays INFERRED

**AD2, the denominator.** `land_swing`'s enemy-swing site and `land_skill`'s hostile-skill
site now pass `dealt / player_max_health(state)` to `pools.damage_units` — the same number
the damage word beside each divides by. A **third site** did not exist before: retail's
gain rides property-55 damage too (§53.5), and `armour_ignoring_damage`'s player branch
now sends it, one message ahead of the 55 word. The batch on RB, re-read for this rung
(`aw_prop55` scratch over `tape.decode_all`, all three rows identical in shape):

```
0x009F [58, 104, 0]              the caster's skill-finished
0x00A0 [20, 25, 104, 258]        the cast named at the observer
0x0044 / 0x009F [7, ...]         (the animation and the health-loss int)
0x00CF [25, 9]                   the GAIN, round(41/480 = 8.54 %)
0x00A3 [55, 104, 104, +0.0854]   the steal's heal to the source
0x009F [10, 25, 143]
0x00A3 [55, 25, 104, -0.0854]    the damage word at the observer
0x001E [...]
```

So the gain precedes BOTH 55 words, 3 of 3 — the same gain-then-damage adjacency as
property 16's modal batch (test_adrenwire 7). Labels: **OBSERVED** for a hostile life
steal at the player; **INFERRED** for any other 55 word at the player (a hex punishing the
player's attack, a foe's adjacent damage), by AD4's mechanism — a gain rides every damage
word to an adrenal bar.

**AD4, the zero.** `player_gains_adrenaline` now sends `0x00CF [player, 0]` when
`damage_units` rounds to 0 — the seven converted hits (7 of 7) — and skips `grant`, so no
slot moves and the pool's `_last_combat` is not marked. **The clock half is the smaller
claim and is INFERRED, not measured**: retail's 25 s clears are measured from the last 207
on the wire (15 of 15), but every zero on RB sits inside a run of non-zero gains, so
whether a zero alone re-arms the clear has no witness. Left in `PLAN.md` §8. The sub-0.5 %
band sends a zero by the same code path; no armed row has ever landed there
(test_adrenwire's near miss is dark), so that is the prediction test_pools §11d states,
not a measurement.

**The census.** `adrenjoin.is_damage_to` files a property-55 word as a damage row only when
it names the observer as TARGET and its value is NEGATIVE — 55 is signed where 16/17 are
not, and the same batch carries the steal's `+` word to the source. With it the armed
population is **93 rows, 93 granted, round 93 of 93** (was 90); the three new rows are the
`9`s. `hits_landed` still counts 16/17 only: a 55 is not a weapon hit.

**Tests.** `test_pools.py` §11d (the zero goes out; it moves no slot and marks no clock;
the 11 % control grants and marks it) and §11d2 (a Deep Wound on the player, 100 → 80,
and 2 points where the two rules give 3 against 2: the 55 site and an enemy swing each
grant round of the damage word they ride with, the gain one message ahead), floor 128 →
132. `test_adrenwire.py` green at 77 with the joined rows; `test_agentlife`, `test_guards`,
`test_playerswing`, `test_mechanics`, `test_skilldamage`, `test_weapons` green.

**Not touched, and named so nobody re-derives them.** (1) `hero_pool_gain` still returns on
0 units — JARIN's tape has no converted hit on the hero, so the hero's zero is unread either
way. (2) This server declares `[42, max]` ahead of EVERY 55 word to the player
(`declare_max="always"`); RB's three player batches carry no 42 (0 of 3; the "declared
first, 3 of 3" in that function's docstring was measured on BODIES on the daggers tape). A
divergence spotted in passing, one rung's worth on its own. (3) The DARK-bar ruling
(§34.10) is unchanged: the zero goes to any bar, as every other gain does.

**What would refute this section.** A retail `0x00D0` clear landing 25.00 s after a zero
`0x00CF` with no non-zero gain between → the clock half is wrong and `grant`'s mark belongs
on the zero too. An armed hit in (0, 0.5 %) with no 207 in its batch → the band prediction
is wrong and the zero is specific to conversion.

## 54. SKILLS-DT — the description templates: `%str1%` is the SCALE slot, `%str2%` the BONUS slot, `%str3%` the DURATION slot; a referee over all 1,333 rows finds 0 slot conflicts and 1 hand-row conflict; and the coverage census — 54 modelled, 419 episodes, 815 nothing (2026-09-22)

**Status: MEASURED, and shipped as a tool with its lock; nothing is served from it, no
overlay is emitted, the server is untouched. The route's own step-3 gate FAILED: 341 of
the 1,265 slot-bearing rows (27 %) have every slot read by a server consumer (§54.4).**
DESKWORK-D4 steps 1–3 and the DESKWORK-Q7 census
([studies/deskwork/PLAN.md](../deskwork/PLAN.md) §3 D4, §4 Q7). Extractor:
`toolkit/clientscan/skilldesc.py` (`--mapping`, `--referee`, `--census`, `--hand`,
`--shift N` for the known-bad arm, `--row ID`). Lock: `toolkit/clientscan/test_skilldesc.py`,
85 checks with the vault, floor 40 bare. Build 38797, snapshot
`vault/client/2026-07-29_221c13772c7a`, the archive beside it. Reviewed the day it landed
(two reviewers, findings D4-R1..R12 and ENG-1..12) and corrected the same day; §54.9 lists
what changed, because the first version of this section overstated the served tier by a
factor of 1.7. `SKILLS-DT<n>` = a finding of this section. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Provenance, stated once.** A description is ArenaNet's authored text. This section quotes
none of it: what it carries is skill ids, slot indices, the record's own numbers (already in
`vault/content/skills.toml`), verdicts, and OUR label enum. The tool prints a template
window only from `--row` and `--residue`, as a tool over the owner's install, the way
`textrec.py`'s CLI prints a string. Skill NAMES below are the short proper nouns
`PLAN.md` §7 Q17 permits.

### 54.1 SKILLS-DT1 — the probe, reproduced to the row

`textrec.TextIndex` + `skilltable.parse_record` over the corpus `player_corpus` returns —
which is key-for-key the 1,333 of `vault/content/skills.toml` — **1,265 rows carry a
`%strN%` placeholder, 0 are unreadable; str1 1,090, str2 582, str3 685; 2,357 occurrences.**
The operator judge's and the orchestrator's counts, to the row. Two things neither probe
counted: **`%%` is the escaped literal percent sign** (424 occurrences in 372 rows — 250 of
them right after a slot, the spelling `%strN%%%` for a slotted percent; the "66%%" the survey
saw is Deep Freeze's constant printed as text; 166 rows print a literal digit-percent), and
the other markup is small: `[s]` the plural (940 occurrences in 822 rows),
`<c=@SkillDull>…</c>` (10), `[pl:"…"]` (16 in 13 rows). Thirty-three templates use one
index twice (the same number printed twice); no two corpus rows share a `description_id`,
though 29 groups of rows carry identical text.

### 54.2 SKILLS-DT2 — which slot is which field: MEASURED, and the natural order is WRONG

|  | field | offset | witness rows (id: endpoints, `skill_arguments`) |
|---|---|---|---|
| `%str1%` | **scale** | `+0x5C`/`+0x60` | Power Attack 322: 10..40, args = scale only, its ONE slot · Defy Pain 318: 90..300 · "To the Limit!" 316: 10..60 · Deep Freeze 234: 10..85 (a consistency row, not wiki-pinned) |
| `%str2%` | **bonus_scale** | `+0x64`/`+0x68` | Sever Artery 382: 5..25, args = bonus only, its ONE slot · Faintheartedness 135: 0..3 · Defy Pain 318: 1..10 · "To the Limit!" 316: 1..6 |
| `%str3%` | **duration** | `+0x44`/`+0x48` | Faintheartedness 135: 3..16 · Rush 319: 8..20 · Defy Pain 318: 20/20 · "To the Limit!" 316: 10..20 |

Every witness but Deep Freeze is a row whose slot is already pinned to the wiki by
`content/world.toml`'s hand rows or by §4's table, and each lands on the field the wiki
named; Deep Freeze (234) is in neither and is listed as a consistency row (args = scale
only, one slot, str1). The route text assumed no order and warned about "seconds"; the order
a reader WOULD assume — str1 = duration, the natural one — would have Power Attack print its
0-second duration as its damage.

**The theorem the artifact can refute (OBSERVED, all 1,333 rows).** Under this mapping,
**0 of the 2,357 slot occurrences point at a 0/0 field — whatever its bit says**, **0 reach
a duration sentinel** (≥ `0x10000`, §13), and every index is 1..3. The verdicts, over the
2,320 distinct (row, index) slots: 1,698 `AGREE_PROGRESSION` (bit set, endpoints differ),
481 `AGREE_FLAT` (equal, non-zero: a constant the client prints), 141 `INDETERMINATE`
(§54.3). **The known-bad arm**: shift the mapping one field along and 762 distinct slots
land on 0/0 fields (33 of them bit-set) and 12 on sentinels; shift it two (the natural
order) and it is 763 and 24; the hand rows' 51 AGREE (§54.5) collapse to 3 and 2, read from
the templates; and the count of enabled progressions no slot shows rises from **21** to
858 / 832. Three signals, one direction. **The theorem's reach, stated as a standing
weakness**: it can refute a slot only where some OTHER field of the same row is 0/0 — 1,264
of the 2,320 distinct slots; on the other 1,056 it is blind, and the label distribution is
the witness there (356 of those 359 str3 slots carry a time label; the three exceptions,
199 / 1950 / 2093, number a count or an energy cap stored in the duration field, which is a
use of the field, not a mapping violation).

**"seconds" is not the duration slot's word**, which is why the mapping is per index and
never inferred from the words: of 905 "second" slots, 682 are str3, **141 are str2 and 82
are str1** — a condition's duration lives in the bonus slot (Sever Artery's Bleeding 5..25)
or the scale slot (Jagged Strike's, `world.toml` 782). The survey's warning holds exactly.

**The 21 hidden progressions** (bit set, endpoints differ, no slot numbers them; all
listed by `--mapping`): 13 bonus, 5 scale, 3 duration — Riposte 387's bonus 1..10, Winter
462's bonus 1..16, Panic 52's bonus 10..82 among them. The record scales something the text
does not state as a number; nothing here reads them.

### 54.3 SKILLS-DT3 — the 141 INDETERMINATE slots are a CONTEST the desk cannot settle

§12 refuses the shape "bit clear, endpoints differ" (49 durations then; 23 scale + 74 bonus
+ 44 duration slot occurrences now), because no corpus apply witnesses what the client
does with it. **The templates DO number those slots** — 141 times — so the client prints
*something* there, and one hand row already says what: Glyph of Lesser Energy 200 (scale
10/18, args = 0) is numbered by `%str1%`, and its `verified` text records that the wiki
lists 10..18 as a progression. WIKI numbers come from the in-game display. So either the
client interpolates a bit-clear pair after all, or the wiki's progression is wrong for that
skill; the referee marks the 141 `INDETERMINATE`, never `AGREE`, and the module's own
comment carries the contest. **What settles it is a client run** (parked, deskwork §5): the
tooltip of one such skill read at two attribute ranks. Not a desk question.

### 54.4 SKILLS-DT4 — the label vocabulary, and the route's own fail condition measured

Our enum (`skilldesc.Label`, 50 values including `UNPARSED`) reads the words around each
slot after the markup is normalised: five elemental damages, `PLUS_DAMAGE` / `DAMAGE` /
`DAMAGE_REDUCTION`, `HEAL` / `MAX_HEALTH` / `HEALTH_REGEN` / `HEALTH_DEGEN` / `LIFE_STEAL`,
`ENERGY` / `ENERGY_LOSS`, `MOVE_SPEED_UP/DOWN`, `ATTACK_SPEED_UP/DOWN`, `RATE_PERCENT` (a
recharge, an expiry or adrenaline "N % faster" — not a body), `ARMOR`, `ARMOR_PENETRATION`,
`DURATION`, `CONDITION_DURATION` with the condition as detail, `DISABLE_DURATION`,
`LIFETIME`, `LEVEL`, `COUNT`, `CHANCE`, `PERCENT`, … and `UNPARSED`. **Every one of the
2,357 slots receives a label: 0 `UNPARSED` rows** — with the caveat that ~150 of them land
in the catch-alls (`COUNT` 62, `PERCENT` 32, `HEALTH` 27, `SECONDS` 16, `REDUCTION` 3), so
"100 % labelled" is a statement about OUR enum's reach and not about precision. Precision
was audited after review: every `MOVE_SPEED_*` slot now follows a movement verb (25 of 73
did not and were recharge / expiry rates; they are `RATE_PERCENT`: recharge 23, expiry 8,
adrenaline 2) and every `HEALTH_PERCENT` names health (4 of 20 were energy or damage
shares). By index the corpus reads as expected — str3 is `DURATION` 578 times,
`CONDITION_DURATION` 37, `LIFETIME` 46; str1 is `PLUS_DAMAGE` 156, `HEAL` 107, `DAMAGE` 84,
`LEVEL` 64, the five elements 25–36 each; str2 is `CONDITION_DURATION` 126, `ENERGY` 62,
`DAMAGE` 57, `HEAL` 47. All ten conditions are numbered somewhere (Bleeding 35, Burning 27,
Crippled 26, Weakness 26, Blind 25, Deep Wound 25, Cracked Armor 17, Dazed 14, Poison 14,
Disease 7). Eighteen templates give one index two different labels (476's str3 is
`DURATION` and `LIFETIME`; 951's str1 is a speed up and a speed down); `analyse()` lists
them as the classifier disagreeing with itself, never fitted.

**Two tiers, and the tier is a fact about CONSUMERS — per (label, slot INDEX, type_code),
not per label.** Every server reader of a `skill_effect` label reads ONE field, and most
read it on one family of types (`skilldesc.CONSUMERS`, read off the sites 2026-09-22):
`skill_damage` and `skill_heal` read `scale_means` at cast — str1, on a type outside
`effects.EFFECT_TYPES` (the one episode reader of a damage label is the preparation's arrow
bonus, type 19); `skill_condition` reads `bonus_scale_means` then `scale_means` on any type
and never the duration field; armour penetration is `bonus_scale_means` alone; the movement
means are read off OPEN EPISODES from either slot and attack speed from `scale_means` on an
open episode; `Energy` is `glyph_energy_amount`'s, reached only from a Glyph's episode;
`DURATION` is the episode machinery's, str3 on `EFFECT_TYPES`. Two labels a reader mentions
are NOT consumers of the label: `Energy loss` acts only as the Energy Feast pair with
`Heal per energy lost`, and `Health threshold %` reads a flat bonus below which an attack's
`+ Damage` doubles — a shape the parse cannot tell from a share of health (none of the 21
`HEALTH_PERCENT` slots is it). So a heal numbered by `%str2%`, a Hex's cold damage at
`%str1%`, an energy gain on a Spell: labelled, and read by nothing. `SERVED` is the row
whose every slot has its reader; `RECOGNISED` is labelled with at least one slot no reader
takes. Per row:

| tier | rows | of slot-bearing |
|---|---|---|
| SERVED — every slot read by a consumer for its label, index and type | **341** | **27 %** |
| RECOGNISED — every slot labelled, at least one with no reader | 924 | 73 % |
| UNPARSED | 0 | 0 |
| no slot | 68 | — |

**The route's own step-3 gate — "FAILS if fewer than half the slot-bearing templates land
in the server's label vocabulary" — FAILED: 27 %.** The first version of this section
tiered by label alone, counted 583 rows (46 %) and called it a near-miss; the reviewers
(D4-R1, ENG-1) re-tiered against what each consumer reads and it is 341 — not near. The
route's stated consequence is that "the label route is refuted for the residue and coverage
is per-skill work", and the measurement supports it more than the first version admitted:
the 924 recognised rows are held out by **91 distinct (label, slot, reason) keys**, the
largest being **a duration on a non-episode type 186** (a Shout's, a Signet's or a Spell's
"for N seconds", which opens no episode today), **untyped `DAMAGE` at str1 84**
(`SCALE_MEANS_DAMAGE` has the five elements and `+ Damage`, not the armour-ignoring plain
"N damage" GWW's "Damage" article describes), `ENERGY` at str2 61 and at str1 on a non-glyph
49, `DAMAGE` at str2 57, `HEAL` at str2 47 and on an episode type 28, `LEVEL` 64, `LIFETIME`
46, `CONDITION_DURATION` at str3 35, `PLUS_DAMAGE` at str2 34. 564 of the 924 have a single
blocker, spread across those keys.

**A PROPOSAL, labelled as one, for the owner and not a finding:** two consumers — the plain
untyped damage, and a duration episode for the non-episode families — would move the rows
whose EVERY blocker is one of those two, and that is **115 rows, not the ~325 the first
version estimated** by adding per-label counts (341 → 456, 36 %; still under the gate). The
next six single-blocker consumers (`ENERGY` at str2, `ENERGY` on non-glyphs, `DAMAGE` at
str2, `HEAL` at str2, `CONDITION_DURATION` at str3, `PLUS_DAMAGE` at str2) would move another
~130. Whether that is worth building before the residue is treated per skill is the owner's
call, and step 4 (an overlay from the SERVED tier) waits on it — the D4 bullet in `PLAN.md`
§8.1 says so.

**The row classifier** (an enum of flags per row, exporting no text): IF 468, WHEN 241,
FOR_EACH 117, WHILE 94, EXCEPTION 23, CHANCE 68, LITERAL_PERCENT 166; area wording —
ADJACENT 138, NEARBY 94, IN_THE_AREA 53, EARSHOT 84, TOUCH 35; ALL_FOES 172, ALL_ALLIES 83,
TARGET_FOE 404, TARGET_ALLY 152. D6's "all foes in this area" rows are the union of
IN_THE_AREA and ALL_FOES: 204 (21 carry both). LITERAL_PERCENT's first pattern matched the
`1%` closing `%str1%` and was up on all 1,278 slot-bearing rows — a flag that could not stay
down, caught in the fix pass and by neither reviewer.

### 54.5 SKILLS-DT5 — the 54 hand rows as the second witness, and what they got wrong

`referee_hand_row` takes the FIELD a hand row names (`scale_means` = the scale field), the
index the mapping gives that field, and compares the hand label with the label parsed at
that index, by family (`skilldesc.HAND_FAMILY`; "Heal" / "Healing" / "Maximum heal" are one
family, "+ Damage" accepts "+N ⟨element⟩ damage" because Spear of Lightning 1551's own
`verified` text records the wiki variable as `+ Lightning damage`).
**51 AGREE, 1 CONFLICT, 2 NOT COMPARABLE ("Resurrect", "none"), 14 NO_SLOT.** Because the
verdict is read from the template, this is the second witness for §54.2's mapping that the
known-bad arm can fail — under `shifted()` the 51 AGREE become 3 (shift 2: 2), the rest
NO_SLOT and CONFLICT. (The first version short-circuited to a `MAPPING_CONFLICT` computed
from the mapping alone and counted "66 of 66" as evidence; that check could not fail on
data — D4-R4 / ENG-3.)

- **The conflict is real: Battle Rage 317, `scale_means = "Duration"`.** Its scale slot is a
  flat 33 with the bit clear, numbered by `%str1%` as its movement speed (`MOVE_SPEED_UP`);
  the duration 5..20 is str3. Nothing in the server compares `scale_means` against
  `"Duration"` (grep), so the row is inert rather than wrong-acting. **Scourge Sacrifice 253
  is the same label twice wrong**: `scale_means = "Duration"` on a flat 100 the text never
  states (a `LITERAL_MISS`, below), with its duration 8..20 on str3.
- **Hamstring 320 labels the WRONG slot, and the server inflicts nothing for it today.**
  `scale_means = "Crippled duration"`; the client's row has args = bonus only, scale 0/0,
  bonus 3..15, and the template numbers the Crippled duration with `%str2%`. The row's own
  `verified` says "args = 4 (bonus only); the scale slot is 0->0" and still put the label on
  `scale_means`. And "Crippled duration" is not in `effects.CONDITION_BY_NAME` ("Crippled"
  is), so `skill_condition` finds no condition on either slot. Two fixes owed to
  `content/world.toml` — `bonus_scale_means = "Crippled"` — with `test_skilldamage` /
  `test_mechanics` as the lock; `test_skilldamage.py:102-111` pins the current labels of
  253 and 320 by name and `test_skilldesc` pins 317 as the one conflict, so all three move
  in the same commit as the rows; NOT done in this pass (content and server untouched by
  design). Listed here, not fitted around.
- **The 14 NO_SLOT rows are the flat-constant pattern, and the text proves it**: 12 of the
  14 named slots are bit-clear or bit-set FLAT values that appear as a literal number in the
  template (Faintheartedness' 50, Rush's 25, Bonetti's Defense 380's 75 and 5, Final Thrust
  385's 50, the 20 of both armour-penetration rows). The other two are Hamstring's 0/0 and
  Scourge Sacrifice's unstated 100.
- **The Deep Wound trio** (Dismember 337, Executioner's Strike 352, Gash 384) name the
  condition at the head of the sentence and number it at the tail; a 48-character window
  read them as plain `DURATION` and the referee said CONFLICT — correctly, against a parser
  that was wrong. The classifier now reads the slot's own sentence (bounded at the previous
  full stop, and guarded when the verb right before "for" is "hexed"/"enchanted"/…, Ash
  Blast 1085). 37 of the 38 str3 condition durations were right before the guard; the 38th
  was the guard's case.

**The literal check, corpus-wide (a census, not a verdict).** Of the 358 flat, non-zero,
non-sentinel fields the template does NOT number with a slot, **255 are printed as a literal
number in the text and 103 are constants the text never states.** Under the shifted mapping
the 255 fall to 95 — a fourth signal for §54.2.

### 54.6 SKILLS-DT6 — the PvP / PvE join, over the full 3,443-row table

`linked_id` (`+0x2C`) is 3443 — the table's own length, its "none" — on 3,109 rows. **177
rows link INTO the player corpus: all 177 are `pvp_only`, family 0, outside the corpus, and
every one carries a name ending in the PvP marker; 0 of 177 share their original's
`description_id`** — each PvP twin has its own template. 156 corpus rows link out to a twin.
So the referee's join is each corpus id to ITS OWN record, `linked_id` is never followed for
a number, and no corpus template is a PvP text over PvE numbers. `test_skilldesc` §2 pins
all three counts.

### 54.7 SKILLS-DT7 — the coverage census (DESKWORK-Q7): what the server resolves today

Grades, computable from `content.load()` + `effects` alone (`skilldesc.census`): **modelled**
= carries a `skill_effect` row (today's `sandbox.modelled_skills`; it does NOT mean "acts" —
at least four of the 54 act on nothing through their row: 320's label is outside the
condition vocabulary, 317's and 253's `Duration` is compared by nothing, 321's is `none`);
**episode-only** = `type_code` in `effects.EFFECT_TYPES` and `resolve_duration` resolves at
rank 12 (icon, timer, expiry — no numbers); **episode-refused** = in `EFFECT_TYPES` but the
duration refuses (§12/§13 shapes); **nothing** = the cast and its animation. The sandbox's
"modelled" mark could take these grades later; it is not wired here. Type names are the
client's own (§35), resolved at run time.

| type | client's word | rows | modelled | episode | ep-refused | nothing | with slot | SERVED | RECOG |
|---|---|---|---|---|---|---|---|---|---|
| 3 | Stance | 76 | 5 | 69 | 2 | 0 | 74 | 30 | 44 |
| 4 | Hex Spell | 151 | 3 | 139 | 9 | 0 | 151 | 34 | 117 |
| 5 | Spell | 287 | 11 | 0 | 0 | **276** | 267 | 102 | 165 |
| 6 | Enchantment Spell | 227 | 3 | 192 | 32 | 0 | 219 | 40 | 179 |
| 7 | Signet | 66 | 2 | 0 | 0 | 64 | 55 | 9 | 46 |
| 9 | Well Spell | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 8 |
| 10 | Skill | 55 | 1 | 0 | 0 | 54 | 49 | 6 | 43 |
| 11 | Ward Spell | 12 | 0 | 0 | 0 | 12 | 12 | 0 | 12 |
| 12 | Glyph | 10 | 1 | 8 | 1 | 0 | 9 | 1 | 8 |
| 14 | (weapon attacks; §35) | 199 | **23** | 0 | 0 | 176 | 182 | 98 | 84 |
| 15 | Shout | 52 | 2 | 0 | 0 | 50 | 49 | 1 | 48 |
| 16 | Skill (PvE) | 21 | 1 | 0 | 0 | 20 | 21 | 0 | 21 |
| 19 | Preparation | 14 | 2 | 11 | 1 | 0 | 14 | 10 | 4 |
| 20 | Pet Attack | 14 | 0 | 0 | 0 | 14 | 14 | 6 | 8 |
| 21 | Trap | 12 | 0 | 0 | 0 | 12 | 12 | 4 | 8 |
| 22 | (global skill; §35) | 49 | 0 | 0 | 0 | 49 | 49 | 0 | 49 |
| 24 | Item Spell | 17 | 0 | 0 | 0 | 17 | 17 | 0 | 17 |
| 25 | Weapon Spell | 22 | 0 | 0 | 0 | 22 | 22 | 0 | 22 |
| 26 | Form | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 8 |
| 27 | Chant | 21 | 0 | 0 | 0 | 21 | 21 | 0 | 21 |
| 28 | Echo | 12 | 0 | 0 | 0 | 12 | 12 | 0 | 12 |
| **all** | | **1,333** | **54** | **419** | **45** | **815** | **1,265** | **341** | **924** |

Read it as the route asked: **1,333 rows; 54 carry a row (at least 4 of them inert); 419
more show an icon and a timer with no numbers behind them; 45 would open an episode and
refuse its duration; 815 do nothing past the cast.** The 341 SERVED rows are where a label
overlay (step 4) could act with the consumers that exist — 102 Spells, 98 attacks, 40
enchantments, 34 hexes, 30 stances — and the by-type column says which consumer each family
waits on: type 22 / 24–28 wait on step 6's effect types (0 served, 0 episodes), Signets and
Shouts on a non-episode duration, the enchantments and hexes mostly on a reader for a heal
or a damage that rides an episode. The survey's estimate "300–400 skills act" after step 4
is reachable only at its floor and only if every served row were emitted: 54 + 341 = 395
before step 4's own type gate ("A LABEL DOES NOT SAY WHEN") removes any.

### 54.8 What this refutes or changes in the route, and what is next

- **Refuted: the natural slot order.** The route text assumed no order and warned about
  "seconds" (a warning §54.2 quantifies: 141 str2 and 82 str1 "second" slots); the order a
  reader would assume is refuted by the theorem's known-bad arm (763 slots on 0/0 fields).
- **The step-3 gate FAILED, at 27 %** (§54.4). The route's consequence — the label route is
  refuted for the residue, coverage is per-skill work — stands on the measurement: 91
  blocking keys, and the two largest consumers would move 115 rows. §54.4 carries a
  separate, labelled PROPOSAL (bulk consumers first) for the owner; step 4 waits on that
  decision. (The first version called the gate "a near-miss (46 %) on the served tier and a
  pass (100 %) on the label tier"; the 100 % is our enum's reach, ~150 slots of it
  catch-alls, and the 46 % was a label-only count — §54.9.)
- **Changed: the licence lines.** `PLAN.md` §1's table row and A6 said gw-skilldata is MIT;
  the critic said GFDL / CC BY-NC-SA. From primary sources (the repository's `LICENSE`,
  GitHub's licence API, SPDX `MIT`; its README's own "Licensing" section) BOTH are right
  about different things: the repository is MIT, the DATA carries the source wikis'
  licences — GFDL (GWW), CC BY-NC-SA 2.5 (GuildWiki), CC BY-NC-SA 2.0 FR (GWiki). Corrected
  on both lines. No mirror of it exists under `vault/mirrors/`. Not used by anything; no
  §6.1 row owed.
- **Owed to content, next pass (not this one):** Hamstring 320 → `bonus_scale_means =
  "Crippled"`; Battle Rage 317 and Scourge Sacrifice 253 → drop `scale_means = "Duration"`
  (inert today). Each with `test_skilldamage` (its :102-111 pins move in the same commit)
  and `test_mechanics` re-run, and `test_skilldesc`'s pin of 317 as the one conflict.
  **DONE 2026-09-23** (`73eb8320`; §55's status paragraph).
- **Open, client run:** the 141 INDETERMINATE slots (§54.3) — one tooltip at two ranks.
- **Next in the route, CONDITIONAL on the owner's answer to the gate:** step 4, the overlay
  — `vault/content/skill_labels.toml` from the SERVED tier (341 rows, per label / index /
  type), `tier = 'label'`, merged UNDER the 54 hand rows — or the per-skill residue the
  route's own text prescribes on a failed gate. **ANSWERED 2026-09-23: option 1, the plain
  rows only — §55.**

**What would refute this section.** A client tooltip printing a `%str1%` number that is not
the row's scale slot at that rank (the mapping is wrong); a slot occurrence under the
measured mapping landing on a 0/0 field on a later build (the theorem is build-specific and
`test_skilldesc` will say so); a hand row's `verified` text naming a slot the parser
contradicts where the parser is right on inspection (the family table is wrong, not the
row); a consumer site reading a field `skilldesc.CONSUMERS` does not list (the tier is
stale — the table names each site so a reader can check it against the source).

### 54.9 SKILLS-DT8 — what the same-day review corrected

Two reviewers (an evidence refuter re-deriving every number from the snapshot, and an
engineering reviewer breaking the test's arms in memory) read the first version; the fix
pass took every finding whose evidence held, and none failed to reproduce. What changed, so
a reader of the first commit (`5ec8e1d5`) knows what not to trust: **(a)** the served tier
was per label and said 583 / 46 %; per (label, index, type) it is 341 / 27 % and the gate
FAILED (D4-R1, ENG-1); **(b)** the hand-row known-bad arm returned `MAPPING_CONFLICT` from
the mapping alone — a check that could not fail — and now reads the template (51 AGREE → 3)
(D4-R4, ENG-3); **(c)** a bit-set 0/0 field was graded `AGREE_FLAT` against the docstring,
hiding 33 empty-field landings per arm (D4-R5, ENG-8); **(d)** the literal-check fixture in
the test was Rush's whole template after normalisation, and two classifier phrases were
verbatim fragments — all replaced with our own sentences (D4-R2, ENG-11); **(e)** "N % faster"
with no movement verb was a movement speed (25 slots, 13 of the rows SERVED) and "N % of
that …" a health share — now `RATE_PERCENT`, and only health names `HEALTH_PERCENT` (ENG-2,
D4-R8); **(f)** the test skipped its corpus section on any exception and passed a simulated
loader defect at the bare floor — it skips on `pinned.find`'s refusal alone (ENG-4);
**(g)** numbers: 905 "second" slots not 872, 50 enum values not 52, `%%` 424 occurrences in
372 rows, IN_THE_AREA ∪ ALL_FOES 204 not 53 + 172, Deep Freeze not wiki-pinned, the
theorem's reach 1,264 of 2,320, the "~325 rows" two consumers would move is 115 (D4-R7 /
R9 / R10 / R11 / R12, ENG-5); **(h)** the census's "54 act" is "54 carry a row, at least 4
inert" (D4-R6); **(i)** same-index self-conflicts (18) and unreadable descriptions (0) are
counted, `census` catches `EffectError` only (ENG-9, ENG-10); **(j)** the content-side pins
in the test are derived from the rows loaded (ENG-7) and the served bound sits below the
half-mark (ENG-6). Found in the fix pass and by neither review: `LITERAL_PERCENT` was raised
on every slot-bearing row (§54.4), and `normalise()` let a slot's closing `%` pair with the
escape after it — harmless on this corpus by ArenaNet's spelling alone (§54.1), fenced now.

## 55. SKILLS-LT — the label tier: 47 of the 131 plain SERVED skills shipped as generated `tier = "label"` rows under the hand rows; 84 excluded by the step-4 gate, each by reason; `--no-skill-labels` reverts (2026-09-23; the fix pass of the same day took the count from 59 to 47, §55.7)

**Status: SHIPPED, behind a revert flag, as a MARKED tier.** DESKWORK-D4 step 4 on the
owner's decision of 2026-09-23 (option 1): the step-3 gate having FAILED at 27 % (§54.4),
ship the PLAIN SERVED rows now and treat the residue per skill. Extractor:
`toolkit/clientscan/skilldesc.py --emit-labels` → `vault/content/skill_labels.toml` (the
vault, never git). Locks: `toolkit/clientscan/test_skilldesc.py` §1b + §3 (bare floor 72,
138 with the vault), `toolkit/test_content.py` (floor 52 bare, 55 with the vault),
`toolkit/authsrv/test_skilldamage.py` §14 (80 with the overlay), `toolkit/harness/test_sandbox.py`
§5 (111), `tools/orchestrator/orchestrator.py --smoke` (23, two of them the grade marks). Build
38797, snapshot `vault/client/2026-07-29_221c13772c7a`. `SKILLS-LT<n>` = a finding of this
section; convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md). The three
content fixes §54.8 owed landed the same day, first (`73eb8320`): Hamstring 320 →
`bonus_scale_means = "Crippled"`, and Battle Rage 317's and Scourge Sacrifice 253's inert
`scale_means = "Duration"` dropped; §54.5's one CONFLICT and two unmatched NO_SLOT rows are
gone, and Hamstring inflicts Crippled 3..15 s where it inflicted nothing. **The first pass
shipped 59 rows; two reviewers read all 59 templates and refuted nine of them (§55.7), and
the fix pass turned each refutation into a gate rule with a known-bad arm. 47 ship.**

**Provenance, stated once.** A description is ArenaNet's authored text and none of it leaves
the parse. What the overlay carries is a skill id, the record's `type_code`, a means string
from the hand rows' own vocabulary (`Fire damage`, `Poison`, `+ Damage`, …), `tier =
"label"`, a `tier_detail` list of OUR tokens, and client-table provenance whose `verified`
is a list of `{slot, field, lo, hi, verdict, label[, detail]}` — numbers and enum names.
`skilldesc.OVERLAY_VOCABULARY` is the closed set of every string the file may hold, and
`skilldesc.text_leak()` names any string outside it; the test asserts the emitted file
leaks nothing and that no string value is longer than the vocabulary's longest token (31,
the extractor path). The header names the exe, its build (from the image's sha256), the
`Gw.dat` the templates were read from and a sha256 over the corpus's templates in id order
(`skilldesc.template_digest`) — a measurement of the text, so a drift between builds shows.
This section names skills by id; the names used are the short proper nouns `PLAN.md` §7
Q17 permits and are already in §54.

### 55.1 SKILLS-LT1 — the set, defined in code and reproduced

`skilldesc.plain_served(report)`: tier SERVED and none of `COMPOUND_FLAGS` — IF, WHEN,
FOR_EACH, WHILE, EXCEPTION, CHANCE — the six wordings a label would drop, making the skill
fire unconditionally. **341 SERVED = 131 plain + 210 conditional** (IF 154, WHEN 37, FOR_EACH
17, WHILE 9, CHANCE 7, EXCEPTION 6), the orchestrator's count to the row (OBSERVED, build
38797). Of the 131, **10 already carry a hand row** (160, 170, 186, 229, 252, 253, 281, 319,
431, 433) and stay hand rows; 121 are candidates, by type: Spell 49, Hex 22, Enchantment 18,
Stance 12, attack 7, Signet 4, Skill 4, Preparation 2, pet attack 1, Glyph 1, Shout 1. The
fix pass added flags the GATE reads (`AREA_NEAR`, `UNMODELLED_CLASS`, the `CLAUSE_*` family,
`SPEED_MOVE`) and none of them is a COMPOUND flag: the owner's 131 stay 131 (`test_skilldesc`
§1b pins the disjointness).

### 55.2 SKILLS-LT2 — the gate: "A LABEL DOES NOT SAY WHEN", applied to every consumer

The tier (§54.4) says a consumer EXISTS for a (label, index, type); the step-4 gate
(`skilldesc.build_label_row`) asks whether that consumer acting at THIS skill's cast does
what retail does. The rule for the pass: a row the server would **OVER-apply** — do
something retail would not — is **excluded with a reason**; one it would **UNDER-apply**
ships with the shortfall named in `tier_detail` and counted. Every exclusion is written
into the overlay's header by id. The rulings, each read off the consumer's own code and
the record's own bytes (the template windows were read as a tool over the owner's install,
`--row`, to decide; none is carried); the last four rows are the fix pass's (§55.7):

| reason | rows | ids | why the server would over-apply |
|---|---|---|---|
| `HAND_ROW` | 10 | (above) | a hand row exists; the tier sits under it (§55.4) — the emitter skips them and the load rule guarantees it |
| `DURATION_ONLY` | 41 | 13 16 31 35 56 74 76 129 136 137 157 169 173 184 208 210 218 245 267 273 310 349 371 764 802 804 811 815 859 883 928 978 1096 1517 1542 1640 1738 2005 2063 2137 2237 | every slot is the episode's own duration, which `effects.resolve_duration` reads from the skills table with no label; a `skill_effect` row would carry NO field and would upgrade the skill from "episode-only" to "modelled" for nothing |
| `CONDITION_ON_EPISODE` | 6 | 113 435 926 1041 1997 2136 | the condition is what the EPISODE does later — 435's arrows poison on hit (a Preparation), 926's dagger attacks bleed (an Enchantment), 1997's ally's melee weakens, 113's area diseases those who strike in melee, 1041's and 2136's stances blind adjacent foes — and `skill_condition` reads any type at the cast, on the cast's target. The rule `skill_damage` already applies to damage on an episode type, applied to conditions |
| `PET_ATTACK` | 1 | 441 | type 20; no pet is modelled and the bonus rides a pet's swing |
| `RECIPIENT_NOT_A_FOE` | 11 | 97 183 188 769 770 840 917 1113 1364 1468 2212 | an at-cast damage or condition acts on the cast's TARGET (the player path: `if inflicted and target`; the body path: `_tid`), and the record's target byte says the target is the caster (0: 97 183 188 840 1113 1364 2212 — self-centred areas and 1364's own Bleeding), unresolved (1: 769 917 1468 — `effects.TARGET_KINDS` has no entry; 1468's conditions ride a later attack besides) or another ally (4: 770, whose Crippled is on the foes around the ally). The server would act on the SELECTED agent at any range, or on the ally |
| `RECIPIENT_NOT_AN_ALLY` | 3 | 918 1032 1354 | heals whose target byte is 1: `cast_recipient`'s fall-through hands an unresolved byte to the selected target, a foe included |
| `PERCENT_SLOT` | 1 | 292 | the slot is printed with a literal `%` (`%str1%%%` in the corpus's spelling) and the parse labelled it HEAL: retail heals N % of the health the caster gave up, the row would heal N Health and charge no sacrifice (LT-R5). Rule: a `%` slot ships only under a label the consumers read as a percent (`PERCENT_LABELS`: armour penetration, the four speeds); `analyse()` now records `percent` per slot |
| `CHAIN_REQUIREMENT` | 3 | 784 973 1033 | the record's `combo_req` (must follow a lead / off-hand / dual) on a NON-attack type: DAGGERS-B5's chain gate at the E5 runs inside `if target and _is_attack_skill(...)`, so a Spell's or a Skill's condition and standalone damage would land whatever the chain says (LT-R4). On an attack the gate exists and the row ships |
| `UNMODELLED_CLASS` | 4 | 96 106 2051 2100 | the recipient or the prerequisite is an object the server does not have: 2051's and 2100's heal belongs to the spirits the caster controls, 96 needs a corpse exploited, 106 inflicts on a fleshy foe only (LT-R2, R6, R10). Rule: the `UNMODELLED_CLASS` flag — spirits (not `non-spirit`), minions, a pet, a corpse, `exploit`, `fleshy` — excludes. Placed after the target-byte rules so 97 917 918 1468, which both refuse, keep their byte reason |
| `HEAL_RECIPIENT_CLASS` | 4 | 287 943 1262 2221 | a SELF-targeted heal (byte 0) whose text names a CLASS of recipients — adjacent creatures, the party: `cast_recipient` places it on the caster and nobody else, and only the text says whether the caster is in the class. 1262 excludes the caster outright (LT-R1); 943 heals only the members relieved of Burning (LT-R3); **287 and 2221 include the caster and would only be under-applied, but the parse cannot tell them from the other two, so the rule takes all four** (Refuse to guess). A caster-centred party heal is the residue for the four |

Foe bytes are 5 and 16 (`authsrv.AREA_TARGET_BYTE`); heal bytes 0, 3, 4 (self, ally, other
ally — what `cast_recipient` places). A damage label on a Preparation (434) is NOT
target-gated: its consumer is `swing_preparation_bonus`, riding the caster's own arrows.
`SELF_CONFLICT` (one index, two labels) is a rule too; it caught nothing in the plain set.
`check_label_rows` re-checks the set against the report (and, given the records, against
`combo_req`), so a percent slot, an unmodelled class or a chain requirement forced past the
gate is named — `test_skilldesc` §1b on synthetic rows and §3 on 292, 96 and 784.

**Excluded ≠ refuted.** These 74 client-side exclusions are the FIRST per-skill targets:
each names the machinery it waits on (a caster-centred area for byte 0/1 and for the four
class heals, a resolution of byte 1, a condition rider on episodes, a chain gate for
non-attacks, a percent-of-loss heal, a pet, spirits, corpses, fleshiness), and the wording is
plain — nothing here is the conditional residue.

### 55.3 SKILLS-LT3 — what ships: 47 rows, and what the server does LESS of

**47 = 131 − 10 − 74**, by type: Spell 26, attack 7, Stance 4, Hex 3, Signet 3, Skill 3,
Preparation 1, Enchantment 0 (all 18 plain Enchantments were duration-only or
condition-riders; the shipped Hexes are 1044's and 1652's snares and 1996's attack slow, the
Stances 831, 1043, 1404 and 1762 with their speeds). Means, as the consumers read them:
`Heal` 10 (on byte 3 or 4 — every byte-0 heal on a class is out), `+ Damage` 8, `Fire
damage` 5, `Lightning damage` 5, `Earth damage` 2, `Cold damage` 1, `Holy damage` 1;
conditions on the scale slot 4 (Crippled 2, Bleeding, Dazed) and on the bonus slot 9
(Weakness 4, Blind 3, Burning 2); the speeds 9 (attack up 3, attack down 1, movement up 2,
movement down 3). Seven rows carry two means: 831 (attack speed + movement speed), 1404
(attack speed + snare), and 167, 189, 191, 224, 228 (damage + a condition).

**Marked under-applications** (`tier_detail`; every token in `skilldesc.DETAILS`; counted by
`test_skilldesc` §3; 36 of the 47 rows carry at least one, and the 11 that carry none — 117
191 220 286 293 959 1043 1120 1404 1686 1762 — are single-clause templates: a foe's condition
or damage, a target ally's heal, a stance's speeds):

- `AREA_BURST` **3** — 187 189 1086: byte-16 Spells with standalone damage, no projectile of
  their own and no duration — `spell_burst`'s WHOLE predicate (studies/weapons 40), mirrored
  in the gate and checked row by row against the server's own function in `test_skilldamage`
  §14. Not under-applied; marked so a reader knows which machinery it rides. **Correction
  (ENG-2, LT-R7):** the first pass marked 192 and 197 `AREA_BURST` too; both carry a duration
  (9 / 10 s) and `spell_burst` refuses a duration, so the server deals one hit, once, to one
  target. They are `AREA_ONE_TARGET` + `DURATION_UNMODELLED`.
- `AREA_ONE_TARGET` **20** — area wording the server reaches ONE recipient of: 105 118 131 167
  192 197 223 228 231 294 330 353 424 434 985 992 1118 1664 2107 3425 — the adjacent attacks
  (330 353 992 2107 3425: `adjacent_damage` is a hand opt-in and a different mechanic), the
  areas over time (167 192 197), "up to two other foes near your target" (223 1664, the new
  `AREA_NEAR` flag; 105's three targets), 131's and 294's Signets, 228's shockwave, 118's
  and 985's area conditions, 424's and 231's touch wording, 1118's party gain, 434's arrow
  splash.
- `DURATION_UNMODELLED` **7** — 105 167 192 197 228 424 799: a non-episode record whose
  duration field is not zero. The at-cast path reads the scale and bonus slots and never the
  duration, so an area over time ticks once (167 192 197), and whatever else the field times
  (105's flight, 228's 3 s, 424's and 799's 3..10 / 3..9 beside their condition slot) does not
  run. The mark can over-state — 424's and 799's timed thing may be the condition the bonus
  slot already carries — and a mark that over-states costs nothing.
- `CONDITION_BIT_CLEAR_REFUSED` **1** — 167's Blind 10/10 sits on a bonus slot whose bit is
  clear; `skill_condition` reads only enabled progressions (`skill_scale_value` raises), so
  the damage lands and the Blind does not. The label is right and inert; a flat-constant
  reader in `skill_condition` is the fix, not the row. (1033's Deep Wound was the second;
  1033 is out on its chain requirement, so `INDETERMINATE_SLOT` is 0 this pass.)
- `CONDITION_UNNUMBERED` **1** — 228 names Cracked Armor beside its numbered Weakness; no
  slot numbers it and no field carries it (`analyse()`'s `conditions_named` minus the slots').
- `LITERAL_DROPPED` **5** — 223 224 228 231 1664: a constant printed in the text (their 25 %
  armour penetration) that no slot carries and no field reads (`FLAG_LITERAL_PERCENT`).
- `CHAIN_STEP_NOT_ADVANCED` **1** — 974 "counts as an off-hand attack" on a Skill: the chain
  advances inside the attack branch only, so its Crippled lands and the chain does not move.
- **The dropped clauses, by kind** (`CLAUSE_*`, raised by wording; the first pass listed five of
  these in prose as "the standing weakness" and the fix pass made them marks): `CLAUSE_KNOCKDOWN`
  **6** (187 192 231 294 1086 3425 — a label row carries no `knocks_down`), `CLAUSE_SHADOW_STEP`
  **4** (799 1044 1652 2420), `CLAUSE_INTERRUPT` **2** (228, 434's Choking Gas; "easily
  interrupted" on 959 is a property of the cast, not a clause, and is not raised),
  `CLAUSE_REMOVAL` **2** (941, 1126: the cure beside the heal), `CLAUSE_ALSO_CASTER` **2**
  (1126 2420: "you and that ally"), `CLAUSE_DISABLE` **1** (1118), `CLAUSE_DOUBLE_DAMAGE` **1**
  (831), `CLAUSE_RANGE` **4** (407 958 985 1192: "half the normal range"), and 1996's one slot
  that slows movement, attacks and casting together — read as attack speed, the other two
  marked `CLAUSE_MOVE_SPEED` (a move clause with no MOVE_SPEED label) and `CLAUSE_CAST_SPEED`.

**Corrections to the first pass's prose (LT-R8):** 167 is NOT "one foe" — it is an area near
a location struck every second for 5 s (now `AREA_NEAR` + `AREA_ONE_TARGET` +
`DURATION_UNMODELLED`); 231 does NOT exhaust its caster — its unmodelled clauses are a
knock-down and 25 % penetration, both now marked.

**The standing weakness, restated smaller.** "Plain" is measured by OUR flags, and the marks
are measured by our patterns. A clause with no slot, no conditional word and no pattern in
`FLAG_PATTERNS` is still invisible; after the fix pass the reviewers' census of the shipped
templates found none, but the census is of 47 rows on one build.

### 55.4 SKILLS-LT4 — the plumbing: one path, a tier rule, a flag, a grade

- **No second path.** A label row resolves through `skill_damage`, `skill_heal`,
  `skill_condition` and the episode terms exactly as a hand row does: `test_skilldamage`
  §14 puts 187 through `skill_damage` (7 at rank 0, 112 at rank 15, "standalone") and 220
  through `skill_condition` (Blind 479 for 3 s / 8 s; 784 was the example until its chain
  requirement excluded it) and then drops the tier and watches both resolve to None with
  Holy Strike, Sever Artery and Hamstring's 54.8 fix untouched.
- **The tier sits UNDER everything** (`content.py` WHERE ROWS LIVE): a `tier = "label"` row
  never replaces a row without that tier, whichever layer either came from — the vault is
  merged over the repo, and this is the one exception, by TIER rather than by layer.
  `test_content` proves a label row keyed on a hand id LOSES and, as the known-bad arm,
  that the plain update this merge was until today lets it win. **The tier values are a
  closed set** (`content.TIERS`, ENG-6): a near-miss spelling (`Label`, `labels`, `label `)
  would have loaded as a hand row, beaten the real one and survived the flag; it is refused
  at load, and `test_content` proves the refusal on all three. (A client-table row with NO
  tier is a hand row — world.toml's 346 — so the other direction is not a rule.)
- **The log names the tier.** At the player's E5 and at a body's landing:
  `resolves through a LABEL-tier row (<detail>) -- parsed from the client's template, not
  hand-verified`. `test_skilldamage` §14 captures the line for 187, its silence for 312, and
  source-locks both call sites. **`--no-skill-labels`** drops the tier at startup
  (`World.drop_tier`, in `main()` before `srv.listen`; §14 parses the flag and locks the
  order) — the consumers then see the HAND rows alone, **including the 54.8 hand fixes of the
  same day** (the first pass's help text said "the server as it was until 2026-09-23", which
  Hamstring's Crippled refutes; reworded). The dead `SKILL_LABELS` global is gone.
- **The grade.** `sandbox.modelled_skills` is the HAND rows only; `label_skills` the tier;
  `sandbox.LABEL_TIER` is `content.LABEL_TIER` (one definition); the orchestrator marks `*`
  and `~label`, so nothing it shows as modelled is a label row (the fidelity judge's
  condition on step 4), and its `--smoke` now asserts a hand row ends ` *`, a label row
  ` ~label`, and "modelled only" shows exactly the union (54 + 47). `skilldesc.census`
  grades a label row `label-only`, never `modelled`: the census today reads 54 modelled, 47
  label-only, 411 episode-only, 45 refused, 776 nothing.

### 55.5 Regeneration, and the owed client confirmation (a runsheet, not a run)

```
python toolkit/clientscan/skilltable.py --emit-content   # vault/content/skills.toml FIRST, when the pin moves
python toolkit/clientscan/skilldesc.py --emit-labels     # -> vault/content/skill_labels.toml
python toolkit/clientscan/test_skilldesc.py              # the on-disk overlay must equal a fresh emit
```

Deterministic (two emits are byte-identical) and stamped with the build derived from the
image's own sha256, the `Gw.dat` path and the templates' sha256. Refused (rc 2): an exe
outside `pinned.BUILDS`' pristine set; a shifted mapping; **a build other than the loaded
skills table's** (ENG-7: the consumers interpolate a label row's numbers from THAT table, so
38833's labels over 38797's endpoints would be two builds in one row — regenerate
`skills.toml` first); **no `vault/content/` to write into** (the default path goes through
`vaultpath.require_dir`; an emit must not conjure a vault). The file is written to a sibling
`.tmp` and renamed into place, so a server starting mid-emit never reads half a file. Every
ArenaNet update means redoing both emits, and `test_skilldesc` §3 says so by comparing the
file on disk with a fresh emit.

**OWED: the client confirmation** — a label-tier cast on the loopback client shows the
number the record gives. Not run this pass (no client). The runsheet, prediction first:
**187 (Fire Magic 10, an Elementalist Spell, byte 16) at rank 0 resolves 7 before armour**
(`skill_scale_value(187, 0)`; at rank 15, 112), so the client's damage word on the practice
target is 7 × 2^((60 − AR)/40) truncated to whole points (studies/skills 43's rule), and
the gamesrv log carries `skill 187 resolves through a LABEL-tier row (ALL_FOES
AREA_ADJACENT TARGET_FOE AREA_BURST CLAUSE_KNOCKDOWN)` on the same tick; under
`--no-skill-labels` the same press deals nothing and the log says `no modelled effect`.
The control arm is runnable (ENG-8): a sandbox spec's `gamesrv_args` list passes any flag to
the gamesrv, last (`sandbox.game_args`; `test_sandbox` §5).

```
python toolkit/harness/sandbox.py --spec labelcast.toml --launch          # [player] secondary = 6, 187 first on the bar; cast it on the practice target by hand
python toolkit/harness/sandbox.py --spec labelcast_ctl.toml --launch      # the same spec plus  gamesrv_args = ["--no-skill-labels"]  : the control, no word
```

### 55.6 What this refutes or changes in the route, and what is next

- **The route's step 4 is DONE for the plain set and the residue is per skill**, as the
  route's own failed-gate consequence prescribed. Nothing here moves the 27 % (§54.4): the
  tier adds 47 acting skills to 54, not 341.
- **Changed: what "modelled" means.** Until today a `skill_effect` row was the grade; now
  the grade is the row's TIER, and three readers (the census, the sandbox, the orchestrator)
  say `label-only` for the generated ones.
- **Refuted, small:** the assumption in §54.4 that `CONDITION_DURATION` is served "on any
  type" is true of the consumer and false of six skills — the step-4 gate is where that
  difference lives, as §54.4's last sentence said it would.
- **Refuted, by review (§55.7):** nine of the first pass's 59 rows over-applied. The gate's
  first version read the target byte and the type and nothing else; it now reads the slot's
  own `%`, the record's `combo_req` and `combo`, `spell_burst`'s whole predicate, and the
  recipient's class.
- **Open, per skill (the residue, in order of cheapness):** the 74 client-side exclusions by
  class (a caster-centred area for byte 0/1 would move 12 and a caster-centred party heal 4
  — 287 and 2221 first, being under-applied only; a chain gate for non-attack `combo_req`
  moves 3 and would also advance 974's step; a condition rider on episodes 6; byte 1's
  resolution 3 heals; a percent-of-loss heal 1); the 210 conditional SERVED rows; the marked
  clauses (knock-downs on label rows first: 6); a flat-constant reader in `skill_condition`
  (167); then the 924 RECOGNISED and §54.4's two-consumer proposal, still the owner's call.
- **Open, route:** step 5 (the 68 no-slot rows), step 6 (the timed effect types 16, 24–28),
  the 141 INDETERMINATE slots on a client tooltip run (§54.3), and §55.5's confirmation run.

### 55.7 SKILLS-LT5 — the fix pass: what the reviewers refuted, and how the gate answers each

Two reviewers read the first pass (59 rows): an evidence refuter who read all 59 templates
at run time and called the real consumers on each, and an engineering reviewer who probed
the plumbing. Their findings, and the fix pass's answer (every answer is a rule in
`build_label_row` with a synthetic known-bad arm in `test_skilldesc` §1b and, where a corpus
row carries it, a forced-row arm in §3 that the checker must name):

| finding | rows | what the server did | the rule now |
|---|---|---|---|
| LT-R1 a byte-0 heal whose text excludes the caster | 1262 | `skill_heal` 30..150 on the caster — the one recipient retail refuses | `HEAL_RECIPIENT_CLASS` |
| LT-R2 heals that belong to the caster's spirits | 2051 2100 | 60..92 on the caster | `UNMODELLED_CLASS` |
| LT-R3 a heal conditioned on a condition's removal | 943 | 10..82 on the caster at every cast, Burning or not | `HEAL_RECIPIENT_CLASS` (287, 2221 fall with it — under-applied only, the parse cannot tell) |
| LT-R4 a chain requirement on a non-attack | 784 973 1033 | Poison / Blind / earth + Deep Wound landing with no chain test (the E5 gate is attacks-only) | `CHAIN_REQUIREMENT` from the record's `combo_req` |
| LT-R5 a percent slot labelled HEAL | 292 | 100..136 Health, no sacrifice | `PERCENT_SLOT` (`analyse()` records `percent` per slot) |
| LT-R6 a corpse prerequisite | 96 | 50..234 on the caster with no corpse | `UNMODELLED_CLASS` |
| LT-R10 a fleshy-only condition (PLAUSIBLE, minor) | 106 | Disease on any target | `UNMODELLED_CLASS` — the server has no fleshiness, so it cannot refuse what retail refuses |
| LT-R7 / ENG-2 `AREA_BURST` false for two rows | 192 197 | one hit, once, to one target — `spell_burst` refuses a duration | the gate mirrors `spell_burst`'s whole predicate; `test_skilldamage` §14 checks the mark against the function on every row |
| LT-R8 under-applications shipped unmarked | 20 rows | a knock-down, a shadow step, an interrupt, a cure, a disable, a range, "you and", 1996's slows, 25 % penetration, Cracked Armor, the areas over time | `DURATION_UNMODELLED`, `CONDITION_UNNUMBERED`, `LITERAL_DROPPED`, `CHAIN_STEP_NOT_ADVANCED`, `CLAUSE_*` (§55.3); 36 of 47 rows marked |
| LT-R9 no arm for the classes that got through | — | nothing could have gone red | `check_label_rows` names a percent slot, an unmodelled class and (with the records) a chain requirement; arms on 292 96 784 |
| LT-R11 / ENG-4 the flag's wiring untested; a dead global | — | — | §14 parses `--no-skill-labels` and locks `drop_tier` before `srv.listen`; `SKILL_LABELS` removed |
| LT-R12 no `Gw.dat` in the provenance | — | — | header: `dat`, `templates_sha256` |
| ENG-5 the log line and the `~label` mark unchecked | — | — | §14 captures the line and locks both call sites; `--smoke` asserts the marks and the filter |
| ENG-6 `tier` unvalidated | — | `tier = "Label"` loaded as a hand row and won | `content.TIERS`, refused at load, three spellings tested |
| ENG-7 an emit with no vault, or on another build | — | created `vault/content/`; stamped 38833 over a 38797 table | `require_dir`; the build must be the loaded skills table's |
| ENG-8 the runsheet's control not runnable | — | — | `gamesrv_args` in the sandbox spec |
| ENG-3 four citations shifted by the helper block | — | — | re-pointed (deskwork PLAN 260 / 439 / 446, unitsetup FINDINGS 22) |
| LT-R13 / ENG-9 / ENG-10 / ENG-11 | — | a mangled line, a stale message, an overstated help text, a miscounted skip, three LABEL_TIER literals, a non-atomic write | each fixed; `test_skilldamage` is NOT bare-capable (section 1 needs the skills table — pre-existing, main's copy crashes the same way) |

**Declined, with the reason.** ENG-1 asked that the overlay be moved out of `vault/content/`
until the branch merges, because main's `test_skilldesc` (pre-tier `hand_rows`) counts the
label rows as hand rows and is red against the live vault, and four stale worktrees whose
checkout lacks `skilldesc.py` refuse to load content on its extractor condition. The fix
pass does not merge (its instructions) and does not move the file: the overlay's home is
the scope's own design and the merge is the fix — **merge desk-d4b promptly, and any tree
older than 2026-09-22 needs `RURIK_VAULT` pointed elsewhere to load content** (this is now
in the PLAN-LOG entry). The one reviewer proposal not taken is ENG-6's second half (refuse a
client-table `skill_effect` row with no tier): world.toml's 346 is exactly that and is a
hand row.

**Count, honestly.** 131 plain → 10 hand → 74 excluded → **47 shipped**, 36 of them marked.
The first pass said 59; the reviewers' honest number was "at most 50"; the rule that answers
LT-R1/R3 without reading grammar costs 287 and 2221 as well, and 106 falls to LT-R10's
class. Every id is in the overlay's header by reason.

**What would refute this section.** A label-tier cast whose client word is not the record's
number (the consumer or the mapping is wrong — the runsheet above is the test); a string in
`skill_labels.toml` outside `OVERLAY_VOCABULARY` (the gate leaked text; `test_skilldesc` §3
would be red); a hand row that a label row replaced at load (the tier rule failed;
`test_content`); a shipped row whose skill retail does NOT fire unconditionally, or fires on
someone else — a clause our flags and patterns do not catch — which is the standing
weakness above, and the reason the tier is marked; an `AREA_BURST` mark on a row
`spell_burst` refuses (`test_skilldamage` §14 would be red).

---

## 56. SKILLS-SH — party-wide shouts: retail applies "Charge!" and "Watch Yourself!" to every ally in earshot, each apply attributed by the INSTANT-skill announce `[48, caster, skill]`; the radius is the client's own `aoe_range` (1000 u), which the tape neither measures nor bounds (2026-09-23; the fix pass the same day, §56.8)

**Desk, no run.** DESKWORK-D5 step 5 ([studies/deskwork/PLAN.md](../deskwork/PLAN.md)
§3 D5). The route's survey said: every type-15 `0x0042` on an observer is skill 364,
all on `20260817T231139`, 42 the observer's own cast and 23 another caster's. The
reader `toolkit/authsrv/shoutjoin.py` re-derives that from the bytes with its
predictions stated first, and what it found is below. **The witness context is PvP**
(Random Arenas on `20260817T231139`, the observer's four-player team against another)
plus the owner's own PvE casts on six later captures, one of them with a hero.

### 56.1 The survey, re-derived — P1 FAILED as registered, REPRODUCED as a total

96 connections decode whole; 95 name one observer (the 96th, `20260807T133758` conn
54560, carries no property 41 and no skill press and is refused by the observer rule —
§56.8). **65 shout applies**: 58 on the observer (364 × 48, 348 × 10) and **7 on a
hero** (348, `20260914T005758`, the hero's own casts); **42 with caster == wearer, 23
another ally's**. The 65 = 42 + 23 is the survey's number to the unit — but ONLY as
caster == wearer versus not: **the observer cast 35 of them, not 42** (34 × 364 and
1 × 348), a hero cast 7 on itself, and of the 23 foreign applies on the observer **6 are
the hero's shout landing on the player**. The "all 364, all on one capture" is not the
tape's either: 348 ("Watch Yourself!", type 15, `aoe_range` 1000) is in the set and the
applies sit on ten captures. Recorded as P1 FAILED-as-registered with the measured
composition beside it; `test_shouts.py` §2 pins the composition on tapes stamped to
2026-09-23, a cutoff the census applies by construction. (The first record of this
section said 59 / 6 and "42 the observer's own": it had taken the hero for the observer
on the one hero tape — §56.8.)

### 56.2 Which message announces a shout — OBSERVED, and it is not property 60

The first cut looked for the spell's `0x009F [60, caster, skill]` and found **zero**
for any Shout id in the corpus: every apply came out unattributed. The apply's own
batch shows the announce: **`0x009F [48, caster, skill]`** — `agents.GV_INSTANT_SKILL_ACTIVATED`,
named there since the property census and **sent by this server nowhere** — beside a
`[21, caster, 622]` and an `0x00A5 [caster, text]` (the speech bubble), and for the
observer's own shout E4 / E5 / E3 with no E4→E5 gap (activation 0). The corpus census
of property 48 by the skill's type: **Stance (3) 64, Shout (15) 67, type 16 2** — 48 is
the INSTANT skill's announce, not the shout's alone. Every one of the 65 applies has
its 48 inside 1.5 s (P2), all at dt = 0. **Divergence, OPEN:** ours announces a shout
through `cast_anim_msg`'s property 60.

### 56.3 Sides: a shout reaches allies and never foes — OBSERVED

The `0x0020` create's field 12 (the allegiance token) names the sides, and the reader
reads them from the tokens ALONE: the same token is an ally, the client's own
`ALLEGIANCE_NONCOMBATANT` ('nonc', 0x6E6F6E63, `agents.py`) is its own class, any other
token is a foe (the first cut defined a foe token by the outcome under test — a token
whose casters never produced an apply on the observer — which made "0 foe applies"
nearly true by construction; §56.8). The other team's casters shouted 364 **8 times**
with **0 applies** on the observer. 4 of the 8 sit inside 1000 u by POINT ESTIMATE
(230–500 u), but every one of those estimates rests on a lead sample (§56.4), so the foe
exclusion is OBSERVED as 0 of 8 and is **not distance-controlled** on this corpus. All 23
foreign applies on the observer came from the observer's own token (P3). One agent per
arena connection (11 on conn 50286, 15 on 50513 and 54071, 17 on 50527) carries the
**noncombatant token**, never shouts, and is boosted by the team's shouts (15 words at
383.04 across the 364 batches — the arena's and five PvE connections'; on conn 63805
three noncombatants at once) — so token equality is not party membership, and **retail's
party shout reaches an allied noncombatant where ours does not** (`skillread.allies_of`
admits `ALLEGIANCE_PLAYER` alone; §56.7).

### 56.4 Reach: the radius, bounded, not measured

`aoe_range` (+0x6C of the skill record, `skilltable.py`) is **1000.0** for 364 and 348 —
the value WIKI (GWW "Area of effect", as `skilltable.py`'s comment cites it) calls
earshot. **The tape has no agent's position at an apply, and what it has is worth less
than the first record allowed.** Exact samples are a create (once), `0x002C` (rare) and
the observer's own c2s move reports; every other sample is a `0x0029` lead or a `0x002A`
destination — a point AHEAD of the agent on its path. The one place the tape holds an
exact position and a lead for the same agent at the same moment is the observer itself,
and **the lead check** (`shoutjoin.py`: 6,639 observer leads with a c2s report inside
0.1 s) puts the lead a **median 765 u** from the position (maximum 4,264 u; 5,238 of the
6,639 beyond the 300 u the first cut allowed a lead). A lead is not a position with an
allowance. Every one of the 32 caster-to-wearer pairs rests on at least one lead sample
— the observer is the only agent with exact samples, and the other agent of every pair
has leads alone — so **no pair resolves, the tape bounds earshot in neither direction,
and the distance half of P4 is UNTESTABLE on this corpus.** The sides half stands: 0 of 8
foe pairs applied, 23 of 24 ally pairs did (the 24th is the hero's shout at t = 439.258
on `20260914T005758`, whose apply on the player is absent — on a lead, unresolved). By
point estimate the 23 applied ally pairs sit at 51–753 u: a consistency, not a bound.

**The first record's "the tape puts earshot at ≥ 913 u" is withdrawn.** That pair
(`20260817T231139` conn 50513, t = 476.998) took the observer's own `0x0029` lead — 765 u
from its c2s report 35 ms earlier — for its position; from the report the pair is 188 u.
And "resolved" was asymmetric: a pair that agreed with the radius resolved whatever its
error, so 912.7 ± 882.8 u counted as a bound. Both rules are replaced (§56.8). **Label:
the party-wide rule OBSERVED (23 foreign applies on the observer, every caster the
observer's token; 0 foe applies); the radius CORROBORATED (client table + WIKI) and
untested by the tape; the hero-to-player direction OBSERVED (6 applies), the
player-to-hero direction UNWITNESSED (RECONSTRUCTION by symmetry — no tape has both a
player shout and a hero wearer).**

### 56.5 The other allies are on the wire too — P6

The batch of a 364 apply on the observer carries **`0x0027` speed words for the OTHER
party members**: 86 words across the observer's 364 batches, **0 to 5** other agents per
apply ({0: 17, 1: 5, 2: 6, 3: 13, 4: 5, 5: 2} over the 48 applies — the first record
said 3–5), none on a foe-token agent, 15 on the noncombatant. That is the wire's own statement that the
shout landed on every ally reached, not only on the agents whose effect list is sent
(F38: the observer's and a hero's). Two refinements fall out: the observer's own words
sit at 288 × 1.33 = 383.04 while the other players' sit at 300 × 1.33 = 399 (F48 P6's two
bases, seen side by side in one batch); and at t = 702.662 the observer re-cast 364 over
an ally's still-open 364 and **no word went out for the observer** — retail declares a
speed word on a change of the VALUE, not at every episode change; F48 P5's "re-declares
at EVERY episode change" was read off the cure batch, where both words were changes.
`push_speed` already sends only on a change, so nothing moved.

### 56.6 Shipped

* `content/world.toml` `skill_effect.364`: `party_wide = "earshot"`, the row's own
  provenance carrying §56.1–56.4.
* `authsrv.apply_effect`: the per-wearer body moved into `_apply_effect_on` unchanged;
  a `party_wide` row runs it once more for every agent `shout_wearers` returns — the
  living allies (`allies_of`: heroes, henchmen, the player when a body shouts) inside the
  skill row's `aoe_range` of the caster; each wearer gets its own episode, buff id, cure,
  status / speed / attribute words, and the `0x0042` only where `effect_list_send` sends
  one (the player, a hero). A row with no radius, or a caster with no position, reaches
  the caster alone and says so. `--no-party-wide-shouts` is the caster-alone arm.
* `toolkit/authsrv/shoutjoin.py`, `test_shouts.py` (42 checks, floor 30; TESTS.md).

### 56.7 Not settled

* **348 has no `skill_effect` row** and gets none here: its effect is an armour bonus
  and no armour-bonus mechanic exists to hang it on, so a hand row would be an
  icon-only row — the label tier's business (§55), not a hand row's.
* **The hero's cure on screen** is final-confirmation-needs-run (D5's own cost line).
* **The announce property** (56.2) and **the batch order** — retail sends every apply,
  then every speed word; ours interleaves per wearer — are named divergences, unshipped.
* **Retail's party shout reaches the allied NONCOMBATANT; ours does not** (§56.3: 15
  boost words on the 'nonc' agent in the arena batches, three at once on conn 63805).
  `skillread.allies_of` admits `ALLEGIANCE_PLAYER` alone. An under-application, open.
* **The player's shout reaching a hero is unwitnessed.** On the hero-roster connections
  where the observer shouted no hero cast anything, and on the one tape with a casting
  hero (`20260914T005758`) the player never pressed a shout (its presses are 392 / 394 /
  433 / 446 / 455). The server does it by symmetry (RECONSTRUCTION); the loopback run in
  D5's cost line is its confirmation.
* The reach table's distances are point estimates on leads (§56.4). A tape with `0x002C`
  positions around a shout, or a loopback run with the party placed at 990 / 1010 u,
  would make earshot a measurement; nothing on disk does.
* `spellhitjoin.player_of` — the first-`0x00E3` rule shoutjoin's first cut copied — is
  what `interruptjoin` still uses to name the player; on the hero tape it names the hero.
  Outside this pass's scope; recorded so the next reader of that tape knows.

### 56.8 Fix pass (2026-09-23): what two reviewers refuted, and how the reader answers each

Two reviewers read the first record of this section — one re-deriving every claim from
the tapes, one reading the code. Both are right on the two facts below; nothing they
found touches what shipped (`party_wide` on 364 with the client's 1000 u; the per-ally
episodes; `--no-party-wide-shouts`).

* **The observer on the hero tape was the hero.** `shoutjoin.rows_of` took the agent
  of the connection's first `0x00E3` (`spellhitjoin.player_of`'s rule). On
  `20260914T005758` conn 56011 agent 30 — class tag 2, definition 0x11ab, 48 of the 54
  acks — casts 346 and 348 all session and is the hero; agent 29 is the only class-tag-3
  create, the agent of the first property 41, and the agent whose acks answer every c2s
  press. So "6 applies on a hero" was the hero's Watch Yourself! landing on the PLAYER,
  the composition is 58 / 7 not 59 / 6, and the observer cast 35 not 42. The reader now
  names the observer by `adrenjoin.whose_agent` (property 41, self-scoped, the JARIN
  kind-5 tie-break) CROSS-CHECKED against the agent that answers the connection's own
  presses, and REFUSES a connection where the two disagree; the 96th connection, with
  neither, is refused rather than guessed. `test_shouts` §2 pins the observer as 29.
* **"≥ 913 u" was the observer's own lead.** The observer's `0x0029` is a point ahead
  of it, not its position (§56.4); the reader now positions the observer from its exact
  samples only, measures what a lead is worth against those samples (the lead check:
  median 765 u), never resolves a pair that rests on a lead, and resolves an exact pair
  only when its verdict stands outside its stated error on EITHER side of the radius —
  the first cut resolved every agreeing pair whatever its error. The stated error for
  exact samples is a bound with no free parameter (speed × hold age; twice speed × the
  nearer age when interpolated). Result: no exact pair exists, no bound exists, and the
  section says so instead of a number.
* **Sides were defined by the outcome.** A foe token was "one whose casters never
  applied on the observer". Now: the same token is an ally, 'nonc' is the noncombatant,
  anything else a foe — from the create's field 12 alone. 0 of 8 foe applies reproduces.
* **The third token is the client's own noncombatant constant**, and retail's shout
  boosts it (56.3, 56.7). Named, and the under-application recorded as open.
* **"4 foe shouts inside 1000 u under both readings"** — one held at 1156 u, and all
  four rest on leads; now "4 by point estimate, none exact, not distance-controlled".
* **"3–5 agents per apply"** — the distribution is 0–5 and is given (56.5).
* **The 364 row said "17 of the 48 applies of 364"** — 17 was 364 and 348 together;
  the row now says 14 of 48 (23 of 58 with 348's 9).
* **The test** claimed section 1 "needs no vault"; it needs the vault's skills table
  (the client's row for 364) and now declares a skip without it, so a bare machine gets
  a named shortfall instead of a traceback. Its "primary excluded" check named the
  player as the primary, which is never in its own ally set — a check that could not
  fail; it now names the hero. Its cutoff filtered rows after the census counted
  connections and refusals over every tape; `census(cutoff=…)` now skips a later tape
  before reading it, so every pin is exact by construction. 47 checks, floor 30.

---

## 57. SKILLS-RX — the refusal block by id: the 60 plain strings 1934–1993 as a table of ids and OUR labels, three OBSERVED, the rest RECONSTRUCTION, behind a default-off flag whose one consumer is the weapon gate (2026-09-23)

**Desk, no run.** DESKWORK-D5 step 7 (REX-5), closing §38.8's second item as far as a
desk can. The owner's archive, read through `textrec.TextIndex` (never committed):
**1934–1993 are 60 PLAIN records, none empty; 1928–1933 and 1994–2000 are RC4-encrypted**
(`needs_key`). So the route's "60 readable, 6 encrypted" is the span 1928–1993, and the
readable block is exactly the table. Two ids carry the same recharging sentence (1964
and 1988); 1964 never appears on any wire we hold (§38.5). Two are TEMPLATED (1942,
1943 take `%str` / `%num` arguments) and cannot be sent as a bare coded word.

**What is committed** (`toolkit/authsrv/chatdefs.py`): `REFUSAL_REASONS`, id → a
snake_case label of ours for the condition the sentence names (where a label carries a
skill's name it is the short proper noun the repo uses everywhere, PLAN.md §7 Q17);
`REFUSAL_OBSERVED = {1934, 1960, 1961}` (1934 1 of 1, §38.5; 1960 39 of 39; 1961 on
screen, §38.2) — **every other row is RECONSTRUCTION**, because the ids live server-side
and the client renders what it is handed (§38.8); `REFUSAL_TEMPLATED`; the block's edges
and its encrypted neighbours; `refusal_evidence(id)`, `refusal_reason_id(label)`.
`REFUSE_WEAPON_TYPE = 1985`.

**The flag.** `--refusal-reasons`, **DEFAULT OFF**. Its one consumer is DAGGERS-B4's
weapon gate, which sends `#1985` with the `0x00E2` release when the flag is on and the
bare release (retail's shape for 3 of 43 refusals) when it is off — off because what
retail sends on a weapon mismatch is NOT OBSERVED (the client very likely never sends
the press). The two OBSERVED resource refusals go out either way, as before.

**Tests pin ids and labels, never text**: `test_chatdefs` §6 (the table's shape and the
three constants), §7 (the archive: every id plain and non-empty, the 13 neighbours
encrypted — a declared skip without the archive), `test_daggers` §4 (the gate under both
arms).

**Fix pass (2026-09-23): the wire re-counted.** The evidence refuter scanned every live
`0x005D` for a coded id in the block; this pass did the same and agrees: **1960 × 39,
1961 × 17, 1934 × 1, 1988 × 1** (and 2000 × 1 on channel 10 at a death, outside the
block). Two rows above were wrong about the wire. **1961** was labelled from the screen
alone (§38.2) while retail's wire carries it **17 times** — 12 on `20260914T005758`
answering the player's `0x0046` presses of 392 and 446, 5 on `20260916T213125` answering
307 and 346, each `0x005D #1961, 0x005E [1, 7], 0x00E2` — and `chatdefs.py`'s 1960 / 1961
comments still said the corpus held zero energy refusals, true when written and false
since those two tapes (§38.2 carries the pointer now). **1988 was RECONSTRUCTION and is on
the wire once, as the recharge refusal**: `20260913T210901` conn 60877 t = 701.625, the
player's second press of skill 40 (c2s `0x0046` at 700.022, during its own cast) after its
8 s recharge began (`0x00E5 [9, 40, 0, 8]` at 700.897), answered **`0x00E3 [9, 40, 0]`,
`0x005D #1988`, `0x005E [1, 7]`, `0x009F [57, 9, 0]`, `0x00E2 [9, 40, 0]`** — the
sentence AFTER the ack and BEFORE the release with property 57 between, an order no 1960
refusal uses. So the recharge refusal's id is **1988, not 1964**: the two records carry
the same sentence, §38.5's "1964 never appears on any wire" stands, and its "the genuine
recharge refusal is silent" was that tape's — this one is not. `REFUSAL_OBSERVED = {1934,
1960, 1961, 1988}`; the pass-3 summary's "the recharge refusal (1964 / 1988) has never been
on any wire" is withdrawn. Also from the review: the templated guard now sits on
`refusal_body` (the send path — `refuse_press` takes a constant that never passes
`refusal_reason_id`); the Q17 sentence is re-worded as a reading of the carve-out, not a
citation of the ruling; `test_chatdefs` §7 catches `SystemExit` (textrec's refusal on a
bare machine), a regression from `main` where the test died with no verdict; the authsrv
flag is `REFUSAL_REASON_IDS`, so it cannot be read as the table; the weapon gate's comment
names the label, not four words of the sentence. `test_chatdefs`: 52 checks with the
vault, 43 + 2 declared skips bare (it died bare before), floor 40 → 43 (the bare run's
count); `test_daggers` 105 unchanged under the renamed flag.

---

## 58. SKILLS-MC — Mend Condition (275): remove ONE condition and heal the flat scale once, IF one was removed (2026-09-23)

**Desk, no run, no corpus witness** — the third cure shape §46.3 left unmodelled.
The client's row: scale 5→70 (57 at rank 12), energy 5, activation 0.75, recharge 2,
**target byte 4 = other ally** (the caster is not a legal recipient; Mend Ailment's is 3).
The mechanic is the one §46.1/46.3 recorded from GWW on 2026-09-10 — remove one
condition; if a condition was removed, heal — a flat heal gated on the removal, neither
per-removed (276) nor per-remaining (277). Which condition goes: the newest (GWW "Cover",
the rule `remove_conditions` already honours).

**Shipped:** `skill_effect.275` (`removes_conditions = 1`, `heal_if_removed = true`);
`resolve_heal` reads `heal_if_removed` and heals the flat scale once when the removal
removed something, nothing otherwise; `--no-condition-heal-rule` reverts it with the other
two shapes. `test_mechanics` §34: the no-condition CONTROL heals nothing (a flat heal
there is the revert arm), one condition → removed and 57 once, two → the newest goes and
still 57 once, aimed at the caster → no legal recipient, the revert arm heals without
curing. **RECONSTRUCTION on the wire** (§46.3 stands: no retail cure has been captured).

**Fix pass (2026-09-23): the witness named.** Both reviewers found the row's provenance
pointing at a source that does not quote it — §46.3 paraphrases 275 and §46.1's GWW quote
is Mend Ailment's. Two witnesses now stand where the paraphrase stood. **WIKI (GWW, "Mend
Condition", rev. 2023-02-19, read through the browser)**: Spell, Monk / Protection
Prayers, energy 5, activation ¾, recharge 2, target "other allies" ("Cannot self-target."),
and the description's two sentences — remove one condition from target other ally; **if a
condition is removed**, that ally is healed for 5…70 — every number the client's row
carries. **The client's own description template** (`skilldesc.py --row 275`): `str1` is
the scale slot at AGREE_PROGRESSION 5/70 labelled HEAL, the flags CLAUSE_REMOVAL, IF and
TARGET_ALLY, the hand row's `scale_means = Healing` AGREE — the same mechanic, from the
client the server drives. The row's `page` now names the revision; the mechanic's label is
unchanged (the heal shape CORROBORATED by page and template; the wire RECONSTRUCTION).
