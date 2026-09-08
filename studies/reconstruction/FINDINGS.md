# Reconstructing systems we have no binary, assert or code access to

**What this is.** Drop tables, item generation, the economy, progression, world population
and the other server-authoritative systems have no client-side artifact to read. This
document is the result of asking what *creative* methods reach them anyway. Five census
agents measured the ground first; thirty-nine proposed techniques were then handed to six
adversarial lenses, one skeptic each, with a standing instruction to refute by measurement
rather than by argument. **Sixteen survived, twenty-three died, and only two survived
un-weakened.** Both of those two are about the PRNG, and one of them is a negative result.
A completeness critic then re-derived every load-bearing number and returned a punch list;
a six-agent revision pass measured each item rather than rewriting prose. **Three technique
classes the original pass missed entirely were added and are now among the strongest things
here** — the 332-opcode loopback stimulation sweep (§4.11), the identification and salvage
class (§4.16a–§4.18), and skills as a system (§2.9). The revision note at the end says what
was adversarially checked and what was not.

Combat AI is a parallel arc and is out of scope here; it appears only in clauses where a
technique transfers, and as row 28 of §2.8 so the census is complete.

**Provenance.** Everything below was measured in
`C:/gd/Rurik/.claude/worktrees/zealous-bartik-f3e60d` against the vault resolved by
`toolkit/vaultpath.py` (`C:\gd\Rurik\vault`, via the main working tree). No client was
launched, no socket opened, no live capture run, and nothing was written into the repo or
the vault — by the research pass, by the critic, or by the revision. Every number in §1, §2
and §6 was re-derived by this document's own readers, not copied from the agents that
reported it.

**Denominator.** Every count, percentage and ratio below is over **canon-12** unless the
sentence names another: the twelve decrypted game connections in
`vault/captures/live/` — every `game-*.jsonl` in all three keyed captures
(`20260807T133758`, `20260807T143055`, `20260810T235916`), each loaded with
`tape.load_tape` and framed **once** with `tape.decode_all`, never per event. That is
**22,524 GAME_SMSG / 398,945 B / 758.0 s / 155 distinct opcodes**, with **12 of 12
framing to `consumed == total`, `err is None`**, plus **971 GAME_CMSG / 18,318 B /
29 opcodes** on the same twelve connections. Two smaller readings appear in this
document's own sources and are named wherever a figure is quoted from them:

| reading | connections | GAME_SMSG | GAME_CMSG | `0x0161` | seconds | what it drops |
|---|---|---|---|---|---|---|
| `tape.chain()`, two big captures | 8 | 21,543 | — | 246 | 684.2 | each big capture's character-select connection, and the whole third capture |
| all `game-*.jsonl`, two big captures (**BIG-10**) | 10 | 22,137 | 919 | 340 | 702.4 | the whole third capture |
| all `game-*.jsonl`, all three keyed captures (**canon-12**) | **12** | **22,524** | **971** | **394** | **758.0** | — |

Client-side figures are read from the pinned pristine build
`vault/client/2026-07-29_221c13772c7a/Gw.exe`, which those captures' own `VERSION`
frames identify as **build 38797**. §1.1 is why this note exists.

**Labels** are `studies/character/FINDINGS.md`'s: OBSERVED, UPSTREAM, RECONSTRUCTION,
CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. Where a claim has an observed half and an
inferred half the label is split at the clause, not averaged.

---

## 0. The answer in one page

**§0 inherits the weakest label of what it summarises.** The draft of this document stated
three things flat that its own sections rate CONTESTED or UNVERIFIED; the critic caught all
three and they are carried here with their labels attached, because a one-page summary that
is more confident than its body is how a caveat dies.

**The instrument problem is solved and nobody noticed.** ArenaNet's own recorded traffic
already carries a kill→drop chain, end to end, from their server: a death is a sourced bit
(`CHAR_STATUS_DEAD 0x10` on `0x00F0`/`0x00F1`) **[OBSERVED]**; a hostile is a four-character
allegiance tag in `WORLD_CREATE_AGENT` field[12], carried as a little-endian dword — the
value is `0x6D6F6E31`, so **the wire bytes are `31 6E 6F 6D` and read in order they spell
`1nom`**; `mon1` is that value written MSB-first **[OBSERVED]**; the item record decodes to
model id, quantity and a modifier array **[OBSERVED]**; and the ground agent is created at
the corpse on the same timestamp **[OBSERVED]**. **One link in that chain is CONTESTED and
must not be quoted as settled: reading the drop's owner off `0x0168`'s second field holds in
2 of 7 occurrences and matches neither stated hypothesis in 5** (§4.7). The denominator is
free. **The numerator is the whole problem: 4 kills and 2 drops in 12.1 minutes of in-world
play** (726.7 s across the nine canon-12 connections whose `map_id` is not 0), of which only
**9.5 minutes** is explorable — **and a second five-minute session with a different character
three days later added exactly TWO new opcodes to a cumulative 155.**

