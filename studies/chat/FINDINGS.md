# The chat family: `0x005D`–`0x0061` decoded, and the sender/body cross-check

**2026-08-19.** This closes `PLAN.md` §8 item 3 — *"`0x005D` — candidate `CHAT_MESSAGE`:
needs the sender/body cross-check"* — and it closes it **offline**, from captures the
vault already held. No client was launched for any claim in this document.

Corpus: the 13 readable live captures (of 14 under `vault/captures/live/`;
`20260817T175358` is an aborted run with no assembled game stream), read with
`toolkit/authsrv/cmsgstream.py` against `schema/messages.json` + `overrides.json`,
coded strings parsed with `toolkit/clientscan/codedstr.py`. Every count below is from
one scan over that corpus; the scan scripts are throwaway (scratchpad), the numbers
are restated here with enough method to re-derive each.

Label vocabulary per `studies/character/FINDINGS.md`.

---

## 1. The family — five consecutive RECV handlers, one mechanism

**[SOURCED]** The client's RECV table gives `0x005D`–`0x0061` five *consecutive*
handlers — `0x0091df60`, `0x0091df80`, `0x0091dfa0`, `0x0091dfc0`, `0x0091dfe0`
(`msgshape.py`, pinned build 38797) — with shapes that agree field-for-field with
the imported schema:

| opcode | RECV shape | wire max | role (this study) |
|---|---|---|---|
| `0x005D` | `[string16(122)]` | 248 B | **body fragment** — coded string, appended |
| `0x005E` | `[u16, u8]` | 5 B | **commit: server line** — `[subject playerId \| 0, channel]` |
| `0x005F` | `[agent_id, u8, string16(8)]` | 25 B | **commit: agent line** — `[agent, channel, sender enc-name]` |
| `0x0060` | `[u8, string16(32), string16(6)]` | 83 B | catalogued, **0 live sightings** (shape reads name + tag) |
| `0x0061` | `[u16, u8]` | 5 B | **commit: player line** — `[sender playerId, channel]` |

Prior per-opcode work reconciled here rather than re-derived
(`project-rurik-smsg-naming-method`): `0x005D`'s handler appends to the growing
string table at `ctx+0x2c +4` (`studies/smsgnames/FINDINGS.md` §4);
`0x005F`'s handler marshals into the "coded string" queue off
`GlobalSingleton+0x2c` (`studies/newopcodes/FINDINGS.md` `0x005F`);
`studies/isle/FINDINGS.md` §5 established by loopback probe that a bare `0x005D`
**renders nothing** and one followed by `0x005E` renders a Local-chat line.

## 2. The state machine — OBSERVED, exceptionless on 227 bodies

Across the corpus: **227 × `0x005D`, 133 × `0x005E`, 45 × `0x005F`,
0 × `0x0060`, 47 × `0x0061`**.

- **Every `0x005D` is immediately followed by a commit tag or another `0x005D`**:
  133 by `0x005E`, 47 by `0x0061`, 45 by `0x005F`, 2 by another `0x005D`.
  No other opcode ever appears between a body and its tag. 227 = 133+47+45+2.
- **Every commit tag immediately follows a `0x005D`.** 225 tags, 225 direct
  adjacencies, no tag with an empty buffer, no orphan body at stream end.
- **Multi-part bodies are real and the fragment cap is measured: 121 units.**
  Both continuations in the corpus (one long advert sent twice, to two channels,
  by the same player — `20260817T183756/:58389`, t=165.0) split their coded string
  into a **121-unit** first fragment plus a 2–3-unit remainder carrying the
  terminator. 121 = declared(122) − 1 — the same "declared cap is exclusive"
  rule `charstore` measured independently on `0x00F3`'s `string16(8)`
  (`studies/character/RUNS.md`, title_track). OpenTyria fragments at 122
  (`CHAT_MESSAGE_FRAGMENT_MAX_LENGTH`); ArenaNet's own traffic says 121.
