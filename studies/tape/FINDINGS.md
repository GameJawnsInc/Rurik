# Tape runs — what a recording of ArenaNet's server does to our client

R1.5's instrument is `toolkit/authsrv/tape.py` (loader) plus `play_tape` in
`authsrv.py` (player). What a tape *is*, and the three things it is not, are in
`tape.py`'s docstring; the feasibility argument that preceded the first run is
[../divergence/FINDINGS.md](../divergence/FINDINGS.md) §4. **This file is the log of
what actual runs observed**, because the tape is now a standing instrument rather than
a one-off experiment and its results will accumulate.

Claim labels are the vocabulary in
[../character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM,
RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

---

## 1. The runs

Both from `vault/captures/live/20260807T143055`, the 2026-08-07 secondary-account
session. Both played into a caged loopback client with the auth channel synthesised by
our own server and the game channel replaced entirely by the recording.

| # | date | connection | map | events | outcome |
|---|---|---|---|---|---|
| 1 | 2026-08-10 | `:60935` | 148 Ascalon City | 1,209 / 1,209 | clean. Ended at the map transition: the client dialled `54.198.7.73:6112` from the recorded `GAME_SERVER_INFO` and the cage refused it (`Code=005`). |
| 2 | 2026-08-10 | `:64103` | 146 Lakeside County | 1,074 / 1,074 | clean, ran to completion, **combat rendered**. Operator kept the client after the tape ended and probed it. |

Run 1's findings — the client does not validate identity, and the earlier
`AgAgent.cpp(978)` assert was our own world tick talking over the recording — are in
`PLAN.md` §3.4. Everything below is run 2.

### 1.1 Which tape, and why it was nearly the wrong one

The capture holds four game connections. Naming them needs the `map_id` in each
connection's own c2s `VERSION` body (`<5I>` at offset 4: build, unk1, world_id, map_id,
player_id), resolved through the client's `AreaInfo` table:

| connection | map | first seen | events | combat |
|---|---|---|---|---|
| `:63158` | 0 (character select) | 7.5 s | 14 | — |
| `:60935` | **148** Ascalon City | 17.0 s | 1,209 | — |
| `:62994` | **146** Lakeside County | 65.9 s | 780 | attack-speed only |
| `:64102` | **164** Ashford Abbey | 213.8 s | 118 | — |
| `:64103` | **146** Lakeside County | 228.2 s | 1,074 | **yes** |

There are *two* Lakeside tapes. The chronological successor to Ascalon is `:62994`, and
it is the one that was nearly played; the combat is in the operator's **second** visit,
`:64103` — 4 × `SKILL_ACTIVATED` and roughly ten times the target-property traffic
(22 vs 3 `0x00A0`, 17 vs 2 `0x00A3`). **Pick a tape by decoding it, never by position in
the session.**

### 1.2 Pre-flight that matters

All four tapes name the **same** `map_file_id 113021` in their `0x0195`
`INSTANCE_LOAD_SPAWN_POINT`, differing only in spawn coordinates. The Gw.dat drift fix
that run 1 needed (`RUNBOOK.md`, "The two run directories drift apart") therefore covers
every tape in this capture — both archives now resolve 113021 to MFT row 177262.

That three different pre-Searing maps share one `map_file_id` is OBSERVED and
**UNVERIFIED as to why**. Do not build on it; it may mean the field is a region rather
than a map, or that pre-Searing Ascalon is one terrain file. It has not been checked.

---

## 2. What run 2 establishes

### T1 — A recording drives combat. OBSERVED.

1,074 of 1,074 events, 53,544 B, 186.2 s, **0 non-tape sends** — measured from the
gamesrv's own capture by counting `sent` records whose label is not `tape[…]`. Since our
server contributed nothing, everything the operator saw came from the recording.

The tape frames to 3,604 `GAME_SMSG` messages across **105 distinct opcodes, of which
our server can name 42**. It included 188 `WORLD_CREATE_AGENT`, 163 `WORLD_REMOVE_AGENT`,
351 `AGENT_MOVE_TO_POINT`, 1,511 `WORLD_SIMULATION_TICK` and 4 `SKILL_ACTIVATED`.

Operator's account: *"i walk over to a Wolf enemy, attack it from range, then cast my
Vampiric Gaze (skill 1) and Deathly Swarm (skill 2) on it and fight it until victory."*
The tape agrees, message for message:

| what was seen | in the tape |
|---|---|
| walking to the Wolf | agent 31 (never removed) moves, 1.7 → 39.7 s |
| the Wolf | agent 40, created 0.7 s, removed 68.5 s |
| Vampiric Gaze | `0x00E3 SKILL_ACTIVATED [227, 31, 153, 0]` at 10.5 s and 20.3 s |
| Deathly Swarm | `0x00E3 SKILL_ACTIVATED [227, 31, 105, 0]` at 13.2 s and 23.0 s |

**This is the first time this project has rendered combat.** No semantics were required
to do it: 63 of the 105 opcodes involved have no name anywhere in the repo.

### T2 — The client rendered a map it never asked for. OBSERVED.

The client's own game `VERSION` carried **`map_id=148`** (Ascalon City — the map its
character record held). The tape's `0x0199 INSTANCE_LOAD_INFO` declared **146**
(Lakeside County). The client loaded and rendered Lakeside County.

