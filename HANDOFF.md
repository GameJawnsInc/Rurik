# Rurik — a Guild Wars 1 server emulator + content toolkit

**Handoff brief. Read this first, in full, before writing any code.**

Authored 2026-08-04, at the close of a scoping pass. Sibling project to Dream World IX
(`C:\gd\Dream-World-IX`), from which most of the laws below are ported at the cost of real
playtests.

> **⚠ READ THIS BEFORE ACTING ON ANYTHING BELOW — annotated 2026-08-14.**
>
> This document was written **before a line of code existed**, and it is the reasoning
> that started the project rather than a description of it. It is kept because the
> *strategy* held: the live game is the donor, capture is the wasting asset, R4 is
> archaeology and not invention. Every one of those is still true and still load-bearing.
>
> But **six of its concrete premises have since been MEASURED, and they were wrong.** They
> are struck in place below, each pointing at the section of [PLAN.md](PLAN.md) that
> measured it — §7 was already struck this way on 2026-08-13 and that is the pattern.
> Nothing here is deleted, so that nobody re-proposes it.
>
> | Where | What it claims | Measured |
> |---|---|---|
> | §1 | "There never was one to have" (a server binary) | `PLAN.md` §1.8 — **there was**, and `Gw.exe` embeds 937 of its build-machine source paths |
> | §1 | Prior attempts produced "zero playable outcomes" | `PLAN.md` §1.1 — two working implementations exist; what nobody has built is **R4** |
> | §3, §5, §10 | Build capture as an in-process GWCA/GWToolbox module, "not as a network sniffer" | `PLAN.md` §1.2b/§1.4 — GWCA is archived; **route C, off-wire**, is what was built |
> | §3 | Skill effects are recoverable "only [from] the live service" | `PLAN.md` §1.7 — skill numerics ship **in the client**; only four things are truly server-only |
> | §4 | "R1 needs no binary patching" | `PLAN.md` §1.5/§1.5b — the client's DH public key is baked in; **R1 has needed a patched client since day one** |
> | §5, §10 | A C#/.NET server core, and a `docs/`+`capture/`+`server/`+`oracle/` layout | ~18,000 lines of **Python** server exist and none of those directories do — `CLAUDE.md`'s Layout table is the real map. The language decision is formally still open: `PLAN.md` §8 item 8 |
>
> **Where the project actually is: [PLAN.md](PLAN.md) §3, and nowhere else.** This file
> deliberately does not say, and §2's ladder below is the *original* ladder, not a status.

---

## 0. What this is, and the decision already made

**Goal:** a private, local Guild Wars 1 server that runs authentic content — skills, monster AI,
quests, drops — plus a declarative toolkit for authoring new content on top of it. Rungs R4
(simulation) and R5 (toolkit) are the *target*. R0–R3 are prerequisites, not the deliverable.

**The cost was scoped and accepted.** Roughly fifteen years of intermittent community attempts
(GWLP-R in Java, sgwlpr in Scala) produced zero playable outcomes; TrinityCore took a decade and a
large community to reach the equivalent of R4 for WoW. This is a multi-year solo effort. The owner
has heard this and chosen it anyway. Do not re-litigate the scope in later sessions — argue about
*sequencing*, never about whether R4 is worth reaching.

**What the scoping pass changed:** targeting R4 reorders the ladder. See §2. That is the one
structural consequence of the decision, and it is time-sensitive.

---

## 1. The central problem, and its answer

There is no server binary. ~~There never was one to have.~~ Every authoritative behavior — how much
damage Fireball does, where a Charr patrol walks, what an ettin drops — lived only on ArenaNet's
machines and was never shipped to anyone.

