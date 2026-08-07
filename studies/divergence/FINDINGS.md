# R1.5 — Divergence analysis: where our server differs from ArenaNet's

Study arc: `studies/divergence/`. Written 2026-08-07 against the first live capture.
Vocabulary per `studies/character/FINDINGS.md`: OBSERVED, UPSTREAM, RECONSTRUCTION,
CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

---

## 1. What was measured

### 1.1 The two corpora

| | live (ArenaNet) | ours (Rurik) |
|---|---|---|
| source | `vault/captures/live/20260807T143055` | 415 `ours`-classified files under `vault/captures/` |
| s2c messages | 11,263 | 271,449 |
| s2c bytes | 191,675 | 1,972,664 |
| distinct s2c opcodes | 163 (153 GAME_SMSG + 10 AUTH_SMSG) | 61 (53 GAME_SMSG + 8 AUTH_SMSG) |
| c2s messages | 437 (419 game + 18 auth) | 11,502 game c2s |
| connections | 1 auth + 5 game | many, over months |
| build | 38797 | 38797 |

`toolkit/origin.py` classified every file; `origin.require_single()` was called on each
pool separately and accepted each. The two were never pooled. (OBSERVED.)

Both corpora frame to the exact final byte. Live: 191,675 of 191,675 s2c bytes and
8,478 of 8,478 c2s bytes consumed, zero `Undecodable`, zero `NeedMoreData`, zero
remainder, on six of six streams. Ours: 271,449 of 271,449 `sent` records decoded with
the independently-logged `opcode` field agreeing every time. Mask is confirmed rather
than assumed — 0 of 11,263 s2c headers carry bit 15, all 437 c2s headers satisfy
`raw == opcode | 0x8000` exactly, and mask=0 stops the c2s framer at offset 0 on all six
streams. (OBSERVED.)

The live 100% figure is not vacuous. Three controls ran and each broke as it should:
shifting each stream by one byte yields 0 messages stopping at offset 0 on all six;
decoding the largest game stream against the AUTH_SMSG table yields 0 messages; and
for the 123 fixed-layout opcodes the observed size equals the schema's declared size for
every message in every stream, 0 disagreements. (OBSERVED.)

### 1.2 What the live session actually was

Re-measured for this document from `wire.jsonl` and the decrypted channel files.
The wire clock spans **t = 3.20 s to 414.77 s** (411.6 s, 6.9 minutes); in-world time is
t = 17.22 s to 414.57 s (397 s). Five game connections are five instance loads:

| conn | t (s) | map | name (`content/maps.toml`) | s2c msgs | s2c bytes |
|---|---|---|---|---|---|
| :63158 | 7.62–16.72 | — | character select (no agents, no ticks) | 297 | 5,788 |
| :60935 | 17.22–65.78 | 148 | Ascalon City (Pre-Searing) | 3,981 | 74,319 |
| :62994 | 66.11–213.69 | 146 | Lakeside County | 2,633 | 41,997 |
| :64102 | 214.01–228.05 | 164 | Ashford Abbey | 726 | 14,896 |
| :64103 | 228.41–414.57 | 146 | Lakeside County | 3,604 | 53,544 |

Map ids come from `GAME_SMSG 0x0199` field 2 and the client's own game version frame,
which agree on all four. All four instances are Pre-Searing. (OBSERVED.)

**A character was created during this session.** The chain is measured end to end: the
auth channel offered exactly four `AUTH_SMSG 0x0007` roster rows with name lengths
7 / 8 / 9 / 7, and none of them equals, prefixes or contains the 11-character name the
client later played; the character-select connection's version frame carries roster row
0's uuid; `GAME_CMSG 0x808b` carries an 11-character string; `GAME_SMSG 0x0188` at s2c
offset 5,680 of that connection carries a 16-byte value that is then the `char_uuid` in
all four subsequent in-world version frames; and the second `AUTH_SMSG 0x0011`
ACCOUNT_INFO carries that new uuid where the first carried roster row 0's. (OBSERVED for
the uuid chain; RECONSTRUCTION that `0x0188` *is* the creation reply.)

### 1.3 The honest limit of this evidence

This is n=1: one account, one operator, one build (38797), one 6.9-minute session, one
newly created character, four instances all inside the Pre-Searing region, no party, no
henchmen, no death, no trade, no guild, no PvP, no zone into a post-Searing map, and no
combat beyond nine `0x8026` attack orders at two agents. What generalises from it is
**message shapes and structural pairings** — a 130-of-130 bidirectional adjacency, a
68-long bracketed run reproduced on two independent connections, a field whose observed
magnitude is constant to 0.39% across 24,000 units of map — because those are properties
of the protocol that would have had to be manufactured to appear. What does **not**
generalise is every frequency in this document: `0x803d` is 38.4% of game c2s because the
operator walked, and the tick rate is 40 Hz on one map and 7 Hz on another because of what
was happening in each. Do not turn a percentage here into a protocol constant. And the
diff has a direction: our corpus is a recording of our own hardcoded `send()` calls, so an
opcode's absence from it is evidence about Rurik and never about ArenaNet — only
**live-present + ours-absent** is informative, and that is the direction reported below.

