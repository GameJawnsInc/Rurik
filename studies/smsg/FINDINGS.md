# GAME_SMSG: what ArenaNet's server actually sends

**The corpus.** Capture `20260807T143055`, four chained live tapes from one session
(Lakeside -> Lakeside -> Ashford -> Lakeside), **10,944 GAME_SMSG messages** across
**146 distinct opcodes** of 487, framing 100% clean with **zero unconsumed bytes**.
The top 30 opcodes are **92%** of the whole stream. This is ArenaNet's own server
talking to ArenaNet's own client; nothing here is our reconstruction of it.

**The method, and why it can be trusted more than either half alone.** Two witnesses
that were not consulted to produce each other:

1. **The client's own words.** `msghandler.py` resolves an opcode to its dispatch
   function through the binary's `MsgFormatRecv` table -- a lookup, not a search --
   and `asserts.py` reads the **19,620 assert expressions** ArenaNet compiled into the
   shipping image as ASCII, each carrying its source file and line. `moveSpeed <=
   AGENT_MAX_MOVE_SPEED` is ArenaNet's sentence, not ours.
2. **The wire.** Value ranges, referential integrity, adjacency with the subject
   checked, and timing, over all 10,944 messages.

A name was only proposed where the two **agree**. That agreement is a real check
because the two sources can disagree, and on four occasions they did.

**Every proposal was then given to a second reader told to refute it.** That pass
struck four headline citations and two verdicts, and caught one **fabricated quote**
(see below). A single-pass version of this work would have shipped it.

## The ledger, stated before the results

| verdict | n | meaning |
|---|---|---|
| **NAMED** | 20 | in `schema/overrides.json` with a `name_confidence` |
| **PARTIAL** | 10 | mechanism understood, name not earned -- deliberately NOT in the schema |
| **UNRESOLVED** | 0 | -- |

**Zero UNRESOLVED is a warning sign, not a triumph**, and it is recorded here as one.
Thirty opcodes of a 487-opcode protocol came back with no complete failures; the honest
reading is that the 30 were chosen by corpus frequency, and frequent messages are the
ones with the most wire evidence and the most reachable handlers. It should not be
extrapolated to the remaining 116 opcodes in the corpus, let alone the 341 that never
appeared. Fifteen of the twenty are high confidence and five are medium.

**What the twenty rests on, so the number is not read as stronger than it is:**

- **13 of 20** have an assert naming a payload field or its destination *inside a
  function the handler reaches*.
- **3 of 20** rest on the wire plus a mechanism, with **no assert naming the quantity
  at all** -- `0x00A6`, `0x0048`, `0x00B1`. These are filed medium for that reason.
- **`0x000C`** names what the handler *does*; the message itself carries nothing.
- **Nine of the twenty confirm names our server already shipped.** Real value -- they
  move RECONSTRUCTION to CORROBORATED, and two overturn the upstream gloss -- but they
  are not nine new capabilities.
- **`0x0026` and `0x002E` are the only two that go from *unnamed and unsent* to *named
  and sendable*.**

**The caveat that bounds every count below.** Four tapes, **one** session, one
character, one account, two starting areas. "4/4 tapes" is four samples sharing a
character record. A second live capture on a different character separates protocol
from character in one decode, and it is the cheapest open test this pass produced.

**The checks live in [`toolkit/authsrv/test_smsgnames.py`](../../toolkit/authsrv/test_smsgnames.py)**
-- 21 wire invariants the corpus could have violated and did not. A name in a JSON
file is an assertion nothing can refute; that file is the half that can go red.

---

# 1. NAMED


## `0x001E` WORLD_SIMULATION_TICK  *[high]*

**3971 messages, 36.3% of the corpus.** Handler `0x005fcf70`.

Reached: `AgMsg.cpp`, `AgTimer.cpp`, `AgNotify.cpp`, `Agent.h`


**SOURCED** -- the client's own words:

- AgMsg.cpp:208 (VA 0x005fcf8b), guarding the handler's ONLY payload dword ([msg+4]): "(int)message.time >= 0" -- the client's own name for field 1 is message.time
- AgTimer.cpp:32 (VA 0x00603ff2), in the routine 0x00603fe0 that the handler passes that same dword to: "(int)elapsedMs >= 0" -- the parameter is named elapsedMs, so the unit is milliseconds
- AgTimer.cpp:36 "!m_advancing"; AgTimer.cpp:69 "(int)delay >= 0"; AgTimer.cpp:92 "repsAtTime < 0x1000" -- 0x00603fe0 walks a queue firing everything now due
- AgAgent.cpp:2211 "time == context->world[m_world].timerQueue.GetTime()" -- the queue is world-scoped, not per-agent

**OBSERVED** -- the wire:

- 3971 of 10944 messages (36.3%), the largest single opcode in the corpus; the handler takes no agent and the message has no agent field
- DECISIVE: per-tape sum(field1) vs wall-clock span of that tape -- 47761/47762 ms, 146890/146892 ms, 13268/13250 ms, 185390/185380 ms. Ratio 1.000, 1.000, 1.001, 1.000 on 4 of 4 tapes
- 3289 of 3967 consecutive pairs have |field1 - wall gap| <= 12 ms; 0 pairs off by more than 40 ms
- 445 distinct values, 1..520 ms. Most common: 20 (431x), 21 (201x), 1 (196x), 41 (70x), 40 (67x), 16 (59x), 500 (50x)

| field | meaning | label |
|---|---|---|
| 1 | elapsed milliseconds since the previous tick; the handler advances the world timer queue (agent context+0x128) by it, then measures a drift and, if the drift is below -10000 ms or above +1000 ms, catches a SECOND timer queue (+0x18c) up to it | SOURCED |

**Why this and not the nearest rival.** The client names the field twice: message.time where it arrives (AgMsg.cpp:208) and elapsedMs where it is consumed (AgTimer.cpp:32). The wire then agrees to 0.1% on four independent tapes -- summing field1 over a tape reconstructs that tape's wall-clock duration, which is a property no other reading of a one-dword message produces. Nearest rival: HEARTBEAT / KEEP_ALIVE / PING, and it is what 36% of a corpus tempts you to assume. Rejected because the payload is CONSUMED, not echoed or ignored: it drives a timer queue that fires due callbacks, and its running sum is wall-clock time. Second rival: an absolute server clock -- rejected because the values are 1..520 and it is their SUM, not the values, that tracks the clock. Third rival: a per-agent tick -- rejected because there is no agent field and the handler is world-scoped (AgAgent.cpp:2211 names context->world[..].timerQueue). Name: WORLD_SIMULATION_TICK is already in authsrv.py:183 on UPSTREAM authority and this promotes it to CORROBORATED; the only thing wrong with it is that 'tick' implies a fixed cadence the wire refutes (445 distinct deltas), so if the repo ever renames, the client's own vocabulary renders it WORLD_ADVANCE_TIME.

**Ruled out:** HEARTBEAT / KEEP_ALIVE / PING -- the dword is fed into a timer advance whose callbacks fire, not echoed back or discarded; absolute server time -- max value is 520 and the running sum, not the value, equals wall clock; per-agent timer -- no agent field, no agent lookup in the handler; a sequence number -- 445 distinct values that repeat heavily (20 appears 431 times) and are not monotonic

**Still open:** What the drift the handler measures actually is: eax = [ctx+0x148] - [ctx+0x1ac], with hard thresholds -10000 ms (fast-forward the second queue by 0x7FFFFFFF) and +1000 ms (advance it by the drift). The two queues are almost certainly the sync and async worlds that AgMsg's syncPtr/asyncPtr asserts name, but nothing SOURCED says so.; Whether the client requires this message to animate between destination updates. The movement study lists it as never sent by our server; that experiment is still unrun.

**For our server:** Our server has never sent the single most common message on the wire; sending a true elapsed-ms delta at our own cadence is the missing driver for every client-side timer and interpolation between movement legs.


> **Refutation pass.** Re-resolved the handler myself: `msghandler.py 0x001E --follow --annotate` gives RECV table 0x00a52d70, handler 0x005fcf70 — as claimed. Both load-bearing asserts exist verbatim at the claimed VAs and lines and both genuinely reach the payload: AgMsg:208 "(int)message.time >= 0" at 0x005fcf8b guards [edi+4], and [edi+4] is the ONLY payload dword the handler reads (verified: no other [edi+n] access in the whole function); the handler then passes exactly that dword to 0x00603fe0, whose own entry assert at 0x00603ff2 is AgTimer:32 "(int)elapsedMs >= 0" — so the identifier naming the parameter is on the callee that receives this field, not on some bystander. AgTimer:36/:69/:92 confirmed at 0x006


## `0x0029` AGENT_MOVE_TO_POINT  *[high]*

**987 messages, 9.0% of the corpus.** Handler `0x005fd890`.

Reached: `AgMsg.cpp`, `agint.h`, `AgAgent.cpp`


**SOURCED** -- the client's own words:

- agint.h:929, applied by 0x005fcec0 to field 2 before anything else happens: "pos.x >= worldDims.x0", "pos.y >= worldDims.y0", "pos.x <= worldDims.x1", "pos.y <= worldDims.y1" -- field 2 is a world POSITION and the client says so in four asserts
- AgMsg.cpp:513 "ptr" -- field 1 is bounds-checked (Array.h:587 "index < m_count") against the agent array and the resulting pointer asserted non-null
- AgAgent.cpp:2334 "m_flags & INTERNAL_FLAG_IN_WORLD" in the setter 0x00602a40 the handler calls

**OBSERVED** -- the wire:

- 987 messages. |field2| ranges 1119..21551 world units, components -19314..12110; 0 of 987 are unit-length. The contrast with 0x0025 (201 of 201 unit-length) is the position/direction discriminator, measured rather than assumed
- field 3 takes {0,18,19,22,52,53}, field 4 takes {0,19,22,47,52,53}; they are EQUAL in 973 of 987, and both are 0 in about 90% -- consistent with plane ids on a mostly single-plane map
- Sequence: 160 of 163 0x002B are immediately followed by 0x0029; 0x0025 is followed by 0x0029 152 times. The movement triple on the wire is [0x0025 direction] -> [0x002B speed+facing] -> 0x0029 destination
- 0x002B and 0x0029 share their agent-id space completely (every id seen in 0x002B also appears in 0x0029)

| field | meaning | label |
|---|---|---|
| 1 | agent -- an index into the client's agent array, bounds-checked then null-checked | SOURCED |
| 2 | destination position (x, y) in world units | SOURCED |
| 3 | the DESTINATION's plane; packed into the point struct beside x and y and travels with the point (agent+0x88..0x94) | SOURCED |
| 4 | the AGENT'S CURRENT plane; written to agent+0x80 unless it is -1, which the wire cannot express | SOURCED |

**Why this and not the nearest rival.** THE BINARY AGREES WITH OUR SERVER, loudly and in full. This was checked, not assumed: the handler builds {x,y,plane,0} from fields 2 and 3, hands it to 0x00602a40 with field 4 as the third argument, and 0x00602a40 writes the point into the agent's goal slots and field 4 into agent+0x80. The four worldDims asserts settle that field 2 is a position and not a direction -- the exact confusion that would have made a rival name plausible. Nearest rival: 0x002A AGENT_UPDATE_DESTINATION, whose handler at 0x005fd930 calls the SAME setter and differs by one push -- 0x0029 hardcodes 0 for the argument that lands in agent+0x98, 0x002A supplies it from a fifth wire field. So the rival is a real message with the same shape plus one field, and the discriminator is the hardcoded zero, not the payload. Note that the study doc studies/movement/FINDINGS.md already carried this reading from the same binary; I re-derived it from the handler without consulting it first and it matched field for field, including the -1 sentinel being unreachable from the wire.

**Ruled out:** AGENT_UPDATE_DESTINATION (0x002A) -- same setter, but 0x0029's handler pushes a literal 0 where 0x002A passes a wire field; a direction / velocity message -- 0 of 987 vectors are unit-length and all four worldDims asserts fire on this field; (currentPlane, nextPlane) field order (GWLP-R) -- field 3 is the one packed into the point struct that travels to the destination, field 4 is the one written to the agent's own position record