- This settles `studies/smsg/FINDINGS.md` §10/§11's open row *"`0x005D` → `0x005E`
  23/24, deterministically adjacent, no field pair agrees"*: the 24th follower was
  `0x0061` (that capture's one player-chat line), and no field pair agrees because
  the body and the tag do not share a subject field — the tag carries the sender,
  the body carries the text.

## 3. The sender/body cross-check — the ask, answered

**[OBSERVED] `0x0061`'s word is the sender's playerId: 47 of 47 resolve against
the same connection's `0x0059 PLAYER_INFO` table** (field 1 → field 7 name), a
check run per connection that could have failed on any row. The strong cases are
outposts with real populations (31, 64, 13 players known), and the resolution is
demonstrably per-instance: **playerId 57 resolves to two different names on two
different connections** ("player A" on `143055/:60935`, "player B" on
`235916/:61193`) — a reader that pooled tables across connections would get one
of them wrong, which is `studies/reconstruction` §8.2(c)'s id-reuse control
arriving on the player table.

**[OBSERVED] The body is the typed text, verbatim, in the clear.** Player lines
carry a literal run — `LITERAL_MARK 0x0107` + UTF-16 code units + `0x0001`,
exactly `questdefs.py`'s measured framing — wrapped by one leading string id.
Real lines from ArenaNet's wire, sender resolved from `0x0059`, body decoded by
`codedstr.py`:

| capture/conn | tag | sender | line |
|---|---|---|---|
| `143055/:60935` | `[57, 12]` | player A | "wtb Axe grip of the paragon" |
| `235916/:61193` | `[66, 3]` | player C | "both are very viable " |
| `235916/:61193` | `[17, 3]` | player D | "i'd say necro is more survivability and ele is damage" |
| `235916/:61193` | `[84, 12]` | player E | "WTS EL Master of Whispers Tonic" |
| `183756/:58389` | `[4, 12]` then `[4, 3]` | player F | the same 130-unit services advert, sent to two channels, each copy split 121+remainder |

**The channel byte separates by content with zero exceptions**: every
free-conversation line is channel 3, every WTS/WTB advert is channel 12 —
assigned before any upstream enum was consulted (§5).

**And the operator's own lines come back from the server.** In the isle
captures the operator's ctrl-click target callouts arrive as `0x005D` template
bodies committed by `0x0061 [1, 11]` — 40 of the 47 — where playerId 1 is the
operator's own `0x0059` row in those solo instances. So the render path for
your own chat is a **server echo**, not a client-local print. (The callouts'
c2s trigger is not `0x0064`; `0x0064` appears exactly once live — §7.)

That is the cross-check `PLAN.md` §8.3 asked for: **body = `0x005D`'s coded
string; sender = the commit tag's id, resolved through the client's own player
table for `0x0061`, carried as an enc-name string for `0x005F`, and absent by
design for `0x005E`.**

## 4. `0x005E` — the server line, and what its word is

**[OBSERVED]** 133 sightings: word = **125 × the operator's own playerId**
(joined via `0x017D`'s literal name → `0x0059` row, across 16 connections and
four different characters), **7 × 0**, **1 × another player**. Zero unresolved.

The one other-player case is the reading's sharpest support: `143055/:60935`
`[51, 10]` with body `#1796 #13 #51 #1 #17` — template 1796 with **arg slot 13
= playerId 51** ("player G") and arg slot 1 = 17 — i.e. *"player G is now level
17!"*, the exact phrase family the isle probes rendered on our own client. So
the word is **the player the line is about** (usually you: your gold, your
items, your level), and 0 means no in-instance subject — all seven zeros are
district-wide announcements whose subject is a *literal name* in the body
(`#73531 #10 #2656 "<player name>"`; observed naming "player H",
"player J", "player K" ×3, "Ce L L", and once with three trailing
numeric args, "player M" — Hall-of-Heroes-broadcast-shaped,
UNVERIFIED which announcement template 73531 is, its record being encrypted).

**Arg slot 13 renders a playerId as a name** — witnessed twice in unrelated
templates (`#1796` above; `#1687 #13 #1` in §7). RECONSTRUCTION beyond those
two: the slot's general contract is unmeasured.

## 5. The channel byte — pinned from content, then corroborated

**[OBSERVED]** from line content alone, before consulting any upstream:

| channel | n (by tag) | evidence from the lines themselves |
|---|---|---|
| 3 | 3×`0x0061`, 1×`0x005F` | free conversation between strangers |
| 6 | 1×`0x005E` | the `/bow` translation, 51 ms after the typed `/bow` (§7) |
| 7 | 40×`0x005E` | terse bare-template repeats (`#1960`, `#1934`) during bench work and the merchant refusal step — warning-shaped |
| 10 | 92×`0x005E` | gold/item/XP/level notifications + the w=0 broadcasts |
| 11 | 40×`0x0061`, 43×`0x005F` | the operator's target callouts; the Master of Damage's reports; NPC tutorial callouts naming the character |
| 12 | 4×`0x0061` | WTS/WTB, nothing else, ever |
| 1 | 1×`0x005F` | one NPC line on the isle — **UNVERIFIED**, n=1 |

**[CORROBORATED]** GWCA's channel enum (`GWCA/Constants/Constants.h`,
consulted *after* the table above was fixed) assigns 3=ALL, 6=EMOTE, 7=WARNING,
10=GLOBAL, 11=GROUP, 12=TRADE, 1=ALLIES — agreement at every measured point.
UPSTREAM for every byte not in the table (0, 2, 4, 5, 8, 9, 13, 14).

