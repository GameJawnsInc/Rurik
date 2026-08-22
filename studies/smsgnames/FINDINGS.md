# Naming the seen-but-unnamed GAME_SMSG opcodes: a static reachable-handler pass

**Status: OBSERVED / CORROBORATED, 2026-08-18.** Build 38797 (`vault/client/2026-07-29_221c13772c7a/Gw.exe`). This pass takes the 116 GAME_SMSG opcodes ArenaNet has sent us (`vault/probes/smsgsweep-seen.txt`, 155 seen) that were **not** yet named in `schema/overrides.json`, scopes the ones with tractable handlers, and names them from two witnesses — the client's own handler code and the decoded wire — with an adversarial refutation pass and a consistency critic on top. No client was launched; no packet was injected. Every reading is static disassembly of a file plus already-captured live tapes.

Labels follow [studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

## 1. The answer in one page

- **33 opcodes** were in scope — the tractable subset of the 116 (real-file BODY handlers, real-file agent/item blocks, and the Array.h table-registration forwarders). All 116 are **reachable**: 63 FORWARDER + 53 BODY, zero NO_HANDLER, zero table-less. Reachability was never the filter; tractability was.
- **13 earned a name** (survived two witnesses + adversarial refutation + critic). **17 are PARTIAL** — mechanism understood, purpose not pinned, deliberately kept OUT of the schema. **3 are WITHHELD** — even the mechanism is not settled enough to characterise.
- **The 13 named opcodes were PROMOTED into `schema/overrides.json` on 2026-08-18** (GAME_SMSG went 66→79 named). All 16 affected tests stay green — including `test_agentlife.py` AXIS 3, whose pin count moved 9→12 because the three property opcodes it had *pre-registered by name* (0x009F/0x00A0/0x00A3) are now named exactly as it expected. [proposed_overrides.json](proposed_overrides.json) is the (now-merged) proposal record.
- **Follow-up 2026-08-18: three PARTIALs earned names** (GAME_SMSG 79→82), see §8: `0x009B AGENT_SET_NAME`, `0x00F3 TITLE_RANK_DATA`, `0x00F4 TITLE_RANK_DISPLAY`.
- **0x0027/0x002B resolution.** The critic flagged a naming inversion and suggested renaming the existing 0x002B `AGENT_UPDATE_SPEED` to `_MODIFIER`. That was declined: 0x002B's own overrides entry already **OBSERVED-refutes** the GWLP-R "SpeedModifier" gloss (its float is capped at 1.0, its byte is *facing* not type), and the client's asserts split the pair by their own words — 0x0027's float is `maxSpeed` (base/max, agent+0x5c), 0x002B's is `moveSpeed` (applied). So 0x002B stands unchanged and `_BASE` is the deliberate disambiguator. The rename would also have broken the test pin and the server constant. A UPSTREAM gloss the repo had already rejected nearly rode back in through the critic — caught before promotion.
- **The wins cluster by subsystem, exactly where `srvtree` said the Cli halves live:** the agent-movement family (`AgMsg.cpp`), the agent-property generic-value family (`ChCliApi`), and the item/inventory block (`ItCliApi.cpp`). Reading these handlers is reading the client half of subsystems whose server half we are reconstructing.

## 2. Method

1. **Scope by reachability + tractability.** `toolkit/clientscan/msghandler.py --classify` partitions every receive handler (FORWARDER vs BODY); `--map` and a one-level `--follow` name the source file each asserts in. Wire frequency came from `tape.decode_all` over 46 live connections in `vault/captures/live/` (105,894 GAME_SMSG messages; 34,710 on these 33).
2. **Two witnesses, name only where they agree.** Per opcode an evidence bundle carried the authoritative wire shape (`msgshape.py`, initializer-writes recovered — not the raw zero `cmds`), the decoded per-field value distributions, and the annotated handler disassembly (the client's own asserts and string refs). A name was proposed only where the code's behaviour and the wire's value ranges agreed, **and** reconciled against prior `studies/` analysis rather than re-derived.
3. **Adversarial refutation.** Every proposed name was handed to a second reader told to refute it — is a field constant/misread, is the name overreaching a forwarder, does a prior study contradict, is it really only PARTIAL. Verdicts: CONFIRMED / DOWNGRADE / REJECT, applied deterministically.
4. **Consistency + completeness critic** across all three clusters: name collisions with the existing schema, field-story conflicts between adjacent opcodes, and thin NAMEs / over-withheld PARTIALs.
5. **Independent field-width cross-check.** Every named opcode's agent-assigned field types were checked against `msgshape`'s authoritative shape — a check designed to refute. It caught one real error: the four item opcodes' first field (the *inventory key*) was labelled `u32` when the recovered initializer-writes say `u16`; the agents read the handler's dword register load and over-widened it. `proposed_overrides.json` carries the corrected `u16` and records the correction. The agent and property clusters matched exactly.

**Provenance.** Single asserts are cited as the evidence for a claim (a MEASUREMENT, `PLAN.md` §7 Q3); there are no bulk assert dumps. Nothing here is an ArenaNet asset. `messages.json` carries no UPSTREAM name for any SMSG opcode, so these names are ours, not OpenTyria's.

## 3. NAMED — earned a two-witness name (proposed for the schema)

| opcode | name | conf. | subsystem | basis (client word + wire) |
|---|---|---|---|---|
| 0x0027 | `AGENT_UPDATE_SPEED_BASE` | high | AgMsg.cpp | AgMsg:462 syncPtr / AgMsg:467 asyncPtr resolve the agent by id, then 0x602910 asserts AgAgent:2317 'maxSpeed >= 0' and does fstp [esi+0x5c] (store spe |
| 0x0028 | `AGENT_STOP_MOVING` | high | AgMsg.cpp | AgMsg:486 syncPtr / AgMsg:491 asyncPtr; 0x602540 tests flag 0x20000 (in-world/moving), clears the queued event at agent+0x50, asserts AgAgent:2211 'ti |
| 0x002A | `AGENT_UPDATE_DESTINATION` | high | AgMsg.cpp | AgMsg:535 'ptr'; 0x5fcec0 fires agint:929 pos.x>=worldDims.x0 / pos.y>=worldDims.y0 / <=x1 / <=y1 on the vec2 (proves it is a position, not a directio |
| 0x002C | `AGENT_UPDATE_POSITION` | high | AgMsg.cpp | AgMsg:579 syncPtr / AgMsg:584 asyncPtr; 0x5fcec0 worldDims asserts on the vec2; 0x605f70 clears the per-agent slot in the [esi+0x1cc] array; 0x602b20  |
| 0x005A | `PLAYER_REMOVE` | medium | ChCli/table | Handler 0x0091df00 -> 0x008101a0 ensures the array to index+1, reads player_record[N] first dword, if nonzero calls the agent-unlink 0x80ecf0, then fr |
| 0x009F | `AGENT_PROPERTY_UPDATE_INT` | medium | ChCli/table | Handler 0x0091ed00 -> shared worker 0x008128f0. ChCliApi:2112/2123 'sourceAgent < 5' names the worker's third arg (0 here). prop_id bounded by the cli |
| 0x00A0 | `AGENT_PROPERTY_UPDATE_INT_TARGET` | medium | ChCli/table | Handler 0x0091ed20 pushes field4,field3,field2,field1 into the shared worker 0x008128f0 (vs 0x009F's push of 0 for the source). Same +0x7c/0x34 array, |
| 0x00A2 | `AGENT_PROPERTY_UPDATE_FLOAT` | medium | ChCli/table | Handler 0x0091eda0 does `fld [msg+0xc]; fstp [esp]` (value is a float) then calls worker 0x00813040 -> float setter 0x00818210 with an fmul/x87 path.  |
| 0x00A3 | `AGENT_PROPERTY_UPDATE_FLOAT_TARGET` | medium | ChCli/table | Handler 0x0091edd0 `fld [msg+0x10]; fstp [esp]` then pushes field3,field2,field1 into 0x00813040 (float setter 0x00818210, AvApi:883 'agent' via 0x7df |
| 0x013E | `ITEM_ADD_TO_INVENTORY` | medium | ItCliApi.cpp | asserts empty destination slot, then writes item into inventory/bag[slot] and sets its INVENTORY flag |
| 0x0144 | `ITEM_STREAM_CREATE` | high | ItCliApi.cpp | registers a new inventory under field1 in inventoryTable; asserts the key is not already declared |
| 0x014B | `ITEM_CHANGE_LOCATION` | high | ItCliApi.cpp | removes item from its current bag/slot then adds it to the destination bag/slot (shared add-worker 0x849ea0) |
| 0x014D | `ITEM_REMOVE_FROM_INVENTORY` | medium | ItCliApi.cpp | asserts item has the INVENTORY flag, then removes it from its bag/slot and clears it from all equip sets |

Field semantics and full justification (with assert citations and the refuter's reasoning) are in [proposed_overrides.json](proposed_overrides.json).

## 4. PARTIAL — mechanism understood, name not earned (kept OUT of the schema)

These are not failures. Several carry a strong candidate name held back on discipline; naming them would embed an unpinned purpose. They are the best targets for a follow-up (a live probe, or reading fields 4+).

| opcode | candidate | subsystem | mechanism (OBSERVED) |
|---|---|---|---|
| 0x001F | — | AgMsg.cpp | Server pushes a single u32 time value; the handler rebases the agent subsystem's two timer queues (world context +0x18c and +0x128) by (value - last_base) and marks them  |
| 0x002D | — | AgMsg.cpp | Per-agent state cancel on a MOVING agent. field[1] is the agent id; the handler resolves sync (and, gated on a slot in the [esi+0x1ec] array, async) pointers and calls 0x |
| 0x003C | `PLAYER_UPDATE_FLAGS` | ChCli/table | Masked read-modify-write of a 3-bit flags word at player_record+0x34 in the ChCliApi player array (ctx+0x2c +0x80c, count +0x814, stride 0x50), keyed by playerId; fires e |
| 0x003E | `AGENT_REMOVE` | ChCli/table | Removes an agent (by id) from the client's by-id sorted agent list at ctx+0x2c +0x8c (binary-searched, entry memmoved out, count decremented) and detaches it from the mis |
| 0x005D | `CHAT_MESSAGE` → **EARNED 2026-08-19 as `CHAT_MESSAGE_CORE`** (studies/chat/FINDINGS.md — the sender/body cross-check ran offline; the whole family 0x005E/0x005F/0x0061 landed with it) | ChCli/table | Delivers an encoded (EncString) wide message string, appended to a growing string table at ctx+0x2c +4 (count +0xc); the same channel that carries level-up templates, /bo |
| 0x008D | `MAP_MARKER` | ChCli/table | Stores a 40-byte indexed marker record -- world position (vec2), two small ints, two file-id-shaped dwords and an 8-unit label -- into the marker table at ctx+0x2c +0x7ec |
| 0x009A | — | ChCli/table | Indexed store into the ChCli char/agent-by-id table (ctx+0x2c +0x7cc, count +0x7d4, stride 0x38): ensures the id exists, then writes field2 to record+0x30. The ensure run |
| 0x009B | `AGENT_SET_NAME` | ChCli/table | Stores an encoded wide string at record+0x34 in the ChCli char/agent-by-id table (ctx+0x2c +0x7cc, count +0x7d4, stride 0x38), keyed by agent id; compare-else-free-reallo |
| 0x00B0 | — | ChCli/table | Writes {owner=playerId, value=byte} into player_record+0x38 in the ChCliApi player array (ctx+0x2c +0x80c, stride 0x50) via 0x0081ed80, and fires event 0x10000048 once pe |
| 0x00F3 | `TITLE_RANK_DATA` | ChCli/table | Streams the title-rank vocabulary: an indexed store of {flag, threshold, name-string} into the title table at ctx+0x2c +0x82c, keyed by rank_id. Fixed record dwords at re |
| 0x00F4 | `TITLE_RANK_DISPLAY` | ChCli/table | Binds a displayed title-rank to a player: writes field2 (a rank id referencing the 0x00F3 table) to player_record+0x30 in the ChCliApi player array (ctx+0x2c +0x80c, stri |
| 0x013A | — | ItCliApi.cpp | Handler 0x00845e60 (ItCliApi:1828 item) wcslen's the trailing wide string, reallocates a buffer and stores it at item+0x18, then raises the item-refresh event via 0x848b7 |
| 0x0140 | — | ItCliApi.cpp | Handler 0x00846120 resolves an inventory (ItCliApi:1955) and calls 0x849fe0, which does `add [inventory+0x90], field2` (an accumulate, not a set) and raises event 0x10000 |
| 0x0147 | `ITEM_UPDATE_EQUIP_SET` | ItCliApi.cpp | Handler 0x008463c0 resolves two items (from fields 3 and 4) and an inventory (ItCliApi:2077), then calls 0x84a560 which asserts set < ITEM_PLAYER_EQUIP_SETS (ItCliInv:375 |
| 0x0148 | `ITEM_SET_ACTIVE_EQUIP_SET` | ItCliApi.cpp | Handler 0x00846450 resolves an inventory (ItCliApi:2095) and calls 0x84a340, which asserts set < ITEM_PLAYER_EQUIP_SETS (ItCliInv:329), and if inventory+0x84 differs from |
| 0x015E | `ITEM_LOW_DETAIL` | ItCliApi.cpp | Handler 0x00846fa0 asserts msg.fileId (ItCliApi:2410, guarding field2) then builds an item record via 0x848450: fileId->item+0x1c (masked 0x7fffffff), plus type/flag byte |
| 0x0161 | `ITEM_HIGH_DETAIL` | ItCliApi.cpp | Handler 0x00846d70 asserts msg.fileId (ItCliApi:2505) then runs the SAME item builder 0x848450 as 0x015E, followed by 0x848250 which installs the item's modifier code[] a |

## 5. WITHHELD — mechanism not settled

| opcode | subsystem | what we can say |
|---|---|---|
| 0x0104 | ChCli/table | On dispatch table 0x00bc9a18 (not the 0x00bc8f68 the rest share). Handler resets a [ctx+0x30] subsystem -- tearing down char-agent views (AvApi:103 charAgent iteration), zeroing tr |
| 0x0135 | ItCliApi.cpp | Handler 0x00845bb0 looks up an item (ItCliApi:1722 item, :1723 item->IsDetailHigh), unassigns any prior state via ItCliAssign (0x84b690), sets item flag 1, then builds/refreshes an |
| 0x015A | ItCliApi.cpp | Handler 0x00846b70 (ItCliApi:2314 item) is a one-line setter: it stores the field2 byte at item+0x4f. The same offset is initialised to 0xB (11) by the full-item builder 0x848450 ( |

## 6. Critic's items — what was applied at promotion, and what remains

Applied to the promoted entries on 2026-08-18: the **0x0027/0x002B resolution** (§1); **0x014D**
label CORROBORATED→OBSERVED; **0x009F** per-property provenance (41=energy is UPSTREAM, only
42=health OBSERVED live); and the **item field-width correction** (field1 u32→u16, from the
independent `msgshape` cross-check). The remaining items below are **non-blocking naming-vocabulary
notes**, not correctness problems, and none holds a name out of the schema.


- **0x0027** — Role/name adjacency with existing schema name AGENT_UPDATE_SPEED (0x002B). Per studies/movement/FINDINGS.md:745-747, 0x0027=P028 MovementSpeed (base, dword,float) and 0x002B=P032 SpeedModifier (dword,float,byte). Distinct roles, so not a hard duplicate, but the schema will then carry the plainer name AGENT_UPDATE_SPEED on the MODIFIER opcode and the suffixed AGENT_UPDATE_SPEED_BASE on the BASE opcode â€” specificity is inverted and a reader can easily conflate the two speed messages. Resolve the pair's naming (e.g. AGENT_UPDATE_SPEED->AGENT_UPDATE_SPEED_MODIFIER, or accept _BASE as the deliberate disambiguator) before promoting 0x0027.
- **0x003E** — Proposed name GAME_SMSG_AGENT_REMOVE collides in role with existing schema name WORLD_REMOVE_AGENT (0x0021). 0x003E only binary-search-deletes an entry from ONE by-id list (ctx+0x8c) and detaches the mission-map view â€” a view unlink, not the canonical despawn that WORLD_REMOVE_AGENT names. Mitigated because 0x003E is held PARTIAL/out-of-schema, but the name should be narrowed (e.g. AGENT_VIEW_UNLINK) so it never reads as the world-level remove.
- **0x002A, 0x0029** — 0x002A AGENT_UPDATE_DESTINATION uses the byte-identical goal-slot setter (+0x88..+0xa8) as the existing 0x0029 AGENT_MOVE_TO_POINT (the verdict states this explicitly), yet the two siblings get divergent verb vocabulary (MOVE_TO_POINT vs UPDATE_DESTINATION). The real distinction is only 0x002A's extra followed-agent field5. Naming does not signal they are the same setter family; consider aligning the vocabulary.
- **0x00A0, 0x00A3** — The _TARGET suffix labels the variant that ADDS a cause/source agent, but field2 in the base opcodes 0x009F/0x00A2 is already named 'target agent' and field2 stays the target in 0x00A0/0x00A3. So the suffix that semantically means '+source/cause' reads as '_TARGET', conflicting with the family's own field vocabulary. Follows upstream 'GenericValueTarget' so defensible, but flag the internal inconsistency.
- 0x014D GAME_SMSG_ITEM_REMOVE_FROM_INVENTORY is labeled CORROBORATED but has only ONE semantic witness. The wire (inventory key + item id, same domain as 0x014B) confirms field identities, not the 'remove' operation, and there is NO upstream name (reconstruction:2298 lists it unnamed). The refuter itself says the label should be OBSERVED. Binary is decisive, so the name is earned and it is promotable, but the CORROBORATED label overstates the basis â€” downgrade to OBSERVED; it is the thinnest NAME in the promote set.
- 0x005A GAME_SMSG_PLAYER_REMOVE has no naming assert, no live confirmation, and a playerId-only wire. Its 'two witnesses' are really the decisive binary teardown (free name string via 0x80bba0 + agent-unlink via 0x80ecf0) plus a structural-inverse-of-0x0059 argument and a passing mention (smsg:410). Defensible as the inverse of the CONFIRMED 0x0059 PLAYER_INFO, but medium confidence is at the generous edge; note the single independent semantic witness.
- 0x00A2 GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT is the only one of the four property opcodes with NO opcode-specific live confirmation (0x009F, 0x00A0, 0x00A3 each have a live crash probe). It rests on the distinct binary float path (fld/fstp -> 0x818210) plus the wire float distribution. Two witnesses hold and it is promotable, but it lands on shape+binary rather than a live probe â€” the weakest-confirmed of the promoted property family.
- Under-named-but-supportable: 0x015E ITEM_LOW_DETAIL and 0x0161 ITEM_HIGH_DETAIL carry a genuine two-witness MESSAGE identity (this pass + prior smsg/FINDINGS, fileId SOURCED at ItCliApi:2410 / :2505) and are held PARTIAL only because fields 4-10 are unread â€” the message meaning is well supported even where the field layout is not. If the schema admits message-level names with partial layouts (several existing PARTIAL-mechanism entries do), these two are the strongest withheld candidates for a message-only name. Also: 0x0161's field indices are off-by-one vs msgshape (name is wire field12 string16(64), code[] is field13 nested, not 11/12) and must be corrected before any promotion.
- 0x009F field comment marks 41=energy as OBSERVED, but the refuter notes 41=energy is UPSTREAM (only 42=health was OBSERVED live). Fix the provenance label on the per-property enum before promotion.

**Critic's promote set (survived as NAME, no schema-name collision):** 0x0144, 0x014B, 0x013E, 0x002A, 0x002C, 0x0028, 0x0027, 0x009F, 0x00A0, 0x00A2, 0x00A3, 0x005A, 0x014D.

## 7. Reproduction

Scoping, evidence bundles and the naming workflow are scripted under the session scratchpad (`scope.py`, `gather.py`, `wf_naming.js`). The bundles are self-contained (shape + wire + annotated disassembly + prior-work pointers). Re-derive the scope with `msghandler.py --classify` and the frequency with `tape.decode_all` over `vault/captures/live/`.

## 8. Follow-up: three PARTIALs earned names (2026-08-18)

Worked the strongest withheld candidates. All three were already characterised across prior
studies but held short of a schema name; each was earned by supplying the missing witness.

**0x009B `AGENT_SET_NAME` [medium].** Reconciliation, not new work. `smsg/FINDINGS.md:1013`
proposed the name with the store mechanism SOURCED (per-agent-by-id array, record+0x34, stride
0x38) but field 2's *meaning* only INFERRED. `newopcodes/FINDINGS.md:511` supplied the second
witness: field 2's string is OBSERVED byte-identical to the agent's name, and player names arrive
instead as literal text via 0x017D — so 0x009B is the encoded (.dat-string) name path for
NPCs/agents. Two witnesses now agree; promoted.

**0x00F3 `TITLE_RANK_DATA` / 0x00F4 `TITLE_RANK_DISPLAY` [medium].** These were the repo's
canonical UPSTREAM case — `STORAGE.md:175` ("UPSTREAM on names throughout; no observation
anywhere"), `newopcodes:836` ("UPSTREAM-plus-shape, not independently confirmed"), and even GWCA
binds the title structs to the *siblings* 0x00F5/0x00F6, not these. The missing witness was
0x00F4's UI consumer, left explicitly unread at `RUNS.md:203`. Found it via the frame bus:

- 0x00F4's body posts frame `0x10000064`; its **sole subscriber** is a CtlText UI panel
  (`fn 0x008aa080`).
- That same panel **also** subscribes to `0x10000065` — the frame posted by **0x00F5
  `TITLE_UPDATE`** (0x00F5 handler → callee `0x00814f60`, which posts `0x10000065`; 0x00F5 is a
  schema-confirmed title opcode at HIGH confidence).
- So 0x00F4 drives the **same UI panel as the confirmed title opcode** — an independent,
  binary-derived witness (not the mirror) that 0x00F4 is title display. `STORAGE.md:201` adds the
  wire behaviour: 0x00F4 ×215 in towns, binding *other* players to rank records — the signature of
  a title rendered under other players' nameplates.
- 0x00F3 is the rank-definition vocabulary {flags, threshold, coded-name} keyed by rank_id that
  0x00F4 indexes; the displayed name is 0x00F3's own string (`RUNS.md:192`).

This **elevates 0x00F3/0x00F4 from UPSTREAM to OBSERVED** and closes the open lead at `RUNS.md:203`.
Tool: `toolkit/clientscan/framebus.py`'s post/subscribe scan (POST 0x00633D70 / SUBSCRIBE
0x00633BD0), extended to arbitrary frame ids. Confidence is medium, not high: the shared-panel
chain and town-binding wire are strong, but the panel's exact per-frame scope carries some inference.

## 9. Follow-up: five more PARTIALs earned names (2026-08-22)

Worked §4's remaining priced items — the item-detail pair, the equip-set pair, and
`0x009A` — by reading the code the 2026-08-18 pass had priced but not read. GAME_SMSG
named entries 115 → 120. No client launched; every reading is static disassembly of
the pinned 38797 build plus the live corpus (now 4,210 / 2,235 / 236 / 59 / 965
messages on the five opcodes). Wire invariants that can take each name back are
pinned by `toolkit/authsrv/test_itemdetail.py` (19 checks); the field detail lives in
each opcode's `schema/overrides.json` why. What the reads found, beyond the names:

**`0x015E ITEM_LOW_DETAIL` / `0x0161 ITEM_HIGH_DETAIL` [medium/high].** The split IS
the client's own vocabulary: the shared builder `0x848450` consumes fields 1–9 (the
complete `0x015E` payload — fileId masked `0x7FFFFFFF` → +0x1C, type → +0x20, f4 →
+0x21, f5 → +0x22, f6−1 → +0x48 word (default 0x5DD when f6=0) with f7 → +0x4A, flags
→ +0x28, value → +0x24), while `0x0161`'s installer `0x848250` adds model_id → +0x2C,
quantity → +0x4C, the name (wire field TWELVE) → +0x34, code[] (field THIRTEEN) →
+0x10, and then sets `[item+0x40] |= 2` — the bit `test byte [item+0x40], 2` reads
under the assert `baseItem->IsDetailHigh()` (ItCliApi:66, `0x0084816B`). The critic's
off-by-one (name/code as fields 11/12) is corrected in the promoted entries. Three
sharp edges for our own sender: the code[] must arrive WITHOUT its terminator —
ItemCode:516 asserts `!count || code[count - 1] != ITEM_CODE_TERMINATOR` and the
client appends its own `0xC0000000` (prediction passed with no free parameter: 0
terminators in 6,806 corpus code words); declared field 14 never arrives (0 of 2,235
— the format table declares a slot retail never fills, settling `studies/smsg`'s open
question); and the fileId TOP BIT is a deferred-fetch request (`0x84be50`) that rides
only the high-detail stream (697/2,235 vs 0/4,210).

**`0x0147 ITEM_UPDATE_EQUIP_SET` / `0x0148 ITEM_SET_ACTIVE_EQUIP_SET` [high/high].**
`ITEM_PLAYER_EQUIP_SETS = 4` (both workers `cmp` against the literal under
`set < ITEM_PLAYER_EQUIP_SETS`, ItCliInv:375/:329). A set is a PAIR of item slots at
`inventory+0x64+set*8`; membership mirrors into a per-item bitmask at `item+0x4E`
(`!(setMask & ~ITEM_EQUIP_SET_MASK)`, ItCliInv:348); the active-set index lives at
`inventory+0x84`, change-detected, UI events 0x100000F0/0x100000E9. On the wire the
server streams the COMPLETE table: 236 updates = 59 × all four indices, plus one
active-set select each; 472/472 item refs null-or-declared, 295/295 inventory keys
declared. A-only pairs occur 17 times, B-only never (reported, not asserted).

**`0x009A AGENT_SET_MODEL_SCALE` [medium, name INFERRED].** Reconciled with
`studies/pvpui` FINDINGS §27, which had already identified the table, measured the
percent<<24 value shape over 38 connections, shown that the ensure runs BEFORE the
bounds check (one send REGISTERS an id — the `--hero-char` arm depends on that), and
found `GmAgentDoll`'s `CharBy` indexing the same table for the commander paperdoll;
its interim mechanism-name `GAME_SMSG_CHAR_TABLE_VALUE` stands grandfathered in
`authsrv.py`. What was missing was WHO READS `+0x30`, and the answer earns the
consumer-name: the `+0x30` consumer §4 asked for is the COMPOSITE pipeline. Getter `0x0080CD00` (ChCliApi:3804
`targetDef == GW_AGENTDEF_CHAR`) resolves the agent's char record — the message's key
is an agent id BY THE CLIENT'S OWN TYPING (msgshape recovers `[agent_id, u32]`) —
and falls back to the `0x0056`/`0x0057` definition record's slot +8 when the char
record is invalid. Caller `0x0082F520` (CpsMonster.cpp) takes the value >> 24,
multiplies by f32(0.01) from `.rdata 0x946e58`, and applies it to the composite
unless the byte is 100; `0x00831D30` (CpsTex.cpp) picks texture resolution from it
(`s_scaleR`). Wire: 965/965 values are a pure top-byte percent (low 24 bits zero),
span 8..115, 100 × 908 — town children at 43%, giants at 115%. **This also settles a
question another study priced at a client launch**: `studies/smsg` FINDINGS' 0x0056
row left "is field 4's 100/120/150 a scale percentage" open pending a
photograph-the-model probe; the ×0.01 on the composite answers it statically, and the
gw-preservation `scale` gloss (UPSTREAM at `studies/enemy/PLAN.md` §"dword 4") is now
CORROBORATED by the binary. Caveat carried in the entry: the definition-side sibling
dword packs hue/sat/lightness below the scale octet (UPSTREAM); retail has never sent
those bits on THIS message, and if one ever arrives, SCALE under-names the payload.

**Still held, and why:** `0x003C`/`0x00B0` (the player-record pair) and `0x008D`
(the marker store) — mechanisms in §4, consumers unread; nothing new this pass.
`0x003E`'s narrowing to a view-unlink name (critic §6) also remains open.
