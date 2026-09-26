# The sandbox — the vertical slice as a configurable practice run

**Written 2026-09-20.** The owner's ask, verbatim from the session that opened this arc:

> it'd be another UI app, let's start it like this: run orchestrator. we'll take the
> vertical slice, and make it configurable. the user can change which heroes spawn into
> the party and their professions. the user can set up to 4 enemies per group, including
> the boss. the user can pick their profession(s). the user can pick which skills are
> unlocked for them and their heroes. this lets anyone do a little quest against enemies
> of their choice with heroes of their choice. a good little practice sandbox

**Identifiers.** `SANDBOX-B<n>` = build steps, things to do. `SANDBOX-U<n>` = unknowns,
each with the prediction written before the run that settles it. `SANDBOX-F<n>` = findings.
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

Status authority is `PLAN.md` §3's `R-SANDBOX` row; this document carries the detail.

---

## 0. What exists, and what the app is

The slice ([studies/slice/PLAN.md](../slice/PLAN.md)) already runs the whole loop the
owner describes — outpost, quest, corridor, two groups, a boss, the turn-in — and every
knob the ask names is *already content*, just content with one value:

| The ask | Where it lives today | What one value it holds |
|---|---|---|
| which heroes, their professions | `[party.slice]` in `content/world.toml`: `hero`, `body`, `skills`, `level`, ranks, weapon | ONE hero (Tahlkora, index 3, the Academy Monk body); the profession is the **body template's byte** |
| enemies per group, the boss | `[spawn.corridor_*]` rows, `area = "corridor"`, five of them | 2 + 2 + the boss, hand-placed at y 4600 / 7600 / 10400 |
| the player's profession(s) | `player_profession` on the party row; `--spawn-profession` | a primary only — `agent_set_profession(..., 0)` hardcodes the secondary to none |
| skill unlocks | `--unlocks` (the ACCOUNT set, `0x001D`); the character set `0x00DB`; a hero's own list on `0x0073` | `corpus` (1,333 player-usable ids) |

