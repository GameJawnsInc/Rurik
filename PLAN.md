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
| **R4a** | Agent model + combat core | An ettin swings at you and you die | 🔶 **half.** A hostile Hatcher stands in the map, and a click orders an attack the server drives to a kill and a revive (`f8320ff`, `37cb856`, 2026-08-06). **Nothing swings back and the player cannot die**, which is the half the criterion actually names. There is still no agent table — `studies/enemy/PLAN.md` §7.2. |
| **R4b** | The skill substrate | See §3.2 — rewritten as a count | 🔶 **started.** Eight real skills on the bar with correct tooltips (`70c3926`), the cast lifecycle read out of the client's own asserts, `USE_SKILL` answered. **No skill resolves an effect.** |
| **R4c** | AI + spawns + quests | See §3.2 — rewritten as a count | ⬜ not started. |
| **R5** | Declarative authoring toolkit | A new zone in TOML, hot-reloaded, walked | ⬜ not started — but its substrate exists as of `501698b`: `content/*.toml` and `toolkit/content.py`, with the server holding zero content literals. |
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
- **R4c — split, because half of it is blocked and reporting one number hides which.**
  *R4c-1, capture-free*: 19 of 19 map rows with resolved file ids and arrival points that
  pass the spawn-in-trapezoid test (today 2), ≥15 NPC templates (today 1), 2 of 2
  mandatory quests completable, 6 of 6 quest verbs implemented, 4 of 4 services working.
  *R4c-2, capture-gated*: 35–40 monster types with real stats and skill bars, graded on
  **types, never on spawn instances** — spawn counts are unstatable from any source this
  project has. R4c-2 stays at 0 and is **reported as blocked until R0b exists**, which is
  a dependency rather than a failure and the ladder should show it as one.

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

**Q3. Does the provenance gate survive contact?** §9 says "zero ArenaNet bytes in the repo, ever,"
but R0 vaults `Gw.exe` and `Gw.dat` and every schema derives from them. *Recommendation:* restate
the gate as a **derivation graph with a gitignored `build/`** — every derived artifact regenerates
from a documented fetch of a freely downloadable client. That is a stronger and more honest
formulation than a prohibition needing constant qualification, and it matches the owner's own point
that the client is available to anyone.

**Q4. A secondary account for automation?** ✅ **CLOSED 2026-08-06, by the owner.** A second
account is bought. **Automation against the live ArenaNet service on that account is
authorized** — and it "shouldn't be the go-to test mode". Both halves are binding: the
default loop stays hand-driven against our own server, and live automation is a mode you
enter deliberately for a capture campaign, never a convenience left switched on. The
conditions and the machinery that has to change first are §6.2. **A1 is unblocked; it is
not yet safe to run.**

**Q5. Does Pre-Searing remain the finish line?** *Recommendation: yes, unchanged.*

---

## 8. Immediate next actions

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

### 8.0 Next, as of 2026-08-10 (`b185bce`+, suite 37/37 ~960 checks)

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

0c. 🔶 **BUILT 2026-08-10, awaiting one operator run.** Plague Worms hide by being REMOVED
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

1. **Build the capture harness (A1).** *Started 2026-08-06, in build.* Every capture in the
   vault is Rurik talking to Rurik; **not one byte is ArenaNet's**, so R0b is unmet and R1.5
   and R4c's original criterion are both blocked behind it.
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
