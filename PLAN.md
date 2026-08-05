# Rurik — the hardened plan

**Companion to [HANDOFF.md](HANDOFF.md), which it corrects rather than replaces.** Written
2026-08-04 from a nine-agent recon sweep, three adversarial critiques, two focused
reverse-engineering passes, and direct measurement of the local install and the mirrored prior art.

HANDOFF.md's *strategy* survives intact: the live game is the donor, archaeology beats invention,
capture is a wasting asset, the defect follows the authorship, and Pre-Searing is the finish line.
Its *mechanism* does not. Nearly every implementation choice in §3, §4, §5 and §7 was made against
a picture of the field that turns out to be four years stale.

Confidence is marked throughout. **[measured]** means this session verified it directly against
`C:\gw` or a mirrored repo. **[sourced]** means a cited primary source. **[probe]** means it is a
hypothesis with a specific experiment attached, and it is not yet a fact.

---

## 1. What changed, ranked by impact

### 1.1 The field is not dead. It is the most active it has been in a decade.

HANDOFF.md §1 and §4: *"roughly fifteen years of intermittent community attempts (GWLP-R in Java,
sgwlpr in Scala) produced zero playable outcomes."* This is the load-bearing premise for the whole
"R4 is pure authorship, and that is fatal" argument. It is wrong.

