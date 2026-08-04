# Rurik — a Guild Wars 1 server emulator + content toolkit

**Handoff brief. Read this first, in full, before writing any code.**

Authored 2026-08-04, at the close of a scoping pass. Sibling project to Dream World IX
(`C:\gd\Dream-World-IX`), from which most of the laws below are ported at the cost of real
playtests.

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

There is no server binary. There never was one to have. Every authoritative behavior — how much
damage Fireball does, where a Charr patrol walks, what an ettin drops — lived only on ArenaNet's
machines and was never shipped to anyone.

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
and `GwLoginClient.dll` (Steam build). GWToolbox already injects GWCA into your client process —
so the capture harness has a host and an API on day one. Build it as a GWToolbox-lineage module,
not as a network sniffer; hooking the client's own StoC dispatch gives you decrypted, framed,
already-typed messages, which is strictly better than pcap.

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
  authentication to an arbitrary address. R1 needs no binary patching. Verify it still behaves this
  way post-Reforged; that check is your first go/no-go.

---

## 5. Architecture

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

## 7. The replay oracle

This is the test strategy, and it is better than anything Dream World IX ever had.

**Take a recorded session. Feed its CtoS stream to your server. Diff your emitted StoC stream
against the recorded one.**

That is a byte-level regression gate against genuine server output. It is as close to a real oracle
as this kind of project gets, and it exists only because of the capture vault — another reason §2
front-loads it.

Build it at R2, the moment you emit your first packet, and grow it continuously. Structure it as:
per-session replay fixtures, a tolerance layer for legitimately nondeterministic fields (timestamps,
ids, RNG), and a ledger of which sessions currently pass.

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

## 10. Repo layout (proposed)

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

## 12. Open questions for the owner

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
