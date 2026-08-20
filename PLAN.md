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
| **R0a** | Vault + provenance gate + prior-art mirrors | A capture replays byte-identically from disk | ✅ **2026-08-04**, criterion met **2026-08-07**, `4ffa82a` (`toolkit/authsrv/replay.py`). Gate proven both directions, client pinned and hash-verified, prior art mirrored — and the `.raw` now decrypts back to the logged plaintext, 329 real captures reproduced exactly, all-or-nothing across 375. The stated criterion finally rests on the stated fact. See §3.1. |
| **R1** | Handshake against a local server | Client reaches character select | ✅ **2026-08-04 22:58**, `e34c417`. Build 38797 rendered "Test Warrior" against our portal, our DH parameters, our ARC4 channel and our login burst. |
| **R2** | Presence | Your own body standing in a real map | ✅ **2026-08-05 11:15**, `aedc214`. |
| **R3** | Movement on real geometry | You walk to a wall and are stopped | ✅ **2026-08-05 17:40**, `a97c7c4` — the server reads the game's own navmesh. Movement itself landed at `885d05d` (11:46). Estimated here as "a quarter, not a week"; it took six hours. **Movement FIDELITY is a separate question and it moved on 2026-08-19** (`a57960e`, `studies/movement/HANDOFF.md` §8): the warp is decoded in the binary — the snap is `0x006022B0` copying SYNC→ASYNC, reached only from `0x00605FC0`'s three message-driven callers, whose test is now decoded in BOTH halves (2026-08-20): a 100 u match against the client's own history chain — which never reads our grant — and failing that a fallback of **three gates, any one of which snaps** (straight-line separation over **299.33 u**, so exactly 300.0 u snaps; a walkable `pathCount == 0` meaning our granted position is off the navmesh; or the sync agent unable to take a first step). It is never evaluated per frame, and the snap reseeds **every** async agent. "Under 300 u is safe" is FALSE, and the 300.0f was recorded as walkable-path until 2026-08-20 when it is straight-line. Six candidate fixes are dead, **seven as of 2026-08-20**, and **no gate of the test is a server lever** — the only lever found is `0x002C`, already tried and removed by an earlier build. Both of the arc's instruments were repaired and mutation-pinned the same day: `movesync.py`'s hard bar now has TWO ARMS (implied speed > 400 u/s at dt ≥ 0.05 s, displacement ≥ 520 u below that floor), which takes the corpus from 61 to 64 hard rows over 961 captures and makes the three configurations read **7 of 267 / 20 of 468 / 13 of 197** hard jumps, **1.31 / 5.69 / 11.88 per minute of span**, magnitude p50 **1,969 / 569 / 582 u** — retail scores ZERO on both arms, and implied velocity is demoted everywhere to a labelled gate input, so magnitude and excess over the 288 u/s budget are the quotable pair. `pinned.py` now carries per-build TUPLES of accepted patched digests that the patchers themselves register, so the gate no longer refuses the 38797 we launch and can represent 38833. Tests: `test_movesync.py` 104 (floor 57), `test_pinned.py` 143 (floor 130), `test_buildid.py` 42, `test_buildpins.py` 40, `test_srclint.py` 22. |
| **R4a** | Agent model + combat core | An ettin swings at you and you die | 🔶 **half.** A hostile Hatcher stands in the map, and a click orders an attack the server drives to a kill and a revive (`f8320ff`, `37cb856`, 2026-08-06). ~~Nothing swings back and the player cannot die~~ — **BOTH MET 2026-08-11**, which is the half the criterion actually names. A Hatcher swings at the player, the player's health falls 10 a swing, and at zero the player drops face-down with both orbs at 0 and stands back up ten seconds later. Three full death/revive cycles in one 65 s run, on the wire and on film (`vault/captures/gamesrv/authsrv-20260811T160502-c1.jsonl`, `frames-20260811T160449`). `studies/enemy/PLAN.md` §11. What is still missing is a real agent model — no AI, no pathing (the Hatcher stands where it spawned and swings when you are inside 1200 units), no resurrection shrine (the revive is a timer), and energy is not restored on revive. No agent table either — `studies/enemy/PLAN.md` §7.2. **2026-08-11: one click now drives a whole fight** — `0x0026` ATTACK_AGENT arrives (four of them at our Hatcher, zero `0x0033`, ending a year in which the client had never once sent it), the server dispatches it, seven swings at 1.77 s kill the agent, and it revives; the client drops the dead target and re-acquires the revived one unprompted (§10.9). **The first revive crashed the client** — `CharPool.cpp:84`, `fraction <= 1.0f` — because we sent `max_health` where a fraction belonged, on the one side of a `<=` bound that no damage test could ever reach. Fixed and re-verified. **2026-08-11 (earlier): the click arrives as `0x0026` ATTACK_AGENT** — four of them at our Hatcher, zero `0x0033`, ending a year in which the client had never once sent it (§10.7). The server now dispatches both arms. **2026-08-15, the combat arc ([studies/combat/PLAN.md](studies/combat/PLAN.md)):** the kill window is now ArenaNet's three messages rather than one — `0x00F1` death, `0x00EE [0, 26]` reward, `0x0026` flags 8, same tick, the reward byte-identical to the capture — and the richer-looking `0x00EE` PAIR is deliberately REFUSED, because 6 of its 7 sightings fire far from any death inside a `0x009C`-marked broadcast burst (§13). The guard contract was rebuilt red-first so a refused value costs the value and not the socket or the world tick, and **overkill now clamps to a kill instead of silently no-opping** — a bug caught before it could ship, since damage rides the wire as a fraction of max health and a decoded skill exceeding a weak target's pool would have been refused outright. The server also models attribute ranks at last: `0x003A` carries real ranks, so `2 * rank` is no longer 0 (see R4b). **And for one day that message killed the client on every spawn** — `0x003A` is COLUMN-MAJOR (`ids | ranks | ranks`, the handler slices one flat array at `n` and `2n`) and it was sent as interleaved `(id, rank, rank)` triples, which puts attribute ids in the rank column and asserts `level < arrsize(s_attribPoints)` at `CharData.cpp:202`. Fixed 2026-08-15, `studies/combat/PLAN.md` §14, diagnosed statically from the dump's own stack. `arrsize` was a number nobody had read and the one recorded was wrong — `consttable.py` had 14 x 4, it is 13 x 4, corrected with a new structural locator (`clientscan/attribpoints.py`). **CURE VERIFIED the same day** (§14g): caged loopback run, 1,716 messages, last at t=78.2 s, no assert — the payload the client used to die on now goes out at t=0.85 s and it runs on for another seventy-seven seconds. **And L6's attributability criterion is MET on the same run**: `--probe attributes` drove all three steps and the panel followed, with the ranks against the right names (see R4b). Note that two earlier instrumented runs were reported healthy while the crash box was on screen — the assert dialog is modal INSIDE the client, so liveness polling cannot see it, and the run above is watched with `crashwatch.ps1` instead. **AND THE DAMAGE IS NO LONGER OURS, 2026-08-20** (`abd9910`, `2b57034`, `2173584`): a swing was 15% of the target's max health — so every creature took the same seven swings however tough it was — and is now the equipped weapon's own range (identifier 584) scaled by `2^((SL−AR)/40)`, with criticals as an armour reduction of 20. The model is `studies/isle` rung 7's, read off 495 live damage events, and the implementation reproduces that capture's own point bands at **all six endpoints** with zero free parameters. Creature AR is DERIVED from level and profession (WIKI), after a picked 60 turned out to be level-20 armour on a level-1 creature — the wrong SHAPE, which is `studies/monsterai` §3.3's lesson for reach paid a second time. On screen and matching the wire swing for swing (`20260820T162204`, `…T162932`). **Still absent: nothing reads the PLAYER's armour** — five pieces carrying `Armor: 25` go out and the enemy's swing is still a flat 10% of the player's pool — and no unmet-requirement term, which `studies/isle` refutes and forbids replacing. |
| **R4b** | The skill substrate | See §3.2 — rewritten as a count | 🔶 **started, and the combat arc moved it a long way (2026-08-15, `studies/combat/PLAN.md`).** Eight real skills on the bar with correct tooltips (`70c3926`), the cast lifecycle read out of the client's own asserts, `USE_SKILL` answered. ~~No skill resolves an effect.~~ **Skills now resolve damage from the client's own numbers**: the whole `s_skill` scaling window `+0x44..+0x68` is decoded, and damage is the skill's scale endpoints interpolated by the CLIENT's own formula (`0x005A8920`: `max(0, round(lo + (hi−lo)·rank/15.0))`, divisor a literal 15.0 verified by a stdlib read, no upper clamp so ranks above 15 extrapolate). `ENEMY_SKILL_FRACTION = 0.25` — a flat quarter of the player's maximum for every skill, admitted invention — is **gone**. The cast lifecycle is on the wire as ArenaNet sends it (`0x00E4→0x00E5→0x00E3→0x00E6`, with the QUEUE LAW: a press during aftercast schedules from the aftercast's end, which refutes the naive press+activation model by +0.64 s/+0.57 s). **The limit is now semantic, not numeric, and it is a real finding**: the client's table gives a magnitude and never says what it MEANS — `scale0/15` is `+ Damage` on Power Attack and `Healing` on Restore Condition, and `type_code` cannot discriminate. Three of the four skills on our own enemy's bar are a heal, a hex and an enchantment, so meaning is GWW-sourced per skill and unmodelled skills resolve to **None, not 0**. Still absent: conditions, hexes, enchantments, energy and adrenaline costs, and effects other than damage. **2026-08-15, L6's attributability criterion is MET** — `--probe attributes` ran caged and the attribute panel followed all three steps with the ranks against the right names, so the ranks `2 * rank` reads are the ranks the player is shown. That also closes the one gap static analysis could not (`studies/combat/PLAN.md` §8b: whether the panel control binds the local agent at runtime) and confirms §8a's slot reading positionally, since step 3 reverses the rank column while holding the id column's order. The same run is what verified the `0x003A` crash fix — see R4a. **2026-08-15, the cast lifecycle is PLAYED AT A CLIENT** (`studies/combat/PLAN.md` §15, retiring §7's blocker): `0x00E4→0x00E5→0x00E3→0x00E6` had been offline-tested against six live cycles and never rendered. Four complete cycles now, accepted without asserting, max 36 ms against the declared recharge; a repeat press after `E6` gives a full second cycle; and recharge is **per-skill with concurrent timers** — slot 6's 8 s overlaps slot 7's 3 s cycles and each `E6` names its own skill. Operator-confirmed rendered: **both slots swept, slot 6 clearly longer than slot 7**, which is what shows the client honours the message's DURATION rather than flashing an icon. Still absent from this: the cast ANIMATION, which was not watched and is the unrun `cast_anim` probe's question (opcode 228 vs agent property 60), not this acceptance's. |
| **R4c** | AI + spawns + quests | See §3.2 — rewritten as a count | ⬜ not started, **and 2026-08-11 established what "started" would even mean** ([studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md), `9eb09a8`+). Monster AI *as a mechanism* is **not recoverable** — not from the client (0 of 937 embedded source paths under any `\Srv\` tree, from a detector proven to catch 6 of 6 planted ones; 33 AI-adjacent searches over two independent routes, all zero), not from the wire, and not by any capture campaign, because it is never shipped and never transmitted. What **is** recoverable is the observable envelope, and the study designs the labelled behaviour campaign that would recover it (§7) plus four desk follow-ups needing no capture at all (§7.9) — **the first of which ran the same day and made the binary negative total**: `CHAR_AI_MODES`, the one lead the study declined to call refuted, is 3 and its modes are Fight/Guard/Avoid Combat, i.e. the player's own hero-and-pet stance widget. It also found the AI-adjacent numbers already in `authsrv.py` are mostly the **wrong shape** rather than merely unmeasured: reach is per-creature-model (~65 / ~599 / ~706 units observed against our one global 150), a leash is *uncomputable* from the state `spawn_enemy` keeps, and 4 of 5 fights in the corpus are started by the **player**, refuting our proximity-initiation model for 4 of 5. **2026-08-15 — the PARTY half of this rung is now scoped, and it is the recoverable half** ([studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md)): heroes and henchmen are the mirror image of monster AI, because a hero is a thing the CLIENT renders, commands and stores. The two party-add messages are shaped from the client's own descriptor tables and traced store-by-store — `0x01BF` PARTY_HENCHMAN_ADD `[u16,u16,string16(20),u8,u8]` (CORROBORATES GWCA independently) and `0x01C2` PARTY_HERO_ADD `[u16,u16,u16,u8,u8]` (**CORRECTS** OpenTyria's "a `uint8` level"); `0x0074`'s upstream `{hero_id,level,primary,secondary}` is **REFUTED** at 20 fields / 127 bytes. The catalogue is located and closed: **`s_heroClientData` = 40 rows × 24 B at `0x00A35E08`**, `HEROES`=40, `HERO_UNUSED`=0, per-player cap **7** (three independent sites) — and the rival 48×12 reading was a misattribution to the **adjacent title table**, settled by reading the client's own assert strings. Extraction is ruled **permitted** under the MEASUREMENT branch. The honest negatives: hero **skill-bar delivery is NOT FOUND** on any wire shape, and the **c2s** direction (stance, flag placement, hiring) is NOT FOUND at every point looked. **The wire cannot teach this** — 0 of 22,524 decoded live GAME_SMSG messages carry opcode 114/116/447/450, because every live session is solo; the only vault appearances are 92 `PROBE[smsgsweep]` sends. A henchman authorship route is **buildable now** (one new message on top of the existing `party_build()`), with acceptance criterion R4c-H in §8. **2026-08-16 — R4c-H IS MET, caged loopback, four arms** ([studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md) §10): control **1** roster row, treatment **2**, the second reading **`Mo1 Hatcher [Collector]`** — archive-resolved name, Monk, level 1 — from one `0x01BF`. Three results beyond the criterion. **(a)** The row draws with **NO world body** (so `PtRoster:602`'s agentId lookup is not a precondition) but draws EMPTY: `Lvl 255 ...`. **(b) A discriminator arm overturns the upstream reading** — with the wire deliberately carrying a *different* name, profession 6 and level 20 while the body kept Hatcher/Monk/1, the row rendered **the BODY's values in every field**, proven from the captured plaintext. So `0x01BF`'s name string and its two trailing bytes do **not** drive the roster row: the message binds a roster SLOT to an `agent_id` and the client reads the rest from that agent. GWCA/OpenTyria's `profession`/`level` names are **not confirmed**, and the body arm alone *looked* like a confirmation because it was a confound. **(c)** Unpredicted: the **compass flag widget appears** (one group flag + three numbered + clear) from one `0x01BF` even with no body, corroborating the wiki's four-control description and §3.1's index-0 reading from the screen. Henchman authoring is done as a mechanism. **2026-08-16, same day — THE HERO ARM RAN TOO, five arms, closing two of §7.2's three blockers** (§11). **(1) `0x01C2`'s word order is settled BY CONSTRUCTION**: the body was created at agent **200**, deliberately outside the 1..39 hero-index range, so a word carrying it cannot be a legal hero index — and the row renders only in the arm where **msg+0xc (→ entry+0x0) holds the agent id and msg+8 (→ entry+0x4) the hero index**. That yields a structural fact too: **entry+0x0 is the agent id in `0x01BF` AND `0x01C2`** — same storage slot, different wire order, so §1.2's refuted "by analogy" reasoning reached the right offset for the wrong reason. **(2)** The hero row renders `Mo1 Hatcher [Collecto…]` **plus a numbered commander-slot button** the henchman row lacks (`GmHeroCommander`'s per-slot UI), and its text again comes from the AGENT — three arms, two message families, one rule. **(3) `0x0074` MERCENARY_INFO is what creates the `charHeroData` record**, by a single-variable pair: with it the trailing `0x0072` diagnostic asserts `attribState` (`ChCliAttrib.cpp:156`), without it `charHeroData` (`ChCliHero.cpp:199`). Every static route had this NOT FOUND; one arm settled it. **The gate did not vanish, it MOVED** — onto §4's sharpest negative, hero **attributes**, which the client now names itself. **(4) That shaped hypothesis — `0x0074`'s two 5-dword groups as the attribute block — was TESTED AND REFUTED the same day** (§12), with the prediction on record before the run. An arm carrying ten dwords of `12` (the rank cap), the third-copy flag set (a branch never previously exercised) and the leading bytes loaded produced a **byte-identical** `attribState` assert. Reading the assert instead of guessing gives the real shape: `attribState` is a **separate `0x43c`-stride record, binary-searched by a key at +0**, holding **`attrib[51]` of 20 bytes each** (`ChCliAttrib:177` `cmp 0x33`; index math `20*i+4`) — 1020 bytes, against a 40-byte chunk in a different structure. New measurements banked: **51 attributes**, **rank cap 12** (`AcctTemplate:441`). **The live lead is now the TEMPLATE system** — `AcctTemplate:422/423/440` and `TemplatesCode:168`/`TemplatesHelpers:368` bound a struct carrying `attribCount` + `attrib[]` + `attribValue[]`, which *is* a build, and is §4's "packed template blob" candidate with named asserts to find it by. **(5) 2026-08-16, third pass — the template lead was a RED HERRING and the real mechanism was already in our tree** (§13). `AccountTemplateDataSkill` (140 B: profPrimary, profSecondary, attribCount, attrib[12], attribValue[12], skill[8]) is **account-local** — the base64 saved-build feature — and a reachability closure from it contains **zero message handlers**. What actually creates an attribState record is **`GAME_SMSG 0x0037`** (`[agent_id,u8,u8]`, handler `0x0091d8c0` → thunk `0x0080EAA0` → creator `0x008199C0`, whose own guard is `ChCliAttrib:313` `!attribState`), and **`0x003A`** (`[agent_id, array32[48]]`) fills `attrib[]`. **Both are keyed by AGENT id, which is why a hero can have attributes at all — and both have been in `authsrv.py` since the combat arc**, sent to the player's agent every session. Two refuted hypotheses were spent hunting a message already in the tree: the §3 failure in miniature. Sending the pair for a hero **does clear the attribState gate** — but the client then dies on **`profession < arrsize(s_profChapter)`, `ConstChar.cpp(1296)`, bound 11**, with or without the `0x0072` diagnostic, so it REGRESSES an otherwise-working hero and the flag ships OFF. Two more fixes tried and refuted there: `0x0074`'s `b2`/`b3` (upstream's "primary/secondary" — a second failure to confirm those names) and matching the body's profession to the attribute set. **(6) 2026-08-16, fourth pass — READING THOSE THREE CALLERS CLOSED IT. THE HERO IS AUTHORED** (§14). All three sit in one function, `0x00819EF0`, which takes the attribState record, reads **its agent id**, and looks that agent's primary/secondary up in **`ctx[0x2c]+0x6BC`** — the array `studies/profession/RUNS.md` already knew is written only by **`0x00B7`**, which we had only ever sent for the player. **There are TWO profession stores**: `0x00A6` writes the agent's own bytes (what the roster label reads — why the row already said `Mo1`), `0x00B7` writes `+0x6BC` (what the attribute code reads). Conflating them cost an afternoon. With `0x00B7` sent for the hero, gate 3 cleared and the assert moved to `attribState ChCliAttrib.cpp(435)` — whose fix `authsrv.py`'s own comment already recorded: **points first, profession second**. **Four gates, all cleared:** `charHeroData`→`0x0074`; `attribState:156`→`0x0037`; `ConstChar:1296`→`0x00B7` for the hero's agent; `attribState:435`→ordering `0x0037`→`0x00B7`→`0x003A`. The `0x0072` diagnostic that ASSERTED on 2026-08-12 now **completes silently**. **The payoff is a name**: with the record incomplete the row read `Mo1 Hatcher [Collector]` (the body's name); complete, the same row reads **`Mo1 Norgu`** — `s_heroClientData` row 1. The client SWITCHES name sources once the hero record is satisfied, which measures §0's central claim that a hero resolves its identity through the static table. Also read in passing: **`s_attrib` = 51 rows × 20 B at `0x00A35740`** (profession, self-index, two string ids, an is-primary flag set on exactly ten rows), and attributes 26-28/45-50 carry profession 11 — the PvE title tracks, out of range by design. **(7) 2026-08-16, fifth pass — THE SKILL BAR, and §4's negative was a SCOPING ERROR** (§15). `0x00DA` SKILLBAR_UPDATE is `[agent_id, array32[8], array32[8], u8]` — RECV, **agent-keyed, eight slots** — and this server has been sending it **for the player every session**. §4 searched `0x0074`/`0x01BF`/`0x01C2` and the SEND-direction shapes and concluded "no skill-bar field anywhere"; the answer was outside that space. **Fourth time this arc that the mechanism was already in the tree** (after `0x0037`, `0x003A`, `0x00B7`) — every piece of a hero turned out to be an existing agent-keyed message we only ever addressed to the player. Sent to the hero it is accepted, 75 B, no assert. **HONEST LIMIT: that is delivery, not display** — the hero panel is opened by clicking the commander-slot button and that click CRASHES, so nobody has seen eight icons. **`0x0072` is not a diagnostic, it is HeroActivate**: its four fields are the client's own format string `HeroActivate (hero %d, agent %d, inventoryId %d, aiMode %d)`, matching the descriptor exactly. Measured, two runs differing only in it — without: the row reads `Mo1 Hatcher [Collector]` (the BODY's name) and flag 1 is greyed; **with: `Mo1 Norgu` and flag 1 goes GREEN**. So `0x0072` promotes a labelled body into a hero, switching the roster label to `s_heroClientData` and binding the `GmHeroCommander` slot. **`aiMode` is field 4, so the Fight/Guard/Avoid stance IS server-settable** — a partial answer to §3.3's oldest open question. **(8) 2026-08-16, sixth pass — `inventoryId` REFUTED as that suspect, twice** (§16). Naming the assert should have come first: the click crash is **`commander` / `GmView.cpp(5890)`**, not any of the eight inventory asserts (`asserts.py` cannot read line 5890 — one of its 371 blind sites, its answers being floors). And `inventoryId = 1` changes nothing: accepted with no assert on the activation path, and the **identical** crash on the click. The field is **inert on every reachable path** and its meaning stays NOT FOUND. **The real cause is now read statically**: commander objects live in a container at `ctx+0x20`, `heroCommanderSlot[7]` at `+0x30` holds **keys into it**, `0x00524C40` is a **get-or-create**, and `0x00524DB0` — the one the click uses — **does not create**, it looks up and asserts. Our hero has no entry. The creator's other caller sits in a loop over the `activeHeroes` stack buffer built by scanning the party's agents (`GmHeroCommander:214`). **Precise next step, desk work only:** does that scan skip our hero, or register it under a key different from the one `GmView:5890` looks up? **(9) 2026-08-16, seventh pass — THE DESK WORK, and it refuted its own prediction** (§17). The whole commander path is now read out of the binary: the iterator `0x008563B0` walks `[ctx+0x4c]`→my-party→`+0x24` with **stride 0x18 — exactly `0x01C2`'s entry size**, so it walks the entries we append; the scan `0x00524E00` filters `[edi+4]` against a widely-used "my id" accessor and takes **`[edi+8]` as the commander key**, which is where `0x01C2`'s `msg+0x10` lands — and we had been sending **0** there. Prediction: put the hero id in `msg+0x10` and the panel click stops asserting. **REFUTED** — identical `commander`/`GmView(5890)`, with no regression (`Mo1 Norgu`, slot bound, flag green), so the change is kept as better-founded but is RECONSTRUCTION, not a fix. **What it eliminates is the value**: the scan has exactly ONE caller, `0x004E5D85`, inside a GmView **event** handler, so the leading explanation is no longer "wrong key" but **"the scan never runs"** — the commander container is filled by a client-side UI event, not by the wire. **Also a self-correction (§17.3): §11.1's "msg+8 is the hero index" is WITHDRAWN.** H1/H2 only showed `msg+8` accepts 1 and rejects 200, and in this rig `PLAYER_NUMBER`, `PLAYER_AGENT_ID` and the hero index are **all 1** — hero index, owner player and owner agent are indistinguishable, and the scan's filter actively suggests *owner*. `msg+0xc` = agent id still stands. **(10) 2026-08-16 — ran that rig: hero index 2, and the confound broke** (§18). With `msg+8`=1, `msg+0xc`=200, `msg+0x10`=2 all distinct, the row rendered **`Mo1 Goren`** — hero 2's own name. So **`msg+8` is definitively NOT the hero index** (it carried 1 while the hero was 2), settling by experiment what §17.3 could only doubt; what it *is* stays UNVERIFIED, narrowed to owner-player-number vs owner-agent-id, which are both 1 here. **And `s_heroClientData` row 2 = `Goren` is now confirmed FROM THE SCREEN**, independently of the recon's `textrec.py` resolution — rows 1 and 2 both verified from two unrelated directions, so the catalogue reading is solid. Remaining confound: `0x0074`, `0x01C2`'s `msg+0x10` and `0x0072` all carried 2, so which message supplies the identity is undetermined; **(11) 2026-08-16 — ran that split too, and `0x01C2` carries NO hero identity at all** (§19). Prediction on record first: row 3's name id 36274 resolves to **Tahlkora**, so Tahlkora would mean the identity rides `msg+0x10` and Goren would mean it rides `0x0074`/`0x0072`. With `0x0074`/`0x0072` on hero **2** and `msg+0x10` on **3**, the row read **`Mo1 Goren`** — the client ignored the party-add message's hero id completely, with no crash and no change. So the hero's identity arrives **entirely on the data-cache family**, and `0x01C2`'s five fields are a party id, an owner-ish word (UNVERIFIED), the agent id and two bytes. That is stronger than §0's original "a hero carries no NAME": it carries no identity. **`msg+0x10` is now inert on everything observable** — §17.1 read it as the commander key from the scan's `[edi+8]`, §17.2's hero-id value did not fix the panel click, and a deliberately WRONG value here changes nothing; consistent with §17.2's leading explanation that the scan never runs. Its role stays RECONSTRUCTION. **(12) 2026-08-16 — split those too, and the question was malformed** (§20). Three outcomes named first; the run gave the third. With `0x0074` creating a record for hero **2** and `0x0072` activating hero **3**, the client produced `charHeroData` / `ChCliHero.cpp(199)` — the **identical** assert §11.3 got by omitting `0x0074` altogether. So **`0x0074`'s field 1 is the record KEY and `0x0072`'s field 1 is a SELECTOR into the same namespace**, and a mismatched selector is indistinguishable from the record never existing. Neither message "supplies" the identity: `0x0074` creates a keyed record that carries it and `0x0072` activates that record under the same key. It also re-confirms §11.3 from a new direction — that section removed `0x0074` to prove it creates the record; this keeps it and mismatches the key, a different manipulation reaching the same gate. **The family now reads: identity is the data-cache record's; `0x01C2` only binds a roster slot to an agent id.** **(13) 2026-08-16 — `msg+8` IDENTIFIED: it is the OWNER PLAYER NUMBER** (§21). `--player-number 2` finally separates `PLAYER_NUMBER` from `PLAYER_AGENT_ID`, and two arms differing only in `msg+8` are **exact mirrors**: `msg+8`=2 (player number) renders the row but leaves the commander slot unbound; `msg+8`=1 (agent id) binds flag 1 but shows **no row**. The roster row appears exactly when `msg+8` equals the declared player number — consistent with the original rig and with H1's rejection of 200 — so the field is now positively identified, closing the thread §11.1 opened wrongly, §17.3 withdrew and §18 refuted. **The mirror is the unexpected half**: both consumers read `entry+4` yet compare it against DIFFERENT "my id" values — the roster UI against our declared player number, the `GmHeroCommander` scan against `ctx[0x44][0x2ac]`, which stayed 1. RECONSTRUCTION: `--player-number` changes only what we SEND, not what the client believes about itself, so it desynchronises the two; in the default rig both are 1 and everything agrees, which is why the hero worked. Whether `ctx[0x44][0x2ac]` is the agent id or a client-side player number is still undecidable here (both are 1) and needs the CLIENT's value moved, not ours. Practical: do not use `--player-number` outside this experiment — it makes the roster row and the commander binding mutually exclusive. **(14) 2026-08-16 — found what writes it, desk work only** (§22): `ctx[0x44]` is the MISSION subsystem (accessor `0x0084DD70` sits in **MsCliApi**), `--field 0x2AC --writes` gives eleven stores of which two in that range are real, both copy **field 1** of a message struct, and neither has a call xref — each VA sits in one aligned `.rdata` word, i.e. a dispatch entry. `msgshape --all` resolves them: **`0x0199` INSTANCE_LOAD_INFO** (handler `0x0084EF00`) and `0x01A4` (handler `0x0084F230`, never sent by us). **So `ctx[0x44][0x2ac]` is `0x0199`'s field 1 — the player's agent id, which this server has sent at every instance load since the beginning.** That explains §21's mirror exactly: the roster UI filters on the player number while the commander scan filters on `0x0199` field 1, and `--player-number 2` moved one and left the other at 1. In the default rig both are 1, both filters see 1, and the hero binds. **Trap removed:** that field was a literal `1` at the send site rather than `PLAYER_AGENT_ID` — harmless today, but it demonstrably feeds a filter three subsystems away, so it now uses the constant. The confirming arm (move both together) was NOT run and the reason is recorded: it means moving `PLAYER_AGENT_ID` itself, which touches the spawn path and deserves its own arm. **(15) 2026-08-16 — A FULL AUTHORED PARTY OF FIVE** (§23): player + heroes **Norgu, Goren, Tahlkora** in commander slots **1/2/3** + the **Hatcher** henchman, one roster, one run. `--hero` takes a list and `hero_slots()` owns the agent-id/definition arithmetic in one place. Four things measured that n=1 could not: the `heroCommanderSlot[7]` array **assigns sequentially and independently** (three separate numbered buttons); each hero **resolves its own identity** from its own `0x0074` record, so §20's keyed-record model holds past one; heroes and henchmen **coexist and the client distinguishes them visually** — the henchman row has NO numbered button, which is §3.1's reconstruction and the wiki's "three individual flags plus one all" now visible rather than inferred; and **`s_heroClientData` row 3 = `Tahlkora` confirmed from the screen**, so rows 1/2/3 are each verified from two unrelated directions (archive resolution and the client's own rendering). Guards mirror the client's bounds: >7 heroes refused (`cmp 7` at PtPlayer:332 and GmHeroCommander:214), duplicate hero ids refused (one record per key),  **(16) 2026-08-17 — THE COMMANDER QUESTION IS MEASURED, and the arc's last wall is down** ([studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md) §33). §26.4/§27.2/§32 all stopped on one sentence — *does `0x008590CA` execute, and it needs a breakpoint or code cave*. Built as `toolkit/clientscan/commandertrap.py`: a debugger in pure `ctypes` setting EXECUTE breakpoints in **DR0..DR3**, which are per-thread processor state, so **nothing is written into the client** — no `int3` over an instruction, no code cave, no injection (carve-out 3 permits a compiler; this did not need one). Every site's bytes are re-verified against the RUNNING process before arming, because the pin is 38797 and these are 38833 addresses and §24 already crossed those once. **Three arms, control firing in all three.** Default rig (party-cache HIT): `worker=1 raise=0` — §26.2's gate OBSERVED doing what the disassembly said, predicted in writing beforehand. `--hero-bust-cache` (cache MISS): `worker=1 raise=1 case93=0` — **the event IS raised and its handler never runs**, and the image's own byte map + jump table make that unambiguous (`0x1000011E` → case 93 → `0x004E5DE1`, the ONLY event routing there). Bulk path: `bulkraise=1 bulk=0 create=0` — `0x00524C40` **never executes**, confirming §27's `count=0` by a code trace rather than a memory read, two unrelated instruments agreeing. **The corrected shape: the missing piece is a SUBSCRIPTION, not a trigger.** Every earlier fix (`inventoryId` §16, `msg+0x10` §19, the cache gate §26) aimed at making the client RAISE the event; §26's arm actually succeeded at that and the panel still asserts. **So `0x01C2` cannot bind a commander and no wire field will change it** — the hero as authored (row, name, level, profession, attributes, skill bar, lit flag) is complete for everything the wire governs. Also confirmed from the frozen client: §25.1's push-order decode against the live stack, and §26.1's `ecx`-holds-the-entry claim. **Four tool defects, three caught by the tool's own control before it ever read the client** (§33.8) — a 64-bit debugger receives `STATUS_WX86_SINGLE_STEP` (`0x4000001E`) not `0x80000004` from a WOW64 target, so v1 reported NO HITS and would have published the right headline from a dead instrument; `EFLAGS.RF` does not survive `ContinueDebugEvent`, so one instruction trapped 32 times in 4ms and read as "executed 32 times"; state was captured after the read handle closed, so a whole run's fields came back `None` and that run was DISCARDED rather than published; and the module list is not ready the instant a process exists. **The control had a hole too**: it stopped at the first hit, proving a breakpoint FIRES while saying nothing about whether the target RESUMES — and the untested half was the broken one. **(17) 2026-08-17 — (16)'s wall is DOWN, and its closing sentence is SUPERSEDED** ([studies/pvpui/FINDINGS.md](studies/pvpui/FINDINGS.md), the PvP-UI arc, `4bab982`+). (16) ended *"`0x01C2` cannot bind a commander and no wire field will change it"* — the subscription reading was right and the conclusion drawn from it was wrong, because the missing piece was **timing**, not a field. Measured: our `0x01B2` raises `0x10000114` at instance load and **GmView subscribes to that event 53 milliseconds later**; its GmView case is the only caller of the commander-model rebuild, nothing raises it again, so the model is built once over an empty container and never rebuilt. **`--party-mine-late SECONDS`** (new, opt-in, off by default) re-sends `0x01B2` after the load — a second send is a second raise, because the handler raises on both branches — and `0x00524C40`, the function (16) proved never executes, **ran for the first time in this project**: commander container `count=0 → count=1`, `heroCommanderSlot[0] = 0x1`. A wire message binds a commander after all; it just has to arrive when someone is listening. **Then three owner clicks on the party-window hero button walked the assert forward four times**, and the whole `GmView` case for `0x100001A4` now passes: `commander` (5890) → `heroData` (5897, with `--hero-roster-id 200`) → `heroData->agentId` (5898) → out of `GmView` entirely. That last hop was this lineage's recurring failure again — `heroData->agentId` has exactly one writer, opcode **`0x0072` HeroActivate**, and `HERO_ACTIVATE = False`: **a message the tree already implemented, behind an opt-in flag no run of the arc had switched on**, the fifth such (after `0x0037`, `0x003A`, `0x00B7`, `0x00DA`). The click now stops at **`inventory` / `ItCliApi.cpp(488)`**, a general 22-caller equip-slot helper — **the hero has no per-owner container in the item client's table at `[globals+0x40]+0xD4`**. Cross-checked against §8's `0x006D` item line the same day and it is NOT that: item RECORDS already exist (375/375 of retail's non-zero `0x006D` ids are `0x015E`-family declarations), the missing piece is the owner's container, and our `0x013F`/`0x013E` bag family has only ever been addressed to the local player. Corrections this arc owes, all in its study: the harness does NOT default to 38833 (`drive_client.py:87` selects by build, :167 excludes it — pass `--exe` **and** `RURIK_DAT`); `0x01D9` writes `+0x58`, a different field, not the container pointer; and **every `PyCliParty` worker takes `this = object + 4`**, so field `+0x54` is spelled `0x50` and a displacement-anchored scan returns a confident zero — now a fourth documented blind spot in `codescan.py`'s footer. **AND THE HERO HALF IS SETTLED THE SAME WAY THE MONSTER HALF WAS, 2026-08-20** (`7df1dce`, `d037bc5`, [studies/heroes §5.5](studies/heroes/FINDINGS.md)): the shipped client holds **no hero AI at all**. 51 of 937 embedded source paths match hero/companion vocabulary and every one is UI, a client-side `Cli` record or a `Const` table; a behaviour-vocabulary regex over 19,758 asserts returns **exactly one hit**, and it is a widget asserting its own button state next to `m_aiMode < AI_MODE_ICONS`. The client's whole notion of hero AI is how many pictures the button strip can draw. This did NOT follow from `studies/monsterai` — GWW says heroes and henchmen share an AI and says nothing about hero↔monster — so it was re-run with hero vocabulary and its own control. **So this rung is authoring, not recovery**, and §5.6 counts what the authoring can be checked against: ~92 implementable per-skill rules, not the 184 the category size implies. Deliberately unplanned further — the rules are conditions over effect state R4b does not model, and the skill substrate's schema is likely the AI's schema. |
| **R5** | Declarative authoring toolkit | A new zone in TOML, hot-reloaded, walked | ⬜ not started — but its substrate exists as of `501698b`: `content/*.toml` and `toolkit/content.py`, with the server holding zero content literals. **Its other half now exists too**: R5m authors the zone's *geometry*, which TOML was never going to describe. **And the ITEM half stopped being opaque on 2026-08-20** (`3cdb0c8`…`2f15b41`, [studies/itemmods](studies/itemmods/FINDINGS.md)): every item's stats live in 32-bit modifier words that `content/items.toml` could only copy verbatim out of a capture — armour rating, damage range and every "+N" line among them, which `studies/character` called "the largest hole" in three places. The format is now read out of the client's own parser — `{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}` over 157 identifier slots, each one's meaning recoverable because every handler formats through TextApi — validated on **5,266/5,266** real modifier words and located structurally on all three builds. **A word we composed has been rendered by the retail client**: `0x21F81301` on the starter hammer drew `Hammer Mastery +1 (Stacking)`, so authoring an item's stats is now writing a number rather than finding one. The trap: bits 31, 30 and 19 are a fixed per-identifier prefix and must be COPIED, not computed. |
| **R5m** | **Custom map geometry, end to end** | A map we authored loads in the retail client, and geometry we chose constrains the character | ✅ **2026-08-11**, arc landed `0be1555`, criterion completed the same day. **The client walks on our terrain and stops at our walls.** `mapbuild.build_flat` assembles a whole map from typed parameters — 7,841 B, 9 chunks, **97.04% generated**, the rest being FINDINGS 14's 232 bytes of ArenaNet constants read from an archive at run time — and the retail client loads it, places a character in it and writes nothing back (FINDINGS §22, four discriminators). Then **E1 proved the geometry is ours and not a coincidence**: two maps differing in **33 of 7,841 bytes**, all inside the pathing chunk, both 7,841 B, with the mesh rect at 0..3072 against 1024..2048, confined the character to reported bounding boxes of **3072.0 × 3072.0** and **1024.0 × 1024.5** — the ratio of the two rectangles, measured from the client's own position reports while our server broadcast no position at all (FINDINGS §23). The read direction is byte-exact across the corpus: terrain 349/349, pathing 349/349, whole map file 349/349 Bloated **and** Stripped — and since 2026-08-12 the STRIPPED terrain chunk too (`strippedterrain.py`, FINDINGS §37), whose real claim is not the round trip but that its **60,468,224 height samples equal the Bloated chunk's on 349 of 349 maps**, pulled out of a Huffman bit stream by a module that never reads that chunk. A retail map also stands up in Blender (`tools/blender/import_gwmap.py`, 213,921 verts, orientation checked against the props chunk through the test's own walker — the terrain path never reads it) and **since 2026-08-12 comes back out of it**: `export_gwmap.py` round-trips Pre-Searing's 212,992 heights, tiles and shade bytes byte-identically through a `.blend` read by a separate Blender process, and a mesh authored in Blender from nothing reaches a map file passing all 17 open-time gates (FINDINGS §32). **Since 2026-08-13 the interchange carries PROPS** (format_version 2): every placement from BOTH streams cross-checked at export through `corresponds()`, model indices resolved to file ids with MFT (size, crc) identity, **the rotation composition measured** — z first, then x, then y, per-axis signs (−, +, −), 3,545/3,545 multi-axis records on a 12-map probe, closing what `props.py` had open — and Blender places every placement as a measured proxy (footprint prism or radius cylinder; placements only, NO ArenaNet model geometry, which nothing in this tree decodes). That byte-identity is the weak half by measurement — a memcpy sabotage keeps all six of those checks green and is caught only by a sculpt control. **And since 2026-08-12 the OTHER delivery route is open: the client's own map compiler builds from a Stripped stream we supply** — §35 it compiles at all and reproduces ArenaNet's bytes, §36 it compiles the stream WE write rather than anything cached, and **§38 it floods terrain we AUTHORED**: the rebuilt navmesh stops at world x = 1152.0, the cell boundary we chose, with walkable area in the steep strip falling from a measured 37.3% to 0. **Portals and multiple planes are DONE as of 2026-08-12** (FINDINGS §31, closing §8 item 10(b)) — ~~this row listed them under "What is NOT done"~~ for six days after they landed, which is exactly the staleness the top of this section is about. A portal WE authored joins two planes: `portalprop` (`plane_map [0, 0]`, **18 of 18 gates**) walked **65 s with no crash**, the bounding box opening from (0, 64)..(2048, 3072) to (0, 0)..(3072, 3072), and the client reported **plane 1 on 19 of 49** reports with **17 past x = 2048** — where the no-portal arm was pinned at x = 2048.0 and reported plane 0 on 76 of 76. The props chunk that makes plane 1 legal (6,585 B, plus 89 B of model dependencies) is **carried from row 33086 at run time and never stored**, the `mapbuild` FINDINGS 14 pattern. **The control is what makes the green arm mean anything**: `portalpropbad` (`plane_map [0, 67]`, one past `propCount`) crashed on `Assertion: index < m_count, Array.h(587)` with **`edi = 0x43 = 67`**, the value we wrote into tag 12, arriving in the register the disassembly said holds the index. The diagnosis predicted the register contents and not merely a crash. A prop index only has to be IN RANGE; prop 0 of row 33086's 67 is somewhere else entirely in the world and the client did not care. **Residuals, named in §31.4 and carried as live next-actions at §8 items 10(h) and 10(i)**: what plane 1 looks like **underfoot is untested** — nothing measured the character's z, our terrain is flat, and the prop carrying plane 1 is elsewhere in the world, so it may be walking on nothing (the interesting version of the rung is a plane whose prop IS its surface); and **one prop index was tried, not the space** (`[0, 0]` works, `[0, 67]` crashes, nothing between). **What is NOT done**: authored art (textures are borrowed retail file ids) and elevation — a height field that is not flat, walked, is still open as §8 item 10(c). That is the TERRAIN side; §31.4's untested-underfoot residual is the neighbouring question on a PROP-MOUNTED PLANE, tracked separately as 10(h), and neither answers the other; only the terrain of §38's map is ours (props, zones and collision are ArenaNet's); and the delivery path is still `datwrite` into a copied archive — which now bounds authoring to maps that SHRINK, since it writes uncompressed and will not relocate (§8.10 e9). |
| **R0b** | **Instrumented-client capture** of a real session | A live session recorded from inside a client we control, both directions, stamped `origin: live` and byte-replayable from disk | ✅ **2026-08-07**, `vault/captures/live/20260807T143055`. Six connections to ArenaNet (one auth, five game, all on **port 80**), both directions, zero TCP gaps, stamped `origin: live`, and **byte-replayable in the strong sense**: `livesession.py --assemble` regenerates all six decrypted files **sha256-identical** from `wire.jsonl` + `keyring.jsonl` alone, with no client and no network. 200,153 bytes of ArenaNet plaintext, 11,700 messages. **The independent check is the framing**: every one of the 12 streams decodes 100% clean to its final byte against `schema/messages.json`, which was built from the *client's* format tables and never from these bytes. Adversarially attacked from four angles (§3.3); three failed to refute, and the fourth's safety finding is fixed. See §3.3 for what the number does *not* mean. The pipeline is complete — key-tap cave (`keytap_patch.py`, `--key-tap`), off-wire WinDivert capture (`wirecapture.py`), memory reader (`keytap.py`), driver (`livesession.py`, wired to launch at `9cd7bca`, 2026-08-07), decrypt (`replay.py`) — and `dryrun_keycapture.py` ran it end to end against our own server, elevated, GREEN (`32c7fe1`, 2026-08-07): the off-wire ciphertext matched the server's own `.raw` byte for byte, and the tapped key decrypted it to the server's logged plaintext. The live build is staged, stock-DH and key-tapped (2026-08-07). **What is left is the live run itself, and it is human-driven by design** (§6.2, and `livesession.run`'s docstring: no scripted input, the operator plays). **Re-specified 2026-08-06 — it used to read "proxy capture", which cannot work: the channel is DH-keyed end to end and a proxy holds neither private exponent. That is the same fact that forces us to patch the client for our own server.** |
| **R1.5** | **Tape player** | A recorded StoC stream replayed at recorded timing walks a real client through Ascalon | ✅ **2026-08-10**, `fbedcfb` — **and it walked through Ascalon City itself.** The full 48.6 s tape of connection `:60935` played **1,209 of 1,209 events, 74,319 B, with ZERO messages of our own on the channel** (measured, not assumed — the previous run's assert turned out to be our own world tick talking over the recording). The client skipped the cutscene, walked to each quest giver in order, spoke to them, accepted quests, and walked to the zone exit; chat arrived. **We still cannot name half the opcodes involved** — a tape needs no semantics, which is the whole point. It ended where a one-connection tape must: at the map transition, the client dialled `54.198.7.73:6112` from the recorded `GAME_SERVER_INFO` and the cage refused it (`Code=005`). See §3.4. **A second run the same day played Lakeside County (`:64103`, 1,074/1,074, 0 non-tape sends) and rendered COMBAT** — plus a labelled c2s corpus, and independent corroboration of D1's agent-id reuse from ArenaNet's own traffic. See §3.5 and [studies/tape/FINDINGS.md](studies/tape/FINDINGS.md). |
| **R-IDENTS** | **An identifier convention for new tokens, and a resolver for the old ones** | A token met in prose resolves to its defining document in one command, and a new namespace is minted with a registered word prefix | ✅ **2026-08-20**, arc landed `f8d63a1`. The arc: [studies/idents/CONVENTION.md](studies/idents/CONVENTION.md) (the rule, and the only place it is written) + [studies/idents/HANDOFF.md](studies/idents/HANDOFF.md) (the census and the three defects — cross-arc collision, kind collision, and the same letter twice in one document). **The headline is a refusal**: a mass renumber of the existing tokens was costed and rejected as the exact shape of the 2026-08-12 provenance scrub, so nothing is migrated and every historical `C-6`, `R0a`, `H1` keeps its name. **Scope note:** the no-migration scope is owner-ratified — §7 Q8, CLOSED 2026-08-20. What landed instead: new tokens take a registered word prefix (`GATEFIRE-C3`) whose word names the *defining document* and is declared in a legend line in that document — the kind of thing a token is lives in the legend, never in the letter, because encoding kind in the letter is what produced the collisions in the first place; a resolver that works on the 80 documents written *before* the convention AND on the tokens it mints (`python toolkit/whichrung.py C-8`, plus the raw grep one-liner in CONVENTION.md §4, which is hyphen-literal and returns two of `C8`'s three row-or-heading defining sites and one of `C-8`'s — the tool returns all three and names the ambiguity, and a fourth definer, a bold list-lead in `studies/combat/PLAN.md`, sits outside both patterns, which is why every count is a floor); and an accumulation tripwire, `toolkit/identlint.py` + `test_identlint.py`, explicitly **not** a hard gate — provlint's posture, for provlint's reason. Two side findings: the R-ladder drift between `PLAN.md` §3 and `HANDOFF.md` was closed by **annotating in place**, not syncing (`HANDOFF.md:116`) — re-syncing two copies only resets the clock, and the `R0`→`R0a`/`R0b` split turned out to *vindicate* that document's own headline call; and the bare-integer commit-subject prefix (`29:`→…, defined by no document — no count is pinned, it grew by one between census and landing) is **retired** with its meaning recorded rather than rewritten. Census counts are floors: the widened re-run found several times HANDOFF §2.1's 108 defining sites, and quoting any number bare is refused — ask the tool. |

| **R-ISLE** | **The Isle of the Nameless as a calibration range** | Rungs per [studies/isle/PLAN.md](studies/isle/PLAN.md): reader, route, offline bench, loopback probes, plumbing, then the live sessions | 🔶 **rungs 1-5 DONE 2026-08-16/17**, landed `f17cd49`. The arc: [studies/isle/HANDOFF.md](studies/isle/HANDOFF.md) (**start here cold** — the traps, not the status) + [studies/isle/PLAN.md](studies/isle/PLAN.md) (the north-star doc: instruments, skeptic-attacked designs, the ladder) + [studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) (rung 3's eight offline answers; rung 4's four operator-confirmed probe results). Headlines: the AoE radii are static (`s_skill +0x6C`: adjacent 156 / nearby 240 / in-the-area 312, +10-16 bounding-radius hypothesis for the Isle markers to test); the Master of Damage's chat numbers are extractable AND rendered ("is now level 17!" on our own client — 0x5D needs its 0x5E tag); the enc_name → nameplate route is PROVEN (station 1470 = the Ascalon City outfitter, operator-read); conditions map 478=Bleeding..486=Weakness (+2077) with degen server-owned; the three damage kinds separate on the client bar (16/17 debit, 18 notifies); `agentroster.py` reads any capture into cross-session-stable stations; `map.280` is in content with the 0x0195 prediction pre-registered; a PvP-only character reaches 280 (owner-confirmed, GWW-corroborated — the ONE PvE area they may enter). **rung 6 is DONE 2026-08-17/18** across two live captures — `20260817T231139` (the island west and centre; 15/15 connections after the manifest-writeback fix) and `20260818T094648` (the east line, 5/5). Both `game_mode base`, `exe_unchanged: true`, seals AGREE. Results: `0x0195` field 1 = **165811 six times**, and it is a TERRAIN-FILE id shared with map 248, not a per-map id — the whole message is now decoded in [studies/mapload/FINDINGS.md](studies/mapload/FINDINGS.md) (7 fields, 30 loads, both builds; settles `studies/tape` §1.2, corrects a `0x0084EE83` misattribution in `studies/enemy`, and moved `map.280`'s spawn to retail's arrival position); field 2 is the arrival position, byte-identical across all Isle loads; **7 of 10 pre-registered missing definition indices** were found in the unwalked east (130, 139, 146 still unseen); the east holds the **skill-bar foe Masters with their pets and spirits** — level-0 model-less bodies with churning agent ids beside a level-20 owner, matching three separate pre-run wiki claims on profession, level and summon structure at once; the **Students** came out 10 bodies over 10 consecutive slots split exactly 5 ally / 5 foe; and the range ladder is closed (10 rungs, byte-identical across visits, ±12.4 u). Which body carries which NAME is NOT recoverable from a capture — the `enc_name` render is the only route, and a claim identifying one was withdrawn under adversarial review. **RUNG 7 IS DONE 2026-08-18** — capture `20260818T132739`, 9/9 decrypted, seals agree, 495 damage events, then five independent agents (one blind re-derivation, one wiki sourcing, two adversarial, one on the chat oracle) sent at the results. **The armour exponent B9 called NOT REACHED is now reached, and the whole outbound damage formula with it**: `points = round(roll × 1.20 × 2^((SL − AR)/40))` with SL = 5·rank to 12 then +2 per rank, pinned by a **band test with zero free parameters** (AR60's support fixes the scale; AR80 → 13..19 and AR100 → 9..14 follow exactly). The mean-ratio fit gives D = 39.5, 95% CI **[37.30, 42.00]** — containing 40 at −0.8σ/−0.1σ, and it must never be quoted bare, which is the review's sharpest correction. **`GV_CRITICAL = 17` is CONFIRMED**, ending a CONTESTED row: 10/10 blocks zero-variance over 100 events, one multiplier fitting nine blocks inside a 0.83% window containing √2, p16+p17 = one event per swing (so 17 REPLACES 16), and crit rate rising monotonically 6%→34% with attribute rank. **The Master of Damage oracle worked**: its announced total 1496 equals our independently summed integer points exactly and *selects* H=590 out of the fraction grid's `{590k}` family — a check that could have failed. **Gate 1's attribute channel is measured at last** (`0x0037 [agent, unspent, 200]`, `0x003A` column-major base|effective ranks, `0x003B` per-change, `0x0038` the debit): the +1 rune bonus is visible on the wire, damage uses the EFFECTIVE rank, and the point budget closes two unrelated ways to cum(12) = 97. **Four claims were corrected or refuted by the review and all are recorded**: the unmet-requirement `/3` is REFUTED at 3.5% with no replacement permitted (the rank-8 crit is a disjointness, not a rounding miss — the one open defect); the rank-kink ratio is statistically worthless (95% CI [−17, 24]) and is replaced by ratios of means at −0.8σ/+0.3σ; "continuous roll" is downgraded to "≥ ~40 steps"; and the 1496 line is an end-of-combat auto-report, not the `/bow` response (`/bow` is 4.46 s later). Full record: [studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) "Rung 7, LIVE #2". **Rung 8 PREP DONE the same day, and its exit criterion was MET OFFLINE** ([studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) "Rung 8 prep"): the design expected a refutation because `0x0042` had zero ArenaNet witnesses, and the corpus in fact holds **97 applies + 88 removals**, with `0x0044` closing `0x0042` at apply+duration to the millisecond. **Field 3 is the applier's ATTRIBUTE RANK** — confirmed on four skills against GWW progressions (Windborne Speed at the Master of Winds' 15 Air Magic → 13 s; `"Charge!"` at the operator's own Tactics 10 → 10 s; Pin Down's Crippled at rank 13 → 13 s; the environment torches at rank 0 → fixed 30 s) — so the two conditions where it equals the duration were arithmetic accident. **Hexes and enchantments, §3.3's "largest single miss … no instrument at all", were already captured and merely unidentified**: skill **984 = Torch Enchantment** and **998 = Torch Hex**, 30 s each, matching GWW's effect ids exactly. And the repo's **first cure** is on record — `"Charge!"` stripping Crippled in the same millisecond, its 33% speed boost visible as 288 × 1.33 on `0x0027`. Consumer built first again: `toolkit/authsrv/bufflog.py` (36 checks) reads episodes as EXPIRED / STRIPPED / OPEN and refuses to attribute an effect outside a mark window, since `0x0042` carries no source agent. **The live session is staged** (`vault/plans/isle_rung8_effects.txt`, 27 steps) for the four things the corpus cannot give: skill **999** (the degeneration torch, never captured), the five foe Students' condition ids, degeneration in pips against GWW's 3/4/4/7, and the rank ladder that closes rung 7's open defect. Prep detail: the consumer `toolkit/authsrv/damagepass.py` built and proven on retail bytes first — the rung-6 detour's PvP arenas turn out to hold the vault's largest damage corpus (641 p16 + 119 p17), which measured the attack-skill confound (10 of 11 arena p17 groups nonzero-variance) and recovered 480 = level-20 base health from a fraction grid; the bench geometry is recovered (Suits 152/153/154/152 in a row, the 60-pair predicted at its ends; MoD prof-6 candidates 144/145); the sealed-plan draft with every prediction pre-registered (including both weapon-type branches for the rank sweep) is staged at `vault/plans/isle_rung7_damage.txt`; and the blocking behavioural-cap question was ruled same-day — **§7 Q7, the cap is STRUCK** — so **the run itself is next and is the operator's**: RUNBOOK live procedure + `--minutes 45 --mode base --plan vault/plans/isle_rung7_damage.txt`. Bonus banked en route: the no-combat east run's one combat episode (operator hit by slot 137's Pin Down) shows **condition application arriving on `0x0042` on retail traffic** (481 Crippled, 13.0f duration-like arg, move speed halved server-side) — rung 8's Torches-first channel question observed once, early. Residuals riding the next loopback pass: the varint send, the overhead channel, skill 2077's render, the energy probe. |

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

### 3.6 The loopback opcode sweep — 334 of 487 GAME_SMSG opcodes measured

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

**IN PROGRESS 2026-08-13 — reading the OTHER channel, the screen.** `SILENT` means *no
c2s reply* and is blind to anything the client draws, so the 239 SILENT rows are unread
rather than empty. `toolkit/authsrv/shotloop.py` re-sends each one to a FRESH client with
screenshots through the hold, and `toolkit/authsrv/shotlabel.py` joins the send to the
frames that bracket it and builds a local page (vault only — the frames are the retail
client) where a person types the name. **One opcode per client launch**, owner's call: a
window an earlier opcode opened is still on screen when the next lands, so it sits in the
next opcode's own baseline. ~40 s each, ~2.5 h for the set; `score_run` refuses a
multi-send run outright. Controls in `test_shotlabel.py` (33 checks).

**And it found the defect that had been silently wrecking harness runs.**
`session.Stack._pump` is the only reader of a server's stdout pipe. One gamesrv line
carried U+FFFD — our own `string16` replacement character — the print raised
`UnicodeEncodeError` against a cp1252 console, the pump thread died, the pipe filled, and
the gamesrv **blocked forever on its next print**. The probe sent nothing. The run still
reported **RUN VERDICT: PASS**, because the one send that kept working is the 20 Hz world
tick — the only send in the server that does not print — so the capture filled with 649
plausible events while three opcodes were recorded as run. `checks.py` had written this
lesson down for tests in 2026-08-06 (`_say`, after `test_textrec` died the same way); the
harness never got it, and it is the one place the failure blocks a SERVER rather than
ending a script. Fixed, and `shotloop` now records an opcode only when the run's own
capture holds its send.

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
  10 map rows and 56 NPC rows** (`toolkit/content.py`'s own census, re-run **2026-08-14**:
  map 10, npc 56, item 1, spawn 4, area 3, attack_speed 1, player 1 — was map 9, npc 2,
  item 1, spawn 1 on 2026-08-11). **Read the NPC figure carefully before scoring R4c-1
  against it**: only **2** of the 56 are tracked in `content/npcs.toml`; the other **54**
  are the gitignored `vault/content/npcs.toml` overlay `npcdefs.py` emits, and they carry
  `level = 0` placeholders with no name, armor, energy or allegiance (that module's own
  header says so). So the "≥15 NPC templates" bar is met on the count and **not** on the
  content, which is the distinction this criterion exists to force. Every map row carries a `file_id` and a `spawn_x`/`spawn_y`; **how many
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

~~Layer the shadow-server idea on top once capture works: feed your server the real CtoS stream and
diff its would-be output against the real server's while still forwarding the real answer. That is
HANDOFF §7's replay oracle at R0 instead of R2, open-loop, self-updating as you play. Then stop
forwarding message types that diff clean and answer them yourself, so the system stays playable
throughout and the project becomes incremental replacement rather than a cold start.~~
**❌ STRUCK 2026-08-13 with HANDOFF §7, which it depended on.** The byte-diff at its centre is
refuted by its own subject: **ArenaNet's server is 0.2% byte-identical against its own recording**
of the same character on the same map minutes apart, diverging at message 6, while the same method
scores 99.3% on opcode *sequence*. A gate that cannot go green cannot go red for a reason, and its
tolerance layer is vacuous by its own control (masking three dwords blanks 45% of bytes and still
scores 76.8–97.5% on *different* maps). The prize is already banked by §8's `msgmix.py` and
`studies/divergence` D1–D11, which is what the shadow diff was for. See HANDOFF §7 and
[studies/recon/FINDINGS.md](studies/recon/FINDINGS.md) §5.5 for the measurement and for the
structural load-prefix gate that replaces it. **The rest of A1 stands** — capture was and remains
the right first move, and R0b/R1.5 are met.
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
  ~~First shadow-server diffs on real traffic.~~ **Struck 2026-08-13** — see §4 A1 and
  HANDOFF §7; the byte-diff is refuted and `msgmix.py` already delivers what it was for.

Capture still starts immediately and never stops — the wasting-asset argument is right. What
changes is that capture is now cheap enough to leave running rather than a project in itself.

---

## 6. Risks and hedges

| Risk | Hedge | Cost |
|---|---|---|
| A prior-art repo disappears | **Already happening** — `gwdevhub/gw_in_browser` 404s today while `gwnative` still names it upstream **[measured]**. `toolkit/mirror_priorart.py` clones the field into `vault/mirrors/` with a manifest recording each HEAD; run it monthly. | done |
| Service closes or changes | Record every live session from inside the instrumented client; zero marginal cost once built. *The hedge is unbuilt, so the risk is currently unhedged — and this row said "leave the proxy on", which was never a thing that could exist (§3 R0b).* | hours |
| **Client auto-patches over ground truth, and the DH keys rotate with it** | **This happened during the session that wrote this document.** The updater replaced `Gw.exe` (10,404,032 → 10,483,904 bytes) and `Gw.dat`, moved the DH struct from RVA `0x6843e8` to `0x6910d8`, and **changed both the prime and the server's public key**. ArenaNet rotates the Diffie-Hellman parameters per build — which is why Headquarter stores 107 server keys rather than one constant. Consequences: the client patch is a permanent recurring step, not a one-time one; every capture and schema revision must carry a build id (free, per §2); and re-snapshot *before* accepting an update prompt, never after. Both builds are now vaulted. **COSTED 2026-08-12, [studies/crossbuild/FINDINGS.md](studies/crossbuild/FINDINGS.md): 64 build-coupled addresses in `toolkit/`, 7 files** — not the 409 one draft claimed nor the 30 §1c of the review estimated, both of which reproduce under no stated method. **28 are converted** and re-verified against both vaulted builds by tests — `msgshape`'s 25 tables, `asserts`' callee, and `avevents`' two allocators, the last of which are now located by ArenaNet's own `AvChar.cpp` asserts rather than by address; **30 are GATED** — `genericvalue.py`'s 27, which read their jump tables out of the instruction that jumps through them and REFUSE on a build they were not measured on (exit 2, not a traceback), and the 3 RVAs in `itemprobe`/`agentprobe`, which dereference into a *running* client and refuse unless the target hashes to the right build; **5 are ACCEPTED**, hash-scoped facts about our own patch. **Zero outstanding: the per-update cost of this surface is now nil** — every site either re-derives or refuses, and none can return a silent wrong answer. What still recurs is not in the census: the DH parameters rotate every build, so the client patch is permanent, and the schema and captures still need a build stamp. The recurring cost that no census can see still dominates: the DH parameters rotate every build, so the client patch is permanent. | **68 addresses, 37 outstanding, 3 jobs** |
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
| **opcode NAMES in `studies/newopcodes/`** | `gwdevhub/GWToolboxpp` → `Dependencies/GWCA` — its `GAME_SMSG` name table, read as one of two witnesses beside OpenTyria | MIT — attribution required if we ship any of it | ⚠️ **promoted out of `NO_DERIVATION` 2026-08-17.** That row said "nothing taken", and on 2026-08-17 the decode pass took something: 14 of 22 opcode NAMES rest partly on this table. Nothing in `toolkit/` uses it yet — it is cited in a study, always labelled UPSTREAM and always beside ldufr. **The moment a name lands in `schema/overrides.json`, this needs a `THIRD-PARTY-NOTICES.md` entry**; MIT asks for that and the register is where we notice. See the mirror-trap note below: cite the MAINTAINED path, never the two archived copies. |
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
| `toolkit/mapdata/modelfile.py` — the **prop model geometry** layout and the FVF stride tables | GuildWarsMapBrowser (its FVF tables and model reader) — **not taken**; recorded because the arc ran alongside it | same custom licence as the rows above | ✅ row added 2026-08-13 with rung M2, and it is the row where **upstream turned out to be RIGHT and we were wrong**. Nothing is taken: the three stride tables are read out of the client's own `.data` (VA `0x00BF5B80`/`BC0`/`BE0`, accessor `0x00688010`) by this repo's own PE walk, and `test_modelfile.py` §5 re-reads them from the vaulted image so the module's literals are pinned to ArenaNet's bytes. GWMB's tables **are** those client tables. The point worth recording: [studies/customarea/FINDINGS.md](studies/customarea/FINDINGS.md) §B6 logged our corpus-fitted byte-cost rule "disagreeing with GWMB's table once (`dat_fvf 0x2C`)" as an open question and every prior row in this register describes upstream as a witness *we* corrected — here the client corrected **us**, `0x2C` never existed, and the cross-file oracle went 0/16 → 16/16 on the affected model. See [studies/models/FINDINGS.md](studies/models/FINDINGS.md) §2. |
| `toolkit/mapdata/modelfile.py` — the **skin binding**: `SubModel.trailing` split into `groupTransformCount[u0]` + `transforms[u1]` + a `u2 × 12` block, and `dat_fvf` bit 1 read as the per-vertex group selector that resolves through them | **GuildWarsMapBrowser, and it DOES have this — but nothing is taken.** The maintained fork `Jonathan-Greve/GuildWarsMapBrowser` @ `fcb8f34f` decodes the FA0 trailing block (`FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat`'s `SubmeshHeader_FA0`/`SubmeshData_FA0`; `SourceFiles/Parsers/BB8GeometryParser.h`'s `FA0GeometryParser`/`BoneGroupData`). **Ours is derived from the client and the archive**, and ArenaNet names every field: bit 1 is `GR_FVF_GROUP` (`MdlCombine:2073` at `0x007A685E`, `GrGeo:738` at `0x0065AA8F` — two independent modules), `sum(groupTransformCount) == transformCount` is **ArenaNet's own assert** (`MdlCombine:860`), and bit 3 is `GR_FVF_DIFFUSE`, absent from all 49,026 sub-models because `MdlCombine:2075` at `0x007A6898` asserts it must be. | same custom licence as the row above — permissive, **requires a repo link and visible credit**, *not* MIT | ✅ row added 2026-08-19 **before the decode landed in the module**, the fourth rung running to meet [studies/archivewrite/FINDINGS.md](studies/archivewrite/FINDINGS.md) §2.2's obligation. **Recorded because the expected answer was wrong**: the brief predicted NOT FOUND across every lineage, and NOT FOUND is right for gw-preservation, Py4GW_Reforged, OpenTyria, Headquarter and Fournux — but not for GWMB, and **not for the ARCHIVED `gwdevhub/GuildWarsMapBrowser` fork, which has none of it**. That is the GWCA mirror trap in a second lineage: cite the maintained path or report NOT FOUND for something that exists. Upstream is a **witness, not an authority** here — its hexpat agrees with the client, but a skeptic checked its narrower palette reading against the archive and the group reading is what survives. |
| `toolkit/clientscan/textrec.py` — the **string-id split** `file = id // 1024, rec = id % 1024` | Fournux/Tyria-Extractor (`doc/SKILL_EXTRACTION.md`, mirrored at `vault/mirrors/Fournux__Tyria-Extractor`) | **MIT** — permissive, attribution required | ✅ row added 2026-08-17, credited in `THIRD-PARTY-NOTICES.md`. **This is the one rule in the repo taken from an upstream and NOT re-derived** — the module's own docstring says so in those words. What makes it defensible is not a second reading but an ORACLE: `textrec.py --dat … 1 2 7 …` resolves ids to words, and the words are right. That is a check the artifact can refute, and it is stronger than agreement with the source it came from. Re-deriving the split from the client's own indexing code would retire the dependency; nobody has. |
| `toolkit/clientscan/skilltable.py` — the **skill record layout** (0xA4 stride and its field offsets) | Fournux/Tyria-Extractor `doc/SKILL_EXTRACTION.md` | same | ✅ row added 2026-08-17, same notice. **Read and re-derived, not copied** — the module locates the table by a four-way conjunction (stride, count, id monotonicity, profession/equip ranges) that a false positive would have to satisfy all of, and `test_skilltable.py` scores 1,333 base rows against Tyria-Extractor's independent count *and* against the wiki's 1,329 player skills. Two unrelated methods, so the agreement is corroboration rather than one witness twice. |
| `toolkit/mapdata/gwentropy.py` — the **meta-coder tables** (`CODE_LENGTH_THRESHOLDS`, `CODE_LENGTH_SYMBOLS`) read in the ENCODE direction | GuildWarsMapBrowser `SourceFiles/xentax.cpp`, reached through this repo's own re-derivation in `toolkit/mapdata/gwdat.py` | same custom licence as the `gwdat.py` row above — permissive, **requires a repo link and visible credit**, *not* MIT | ✅ row added 2026-08-18 **before the module existed**, which is what [studies/archivewrite/FINDINGS.md](studies/archivewrite/FINDINGS.md) §2.2 asked for and what the `gwdat.py` row itself never got. The module **imports** those constants rather than re-transcribing them and takes **nothing new** from upstream — but it reads them in the direction upstream never wrote. That direction is the point: the archivewrite scouts checked all five mirrored lineages (GWMB `xentax.cpp`, gw-preservation `binutil/huffman.go`, Fournux `gw_dat_decompress.rs`, OpenTyria `FaCompress.c`, Headquarter `docs/compress.c`) and **every one declares decode only — NOT FOUND, nobody upstream wrote the inverse**. So the cost model is ours and the tables are theirs, which is exactly the split this register exists to record. `THIRD-PARTY-NOTICES.md`'s GWMB entry names the modules; extend its "Used by" list in the same commit as the module. |
| `toolkit/mapdata/gwmatch.py` — the **LZ77 matcher** for compression 8 (rung A7a), and the format parameters it must match against | **Algorithm: nobody's.** A hash chain over 3-byte prefixes with lazy matching, a `good_length`/`nice_length`/`max_chain` quality dial and a greedy-below-level-4 split is ordinary published technique, and the *design* followed is **deflate's** — RFC 1951 and the shape of zlib's own configuration table, read as prior art from the public description and re-implemented, with no zlib source consulted, no code ported and no constant copied (our preset numbers are ours and are named in the module). **Parameters: upstream's, and already covered.** `LENGTH_BASE`, `LENGTH_EXTRA_BITS`, `DISTANCE_BASE`, `DISTANCE_EXTRA_BITS` — from which min match 3, max match 258, the 285-symbol literal/length alphabet, the 30-symbol distance alphabet and the 32,768 window are all *read* rather than chosen — are **imported** from `toolkit/mapdata/gwdat.py`, which derives them from GuildWarsMapBrowser `SourceFiles/xentax.cpp`. | same custom licence as the `gwdat.py` and `gwentropy.py` rows above — permissive, **requires a repo link and visible credit**, *not* MIT | ✅ row added 2026-08-18 **before the module existed**, as the sibling of the `gwentropy.py` row directly above and for the same reason. **Nothing new is taken from upstream**: the module re-transcribes no table, and the two tables `gwentropy.py`'s row is about (`CODE_LENGTH_THRESHOLDS`, `CODE_LENGTH_SYMBOLS`) it does not touch at all — it reaches the cost model through `gwentropy` rather than through `gwdat`. What is worth recording is the same split that row records, from the other side: **upstream supplies the alphabet, deflate supplies the search, and the encode direction is still ours** — all five mirrored lineages declare decode only, so no upstream has an LZ77 *matcher* for this format to take. The four parameter tables were additionally **confirmed against retail's own emitted token stream** before a line was written (row 11196: observed match lengths 3..258, distances 1..32,766 with none exceeding the bytes produced, literal/length symbols up to 284, distance symbols up to 29, and 691 genuinely overlapping matches), which is corroboration from the artifact rather than from the source the tables came from. `THIRD-PARTY-NOTICES.md`'s GWMB entry names this module. |
| `toolkit/mapdata/gwenc.py` — the **bitstream writer** for compression 8 (rung A7b): the inverse of `gwdat.BitReader`, of `gwdat.build_table`'s meta-token walk, and of its canonical code assignment | **The bit layer is upstream's format, read backwards.** Three things are inverted from `toolkit/mapdata/gwdat.py`, which derives them from GuildWarsMapBrowser `SourceFiles/xentax.cpp` (Copyright (c) 2023 Jonathan Bjørn Greve): (1) the **meta-coder tables** `CODE_LENGTH_THRESHOLDS` + `CODE_LENGTH_SYMBOLS` — this module builds the *emit* table `index → (bit_count, bit_pattern)` by inverting `build_table`'s band-selection arithmetic, which is the same pair `gwentropy.py`'s row is about, now used to write bits rather than to count them; (2) the **canonical code assignment**, `build_table`'s `next_bits` walk counting DOWN from all-ones, reached through `gwentropy.canonical_codes` and never re-transcribed; (3) the **bit order** — 32-bit little-endian words, MSB-first within a word — read off `BitReader.__init__`/`peek`/`consume`. The four LZ77 parameter tables reach it through `gwmatch`. **Nothing is re-transcribed: every constant is imported from `gwdat` or `gwentropy`.** | same custom licence as the `gwdat.py`, `gwentropy.py` and `gwmatch.py` rows above — permissive, **requires a repo link and visible credit**, *not* MIT | ✅ row added 2026-08-18 **before the module existed**, which is the obligation [studies/archivewrite/FINDINGS.md](studies/archivewrite/FINDINGS.md) §2.2 names in those words ("its `PLAN.md` §6.1 register row must exist BEFORE the module does"), and the third rung in a row to meet it. **What is taken and what is ours, stated plainly.** *Taken:* the format itself — the meta alphabet, the code-assignment rule and the word/bit order are ArenaNet's design as recovered by GWMB, and this module could not exist without that recovery. *Ours:* **the encode direction, which no upstream wrote.** All five mirrored lineages (GWMB `xentax.cpp`, gw-preservation `binutil/huffman.go`, Fournux `gw_dat_decompress.rs`, OpenTyria `FaCompress.c`, Headquarter `docs/compress.c`) declare **decode only — NOT FOUND**; there is no `BitWriter`, no table serializer and no compressor in any of them to copy, and the inversions above were derived here from the decoder's own arms. Note the honest limit on how much that direction is "ours": inverting a bijection is not invention, and the strongest evidence this module produces — **byte-identical re-emission of retail's own rows** — is precisely evidence that we hold *their* layer correctly. **The retail client itself is a separate matter and is NOT an upstream this row covers**: its own assert strings (`CmpApi.cpp:81/102`, `CmpDict.cpp:438/467`, `CmpHuff.cpp:158/159/504/511`) say ArenaNet ships a compressor, but no byte of it is read, disassembled or derived from here — that would be a provenance question (`CLAUDE.md`'s first gate), not a licence one. `THIRD-PARTY-NOTICES.md`'s GWMB entry names this module; its "Used by" list was extended in the same edit. |
| **monster AI: aggro radius, leash, scatter, targeting, formation, patrol** — *no module takes these yet* | GWW (`wiki.guildwars.com`), the pages named in [studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md) §4 with revision ids | GFDL 1.2 / CC BY-NC-SA 2.5 (dual) — **attribution required**, and the NC arm is satisfied by this project being local and personal (`CLAUDE.md`) | ✅ row added 2026-08-11 **before any module takes any of it**, which is the first time this table has been used the way it was designed rather than retrofitted. **The split that matters is values vs. algorithms.** The gwinch table (aggro bubble/earshot 1012, touch 144, casting 1248, longbow 1498, compass 5020 …) is a set of *values* and reaches the repo as `content/*.toml` rows carrying `source = "wiki"`, which `toolkit/content.py` already gates. **Scatter, leash, target priority and the melee-surround formation are *algorithms*** and are what this row exists for — none has landed, and none may land without citing it here. **Currency is the failure mode, not licence**: three of the four core pages carry `Category:Unofficial terms`, *Foe* has not been revised since 2021 and *Patrol* since 2017, the wiki **contradicts itself** on target priority (§4.3), and where a stale page and a fresh one disagree the stale one was wrong both times. So every borrowed row records its revision id, and a value our own artifacts can check is checked rather than adopted. |

**A MIRROR TRAP THAT COST FIVE AGENTS AN ARGUMENT EACH, 2026-08-17.** The vault holds
**three** GWCA copies and they do not agree. `GregLando113__GWCA` and `JaborGW__GWCA` are
**archived**; `gwdevhub__GWToolboxpp/Dependencies/GWCA` is the **maintained** fork.
Measured first-party over both full `GAME_SMSG` tables (217 names each): **31 names
identical up to `0x003B`, 186 at maintained = archived + 1 from `0x003E` up, zero other
deltas** — the maintainers inserted one opcode and everything above it moved. During the
`studies/newopcodes` pass five agents independently "derived" a +1 shift for OUR numbers,
each building a case for it, one across three anchor pairs. **There is no shift.** Read
against the maintained fork or against OpenTyria, our opcodes sit at **delta 0**, which is
exactly what `studies/msgtable/FINDINGS.md` measured on all four channels and said in
terms. Cite the maintained path; if you cite an archived one above `0x003B`, say which and
expect to be one out. The three mirrors are all still worth keeping — an archived copy is
the only record of what the field believed at that time — but they are not interchangeable.

**Three further Fournux citations owe NO row, and they are recorded here because an audit that finds 100+ mentions of one upstream should not have to re-decide each.** `toolkit/mapdata/gwdat.py` cites `DECOMPRESSION.md:26` as a SECOND WITNESS for the truncation-length reading we measured ourselves (its own row is GWMB's, and stands). `toolkit/clientpatch/repoint_skill.py` cites Tyria-Extractor as one *side* of a three-way CONTESTED icon-slot reading that we then settled by repointing one field and looking at the bar. `toolkit/mapdata/test_datwrite.py` read its fixture generator and took nothing — its docstring says so and says why ("it reads the entry fields differently than we do"), which is the discipline working rather than an omission. **Citing, verifying against, and disagreeing with an upstream are not derivation.**

**Why this row was four days late, and it is the register's own failure mode.** `studies/reconstruction/FINDINGS.md` §9.3 flagged the missing Fournux row on 2026-08-13; `studies/quests/FINDINGS.md` §7.9 flagged it again on 2026-08-15 and `AUTHORING.md`'s rung Q1b made it a precondition. It still took until 2026-08-17, because **the flag lived in study documents and the obligation lives here** — and `PLAN.md:33`'s prior-art landscape table, which grants nothing and is not this register, reads enough like a row to have been mistaken for one at least once (`studies/quests/AUTHORING.md` §7 records that killed answer). The general lesson is the one §6.1 opens with: the rule was in the plan and nothing was checking. That is now `toolkit/derivlint.py`.


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
  it loses almost nothing. **(This bullet was REFINED the next day and must not be read alone —
  see "REFINED 2026-08-12" three paragraphs down: the refusal is aimed at BULK, and a single
  assert cited as the evidence for one claim is a measurement. Reading this bullet on its own is
  what cost 46 hand-rewritten citations, and it had a live route back in via `toolkit/content.py`
  until 2026-08-16.)**
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

**Q7. Does the monsterai behavioural cap (3 approaches per creature type per session, no
repeated spawn visits) bind the Isle's damage pass?** ✅ **CLOSED 2026-08-18, by the owner:
STRUCK ENTIRELY.** *"As long as the runs are human-driven it's not suspicious at all to kill
the same enemies over and over."* The cap was `studies/monsterai/FINDINGS.md` §7.6's own
operationalization of the traffic-pattern rule for AI-probing campaigns — its number never
measured, never the owner's rule — and its sibling ("at most one session per day") had
already been struck on exactly those grounds in §7.7.2, where the cap itself survived
unchallenged. It is now struck the same way, everywhere, not merely scoped off the Isle.
**What governs instead is the general behavioural rule, unchanged and sufficient**: human
cadence, human hours, one client, hand-driven, never in a competitive context. §7.6's
per-question STOPPING rules (fixed in advance so nothing is rationalised into agreeing
afterwards) are statistics, not behaviour, and stand. This unblocked the rung-7 plan
(`vault/plans/isle_rung7_damage.txt`), which was header-blocked on this ruling per
`studies/isle/PLAN.md` §6's cross-cutting question.

**Q8. Does the identifier convention's scope stay "new tokens only" — no migration of
the existing corpus?** ✅ **CLOSED 2026-08-20, by the owner: YES, new identifiers
only.** This ratifies the ruling `studies/idents/HANDOFF.md`'s top box made and the
arc adopted at landing (§3's `R-IDENTS` row): nothing is migrated, every existing
token (`C-6`, `R0a`, `H1`, …) keeps its name in the documents, the commit messages and
the owner's own memory, and a mass rename is refused as the exact shape of the
2026-08-12 provenance scrub — 46 rewrites, all reverted, the record Q3 carries. The
handoff's decision 1 asked for this yes explicitly because it is the decision that
priced the arc at an hour rather than two days; the arc landed on the refusing,
cheap-to-reverse direction, and both PLAN rows carried a "not yet recorded" note until
this row closed it. [studies/idents/CONVENTION.md](studies/idents/CONVENTION.md) is
the convention; reversing this ruling is the two-day migration it declines.

---

## 8. Immediate next actions

### Outbound damage is REAL — the armour term, the critical, and the numbers on screen (2026-08-20)

[studies/isle §2, §4, §4.1](studies/isle/FINDINGS.md), `studies/combat` F3. Landed
`abd9910`, `2b57034`, `2173584`, `89609f5`, on top of the same day's `611417b`
(armour rating) and `31c79df` (weapon damage).

**The formula was derived on 2026-08-18 and sat unused for two days.** `studies/isle`
rung 7 read the outbound damage model off 495 live damage events, and `GV_CRITICAL = 17`
was CONFIRMED in the same run — while `hit_enemy` rolled a number and sent it straight
through. Both are now in the swing:

```
points = round( roll * mult * 2 ** ((SL - AR) / 40) )
SL = 5*rank to T, then 5*T + 2*(rank-T),   T = (level+4)/2
critical: the range MAXIMUM, at AR - 20
```

**THE CHECK HAS NO FREE PARAMETERS.** Feed the implementation the rung-7 character's
own weapon (customized 15-22), her rank (13) and the three armour ratings her fight was
measured against, and it must land on the point bands retail produced. It does, at all
six endpoints — `AR60 → 19..27`, `AR80 → 13..19`, `AR100 → 9..14` — and the critical
lands on **39, not 38**, which pins the rounding rule the study rules `floor` out on.
The bands came off retail traffic and nothing here was tuned to them.

**Then the client drew it.** Capture `20260820T162204`: the server's stream and the
client's floating numbers agree swing for swing (`-5`, `-7`, `-9`), 15 swings killed the
100 HP practice target, and the distribution matched the offline model exactly. A second
run caught the critical: **`-12`, in the same yellow, font and float as an ordinary
hit** — so `17 REPLACES 16` is true of the rendering too and nothing marks a critical as
special (isle §4.1). That was worth photographing because the opposite was plausible.

**Creature armour is DERIVED, after a picked 60 was the wrong SHAPE.** 60 is the Isle's
own Suit baseline, which is why it was picked, and it is level-20 armour on a level-1
creature — the failure `studies/monsterai` §3.3 already records for reach. WIKI (GWW
"Armor rating") gives `AR = 3*level + profession bonus`, the bonus read off a *second*
page's level-20 maxima, so the test makes two wiki pages cross-check each other through
our arithmetic. Our level-1 Monk Hatcher derives to **AR 3**, and the fight went from
~35 swings to ~14.

**Three corroborations fell out unsought**, all from GWW pages fetched for something
else: its damage-multiplier table is `2^((60-AR)/40)` to three decimals — the divisor
the Isle measured, arrived at independently by players; "60 is the baseline" is the
assumption the band test already rested on; and Warrior armour "25...80 with Armor +20
(vs. physical damage)" is exactly what our five starter pieces decode to.

**What was deliberately NOT copied**, because the study's scope is narrow and this is
the wiring rather than the claim: the `1.20` (that character's own `Damage +20%` and
customization, which the fit cannot separate — ours is 1.0); a second crit multiplier
(it is an armour reduction, expressed once, since `2^(20/40) = √2` makes "×1.414" and
"at AR−20" one statement); and any unmet-requirement penalty (REFUTED at 3.5%, with the
study forbidding a replacement in terms). Crit RATE is the five measured ranks;
`critical_rate` interpolates between them and clamps outside, both labelled OURS.

**The harness can order a swing now, and that was the blocker.** Watching a damage
number needs the player to swing; the player swings on `0x0026 ATTACK_AGENT`; the client
sends that on a click at a HOSTILE — the world-anchored click `control.py` says this
harness cannot aim. `interact:` could not stand in (its server arm is the NPC dialog
path and never begins an attack). So `control.py` gained a second slot and `attack:` is
both an action and a **walk verb** — the latter because actions all fire before the
walk and the hold while `--shots` photographs only those two, so a fight ordered from
the action script can finish unphotographed. Measured, not reasoned: a critical landed
at 20:11:39 and the first hold frame was stamped 20:13:58, **139 s later**. Anchoring
frames by TIMESTAMP rather than filename is what caught it.

**NEXT, in cost order:**

1. **Nothing reads the PLAYER's armour.** Five pieces carrying `Armor: 25` and
   `+20 vs. physical` go out and no incoming damage term consults them — the enemy's
   swing is still `ENEMY_HIT_FRACTION`, a flat 10% of the player's pool. The formula is
   already written and symmetric; this is applying it in the other direction, plus the
   per-slot hit-location table GWW publishes (chest 3/8, legs 2/8, the rest 1/8).
2. **SL uses level 20 while the body is level 1.** Defensible only because the
   character also carries a 200-point attribute budget, which is ours — but it is an
   assumption, not a measurement, and the cheapest thing here for a capture to overturn.
3. **The unmet-requirement term stays unmodelled** and should stay that way until a
   capture separates the divisor from SL. `studies/isle` §2 bounds both and forbids
   publishing a replacement; the rank-8 critical is the same defect's sharpest face.
4. **`--practice-target` is doing two jobs** — it stops the creature attacking *and*
   stops it moving — so a fight watched this way is never a fight that moves.

### Hero AI: the client holds NONE of it, and the wiki holds more than expected (2026-08-20)

[studies/heroes §5.5, §5.6](studies/heroes/FINDINGS.md). Landed `7df1dce`, `d037bc5`.

**Asked directly, because §4 answers the skill bar and §5 answers the wire and neither
answers this.** `studies/monsterai`'s negative is total but it is about MONSTERS, and
GWW says "heroes and henchmen share the same AI" while saying nothing about
hero↔monster — so it does not transfer and was re-run with hero vocabulary.

Two independent routes, each with a control. **937 embedded source paths, 51 matching
hero/companion/AI vocabulary, and all 51 are UI, a client-side `Cli` record, or a
`Const` table** — not one behaviour module and no `Srv` half of anything. **19,758
asserts, and a behaviour-vocabulary regex returns exactly one hit**:
`GmPetCommander:127 m_aiMode == CHAR_AI_MODE_AGGRESSIVE`, a widget asserting its own
button state. The symbol that settles it is beside it: `m_aiMode < AI_MODE_ICONS`, next
to two image lists. **The client's entire notion of hero AI is how many pictures the
button strip can draw.**

So it is ours to author, and §5.6 records what the authoring can be checked against —
counted rather than estimated, including a correction: `Category:Hero-vetted skills`
reads as "184 rules already written down" and is really 183 pages, 182 with a
`Hero Usage` section, 232 statements, **~92 with an implementable condition** and ~90
qualitative ("Heroes will rarely use this skill"). Architecture: **AI policy is
per-SKILL data, not per-unit logic**, corroborated by GWW *Foe* and a Guru archive
guide independently.

**Deliberately NOT planned further, owner's call.** The rules are conditions over effect
state R4b does not model — energy, adrenaline, enchantments, conditions and hexes are
all absent — and if the per-skill architecture is right then **the skill substrate's
schema IS the AI's schema**, so designing the policy table first is designing half the
skill table blind. Build the substrate, let the row shape settle, then hang policy on it.

### Item modifiers DECODED, and the attribute panel answers our server (2026-08-20)

[studies/itemmods/FINDINGS.md](studies/itemmods/FINDINGS.md) (new) and
[studies/pvpui/FINDINGS.md](studies/pvpui/FINDINGS.md) §31–§34.6. Branch
`claude/hero-henchmen-opcodes-6ee002`, landed over eight merges: `4ab2537`,
`15ce4e2`, `790165d`, `d49bea4`, `3cdb0c8`, `a5bf2c0`, `f1887c5`, `2f15b41`.

**THE HEADLINE: an item's 32-bit modifier words are decoded, and the retail client
has rendered one we composed.** `studies/character` called these "the largest hole"
in three separate places and `studies/combat`, `studies/enemy` and `studies/isle`
each record the same wall; `content/items.toml` could only copy them verbatim out of
a capture. The format is read out of the client's own parser in `ItemName.cpp` —
**`{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}`** with two skip
predicates — over **157 identifier slots in two jump tables, 133 distinct handler
bodies**. Each identifier's meaning comes from ArenaNet's own words, because every
handler formats through TextApi and the template id is extractable. Validated on
**5,266/5,266 real modifier words** across 1,781 item declarations (a wrong shift or
mask scatters identifiers across a 10-bit space and most miss both tables) and
located structurally on all three builds. `toolkit/clientscan/itemmods.py`,
`test_itemmods.py` (30 checks, floor 30), `vault/content/item_modifiers.toml`.

**The attribute-bonus identifier is 543 (Stacking) and 542 (Non-stacking)** — `arg`
the attribute, `arg2` the amount, and `arg2` doubles as the Minor/Major/Superior
grade index. **Confirmed by the client drawing our own word**: `0x21F81301` went on
the starter hammer and the tooltip read `Hammer Mastery +1 (Stacking)`
(`20260820T113942`). Every field had to be right at once, including the **bit-19
prefix** — bits 31, 30 and 19 are constant per identifier over the whole corpus and
must be copied rather than computed, so composing from the four fields alone yields a
different identifier entirely.

**Three things came out of it that outlive the arc:**

1. **`asserts.py` counts are a FLOOR and this arc paid for reading one as a census.**
   "Exactly two handlers treat their argument as an attribute index" came from the two
   asserts naming `attrib < CHAR_ATTRIBS`. The real number is **fourteen**, found by
   anchoring on a data structure instead — `s_attrib`'s four field accessors, located
   by their own shape, and then everything that calls the name-id one. The tool says
   so in its own output; the lesson is to believe it.
2. **A negative needs a positive control, and 617 got one.** `ItemName.cpp` renders
   nothing for 21 of its 157 slots, including the two busiest in the wild. **633 is
   the attribute REQUIREMENT** — read by a dedicated `ItCliApi` function whose "no
   requirement" default is literally `CHAR_ATTRIBS`, feeding a `ChCliApi` lookup into
   the char attribute container at `[charCtx+0xAC]` and a `setge` against the
   player's rank. **617 is read by NOTHING** in build 38797: no literal compare in
   `.text` in any encoding, not among the ten identifiers `ItCliApi`'s by-argument
   accessors ask for, and the image holds exactly **one** identifier-indexed jump
   table. That negative is only worth stating because the same scan finds 633 twice
   and names ten others.
3. **The panel and the tooltip are two independent paths, proven by an experiment
   that could have refuted it.** With the bonus word on the item the attribute panel
   shows Hammer Mastery **7** against a base of 6 — not 8. The client reads the item's
   words for the TOOLTIP and the server's `0x003A` effective column for the PANEL and
   does not mix them (`20260820T114403`).

**Also landed, on the wire.** The c2s attribute-spend protocol is answered — `0x000E`
/`0x000F`/`0x0010` against `0x0036`/`0x0038`/`0x003B` — with a real server-side model
(`toolkit/authsrv/attribspend.py`, `test_attribspend.py` 49 checks) that **persists**
across a restart; the panel is a client-side prediction the server reconciles.
`0x0093` is `AGENT_MINION_COUNT`, named from the client's own display template. Six
buff opcodes named (63–68). The `charCtx` container family closes at seven.

**NEXT, in cost order:**

1. **`equipped_attribute_bonuses()` should decode `modifiers` instead of reading
   `content/items.toml`'s declared `attribute_bonus`.** Deliberately NOT done: the
   two now hold one fact twice — the shape of bug §34.5 is about — and it is guarded
   rather than ignored (`test_itemmods.py` §11, with a control that proves it can go
   red). The blocker is placement, not effort: `authsrv` importing `itemmods` drags
   `pinned` → `vaultpath` into a path that must work on a bare machine, so the pure
   decode wants a home both can reach. **This pays the day a SECOND bonus-bearing
   item exists** — a headpiece (543 is literally the headpiece form) or a rune (542)
   — which is also when the right home stops being a guess.
2. ~~**What reads 617?**~~ **ANSWERED 2026-08-20 as far as a client read can answer
   it** (`b8d894a`, studies/itemmods §4.1/§4.3). **Nothing does.** The negative now
   rests on a bounded total rather than an empty search: to isolate bits 29-20 x86
   leaves two ways, both fixed byte sequences, and there are **sixteen** such sites
   in the whole image, naming eleven identifiers between them — the same sixteen on
   all three builds, with 633 among them and 617 never. The four non-immediate
   routes are closed (accessor call sites, vtable, a second dispatch table, a mask
   keeping bit 19), and **item creation `memcpy`s the array verbatim** — 66
   functions reachable from `0x0161`'s handler, one touches the modifiers, and it
   interprets one identifier out of them. The positive half: `arg2` is a
   per-`model_id` constant, **71/71**, with the file id as the control that FAILS —
   which corrected the study's "29 of 34 item model ids", a file-id result under the
   model id's name. What remains is not a gap in the search but that **ArenaNet's
   server is not readable from here**; naming the field would need their server, a
   build we do not hold, or a campaign varying one skin at a time.
3. **542 cannot be composed.** Its three-bit prefix has no corpus witness — no
   capture of ours carries one — so `attribute_bonus_word()` ships the stacking form
   only and refuses to invent the other.
4. **34 of 157 identifiers extract no text id at all**, and the `labels`/`templates`
   split is best-effort where a handler branches before formatting. The complete
   ordered `text_ids` list is what the content rows carry.
5. ~~**Two arcs are unblocked and neither has collected.**~~ **`studies/character`
   COLLECTED 2026-08-20** (`611417b`). Armour rating is identifier **572**'s argument
   and it is on screen: the chest's tooltip reads `Armor: 25` / `Armor +20 (vs.
   physical damage)` (`20260820T125155`). The experiment had been open since
   2026-08-06 because it was **two problems wearing one coat** — the words were opaque
   *and* this server sent no armour at all, so the character was bare-chested and there
   was nothing to hover. It now declares the five pieces, places them at the slots
   retail's own `0x006F` writes name, and dresses the body. **Those five content rows
   also stopped being UPSTREAM**: ArenaNet sent us these exact model ids nine times
   each across three captures, every fixed field and all three modifier words agreeing
   (`test_armour.py`, 16 checks). **`studies/combat` COLLECTED the same day** (`31c79df`): weapon
   damage is **584**, `arg` the MAXIMUM and `arg2` the minimum, drawn as
   `Blunt Dmg: 3-5` by the client itself. `HIT_FRACTION` is retired from the
   player's swing — it dealt 15% of *the target's* max health, so every creature
   took the same seven swings however tough it was — and survives only as the
   no-weapon fallback. F3's "GWCA's `ItemModifier` struct is second-gate territory,
   §6.1 row first" never came into it: the client's own parser was the shorter route
   and the better witness, and no upstream was opened. **Both arcs are now
   collected.**

   ~~**Still absent, and worth one line so it is not read as done:** nothing APPLIES
   an armour rating — this server sends five pieces carrying one and no damage term
   reads it — and attribute-rank scaling and criticals are absent too. The range is
   ArenaNet's; the roll inside it is ours. **And the floating damage numbers over a
   struck target have not been watched**: making the player swing needs a click on a
   hostile, which the harness cannot aim, so that one is the owner's run.~~
   **ALL FOUR CLOSED THE SAME DAY** — the armour term, rank scaling, the critical and
   the on-screen watch. See the entry above; the harness learned to aim rather than
   the run being handed over.

### Identifiers: a convention for new tokens, a resolver for the old ones (2026-08-20)

[studies/idents/CONVENTION.md](studies/idents/CONVENTION.md) (new) and
[studies/idents/HANDOFF.md](studies/idents/HANDOFF.md). Landed `f8d63a1`; §3's
`R-IDENTS` row is the status.

**THE HEADLINE IS A REFUSAL.** "C-8 finished, looking into C-9 next" cannot be resolved
by a cold session — the census found the same letter meaning a correction in one arc, a
build step in another and a ladder rung in a third, plus the same letter twice inside one
document. The obvious fix, renumbering the existing tokens into a clean scheme, is the
exact shape of the 2026-08-12 provenance scrub whose 46 rewrites were all reverted, and
it was **refused**: nothing is migrated, and every historical token is grandfathered.
(That scope is owner-ratified: §7 Q8, CLOSED 2026-08-20.) What landed is a rule for
NEW tokens only (a registered word prefix naming
the defining document, with the token's KIND in a legend line rather than in the
letter), the resolver that works on the documents written before the rule
(`python toolkit/whichrung.py C-8`), and an accumulation tripwire —
`toolkit/identlint.py` + `test_identlint.py`, provlint's posture, not a gate.

**Also settled:** the `PLAN.md`/`HANDOFF.md` R-ladder drift is closed by annotation in
place rather than a re-sync, because the duplication *is* the mechanism
(`HANDOFF.md:116`); and the undocumented bare-integer commit-subject prefix
(`29:`→…, count deliberately unpinned — it grew even while this arc landed) is retired
with its meaning recorded, not rewritten.

**NEXT:**

1. **Nothing is scheduled.** The convention is live for the next document that mints a
   token; there is no follow-up work and deliberately no migration backlog.
2. **If `test_identlint.py` goes red**, it is reporting accumulation, not a forbidden
   commit — raise the ceiling in the test with a comment saying why, as
   `test_provlint.py` does, or prefix the new namespace. Do not scrub existing tokens
   to make it green.

### Merchants — a player can now BUY from a server we wrote (2026-08-19)

[studies/newopcodes/FINDINGS.md](studies/newopcodes/FINDINGS.md), the unit-setup arc.
Authored NPC, authored stock, authored prices, a funded purse, a client that asks and a
server that answers. `20260819T170427`: `Your Funds` fell **2000 → 1990** — the quoted
price exactly — on the merchant panel *and* the inventory window's gold line, with the
bought item in backpack slot 0 carrying its real stats. First transaction this project
has completed.

**What landed.** `authsrv.PLAYER_BAGS` — retail's nine containers, sent during LOAD where
retail sends them (49/49 live connections, five distinct characters, one distinct set);
with one bag the client refused every purchase LOCALLY and cost no wire message doing it.
`content/items.toml [item.backpack]` — the Backpack is an ITEM, `0x013F`'s trailing field
is its id, and sending 0 there drew eight containers and no Backpack. `0x014F` is the gold
DEBIT, mirror of `0x0140`'s credit, which refutes this arc's own "no server message carries
it". `handle_item_purchase` answers `GAME_CMSG 0x004D`: **pay, mint, place, confirm**.
Tests: `test_playerbags.py` (18), `test_purchase.py` (22).

**BOTH DIRECTIONS NOW WORK, and the round trip is on screen** (`20260819T173604`):
buy at the quote, sell back at half, **2000 − 10 + 5 = 1995**, `Backpack (empty)`, Sell
greyed. `handle_item_sale` answers `0x004A` with remove → pay → confirm, read by byte
offset from all **eight** sales — and the trap it holds shut is that the sell request is
NOT the buy message's shape: five fields against seven, price at index **4** against
index 2, so reading the buy's index would credit 0 silently.

**`0x00C3`'s CONTESTED row is CLOSED, on a positive result.** `0x00C3 [11, 0]` adds a
**Buy/Sell tab pair** — it is what turns `0x00CA`'s buy-only panel into a merchant — so
field 1 is a **transaction KIND**, the same 11 the client sends on `0x004A` and gets back
on `0x00CC`. One enum, three opcodes, two directions. Upstream's `WINDOW_MERCHANT` is
earned at last. The count reading rested entirely on all six corpus windows happening to
stage eleven items.

**NEXT, in cost order:**
1. **A purchase does not persist and stock is infinite** — ids come from a fixed base and
   slots from a per-connection cursor. Fine for probes, wrong for a world.
3. ~~**The level-up burst**~~ **DONE 2026-08-19** — observed twice and written up in
   [studies/unitsetup/FINDINGS.md](studies/unitsetup/FINDINGS.md). `0x009F` prop **37** is
   the level-up carrying the new level (2 sightings, both at a transition) and prop **36**
   is the level state (1,819); `0x0039` is total attribute points and prop **42** maximum
   health, both closing on GWW's published tables the capture never supplied. Left open:
   `0x0038` is NOT IDENTIFIED, and whether attribute points and health are owner-private
   is RECONSTRUCTION needing a second player in view.


### Model authoring — the PLAYER path is open, and one bit decides whether it animates (2026-08-19)

[studies/playercomposite/FINDINGS.md](studies/playercomposite/FINDINGS.md), rung U10 in
[studies/unitmodels/PLAN.md](studies/unitmodels/PLAN.md). Monster authoring is closed end to end
(U1–U9: decode → modify → re-emit → the retail client renders it). The player analogue had no
resolver at all, and the named suspect was wrong — `ConstComposite`'s pointer tables in `Gw.exe`
hold no file id at any depth, they are texture-atlas RECTs. **The ids come from Gw.dat file
`0x33EA`**, and `toolkit/mapdata/cpsdata.py` + `test_cpsdata.py` (58 checks, floor 58) now parse
it: residue 0 on 105,531 B, 3,803 records, cross-half type agreement 3803/3803. The two-witness
join runs in-suite — composite type 1 resolves to **exactly the twenty shells an independent FFNA
walk names, 20/20 composited**, and type 2 is a second twenty on element-for-element identical
node counts.

**NEXT, in cost order:**
1. **What is `arg0`, whose bit 0 picks composite type 1 over type 2?** (`and eax,1; inc eax` at
   `0x008315B5`, stored `this+0x3E4`; trace back through `0x0082DBB0`/`0x0082DBA0`'s callers.)
   Two complete twenty-shell sets exist on identical skeletons — one with 220–289 sequences, one
   with 10–17 — so **authoring against the wrong one produces a character that cannot animate.**
   One bit, total consequence. Everything else on this path is cheaper than it is important.
2. **P2** `toolkit/clientscan/composite.py` — the static half (`s_components` `0x00A3AE58`,
   `s_dims` `0x00BF37F8`, `s_fileFlags` `0x00A978EC`, base pieces `0x00A96D9C`,
   `s_appearanceSlot` `0x00BC8AC8`, the ConstComposite CSR/rect pair). Stdlib only, bare-machine.
3. **P3** `toolkit/mapdata/playerassembly.py`, after a behaviour-neutral `seeds` refactor of
   `unitassembly.Resolver` — its pinned 54/54 is the refactor's regression oracle.
4. **The wire item-type ↔ composite-type mapping** (§2 step E). Our server picks the wire type; if
   it does not induce the right composite type, every equipped piece lands on the wrong component.
5. **`npcdefs.py` refuses on the full 14-capture pool** — "definition 159 has two move speeds
   (288.0, 144.0)", and 144 is exactly half of 288, so field 9 may be an observed instantaneous
   speed rather than a definition constant. Every `unitassembly`/`unitmodels` figure in the tree is
   therefore a **3-capture number**. Content-pipeline work, not model work; belongs with R4c.

**Cross-arc, and neither side could see it alone: file 15018 — the archivewrite arc's standing
"unwritable" wall (row 11196, 1,029,564 B in a 1,029,632 B reservation) — is the human male player
shell for profession 1.** The hardest write target in the archive is a player shell.


### Movement — the OTHER two callers are decoded, and gate 2 is knowledge not a lever (2026-08-20, round 3)

`0x00709E90`'s other caller is the LOCAL PLAYER's own move planner (`0x0081ADB0`, ChCliBase.cpp:248 `this == context->playerControlledChar`) and `0x005FEF70`'s is AgAgent's one-shot obstacle sidestep (`0x00600500`) — so the client plans with the same *function* it is judged by but never the same *question*: the planner starts from ASYNC (`0x005FC42D [edi+0x14c]`), gate 2 from SYNC, and both callers of `0x005FEF70` read a zero identically (n = 2 of 2, the predicate was not over-generalised). **Both parameter asymmetries are incidental** — `maxCount` 4-vs-9 cannot produce a zero (`*pathCount` is the emitted count; overflow drops through a void `ret`; the fallback returns truncated results unvalidated) and arg3 300-vs-10000 is a march budget whose exhaustion *succeeds*. `pathCount == 0` narrows to "the START point could not be RESOLVED", defeatable by an integer alone (`0x0072AE4F` range-checks the start's plane against `staticData->map.Count()`), **but we never write such a value** (plane is literal 0 or the client's echo, 12/12 config rows). Round 2's one live hole is inert: tier 1 is `LoadLibraryA("PathEngine.dll")`, absent from the owner's install. **★ Gate 2 has n = 0 observed firings** — gate 1's 299.3326 u straight-line fence subsumes all 24 measured snaps (623 paired intervals, min before-separation 342.8 u). Next is unchanged (the `clientControlled` breakpoint), plus one cheap new assert: **n = 12 configured spawns, 8 OK / 1 plane-mismatch (map 474) / 3 off-mesh — all four are placeholder (0,0) rows and 7 of 7 real spawns pass.** See `studies/movement/FINDINGS.md` §2026-08-20 round 3.

### Movement — the FALLBACK half is DECODED; "under 300 u" is not safe (2026-08-20)

**Movement / AgTrack fallback — DECODED 2026-08-20, and "300 u" is dead as a rule.** Three gates (straight-line >299.3326 u — exactly 300.0 SNAPS; walkable `pathCount==0`, meaning OUR granted position is off the navmesh; `timeToEvent<0.0005f`), any one snaps, and the snap reseeds EVERY world-1 agent. **No gate is a server lever.** Next: measure `clientControlled` alongside separation to find which gate fires (`0x0060580D`/`0x00605820`), and price `0x002C` — the one real lever — against the record that it was already tried and removed as "the warp the player described". See `studies/movement/FINDINGS.md` §2026-08-20 round 2.

### Movement — the AgTrack match test is DECODED and shape 1 is DEAD (2026-08-20)

`0x00605AF0` compares POINT ONLY (100.0f straight-line-squared-strict AND walkable-path-linear-inclusive, ~99.6 u effective) against `source+0x78` — the SYNC agent's own dead-reckoned position, which our `0x0029` never writes (n = 0 writes in `0x00602A40`) — over ArenaNet's `history` chain, not a prediction; so no grant can make it match, `--heading-grant` already proved that on the wire, and the next job is the undecoded fallback half `0x00605753`–`0x0060583D` where a MISS is actually adjudicated (and the 300.0f gate there is STRAIGHT-LINE, correcting FINDINGS:2373).

### Movement — ★ MECHANISM DECODED IN THE BINARY; SIX fixes dead; three shapes left (2026-08-19)

**★ READ [studies/movement/HANDOFF.md](studies/movement/HANDOFF.md)'s top box before
anything else.** The warp is fully traced: the snap is `0x006022B0` copying SYNC →
ASYNC, reached only from `0x00605FC0` (exactly 3 callers, **all message-driven —
never per-frame**), whose test `0x006055E0` returns "no snap" if one of the client's
own pending predicted commands matches our grant (100.0 @0x00946560) and otherwise
compares the **walkable path length** between the copies against **300.0f
@0x00946564**. We answer a click with `0x0029` (SYNC-only); the authoritative copy
glides there and PARKS (93.4 of 177.3 s); the player keyboards away; **nothing we
send can reach the copy they see** — `0x0025`'s async arm is gated shut for the
client-controlled agent (`0x005FD5D3`, `[mgr+0x1E0]`); separation grows to 3,648 u
unwatched; the next grant or arrival redeems it all at once.
**A SIXTH CANDIDATE IS DEAD:** the `0x002B` direction factor is worth **−3.1%
magnitude and 0% frequency** on the shipped build (two independent derivations),
and `0x0027` at spawn is a measured no-op. **The shipped build's real separation is
p50 1,164 u** (n=251) — every "125.9 u / under 150 u" bound in the older record came
from `171153`, a refuted configuration. **The scoreboard's denominators are not
comparable** (coverage 31% / 72% / 89%); per observed second the default build is
the worst on displaced distance. `movesync.py` and `pinned.py` were repaired this
round, both mutation-pinned: the hard bar grew a **distance arm** (≥ 520 u below the
0.05 s dt floor, corpus **61 → 64** hard rows over 961 captures), so the three
configurations now read **7 / 20 / 13** hard jumps and **1.31 / 5.69 / 11.88** per
minute of span with magnitude p50 **1,969 / 569 / 582 u** — implied velocity is
demoted to a labelled gate input everywhere — and the pin now carries per-build
TUPLES of accepted patched digests that the patchers themselves register, so it no
longer refuses the 38797 we launch and can represent 38833.
The three shapes left, in evidence order: **match the client's pending
command** (the only one that prevents a snap), **`0x002C`** (the sole ungated
both-copies position primitive; `AgTrack::Clear` + double SetPosition), and
**`0x0027` as a mid-flight re-bake** (reaches both copies AND re-issues the
outstanding grant). Everything below this paragraph predates the decode.

### Movement — latch FIXED; teleport EXPLAINED; FIVE fixes dead and the arc re-aimed (2026-08-19)

**Picking this up cold? Read
[studies/movement/HANDOFF.md](studies/movement/HANDOFF.md) first** -- the
mechanism, the five dead candidates with their numbers, the one-minute scoring
loop, and the four traps that have each cost a client run. Full record:
[studies/movement/FINDINGS.md](studies/movement/FINDINGS.md). Two separate
bugs; one fixed, one understood and unfixed.

**FIXED (`6793260`).** The position-trust guard latched: its 900 u radius was measured
from the value it was preventing from being corrected, so once the model was wrong by
more than 900 u it could never resynchronise — 36 consecutive refusals in one run.
Scored over the **72** refusals the four harness runs printed: client right 71, guard
right 0, undecidable 1. Budget is now `max(900, 580·dt)` — a strict loosening — and the
second consecutive refusal is adopted regardless. `test_position_trust.py`, floor 28.

**THE TELEPORT IS EXPLAINED AND STILL UNFIXED.** `0x0029` is **not a heading hint — it
is a scheduled teleport.** It caches an arrival tick at `agent+0x48` and a target at
`agent+0x9C`; at that exact millisecond the client snaps. Seven arrivals watched
directly in client memory (98 u to 5,238 u), each within one 20 ms sample of schedule;
`+0x48` is set once **per isolated click grant — under re-grants it re-arms freely
(304 re-arms in 61 s; FINDINGS refuted the unqualified "never re-armed")**. The formula
`+0x48 = +0x58 + floor(dist*1000/(maxSpeed*moveSpeed))` predicted 18,187 ms against
18,087 actual.

**THE CORPUS PASS ANSWERED §8'S QUESTION AND RE-AIMED THE ARC** (12 agents over the
9-capture live corpus, every measurement attacked by an independent skeptic; framing
residual 0 on every connection). Three things changed:

1. **The question's two branches both miss.** Retail's heading grants never point behind
   the player's **travel** (0 of 44, and 0 of 12 connection clusters — but the forward
   family's own background is 2.2%, so this says backward is *not different*, not that
   it is clean); they usually point behind **facing** (25 of 29), and that number is a
   property of the client's own message — a substitution control with the server deleted
   reproduces it byte-identically. **Zero impossible-speed steps** in 2,565 intervals,
   largest 388.80 u/s — but the null's **recall is 0 of 1**: it misses the corpus's one
   real retail teleport, because the client stops reporting when it stops moving.
   And §8's branch-2 prescription is a **no-op**: retail's expression is
   `reported_pos + vec2 (+0.5 u)` and ours is `state["pos"] + heading` — the same formula.
2. **`HEADING_GRANT` is `False` by default, so the heading arm sends NO `0x0029` at
   all.** The warp the owner watches arrives through the **CLICK** arm
   (`authsrv.py:7617`), where our destination is the client's own clicked point —
   exactly what retail sends. **The difference is not the point: retail's click grant is
   superseded within a median 0.490 s by the heading grants that follow, and ours is
   never superseded by anything.** Three of the four dead fixes were aimed at a path
   that by default sends nothing.
3. **A FOURTH fix is dead** — "echo the client's own vector", killed as a no-op above,
   joining suppress-the-grant, `--stop-echo` and `--heading-grant`. Also struck: any
   backward/direction guard (retail has none, and it would be the fifth over-fit), the
   `+0.500 u` constant as a fix (real to ±0.00003 in 8 of 8 captures, but it moves the
   schedule 2 ms against a 5,238 u harm), and a `k ≤ 1` clamp "bounding any warp to
   768 u" — false, because it bounds against the server's own `p`, whose measured drift
   is a median 538 u and a max 1,429 u.

**ALSO FIXED, and deliberately NOT billed as a warp fix.** Our `0x0025` carried a vector
**765× too long** — 4,704 of 4,760 sends at 765–768 where retail is unit-length in
3,789 of 3,789, zero overlap. Inert: the only float read of `+0xBC` in `AgAgent` is a
lazy angle cache calling `atan2` (`0x005BCA00`, CRT descriptor `\x05atan2`), which is
scale-invariant. Fixed because it is wrong and costs one line; locked by
`test_position_trust.py` §8 with a control. It also closes `studies/smsg`'s open
"why 26.57° and not 45°": the diagonal is `normalize(2·v + perp(v))`, sqrt-free, and
`atan(1/2)` is what that costs.

**THE GENERALISATION IS CLOSED (2026-08-19).** The resync mechanism was
established with `--heading-grant` on and its extension to the default build was
flagged as inference. `movesync.py --wire-only` closed it retrospectively from
captures already in the vault, using **measured positions only** -- no glide
reconstruction, because a resync landing point is itself a *reading* of the
authoritative agent (1.0-59.5 u from movetap's, n=13). On the **default build**
capture `20260819T145717`: landings sit **43.9 u** from the path they were
granted against **744.8 u** for an unrelated grant, **18 of 30 on-path against
0 of 31**, and the corpus's biggest warps (3,166 u / 2,583 u / 2,234 u) land at
fractions 0.5-1.0 along grants **12-21 seconds old**. Two further captures refuse
a verdict rather than being averaged in -- one at 2.75 s report cadence where 57%
of intervals clear the jump bar, one at n=3 -- and `--wire-only` now declines
above 0.5 s cadence.

**THE CONSTRAINT THAT KILLS THE EASY FIX.** Grant age at the jump is **5.84 s
median** in the default build against retail's **0.490 s** re-grant, so "just
re-grant more often" is the obvious read -- and it is wrong. `--heading-grant`
held grant age to **0.32 s**, faster than retail, and still warped, with mean
separation 587 u before each resync. **Both terms are required: the granted point
must be where the player is actually going AND it must be refreshed.** Each of
our two configurations does exactly one of those.

**THE "LARGEST REMAINING HOLE" IS CLOSED (2026-08-19, later): an instrument
artifact.** Capture `20260811T173940`'s five jumps were a client WALKING —
pre-2026-08-19 captures emitted `position_report` from the `0x0047` stop arm
only, hiding 130 of the capture's 158 position observations; spliced, 0 of 5
jumps exceed run speed (max implied 243.3 u/s) and positions are bit-identical
across every client silence. The number had been quoted from above movesync's
own REFUSING-a-verdict line. The live half of the population is OUR gamesrv
corpus's **26 kinematically impossible steps** (7 captures, one of them the default
build), since adjudicated as 25 resyncs and one client-side click-move at 2.6x the
walk budget, and quoted as magnitude and excess over the 288 u/s budget (excess
p50 671 u, max 3,804 u over the corpus's 43 detections) rather than as the implied
velocity this line used to carry (v p50 2,521 u/s, max 23,279 u/s) — see the FINDINGS
corpus-pass section.

**THE FIFTH CANDIDATE IS REFUTED (2026-08-19), and it is the worst of the
three configurations.** Run `20260819T182652`: **14.6 jumps/min against a stated
bound of 2**, versus `--heading-grant`'s 12.8/min and the default build's
5.7/min. **Both candidate fixes are worse than shipping nothing; the default
build is still the best configuration this repo has, and both flags stay off.**
The mechanism confirmed a third time (12 of 16 landings on the granted path,
perp 7.5 u against 338.9 u control, grant age p50 0.28 s) -- so the fix met both
terms it was designed for and warped more.

**WHAT THE RUN SAYS IS WRONG IS THE SPEED, NOT THE POINT.** The player moved at a
median **111.7 u/s** while every grant told the client moveSpeed 1.0 = **288.0
u/s**, a 2.6x mismatch none of the five candidates touched. **The clean form of
that claim FAILED and is recorded as a failure**: "separation grows at
`288 - player speed`" over-predicts (mean predicted 179.6, observed 124.8, mean
|error| 93.2 u/s over 13 runs). Speed is a major term, not the whole model.

**AFTER FIVE FAILURES, ALL FIVE WERE ADDITIONS AND ALL FIVE PICKED A POINT.** The
server cannot know the player's instantaneous speed and the client can. The next
intervention should be a **subtraction**: clear the outstanding destination with
`0x0028 AGENT_STOP_MOVING` when keyboard movement begins, rather than re-aiming
it. Untested, deliberately not shipped alongside the refutation.

**THE FORMER FIFTH-CANDIDATE ENTRY, kept for the shape it locked.**
`--client-endpoint` (`authsrv.py`, `CLIENT_ENDPOINT`) answers every keyboard
heading with **`reported + heading + 0.5 * unit(heading)`, UNCLIPPED** -- retail's
own expression, the client's reported position plus its own vec2 plus the +0.500 u
constant measured to +/-0.00003 in 8 of 8 live captures. It differs from the
refuted `--heading-grant` in exactly the two things that made that one warp: it
does not send `clip_to_walkable`'s shortened point, and it derives from the report
in hand rather than `state["pos"]`. `test_position_trust.py` §9 locks both, with a
control that hands the matchers the old defects and requires them to still fire.
Floor 34, green 38.

**THE PREDICTION, in two parts because the last one had only one and failed by
it** -- it bounded teleport SIZE while the harm arrived as FREQUENCY:
- **SIZE:** mean separation before a resync stays under **150 u** (587.0 u measured
  under `--heading-grant`).
- **FREQUENCY:** client steps over 300 u fall under **2 per minute** (12.8/min
  under `--heading-grant`, 5.7/min in the default build).
**Refuted if either fails.** Both are readable from one 60-second run, and the
frequency half needs no client-memory probe at all:

    python toolkit/harness/session.py --keep-open --exe <38797 build> --game-args='--client-endpoint'
    python toolkit/clientscan/movesync.py --wire-only

**THE NEXT EXPERIMENT, and it is a measurement rather than a fix.** The surviving
candidate — grant on every heading, ungated, `0x0025`+`0x002B`+`0x0029`, from the
client's just-reported position — is a **refinement of the REFUTED `--heading-grant`
run**, and it differs from it in exactly two terms: the origin and the moveSpeed. **The
origin term is now known to be a no-op** (`_take_client_position` writes
`state["pos"] = reported` on accept, and the heading arm reads it back immediately), so
**it differs by the moveSpeed term and the cached-`m_point` carry, and nothing else.**
The wire cannot separate those — a cache-free model reproduces every mechanism
conclusion equally well. **Run `movetap.py` on `+0x48`/`+0x9C`/`+0x78` across a
`--heading-grant` run.** The arrival formula has no free parameter. Do not ship a fix
that changes both terms at once; a green run would teach us nothing about which mattered.

**Standing rule for any future warp run:** keep the keyboard moving through the whole
waiting period. The client emits `0x003D` only while moving, so a stationary wait blinds
every wire-side instrument exactly when the phenomenon fires — 8.7% of retail's own
grants sit outside any watched interval for this reason. And **retire the 320 u/s
ceiling**: it fires on 19.7% of legitimate retail intervals, because it sits below the
383.04 u/s boost mode the wire declares literally.

Secondary, ~~still open~~ **ADJUDICATED 2026-08-19**: 26 of 43 warpscan detections in
OUR gamesrv corpus are kinematically impossible, **25 of the 26 are resyncs**, the
survivor is a client-side click-move at 2.6x the walk budget, and the 729-768 u band
is our own heading-derived grant leash (n=21, p90 757.5) rather than the `0x003D`
heading-vector length. Quote them as excess over the 288 u/s budget (p50 671 u,
max 3,804 u over the 43) and never as the implied velocity this line carried
(v p50 2,521 u/s); the
two `0x003D` magnitude constants (765.017539 / 768.000000) stratify by `movementType`
91.2% vs 22.3% but have no mechanism; and the sync (`+0xE8`) vs async (`+0x14C`) agent
question decides whether the model we watch is the one the player sees.

**THE SECOND CORPUS PASS (2026-08-19, later) — the handoff's §4 list was run, every
number adversarially re-derived; record in FINDINGS "the corpus pass on the handoff's
list", next actions in HANDOFF §4.** In brief: (1) retail does NOT stop on keyboard
onset (1 of 499 onsets, a zone transition) — it SUPERSEDES at one RTT, so the
`0x0028` subtraction candidate is dead before it was built, and supersede-every-heading
IS dead candidates 3/5 (both already ran a tighter leash than retail and warped more —
the point is bracketed from both sides). (2) The `0x002B` contest resolves:
`0x002B = direction_factor × modifier` (1.00/0.66/0.75 × snare, byte↔float lock
0/1,049), the absolute base rides `0x0027` (288 / 383.04 boost; we send `0x0027`
never, `0x002B`=1.0 always) — but the CAUSAL step is open: our client backpedals at
0.66× while we send 1.0, so the factor is client-side on the predicted copy, and
whether the wire float steers the AUTHORITATIVE copy needs the handlers or a client
run. (3) TWO new structural findings: the 300 u scoreboard metric is contaminated
(retail scores 6.4/min on it with ZERO intervals over 400 u/s; speed-gated our
configs read 1.31 / 5.69 / 11.88 hard-jumps/min of span, not 5.7 / 12.8 / 14.6 —
corrected 2026-08-19 from 1.3 / 5.4 / 11.9 when the bar gained its distance arm,
n = 7 / 20 / 13), and the default
build's authoritative copy is mostly PARKED (moving 39.8% of backward intervals,
mean 114.57 u/s; duty cycle tracks grant rate 0%→98%) — its separation is the client
walking away from a parked point. (4) The snap trigger (timer vs threshold) has
never been measured and decides whether any slow-the-copy fix can bound FREQUENCY;
the five movetap runs already hold the answer. Sixth-candidate VALUES are ready
(0.66 = `c3f5283f`, 0.75, `0x0027 288.0` at spawn as its own change, re-send at
report cadence — "edge-triggered" falsified at 72.2% same-family repeats); its
causal step is NOT. ~~`pinned.py` still blocks the next live run (stale patched hash;
no 38833 row).~~ **FIXED 2026-08-19**: `Build.patched` is a per-build TUPLE of
accepted digests — the current patcher's 38797 copy and both 38833 copies committed
— and both patchers register what they write into
`vault/client-patched/patched_digests.json`; the loosening is fenced by refusals a
mutation reddens (`test_pinned.py` 143 checks / floor 130, `test_buildid.py` 42 /
floor 39).

**Instruments:** `toolkit/clientscan/movetap.py` (client-side arrival time and live
position; `--selftest` needs no client) and `toolkit/authsrv/warpscan.py` (scores a
capture, printing the TRIAL count before the verdict — a run with zero armed trials
tested nothing).

### GAME_SMSG naming — 16 opcodes named and merged; 14 PARTIALs remain, priced (2026-08-18)

[studies/smsgnames/FINDINGS.md](studies/smsgnames/FINDINGS.md) is the static reachable-handler
pass over the seen-but-unnamed set: two witnesses (the client's own handler asserts + the decoded
wire over 46 live connections), adversarial refutation, a consistency critic, and an independent
`msgshape` field-width cross-check that caught one real error (the item `inventory key` is `u16`,
not the `u32` a handler's dword load implied). **16 opcodes earned a name and are in
`schema/overrides.json` (GAME_SMSG 66 → 82):** agent movement `0x0027`/`0x0028`/`0x002A`/`0x002C`,
the generic-value family `0x009F`/`0x00A0`/`0x00A2`/`0x00A3`, `0x005A PLAYER_REMOVE`, the
item/inventory block `0x013E`/`0x0144`/`0x014B`/`0x014D`, `0x009B AGENT_SET_NAME`, and the title
pair `0x00F3 TITLE_RANK_DATA`/`0x00F4 TITLE_RANK_DISPLAY`. Two resolutions worth carrying:
`0x0027 AGENT_UPDATE_SPEED_BASE` did NOT force a rename of `0x002B AGENT_UPDATE_SPEED` — that
entry already OBSERVED-refutes the GWLP-R 'SpeedModifier' gloss, and the client splits the pair by
its own words (maxSpeed vs moveSpeed); and `0x00F3`/`0x00F4` were lifted **UPSTREAM → OBSERVED** by
the frame bus — `0x00F4`'s frame `0x10000064` and `0x00F5 TITLE_UPDATE`'s `0x10000065` feed the
same CtlText panel (`toolkit/clientscan/framebus.py` post/subscribe scan, closing the open lead at
`studies/character/RUNS.md:203`). That shared-panel technique generalizes to any UPSTREAM display opcode.

**NEXT: the 13 held PARTIALs, in cost order** (all mechanism-OBSERVED, name not yet earned —
deliberately OUT of the schema; full ledger and each held-reason at `studies/smsgnames` §4/§5):
1. **`0x015E ITEM_LOW_DETAIL` / `0x0161 ITEM_HIGH_DETAIL`** — the critic's strongest withheld pair:
   a genuine two-witness MESSAGE identity (fileId SOURCED at `ItCliApi:2410`/`:2505`), held only
   because fields 4–10 are unread. Cheapest: read the shared item builder `0x848450`'s field writes;
   fix `0x0161`'s off-by-one field indices first (critic flagged: name is wire field 12, code[] field 13).
2. **`0x009A`** — the char-record `+0x30` dword store keyed by agent id that PAIRS with the now-named
   `0x009B AGENT_SET_NAME` at `+0x34` (same `0x38`-stride ChCli record). Read what consumes `+0x30`.
3. ~~**`0x005D`** — candidate `CHAT_MESSAGE`: needs the sender/body cross-check~~ **EARNED
   2026-08-19, and the cross-check ran OFFLINE** — the corpus already held it
   ([studies/chat/FINDINGS.md](studies/chat/FINDINGS.md)). The whole family landed at once:
   `0x005D CHAT_MESSAGE_CORE` (body fragments, cap measured 121 = declared−1), `0x005E
   CHAT_MESSAGE_SERVER` (133/133 words = the subject playerId or 0), `0x005F CHAT_MESSAGE_NPC`
   (45 sightings, commit tag carries the sender's enc-name), `0x0061 CHAT_MESSAGE_LOCAL`
   (**47/47 sender playerIds resolve to `0x0059` names**, typed player text verbatim in the
   bodies — "wtb Axe grip of the paragon" et al.). `0x0060` stays unnamed: zero witnesses.
   The server now ANSWERS `0x0064 CHAT_SEND` (test_dispatch's oldest recorded drop): All-chat
   echo + the observed `/bow` reply, everything else refused loudly (`chatdefs.py`,
   `test_chatdefs.py` — the framing check is byte-identity against ArenaNet's own multi-part
   advert). **The loopback confirmation RAN 2026-08-20, all three arms as predicted**
   (`studies/chat` §10): `!hello` rendered `Test Warrior: hello` off the byte-exact echo,
   `/bow` rendered its emote line, and the `#test` control rendered NOTHING — which also
   proves the echo is the only render path (no client-local copy). Chat is DONE as a
   mechanism; what remains is breadth (other sigils/channels need labelled captures first).
4. **`0x0147`/`0x0148`** — the equip-set pair, already asserting `ITEM_PLAYER_EQUIP_SETS`
   (`ItCliInv:375`/`:329`); then the player-record pair `0x003C PLAYER_UPDATE_FLAGS`/`0x00B0` and the
   marker `0x008D`.

### Unit setup — the pipeline is one document, ALL 11 questions ran, and the fixes landed (2026-08-17)

The arc is [studies/unitsetup/FINDINGS.md](studies/unitsetup/FINDINGS.md): how a unit comes
to exist, server → wire → client, synthesized 2026-08-16 and then mostly EXECUTED the next
day — its §8 ladder priced every open question by cheapest experiment, and ten of eleven
are now ANSWERED in place, seven of them by **agent-piloted caged runs** (the harness
launches, keys, screenshots, and the frames are read without an operator; the first was
`20260817T142147`). The measured headlines: property 36 is a per-agent level store written
at `entry+0x2C` and read back for any agent's roster row; the health pool is a SIGNED,
unclamped store under a display floor of 1; a declared-but-composite-less definition
renders as a white placeholder box (the new diagnosable signature); armor items place
THEMSELVES, so `0x006E`'s slot-order contest is invisible to pixels; and the create-burst
census (`toolkit/authsrv/createburst.py`, 951 paired `0x00F0`s) split the initial-status
payload by kind — which armed two server fixes that landed the same day: **`0x00F0` is now
the unconditional create preamble on every path** (divergence D2's v1, closure notes at
both docs) and **the player's agent gets prop 36 pre-create** (the roster's `W0` was the
absence rendered; it reads `W1` now, harness `20260817T153701`). The harness also learned
to aim: `--walk` gained `yaw`, named-key holds (`alt:` is nameplates) and `shot:` on the
plan's clock, validated live (`20260817T151242`) — "the harness cannot aim" survives only
for world-anchored clicks and model-appearance judgment.

**Q11 RAN, 2026-08-17 — the arc is 11 of 11.** Three owner-driven live captures of a new
Factions character (`20260817T180610` starter zone, `183323`, `183756` Shing Jea
Monastery), all assembled, sealed and plan-marked. They took the observed `GAME_SMSG` set
from **155 opcodes over 12 connections to 177 over 20**, and that 22-opcode difference is
its own study, [studies/newopcodes/FINDINGS.md](studies/newopcodes/FINDINGS.md): 9 names
earned, 4 upstream-only, **8 NOT FOUND**, 1 CONTESTED, eight landed in
`schema/overrides.json` behind `toolkit/schema/test_smsgnames.py`. The headline is not a
name — `0x006F` has none in any lineage and **settled the nine-slot equipment order**
against the two-lineage majority (§6 Q6 below). Three same-day corrections came out of
the same corpus: `0x0199` field 1 is the player NUMBER not the agent id
(`studies/heroes` §22), the allegiance vocabulary is **eight** tokens not three with
`mons` turning out to be retail's own, and `0x0071` is a henchman-slot commit whose
declaration block (`0x009B` + prop 36 + `0x00A6`) nobody had read.

**What is left, in cost order:** the `0x00F0` non-zero payload tail — **now shaped rather
than open**: the client stores all 32 bits at `record+0x30` and branches on **bit 4
alone** (`test al, 0x10`, so bits 8–31 are never examined on the create path), then a
constructor copies the word wholesale to `+0x10C`. So payload 0 is *safe* and the tail is
fidelity, not correctness; finishing it is one defined step, find what reads `+0x10C`.
`0x006D` NPC weapons at create —
**refined 2026-08-17 after the heroes arc hit ItCliApi:488 and asked whether its blocker
was this line**: it half is. The item-authoring gap has TWO floors. Floor one, item
RECORDS, already exists — the armor probe declares content-row items via `0x0161`, and a
census over all three keyed captures proved retail's `0x006D` ids are exactly such records
(**375/375** non-zero ids declared earlier in the same stream by the `0x015E`-family, zero
exceptions — so what `0x006D` still lacks is per-NPC-type weapon ROWS, not machinery; and
**210/585** retail `0x006D`s carry item **0**, a legal no-weapon value needing no authoring
at all). Floor two, per-OWNER inventory containers in the item client's table
(`[globals+0x40]+0xD4`), is what ItCliApi:488 actually wants — the hero's owner has no
container, and our `0x013F`/`0x013E` bag family only ever goes to the local player. Same
subsystem, different missing piece: floor two is the heroes arc's to price as its own
work, not a duplicate of this line. (Priced 2026-08-18, `studies/pvpui` §26, with one
correction: the table is keyed by inventory id, not owner, and its registrar is `0x0144`
— see the PvP-UI entry below.) And two residues filed with their own arcs — the
heroes split-filter (§21.2) and whether `0x006E` position semantics matter for the HANDS.

**2026-08-18, THE LADDER RAN: five caged runs, and the CONTESTED row is CLOSED.**
[studies/newopcodes/FINDINGS.md](studies/newopcodes/FINDINGS.md) has each result in place.
**`0x002F` IS `AGENT_UPDATE_ALLEGIANCE`, OBSERVED on our own client** — and it acts
**alone**: four bodies created `'mons'` (all red), arms 10 s apart, `0x002F` alone flipped
its body's compass dot red→**green** in the next frame, `0x00AA` alone left its body red
for 53 s, the pair flipped, and the untouched control never moved. So `0x00AA` is neither
necessary nor sufficient, refuting the hypothesis the probe was built on. **The
reconciliation is the finding worth carrying:** `studies/enemy/PLAN.md`'s "sending it
changed nothing" **stands** — it watched *attack initiation*, gated by `+0x1B5`, which
really is write-once at construction. Allegiance is **at least two stores**: the displayed
team token `0x002F` writes at any time, and the attackability byte nothing post-construction
moves. Both old claims were true about different surfaces; the word "allegiance"
equivocated. `authsrv.py`'s "no later message can correct it" is corrected at the site.
**`0x00B9` field 2 is a TEXT-STYLE flag** — 0 cream, 1 gold, same box and close button,
measured over two runs differing in that field alone (meaning still UNVERIFIED; retail
exercises both values in adjacent messages, so the discriminator is a capture, not an arm).
**`accum_drains` came back QUIET** on `0x0085`/`0x00D4`/`0x0086` with real declared ids
staged — the pre-registered null, which refutes nothing — plus one positive: `0x0086` with
counts deliberately equal drew **no `ChCliApi.cpp(1587)`**, confirming the assert guard from
the running client. Two honest gaps recorded rather than smoothed: **`0x00E1` was never
observed** (the client left the OS foreground and ten frames do not exist), and a 7,172-px
"hit" at the `0x00D4` drain was a **skill tooltip** raised by the resting mouse, caught only
by cropping. **`0x00E1`'s gap CLOSED the same day** (`accum_drain_e1`, run
`20260818T180039`, three drains ~11 s apart, full coverage, max frame gap 2.3 s): **nothing
renders**, verified by pixel count, by direct visual inspection, and by connected-blob
structure inside the masked region — with the scope stated in the study, namely that a bare
drain with **no UI window open** bounds the *subscriber*, not the opcode. The wire side was
re-decoded independently with our own codec (`0x0084 = [[40,41,42]]`,
`0x00D8 = [[1,1,1]]`, exact-byte consumption). **The window arm then ran too** (`20260818T184210`, same probe, byte-identical
sends, only `--actions` differing — a single-variable comparison): with **Inventory and
Skills both open and verified from the frames**, three drains changed the skill list by
**0 px**, its category headers by **0 px**, and the bag row by **0 px** — the list is
pixel-identical, `(30 Skills)`/`(19 Skills)` included. **The window-gated hypothesis, which
was the leading explanation, is refuted for both panels a player can open with a keypress**,
and upstream's `SKILL_ADD_TO_WINDOWS_END` does not mean the skills panel. What survives is
the `0x00C5` flow's own merchant/collector context, which needs an NPC and is a different
experiment. **THEN THE MERCHANT ARM OPENED A SHOP** (`merchant_window`, `20260818T211036`): replaying retail's own `0x00C4` → `0x0161`×3 → `0x0084` → `0x00CA` sequence against an NPC we spawned, **`0x00CA` opened a collector panel titled `Hatcher [Collector]` listing all three staged items by name** (Ringmail Leggings/Boots/Gauntlets, with armour values, a quantity spinner and Buy/Goodbye) — 56,928 changed pixels against 264 for the frame before. **So the accum buffer DOES feed a window, `0x0084` earns its `WINDOW_ADD_ITEMS` name, and the three drain nulls above are explained: no window was open, and the message that opens one was never among the drains.** **Priced and scaled, 2026-08-19** (`20260818T234622`): `displayed = F9 x 2 x 0x00CA-field2`, nine of nine cells exact across arms at 1.0f/2.0f/0.5f — a fixed **2x client markup** AND a **float multiplier on the wire**, which retail's `1.0f` collapses into one number. Re-arming `0x00C4`+`0x0084` reopens the shop every time, so consume-and-clear is per-window not per-session. (**Naming caution, 2026-08-18:** the `[Collector]` in that title is **our NPC's own name string**, not a window type — `content/npcs.toml`'s Hatcher resolves to "Hatcher [Collector]", the same label the heroes arc's roster showed. Nothing distinguishes collector from merchant here, and `0x00CA`'s NAME stays NOT FOUND; only its BEHAVIOUR is measured. The panel also proved three things nothing else had: `0x0161`'s **modifier array is decoded and displayed** (`Armor: 25`, `Armor +20 (vs. physical damage)`), its `enc_name` **resolves through the archive** to retail's own strings, and **`F9` is the price — confirmed from the screen**, every row reading 0 gold against `value = 0` in every content row.) The following `0x00C3[3, 0]` then crashed the client (`Assertion: item`, `ItCliApi.cpp(859)`, same-second attribution): its field 1 is **an item id, not a count** (RECONSTRUCTION — 3 was never a declared item; the one-run test is `0x00C3[40, 0]`), so the count reading is withdrawn. **And the drain question CLOSED the same evening** (`20260818T213244`, `0x00C3` withheld): with the shop open and both columns restaged, `0x00E1` changed **1** full-frame pixel and **0** in the panel, in a run where the same scorer caught the shop's own arrival at **56,910** — an in-run sensitivity control — and the panel is pixel-identical by eye afterwards. So its event `0x100000BA` has **no subscriber in any reachable context**: not bare, not with Inventory/Skills open, not with the one window that provably reads its own buffer. It still zeroes both accum counts, so the claim is **no VISIBLE effect**, not inert. **A defect in the screenshot scorer came out
of that audit and outlives it:** the player-body mask used to suppress idle animation sits
exactly where GW draws centred banners and toasts — it swallows **53%** of the `0x00B9`
callout's changed pixels — and its `delta > 28` rule is a step function (a 28-shift scores
0, a 29-shift scores 512). Never publish a null from that scorer without also looking at
the masked region. Harness trap for the next probe: **a `--walk` plan's `shot:` fires after
`alt:` releases**, so neither allegiance run captured a nameplate.

**2026-08-18, the follow-up ladder is STAGED and one fix landed.** The `0x0199` field-1
correction reached the code: the send site now fills it with `PLAYER_NUMBER` (heroes §22's
CORRECTED block; it sent `PLAYER_AGENT_ID` for two days, indistinguishable in a solo
instance), and the stale "agent id" sentences in heroes §22.1/§25.3 and pvpui §13.1 are
corrected in place. The `newopcodes` §4 ladder's three loopback probes are instrumented
and waiting on a harness slot: **`allegiance_pair`** (new probe, encodes clean, prediction
on record — settles the one CONTESTED row `0x002F`; run `--explorable`, and note the
design correction: retail's nonc→play is invisible since both draw green, so the
discriminating arm flips a `mons`-red body with the same `'play'` pair against an
untouched red control); **`0x00B9` field2=1** needs zero new code
(`smsgsweep.py --plan --only 0x00B9 --encstring --set 0x00B9:2=1`, verified in-process:
the composed payload keeps the real string and files under its own ledger regime);
**`0x0084` vs `0x00D7`** — the desk work RAN and killed the ladder's design before it
could crash a session: `0x0086` asserts the two accum counts equal (`ChCliApi.cpp(1587)`,
verified by hand), only `0x0085` drains a single list, and the appenders share one handler
so nothing can separate them. Replaced by the **`accum_drains`** probe (one appender, all
four drain events, real named ids, equal columns, assert-carrying drain last) — newopcodes
`0x0084` section's ADDENDUM has the drain table.

**A NAMED FUTURE CAPTURE: the Factions tutorial, start to Shing Jea Monastery.** Owner's
call 2026-08-17, made while walking a new character through it: *"there are definitely
some good packets in this tutorial."* Too long to bolt onto a Q11 run, so it is its own
session — and it is aimed, not speculative. What it would be the FIRST capture of, each
checked against the corpus before this was written:

- **A level CHANGING.** Property 36 has 513 sightings across four captures at values 1–20,
  and every one is a different body seen once at its create. A tutorial takes one agent
  1→8, so the same agent id receives successive values — and whatever ELSE rides a
  level-up (max health on 42? attribute points on `0x0037`? a skill point?) is a burst
  nobody has seen. A server that wants levelling has to guess it today.
- **Quest state with real quests.** The whole corpus holds 40 `0x0054` and 6 `0x0053`; a
  tutorial is dense with accept → objective → complete, which is exactly the kind-18 /
  kind-22 / kind-23 progression `studies/quests/FINDINGS.md` §9.3 reasons about from the
  client side.
- **Secondary profession selection**, which the Factions tutorial ends with — an open
  question in `studies/profession/`, and a transition no capture carries.
- **Skill acquisition and the first equipment grants**, i.e. `0x0161` item records
  arriving as rewards rather than at login.
- **Cinematics.** The tutorial has cutscenes; whatever drives them is unread.

Two properties worth naming while a tutorial capture is being planned, because both are
frequent and neither is understood: **property 66** (202 sightings, the second most common
int property, sent pre-create to NPCs) is past OpenTyria's enum and unnamed in every
lineage — see the unit-setup arc's Q7 answer — and **property 30** (`ApplyGuild1`, 223
sightings) rides the player create burst on retail and is deliberately unsent by us.

### The PvP-UI arc — OPENED and LANDED 2026-08-17, out of the heroes arc's measured wall

> **Cross-reference for the unit-setup arc's open residue above.** That entry lists "the
> heroes split-filter (§21.2)" as a leftover — the roster UI and the commander scan
> comparing `entry+0x4` against different notions of "my id". This arc bears on it: §13.1
> corroborates the commander's notion as `ctx[0x44][0x2AC]` from the UI side (heroes §22
> had it from the wire side), and §20 shows a commander binding **without** touching that
> field — the identity was never the blocker, the timing was. Anyone picking up §21.2
> should read §19 first.

Study: [studies/pvpui/FINDINGS.md](studies/pvpui/FINDINGS.md). Branch `claude/pvpui-arc`,
worktree `.claude/worktrees/pvpui-arc`.

**Why it exists.** Heroes §36.10 measured that `GmPosseRoster` — one of the eight subscribers
to the commander event `0x1000011E` — has its handler **never entered once** in a session with
the party window open and a hero row rendering, so the guarded install site `0x00578BF0` is
never reached. (The gate reading that accompanied this is retracted — see 2 below.) The
subscriber is not unregistered; **its whole construction path is absent**, and every route to
it runs through UI an explorable PvE session does not build.

**The deciding question is ANSWERED (2026-08-17, study §6), on desk work alone.** The message
is **9** — UI "frame created" — and **there is no type selector**. `hdr.param` is the instance
slot `T**`, not a type code; which control gets built is fixed at compile time by which
`UiCtlInstance<T>` was instantiated. The one runtime choice on the whole path is *which window
index was opened*, through `GmView::ShowFloatingDialog` (`0x004E1E80`, 38833) over
**`s_floatingDialogs`** — a 58-entry, 36-byte-stride registry of named windows at `0x0094BEE8`,
named by the client's own assert `GmView:2073`. `GmPosseRoster` is a child of dialog **39
`PvpItemCreate`** and of dialog 10 `DeckBuilder` — both PvP windows, now name-confirmed.

**Three things came out of it that outlive the arc:**

1. **A build hazard worth a house rule** (study §4). The static tools default to the pinned
   **38797**; the harness runs **38833**. Region drift is −0x20 to −0x160, and on 38797 the
   install site `0x00578BF0` is not a function at all but a switch jump table — so `--xrefs`
   answers "no callers" with total confidence. Pass `--exe` and stamp the build on every VA.
2. **Two corrections to heroes §36.8/§36.10** (study §7). `0x00815EA0` is the gate's *early-out*,
   not its verdict — the value returned is bit 11 of a record field nobody read — and the gate
   has **14 callers**, so hits inside it attribute to no caller. "The gate is not the reason"
   is retracted to UNVERIFIED. The handler-never-entered measurement itself stands.
3. **The commander panel is `GmPetCommander`, not `GmPosseRoster`** (study §8). It is
   `s_floatingDialogs[31..38]` (`PetCommanderPlayer`, `PetCommanderHero0..6`, handler
   `0x0050E540` → `0x0050DC50`), opened at `0x004E8990` with `dialog = 32 + heroIndex` where the
   hero index comes from `0x00524DB0(agentId)`. **Heroes was chasing the wrong subscriber.**

**Q4 is ANSWERED too (study §10), same session, still desk work.** `GmView`'s frame handler
(`0x004E27D0`, installed by `UiGame.cpp`) dispatches small UI messages 4..0x52 and events
`0x10000007..0x100001CE` through two MSVC switch tables, so a call site inside it maps back to
the exact selector that reaches it. Three sites, each in a block with **one** selector:

- `0x004E3D16` → the commander-window opener → event **`0x100001C2`**, whose **only raise** is
  `0x00567069` in **`PtTeamAgent`** on UI message 1 param 8 — **a party-row click.** So the
  commander window is **not server-openable**; the player opens it, and the server's only
  influence is over what `0x00524DB0(agentId)` finds. That is a better position than "not
  reachable": we do not need to open the window, we need the lookup to succeed.
- `0x004E38F0` → **`GmView:5890 commander`, the heroes crash** → event **`0x100001A4`**, *not*
  `0x1000011E`. Its only raise is `0x00524FD0`, which loops over 12-byte records in the same
  region as `0x00524DB0` and `0x00524C40` and raises once per record passing `0x0049C4B0`.
  Neighbouring asserts give the shape of what is missing: a `commander` with
  `slotIndex < DLG_AGENT_COMMANDERS` (the registry's `AgentCommander0..6`) and `heroData` with
  an `agentId`.

**LANDED 2026-08-17: A COMMANDER EXISTS.** Eight loopback runs, build 38833. The cause was
a **53 millisecond** race, not a wire field:

```
  +0.000s  worker     our 0x01C2 appends the hero row
  +0.000s  raise114   our 0x01B2 raises 0x10000114
  +0.053s  gmvSub114  GmView SUBSCRIBES to 0x10000114
```

`0x10000114` is the only event whose GmView case (90) calls the commander-model rebuild
`0x00524E00`, itself the only caller of `0x00524C40` — the function heroes measured as
never running. We raise it 53 ms before the module that listens for it exists, and nothing
raises it again, so the model is built once over an empty container and never rebuilt.

**`--party-mine-late SECONDS`** (new, opt-in, defaults off) re-sends `0x01B2` after the
load. `0x01B2`'s handler raises `0x10000114` on both branches, so a second send is a second
raise. With `--party-mine-late 2.0`:

```
  +2.048s  raise114   the re-send        |  before: cap=7 count=0, all slots 0x0
  +2.048s  bulk       case 90 ENTERED    |  after:  cap=7 count=1, slot0 = 0x1
  +2.054s  create     0x00524C40 RAN     |  => 1 commander(s) EXIST
```

`n=1` on the fix; the control is that runs 1–6 fire `worker` and the first raise identically
while `bulk` and `create` stay cold.

**THEN IT WAS CLICKED — three times, and the GmView chain is FINISHED** (study §24–§25).
The owner clicked the party-window hero button and the assert moved four times in one
session, each arm naming the next missing piece:

| arm | assert |
|---|---|
| before this arc | `commander` — `GmView.cpp(5890)` |
| `--party-mine-late` + `--hero-roster-id 200` | `heroData` — `GmView.cpp(5897)` |
| `--party-mine-late` | `heroData->agentId` — `GmView.cpp(5898)` |
| `--party-mine-late --hero-activate` | `inventory` — **`ItCliApi.cpp(488)`** |

Every assert in `GmView`'s case for `0x100001A4` now passes: the commander binds, its
`slotIndex` is in range, the `AgentCommander` window is constructed, `heroData` resolves,
its `agentId` is set. **The last hop was an opt-in flag, not a bug** — `heroData->agentId`
has exactly one writer, opcode `0x0072` HeroActivate, and `HERO_ACTIVATE = False`. Fifth
time in this lineage that the missing mechanism was a message already in the tree.

**PRICED AND STAGED 2026-08-18 (study §26) — the run is one click.** The `+0xD4` table is
ArenaNet's own **`inventoryTable`**, keyed by inventory id (their assert `ItCliApi:1194`
names it), and its insert has **one** wire-side caller in the image: the **`0x0144
ITEM_STREAM_CREATE`** handler — the message we already send for the player, one line above
the bags. Retail agrees 38/38 connections (`invcensus.py`; exactly one `[key, 0]` each, key an
arbitrary per-connection handle; zero `0x0072` anywhere in the corpus, so no retail hero
activation exists to imitate). The hero hop: `0x0072`'s worker stores field 3 — `HERO_INVENTORY`,
sent as 0 so far — at activation-record +8, and the party window's gear draw (`PtHero.cpp`
via `0x5265B0`) reads it back as the equip-walk key, so key 0 finds nothing and
`ItCliApi:488` is exactly the crash measured 2026-08-17. `--hero-bags` (new, opt-in)
declares the key: `0x0144 [HERO_INVENTORY, 0]` + the equipped bag. (The old text here said
"per-owner container" and pointed at the bag family — both corrected: the key is an
inventory id, and `0x013F` *requires* the container (`ItCliApi:1942`) rather than creating
it.) **THE CLICK RAN, same day: `ItCliApi:488` CLEARED — §26.3's predictions held** — and
died one floor deeper, `Array:587` in the char client (build 38833, full 40-frame stack in
`vault/captures/harness/20260818T121224/`). That floor is diagnosed and its arm staged the
same day, study **§27**: the commander panel's paperdoll indexes the char-by-id table at
`[charctx+0x7CC]` with the hero's agent id, nothing we send grows that table, and — the
correction that matters — **`0x0020` create doesn't either** (it builds a char object,
never the by-id entry, so `--hero-body` is NOT this fix). The registrar is opcode
**`0x009A`** `[agent_id, dword]`, whose handler grows the table *before* its bounds check
(hand-verified on the run's exe). `--hero-char` (new, opt-in) sends it per hero slot. **That click ran too — `Array:587`
CLEARED — and named floor three** (study §28): the doll's fallback feeds
`0x0074`'s two u32s at `+0x14`/`+0x18` (sent as zeros since the message existed) to the
**CpsMonster composite factory** as (model file id, optional skeleton file id), and the
File.cpp codec asserts `fileId` on the zero — `File.cpp(367)`, capture `20260818T142252`.
`--hero-appearance D1[,D2]` (new) fills the pair, and **the fourth click OPENED THE
PANEL** (study §28.3): title, health bar, AI-mode buttons, the hero's skill bar, and the
burrower drawn in the paperdoll — janky, no assert. **The commander panel is
wire-authorable end to end**: four floors in one day (`0x0072` → inventory key → char
table `0x009A` → appearance pair), every fix a message already in the tree carrying a
field we sent as zero or never sent. The full rig:
`--hero 1 --party-mine-late 2.0 --hero-activate --hero-inventory 2 --hero-bags
--hero-char --hero-appearance 116366`. Cosmetic residue filed in §28.3, not floors: the
Lvl 255 sentinel (prop 36 for agent 200, or a body) and the humanoid-doll arm
(`--hero-appearance 116703,116228`). **Both residue arms RAN 2026-08-19, agent-piloted
(§28.4):** the appearance pair is ORDER-SENSITIVE — `116228,116703` draws a humanoid
bust, the reverse draws an empty doll, neither asserts, so a wrong pair fails silently
(§28.5's dat chunk-walk settled the semantics: d1 must carry the FA1 skeleton chunk, d2
supplies the geometry — the content labels were right and §28.4's swapped-labels
speculation is refuted); and `--hero-level 20` (new flag, `0x009F` prop 36 pre-body)
cleared the Lvl 255 sentinel in the panel title AND the roster row. **Then the c2s wall
fell (§28.5, same day):** the open panel made heroes §3.3's triple NOT FOUND clickable,
and three opcodes came off it in one afternoon — `0x0015` HERO_AI_MODE `[agent, mode]`
(3/3 stance clicks, enum = 0x0072's aiMode; echo arm wired into authsrv, fires
confirmed), `0x001A` HERO_FLAG_PLACE `[agent, coords, plane]` and `0x001B`
PARTY_FLAG_PLACE `[coords, plane]` (compass flag widgets, arm-then-ground, n=1 each) —
all three named in `schema/overrides.json`. `--hero-vitals 480,45` (new) fills the
panel bars exactly. **Then the loop CLOSED (§28.6, still the same day):** three static
tracers found every echo and one wire run confirmed all of them — s2c `0x0062`
HERO_AI_MODE_SET moves the stance ring (and Norgu speaks his Guard line; `0x0072` was
inert because it raises `0x10000038`, an event the panel has no case for), s2c `0x0066`
HERO_FLAG_SET plants the hero flag (world model + compass marker, via activation-record
+0x10..0x1C → event `0x100000A0` → CompassCanvas, ArenaNet's verb: CommandMoveToPoint),
s2c `0x0067` PARTY_FLAG_SET plants the party pennant. The crosshair's c2s is CAPTURED and its echo
closed the same day (§28.7): `0x0016` HERO_LOCK_TARGET `[hero, target]` locks and
`[hero, 0]` clears (both wire-captured), echoed by s2c `0x0063` HERO_LOCK_TARGET_SET
(activation-record +0x20, event 0x1000003F) — crosshair lit gold with the target's
resolved name, then unlit. `0x0017` never fired (its 0x0080CEE0 guard reads a state
this rig does not set; pet container +0x6AC is the suspect) and stays medium. All named in
`schema/overrides.json`; authsrv answers `0x0015`→`0x0062`, `0x001A`→`0x0066`,
`0x001B`→`0x0067`. The commander UI is round-trip complete: click → c2s → echo →
render, six messages, all named. Hiring stays NOT FOUND with a stronger floor (all 174
channel-send callers enumerated; the party-add opcodes ride a different send helper —
that helper's callers are the next place to look). **The greyed row is settled (§28.10):**
the owner's reading was right that a body lights it — measured on the glyph colour, a
bodiless hero's name renders (182,148,148) against the player's (220,181,181) across
four runs, and a body brings it to (223,184,184) — but the positive control refutes
distance as the trigger: a body at −3000u is dropped from the compass in the same frame
and its row stays lit. The predicate is agent-presence; retail's range greying is that
same rule with server-side visibility culling in front of it (`agentroster.py`'s corpus
churn), which is a server feature we have not built rather than a message we have not
sent. `--hero-body-offset` (new) is the placement knob.
**`0x0017`'s name is RETRACTED (§28.11)** — it is not the unlock. Its branch is chosen
by a getter reading a per-agent ChCliApi `obj+0x24`, the same store GmBundle,
GmWeaponBar and GmCoreAction treat as "carrying a bundle"; the real toggle-off is
`0x0016 [hero, 0]`, its own zero form, and the crosshair paint reads both stores in the
same priority order so there was never a disagreement. The schema entry is deleted
rather than renamed (the mechanism is OBSERVED, a name would be inference) and its
writer is NOT FOUND on four searched surfaces, so `0x0017` is unreachable from any rig
we can build. **Pets DO share the commander messages (§28.12)**: `0x0062`/`0x0063` write
the pet container at `+0x6AC` with the same agent id, 28-byte records (+0x14 aiMode,
+0x18 lockedTarget) — but only after a declaration we have never sent, s2c `0x00B2
PET_ADD`; without it both mirror writes hit a NULL find and silently do nothing, which
is why the pet half was invisible all arc. `0x00B2`/`0x00B3`/`0x00B4` PET_ADD/REMOVE/
RENAME named from the client's own log strings, medium (static-only, no capture).
**`0x0074` IS READ, FIELD BY FIELD (§29)** — the arc's biggest standing unknown, and it
answers two of our own refutations. The record is a **HERO POOL entry** (the 0x9c-stride
hero-keyed array at `+0x594`, finally disambiguated from the 0x24-stride agent-keyed
activation array at `+0x584`; the same object holds both, which is what this arc kept
tripping on). Named from their own consumers: **b1 = LEVEL** (the client's own log string
says so), **b2/b3 = primary/secondary profession** (into a table whose assert names the
parameter, `ConstChar.cpp:1290`), **b5 bit 0 = hero-disabled**, **d3 = an id, 0 = none**,
and **the ten-dword chunk = an EQUIPPED-ITEM SNAPSHOT** for item slots 2..6, named from
the sibling branch of its own reader that walks the live item container when d3 is 0.
Its packer is `0x0081DE20` = HeroEnable — **the function §24.2 named as "the next thing
to read"**, now read. `b4` is a measured NOT FOUND. Two refutations explained rather than
overturned: heroes §13.2 (professions) varied the right bytes and watched the wrong
window — the roster reads the AGENT, these drive the hero-pool/search lists; heroes §30.2
(inert EncString) never had a chance, because the name copy is **gated on d3 != 0** and
every run ever made sent 0. Prediction on record: `--hero-info-name` WITH a non-zero
`--hero-flag` should change the pool/search name. Fields now authorable: level, both
professions, the disabled bit, a five-slot equipment display.
**FOUR OF THE SIX SIBLING CONTAINERS ARE NOW READ (§30)**, all eight meaning claims
CONFIRMED by their skeptics. `+0x6BC` is the **per-agent PROFESSION table** — 20-byte
records {agent, primary, secondary, a profession BITMASK, a boolean}, named by its own log
string *"OnProfessionSecondaryBits … Agent not found in sort array"* — which is the table
this server has been writing blind since 2026-08-16 via `0x00B7` (now named
AGENT_PROFESSIONS, and the hero attribute path depends on it); `0x00B6`
AGENT_PROFESSION_BITS is a second door we never knew existed. `+0x6F0` is the **per-agent
SKILL BAR**, the client's own `hotKeyState` (ChCliSkill.cpp), stride 0xBC, eight 0x14-byte
entries closing exactly on a 8-bit slot mask at `+0xA4`, driven by `0x0064`/`0x0065` (now
named) — and `0x0065` was one of §28.6's four candidates for the stance echo, so that
loose end is closed as a negative. **The minion guess is REFUTED**: `PtMinionRoster` reads
the PARTY client at `[root+0x4C]`, not this family at all, and minion-ness is a
monster-definition FLAG TEST the panel performs itself, not a declaration opcode.
**Two §29 rows corrected in place:** `+0x24..+0x43` is eight SKILL IDS seeding the deck
builder (written by sibling `0x0073`, not permanently stale), `+0x20` is their count, and
`d3` is a **packed character-appearance dword** (`s_appearanceSlot`), not an id — which is
why one field gates both the name and the equipment. **Hazard on record: `0x0073` and
`0x0074` are mutually destructive**, each zeroing what the other carries.
**THE CONTAINER FAMILY IS CLOSED (§31, 2026-08-19)** — all seven read (the sweep walks a
SEVENTH inline at `+0x5BC` that §28.12 miscounted past), and the punchline is that neither
remaining row needed new reading: **`+0xAC` is heroes §12/§13's `attribState` and `+0x508`
is skillcast §14's `BuffState`** — both fully mapped in neighbouring studies this table
never joined, the heroes-§13.1 failure twice more. The joins paid immediately:
ChCliAttrib's opcode family is **six contiguous** (`0x0036`–`0x003B`, we knew two — new:
`0x36` dequeues and UNAPPLIES a pending attribute modifier by sequence, `0x38` points+
replay, `0x39` writes a still-unnamed `+0x438`, `0x3B` single-attribute set), and heroes
§13.1's three anonymous sub-arrays now mean pending-queue / processed-sequences / the
store. The buff six are named — `BUFF_SOURCE_ADD`/`_REMOVE`, `BUFF_TARGET_ADD`/
`_ADD_TIMED`/`_EXTEND_TIMED`/`_REMOVE` (0x3F–0x44), the client's own API names, two
independent builds — with the full event set (`0x10000062/63/55/56/57`). `+0x5BC` is
GmEffect's per-agent value feed, written by `0x0093` — whose writer **updates every match
then unconditionally APPENDS** (measured; re-sending state on reconnect appends
duplicates, first-match-wins readers — a server hazard on record). ~~Still open:
skillcast §14.4's CONTESTED buff field~~ **ANSWERED same day, by running the probe
(skillcast §14.7): the field is the ATTRIBUTE RANK the effect's tooltip renders at —
three arms 0/14/12 drew pixel-identical icons whose tooltip numbers are
`round(lo+(hi−lo)·rank/15)` on skill 316's own scale windows, nine numbers, zero free
parameters. GWCA's `attribute_level` confirmed, Headquarter's `effect_type` refuted.
The run also earned the harness a `hover:FX,FY,SECS` walk verb — a HUD tooltip is now a
readable surface unattended. And the `buff_side` probe ran the same night (skillcast
§14.8): every clause held — `0x3F` alone lights the maintained-enchantment UPKEEP
MONITOR above the energy bar, `0x40` clears it while the effect icon stands, the
countdown bar is record `+0x10`'s only visible reader (absent at 0.0, depleting at 30),
and the upkeep icon needs no `0x0093`, which subtracts the one guessed consumer from the
`+0x5BC` table.**

**THE C2S SIDE IS READ, AND THE ATTRIBUTE PANEL IS A CLIENT-PREDICTION PROTOCOL — §32,
the first one identified in this repo.** The advice to "read the c2s side for a
sequence-carrying spend first" was right and it paid: a click **queues** a 16-byte
modifier at `attribState+0x400`, **applies it locally**, then sends `0x000E`/`0x000F`
`[agent, sequence, attribute]`; the server answers with the fixed triple
**`(0x0036` retire-prediction, `0x0038` points, `0x003B` attribute`)` — 14 of 14 in a
live capture**, against `(0x0037, 0x003A)` create-then-fill 8 of 8. Nine live rank
transitions price out **exactly** against `s_attribPoints` in both directions with no
free parameter. Named: c2s `ATTRIBUTE_DECREASE`/`INCREASE`/`LOAD` (upstream's names,
previously its weakest tier — now the direction assignment is measured and the two
anonymous dwords are named), s2c `ATTRIBUTE_SPEND_ACK`, `ATTRIBUTE_POINTS_AVAILABLE`,
`ATTRIBUTE_POINTS_TOTAL` (high — two arcs) and `AGENT_UPDATE_ATTRIBUTE`.
**`+0x438` is CLOSED**: the attribute-point TOTAL, 200 in all 8 live sightings, and
`studies/unitsetup` had already named `0x0039` from a level-up burst — the third cross-arc
join in two days. `0x00818E40` (never read before) shows the rank costs are **derived,
recomputed per change**, and enforces "you cannot raise a primary attribute of a
profession that is not your primary" — with `s_attrib`'s isPrimary flag on exactly ten
rows, one per profession, matching [heroes §14.2](studies/heroes/FINDINGS.md) from the
other end. Two client defects on record: `0x0010`'s framer clamps to 64 with a 16-entry
buffer, and the decrease path has no attribute bound check.

**The server still has no arm for any of the three**, and that is now a *recorded* drop
with a reason rather than a gap (`test_dispatch.py`'s `DROPPED_ON_PURPOSE`): the blocker
is not knowledge — §32.9 is a complete spec — but **state**, since ranks come from a
content row and the point budget is a constant sent for both of `0x0037`'s fields, which
those fields' new meanings make wrong (we claim every point unspent while handing out
ranks). One warning if anyone arms it: reply with the **whole** triple or none of it — the
client re-stacks unacknowledged predictions on top of fresh authoritative values, so a
half-arm is worse than the drop.

**`0x0093` IS NAMED — §33, the container family's last open field.** Its value dword is a
**MINION COUNT**, and the client says so in words rather than by position: the reader
passes it to TextApi as `%num1%` of string 50499 *'You are currently controlling %num1%
minion[s].'* (or 50498 with the agent's own name as `%str1%`), with two more GmEffect
readers agreeing — one rendering it as a number, one gating on non-zero. That **refutes**
§31.3's band-level "upkeep/maintained-effect value" RECONSTRUCTION, and it **narrows**
§30.4 rather than contradicting it: no message declares which agents ARE minions (the
roster panel decides that by its own flag test), but this one declares HOW MANY one agent
has — so that section's heading, "there is no minion message", is corrected in place.
**CONFIRMED ON A CLIENT the same night** (§33.5, captures `20260820T081504` /
`20260820T082018`): sending 7 drew a minion icon reading **7**, tooltip *'You are currently
controlling 7 minions.'*; sending 1 redrew it as *'1 minion.'* — the template's own `[s]`
plural resolving, which nothing else could drive — and sending 0 removed the row while a
buff icon sent alongside **stayed**, so the removal is specific. `AGENT_MINION_COUNT` is
**high**. Retail usage is still unobserved (zero live witnesses): the meaning is measured,
the usage is not.

**And the run produced a method failure worth more than the result — §33.6.** The first
run was called a null and was not: `--walk` and `--shots` do not overlap, so `hold*.png`
begins after the probe has cleaned up and `w*.png` is the window that matters. Worse than
the misread was the response — the artifact got a *mechanism* built from real disassembly
("the row is a child frame, so a monitor must exist first"), and a second run appeared to
confirm it. Both halves were wrong. A free positive control was sitting in the same frames
and was read as data instead. Anchor frames by timestamp, not by filename glob.

**THE ARMS LANDED, 2026-08-20 -- a player can spend attribute points on a server we
wrote (§34).** `studies/review`'s standing complaint (*"you sat there spending attribute
points and the server had nowhere to put them"*) is closed. Caged run `20260820T084923`:
the client's own Skills and Attributes panel went **27 -> 25 -> 22** unused points across
two clicks on Tactics' **+**, rank 1 -> 2 -> 3, and `20260820T085218` ran the mirror --
one click DOWN, refund 1, 27 -> 28. Three predictions made from the disassembly held on
screen: the sequence was **0 both times** (§32.2's LIFO recycling), the arrows **re-priced
themselves** after every click (`0x00818E40`, §32.4), and Strength at rank 12 shows a ▼20
refund and **no up arrow at all** (`s_attribPoints[12] = -1`, the cap rendered as a missing
button).

New: `toolkit/authsrv/attribspend.py` (pure, stdlib-only -- the cost curve and the client's
three refusal rules), `attribpoints.py --emit-content` feeding a `client-table`
`attribute_cost` table, `points_total = 200` on the player content row, arms for `0x000F`,
`0x000E` and `0x0010`, and `test_attribspend.py` (35 checks, floor 35) whose §5 REPLAYS the
nine real rank transitions from live capture `20260818T132739` and requires this model to
reproduce ArenaNet's own balances -- no free parameter. `0x0037` now carries **(available,
total)** instead of one constant twice, which retires a stale comment: its *"every live
0x0037 is [0,0], 8 of 8"* was true of two captures, and across **13 captures and 48
sightings** the corpus reads [0,0] x14, [1,5]/[6,10] x8, and [x,200] x26 -- with
field3 <= field4 in 48 of 48, which is a third, independent settling of the field order.

**AND IT PERSISTS (§34.5, same day).** Three processes: seed from the store (`55 of 200`,
`17=9, 19=12`), click Axe Mastery's **+** (`raise: 18 0 -> 1`, saved to disk), **restart** --
and a brand-new process sends `54 of 200`, `17=9, 18=1, 19=12`, with the panel reading 54
unused and Axe Mastery 1. Closing this exposed a latent SECOND SOURCE OF TRUTH: the burst
read the persisted spread for `0x003A` while `0x0037`'s balance came from the content row,
and they agreed only because nothing had ever written the store -- persisting a spend is
exactly what pulls them apart. `attribspend.seed_ranks` is now the single answer and is
tested from both sides. Ranks only are stored; the budget stays a content fact and
`available` is recomputed, so the two cannot drift. Free corroboration: the store's
pre-existing `17=9, 19=12` priced out to 55 unused and the client drew ▼11▲13 on Strength,
▼20-and-no-up on capped Hammer Mastery, ▲1-and-no-down on Axe Mastery at 0 -- four numbers
typed nowhere in this repo. Schema: `0x0038` and `0x003B` go medium -> **high** (static read
plus rendered effect); `0x0036` stays medium on purpose, since ACK is our word.

**ITEM BONUSES LANDED (§34.6, same day)** and the corpus specified them: across all 34
`0x003A` and all 14 `0x003B` in the vault the two value columns differ by **0 or +1 and
nothing else** over 94 (attribute, sighting) pairs, the +1 belonging to attribute 20 alone
in 26 of 26 sightings of one character -- whose base slid 12→7 with the bonus riding along
unchanged. So the bonus is **display-only** (every refund closed on `s_attribPoints[BASE]`;
counting it would need a cost for 'rank 13', which does not exist) and **uncapped** (retail
sent effective 13 against a cap of 12). That CONFIRMS the prediction `attribute_columns`
made against itself in 2026-08-15 -- *"if a capture ever shows the two differing, THIS is
the line that was wrong"* -- with the reading right and only its "ours wears nothing"
premise expired. The starter hammer declares `attribute_bonus = [[19, 1]]` and
`equipped_attribute_bonuses()` sums the worn set, gated on `EQUIP_WEAPON` so `--no-weapon`
is a real control. **NOT a decoding of ArenaNet's `modifiers` dwords** -- still the
character arc's largest open hole -- and the content row says so in place. On screen, both
directions: at the cap the panel drew Hammer Mastery **13 in BLUE** with ▼20 and no up
arrow; one click of ▼ sent `0x003B attr 19 = 11 +1 = 12` and drew **12 in blue** with
▼16 ▲20. The client has its own render path for a boosted attribute, and its chevrons price
off the BASE throughout -- so display-only is something the client renders, not just
something we honour. test_attribspend §10, floor 42 → 49.

Still open here: `0x0010`'s arm has zero live witnesses anywhere in the corpus and is built
to a static reading alone; and the `modifiers` dwords remain undecoded, so a bonus is
declared by us rather than read off the item ArenaNet shipped.

**Corrections this arc owes, all recorded in the study:** §4's claim that the harness runs
38833 (it selects by build and *excludes* it — use `--exe` and `RURIK_DAT`); §13.2's
container claim (refuted by RESKIN §18, which was right); §13.3's "only `0x01D9` writes
it" (refuted twice — `0x01D9` writes `+0x58`, a different field, because every `PyCliParty`
worker takes `this = object + 4` and spells `+0x54` as `0x50`); and §14.3's ordering
hypothesis (refuted — our rows land *before* the raise, which is the order the rebuild
wants). `PyCliGetMyPartyId` is `0x00856310` on 38833, not the `0x00856250` in
`agents.py:369`.

**Superseded detail below, kept for the record.**

**MEASURED ON THE HARNESS 2026-08-17 (§15-§16). Three loopback runs, build 38833, one
hero, every site byte-verified in the running process, every run reaching its map:**

- **The ordering hypothesis is REFUTED.** `worker` (our `0x01C2`) fires BEFORE `bulkraise`,
  so the hero row is already in the container when `0x10000114` is raised.
- **"Raised into nothing" is REFUTED for this event.** `lookup114`, the client's own
  subscriber-map read armed off the raise, reports **SUBSCRIBED**. The event is raised and
  delivered, and GmView's case 90 — the only caller of the commander rebuild — still never
  runs. `bulk` 0 hits, `create` 0 hits, across every run.
- `commanderpeek` with the client in the map: commander container **cap=7, count=0**.
- **§14.2's CONTESTED point is SETTLED in RESKIN's favour (§16).** `0x00858850` is a
  thiscall whose caller (`0x01B2`'s handler) passes `ecx = [globals+0x4C]+4`, so its
  `mov [esi+0x50], eax` **is** the `[[globals+0x4C]+0x54]` store. `0x01B2 PARTY_SET_MINE`
  writes it and `agents.py:434` already sends it. `codescan --field 0x54` missed it because
  the displacement is `0x50` — the base is pre-biased by four — exactly the blind spot the
  tool documents. §13.3 is refuted.
- **§4 is corrected (§15.0):** the harness does NOT default to 38833. `drive_client.py:87`
  selects by build and :167 excludes it. Running 38833 needs `--exe` **and** `RURIK_DAT`
  pointed at that run dir's own `Gw.dat`, or `contentids` refuses on maps 146/148.

**So the break is neither delivery nor ordering.** GmView's *subscriber* is `0x004ED055`
(heroes §36.7), which is not its frame handler `0x004E27D0` — two different doors, and
case 90 sits behind the second. The open question is now narrow and mechanical: **does
`0x10000114` ever reach GmView's frame-handler event half at all**, and if not, what
decides which events its subscriber forwards into the frame.

**Earlier, superseded framing, kept for the record:** The
retraction matters more than the claim: `[[ctx+0x4C]+0x54]` was already named by
`agents.py:369` and RESKIN §17.1, and RESKIN §18 **measured** it non-null and equal to 1
after the party build. So the commander model is reading our rows, not an empty list,
and §13.4's experiment is withdrawn. What survives:

- **CORROBORATED**: `ctx[0x44][0x2ac]` — reached from the UI side in this arc, from the
  wire side in heroes §22. Same answer, opposite directions. The identity is not the blocker.
- **CONTESTED**, and worth settling: `[c+0x54]` has exactly two pointer stores in the image,
  both reachable only from opcode `0x01D9`, which we never send — yet RESKIN measured the
  pointer written. Either `codescan.py` missed a store (its own footer says how that
  happens, and that is the way to bet) or §17.1 misreads `PyCliGetMyPartyId`. Neither
  side may be quoted as fact until one is checked.
- **The corrected chain** (§14.3): `0x00524C40` ← the rebuild `0x00524E00` ← its ONE caller
  in GmView's event dispatcher ← event `0x10000114` ← `0x00858850` ← the handler for
  **`0x01B2` PARTY_SET_MINE, which `agents.py:434` already sends**. So the trigger is not
  missing; the live question is **ordering** — our `0x01C2` rows go out inside the
  `0x01D2..0x01D3` window, and if the rebuild has already run over an empty container
  nothing re-raises `0x10000114`. `authsrv.py:2322`/:7896 already carry a flag for exactly
  that ordering. **Whether it has ever been run together with a commander check is not
  recorded anywhere — establish that before forming a new hypothesis.**

**Original §13 claim, kept for the record:** `0x01C2`'s FIRST
field is the container selector, not a label: `0` resolves to `[[globals+0x4C]+0x54]`, the
**default** container — which is byte for byte the only container the commander model reads
(`0x008563B0(0, n)`, arg0 a literal zero). `1..20` resolve to numbered containers. **We send
`party_id = 1`** (`authsrv.py:8159`), so the roster UI reads our row and the commander model
reads an empty list. `agents.py:560` refuses `0` on the belief that zero is a "silent" no-op
branch; the branch is real, the reading is not.

The default container is installed by **`0x01D9`** (handler `0x00857200` → `0x0085A340`, the
only two pointer stores to `[c+0x54]` in the image). **Nothing in `toolkit/` sends `0x01D9`.**

**The experiment, prediction first (§13.4):** send `0x01D9`, then `0x01C2` with
`party_id = 0`. Predicted — the container fills, `0x00524C40` runs for the first time in this
project, `0x100001A4` is raised, and the party-row click stops asserting. Refuted if the
container fills and `0x00524C40` stays cold (the identity is wrong), if `0x01D9` does not
install it (the store is gated on something unread), or if **the row stops rendering** (then
retail sends `0x01C2` twice and heroes §21.2's tension is real). Pre-empt the third by sending
the row **both ways** — one extra message settles §21.2 either way. Two of heroes' own guards
must be relaxed to run it, both documented as inheriting a belief rather than a measurement.

Separately CORROBORATED on the way: `ctx[0x44][0x2ac]` — reached from the UI side here,
already reached from the wire side in heroes §22. Same answer, opposite directions. The
identity was never the blocker. **Still worth checking early:** whether any of this shares
RESKIN §18.1's explorable gate — heroes §32 blocks `0x01BF`'s last question behind it.

**The prior is now sharper than "not server-reachable".** The wire cannot name a control type
(§6) and cannot open the window (§10.1) — but it was never supposed to. The heroes arc spent
itself on `0x1000011E` while the assert the player hits is on `0x100001A4`'s path.

### Unit models and animation — the skeleton chunk is decoded; the arc has a ladder (2026-08-16)

**`0x00000FA1` is the skeleton/animation chunk, and it is structurally decoded** —
parser found at `0x00796310` (it is the models arc's mystery "second geometry-object
producer"), header and 15 gated blocks derived from disassembly, and the derived walk
closes byte-exact on **14,571 of 14,571 FA1 chunks, the complete flags=515 population**,
with closure being our check rather than the client's. The COMPOSITED bit ⟺ no-geometry
rule was measured from the archive and from live wire traffic by agents that did not know
each other's result (14,571/14,571; 8/8, 36/36, 43/43). Trailing blocks H/I/J named
(streaks / switchable parts / particle clouds+emitters), FA6 = the model's sound-cue list
(231/231 MPEG-header oracle), FA8 = recursively-resolved linked models, and the
flags-2817 stream mystery is solved (stream-chain tails). The full evidence base is
[studies/unitmodels/FINDINGS.md](studies/unitmodels/FINDINGS.md); the ladder to
round-trip authorship (U1–U7, summit: modify an animation, rebuild the archive, the
loopback client renders it) is [studies/unitmodels/PLAN.md](studies/unitmodels/PLAN.md).

**U1 landed the same day**: `toolkit/mapdata/skelfile.py` decodes FA1 (typed
sequences/key-times layer, byte-span preservation for the U6 writer), and
`test_skelfile.py` (71 checks, floor 63) pins closure at exactly **14,571/14,571 under
`--all`** plus the COMPOSITED and span-binding oracles; the synthetic fixtures cover
what the corpus cannot (n56 fires on 0 files; block H on 0 of 20,661, now exercised in
`test_modelfile.py` together with the client's error-0x1D refusal). The full-population
run also CORRECTED the study's sabotage table — six "clean" variants carry 1–29
aliasing survivors at n=14,571 (FINDINGS §3.6) — and the measured ceilings are pinned.

**U2 and U3 both landed the same day, as parallel worktree arcs, each surviving an
independent adversarial review.** U3 (`studies/mdlrefs/`, `toolkit/mapdata/mdlrefs.py`,
30,722/30,722 reference chunks closed): the five list chunks share one client reader
whose record rule is null-word-terminated; the m_skel/m_geom question is ANSWERED — two
classes, 0x15C/0x11C, distinct deleting destructors; the mid/tail chunk families are
classified (tails = runtime collision/visibility, mids = MdlDecomp's mirror). U2
(`studies/anim/`, the typed layer in `skelfile.py`): **the animation payloads are
NAMED** — blk2C is one record per animated node carrying translation + QUATERNION
rotation + aux channels as times-prefix SoA, and the node-link byte is the
rigid-segment hierarchy itself (121,532/121,532 topological) — **the recon's quaternion
refutation is reversed**: it measured a byte-count-identical, shape-wrong overlay, and
the review confirmed the reversal from the samplers' address arithmetic plus the
client's own unit-gated fast-normalize. n40 is the sound-event table indexing FA6;
MdlAnim:367 is settled; flag bits 1–2 are ORed into one runtime bit. So the
rigid-segment reading now stands on structure, not just assert absence — custom-unit
authoring needs no skinning path.

**U4 and U5 landed the same day, the second pair of parallel review-gated arcs — the
ladder is complete through FIVE of its seven rungs, all in one day.** U4
(`toolkit/mapdata/unitassembly.py`, `studies/unitassembly/`): **wire → file closure,
54/54 pooled definitions** resolving to closed sets (1,393 distinct files; hatcher
definition 1471 = 232 files pinned id-by-id), the COMPOSITED rule derived from the
archive bit and equal to wire 0x0057-presence 54/54, and content rows resolving to
IDENTICAL sets — our server can dress a unit from `content/*.toml`. U5
(`toolkit/mapdata/unitexport.py`, `tools/blender/import_gwunit.py`,
`studies/unitexport/`): **both anchor bodies export** with the M3 re-interleave holding,
the FA1 sidecar byte-verbatim plus a typed layer that must equal a fresh decode, and a
Blender viewer measured headless (predicted-vs-measured silhouettes, exact-zero hidden
controls) — the flat placement is pinned as the bind pose by a review-measured
cloud-occupancy statistic. Honest finds recorded: the hatcher's picked diffuse is 99.9%
transparent texels (the diffuse-slot question stays open with AMAT), and the corpus FA8
graph is acyclic at depth 1, so a synthetic cycle fixture is what carries the recursion
claim. **AMENDED 2026-08-18 — that diffuse no longer renders as a floating head:** the
terrain arc's `_alpha_class` (FINDINGS 7.17) classes it an eraser and the viewer skips
its alpha, which closed the gap U5's `--opaque` control was measuring and left that
check unable to fail either way — the suite's only pre-existing red. Rewritten to assert
the new truth with a tamper positive control (the erasure stays reproducible on demand),
all four replacement checks mutation-tested red, floor 72 → 76; the texture measurement
above is unchanged and alpha's MEANING stays NOT DECODED.
[studies/unitexport/FINDINGS.md](studies/unitexport/FINDINGS.md) §5.1.

**U6 landed 2026-08-17 — SIX of seven rungs, and everything that can be proven without
launching the client is proven.** `toolkit/mapdata/skelwrite.py` re-emits the complete
population byte-identically — **14,571/14,571 FA1 chunks, 21,420/21,420 whole
containers** — and the review's mutation test (51 typed-field classes × 8 payloads,
zero survivors) proves the identity is informative, not vacuous. Identity's own catch:
header bytes +0x09..+0x0B are NOT padding (non-zero on 5,208 FA1s; consumer unknown).
The rebuilt-archive round trip holds with the nextStream chain verified; the U7
modification seam is atomic after the review's one real bug (a mid-span refusal used to
leave a half-retimed repr); and `skelfile.sound_events()`'s majority-class crash was
found by this rung and fixed — independently, twice, by two sessions in the same hour.

### ✅ U7 IS MET — the ladder is COMPLETE, and a model we authored renders in the retail client (2026-08-17)

**The summit run happened and it went green.** The hatcher's skeleton, its 85 animated
node bases scaled ×2 through `skelwrite`, drawn visibly stretched by the pinned 38797
client reading a `datmove`-rebuilt archive — owner-driven run, OBSERVED, screenshot with
the record. **Our decode → our typed representation → our encode → our container →
their renderer.** That is round-trip authorship of unit models, which is the goal this
arc was scoped around, closed seven rungs after the recon that opened it.

**It took four client runs and three of them failed on the EXPERIMENT, not the chain** —
recorded in [studies/unitmodels/U7-RUN.md](studies/unitmodels/U7-RUN.md) because the next
session will otherwise pay the same tolls: (1) the plan's named target was the worm, but
the harness's `--enemy` spawns the HATCHER and U4 had already proved those file sets
disjoint — the client never read a modified byte; (2) `Code=007` with and without the
modification, which exonerated the archive and exposed a real server bug — the 2026-08-14
crossbuild key fix lived inline in `handle()`'s auth branch and the game branch never got
it, so a 38797 client got 38833's key and the ARC4 stream was noise (fixed as one shared
`bind_key_to_build()`, with an AST regression check that both channels reach it); (3) the
`burrow` probe re-creating a body at a fresh agent id while a combat AI drove the first,
so three things animated the target at once.

**What the run settled beyond the summit.** A **stored** flags=515 row IS acceptable to
the client — the arc's named risk candidate, REFUTED, and retail ships that row
compressed. A COMPOSITED shell's own FA1 poses its creature. And **pose and playback rate
come from different places**: ×4 on the same file's key times changed nothing visible
across two operator-reviewed clips, which is a real constraint on `studies/anim`'s timing
reading and the sharpest open question this arc leaves.

**The standing wall, named precisely**: the shell's first FA8 link (15018) carries 1.5 MB
of FA1 — 237 sequences against the shell's sparse set — and cannot be written back.
`datmove` refuses it in its own words ("nothing fits… the largest run datplan will hand
over is 953,856 B") because retail ships it compressed, we write stored, and no
compression-8 encoder exists. **Authorship that reaches the full animation set needs that
encoder, or an archive permitted to grow** — that is the next arc, and it is a decision
for the owner rather than a gap in this one.

### The archive write-size wall — the arc is DOWN and the encoder is now AUTHORING INFRASTRUCTURE (2026-08-18 → 2026-08-20)

**2026-08-20, ~12:24 — A10 RAN, owner-driven, P1 FIRED. PLAYBACK TIMING LIVES IN THE
LINKED KEY CLOCK, AND IT IS NOW AN AUTHORED CONTROL SURFACE.** Study §19.6, and the
ANSWERED block in `studies/anim/FINDINGS.md` §6. Owner, on video: *"normal in control
then slowed down in the deployed"* — the between-runs control N6 required, and the
retime did not hedge where U7's did, because U7 retimed the n3C tag track in the one
file where the clock does not live. Instrumented record all green: our 15 rows
byte-identical through the client's Flush, sweep exactly retail's 177,319/0, coupling
re-measured on the ACTIVE bytes 237/237 + 242/242, 30 walk cycles logged, no crash
dialog — and **N2 is retired by the client itself, which played key times 3.09× beyond
retail's shipped ceiling**. Magnitude recorded honestly as "visibly slowed vs baseline"
(not frame-measured ×4). **The ladder's capability story closes: authored CONTENT
(run 7), CREATED rows (A9), authored TIMING (A10) — all client-proven at compression 8,
in place.** The A10 archive is LEFT DEPLOYED — the hatcher animates at quarter speed by
design until `a10stage.py --retail --yes`.

**2026-08-20, midday — A10 WAS STAGED: the FA1 write-back, re-authored onto the PROVEN
clock; the launch is the owner's.** Study §19; runbook `vault/research/archivewrite/
A10-RUN.md`. The U7-era edit (§17.8 item 2's "re-author the payload") turned out to be
**structurally a null** — it scaled the n3C tag table, while the sampler reads `blk2C`'s
76,008 channel times and the clamp windows on the SAME clock (both max exactly
22,883,332). The staged edit retimes that proven clock **×4 across 15 rows in place**
(fourteen linked files + the shell's 234 coupled windows; 222949 dropped at +4 B of
slack; n3C/`u32_0F`/n40 stay retail everywhere after a verifier showed no partial scaling
preserves both measured couplings — "Design B"). Verified by **blind re-derivation, 15/15
byte-identical, with a Design-A control red on 11 of 15**; two isolated rebuilds
hash-identical; whole-4.2 GB diff zero unowned bytes; every row fits its own reservation
(15018 at 1,016,720 B, +12,912). **Both launch outcomes are findings**: quarter-speed
animation (foot slide is the shape cue) ⇒ playback timing lives in the linked key
clock; null ⇒ it does not — sharpening `studies/anim`'s open timing question, and not
dismissible as "file not read" since run 7 proved the channel renders. Named risk first
in the failure list: ×4 exits retail's attested time envelope 3.09×. Procedure: baseline
clip FIRST (no within-frame control exists), then `a10stage.py --deploy --yes`, the
run-7-style harness line with `--walk`, video, `--verify-after`, `--retail --yes` or
leave. **H8 is live** — a client ran in the shared run directory at 11:44 on 2026-08-20
from another session; confirm nobody is mid-run before deploying.

**2026-08-20, ~09:40 — A9 RAN, owner-driven, GREEN on every pre-registered prediction.
THE RETAIL CLIENT READ A ROW THIS PROJECT CREATED.** Study §18.6. Owner at the keyboard:
*"Hatcher with normal animations/proportions"* — which, by the measured load-time fact
(the FA8 loop resolves every link at spawn and requires `m_seqCount != 0`), IS the
verdict that the `datalloc`-created chain under new file id `0x5F0AD` was resolved,
decompressed from our compression-8 bytes and parsed as a skeleton, and the retargeted
20,060 B shell — a small row compressed by us — read on the way. Instrumented half: 37
`walks to` cycles + 54 attack/cast lines in the gamesrv log, **no crash-dialog.txt**;
archive after: preflight 10/10, crc sweep 177,322/0 bad, only scratch rows 8315/8316
moved, **our 16 rows byte-identical and the created chain intact through the client's
own Flush** — nothing repaired or discarded, MFT numbers unmoved (H1 never fired), and
the client accepted our ASCENDING chain where retail's all descend (H7 answered). Still
deliberately unclaimed: E3's rider (no instrument shows the client opened rows
8295-8306, so the all-skip shape stays without a client witness) and the two
phantom-pair shapes (unshippable on real content). `report.json` was never written —
the owner closed the client mid-hold — and the verdict does not rest on it. **The A9
archive is LEFT DEPLOYED**; `a9stage.py --retail --yes` restores the baseline.
`datalloc.py`'s "no client has ever read a row this module allocated" caveat had its
FINDINGS-39 moment and is superseded with scope stated (one chain shape, one build,
one launch). **With this, every layer of new-content authoring is client-proven:
encode (A8), edit in place (run 7), grow/relocate (offline, §17), CREATE (A9).**

**2026-08-20, earlier — A9 WAS STAGED: the client oracle for §17's shapes, one launch, the
owner's to run.** Study §18; procedure `vault/research/archivewrite/A9-RUN.md`. The staged
archive (`vault/exports/archivewrite/a9/Gw.a9.dat`) carries three independent arms — a
`datalloc`-CREATED 3-row chain under new file id `0x5F0AD` holding 222949's payload
compressed by us, the hatcher shell retargeted 4 bytes so the client's own FA8 link walk
resolves that row **at spawn** (load-time resolution measured at `0x00794850`: every link,
`m_seqCount != 0`, so a normal animating hatcher IS the verdict), and twelve byte-identical
small rows re-encoded in place as an unscored rider carrying the attested all-skip
declared-5 table. Skeptic-verified GREEN, including a from-scratch **byte-identical 4.2 GB
rebuild** and a whole-file diff attributing every changed byte to exactly the intended
rows. Two envelope shapes (both phantom pairs) are UNSHIPPABLE on real content — 0
occurrences over every dial and the archive's 2,500 most compressible rows — and stay
recorded, not forced. Deploy: `a9stage.py --deploy --yes`, client closed, run directory
confirmed free (another session used it at 00:11 on 2026-08-20); launch:
`python toolkit/harness/session.py --enemy --hold 150 --shots 10`; then
`a9stage.py --verify-after`; then `--retail --yes` or leave deployed. **Never click the
client's crash dialog** — its default button uploads a dump to ArenaNet.

**2026-08-20 — THE AUTHORING HARDENING LANDED, `0802b1f`, study §17, corrections §0 C-11/C-12/C-13.**
A6–A8 proved the encoder on one big row; what stood between that and *authoring new
content* was four named gaps, and all four are closed offline: **(1)** every table our
encoder emits is now a retail-attested SHAPE — `gwentropy.authoring_table`, floors dist ≥ 5
/ lit ≥ 257, closing §13.5's gaps A, B, the distance half of C, and D, with the A8 anchor
row **byte-identical** (crc `0xd03ab671` now pinned in the suite) and the lift costing
**+0 B on 120 real small retail rows**; **(2)** `datwrite.replace(grow_to=)` grows a shrunk
row back — §14.4's "fatal for a second write" defect, reproduced then fixed, with one
`_grow_gate` shared with `--restore`, which gained the EOF/MFT/withheld-run refusals by the
factoring; **(3)** the journal is a durable file — measured **34.1× / 533 MB** write
amplification on a real run and a torn flush that lost the whole journal, now 1.00×,
fsync-per-record, torn-tail recovery, all 59 vault journals still parse; **(4)** `datalloc`
gained the fidelity gate an adversarial verifier proved it lacked — **a corrupted-trailer
gwenc stream reached disk GREEN through `alloc(confirm=True)`** (528-flip census: 394
wrong-bytes streams accepted), and `expect=` is now mandatory with `extraBytes 8`, the gate
running in `alloc()` too because `alloc(plan=)` bypassed `plan_alloc` entirely. The
capstone is **`test_authorflow.py`**: one synthetic archive, six steps at compression 8 —
author → create a NEW row under a new file id → revise smaller → grow back → outgrow,
refuse, relocate → revert to pristine **byte-for-byte** — because this arc's two worst
defects (C-6, §14.4) were compositional and green in isolation. Floors: gwenc 55→60,
datwrite 138→199, datalloc 100→177 (TESTS.md had said 98), authorflow 59 new; suite
affected-set all green, srclint 22/22. **Not consulted: the client** — no retail client has
read a small-row or datalloc-created output yet; that one-launch check is §17.8's item 1
and rides the next convenient launch. The skeptic pattern paid for the **fifth**
consecutive rung (a builder's "proven end to end" was true of framing only), and the
matcher is priced at ~0.19 MB/s / 82 MB peak — fine for the loop, recorded so nobody
re-measures it.

**Full study: [studies/archivewrite/FINDINGS.md](studies/archivewrite/FINDINGS.md).** Five
routes scouted, each attacked by its own skeptic; **four of five verdicts overturned**. A
separate pass answered the durability question `studies/datwrite` named as decisive and left
open for eleven days. §3's ladder is A1–A8; **A1, A2, A3, A4, A6, A7a, A7b and A8 have all
run — only A5 has not.** (This paragraph read "Nothing is built" for a day after A3 and A4
landed, and then said A7 and A8 "have not" run for a day after both did.)

**RUN 7 FIRED, 2026-08-19 — study §11.7. A LINKED FILE'S CONTENT REACHES THE SCREEN, and
the arc's animating question is ANSWERED.** Owner, at the keyboard: *"their bodies are kind
of twisted like pretzels… idle/walk/cast all have pretzel model animations."* Six runs had
failed to show it. `vault/research/archivewrite/a4stage7.py` flipped every rotation key in
fourteen linked files by 180°, wrote all fifteen rows **in place at compression 8**, and the
retail client rendered from every one: spawn 8 of 8 PASS, **no assert**, and the post-launch
diff shows only the client's own scratch rows 8315/8316 moved, no growth, and **our 15
edited rows byte-identical after the launch**. That validates the compression-8 write path
under a CONTENT change, which A8 — byte-identical payload by design — could not. **The
positive control failed and is recorded as a failure (§11.7b)**: the head was not enlarged,
and the reason it costs nothing is §11.6e's decision-table rewrite, which scores that exact
cell ANSWERED where §11.5's original scored it ABORT. A8 rewrote its design: **fourteen of the hatcher's fifteen linked
animation files fit their OWN reservation compressed**, including the two §11.5 called
unreachable, so the run relocates nothing, grows nothing and changes exactly 15 rows in
place. It also produced correction **C-10**, which reaches backwards — `blk2C` bases are
**absolute model-space rest positions**, not the bone lengths §9.3g called them, refereed by
ArenaNet's own mesh.

**A6 IS RUN, 2026-08-18 — the entropy layer costs +8 bytes, and that is a SMALLER result
than it sounds.** Study §10. `toolkit/mapdata/gwentropy.py` + `test_gwentropy.py`, 91 checks,
floor 91. Re-costing retail's own token stream for row 11196 under a from-scratch canonical
Huffman plus this format's meta-coder gives **1,029,572 B against retail's 1,029,564 B —
+8 B, +0.00078%**, meeting the prediction pre-registered on 2026-08-17 ("within 0.5%") by
roughly 640×. **A6 does not kill the encoder arc.**

**But the honest reading is the skeptics', and it must travel with the number: A6's headline
was close to unfalsifiable.** Huffman optimality is a theorem, so the token term — 95.6% of
the stream — *had* to tie, and the extra bits, `block_size` fields and header are retail's by
construction. Only 13,486 bits of table transmission were genuinely free, against a tolerance
of 41,184. What A6 excluded is a defect in **our own cost model**, which was worth excluding;
the decision-relevant risk was always the **LZ77 matcher and A6 does not touch it**. §1.2
stands: the pass/fail boundary sits inside deflate's own tuning range. **The number that
should be quoted instead of +8 B:** row 11196's table transmission is 1,686 B = **25× the
row's entire 68 B of reservation slack**, one extra block costs ≈105 B = **1.5× the whole
authoring budget**, and the row is 15.58 blocks — so a matcher producing merely **+2.7% more
tokens buys a 17th block and overflows the reservation on table overhead alone.**

**Two skeptic results are larger than A6's own, and both are capability.** Retail's stored row
was **re-emitted BYTE-IDENTICALLY** (row 11196 at 1,029,564 B with `crc32` matching the MFT's
own recorded value; **428 rows total, zero failures**, drawn from outside the module's witness
list). And **ArenaNet's table encoder is identified: it is longest-run greedy**, reproduced
bit-exactly on **2,194 of 2,194 tables**. So every piece of a compression-8 encoder now exists
**except the LZ77 matcher** — a bit packer was fed to `build_table` on those 2,194 tables with
**zero refusals**. That re-prices A7 downward.

**§4.5's literal-only question is answered and the answer is DEAD:** row 11196 as Huffman
literals with no LZ77 is **1,421,280 B, ×1.3805 of retail and 391,648 B OVER the reservation**.
Only 32,952 of 1,021,421 tokens are matches — 3.2% of tokens carrying 32% of the compression.

**One rule violation caught by the skeptic pass and corrected in the same commit.** The
module, its `framing_bytes()` docstring and its TESTS.md entry all claimed the framing model
*predicts* the MFT's own `size` field, "a field that is not an input to the calculation". It
does not: `ar.raw(e)` slices the payload to `e.size`, so agreement is forced for every stored
size divisible by 4 — **138,708 of 138,708 comp-8 rows**. It is **a check that cannot fail**,
which CLAUDE.md forbids by name, and it is now demoted to bookkeeping at all three sites.
Three other over-claims, all in our favour, are corrected in §10.6.

**The wall was misframed, and correcting it shrinks the arc.** U7 recorded 15018 as "1.5 MB,
unwritable". It never needed 1.5 MB of contiguous space: the row **already owns a 1,029,632 B
reservation and already ships compressed at 1,029,564 B**, and the 1.5 MB is what it
decompresses to. So the bar is not *beat ArenaNet by 7.35% to fit a 953,856 B free run* but
*match ArenaNet within 3,732 B, in place* — and `zlib -9` already clears that. Verified
independently (row 11196, ratio 0.679645; the shell 116228 agrees to four decimals at
0.679015).

**Two routes may skip the encoder entirely and both are free reads.** A1: is the sequence
index space global across the FA8 link graph? If yes, adding a 16th linked file is
transparent and nothing needs compressing. A2: does a *realistic* edit still fit the
reservation — measured elasticity is +806 B at 0.1% of slots retimed but **+8,725 B
(overflow) at 1.0%**, so the encoder may be unable to deliver the thing it would be built
for. **Both were skipped by scouts who then costed multi-session builds on top of the gap.**

**REFUTED: `nextStream` is not a continuation link.** 44,699 of 44,700 link targets begin
with their own container magic. A payload cannot spill across two rows. Do not re-derive it.

**Two live defects in our own tooling, both confirmed by the session lead:**
- `datmove` flattens `compression → 0` unconditionally, so **there is no safe relocation verb
  for a compressed row** — moving one produces a green archive holding an unreadable file
  that passes all three checksum rules and all ten open-time rules.
- `archive.py:322` reads the header `mftOffset` as `<I` while `datcheck.py:223` and
  `datwrite.py:101` read `<Q`. Latent today and **it caps archive growth**: the live MFT sits
  121,634,304 B below the u32 ceiling.

**Durability is answered, and it is the reason this arc gets a safety rung before a feature
rung.** "Repair" means **discard** — the client adopts a surviving older MFT generation and
then deletes the entire `nextStream` chain of any row whose payload CRC mismatches,
persisting after one launch. The genuine one-way door is quieter: a bad **12-byte header
CRC**, or a repair that finds no valid generation, returns zero with **no log line** into
`ArchiveCreate`, which writes a fresh empty archive over the file. Six MFT generations
survive in the study archive (measured, counters 26,881 down to 8,735) — which is what makes
this recoverable-in-principle rather than fatal, and why no allocator may consume the shadow
rotation region. **Operational rule, now standing: never launch the client on a suspect
archive; diff it first. The launch is the irreversible step, not the write.**

**A1 AND A2 ARE RUN, both 2026-08-17, and between them they took the compression-8 encoder
off the critical path.** Study §7 and §8.

**A2: GREEN, and the rung as written was vacuous.** The edit it named
(`scale_sequence_keytimes`) can only move 692 B of a 1,514,855 B payload, so retiming ALL
237 sequences costs **+7 bytes** — a gate that cannot perturb its input. The honest version
against the curves (86 nodes, 76,008 samples): translations ×2 costs **−21 B**;
requantizing every float to a 1/1024 grid costs **−467,928 B, i.e. 46% smaller than retail
ships it**. My stated prediction that requantization would be expensive was **refuted** —
coarser grids make mantissas more repetitive, so the adversarial case is the compressible
one. The residual risk is therefore inverted: not that an authored payload is too big, but
that a *higher-fidelity* one could be. Nothing measured bounds that, because every edit
preserved the sample count. Also: the best of 16 deflate configurations is **11,930 B
smaller than ArenaNet's own output**, so the encoder's difficulty is format conformance, not
ratio.

**A1: PER-FILE, by blind replication — two researchers from opposite ends, each told to
refute the hypothesis they were assigned, both independently returning PER-FILE.** The
selector is **named**: the FA1 parser swaps the first two record fields, so disk `u8@+0x00`
lands at runtime `+0x04` and is read at `MdlAnim 0x007822F0` as a **1-based** index into the
FA8 link array (`links[sel-1]`: 31,700/0 = 100.0000%, against a 0-based rival at 0.82% and a
random-link null at 8.06%). Indices are born bounded by one file's own count — the key
lookup is a `lower_bound` over a single file's array with **no fall-through** — and the
32-byte runtime record is fully enumerated, leaving **no field that could carry a global
base**. `242 = 2 + 110 + 125 + 5`, reproduced independently from the selector histogram; the
old `242 = 237 + 5` is dead.

**WHY THAT IS THE GOOD OUTCOME, despite reading as the bad one.** A 16th FA8 record is
necessary, safe and inert — *safe* is measured, since **retail ships 410 unselected links
across 63 shells**. Playback needs new sequence records in the **shell's** own FA1. So the
file to rewrite is **116228: 29,802 B decompressed, 20,236 B stored in a 20,480 B
reservation** — the 20 KB shell U7 already rewrote successfully. **Retail's 1 MB link 15018
is never touched, and the 1.5 MB wall does not arise on this path at all.**

**A4 now has a near-ideal oracle.** `0x00804240` is a variant *picker*, and the call site
passes a literal `push 0`, so the client chooses **uniformly at random among sequences
sharing a key**. With 216 of the shell's 224 keys single-variant, appending one record on an
**existing** key with selector 16 gives a **50/50 coin flip between retail's animation and
ours on every play** — self-controlling, unmistakable, and needing no invented key. Hard
constraint for that rung: the array is `lower_bound`-searched, so a record is **inserted in
key order, never appended**.

**Retracted in `studies/anim/FINDINGS.md`**: the reading that 592 files carry indices keyed
by "a linked model's larger sequence space". All 149 out-of-range values sampled are exactly
`0x10000` — a sentinel, not a cross-file index. The `0x0078007F` mechanism named alongside it
is correct and is now corroborated.

**A3 AND A4 ARE BUILT, 2026-08-17.** Study §9. Nothing has been launched.

**A3, the safety fixes** — seven items, floors `test_datcheck` 84→112, `test_datwrite`
78→87, `test_datplan` 38→44. On the real archive: **6 MFT generations** (`--generations`,
3.4 s) and **177,327 payload CRCs recomputed, all matching** (`--crc-sweep`, 2.4 s). The
`<I`→`<Q` fix removes a silent cap on archive growth. `datwrite` now refuses
`[0x00,0x10)`, the one corruption with no recovery path, which until today was protected
by *absence*. `datplan` projects a generation's declared extent across run boundaries — a
mark is where a signature sits, not where the table it declares ends. One item was
**removed after a single test run because the fixtures refuted it**: the generation census
is a property of an archive's history, not its validity, and pre-flight costs 1.7 s
precisely because it never reads a payload.

**A4, the additive path** — `toolkit/mapdata/unitauthor.py`. On the real hatcher shell the
whole edit is **+29 bytes**: 15 links → 16, 242 sequences → 243 inserted in key order, and
key 805313525 goes from 1 variant to 2. Two of the three things it must get right cannot
fail a checksum and cannot fail any of the ten open-time rules — the array must stay
sorted for the client's `lower_bound`, and the FA8 list is positional so a link is
appended rather than inserted — so the test inserts at the front, middle and end of the
table and unsorts it by hand to prove the refusal fires. 30 checks, floor 30.

**A8 IS GREEN, 2026-08-18 22:16 — THE RETAIL CLIENT READ A ROW THIS PROJECT COMPRESSED.**
Study §16. Deployed and launched on loopback, pinned build 38797, agent-driven with the
owner's explicit go-ahead. `RUN VERDICT: PASS (target: map)`, **8 of 8 capture checkpoints**,
body in the map at t+17.4 s. The Hatcher spawned, **walked, attacked and cast repeatedly for
the whole 150-second hold** — the three animation classes this arc has chased — while row
11196 sat in the archive compressed by `gwmatch` + `gwenc`. **No assert anywhere**: a grep
for `assert|MdlAnim|MdlSeq|MdlLoad|error|crash` across all three logs and the report returns
nothing.

**The archive survived the launch**, which is the check that matters because the client
Flushes and a repair is permanent after one: preflight **10/10**, CRC sweep **177,319
payloads 0 bad**, size **unchanged**, and **row 11196 still 1,011,244 B at compression 8,
decompressing to 1,514,855 B**. Two rows moved — 8315 (88→92 B) and 8316 — which are the
client's own scratch rows and independently reproduce `studies/datwrite` §6's caged-session
observation. **Nothing of ours was repaired or discarded.**

**So the encoder arc is FINISHED — A6, A7a, A7b, A8 — and §2.2's standing worry that a round
trip through our own decoder "proves agreement, not correctness" is answered by the only
oracle that could answer it.** The 1.5 MB wall this arc opened against is down, and 62% of
the hatcher's animation records stop being unreachable.

**What A8 does NOT settle, measured rather than assumed: gap A is untouched.** The deployed
row's 218 tables declare literal counts 257–285 and distance counts 24–30, with **zero tables
declaring fewer than 2** — so the `symbol_count == 1` shape our encoder emits on small and
degenerate payloads was never reached. Its fix stays costed and unspent. One envelope claim
*is* directly widened: the row declares a minimum of 257, below retail's attested floor of
258, and the client read it, retiring that part of gap C.

**A8 was STAGED earlier the same day.** Study §15.
`vault/research/archivewrite/a4stage8.py` built
`vault/exports/archivewrite/a4run8/Gw.a4run8.dat`: row 11196 (file 15018) **re-compressed by
OUR encoder** to 1,011,244 B, 18,320 B smaller than retail's, fitting **in place** with no
relocation. **The payload is byte-identical to retail's 1,514,855 B — the only variable is
who compressed it**, which is what makes "no visible change" the PASS and any assert
attributable to the encoder alone. Verified independently of the script that built it:
size **4,198,489,600 B unchanged**, preflight **10/10**, generations **6/6**, CRC sweep
**177,319 payloads 0 bad**, **1** row changed, five neighbours byte-identical, and the row
decompresses to the original payload with the declared size matching.

**The deploy and the launch are the owner's** — the launch is the irreversible step (§5.6
rule 1: the client Flushes, and a repair deletes the whole `nextStream` chain permanently
after one launch). `python vault/research/archivewrite/a4stage8.py --deploy`, then look at
the hatcher; `--retail` restores the baseline.

**Correction to the arc's own state note:** the deployed archive is **RETAIL, not run 6** —
`vault/run/.../Gw.dat` was restored at 21:34 that day by another session, and the handoff
claimed run 6 for hours afterwards. Check the run directory before believing any claim about
it; it is shared.

**THE WRITE PATH IS BUILT, 2026-08-18 — and the skeptics found FOUR holes in it.** Study
§14. `datwrite.replace(..., compression=8, expect=payload)` writes a compressed row and
**decompresses to verify before committing** — the only refutation available, since
`datcheck.py` has zero references to compression codes and the entry CRC is over the *stored*
bytes, so a wrong payload passes every checksum rule and all ten open-time rules. `datmove`
gained the **safe relocation verb for compressed rows that C-6 said did not exist**, and C-6
was reproduced live on a synthetic archive before being closed. Every existing caller is
untouched by default: all six `a4stage*.py`, `deploy.py`'s subprocess, `iconset`, `rebloat`,
`textwrite`. Floors `test_datwrite` 87→138, `test_datalloc` 98→100.

**The four holes matter more than the verb.** All were found by hostile reads of code written
to prevent exactly them: (1) the C-6 arm was gated on `expect is None`, and since
`expect == data` is trivially true for any bytes, one documented CLI command wrote compressed
bytes under a stored code with **exit 0 and a log line indistinguishable from an ordinary
replace**; (2) `--overwrite` never reached the guard, so overwriting a comp-8 row with
plaintext left a green archive whose `Archive.read()` returns **zero bytes**; (3)
`datalloc`'s gate matched a two-byte marker without decoding — **the row CREATION path, the
one A8 will use** — and its own test asserted that defect as correct; (4) a check labelled
"a compressed payload past the reservation" was a duplicate of the C-6 check, because the
fixture compressed 12× and fitted. All four fixed.

**§14.3 is the finding to carry forward: this is the FOURTH consecutive rung in which a check
claimed more than the artifact delivered** (§10.6, §12.7, §13.6, §14.2), three of them
shipping after the previous correction was written. The technique that has caught it every
time is **sabotage — disable one arm and require a named check to go red.**

**A7b IS RUN, 2026-08-18 — GREEN. THE COMPRESSION-8 ENCODER EXISTS.** Study §13.
`toolkit/mapdata/gwenc.py` + `test_gwenc.py`, 55 checks; three skeptics, none refuting.
**Retail's own stored rows re-emit BYTE-IDENTICALLY** — row 11196 at 1,029,564 B with
`crc32 == 0xF862D5C4 ==` the MFT's own recorded value, and **3,051 distinct rows across five
archives, plus a skeptic's independent ~5,990 more across seven, with ZERO failures and no
failure class.** That check does not depend on `gwdat` being a correct decoder, which is why
it is the one that matters. **And our own encoder emits real bits**: `gwmatch` → `gwenc` →
unmodified `gwdat.decompress` returns the payload, with row 11196 at **1,011,244 B — equal to
A7a's model to the byte, 18,388 B under the reservation.** §12.6's remaining risk is retired
(328 encoder-implied tables serialized and rebuilt by `build_table`, 0 refusals).

**Two measurements make `gwdat` far more trustworthy than §2.2 recorded.** The bit order is
corroborated from **ArenaNet's own source lines** — the client's bit layer is
`P:\Code\Base\Compress\CmpIo.h` and it has a bit *writer* whose preconditions are exactly
ours (`CmpIo:138`, `CmpIo:139`). And decoding ArenaNet's **own** row 8295 with an
upstream-faithful `build_table` **FAILS**: `gwdat`'s zero-length repair, long recorded as a
divergence from both upstream lineages, is **required by ArenaNet's own archive**.

**The one gap to carry into A8, with its fix named.** Our encoder emits declared
`symbol_count == 1` on 3.4% of tables where retail does so **0 times in 138,708 first
blocks**, so byte-identical re-emission structurally cannot cover it. If the client refuses
it, the fix is a two-symbol distance table inside retail's attested envelope — a size
question, not a design one. **Still unbuilt for A8: the `datwrite` compression-8 arm, the
§5.6 safety gates, and the owner at the keyboard.**

**Corrections: the trailer double-count recurred a THIRD time** — §3's A7 ladder row still
carried the trailer-exclusive `≤ 1,029,628 B` as the acceptance criterion, which is the row a
cold session reads *as* the bar. Fixed. Two `test_gwenc` fixture annotations also claimed
table shapes the fixtures do not produce; both corrected in §13.6.

**A7a IS RUN, 2026-08-18 — A7_VIABLE, and the win is the BLOCK PARTITION, not the matcher.**
Study §12. `toolkit/mapdata/gwmatch.py` + `test_gwmatch.py`, 62 checks, size-only, still no
bitstream. Row 11196 comes out at **1,011,244 B against its 1,029,632 B reservation —
18,388 B of slack, and 6,394 B better than the best of 18 raw-deflate configurations.** Our
token stream is **12 tokens** from retail's out of 1,021,421: the matcher is a dead heat.
The win is bought by **109 blocks against retail's 16** — 74,777 more table bits to save
221,778 token bits. Cross-validation exact to the byte: our tokens on retail's own partition
give 1,029,572, **identical to A6's re-cost of retail's own tokens**.

**This substantially reverses §1.2's population case against the encoder.** 25 random
compression-8 rows from 200 KB to 1.5 MB: **ours beats retail 25 of 25 and fits 25 of 25,
where raw deflate fits only 14 of 25** — and the three rows §1.2 named as zlib's worst
overflows (+7,142, +5,800, +5,259) all fit under ours. Honest counterweight, the skeptic's:
on those hard rows our margin is 0.003–0.01%, so row 11196's 1.8% is a favourable draw
exactly as §1.2 warned. And at the best dial setting we fit even on retail's own partition
by 60 B, so the partition buys the *size* of the win and robustness across the whole dial
rather than fail→pass. **The budget in payload terms, which §7.3 asked for and nobody had:
18,388 B of slack ≈ 34,273 B of extra payload — 2.26% growth, against retail's own 127 B.**

**A7b — the bitstream writer — is now the only unbuilt piece**, and no table this encoder
implies has ever been serialized and rebuilt by `gwdat.build_table`.

**A check that cannot fail turned up for the SECOND time in two rungs** and is corrected:
A7a's C1 closure is genuine on retail's stream and forced on ours. Recorded in §12.7
because the defect class survived a rung that had just been corrected for it.

**RUN 7 IS DESIGNED AND DE-RISKED, 2026-08-18 — not staged, not launched.** Study §11. A
design pass proposed it; three skeptics on distinct lenses **all refuted it**, and the
salvage is worth more than the design. **The trap that blocked this rung is solved without
finding the cast file:** the hatcher's most universal animation is base key 3,259,067,510
(1.067 s), present in **26–32 of 32 corpus shells**, and all six of its weapon-class variants
are served by **selector 10 = file 109464 — 27,948 B stored, WRITABLE, already relocated in
run 5**. That is locomotion, and the harness re-triggers it whenever the player walks >120 u.
**Provoke the walk, not the cast.** Ship a 180° rotation flip on the writable links
(length-preserving, so no record, key table or window changes) plus the head-cluster ×3
positive control — nodes 51–64, audited as genuinely the head by rebuilding the hierarchy
from `blk2C` parent links. **Do not decimate**, even though it works: its rotation error is
p99 46.6° / max 169.3°, the same order as the flip that is supposed to be the readout.

**A real mechanism was found and its strong form refuted.** The client's animation key is
arithmetic: `key = 0xE0000000 + (23·G) + C(letter)` at `0x007F1DD0` — the `imul …,0x17` was
hand-disassembled from the pinned image and the calibration family recovered *blind* from the
archive at 90–100%, against five control lattices scoring 0. **But "key mod 23 names the
weapon class of every record, absolutely" is false**: the client's table has **12 letters**,
26–37% of records are off-lattice, the largest single class (61 records, 25%) is emote-shaped
and off-lattice, and `SEQ_FALLBACKS` (`AvSeq.cpp:253`) means the client sweeps *every* letter
rather than committing to one. The lattice is a good instrument; it says nothing about which
file serves the cast, because the selector byte already does, 242/242.

**Correction C-9, and it makes A5 cheaper.** §2.5's *"the population supporting 'the client
reads a large stored row' is EMPTY"* is **stale by our own hand**. Retail's 19,292 B ceiling
still reproduces exactly, but `datmove` writes compression 0 unconditionally, so **run 5
shipped eleven stored rows above it — largest 765,378 B — deployed and launched with no
assert**. The honest bar is 11× the largest proven-read stored row and **0.5× the largest
already deployed without a crash**.

**SEVEN CLIENT RUNS, 2026-08-17/18. Handoff:
[studies/archivewrite/HANDOFF.md](studies/archivewrite/HANDOFF.md).**

**The arc's two opening premises were both WRONG, and that is its main output.** File 15018
never needed 1.5 MB of contiguous space — it already owns a 1,029,632 B reservation and
ships compressed, so the bar is *match ArenaNet in place* (zlib clears it) rather than
*beat them by 7.35%*. And **bone lengths come from the SHELL, not from the linked animation
files**: run 5 scaled twelve links' bases across 32% of the creature's records and nothing
changed, while run 6 scaled the shell's and the hatcher exploded (OBSERVED, owner
screenshot). The rest skeleton is replicated into every animation file and only the shell's
copy is used. **So the compression wall does not block shape authoring at all** — the lever
is a 29,802 B file we can already write.

**Proven at the retail client:** a shell we authored renders (U7, reproduced larger as run
6); the client accepts a **16th FA8 link and a 243-record sequence table** with no assert;
and our authored records **are selected** by the client's own variant picker. **Not shown:**
a linked file's *content* changing the screen — the only property tested in a linked file
is the one linked files do not own.

**Also corrected:** retail's nine record-shape invariants are now measured at 100.0000%
(252 shells, 31,700 records, plus an independent 6,000-id sample), and two of them killed
the coin-flip design outright — a key must exist in the linked file's own table, and equal-
key runs are homogeneous, so a key is served by exactly one file.

**Previously recorded and still true:**

**THE RUN HAPPENED, 2026-08-17, and the client ACCEPTS the addition.** Study §9.3c.
`RUN VERDICT: PASS (target: map)`, exit 0, eight of eight capture-derived checkpoints, body
in the map at t+16.3s, **no `MdlLoad`/`MdlSeq`/`MdlAnim` assert**. The retail client loads an
archive carrying a **16th FA8 link and a 243-record sequence table**, with the relocated
29,831 B **stored** shell and a newly allocated row at file id 389632. Every named rejection
risk for the additive path is REFUTED, and A4's criterion is met **at the client**.

**What is NOT settled is whether our record was ever PICKED.** The owner's report —
*"sometimes it feels altered but I'm not sure"* — is not a verdict, and that is the
experiment's fault: the variant sat on **1 key of 224** and its content was a duplicate of a
working file, so even when picked it looks plausible. Worse, `--shots` skipped **every**
screenshot (`client not foreground`), so no measurable record exists. **Next run: scale the
linked file's node bases and attach the variant to every single-variant key** — U7 proved
that changing SHAPE is unmissable where changing timing is not. Standing instruction from the
owner, adopted: spawn anything to be looked at **~150u to the player's left or right**, never
in front, because the player model occludes it.

**Previously recorded as the remaining risk, now closed by the run above:**
Everything above is archive-legal and self-consistent, which is exactly the state the two
dangerous defects would also produce. `datcheck.py` has zero references to compression
codes and nothing we own can refute a conforming-but-wrong result. **The client is the
only oracle.** The run is designed with its prediction stated in §9.4 and is **waiting on
the owner's go-ahead**; the target must be a creature the harness actually spawns, which
is the toll U7's first run paid.

A1b — who fills the per-agent key array — remains downgraded from blocking to
worth-doing.

### Quests — the lifecycle runs end to end; two known bugs left open (2026-08-16)

**A quest we authored is offered, accepted, tracked, advanced and turned in at a real
client**, with the offer and turn-in screens carrying a reward line and the marker moving
between giver and objective NPC. `studies/quests/` has the arc; `content/quests.toml` is the
table; `toolkit/test_quests.py` (62 checks) is what holds it.

**BUG 2 IS FIXED 2026-08-19 AND ITS DIAGNOSIS BELOW WAS WRONG IN BOTH HALVES; BUG 1
STANDS, AND THE TWO WERE NEVER ONE FIX.** The block below is left as written because the
error is instructive — read it, then read this. The client does **not** walk you over on
its own: 46 c2s INTERACTs across five keyed captures carry **zero** `0x003E MOVE_TO_COORD`
within 100 ms, and the 2026-08-16 session's own capture has the player's position
byte-identical across two clicks 1.34 s apart. The walk is a **server** order,
`GAME_SMSG 0x002A AGENT_UPDATE_DESTINATION` — decoded and named `high` in
`schema/overrides.json` all along, never once sent by `authsrv.py`, the fifth time the
mechanism was already in the tree. ArenaNet also does not DROP an out-of-range interact;
it answers it after about `(gap − range) / 288 u/s`, the walk's own duration (1054 u:
predicted 2.79 s, observed 2.56 s). Both behaviours now exist: `_order_walk` sends the
order, `interact_pending_tick` serves the held interact on the client's own reported
arrival, and `toolkit/authsrv/test_interact.py` (19 checks, floor 19) covers a path
nothing in the suite touched before. **Bug 1 is untouched and still admitted-invented** —
no measured talk range exists in this repo, the client has no distance gate on either
send, and the one real 156.0 proximity constant has no call edge to the click path — but
it is now independently tightenable, which is exactly what the "one fix" framing denied.
The verification run is staged and not yet done (harness contention).

**TWO BUGS ARE KNOWN AND DELIBERATELY LEFT** — owner's call, end of session 2026-08-16.
Neither blocks the lifecycle; both are wrong against stock and should be fixed before this
is called done.

1. **`INTERACT_RANGE = 250.0` is TOO FAR.** Owner walked it and says so. The constant is
   ours and admitted unmeasured — an attempt to read ArenaNet's off the corpus produced
   541–4275 units, which is a bad join rather than a range (the player's position is unknown
   at most interact moments and the agent positions available are stale spawn coordinates).
   The cheap fix is a probe that walks a player in and finds the boundary the client itself
   uses; the cheaper one is to take the owner's number.
2. **Clicking an NPC does not AUTO-WALK the player to it.** In stock, clicking a distant NPC
   walks you over and the dialog opens on arrival. Ours does not move the player at all, so
   with (1) fixed the player would simply be unable to talk to anything they are not already
   standing on. **These two are one fix, not two** — the range gate is only correct once the
   walk exists, and shipping the gate alone would make the quest unplayable.

**What is NOT done beyond those:** no reward is GRANTED (the grant protocol is 0 of 22,524
s2c in the corpus — this line said 23,495 until 2026-08-19, a denominator the study itself
never used — and is its own arc), the quest name — authored 2026-08-19, string id 100552, see
the Q2b paragraph below — has not yet been SEEN on a screen, and the giver/objective
binding is by AGENT ID, which is per-connection and per-spawn — a probe-world binding, not
a content one (R5's job).

**RUNG Q1 LANDED 2026-08-16, and it was the arc's unbanked value.** Fifteen of the nineteen
quest opcodes were **absent from `schema/overrides.json` entirely** — `QUEST_ADD`,
`QUEST_DESCRIPTION` and the `0x0080`/`0x0081` dialog pair existed only in a study document,
invisible to every tool that reads the schema. Now: **12 named, 1 renamed, 4 deliberate
abstentions**, each with its own evidence chain and confidence.

The evidence for eleven of the twelve is the **frame bus**, and it was made refutable before
it was used. `studies/quests/FINDINGS.md` had both halves — §1.6's publisher VAs, §2.1's
handler bodies — in two tables and never multiplied them. The pairing was **predicted**
structurally (*the two adds share a frame id, the two text-fills share one, the three marker
ops — one shared payload layout — do not*) and then read out of the pinned image: **11 of 11**.
It is committed as `toolkit/clientscan/framebus.py` with `test_framebus.py` (18 checks, floor
14, §1 runs on a bare machine) so every row's `why` is reproducible by RUNNING, not by
rewriting a scratch script.

**The result worth carrying: `0x004E` VICTORY_BANNER → `QUEST_COMPLETE_PANEL`.** Its body
`0x0080F670` does `push 0x10000155` / `call 0x00633D70` — posting into the band
`GmQuestComplete` subscribes to. FINDINGS §7.6 had ruled that question needed *"one narrated
live session in which the operator completes a mission. Nothing static will substitute."*
Half the join was in its own §1.6 table. The 2026-08-13 smsgsweep had **already** fired the
opcode at a client and photographed a centre-screen banner, filed `medium` because a name
from a picture is a guess about purpose — the static join supplies the purpose, and the two
lineages share no ancestry. **The reward arc is not unblocked, but it is one loopback run
from its first real question** (what the panel expects in its three dwords), rather than a
live capture campaign away from it.

Two process notes, both cheap and both paid for. The **call window** failed twice by
returning a confident short list rather than an error — §1.6's own scan at 6 bytes lost two
sites, 24 lost `0x0050`'s (its call sits at +29 behind three payload stores). And naming CMSG
`0x0014` made `test_dispatch.py` §7 **go red before** its `DROPPED_ON_PURPOSE` row landed,
which is the tripwire working rather than a gap.

**Q1b is done, both halves:** `toolkit/content.py` no longer declares a single cited assert to be
refused expression — the trap that would have re-run the 2026-08-12 over-refusal, and the last
place still carrying the old wording four days after CLAUDE.md fixed it. §7 Q3's REFUSED
bullet now forward-points to its own refinement; the dated ruling text was left alone.
**(a) landed 2026-08-17 and was bigger than one row.** §6.1 gained TWO Fournux rows --
`textrec.py`'s `id // 1024` string-id split, which that module's own docstring says was
**not** re-derived by us and which is held up by an oracle rather than a second reading,
and `skilltable.py`'s 0xA4 record layout, which was. Fournux is MIT, so the missing
`THIRD-PARTY-NOTICES.md` entry was an unmet **licence obligation** rather than an untidy
table, and it is there now. Three further Fournux citations owe nothing and §6.1 says so,
so the next audit does not re-decide them.

**AND THE CLASS IS CLOSED, NOT JUST THE INSTANCE.** §6.1 opens with `gwdat.py` landing as
a port of an unlicensed repo the day after the plan forbade it, and ends that paragraph
*"The rule was in the plan; nothing was checking."* It still wasn't. `content.py` guards
the row-level half; nothing looked at MODULES, which is how Fournux went 100+ citations
and two real derivations without a row for four days after two studies flagged it.
`toolkit/derivlint.py` + `test_derivlint.py` (20 checks, floor 17) check it now. **The
design decision is measured rather than assumed:** 21 upstreams appear in 223 (module,
upstream) pairs and `gw-preservation/server` alone is in 106 modules -- *because* it is
the one we may not copy -- so a per-pair rule is the permanently-red test that gets
deleted. The check is per-upstream: fourteen, each accounted for by a row, a notice, or a
`NO_DERIVATION` entry naming its site. Its sharpest check reproduces a real error --
`PLAN.md:33`'s prior-art LANDSCAPE table was once read as a register row and recorded as
fact, and a whole-file substring search repeats that and scores the tree clean.

**The 66/66 is now a check** (2026-08-17). `toolkit/clientscan/codedstr.py` +
`test_codedstr.py`, 18 checks, floor 12: §3.2's re-encode 66 of 66, its per-slot shape
partition, and the plain-22/encrypted-44 split, plus the rival raw-word reading as a
CONTROL that could have won. The ENCODE half had never existed anywhere, so that
headline number was reproducible only by rewriting the script behind it. It also caught
a live instance of the rival reading: `questdefs.py`'s `LITERAL_MARK` comment said
"archive id 263", the raw word, where the id is 7.

**Q6 IS BUILT, TESTED OFFLINE, AND NEEDS ONE RUN TO GET ITS VERDICT (2026-08-17).** The rung turned out to be a LIFETIME question rather than a message one: `state = {}` is per connection, so held quests died at every map transition before any replay could matter. `QUEST_PROGRESS` carries `quests`/`objectives_done` across connections and deliberately does NOT carry `desc_sent` — carrying that would make the replay skip the `0x004C` that arms the description-filled flag, and every objectives line after it would be a silent no-op appearing only on the SECOND map. We send `0x004C` before `0x0054`, which is NOT ArenaNet's order: they trip their own gate twice in the corpus, and copying it would reproduce a visible bug that fails invisibly. `test_quests.py` §§17-19, 74 checks. **The acceptance criterion — walk a portal, the log survives — needs a client and is the owner's.**

**Floor 73, recomputed.** `test_quests.py` carried a DERIVED floor of 17 ("13 row-independent checks plus 4 per row") that was right when written; the file grew to 74 against the same one-row table and the floor never moved, so a healthy run did four times its own minimum and three sections could have vanished unnoticed. A derived floor goes stale silently where a measured one goes stale loudly.

**FLAGGED, NOT FIXED:** `authsrv.py` holds `MAP_ID_COUNT = 877` and now `NO_MARKER_MAP = 888`, both meaning "one past the last map" in different places. Either they are two different quantities or one is wrong, and nothing here has measured which — 888 is re-derived from `areatable.py` by `test_quests.py` §19, 877 is not. Do not quietly make them equal.

**THE 38797→38833 RE-CHECK RAN 2026-08-17 AND EVERY CLAIM HELD.** The eleven quest handler bodies were re-derived by a different route — the client's own receive table via `msghandler.classify` — matching FINDINGS §2.1 11 of 11 on the pin and **unmoved on 38833**. Twelve byte-level citations are byte-identical across the two builds, the frame-bus pairing is 11 of 11 on both, `CHALLENGES` is 1465 on both (the authored-id band is intact) and `areatable`'s extent is 888 on both. What moved: the dispatch stubs (+0x60, uniform) and the `UiCtlWebLink:576` assert site (+0xD0).

**The scope is narrower than "these addresses are stable", and the check says so.** On the vaulted 38519 build — ~90 days older — **0 of 12 sites match and the frame-bus scan finds nothing in any quest body at all.** So the claim is that nothing moved across the 15-day 38797→38833 patch, which is much smaller than durability; 38519 is now the control that proves the equality is a measurement rather than a tautology. `test_quests.py` §20 (77 checks) re-runs the whole thing, and a fourth vaulted build is covered without an edit.

**THE THREE DWORDS ARE MEASURED — the loopback run this block asks for below RAN
2026-08-19, agent-piloted, and the panel named its own fields** (harness
`20260819T071548`, `--probe quest_panel`, five sentinel arms with the prediction filed
first): **dword 1 is EXPERIENCE, dword 2 GOLD, dword 3 SKILL POINTS**, read from the
panel's own toast — the (111, 222, 333) arm rendered *"You have earned 111 experience,
222 gold, and 333 skill points!"*. Zero-valued fields are omitted from the sentence,
which explains the 2026-08-13 sweep's silent banner (its all-zero payload suppressed
the toast entirely); the panel re-fires per send, five renders in one session; max
dwords render unsigned with no assert. The arm-3 hypothesis (field 1 = quest id) is
REFUTED — 1463 came back as "1,463 experience". **What it is not: a grant.** The Level
chip read 1 beside a 4.29-billion-experience toast, and
`0x006C`/`0x0096`/`0x0097`/`0x00FB` stay 0-of-corpus — display vs grant is now the
reward arc's live-capture question. `studies/quests/FINDINGS.md` §9.6 is the record;
the probe stays registered as the completion-panel calibration.

**AND THE OTHER FOUR PUBLISHERS ARE ATTRIBUTED — §9.3's "next static question" ran
2026-08-19, same day.** The five frame ids GmQuestComplete subscribes to are published
by exactly the five completion-family opcodes: `0x006C`→`0x10000156`,
`0x0097`→`0x10000157`, `0x0096`→`0x10000158` (**mind the swap** — frame-id order does
not follow opcode order), `0x00FB`→`0x10000159`, each body located through the receive
table and the pairing confirmed by two instruments (msghandler's disassembly,
framebus's scan). The scene and the 0-of-corpus family CLOSE ON EACH OTHER, which
structures the grant question: `0x0097` is the one message carrying a STRING (the
rewards-blurb candidate, RECONSTRUCTION), `0x0096` is gated on completion-flag bits
(the sweep's assert), and a loopback ladder over those with the `quest_panel` rig is
the next cheap probe. `framebus.py` prints the pairing and `test_framebus.py` asserts
it (27 checks, floor 16); `0x0096`/`0x0097` get `why`-only schema rows per §9.4's
restraint. `studies/quests/FINDINGS.md` §9.7.

**AND THAT LADDER RAN THE SAME DAY — `0x0096` IS MISSION_COMPLETE (§9.8).** Two probes,
`completion_gates` then `completion_rewards`, bodies disassembled first: one flag bit
draws the whole 3D scene (so `0x0096` alone suffices — the "underfed" caveat retires for
it), and the client's own crash class `UiMsgQuestCompleteMissionNonMedal` IS the name.
Field 1 = `completionFlagsGained` (bit0 "completed the mission", bit1 "completed the
bonus goal", gate at `GmQuestComplete.cpp:729`, pinned to f1 by the f1=0 crash); fields
3/4/5 = the reward triple that rendered **"111 experience, 222 gold, 333 skill points"**,
decoding f3=xp / f5=gold (middle slot, record `{4,f3,f5,f4}`) / f4=skill points. `0x0097`
cold dies at `:678` ("No valid case for switch") — it is a sub-panel keyed by a u8 over
state a PRIOR completion message stages, name still abstained. **Still DISPLAY not GRANT**
(the toast reads back what we send; XP bar unmoved). The completion DISPLAY is now fully
mapped from our server; the grant and `0x0097`'s priming message are the live-capture
remainder. `0x0096` earns its name in overrides.json (measured effect, §9.4 bar cleared).
`studies/quests/FINDINGS.md` §9.8.

**Q2b's AUTHORING HALF RAN 2026-08-19.** `textwrite.py --set 200 "A First Errand"` wrote
OUR name into text file 98, record 200 (string id 100552) of the reskin-roster archive —
in place, journalled (`questname.journal`), read back exactly, neighbours and identity
tier intact — and `content/quests.toml`'s `enc_name` now commits the bare id as the
two-word varint `[0x8103, 0x0CC8]` (`codedstr.encode_id`), replacing ArenaNet's `0x3D64`
placeholder. `textwrite.py` gained the generic `--set RECORD TEXT` source (the 188 skill
names were a special case). **AND THE SCREEN HALF RAN THE SAME DAY — Q2b IS CLOSED.**
Probe `quest_name_authored`, agent-piloted, harness `20260819T085654`, reskin-roster
client (the one archive holding record 200): the control arm rendered 'Ascalon' and the
treatment arm rendered **'A First Errand'** in BOTH the tracker and the 'Quest Added'
toast — an A/B in one run, riding `0x0049`'s last-pushed-becomes-active write. The quest
now announces itself in our words on their renderer; the reskin-roster pairing trap is
recorded in the probe's note. **Then 877 vs 888** — the FLAGGED paragraph above is the whole of what is
known, and which one is wrong is a measurement nobody has taken.

**Two runs were what the arc was waiting on; the loopback one RAN 2026-08-19 (the dwords
paragraph above), so Q6 is the run that remains.** **Q6 needs the owner:** walk a portal, the
log survives. The code and its checks are landed, and nothing offline substitutes for that
criterion. What is left of the reward arc past the panel display is the GRANT protocol,
which is a live-capture question (a narrated mission completion), not a loopback one.

**And the largest piece is the two known bugs at the top of this block, which are ONE fix and
not two:** the range gate is only correct once click-to-walk exists, and shipping it alone
makes the quest unplayable. Neither half is measured, and the cheap route to the range is
still the owner's number rather than a probe.


### Heroes and henchmen — R4c-H MET, hero row renders, next gate NAMED (2026-08-16)

**The caged run happened and R4c-H passes** — `studies/heroes/FINDINGS.md` §10, four arms,
build 38833, map 90. Read §10.2 before doing anything else with this family: the
discriminator arm shows **`0x01BF`'s name and trailing bytes do not drive the roster row**,
which is the opposite of what the upstream field names invite, and the body-only arm looked
like a confirmation because both sources carried identical values.

**The hero arm ran the same day and closed two of its three blockers** (§11): `0x01C2`'s
word order (msg+0xc is the agent id), and **what creates the `charHeroData` record — it is
`0x0074`**, proven by one message's presence flipping the diagnostic assert between
`attribState` and `charHeroData`. **The gate moved rather than vanished**, and where it moved
is the headline: `ChCliAttrib.cpp:156`, hero **attribute state** — §4's negative, now named by
the client itself.

**What is left here, in order.** *(Refreshed 2026-08-16 after §18-§22; the previous list
had gone stale on four items that were since closed, which is the drift the top of
`CLAUDE.md` is about.)*

0. ~~**What writes a HERO's attribute record?**~~ **CLOSED (§13).** `0x0037` creates the
   attribState record, `0x003A` fills it, both AGENT-keyed and both already in `authsrv.py`
   since the combat arc. The TEMPLATE system was a **RED HERRING** (§12.3, confirmed:
   `AccountTemplateDataSkill` is account-local and its closure holds zero message handlers).
   Do not re-open it and do not re-run the `0x0074`-chunk hypothesis (§12, refuted).
   ~~The live gate is `ConstChar.cpp(1296)`~~ — **also closed (§14): there are TWO profession
   stores.** `0x00A6` writes the agent's profession bytes (the roster label); `0x00B7` writes
   `ctx[0x2c]+0x6BC`, which is what the ATTRIBUTE code reads. Sending `0x00B7` for the hero's
   agent cleared it.
1. ~~**`0x01C2`'s `msg+8`**~~ **CLOSED (§21): it is the OWNER PLAYER NUMBER.** Both rigs the
   old list asked for were run — hero index 2 (§18) and a different player number (§21).
   ~~`msg+0x10`~~ **also closed (§19): `0x01C2` carries NO hero identity at all**; identity
   arrives entirely on `0x0074`/`0x0072`, and `msg+0x10` is inert on every observable.
   ~~What writes `ctx[0x44][0x2ac]`~~ **closed (§22): `0x0199` INSTANCE_LOAD_INFO field 1.**

2. **THE LIVE UNKNOWN — the commander-panel click**, `commander` / `GmView.cpp(5890)`.
   `inventoryId` was the named suspect and is **refuted twice** (§16); do not re-try it.
   The desk work is done as far as it goes (§17, §20): commander objects live in a container
   at `ctx+0x20`, `heroCommanderSlot[7]` at `ctx+0x30` holds **keys** into it, `0x00524C40`
   is a get-or-create, and `0x00524DB0` — the one the click uses — does **not** create. The
   creator's caller is a loop over `activeHeroes` built by a party-agent scan.
   ~~**Next, identify the event that runs that scan**~~ **DONE (§23), and the leading
   hypothesis was WRONG.** The commander branches are cases of one GmView switch
   (`sub eax,0x10000007; cmp eax,0x1c7; movzx [0x4E66C4]; jmp [0x4E6480]`): the scan is
   event **`0x10000114`**, the crashing branch is **`0x100001A4`**. `0x10000114` is raised
   **from the PARTY MANAGER** at `0x008588AD`, in the same region as `0x01BF`'s and
   `0x01CB`'s workers — **so the trigger IS server-provokable and the panel is not outside
   what a server authors.** `0x100001A4` has two raisers: inside the scan itself (after the
   create loop) and in **PtHero** — the party-window button, which raises it directly and so
   hits the non-creating resolver when the scan never ran.
   ~~**Next, item 1 first…**~~ **BOTH DONE (§25).** (1) The iterator walks
   `party->container[0x24]`, bound `[party+0x2c]`, **stride 24** — confirmed against
   `0x01C2`'s writer **on the same build** (`0x00859010` on 38833, NOT the 38797 address this
   arc had been quoting), and every §1.2 field offset reproduces. So `[edi+4]`/`[edi+8]` ARE
   `msg+8`/`msg+0x10`; the chain is confirmed, not invalidated. (2) **`0x01C2` raises
   `0x1000011E` (case 93), NOT `0x10000114` (case 90, the bulk scan)** — and `0x10000114`'s
   raiser has eight callers, **all UI**, none a message worker. So the bulk scan is
   UI-triggered and no message provokes it, while our message drives the INCREMENTAL path:
   case 93 applies the same my-id filter and hands a key to `0x00524CC0`, which walks the same
   iterator and derives the commander SLOT by counting my entries. **This revises "the scan
   never runs"** — true of the bulk scan, not the whole story — and confirms §21/§22's mirror
   from a third code path. **Loose end, flagged:** case 93's `[esi+4]`/`[esi+8]` may read past
   the 8-byte payload `0x01C2`'s worker builds, so those exact offsets are RECONSTRUCTION;
   the structure around them is solid. **RESOLVED (§26.1):** the payload's second dword is the
   ENTRY POINTER (`ecx`, set at `0x00859089`, never reassigned through the six stores), so
   case 93 dereferences it — and §21's behavioural arms corroborate the semantics without
   needing the plumbing at all.
   **NEW, OBSERVED (§26.2): `0x01C2` raises its commander event only on a party-cache MISS.**
   `cmp edi,[mgr+0x4c]; je <epilogue>` at `0x008590AF` skips the raise when the party is
   already the cached one — a real, previously unrecorded gate.
   **It looked like the answer and is REFUTED (§26.3).** `--hero-post-commit` proves nothing
   (post-commit the party is still 1, so the condition under test never changed — a confound
   I nearly scored as a result); `--hero-bust-cache`, which opens a build on party **2** first
   so the hero-add must take the slow lookup, **still asserts identically**.
   **NEXT IS RUNTIME, NOT MORE STATIC READING.** Three static hypotheses have now been refuted
   by experiment on this one question, and what is needed is a single measurement of whether
   the event fires at all — a breakpoint or code-cave trace on `0x008590CA`. `CLAUDE.md`
   carve-out 3 permits native tooling explicitly.
   **DONE, and it needed no debugger (§27).** The commander context is a **plain static global
   at `0x00C07850`**, so the RESULT can be read instead of the event trapped:
   `toolkit/clientscan/commanderpeek.py` (new, pure ctypes through `keytap`'s read-only
   reader). Live, with the hero authored and the roster row drawn:
   **`container ctx+0x20: cap=7 count=0`, all seven `heroCommanderSlot` entries zero.**
   **NO COMMANDER IS EVER CREATED** — so §26.4's "key mismatch" branch is REFUTED (nothing is
   filed under any key) and "the creation path never runs" is confirmed. The party entry IS
   present, since the roster renders its archive-resolved name from that same `party+0x24`
   array. **Still open:** empty does not distinguish *the event never fires* from *case 93
   runs and its my-id filter rejects*; that needs a trace on `0x008590CA`, and the case for
   spending native tooling is now made of a measurement rather than a hypothesis. Note
   `ctx[0x44][0x2ac]` is NOT readable the same cheap way — `0x0047F660` goes through **TLS**
   (`fs:[0x2c]`), so it needs the target thread's TEB, not a global read.
   **Then the next cheap read WAS TRIED AND WAS WRONG (§28).** The UI subscriber map at
   `0xc11bc4` reported **NO SUBSCRIBER** for all three commander events — refuted on the spot
   by evidence already in hand, since `0x100001A4` demonstrably reaches its handler (it is
   what raises the `GmView:5890` assert). Dumping the buckets confirmed the reader was blind:
   512/512 slots non-empty and no event-id-shaped value at any offset, because the lookup
   hashes through `0x004920B0` and the walk never sees real keys. `commanderpeek --events`
   now **refuses to answer** unless it finds that control first; both branches verified
   offline. **So the subscriber question is unanswered and is NOT cheap** — it needs the hash
   replicated (a second thing to get wrong) or the trace §26.4 already named.
   **Loose end:** the control gate has no committed test, and a new test file needs its
   `TESTS.md` entry in the same commit.
   **Method note worth carrying, now cutting both ways:** three static hypotheses were killed
   by client runs at ~7 minutes each and what moved it was four dwords of live memory — but
   the very next live read produced a clean, memorable, completely FALSE finding, and only a
   built-in positive control caught it. Measure the state; then check the instrument against
   something you already know.
3. **Desk leftovers, mostly closed.** ~~(a) the scan trigger~~ **DONE (§23, §25).**
   ~~(c) `msg+0x14`~~ and ~~(d) aiMode~~ **DONE (§31): both inert on every observable** —
   though the aiMode result is **UNINFORMATIVE and must not be read as "stance does nothing"**,
   because our server has no follow AI for a stance to act on. Still open: **(b) `0x0074`'s
   other 17 fields**, where the prior after §12 and §30.2 is that most are inert on the
   surfaces we can see.
4. **`0x01BF`'s two trailing bytes and its wire name** — measured negatives, not just missing
   asserts (§10.2). The untested candidate is the **outpost hiring UI**, which needs
   RESKIN §18.1's explorable gate solved first.
5. ~~**Retry the family under `--encstring`**~~ **CLOSED (§30.2).** Superseded for `0x01BF`
   from §10 onward (a real EncString is what makes the henchman row render a name), and the
   last untested case — `0x0074`'s `string16(32)`, empty in every run until now — was sent
   with a real one: 71 bytes, `4 name ids`, and the row still reads `Mo1 Goren`. **Neither
   name-bearing message in this family reaches the party roster.** Also recorded (§30.1, free
   from existing screenshots): the hero row's label MIXES sources — profession and level from
   the AGENT, name from `s_heroClientData` via the hero id — which is why a Monk-bodied
   "Goren" renders without complaint. The henchman row takes all three from the agent.
6. ~~**`heroes_table.py`**~~ **BUILT (§29).** A thin emitter over `consttable`'s locator, so
   there is one place that can be wrong about where the table is. It carries **no address**:
   it anchors on `ConstHero.cpp` and REFUSES any geometry that is not 40 × 24, naming the
   title-table trap in the refusal. Closure holds on the byte (`base + 40*24 == anchor_off`).
   Ids only — `--resolve` refuses a whole column. `vault/content/heroes.toml` written; all 40
   rows pass `content.py`'s real `_check_provenance`, and stripping `extractor` makes it
   refuse. `test_heroes_table.py` floor 10, catalogued in the same commit.
7. **Follow AI** — unbuilt work rather than an unknown; the movement messages exist.

**A defect this arc shipped, and the guard now standing over it.** `HERO_ATTRIBS`,
`HERO_SKILLBAR` and `HERO_BODY_NPC` landed with no module-level default while the world-load
path read them unconditionally, so **every default launch** died with NameError inside the
instance load and showed the client `Code=007`. Two other sessions hit it and one spent its
first attempt on the archive, because a server-side NameError and a bad map row look
identical from the client's side. Fixed, and `srclint.conditional_globals` +
`test_srclint` §8 (floor 20) now fail on the shape.

**Two environment facts this run measured — and the FIRST IS RETRACTED (§24).** The 38797
pin **runs fine**: its failure was the crossbuild key bug (a 38797 client handed 38833's key
on the game channel), fixed 2026-08-17 as `bind_key_to_build()`, and the whole hero arc
reproduces on the PIN with the row reading `Mo1 Goren`. The archive half is real but concerns
maps 146/148 and was wrongly carried onto a map-90 run — the evidence was in my own log
(`starting with the newest, rurik_dh_2026-08-13…` two lines above `build=38797`). The
retracted claim read: ~~the **38797 pin cannot
currently run**~~ (its archive has 146/148 mid-replacement; on 38833 those maps bind different
files than `dat_study`) — clean explorable maps on the 38833 pair are **90, 474, 558**; and a
client `Code=007` is usually **our** crash, so read `gamesrv.log` for a traceback before
believing the dialog.

### Heroes and henchmen — the commander question is MEASURED and the arc is closed (2026-08-17)

The arc is [studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md); R4c's row in §3
carries the summary. **Everything below this paragraph is history, kept because it records
what was tried.** The arc's last wall — §26.4/§27.2/§32's *"does `0x008590CA` execute, and it
needs a breakpoint or code cave"* — was spent on 2026-08-17 and **answered**:
`toolkit/clientscan/commandertrap.py` (hardware breakpoints in DR0..DR3, pure `ctypes`,
nothing written into the client) shows the raise **does** execute once the party-cache gate
opens, and its handler **never runs**. `0x00524C40` never runs either, confirming §27's
`count=0` from a second independent instrument. **The event is raised into nothing: what is
missing is a SUBSCRIPTION, not a trigger** — so no wire field can bind a commander, and the
authored hero is complete for everything the server governs. FINDINGS §33.

**And the successor question is answered too — FINDINGS §34.** The subscriber question §28
declared off the table (the map hashes through `0x004920B0`, so a bucket walk cannot read it)
needed no hash at all: the raise is `call 0x491f20; test eax,eax; je`, so **`eax` at
`0x0064CA47` IS the subscriber list** for the event in `[ebp+8]`. Read there,
`0x1000011E` has **`subscribers = 0`** — raised into nothing, mechanism and all.
Control-verified by a 4000-hit census: 54 distinct events, 23 of them subscribed, so the
reader demonstrably says both things. *(Its FIRST control run said NO SUBSCRIBER to
everything and would have confirmed the finding falsely — all 32 hits landed inside one 4 ms
burst of a single event, because a hot site's default ceiling is not a sample. A control that
samples badly does not fail loudly; it agrees with whatever you were about to conclude.)*

**2026-08-17, latest: it REPRODUCES 4 OF 5 (FINDINGS §35.5).** Three more late runs with
`worker,raise,lookup,case93` armed all ran the full chain, each with its own live subscriber
pointer (`0x272BA958`, `0x25EE9D78`, `0x25BF7AA8` — four distinct addresses across four runs,
so it is a per-session list rather than a static). **Sending the roster sequence after
`INSTANCE_LOAD_FINISH` reliably finds a subscriber for `0x1000011E` where sending it inside
the load reliably does not.** The one stall (run 10) did not arm `raise`/`lookup`, so it stays
unattributed and is recorded as a 1-in-5 rate rather than explained away. **STILL UNEXPLAINED
and now the whole question: case 93 runs and NO COMMANDER IS CREATED** (`count=0` across 14
samples), so the break sits between case 93's entry and the get-or-create — the my-id filter
or `0x00524CC0` itself.

**AND THEN DOWNGRADED AGAIN, FINDINGS §35.6 — the late rig makes the client ASSERT, 4 of 4:**
`Assertion: SkillListContext::SKILL_LIST_USERS != skillListUser`, in every late run and in no
inline run. So every late measurement was taken from a client that asserts during the session,
and "the subscriber appears later" cannot be separated from "the client is in a degraded
state". §35.1/§35.5 are **CONTESTED**, not corroborated. What survives is the *contrast* —
inline reads `subscribers = 0`, late reads non-zero, repeatedly and control-verified — not any
claim about why. **Fix the assert before re-running: a rig that asserts is not a rig.** Since then (§35.6a/b):
the inline half of that claim is now VERIFIED rather than assumed — **inline 0 of 3 assert,
late 9 of 9** — and the obvious fix FAILED. Moving `0x0074` back inline (it had been deferred,
putting `0x0072`/attributes/skill bar 20 s before the record they need) left the chain running
and the client still asserting, 2 of 2. **What remains is the last inline/late split:** the
hero's body, attributes, skill bar and HeroActivate are still sent inline while only the
roster binding is late, so they are now too EARLY relative to `0x01C2` — and a
`SkillListContext` assert naming a skill-list *user* fits a bar addressed to an agent the
party does not yet hold. The correct rig defers the **whole hero pipeline as one unit** — **BUILT AND TRIED (§35.6c),
and it STILL asserts.** `hsend()` now routes the entire pipeline through one deferral point,
relative order identical to inline, only absolute time changed; the chain ran and the client
asserted anyway. **Three orderings, three asserts — so the cause is LATENESS ITSELF, not
ordering.** The client will not accept a party roster and hero delivered after
`INSTANCE_LOAD_FINISH`. So **"send it later" is not a viable authoring route**, the timing
experiment cannot be run cleanly this way, §35.1/§35.5 stay CONTESTED with no cheap way to lift
it, and §33.5 stands better understood: the commander panel is not reachable from the server.
Regression control held throughout — the same code inline is clean, send order unchanged.
**The remaining route is a different instrument:** trap the map INSERT rather than the lookup,
and find which UI construction registers `0x1000011E`. **DONE — FINDINGS §36.3, and it lifts
the CONTESTED status.** A properly serialised census of the subscribe path (277 distinct
(event, caller) pairs) shows **`0x1000011E` registered TWICE on the ordinary INLINE rig** — the
one that does not assert. So the commander event does acquire a subscriber in a normal session;
§34's `subscribers = 0` was measured only because the raise happens *during* the instance load,
before that registration. The timing story therefore no longer depends on the asserting late
rig at all: §35's *contrast* was right and its late-rig mechanism was never needed. **Next, and
it is static:** the caller resolves (after un-sliding: `0x00843C07 - 0x210000 = 0x00633C07`) to
a thin subscribe wrapper at `0x00633BF0` through which every registration funnels — so
enumerate ITS callers and find which passes `0x1000011E`. That names the UI construction. Also
recorded UNRESOLVED (§35.7): the two trap site-sets disagreed 4-of-4 versus 0-of-3 on the same
rig, which could be variance, an observer effect, or the sites themselves — so §35.5's numbers
are not safe to build on yet.

**The intermediate labelling, kept because the correction is mine:** that hypothesis was first
TESTED at n=2 as CORROBORATED but NOT REPRODUCIBLE, retracting a mid-session "CONFIRMED"
(FINDINGS §35).** `--hero-late N` holds the whole roster
sequence until N seconds after `INSTANCE_LOAD_FINISH`. One run showed exactly what the
hypothesis predicted — subscriber `0x26151EA0` instead of `0`, and case 93 **running** — but a
second run on the identical rig stopped at the worker, and a third held the container at
`count=0` for 14 samples. **No commander is created in any run, early or late.** The confound
is named: `--hero-late` moves *two* things, the send time **and** the party-cache state that
gates the raise, so run 2's stall is probably `raise=0` from a re-cached party 1 — the same
confound shape as §10.2's body arm and §26.3's arm A. Settle it by trapping
`worker,raise,lookup,case93` on the late rig over several runs.

**The original framing, kept because the hypothesis is still live:** The census shows
**eight events whose subscriber state changes mid-session**, so the map is filled as UI
modules come up. Hence **TIMING**: our `0x01C2` rides inside the instance load and may simply
arrive before the commander UI subscribes — in which case the same bytes would work sent
later. Refuted by censusing `0x1000011E` across a whole session and finding it never
subscribed at any moment. Testing it needs the registration site trapped, or a hero-add sent
long after `INSTANCE_LOAD_FINISH`, which no flag does today. Also unresolved and named rather
than smoothed over: `0x10000114` HAS a live subscriber yet case 90 never executed (§34.3).

**The one thing to do first, and everything hangs on it:** send a single `0x01BF`
PARTY_HENCHMAN_ADD inside the party build window our server already opens, with `0x00B0`
raised to 2 and a real `EncString` name, **and no world body at all**. That deliberately
isolates the roster question from the agent question. The smsgsweep scored this opcode
SILENT on 2026-08-12, but it did so with an all-zero payload whose `party_id = 0` took the
"current party" branch and found NULL — **and our server has since learned to build a
party** (`party_build()`, RESKIN §17). That is exactly the condition that changed, so the
QUIET reading is RECONSTRUCTION until a run answers it.

Acceptance is **R4c-H**: two roster rows against a control arm's one, the second bearing the
archive-resolved name. Two controls the verifier added and both are adopted — `shotlabel`
proves *change against a noise floor* and the **operator** reads the row (the tool "does not
name anything"), and a **name-swap arm** (two treatment runs differing only in the name id)
is what a pixel-diff cannot fake. No echo is possible: with 0 of 22,524 live messages
carrying `0x01BF`, there is no retail stream to replay.

Buildable now, no client needed: `agents.party_henchman_add()` / `party_hero_add()` /
`mercenary_info()` builders in `party_build()`'s assert-mirroring `ValueError` style (party
id 1..20 non-zero, hero index **1..39**, the 20/32 code-unit name caps), flag-gated wiring
in the `PLAYER_FLAGS` pattern, and **`heroes_table.py`** — owner-ruled permitted under the
MEASUREMENT branch, anchored on accessor `0x005A9380` / base `0x00A35E08` (**not** the
adjacent title table at `0xA35B80`, which is the trap that cost this arc a contested
reading), emitting ids per row and never a committed column of resolved English.

Also unrun and cheap: the family was **never retried under `--encstring`**, only all-zero —
and a real encoded string is what flipped six other opcodes from ASSERTED to a named visible
effect.

**Three things deliberately NOT done, so nobody re-derives them.** Hero **skill-bar
delivery is NOT FOUND** on any wire shape scanned — `ChCliHero`'s two hero-indexed
structures were traced to no message, and that is the gap. The **c2s** direction is NOT
FOUND three times over (stance change, flag placement, hiring), and both readings —
client-local UI vs an opcode we missed — fit the evidence. And **follow AI does not exist**
on our server; the movement messages do, so it is unbuilt work rather than an unknown.

**One defect to fix in passing — FIXED `c81d6d1`, CHECKED 2026-08-19:** `msgshape.py` printed
`string16(0)` for *every* wide-string field — `Field.__repr__` reads `self.cap` but the
`wstring` branch never passed `cap=`, so the real capacity was only recoverable by
back-solving from the wire total. It now prints the declared capacity, pinned by
`test_msgshape.py` §4 over all 141 wide-string fields on all three vaulted builds (floor
44 → 73). **The fix landed on 2026-08-15 and this paragraph still called it open on
2026-08-19**, because nothing checked it — the same failure the top of `CLAUDE.md` is about,
in miniature: a rule nothing checks is a wish, and so is a fix nothing pins.

### Combat — steps 0-9 landed and the caged runs happened; NOTHING is left (2026-08-15)

The arc is [studies/combat/PLAN.md](studies/combat/PLAN.md); its §3 progress
ledger is the detail and this is the summary. Nine steps landed. What it
changed is in R4a and R4b above. **Everything this section listed as open has
now run at a client**, on 2026-08-15:

~~0. verify the `0x003A` fix.~~ ~~1. `--probe attributes`.~~ **BOTH DONE
2026-08-15 in one caged run** — `studies/combat/PLAN.md` §14g. The message had
been going out INTERLEAVED against a wire that is COLUMN-MAJOR and asserted the
client dead on `CharData.cpp:202` in every session that sent it, including two
instrumented runs reported healthy because the assert box is modal *inside* the
client. Fixed, and the run confirms it: 1,716 messages, t=78.2 s, no assert,
watched with `crashwatch.ps1` rather than `Get-Process`. The same run drove
`--probe attributes` through all three steps and **the panel followed with the
ranks against the right names**, so L6's attributability criterion is MET —
which also closes §8b's runtime agent-binding assumption by observation, and
confirms §8a's reading of column 2 as `baseValue` positionally (step 3 reverses
the rank column while holding the id column's order).

~~The cast-lifecycle loopback acceptance.~~ **DONE 2026-08-15, two caged runs
— `studies/combat/PLAN.md` §15, and this section's combat list is now EMPTY.**
`0x00E4→0x00E5→0x00E3→0x00E6` had been offline-tested against six live cycles
and never played at a client. It has now been: four complete cycles, the client
accepts every opcode without asserting, a repeat press after `E6` produces a
full second cycle, and recharge is **per-skill with concurrent timers** — slot
6's 8 s overlaps slot 7's 3 s cycles and each `E6` names its own skill. Max
error against the declared recharge is 36 ms. The rendered half is
operator-confirmed: **both slots swept and slot 6 was clearly longer than slot
7**, which is the comparison that shows the client honours the DURATION the
message carries rather than just flashing an icon on receipt.

**The one thing it did NOT settle**: the cast ANIMATION. The operator was
watching the bar, so nothing was reported about the character's body, and
silence is not a negative result. It is also a different question — the unrun
`cast_anim` probe predicts opcode `228` "does nothing visible at all when
addressed to the local player", and `228` is what this run sends; agent
property 60 is the candidate that would animate. `--probe cast_anim` is
UNRUN and is the natural next caged run if anyone wants it.

Both were blocked on the harness refusing to launch, and **that blocker is
gone**: it was `session.py` selecting the newest run directory, which became
the fresh 38833 snapshot whose archive never had the 146/148 replacement
installed. `391e8ca` made the harness pick by BUILD and NAME — and the run
above is the proof, since it is the first caged session to reach a map, drive
a probe and be judged healthy by a watcher that can actually see a crash.

Three things this arc deliberately did NOT do, so nobody re-derives them:
**conditions, hexes and enchantments are unmodelled** (F5 — nothing in the
vault can ground a bleed tick); **energy and adrenaline are not enforced**
(F2 — and the wire says the client tracks them itself); and **damage lands at
press rather than at cast end** — magnitudes moved in step 8, timing did not.

### The minimap — Tier 1 complete, and THE COMPASS DRAWS THE ATLAS: C1 ran and the fallback premise expired (2026-08-14)

**READ THIS FIRST, because it retires the headline this section carried all day.** *It read "the compass on our server is drawing the client's FALLBACK", and every paragraph below was written under that premise.* **Rung C1 — the arc's first client run — put the compass on screen drawing a recognisable crop of Ascalon City on retail map 148**, our server, our DH, caged, loopback, synthetic credential. The metric is §6's own chromatic ratio with the control measured first: the previously-classified fallback frames re-read at **χ +1.154 … +1.160** by the same sampler, and this run's five frames at **+0.250 … +0.279** — against rung S5's *offline* prediction of **+0.286** for map 148's crop, computed before any frame existed and never fitted to one. **`studies/minimap/FINDINGS.md` §6d** carries it.

**The condition it took, and this is the transferable part:** build **38833 against its own archive generation** (`vault/run/2026-08-13_64fae3b1369b`, `RURIK_DAT` at a post-update archive). The 38797 arm **failed at Code=007** — `content/maps.toml`'s corrected plain `0x1B97D` does not bind in the 38797/`dat_study` archives at all, only `0x8001B97D` does, and the client's lookup is an exact 32-bit compare with no retry; the server sent `0x0199`, loaded its navmesh, and the client hung up. **`toolkit/contentids.py` cleared that pair anyway** and that is a real hole: it resolves through `archive.file_id_table()`, which dual-registers a bit-31 id under both forms, so it compared row 7982 to row 7982 and never tested the form actually sent. It validates our reader's opinion, not the client's. **UNFIXED — it is §8's newest item.** *(Since fixed, and on 2026-08-16 the 38797 archive state itself was repaired — that §8 item has the record.)*

**ATTRIBUTION IS NOW CLOSED TOO — rung S13, same day (`studies/minimap/FINDINGS.md` §6e). The cause is the ARCHIVE'S ARMED STATE, and specifically the ATLAS TILE ROWS.**

> **Corrected within the hour, and the correction is load-bearing.** S13 first reported this as a *generation* difference (38797-era broken, 38833 fixed) and claimed its refutation clause did not fire. **It fired.** Three build-**38797** sessions drew a full atlas crop, and the decisive pair is `20260813T103437` (atlas) against `20260813T105432` (fallback) — **twenty minutes apart from the same run directory, same exe, same archive path.** The archive was armed under the client between those two runs. So the variable is the **armed state of the client's own `Gw.dat`, which changes over that copy's life**, not the vintage of anything; and that pair exonerates the client build by natural experiment, more cleanly than the static code diff below. The mechanism is unchanged and better supported. *(Sweep limit: of 620 frame-carrying sessions only the 320 with a hold frame are scored — 188 others read χ ≈ +0.529 off `final.png`, which is the character screen, not a compass.)* In every archive the fallback sessions played from, map 148's world-map tiles carry **bit 31** — replacement pending — so the **plain** id the client's own tile table holds does not bind, its exact 32-bit compare misses, the tile getter returns NULL and the fallback is tiled over the whole disc. Across the atlas: **470 of 492 tiles addressable in `run/38797` — 22 missing, 18 of them in world 1 — against 492 of 492 in `run/38833`.** Maps 143, 146 and 148 are **all world 1**, and they are the entire fallback corpus; Kamadan (world 4) was never served. **The arc's premise was a survey of one broken continent.**

The other three candidates were each tested and died: the **map file** (height field byte-identical, `MAP_PARAMS`'s rect bytes identical, differing only in a trailing v4 GUID), the **client build** (all 12 `CompassMap.cpp` asserts identical and uniformly displaced +0xA0; ctor, crop, latch and fallback tiler have identical instruction counts and **zero** mnemonic mismatches; the footprint table, `s_worldData` and the tile arrays byte-identical), and the **map-type byte** (map 148's two footprints are the same rect, and a forced `--explorable` run still drew the atlas). **S9's hypothesis 2 was right in substance and refuted for the wrong reason** — the load does fail, but upstream of the loader, in a lookup that never yields a row.

**This is the same defect a third time, and that is the durable lesson.** `archive.file_id_table()` dual-registers a bit-31 id, so it answered "row 44717, present" for a tile the client cannot address. It has now hidden: the map **file** id (caught by crossbuild), the **`contentids`** pre-flight (below; since fixed), and rung **S9's tile-presence check** — which cost S9, S12, C1 and S13 to unwind. **One predicate fixes all three: does the id bind in the form it is sent?**

**Second result, small and operational:** the ground layer **arrives late** — `final.png` at the map verdict reads χ +1.182 (fallback band) and converges to +0.250 by ~t+26 s. A single early frame is not evidence of a NULL image. **Consequences: C2 and C3 are UNGATED** (they were held behind a vacuous-arm problem that no longer exists), **risk 7 is RETIRED**, and Tier 3's premise survives. Two caveats the run carries: the server ran **without a navmesh** (`Permission denied` — the client holds its own archive open, so give the server a separate copy), and `--shots` is foreground-gated, skipping 4 of 9.

**Everything below this line was written under the fallback premise. The static analysis stands; the framing does not.**

### `file_id_table()`'s dual registration has now hidden three failures — all three CLOSED, and the archive state behind them repaired (2026-08-14 → 2026-08-16)

**Read this as one defect with three victims, not three bugs.** `archive.file_id_table()` registers a bit-31 id under **both** its raw and its masked form — correct for finding a row, and documented in that same file as **not a model of the client**, which compares 32 bits exactly at `0x0047AA20` with no retry. Every caller that asks it "does this id resolve?" gets an answer about *our reader*.

1. **The map file id** — `content/maps.toml` recorded `0x8001B97D`. Caught 2026-08-14 by the crossbuild arc; the row now reads `0x1B97D`.
2. **Rung S9's atlas-tile presence check** — concluded "all four of map 148's tiles present in the archive the client opened", and through it the minimap arc's entire leading question. **The tiles were present as rows and unaddressable by the client**: 22 of 492 armed, 18 in world 1. It cost rungs S9, S12, C1 and S13 to unwind. Closed by S13.
3. **`toolkit/contentids.py`** — **FIXED**: `check()` resolves the client's half on the
   RAW table and the server's half on the masked one, which is not a compromise but the
   measured model of each side (the gamesrv really did serve a navmesh through the alias
   on 2026-08-14). `test_contentids.py` §1b/§2 are the regression guards, red on the old
   code. The account below is kept as the record of the defect.

**The single fix:** a `binds_plainly(archive, file_id)` / `file_id_table(raw=True)` predicate, and every caller that is asking *what the client will do* uses it. Each of the three above becomes a one-line check.

#### `contentids.py` clears a pair the client will refuse — found by walking into it

**The guard exists to catch exactly one failure and is blind to it.** `toolkit/contentids.py` answers "do server and client agree what `content/maps.toml`'s ids NAME" by resolving both through `archive.file_id_table()` — which **deliberately registers a bit-31 id under both its raw and its masked form**, "plain ids first so that a real id can never be shadowed". That dual registration is right for finding a row and `archive.py`'s own docstring says it is **not a model of the client**: *"THE CLIENT DOES NOT MASK"*, an exact 32-bit compare at `0x0047AA20` with no retry on the map path.

**Measured 2026-08-14**, reading MFT row 2 directly instead of through the helper:

| archive | `0x1B97D` raw | `0x8001B97D` raw | bit-31 ids |
|---|---|---|---|
| `run/2026-07-29_221c13772c7a` (38797) | **absent** | row 7982 | 29 |
| `dat_study` | **absent** | row 7982 | 25 |
| `run/2026-08-13_64fae3b1369b` (38833) | **row 177262** | absent | **0** |

`contentids` reported `10 of 10 map row(s) agree` for the 38797 pair, comparing row 7982 to row 7982. The run then died at **Code=007** with the client hanging up immediately after `0x0199`. **The guard passed, the launch proceeded, and the failure was silent on our side and unexplained on the client's** — which is the precise shape the guard was written to prevent.

**Fix:** do not change `file_id_table()` — its convenience is load-bearing elsewhere. Have `contentids` resolve on the **raw** table and fail when the id `content/maps.toml` will actually put on the wire is absent from the client's archive *in the form it is sent*. The refusal must name both forms and both rows. `test_contentids.py` needs an arm that goes red on today's code: a fixture pair binding only the renamed form, asked for the plain one.

**RESOLVED, in two layers.** The guard fix above landed (raw table for the client's half,
masked for the server's, regression-guarded), and **on 2026-08-16 the archive state it
was refusing was itself repaired**: `datwrite.py --relink-plain 0x1B97D` re-bound the
plain id to row 7982 in the canonical `vault/run/2026-07-29_221c13772c7a/Gw.dat` — the
DnArchive re-link minus the download that was never coming, one dword of the file-id
table plus the two checksums, journalled, with a sha-verified full backup beside the
archive (`Gw.dat.pre-relink-20260816`) and censuses under
`vault/research/relink-1b97d-2026-08-16/`. `contentids` preflight now reads **10 of 10
agree, 0 FATAL** — maps 146/148 included — against the archive `select_run_exe`
launches, and `datcheck --preflight` holds 10 of 10 open-time rules. The 38797 lane can
serve Pre-Searing again; the `-c2`/`-probe`/`reskin-roster` copies are deliberately left
mid-replacement (test_contentids's positive controls need one, and the verb repairs any
of them in one command). **One premise from the 2026-08-15/16 accounts is REFUTED by
measurement**: the 38833 copy's `0x1B97D` file is **not** a terrain-arc rewrite — row
177262's stored bytes are sha-identical across the pristine `client/2026-08-13`
snapshot, the 38833 run dir and the 38833 `run-live` copy, so it is ArenaNet's own
38833-generation Pre-Searing map, which simply differs from the 38797 bytes `dat_study`
paths against. A 38833-exe run therefore still needs `--map 449` or a same-generation
`RURIK_DAT`. `contentids.default_client_dat()` was also re-aligned to mirror
`select_run_exe` (pinned build, measured from the exe, canonical stamp dir) instead of
the newest-mtime rule the harness abandoned.

### The minimap — the record under the fallback premise (superseded above)

**Read [`studies/minimap/FINDINGS.md`](studies/minimap/FINDINGS.md), then its
[`PLAN.md`](studies/minimap/PLAN.md) ladder.** Static recon over build 38797 plus the
full live corpus; **no client was launched for any of the STATIC rungs S1–S12** (that
clause read "by any of the eleven agents on this arc" and stopped being true when C1 ran
on 2026-08-14 — see the headline above).
The pathing-map hypothesis is REFUTED: the compass, mission map and world map are three
crops of ONE per-continent atlas of ATEX tiles compiled into the client — **492 tiles
over three tiers, 484 resolving identically in all three vaulted archives** — cropped by
the area row's footprint rect at **exactly one texel per terrain cell** (OBSERVED from
the client's own `add`/`shr 9` and from a five-scale population test with four rivals at
zero). **No map file supplies a pixel of it** — though it does bound how much of it is
ever asked for, which this paragraph denied until S9 corrected it (below).

**The one result that reorders everything, and it was not predicted.** Rung S5 rendered
the crops offline and went to compare them against the compass frames we already have —
and **every compass frame in the vault is the client's NULL-image fallback tile (archive
file 9153, 64×64, tiled), not any crop of the atlas.** Six frames, three maps, four
sessions, chromatic ratio +1.081..+1.110 against the fallback's +1.164 and the crops'
−1.718..+0.286, with 0 of 7,948 atlas windows in band, no translation improving the fit
across a walk and no rotation improving it while the bezel visibly turns. **It fires on
retail map 148 too, with all four of that map's tiles present in the archive the client
opened** — so it is not our authored maps' fault, and the customarea "featureless brown
disc" is now positively identified rather than explained.

**S9 then killed BOTH hypotheses this paragraph used to name, and the `Gw.log` line it
called a free discriminator.** *It read: "Why it fires is NOT FOUND, with two separable
hypotheses (a world index latched before the instance load, or a failed texture load)
and a `Gw.log` line that tells them apart for free."* Two agents each owned one
hypothesis and were told to refute their own; both died. The **stale index** cannot
happen — the sentinel in `missionContext+0x230` is **888**, not 0 (`0x00855E3E`, teardown
`0x00856119`), so row 0 is unreachable, and the sentinel path does not fall back at all:
it hands a garbage world to the `s_worldData` accessor and dereferences ~`0x53A00000`, an
access violation nowhere in our record. The **failed load** cannot be it either — the
fallback tile the compass is drawing was loaded by that same loader, from the same
archive, in the same process, on the same frame. And **the log line can never fire**: it
sits on the *conversion* arm (`0x008C21EB cmp dword [ebp-4], 0xf; jne`), which is skipped
because all 484 resolvable tiles are already DXT1 — absence of the line is exactly what a
perfect load produces. **Do not budget it as evidence.**

**What replaced them (H3, mechanism OBSERVED, cause UNVERIFIED):** `0x008C28D0` is a
latch-once init that copies the **loaded map file's** world rect out of `Engine\Map`,
divides by the 96.0 cell pitch and stores `(0, 0, mapCellsX, mapCellsY)`; the crop clamps
every request to that rect **before** adding the footprint origin, and an empty
intersection goes straight to the fallback tiler. Hence the correction above — the art is
archive-only, the *addressing* is not.

Four things landed underneath that:

- **The lever is confirmed and its population shrank by 8×.** The `0x0199` map-type byte
  selects FOOTPRINT_A vs B, and the enum is now named from the binary — 0 =
  `MISSION_MAP_OUTPOST`, 1 = `MISSION_MAP_GAME`. **Six** readers apply it image-wide, not
  the one the rung predicted, closable because the table base occurs exactly once in the
  image. And of the 172 rows where A ≠ B, **136 have A all-zero and 16 have B all-zero —
  only 20 carry two real rects**, which is C3's actual population.
- **The continent → world map is the IDENTITY**, closing this study's leading NOT FOUND
  and promoting `areatable.OFF_CONTINENT` from UPSTREAM to CORROBORATED. But the
  prediction's supporting argument is REFUTED: the seven area-table values are not the
  seven tile-bearing worlds, world 6's art is orphaned, and five map ids point at a world
  with no tiles at all.
- **The fog contest is CLOSED** — two agents from opposite ends with the rival answers
  withheld, agreeing on every VA and all five live counts: `0x008B` declare + `0x008A`
  payload + `0x008C` incremental mark; `0x0089` is an AgentView mannequin message and not
  in the subsystem. The wrong reading was manufactured by `asserts.py --at`'s fixed
  2,000-byte window over four functions occupying 998 bytes — the same class of trap that
  made `codescan --in CompassMap` hide the very branch rung S2 was run to find. **Both
  locators answer confidently and wrongly outside their range and neither can warn.**
- **A genuine unnamed drop, with its name now attacked as well as confirmed**: GAME_CMSG
  `0x002B` is the compass draw (sole producer re-established by a value-first sweep of all
  134 materialisations of `0x2b`, exactly one inside any of the **214** send-call bodies —
  the earlier 174 missed a second send entry), our client has already sent it 5× on
  loopback, and `authsrv.py` discards it with no arm, no allowlist row, no name. **The
  `knotCount > 16` process-kill hazard is RETRACTED** — the generic unpacker refuses the
  message before dispatch, so an over-range send is inert, not dangerous.

**Next, in order (S1-S12 are all LANDED as of 2026-08-14; `worldmap.py` and its test are
committed, floor 78, 19 sabotages all reddening; the suite is 83/83 green, 4,035
checks):**

1. ~~**S12**~~ **DONE 2026-08-14, and it over-delivered — `studies/minimap/FINDINGS.md`
   §6c.** **H3a is DEAD three ways**: the rect writer is chunk `0x2000000C` —
   `mapbuild.py`'s own `MAP_PARAMS_CHUNK`, met from the client side (`0x007129D0` →
   `0x0070D780`, one caller image-wide) — running inside the synchronous chunk loop
   before the object is ever installed into the per-thread slot (`0x00707CC4`, one of
   exactly two writers); the compass's copy (`0x0070A5C0`) has **no NULL path**, so a
   too-early paint crashes rather than latching zeros; and the build runs inside the
   synchronous dispatch of frame msg `0x10000098`, posted only by the MsCliApi
   instance-load path, with the HUD a later message. **The file-side half also killed
   H3 for retail 148 — after first getting it wrong and catching it.** The rung
   exported `0x0287d3` (the id in the `Gw.log` re-bloat line), read 64×64 / ±3072, and
   proposed that our spawn falls outside the map's rect and causes the fallback;
   **`0x0287d3` is the authored SCULPT map**, which is why re-bloat names it, and map
   148's id was in `content/maps.toml` all along (`0x1B97D`). Corrected: map 148 is
   **416×512 cells — exactly the footprint** — with our spawn at cell (294, 340), well
   inside, so **the latch covers the whole footprint and H3 is dead here too.** All
   three named hypotheses are now refuted on retail 148 and the fault is **downstream
   of the crop**. H3b stands for authored maps, now quantified.
2. ~~**C1 — one loopback run, NEEDS OWNER GO-AHEAD**~~ **— DONE 2026-08-14, and the
   compass drew the atlas (see this section's new headline and
   `studies/minimap/FINDINGS.md` §6d). The RPM read below was NOT performed and is
   demoted to an optional confirmation**, because the fallback stopped reproducing and
   there was no NULL image left to diagnose. Its predictions are still the right ones
   to check if anybody spends the run: `+0x84 == 1`, `+0x58/+0x5c == (416, 512)`.
   **The live next action is S13 — which of client build, archive generation or id
   form un-NULLed it — whose first leg is static and needs no go-ahead.** Original
   text follows.
   Retail map 148, our DH, caged, no probe, no `--enemy`. A
   cross-process `ReadProcessMemory` of the live `CompassMap` (instance at
   `[compass+0x4C]`, lazy create `0x008BC426`; `toolkit/harness/keytap.py` already does
   ASLR-correct RPM in pure `ctypes`) reads: predicted `+0x84 == 1`,
   **`+0x58/+0x5c == (416, 512)`**, `+0x60..0x6c == (−18432, −24576, 21504, 24576)`.
   That outcome **confirms the upstream half healthy by measurement** and leaves the
   whole question downstream — the per-slot load at `0x008C21C0`, the blit at
   `0x008C2077`, or rung S5's metric. **The spawn arm an earlier draft proposed is
   VOID** (the spawn is inside the rect). χ alone still discriminates nothing; C1 still
   **gates C2 and C3**.
**Owner flag for Tier 3 is unchanged**: an authored map's compass showing OUR terrain
needs both an archive tile write (A1) and a client patch repointing the footprint (A2) —
it is not a free consequence of good authoring, and it is worth nothing until C1 explains
the fallback.

### Custom professions — the route is RESKIN, and the party window just opened

**Read [`studies/profession/RESKIN.md`](studies/profession/RESKIN.md) first, then
[`RUNS.md`](studies/profession/RUNS.md) §10.** RESKIN.md is the live document; RUNS.md
§§1–9 are kept only as the record of seven sessions spent on a crash that turned out to
be our own unlock bit 0.

**SETTLED.** Adding a 12th profession is refused on cost (zero slack in `.rdata`, and
seven of the per-profession tables are `mov imm32` ladders — code, not data). **Repurposing
a shipped id is the route**, host = **Ritualist (8)**, and it is validated in a running
client: name, abbreviation, attribute ownership, attribute names and the primary marker
are all same-length dword edits via `toolkit/clientpatch/reskin.py`, which locates every
table structurally and writes out-of-place. A custom id can never be a SECONDARY (the
builder loops `cmp edi, 0xb`) and `0x00B7` can never carry one (`ConstChar.cpp:1296`, on
arrival, measured twice).

**AUTHORED TEXT WORKS — the whole identity tier is ours** (§19). Text file index 98 is
1,024 EMPTY records (ids 100352..101375); we wrote seven of them and the client resolved
every one: **`Profession: Stormcaller`** over attributes **Tempest, Galecraft, Windward,
Thunderhead, Storm Calling**. Nothing on that screen is ArenaNet's text. This retires the
arc's standing limit that a custom profession could only be *named* things the client
already shipped strings for.

The unproven step was step 1 — no text file had ever shipped **stored**, so the client had
never been handed one. It reads them. Each step kept a check: `encode_file` with no strings
is **byte-identical to ArenaNet's own row 8295** (6,146 B) *before* anything is written;
`datmove` relocated 56 B compressed → 6,172 B stored with **0 overlapping pairs** and
`datcheck --preflight` **10 of 10**; a second `datwrite --replace` fitted 6,268 B into the
same reservation, still 10 of 10. Both journals revert byte-for-byte.
`recipes/stormcaller.toml` is the design; **`reskin.py` refuses to re-patch its own output**
(the locator requires anchor and shape to agree), so always patch from a clean client.

**THE PARTY ROSTER DRAWS A MEMBER ROW, WITH ITS ABBREVIATION** (§§17–18). The gate was
`PyCliGetMyPartyId` (`0x00856250`), zero on our server; retail's four-message build
(`0x01D2` / `0x01CB` / `0x01D3` / `0x01B2`, 20 bytes, 8 of 8 live connections) is in the
burst now. **But the gate is a PAIR, and each half had been tested alone** — the party
record AND an explorable instance. §16.1's explorable run predated the build; §17.3's
build ran in an outpost and got Party *Search* (dialog `0x1E`, 281,814 px). Together:
`Party Members [P]` carrying the row `W0 Test Warrior`.

`is_explorable` turns out to be the mission **MAP TYPE** — that dword is `context->map`,
`MISSION_MAP_GAME` is ArenaNet's own name for `1` (asserted 9× in MsCliApi), and PtFrame's
child builder does `cmp eax,1 / jne`, loading PtRoster's proc on equal and **PtFormation**
on not-equal. In an outpost the roster is never the frame that *exists*. The member row is
**`PtPlayer`** (proc `0x00574F30`, asserts PtPlayer.cpp:442/445), **not** `PtPartyEntry`,
which is the row for a whole *party* — §§16.1/17.4 had that wrong.

**The row's red bar is HEALTH, and this server drives both terms** (§§18.10–18.13). Red is
not a state — WIKI (GWW, "User interface", rev. 2026-07-15): red bars are members' health,
a *disconnected* player greys out. Measured: `0x00A3 [16, …]` (a fraction of maximum) took
the bar to **49.7%** then **24.0%** against a prediction of 50/25; `0x009F [42, …]` is
maximum health and **`health += (new_max − old_max)`** — 25/100 with max set to 200 read
**125**, not 200, refuting ldufr/Headquarter's "refills" (UPSTREAM) and this arc's own
fraction guess. `agents.py`'s `PROP_HEALTH_MAX` comment is corrected.

**`0x003C` is a measured NULL** (§§18.8–18.9): 423 sends over 12 of 12 live connections and
never sent by us, so it looked load-bearing. Swept 0/4/7 both late and at retail's own
load-time slot (before `0x0020`, behind `--player-flags`): party region **0.000%** against
control on every matched frame, client traffic identical. Off by default. Untested with
more than one player.

**The archive decision this list carried is CLOSED, and by accident** (§19.4). It asked the
owner to choose which 4.2 GB archive the text route should write into. The dedicated run
directory built for §18.14 — `vault/run/reskin-roster/` — is a throwaway copy only its own
caged client reads, so the write risked nothing shared and needed no decision. Cost: 4 GB
of disk and one UAC prompt, because **the firewall cage is per BINARY** and a new client
under `vault/run/` has no rule until `isolate_client.ps1` runs elevated.

**SKILL ICONS ARE OPEN TOO, and the roster needs no archive relocations** (§13,
[`studies/texture/FINDINGS.md`](studies/texture/FINDINGS.md) §9). The wall this list would
have quoted — "3,292 of 3,439 are DXTL" — was `datwrite/FINDINGS.md` blocker #3, retired
on 2026-08-06: DXTL is `+0x8c` at 64×64 and the bar reads `+0x90` at DXT1 128×128.
Harness `20260814T002445` settled the last open term by measuring that the client
**stretches the whole texture onto a fixed screen quad** — a 64×64 and a 128×128 of the
same picture render at the same framing (15.19/255 apart, against 68.9–134.6 for the
retail icons beside them), and a ruler's two landmarks give 0.958 and 0.955 px per texel,
predicting one from the other to 0.1 px. So a 64×64 icon is 2,068 B against a 2,560 B
reservation and fits **132 of profession 8's 132 distinct icon rows in place**, where a
128×128 fits 16. What is missing is art, not mechanism: nothing yet draws 132 pictures.
**Procedural rule earned the same day** ([`studies/crossbuild/FINDINGS.md`](studies/crossbuild/FINDINGS.md)
§4c): the client moved the MFT 4.03 MB mid-session, so a journal expires the moment a
client runs — **revert before you launch, not after**. `vault/run/reskin-roster/Gw.dat`
is still armed on rows 174150/174487/174861 for that reason.

**THE PROFESSION GLYPH IS FOUND (2026-08-14, RESKIN §22)** — the last NOT FOUND in the
arc, after three failed bounded searches. It is ONE SHARED SHEET, not eleven files:
`.rdata` VA `0x00959964` holds the pair `{0x573D, 0x0102}`, decoding to file id 152638 =
MFT row 12032, a 256×128 32bpp DDS of 8×4 cells at 32×32, of which exactly 22 are
distinct. The 12-entry jump table at VA `0x005A5EB8` maps profession to an even frame and
a state bit adds lit/dim; **profession 8 is frames 14/15**. Owner is
`VnProfessionButton.cpp`, by ArenaNet's own `__FILE__`.
**Why three searches missed it, and it is reusable: the client never stores a raw u32 file
id, only `{u16 id0, u16 id1}` pairs**, so every sweep for runs of resolving dwords was
structurally blind rather than unlucky. Authoring costs a partial overwrite of one 32×32
region plus a `datmove` — the row ships compressed at 35,460 B and we would write stored
at 131,200 B, which does not fit its 35,840 B reservation.

**THE SKILL TIER IS NAMED (2026-08-14, RESKIN §24, `ccdf82a`).** **188 authored skill
names**, generated rather than typed, on screen in the retail client: the noun comes from
the MOTIF of the icon the skill draws (`glyphs.py`, `i % 22`) and the adjective from the
ATTRIBUTE the Skills panel groups by, so a name agrees with its picture by construction.
Eight of eight bar icons matched their names on screen — a violet starburst called
*Sheltering Starburst*, reading `(Attrib: Windward)` from the client's own tooltip.
`skillnames.py` generates, `textwrite.py` writes text file 98 (**7,134 B → 12,236 B**, a
journalled `datmove`), `reskin.py`'s `[[skill]] name/concise/desc` dword verb points the
rows at them, and `--emit-recipe` keeps both halves on ONE definition of the
record↔skill assignment (`textwrite.name_assignment`) — nothing joins them at run time, so
a disagreement would label every skill with another skill's name silently. Checked both
directions: 188/188 resolve to their own name, 0/188 under a one-id shift.

**A per-skill discriminator turned out to be MANDATORY, and that is measured.** Over
profession 8: motif alone gives 22 groups worst-case 12; the whole glyph index gives 125
worst-case 7; adding the attribute moves that only to 126 and 6, because skills sharing an
icon overwhelmingly share an attribute too. **50 names would have collided.**

**NEXT, and it is a design question rather than a mechanism one.** The identity tier is
done, the primary marker moved onto our own claimed row (§19.7, `cb53a9b`), the icon path
is open and the names are authored. What is left is what makes the class *play*
differently. In rough order of value: skill DESCRIPTIONS are still ArenaNet's — RESKIN
§24's "the tooltip still lies", and the `concise`/`desc` verbs exist and are unexercised;
the skill roster is 1 byte per skill row and only two skills have been moved (§10's
countable check); and armour, model scale and palettes are all same-length dwords that
nothing has exercised yet. None of these is blocked — they need a design, not a discovery.

**The one thing that *is* server work is COMBAT, and its cost was re-measured 2026-08-14
(RESKIN §24.1) against what §20 assumed.** The client never computes damage, healing,
energy or cast time, and reads an attribute rank nowhere outside its own UI. Beyond that:
**property 33 and property 52 have ZERO observations on any wire, ever** — 0 probes, 0
server call sites, 0 of 22,524 live GAME_SMSG over twelve connections — and property 62,
the only energy-moving float ever seen, is NEGATIVE in all 6 occurrences. Nobody has
observed energy *gain* on a Guild Wars wire. The server also models **no attribute rank in
any form** (`2 * rank` evaluates to 0) and no live energy, and sends `0x003A` as 42 zeros,
so a passive shipped today would compute with rank R against a panel showing 0 and be
unattributable. **So the passive is a PROBE first, not a feature.** Two hazards to respect:
`hit_enemy`'s USE_SKILL caller is on the **connection thread**, whose only handler catches
`ConnectionError`/`socket.timeout`/`OSError`, so a `_fraction` refusal there disconnects
the client on exactly the path a demonstration uses; and at 25 max energy and +2 a kill an
uncapped accumulator crosses fraction 1.0 on the **13th kill**. The cheapest real rung is
`s_skill +0x44`–`+0x68`, the rank-0/rank-15 scaling, still undecoded — it would replace
`ENEMY_SKILL_FRACTION = 0.25`, which `authsrv.py` itself labels an invention.

Probes are registered and encode-checked: `profession_custom`, `profession_ab`,
`profession_skillbar`, `profession_spawn`, `profession_sentinel`, `profession_max`
(`toolkit/authsrv/probes.py`). L0 is done —
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
**2026-08-13:** full-map export with props — the interchange (format_version 2) carries every
placement from both streams cross-checked at export, the rotation composition is MEASURED
(z, then x, then y — was `props.py`'s open item), and Blender places each prop as a measured
proxy; Kamadan and Pre-Searing exported whole to `vault/exports/` with `.blend` scenes beside
them. Placements only — model geometry stays undecoded; **scoped the same day as a six-rung
ladder in [studies/models/PLAN.md](studies/models/PLAN.md)** (a proposal until adopted): the
format is half-read in customarea §5, the radius identity is a ready-made oracle, and the
missing piece is committed code plus the client's own FVF dispatch.

### The terrain texturing arc — CLOSED 2026-08-18; the ground matches the mechanism, and every open item is answered

> **THE ARC IS CLOSED, 2026-08-18. Everything under this heading from 2026-08-15
> is HISTORY — read it for the reasoning, never for the status.** Five things
> below are superseded and two are outright refuted. Full record:
> [`studies/terrain/FINDINGS.md`](studies/terrain/FINDINGS.md) §7.11–§12.
>
> **The mechanism, all locked to client captures.** The coverage pick is a
> function of (corner types, SELECTOR) — 212/212; the mask is PHYSICAL, not
> permuted (the permuted reading scored 31.1%); the base layer is the corner
> that SORTS FIRST (102/102); `trnvariation` reproduces the client's stream on
> 511/511 consecutive live draws; and **§7.2's second UV rectangle is REFUTED**
> (0 of 512 cells — the `0xFFFF` path is an unused-slot no-op). So the
> "blocking format bug" below was subsumed, and the "base layer's OWN UV
> rectangle" it calls the likeliest cause of repetition DOES NOT EXIST.
>
> **§7.20 — the ground does NOT repeat** beyond a floor the ART sets. Measured
> prediction-first with an artifact-gated compositor
> (`studies/terrain/repeatprobe.py`, checked in): the export sits ON the
> ideal-random floor on every window of both maps while the pre-arc pinned
> control separates 3–9×. Two adversarial reviewers returned SURVIVES; one
> found a real mislabel (Kamadan's whole-GRID row is 68% out-of-bounds filler)
> and it is corrected in place.
>
> **§7.21 — the `arg4 = 0` scope caveat is DISCHARGED**, and `trnvariation`
> claim 1 is confirmed against the client for the first time. Row 34429 tile
> (4,3) captured whole — 1024/1024 cells, 590 with authored tag 3: the
> draw-CONSUMED model scores **1024/1024** against the skip model's 693/1024,
> and the 331 cells where they disagree are **exactly** the 331 predicted
> before the run. An authored cell draws its authored value 590/590, and
> §7.14's cover-word rule holds 735/735 on an authored block.
> **Aiming the instrument was the work**: `trnhook/trnblock.c` filters on the
> block's own reseed and stays armed until the target completes (33,639 hits
> across 32 blocks in one run), and `trnhook/autoinject.py` exists because
> terrain builds ONCE at map load — a poll-then-inject round trip returns
> `hits 0` with a perfectly correct breakpoint.
>
> **§9 — prop material fall-through is CLOSED, and the recorded 31.6% was
> OVERSTATED rather than stale.** The population never moved (13 sub-models
> then and now); 12 of the 13 bind to material slot 0 explicitly, which is the
> slot the default would have given — identical pixels. Only **one** sub-model
> (0.11% of Kamadan's prop area, 0 on Lornar's) is genuinely unbound, and it
> now draws a marker instead of impersonating a textured surface.
> **Two claims refuted**: the dark rocks are the ART (12 of 12 fall-back
> sub-models draw the only colour map their model owns), and "decode AMAT" was
> wrong in kind — **AMAT is a compiled SHADER binary** (`TECH`/`PASS` chunk
> tags), not a texture-index table.
>
> **§10–§12 — the FIELD OF VIEW is measured, and so is its axis.** Exactly
> **75.000° HORIZONTAL**, far plane **48000**, read live from the global at
> `0x00C078C4` (`toolkit/clientscan/fovread.py`). The axis was settled twice:
> the projection's adjacent scale pair puts `cot(75/2)` as the x scale, and an
> aspect test — the same client resized wide→portrait — kept `m00` pinned
> while `m11` tracked the aspect (vertical 43.6° at 16:9, 95.3° at 0.699).
> `gwcam.py`'s 28 mm placeholder is gone. **Left unexplained, deliberately**:
> this contradicts ArenaNet's 2018-06-06 patch note describing a *vertical*
> calculation. The measurement stands; the reconciliation is not guessed.
>
> **§13 — the lightmap's TRANSFER CURVE is SETTLED (2026-08-19), and it is a
> QUARTIC.** The bake is `255·(1 − (1 − N·L)⁴)`, a fast ease-out — not the
> linear `shade/255` the earlier text assumed and not a gamma — read byte-exact
> from the generator `0x0075CC30` and reproduced on 667,647/667,648 corpus
> cells (and 1024/1024 on four client compiles) by
> `studies/terrain/trnbake.py`, which reads the client's invsqrt table at run
> time and commits none of it. The quartic's fast saturation is why 348/349
> maps peg at 255 and why §6.5's linear fit could only reach r 0.887. No
> cast-shadow term; the bake is a pure function of (heights, sun angle).
> **Two follow-ons replace it, neither blocking a render**: how the client
> *displays* the baked lightmap (§13.3 — both terrain vertex shaders write a
> DEPTH-FADE to the shader's `v0`, not tag 9; the lightmap's on-screen consumer
> was NOT FOUND statically and needs a live vertex-declaration capture, NOT
> more disassembly), and Blender's lightmap COLOUR-SPACE (§13.2 — the client
> blends in raw byte-space, `import_gwmap` in scene-linear; a visual fix, not a
> blind flip).
>
> **What else is still open** is FINDINGS §8, and it is now short: the
> quadrant's `+u` ORIENTATION (a convention, not a measurement), and three
> named-but-not-understood fields (`table_b`, tag 0's `tex_word`, the 4-dword
> table at `0x00A73DF8`). **Nothing on that list blocks a render.**

**Cold session: read [`studies/terrain/HANDOFF.md`](studies/terrain/HANDOFF.md)
FIRST** — the traps, not the status, in the pattern `studies/isle/HANDOFF.md`
established. Then [`FINDINGS.md`](studies/terrain/FINDINGS.md) §7.6–§12, and
[`studies/terrain/PLAN.md`](studies/terrain/PLAN.md) for the original ladder.

**The 2026-08-15 text from here down is HISTORY.** The props round trip landed on a map
whose GROUND has no material: measured in Blender itself, the terrain is the only
object in the scene with no material slot — **186,368 of 326,708 faces (57%)** and very
nearly all of the visible area. Every one of the 516 props is textured; the map surface
is not, because nothing mapped a tile byte to a texture.

Six rungs, T1–T6, **all landed**. T1 `5bf5a20`, T3 `44e0f78`, T4+T5 `a337c5c`,
**T6 `bee684d`+`83fb4cf`+`6608c18` (2026-08-14)**; T2 was answered early out of the
client rather than run as a rung.

**AND THE ARC IS NOT DONE, because the criterion was never "the rungs land" — it
was that the ground looks like Guild Wars.** It does not. The owner went to Kamadan
in the retail client and photographed the same spot: organic grass/dirt boundaries,
no 96-unit grid. Two of this arc's own claims were STRUCK on that evidence —
"per-cell variation removes the repetition" (`5c92603`) and "the visible tiling is
inherent and the client draws exactly that" — both produced by reasoning from our own
render instead of comparing against the client, which is the failure mode
`CLAUDE.md` opens with.

**What landed since, and it is real progress on the mechanism.** The per-cell corner
SELECTOR at `chunk+0x2B4` went NOT FOUND → read → **CLOSED** (`139acc3`): it is a
corner permutation generated by a **selection-sort comparator network** over the four
corner types, reproduced **2048 of 2048 cells** against memory dumped from a running
client. `trnblend.SELECTION` is no longer the `"identity"` pin. Getting there needed a
32-bit `int3` hook DLL (`toolkit/clientscan/trnhook/`, carve-out 3), and the route to
it is instructive: hardware breakpoints are DEAD in this client — proven by a control
that armed an address the process was provably executing and saw nothing — and five
earlier "the terrain functions are never called" readings were all measuring our own
broken instrument. Two commits of conclusions were retracted (`931397d`).

**The blocking item is now a format bug of our own making** —
`studies/terrain/FINDINGS.md` §7.10. `layers.u16` carries no permutation, so the
exporter picks a coverage quadrant in permuted space and the Blender importer places
its alpha in physical space; harmless while the selector was pinned to the identity,
wrong for ~1 cell in 7 now that it is not. The layer MODEL is verified sound
(7,156 mixed cells, 0 coverage failures); the interchange is what drops the
information. Two candidate fixes are written up and neither is chosen: an `int3` at
`0x00761A25` dumps the client's own per-cell layer descriptors and decides it, and
that instrument works. **Also still open and still unimplemented: the base layer's
OWN UV rectangle** (`obj+0x68/0x6C` span, `obj+0x70/0x74` origin, §7.2) — the
mechanism most likely to govern large-scale repetition.

- **T1.** `atex.split_trailer` splits an ATTX row and `decode_rgba` reads one end to
  end. `parse` still REFUSES ATTX and that is the design. Criterion met on the whole
  corpus: **349/349 maps, 1,656 distinct textures, 1,652/1,652 ATEX-family close and
  decode.** The boundary is WALKED — the two rivals (`find`, `rfind`) are live
  functions in the test against a fixture built to separate them, because the corpus
  cannot: `ffna` occurs exactly once on 1,648/1,648 rows. **ArenaNet declares the
  boundary herself** in a 12-byte footer `{u32 head length, u32 0, b"XTTA"}`, equal to
  the walk on 1,648/1,648 with two controls at 0.
- **T2 (from the client, SINGLE witness).** The binding is **`dep[tile]`, DIRECT** —
  `TrnTexBlendLo` indexes the texture array with the raw tile byte; the table it also
  feeds is only COMPARED between a cell's corners. The corpus confirmation is still
  worth running (41 of 80 maps discriminate) but no longer blocks anything.
- **T3.** **One cell = one 128×128 variant = 96 world units = its inner 111×111
  texels**; `tileVar[v]` = texel `(128*(v&1)+8.5, 128*(v>>1)+8.5)`, so variation *v* is
  quadrant *v*. The rung's own hypothesis was REFUTED — the scale comes from no map
  field at all, only compile-time literals plus a tile count that cancels.

**Two corrections worth more than the rungs.** `PASS_TERRAIN_BORDERS` was recorded as
used by "0 of 49,800 sampled levels" and is used by **every ATTX row** — the sample
could not contain one, because `parse` raised on all 1,648 until T1 landed. And
`decode_rgba` was **not returning what the client uploads**: the client regenerates the
border band by mirroring and we left it zero, a black 8-pixel cross through every
terrain texture. `atex.mirror_borders` fixes it (15,360 band pixels changed, all 15,360
zero before, **0 interior pixels touched**) — and that zero had already corrupted a
measurement made in the same session, written up rather than quietly amended.

`terrain.py`'s **tag 3 moves NOT FOUND → MEASURED on both counts**: it is the per-cell
tile VARIATION selector (0 = take the PRNG's pick, Lehmer/MINSTD reseeded per 32×32
tile with `(tile.x << 16) ^ tile.y`), and `bits_at`'s `(i & 3) * 2` guess was already
exactly the client's convention.

- **T4** (2026-08-14). `mapexport.build_terrain_textures` — manifest format_version 3,
  PNGs under `terrain/` keyed by file id, one table row per tile byte with the MFT's
  (size, crc), the corrupt-a-byte control refusing the whole export. The binding is
  `dep[tile + (1 if tag3b else 0)]`, its law MEASURED **349/349** and enforced as
  refusals — which **corrected the study's own "len(table_a) == len(dep) on 80 of 80"**
  (true only without the second tag-3 record). And the mixed population T1 found is
  **entirely the 24 tag3b maps' extra LEADING entry**: 17,089/17,089 tile positions are
  ATTX, so no retail tile can be undecodable — the V8U8 pair lives in the slot the
  binding never indexes, meaning UNVERIFIED. `studies/terrain/FINDINGS.md` §4.
- **T5** (2026-08-14). The ground has a material: one per distinct texture,
  `material_index` per face from `gw_tile` through the manifest table, T3's UV window
  (inner 111×111 texels). ~~quadrant 0 pinned — tag 3 is not exported and the
  PRNG not reproduced~~ — **all three superseded by T6**: tag 3 IS exported, the
  PRNG is reproduced bit-exactly (including its magic-number division quirk), and
  the quadrant is per-cell. Criterion met at full coverage against the SIDECAR: all 212,992
  Pre-Searing face indices sha256-match a recomputation from `tiles.u8` outside
  Blender; `--no-terrain-textures` is the control. A tile with no decodable texture
  gets its OWN magenta slot, never slot 0. Kamadan renders as a place: base tiles read
  as ground; **alpha-overlay tiles draw their unwritten regions opaque and stripe**,
  which is §3.5's three-layer blend not being reproduced — **T6 fixed this**, and
  the scene now blends. What it did NOT fix is the match to retail; see the head of
  this block. FINDINGS §5.

**What a follow-on session must not rediscover** (T6 has landed; this stands as the
model, not as work to do): terrain is genuinely **three blended layers per cell** with
alpha as a mask (only 7 of 192 tiles fully opaque); the layer count is decided by
COMPARING `tileTypes` between a cell's four corners (T2); each 128×128 quadrant is an
AUTHORED coverage shape, confirmed from the art itself on **97 of 101** Kamadan
textures independently of the client tables; and the corner permutation is a
selection-sort network, closed at 2048/2048. None of that is open. **The prop fall-through is still open** — unbound
faces keep `material_index = 0` and silently draw whichever image landed first, 31.6%
of prop screen area on Kamadan, which is why its rocks render near-black
(`studies/terrain/PLAN.md` §4); the GROUND now refuses that pattern, the props still
don't.

### 8.0 Next, as of 2026-08-11 (`10b11dc`+, suite 53/53, 1,982 checks — a FROZEN snapshot; the suite is 85 files / 4,161 checks as of 2026-08-14, `python toolkit/run_suite.py`)
### Cross-build resilience — the arc that cost the update risk (2026-08-12)

**[studies/crossbuild/PLAN.md](studies/crossbuild/PLAN.md), results in
[FINDINGS.md](studies/crossbuild/FINDINGS.md).** Maintenance, not a rung, so no R-number —
§6's risk row above is what it changes. Four of nine deliverables landed:

- **`msgshape.py` derives the message tables** (`db26a00`). It had 25 addresses from build
  38797 and used them as the lookup, so on the older vaulted build it printed `cmd slots 0`,
  `descriptor invariant violations: 0` — vacuous over ZERO descriptors, byte-identical to a
  healthy run — and **exited 0**, while `msgshape.py 0x00E5` claimed the opcode "is in no
  table on this build", which is a statement about ArenaNet's client and was false. 651 of
  751 entries were dying at one `continue`. `RegisterMsgs` is now anchored by byte shape and
  its 14 callers parsed; the older build yields 25 tables, 666 messages and four passing
  oracles. `test_msgshape.py`, 37 checks — the gate `studies/review/FINDINGS.md`:585 called
  the cheapest in the repo and left un-wired.
- **`asserts.py` derives its callee** (`458b79d`). Both builds now return
  `single-routine=True`; the older one's corpus was untrustworthy and feeds `codescan --in`.
- **`pinned.find()` verifies and fails closed** (`25cd1c4`), and knows there is more than
  one build. It used to hand back the auto-updating `C:\gw` install with a warning string
  and no refusal.
- **The census** (`buildpins.py`): **68 build-coupled addresses, 7 files** — 26 converted,
  5 accepted, **37 outstanding in three jobs**. Neither figure previously in circulation
  reproduces; both are corrected at their source.

**Next in that arc, cheapest first:** the three RVAs in `itemprobe`/`agentprobe` that
dereference into a *running* client with no build check at all; `genericvalue.py`'s 32,
which already contains the gated pattern it needs; `SIG_KEYS`' three implementations
disagreeing on the refuse-on-2+ rule, one of them the patcher; then the build-id reader and
the `origin.py` build stamp, without which "stamp every capture with its build" is
unsatisfiable for half the corpus.

### The update arrived — build 38833, 2026-08-14

**[studies/crossbuild/FINDINGS.md](studies/crossbuild/FINDINGS.md) §7 is the record.** The
whole arc above was built on n=2; ArenaNet shipped **38,833** on 2026-08-13, the owner took
it on 2026-08-14, and `RUNBOOK.md` §0/§0b was walked on a real update for the first time.

- **The derivation work held.** 8 of 8 signatures at their exact hit counts;
  `msgshape` (25 tables, 666 messages, 4/4 oracles), `asserts` (`single-routine=True`),
  `buildid` (38833), `srctree` and `dump_dh_params` (**GO**) all read the new build.
- **`genericvalue.py` REFUSED it** — its int-main switch at `0x008129CC` is restructured —
  and took `avevents.py`'s property map with it. That was the outstanding job named two
  paragraphs above, and it is now the arc's one measured casualty rather than a hypothetical
  one. It failed the *right* way: named the address, called it a finding, did not guess.
- **The headline claim needed weakening, not strengthening.** "Any patch anchored to a raw
  address is broken by the next build" is too strong: this 15-day bugfix left `Gw.exe` the
  **same length** and left the build getter, assert callee, DH struct and AgentView
  allocators at **identical addresses**. Pinned tools are *unpredictably* broken, not
  reliably broken — worse, because they earn trust they cannot honour.
- **`updatecheck.py` — this arc's own deliverable — printed a vacuous pass** on its first
  firing, claiming the anchors held on a build it had never opened, because it read
  signatures only from the vaulted builds. Fixed; it now reads the live install and names
  what it read. `RUNBOOK.md` step 3 also omitted `--no-updater-patch` and produced a wrong
  live-capture build; fixed, and the `CLAUDE.md` sentence that contradicted it ("the
  updater kill switch … wanted on both configurations") is **corrected** — the switch is
  wanted on the loopback build and must be OFF for the live-capture one.
- **Registered, not pinned.** `pinned.BUILDS` carries 38833; `PINNED` stays **38797**,
  spelled explicitly rather than `BUILDS[-1]`. Moving the pin is a re-measurement arc.
- **The claimable-row collision is now 3 of 3** — this update recycled both 35300 and 35301,
  the slots `datplan.plan_insert` claims. **And as of 2026-08-15 there are none left to
  collide over**: `free_rows` returns `[]` on loopback 38833, live 38833 and live 38797, so
  every allocation must now APPEND. See the next bullet, and
  [studies/datwrite/FINDINGS.md](studies/datwrite/FINDINGS.md).
- **`datwrite` can ALLOCATE as of 2026-08-15 — `toolkit/mapdata/datalloc.py`**, the third
  write verb, and the one that stops authoring needing a victim. `--replace` and `datmove`
  both start from a row ArenaNet made, which is why every authored map so far has displaced
  a real retail area. This appends MFT rows for a file that never existed and registers it
  in the file-id table. **Proven end to end on a copy of the live 38833 archive**: a map
  pair allocated at file id `0x5F0B0`, `datcheck --preflight` 10 of 10, both crc rules,
  0 overlapping pairs over 177,741 live rows, then reverted **byte-identical** by sha256.
  The binding constraint is small and now enforced: the MFT may grow only into the slack of
  its own last 512-byte block — **424 bytes = 17 rows** on the 38833 pair, where the gap
  measure claims 4,266,920 — because the next block is a container generation or, on live
  38833, EOF. Seventeen rows is eight authored maps. **Three latent defects were found and
  fixed on the way**, all present in the tree beforehand: `datplan.free_rows` offered an
  ARMED MAP HEAD as a free slot (`vault/dat_c2` returned `[71496]`, map 143's head, still
  chained to its partner — and no checksum covers the swap); `Writer.fix_mft_self_crc`
  computed the crc over the pre-growth table for any caller that grew it, silently, with
  `datcheck` still 10 of 10 because datcheck does not check the self-crc; and `revert()`
  could not open a torn archive, because `Archive.__init__` refuses when
  `entry_count * 24 != mft_size` and that is exactly the state the two unavoidable 4-byte
  writes pass through. `test_datalloc.py`, floor 87, six sabotages all red.

- **The server broke too, by the rule-book's own named defect.** `authsrv.load_keys()` did
  `sorted(rurik_dh_*)[-1]`, so patching 38833 silently handed a 38797 client the wrong DH
  key — handshake completes, ARC4 is noise, `Code=058`. The key is now bound to the build
  the client announces in its version frame, with a refusal when no key matches.
- **Suite 94/94 green, 4,686 checks, 2,721 s**, on the tree with `main` merged in. Three
  runs: 89/5 before, 93/1 after the code fixes, 94/0 once the new loopback client was
  caged (a UAC prompt, by design).

- **`genericvalue.py` IS DERIVED, and the casualty is closed** (FINDINGS §8). Its 27
  build-coupled addresses are **zero**: the dispatchers are the handlers the client's own
  receive table gives for opcodes `0x009F`/`0x00A2` — so the chain bottoms out in
  `RegisterMsgs`, anchored by byte shape — and every switch, default, id span, chain case
  body and gate falls out of them, with an asserted count at each link. All three vaulted
  builds now read **47 int / 14 float ids, `{40}` untouched, main switches disjoint**, at
  three completely different address sets. `avevents.py` is back to 39 of 67 on all three.
  **The repo-wide class-(a) census is 73 → 46**, its first large fall. **47 on 2026-08-15**,
  one pin added on purpose: `atex.TABLES_BUILD` records which build its two codec VAs were
  measured on, and the bare VAs are what let a test silently re-read them against the wrong
  client (FINDINGS §7.9).

**Next — and this list was STALE as written, which is worth saying rather than quietly
fixing.** It opened "cheapest first: the two live-memory readers in
`itemprobe`/`agentprobe` — three RVAs, and on a new build they do not compute a wrong
number, they dereference a stale address inside a *running* client." **That describes
their state before 2026-08-12.** Both now call `pinned.assert_build`, which REFUSES by
default; `--any-build` is an explicit opt-in that prints "every address below may be
reading something else entirely". Gated was one of the three verdicts §6 allowed, and
these two took it — so the arc's scariest sites are closed, not pending. VERIFIED
2026-08-15 by reading both call sites.

What genuinely remains in the census is bookkeeping rather than liability, and it is worth
naming so nobody re-opens it as work:

- `msgshape.py`'s 25 and `asserts.py`'s 1 are **cross-check tuples** the plan asked to keep
  when their lookups were derived — they print on disagreement and are not consulted.
- `pinned.py`'s 8 are build numbers and sizes, two per registered build by construction.
- `atex.py`'s 3 and `modelfile.py`'s 5 are ArenaNet's own tables carried as literals so the
  modules work on a bare machine, each re-read out of the vaulted image by its test. Those
  tables ARE build-coupled — MEASURED, both differ on 38519 — so the guard that matters is
  the test resolving the right image, which is what §7.9 fixed.

**The one deliverable still open is rung 6**, and 38833 came and went without advancing it:
the durability tracer sits in `vault/dat_durability/`, whose mtime is still 2026-08-13,
because no updater touches an inert vault copy (FINDINGS §4). It will keep costing an update
every time one ships.

**The decision it needs is NOT the one this paragraph asked for until 2026-08-15.** It said
"accepting either a search for an uncompressed row or one broken map", and both halves are
now measured away (FINDINGS §4a): **0 of 361 map rows are stored uncompressed**, so the
first does not exist, and `deploy.py --area sculpt --install` writes a real loadable map —
proven surviving a play session twice — so the second is unnecessary. The broken map was an
artifact of how the tracer was first staged. What actually remains is an **account-posture**
call: the only updater-enabled client is the LIVE build, so a patch reaches our authored row
only if a live client opens a modified archive (route A, §6.2). The price may be smaller
than it sounds — the updater runs at launch, so launch-and-quit is plausibly enough, with no
play session and nothing that loads the armed map — but that is UNVERIFIED and wants
predicting before it is tried.

**Both of the judgement calls this arc parked are now settled** (2026-08-14):

- **`content/maps.toml`'s Pre-Searing file id is the PLAIN `0x1B97D`**, not the renamed
  `0x8001B97D`. Bit 31 is `FcArchive` announcing a pending replacement, so the renamed form
  was one archive copy's transient state recorded as the map's name — and 38833 installed
  that replacement, after which it binds nowhere. `archive.py` had already drawn the rule:
  *send the plain logical id and serve from an archive that binds it.* The plain id works on
  **both** archive generations; a mixed pair (post-update client, pre-update server) is
  refused by `contentids.preflight`, because the update delivered genuinely different
  geometry. Point `RURIK_DAT` at a post-update archive to run the new client. FINDINGS §7.5a
  has the three measured pairings.
- **`CLAUDE.md`'s updater sentence is corrected.** The kill switch is wanted on the
  **loopback** build and must be **OFF** for the live-capture build, which has to stream
  content; only the multi-instance NOP is wanted on both. `RUNBOOK.md` and the vault were
  right and now say so in one voice.

### 8.0 Next, as of 2026-08-11 (`10b11dc`+, suite 53/53, 1,982 checks)

**Arc status, 2026-08-14:** the tooling below was cherry-picked onto `main` from
`claude/studies-crossbuild-plan-e32afb`; that branch's *study docs* were NOT, because
`main` continued the same arc independently through 2026-08-14 (11 further commits,
and `studies/crossbuild/FINDINGS.md` on `main` is the live record). Read the
deliverable list below as the state of the TOOLING, not of the research.

*1,927 is **derived, not re-summed**, and says so: the 1,878 below was measured over 50 files, and this session added `test_behaviourrun.py` (35, new — the file has been **36 since `1598f61`**, 2026-08-12, which added the both-clocks MARK check; the 35 is the count this arithmetic actually summed, kept so the sum stays checkable) and took `test_wirecapture.py` from 28 to 42 — both counted from real green runs. 1,878 − 28 + 42 + 35 = 1,927. The suite runner reports 51/51 green in 611 s; its per-file log truncates, which is what made the earlier 965 wrong, so the arithmetic is shown rather than a figure quoted from a partial log. The 1,878 figure's own method:* Method, because the gap is
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

0n. **NAME THE SILENT OPCODES — 239 candidates. RUNNING 2026-08-13, ~2.5 h of harness.**
    `shotloop.py` (one opcode per fresh client, screenshots through the hold) +
    `shotlabel.py` (joins the send to the frames, builds the local labelling page).
    See §3.6. The text below is the manual procedure it replaced, kept because the
    `--encstring` note and the four already-named opcodes still apply.

0n-old. **The manual procedure.**
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
    writes ArenaNet's text into the repo. About 40 s per opcode unattended. Deferred
    2026-08-12 at the owner's request, **and taken up 2026-08-13 — see 0n above, which
    automates exactly this.** Note the corpus string is picked fresh at plan time and one
    of them (U+3D64) is not encodable in cp1252, which is how the harness pump defect in
    §3.6 was found. Four are done:
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
3. **Finish R4a.** ~~Nothing swings back. The player cannot die.~~ — **both met 2026-08-11**,
   see §3's R4a row; this item was written 2026-08-06 and restated the retired criteria for
   eight days. What is actually left is the agent *model*: no AI, no pathing (the Hatcher
   stands where it spawned), no resurrection shrine (the revive is a timer), and energy is
   not restored on revive. The agent table
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
    **(b)** ✅ **DONE 2026-08-12 (FINDINGS §31) — the within-map portal is LANDED, and
    this item is no longer blocked on anything.** Two trapezoids landed first (§27,
    ArenaNet's own two-trapezoid plane walked in front of a client; §28 settled the DAG
    semantics at 0.999935 over 3.6M queries); §30's props-chunk prerequisite is now
    satisfied rather than pending, and §31 states in its own words that this item is done.
    **A portal we authored joins two planes.** `portalprop` (`plane_map [0, 0]`, **18 of
    18 gates**) walked **65 s with no crash**: the bounding box opened from
    (0, 64)..(2048, 3072) to (0, 0)..(3072, 3072), and the client reported **plane 1 on 19
    of 49** reports with **17 past x = 2048** — where the no-portal arm was pinned at
    x = 2048.0 and reported plane 0 on 76 of 76. Plane 0 is x 0..2048 and plane 1 is
    x 1792..3072, overlapping by 256 units with the spawn clear of it. The props chunk
    (6,585 B) and its model dependencies (89 B) are **carried from row 33086 at run time,
    never stored** — `mapbuild`'s FINDINGS 14 pattern — and their insertion point is
    read from a real map rather than chosen.
    **The control §30 demanded was run, and it crashed as predicted.** `portalpropbad`
    (`plane_map [0, 67]`, one past `propCount`, **RED** by the §30 gate) died on
    `Assertion: index < m_count, Array.h(587)`, loaded at BaseAddr 0x00400000 so the trace
    carries §30's static addresses unmodified, and at the fault **`edi = 0x43 = 67` — the
    number we wrote into tag 12, in the register the disassembly said holds the index.**
    The diagnosis did not merely predict a crash; it predicted which value would be in
    which register, and that is what arrived. It also answers §30's open question about
    whether the prop must carry the surface: **a prop index only has to be IN RANGE**, and
    prop 0 of row 33086's 67 is somewhere else entirely in the world.
    **Residuals — named in §31.4, NOT closed by the landing, and carried as live items
    (h) and (i) below** so they are not read as closed along with this one. What plane 1
    looks like **underfoot is untested**: the character crossed and kept walking, but
    nothing measured its z, our terrain is flat, and a plane mounted on a prop whose model
    is elsewhere may well be placing the character on nothing. The interesting version of
    this rung is a plane whose prop IS its surface. And **one prop index was tried, not
    the space** — `[0, 0]` works, `[0, 67]` crashes, nothing between was tested.
    Fixed en route: the harness said PASS over the crash again, for a new reason
    (`judge()` runs before the walk and this client died during the HOLD), so a
    hold-time exit now retracts the verdict too.
    **The 2026-08-11 text from here down is HISTORY — read it for the reasoning, never
    for the status.** ~~The portal is BLOCKED, and §30 says on what.~~ Tag 12 `plane_map`
    is a per-plane PROP INDEX: every plane above 0 is mounted on a prop, so a two-plane
    map needs chunk `0x20000004` with `propCount > max(plane_map[1:])`. We shipped
    `[0, 0]` into a props-less map and crashed a client twice. `gates()` now refuses
    that shape.
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
    **That last warning is the one line above that is not history**: it is why the run
    that landed this item added a plane rather than removing one, and why a green
    single-plane run says the map is walkable and says nothing about `plane_map`.
    **(h)** ⬜ **A plane whose prop IS its surface, with the z MEASURED** — (b)'s first
    residual, §31.4. The portal that landed mounts plane 1 on prop 0 of row 33086, a prop
    that sits somewhere else entirely in the world; the character crossed onto it and kept
    walking, but nothing measured its z and our terrain is flat, so **a client standing on
    nothing and a client standing correctly produce the same numbers in every arm that
    run recorded.** What settles it is a prop whose model actually carries the surface the
    plane describes, plus a z read from the client's own position reports rather than
    inferred from the fact that it kept moving. Distinct from (c) and neither answers the
    other: (c) is the TERRAIN height field, this is a prop-mounted plane.
    **(i)** ⬜ **The prop-index space, not one point of it** — (b)'s second residual,
    §31.4. `plane_map [0, 0]` walks and `[0, 67]` crashes on `propCount`; nothing between
    was tried, so **"a prop index only has to be IN RANGE" rests on one in-range value,
    and that value is 0.** Cheap, and it is the arm that could refute the claim: the same
    single-`u16` edit at offset 14900 that separated the two arms, with an index in the
    middle of the range instead of at either end.
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
    **(e10f)** ✅ **DONE 2026-08-12 (FINDINGS 49). THE TERRAIN WEARS OUR PAINT.**
    Old rung F2, one variable against the walked map: tag 2 painted by height band,
    tags 4/5 and tex_word read from the donor at run time (table_b is a property of
    the TEXTURE — inventing it is wrong when reading it is free). Compiled tag 2
    came back VERBATIM, everything else carried, and the owner walked the four
    bands. Still NOT FOUND: table_a's grouping, table_b's 7 bits.
    **(e10g)** ✅ **DONE 2026-08-12 (FINDINGS 50). ANOTHER BIOME'S GROUND RENDERS.**
    Pre-Searing's four most-used textures (by its own census, read at run time)
    on the walked map's geometry, table_b travelling with its files. One run, all
    readback HIT, owner confirmed. Texture files are ordinary archive files;
    nothing ties a map to its biome's set.
    **(e10h)** ✅ **DONE 2026-08-12 (FINDINGS 51). THE SUN IS OURS.** One byte —
    tag 0's angle, 68.7° → 36.5° — re-baked 985 of 1,024 lightmap bytes, and the
    elevation sweep orders with the byte. The pre-registered N·L inequality missed
    on its own model (no cast shadows — recorded as the model's defect), and the
    visual was masked by the missing environment, which (e10i) then explained.
    **(e10i)** ✅ **DONE 2026-08-13 (FINDINGS 51). THE SKY ARRIVES.** The
    environment pair 0x10000009/0x11000009 — never carried by our maps, present on
    every retail one — added in retail's slot with Pre-Searing's 639 B payload
    borrowed at run time. The compiler carried it VERBATIM; the owner: "yep that's
    a sky, and it was key to the lighting. the ocean looks much better now." The
    payload is 639 bytes NOT UNDERSTOOD, counted borrowed. `stripbuild` takes the
    pair as of this rung (test §3e, floor 51). Presentation still open: SOUND, and
    understanding the environment payload.
    **(e10j)** ✅ **DONE 2026-08-13 (FINDINGS 52). THE MAP HAS A VOICE.** The sound
    pair 0x10000012/0x11000012, Pre-Searing's 89 B payload borrowed at run time,
    carried VERBATIM; the owner: "background audio plays birds and wind."
    `stripbuild` takes the pair under the env rules (test §3e, floor 54). THE
    PRESENTATION LADDER IS WALKED — what remains is AUTHORING the borrowed
    payloads (env 639 B, sound 89 B) instead of wearing Pre-Searing's.
    **(e10k)** ✅ **DONE 2026-08-13 (FINDINGS 53). THE TWO PAYLOADS ARE UNDERSTOOD.**
    Both borrowed chunks are now decoded to typed fields and re-encoded **349/349
    byte-identically** — corpus-derived, then CORROBORATED against the client
    loaders (`0x0071ef70` env, `0x0076afc0` sound), which corrected the corpus
    three times (env header is 8 B not 5; the tag5-width flag is the header word
    not tag0's count; tag8 is a real 17 B section not tag7's tail).
    `toolkit/mapdata/soundchunk.py` + `test_soundchunk.py` (floor 21) and
    `envchunk.py` + `test_envchunk.py` (floor 20) land the codecs, each with a
    cross-chunk oracle a codec cannot force (sound: emitters in the Map Parameters
    rect 318/318; env: dep fields in bounds of `0x11000009` 0/5,897). **Sound is a
    positioned-emitter layer** — `{dep, x, y, r_lo, r_hi, r_mid}`, radii squared at
    load, sounds one hop deeper in `ffna8` descriptors — and is AUTHORABLE.
    **Environment is parallel aspect arrays + a spatial zone list**, where a
    configuration is a SELECTOR TUPLE — tag8 is the map default, a tag9 zone is the
    same tuple plus a circle. Fog (tag2) and zones typed; **tag6 is the WATER
    record**, not the "main environment" a size-based guess called it, which is why
    (e10i)'s "the ocean looks much better now" was literally true. **The sun is
    written twice**: tag8's angle byte predicts the terrain chunk's own
    `angle_index` on 313/349 maps (ratio exactly 127/32), so our authored maps —
    which moved the terrain byte and borrowed the env chunk — had a baked lightmap
    and a runtime sky that disagreed. NEXT RUNG (needs owner go-ahead + harness): a
    client run authoring a sound chunk from scratch — Pre-Searing's same sounds at
    custom `(x, y)`/radii, a minimal delta from (e10j)'s proven dep list — and, if
    the compiler accepts it, promote authored sound (and fog/zones/sun) into
    `stripbuild` the way (e10j) promoted the borrowed pair. Still open: tag6's
    floats at +0x21/+0x25, and what tag0/tag1/tag3 ARE as aspects (their fields are
    read out; their purpose is NOT FOUND). Record: `vault/research/envsound-2026-08-13/`.
    **(e10l)** ✅ **DONE 2026-08-13 (FINDINGS 54). OUR OWN BYTES COMPILE.** The gate
    (e10k) named, run and passed: a map whose env and sound chunks were ASSEMBLED BY
    OUR CODECS — three emitters at our positions, fog recoloured, and **the zone list
    grown 11 → 12** so every byte after tag9 shifted — compiled clean and both
    payloads came back VERBATIM (env 671 B, sound 89 B, sha-matched), no assert.
    The zone growth is the load-bearing delta: a codec replaying stored counts (the
    saboteur `test_envchunk` §2 builds) would have declared 11 while carrying 12 and
    desynced ArenaNet's parser, so **the count re-derivation is now checked against
    the real consumer** rather than only against our decoder. `stripbuild.build()`
    accepts typed `EnvChunk`/`SoundChunk` and counts them GENERATED, raw bytes still
    BORROWED (`test_stripbuild` §3f, floor 54 → 59). Owner was away and none of this
    needed eyes or ears. Three procedural defects are recorded in FINDINGS 54 rather
    than scrubbed — wrong archive armed, `ar.entries[row]` off by one, and a harness
    PASS that meant "reached A map" while the client never loaded ours; the second
    was caught only because `datcheck --diff` CONTRADICTED the readback.
    Record: `vault/research/e10l-authored-2026-08-13/`.
    **(e10m)** ✅ **DONE 2026-08-13 (FINDINGS 55). ARENANET NAMES THE FIELDS.**
    §53's two loose threads closed offline, no client. The client looks its shader
    constants up BY NAME and the strings are in the image, so tag6 `+0x21` is
    **`waterFresnel`** (string `0x00A6C430`) and `+0x25` is **`waterSpecularColor`**
    (`0x00A6C474`) — our labels replaced by ArenaNet's. Both are also GATES: each
    promotes the water technique, so the path that reads a field is unlocked by that
    field. **tag1 is POST-PROCESS** {BloomAmount, PostProcSaturation, tint .w, B,G,R}
    from the constant table at `0xBF7DA8`, corpus-corroborated (saturation 1.0 on
    648/741, tint off on 571/741) and correcting this repo's "raw u16" to two thirds
    of a packed colour; **tag3 is the DIRECTIONAL LIGHT**, two {rgb, intensity} pairs
    to `GrLight`, which REFUTES the idea its u16s were dep indices. Still NOT FOUND
    and deliberately unnamed: tag0 (consumer at `0x0071A4C0` unattempted), tag4,
    tag7 — naming tag7 "wind" is precisely the move that mis-named tag6 once already.
    Two of ten namings were REFUTED on audit, one of them a false "no correlation"
    contradicted by its own numbers (χ²=92.4, 0/2000 permutations).
    `envchunk` gains `postproc()`/`lights()`; test floor 25 → 28, 40 under `--all`.
    **(G)** ✅ **DONE 2026-08-13 (FINDINGS 56). THE LADDER IS CLIMBED.** Rung G of
    the original ladder — *"someone models a shape in Blender, runs one command,
    and walks around it in the retail client"*, dependencies **all of the above** —
    is one command: `deploy.py --area plaza --install --launch --dat <copy>`, with
    the recipe in `content/areas.toml` (`source = "invented"`). Geometry → borrow →
    assemble → verify → install → launch → read back, refusing at each step. The
    client compiled it and every readback check is green: **55 trapezoids built
    from our terrain** (against 22 for the flat map), heights **1024/1024**, env and
    sound VERBATIM, 5 props, and the spawn in **exactly one** trapezoid with two
    retail spawns as 0-scoring controls. **3,941 B, 77.90% ours**, 770 borrowed
    bytes every one named. Three defects, all in the JOINS rather than in any
    component (every one of which was green): structural constants must come from a
    map SHAPED like ours (Pre-Searing's Zones is 7,208 B against 34, which blew the
    reservation), the client must OWN the archive you armed, and a documented stage
    that no line runs is a docstring. `test_deploy.py` (floor 34) pins all three —
    and its own syntax check was VACUOUS at first, passing against a sabotaged
    source, so it now runs that sabotage as a negative control.
    Not a hot reload: the client compiles at load, so iterating means running it
    again. Record: `vault/research/rungG-2026-08-13/`.
    **(H)** ✅ **DONE 2026-08-13 (FINDINGS 57). THE SIZE CEILING IS BROKEN.** Every map this toolkit built was 32x32 because `datwrite` cannot grow
    a reservation — not because of the format, whose cap is 16,777,216 cells.
    `deploy --install` now picks the verb from the size, and a **96x96 map, 21,926 B,
    was relocated into a row reserving 4,608**: terrain 9,216/9,216 exact, **96.03%
    ours**, 10/10 open-time rules, 0 overlaps, exactly two rows changed. **THE RUN
    LANDED the same day**: the client re-bloated, built **88 trapezoids over 9,216
    cells** (the 32x32 plaza gave 55 over 1,024), matched our height field
    9,216/9,216, carried env and sound verbatim, kept all 12 props and put the spawn
    in exactly one trapezoid — no assert. **It also answers FINDINGS 39's standing
    question: a relocated row SURVIVES a play session** (10/10 rules, 0 overlaps, our
    row byte-untouched at 0x6FF0A00 afterwards). Two defects worth carrying:
    `snap_block` is a ONE-TILE function and a whole-field caller loses only
    CURVATURE (a 400-unit cliff round-trips, a smooth hill loses 2,752 samples), now
    `snap_field` with a negative control; and `--check-overlaps` is a read-only verb
    that returned 0 having written nothing while `deploy` reported success over
    ArenaNet's own map, so install now READS THE ROW BACK. Record: `vault/research/size-2026-08-13/`.
    **(I)** ✅ **DONE 2026-08-13 (FINDINGS 59). THE NAVMESH JOIN, AND IT IS
    A RETRACTION.** Every rung above says the client compiled our map and the
    character walked in it. True — and **the SERVER never once pathed on our
    geometry.** `load_pathmap`'s only call site was instance bring-up, i.e. after
    a client is up: on its default archive it read **ArenaNet's map 143 (27
    trapezoids)** while the client drew ours, and once pointed at our archive it
    got **EACCES**, because a running client holds its `Gw.dat` open exclusively.
    Both silent — the second is `load_pathmap`'s documented no-collision
    fallback, and the harness still reported PASS. Rung G's own headline run logs
    27. **How wrong: the walkable sets are DISJOINT** — 4,096-point grid on the
    sculpt map, 49 ours, 435 theirs, **0 shared**, spawn off ArenaNet's mesh
    entirely; 16 vault runs carry `collision suspended`. The stated prediction
    (>50% disagreement) FAILED at 11.8% and is recorded as failing: both meshes
    are mostly empty there, so unwalkable-on-both scores as agreement. Controls
    held (each mesh self-agrees 13/13, 27/27, 1270/1270; Kamadan 0%).
    **`authsrv.prewarm_pathmap` reads at startup**, the only moment the archive
    both holds our map and is unlocked — verified 13 trapezoids on our archive,
    27 on the default, refusal on an unconfigured map. **Serving an authored mesh
    is inherently TWO runs** (`--install` arms the head to zero, so the run that
    produces the mesh cannot serve it) and `deploy --serve` is the second, its
    verdict the server's own log line against a count `pathmap` read from the
    archive. `test_deploy` §6, floor 25 → 35, sabotage reddens 2.
    **THE RUN LANDED the same day, both predictions confirmed**: run 1 (armed)
    pre-warmed against an empty head and said so (`not an FFNA file: b''` →
    PRE-WARM FAILED, serves NO collision) — a SUCCESS there would have meant
    stale geometry and a wrong fix — and run 2 (`--serve`, unarmed) logged
    `[map] navmesh 0x287D3: 1 planes, 13 trapezoids`, matching what `pathmap`
    reads from the archive. Exit 0, readback green throughout (4,096/4,096
    heights, env and sound verbatim, 8 props, spawn in one trapezoid, 92.34%
    ours). **The server and the client now agree about the ground.** A third
    defect fell out: the two runs started **17 s apart under `--hold 40`**,
    because `session.hold_open` is gated on `keep_open` and `deploy` passed
    `--hold` alone — the flag named a wait that never happened. Fixed, pinned on
    the syntax tree, sabotage reddens 1. FINDINGS 58's "MEASURED" sentence is
    retracted in place.
    **(J)** ✅ **DONE 2026-08-13 (FINDINGS 60). THE ZONE IS POPULATED.** R5's
    criterion is "a new zone in TOML, hot-reloaded, walked" and the toolkit could
    author a zone's GROUND and nothing standing on it. `authsrv --area NAME`
    serves `content/world.toml` spawn rows carrying `area = NAME`; **three bodies
    stood in the sculpt map at their declared coordinates**, `3 of 3 placed`, run
    20260813T185442. No new protocol -- every body goes out through
    `create_agent_world` -- what is new is that the SET, the positions, the
    allegiances and the health are content rows. **This is what rung (I) was
    for**: a body goes out only where the navmesh says there is ground, and the
    sculpt map is **1.2% walkable**, so a coordinate picked by eye is ground one
    time in eighty. Positions are trapezoid centres read out of the mesh the
    client compiled; the server nudges and REPORTS, or refuses past 480 units.
    **The defect is the lesson: the first populated run placed ZERO bodies and
    reported PASS** -- `spawn_population` took the raw content row, whose
    `enc_name` is a list of string ids, so the codec refused every definition
    (`string of 28 code units exceeds cap 8`); the throw landed inside instance
    bring-up, so the harness passed, all six map checks were green and the
    command exited 0. Caught because the OWNER LOOKED AT THE SCREEN.
    `agents.npc_template` is public now and `deploy --serve` reads
    `area 'X': N of M placed` out of the server's own log. `test_population.py`
    floor 38; sections 0-2 could not have caught it (the bug was in entry
    construction), so section 2b encodes every row through the real codec with
    the raw row as a negative control. Seven sabotages, all red -- one CRASHED
    rather than reddening and one passed GREEN because it derived its probe from
    the constant under test.
### Naming the archive's map rows — 2026-08-13

**[studies/maprows/FINDINGS.md](studies/maprows/FINDINGS.md), `toolkit/clientscan/maprows.py`.**
The arc was opened to find the join `s_missionClientData` index → map file id.
**There is none, and that is now REFUTED rather than assumed** — three methods
that share nothing: an exhaustive packed-dword sweep against a 500-trial null
(21 hits, null mean 21.4, and *below* chance on distinctness); a backwards walk
of every producer of the file-id argument, which finds exactly two and both are
the network; and a sweep of every field of every map chunk, whose positive
control fires on the content UUID and on nothing else.

**What replaced it does not need a file id.** The table carries each map's
FOOTPRINT on its continent at `+0x48`/`+0x58` — a rect in terrain cells, unnamed
in every mirror — and its size equals the map file's terrain dims at the known
96.0 pitch, **319 of 319**, with a one-cell shift scoring **0 of 319** and a
random-size null at 41%. Against gw-preservation's hand-typed table (verification
only): **350 of 353, versus a 5.4% shuffle control**; on the rows named outright,
**15 agree, 0 differ, 5 are named that no upstream names**.

**Three corrections land on other documents.** The table is
`s_missionClientData` and **888/124 are ArenaNet's own numbers**, out of its
accessor's assert at `0x005A8580`. `textrec.combine()` moves from UPSTREAM to
**CORROBORATED** — the client computes exactly it at `0x004702B0`. And
`FORMAT.md`'s "the client does not mask" is **CONTESTED**: ArenaNet's own server
sent the MASKED `0x1B97D` in 9 of 9 live instance loads.

**(1) IS DONE, SAME DAY, AND IT REFUTED THE SESSION'S OWN CORRECTION.** The
client never masks — the index stores the id verbatim (`0x0047C027`), the lookup
is an exact 32-bit compare (`0x0047AA20`), and no retry exists on the map path.
**Bit 31 is a RENAME**: `FcArchive` binds `id | 0x80000000` and deletes the plain
name when a replacement has been requested (`0x007D7B70`), and `DnArchive`
re-links the plain id once it is installed (`0x004766F0`). The question open
since 2026-08-06 is closed.

What settled it was not the disassembly but a question nobody had asked: **which
archive the live client was reading.** It was `vault/run-live/`, and that copy
binds the PLAIN `0x1B97D` — to row 177262, not 7982 — and carries 9 bit-31 ids
against `dat_study`'s 25. So ArenaNet sends the plain logical id, our study copy
cannot answer it, and both "the masked form is refused" and "the masked form
works" were true of different copies.

**Operational consequence, and it touches `content/maps.toml`:** a `file_id` is
archive STATE, not a property of the map. `0x8001B97D` is right for `dat_study`
and wrong for `run-live`. Any content row carrying a bit-31 id records a
transient state of one copy, and a server should send the plain id and serve from
an archive that binds it. Nothing was changed on that basis yet.

**(B) IS DONE 2026-08-13.** `toolkit/contentids.py` + `test_contentids.py`
(floor 15) check that every `content/maps.toml` file id names the SAME FILE in
both archives a run uses -- identity by MFT size and crc, never by row, since row
indices do not survive a patch -- and `drive_client.assert_safe` refuses a
loopback launch when it does not. Gated to `RUN_ROOT`: a live run answers to
ArenaNet's own ids and must never be refused on our rows. The positive control is
`vault/run-live/`, which genuinely fails on exactly the two Pre-Searing rows.
Today the real pair is 10 of 10 clean.

**(C) IS PLANNED, NOT BUILT -- make content archive-INDEPENDENT.** (B) is a guard;
it tells you the two copies disagree, it does not let a content row survive the
disagreement. The defect it guards is real and structural: `content/maps.toml`
records a file id, and a file id is a fact about one copy of `Gw.dat`.

  *What C would do.* Record a durable KEY per map instead of (or beside) the id,
  and resolve the id at launch against the archive the CLIENT will open. The key
  has to be something both copies agree on when the bytes are the same map.
  Candidates, cheapest first: the MFT entry's `crc` + `size` over the stored
  bytes (already proven sufficient for identity by `contentids.py`, and free --
  no decompression); the map's dims from chunk `0x2000000C` (weak alone, 104
  distinct over 349 rows -- see the footprint work above); or the content UUID in
  the same chunk, which is per-map and stable but which `mapbuild.py` records as
  never read by the client, so nothing guarantees ArenaNet keeps it stable across
  a patch. **The crc is the one to try, and it needs measuring across a patch
  before it is trusted** -- a re-bloated map changed both size and crc between
  `dat_study` and `run-live` (1,300,036 B vs 1,300,044 B), so crc identifies a
  FILE, and whether it identifies a MAP across an ArenaNet update is exactly the
  open question.

  *Why it is not urgent.* The exposure is two content rows and one id, it is
  correct for the current pair, and (B) now makes any future divergence a refusal
  rather than a client assert. Do C when a second archive state actually has to
  be supported -- e.g. serving a live-updated copy -- not before.

  *What C must not do.* Silently pick an id. If two archives disagree the right
  answer is still to refuse; C only widens the set of pairs that can agree.

**Next.** (2) The remaining 296 rows are limited by information, not
effort: the archive carries a map's dims and nothing that places it on a
continent. A live capture on a known-named zone yields one exact `(map id, file
id)` pair at zero ambiguity, which is the cheapest evidence left and needs only
play, not analysis.