### 1.4 Method note for the numbers that are new here

The histogram and gap counts come from the R1.5 inventory pass (four independent decodes:
live s2c, live c2s, ours s2c, and a static enumeration of the server's send sites). The
timing, map, identity, tick-semantics, preamble and character-creation results in this
document were measured fresh for it: `wire.jsonl` s2c segments were deduplicated by TCP
sequence and concatenated in sequence order, the plaintext prefix computed as
`len(wire) − len(plaintext)` (22 bytes on every s2c stream, 82 on the auth c2s stream,
130 on each game c2s stream), and every message stamped with the timestamp of the segment
containing its last byte. All of it is read-only.

---

## 2. The divergences, ranked

The gap in aggregate: **105 opcodes ArenaNet sent that our server has never sent** (103
GAME_SMSG + 2 AUTH_SMSG — that is 105 *(channel, opcode) pairs* and **104 distinct opcode
values**, because `0x26` is the one value ArenaNet sends on both channels; both counts are
correct and a reader re-deriving this will hit the discrepancy, so it is stated here),
carrying **3,529 of 11,263 live s2c messages (31.3%)** and
**53,662 of 190,544 GAME_SMSG bytes (28.2%)**. In the reverse direction only three
opcodes go the other way — `0x0141`, `0x002F`, `0x003A` — and two of those three cannot
be produced by any code in the current tree at all (they are artefacts of an older
server). Scope exclusions are accounted at the end of this section rather than padded
into the list.

---

### D1 — `0x0021` agent removal: we create agents and can never destroy one

**Label:** OBSERVED (counts, the id test, the client's own handler). RECONSTRUCTION only
for the human-readable name.

6-byte message, `[dword]`. ArenaNet sent it **416 times** across all four in-world
connections (160 / 87 / 6 / 163). Our server has sent it **0 times in 271,449 recorded
s2c messages**, declares no constant for it, and has no send site.

**Evidence.** The dword is a previously-created agent id in **416 of 416** cases when
keyed on `0x0020 WORLD_CREATE_AGENT` field 0, and in **3 of 416** when keyed on field 1 —
a split no framing accident produces. Forcing the message to other sizes breaks the
stream: at 2 bytes only 54,411 of 190,544 bytes frame, at 10 bytes 63,911, at the
catalogued 6 bytes all 190,544. Four further checks: 0 double-removals without an
intervening create, 0 removals of a never-created id, 301 of 301 id re-creations preceded
by a removal of that id, and 0 of 416 sitting directly after that id's create (which
rules out "creation ack"). A coincidence attack fails: field-0 occupancy over its own
value span is 9.4–41.0%, so a uniform draw would hit 9–41%, not 100%. Decisively, the
client's own binary agrees — `msgshape` reads the RECV table at 0x00a52d70 as
`0x0021 → handler 0x005FD2F0, 1 field u32, wire 6 bytes`, `asserts.py --at 0x005fd2f0`
names `Array:587 "index < m_count"` and `AgMsg:316 "ptr"` (the dword is bounds-checked as
an index into an agent array), and the handler walks every object bound to the agent,
clears `m_bindTarget`, frees the array and zeroes count/capacity/base. That is teardown,
read out of the exact binary that produced this capture.

**Impact on a real client.** A Rurik map with spawning, dying or wandering NPCs leaks
agents in the client's agent table for the life of the session. ArenaNet reuses agent ids
(68 distinct ids across 205 creates on one connection), which is only safe because ids get
released; we must not imitate the reuse until we can retire an id.

**One correction to carry.** "It cannot construct it at all" is too strong:
`schema/messages.json` does carry `GAME_SMSG 0x0021` as `[msg_header, dword]`, so
`Codec().encode()` would produce it today. What is missing is the constant, the send site
and an agent-lifetime owner.

---

### D2 — `0x00F0` per-agent initial effects: the single most frequent thing we never send

**Label:** OBSERVED (counts, id membership, adjacency). UPSTREAM/RECONSTRUCTION for the
name `AGENT_INITIAL_EFFECTS`, which is this repo's own label harvested from `studies/*.md`.

10 bytes, `[agent_id, dword]`. **472 messages, 4,720 bytes — the highest count in the
entire gap.** Present on all four in-world connections (191 / 80 / 22 / 179), absent from
the character-select connection, which has no agents. We send the neighbouring `0x00F1`
18 times and `0x00F0` never.

**Evidence.** It is bound to the spawn unit rather than free-floating: 343 of 472
arguments are an agent id created earlier in the same stream by `0x0020` or `0x0059`.
Stream position is consistent — preceded by `0x009F` / `0x003C` / `0x009B` and followed by
a tick or the next `0x0020` (285 and 187 times). Ratio to creates is stable across
connections at ≈0.93 (191/205, 80/109, 22/25, 179/188). The 129 arguments not traced to a
create inside the captured window are **unexplained and not invented past** — they may
come from a create before the window or from a fourth create path.

**Impact.** Every agent ArenaNet spawns is given a starting effect state; every agent we
spawn is left undefined.

---

### D3 — Two streams where we send the brackets and never the body

**Label:** OBSERVED (all counts and the run structure).

Two instances of the same defect, which is why they are one entry.

1. **The instance manifest.** ArenaNet alternates `0x0198 PHASE` with a `0x0196` body —
   15 messages, 3,829 bytes, averaging 255 B — and closes with `0x0197 DONE`. Our server
   has sent `0x0198` **442 times**, `0x0197` **216 times**, and `0x0196` **zero times**;
   `authsrv.py` declares constants for PHASE and DONE at lines 170–171 and none for the body.
2. **The unlock/item stream.** ArenaNet opens with `0x0018`, sends `0x001A` rows, closes
   with `0x001B`. We have sent `0x0018` 209 times, `0x001B` 209 times, and `0x001A`
   **zero times**.

**Evidence.** The `0x001A` run structure is exact and refutable: on both connections that
carry it there is exactly one run of exactly **68 consecutive** `0x001A` messages,
immediately preceded by `0x0018` and immediately followed by `0x001B` (index 66 on port
60935, index 65 on port 63158). Two independent connections producing the identical
bracketed run length is a structural signal, not a coincidence. Together the two bodies
are 6,541 bytes, 12.2% of all gap bytes, across 151 messages.

**Impact.** This is ranked above larger byte gaps because the failure mode is worse than a
missing opcode: our streams are structurally well-formed and semantically empty, so
nothing in our stack reports a problem. Any test asserting "the manifest was sent" passes
today and will keep passing.

---

### D4 — `0x000C` / `0x000D`: the server-driven ping loop, and the pong we silently drop

**Label:** OBSERVED (counts, cadence, the three-way pairing). RECONSTRUCTION that
`0x000D` carries a round-trip time in ms.

`0x000C` is header-only (2 bytes); `0x000D` is `[dword]`. ArenaNet sent **81 of each**.
Our server sends neither, and does not handle the reply either: `authsrv.py` has exactly
nine GAME_CMSG handlers and none is opcode 9, so all 81 client pongs land on the
silent-ignore path.

**Evidence.** c2s `0x8009` = s2c `0x000C` = s2c `0x000D` on **every connection
separately** (10/10/10, 29/29/29, 2/2/2, 3/3/3, 37/37/37). A three-way per-connection
identity is not something a decoder can force. `0x8009` cadence is 5.000 s (75 of 76 gaps
within 100 ms of 5.000 s, p50 5.0047 s); median lag from `0x000C` to the reply is 9.3 ms;
`0x000D`'s dword is min 35, p50 50, max 456 — the profile of a millisecond RTT to an AWS
east host, not a counter.

**Impact.** This is the connection-liveness mechanism and, on the RECONSTRUCTION reading,
the source of the latency number the client displays. Our server has no liveness probe in
either direction on the game channel, so a half-open connection is invisible to it. It
also means **19.3% of live game c2s traffic** is a message class our stack has never
decoded, purely because it never asks the question.

---

### D5 — `0x0048`: ArenaNet never sends visual equipment without it, 130 times out of 130

**Label:** OBSERVED (the pairing is exact in both directions).

5 bytes, `[agent_id, byte]`, second field 0 or 1. **130 messages.** We send
`0x006E UPDATE_AGENT_VISUAL_EQUIPMENT` 18 times and `0x0048` never.

**Evidence.** Every one of the 130 `0x0048` messages is immediately preceded by a
`0x006E`, **and** every one of the 130 `0x006E` messages is immediately followed by a
`0x0048` — 130/130 in both directions, across four connections, zero exceptions. A
one-sided pairing would be weak; a bidirectional one at n=130 is close to a protocol rule.

**Impact.** Small in volume, highest in confidence, cheapest to close. On this evidence
our 18 existing `0x006E` sends are incomplete in the sense that matters: the live client
has never seen equipment without the follow-up.

---

### D6 — The simulation tick: our payload is right and our cadence is wrong

**Label:** OBSERVED (correlation, cadence). This entry is new to this document.

`GAME_SMSG 0x001E` is 6 bytes, `[dword]`. `authsrv.py:1499` computes
`delta_ms = int((now - prev_tick) * 1000)` and sends it at a fixed 20 Hz
(`TICK_SECONDS = 0.05`). It is 94.8% of all GAME_SMSG traffic our server has ever emitted.

**Evidence for the payload (a confirmation, not a divergence).** Correlating each live
tick's dword against the measured inter-tick wire gap gives Pearson **r = 0.985** on map
148 (n=1,176) and **r = 0.999** on map 146 (n=1,066); median wire gap 25.0 ms against
median dword 22.0, and 136.3 ms against 129.0. The dword is milliseconds since the
previous tick. This is the first confirmation of that reconstruction against ArenaNet.

**Evidence for the divergence.** The live cadence is not fixed and not 20 Hz:

| map | instance | ticks | median inter-tick | p10 / p90 |
|---|---|---|---|---|
| 148 Ascalon City | ~40 players | 1,252 | 25.0 ms (40.0 Hz) | 18.4 / 79.4 ms |
| 164 Ashford Abbey | 19 players | 111 | 77.0 ms (13.0 Hz) | 20.2 / 277.5 ms |
| 146 Lakeside County | solo | 1,097 | 144.3 ms (6.9 Hz) | 31.7 / 490.5 ms |
| 146 Lakeside County | solo | 1,511 | 136.3 ms (7.3 Hz) | 24.6 / 416.7 ms |

**Impact.** Our fixed 20 Hz is roughly half rate in a crowded outpost and roughly three
times rate in a solo instance. What decides the live rate is UNVERIFIED — player count
correlates, but so does "how much else the server had to say", and n=4 instances cannot
separate them.

---

### D7 — Player number and agent id are two id spaces; our server conflates them

**Label:** OBSERVED. New to this document.

`authsrv.py:1456` sends `GAME_SMSG 0x0199 INSTANCE_LOAD_INFO` with field 1 commented
"agent_id — the player's own agent, 1 for the first", and `PLAYER_AGENT_ID = 1` is used
for `0x0022 WORLD_UPDATE_CONTROLLED_AGENT` as well. `schema/messages.json` types that
field as `agent_id`. Live says they are different numbers.

**Evidence.** On each in-world connection, `0x0199` field 1 selects exactly one
`0x0059 PLAYER_CREATE` row (4 of 4), and that row's own `agent_id` field is a different
value — which is then exactly what `0x0022` names, and is a member of the `0x0020` create
set (4 of 4; 3 of 3 on the busiest connection):

| conn | map | `0x0199` f1 | my `PLAYER_CREATE` agent id | `0x0022` |
|---|---|---|---|---|
| :60935 | 148 | 26 | 725 | 725, 300, 725 |
| :62994 | 146 | 1 | 31 | 31 |
| :64102 | 164 | 22 | 23 | 23 |
| :64103 | 146 | 1 | 31 | 31 |

The player-number reading is corroborated by scale: the two solo explorable instances have
exactly one `PLAYER_CREATE` and field 1 = 1; the two outposts have 40 and 19 and field 1 =
26 and 22. Two further fields of `0x0199` resolve at the same time: field 3 equals
`content/maps.toml`'s `explorable` for all three map ids observed (146 → 1, 148 → 0,
164 → 0), and field 4 is 2 / 1 / 0 / 0 — nonzero only in outposts, consistent with a
district number (RECONSTRUCTION).

