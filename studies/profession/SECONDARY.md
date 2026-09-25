# The K panel's secondary-profession change — SECONDARY (2026-09-25)

**Identifiers.** `SECONDARY-F<n>` = findings, each labelled per
[studies/character/FINDINGS.md](../character/FINDINGS.md)'s vocabulary. `SECONDARY-B<n>`
= build steps, what the server does. `SECONDARY-R<n>` = runsheet steps, each with its
prediction registered before the run. `SECONDARY-Q<n>` = open questions. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**What this arc is.** The Skills and Attributes panel (K) carries a secondary-profession
drop-down. Our server never sent the message that populates it (`0x00B6`), never answered
the message a pick sends (`0x0041`), and carried a stale note saying both were retail
oddities confined to fifteen arena maps. Four read-only research angles (the repo, the
client, the tapes, the upstreams) were run on 2026-09-25 and this document is what they
found, labelled, plus the build that landed on them and the runsheet that will confirm it
on a client. The owner's decisions of 2026-09-25 bound the design: **(1)** the PRIMARY
stays a launch setting — no in-game primary change; **(2)** the drop-down offers ALL NINE
other professions by default (retail's PvP-character mask); **(3)** the skill list
behaves as retail's does — the server does NOT scope the library by profession, the
client filters once a secondary is set and shows every learned skill while it is none;
**(4)** heroes' secondaries change through the same message.

The pre-arc record is [RUNS.md](RUNS.md) §13–§14 (the `0x00B6` mechanism, read and run in
map 796 on 2026-08-13) and [FINDINGS.md](FINDINGS.md) §5 (the skill/attribute cross-tab);
this document supersedes §13's map caveat (SECONDARY-F3) and nothing else in them.

---

## 1. Findings

### SECONDARY-F1 — retail sends `0x00B6` on every load, and the values are two — OBSERVED

Census over `livewire.decode_conn` on all 96 origin=LIVE game connections in
`vault/captures/live/` (96 byte-closed, 0 not-ok). `0x00B6` AGENT_PROFESSION_BITS: **95
sightings on 95 of 95 connections that carry a character block**, once each, **for the
player's own agent only**, and **immediately after that agent's `0x00B7`** on all 95 (the
player's block opens `0x0037 → 0x00B7 → 0x00B6 → 0x00DA → 0x009F(41) → 0x009F(42) → 0x009C`
on every one of the nine variants). The 96th connection is an aborted load with no
character block and no `0x00B7` either (`20260807T133758` :54560). Heroes: `0x00B7 [hero,
1, 0, 0]` and **never a `0x00B6`** (4 of 4, all Koss on the PvE Ranger).

The value has exactly two forms. **0 on the PvE characters (45 connections).** **`0x7FF`
with the primary's bit cleared on the PvP characters**: `2045 = 0x7FD` on all 46 loads of
the Warrior "Jack Jawnson" (`0x00B7` primary 1) and `1919 = 0x77F` on all 4 of the Assassin
"Strikey Blikey" (primary 7). Bit 0 ("None") is set in both. `python -c "print(0x7FF &
~(1 << 1), 0x7FF & ~(1 << 7))"` → `2045 1919`. **The mask never changed within a
connection**, the one in-game secondary change (F2) included.

`0x00B7` AGENT_PROFESSIONS: 130 sightings — one per player load (95), one per hero load
(4), one per character-creation `0x0060` (25 of 25 echoing the request's profession as
field 2, `[agent, p, 0, 0]`), one in-game change (F2). **Field 4 (the trailing bool) is 1
on exactly the connections whose `0x00B6` is non-zero and whose login summary blob says
`is_pvp = 1`** — 46 + 4 rows of `(1, 0x7FD|0x77F, is_pvp 1, off-pair skills present)`,
27 rows of `(0, 0, is_pvp 0, none)`, 18 rows of `(0, 0, no blob on tape, none)` —
**CORROBORATED in pairing, NOT FOUND in meaning** (F6 reads its reader). Only two PvP and
six PvE characters are on tape, none of the PvE ones with a secondary unlocked, so "is a
PvP character" and "may change secondary" cannot be told apart from the wire.

`0x00A6` AGENT_SET_PROFESSION: 4,064 sightings (the 136 in `overrides.json`'s row 166 was
the first pass). **The player's own is NOT in the character block**: it arrives directly
after that player's `0x0059 → 0x00B0 → 0x00B1` (90 of 90 map connections), values always
equal to the player's `0x00B7` pair; four connections carry it three times because the
whole agent list was re-sent there. Our server's placement (right after the `0x00B7`)
stays: it has drawn the roster label since 2026-08-16 (RESKIN §14) and moving it is not
this arc's question.

Stale texts this refutes, corrected in the same commit: `schema/overrides.json` rows 182
and 183 ("never sent or captured"), row 166 ("136 messages"), `authsrv.py`'s `0x00B6`
comment and the `--secondary-bits` print and help ("11 of 11 samples carry mask 0",
"only in maps 796 and 823-836"), RUNS.md §13's "11 of 11" (annotated, kept),
`test_agentlife.py`'s detail line.

### SECONDARY-F2 — the pick sends `0x0041 [agent_id, u8]`, and retail answers it in one segment — OBSERVED (static, n=1 live)

**The sender, static on 38797.** GmDeckBuilder's frame proc `0x00500430`, case
`0x00500533..0x0050058D`: `cmp [ecx+8], 7` / `push [ecx+0xc]; push [ecx]; call 0x619120`
(the picked entry's stored value, a profession id the builder wrote per entry) / `push eax;
push [esi+4]; call 0x816d70`. `0x00816D70` is `jmp 0x920800`; `0x00920800` stores `0x41` and
two dwords and hands 12 bytes to the game framer `0x007DCF00` (`msgshape.py 0x0041`: SEND
table `0x00bc8cb8`, 7 B on the wire: `[agent_id u32, profession u8]`). The agent pushed is
`[esi+4]`, **the deck builder's own agent** (`0x0050057F`) — so a HERO's drop-down sends
the hero's agent id. `sendsites.py` on 38797: 214 sites, 0 unresolved; the API's only other
rel32 caller is the template loader `0x0058ADB0` (TemplatesHelpers:253
`TemplatesSkillsCanApply(targetAgentId, templateData, NULL)`, :258 `targetPrimaryProf ==
templateData.profPrimary`), which sends it when a loaded template's secondary differs and
is used (an attribute or one of its 8 skills belongs to it) after testing the secondary's
bit in the `0x00B6` mask (the `secondaryNotOwnedPvp` path). Which control's notification
(`[msg+8] == 7`) reaches the send is not pinned; the send itself is (SECONDARY-Q3).

**The witness, n=1.** `vault/captures/live/20260824T074002`, connection
`game-10.0.0.210_61329-to-52.23.107.149_80`, **map 248 Great Temple of Balthazar** (three
ways: `0x0199 [47, 248, …]`, `0x0099 [248, 0]`, the summary blob's outpost 248;
`content/partycap.toml:82`), a PvP Warrior (`0x00B7 [568, 1, 0, 1]`, `0x00B6 [568, 2045]`
at load). c2s `0x0041 [568, 4]` at 43.237 s (idx 1583), no NPC interaction or dialog c2s
since the load finished (the only c2s since 5.25 s was one `0x0009`). **44.35 ms later,
ONE TCP segment:** `0x00B7 [568, 1, 4, 1]` → `0x00A6 [568, 1, 4]` → `0x00DB` (30 dwords) → a
`0x001E` tick (idx 1594–1596, one wire timestamp). **No `0x00B6` re-send, no `0x0036..0x003B`
attribute message, no `0x00DA`/`0x00D9` bar message** within 3 s. **The `0x00DB` is
byte-identical to the load's** (`libs.py diff`: `+[] -[]`) — retail did not re-scope the
library; Necromancer skill 105 was already in it while the secondary was 0. 3.06 s later
the player equipped 105 (`0x005C [568, 5, 105, 0]` → `0x00D9 [568, 5, 105, 0]`). The
client's AUTH `0x0009` UPDATE_CHARACTER_SETTINGS left 9.09 s after the change, 0.2 s after
the `0x01A5` transfer, differing from the blob served at login only in **secondary 0 → 4**
(`authblob.py`, `charsummary.py`'s bits 10–13). The next map connection (:55771) loaded
`0x00B7 [25, 1, 4, 1]` with 105 on the bar: the change persisted server-side.

The old note — `test_dispatch.py`'s DROPPED_ON_PURPOSE row and `studies/cmsg/FINDINGS.md`'s
row ("followed by movement only"), `retail_c2s.json`'s `first_reply 0x001E` — was the
triage's first-reply column catching the tick at 4.4 ms. Both texts are corrected; the
census row is the census's own reading and is left.

### SECONDARY-F3 — there is no 15-map whitelist — CONTESTED, refuted on two legs

RUNS.md §13 said the drop-down builder self-gates on maps 796 and 823–836 and that
"which builder serves roleplaying characters is the largest open question". **(1)** F2's
witness used it in map 248, an ordinary outpost (areatable type 13, flags `0x8000`, not a
`0x40000`-flag arena). **(2)** The static re-read: the builder's `[obj+8] & 0x10` test is
the CREATE FLAG the Skills & Attributes window (AttribFrame) passes when it creates its
third GmDeckBuilder child, unconditionally, and nothing in GmDeckBuilder clears the bit.
**The enable rule is two gates and nothing else**: `0x00502543..0x00502568` `call 0x84d9b0;
test eax, eax; jne` (skip when non-zero) then `call 0x6190c0` (the entry count) `cmp eax, 2;
jb` → `call 0x631690(list, enable)`; `0x0084D9B0` is `call 0x47f660; mov eax, [eax+0x44]; mov
eax, [eax+0x238]`, and `0x0199`'s handler `0x0084EE40` stores msg+0xC to +0x238 — **our
`is_explorable`** (authsrv sends `[PLAYER_NUMBER, map_id, is_explorable, district, language,
is_observer]`). The `0x40000` area bit the whitelist most likely came from governs the
list's PvP-skill SUBSTITUTION (`0x0050258D`: a row's linked id at +0x2c replaces the id
unless it is `0xD73` or the row has flag `0x400000`; 248 flags `0x8000` type 13 does not
trigger it, 796 `0x04040003` and 823 `0x04840000` do), not the drop-down. Whether
AttribFrame's own CREATION is map-gated elsewhere was not traced (the K window opens on
every map in practice; SECONDARY-Q5). §14's run in 796 stands; it did not need 796.
Marked in RUNS.md §13, `probecharacter.py` and `serverargs.py`; nothing deleted.

**The entries** (builder `0x00502380`, OBSERVED static): from the per-agent PROFESSION
record (`ctx[+0x2C]+0x6BC`) — primary at +4 (`0x00816D10`), secondary at +8
(`0x00816D30`), the `0x00B6` mask at +0xC (`0x00816D50`); loop ids 0..10, add an entry iff
`id == current secondary` (`cmp eax, edi / je`) or (`id != 0` and `id != primary` and bit
`id` of the mask). An absent agent yields 11/11 and mask 0; the `0x00B7` CREATE path zeroes
the mask, an UPDATE keeps it (`0x0081FD95` on the creation path only). **A HERO's
drop-down ignores `0x00B6`**: with a hero-activation record (`0x005023B5 call 0x80e390`,
pvpui §29) the mask is replaced by `0x7FF` (`0x005023DE`) and the entry-string format
switches on heroData+0x1c. So with no `0x00B6` the player's list holds one entry and is
greyed; with 2045 it holds ten (None + nine).

### SECONDARY-F4 — the client filters the local player's skill list by the pair, and only when a secondary is set — OBSERVED (static 38797)

The list's refresh `0x00502580`, local-player path from `0x00502757`: `call 0x816d10`
(primary), `call 0x816d30` (secondary), then `call 0x816e50(&idx, &skill, &count)` — the
iterator over the CHARACTER store `charCtx[+0x2C]+0x700`: the `0x00DB` bitmap at +0x10
crossed with the `0x00DC` copies map at +0x20 (a set bit with no copies entry counts once,
`mov [eax], 1` at `0x0082185C`), asserting ChCliSkill:1022 `*skill` / :1036 `*copies`. It
does NOT consult the account set (`0x001D`) and does NOT consult the `0x815A80` flag.
**The filter**: `0x005027BA test esi, esi; je 0x5027d1` — **if the secondary is 0 the
profession test is skipped and every learned skill is listed**; else `0x005027BE mov al,
[eax+0x28]; test al, al; je post` (common, profession 0) / `cmp eax, [ebp-0x1c]; je post`
(primary) / `cmp eax, esi; jne skip` (secondary) — any other profession's skill is HIDDEN,
not greyed. Elite skills of the secondary are NOT excluded on this path (the exclusion at
`0x0050270D` sits on the other branch). This is why a Warrior spawned with secondary 0 and
the full 1,333-id corpus showed 43 attribute groups (RUNS.md Run 5) — no defect, the
client's own rule — and why the owner's decision (3) costs the server nothing: the list
narrows the moment a secondary is set.

The `0x815A80` bit (value 2) picks the ACCOUNT set vs the CHARACTER set **only for a
HERO's list** (`0x005029CB..` after the local-player split at `0x00502636`; the hero's own
skills at heroData+0x24 first, GmDeckBuilder:1275 `unlockedSkills`), filtered to profession
in {0, primary, secondary} and excluding rows with byte +0x2a != 0x30 or flags & 0x2080000.
skills §47.3's reading that this flag picks what the panel enumerates for the PLAYER was too
broad. Its writer is s2c `0x003C` PLAYER_UPDATE_FLAGS into player_record+0x34, clear on
every identifiable retail local player (deskwork PLAN item 5). Which events re-enumerate
the list: `0x1000004E` (posted by the `0x00B7` handler, agent must match), `0x1000005F`
(`0x00DB`'s, local player only), `0x100000C4` (`0x001D`'s, hero lists only), `0x1000005E`,
`0x100000C3` (with the area predicate `0x84dea0` = campaign 5, NOT FOUND what that names),
and the sealed-deck pair `0x10000061` / `0x1000019B`. The drop-down rebuilds on
`0x1000004D` (`0x00B6`) and `0x1000004E` (`0x00B7`). So the reply's `0x00B7` is what
re-labels the drop-down AND re-filters the list; the `0x00DB` re-send refreshes the list
a second time from an unchanged bitmap. `0x00A6` writes only the world agent's own copy
(`0x0091EE70 → 0x00813380 → 0x007DFFC0`, setter `0x7f7330` / deferred `0x7f73a0`); the
panel subscribes to no event from it.

**UPSTREAM, corroborating:** no server reimplementation filters server-side —
gw-preservation's `sendUnlockedSkills` sends an all-ones 128-word bitmap (verify-only
licence); OpenTyria and GWLP-R never join skills to professions; GWCA/GWToolbox never
touch the list. One witness each, none a fact about retail; F4 is the client's own bytes.

### SECONDARY-F5 — on `0x00B7` the client rebuilds the agent's attribute-id list itself — OBSERVED (static 38797)

`msghandler.py 0x00B7 --follow`: handler `0x0091F0B0 → 0x00813AE0`: `lea ecx, [edi+0x6bc];
call 0x81fd60` (the record upsert: lookup `0x81f920`, insert `0x81fae0` + `mov [esi+0xc],
0`, stores +0x10 (bool), +4, +8, posts `0x1000004E` at `0x0081FDAE`) then `lea ecx,
[edi+0xac]; call 0x819e60` (attribState, ChCliAttrib:435/442). `0x00819EA0` loops
`[attribState+0x424]` (count at +0x42c, 20-byte entries): for each attribute it takes the
profession (`0x5a9320`), asks whether the agent has it (`0x81fc60`), and — if it does and
(it is the primary's, or a non-primary attribute) and the profession's `s_profChapter` bit
(`0x5ab810`) is in the CHAPTER MASK — KEEPS the entry (`jne 0x81a02e`); otherwise it drops
the entry **only when the entry's +8 and +0xC are both zero** (`0x00819FC1 cmp [ecx+eax*4+8],
0; jne keep` / `0x00819FC8 cmp [..+0xc], 0; jne keep`), posting `0x1000002D {agent,
attrib}`. Then (`0x0081A036..`) it inserts the primary's attributes — **only if the primary's
chapter bit is in the mask** (`0x0081A056 test esi, edx / je 0x81a205`) — and the
secondary's non-primary attributes. **So the panel's rows for a NEW secondary appear with
no further message, and an OLD secondary's row that still carries a rank or points is
KEPT until the server zeroes it.** That is what SECONDARY-B3 is built on.

### SECONDARY-F6 — `0x00B7` field 4 selects a chapter-ownership mask; this server keeps sending 0 — OBSERVED (static 38797), UNVERIFIED what our account data yields

The bounded read this arc owed. The record's +0x10 has ONE getter, `0x0081FA60`
(`push [ebp+8]; call 0x81f9c0` (lookup); `mov eax, [eax+0x10]`; 0 for an absent agent),
beside the +4/+8/+0xC getters at `0x0081FA80/A0/C0`. `codescan --xrefs 0x0081FA60`: **one
direct rel32 caller, `0x00819EFE`** — inside the attribute-list rebuild above, on the
LOCAL-PLAYER branch only (`0x00819EF2 call 0x80d3e0; cmp esi, eax; jne` → other agents get
`[ebp-4] = 0xFFFFFFFF`, every chapter): `test al, 1; je` → **flag 1: `call 0x84d8d0`
(= `[ctx+0x44]+0x60`); flag 0: `call 0x84d800` (= `[ctx+0x44]+0x5C | +0x54`)**. Both caches are
filled lazily (when -1) by `0x00927690`, which walks a per-chapter table at `0xBCB568`
against two 64-bit account bitfields — `0x0048EF60(1)` and `0x0048EF30(1)`, the globals at
`0xC03330..0xC0334C` (the account's product/feature bits, set from the login/feature
stream) — masking `0x70003F`/`0x700`/`0x60000`/`3` per chapter and OR-ing chapter bits into
four outputs (+0x54, +0x58, +0x5C, +0x60). So **the flag chooses WHICH ownership mask
decides whether an attribute row is kept and whether the primary's attributes are inserted
at all** — flag 1 reads the narrower +0x60 alone. What this server's account stream leaves
in +0x60 is UNVERIFIED, and **an empty mask inserts no attribute for the primary** (F5's
`0x0081A056`). Retail pairs 1 with a non-zero `0x00B6` (F1), but every run to date — RUNS
§14's ungreyed drop-down included — has worked under 0, and the drop-down itself never
reads the flag (F3's builder reads +4, +8 and +0xC only). **Decision: keep 0**, say why at
the builder (`spawn_profession_values`), and leave flipping it to a labelled run
(SECONDARY-Q1) with the panel's attribute rows as the readout.

### SECONDARY-F7 — no in-world primary change exists, anywhere — NOT FOUND

The only c2s carrying a primary is `0x0060` CHAR_CREATE_SET_CHAPTER_PROFESSION (creation;
25 of 25 answered 31–52 ms later by `0x00B7 [agent, p, 0, 0]`, an empty `0x00DB`, then the
new profession's armour with `0x014D` removals before it on 10 of 25); the `0x0041` API
takes (agent, secondary) only; the drop-down skips the primary; the only writer of
record+4 is the `0x00B7` handler; 0 of 90 map connections change a primary. No mirror
(GWCA ×2, GWToolboxpp, GWLP-R, OpenTyria, gw-preservation) exposes one outside creation.
The owner's decision (1) matches the client.

### SECONDARY-F8 — the upstreams: agent-keyed, declared, never implemented — UPSTREAM

GWCA's `PlayerMgr::ChangeSecondProfession(profession, hero_index)` resolves the hero index
to an agent id and calls the in-process `0x00816D70` (found by the TemplatesHelpers assert
string) — agent-keyed for the player and any hero, one witness counted once (JaborGW's
copy is byte-identical). GWToolboxpp's `CompletionWindow::CheckAllSkills` calls it in a
bare loop over ids 1..10 with no unlocked check and says it "will trigger the ui message to
update the skills unlocked" — the `0x00B6` mask is a UI gate, not one inside the function.
OpenTyria declares `GAME_CMSG_CHANGE_SECOND_PROFESSION = 0x0041` with no struct and no
arm (its dispatch falls to the unhandled default); GWLP-R parses a `P058` of the same shape
and dispatches it nowhere; gw-preservation has no such inbound opcode. OpenTyria's own
`0x00B7` sender never fills the secondary field. None of them models the old secondary's
state on a change, so nothing here is copied from them.

---

## 2. The build — SECONDARY-B1..B5 (landed 2026-09-25)

**SECONDARY-B1 — the load.** `0x00B6 [player, mask]` on EVERY load, immediately after the
player's `0x00B7` (retail's adjacency, 95 of 95; it sat after the `0x00A6` under
`--secondary-bits` before), never for a hero. `load_secondary_offer()` is the three regimes
in one expression, used by the burst and by B2's refusal so the two cannot disagree:
`--secondary-bits N` → N (the override, as before); the feature on →
`secondary_offer_mask(SPAWN_PROFESSION)` = `0x7FF & ~(1 << primary)` (retail's PvP form,
2045/1919 OBSERVED; a custom primary past 10 gets `0x7FF`); `--no-secondary-change` → 0,
not sent. The `0x00B7` flag stays 0 (F6).

**SECONDARY-B2 — the change.** `GAME_CMSG_SET_SECONDARY_PROFESSION = 0x0041`, named in
`overrides.json` at medium (F2), off `test_dispatch`'s DROPPED_ON_PURPOSE, handled by
`handle_secondary_change`. Accepted when the agent is this connection's player or a hero
IN its party (a kicked hero has no panel); the instance is a town
(`instance_is_explorable(state)` — the `0x0199` field-3 expression, the client's own enable
gate, F3); and the profession is the CURRENT secondary (a no-op: the batch is answered,
nothing else moves) or is 1..10, not the primary (GmDeckBuilder:2321), and inside the mask
offered — `load_secondary_offer()` for the player, the client's own `0x7FF` minus the
primary for a hero (F3). **Anything else sends nothing and says why in the log —
RECONSTRUCTION, retail's refusal is unobserved.** The reply is retail's batch in retail's
order: `0x00B7 [agent, primary, new, 0]` → `0x00A6 [agent, primary, new]` → for the player
`0x00DB` (the character library exactly as the load resolves it — unchanged, as retail's
was); **for a hero `0x00B7` + `0x00A6` only**, because the hero's list re-enumerates on
`0x00B7`'s own event from heroData + the account set and `0x00DB`'s event is local-player
only (F4). No `0x00B6` re-send (retail: none; the record keeps its mask on an update).

**SECONDARY-B3 — the old secondary's state — RECONSTRUCTION** (retail's only witness
changed from none: nothing was on its bar or in its attributes, so both halves are built
on F5's rule, not on a tape). **(a)** Its attribute ranks are zeroed and their points
refunded through the live `AttributeState` (the same object the spend handlers mutate and
`persist_attributes` writes), and told to the client BEFORE the `0x00B7` so the rebuild
finds zero/zero and drops the rows: `0x0038 [agent, unspent]` then one `0x003B [agent,
attr, 0, effective]` per zeroed attribute — **the mid-session shapes retail sends for
every spend (14 of 14, pvpui §32)**. NOT `0x0037` + `0x003A`: `0x0037` is the CREATOR and
asserts `!attribState` (ChCliAttrib:313) on an agent that already has one (which is why
the hero KICK's `0x00F8` sweep must precede the ADD's block), and `0x003A` is the load's
BULK FILL that drains the pending-modifier queue and mints modifiers (pvpui §31.1). A gear
bonus on such an attribute keeps its row (F5's rule; effective is sent as the truth).
**(b)** Its skills leave the bar: `0x00D9 [agent, slot, 0, 0]` per slot, after the
`0x00DB` so the observed triple stays contiguous; the player's `SKILLBAR` and a hero's
session bar (`state["hero_bars"]`, the panel's and the body's one expression) and the store
follow; a hero's body casts the edited bar from then on (`sync_hero_body_bar`). A skill with
no content row on this machine (the bare-machine rule) stays and is named in the log.
Whether the client itself strips or refuses an old-secondary skill on the bar was not
traced (SECONDARY-Q2). `--no-secondary-cleanup` keeps both halves.

**SECONDARY-B4 — persistence.** `charstore`: an optional `secondary` (int 0..10, 0 = none)
on the character row and on each hero row, `STORE_VERSION` unbumped (the purse's precedent:
absent = never changed = today's bytes), `_validate_secondary` refusing 11, a bool, a
negative; `character_secondary` / `set_character_secondary` / `hero_secondary` /
`set_hero_secondary`; the CLI's `--secondary N` and `--hero-secondary N`; `CHAR_PROFESSIONS
= 11` mirrored from `agents` (test-checked). In `authsrv`, `player_secondary(state)` and
`hero_secondary(state, hid)` resolve once per connection — the session's value once a
change is accepted, else the STORED one under `--persist`, else the launch value — and feed
the load's `0x00B7`, the player's `0x00A6`, the hero block's `0x00B7`/`0x00A6`, the
`0x0073` HERO_INFO's field 4, and both attribute states. **Precedence: the stored value
WINS over `--spawn-secondary` / a `[party.KEY]` row's `player_secondary`**, the way a stored
`skillbar` wins over `--skills` and the persisted ranks win over the content row — the
launch value is the SEED a character starts from, the store is what the character has
since done. Under `--no-secondary-change` the store is NOT read (`--no-hero-kick`'s
precedent for a revert arm). A stored secondary equal to a MOVED launch primary is ignored
loudly (GmDeckBuilder:2321). The client's own AUTH `0x0009` push (F2) is absorbed by the
existing verbatim `update_settings` — VERIFIED in `test_secondary` §6: a `charsummary`
blob with secondary 4 stores as its own hex and decodes back to 4.

**SECONDARY-B5 — the master revert.** `--no-secondary-change`: no `0x00B6` unless
`--secondary-bits`, `0x0041` dropped with nothing sent and no state written, the store's
secondary not read — 57e89956's bytes, pinned against literals recorded from that tree
before any edit (`0x00B7 [1, 1, 0, 0]` / `[200, 7, 0, 0]`, `0x00A6 [1, 1, 0]`,
`SECONDARY_BITS 0`, no constant at `0x0041`).

---

## 3. The tests

`toolkit/authsrv/test_secondary.py` (108 checks, floor 108 from the green run; TESTS.md
has the section list). Every new guard was inverted in a SCRATCH COPY of `authsrv.py` —
the test's `RURIK_SECONDARY_AUTHSRV=<path>` hook loads that copy as `authsrv` with the
tree's siblings on the path — and shown to redden:

| mutation (scratch copy) | FAILs | what reddened |
|---|---|---|
| `load_secondary_offer()` returns 0 | 33 | §1 the default and the primary-following regimes, then every player change in §2–§6 refused as "outside the mask (0x0000)" — the burst and the handler share the expression, so breaking it breaks both |
| `instance_is_explorable()` returns False | 4 | §3 the `--explorable` and the map-146 preconditions and refusals |
| the `prof == primary` refusal removed | 2 | §3 the player's and §4 the hero's primary refusal (both fell through to the mask check with a different reason, which the label test caught) |
| the offered-mask test removed | 1 | §3 the out-of-mask refusal (4 accepted under `--secondary-bits 0x44`) |
| the attribute zeroing skipped | 9 | §5 the batch order, the refund, the `0x003B`, the live state, the capture row, the hero's batch and its values |
| the revert flag ignored (`if not SECONDARY_CHANGE_ENABLED` removed) | 1 | §7 the drop (the request reached the mask check instead) |
| the `0x00B6` block moved after the `0x00A6` (the pre-arc placement) | 2 | §1 the adjacency lock and the before-`0x00A6` lock |
| the store write skipped (`persisted = True` without writing) | 7 | §6 the row, the reopened store, the fresh connection's value and its `0x00B7`, the equal-pair guard, the rank round trip |
| the bar strip skipped | 6 (+ a traceback) | §5 the `0x00D9`, the bar, the capture row, the hero's batch and values; §6's hero part died on the missing session bar |
| the `0x00B7` flag set to 1 | 10 | §2 the `0x00B7` literal and the flag-by-decision check, §4 the hero's two, §6 the fresh connection's `0x00B7`, §7 both 57e89956 literals |

(The table is the sabotage run's own output, `scratchpad/impl-skillpanel/sabotage.txt`,
ten scratch copies, all ten exit 1 against a green 108-check baseline.)

The sweep after the edits: every test that imports or reads `authsrv.py`, `charstore.py`,
`serverargs.py`, `test_dispatch.py`, `test_agentlife.py`, `probecharacter.py` or
`overrides.json` as text — see the landing entry for the count.

---

## 4. The runsheet — SECONDARY-R1..R6 (the orchestrator runs these; predictions registered here)

Harness, loopback, the owner's sandbox spec or the slice; `K` opens the Skills and
Attributes panel; the drop-down's position needs ONE discovery screenshot on the first
run (the panel's top-right profession line; the harness can click/dclick/drag/hover at
window fractions). Watch the gamesrv log for the tags `[SECONDARY-B1]`, `[SECONDARY-B2]`,
`[SECONDARY-B3]`.

| step | what | prediction (registered before the run) |
|---|---|---|
| **R1** | an OUTPOST load (e.g. 148), `K` | gamesrv: `AGENT_PROFESSION_BITS(0x07FD) [default: all but the primary, SECONDARY-B1]` right after `AGENT_PROFESSIONS`; the drop-down is UNGREYED with **ten** entries (None + every profession but the primary), no crash, the attribute rows and skill list as before the arc (the flag is still 0) |
| **R1b** | pick Necromancer | gamesrv: `c2s 0x0041 [1, 4]` then `SECONDARY CHANGE (player): 1/0 -> 1/4 ... [SECONDARY-B2]` and the three sends `0x00B7`, `0x00A6`, `0x00DB`; **on screen without a reload**: the drop-down re-labels to Necromancer, the panel's skill list NARROWS to common + Warrior + Necromancer (F4: the filter arms the moment the secondary is non-zero), the attribute rows GAIN Blood/Curses/Death/Soul Reaping (F5: the rebuild inserts them; Soul Reaping's `+` is refused server-side as another profession's primary), the party roster's label reads `W/N` |
| **R2** | spend two points in Curses, drag a Necromancer skill onto the bar, pick Monk | gamesrv: `ATTRIBUTE_POINTS_AVAILABLE(... refunded ...)`, `AGENT_UPDATE_ATTRIBUTE(player attr N = 0) [SECONDARY-B3]`, the batch, `SKILLBAR_UPDATE_SKILL(player slot S: skill X of profession 4 leaves)`; on screen the Necromancer rows GO (F5: zero/zero at rebuild time), the points return to the pool, the slot empties, the list shows Warrior + Monk; the Warrior rows and skills untouched. **If the Necromancer rows LINGER** the `0x003B`-before-`0x00B7` order is wrong for the client (SECONDARY-Q4) — try the arm `--no-secondary-cleanup` to confirm it is the cleanup and not the batch |
| **R3** | relaunch the same character with `--persist` (the sandbox always does) | gamesrv: `AGENT_PROFESSIONS(prof 1/2)` at load, `AGENT_SET_PROFESSION(player, 1/2)`; the panel opens as W/Mo with the Monk rows and the narrowed list; `python toolkit/authsrv/charstore.py --account <email> --show` prints `secondary: 2`. To start over: `charstore.py --account <email> --character <name> --secondary 0` |
| **R4** | a hero's panel (`--party` with a hero; open the hero's K panel from its roster row), pick a secondary | gamesrv: `c2s 0x0041 [200, N]`, `SECONDARY CHANGE (hero 6): P/0 -> P/N` and TWO sends (`0x00B7`, `0x00A6`, no `0x00DB`); the hero's drop-down re-labels and its attribute rows gain N's; the hero roster label shows the pair. A pick with a rank in the old secondary follows R2's shape on the hero's agent |
| **R5** | the master revert: `--no-secondary-change` | gamesrv prints `NO SECONDARY CHANGE ...` at start; no `AGENT_PROFESSION_BITS` at load; the drop-down is GREYED with one entry; a pick is impossible (nothing to pick); `--secondary-bits 0x44` under the same flag ungreys it with three entries and a pick logs `SECONDARY CHANGE dropped (--no-secondary-change)` with nothing sent |
| **R6** | a FIELD (`--explorable` or map 146) | `AGENT_PROFESSION_BITS(0x07FD)` still at load (retail sends it in fields too); the drop-down is GREYED (the client's own field-3 gate); nothing to pick |

What would refute the build: R1's drop-down staying greyed with ten entries logged (the
`0x0199` field or the `0x00B6` ordering); R1b's list NOT narrowing (F4's filter read
wrongly); R2's rows lingering (Q4); any assert on `0x003B`/`0x0038` mid-session (then
`--no-secondary-cleanup` is the known-good arm and Q4 moves to a static read of
`0x00819B50`'s profession check).

---

## 5. Open — SECONDARY-Q1..Q6

- **Q1** — `0x00B7` field 4 on a client: with `--secondary-bits` unchanged, a one-line
  experiment sending 1 (F6 says what to watch: the attribute rows at panel open; if they
  vanish, +0x60 is empty on our account stream and the flag stays 0 for good).
- **Q2** — the bar on a change: does the client strip or refuse an old-secondary skill on
  its own (GmSkSlot / ChCliSkill)? Retail's witness had nothing on the bar to strip. R2
  answers the server-side half; the client-side half needs a `--no-secondary-cleanup` run
  with a Necromancer skill on the bar.
- **Q3** — which control's notification (`[msg+8] == 7`) reaches the `0x0041` send — the
  combo child (proc `0x0087E560`) or the templates child (`0x0058A780`); the send is pinned,
  its trigger is not.
- **Q4** — the order of the zeroing against the `0x00B7`: `0x003B` before the `0x00B7`
  (chosen: the attribute is still owned when written) versus after (would `0x00819B50`
  refuse an unowned attribute?) — R2 decides on screen; a static read of `0x00819B50`'s
  ownership check would settle it without a run.
- **Q5** — whether AttribFrame's CREATION is itself map-gated anywhere (the drop-down's
  builder is not); the K window opens on every map in practice.
- **Q6** — a PvE character with an unlocked secondary on tape: is retail's mask "unlocked
  minus primary", and is its flag 0 or 1? No such character is on tape; the owner's
  decision (2) makes it moot for this server.