## 6. `0x005F` — the agent line, reconciling `newopcodes`

**[OBSERVED]** 45 sightings (up from `newopcodes`' 7): the word is always an
agent id, every observed sender is an **NPC** agent (7, 9, 11, 12, 15, 17, 44,
100), and the 8-unit trailing string is the **sender's enc-name** — for the
Master of Damage (agent 100) it is the same two-varint coded name in all 18 of
its lines, and the body is the report template family the isle arc decoded
(`#49947`–`#49950`, including the `#1 #1496 #2 #73 #3 #20` end-of-combat report
`studies/isle/FINDINGS.md` §5 verified against our own summed damage). The
starter-zone lines (`180610/:53354`, agents 11/12) carry template bodies with
the operator's character name as a *literal* argument — an NPC addressing the
player by name, on channel 11.

The tag carrying its own name string is what makes the agent line
self-contained: `0x0061` resolves its sender through the player table, `0x005F`
ships the name with the message. The `NPC` discriminator in the name remains
what `newopcodes` said it was — every observed sender is an NPC, nothing on the
handler path says "NPC" — but the *commit-tag* role is now OBSERVED on 45.

## 7. The c2s half — `0x0064 CHAT_SEND`, and the one live exchange

**[OBSERVED]** `0x0064` appears **once** in all live traffic ever captured:
`20260818T132739/:53202` t=1122.037, `[100, '/bow']` — field 1 = agent 100, the
Master of Damage, the operator's target at that moment (consistent with the
loopback reading `overrides.json` already carries: target for slash commands,
0 for plain chat; loopback samples `[0, '!test']`, `[0, '!rurik two']`,
`[499, '/me waves']`).