> **❌ "There never was one to have" is REFUTED — [PLAN.md](PLAN.md) §1.8,
> [studies/srvtree/FINDINGS.md](studies/srvtree/FINDINGS.md).** There *was* a server
> binary; it simply never shipped. `Gw.exe` embeds **937 distinct `P:\Code\…`
> ArenaNet build-machine source paths**, every gameplay subsystem sitting under a
> client-only marker, on two builds four months apart — client and server were two build
> targets compiled from **one shared source tree**. The first sentence survives and is
> the one that matters. The second changes what is worth *looking* for, which is why it
> is struck rather than deleted.
>
> **Also REFUTED, and it is the premise this whole section argues from:** the "roughly
> fifteen years … produced zero playable outcomes" line above. [PLAN.md](PLAN.md) §1.1
> tables **OpenTyria** (a working GW1 server in C, Unlicense) and
> **gw-preservation/server** (Go, 397 map definitions, working navmesh and pathing,
> pushed hours before this document was written). The sharper claim survives and is
> worth more: **nobody has ever built R4.**

Naive framing: *R4 is pure authorship.* That framing is fatal. Dream World IX established, over
thirteen playtest verdicts in the Path-D arc, that **the defect follows the authorship** — 12 of 13
verdicts and 32 of 37 named defects landed on whatever the round had most recently invented. A
project that is 100% authorship has no ceiling on its defect rate. Under that framing Rurik fails,
and it fails slowly, over years, which is the worst way to fail.

**The answer: the live game is your donor.**

The official service is running right now. Guild Wars Reforged shipped 3 Dec 2025 and a mobile
client on 24 Jun 2026 — the service is actively invested in and is not going away this month. While
it is up, every question you will ever ask about R4 is empirically answerable:

- What does the server send when a Fireball lands? Cast one and record the packets.
- Where do the Charr in Old Ascalon spawn? Zone in twenty times and record the agent-create stream.
- What are an ettin's stats? Read them off the wire.
- What does the quest-accept handshake look like? Accept a quest and record it.

This converts R4 from invention into **archaeology**, which is the exact discipline Dream World IX
is built on and good at: *study real bytes → replicate ONE piece → verify.* It is the verbatim-first
law, relocated from a disk image to a network socket.

**It is also a wasting asset.** Every observation you have not captured before the service changes
or closes is an observation you will have to invent instead. This is the single fact that should
drive your sequencing for the next year.

---

## 2. The reordered ladder

The naive order is R0→R5. The correct order for this goal front-loads capture.

| Rung | Deliverable | Acceptance criterion |
|---|---|---|
| **R0** | Ground-truth vault: pinned client, `Gw.dat` extraction, **the capture harness** | A recorded session replays byte-identically from disk |
| **R1** | Handshake: client connects to `127.0.0.1` and gets past auth | Client reaches character select against your server |
| **R2** | Presence: character loads into an outpost | You see your own body standing in a real map |
| **R3** | Movement on real geometry | You can walk to a wall and be stopped by it |
| **R4a** | Agent model + combat core | An ettin swings at you and you die |
| **R4b** | The skill substrate | One skill from each mechanical family resolves correctly |
| **R4c** | AI + spawns + quests | An area populates and plays like the recording |
| **R5** | Declarative authoring toolkit | A new zone authored in TOML, hot-reloaded, walked |

> **⚠ THE RUNG NAMES IN THIS TABLE ARE STALE — annotated 2026-08-20. The ordering
> argument below them is NOT.** Authority for the ladder and for every rung's status is
> [PLAN.md](PLAN.md) §3, and nowhere else. Read the names here as the 2026-08-04
> vocabulary rather than the current one:
>
> | Here | In `PLAN.md` §3 |
> |---|---|
> | **R0** | **Split in two.** **`R0a`** — vault + provenance gate + prior-art mirrors (✅ 2026-08-04, criterion met 2026-08-07). **`R0b`** — **instrumented-client capture of a real live session**, both directions, stamped `origin: live` and byte-replayable (✅ 2026-08-07) |
> | — | **`R1.5` — tape player.** Added after this was written: a recorded StoC stream replayed at recorded timing walks a real client through Ascalon City (✅ 2026-08-10) |
> | — | **`R5m` — custom map geometry, end to end.** Added after this was written: a map we authored loads in the retail client and geometry we chose stops the character (✅ 2026-08-11) |
>
> **The R0 split VINDICATES this section rather than correcting it.** §2's headline call
> is *"R0 is where the capture harness gets built, not R4"*, and `R0b` is precisely that
> rung carrying precisely that deliverable — landed third, on 2026-08-07, four days in.
> The strategy held; only the vocabulary moved. What is genuinely wrong above is
> narrower: the `R0` row folds the vault and the live capture into one line, and they
> are two rungs that landed three days apart against two different servers.
>
> **Do not hand-sync this table to §3.** Nothing in this file is deleted or rewritten to
> match a later measurement — see the box at the top, and the reason: a struck premise
> that stays visible is what stops it being re-proposed. Duplicating §3's rows here is
> also the mechanism that produced this drift in the first place, and re-syncing them
> only resets the clock on it.