**Impact.** Our server works today only because it sends `1` for both, so the conflation
is invisible in a one-player instance and would break the moment there are two.
`0x0022`'s excursion 725 → 300 → 725 on the Ascalon City connection is a control transfer
we have no concept of at all.

---

### D8 — `0x002B`: a per-agent movement rate that precedes 98% of ArenaNet's move messages

**Label:** OBSERVED (counts, float range, adjacency). RECONSTRUCTION that the float is a
speed multiplier.

11 bytes, `[dword, float, byte]`. **163 messages** across all four in-world connections.
Our server sends `0x0029 AGENT_MOVE_TO_POINT` 3,088 times — more than three times
ArenaNet's 987 — and has never sent `0x002B`.

**Evidence.** The float is the tell: 15 distinct values spanning 0.278 to 1.0, including
1.0, 0.75, 0.4167, 0.3333, 0.3125 — a bounded multiplier set, not a coordinate, a duration
or a counter. Field 0 takes 50 distinct values in [15, 725], the agent-id range. 160 of
163 are immediately followed by `0x0029`. The reverse ratio is the important nuance and it
refutes the simpler story: only **160 of 987** `0x0029` messages are preceded by
`0x002B`, so this is sent when a rate *changes*, not with every move.

**Impact.** Our server drives movement heavily and has no per-agent speed concept, so
cripple, haste and snare have no wire representation. Implementing it on every move would
be wrong.