**The reply is 51 ms later**: `0x005D` body `#1687 #13 #1` + `0x005E [1, 6]` —
a server-composed line on the **emote** channel whose template renders playerId
1's name (arg slot 13). The typed text `/bow` itself is never echoed. So slash
commands are **translated server-side**; plain chat is **echoed as typed**
(§3's verbatim lines are other players' sends arriving at our client — the
echo direction is measured on the operator's own callouts).

## 8. Names promoted, and what stays open

Promoted to `schema/overrides.json` (no `GAME_SMSG_` prefix, house convention;
GAME_SMSG named 96 → 100):

- `0x005D` **CHAT_MESSAGE_CORE** — high. Body-fragment carrier: mechanism from
  `smsgnames` (string-table append), commit-or-continue measured exceptionless
  on 227, render gating measured by the isle probe. The name's `CORE` suffix
  matches both upstream lineages (OpenTyria `opcodes.h`, GWCA `MessageCore`),
  which agree with a role we measured independently.
- `0x005E` **CHAT_MESSAGE_SERVER** — high. 133/133 words resolve as §4's
  subject-playerId-or-zero; sender is the system (no name renders in the tag).
- `0x005F` **CHAT_MESSAGE_NPC** — medium, kept from `newopcodes` (UPSTREAM
  discriminator, now with the commit-tag mechanism OBSERVED on 45 and every
  sender an NPC).
- `0x0061` **CHAT_MESSAGE_LOCAL** — high. 47/47 sender resolution, typed text
  verbatim, per-instance id space proven by the playerId-57 collision.

**Not promoted:** `0x0060` — zero sightings on any wire this repo holds. Its
shape (channel byte + 32-unit name + 6-unit tag string) and both upstreams read
"global/guild chat with an out-of-instance sender name", which solo sessions
can never produce. Catalogued; naming it would embed an unpinned purpose.

**Open, honestly:**

- Channel bytes 0/2/4/5/8/9/13/14 — UPSTREAM only, never observed.
- Template ids observed but unresolved (encrypted archive records): the
  gold/item family `#1735`–`#1742`, `#1796` (level-up), `#1687` (bow), `#1960`
  / `#1934` (warnings), `#73531`+`#2656` (broadcast + name wrapper), the
  All-chat body wrapper `#8`, the trade wrapper `#68606`. The ids are
  measurements; the texts are ArenaNet's and resolve at run time or not at all.
- Whether the client ALSO renders its own typed line locally before the echo —
  unmeasured (needs the staged loopback run; the callout evidence proves the
  echo path exists and renders, not that it is the only path).
- `0x005F` channel 1 (n=1) and the `0x0064` field-1 "target" reading (n=3
  typed, no counterexample) keep their existing labels.

## 9. What this changes for the server

`GAME_CMSG 0x0064` was `test_dispatch.py`'s loudest recorded drop ("REAL
MISSING WORK ... the whole chat and emote surface"). The echo it needs is now
specified entirely from measurements:

1. Body: `[#8, 0x0107] + text + [0x0001]` (the exact All-chat framing on 3 of 3
   observed channel-3 player lines), split at **121 units** per fragment.
2. One `0x005D` per fragment, then `0x0061 [PLAYER_NUMBER, 3]`.
3. Slash commands echo nothing except `/bow`, which sends the observed
   `#1687 #13 #playerId` on `0x005E [playerId, 6]` — the one command whose
   reply we hold. Every other command and sigil is printed and dropped,
   loudly, rather than guessed.

The name table the echo depends on (`0x0059` for playerId 1) is already sent
every session. Implementation: `toolkit/authsrv/chatdefs.py` + the dispatch arm
in `authsrv.py`; tests `toolkit/authsrv/test_chatdefs.py` (offline, the framing
and fragmentation against the captured bytes) and the dispatch coupling in
`test_dispatch.py`. The on-screen confirmation was staged as a runsheet for the
owner — the naming above did **not** wait on it, because the cross-check is
measured on ArenaNet's own traffic; the run verifies our *consumer*, not the
decode.

## 10. The loopback run — CONFIRMED 2026-08-20, all three arms as predicted

Operator-driven, `session.py --keep-open`, predictions on record before launch
(§9 / PLAN §8.3). Wire record `vault/captures/gamesrv/authsrv-20260820T001020-c1.jsonl`;
render verdicts are the operator's, per the fixed-position-UI boundary.

| typed | wire (verbatim from the capture) | screen |
|---|---|---|
| `!hello` (×2) | `CHAT_SEND [0, '!hello']` → CORE `5d000800` + `0108 0107 h e l l o 0001` + LOCAL `6100 0100 03` — the predicted 8 units and `[1, 3]`, byte-for-byte, both times | **`Test Warrior: hello` rendered** |
| `/bow` | `CHAT_SEND [0, '/bow']` → CORE `0797 010D 0101` (= `#1687 #13 #1`) + SERVER `5e00 0100 06` (= `[1, 6]`) | **the emote line rendered** (exact wording is template 1687's, ArenaNet's encrypted record — not transcribed) |
| `#test` | `CHAT_SEND [0, '#test']` arrived at t=59.674 and **nothing was sent after it** | **nothing rendered** — the control that makes the two positives mean something |

Three incidental measurements banked: the client renders **no local copy** of a
typed line (the `#test` silence proves the echo is the only render path, closing
§8's last open question); `/bow`'s field 1 was **0 with no target**, the fourth
sample consistent with the target-agent reading (live: 100 with the Master of
Damage targeted); and the double `!hello` shows the echo is stateless per send —
two identical arrivals, two identical echoes, two rendered lines.