**R0 is where the capture harness gets built, not R4.** This is non-obvious and it is the most
important sequencing call in this document. You will not be able to *use* most of what you capture
for two years. Capture it anyway. Record broadly and early: every profession's skill bar, every
starting zone, every quest chain you can stomach, PvE and PvP, henchmen behavior, death, resurrection,
zoning, trade, storage. Store it as raw framed packet logs with timestamps and a session manifest —
do not pre-parse, because your parser will be wrong for the first year and raw bytes are re-parseable.

Corollary: **archive capture logs immediately and redundantly.** Dream World IX lost captures to a
shared install being overwritten mid-session. These are irreplaceable in a way source code never is.
Treat the vault as the most valuable artifact in the repo — because if the service closes, it is
the only part that cannot be reconstructed.

---

## 3. Ground-truth inventory

| Layer | Where it lives | Difficulty |
|---|---|---|
| Wire framing, encryption, handshake | client binary | hard, one-time, mostly solved by prior art |
| StoC/CtoS packet catalog | client + **GWCA** | largely already done — see §4 |
| Map geometry, models, pathing, textures | `Gw.dat` | tooling exists (GuildWarsMapBrowser) |
| Skill/item/quest display data | client tables | extractable |
| **Skill effects, AI, spawns, drops, quest logic** | **only the live service** | **capture, per §2** |

Your install is at `C:\gw` and already contains `Gw.exe`, `Gw.dat`, `GWToolbox.exe`, `gMod.dll`,
and `GwLoginClient.dll` (Steam build). ~~GWToolbox already injects GWCA into your client process —
so the capture harness has a host and an API on day one. Build it as a GWToolbox-lineage module,
not as a network sniffer; hooking the client's own StoC dispatch gives you decrypted, framed,
already-typed messages, which is strictly better than pcap.~~

> **❌ The capture route is REFUTED, and the opposite was built — [PLAN.md](PLAN.md)
> §1.2b and §1.4, [studies/livekey/CAPTURE.md](studies/livekey/CAPTURE.md).** Three
> things went wrong with this paragraph. **GWCA is archived read-only** (since
> 2023-11-14, no live fork) so it is a *dictionary* now, not a runtime dependency.
> **The owner chose route C, off-wire packet capture** — `toolkit/harness/wirecapture.py`,
> WinDivert-backed, which is precisely the "network sniffer" this told the reader not to
> build; an in-process hook was rejected as the most detectable change. And this
> paragraph **contradicts §11 step 4**, which asks the same hook for *raw framed packets*
> while this one promises *already-typed messages* — §1.2b is about that.
>
> **Also REFUTED, one row up in the table above:** "Skill effects, AI, spawns, drops,
> quest logic | **only the live service**". [PLAN.md](PLAN.md) §1.7 measured that
> substantially overstated — the client ships a **static 160-byte skill record** carrying
> energy cost, adrenaline, activation, aftercast, recharge and the two-point rank-scaling
> model R4b needs, readable with no server and no capture. Only four things are genuinely
> server-only on the evidence. AI is the row that survives hardest, and *more* than this
> claims: [studies/monsterai/FINDINGS.md](studies/monsterai/FINDINGS.md) finds it is not
> recoverable **even by capture**, only its observable envelope.

---

## 4. Prior art — what to take, what to ignore

- **GWCA** (`github.com/GregLando113/GWCA`, and the `gwdevhub` fork) — a C++ in-process API for the
  client, carrying reverse-engineered StoC packet structs. Its StoC handler work descends from the
  old *GWLP Dumper*, meaning the dead emulator projects' protocol corpus survived inside a
  maintained client-side project and kept growing. **This is your most valuable external asset.**