`--map 146` was passed but is **not** the explanation: `--game-args` reaches the gamesrv
only, and although `MAP_OVERRIDE` does rewrite `state["map_id"]` there, tape mode never
reads it — the whole preamble that would use it is skipped. The client genuinely asked
for 148 and was genuinely told 146.

This is the same family of result as run 1's identity finding: **the client does not
cross-check what it requested against what it is told.** The map it draws follows the
tape's `0x0195 map_file_id`, not its own `map_id`.

### T3 — Agent-id reuse, from ArenaNet's own server, at scale. CORROBORATES D1.

`../divergence/FINDINGS.md` D1 asked whether a removed agent id is poisoned. It was
closed on 2026-08-09 with a hand-built probe against the client. This tape answers it
again from the other direction — ArenaNet's own traffic:

```
agent 281: create@1.7s REMOVE@6.7s create@12.8s REMOVE@18.7s … create@181.5s REMOVE@186.0s
           (19 create/remove cycles in 186 seconds)
agent 284: 19 cycles.   agents 273/274/275/276: 5–6 cycles each.
19 of the 45 agent ids the tape uses are created more than once.
```

The client accepted every one of them and never complained. Id reuse after
`WORLD_REMOVE_AGENT` is not merely permitted; on ArenaNet's server it is **routine and
high-frequency**. This is corroboration by an independent witness, not our probe agreeing
with itself.

> **EXPLAINED 2026-08-10.** The operator names the mechanic: Lakeside is full of **Plague
> Worms, which burrow**, and Guild Wars hides a burrowed creature from targeting. So this
> is not spawn-and-death churn — it is one creature going away and coming back, and
> ArenaNet hands it **the same agent id every time**. That sharpens D1 rather than
> softening it, and it means `WORLD_REMOVE_AGENT` is how the client is told a creature is
> *untargetable*, not only how it is told one died. Our server has no concept of this and
> ~~it runs entirely through the two opcodes we already implement.~~

> **CORRECTED 2026-08-10, same day, by re-reading the tape instead of the paragraph above.**
> Three things in T3 are wrong or understated, and the last one was about to be built on.
>
> * **19 is not the ceiling.** Agents 283 and 285 cycle **23** times, 282 cycles 21.
> * **"Created more than once" is not the burrow signature.** The Ascalon *outpost* tape
>   has 53 multi-create ids and most carry the `play` allegiance — those are players
>   walking in and out of range. The real signature is three-part: model `0x200005A2`
>   (monster class | definition 1442), allegiance `mon1`, and `0x00F0 = 0x1000` on create.
> * **It does NOT run entirely through `0x0020`/`0x0021`. REFUTED, 151 of 151**, across
>   two independent Lakeside visits. Every worm re-creation is a fixed five-message burst —
>   `0x009F[66,agent,0]`, `0x00F0[agent,0x1000]`, `0x0020`, `0x006D[agent,item,0]`,
>   `0x0026[agent,9]` — and the visible phase carries `0x00F1[agent,0]` at exactly 2.00 s
>   after the create and `0x00F1[agent,0x1000]` exactly 2.00 s before the remove (n=132
>   each, every one inside ±60 ms). The removal side *is* bare, as T3 implies: 134 of 134
>   are a lone `0x0021`. Six opcodes, not two, and `0x00F0` is D2 — the highest-count
>   message our server has never sent.
>
> Every worm re-emerges at **byte-identical coordinates**, which the wiki independently
> predicts (a submerged worm cannot move). Two period families share one model and
> distance from the player does not separate them: 272–277 run a ~33 s cycle, 281–285 a
> ~8–10 s one. Only the two 2.00 s windows are fixed; the rest is not a period.
>
> And the thing no offline reading can settle: ArenaNet sends the `0x0056` definition
> **once for 140 creates**. Our own probe re-sent it before every re-create, so "does a
> definition survive a removal" has never actually been asked — and `agents.py` warns that
> an agent whose definition was never sent takes the client down on `index < m_count`.
> That is the difference between a burrow and a client assert, and it needs the client.

### T4 — `GAME_CMSG 0x0046` field 1 is a skill id. OBSERVED, ground-truthed.

After the tape, the operator pressed skills. The client sent:

```
149.7s  0x0046 USE_SKILL [32838, 153, 0, 281, 0]
155.7s  0x0046 USE_SKILL [32838, 153, 0, 273, 0]
157.3s  0x0046 USE_SKILL [32838, 153, 0, 273, 0]
157.5s  0x0046 USE_SKILL [32838, 153, 0, 273, 0]
158.0s  0x0046 USE_SKILL [32838, 105, 0, 273, 0]
```

The operator named the two skills independently, *before* the payloads were decoded. The
client's own tables then confirm them:

| operator said | field 1 | client skill table | client string table |
|---|---|---|---|
| Vampiric Gaze (slot 1) | **153** | prof 4 / attr 4, 10 energy, 1.0 s cast, 8 s recharge | name id 25126 → **'Vampiric Gaze'** |
| Deathly Swarm (slot 2) | **105** | prof 4 / attr 5, 10 energy, 2.0 s cast, 6 s recharge | name id 25030 → **'Deathly Swarm'** |

