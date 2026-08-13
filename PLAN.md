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

### 1.8 There *was* a server binary, and the client is one half of its source tree

HANDOFF.md §1 opens *"There is no server binary. There never was one to have."* The first sentence
is true of what we can hold. The second is false, and correcting it changes the shape of the work.

`Gw.exe` carries **937 distinct `P:\Code\…` source paths** — ArenaNet's own build-machine paths,
left in the image by `assert()` and a few other macros **[measured, on both vaulted builds]**. Every
gameplay subsystem in them sits under a client marker: `Gw\Char\Cli\ChCliApi.cpp`,
`Gw\Item\Cli\ItCliApi.cpp`, `Gw\Party\Cli\PyCliParty.cpp`, `Gw\Main\MainCli.cpp`. **Twelve
subsystems ship a `Cli` half and nothing else**, and **no path in either image lies under a `Srv\`
directory** — six spellings checked, zero hits, on two builds four months apart. The linker's own
PDB path agrees from the other side: `P:\Code\.build\target\Gw\vs2022\builder_x32\bin\Gw.pdb`, one
`.build` with a directory per target.

So the client and the server were **two build targets over one source tree**, and the shipped client
is the `Cli` half. That is a materially better position than inventing from nothing, because it says
exactly which of ArenaNet's code we can read: `Base\`, `Engine\`, `Net\` and `Gw\Const\` carry no
Cli/Srv split at all, so both targets compiled them. `Net\Msg\` is the transport both ends spoke —
which is why §1.2's message-table dump worked. `Engine\Agent\` is the agent *model* (the client's
own `Gw\AgentView\` is only its rendering), and `Engine\Map\Path\` is R3's authority.

**Consequence:** "reconstruct the server binary" is the wrong target and always was. The right one
is the `Srv` half of `P:\Code`, which decomposes into transport (recovered), constants (readable),
agent model and pathing (readable, shared engine), and twelve subsystem halves — narrowed further by
§1.7's four genuinely server-only behaviours. Full census, method and limits:
[studies/srvtree/FINDINGS.md](studies/srvtree/FINDINGS.md), checked by
`toolkit/clientscan/test_srctree.py`.

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

**Probe 5 — is `-mock` anything?** ❌ **Answered NO, statically, no launch needed.** It selects a
mock *graphics device*. Exactly three strings in the image contain "mock" — `mockDevice` (ASCII),
the flag `mock`, and `MockDevice` sitting in a run of window names (`BtnExit`, `BtnRestore`,
`BtnMin`, `Game`, `UiRoot`) — and the single assert site naming it is `MainCli:176 mockDevice`,
inside `Gw\Main\MainCli.cpp`'s argument handling **[measured]**. There is no offline mode and no
mock server. Salvage: a null render device belongs on the capture-arc list next to `-noui`,
`-nosound` and the mutex NOP, for running many clients at once.
[studies/srvtree/FINDINGS.md](studies/srvtree/FINDINGS.md) §7.

---

## 3. The revised ladder

**This table is the project's single status authority.** `CLAUDE.md` and `RUNBOOK.md`
point here and do not restate it. That rule exists because on 2026-08-06 the three
documents asserted three different current positions, the newest of them 40 hours stale,
and a cold agent session reads whichever it opens first. If you land a rung, date it and
stamp it with a commit hash **in the same commit**; if you cannot, the rung is not landed.

| Rung | Deliverable | Acceptance criterion | Status |
|---|---|---|---|
| **R0a** | Vault + provenance gate + prior-art mirrors | A capture replays byte-identically from disk | ✅ **2026-08-04**, criterion met **2026-08-07** (`toolkit/authsrv/replay.py`). Gate proven both directions, client pinned and hash-verified, prior art mirrored — and the `.raw` now decrypts back to the logged plaintext, 329 real captures reproduced exactly, all-or-nothing across 375. The stated criterion finally rests on the stated fact. See §3.1. |
| **R1** | Handshake against a local server | Client reaches character select | ✅ **2026-08-04 22:58**, `e34c417`. Build 38797 rendered "Test Warrior" against our portal, our DH parameters, our ARC4 channel and our login burst. |
| **R2** | Presence | Your own body standing in a real map | ✅ **2026-08-05 11:15**, `aedc214`. |
| **R3** | Movement on real geometry | You walk to a wall and are stopped | ✅ **2026-08-05 17:40**, `a97c7c4` — the server reads the game's own navmesh. Movement itself landed at `885d05d` (11:46). Estimated here as "a quarter, not a week"; it took six hours. |
| **R4a** | Agent model + combat core | An ettin swings at you and you die | 🔶 **half.** A hostile Hatcher stands in the map, and a click orders an attack the server drives to a kill and a revive (`f8320ff`, `37cb856`, 2026-08-06). ~~Nothing swings back and the player cannot die~~ — **BOTH MET 2026-08-11**, which is the half the criterion actually names. A Hatcher swings at the player, the player's health falls 10 a swing, and at zero the player drops face-down with both orbs at 0 and stands back up ten seconds later. Three full death/revive cycles in one 65 s run, on the wire and on film (`vault/captures/gamesrv/authsrv-20260811T160502-c1.jsonl`, `frames-20260811T160449`). `studies/enemy/PLAN.md` §11. What is still missing is a real agent model — no AI, no pathing (the Hatcher stands where it spawned and swings when you are inside 1200 units), no resurrection shrine (the revive is a timer), and energy is not restored on revive. No agent table either — `studies/enemy/PLAN.md` §7.2. **2026-08-11: one click now drives a whole fight** — `0x0026` ATTACK_AGENT arrives (four of them at our Hatcher, zero `0x0033`, ending a year in which the client had never once sent it), the server dispatches it, seven swings at 1.77 s kill the agent, and it revives; the client drops the dead target and re-acquires the revived one unprompted (§10.9). **The first revive crashed the client** — `CharPool.cpp:84`, `fraction <= 1.0f` — because we sent `max_health` where a fraction belonged, on the one side of a `<=` bound that no damage test could ever reach. Fixed and re-verified. **2026-08-11 (earlier): the click arrives as `0x0026` ATTACK_AGENT** — four of them at our Hatcher, zero `0x0033`, ending a year in which the client had never once sent it (§10.7). The server now dispatches both arms. |
| **R4b** | The skill substrate | See §3.2 — rewritten as a count | 🔶 **started.** Eight real skills on the bar with correct tooltips (`70c3926`), the cast lifecycle read out of the client's own asserts, `USE_SKILL` answered. **No skill resolves an effect.** |
| **R4c** | AI + spawns + quests | See §3.2 — rewritten as a count | ⬜ not started, **and 2026-08-11 established what "started" would even mean** ([studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md), `9eb09a8`+). Monster AI *as a mechanism* is **not recoverable** — not from the client (0 of 937 embedded source paths under any `\Srv\` tree, from a detector proven to catch 6 of 6 planted ones; 33 AI-adjacent searches over two independent routes, all zero), not from the wire, and not by any capture campaign, because it is never shipped and never transmitted. What **is** recoverable is the observable envelope, and the study designs the labelled behaviour campaign that would recover it (§7) plus four desk follow-ups needing no capture at all (§7.9) — **the first of which ran the same day and made the binary negative total**: `CHAR_AI_MODES`, the one lead the study declined to call refuted, is 3 and its modes are Fight/Guard/Avoid Combat, i.e. the player's own hero-and-pet stance widget. It also found the AI-adjacent numbers already in `authsrv.py` are mostly the **wrong shape** rather than merely unmeasured: reach is per-creature-model (~65 / ~599 / ~706 units observed against our one global 150), a leash is *uncomputable* from the state `spawn_enemy` keeps, and 4 of 5 fights in the corpus are started by the **player**, refuting our proximity-initiation model for 4 of 5. |
| **R5** | Declarative authoring toolkit | A new zone in TOML, hot-reloaded, walked | ⬜ not started — but its substrate exists as of `501698b`: `content/*.toml` and `toolkit/content.py`, with the server holding zero content literals. **Its other half now exists too**: R5m authors the zone's *geometry*, which TOML was never going to describe. |
| **R5m** | **Custom map geometry, end to end** | A map we authored loads in the retail client, and geometry we chose constrains the character | ✅ **2026-08-11**, arc landed `0be1555`, criterion completed the same day. **The client walks on our terrain and stops at our walls.** `mapbuild.build_flat` assembles a whole map from typed parameters — 7,841 B, 9 chunks, **97.04% generated**, the rest being FINDINGS 14's 232 bytes of ArenaNet constants read from an archive at run time — and the retail client loads it, places a character in it and writes nothing back (FINDINGS §22, four discriminators). Then **E1 proved the geometry is ours and not a coincidence**: two maps differing in **33 of 7,841 bytes**, all inside the pathing chunk, both 7,841 B, with the mesh rect at 0..3072 against 1024..2048, confined the character to reported bounding boxes of **3072.0 × 3072.0** and **1024.0 × 1024.5** — the ratio of the two rectangles, measured from the client's own position reports while our server broadcast no position at all (FINDINGS §23). The read direction is byte-exact across the corpus: terrain 349/349, pathing 349/349, whole map file 349/349 Bloated **and** Stripped — and since 2026-08-12 the STRIPPED terrain chunk too (`strippedterrain.py`, FINDINGS §37), whose real claim is not the round trip but that its **60,468,224 height samples equal the Bloated chunk's on 349 of 349 maps**, pulled out of a Huffman bit stream by a module that never reads that chunk. A retail map also stands up in Blender (`tools/blender/import_gwmap.py`, 213,921 verts, orientation checked against a chunk the exporter never reads) and **since 2026-08-12 comes back out of it**: `export_gwmap.py` round-trips Pre-Searing's 212,992 heights, tiles and shade bytes byte-identically through a `.blend` read by a separate Blender process, and a mesh authored in Blender from nothing reaches a map file passing all 17 open-time gates (FINDINGS §32). That byte-identity is the weak half by measurement — a memcpy sabotage keeps all six of those checks green and is caught only by a sculpt control. **And since 2026-08-12 the OTHER delivery route is open: the client's own map compiler builds from a Stripped stream we supply** — §35 it compiles at all and reproduces ArenaNet's bytes, §36 it compiles the stream WE write rather than anything cached, and **§38 it floods terrain we AUTHORED**: the rebuilt navmesh stops at world x = 1152.0, the cell boundary we chose, with walkable area in the steep strip falling from a measured 37.3% to 0. **What is NOT done**: authored art (textures are borrowed retail file ids), portals, multiple planes and elevation; only the terrain of §38's map is ours (props, zones and collision are ArenaNet's); and the delivery path is still `datwrite` into a copied archive — which now bounds authoring to maps that SHRINK, since it writes uncompressed and will not relocate (§8.10 e9). |
| **R0b** | **Instrumented-client capture** of a real session | A live session recorded from inside a client we control, both directions, stamped `origin: live` and byte-replayable from disk | ✅ **2026-08-07**, `vault/captures/live/20260807T143055`. Six connections to ArenaNet (one auth, five game, all on **port 80**), both directions, zero TCP gaps, stamped `origin: live`, and **byte-replayable in the strong sense**: `livesession.py --assemble` regenerates all six decrypted files **sha256-identical** from `wire.jsonl` + `keyring.jsonl` alone, with no client and no network. 200,153 bytes of ArenaNet plaintext, 11,700 messages. **The independent check is the framing**: every one of the 12 streams decodes 100% clean to its final byte against `schema/messages.json`, which was built from the *client's* format tables and never from these bytes. Adversarially attacked from four angles (§3.3); three failed to refute, and the fourth's safety finding is fixed. See §3.3 for what the number does *not* mean. The pipeline is complete — key-tap cave (`keytap_patch.py`, `--key-tap`), off-wire WinDivert capture (`wirecapture.py`), memory reader (`keytap.py`), driver (`livesession.py`, wired to launch at `9cd7bca`, 2026-08-07), decrypt (`replay.py`) — and `dryrun_keycapture.py` ran it end to end against our own server, elevated, GREEN (`32c7fe1`, 2026-08-07): the off-wire ciphertext matched the server's own `.raw` byte for byte, and the tapped key decrypted it to the server's logged plaintext. The live build is staged, stock-DH and key-tapped (2026-08-07). **What is left is the live run itself, and it is human-driven by design** (§6.2, and `livesession.run`'s docstring: no scripted input, the operator plays). **Re-specified 2026-08-06 — it used to read "proxy capture", which cannot work: the channel is DH-keyed end to end and a proxy holds neither private exponent. That is the same fact that forces us to patch the client for our own server.** |
| **R1.5** | **Tape player** | A recorded StoC stream replayed at recorded timing walks a real client through Ascalon | ✅ **2026-08-10, and it walked through Ascalon City itself.** The full 48.6 s tape of connection `:60935` played **1,209 of 1,209 events, 74,319 B, with ZERO messages of our own on the channel** (measured, not assumed — the previous run's assert turned out to be our own world tick talking over the recording). The client skipped the cutscene, walked to each quest giver in order, spoke to them, accepted quests, and walked to the zone exit; chat arrived. **We still cannot name half the opcodes involved** — a tape needs no semantics, which is the whole point. It ended where a one-connection tape must: at the map transition, the client dialled `54.198.7.73:6112` from the recorded `GAME_SERVER_INFO` and the cage refused it (`Code=005`). See §3.4. **A second run the same day played Lakeside County (`:64103`, 1,074/1,074, 0 non-tape sends) and rendered COMBAT** — plus a labelled c2s corpus, and independent corroboration of D1's agent-id reuse from ArenaNet's own traffic. See §3.5 and [studies/tape/FINDINGS.md](studies/tape/FINDINGS.md). |

Two structural changes, both argued below in §4.

### 3.1 What "done" is doing in the table above

R0a was the honest wart. Its criterion is *a capture replays byte-identically from disk*,
and for three days nothing in `toolkit/` had ever read a `.raw` file back — the row stood
on the gate, the pinned client and the mirrors, none of which is that criterion.
**Closed 2026-08-07.** `toolkit/authsrv/replay.py` reads the `.raw` ciphertext back,
derives the session key from the capture's own handshake records plus our stored exponent,
and decrypts it to exactly the plaintext the server logged — `test_replay.py` confirms
329 of the vault's real captures reproduce their plaintext byte-for-byte, and that the
375 keyable captures are all-or-nothing, never partial. The remaining 46 correctly do not
decrypt: the 2026-08-04 bring-up sessions logged a synthetic `RURIK-HANDSHAKE` marker
rather than real traffic, and some predate the 07-29 build whose exponent we hold. What
this does *not* yet prove is that ArenaNet's server_seed matches ours bit-for-bit; only a
live capture settles that, which is R0b.

The lesson generalises, and it is why the status column now carries hashes: **R2 and R3
were both landed and neither was recorded here for 40 hours**, while R3's own estimate
in this table ("a quarter, not a week") stayed in print through the six hours it actually
took. A ladder nobody updates stops being a control instrument in both directions at
once — it under-reports what is done and keeps mis-estimating what is next.

### 3.3 What R0b's green does and does not mean

The rung was marked only after four agents were told to **refute** it. Three could not; the
fourth did, on grounds now fixed. Recording both halves, because a milestone is exactly
where a status table stops being read critically.

**What survived attack.** The framing evidence is stronger than it looked. Against
uniform-random bytes the codec frames 0 of 2000 trials (deepest 22 B); against real
ciphertext under 20,000 wrong ARC4 keys, 0 clean, deepest 51 B — while the right key frames
74,319 of 74,319 B. Byte-shuffled real plaintext (identical byte histogram) frames 0 of 12.
91.8% of the 11,700 messages advance by a length the *schema* fixes, not one the data
supplies. And a semantic confirmation nobody planned: `AUTH_CMSG_SEND_COMPUTER_INFO`
decodes to the operator's own Windows username and machine name, which no wrong key
produces. The schema files predate the capture by two days and are unmodified.

**What the number does not mean.** "6 of 6" is *six of six connections that already parsed
as GW* — `prune_wire` drops non-handshake connections before assembly, so a genuine channel
with an unrecognised VERSION header would leave both numerator and denominator silently.
Two endpoints the client's own TCP table recorded (`54.86.64.251:80`, `3.92.123.50:443`)
are absent from the artifact by design. Do not quote it as coverage. Relatedly: "both
directions" is true but lopsided — the client half is 4.2% of the bytes, and half of *that*
is one movement opcode. And "ArenaNet addresses" is a protocol inference (GW VERSION,
build 38797, `webgate.ncplatform.net` in `Gw.log`), not a WHOIS fact.

**Four defects it found, all fixed.** The `refusing to choose` guard deduped on the key's
*label* rather than its bytes, so two different keys sharing a rounded timestamp collapsed
into one and the refusal quietly became "take the first". `assemble_live` never cleared
stale channel files, so a partial re-assemble left a directory that looked like a full one
— R0a's failure shape exactly; it now clears them when it produces output and *keeps and
flags* them when it produces none, so a failed check cannot destroy a good decryption. The
manifest carried no hash binding the artifact to the wire, so deleting a wire record still
reported 6/6; it now records `wire_sha256`, `keyring_sha256` and the pruned count. And
`wirecapture` hardcoded `origin: live`, which is why three **loopback** dry-run files on
disk claim to be live traffic — the stamp is now derived from the endpoint, and a sniff
pinned to 127.0.0.1 says `ours`.

**The one that mattered outside this repo.** `vault/captures-scrubbed/`'s root
`SCRUB-MANIFEST.json` was written 2026-08-06, before any live capture existed — no
`WARNING`, no opaque-payload list, `files: 421` — while the tree had since gained three
live sessions, one of which demonstrably carries the account name as UTF-16 inside a
`plain` blob. RUNBOOK names that tree as the copy which may leave the machine, so the
top-level report was giving an all-clear on a credential. `scrub_captures.mark_tree_unsafe`
now writes a `DO-NOT-SHARE.txt` at the root and stamps the root manifest, and the existing
tree has been marked. A stale all-clear is worse than no report.

**And the stamp is no longer a self-declaration** (fixed 2026-08-07, its own commit).
`origin_of` used to return the stated value and stop reading. It now reads on and **refuses
a `live` stamp on a file whose every recorded address is loopback** — a capture of ArenaNet
cannot look like that. `PEER_FIELDS` gained the fields producers actually write (`src`,
`dst`, `connection`), so the corroboration that was sitting unread in every live capture is
now used; and placeholders like `"client": "unknown"` are excluded by `is_address`, because
a non-address reads as "not loopback" and silently defeated the check on its first real
test. Producers derive their stamp from the endpoint instead of asserting it. MEASURED over
1,076 vault files, exactly **one** verdict moved: `vault/dryrun/dryrun_wire.jsonl`,
`live → unknown (CONTRADICTED)` — the loopback file that had been mislabelled all along.
754 `ours` and the 33 genuine live files are unmoved. The reverse direction is deliberately
not symmetric: an `ours` stamp on a file with public addresses is reported as
uncorroborated, never overridden, because our own tooling legitimately records ArenaNet
endpoint metadata.

### 3.4 What the tape run settled, and what it did not

**The client does not validate identity.** This was R1.5's one unknown — §4.2 item 2 called
it "the unknown that decides feasibility" — and the answer is no. The tape names the
*recorded* character: an 11-character name in `0x017D`, player number 26, agent 725, plus
40 other players in the outpost. The client had logged in as ours. It accepted all of it,
rendered the world, and drove a full session without a murmur. The predicted informative
failure — an assert naming a player-identity field — never fired. (OBSERVED.)

**A tape needs no semantics, demonstrated rather than argued.** 105 opcodes in that stream
are ones our server has never sent and several have no name anywhere in this repo,
`0x015E` among them. It did not matter. We re-emitted bytes.

**The previous run's assert was our own contamination.** `AgAgent.cpp(978)`,
`!m_timeStopMovement || ((int)(m_timeStopMovement - time) >= 0)`, looked like a stale-clock
finding and was not: our server had sent 378 messages of its own alongside the tape — a
five-message load preamble and 373 `WORLD_SIMULATION_TICK`s — so two independent tick
streams were reaching one client. With the channel clean it did not recur. **§4.2 item 5,
session-embedded absolute time, is therefore still UNVERIFIED** — it was never actually
tested, and the run that appeared to test it was measuring our own bug.

**Where it ended is the tape's boundary, not a fault.** At the zone exit the client dialled
`54.198.7.73:6112` — ArenaNet's real game server, from the recorded `GAME_SERVER_INFO` —
and the cage refused it (`Code=005`). One connection is one instance; a tape cannot cross a
map transition, because the next map lives on a different recorded connection with its own
handshake and its own key.

**Still out of scope, by construction:** control. The avatar walked the *recorded*
operator's path — to the quest givers, through the dialogues, to the exit — regardless of
what the new operator did. `Client pathing data out of sync with server` is that, and it is
expected. A tape shows a load and a populated, animated world. It cannot show a world that
responds.

**What this is now useful for:** a regression instrument. Any future change to our server
can be run against a real recorded stream and compared, which is the first time this
project has had an oracle it did not write itself.

### 3.5 The second tape run: combat, and a labelled c2s corpus

Run 2 the same day played `:64103` — Lakeside County, map 146 — **1,074 of 1,074 events,
0 non-tape sends, and it rendered combat.** Full write-up in
[studies/tape/FINDINGS.md](studies/tape/FINDINGS.md), which is now the log of tape runs;
`§3.4` above is run 1 and stays as written. The four results that change what we know:

- **Combat renders from a recording** (T1). The operator named the fight — a Wolf, cast
  Vampiric Gaze then Deathly Swarm — and the tape's four `SKILL_ACTIVATED` messages carry
  skills 153 and 105 against it.
- **The client rendered a map it never asked for** (T2). Its own `VERSION` said map 148;
  the tape said 146; it drew 146. Same permissiveness as run 1's identity result, on a
  second axis. Note `--map` is a **no-op under a tape** — `MAP_OVERRIDE` sets state the
  tape path never reads.
- **D1's agent-id reuse is corroborated by ArenaNet's own traffic** (T3): 19 of the 45
  ids in that 186 s tape are created more than once, agent 281 nineteen times. Our probe
  and their server now agree, independently.
- **`GAME_CMSG 0x0046` field 1 is a skill id, not a slot** (T4) — ground-truthed by an
  operator label given before the payloads were decoded, then matched against the
  client's own skill and string tables. Candidate meanings for `0x00C1` and `0x0026`, and
  a confirmed 5 s keepalive on `0x0009`, came out of the same five minutes (T5).

The cheapest next thing this opens up is **a deliberately labelled input run** (T4/T5 were
an accident of five unplanned minutes) and **chaining tapes across a map transition**,
which is what would turn four instance tapes into one continuous session.

### 3.6 The loopback opcode sweep — 242 of 487 GAME_SMSG opcodes measured

**COMPLETE 2026-08-12**, plus the ten table-less opcodes and both quick-win controls. [studies/smsgsweep/FINDINGS.md](studies/smsgsweep/FINDINGS.md).
Our own server sends each catalogued opcode ArenaNet has never shown us to a client we
control on 127.0.0.1 and reads the reaction. **All 324 of the never-seen set are
measured** — the unattended loop stopped on "nothing left to plan": **82 ASSERTED,
3 FAULTED, 1 DROPPED_CHANNEL, 3 REPLIED, 235 SILENT**, with all 86 crash rows paired to
the dialog their own run captured and every reading taken in map 148 on a live player.
The ten with no receive-table entry were then taken one per run: **the family splits**,
four survive and six close the channel with a transport-level `Code=007` — no assert, no
dialog, client alive at character select. `0x000C`, the ping the client demonstrably
answers, is the control that makes that table mean something. **334 of 487 measured.**
Two bindings now stand: `0x0000` → c2s `0x0000` (the first-send confound killed by
`--reverse`, sent third behind two silent sends) and `0x0166`/`0x0167` → c2s `0x0079`,
whose handlers post adjacent event ids `0x10000100`/`0x10000101` through the same
dispatcher `0x0017` uses.

**One binding, and it is the first this project can quote.** s2c `0x0166` and `0x0167`
each draw an empty c2s `0x0079` within 10 ms — replicated in two runs, with `0x0164` and
`0x0165` silent immediately before them as internal negative controls. `0x0000 → 0x0000`
reproduces three times and stays CONTESTED, because `0x0000` is always the first send.

**The crash census maps the catalogue**: 8 opcodes want an inventory record, 6 an item, 6
a loadable file id, 5 a valid encoded string, 4 an attribute state, 3 a bag. `0x0137`–
`0x0163` is the inventory and item block — 17 of 60 crash rows in one contiguous stretch.

**What it cannot reach, measured rather than assumed.** The remaining gates are CLIENT
STATE, not payload: `charHeroData` wants a hero, the mission mask wants a finished
mission, `bagCount` wants bags past the starter. No wire value opens them from a level-1
character standing in one map. Six of twenty gates opened; the rest need a richer client.

Three readout defects were found the hard way and each printed a confident wrong number
first — a stimulus stream that could not see itself, a stimulus fired inside the client's
own load traffic, and a socket fence that scored **78 opcodes SILENT against a client
showing a crash dialog** because a Guild Wars assert leaves the process alive with its
socket open. The fence is the client's own ping reply now. A fourth was found only
because the operator said what was on screen: the default hostile was killing the player
throughout, so sixteen `SILENT` rows meant "silent on a corpse". `record()` refuses such
a run outright.

### 3.2 R4b and R4c, rewritten as counts

The old criteria could not be evaluated. R4b's was *"one skill from each mechanical
family resolves correctly"* and **"mechanical family" is enumerated nowhere in this
repo**. R4c's was *"an area populates and plays like the recording"* and **there is no
recording** — R0b has not been built, so that criterion referenced an artifact the plan
had deprioritised.

Both are now graded against an enumerated content surface:
[studies/presearing/MANIFEST.md](studies/presearing/MANIFEST.md).

- **R4b — *n* of **9**.** Pre-Searing's reachable skills span nine of the client's 21
  player-skill `type_code` families, and R4b is met when at least one named skill id in
  each resolves its effect correctly *against the client's own state* — not against our
  server agreeing with itself. The manifest names an exemplar per family (Frenzy 346,
  Flare 194, Healing Signet 1, Sever Artery 382, …). **Today n = 0.** Nine and not 21
  because the other twelve codes have no Pre-Searing content to test against; grading
  against 21 would grade v1 against non-v1 content.
- **R4c — split, because the two halves are reached by different instruments and reporting
  one number hides which.**
  *R4c-1, capture-free*: 19 of 19 map rows with resolved file ids and arrival points that
  pass the spawn-in-trapezoid test, ≥15 NPC templates, 2 of 2 mandatory quests completable,
  6 of 6 quest verbs implemented, 4 of 4 services working. **Today the content store holds
  9 map rows and 2 NPC rows** (`toolkit/content.py`'s own census, 2026-08-11: map 9, npc 2,
  item 1, spawn 1). Every map row carries a `file_id` and a `spawn_x`/`spawn_y`; **how many
  of the nine pass the trapezoid test has not been re-run**, so the map figure is a row
  count and not yet a score against this criterion. The printed "(today 2)" and "(today 1)"
  were true when written and were never updated.
  *R4c-2, formerly capture-gated*: 35–40 monster types with real stats and skill bars,
  graded on **types, never on spawn instances** — spawn counts are unstatable from any
  source this project has.
  **R4c-2 IS NOT BLOCKED — IT IS UNGRADEABLE, which is worse and is now measured.**
  ⚠️ **Its criterion cannot be evaluated as written, and one clause can never be met.**
  Full verdict: [studies/presearing/R4C2-FEASIBILITY.md](studies/presearing/R4C2-FEASIBILITY.md),
  which proposes a three-way split (R4c-2a roster / R4c-2b evidence / R4c-2c the name join)
  **and is a proposal until the owner adopts it**, exactly as the two rewrites above are.
  The four clauses, measured over the canonical 12-connection corpus:
  - *"35–40 monster types"* — **today 7** hostile definition slots (1346, 1420, 1421, 1431,
    1432, 1434, 1442), all from one 568 s visit to one map. Coverage-blocked; a live capture
    campaign fixes it at roughly one explorable per session. **And the denominator is
    contested by 22% between two of our own wiki passes** (91 vs 111 hostile), while the
    wire counts *slots* and the wiki counts *pages* — slots 1431/1432/1434 are one model
    (file 82023) at three levels, so "n of 91" can exceed 1.0 and is not evaluable either way.
  - *"real stats"* — health 3 of 7 and mode-ambiguous; energy 0 on the wire; **armour has no
    property id in any channel across 22,524 messages** and wiki armour is back-computed from
    observed damage, so fitting a damage formula to it closes the loop on itself. Armour and
    energy should be **struck, not deferred** — a deferred column reads as "not done yet" and
    invites a session that cannot succeed.
  - *"and skill bars"* — **structurally unreachable, and this is the finding.** `0x00DA` is
    the skill-bar message; it occurs 11 times in 22,524 and **0 of 11 name a `mon1` or `band`
    agent** (verified twice, independently). ArenaNet never sends a monster's bar to a
    client, so **no capture campaign of any length produces one.** A bar can only ever be
    *inferred from observed casts*. Today: 0.
  - *"graded on types, never on spawn instances"* — **survives and should be strengthened.**
    Slot 1442 alone is 202 of 585 monster-class creates.

  **This line previously read** "R4c-2 stays at 0 and is **reported as blocked until R0b
  exists**" until 2026-08-11, four days after R0b was met. Worse than stale: the monster stats it was waiting for have been sitting in the vault
  in the clear since 2026-08-07, and the join that makes them a *table* rather than a
  reading is measured — **`WORLD_CREATE_AGENT` field[2]'s definition slot is a stable
  server-side key across sessions**, slot 1434 yielding `PROP_HEALTH_MAX` 8 in two captures
  three days apart, on two characters, two connections and two agent ids
  ([studies/reconstruction/FINDINGS.md](studies/reconstruction/FINDINGS.md) §6.1). What
  gates R4c-2 now is **coverage, not instrument**: four kills of three species in the whole
  corpus. It is **unstarted, not blocked**, and the difference decides what to do about it —
  a blocked rung waits, an unstarted one gets a session. §7.6's caveat travels with every
  number it will produce: Reforged Mode is not recorded anywhere, and it scales enemy health
  ~20%, so each figure is base or base × 0.8 and nothing on this machine can say which.

**Carried in the criterion rather than buried:** five real mechanical families — Shout,
Interrupt, Well/Spirit/Trap/Ward, Block, Ritual — have **no** Pre-Searing exemplar at
all, and five more have exactly one. A green R4b therefore does not mean the skill engine
is general. That is the GW1 specialist's dissent from the 2026-08-06 review, now
quantified: you can finish v1 having proven very little about whether the engine can
drive a real Guild Wars fight. If generality matters it needs its own rung with a
post-Searing exemplar per absent family, and that is outside the declared v1 line.

*Both are proposals until the owner adopts them.* Two caveats travel with them. The
manifest's CLIENT numbers are strong and were re-derived independently here — 19 zone
rows at `continent == 1`, 1,333 player skills over 21 type codes. Its **WIKI numbers are
weaker than this repo's usual bar**: the browser route was unavailable for every pass, so
wiki figures came through search-engine prose rather than page reads, and the manifest
says so itself. Treat any wiki-only figure as approximate until re-read. And the manifest
raises one scope question no data can answer — whether "playable solo end to end" includes
the Ascalon Academy mission cluster and the hand-off into post-Searing, or stops at the
mission being completable.

**R0b replaces R0's C++ harness.** The capture harness stops being an in-process DLL. It does
**not** become a proxy — this section originally said it would, and that was wrong for a reason
this document establishes elsewhere and then failed to apply here: §1.5 and §1.6 record that the
auth and game channels are keyed by Diffie-Hellman between the client and the server, which is
precisely why *our* server cannot talk to a stock client without patching its parameters. A proxy
sits in the same position and holds neither private exponent, so it can relay ciphertext and read
none of it.

What R0b actually is: **a client we control, recording its own decrypted stream.** Headquarter's
headless-client approach (MIT, C, tracking live builds) is the instrument named in §4-A1, and
`gw-preservation/network-logger` is the in-client route to read for it. That keeps the property
the proxy idea was chosen for — it is not an in-process DLL hooking addresses that move with every
build — while being a thing that can exist.

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

> **The day-windows below are dead, kept until the owner rules on deleting them.** Measured
> from git against this document's own commit (`1ac675c`, 2026-08-04 19:56): the Days 1–14
> target *"a character standing in a map"* landed 15h19m later; Days 46–90's skill-table
> extraction landed at 19h16m; §3's separate "a quarter, not a week" estimate for R3 took
> 21h44m. The whole 90-day programme was consumed in under 46 hours — **except** the three
> items needing a human to act against the live service or answer an open question (A1, A2,
> Probe 3), which are still at zero. So the estimate is wrong by 15–100× in the agent-farmable
> lane and by nothing at all in the other, which is the useful finding: *the constraint is not
> throughput, it is the three things below that only the owner can do.* Status is §3; what to
> do next is §8.

The human is the bottleneck for exactly three things: anything that launches the game, anything
that judges whether the game *feels* right, and the account risk decisions. Everything else is
agent-farmable. **That sentence is the part of this section that held.**

**Human-only:** Probes 1, 2, 4. Playtesting. Deciding whether to use a secondary account.
**Agent-farmable:** the schema translation (A3), WASM tooling and symbolization (A4), the browser
harness (A5), the skill data pipeline (A6), Pre-Searing scope enumeration, and reading the mirrored
prior art.

- **Days 1–14** — Probes 1 and 2. Build and run OpenTyria (A2). In parallel, agents translate
  `msgdefs.c` into the schema and stand up codegen (A3). *Target: a character standing in a map.*
- **Days 15–45** — Probe 3. If it passes, the instrumented client becomes the capture harness (A1) and runs on
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
| Service closes or changes | Record every live session from inside the instrumented client; zero marginal cost once built. *The hedge is unbuilt, so the risk is currently unhedged — and this row said "leave the proxy on", which was never a thing that could exist (§3 R0b).* | hours |
| **Client auto-patches over ground truth, and the DH keys rotate with it** | **This happened during the session that wrote this document.** The updater replaced `Gw.exe` (10,404,032 → 10,483,904 bytes) and `Gw.dat`, moved the DH struct from RVA `0x6843e8` to `0x6910d8`, and **changed both the prime and the server's public key**. ArenaNet rotates the Diffie-Hellman parameters per build — which is why Headquarter stores 107 server keys rather than one constant. Consequences: the client patch is a permanent recurring step, not a one-time one; every capture and schema revision must carry a build id (free, per §2); and re-snapshot *before* accepting an update prompt, never after. Both builds are now vaulted. | ongoing |
| **The client phones home when it crashes** | `Gw.exe` embeds Sentry: `SENTRY_DSN`, `sentry.native`, `getsentry`, `x-sentry-rate-limits` are all present **[measured]**. The working method here is inject, patch, malform, crash — so the client's own outbound reporting channel is a posture problem HANDOFF §9 never considered, since §9 reasons only about server-side visibility. Neutralise it before the first malformed packet: block the endpoint at the firewall or null the DSN in the patched copy. Minutes, and it belongs on the R0 checklist next to the vault snapshot. | minutes |
| **The captures contain the owner's real ArenaNet credential** | The client sends its saved password to our own webgate on every login, and `vault/captures/portal/*.jsonl` records it as base64 — `<Password>…</Password>`, reversible in one command **[measured 2026-08-04]**. It has never been in git: `vault/` was gitignored in the first commit, before any content existed, so there is no history to rewrite and "private repo" does not bear on it either way. **Owner's decision, 2026-08-05: the repo stays private, and a credential-scrubbing / anonymising pass is a gate before any public push** — not a change to capture fidelity now, since the whole method depends on recording what the client actually sent. Until then the vault is the only copy and stays local. | deferred, by decision |
| Account loss | Never automate on the primary account — now enforceable rather than aspirational, because a second account exists (§7 Q4). **The old reason given here was wrong and is replaced:** it said "the proxy posture — watching your own traffic — is milder than injecting a DLL", but A1's instrument is Headquarter, a third-party client that logs into the live service. That is not a proxy. **SOURCED:** *MDY v. Blizzard* turned on unattended automation of gameplay, and Warden targeted automated play *patterns* rather than the presence of third-party code — which is why addons and injected tooling coexisted with it for years, and why `HANDOFF.md` can record that "GWToolbox is tolerated precisely because of how it has behaved". So the control is behavioural: human cadence, human hours, one client, never in a competitive context. §6.2 | one account |
| A client update invalidates months of offset work | Choose WASM: the module bytes are the code and offsets come from the module | free, if you switch |
| Two years with nothing playable | A2 and R1.5 both target a visible result inside 90 days | — |


### 6.2 Live capture, and the two client configurations

§7 Q4 authorizes automation against the live service. That breaks an assumption every
safety control in this repo was built on — that **nothing ever talks to ArenaNet** — and
the controls now have to distinguish two configurations rather than forbid one.

**"Patched" is not the property the rule wants.** `make_custom_client.py` applies four
modifications and only ONE disqualifies a client from touching the real service:

| Patch | Effect on a live login |
|---|---|
| **Diffie-Hellman triple** (generator, prime, server public B) | **DISQUALIFYING.** The client derives the ARC4 key locally from our `B`; ArenaNet's AuthSrv keys from theirs. The result is not a clean refusal, it is **a stream of garbage frames delivered to ArenaNet's auth server** — the mirror image of the `AUTH_CMSG has no opcode 26763` failure a stock client produces against us, which RUNBOOK already calls "exactly the kind of malformed traffic worth not sending". |
| Updater kill switch | Harmless, and **wanted** — it pins the build against an update that would replace our ground truth. |
| `CreateMutexA` guard NOPed | Harmless, and **wanted** — multiple instances is what capture at scale needs. |
| Mutex renamed | Harmless. A client-side fingerprint change, noted only because it is visible. |

So the non-negotiable is restated as **a client carrying OUR DH parameters must never
reach the real service** — three quarters of the patch set is fine on both sides.

**The sharpest hazard is not the DH patch, because the DH patch fails late.** Login is
three stages (§1.6). The DH substitution touches Stage B only. A patched client launched
at the live service with no `-portal` completes a **real Stage A portal login, with the
owner's autofilled primary credential**, and only then fails at Stage B. The
account-visible event happens before the patch matters.

**What must be true before the first live run. All five are met as of 2026-08-07**, which
is a change of state worth naming: from here the thing standing between this repo and
ArenaNet's bytes is code nobody has written, not a control nobody has built.

1. ✅ **A live-capture client is a separate build** — unpatched DH, with the updater and
   mutex patches. **Done 2026-08-07.** The build exists, the filing that keeps it apart
   from the loopback one exists, the launch gate exists, and the run directory is
   assembled and complete.

   *The artifact.* `make_custom_client.py --no-dh-patch` produces it — stock DH, updater
   off, multi-instance on — so it is reproducible after the next ArenaNet update rather
   than assembled by hand. It verifies the negative (the DH struct is byte-identical to
   the input) and then classifies the result against `vault/keys/dh_params_*.txt`, which
   a different tool dumped on a different day.

   *The filing, which is a safety control and not tidiness.* Whose DH a build carries
   decides where it may point, so the vault is split on exactly that:

   | | ours | stock |
   |---|---|---|
   | staged | `vault/client-patched/` `Gw.custom.<tag>.exe` | `vault/client-patched-live/` `Gw.live.<tag>.exe` |
   | assembled | `vault/run/<tag>/` | `vault/run-live/<tag>/` |
   | posture | loopback only, caged | live only, **cannot** be caged |

   `toolkit/clientpatch/dhbuild.py` answers `ours`/`stock`/`unknown` from the bytes;
   the patcher refuses to write either kind into the other's directory; `make_run_dir.py`
   classifies even an explicitly passed `--patched`; `test_handshake.py` selects the same
   way and refuses a wrong artifact *before* spawning a server. `python
   toolkit/clientpatch/dhbuild.py` audits the whole vault in one command.

   *Why all of that, from one afternoon.* The live build first landed **inside**
   `vault/client-patched/`, where two tools picked "the patched client" with
   `sorted(exes)[-1]` and `l` sorts after `c`. `test_handshake.py` went red with four
   failures and 8-of-13 checks, none of which was a crypto regression and all of which
   read as one; `make_run_dir.py` would have assembled a client that cannot key into
   `vault/run/`, which `drive_client.assert_safe` treats as the set of legal loopback
   targets. Filename order is not a safety property. `test_dhbuild.py` rebuilds that
   directory with the stock build sorting last *and* newest, and requires the right
   answer.

   *The launch gate.* Launch safety is no longer "is this client caged" but a **binding
   between the binary and the target**, read out of the bytes:
   `cage.assert_launch_safe(exe, host)` enforces all four cells, and `test_cage.py`
   proves each fires. **ours→loopback** needs a verified cage; **ours→live** and
   **stock→loopback** are refused; **stock→live uncaged** is *allowed*, because a gate
   that refuses everything is an outage rather than a control — and refusing the
   authorized run is how someone ends up forking a driver without the guards. This
   replaces whole-file hashing for the safety question: `pinned.py` knows exactly one
   patched SHA-256, so every client the patcher builds read as `unknown` and was refused,
   and its single `patched` bucket held four independent modifications when only the DH
   substitution decides anything.
   One thing fell out of building it. A **missing** `-portal` is not neutral — the client
   falls back to its compiled-in ArenaNet endpoint — so `intended_target()` resolves an
   absent flag to the *live* target, which means §6.2's sharpest hazard (a DH-patched
   client launched with no `-portal` completing a real Stage A login) is caught by a
   measurement rather than by a rule about flags.

   *The run directory, assembled 2026-08-07.* `vault/run-live/<build>/` was incomplete
   for a day — `Gw.dat` could not be copied while a client held the source open
   exclusively, and `assert_safe` refuses an incomplete run directory. Copied with every
   client closed and **verified byte-identical to `C:\gw\Gw.dat` by SHA-256 over all
   4.2 GB**, because "the copy reported success" and "the copy is the same file" are
   different claims and this one is the ground truth a live capture gets replayed
   against. `dhbuild.py` and `cage.py` both audit it clean: `stock`, and `UNCAGED` where
   uncaged is what the row wants.

   **So all five preconditions are met, and A1 is the next thing to build rather than
   the next thing to unblock.** *(Updated 2026-08-07: the driver now exists —
   `livesession.py` launches, sniffs, taps, holds, stops, assembles and scrubs. What is
   left is the run.)*

   *Two things a live session is that the loopback dry-run was not, both found by
   building the driver rather than by reasoning about it.* **It is several connections**:
   login is three stages (§1.6) on three endpoints, and Stage C's game-server address
   arrives *inside* the ARC4-encrypted `AUTH_SMSG_GAME_SERVER_INFO`, so it cannot be known
   when the packet filter is opened and cannot be added afterwards. The sniff therefore
   filters by PORT on any host and there is deliberately no way to pin it to an address —
   a pinned run records the auth channel, prints `1/1 connection(s) decrypted`, exits 0,
   and spends the one authorized session on the only channel loopback already reproduces.
   `--host` is accepted solely to refuse it by name, because RUNBOOK documented it for a
   day. **And it is several keys**: each DH-keyed channel derives its own `master_secret`
   through the same code, so the single tap slot is overwritten at every handshake and
   reading it once loses whichever channel handshook first. The driver keeps a keyring of
   every distinct value the slot held, and pairs keys to connections by a criterion the
   artifact can refute — the client's own first message after the handshake is opcode
   0x8001 on auth and 0x808a on game (**MEASURED 2026-08-07** over the 401 vaulted captures
   carrying both a channel marker and a first c2s frame: 271 of 276 auth, 42 of 42 game;
   the other five are the 08-04 synthetic markers). A wrong key cannot produce those two
   bytes, so a keyring that does not fit decrypts nothing and writes no file rather than
   leaving a believable artifact.

   *The duplication is resolved.* `dhbuild.py` and `buildid.py` were written the same
   afternoon by two sessions for the same job. Merged 2026-08-07, `dhbuild` surviving:
   it keeps selection, staging and the hostile-filename regression, and gains `buildid`'s
   exponent proof, `patch_state()` and `describe()`. Before deleting `buildid`, both
   modules were run against all three clients on this machine and agreed on `dh` and
   `patches` for every one — a migration is a claim about behaviour, so it was measured
   rather than reasoned about.
2. **The cage is per-client and its removal is elevated.** `isolate_client.ps1` pins a
   client to loopback by program path, so a live client cannot be caged — there is no
   partial setting. `cage-off` was reachable unelevated through
   `toolkit/harness/admin.py`, and `-Remove` takes down **every** cage on the machine;
   removed from the allowlist 2026-08-06, so uncaging now costs a UAC prompt.
3. ✅ **Launch sites check for a cage.** Done 2026-08-06. `toolkit/clientpatch/cage.py`
   asks the Windows Firewall whether *this* binary has both rules — the loopback allow
   AND the broad block, because an orphaned allow looks like cleanup and permits
   everything — and both launch sites (`drive_client.py`, `session.py`) assert it
   independently rather than one trusting the other. It classifies the binary through
   `pinned.identify()` and **refuses `unknown`**, which is the case that matters next:
   `make_custom_client` generates fresh DH parameters, so the next patched copy has a
   hash nobody has recorded. Fail-closed throughout — an undeterminable firewall is a
   refusal, not permission. `test_cage.py` proves all four refusals.
   *The state that prompted it: two patched binaries on disk, one (`…-probe`) uncaged
   for a day, and `assert_safe` waved it through because it checks the path and the
   flags, both of which an uncaged copy passes. Both are caged as of 2026-08-06.*
4. ✅ **The automation selects its account.** Done 2026-08-06.
   `toolkit/harness/accounts.py` decides by target: **loopback gets a synthetic
   credential and no real account at all**, because `webgate.py` says yes to anyone —
   its own comment says so — so a real login there bought nothing and is how the owner's
   password reached 206 capture records. A non-loopback target must name an account and
   that account must carry `automation: true` in `vault/keys/accounts.json`. The flag is
   **opt-in**, so an account with no flag — the primary — is refused by default rather
   than by remembering to exclude it; forgetting is safe, which a blocklist cannot
   promise. `-email`/`-password` are the client's own flags **[measured, argtable.py,
   build 38797]**; passing a password in an argv is visible in the local process list and
   is accepted deliberately over leaving autofill in charge, and `redact()` keeps it out
   of both launch sites' prints and the run manifest. `test_accounts.py` proves six
   refusals including the primary one.
5. ✅ **Live records are distinguishable from loopback ones.** Done 2026-08-06.
   `toolkit/origin.py` classifies every capture **ours / live / unknown**, and the third
   value is the design: a two-valued scheme forces an unstamped file to be called one or
   the other, and whichever default you pick is wrong exactly when it matters — the
   first live capture written by a tool that forgot to stamp. `authsrv.py`'s Recorder
   now writes an `origin` record as the first line of every session; unstamped legacy
   files infer OURS only from all-loopback peers **plus** our own session markers, and
   nothing ever infers LIVE, because `captures/patcher/` holds public addresses too.
   The guard that matters is `require_single()`: `test_movement_fidelity.py` pools every
   game-channel capture into one number, and a live file in that pool would blend two
   oracles invisibly. **The first live files arrived 2026-08-07 and the guard held**:
   `test_origin` now takes its live branch — a live capture is present, and pooling it with
   ours is refused by name. *(That test used to assert "no live capture exists yet", which
   is a check that goes RED on success; rewritten 2026-08-07 to assert the property that
   actually protects the corpus, so it gets stronger once a live file exists rather than
   turning the project's biggest win into a failing suite.)*

**Four defects the build turned up, all of them in the controls themselves.** Recorded
because every one was invisible to the thing meant to catch it:

* **Both launch sites had been unimportable since the cage guard landed.**
  `drive_client.py` did `import cage` with `clientpatch/` not on `sys.path`, so
  `drive_client.py` and `session.py` both raised `ModuleNotFoundError` at module level
  — the guard existed and the file holding it could not load. `test_harness.py` catches
  it on the first run; it is named in `CLAUDE.md`'s suite list and was not among the
  tests run when that suite was last reported green. Fixed, and `test_harness.py` now
  passes 36 checks with its floor tightened from a read-off 26 to the measured total.
* **`launch_caged.ps1` opened the cage on the daily path, months after it stopped
  needing to.** Its own comment ends "The real fix is to stop the updater from running
  at all, so the cage never has to open"; that fix shipped and is applied by default,
  and `RUNBOOK` went on naming the script as step 4 anyway. Opening the cage leaks by
  construction — firewall rules are evaluated at connection **establishment**, and
  Windows offers no supported way to tear down an established TCP connection. It now
  asks `dhbuild.py` and refuses any build carrying the kill switch. Its rule lookup was
  also broken: it matched an exact display name while `isolate_client.ps1` appends
  `[<tag>]`, so it found only rules left by an older version of that script.
* **`drive_client.py` wrote the plaintext password into `report.json`** while the console
  print of the same argv two lines later was redacted — the precise failure
  `accounts.redact`'s docstring says it exists to prevent. Found before a real automation
  account had ever used it. `redact_for_file()` now covers the address too, because
  `scrub_captures.py` matches JSON **keys** and in a manifest the address is a **value**
  inside an argv list, so a tree-wide scrub would have walked straight past it.
* **`test_handshake.py` selected its client with `sorted(exes)[-1]`.** `Gw.live.` sorts
  after `Gw.custom.`, so the first live-capture build in the directory silently became
  "the patched client" and the test reported that client and server derived different
  keys — a true statement about the wrong binary, and indistinguishable from a broken
  handshake. It now selects on `dh_verdict == ours`, which is the property it actually
  needs. `make_run_dir.py` had the same latent bug and was fixed before it could fire.

**R0b's deliverable was wrong, and is fixed.** §3 called it "proxy capture of a real
session", which cannot work: the channel is DH-keyed end to end and a proxy holds neither
private exponent — the same fact that forces us to patch the client to talk to our own
server. Re-specified 2026-08-06 in §3's rung table and in §4's structural note as capture
from inside a client we control, before the rung is started rather than after it fails.
The property the proxy idea was chosen for survives: it is still not an in-process DLL
hooking addresses that move with every build.

### 6.1 The derivation register

Which upstream each module's *code or layout* came from, and what that upstream grants.
It exists because on 2026-08-05 `toolkit/mapdata/gwdat.py` landed declaring itself a port
of `gw-preservation/fileserver-utils` — **the day after §1.1 wrote "never copy from them"
about exactly that repository** — and sat in the running server's dependency chain until
the 2026-08-06 review found it. The rule was in the plan; nothing was checking.

**SOURCED:** the model is ReactOS's post-2006 contributor taint register, not a Phoenix
clean room. A clean room is two teams, a specification wall and an audit trail; that is
disproportionate for one owner and a 356-line decompressor. A register is a table you
keep honest.

| Module | Derived from | Upstream grants | Status |
|---|---|---|---|
| `toolkit/mapdata/gwdat.py` | GuildWarsMapBrowser `SourceFiles/xentax.cpp` | custom licence — permissive, but **requires a repo link and visible credit**; it is *not* MIT | ✅ re-derived 2026-08-06, attributed in `THIRD-PARTY-NOTICES.md`, and the six-table correspondence is **checked** by `test_gwdat.py` against the vaulted mirror |
| `toolkit/mapdata/pathmap.py` | GuildWarsMapBrowser ImHex FFNA pattern | same | ✅ attributed 2026-08-06, same notice |
| `schema/messages.json` | OpenTyria `code/msgdefs.c` | Unlicense — public domain, no obligation | ✅ credited anyway; `overrides.json` keeps our corrections separable |
| `content/items.toml` `starter_hammer` | OpenTyria `GmDefaultArmors.c` | Unlicense | ✅ row records source `opentyria`, and records that no capture corroborates it |
| `toolkit/mapdata/archive.py` | OpenTyria — the archive magic's byte order | Unlicense | ✅ cited in the module |
| `content/npcs.toml` `hatcher`, `content/maps.toml` ids | gw-preservation — **all rights reserved** | nothing | ✅ verified-only: each row records what it was checked against in our own artifacts, and `toolkit/content.py` **refuses to load** one that does not |
| `toolkit/authsrv/probes.py` ALLEGIANCE constants | four-byte tokens `'play'`, `'nonc'`, `'mons'` | — | ✅ confirmed against our own client; **JUDGEMENT:** short functional identifiers of this kind are facts about the wire, not expression |
| `toolkit/mapdata/atex.py` | nothing — authored from our own record walk | — | ✅ checked 2026-08-06, clean |
| `toolkit/mapdata/dxt1.py` | nothing — DXT1/BC1 is a publicly documented format | — | ✅ checked 2026-08-06, clean |
| `toolkit/mapdata/datwrite.py`, `datplan.py` | nothing declared | — | ✅ checked 2026-08-06, no derivation statement and none needed |
| `toolkit/harness/wirecapture.py` | WinDivert (the packet backend, called via `ctypes`) | **LGPLv3** or a commercial licence; dynamic-linked, not vendored, used locally and never redistributed | ✅ carve-out pinned 2026-08-07 (CLAUDE.md): live driver **only**, never the server path or the suite. No WinDivert code is copied — only its documented DLL API is called. `keytap.py` takes no dependency. |
| `schema/overrides.json` — GAME_CMSG **names** | ldufr/Headquarter `opcodes.h` | **MIT** — permissive, attribution only | ✅ row added 2026-08-10, *before* the first name landed. Headquarter is where §4's A3 got the 60/40/194/487 counts and it has carried `ROTATE_PLAYER = 0x0040` all along, with no row here — the `gwdat.py` shape exactly. **What we take is corroboration, not the name**: 0x0040 was named from the client's own assert text `(rotation >= -1.0f) && (rotation <= 1.0f)` at `ChCliApi.cpp:5562`, read out of build 38797, and Headquarter agreeing is a second witness we did not need. Any *future* name adopted from Headquarter without that independent leg is a derivation and must say so in its `why`. |
| `toolkit/mapdata/terrain.py` — the **terrain chunk** layout | GuildWarsMapBrowser: `FFNA_ImHexPatterns`, `FFNA_MapFile.h`, and `SourceFiles/Terrain.cpp` | same custom licence as the two rows above — permissive, **requires a repo link and visible credit**, *not* MIT | ✅ row added 2026-08-10, *before* the module exists. The `pathmap.py` row covers the **pathing** pattern only and does not reach terrain. **What we take is the hypothesis, not the layout**: every load-bearing field is re-derived from the client's own 11-entry step table at `0xA74F28` and confirmed corpus-wide — see [studies/customarea/FINDINGS.md](studies/customarea/FINDINGS.md) §4 and §17.4. Recorded because upstream is a **witness we had to correct**, which is the strongest argument for keeping the row honest rather than dropping it: its pattern reads the tags positionally so its "tag5"/"tag6 Shadow Map" are the file's tags 3 and 9 and **tag 6 exists in none of the 349 maps**; its `cellSize` is not a cell size but `max(3, v/3072.0)`, a distance in whole terrain chunks; and its pattern and its own renderer **disagree with each other** on storage order — the renderer is right and only the pattern had been read. |
| `toolkit/mapdata/mapchunks.py` — the **Dependencies record** `{u16 id0, u16 id1, u16 pad}` and the pair→file-id formula | GuildWarsMapBrowser: `FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat` (`MapFileRef` / `MapFileRefPadded`, and the comment `decode: (id0 - 0xff00ff) + (id1 * 0xff00)`), the same expression in `SourceFiles/animation_state.cpp` | same custom licence as the three rows above — permissive, **requires a repo link and visible credit**, *not* MIT | ✅ row added 2026-08-11 by the verifier, *after* the module landed without one — the `gwdat.py` shape again, and the reason this table exists. The `pathmap.py` row covers the **pathing** chunk of that pattern and does not reach the dependency lists, exactly as the `terrain.py` row argues for terrain. **Everything else in the module is not upstream's**: the id decomposition, the 23-slot `s_chunkInfo` name table and the `alloc` byte split are read from the client's own strings and asserts (SOURCE-CODE, [FINDINGS](studies/customarea/FINDINGS.md) §3/§17.4), and the signature `0x29939830` and the `(size − 5) % 6` law are measured from the archive — GWMB has neither. **And upstream is a witness we corrected**: nobody upstream wrote the inverse, so nobody found that the pair encoding *aliases* (`id0 ≥ 0xFF00` names the same file as `(id0 − 0xFF00, id1 + 1)`), which retail's own writer uses in 85 records of 134,290. `THIRD-PARTY-NOTICES.md` names the module. |
| **monster AI: aggro radius, leash, scatter, targeting, formation, patrol** — *no module takes these yet* | GWW (`wiki.guildwars.com`), the pages named in [studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md) §4 with revision ids | GFDL 1.2 / CC BY-NC-SA 2.5 (dual) — **attribution required**, and the NC arm is satisfied by this project being local and personal (`CLAUDE.md`) | ✅ row added 2026-08-11 **before any module takes any of it**, which is the first time this table has been used the way it was designed rather than retrofitted. **The split that matters is values vs. algorithms.** The gwinch table (aggro bubble/earshot 1012, touch 144, casting 1248, longbow 1498, compass 5020 …) is a set of *values* and reaches the repo as `content/*.toml` rows carrying `source = "wiki"`, which `toolkit/content.py` already gates. **Scatter, leash, target priority and the melee-surround formation are *algorithms*** and are what this row exists for — none has landed, and none may land without citing it here. **Currency is the failure mode, not licence**: three of the four core pages carry `Category:Unofficial terms`, *Foe* has not been revised since 2021 and *Patrol* since 2017, the wiki **contradicts itself** on target priority (§4.3), and where a stale page and a fresh one disagree the stale one was wrong both times. So every borrowed row records its revision id, and a value our own artifacts can check is checked rather than adopted. |

**The rule this table encodes:** before a module takes a layout, an algorithm or a table
from any upstream, add its row *first*. If the upstream grants nothing, the only
permitted use is to verify a value we derived ourselves — which is what
`toolkit/content.py` now enforces at load rather than leaving to memory.

Two things this register deliberately does **not** claim. It is not a statement that no
contributor ever read an unlicensed repository — reading them is explicitly allowed and
is how several of our own bugs were found. And it says nothing about ArenaNet: the
provenance gate is separate, absolute, and covers bytes rather than derivation.

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

**Q3. Does the provenance gate survive contact?** ✅ **CLOSED 2026-08-11, by the owner. The gate
does not move; its boundary is now written down.** The question was posed as "§9 says zero ArenaNet
bytes in the repo, ever, but R0 vaults `Gw.exe` and `Gw.dat` and every schema derives from them",
and the answer turned out to be that **the gate already said the right thing and only one of its
two sentences was being read.** `.gitignore`'s header is: *"Zero ArenaNet bytes in this repo,
ever… Everything derived regenerates from the owner's own legally purchased install via a
documented extraction step."* The second sentence is a permission and it governs derived data.
`CLAUDE.md`'s one-line summary — "only our code and our observations" — is what a cold session
reads first, and every session resolved the ambiguity by refusing.

**That refusal had a measured cost.** `studies/reconstruction/FINDINGS.md` §9.4 left the ruling on
a derived assert table neutral rather than deciding it; §4.9 quoted three extracted item names into
what would have become a tracked file and nobody caught it until a critic re-read the draft; and
R4c-2's unit data sat unbuilt behind a rule that never actually forbade it.

**The boundary, and it is measurement versus expression — not bulk versus single, and not data
versus code:**

- **PERMITTED: facts we measured.** Numbers, bounds, counts, strides, ids, offsets, addresses,
  layouts. A monster's level, an item's requirement, a table's element count. These are facts about
  a system, they are not ArenaNet's expression, and the gate's own second sentence contemplates
  them. **In bulk, and generated, subject to the three conditions below.**
- **REFUSED, unchanged: ArenaNet's expression.** Asset bytes, `Gw.dat` chunks, textures, audio,
  model data, decompiled function bodies, and **verbatim assert expressions with their source path
  and line** — `P:\Code\Base\Rtl\Random.cpp` plus `fraction <= 1.0f` is a line of their source
  code, and a 477-opcode table of them is a source dump with extra steps. What a derived table may
  carry instead is the *constraint*: opcode, field, bound, address. That is the useful content and
  it loses almost nothing.
- **NAMES AND AUTHORED TEXT: commit the id, resolve at run time.** Item, skill, NPC and dialogue
  strings are individually trivial and in bulk a dump of authored work. A row carrying
  `model_id = 419, name_string_id = 2519` is fully useful to the server and carries no ArenaNet
  expression at all. **This is not a compromise invented for this ruling — it is the pattern the
  repo already proved.** FINDINGS 14's five mandatory chunks are 232 bytes per map of genuine
  ArenaNet constants, read from the owner's archive **at run time**; `mapbuild.py` refuses without
  one (`NoConstants`), and `test_mapbuild.py` §2 reads the builder's own syntax tree to require no
  bytes literal over two bytes in it. Extending that to unit and item data is consistent with what
  already ships and is strictly better than committing the data.

**Three conditions on anything committed under the permission**, and they are what keep this a
boundary rather than a hole:

1. **The extractor is in the repo and the row names it.** If the tool that produced it is not
   here, the artifact does not regenerate and the gate's second sentence is not satisfied.
2. **The row records the build it came from.** Build 38797 today. A number with no build is a
   number that cannot be re-derived or refuted.
3. **Provenance is per row**, the way `content/*.toml` already carries it — not per file, not per
   commit message.

**REFINED 2026-08-12 by the owner: the refusal is aimed at BULK, and a single assert cited as
evidence is a measurement.** The clause above — "verbatim assert expressions with their source
path and line" — was read literally for one session and produced a 134-site sweep across sixteen
documents. That was too much, and the owner's question ("are we going too crazy with provenance?")
is answered by this section's own history: **the costly mistakes in this repo have been refusals**,
not disclosures. Three are recorded four paragraphs up. So the boundary gains a size term and a
source term:

- **A single assert expression, cited as the evidence for a claim, is a MEASUREMENT.** Permitted,
  with its file and line. This is what `studies/smsg/FINDINGS.md` does twenty times over to name
  GAME_SMSG opcodes, and the quote is what lets a reader audit the naming argument without the
  binary in front of them. Removing it costs real evidence quality and buys almost nothing.
- **A BULK DUMP of assert strings is still ArenaNet's expression.** A 477-opcode table of them is
  a source dump with extra steps, exactly as the paragraph above says. The line is accumulation,
  not any one citation.
- **The crash dialog is NOT extraction.** `Assertion: <expr> / File.cpp(NNN)` is text the retail
  client puts on screen for any player who crashes; people paste it into forums. That is
  categorically different from a scripted sweep of the PE's string table, and the two had been
  treated identically.
- **Unchanged and absolute:** asset bytes, `Gw.dat` chunks, textures, audio, model data, and
  decompiled function bodies. That tier is the one with teeth and it does not move.

**What this leaves.** [studies/provenance/FINDINGS.md](studies/provenance/FINDINGS.md) is the
audit. `content.py` enforced the PERMITTED half of this ruling from the day it was written; the
REFUSED half applied to prose and was checked by nobody, which is the finding worth keeping. **46
sites in 15 files were scrubbed** before the refinement landed — they read fine and are left that
way, but they are no longer *required* to be at zero. The **104 remaining** are now permitted, and
`toolkit/provlint.py` is repurposed from a zero-tolerance gate into an **accumulation tripwire**:
it fails when a document starts becoming a dump, not when one is cited. Two findings worth carrying
back here: a `P:\Code` grep finds only **13 of the 134**, because most citation uses
`AgMsg.cpp:513` rather than the full build path — and **the illustrative example three paragraphs
above is itself the pattern it once forbade**, kept deliberately, because a rule that cannot show
what it means is harder to follow than one that quotes itself once.

**What this deliberately does not touch.** The **derivation register** (§6.1) is a *second and
separate* gate: it governs other people's work — OpenTyria, Py4GW_Reforged, GWCA, `gw-preservation`
— and it is a licence question, not the ArenaNet question. Loosening nothing here changes it, and
"we relaxed provenance" must never be read as covering both. `toolkit/content.py`'s verified-only
refusal for unlicensed upstreams (owner's ruling 2026-08-06) stands exactly as written.

**The three arguments against going further than this**, recorded so the next person to propose it
has to answer them: retrofitting is impossible — once bytes are in the history of a repo that is
half merge commits, nobody will ever be confident they are out; it closes the currently-open door
to sharing any of this; and the gate has an epistemic function as well as a legal one, in that the
349/349 byte-exact round trips exist partly because copying was not available.

**A rule nothing checks is a wish** — this document's own §1.1 lesson, learned while `gwdat.py`
sat in the server's dependency chain breaking a rule that had been written for two days. The
loosening direction is the one where that matters most, so the three conditions are enforced by
`toolkit/content.py` and `toolkit/test_content.py` rather than asserted here.

**Q4. A secondary account for automation?** ✅ **CLOSED 2026-08-06, by the owner.** A second
account is bought. **Automation against the live ArenaNet service on that account is
authorized** — and it "shouldn't be the go-to test mode". Both halves are binding: the
default loop stays hand-driven against our own server, and live automation is a mode you
enter deliberately for a capture campaign, never a convenience left switched on. The
conditions and the machinery that has to change first are §6.2. **A1 is unblocked; it is
not yet safe to run.**

**Q5. Does Pre-Searing remain the finish line?** *Recommendation: yes, unchanged.*

**Q6. May this project take a native (C/C++) toolchain dependency?** ✅ **CLOSED 2026-08-12,
by the owner.** *"I don't mind the C/C++ requirement for the project."* **A compiler is a
cost, not a blocker.** Routes that need native code — a hook DLL, an injected loader, a code
cave assembler — are costed on their merits and are not refused on dependency grounds.

**Why this needed asking, and it is Q3's shape exactly.** `CLAUDE.md` opens its dependency
rule with *"Python 3, standard library only. No third-party dependencies anywhere in
`toolkit/`"* and then names two narrow carve-outs. Read cold — which is how it is always read
— that makes a native DLL look **forbidden**, so a route needing one gets scored BLOCKED
rather than expensive. That is the same failure as Q3: a rule refusing something it never
actually said, with the refusal costing real work. The ruling was volunteered by the owner
mid-pass, unprompted, while a workflow was costing exactly those routes for the custom
profession arc (`studies/profession/WORKAROUNDS.md`).

**What does NOT change, and this is the one place the ruling has been scoped rather than
quoted.** The owner's words were "for the project", which is broader than the boundary below.
The existing bare-machine requirement is a *separate* rule with its own reason, and it is
being left standing until the owner says otherwise:

- **The server path stays dependency-free**, and so does every tool whose byte patterns are
  fixed — `asserts.py`, `msgshape.py`, `areatable.py`, `genericvalue.py`. Those must keep
  working on a bare machine, which is why the `capstone` carve-out was scoped to exactly two
  files rather than to "client analysis" generally.
- **The second gate is untouched.** A native dependency is still somebody else's work: it
  needs its §6.1 derivation-register row and its licence checked *before* a line imports it.
  "We relaxed the dependency rule" has never covered the licence question.
- **Prefer `ctypes` where it genuinely suffices** — not as a rule, as economics.
  `toolkit/harness/keytap.py` already does cross-process `ReadProcessMemory` with
  ASLR-correct module-base resolution in pure `ctypes`. Where that generalises, it buys a
  shorter iteration loop and no compiler in the inner cycle. Where it does not, reach for the
  compiler without apology.

If the intended scope was wider than this — native code on the server path, or dropping the
bare-machine requirement — say so and this entry gets corrected rather than reinterpreted.

---

## 8. Immediate next actions

### Custom professions — a five-document arc, and one live result (2026-08-12)

**Read [`studies/profession/RUNS.md`](studies/profession/RUNS.md) first.** It is the only one
of the five made of observations rather than readings, and it corrects the other four.

| Doc | What it settles |
|---|---|
| [`FINDINGS.md`](studies/profession/FINDINGS.md) | The limits. `CHAR_PROFESSIONS = 11` is a compiled array *dimension*, not a table row — 29 bound checks over 13 modules, and the assert reporter is **noreturn**. |
| [`WORKAROUNDS.md`](studies/profession/WORKAROUNDS.md) | The routes. The 29 session-enders are **one 5-byte patch site**; the armour composite gate is a redirect, not art (professions 0/1/2/9 already share a row). |
| [`MODDABLE.md`](studies/profession/MODDABLE.md) | The design for arbitrary N. Ceiling **256** via the `u8` carriers; the appearance nibble is real but different storage. Custom ids start at **12** (11 is the client's sentinel). |
| [`ATTRIBUTES.md`](studies/profession/ATTRIBUTES.md) | **204** custom attributes (52–255), capped by a one-byte field. 191 same-length edits; custom attributes start at **52** (51 is the NONE sentinel). |
| [`RUNS.md`](studies/profession/RUNS.md) | **OBSERVED.** Profession 12 rides `0x00A6` and the client plays on 5.1 s. It dies in the **skills panel**, on a **null-pointer** assert — not a bound check. |

**The next rung, and why it is cheap.** `R1` — NOP the `call` at `0x00487C11`, five bytes,
one site for all 19,758 asserts. The ABI it depends on is confirmed by a live crash
(`RUNS.md` §3), and `ret 4` is correct because there is exactly one stack argument. With
asserts falling through, one client run yields the *ordering* of many profession-keyed
surfaces instead of only the first.

**The cheaper alternative that may not need patching at all.** The assert was
`*skill` — nothing registered for profession 12, rather than "12 is invalid". **Send a
skillbar for the custom profession before opening the panel** and see whether the null
clears. If it does, the mechanism is population, not bounds, and most of `ATTRIBUTES.md`'s
191 edits are not on the critical path.

Probes are registered and encode-checked: `profession_custom`, `profession_ab`,
`profession_sentinel`, `profession_max` (`toolkit/authsrv/probes.py`). L0 is done —
`agents.py`'s `CHAR_PROFESSIONS_MAX = 6` was a live bug that refused professions 7–10.

---

**Status lives in §3, not here.** This list is what to *do*; §3 is where the project *is*.
Cross off an item in the same commit that lands it — on 2026-08-06 this list still opened
with "R2 — the game server" thirty-two hours after R2 was standing in a map, and `CLAUDE.md`
calls this the live list, so a cold session was being handed a finished task as its next one.

**Done since this list was written** — kept to one line each so it stays a plan and not a diary.
R2 (`aedc214`), movement and collision (`885d05d`, `a97c7c4`), the client's packet-format
tables dumped and reconciled against our catalog at 477/477 (`toolkit/schema/test_catalog.py`,
which retires old item 3), the skill table extracted and joined to the wiki by id
(`toolkit/clientscan/skilltable.py`, which retires old item 6), a hostile NPC that can be
attacked, killed and revived, and the content store (`content/*.toml`, `501698b`).
**2026-08-10:** R0b and R1.5 both met (§3, §3.3–§3.5), and the labelled input run built and
run twice (`toolkit/authsrv/labelrun.py`, [studies/cmsg/FINDINGS.md](studies/cmsg/FINDINGS.md))
— witnessed `GAME_CMSG` opcodes 15 → 23 of 194, seven named in `schema/overrides.json`.

### 8.0 Next, as of 2026-08-11 (`10b11dc`+, suite 53/53, 1,982 checks)

*1,927 is **derived, not re-summed**, and says so: the 1,878 below was measured over 50 files, and this session added `test_behaviourrun.py` (35, new) and took `test_wirecapture.py` from 28 to 42 — both counted from real green runs. 1,878 − 28 + 42 + 35 = 1,927. The suite runner reports 51/51 green in 611 s; its per-file log truncates, which is what made the earlier 965 wrong, so the arithmetic is shown rather than a figure quoted from a partial log. The 1,878 figure's own method:* Method, because the gap is
large enough to want one: run each of the 50 files in `toolkit/**/test_*.py` as its own
process, take the `ALL CHECKS PASSED (N checks` line, sum N, and require every exit code to
be 0 — 50 of 50 green. This is a **default** run, so the three tests with an `--all` mode
(`test_pathchunk`, `test_terrain`, `test_mapfile`) contribute their default subset and not
their full sweep; quoting a bigger number would need the ~20 minutes those take. The file
list is reconciled against `CLAUDE.md`'s suite list in both directions: 50 named, 50 on disk,
none named that does not exist and none on disk that is not named. That reconciliation is
the point — the first sweep of this session ran 49 and would have reported a full pass,
which is the defect `CLAUDE.md` already names from the other side.*

0n. ✅ **CLOSED 2026-08-12 by the owner, the same day it opened — and the decision was
    to STOP, which is the interesting part.** The question was what to do with 104
    refused triples left after a 46-site scrub, 65 of them in
    `studies/smsg/FINDINGS.md`. **Ruled: a single assert expression cited as evidence
    is a measurement; the refusal targets bulk dumps and decompiled bodies** (§7 Q3,
    refined). The 104 are permitted, the backlog is retired, and the scrub stops here.
    Rationale, in the owner's framing: provenance must not hinder development speed,
    and this section's own record says the expensive mistakes have been **refusals** —
    an undecided assert table, three names caught late in a draft, R4c-2's unit data
    unbuilt behind a rule that never forbade it. `smsg`'s quoted asserts are the
    auditable half of how twenty opcodes got named; scrubbing them would have traded
    real evidence quality for negligible risk. `toolkit/provlint.py` stays, repurposed
    from a zero-tolerance gate into an **accumulation tripwire** — it is the one part
    with no recurring cost, and it now fails only when a document starts becoming a
    dump. The hand-sweep expectation the audit created is **deleted**: an unbounded
    manual grep in service of the low-risk tier is exactly the drag this ruling exists
    to avoid. The checker catches what it catches, and that is the standard.

0m. **THE MONSTER-AI DIVE LANDED, and it leaves four desk tasks that need NO capture,
    NO client launch and NO operator.** [studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md)
    is the study; its §9 ranks every open question by cost and these are the whole
    top of that ranking. Each is an afternoon and each closes a named lead:

    1. ✅ **DONE 2026-08-11 — `CHAR_AI_MODES` IS 3, AND IT IS THE STANCE WIDGET.**
       The prediction was stated first and confirmed on every axis. Five bound
       sites read `cmp <var>, 3`; two independent switches (`GmAgentCommander:150`,
       `GmView:6743`) compile to `sub`/`je` chains with exactly three arms each,
       so the count owes nothing to any `cmp`; `AI_MODE_ICONS` is also 3, a
       parallel icon array; `CHAR_AI_MODE_AGGRESSIVE` is 0; and the switch maps
       the three modes to consecutive string ids 44156/44157/44158, which
       `textrec.py` resolves to **Fight / Guard / Avoid Combat**. So the only
       named server-shaped AI concept in the shipped image is the player's own
       hero-and-pet stance control, **the binary negative is now total**, and the
       `HeroActivate (… aiMode %d)` format string reads as the client telling the
       server which stance the player picked. `studies/monsterai/FINDINGS.md`
       §2.2.1, with the four reproduction commands in §2.2.2. **The read
       self-validated**: an MSVC assert pushes its own source line as an
       immediate, so every one of the nine sites had to agree with the line
       `asserts.py` reports from a different mechanism, and all nine did.
    2. ✅ **DONE 2026-08-11 — THE FLAGS ARE DISPLAY, ALL NINE READERS.** Prediction
       stated first (display, not combat) and confirmed. The `0x0056` handler chain
       is a pure marshaller: it writes 32 bytes into `base[+0x7fc] + def_id * 48`
       and interprets nothing, so the meaning lives in the readers. There are nine,
       and every one is `AvChar`/`AvApi` — `Gw\AgentView`, the renderer — or
       `PtRoster`/`PtMinionRoster`/`CtlInstance`, which are party-panel frames and
       the UI control library. **No combat site, no gameplay site.** Bit 9, which is
       the near-perfect combatant separator on the wire (**0/302 vs 282/283**, with
       bit 8 covering the single straggler), is an **animation gate** in `AvChar`
       whose branch ends in `seqIndex != SEQ_INDEX_UNDEFINED`. So the partition is a
       consequence of a display rule, not a combat rule.
       **Two by-products worth more than the answer.** The client dispatches
       definition ids on the top nibble — `0x20000000` → the monster table (48-byte
       rows), `0x30000000` → the player table (80-byte rows), else an assert — and
       **the wire agrees**: 585 of 585 joined creates are `0x20000000`-based, 48 of
       54 ids join under `− 0x20000000` and **0 of 54** under the identity. And
       `AvChar` consumes row+0x14 — the byte we call `profession` — as an
       **appearance** parameter, which is fresh evidence against the gameplay
       reading §3.7 already doubted.
       **The sting was ours and it dissolves**: our hatcher's `flags = 0x20C` is
       CORRECT — a Hatcher is a Collector, a non-combatant, and that is what
       ArenaNet declares for one. What it shows is that our test hostile is a
       non-combatant wearing a fight, which `content/world.toml` already says out
       loud. Nothing in `content/` needs changing.
       `studies/monsterai/FINDINGS.md` §3.7.1, reproduction commands included.
       **And the result carries its own scope limit**: `ChCliBase`'s consumer has NO
       direct caller — it is installed as a callback — so `--xrefs` demonstrably
       under-reports inside this very result, and "every reader" means every reader
       that method can reach.
    3. ✅ **DONE 2026-08-11 — IT IS A SPATIAL QUERY LIBRARY, NO STEERING.**
       All 88 asserts across the subsystem read. The vocabulary is exhaustively
       geometric — trapezoids and their above/below links, portals, barriers,
       SINK_NODE/X_NODE/Y_NODE, segments, flood fill, blockMap/mapDims,
       tileMap/tileDims — and there is no follow, arrival, desired-velocity or
       repath concept anywhere. It answers WHERE CAN I GO and never WHERE SHOULD
       I GO, so **movement policy stays in the "cannot be settled" tier.** This
       one mattered because `Engine\Map\Path` is in the SHARED tree, so
       ArenaNet's server compiled these same files — it was the one place
       server-side movement logic could have been visible.
       **Three corrections to the study's own accounting**: the directory is NINE
       files, not eleven; `PathBsp.cpp` carries zero asserts and was listed as
       though read; and a separate `Engine\Map\PathEngine\` (`PeApi`,
       `PeObject`) exists that nobody mentioned and that also has zero asserts.
       **Three files remain unread because no tool here can see them.**
       **A new search axis closed the negative's own named hole.** The study ran
       33 keyword searches over assert TEXT and never over the 936 embedded
       source FILE NAMES. Scanned: no name contains steer, pursu, chase, follow,
       seek, flee, wander, patrol, roam, brain, behav, tactic, decis, aggro,
       threat, navig, flock, herd, goal or waypoint. Three names did hit and
       their DIRECTORIES dispose of all three — and one is
       `Gw\Ui\Game\Compass\CompassAIControl.cpp`, the "AI Control" file the
       study flagged as structurally unsearchable. Its path answers it,
       corroborating task 1's Fight/Guard/Avoid-Combat result from an angle that
       shares no evidence with it. (`AtAvoid.cpp` is `Ui\Game\AgentText` —
       floating-label overlap avoidance; `GmWalk.cpp` asserts
       `evt.code < KEYSTATES`, the player's own walk keys.)
       **Kept**: `PathApi:753/754 obstacleCenter`/`obstacleRadius` is a second
       and STRONGER dynamic-obstacle witness than `PathObstacle:176` — a public
       API parameter rather than an internal invariant, so the shipped interface
       accepts moving circular obstacles, and `pathmap.py` has none.
       `MsPathPack:115 !m_charIndex.Count()` is a path pack keyed by CHARACTER
       and is unread. `PathData:34` bounds world y to ±131071.0 (2^17−1).
       **And a reading of mine was refuted by our own decoder**: I took
       `PathBuild:2297 def->trapezoidCount < 1024` for a per-plane cap, and 40 of
       1,805 planes across 60 retail maps exceed it, the largest 6,577. `def` is
       a build-time input. `studies/monsterai/FINDINGS.md` §2.1.1.
    4. ✅ **DONE 2026-08-11 — NO SPAWN TABLE, AND THE QUESTION WAS MALFORMED.**
       Nine agents over the Props chunk. **The framing first**: this item asked
       whether a prop model id lands in the `0x20000000` creature-class range,
       and that is two unrelated numbering schemes sharing a leading `2`. The
       leading nibble of a **chunk id** is its *stage* field
       (`decompose(0x20000004)` → stage=Bloated, baseId=4); `CHAR_CLASS_MONSTER_BASE`
       is the top nibble of a runtime **agent class id** that never appears in
       the archive. And the field itself is a **u16** — corpus-wide 0..439 — so a
       32-bit tag cannot fit in it and the search as posed had no failing branch.
       **The answerable question is what the index RESOLVES to**, and it resolves:
       `+0` is a per-map index into that map's own Props Dependencies chunk
       `0x21000004`, in range on 346/346 maps that have one, with a cross-map
       control that forces an out-of-range in ≥44.9% of 119,716 pairings.
       **The answer is no.** All 285,670 prop records in 349 maps resolve to model
       files; **0** resolve to any of the creature model ids we can name. Under
       the right null — creature ids are drawn from the archive's model files, of
       which the props system names 54.65% — P(zero) ≈ 3.9e-26. The structural
       reason is better than the count: **interactive world objects in this client
       are gadget AGENTS** (`GdCliApi.cpp:430 agentDef == GW_AGENTDEF_GADGET`), a
       subsystem disjoint from `Engine\Map\Props`, and **zero** of the 692
       asserts across 73 Agent/Char/Gadget files reference a map prop. Looking for
       creatures in Props was looking in the wrong subsystem.
       **But the slot is not closed — it is newly OPEN.** Only 32.68% of the Props
       chunk is the prop array. The other **67.32% frames as `{u8 tag, u32 size}`
       records closing 349/349** (both ±1 start controls close 0/349), two tag
       sequences only, and **tag 1 alone is 66% of the entire Props chunk corpus**
       — framed, walkable today, and read by nothing in this repo. That is now the
       single most valuable unread structure in the map format.
       `studies/monsterai/FINDINGS.md` §3.10.1, which also corrects two reversed
       size ranges in §3.10 and lists what each of the 23 slots actually is: **11
       have no field-reading code anywhere in the repo.**
       **A tooling defect fell out and is fixed in the same commit.**
       `asserts.py --modules` keyed on the source BASENAME and printed the first
       colliding file's path, so `Engine\Map\Props\PrApi.cpp` (19 sites) was
       invisible behind `Gw\Pref\PrApi.cpp` (67) as one `86` line — a module
       missing from the census that decides what source files exist. Now keyed by
       full path, `--file` prints the split, and `test_codescan.py` §8 pins it
       (62 checks, floors 56→62 / 16→22). Checked and clear: no Path basename
       collides, so task 3's read is unaffected.

    **And one analyser check that needs no new session either:** run the `0x001E`
    tick-clock integral against the wire span on the two EXISTING captures. If it
    reddens there, the wire-clock-to-plaintext mapping every timed claim in this repo
    rests on is broken — which is worth knowing before a campaign is designed on top
    of it, not after.

    **What is NOT on this list is the campaign itself.** It is 6–10 operator sessions
    at human cadence over two to three weeks and it is the owner's call, not a task an
    agent picks up. §7 of the study specifies it fully — operator script, the live
    CONTROL predicate (which is *not* `labelrun`'s: against ArenaNet the world keeps
    talking, so "no traffic" reddens in every window), the `behaviourrun.py` analyser
    with nine checks that can go red, per-question stopping rules fixed in advance,
    and an explicit refusal list. **Read §7.8 before proposing any shortcut**; the
    cheap way to get n on skill selection is exactly the traffic pattern that closes
    accounts, and grinding one spawn point is refused rather than refuted.

0k. **DONE 2026-08-11 — `0x0026` IS ON THE WIRE and the attack blocker is dead.**
    The `worldaction` labelled run on loopback drew **four `ATTACK_AGENT` at our own
    Hatcher across three steps** — one on a plain left-click, two on a double-click —
    and **zero `0x0033`** in the same run, both idle controls silent. Per the outcome
    table below, that is "the blocker died to work already landed": no fix aimed at it
    ever worked, and none was needed once the agent was correctly stated. **What blocks
    a fight now is ours** — the server had no dispatch arm for `0x0026` and answered all
    four with silence; the arm is added in the same commit. Two claims of mine died with
    it: there is **no right-click context menu on a world agent** (I invented the
    gesture; `0x005144F0`'s actions list is real, its route to the screen was not), and
    the **"prohibited marker" is the button that clears the selected target** — which was
    §10's founding observation. Full result and both retractions: `studies/enemy/PLAN.md`
    §10.7. **Still un-run from this item: 0c's burrow probe.** The original text follows.

    **THE NEXT ACTION IS ONE OPERATOR SESSION, and the design changed today.** §10.6
    reframed the whole attack arc: `0x0033` is not a refusal and not an "interaction" —
    it is **arm 1 of the six-arm world-action switch** at `0x00514840`, where ArenaNet's
    agents get arm 0 (`0x0026` ATTACK). The client resolves a click to an action and
    sends it; ours resolves to the wrong arm. Four target properties and our own weapon
    are all measured correct (§10.1, §10.2, §10.4), and `is_explorable` is now REFUTED as
    the lever — **ten** of the nineteen zero-attack sessions had it set and produced
    80 × `0x0033` with zero `0x0026`.
    **Nothing has been clicked since 2026-08-06.** All 21 game sessions on 2026-08-11
    produced no world action at all, and every property above was measured after the last
    click. The 206-to-0 split is a fact about a five-day-old server.
    **The run.** Loopback, Hatcher spawned, `--explorable` (not because it unlocks
    anything — it does not — but so a silent drop at the send leaf cannot be confused with
    the switch's choice). Then, in one session: **(a)** right-click the agent and read the
    context menu, which `0x005144F0` builds from the same gate, so the menu IS the gate's
    answer as the live client computes it; **(b)** double-click it — `0x00C1` alone is
    "selected, no action attempted", which is all today's sessions did; **(c)** run
    `labelrun.py`, whose `attack` step **has never been aimed at one of our own agents**
    (all three labelled runs in the vault are tape sessions).
    **What each outcome means.** `0x0026` on the wire → the blocker died to work already
    landed. `0x0033` again → it survives every measured property, and the create-burst
    differential is next. Menu offering Attack but nothing on the wire → the send leaf.
    Menu showing "Talk To" → allegiance is not 3 today and §10.1 needs re-measuring.
    Fold 0c's burrow probe into the same session, as 0a already says.


0j. ✅ **DONE 2026-08-11. The attack refusal is NOT on our side of the interaction, and
    that is now measured rather than argued.** §10.3 read the refusal down to one bit —
    for an ENEMY target the client's eligibility test is `0x005147F0`, which never looks
    at the target and instead returns **bit 25 of the PLAYER's own equipped weapon**. It
    ended by naming one step and telling the next reader to take it before changing
    anything. Taken, with a new read-only probe (`toolkit/clientscan/itemprobe.py`, which
    walks the thread-local `ItCliApi` context to the item manager and its container hash):
    **slot 0 holds our hammer, gate dword `0x22201000`, bit 25 SET.** All three branches
    pass, so the ENEMY arm returns 0 and `0x004E22D5` **adopts** our agent as a target.
    ArenaNet sets the same bit — every equipped weapon in both live captures has it, and
    the Ranger's bow is byte-identical to the hammer we send. `test_smsgnames.py` +3
    checks (floor 23 → 26) pins it, because the gate is on the side we control.
    **So four properties of the interaction have now been measured and all four are
    correct**: the target's type tag, its allegiance, its skip flag (§10.1, §10.2) and our
    own weapon (§10.4). The `m_attackInterval` assert at `AvChar.cpp(4791)` is the one
    hard observation still unexplained, and §6p — the field living on the view-layer
    `AvChar` rather than on the agent — is the only surviving lead.
    **THE METHODOLOGICAL RESULT IS THE BIGGER ONE, and it is now three for three.** §10.1,
    §10.2 and §10.4 each killed a chain that had been derived confidently from the
    disassembly and had already survived a session of reasoning. *A decision tree read out
    of the binary tells you what the client TESTS and never what the answer IS on our
    data.* Derive the chain, then probe the values. Both probes took under an hour.
    `studies/enemy/PLAN.md` §10.4.

0i. ✅ **DONE 2026-08-11. The CLIENT half of the protocol is readable, and GAME_CMSG
    goes from 7 names of 194 to 16.** Two obstacles, both now gone: the client ORs
    `0x8000` into every game-channel opcode it sends (so nothing decoded at all until
    it was masked — `codec` already took the parameter, nobody had passed it), and the
    assembled captures carry no per-message time (`cmsgstream.py` rebuilds it from the
    wire log's segment stamps). That turns a **narrated** session into a labelled run
    against ArenaNet's own server — the map transfers, both kills and both skill casts
    are all visible in the server's own messages, so client messages can be matched to
    what a human actually did.
    **THE HEADLINE IS A HOLE IN OUR SERVER.** `0x0046` USE_SKILL was named from a
    Necromancer on our own server. A whole Ranger session casting Power Shot sent
    **zero** of it: attack skills go out on **`0x0027`**, which `authsrv.py` has no
    dispatch arm for — its only mention of that number is a comment about a GAME_SMSG
    of the same number in a different channel. Every physical attack skill lands on the
    silent-ignore path. ~~and per D9(b) a schema-unknown c2s opcode discards whatever
    shared its TCP read, so it is a correctness bug. **This is the next code change.**~~
    **BOTH HALVES CORRECTED 2026-08-11.** The D9(b) clause was a mis-attribution: `0x0027`
    is schema-**known** (`GAME_CMSG_0039`), so it took D9(a)'s silent-ignore path and never
    discarded a neighbour — a missing feature, not a correctness bug (`studies/divergence`
    D9, which now records the trap). And it is **no longer the next code change**: the arm
    landed the same day — `authsrv.py:722` defines `GAME_CMSG_ATTACK_SKILL`, and one
    dispatch arm serves both halves, which §3's R4a row records.
    **12 NAMED · 6 PARTIAL · 2 that were never GAME_CMSG** — the last two were our own
    reader decoding the AUTH connection against the GAME_CMSG tables, which does not
    error, it invents. Pinned now.
    `studies/cmsg/FINDINGS.md` C14, `toolkit/authsrv/cmsgstream.py`,
    `toolkit/authsrv/test_cmsgnames.py`.

0g. 🔶 **THE FIVE NAMED MESSAGES ARE PARTLY LANDED, and the honest state matters.**
    `0x0048`, `0x00A6` and `0x0026` are wired and confirmed going out on a real
    loopback session with the client accepting them and no assert. `0x002B` is wired
    to the MOVEMENT path -- 303 of 309 in the live corpus are immediately followed by
    `0x0029`, median 574 messages from their agent's own create, so the spawn-time
    placement it shipped with for one evening was wrong on ArenaNet's own evidence --
    but it has NOT been seen to fire, because the harness's clicks land outside the
    server's 1-second position-freshness guard. `0x002E` has a tested builder and NO
    send site: nothing in our server yet knows what angle to turn an NPC to, and
    inventing a caller to tick the box is the guess this repo keeps paying for.
    **OPEN: the client asserts `!(m_flags & INTERNAL_FLAG_MOVEMENT_STALE)` at
    AgAgent.cpp:1198 as the loading screen fades.** Three causes were proposed and all
    three were refuted by experiment (`0x002B` for a tape-replay symptom, Windows sleep
    granularity, then `0x0026` -- which reproduced with it disabled). No fourth cause is
    claimed. The owner saw no crash after the `0x002B` move, which is one run and not
    proof. **The harness now captures the crash dialog itself** (`crash-dialog.txt` in
    the run directory), which is the only machine-readable evidence a client assert
    leaves -- `Gw.log` does not record asserts, no dump file is written anywhere
    findable, and a ConnectionResetError appears on clean teardowns too.

0n. **NAME THE SILENT OPCODES — 239 candidates, tooling done, needs only harness time.**
    [studies/smsgsweep/FINDINGS.md](studies/smsgsweep/FINDINGS.md) §3.4. The sweep's
    `SILENT` means *no c2s reply* and is BLIND to anything the client draws: four of four
    opcodes retested with a meaningful payload turned out to be opening windows and
    printing chat, and the operator reports visible UI throughout every earlier round too.
    So 239 rows are unread rather than empty. The conversion is mechanical and needs no
    new decoding — one opcode per run, screenshots during the hold, read the picture:

    ```
    python toolkit/authsrv/smsgsweep.py --plan --encstring --dwell 0.9 --only <opcode>
    python toolkit/harness/session.py --game-args "--probe smsgsweep --ping-seconds 0.5 --no-enemy"         --keep-open --shots 2 --hold 22
    # then read <run>/hold007.png -- the send lands ~13 s in
    ```

    `--encstring` reads a real encoded string from the owner's own captures at plan time
    (`corpus_encstring`), so string-gated opcodes get past their format check; it never
    writes ArenaNet's text into the repo. About 40 s per opcode unattended. **Deferred
    2026-08-12 at the owner's request — the harness is wanted elsewhere.** Four are done:
    `0x0033` is Message of the Day by the client's own title bar, `0x009E` is a chat line,
    `0x00B9` a framed world callout, `0x00C0` unframed floating world text.

0h. **The measured gap list, and it is the best next-actions source this project has
    had.** `toolkit/authsrv/msgmix.py`, `studies/divergence/FINDINGS.md` D12. Where our
    server sends a message at all it sends it at **3-13% of ArenaNet's rate**: we
    declare once at spawn, they update continuously. Eight NAMED opcodes we never send,
    ranked by their rate. And `0x001E` is the one we OVER-send at 1.82x, which corrects
    the naming pass's claim that we "have never sent it correctly" -- the payload was
    always a measured delta, the divergence is cadence.

0f. ✅ **DONE 2026-08-11. A second live capture, on a different character.** This was
    the naming pass's own cheapest open test and it came back clean: every invariant in
    `test_smsgnames.py` held on a Ranger where they were derived from a Necromancer,
    with nothing changed, and the checks now run pooled over both (8 tapes, 21,543
    messages). The file's shipped caveat is retired. Two structural results: the opcode
    vocabularies are **nearly identical** (146 distinct each, **148 in union**, 2 in and
    2 out), so an ordinary session's surface is stable across characters; and the
    `0x013F` bag table's (bagType, slot, capacity) triples are **byte-identical across
    characters**, which was the sharpest character-versus-protocol question in the pass
    and the answer is protocol. The session also answered 0c and named the burrow status
    values -- see there and `studies/tape/FINDINGS.md` T16.
    **T17, and it is the biggest thing this capture opened:** the **client-to-server**
    direction decodes cleanly as GAME_CMSG once bit `0x8000` is masked off (419 and 500
    messages, 0 B unconsumed both). The naming pass had already read that bit out of the
    binary -- `MsgConn`'s send computes `((conn+0x54) ? 0x8000 : 0) | msg[0]` -- without
    connecting it to decoding this side. So both captures are **labelled runs against
    ArenaNet's own server**, with a narrated session, which is what `labelrun.py` does on
    ours. 194 GAME_CMSG opcodes have layouts and seven have names.

0e. ✅ **DONE 2026-08-10. Twenty GAME_SMSG opcodes named — the catalog goes from 1 of
    487 to 21.** This is the item that was not on the list, and it is where the leverage
    turned out to be: §8.0's four items were all written from one session's leftovers,
    while the four live tapes were a **10,944-message behavioural corpus that nothing in
    this plan was mining**. Framed and counted: **146 distinct GAME_SMSG opcodes**, of
    which the top 30 are **92%** of the stream, and exactly one had a name.
    **Method** — two witnesses neither of which was consulted to produce the other: the
    client's dispatch handlers plus its **19,620 compiled assert expressions**, against
    the wire. Every proposal was then handed to a second reader told to refute it, and
    that pass earned its cost: it struck four headline citations and two verdicts, and
    caught a **fabricated quote** (an agent reported the client's log string as
    `item name=%s` and built an argument on the `%s`; it is `%d`).
    **The headline result.** `0x001E` is **36.3% of all server traffic** — more than the
    next five opcodes combined — and is *not* a heartbeat. Its payload is elapsed
    milliseconds: summing it across a tape reconstructs that tape's own wall clock to
    **−1.2 ms over 48 s and +18 ms worst case**, and the client names the field twice
    (`message.time` at AgMsg.cpp:208, `elapsedMs` at AgTimer.cpp:32). We send it on a
    fixed 0.05 s sleep, which is our single largest divergence from ArenaNet's traffic.
    **Three upstream/incumbent glosses refuted**, all of which had cost us something:
    `0x002E` as `cos, sin` (sin²+cos² over the corpus ranges 1.23–4.87 and is never 1 —
    this is why `0x002E` went unsent for weeks), `0x002B` as a `SpeedModifier` (the
    client asserts the field into [0.01, 1.0], so no buff can ride it), and
    `0x00F0`/`0x00F1` as *effects* (the client's word is `m_status`; the "effects" noun
    is traceable to OpenTyria's struct member — one witness, and not the client).
    **Landed:** `schema/overrides.json` +20 entries each carrying a `name_confidence`
    that is the POST-refutation value; `studies/smsg/FINDINGS.md`;
    `toolkit/authsrv/test_smsgnames.py` (21 invariants ArenaNet's own traffic could have
    violated, mutation-tested — a constant tick payload drifts 155 s and is rejected).
    **10 came back PARTIAL and are deliberately NOT named**, with what would settle each.
    **The number to distrust: 0 UNRESOLVED of 30.** Recorded in the findings as a warning
    rather than a triumph — the 30 were chosen by corpus frequency, and frequent messages
    have the most wire evidence and the most reachable handlers. It does not extrapolate
    to the other 116 corpus opcodes, let alone the 341 that never appeared.
    **The cheapest open test in the whole pass: a second live capture on a different
    character.** Every count rests on four tapes of ONE session, one character, one
    account — "4/4 tapes" is four samples sharing a character record — and one decode
    separates protocol from character.

The items below this section predate today and are still live; these four are what today's
work opened. **The order has changed since they were written**, on evidence: four scouts
read one item each and a fifth was told to refute them, and it broke a headline claim in
three of the four. 0d turned out to be finished rather than open and is done. 0c is bigger
than the sentence below used to claim and is where the new information is. **0a should not
be run as written** — its premise, that a labelled run on our own server would newly show a
completed action, rests on an experiment the repo has already run twelve times with a null
result (`authsrv.py:831-841` records it as NOT FOUND), and the measurement that seemed to
support it was taken off the client's VERSION frame, which is declared *before* `--map` is
applied and is therefore blind to every `--map` run. 0b is independent and can go in
parallel, with one safety change that is not optional — see its entry.

0a. **A labelled run against our OWN server — RE-SPECIFIED, do not run as written.** The
    premise stands (a tape never replies, so nothing yet shows a *completed* action —
    `studies/tape/FINDINGS.md` T6) but the proposed experiment does not. It was going to
    test whether the client sends `0x0026` ATTACK on our server in an explorable rather
    than a town; `authsrv.py:831-841` already records that as tested and **NOT FOUND**,
    "in an outpost or an explorable", and the twelve map-146 sessions of 2026-08-06 sent
    `0x0033` 48 times and `0x0026` zero. What replaces it is sharper and came out of 0c's
    reading: **all seven c2s `0x0026` in the entire vault target agent ids 274, 275, 276
    and 284 — Plague Worms.** The client aims `0x0026` at agents *ArenaNet* created and
    `0x0033` at ours, in the same map type. So the axis is something in the create burst,
    not explorability, and 0c is the item holding that evidence. Run 0a *after* 0c has
    changed what our create burst looks like, and fold it into the same operator session —
    0c needs a hand-driven loopback run of its own. The merchant reply is still worth
    doing and is **not** "cheap": it is a session, and it may fail for the same unknown
    reason `0x0026` does.

0b. 🔶 **BUILT 2026-08-10, awaiting one operator run.** `0x01A5` is now
    `GAME_SERVER_TRANSFER` — the **first named `GAME_SMSG` opcode** of 487 — because it
    carries the next instance's `world_id`, `map_id` and `player_id` as well as its
    `sockaddr_in`, and all four match the next connection's own c2s VERSION frame, 12/12
    across three transitions (T9). **Landed:** `tape.chain()`, which discovers the chain
    and **refuses a link it cannot prove** rather than ordering hops by timestamp;
    `tape.transfer_of()` / `rewrite_transfer()`, length-preserving at **4 bytes of
    74,319** so `load_tape`'s accounting is untouched and the tape still frames 100%
    clean; `authsrv --tape-rewrite-next`; and `session.py --tape-chain`, which starts one
    gamesrv per hop on its own 127.x alias — hops **cannot** be separated by port, and
    every recorded hop changed address, so an alias each also keeps the run to one
    variable. The measured chain is 4 tapes / 3 links, 184,756 B, **396 s** of ArenaNet
    plaintext: 148 → 146 → 164 → 146.
    **The safety trade is the point, not a footnote.** The rewrite deletes the only
    control that has ever caught this: an un-truncated tape used to fail **closed** —
    client dials ArenaNet, cage refuses, `Code=005` — and afterwards a wrong address is a
    dead connection with no signal. So `rewrite_transfer` refuses any host outside 127/8
    and self-checks offline before the client runs; that refusal *is* the replacement,
    and `test_tape.py` breaks it on purpose to prove it can go red.
    **First run, 2026-08-10: two hops played end to end and the third did not dial** —
    1209/1209 then 780/780, then nothing (T10). The client was healthy: right map on its
    loading screen, right alias in its overlay, auth still heartbeating, no assert, and
    **no SYN at all**. Cause, OBSERVED from the binary: handler `0x0084f290` branches on
    bit `0x20` at `+0x190` — clear dials immediately, set stashes and defers — and the
    connect function `0x850df0` **sets that bit itself** (`0x00850e56`). So exactly one
    game-channel transfer per session dials at once and every later one waits for the
    connection it already holds to go away. ArenaNet's server hangs up 0.12–0.14 s after
    every handoff; ours sat on the socket. `close_after_transfer` fixes that, keyed on the
    tape's contents so a last hop or `--tape-no-transfer` run is never hung up on.
    **SETTLED 2026-08-10 by a discriminating run: exactly ONE game-channel transfer per
    session dials** (T14). `--tape-chain-from 62994` made the failing Lakeside -> Ashford
    transition the FIRST one and it worked, 118/118, with Ashford rendering; the NEXT
    transfer then stalled. Same transition, opposite outcome, decided by its ordinal --
    so it is not the map, the tape, the address or the shutdown. Three fixes aimed at the
    close were all correct-and-irrelevant. **And the mechanism is now read out whole (T15):**
    `0x00851380` has no callers because it is a **switch case**. The function at
    `0x00851340` dispatches on an event **type** and handles exactly three —
    `0x1D` and `0x1E` both **dial**, and `0x1E` is also the only thing that clears bit
    `0x20`; `0x1F` tears the instance down and **never dials**. A peer that merely goes
    away raises `0x1F`, which is what our close produces however politely, so no shutdown
    fix could ever have worked. **The open question is whether a server can provoke `0x1E`
    at all** — those events come from the client's own connection layer, not from any
    message. If it cannot, chaining past one hop needs a lever other than a tape, and
    R1.5's chained form should be re-scoped rather than retried.
    **Superseded:** *Re-run 2026-08-10: the hang-up was necessary but NOT sufficient* — same two hops,
    same stop. What releases a deferred transfer is a *player-state* transition, not a
    socket close: the consumer at `0x00851402` clears the pending bit and dials, and it
    lives in a handler asserting `!(context->playerFlags & PLAYER_FLAG_CONNECTED)` at
    `MsCliGame.cpp:76` (T11). Two dead ends ruled out cheaply and recorded: all four tapes
    declare the **same** `map_file_id` 113021, so it is not map content; and the auth
    channel carries only two `GAME_SERVER_INFO` in the whole session, both before the
    first hop, so it is not an auth handoff. Both flag-clears turn out to be
    the tail of one nine-call instance teardown with two routes in (T12): `GAME_SMSG
    0x01B1`'s handler, and the network layer's own disconnect event, which branches on a
    **reason code**. `0x01B1` is ruled out — it appears **zero times in all four tapes**
    while the real client transferred three times, so the live route is the reason code.
    **Next, and it is offline:** what reason code our close produces versus ArenaNet's,
    and whether the client distinguishes a server FIN from a reset.
    **Not landed:** a full four-hop run. ~6.6 minutes during which the operator does
    nothing, and each hop's avatar stops moving well before its tape ends — the
    `tape complete: N/N` line is the only truthful signal. **UNVERIFIED:** whether the client honours the port
    in a *game*-channel handoff. The "it dials 6112 regardless" observation is of the
    **auth** channel; every recorded `0x01A5` advertises 6112, which is also the
    hardcoded value, so the capture cannot separate them. `--tape-rewrite-next host:port`
    exists so one run settles it. The `world_id`/`player_id` values stay in the vault —
    `schema/` records the structure and the fact of the match, never the identifiers.

0c. ✅ **RUN 2026-08-11, and it confirmed the inference AND refuted its own side prediction.** The probe removed our Hatcher and re-created it twice with **no `0x0056`/`0x0057`** — once at the same id, once at a fresh one — and **both drew a correct collector**. That is what the live-capture inference below could not reach: ArenaNet's 1-to-140 proved THEIR client keeps a definition, not that OUR create path is right without one. `burrow_tick` now passes `send_definition=False`, and `test_burrow.py`'s check flipped with it — it had asserted the resend and named this probe as what would settle it. **The refuted half: `0x1000` is an ANIMATION.** The probe's honest expectation was that nothing visible would happen; set the bit and the agent falls prone, clear it and it gets up, staying rendered and nameplated the whole time. The bit animates, the removal hides — which is why ArenaNet needs both. `studies/enemy/PLAN.md` §10.8. **Prior reasoning follows.**

    ✅ **ANSWERED 2026-08-11 by the second live capture, and not by the probe built
    for it.** The blocking question was whether the client keeps an NPC definition
    across a removal, since `agent_removal` resent it every time and so its positive
    said nothing. ArenaNet's own traffic settles it: **1 `0x0056` declaration, 32
    creates** for the Lakeside worm in capture `20260810T235916`, and 1 declaration to
    **140** creates pooled across both captures. It is the *same client* on both ends,
    so the client keeps the definition -- otherwise 31 of those 32 creates would name a
    slot it no longer holds and it would go down on `Array.h`'s `index < m_count`. A
    server may declare once and re-create freely. `probes.py`'s `burrow` probe is now
    confirmatory rather than necessary; what it still uniquely tests is whether OUR
    create path is right once it stops resending. **And the burrow status values are
    named** (T16): `0x00F1` status `0x1000` is burrowed, `0x0000` is surfaced, the two
    2.00 s windows are create->surface and burrow->remove, and **death is not a burrow**
    -- a kill sets `0x0010` while the agent is surfaced and never removes it.
    Original entry follows.
    🔶 **BUILT 2026-08-10, awaiting one operator run.** Plague Worms hide by being REMOVED
    and re-CREATED under the same agent id (T3). ~~It runs entirely through
    `0x0020`/`0x0021`, both already implemented~~ — **that was wrong and is REFUTED
    151/151**: every worm re-creation in both Lakeside tapes is a fixed five-message burst
    `0x009F`, `0x00F0`, `0x0020`, `0x006D`, `0x0026`, and the visible phase carries two
    `0x00F1` writes at exactly 2.00 s from each edge (n=132 each, all inside ±60 ms). Six
    opcodes, not two, and `0x00F0` is D2 — the highest-count message our server has never
    sent. The ceiling was understated too: 23 cycles, not 19.
    **Landed:** `EFFECT_TRANSITION` and the `0x00F0` constant; `create_agent_world`, the
    guarded create that finally makes the world model symmetric (`remove_agent` refused a
    double-remove while the create side was a bare dict assignment — a re-create that
    forgot the state write would have raised inside the world-tick daemon thread and
    stopped the world for the session); `state["hidden"]`, the first place an agent can
    exist while not being in the world; `burrow_tick` as the third tick sweep; a content
    flag defaulting off; and `test_burrow.py`, which re-measures ArenaNet's burst from the
    capture rather than trusting the study doc that was wrong.
    **Not landed, and it is the whole reason this is 🔶:** ArenaNet sends the NPC
    definition ONCE for 140 creates, so their client keeps it across a removal. Ours has
    never been asked — `agent_removal` resent the definition every single time, so its
    positive says nothing here. The server therefore resends, which is the side whose
    failure mode is not a client assert. `probes.py`'s new `burrow` probe settles it with
    a same-id/fresh-id control; **UNRUN**. Three of the burst's five messages
    (`0x009F` property 66, `0x006D`'s item id, `0x0026`'s tail byte) are deliberately NOT
    sent by the server — their values are unknown and filling them with guesses is what
    made the first `agent_removal` run's negative meaningless.

0d. ✅ **DONE 2026-08-10. `0x0040` is `ROTATE_PLAYER`** — field 1 an angle in radians,
    field 2 a normalised turn amount in (0,1]. Settled by the **binary**, not by a run:
    the client's own assert `(rotation >= -1.0f) && (rotation <= 1.0f)`
    (`ChCliApi.cpp:5562`), reached from the only one of 174 send sites that carries this
    opcode; the ±inf is a sentinel loaded from two `.rdata` constants, which is the fact
    that kills the "±inf rules out an angle" inference that had held the name back. 559
    wire samples agree — every finite value inside ±π, 13 matching `atan2` of a nearby
    `0x003D` direction to float32 round-off against a shuffled null of 5.
    `schema/overrides.json`, [studies/cmsg/FINDINGS.md](studies/cmsg/FINDINGS.md) C13,
    `toolkit/authsrv/test_rotate.py`. **The wire typing stays `u32`** — the values are
    floats, the marshalling is not, and C6's "the schema types them as dwords" read as a
    bug report for three days while being the correct behaviour.

1. **Build the capture harness (A1).** ✅ **DONE 2026-08-07. R0b is met, R1.5 is met, and
   nothing is blocked behind either of them.** The vault holds **three keyed live captures**
   — `20260807T133758`, `20260807T143055`, `20260810T235916` — decoding to **22,524 GAME_SMSG
   over twelve connections, 398,945 B, 758.0 s, 155 distinct opcodes, twelve of twelve framing
   to `consumed == total` with `err is None`**, plus 971 GAME_CMSG. See §3's R0b and R1.5 rows,
   §3.3–§3.5, and [studies/reconstruction/FINDINGS.md](studies/reconstruction/FINDINGS.md) §1
   for the corpus measured end to end.
   *This item's lead sentence read* "Every capture in the vault is Rurik talking to Rurik;
   **not one byte is ArenaNet's**, so R0b is unmet and R1.5 and R4c's original criterion are
   both blocked behind it" *until 2026-08-11 — every clause of it false since 2026-08-07, and
   contradicted by its own body eight lines later and by §3's two ✅ rows.* The body was
   rewritten as the work landed and the lead sentence was not, so a cold session reading §8
   first — which `CLAUDE.md` calls the live next-actions list — was told the project's central
   instrument does not exist. **That is the exact failure §3's header exists to prevent,
   arriving in the one document that is supposed to be immune.** Recorded rather than quietly
   deleted, because the fix for it is a habit and not an edit.
   **Done:** the live-capture build exists, the launch gate binds a binary to a target
   (§6.2 preconditions, all met), and the **decryption engine is built and proven** —
   `toolkit/authsrv/replay.py` reads a `.raw` back and decrypts it offline, 329 captures
   reproduced exactly (which also closed R0a's caveat, §3.1). The route is **decided**
   (owner, 2026-08-07): **patch the real client to log its own session key**, capture the
   ciphertext **off the wire** (route C, a scoped packet-capture carve-out), decrypt with
   `replay.py`. The headless-client route is rejected —
   its client→server bytes are our reconstruction, not ArenaNet's, and both directions are
   needed. See [studies/livekey/FINDINGS.md](studies/livekey/FINDINGS.md),
   [CAPTURE.md](studies/livekey/CAPTURE.md), [CODECAVE.md](studies/livekey/CODECAVE.md).
   **Done, the load-bearing part:** the key material is located (`master_secret` at
   `0x007DC0CE`, `MsgConn.cpp`), the key-tap code cave is implemented
   (`make_custom_client.py --key-tap`, `keytap_patch.py`), the reader is written
   (`keytap.py`), and the whole path is **verified on a live loopback client** — the cave
   ran during a real handshake without crashing, and `keytap.py` read the exact
   `master_secret` our server independently derived (2026-08-07, `verify_keytap.py`). Key
   acquisition is proven with zero trust in the live service.
   **Also done 2026-08-07:** the off-wire ciphertext capture (`wirecapture.py`, WinDivert
   SNIFF, pure half tested) and the driver that ties it all together (`livesession.py`:
   account + launch gate + key-tap + capture + decrypt + `origin: live` + scrub + the
   behavioural guards). The driver's **offline assembly is proven on real bytes** — split
   the plaintext handshake off a wire stream and decrypt the rest, reproducing the server's
   logged plaintext *reached from the wire side*, both directions, self-consistent.
   **Proven end to end on loopback 2026-08-07** — `dryrun_keycapture.py`, run elevated,
   came back GREEN: WinDivert **does** capture loopback here (the one real unknown), the
   off-wire ciphertext matched the server's own `.raw` **byte for byte** (62/62), the
   tapped `master_secret` equalled what the server derived, and the capture decrypted to
   the server's logged plaintext. The whole pipeline works against a key we hold, with an
   oracle for every byte.
   **Done 2026-08-07, the last of the code:** `livesession.run` is wired — it starts the
   sniff, launches the stock-DH build at ArenaNet's own endpoints through the launch gate,
   polls a keyring off the tap, holds to a ceiling under the operator's hand, then
   assembles per connection and scrubs. It deliberately sends **no** scripted input: the
   loopback harness's three-Enters-and-a-Play-click is exactly the traffic pattern §6.1
   says closes accounts. The stock-DH live build is key-tapped and staged.
   **The first live run happened 2026-08-07** (`vault/captures/live/20260807T124912`). It
   worked, and it taught three things no loopback session could:

   * **The VERSION message has two shapes.** Auth is header `0x000C0400` + 12-byte body;
     the game channel is `0x000C0500` + **60**, so CLIENT_SEED sits at offset 64 rather
     than 16. **OBSERVED**: `00 42` occurs exactly once in the first 200 bytes of all seven
     streams — at 16 for the auth connection, 64 for all six game ones. Our server only
     ever speaks the auth shape, so nothing on loopback could have shown it, and the first
     run split 1 of 7 connections because of it. Now handled, and an unknown third header
     still stops the reader rather than being guessed past. *(The 60-byte body reads as
     build/1/id/n/n + two 16-byte uuid-shaped fields + 8 zero bytes; the second uuid is
     identical across five connections and ZERO in the earliest — the one opened before
     the new character existed. That reading is **RECONSTRUCTION**; only the offsets are
     OBSERVED, and only the offsets are what the code depends on.)*
   * **The keyring must reach disk as it is tapped, not at the end.** Seven keys were
     tapped and one was written — by the single connection that happened to assemble — so
     six channels of real, gap-free ArenaNet ciphertext became **permanently
     undecryptable** when the process exited. There is no recovering them: the key derives
     from ArenaNet's private exponent. Fixed: `keyring.jsonl`, written and flushed per key,
     plus `--assemble DIR` to decode a capture again from its own two files. That is what
     R0b's "byte-replayable from disk" actually requires, and the first run did not have it.
   * **The updater kill switch is wrong on the live build.** `DnSetEnabled` gates the
     whole download path, so a client that cannot patch also cannot **stream map
     content**. The second live run died entering Pre-Searing: `Map file '0x01b97d'
     failed to load. Attempting to re-bloat.` then `Assertion: found, Map.cpp(1762)`.
     MEASURED: the map is present in both `Gw.dat` copies and reads identically, so it is
     the fetch that failed, not the archive. Owner's decision 2026-08-07: the live build
     is now built `--no-updater-patch`. The concern that justified the launch gate's
     refusal — an update mid-capture replacing the build the frames came from, "and after
     the fact nothing says which build produced which frames" — is answered by a
     measurement instead: `livesession` hashes the exe before and after every run and
     records both in the manifest. The loopback build keeps the kill switch.
   * **The key-acceptance criterion was too narrow, and it was wrong in the expensive
     direction.** It matched literal opcodes (`0x8001` auth, `0x808a` game) taken from our
     own server's flow; the real service's game channels opened `0x800a` and `0x8091`, so
     two connections whose keys we were HOLDING were reported undecryptable. Replaced with
     a structural test — **MEASURED over 534 captures**: bit 15 of the first client u16 is
     a direction flag (set in 400 of 409 c2s, never in s2c; the nine are the 08-04
     synthetic markers), and stripping it puts every observed value inside
     `schema/messages.json`'s own `0x0000-0x01E6` range. So a key is accepted when the
     direction bit is set and the opcode is one the catalog could hold — 487 of 65536
     values, still a check that can fail. On the live capture it picks exactly one key per
     connection, correct every time. The **channel** now comes from the VERSION header,
     which is the field that carries it.
   * **`payload` is a second field the scrub cannot clean.** The DH handshake crosses the
     wire in the clear, so `a` and `sent` sit as hex inside `wire.jsonl` two records before
     the fields where the scrub redacts them. `test_scrub`'s leak check found both the
     first time a live capture entered the corpus — the check working, not failing.

   **R0b landed on the fifth run, 2026-08-07 14:30** (`vault/captures/live/20260807T143055`,
   §3 and §3.3). Runs three and four recorded ZERO bytes each and the cause was one thing:
   **the client's channels were on port 80**, not 6112. `LIVE_PORTS` now spans GW's whole
   known range plus 80, and `prune_wire` drops the non-GW connections that width lets in.
   Nothing about the crypto, the keys or the driver was wrong — the filter was pointed
   somewhere the traffic was not, and for two runs nothing could say so. What found it was
   an instrument, not an argument: the driver now samples the client's own connections and
   the capture reports per-stage counters, so run four named `52.3.40.244:80` sixty seconds
   in. Every lesson in this item cost a session that could have been spent capturing.
   *Two defects the wiring turned up, both in the controls rather than the pipeline.* The
   sniff could be pinned to one address by a documented flag, which silently discarded the
   game channel while reporting success (§6.2). And **`scrub_captures.py` cannot clean a
   `plain` frame payload** — it matches JSON keys, and the auth channel's first client
   message carries the account email as UTF-16 *inside* that hex blob, so the scrub walked
   past it and the leak check stayed green because it searches ASCII. Redacting the blob
   would delete the capture, so the scrub now reports it: a count, the file list, and a
   `WARNING` in `SCRUB-MANIFEST.json` saying the tree is not shareable. This is retroactive
   — **MEASURED 2026-08-07: 401 of the vault's 517 existing captures** carry a `plain`
   payload, and `captures-scrubbed/` is the tree RUNBOOK names as the one that may leave
   the machine.
   *The s2c-ordering hazard this item used to raise is closed:* the keystream `seq` work
   (`b70920e`) numbers each send inside the send lock, so a capture sorts back to true wire
   order regardless of thread contention.
2. **Spec the row format before the sniffer.** The half nobody owns: even with tape, nothing
   turns a capture into a content row. `content/*.toml` now gives that output a shape, so the
   job is a capture→row compiler, not a parser. **SOURCED:** this is the difference between
   WowPacketParser and a packet logger, and TrinityCore's whole 3.3.5a world database exists
   because that pipeline ran while retail was on 3.3.5a. Target the first monster row, not a
   complete zone.
3. **Finish R4a.** Nothing swings back. The player cannot die. The agent table
   `studies/enemy/PLAN.md` §7.2 asks for is the prerequisite, and it should read its NPCs from
   `content/npcs.toml` rather than minting constants.
4. **Enumerate Pre-Searing** — [studies/presearing/MANIFEST.md](studies/presearing/MANIFEST.md).
   It is what makes R4b and R4c countable (§3.2). Keep it current as content rows land.
5. **Build OpenTyria** (`vault/mirrors/ldufr__OpenTyria`) and connect a *patched copy* of the
   client. Never patch `C:\gw`. Fastest route to understanding the whole stack end to end.
   *Note: its value has dropped — the assumption it was hedging (that R1–R3 would be research)
   was tested and did not hold. See §7 Q1.*
6. **Read `gw-preservation/server`'s pathing and instance definitions** — 397 maps and a real
   `Gw.dat` navmesh. Read only: no licence means all rights reserved, and `toolkit/content.py`
   now refuses a row citing them that does not record what we verified it against.
7. **Run Probe 3** (`vault/mirrors/shiburito__gw_in_browser`) for offline WASM analysis only —
   not for live capture, per §1.3. It is the only thing gating §7 Q2, which has been open since
   the plan was written; give it a date and a default answer of "no" if it does not run by then.
8. **The C# server core.** *Contested, and open.* This item used to read "install a .NET SDK if
   the C# server core survives Q1/Q2". Since then ~18,000 lines of working server have been
   written in Python, `CLAUDE.md` binds `toolkit/` to the standard library, and the 2026-08-06
   review measured the transport at ~7,000 encode+encrypt messages per 50 ms tick against an R4
   budget near 60 — so performance was never the constraint. The review's recommendation is to
   strike this item and record a closed decision. **That is the owner's call and it has not been
   made**; until it is, no new server code should presume either answer.
9. **Re-run `toolkit/mirror_priorart.py`** monthly. Repos in this ecosystem vanish; one already
   has.
10. **Custom areas, after R5m** ([studies/customarea/FINDINGS.md](studies/customarea/FINDINGS.md)).
    In the order they are worth doing:
    **(a)** Split E1's result — it shrank the boundary polygon, the trapezoid and the DAG
    together, so which one the client reads is open. Two more 33-byte edits settle it.
    **(b)** ✅ **Two trapezoids DONE** (§27, ArenaNet's own two-trapezoid plane walked in
    front of a client; §28 settled the DAG semantics at 0.999935 over 3.6M queries).
    **The portal is BLOCKED, and §30 says on what.** Tag 12 `plane_map` is a per-plane
    PROP INDEX: every plane above 0 is mounted on a prop, so a two-plane map needs chunk
    `0x20000004` with `propCount > max(plane_map[1:])`. We shipped `[0, 0]` into a
    props-less map and crashed a client twice. `gates()` now refuses that shape.
    **Newly unblocked by `studies/monsterai` §3.10.1** (2026-08-11, the other session):
    the Props chunk is opened — the prop array is read, `read_props()` exists in
    `test_mapexport.py`, and 346/346 maps validate. The remaining 67.42% of the chunk is
    a `{u8 tag, u32 size}` record list that closes 349/349 with its meaning NOT FOUND, so
    the route is to CARRY a props chunk read from the archive at run time — the pattern
    `mapbuild` already uses for FINDINGS 14's five constants — rather than author one.
    Its control is named in §30: change tag 12 entry 1 to exactly `propCount`, one past
    the end, and it must still crash, or a green run means nothing.
    **Do not "fix" it by collapsing to one plane** — zplane is then permanently 0, the
    short-circuit at `0x0070A433` fires, and the assert is unreachable by construction.
    **(c)** A height field that is not flat, walked — E1's terrain was flat, so nothing
    tested slope, step height or the z the client places a character at.
    **(f)** ✅ **DONE 2026-08-12.** The Blender importer was upside down and is not
    any more: `import_gwmap.py` negates z, `test_blenderimport`'s prop oracle negates
    the prop too, and the score is INVARIANT under that -- |-a - -b| == |a - b| -- so
    0.7338 and its 0.0775/0.1389 controls came back bit-identical rather than being
    re-measured. `mesh_z` is now the one place stating the sign, with a check against
    LITERALS beside it, because every other z prediction is computed through it and
    would move with it. Sabotaging `mesh_z` to the identity reddens 10 checks.
    **(d)** ✅ **DONE 2026-08-12 (FINDINGS 32).** `tools/blender/export_gwmap.py` is the
    way out, and `test_blenderroundtrip.py` (77 checks, floor 77, ~39 s) is the claim:
    an interchange imported, saved to a `.blend`, and exported by a SEPARATE Blender
    process — two processes, because a round trip inside one scene proves the functions
    are inverses and nothing about the file. Pre-Searing's **212,992 heights, tiles and
    shade bytes all come back byte-identical**. That headline is the WEAK half and was
    measured to be: a memcpy sabotage keeps all six byte-identity checks green,
    including the retail ones, and is caught only by section 2's SCULPT — one vertex
    moved in Blender by a literal +250.0, requiring exactly that cell to move by exactly
    −250.0. Three refusals for things a height field cannot express, the two
    displacement bands covered by two different checks (a sabotage deleting the residual
    leaves the 40-unit case green). Section 4 authors a mesh from NOTHING and `mapbuild`
    turns it into a map file passing all 17 open-time gates.
    **NOT CLOSED BY THIS:** the round trip is terrain only. Props, zones, water and the
    navmesh do not go through Blender, so an author edits the height field and nothing
    else — and the pathing mesh, which is what the client actually collides against
    (§23, §24), still has to be authored by hand.
    **(g)** CLOSED as a cosmetic artefact (FINDINGS 26): the rendering fault is
    reproducible, recovers, and happens only where the camera can get out over
    empty space -- which no playable map shape allows. On the map as designed the
    operator calls the camera stock. Our test maps carry none of the ten chunk
    kinds that would draw a sky, so there is nothing to see out there. Reopen only
    with a map that has an Environment chunk.
    **(e)** E3 (provoking the client's own map compiler) is weakened but not dead — arm 3b
    showed a corrupt Bloated chunk crashes rather than re-bloating, so the zero-length
    stream-1 payload of §17.1 is the cheapest remaining probe.
    **(e1)** ✅ **DONE 2026-08-12 (FINDINGS 33).** The compiler's INPUT side is now
    readable and authorable: `pathchunk.StrippedPath` decodes and encodes chunk
    `0x10000008`, **349/349 byte-identical** and **349/349 exactly `19 + 8n` bytes**.
    Nothing in the tree could read it before, so §17.2's contract rested on one
    unreproducible sweep. Its framing is NOT the Bloated chunk's despite a shared
    signature — 9-byte header with a `u8` version, unsized records — and each codec now
    refuses the other's bytes.
    **(e2)** ⚠️ **E3's INPUT CONTRACT IS WRONG AND MUST BE RESPECIFIED BEFORE IT RUNS.**
    §17.2 reads the boundary polygon as what the compiler turns into a navmesh. MEASURED:
    the Stripped boundary is identical to the Bloated one, point for point, in **349 of
    349** maps — it is *carried*, not consumed — and **28 maps ship a boundary of ≤2
    points**. File id `0x9F5E`'s entire Stripped pathing chunk is **27 bytes holding one
    point**, and its Bloated partner has **3,437 trapezoids**. So tag 7 is not the mesh
    input, and E3's "fewest authored bytes" economy conflated *this chunk is tiny* with
    *the input is tiny*. The trigger is still cheap; the input is a whole Stripped map
    (~900 KB for Pre-Searing). Likely source is terrain + collision — `PathFlood.cpp` is
    on the builder's closure and a flood fill is a terrain operation.
    **(e3)** ✅ **DONE 2026-08-12 (FINDINGS 34).** The compiler's input set is read off the
    client's own instructions. The Path builder reads **no chunk by id** — it reads the
    already-bloated in-memory objects out of a 0x34-byte converter-local (`state`), and
    **terrain and props are HARD GATES**: `0x00712671` and `0x00712678` are unguarded `je`s
    to `return 0`, so with either object null the Path chunk is not built at all. All four
    object writes verified by direct disassembly (`state+0x24` props, `+0x28` zones,
    `+0x2C` terrain, `+0x30` collision). **The flood grid IS the terrain lattice** — one
    cell per terrain cell, ±96.0 quad corners, the same pitch `test_terrain.py` pins from
    the file side — so the compiler would flood OUR terrain, which is the mechanism §32
    needs. The seven-stage pipeline at `0xBF72F0` also settles §33 mechanically: tag 7 is
    copied through by pass 1, the mesh is built by pass 2, which never touches it.
    **(e4)** ✅ **ANSWERED YES, 2026-08-12 (FINDINGS 35). THE CLIENT COMPILES.** Map 143's
    Bloated stream was zeroed on a copy; the retail client logged
    `Map file '0x0287d3' failed to load.  Attempting to re-bloat.`, compiled the navmesh
    from the Stripped partner, and wrote it back — **byte-identical to what ArenaNet
    shipped**, 9,284 B stored and 33,021 B decompressed, sha-identical in both forms, 27
    trapezoids over 1 plane. The driver is `toolkit/mapdata/rebloat.py`
    (`--plan/--arm/--verify`, refusing `C:\gw` and `vault/dat_study`), with
    `toolkit/mapdata/test_rebloat.py` (28 checks, floor 28) covering everything about it
    that can be judged without a client, and `RUNBOOK.md` §"Rung E3" as the procedure.
    The row relocated `0x63C64200` → `0x4B82E00` exactly as
    predicted from the released reservation, and `verify` re-resolving by file id is what
    made that a non-event. The arm demonstrably applied — the journal shows compression
    8 → 0 and the rebuilt row carries 8 again, so the client rewrote it wholesale.
    **And it corroborates FINDINGS 17.1's INFERRED claim** that retail's Bloated streams
    are locally generated at download time: a compiler reproducing a shipped payload to
    the bit is what you see when the shipped payload came out of that compiler. So every
    retail Bloated map in the archive is an output of the compiler we want to borrow.
    **E3 is alive and the route works.**
    **(e5)** ✅ **DONE 2026-08-12 (FINDINGS 36). THE COMPILER BUILDS FROM THE STREAM WE
    SUPPLY.** §35 left an alternative reading open — the client might have restored map
    143 from a cache or a download keyed to the file id. So map 143's Stripped partner
    (row 71497) was replaced with **row 46197's** stream, a different map entirely, and
    its Bloated stream zeroed. **PREDICTION recorded before the run: 2 trapezoids, not
    27.** The client rebuilt `0x287D3` as **8,471 B, 18 chunks, 2 trapezoids over 1
    plane** — byte-identical to the DONOR's shipped map (`4178b052…`) and not to map
    143's (`acfc8e75…`). So the compiler's input is the bytes in stream 0 and nothing
    else. **Author a Stripped stream → the retail client builds the Bloated map, navmesh
    included.**
    **(e6)** ✅ **DONE 2026-08-12 (FINDINGS 37). THE STRIPPED TERRAIN CODEC EXISTS**, so
    the gap between §36 and §32's Blender pipeline is closed on paper.
    `toolkit/mapdata/strippedterrain.py` decodes and encodes `0x10000002`;
    `toolkit/mapdata/test_strippedterrain.py` (floor 66, 57 vault-less) covers it.
    **The headline is deliberately not the round trip.** The height field the codec
    pulls out of a canonical-Huffman bit stream and a 4x4 integer transform EQUALS,
    sample for sample, the one `terrain.py` reads out of the Bloated chunk — a different
    encoding, written by a different subsystem, that the codec never looks at. The
    byte-identical re-encode is reported beside it as the weaker claim, because a memcpy
    passes it; the test BUILDS that saboteur and requires it to pass the round trip and
    fail the mutation checks.
    Read out of the eleven-stage pipeline at **0x00A74958** (`TrnDataBloat.cpp:730/731`),
    the bit reader at `TrnBitStore.h`, and the codec at `TrnCodecHeight.cpp`. Three
    things came out of it that were not the point:
    **(i) tag 9 is BAKED, not stored** — stage 7 reads nothing from the cursor and
    generates the lightmap from tag 0's sun elevation, which is what FINDINGS 19's
    0.887 Pearson fit was measuring;
    **(ii) `terrain.py`'s 1-ULP angle caveat is retired** — the client computes
    `float32(b * 282.74334716796875 / 45720.0)` in double, and the two formulations that
    file preferred differ from it at 88 and 3 of 256 indices;
    **(iii) the Stripped header is FIVE bytes, not eight** — `terrain.py`'s docstring
    read the version as a `u16` and called tag 0's first two body bytes a field.
    **What is NOT done and is the next experiment**: nothing this codec authored has
    been through the client. Also unknown: whether an authored terrain/props pair bloats
    to objects the builder ACCEPTS ("non-null" is not "usable"), and what sets the
    walkability mode that picks 10/45/40° over 15/35/30°.
    **A real constraint fell out, and it is small**: the transform's matrix has
    determinant 8, so an authored height field must be snapped onto a sublattice.
    MEASURED worst move **4 world units** against a 96.0 cell pitch.
    **(e7)** ✅ **DONE 2026-08-12 (FINDINGS 38). THE CLIENT COMPILED A NAVMESH OVER
    GROUND WE AUTHORED**, and the ladder E3 was built for is complete. A height field
    written by `strippedterrain.py` — never in any archive, exactly on the transform's
    lattice — went into a map's Stripped stream with its Bloated stream zeroed, and the
    rebuilt mesh **stops at world x = 1152.0, the cell boundary we chose, to the unit**.
    Walkable area in the sawtoothed strip fell from the control's 37.3% to **0**, and
    the surviving 5,898,240 is exactly the control's other half. **The trapezoid COUNT
    did not change** (2 → 2, 419 B → 419 B), so the geometry is the whole finding and a
    count comparison would have read it as nothing happening — which is what
    `rebloat.py --verify` prints, and is worth remembering about §35 and §36 too.
    **(e8)** ⬜ Nothing in FINDINGS 34 is covered by a test, and none of it is in the
    suite. (FINDINGS 37 is: `test_strippedterrain.py`.)
    **(e9)** ✅ **DONE 2026-08-12 (FINDINGS 39). THE CLIENT READS A ROW WE RELOCATED**
    — map 143's Stripped partner moved **1.6 GB**, from `0x63C66800` to `0x323A400`,
    stored uncompressed where a compressed row had been, and the client found it,
    compiled from it, and emitted ArenaNet's shipped map to the byte (33,021 B, sha
    `acfc8e7501e94b9e`, 27 trapezoids). FINDINGS 35 is the control and was already
    measured, so the only new variable was the offset — the one field `datwrite`
    refuses to change. `datmove --check-overlaps` reports 0 overlapping pairs after a
    client session on the relocated 4.2 GB archive. The wall was never the compiler:
    `datwrite --replace` writes
    UNCOMPRESSED and refuses to relocate, so an authored stream only fits where it is
    smaller than its row's existing reservation. Map 143's own 64x64 file is 12,495 B
    against a 4,608-byte reservation, which killed FINDINGS 38's first design and forced
    it onto a 32x32 map. `toolkit/mapdata/datmove.py` is the relocation half:
    placement from `datplan.classify_runs` (never `free_runs` — 89.6% of the gap
    measure is live container generations), best fit, old reservation zeroed after the
    MFT is repointed, overlapping destinations refused. **46 checks, five sabotages all
    red, no vault** — and now two caged runs on top. FINDINGS 40 held a relocated row
    across **four consecutive sessions**: it never moved, its payload sha never
    changed, arming afterwards still rebuilt ArenaNet's map, and
    `datmove --check-overlaps` stayed clean on the real archive. The control fired
    every time (the client's scratch rows relocated in all four, 8315/8316 alternating
    between two address pairs — FINDINGS 18's double buffer from the row side), so
    "nothing moved" is a measurement rather than an absence of activity. **Two things
    are still unmeasured and neither is small**: the movement session did NOT run —
    our own `[npc.hatcher]` killed the character 10 s in and the last two walk legs
    were cut to 1.5 s by loss of foreground — and **nothing ever pressured the
    allocator**, since the 4,608 B the move freed was never claimed, so the client
    was never observed wanting space near our row. The
    capacity limit is real and reported: 176 of 349 map rows are larger than the largest run
    `datplan` will hand over, so for half the archive "nowhere" is the true answer —
    which is what the OTHER half, a compressor for the archive's format, would fix.
    That half is deliberately not attempted: its only strong oracle is a client
    accepting the stream, since agreement with our own `gwdat.py` decompressor is two
    of our own components agreeing.
    **(e10a)** ✅ **DONE 2026-08-12 (FINDINGS 41). THE COMPILER NEEDS SEVEN CHUNKS, NOT
    EIGHTEEN** — measured against the client one removal at a time, six sessions, and
    FINDINGS 34's disassembly-derived list was wrong in BOTH directions. `0x11000002`
    (Terrain Dependencies) is required and was not on it; Collision `0x1000000E` is on
    it and is not required. **Order matters and nothing had said so**: terrain bloat
    asserts `state->zones`, so Zones must precede Terrain. The four failure signatures
    are all different and all diagnostic — assert `deps`, assert `state->zones`,
    `Error: Creating default map` with no crash (the props gate's `je return 0`, exactly
    as §34 read it), and a rebuild carrying no mesh at all (no Stripped Path chunk).
    **Everything outside terrain and path is 124 bytes**: Header 8, Map Parameters 41,
    Props 12, Zones 34, Terrain Dependencies 29. That is the whole authoring target
    left, and `strippedterrain.py` and `pathchunk.StrippedPath` already write the other
    two.
    **(e10a-2)** ✅ **DONE 2026-08-12 (FINDINGS 42).** All seven have now been removed
    individually and all seven are required; Collision remains the only member of §34's
    list that is not. **The loader NAMES the chunk it cannot use** — `missing chunk
    'Header Stripped Data'`, `corrupt chunk 'Terrain Stripped Data'` — which §41 missed
    by reading `tail -1` of `Gw.log` instead of `tail -4`, and which corrects §41's
    account of the props signature: the re-bloat DOES run, and the failure surfaces as
    `corrupt chunk 'Path Stripped Data'`. Two more facts fell out. The Header is refused
    BEFORE the re-bloat and everything else after, so requirement has two stages. And
    removing Map Parameters makes the converter assert
    `dims.x * XY_DIST == mapRect.x1 - mapRect.x0` — `terrain.py`'s 96.0 cell pitch in
    the client's own expression, and a hard authoring rule for any map we build.
    **The harness gap is closed too**: `capture_error_dialog` was reachable only under
    `--keep-open`, so ordinary runs captured nothing; it now runs in `run_client`'s
    `finally` before the client is closed, and caught both of §42's asserts unaided.
    **(e10)** ✅ **DONE 2026-08-12 (FINDINGS 43). THE CLIENT COMPILED A MAP WE
    ASSEMBLED** — seven chunks built from typed parameters, **97.69% generated**
    (2,285 B of 2,339), 54 B borrowed across three NAMED chunks read from the owner's
    archive at run time. Map Parameters, Terrain, Terrain Dependencies and Path are
    generated; the deps chunk lands byte-identical to the donor's from four ids. All
    four predictions passed: no crash, 1,024/1,024 samples equal our height field, a
    Path chunk produced, and the mesh confined to the flat half (0.0% walkable area
    below x=1152, extent 1152..3072 — FINDINGS 38's mesh from a map we built rather
    than an edit of theirs). **One failure paid for itself**: seeding the Path chunk's
    boundary point at the rect corner, which our own terrain makes unwalkable, asserted
    `segments->Count()` at PathData:365. **The boundary point is a flood SEED and must
    stand on walkable ground** — FINDINGS 34 had seed/flood/contour as INFERRED, and
    this is the first observation of it, undiscoverable from the corpus because every
    retail map's point is already sensible.
    **(e10b)** ✅ **DONE 2026-08-12.** `stripbuild.py` + `test_stripbuild.py` (40
    checks, floor measured, 60th test in the suite): the E10 assembler out of the
    scratchpad, with all three rules that rung cost as REFUSALS — order, the derived
    rect, and `check_seed()`, which computes the quad slope under the Path chunk's
    boundary point and refuses above 30° with a message naming `segments->Count()`.
    Its controls are the measurement: the same point is accepted on flat ground. One
    defect shipped and the test caught it — `cell_of` sent the `(0,0)` corner to row
    `dim_y`, one past the end, because grid row 0 is world maxY.
    **(e10c)** ✅ **DONE 2026-08-12 (FINDINGS 44). THE PROPS CHUNK IS READ.**
    `props.py` + `test_props.py` (70 checks default / 79 under `--all` in ~200 s, floor
    measured, 61st test in the suite). **349 of 349 byte-identical**, and the record
    is VARIABLE LENGTH — 20 bytes plus four per outline point — which is why the
    survey in [studies/customarea/PROPS.md](studies/customarea/PROPS.md) found no
    law and was right to refuse to invent one: no fixed stride could ever have
    closed, and its count was read a byte late, straddling the tag. **285,670 props
    over 349 maps**; 37,548 carry a closed outline. `stripbuild.BORROWED` is now
    Header and Zones alone — **42 bytes, and 98.20% of the map generated**.
    The layout is a MEASUREMENT and the file keeps every control that makes it one:
    the stride came from an oracle in another chunk (float pairs against the Map
    Parameters rect — **285,670 of 285,670** inside), tag 6's stride 4 is the only
    one that closes the 149 maps whose count is non-zero, and the rival layout a
    stride-20 hexdump suggests closes for **0 of 349**. The memcpy saboteur is built,
    run, passes the headline and is caught 3 of 3. What the corpus CANNOT decide is
    asserted as such: tag 4's largest table is 81 entries, so its count width is
    undecided, and the check reddens the day that changes. Still UNVERIFIED: the
    tag-4/6 `value` words are carried, not understood, and the
    client's tag walk below `0x00737B40` was not read.
    **(e10c-2)** ✅ **DONE 2026-08-12 (FINDINGS 45). THE BLOATED PROPS CHUNK IS READ
    AND THE ORACLE IS A TEST.** `props.BloatedProps` (read-only, no encode, and the
    test asserts that) + `test_props.py` section 9: the compiled tag-0 size equals
    `2 + 48*props + 8*points` predicted from the Stripped side — **349/349 under
    `--all`** (110 checks, 718 s measured, floor 99), five rival formulas 0/335,
    record-for-record correspondence 285,670/285,670. Three of FINDINGS 44's
    INFERRED readings are now compiler-corroborated: the scale formula holds
    EXACTLY corpus-wide, the rot bytes single-axis-rotate a constant basis
    (composition still unmeasured), and the `extra` u32's fourth byte is §5's
    placement radius (595.0 × scale on all 414 instances of model 209883). Two §44
    population figures corrected in place (§45). And `stripbuild` learned the
    props-deps pairing: `0x11000004` present iff props, **349/349**, generated from
    run-time ids, both unpaired shapes refused (`test_stripbuild` §3d, floor 46).
    **(e10d)** ✅ **DONE 2026-08-12 (FINDINGS 46). SOMETHING IS PLACED.** Two client
    runs, one variable apart — the same authored prop (model file id 209883 via our
    own `0x11000004`) without and with a closed ±100 outline — and every load-bearing
    prediction hit: **the oracle on OUR input (compiled tag-0 sizes 50 and 90,
    exactly)**, `corresponds()` CLEAN both runs with B's ring back EDGE-EXACT, the
    +42 radius byte-identical to retail's own value for this model+scale, and the
    deps chunk surviving to `0x21000004`. **The outline is collision geometry**: B's
    navmesh hole is exactly the authored square, all four inside-ring probes flip,
    no outside probe moves. **And a prop with NO outline still carves** — run A
    found the compiler ALSO instances the model file's own collision sub-mesh
    (~±40-unit irregular polygon), falsifying the outline-only reading in the branch
    the predictions reserved. Predictions were recorded before arming and two
    prediction defects are kept in the run record
    (`vault/research/e10d-props-2026-08-12/`). Still open: visuals (screenshots
    caught the loading crossfade), play-session collision, union-vs-replace of ring
    and model footprint, generalisation past one model and one map.
    **(e10-next)** ✅ **DONE 2026-08-12 (FINDINGS 47). THE BLENDER LOOP IS CLOSED.**
    A scene authored in headless Blender (plaza, rolling ground, a landmark hill),
    exported through §32's pipeline, LATTICE-SNAPPED (`snap_block` first — a free
    field is essentially never on the transform's sublattice; worst move 4 units)
    and assembled by `stripbuild` with five ringed trees, was compiled by the
    retail client in one run with **every prediction hit**: heights back
    **1,024/1,024** through the BLOATED codec, oracle 442 exact, `corresponds()`
    clean, radii retail-exact ×5, and 12 of 12 mesh probes — five carved tree
    rings, walkable plaza and hill. Header (8 B) and Zones (34 B) remain the two
    borrowed constants. Still open: textures/sound/environment/light.
    **(e10e)** ✅ **DONE 2026-08-12 (FINDINGS 48). THE THRESHOLD SET IS MEASURED:
    15/35/30, walkable boundary 35.** The ramp map — five strips bracketing every
    candidate cutoff — compiled its 32.0° strip walkable and its 36.1° strip not,
    so the cut sits in (32.0°, 36.1°) and only 35 is inside; every number of
    10/45/40 is excluded. Free second result: walkable area is CONNECTIVITY-PRUNED
    from the flood seed — a flat plateau above a too-steep ramp is absent from the
    mesh, 5 of 5. `stripbuild`'s 30° seed refusal stays as a measured 5° margin.
    Unread still: the roles of 15 and 30, and whether the mode flag ever selects
    the other set.
