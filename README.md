# Rurik

under development (v0.0.1 or something)

it's a guild wars 1 server emulator + mod kit. 

**research project, not a private server** 
published as information and preservative
there is no public server
as of now - no support, no releases, no roadmap, ignoring issues and PRs (unless you convince me)

[MIT-licensed](LICENSE), with a carve out for some wiki-derived content 
(CC BY-NC-SA 2.5 / GFDL 1.2). 

**no .dat file is distributed**
none of ArenaNet's bytes are here

---

##AI-first project

this project was written to be developed from an agentic coding harness

it is not meant to be developed by hand (though nothing is stopping you from trying)

the codebase is mostly documentation, research, and plans. not meant for human consumption.

**the recommended way to develop, or to ask anything at all, is to open the checkout in
your favorite coding harness and just ask.**
"How does the handshake work?", "why is my client stuck on Connecting to ArenaNet?",
"what would it take to make a new zone?"

questions like these are easy for the agent to find

---

## What you need

- Windows, PowerShell. (this is how i developed it)
- **Your own legally purchased Guild Wars install**
- Python 3. Standard library only — there is nothing to `pip install` for the server path.


## END OF HUMAN AUTHORING, SLOP SETUP BELOW

not much to look at yet. movement code is getting pretty reliable and much of the roadmap is planned

combat is in early days

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