So **field 1 is the skill id, not the skillbar slot** — the values are not 0 and 1 — and
field 3 is the target agent id. This is a labelled human action matched against two
independent client-derived tables, which is as strong as evidence in this repo gets.
Method note: the corroborating tables come from `skilltable.py` and `textrec.py` reading
the client, and the operator's label came first, so this is not our decoder forcing the
answer.

### T5 — Two more c2s opcodes acquire candidate meanings. RECONSTRUCTION.

Neither is confirmed; both are consistent across every occurrence in the run.

* **`0x00C1 [req, agent_id, 0]`** — target select, `0` clears. 24 sends, alternating
  between an agent id and 0, and it **precedes every `USE_SKILL` with the matching id**
  (`[281]`@148.2 s → skill→281@149.7 s; `[273]`@155.5 s → skill→273@155.7 s).
* **`0x0026 [req, agent_id, 0]`** — attack or interact. 6 sends, each immediately after a
  `0x00C1` naming the same agent (`[274]`@152.5 s → `0x0026 [274]`@152.6 s).

Also CORROBORATED, since the operator labelled the action: `0x003D TURN_TO_DIRECTION`
(29 sends, carrying position + facing — what held-key movement produces) and
`0x003E MOVE_TO_COORD` (8 sends, position only — what a click produces). Those names were
UPSTREAM; a labelled walk now supports them.

And **`0x0009 [req, 16, 0]` is a client keepalive**: 37 sends at 5.0 s intervals from
4.6 s to 184.7 s, dead regular, independent of anything on screen. OBSERVED.

> **CORRECTED 2026-08-10 by the labelled run**
> ([../cmsg/FINDINGS.md](../cmsg/FINDINGS.md) §3). "Independent of anything on screen"
> is right; the implied "unconditional 5 s heartbeat" is wrong. In the labelled capture
> all 37 sends land during the tape and **zero** land in the three and a half minutes of
> active play after it — the client stopped the moment the server went silent. It is
> tied to server traffic, not to a free-running timer. Whether it is a reply or a timer
> the server resets is UNVERIFIED.

### T6 — A tape answers nothing, and the client tolerates it. OBSERVED.

Tape mode never replies to c2s — the dispatch `continue`s. The operator's report is the
behavioural consequence: *"gateways and attacking and casting blocked."* The client sent
121 well-formed messages across 15 opcodes, received **no** answer to any of them, and
neither crashed nor disconnected; it was still sending `0x00C1` and `0x000C` after the
tape completed.

This is a property of the instrument, not a defect, but it is the ceiling on what a tape
can test and it should be stated whenever a tape run is reported: **a tape shows a load
and a populated, animated world; it cannot show control.**

### T7 — A tape's visible length and its real length are not the same. OBSERVED.

The operator held all input until they believed the tape had ended, judging by their
character standing still — and then reported input starting "after the tape ended", while
the measurement shows their first message at 86.2 s of a 186.2 s tape. Both accounts are
correct:

```
the recorded PLAYER agent (31) moves:  1.7s → 39.7s, then never again
all other agents keep moving:          throughout, to 186.2s
operator's first input:                86.2s
tape actually completes:               186.2s
```

The recorded operator walked, fought, and then **stood still for the last 146 seconds**
while the world carried on around them. From the seat, that is indistinguishable from the
tape ending. Nothing is wrong with the tape.

**Consequence for the procedure:** `play_tape` already prints `tape N/1074` progress and
a `tape complete` line to the gamesrv terminal. A tape run's operator should be told to
watch *that*, not the avatar, before treating the client as free. Recorded in
`RUNBOOK.md`.

---

### T8 — `0x01A5` is the instance handoff, and the capture proves it. OBSERVED.

Found while diagnosing why a third run died: the Ascalon tape ends by **leaving the map**.
Its second-to-last message is `0x01A5` carrying a 24-byte blob, and reading that blob as a
`sockaddr_in` — family 2, port big-endian, then IPv4 — gives an address. The message after
it is `0x0099 MAP_UPDATE_CURRENT` naming a map id.

**Checked against a witness we did not consult to make the claim** — the capture's own
later connections:

| tape | `0x01A5` decodes to | `0x0099` map | what the capture's NEXT connection actually did |
|---|---|---|---|
| Ascalon City (148) | `54.198.7.73:6112` | 146 | connected to `54.198.7.73`, VERSION said map 146 |
| Lakeside #1 (146) | `52.3.40.244:6112` | 164 | connected to `52.3.40.244`, VERSION said map 164 |
| Ashford Abbey (164) | `54.198.7.73:6112` | 146 | connected to `54.198.7.73`, VERSION said map 146 |
| Lakeside #2 (146) | **absent** | — | nothing; the session ended here |

Three for three on both fields. This is the message that made run 1 end at `Code=005`:
the client read it, dialled ArenaNet, and the cage refused.

**Two consequences.** First, `0x01A5` is exactly what tape-chaining needs — intercept it,
substitute a loopback `sockaddr`, and hand the client the next connection's tape.
`toolkit/authsrv/tape.py` `stop_before_transfer` already locates it precisely.

Second, and this is the operational one: **only a capture's LAST connection is usable for
anything after the tape.** Every other tape ends by zoning out, because that is why the
recording ended. `--labelrun` therefore truncates, dropping one event of 1,209 from
Ascalon and none from Lakeside #2.