**Still open:** Nothing new for the name. Still open from before: what agent+0x98 (0x002A's extra argument, hardcoded 0 here) does. The 14 of 987 messages where field 3 != field 4 are the ones worth a labelled run -- they are the plane transitions.

**For our server:** No change needed; this confirms the name and the field order the server already ships, and turns 'which reconstruction do we believe' into a repeatable command.


> **Refutation pass.** Handler re-resolved: 0x005fd890, as claimed. The four agint:929 asserts (pos.x >= worldDims.x0 / pos.y >= worldDims.y0 / pos.x <= worldDims.x1 / pos.y <= worldDims.y1) are real, at 0x005fcee0/0x005fcf06/0x005fcf2b/0x005fcf5a inside 0x005fcec0, and 0x005fcec0 is called by this handler at 0x005fd8aa with `lea eax,[edi+8]` — so they land on field 2 and only field 2 (the callee reads [edi] and [edi+4] of the pointer it is given, i.e. msg+8 and msg+0xc). AgMsg:513 "ptr" confirmed at 0x005fd8e0, guarding the array lookup of field 1. The setter chain reproduces field-for-field: handler builds {[edi+8], [edi+0xc], [edi+0x10], 0} on the stack, pushes [edi+0x14] as the third argument, calls 0x00602a40


## `0x0020` GAME_SMSG_WORLD_CREATE_AGENT  *[high]*

**527 messages, 4.8% of the corpus.** Handler `0x005FD080`.

Reached: `AgMsg.cpp`, `agint.h`, `AgAgent.cpp`


**SOURCED** -- the client's own words:

- AgMsg.cpp:252 "message.position != AGENT_INVALID_POSITION" (0x005FD0B0) -- the handler fld's [msg+0x14] and [msg+0x18] immediately before it
- AgMsg.cpp:270 -- the handler passes (file=AgMsg.cpp, line=270, size=0x134) to the tagged allocator at 0x0047F490 and builds a NEW 308-byte object; nothing is looked up
- agint.h:929 "pos.x >= worldDims.x0" / "pos.y >= worldDims.y0" / "pos.x <= worldDims.x1" / "pos.y <= worldDims.y1" -- the same two floats bounds-checked against the world
- AgMsg.cpp:295 "ptr->IsInWorld()" -- asserted on the freshly constructed object

**OBSERVED** -- the wire:

- 527 messages over 4 tapes (10,944 GAME_SMSG total); 187 are immediately preceded by 0x00F0 and 275 immediately followed by 0x006D -- the create burst
- field 3 (agentDef) is 1 on 472 of 527, and every one of those 472 carries a non-zero team token; the 55 with agentDef 2/3/4 carry team token 0. The client's enum and the wire partition the corpus the same way, zero exceptions
- field 12 takes exactly 5 non-zero values, all MSVC four-character constants: 'anim','band','mon1','nonc','play'. Joint with field 2's top nibble: 'play'->3 (130) and 2 (17); 'nonc'/'mon1'/'band'/'anim'->2 (325); zero token->0 (55/55)
- field 9 x field 12: 288.0 on 138 of 147 'play' creates (288 is Guild Wars' documented player run speed), 0.0 on 55 of 55 agentDef!=CHAR creates, 12.0 on 151 'mon1' creates (the burrowing worms)

| field | meaning | label |
|---|---|---|
| 0 | msg_header (opcode 0x0020) | OBSERVED |
| 1 | agent id -- the index into world[m_world].agentArray | SOURCED |
| 2 | model/definition selector handed to context->def[agentDef].classFactoryFunc; stored at agent+0x18. Top nibble is a class (0 when agentDef!=CHAR, 2 for NPC-side characters, 3 for players) | INFERRED |
| 3 | agentDef. GW_AGENTDEF_CHAR=1, GW_AGENTDEF_GADGET=2, GW_AGENTDEF_ITEM=4; bounds-checked < 9 | SOURCED |
| 4 | initial m_flags (agent+0x20 -- the offset AgAgent.cpp:2301 names m_flags). The same word 0x0026 rewrites | SOURCED |
| 5 | position (two float32) -- message.position | SOURCED |
| 6 | the plane/layer companion of field 5: the handler copies fields 5 and 6 into one 3-dword local and passes a pointer to it, matching the {position, plane} Point struct AgAgent asserts about | INFERRED |
| 7 | a second 2-float vector passed by pointer with NO plane companion -- direction-shaped, but nothing in the handler names it | UNVERIFIED |
| 8 | stored at agent+0xC4; values {1,4,9} | UNVERIFIED |
| 9 | a speed in units/second: 288.0 for players, 0.0 for non-character agents. AgAgent's vocabulary for the pair is maxSpeed (AgAgent:2317 "maxSpeed >= 0") and moveSpeed (AgAgent:2367 "moveSpeed <= AGENT_MAX_MOVE_SPEED") | INFERRED |
| 10 | a dimensionless speed multiplier <= 1.0; field9 x field10 is the effective speed | INFERRED |
| 11 | a float32 (client fld's it, catalog says dword). 12.0 on nearly every character agent; 0/10/20/30/50 on the non-character ones. Radius-shaped, but not named by any assert reached | UNVERIFIED |
| 12 | teamToken -- stored at agent+0xE8, which is what AgentGetTeamToken returns. Four-character code; the client compares it against the player's own playerTeamToken and against the literals 'anim' and {'nonc','nonn'} to derive the displayed allegiance | SOURCED |
| 13 | a float32 (client fld's it, catalog says dword); 0.0 in 527 of 527 | OBSERVED |
| 14 | a server timestamp: the handler rebases it against a local time origin at context+0x148 and clamps the result to >= 1 before passing it on | INFERRED |
| 15 | a second timestamp, put through the identical rebasing | INFERRED |
| 16 | passed through verbatim; not named | UNVERIFIED |
| 17 | passed through verbatim; always 0 on the wire | UNVERIFIED |
| 18 | a 2-float vector passed by pointer | UNVERIFIED |
| 19 | a 2-float vector copied with field 20 into one {x,y,plane} local -- a second Point | INFERRED |
| 20 | the plane companion of field 19 | INFERRED |
| 21 | passed verbatim; always 0 on the wire | UNVERIFIED |
| 22 | a 2-float vector copied with field 23 into one {x,y,plane} local -- a third Point | INFERRED |
| 23 | the plane companion of field 22 | INFERRED |

**Why this and not the nearest rival.** The handler allocates rather than looks up: `mov ecx,0x134; call 0x0047F490` with AgMsg.cpp and line 270 in the operand registers, then asserts the fresh object IsInWorld(). It runs the body twice with the array base advanced 0x64, which AgAgent.cpp:312 names as m_world 0 and 1. That settles create over the nearest rival, WORLD_UPDATE_AGENT / a state refresh: a refresh has no allocation site and would resolve an existing pointer, and this handler never does. The second rival, PLAYER_CREATE (0x0059), is ruled out because 55 of 527 carry agentDef 2/3/4 -- gadgets and ground items, not players. The existing repo name was imported from OpenTyria (UPSTREAM); it now stands on the client's own words and on the wire independently. On the batch's specific question -- field 12 -- the chain closes end to end: the creator writes it to agent+0xE8, AgApi's accessor at 0x005FC4F0 returns agent+0xE8, and ChCliBase.cpp:326 calls that accessor AgentGetTeamToken. So it is a teamToken, not an opaque allegiance constant: the client derives allegiance FROM it by comparing to playerTeamToken. The comparison I used to pin the field layout is field 5 (the position vec2 at msg+0x14) and no other -- that is the field the AgMsg:252 assert reads, and it anchors the whole 4-byte-slot mapping. I deliberately did not pair against fields 18/19/22, which are also vec2-shaped and would have produced a plausible-looking but unanchored map.

**Ruled out:** WORLD_UPDATE_AGENT / agent state refresh -- refuted by the tagged 0x134-byte allocation at AgMsg.cpp:270 and the absence of any lookup; PLAYER_CREATE / a player-only spawn -- refuted by 55 creates carrying agentDef 2/3/4; field 12 as an enumerated allegiance vocabulary -- refuted: 'band', 'mon1' and 'play' appear NOWHERE in the image as dword immediates; only 'nonc'/'nonn' (one 4-instruction predicate) and 'anim' (two compare sites) are literals, and everything else falls to the unrecognised branch; fields 11 and 13 as integers -- refuted: the handler fld's both

**Still open:** fields 7, 8, 16, 17, 18, 21 -- carried through the creator into members no assert names; which of fields 9/10 is ArenaNet's maxSpeed and which is moveSpeed; the AgAgent vocabulary has both but no assert reached ties either to a message field; field 11's meaning (radius is the shape, not a sourced claim); what fields 14/15 time -- only the rebasing is established

**For our server:** Our create_agent() can stop guessing four fields: field 3 must be 1 (GW_AGENTDEF_CHAR) for anything meant to behave as a character, field 4 is the m_flags word 0x0026 later rewrites, field 9 x field 10 is the effective move speed, and fields 11/13 are floats not ints.


> **Refutation pass.** Re-resolved handler: msghandler.py 0x0020 gives RECV table 0x00a52d70 -> handler 0x005fd080. Correct. Every quoted assert exists at the quoted file:line (asserts.py --file AgMsg, --grep worldDims/agentDef/agentArray/TeamToken): AgMsg:252 at 0x005fd0b0, AgMsg:295 at 0x005fd20a, agint:929 x4 at 0x005fd233-0x005fd2a5, AgAgent:180/181 at 0x005fe193/0x005fe1b4, ChCliBase:326 at 0x0081b2f8, ChCliApi:4047 / GdCliApi:430 / ItCliApi:614 all present. The AgMsg.cpp:270 allocation is real and is not an assert -- I read the bytes: 0x005fd121 push 0x10e; push 0xa52e58; xor edx,edx; mov ecx,0x134; call 0x47f490. Unconditional allocation of 308 bytes, no lookup. The two-world loop is real: 0x005fd2b7 inc eb


## `0x00F0` AGENT_INITIAL_STATUS  *[high]*

**472 messages, 4.3% of the corpus.** Handler `0x0091F810 (dispatch stub) -> 0x00814C30 (the work, ChCliApi.cpp)`.

Reached: `ChCliApi.cpp`, `ChCliInt.h`, `AvApi.cpp`, `AvChar.cpp`, `AgApi.cpp`


**SOURCED** -- the client's own words:

- ChCliInt.h:254 (0x00815830) 'IS_TRUE(m_status & CHAR_STATUS_DEAD)' -- compiled as `test byte ptr [edi + 0x10c], 0x10`. That one assert names the field the payload lands in (m_status, at char+0x10C) AND pins CHAR_STATUS_DEAD == 0x10.
- AvChar.cpp:8673 (0x007FDF83) '(status & CHAR_STATUS_DEAD) != m_dataVisible.TestStatus(CHAR_STATUS_DEAD)' -- compiled as `and esi,0x10 / and eax,0x10 / cmp` on a different object in a different source file. Second independent witness for 0x10, and it names the argument `status`.
- AvApi.cpp:1411 (0x007E0400) 'agent' -- the AgentView setter 0x007E03F0 that ONLY 0x00F0 reaches.
- Array.h:587 'index < m_count' at 0x00814C5F -- the per-agent record array (ctx+0x7C, stride 0x34) is grown to agentId+1 and indexed by the first payload field.

**OBSERVED** -- the wire:

- 472 of 10944 messages, 4 tapes; 187 distinct agents, 105 of them getting exactly one.
- 187/472 arrive BEFORE that agent's own WORLD_CREATE (0x0020), and all 187 are the message immediately preceding it. 0x00F1 does this 0/312 times. That asymmetry is the whole 'initial vs update' argument.
- 0/472 target an agent the tape never creates.
- Payload takes only three values across the whole corpus: 0x0000 (315), 0x1000 (153), 0x2000 (4). It NEVER carries 0x10 (CHAR_STATUS_DEAD) -- 0/472, while 0x00F1 does 3/312.

| field | meaning | label |
|---|---|---|
| 0 | msg_header, the opcode | OBSERVED |
| 1 | agent id. The handler grows the ChCli per-agent record array to this+1, indexes it at stride 0x34, and hands the same value to the AgApi agent lookup at 0x005FC380. Paired against 0x0020 FIELD 1 (the 1..725 agent-id space), NOT 0x0020 field 2 -- field 2 is 0x2000xxxx, a class-based NPC definition id, and pairing there would have looked plausible and been wrong. | OBSERVED |
| 2 | the character status word. Stored verbatim into m_status (char+0x10C), into the ChCli per-agent record's flags (+0x30 of the 0x34-byte CharPool triple), and into the AgentView. Bits are CHAR_STATUS_*; CHAR_STATUS_DEAD == 0x10; bit 0x1000 is the state a burrowing agent is created in; bit 0x100 was seen only on player agents. It is an assignment of the whole word, not an add/remove. | SOURCED |

**Why this and not the nearest rival.** 0x00F0 and 0x00F1 compile to byte-identical ChCliApi functions that differ in exactly one call, and both write ONE field: the character status word. So the pair is not two different payloads, it is one payload with two delivery semantics, and the name has to carry that. Which is which is settled twice over. Client side: 0x00F0's AgentView setter (0x007F79D0, reached from AvApi:1411) resets the visual pools whenever the new value has bit 0x10, with no regard to the old value, additionally maintains bit 3 of AvChar+0x15C from that bit and calls a further notifier -- a hard snap; 0x00F1's setter (0x007F7AD0, AvApi:1423) guards the same reset on `test byte ptr [eax+0x30], 0x10` against the OLD value, i.e. it only acts on a 0->1 edge, and does none of the extra work. They also queue different AvChar event codes (0x11 vs 0x12). Wire side: 0x00F0 is the only one of the two ever sent before its agent exists (187/472 vs 0/312), it is broad and shallow (187 agents, mostly once), 0x00F1 is narrow and deep (34 agents, one of them 42 times), and the burrow cycle runs create-with-0x00F0 then change-with-0x00F1. Nearest rival is the repo's own RECONSTRUCTION, AGENT_INITIAL_EFFECTS. I reject the noun, not the shape: the INITIAL/UPDATE split is exactly right and is now measured rather than assumed, but 'effects' is the wrong word for this field. ArenaNet's own identifier is m_status and the bit constants are CHAR_STATUS_*, in two unrelated source files. The client's effect subsystem is a different subsystem entirely -- GmEffect.cpp, ConstEffect.cpp, CTL_EFFECT_SKILL_FIRST, AvChar:2433 'effect->effectLink.IsLinked()' -- and neither handler reaches any of it at any depth I followed. The 'effects' reading came from OpenTyria's agent struct having a uint32 effects beside health and level, which is UPSTREAM, one witness, and not the client.

**Ruled out:** AGENT_INITIAL_EFFECTS / anything named for 'effects' -- the client calls this word m_status / CHAR_STATUS_*, and the handler never touches the effect subsystem.; 'sets a death flag' as the whole meaning -- 0x10 is one bit of a word carrying at least six others in this corpus (0x4, 0x100, 0x1000, 0x2000, 0x10000, 0x40000, 0x80000).; A per-agent effects LIST or add/remove message -- the handler stores a single dword whole; there is no accumulate path.

**Still open:** Names for the bits other than CHAR_STATUS_DEAD. 0x1000 is measured (created-with, cleared 2.00 s after create, re-set 2.00 s before remove, never on a player) but unnamed; 0x100 is player-only and makes the client call AgApi 0x005FC5C0(agentId, 0) on its rising edge; 0x2000, 0x4, 0x10000/0x40000/0x80000 have n<=4 each.; What AvChar event codes 0x11 and 0x12 do downstream -- the consumer switch was not located, so the *visual* difference between the snap and the edge form is inferred from the setters only.; Whether the ChCli record array (ctx+0x7C) and the AvChar record reached by 0x007F58A0 are the same allocation. Both take the write at +0x30; if they are one object the double write is harmless, if not there are two caches.

**For our server:** Lets the server spawn an agent already in a state -- send it immediately before WORLD_CREATE_AGENT -- instead of creating everything in state 0 and correcting after, which is the 472-message D2 gap and the only way to create something already burrowed or already dead.


> **Refutation pass.** Reproduced every load-bearing step and found the wire case is STRONGER than claimed. Ran: msghandler.py 0x00F0 -> table 0x00bc8f68 [RECV], handler 0x0091f810, which is `push [eax+8]; push [eax+4]; call 0x814c30` -- the cited chain, exactly. asserts.py --grep CHAR_STATUS_DEAD returns exactly 2 sites in the whole 19,620-site image, both quoted verbatim and at the claimed VAs (0x00815830 ChCliInt:254, 0x007fdf83 AvChar:8673). Disassembled 0x00815822 aligned: `test byte ptr [edi + 0x10c], 0x10 / jne / <assert ChCliInt:254 IS_TRUE(m_status & CHAR_STATUS_DEAD)>` -- so char+0x10C is m_status and CHAR_STATUS_DEAD == 0x10 is SOURCED, not inferred. Disassembled 0x00814C30: Array:587 'index < m_count' 


## `0x0021` GAME_SMSG_WORLD_REMOVE_AGENT  *[high]*

**416 messages, 3.8% of the corpus.** Handler `0x005FD2F0`.

Reached: `AgMsg.cpp`, `AgAgent.cpp`, `AgNotify.cpp`


**SOURCED** -- the client's own words:

- AgMsg.cpp:316 "ptr" (0x005FD33D) -- the array slot named by field 1 must be non-null, i.e. the agent must already exist
- Array.h:587 "index < m_count" -- field 1 is bounds-checked as an array index before the load
- AgAgent.cpp:804 "(*curr)->m_bindTarget == this" and AgAgent.cpp:815 "index < count" -- inside the routine the handler calls per world (0x005FF5A0): it walks every object bound to the agent, clears each one's m_bindTarget, frees the bind array, then removes the agent from its own bind target's list
- AgNotify.cpp:87 "agentPtr" -- the handler finishes by flushing the agent notify queue at context+0x94, the same tail 0x0020 and 0x0026 use

**OBSERVED** -- the wire:

- 416 messages; 416 of 416 name an id that 0x0020 created earlier in the same tape, and 0 name a never-created id or double-remove without an intervening create
- the handler runs its body exactly twice with the array base advanced 0x64 -- the same sync/async world pair 0x0020 populates and 0x0026 writes
- studies/tape T3's burrow measurement: the removal side is a lone 0x0021 in 134 of 134 cases, against a five-message burst on the create side

| field | meaning | label |
|---|---|---|
| 0 | msg_header (opcode 0x0021) | OBSERVED |
| 1 | agent id -- the index into both world agent arrays; the agent must exist | SOURCED |

**Why this and not the nearest rival.** The nearest rival is 'hide / make untargetable', which is what studies/tape T3 briefly proposed on finding the same id created 19+ times. That reading is refuted from both sides: the handler sets no visibility bit, it tears down the agent's bind graph in both worlds and flushes the notify queue, and the wire shows the id must be re-created by a full 0x0020 before it can be used again -- 416 of 416 removes target a live id and none double-removes. The second rival, 'stop movement', is refuted because the movement path lives behind different asserts (AgAgent:2309 "!IsMoving()") and this handler never touches m_targetPoint. The existing repo name is confirmed rather than changed. One honest limit: I read 0x005FF5A0 to its first ret and it unbinds and re-points but does not visibly call a destructor in that window, so 'the object is freed' is not something I proved -- 'the agent is torn down and its id becomes reusable' is.

**Ruled out:** agent hide / untargetable toggle -- no flag write, and a full re-create is required afterwards; stop movement -- the movement asserts are in a different handler and m_targetPoint is untouched; a per-frame despawn tick -- the payload is a single bounds-checked agent index and the client asserts the slot is occupied

**Still open:** whether the AgAgent object is destructed or pooled -- the routine's first ret is reached without a destructor call in view; what the floats it computes from agent+0x78/0x7C after the unbind are for

**For our server:** Already sent; no change. What is new is that the tear-down runs in BOTH worlds, so a server that removes and immediately re-creates the same id is doing exactly what ArenaNet does.


> **Refutation pass.** Handler re-resolved: 0x005fd2f0, correct. The whole body verified in the disassembly: mov ebx,2; lea esi,[eax+0xe8]; loop head 0x5fd310 bounds-checks field 1 against [esi+8] (Array:587 at 0x005fd320), loads [esi][idx], asserts non-null (AgMsg:316 at 0x005fd33d), calls 0x005ff5a0 per world, add esi,0x64; sub ebx,1; jne -- then lea ecx,[ctx+0x94]; call 0x603990. Inside 0x005ff5a0 the annotated dump shows AgAgent:804 '(*curr)->m_bindTarget == this' at 0x005ff5e2 and AgAgent:815 'index < count' at 0x005ff675; the notify flush contains AgNotify:87 at 0x00603a55 and :96 at 0x00603abe. Every assert quoted is real, at the quoted line, and genuinely reached. WIRE: I reproduce 416 of 416 removes namin


## `0x00F1` AGENT_UPDATE_STATUS  *[high]*

**312 messages, 2.9% of the corpus.** Handler `0x0091F830 (dispatch stub) -> 0x00814CC0 (the work, ChCliApi.cpp)`.

Reached: `ChCliApi.cpp`, `ChCliInt.h`, `AvApi.cpp`, `AvChar.cpp`, `AgApi.cpp`


**SOURCED** -- the client's own words:

- ChCliInt.h:254 (0x00815830) 'IS_TRUE(m_status & CHAR_STATUS_DEAD)' -- `test byte ptr [edi + 0x10c], 0x10`. Same field, same bit as 0x00F0.
- AvChar.cpp:8673 (0x007FDF83) '(status & CHAR_STATUS_DEAD) != m_dataVisible.TestStatus(CHAR_STATUS_DEAD)'.
- AvApi.cpp:1423 (0x007E0450) 'agent' -- the sibling setter 0x007E0440 that ONLY 0x00F1 reaches, 12 source lines after 0x00F0's.
- AgApi.cpp:980 '!(facing & ~AGENT_FACING_MASK)' and AgApi.cpp:736/780 'ptr' -- the AgApi setters the status-change path calls when bit 0x10 or bit 0x100 rises.

**OBSERVED** -- the wire:

- 312 of 10944 messages; only 34 distinct agents, but one of them 42 times, another 38, another 37 -- narrow and deep, the opposite profile to 0x00F0's 187-agents-mostly-once.
- 0/312 arrive before their agent's 0x0020 create. 3/312 target an agent this tape never created.
- Payload values: 0 (152), 0x10 (2), 0x14 (1), 0x100 (8), 0x1000 (144), 0x2000 (2), 0x60000 (2), 0xD0000 (1).
- Carries CHAR_STATUS_DEAD (0x10) 3 times; both 0->DEAD transitions were followed by that agent's 0x0021 removal. n is small, so this is corroboration, not proof.

| field | meaning | label |
|---|---|---|
| 0 | msg_header, the opcode | OBSERVED |
| 1 | agent id -- identical treatment to 0x00F0 field 1 (grows and indexes the same ChCli record array, feeds the same AgApi lookup). Paired against 0x0020 field 1, the agent-id space, not field 2. | OBSERVED |
| 2 | the same character status word as 0x00F0 field 2 -- m_status, CHAR_STATUS_* bits, CHAR_STATUS_DEAD == 0x10 -- assigned whole. The difference from 0x00F0 is not the payload, it is that the client treats this one as an edge: the AgentView reset fires only when bit 0x10 was clear before. | SOURCED |

**Why this and not the nearest rival.** Same evidence base as 0x00F0; the two must be named as a pair because they write one field. 0x00F1 is the update/edge form: its AgentView setter guards on the old value, it never precedes a create, and it is the message that carries every later change including death (0x10) and both burrow transitions. Nearest rival is the repo's existing AGENT_UPDATE_EFFECTS -- I keep UPDATE and reject EFFECTS, for the reason given under 0x00F0: the client's own name for this word is m_status and its constants are CHAR_STATUS_*, quoted in two unrelated files, while the effect subsystem (GmEffect.cpp, ConstEffect.cpp, AvChar's effect list) is never reached. The second rival was 'these are two different fields' -- rejected by disassembly: 0x00814C30 and 0x00814CC0 are instruction-for-instruction identical apart from one call target, and both funnel into the same char+0x10C write via 0x0081C020. Worth recording that the repo's own probe result (studies/agentprops: sending 0x00F1 with 0x10 kills an agent, clearing it revives) is now independently SOURCED from the client's assert text -- a live-client experiment and a compiled assert agreeing is the strong form of this check.

**Ruled out:** AGENT_UPDATE_EFFECTS -- wrong noun, see reasoning.; A death message. It is a state word, and death is one bit in it; naming the message for the bit would mis-describe the other 309 of 312 messages in this corpus.; INSTANCE_LOADED (gw-preservation assigns 0x00F1 that meaning, noted in studies/character/FINDINGS.md:954) -- refuted: the handler is a per-agent ChCli status write and takes an agent id, and the wire shows 312 of them spread across a session on 34 different agents.

**Still open:** Bit names beyond DEAD; see 0x00F0. In particular 0x100 (player-only, stops the agent) and 0x1000 (the burrow-window bit the repo currently calls EFFECT_TRANSITION) are measured but unnamed.; The 3 messages targeting an agent never created on that tape -- probably created before capture start, not checked.; Whether clearing 0x10 alone restores anything (the repo's probe says no, health stays at ~0-1); the client's death path zeroes the CharPool interpolators, which is consistent, but I did not read the revive path far enough to say what else must follow.

**For our server:** We already send this one; knowing it is the EDGE form -- and that 0x00F0 is the snap -- is what makes the 2.00 s burrow cycle reproducible instead of approximated, and tells us bit 0x100 is for player agents only.


> **Refutation pass.** Same evidence base, independently re-run, and the wire half is cleanly complementary to 0x00F0. Ran msghandler.py 0x00F1 -> handler 0x0091f830 -> call 0x814cc0, as cited. AvApi:1423 'agent' is at 0x007E0450 inside 0x007E0440, 12 source lines after 0x00F0's, exactly as claimed; the setter it reaches, 0x007F7AD0, contains the literal `test byte ptr [eax + 0x30], 0x10` old-value guard the proposal describes, and does none of the AvChar+0x15C or extra-notifier work its sibling does. Both handlers funnel into 0x0081C020, which is the only writer of char+0x10C and computes `old XOR new` before assigning the whole word -- so 'assigned whole, with edge detection on bits 0x10 and 0x100' is right, and


## `0x0025` AGENT_MOVE_DIRECTION  *[high]*

**201 messages, 1.8% of the corpus.** Handler `0x005fd540`.

Reached: `AgMsg.cpp`


**SOURCED** -- the client's own words:

- AgMsg.cpp:412 "syncPtr" and AgMsg.cpp:418 "asyncPtr" -- this message is applied TWICE, once to the server-authoritative agent and once to the client's predicted copy, with the second application suppressed for one particular agent slot
- Array.h:587 "index < m_count" bounding field 1 against the agent array, twice
- The byte's name is not sourced from this handler. It comes from the sibling setter used by 0x002B: AgAgent.cpp:2368 "!(facing & ~AGENT_FACING_MASK)", compiled as `test edi, 0xfffffff0`, so AGENT_FACING_MASK = 0x0F
- HONEST GAP: the setter 0x00602660 contains no assert at all, so it names no source file. That is silence, not absence. It sits inside the address run whose neighbours all assert in AgAgent.cpp, which is why AgAgent.cpp is listed as INFERRED and not in source_files.

**OBSERVED** -- the wire:

- 201 messages. |field2| in [0.996546, 1.000000], every component inside [-1,1], 0 of 201 exactly 1.0 -- a near-unit DIRECTION vector. Against 0x0029's 1119..21551, this is the cleanest structural discriminator in the batch
- Pairing (field indices stated because this is where the project has been burned): 0x0025 field index 2 -- the only vec2, and the one the client copies to agent+0xbc/+0xc0 -- against the heading between two CONSECUTIVE 0x0029 field-index-2 POSITIONS for the SAME agent, one before and one after. 41/172 within 0.10 rad vs 149/3440 (4.3%) for a shuffled null; 51/172 within 0.25 rad vs 9.4% null. Real, 5.5x enrichment, and far from 1:1 because the chord between two destinations is a coarse proxy for the instantaneous heading
- facing byte values and counts: 1 (168), 3 (21), 4 (5), 2 (4), 8 (2), 7 (1). Never 9, which 0x002B does carry
- The byte's angle is NOT confirmed by the wire: rotating by the code-derived angle before pairing made the match slightly WORSE (35/172 vs 41/172), because 140 of the 172 usable samples are byte=1 whose rotation is 0. Reported as a negative rather than dressed up

| field | meaning | label |
|---|---|---|
| 1 | agent -- index into the agent array; applied to both the sync and async copies | SOURCED |
| 2 | unit direction vector; the client invalidates its cached heading angle (agent+0xb8 := the .rdata +inf at 0x00948654) and stores a fixed rotation of this vector at agent+0xbc/+0xc0, which is exactly the slot 0x002E reads back through atan2 | SOURCED |
| 3 | facing: selects one of 8 fixed rotations applied to field 2 before it is stored. 1 -> 0 deg, 2 -> -26.57 deg, 3 -> +26.57 deg, 4 -> 180 deg (exact vector negate), 5 -> -135 deg, 6 -> +135 deg, 7 -> -90 deg, 8 -> +90 deg. Anything else falls to the switch default and does nothing | OBSERVED |

**Why this and not the nearest rival.** The name was already ours and the binary keeps it, but the byte is now readable. 0x00602660 is a jump table of 8 cases (table at 0x00602860); each case invalidates the heading-angle cache and writes a rotation of the wire vector into agent+0xbc/+0xc0, built from Vec2Add (0x005350a0), Vec2Normalize (0x005351d0) and Vec2Negate (0x005fe8a0) -- all three disassembled rather than guessed from their call sites, per the operand-vs-data trap. Case 4 is a bare negate, i.e. exactly 180 degrees, and the movement study independently records from PLAY that holding S drives this message with 'movement type 4 (Backward)'. Two witnesses that could not have contaminated each other. Nearest rival name: AGENT_UPDATE_DIRECTION / AGENT_SET_HEADING, i.e. reading it as a pure facing update. Rejected because the vector is stored as the input to the MOVEMENT system and 0x002B, which sets moveSpeed, carries the same facing enum -- a heading-only message would not need the movement-type transform, and 44 of 201 are immediately followed by 0x002B. I keep MOVE_DIRECTION. The remaining oddity I cannot explain and will not paper over: cases 2 and 3 are +/-atan(1/2) = 26.57 degrees, not the 45 degrees a forward-diagonal would suggest.

**Ruled out:** a position update -- every vector is unit-length to within 0.0035; AGENT_UPDATE_ROTATION -- that is 0x002E, which writes different agent slots (+0xc8/+0xcc) and interpolates over time; this one snaps the heading vector; the byte as a 4-bit direction BITMASK (fwd/back/left/right) -- value 3 would then mean forward+backward, and the switch treats it as a dense 1..8 enum with a jump table

**Still open:** Which real-world input each of facing 2, 3, 5, 6 is. n = 4, 21, 0, 0 in this corpus. One labelled run with the operator told to hold W+D, W+A, S+D, S+A settles all four in a minute.; Why cases 2 and 3 rotate by atan(1/2) rather than 45 degrees.; The async-suppression condition: the second application is skipped when a 28-byte-stride record at [ctx+0x1ec] is non-zero for that index, or when the index equals [ctx+0x1e0]. The natural reading is 'do not overwrite the locally predicted player', but no assert says so.

**For our server:** The server currently echoes the client's byte back; knowing byte 4 is an exact 180 degrees and that the byte is `facing` means the server can drive backpedal and strafe facing deliberately -- and it explains why mixing held-S with clicks fights over one piece of agent state.


> **Refutation pass.** Handler re-resolved: 0x005fd540, as claimed. AgMsg:412 "syncPtr" (0x005fd582) and AgMsg:418 "asyncPtr" (0x005fd60c) are real and in this handler; the double application and its suppression condition ([esi+0x1ec] 28-byte stride non-zero, or index == [esi+0x1e0]) are as described. Both applications call 0x00602660 with `lea eax,[edi+8]` (field 2) and `push [edi+0x10]` (field 3). I read the jump table at 0x00602860 out of the image: 8 entries (0x60267d, 0x6026a4, 0x602704, 0x602767, 0x602784, 0x6027c9, 0x60280e, 0x602829), reached by `dec eax; cmp eax,7; ja default` — a dense 1..8 enum, so their bitmask rival is correctly ruled out. Wire re-measured on my own decode: 201 messages, |vec2| in [0.


## `0x002B` AGENT_UPDATE_SPEED  *[high]*

**163 messages, 1.5% of the corpus.** Handler `0x005fd9d0`.

Reached: `AgMsg.cpp`, `AgAgent.cpp`


**SOURCED** -- the client's own words:

- AgAgent.cpp:2366 (VA 0x006029b0), on the float the handler pushes from field 2: "moveSpeed >= AGENT_MIN_MOVE_SPEED"
- AgAgent.cpp:2367 "moveSpeed <= AGENT_MAX_MOVE_SPEED"
- AgAgent.cpp:2368, on the byte the handler pushes from field 3: "!(facing & ~AGENT_FACING_MASK)"
- AgAgent.cpp:2369 "m_flags & INTERNAL_FLAG_IN_WORLD"

**OBSERVED** -- the wire:

- 163 messages. moveSpeed min 0.277778, max 1.000000 -- 163 of 163 inside the client's OWN asserted bounds [0.01, 1.0], which is a check the corpus could have failed and did not
- 15 distinct speeds. 7 of them are exact multiples of 1/288 (0.277778, 0.3125, 0.333333, 0.347222, 0.416667, 0.75, 1.0 = 80, 90, 96, 100, 120, 216, 288 / 288); three more are exact hundredths (0.32, 0.40, 0.66); the rest (0.7245759, 0.7252440, 0.7369260, 0.8996372, 0.9987704) are irregular and look like products
- facing values {1,2,3,4,7,8,9}, all <= 15 as AGENT_FACING_MASK requires. facing=1 in 119 of 163 and carries all the varied creature speeds; facing=9 in 29 of 163 and carries speed exactly 1.0 every time
- 160 of 163 are immediately followed by 0x0029

| field | meaning | label |
|---|---|---|
| 1 | agent -- index into the agent array | SOURCED |
| 2 | moveSpeed, a normalised speed fraction in [0.01, 1.0]; stored at agent+0x60 | SOURCED |
| 3 | facing, 4 bits; stored at agent+0xc4 -- the same enum 0x0025 uses to rotate its direction vector | SOURCED |

**Why this and not the nearest rival.** Both payload names come out of the client's own asserts on the exact arguments the handler pushes, which is as direct as this project's evidence gets, and the wire then lands inside the bounds those asserts declare, 163 times out of 163. Nearest rival: the repo's current gloss 'agent, modifier, type' (from an upstream reconstruction) -- rejected on both words. It is not a MODIFIER: the client asserts it at or below 1.0, so it cannot carry a speed buff, and a 33% run enchantment could not be expressed. It is not a TYPE: the byte is `facing`, named in the assert immediately below the two speed asserts. Second rival: AGENT_MOVE_DIRECTION -- rejected because no direction vector is present; this setter writes only speed and facing. I keep the upstream-shaped name AGENT_UPDATE_SPEED because it is the incumbent and now corroborated; if the repo wants the second field visible the client's vocabulary gives AGENT_UPDATE_SPEED_FACING.

**Ruled out:** 'speed modifier' / multiplier -- AGENT_MAX_MOVE_SPEED = 1.0 caps it, so no buff above base speed can ride this field; the byte as a movement 'type' -- the client calls it `facing` and masks it to 4 bits; a per-skill or per-effect speed change -- the value is written straight to agent+0x60 with no accumulation and no duration

**Still open:** What facing = 9 means. It is legal under AGENT_FACING_MASK, it never appears in 0x0025, 0x0025's switch would ignore it, and all 29 occurrences carry speed exactly 1.0. Something distinguishes those 29 messages and I could not say what.; Whether moveSpeed is a fraction of a fixed 288 units/s. Seven of fifteen values are exact multiples of 1/288 and 288 is the commonly cited retail run speed, but that is UNVERIFIED here and I am not resting anything on it.; Whether flag 0x80000 is exactly 'moving by direction'. 0x002B sets it and 0x0029 clears it, which is suggestive and nothing more.

**For our server:** The server can now set an agent's move speed correctly bounded (a value above 1.0 will trip the client's own assert), which is the missing half of NPC patrol and chase pacing -- and it must send facing with it, not a 'type'.


> **Refutation pass.** The strongest of the five, and everything checks. Handler re-resolved: 0x005fd9d0. AgMsg:554 "ptr" confirmed at 0x005fda12. The handler pushes [ebx+0xc] (field 3) then fstp's [ebx+8] (field 2) into 0x00602990, so field 2 -> arg1, field 3 -> arg2. Inside 0x00602990 all four asserts are real, in order, on those exact arguments: AgAgent:2366 "moveSpeed >= AGENT_MIN_MOVE_SPEED" (0x006029b0) and AgAgent:2367 "moveSpeed <= AGENT_MAX_MOVE_SPEED" (0x006029d4) both on [ebp+8]; AgAgent:2368 "!(facing & ~AGENT_FACING_MASK)" (0x006029f3) on [ebp+0xc] via `test edi, 0xfffffff0`; AgAgent:2369 IN_WORLD. I read the constants out of the image myself: 0x00941148 = 0.009999999776482582 (AGENT_MIN_MOVE_SPEED), 


## `0x00B1` PLAYER_SET_PARTY  *[medium]*

**162 messages, 1.5% of the corpus.** Handler `0x0091f050`.

Reached: `ChCliApi.cpp`, `GmView.cpp`, `AvChar.cpp`, `AtName.cpp`


**SOURCED** -- the client's own words:

- ChCliApi:4966 `!(playerId & CHAR_CLASS_BASE_MASK)` — asserted on the register that, three instructions later, indexes the very array this handler writes (base ctx+0x80c, count ctx+0x814, stride 0x50). The index is called playerId in ArenaNet's own words.
- AtName:359 `msg.playerId == AvCharGetPlayerId(m_agent)` — the same array's rows are addressed by playerId in the name-plate module
- PtUtil:221 `leader` — the party module's word for the role this field points at
- Array:587 `index < m_count` guards every access, on the same array the player-add (0x0059) and player-remove (0x005A) handlers use

**OBSERVED** -- the wire:

- 162 messages, client table shape [u16, u16], 6 bytes
- field 1 is a playerId the same tape created via 0x0059 in 161/162; the remaining 1 is 0. field 2 is a created playerId in 150/162 and 0 in 12/162. NEVER a value the tape did not create.
- field1 == field2 (a self-link) in 143/162; field2 == 0 in 12/162; a link to a different player in 6/162
- of the 6 links to a different player, the target was already self-linked (i.e. already its own leader) in 6/6 where the target's state was known; a chain deeper than two levels never exists in the corpus

| field | meaning | label |
|---|---|---|
| 1 | playerId — the player being (re)assigned | SOURCED |
| 2 | the playerId of the group's leader, or 0 for none | INFERRED |

**Why this and not the nearest rival.** This is a re-parent on the client's player table: player i is unlinked from its old owner's member list and linked into a new owner's, with 0 meaning none. That the owner is a player and not a separate id space is not an assumption — the handler indexes the SAME array with the same bounds assert, and 161/162 indices and 150/162 targets are playerIds the same tape created with 0x0059. The structure is strictly leader-rooted: self-link is the default (143/162), every non-self link points at a player who is already its own leader, and no chain deeper than two levels ever appears. Both readers of the link ask the same question — 'does this player's group have more than one member' — one to pick the colour its name is drawn in (AvChar), the other to decide what a click on that player offers (GmView). That is a party. The nearest rival is PLAYER_SET_TRADE_PARTNER, which also produces player-to-player links that clear to 0; it is rejected because groups of three occur and because a trade has no member list or size. The second rival is a guild membership link, rejected because guilds are identified elsewhere by a u16 guild id, not by a playerId, and because the self-link default makes no sense for a guild. 'Party' itself is INFERRED — no assert in this code path uses the word.

**Ruled out:** PLAYER_SET_TRADE_PARTNER — groups of three occur; no member list or count in a trade; guild membership — guilds are keyed by a u16 guild id in a different context (ctx+0x3c), not by playerId; a separate party-id namespace — every index and target is 0 or a playerId the same tape created, and the handler bounds-checks both against the player array's count; pet/minion ownership — the indices are playerIds, not agent ids

**Still open:** Whether ArenaNet calls field 2 a partyId or a leader playerId. The party UI modules (PtRoster, PtPlayer, PtUtil) never reach this array directly, so no assert names it.; Whether 0 means 'no party' or 'party pending'. Only 12 samples, all shortly before the player leaves.

**For our server:** Sending 0x00B0 then 0x00B1 for each player we spawn into an outpost is what makes other players' names render in the right colour and the right-click menu behave; without it every player row sits in an unset group.


> **Refutation pass.** Ran msghandler.py 0x00B1 --follow --annotate --depth 3, msghandler.py --callers 0x00815d60, asserts.py --grep CHAR_CLASS_BASE_MASK/leader/party, and my own timeline rebuild. HANDLER: exact. 0x0091f050 -> 0x00813980: same player array (base ctx+0x80c, count ctx+0x814, stride 0x50), reads player[i]+0x2c, returns early if unchanged, unlinks from player[old]+0x38 via 0x0081ed10 when old is non-zero, writes the new parent, relinks. Array:587 guards every access. WIRE: reproduces exactly - 161/162 indices and 150/162 targets are playerIds the same tape created, the rest are 0, never an uncreated value; 143/162 self-links. I also verified both readers by disassembling them: 0x007f5b8e picks a name 


## `0x0026` GAME_SMSG_AGENT_UPDATE_FLAGS  *[high]*

**155 messages, 1.4% of the corpus.** Handler `0x005FD640`.

Reached: `AgMsg.cpp`, `AgAgent.cpp`, `AgNotify.cpp`


**SOURCED** -- the client's own words:

- AgMsg.cpp:438 "syncPtr" and AgMsg.cpp:443 "asyncPtr" (0x005FD682, 0x005FD6CC) -- the client's own names for the two agent arrays 0x64 apart that this handler, 0x0020 and 0x0021 all walk
- AgAgent.cpp:2301 "m_flags & INTERNAL_FLAG_IN_WORLD" (0x00602897) -- asserted on entry to the setter the handler calls with field 2, and it tests dword [agent+0x20], which names offset 0x20 as m_flags
- the setter's write is ((old ^ new) & 0x3f0000) ^ new -- it keeps the OLD bits inside mask 0x3f0000 and takes the NEW bits everywhere else. INTERNAL_FLAG_IN_WORLD is 0x20000, inside that mask, so the mask is exactly the INTERNAL_FLAG_* range the client owns
- AgAgent.cpp:2309 "!IsMoving()" -- reached only when bit 0x02 of the flags word actually changes, after which the setter re-applies the agent's stored position

**OBSERVED** -- the wire:

- 155 messages; 151 immediately follow 0x006D, the burst tail
- 155 of 155 name an agent 0x0020 created earlier in the same tape
- the joint with the create is decisive: (create field 4, this field 2) is (9,9) in 153 cases and (9,8) in 2 -- xor 0 and 1. This message carries the SAME word the create carried, and the only change ever seen is bit 0 clearing
- the two fields share one bit space: create field 4 in {0,1,5,9} (5 on players, 9 on NPCs/creatures, 0/1 on non-character agents), this field 2 in {8,9}

| field | meaning | label |
|---|---|---|
| 0 | msg_header (opcode 0x0026) | OBSERVED |
| 1 | agent id -- bounds-checked index into both the sync and async agent arrays | SOURCED |
| 2 | the agent's m_flags word. The client keeps its own INTERNAL_FLAG_* bits (mask 0x3f0000) and takes every other bit from this field; changing bit 0x02 additionally re-applies the agent's position | SOURCED |

**Why this and not the nearest rival.** This is the one opcode in the batch the repo had deliberately left unnamed (GAME_SMSG_AGENT_UNNAMED_0026), on the correct ground that two wire values, one seen once, is a shape and not a semantic. The client removes the ambiguity: the handler's only work is to call a setter whose entry assert names the destination member m_flags, and whose write idiom preserves precisely the INTERNAL_FLAG_* mask. The wire then agrees from the other side -- the value equals the create's field 4 in 153 of 155, and field 4 is that same member (the creator stores it to agent+0x20). Two independent witnesses on one member is the whole check. Nearest rival: the effects bitfield carried by 0x00F0/0x00F1. Rejected because those are a different member on a different message and carry a different value at the same instant (0x1000 on the worm creates while 0x0026 carries 9); flags and effects are two words, not one. Second rival: AGENT_UPDATE_KIND, since field 4 does encode player-vs-NPC in its low bits. Rejected on vocabulary -- the client calls the whole word m_flags and merges it as a bitfield, so naming the message for one bit-group would repeat the mistake T3 made with EFFECT_BURROWED. Third rival: reusing GAME_CMSG 0x0026's meaning (ATTACK). Different channel, different handler, no relation.

**Ruled out:** the agent effects bitfield (0x00F0/0x00F1) -- different member, and both are sent with different values inside the same burst; AGENT_UPDATE_KIND / agent type -- the client's word for the destination is m_flags and the write is a masked bitfield merge; anything to do with GAME_CMSG 0x0026 (ATTACK) -- opposite direction, unrelated handler; a create-only field echo -- 2 of 155 carry a changed value, so it is a genuine update channel

**Still open:** what bit 0 means. It is set on every create with a team token and clears in 2 of 155 updates; the client stores it with no special handling, so only a probe can settle it; whether the server is expected to preserve the 0x3f0000 bits it never sees -- the client masks them off defensively, so a server that sets them is silently corrected; bit 0x02, the one bit whose change re-applies position: never exercised in this corpus

**For our server:** Our server can change an agent's flags after creation instead of only at spawn -- the fifth message of the burrow burst we could not send, and the natural place to toggle the low bit the worms toggle.


> **Refutation pass.** This is the best-supported name in the batch and it survives intact. Handler re-resolved: 0x005fd640, correct. AgMsg:438 syncPtr at 0x005fd682 and :443 asyncPtr at 0x005fd6cc verified in place, each after an Array:587 bound check on field 1. Both paths call 0x00602880 with push [ebx+8] = field 2. I disassembled 0x00602880 myself: entry test dword ptr [esi+0x20], 0x20000 guarding AgAgent:2301 'm_flags & INTERNAL_FLAG_IN_WORLD' at 0x00602897 -- which pins m_flags to agent+0x20 and INTERNAL_FLAG_IN_WORLD to 0x20000 from the client's own words. The write idiom is exactly as claimed, byte for byte: 0x006028a6 mov ecx,[esi+0x20]; mov edx,ecx; xor edx,[ebp+8]; and edx,0x3f0000; xor edx,[ebp+8]; mov


## `0x00A6` AGENT_SET_PROFESSION  *[high]*

**136 messages, 1.2% of the corpus.** Handler `0x0091ee70`.

Reached: `AvApi.cpp`, `AvChar.cpp`, `AttribFrame.cpp`, `GmPosseRoster.cpp`, `GmAgentCommander.cpp`


**SOURCED** -- the client's own words:

- AvApi:1141 `agent` — the assert on arg1 at the head of the handler's target 0x007dffc0
- GmDeckBuilder:2321 `agentPrimaryProf != agentSecondaryProf` — the client's own name for this pair, and its own invariant
- AcctTemplate:411/412 `data.profPrimary < CHAR_PROFESSIONS` / `data.profSecondary < CHAR_PROFESSIONS`
- setter 0x007f7330 sits inside AvChar.cpp's assert block (between AvChar:3305 and AvChar:4320)

**OBSERVED** -- the wire:

- 136 messages, 64 distinct agents, 4 tapes; catalog shape from the client's own table is [agent_id, u8, u8], 8 bytes
- field 2 range 1..6, 6 distinct, value 0 NEVER occurs (n=136)
- field 3 range 0..8, 8 distinct, 0 is the mode (64/136); 7 never occurs
- field 2 == field 3 in 0 of 136 — exactly the invariant GmDeckBuilder:2321 asserts

| field | meaning | label |
|---|---|---|
| 1 | agent_id — the agent whose professions are being set | SOURCED |
| 2 | primary profession (1..6 observed; 0 never sent) | OBSERVED |
| 3 | secondary profession (0 = none; equals the profession byte the player-add message carries) | OBSERVED |

**Why this and not the nearest rival.** Three independent witnesses agree. The client's code writes the two bytes into adjacent slots of the agent's character-summary struct and notifies exactly the attributes panel, the party roster and the hero commander — the UI that shows profession icons. The client's own identifiers for a pair of per-agent quantities of this kind are agentPrimaryProf/agentSecondaryProf, and it asserts they differ; the wire never violates that in 136 samples. Which field is which is settled by the wire, not by guessing: field 2 is never 0 (every character has a primary) while field 3 is 0 in 64/136 (pre-searing characters below the secondary-profession quest), and field 3 reproduces the player-add message's profession byte 130/130. The nearest rival is AGENT_SET_LEVEL_AND_RANK — rejected because levels run to 20 and the corpus caps at 8, and because a level and a rank have no reason to be mutually exclusive whereas these two fields are never equal in any sample. The reversed assignment (field2=secondary, field3=primary) is the second rival and is rejected by the same two facts: field 2 never takes the 'none' value, and the cross-message match lands on field 3.

**Ruled out:** AGENT_SET_LEVEL / rank pair — value range caps at 8 and the two fields are never equal; field2=secondary, field3=primary — field 2 never takes value 0 and the 0x0059 cross-match lands on field 3; field 3 being a campaign or costume id — it matches the 0x0059 profession byte exactly in 130/130

**Still open:** The exact CHAR_PROFESSION enum ordering is not read out of the client here; only that field 2 spans 1..6 and field 3 adds 0 and 8. Reading ConstChar's s_charProfession / s_charProfessionAbbrev tables would pin the numbering.; What the single value 8 on non-player agents corresponds to (only 5 samples, all on agents with no player record).

**For our server:** Our server can send correct primary/secondary professions per spawned agent, which is what makes the party roster, attribute panel and nameplate render the right profession icons instead of blanks.


> **Refutation pass.** Ran msghandler.py 0x00A6 (plain and --follow --annotate --depth 3), asserts.py --grep on agentPrimaryProf / profPrimary / CHAR_PROFESSIONS / profession, a resyncing full-.text capstone sweep for the event id, and my own rebuild of the four-tape timeline from tape.py+codec.py. HANDLER: exact. 0x0091ee70 -> 0x00813380 (jmp) -> 0x007dffc0 (agent lookup 0x00802160) -> 0x007f7330, which writes field2 to byte +2 and field3 to byte +3 of *(AvChar+0x108), caches them at +0x10e/+0x10f and fires 0x1000001d. Every instruction they describe is there. WIRE: every number reproduces exactly - f2==f3 in 0/136; f3 equals the 0x0059 player-add byte in 130/130 while f2 equals it in 0/130; f3==8 in 5 samples on


## `0x0048` AGENT_SET_TABARD_VISIBLE  *[medium]*

**130 messages, 1.2% of the corpus.** Handler `0x0091db50`.

Reached: `AvApi.cpp`, `AvChar.cpp`, `CpsApi.cpp`, `GuCliApi.cpp`


**SOURCED** -- the client's own words:

- CpsApi:520 `composite` — the assert on arg1 of 0x0082dbb0, the function the flag gates
- CpsApi:504 `teamColorId`, CpsApi:505 `composite` — the same call's other arguments
- CpsTex:459 `teamColorId || tabard` — the client pairs teamColorId with `tabard`, the same pair this call passes
- AvApi.cpp block placement for the entry 0x007df3b0; AvChar.cpp block placement for the setter 0x007fc310

**OBSERVED** -- the wire:

- 130 messages, 58 distinct agents; client table shape [agent_id, u8], 7 bytes
- field 2 takes only 0 (32) and 1 (98); no agent ever received both values in the corpus
- the agent set is EXACTLY the agent set of 0x006E (58/58), and 0x0048 immediately follows 0x006E in 130/130 occurrences
- 45 of the 58 agents are player-controlled; both values occur on player and non-player agents

| field | meaning | label |
|---|---|---|
| 1 | agent_id — the agent whose guild insignia is being shown or hidden | SOURCED |
| 2 | 1 = show the guild insignia, 0 = hide it (the client stores the complement) | SOURCED |

**Why this and not the nearest rival.** The bit this message writes has exactly one reader in the entire binary, and that reader's whole job is: detach the current guild visual, then unless the bit is set, look the agent's guild up by the u16 at the head of its char-summary struct and composite the guild's design onto the model with a team colour. That is the guild cape/tabard, and the client's own noun for the composited guild piece, paired with teamColorId exactly as this call pairs them, is `tabard` (CpsTex:459). The nearest rival is AGENT_SET_HELM_VISIBLE — a headgear toggle is the other well-known per-character appearance boolean, and it is rejected outright because the gated code path performs a GUILD lookup and nothing else; no armour piece or head slot is touched. The second rival is 'a client-side render preference' — rejected because it arrives server-to-client, once per agent, for other players' agents, immediately after each agent's appearance message. Confidence is medium rather than high only because no assert in the image says 'cape' or names this bit; 'tabard' is our reading of CpsTex:459 plus the guild lookup, i.e. INFERRED.

**Ruled out:** AGENT_SET_HELM_VISIBLE / headgear toggle — the gated path does a guild lookup, not an armour-slot lookup; a client render option — it is server-sent per agent and the bit has a single test site tied to the guild visual; a generic 'appearance dirty' flag — the bit is never tested anywhere else in the image

**Still open:** Whether ArenaNet's word for the message is cape, tabard or insignia. No assert names the bit. Reading the guild record's +0x90 sub-struct, or finding the GAME_CMSG the guild panel sends when a player toggles cape display, would settle it.; Why 32 of 130 samples carry 0 in a pre-searing district where guild membership is rare — i.e. whether 0 is 'hidden by the player' or 'no guild'.

**For our server:** One byte per spawned agent that decides whether that agent renders a guild cape; sending 0 for our synthetic agents avoids a guild lookup on an id we never populate.


> **Refutation pass.** Ran msghandler.py 0x0048 --follow --annotate --depth 3, asserts.py --file CpsApi and --grep tabard/teamColorId/guild, a resyncing full-.text sweep for every instruction touching +0x15c, and my own timeline rebuild. HANDLER: exact. 0x0091db50 -> 0x0080f090 (jmp) -> 0x007df3b0 -> 0x007fc310, which computes ~(bit12) and, on a changed value, clears bit 0x1000 for wire 1 / sets it for wire 0 and calls 0x007f3bc0. The complement really is stored. THE STRONGEST CLAIM CHECKS OUT AND I VERIFIED IT INDEPENDENTLY: 'bit 0x1000 of +0x15c is tested at exactly one site in the whole image'. My sweep decoded 1.9M instructions and found 4 sites combining +0x15c with a 0x1000-family immediate; only 0x007f3bf5 


## `0x006E` UPDATE_AGENT_VISUAL_EQUIPMENT  *[high]*

**130 messages, 1.2% of the corpus.** Handler `0x0091E1C0 (dispatch stub) -> 0x00810E30 (worker)`.

Reached: `CharMsg.cpp`, `ChCliApi.cpp`, `AgApi.cpp`, `ItCliApi.cpp`, `ConstCostume.cpp`


**SOURCED** -- the client's own words:

- ChCliApi.cpp:51 "No valid case for switch variable 'prop'" — the assert at 0x008110B3 IS the default arm of this worker's own 9-way jump table (`cmp ebx,8 / ja 0x8110b1 / jmp [ebx*4+0x8110c4]`), so ArenaNet's name for the array index is `prop`
- ConstCostume.cpp:1188 "set - 1 < COSTUME_BODY_COUNT" (fn 0x008EE120, called only on the prop-7 arm)
- ConstCostume.cpp:1217 "set - 1 < COSTUME_HAT_COUNT" (fn 0x008EE220, called only on the prop-8 arm)
- ConstCostume.cpp:1204 / :1232 "profession < CHAR_PROFESSIONS" (fns 0x008EE1D0 / 0x008EE2B0 — the costume lookup is keyed by the character's profession)

**OBSERVED** -- the wire:

- 130 messages over 4 tapes; 55 distinct target agents. Immediately FOLLOWED by 0x0048 130/130; immediately PRECEDED by 0x0020 76/130 (the rest by 0x015E).
- Payload is exactly 9 dwords after the agent id — matches the worker's loop bound `cmp ebx,8` and its 9-entry jump table exactly.
- Per-field distinct counts across n=130: card[2]=3, card[3]=1 (constant 0), card[4..7]=58 each, card[8]=42, card[9]=6, card[10]=6. The three fields the client resolves through ItCliApi (card[2], card[9], card[10]) are precisely the three with small distinct counts (3, 6, 6); the five it forwards untouched to AvApi (card[4..8]) are the four-to-five with 58/58/58/58/42.
- Worker writes the value at char_object + 0x24 + 4*prop (`mov [esi + eax*4 + 0x24], edx` in 0x0081BE10), so the nine dwords are nine consecutive slots of one struct.

| field | meaning | label |
|---|---|---|
| 1 | agent id — resolved via AgApi.cpp's lookup, which requires agent kind 1 (a character); a non-char agent is dropped | SOURCED |
| 2 | prop 0 — item id of the HELD ITEM (`bundle`). Looked up through ItCliApi.cpp (0x008451E0); if the item's type byte == 6 a change raises FrApi message 0x10000031 (equip) and a clear raises 0x10000032, both consumed by GmBundle.cpp / GmAgentCommander.cpp. 0 means empty. | SOURCED |
| 3 | prop 1 — an appearance slot: stored at char+0x28 and forwarded to AvApi like props 2..6, but with no special handling. Constant 0 in all 130 samples, so which slot it is was not determined. | UNVERIFIED |
| 4 | prop 2 — appearance slot, forwarded verbatim to AvApi.cpp 0x007DFCE0(agent, prop, value). Not an item id (never enters ItCliApi). | OBSERVED |
| 5 | prop 3 — appearance slot, same path as prop 2 | OBSERVED |
| 6 | prop 4 — appearance slot, same path as prop 2 | OBSERVED |
| 7 | prop 5 — appearance slot, same path as prop 2 | OBSERVED |
| 8 | prop 6 — appearance slot, same path as prop 2 (42 distinct, more zeros than props 2-5) | OBSERVED |
| 9 | prop 7 — item id of the COSTUME BODY. Resolved through ItCliApi, then the item's first dword indexes ConstCostume's profession-keyed table whose bound is COSTUME_BODY_COUNT; result 0x2C means 'none'. | SOURCED |
| 10 | prop 8 — item id of the COSTUME HAT. Same chain but the COSTUME_HAT_COUNT table; this arm also runs the ConstAura s_aura lookup, so the costume's aura effect rides on this prop. | SOURCED |

**Why this and not the nearest rival.** The repo already ships this opcode as UPDATE_AGENT_VISUAL_EQUIPMENT (authsrv.py:139, playtested via probes). That name is CONFIRMED rather than merely inherited: the worker's only sinks are ItCliApi (items), ConstCostume (costume body/hat sets), ConstAura, and AvApi — the AgentView render layer — plus two frame messages whose only other consumers are the held-item UI (GmBundle.cpp). Nothing on this path touches health, energy, skills or any combat state, so the message is purely visual. The nearest rival was AGENT_UPDATE_PROPERTIES / a generic stat block, because the client's own word for the index is `prop` and 'prop' reads like 'property'. I rejected it because the destination is the render-side agent view and the constant tables are costume tables: it is a property block, but every property in it is an appearance property. ArenaNet-flavoured, UPDATE_AGENT_APPEARANCE_PROPS would be closer to their vocabulary, but the substance of the existing name is right and renaming buys nothing. FIELD PAIRING, stated explicitly because this is where the project has been burned: I paired card field index i (i=2..10) against prop (i-2), on the strength of the worker taking `lea eax,[ecx+8]` as the base of the prop array and indexing it with the same ebx that drives the jump table — i.e. the pairing comes from the client's own indexing, not from my reading of the value profiles. I did NOT pair against 0x0048's fields at all.

**Ruled out:** "All nine dwords are item ids" — false. Only props 0, 7 and 8 are passed to ItCliApi's lookup; props 1..6 go straight to AvApi with no resolution step.; "`prop` is the switch VALUE, not the index" — false. The switch is `cmp ebx,8 / jmp dword ptr [ebx*4+0x8110c4]` where ebx is the loop counter, and the loaded value lives in edi.; "This is a gameplay/stat update" — false. Every sink is render-side (AvApi, ConstCostume, ConstAura) or UI (GmBundle).; "The 9 dwords are floats like GAME_CMSG 0x0040's angles" — no evidence: they are used as array indices and item ids, never loaded into the FPU on this path.

**Still open:** Which body slot each of props 2..6 is (head/chest/hands/legs/feet is the obvious guess but nothing on this path names them). The answer is inside AvApi.cpp 0x007F70B0, which was not read.; prop 1 (card field 3) is 0 in all 130 samples, so its slot is unknown. A labelled probe that dyes/changes one armour piece at a time would resolve props 1..6 in one run.; Whether prop 0's type byte 6 is 'bundle' specifically or a broader item class — ItCliApi.cpp:614 has `def == GW_AGENTDEF_ITEM` nearby but the byte at item+4 was not chased to its enum.

**For our server:** We already send 0x006E; this pins which dword is which, so the server can dress an agent deliberately — slot 0 for the weapon it is holding, 9 and 10 for costume body/hat — and it re-confirms studies/divergence D5 that 0x0048 must follow every one (130/130 on the wire).


> **Refutation pass.** Re-resolved and reproduced everything load-bearing; the name holds, two field glosses do not. RAN: msghandler.py 0x006E --follow --annotate (twice, --limit 500 for the tail); asserts.py --grep "switch variable 'prop'"; asserts.py --at 0x00810e30 --span 1200; asserts.py --grep COSTUME_(BODY|HAT)_COUNT / arrsize\(s_aura\) / "msgId >= FRAME_MSG_EX"; asserts.py --file ConstCostume; asserts.py --callers 0x007dfce0; a scratch assert-range listing over 0x007df400-0x007e0600 and 0x00844e00-0x00845600; a scratch .text immediate scan for 0x10000031/0x10000032; scratch disassembly of 0x007dfce0 and 0x00811093. CONFIRMED: RECV table 0x00bc8f68 dispatches 0x6E to 0x0091e1c0, which calls 0x00810e30 with (


## `0x000D` LATENCY_REPORT  *[high]*

**79 messages, 0.7% of the corpus.** Handler `0x00491ED0 -> 0x0048DA40 (store) ; accessor 0x0048F010`.

Reached: `GcGameCmd.cpp (handler block, bracketed)`, `GcApi.cpp (the sample ring and its accessor)`, `UiRoot.cpp (the consumer)`, `EvtApi.cpp`


**SOURCED** -- the client's own words:

- UiRoot.cpp assert string "s_netGraph" sits immediately before the call site 0x004A384E, and that call site is one of only TWO direct callers of the accessor 0x0048F010. The value 0x000D delivers is plotted on the client's NET GRAPH, next to two MsgConn counters.
- EvtApi.cpp:2011 "context" — the store raises event 0xA2 through the engine event API after writing.
- The handler at 0x00491ED0 lies between GcGameCmd.cpp:425 and GcSrv.cpp:71 in P:\Code\Gw\Net\Cli\ — the game-connection command layer.

**OBSERVED** -- the wire:

- Store 0x0048DA40: `cmp esi, 0x1388 / ja skip` — the value is DISCARDED unless it is <= 5000. Then memmove(0xC03374, 0xC03370, 36) shifts the ring and [0xC03370] = value. 36 bytes moved + 4 written = a 10-deep history.
- Accessor 0x0048F010 walks `samples[i]` while non-zero, i < 10, summing; returns *out1 = samples[0] (the latest) and *out2 = sum/count (the mean). A current-and-average pair is the shape of a meter, not a state variable.
- 79 messages in the card corpus, exactly equal to 0x000C's 79; studies/divergence D4 measured the identity per connection (10/10/10, 29/29/29, 2/2/2, 3/3/3, 37/37/37) with the client's reply, which is a three-way per-connection equality no decoder can force.
- Field 1: 35..456, 35 distinct, p50 ~50 (D4). Inside the 5000 clamp with two decimal orders to spare.

| field | meaning | label |
|---|---|---|
| 1 | a measured latency sample. SOURCED: it is clamped to <= 5000, pushed into a 10-deep ring in GcApi, and the ring's (latest, mean) pair is plotted on UiRoot's s_netGraph. INFERRED: the unit is milliseconds — from the 5000 bound, the observed 35..456 range, and the fact that the loop it belongs to is a 5.000 s solicited round trip. | SOURCED |

**Why this and not the nearest rival.** studies/divergence D4 already labelled this a round-trip time, but labelled that reading RECONSTRUCTION. It is now sourced from the client. The chain is: handler -> clamp at 5000 -> 10-deep shift register in GcApi -> an accessor returning (latest, mean) -> UiRoot's s_netGraph. A number that is thrown away above 5 seconds, kept as a ten-sample history, averaged, and drawn on a network graph is a latency meter. The nearest rival was 'the server echoing back the client's own frame time', which is live because 0x000C makes the client report exactly that and 50 ms is also a plausible 20 fps frame interval. I rejected it on the net graph: the accessor's output is drawn on s_netGraph alongside two MsgConn counters, not on a frame-rate readout, and the client has no reason to be told its own frame time. The second rival, 'a server tick interval', dies the same way plus on the per-connection variation.

**Ruled out:** "The client's own frame time echoed back" — the sink is s_netGraph in UiRoot.cpp, next to MsgConn byte counters.; "A counter or sequence number" — a counter would not be discarded above 5000, would not be averaged, and would not be non-monotonic across 35 distinct values.; "There is no receive handler for this opcode" — which is what `msghandler.py 0x000D` reports today. See the note under 0x000C; the tool is wrong, not the wire.

**Still open:** The unit. Milliseconds is inferred, not read. A live capture where we know the true RTT (we control neither end, so this needs the ping loop implemented on OUR server and the client's net graph photographed) would confirm it. **UNBLOCKED 2026-08-11: the ping loop now exists** (`authsrv.py:ping_tick` / `handle_perf_report`), so this is no longer a dependency -- it is a 20-minute experiment. We now control one end and know the true elapsed time exactly, so: run a loopback session, read `[cN] net graph: last round trip <n> ms` off our own log, and photograph the client's net graph beside it. If the units are milliseconds the two agree; if they are not, the graph is wrong by a fixed factor and that factor names the real unit. **RUN 2026-08-11, and the experiment did not survive contact: THE NET GRAPH IS NOT REACHABLE FROM A LAUNCH FLAG.** The prediction above assumed it could be displayed. `-perf` is the only candidate in the client's 41-entry argument table and it draws exactly what GWW says it does -- measured off our own screenshot, top-right corner: `Tri: 66,054  FPS: 60  Bytes/Sec: 1,164`. Triangles, frame rate, throughput. **No latency figure.** So `s_netGraph` (UiRoot:331, one assert site) is a separate UI element that `-perf` does not expose, and **the unit stays INFERRED**. `Bytes/Sec` is very likely one of the two MsgConn counters this section says the graph sits beside, which is consistent with the read and still does not show the value. **ANSWERED 2026-08-11 by reading the client, and the answer is in two halves -- one of which IS a server message after all.**

`s_netGraph` is the object pointer at **`0xC06FE4`** (the assert at `0x004A37E4` pushes `0x14b` = line 331, so UiRoot:331 is `assert(s_netGraph)`). Its draw routine is `0x004A37D0`, and the **latency half is separately gated**: `cmp dword ptr [0xC06FE8], 0 / je` at `0x004A383D` is what wraps the call to accessor `0x0048F010` at `0x004A384E`. Two objects, not one.

**Half 1 -- the graph frame is a KEYPRESS, and nothing else in the image writes it.** Both objects are created at `0x004A3EB0`-`0x004A3F1C`, behind `cmp dword ptr [0xC06FD0], 0` at `0x004A3E96`. `codescan --field 0xC06FD0` is exhaustive over the disp32 encoding and finds **exactly two stores**, both in that one function; the live one at `0x004A3E89` is `sete al` on `== 0` followed by `mov [0xC06FD0], eax` -- a **flip**, not a set. It is reached from UiRoot's UI-message handler `0x004A3D50`: message type `[ebx+4] == 0x20` selects a key case, then `[ebp+0xc]` is the key parameter with `param[0]` = key code and `param[8]` = modifier. Two jump tables later (`0x4a46a0`/`0x4a46cc` by message, `0x4a4718`/`0x4a472c` by key), **exactly one key code reaches the net graph: `0x29`, and only with modifier `== 4`.** Its siblings in the same table calibrate the shape -- `0x48` (`H`) with modifier `== 6` toggles a different global at `0xC06FDC`, and `0xAE` and `0xBB` have their own cases. (OBSERVED for the values. **UNVERIFIED: what they MEAN** -- `0x29`/`0x48`/`0xAE`/`0xBB` are consistent with Windows VK codes (`VK_SELECT`, `H`, `VK_VOLUME_DOWN`, `VK_OEM_PLUS`) but the client may carry its own enum, no assert string names a keyboard modifier anywhere in the image, and **this has not been pressed at a running client**.)

**Half 2 -- the LATENCY readout is enabled by `GAME_SMSG 0x016E`, which we can send.** The second object `0xC06FE8` is built only if the predicate at `0x0084DF00` returns true, and that function is four instructions: TLS context (`0x0047F660`, via `fs:[0x2c]`), `[+0x44]`, `[+0x2A8]`, `shr 3`, `and 1` -- **bit 3 of a flags word**. No instruction anywhere in `.text` sets that bit directly; `--field 0x2A8` returns 35 accesses and every bit operation on it is `0x2` or `0x10`. It is written wholesale by `0x0084E090`, which clears `0xFFFFFFF2` and then maps an argument bitfield on: `[arg+4]` bit 0 -> flags bit 0, bit 1 -> flags bit 2, and **bit 2 (value 4) -> flags bit 3**. `msghandler.py 0x016E` names that function as the RECV handler for **`GAME_SMSG 0x016E`** (table `0x00bcb0a8`), and the schema's `0x016E` is `msg_header` + **one byte**, `declared_unpack_size` 3 -- which is exactly the `[edx+4]` the handler reads. Three independent things agree on the same message.

> **A correction worth keeping, because it nearly shipped.** Walking the descriptor table by hand gave `0x016F`, and `0x016F` is header-only with no payload -- which contradicts a handler that reads `[edx+4]`. The contradiction was the tell: the hand walk was off by one descriptor, and `msghandler.py` -- which knows the table's real stride -- says `0x016F` belongs to `0x0084E110`. The schema disagreeing with the disassembly is what caught it, so **neither** was trusted alone.

**RUN 2026-08-11, both halves, and the client's own memory was the instrument rather than a screenshot.** Screenshots cannot tell "the key never arrived" from "the key arrived and nothing draws"; the four gate globals can, so they were read live out of the running client with `keytap.read_rva` (ASLR-correct, RVA = VA - 0x400000).

**The message is validated.** Our server sent `GAME_SMSG 0x016E` = `6e 01 04`, three bytes, once after the instance loaded. The client **accepted it silently and stayed healthy** for the rest of the session -- no assert, no disconnect, the `0x000C`/`0x000D` loop still round-tripping at 11 ms. The wire shape the schema declares is now confirmed against a real client. **And it created nothing**, exactly as predicted: with the message delivered, all four globals still read 0. Setting the bit alone leaves it with nothing to read it, because the widget is built inside the frame's own gate.

**The keypress mechanism is PROVEN -- by the control, not by the target.** `Ctrl+Shift+H` set `0xC06FDC` from `0x00000000` to `0x00000001`, read out of process memory. Three things follow, and none of them was known before: the case inputs really are **Windows virtual-key codes** (0x48 is `H`); **modifier 6 is Ctrl+Shift**, so the two bits are `{ctrl, shift} = {2, 4}` in some order; and a synthetic keystroke with a real scan code reaches this UiRoot handler. The control is what makes the negative below worth anything.

**Key `0x29` does not toggle the frame, and the modifier is NOT the reason.** `0xC06FD0` stayed 0 through `0x29` under alt, shift and ctrl. Since modifier 4 must be ctrl-alone or shift-alone (from the Ctrl+Shift result above) and **both were tried**, the surviving explanation is the key itself: `MapVirtualKeyW(0x29, MAPVK_VK_TO_VSC)` returns **0** on this layout, so `VK_SELECT` has no position on an ordinary keyboard and had to be injected with `bScan=0`. The three sibling keys all have real scan codes (`H` 0x23, `VK_VOLUME_DOWN` 0x2e, `VK_OEM_PLUS` 0x0d); `0x29` is the only one that does not.

**Conclusion: the net-graph FRAME is behind a key an ordinary keyboard cannot produce**, which makes it a developer path rather than a hidden player feature -- consistent with `-perf` never showing it. **UNVERIFIED, and stated because the delivery was the weak one:** a genuine `VK_SELECT` (from hardware that has the key, or a lower-level injection than `keybd_event`) has not been tried, so "undeliverable here" is not quite "unreachable". What IS excluded is the modifier, which was the open variable when this section was written.

**SendInput pass, 2026-08-11 -- the negative is now strong, and `0x29` is NOT a key we can name.** `keybd_event` with `bScan=0` was the weak delivery, so the whole matrix was re-run through `SendInput`, which can set `wVk` and a NONZERO `wScan` independently and can also hand Windows the scan code as authoritative via `KEYEVENTF_SCANCODE`.

**The control fired twice, which is what makes the rest worth reading.** `H` + Ctrl+Shift flipped `0xC06FDC` `0 -> 1` with a real scan code and no flag, and then `1 -> 0` again under `KEYEVENTF_SCANCODE`. So SendInput reaches this handler, **both delivery modes reach it**, and the toggle is observable in memory in real time. It also pins the modifier for the first time: **modifier 6 IS Ctrl+Shift**, so the two bits are `{ctrl, shift} = {2, 4}` and the net graph's modifier 4 is one of them ALONE.

**Seventeen deliveries of `0x29`, none of which moved `0xC06FD0`.** Nine as a virtual key -- `wScan=0`, `wScan=0x23`, `wScan=0x53`, `KEYEVENTF_EXTENDEDKEY`, under ctrl, shift, alt and no modifier. Then eight more testing the best rival reading: **`0x29` is also `DIK_GRAVE`, the scan code of the backtick/tilde key** and the conventional debug toggle in games -- `MapVirtualKeyW(VK_OEM_3)` returns exactly `0x29`, so the coincidence is real. Sent as `VK_OEM_3` and as raw scan `0x29` under `KEYEVENTF_SCANCODE`, with every modifier. Nothing.

**So the table's `0x29` is neither `VK_SELECT` as typed nor the backtick key**, and since `0x48` answers to `VK_H`, the vocabulary is not uniformly one thing either. What `0x29` denotes is UNIDENTIFIED, and that is now the whole of what stands between us and the readout. The next move is not another guessed keystroke: it is to read where the client BUILDS the UI-message-`0x20` parameter, because that call site is where the key value's provenance is decided and it would settle the vocabulary instead of sampling it.

> **A trap worth naming, because it wasted a run and mimics the result.** `SendInput` returned 0 with `ERROR_INVALID_PARAMETER` for every trial until the `INPUT` struct was sized correctly: the union is as large as its BIGGEST member, `MOUSEINPUT` (32 bytes on x64), not `KEYBDINPUT` (24), so `INPUT` is 40 bytes and a `KEYBDINPUT`-sized union yields 32. A rejected struct and a rejected keystroke look identical from the outside -- both are "the key did nothing". The script now asserts `sizeof(INPUT)` before it sends anything.

**RESOLVED 2026-08-11 by reading where the parameter is BUILT, which is what the guessing should have given way to sooner.** `0x004A3D50` is the **Root frame's** message callback -- registered at `0x004A2375` through `0x630C90` with the UTF-16 name `"Root"`, which is why its asserts say UiRoot. The key value in its message-`0x20` parameter comes from the OS input layer at `~0x005EDA80`, and that code answers the vocabulary question outright:

```
005EDA86  mov ecx, ebx          ; ebx = the WM_KEY* lParam
005EDA89  shr ecx, 0x10         ; lParam >> 16
005EDA8C  movzx ecx, cl         ; ...low byte = the SCAN CODE
005EDA88  push eax              ; hkl, from [0xC103FC]
005EDA8F  push 1                ; MAPVK_VSC_TO_VK
005EDA91  push ecx              ; the scan code
005EDA92  call [0x9394D8]       ; USER32!MapVirtualKeyExA  (verified in the import table)
005EDABA  test ebx, 0x1000000   ; lParam bit 24, the extended flag
005EDAC2  or   esi, 0x80000000  ; VK_EXTENDED  (hence OsInput:402's !(vKey & VK_EXTENDED))
```

**The client never looks at `wParam`. It recomputes the virtual key from the SCAN CODE through the active keyboard layout.** So the table's values are Windows VKs after all -- but a key is reachable if and only if some scan code maps to it under the client's own `hkl`.

**That explains every result of the SendInput pass exactly, including the controls.** `H` worked because the scan code sent was `0x23` and `MapVirtualKeyEx(0x23, VSC_TO_VK)` is `0x48` -- the value the table wants. It worked identically with and without `KEYEVENTF_SCANCODE` because in both cases the delivered lParam carried scan `0x23`. And **`0x29` failed all seventeen times because no scan code on layout `0x0409` maps to `VK_SELECT`** -- measured directly, forwards and backwards, over the whole `0x000`-`0x1FF` range. Setting `wVk = 0x29` could never have worked: that field is discarded before the value the handler compares is even computed. The backtick attempt failed for the same reason from the other side -- scan `0x29` maps to `VK_OEM_3` (`0xC0`), not to `0x29`.

**Conclusion: the net-graph frame is unreachable on a US layout by construction, not by accident.** It is a developer path gated behind a virtual key that no scan code on this keyboard produces. The only route left is a keyboard layout under which some scan code maps to `VK_SELECT`, which is a machine-level change to the operator's system and is **not** something to do on a hunch -- it is recorded here as the option, not taken.

**So the readout stays unread and the unit stays INFERRED, but nothing about it is mysterious any more.** `--netgraph` sends `GAME_SMSG 0x016E` and is verified against a real client; the flags bit it sets is real; the widget it would build is gated behind a frame whose toggle this keyboard cannot type. Every link in the chain is now either done or explained.

**What the run did settle, because we now hold the other end.** The loop runs against a real client: **10 of 10 requests answered** in a 45 s session and 0 missed in a second, with round trips of 658, 15, 12, 10, 7, 7, 3, 14, 14, 11 ms -- the 658 is the first ping landing during the map load, and every later one is loopback-shaped. So the three-message exchange, the 5 s cadence and our elapsed-ms arithmetic are all confirmed end to end; only the client's *rendering* of the number is still unread.; What event 0xA2 does downstream.; Which index of the 0xC03370 ring other code writes — the accessor reads up to 10 but 0x000D only ever writes index 0, so either nothing else writes it or the other writer was not found.

**For our server:** Implement the 5 s loop and the client's net graph and connection meter start working against our server; more usefully, it gives us a place to put a real measured RTT instead of a constant.


> **Refutation pass.** Reproduced end to end; the name holds and I can now pin the wire shape from the client's own descriptor. RAN: msghandler.py 0x000D --follow --annotate (reports SEND-only, as they warned); a raw stdlib walk of the descriptors at 0x00BEC394; scratch disassembly of 0x00491ed0, 0x0048da40, 0x0048f010; asserts.py --callers 0x0048f010; asserts.py --grep s_netGraph; a scratch assert-range listing over 0x00491000-0x00492400 and 0x0048d800-0x0048f400. CONFIRMED: descriptor 4 of table 0x00BEC394 has cmds[0]=13 and dispatch 0x00491ed0. 0x00491ed0 pushes msg+4 into 0x0048da40. 0x0048da40 is `cmp esi,0x1388 / ja skip`, then memmove(0xc03374, 0xc03370, 0x24) and [0xc03370]=esi — 36 bytes shifted plus one 


## `0x000C` CLIENT_PERF_REQUEST  *[medium]*

**79 messages, 0.7% of the corpus.** Handler `0x00491E50`.

Reached: `GcGameCmd.cpp (handler block, bracketed)`, `GrPerf.cpp`, `FrApi.cpp`, `MsgConn.cpp`


**SOURCED** -- the client's own words:

- GrPerf.cpp:291 "counter < GR_COUNTERS" and GrPerf.cpp:292 "period < GR_PERIODS" — the handler's first act is to query the graphics performance counters with counter=4, period=3.
- MsgConn.cpp:1186 "mc", :1187 "msg", :1194 "count" — the handler's last act is MsgConn's send, with count=3 dwords.
- MsgConn.cpp send (0x007DCB10) computes the wire opcode as `(([conn+0x54] != 0) ? 0x8000 : 0) | msg[0]`. THIS IS THE 0x8000: studies/divergence D4 calls the client's reply `0x8009`; it is send opcode 9 with a connection flag bit OR'd in by MsgConn, not an opcode in the 0x8000 range.
- The handler at 0x00491E50 lies between GcGameCmd.cpp:425 and GcSrv.cpp:71 in P:\Code\Gw\Net\Cli\.

**OBSERVED** -- the wire:

- The handler takes no payload — the message is 2 bytes, header only — and its entire body is: query GrPerf(4,3) -> n; esi = (n ? 1000/n : 40); read the FrApi global -> boolean; build {9, esi, bool}; send. A 1000/n with a fallback of 40 is a rate inverted to a per-frame interval in ms (40 ms = 25 fps).
- 79 in the card corpus, exactly equal to 0x000D's 79 and (per studies/divergence D4) to the client's replies, per connection.
- D4 measured the reply cadence at 5.000 s (75 of 76 gaps within 100 ms) and the lag from 0x000C to the reply at a 9.3 ms median — which is what a handler that replies synchronously, inside its own dispatch, produces.
- THE TABLE THIS OPCODE LIVES IN WAS MISSING FROM OUR TOOLING. See reasoning.

| field | meaning | label |
|---|---|---|
| 0 | no payload — header only. The message's entire content is the fact that it arrived. | SOURCED |

**Why this and not the nearest rival.** THE STRUCTURAL FIND HERE MATTERS MORE THAN THE NAME. `msghandler.py 0x000C` and `0x000D` both report 'the client only SENDS this one; there is no handler to read' — a confident wrong answer. The cause: read_table() builds `cmds = [...for k in range(n)]` and then `if not cmds: continue`, so every descriptor whose count field is 0 in the file is silently dropped. That is 37 receive descriptors — all 5 of table 0x00BEC394 and all 32 of 0x00BEC540 — invisible to both msghandler and msgshape. Proof that 0x00BEC394 is the GAME channel's, not the auth channel's: (a) its five opcodes are exactly {0x0A,0x0B,0x0C,0x0D,0x0E}, which is exactly the hole in the game receive space, whose other tables tile 0x0000-0x0009 and 0x000F-0x01E6 contiguously; (b) the auth receive table 0x00BEC540 ALREADY contains 0x0A..0x0E, and two descriptors for one opcode on one channel is impossible; (c) its send partner 0x00BEC384 holds exactly {0x08,0x09}, the matching hole in the game send space; (d) send opcode 9 is precisely the reply this handler transmits, and precisely the c2s message D4 measured on the wire. Four independent closures. So: handler 0x000C = 0x00491E50, handler 0x000D = 0x00491ED0, and the catalog's true orphans are only five — 0x004F, 0x0055, 0x007F, 0x014A, 0x01DA have no receive descriptor anywhere in build 38797 (487 catalog = 477 read + 5 recovered + 5 genuinely absent). ON THE NAME: the handler's only effect is to compose and send a client performance report, so CLIENT_PERF_REQUEST is what the message MEANS to the client. The nearest rival is PING / KEEPALIVE_REQUEST, which is how studies/divergence D4 reads it from the server side, and which is not wrong — the server clearly times the round trip and hands the result back as 0x000D. I chose the perf name because a pure liveness ping would not need the reply to carry a frame interval and a frame-system flag, and because naming it 'ping' would hide that the reply has real content our server would have to make sense of. Both readings should be recorded.

**Ruled out:** "There is no receive handler; the client only sends 0x000C" — that is our tool's zero-count blind spot, not a fact about the client.; "0x00BEC394 is the auth channel's table" — impossible: the auth receive table already carries 0x0A..0x0E.; "The client's reply opcode is 0x8009" — no. MsgConn OR's 0x8000 in from a connection flag; the registered send opcode is 9.; "The reply echoes the request" — it carries no data from the request, which is empty; it carries GrPerf and FrApi state.

**Still open:** What GrPerf counter 4 / period 3 actually counts. 1000/n with a 40 fallback is frame-rate shaped, but GR_COUNTERS' enum was not recovered — the names are not in the assert strings.; What the FrApi global at 0xC1100C means (the reply's second dword, a 0/1).; Whether the server ever sends 0x000A, 0x000B or 0x000E — none appeared in 10,944 messages, but their handlers now have addresses (0x00491E30, 0x00491E10, 0x00491EF0) and 0x000B's is a one-shot latch of its dword into a global.

**For our server:** ✅ **BUILT 2026-08-11** (`ping_tick` / `handle_perf_report`, `test_ping.py`). A 5 s timer sending a 2-byte 0x000C, plus a GAME_CMSG opcode-9 handler that at minimum fails loudly instead of silently — today all of the client's replies land on our silent-ignore path. ~~and per D9(b) a schema-unknown c2s opcode discards whatever shared its TCP read.~~ **CORRECTED 2026-08-11:** `0x0009` is schema-**known** (`GAME_CMSG_0009`), so it takes D9(**a**)'s silent-ignore path, which does not touch the buffer; D9(b) covers schema-*unknown* opcodes and is itself fixed. The replies are ignored, not destructive — worth handling for tidiness and for the net graph, not as a correctness fix.

**NEW, from the 2026-08-11 loopback run: `GAME_CMSG 0x0009` field 1 is the frame interval in MILLISECONDS, and the client's own screen corroborates it.** Every one of the ten replies decoded to `[32777, 16, 0]` -- `32777` is `0x8009`, the masked header, so the two payload dwords are **16** and **0**. In the same session, with `-perf` drawing the client's own readout, the screenshot says **`FPS: 60`**. `1000/60 = 16.67`, which truncates to 16. So field 1 is a frame time in ms and field 2 is the FrApi flag, sitting at 0.

That is a *better* class of evidence than the rest of this section: the number the client SENDS us and the number the client DRAWS for itself agree, and neither passes through our decoder on the way to the other. It also retires the nearest rival named above -- "the server echoing back the client's own frame time" was live precisely because 50 ms is a plausible 20 fps interval, and now the frame interval is pinned in the CLIENT's message rather than in ours, on the other side of the round trip. (OBSERVED, n=10 replies in one session at a locked 60 fps. A run at a different frame rate would test it properly and has not been done -- `-fps <number>` exists for exactly that.)


> **Refutation pass.** The structural find is CONFIRMED and I can now close it harder than they did; the name is defensible but it is an inference from what the handler does, and the PING co-reading is not excluded. RAN: msghandler.py 0x000C --follow --annotate; read read_table in msghandler.py and _enumerate in msgshape.py; a raw stdlib descriptor walk of all 25 tables; a scratch .text scan for the load-time stores into every 0x00BEC384/0x00BEC394 count field; scratch disassembly of 0x00491e50, 0x007dcb10, 0x00631aa0; asserts.py --grep GR_COUNTERS / GR_PERIODS. CONFIRMED, THE TOOL BUG IS REAL: msghandler.read_table builds `cmds = [...for k in range(n)]` then `if not cmds: continue`, and msgshape._enumerate has `i


## `0x002E` AGENT_UPDATE_ROTATION  *[high]*

**64 messages, 0.6% of the corpus.** Handler `0x005fdc60`.

Reached: `AgMsg.cpp`, `AgAgent.cpp`


**SOURCED** -- the client's own words:

- AgMsg.cpp:629 "syncPtr" and AgMsg.cpp:635 "asyncPtr" -- applied to both agent copies, same double-application as 0x0025
- AgAgent.cpp:2438 "m_flags & INTERNAL_FLAG_IN_WORLD" in the setter 0x00602cc0
- Array.h:587 / Array.h:594 "index < m_count" bounding field 1
- No assert names the two payloads, so the argument is arithmetic, and it is unambiguous: the setter stores field 2 at agent+0xcc and field 3 at agent+0xc8, then computes |wrap(field2 - atan2(agent+0xbc, agent+0xc0))| * 1000.0 / field3, converts to int and adds it to the timestamp at agent+0x58. Multiplying radians by 1000.0 and dividing by field 3 to get a millisecond deadline means field 3 is radians per second

**OBSERVED** -- the wire:

- 64 messages. 55 finite field-2 values, ALL inside [-pi, pi] (min -2.87253, max 3.11908, 0 outside). The only non-finite values are exactly +inf (4x) and -inf (5x) -- the two constants the client branches on, appearing on the wire from ArenaNet's own server
- field 3 has exactly 3 distinct values: 0.2489200, 0.8901179, 2.0943952 rad/s = 14.2621, 51.0000, 120.0000 deg/s. 2.0943952 is 2*pi/3 to the bit. All positive
- field 3 is essentially per-agent constant: of 31 agents that sent 0x002E, 29 never changed it, and 28 of 31 use 120 deg/s -- the signature of a per-creature turn rate
- Only 11 of 64 have ANY movement message (0x0025/0x0029/0x002B) for the same agent within +/-40 messages, so these are mostly agents turning in place

| field | meaning | label |
|---|---|---|
| 1 | agent -- index into the agent array; applied to sync and async copies | SOURCED |
| 2 | target rotation, an absolute angle in radians in the same frame as atan2 of the agent's heading vector. +inf / -inf are sentinels meaning 'turn without a target' -- that branch sets the completion deadline to now + 0x1FFFFFFF ms and skips the angle arithmetic entirely | OBSERVED |
| 3 | angular speed in radians per second; the client turns |delta| radians in |delta|*1000/field3 milliseconds | OBSERVED |

**Why this and not the nearest rival.** This one CONTESTS the written sources and settles studies/movement/FINDINGS.md's own open question ('What does 0x002E actually carry -- sin+cos floats, two angles, or something else'). Upstream GameMsg.h:546-551 names the two dwords rotation_cos and rotation_sin. That is refuted three separate ways: a sine cannot be 2.0943952, field 3 is never negative in 64 samples and takes only 3 values, and a cosine is never +/-inf -- yet 9 of the 64 field-2 values are exactly the two infinity constants the client's code branches on. Positively, the client subtracts field 2 from an atan2 result and wraps the difference by pi/2pi, which only makes sense if field 2 is an angle, and it divides by field 3 after multiplying by 1000.0 to produce a millisecond deadline, which only makes sense if field 3 is rad/s. Nearest surviving rival: 'two angles, target and current' -- rejected because field 3 is per-agent constant across the session, always positive, confined to 3 values, and appears as a DIVISOR. Second rival: the same normalised turn rate that GAME_CMSG 0x0040 carries (the client asserts that one within +/-1.0 and gates it at 0.1) -- rejected because 2.0944 is outside +/-1.0, so the SMSG rate is a different quantity occupying the same slot role. Field-index discipline, since this is where the project lost a day: the handler pushes [msg+8] (field 2) as arg1 and [msg+0xc] (field 3) as arg2, verified by disassembling the two fstp's into esp+0 and esp+4, and inside the setter arg1 lands at agent+0xcc (the angle that gets wrapped) and arg2 at agent+0xc8 (the divisor). I checked that before naming either.

**Ruled out:** (cos, sin) per upstream GameMsg.h:546-551 -- field 3 reaches 2.0944 and is never negative; field 2 is +/-inf 9 times; and the client wraps field 2 by 2*pi; (sin, cos) in the other order -- same refutation, and the order question is moot once neither field is a trig value; two angles (current and target) -- field 3 is per-agent constant, strictly positive, 3 distinct values, and is used as a divisor producing milliseconds; a quaternion or a normalised [-1,1] rate like GAME_CMSG 0x0040's second field -- 2.0944 exceeds the +/-1.0 the client asserts for that one

**Still open:** Which of +inf and -inf is a left turn. Exactly the coin flip the repo declined to call for GAME_CMSG 0x0040 and I decline it here for the same reason: the two branches differ only in x87 stack cleanup, and the sign has to be read out of the angle-at-time function (0x005ff9f0) or a labelled run.; The target angle could not be corroborated against an independently derived heading. Only 4 of the 31 agents that sent 0x002E ever sent 0x0025, and pairing against the heading between consecutive 0x0029 positions left n=2 usable samples. The angle claim therefore rests on the client's arithmetic plus 55 of 55 finite values landing inside [-pi,pi], not on a wire-to-wire correspondence. A labelled run that parks the operator next to a patrolling NPC and records it turning would close this.; Where the third rate value 0.2489200 rad/s (14.2621 deg/s) comes from. The other two are round in degrees (51.0000 and 120.0000) and that one is not.; The wire typing stays `dword` for both float payloads. Do not 'fix' it to `float` -- this is the identical trap that test_rotate.py exists to keep red for 0x0040.

**For our server:** This is the missing piece for NPC facing: the server can now turn any agent to a stated heading over a stated time, or set it spinning with the +/-inf sentinel, instead of never sending the message because nobody knew what went in it.


> **Refutation pass.** Handler re-resolved: 0x005fdc60. AgMsg:629 "syncPtr" (0x005fdca2) and AgMsg:635 "asyncPtr" (0x005fdd35) confirmed. Their field-index discipline is correct and I re-checked it instruction by instruction: the handler does `fld [edi+0xc]; fstp [esp+4]` then `fld [edi+8]; fstp [esp]`, so field 2 is arg1 and field 3 is arg2; inside 0x00602cc0 the two are swapped through locals and land at agent+0xcc (field 2) and agent+0xc8 (field 3). The arithmetic reproduces exactly: subtract the cached heading angle from field 2, wrap by +/-pi using the doubles at 0x00946258 / 0x00946ed8 / 0x00946e80, fabs, multiply by the double at 0x00943898, divide by [esi+0xc8] (field 3), convert to int and add [esi+0x58].


## `0x0056` NPC_UPDATE_PROPERTIES  *[high]*

**62 messages, 0.6% of the corpus.** Handler `0x0091DD80 (dispatch stub) -> 0x0080FA30 (worker)`.

Reached: `CharMsg.cpp`, `ChCliApi.cpp`


**SOURCED** -- the client's own words:

- CharMsg.cpp:4438 "message.compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS" — this is the assert in the handler for 0x0057 (0x0091DE00), the message that ALWAYS follows 0x0056 and shares its field 1. It names the definition table's owner: MONSTER.
- ChCliApi.cpp:6312 "baseClass == CHAR_CLASS_MONSTER_BASE" and ChCliApi.cpp:4966 "!(playerId & CHAR_CLASS_BASE_MASK)" — the client's id space for these definitions is a CHAR_CLASS space with a monster base.
- Worker 0x0080FA30 is bracketed on both sides by ChCliApi.cpp asserts (ChCliApi:792 .. ChCliApi:4966), so it is in P:\Code\Gw\Char\Cli\ChCliApi.cpp.
- 0x0057's worker 0x0080FBD0 has a byte-identical prologue to 0x0056's — same context member [ctx+0x2c], same array at +0x7fc, same 0x30 element stride — so the two messages provably write the same table row.

**OBSERVED** -- the wire:

- 62 messages; field 1 has 44 distinct values and 0x0057's field 1 has 36 distinct drawn from the same set. 50 of 62 are immediately followed by 0x0057.
- THE ELEMENT CLOSES TO THE EXACT BYTE, which is the check this repo prefers: the handler memsets a 0x20-byte local, fills it with wire fields 2..8 (7 dwords into slots 0,4,8,0xC,0x10,0x14,0x1C — slot 0x18 deliberately left zero), and the worker writes those 32 bytes at element+0x00 and the string16[8] (8 x u16 = 16 bytes) at element+0x20. 0x20 + 0x10 = 0x30, which is exactly the stride the worker computes (`lea eax,[edx+edx*2]; shl eax,4`).
- Field 1 is used as a raw array index: the worker grows the array to index+1 and asserts `index < m_count` before writing, so it is a definition slot number, not a handle.
- Field 3 and field 5 are 0 in all 62 samples. Field 4 takes exactly 3 distinct values, all with the low 24 bits zero, the top octet being 100, 120 and 150 decimal.

| field | meaning | label |
|---|---|---|
| 1 | definition slot index — used directly as an array index into the per-instance monster-definition table (ChCliApi, [ctx+0x2c]+0x7fc, 0x30-byte elements); 0x0057 addresses the same slot | SOURCED |
| 2 | record dword 0 (element+0x00). 23 distinct, large values; not resolved further. | OBSERVED |
| 3 | record dword 1 (element+0x04). Constant 0 across all 62 samples. | UNVERIFIED |
| 4 | record dword 2 (element+0x08). Only 3 values, all of form <byte>000000 with the top octet 100/120/150 — the shape of a percentage-scaled quantity carried in the high byte. Not a float32 (those bit patterns decode to ~1e22). | OBSERVED |
| 5 | record dword 3 (element+0x0C). Constant 0 across all 62 samples. | UNVERIFIED |
| 6 | record dword 4 (element+0x10). 11 distinct with disjoint bit groups — a flags word. | INFERRED |
| 7 | record dword 5 (element+0x14), widened from a wire byte. 7 distinct in 1..11. | OBSERVED |
| 8 | record dword 7 (element+0x1C), widened from a wire byte. NOTE THE GAP: the handler skips element+0x18, which stays zero — so the record has 8 dword slots but the wire only fills 7 of them, and field 8 lands in the LAST slot, not the seventh. | SOURCED |
| 9 | encoded name string, 8 u16 units, written at element+0x20 (GW encoded-string form, which is why it renders as CJK mojibake in the card) | SOURCED |

**Why this and not the nearest rival.** The repo already calls this NPC_UPDATE_PROPERTIES and 0x0057 NPC_UPDATE_MODEL, and both are confirmed rather than inherited. The decisive new evidence is the client's own assert on the PAIRED message: `message.compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS` in CharMsg.cpp. Two things fall out of one line — ArenaNet's word for the thing being defined is MONSTER, and their word for the descriptor struct is `message`, so the array32[8] in 0x0057 is a composite (model-assembly) dword list bounded at 8. The two workers then prove they address the same table row by construction. The nearest rival was 'this is a per-agent property update, not a type definition', which is what the field-1 value range (up to 8077) invites you to think if you read it as an agent id. I rejected it because the worker uses field 1 as a direct array index and grows the array to fit it — an agent id would be looked up, not indexed — and because the record is a 48-byte template with a name string, which is a type, not an instance. ArenaNet-flavoured the name would be MONSTER_DEFINITION; I am NOT recommending a rename, only recording that 'monster' is their word and 'NPC' is ours.

**Ruled out:** "0x0056 and 0x0057 are unrelated messages that merely co-occur" — refuted: identical worker prologues onto the same context member, same array base offset +0x7fc, same 0x30 stride, indexed by the same wire field.; "Field 4's three values are floats" — refuted: as float32 those bit patterns are ~1.5e22 / 3.9e33-scale nonsense. The live part is the top octet.; "The record is 7 dwords" — refuted: the handler leaves element+0x18 zero and puts wire field 8 at element+0x1C, so the record is 8 slots with a hole. A server that packs 7 fields contiguously would land field 8 one slot early.

**Still open:** What the 8-dword record's individual slots mean. Nothing on this path asserts on them; the readers are elsewhere in ChCliApi and were not chased.; Whether field 4's 100/120/150 is a scale percentage. A probe that sends one value and photographs the resulting model size would settle it in one launch, and it is cheap because our server already sends this message.; Whether element+0x18 (the hole) is written by some other message.

**For our server:** Nothing new to send — we already send it — but the exact record layout means our probes can stop guessing which dword they are setting, and the +0x18 hole says field 8 must be placed last, not seventh.


> **Refutation pass.** The name survives and is now better supported than they made it, but their headline check is fabricated and one 'sourced' bullet does not reach anything. RAN: msghandler.py 0x0056 --follow --annotate (--limit 400); msghandler.py 0x0057 --follow --annotate; asserts.py --grep compositeCount / CHAR_CLASS_MONSTER_BASE / CHAR_CLASS_BASE_MASK; a scratch assert-range listing over 0x0080f000-0x00810600; scratch disassembly of 0x008170c0. CONFIRMED: RECV 0x00bc8f68 dispatches 0x56 to 0x0091dd80 -> worker 0x0080fa30, and 0x57 to 0x0091de00 -> worker 0x0080fbd0. CharMsg:4438 `message.compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS` exists verbatim at 0x0091de1f, which is INSIDE the 0x0057 handler and gu


## `0x0059` GAME_SMSG_PLAYER_INFO  *[high]*

**61 messages, 0.6% of the corpus.** Handler `0x0091de90`.

Reached: `CharMsg.cpp`, `CharData.cpp`, `ChCliApi.cpp`, `AvApi.cpp`


**SOURCED** -- the client's own words:

- CharData:178 "slot < arrsize(s_appearanceSlot)" and CharData:180 "data.slot == slot" -- the handler calls this getter at 0x0091deba with slot=3 and field 3 as the packed value, so field 3 IS a CharData appearance word
- ChCliApi:4966 "!(playerId & CHAR_CLASS_BASE_MASK)" at 0x0081048d; that function then does ctx[0x2c]+0x80c, index*0x50, +0x28 -- the same array, the same 80-byte stride and the same name field the handler writes. The client's own word for field 1 is playerId.
- AvApi:1141 "agent" at 0x007dffc0, the sink the handler hands (appearance slot 3, field 4) to as an adjacent byte pair
- CharMsg:4438 "message.compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS" at 0x0091de1f -- 0x8e bytes before this handler, which is how the handler is placed in CharMsg.cpp (it carries no assert of its own)

**OBSERVED** -- the wire:

- 61 of 10944 messages, 4 tapes (40/1/19/1)
- field 1 shares an id space with 0x00B0 field 1: of 0x00B0's distinct values, 29/30 (tape0) and 13/14 (tape2) are also 0x0059 field-1 values in the same tape; 0x00B0 immediately follows 0x0059 33 times
- field 2 was created by an 0x0020 agent-create in the same tape in 58 of 61 cases
- s_appearanceSlot at 0xbc8ac8 is 8 entries of {slot, shift, bits}: slot6=(0,1) slot5=(1,4) slot7=(5,5) slot1=(10,5) slot0=(15,5) slot3=(20,4) slot2=(24,6) slot4=(30,2). Decoding field 3 by that table over all 61 rows: slot 6 splits 33/28 (one bit, balanced -> sex), slot 4 is 0 in 61/61 (2 bits, CHAR_APPEARANCE_RACES, all one race), slot 3 takes only 1..6 and is NEVER 0 (max 6 in 4 available bits).

| field | meaning | label |
|---|---|---|
| 0 | msg_header, opcode 89 | OBSERVED |
| 1 | playerId -- index into the client's player array (ChCliApi ctx[0x2c]+0x80c, stride 0x50); not dense, values repeat as updates | SOURCED |
| 2 | agent id of that player's agent; stored at record+0 and used to reach the agent view | OBSERVED |
| 3 | packed character appearance dword, decoded through s_appearanceSlot; bit 0 = sex, bits 30-31 = race, bits 20-23 = primary profession | SOURCED |
| 4 | secondary profession, 0 = none | INFERRED |
| 5 | per-player flags word (record+0x14); server sends 0, client sets bit 3 itself | OBSERVED |
| 6 | dead: uninitialised server-side fill, never read by the handler | OBSERVED |
| 7 | character name, UTF-16 | OBSERVED |

**Why this and not the nearest rival.** The handler is a pure store: index the ChCliApi player array by field 1, write field 2 at +0, a 32-byte block at +4 (raw field 3, field 5, appearance slot 3, field 4), and two allocated copies of field 7 at +0x24 and +0x28. The client itself calls that index playerId (ChCliApi:4966, same array, same 0x50 stride), which fixes the message as the per-player record. The professions fall out of the two witnesses agreeing: the client extracts appearance slot 3 (4 bits) and hands it to the agent view as an adjacent byte pair with field 4 -- and on the wire slot 3 is 1..6 and never 0 while field 4 is 0..6 and zero half the time. In pre-Searing Prophecies every character has a primary from the six core professions and about half have not yet taken a secondary. Slot 3 = primary, field 4 = secondary; the pair is what the agent view needs to draw and label the character. Nearest rival: PLAYER_NAME / the agent-name message. Rejected -- 0x009B already carries (agent_id, encoded name) and is the agent naming message; 0x0059 binds a playerId to an agent, an appearance word, two professions and a flags word, and the name is only one of six payload fields. Second rival: field 4 = primary profession. Rejected by its own histogram (0 in 30 of 61 rows, impossible for a primary in pre-Searing) once slot 3 is available as the never-zero 1..6 candidate.

**Ruled out:** PLAYER_NAME / AGENT_NAME -- 0x009B is that message (agent_id + encoded name); 0x0059 carries appearance, professions and an agent binding as well; field 4 = primary profession -- 30 of 61 rows are 0; field 4 = level -- capped at 6 in a zone where levels run to 20; field 1 = agent id -- the handler uses it as an array index with an 0x50 stride and the client's assert on that array calls it playerId; the agent id is field 2

**Still open:** Which appearance fields slots 0, 1, 2, 5 and 7 are (face / hair style / hair colour / skin colour / height) -- the widths are known, the names are not.; Whether field 5's other bits are ever set by a live server; the corpus only ever shows 0.; Opcode 0x59 also exists in the SEND direction (table 0x00bc8cb8) with a different, unread meaning -- do not assume the two are the same message.

**For our server:** Sending one per player would make other characters appear with their real name, sex, appearance and profession pair instead of a default model -- and 0x00B0 keys off the same playerId, so it unlocks that message too.


> **Refutation pass.** Everything load-bearing reproduced. (1) msghandler.py 0x0059 --follow --annotate: RECV table 0x00bc8f68 -> handler 0x0091de90, exactly as claimed (and it correctly notes a separate SEND table entry for 0x59). (2) asserts.py --grep confirms CharData:178 'slot < arrsize(s_appearanceSlot)' and CharData:180 'data.slot == slot' verbatim, and they are INSIDE 0x0091d490, which the handler calls at 0x0091deba with slot=3 and field 3 as the packed value -- reach test passes. (3) The ChCliApi:4966 site is at 0x0081048d as claimed, and I disassembled it: call 0x47f660; eax=ctx[0x2c]; cmp esi,[eax+0x814]; eax=[eax+0x80c]; ecx=esi*10; [eax+ecx*8+0x28]. That is the SAME array the handler's sink 0x0080ff40


## `0x0057` GAME_SMSG_MONSTER_COMPOSITE  *[high]*

**50 messages, 0.5% of the corpus.** Handler `0x0091de00`.

Reached: `CharMsg.cpp`, `ChCliApi.cpp`


**SOURCED** -- the client's own words:

- CharMsg:4438 "message.compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS" -- inside this handler at 0x0091de1f, guarding field 2's element count before the rep movsd that copies it
- Array:587 "index < m_count" in the sink 0x0080fbd0, which grows the array to field1+1 and then indexes it

**OBSERVED** -- the wire:

- 50 of 10944 messages, 4 tapes (19/20/4/7); every single one is immediately preceded by an 0x0056
- field 1 equals the field 1 of the 0x0056 directly before it in 50 of 50 cases, 0 exceptions; every 0x0057 key was also seen as an 0x0056 key (0 orphans)
- field 2 element counts: 1 (48 times), 2 (2 times) -- both under the asserted bound of 8
- the sink writes ChCliApi ctx[0x2c]+0x7fc with a 0x30 stride, storing the dwords at record+0x24 and the count at record+0x2c; 0x0056's sink 0x0080fa30 writes the FIRST 32 bytes of the same record in the same array at the same index (verified by disassembly, not by inference)

| field | meaning | label |
|---|---|---|
| 0 | msg_header, opcode 87 | OBSERVED |
| 1 | NPC / monster definition id -- index into the ChCliApi definition array (ctx[0x2c]+0x7fc, stride 0x30); the same key 0x0056 uses | OBSERVED |
| 2 | the composite (appearance) dwords for that definition, at most MONSTER_COMPOSITE_MAX_DWORDS = 8 of them; stored at record+0x24 with the count at +0x2c | SOURCED |

**Why this and not the nearest rival.** ArenaNet names the payload in this handler's own assert: compositeCount, bounded by MONSTER_COMPOSITE_MAX_DWORDS. A composite is the client's assembled character/NPC appearance (CpsApi.cpp, ITEM_FLAG_COMPOSITE, COMPOSITE_COMPONENTS), so the message delivers the appearance dwords for something. What that something is comes from the wire and from the sink together: 0x0056 and 0x0057 write different halves of the same 48-byte record in the same ChCliApi array at the same index, and on the wire the two field 1s agree 50/50 with no orphans. The key is therefore a definition id shared with 0x0056, not an agent id -- 44 distinct keys against 145 distinct agent ids settles that. Nearest rival: AGENT_COMPOSITE / AGENT_APPEARANCE, i.e. field 1 as an agent id. Rejected on two counts: the key space (396..8077) does not overlap the agent id space this corpus uses, and it is re-sent once per NPC type rather than once per spawned agent. Second rival: PLAYER_COMPOSITE. Rejected -- the client's own token is MONSTER_, and the player-facing appearance path is 0x0059's packed CharData word, a different mechanism entirely.

**Ruled out:** field 1 = agent id -- disjoint value range from 0x0020's agent ids, and far too few distinct values; a per-spawn message -- it is re-sent per NPC type per session, always as the second half of an 0x0056/0x0057 pair; the array32[8] being a fixed-size array -- observed lengths are 1 and 2; 8 is the client's asserted maximum, not the wire length

**Still open:** ~~What the individual composite dwords encode (which model piece / colour each one selects) -- that lives in CpsApi/CpsData, not in this handler.~~ **ANSWERED 2026-08-16 by the unit-model arc** ([../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md) §5.4): the composite dwords are archive FILE IDS of geometry-bearing ffna type-2 files (43/43 resolve, every one carrying an FA0 chunk), sent exactly when the 0x0056 file's skeleton carries MODEL_SKELETON_FLAG_COMPOSITED (= no geometry of its own; 36/36 and 8/8 on the same capture). What remains open of the original question is only per-dword colour/piece *selection* when a list has more than one entry (observed lengths 1 and 2). What 0x0056's own eight fields mean is still open; only that it keys the same record was established here.

**For our server:** Emitting 0x0056+0x0057 for each NPC type we spawn is what would give our NPCs their real look instead of whatever the client falls back to for an unknown composite.


> **Refutation pass.** Handler and assert both reproduce, one of their stated grounds is close to vacuous and I struck it, and I found a much stronger replacement. (1) msghandler.py 0x0057: RECV table 0x00bc8f68 -> handler 0x0091de00, as claimed, with 'CharMsg:4438 message.compositeCount <= MONSTER_COMPOSITE_MAX_DWORDS' compiled INLINE at 0x0091de1f guarding [ebx+8] against 8 before the rep movsd -- reach test passes, and the token MONSTER_COMPOSITE is genuinely the client's own word for this payload. (2) I disassembled the sink 0x0080fbd0 myself: array at ctx[0x2c]+0x7fc, m_count at +0x804, stride 0x30 (ebx*3<<4), dwords stored at record+0x24 and the count at record+0x2c. (3) I independently disassembled 0x0056's


## `0x013F` GAME_SMSG_ITEM_CREATE_BAG  *[high]*

**36 messages, 0.3% of the corpus.** Handler `0x00846040`.

Reached: `ItCliApi.cpp`, `ItCliBag.cpp`, `ItCliInv.cpp`


**SOURCED** -- the client's own words:

- ItCliApi:1942 "inventory" -- inside this handler at 0x008460f7, on the result of the hash lookup keyed by field 1
- ItCliBag:167 "slot != m_bagArray.Count()" -- the remove path the handler runs first, searching m_bagArray for an existing bag whose id equals field 4
- ItCliInv:38 "No valid case for switch variable 'bagType'" -- the client's own name for field 2
- ItCliInv:129 "!m_bagEquip" and ItCliInv:140 "!m_bag[bagSlot]" -- the two insert paths, and the client's own name for the derived slot

**OBSERVED** -- the wire:

- 36 of 10944 messages, exactly 9 per tape in all four tapes
- the nine (bagType, field3, capacity) triples are byte-identical in all four tapes: (1, 0, 20), (2, 21, 9), (3, 6, 12), (4, 7..11, 25) five times, (5, 5, 42)
- field 1 is constant within a tape (one value per tape, three distinct across the four)
- field 6 is non-zero for exactly one of the nine -- the 20-slot one -- and zero for the other eight, matching a container that is itself an item versus containers that are not

| field | meaning | label |
|---|---|---|
| 0 | msg_header, opcode 319 | OBSERVED |
| 1 | key of the owning inventory; hashed into the item client's inventory table (ItCliApi:1942 asserts the result). Constant within a session, consistent with the local character's id. | INFERRED |
| 2 | bagType | SOURCED |
| 3 | bagSlot -- used verbatim for types 1 and 4, ignored for 2, 3 and 5 where the client derives 21, 6 and 5 | SOURCED |
| 4 | bag id; any existing bag carrying it is destroyed first, so it is unique within the inventory | OBSERVED |
| 5 | capacity in item slots -- the length of the bag's item-pointer array | SOURCED |
| 6 | index of the item that IS this container, 0 = none; the handler links item->bag both ways and sets item flag 4 | SOURCED |

**Why this and not the nearest rival.** Every identifier in the chain is the client's own: a CBag is allocated, its type is field 2 (bagType), its slot is derived from field 2 and field 3 (bagSlot), its id is field 4, its item-pointer array is sized to field 5, its backing item is itemArray[field 6], and it is inserted into the CInventory the field-1 hash lookup returns. The wire then confirms the shape rather than merely being consistent with it: the same nine containers with the same capacities in every session, one type-2 container that lands in m_bagEquip, five type-4 containers that bump the pane counter, and exactly one container carrying an item of its own. Nearest rival: ITEM_UPDATE_BAG. Rejected -- the handler destroys any existing bag with the same id first and then asserts the destination slot is empty; that is construction, not update. Second rival: STORAGE_OPEN / a merchant-window message. Rejected -- all nine arrive in the login burst of every tape including the two where nothing was ever opened, and five of the nine are ordinary character containers.

**Ruled out:** ITEM_UPDATE_BAG -- constructs a fresh CBag and asserts the destination is empty; a storage/merchant open message -- present in every login burst including sessions where nothing was opened; field 5 = an item count rather than a capacity -- it is the allocation length of the pointer array, which the client then zeroes; field 3 = a free-form slot -- for three of the five types the client overrides it

**Still open:** Which real container each bagType is. The structure is pinned (one goes to m_bagEquip, five are counted panes, one has its own item), but mapping type->'Backpack'/'Equipment Pack'/'Xunlai pane'/'Material Storage' by capacity would be a guess this corpus cannot refute.; Whether field 1 is the character's agent id or a separate inventory handle -- it is a hash key and the corpus only ever shows one value per session.

**For our server:** Nine of these at login is the entire reason the client has an inventory and Xunlai panes to draw; our server sends none, so the bag UI is empty by construction and no item message can land anywhere.


> **Refutation pass.** The mechanism reproduces in full, but two of their SOURCED citations do not survive the reach test and one stated mechanism is invented. (1) msghandler.py 0x013F: RECV table 0x00bcad58 -> handler 0x00846040, as claimed. (2) Inside it: ItCliApi:1942 'inventory' at 0x008460f7 on the result of the lookup keyed by field 1 -- confirmed inline. (3) The remove path 0x00848fb0 carries ItCliBag:167 'slot != m_bagArray.Count()' at 0x00849002 -- confirmed, and the search 0x00849160 does compare [entry+8] against field 4. (4) The insert 0x00849de0 carries ItCliInv:129 '!m_bagEquip' at 0x00849dfb and ItCliInv:140 '!m_bag[bagSlot]' at 0x00849e26 -- confirmed, and the index in that assert is [bag+4], i.e. 


---

# 2. PARTIAL -- mechanism understood, name not earned

These are NOT in `schema/overrides.json`. Each is recorded so the same reading is not
re-derived from scratch next month, and so the specific thing that would settle it is
written down while it is still known.


## `0x009F` -- proposed *GAME_SMSG_AGENT_PROPERTY_UPDATE_INT*, 548 messages (5.0%)

**SOURCED:** ChCliApi.cpp:2112 and :2123 "sourceAgent < 5" (0x00812A26, 0x00812A71) -- inside the worker 0x008128F0. It names the worker's THIRD argument, which 0x009F's handler hardcodes to 0 and 0x00A0's handler (0x0091ED20, same worker) fills from its own field 3

**OBSERVED:** 548 messages, the third most common opcode in the corpus; 174 immediately precede 0x00F0


> **Why it is PARTIAL.** The name holds, but its stated decisive support is refuted and it must not ship as high-confidence NAMED on that reasoning. WHAT VERIFIES: handler 0x0091ed00 -> worker 0x008128f0, correct. Field 2 is the array index -- 0x00812912 cmp edi,[esi+0x84] guarding Array:587 at 0x0081291f, then imul ecx,edi,0x34 over the array at esi+0x7c, then ChCliGetAgent 0x5fc380 with a def==1 gate. Field 3 (ebp+0x14) goes to the record setter 0x818170. Field 1 is bounded by the client's own switch: cmp eax,0x42 at 0x008129c3 and lea edx,[eax-4]; cmp edx,0x3c at 0x00812986. I decoded the main jump table from the r


**What would settle it:** names for the property enum: the client carries no strings for it, only jump tables. Only the valid-id set and each id's target are recoverable statically; what property 66 does -- a probe that creates an agent with and without it, watching the AgentView, is the only way to settle it; the 20 ids inside 0..66 with no case in the main dispatch (5,8,10,16,17,18,33,34,40,43,44,51,52,53,55,56,61,62,63,64): some are live on the float channel instead, and property 8 is observed on the wire here with no case at all


## `0x006D` -- proposed *GAME_SMSG_AGENT_UPDATE_HELD_ITEMS*, 342 messages (3.1%)

**Refutation changed this to:** GAME_SMSG_NPC_UPDATE_WEAPONS

**SOURCED:** ChCliApi.cpp:51 "No valid case for switch variable 'prop'" (0x00810DF3) -- the default arm of the switch inside the worker 0x00810B70. `prop` is the client's own name for the loop variable, and the jump table has nine cases (`cmp ebx,8; ja default`)

**OBSERVED:** 342 messages; 275 immediately follow 0x0020 and 151 are immediately followed by 0x0026 -- the burst


> **Why it is PARTIAL.** The technical work is sound; the RENAME is not, and it should be rejected. What I verified and it all holds: handler 0x0091e1a0 -> worker 0x00810b70, correct. The loop bounds are exactly as claimed -- 0x00810dd6 inc ebx / cmp ebx,2 / jne, and the sibling at 0x00810e30 does inc ebx / cmp ebx,9 / jne at 0x00811096. ChCliApi:51 'No valid case for switch variable prop' sits at 0x00810df3 in this worker and 0x008110b3 in the sibling. ItCliApi:400 'ptr' at 0x00845211 is genuinely inside the item lookup 0x8451e0 the worker calls. I reproduced 291 of 291 non-zero values declared earlier by 0x015E/0x01


**What would settle it:** which slot is the main hand and which the offhand: the item-type numbering is not decoded, only shown to be disjoint; item type 6, the value slot 0's special UI-event path tests for -- it never occurs in this corpus; the identity of prop slots 2-8 individually (0x006E's territory, out of scope here)


## `0x015E` -- proposed *ITEM_UPDATE_LOW_DETAIL*, 263 messages (2.4%)

**Refutation changed this to:** ITEM_LOW_DETAIL (drop the verb; the detail level is what is SOURCED, the update is not)

**SOURCED:** ItCliApi.cpp:2410 (0x00846FCC) 'msg.fileId' -- guarded by `cmp dword ptr [esi + 8], 0`, so the SECOND payload dword is the field ArenaNet calls fileId.

**OBSERVED:** 263 of 10944 messages, on 2 of 4 tapes. 209 are adjacent to another 0x015E: 54 runs, each opening immediately after a 0x0020 and closing immediately before a 0x006E.


> **Why it is PARTIAL.** The DETAIL-LEVEL half of this name is real and I verified every step of it; the UPDATE verb is contradicted by the corpus. Confirmed by disassembly: handler 0x00846FA0 from table 0x00bcad58; the fileId guard is `cmp dword ptr [esi + 8], 0` with the assert `push 0x96a` (= line 2410) at 0x00846FC7 and ecx = the string 'msg.fileId' -- so field 2 is msg.fileId, exact. The second assert is `push 0x97f` (= 2431), expression 'item', at 0x0084702B, after the item-table index -- exact. The log format string at 0xB96DE0 reads as UTF-16 'FileId=0, type=%d' with `push [esi+0xc]` (field 3) as its argument 


**What would settle it:** Fields 4, 5, 7, 8, 9 and what field 6 counts. They land at item+0x21, +0x22, +0x4A, +0x28, +0x24 and +0x48; reading those five offsets' consumers (codescan --field, bounded to ItCliApi/ItCliItem/the vendor and inventory UI) is the next step and is cheap.; Why the message is confined to 2 of 4 tapes. 0x006E is likewise 109+19 on those two tapes and 1+1 on the others, so the bracket travels with it -- but what makes a connection need it was not established.; The value of ITEM_TYPE_* for the seven type values actually seen here. Only ITEM_TYPE_BAG == 3 is SOURCED, and it is the one value this message never carries.


## `0x00B0` -- proposed *PARTY_SET_SIZE*, 164 messages (1.5%)

**SOURCED:** ChCliApi:4966 `!(playerId & CHAR_CLASS_BASE_MASK)` — the index domain of the array this handler writes, in ArenaNet's own words

**OBSERVED:** 164 messages, client table shape [u16, u8], 5 bytes


> **Why it is PARTIAL.** Ran msghandler.py 0x00B0 --follow --annotate --depth 3, disassembled 0x0081ed80, swept .text for event 0x10000048, and rebuilt the timeline myself. The mechanism is exactly as described and I confirm it: 0x00813850 writes {owner = index, value = the byte} into player[index]+0x38 via 0x0081ed80 and fires 0x10000048 once per member; both readers threshold at 1. Field 1 as the group's identifying playerId is solid. THE NAME DOES NOT SURVIVE AS FILED, because the observation carrying it is false. They write: 'the final reconstructed group sizes in the corpus are exactly 1, 2 and 3' and conclude 't


**What would settle it:** Whether the count includes henchmen and heroes or only players. Pre-searing has neither, so the corpus cannot say.; What the 14 messages addressed to group 0 mean — a size on the null group is not obviously meaningful, and the client stores it anyway.; Whether 3 is the ceiling. The corpus is pre-searing only, so the observed maximum is a property of the area, not of the protocol.


## `0x003C` -- proposed *PLAYER_UPDATE_FLAGS*, 160 messages (1.5%)

**SOURCED:** AtName:359 `msg.playerId == AvCharGetPlayerId(m_agent)` — asserted on field 0 of the event THIS handler fires, whose field 0 is this message's field 1. That is the client naming this message's first field.

**OBSERVED:** 160 messages, client table shape [u16, u32, u32], 12 bytes


> **Why it is PARTIAL.** Ran msghandler.py 0x003C --follow --annotate --depth 3, asserts.py --grep AvCharGetPlayerId and CHAR_CLASS_BASE_MASK, a full-.text sweep for event 0x10000067, targeted disassembly of the AtName dispatcher, and my own timeline rebuild. HANDLER: exact. 0x0091d960 -> 0x0080eb70, which resolves the same player array, grows it to index+1 if short, then `and [row+0x34], ~field3` followed by `or [row+0x34], field2` - a masked read-modify-write - and fires 0x10000067 with {playerId, mask, new flags}. Three Array:587 asserts, exactly as claimed. WIRE: every number reproduces exactly - field 1 is a play


**What would settle it:** What bits 0, 1 and 2 mean. The cheapest next step is UiGame's character-summary code at 0x004a8c66: it passes the three bits as three separate arguments into the summary frame message, and the frame's field names or its string ids should label them.; Why bit 1 is never set without bit 2 in 160 samples — that is either a real dependency between two flags or an artefact of a pre-searing-only corpus.; Whether the mask is ever anything other than 7. One district, one campaign area; a post-searing or PvP capture would say.


## `0x009B` -- proposed *AGENT_SET_NAME*, 145 messages (1.3%)

**Refutation changed this to:** AGENT_SET_NAME stands as the best reading, but field 2's meaning is INFERRED and one cited source file is unproven

**SOURCED:** Array.h:587 'index < m_count' at 0x008126D2 and 0x0081270B -- the first payload field indexes a ChCli per-agent record array at ctx+0x7CC, stride 0x38, and the array is grown to fit it.

**OBSERVED:** 145 of 10944 messages across all 4 tapes; 79 distinct agents, 44 distinct strings.


> **Why it is PARTIAL.** The mechanism verifies completely; three supporting claims do not. VERIFIED: msghandler 0x009B -> table 0x00bc8f68 [RECV], handler 0x0091ec60, which does `lea eax, [ecx+8]; push eax; push [ecx+4]; call 0x8126a0` -- a pointer to the inline string, as a string16[32] payload requires. In 0x008126A0: Array:587 at 0x008126D2 and 0x0081270B exactly as cited, array at ctx+0x7CC, count at ctx+0x7D4, and `lea edi,[esi*8]; sub edi,esi; shl edi,3` = stride 0x38 -- exact. The compare-else-free-realloc-copy is there: `call 0x46be20` with -1 (compare), `call 0x46c3a0` then `lea eax,[eax*2+2]` (wcslen*2+2), 


**What would settle it:** A SOURCED word for the string. No assert in ChCliApi, GmAgentDoll or GmAgentCommander names it; the next move is the 0x1000001E handler inside GmAgentDoll (find the case in its message switch and see which child frame the pointer is written to -- a FrameSetText-shaped call would close it).; The other fields of the 0x38-byte record: +0x00, +0x04..+0x17 (an array of 5, per ChCliApi:2112 'sourceAgent < 5'), and +0x30 with a validity byte at +0x33. Knowing them would confirm the record is 'the ChCli view of an agent'.; Whether the 6 messages naming an agent the tape never creates are pre-capture agents or a second id space.


## `0x0161` -- proposed *ITEM_UPDATE_HIGH_DETAIL*, 121 messages (1.1%)

**Refutation changed this to:** ITEM_HIGH_DETAIL (drop the verb; and one quoted client string in the submission is not the client's string)

**SOURCED:** ItCliApi.cpp:2505 (0x00846DA1) 'msg.fileId' -- same guard on the same second payload dword as 0x015E's 2410.

**OBSERVED:** 121 of 10944 messages, on all 4 tapes, in the pre-instance block alongside 0x013A / 0x013E / 0x015A / 0x0148.


> **Why it is PARTIAL.** THE SUBMISSION CONTAINS A FABRICATED QUOTE, and it is one of the five SOURCED items. They quote the client's log line as 'FileId=0, item name=%s. type=%d' and build on it: 'with the string16[64] field passed as the %s. That is ArenaNet naming field 12 the item name.' I read the string at 0xB96E10 as UTF-16 and it is 'FileId=0, item name=%d. type=%d' -- %d, not %s. The conclusion partly survives on other grounds (the call site does `lea eax, [edi+0x30]; push eax` into the 'item name=' slot, and 0x00848250 wcslen's that buffer and heap-copies it to item+0x34, so it is a wide string ArenaNet asso


**What would settle it:** Fields 4-10 (shared with 0x015E) and field 10, which is unique to this message.; Whether field 14 exists on the wire at all. 121/121 decoded to 14 values; msgshape.py could settle whether the client's own format table really declares a tenth-plus slot after the code array.; The encoding of the code[] entries -- ITEM_CODE_TERMINATOR is SOURCED as the sentinel, but the field layout inside each code dword was not read (ItemCode.h has more to give).


## `0x001A` -- proposed *ACCOUNT_UNLOCK_ROW*, 68 messages (0.6%)

**SOURCED:** The worker 0x00807E90 is bracketed on BOTH sides by asserts from the same translation unit: AcctCliUnlock.cpp:105 "unlock" at 0x00807E40 and AcctCliUnlock.cpp:189 "deleted" at 0x00808168. Functions from one .cpp are contiguous, so 0x00807E90 is in P:\Code\Gw\Account\Cli\AcctCliUnlock.cpp.

**OBSERVED:** It is a three-phase bulk transfer, read straight out of the three handlers. 0x0018 sets obj+8 from its payload count, memmoves its array32[8] into obj+0, and raises frame message 0x100000BF. 0x001A appends a 3-dword record {row id, running total, element count} to a staging array at obj+0x50 and appends its `count` dwords to a staging array at obj+0x40. 0x001B moves obj+0x40/0x50 into the LIVE arrays at obj+0x10/0x20 and zeroes the staging. Commit semantics — the client does not see a partial list.


> **Why it is PARTIAL.** PARTIAL is the right verdict and it stands, but one of their SOURCED bullets is false and contradicts their own reasoning paragraph. RAN: msghandler.py 0x001A --follow --annotate; msghandler.py 0x0018 and 0x001B; a scratch assert-range listing over 0x00807400-0x00808400; a scratch .text scan for 0x100000BF; read authsrv.py around line 726. CONFIRMED: RECV table 0x00bc89b0 dispatches 0x1A to 0x00804730, which copies `count` dwords off the wire to the stack and calls 0x00807e90 with ecx = [tls+0x28]+0xB4. The worker is exactly what they describe: append the row id to the list at obj+0x60 (0x59d1


**What would settle it:** Which account list this is: unlocked skills, unlocked PvP items/runes, unlocked heroes, or something else. The cheapest resolution is to chase the readers of the committed arrays at obj+0x10 and obj+0x20 (obj = [tls_ctx+0x28]+0xB4) and see which UI module reads them — GmUnlockBlurb.cpp and VnAccountFeaturesSummary.cpp are the candidates the assert strings suggest.; What distinguishes a 3-dword row from a 5-dword row (43 vs 25 in one run).; What frame message 0x100000BF, raised by the 0x0018 that opens the stream, is handled by — that would name the feature directly, and it has exactly one referencer in the image.


## `0x0115` -- proposed *GAME_SMSG_GADGET_SET_FLAGS*, 44 messages (0.4%)

**SOURCED:** GdCliApi:429 "result" and GdCliApi:430 "agentDef == GW_AGENTDEF_GADGET" at 0x0083ef82/0x0083ef9c -- that sibling function calls the SAME lookup 0x005fc380 and asserts its agentDef output equals the literal 2 (cmp dword ptr [ebp-8], 2). The 0x0115 chain does the identical `cmp ... 2` on the identical output slot, so the client's own words say this message is gadget-only.

**OBSERVED:** 44 of 10944 messages, 4 tapes (12/22/3/7); all 44 immediately preceded by an 0x0020 agent-create


> **Why it is PARTIAL.** The gadget half is even better supported than they argued; the FLAGS half is correctly left unverified. (1) msghandler.py 0x0115: RECV table 0x00bca740 -> handler 0x00921d70, as claimed; it calls 0x0083f410(field1, field2), which calls 0x005fc380(agentId, &out1, &out2), tests the return, compares one out-slot against 2, and only then calls 0x0083f710. (2) asserts.py --grep GW_AGENTDEF puts 'GdCliApi:430 agentDef == GW_AGENTDEF_GADGET' at exactly 0x0083ef9c and 'GdCliApi:429 result' at exactly 0x0083ef82, as claimed. I disassembled the sibling from 0x0083ef60 and it does call the same 0x005fc38


**What would settle it:** What each bit of field 2 means. It needs a capture where a gadget actually changes state (open a chest, trigger a door) -- the load-burst corpus only ever carries 0.; Whether GdCliBase.cpp is really the module for 0x0083f710; that attribution is by address adjacency (GdCliBase:167 precedes it, no assert inside it).


## `0x0121` -- proposed *GAME_SMSG_GUILD_INFO*, 29 messages (0.3%)

**SOURCED:** GuCliApi:202 "guild" at 0x008406f7 and GuCliApi:340 "guild" at 0x008409d5 bracket this handler (0x008408b0..0x00840990), placing it in P:\Code\Gw\Guild\Cli\GuCliApi.cpp between those lines; the handler carries no assert of its own

**OBSERVED:** 29 of 10944 messages, and only in the two tapes with heavy player traffic (18/0/11/0)


> **Why it is PARTIAL.** PARTIAL is the right verdict and the structural description is unusually accurate -- every record offset they quote checks out -- but the SOURCED basis is thinner than the label suggests. (1) msghandler.py 0x0121: RECV table 0x00bca870 -> handler 0x008408b0, as claimed, 20 catalog entries matching the card. (2) asserts.py --file GuCliApi puts 'GuCliApi:202 guild' at exactly 0x008406f7 and 'GuCliApi:340 guild' at exactly 0x008409d5, bracketing the handler 0x008408b0..0x00840990, and the handler indeed carries no assert of its own -- they flagged this honestly. (3) FrApi:3901 'msgId >= FRAME_MSG


**What would settle it:** Which of fields 7..13 is background colour, detail, emblem, pattern and trim. The block is copied verbatim so the handler names none of them; VnGuildTabard*/ConstColor would have to be read to split it.; Fields 5, 6, 14, 16 and 18. Each is a bare store to a known record offset with no assert and a near-constant wire value.; Where the guild index in field 1 is bound to a player -- 0x0059 does not carry it, so the association arrives in another message (0x003C is the candidate: it precedes 8 of the 29).


---

# 3. Corpus patterns, independent of any name

These were mined from the message stream WITHOUT reference to what any opcode is
called -- the question is what shapes recur, not what they mean. The precedent is
T3 in [../tape/FINDINGS.md](../tape/FINDINGS.md), which found one such idiom by hand
and in doing so refuted a written claim in this repo.

All analysis is complete and every number re-derived. Writing up.

# Recurring message idioms in the four live GAME_SMSG tapes

Corpus loaded exactly as `evidence.py` does (`tape.chain` → `tape.load_tape` → `codec.decode_stream`), plus a **client→server** timeline I built the same way (`tape._segments` on `wire.jsonl` c2s + the channel file's c2s plaintext, mask `0x8000`). Both framings are 100% clean: **10,944 GAME_SMSG / 146 opcodes** and **371 GAME_CMSG / 20 opcodes**, 0 bytes carried past the end of any of the eight streams. Scripts are in `C:\Users\<user>\AppData\Local\Temp\claude\C--gd-Rurik--claude-worktrees-r0b-live-capture-ready-80ced7\1e39e3dd-16ac-4e05-86f1-a86859caab2f\scratchpad\idiom_*.py`.

## 0. Correct the tape labels first — the cards and the brief are wrong

**OBSERVED.** The card header (and this task's brief) says the four tapes are *Lakeside → Lakeside → Ashford → Lakeside*. Decoded from each tape's own single `0x0199`, they are:

| tape | msgs | `0x0199` field[2] | map | `0x0199` field[3] |
|---|---|---|---|---|
| t0 | 3,981 | 148 | **Ascalon City** | 0 |
| t1 | 2,633 | 146 | Lakeside County | 1 |
| t2 | 726 | 164 | Ashford Abbey | 0 |
| t3 | 3,604 | 146 | Lakeside County | 1 |

This matches `studies/tape/FINDINGS.md` T9 exactly; the wrong label is a hardcoded string at `evidence.py` line 134. It matters because **two tapes are outposts and two are explorables**, and that split turns out to be the largest phase signal in the corpus (§6). `0x0199` field[3] separates them **4/4** — 0 for both outposts, 1 for both explorables.

Durations used for all rates: 48.6 / 147.6 / 14.0 / 186.2 s (393 s total).

---

## 1. `0x001E` is a millisecond clock delta, and the deltas partition the session exactly

**OBSERVED.** 3,971 messages (36.3% of the corpus), per tape 1252 / 1097 / 111 / 1511. Field[1] is a **millisecond delta**, and summing it reconstructs the tape's own wall clock:

| tape | n | Σdeltas[1:] | first→last span | error |
|---|---|---|---|---|
| t0 | 1252 | 47,761 ms | 47,762 ms | **−1 ms** |
| t1 | 1097 | 146,890 ms | 146,892 ms | **−2 ms** |
| t2 | 111 | 13,268 ms | 13,250 ms | +18 ms |
| t3 | 1511 | 185,390 ms | 185,380 ms | **+10 ms** |

Running error against wall clock never exceeds a 42 ms spread over 186 s (t3: −15 to +26 ms). This is a check the artifact could have refuted at any of 3,967 steps and did not.

**It is not periodic, and that is a divergence from our server.** Cadence is 26.21 Hz in Ascalon City and 7.47 / 8.38 / 8.15 Hz in the other three; inter-arrival CV is 0.80–0.88, median delta 21 ms (t0) vs 59–76 ms (t1–t3), max 520 ms. `authsrv.py` sends it on a fixed `TICK_SECONDS = 0.05` sleep (CV ≈ 0). ArenaNet emits a clock stamp **per flush of world updates**, not on a timer — 1,067 of t3's segments carry one tick, 432 carry two, 6 carry three, and a 1 ms delta is the second stamp inside one segment.

**Consequence for every other analysis here:** `0x001E` interleaves everything and destroys contiguity. All n-grams below are measured with it removed. That single decision is what produced §3.

---

## 2. Periodic: exactly one thing, and it settles an UNVERIFIED question

**OBSERVED.** I scanned inter-arrival CV for every (opcode, tape) with n ≥ 6. **`0x000C` and `0x000D` are the only periodic messages in the corpus.** The next-lowest CV in the whole scan is 0.586.

| tape | n | mean period | CV |
|---|---|---|---|
| t0 | 10 | 5.0008 s | 0.0031 |
| t1 | 29 | 5.0014 s | **0.0006** |
| t2 | 3 | 4.9996 s | 0.0001 |
| t3 | 37 | 5.0023 s | 0.0022 |

They strictly alternate `C D C D …` in every tape — **79/79 pairs, no exception** — and per-tape counts are identical vectors (10, 29, 3, 37).

**`0x000D`'s dword is the elapsed milliseconds since its `0x000C`.** Over 79 pairs, |gap_ms − dword| has median 1.3 ms (t1), 0.4 ms (t2), 1.0 ms (t3).

**And the third leg is in the client stream.** Building the c2s timeline gives `GAME_CMSG 0x0009` = **79**, per tape (10, 29, 3, 37) — the same vector again, a three-way exact match. Pairing them directly:

- **79/79** `0x000C` have a `0x0009` reply inside their own 5 s window.
- **0/79** `0x0009` are unprompted (none lacks a `0x000C` within 1.0 s before it).
- Client turnaround: median **8.0 ms**, mean 13.3 ms.

> **This resolves `studies/cmsg/FINDINGS.md` §3, which says of `0x0009`: "Whether it is a reply, or a timer the server's messages reset, is UNVERIFIED."** It is a **reply**. The exchange is a three-message round-trip: server `0x000C` → client `0x0009` → server `0x000D[rtt_ms]`. It also explains T5's retracted "unconditional 5 s heartbeat" mechanically — the client stopped when the tape stopped because nothing was pinging it. Note the strongest single number: tape 3 carries **37 `0x000C` spanning 4.625→184.707 s**, and `studies/cmsg` independently counted **37 client `0x0009` from 4.6 s to 184.7 s** in the labelled run of that same tape.

`0x0009`'s payload is `[·, 16, 0]` in 76 of 79 sends, `[·, 17, 0]` twice, `[·, 33, 0]` once.

---

## 3. The agent-create idiom, and a rule with zero exceptions — this corrects D2

**OBSERVED.** With `0x001E` removed, **`0x00F0 → 0x0020` is 472/472 = 1.000**, and `0x00F0` field[1] equals `0x0020` field[1] in **472/472**. Every `0x00F0` in the corpus is the immediate preamble to the creation of that same agent.

**The rule that decides which creates get one is `0x0020` field[4]:**

| `0x0020` field[4] | n | preceded by `0x00F0` | followed by `0x0115` | carries `0x006E→0x0048` | field[12] tag |
|---|---|---|---|---|---|
| 0 | 11 | **0/11** | 0/11 | 0/11 | (0) |
| 1 | 44 | **0/44** | **44/44** | 0/44 | (0) |
| 5 | 130 | **130/130** | 0/130 | 76/130 | `play` 130/130 |
| 9 | 342 | **342/342** | 0/342 | 0/342 | `mon1` 166, `nonc` 121, `band` 20, `anim` 18, `play` 17 |

Three exceptionless rules fall out, each one arithmetically tight:

- **`0x00F0` occurs iff field[4] ∈ {5, 9}.** 472 = 130 + 342, and `0x00F0`'s corpus total is exactly 472.
- **`0x0115` occurs iff field[4] == 1.** 44/44 with, 483/483 without; `0x0115`'s corpus total is exactly 44.
- **`0x006E`/`0x0048` occur only inside kind-5 creates.** 76/130 kind-5, **0/397** everything else.

> **CONTRADICTS `studies/divergence/FINDINGS.md` D2, and in the same shape T3 was wrong.** D2 says of `0x00F0`: *"343 of 472 arguments are an agent id created earlier in the same stream… The 129 arguments not traced to a create inside the captured window are **unexplained and not invented past**."* and *"followed by a tick or the next `0x0020` (285 and 187 times)"*.
>
> I reproduce D2's numbers exactly — in the raw stream `0x00F0` is followed by `0x001E` 285 times and by `0x0020` 187 times, and only **285/472** of its agents were created by an *earlier* `0x0020`. **D2 looked backwards.** Looking forwards with the clock stamp removed, **472/472** are created by the *immediately following* `0x0020`, with **0 remaining**. There is nothing unexplained: `0x00F0` is a create *prefix*, not a post-create effect application.
>
> D2 also records the create ratio as *"stable across connections at ≈0.93 (191/205, 80/109, 22/25, 179/188)"*. It is not a ratio — it is an exact identity conditioned on field[4], and the 55 creates that lack `0x00F0` are precisely the 11 kind-0 and 44 kind-1 ones.

**The removal side is bare, quantified across all four tapes.** Taking the maximal same-agent run around each `0x0021`: **413 of 416 (99.3%) are a lone `0x0021`**. The three exceptions are two `0029 0021` and one `0100 0021`. T3's "134 of 134" holds and now has a corpus-wide figure with its exceptions named.

**Create templates by frequency** (maximal same-agent run containing each `0x0020`, 527 creates, 29 distinct templates):

| n | % | template | tapes |
|---|---|---|---|
| 132 | 25.0 | `009F 00F0 0020 006D 0026` | t1=5, t3=127 |
| 73 | 13.9 | `00F0 0020` | all four |
| 68 | 12.9 | `009B 00F0 0020 006D` | t0=55 |
| 67 | 12.7 | `00F0 0020 006E 0048` | t0=66, t2=1 |
| 43 | 8.2 | `0020 0115` | all four |
| 28 | 5.3 | `009B 00F0 0020` | all four |

Only **5 of 527** creates are a bare `0x0020`.

**The two 2.00 s windows generalise, and they are strictly `mon1`-only.** Re-measured over all four tapes and broken out by the agent's create profile:

- `0x00F1[·, 0x0000]` at 2.00 ± 0.06 s **after** create: **148/148** for kind-9 `mon1`; 2/4 for kind-9 `nonc`; **0 for everything else**.
- `0x00F1[·, 0x1000]` at 2.00 ± 0.06 s **before** remove: **141/141**, all kind-9 `mon1`.

T3 measured n = 132 each on the Lakeside pair. The larger corpus gives 148 and 141, still exceptionless on `mon1`, and adds that no other agent class exhibits the window at all.

---

## 4. The instance-load prologue is a fixed template — 38 opcodes in one fixed order

**OBSERVED, and this is the strongest idiom in the corpus.**

**38 opcodes occur exactly once in every one of the four tapes**, and **all 38 appear in one identical order in all four**, entirely within the first 0.752 s:

```
017C 0186 017D 0199 0144 0148 00EA 00EB 00EC 00ED 0030 01AB 0195
000F 00F2 007C 007D 0037 00B7 00B6 00DA 008B 008A 00DB 00E9 00EF
001F 006B 0119 011C 01D2 01CB 01D3 01B2 01BE 01BD 016E 018E
```

It arrives in **two blocks** separated by a ~0.5 s silence:

**Block A — the prologue proper**, everything up to and including the single `0x0195`: 64 / 67 / 69 / 71 messages, ending at t = 0.138 / 0.125 / 0.108 / 0.147 s.

- Its **first 9 messages are identical in all four tapes**: `017C 0186 017D 0199 0144 0148 0161 013A 013F`.
- **19 opcodes have identical per-tape counts inside it**: `0030` `0099` `00EA` `00EB` `00EC` `00ED` `013A`(7) `013F`(9) `0144` `0147`(4) `0148` `015A`(6) `017C` `017D` `0186` `0195` `0197`(2) `0199` `01AB`.
- A **4-message cycle `0161 013A 015A 013E` repeats exactly 6 times per tape** — 24/24 corpus-wide, every one inside a prologue.
- Then a **run of 7 × `013F` followed by a run of 4 × `0147`**, 4/4 tapes.
- Then a **contiguous 7-message block `00EA 00EB 00EC 00ED 0030 0099 01AB`**, exactly once per tape, 4/4, at t = 0.076 / 0.051 / 0.039 / 0.074 s. Four of those seven opcodes have corpus total = 4, i.e. they exist nowhere else.
- Pairwise LCS of the four prologues: 60–66 of 64–71.

**Block B — the character/account dump**, from just after `0x0195` to the last singleton: 735 / 77 / 244 / 80 messages over 34 / 2 / 2 / <1 ms of wall clock. Its 25 singleton opcodes are in **identical order 4/4** despite the block itself varying 9× in length. The two Lakeside blocks are near-identical whole (LCS ratio 0.981, 77 vs 80 messages).

**Caveat, stated because it bounds the claim:** all four loads are one character on one account in one session. "Identical 4/4" is four samples that share a character record — the *counts* (6 cycles, 7 × `013F`, 4 × `0147`) may be properties of that character rather than of the protocol. The *order* is the part that is hard to explain that way.

---

## 5. Deterministic adjacency, with field-level subject matching

**OBSERVED.** Every pair below is measured on the `0x001E`-filtered stream. "Same subject" means one field of A equals one field of B in that fraction of occurrences.

| idiom | adjacency | totals (A / B) | subject link |
|---|---|---|---|
| `0x00F0 → 0x0020` | **472/472** | 472 / 527 | A[1] == B[1], **472/472** |
| `0x006E → 0x0048` | **130/130** both ways | 130 / 130 | A[1] == B[1], **130/130** |
| `0x0020 → 0x0115` | **44/44** (of `0x0115`) | 527 / 44 | A[1] == B[1], **44/44** |
| `0x0056 → 0x0057` | **50/50** (of `0x0057`) | 62 / 50 | A[1] == B[1], **50/50** |
| `0x0121 → 0x009F` | **29/29** | 29 / 548 | A[1] == B[3], **29/29** |
| `0x0107 → 0x0020` | **26/26** | 26 / 527 | A[1] == B[2], **26/26** |
| `0x0161 → 0x013A` | **28/28** (of `0x013A`) | 121 / 28 | A[1] == B[1], **28/28** |
| `0x00B0 → 0x00B1` | 161/164, 161/162 | 164 / 162 | A[1] == B[**2**], **161/161** |
| `0x00A6 → 0x009F` | 130/136 | 136 / 548 | A[1] == B[2], **130/130** |
| `0x002B → 0x0029` | 160/163 | 163 / 987 | A[1] == B[1], **160/160** |
| `0x006D → 0x0026` | 151/155 (of `0x0026`) | 342 / 155 | A[1] == B[1], **151/151** |
| `0x0080 → 0x0081` | **15/15** | 15 / 21 | no field agrees ≥95% |
| `0x00F4 → 0x003C` | **13/13** | 13 / 160 | A[1] == B[1], **13/13** |
| `0x002D → 0x0025` | **10/10** | 10 / 201 | A[1] == B[1], **10/10** |
| `0x005D → 0x005E` | 23/24, **23/23** | 24 / 23 | no field agrees ≥95% |
| `0x0198 → 0x0196` | **14/14** | 14 / 15 | — |
| `0x0196 → 0x0197` | **9/9** (of `0x0197`) | 15 / 9 | — |
| `0x009F → 0x00F3` | **9/9** (of `0x00F3`) | 548 / 9 | no field agrees ≥95% |

Note `0x00B0 → 0x00B1` links A[1] to B's **second** word, not its first — so `0x00B1` reads as `[new, old]`, which a "both are the same field" assumption would get backwards.

**The longest exact idiom: the outpost join chain.**
`00B0 00B1 00A6 009F 003C 00F0 0020 006E 0048` occurs **68 times** contiguously (t0 = 67, t2 = 1). Prefix counts step down cleanly: len 2 → 161, len 3–4 → 130, len 5–7 → 116, len 8–9 → **68**.

---

## 6. `0x009F` is a selector, and its field[1] predicts the continuation

**OBSERVED.** `0x009F` is the third-commonest opcode (548) and its field[1] takes 17 values. Three of them are near-deterministic gates:

- **field[1] == 66 → `0x00F0` naming the same agent: 153/153.** Occurs *only* in the two Lakeside tapes (13 + 140). This is the general form of T3's `0x009F[66, agent, 0]` worm-burst opener.
- **field[1] == 30 → `0x00B0`: 71/72.** Occurs *only* in the two outposts (59 + 13).
- field[1] == 36 → `0x003C`: 139/184 (75.5%), and the `0x003C` names a **different** subject 139/139 — so this one is a sequence, not a transaction.

---

## 7. The skill cycle: four opcodes, four cycles, and the recharge is on the wire

**OBSERVED.** `0x00E3` / `0x00E4` / `0x00E5` / `0x00E6` have the exact-count vector **(0, 0, 0, 4)** — 4 each, tape 3 only, 16 messages total. Grouped by (agent, skill id) they form **four complete cycles in the order `00E4 → 00E5 → 00E3 → 00E6`, 4/4, with no interleaving between the two skills**.

| skill | cycle | `00E4→00E5` | `00E5→00E6` | `00E5` field[4] | error |
|---|---|---|---|---|---|
| 153 | 1 | 1.003 s | 8.003 s | **8** | +0.003 s |
| 153 | 2 | 1.000 s | 8.014 s | **8** | +0.014 s |
| 105 | 1 | 2.642 s | 6.000 s | **6** | −0.000 s |
| 105 | 2 | 2.571 s | 6.009 s | **6** | +0.009 s |

**`0x00E5` field[4] is the recharge in seconds, and `0x00E6` fires exactly that long after it — 4/4, max error 14 ms.** The two values, 8 and 6, are exactly the recharge times the client's own skill table gives for skills 153 and 105 (T4: Vampiric Gaze 8 s, Deathly Swarm 6 s). That is the client's table and the wire agreeing without either being used to produce the other.

The `0x00E3` timestamps (10.493, 20.269, 13.240, 23.026 s) reproduce T1's SKILL_ACTIVATED table to the millisecond, which is what tells me the grouping is right.

`0x00E4 → 0x00E5` equals the declared cast time for skill 153 (1.0 s, twice) but overruns it for skill 105 (2.64 / 2.57 s vs 2.0 s declared). **UNRESOLVED** — I will not name `0x00E4` on two samples with a 0.6 s discrepancy.

---

## 8. Phase structure, normalised

**OBSERVED.** The load window is the first **2.0 s** of each tape: 2.0% of the 393 s of wall clock, carrying **19.7% of all messages** (2,155 of 10,944).

- **50 opcodes are ≥90% load-concentrated.** 38 of them are the once-per-tape set from §4; the rest are `001A`(68/68), `013F`(36/36), `013A`(28/28), `015A`(27/28), `013E`(25/26), `0147`(16/16), `0196`(15/15), `0198`(14/14), `008D`(14/14), `0197`(9/9), `0050`(6/6), `01DF`(4/4).
- **12 opcodes never appear in the first 2 s** (n ≥ 8): `002B`(163) `00A0`(25) `005D`(24) `005E`(23) `007E`(22) `008C`(21) `0081`(21) `00A3`(19) `0080`(15) `002A`(12) `002D`(10) `00EE`(9).

**Outpost vs explorable, steady state only (t ≥ 2 s), per 100 s** — this is where normalisation earns its keep, since the tapes differ 13× in length:

| outpost-exclusive | outpost rate | explorable |
|---|---|---|
| `0x015E` | 170.1 (n=97) | **0.0 (n=0)** |
| `0x00B0` | 159.6 (n=91) | **0.0** |
| `0x00B1` | 156.1 (n=89) | **0.0** |
| `0x003C` | 145.6 (n=83) | **0.0** |
| `0x00A6` / `0x006E` / `0x0048` | 112.3 each (n=64) | **0.0** |

| explorable-exclusive | outpost | explorable rate |
|---|---|---|
| `0x0026` | **0.0** | 46.3 (n=152) |
| `0x00A0` | **0.0** | 7.6 (n=25) |
| `0x00A3` | **0.0** | 5.8 (n=19) |
| `0x00A2` | **0.0** | 4.6 (n=15) |
| `0x0107` | **0.0** | 2.7 (n=9) |

Sanity check on the normalisation: `0x000C` and `0x000D` come out at 19.3–21.0 per 100 s in both groups — exactly the 20/100 s a 5 s timer should give.

**Three opcodes are confined to a single tape** (n ≥ 8): `0x001A` (68, t0), `0x01DE` (20, t0), `0x019F` (8, t0).

**Mass-removal bursts are a load artifact, not a teardown.** Tape 0's `0x0021` runs are 52 (t=0.977 s), 49 (1.837 s), 13 and 30 (2.917 s) — each entirely inside one wire segment — and **150 of t0's 160 removals land in the first 3 s**. The other tapes: 1/87, 1/6, 0/163. Ascalon City settles its population by deleting ~150 agents in the first three seconds.

---

## 9. Exact-count pairs, ranked by how hard they are to explain by chance

**OBSERVED.** Total-count coincidences are mostly noise (I found 34 pairs within 5% and nearly all have unrelated per-tape distributions). The discriminating test is an identical **per-tape count vector**:

| vector (t0,t1,t2,t3) | opcodes | total | what it implies |
|---|---|---|---|
| (109, 1, 19, 1) | `0x0048` `0x006E` | 130 | plus 130/130 adjacency, same agent — **one transaction**, not two messages |
| (10, 29, 3, 37) | `0x000C` `0x000D` | 79 | the ping (§2), with c2s `0x0009` making it a three-way match |
| (1, 7, 8, 4) | `0x0051` `0x0054` | 20 | both prologue/load-phase, both `dword + string16` family |
| (0, 0, 0, 4) | `0x00E3` `0x00E4` `0x00E5` `0x00E6` | 4 each | the skill cycle (§7) |
| (2, 2, 0, 1) | `0x010E` `0x0111` | 5 | too small to rest on |
| (1, 1, 1, 1) | **38 opcodes** | 4 each | the fixed load sequence (§4) |

Near-misses worth naming: `0x00B0`(164) / `0x00B1`(162) — vectors (125,2,35,2) vs (123,2,35,2), off by 2 in Ascalon only, alongside 161/161 adjacency. And `0x00A6`(136) vs `0x006E`/`0x0048`(130) — vectors (112,1,22,1) vs (109,1,19,1), a consistent surplus of 3 per outpost.

---

## 10. Smaller observations worth recording

- **The transfer tail is three messages, not two.** `0x0028 → 0x01A5 → 0x0099`, **3/3** in the three transferring tapes. T8/T9 documented `0x01A5 → 0x0099`; the `0x0028` immediately before it is consistent 3/3, though `0x0028`'s corpus total is 18 so it is not exclusive to the transfer.
- **`0x002E` carries the ROTATE constants.** Read as float32, field[3] is `0x40060A92 = +2.094395` (= 2π/3) in **58/64** cases, and field[2] is ±inf in **9/64** — the same two constants `studies/cmsg` C13 used to identify `GAME_CMSG 0x0040` as ROTATE_PLAYER. This is the server-side twin and nobody has looked at it.
- **`0x001A` is one burst.** All 68 arrive at t = 0.718 s in tape 0, each with a distinct field[1], nested-struct length 3 (43×) or 5 (25×). Consistent with D3's bracketed-run finding.
- **`0x015E` is a bulk dump with 263 distinct field[1] values over 263 messages**, outposts only (174 + 89), followed by another `0x015E` 209 times or by `0x006E` 54 times.
- **`0x0026` (GAME_SMSG) field[2] is 9 in 153 of 155 sends**, 8 in the other 2. Unrelated to `GAME_CMSG 0x0026`.
- **The live client stream has 20 distinct GAME_CMSG opcodes**, framing 100% clean, per tape 83 / 188 / 30 / 70: `0x003D`(161) `0x0009`(79) `0x00C1`(29) `0x0039`(15) `0x003E`(15) `0x003B`(11) `0x0092`(10) `0x0047`(9) `0x0026`(9) `0x0012`(8) `0x0091`(4) `0x0088`(4) `0x0090`(4) `0x0008`(4) `0x0046`(4) `0x000D` `0x0093` `0x0063` `0x0040` `0x002B`(1 each). `studies/cmsg` §4 counts 23 witnessed from labelled loopback runs — but this is the client talking to **ArenaNet**, and several here (`0x003B`, `0x0012`, `0x0088`, `0x0090`, `0x0091`, `0x0008`, `0x0063`) do not appear in that file's named or added lists. Worth a census pass; I did not verify the full 23-item set so I am not claiming a number.

---

## 11. What I could not settle — UNRESOLVED, with what was ruled out

- **Why Ascalon City ticks at 26 Hz and the other three at ~8 Hz.** Ruled out: population count from `0x0199` field[1] (Ashford declares 22 and ticks at 8.38 Hz, so it is not headcount) and total message rate (Ashford runs 54.8 msg/s at 8.38 Hz while Lakeside runs 19.4 msg/s at 8.15 Hz). Not ruled out: outpost-vs-explorable, or a per-server-instance setting.
- **What `0x0020` field[4] means.** It is a clean 4-valued selector {0, 1, 5, 9} that predicts three burst rules exceptionlessly, and value 5 co-occurs with the `play` tag 130/130 — but kind 9 spans five different allegiance tags including 17 `play`, so it is *not* simply the allegiance. I will not name it.
- **`0x00E4`.** It opens the skill cycle 4/4 but its gap to `0x00E5` matches the declared cast time for one skill and overshoots by ~0.6 s for the other, on n = 2 each.
- **Whether the fixed 38-message order is protocol or character.** One session, one character, four loads (§4 caveat). A second live capture on a different character would separate these in one decode, and it is the cheapest test on this list.
- **`0x0080 → 0x0081` (15/15) and `0x005D → 0x005E` (23/23 backwards).** Deterministically adjacent, but no field pair agrees in ≥95% of occurrences, so I cannot say they are about the same subject.


---

# 4. What this changes for the server

Ranked by what is buildable **now** against what still needs a run. Our server
currently sends about a dozen opcode types.

### Tier 1 — buildable today, largest effect per line of code

> **Status re-checked against the code 2026-08-11 — most of this list has landed.** It was
> written 2026-08-10 and read as a to-do list for a day after it stopped being one. Send
> sites now exist for **`0x00F0`, `0x0026`, `0x002B`, `0x0029`, `0x002E`, `0x0021` and
> `0x0048`**. Item **4 is built and verified at its send site**; items **2 and 3 have send
> sites**, which is weaker — each also carries an *ordering* rule (`0x00F0` before every
> `0x0020`, `0x002B` before `0x0029`) that a grep cannot confirm, so they are marked
> PARTIAL rather than done. Item 1 is **half** built; item 5 is **not started**.
> `authsrv.py` is the authority; this list is not.

1. **`0x001E` with a real elapsed-ms delta, emitted per flush rather than on a timer.**
   *The single most common message on the wire and we have never sent it correctly.*
   It drives every client-side timer and interpolation between movement legs. ~~We send
   it on a fixed 0.05 s sleep (CV ~ 0)~~; ArenaNet stamps it per world-update flush (CV
   0.80-0.88, 445 distinct deltas, up to 520 ms). Change: stamp the true delta at
   flush time. **No new message needed — this is a fix to one we already send.**
   **HALF DONE 2026-08-11:** the delta is now *measured* — `delta_ms` comes from a
   `time.perf_counter()` difference and the send is skipped when it rounds to 0 — so it is
   no longer a constant. But it is still emitted from a `time.sleep(TICK_SECONDS)` loop
   rather than per world-update flush, so the cadence is still ours and not the client's
   work pattern. **The item's actual ask stands; only its "we send a constant" premise is
   retired.**

2. 🔶 **PARTIAL — both messages now have send sites** (`AGENT_INITIAL_STATUS`,
   `AGENT_UPDATE_FLAGS`); whether the *ordering* rule below holds at every create is
   unverified. **`0x00F0` immediately before every `0x0020`, and `0x0026` after.** 472/472 of
   ArenaNet's creates carry the status preamble; only 5 of 527 are a bare create — and
   the bare form is what we send. This is what lets us **spawn an agent already in a
   state** (already burrowed, already dead) instead of creating it clean and
   correcting after, which is the 472-message D2 gap. `0x0026` is the fifth message of
   the burrow burst we could not send and the natural place to toggle flags after
   creation. Guard: `0x0026`'s merge **clears every set bit above bit 7 outside
   0x3f0000**.

3. 🔶 **PARTIAL — both have send sites** (`AGENT_UPDATE_SPEED` ×2, `AGENT_MOVE_TO_POINT`
   ×3); the ordering and the bounds check are unverified from here. **`0x002B` before
   `0x0029`, with a bounded speed and a real facing byte.** NPC
   patrol and chase pacing has no other driver. Speed must be in `[0.01, 1.0]` — a
   value above 1.0 trips the client's own assert — and the third field is `facing`,
   not the "type" our comment claims. **Hazard, flagged in §0x0025:** do not emit
   `0x0025`'s vector as intended movement with facing != 1 until the facing-vs-
   movement question is settled, or the client will be 26.57–180° off.

4. **`0x002E` for NPC facing.** ✅ **BUILT 2026-08-11** (`b37db6f`, `authsrv.py:1467`).
   ~~Previously never sent because nobody knew what went in~~ it. Field 2 = absolute
   target angle in radians (or ±inf to spin), field 3 = turn rate in rad/s, inside
   `[pi/100, 20pi]`. Keep both typed `dword` in the catalog — and note the commit records
   that our turn rate is one constant where **ArenaNet's is per-creature**, so this is
   built but not yet faithful.

5. ✅ **BUILT 2026-08-11. The tick/ping loop: a 5 s `0x000C` and a `GAME_CMSG 0x0009`
   handler.** ~~Today every one of the client's replies lands on our silent-ignore path.
   and per D9(b) a schema-unknown c2s opcode **discards whatever shared its TCP read** —
   so this is a correctness fix, not a cosmetic one.~~ **CORRECTED 2026-08-11 — it *is*
   the cosmetic one.** `0x0009` is schema-**known** (`GAME_CMSG_0009`); the silent-ignore
   path is D9(**a**) and leaves the buffer alone. D9(b) applies to schema-*unknown*
   opcodes only and is now fixed.

   All three legs now exist (`authsrv.py`: `ping_tick`, `handle_perf_report`,
   `report_ping`; `test_ping.py`, 27 checks). The cadence and the cutoff are ArenaNet's
   measured numbers rather than ours — 5.000 s, and the client's own `0x1388` — and three
   refusals are built in because each is a way to put a *plausible wrong number* on the
   net graph: a second request never moves the outstanding start time, an unprompted
   reply is dropped rather than answered with an invented elapsed, and a round trip over
   5000 ms is **not sent at all**, because the client discards it at `0x0048DA40` and a
   still graph would read as a dead feature rather than a bad value.

### Tier 2 — buildable, unlocks visible content

6. **`0x0056` + `0x0057` per NPC *type*, then `0x0020` referencing it.** We already
   send `0x0056`/`0x0057`, but the record layout is now exact: **the record has a hole
   at +0x18**, so wire field 8 must be placed **last, not seventh** — a server packing
   seven fields contiguously lands it one slot early. And the create's model field is
   a **tagged** id whose low 28 bits must be a definition this connection declared
   (342/342 on ArenaNet's own traffic).

7. **`0x013F` x9 at login.** *Nine of these is the entire reason the client has an
   inventory to draw.* We send none, so the bag UI is empty by construction and **no
   item message can land anywhere**. The nine (type, slot, capacity) triples are
   byte-identical across all four tapes, so this is a fixed table we can ship. Field 3
   is overridden by the client for three of the five types, so it must not be
   free-form.

8. **`0x015E` per worn item, then `0x006E` naming the slot ids.** Visible equipment on
   NPCs — D11's largest byte gap. The precondition the old weapon-type reading hid:
   **every id in `0x006E` must have been declared by a prior `0x015E`/`0x0161`**
   (621/621 on the wire, 1.1% by chance). Then `0x0048` after every `0x006E`
   (130/130), with 0 for synthetic agents so the client skips a guild lookup on an id
   we never populate.

9. **`0x0059` per player, then `0x00B0` + `0x00B1`.** Other characters appear with
   their real name, sex, appearance and profession pair instead of a default model;
   `0x00B0`/`0x00B1` key off the same playerId. Note **field 6 is dead** (uninitialised
   fill on ArenaNet's side, never read) — send anything. Caveat: `0x00B0`'s byte is a
   **declared** size the client cannot verify (see §4), so treat it as "at least the
   membership" rather than a count.

10. **`0x00A6` per agent** for correct profession icons in the roster, attribute panel
    and nameplate. Primary must never equal secondary and must never be 0.

11. **`0x0161` to hand a player a fully-formed item** — name, `code[]` modifiers, and
    the backpack itself. **Ordering hazard:** a later `0x015E` on the same item id
    strips the detail status back off.

### Tier 3 — needs a run before it is worth sending

12. **`0x0115`** — gadget state is 0 in 44/44 samples, so no bit has a meaning. Needs a
    capture where a gadget actually changes state (open a chest, trigger a door).
13. **`0x009F` property enum** — the binary carries jump tables and no strings. Only a
    probe names the ids. The one cheap exception: `0x009F[66, agent, 0]` immediately
    before a create is what ArenaNet does 153/153 and costs nothing to replicate.
14. **`0x003C`** — shape is exact, but nothing behavioural can be claimed until bits
    0/1/2 are named. The named next step is UiGame's summary code at 0x004a8c66.
15. **`0x0121`, `0x001A`** — sending an account or guild list whose contents we cannot
    read would be inventing data.

### One-line fixes, do these first because they are free

- `authsrv.py:145-147` — stale comment saying `0x006D` carries **weapon types**;
  the call site 2,900 lines below says the opposite and is right.
- `evidence.py:134` — hardcoded tape labels are wrong (two outposts, two explorables).
- `authsrv.py:681` — the `planes` gloss on `0x0029`'s fields 3/4 is not from the
  binary.
- `authsrv.py:683` — `SpeedModifier -> agent, modifier, type` is wrong on both nouns.

---


---

# 5. What got killed, and what it cost

**Upstream / incumbent readings refuted outright (5):**

| killed | by what | cost |
|---|---|---|
| `GameMsg.h:546-551` **rotation_cos / rotation_sin** for `0x002E` | sin²+cos² ranges 1.23–4.87 and is never 1; field 3 reaches 2.0944 and is never negative; field 2 is ±inf 9 times | This kept `0x002E` unsent. `studies/movement`'s own open question is now closed. |
| `authsrv.py:683` **SpeedModifier / "modifier, type"** for `0x002B` | `AGENT_MAX_MOVE_SPEED = 1.0` caps the field, so no buff can ride it; the byte is `facing` in the assert directly below | A 33% run enchantment could never have been expressed through this field. |
| **"EFFECTS"** as the noun for `0x00F0`/`0x00F1` | the client's word is `m_status`, constants `CHAR_STATUS_*`, in two unrelated files; the effect subsystem is never reached | Traceable to OpenTyria's struct having a `uint32 effects` — one witness, and not the client. |
| gw-preservation **INSTANCE_LOADED** for `0x00F1` | the handler takes an agent id and indexes a per-agent array | Would have made us send an agent-scoped write as a session event. |
| GWCA **weapon_type** enum for `0x006D` | 291/291 non-zero values were declared item ids earlier in the same tape | **Already killed 2026-08-06** by crashing a real client on `ItCliApi:400`. Only a stale comment survives. |

**Our own findings corrected (4):**

- **D2's "129 unexplained `0x00F0` arguments".** D2 looked backwards. Looking forwards
  with the clock stamp removed: **472/472, zero remaining.** The "≈0.93 ratio stable
  across connections" is not a ratio — it is an exact identity conditioned on the
  create's field[4]. *Cost: a documented "not invented past" gap that did not exist.*
- **T5's "unconditional 5 s heartbeat"** (already retracted) now has its mechanism:
  the client's `0x0009` is a **reply**, 79/79 prompted, 0/79 unprompted. This also
  resolves `studies/cmsg` §3's standing UNVERIFIED.
- **`studies/agentprops`' "two dispatch paths" for `0x009F`** — the repo's own map
  already records **seven**, and the re-read reproduced that document's off-by-one
  (55 vs the correct 56), which is itself evidence the read was not independent of it.
- **`evidence.py`'s tape labels.** Two outposts, two explorables — and that split is
  the largest phase signal in the corpus.

**Proposed names rejected (2):**

- **`0x006D` -> `GAME_SMSG_AGENT_UPDATE_HELD_ITEMS`.** Rejected four ways: it refutes a
  straw man (settled 2026-08-06 by crashing a client on the same assert it cites); the
  new name is **strictly weaker** than the tested incumbent, which already carries
  leadhand/offhand; its justifying observation is false (the nine-slot message *does*
  write slot 0, twice, with a type `0x006D` also carries); and `ItCliApi:485 "slot <
  ITEM_EQUIP_SLOTS"` is never reached. *Cost: a comment fix presented as a rename.*
- **`0x00B0` -> `PARTY_SET_SIZE` at NAMED.** The observation carrying it —
  "the corpus's final group sizes are exactly 1, 2 and 3" — is **false**. Membership was
  reconstructed four ways and **no group ever holds three members**; the byte carries 3
  eight times. All 23 misses run one way (announced above actual) and **include every
  sample of the value 3**. The honest residual is "a declared size the client cannot
  verify" — and the client can't police it either, since both readers only ask `> 1`.

**Evidence struck for failing the reach test (7 citations across 6 opcodes).** Every one
is an assert that exists, at the quoted line, in a plausible file — and does not reach
the handler:

| opcode | struck | why |
|---|---|---|
| `0x00A6` | `GmDeckBuilder:2321`, `AcctTemplate:411/412` | hero-deck UI and account template data; **not one assert in AvApi.cpp or AvChar.cpp mentions profession in any spelling** |
| `0x013F` | `ItCliApi:1425/1426` | in a function the handler never calls |
| `0x006D` | `ItCliApi:485` | different function |
| `0x0020` | `AgAgent:312` | the **teardown** routine, not the create path |
| `0x001E` | `AgAgent:2211` | same source file, not in the call graph |
| `0x0026` | `AgAgent:717` | vocabulary for the member, not evidence about the message |

*Cost: these were 4 of `0x00A6`'s 4 SOURCED bullets, 2 of `0x013F`'s 6, and the entire
"three independent witnesses agree" claim.*

**Checks that could not fail, struck (3):**

- **`0x0056`: "the element closes to the exact byte, 0x20 + 0x10 = 0x30."** The name is a
  **heap pointer**, not sixteen inline bytes. The stride is real; the arithmetic that
  "closed" it was built on a layout that is not there.
- **`0x0057`: "the key space does not overlap the agent id space."** Only 1 of 36 keys
  even falls inside that span — the absence of a collision is one coin flip.
- **`0x0025`: the angle-table negative result.** 140 of 172 samples are facing=1, whose
  rotation is the identity. It neither supports nor undermines the table.

**One fabricated quote.** `0x0161`'s log line was quoted as `"FileId=0, item name=%s.
type=%d"` and the `%s` was doing the argumentative work. The image reads **`%d`**. The
conclusion partly survives on other grounds — but by this repo's own standard a
paraphrased assert is a fabricated assert, and it was one of five SOURCED items.

**One disclaimer that was false in the author's own favour.** `0x002E`: "No assert names
the two payloads, so the argument is arithmetic." Two asserts name them —
`targetAngle` and `rotationRate` — in the function that calls the identical setter with
the identical argument order. The correction *promoted* the result from INFERRED to
SOURCED. *Recorded because a self-deprecating error is still an error, and it hid the
strongest evidence in that entry.*

**Statistics that were the wrong quantity (4):** `0x001E`'s ratio used the favourable
denominator and its per-pair figure is 21% capture segmentation; `0x009B`'s
"25 agents" was 25 **messages** on 12 agents and "18 unique strings" was 33;
`0x00B1`'s "161/161" is 143 self-links plus n=18 discriminating; `0x0048`'s
"45 of 58 player-controlled, both values on non-player agents" — there are **zero**
non-player samples.

**One tool bug that produced a confident wrong answer.** `msghandler`/`msgshape` drop
zero-count descriptors — 85 of them, 37 RECEIVE — so both reported "0x000C/0x000D have
no receive handler." *Cost: five opcodes filed as catalog orphans that are not, and two
entire dispatch tables invisible.*

---


---

# 6. Open questions this pass produced

1. **A second live capture on a different character.** Every count here is four tapes of
   one session, one character, one account. This separates protocol from character in a
   single decode and is the cheapest open test in the pass.
2. **`0x009F`'s property enum -- the batch's own headline question, and it produced
   nothing.** The client carries jump tables and no strings, so only *which* ids are
   real is recoverable statically. Naming them needs a probe.
3. **`0x0115` gadget state is 0 in 44/44 samples**, so no bit has a meaning yet. Needs a
   capture where a gadget actually changes state -- open a chest, trigger a door.
4. **`0x003C`'s bits 0/1/2.** Shape is exact; nothing behavioural can be claimed until
   they are named. The named next step is UiGame's summary code at `0x004a8c66`.
5. **The 116 corpus opcodes this pass did not touch**, and the 341 that never appeared
   in the capture at all.

---

# 7. CORRECTION, 2026-08-11 — section 4 was not verified and is partly wrong

Section 4 ("What this changes for the server") was written by the synthesis agent
and, unlike every claim about ArenaNet's binary and wire, **it never went through the
refutation pass**. Those claims are about OUR repo, and they were checked against the
code on 2026-08-11. Two of its headline items are wrong:

| section 4 said | the code says |
|---|---|
| "`0x001E` … We send it on a fixed 0.05 s sleep (CV ~ 0)" and "we have never sent it correctly" | **We already send a measured delta**: `delta_ms = int((now - prev_tick) * 1000)` (`authsrv.py`, the world-tick daemon). The *cadence* is a fixed 20 Hz, so our deltas cluster near 50 ms where ArenaNet's spread to 520 ms — a real but much smaller difference than claimed. |
| "`0x013F` x9 at login. *We send none, so the bag UI is empty by construction*" | `GAME_SMSG_INVENTORY_CREATE_BAG` **exists and has a send site.** Whether it sends all nine is a separate question the claim did not ask. |

**The verified gap is five opcodes**, reconciled by walking every named opcode against
the server's own constants and send sites:

| opcode | name | state in our server |
|---|---|---|
| `0x0026` | AGENT_UPDATE_FLAGS | constant defined (`..._AGENT_UNNAMED_0026`), **never sent** |
| `0x002B` | AGENT_UPDATE_SPEED | **not even defined** |
| `0x002E` | AGENT_UPDATE_ROTATION | **not even defined** |
| `0x0048` | AGENT_SET_TABARD_VISIBLE | **not even defined** |
| `0x00A6` | AGENT_SET_PROFESSION | **not even defined** |

And **five server constants carry names this pass refuted**, which is worse than no
name because they read as settled: `GAME_SMSG_AGENT_INITIAL_EFFECTS` and
`GAME_SMSG_AGENT_UPDATE_EFFECTS` (the client's word is `m_status`, not effects),
`GAME_SMSG_NPC_UPDATE_MODEL` (`0x0057` is MONSTER_COMPOSITE), `GAME_SMSG_PLAYER_CREATE`
(`0x0059` is PLAYER_INFO), and `GAME_SMSG_AGENT_UNNAMED_0026`.

**The lesson, and it generalises past this document.** The naming pass was structurally
sound where it had two independent witnesses that were adversarially checked — the
client's binary and the wire. It had neither for claims about this repository, and
nobody was assigned to refute that half. A fan-out that verifies its findings about the
*subject* and not about *itself* will produce exactly this: a reliable body of work with
an unreliable "so what" section bolted to the end. Any future pass that ends in a
recommendations section needs that section refuted too.