---

### D9 — What our server does with traffic it does not handle

**Label:** OBSERVED (code read plus corpus measurement).

Two behaviours, and conflating them is the trap.

**(a) A schema-known opcode with no handler is silently ignored.** `authsrv.py:1589-2458`
is one dispatch loop and **neither** chain has an `else`. The message is printed and
recorded, then falls off the end: nothing sent, nothing logged as a miss, socket healthy.
Measured against our own corpus, this is **19 distinct GAME_CMSG opcodes, 1,126 of 11,502
game-channel messages (9.8%)**. Against live traffic shapes it would be worse — `0x8009`
alone is 19.3% of live game c2s. `elif kind != "auth": pass` at 2369-2374 is unreachable
dead code.

**(b) A schema-unknown opcode discards the pending buffer.** The `Undecodable` path at
2460-2468 is loud in the log and silent to the client, keeps the connection open, sends no
error, and sets `pending = b""` — which measurably swallows already-decodable handled
messages that arrived in the same TCP read.

**Impact.** (b) is the one that will bite a tape-player run (§4): any live-shaped client
sends message classes we have never seen, and one of them landing outside the schema takes
out its neighbours too.

---

### D10 — Character creation is a flow we have no part of

**Label:** OBSERVED (the sequence and the uuid chain). RECONSTRUCTION for what each
opcode means.