> **The trap, recorded because it produced a plausible wrong answer.** `0x0099` is NOT a
> transfer marker. The client is also told its *current* map during the instance load,
> with the same opcode — so cutting on `0x0099` truncated Ascalon at byte 962 of 74,319,
> one event out of 1,209, and produced a "successfully truncated" tape with an empty
> world. The destination reading is only correct for the copy that follows `0x01A5`.
> `test_tape.py` now requires that `0x0099` **survives** the cut.

### T9 — `0x01A5` is `GAME_SERVER_TRANSFER`, and the four tapes are one chain. OBSERVED.

T8 read the sockaddr. The message carries more than that, and the extra fields are what
turn "the tapes probably chain" into something the capture can refute.

**Fields 2, 4 and 6 are the next instance's `world_id`, `map_id` and `player_id`** — and
every one of them equals what the *next connection* then sent in its own client-to-server
VERSION frame. Three transitions, four fields each, **12 of 12**. The VERSION frame is
parsed straight off `wire.jsonl`; the decrypted channel files do not carry those ids at
all, so the witness is the client's own first bytes on a connection nothing of ours had
touched yet. That makes `0x01A5` the game-channel twin of `AUTH_SMSG 0x0009
GAME_SERVER_INFO`, and it is the **first name any `GAME_SMSG` opcode has ever carried** —
the imported catalog has 487 layouts and had zero names.

The values are session identifiers from a live account, so they live in the vault and not
in `schema/`. What is recorded is the structure and the fact of the match;
`tape.chain()` re-derives it every run and **refuses a link it cannot prove** rather than
ordering hops by timestamp.

```
1. 10.0.0.210:60935  map 148 Ascalon City    74,319 B   48.6s  -> map 146
2. 10.0.0.210:62994  map 146 Lakeside County 41,997 B  147.6s  -> map 164
3. 10.0.0.210:64102  map 164 Ashford Abbey   14,896 B   14.0s  -> map 146
4. 10.0.0.210:64103  map 146 Lakeside County 53,544 B  186.2s  (chain ends)
                                            ---------  ------
                                            184,756 B   396.3s
```

**The rewrite is smaller than it looked and the risk is bigger.** `0x01A5` is the first
message of the last event in all three linking tapes, the sockaddr sits at message offset
+2, and repointing it changes **4 bytes of 74,319** — length-preserving, so the event
partition and `load_tape`'s byte accounting are untouched, and the tape still frames 100%
clean to its final byte.

What the rewrite costs is a safety control, and this is the part worth remembering.
Before it, an un-truncated tape failed **closed**: the client dialled ArenaNet, the cage
refused, and `Code=005` said so out loud — which is exactly how run 1 ended on 2026-08-10.
After a rewrite, a wrong address is a dead connection with no signal at all. So
`rewrite_transfer` refuses any host outside 127/8 and self-checks the result offline
before the client ever runs; that refusal *is* the replacement for `Code=005`, not
hygiene around it.

**The port is a trap and remains UNVERIFIED.** The client is OBSERVED to ignore the
advertised port and dial `<host>:6112` — but that was measured on the **auth**-channel
handoff, and `0x01A5` is the **game** channel. Every recorded `0x01A5` advertises 6112,
which is also the hardcoded value, so the live capture cannot tell the two apart. Hops are
therefore separated by 127.x **alias**, which is correct either way; `--tape-rewrite-next
host:port` exists so one run can settle it.

**NOT FOUND, and it decides nothing here but would decide a later question:** whether the
client will re-dial an endpoint it has just been disconnected from. All three recorded
hops changed IP, so the capture never exercised host reuse — which is the reason the
implementation gives each hop its own alias instead of reusing one listener.

### T10 — The client defers every transfer after the first, and the recorded server's HANG-UP is what releases it. OBSERVED, from the binary.

The first chained run, 2026-08-10. Two hops played end to end and the third never dialled:

```
hop 1  127.0.0.3  Ascalon City     tape complete: 1209/1209 in  48.6s   -> dialled hop 2
hop 2  127.0.0.4  Lakeside County  tape complete:  780/780  in 147.6s   -> never dialled
hop 3  127.0.0.5  Ashford Abbey    no connection ever arrived
```

The client was **healthy**: correct destination on its loading screen (Ashford Abbey),
correct alias in its overlay (`127.0.0.5`), auth channel still heartbeating three minutes
later, no `Assertion` in `Gw.log`, and **no SYN at all** in `netstat` — it never opened a
socket. `gamesrv3` was listening the whole time.

**The client has two transfer paths.** Handler `0x0084f290` branches on bit `0x20` of a
flags dword at `+0x190`:

```
mov  eax, [esi + 0x190]
test al, 0x20
je   0x84f359      ; CLEAR -> call 0x850df0, dial immediately
or   eax, 0x10     ; SET   -> stash the sockaddr + ids at +0x1c8, mark pending, return
```

and **the connect function sets that bit itself** — `or [ebx+0x190], 0x20` at `0x00850e56`,
inside `0x850df0`, no `ret` between them. So **exactly one game-channel transfer per
session dials immediately; every later one defers.**

That is precisely the observed shape. Hop 1's connection came from the *auth* handoff
(`AUTH_SMSG 0x0009`), a different path, so bit `0x20` was still clear when its `0x01A5`
arrived — immediate dial, 140 ms, worked. Connecting to hop 2 went through `0x850df0` and
set the bit, so hop 2's `0x01A5` stashed and waited.

