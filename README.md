# Rurik

A private, local Guild Wars 1 server emulator plus a content toolkit. You point the
retail client at your own machine, and it logs in, renders your character, loads a real
map and walks on the game's own geometry.

**Limited private release.** This is one person's research project, shared with a few
people. There is no public shard, no support, no releases and no roadmap promises. If
you are reading this, you were handed it directly.

**Where the project actually is: [PLAN.md](PLAN.md) §3.** That table is the single
status authority — dated, and stamped with a commit hash per rung. This file deliberately
does not restate it, because every document here that tried went stale and disagreed.

---

## This is an AI-first project

Rurik is written to be worked on with an agentic coding harness, and it is not really
optimised for reading by hand. The reasons are structural, not stylistic:

- The documentation is larger than the code. `PLAN.md` is over a megabyte, `TESTS.md`
  approaching one, and `studies/` holds sixty-odd research arcs of measured findings.
  Nobody reads that; you ask questions of it.
- Every claim is labelled by confidence — OBSERVED, UPSTREAM, RECONSTRUCTION,
  CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND — so an agent can tell what was
  measured from what was assumed, and so can you when it quotes back.
- Most findings are the result of capturing the real client and reading it. The
  provenance of a number matters more than the number, and it travels with the number.

**The recommended way to develop, or to ask anything at all, is to open the checkout in
[Claude Code](https://claude.com/claude-code) (or a comparable harness) and just ask.**
"How does the handshake work?", "why is my client stuck on Connecting to ArenaNet?",
"what would it take to make a new zone?" — all of those are answerable from this repo,
and answering them is what its layout is for.

[CLAUDE.md](CLAUDE.md) is the house rules and is loaded automatically. Read it yourself
before your first session: it carries the non-negotiables below, and the reasoning for
each one is the expensive part.

---

## What you need

- Windows, PowerShell.
- **Your own legally purchased Guild Wars install**, at `C:\gw`. Rurik reads bytes out
  of it; it never patches or launches it.
- Python 3. Standard library only — there is nothing to `pip install` for the server path.

Nothing ArenaNet-authored ships in this repo. Everything derived regenerates from your
own install through the extraction steps below.

## Setup — one time, and again after every ArenaNet update

The client's Diffie-Hellman parameters rotate with every build, so a patched copy from
last week keys to nothing.

```bash
python toolkit/snapshot_client.py
python toolkit/clientpatch/make_custom_client.py
python toolkit/clientpatch/make_run_dir.py
```

1. **Snapshot** copies `C:\gw` into the vault and verifies it byte-for-byte. Exit `3`
   means a file was locked — close Guild Wars and re-run.
2. **Patch** writes fresh DH parameters into a *copy*, saves the private half to
   `vault/keys/`, and ends with `B == g^b mod p -> True`. If that says `False`, stop.
   **Keep that key file** — the server needs it to decrypt, and without it the patched
   client is a brick.
3. **Stage** assembles `vault/run/<build>/` with the exe, `Gw.dat` and the DLLs (~4.2 GB,
   a few seconds) and prints the exact launch command for your build.

If you are about to accept a client update, snapshot the before-state first
(`python toolkit/updatecheck.py --before --snapshot`) — afterwards it is gone.
Full procedure, including the live-capture build, is in [RUNBOOK.md](RUNBOOK.md).

## Getting into a map

Check it works without the game first. A red test names the broken thing; the client
says `Code=058` thirty seconds later and tells you nothing.

```bash
python toolkit/run_suite.py
```

Then one command drives the whole thing:

```bash
python toolkit/harness/session.py
```

It pre-flights the ports, starts the three servers (portal, auth, game catalog) and
proves each owns its port, launches the client, drives login → EULA → Play with
focus-verified clicks, and judges the run from the client's own messages — one
`[PASS]`/`[FAIL]` line per checkpoint. The report, server logs and screenshots land in
`vault/captures/harness/<stamp>/`.

Useful flags:

```bash
python toolkit/harness/session.py --game-args "--map 280"   # Isle of the Nameless
python toolkit/harness/session.py --until login             # stop at character select
python toolkit/harness/session.py --serve                   # just the stack, no client
```

`--map 280` is the map to reach for: the archives agree on it, it is explorable, it has
training dummies, and its spawn is retail's own arrival position. Many rows in
`content/maps.toml` have no known spawn point and will drop you at the world origin, off
the mesh, unable to move.

Running the stack by hand in separate terminals, what a good run looks like line by line,
and a failure table covering roughly every way this goes wrong are all in
[RUNBOOK.md](RUNBOOK.md).

---

## Rules that are not negotiable

These are enforced in code where they can be, and the full reasoning is in
[CLAUDE.md](CLAUDE.md). Read it before you work around any of them.

- **Never point a client carrying our Diffie-Hellman parameters at the real service.**
  It does not fail cleanly, and it fails *after* a real login with whatever credential
  the client autofilled. The two builds are byte-identical in every other respect, so
  never select one by filename — `python toolkit/clientpatch/dhbuild.py` reads the struct
  and answers `ours` / `stock` / `unknown`, and the launch sites refuse the wrong pairing.
- **Zero ArenaNet bytes in the repo, ever.** No client files, no `Gw.dat`, no extracted
  assets, no decompiled code. Measurements are permitted and carry per-row provenance;
  ArenaNet's expression is not.
- **The vault stays local.** `vault/` holds captures, keys and client snapshots. It is
  gitignored, it is personal data from your own account, and it never goes on the internet.
- **Never patch or launch anything under `C:\gw`.** That install is read-only to us.
- **Local and personal only.** No public shard.

Third-party work this project draws on is credited in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md); the derivation register is `PLAN.md` §6.1.

## Map of the repo

| Path | What it is |
|---|---|
| `toolkit/portal/`, `toolkit/authsrv/` | The server: portal (6601), auth + ARC4 channel (6112) |
| `toolkit/harness/` | Drives the client — the session runner, capture, tape playback |
| `toolkit/schema/`, `schema/*.json` | Codec and the wire message catalog |
| `content/*.toml` | The world: maps, NPCs, items, spawns. One row per fact, each with its own provenance |
| `toolkit/clientscan/`, `toolkit/clientpatch/` | Read-only client analysis; patching and the firewall cage |
| `toolkit/mapdata/` | `Gw.dat` reader, planner, writer, textures |
| `studies/` | Per-arc research, labelled by confidence. The real documentation |
| `vault/` | Gitignored. Snapshots, keys, captures |

[HANDOFF.md](HANDOFF.md) is the original strategy brief, kept with its wrong premises
struck in place rather than deleted. [TESTS.md](TESTS.md) is the test catalog — read it
when you touch a module, not to run the suite.
