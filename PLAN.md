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
| [ldufr/OpenTyria](https://github.com/ldufr/OpenTyria) | A working GW1 **server** in C | 180 commits, last 2026-02-21, **Unlicense (public domain)**, ~25,630 lines of real code |
| [ldufr/Headquarter](https://github.com/ldufr/Headquarter) | A GW1 **headless client** in C | MIT, pushed 2026-07-11, full NCSoft portal stack in `code/portal/` |
| [apoguita/Py4GW](https://github.com/apoguita/Py4GW) | Python scripting layer + packet sniffer | 68★, **4,626 commits**, pushed 2026-07-21; `Py4GW_Reforged_Native` (56 commits, 2026-08-02) explicitly replaces GWCA |
| [gwdevhub/GWToolboxpp](https://github.com/gwdevhub/GWToolboxpp) | The in-client toolbox | 872★, MIT, pushed **2026-08-04 — today** |
| [jean-humann/gwnative](https://github.com/jean-humann/gwnative) | Rust host for the WASM client | GPL-3.0, pushed **2026-08-04 — today** |
| [build-wars/gw-skilldata](https://github.com/build-wars/gw-skilldata) | Community skill dataset | MIT, pushed **2026-08-04 — today** |

Three separate repositories in this ecosystem were pushed to on the day this plan was written. The
same developer, `ldufr`, has independently built both halves of the problem HANDOFF.md treats as
unprecedented. `entice` (the GWLP-R successor org) is genuinely dead — last activity 2016
**[measured]** — so the handoff's pessimism was accurate *as of about 2016* and has not been
revisited since.

**Consequence:** the estimate that "R1 is a few weeks or a research project" resolves to *weeks*,
and the two-year no-output stretch that is this plan's biggest morale risk is not necessary.

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

Why this matters more than it sounds: a WASM module is a structured, typed format, not a stripped
x86 blob. `gw_in_browser` ships `wasmscan.py`, `wasmdetour.py`, `wasmpatch.py` and `gensyms.py`
**[measured — present in the mirror]**. Its own documentation reports full decode of all 17,596
functions, detour capability on every one of them, and — the part that should stop you — **850
original source paths surviving in `.data`**, e.g. `../../../../Gw/Ui/UiRoot.cpp`, letting
`gensyms.py` attribute most functions to their originating C++ file and emit a standard `name`
section that Ghidra and Chrome DevTools both read. Those are that project's self-reported numbers,
not independently reproduced here **[sourced, not measured]**.

Fifteen years of GW1 reverse engineering fought a stripped binary. The WASM build hands over the
map.

**Consequence:** HANDOFF §5's *"capture harness — C++, because it must live inside the client next
to GWCA"* is the highest-friction choice in the plan and it is now optional. The harness can be
Python plus JavaScript — the pairing the handoff already prefers everywhere else.

### 1.4 GWCA is no longer an open dependency

HANDOFF.md §4 calls GWCA *"your most valuable external asset."* As a runtime dependency it is not
available. `GregLando113/GWCA` has been **archived read-only since 2023-11-14** **[measured]**, and
there is no `gwdevhub/GWCA` — that path 404s **[measured]**. The maintained GWCA is closed-source,
vendored into GWToolboxpp as a prebuilt DLL, import library and headers.

**Consequence:** downgrade GWCA from *dependency* to *dictionary*. Its named opcodes and typed
structs remain the best naming corpus in the field. Do not plan to build on its DLL.

### 1.5 R1 is not patch-free, and the reason is specific

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

**Probe 1 — does the portal downgrade to plain HTTP?** *(hours)*
Procedure and outcome table: [studies/handshake/PLAN.md](studies/handshake/PLAN.md) §5, runs A–C.
Run the listener, launch with `-portal 127.0.0.1`, watch port **6601** for a plaintext request
under `/Spawned/WebGate`. **If plaintext:** Stage A is days of work and the captured request body
is your specification. **If TLS (leading `0x16`):** §1.6 is wrong and R1 re-plans around
certificates. Everything downstream branches here.

**Probe 2 — does this build still honour `-authsrv`?** *(hours)*
Run C. Stage A goes to the real service and succeeds, so a connection on 6112 proves both that the
flag works and that Stage B is gated behind a successful portal login. Caution: runs A and B put
real credentials on the command line and into a socket that logs them.

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
| **R1** | Handshake against a local server | Client reaches character select | Probes 1, 2, 4 |
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

**A1 — Proxy first: the two-server trick, and it is already written.** *(days · agent-farmable)*
`toboshii/gw-web-player`'s `serve.py` proxies `/cdn` → the ArenaNet patching CDN, `/webgate` →
login, `/account` → account management, and `/ws?d=HOST:PORT` → **a raw TCP bridge over WebSocket
for the game servers** **[measured — mirrored locally]**. That last route is a complete
bidirectional man-in-the-middle on every byte the client and server exchange, with no DLL
injection, no pattern scanning, no admin rights, and nothing for a client patch to break.
It buys three things in increasing order of ambition: tee both directions to disk (R0b, an
afternoon); run your server in parallel on the real CtoS stream and diff its would-be output
against the real server's while still forwarding the real answer (HANDOFF §7's replay oracle, at
R0 instead of R2, open-loop, self-updating as you play); and then stop forwarding message types
that diff clean and answer them yourself, so the system stays continuously playable and the
project becomes incremental replacement rather than a cold start.
*Wasted if:* the game channel's DH/ARC4 makes the proxy see only ciphertext — but you host the
page, so the crypto boundary inside the module is hookable. *Risk is moderate, not fatal.*
*First step:* Probe 3, then run `serve.py` against your own account.

**A2 — Stand up OpenTyria and see your character.** *(days · human)*
Public domain, ~25k lines, with agent, chat, inventory, item, map, pathfinding, party and title
modules plus SQLite persistence. Even if Rurik never ships a line of its code, building and
running it converts a pile of protocol theory into a working reference you can step through in a
debugger. *Wasted if:* it does not build against the 2026-04-30 client — in which case *why* is
itself the most valuable R1 finding available. *First step:* Probe 4.

**A3 — Adopt the 777-message schema as Rurik's source of truth.** *(days · agent-farmable)*
Translate `msgdefs.c` into the TOML/JSON schema HANDOFF §5 specifies, then codegen from it. Verify
each definition against captures rather than trusting it. This is exactly the work the handoff
scoped, minus the discovery cost, with no license friction. *Wasted if:* the definitions have
drifted from the current build — which the capture stream will tell you, message by message.

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
| Client auto-patches over ground truth | Client pinned and hash-verified in `vault/client/2026-04-30_b174de1f2d8d/` | done |
| **The client phones home when it crashes** | `Gw.exe` embeds Sentry: `SENTRY_DSN`, `sentry.native`, `getsentry`, `x-sentry-rate-limits` are all present **[measured]**. The working method here is inject, patch, malform, crash — so the client's own outbound reporting channel is a posture problem HANDOFF §9 never considered, since §9 reasons only about server-side visibility. Neutralise it before the first malformed packet: block the endpoint at the firewall or null the DSN in the patched copy. Minutes, and it belongs on the R0 checklist next to the vault snapshot. | minutes |
| Account loss | Never automate on the primary account. The proxy posture — watching your own traffic — is milder than injecting a DLL, which is what the original plan required | one account |
| A client update invalidates months of offset work | Choose WASM: the module bytes are the code and offsets come from the module | free, if you switch |
| Two years with nothing playable | A2 and R1.5 both target a visible result inside 90 days | — |

---

## 7. Open questions for the owner

**Q1. Build on OpenTyria, or learn from it and stay independent?** *Recommendation: learn from it,
stay independent, and vendor nothing except `msgdefs.c` (public domain).* Rurik's actual goal is
the declarative authoring toolkit, and inheriting 25k lines of someone else's C server architecture
would fight that. But build it and run it first — the fastest route to understanding the stack.
*Counterargument worth weighing:* if it already reaches R2–R3, refusing it may cost a year of
rebuilding for purity.

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
1. **Run Probe 1** — [studies/handshake/PLAN.md](studies/handshake/PLAN.md) §5 run A. Everything branches here.
2. **Run Probe 2** — run C. Confirms `-authsrv` on this build.
3. **Dump the client's packet-template table** (§1.2), then read
   `vault/mirrors/OpenTyria/code/msgdefs.c` as the naming layer and reconcile the two. Any
   disagreement with the client's own `template_size` is a mechanically detectable defect.
4. **Build OpenTyria** and try to connect a *patched copy* of the client. Never patch `C:\gw`.
5. **Run Probe 3** — `wasmscan.py` + `gensyms.py` from `vault/mirrors/gw_in_browser`.
6. **Stand up the proxy** from `vault/mirrors/gw-web-player/serve.py`; tee both directions to `vault/captures/`.
7. **Translate `msgdefs.c`** into `schema/` and generate the first parsers. Agent work.
8. **Dump the skill table** via a WASM detour on the skill-lookup function. Agent work.
9. **Install a .NET SDK** if the C# server core survives Q2 — only the 6.0 runtime is present, and
   the plan calls for 8+. Defer until the language decision is settled.
10. **Re-run `toolkit/mirror_priorart.py`** monthly. Repos in this ecosystem vanish.