**"No client-side access" is mostly false, and the census is now published rather than
asserted.** The draft said *"of eleven candidate systems, two are genuinely server-only"* and
listed none of them. §2.8 lists **28 systems** with a verdict and an evidence cell per row:
**3 are FULLY CLIENT-SIDE, 12 are HALF-MIRRORED, 13 are SERVER-ONLY.** The client holds the
entire vocabulary — `ITEM_ATTRIBUTES` = 559 weapon-mod names, `ITEM_DESCRIPTIONS` = 388
templates, `s_charCondition` = 9, `s_charDamage` = 14, `s_skill` = 3,443, `s_effect` = 2,077,
`ITEM_FORMULAS` = 1,501 crafting recipes — and it bounds-checks **90 distinct named `s_*`
tables** by name, not the seven §2.2 samples. The `Gw\Const\` tree is *shared*, not
Cli/Srv-split. **[CONTESTED, and the draft stated it flat]** that "every one of those tables
resolves to plain readable `Gw.dat` records today": `s_skill` resolves 3,440 of 3,443, and
`ITEM_FORMULAS` is not a string-id array at all — §2.4's probe read the wrong stride and its
CONTESTED verdict is retired here in favour of a measured 20-byte record layout, which is a
different and better answer. **[UNVERIFIED]** that the server links the same translation unit
as the client for any of it (§2.7); that is inference from the shared-tree layout and it must
sit at every call site.

**The frame that explains every verdict.** This repo has many strong oracles for PROTOCOL
and FORMAT claims and exactly three for SERVER-BEHAVIOUR claims. Drops, spawns and economy
are behaviour. So thirty-nine clever techniques all had to land on the smallest three
instruments, and twenty-three of them died there — most often to **their own stated null
control, executed for the first time.**

**The best case for the document's own thesis is skills, and the pass missed it.** `s_skill`
is 3,443 rows of 164 bytes and holds every number a caster needs; the server owns which and
when and states almost none of it. §2.9 measures the whole lifecycle at **26 messages over
22,524** — and inside it, the first client-side skill constant ever checked against
ArenaNet's own server: **exactly 1 of the 41 dword columns** of the skill record reproduces
the recharge values their `0x00E5` sent, and it is `+0x4C`, where GWCA independently declares
`recharge`. One hit out of forty-one is what makes that a measurement.

**The single highest-leverage act is now two acts, in order.** First, at **zero human
minutes**: the loopback stimulation sweep (§4.11) — send each of the 332 catalogued
GAME_SMSG opcodes ArenaNet has never shown us to our own client on loopback and record what
happens. 66 minutes of *agent* time, both endpoints ours, no live service at any point, and
the deliverable is a 332-row opcode→effect map for a third of the catalogue. Second, and it
is still the only act that costs human minutes: **one ~30-minute session** with a merchant,
an identification kit and a salvage kit. Our live corpus contains ZERO merchant, trader,
quote, price or transaction messages across 22,524 server messages, and **zero of the 19 c2s
and 17 s2c item-manipulation opcodes** the client carries code for. One person opening one
merchant window and clicking one ID kit converts GWW's 507 "in exchange for" articles, the
Pre-Searing manifest's trophy table and 1,498 crafting rows from unusable to corroborating —
and settles whether every drop record in the vault is complete or censored. **The operator
plays; the driver sends no keystrokes and no clicks.**

**And a ladder row moved without anyone doing the work.** Absolute monster max health —
item 1 of `PLAN.md` §1.7's four "genuinely server-only" things, which `R4c-2` still reports
as blocked — has been sitting in the vault in the clear since 2026-08-07, and **the
definition slot is a stable server-side key across sessions.** That last claim was refuted
by one of this pass's own skeptics; the refutation rested on a mis-decode, and §6 shows the
bytes.

---

## 1. The corpus, measured — and the reader idiom that decides its size

### Three corpus sizes are all correct, and they differ by 37.6% on the item records

**[OBSERVED] 1.1** Three readers of the same vault reported three different corpora. All
three are right; the difference is which channel files the reader opens. The table is in
the front matter and is the document's denominator declaration.

The arithmetic closes exactly. `chain()` drops the login/character-select connection of each
big capture — `:63158` and `:61190`, 297 messages and 47 item records each — and the third
keyed capture `20260807T133758` adds 387 messages and 54 records. Verified twice in this
tree by two readers that share no code: 12 connections, 22,524 GAME_SMSG, 398,945 bytes,
758.0 s, 155 distinct opcodes, 394 `0x0161`, 1,068 `WORLD_CREATE_AGENT`, 7 `0x0168`,
2 `0x0135`, 17 `0x00EE`, and **12 of 12 framing to `consumed == total` with `err is None`.**

**This is not pedantry.** `tape.chain()` is the idiom every proposal reached for, and it
loses **148 of 394 item records — 37.6%** — precisely the records an item-generation
statistic is computed over. `chain()` is correct for *route* questions (it refuses a link
the next connection's own `VERSION` frame does not confirm, 12 fields across 3 transitions)
and wrong for *inventory* questions.

**So this document fixes one denominator and uses it everywhere: canon-12.** Three rules
follow, and each is checkable rather than exhortative.

1. **Never mix a numerator from one idiom with a denominator from another.** This is not
   hypothetical: the draft of this document read *"22,524 of 22,524 … Today 127 fail"* —
   canon-12's denominator against BIG-10's numerator — in an **acceptance criterion**.
   On canon-12 it is **133**.
2. **State the denominator inline.** Not "5.51%" but "5.51% of canon-12"; not "10 of 10
   connections" but "12 of 12"; not "17 identifiers" but "17 on chain-8, 18 on canon-12".
3. **When a figure survives a change of denominator, say that too** — it is the
   difference between a property of ArenaNet's traffic and an artifact of our reader.
   Identical on all three idioms: `0x0020` = 1,068, `0x0168` = 7, `0x0135` = 2, `0x00EE`
   = 17, `0x0056` = 126 with 71 at t ≤ 1.0 s, 233 `mon1` creates → 76 distinct agent ids,
   4 deaths, 2 drops, 0 uncatalogued opcodes live.
   **Not** identical: `0x013F` 72 / 90 / **108**, item records 246 / 340 / **394**,
   modifier words 598 / 858 / **990**, modifier identifiers 17 / 18 / **18**, and
   catalogued-never-seen 339 / 332 / **332** — which the draft listed as identical on all
   three, because it never measured chain-8's distinct-opcode count (148, not 155). §5.1's
   Chao1 entry has been carrying the correct chain-8 figure, "a truth of 339", all along.

### The capture that is mourned, the one that was recovered, and the four that were not

**[OBSERVED] 1.2** Six live capture directories exist, not two, and **only two of the six
worked at the time they were run.** `20260807T124912` is the first live capture ever taken
and it is the one the ladder still mourns: 7 connections, 20.0 minutes, 259,228 B of
reassembled TCP payload, of which **255,102 B is game-channel ciphertext that no key on this
machine will ever open** (c2s 29,638 B, s2c 225,464 B). The draft's "1.74 MB wire log" is the
size of `wire.jsonl` as JSON with hex-encoded payloads — 6.71× the bytes it carries. Two
things about this capture were reported wrong in opposite directions and both are settled
here from the artifact.

*It is not "no game key".* `manifest.json` records `"keys_tapped": 7`. One of those seven —
the auth channel's — is on disk inside the decrypted `auth-*.jsonl` and opens its connection
today. **The other six were held in memory and died when the process exited**, which is why
this is the only capture of the six with no `keyring.jsonl`. `KeyRing._persist`'s docstring
is the confession, written the same afternoon.

*And it is not a sniffer that attached mid-stream.* Today's `livesession.split_c2s` opens
**7 of 7** of that capture's connections: every c2s stream begins at byte 0 with a valid
VERSION header (one `0x000C0400` auth, six `0x000C0500` game), CLIENT_SEED `0x4200` follows
at the shape's own offset, every s2c stream begins with SERVER_SEED `0x1601`, and reassembly
reports **zero gaps on all 14 streams**. A mid-stream attach fails all four tests. The
recorded per-connection `why` — *"c2s does not start with VERSION (got header 0x000c0500)"* —
is verbatim the error text of the **old** `split_c2s`, which knew only the auth shape;
`0x000C0500` *is* the game VERSION header, and it was named **from this capture** thirty-eight
minutes of commit history later (`4e16dec`, 2026-08-07 13:27: *"it is why the first run split
1 of 7"*). The defect was in the decoder, not in the instrument. The instrument was perfect
and the vault holds its output intact.

**[OBSERVED] 1.2a The ciphertext is not recoverable, and the reason is not the one usually
given.** There is no keystream-offset problem: the DH handshake is plaintext at the head of
every stream, so the ciphertext starts at a known boundary and ARC4 begins at position 0.
What is gone is the key — 20 bytes, **2^160 = 1.46e48 candidates**, 4.6e31 years at 10^9
trials/s and 4.6e22 years at 10^18, and the framing-as-wrong-key-detector this document
cites elsewhere is a per-trial oracle, not a shortcut. `master_secret = server_seed XOR
(A^b mod p)[:20]`, so the only route that is not arithmetically closed is the **512-bit
`g=4` DH group** the client carries — and attacking ArenaNet's key exchange is a different
act from reading our own client's memory, an owner question rather than a technique. The one
genuine cryptanalytic opening is smaller than it sounds and was measured: both directions run
ARC4 from position 0 under the **same** key (verified on ArenaNet's own bytes — `ks_c2s ==
ks_s2c == ARC4(key)` on **15 of 15** decrypted channels), so each connection is a two-time
pad. Its ceiling is **13.1%** of the game s2c ciphertext (29,638 B of c2s to drag against
225,464 B of s2c) and its crib is **2 to 4 bytes**: across the 12 keyed game c2s streams the
common prefix within each first-opcode group is 2 B (`0x800a`, n=3) and 4 B (`0x8091`, n=9),
and 0 B across all twelve. **Retire the recovery item.**

**[OBSERVED] 1.2b And "roughly double the corpus" does not survive.** Fully recovered, those
six connections add 225,464 B to the canonical corpus's 398,945 B of s2c plaintext —
**+56.5% (×1.565)**, an estimated ~12,700 further GAME_SMSG at the corpus's own 17.71
B/message **[RECONSTRUCTION, for the message estimate]**. What the estimate *did* miss is
larger and points the other way: the c2s side would go 18,318 → 47,956 B, **×2.62**, on the
oracle §3.1 calls two orders of magnitude smaller than O1. That is a design input for §10
rather than a lament — **c2s volume tracks wall clock and s2c volume tracks what happens.**
124912's long connection ran 24.5 B/s of c2s against the corpus's 24.2, while its s2c ran
103.7 B/s against the corpus's 526.3. A long quiet session is cheap s2c and full-price c2s.

**[OBSERVED] 1.2c The live-capture procedure's actual success rate — nobody had written this
down.** Six authorized live runs exist. Two worked as run, one was recovered offline from its
own persisted keyring, one is permanently part-lost, and two recorded no ciphertext at all.
Every failure had a *different* cause, and each fix shipped within about twenty minutes of
the run that exposed it — which is the honest reading of the table: this is a procedure that
was debugged **by spending authorized live sessions**, and there are four such expenditures
in it.

| capture | span | conns (auth+game) | keys tapped | keyring on disk | wire payload | decrypted then | decrypted now | GAME_SMSG | what happened |
|---|---|---|---|---|---|---|---|---|---|
| `20260807T124912` | 20.0 min | 7 (1+6) | 7 | **no** | 259,228 B | 1/7 | **1/7** | 0 | Assembler knew ONE VERSION shape, so the six game connections were refused at the split and **no key was ever tried against them**; the keyring was in memory, so six keys died at exit. **Permanent.** Fixed by `4e16dec` (both halves). |
| `20260807T133758` | 1.1 min | 3 (1+2) | 3 | yes | 11,280 B | 1/3 | **3/3** | 387 | VERSION shapes now known; the **key criterion** was still a literal opcode list taken from our own loopback server, and the real service opened on `0x800a`/`0x8091`. Recorded reason: *"none of the 3 tapped key(s) decrypt this connection to a known first opcode."* **Recovered** by `--assemble` after `db0980e`. |
| `20260807T135532` | — | 0 | 9 | yes | 0 B | — | — | 0 | `wirecapture.py` died on a `KeyboardInterrupt`; `wire.jsonl` is 260 B of header and no manifest was ever written. Nine keys, nothing to decrypt. |
| `20260807T141736` | — | 0 | 6 | yes | 0 B | 0/0 | 0/0 | 0 | `LIVE_PORTS` was `6111–6601`; the watchdog logged **ZERO packets for 255 s** while the client's own connection sampler named `:80`. This is the run that diagnosed port 80 (`2ccdb90`). |
| `20260807T143055` | 6.9 min | 6 (1+5) | 6 | yes | 201,017 B | **6/6** | 6/6 | 11,241 | Clean. |
| `20260810T235916` | 5.1 min | 6 (1+5) | 6 | yes | 212,006 B | **6/6** | 6/6 | 10,896 | Clean, and the first manifest carrying `wire_sha256` / `keyring_sha256` / `pruned_records`. |

**15 of the 25 GW connections ever captured are readable, and 12 of those 15 are the
canonical corpus.** Two lessons the table carries that no single row does. First,
**`keys_tapped` is not a success indicator** — 15 keys sit in the vault against zero
ciphertext, and reading `keys_tapped: 7` as evidence that nothing was lost is the specific
mistake this table exists to prevent. Second, **the recoverable failures were recoverable
because the keyring was on disk**; that is the entire difference between row 1 and row 2,
and rows 3–6 all inherit it. §10's pre-flight is derived from this table line by line.

### What is in it

**[OBSERVED] 1.3** Server outtalks client **23.2:1 by message and 21.8:1 by byte**
(22,524 vs 971; 398,945 B vs 18,318 B over all twelve connections). The byte ratio is 21.8:1
on BIG-10 as well, so that one is a property of the traffic; the message ratio is not. One
opcode is **30.76%** of all server traffic (`WORLD_SIMULATION_TICK 0x001E`, 6,928 — the count
is unchanged across denominators because `0x001E` does not occur outside the two big
captures, so only the denominator moved). The top four are **49.88%**: `0x001E` 6,928,
`0x0029` 1,997, `0x009F` 1,242, `0x0020` 1,068 = 11,235 of 22,524.

**[OBSERVED] 1.4** Naming coverage. 21 of 155 live GAME_SMSG opcodes are named (13.5% of
opcodes, **69.67% of volume**) — **unnamed volume is 30.33%**. 15 of 29 live GAME_CMSG
opcodes are named — unnamed volume **20.08% of 971**, and `0x003D MOVE_SET_HEADING` alone is
430 = **44.3%** of the client's traffic, not "half". **332 catalogued GAME_SMSG opcodes have
never been seen from ArenaNet** (487 catalogued − 155 live), and **zero live opcodes are
absent from the catalogue**, so a zero in this corpus is a real zero rather than a decode gap
**[CORROBORATED — the difference was taken in both directions]**. One named c2s opcode,
`0x0064 CHAT_SEND`, appears **zero** times across all twelve connections and all three
captures: its name came entirely from loopback labelled runs and ArenaNet's own traffic has
never corroborated it.

**[OBSERVED] 1.5** The kill ledger, re-derived here. Six status words carry
`CHAR_STATUS_DEAD 0x10`; **four are distinct first deaths**, one is a repeat status word
(`0x14` on agent 38, 4.3 s later) and one is a create-with-dead (agent 43 re-created as a
corpse 43 s after dying). All four dying agents carry `mon1`, `f3=1` (living), `f4=9`
(NPC) — a check that could have failed, since `nonc`, `anim`, `band` and `play` agents are
in the same instances and none of them died.

```
143055 :64103 t= 23.511  agent  40  f2=0x20000542 slot 1346  'mon1'   no drop
143055 :62994 t= 19.912  agent  38  f2=0x2000059a slot 1434  'mon1'   DROP
235916 :61624 t= 36.330  agent  43  f2=0x2000059a slot 1434  'mon1'   DROP
235916 :49163 t= 23.202  agent 278  f2=0x200005a2 slot 1442  'mon1'   no drop
```

**Both drops came from the same definition slot, in two sessions three days apart, on two
different characters.** So the corpus does not give one species two independent trials of a
*rate*; it gives one species two independent trials of *membership*.

Traced create-by-create, each dying agent's own history holds: agent 40 created `mon1` slot
1346 at t=0.722; agent 38 created `mon1` slot 1434 at t=0.629; agent 43 created `mon1` slot
1434 at t=18.579; agent 278 created `mon1` slot 1442 at t=17.985, and created and removed
three times before it dies. Two smaller facts belong beside them: agent 43's create-with-dead
at t=79.186 carries `f4=8`, not 9 — the single `mon1 f3=1 f4=8` row in the whole corpus —
and **agent id 38 on `:62994` is REMOVED at t=47.514 and the id is REUSED at t=74.779 for an
`anim` agent (slot 1343)**, so a reader that maps agent id → class tag without a time window
reads the drop-producing kill as `anim`. That is not hypothetical; it happened on a fixer's
first pass. It is §8.2's control (c).

**[OBSERVED] 1.5a The allegiance tag, spelled the way a grepper needs it, and its full
vocabulary.** `WORLD_CREATE_AGENT` field[12] is a little-endian dword. To find one in a
capture, search for the **byte sequence** or for the dword — **never for the readable text**,
which appears nowhere on the wire. The trap runs both ways: the ASCII text `play` occurs 39
times inside the pinned client while the dword `0x706C6179`'s byte sequence occurs **zero**
times there, so a text grep and a dword grep are different searches and neither finds a wire
tag by its spelling.

| dword | wire bytes | bytes in order | value MSB-first | n | agent ids | maps | definition slots |
|---|---|---|---|---|---|---|---|
| `0x706C6179` | `79 61 6C 70` | `yalp` | `play` | 405 | 161 | 148, 146, 164 | 90 |
| `0x6E6F6E63` | `63 6E 6F 6E` | `cnon` | `nonc` | 244 | 117 | 148, 146, 164 | 30 |
| `0x6D6F6E31` | `31 6E 6F 6D` | `1nom` | `mon1` | 233 | 76 | **146 only** | 5 (1346, 1431, 1432, 1434, 1442) |
| `0x62616E64` | `64 6E 61 62` | `dnab` | `band` | **37** | 23 | **146 only** | 2 (1420, 1421) |
| `0x616E696D` | `6D 69 6E 61` | `mina` | `anim` | 32 | 24 | **146 only** | 1 (1343) |
| `0x00000000` | `00 00 00 00` | — | — | 117 | 77 | 148, 146, 164 | 25 |

1,068 creates, canon-12. The vocabulary is **five non-zero values plus a zero that is not an
allegiance at all** — the draft named four, and the critic's `band` count of 4 was one
connection's share of 37. What each appears to be, labelled separately from the counts:

- **`play` — other players. [OBSERVED]** 336 of 405 are in the crowded outpost (map 148),
  and it is the only tag whose `field[2]` carries top nibble 3, the player class base, in
  366 of 405 creates.
- **`nonc` — non-combatant. [CORROBORATED]** It is one of only two allegiance-shaped dword
  constants in the pinned client (`nonc` twice, `nonn` once, and nothing else), which is
  `agents.py`'s standing claim re-checked here against build 38797.
- **`mon1` — hostile. [OBSERVED]** All four first deaths in the corpus are `mon1` agents,
  and all **17** `ATTACK` (`0x0026`) messages the client sent name agent ids that were
  created `mon1`.
- **`band` and `anim` — counts OBSERVED, meaning UNVERIFIED.** Both are map-146-only, both
  carry the living-NPC shape `field[3]=1, field[4]=9` exactly as `nonc` and `mon1` do, both
  occupy one or two definition slots, **neither ever died and neither was ever the target of
  an `ATTACK`**, and **neither dword appears anywhere in the pinned client** — 0 occurrences
  of either byte sequence. Do not read the letters into a meaning: `band` could be bandit,
  banded, or a team label, and nothing measured here distinguishes them.
- **Zero is not a neutral allegiance. [OBSERVED]** The 117 zero-tag creates carry
  `field[3]/field[4]` of (2,1) in 94, (4,0) in 12 — the ground items — and (3,0) in 11, and
  **not one is `field[3]==1`**. The tag is a field of *living* agents; a reader that treats
  zero as an allegiance value is reading a field that was never written.

**[OBSERVED] 1.6** Denominators must be distinct agent ids, not creates. 233 `mon1` creates
resolve to **76 distinct** agent ids across four explorable connections (`:64103` 142/15,
`:62994` 24/19, `:61624` 32/22, `:49163` 35/20); one connection alone is 142 creates of 15
agents, which `studies/tape` and `test_burrow.py` already identify as the worm burrow cycle
on that exact tape. A drop rate built on create counts would be 3× too generous. This figure
is identical on all three denominators.

**[OBSERVED] 1.7** Rates from ordinary human play, each naming the map class it is over:
**explorable (map 146, four connections) 1,109 s2c msgs/min and 17.1 KiB/min over 568.2 s**;
**outposts (maps 148 and 164, five connections) 4,212 msgs/min and 79.6 KiB/min over 158.5 s**
— a crowd artifact, not a steady state. The draft's outpost figure of 5,712 msgs/min over
116.0 s was four of the five outpost connections: it missed `20260807T133758 :54560`, which
`tape.client_version` reports as **map 148**, carrying 88 messages / 3,629 B in 42.5 s, and
that one quiet connection moves the outpost rate by 26%. **26.3% of all messages (5,931 of
22,524) arrive in the first 2 s of an instance load** — a figure that rises monotonically
with the denominator (24.1% chain-8, 25.5% BIG-10) because the connections the smaller idioms
drop are almost entirely load burst. Extrapolated from map 146: **~66,529 messages and
~1.00 MiB of server plaintext per hour, ~25.3 kills, ~12.7 drops**, and **zero items entering
a bag from loot** — §10.4 counts the inventory placements exactly and finds 109 `ITEM_MOVED`
of which not one is a picked-up drop.

Map assignment for all twelve, from the client's own c2s VERSION frame rather than from
`chain()`'s residue: **map 0** = `:54557`, `:63158`, `:61190` (character select, and all
three carry the same `world_id` 3775786921 across three days); **map 148** = `:54560`,
`:60935`, `:61193`; **map 164** = `:64102`, `:49160`; **map 146** = `:64103`, `:62994`,
`:61624`, `:49163`.

### The number that should design every campaign

**[OBSERVED] 1.8 Opcode discovery saturates almost immediately.** Cumulative distinct
GAME_SMSG on the BIG-10 route: 39 after character select (0.15 min), 134 after the first
outpost (0.96 min), **150** after the first explorable (4.06 min), 153 by the end of session
one (6.76 min), reaching 155 at 11.71 min. The draft's 149 is not reproducible from any
idiom that exists: `decode_all` gives 150 at that point and the defective per-event idiom
gives 143. On the canonical route — which puts `20260807T133758` **first**, because it is
chronologically earlier — the curve is 39 / 52 / 52 / 134 / 150 / 153 / 153 / 153 / 153 /
154 / 155 / 155, saturating at 12.48 min of 12.63.

The conclusion is unchanged and **much** stronger than the draft's, because the draft had the
third capture's contribution wrong in the direction that understated the result. Measured
per capture rather than along the cumulative curve: `20260807T143055` alone carries **153**
distinct GAME_SMSG, `20260810T235916` alone carries **153**, their union is **155**, and
`20260807T133758` — 52 distinct over 387 messages and 2 connections — adds **ZERO** over that
union. So: **the entire second session, different character and different profession on the
same route, adds two opcodes, and the entire third capture — chronologically the FIRST of the
three — adds nothing at all that the other two lack.** (The draft's "adds thirteen" was
`:54560`'s within-capture increment over `:54557`, i.e. a step inside the cumulative curve,
mislabelled as the capture's marginal contribution. It is the same denominator slip §1.1
makes a rule about, arriving as a *numerator* this time.) More hours of the same content buy
nothing. Only new content buys anything. That single curve is why every "grind for n" design
in §5 is refused twice over: by policy, and by the data.

### Every figure that moved when the denominator was fixed

**[OBSERVED] 1.9** Re-derived by one reader over all three corpora. **The BIG-10 column
reproduces the draft to the digit**, which is the control that says the reader is measuring
the same thing the draft measured and that the only difference is the denominator.

| § | claim | chain-8 | BIG-10 (as drafted) | **canon-12 (use this)** |
|---|---|---|---|---|
| 1.3 | `0x001E` share of s2c | 32.16% | 31.30% | **30.76%** (6,928) |
| 1.3 | top four opcodes | 52.05% | 50.70% | **49.88%** (11,235) |
| 1.3 | s2c : c2s by message | — | 24.1 : 1 | **23.2 : 1** (22,524 : 971) |
| 1.3 | s2c : c2s by byte | — | 21.8 : 1 | **21.8 : 1** (398,945 : 18,318) |
| 1.4 | unnamed GAME_SMSG volume | 27.44% | 29.27% | **30.33%** |
| 1.4 | unnamed GAME_CMSG volume | — | 20.13% | **20.08%** of 971 |
| 1.4 | catalogued never seen | 339 (487 − 148) | 332 (487 − 155) | **332** (487 − 155) |
| 1.7 | outpost rate | — | 5,712 msg/min, 106.9 KiB/min, 116.0 s | **4,212 msg/min, 79.6 KiB/min, 158.5 s** |
| 1.7 | first-2 s share of all messages | 24.1% | 25.5% | **26.3%** (5,931) |
| 1.8 | distinct opcodes after the first explorable | 143 | 149 (not reproducible; `decode_all` gives 150) | **150** at 4.06 min |
| 3.1 | O2 corpus size | — | 919, "half" one opcode | **971**, `0x003D` = 430 = **44.3%** |
| 4.13 | `ITEM_CREATE_BAG` rows | 72 | 90, "9 on 10 of 10" | **108, 9 on 12 of 12** |
| 4.15 | `0x009F` share | 5.67% | 5.56% | **5.51%** (1,242) |
| 4.15 | naming `0x009F` lands unnamed at | 21.77% | 23.71% | **24.82%** |
| 4.15 | agents named by `0x009F` | 203 | 204 | **209** (21 kinds, unchanged) |
| 4.5 | modifier identifiers | 17 | 18 | **18**; `0xA0F8` n=20→**110** |
| 5.1 | s2c wire segments | 5,728 | 5,756 | **5,786** over 12 connections |
| 5.2 | `0xA488` words | 151 | 163 | **170** |
| 6.2 / 8.1 | round-trip failures | 117 / 21,543 | 127 / 22,137 | **133 / 22,524** |

Unchanged in every column, and therefore properties of the traffic rather than of the
reader: `0x0161` within 2.0 s = **231 of 394 (58.6%)**, `0x0056` = 126 with 71 at
t ≤ 1.0 s, `0x0020` = 1,068, 233 `mon1` creates → 76 ids, explorable rate 1,109 msg/min
and 17.1 KiB/min over 568.2 s of map 146, and the extrapolations that ride on it
(~66,500 messages/h, ~1.00 MiB/h, ~25 kills/h, ~13 drops/h).

**And the four session-duration figures are all arithmetically right and all measure
different things** — only §0's was on an unstated denominator:

| figure | seconds | minutes | what it actually measures |
|---|---|---|---|
| §1.1 | 758.0 | 12.63 | all twelve canon-12 connections |
| §1.8 | 702.4 | 11.71 | the ten BIG-10 connections, character-select included |
| §0 (as drafted) | 684.2 | 11.40 | the eight BIG-10 connections with `map_id != 0` |
| **§0 (corrected)** | **726.7** | **12.11** | the nine canon-12 connections with `map_id != 0` |
| §1.7 explorable | 568.2 | 9.47 | the four `map_id == 146` connections |
| §1.7 outpost (as drafted) | 116.0 | 1.93 | four of the five outposts — misses `:54560`, map 148 |
| **§1.7 outpost (corrected)** | **158.5** | **2.64** | all five `map_id ∈ {148, 164}` connections |

The arithmetic closes twice: **758.0 = 702.4 + 55.6** (the third capture) and
**758.0 = 568.2 + 158.5 + 31.3** (explorable + outpost + character-select).

---

## 2. The premise test: most of this is *not* server-only

**[OBSERVED] 2.1** The client carries shared Cli/Srv struct definitions with the server half
nulled out — `ItCliAgent:37 !serverData` @0x0084d03b, `CiCliAgent:36 !serverData` @0x0082893b.
`Gw\Const\` (37 files), `Base\` (79), `Engine\` (297) and `Net\` (18) have **no** Cli/Srv
split. 855 modules carry readable asserts in build 38797.

**[OBSERVED] 2.2** Compiled constant tables, sizes read from ArenaNet's own bounds checks.
This is a *sample*, not a census: §2.9.4 measures that the client bounds-checks **90 distinct
named `s_*` tables** (142 distinct `arrsize(...)` operands over 140 assert sites), and six
that this document needs are listed there rather than here.

| table | count | assert | resolves to plain `Gw.dat` text |
|---|---|---|---|
| `ITEM_ATTRIBUTES` (weapon prefix/suffix vocabulary) | 559 | `ConstItem:9119` @0x005A8FE7 | 559/559 |
| `ITEM_DESCRIPTIONS` (templates with `%num1%`) | 388 | `ConstItem:9125` @0x005A90E7 | 388/388 |
| `ITEM_FORMULAS` | 1501 | `ConstItem:9131` @0x005A9147 | not a string-id array — see 2.4 |
| `s_skill` (3,443 × 164 B @0x00988ED0) | 3443 | `ConstSkill:3833` | 3,440/3,443 |
| `s_charCondition` / `s_charDamage` | 9 / 14 | `ConstChar:1135/1158` | full |
| `s_charKind` / `s_charKindSlaying` | 12 / 12 | `ConstChar` | full |
| `s_titleClientData` / `s_heroClientData` | 48 / 40 | `ConstTitle:81` / `ConstHero:150` | full |

The prediction was stated first, from `studies/textrec` §4 — a string id reached by a bare id
from a PE table carries no RC4 key pair and must take the verbatim path — and it held, with
a control that scores zero (a non-table `.rdata` run: 0 of 64 decode to text) and a second
control that is honest about the method's limit (40 uniform-random ids in the same numeric
range: 9/40 decode to real but unrelated text). **Resolvability is cheap; one-semantic-family
coherence is the evidence.** The nine `s_charCondition` ids resolve through `Gw.dat` to GW's
nine conditions exactly — a check that could have failed on any one of them.

**[OBSERVED] 2.3** Merchant/trader/collector/crafter UI is entirely client-side — 30
`Vendor\Vn*.cpp` modules, **298 assert sites** (the draft's 345 was an over-count; largest
first: `VnUnlockItem` 32, `VnCraft` 23, `VnTradeBuy` 18, `VnTradeSell` 17, `VnGuildRegister`
16), exactly 14 named `CHAR_TRANSACTION_*` enum members (BUY, SELL, CRAFT, COLLECT,
CUSTOMIZE, LEARN_SKILL, TRADE_BUY, TRADE_SELL, UNLOCK_ITEM, UNLOCK_SKILL, GUILD_ADD_SERVICE,
GUILD_ADJUST_FACTION, GUILD_REGISTER, GUILD_TABARD), and a client-side affordability check
`VnGuildAddService:969 gold <= ItemCliGetGold()`. **Only the prices are server-side, and the
client's own text says so.** The gold/platinum conversion rule is a text record, not a server
field.

**[OBSERVED] 2.4 `ITEM_FORMULAS` — the draft's CONTESTED verdict is retired, and the reason
is a wrong stride.** The draft reported reading 1,501 consecutive **dwords** at `0xA2AFF8` as
string ids and getting PLAIN 815 / ENCRYPTED 85 / not-a-record 601, and concluded the layout
was NOT ESTABLISHED. The accessor says why: `ConstItem:9131`'s body is
`lea eax,[esi+esi*4]; lea eax,[eax*4 + 0xa2aff8]` — **20-byte records, returning a pointer**,
not a dword. Read at the right stride, `ITEM_FORMULAS` is 1,501 × 20 B = 30,020 B: `dword[0]`
is a float in 3.0..100000.0 (299 distinct), `dword[1]` an integer 1..15000 (22 distinct),
`dword[2]` sparse (20 non-zero, max 15), `dword[3]` a 1..4 enum, and `dword[4]` a strictly
ascending pointer into the contiguous 45,744-byte block immediately below the table,
`[0x00A1FB48, 0x00A2AFF8)`, with 1,501 distinct values. The consumer is named by ArenaNet's
own asserts: `VnCraft:144`, `:1035`, `:1094`, `:1209` all read `formula != ITEM_FORMULAS`,
and `VnCraft:124 elemCost`. **So the crafting recipe table is compiled into the client.**
§4.18 adds a second, independent witness for the 1,501 bound from the salvage path
(`InvSalvage` compares a per-item u16 at `item+0x48` against `0x5DD` as its "no formula"
sentinel), which is why the bound is **CORROBORATED** rather than measured-from-one-immediate.
The element *semantics* remain unnamed; the layout does not.

*(The draft's probe is kept above rather than deleted. It was a correct measurement of the
wrong thing, and the reason it was believed — a `cmp` immediate with no stride beside it —
is the transferable part.)*

**[OBSERVED] 2.5** The payoff negative holds. Across **19,758** readable assert expressions,
a grep for `rand|seed|roll|chance|weight|spawn|drop|loot|chest|treasure|reward|encounter`
returns **44 sites** — `asserts.py --grep` compiles with `re.I`, and the same pattern run
case-sensitively returns **29**; the draft's 21 is neither, and re-running the tool is what
found that. **The conclusion is unchanged by the correction**, because every one of the extra
hits is a substring collision: `cont`**`roll`**`ed` (13), `sc`**`roll`** and `scroll*` (6),
**`drop`**`list` (9), **`Encounter`**`ed draw command` (2), **`reward`**`sFrameId` /
`REWARD_POINTS_STYLE_*` (5), plus `BigNum:949 `**`seed`**` != this` and `SndMain:1301
`**`roll`**`off <= 10`. **Three are game logic** — `VnCollect:441 trophyHasLootDef`,
`GmQuestComplete:246` and `GmQuestComplete:242` — and the two `GmQuestComplete` sites contain
a lowercase `reward`, so they survive both runs; **`trophyHasLootDef` is the one hit reachable
only through the case-insensitive run**, which is why the case-sensitive 29 finds two of the
three and not three. So **44 is the number this negative rests on**, and quoting 29 would drop
`trophyHasLootDef`, the single most loot-shaped expression in the client. *(An earlier fix
pass wrote "two of those three"; measured, it is one — the arithmetic that matters is 3 at
`re.I` against 2 case-sensitive.)* The rest are graphics, audio, crypto and a UI
droplist. And `Gw.dat`'s 19 shipped chunk kinds across all 349 maps (Bloated and Stripped,
8,047 chunks each, 698 rows, 26 distinct `(slot, kind)` pairs) contain **no** NPC, spawn,
encounter, loot or population chunk. The client even knows a server map exists and refuses to
build one — `MapData:395 Client cannot create server maps`, type-2 manifest = 9 chunks.

**The same census carries a positive result the draft did not use.** The 19 slots include
**Environment (0x09) in 698 of 698 rows, Light (0x0F) 698/698, Sound (0x12) 698/698, Shore
698/698**, plus CubeMap 414, VisData 470, Occluders 234 and PathEngine 2. So weather, sky,
lighting and ambience are per-map client data present in **every** map — a whole system
settled for free (§2.8 row 17), and the absence result stands only for NPC / spawn /
encounter / loot / population, which have no slot at all.

**Every "NOT FOUND" above is a floor, and `asserts.py` says so itself:** 19,758 expressions
read against 20,131 `call rel32` sites found by an independent sweep, so **373** assert call
sites (3 named-but-unreadable plus ~370 more) are unreadable to a fixed byte pattern. An
absence from an admittedly incomplete scan is UNVERIFIED, not NOT FOUND.

**2.6 But the server's PRNG is not gone.** `P:\Code\Base\Rtl\Random.cpp` is in the SHARED
tree. **[OBSERVED]** the constants at four distinct `.text` sites: multipliers `0x9069` =
36969 and `0x4650` = 18000, zero-guard seeds `0x159A55E5` = 362436069 and `0x1F123BB5` =
521288629; **[OBSERVED]** the range helper's shape `lo + (x % (hi-lo))`; **[OBSERVED]** that
disassembling the whole enclosing function finds **zero backward branches**. Two readers found
the constants independently, the second by a pure-stdlib PE walk sharing no code with the
first. **[CORROBORATED against UPSTREAM]** the identification as Marsaglia MWC1616 — all four
are Marsaglia's published constants, and the naming is the upstream's, not a fact we measured.
**[RECONSTRUCTION]** the conclusions that follow: that the generator is therefore
modulo-biased with no rejection loop *as the server uses it*, and that the entry at
`0x0046D1F0` is *the* server RNG rather than one member of a family. The constants appear at
four sites, so the entry must be tied to a caller before it is called that.

**[UNVERIFIED] 2.7** That the *server* linked this same translation unit is inference from the
shared-tree layout, not measurement. `Base\Os\Win32\Exe\ExeHeapCliRelease.cpp` is a known
per-target specialization inside `Base\` itself. This caveat must sit at the call site, in the
module docstring, not only in a study — and §4.18's client-computed salvage-destroy formula is
a second place where it bites harder than it does for the PRNG.

### 2.8 The system census — every row, and what decides it

**Why this table exists.** The draft asserted *"of eleven candidate systems, two are genuinely
server-only"* and never listed them, and two paragraphs later cited `PLAN.md` §1.7's *"four
genuinely server-only things."* Both can be true because they answer different questions, and
neither published its rows. §1.7 means **"has no client-side artifact"**; §0 means **"no
instrument reaches it."** Those come apart immediately — absolute monster health has no
client-side artifact *and* has been sitting in the vault in the clear since 2026-08-07 (§6.1)
— so the census below splits the predicate into three columns and lets the tally fall out.

**All four of `PLAN.md` §1.7's items survive re-checking** as SERVER-ONLY: absolute monster
HP/energy/armour, spawn placement, drop tables, AI decision logic. **The draft's "two of
eleven" does not**, and is replaced by this table's own count, taken from the verdict cells
themselves rather than from prose: of 28 systems, **3 are FULLY CLIENT-SIDE, 12 are
HALF-MIRRORED and 13 are SERVER-ONLY.** The document's thesis survives the larger census
intact and is if anything understated.

**Denominators, once, for the whole table.** Every wire count is canon-12 (§1.1). Every binary
count is over build 38797, whose readable assert corpus is 19,758 sites. Every `Gw.dat` count
is over 698 map rows. **Instruments** are §3.1's, plus the offline ones: **O1** ArenaNet's
recorded s2c, **O2** their recorded c2s, **O3** the live client as a judge that can crash,
**C** the client binary (asserts, compiled tables, disassembly), **D** `Gw.dat`, **L** loopback
labelled runs, **W** GWW.

| # | system | where the vocabulary lives | where the decision lives | verdict | evidence (measured in this tree) | instruments | Pre-Searing v1 |
|---|---|---|---|---|---|---|---|
| 1 | Item **modifier vocabulary** | client, `ITEM_ATTRIBUTES` = **559** dwords @0xA33B00 + `ITEM_DESCRIPTIONS` = **388** @0xA343C0 | — | **FULLY CLIENT-SIDE** | `ConstItem:9119`/`:9125`; both accessors are `mov eax,[esi*4 + base]`, i.e. string-id arrays; §2.2's 559/559 and 388/388 plain | C, D | in scope |
| 2 | Item **generation** (which mods, what magnitude) | client (row 1) | server | **SERVER-ONLY** (the roll) | 394 `0x0161`; 990 modifier words; §4.2's FD result; evaluator `0x00923A40` | O1 | in scope, n small |
| 3 | **Base-item drop table** (foe → item) | nowhere we hold | server | **SERVER-ONLY** | 19 `Gw.dat` chunk slots over 698 rows carry no loot slot; 3 game-logic sites in a 19,758-expression grep; §1.5's 4 kills / 2 drops | O1 only | in scope, n = 2 |
| 4 | **Gold** drops and gold arithmetic | client holds the *rendering* rule (§2.3) and the affordability test `VnGuildAddService:969` | server for every amount | **HALF-MIRRORED** | 5 gold-naming asserts, all UI (`VnTradeBuy:162/174`, `VnTradeSell:265/277`); no gold opcode in 155; but §10.6's field[9] is a per-instance gold value on 84 of 394 records | C; O1 partial | in scope |
| 5 | **Chests** | — | server | **SERVER-ONLY** | zero `chest`-naming asserts in 19,758; zero chest traffic in 22,524 | none today | **out of scope** — no chest was opened in either capture and none is reachable in the v1 area |
| 6 | **Skills — the catalogue** | client, `s_skill` = **3,443 × 164 B** @0x00988ED0 | — | **FULLY CLIENT-SIDE** | `ConstSkill:3833` bound `0xd73`; `imul eax, esi, 0xa4` at 0x005A88D3; `skilltable.py` finds it structurally | C, D, W | in scope |
| 7 | Skills — **energy debit** | client: cost is an index into `s_energyTable` = **19** entries @0x00988E80 | server enforces; never states | **HALF-MIRRORED** | `ConstSkill:3762`; energy is **0 of 22,524** on the wire — the client debits optimistically and the server is silent | C; O1 blind | in scope |
| 8 | Skills — **adrenaline** | client, `+0x38` raw units; `ceil(raw/25)` displayed | server accrues | **HALF-MIRRORED** | `studies/skills` §10, CORROBORATED against GWW's "80 units"; **0 of 22,524** adrenaline messages | C, W; O1 blind | in scope |
| 9 | Skills — **recharge enforcement** | client, `s_skill` **+0x4C** | server, and it **re-states the client's own number** | **HALF-MIRRORED** | **exactly 1 of 41 dword columns** reproduces ArenaNet's `0x00E5` values {153:8, 105:6, 394:3}, and it is +0x4C — where GWCA independently declares `recharge`. 6 messages, 2 conns | **O1 + C** | in scope |
| 10 | Skills — **cast, interrupt, aftercast** | client, `+0x3C` activation / `+0x40` aftercast (1.0/2.0/0.0 and 0.75/0.75/0.0 for skills 153/105/394) | server confirms; client predicts | **HALF-MIRRORED** | the whole lifecycle is `0x00E2`=1, `0x00E3`=6, `0x00E4`=7, `0x00E5`=6, `0x00E6`=6, `0x00E7`=`0x00E8`=**0** — **26 messages**; field 3 of `0x00E3`/`0x00E4` is the skill id and matches the bar | O1, C | in scope |
| 11 | Skills — **condition / hex application and duration** | client holds the names only: `s_charCondition` = **9** ids → Bleeding, Blind, Burning, Crippled, Deep Wound, Disease, Poison, Dazed, Weakness | server: `buffId`, and the **duration is a float the server sends once** | **SERVER-ONLY** (the numbers) | `ConstChar:1135`; six `EFFECT_*` opcodes `0x3F`–`0x44` and only **`0x0041` fires, 4 times on 4 conns**. No duration is in any client table | O1 (n=4), C | in scope |
| 12 | Skills — **damage application** | client holds `s_charDamage` = **14** type names | server | **SERVER-ONLY** | `ConstChar:1158`; damage arrives as agent-property traffic (`0x00A3` 61 msgs / 4 conns, kind 16 = `PROP_DAMAGE`); §4.6's 31-of-53 exact-integer control | O1, O3 | in scope |
| 13 | Skills — **healing** | — | server | **SERVER-ONLY** | indistinguishable from row 12 on the wire; no separate opcode among the 155 | O1 | in scope |
| 14 | Skills — **target validation** | client pre-filters: the equip gate `0x005147F0` reads bit 25 of the equipped weapon record (set in **103 of 394** `0x0161` flag words) | server decides | **HALF-MIRRORED** | `studies/enemy` §10.4; c2s split measured: **`0x0046` USE_SKILL n=4 on 1 conn, `0x0027` n=3 on 1 conn, `0x0026` ATTACK_AGENT n=17 on 4** — 7 casts in the entire corpus | O2, C, L | in scope |
| 15 | **Death, resurrection, morale / DP** | **NOT FOUND in the client** — zero asserts matching `morale\|death\|resurrect\|corpse` in 19,758 | server | **SERVER-ONLY** | the only wire evidence is a status bit on `0x00F0` (951) / `0x00F1` (415); no DP, morale or resurrect opcode among the 155. `CharPool.cpp:84 fraction <= 1.0f` is the revive bound O3 already found | O1, O3 | in scope |
| 16 | **Quest state machine** | client holds only UI (8 `Quest*` modules, 53 sites) and renders **server-supplied coded strings** (`GmQuestComplete:312 codedRewardsBlurb`) | server | **SERVER-ONLY** | `0x003B` = 22 selects / 6 conns, `0x0012` = 16 / 8 conns, **7 distinct quest ids** (62, 80, 82, 86, 218, 222, 1462). Quest id = **`(code >> 8) & 0x0FFF`**, 14 of 17 pairs; the low byte is the dialog OPTION | O2, C | in scope, and cheap |
| 17 | **Weather and time of day** | client: map chunk slot **0x09 Environment in 698 of 698 rows**, plus Light 698/698, Sound 698/698, Shore 698/698, CubeMap 414 | selection index possibly server; no traffic observed | **FULLY CLIENT-SIDE** | `MapData:4415 id < arrsize(s_chunkInfo)`; `EnvDataImport:573 tag->index < …envArray.Count()` says a map holds SEVERAL environments; `ConstTime` = 8 sites, all formatting | C, D | in scope; the cheapest whole system in the document |
| 18 | **Instancing and district assignment** | client holds the district vocabulary: `UiCtlDistrict:461-464` names MISSIONS, TERRITORIES, LANGUAGES and `district.instance`; 55 sites / 2 modules | server assigns | **HALF-MIRRORED** | one TCP connection per instance is the observable — 12 connections over 3 captures, route 148→146→164→146 in both sessions; `GAME_SERVER_TRANSFER 0x01A5` n=6 | O1, C | in scope |
| 19 | **Player-to-player trade** | client holds the whole state machine's vocabulary: `GmTrade:529/645/812/873/960` name `TRADE_STATE_*`/`TRADE_TRANSACT_*`, `TrdCliSess:371 TRADE_STATUS_OFFER_COUNT`; 70 sites | server arbitrates | **HALF-MIRRORED** | **0 of 22,524** trade messages — both captures are solo | C only | **out of scope for v1** — needs two accounts in one instance, which the live-behaviour rule and the one-client rule both forbid |
| 20 | **Title and reputation accrual** | client, `s_titleClientData` = **48 × 12 B** @0x00A35B80 and `s_charFaction` = **4** → Kurzick, Luxon, Balthazar + 1 | server accrues | **HALF-MIRRORED** | `ConstTitle:81`, `ConstChar:1194`, `AttribTitles` 9 sites, `GmCtlSkList:3294 title < TITLES`; **0 of 22,524** title messages | C | **out of scope** — the measured faction vocabulary is Factions/Nightfall content, and no title track is reachable in the v1 area |
| 21 | **XP and the level curve** | GWW's closed forms, fitted by us (§9.3) | server | **HALF-MIRRORED** | `0x00EE` = **17 messages on 6 conns**, payloads only `(10,0)×7` and `(0,N)` for N ∈ {26,100,126,250,500}; §4.6's residue refutation stands. No XP table among the client's 90 | O1, W | in scope |
| 22 | **Attribute points** | client holds the **cost ladder**: `s_attribPoints` @0x00BC8B24 = `[5, 1,2,3,4,5,6,7,9,11,13,16,20]`; `s_attrib` = **51 × 20 B** | server owns the **budget** | **HALF-MIRRORED** | `CharData:202 level < arrsize(s_attribPoints)`, bound 13; `ConstAttrib:139`; `0x0037` = 11 msgs on 11 conns, all `[55, agent, 0, 0]`. `ChCliAttrib` runs a **sequence-numbered** optimistic protocol (`:295 mod->sequence == sequence`) | C, O1, W | in scope |
| 23 | **Spawn tables and population** | nowhere we hold | server | **SERVER-ONLY** | no spawn slot among the 19 chunk kinds; §5.3's confound (all 233 `mon1` creates in map 146); 76 distinct agent ids | O1 only | in scope |
| 24 | **Merchant / trader pricing** | client holds the entire UI and taxonomy: **30 `Vn*` modules, 298 assert sites**, 14 `CHAR_TRANSACTION_*` members | server owns every number | **SERVER-ONLY** (prices) | **0 of 22,524** economy messages; and the sharper statement — **all 22 `0x003B` dialog codes carry high byte 0x00**, so a merchant/trainer/collector service family has *never* reached the wire | C; O1 at n=0 | in scope, and §10 is right that it is the gap |
| 25 | **Salvage and identification** | client holds the tool model: `InvSalvage:663 m_toolId`, `InvItemInteractions:57 toolIndex < MAX_ITEMS_PER_TOOL`, `ITEM_TOOLS` = 10 | server rolls | **SERVER-ONLY** (the roll) | 39 sites over 11 `Inv*` modules; **0 of 22,524** salvage or identify messages, and **0 of 971** on any of 19 c2s item opcodes (§4.16a) | C; O1 at n=0 | in scope, and it is a server roll obtainable one click at a time with no combat |
| 26 | **Collectors and crafters** | client holds the **recipes**: `ITEM_FORMULAS` = **1,501 × 20 B** @0x00A2AFF8 | server owns availability and price | **HALF-MIRRORED** | `ConstItem:9131` bound `0x5dd`; consumer named by `VnCraft:144/1035/1094/1209` and `VnCraft:124 elemCost`; `VnCollect:441 trophyHasLootDef`, `:445 trophyHasItemDef` | C, D | in scope |
| 27 | **Damage and armour** | client holds `s_charDamage` = 14 and `s_charKindSlaying` = 12 | server | **SERVER-ONLY**, and **armour is not on the wire at all** | §7.5 re-confirmed: no armour-shaped property id among the 21 integer and 3 float ids over 22,524; a damage-formula fit keeps armour as a free parameter | O1, O3 | in scope |
| 28 | **Combat AI** | — | server | **SERVER-ONLY** | **parallel arc — no research done here.** Named so the census is complete and so §4.4's inter-tick bucket and §4.12's reachable-assert sieve have a stated destination | — | out of scope by arc |

**What the tally means.** Of the thirteen SERVER-ONLY rows, **nine are reachable by a behaviour
oracle at n ≥ 1 today** — eight by O1 (2, 3, 11, 12, 13, 15, 23, 27) and one, row 16, by **O2
only**, since the quest state machine is witnessed in the client's own `0x003B` selects and
`0x0012` requests and never in server traffic. Three (5, 24, 25) are at **n = 0** because
nobody has opened the panel, and one (28, combat AI) names no instrument at all and is the
parallel arc. The rows were counted from the verdict and instrument cells directly, and the
O1/O2 split was re-read from the instrument cells after a first pass wrote "nine by O1 alone". That
is the same conclusion §10 reaches from the economy side, arriving from the census side, and
it adds two systems to §10's shopping list that cost the same minutes: **use one ID kit and
one salvage kit** (row 25 — a server roll with a client-visible ground truth, no combat, no
repetition) and **select one service at a skill trainer or crafter** (row 24 — the only way to
put a non-zero high byte on `0x003B`, which 22 of 22 captured selects lack).

### 2.9 Skills, the largest half-mirrored system, and the one place a client constant has been checked against ArenaNet

**The document's own thesis has a best case and the original pass missed it.** `s_skill` is
**3,443 rows of 164 bytes** at `0x00988ED0` — `ConstSkill:3833` bounds it at `0xd73` and the
accessor's `imul eax, esi, 0xa4` states the stride — and every number a caster needs is in it:
energy (an index into `s_energyTable`), adrenaline, activation, aftercast, recharge, the
two-point rank scaling, and the profession/attribute codes. Nothing in any message in either
direction carries one of them. **The server owns which and when; the client owns what.**

**[OBSERVED] 2.9.1 The corpus witnesses the whole lifecycle and it is 26 messages.**
Over 22,524 server messages: `0x00DA SKILLBAR_UPDATE` **11 on 11 of 12 connections** (the
Necromancer's bar is `[153, 105, 0×6]`, the Ranger's `[394, 446, 0×6]` — two skills each, and
the second array every catalogue calls `pvp_masks` is **all zeros in 11 of 11**), `0x00D9` 4,
`0x00E2` 1, `0x00E3` 6, `0x00E4` 7, `0x00E5` 6, `0x00E6` 6, and **`0x00E7` and `0x00E8` zero**.
The effect family is thinner still: of the six `EFFECT_*` opcodes `0x3F`–`0x44`, only
**`0x0041` appears, 4 times**. Client-side, `0x0046 USE_SKILL` is **4 messages on one
connection** and `0x0027` is **3 on one** — the split `test_cmsgnames.py` found, now measured
on the canonical twelve. **The skill numerator is as small as the drop numerator**, and §1.8's
saturation curve says more hours of the same content will not grow it.

**[OBSERVED/CORROBORATED] 2.9.2 `0x00E5`'s trailing field is the client's own `+0x4C`, and
this is the first client-side skill constant ever checked against ArenaNet.** The server sent
recharge 8 for skill 153, 6 for 105 and 3 for 394. Reading **all 41 dword columns** of those
three records out of the pinned build, **exactly one reproduces all three** — dword 19, byte
offset **`+0x4C`** — which is where GWCA's `Skill.h` declares `recharge`, from a lineage that
never saw this capture. Activation and aftercast sit beside it and agree the same way
(`+0x3C` = 1.0 / 2.0 / 0.0 s, `+0x40` = 0.75 / 0.75 / 0.0). Printing all 41 columns is the
control: one hit out of forty-one is what makes this a measurement rather than a coincidence.
**`0x00E5 SKILL_RECHARGE` should be promoted from UPSTREAM to CORROBORATED in
`schema/overrides.json`, with ArenaNet's own traffic as the independent leg** — it would be
the 22nd named GAME_SMSG and the first named on a *value* rather than on a shape.

**[OBSERVED] 2.9.3 The client's compiled effect table, which no pass in this repo had.**
`ConstEffect:2108` bounds `s_effect` at `0x81d` = **2,077**, and the accessor's `shl esi, 4`
gives a **16-byte** record at `0x00BA3CA8`. The table is self-indexed in 2,076 of 2,077 rows —
the same idiom `skilltable.py` already relies on for `s_skill`. Its one populated payload
column resolves through `Gw.dat`'s own file-id table **2,077 of 2,077 (100%)** against a
size-matched uniform control at **923 of 2,077 (44.4%)**, and **2,017 of 2,077 (97.1%)** of the
targets open with the `ffna` magic. It is **not** a text string id: `textrec.py` resolves 1 of
9 sampled values, to unrelated text — the same rate as §2.2's own uniform-random control, and
it is reported rather than dropped.

**This closes a NOT FOUND that `studies/skills` has carried since 2026-08-05.** That document's
*"Cast animations — the real gap"* records six ids at `+0x74`..`+0x88` with *"nothing anywhere
resolves an animation id to an asset."* Across 3,443 rows × 6 columns every value is ≤ 2,076
or **exactly 2,077**, and 2,077 = `arrsize(s_effect)` is the null, used 1,921 / 2,536 / 2,567 /
3,427 / 3,243 / 3,300 times per column; the control column (a string id) reaches 388,755, so
the record is perfectly capable of holding larger numbers and does not. So the six fields are
`s_effect` indices, and the resolution chain **skill row → `s_effect` row → `Gw.dat` file id →
MFT row** runs entirely on artifacts we hold, with no upstream and no server. `studies/skills`
should be updated in the same commit as this document.

**[OBSERVED] 2.9.4 The compiled-table census is 90, not 7.** §2.2 samples seven tables; the
client bounds-checks **90 distinct named `s_*` arrays** (142 distinct `arrsize(...)` operands,
140 assert sites). Six that this document needs and did not have: `s_effect` = 2,077 (above);
`s_energyTable` = **19** @0x00988E80, holding `[0,1,2,3,4,5,6,7,8,9,10,15,25,40,60,90,135,200,
-1]` — GW's literal energy ladder, which means the skill record stores an *index* and
`toolkit/clientscan/skilltable.py`'s hard-coded *"11 means 15, 12 means 25"* is ArenaNet's rows
11 and 12 rather than a magic rule (and is **latently wrong for raw 13..17**, where it returns
the index and the table says 40/60/90/135/200; the observed `energy_raw` set over all 3,443
rows is {0,1,2,3,4,5,6,10,11,12}, so no shipped skill exercises those rows and it has never
fired — note also that checking `decode_energy` against `energy` is circular, since the module
computes one from the other, and only the table read is independent); `s_attrib` = **51 × 20 B**;
`s_attribPoints` = **13 dwords** whose entries 1..12 are GW's published attribute rank costs
`1,2,3,4,5,6,7,9,11,13,16,20` — a **third** primary witness beside §9.3's GWW/GWLP-R pair, and
this one is ArenaNet's own bytes; `s_charFaction` = **4**; `s_titleClientData` = **48 × 12 B**.
Also `ITEM_COLORS` = 14 and `ITEM_MATERIALS` = 50, addressed as one 5-byte-row grid at
0x00A1ED98.

**[OBSERVED] 2.9.5 What the client does NOT hold, stated as sharply as the rest.** The
condition names are names: **there is no duration, no stacking rule and no magnitude anywhere
in `s_charCondition`, `s_charDamage` or `s_effect`** — those tables are flat arrays of ids.
`ChCliBuff.cpp` stores the effect record's `+0x04` and never reads it (`studies/skillcast`
§14.4, still CONTESTED). So §2.8 row 11's verdict is SERVER-ONLY on the numbers even though
the vocabulary is entirely client-side, and a server that hands out large `buffId`s will
assert in a real client the moment the effect UI touches one (`GmEffect:3021`/`:3030`) — which
makes `buffId` a **small dense space we must allocate carefully**, and is exactly the kind of
constraint §4.12's sieve exists to find.

---

## 3. The oracle asymmetry — the frame that explains every verdict below

**[RECONSTRUCTION] 3.1** The taxonomy below is this document's own, not a measured count.
The draft wrote *"the repo owns twelve oracles"* as if twelve were a number somebody had
established; it is a partition we invented for this pass, and one of its members — "the
upstream mirrors" — is several artifacts of which `PLAN.md` §1.1 makes most
verification-only and grants-nothing. **Read the list, not the count.**

Nine of them refute FORMAT and PROTOCOL claims: the client's own `cmds[]` tables (477/477
GAME_SMSG agree field-for-field), its **19,758** readable assert expressions, its dispatch
disassembly, its live memory, a *different* `Gw.dat` chunk than the one under test, the
client's own next handshake, the framing itself as a wrong-key detector, our own logged
plaintext for `replay.py`, and the upstream mirrors. *(19,758, not the draft's 19,620:
`asserts.py` prints the decomposition itself — **19,620 edx-first + 75 ecx-first + 63
shared-tail = 19,758** readable sites, plus 3 sites it can name but not read, against
**20,131** `call rel32` sites landing on the assert routine found by an independent sweep.
So **373** assert call sites are unreadable to a fixed byte pattern, and 19,620 is the
edx-first shape alone — the figure from before `test_codescan.py` §7 pinned that the idiom
has three shapes. It must never appear as a total.)*

**Three refute BEHAVIOUR claims, and that is all there are:**

- **O1 — ArenaNet's recorded s2c.** 12 connections, 22,524 messages, 758.0 s, 155 opcodes,
  12/12 clean. The only artifact this project cannot reproduce. Its refuting power is
  demonstrated: it killed the heartbeat reading of `0x001E`, the cos/sin gloss of `0x002E`,
  the SpeedModifier gloss of `0x002B`, and settled the NPC-definition-across-removal
  question 1-to-140 with no probe. §2.9.2 adds a fifth: it is the only witness that has
  ever checked a value inside the client's skill table.
- **O2 — ArenaNet's recorded c2s.** **971 messages over the same twelve connections, 29
  distinct opcodes, 12 of 12 framing to `consumed == total` with `err is None`** — two
  orders of magnitude smaller than O1, and **44.3% of it one movement opcode** (`0x003D`,
  430). Per-connection: 49/3/83/188/48/30/70/27/69/48/72/284. *(The draft's 919 is BIG-10's
  figure, in the one place the document sizes its second behaviour oracle — the same
  denominator slip §1.1 makes a rule about.)* It has already refuted one of our own names:
  `0x0046 USE_SKILL` was named from a caster, and a whole Ranger session casting Power Shot
  sent zero of it — attack skills leave on `0x0027`, for which our server has no dispatch
  arm.
- **O3 — the live client itself, as a judge that can crash.** `CharPool.cpp:84 fraction <=
  1.0f` killed the client on the one side of a bound no damage test could reach.

**Every technique in §4 and §5 is an attempt to squeeze more out of O1, O2 or O3.** The ones
that died mostly died because they were actually squeezing a format oracle and reporting it
as behaviour. §4.11's sweep is the sharpest case: it is a magnificent *format* oracle and
§4.11g says so out loud, because a technique that renames a third of the catalogue is
exactly the kind of thing that gets quoted as a behaviour result.

**[OBSERVED] 3.2** The attribution gap, and it is structural rather than a missing flag.
`toolkit/authsrv/labelrun.py` is the only instrument that attributes a client message to a
human action — and it is a flag on `authsrv.py` that writes `rec.event('label_step', ...)`
through **our own server's recorder** (`labelrun.py:398`). During a live capture there is no
Rurik process in the loop. `livesession.py` launches, sniffs, taps, holds, assembles and
scrubs, and writes **no mark of any kind**. So both live captures are NARRATED (a human
wrote down what they did afterwards) and never LABELLED. §10.5 promotes `marks.py` from a
closing sentence to a precondition and specifies it to the file.

**[OBSERVED] 3.3** And the two directions cannot be joined on one clock without new code.
`tape.load_tape` computes `t0` — the first s2c segment's absolute wire time — at
`tape.py:213` and **discards it**; `info` carries capture/connection/file/events/bytes/
seconds/origin and no `t0`. `cmsgstream.timed()` already returns wire-absolute times for both
directions, so the join is one exposed value away. Two skeptics disagreed on whether this
blocks anything: one showed `cmsgstream.timed()` alone already joins c2s and s2c on one
absolute clock, which is true, and the join is not a toy — on `20260807T143055` it returns
**(419 + 11,241 messages on one absolute clock)**, both directions, five connections, and on
`20260810T235916` it is 500 + 10,896. But a *tape* event time is relative and cannot be joined to
it. Both are right about different readers. **Expose `t0`. It is one line and everything
downstream wants it**, `marks.on_tape` first.

---

## 4. What survived, ranked by information per hour of human play

Sixteen of thirty-nine, plus three classes the pass missed and the revision added. The
ranking metric is brutal and it inverts the intuition: **almost everything that survived
costs zero human play hours**, because it runs offline on bytes already in the vault. The
live actions are cheap in minutes but they are the only ones that add a message class the
vault has never held.

### Tier 0 — zero live hours, zero loopback, offline on bytes we already have

| # | technique | verdict | status |
|---|---|---|---|
| 4.1 | **Instance re-roll: SET vs ORDER of the load burst** | SURVIVES-WEAKENED | **result already produced** |
| 4.2 | Functional-dependency mining over `0x0161` | SURVIVES-WEAKENED | **result already produced** |
| 4.3 | Refusal-first three-valued loot constraint checker | SURVIVES-WEAKENED | train/test already run |
| 4.4 | Flush-bucket causality (count steps, not milliseconds) | SURVIVES-WEAKENED | **result already produced** |
| 4.5 | gcd-of-differences lattice detection | SURVIVES-WEAKENED | `math.gcd` only, ~1 h |
| 4.6 | Residue-class refutation of formula-named payloads | SURVIVES-WEAKENED | refutation already complete |
| 4.7 | Kill ledger with a two-sided coincidence null | SURVIVES-WEAKENED | 4 rows, censored flags |
| 4.8 | Definition-slot archaeology, slot-band half | **upgraded from REFUTED** — see §6 | |
| 4.9 | Unclaimed string-run census | SURVIVES-WEAKENED | needs null rebuilt + pinned build + a §9.4 ruling |
| 4.10 | Adopt ArenaNet's MWC1616 + PRNG identifiability audit | **SURVIVES** (both) | the only clean survivors |

**4.1 [OBSERVED] Instance re-roll — the answer is in hand and cost nothing.** Pairwise order
agreement over shared definition slots, on the two matched *explorable* pairs: **0.963 over
820 comparable pairs and 1.000 over 153**, against per-pair empirical shuffle nulls of
0.506 ± 0.043 and 0.340 ± 0.070. Different-map pairs land at 0.443–0.571, so the statistic
discriminates rather than always saying yes. The list-walk model holds; the roster is walked
in order, not drawn from a pool. n = 2.

Three repairs are mandatory and each is one line. The proposal's stated null was "shuffle and
it must collapse to ~50%" — **measured shuffle means run 0.340 to 0.568, and 7 of 11 pairs
sit more than three standard errors off 0.50**, because definition slots repeat heavily and
first-occurrence indexing pulls frequent slots earlier after a shuffle. Score against the
*empirical* per-pair null and print its mean and sd beside every agreement. Second, apply the
`field[12]` class-tag filter to the outpost control: the busy-outpost pair scores 0.685 only
because 223 of its 323 creates are other players, and an operator running the control as
written would read that as "unstable" and throw away a 0.963 finding. Third, `field[2]`
masking of `0x20000000` is wrong for the `0x3000xxxx` player family. §8.3 turns all three into
criteria that can go red.

**4.2 [OBSERVED] Functional dependencies localise the per-instance roll to one list and one
bit — and the bit is now named.** Mining all 394 canon-12 records, 16 columns, minimum support
5 distinct determinant values fixed before the run, every FD checked against 200 independent-
column shuffles: `(item_type, model_id) → field[2]` holds with **zero violations over 59
groups**; `→ field[8]` has **6 violations, and all six differ in exactly one bit, bit 23**.

**Bit 23 is the UNIDENTIFIED flag, read out of the client rather than guessed** (§4.17): the
item-name builder at `0x009236B0` executes `0x009236D9 test dword ptr [esi + 0x1c], 0x800000`
and, when set, pushes string id **2453** — the word "Unidentified" — in front of the base
name. So the correct sentence is *the roll visible in this record is the modifier list, and
the one bit that varies beside it is the server telling the client whether to show that list*,
which is a better and different answer than either the proposal or the draft reached. **16 of
394 records in the vault are unidentified items**, on 4 of 12 connections, item types 27 (9),
24 (6) and 12 (1).

Three of the proposal's four stated predictions were refuted by its own run: `model →
item_type` has one violation (model 419 carries types 4 and 27); the "subset relation"
prediction cannot fail and must be deleted; and the named discriminator was refuted for
`field[2]`. Cross-check `field[8]`'s identity against `toolkit/clientscan/itemprobe.py`, which
reads bit 25 of the item record at `rec+0xc` — a second witness the proposal never named, and
one command settles whether wire `field[8]` and the client's item-flags dword are the same 32
bits, which is **UNVERIFIED** today (§4.17 gives the two circumstantial legs).

**4.3 [OBSERVED] Refusal-first constraint checker.** Trained on `20260807T143055` alone and
tested on `20260810T235916`: legal 73.8% / unknown 26.2% / **illegal 0.0%**, against a
pre-registered "< 25% unknown". At word level the unknown rate is 13.5%. Four repairs, and the
first is the interesting one: **its own shuffle control fails in the direction that proves the
technique works.** Reassigning modifier lists across items made the incidence matrix 2.8×
*denser* (45 → median 126 cells) while making held-out generalisation *worse* (13.5% → median
19.5%, and all 400 shuffles were worse than the real gate). The proposal's pass condition was
"denser AND lower unknown", so as written it would report its own strongest evidence as a
failure. Invert it. Also: cardinality above the observed maximum must be UNKNOWN, never
ILLEGAL — running the split the other way produces exactly one "illegal", and it is the earlier
capture's single 5-modifier item judged against a held-out maximum of 4.

And report coverage over the **82 distinct `(field[2], field[3], field[10], mods)` tuples and
46 distinct modifier lists**, not over 394 records. **Name those field indices in the module.**
The 46 reproduces on canon-12 and on BIG-10 (chain-8 gives 42); the 82 reproduces only for a
reader who knows which columns `type` and `model` are — an independent fixer, told only
"(f2, type, model, mods)", got 110 tuples on BIG-10 and 128 on canon-12 under a plausible
different guess and correctly reported the figure as unauditable. Two readers who cannot
reproduce a coverage denominator do not have one. *(The related group count is stable and
worth stating: `0x0161` field[10] has 58 distinct values and is the only column yielding **59**
groups when paired with any of field[2], [3], [4], [6], [7] or [12], on BIG-10 and canon-12
alike — which is §4.2's group count arriving from the other side.)*

Say out loud that **58.6% (231/394) of the corpus arrives within 2.0 s of a connection
opening** — this is one of the few item-side figures the draft had on the right denominator
already (BIG-10 195/340 = 57.4%, chain-8 137/246 = 55.7%), and it is worth naming as such. But
correct the noun twice: it is not "eight times over" — the 2.0 s cohort spans **12 of 12
connections**, and 87 of the 231 (37.7%) are the three character-select connections, which are
not instance loads at all. And it is not an inventory dump: the in-world load-burst records are
dominated by NPC- and monster-carried weapons declared as agents enter view, arriving in
`(type 27, type 24)` pairs at one timestamp throughout a session (t = 0.6 s to 132.9 s on
`:62994`), never bagged, never equipped, never named by any `0x006E`. Whose they are is
**UNVERIFIED** — `0x0161` carries no agent id — but they are demonstrably not the player's
inventory and not other players' visible gear.

**4.4 [OBSERVED] Flush-bucket causality, and it refuted its own prediction.** Counting `0x001E`
ticks between two events instead of milliseconds is the right unit, and the run says: in
**both** corpus drops, `0x00F1 → 0x0161 → 0x0135 → 0x0168` are all lag 0, and `0x0020` (the
ground agent) is **lag 1**, followed by `0x00EE` at lag 0. The prediction was lag 0 throughout.
The honest reading is "the item record and the reward are same-step; the ground agent is one
step later, in 2 of 2" — with the per-link noise floor printed beside it, because **72.31% of
consecutive non-tick pairs are already at lag 0** (pooled, n = 14,607; 0.521 in the drop tape).
Two more corrections: predicted lag must come from the *mean* delta, not the median
(`0x00F0 → 0x00F1` at 2.000 s measures 17.0–21.5 buckets against a median-based prediction of
22.5–33.9); and the instance-load prologue must be excluded, because the first tick lands at
message index 203–1,334 on every tape and every lag inside that one bucket is 0 by
construction. Rename the unit: it is an inter-tick bucket, and **16.6% to 69.8% of them are
empty**, so "flush of world updates" is the wrong noun. *(This unit transfers directly to
combat AI: "did the server decide the target in the same step as the damage" is the same
question in the same clock.)*

**4.5 [OBSERVED] gcd lattice detection**, with its negative control run on ArenaNet's own bytes
and passing: `0x24B8` returns gcd 256 over **172** canon-12 samples with 9 distinct arguments;
`0xA488` returns 1 over **170**; and `0x001E`'s 6,928 tick payloads (489 distinct) return gcd 1
both raw and on within-tape differences, on all 8 tapes individually and pooled. The detector
does not report a lattice where none exists.

One defect must be fixed before use, and **the draft's exemplar for it does not survive the
canonical denominator, which is itself the lesson**: *8 of the identifiers have exactly one
distinct argument value, and gcd on a constant returns the constant.* On canon-12 there are
**18** identifiers, not chain-8's 17 (`0x8040` is absent from chain-8 entirely), 8 still have
exactly one distinct low half, but **`0xA0F8` is no longer one of them** — n = 110 with 3
distinct low halves (chain-8 n = 20 with 1). The new worst case is **`0x8040` at n = 75 with
one distinct value**, invisible to chain-8 at n = 0; the full one-value set is `0x8040` 75,
`0x8030` 35, `0x62E8` 29, `0x2448` 12, `0xA498` 9, `0x8080` 3, `0xA228` 3, `0x23A8` 1. Replace
the sample-count floor with a **distinct-value floor** (`len(set(values)) >= 2`), report `d` as
a divisor of the observed spread rather than of the values, and restate the null empirically
rather than as `256^-k` under a uniformity the data refutes.

**4.6 [OBSERVED] Residue-class refutation.** `0x00EE`'s 17 payload pairs are `(10,0)×7`,
`(0,26)×3`, `(0,100)×2`, `(0,250)×2`, `(0,500)×2`, `(0,126)×1`; residues mod 16 are
`{10,4,14,10,4,0}` and the kill-coincident value 26 is outside `{0,4,8}`, which the GWW per-foe
XP closed form requires. It has a positive control that runs on ArenaNet's bytes: `0x00A3`
property-16 fractions × the `0x009F`-declared `PROP_HEALTH_MAX` give exact integers
(−4, −3, −22, −5, −6, −25, −1) on 31 of 53 events, with the other 22 reported as uncomputable
rather than dropped. Two repairs: **state the join as segment-ordinal, not timestamp** — the
four death segments carry 12, 8, 19 and 6 messages, so co-timestamping is a 1-in-12 join and
what actually rescues the pairing is intra-segment order — and write the refutation as a note
that enumerates its conjuncts, marking the naming CONTESTED rather than dead, since the test
cannot say which conjunct broke.

**4.7 [OBSERVED] The kill ledger**, demoted to what the corpus supports. Its novel move —
reading the drop owner off `0x0168`'s second field instead of inferring it from a time window —
is **CONTESTED at 2 of 7**: in 2 occurrences `f2` names a created agent, in 1 it matches a
declared `0x0161` item id, and in **5 it matches neither**, so the stated `f2 = dead agent` vs
`f2 = local player` dichotomy is a false one the corpus already breaks. **§0 must not state
this chain settled, and no longer does.** What holds: corpse-to-item distance 126.3 and 35.6
units, **rank 0 of 18 and 0 of 8** living agents, nearest other agent 721.3 and 1,629.1 — and
**the wire records the kill that dropped nothing**, which is the structural point and is
confirmed (the two no-drop death segments carry `0xF1` and `0xEE` and no `0x0161`, `0x0168` or
ground create at all). Two defects would have shipped: the spatial null must use **tracked**
position from `0x0029`/`0x0025`, not the create position (using the create position measures
14,368.8 units on the 19.912 case and would refute the pairing it exists to support), and the
"two census passes disagree on which byte marks the ground item" refusal is a misread nesting —
`field[3]` and `field[4]` cross-tabulate cleanly as `{(1,5):366, (1,8):25, (1,9):560, (2,1):94,
(3,0):11, (4,0):12}`, so the rule is **item iff `field[3]==4`**, and refuse only when
`field[4]!=0` while `field[3]==4`. A third is added by §1.5: the class-tag join must be
**time-windowed**, because agent id 38 is reused for an `anim` agent 55 s after the kill.

**4.8 Definition-slot archaeology** — see §6, where a skeptic's REFUTED verdict is overturned
by the bytes. The slot-band half (54 distinct slots, four bands, per-map sets) stands as a
floor. The name join does not, until the codec is fixed.

**4.9 [OBSERVED] Unclaimed string-run census**, with its headline numbers corrected. The plain
count is **28,407 of 101,376 (28.02%)**, not 26,705 — the reported pair `26,705 plain + 72,969
encrypted` sums to 99,674 against 101,376, an internal contradiction of 1,702 records that
nobody caught. "217 runs" was segmented from *skill name ids* on the **wrong build** (3,438
skills = the 2026-04-30 client; the pinned 38797 build gives 3,443 skills / 3,442 gaps / 220
gaps > 16). Segmenting the plain id set at gap > 16 gives **476 runs**. Its null control is
confounded and cannot fail: a run cut out of the plain set is plain by construction (90.3%
inside runs vs 23.7% for uniform windows), so random windows lose on *resolvability*, not
coherence. Rebuild the null by drawing size-matched windows **from the plain id set itself**.
And re-aim the target: decoding the 12 largest unclaimed runs finds **item base names** (armour
families and weapon names) and **no creature-name family at all**. Sell it as item base names;
that is what it delivers.

**And it carries a provenance-gate exposure the draft flagged for the assert export and not for
this.** Its deliverable is 476 runs of decoded `Gw.dat` text, and the draft already quoted three
extracted item names into what will become a tracked file. **That is a bulk string extraction
from ArenaNet's archive heading for version control, in exactly the same category as §9.4's
assert export, and under the top of `CLAUDE.md` the default is REFUSAL pending an owner
ruling.** The permitted shape is §4.16a's: cite by **string id and paraphrase**, resolve at run
time against the owner's own archive, and leave the bytes where they are. Named item strings do
not appear anywhere in this document for that reason.

**4.10 [OBSERVED/CORROBORATED] MWC1616, and the negative that must be written down once.**
Adopting ArenaNet's own generator and its modulo-biased range helper is legitimate, costs
nothing, and can never rise above RECONSTRUCTION — which is exactly why it is safe: the relative
bias is ~n/2^32, so detecting it needs ~10^14 draws. Correct the addresses before anyone follows
them: the **entries are `0x0046D170` (range helper) and `0x0046D1F0` (raw draw)**;
`codescan.py --dis 0x0046D1E0` shows six instructions and a `ret` and misses the inlined MWC
core and both zero-guards entirely. §2.6 splits the label three ways and §2.7's caveat rides at
the call site.

The audit that goes with it is the one technique on the whole list whose deliverable is a
**bound rather than a number**: 64 bits of state, ~5 bits observable per event, 53 damage events
and 4 kills in the entire corpus, with an unknown number of interleaved draws from every other
subsystem. **PRNG state recovery is not merely expensive, it is closed.** Writing that down
before a capture campaign is designed around it is worth the four hours by itself. Drop its
clock-dependence bit — it depended on a `p̂` that §5 refutes.

### Tier 1 — loopback agent hours, no live service

**4.11 [SURVIVES, RESCOPED] Exhaustive s2c stimulation of a real client on loopback — the
332-row opcode→effect map.** §1.4 measures 332 catalogued GAME_SMSG opcodes never seen from
ArenaNet across the canon-12 corpus. The proposal that reached this pass provoked replies for
exactly two of them (`0x00C3`, `0x00F7`). The inverse and much larger move is to **send each of
the 332 to our own client on loopback and record what happens** — zero live minutes, zero policy
exposure, and the deliverable is the one thing no volume of capture produces: a name for the
third of the catalogue our corpus has never carried. **Every one of the six adversarial lenses
missed this, and on the document's own ranking metric it is Tier 1 #1**, because it costs no
human play hours at all.

*(The proposal's original strategic point survives verbatim and is the reason the rescoping is
worth doing: sending a message and reading the client's* reply *turns a live-capture-gated
problem into a loopback problem — the most valuable transformation available under the
live-behaviour rule. `0x00C3` and `0x00F7` are 0 of 22,524, both have real receive handlers
(`0x0091F230`, `0x0091F970`), and `test_dispatch.py` is shipped and green: 21 checks, both
chains ending in a real `else` calling `note_unhandled`, four negative controls red. They are
now two rows of a 332-row table.)*

**[OBSERVED] 4.11a The sending half is already built and costs nothing to reach.**
`authsrv.py`'s per-connection `send(opcode, values, label)` closure encodes through
`codec.encode` and writes under the ARC4 send lock, recording `rec.event("sent", seq=…,
opcode=…, plain=…)`; `send_raw` takes pre-formed plaintext; and `run_probe` already drives a
list of `Step(delay, opcode, values, label, watch)` on its own thread and swallows a failed step
as a result rather than a crash. A sweep is a generated probe, not new plumbing. Measured over
all 487 catalogued GAME_SMSG: **487 of 487 encode with degenerate values** (zero failures,
2–99 B on the wire) and **487 of 487 encode and round-trip byte-identically with plausible
values**, including a five-character ASCII `string16`. 363 of 487 carry no counted field at all
(43 header-only, 320 fixed scalars); restricted to the 332 never-seen it is **247 of 332** (32
header-only, 215 fixed-only), with 63 taking a `string16`, 13 an `array32`, 8 a `nested_struct`,
7 a `blob` and 49 at least one `agent_id`. **§6.2 does not gate this.** `codec.py:202` is a
*decode* defect — it destroys GW's surrogate-range code units on the way in — while the encode
side writes `len(s)` and `utf-16-le` exactly, so every `string16` opcode is sendable today.
(487/487 round-tripping is our codec agreeing with itself and proves nothing about the client;
the client-side oracle is `test_catalog.py`'s 477/477 field-for-field agreement with the
client's own `cmds[]` tables.)

**[OBSERVED] 4.11b The readout, and the best channel is already instrumented and free.**
Ranked by cost × reliability:

1. **The client's own c2s reply, attributed by opcode identity.** `note_unhandled` writes
   `rec.event("unhandled", channel, opcode, name)` for every schema-known c2s opcode with no
   server arm — first occurrence prints, the rest are counted, the tally lands at disconnect.
   **New measurement, and it is what makes this channel complete: 189 of 189 opcodes the client
   can transmit are in our GAME_CMSG catalogue, and 189 of 189 agree with the client's own SEND
   descriptors field-for-field on (kind, wire bytes).** That is the SEND-side mirror of
   `test_catalog.py`'s RECV-side 477/477 and nobody had run it. Two consequences: a provoked
   reply always decodes, and it can never reach D9(b), the undecodable path that *ends the
   connection*. Noise floor, measured on our own loopback captures and never pooled with live:
   over 47 sessions and 2,822 s of post-load wall clock the background is 0.502 msg/s, but it is
   dominated by input-driven opcodes (`0x003D` 772, `0x00C1` 162, `0x0047` 88, `0x0040` 57).
   **With the client parked the residual is two opcodes** — `0x0009` at 0.082/s and `0x0008` at
   0.013/s — so a reply on any third opcode is attributable by identity rather than by a timing
   window. In the quietest session in the vault the whole c2s stream is 13 frames in 122 s, with
   post-load gaps of 9.3–29.5 s.
2. **The crash dialog** — still the only machine-readable evidence an assert leaves
   (`session.py: capture_error_dialog`, WM_GETTEXT, never clicks "Send report to ArenaNet").
   Cost: one client restart. Yield: an ArenaNet source file, line and expression. Rebase before
   looking anything up: `file_va = trace_addr - BaseAddr + 0x00400000`.
3. **`Gw.log`, and it is better than this document had assumed.** It does not record asserts. It
   *does* record `Error:` lines: across all 125 harness reports in the vault, 2,377 log lines,
   2,037 `Perf:` and **337 `Error:`** in eight distinct shapes — three of them game-logic
   complaints our own s2c produced (`Health non-zero on resurrect` ×19, `Client pathing data out
   of sync with server` ×14, `Pending skill %u copy %d not found` ×14). Free, already lifted
   into `report.json["gw_log"]`.
4. **The frame channel.** `drive_client.shot()` needs PIL, which is not one of `CLAUDE.md`'s two
   carve-outs and already prints "PIL missing" on a bare machine. The machine-readable form needs
   no image library: a stdlib `framediff.py` doing ctypes `BitBlt` + `GetDIBits` into a BGRA
   buffer and returning a **changed-pixel count and bounding box** — a number a check can assert
   on, rather than a picture a human has to look at.
5. **ReadProcessMemory**, `itemprobe.py`/`agentprobe.py` shape, `PROCESS_VM_READ` only, offsets
   RVA-relative because the client relocates. The only channel that can see a silent accumulator
   — see 4.11d.
6. **Disconnection.** Cheapest, least informative, and by 4.11b(1) it can no longer be caused by
   the reply itself.

**And the loopback advantage §3.2 implies but never states: this technique is LABELLED by
construction.** Both live captures are narrated because no Rurik process is in the loop. Here one
is, so every stimulus and every reaction land in the same recorder file on the same clock. It is
the only technique in this document that does not need `marks.py`.

**[OBSERVED] 4.11c The static pre-pass, which is what turns a fishing trip into an experiment.**
Classify all 487 from the client's own RECV tables *before* sending anything. A handler is a SHIM
when its whole first function is ≤ 16 instructions with ≤ 1 distinct callee and its call chain
reaches FrApi's frame-message broadcast at `0x00633D70` — identified by its own assert,
`FrApi:3901 msgId >= FRAME_MSG_EX` — with a constant `msgId`.

| population | SHIM | POST+BODY | BODY | no RECV entry |
|---|---|---|---|---|
| all 487 catalogued | 124 | 179 | 174 | 10 |
| the 332 never-seen | 89 | 138 | 97 | 8 |
| the 155 live-observed | 35 | 41 | 77 | 2 |

**The never-seen population is UI-heavy, not dead: 227 of 332 (68.4%) post at least one constant
UI msgId, against 76 of 155 (49.0%) of the observed set, z = 4.10.** 253 distinct msgIds are
pushed across all handlers and **180 are reachable only from never-seen opcodes**. Assert
reachability at call depth 2: 280 of 332 reach one, 1,016 sites, 51 modules; strip container
boilerplate and it is **104 of 332 with a game-logic assert, 214 sites, 181 distinct expressions,
68 of them relational** — a domain bound the field must satisfy. At depth 3, 308 of 332 and 74
modules. The subsystem census names where the yield is: ItCliApi 18, PyCliParty 15, ChCliApi 8,
ItCliInv 8, AvApi 7, GuCliApi 7, ChCliAttrib 5, ItCliItem 5, MsCliTourn 5, TrdCliSess 1.

**The prediction, stated first and three-valued.** For each of the 332 the pre-pass predicts
*which readout channel fires*: 227 the frame channel, 258 at least one of {frame, named
subsystem}, and **74 neither — no msgId and no non-boilerplate module even at depth 3, so a
one-shot sweep is predicted silent**. Eight of those 74 have no handler at all and eight are
accumulator-shaped.

**How it can fail, and the control that measures the failure rate.** Run the same classifier over
the 155 opcodes whose effects we already have independent evidence for: it calls **31 of 155
(20.0%) silent**, and that list contains `0x00E3 SKILL_ACTIVATED`, `0x0056 NPC_UPDATE_PROPERTIES`
and `0x0168` — messages that visibly do things. So the silent class carries a measured
false-silence rate of at least 20%, because the classifier is a function of assert density and
one call idiom rather than of effect. A sweep finding effects for far more than 74 refutes the
partition upward; a sweep finding nothing for a large share of the 258 refutes it downward, since
a posted frame message nobody subscribes to is a no-op on screen. Both are results, and both are
why the static pass cannot be the answer on its own. Its other blind spot is structural: the walk
follows direct `call` and tail-`jmp` only, so the frame system's runtime subscription is invisible
to it — **no `Vn*` (Vendor) module is reachable from any message handler at depth 3**, in a client
carrying 30 `Vn*.cpp` modules and 298 vendor assert sites. The static pass can name the msgId.
Only the sweep binds it to a panel.

**[OBSERVED] 4.11d Two findings that fell out of the pre-pass and change the design.** `0x0084`
and `0x00F9` — the two `array32` candidates §10 names — are **not UI posts and not dead: they are
accumulators.** `0x00F9`'s handler (`0x0091F4B0` → `0x00814610`) appends every element of its
array into a list hung off the per-thread client context at base `+0x34`, count `+0x3C`;
`0x0084`'s (`0x0091E820` → `0x00811980`) does the identical thing into `+0x24` and `+0x2C` of the
same struct. Neither posts anything. **A one-at-a-time sweep will file both as silent**, and eight
of the 74 predicted-silent opcodes have exactly that shape, so the sweep must include a paired
pass (fill, then open) and the RPM readout must know those two offsets. `itemprobe.py` already
walks `fs:[0x2c]` / `*0x00C0F300` to reach that context, so this is an offset change rather than a
new instrument.

Second: **`msghandler.py`'s 477 is a floor, and the draft should have said so the way it already
says it about `asserts.py`'s 19,758 against 20,131.** Ten of the 487 catalogued GAME_SMSG have no
readable RECV entry (`0x000A`, `0x000B`, `0x000C`, `0x000D`, `0x000E`, `0x004F`, `0x0055`,
`0x007F`, `0x014A`, `0x01DA`), and **two of them are demonstrably received**: `0x000C`
(header only) occurs **145** times and `0x000D` (header + dword) **144** times in ArenaNet's own
s2c over canon-12, in matched pairs on 11 of 12 connections (39/39 on `:61624`, 37/37 on
`:64103`, 29/29 on `:62994`), with 43 distinct `0x000D` dword values. A message the client
receives 145 times must have a receive descriptor, so either the table recovery misses a path or
the imported catalogue has their direction wrong. **CONTESTED**, and settled by two sends.

**[OBSERVED] 4.11e Cost, safety, and the one design rule that matters.** **No live service is
involved at any point.** Both endpoints are ours: `authsrv.py` on 127.0.0.1 and a `vault/run/`
client carrying OUR Diffie-Hellman parameters, which is the configuration
`cage.assert_launch_safe(exe, "127.0.0.1")` exists to permit. Measured read-only here, with
nothing launched: `dhbuild.describe` 0.05 s → `ours`, `cage.cage_state` 2.89 s → `CAGED`,
`assert_launch_safe` 2.70 s → cleared. `accounts.for_target` supplies the loopback synthetic
credential. Nothing touches `client-patched-live/` or `run-live/`.

**Do not batch — make it resumable, and flush the cursor BEFORE the send.** A crash then costs one
restart rather than a batch, and the cursor names the opcode that did it, which is the assert
channel's primary datum; writing the cursor after the send loses exactly what the crash produced.
A crash arriving two stimuli late is disambiguated by re-sending the suspect alone and requiring
reproduction. Restart cost, measured: gate 2.7 s, process start → game channel open median 5.21 s
over 77 harness runs, auth capture → game capture median 2.0 s over 96 — budget 30 s. Sweep cost:
332 stimuli at 2.0 s spacing is 664 s; interleaving **empty control slots 1:1** (the null — a slot
where nothing is sent must produce no reply) doubles it to 22 min a pass; three passes in
randomised order requiring a reply to reproduce 3/3 is **66 minutes of client-connected time plus
30 s per crash**, worst case (everything crashing) +2.8 h. Report the crash count as a headline; it
is both the cost and the finding.

**Value choice is the entire crash budget.** Zeros are the worst possible fill — 113 of the 181
reachable non-boilerplate expressions are existence checks (`agentPtr`, `item`, `fileId`,
`bag->GetItem(slot)`) that a zero id trips on contact. Pass 1 uses the player's own agent id, item
handles from our own item stream, and small in-range integers. Pass 2 uses deliberately
out-of-domain values, and *its* crashes are the deliverable rather than the cost. A third risk is
bounded: only 7 of the 324 never-seen handlers have a zero-return path in their first function,
against 3 of 153 observed — 2.2% against 2.0%, so "the client rejects it as a protocol error" is
not a property of the never-seen population.

**[RECONSTRUCTION] 4.11f What it buys, ranked.** (1) The opcode → frame-message binding, 227 rows,
and through it the panel — a naming instrument for a third of the catalogue that has no other
route. (2) The c2s request each panel then sends, at n = 332 instead of n = 2, which **pre-answers
§10's fallback branch before the live session rather than after**. (3) The item and economy band:
**23 never-seen opcodes reach ItCliApi / ItCliInv / ItCliItem / ItCliBag / ItCliAssign / ItemCode**,
contiguous from `0x0139` to `0x0162` around the two we do know (`0x013F ITEM_CREATE_BAG`,
`0x0161 CREATE_NAMED_ITEM`), plus `0x0002` into `TrdCliSess`. (4) Field domains by assert at scale
— 68 distinct relational bounds, among them `ItCliInv:375 set < ITEM_PLAYER_EQUIP_SETS`,
`ItCliApi:1305 unlockIndex < ITEM_PVP_UNLOCK_COUNT`, `ItemCode:516 !count || code[count - 1] !=
ITEM_CODE_TERMINATOR`, `TrdCliSess:371 statusCode == TRADE_STATUS_OFFER_COUNT`,
`ChCliAttrib:338 (int)attribState->attribPointsAvail >= 0`. This is `CharPool.cpp:84` at scale, and
it is §4.12's lever with a stimulus aimed at it on purpose. (5) A partition of the 332 into
"content we have never reached" — 45 reach a guild, party, trade-session, mission, tournament, PvP
or hero subsystem our server cannot fabricate — against "reachable solo in Pre-Searing" against the
residue.

**[OBSERVED] 4.11g The honest negative, and it is the important half.** **This is a FORMAT oracle,
not a behaviour one.** Under §3 it joins the nine, not the three. It measures what Gw.exe build
38797 does with *our* bytes; it cannot say when ArenaNet's server sends an opcode, what values it
carries, or whether it is ever sent at all — which is the entire content of "never seen".
**Nothing here shrinks the 332; it renames them.** Beyond that: 8 of the 332 have no receive
handler in any readable table, so the only available observation is a refusal — a fact about our
imported schema, not about ArenaNet. **11 opcodes in 4 groups share a dispatch VA** with another
never-seen opcode: the client runs literally the same function, so the sweep cannot separate them
by effect. **90 of 332 share a UI msgId** with another never-seen opcode (45 msgIds; eight opcodes
on `0x100000B5` alone), so the msgId names the frame and not the message. The 45 state-gated
opcodes will return early or trip an existence assert, and the honest reading of that is "not
reachable in this configuration", never "dead". Panel *contents* need readout channel 4 or 5; the
binding alone does not read a price. And the origin rule bites: everything the sweep produces is
`origin: ours`, can never be pooled with the 22,524, and any opcode→effect table must carry
`origin` **per row** the way `content.py` carries provenance per row. §8.7 is its acceptance
criterion.

**4.12 [SURVIVES-WEAKENED] Assert-reachability sieve** — the client's crash surface as a partial
spec. The load-bearing inference is sound and twice demonstrated (`CharPool.cpp:84`,
`CharPool.cpp:98`). Its yield is a seventh of what the write-up implies: `msghandler.py --map`
reports **477 receive handlers read, 7 source files named, 62 distinct opcodes covered — 415 of
477 name nothing**, and the tool prints its own honest footer. **Read 477 as a floor** (4.11d).

Structurally, **a first function is 10–12 instructions and a span-local assert scan returns zero
for it by construction, so `--follow --depth 2+` is required** — and that conclusion is stronger
than the draft states while its exemplar list was wrong on three of six. The draft called
`0x009F`, `0x0168`, `0x00EE`, `0x00B0`, `0x006D` and `0x003C` "all identical shims". They are not:
`0x00B0`, `0x006D` and `0x003C` are true shims that post a UI frame message (msgIds `0x10000048`;
`0x10000031` + `0x10000032`; `0x10000067`), while `0x009F`, `0x0168` and `0x00EE` post no frame
message at all and call into real bodies of 1,044, 301 and 623 instructions at call depth 2. Say
"a 10–12 instruction first function", not "identical shims". The measured version of the claim:
**12 of 487 handlers reach an assert within their own first function, against 280 of 332
never-seen at depth 2 and 308 of 332 at depth 3.**

And **39.1% of the whole corpus (7,728 of 19,758) is `Array.h`/`List.h` container boilerplate, with
2,682 sites sharing the single expression `index < m_count`** — filter those before calling a row a
constraint. Its discriminator must be restated as **3 of 4**: `MIN_MOVE_SPEED` returns 0 sites and
`AgAgent:2366` is one of the 373 unreadable sites (an `fstp` scheduled into the idiom), so an
operator would see 3/4 and debug a generator that is fine. *(This is the technique that transfers
most directly to combat AI: a reachable assert is a constraint ArenaNet's own server satisfies, and
an AI-driving server must satisfy the same ones.)*

**4.13 [SURVIVES-WEAKENED] Client-as-comparator bisection** — separating a client LIMIT from a
server POLICY, which no volume of capture can ever do because ArenaNet's server never leaves its
own policy. Its exemplar is exact and reproduced, on the right denominator this time: **nine
`ITEM_CREATE_BAG` rows per connection on 12 of 12 connections — 108 rows, not the draft's "10 of
10" — capacities `20/9/12/25/25/25/25/25/42 = 208` slots.** The stronger form of the claim, and the
one the exemplar should carry: that capacity vector is **byte-identical on all twelve connections,
exactly one distinct capacity vector in the corpus**, while the other five fields differ per
connection. §10.3 names what the nine bags *are* and shows that 167 of the 208 declared slots are
account storage that is never once filled.

Three repairs: read the field **width** out of the `MsgFormatRecv` descriptor first — `0x013F`'s
capacity is `0x104`, i.e. **one byte**, so the range is 0..255 and at most 8 probes, and an 8-bit
field that must already express 42 **cannot be what limits the backpack to 20**, which
half-answers the question for free. Make the comparator's output the rebased `Pc:`/`Rt:` frame,
not the dialog's file:line, because 2,682 sites share `index < m_count` and two entirely different
bounds produce an identical line. And drop or restate the NPC-definition target: its field is a
dword and the corpus already spans 272..8077, so the bracket's floor is 8,078 and the search space
is 2^32.

**4.14 [SURVIVES-WEAKENED] Fixed-width in-place tape mutation.** Replaying ArenaNet's own recording
with one field changed is a real differential against a populated world, and the safety story is
inherited intact (`load_tape` refuses a byte-accounting mismatch, `rewrite_transfer` refuses a
non-loopback host, `stop_before_transfer` keeps the client off a real address). **But its own no-op
control is red today**, on the family it targets: `0x0161` fails to re-encode on 31 of 394 records,
so roughly one mutation in thirteen would be measuring our encoder. See §6.2.

### Tier 2 — live human minutes, bounded, human cadence

**4.15 [SURVIVES-WEAKENED] Single-variable equipment diff** (~10 min). One server-side input
changed per trial, no randomness in the loop, and a decisive negative either way: if both swaps are
silent, armour is client-side and the damage-formula fit keeps armour as a free parameter
permanently. The arithmetic on canon-12: **unnamed GAME_SMSG volume 30.33%, `0x009F` 1,242 =
5.51%, so naming it alone lands at 24.82%** (the draft's 29.27 / 5.56 / 23.71 are BIG-10).

**Four corrections, and one is the whole run.** `0x009F` has **21** distinct kinds, not 20 (chain-8
gives 20, which is where a "20" would have come from); `0x00A2`'s kinds are `{34,43,44,62}` (n=58)
and `0x00A3`'s are `{16,17,55}` (n=61) — a different vocabulary — and `0x00A0`'s are
`{4,20,50,60}` (n=74); kind 16 is `PROP_DAMAGE` and kind 34 is `PROP_HEALTH_ABSOLUTE`, both already
named in `agents.py`. The run-burning one: the proposed null ("an identical-stats swap must come out
silent") is unscorable because `0x009F` names **209** distinct agents and runs at **0.378 per 350 ms
idle window, present in 97 of 429 quiet windows (22.6%), up to 9 in one**. One swap has a
one-in-four chance of looking non-silent by luck. **Filter every diff to the player's own agent id**
— kinds 41/42 touch only 11 agents in 46 messages — repeat the identical-stats swap at least three
times, and either write `test_itemprobe.py` in the same commit or demote `itemprobe` from
"independent oracle" to "corroboration only".

*(The idle-window figures — 0.378 per 350 ms, 97 of 429 — are BIG-10 and have **not** been
re-derived on canon-12. §10's script step 3 collects a fresh 30-second quiet baseline precisely so
this null stops being quoted from an un-re-derived denominator.)*

**4.16 [BLACK-BOX #4, REFUTED AS WRITTEN, WORTH RUNNING REPAIRED] The merchant window** (~10 min).
See §10, where the epistemics are inverted and a second, falsifiable prediction is added.

### Tier 2 — added by the revision: the identification and salvage class

Nine of the thirty-nine techniques above work on the item **modifier vocabulary** over 394
records. None of them noticed that the game ships two buttons that make the server show its work on
demand. **Using an identification kit makes the server reveal a roll it has already performed, with
a client-visible ground truth in the same second, at zero combat and zero repetition. Salvage is a
second, genuinely stochastic server roll whose outcome space is bounded by the item's own visible
modifiers — the drop pipeline running backwards.** Both are what a person playing normally does, so
both sit inside the live-behaviour rule with room to spare.

The census first, because it is what makes the case.

**[OBSERVED] 4.16a The whole system is in the client and none of it is in the corpus.**

| question | answer | how |
|---|---|---|
| named identify/salvage opcode in `schema/messages.json` + `overrides.json` | **0**, of 16 named GAME_CMSG and 21 named GAME_SMSG | direct read of both files |
| assert expressions naming salvage | **0 of 19,758** | `asserts.py --grep "salvage"` |
| assert expressions naming identify | **3**, all `GR_TEXFLAG_TEXTURE_IDENTITY` / `MODEL_GEOMETRY_FLAG_RESERVE_TEX_IDENTITY_TRANSFORM` / `ITEM_COLOR_IDENTITY` | `asserts.py --grep "ident"` |
| salvage UI module in the client | **yes** — `P:\Code\Gw\Ui\Game\Inventory\InvSalvage.cpp`, one readable assert `InvSalvage:663 m_toolId` @`0x008E4105` | `asserts.py --modules` |
| a "tool" concept | **yes** — `InvItemInteractions:57 toolIndex < MAX_ITEMS_PER_TOOL` @`0x008E80A9`, `InvBag:576 itemTool != ITEM_TOOLS` @`0x008E6201` | ditto |
| how many tool kinds | **ITEM_TOOLS = 10**, from the guard immediate `cmp eax, 0xa` @`0x008E61F7`, on the return of the item→tool getter `0x00845A70` | `codescan.py --dis` |
| salvage/identify text in `Gw.dat` | **71 matches** over 26,705 plain records — string ids 2448–2523 (kit descriptions, the six refusal messages, the salvage-result template), 31618, 37315, 38525–38528, 44177–44178, 50580, 51162, 52058, 52136, 54207, 55334, 56417, 74699, 79885, 80232, 80743–80746, 87495 | `textrec.TextIndex` walk of all 99 files × 1,024 records |
| item-manipulation **c2s** opcodes in the corpus | **0 of 971** — nineteen opcodes: `0x0065 0x0066 0x0067 0x0069 0x006A 0x006B 0x006C 0x006D 0x0070 0x0072 0x0073 0x0074 0x0075 0x0077 0x007D 0x007E 0x007F 0x0080 0x0086` | see below |
| item **s2c** opcodes never seen | **17 of 30**, over 22,524 | `msghandler.py --map` + corpus (§6.4) |

The refusal strings alone are a specification of the server's own preconditions, in ArenaNet's
words: an item can be already identified, un-salvageable, equipped, in the weapon bar, in the
equipment pack, PvP, unidentified-and-therefore-not-yet-salvageable, or the attempt can be blocked
because the client is waiting to enter a mission. Every one of those is a server refusal our own
server must reproduce and currently has no notion of. *(These are cited by **string id and
paraphrase**. The text itself stays out of the tree pending §9.4's ruling, which covers this
extraction as well as the assert export and §4.9's 476 runs — and this is the shape §9.4 recommends
for all three.)*

**[OBSERVED] The instrument that names a c2s opcode without a capture, and what it says about item
traffic.** `studies/cmsg` named `0x0040 ROTATE_PLAYER` by enumerating the callers of the channel
send `0x007DCF00` and recovering the opcode immediate at each. Run to completion that is a general
instrument, and nobody had run it to completion: **174 call sites, 164 of the 194 GAME_CMSG opcodes
resolved to a send wrapper**, 9 sites carrying no recoverable small immediate. Nineteen of the
resolved opcodes are emitted by front-ends inside `P:\Code\Gw\Item\Cli\ItCliApi.cpp` whose asserts
name the arguments outright — and the assert text is the naming evidence, not a guess:

| c2s | front-end | ArenaNet's own argument names | wire layout | live |
|---|---|---|---|---|
| `0x0065` | `0x00847360` | `itemTable.Get(itemId)` | `dword` | 0 |
| `0x0066` | `0x008473B0` | `itemTable.Get(sourceItemId)`, `itemTable.Get(targetItemId)` | `dword, dword, byte` | 0 |
| `0x006A` | `0x00847540` | `dstItemId`, `dyeItemCount > 0`, `dyeItemCount <= ITEM_DYE_MIX_MAX` | `dword, array32` | 0 |
| `0x006C` | `0x008476A0` | `itemTable.Get(srcItemId)`, `itemTable.Get(dstItemId)` | `dword, dword` | 0 |
| `0x0077` | `0x008479B0` | `targetInventoryId`, `sourceItemId`, `targetItemId` (+ three `Get` checks) | `word, dword, dword` | 0 |
| `0x007F`/`0x0080` | `0x00847BC0` | `upgradeItemId`, `targetInventoryId`, `targetItemId` | `byte, dword` / `word, dword` | 0 |
| *(twelve more)* | | bags, equip slots, colours, PvP templates | | 0 |

**Every one is zero.** The 971 c2s messages we hold are movement (`0x003D` 430), instance and
character-create chatter, two kills' worth of `0x0026`, and nothing that touches an item.

Three of these carry two item ids, which is the shape of *use tool X on item Y*, and one carries two
ids plus a byte, which is the shape of *use tool X on item Y, choosing option N*. Which is identify
and which is salvage **is NOT FOUND** — no assert names either, and the salvage UI does not call a
send front-end directly (checked: no call from `InvSalvage`'s VA range into any of the 98
front-ends; the three inventory-side callers of `0x006C` and the two of `0x0077` sit in the
drag-and-drop region `0x008E9640`–`0x008EA871`). One click names it. Nothing else can.

**4.17 [SURVIVES] Identification: an unidentified item is a sealed sample of the generator**
(~3 human minutes)

**Target.** Item generation: whether the drop record the server sends already contains the full
roll, or whether part of it is withheld until asked for. This is upstream of §4.2, §4.3, §8.4 and
§8.5 — all four are computed over records whose completeness has never been checked.

**Idea.** An unidentified item is a roll the server has already made and is refusing to show. The
refusal is one click deep and the click is free.

**Instrument.** `toolkit/harness/livesession.py` for the capture, `marks.py` (§10.5) for the clock,
`toolkit/authsrv/tape.py` + `toolkit/schema/codec.py` to decode, and
`toolkit/clientscan/itemprobe.py` — which already reads the running client's item record at
`rec+0xc` — as the second witness.

**Observed, and it is the finding this technique starts from.** The client's item-name builder at
`0x009236B0` contains

```
0x009236D9  test dword ptr [esi + 0x1c], 0x800000     ; bit 23
0x009236E3  je   0x00923708                           ; clear -> ordinary base name
0x009236E5  push 0x995                                ; string id 2453 = the word "Unidentified"
```

nearest assert `ItemName.cpp:953 m_baseName`. **Bit 23 is the unidentified flag**, which resolves
§4.2's six one-bit violations. 11 of the 16 unidentified records arrive inside the 2.0 s
instance-load dump.

**Inferred, and flagged as such.** That wire `field[8]` and the client's item-flags dword are the
same 32 bits is **UNVERIFIED**. Two circumstantial legs: `InvSalvage` tests bit 19 of the item
record at `item+0xc` (`0x008E437C test dword ptr [eax + 0xc], 0x80000`), and bit 19 of wire
`field[8]` partitions the corpus exactly into the 11 records that carry no modifier list and the
383 that do; and `ItemName` tests bits 0, 21, 23 and 26 of its dword, of which 0, 21 and 23 are live
on the wire and 26 is never set in 394 records. **`itemprobe.py --dump` against a running client
settles it in one command** and should be run before this technique is quoted.

**Prediction, stated first.** Identifying one unidentified item will (a) emit exactly one c2s
message on one of `0x0065`, `0x0066`, `0x006C` or `0x0077`, naming the kit and the item; (b) draw a
server reply containing **`0x0162`** — layout byte-identical to `0x0161`, zero occurrences in
22,524, and whose handler at `0x00846E50` is the *only* long-record handler that first looks the
item up in the client's own table and calls the removal helper `0x008488D0`
(`ItCliItem:317 m_itemArray[itemId] == item`, then `m_itemArray[itemId] = 0`) before rebuilding it.
`0x0161` does not. **`0x0162` is REPLACE and `0x0161` is CREATE, read out of the client's code
rather than assumed** — and `0x015F`/`0x015E` are the same pair for the short record (§6.4).
(c) The replacing record will have bit 23 of `field[8]` clear.

**The discriminating observation, and it is the whole point.** Diff the pre-identification `0x0161`
against the post-identification `0x0162` for the same item id. Either the modifier array grows — in
which case **the server withholds the roll until asked, every drop record in the vault is
incomplete, and §4.2/§4.3/§8.4/§8.5 are all computed over censored data** — or it does not, in which
case identification is a pure client-side veil, **every drop we have ever captured already contains
the full roll**, and the item-generation arc needs no identification step at all. Both outcomes are
large and the document currently assumes the second without having checked it.

**Null control that can fail, and it has already been run.** If the server withholds mods, the 16
unidentified records should carry systematically fewer modifier words than their identified
siblings. Stratified by `item_type` and permuting the bit-23 label 20,000 times within each
stratum: observed total 25 words over 16 records (mean 1.562), **P(total ≤ observed) = 0.0921**.
Inside the 6 `(type, model)` groups where both states appear, the cardinalities and identifier sets
are *identical*. So the corpus **cannot** settle it — which is the honest statement, and it is
exactly why the click is worth three minutes. State this p-value beside any claim about record
completeness rather than assuming either branch.

**Cost.** ~3 minutes: obtain a kit, open the bag, identify three items one at a time with a mark
before each.

**Identifiability limit.** This names the channel and settles completeness. It does **not** give a
per-item-type probability of any modifier — three identifies is n = 3 and the ranking in §7.1
applies unchanged. Never emit a percentage from it.

**Novelty.** The pass produced thirty-nine techniques and none of them proposed making the server
answer a question. Every one of the sixteen survivors either re-reads bytes we already have or
watches traffic we did not cause. This causes traffic, deterministically, once.

**4.18 [SURVIVES-WEAKENED] Salvage: the drop pipeline running backwards, one click at a time**
(~4 human minutes)

**Target.** A server-side stochastic decision with a *bounded, client-enumerated* outcome space —
the only one in the game that is both random and small enough to observe.

**Idea.** Salvage rolls: the item breaks or it does not, and something comes out. Unlike a drop, the
outcome space is not the whole item catalogue; it is the item's own modifier list plus a
crafting-material formula, both of which the client already holds. An Expert kit makes the client
*name its own choice set in the UI*, which is a labelled decomposition of exactly the words §5.2 and
§8.5 are about.

**Instrument.** Same as 4.17, plus `codescan.py` for the client-side half, which is where most of
the value already is.

**Observed — the destroy chance is computed by the client, and it is readable today.** The site that
formats string id 38528 (the "…% chance of destroying…" template) is inside `InvSalvage`, at
`0x008E4837 push 0x9680`, and the number it pushes is computed immediately above it:

```
0x008E47A6  push 0x2d / 0x2e            ; two lookups into the 0x2C-byte track table at [ctx+0x2c]
0x008E47F4  add  ecx, [ebp+8]           ; r = rank(45) + rank(46)
0x008E47FC  fild ...                    ; r as float
0x008E4814  fmul qword [0x00A83D00]     ; 0.03
0x008E481A  fsubr qword [0x00945B40]    ; 0.5 - 0.03*r
0x008E4820  fmul qword [0x00945B50]     ; * 100
0x008E4826  call 0x005AEBB0             ; round
0x008E482B  sub esi,6 / neg / sbb / and ; keep it only when the tool kind == 6
```

**`destroy% = round(100 · (0.5 − 0.03 · (rank₄₅ + rank₄₆)))`, displayed only for tool kind 6** — one
of the ten `ITEM_TOOLS`. Two ranks summed is consistent with string id 52058, which says a title
track reduces the chance of destroying an item on salvage. **This is a genuine probability in the
item pipeline that is fully recoverable from the binary with no live play at all**, and it is the
only one this document has found. Label it carefully: the constants and the arithmetic are OBSERVED;
that *the server rolls against this same number* is **RECONSTRUCTION**, because the client only
renders an estimate and the roll happens on the server. §2.7's caveat applies here with more force
than it does to the PRNG, and it belongs at the call site.

**Observed — the outcome space is enumerable and it is a modifier lookup.** `ItemCliGetComponents`
at `0x00845240` (asserts `ItCliApi:410/411/412 ptr / ptr->IsDetailHigh() / components`) calls
`0x008487B0` twice with identifier `0x24E` and two sub-selectors. That callee is the client's
modifier-word lookup:

```
ecx = item->modifiers            ; [item+0x10]
loop: w = *ecx
      if w == 0xC0000000: return default          ; ITEM_CODE_TERMINATOR
      if ((w >> 20) & 0x3FF) == wanted: return w & 0x3FFFF
      ecx += 4