- **GWToolbox++** (`github.com/gwdevhub/GWToolboxpp`) — 872 stars, actively committed. The
  reference for how to live inside the client process without breaking it. Already on your machine.
- **GuildWarsMapBrowser** (gwdevhub) — `.dat` map extraction. Start here for R0's asset half.
- **GWLP-R** (`github.com/GameRevision/GWLP-R`) — Java, deprecated, ~341 commits, never reached
  playable. Read its protocol notes; **do not read its architecture as a template.** It died of the
  thing this document is trying to avoid.
- **sgwlpr** (`github.com/th0br0/sgwlpr`) — Scala rewrite, also abandoned. Same treatment.
- **`-authsrv <ip>`** — an officially documented `Gw.exe` command-line argument that redirects
  authentication to an arbitrary address. ~~R1 needs no binary patching.~~ Verify it still behaves this
  way post-Reforged; that check is your first go/no-go.

  > **❌ "R1 needs no binary patching" is REFUTED — [PLAN.md](PLAN.md) §1.5 and §1.5b**,
  > measured against this project's own binary. The flag redirects *where* the client
  > dials, but `Gw.exe`'s `.rdata` carries a pinned Diffie-Hellman blob including
  > **ArenaNet's own baked-in public key**, so no server we control can key the auth
  > channel without patching the client. R1 has run on a patched build since day one.
  > This is not a footnote: it is the origin of the entire
  > `client-patched/` vs `client-patched-live/` vault split, of
  > `toolkit/clientpatch/dhbuild.py`, and of `cage.assert_launch_safe` — i.e. of the
  > non-negotiable in `CLAUDE.md` that exists to stop an account being closed. **Read
  > that rule before launching anything.**

---

## 5. Architecture

> **⚠ SUPERSEDED IN PRACTICE, and the decision is formally still open —
> [PLAN.md](PLAN.md) §8 item 8.** None of this split was built. There is **no C#**
> and **no C++** anywhere in the repo: the server is `toolkit/authsrv/` +
> `toolkit/portal/`, ~18,000 lines of **Python**, and `CLAUDE.md` binds all of
> `toolkit/` to the standard library (with three named carve-outs, one of which —
> 2026-08-12, `PLAN.md` §7 Q6 — permits a native toolchain where it earns its cost).
> The capture harness is Python too, per §3's annotation above. `PLAN.md` §8 item 8
> records that the owner has **not** ruled on whether to strike the C# recommendation,
> so this is marked superseded-in-practice rather than refuted — but **no cold session
> should read the bullets below as an instruction to start writing C#.**
>
> The paragraph that *did* hold, and holds hard: **generate, don't hand-write, the
> packet layer.** `schema/messages.json` is that single source, and `test_catalog.py`
> checks it against the client's own format tables at 477/477.