The character-select connection (:63158, t = 7.62–16.72, 297 s2c messages, 39 opcodes,
5,788 bytes) is not a map: zero `0x001E`, zero `0x0020`, and it is the only stream that
ends its player block with `0x018A` instead of `0x018E`. What happens on it is a character
being made: `0x800a` machine info, `0x800b` `Gw/38797.0 (Win32)`, then five `0x8060`
cycles each followed by a seven-step `0x8084` enumeration (field 0 running the exact cycle
4,2,3,6,5,0,1 five times, field 1 always 6), then `0x808b` carrying an 11-character name,
then `0x8008`. The server replies with, among others, 47 `0x0161 CREATE_NAMED_ITEM` and a
68-long `0x001A` run, and issues the new character's uuid in `0x0188`.

Our server offers exactly one character (`AUTH_SMSG 0x0007` with `TEST_CHAR_UUID`) and has
no creation path at all: `0x0060`, `0x0084`, `0x008b` are not among its nine GAME_CMSG
handlers.

**Impact.** Low for the current loop, which uses a fixed test character; a blocker for any
future where the client is allowed to make one. Ranked here rather than higher because
nothing in the ladder currently needs it.

---

### D11 — `0x015E`: the largest byte gap and the least understood message in the list

**Label:** OBSERVED (counts, size, adjacency). UNVERIFIED (meaning — no name anywhere in
this repo and no field names in the schema).

25 bytes fixed, `[dword, dword, byte, byte, word, word, byte, dword, dword]`, and all 263
instances matched the declared size exactly. **6,575 bytes — 12.3% of all gap bytes**,
the single largest byte consumer. Confined to two connections (174 and 89), which are the
two carrying the heaviest `0x0059 PLAYER_CREATE` traffic (40 and 19).

**Evidence.** It arrives in runs bracketed by agent-appearance messages: preceded by
another `0x015E` 209 times and by `0x0020` 54 times; followed by another `0x015E` 209
times and by `0x006E` 54 times. The 54/54 bracketing is the usable signal. Field 1
clusters near 665–668 and fields 3–6 are near-constant (33, 11, 39), consistent with a
table row rather than an event.

**Impact.** Listed so it is not lost, and flagged as needing identification before any
implementation. Its absence from two of four in-world connections argues it is situational
rather than mandatory.

---

### Scope accounting (so the list is not padded)

- **"We can send it but no capture exercised it" is nearly empty.** All 47 GAME_SMSG and
  all 8 AUTH_SMSG the default path constructs already appear in our corpus, so on the
  default path this case does not exist. Adding `probes.py` yields exactly **4 opcodes,
  14 messages, 0.4% of the gap** (`0x0041` n=2, `0x00E4` n=4, `0x00E5` n=4, `0x00E6` n=4).
- **Login/account scaffolding a private server does not need:** 6 GAME_SMSG seen only on
  the character-select connection (`0x015B`, `0x014B`, `0x014D`, `0x0189`, `0x005B`,
  `0x0188`, 60 messages) plus both AUTH_SMSG gaps (`0x0017` empty blob n=1, `0x0026`
  values [2,1] n=1) — **62 messages, 1.8% of the gap**.
- **The reverse direction** is 3 opcodes: `0x0141 UPDATE_GOLD_STORAGE`,
  `0x002F AGENT_UPDATE_ALLEGIANCE`, `0x003A AGENT_UPDATE_ATTRIBUTES`. Two of the three
  (`0x002F`, `0x003A`) survive only in old capture files; no code in the current tree
  produces `0x002F`. Our corpus is a record of three different servers and any measurement
  that pools it is measuring a moving target.

---

### Not divergences: eight things the capture confirms we already get right

These matter as much as the gaps, because several close standing caveats.

1. **The ARC4 preamble and key derivation are ArenaNet's.** Every live s2c stream opens
   with the 22 unencrypted bytes `01 16` + a 20-byte server seed — i.e. the
   `struct.pack("<H", 0x1601)` + seed that `authsrv.py:1364` writes — on **6 of 6**
   connections. And all six streams decrypt to schema-framable plaintext under
   `master = server_seed XOR shared[:20]; key = arc4_hash(master)`, two independent
   keystreams per direction. `replay.py`'s own "WHAT IT DOES NOT PROVE — that ArenaNet's
   real AuthSrv sizes and derives its master_secret the way ours does" is **now closed by
   measurement**. (OBSERVED.)
2. **The version frames are the sizes we parse.** Auth c2s wire minus plaintext is exactly
   82 (4+12 version, 2+64 seed); each game c2s is exactly 130 (4+60 version, 2+64 seed) —
   matching `recv_exact(sock, 12)` and `recv_exact(sock, 60)`. The game frame's
   `account_uuid` / `char_uuid` echo is real: the character-select connection carries
   roster row 0's uuid, straight from `CHARACTER_INFO`. (OBSERVED, CORROBORATES the
   comment at `authsrv.py:1327`.)