**What it waits for is the connection it already holds going away, and the recording says
so.** ArenaNet's server hangs up immediately after each handoff — `:62994` closes at
t=213.70 and `:64102` opens at t=213.84, and the same 0.12–0.14 s shape at all three
transitions. Our player ran out of events and sat on the socket.

`authsrv.close_after_transfer` now hangs up when a tape contains a transfer — keyed on the
tape's *contents*, never a flag, because the last hop and every `--tape-no-transfer` run
exist so the client keeps playing afterwards. Pinned in `test_burrow.py` §4, both
directions, and both mutations go red.

> **The hang-up was NECESSARY BUT NOT SUFFICIENT — settled by the re-run, 2026-08-10.**
> With `close_after_transfer` in place the chain still stops at the same place: hop 1
> played 1209/1209, we hung up, the client dialled hop 2 and played 780/780, we hung up
> again, and hop 3 was never dialled. Identical treatment at both transitions, different
> outcome, twice. Keep the close — it is what the recorded server does — but it is not
> the release.

### T11 — What releases a deferred transfer is a player-state transition, not a socket close. OBSERVED.

Following T10's pending bit `0x10` to its consumer, at `0x00851402`:

```
mov  eax, [edi + 0x190]
test al, 0x10
je   0x85145e            ; nothing pending -> done
and  eax, 0xffffffef     ; clear pending
mov  [edi + 0x190], eax
push [edi + 0x1f8] ... [edi + 0x1c8]    ; the stashed sockaddr and ids
call 0x850df0                            ; DIAL
```

That code lives in a handler whose own assertion names the module and the condition:

```
!(context->playerFlags & PLAYER_FLAG_CONNECTED)
        P:\Code\Gw\Mission\Cli\MsCliGame.cpp:76
```

`playerFlags` is `+0x2a8`; `PLAYER_FLAG_CONNECTED` is **bit 1**, set at `0x008513a7` and
cleared at exactly two sites, `0x00850ca7` and `0x00851534`. The handler also dispatches
event `0x10000112` (the connect path dispatches `0x10000111`).

So the dial is released when the client's **mission/player state** says it is no longer
connected — a game-level transition inside `MsCliGame`, not the TCP socket going away.
That is why hanging up twice changed nothing, and it is consistent with everything else
observed: the first transfer of a session never needs the release because bit `0x20` is
still clear and it dials immediately.

**Two dead ends, ruled out cheaply and recorded so they are not re-run.**

* *Map content.* All four tapes declare the **same** `map_file_id` 113021 in their
  `0x0195`, so Ashford streams what Ascalon and Lakeside already streamed. The loopback
  build's updater kill switch is not implicated.
* *The auth channel.* It carries exactly two `GAME_SERVER_INFO` in the whole 411-second
  session — map 0 and map 148 — both before the first game hop. The three map transitions
  get nothing from it; the remaining auth traffic is `REQUEST_RESPONSE` acks our server
  already answers. The transition is game-channel only, and the tape plays all of it
  (780/780).

### T12 — The flag is cleared by an instance teardown with TWO routes, and only one of them is a message. OBSERVED.

`PLAYER_FLAG_CONNECTED` (bit 1 of `+0x2a8`) is cleared at exactly two addresses, and both
are the tail of the **same** nine-call sequence, gated on the flag being set:

```
test byte ptr [X + 0x2a8], 2      ; only if still connected
push X;  call 0x851f70            ; then nine subsystem shutdowns
mov ecx, X; call 0x8560b0 / 0x8043e0 / 0x828440 / 0x82cdc0
call 0x856240 / 0x80e110 / 0x844720 / 0x83fab0 / 0x85c420
and  [X + 0x2a8], 0xfffffffd      ; CLEAR PLAYER_FLAG_CONNECTED
```

That is the instance being torn down. The two routes into it:

* **`0x00850c50`** — one caller only, `0x0084f869`, which lies inside the RECV handler for
  **`GAME_SMSG 0x01B1`** (handler `0x0084f740`; the next handler starts at `0x00856920`).
  So a server message *can* drive the teardown.
* **`0x008514d0`-ish** — no message involved. It dispatches event `0x10000110` and branches
  on a **reason code at `[esi+0xc]`**, the same field the pending-transfer consumer opens
  with (`cmp [esi+0xc], 0`). This is the network layer's own disconnect event.

**`0x01B1` is NOT the answer, and this is the check that says so.** It appears **zero
times in all four tapes** — ArenaNet never sent it on any game connection of that session,
yet the real client transferred three times. So the route that matters in a normal
transfer is the second one, and it is client-side: the reason code decides everything.
Recording this because "`0x01B1` releases the transfer, send it" is exactly the plausible
wrong answer this trail invites, and the tapes refute it in one decode.

### T13 — The reason code is a real dispatch, and our close produced the wrong one. OBSERVED.

Read straight out of the disconnect path:

| `[esi+0xc]` | what the client does |
|---|---|
| **0** | falls through to `0x008515b7` — **`call 0x850df0`, re-dials the stashed address** |
| **< 3** | `jl 0x851695`, continuing toward that path |
| **≥ 3** | `pop`/`ret` — nothing; the pending transfer is simply dropped |
| **7** | special-cased against flag bit 8 → `0x851870` |