**Recommended split, mirroring Memoria (C#) + ff9mapkit (Python) in Dream World IX:**

- **Server core — C# / .NET 8+.** Hot reload, fast iteration, strong tooling, and perf is a
  non-issue (a GW instance is ≤8 players plus a few hundred agents; this is not a load problem).
  Iteration speed matters more than throughput here by two orders of magnitude, and R4 is a
  content-volume problem, not a performance problem.
- **Toolkit + offline tooling — Python.** Capture parsing, `.dat` extraction, content linting,
  codegen, the replay oracle. Matches existing muscle memory and is the right language for the
  data-wrangling half.
- **Capture harness — C++,** because it must live inside the client next to GWCA. Keep it thin: hook,
  frame, timestamp, write. All intelligence belongs in the Python side, offline, where it can be
  re-run against the raw vault when your understanding improves.

**Generate, don't hand-write, the packet layer.** Extract the packet catalog into a machine-readable
schema (TOML/JSON) and codegen the C# structs, the Python parsers, and the capture harness's framing
from that one source. Hand-maintaining three parallel copies of 400+ packet definitions is how this
project dies of paper cuts.

---

## 6. R4b — the skill mountain, and why it is R5

~1,300 skills is the number that scares people off, and it is the wrong number to be scared of.

Skills are not 1,300 bespoke implementations. They are a **combinatorial system over a small set of
primitives**: damage packets, conditions, hexes, enchantments, stances, shouts, spirits, echoes,
interrupts, energy and adrenaline costs, activation and recharge. Most of the 1,300 are data rows
over maybe two dozen mechanisms.

So the correct move is to find the substrate first and let the content be declarative — which is
precisely the `field.toml` lesson: *the authoring layer goes on top of a proven substrate, never
before it.* Build an effect DSL, prove it against captures for one skill per mechanical family, and
then the remaining ~1,250 are data entry against recorded ground truth rather than 1,250 acts of
invention.

**This collapses R4b and R5 into the same project.** The skill DSL *is* the toolkit. If you find
yourself writing R5 as a separate authoring layer bolted onto a hard-coded R4, stop — you have
built the thing twice and the second one will disagree with the first.

Same argument for R4c: monster AI is patrol/aggro/pull/flee/skill-use behavior trees. Dream World IX
already proved a behavior-tree compiler that turns designer trees into engine bytecode; the design
lesson ports directly even though no code does.

---

## 7. The replay oracle — ❌ REFUTED 2026-08-13, and struck

**This section was wrong, and it was wrong for eight days while calling itself the test
strategy.** It is kept rather than deleted so nobody re-proposes it; the refutation is
short and it is decisive. Full record:
[studies/recon/FINDINGS.md](studies/recon/FINDINGS.md) §5.5.

*What it used to say:* take a recorded session, feed its CtoS stream to your server, diff
your emitted StoC against the recorded one — a byte-level regression gate against genuine
server output. Build it at R2, with a tolerance layer for nondeterministic fields
(timestamps, ids, RNG) and a ledger of which sessions pass.

**ArenaNet's own server fails that gate against its own recording.** Same character, same
account, same map, same session, minutes apart: **11 of 2,633 messages and 95 of 41,997
bytes identical — 0.2%, diverging at message 6.** The comparison is not broken; the
identical method reports **99.3% opcode-sequence agreement** (LCS 295/297, histogram cosine
1.0000) on the very pair that is 5.4% byte-identical. **A gate that cannot go green cannot
go red for a reason**, which is this project's own standing rule about checks that cannot
fail, arriving from the other direction.

**The tolerance layer does not save it, and the reason is worth keeping.** The obvious one —
mask the first three dwords — lifts same-map agreement to 88–94%, but it blanks **45% of
bytes and 60–68% of messages entirely**, and it scores **76.8–97.5% on *different maps***.
It is vacuous by its own control. A non-vacuous layer must know which of **540 (opcode,
field) slots** is an agent id, a timestamp or an RNG draw — and `schema/overrides.json`
names **zero fields in the whole file**. `test_catalog`'s 477/477 pins field *types*, which
is precisely the axis that does not help. So the oracle is a semantic-annotation project
wearing a replay project's clothes, it is larger than the thing it enables, and it returns
**noise, not partial value, from partial work**.

**The prize was already banked by cheaper means.** `studies/divergence/FINDINGS.md` D1–D11
*is* the oracle's intended output — the ranked, named list of where our server diverges from
ArenaNet's — produced by histogram comparison, and `toolkit/authsrv/msgmix.py` is its tool.

**What replaces it, and it must never be called an oracle:** a *structural* load-prefix
conformance gate. Compare the opcode *sequence* of an instance load rather than its bytes,
which needs no field semantics and has a built-in negative control — different-map pairs
score 3.5–20% against same-map 99.3%. Scope caveat, stated because the number is seductive:
**that 99.3% is n=2 connections on one map.** Segment a second map's load prefix before
building anything on it.

**But hold the line from Dream World IX: a green gate is not an oracle.** Measured over the Path-D
arc, 0 of 13 playtest verdicts were predicted by a gate, because every gate scored against marginals
nobody had asked the right question about. The replay oracle is much stronger than those gates were —
it compares against real output rather than against a statistic — but it still only proves *you
reproduce the situations you recorded*. It cannot tell you the game feels right. Only playing can.

Which is Rurik's one genuine advantage over Dream World IX: **the owner can play this one.** Use it.
Every rung ends in actually playing, not in a green suite.

---

## 8. Laws ported from Dream World IX

Each of these cost real rounds there. They are not aspirational.

- **Verbatim-first.** Real bytes → replicate ONE piece → verify. Offline agreement is not proof.
- **One change per test.** When it breaks, you must know which edit did it.
- **The defect follows the authorship.** The cheapest way to stop minting defects is to stop
  minting surface. Before writing a mechanism, ask whether the client even reads it.
- **A green gate is not an oracle.** See §7.
- **A law in a docstring is a wish.** A rule not enforced at the call site is not enforced.
- **Calibrate the instrument before you judge with it.** A probe that cannot reproduce the
  lifecycle cannot falsify a lifecycle bug. An empty tempdir is not a clean room.
- **A check that cannot fail.** Break your gate deliberately to prove it can go red.
- **Commit freely at tested milestones.** Granular trail, good messages.
- **Ask for video early on anything visual or positional.**

---

## 9. Hard constraints

- **Provenance gate: zero ArenaNet bytes in the repo, ever.** No client files, no `Gw.dat`, no
  extracted assets, no decompiled code. The repo contains *your* code and *your* observations.
  Everything derived regenerates from the owner's own legally-purchased install, via a documented
  extraction step. This is the same gate Dream World IX holds and it must stay clean from commit one
  — retrofitting provenance is not possible.
  **The gate has not moved, but its BOUNDARY has been written down since — read
  `CLAUDE.md`'s version before refusing anything on this paragraph's authority**
  ([PLAN.md](PLAN.md) §7 Q3, owner's ruling 2026-08-11, refined 2026-08-12). The
  boundary is **MEASUREMENT vs EXPRESSION**, not code vs observations: facts we
  measured — levels, bounds, counts, strides, ids, offsets, addresses, layouts — are
  **permitted in bulk** on three conditions, while ArenaNet's expression (asset bytes,
  `Gw.dat` chunks, textures, audio, model data, decompiled bodies) stays refused. The
  second sentence of this bullet is the permission that makes derived data work, and
  it went unread for four days at real cost. **The direction of error in this repo is
  OVER-refusal**, every recorded provenance mistake has been a refusal rather than a
  disclosure, and one session's literal reading of the strict form generated 46
  document rewrites that were all reverted. Full record:
  [studies/provenance/FINDINGS.md](studies/provenance/FINDINGS.md).
- **The capture vault is personal data from your own account, and stays local.** Recording your own
  client's traffic for personal reverse engineering is one thing; publishing a corpus of a live
  commercial service's server output is a different thing with a different answer. Vault stays out
  of the repo and off the internet. Add it to `.gitignore` before you record anything.
- **Local and personal only. Do not run a public shard.** Guild Wars is not an abandoned service —
  it is a $19.99 product that got a mobile launch eight weeks ago. The posture that makes this a
  defensible personal RE project is exactly that nobody else plays on it.
- **Never contribute to or open PRs against upstream client-side projects on this project's behalf**
  without an explicit decision — GWToolbox is tolerated precisely because of how it has behaved, and
  associating an emulator with it is not your call to make unilaterally.
- **Pin the client version and back it up.** Reforged "modernized infrastructure"; existing owners
  were auto-upgraded. Your ground truth is a moving target maintained by someone else. Snapshot
  `Gw.exe` and `Gw.dat` to a versioned vault now, and record the build id in every capture manifest.
- **Back up before editing anything in `C:\gw`.** That is a live install and the only source of truth.

---

## 10. Repo layout (proposed) — ⚠ SUPERSEDED; the real map is `CLAUDE.md`'s Layout table

> **Four of these directories were never created and never will be.** `docs/` (protocol
> prose lives in `studies/<arc>/`), `capture/` (no C++ — §3's annotation), `server/`
> (no C# — §5's annotation), and `oracle/` — which is not merely unbuilt but **REFUTED
> by §7 of this very document**, so do not create it. What exists instead: `toolkit/`
> (all Python, subdivided `authsrv`/`portal`/`schema`/`clientscan`/`clientpatch`/
> `harness`/`mapdata`), `content/`, `schema/`, `studies/`, `tools/`, and the gitignored
> `vault/`. **`CLAUDE.md`'s Layout table is the authority.** The two lines below that
> did hold are `studies/<arc>/` and `vault/`, and they are the two this project leans
> on hardest.

```
C:\gd\Rurik\
  HANDOFF.md            <- this file
  CLAUDE.md             <- write after R0; keep it LEAN, same house rules as Dream World IX
  docs/                 <- protocol notes, packet catalog prose, decisions
  schema/               <- packet definitions (source of truth for codegen)
  capture/              <- C++ GWCA-lineage harness (client-side)
  server/               <- C# server core
  toolkit/              <- Python: dat extraction, capture parsing, codegen, linting
  oracle/               <- replay harness + fixture index (fixtures themselves are gitignored)
  studies/<arc>/PLAN.md <- per-arc research and open status, Dream World IX convention
  vault/                <- GITIGNORED. captures, client snapshots, extracted assets
```

---

## 11. First session — do exactly this

1. `git init`, add `.gitignore` with `vault/` **before** anything else exists.
2. Snapshot `C:\gw\Gw.exe` and `C:\gw\Gw.dat` into `vault/client/<build-id>/`. Record the build id.
3. **The go/no-go probe:** launch `Gw.exe -authsrv 127.0.0.1` with a socket listening, and look at
   what arrives. Does the post-Reforged client still speak the documented handshake to an arbitrary
   address? This single fact determines whether R1 is a few weeks or a research project, and it
   gates everything downstream. Write the result up in `studies/handshake/PLAN.md` either way.
4. Regardless of the probe's outcome, **start the capture harness.** It does not depend on the
   answer, and it is the wasting asset. GWToolbox is already injecting into your client; a module
   that hooks StoC dispatch and writes framed, timestamped raw packets to `vault/captures/` is the
   highest-value thing in the project and the least likely to be invalidated by anything you learn
   later.
5. Only then write `CLAUDE.md`.

---

## 12. Open questions for the owner — ⚠ **none of these three has been ruled on**

> **Checked 2026-08-14, and the honest answer is uncomfortable: all three are still
> open, and all three have been settled by PRACTICE instead.**
> [PLAN.md](PLAN.md) §7 is where owner rulings live. It carries Q1–Q6, of which exactly
> **three are ✅ CLOSED by the owner** — Q3 the provenance boundary (2026-08-11),
> Q4 the secondary account for automation (2026-08-06), Q6 the native-toolchain
> carve-out (2026-08-12) — **and none of those three is a question this section asked.**
>
> - *Which client is canonical* — **not in §7 at all.** Flagged here as needing a
>   decision "before R1, not discovered during it"; everything from R1 to R5m has since
>   landed against build **38797**, the Reforged build the install auto-updated to.
> - *What is "done"?* — carried into §7 as **Q5**, which still reads
>   *"Recommendation: yes, unchanged"* and has no ruling. Pre-Searing is the de facto
>   target and `studies/presearing/MANIFEST.md` is built on it.
> - *PvE only for v1?* — **not in §7 at all.** Deferred by never being started.
>
> Each is a defensible answer. None was ever *made* as one, which is the difference the
> §7 table exists to record — and the first one's cost is visible every time a client
> update threatens the pinned addresses (`toolkit/updatecheck.py`).

- **Which client is canonical** — the Reforged build, or is a pre-Reforged client still obtainable?
  If prior RE work targets the older protocol, this is a real fork in the road and it should be
  decided before R1, not discovered during it.
- **What is "done"?** R4c is infinite unless bounded. A defensible v1 is *one campaign's starting
  region, playable solo end to end* — Pre-Searing Ascalon is the obvious candidate: self-contained,
  small skill surface, well-defined edge, and it is the part of the game most worth having back.
  Recommend adopting that as the R4 finish line and treating everything past it as post-1.0.
- **PvE only for v1?** PvP has a much harder correctness bar and no single-player fallback. Recommend
  deferring it entirely.

---

*Prince Rurik died on the wrong side of the Shiverpeaks. Aim for Pre-Searing and you will be fine.*