So the orchestrator is not a new server feature. It is **a spec, a compiler and a
window**: a spec names the party, the groups and the libraries; the compiler turns it
into a content overlay (a `[party.sandbox]` row and `[spawn.sandbox_*]` rows the server
loads over the repo's tables) plus the flags the existing harness already takes; the
window edits the spec, resolves every name from the owner's own archive at run time, and
presses the button. Two server changes were needed for the ask to be expressible at
all, and both are the plainest possible generalisation of a single value into a list:
a party row may carry **several heroes each with their own row**, and the player's
profession pair may carry **a secondary**.

**The gate.** Nothing here commits ArenaNet's text. Skill, hero and attribute names are
string ids resolved through `toolkit/clientscan/textrec.py` when the window opens, and
the spec on disk carries ids. The vault's `heroes.toml`, `skills.toml` and
`attributes.toml` are the extracted tables the window reads; each is a client-table row
with its extractor and build named.

---

## 1. The pieces

| Piece | Where | Rule it lives under |
|---|---|---|
| **The spec** | `vault/sandbox/<name>.toml` (gitignored), one file the window writes; `toolkit/harness/sandbox.py --example` prints the slice as one | ids only; a place or profession name is a label (`PLAN.md` §7 Q17) |
| **The compiler** | `toolkit/harness/sandbox.py` — `compile_spec(spec, world)` → the overlay text, the gamesrv args, the harness command, the environment | stdlib, offline, tested by `test_sandbox.py`; refuses a spec that names a skill outside its profession, a body the content lacks, a fifth member, an eighth hero, or ranks the level cannot pay for |
| **The overlay** | `vault/sandbox/<name>/world.toml`, merged LAST by `toolkit/content.py` when `RURIK_CONTENT_EXTRA` names its directory | the same provenance rules as every row; every generated row is `source = "invented"` and says which spec wrote it |
| **The server** | `[party.KEY]` + `[[party.KEY.heroes]]` (SANDBOX-B3); `player_secondary` / `--spawn-secondary` (SANDBOX-B4) | a row with no `heroes` list and no secondary is byte-identical to every run before |
| **The window** | `tools/orchestrator/orchestrator.py` (PySide6, like `tools/viewer/`), `apps/orchestrator.pyw` to double-click | outside the stdlib rule, holding no archive knowledge: every fact comes from `sandbox.py`, `content.py`, `textrec.py` |
| **The run** | `session.py --replace --keep-open --exe vault/run/slice/Gw.exe --game-args "--map 148 --party sandbox --area errand,sandbox --unlocks …"` with `RURIK_DAT` on the slice archive | the operator plays; the stack comes down when the client closes |

---

## 2. The build ladder

| Item | What | Status |
|---|---|---|
| **SANDBOX-B1** | `toolkit/content.py` takes `RURIK_CONTENT_EXTRA` (os.pathsep-separated directories merged after `overrides/`), so one run can carry rows the tree does not, without touching `vault/content/`, which every process reads | **DONE 2026-09-20**, `test_content` |
| **SANDBOX-B2** | The compiler: spec → overlay + args + command. Group geometry along the corridor's long axis (groups evenly spaced between y 3900 and the boss at 10400, members 470 u apart within a group, the boss at its group's centre with a glow), agent ids from 110 and one definition per template from 60 — outside the errand rows (98/99, 50/51) and the party's reserve (1, 30, 200..206, 9..16), which `area_population` refuses at startup | **DONE 2026-09-20**, `test_sandbox` |
| **SANDBOX-B3** | Per-hero rows: `[[party.KEY.heroes]]`, each with `hero`, `body`, `profession`, `skills`, `level`, `health`, `energy`, `weapon`, `attributes`, `armor`, `damage`, `weapon_attribute`. `HERO_ROWS` and one `hero_*()` reader per field, falling back to the single-hero globals; every site that read `HERO_BODY_NPC` / `HERO_SKILLS` / `HERO_LEVEL` / `HERO_VITALS` / `HERO_ATTRIBUTES` / `HERO_ARMOR` / `HERO_DAMAGE` / `HERO_WEAPON` for "the hero" now asks for *this* hero. `PARTY_WEAPON_ITEMS` gains `sword` and `hammer` (the item rows landed at SLICE-H9/H11 and the table was never told) | **DONE 2026-09-20**, offline; on a client: SANDBOX-U2 |
| **SANDBOX-B4** | The player's secondary: `player_secondary` on the party row and `--spawn-secondary N`, carried on `0x00B7` and `0x00A6` and into `attribute_state` so the secondary's attributes are spendable and its primary attribute is refused | **DONE 2026-09-20**, offline; on a client: SANDBOX-U1 |
| **SANDBOX-B5** | The window: Player / Heroes / Enemies / Run. Names from the archive; the spec saved to the vault; the compiled overlay and command shown before the button; the run's output streamed | **DONE 2026-09-20**; `--smoke` drives every panel headless |
| **SANDBOX-B6** | The owner's first run: the slice's own spec through the window, then a spec that changes every knob at once | OPEN — the owner's |
| **SANDBOX-B7** | **The in-game panels own the bars and the ranks** (2026-09-22, the owner: "remove all the attribute and skill defs, they can be managed through the in-game interface"; "we're gonna need a working player and hero Skill and Attribute panel adjustments + skill slotting"). What already stood, read out of the handlers and the run docs (§4, SANDBOX-F3): `0x005C` slot write and `0x005E` swap are AGENT-KEYED and refereed for the character and for every hero (RUN-HEROLIB-B/C/D settled the swap's field order on a client); `0x000F`/`0x000E` raise and lower are answered for both, refused with the reply still sent, persisted (`persist_attributes`, `persist_hero_attributes` — J1 met on a client); `0x0010` template load, the character only. What was MISSING, and shipped: a hero's BODY cast the row's bar while its panel drew the store's (`hero_cast_bar`, and `sync_hero_body_bar` after an in-game edit — recharges reset, said); a hero with no ranks had no budget and dead plus buttons (`points` on the hero row, `hero_points`); an authored EMPTY bar or rank list was read as "no field" and fell through to the fixture's hammer bar and 173-point ranks, or to the PLAYER's bar on the hero's panel (`is not None`, `hero_bar_authored`); the store's seed LEVEL overrode the row's (`PLAYER_LEVEL_AUTHORED`: the store follows the row); the run never passed `--persist` (it always does now, `persist = false` in a spec reverts). The window: **Skills** (the account library, every player-usable skill, filterable) and **Party** (the character's pair, level, hands; the heroes UNLOCKED, each with a profession, a body and a level — no bars, no ranks) replace Player/Heroes; Run gains the store's warnings at compile and a reset | **DONE 2026-09-22**, offline; on a client: U5 |
| **SANDBOX-N1** | A better, filterable skill and attribute selector for the Enemies tab (the owner, 2026-09-22: "mark this as a next step") — the Skills tab's list with a profession filter and text search, and a rank editor that names the attribute, in place of eight combo boxes and a form of spin boxes | **DONE 2026-09-24**, offline (branch `orch-beauty` `3e397421`..`9925c586`; PLAN-LOG "SANDBOX-N1, the Enemies tab's skill and attribute selector"): the Skill bar (eight wells over an inline filterable library) and one attribute to a row; the residue is in `PLAN.md` §8.1 |
| **SANDBOX-N2** | Adding and kicking heroes from the in-game party panel. The Heroes tab draws with Add Hero / Kick (SLICE-F42), and the c2s for either is NOT FOUND (heroes §3.3); today "unlocked" means "in the party" | ~~NEXT, after N1~~ **SHIPPED** as DESKWORK-D1 steps 1 + 4 (c2s `0x001F` kick OBSERVED, `0x001E` add RECONSTRUCTION) and CONFIRMED on our client in an outpost 2026-09-23 (studies/deskwork/CONFIRM-2026-09-23.md R1–R5; DESKWORK-Q1 note, 2026-09-24) |