So a deferred transfer is released **only by the disconnect the client considers clean**,
and `close_after_transfer`'s first version could not produce it. It called
`shutdown(SHUT_RDWR)` and then `close()` with bytes still unread — and the client always
has bytes in flight after a tape ends, it keeps sending `0x8008`/`0x800c`. Closing a
socket with an unread receive buffer makes Windows send an **RST rather than a FIN**,
which is a different reason code. That is why hanging up twice released nothing while
looking exactly like the right fix.

Now: half-close (`SHUT_WR`, our FIN), drain what the client is still sending until it
closes its half or a 2 s deadline passes, then `close()`. An ordinary graceful shutdown,
which is what the recording shows. `test_burrow.py` §4 asserts the half-close specifically
rather than "close was called", and reverting it to `SHUT_RDWR` goes red.

**SUPERSEDED by T14: the close is not the release at all, graceful or not.**

**UNVERIFIED:** that reason 0 is what a graceful FIN actually produces here. The mapping
from wire event to reason code has not been read — only the branch on it has. The next
chained run is the test, and it is the cheapest one available.

**Where to look next if that fails.** The reason code at `[esi+0xc]`. Three events live in this family —
`0x10000110`, `0x10000111` (dispatched by the connect at `0x850df0`) and `0x10000112` —
and the handler at `0x00851380` treats `[esi+0xc] == 0` as success, asserts it was not
already connected, sets the flag, and only then consumes any pending transfer. The open
question is what reason code our close produces versus ArenaNet's, and whether the client
distinguishes a server FIN from a reset. That is answerable offline by reading the network
layer, and it is where the next session should start — not with another six-minute run.

**Also settled, and it cost nothing:** the recon's stated blocker — "consecutive hops to
the same endpoint were never witnessed" — is irrelevant. Every hop here had a distinct
alias and hop 2→3 failed anyway. And the port question is still open: the client never got
far enough to reveal one.

---

## 3. What run 2 did not settle

* **Control.** Out of scope by construction (T6). Unchanged from `tape.py`'s docstring.
* **Session-embedded absolute time** — `../divergence/FINDINGS.md` §4.2 item 5. Still
  UNVERIFIED. Run 1's apparent evidence was retracted as our own contamination; run 2
  produced no assert at all, which is consistent with the field not existing *and* with
  it existing and being ignored. Not tested.
* **Why three maps share `map_file_id 113021`** (§1.2).
* **Whether `0x0026` is attack specifically** rather than a general interact — the
  operator tested attacking and gateways in the same window, and a gateway is also an
  interact. One labelled run separating the two would settle it.

---

## 4. Next, in order of value

1. **Chain the tapes across a map transition.** T8 found the message that makes this
   concrete: `0x01A5` carries the next instance's `sockaddr_in`, and
   `tape.stop_before_transfer` already locates it exactly. Rewrite that blob to a
   loopback address instead of cutting it, arm the next connection with the next tape,
   and four instance tapes become one continuous session. Largest single increase in
   what the instrument covers, and no longer speculative.
2. **Diff our server against a tape at matching points in the load.** The tape is the
   first oracle this project has that it did not write itself, which turns D2–D11 from a
   list into a failing test.