3. **The auth request-id echo is real and we do it correctly.** 18 of 22 AUTH_SMSG
   messages carry, as their first payload field, a value the client chose (observed ids
   1, 2, 3, 5, 6, 8, 10, 13), ascending in the same order as the client's requests.
   (OBSERVED.)
4. **`GAME_SMSG 0x0030`'s unexplained literal is ArenaNet's too.** Live payload is
   `['', 0, 0, 1000, 0, 0, 0]` on **4 of 4** in-world connections — byte-identical to
   `authsrv.py:1671`. (OBSERVED.)
5. **`0x0199`'s explorable flag agrees with `content/maps.toml`** for all three map ids
   observed, which is a live check on a value derived from the client's AreaInfo table.
   (OBSERVED.)
6. **`0x001E`'s payload is milliseconds since the previous tick** (D6, r ≥ 0.985).
7. **`schema/overrides.json` beat OpenTyria on the wire.** `GAME_CMSG 144` = 19 bytes
   (blob(16) + byte), where OpenTyria said 18. Four instances appear live; at 18 bytes the
   c2s streams would not have closed. (OBSERVED.)
8. **The mask rule is confirmed from both ends**: s2c mask 0 (0 of 11,263 headers carry
   bit 15), c2s mask 0x8000 (437 of 437 satisfy `raw == opcode | 0x8000`).

---

## 3. Checked and refuted

Recorded so nobody re-derives them.

### R1 — "Our combat entry point is a message the real client never sends" — REFUTED

The arithmetic was right and the analysis failed on three load-bearing points.

Confirmed: live counts `0x00c1` n=29, `0x0039` n=15, `0x0026` n=9, `0x0033` n=0; ours
`0x0033` n=206 / 19 files, `0x00c1` n=83, `0x0039` n=22, GAME `0x0026` n=0; and the silent
drop is real. The decode is trustworthy on a check that could have refuted it: every
`0x0026`, `0x0039` and targeted `0x0046` in the live capture carries the agent id set by
the most recent `0x00c1` — 28 agree, 0 disagree.

Why it is not the claimed gap:

- **The "three-message combat unit" is refuted by the same capture.** `0x0039` is
  dialogue, not combat. All 7 runs of it (15 messages) are followed by `0x003b`, whose
  dwords are all dialog-shaped (0x804001, 0x85A001, 0x802E04, …), usually then `0x0012`.
  In a 3-message window `0x0039` is followed by `0x003b` 13 times and by `0x0046 USE_SKILL`
  **zero** times. `0x0026` is the mirror: followed by `0x0046` at the same agent 4 times,
  never in a `0x003b` chain. Two distinct chains, merged into one by the claim.
- **"A message the real client never sends" is false.** `0x0033` is in the client's own
  send table and the same build sends it 206 times in our corpus. Its absence live is
  explained: our `0x0033` targets are agents 10 and 7 — our synthetic hostile — and the
  live session never clicked another player. The defensible statement is only "`0x0033` is
  not the attack order", which `authsrv.py:803-807` already says.
- **The impact is backwards.** `0x0026` has never once reached our server, so the described
  failure cannot occur today and a handler would be dead code. The real defect is upstream
  and already logged at `authsrv.py:792-808`, `agents.py:305-330` and
  `studies/enemy/PLAN.md` §904 and §1595-1607 — including that the explorable flag, the
  hostile team token, `0x002F`, the weapon and the energy/health pools were all tried and
  the client still never sent `0x0026`, cause NOT FOUND.

### R2 — "The auth roster does not contain the character that was played" — resolved, not a finding

Measured and initially alarming: the four `AUTH_SMSG 0x0007` rows have name lengths
7 / 8 / 9 / 7, none equal to, prefixing or containing the 11-character name the game
server used in-world, and none of the four roster uuids appears in any game stream. The
tempting conclusions — that field 4 is not the name, or that the roster arrives on a
channel we did not decrypt — are both wrong. The character was **created during the
session** (§1.2), so a fifth character legitimately existed that the roster predates. The
lesson is the reason this is written down: the anomaly was real, the two obvious
explanations were both available, and the measurement that settled it was the uuid chain,
not either hypothesis.

### R3 — "`0x0040` is a high-impact silent drop" — REFUTED

*(Recovered from the review round's journal after the synthesis pass flagged it missing.
The flag was correct and is left in the history rather than tidied away.)*

Every number in the claim reproduced. `GAME_CMSG 0x0040`, UPSTREAM-named `ROTATE_PLAYER`,
is decoded and then ignored: **n=536 across 49 of 116 ours game-channel files** (4.66% of
11,511 ours game c2s), the largest single unhandled c2s opcode — next is `0x0092` at 168 —
and it does fall off the end of the `if kind == "game"` chain with no `else`. The decode
survived attack: all 116 files framed with zero errors and full byte consumption, so the
10-byte length is confirmed by 536 occurrences across 49 independent streams.

It is still not the claimed finding, on four counts:

- **Not invisible — already on the books, twice, with the identical count.**
  `studies/movement/FINDINGS.md:166` states there is no dispatch handler for `0x0040`, and
  `studies/review/FINDINGS.md:179` already lists "ROTATE_PLAYER (0x0040) x536" with a
  written recommendation. A re-discovery presented as a hidden defect.