```

Three things fall out, and two of them are gifts to §8.5. It is a **second, independent witness** for
`id10 = (w >> 20) & 0x3FF` — the evaluator at `0x00923A40` is no longer the only one saying so. It
names the list terminator, which is `ItemCode.h:516 !count || code[count - 1] != ITEM_CODE_TERMINATOR`
from the other side. And it returns the argument as **the whole low 18 bits**, `w & 0x3FFFF`, so
§5.2's "ten-bit argument plus a separate low byte" is one 18-bit field and the skip flag at bit 18
sits immediately above the payload mask rather than inside it.

**And the corpus corroborates, in a way it could have refused to.** Over all 990 canon-12 modifier
words: **0 equal `0xC0000000` and 0 have `tag2 == 3`** (histogram `{0: 325, 2: 603, 1: 62}`), so the
terminator is stripped by the wire encoding and re-supplied by the client. That is the failable
control §8.5 has been missing.

**Observed — salvage reaches `ITEM_FORMULAS`.** `InvSalvage` reads a per-item `u16` at `item+0x48`
(getter `0x00845550`, `ItCliApi:518 ptr`) and compares it to `0x5DD` = **1501** at `0x008E43BF` as
the "no formula" sentinel. That is a second independent witness for §2.4's bound, from a completely
different site than `ConstItem:9131` @`0x005A9154`. A wire candidate follows immediately: **`0x0161`
field[6] is a perfect function of `(item_type, model_id)` — 59 of 59 groups, zero violations** —
with 11 distinct values, maximum **487**, never ≥ 1501, and non-zero on 69 of 394 records. If
field[6] is the formula index, §2.4's dead end has a labelled entry point.

**Prediction, stated first.** (1) Salvaging a plain item will emit one c2s message on one of the
two-item-id opcodes and draw a `0x0162`-or-`0x015F` replace for the *kit* (its remaining uses
decrement) plus a create for the produced material. (2) An **Expert** salvage on an item that
carries modifier identifier `0x24E` will additionally raise a choice dialog whose entries are read
out of the item's own modifier words client-side, no server message required — the switch at
`0x008E4610` scans exactly three slots at `[this+0xC/0x10/0x14]` before branching to string id
44177. (3) The chosen option travels as the **byte** in `0x0066`'s `dword, dword, byte` layout,
which is the only item opcode shaped like a choice.

**Discriminating observation.** A salvage outcome that removes one specific modifier word is a
*labelled example of §5.2's decomposition*: we know which `id10` disappeared, we know the
`w & 0x3FFFF` payload that went with it, and we know the material and quantity that came out because
**string id 2519's template interpolates a count, an item name and a source name in that order** —
paraphrased rather than quoted, per §4.16a's own id-plus-paraphrase rule and §9.4's refusal, which
this document has to obey in its own prose too. Three of those bind the identifier space to real
names from ArenaNet's own server rather than from an unlicensed catalog.

**Null control that can fail.** Salvage the *same* item type twice with the same kit. If both
attempts produce identical material and quantity, the outcome is deterministic and the "second
stochastic roll" framing is dead — say so and demote this to a naming exercise. If they differ,
record both and do not compute a rate from n = 2. Second control, free and already run: the corpus
contains **zero** words with `id10 == 0x24E` in all 990, so **no item we have ever captured carries
an upgrade component** and the Expert dialog would be empty for every one of them. That is a precise
statement of what the vault cannot support and what one session adds.

**Cost.** ~4 minutes for three salvages, each preceded by a mark.

**Identifiability limit, and it is the sharp one.** Three salvages give three Bernoulli trials
against a client-displayed 50%-at-rank-0 chance. The exact permutation floor from §5.1 applies
verbatim: at k = 3 the smallest attainable p is 1/C(3,d), so **no salvage-destroy rate is estimable
at any n this protocol can authorize.** The value here is the *mechanism* — which opcode, which
fields, which outcome space, and the client-side formula — not a probability. A proposal that asks
for more salvages to reach significance is asking for the grind and is refused by §7.1's second
wall.

**Novelty.** §5.2 killed four techniques for reasoning about the modifier vocabulary from offline
agreement between our own components. This is the only proposal in the document that gets
ArenaNet's server to *label* a modifier word for us.

---

## 5. The graveyard — twenty-three refuted techniques, and what killed each

Kept so the next session does not propose them again. **Nine died to their own stated null
control, executed for the first time.** That is the single most transferable lesson in this
document: a proposal that names its own kill condition is doing the right thing, and running that
condition *before* costing the work is nearly free.

Two denominator caveats ride over the whole section and are stated once here rather than buried.
The graveyard's figures were each measured once, by the lens that killed them, mostly on BIG-10 or
on `chain()`'s eight connections. Where §1.9 shows the denominator moved, the entry says so
inline. **Two figures in particular have not been re-derived on canon-12 and must not be quoted
until they are: §5.1's 22.5% merge rate and §5.2's "exactly one of 151".** The *verdicts* do not
depend on them — each was killed by a control that is a property of the technique, not of the
corpus size — which is why the entries stand while those two numbers are flagged.

### 5.1 Killed by their own stated control

| technique | the control, and what it did |
|---|---|
| **Flush-boundary transaction reconstruction** (`segstream.py`) | "A grouper keyed on timestamp must produce a strictly coarser partition; if they agree everywhere the technique must be abandoned." **The two partitions are identical on all twelve connections**, and zero adjacent segments share a timestamp — `wirecapture.record()` calls `perf_counter` once per segment, so `cmsgstream.timed` already returns the segment partition. Its own merge detector then fires on **22.5% (1,295 of 5,756 segments span ≥ 2 ticks) — a BIG-10 figure; the canonical segment count is 5,786 over twelve connections (chain-8 is 5,728), and the 22.5% and the 5,600 tick-bearing segments must be recomputed over 5,786 before either is quoted again.** And its discriminator is an n = 2 selection artifact: scored over all tick-bearing segments, **four of the eight named opcodes sit on the opposite side of the tick** from the claim. Only `0x00F1` (406:1 pre-tick) and `0x0020` (9:226 post-tick) survive. |
| **Reply-ratio partition** (which c2s messages the server answers) | "If a shuffle-beating reply falls out of `0x003D MOVE_SET_HEADING` too, every classification is spurious." **Four fall out.** Running the stated rule over every opcode with n ≥ 3 classifies **17 of 18 as RPC**. Worse, both "predictions stated before I ran it" are already committed verbatim in `schema/overrides.json`'s `why` fields for the very entries the technique reads for names — one witness counted twice, in its purest form. The idle floor does not reproduce either (429 windows and 6 hits, not 671 and 0). |
| **Chao1 completeness certificate as a stopping rule** | Both calibration controls reproduce and are worth keeping (agent class tags: f1 = 0, unseen 0.0; opcodes: f1 = 2, f2 = 11, unseen 0.18 against a truth of 339). But **the thing it consumes does not exist**: the only species with > 1 kill has 2 kills and 2 drops of different models, so f2 = 0 and classic Chao1 is **undefined**. The scheduler it justifies would spend live hours feeding an estimator undefined at the n those hours produce. |
| **Anti-farm decay as a mandatory pre-test** | An exact within-session permutation test on k kills of which d dropped has minimum attainable p = 1/C(k,d). The largest session has **2 kills → min p = 0.50**; pooled over all 4 → **0.167**. It cannot reach 0.05 on any data that exists, and making it *mandatory* creates standing pressure to reach the n at which it has power — which is the grind. **Its two infrastructure observations are real and must be kept: expose `t0`, and build `marks.py`.** Both are now §7's items (1) and (3) and §10.5's specification. |
| **The comb** (server step period from a periodogram of `0x001E` deltas) | "R_wire must sit well below R_server, or the peak lives in the capture path." **R_wire ≥ R_server on 6 of 8 tapes.** Its second control is mathematically vacuous — `R(p)` depends only on the delta multiset, so shuffling changes nothing (measured bit-identical). And the marginal kills it before any statistic: **delta = 1 ms occurs 332 times (4.8%)**, 18.5% of deltas are below 16 ms, and the estimator's argmax over [1,120] is **p̂ = 1.000 ms with R = 1.000**, the integer lattice. |
| **The residual channel** (pricing a server-side event in server milliseconds) | Predicted a bimodal (delta, payload) joint with a positive-correlation work branch. **Measured correlation per tape: +0.012, −0.028, +0.043, −0.051, +0.015, −0.029, +0.156, −0.036.** There is no work branch. And the discriminator could not have discriminated anyway: a longer interval accumulates more events under *both* hypotheses. `r`'s total range is 5.6–47.2 ms against tick deltas spanning 1–520 ms. |
| **Flush shape as context** (naming `0x009F`'s kinds by what shares its step) | "Kind 36, the most common at 491, is predicted **not** to concentrate; if it does, every other result is void." **Kind 36 is in a CREATE flush 98.6% of the time.** Void by its own rule. The CREATE channel is saturated (base rate 0.1465, so max ratio ×6.83, and four kinds sit at exactly ×6.83). And the context labels are not independent of the channel: COMBAT is defined as `0x00A3`/`0x00A0`, which are `0x009F`'s own targeted twins. `genericvalue.py` already reads all 67 ids' dispatch arms out of the client. |
| **Closed-form sieving** (published XP formulas as residue lattices over unnamed opcodes) | Ran as written: the XP lattice catches **zero** columns at the support threshold, and 200 scrambled lattices of identical cardinality catch zero too, so it does not beat p95 at **any** threshold. The lattice is also mis-counted 3× (54 members, not 18) and the "pre-registered refutation" is arithmetic on data quoted two paragraphs earlier in the same proposal. |
| **Free repeated-measures on the server clock** | Predicted the 2.00 s windows would land tighter in server-tick time than on the wire. **Measured: wire sd 7.0–13.7 ms; SVT sd 120.7–256.2 ms — 15–19× worse.** It was derivable before any code: the technique's own limit section says SVT cannot resolve finer than one flush (~60–80 ms explorable), and the wire spread it promised to beat was already ±60 ms. Quantizing by a step coarser than the existing error cannot tighten it. |

### 5.2 Killed by a field decomposition the wire or the binary contradicts

- **German-tank support-boundary estimation of roll ranges.** There is no roll to bound in most
  cells: **11 of 18 `(item_type, model_id)` cells carrying `0xA488` have exactly one distinct
  `(hi,lo)` pair.** Its headline p-value (3.9e-4) does not survive its own deduplication
  (effective n = 11, giving 0.183). And its free-growth claim is refuted from the wire: outpost
  crowding does not stream item records (223 `play` creates → 25 records; 3 creates → 36), because other players' equipment arrives on `0x006E`, whose field list has **no
  nested_struct at all**. Stronger, from a direction the draft did not use: the two families describe
  **disjoint item populations** — across `:60935`, `:62994` and `:61193` there are 478 distinct model ids in
  `0x006E` and 107 `0x0161` declarations, and the intersection is **0 of 107**. Crowding is also measured not
  to drive tuples: the busiest outpost (`:61193`, 223 `play` creates) yields 22 tuples while the quietest
  explorable (`:62994`, 10 `play` creates) yields 30. Of the **170** canon-12 `0xA488` words, "exactly one was
  produced by a monster drop" was computed over chain-8's 151 and **has not been re-derived over 170**.
- **Modifier-word "mod-8 stride" lattice**, and **modifier-word grammar induction** built on it. Two proposals
  independently read `identifier = w >> 16` and concluded the low three bits are structurally zero, so the
  vocabulary is 8× smaller. ArenaNet's evaluator at `0x00923A40` says otherwise: `tag2 = w>>30`, a **skip flag at
  bit 18**, `identifier = (w>>20) & 0x3FF` (a 10-bit bitfield — four low bits discarded, not three), `argument =
  (w>>8) & 0x3FF` (**ten** bits, not eight), plus a separate low byte — and §4.18 adds a **second, independent
  witness** at `0x008487B0` that reads the argument as the whole low 18 bits, `w & 0x3FFFF`, so the "ten bits
  plus a low byte" is one 18-bit field with the skip flag immediately above it. So the mod-8 "invariant" is
  exactly *"the 10-bit argument never exceeded 255 and the skip flag was never set"* — re-measured here over all
  394 canon-12 records: **the HIGH HALF is 8-aligned in 990 of 990 words (`(w >> 16) % 8 == 0`), arg10 max 120,
  0 words above 0xFF, bit 18 set 0 times, bit 19 set 877 times, 18 distinct identifiers.** State the alignment on
  the high half and nowhere else: **only 763 of 990 whole words are congruent 0 mod 8**, so the draft's
  "990/990 words congruent 0 mod 8" is literally false and would have been refuted by anyone who ran it. The
  refuted reading was `identifier = w >> 16`, and it is that derived quantity — not the word — whose low three
  bits are always zero, which is exactly why the refutation lands where it does. (BIG-10 is 858/858 on the high
  half with 642/858 whole words and bit 19 at 770; chain-8 is 598/598 on the high half with 397/598 whole words,
  575, and only 17 identifiers — so the 877 and the 18 pin the denominator.) A branch on an always-zero bit is dead
  code, so the client itself says the low bits carry meaning. And Py4GW_Reforged's catalog — the designated
  verification target — contains **5 non-8-aligned ids** (`0x2532, 0x27e9, 0x27ea, 0xa0fb, 0xa532`), four of them
  base+1/+2/+3 neighbours of ids that *are* in the set. The "ceiling of 137 renderable symbols" is also wrong:
  the switch's non-default domain is **158 cases** over an index that has discarded 4 argument bits and 2 flags,
  i.e. up to ~10,112 distinguishable wire identifiers.
- **The client as a decompiler for the modifier vocabulary.** Same premise (`ITEM_ATTRIBUTES` index, bound 559),
  same refutation: the **smallest observed high half is `0x23a8` = 9,128**, more than sixteen times past 559, and
  ArenaNet's server sent all 18 to a real client with no crash. Its readout is also circular — `0x0161` field[12]
  is an *encoded* reference the server supplies (**44 distinct values on canon-12**, commonest a single code unit
  U+2186 at n=110; chain-8 gives only 33 distinct, so 44 pins the denominator too) — and reading it back out of
  the item record returns what we put in.
- **The client as an EQUIVALENCE oracle** (partition stages by whether an illegal value crashes). Its named
  discriminator does not exist. Both identifier-switch defaults are `ja 0x0092641A`, which is the **loop-continue**
  — an unknown identifier is silently skipped. `ItemName:1529`'s block has exactly **one** inbound branch in
  `0x00920000-0x00930000`, guarded by `cmp ebx, 0x2C` on the **argument**. Worse: **2 of the 18 identifiers
  ArenaNet's own server sends (59 of 990 words) land on jump-table entries that are the loop-continue**, so
  "accepted, renders the same" is the client's answer to both a legal and an illegal symbol. The instrument is
  degenerate on exactly the axis the technique is built around.
- **Assert-named property binding** (the deliberate-zero probe). Over the client's *entire* agent-property setter
  surface there is not one naming assert: `asserts.py --at 0x008129EF --span 0x4E0` (all 47 int case bodies)
  returns **2 sites, both `sourceAgent < 5`**; the 14 float case bodies return **0**; both store switches return 0.
  It also aims at the wrong dispatcher (`0x00818210` is the float store; `0x009F` never reaches it), silence is
  near-unobtainable (`genericvalue.py`: exactly **one** id of 67 is acted on by no switch), and the headline
  prediction has already been run and came out the other way — `studies/enemy/PLAN.md` §6g got
  `CharPool.cpp(98) range > 0`, a generic clamp bound, and the meaning was read off *behaviour*. Its second
  prediction is printed for free by `genericvalue.py` in one command.
- **Rolled item properties as the generator running forwards.** Its null cannot fail: `field[11]` is **1 in 394 of
  394**, so it has zero variance inside every possible partition, including a broken one — and it is itself part of
  the proposed key. Its naming is refuted from the wire: the equipment requirement is not `field[9]`, it is the
  argument of modifier `0x2798`, and two type-27 items share `f9=47` while their `0x2798` low bytes differ.
  *(field[9] is not nothing, though — §10 shows it is a per-instance rolled gold value with 84 non-zero
  observations, which is a different claim from "the requirement".)*
- **Dialog-code lattice sweep** (`0x003B`'s low byte as the held-and-varied variable). The "NPC dialog root" is a
  **quest id**, and the shift the draft published was wrong: the quest id is **`(code >> 8) & 0x0FFF`**, not
  `code & 0x0FFF`. Over canon-12 there are 22 `0x003B` selects and 16 `0x0012` requests; pairing each select with
  the next request within three client messages gives 17 pairs, of which **14 agree under `(code>>8)&0xFFF` and
  0 agree under `code & 0xFFF`**. Worked: `0x85B603 → 1462`, `0x80DA01 → 218`, `0x803E01 → 62`. The three
  exceptions are all a turn-in immediately followed by a *different* NPC's offer (`0x805007→218`,
  `0x805007→222`, `0x80DE07→86`), so the rule is not violated — the pairing is. **The low byte is the dialog
  OPTION** (0x01, 0x03, 0x07), which is the axis §10's rider should vary. The service families OR in
  `0x0A/0x0E/0x0F/0x10 000000` — a merchant selection changes the **high** byte, which the design holds fixed,
  and **all 22 captured selects carry high byte 0x00**, so a service-family dialog has never reached the wire.
  And its repeat control is unsatisfiable on quest NPCs, because the codes are a one-way state walk (offer at
  27.679, accept at 28.147, turn-in at 46.765). *Repairable by changing the axis — see §10's script, steps 6–7.*
- **Price-vector invariance from one merchant window.** It rests on three opcodes that are **0 of 22,524** and
  labels their bytes OBSERVED. `schema/messages.json` carries their layouts but names nothing and its own
  provenance header calls it one lineage. Its controlled variable is three variables (selling changes gold *and*
  inventory *and* the quoted vector). *Repairable by inverting the epistemics — see §10.*

### 5.3 Killed by a denominator, a key or a graph that does not exist

- **NNLS additive pool decomposition across species × zone.** The route is `148 → 146 → 164 → 146` in both
  sessions, and **all 233 `mon1` creates are in map 146** — maps 148 and 164 carry zero, and this holds identically
  on all three denominators. The species-zone incidence graph is a single column, so species and zone are
  perfectly confounded at any n. Its COLLINEAR REFUSAL control would fire on 100% of columns. **Separate policy
  note: the write-up says scipy "is not available and not needed". It IS available on this machine** (numpy 2.4.4
  and scipy 1.18.0 both import), so an agent would ship `from scipy.optimize import nnls`, break the stdlib rule
  silently, and only fail on a bare machine — the exact `gwdat.py` failure mode.
- **The navmesh as a spawn-rule oracle**, and **navmesh-normalised spawn density.** One leg is confirmed
  spectacularly — **1,064 of 1,068 live wire positions (99.6%) land inside a walkable trapezoid of ArenaNet's own
  mesh, 233/233 for `mon1`** — but it is 99.1% for `play` too, so it tests the pipeline. Then: `areatable.py`
  returns **file_id = 0 for maps 146, 148 and 164** (only 157 of 888 rows carry one), so the only map-id→file-id
  join in the repo is `content/maps.toml`, sourced from an upstream that grants nothing. All three maps resolve to
  **one** mesh spanning 39,936 × 49,152 units while the observed points occupy ~18% of it, so the uniform null
  scatters across a continent and every clustering statistic beats it for free. And "agents created within the same
  second" is co-visibility from the player's position, which is what the mutual-LOS statistic tests. Density is
  60% burrow re-creates, and at n = 15–22 distinct agents the factor-of-2 prediction passes 94% of the time when it
  should and **51% of the time when it should not**.
- **Repeat-instance differencing on `0x0056` definition sets.** Premise false: only **71 of 126** `0x0056` arrive
  at t ≤ 1.0 s, and on the two long map-146 visits only **6 of 28** — it is a streamed, arrival-driven message
  carrying exactly the visibility confound it was chosen to avoid. The four map-146 set sizes are 11, 28, 28, 11
  and are **rank-ordered by connection duration** (134 s, 185 s, 29 s, 13 s). Reporting the symmetric difference of
  20 as "the roll's arity" would publish a measure of how long the operator stood around. (`0x0056` = 126 with 71
  at t ≤ 1.0 s is identical on all three denominators.)

---

## 6. Corrections this pass made to its own inputs

Four of these were found by skeptics. **Two were found in skeptics**, which is the point of writing them down.
The revision pass then found two more **in the critic**, which is the same point from one level further out:
§1.2's mid-stream-capture reading and §1.5a's `band` count are both corrected above, from the artifacts.

### 6.1 [OBSERVED] A refutation that rested on a mis-decode — and the finding it was suppressing

The cross-system skeptic refuted "definition-slot block archaeology" on the ground that *"slot 1434 → health 8
appears exactly once… there is ZERO cross-capture, cross-instance or even cross-agent repeat of any slot→health
pair anywhere in the corpus"*, reading the dying agent 38's create `field[2]` as `0x2000053f`. Re-decoded here over
all 12 connections with the field indexing checked against `agents.py`'s own builder:

```
PROP_HEALTH_MAX (0x009F property 42), 28 rows over 12 connections
  20260807T143055 :62994 t=18.169  agent  38  f2=0x2000059a slot 1434 'mon1'  HP_MAX=8
  20260810T235916 :61624 t=33.770  agent  43  f2=0x2000059a slot 1434 'mon1'  HP_MAX=8
  20260807T143055 :64103 t= 6.949  agent  40  f2=0x20000542 slot 1346 'mon1'  HP_MAX=96
  20260810T235916 :49163 t=14.483  agent 278  f2=0x200005a2 slot 1442 'mon1'  HP_MAX=40
  20260810T235916 :49163 t=20.292  agent 278  f2=0x200005a2 slot 1442 'mon1'  HP_MAX=40
  … 23 further rows, all the local player
