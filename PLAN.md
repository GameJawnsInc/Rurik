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
| [build-wars/gw-skilldata](https://github.com/build-wars/gw-skilldata) | Community skill dataset | Repository MIT (its `LICENSE`, SPDX MIT via GitHub's licence API); the DATA carries the source wikis' licences per its README §Licensing — GFDL (GWW), CC BY-NC-SA 2.5 (GuildWiki), CC BY-NC-SA 2.0 FR (GWiki). Verified 2026-09-22, skills §54.8. Pushed **2026-08-04** |

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
| **R0a** | Vault + provenance gate + prior-art mirrors | A capture replays byte-identically from disk | ✅ **2026-08-04**, criterion met **2026-08-07**, `87179f3` (`toolkit/authsrv/replay.py`). Gate proven both directions, client pinned and hash-verified, prior art mirrored — and the `.raw` now decrypts back to the logged plaintext, 329 real captures reproduced exactly, all-or-nothing across 375. The stated criterion finally rests on the stated fact. See §3.1. |
| **R1** | Handshake against a local server | Client reaches character select | ✅ **2026-08-04 22:58**, `3a6b9c5`. Build 38797 rendered "Test Warrior" against our portal, our DH parameters, our ARC4 channel and our login burst. |
| **R2** | Presence | Your own body standing in a real map | ✅ **2026-08-05 11:15**, `d9b38c1`. |
| **R3** | Movement on real geometry | You walk to a wall and are stopped | ✅ **2026-08-05 17:40**, `81b6002` — the server reads the game's own navmesh. Movement itself landed at `b48c78b` (11:46). Estimated here as "a quarter, not a week"; it took six hours. **Movement FIDELITY is a separate question and it moved on 2026-08-19** (`448e07c`, `studies/movement/HANDOFF.md` §8): the warp is decoded in the binary — the snap is `0x006022B0` copying SYNC→ASYNC, reached only from `0x00605FC0`'s three message-driven callers, whose test is now decoded in BOTH halves (2026-08-20): a 100 u match against the client's own history chain — which never reads our grant — and failing that a fallback of **three gates, any one of which snaps** (straight-line separation over **299.33 u**, so exactly 300.0 u snaps; a walkable `pathCount == 0` meaning our granted position is off the navmesh; or the sync agent unable to take a first step). It is never evaluated per frame, and the snap reseeds **every** async agent. "Under 300 u is safe" is FALSE, and the 300.0f was recorded as walkable-path until 2026-08-20 when it is straight-line. Six candidate fixes are dead, **seven as of 2026-08-20**, and **no gate of the test is a server lever** — the only lever found is `0x002C`, already tried and removed by an earlier build. Both of the arc's instruments were repaired and mutation-pinned the same day: `movesync.py`'s hard bar now has TWO ARMS (implied speed > 400 u/s at dt ≥ 0.05 s, displacement ≥ 520 u below that floor), which takes the corpus from 61 to 64 hard rows over 961 captures and makes the three configurations read **7 of 267 / 20 of 468 / 13 of 197** hard jumps, **1.31 / 5.69 / 11.88 per minute of span**, magnitude p50 **1,969 / 569 / 582 u** — retail scores ZERO on both arms, and implied velocity is demoted everywhere to a labelled gate input, so magnitude and excess over the 288 u/s budget are the quotable pair. `pinned.py` now carries per-build TUPLES of accepted patched digests that the patchers themselves register, so the gate no longer refuses the 38797 we launch and can represent 38833. Tests: `test_movesync.py` 104 (floor 57), `test_pinned.py` 143 (floor 130), `test_buildid.py` 42, `test_buildpins.py` 40, `test_srclint.py` 22. **The PLANE channel moved again 2026-08-30** (`cde235d`, `studies/movecode/FINDINGS.md` §1z-n/§1z-o — the census): the plane-disagreement census over **11,754 scored reports** prices the repair's licence (2.34% of on-mesh disagree; a declared 0 disagrees 0.54%, a declared non-zero 12.91%); the mesh pin moved **IN BAND** (every capture's own `INSTANCE_LOAD_SPAWN_POINT` attributes all 12,215 reports — `noclipscore.py`'s hand-pin and `pathdiff.py`'s typed `--map` are retired, and the pin transfers to all 19 movehook captures by corpus-unique fingerprint); **gate 2 of the snap test HAS fired** (3 of 3 zero-answers followed by `reseed` in the same tick, exceptionless 214/214 — the plane channel is a WARP cause, not only a lock); R7's arming was a **TRUE POSITIVE the trigger structurally cannot fire on** (intermittent freeze tops out at 1.02 s of the 5.0 s HOLD); and the repair's `ambiguous` disarm has engaged **0 of 259** times — anti-correlated with the hazard by construction (§1z-o.9). The repair remains the one shipped default-ON arm with **no owner ruling — now §7 Q14**, and `studies/movecode/RUN-R8.md` pre-registers the run that fills the empty "armed, router off" cell (the shipped default has never been run armed). Instrument: `toolkit/clientscan/planecensus.py` (+ `test_planecensus.py`, 54 checks). **The arc's direction changed 2026-08-30 (owner): derive, don't iterate — and the derived object exists that same evening** (`472daa6`, `studies/movecode/FINDINGS.md` §1z-q/§1z-r): the client's AgTrack history chain is decoded whole and TRANSCRIBED server-side (`toolkit/authsrv/agtrack_mirror.py`, 64-check test), and the corpus replay (`toolkit/clientscan/agtrack_replay.py`, no client run) **validates the sync-agent simulation against every observed warp** — 223 of 251 hard-bar steps across 177 captures land ≤150 u from the mirror's simulated sync position (median 24 u; the 28 others are a second, non-AgTrack mechanism now measured per step), and the reprieve model's killing cell is EMPTY in the current regime (10/10 covered with reader-2 pruning; freerun misses = old-trail matches + one 0.6 u boundary case; known-bad arm degrades 11×). Policy target sharpened (§1z-r.4): keep q within 100 u of the CURRENT leg — old history is deleted by invisible resets and is never protection. **The rule is DERIVED and SHADOWED the same evening (§1z-s)**: `agtrack_guard.py` (three zones, three clauses — veto+replace with the safe re-pin-then-grant composition, the proactive arrival check that closes HOLE A, audited tube-keeping; every constant a decoded value or one arithmetic step from two), retrodiction pre-empts **217/251 corpus warps (10/10 current regime, 59/61 on the 08-19 graveyard day)** with residuals decomposed, and authsrv now ships the SHADOW telemetry ON (`agtrack_guard`/`agtrack_repin` rows, fused, `--no-agtrack-shadow`). **And the ACTIVE arm is LIVE the same night (§1z-s.5, owner's direction: "movement code that works")**: the derived re-pin ships ON by default — one 0x002C at the client's own fresh report whenever the next snap-test evaluation is predicted to fail, additive (no grant suppressed or held), `--no-agtrack-repin` to restore the old wire exactly. The next ordinary session is the arm's first live scoring, at zero operator cost. **The CLICK path moved 2026-09-03 late (`3e10438`, merge of `7475b86`; `studies/movecode/FINDINGS.md` §1z-v): the router is the DEFAULT click policy** -- §1z-u's derived answer built (`--no-router` reverts; the click-leg record re-armed to the routed leg, `--router-raw-leg`; the verbatim field 4 from the mesh under the modelled sync copy, `--router-report-plane`; a press or a follow abandons a live chain), and the operator's 40 `geo-stale` refusals retrodict to 40 answered (`studies/movecode/review/clickretro.py`). `test_router` 73 -> 103. **§1z-w the same night (`8fe6341`, merge of `b351edb`): the routing origin's own plane word (same revert as the sync-copy word) and a cast abandons a live chain; `test_router` -> 114.** **§1z-x (`30ae986`, merge of `fa689a1`): the ENSLAVEMENT DETECTOR in `w0score.py` -- the drawn body's target vs server-chosen grants, joined to the gamesrv capture; RUN-1zT's registered arm reads ENSLAVED (115 of 193, onset 17.77 s tap-clock) and its confirmation is WITHDRAWN by its own scorer; the baseline reads FREE; `test_w0score` new (38, floor 35).** **§1z-y (`9959139`, merge of `57225c0`): a rate-refused heading is HELD and re-baked at the floor (live under the shipped default; `--no-kbd-hold`), and an in-flight keyboard lead is KILLED on a press or a click by a zero-lead GRANT at the modelled body, not a 0x002C (Clear closes the fence; `--no-kbd-lead-kill`) -- 1z-u.5 item (a) built; (b) and (d) remain before the lead returns; `test_kbdsync` 33 -> 60.** **§1z-z (`3914637`, merge of `3320c07`): item (b) -- the keyboard lead grant's field 4 matched to field 3 (`--no-kbd-matched-plane`), the stop echo already matched by construction, the zero-lead default's F1 lag pinned unchanged; only (d), the fence-shutter audit, remains before the lead returns; `test_kbdsync` -> 69.** **§1z-aa (`bc31f85`, merge of `a15e548`): the FENCE-SHUTTER AUDIT -- measured on the movetap corpus, every server 0x002C shuts AgTrack's fence (12/12), the fence re-arms only at a keyboard walk-start (7/8; a stop 0/4), and a lead is never sent into the window (`KBD_LEAD_FENCE_GATE`, `--no-kbd-lead-fence-gate`); the mirror's stop re-arm is CONTESTED and recorded. All four of 1z-u.5's gates stand; the lead's return waits on the length argument and one scored run; `test_kbdsync` -> 84.** **§1z-ab (`a0e5da4`, merge of `415dab4`, 2026-09-03): the LEAD'S LENGTH argued -- the maturation margin is void under the hold (a lead's copy is outside the reprieve tube by construction, so every evaluation on it is gate 1, and a dropped re-aim snapped at the next grant's evaluation whatever the length), 520 stands one tap sample over the trigger's measured 517.5 u ceiling, 766 is refuted as a margin and costs 246 u of order-walk; 28 silent walks in the server logs are §0.11's lock readable without a tape; `toolkit/clientscan/leadmargin.py` + `test_leadmargin` (25, floor 24). The lead's return waits on one scored `--kbd-lead` run alone, with `--resync` off.** **§1z-ac (`0766c7b`, merge of `621094e`, 2026-09-03): that run RAN as RUN-1zAB and is INCONCLUSIVE — p50 1.0 u and per-leg travel scaling with hold, but the enslavement detector read MIXED, and 44 of its 50 flagged samples were its OWN co-directional-lead blind spot (our 520 u lead lands 0.53 u from the client's own target, by construction, because 1z-t.6 derived the length from the client's own report chord). CLOSED: enslavement is now the two world targets being BIT-IDENTICAL, which is what a fence-shut grant writes — RUN-1zT stays ENSLAVED 113/114, the baseline FREE, this run 2.2% with seven of eight legs FREE. The residual six are the lead MATURING at the report boundary (520/speed is within 0.01 s of the report gap in all three families), costing ~26 u and one sample of stall with NO lock: every release reported, no 0x002C all run, max separation 155.6 u. `--kbd-lead` stays OPT-IN and the length is not tuned; `test_w0score` 38 → 45.** **§1z-ad (`f4becab`, merge of `1e07a74`, 2026-09-03) — THE RERUN REFUTES.** Same script, prediction registered first: **ENSLAVED 48.3%** (29 of 60) and **five of eight legs parked with a held key**, one reported stop for seven key legs against run 1's seven. The door, to the second: a 520 u backpedal lead **matured 0.26 s BEFORE the player released** (matures 19.54 s, release 19.80 s), the `0x0047` was swallowed, the next report came back at our lead's endpoint exactly, and the client stayed locked for five legs while still reporting `mt` 7/8/4 — REALFIX §0.11 stage 2 verbatim. **No gate covers it**: the fence gate acts only on a fence WE shut, and the hold and kill had zero exposure. §1z-ac's “~26 u and no lock” was n = 1 and is corrected — the park and the lock are the same event. §1z-ab.2 is CONTESTED for this path but **766 is not adopted**; the derived object is that **a lead must never be left to mature**. `--kbd-lead` stays OPT-IN and OFF; no code changed.** **§1z-ae/§1z-af (`a4e51ae`, 2026-09-03): the REFRESH-BEFORE-MATURATION fix was built and then REFUTED BY ITS OWN TWO VERIFICATION RUNS.** At ETA − 2 ticks the server pushed the leg's own destination a lead further along its ray (the first draft aimed from the MODEL and `test_d1lead`'s clip census caught it — `--heading-grant`'s graveyard). Both runs LOCKED: MIXED 24.3 % with two parked held-key legs, then ENSLAVED 31.4 % with three, three reported stops of seven key legs in each, and the second carried a **`refresh-late`** — an arrival won its race in spite of the backstop. So preventing the arrival does NOT prevent the lock: §1z-ae.1's armer account is refuted as SUFFICIENT and, with §1z-z having killed §0.11's plane route, **the keyboard armer is UNIDENTIFIED**. `KBD_LEAD_REFRESH` is OPT-IN and OFF by §29's rule (`--kbd-lead-refresh`); the code and its 22 checks stay as the instrument. Four scored `--kbd-lead` runs now exist, three locked, and n = 2 either side does not separate the arms. **§1z-ag (`b14bcde`, merge of `8f8c655`, 2026-09-03) CLOSED that gap and IDENTIFIED THE ARMER: the lead's own ARRIVAL.** In the client's own memory, two consecutive samples — the sync copy walks the granted lead while the drawn body is PARKED (`async_vel_raw` = 0, so not the `+0x78` sample-and-hold trap), separation grows 347 → 518 u past gate 1's 299.33, the arrival fires, and the body's point is written **520 u exactly onto our granted destination** while `clientControlled` clears and never re-arms — with **no player `0x0029` or `0x002C` within ±1.5 s**. A second capture is a within-arm control that did NOT lock (7 reported stops of 7 key legs against 1): its only shut had no arrival armed, 96.8 u of separation, and re-armed 3.8 s later, so the plane shut self-heals and the arrival shut does not. §1z-af.3 is corrected — the refresh's COVERAGE was incomplete and its SHAPE was wrong, because **the quantity that kills is the separation at the arrival, not its timing**. The guard has the predicate; **1z-ah.2 CORRECTS the reading that it did not fire in time** — it reported `arrival-risk` at t=18.074, **0.425 s BEFORE** the 18.499 arrival, and was refused by the report-freshness gate alone (last accepted report 2.311 s old against a 0.347 s ceiling, zero refusals since, previous re-pin 6.1 s back). **MOVECODE-1z-ah, 2026-09-03, `632b3c1` — THE RETRACT IS BUILT, and it is the `0x002C`, not the grant 1z-ag.5 named.** Adjudicated against the mirror: a `0x0029` retract SNAPS at its own bake-tail wherever separation is already RED (520 u and 378.7 u both snap, 227.2 u is safe) — 1z-s.1 clause 3 on this exact leg — and its safe window closes at t0+1.05 s while the arrival is at t0+2.735 s, with no trigger aimable at the gap (a separation one fires on every cruise chord; a timing one has only 1z-ae.1's 8 u / 0.03 s photo finish, narrower than a tick). The freshness gate cannot be opened on AGE — a `0x002C` SetPositions BOTH copies (`AgMsg.cpp` 579 and 584) and this repo already shipped that warp once (630, 189 and 765 u). **The discriminator is that two accepted reports agreeing to within the client's own `ZERO_DIST_SQ` are a MEASUREMENT that the body is still**, so the re-pin's harm bound is 1.0 u rather than `RUN_SPEED × age`; a walking body (reports ~512 u apart) can never satisfy it, and run A's parked body reported the same point BIT-IDENTICAL three times. On that leg the re-pin becomes DUE, lands on the body for a measured **0.000 u** of harm, and clears `+0x48` and `dest` — **the 520 u arrival never matures**; the known-bad walking arm never even gets a re-pin proposed. A `0x002C` now also clears the keyboard leg record, and the row NAMES its blocker. `STATIONARY_WAIVER` ON, `--no-repin-stationary-waiver` reverts; `test_agtrack_guard` 49 → 71. Residual, stated: the retract shuts the fence — a bounded window (already the shipped RE-PIN's behaviour, and 1z-aa's gate covers it) traded against a permanent lock. The registered prediction and its REFUTED-IF are 1z-ah.7. **RAN 2026-09-03 as RUN-1zAH, four runs (MOVECODE-1z-ai, `0b2cc27`): MECHANISM CONFIRMED — four retracts fired, every one at `prev_d` 0.0 u AND `next_d` 0.0 u (the next report landed on the pinned point), zero violations in four runs and across the 1,262-capture corpus, and it refused correctly live where the body had moved. OUTCOME **REFUTED** by the sheet's own clause: arm T's second run fired a retract and still had a held-key leg move 0 u — though that leg carried a ZERO-LENGTH lead with no `arrival-risk` row at all and follows the `gate2-offmesh` re-pin firing at ≈11.9 s in all four runs, so the clause caught a different defect than it was written for. The PERSISTENT lock (1 stop of 7, no re-arm) reproduced in arm C only, never in arm T. AND THE FLOOR COUNTED THE WRONG THING: only **2–4 leads per run** survive `a2_clip_lead` at full 520 u (10–15 are `origin-unwalkable`), so the run had a quarter of the exposure it claimed. `--kbd-lead` stays OFF, the waiver stays ON. **RERUN 2026-09-03 as RUN-1zAJ (MOVECODE-1z-aj, `7034403`) with the floor and the route repaired: the floor now counts leads that SURVIVE `a2_clip_lead` and is MET 4/4 — clear leads **2-4 → 9-14**, exactly the 8-12 `leadroute.py` predicted from the mesh at the desk, with an oscillating script staying inside 300 u of spawn where 0 % of origins are off mesh. Seven more retracts, all `prev_d` 0.0 u, **11 total with zero violations**. But INCONCLUSIVE, as that sheet registered in advance: all four runs healthy (12 stop-echoes for 13 legs) and **the control never locked**. The reason is structural and was derived before the run — a CLEAR lead means nothing stops the body for 520 u, so it reaches its 512 u trigger and re-aims; **the geometry that makes a lead full-length is the geometry that stops it maturing**. Next: CAUSE the parking (the enemy's collision), do not wait for it.** Withdrawn: “§1z-z removes the cross-plane state”. Instrument debt: both captures failed `movetap`'s own 50 Hz floor (10.2 / 12.0 Hz) under the harness, reproducibly.** **§1z-ak (2026-09-04): the OTHER `0x002C` sender is settled and needs no bound.** RUN-1zAH's sweep had incidentally flagged `PRESS ENDS THE WALK` pins carrying reports up to **13.5 s** stale with the last two reports 12.7 u apart; `repincheck.py` scoped them out, and the scoping is now **checked rather than assumed**. That arm never sends the report — its payload is `_click_leg_start`'s **model** of the body and it calls `_forget_client_position` in the same breath, so the five "stale" pins fire **446–568 u from the report whose age is scored**. The quantity that matters, `|pin − the DRAWN body|`, was measured on the one capture carrying both press pins and an `agenttap` tape (`authsrv-20260903T084616-c1`), through the client's own `position_at`: **10 of 10 pins, nine at 0.0 u, worst 6.9 u** against `R_MATCH` = 100 u — the stale five at **0.0 u every one**, and the lone moving case 6.9 u **ahead** of a 289 u/s body that reached the pin 30 ms later. **No pin moved the body backward; no bound, no flag, no code change.** Instrument `studies/movecode/review/pressharm.py` (exits 1 on zero exposure). **§1z-ak.6 (2026-09-04) FILLS the bent cell, by derivation:** all 37 of that session's click chords clip **clean** (0 bent) and at its click lengths **0 of 496** origin/heading pairs are bent, so §1z-ak measured a regime with **zero bent exposure**. Where a path IS bent the model lerps the chord while the body walks the route, running **ahead** on the shorter path: even at bow < 1.25 the residual reaches **164.9 u with 19 of 135 past `R_MATCH`** (control: 60 clear chords at 0.000 u). **But that is the RAW-CHORD regime** — the capture ran `ROUTER: False`, and under the shipped default `ROUTER_LEG_REARM` re-aims the record at the ROUTED leg, so the bow term is gone by construction. §1z-ak's verdict stands; the bow is a stated cost of `--no-router` / `--router-raw-leg`, now recorded at the flag. `studies/movecode/review/bentbound.py`. **§1z-ak.7 (2026-09-04) closes the other loose end — the 140659 pins, which have no tape.** A `0x002C` is **self-fulfilling** (it SetPositions both copies), so the wire can NEVER audit its own pin and `next_d` is context by construction. But two origins are PROVABLE — pin 1's leg starts at the spawn (the session's first movement command is its own click) and pin 2's at pin 1's own point — and both reproduce the emitted payload exactly. On a clear chord from an exact origin `|model − body| ≤ 288·dt`, which hits `R_MATCH` at **dt = 100/288 = 0.347 s = `REPIN_MAX_REPORT_AGE`**, the re-pin's own constant on the LEG clock: **the arm was never unbounded.** All 7 chords clear; pins 1-3 CLEARED (≤ 90.8 / 86.1 / 67.5 u), pin 4 **UNCERTIFIED** (≤ 312.2 u, leg 1.084 s old) — not harmed, and §39.6 has the operator's no-jump verdict on it. Instrument debt: the tape is **9.1 Hz effective**, ~31 u/sample, so the click start transient is NOT resolvable and none is published; §1z-ak.3's moving specimen reads “within a sample” rather than 6.9 u exactly, the nine parked readings unaffected. `pressharm.py` gained the tape-free arm and exits non-zero on an uncertified pin. **§1z-al (2026-09-04) REFUTES §1z-aj.5's nominated next step at the desk:** the enemy's collision cannot park a keyboard body, because the resolver's stop arm is gated on the blocker being `+0x98` (`0x006017CB`) and a walking player's `+0x98` is **0 in 3,032 of 3,032 moving samples** — **636 (21%) of them INSIDE the 80 u disc**, closest pass **4.8 u at 190 u/s** undeflected. **And the lead's own `0x0029` clears `+0x98`** (`0x005FD890` writes 0 where `0x002A` writes the target), so a maturing lead and an enemy-parked body are mutually exclusive BY CONSTRUCTION. Positive control: the Hatcher, which does carry `+0x98` (25.8%), halts at p50 **84.5 u** with 62% inside the 60-100 u band — the resolver fires for the agent that names a target and never for the one that does not. A near-miss recorded: 29 player stalls cluster at ~75 u and look like the disc, but `+0x98` is 0 before each — they are the HATCHER's own chase-halt seen from the player's frame. Left, unchosen: a mesh/collision DISAGREEMENT, or §1z-ad's swallowed `0x0047`. `studies/movecode/review/collisionpark.py`. **§1z-am (2026-09-04) takes the second:** the swallow is real at FRAME level (`0x8047` ×1 against seven key legs; no Undecodable, no refusal), the right denominator is the KEY LEG not the message (A/D turn in place and never report a stop; W/S only reads **76% lead-ON vs 92% lead-absent**), and the signature is **TERMINAL, not a rate** — trailing silence ≥ 2 in **6 of 17 lead runs and 0 of 32 without**, a lock detector that needs **no tape**. **And the registered test REFUTED §1z-ad's cause:** six HEALTHY runs carry a lead maturing before its release and one LOCKED run carries none, so maturation is neither necessary nor sufficient — REALFIX §0.11's two-stage account is untouched, §1z-ad's "the door" framing is not. `fence-shut` correlates almost perfectly and is CIRCULAR (our own flag, uncleared because the reports stopped). Next: the fence dword on `agenttap`, or the client's send-only `0x0047` sender — neither is a run. `studies/movecode/review/stopcensus.py`. **§1z-an (2026-09-04) BUILDS the cheap half of that next step: the AgTrack fence dword is now a column on `agenttap`** (`--no-fence` reverts) — `movetap.agtrack_fence` CALLED not copied, so `movetap --selftest` still owns the offsets; a per-sample read memo, because the header is per-AgTrack and this reader already delivers ~9 Hz of the 30 it asks for; the SYNC block handed over, world 0 being where the test is reached; and a FREE NEGATIVE CONTROL — only the local player's agent is client-controlled (`0x00605F10`, two local-command callers), so the Hatcher must read `shut` all run and the summary goes RED if it does not. `test_agenttap.py` 15 (floor 15, bare machine) caught the success path still returning a bare dict and a guessed floor. **RAN THE SAME DAY as RUN-1zAN (§1z-an.6): ALL FOUR registered clauses CONFIRMED** — the Hatcher negative control reads `shut` on **680 of 680** samples while the player reads `open` on 581 (same reader, same array, one index apart), **zero `unread:`**, three fence transitions, and **10.73 Hz against the fence-less 9.1** so the rate cost is nil. **And the WIRE corroborates it to one sample:** the run's only `0x002C` at tape t 21.40 → fence shut 21.44; the only walk-start `0x003D` at 23.97 → fence re-open 23.91; the server's own `shut_for` 2.569 s against the tape's 2.47 s — **§1z-aa's fence-shutter rule confirmed from the client's memory for the `AGTRACK RE-PIN` sender, which §1z-aa could not test.** The run is HEALTHY (`YYYYYYYY.YYYY`) and carries no evidence about the lock, as the sheet pre-registered. **RUN-1zAO THEN CAUGHT ONE (§1z-ao): four arm-C runs on the `WSWQESW` script, run 4 LOCKED (`Y......`) with a valid tape** — all three registered clauses confirmed, and **the mechanism observed whole in the client's memory**: the drawn body sat at v = 0.0 for 3.0 s under a held key while the sync copy walked the 520 u lead, separation crossed gate 1 at 16.53 and reached **502 u**, and at 17.67 the arrival **teleported the body 520 u onto the granted point and shut the fence in the same sample, with NO `0x002C` involved** — REALFIX §0.11 stage 1 read directly for the first time. **THE DISCRIMINATOR IS WHAT SHUT IT, both kinds in one run:** a `0x002C`-shut fence RE-ARMED at the next walk-start (10.91 → 14.74, bounded 3.8 s); the SNAP-shut fence NEVER re-armed, through six subsequent `0x003D` walk-starts — so the client keeps reporting walk-starts while the fence stays shut, which sharpens §0.11 stage 2. §1z-am's refutation RESOLVES: maturation must produce a SNAP, which needs the parked body (§1z-ag's separation-at-arrival). **And the parking is a PLANE-BLIND CLIP** — the fatal lead runs plane 29 → plane 0 and `pm.clip` takes no plane argument, so a cross-seam ray scored CLEAR at full 520 u and the client would not walk it (§1z-al.5 candidate (a), RECONSTRUCTION). **AND §1z-ap FIXES IT the same day** (`A2_LEAD_PLANE_CLIP`, `--no-lead-plane-clip` reverts): `pm.clip` gains a `plane=`, `a2_clip_lead` takes it from `plane_at(prefer=` the REPORT's own plane word, `plane_at` returning None refuses to guess and disables the term, and the row NAMES the door with a new `why="plane-seam"`. RUN-1zAO's fatal lead goes **520 u `clear` → 14 u `plane-seam`**, under gate 1 so the arming event is unreachable. **RETRODICTS 6 of 6 locked runs below gate 1** (520 → 2-146 u, every one a plane-29 origin; the 7th had no lead armed on its silent leg, the same odd-one-out §1z-am found). Over 464 leads it changes **36 (7.8%)**, all `plane-seam`, the rest bit-identical. `test_d1lead` 94 → **104** with the KNOWN-BAD ARM driven first. **The ROUTER's clip is untouched** (§1z-o and §1z-v have arms there — its own section). **RUN-1zAQ then RAN IT (§1z-aq): the mechanism is CONFIRMED LIVE** — four runs alternating the flag, **0 of 65 arm-A leads cross a seam at gate 1 against 4 of 62 in the known-bad arm**, those four at the full 520 u reading `clear` (two 29→0, two 0→29, so both directions), and arm A's max reach still 520 u with only 3 of 65 clipped — healthy grants unperturbed in front of a client. All four tapes' Hatcher controls `shut` 100%. **But NO LOCK IN EITHER ARM (0/2, 0/2), so the OUTCOME is still open** and “arm A did not lock” must not be read as the fix working — pre-registered as weak, since 1-in-4 expects 0.5 locks in two runs. **§1z-ar then took up the ROUTER's clip and shipped NOTHING:** it is plane-blind for CERTAIN (`_visible` → `_sightline` answers exactly plane-blind `clip`, and `route()`'s gate too, so the pull can undo the A*'s plane discipline), but whether it ever fires is UNMEASURED — three desk instruments, the last **refuted by its own positive control** (it found only **31%** of the portals `_cross` asserts). The blocker: **portal-linked trapezoids do NOT reliably overlap in 2D**, so the legitimacy question cannot be answered by sampling a segment. No observed harm either — the router has no tape-covered grants, the campaign being keyboard-only. The plane-blindness is now NAMED at `_visible` instead. Settling it needs a CLICK run with a tape, which needs a click script. **§1z-as WROTE AND CALIBRATED THAT SCRIPT** — the `click:` verb does reach the world (13 of 14 legs produced a `MOVE_TO_COORD`), the camera is **12.5 px per degree** (confirmed predictively: `yaw:1500` → a 240.0° bearing), and `fy` 0.46 ≈ 420-620 u though range is terrain-dependent. **But the owner, watching, named the limit: PROPS SWALLOW CLICKS** — a click on the bridge prop walks the body STRAIGHT AT IT rather than routing, and since we carry no prop geometry the mesh is the sensor (2 GROUND / 5 prop-void, agreeing 7 of 7 with the router's own verdicts). **THE BIND: map 146's only click-reachable route-forcing bearings ARE the bridge**, so a blind click there lands on the prop — zero routed multi-waypoint paths under any tape, and the router probe stays undeliverable. Ways out: **one owner-aimed click** past the bridge with a tape running, or a map whose obstacles are terrain rather than props. **§1z-at took the second and it answered differently: THE MAP WAS NEVER WRONG.** `mapscout.py` ranks map 146 FIRST (17-20% route-forcing, 87-89% terrain-shaped) — §1z-as had scanned bearings from the SPAWN only and generalised one origin to a map; the spawn merely sits beside a bridge, and the nearest terrain obstacle is **2,827 u on foot**. **And the walk script is now DERIVED FROM THE MESH and navigates to 16 u** of a computed target (`--script`: the mesh's route as yaw+W legs on the 12.5 px/deg calibration), which validates that the calibration composes, that W follows the camera, and that the harness can be sent to a coordinate. **What remains is blind click targeting ACROSS an obstacle**: 4 clicks ranged 511-1767 u, the near one landing 75 u SHORT inside the obstacle's hole and the one GROUND hit refused `no-path-or-gate`. Zero routed paths under any tape still; the missing piece is the one judgement a screen fraction cannot encode. **§1z-au → §1z-ba (2026-09-04) — THE ROUTER'S PLANE-BLINDNESS IS NOW OBSERVED HARM, TWICE.** (These six sections merged to `main` without this row being stamped; recorded here in one pass.) §1z-au read the scene: the "terrain" obstacle was the CITY WALL. §1z-av's water hunt corrected §1z-at's ranking and was itself corrected by §1z-az: open country has plenty of route-forcing geometry — the scan had sat at the map's clearance peak. §1z-aw fitted a camera and was REFUTED by its own hold-out (205 u mean, non-monotone in `fy`); §1z-ax READ the camera instead (`fovread`'s Position/Target/fov) and §1z-ay validated it live — bearing to **1.02°**, `fov` **75.000°** on the click's own clock — while its vertical half failed; §1z-az's aimed click produced **the first `routed` grant under a tape** (bearing right, range long), crossing no seam. **§1z-ba (`514791c`…): `seamscout.py`'s census — portal links are a CLUSTER relation carried by ZERO-HEIGHT LINE trapezoids and a seam is DIRECTIONAL (the plane a body is ON must end); map 146 has 195 blind seams, controls 168/168 and 99% — targeted the stone bridge into Ascalon City (plane 18, ~155 u above the shore, railed). RUN-1zBA, four runs: a router `clip-fallback` grant off the deck's railed west edge left the drawn body PARKED at x = 10860.0 with velocity 0 for 7.1 s and 7.5 s while the sync copy walked 2 km, then a 2,021 u teleport at the leg's ETA and the fence shut — RUN-1zAO's signature on a ROUTER grant, seen by the operator ("straight line towards the edge, stopped, seconds later warped"); 12 of 12 portal / seam-free legs WALKED.** Both specimens are the clip FALLBACK; the pull's own is out of reach from a railed deck, but the pull's sightline is the same `clip()` primitive. `clickaim`'s vertical sign was inverted (the world is z-DOWN) and is fixed — §1z-ay's P2 explained. Run 1 failed for the mechanism itself: the walk-in planner was the plane-blind pull, and the body was blocked at the deck edge under the keyboard. **§1z-bb (2026-09-04, `5ccdbeb`) — SHIPPED, default ON, `--router-blind-clip` reverts:** `pathmap.planes_at` / `portal_at` / `seam_clip` (a body's plane may end only at a portal; the 1 u tolerance sees the zero-height portal lines), wired into `route()`'s pull (at the sightline's 16 u, off-mesh-tolerant — a strict 2 u walk there refused 35 of 300 seam-free paths and blew the tick) and gate, and into `authsrv._router_clip` for the leg gate and the clip fallback — one flag, both rays. Chase band: p50 0.51 → 0.85 ms, max 27.6, 0 of 1,500 over the tick; 4 of 300 paths change, 3 for a blind crossing; 0 seam-aware routes cross one. **A latent bug fixed on the way: `with_planes` reported the FIRST of coincident portal waypoints' planes (value-matching); the pull now records its indices.** `test_pathmap` §14 (floor 89) and `test_router` §6 (floor 121). **RUN-1zBB, the A/B on RUN-1zBA's own click: fix arm — fallback stop (10862, 5190), 136 u, body WALKED, fence untouched; known-bad arm — 2,158 u, PARKED 7.5 s, 2,021 u teleport, fence shut.** Filed: one benign unexplained path change in 300. **§1z-bc (2026-09-04): the lead's clip STAYS as 1z-ap built it — the seam test is REFUTED for the lead by its own retrodiction.** `leadretro.py` replayed the campaign's 622 keyboard leads: the seam ray is never shorter than the plane ray and 54 times longer, 33 of those past gate 1 — **including all six fatal leads of the six measured locks (RUN-1zAO's (10373,8286): 14 u → 520 u). 0 of 6 kept under the gate.** At both ends of the spawn-side bridge the seam the body would not walk is portal-linked in the file (plane 29's portal is the BODY trapezoid `p29#0` along its whole slanted edge, not a line as on plane 18), so "linked" ≠ "crossable here", at a measured 1-in-4 lock rate per crossing. `A2_LEAD_SEAM_CLIP` ships **OFF**, `--lead-seam-clip` opt-in (the known-bad arm of the open question: why the client refuses a linked portal — declared plane at a wedge tip / prop / a narrower ramp). Corrects §1z-ar.6 ("the portal was not on that ray" — it was, in the file) and §1z-bb.6. `test_d1lead` §2f (floor 110). The router rides the same portals through its corridor and always has — filed. **§1z-bd (2026-09-04): the `MapFindPath` return tap on a lead run, two runs, three captures each.** The keyboard mover **never calls `MapFindPath`** (0 of ~880 step commands; the 2 calls were snaptest's gate 2) — R7's class is not the lead's park. **The portal IS crossable** (run 1 walked RUN-1zAO's exact fatal lead at 190 u/s): §1z-bc's "the body walked none of them" is corrected. **The park is the client's keyboard mover stalling at the wedge tip** — it re-targets the tip vertex 35× at 16 ms from −4.46 s, its report is stationary at −3.87, and our `gate2-offmesh` re-pin follows at −3.72: downstream. At the S press both clients issue the same `movecmd → movedispatch → chcli_dir → agapi_setdest` with the first quarterstep ON the seam line; run 1 fires `chcli_advance` 47 ms later and walks, run 2 never advances and stands 4 s with the fence open and identical `resume_fire` gate words. Our part is only the warp when a full-length lead matures during the stall — §1z-ap's clip keeps it shut. One R7-class warp seen: a lead carried plane 29 across the NE portal onto plane-0 ground, gate 2 asked, `pathCount 0`, `reseed`. NEXT: decode `chcli_advance`'s guard (client-side); the lead's plane word across a portal. Tools `leadtap.py`, `tapdrive.py`. Entry point for all movement work: `studies/movement/HANDOFF.md`. **§1z-be (2026-09-04): `chcli_advance`'s guard decoded — the client sent notify 4 (agent-avoidance, the follower in the 60° cone), not notify 5; §1z-bd.2's wedge-tip stall is refuted: our `0x002C` install halted a walking body, then the held key never re-dispatched. Guard fix filed with the plane-channel fix.** **§1z-bf (2026-09-04): the guard fix SHIPPED — gate 2 reads `on_mesh(a, SEAM_TOL)`, not exact containment; 19 → 0 false vetoes on the 66 controllable runs with the control exact; `--agtrack-gate2-exact` reverts.** **§1z-bg (2026-09-04): the lead's origin test SHIPPED — a report within `SEAM_TOL` with a nameable plane is an origin and takes the plane clip; 148 of 148 refusals retrodict to leads, none across the seam, the six fatal leads untouched; `--lead-origin-exact` reverts.** **2026-09-05, `MOVECODE-1z-bh` (review step 1): the law's retail clause corrected (retail reports on the same 512 u trigger; its copy walks the lead; the lead-OFF default sits ~515 u behind a moving body), the inert lead-path arms named in the banner, the keyboard drop given its revert arm, `w0score` given a moving-only line; no default moved.** **`MOVECODE-1z-bi` (review step 2, desk): the lead's conviction replayed through the fixed guard — 5 of 7 locks begin with OUR gate-2 `0x002C` halting the body under a held W and `GATE2_SEAM_TOL` removes it 14/14; the chain is exposure (~4/7), not a verdict; the two Q-leg locks are the plane clip's class; next: ONE `--kbd-lead` run under HEAD checking the chain's first link (§1z-bi.6).** **`MOVECODE-1z-bj` (RUN-1zBI, one launch): with `--kbd-lead` under the shipped guard, 0 gate-2 vetoes in 38, moving-only separation p50 26 u (retail ~74), body FREE, no lock; one W hold dead 5.0 s — a 106 u seam-clipped lead refused by the client's avoidance pass with the follower parked in the walk direction (RECONSTRUCTION). Next: `--no-enemy` arm, movehook at the avoidance exit, the combined radius read live; the lead's return is the owner's ruling.** **`MOVECODE-1z-bk` (RUN-1zBK, `--no-enemy`): §1z-bj's follower reconstruction confirmed (no dead hold without the follower; the 494 u seam lead walks). New failure — after the 29→0 seam crossing the client's report froze at the far point for the last four legs (~21 s), the drawn body pinned there, our re-pins reseeding it back; `stopcensus` and `w0score` both scored it clean (review M-F2/M-F4 live). Next: the `MapFindPath` return tap on this route, and a lead-OFF `--no-enemy` run.** **`MOVECODE-1z-bl` (RUN-1zBL, the hook on the stall): THE STALL IS OURS — `MapFindPath` 0 hits (not a client path refusal); the body walks the held key 308–443 u and our AGTRACK re-pin throws it back to the leg's start, killing the held key. Trigger = report silence (9/9 silent legs re-pinned vs 1/12 reporting); 8 bodies thrown back 294–433 u; every instrument scored it clean (review M-F2/M-F4 live). §1z-bk's client-side attribution REFUTED. Fix derived and retrodicted (removes 24 of 62 fires, all budget-red), NOT built.** Panel (§1z-bl.8): headline confirmed by 4 lanes + 2 refuters and corroborated by the client's CAMERA target; the source defect localised (`stationary()`'s waiver, whose own comment says its counterexample cannot exist, fires on every leg's opening report pair); corrections — `movecmd` counts grants not key edges, the one-shot regime is any leg's first ballistic segment (not our lead), the re-pin is sufficient but not proven necessary, leg 1W's re-pin was refused by a startup accident, rewind 311–468 u. **`MOVECODE-1z-bm` (RUN-1zBM, the lead-OFF control): the re-pin is NECESSARY as well as sufficient — 7 of 7 legs opened with the same 410–514 u silent glide the lead-ON runs were rewound inside, and with no re-pin nothing was thrown back. The client's opening waypoint is identical lead-on/lead-off, so the glide is the client's reach, not our lead. Lead OFF: copy p50 252 u behind, never rewound. Lead ON: p50 26 u, 3 of 4 re-pinned legs rewound 298–433 u. Q13 now has a precondition — fix `stationary()`'s waiver and the lead can return.** **`MOVECODE-1z-bn` — THE FIX, BUILT AND SHIPPED ON (2026-09-05): the waiver's WALK-START CLAUSE.** `stationary()` waives the 0.347 s freshness gate whenever the last two accepted reports coincide, and the pair it fires on almost every time is `{0x0047 stop → 0x003D walk-start}` — a leg's opening report, 0.000 u from the previous leg's stop only because the body has not moved *yet*. The corpus splits totally by that order: harm p50 **366.6 u** (18 of 19 over 100 u) against **0.0 u** for both other orderings, so the clause does not overrule the waiver, it restores the waiver's own stated bound. Retrodicted by `studies/movecode/review/waiverretro.py` over 68 control-OK runs and 56 real `0x002C` fires: removes **10 of 10** reproduced `arrival-risk` and **4 of 4** `budget-red`, **0 of 9** `gate2-offmesh`; 68 due-transitions dropped and **0 newly raised**, all 68 on the named pair and all 68 stale. Estimated rewind removed p50 **375 u**, inside §1z-bl's tape-measured 311–468 u from an instrument sharing no sampler. `--waiver-walkstart-stands` reverts; `test_agtrack_guard.py` §14, floor 77 → 97. **What is NOT established: this is a retrodiction and a unit test, and the lead-ON run under the fix has not happened.** **`MOVECODE-1z-bo` (RUN-1zBO, 2026-09-05): THE LEAD-ON RUN UNDER THE FIX — the rewind is gone and the tracking held.** All five pre-registered predictions MET, three adversaries failed to refute. Zero `0x002C` in the whole 87.3 s (1zBL: 4); the client's `setposition` site **0 hits** against 8; **0 of 7** legs report the same point at walk-start and stop (1zBL 3 of 7 at exactly 0.0 u); largest backward step **0.0 u on both copies** over 964 samples (1zBL −449.7 / −452.6 u); moving-only separation **13.0 u** (1zBL 31.2, lead-off 1zBM 251.6). The guard was refused **seven** times, every one `blocked_by: stale-report`, against 1zBL's 4 fires — so the zero is not the situation failing to arise, and the lead was strictly STRONGER than the unfixed arm's (13 non-zero leads, p90 422 u, against 8 / 294 u). **Three limits, and they are larger than the result: only ONE of the four removed re-pins is a state-matched trial** (legs 3–7 start 503–714 u apart because 1zBL's leg 2 was rewound); **`gate2-offmesh` had zero exposure**, untested not confirmed; and **nothing separates the shipped clause from deleting the stationary waiver** — they differ in zero of 71 control-OK runs, so §1z-bn.5's "strictly narrower" is true as code and unwitnessed as behaviour. **Two defects in §1z-bn found and corrected:** `waiverretro` replayed every capture at the pre-§1z-bf tolerance and thereby excluded RUN-1zBL — the very run the clause is A/B'd against — from its own evidence population (table re-published); and the moving-only 26.3 u attributed to RUN-1zBL in five places is RUN-1zBI's tape, 1zBL's own 31.2 u having never been published. **`MOVECODE-1z-bp` (RUN-1zBP, the revert arm, same day): the control this arc never had.** Same binary, same route, `--waiver-walkstart-stands` the only flag different (the two captures' whole flags dicts differ in that one key): the re-pin fires **3** times against 0, the client's `setposition` takes **6** hits against 0 (3 sends × 2 world copies), **3 of 7** legs are thrown back against 0, the body goes **−432.2 / −432.4 u** backward on both copies against 0.0 — and three decision points matched to **0.01–0.02 s** flip `blocked/stale-report` → `due`. **§1z-bo.4's "only one state-matched trial" is repaired: three, in one build.** The instruments are now proven to discriminate on a same-build negative. **Q15 RULED 2026-09-05 — `STATIONARY_WAIVER` DELETED** (MOVECODE-1z-bt, [§1z-bt](studies/movecode/FINDINGS.md); 1z-bs first closed the click path at desk and found the kept branch splits by ordering — still in 151 of 151 windows when the newest report is a stop, walking in 14 of 87 when it is a walk-start). **Q13 RULED 2026-09-05 — the keyboard lead ON by default** (MOVECODE-1z-bu, [§1z-bu](studies/movecode/FINDINGS.md); the shipped default is RUN-1zBO's arm, `--no-kbd-lead` reverts; applied to `KBD_SYNC_LEAD_ON`, the lead the runs measured, with the `D1_LEAD`-versus-keyboard-lead assumption stated in Q13). **RUN-1zBW RAN 2026-09-05 21:31 — the operator: "felt good"** (MOVECODE-1z-bw/1z-bx, [§1z-bw](studies/movecode/FINDINGS.md)); the fence gate's unbounded latch found and bounded, the 13.0 u comparator corrected to ~2.2×, `agenttap` given its plane column. **`gate2-offmesh` CLOSED 2026-09-05** (MOVECODE-1z-bv, [§1z-bv](studies/movecode/FINDINGS.md)): the deletion could not have removed one — all 17 fires were fresh and non-coincident, all 25 waiver-carried fires are `arrival-risk`/`budget-red`; the open item's "every replay used `mesh=None`" was false, the real gap was the guard's own tests, now closed (`test_agtrack_guard` §14, floor 81). Left: [RUN-1zBW](studies/movecode/RUN-1zBW.md), the operator's. |
| **R4a** | Agent model + combat core | An ettin swings at you and you die | 🔶 **half.** A hostile Hatcher stands in the map, and a click orders an attack the server drives to a kill and a revive (`6b71f42`, `12c95f5`, 2026-08-06). ~~Nothing swings back and the player cannot die~~ — **BOTH MET 2026-08-11**, which is the half the criterion actually names. A Hatcher swings at the player, the player's health falls 10 a swing, and at zero the player drops face-down with both orbs at 0 and stands back up ten seconds later. Three full death/revive cycles in one 65 s run, on the wire and on film (`vault/captures/gamesrv/authsrv-20260811T160502-c1.jsonl`, `frames-20260811T160449`). `studies/enemy/PLAN.md` §11. What is still missing is a real agent model — no AI, no pathing (the Hatcher stands where it spawned and swings when you are inside 1200 units), no resurrection shrine (the revive is a timer), and energy is not restored on revive. No agent table either — `studies/enemy/PLAN.md` §7.2. **2026-08-11: one click now drives a whole fight** — `0x0026` ATTACK_AGENT arrives (four of them at our Hatcher, zero `0x0033`, ending a year in which the client had never once sent it), the server dispatches it, seven swings at 1.77 s kill the agent, and it revives; the client drops the dead target and re-acquires the revived one unprompted (§10.9). **The first revive crashed the client** — `CharPool.cpp:84`, `fraction <= 1.0f` — because we sent `max_health` where a fraction belonged, on the one side of a `<=` bound that no damage test could ever reach. Fixed and re-verified. **2026-08-11 (earlier): the click arrives as `0x0026` ATTACK_AGENT** — four of them at our Hatcher, zero `0x0033`, ending a year in which the client had never once sent it (§10.7). The server now dispatches both arms. **2026-08-15, the combat arc ([studies/combat/PLAN.md](studies/combat/PLAN.md)):** the kill window is now ArenaNet's three messages rather than one — `0x00F1` death, `0x00EE [0, 26]` reward, `0x0026` flags 8, same tick, the reward byte-identical to the capture — and the richer-looking `0x00EE` PAIR is deliberately REFUSED, because 6 of its 7 sightings fire far from any death inside a `0x009C`-marked broadcast burst (§13). The guard contract was rebuilt red-first so a refused value costs the value and not the socket or the world tick, and **overkill now clamps to a kill instead of silently no-opping** — a bug caught before it could ship, since damage rides the wire as a fraction of max health and a decoded skill exceeding a weak target's pool would have been refused outright. The server also models attribute ranks at last: `0x003A` carries real ranks, so `2 * rank` is no longer 0 (see R4b). **And for one day that message killed the client on every spawn** — `0x003A` is COLUMN-MAJOR (`ids | ranks | ranks`, the handler slices one flat array at `n` and `2n`) and it was sent as interleaved `(id, rank, rank)` triples, which puts attribute ids in the rank column and asserts `level < arrsize(s_attribPoints)` at `CharData.cpp:202`. Fixed 2026-08-15, `studies/combat/PLAN.md` §14, diagnosed statically from the dump's own stack. `arrsize` was a number nobody had read and the one recorded was wrong — `consttable.py` had 14 x 4, it is 13 x 4, corrected with a new structural locator (`clientscan/attribpoints.py`). **CURE VERIFIED the same day** (§14g): caged loopback run, 1,716 messages, last at t=78.2 s, no assert — the payload the client used to die on now goes out at t=0.85 s and it runs on for another seventy-seven seconds. **And L6's attributability criterion is MET on the same run**: `--probe attributes` drove all three steps and the panel followed, with the ranks against the right names (see R4b). Note that two earlier instrumented runs were reported healthy while the crash box was on screen — the assert dialog is modal INSIDE the client, so liveness polling cannot see it, and the run above is watched with `crashwatch.ps1` instead. **AND THE DAMAGE IS NO LONGER OURS, 2026-08-20** (`ac08326`, `d935516`, `2baed69`): a swing was 15% of the target's max health — so every creature took the same seven swings however tough it was — and is now the equipped weapon's own range (identifier 584) scaled by `2^((SL−AR)/40)`, with criticals as an armour reduction of 20. The model is `studies/isle` rung 7's, read off 495 live damage events, and the implementation reproduces that capture's own point bands at **all six endpoints** with zero free parameters. Creature AR is DERIVED from level and profession (WIKI), after a picked 60 turned out to be level-20 armour on a level-1 creature — the wrong SHAPE, which is `studies/monsterai` §3.3's lesson for reach paid a second time. On screen and matching the wire swing for swing (`20260820T162204`, `…T162932`). ~~**Still absent: nothing reads the PLAYER's armour**~~ — **read as of `c06a783`**: incoming damage scales by `2^((60−AR)/40)` at a hit location on GWW's published 3/2/1/1/1 odds, checked against that page's own 40-row multiplier table, and the player takes 13 a swing instead of 10. It also exposed a corpse being re-killed, which a flat damage fraction had hidden by dividing evenly into the pool. **What IS still absent is sharper than what was written here**: `skill_damage` ignores armour entirely, and the enemy almost never auto-attacks — its four-slot bar is always recharged — so the armoured path barely runs in a real fight while the unarmoured one does all the damage (isle §4.2). That waits on a per-skill armour-ignoring flag, i.e. on R4b. Also still absent: no unmet-requirement term, which `studies/isle` refutes and forbids replacing. **THE CAST WIRE NOW CARRIES RETAIL'S OWN PROPERTY SHAPES, 2026-08-22** (`d1ca4d1`, `8ec8c9e`, `69c8fdd`, `525a014`; the census is [studies/castmech §3c](studies/castmech/FINDINGS.md)): `[58, agent, 0]` rides every non-attack cast end in the corpus's own slot (immediately after E5, before the damage — the "0 of 21,543" that kept it unsent was a wrong-channel count); the attack-skill press animates with property 50 not 60 (2/2 live presses, 39/39 adrenal adjacencies); a QUEUED cast pays and animates at CAST-BEGIN (E4 alone at the press, then E3 → 62 → 60 at the instant the caster frees, 2/2 — and a cast that never begins never pays, the terminated cast's own missing debit); and property 8 goes out as the view's action-hold flag, transition-only, wired only after the client handler was read (a 1/0 bit on the type-1 view object, animation plumbing — skillcast §16.2). Property 45 alone stays unsent: one corpus occurrence, nothing names it. **2026-09-02, ANIMREF-RE §40: the Hatcher's chase is retail's FOLLOW** — a `0x002A` naming the player, re-pathed every 0.5 s while they move, the server's copy parked where the client's own disc stops the body (80 u), a bare `0x0028` halt on arrival and no swing mid-follow, in place of the `0x0029`-to-the-point chase that stopped 150 u out. Default ON behind `--legacy-npc-chase`. **CASE 8 ran 2026-09-02 18:04 — not closed (§40.7):** the engage reach had been the player's 144 u press reach borrowed, so the Hatcher stood and swung across an 80–144 u band; **fixed §40.1** (engage = halt + one radius = 92 u). The arc stutter is our 216 u/s Hatcher idling at its 0.5 s-stale follow point (`--enemy-chase-rate` arm tests a retail-typical 0.35). And the warp beside the enemy is **agent-versus-agent collision, not modelled at all** — the operator's own read, confirmed; a `0x006011F0` dig is next. **CASE 8 v2 (18:55, §40.9): still far with the operator standing still and the server's copy at exactly 80 u — the client's rendered body was frozen short by our instant `0x0028`; and retail's chasers run at 1.0, not 0.75 or 0.35.** Shipped: `ENEMY_MOVE_RATE = 1.0`, `HALT_ON_CLOCK`. **§40.11 (2026-09-03) then MOVED the diagnosis off the enemy entirely:** a rendered-position tap of both client world-copies (`toolkit/clientscan/agenttap.py`) shows the client parks the Hatcher at 79/84 u standing (correct) but, while the player moves, the PLAYER's own world-0 vs world-1 copies diverge a median 237 u / max 806 u — so the enemy (which parks ~80 u from the player's world-0 copy, faithfully) is rendered 2–587 u from the rendered player. All three CASE 8 v3 symptoms are that one player-sync desync; retail holds it to ~74 u. The enemy arc is faithful and done; the fix is the MOVECODE two-world player-sync (§40.12), which also owns the player's own move-command warp. **§41 (2026-09-03, `8533045`): the operator's "couldn't resume attacking" is FIXED at the swing gate** — the starver was `kbd_moving_at` with no stop report behind it (the drawn body was snapped ~498 u onto our own 520 u keyboard lead's endpoint and the release went unreported; 22 presses starved over 16.6 s), not the click latch RUN-FEEL first blamed — every press already ends that one. The press now supersedes the keyboard belief too (retail answers 24 of 48 such presses within 0.2 s and never waits for the stop), behind `--press-waits-for-stop`; and every press leaves a `press_verdict` row, the first refusal printed. Scores itself on the operator's next ordinary session. **2026-09-06 — THE HOSTILE CHASES, AND THE SERVER'S COPY OF IT IS THE CLIENT'S OWN (`a2d6bfd`):** the Hatcher aggros at 1200 u and follows with a `0x002A` naming the player every 0.5 s, halts on the clock, swings at reach, and walks the game's navmesh with a routed corridor out of the wedge (ANIMREF-RE §38–§42, MOVECODE-1z-by); since NPCTRACK-Q1 the server's position for it is the client's own sync copy plus the disc stop (6.7–15.7 u from the client's at the halts over four runs and a control), and since NPCTRACK-F14 the server's mirror of the PLAYER's world-0 runs the client's agent-avoidance pass (24 of 26 sidesteps and 14 of 14 halts on seven tapes, then out of sample on RUN-R4). So "no AI, no pathing" above is dated: what is still absent is any behaviour beyond aggro-and-chase-and-swing, a spawn table, and the shrine — `studies/npctrack/FINDINGS.md`, `PLAN.md` §8. |
| **R4b** | The skill substrate | See §3.2 — rewritten as a count | 🔶 **started, and the combat arc moved it a long way (2026-08-15, `studies/combat/PLAN.md`).** Eight real skills on the bar with correct tooltips (`04bafc1`), the cast lifecycle read out of the client's own asserts, `USE_SKILL` answered. ~~No skill resolves an effect.~~ **Skills now resolve damage from the client's own numbers**: the whole `s_skill` scaling window `+0x44..+0x68` is decoded, and damage is the skill's scale endpoints interpolated by the CLIENT's own formula (`0x005A8920`: `max(0, round(lo + (hi−lo)·rank/15.0))`, divisor a literal 15.0 verified by a stdlib read, no upper clamp so ranks above 15 extrapolate). `ENEMY_SKILL_FRACTION = 0.25` — a flat quarter of the player's maximum for every skill, admitted invention — is **gone**. The cast lifecycle is on the wire as ArenaNet sends it (`0x00E4→0x00E5→0x00E3→0x00E6`, with the QUEUE LAW: a press during aftercast schedules from the aftercast's end, which refutes the naive press+activation model by +0.64 s/+0.57 s). **The limit is now semantic, not numeric, and it is a real finding**: the client's table gives a magnitude and never says what it MEANS — `scale0/15` is `+ Damage` on Power Attack and `Healing` on Restore Condition, and `type_code` cannot discriminate. Three of the four skills on our own enemy's bar are a heal, a hex and an enchantment, so meaning is GWW-sourced per skill and unmodelled skills resolve to **None, not 0**. ~~Still absent: conditions, hexes, enchantments, energy and adrenaline costs, and effects other than damage.~~ **Hexes and enchantments came off that list 2026-08-20 — see the effect substrate below in this same row.** Conditions, energy, adrenaline and every non-damage MECHANIC are still absent. **2026-08-15, L6's attributability criterion is MET** — `--probe attributes` ran caged and the attribute panel followed all three steps with the ranks against the right names, so the ranks `2 * rank` reads are the ranks the player is shown. That also closes the one gap static analysis could not (`studies/combat/PLAN.md` §8b: whether the panel control binds the local agent at runtime) and confirms §8a's slot reading positionally, since step 3 reverses the rank column while holding the id column's order. The same run is what verified the `0x003A` crash fix — see R4a. **2026-08-15, the cast lifecycle is PLAYED AT A CLIENT** (`studies/combat/PLAN.md` §15, retiring §7's blocker): `0x00E4→0x00E5→0x00E3→0x00E6` had been offline-tested against six live cycles and never rendered. Four complete cycles now, accepted without asserting, max 36 ms against the declared recharge; a repeat press after `E6` gives a full second cycle; and recharge is **per-skill with concurrent timers** — slot 6's 8 s overlaps slot 7's 3 s cycles and each `E6` names its own skill. Operator-confirmed rendered: **both slots swept, slot 6 clearly longer than slot 7**, which is what shows the client honours the message's DURATION rather than flashing an icon. Still absent from this: the cast ANIMATION, which was not watched and is the unrun `cast_anim` probe's question (opcode 228 vs agent property 60), not this acceptance's. **THE SUBSTRATE'S SPINE LANDED 2026-08-20** (`d37ef8d`, `6b1f13c`, [studies/skills §12–§16](studies/skills/FINDINGS.md)): the effect channel `0x0042`/`0x0044` is wired, and the CLIENT DRAWS IT — a keypress runs `USE_SKILL` → the cast cycle → an apply at cast end → a removal at the stated duration, and the enemy's hex lands on the player unprompted. The client types the effect itself from the skill id alone (green stance border, magenta hex border, each skill's own art), expiry residuals are `+0.03..0.05 s` against retail's own 50 ms shoulder, and death strips per agent. **SCORING IT NEEDS AN OWNER RULING, so both readings are given rather than one number chosen.** §3.2 says R4b is met when an exemplar *"resolves its effect correctly against the client's own state"*. On **"the episode resolves"** — applied, typed, timed, expired, on screen — **n = 8 of 9**, every family except Skill (Charm Animal 411, whose effect is a PET: no table data at all, `skill_arguments = 0`, genuinely outside this rung). On **"the MECHANIC resolves"** — the skill actually doing what its text says — **n = 3 of 9**: Spell (Flare's 20 fire damage), Signet (Healing Signet's 88 heal, the client's own health readout moving 54→100 by exactly the 46 sent) and Attack (Sever Artery's Bleeding, **three degeneration arrows drawn on the health bar** and the client's displayed health falling at 6.03/s against the 6.00 sent). The other five apply a correctly typed, correctly timed effect whose consequence is unmodelled — attack speed, movement speed, damage negation, energy cost, arrow damage — and each is a per-skill wiki row on machinery that now exists. **The honest report is 8 of 9 partial, 3 of 9 complete, 1 of 9 untouched**, and the wording points at the first count while the second is what makes the engine real. **THIS RUNG IS ALSO THE BLOCKER FOR THREE OTHER ARCS, which is new as of 2026-08-20 and is the reason to raise its priority.** (1) **Hero AI** — the client holds none of it (R4c), the rules are conditions over effect state, and if AI policy is per-SKILL data as two independent sources say, then *the skill substrate's schema IS the AI's schema*; designing the policy table first is designing half the skill table blind ([studies/heroes §5.6](studies/heroes/FINDINGS.md)). (2) **Armour on skill damage** — `skill_damage` ignores armour, and the enemy's always-recharged bar means that unarmoured path does nearly all the damage in a real fight; the fix needs a per-skill armour-ignoring flag, because GWW makes it a per-skill property and a global answer would be wrong on every skill ([studies/isle §4.2](studies/isle/FINDINGS.md)). (3) **Its own listed gaps** — ~~hexes, enchantments~~ **both now resolve as episodes**; still conditions (which need the inflicting-skill join this server has no model of), energy and adrenaline. `agents.GV_ARMOR_IGNORING = 55` already exists and nothing reads it. Three arcs arriving at the same wall from different directions in one week is the signal; each was individually cheap to defer and collectively they are not. **DEEP WOUND landed 2026-09-09 (`ed46ffee`, SKILLS-DW, `studies/skills` §41): the mechanic count is 4 of 9** — 482 now reduces the maximum by 20 % on the wire (retail's own [`0x0042`, `0x00F1`, `0x009F 42`] batch, `deepwoundjoin.py` joins it 4/4 in the corpus), cuts healing 20 %, and kills only through the next health loss, arm-C confirmed live (the orb read 5 on a maximum-onto-25 pool, the signed delta, grey bar and all). It also filled a channel the server never had: the agent STATUS WORD (`0x00F1`) now rides behind every condition, hex and enchantment, so the client's health-bar colorations (hexed, poison, bleeding, deep-wound grey) finally draw. Still absent: the six other non-degenerating conditions' mechanics (Blind, Weakness, Cracked Armor need an armour/attack field we cannot witness), energy/adrenaline are separately DONE, and the AI-heals-itself and armour-on-skill-damage items stand. **HEAL NUMBER closed 2026-09-09 (SKILLS-HN, `studies/skills` §42) without a run:** the "applies property 55 and draws no number" item was an instrument error — the 2026-08-20 scan looked for saturated green, and the frames carry a pale BLUE "+46" over the player 3 of 3, with the "−46" damage number as the same-run control; retail's 800 heal events ride with no sibling that damage lacks (`healjoin.py`), so the client draws from the 55 alone. The census also refuted "overheal is silent": retail sends the 55 onto full pools (46 witnesses, GWW "Heal" says the blue number shows even then), so `heal_agent` now sends the skill's amount regardless of the pool (`--no-overheal-number` reverts); `--probe heal_number` is registered for the one thing no capture shows — our client on a full pool. **ARMOUR-ON-SKILL-DAMAGE closed 2026-09-09 (SKILLS-FA, §43), incoming half:** a fire spell now scales by the player's ELEMENTAL rating, one rating and no location roll — the shape retail's own casts show (68 of 68 hits one value per caster/skill/target, `spellhitjoin.py`), CORROBORATED with the wiki's wording rather than OBSERVED on a lopsided set; §39.6's loopback probe was struck as unable to answer. Outgoing stays blocked on a creature armour value no channel carries. **BLIND closed 2026-09-10 (SKILLS-BL, §44), and the counts above are put straight:** 479 makes a swing miss 90 % (WIKI, unmeasurable on this corpus — 0 of 1,042 retail closes were swung blind, `missjoin.py`) and the miss goes out as the client's own attack-fail word `0x00A0 [38, target, attacker, 3]`, whose reason table (block/dodge/fail/miss/obstructed/stray) was read out of the drain and the owner's archive; one retail witness (reason 2, an attack skill) pins the slot order. **Two tallies, not one:** the FAMILY count is the 08-22 entry's **8 of 9** (every family but Skill resolves its mechanic; the 09-09 entry's "4 of 9" was a condition count written in the family column), and the CONDITION count is **6 of 10** — Bleeding, Burning, Disease, Poison, Deep Wound, Blind — with Crippled, Dazed, Weakness and Cracked Armor still icons. **RESTORE CONDITION closed 2026-09-10 (SKILLS-RC, §45):** the "AI heals itself" item was the skill's own mechanic unmodelled — it heals per condition REMOVED from a target OTHER ally (WIKI), so a lone hostile cannot cast it and one with an ally cures before it heals; the client's target byte 3/4 = ally/other-ally is CORROBORATED on eleven skills; the cure's batch order is RECONSTRUCTION (no retail 276 cast in 1,364). **2026-09-16 (SLICE-F48, `3ffee5ab`+): movement speed on the wire, BOTH signs, on by default — boosts summed and capped at +34, Crippled × 0.5 multiplying, "Charge!" curing it, bodies declared too, the movement composite reading the declared base; confirmed on three agent-driven Isle runs (383.04 / 385.92 / 144.00 / 191.52 on our wire, the client walking at each).** |
| **R4c** | AI + spawns + quests | See §3.2 — rewritten as a count | ⬜ not started, **and 2026-08-11 established what "started" would even mean** ([studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md), `921d722`+). Monster AI *as a mechanism* is **not recoverable** — not from the client (0 of 937 embedded source paths under any `\Srv\` tree, from a detector proven to catch 6 of 6 planted ones; 33 AI-adjacent searches over two independent routes, all zero), not from the wire, and not by any capture campaign, because it is never shipped and never transmitted. What **is** recoverable is the observable envelope, and the study designs the labelled behaviour campaign that would recover it (§7) plus four desk follow-ups needing no capture at all (§7.9) — **the first of which ran the same day and made the binary negative total**: `CHAR_AI_MODES`, the one lead the study declined to call refuted, is 3 and its modes are Fight/Guard/Avoid Combat, i.e. the player's own hero-and-pet stance widget. It also found the AI-adjacent numbers already in `authsrv.py` are mostly the **wrong shape** rather than merely unmeasured: reach is per-creature-model (~65 / ~599 / ~706 units observed against our one global 150), a leash was *uncomputable* from the state `spawn_enemy` kept (2026-09-24: the anchor is kept at create and a stander walks home, DESKWORK-D8 steps 3–4, PLAN-LOG), and 4 of 5 fights in the corpus are started by the **player**, refuting our proximity-initiation model for 4 of 5. **2026-08-15 — the PARTY half of this rung is now scoped, and it is the recoverable half** ([studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md)): heroes and henchmen are the mirror image of monster AI, because a hero is a thing the CLIENT renders, commands and stores. The two party-add messages are shaped from the client's own descriptor tables and traced store-by-store — `0x01BF` PARTY_HENCHMAN_ADD `[u16,u16,string16(20),u8,u8]` (CORROBORATES GWCA independently) and `0x01C2` PARTY_HERO_ADD `[u16,u16,u16,u8,u8]` (**CORRECTS** OpenTyria's "a `uint8` level"); `0x0074`'s upstream `{hero_id,level,primary,secondary}` is **REFUTED** at 20 fields / 127 bytes. The catalogue is located and closed: **`s_heroClientData` = 40 rows × 24 B at `0x00A35E08`**, `HEROES`=40, `HERO_UNUSED`=0, per-player cap **7** (three independent sites) — and the rival 48×12 reading was a misattribution to the **adjacent title table**, settled by reading the client's own assert strings. Extraction is ruled **permitted** under the MEASUREMENT branch. The honest negatives: hero **skill-bar delivery is NOT FOUND** on any wire shape, and the **c2s** direction (stance, flag placement, hiring) is NOT FOUND at every point looked. **The wire cannot teach this** — 0 of 22,524 decoded live GAME_SMSG messages carry opcode 114/116/447/450, because every live session is solo; the only vault appearances are 92 `PROBE[smsgsweep]` sends. A henchman authorship route is **buildable now** (one new message on top of the existing `party_build()`), with acceptance criterion R4c-H in §8. **2026-08-16 — R4c-H IS MET, caged loopback, four arms** ([studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md) §10): control **1** roster row, treatment **2**, the second reading **`Mo1 Hatcher [Collector]`** — archive-resolved name, Monk, level 1 — from one `0x01BF`. Three results beyond the criterion. **(a)** The row draws with **NO world body** (so `PtRoster:602`'s agentId lookup is not a precondition) but draws EMPTY: `Lvl 255 ...`. **(b) A discriminator arm overturns the upstream reading** — with the wire deliberately carrying a *different* name, profession 6 and level 20 while the body kept Hatcher/Monk/1, the row rendered **the BODY's values in every field**, proven from the captured plaintext. So `0x01BF`'s name string and its two trailing bytes do **not** drive the roster row: the message binds a roster SLOT to an `agent_id` and the client reads the rest from that agent. GWCA/OpenTyria's `profession`/`level` names are **not confirmed**, and the body arm alone *looked* like a confirmation because it was a confound. **(c)** Unpredicted: the **compass flag widget appears** (one group flag + three numbered + clear) from one `0x01BF` even with no body, corroborating the wiki's four-control description and §3.1's index-0 reading from the screen. Henchman authoring is done as a mechanism. **2026-08-16, same day — THE HERO ARM RAN TOO, five arms, closing two of §7.2's three blockers** (§11). **(1) `0x01C2`'s word order is settled BY CONSTRUCTION**: the body was created at agent **200**, deliberately outside the 1..39 hero-index range, so a word carrying it cannot be a legal hero index — and the row renders only in the arm where **msg+0xc (→ entry+0x0) holds the agent id and msg+8 (→ entry+0x4) the hero index**. That yields a structural fact too: **entry+0x0 is the agent id in `0x01BF` AND `0x01C2`** — same storage slot, different wire order, so §1.2's refuted "by analogy" reasoning reached the right offset for the wrong reason. **(2)** The hero row renders `Mo1 Hatcher [Collecto…]` **plus a numbered commander-slot button** the henchman row lacks (`GmHeroCommander`'s per-slot UI), and its text again comes from the AGENT — three arms, two message families, one rule. **(3) `0x0074` MERCENARY_INFO is what creates the `charHeroData` record**, by a single-variable pair: with it the trailing `0x0072` diagnostic asserts `attribState` (`ChCliAttrib.cpp:156`), without it `charHeroData` (`ChCliHero.cpp:199`). Every static route had this NOT FOUND; one arm settled it. **The gate did not vanish, it MOVED** — onto §4's sharpest negative, hero **attributes**, which the client now names itself. **(4) That shaped hypothesis — `0x0074`'s two 5-dword groups as the attribute block — was TESTED AND REFUTED the same day** (§12), with the prediction on record before the run. An arm carrying ten dwords of `12` (the rank cap), the third-copy flag set (a branch never previously exercised) and the leading bytes loaded produced a **byte-identical** `attribState` assert. Reading the assert instead of guessing gives the real shape: `attribState` is a **separate `0x43c`-stride record, binary-searched by a key at +0**, holding **`attrib[51]` of 20 bytes each** (`ChCliAttrib:177` `cmp 0x33`; index math `20*i+4`) — 1020 bytes, against a 40-byte chunk in a different structure. New measurements banked: **51 attributes**, **rank cap 12** (`AcctTemplate:441`). **The live lead is now the TEMPLATE system** — `AcctTemplate:422/423/440` and `TemplatesCode:168`/`TemplatesHelpers:368` bound a struct carrying `attribCount` + `attrib[]` + `attribValue[]`, which *is* a build, and is §4's "packed template blob" candidate with named asserts to find it by. **(5) 2026-08-16, third pass — the template lead was a RED HERRING and the real mechanism was already in our tree** (§13). `AccountTemplateDataSkill` (140 B: profPrimary, profSecondary, attribCount, attrib[12], attribValue[12], skill[8]) is **account-local** — the base64 saved-build feature — and a reachability closure from it contains **zero message handlers**. What actually creates an attribState record is **`GAME_SMSG 0x0037`** (`[agent_id,u8,u8]`, handler `0x0091d8c0` → thunk `0x0080EAA0` → creator `0x008199C0`, whose own guard is `ChCliAttrib:313` `!attribState`), and **`0x003A`** (`[agent_id, array32[48]]`) fills `attrib[]`. **Both are keyed by AGENT id, which is why a hero can have attributes at all — and both have been in `authsrv.py` since the combat arc**, sent to the player's agent every session. Two refuted hypotheses were spent hunting a message already in the tree: the §3 failure in miniature. Sending the pair for a hero **does clear the attribState gate** — but the client then dies on **`profession < arrsize(s_profChapter)`, `ConstChar.cpp(1296)`, bound 11**, with or without the `0x0072` diagnostic, so it REGRESSES an otherwise-working hero and the flag ships OFF. Two more fixes tried and refuted there: `0x0074`'s `b2`/`b3` (upstream's "primary/secondary" — a second failure to confirm those names) and matching the body's profession to the attribute set. **(6) 2026-08-16, fourth pass — READING THOSE THREE CALLERS CLOSED IT. THE HERO IS AUTHORED** (§14). All three sit in one function, `0x00819EF0`, which takes the attribState record, reads **its agent id**, and looks that agent's primary/secondary up in **`ctx[0x2c]+0x6BC`** — the array `studies/profession/RUNS.md` already knew is written only by **`0x00B7`**, which we had only ever sent for the player. **There are TWO profession stores**: `0x00A6` writes the agent's own bytes (what the roster label reads — why the row already said `Mo1`), `0x00B7` writes `+0x6BC` (what the attribute code reads). Conflating them cost an afternoon. With `0x00B7` sent for the hero, gate 3 cleared and the assert moved to `attribState ChCliAttrib.cpp(435)` — whose fix `authsrv.py`'s own comment already recorded: **points first, profession second**. **Four gates, all cleared:** `charHeroData`→`0x0074`; `attribState:156`→`0x0037`; `ConstChar:1296`→`0x00B7` for the hero's agent; `attribState:435`→ordering `0x0037`→`0x00B7`→`0x003A`. The `0x0072` diagnostic that ASSERTED on 2026-08-12 now **completes silently**. **The payoff is a name**: with the record incomplete the row read `Mo1 Hatcher [Collector]` (the body's name); complete, the same row reads **`Mo1 Norgu`** — `s_heroClientData` row 1. The client SWITCHES name sources once the hero record is satisfied, which measures §0's central claim that a hero resolves its identity through the static table. Also read in passing: **`s_attrib` = 51 rows × 20 B at `0x00A35740`** (profession, self-index, two string ids, an is-primary flag set on exactly ten rows), and attributes 26-28/45-50 carry profession 11 — the PvE title tracks, out of range by design. **(7) 2026-08-16, fifth pass — THE SKILL BAR, and §4's negative was a SCOPING ERROR** (§15). `0x00DA` SKILLBAR_UPDATE is `[agent_id, array32[8], array32[8], u8]` — RECV, **agent-keyed, eight slots** — and this server has been sending it **for the player every session**. §4 searched `0x0074`/`0x01BF`/`0x01C2` and the SEND-direction shapes and concluded "no skill-bar field anywhere"; the answer was outside that space. **Fourth time this arc that the mechanism was already in the tree** (after `0x0037`, `0x003A`, `0x00B7`) — every piece of a hero turned out to be an existing agent-keyed message we only ever addressed to the player. Sent to the hero it is accepted, 75 B, no assert. **HONEST LIMIT: that is delivery, not display** — the hero panel is opened by clicking the commander-slot button and that click CRASHES, so nobody has seen eight icons. **`0x0072` is not a diagnostic, it is HeroActivate**: its four fields are the client's own format string `HeroActivate (hero %d, agent %d, inventoryId %d, aiMode %d)`, matching the descriptor exactly. Measured, two runs differing only in it — without: the row reads `Mo1 Hatcher [Collector]` (the BODY's name) and flag 1 is greyed; **with: `Mo1 Norgu` and flag 1 goes GREEN**. So `0x0072` promotes a labelled body into a hero, switching the roster label to `s_heroClientData` and binding the `GmHeroCommander` slot. **`aiMode` is field 4, so the Fight/Guard/Avoid stance IS server-settable** — a partial answer to §3.3's oldest open question. **(8) 2026-08-16, sixth pass — `inventoryId` REFUTED as that suspect, twice** (§16). Naming the assert should have come first: the click crash is **`commander` / `GmView.cpp(5890)`**, not any of the eight inventory asserts (`asserts.py` cannot read line 5890 — one of its 371 blind sites, its answers being floors). And `inventoryId = 1` changes nothing: accepted with no assert on the activation path, and the **identical** crash on the click. The field is **inert on every reachable path** and its meaning stays NOT FOUND. **The real cause is now read statically**: commander objects live in a container at `ctx+0x20`, `heroCommanderSlot[7]` at `+0x30` holds **keys into it**, `0x00524C40` is a **get-or-create**, and `0x00524DB0` — the one the click uses — **does not create**, it looks up and asserts. Our hero has no entry. The creator's other caller sits in a loop over the `activeHeroes` stack buffer built by scanning the party's agents (`GmHeroCommander:214`). **Precise next step, desk work only:** does that scan skip our hero, or register it under a key different from the one `GmView:5890` looks up? **(9) 2026-08-16, seventh pass — THE DESK WORK, and it refuted its own prediction** (§17). The whole commander path is now read out of the binary: the iterator `0x008563B0` walks `[ctx+0x4c]`→my-party→`+0x24` with **stride 0x18 — exactly `0x01C2`'s entry size**, so it walks the entries we append; the scan `0x00524E00` filters `[edi+4]` against a widely-used "my id" accessor and takes **`[edi+8]` as the commander key**, which is where `0x01C2`'s `msg+0x10` lands — and we had been sending **0** there. Prediction: put the hero id in `msg+0x10` and the panel click stops asserting. **REFUTED** — identical `commander`/`GmView(5890)`, with no regression (`Mo1 Norgu`, slot bound, flag green), so the change is kept as better-founded but is RECONSTRUCTION, not a fix. **What it eliminates is the value**: the scan has exactly ONE caller, `0x004E5D85`, inside a GmView **event** handler, so the leading explanation is no longer "wrong key" but **"the scan never runs"** — the commander container is filled by a client-side UI event, not by the wire. **Also a self-correction (§17.3): §11.1's "msg+8 is the hero index" is WITHDRAWN.** H1/H2 only showed `msg+8` accepts 1 and rejects 200, and in this rig `PLAYER_NUMBER`, `PLAYER_AGENT_ID` and the hero index are **all 1** — hero index, owner player and owner agent are indistinguishable, and the scan's filter actively suggests *owner*. `msg+0xc` = agent id still stands. **(10) 2026-08-16 — ran that rig: hero index 2, and the confound broke** (§18). With `msg+8`=1, `msg+0xc`=200, `msg+0x10`=2 all distinct, the row rendered **`Mo1 Goren`** — hero 2's own name. So **`msg+8` is definitively NOT the hero index** (it carried 1 while the hero was 2), settling by experiment what §17.3 could only doubt; what it *is* stays UNVERIFIED, narrowed to owner-player-number vs owner-agent-id, which are both 1 here. **And `s_heroClientData` row 2 = `Goren` is now confirmed FROM THE SCREEN**, independently of the recon's `textrec.py` resolution — rows 1 and 2 both verified from two unrelated directions, so the catalogue reading is solid. Remaining confound: `0x0074`, `0x01C2`'s `msg+0x10` and `0x0072` all carried 2, so which message supplies the identity is undetermined; **(11) 2026-08-16 — ran that split too, and `0x01C2` carries NO hero identity at all** (§19). Prediction on record first: row 3's name id 36274 resolves to **Tahlkora**, so Tahlkora would mean the identity rides `msg+0x10` and Goren would mean it rides `0x0074`/`0x0072`. With `0x0074`/`0x0072` on hero **2** and `msg+0x10` on **3**, the row read **`Mo1 Goren`** — the client ignored the party-add message's hero id completely, with no crash and no change. So the hero's identity arrives **entirely on the data-cache family**, and `0x01C2`'s five fields are a party id, an owner-ish word (UNVERIFIED), the agent id and two bytes. That is stronger than §0's original "a hero carries no NAME": it carries no identity. **`msg+0x10` is now inert on everything observable** — §17.1 read it as the commander key from the scan's `[edi+8]`, §17.2's hero-id value did not fix the panel click, and a deliberately WRONG value here changes nothing; consistent with §17.2's leading explanation that the scan never runs. Its role stays RECONSTRUCTION. **(12) 2026-08-16 — split those too, and the question was malformed** (§20). Three outcomes named first; the run gave the third. With `0x0074` creating a record for hero **2** and `0x0072` activating hero **3**, the client produced `charHeroData` / `ChCliHero.cpp(199)` — the **identical** assert §11.3 got by omitting `0x0074` altogether. So **`0x0074`'s field 1 is the record KEY and `0x0072`'s field 1 is a SELECTOR into the same namespace**, and a mismatched selector is indistinguishable from the record never existing. Neither message "supplies" the identity: `0x0074` creates a keyed record that carries it and `0x0072` activates that record under the same key. It also re-confirms §11.3 from a new direction — that section removed `0x0074` to prove it creates the record; this keeps it and mismatches the key, a different manipulation reaching the same gate. **The family now reads: identity is the data-cache record's; `0x01C2` only binds a roster slot to an agent id.** **(13) 2026-08-16 — `msg+8` IDENTIFIED: it is the OWNER PLAYER NUMBER** (§21). `--player-number 2` finally separates `PLAYER_NUMBER` from `PLAYER_AGENT_ID`, and two arms differing only in `msg+8` are **exact mirrors**: `msg+8`=2 (player number) renders the row but leaves the commander slot unbound; `msg+8`=1 (agent id) binds flag 1 but shows **no row**. The roster row appears exactly when `msg+8` equals the declared player number — consistent with the original rig and with H1's rejection of 200 — so the field is now positively identified, closing the thread §11.1 opened wrongly, §17.3 withdrew and §18 refuted. **The mirror is the unexpected half**: both consumers read `entry+4` yet compare it against DIFFERENT "my id" values — the roster UI against our declared player number, the `GmHeroCommander` scan against `ctx[0x44][0x2ac]`, which stayed 1. RECONSTRUCTION: `--player-number` changes only what we SEND, not what the client believes about itself, so it desynchronises the two; in the default rig both are 1 and everything agrees, which is why the hero worked. Whether `ctx[0x44][0x2ac]` is the agent id or a client-side player number is still undecidable here (both are 1) and needs the CLIENT's value moved, not ours. Practical: do not use `--player-number` outside this experiment — it makes the roster row and the commander binding mutually exclusive. **(14) 2026-08-16 — found what writes it, desk work only** (§22): `ctx[0x44]` is the MISSION subsystem (accessor `0x0084DD70` sits in **MsCliApi**), `--field 0x2AC --writes` gives eleven stores of which two in that range are real, both copy **field 1** of a message struct, and neither has a call xref — each VA sits in one aligned `.rdata` word, i.e. a dispatch entry. `msgshape --all` resolves them: **`0x0199` INSTANCE_LOAD_INFO** (handler `0x0084EF00`) and `0x01A4` (handler `0x0084F230`, never sent by us). **So `ctx[0x44][0x2ac]` is `0x0199`'s field 1 — the player's agent id, which this server has sent at every instance load since the beginning.** That explains §21's mirror exactly: the roster UI filters on the player number while the commander scan filters on `0x0199` field 1, and `--player-number 2` moved one and left the other at 1. In the default rig both are 1, both filters see 1, and the hero binds. **Trap removed:** that field was a literal `1` at the send site rather than `PLAYER_AGENT_ID` — harmless today, but it demonstrably feeds a filter three subsystems away, so it now uses the constant. The confirming arm (move both together) was NOT run and the reason is recorded: it means moving `PLAYER_AGENT_ID` itself, which touches the spawn path and deserves its own arm. **(15) 2026-08-16 — A FULL AUTHORED PARTY OF FIVE** (§23): player + heroes **Norgu, Goren, Tahlkora** in commander slots **1/2/3** + the **Hatcher** henchman, one roster, one run. `--hero` takes a list and `hero_slots()` owns the agent-id/definition arithmetic in one place. Four things measured that n=1 could not: the `heroCommanderSlot[7]` array **assigns sequentially and independently** (three separate numbered buttons); each hero **resolves its own identity** from its own `0x0074` record, so §20's keyed-record model holds past one; heroes and henchmen **coexist and the client distinguishes them visually** — the henchman row has NO numbered button, which is §3.1's reconstruction and the wiki's "three individual flags plus one all" now visible rather than inferred; and **`s_heroClientData` row 3 = `Tahlkora` confirmed from the screen**, so rows 1/2/3 are each verified from two unrelated directions (archive resolution and the client's own rendering). Guards mirror the client's bounds: >7 heroes refused (`cmp 7` at PtPlayer:332 and GmHeroCommander:214), duplicate hero ids refused (one record per key),  **(16) 2026-08-17 — THE COMMANDER QUESTION IS MEASURED, and the arc's last wall is down** ([studies/heroes/FINDINGS.md](studies/heroes/FINDINGS.md) §33). §26.4/§27.2/§32 all stopped on one sentence — *does `0x008590CA` execute, and it needs a breakpoint or code cave*. Built as `toolkit/clientscan/commandertrap.py`: a debugger in pure `ctypes` setting EXECUTE breakpoints in **DR0..DR3**, which are per-thread processor state, so **nothing is written into the client** — no `int3` over an instruction, no code cave, no injection (carve-out 3 permits a compiler; this did not need one). Every site's bytes are re-verified against the RUNNING process before arming, because the pin is 38797 and these are 38833 addresses and §24 already crossed those once. **Three arms, control firing in all three.** Default rig (party-cache HIT): `worker=1 raise=0` — §26.2's gate OBSERVED doing what the disassembly said, predicted in writing beforehand. `--hero-bust-cache` (cache MISS): `worker=1 raise=1 case93=0` — **the event IS raised and its handler never runs**, and the image's own byte map + jump table make that unambiguous (`0x1000011E` → case 93 → `0x004E5DE1`, the ONLY event routing there). Bulk path: `bulkraise=1 bulk=0 create=0` — `0x00524C40` **never executes**, confirming §27's `count=0` by a code trace rather than a memory read, two unrelated instruments agreeing. **The corrected shape: the missing piece is a SUBSCRIPTION, not a trigger.** Every earlier fix (`inventoryId` §16, `msg+0x10` §19, the cache gate §26) aimed at making the client RAISE the event; §26's arm actually succeeded at that and the panel still asserts. **So `0x01C2` cannot bind a commander and no wire field will change it** — the hero as authored (row, name, level, profession, attributes, skill bar, lit flag) is complete for everything the wire governs. Also confirmed from the frozen client: §25.1's push-order decode against the live stack, and §26.1's `ecx`-holds-the-entry claim. **Four tool defects, three caught by the tool's own control before it ever read the client** (§33.8) — a 64-bit debugger receives `STATUS_WX86_SINGLE_STEP` (`0x4000001E`) not `0x80000004` from a WOW64 target, so v1 reported NO HITS and would have published the right headline from a dead instrument; `EFLAGS.RF` does not survive `ContinueDebugEvent`, so one instruction trapped 32 times in 4ms and read as "executed 32 times"; state was captured after the read handle closed, so a whole run's fields came back `None` and that run was DISCARDED rather than published; and the module list is not ready the instant a process exists. **The control had a hole too**: it stopped at the first hit, proving a breakpoint FIRES while saying nothing about whether the target RESUMES — and the untested half was the broken one. **(17) 2026-08-17 — (16)'s wall is DOWN, and its closing sentence is SUPERSEDED** ([studies/pvpui/FINDINGS.md](studies/pvpui/FINDINGS.md), the PvP-UI arc, `1e631ea`+). (16) ended *"`0x01C2` cannot bind a commander and no wire field will change it"* — the subscription reading was right and the conclusion drawn from it was wrong, because the missing piece was **timing**, not a field. Measured: our `0x01B2` raises `0x10000114` at instance load and **GmView subscribes to that event 53 milliseconds later**; its GmView case is the only caller of the commander-model rebuild, nothing raises it again, so the model is built once over an empty container and never rebuilt. **`--party-mine-late SECONDS`** (new, opt-in, off by default) re-sends `0x01B2` after the load — a second send is a second raise, because the handler raises on both branches — and `0x00524C40`, the function (16) proved never executes, **ran for the first time in this project**: commander container `count=0 → count=1`, `heroCommanderSlot[0] = 0x1`. A wire message binds a commander after all; it just has to arrive when someone is listening. **Then three owner clicks on the party-window hero button walked the assert forward four times**, and the whole `GmView` case for `0x100001A4` now passes: `commander` (5890) → `heroData` (5897, with `--hero-roster-id 200`) → `heroData->agentId` (5898) → out of `GmView` entirely. That last hop was this lineage's recurring failure again — `heroData->agentId` has exactly one writer, opcode **`0x0072` HeroActivate**, and `HERO_ACTIVATE = False`: **a message the tree already implemented, behind an opt-in flag no run of the arc had switched on**, the fifth such (after `0x0037`, `0x003A`, `0x00B7`, `0x00DA`). The click now stops at **`inventory` / `ItCliApi.cpp(488)`**, a general 22-caller equip-slot helper — **the hero has no per-owner container in the item client's table at `[globals+0x40]+0xD4`**. Cross-checked against §8's `0x006D` item line the same day and it is NOT that: item RECORDS already exist (375/375 of retail's non-zero `0x006D` ids are `0x015E`-family declarations), the missing piece is the owner's container, and our `0x013F`/`0x013E` bag family has only ever been addressed to the local player. Corrections this arc owes, all in its study: the harness does NOT default to 38833 (`drive_client.py:87` selects by build, :167 excludes it — pass `--exe` **and** `RURIK_DAT`); `0x01D9` writes `+0x58`, a different field, not the container pointer; and **every `PyCliParty` worker takes `this = object + 4`**, so field `+0x54` is spelled `0x50` and a displacement-anchored scan returns a confident zero — now a fourth documented blind spot in `codescan.py`'s footer. **AND THE HERO HALF IS SETTLED THE SAME WAY THE MONSTER HALF WAS, 2026-08-20** (`910d7ba`, `fc6821a`, [studies/heroes §5.5](studies/heroes/FINDINGS.md)): the shipped client holds **no hero AI at all**. 51 of 937 embedded source paths match hero/companion vocabulary and every one is UI, a client-side `Cli` record or a `Const` table; a behaviour-vocabulary regex over 19,758 asserts returns **exactly one hit**, and it is a widget asserting its own button state next to `m_aiMode < AI_MODE_ICONS`. The client's whole notion of hero AI is how many pictures the button strip can draw. This did NOT follow from `studies/monsterai` — GWW says heroes and henchmen share an AI and says nothing about hero↔monster — so it was re-run with hero vocabulary and its own control. **So this rung is authoring, not recovery**, and §5.6 counts what the authoring can be checked against: ~92 implementable per-skill rules, not the 184 the category size implies. Deliberately unplanned further — the rules are conditions over effect state R4b does not model, and the skill substrate's schema is likely the AI's schema. |
| **R5** | Declarative authoring toolkit | A new zone in TOML, hot-reloaded, walked | ⬜ not started — but its substrate exists as of `8a28c42`: `content/*.toml` and `toolkit/content.py`, with the server holding zero content literals. **Its other half now exists too**: R5m authors the zone's *geometry*, which TOML was never going to describe. **And the ITEM half stopped being opaque on 2026-08-20** (`da1bbff`…`0d0a4b2`, [studies/itemmods](studies/itemmods/FINDINGS.md)): every item's stats live in 32-bit modifier words that `content/items.toml` could only copy verbatim out of a capture — armour rating, damage range and every "+N" line among them, which `studies/character` called "the largest hole" in three places. The format is now read out of the client's own parser — `{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}` over 157 identifier slots, each one's meaning recoverable because every handler formats through TextApi — validated on **5,266/5,266** real modifier words and located structurally on all three builds. **A word we composed has been rendered by the retail client**: `0x21F81301` on the starter hammer drew `Hammer Mastery +1 (Stacking)`, so authoring an item's stats is now writing a number rather than finding one. The trap: bits 31, 30 and 19 are a fixed per-identifier prefix and must be COPIED, not computed. |
| **R5m** | **Custom map geometry, end to end** | A map we authored loads in the retail client, and geometry we chose constrains the character | ✅ **2026-08-11**, arc landed `a776950`, criterion completed the same day. **The client walks on our terrain and stops at our walls.** `mapbuild.build_flat` assembles a whole map from typed parameters — 7,841 B, 9 chunks, **97.04% generated**, the rest being FINDINGS 14's 232 bytes of ArenaNet constants read from an archive at run time — and the retail client loads it, places a character in it and writes nothing back (FINDINGS §22, four discriminators). Then **E1 proved the geometry is ours and not a coincidence**: two maps differing in **33 of 7,841 bytes**, all inside the pathing chunk, both 7,841 B, with the mesh rect at 0..3072 against 1024..2048, confined the character to reported bounding boxes of **3072.0 × 3072.0** and **1024.0 × 1024.5** — the ratio of the two rectangles, measured from the client's own position reports while our server broadcast no position at all (FINDINGS §23). The read direction is byte-exact across the corpus: terrain 349/349, pathing 349/349, whole map file 349/349 Bloated **and** Stripped — and since 2026-08-12 the STRIPPED terrain chunk too (`strippedterrain.py`, FINDINGS §37), whose real claim is not the round trip but that its **60,468,224 height samples equal the Bloated chunk's on 349 of 349 maps**, pulled out of a Huffman bit stream by a module that never reads that chunk. A retail map also stands up in Blender (`tools/blender/import_gwmap.py`, 213,921 verts, orientation checked against the props chunk through the test's own walker — the terrain path never reads it) and **since 2026-08-12 comes back out of it**: `export_gwmap.py` round-trips Pre-Searing's 212,992 heights, tiles and shade bytes byte-identically through a `.blend` read by a separate Blender process, and a mesh authored in Blender from nothing reaches a map file passing all 17 open-time gates (FINDINGS §32). **Since 2026-08-13 the interchange carries PROPS** (format_version 2): every placement from BOTH streams cross-checked at export through `corresponds()`, model indices resolved to file ids with MFT (size, crc) identity, **the rotation composition measured** — z first, then x, then y, per-axis signs (−, +, −), 3,545/3,545 multi-axis records on a 12-map probe, closing what `props.py` had open — and Blender places every placement as a measured proxy (footprint prism or radius cylinder; placements only, NO ArenaNet model geometry, which nothing in this tree decodes). That byte-identity is the weak half by measurement — a memcpy sabotage keeps all six of those checks green and is caught only by a sculpt control. **And since 2026-08-12 the OTHER delivery route is open: the client's own map compiler builds from a Stripped stream we supply** — §35 it compiles at all and reproduces ArenaNet's bytes, §36 it compiles the stream WE write rather than anything cached, and **§38 it floods terrain we AUTHORED**: the rebuilt navmesh stops at world x = 1152.0, the cell boundary we chose, with walkable area in the steep strip falling from a measured 37.3% to 0. **Portals and multiple planes are DONE as of 2026-08-12** (FINDINGS §31, closing §8 item 10(b)) — ~~this row listed them under "What is NOT done"~~ for six days after they landed, which is exactly the staleness the top of this section is about. A portal WE authored joins two planes: `portalprop` (`plane_map [0, 0]`, **18 of 18 gates**) walked **65 s with no crash**, the bounding box opening from (0, 64)..(2048, 3072) to (0, 0)..(3072, 3072), and the client reported **plane 1 on 19 of 49** reports with **17 past x = 2048** — where the no-portal arm was pinned at x = 2048.0 and reported plane 0 on 76 of 76. The props chunk that makes plane 1 legal (6,585 B, plus 89 B of model dependencies) is **carried from row 33086 at run time and never stored**, the `mapbuild` FINDINGS 14 pattern. **The control is what makes the green arm mean anything**: `portalpropbad` (`plane_map [0, 67]`, one past `propCount`) crashed on `Assertion: index < m_count, Array.h(587)` with **`edi = 0x43 = 67`**, the value we wrote into tag 12, arriving in the register the disassembly said holds the index. The diagnosis predicted the register contents and not merely a crash. A prop index only has to be IN RANGE; prop 0 of row 33086's 67 is somewhere else entirely in the world and the client did not care. **Residuals, named in §31.4 and carried as live next-actions at §8 items 10(h) and 10(i)**: what plane 1 looks like **underfoot is untested** — nothing measured the character's z, our terrain is flat, and the prop carrying plane 1 is elsewhere in the world, so it may be walking on nothing (the interesting version of the rung is a plane whose prop IS its surface); and **one prop index was tried, not the space** (`[0, 0]` works, `[0, 67]` crashes, nothing between). **What is NOT done**: authored art (textures are borrowed retail file ids) ~~and elevation — a height field that is not flat, walked, is still open as §8 item 10(c)~~ (**elevation CLOSED 2026-08-21, corrected here 2026-09-24**: WORLDMAPS W16–W19 walked authored slopes on the retail client — W19's S4 arm climbed a 41.5–42.5° strip to its plateau, max y 3,064, and S5 stopped below a 46.45° one at 1,728, to the unit; [studies/worldmaps/FINDINGS.md](studies/worldmaps/FINDINGS.md) W19). That is the TERRAIN side; §31.4's untested-underfoot residual is the neighbouring question on a PROP-MOUNTED PLANE, tracked separately as 10(h), and neither answers the other; only the terrain of §38's map is ours (props, zones and collision are ArenaNet's); and the delivery path is still `datwrite` into a copied archive — which now bounds authoring to maps that SHRINK, since it writes uncompressed and will not relocate (§8.10 e9). |
| **R0b** | **Instrumented-client capture** of a real session | A live session recorded from inside a client we control, both directions, stamped `origin: live` and byte-replayable from disk | ✅ **2026-08-07**, `vault/captures/live/20260807T143055`. Six connections to ArenaNet (one auth, five game, all on **port 80**), both directions, zero TCP gaps, stamped `origin: live`, and **byte-replayable in the strong sense**: `livesession.py --assemble` regenerates all six decrypted files **sha256-identical** from `wire.jsonl` + `keyring.jsonl` alone, with no client and no network. 200,153 bytes of ArenaNet plaintext, 11,700 messages. **The independent check is the framing**: every one of the 12 streams decodes 100% clean to its final byte against `schema/messages.json`, which was built from the *client's* format tables and never from these bytes. Adversarially attacked from four angles (§3.3); three failed to refute, and the fourth's safety finding is fixed. See §3.3 for what the number does *not* mean. The pipeline is complete — key-tap cave (`keytap_patch.py`, `--key-tap`), off-wire WinDivert capture (`wirecapture.py`), memory reader (`keytap.py`), driver (`livesession.py`, wired to launch at `b8f6740`, 2026-08-07), decrypt (`replay.py`) — and `dryrun_keycapture.py` ran it end to end against our own server, elevated, GREEN (`7a25361`, 2026-08-07): the off-wire ciphertext matched the server's own `.raw` byte for byte, and the tapped key decrypted it to the server's logged plaintext. The live build is staged, stock-DH and key-tapped (2026-08-07). **What is left is the live run itself, and it is human-driven by design** (§6.2, and `livesession.run`'s docstring: no scripted input, the operator plays). **Re-specified 2026-08-06 — it used to read "proxy capture", which cannot work: the channel is DH-keyed end to end and a proxy holds neither private exponent. That is the same fact that forces us to patch the client for our own server.** |
| **R1.5** | **Tape player** | A recorded StoC stream replayed at recorded timing walks a real client through Ascalon | ✅ **2026-08-10**, `db924a4` — **and it walked through Ascalon City itself.** The full 48.6 s tape of connection `:60935` played **1,209 of 1,209 events, 74,319 B, with ZERO messages of our own on the channel** (measured, not assumed — the previous run's assert turned out to be our own world tick talking over the recording). The client skipped the cutscene, walked to each quest giver in order, spoke to them, accepted quests, and walked to the zone exit; chat arrived. **We still cannot name half the opcodes involved** — a tape needs no semantics, which is the whole point. It ended where a one-connection tape must: at the map transition, the client dialled `54.198.7.73:6112` from the recorded `GAME_SERVER_INFO` and the cage refused it (`Code=005`). See §3.4. **A second run the same day played Lakeside County (`:64103`, 1,074/1,074, 0 non-tape sends) and rendered COMBAT** — plus a labelled c2s corpus, and independent corroboration of D1's agent-id reuse from ArenaNet's own traffic. See §3.5 and [studies/tape/FINDINGS.md](studies/tape/FINDINGS.md). |
| **R-IDENTS** | **An identifier convention for new tokens, and a resolver for the old ones** | A token met in prose resolves to its defining document in one command, and a new namespace is minted with a registered word prefix | ✅ **2026-08-20**, arc landed `9697c8c`. The arc: [studies/idents/CONVENTION.md](studies/idents/CONVENTION.md) (the rule, and the only place it is written) + [studies/idents/HANDOFF.md](studies/idents/HANDOFF.md) (the census and the three defects — cross-arc collision, kind collision, and the same letter twice in one document). **The headline is a refusal**: a mass renumber of the existing tokens was costed and rejected as the exact shape of the 2026-08-12 provenance scrub, so nothing is migrated and every historical `C-6`, `R0a`, `H1` keeps its name. **Scope note:** the no-migration scope is owner-ratified — §7 Q8, CLOSED 2026-08-20. What landed instead: new tokens take a registered word prefix (`GATEFIRE-C3`) whose word names the *defining document* and is declared in a legend line in that document — the kind of thing a token is lives in the legend, never in the letter, because encoding kind in the letter is what produced the collisions in the first place; a resolver that works on the 80 documents written *before* the convention AND on the tokens it mints (`python toolkit/whichrung.py C-8`, plus the raw grep one-liner in CONVENTION.md §4, which is hyphen-literal and returns two of `C8`'s three row-or-heading defining sites and one of `C-8`'s — the tool returns all three and names the ambiguity, and a fourth definer, a bold list-lead in `studies/combat/PLAN.md`, sits outside both patterns, which is why every count is a floor); and an accumulation tripwire, `toolkit/identlint.py` + `test_identlint.py`, explicitly **not** a hard gate — provlint's posture, for provlint's reason. Two side findings: the R-ladder drift between `PLAN.md` §3 and `HANDOFF.md` was closed by **annotating in place**, not syncing (`HANDOFF.md:116`) — re-syncing two copies only resets the clock, and the `R0`→`R0a`/`R0b` split turned out to *vindicate* that document's own headline call; and the bare-integer commit-subject prefix (`29:`→…, defined by no document — no count is pinned, it grew by one between census and landing) is **retired** with its meaning recorded rather than rewritten. Census counts are floors: the widened re-run found several times HANDOFF §2.1's 108 defining sites, and quoting any number bare is refused — ask the tool. |

| **R-ISLE** | **The Isle of the Nameless as a calibration range** | Rungs per [studies/isle/PLAN.md](studies/isle/PLAN.md): reader, route, offline bench, loopback probes, plumbing, then the live sessions | 🔶 **rungs 1-5 DONE 2026-08-16/17**, landed `52c96ff`. The arc: [studies/isle/HANDOFF.md](studies/isle/HANDOFF.md) (**start here cold** — the traps, not the status) + [studies/isle/PLAN.md](studies/isle/PLAN.md) (the north-star doc: instruments, skeptic-attacked designs, the ladder) + [studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) (rung 3's eight offline answers; rung 4's four operator-confirmed probe results). Headlines: the AoE radii are static (`s_skill +0x6C`: adjacent 156 / nearby 240 / in-the-area 312, +10-16 bounding-radius hypothesis for the Isle markers to test); the Master of Damage's chat numbers are extractable AND rendered ("is now level 17!" on our own client — 0x5D needs its 0x5E tag); the enc_name → nameplate route is PROVEN (station 1470 = the Ascalon City outfitter, operator-read); conditions map 478=Bleeding..486=Weakness (+2077) with degen server-owned; the three damage kinds separate on the client bar (16/17 debit, 18 notifies); `agentroster.py` reads any capture into cross-session-stable stations; `map.280` is in content with the 0x0195 prediction pre-registered; a PvP-only character reaches 280 (owner-confirmed, GWW-corroborated — the ONE PvE area they may enter). **rung 6 is DONE 2026-08-17/18** across two live captures — `20260817T231139` (the island west and centre; 15/15 connections after the manifest-writeback fix) and `20260818T094648` (the east line, 5/5). Both `game_mode base`, `exe_unchanged: true`, seals AGREE. Results: `0x0195` field 1 = **165811 six times**, and it is a TERRAIN-FILE id shared with map 248, not a per-map id — the whole message is now decoded in [studies/mapload/FINDINGS.md](studies/mapload/FINDINGS.md) (7 fields, 30 loads, both builds; settles `studies/tape` §1.2, corrects a `0x0084EE83` misattribution in `studies/enemy`, and moved `map.280`'s spawn to retail's arrival position); field 2 is the arrival position, byte-identical across all Isle loads; **7 of 10 pre-registered missing definition indices** were found in the unwalked east (130, 139, 146 still unseen); the east holds the **skill-bar foe Masters with their pets and spirits** — level-0 model-less bodies with churning agent ids beside a level-20 owner, matching three separate pre-run wiki claims on profession, level and summon structure at once; the **Students** came out 10 bodies over 10 consecutive slots split exactly 5 ally / 5 foe; and the range ladder is closed (10 rungs, byte-identical across visits, ±12.4 u). Which body carries which NAME is NOT recoverable from a capture — the `enc_name` render is the only route, and a claim identifying one was withdrawn under adversarial review. **RUNG 7 IS DONE 2026-08-18** — capture `20260818T132739`, 9/9 decrypted, seals agree, 495 damage events, then five independent agents (one blind re-derivation, one wiki sourcing, two adversarial, one on the chat oracle) sent at the results. **The armour exponent B9 called NOT REACHED is now reached, and the whole outbound damage formula with it**: `points = round(roll × 1.20 × 2^((SL − AR)/40))` with SL = 5·rank to 12 then +2 per rank, pinned by a **band test with zero free parameters** (AR60's support fixes the scale; AR80 → 13..19 and AR100 → 9..14 follow exactly). The mean-ratio fit gives D = 39.5, 95% CI **[37.30, 42.00]** — containing 40 at −0.8σ/−0.1σ, and it must never be quoted bare, which is the review's sharpest correction. **`GV_CRITICAL = 17` is CONFIRMED**, ending a CONTESTED row: 10/10 blocks zero-variance over 100 events, one multiplier fitting nine blocks inside a 0.83% window containing √2, p16+p17 = one event per swing (so 17 REPLACES 16), and crit rate rising monotonically 6%→34% with attribute rank. **The Master of Damage oracle worked**: its announced total 1496 equals our independently summed integer points exactly and *selects* H=590 out of the fraction grid's `{590k}` family — a check that could have failed. **Gate 1's attribute channel is measured at last** (`0x0037 [agent, unspent, 200]`, `0x003A` column-major base|effective ranks, `0x003B` per-change, `0x0038` the debit): the +1 rune bonus is visible on the wire, damage uses the EFFECTIVE rank, and the point budget closes two unrelated ways to cum(12) = 97. **Four claims were corrected or refuted by the review and all are recorded**: the unmet-requirement `/3` is REFUTED at 3.5% with no replacement permitted (the rank-8 crit is a disjointness, not a rounding miss — the one open defect); the rank-kink ratio is statistically worthless (95% CI [−17, 24]) and is replaced by ratios of means at −0.8σ/+0.3σ; "continuous roll" is downgraded to "≥ ~40 steps"; and the 1496 line is an end-of-combat auto-report, not the `/bow` response (`/bow` is 4.46 s later). Full record: [studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) "Rung 7, LIVE #2". **Rung 8 PREP DONE the same day, and its exit criterion was MET OFFLINE** ([studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) "Rung 8 prep"): the design expected a refutation because `0x0042` had zero ArenaNet witnesses, and the corpus in fact holds **97 applies + 88 removals**, with `0x0044` closing `0x0042` at apply+duration to the millisecond. **Field 3 is the applier's ATTRIBUTE RANK** — confirmed on four skills against GWW progressions (Windborne Speed at the Master of Winds' 15 Air Magic → 13 s; `"Charge!"` at the operator's own Tactics 10 → 10 s; Pin Down's Crippled at rank 13 → 13 s; the environment torches at rank 0 → fixed 30 s) — so the two conditions where it equals the duration were arithmetic accident. **Hexes and enchantments, §3.3's "largest single miss … no instrument at all", were already captured and merely unidentified**: skill **984 = Torch Enchantment** and **998 = Torch Hex**, 30 s each, matching GWW's effect ids exactly. And the repo's **first cure** is on record — `"Charge!"` stripping Crippled in the same millisecond, its 33% speed boost visible as 288 × 1.33 on `0x0027`. Consumer built first again: `toolkit/authsrv/bufflog.py` (36 checks) reads episodes as EXPIRED / STRIPPED / OPEN and refuses to attribute an effect outside a mark window, since `0x0042` carries no source agent. **The live session is staged** (`vault/plans/isle_rung8_effects.txt`, 27 steps) for the four things the corpus cannot give: skill **999** (the degeneration torch, never captured), the five foe Students' condition ids, degeneration in pips against GWW's 3/4/4/7, and the rank ladder that closes rung 7's open defect. Prep detail: the consumer `toolkit/authsrv/damagepass.py` built and proven on retail bytes first — the rung-6 detour's PvP arenas turn out to hold the vault's largest damage corpus (641 p16 + 119 p17), which measured the attack-skill confound (10 of 11 arena p17 groups nonzero-variance) and recovered 480 = level-20 base health from a fraction grid; the bench geometry is recovered (Suits 152/153/154/152 in a row, the 60-pair predicted at its ends; MoD prof-6 candidates 144/145); the sealed-plan draft with every prediction pre-registered (including both weapon-type branches for the rank sweep) is staged at `vault/plans/isle_rung7_damage.txt`; and the blocking behavioural-cap question was ruled same-day — **§7 Q7, the cap is STRUCK** — so **the run itself is next and is the operator's**: RUNBOOK live procedure + `--minutes 45 --mode base --plan vault/plans/isle_rung7_damage.txt`. Bonus banked en route: the no-combat east run's one combat episode (operator hit by slot 137's Pin Down) shows **condition application arriving on `0x0042` on retail traffic** (481 Crippled, 13.0f duration-like arg, move speed halved server-side) — rung 8's Torches-first channel question observed once, early. Residuals riding the next loopback pass: the varint send, the overhead channel, skill 2077's render, the energy probe. **RUNG 8 IS DONE 2026-08-21**, across three short runs after the 27-step design proved unfollowable mid-session (`20260821T152147` effects, `20260821T155022` the last two conditions, `20260821T163511` the rank ladder). **Skill 999 observed** and the **condition map is COMPLETE** — all ten Students named to ids, 482 = Deep Wound confirmed by elimination and 2077 = Cracked Armor corroborated by GWW's own `<!--id:2077-->`. **The unmet-weapon-requirement penalty SCALES with rank**, closing rung 7's one open defect: PINNED dies on the distributions, not a fit — eleven 3s at rank 5 that PINNED cannot reach, and zero 6s at ranks 5/6/7 against twenty at rank 8 (`5.5e-10`). Means within 1.1%, r8 control at +0.5% of rung 7 on the same body, divisor **3.098 [3.073, 3.133]** which newly excludes 10/3. **§4's crit disjointness reproduced** on a different day and still unexplained. Two runbook traps landed with it: an ArenaNet build shipped mid-run and took the key-tap cave with it, and the build gate's "service" is `C:\gw`, which only updates when LAUNCHED — it refused a correct 38849 client as "stale", and following its own advice reproduces the zero-key failure. **Rung 8d, RECONCILED 2026-09-17 — its RE-CAST half is CLOSED, by a different run; its BENCH half is still owed.** 8d bundled two things. (1) The re-cast shape — skills §36.8's "our REMOVE-then-APPLY is unwitnessed either way" — was answered on the Isle by RUN-SKILLS-RB2 (`20260917T090355`, [studies/skills/FINDINGS.md](studies/skills/FINDINGS.md) §49.7) with other skills than the shout staged here: a recast ENCHANTMENT is a bare `0x0042` with a new buff id beside the old one, which closes on its own clock (Reversal of Fortune, 3 of 3, 8.000 s each), and a recast STANCE is `0x0044` then `0x0042` in one batch (Frenzy, 3 of 3); both are what the server already sends, so nothing shipped. The enchantment is the clean witness §36.9 wanted a shout for — no exclusivity rule, and it STACKS. A recast SHOUT is still n = 0, and nothing waits on it: `effects.EFFECT_TYPES` does not time shouts at all. (2) **The rank-13 bench block has NEVER run** — the requirement-MET in-run reference for the 3.098 divisor, ~80 s, [studies/isle/PLAN.md](studies/isle/PLAN.md)'s "one cheap gap"; it died with the aborted run and was riding on the re-staged one. So `isle_rung8d_recast_v2.txt` should NOT be run as staged — four of its nine steps (the tooltip gate and the three shout presses) re-measure a closed question; the bench block wants a plan of its own, or a line on the next Isle tape. The record as written 2026-08-22, when the rung was ~~OPEN and mid-flight~~: the first run (`20260821T184758`) was ABORTED by the operator at the tooltip step, correctly — the plan's skill pick ("348, already on the bar") was inferred from ambient town-capture effect episodes, and the bar's real shout was 364 `"Charge!"`, whose 20 s recharge against a 10-12 s duration can never overlap itself ([studies/skills/FINDINGS.md](studies/skills/FINDINGS.md) §36.9 — a scope error of §36.8's own family), and the rank-13 bench reference died with the abort. **The pick is now MEASURED and the plan re-staged** (§36.10): retail's `0x00DA SKILLBAR_UPDATE` is self-scoped, so the operator's own bar reads straight out of the corpus (`python toolkit/authsrv/adrenjoin.py --bars`, 58/58 against §34's census) — the newest capture (`20260821T205552`) shows slot 1 = **348 `"Watch Yourself!"`**, put there by the operator themselves for §33's spend-clock run, recharge 4 s < duration 10 s with CLIENT-DATA and WIKI agreeing by id join, and that same capture banks the single-press control episode (expired, 10.0 s, 14 ms residual). `vault/plans/isle_rung8d_recast_v2.txt` (9 steps, sha `5821fa75…` staged) runs the **rank-13 bench block FIRST** so a skill surprise cannot zero the run twice, rides the re-casts on the bench swings (every press its own `0x00D2`), and pre-registers GWW's ten-damage early-end as the one false-REPLACE channel. The run is the operator's: `--minutes 20 --mode base --plan vault/plans/isle_rung8d_recast_v2.txt`. ~~**Rung 9 is BLOCKED ON ITS ANALYSER**~~ **— THE ANALYSER IS BUILT (2026-08-22) and this row was stale for five days**, which is exactly the failure the top of `CLAUDE.md` is about: [studies/isle/PLAN.md](studies/isle/PLAN.md) §3.4 has carried the correction since, while §3 — the single status authority — still said BLOCKED. `toolkit/authsrv/respawn.py` + `test_respawn.py` exist and are green (46 checks), keyed on **(definition slot, spawn position) with a preceding-death bit** as ruled, with all three named traps defeated on real bytes and the naive answer exported so the test can DEMAND the disagreement (agent 38's 54.9 s phantom stays a phantom). The consumer-before-run rule that rungs 7 and 8 both paid for is satisfied. **What now stands between the arc and rung 9 is the RUN, not the instrument** — and per this row's own history, check `studies/isle/PLAN.md` before trusting this sentence. |
| **R-SLICE** | **The vertical slice** — outpost quest → Monk hero → zone → two monster types → corridor with 2+2 and a boss → return and complete, per [studies/slice/PLAN.md](studies/slice/PLAN.md) §0 | The six steps run end to end by the owner's hand on a retail client, with the hero walking, fighting and healing beside the player | ✅ **2026-09-12** the six steps (the owner's first full run, SLICE-F18, `git log` 2026-09-12 on `main`); ✅ **2026-09-13** the hero ladder **H1–H8 landed**, `8fe17d71` (merge of `slice` at `519ce042`): `--party slice` gives a Monk hero from content that walks retail's formation, fights the leader's target, obeys the commander's stance/lock/flag, crosses the transfer, holds a staff, and the whole corridor plays at level 2–3 on retail's single-digit damage (SLICE-F28..F34). Status detail is the arc's own tables: `studies/slice/PLAN.md` §2 (B1–B9), §7 (C1–C9, H1–H8). The owner's hand pass at level 3 on the sword bar (H9–H11) landed the same evening: "the skills work as advertised. the bandit quest was completable". Open there: H2d (Party Search's Heroes tab assert, a residual). ✅ **2026-09-13 MANTID-S** (SLICE-F38): the Factions tutorial tape's four corrections landed — the effect list is the player's own, a hex's auras and trigger damage, Ether Feast, skills granted mid-map |
| **R-SANDBOX** | **The run orchestrator** — the slice as a practice sandbox: the character's profession pair, level, bar, ranks and unlocks; up to seven heroes each with its own body, profession, bar and ranks; up to four hostile groups of up to four with a boss; from a window, per [studies/sandbox/PLAN.md](studies/sandbox/PLAN.md) | A spec through the window plays the slice's loop on a retail client with every knob changed at once | 🔶 **2026-09-20, SANDBOX-B1..B5 landed offline**, `b2a910aa` (merge of `sandbox` at `60f913a7`): `toolkit/harness/sandbox.py` compiles a spec into a content overlay (`RURIK_CONTENT_EXTRA`, merged last for one launch), the gamesrv flags and the harness command (`test_sandbox` 88); `[[party.KEY.heroes]]` gives each hero its own row (`HERO_ROWS`, `hero_*()` readers); `player_secondary` / `--spawn-secondary` carry the pair; `tools/orchestrator/orchestrator.py` + `apps/orchestrator.pyw` is the window (`--smoke` 20 of 20). The server accepted the generated overlay at startup with no client (the party row, its hero table, seven spawn rows, the rig). **2026-09-22, SANDBOX-B7 landed offline**, `51bc5291` (merge of `sandbox` at `036dc3f4`): the in-game panels own the bars and ranks — the window's Player/Heroes tabs became **Skills** (the account library) and **Party** (the character; which heroes are unlocked, each a profession, body, level), a sandbox run always passes `--persist`, a hero's body casts its STORED bar and follows an in-game edit at once, a hero row carries its points budget, an authored empty bar or rank list is honoured as empty, and the party row's level wins over the store's seed (`test_sandbox` 107). **2026-09-24, the window restyled offline** (branch `orch-beauty`, fix passes through `35204d99`; PLAN-LOG): Dream-World-IX's GUI laws — a derived, audited two-theme palette, cards, one accent — taken through four adversarial review rounds; `--smoke` 21 → 163 laws through `checks.py`'s ledger (floor 145, each fix's law proven red; template labels capped so operator content of any length keeps the layout), `test_orchtheme` 37; and `sandbox.validate` then refused a hostile level outside 0..20 and held a hostile's ranks to validity (its template's profession, each rank within the table — **both hostile caps SUPERSEDED the same day, lifted to 0..255 / 0..21 below**) — **the owner ruled the same day, "exempt hostiles from the rank budget"** (branch `orch-beauty` on `f93fa30f`; PLAN-LOG "R-SANDBOX, hostiles exempt from the point budget"): the point budget is the player's and a hero's only, a hostile's ranks are never held to it, and the window's Attributes chip counts the spend without judging it (`test_sandbox` 129, `--smoke` 165 in both themes, each inverted law proven red; the verifier's fixes -- the roster line's count law, a malformed pair and an id outside the table witnessed on a hostile -- each red under its plant). **The same day, the owner's second ruling, "lift the rank and level caps for hostiles too"** (PLAN-LOG "R-SANDBOX, hostile level and rank caps lifted"): a hostile's level 0..255 (`HOSTILE_LEVEL_MAX`, the wire's `0x0056` level byte, tied to the schema by a check) and ranks 0..21 (`HOSTILE_RANK_MAX`, retail's ceiling; WIKI, GWW "Attribute" §Notes rev. 2026-09-02, as the owner quoted it -- 20 through runes and skills, +1 from 20%-chance items -- and the client witnessed at 15), constants of their own beside the player's and a hero's unchanged 1..20 / 0..12 (four controls added), one client definition per (template, level) in `spawn_rows` (RECONSTRUCTION), the Attributes chip pricing to the table's 12 and counting the ranks past it (`test_sandbox` 139, `--smoke` 174 in both themes, floor 150; every changed check red under its plant; the verifier's fixes, PLAN-LOG "R-SANDBOX, hostile caps lifted: the verifier's fixes" — `validate` refuses ONE member past both caps for both (`if tmpl:`, the `elif` hid the rank reason; `test_sandbox` 140), the spin-fit law pins each Ranks spin's maximum at '21' and prints what it measured, the displayed-level half of the definition defect labelled RECONSTRUCTION, and the two open items named in §8.1). **The same day, the server-load level guard** (PLAN-LOG "R-SANDBOX, the server-load level guard"; the lift's residue (a) closed, the level-0 quirk stays open): a content row or fixture whose effective level `0x0056`'s byte cannot carry is refused when the server STARTS -- `area_population` for an area's rows (the row's level, else its template's), `fixture_level_guards` for the test enemy, every 0x0056 step of a `--probe` built at startup as it will fire (the verifier's fix, PLAN-LOG "R-SANDBOX, the server-load level guard: the verifier's fixes" -- the first cut checked the hatcher under any probe and its log line claimed a quest probe's vault template fit; the last line's text now names the send, two controls test the literal 255), the henchman's and each hero's body, `create_agent_world` as the last line -- the range read off the schema and pinned to `HOSTILE_LEVEL_MAX` by the test (`test_population` 75 → 106 → 114, thirteen plants red). **Open: SANDBOX-B6, the owner's first run, and U1–U5 on the client** — what it draws for a secondary, two heroes in two bodies, a body of another profession, a four-strong group's pull, a build made entirely in-game surviving a run. **The same day, SANDBOX-N1 landed offline** (the owner's 2026-09-22 ask, "a better/filterable skill/attribute selector" for the enemies; branch `orch-beauty` `3e397421`..`9925c586`, main merged in at `69243d13`; PLAN-LOG "SANDBOX-N1, the Enemies tab's skill and attribute selector"): each hostile's eight skill combos became a Skill bar -- eight wells showing each skill's attribute and the rank the server ACTS at (`sandbox.effective_rank`, text-locked to `agent_skill_rank` and the create path: 12 with no ranks on the row or its template, else the attribute's rank or 0) over an inline, filterable library (search, profession, 'Modelled or label'; tick, double-click, drag, or type and Return) -- and the Attributes card one attribute to a row with 'N on the bar' chips that warn at rank 0; the window's range is the compiler's (Open and a template change hold off-profession and unknown ids that the combos dropped in silence; a hostile's unedited keys such as `weapon_attribute` ride through Save); the server's create path reads a template's ranks in both shapes (`rank_pairs`); `validate` refuses a hostile with more than 8 skills. Three designs, three adversarial verifiers (35 findings, two blockers: laws that could not fail), every changed behaviour red under its plant (`--smoke` 177 → 208 in both themes, floor 153 → 170 with 38 gated; `test_sandbox` 140 → 156; `test_population` 114 → 116); opening the example spec 6.3 → 1.1 s, sixteen hostiles 20.5 → 3.3 s. **N2**, hero add/kick from the party panel, shipped (DESKWORK-D1 steps 1 + 4) and was confirmed on our client 2026-09-23. **2026-09-25, SANDBOX-F4, a heroless spec starts** (`61c9dfbd`; PLAN-LOG "SANDBOX-F4, the heroless party"): it died at startup on `KeyError: 'hero'` (harness `20260925T161150`), since TOML writes no empty `[[party.sandbox.heroes]]` and `main()` took the missing list for the single-hero shape; the compiler writes `heroes = []` and `main()` reads a row with neither key as the player alone (`test_sandbox` 156 → 158; `test_partyrow` 15, which drives `main()` itself through `--list-probes`); **CONFIRMED the same day from the window on the client** (harness `20260925T170126`, the Launch button on a spec with no heroes: `PLAYER_PARTY_SIZE(1)`, no hero record, PASS; PLAN-LOG "SANDBOX-F4, CONFIRMED from the orchestrator"). |

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
  Flare 194, Healing Signet 1, Sever Artery 382, …). **Today n = 8 of 9 on the episode reading and 3 of 9 on the mechanic reading, 2026-08-20 — and which of those the criterion means is an OWNER RULING this rung now needs.** Eight of the nine families apply, render, time and expire at the client; three of them (Spell, Signet, Attack) also do what the skill says, and the ninth is Charm Animal, whose effect is a pet. §3's R4b row carries both numbers, the per-family table and the argument. Nine and not 21
  because the other twelve codes have no Pre-Searing content to test against; grading
  against 21 would grade v1 against non-v1 content.
- **R4c — split, because the two halves are reached by different instruments and reporting
  one number hides which.**
  *R4c-1, capture-free*: 19 of 19 map rows with resolved file ids and arrival points that
  pass the spawn-in-trapezoid test, ≥15 NPC templates, 2 of 2 mandatory quests completable,
  6 of 6 quest verbs implemented, 4 of 4 services working. **Today the content store holds
  19 map rows and 63 NPC rows** (`toolkit/content.py`'s own census with this machine's
  vault overlay, re-run **2026-09-24**: map 19, npc 63, item 28, spawn 23, area 25, quest 2,
  skill_effect 113 — was map 10, npc 56 on 2026-08-14 and map 15, npc 56 on 2026-08-27).
  **The tracked census** (`content/*.toml` and `content/overrides/` alone, no vault, which
  `toolkit/test_checks.py` recomputes and reddens on when this line disagrees): map 19,
  npc 9. **Read the NPC figure carefully before scoring R4c-1 against it**: only **9** of
  the 63 are tracked in `content/npcs.toml`; the other **54** are the gitignored
  `vault/content/npcs.toml` overlay `npcdefs.py` emits, with no name, armor, energy or
  allegiance (that module's own header says so). So the "≥15 NPC templates" bar is met on
  the count and **not** on the content, which is the distinction this criterion exists to
  force. Every map row carries a `file_id` and a `spawn_x`/`spawn_y`. ~~**How many
  of the nine pass the trapezoid test has not been re-run**, so the map figure is a row
  count and not yet a score against this criterion.~~ **RE-RUN 2026-08-27, and it is a
  SCORE now: 8 of 15** ([toolkit/mapdata/spawncheck.py](toolkit/mapdata/spawncheck.py),
  `test_spawncheck.py`, floor 44). **RE-RUN 2026-09-24 over the store's 19 rows — not the
  criterion's 19 Pre-Searing zones, which is the same number by coincidence — against the
  study archive (the tool's default): 11 of 19** — PASS 9, SEAM 2, OFF-MESH 3, WRONG-PLANE 1,
  UNRESOLVED 4 (the four created chains 165–168); the one `(0,0)` PASS is still Sparkfly
  Swamp's. The rest of this paragraph describes the 2026-08-27 run. Nine had become fifteen, and one number was hiding four
  different failures, so the verdict is five-valued: **PASS 6, SEAM 2, OFF-MESH 3,
  WRONG-PLANE 1, UNRESOLVED 3.** Four things the score does not say on its own, each of
  which is the reason its own token exists. (1) **The criterion's own premise has an
  unstated boundary case.** `content/maps.toml`'s header says "EXACTLY ONE is what a
  non-overlapping tiling gives", but `Trapezoid.contains` closes both y bounds *and* both
  x bounds, so a point on a seam between two neighbours is in both — maps 143 and 144 sit
  exactly on one, at the authored `(1536, 1536)`, and one unit either way returns 1. That
  is walkable ground and a pass; `SEAM` is a pass with a name, not a failure. (2) **The
  three UNRESOLVED rows are the created chains** (165/166/167), and "not in the archive"
  turned out to mean "not in the *study* archive" — `--find-missing` puts all three in
  exactly one place, `vault/run/2026-07-29_221c13772c7a-probe/Gw.dat`, a 38797-era probe
  directory and **none of the current run dirs**. Whether that matters is a question for
  WORLDMAPS, but it is a fact about deployment and not about the maps. (3) **Four of the
  five `(0,0)` placeholder rows fail honestly and one does not** — Sparkfly Swamp's origin
  happens to be walkable ground and scores a clean PASS. A placeholder that passes is
  worse than one that fails, because it looks verified; the count is asserted so the day
  somebody promotes that row the check says which greens were earned. (4) **Domain of
  Anguish's `(0,0)` is contained but not on the `plane = 0` its row declares.** Seven of
  seven deliberate mutations of the scorer turn the test red, including two that escaped
  the first pass and were both real defects rather than missing assertions — one of them a
  *vertical* seam being condemned as an overlap. The printed "(today 2)" and "(today 1)"
  were true when written and were never updated; the map-row count in the census line
  above was stale then too — `content.py` read **map 15, npc 56** on 2026-08-27 — and was
  refreshed 2026-09-24, when its tracked half became a check.
  *R4c-2, formerly capture-gated*: 35–40 monster types with real stats and skill bars,
  graded on **types, never on spawn instances** — spawn counts are unstatable from any
  source this project has.
  **R4c-2 IS NOT BLOCKED — IT IS UNGRADEABLE, which is worse and is now measured.**
  ⚠️ **Its criterion cannot be evaluated as written, and one clause can never be met.**
  Full verdict: [studies/presearing/R4C2-FEASIBILITY.md](studies/presearing/R4C2-FEASIBILITY.md),
  which proposes a three-way split (R4c-2a roster / R4c-2b evidence / R4c-2c the name join)
  **and is a proposal until the owner adopts it**, exactly as the two rewrites above are.
  The four clauses, measured over the canonical 12-connection corpus:
  - *"35–40 monster types"* — ~~**today 7** hostile definition slots (1346, 1420, 1421, 1431,
    1432, 1434, 1442), all from one 568 s visit to one map.~~ **RE-MEASURED 2026-08-27:
    the corpus now pools 16 captures and 266 definitions, of which 31 are hostile, and
    `unitassembly.py` closes 266 of 266. READ THAT CAREFULLY — it is NOT "31 of 35".**
    The growth is almost entirely **Isle of the Nameless**: the new block at indices
    129-165 is the calibration range's furniture (the Suits at 152/153/154, the Master
    of Damage candidates at 144/145, and 130/139/146 among R-ISLE's own pre-registered
    indices). **The PRE-SEARING hostile roster — which is what this criterion grades —
    is still the original seven.** Reporting 31 against a 35 denominator counts the
    training dummies, which is §6 item 9's named error. What did genuinely improve:
    health readings went from 3 to 15, attack rates from 4 to 20, model ids to 245, and
    the extractor held at 5× its original corpus with 0 problems. **RE-COUNTED 2026-09-24
    PER BUILD (DESKWORK-Q5, PLAN-LOG):** `npcdefs` refuses a pool spanning client builds (7809
    is a different creature in 2026-07-29 and 2026-09-01, the only one of 38 shared indices whose
    body differs); the September map-146 tapes (5 connections, build 38888) create **13 hostile
    definition slots** — six of the original seven (1434 absent) plus 1397, 1405, 1409, 1411,
    1428, 1433, 1437 — **4 of them with a stat past the declaration**; the 40 hostile in the
    whole September pool are mostly the Isle's and map 430's furniture, so "40 of 35" would be
    §6 item 9's error again (R4C2-FEASIBILITY §7.4). Full re-measurement
    and the stale-claim list: [studies/presearing/R4C2-FEASIBILITY.md](studies/presearing/R4C2-FEASIBILITY.md) §7. Coverage-blocked; a live capture
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
Seed from `build-wars/gw-skilldata` (repository MIT; its DATA is GFDL / CC BY-NC-SA from the
source wikis — README §Licensing, verified 2026-09-22; the owner's own archive's description
templates are now the primary source, skills §54, and the dataset the fallback). Cross-check every numeric field against
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
> from git against this document's own commit (`1617071`, 2026-08-04 19:56): the Days 1–14
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
| **Client auto-patches over ground truth, and the DH keys rotate with it** | **This happened during the session that wrote this document.** The updater replaced `Gw.exe` (10,404,032 → 10,483,904 bytes) and `Gw.dat`, moved the DH struct from RVA `0x6843e8` to `0x6910d8`, and **changed both the prime and the server's public key**. ArenaNet rotates the Diffie-Hellman parameters per build — which is why Headquarter stores 107 server keys rather than one constant. Consequences: the client patch is a permanent recurring step, not a one-time one; every capture and schema revision must carry a build id (free, per §2); and re-snapshot *before* accepting an update prompt, never after. Both builds are now vaulted. **COSTED 2026-08-12, [studies/crossbuild/FINDINGS.md](studies/crossbuild/FINDINGS.md): 64 build-coupled addresses in `toolkit/`, 7 files** — not the 409 one draft claimed nor the 30 §1c of the review estimated, both of which reproduce under no stated method. **28 are converted** and re-verified against both vaulted builds by tests — `msgshape`'s 25 tables, `asserts`' callee, and `avevents`' two allocators, the last of which are now located by ArenaNet's own `AvChar.cpp` asserts rather than by address; **30 are GATED** — `genericvalue.py`'s 27, which read their jump tables out of the instruction that jumps through them and REFUSE on a build they were not measured on (exit 2, not a traceback), and the 3 RVAs in `itemprobe`/`agentprobe`, which dereference into a *running* client and refuse unless the target hashes to the right build; **5 are ACCEPTED**, hash-scoped facts about our own patch. **That verdict was "Zero outstanding: the per-update cost of this surface is now nil — every site either re-derives or refuses, and none can return a silent wrong answer", and it is WITHDRAWN as of 2026-08-29.** It was measured over the 7-file surface above and has never been re-measured; the surface is now **233 class-(a) sites across 21 files**, and paying that bill produced two counterexamples on the day it was paid. **`gatetrace.py`'s three VAs — CLOSED 2026-08-30.** They were guarded by hand-typed byte patterns occurring 14,765 / 94 / 531 times in `.text`, under a control that moved a different constant — point all three at decoys four megabytes away and the section stayed 9 of 9 green — and `test_gatetrace._pinned_exe()` hardcoded the 38797 vault path instead of resolving through `pinned.find()`, so it could never read a newer build nor redden on a rebase. `test_gatetrace.py` §1 now resolves through `pinned.find(gatetrace.BUILD)`, hangs its four derived rows off `VA_APPLIER` as offsets, widens each VA pattern until it is MEASURED to occur exactly once in `.text` (30, 8 and 21 bytes) and re-measures that every run, and carries one control per counted pin — including `BUILD`, which reads every other vaulted build through the same `find()` and requires every row to fail there. The decoy reproduction now yields 10 FAILs; the file goes 44 checks to 51 with its bare-machine floor unchanged at 35, and the census is unmoved at 233 (class (c) drops 446 → 443). **`compositetrap.py`'s `UPSTREAM_CALLERS` -- CLOSED 2026-08-30.** Nine of its eleven keys were call-site VAs matched against RETURN addresses off `[ebp+4]`, so nine could never fire; the two that ever named an answer are the two that were MEASURED off a live frame rather than read off a disassembly. Every check the map had was a dict-membership or count check against fixtures carrying the same literals, while the pinned-image byte check guarding the sibling `WRITER_CALLERS` was never pointed at it. Re-keyed to `call + 5` rather than deleted -- the 233 -> 224 reduction was available and NOT taken, because the nine had never fired only because they could not: every function in the chain carries a frame pointer, so `walk_frames(depth=4)` reaches them, and deleting would have left the `UiChInfo` path reporting itself as `an unlisted path, which is a result`. `test_compositetrap.py` §6 now decodes every key of BOTH maps out of the pinned image and re-DERIVES the two caller sets from it (every `call 0x0082D6A0` inside the per-slot worker's 0x17E bytes -- exactly seven of forty -- and every `call 0x004B1800` in the image -- exactly two); 102 checks to 105, census unmoved at 233. Full record: [studies/playercomposite/FINDINGS.md](studies/playercomposite/FINDINGS.md) §9.25. Both defects degraded quietly rather than loudly, which is exactly what the withdrawn sentence promised could not happen, and both are now fixed. The claim needs re-costing over the 21-file surface before it is restated; `toolkit/test_buildpins.py`'s changelog carries the per-file detail. What still recurs is not in the census: the DH parameters rotate every build, so the client patch is permanent, and the schema and captures still need a build stamp. The recurring cost that no census can see still dominates: the DH parameters rotate every build, so the client patch is permanent. | **233 addresses across 21 files; re-cost outstanding** |
| **The client phones home when it crashes** | `Gw.exe` embeds Sentry: `SENTRY_DSN`, `sentry.native`, `getsentry`, `x-sentry-rate-limits` are all present **[measured]**. The working method here is inject, patch, malform, crash — so the client's own outbound reporting channel is a posture problem HANDOFF §9 never considered, since §9 reasons only about server-side visibility. Neutralise it before the first malformed packet: block the endpoint at the firewall or null the DSN in the patched copy. Minutes, and it belongs on the R0 checklist next to the vault snapshot. | minutes |
| **The captures contain the owner's real ArenaNet credential** | The client sends its saved password to our own webgate on every login, and `vault/captures/portal/*.jsonl` records it as base64 — `<Password>…</Password>`, reversible in one command **[measured 2026-08-04]**. It has never been in git: `vault/` was gitignored in the first commit, before any content existed, so there is no history to rewrite and "private repo" does not bear on it either way. ~~**Owner's decision, 2026-08-05: the repo stays private, and a credential-scrubbing / anonymising pass is a gate before any public push**~~ — **SUPERSEDED 2026-09-07 by §7 Q16: the repo goes public and the gate is discharged** by [studies/prepub/FINDINGS.md](studies/prepub/FINDINGS.md), which verified across all 2,645 commits that no vault file, capture or key was ever committed, and which found and fixed the real exposure — a recoverable form of the account address pinned in `sessionstore.py`/`test_handshake.py`, not the captures. **None of this changes capture fidelity**, which still depends on recording what the client actually sent, and **the vault is still the only copy and still stays local** — publishing the source does not publish it. | ✅ **resolved 2026-09-07** (§7 Q16) |
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
| `toolkit/authsrv/probecombat.py` ALLEGIANCE constants (`toolkit/authsrv/probes.py` until the 2026-09-11 split; `probes.py` re-exports them) | four-byte tokens `'play'`, `'nonc'`, `'mons'` | — | ✅ confirmed against our own client; **JUDGEMENT:** short functional identifiers of this kind are facts about the wire, not expression. **Row re-aimed 2026-09-11, BEFORE the constants moved**, which is the order CLAUDE.md asks for and the only order that works here: `derivlint.py` keys on the UPSTREAM and not the module, so a row naming a file the constants have left stays **green** while pointing at nothing. That is the `gwdat.py` shape — a rule nothing checks is a wish — arriving through a refactor instead of through a new dependency. |
| `toolkit/mapdata/atex.py` | nothing — authored from our own record walk | — | ✅ checked 2026-08-06, clean |
| `toolkit/mapdata/dxt1.py` | nothing — DXT1/BC1 is a publicly documented format | — | ✅ checked 2026-08-06, clean |
| `toolkit/mapdata/datwrite.py`, `datplan.py` | nothing declared | — | ✅ checked 2026-08-06, no derivation statement and none needed |
| `toolkit/harness/wirecapture.py` | WinDivert (the packet backend, called via `ctypes`) | **LGPLv3** or a commercial licence; dynamic-linked, not vendored, used locally and never redistributed | ✅ carve-out pinned 2026-08-07 (CLAUDE.md): live driver **only**, never the server path or the suite. No WinDivert code is copied — only its documented DLL API is called. `keytap.py` takes no dependency. |
| `tools/viewer/modelviewer.py`, `tools/orchestrator/orchestrator.py` (2026-09-20, the same terms), `tools/orchestrator/orchui.py` (2026-09-23, the same terms; its sibling `orchtheme.py` is stdlib and imports nothing from Qt) | **PySide6** (Qt for Python) — imported as the GUI toolkit; nothing is derived from it | **LGPLv3** (or a commercial licence); dynamic-linked from the machine's own install, never vendored, used locally, never redistributed | ✅ 2026-09-14: lives under `tools/` beside `tools/blender/`, OUTSIDE the stdlib rule, and no line under `toolkit/` imports it. Every archive fact the viewer draws comes from `toolkit/mapdata/modelcatalog.py` (stdlib, read-only, `test_modelcatalog.py` 66 checks), so the dependency sits on the picture and not on a single measurement. Credited in `THIRD-PARTY-NOTICES.md`. |
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

**Q9. Does the movement composite become the shipped default?** ✅ **CLOSED
2026-08-22, by the owner: YES — `--zero-lead --grant-suppress --plane-carry` are ON
by default, with `--no-*` opt-outs kept for A/B work.** Asked and ruled the same day
REALFIX-L9 demonstrated the save (33 escaping full-lead click grants under the
composite, 0 warps; per-fired-grant Fisher 0.0023 against the control's 7/27) and the
costs were priced on L9's own captures (drift and model motion statistically identical
to the control, zero rejected reports, wire at half retail's own grant cadence).
`--plane-carry` rides the ruling on REALFIX-L4's demonstration and L8's counter-case
(its absence let the plane echo fire at a boundary). The one unpriced cell, stated at
the asking: enemies present — every warp run used `--no-enemy` or the town; the
position model those consumers read is measured identical, and normal play will
surface any residue immediately. Implementation: module globals still default False;
`main()`'s argparse layer resolves three-state flags (absent → ON, `--no-*` → off,
`--plane-carry` follows `--zero-lead`), the full pre-registration banners print only
when a flag is passed EXPLICITLY (the default path prints one line each — the
9.8 KB of banner text was wedging any consumer that spawns the server over an
undrained pipe, which `test_handshake` found within the hour), and the refuted-arm
refusals now name `--no-zero-lead` in their hint. Tests: `test_position_trust` 216
green with its three banner anchors taught the resolved-local shape;
`test_grantsim`/`test_grantsuppress`/`test_srclint` green;
`test_handshake`'s residual red is the pre-existing build-38849 vault drift,
byte-identical on `main`, not this change.

**Q10. Is a movement fix that warps acceptable?** ✅ **CLOSED 2026-08-25, by the
owner: NO — "the stock game doesn't warp, i am not going to accept a fix that
still warps."** Asked implicitly by CANCELWALK-R8's result (the `--cast-stop`
halt fixes F28's float-forward 3 of 3 but lands the body on the sync copy — a
backward warp equal to the copy's staleness, F31, 110–207 u measured), and
ruled the day it was reported. The ruling is general in shape: retail's bar is
stop-IN-PLACE, and a candidate whose visible cost is a warp is refused
regardless of what it fixes. Consequences: `--cast-stop=halt` stays runnable
as a measured diagnostic and R10's control arm, REFUSED as a ship;
`--cast-stop=pin` (CANCELWALK-R10, wired 2026-08-25) is the no-warp
candidate — a dead-reckoned `0x002C` hard-set at the body's true position
before the halt — **and it MET the bar: after two clean owner runs the
owner ruled the same day (2026-08-25, CANCELWALK.md §8.3g, “pin it”) —
pin is the SHIPPED DEFAULT (`--no-cast-stop` reverts) and F28 CLOSES**;
and the grant-cadence staleness itself (F27/F33/F35, sep to 864 u
measured) is the standing debt this ruling prices for REALFIX too:
any candidate there that expresses staleness as a snap fails the same bar.

**Q11. Which `RESYNC_SEPARATION` — 100.0 or 299.33?** ✅ **CLOSED 2026-08-25,
delegated by the owner ("reconcile RESYNC_SEPARATION") and ruled in-session:
100.0, everywhere.** The tree held two defaults for one dial — `authsrv.py`
100.0 (the client's own "close enough" radius, 3× under gate 1), 
`resyncscore.py` 299.332591 (gate 1's cut, argued as "the last moment at
which a snap is not already earned") — and the follow-on recon flagged that
under HOLE B **the threshold IS the residual snap magnitude**, i.e. the thing
Q10 judges. The fence lost on the decisive measurement of the **differential
band [100, 299.33)**: 120 of 157 shipped-regime fires sit in it (p50
143.7 u), every one refused at the fence, each leaving a HOLE-B residual —
and the fence's fire set is a strict subset of 100's (fence-only fires 0 of
558), so the band is pure addition. (The ruling's first draft argued from
F35's drag magnitudes — "the fence never fires" — and was refuted by its own
adversarial review the same day: the fence fires at F35's 512.9 u arming
report and the short-circuit turns that into prevention; the verdict fires
on arming-report staleness, never on drag size. The conclusion survived on
the band.) Its supports were also measured off-target — "no coverage lost"
was over hard jumps only (and reverses on `182652`: the 100 u cell covers
13/13 vs the fence's 12/13), and the retail-rate argument prices traffic the
rule never runs on. Wired and tested the same day: both files at 100.0,
`test_resyncscore.py` §0 pins their agreement, §13 pins both threshold cells.
Full record: `studies/movement/followon-notes/p5-resync-disarm.md` §4.2a's
ruling block.

**Q12. The four MOVECODE process questions — how does a hook arc carry the
repo's discipline?** ✅ **CLOSED 2026-08-26, by the owner**, all four at once
("your recommendations are all good"). Posed in `studies/movecode/PLAN.md` §6
before the first native commit, which is where that doc says to pose them.

- **(a) Client-derived constants go in `content/*.toml` with
  `source = "client-table"`, not in a plain Python module.** The reason is
  enforcement, not taste: a TOML row inherits `content.py`'s refusals
  automatically — the extractor must be named and present, and
  `NEEDS_BUILD = {"client-table"}` forces the build stamp — while a Python
  constant inherits **nothing** and needs the whole discipline hand-copied. "A
  rule nothing checks is a wish." The C hook takes its addresses from a header
  generated off the same rows, so there is one home for the fact. **The one
  thing that is refused is SPLITTING** one struct's offsets across both homes;
  if the generation step proves too expensive, keep them in one Python module
  and say so out loud instead.
- **(b) A hook DLL DOES need a `test_*.py`.** `trnhook/` has none and `srclint`
  therefore imposes nothing on it — that was silence, and it is now a ruling.
  The hook is the arc's instrument and its whole output is a ledger; a hook that
  silently mis-captures makes every downstream number wrong with nothing to say
  so. The shape is already proven and cheap: `test_commandertrap.py` exercises
  its debugger plumbing against a throwaway 32-bit `cmd.exe` under WOW64
  (`C:\Windows\SysWOW64\cmd.exe`), reserving `LEDGER.skip` for the sections that
  genuinely need the vaulted client — so build, inject and read-back are all
  testable with the game not running, and a bare machine skips instead of failing.
- **(c) The capstone/pefile carve-out stays FILE-SCOPED.** It names
  `msghandler.py` and `codescan.py` and it is not widened to a category, because
  the category would erode the guarantee it was scoped for: the fixed-byte-pattern
  tools (`asserts.py`, `msgshape.py`, `areatable.py`, `genericvalue.py`) must keep
  working on a bare machine. When something new needs a disassembler, fold the
  capability into `codescan.py` — as MOVECODE-B1's `--bit` did, which is why B1
  needed no ruling here — or add that one filename explicitly.
- **(d) The hook stays HAND-ROLLED; no MinHook, no Detours, and no §6.1 row is
  owed.** A library's real cost is the second gate (a derivation-register row and
  a notices entry *before a line imports it*), and it buys a length-disassembler
  this arc can avoid needing. **The design consequence is the load-bearing half:
  prefer FUNCTION ENTRIES as hook sites, so the persistent-`int3` handler
  re-emulates one standard prologue shape rather than an arbitrary instruction per
  site.** Concretely — hook the entry of the teleport `0x006020B0` rather than the
  branch `0x0060029F` (7 bytes, mid-function): the branch's only CLEAR-path
  consequence *is* that call, so the ledger is the same and the emulation is one
  shape instead of several. `trnblock.c`'s proven pattern re-emulates a
  `call rel32`; every site shape beyond that is new code, and the site list should
  be chosen to keep that number at one.

**Q13. Do we turn `D1_LEAD` on, now that the cost of leaving it off is measured?**
✅ **RULED 2026-09-05 — the owner: "turn `D1_LEAD` on by default." Landed as
MOVECODE-1z-bu ([§1z-bu](studies/movecode/FINDINGS.md)), applied to the lead this
question's evidence is about: `KBD_SYNC_LEAD_ON`, 1z-t's 520 u navmesh-clipped
keyboard lead behind `--kbd-lead`, opt-in since 1z-u — now ON by default,
`--no-kbd-lead` reverting, `--kbd-lead` parsing as a no-op. The shipped default
is RUN-1zBO's configuration exactly (zero `0x002C`, 0 of 7 legs thrown back,
separation 13.0 u; RUN-1zBP the revert arm; the waiver since deleted, 1z-bt).
STATED ASSUMPTION, and read it, because this question's own body twice calls
itself "the bundle question": the symbol `D1_LEAD` in the title names
REALFIX-A2's 766 u *unclipped* four-term bundle of 2026-08 (`--d1-lead`). It
stays opt-in for reasons that are about the code, not the flag count: (i)
`D1_LEAD` WINS when both leads are set (the 0x003D arm's first branch), so a
literal flip would make the 520 u measured lead unreachable and RUN-1zBO would
stop being the default's witness; (ii) the 1z-y gates that justified the lead's
return are keyboard-only — the hold is gated `and not D1_LEAD`, the kill arms
only `a2_src == "kbd"` — so D1 by default ships a lead at 1.49× the client's
trigger with exactly the maturation failure 1z-u convicted; (iii) its click
half (`a2_click_leg`) is unreachable under the router, which is what §1z-v
shipped instead; (iv) it parses alone today — `--zero-lead` and
`--plane-carry` resolve ON at run time, an earlier owner ruling — but a real
default needs `--no-d1-lead`, a resolved value fed to the composition matrix
(the send site reads the global, the matrix reads the argument), and a
router×d1 composition rule that does not exist. If the owner meant that
bundle, say so: it is its own arc.**

*(As it stood before the ruling:)* **Its blocking precondition is now MET (2026-09-05, §1z-bo).** §1z-bm reduced this
from a trade-off to a precondition — the lead earns retail-class tracking and the
warp came from the guard's re-pin, not from the lead — and RUN-1zBO ran the lead ON
under §1z-bn's fix: **zero `0x002C`, zero legs thrown back, tracking held at 13.0 u**.
The remaining caveats are in §1z-bo.4 (one state-matched trial, not four) and the
revert arm has never been run.
⏳ **OPEN — and its "cheapest item" was DERIVED 2026-09-03 and is not a fix
([studies/movecode/FINDINGS.md](studies/movecode/FINDINGS.md) §1z-u).** The
operator's ordinary session reproduced the refusals at 40 of 40 (`geo-stale`).
Widening the 1.0 s window is dead by arithmetic (click ages 15–21 s; only ≥ 23 s
answers all, past retail's 20.99 s max); the gate protects no plane word; retail
has no freshness precondition. `--click-echo` — the only surviving bypass — was
refuted as a default on three lenses (does not fix the session, plane-lock
hazard off map 146, no-clip on long clicks). **The click path's derived answer
is `--router` as default**, with the click-leg record re-armed to the routed
first leg and a plane word from the modelled copy's mesh plane; that is its own
arc. **BUILT 2026-09-03 evening, §1z-v: the router IS the default, both conditions
shipped with a revert each (`--no-router`, `--router-raw-leg`,
`--router-report-plane`), and the press and the follow abandon a live chain;
the operator's 40 refused clicks retrodict to 40 answered. §1z-w (same night)
added the routing origin's own plane word and the cast abandon; §1z-x the
enslavement detector, which withdraws RUN-1zT's confirmation; §1z-y the held
re-aim and the lead kill, item (a) of the list before the lead returns; §1z-z
the matched plane word on the lead grant, item (b); §1z-aa the fence-shutter
audit, item (d), measured 12/12 and built as a gate. All four gates stand. §1z-ab
(2026-09-03) argued the length: the maturation margin is void under the hold, 520
stands at one tap sample over the trigger's 517.5 u ceiling, 766 is refuted as a
margin, and the lead's return now waits on one scored run alone.** The bundle
question Q13 poses (adopt `D1_LEAD`?) is unchanged by it. The session's felt symptoms were
1z-t's keyboard lead, now opt-in.
Raised 2026-08-27 by
[studies/movecode/FINDINGS.md](studies/movecode/FINDINGS.md) §1i.**

The measurement, not the proposal, is what is new. When our geometry cannot place
or clear a click, `authsrv.py:16453` refuses to grant and says so in its own
comment — *"the client is pathing around it and knows more than we do. Say
nothing."* §1i measures what the silence costs: the client's **sync-world copy of
the player is driven by our grants and by nothing else** (51 grants ↔ 51 setter
calls, paired 1:1 on inter-event gaps to a 15 ms maximum), so a refusal does not
leave the client to its own pathing — it leaves the sync copy standing still while
the local copy walks away, until the client's own desync test **rolls the player
back**. In one 207 s run that was 17 refused clicks, 37% of all movement authority
suppressed, and a grant density of **1.40 per 1000 u against retail's 4.30 median
and 1.70 minimum over 118 live agents** — below the floor of anything ArenaNet's
own server was ever observed doing.

`D1_LEAD` (`authsrv.py:4595`) already contains the alternative: under the bundle
geometry does **not** refuse, because the answer is a verbatim echo of the client's
own chosen point, and an echo invents nothing for our navmesh to be wrong about
(REALFIX-A2, "retail's contract, 23/23 bit-exact"). Every one of the 17 refusals
recorded `d1_passthrough: false`.

**Why this is the owner's call and not a session's.** It is a FOUR-TERM BUNDLE —
lead, speed truth, plane truth, stop-ack — that travels together by design, it
requires `--zero-lead` and `--plane-carry`, and it carries its own registered
predictions and REFUTED-IF lines in `studies/movement/REALFIX.md` §0.9 plus an
UNVERIFIED remainder (~5.7% of retail-unclipped rays clip >20 u on our mesh). It is
off by default deliberately. §1i changes the *price of the status quo*; it does not
by itself discharge that spec.

**Two rivals, and the cheaper one is not the bundle.** §1i.5 decomposes the 17
refusals and only **4** are geometry; **13** are `geo-stale` — no position report
inside `authsrv.py:16373`'s 1.0 s window, in a session that spends **69% of its time
staler than that**. So:

* **Widen or bypass the freshness window** (13 of 17). `D1_LEAD` already contains the
  bypass — its `a2_click_leg` block at `authsrv.py:16385` answers from the model when
  the report is stale, and is inert under the shipped default — but the window is also
  a one-line policy question that can be asked on its own, without the bundle. **This
  is the cheapest thing on the list and the largest single contributor.**
* **Repair map 280's north-east mesh** (4 of 17). Those four are unanimous about the
  region and two of them are exactly §1h.4's OFF-MESH coordinates, so the geometry
  refusals really are *our decode being wrong* rather than the client knowing better.
  Needs no policy change at all.

Neither excludes the other, and neither requires answering Q13 as posed. **What Q13
actually asks is whether we adopt the BUNDLE**, which is a bigger commitment than
either fix above.

**Q14. The plane repair ships ON by default with no ruling — does it keep the
default, and what is its safety story?**
⏳ **OPEN, raised 2026-08-30 by
[studies/movecode/FINDINGS.md](studies/movecode/FINDINGS.md) §1z-n/§1z-o
(HANDOFF §D′ item 1).**

Q9–Q12 each have a ruling; the plane repair puts a numbered `0x002C` on the wire
by default on the authority of a code comment. The census now prices what a
ruling needs, and the evidence cuts both ways.

*For the default — specificity is well evidenced.* Replaying the trigger
corpus-wide fires **5 times, in exactly the 3 sessions §1z-e.2 adjudicated as
REAL locks, and nowhere else** — two independent derivations months apart agree
to the row. The disagreement rate transfers armed-vs-replay (2.26% vs 2.34%),
and a declared plane of 0 — the value the trigger draws its strongest inference
from — disagrees with our decode only **0.54%** of the time (a declared non-zero:
12.91%). R7's one live arming was a **true positive**, confirmed independently by
the client's own pathfinder (§1z-o.4) and by mesh ground truth (§1z-f.4 via
§1z-o.8).

*Against complacency, three things, and they belong in the same conversation:*

1. **95% of the evidence is counterfactual replay** (§1z-o.10). Nothing in the
   record both fired and was watched. And arming is perfectly confounded with
   `--router` — ON in 4 of 4 armed runs against 1.2% of the corpus, with the
   armed sessions granting 4.2× more per report. **The shipped default (armed,
   router off) has never once been run**; `studies/movecode/RUN-R8.md`
   pre-registers the run that fills it.
2. **The `ambiguous` safety valve is decorative** (§1z-n.3, §1z-o.9). Engaged
   **0 of 259** disagreements; dead by construction at its own call site;
   stacked ground is 0.17–0.50% of the meshes, and 194 corpus reports stood on
   it without one disagreeing — a stack offers two chances to agree, so the
   valve is anti-correlated with the hazard it guards. The doctrine leans on a
   safety property it does not deliver. Sub-question (§D′ item 3): does the
   clause earn its place, or should the doctrine simply stop citing it?
3. **The trigger cannot catch the intermittent lock morphology** (§1z-o.3).
   `HOLD = 5.0 s` is calibrated on the continuous freeze; R7's real lock topped
   out at **1.02 s** because the victim jumped ~100 u between freezes and the
   point test is exact float equality. n = 1, and lowering `HOLD` trades a miss
   for a false fire — not a change to ship, but the arm may be simultaneously
   too quiet (misses intermittent locks) and unprotected (the disarm never
   engages).

*What would settle it:* **R8** (the shipped default armed for the first time —
specificity and the router confound, provokes nothing) then **R8b** (authorship
by removal, and the first live trial of the heal — the `0x002C` restamp has
never met a locked client). Both are pre-registered with predictions, exposure
floors and aborts in `RUN-R8.md`; both are operator-driven client runs.

**Q15. Should `agtrack_guard.STATIONARY_WAIVER` exist at all?**
✅ **RULED 2026-09-05 — the owner: delete it. Landed as MOVECODE-1z-bt
([§1z-bt](studies/movecode/FINDINGS.md)):** the predicate, both clauses, the
three revert flags and the report-kind bookkeeping are gone from the guard and
the CLI, the re-pin's freshness gate stands on report age alone, and the capture
header carries no `agtrack_guard.*` key. Zero behavioural change on any capture
held (§1z-bs.5: the last shipped clause and deletion were one object), so the
deleted build's client-side witness is RUN-1zBO. The accepted cost is the class
1z-bn already accepted — a maturing lead over a stale report matures, and the
client's own test decides — with zero corpus exposure. The approach-leg hole
(§1z-bs.6) closes with it. `test_agtrack_guard.py` §9 rewritten (floor 116 → 74),
`waiverretro.py` retired, RUN-1zBS withdrawn. No revert flag: the arms of that
era live in the captures' flags rows. *The record below is as it stood when the
ruling was made.*

⏳ ~~OPEN, and newly answerable~~ — asked 2026-09-05 because the evidence changed
under it ([studies/movecode/FINDINGS.md](studies/movecode/FINDINGS.md) §1z-bo.9,
§1z-bo.5b).** The waiver (§1z-ah) lifts the re-pin's 0.347222 s report-freshness
gate whenever the last two accepted reports coincide, arguing that two identical
reports *measure* a still body so the harm bound is 1.0 u rather than
`RUN_SPEED × age`. **The argument is sound and its benefit is unwitnessed.** Two
instruments, from opposite directions: `waiverbenefit.py` censuses all 1,309
gamesrv captures and finds **82 real re-pin fires, of which the waiver carried
22 — every one of them on `{0x0047 stop → 0x003D walk-start}`, the single pair
§1z-bn's clause already refuses, and ZERO on a pair the clause keeps**;
`waiverretro.py`'s third arm replays the corpus with the waiver deleted entirely
and finds it **identical to the shipped build in zero of 71 control-OK runs**.
(They are corroborating rather than independent — both read `_repin_block`'s
`age > gate and not stationary()` conjunction — and §1z-bo.9 says so.) The
waiver's only ever claimed benefit, §1z-aj's 11 retracts at 0.0 u harm, is
inside that 22, and §1z-aj registered itself INCONCLUSIVE because its control
never produced the defect.

**AND ITS FOUNDING SPECIMEN TURNS OUT TO BE ON THE REFUSED PAIR TOO
(§1z-bq, 2026-09-05).** The waiver's own comment block cited RUN-1zAB run A —
*"the parked body reported (10369.4169921875, 8282.3349609375) BIT-IDENTICAL
three times"* — and the capture (`authsrv-20260903T202121-c1`) carries
`0x003D` / **`0x0047`** / `0x003D`. The middle report is a STOP, so the pair at
the +18.074 s arrival-risk is `{0x0047 → 0x003D}`, coincident at d² = 0.000 and
2.311 s stale: **the pair the clause refuses.** And refusing it is right — the
next report is **520.0 u away** 3.053 s later, so at the decision instant the
body was **~394 u downrange**, inside §1z-bl's tape-measured 311–468 u for this
class. §1z-ai's justifying *"harm 0.000 u"* measured the distance to the
**report**, which is zero by construction because we re-pin to it.

*Revised recommendation (§1z-bq.5, replacing "keep it and rule deliberately"):
**delete `STATIONARY_WAIVER`, or equivalently make the clause unconditional.***
Three independent readings of the archive now say the same thing — the founding
specimen is on the refused pair and would have cost 394 u; all 22 re-pins it has
ever carried are on that pair; and its only other claimed benefit registered
itself INCONCLUSIVE. **There is no case anywhere in the archive in which the
waiver has done anything but permit a rewind.** The argument for keeping it is
now purely a priori.

**RUN-1zBR TRIED TO MANUFACTURE THE CASE THAT WOULD OVERTURN THIS, AND COULD
NOT (§1z-br).** Parking the body against geometry twice with the lead on — one
window of 0.0 u across **11.45 s** — produced **zero** kept-pair windows. The
reason is structural: **a parked body emits a `0x0047` stop, and the next thing
it emits when told to move again is a `0x003D` walk-start at that same point,
which IS the refused pair.** The keyboard path reaches a parked body only
through the ordering the clause already refuses. Both of that run's
waiver-load-bearing decisions were on the refused pair, both `blocked`, and the
shipped build sent zero `0x002C`.

*~~What would still change the recommendation: the click path~~* — **CLOSED AT
DESK 2026-09-05 (§1z-bs), and the three numbers that sentence rested on are
retracted** (180 was `waiverlive.py` scoring staleness with the pair's own gap;
124 reproduces only as "a click within ~10 s"; 19 reproduces from nothing).
Joined on the guard's OWN state — its click contract kills the waiver while a
0x003E is pending and clears on the next report — the kept branch splits by
ORDERING, not by mover: where the newest report is a **stop**
(`{0x003D → 0x0047}`, 151 live windows) the next report finds the body still in
**151 of 151**; where it is a **walk-start** (`{0x003D → 0x003D}`, 87 live
windows) the body has walked on in **14**, every one at a client movement speed
— the 1z-bl defect's shape on a pair 1z-bn kept. That half is now REFUSED:
**`WAIVER_NEWEST_MUST_BE_STOP` shipped 2026-09-05** (MOVECODE-1z-bs; revert
`--waiver-walkstart-pair-stands`; RUN-1zBP's arm now needs both revert flags),
altering zero of the 85 historical fires, and on every capture held it is
indistinguishable from deleting the waiver. No kept window in the corpus has
ever carried a re-pin want (317 windows; the four sample-and-hold candidates all
explained from raw rows), and `{0x0047 → 0x0047}` never coincides, so **the
waiver's surviving branch is `{walk-start → stop}` alone.**

*The question now, narrower than above:* is that one branch worth a code path
for an a-priori benefit — correcting a drawn body that has diverged from its
reported point by less than the ≥ 299 u the client's own test would snap — that
no report chord can measure and no capture has produced? **Keeping it also
means closing a latent hole found on the way (§1z-bs.6): `_approach_send` arms
authsrv's click latch without reaching the guard's `on_click`, so over an attack
approach leg the waiver's click refusal does not fire (zero corpus exposure,
9 grants in 3 captures). Deleting the waiver closes that for free.**
Recommendation unchanged: delete, or equivalently leave the shipped clause.
RUN-1zBS is registered as *optional* confirmation (a keyboard run; it needs a
harness chord verb that does not exist and an exposure floor of ~32 leg
openings) — the ruling does not wait on it.

---

**Q16. Does the repository go public, and is the 2026-08-05 pre-public gate met?**
✅ **CLOSED 2026-09-07, by the owner. It goes public, and the gate is met — by an
audit, not by a scrub of the vault, because the vault was never the exposure.**

**Addendum 2026-09-08 — history rewritten before the first public push.** Two
`git filter-repo` passes: the author identity on all 2,680 commits is the id-prefixed
GitHub noreply address, and every string §2–§5 of the study redacted from the tree is
gone from every blob and commit message in every encoding, verified by simulation before
and a reachable-only scan after. 536 commit citations re-stamped in `f85a926e`. The
study's §8 records what changed and how it was checked; its "history goes public in
full" caveat no longer applies.

§6's risk row has carried this since 2026-08-05: *"the repo stays private, and a
credential-scrubbing / anonymising pass is a gate before any public push"*. That
sentence was written about `vault/captures/portal/*.jsonl`, which holds the owner's
real credential — and it was already answered by construction in the same paragraph:
`vault/` was gitignored in the first commit, before any content existed. **Verified
2026-09-07 across all 2,645 commits: 704 paths were ever added and not one is a vault
file, capture, key, binary or image.** There was never anything to scrub out of git.

**What the audit found instead is that the exposure was in the tracked tree, and it was
not the credential itself but a recoverable form of it.** `sessionstore.py` and
`test_handshake.py` pinned the real issued `user_id`/`token` GUIDs, and `webgate.py`
publishes `stable_guid` — `sha256` — two files away, so the pair was a confirm-a-guess
oracle for the account address they were derived from, with `RUNBOOK.md` stating that
account's password length one page over. Neither is credential *material* and neither
was ever in the vault; both were in the source, which is the half nobody was looking at.
That is the same shape as the row above it — *"the recipe was the exposure, not the
vault"* — arriving a second time and still not caught by a rule.

**The gate is therefore discharged by [studies/prepub/FINDINGS.md](studies/prepub/FINDINGS.md)**,
which is the pass §6 asked for, run over the tracked tree and the full history rather
than over the captures. Its five remediations landed in the same arc. **The provenance
gate came through clean** — four sweeps aimed at ArenaNet expression across 5 MB of
prose and 483 modules returned zero confirmed crossings, which is the first independent
confirmation that the MEASUREMENT/EXPRESSION boundary Q3 drew is actually holding in
the tree and not just in the rule.

**What the owner is accepting, stated plainly rather than buried:** publication attaches
this repository's documented live-service capture campaign (§3 R0b, §6.2, dated) to a
public GitHub identity, and publishes a runbook for patching the retail client. Those
were already the project's own recorded decisions (Q4, §6.2); publishing does not change
what was done, only who can read that it was done. The owner has read this paragraph and
chosen it. **Do not re-litigate it in a later session** — the same standing as Q4.

---

**Q17. Does `content/maps.toml`'s `name = "Lion's Arch"` cross the provenance
gate's "commit the id, resolve the string at run time" bullet?**
✅ **CLOSED 2026-09-08, by the owner. No. The bullet is scoped to authored bodies
of text, and the place names stay as they are.**

The pre-publication audit ([studies/prepub/FINDINGS.md](studies/prepub/FINDINGS.md)
§7) left this open deliberately rather than deciding it: `content/maps.toml` carries
about ten literal ArenaNet place names, and `CLAUDE.md`'s bullet then read *"Names
and authored text: commit the id, resolve the string at run time"*. Read strictly,
the word *Names* covered them.

**The ruling is that the bullet was about authored text and the word "Names" was
carrying more than it should.** The boundary is the same one §7 Q3 draws for the
gate as a whole — MEASUREMENT versus EXPRESSION. A body of authored text is
ArenaNet's expression and stays an id: quest descriptions, dialogue, reward
strings, item and skill names, which is exactly what `questdefs.py`, `reskin.py`
and `attribtable.py` already do. **A short proper noun used as a LABEL is not.**
A place name is how a reader knows which map a row describes; the prose in
`studies/` and in `CLAUDE.md` itself uses those names freely; and they are
published on ArenaNet's own wiki, which is one of this repository's cited sources
(`source = "wiki"`, 26 rows, with its own `THIRD-PARTY-NOTICES.md` section).
Converting ten of them to string ids would cost every content row its legibility
and protect nothing — and eight of `maps.toml`'s eighteen `name` rows are *our own*
labels for created chains and test slots, which the strict reading would have swept
up too.

**Recorded because a rule that is quietly not followed is worse than one that is
written down and scoped.** The direction of error in this repository is
over-refusal — §7 Q3's own history is four days of sessions refusing what the rule
never said, and 46 citations rewritten and reverted the same day. This is that
pattern caught one step earlier: the audit flagged the mismatch instead of either
converting the names or ignoring it, and the ruling names the boundary rather than
leaving the next cold session to re-derive it. `CLAUDE.md`'s bullet now carries the
scope; nothing in `toolkit/` changed, because nothing ever enforced this in code.

---

**Q18. Is retail's notice radius one global number, or per creature?**

✅ **RULED 2026-09-16 — the owner: *"the aggro radius is global from what I know. it's
hard coded as a circle in the minimap so I doubt it would differ from enemy to enemy —
they specifically put aggro range in the game as a visible mechanic."*** The argument is
design intent read off the interface, and it is the strongest kind available here: the
compass circle is drawn at one radius for every map and every creature, so a per-creature
radius would make the game's own instrument lie to the player. ArenaNet shipped aggro range
as something the player *reads*, which is an argument no amount of our approaching settles
better.

**Our data does not contest it.** Every observed notice in the corpus falls in 868–1048 u
across five definitions and three maps, and the wiki's 1012 sits inside every two-sided
bracket ([studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md) §11 N7, §12.5).
Nothing has ever measured two creatures whose brackets exclude each other — the refutation
condition §13.1 registered, and it never fired.

**What this closes, and what it saves.** `studies/monsterai/FINDINGS.md` §9 **Q7 is
CLOSED** — it was costed at "1–3 sessions" and its bar (10 observed points over ≥ 3 types)
is retired unmet, because the bar was measuring toward a question the design already
answers. **RUN-AGGRO-LAKESIDE-2 is WITHDRAWN** (§13), unrun. `AGGRO_RANGE = 1012.0` stands
as **one constant for every creature**, WIKI + CORROBORATED, and the server needs no
per-row radius field.

**A weakness in our own count, found while withdrawing the plan and worth recording.** The
"5 observed points over 3 definitions" this arc quoted is thinner than it reads: **three of
the five are the same individual** — agent 55 of the 2026-09-15 tape, approached three
times — and that individual is a **unique quest creature** (§14), one per map. So the
per-creature question had one clean point per definition and never had the population its
own bar implied. The ruling closes it; the count should not be re-quoted as if it had been
close to ten.

---

## 8. Immediate next actions

**This section lists what is OPEN, one line per item. What LANDED is in
[PLAN-LOG.md](PLAN-LOG.md), newest first.** Status is §3 and nowhere else; questions
for the owner are §7; this is the list of things somebody could pick up next.

**The rule.** When an item here runs, ships, is refuted or is withdrawn, write its
entry at the top of `PLAN-LOG.md` and take its line out of here *in the same commit*.
A new open item gets ONE line: its registered identifier, what is open, and a link to
the study section that carries the detail. The detail lives in the study, never here —
`toolkit/test_checks.py` holds this section under 40,000 bytes and goes red past it,
because until 2026-09-17 this section *was* the log: 226 entries and 1.1 MB, 79 % of a
file every cold session is told to read. When that check fires, move entries out; do
not raise the number.

**A citation of "`PLAN.md` §8" written before 2026-09-17 resolves in the log** —
including "§8 item N", which is the log's two `8.0 Next, as of 2026-08-11` lists, and
every such citation in a commit message. The entries moved byte for byte at `01639d69`.

**Where this list came from, and how far to trust it.** It was seeded on 2026-09-17 by
a sweep of all 226 moved entries for what each left open, followed by a grep for a
later closure ([studies/plansplit/FINDINGS.md](studies/plansplit/FINDINGS.md) has the
method and every candidate, in 95 rows). **The sweep over-reports for the August
entries**: of ten older candidates checked against the code or the study itself, three
had been closed with no log line saying so (`ENEMY_SKILL_FRACTION`, `INTERACT_RANGE =
250`, `test_guards` §8). So an item is listed below only
if it is from September's arcs, or if something current — a study's own open list, a
§3 row, a comment in the code — still says it is open. Everything else stayed in the
study doc as UNVERIFIED, which is the honest label for "no closure found".

### 8.1 Open from the live arcs (September)

**Desk routes the owner took, 2026-09-22** — [studies/deskwork/PLAN.md](studies/deskwork/PLAN.md) §3

* **DESKWORK-D1**: steps 1–8 landed (PLAN-LOG) — the bare-machine c2s
  send-site census over both framers (`sendsites.py`, 214 sites), SANDBOX-N2's hero kick
  armed from retail's one batch (c2s `0x001F`), retail's c2s triaged (`c2striage.py`: 57
  opcodes over 96 live connections, zero undecided; `test_dispatch` §10 is the reverse
  guard; `0x00B1` MAP_TRAVEL named medium and dropped until its arm), the party family's
  henchman ADD armed (c2s `0x009F`, `--no-henchman-add`; PLAN-LOG step 5 and its fix
  pass, studies/cmsg "The party family") and its KICK armed as RECONSTRUCTION (c2s `0x00A8`,
  `--no-henchman-kick`; PLAN-LOG "CLEANUP-3", 2026-09-24), a town ARMOUR change's `0x006F`
  planned per slot in both regimes (`--no-town-armour-visuals`, the same entry),
  the hero ADD armed as RECONSTRUCTION (c2s `0x001E`, `--no-hero-add`, for
  the commander rig — `--party` — where it re-declares the inventory a kick destroyed
  and refuses in the legacy rig; `0x0018` from the owned set as a labelled policy,
  `--no-hero-unlock-mask`; the client sends both hero commands from an OUTPOST only),
  the hero skill SUPPRESS toggle armed as RECONSTRUCTION (c2s `0x0019`
  HERO_SKILL_TOGGLE, `--no-hero-skill-toggle`: Shift-click a hero skill → a per-hero
  mask answered with the whole-mask `0x0065`, the body skips the slot, persisted), and
  the inventory pair armed on an item store (`itemstore.py`, `--no-item-moves`: c2s
  `0x004F` ITEM_MOVE is an item leaving the EQUIPPED bag — field 1 its slot there,
  4 of 4 — and `0x0030` EQUIP_ITEM draws `0x014B`+`0x006F` into an empty slot or
  `0x0152` onto an occupied one, both replayed from the decoded tapes; cells persisted
  and restored at the dress, a stored HAND change not restored; the fix pass closed five
  blockers — the dress reads the store itself, reserved cells, the launch records never
  rewritten by an equip, removed armour protects nothing, a suppressed resurrection is
  never cast — and the suppress mask now follows the client's own bar edits; the owner's
  confirmation pass, same day, PLAN-LOG: the doll's row order fixed — retail's bag order
  dressed, `--equipped-visual-order` reverts — and the general move `c2s 0x0072`
  ITEM_MOVE_BY_ID armed as RECONSTRUCTION, `--no-item-move-by-id`; its fix pass, same
  day, PLAN-LOG: the dress cell keyed by location, the merchant's purchases in the item
  store, off hands' homes alone reserved, storage bags refused), and world-map travel
  (step 7, `maptravel.py`, PLAN-LOG: the landing and its fix pass, both 2026-09-23).
  **CONFIRMED on our client 2026-09-23** (studies/deskwork/CONFIRM-2026-09-23.md): kick,
  add, kick-add-kick-add, the kick held across a relaunch, the suppress circle on and off
  and the body skipping a suppressed skill, move, stored-cell restore, equip and swap;
  and after the owner's-answer fixes (PLAN-LOG: the doll order, the display mode
  `0x00EF`/`0x0057`, the backpack drag `0x0072`) the doll's order, the eye and the helm,
  Hide in Towns hiding the helm on the doll AND the world body, and the drag staying.
  **CONFIRM-2 ran 2026-09-24** (studies/deskwork/CONFIRM-2026-09-24.md, PLAN-LOG): the
  henchman add HELD on the client. The town weapon's carrier fix
  CONFIRMED on the client (CONFIRM-2 §7, PLAN-LOG): our load's player `0x006D` was the
  carrier — withheld in a town the body is empty-handed at load and after F2, and
  `--town-player-weapons` reproduces the stale hammer (OBSERVED). The owner's answer
  (2026-09-24): on retail no weapon is shown on the body in a town, only on the doll — the fix's
  picture. The field shield's fix CONFIRMED on the client (CONFIRM-2 §8, PLAN-LOG): the
  player's own `0x006D` withheld in a field too, the shield standing at load and through a swing.
  The henchman kick CONFIRMED on the client (CONFIRM-2 §9: the row leaves, the count drops, a
  re-add restores both, `--no-henchman-kick` keeps the row). The town armour CONFIRMED on the client (CONFIRM-2 §10,
  2026-09-25, the harness's `drag:` / `dclick:`: in a town the body's helm follows the equip,
  `--no-town-armour-visuals` leaves it on, a field is unchanged). **Open**: **the refusal at the cap** (PLAN-LOG
  "DESKWORK-D1, the refusal at the cap", 2026-09-25): retail's reply is NOT FOUND on 96 live
  connections, the client's party error table (81 rows at `0x00B97968`, carriers `0x01B8` /
  `0x01BC` / `0x01D6` / `0x01E3`) has no "party is full" row, and the sentence a player expects
  (#57757) is CLIENT const text — so retail's client may refuse locally, and why ours does not is
  UNVERIFIED; `--party-full-reply CODE` (one `0x01BC [CODE]`) ships OPT-IN, default silent; owed:
  the owner's loopback runsheet (studies/cmsg "The refusal at the cap") and, in any live session,
  ONE Add click at a full party; travel's confirmation BLOCKED on content (no fog-initialised view
  carries a second pin; `M` on 449 / 242 / 248 / 310 asserts, CONFIRM-2 §3); the display
  mode's field step (the owner's hands, the harness cannot open the drop-down); the
  henchman FIELD-body carry, the outpost re-join and the `'play'` allegiance behind a
  `standing` gate (step 5's deferred half — the `0x00B0`-climbs-by-2 field size is NOT FOUND). The per-map cap and the Leave CONFIRMED on the client (CONFIRM-2 §11).
* **DESKWORK-D5**: the combat rules retail's tapes on disk already settle. LANDED
  2026-09-22: the adrenaline gate (SKILLS-B1's gate half, skills §34.11); property 10
  and the `[42]` residue (§16.6, self-scoped; `[42]` only when the maximum moved); the
  adrenaline replay (ANIMREF §19, a second refusal gate named). LANDED 2026-09-23: the
  interrupt (castmech §4's note, animref D5's note; `interruptjoin.py`, `interrupt_player`
  OBSERVED n=1 per shape at the player -- a cast, a swing -- `interrupt_body`
  RECONSTRUCTION); the NPC recharge anchor moved to the cast's COMPLETION
  (`rechargeprobe.py`, six spells OBSERVED, 229 a named divergence;
  `--no-npc-recharge-from-completion`); the fix pass the same day (the body hook, the
  running-chain gate, P2/P3 recorded FAILED as written -- the log's fix-pass entry).
  LANDED 2026-09-23 (pass 3): party-wide shouts (skills §56, `shoutjoin.py`: 23 foreign
  applies of 364/348 on the observer, 6 of them a hero's, 0 of 8 foe shouts; the radius the
  client's own `aoe_range` 1000, CORROBORATED, which the tape neither measures nor bounds —
  every pair rests on a lead, §56.8 (the fix pass withdrew "≥ 913 u" and corrected the hero
  tape's observer); `party_wide = "earshot"`, `--no-party-wide-shouts`); the refusal ids
  (skills §57, `chatdefs.REFUSAL_REASONS`: the 60
  plain ids 1934–1993 by label, four OBSERVED — 1988 the recharge refusal, witnessed once,
  the fix pass — `--refusal-reasons` DEFAULT OFF, the weapon
  gate's #1985 its one consumer); 3(d) Mend Condition (skills §58, `heal_if_removed`). Still
  OPEN: §56.9's residuals (the instant E3's slot and the `[8]` hold pair, the E4→E5 tick gap, a hero's E4 and debit at its start); a 348 row (no armour-bonus mechanic to hang
  it on); the hero's cure on screen (final-confirmation-needs-run; the hero's apply itself
  CONFIRMED on our wire 2026-09-23, 2 of 2 vs 0 of 2, as was the interrupt at the PLAYER,
  2 of 2 with the 24 s disable drawn — studies/deskwork/CONFIRM-2026-09-23.md; the player-to-hero
  direction is unwitnessed on every tape); the allied NONCOMBATANT retail's shout boosts
  and `allies_of` excludes (§56.7); 3(e) a hero's zero gain;
  the `[62]` energy word (read, own-party-scoped, not shipped); the second refusal gate's
  variable (the recharge refusal's id is 1988, witnessed once on `20260913T210901`, §57);
  the armed-EMPTY death clear (a one-witness divergence, skills §34.11.4); a body
  or hero as interrupt VICTIM (RECONSTRUCTION, final-confirmation-needs-run) and the
  windup-swing drop (UNOBSERVED); 229's recharge anchor (HSR proc vs start, a capture
  campaign); NPC aftercast proper and attack-skill recharge cadence (unmeasured).
* **DESKWORK-D4**: skill coverage in bulk. **Steps 1–4 LANDED** — 1–3 on 2026-09-22
  (skills §54, SKILLS-DT: the slot mapping, the referee, the Q7 census; the step-3 gate
  FAILED at 27 %), **step 4 on 2026-09-23 on the owner's option 1** (skills §55, SKILLS-LT;
  PLAN-LOG): the 131 PLAIN SERVED rows through the step-4 gate → **47 label-tier rows** in
  `vault/content/skill_labels.toml` (59 before the same day's review-driven fix pass,
  §55.7), under the hand rows, 36 of them marked, `--no-skill-labels` reverting; 84
  excluded by reason (§55.2); the three hand-row fixes done. (i) **The client confirmation
  is DONE** (2026-09-23, studies/deskwork/CONFIRM-2026-09-23.md): 187 drew −7 on the
  client, nothing under `--no-skill-labels`; 183's caster-centred area 30 on the near foe
  only, nothing under `--no-caster-areas`. **Still open:** (ii) **the
  residue per skill** — pass 1 and its fix pass landed 2026-09-23 (skills §59–§59.7,
  SKILLS-LU; PLAN-LOG): 57 label rows (`57ae1dbe`); pass 2 landed 2026-09-25 (skills §60, SKILLS-LV; PLAN-LOG): 60 rows, the overlay installed at the merge, CONFIRMED on the client (CONFIRM-2 §11). Still out: a BODY's own chain (a body's chain-gated cast lands on NOBODY;
  retail's bodies meet the requirement, 5 of 5 live 784s); 770's ally-centred adjacency; the ON-STRUCK riders (2136; 113) and 926 (a tooltip run); byte 1's resolution (769 917 1468) and its 3 heals; 292's
  percent-of-loss heal; 943's conditioned heal, 1262's "creatures"; the 210 conditional
  SERVED rows, the two knock-downs left marked (192, 3425), 840's self-Poison, 1113's four ticks, 1033 (a tooltip run), 784's Poison CONTESTED 2 of 4 (§60.8), then the 924 RECOGNISED and §54.4's two-consumer
  proposal (still the owner's call); (iii) step 5, the 68 no-slot rows; (iv)
  step 6, the timed effect types 16 / 24–28; (v) the 141 INDETERMINATE slots wait on a
  client tooltip run (§54.3).

**Skills and the slice** — [studies/skills/FINDINGS.md](studies/skills/FINDINGS.md),
[studies/slice/FINDINGS.md](studies/slice/FINDINGS.md)

* **SLICE-F48, the snare row.** Movement speed's decrease arm has no content row to run
  on: a Water hex, a self-snare stance or Deep Freeze, to settle boost × snare on our
  own client (slice §48).
* **SKILLS-WK, heroes and bodies.** Weakness's −1 reaches a hero's or a body's rank
  arithmetic and never the wire; only the player gets the `0x003B` batch (skills §51.3).
* **The Frenzy arm is UNSEPARATED** — both orderings of the multipliers fit the four
  observed hits (skills §48.8). Needs a tape where they diverge, not more of the same.
* **One Javelin for 45**, n = 1, unexplained; an effective +8 armour at that instant and
  not a differently rated piece (skills §50). Recorded, not chased.
* **The skill library has no writers**: trainers (`VnLearnSkill`), tomes (`0x006D`) and
  capture signets are all unanswered, and the `GmDeckBuilder` flag that picks which set
  the panel enumerates is unread — "is this a PvP character" is a guess (skills §47).
* **SLICE-F46.9, ZERODRAW with a Deep Wound on the Hatcher**: what the client draws for
  a foe between its wound edge and its next maximum word. Named, not run.
* **SLICE-F47**: the RA tape's Mind Burn pair reads non-integer points under the
  last-seen-maximum join; scoped out of the pool check rather than chased.
* **SKILLS-AD4's clock half.** The zero gain ships (skills §53.6) without marking the
  25 s combat clock; whether retail's clear counts from a zero `0x00CF` is NOT OBSERVED
  (every zero on RB sits inside a run of other gains). A hero's zero gain is still not
  sent (`hero_pool_gain`), unread on JARIN's tape either way.
* **SLICE-F43, shrines and gadgets as server-created agents** — understood, not built;
  no longer the wipe's blocker. With it, R4a's other absences per §3: a spawn table and
  any behaviour beyond aggro, chase and swing.

**Daggers** — [studies/daggers/FINDINGS.md](studies/daggers/FINDINGS.md)

* **Area damage beyond Death Blossom.** Of the 73 multi-target Fire Magic instants on
  `20260817T231139` (daggers F13), 185 and 179 have no row and 197's label row reaches one
  target; the areas over time and area hexes are unbuilt; B8's adjacent damage is the
  player's strike only (a body's spell areas ship: weapons §37–§40, skills §59). Cyclone
  Axe's per-foe attack and scatter are unmeasured.
* **DAGGERS, after RUN-2** (daggers §8, last paragraph). A dual whose first strike
  lands and whose second misses (is 3 sent?); ~~property 10 on the victim~~ (decoded, skillcast §16.6, and SENT since 2026-09-22: `[10, me, skill]` ahead of a skill's word at the observer, self-scoped 92 of 92; 229 / 230 are Lightning Orb / Javelin); the short gap
  after a skill's hit on SWORDS (9 of 21, an eighth of the interval off) and the three
  short-and-single dagger ones — not DAGGERS-F20's early double, which explains the
  rest. Sneak Attack with a sword is dropped (PvE-only).

**Weapons** — [studies/weapons/PLAN.md](studies/weapons/PLAN.md)

* **Every weapon type, accurately** (plan 2026-09-18; W0's first half, W1, W2a, W6a,
  W2c, W2b's server half, W5 and W4c landed — a held staff's or focus's `556` joins the
  pool, and a wand or staff scales on the character's LEVEL against armour (strike level
  3 × level, the wiki's rule and worked example; the owner's level-1 wand hits and a
  level-20 client run reproduced, 20 of 20 words), where it dealt its raw range at any
  level against anything; Dual Shot fires two arrows at one windup, each its own
  roll at 75 % — the shape OBSERVED on eight pairs, the numbers WIKI; and a preparation
  is on the wire — Kindle Arrows' own 343, its kind, its impact and its own second word,
  OBSERVED on the owner's recurve; and W2f gives bodies the same preparation and arrow
  factor). Q16 is MEASURED and open (§20): the client walks a follow to the melee disc
  regardless of weapon, so a ranged press still closes to melee on the client even
  though the server's copy stops at range — a MOVECODE-side clear-the-follow change, not
  a weapon one. **The desk check of 2026-09-18 spent the last server-side arm** (the
  hold and the `0x0028` TOGETHER, retail's own start batch, on a frozen target:
  `20260918T201027`, flights 0.727 -> 0.282 -> 0.050 -> 0.050 s, the body closing to
  the disc exactly as with neither message) and refuted two rivals -- no item
  modifier is an attack REACH, and retail's follow aims at the TARGET as ours does --
  so the wire is now byte-for-byte retail's and the stopping distance is decided
  client's resolver. **That codescan ran the same day and CLOSED Q16's mechanism (section
  22): the client's park threshold is `(r1 + r2 + TABLE[kind])^2` and NOT ONE of its six
  inputs is a weapon, so a follow parks at the melee disc whatever is held -- retail's
  client and ours alike -- and Q16's premise is refuted. `0x0028`'s handler never writes
  the followed-agent field, which is why all three arms failed; only `0x0029` clears it,
  and retail sends one to park a shooter 0 of 306 follows. **Section 22.4's "owner choice"
  is RETRACTED by section 23: the operator asked for faithfulness, both options were
  built or costed, and both are wrong -- reverting loses the range opening retail has,
  and the `0x0029` sends a message retail never sends. WHAT WE HAVE IS FAITHFUL: the
  wire is retail's bit for bit, the swing opens at the weapon's range (retail's first
  launch after a follow reaches 1,284 u on a 1,273 u recurve), and the body finishing at
  the melee disc is the client's own arithmetic. W2g (the leg moved to the disc) was
  built, tested at 115 checks, REGRESSED on the client -- first shot 1.17 s -> 6.03 s,
  every arrow at 80 u -- and is WITHDRAWN: the leg's END is what the reach gate reads,
  so the leg at the range is the mechanism that opens the swing there. One internal
  inaccuracy remains (`state["pos"]` parks at the range while the body walks on) and it
  is a MOVECODE change to `_reach_frame`'s sourcing, not a weapons rung.** Eleven player types and the hostile-only ranged
  type are one content table with retail items, and EVERY holder of a bow, wand or staff
  shoots — the player, a party caster, a hostile archer: release at the windup, the hit
  distance ÷ speed later, from the weapon's range — a bow ATTACK SKILL releases at its
  E5 with the skill's own projectile (the skill record's `+0x88`, WEAPONS-C10), its
  strike a flight later, no 46, and a press OUTSIDE range walks the server's copy to the
  weapon's RANGE and opens the swing there (the old arm shot from 72 u), row for row
  retail's on the client. Open: **Q16, W2b's client half** — the harness's attack step
  is the server mailbox, so the client never arms its own attack-follow and walks on
  through the start; retail's parks itself with no message; an OWNER press from beyond
  range (RUN-WEAPONS-2) is the instrument; ~~W3~~ (shipped 2026-09-19,
  `studies/weapons/PLAN.md` §26: the scythe's extras and its 2^0.125 critical), ~~W4's rest~~ shipped 2026-09-19 (§30: `587` against the pieces'
  `527` under its condition word, the `633` reader with `634` / `635` / `636`, the isle's 3.098
  unmet divisor; left of W4: the fifteen AREAS OVER TIME the record's target byte 16 also
  marks (Fire Storm's seventeen casts on `20260817T231139` are the witness: a ground `0x00A1`
  350 at the completion, ticks once a second with no 58, the scatter) and its seven area
  hexes, line of sight (*Obstructed* / *Stray*), and the BONUS penetration sources beyond the
  hornbow (the client's item word 574 `Armor penetration`, the Sundering upgrade, on no corpus
  item; Judge's Insight 267); ~~the point-blank bursts~~ shipped 2026-09-20, §40 -- the ten
  single-packet bursts (target byte 16, no projectile, no duration: Earthquake, Meteor,
  Rodgort's...) reach every foe inside the record's radius of the target's position at the
  completion, each its word, `[20]`, condition and knock-down (RECONSTRUCTION: Fireball's
  arrival without the flight; never cast on a tape, the lock says so); Earthquake's row; ~~the
  finer hit test~~ shipped 2026-09-20, §39 -- the aim leads the target's velocity (WIKI), a
  target off the aim by more than 24 u at the arrival dodges: an arrow draws `[38, target,
  attacker, 1]` behind its `0x00A7` (7 of 7 on retail), a spell its impact on the ground; the
  two numbers are ours, RUN-1B's Orb block measures them; `--no-dodge`; ~~Fireball's splash~~ shipped
  2026-09-20, §38 -- the record's target byte 16 and `aoe_range` 240 make a burst at the aim: the
  impact, the explosion `0x00A1` 333 (35 of 35), then a word and a `[20]` per foe inside the
  radius, each its own number; `--no-spell-areas`; ~~a BODY's spell projectile~~ shipped 2026-09-20, §37 -- the
  completion batch launches behind the 58 (75 of 77 launches at the client's own activation),
  the terms are computed at the arrival against the taker as it stands then, `0x00A7` / the
  impact visual / the word (the Master's Orb onto the owner 11 of 11); ~~a player's spell projectile~~ shipped 2026-09-20, §36
  -- the E5 batch launches the record's projectile (Dancing Daggers 17 of 17, the corpus's only
  player-cast projectile spell), the arrival is `0x00A7` / the impact visual / the word, a
  spell of several sends them a third of a second apart, speeds a round number per projectile
  (343 / 403 at 1800, 405 / 854 at 1200, OBSERVED 41 of 47), `--no-spell-projectiles`;
  ~~the base penetration sources~~ shipped 2026-09-19, §35 -- the client's own bonus slot holds the
  wiki's 10 / 20 / 25 on the five attack skills (CORROBORATED, every snapshot), Strength's 1 % a
  rank rides attack skills only (WIKI, UNWITNESSED -- 1B's new block), Air Magic's 25 % is the
  tape's Orb (80 → 60, studies/skills 50.1); the largest base plus the bonuses at every rating
  read, `--no-base-penetration`;
  ~~a spell's own type~~ read 2026-09-19, §34 -- no client column (all 41 checked), the wire
  carries it (Orb arrives as lightning under an earth staff, Dancing Daggers as earth with
  daggers, 79 of 79), the row's wiki label names it (`damage_type` on 194 / 312 / 252; Flare
  meets the pieces' elemental rating, a physical spell would meet their +20); ~~identifier `573`~~ read 2026-09-19, §33 -- a hero's level-scaled
  armour, the wire's (80, 23) the wiki's Warrior row and the isle's 3 x level + 20;
  ~~the hornbow's 10 %~~ and ~~Q2~~ closed 2026-09-19, §32: the client's own 609 handler names
  the classes -- 0 shortbow, 1 longbow, 2 flatbow, 3 recurve, 4 hornbow, 1 and 3 the corpus's
  2.475 s pair -- so a bow now swings at its class's rate and a hornbow takes 10 % off the
  target's rating, WIKI, `--no-bow-classes` reverts), ~~Q10~~ (the weapon's unmet term is the isle's, §30; the shield's
  and focus's are WIKI; RUN-3 separates divisor from strike-level drop), ~~a staff's `570`
  recharge word~~ (shipped 2026-09-19, §31: a 20 % roll at a spell's completion halves its
  recharge to the nearest second on the player's and a hero's `0x00E5`; WIKI, unwitnessed on
  any tape -- RUN-1B's staff should cast one 5 s spell ten times), ~~Ignite Arrows' splash~~ (section 24: it explodes on the target and on every
  foe inside the client's own 156 u radius, armour-respecting, and fires even when
  the arrow misses or is blocked); no content spawn row
  holds a ranged item yet. Q16 (the client walking a ranged follow to melee, MEASURED,
  its server-side arms EXHAUSTED
  §20) is a MOVECODE-side clear-the-follow change; the rest of the arc needs the owner
  (RUN-WEAPONS-1B / 2 / 3; 1A ran 2026-09-19) or a content decision (spawn rows). The
  spear throws since §26 (143, flag 1, the 1600 class); ~~Q12~~ closed there (585 is the
  customisation word, W8 reads it); ~~W9, the weapon-set switch~~ shipped 2026-09-19 (§27:
  c2s `0x0032` answered with retail's one batch, `--weapon-set N=ITEM[+OFFHAND]`, F1-F4 on the
  client) -- ~~RUN-W9-2~~ ran 2026-09-19 (§28: a base-changing switch owed a `0x0035`, retail
  sends it at the NEXT attack start not in the batch -- 2 of 2 base changes on the 1A tape, 2 of
  2 same-base sent none -- and `select_weapon_set` now arms it; on the client the axe -> hammer
  swing ran 1.33 -> 1.75 s with the pair riding the first post-switch start); ~~`0x0152`'s client
  effect and the item family's first field~~ closed at the desk 2026-09-19 (§29: the handler
  EXCHANGES the two items' bag and slot, renamed `ITEM_SWAP_LOCATIONS`; the first field is the
  `0x0144` inventory key). Open after W9, all on ONE live tape and written into RUN-1B's steps:
  retail's reply to a same-set and to an empty-set press, and whether a switch that moves the
  maximum energy re-sends 41 / 43 (INFERRED; a staff in a set does it).
  Captures wanted: 1B (five bows, staff, wand — predicts 1200 / 1600 / 2800 u/s), 2
  (range: every range here is WIKI or reconstructed, and 1A's spear PARKED at 0.75 × the
  wiki's number, §25.4 — the run must separate park from range).

**Monster AI** — [studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md)

* **MONSTERAI-J has no content rows.** `passive` and `group` are built and tested and only
  the sandbox compiler writes them; the tapes name five retail definitions that would
  (§12.9). Which rows is the operator's call.
* **DESKWORK-D8 steps 3 and 4 SHIPPED at the desk (2026-09-24, PLAN-LOG "DESKWORK-D8 steps 3
  and 4" and its fix pass); the client run 2026-09-24 (CONFIRM-2 §9): the return, the caster
  opening and its notice gate HELD; the caster's stall after its first cast was fixed and the
  fix CONFIRMED on the client 2026-09-25** (PLAN-LOG "the caster's held-slot stall"; CONFIRM-2
  §9's re-runs). Feel stays the owner's instrument. `--no-leash-return` / `--no-caster-opening`. Residues: (i) **SLICE-F22's "no swing mid-follow" is contradicted at
  n = 2 on the caught-runner case** — retail opened an `attack_started` between two follows with
  the follow re-issue PAUSED ~1.15–1.21 s, one swing landing and one STOPPED without landing,
  both under a 1.5× Bull's Charge burst (monsterai §15 L4); ours halts on the clock, owes the
  swing and re-follows — a ruling on modelling the caught-runner swing without a halt is owed.
  (ii) **the wand/staff caster** still takes W6a's `0x002A` walk-in (`hostile_caster` excludes
  ranged weapons); a wand carrier stops at ~430–490 u on tape where W6a stops at 1,248 — one run
  on a wand row settles both. (iii) **the fixture Hatcher is a caster under `--enemy` alone** (a
  Monk, four spells, empty hands); a harness scenario that wants the walk-in passes
  `--no-enemy-skills` or `--enemy-weapon`.

**Heroes** — [studies/heroes/RUN-HEROLIB.md](studies/heroes/RUN-HEROLIB.md)

* **Retail's reply to `0x005E`** (a live-account swap at human cadence) is unobserved
  (§12.6). The settings blob's five `5a`–`5e` groups read like an appearance record, and
  that is a guess.

**Quests and the schema** — [studies/quests/FINDINGS.md](studies/quests/FINDINGS.md),
[studies/divergence/FINDINGS.md](studies/divergence/FINDINGS.md)

* **Map 888 on a 38888 client (arm A)** has never been loaded; the cage it waited on
  was closed 2026-09-16, so it is now only a run (quests §11.4).
* **The manifest family**: the hash function, `0x0196`'s body layout, and why one
  session asked for 5 maps when 17 hashes had changed (divergence D13).

**Movement** — [studies/movecode/FINDINGS.md](studies/movecode/FINDINGS.md),
[studies/npctrack/FINDINGS.md](studies/npctrack/FINDINGS.md)

* **§1z-dd.8's retail half needs a live corner**: at the desk the slide-then-silence class
  is NOT FOUND on retail, 0 of 236 (§1z-dh). It decides server-side slide integration
  against client silence.
* **§1z-dl**: a `datplan` check of the mesh lip at the corner, ONLY if the corner
  recurs as a felt defect. Conditional on the owner's sessions.
* **NPCTRACK**: two hostiles park in one body (Q10 — retail does too; a per-chaser
  bearing would be a reconstruction with no witness, so it is a lever for the owner's
  eye, not a defect); Q8 is an observation.
* **`movetap` cannot certify a capture under the harness** — 10–12 Hz against its own
  50 Hz floor (§1z-ag). Instrument debt; nulls taken that way do not count.
* **RUN-R8** ([studies/movecode/RUN-R8.md](studies/movecode/RUN-R8.md)) is a
  pre-registration that never ran. Run it or withdraw it.
* **The review's nine one-sentence documentation fixes** (§1z-bh) are still owed.
* A real `D1_LEAD` default — `--no-d1-lead`, a composition-matrix value and a
  router × d1 rule — is "its own arc, if wanted" (§1z-bu). Not wanted so far.

**Items** — [studies/itemmods/FINDINGS.md](studies/itemmods/FINDINGS.md)

* **A 542 on a WORN piece.** The rune ITEM's word is measured and composable (§5.7); the
  word on a host piece with the rune applied is not, and every payload word after a
  component's 614 carries bit 31, so it may differ. One capture of a runed character.

**Tools**

* **MODELVIEWER**: no per-map reverse index across the ARCHIVE yet (model → maps over all 349
  retail maps, D11 step 2, ~7 min first build); the content-map → model index and lazy
  thumbnails landed 2026-09-24 (PLAN-LOG "DESKWORK-Q4, DESKWORK-Q5 and MODELVIEWER").

**The sandbox** — [studies/sandbox/PLAN.md](studies/sandbox/PLAN.md)

* **SANDBOX-B6, the owner's first run** through the window: the slice's own spec, then
  one that changes every knob. It settles **SANDBOX-U1** (what the client draws for a
  non-zero secondary on the player's pair: predicted `W/Mo` on the party window and
  the secondary's skills on the panel), **U2** (two heroes in two bodies both render,
  follow and cast), **U3** (a body of another profession carries the declared one),
  **U4** (a four-strong group pulls as one) and **U5** (a character and a hero built
  entirely in-game from empty bars and unspent points keep the build across a run) —
  predictions in §3 there.
* **SANDBOX-N1's residue** (the selector landed 2026-09-24, PLAN-LOG "SANDBOX-N1, the Enemies
  tab's skill and attribute selector"): a file's explicit all-zero ranks (`[[17, 0]]`) open as
  NONE, so its hostile acts at 12 where the file's acts at 0 (pre-existing, file-only); a
  hostile carrying one skill twice is held and `validate` does not refuse it (retail allows one
  copy); the rank another profession's skill acts at (0 with any rank set, 12 with none) is read
  from the server's source, text-locked, never run -- one U-run with an Orison of Healing on a
  Warrior hostile, prediction first, closes it; a real OS drag is the owner's to try (the smoke
  drives synthetic drops). (N2, adding and kicking heroes from the in-game party panel,
  shipped as DESKWORK-D1 steps 1 + 4 and was CONFIRMED on our client in an outpost
  2026-09-23 — studies/deskwork/CONFIRM-2026-09-23.md R1–R5; the hero ADD stays
  RECONSTRUCTION, heroes §3.3; the kick of an embodied hero stays UNOBSERVED on retail.)
* **SANDBOX: `ENERGY_BY_PROFESSION` is WIKI recalled, unread** — eight of ten rows in
  `toolkit/harness/sandbox.py` want GWW "Energy" read back before they are quoted as
  facts; the window shows them as editable defaults.
* **SANDBOX, the residue of the hostile-cap lift** (2026-09-24; PLAN-LOG "R-SANDBOX, hostile
  level and rank caps lifted", "Two things NOT done" — its (a), the server-load guard for a
  content row past 255, shipped the same day: PLAN-LOG "R-SANDBOX, the server-load level
  guard"): **the level-0 quirk** — `agent_level` treats 0 as None, so a level-0 hostile
  armours at 0 but strikes as 20 (the fallback 60); level 0 is a real retail value (map
  146's defs 1428 / 1433 / 1434 / 1442) and the window offers it; which arm is right wants a
  retail witness of a level-0 foe's damage, not a guess.

**Profession** — [studies/profession/SECONDARY.md](studies/profession/SECONDARY.md)

* **The K panel's secondary change is CONFIRMED on the client** (SECONDARY.md section 6, 2026-09-25;
  PLAN-LOG "SECONDARY-R1..R6"). Open: **SECONDARY-Q1** (0x00B7's flag on a client), **Q2 / Q7** (what the
  client does by itself with an old or a third profession's bar skill; only the server's strip is seen),
  **Q3** (which control's notification reaches the send), **Q6** (a PvE character with unlocks, on tape).
  The overspent-store load fix (PLAN-LOG, 2026-09-25) is offline only: its client check spends past 10
  points under a larger budget, then launches `--party slice` -- the load completes, the panel at 0 of 10.

### 8.2 Waiting on the owner, or on a live capture

* **DESKWORK-D14's off-disk vault copy** waits on a second disk: the owner has none
  available (2026-09-22). The mirror stays same-disk, last run 2026-08-06; the route's
  census, manifest and RUNBOOK half need no disk and were not taken
  ([studies/deskwork/PLAN.md](studies/deskwork/PLAN.md) §3 D14).
* **§7 Q14** — the plane repair ships ON by default with no ruling. **§7 Q2** — the
  WASM question has no date and no default; every line written since presumes "no".
* **R-ISLE rung 8d's bench half**: one requirement-MET block at effective rank 13, ~80 s,
  the in-run reference the unmet-requirement divisor (3.098) has never had. It needs its
  own short plan or a line on the next Isle tape — not `isle_rung8d_recast_v2.txt`,
  whose re-cast steps RB2 made moot ([studies/isle/PLAN.md](studies/isle/PLAN.md), rung 8d).
* **SKILLS-B1**, the rounding half only (the gate half closed at the desk 2026-09-22,
  skills §34.11): ceil is dead, round holds k = 1 (skills §53.1), and what is left is a
  hit in (0, 0.5 %): a `0x00CF` carrying 0, or nothing.
* **MORALE-Q5 and Q6's field-to-field half**: morale BOOSTS have zero sightings on
  retail's wire, and both zones in the corpus that carry a live penalty go into an
  OUTPOST (n = 2, one map pair), so what a field-to-field zone does with a penalty is
  WIKI only
  ([studies/morale/FINDINGS.md](studies/morale/FINDINGS.md) §6).
* **The account-posture call**: whether a live session may run against an archive
  holding an authored map is the owner's, unmade, and "launch and quit is enough" is
  UNVERIFIED ([studies/crossbuild/FINDINGS.md](studies/crossbuild/FINDINGS.md)).
* **296 map rows are limited by information, not effort**: one live capture on a
  known-named zone yields one exact `(map id, file id)` pair
  ([studies/maprows/FINDINGS.md](studies/maprows/FINDINGS.md)).

### 8.3 Standing residue the studies still call open

Older than September, and each confirmed against something current rather than against
the log alone.

* **Skills** (skills §35.6, §37.6, §38.8): `effects.py`'s `EFFECT_TYPES` still lists
  five types while Well, Ward, Item and Weapon Spell, Form, Chant and Echo are plainly
  timed; the character's own cast-animation duration is NOT FOUND; `GmSkSlot`'s refresh
  at `0x00543020` is an UNVERIFIED second way to clear the overlay; 56 of the 60 refusal
  ids 1934–1993 are RECONSTRUCTION-labelled, not OBSERVED (skills §57). The unmet-weapon-requirement
  term is unmodelled on purpose ([studies/isle/FINDINGS.md](studies/isle/FINDINGS.md) §7).
* **Authored places** ([studies/worldmaps/FINDINGS.md](studies/worldmaps/FINDINGS.md)):
  water and shore, slope materials, narrow-gate clearance and a minimap for a created
  map are untouched. The engine half is green; the presentation half is why the arc
  is paused.
* **The archive** ([studies/crossbuild/FINDINGS.md](studies/crossbuild/FINDINGS.md)):
  nothing has pressured the allocator with many sessions over many maps. Content keyed
  to a durable per-map key (option C) is NOT BUILT: its three candidate keys are REFUTED
  (maprows §10.11–§10.12 — each is a fact about the bytes, which a patch changes), a
  durable key must come from the map id the server sends or an `s_missionClientData`
  join, and it waits for a second archive state.
* **The silent-opcode sweep's residue** ([studies/smsgsweep/FINDINGS.md](studies/smsgsweep/FINDINGS.md)):
  the five account-name selectors (§7.9), and `0x0191` — READ as a map change (§7.5) —
  has no `schema/overrides.json` row.
* **ANIMREF's desk queue** ([studies/animref/FINDINGS.md](studies/animref/FINDINGS.md)):
  §19's second refusal gate — 20 of 39 reason-1960 refusals arrive with the client-rule
  slot exactly at cost (`adrenreplay.py`, 2026-09-22; the simulation is built, the
  variable is not found); §16's visual ids are wired and their appearance is the owner's
  verdict to give.