3. **A labelled input run — BUILT 2026-08-10, not yet performed.**
   `toolkit/authsrv/labelrun.py` plus `--labelrun`; procedure in `RUNBOOK.md`. Run 2 got
   T4 and T5 as a by-product of an unplanned five minutes, so a deliberate pass is the
   cheapest naming instrument available: it needs no new capture and no live session.

   **The size of the prize, measured:** `schema/messages.json` carries field layouts for
   **194 `GAME_CMSG` opcodes and names for none of them** — `authsrv.py`'s own c2s print
   site says so ("No semantic names exist for GAME_CMSG in this repo yet; the schema
   knows shapes only"). Our server names 11 by hand. **15 have ever been witnessed
   coming out of a real client**, all of them in run 2.

   The design decision worth recording: steps are marked into the capture **by the
   server, at the moment it prompts**, so attribution is by timestamp against a mark we
   wrote — not by inferring boundaries from gaps in the c2s stream afterwards. Gap
   inference silently misaligns the moment a step produces nothing, and *a step producing
   nothing is a result here*. Two idle steps bracket the script as controls: traffic in a
   window the operator was told to sit out means the marks and the messages disagree, and
   the run must be discarded rather than read. `test_labelrun.py` breaks that control on
   purpose to prove it can go red.


### T14 — Exactly ONE game-channel transfer per session dials. OBSERVED, by a discriminating run.

Three chained runs stalled at the second hop and each time the fix addressed the close.
None of them was the cause. `--tape-chain-from` settled it in one 6-minute run by making
the *failing* transition the *first* one:

| run | transfer #1 | transfer #2 |
|---|---|---|
| full chain | Ascalon (148) -> Lakeside (146) **worked** | Lakeside -> Ashford (164) **stalled** |
| `--tape-chain-from 62994` | Lakeside -> Ashford **worked, 118/118** | Ashford -> Lakeside **stalled** |

The same Lakeside -> Ashford transition **works as the first transfer and fails as the
second**. So it is not the transition, the map, the tape, the destination address or the
shutdown: it is the **ordinal**. That is exactly what T10's reading of the binary
predicted -- bit `0x20` at `+0x190` is clear for the first transfer (immediate dial via
`0x850df0`, which then sets it) and set for every one after (stash + pending, deferred).

Two things this also confirms in passing, both live rather than by decode:

* The client echoes the handoff's ids verbatim in its next VERSION frame -- hop 2 opened
  with `world_id=3775625635 map_id=164 player_id=4145270229`, the exact values hop 1's
  `0x01A5` carried. T9's 12/12 match, observed in flight.
* Ashford Abbey renders. The 118-event tape is the cheapest full instance load we have,
  and it is now a 14-second test loop for anything touching transfers.

**What is dead:** that the close matters. Both closes drained **0 B** and the graceful
half-close changed nothing. Keep it -- it matches the recording -- but it is not the
release, and T13's fix should be read as correct-and-irrelevant.

**What is left, and it is now a single question:** what makes the client consume a
*deferred* transfer. The consumer at `0x00851402` sits in a handler that treats
`[esi+0xc] == 0` as success, asserts `!(playerFlags & PLAYER_FLAG_CONNECTED)`, SETS that
flag, and only then dials the stashed address -- i.e. it looks like a
**connection-established** handler that dials a pending transfer once the new connection
is up. If that reading is right the deferral is waiting on a connection the client is not
making, and the next thing to read is what drives `0x00851380` at all, since it has no
direct callers.


### T15 — The deferral is released by network event 0x1E, and our close raises 0x1F. OBSERVED.

`0x00851380` has no callers because it is a **switch case**. The function starts at
`0x00851340`, takes an event struct in `[ebp+0xc]`, and dispatches on the event **type**
at `[esi]`:

```
mov   esi, [ebp+0xc]
mov   eax, [esi]          ; event type
add   eax, -0x1d          ; table is based at 0x1D
cmp   eax, 0xbb
ja    0x851696            ; default: do nothing
movzx eax, byte ptr [eax + 0x8516c4]
jmp   dword ptr [eax*4 + 0x8516a8]
```

The index map at `0x8516c4` is `[0,1,2,6,6,6,...]`, so **exactly three** event types are
handled and everything else falls to the default:

| event | case | what it does |
|---|---|---|
| **`0x1D`** | `0x0085155f` | `and [edi+0x190], 0xfffffdfb`; if reason `0` -> **dials** at `0x008515b7` |
| **`0x1E`** | `0x00851373` | **`and [edi+0x190], 0xffffffdd` — clears bit `0x20`** — then the `0x851380` body: on reason `0` marks connected, dispatches `0x10000112`, consumes pending `0x10` and **dials** at `0x00851446` |
| **`0x1F`** | `0x00851480` | dispatches `0x10000110`, tears the instance down, clears `PLAYER_FLAG_CONNECTED`, and on reason `>= 3` returns. **Never dials.** |

That is the whole mechanism, and it explains every run:

* The **first** transfer never needs an event: bit `0x20` is clear, so the `0x01A5`
  handler dials inline.
* Every **later** transfer stashes and waits for `0x1E` (or `0x1D`), which is also the only
  thing that clears bit `0x20` and would let a *third* transfer work.
* A peer that simply goes away produces `0x1F` -- teardown, no dial. Which is what our
  close produces however politely we do it, and why three shutdown fixes changed nothing.

**Where `0x1D`/`0x1E`/`0x1F` come from is the remaining unknown**, and it is now a small
one: they are raised by the client's own connection layer, not by any message. The
question is what distinguishes them -- most likely who initiated the close and whether the
client was expecting it. Worth noting we may not be able to produce `0x1E` from the server
side at all, in which case chaining beyond one hop needs a different lever than a tape.

**Correction to a step on the way here:** `0x006f4254` looked like a reference installing
this handler and is not -- it is `push 0x8513`, an immediate whose bytes matched the
pointer scan. A byte-pattern search over `.text` finds instruction operands as readily as
data, and this one wasted a query.


## T16 — the second character, and what the burrow status values actually are

**OBSERVED**, capture `20260810T235916` (2026-08-11): a second live session on a
deliberately different character — a Ranger, where the first was a Necromancer —
walking the **same three maps** (Ascalon City 148 -> Lakeside County 146 -> Ashford
Abbey 164 -> 146). Character and profession are the variables; map content is not.
10,599 GAME_SMSG messages over 4 chained tapes, framing 100% clean, 0 B unconsumed.
6/6 connections decrypted, stamped `origin: live`.

**Every invariant in `test_smsgnames.py` held on the new character with nothing
changed.** The file's own shipped caveat — "4/4 tapes is four samples sharing a
character record" — is retired, and the checks now run pooled over both captures
(8 tapes, 21,543 messages). Two results worth stating separately:

- The **opcode vocabularies are nearly identical**: 146 distinct each, **148 in
  union**, 2 in and 2 out. The surface an ordinary session touches is stable across
  characters.
- The **`0x013F` bag table's (bagType, slot, capacity) triples are byte-identical**
  across both characters. That was the sharpest character-versus-protocol question
  in the naming pass and the answer is protocol. The surrounding ids stay
  session-scoped, so it is a fixed SHAPE, not a shippable constant table.

### The burrow status values are named, and death is not a burrow

The session included a deliberate experiment: the operator targeted a worm above
ground, hit it with a skill, watched it burrow, **kept it targeted**, and the
nameplate re-attached when it resurfaced. The server-side trace of that agent
(definition 1442, the Lakeside worm) is the whole cycle three times over, then a kill:

```
t= 1.90  0x00F0 AGENT_INITIAL_STATUS  status=0x1000   <- created ALREADY hidden
t= 1.90  0x0020 WORLD_CREATE_AGENT    def=1442 speed=12.0
t= 1.90  0x006D
t= 1.90  0x0026 AGENT_UPDATE_FLAGS    flags=0x9
t= 3.91  0x00F1 AGENT_UPDATE_STATUS   status=0x0000   <- surfaces, +2.01 s
t= 4.58  0x00F1 AGENT_UPDATE_STATUS   status=0x1000   <- burrows
t= 6.60  0x0021 WORLD_REMOVE_AGENT                    <- +2.02 s after burrowing
   ... repeats at t=11.39 and t=17.98, same agent id each time ...
t=19.98  0x00F1 status=0x0000                         <- surfaces, +2.00 s
t=21.13  0x0035 / t=21.90 0x00A4 / t=22.49 0x00A7     <- the fight
t=23.20  0x00F1 status=0x0010                         <- CHAR_STATUS_DEAD
t=23.20  0x0026 AGENT_UPDATE_FLAGS    flags=0x8
```

So T3's two 2.00 s windows now have **names on both ends**: `0x00F1` status `0x1000`
is hidden/burrowed and `0x0000` is surfaced, and the windows are create -> surface
and burrow -> remove. This is `CHAR_STATUS_*` in the client's own vocabulary
(`ChCliInt.h:254`, `studies/smsg/FINDINGS.md`), not an effects field.

**Death is not a burrow, and that is a distinction the model could have got wrong.**
The kill interrupts the cycle: status goes to `0x0010` (DEAD) while the worm is
*surfaced*, and there is no `0x1000` and no remove afterwards. A burrow always removes;
a death does not.

**The DEAD bit is one per death, n=2, and both name what was killed.** The corpus
had 3 observations in 10,944 messages before this; the new session adds exactly two,
and they are definition 1434 at speed 288.0 (the River Skale Queen) and definition
1442 at speed 12.0 (the worm). Both are followed by `0x0026` at +0.00 s. An earlier
reading of this file called two observations a shortfall — it is not, it is one per
kill, and the operator killed two things.

### 0c is answered, and not by the probe built for it

**The definition is sent ONCE and referenced by every create.** For the worm in the
new capture: **1 `0x0056` declaration, 32 creates**. Pooled across both captures the
most-reused definition is declared once and referenced by **140** creates. Since it
is the *same client* on both ends, this settles what `probes.py`'s `burrow` probe was
built to ask: **the client keeps an NPC definition across agent removal.** If it did
not, 31 of those 32 creates would name a definition slot the client no longer holds,
and a create against an undeclared slot takes it down on `Array.h`'s `index < m_count`.
It does not go down.

A server may therefore declare once and re-create freely. The probe becomes
confirmatory rather than necessary; what it still uniquely tests is whether OUR create
path is correct when it stops resending, which is a much safer change to make now.

### Still open from this session

- `0x0035`, `0x00A4`, `0x00A7` fired during the fight in the 2.1 s before the kill and
  are **unnamed**. They are the most promising combat opcodes in the corpus and this
  is the first capture that has them next to a known, narrated kill.
- The skill cycle is still thin: `0x00E3`/`0x00E5` are 2 each here against 4 each
  before. A session built around casting rather than around movement would settle it.
- The **client-to-server** direction is decodable and barely mined — see T17.

## T17 — the c2s stream decodes, and the opcodes carry bit 0x8000

**OBSERVED.** Both live captures store a `c2s` frame per connection alongside the
`s2c` one, and it decodes cleanly as GAME_CMSG **once bit `0x8000` is masked off**:
419 messages / 27 opcodes (Necromancer) and 500 / 25 (Ranger), **0 B unconsumed** in
both. Without the mask nothing decodes at all.

The mechanism was already read out of the binary by the naming pass without anyone
connecting it to this: `0x000C`'s handler replies through `MsgConn`'s send, which
computes the wire opcode as `((conn+0x54) != 0 ? 0x8000 : 0) | msg[0]`. So the game
channel sets the high bit on everything the client transmits. `studies/divergence` D4
recorded a mysterious client reply of `0x8009`; it is GAME_CMSG `0x0009` with this bit.
`codec.decode_stream` already takes a `mask` parameter, so no code change was needed.

**Why this matters more than the count suggests.** The labelled-run programme
(`labelrun.py`, `studies/cmsg/FINDINGS.md`) names GAME_CMSG opcodes by telling an
operator to do one thing at a time on OUR server. These captures are the same
experiment against **ArenaNet's** server, with a narrated session: two quests taken and
turned in, a gate transition, a skill cast at a named target, two kills. The top c2s
opcodes are already suggestive — `0x003D` MOVE_SET_HEADING dominates both (161 and
269), and `0x0009` (81 / 59), `0x0084` (35 / 35 — *identical across sessions*),
`0x003B` (11 / 11), `0x0092` (10 / 10), `0x0012` (8 / 8), `0x0008` (5 / 5),
`0x0060` (5 / 5), `0x0091`/`0x0088`/`0x0090` (4 / 4 each) look like a fixed login
handshake rather than anything the player did.