| Project | What it is | State **[measured]** |
|---|---|---|
| [gw-preservation/server](https://github.com/gw-preservation/server) | A GW1 **server in Go** — the most advanced effort in the field | pushed **2026-08-04 19:07 UTC**, i.e. hours before this was written. **No license = all rights reserved.** |
| [ldufr/OpenTyria](https://github.com/ldufr/OpenTyria) | A working GW1 **server** in C | 180 commits, last 2026-02-21, **Unlicense (public domain)**, ~25,630 lines of real code |
| [ldufr/Headquarter](https://github.com/ldufr/Headquarter) | A GW1 **headless client** in C | MIT, 496 commits, pushed 2026-07-11, tracking live builds to 38688 |
| [gw-preservation/network-logger](https://github.com/gw-preservation/network-logger) | Drop-in DLL logging **100% of game↔client traffic** | pushed 2026-07-25. No license. |
| [apoguita/Py4GW_Reforged](https://github.com/apoguita/Py4GW_Reforged) | Live successor to Py4GW | pushed **2026-08-04 19:53 UTC**. No license. (`apoguita/Py4GW`, 68★, was **archived 2026-07-21**.) |
| [Fournux/Tyria-Extractor](https://github.com/Fournux/Tyria-Extractor) | `Gw.dat` → skills/items/quests/NPCs, plus a sniffer | **MIT**, Rust, created 2026-06-30 |
| [gwdevhub/GWToolboxpp](https://github.com/gwdevhub/GWToolboxpp) | The in-client toolbox | 872★, MIT, pushed **2026-08-04** |
| [build-wars/gw-skilldata](https://github.com/build-wars/gw-skilldata) | Community skill dataset | MIT, pushed **2026-08-04** |

Four repositories were pushed to on the day this plan was written, two of them within the hour. The
`gw-preservation/server` tree carries **397 map definitions** (essentially the whole game), a real
`Gw.dat` trapezoid navmesh with A* and line-of-sight, working map portals with spawn coordinates,
character creation, dye, emotes and cartography, plus a from-scratch TLS-SRP portal — with commits
like `fix world/movement tick sync` and `trap pathing impl` landing this week. It pins
`clientVersion == 37600`, a **pre-Reforged** build, which is its one significant limitation.

`entice` (the GWLP-R successor org) is genuinely dead — last activity 2016 **[measured]** — so the
handoff's pessimism was accurate *as of about 2016* and has not been revisited since.

**But the sober conclusion survives, for a better reason than the handoff gives.** At least four
independent projects have driven a real client to character select, into a map, and moving:
GWLP-R (2012–13), entice (2015–16), OpenTyria, and gw-preservation. **Nobody has ever built R4.**
No combat, no skill engine, no AI, no spawns — not in fifteen years, not in any repo any of this
research could find. `entice/skill`, whose description was "Defines skills. All of them.", is
marked DEPRECATED. That precedent lands *precisely* on Rurik's actual deliverable, which makes it
a sharper warning than the one HANDOFF.md gives, not a weaker one.

**Consequence, stated carefully:** R1–R3 drop from research to transcription, because working
reference implementations exist for all three. R4 remains exactly as hard as the handoff feared —
and it is now unambiguously *the* project, rather than the last third of it.

**License discipline matters here.** OpenTyria is public domain and Headquarter is MIT, so both are
freely usable. `gw-preservation/*` and `Py4GW_Reforged` carry **no license at all**, which means
all rights reserved: read them, learn from them, cite them — never copy from them.

### 1.2 The packet catalog already exists, in the public domain

HANDOFF.md §5: *"Extract the packet catalog into a machine-readable schema and codegen from that
one source. Hand-maintaining three parallel copies of 400+ packet definitions is how this project
dies of paper cuts."* Correct instinct. Already done by someone else.

OpenTyria's `code/msgdefs.c` is a declarative message-schema table **[measured]**:

| Direction | Count |
|---|---|
| `AUTH_CMSG` (client → auth) | 57 |
| `AUTH_SMSG` (auth → client) | 39 |
| `GAME_CMSG` (client → game) | 194 |
| `GAME_SMSG` (game → client) | **487** |
| **Total** | **777** |

Each entry is a field list over a 15-type vocabulary: `MSG_HEADER`, `DWORD`, `WORD`, `BYTE`,
`FLOAT`, `STRING_16`, `AGENT_ID`, `BLOB`, `VECT2`, `VECT3`, `ARRAY_8/16/32`, `NESTED_STRUCT`.
`GameMsg.h` and `AuthMsg.h` add 84 and 24 hand-typed C structs on top.

Two things make this decisive. First, **Unlicense means public domain** — there is no license
friction at all, unlike GWCA. Second, the 487 game-server messages **independently match Py4GW's
separately-reported 487 StoC headers**, which is real cross-validation from two unrelated projects
against the current client.

**But the real authority is inside the client, and nobody has ever read it.** The client
deserializes with a table of `{uint32_t *packet_template; uint32_t template_size; handler_func}`
against `STOC_HEADER_COUNT = 0x1e5` (485) **[sourced — GWCA's `StoCMgr_old.cpp`]**. GWCA resolves
that pointer, asserts the count, and then uses **only `handler_func`** — the loop over
`packet_template` was never written. The tag encoding is documented by working code in GWLP-R-Utils'
`PacketTemplate Dumper`, and the type system it describes has sized integers, 1–3 floats, opaque
handles, fixed blobs, UTF-16 strings and length-prefixed arrays, with **no unions, no bitfields and
no conditional layouts** — because the client's generic deserializer cannot express them. That
settles the schema-language design question with evidence rather than speculation, and it matches
OpenTyria's 15-type vocabulary closely enough to be the same discovery arrived at twice.

This matters because four corpora disagree about what the catalog even is: GWLP-R has 773 ID slots
with 252 named, its dumper reported 752, GWCA names 217 StoC with 123 structs, OpenTyria defines
487 game-server messages, and Py4GW observes 487 live. Codegen off the wrong one and you find out
when fixtures fail, after the schema has calcified. **The client's own `template_size` is the
arbiter**, and any external corpus that disagrees with it is a *mechanically detectable* defect —
which makes the whole reconciliation job safely delegable to agents.

**Consequence:** HANDOFF §5's codegen plan keeps its architecture and loses its input problem.
Dump the client's template table, use it as truth, and treat OpenTyria's 777 definitions as the
naming and cross-check layer.

### 1.2b The capture hook point in §11 step 4 cannot produce raw bytes

HANDOFF §3 says hooking StoC dispatch yields "decrypted, framed, already-typed messages, which is
strictly better than pcap," and §11 step 4 says to write "framed, timestamped **raw** packets."
Those are incompatible. GWCA's hook swaps `handler_func` in the dispatch table, so what it receives
is an **already-deserialized struct** whose arrays and strings are pointers elsewhere. A
`memcpy(pak, sizeof(T))` truncates every variable-length field in the game — silently, for a year,
into an irreplaceable vault. Worse, the typed-callback API has no catch-all, so an opcode with no
mapped struct is *invisible* rather than merely unparsed, which is strictly worse than pcap for
exactly the packets you most want bytes of.

**Fix: hook twice.** A low hook at the post-decrypt receive boundary feeds the byte vault — the
irreplaceable artifact. A high hook at dispatch feeds a typed sidecar. The plaintext boundary is
named in this build: `MsgConn.cpp`, `MSGCONN_MODE_ENCRYPTED` and `DispatchStream` are all present
in `Gw.exe` **[measured]**. R0's acceptance criterion then becomes a real instrument calibration
rather than a test of your file I/O: *the struct stream I parse from raw bytes equals the struct
stream the client built, field for field, across a whole session.*

### 1.3 Reforged shipped an official WebAssembly client, and it is a far better RE target

Nothing in HANDOFF.md knows this. ArenaNet re-platformed Guild Wars onto a portable C++ core that
builds to Win32-x86, WebAssembly, and mobile. The artifacts are `Gw.wasm`, `Gw.js`,
`Gw.jspi.wasm`, `Gw.jspi.js`, fetched from `patching.1.arenanetworks.com` **[measured — all four
filenames and the CDN host appear throughout the mirrored `shiburito/gw_in_browser` tree, and
`jean-humann/gwnative` hard-requires all four]**.

Local corroboration: `Gw.exe` references `libEGL.dll` and `libGLESv2.dll` (ANGLE) and imports no
Direct3D at all **[measured]**, which is exactly the renderer you build to target Emscripten.
`C:\gw\THIRD-PARTY-LICENSES.md` lists only four dependencies — `jsmn`, `OpenAL-Soft`, `PFFFT`,
`stb_image` — a deliberately portable, dependency-light core.

Why this matters: a WASM module is a structured, typed format with explicit control flow and no
register allocation, so it decompiles far better than x86. `gw_in_browser` ships `wasmscan.py`,
`wasmdetour.py`, `wasmpatch.py` and `gensyms.py` **[measured — present in the mirror]**, reporting
full decode of all 17,596 functions and detour capability across them **[sourced, not reproduced]**.

**Two corrections, because the first version of this section overstated the case.** The shipped
module is **stripped** — no `name` section. What survives is better than nothing but weaker than
symbols: string literals are byte-identical to the `.exe` (same source tree), and ~850 original
source paths persist in `.data` (`../../../../Gw/Ui/UiRoot.cpp`), so `gensyms.py` *reconstructs*
per-function attribution rather than reading it off. Separately, the fully-mangled C++ names that
Py4GW works from appear to come from an **earlier, archived build** that shipped with its `name`
section intact — its function count is 18,004 against today's 17,596. Chunks are content-addressed
and retained while referenced, so retrieving that symbol-bearing build is plausible but unproven.

**And a posture warning that outranks the technical upside.** These browser harnesses reach
ArenaNet production using a shared client key lifted from the Android APK, `gw_in_browser` cannot
log in at all (its `login`/`secureStorage` paths are stubs, making it a **static-RE tool, not a
live-capture one**), and `gwdevhub/gw_in_browser` is now 404 with no stated reason. This is the
riskiest area in this document and it sits badly against HANDOFF §9's "local and personal only"
posture. Treat the WASM path as an *offline analysis* asset — which is where its real value is
anyway — and do not build the live capture story on it.

**Consequence:** HANDOFF §5's *"capture harness — C++, because it must live inside the client next
to GWCA"* is still the wrong default, but the replacement is A1 below, not the browser.

### 1.4 GWCA is no longer an open dependency

HANDOFF.md §4 calls GWCA *"your most valuable external asset."* As a runtime dependency it is not
available. `GregLando113/GWCA` has been **archived read-only since 2023-11-14** **[measured]**, and
there is no `gwdevhub/GWCA` — that path 404s **[measured]**. The maintained GWCA is closed-source,
vendored into GWToolboxpp as a prebuilt DLL, import library and headers.

**Consequence:** downgrade GWCA from *dependency* to *dictionary*. Its named opcodes and typed
structs remain the best naming corpus in the field. Do not plan to build on its DLL.

### 1.5 R1 is not patch-free — verified against your own binary this session

**This is now measured, not argued.** `toolkit/clientscan/dump_dh_params.py` locates the pinned
Diffie-Hellman parameter struct in `C:\gw\Gw.exe` by the accessor signature that Headquarter's
`dump_key.py` (which reads it) and OpenTyria's `patch-gw.py` (which writes it) both use — two
independent implementations that agree. Result on our pinned build **[measured]**:

```
match at file 0x003d7523 -> struct VA 0x00a843e8 (RVA 0x6843e8, section .rdata)
  word0 = 1     generator g = 4     prime p = 512 bits     server public B = 509 bits
  all shape checks pass
```

The scheme is static-ephemeral Diffie-Hellman in which **the server's public value B is never
transmitted** — the client already has it compiled in and derives the shared secret locally as
`B^a mod p`. A server we control cannot reproduce that secret without `b`, the discrete log of B,
which ArenaNet never shipped and which a 512-bit discrete log puts out of scope. So the client's
`(g, p, B)` triple **must** be replaced with one whose private exponent we hold.

**HANDOFF.md §4's "R1 needs no binary patching" is therefore falsified against our own binary,
not merely on someone else's authority.** `-authsrv` gets the client to connect to us; without the
patch the stream is undecryptable. `patch-gw.py` additionally NOPs a `CreateMutexA` check and
renames the mutex, which is what allows multiple client instances — directly useful for capture at
scale. Budget a client-patching step permanently, including redoing it after every ArenaNet build.

The parameters themselves are ArenaNet-derived and were written to `vault/keys/`, never the repo.

### 1.5b Why this was worth doing before touching the network

HANDOFF.md §4: *"`-authsrv <ip>` ... R1 needs no binary patching."* The flag is real — it is the
first entry in a contiguous, alphabetically sorted 41-entry argument table at file offset
`0x005371cc` in `Gw.exe` **[measured]**. But `Gw.exe`'s `.rdata` also carries a pinned 136-byte
crypto blob: two header words plus two 64-byte high-entropy values, being the Diffie-Hellman
modulus and **the server's public key**. Because the server's public key is baked into the client,
no server you control can key the auth channel without patching it. OpenTyria's `tools/patch-gw.py`
does exactly this.

**Consequence:** R1 acquires a patched-client build step, and the patched binary is a derived
ArenaNet artifact that belongs in the vault, never the repo.

### 1.6 Login is three stages, and `-authsrv` reaches only the middle one

```
Stage A  PORTAL    HTTP(S) + XML  ->  account.arena.net / webgate.ncplatform.net   <- -portal
Stage B  AUTHSRV   DH + ARC4      ->  Auth1.ArenaNetworks.com:6112                 <- -authsrv
Stage C  GAMESRV   DH + ARC4      ->  address handed over by Stage B               <- no flag
```

The best news in this document is buried here: **setting `-portal` makes the client use port 6601,
prefix every request path with `/Spawned/WebGate`, and turn its TLS flag off.** A local Stage A
therefore needs no certificate, no trust-store surgery and no SRP — just an HTTP server answering
four XML endpoints. That is why OpenTyria's `webgate.py` is a couple of hundred lines of standard
library.

Two corrections fall out of this, both recorded in [studies/handshake/PLAN.md](studies/handshake/PLAN.md):
`GwLoginClient.dll` is **not** on the client's login path (it is NCSoft's SRP stack, used by
third-party launchers; `Gw.exe` never calls it), and `-portaldll` is **dead code** — parsed into a
buffer that nothing reads. Both were promising leads earlier in this session and both were killed
by checking the call graph instead of the string table.

### 1.7 Much of the "server-only" data ships in the client

HANDOFF.md §1 and §3 assert that skill effects, AI, spawns, drops and quest logic *"lived only on
ArenaNet's machines."* Substantially overstated. `GW::Skill` is a 160-byte static client-side
structure carrying `energy_cost`, `adrenaline`, `activation`, `aftercast`, `recharge`,
`duration0`/`duration15`, `scale0`/`scale15`, `bonusScale0`/`bonusScale15` and `aoe_range`
**[sourced — GWCA `Include/GWCA/GameEntities/Skill.h`]**. The two-point rank-scaling model that R4b
most needs is readable without a server and without a capture. Zone metadata (`AreaInfo`), walkable
geometry (`PathingMap`/`PathingTrapezoid`, also derivable offline from `Gw.dat`), and NPC identity
are likewise client-side.

What genuinely remains server-only, on the evidence: absolute monster HP, energy and armor (GWCA
comments `AgentLiving.hp` as a percentage and marks `max_hp`/`max_energy` "only works for
yourself"), spawn placement, drop tables, and AI decision logic. **Four things, not a whole game.**

**Consequence:** the capture campaign gets much more sharply targeted. Capture what is genuinely
server-only; extract the rest.

---

## 2. The go/no-go probes

Ordered by information gained per unit cost. Probes 1 and 2 need a human at the keyboard — an agent
session cannot launch `Gw.exe` on this machine.

**Probe 0 — the DH parameter struct.** ✅ **Done this session.** No network, no launch, thirty
minutes. It validated the entire R1 approach against our own build and settled the patching
question. Re-run it after every ArenaNet update — if the signature stops matching, no published
patching tool can be trusted until it is re-derived, and that is a real finding rather than a tool
failure:

```bash
python toolkit/clientscan/dump_dh_params.py
```

**Probes 1 and 2 — the auth handshake.** ✅ **Done. Both a GO.** Full result and byte-level
decode: [studies/handshake/PLAN.md](studies/handshake/PLAN.md) §0.

The portal is **plaintext HTTP on 6601**, exactly as predicted — the client sends
`GET /Spawned/WebGate/session/create.xml HTTP/1.1` with `Authorization: Arena 0`, no TLS anywhere.
That single request is the specification for our webgate. AuthSrv on 6112 speaks the documented
Diffie-Hellman opening: a hello carrying the build number, then header `0x4200` followed by 64
bytes of `A = g^a mod p`, with the generator `4` matching the value read out of `.rdata`. The
client speaks first on both sockets, and `Code=058` after a successful connection is the *correct*
outcome of a listener that never replies.

Two things fell out that were not being looked for. The build number rides in the clear on every
session (`User-Agent: Gw/38797.0 (Win32)`), which answers HANDOFF §9's unaddressed question of how
to stamp a build id into capture manifests. And the client hit **6112 before 6601**, so the three
stages are not a strict sequential chain — do not assume the portal must complete before the auth
socket opens.

**Probe 3 — does the WASM client boot and survive instrumentation?** *(days, agent-farmable)*
Fetch the four artifacts, run `wasmscan.py` and `gensyms.py` from the mirrored `gw_in_browser`,
open the result in Chrome DevTools. **Success looks like** recognisable C++ symbols attributed to
source paths. This single probe decides whether the harness is C++ or Python/JS, which is the
largest remaining architectural fork.

**Probe 4 — does OpenTyria build and accept a client?** *(days)*
Build it, seed the SQLite database, generate DH params, patch a *copy* of the client, run
`webgate.py`, connect. **Success is a character standing in a map on your own server** — HANDOFF's
R2, in week one instead of year one. Even total failure is cheap and teaches you the stack.

**Probe 5 — is `-mock` anything?** *(hours)*
The last unexplained flag with real upside. A developer offline mode would be worth a lot.

---

## 3. The revised ladder

| Rung | Deliverable | Acceptance criterion | Cheapest falsifying probe |
|---|---|---|---|
| **R0a** | Vault + provenance gate + prior-art mirrors | A capture replays byte-identically from disk | ✅ **done this session** — gate proven both directions, client pinned and hash-verified, prior art mirrored |
| **R0b** | Proxy capture via the WebSocket bridge | Both directions of a real session tee'd to disk | Probe 3 |
| **R1** | Handshake against a local server | Client reaches character select | ✅ **DONE 2026-08-04.** Build 38797 rendered "Test Warrior" at character select against our portal, our DH parameters, our ARC4 channel and our five-message login burst. |
| **R2** | Presence | Your own body standing in a real map | Probe 4 — OpenTyria may deliver this directly |
| **R1.5** | **Tape player** *(new rung)* | A recorded StoC stream replayed at recorded timing walks a real client through Ascalon | Requires R0b only |
| **R3** | Movement on real geometry | You walk to a wall and are stopped | `GmPaths.c` + `PathingMap` exist; this is a quarter, not a week |
| **R4a/b/c** | Agent model, skill substrate, AI and spawns | As HANDOFF.md | — |
| **R5** | Declarative authoring toolkit | A new zone in TOML, hot-reloaded, walked | — |

Two structural changes, both argued below in §4.

**R0b replaces R0's C++ harness.** The capture harness stops being an in-process DLL and becomes a
proxy. Same deliverable, a fraction of the friction, and it cannot be broken by a client patch
moving an address.

**R1.5, the tape player, is new and it is the best idea to come out of this exercise.** Before
writing any simulating server, write a server that replays a recorded StoC stream at recorded
timing, fixing up only session-specific fields. It simulates nothing. It proves your framing, your
crypto, your opcode table and your session setup — the entire transport stack — against a real
client, with zero game logic written, and it produces a walkable-looking Ascalon months before
R4a. HANDOFF's R1→R2→R3 each require newly invented logic; the tape player collapses all three
into a replay problem you already have the data for.

---

## 4. Angles of attack, ranked

**A1 — Capture first, and do not write the harness from scratch.** *(days · mixed)*
The single largest schedule saving available. Two instruments already exist and they are
complementary rather than competing.

*A headless-client recorder*, following Headquarter's approach (MIT, C, tracking live builds to
38688). It needs no injection, no patched client and no GWToolbox, it runs unattended, and it can
be scripted to sweep maps — which turns the capture campaign from months of manual play into a
batch job. Headquarter is a complete from-scratch GW1 client that logs into live servers and is
already used in production by `gwdevhub/GuildWarsPartySearch` and `kamadanv2`. Adding framed,
timestamped raw-packet writing is roughly one function.

*An in-client sniffer*, for fidelity. `gw-preservation/network-logger` is a drop-in DLL that logs
100% of game-server↔client traffic to disk **[measured — mirrored]**, and `Fournux/Tyria-Extractor`
(MIT) ships an injected sniffer alongside its `Gw.dat` extractor.

Layer the shadow-server idea on top once capture works: feed your server the real CtoS stream and
diff its would-be output against the real server's while still forwarding the real answer. That is
HANDOFF §7's replay oracle at R0 instead of R2, open-loop, self-updating as you play. Then stop
forwarding message types that diff clean and answer them yourself, so the system stays playable
throughout and the project becomes incremental replacement rather than a cold start.
*Wasted if:* nothing obvious — this is required under every strategic option, it does not depend on
the language decision, and building it is how you find out how good the rest of the prior art
really is. **Build it first regardless of every other choice in this document.**
*Note:* the browser/WebSocket proxy route is attractive on paper but `gw_in_browser` cannot log in
(its auth paths are stubs), so it is a static-analysis asset, not a capture one. See §1.3.

**A2 — Stand up OpenTyria and see your character.** *(days · human)*
Public domain, ~25k lines, with agent, chat, inventory, item, map, pathfinding, party and title
modules plus SQLite persistence. Even if Rurik never ships a line of its code, building and
running it converts a pile of protocol theory into a working reference you can step through in a
debugger. *Wasted if:* it does not build against the 2026-04-30 client — in which case *why* is
itself the most valuable R1 finding available. *First step:* Probe 4.

**A3 — Reconcile the five existing opcode corpora into one build-stamped schema.** *(days · agent-farmable)*
Five independent catalogs now exist: OpenTyria's `msgdefs.c` + `opcodes.h` (public domain),
Headquarter's `opcodes.h` (MIT, declaring 60/40/194/487), `Py4GW_Reforged_Native`'s
`include/GW/common/opcodes.h`, the GWCA lineage, and GWLP-R-Utils' `PacketTemplates.xml` — **177 KB,
769 packets, 907 named entries** across all four directions **[sourced]**. They agree on values
where they overlap (`INSTANCE_LOAD_SPAWN_POINT = 0x0195` in three of them independently), which is
strong evidence they are all describing the same real protocol.

**Every schema revision must carry a client build id.** `MOVE_TO_COORD` drifted `0x003C` → `0x003E`
between builds, so an unstamped catalog is not merely stale, it is actively dangerous. The client's
own `template_size` (§1.2) is the arbiter, and disagreement with it is mechanically detectable —
which is exactly what makes this whole job safely delegable to agents.
*Wasted if:* nothing — this work is required under every option and gets cheaper as captures grow.

**A4 — Instrument the WASM client and take decoded ground truth, not bytes.** *(weeks · mixed)*
HANDOFF's model is record bytes → decode later → hope the decoder is right. Inverted: hook the
client's own per-opcode decode handlers and log *their outputs* — the client's own interpretation,
in its own structs, with `gensyms.py` naming the originating `.cpp`. Labelled ground truth on day
one instead of an undecoded pile. The same trick against static tables dumps all ~1,300 skill rows
with their rank scaling, moving R4b's numeric bootstrap from year two to week two without the
capture vault existing at all. *Wasted if:* Probe 3 fails. *First step:* Probe 3.

**A5 — Headless differential testing.** *(weeks · agent-farmable)*
The WASM client runs in a browser, and browsers are drivable by Playwright. That gives N scriptable
Guild Wars clients you can point at either the real service or your server, using the client's own
reactions as the correctness signal — diffing two clients' internal state rather than diffing
packets. This is the answer to "can the client be an oracle," and the harness is a browser
automation script rather than a bespoke engine.

**A6 — Agent-scale data entry with the client as referee.** *(months · agent-farmable)*
Seed from `build-wars/gw-skilldata` (MIT, pushed today). Cross-check every numeric field against
the client-extracted `GW::Skill` table — any disagreement is a hard conflict, not a judgement call.
For behaviour rather than numbers, drive a headless client to cast the skill on the live service
and diff against your engine's prediction. A row counts as verified only when the numbers agree and
the behaviour diffs clean. **No human reviews 1,300 rows**, and the pipeline cannot quietly fill
the database with plausible garbage, because every step has a mechanical referee.

**A7 — Author content into your own running client, with no server at all.** *(days · human, secondary account)*
GWCA exposes `EmulatePacket(Packet::StoC::PacketBase*)` **[sourced]**, and Py4GW independently
proved inbound packets can be rewritten in flight before the client materializes them. So you can
synthesize agents, dialogue and markers into your own client on real Ascalon geometry *before any
server exists*. This inverts the ladder's assumed dependency — R4-level semantic understanding
accumulates during R1–R3 instead of waiting behind them — and it directly attacks the handoff's own
admission that "you will not be able to use most of what you capture for two years."

It also turns §8's strongest law from a docstring into a call-site rule. "Before writing a
mechanism, ask whether the client even reads it" is currently enforced nowhere, which §8 itself says
makes it a wish. Enforce it: **for every packet you intend to emit, first prove via `EmulatePacket`
that the client changes observable behaviour when it receives one.**
*Caveat, stated plainly:* this is the highest ToS-exposure item here — in-process modification of a
live client on the real service. Secondary account, instanced content, supervised, never near
anything competitive. That is why it is A7 and not A1.
*First step:* re-emit a captured chat message and see it appear.

**A8 — Reframe the deliverable as the instrumentation toolchain.** *(continuous)*
The primary artifact becomes a documented, reproducible pipeline that turns the official WASM
client into a symbolized, hookable research target: fetch → verify → patch → detour → symbolize →
drive. It redistributes zero ArenaNet bytes, it is useful on day 30 rather than day 900, it is
what the GW1 RE scene currently lacks in one place, and the emulator becomes its flagship consumer
rather than its only justification. This directly addresses the plan's real failure mode — a
multi-year binary outcome with no interim value.

**Killed by scrutiny, recorded so nobody re-proposes them:** substituting a login DLL via
`-portaldll` (dead code); building on GWCA as a runtime dependency (closed-source and archived);
and hooking GWCA's typed StoC callbacks for raw capture (they fire on deserialized structs, so
unmapped opcodes are invisible rather than merely unparsed — the wrong layer for "record raw,
parse later").

---

## 5. Workstreams and the first 90 days

The human is the bottleneck for exactly three things: anything that launches the game, anything
that judges whether the game *feels* right, and the account risk decisions. Everything else is
agent-farmable.

**Human-only:** Probes 1, 2, 4. Playtesting. Deciding whether to use a secondary account.
**Agent-farmable:** the schema translation (A3), WASM tooling and symbolization (A4), the browser
harness (A5), the skill data pipeline (A6), Pre-Searing scope enumeration, and reading the mirrored
prior art.

- **Days 1–14** — Probes 1 and 2. Build and run OpenTyria (A2). In parallel, agents translate
  `msgdefs.c` into the schema and stand up codegen (A3). *Target: a character standing in a map.*
- **Days 15–45** — Probe 3. If it passes, the proxy becomes the capture harness (A1) and runs on
  every session from then on, including sessions played for fun. Begin the WASM symbolization
  pipeline (A4, A7).
- **Days 46–90** — Tape player (R1.5). Skill-table extraction and the referee'd data pipeline (A6).
  First shadow-server diffs on real traffic.

Capture still starts immediately and never stops — the wasting-asset argument is right. What
changes is that capture is now cheap enough to leave running rather than a project in itself.

---

## 6. Risks and hedges

| Risk | Hedge | Cost |
|---|---|---|
| A prior-art repo disappears | **Already happening** — `gwdevhub/gw_in_browser` 404s today while `gwnative` still names it upstream **[measured]**. `toolkit/mirror_priorart.py` clones the field into `vault/mirrors/` with a manifest recording each HEAD; run it monthly. | done |
| Service closes or changes | Leave the proxy on for every session; zero marginal cost once built | hours |
| **Client auto-patches over ground truth, and the DH keys rotate with it** | **This happened during the session that wrote this document.** The updater replaced `Gw.exe` (10,404,032 → 10,483,904 bytes) and `Gw.dat`, moved the DH struct from RVA `0x6843e8` to `0x6910d8`, and **changed both the prime and the server's public key**. ArenaNet rotates the Diffie-Hellman parameters per build — which is why Headquarter stores 107 server keys rather than one constant. Consequences: the client patch is a permanent recurring step, not a one-time one; every capture and schema revision must carry a build id (free, per §2); and re-snapshot *before* accepting an update prompt, never after. Both builds are now vaulted. | ongoing |
| **The client phones home when it crashes** | `Gw.exe` embeds Sentry: `SENTRY_DSN`, `sentry.native`, `getsentry`, `x-sentry-rate-limits` are all present **[measured]**. The working method here is inject, patch, malform, crash — so the client's own outbound reporting channel is a posture problem HANDOFF §9 never considered, since §9 reasons only about server-side visibility. Neutralise it before the first malformed packet: block the endpoint at the firewall or null the DSN in the patched copy. Minutes, and it belongs on the R0 checklist next to the vault snapshot. | minutes |
| Account loss | Never automate on the primary account. The proxy posture — watching your own traffic — is milder than injecting a DLL, which is what the original plan required | one account |
| A client update invalidates months of offset work | Choose WASM: the module bytes are the code and offsets come from the module | free, if you switch |
| Two years with nothing playable | A2 and R1.5 both target a visible result inside 90 days | — |

---

## 7. Open questions for the owner

**Q1. Build on the existing servers, or learn from them and stay independent?**
*Recommendation: independent codebase, treating OpenTyria and gw-preservation as published answer
keys for R1–R3 and Headquarter as the capture instrument. Vendor nothing except possibly
OpenTyria's public-domain schema.* The reasons to refuse adoption are concrete: OpenTyria implements
only about 8–9% of the opcode space, has 2 unit tests, 6 hardcoded maps, **zero content tables** in
its schema, an empty "Known issues" section and a HEAD that has not moved since February while its
author commits weekly elsewhere; and `gw-preservation` carries no license at all, pins a
pre-Reforged client version, and coordinates entirely off GitHub. Neither is a platform. Both are
one person's exploration.

*The counterargument is genuinely strong and should be recorded honestly.* You want R4c and R5.
Everything below that is plumbing you did not ask for. OpenTyria suggests a competent person needs
something like eighteen months to reach R3 — and Rurik would redo it in another language without
that person's accumulated protocol knowledge, so plausibly slower. That is a large slice of a
multi-year solo budget spent re-deriving something already public domain, before writing a line of
the thing you actually want.

*The recommendation is therefore contingent, not principled.* It rests on one testable assumption:
that a working reference implementation plus a solved crypto scheme plus five agreeing opcode
catalogs turns R1–R3 from research into transcription. If that assumption fails, adoption was right
and independence costs a year.

**The hedge costs nothing: build the capture harness (A1) first, before committing either way.** It
is required under every option, it is the wasting asset, it does not depend on the language
decision, and building it is precisely how you find out how good the prior art really is. Defer
this decision until it has recorded its first sessions.

**Q2. Is the WASM client the primary target?** *Recommendation: yes if Probe 3 passes.* It is
better instrumented, better symbolized, patch-resilient, and drivable by browser automation. Keep
the x86 client as the playtest client.

**Q3. Does the provenance gate survive contact?** §9 says "zero ArenaNet bytes in the repo, ever,"
but R0 vaults `Gw.exe` and `Gw.dat` and every schema derives from them. *Recommendation:* restate
the gate as a **derivation graph with a gitignored `build/`** — every derived artifact regenerates
from a documented fetch of a freely downloadable client. That is a stronger and more honest
formulation than a prohibition needing constant qualification, and it matches the owner's own point
that the client is available to anyone.

**Q4. A secondary account for automation?** *Recommendation: yes, before any scripted driving.*

**Q5. Does Pre-Searing remain the finish line?** *Recommendation: yes, unchanged.*

---

## 8. Immediate next actions

0. **Neutralise the crash-telemetry channel** before any patching or malformed traffic — see §6.
   Minutes, and everything else in this list is the kind of work that crashes clients.
1. **Drive the real client against our two servers** —
   [studies/handshake/PLAN.md](studies/handshake/PLAN.md) §5b has the three-terminal runbook.
   Everything up to and including the encrypted channel is implemented and self-tested; this is
   the first run against the actual game.
2. **Answer what it asks next.** The post-handshake messages now arrive *in plaintext* in
   `vault/captures/authsrv/`. Decode them, reply, and R1's acceptance criterion — a character
   select screen — falls out. This is transcription against a working reference, not research.
3. **Build the capture harness (A1).** Still the hedge that lets Q1 stay open, and still required
   under every strategic option. Start from Headquarter's headless-client approach; read
   `gw-preservation/network-logger` for the in-client route.
4. **Dump the client's packet-template table** (§1.2), then reconcile it against the five existing
   opcode corpora (A3). Build-stamp the result. Any disagreement with the client's own
   `template_size` is a mechanically detectable defect, which is what makes this agent work.
5. **Build OpenTyria** (`vault/mirrors/ldufr__OpenTyria`) and connect a *patched copy* of the
   client. Never patch `C:\gw`. Fastest route to understanding the whole stack end to end.
6. **Read `gw-preservation/server`'s pathing and instance definitions** — 397 maps and a real
   `Gw.dat` navmesh. Read only: no license means all rights reserved.
7. **Extract the skill table.** `Fournux/Tyria-Extractor` (MIT) already does `Gw.dat` →
   skills/items/quests/NPCs; cross-check against `build-wars/gw-skilldata`. This is R4b's numeric
   bootstrap and it needs no capture vault to exist. Agent work.
8. **Run Probe 3** (`vault/mirrors/shiburito__gw_in_browser`) for offline WASM analysis only —
   not for live capture, per §1.3.
9. **Install a .NET SDK** if the C# server core survives Q1/Q2 — only the 6.0 runtime is present
   and the plan calls for 8+. Defer until the language decision is settled.
10. **Re-run `toolkit/mirror_priorart.py`** monthly. Repos in this ecosystem vanish; one already has.