```

**Slot 1434 yields health 8 in two different captures, three days apart, on two different characters, two
different connections, two different agent ids.** The definition slot **is** a stable server-side table key
across sessions, n = 1 pair — plus one within-connection repeat (slot 1442, same agent, 5.8 s apart, both 40).
The skeptic's REFUTED verdict on that ground is overturned; its *other* grounds (the name join is blocked, the
level→health fit is unreachable at n = 4) stand and are independently confirmed.

This is the failure mode CLAUDE.md already names — *"one skeptic's refutation rested on a file that does not
exist in the tree it read"* — arriving from the other side. **A refutation is a measurement and gets the same
scrutiny as the claim.** §7.6's Reforged caveat rides on every number in that table.

### 6.2 [OBSERVED] `toolkit/schema/codec.py:202` corrupts every encoded string on the wire, and it is one number

`string16` decodes as `raw.decode("utf-16-le", "replace")`, so GW's encoded-name code units in the surrogate
range become U+FFFD and are unrecoverable. Measured over canon-12: **133 of 22,524 messages (0.59%) do not
re-encode byte-identically**, none of them differing in *length* — they differ in bytes.

| opcode | fails / total | | opcode | fails / total |
|---|---|---|---|---|
| `0x004C` | **40 / 40** (100%) | | `0x007A` | 6 / 13 (46.2%) |
| `0x0161` | **31 / 394** (7.9%) | | `0x009B` | 4 / 280 (1.4%) |
| `0x0080` | 19 / 28 (67.9%) | | `0x0054` | 2 / 40 (5.0%) |
| `0x005D` | 12 / 50 (24.0%) | | `0x0049` | 1 / 10 (10.0%) |
| `0x0056` | **9 / 126** (7.1%) | | `0x00A5` | 1 / 2 (50.0%) |
| `0x007E` | 7 / 41 (17.1%) | | `0x00F3` | 1 / 27 (3.7%) |

Worked example from a real `0x0161`: original bytes `01 DE` (u16 `0xDE01`, a low surrogate) re-encode as
`FD FF`. The draft's list was short by seven opcodes; the five it named (`0x004C`, `0x0161`, `0x0080`,
`0x005D`, `0x0056`) are **111 of the 133** on canon-12. **105 is those same five on BIG-10**, where they
are 105 of 127 — a BIG-10 numerator quoted against canon-12's denominator, which is §1.1's rule broken
inside the section that exists to fix denominators.

**The 133 messages that fail to re-encode are exactly the 133 that carry U+FFFD after decode** — the same set,
opcode for opcode, with no exceptions in either direction. So the draft's "25 of 340 for round-trip and 31 of
394 for U+FFFD" was never two facts; it was one fact on two denominators, and on canon-12 it is **31 of 394**
both times. The control that proves the reader is measuring the same thing the draft measured: restricted to
the two big captures the same walk returns **127 of 22,137** with the draft's exact per-opcode split, and
restricted to `chain()`'s eight connections, 117 of 21,543.

#### 6.2a [OBSERVED] FIXED 2026-08-11, and it was hiding a second bug

`string16` now decodes and encodes with `surrogatepass`, and **22,524 of 22,524 canon-12 GAME_SMSG re-encode to
ArenaNet's own bytes**, with zero values carrying U+FFFD. Both figures come from one reader running the same
loop over both codecs: **133 → 0**, per-opcode dict identical to the table above, 0 length differences.
`toolkit/schema/test_codec.py` sections 5 and 6 pin it (floor 18 → 27; suite 50 of 50 green).

**The second bug could not fire until the first was fixed.** The encoder wrote `len(s)` as the wire count, and
`len(s)` counts *Python characters* — a valid surrogate PAIR is one character occupying **two** code units, so
the count went out two bytes short of the data that followed it. That is not a lossy field, it is a **desync**:
the next message frames from inside this one. Under `replace` it was unreachable, because U+FFFD is one unit
and one character. The count is now derived from the encoded bytes, so the two cannot disagree, and the check
is on the *following* message — which is where the damage lands.

**And §8.1's own sabotage control was insufficient, which the test found and this section records rather than
quietly fixing.** The criterion as written asked that a mutated neighbouring field read back mutated while the
string survived. That catches a message-level byte cache. It does **not** catch the sabotage §8.1 names by
name — a decoder that stashes the original bytes *on the value object* — because mutating a neighbour leaves
that stash untouched, so it passes every clause. What separates them is **construction**: a value built from
raw code units that was never decoded has no stash to replay, and a naive encoder raises `UnicodeEncodeError`
on it. Section 5 therefore builds one and requires the exact bytes out, with the naive encoder's raising as the
proof the input discriminates. §8.1 below carries the corrected control.

This is not cosmetic. It **blocks two techniques outright** — tape mutation (§4.14: its no-op control is red on
the item-create family it targets, so one in thirteen mutations would be measuring our encoder) and every name
join through `0x0056` field[9] or `0x0161` field[12]. It does **not** block §4.11's sweep, which uses the encode
side only. Fix `string16` to carry raw code units (a bytes-backed type, or `surrogatepass`) and re-run the
control to green.

### 6.3 Smaller corrections carried forward

- **[OBSERVED]** `agents.py:57-62` comments `WORLD_CREATE_AGENT`'s kind as "0 item, 5 player, 9 NPC", citing no
  source. The wire carries a two-level nesting: `field[3] ∈ {1,2,3,4}` and `field[4]` cross-tabulating as
  `{(1,5):366, (1,8):25, (1,9):560, (2,1):94, (3,0):11, (4,0):12}`. Ground items are `field[3]==4` (12 of 1,068).
  "kind 0 == an item on the ground" remains **UNVERIFIED** — the only source is that unattributed comment.
- **[OBSERVED]** `0x013F ITEM_CREATE_BAG` is not an item event. Nine rows per connection, in the load burst, on
  **12 of 12 connections (108 rows)**, never again. §10.3 names what the nine bags are and shows that 167 of the
  208 declared slots are account storage that is never once filled.
- **[OBSERVED]** `PROP_HEALTH_MAX` fires **twice for the player at the same timestamp, value 1 then 100**, in 12
  of 12 connections. Monsters receive one value and never the pair. Any null phrased as "the fitted curve must
  not reproduce the player's 100" is being scored against a channel that also emits 1 for the same agent at the
  same instant.
- **[OBSERVED]** `toolkit/mirror_priorart.py:17` hard-codes `C:\gd\Rurik\vault\mirrors` and never imports
  `vaultpath`; `summarize_capture.py:27` hard-codes `…\captures\authsrv`. Same family as `../../vault`, from the
  other side.
- **[OBSERVED]** `toolkit/content.py` enforcement gap: a row with `source='wiki'` and **no `verified` field loads
  silently**, while `py4gw` and `gwlpr` are refused for the wrong reason (absent from the SOURCES vocabulary, not
  by licence) — so a legitimately-verified Py4GW row cannot be expressed at all. See §9.
- **[OBSERVED]** GWLP-R's `spawnpoints` table must be refused on **data quality, not licence**: `X`/`Y` are
  `float(4,0)`, and **262 of 422 rows (62.1%) have a coordinate saturated at exactly ±9999**. Our own
  `content/maps.toml` map 449 spawns at `(-9067, 13218)`, a value that schema cannot represent.
- **[CONTESTED]** `schema/overrides.json` names GAME_CMSG `0x0060 CHAR_CREATE_SET_CHAPTER_PROFESSION` and
  `0x0084 CHAR_CREATE_SET_EQUIP_COLOR`, and ArenaNet's own client traffic contests both, in the same shape as
  `0x0046 USE_SKILL`. `0x0060` occurs **15 times, 15 of 15 on character-select connections** (5 per connection,
  identical on 3 of 3); `0x0084` occurs **105 times, 105 of 105 on character-select connections** (35 per
  connection, identical on 3 of 3). **No character was created in any of the three sessions** — three identical
  counts across three sessions is what says so, since a creation would appear in one and not the others. These
  fire on ordinary character **select**, and `0x0084` is the direct cause of the item re-declarations that
  inflate §10.1's 47-record figure. Rename or demote before anything joins on "CHAR_CREATE".

### 6.4 [OBSERVED] The item message family, in full, and the seventeen that have never arrived

Thirty GAME_SMSG opcodes have receive handlers that assert in `ItCliApi.cpp`. Counts are over canon-12.

| seen | | never seen |
|---|---|---|
| `0x0135` 2 · `0x013A` 63 · `0x013E` 109 · `0x013F` 108 · `0x0140` 12 · `0x0144` 12 · `0x0147` 48 · `0x0148` 12 · `0x014B` 51 · `0x014D` 33 · `0x015A` 198 · `0x015E` 610 · `0x0161` 394 | | `0x0139` `0x0141` `0x0143` `0x0145` `0x0146` `0x0149` `0x014C` `0x014E` `0x014F` `0x0150` `0x0151` `0x0152` `0x0153` `0x0155` `0x0159` **`0x015F`** **`0x0162`** |

The handlers map onto `ItCliApi.cpp` source lines 1722 → 2672 in opcode order, which is a
structural check the client could have failed and did not. Two rows matter more than the rest:
**`0x015F` and `0x0162` are the only two whose handlers call the item-table removal helper
`0x008488D0` before rebuilding**, and their wire layouts are byte-identical to `0x015E` and
`0x0161` respectively. That is a create/replace pair discovered from the client's code, not
inferred from the names, and the replace half has never once arrived from ArenaNet in 758
seconds of play — because in 758 seconds of play nobody changed an item they owned.

Measured `ITEM_*` bounds from ArenaNet's own guards, with the three that were already known as
the control that had to agree and did: **`ITEM_ATTRIBUTES` 559** @`0x005A8FE7`,
**`ITEM_DESCRIPTIONS` 388** @`0x005A90E7`, **`ITEM_FORMULAS` 1501** @`0x005A9147`, and new:
**`ITEM_TOOLS` 10** @`0x008E61F7`, **`ITEM_TYPES` 46** @`0x0059F94F`, **`ITEM_MATERIALS` 50**
@`0x005A9074`, **`ITEM_COLORS` 14** @`0x005A90B7`, **`ITEM_BAG_SLOTS` 21** @`0x0084AC8C`,
**`ITEM_STACK_SIZE_MAX` 250** @`0x004DF4E6`.

---

## 7. The identifiability frontier

What this project can **never** determine about ArenaNet's server with the instruments it has.

**[OBSERVED] 7.1 No per-species drop probability at usable precision under the authorized protocol.**
The draft said *"no drop probability, from any source, ever"*, and the critic is right that the three walls do
not support the universal. They support this: **no community number is usable; sustained single-species farming
is refused by policy; and the estimator is undefined at the n this protocol produces per species.** They do not
foreclose a pooled or hierarchical estimate across many species from many short sessions — which is exactly the
design §7.4 endorses two items later, and as drafted §7.1 and §7.4 contradicted each other. The restated claim
is the one the walls carry, and each wall alone is sufficient for it.

(a) *The community cannot supply one.* Across GWW's 22,356 articles, **2,370 document what a creature
drops and only 83 contain the phrase "drop rate"** — a 28.6:1 ratio. GWW's own "Anti-farm code" page grades player
theories Accepted/Disputed/Speculative and says confirming the last tier *"would take hundreds of players farming
under controlled conditions for dozens of hours each."* The best quantified study on the wiki is one player, one
endgame chest, 18 rows, last edited 2012. Of 4,040 GWW-scraped item pages bundled in the Py4GW mirror, **43 (1.1%)
contain any percentage and ZERO state a sample size.** (b) *Policy refuses the only method.* Sustained farming is
exactly what CLAUDE.md's live-behaviour rule forbids, and at the measured 0.422 kills/min, 100 kills of one species
is ~3.9 hours of continuous combat with one creature. (c) *The estimator is undefined at feasible n.* Chao1 is
undefined at f2 = 0; the exact permutation floor is 1/C(k,d) = 0.50 at the largest single session.

The correct conclusion is still stronger than "be careful with community numbers": **no community drop rate is
usable here at all, not even as corroboration, and it fails on epistemics rather than licence.** The map-148
precedent works because the borrowed value is a pointer into an artifact we hold — `(9826, 8077)` is refutable by
parsing MFT row 7982. A probability has no such artifact.

**[OBSERVED] 7.2 The rune/material/dye trader price dynamic is irrecoverable in principle.** It was a shard-wide,
time-varying function of aggregate player supply and demand. There is no fixed value to recover and no capture of
one session can contain it. Name it explicitly so nobody spends a campaign on it: the honest reconstruction is a
designed curve of our own, labelled `source='invented'`.

**[OBSERVED] 7.3 PRNG state is closed.** 64 bits of state, ~5 observable bits per event, 53 damage events in the
whole corpus, interleaved draws from every other subsystem. The modulo bias is ~n/2^32 and needs ~10^14 samples.

**[UNVERIFIED] 7.4 Loot scaling / anti-farm diminishing returns is the hazard nobody in this repo has named, and
it invalidates the naive plan.** If it is live on the service we would capture against, then drop rates measured
by repeating one species are biased *downward by the act of measuring them*, and **the bias grows with n — the
estimator gets worse as the sample gets larger.** A grep of `studies/` and `toolkit/` returns nothing on it.
Measuring whether rate depends on session-cumulative kill count must precede quoting any rate at all. It also
resolves the policy tension in the project's favour: the only capture protocol that is both authorized and
statistically valid is **many short sessions in new content**, never one long grind.

**[NOT FOUND] 7.5 Armour is not on the wire.** No armour-shaped property id appears among the 21 integer and 3
float property ids observed across 22,524 messages — a count that is unchanged on canon-12. A damage-formula fit
has armour as a free parameter, and wiki armour figures are themselves player-inferred from damage, so using them
closes the loop on itself.

**[OBSERVED] 7.6 Reforged Mode is not recorded and is not recoverable afterwards.** `MANIFEST` Revision 2 records
that Reforged reduces enemy health ~20% and armor ~20%. Neither the manifest nor `toolkit/origin.py` records the
mode. **Every monster health number in §6.1 is either base or base × 0.8 and nothing on this machine can say
which.** This must be stamped at capture time; §10's pre-flight makes it step 4.

**[OBSERVED] 7.7 Party drop assignment cannot be observed in scope.** It needs ≥2 players or henchmen in the
instance; Pre-Searing has **zero** henchmen and the live corpus is solo. Inside the v1 boundary "the killer owns
it" is indistinguishable from retail. Row 19 of §2.8 (player-to-player trade) is out of scope for the same reason
from the other side: it needs two accounts in one instance, which the one-client rule forbids.

**[OBSERVED] 7.8 There is no server step period.** The comb is refuted; the only measurable cadence is the outpost
flush at 20–21 ms (modes 20 ×914, 21 ×365, 40 ×198, 41 ×154), and tick rate is not even a per-zone-class constant
(outposts 25.79 and 29.55 Hz across two sessions; explorables 6.26–9.56 Hz). If a simulation step is wanted it must
come from the client's own timer code, not from a histogram whose smallest value is 1 ms.

**[OBSERVED] 7.9 What identification and salvage still cannot give us.** No salvage-destroy rate
and no per-item modifier probability, for the same three walls as §7.1 and one more: the client
*displays* a destroy chance it computes itself, so a wire observation of the outcome is not an
observation of the server's parameter. The reachable results are all structural — the opcode
binding, the create/replace pair, the outcome space, whether a drop record is complete. Do not
let a repaired §8.4 or §8.5 quote a frequency from a session with three salvages in it.

**[OBSERVED] 7.10 And the loopback sweep is a format oracle, not a behaviour one.** §4.11g is the
long form. It renames the 332; it does not shrink them, and nothing it produces may ever be pooled with the
22,524 (`toolkit/origin.py`).

**What would have to change**, in cost order: (1) expose `t0` — one line; (2) fix `string16` — small, and it
unblocks two techniques; (3) `marks.py` — a standalone `{t, kind, text}` writer on `wirecapture`'s clock, which is
the entire difference between the live corpus being narrated prose and being a dataset, specified to the file in
§10.5; (4) record Reforged Mode in `manifest.json`; (5) **make `prune_wire` stop deleting** (§10 pre-flight item
11) — it rewrites `wire.jsonl` in place, gated on the same VERSION table whose one-entry ancestor cost six keys;
(6) many short human sessions in **new** content, which §1.8 says is the only thing that buys opcodes anyway.

**The draft's item (5) — "recover the missing game key for `20260807T124912`" — is deleted, not reordered.**
§1.2a shows it is arithmetically closed (2^160), that the cheapest corpus growth is therefore another session,
and that "roughly double" was +56.5% on s2c anyway.

**And one constraint that is a design input, not a bug:** `toolkit/origin.py` forbids pooling, so a loopback
labelled corpus and a live corpus can never merge. They are two datasets and only one is an oracle. Any drop or
economy table must carry `origin` **per row**, the way `content.py` already carries provenance per row.

---

## 8. Acceptance criteria

`PLAN.md` §3.2 had to rewrite two rungs because their criteria could not be evaluated. Each criterion below names
the artifact that decides it and the control that can refute it. **Three of the draft's criteria could not fail
and have been rewritten** — the critic caught all three, and this document indicts that exact defect in §5, so
shipping it would have been the sharpest available self-contradiction.

**8.1 `toolkit/schema/codec.py` — the precondition.** *Criterion:* **22,524 of 22,524** live GAME_SMSG messages
decode and re-encode byte-identically. **Today 133 fail** (canon-12; the draft's 127 was BIG-10's numerator under
canon-12's denominator). *Control:* the failure list must be per-opcode, and `0x004C` must go from 0/40 to 40/40
and `0x0161` from 363/394 to 394/394. A second control that can fail independently: the count of decoded values
containing U+FFFD must go to **zero**, and it must equal the round-trip failure count at every intermediate state,
because §6.2 measures those two sets to be identical today.

*Third control, the sabotage — and §8.6 mandates one of these for compilers while §8.1 had none.* **A
`string16` that stashes the original bytes on the value and replays them at encode passes both clauses above
without ever carrying raw code units:** the round trip is 22,524/22,524 because the encoder is a memcpy, the
U+FFFD count is zero only because clause 2 is comparing bytes rather than the still-lossy decoded text; and —
since §6.2 measures the two sets identical today — the "must equal at every intermediate state" clause is
satisfied by the memcpy as well. So build that version and require it to go **red** on this criterion: **a
decoded surrogate must survive a decode → mutate-a-neighbouring-field → encode → DECODE cycle.** Take a real
`0x0161` whose `field[12]` carries the low surrogate `0xDE01`, change `field[9]` (the gold value) to a different
integer, re-encode, and then **decode the re-encoded bytes and assert both halves: `field[9]` reads back as the
MUTATED value, and `field[12]` still carries `01 DE`.**

**Asserting only the second half is the vacuous version, and it was the first thing written here.** A
message-level byte cache — decode stashes the whole original plaintext, encode replays it — emits `01 DE` and
passes while silently discarding the mutation entirely. Reading the mutation back out separates them. This is
the shape `test_mapfile.py` already uses — mutate a decoded chunk in place until its payload changes length and
require the emitted size field to move with it — and it is here for the same reason: the first version of that
test replaced the chunk object instead of mutating it, and a sabotaged encoder passed it 22 checks to 0.

*Fourth control, and the criterion was still insufficient without it.* **The mutation control does NOT catch
the sabotage this section names by name.** A stash carried *on the value object* survives a mutation to a
neighbouring field untouched — moving `field[9]` does not move `field[12]`'s stash — so it satisfies both
halves and passes. The paragraph above asserted otherwise and was wrong; writing the test is what showed it.
What separates a value that CARRIES code units from one that REPLAYS them is **construction**: build a
`string16` value from raw code units that was never decoded, and require the encoder to emit exactly those
units. A value-level stash has nothing to replay and must fall back to a strict encode, which raises
`UnicodeEncodeError` on a lone surrogate — and that raising, asserted in the same check, is what makes the
input discriminate rather than merely pass. **Status: all four controls are implemented and green**
(`test_codec.py` §5–§6, floor 18 → 27, 2026-08-11), and the criterion is met: **22,524 of 22,524**, U+FFFD
zero, `0x004C` 40/40 and `0x0161` 394/394. See §6.2a, including the astral-pair desync the fix exposed.

**8.2 `toolkit/authsrv/lootledger.py` — the kill ledger.** *Shape, not criterion:* a table with **one row per
(capture, connection, agent-death)**, carrying species slot, class tag, drop/no-drop, item model id and an explicit
`censored` flag. **"4 rows on today's corpus, 2 drops, 2 no-drops, all in map 146" is an outcome this document has
already measured (§1.5), so it is reported and never thresholded on** — a ledger that hard-codes those four rows
satisfies it, which is the same defect §8.4 was rewritten to remove and which this document indicts in §5.1.
*The criterion is control (c), because it is the failable part.* **(c) The class-tag join must be time-windowed,
and the check is agent 38 on `:62994`**: that agent id is REMOVED at t = 47.514 and REUSED at t = 74.779 for an
`anim` agent, so a ledger that joins agent id → class tag without a window reads the drop-producing kill as `anim`
and **must go red**. It is failable because it already failed — on a fixer's first pass. The run must also assert
the *reuse itself* is present in the input, so the check cannot pass on a corpus where the trap is absent.

**And the trap as stated is one-directional, which is its own vacuous pass.** Every reuse of agent 38 on
`:62994` is *later* than the kill at t = 19.912, so an implementation that simply takes the **earliest** create
for an id — no window anywhere — reports `mon1` and passes, while being exactly as wrong in the other direction:
it would tag the later `anim` agent's own events `mon1`. "First create wins" is not "time-windowed". So the
criterion asserts the **window itself**, not its outcome: for every ledger row, the create the ledger selected
must satisfy `t_create ≤ t_death < t_remove`, read out of the ledger's own chosen create rather than
re-derived — and a second row must exist, or be built synthetically, where the correct tag comes from a **later**
create than an earlier one for the same id. Without that second direction the check only ever exercises one.
*Controls that must additionally run:* (a) the temporal null and (b) the spatial null, and the spatial null must
consume **tracked** position with an assertion that tracked ≠ create position on at least one case — otherwise it
passes vacuously (on the 19.912 case the create position measures 14,368.8 units and would refute the pairing the
null exists to support). *Floor:* the run goes red below a declared minimum row count; a run over
three kills must **fail**, not report a confident fraction. *Never emit a percentage.*

**8.3 `toolkit/authsrv/rerollcheck.py` — authored or rolled.** The draft's criterion was *"pairwise order agreement
≥ 0.90 on both matched explorable pairs"*, which §4.1 had already measured at 0.963 and 1.000 — **satisfied before
the module exists**, and the thing §4.1 says actually matters was demoted to "printed beside every number".
Printing is not a criterion. *Rewritten criterion, and it can fail:* on each matched explorable pair the agreement
must sit **≥ 5 standard errors above that pair's own empirical shuffle mean**, where the mean and sd come from
≥ 200 within-pair shuffles the module computes at run time and does not read from this document. On today's data
that is (0.963 − 0.506)/0.043 = 10.6 and (1.000 − 0.340)/0.070 = 9.4, so a correct implementation clears it and a
module that scores against a hard-coded 0.50 null lands at 10.8 and 9.5 — indistinguishable, which is why the
second control exists. *Control 1, and it must go red:* the **cross-map** pairs (measured 0.443–0.571) must land
**below 3 standard errors** of their own nulls; a statistic that always says yes fails here. *Control 2, the
sabotage:* a build that substitutes the analytic 0.50 null for the empirical one must be run and must produce a
**different** z on at least 7 of the 11 pairs — that is the measured fact (7 of 11 sit >3 se off 0.50), and a run
where the two nulls agree everywhere means the empirical null was never computed. *Reported as n = 2, with the pair
identities, the class-tag split, and the outpost control restricted to `nonc`/`mon1`.*

**8.4 `content/itemmods.toml` + `toolkit/authsrv/itemconstraint.py`.** The draft required the shuffle control to
come out *"denser and generalising worse (measured: 2.8× denser, 19.5% vs 13.5%)"* — quoting an already-measured
outcome as the pass condition, which makes it a replay rather than a test. *Rewritten criterion:* a three-valued
verdict on a **train/test split the module has not seen** — the third keyed capture `20260807T133758` is held out
entirely today and never enters the gate — with the unit pre-registered (records or words) and the threshold
written to the run file **before** the test capture is opened. Cardinality above the observed maximum is UNKNOWN,
never ILLEGAL. *Control 1, computed at run time and not read from here:* over ≥ 400 shuffles the module must report
the observed gate's held-out unknown rate as **below the 5th percentile of the shuffled distribution**, and must
print the shuffled median density beside it; a run in which the real gate is not in the tail fails, whatever the
direction. *Control 2, and it is the one that catches a replay:* run the split **backwards** (train on
`20260810T235916`, test on `20260807T143055`) and require the single ILLEGAL that produces — the 5-modifier item
judged against a held-out maximum of 4 — to be reported as **UNKNOWN**, by name. A gate that emits ILLEGAL there
has the cardinality rule wrong. *Coverage reported over the **82 distinct `(field[2], field[3], field[10], mods)`
tuples and 46 distinct modifier lists**, never over 394 records — and the field indices must be named in the
module, because two independent readers could not reproduce the 82 without them.*

**8.5 `toolkit/clientscan/itemcode.py` — the modifier decomposition.** The draft's headline — *"990 of 990 live
modifier words decompose under the client's own split"* — **cannot fail**: any 32-bit word decomposes under any
bitfield partition, and this document indicts that exact defect in §5.1 and §8.6. Deleted. *Rewritten criterion,
three clauses, each refutable:*
(a) **Terminator and tag domain.** Over all 990 canon-12 words, **0 must equal `0xC0000000`** (the client's own
`ITEM_CODE_TERMINATOR`, read at `0x008487B0`) and **0 must have `tag2 == 3`**; the emitted tag2 histogram must be
`{0: 325, 2: 603, 1: 62}`. A decoder that mis-places the tag field moves that histogram, and a decoder that keeps
the terminator inside the array trips the first clause. Both are properties of ArenaNet's bytes, not of our split.
(b) **Two-witness agreement on the identifier, with a disagreement being a failure.** `id10` must be recovered
independently from the evaluator at `0x00923A40` and from the lookup at `0x008487B0`, and the two must agree on
**990 of 990** words; the module must print the count of disagreements, and any non-zero count is red.
(c) **Three-class case-set emission** — handled-with-body, handled-as-no-op, default — with the measured fact as
the criterion: **exactly 59 of 990 words ArenaNet itself sends must land in the handled-as-no-op class**, over
exactly **2 of the 18 identifiers**. A module that collapses no-op into handled reports 0 there and goes red; a
module that collapses no-op into default reports 990-minus-handled and goes red.
*Floor:* a run producing fewer than 990 words has read the wrong corpus and fails naming the shortfall.

**8.6 Any capture→row compiler.** *Criterion:* `PLAN.md` §8 item 2 already names this as "the half nobody owns", and
the industry comparable is explicit: **WowPacketParser is not a sniffer, it is a compiler.** *Control, and this is the
one that must exist:* **sabotage it.** Build a version that emits the right rows for the wrong reason — replaying a
stored field rather than deriving it — and require the headline row count to go **red**. Three tests in this repo
already record that their headline stayed green under a memcpy sabotage; a drop-table compiler will do the same.

**8.7 `toolkit/authsrv/smsgsweep.py` — the opcode→effect map (§4.11).** *Criterion:* a table with one
row per (opcode, pass, value-profile) carrying the predicted channel from the static pre-pass
and the observed one, over **332 of 332** catalogued-never-seen GAME_SMSG, three randomised
passes, with **empty control slots interleaved 1:1**. *Controls, and all three must be able to
fail:* (a) the control slots must stay **at or below the measured idle floor** — §4.11b puts
the parked residual at `0x0009` 0.082/s plus `0x0008` 0.013/s, i.e. ~0.19 messages per 2.0 s
slot and ~190 background messages across the run's empty slots, so **"zero replies" is
unsatisfiable by a HEALTHY run** and stating it that way invites weakening the control at run
time when it reddens. The criterion is therefore: zero control-slot messages **outside
`{0x0008, 0x0009}`**, and a rate for those two within 3σ of the measured floor. Attribution in
this sweep is by opcode identity rather than by timing, which is what makes the exclusion
sound rather than convenient.
(b) **The static partition is scored against a threshold, not printed.** The draft said its
calibration *"is printed beside the score"*, and §8.3's rewrite three criteria above says in
terms that **printing is not a criterion**. So: the module computes, at run time, the observed
effect rate inside the predicted-effectful class (the 258 predicted to reach {frame, named
subsystem}) and inside the predicted-silent class (the 74), and the run goes **red** unless
the first exceeds the second by **at least 20 percentage points**. A partition with no
predictive content lands near zero and fails. Its own calibration on the 155 live-observed
opcodes (31 called silent, false-silence rate 20.0%) is the floor that number was chosen
against and is reported beside it — but the threshold, not the printing, is the criterion.
(c) **A positive control, which the draft had none of, and it is the one that catches a dead
instrument.** A sweep whose transport is broken — sends never arriving, or a readout that
never fires — records "silent" for all 332, emits 332 rows, satisfies control (a) trivially,
clears the floor and **passes**. So two things must hold. **At least 150 of the 227 opcodes
the pre-pass predicts post a constant UI msgId must produce a non-zero observed effect**; and
**known-effectful live-observed opcodes are interleaved as calibration stimuli at one in
twenty** — and the draw is **not** uniform over the 155. It must come from the **31 that the
static classifier itself calls silent** (`0x00E3 SKILL_ACTIVATED`, `0x0056
NPC_UPDATE_PROPERTIES` and `0x0168` are three of them), because a fabricator that simply
copies the prediction into the observation column survives a uniform draw with probability
(124/155)^17 ≈ **2.3%** — being caught 97.7% of the time by luck is not a criterion. Drawn
from the 31, the fabricator is caught every time. **Every calibration stimulus must register
an effect.** One that comes back silent means the readout is broken and every
silence in the run is uninterpretable: that is a FAIL, not a row. Calibration rows are marked
and excluded from the 332. *Floor:* a run that stimulates fewer than 332 opcodes, or that
loses its cursor across a crash, is a FAIL naming the shortfall. *Never* report a msgId as a
"panel" — that binding comes from readout channel 4 or 5, and the static pass cannot supply it
(no `Vn*` module is reachable from any handler at depth 3). *Every row carries `origin: ours`.*

**8.8 `toolkit/authsrv/itemevents.py` — the item-event compiler (§4.17, §4.18).** *Criterion:* every c2s item
message in a capture is paired with the s2c replies inside its mark window, and the table names
the opcode, both item ids, and the **field-level diff** between the item's record before and
after — not the records themselves. *Controls, and all three must run:* (a) **the disjunction
is deleted.** The draft required the identification diff to be *"empty in every field except
`field[8]` bit 23 **or** the run must name which other fields moved"* — every possible outcome
satisfies one disjunct, and naming the fields that moved is what a diff **is**, so the control
was a description of the deliverable wearing a criterion's clothes. Replaced by a criterion
that can go red: **the emitted diff must name `field[8]` and must assert that bit 23 went from
set to clear on that item**, and any field named in the diff that is neither `field[8]` nor
the modifier array is a **red** result that must be reported as *the identification changed
more than the flag* — a finding, and one the run must refuse to summarise as success.
(a2) **The sabotage that catches a replay.** Feed the compiler a synthetic pre/post pair in
which the two records are byte-identical; it must emit an **empty** diff and exit non-zero,
because a compiler that stores the post-record and re-derives the "diff" from a template
emits a bit-23 row against identical inputs. (b) a run over a capture with **zero** item c2s messages —
which is every capture in the vault today — must produce **zero rows and exit non-zero**, not an
empty table reported as success.

**(c) The synthetic POSITIVE fixture, without which this whole criterion never executes.**
Controls (a2) and (b) assert nearly the same thing from two directions, and criterion (a) has
**no fixture that can exercise it** — (b) itself certifies that every capture in the vault has
zero item c2s messages, so a compiler that emits **no rows for any input** satisfies (a2),
satisfies (b), never runs (a), and goes green today while shipping broken; the defect is then
discovered after the live session rather than before it. That is `test_codec.py` printing ALL
CHECKS PASSED with its fixture glob matching nothing, exactly. So the test **builds** its own
positive pair: one pre/post differing in bit 23 of `field[8]` and nothing else, which must
pass; and a second differing in bit 23 **plus one extra field**, which must be reported red
under (a). And the absent-live-data path declares `LEDGER.skip(...)` and is printed, never a
silent zero. *Floor* set from a real green run — over the synthetic fixtures, since the live
ones do not exist yet, and the floor must say so.

**8.9 `toolkit/harness/marks.py` + `test_marks.py` (§10.5).** *Criterion:* `bind()` returns every mark on
wire time and **asserts** the two-clock agreement (`|Δperf − Δwall| ≤ 0.250 s`) rather than assuming it.
*Controls, all against a fake `user32`:* an edge fires once per press and not once per poll; the syntax tree
contains no `SendInput`; `bind()` goes red when the two clocks disagree past tolerance; a mark before `t0` is
refused; a changed plan file is refused; advancing past the last step is refused. *Floor* from a green run.

**8.10 Every one of the above routes its verdict through `toolkit/checks.py` with a `floor` set from a real green
run, and is added to CLAUDE.md's suite list in the same commit as the test.** The suite is 49 files today.

---

## 9. What the owner must decide

**9.1 Three stale blockers in `PLAN.md`, and the first one a cold session reads is the worst.**
- `PLAN.md:1380-1382` (§8 item 1, the live next-actions list) opens *"Every capture in the vault is Rurik talking
  to Rurik; **not one byte is ArenaNet's**, so R0b is unmet and R1.5 and R4c's original criterion are both blocked
  behind it."* Every clause has been false since 2026-08-07, and it is contradicted by its own body 87 lines later
  and by §3's `R0b ✅` and `R1.5 ✅` rows. The body was rewritten as the work landed; the lead sentence was not.
- `PLAN.md:528-531` (§3.2; the quoted sentence is on **:530**, the block reads 528–531): *"R4c-2 stays at 0 and is
  reported as blocked until R0b exists."* `PLAN.md:357` marks R0b ✅ 2026-08-07 and the vault holds 27 live-stamped
  files. **And the blocker is doubly stale**: §6.1 shows the monster stats it was waiting for are already in the
  vault and the definition slot is a stable key. The rung is not blocked, it is unstarted.
- `studies/presearing/MANIFEST.md:893, :960, :962` carry the same pre-R0b framing in three places, and the document
  is stale on two independent axes while its own Revision §8 knows about one of them and asks for a re-derivation
  nobody did.
- Minor: §8.0's heading reads "suite 45/45"; **49 test files exist today** (four landed since `e7d2080`:
  `test_dispatch.py`, `test_datcheck.py`, `test_mapbuild.py`, `test_pathchunk.py`). The hash makes it honest rather
  than wrong, but the number a cold session reads is 45. §3.2's R4c-1 counts also trail the content store (9 map
  rows against "today 2", 2 NPC rows against "today 1").

**9.2 `toolkit/content.py`'s source vocabulary.** Two problems pulling opposite ways. A `source='wiki'` row with no
`verified` string loads silently, so a folklore drop rate could enter `content/*.toml` today with nothing recorded
about what it was checked against. Meanwhile `py4gw` and `gwlpr` are refused as unknown vocabulary, so a
legitimately-verified row cannot be expressed. **But adding `py4gw` as a SOURCE token is the forbidden direction** —
`PLAN.md` §1.1 reserves that position against exactly an unlicensed upstream. The shape that is permitted:
`source='capture'` with the upstream as a note. Owner call on whether `verified` becomes mandatory for `wiki` too.

**9.3 Derivation-register rows needed before any module reads the artifact.**
- **Fournux/Tyria-Extractor (MIT)** — no §6.1 row exists, and its `ITEM_GENERAL` offset table is the most directly
  usable thing in the mirrors. Its *negative* results are more valuable and cheaply testable: it states outright that
  no complete static `model_id → model_file_id` table and no complete static NPC-definition or vendor-inventory table
  is confirmed in the archive or the executable, so the item and vendor catalog is **capture-only by upstream's own
  admission**. Agreeing with a negative borrows nothing.
- **ldufr/Headquarter (MIT)** — a row exists for GAME_CMSG names; any merchant/trader/quote/salvage/chest name adopted
  from `opcodes.h` needs its own `why` with an independent leg, because the corpus leg is unavailable (zero economy
  traffic, and §4.16a measures zero identify/salvage traffic too).
- **GWCA** — §2.9.2 now uses `Skill.h`'s `recharge` declaration as the *independent* leg of a CORROBORATED claim,
  which is the permitted use (verifying a value we derived: the 1-of-41 column match came from ArenaNet's own
  `0x00E5` against the pinned binary, not from GWCA). A register row is still needed, and note that
  **GWCA's LICENSE reads like MIT but deletes publish/distribute/sublicense/sell** from the grant, so it must never
  be described as MIT in `THIRD-PARTY-NOTICES.md`.
- **GWW (GFDL 1.2+)** — the XP closed forms (`next = 1400 + 600·level`, cap 15,000 at 182,600 cumulative; per-foe
  `16·delta + {104, 100, 96}` clamped to `[0, 280]`, reproducing **18 of 18 published rows**) are ours, fitted; the
  table is theirs. Facts are not copyrightable, prose is. Note the one genuine CORROBORATION in the original census:
  GWW's attribute-points-per-level table and GWLP-R's 2013 MySQL dump agree **20 of 20** from lineages that never read
  each other — and §2.9.4 adds a **third** primary witness that is ArenaNet's own bytes, `s_attribPoints` at
  `0x00BC8B24` holding `1,2,3,4,5,6,7,9,11,13,16,20`. Three independent lineages on one table is the strongest
  corroboration in this document.
- **gw-preservation, Py4GW_Reforged, GWLP-R-Utils** — all three grant nothing; verification-only. Py4GW_Reforged's
  catalogs are dumped from **`Gw.wasm`**, a different build from 38797, so its addresses cannot be used against the
  pinned client at all.

**9.4 Bulk extraction from ArenaNet's artifacts, in two places, and the default is refusal.**
- **`toolkit/clientscan/asserts.py` bulk export.** The assert-reachability sieve's deliverable is a committed table of
  ArenaNet's own source file names, line numbers and assert expressions across the whole 477-opcode receive catalogue,
  landing on the server path in git. The repo already quotes individual expressions in studies and `overrides.json`; a
  bulk export is a different scale.
- **§4.9's unclaimed string-run census, which the draft did not flag at all.** Its deliverable is 476 runs of decoded
  `Gw.dat` text, and it already quotes three extracted item names into what will become a tracked file. That is a bulk
  string extraction from `Gw.dat` heading for version control, in exactly the same category. §4.16a's 71
  salvage/identify strings are the same question at smaller scale and are handled the permitted way there — cited by
  **string id and paraphrase**, bytes left in the owner's archive.
- **Under the top-of-`CLAUDE.md` rule the default for both is REFUSAL** — ArenaNet source text and ArenaNet asset text,
  committed at scale, is ArenaNet bytes in the repo, and retrofitting provenance is not possible. Neither export
  happens pending an explicit owner ruling. If a ruling goes the other way, the consuming validator must read the
  table as committed **data** and must never import capstone at runtime; and the string-id-plus-paraphrase shape
  should be preferred over the text itself in every case where a validator can resolve ids at run time against the
  owner's own archive.

**9.5 `scrub_captures.py` cannot clean a `plain` frame payload** — the account email as UTF-16 inside a hex blob, invisible
to an ASCII leak check, in 401 of 517 captures. Any labelled drop dataset built from live captures inherits
DO-NOT-SHARE. `marks.py` is designed around this (§10.5): the note hotkey emits **no text**, so operator-typed
strings never enter a capture in the first place.

---

## 10. If you do one thing next

**Two things, in this order, and the ordering is the answer.**

**First, this afternoon, at zero human cost: run §4.11's loopback sweep.** By this document's own ranking metric —
information per hour of *human play* — it outranks everything below, because it costs none. 66 minutes of agent
time, both endpoints ours, `assert_launch_safe(exe, "127.0.0.1")` cleared in 2.70 s, and the deliverable is a
332-row opcode→effect map for the third of the catalogue ArenaNet has never shown us. It is also the thing that
makes the session below scorable in its most likely branch: if the merchant panel opens and nothing arrives, §10's
fallback question is *which c2s opcode does the panel send*, and the sweep answers that at n = 332 **before** the
session rather than after. **Schedule it first and name it in the session's preconditions.**

It does **not** displace the session, and the reason is its own §4.11g: the sweep adds zero message classes the
vault has never held. It renames the 332; it cannot produce a price.

**Second, and it is still the one act that costs human minutes: one ~30-minute session, on the secondary account,
one client, human cadence — merchant first, identification and salvage second, and the character sweep folded in
as a CONTROL rather than a data source. Do not run it until `marks.py` exists.**

### The operational envelope, stated because the draft did not

The draft said "secondary account, one client, human cadence" and stopped, and the critic is right that an agent
reading it could reach for `drive_client.py`. Precisely:

- **Build:** the stock-DH client under `vault/client-patched-live/`, run from the assembled `vault/run-live/`.
  Never a build carrying our Diffie-Hellman parameters — `ours` → live is refused by
  `cage.assert_launch_safe`, and it is refused because Stage A completes with whatever credential the client
  autofilled *before* the patch matters. Prove it from the bytes with `python toolkit/clientpatch/dhbuild.py`
  (`stock` **and** `key_tapped`), never from the filename or the directory.
- **Account:** `toolkit/harness/accounts.py`, the secondary, through the **automation opt-in**. The primary is
  refused by default and must stay refused.
- **Driver:** `toolkit/harness/livesession.py --confirm`. **Do not pass `--host`** — it is refused by name and
  RUNBOOK explains why at length.
- **And the one that matters: the operator plays. The driver sends no keystrokes and no clicks.** It launches,
  sniffs, taps, holds, assembles and scrubs. `drive_client.py`'s `hold_key` is the thing on the other side of that
  line, and the live-behaviour rule turns on the difference: scripted input is precisely the traffic pattern no
  person could produce, and no guard in this repo substitutes for the cadence rule.
- **Not caged.** `stock` → live is the authorized configuration and must **not** be caged; the cage is for
  `ours` → loopback.

### Pre-flight — read §1.2c's six-row table first

Four of six live runs produced nothing usable, none of them for the reason the operator expected at the time, and
three of the four failures were **invisible until after the client was closed**. Thirty minutes are worth nothing
if they land in row 1, 3 or 4.

**A. Offline, before anything is launched.**

1. **Prove the build from the bytes, not the path.** `python toolkit/clientpatch/dhbuild.py` must report the
   `vault/run-live/` client as `stock` **and** `key_tapped`. RUNBOOK already says so: *"`livesession.py` refuses an
   untapped build, because without the cave there is no key and the ciphertext is unrecoverable."*
2. **Run the loopback dry-run — and know its ceiling.** `python toolkit/harness/dryrun_keycapture.py`, elevated,
   green. It proves tap → sniff → assemble → decrypt end to end. It proves **nothing about the game channel**:
   `livesession.py`'s own comment is *"Our own server only ever speaks the auth shape, so no loopback capture could
   have shown this."* Both of the two decoder defects in §1.2c's table were game-channel defects and both would
   have passed a green dry-run. Necessary, never sufficient.
3. **`marks.py` must exist and be wired before the run, not after.** §3.2 establishes there is no instrument that
   attributes a client action to a capture timestamp during a live session. Without it, the falsifiable half of the
   prediction below has no record of what was visible, and the session is narrated prose for the third time.
   §10.5 specifies it to the file.
4. **Write down Reforged Mode** (§7.6) and the character, profession and route, on paper, before starting.
5. **Close every `Gw.exe`** (`preflight` refuses otherwise, and correctly) and open an **elevated** shell
   (`WinDivertOpen` loads a kernel driver).

**B. Start order — the driver already enforces the important half; do not work around it.**

6. **The sniff starts first, always.** RUNBOOK: *"It starts the sniff before the launch (the DH handshake is the
   first thing on the wire and it is the plaintext half)."* `run()` waits on a real readiness signal
   (`_wait_for_sniff` looks for the `wire_meta` line that is only written after `WinDivertOpen` succeeds) and
   refuses to launch without it. **Never launch the client by hand and attach afterwards** — that is the one
   procedure that would actually produce the mid-stream capture §1.2 was mis-diagnosed as, and it is unrecoverable.
7. **Do not pass `--host`.**
8. `--minutes` is a **ceiling, not a duration**. The script below is ~30 minutes, so `--minutes 45`; Ctrl-C or the
   `STOP` file ends the run at any point and still assembles and scrubs in full.

**C. During the run — what the operator watches, and what the driver must start telling them.**

9. Watch the status line's **`client ports`** field. Any port outside `LIVE_PORTS` means the ciphertext is not
   being recorded; stop. This instrument exists because of §1.2c row 4.
10. **The driver cannot currently see row 1's failure, and must be able to.** `_hold`'s only wire instrument is
    total bytes, and its warning fires on `size < 1024` after 60 s — in the 124912 run bytes *were* arriving in
    volume from t = 27.5 s, from six connections the assembler would refuse an hour later. **Required change:**
    each tick, classify every connection in `wire.jsonl` through `channel_of_stream` and print `auth` / `game` /
    `NO GW HANDSHAKE` with its byte count, and warn loudly on the last. Refuse nothing — the bytes are still worth
    keeping — but say it while the operator can still act.
11. **Required change: `prune_wire` must stop deleting.** It rewrites `wire.jsonl` in place (`os.replace`) before
    assembly, keeping only connections whose c2s header is in `VERSION_CHANNEL` — the same table whose one-entry
    ancestor caused row 1. Measured counterfactual on the artifact: with the 2026-08-07 table it keeps **1 of 7**
    connections and deletes **256,064 of 259,278** wire payload bytes. It has never fired that way (its first
    appearance is `pruned_records: 11` on the 2026-08-10 run) and a third VERSION shape from any client update is
    all it takes. Write dropped records to `wire-pruned.jsonl` beside the capture instead of discarding them.

**D. After the client closes, before the shell closes.**

12. **Re-assemble from disk immediately** — `python toolkit/harness/livesession.py --assemble <outdir>` — and
    require `decrypted == total`. This is not ceremony: it is exactly the operation that recovered §1.2c row 2 in
    full, and running it while the session is fresh converts "a decoder defect" from a permanent loss into a bug
    report.
13. Confirm `manifest.json` carries `wire_sha256`, `keyring_sha256`, `exe_unchanged: true` and a `keys_tapped`
    count **that matches the number of GW connections seen** — a mismatch is the row-1 shape.
14. `wire.jsonl` and `keyring.jsonl` are the capture. Everything else can be rebuilt from them; neither can be
    rebuilt from anything.

**The one-line version, and it is the lesson of the whole table:** *the ciphertext and the keys must both reach
disk before anything is interpreted, and every interpretation after that is retryable.* Rows 2, 5 and 6 obeyed it.
Row 1 did not, and it is the only permanent loss in the vault.

### The alternative was measured, and it is worth roughly one tuple

The completeness critic raised the obvious objection: §4.3 measures that **231 of 394 (58.63%)** item records
arrive within 2.0 s of a connection opening, and the three character-select connections carry **47 records each,
141 of 394 (35.79%)**, from a screen with no gameplay in it. Both figures reproduce exactly on canon-12. So why
spend the session on a merchant rather than on logging in the account's other characters and opening storage?

**Because §4.3's own rule answers it, and the critic is refuted by measurement rather than by argument.** Coverage
is reported over the 82 distinct tuples and 46 distinct modifier lists, never over 394 records — and under that
denominator the character-select screen has already been exhausted, twice.

**[OBSERVED] 10.1**

| | records | distinct tuples | new tuples vs. the other 11 connections |
|---|---|---|---|
| `20260807T133758 :54557` | 47 | 18 | **0** |
| `20260807T143055 :63158` | 47 | 18 | **0** |
| `20260810T235916 :61190` | 47 | 18 | **1** |
| all three pooled | 141 (35.79%) | **24 of 82** | 13 char-select-only (15.9%) |

`:54557` and `:63158` are **identical**: 18 of 18 tuples shared, zero either way. `:61190`, three days later,
shares 12 and adds 6, and every one of those 6 is the one played character's changed armour. 141 records buying 13
tuples is **0.09 tuples per record**. Their opcode profiles are identical on 3 of 3 — 39 opcodes, every pooled
count an exact multiple of three, seven of them exclusive to the screen (`0x005B`, `0x014B`, `0x014D`, `0x015B`,
`0x0188`, `0x0189`, `0x018A`). The 2.6× record inflation is mechanical and the client causes it: **105 `0x0084`
and 15 `0x0060` messages, 105 of 105 and 15 of 15 on character-select connections** (§6.3), and the server
re-declares every item after each.

**[OBSERVED] 10.2 And the screen already gives us every character, so "log the others in" buys their bags, not
their gear.** The 18 declarations decompose exactly: 17 equipped items in three bursts of 5 / 6 / 6 (armour types
4, 7, 13, 16, 19 plus a weapon for two of them), and one type-3 container which `0x013F`'s backpack row names as
the bag itself. **The account has three characters** and both live sessions played the same one — its loadout is
the only one that also appears in-world, 6 of 6 on all nine in-world connections. What the two unplayed characters
could add is what they carry, and the one character we have played twice carried, beyond its equipped set, exactly
**one** non-equipment tuple: type 21, model 2565, no modifiers, the quest reward, in both sessions.

**[OBSERVED] 10.3 Storage is not low-yield, it is closed.** The nine `0x013F` rows are **108 = 9 × 12
connections**, and they are: backpack ×20, **EQUIPPED** ×9, bag ×12, **five storage panes ×25**, **material
storage ×42** — 208 slots, 167 of them account storage. **Zero of 109 `ITEM_MOVED` names a type-4 or type-5 bag,
on 12 of 12 connections.** WIKI (GWW, "Ascalon City (pre-Searing)" / "Xunlai Agent", read 2026-08-11) says why,
from a lineage that has never seen our wire: pre-Searing has no Xunlai Agent and no storage access, and items
cannot be transferred in. All three characters are pre-Searing. Reaching storage means passing the Searing, which
is irreversible. **Refuse the step; do not cost it.**

**[OBSERVED] 10.4 And there is a cheaper act than either, which neither side named: the loot→bag transition is
0 of 22,524.** There are **109 `ITEM_MOVED`** in the corpus, and the split is **55 into the backpack (bag type 1)
and 54 into the EQUIPPED pseudo-bag (type 2, capacity 9, which `test_smsgnames.BAG_TYPE_EQUIPPED` already
names)**. The bag *type* is resolved per connection from that connection's own `ITEM_CREATE_BAG` rows, joined the
way `test_smsgnames.py:436-445` documents the two layouts — `CREATE_BAG [op, stream, bagType, model, bagId,
slots, ?]`, `ITEM_MOVED [op, stream, itemId, bagId, slot]` — rather than from a bag id assumed constant across
sessions, which is what produced the draft's "72 equipped / 37 backpack". Of the 55 backpack placements,
**51 = 17 × 3** are the character-select screen's synthetic staging of all three characters' worn items, one
identical burst of 17 on each of `:54557`, `:63158` and `:61190`, and the remaining **four** are the quest
reward — the same tuple (type 21, model 2565, quantity 1, no modifiers) on `:64103`, `:64102`, `:49163`
and `:49160`, i.e. twice per session, not once. 51 + 4 = 55 closes exactly. **Both corpus drops were left on the ground**: the drops land at
t = 19.912 on `:62994` and t = 36.330 on `:61624`, and neither connection carries a backpack `ITEM_MOVED`. One
click closes the one item-lifecycle edge the vault has never held, on an item whose roll we watched the server
perform. (§1.7's "the two inventory placements are the same scripted quest reward" was right in its conclusion and
wrong in both counts.)

### Head to head

| | character sweep + storage | merchant + identify + salvage |
|---|---|---|
| new distinct tuples (of 82) | **0–2**, predicted from three measured marginals of 0, 0 and 1; storage contributes 0 by 10.3 | **0** from the merchant — a vendor panel is not an `0x0161` population — but identification may *complete* records already counted (§4.17) |
| new opcodes with a zero baseline | **0** predicted (39-opcode profile identical on 3 of 3) | **≥1** near-certain from 332 catalogued-never-seen; `0x00C3`, `0x0084`, `0x00F7`, `0x00F9` are each **0 of 22,524**, and 19 c2s + 17 s2c item opcodes are each 0 (§4.16a, §6.4) |
| new *message class* | **none** — every char-select opcode is already in the 155 | **price / quote / stock / transaction**, plus **identify / salvage / item-replace**, four systems at n = 0 |
| what it unblocks in §8 | nothing. §8.4's coverage denominator moves by ≤ 2 of 82; §8.5's 990 words by 0 | §8.1 (new opcodes must round-trip, and vendor payloads are `string16`-bearing), §8.8 entirely, §8.6's first economy rows |
| policy exposure | **worse**, marginally: three logins and logouts inside ten minutes is a less human cadence than one login and a walk | one login, one walk, human cadence |
| operator minutes | 5–8 | ~30 |
| scorable without `marks.py` | **yes** — a connection with `map_id == 0` *is* its own label | **half**; see §10.5 |

**Commit: the merchant, and it is not close.** The sweep deepens a class whose distinct-tuple curve has already
flattened — the last two connections of the existing corpus added 0 and 0 new tuples, the same saturation §1.8
measures for opcodes — while the session is the only remaining act that converts whole absent systems from n = 0.
An unmeasured system beats a saturated one, and the sweep is not merely smaller, it is **predicted to be zero**,
which is what makes it a good control and a bad experiment. **Keep it: run it as step 2** and require it to
reproduce 47 records / 18 tuples / 39 opcodes. If it does not, something changed on the account and every later
number in the session is suspect before it is collected.

### The prediction, stated first — and a second one the panel cannot dodge

Keep the discovery framing from the refuted version: **the reply set of the first merchant open will contain at
least one GAME_SMSG opcode with a zero-occurrence baseline over 22,524 messages.** Let the corpus name it rather
than asserting `0x00F9`. If `0x00C3`/`0x0084`/`0x00F9` are what appears, Headquarter's naming is corroborated by
an independent leg for the first time; if something else appears, we have learned more.

**The candidate list, named, because naming it is the only way the prediction can be scored — and it is the one
place this document says WHICH opcodes the session would light up. [UPSTREAM]** These are ldufr/Headquarter's
names out of `opcodes.h`, adopted from the mirror and **uncorroborated by our corpus by construction** — that
they are absent is the whole point, so the corpus cannot be the second leg and §9.3's Headquarter
derivation-register row asks for exactly this list with an independent `why` per row:

| Headquarter name | opcode | occurrences in canon-12 |
|---|---|---|
| `GAME_SMSG_MERCHANT_WINDOW_OPEN` | `0x00C3` | **0** of 22,524 |
| `GAME_SMSG_TRADER_WINDOW_OPEN` | `0x00CD` | **0** of 22,524 |
| `GAME_SMSG_ITEM_PRICE_QUOTE` | `0x00F7` | **0** of 22,524 |
| `GAME_SMSG_ITEM_PRICES` | `0x00F9` | **0** of 22,524 |
| `GAME_SMSG_WINDOW_ADD_ITEMS` | `0x0084` | **0** of 22,524 |
| `GAME_SMSG_UPDATE_GOLD_STORAGE` | `0x0141` | **0** of 22,524 |
| `GAME_SMSG_ITEM_UPDATE_QUANTITY` | `0x0139` | **0** of 22,524 |
| `GAME_SMSG_ITEM_CHANGE_LOCATION` | `0x014B` | **51** of 22,524 |

**Seven of the eight are zero and the eighth is not, which is worth more than eight zeros would have been.**
`0x014B` occurs 51 times — §6.4 already lists it in the *seen* column — so one Headquarter economy name is
already testable against ArenaNet's own traffic today without spending a session on it, and any claim that
"the economy family is 0 of 22,524" must say *seven of these eight* rather than all of them. The other seven
are the zero baseline the prediction above is scored against.

That half is near-unfalsifiable with 332 never-seen opcodes in the catalogue — the critic is right — so it is not
the prediction that earns the run.

**[OBSERVED] 10.6 `0x0161` field[9] is a per-instance gold value**: non-zero on **84 of 394 records (21.32%)**
over eight distinct values `{2,3,4,5,9,10,11,47}`, and **7 of 59 `(item_type, model_id)` pairs carry more than
one** — `(24,328)` spans `{2,3,4,11}`, `(27,415)` spans `{2,3,4}` — so it is rolled per item, not a per-model
constant. (§5.2 refutes the reading of field[9] as the *equipment requirement*; that is modifier `0x2798`'s
argument. This is a different claim about the same column.) So predict, before the run:

> **The merchant's quoted price for an item already declared on this connection is a function of that item's own
> field[9] and of nothing else in its record.**

This is falsifiable, it has an 84-observation baseline, and — the reason it matters — **it does not need the panel
recorded**, because the quote carries the item id and the item id already carries field[9] on the wire. It is the
one result in §10 that survives a session that fails to be labelled.

**The control that can fail.** Re-open the same merchant with nothing changed: no sell, no buy, no map change. The
two reply sets must be identical modulo timestamps and ids. If they are not, the panel carries per-open state and
no invariance argument survives.

**The one variable.** Re-open after a map transfer. That moves server state without touching gold, inventory or
stock. Selling moves all three, which is why nothing is sold until the census is closed.

**Get the list's end from the `array32` count field, not from a flush boundary** — the flush-boundary technique is
refuted (§5.1).

### The ordered operator script

~30 minutes, one client, no scripted input. Every step's `text` is written into the plan file **before** the client
launches and its sha256 goes into `manifest.json`; the operator advances the cursor with the mark hotkey and never
types during the run.

| # | step | why it is HERE and not elsewhere |
|---|---|---|
| 0 | **Pre-flight, offline** — the fourteen items above, plus expose `t0` from `tape.load_tape` and land `marks.py` + `test_marks.py`. Write and hash the plan file. Record **Reforged Mode**. | `marks.py` must exist before, not after; §10.5 |
| 1 | **`wirecapture` starts BEFORE the client**, and any game connection whose c2s does not open with `VERSION` is a loud warning. | §1.2c row 1 lost six game connections to a decoder that had never seen the game VERSION shape. The same class of defect eats this session silently. |
| 2 | **Character select: touch nothing.** Let it settle ~10 s, mark, select the character that has been played before. | This is the **control**, not a sweep. It must reproduce 47 records / 18 tuples / 39 opcodes. A disagreement invalidates everything downstream and is cheapest to learn first. |
| 3 | **Ascalon City, stand still 30 s.** Mark start and end. | The quiet-window baseline §4.15's null needs (`0x009F` runs at 0.378 per 350 ms idle window). Before any panel exists, so no panel can contaminate it. |
| 4 | **Merchant (Sanura). Open, read, close. Sell nothing, buy nothing.** ~60 s. Mark open and close. | The whole point. Open-only, because selling changes gold *and* inventory *and* stock. |
| 5 | **Re-open the same merchant immediately.** Mark. | The invariance control, with nothing changed. Must be first, because every later step changes something. |
| 6 | **Weaponsmith (Arthur Ayala or Elias). Open, craft nothing.** Mark. | A crafter is a **different service family** from a merchant, so `0x003B`'s HIGH byte moves — the axis the refuted dialog sweep (§5.2) should have used, and **all 22 captured selects carry high byte 0x00**. It also refuses for want of materials, and the refusal is the client-side affordability check §2.3 read out of `VnGuildAddService:969`. |
| 7 | **Skill trainer (Halbrik). Attempt to open.** Mark either outcome. | Third service family. WIKI: Halbrik teaches only level 10+, so a refusal is a *likely* and still-informative result — record which. |
| 8 | **Open the bag. Mark `inventory-open`.** Read the item names. Any name beginning with "Unidentified" is the sample; if there are none, mark `no-unidentified-items` and skip to 12 — **that is a result, not a failure.** | §4.17. Before the kill, because the kill may add an item and the pre-state is what the diff is scored against. |
| 9 | **Mark `identify-1`, wait 2 s, identify ONE item. Wait 5 s.** Write down the item's name before and after, and every stat line the tooltip now shows that it did not. Repeat as `identify-2`, `identify-3`, 5 s apart. | §4.17's discriminating observation: the pre/post diff settles whether every drop record in the vault is complete or censored. The written line **is** the ground truth. |
| 10 | **Control: mark `identify-repeat`, attempt to identify an already-identified item.** | The client should refuse locally (string id 2514). If a c2s message goes out anyway, that is a finding: the client does not pre-filter and the server's refusal path is observable. |
| 11 | **Mark `salvage-1`, wait 2 s, salvage ONE low-value item with an ordinary kit.** Write down what came out, how many, and whether the item broke. **Repeat once on the SAME item type as `salvage-2`. Stop at two.** If an Expert/Superior kit is on hand and any item carries an upgrade component, mark `salvage-expert`, open the dialog, **write down every option in order before choosing**, then choose the first. | §4.18. Two trials of one type is the determinism control and is the opposite of farming. The option list is the deliverable; the choice is not. If Pre-Searing sells no Expert kits (`studies/presearing/MANIFEST.md` §Services), mark `no-salvage-kit` and say so. |
| 12 | **Transfer to Lakeside County (146). Engage one creature of definition slot 1442 or 1434. Kill it. Do NOT loot yet.** Mark engage and death. | The map transfer is step 13's one variable. Not looting yet keeps the merchant control clean. |
| 13 | **Transfer back to Ascalon City. Re-open the SAME merchant.** Mark. | §10's one variable: server state moved, gold and inventory did not. |
| 14 | **Transfer to Lakeside again. Engage the same creature type.** Mark. | Settles whether the definition-slot→stat-block key of §6.1 holds beyond n = 1. Repeating one creature twice across a re-entry is the *opposite* of grinding. |
| 15 | **Loot the drop, if there is one.** Mark. | §10.4 — the loot→bag edge is 0 of 22,524. Last, because it is the first act that changes the inventory the tuple census counts. |
| 16 | **Log out through character select, do not kill the client.** | A second `map_id == 0` connection in the same session, for free, and a clean teardown. |

**Does anything interfere with anything else?** One thing, and the ordering is what handles it: **selling, salvaging
or looting changes the inventory the tuple census counts**, so every acquisitive act is pushed behind every
invariance control. Two things that do *not* interfere and might look as though they do: the kill in step 12 cannot
disturb the merchant control, because gold and inventory are untouched while the drop lies on the ground; and the
three service families in steps 4/6/7 vary `0x003B`'s high byte while holding the low byte's quest-state walk out of
the picture entirely (§5.2 — quest codes are a one-way state machine and unrepeatable; vendor families are not).
One thing that *does* and is deliberate: step 9 changes item records that step 15 may then re-declare, which is why
the identification block sits before the kill and the loot sits last.

**Why identification and salvage belong in the same session rather than their own.** The merchant opens a message
class the corpus has never held; so do these, and it is a *larger* one — nineteen c2s opcodes and seventeen s2c
opcodes against the merchant's handful. Neither requires combat, both are single clicks, the client is already
running, and the marks cost the same either way.

**What each outcome means.**
- *The stock list arrives with prices* → type-(c) deterministic economy is unlocked. Write the row as
  `source='capture'` with the capture stamp; upstream catalogs become permitted cross-checks, not sources.
- *The price is a function of field[9]* → §8.6's compiler gets its first economy rows and 84 existing observations
  become training data. *It is not* → the quote carries server state the item record does not, which is itself the
  finding, and the next question is what else the quote names.
- *The panel opens and nothing arrives* → the stock is client-side or arrives on request, and the next question is
  which c2s opcode the panel sends — which **§4.11's sweep has already answered if it was run first**, at n = 332
  instead of n = 2. Restated from the draft, which said "loopback cannot substitute": **loopback cannot substitute
  for the server's numbers; it can and should supply the opcode → panel → request binding before the session.**
  `0x00C3`'s handler at `0x0091F230` is confirmed to be ten instructions into `0x00813F80`, which copies two
  arguments and two globals into a stack struct and posts frame message `0x100000B5` with no bounds check and no
  assert — but `0x0084` and `0x00F9` are **accumulators, not posts** (§4.11d), so loopback *can* load a panel's
  contents and then open it.
- *The identify diff grows the modifier array* → every drop record in the vault is censored and §4.2/§4.3/§8.4/§8.5
  are computed over incomplete data. *It does not* → every drop we have captured already contains the full roll,
  and the item-generation arc needs no identification step.
- *The control fails* → per-open server state exists, which is itself a finding about the merchant's design and
  kills the invariance framing before anyone builds on it.

### 10.5 The instrumentation precondition, and `marks.py` to the file

**Is the session scorable today? Plainly: no, not fully.** §3.2 establishes that `labelrun.py` writes through *our
own server's* recorder and there is no Rurik process in a live capture, so both live captures are NARRATED and
never LABELLED. Under that instrument:

- **Step 2 is scorable today.** A character-select connection is a whole TCP connection with `map_id == 0` in its
  own VERSION frame. The connection boundary *is* the label. That is the sweep's one real advantage and it is not
  enough to buy it the session.
- **Steps 4–7, 9–11 and 13 are half-scorable.** `cmsgstream.timed()` already puts both directions on one absolute
  clock, and every operator action that reaches the server leaves a c2s message — `0x0039 INTERACT` (29 in the
  corpus), `0x003B NPC_SERVICE_SELECT` (22), `0x00C1 TARGET_SELECT` (75). So "the panel opened" is bracketed to the
  message *provided the operator does exactly one thing at a time*. What c2s cannot do: say **which** panel,
  distinguish two opens of the same one, record what the human saw, or notice anything purely client-side.
- **The falsifiable half of the first prediction is unscorable without marks.** "That opcode's payload contains the
  item ids visible in the panel" needs the panel's contents on the capture's clock, and no instrument in this repo
  produces that. §10.6's field[9] prediction is the hedge — it is deliberately built to survive an unlabelled run —
  but it is a hedge, not a substitute. And §4.17's tooltip line is ground truth that exists **only** on the
  operator's paper unless a mark points at it.

So: `marks.py` is a **precondition**, not a rider. It is an hour.

#### 10.5.1 `toolkit/harness/marks.py` — specification

**What it is.** A `{t, kind, text}` writer that puts a human-readable, *pre-registered* label on the
same clock as `wire.jsonl`. It is the entire difference between the live corpus being narrated prose
and being a dataset.

**What it is not, and this is load-bearing.** It **reads** the keyboard and never writes it. It may
import `ctypes` and call `RegisterHotKey`/`GetMessage` (or `GetAsyncKeyState`); it must **never**
import or call `SendInput`, and `test_marks.py` asserts that from the syntax tree the way
`test_dispatch.py` asks the AST about its `else` chains. `drive_client.hold_key` is the thing on the
other side of that line, and the live rule turns on the difference.

**Input: a plan file, written before the client launches.** One step per line, `kind<TAB>text`, e.g.
`open<TAB>merchant Sanura, first open`. The plan *is* the pre-registered prediction — a probe states
its expectation first, and after the run the plan is what the marks mean. Its sha256 goes in
`manifest.json`.

**Trigger.** A global hotkey, because the client owns the foreground:

- `VK_F9` → **advance**: emit the next plan step.
- `VK_F10` → **repeat**: re-emit the current step (the operator did it again).
- `VK_F11` → **note**: emit `{"mark": "note"}` with **no text**. Text is added afterwards by
  ordinal, by editing the plan — never typed during the run, which keeps operator PII out of the
  capture by construction (§9.5 already has one leak it cannot clean).

Prefer `RegisterHotKey`, which **swallows** the key, over polling `GetAsyncKeyState`, which does not:
GW binds the F-keys, and a mark keypress that also does something in-game changes the traffic being
measured. If `RegisterHotKey` fails (already held), **refuse** — do not fall back to polling.

**Output: ~~`marks.jsonl`~~ `plan_marks.jsonl`, beside `wire.jsonl` in the same capture
directory. CORRECTED 2026-08-13, when the module was built.** `marks.jsonl` was already
taken: `livesession.py:735` opens it in `"w"` and holds the handle for the whole session
while `behaviourrun.py:385` reads it back, and both shapes use `"kind": "mark"` — so two
writers on one file is silent loss in the one artifact a live run cannot reproduce.
**The owner then ruled the split PERMANENT (2026-08-13): "driver marks and operator marks
are different things."** That is the load-bearing reason and it outlives the filename
clash — the driver's channel is the harness narrating itself with no prediction attached,
this one is a human acting against a plan sealed before launch, and merging them would put
pre-registered and un-pre-registered rows under one `"kind"` where no consumer could
separate them. The record SHAPE below is unchanged.

```
{"kind":"marks_meta","plan_sha256":"…","steps":17,"t0_perf":…,"t0_wall":…,"pid":…}
{"kind":"mark","seq":1,"mark":"advance","step":0,"text":"character select, settled",
 "t_perf":…,"t_wall":…}
```

**Binding to the wire clock, and the check that makes it a claim.** `wirecapture.open_capture`
stamps every segment `"t": clock() - t0` with `clock = time.perf_counter`, and it runs as a
**separate subprocess** launched by `livesession.run` — so `t0` is not in the marks process. Add two
fields to the existing `wire_meta` record: `"t0_perf"` and `"t0_wall"`. Then
`marks.bind(wire_path, marks_path)` returns `[(t, mark, step, text)]` on wire time by computing
`t = t_perf − t0_perf`, and **asserts** `abs((t_perf − t0_perf) − (t_wall − t0_wall)) ≤ 0.250` for
every mark, raising and naming the drift otherwise. Writing both stamps is the whole point: it turns
"`perf_counter` is comparable across processes on Windows" from an assumption into a measurement the
artifact can refute. A check that cannot fail is not a check.

**And it is why `t0` must be exposed.** A *tape* event time is relative to that connection's first
s2c segment (`tape.py:213`, computed and discarded), so a mark in wire time cannot be joined to a
tape until `load_tape` returns its `t0`. `marks.on_tape(info, marks)` subtracts it. The one-line
change §7 already asks for is what makes `marks.py` usable, and `marks.py` is what makes it
load-bearing — land them together.

**Refusals, each of them a failure that has already happened in this project in some other form.**
No plan file → refuse; an unlabelled run must not be reachable by accident. Plan sha256 disagrees
with `marks_meta` → refuse. No `wire.jsonl` in the directory → refuse. A mark whose `t_perf`
precedes `t0_perf`, or a `wire.jsonl` with no `wire_meta` line → refuse, naming it as the
capture-started-late defect (`20260807T124912`) arriving from the other side. Advance past the last
plan step → refuse rather than wrap.

**Compatibility, checked rather than assumed.** Marks live in a sibling file, so nothing that reads
`wire.jsonl` changes. If they are ever inlined instead, note that `tape._segments`,
`wirecapture.load_connections` and `load_wire` all filter on `kind == "wire"` and would ignore a
`{"kind":"mark"}` line — but `origin.origin_of` reads **every** record looking for contradictions, so
a mark must not carry an `origin` field.

**`toolkit/harness/test_marks.py`**, stdlib-only, against a fake `user32` the way `test_harness.py`
fakes it for `hold_key`. Criteria and controls are §8.9. Route the verdict through `toolkit/checks.py`
with a `floor` set from a real green run, and **add the line to CLAUDE.md's suite list in the same
commit** — the suite is 49 files today, and a test not named there is a test nobody runs.

---

## Revision note

This document was produced on 2026-08-11 by a **19-agent research pass** — five census agents
measuring the ground, a proposal cohort producing thirty-nine techniques, and six adversarial lenses
with a standing instruction to refute by measurement — followed by **one completeness critic** and a
**6-agent revision pass**, each fixer measuring one region of the critic's punch list rather than
rewriting prose.

**The critic's re-derivation reproduced the draft's measured half exactly**, from an independent
reader: 12 connections / 22,524 GAME_SMSG / 398,945 B / 758.0 s / 155 opcodes / 12-of-12
`consumed == total, err is None`; `0x0161` 394, `0x0020` 1,068, `0x0168` 7, `0x0135` 2, `0x00EE` 17,
`0x0056` 126, `0x001E` 6,928; 21-of-155 named, 332 catalogued-never-seen; the six `0x10` status words
resolving to four distinct first deaths; §6.1's 28-row `PROP_HEALTH_MAX` table including slot
1434→8 twice across captures, characters and agent ids; §6.2's per-opcode round-trip split with zero
length differences; 231/394; numpy 2.4.4 and scipy 1.18.0 both importing; 49 test files. **The
measured half of the draft survived adversarial re-derivation intact.** What did not survive was
denominators, three unfalsifiable criteria, and completeness.

**What this revision changed.**

- **Every percentage, ratio and count restated on canon-12**, with a per-figure comparison table
  (§1.9) whose BIG-10 column reproduces the draft to the digit — the control that says only the
  denominator moved. §8.1's baseline goes 127 → **133**, and §6.2's "two defects" collapse into one:
  the 133 that fail to re-encode are exactly the 133 carrying U+FFFD.
- **§1.2 rewritten from the artifacts, against both the draft and the critic.** The draft's "no game
  key" and the critic's "the sniffer attached mid-stream" are both refuted: seven keys were tapped,
  six died in memory, and all 7 connections open cleanly under today's splitter. Key recovery is
  **retired as arithmetically closed**, and the six-run success-rate table (§1.2c) is new.
- **Three flat §0 claims demoted to the labels of the sections they summarise**; the class tag
  restated as a little-endian dword with its wire bytes (`31 6E 6F 6D`) and its full five-value
  vocabulary (§1.5a, `band` at 37 rather than the critic's 4); the duration restated at 12.11 min
  with all six denominators shown.
- **§2.8's 28-row system census replaces the uncheckable "eleven candidate systems, two genuinely
  server-only"**, and **§2.9 adds skills** — the largest half-mirrored system, absent from the draft
  entirely — including the first client-side skill constant ever checked against ArenaNet's own
  traffic (1 of 41 columns, `+0x4C`) and the closure of a NOT FOUND `studies/skills` has carried
  since 2026-08-05.
- **Two whole technique classes added**: §4.11's generalised 332-opcode loopback stimulation sweep
  (Tier 1, and it now outranks §10 on the document's own metric because it costs no human minutes),
  and §4.16a–§4.18's identification and salvage class (Tier 2), which also names bit 23 as the
  UNIDENTIFIED flag and so resolves what §4.2's six one-bit violations were.
- **§8.3, §8.4 and §8.5 rewritten so a wrong implementation goes red.** All three previously restated
  outcomes already measured, and §8.5's headline could not fail at all. §8.7–§8.9 are new; the old
  §8.7 is now §8.10.
- **§10 rebuilt**: the operational envelope named (stock-DH `run-live/`, `accounts.py`'s automation
  opt-in, no `--host`, **the operator plays and the driver sends nothing**), a fourteen-item
  pre-flight derived from §1.2c, the critic's character-sweep alternative measured and refuted (0, 0
  and 1 new tuples) then kept as a control, `marks.py` promoted from a closing sentence to a
  precondition and specified to the file, and a sixteen-step operator script.
- **§3.1's second behaviour oracle resized and its own frame demoted.** O2 goes 919 → **971
  over the canonical twelve, 29 opcodes, `0x003D` at 44.3% rather than "half"; and "the repo owns
  twelve oracles" is relabelled **RECONSTRUCTION** rather than quoted as a measured count, since it
  is a partition this pass invented and one of its members is several grants-nothing mirrors.
- **Numbering repaired so every internal cross-reference resolves.** §9's five owner decisions are
  numbered §9.1–§9.5 rather than left as an unnumbered list that four other sections cite by number,
  and §10's two uses of "10.5" are separated: the `marks.py` precondition keeps **§10.5** and the
  field[9] price prediction becomes **§10.6**. Audited mechanically: every `§N.N` reference in the
  finished document resolves to a heading or a labelled claim, and the only three that do not are
  references to other documents (`PLAN.md` §8.0, `studies/enemy/PLAN.md` §6g, `studies/skillcast`
  §14.4).
- **§7.1 restated** per the critic, because as drafted it contradicted §7.4. **§9.4 now states that
  the default for both bulk exports — asserts and §4.9's 476 decoded string runs — is REFUSAL under
  the top of `CLAUDE.md`, pending an owner ruling.**
- **Corrections to the draft's own numbers, each kept beside the reason it was believed**: assert
  expressions 19,620 → **19,758** (19,620 is the edx-first shape alone); vendor assert sites 345 →
  **298**; `ITEM_CREATE_BAG` "9 on 10 of 10" → **9 on 12 of 12, 108 rows**; `ITEM_FORMULAS`
  un-CONTESTED (20-byte records, wrong stride in the original probe); the quest-id shift
  `code & 0x0FFF` → **`(code >> 8) & 0x0FFF`**; §4.5's `0xA0F8` exemplar replaced because it stops
  being a constant on canon-12; §4.12's "six identical shims" corrected to three shims and three
  bodies; `msghandler.py`'s 477 labelled a **floor** with `0x000C`/`0x000D` CONTESTED at 145 and 144
  occurrences; `ITEM_MOVED` counted at 109 with the loot→bag edge at **0 of 22,524**;
  `0x0060`/`0x0084`'s `CHAR_CREATE` naming CONTESTED at 15-of-15 and 105-of-105 on character select.

**What was adversarially checked and what was not.** Everything in §1, §2.8, §2.9, §4.11, §4.16–§4.18,
§6, §10.1–§10.6 has been measured by at least two independent readers in this tree. §5's graveyard
entries were each measured once, by the lens that killed them, except where §1.9 flags a denominator
that moved — **§5.1's 22.5% merge rate and §5.2's "exactly one of 151" have not been re-derived on
canon-12 and must not be quoted until they are.** §4.15's idle-window figures (0.378 per 350 ms, 97 of
429) are BIG-10 and also un-re-derived. Nothing in §7 beyond the arithmetic is measurable by
construction — that is what the section is.

### Fix pass, 2026-08-11 (after the audit)

**An independent audit re-derived this document's numbers from the vault and found that six of them
were wrong — including three inside the regions the paragraph above called adversarially checked.**
That is the honest half of the result and it is written here rather than smoothed over: *"measured by
at least two independent readers"* did not stop a census tally, a saturation figure and an inventory
split from shipping wrong, and two of the three were wrong **in the direction that flatters the
thesis**. Every figure below was re-measured in this tree before it was edited.

- **The system-census tally was wrong in two places (§0 and §2.8), both flattering.** The table's own
  verdict cells count **3 FULLY CLIENT-SIDE / 12 HALF-MIRRORED / 13 SERVER-ONLY**; both prose
  statements said 3 / 15 / 10. Recounted here by parsing the 28 rows and reading the verdict column,
  which is also what row 15's escaped `\|` had defeated. The follow-on sentence is restated from the
  rows themselves: **thirteen SERVER-ONLY, of which nine are reachable by O1 at n ≥ 1 (2, 3, 11, 12,
  13, 15, 16, 23, 27), three are at n = 0 (5, 24, 25), and one (28) names no instrument at all.**
  The draft said seven and three of ten.
- **§1.8's "the entire third capture adds thirteen" was false, and correcting it makes the section's
  thesis stronger.** Measured per capture: `20260807T143055` alone 153 distinct GAME_SMSG,
  `20260810T235916` alone 153, their union **155**, and `20260807T133758` adds **zero** over that
  union. The 13 was `:54560`'s within-capture step over `:54557` — a point on the cumulative curve
  mislabelled as a capture's marginal contribution. A whole third session, chronologically first,
  adding nothing is a better result than one adding thirteen.
- **And confirming §1.9's "catalogued never seen" row found a third error in the same family.** The
  row read 332 / 332 / 332; chain-8 carries only **148** distinct opcodes, so its cell is **339**.
  §5.1's Chao1 entry had been quoting the correct 339 all along, in the same document.
- **§6.2's "the five it named are 105 of the 133" mixed denominators inside the section that exists
  to fix denominators.** Those five (`0x004C`, `0x0161`, `0x0080`, `0x005D`, `0x0056`) are **111 of
  133** on canon-12; 105 of 127 is their BIG-10 figure. The whole per-opcode table was re-derived and
  reproduces to the row, canon-12 and BIG-10 both.
- **§10.4's `ITEM_MOVED` split did not reproduce.** Joined the repo's own documented way
  (`test_smsgnames.py:436-445`, bag type resolved per connection from that connection's own
  `CREATE_BAG` rows), the 109 placements are **55 backpack / 54 equipped**, not 72 equipped / 37
  backpack, and the character-select staging is **51 = 17 × 3**, not 33. 51 + 4 = 55 closes exactly.
  **All three load-bearing conclusions around it survived unchanged and were re-verified**: zero
  placements into a type-4 or type-5 bag on 12 of 12; the four quest-reward placements on exactly
  `:64103`, `:64102`, `:49163`, `:49160`; and neither drop connection (`:62994`, `:61624`) carrying a
  backpack `ITEM_MOVED`.
- **§2.5's "returns 21 sites" does not reproduce from the tool.** `asserts.py --grep` compiles with
  `re.I` and returns **44**; case-sensitively the same pattern returns **29**. Neither is 21. Both
  counts and the reason they differ are now stated, and the conclusion is unchanged — but the section
  now says which number it rests on, because two of the three game-logic sites (including
  `VnCollect:441 trophyHasLootDef`) are reachable only through the case-insensitive run.
- **§5.2's "990/990 words congruent 0 mod 8" was literally false.** Only **763 of 990** whole words
  are ≡ 0 mod 8. The true statement, and the one the refuted `identifier = w >> 16` reading was
  actually about, is that the **high half** is 8-aligned in **990 of 990**. Since the sentence claims
  a re-measurement over all 394 canon-12 records, it now states a measurement that was made.

**Four acceptance criteria that could pass vacuously were rewritten**, which is the same defect §8.3
and §8.4 were already rewritten for and which this document indicts in §5. §8.7 control (b) was
"printed beside the score" where §8.3's own rewrite says printing is not a criterion — it is now a
20-point threshold on the predicted-effectful versus predicted-silent effect rates, plus a **new
positive control**, because a sweep with a dead transport records "silent" for all 332, emits 332
rows, clears every old control and passes. §8.8 control (a) was a disjunction every outcome satisfied
("or the run must name which other fields moved" — which is what a diff *is*); it is now a named-field
assertion plus an identical-inputs sabotage. §8.2's headline was an already-measured outcome quoted as
a pass condition; it is demoted to a reported shape and the criterion moves onto the agent-38-on-
`:62994` `anim` trap, which is failable because it has already failed. §8.1 had no sabotage while §8.6
mandates one: a `string16` that stashes and replays the original bytes passes both of its clauses
today, so the criterion now requires a decoded surrogate to survive a
decode → mutate-a-neighbouring-field → encode cycle.

**Three things the revision had dropped are restored.** The eight upstream-named economy opcodes are
back at §10's prediction, labelled UPSTREAM and with their measured occurrences — and measuring them
corrected the audit as well as the document: **seven are 0 of 22,524 but `ITEM_CHANGE_LOCATION`
`0x014B` is 51**, which §6.4 already listed in its *seen* column, so one Headquarter economy name is
testable today. The `cmsgstream.timed` join's concrete size **(419 + 11,241 messages on one absolute
clock)** is back in §3.3. And `0x0091F230` was re-disassembled: it is **ten** instructions
(`push ebp` … `ret`) calling `0x00813F80`, so §10's figure stands and no 11-instruction claim survives
anywhere in the finished document.

**What this pass did not do.** It did not re-derive §5.1's 22.5%, §5.2's "exactly one of 151" or
§4.15's idle-window figures; those three remain flagged above. It changed no verdict, no label and no
conclusion — every conclusion whose supporting number moved was re-checked and survived, and where a
number moved the direction is stated.