---

## 3. The unknowns, and how each is settled

| Item | The unknown | How it is settled | Prediction, stated first |
|---|---|---|---|
| **SANDBOX-U1** | What the client does with a non-zero secondary on the player's own `0x00B7` / `0x00A6` | One run with `player_secondary = 3` on a Warrior: read the party window's profession label and open the Skills panel | The label reads `W/Mo`, the Skills panel lists Monk skills beside Warrior ones, the attribute panel shows Monk's three non-primary attributes. Refuted if the client asserts at the burst (then the secondary must ride the character-select blob too — `charsummary.py` bytes 10-13 — and `0x00B6`'s offerable mask may gate it) |
| **SANDBOX-U2** | Whether two heroes with DIFFERENT bodies and bars both render, follow and cast | One run with a Monk and a Warrior hero | Both roster rows draw with their own profession abbreviation, both bodies walk to their formation slots, the Monk heals and the Warrior swings. Refuted if the second body wears the first's model (a definition collision — `hero_slots()` gives each its own index, so this would be a new site) |
| **SANDBOX-U3** | Whether a human body of one profession carries a hero declared as another (a Necromancer in the Hatcher's body) | Part of the U2 run | The roster shows the declared profession; the body is cosmetic. NOT FOUND today either way |
| **SANDBOX-U4** | Whether four hostiles in one group aggro as a group | Part of the first run with a 4-member group | Each aggros independently at 1012 u (the slice's rows do), so a tight cluster pulls as one anyway — the 470 u spacing keeps every member inside the first's aggro of the player |
| **SANDBOX-U5** | Whether a character and a hero that start with EMPTY bars and unspent points can be built entirely in-game and keep the build across a run | One run: open K and the attribute panel for the character, the hero's panel for the hero; slot a skill on each, spend a point on each, close the client, launch the same spec again | Both edits draw at once (0x00D9 / the 0x003B batch), the hero CASTS the slotted skill in that session (`sync_hero_body_bar`), and the second launch's `0x00DA` and `0x003A` carry them (the store). Refuted if the hero's panel opens with the PLAYER's bar (the fallthrough this rung closed), or if the second launch's hero body casts the empty row bar (the create reads the store now). **Added 2026-09-25:** the hero's attribute panel must open with NO ranks and its own points unspent (10 at level 3) -- until that day its `0x003A` carried the PLAYER's ranks (the same fallthrough for ranks, found offline; PLAN-LOG "A rankless hero draws its own attributes"), and the empty `0x003A` it now sends has never been shown to a client (UNVERIFIED; the rows themselves follow `0x00B7`, OBSERVED at SECONDARY-R1b). **That half OBSERVED the same evening** (harness `20260925T223247`, a rankless monk hero, `--persist` off; PLAN-LOG "The empty 0x003A, CONFIRMED on the client"): the hero's panel opened "Monk, Attributes (10 unused points)" with Healing, Smiting, Protection and Divine Favor at 0, and the player's panel beside it kept its ranks. The rest of U5 -- the build made in-game surviving a relaunch -- is still unrun |

**Numbers that came from memory of the wiki and must be read back before they are
quoted as WIKI:** `sandbox.py`'s `ENERGY_BY_PROFESSION` (base energy and pips per
profession) is labelled `WIKI, unread` in the code. The Assassin pair (25 / 4) is OBSERVED
on the owner's own wire (`[party.daggers20]`'s note) and the base fixture's 25 / 3 pips is
a Ranger's on retail's wire (`[player.defaults]`'s note); the other eight rows are recalled
and the window lets the operator edit them. `points_for_level` is GWW "Attribute point"
and its four cited points (5 at 2, 10 at 3, 45 at 10, 170 at 20) are the ones the party
rows already cite.

---

## 4. Findings

| Item | What |
|---|---|
| **SANDBOX-F1** | **The server accepts a generated overlay at startup, no client.** 2026-09-20: the slice's own spec compiled, written to a scratch directory, and one gamesrv started on it (`RURIK_CONTENT_EXTRA` + `RURIK_DAT` on the slice archive, `--map 148 --party sandbox --area errand,sandbox`). The banner read the character (profession 1, the sword and shield, the bar, level 3, ranks, 10 points), the hero row (`hero 3 (profession 3) in the body of 'academy_monk' (level 3, bar [281, 276, 2], weapon staff)`), `AREA: errand,sandbox -- 7 spawn row(s): corridor_boss, errand_giver, errand_scout, sandbox_g1_m1 … g2_m2` — the population's set checks passed with the boss under the quest's key — and the rig (`HERO: 1 hero(es) [3] at agents [200] … body=agent 200; level=prop36 3`). OBSERVED on our server; what a client does with it is U1–U4 |
| **SANDBOX-F3** | **Where in-game skill slotting and attribute spending stood on 2026-09-22, read out of the code and the run docs.** Character: `0x005C` (`handle_skillbar_skill_set`, refereed by the character's learned set ∪ the account's, RUN-HEROLIB-A), `0x005E` (`handle_skillbar_skill_swap`, field order S confirmed on a client, RUN-HEROLIB-D §12), `0x000F`/`0x000E` (`handle_attribute_spend`, `attribspend.AttributeState`, persisted), `0x0010` (a template's spread, the character only). Hero: the same three handlers by agent id → `hero_index_for_agent`, refereed by own ∪ account (herolib), persisted to the store's hero row; the raise observed on a client (RUN-HEROLIB J1: `0x800f ATTRIBUTE_INCREASE` then `persist_hero_attributes` SAVE). The store: one JSON per account under `vault/state/characters/`, the loopback account's holding "Test Warrior" at level 3 with no ranks and one hero row. What no run had exercised: a hero starting from an EMPTY authored bar (the wire fell through to the player's bar) and a hero's edited bar reaching its BODY (the create read the row, the panel read the store). Both are B7's |
| **SANDBOX-F2** | **Two `test_agentlife` locks were about the old shape, not the rule.** The SLICE-H2c order lock searched the source for `level {HERO_LEVEL} on hero agent`; the per-hero loop prints `{_hlv}`, and the lock's claim (the pair before the level) still holds, so the lock followed. The SLICE-H7 weapon check asserted a Warrior body holds `None` — recorded 2026-09-13 when the sword row did not exist; it did from SLICE-H9 on, the table was never told, and the check now expects the sword |
| **SANDBOX-F4** | **A party with no heroes crashed the gamesrv at startup, and the compiler's own check could not see it.** OBSERVED 2026-09-25 on harness `20260925T161150` (DESKWORK pass 7's client runs, `studies/deskwork/CONFIRM-2026-09-24.md` §11 III): `KeyError: 'hero'` in `main()`, before any socket. TOML has no empty array-of-tables: `overlay_text` wrote one `[[party.sandbox.heroes]]` per hero, so zero heroes wrote NO `heroes` key, and `main()` read the missing list as the SLICE-H2 single-hero shape. SANDBOX-B3 had defined the empty list as the player alone, but nothing ever produced one: F1's startup was a spec with a hero, and `test_sandbox`'s `party_row(spec(heroes=[]))` check read the DICT, which had the list -- it was lost between the dict and the file. Fixed on both sides: the compiler writes `heroes = []`, and `authsrv.party_heroes` reads a row with neither key as the player alone (the class -- a hand-written row has the same absence) and refuses a hero's fields without `hero` by name rather than dropping the hero. `test_partyrow.py` drives `main()` itself: `--list-probes` returns after the party block and before any socket, so the real startup runs on the compiled overlay, on the defect's own TOML and on [party.slice] as the control. OBSERVED on the client the same day from the window's own Launch (harness `20260925T170126`): `PARTY 'sandbox': NO heroes`, `PLAYER_PARTY_SIZE(1)`, no hero record, PASS |

## 5. What this document does not claim

- That a hero of every profession *fights* — SLICE-B7 gave heroes heals, and H4 the
  plain swing and the leader's target; a damage-dealing hero's skills land through the
  same `land_skill` a body's do, but only the 54 skills with a `[skill_effect.*]` row do
  anything beyond their icon. The window marks a skill `modelled` when such a row exists.
- That every body in the enemy picker renders. Fifteen were watched at the parade
  (`studies/slice/RUN-PARADE.md` §4b); the vault's other definitions load closed but what
  they draw is unrecorded, and the picker says `unwatched` on them.
- That the client honours the secondary anywhere but the three readouts U1 names.