- **Not a request, so no reply is being withheld.** In the heaviest session inter-arrival
  gaps run min 0.016 s / median 0.55 s / max 39.3 s with 94 of 112 distinct — no retry
  timer — and consecutive identical payloads are **0 of 112**. The client never re-sends.
  Fire-and-forget state notification, not an unanswered question.
- **The 536 is mostly our own harness.** Read as float32 (justified: field 2 lands on clean
  decimals — 1.0 in 411 of 536, 0.425 in 105), **field 1 is ±INFINITY in 385 of 536 =
  71.8%**, and 5 of the 49 files carry 49.6% of all occurrences. `drive_client.py:332-356`
  drives the client by clicking fixed fractional window coordinates, which is exactly the
  degenerate zero-length-direction case `studies/movement/FINDINGS.md:130-133` identifies.
  We were largely recording the client reacting to a script clicking its own feet.
- **The live capture actively refutes the extrapolation.** Live n=1 of 419 — a rate 19.5x
  lower, `P(X<=1) = 6.9e-08` under the ours rate. The live session does not merely fail to
  support the claim; it contradicts it.

**Defensible residue:** `0x0040` is decoded and ignored without a log line. That is worth
the `else` branch in D9(a) and nothing more. **The transferable lesson is that our own
corpus is not a sample of client behaviour** — it is a recording of what our harness
provoked, and any frequency taken from it and projected onto a real client will be wrong
in the direction of whatever the script happened to do.

---

## 4. What this says about R1.5, the tape player

The question: can we replay a recorded StoC stream at recorded timing and walk a real
client through Ascalon with what we now hold?

**Short answer: yes for one map, on the game channel only, with the auth channel still
synthesised by our own server — and there is exactly one unknown that decides whether it
works, which one experiment settles.**

### 4.1 What we hold

- **A complete, framed tape of Ascalon City (Pre-Searing).** Connection :60935, map 148:
  74,319 bytes of s2c plaintext, 3,981 messages, 48.6 s, framing to the exact final byte
  with zero undecodables. Lakeside County is a second tape (41,997 B / 2,633 msgs /
  147.6 s), and Ashford Abbey a third.
- **Timing.** 3,212 s2c TCP segments across the six connections, i.e. a real timestamp
  every ~3.5 messages. Map 148 alone has **1,210 timing points for 3,981 messages**,
  median inter-segment gap **24.4 ms**. The instance load is a burst: 800 of 3,981
  messages and 25,276 of 74,319 bytes (34.0%) arrive in the first **0.79 s**, and the
  first `0x001E` tick follows at t+0.79 s on every in-world connection (0.63–0.79 s).
- **The transport, proven.** The preamble, the version-frame sizes and the key derivation
  are all confirmed identical to ours (§2, items 1–2). ARC4 is symmetric, so
  re-encrypting the tape under a fresh session key is the code path `replay.py` already
  runs — and `replay.py`'s docstring already names R1.5 as its consumer.
- **No semantics required.** A tape replays bytes. The 105-opcode gap in §2 is irrelevant
  to it: we do not need to understand `0x015E` to send it. This is the whole reason R1.5
  is worth doing before the gap is closed.

### 4.2 What is missing, in order of how much it blocks

1. **The auth channel cannot be taped.** 18 of 22 AUTH_SMSG messages carry a
   client-chosen request id, and the client's counter increments are not constant (gaps at
   4, 7, 9, 11, 12 — requests issued elsewhere). A verbatim auth replay answers the wrong
   request numbers. **Mitigation: keep the auth channel synthesised.** Our server already
   echoes `req_id` correctly, so this costs nothing except that the handoff, the map id and
   both uuids in the game version frame come from *our* `0x0009 GAME_SERVER_INFO`, not the
   tape's.
2. **Identity mismatch, and it is the unknown that decides feasibility.** The tape's game
   stream names the recorded character: an 11-character name in `0x017D` and in the
   player's `0x0059` row, player number 26, agent id 725, plus 40 other players' names in
   the outpost. A client that logged in as our test character will be shown someone else's
   world. **Whether the client cross-checks the name or uuid it sent in its version frame
   against the tape's `0x017D` / `0x0059` is UNVERIFIED** — we have no measurement either
   way, and this repo has two precedents of the client asserting on a value it disagreed
   with (`Map.cpp(1762)` on a masked file id, `ItCliApi.cpp(400)` on a weapon type). This
   is the first thing a tape run settles, and it settles it in one launch.
3. **A tape is a movie, not a world.** 987 `0x0029 AGENT_MOVE_TO_POINT` and 201
   `0x0025 AGENT_MOVE_DIRECTION` in the tape are responses to the recorded operator's 161
   `0x803d` and their `0x8047` clicks. On replay the avatar walks the recorded path
   regardless of what the new operator does, and client-side prediction will fight it. A
   tape can demonstrate a load and a populated, animated world; it cannot demonstrate
   control. Anything R1.5 claims about control is out of scope by construction.
4. **c2s still arrives and we still mishandle it.** The client leads on every game
   connection (first c2s at t=16.97 s against first s2c at 17.20 s on :60935; the opening
   triple `0x8091 → 0x8088 → 0x8090` inside 0.6 s), so the tape can be gated on the
   client's `0x8090` rather than free-running — good. But if the tape includes the 81
   `0x000C` pings, the client will pong `0x8009` at 5 s intervals into our silent-ignore
   path, and per D9(b) any *schema-unknown* c2s opcode will discard whatever decodable
   messages shared its TCP read. Fix D9(b) before the run or accept a confusing failure.
5. **Session-embedded absolute time.** `0x0195 INSTANCE_LOAD_SPAWN_POINT` carries an
   8-byte Windows FILETIME from 2026-08-07 (e.g. `0x01DD269AED0B6C6B`). Replayed verbatim
   it is stale. Whether the client cares is UNVERIFIED.
6. **Timing granularity is per segment, not per message.** The median map-148 segment
   carries 1 message; the largest carries 88. A player that honours segment boundaries
   reproduces the observed cadence to ~25 ms; one that spaces messages evenly does not,
   and the 0.79-second load burst is exactly where evenly-spaced would look wrong.
7. **n=1, and no second tape of the same map.** Four other live captures exist
   (`vault/captures/live/20260807T124912`, `T133758`, `T135532`, `T141736`) and have not
   been analysed. Nothing in this document is n>1 at the session level.

### 4.3 Verdict

Feasible, cheap, and worth doing before any of the D1–D11 implementation work, because a
tape run is the only instrument that answers "does the client accept a world it did not
ask for" — and that answer determines whether the correct long-run strategy is
*reconstruct the stream* or *replay and diverge*. The failure mode is informative either
way: an assert names a field, and this repo has twice turned a client assert into a fact
faster than any amount of reading.

---

## 5. Next actions, ordered

1. **Tape-player spike — small (≈1 session).** Feed the :60935 s2c plaintext to a caged
   loopback client through the existing `authsrv` handshake, paced from `wire.jsonl`
   segment boundaries, auth channel synthesised as today. **State the prediction first,
   per the house rule:** the client reaches the Ascalon City load screen and draws agents;
   the failure prediction is an assert naming a player-identity field. **Change no
   identity field on the first run** — the point is to learn whether the client checks.
   Prerequisite: fix D9(b)'s buffer discard so a stray c2s opcode cannot masquerade as a
   tape failure.
2. **`0x0021` agent removal — small.** One send site plus an agent-lifetime owner in the
   world state. Already verified against the client's own teardown handler. Highest-value
   protocol gap and the one that unblocks safe agent-id reuse.
3. **`0x0048` after every `0x006E` — small.** 130/130 in both directions; our 18 existing
   `0x006E` sends are incomplete on that evidence. One line at the existing send site.
4. **The `0x000C`/`0x000D` ping loop — small.** A 5 s timer, one 2-byte send, one
   `0x000D` with the measured RTT, and a handler for `GAME_CMSG 0x8009` that does nothing
   but does it *loudly*. Also give the game dispatch chain an `else` (D9(a)) so
   unhandled-but-known stops being invisible.
5. **Split the player-number and agent-id spaces — small.** Fix the comment and the value
   at `authsrv.py:1456`, stop reusing `PLAYER_AGENT_ID` for both, and correct the schema's
   `agent_id` typing of `GAME_SMSG 0x0199` field 1 via `schema/overrides.json` with this
   capture cited as the evidence.
6. **`0x00F0` at spawn — medium.** Needs a per-agent effect model even if v1 always sends
   0. Ratio to creates is ≈0.93, so it is per-agent, not per-instance.
7. **Tick cadence — medium, decision first.** The payload is confirmed; the rate is not.
   Decide whether to keep 20 Hz or make it adaptive, and record *why* — the live data
   (40.0 Hz busy outpost, 6.9–7.3 Hz solo explorable) shows the rate depends on context we
   have not isolated, and n=4 instances cannot separate player count from message volume.
8. **Analyse the four unanalysed live captures — medium.** Specifically to take
   `0x0048`/`0x006E` (130/130) and the 68-long `0x001A` run to n>1, and to see whether the
   tick cadence tracks player count. Pure decode work, no new capture needed.
9. **The empty brackets, `0x0196` and `0x001A` — large.** Content problems, not wire
   problems: the bodies need real map and unlock data. Until then, add a check that fails
   when a manifest is sent with no body, so the current silence stops passing tests.
10. **`0x015E` — study, not patch.** 263 messages, 6,575 bytes, no name anywhere in the
    repo. Identify it with `msgshape`/`asserts.py` against
    `vault/run-live/2026-07-29_221c13772c7a/Gw.exe` before writing any code.
11. **Plan capture #2 around what this session does not contain — medium.** No party, no
    henchmen, no death, no trade, no guild, no post-Searing map, and nine attack orders
    total. Every frequency in this document is provisional until a second session with a
    different shape exists. Same behavioural rule as R0b: human cadence, human hours, one
    client, secondary account.
