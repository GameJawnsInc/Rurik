# Handoff — the archive-write arc, 2026-08-18

Read this first, then [FINDINGS.md](FINDINGS.md). `PLAN.md` §3 is still the single status
authority; this file is the working state of one arc, not a status table.

---

## 1. Where the arc actually stands

The arc opened as *"we cannot write the 1.5 MB animation library, so we need a
compression-8 encoder."* **Both halves of that turned out to be wrong**, and the corrections
are the arc's main output so far.

| claim it opened with | what is true |
|---|---|
| the blocked file needs 1.5 MB of contiguous space | it **already owns a 1,029,632 B reservation** and ships compressed; the bar is *match ArenaNet in place*, not *beat them to fit a free run* |
| authorship needs that file | **bone lengths come from the SHELL** (29,802 B, writable). The unwritable files hold *motion*, not *form* |
| an encoder is the critical path | it is **not** on the critical path for shape authoring |

**What is PROVEN at the retail client, all owner-driven, pinned build 38797 loopback:**

- A shell we authored **renders** — U7, and reproduced larger as run 6 (2026-08-18).
- The client **accepts a 16th FA8 link and a 243-record sequence table** — run 1, eight of
  eight capture checkpoints, no `MdlLoad`/`MdlSeq`/`MdlAnim` assert.
- Our authored sequence records **are selected** by the client's own variant picker —
  run 2, "half the animations", the 50/50 at `0x00804240`.
- **Linked-file bases are never used**; the shell's copy is authoritative — run 5 (12 links
  scaled, 32% coverage, nothing) against run 6 (shell scaled, everything). §9.3k.

**What is NOT shown:** a linked file's *content* changing what appears on screen. The only
property we tested in a linked file is the one linked files do not own.

---

## 2. State of the machine

**The deployed archive is run 6** — `vault/run/2026-07-29_221c13772c7a/Gw.dat`, carrying the
shell with bases ×3. The hatcher will look exploded. Retail is preserved beside it.

```bash
python C:\gd\Rurik\vault\research\archivewrite\a4stage6.py --retail
```

Six staged archives exist under `vault/exports/archivewrite/` (a4, a4run2…a4run6), each
4.2 GB and each rebuildable from its script. **Delete them when disk matters** — they are
outputs, not inputs.

Nothing is running: no client, no server, no background task.

---

## 3. Tooling this arc added (all merged, all tested)

| module | what it does | tests |
|---|---|---|
| `toolkit/mapdata/unitauthor.py` | add an FA8 link; insert a sequence record **in key order** | `test_unitauthor.py`, 30 |
| `datcheck --generations` | surviving MFT generations — what a repair could adopt | `test_datcheck.py` §8 |
| `datcheck --crc-sweep` | every payload CRC; catches what all ten open-time rules miss | §9 |
| `datcheck --diff` growth | the file's own length, which no MFT row records | §10 |
| `archive.py` `mftOffset` u64 | was `<I`; silently **capped archive growth** | §11 |
| `datwrite` header refusal | `[0x00,0x10)` — the one corruption with no recovery | `test_datwrite.py` |
| `datplan` extent projection | a generation's declared extent crosses run boundaries | `test_datplan.py` §9 |

Floors: datcheck 84→112, datwrite 78→87, datplan 38→44. Run scripts live in
`vault/research/archivewrite/` (`a4stage.py` … `a4stage6.py`), each with its prediction
stated in its own docstring.

---

## 4. The safety rules this arc established — read before writing any archive

Full detail in §5. The short form:

1. **Never launch the client on a suspect archive. Diff it first.** The launch is the
   irreversible step, not the write.
2. **"Repair" means DISCARD.** The client adopts an older MFT generation, then deletes the
   whole `nextStream` chain of any row whose payload CRC mismatches. It Flushes, so it is
   permanent after one launch.
3. **The silent killer is the 12-byte header CRC.** A bad one returns 0 with **no log line**
   into `ArchiveCreate`, which writes a fresh empty archive over 4.2 GB. `datwrite` now
   refuses that region outright.
4. Six MFT generations survive in the study archive — measured, not assumed. **Never
   allocate into the shadow rotation region.**

---

## 5. What to do next, cheapest first

**A. Show a linked file's CONTENT changing the screen.** The one thing five client runs
never demonstrated. Bases are the wrong lever — scale the **channel values** (rotations,
translations) of a writable link instead, or zero them, and watch an animation that link
actually serves. Note the trap that cost this session: **the hatcher only ever plays its
casting animation** in the harness's `--enemy` setup, so pick a link that serves *that*, or
provoke other animations. 13 of 15 links are writable; the two that are not (15018, 87333)
hold 149 of 242 records.

**B. Decide the encoder on its real merits.** It is off the critical path for shape, but it
is what reaches *motion* in the 62% of records held by unwritable files. A2 measured the
stdlib beating ArenaNet's own ratio on that payload by **11,930 B**, so the difficulty is
format conformance, not compression. Rung **A6** — the entropy accountant, ~80 lines, no
bitstream — is the cheapest thing that can kill it.

**C. A1b, downgraded but real.** `schema/messages.json` has **zero** occurrences of `anim`,
`sequence`, `seq`, `emote`, `gesture` — *"the server tells the client to play sequence N"*
was never a measured wire fact. Find who fills the per-agent key array at `+0x2C`/`+0x34`.

**D. A5, still unrun and still the biggest lever on the wall.** Does the client read a
1,514,855 B **stored** row placed past the old EOF? That population is currently empty —
retail's largest ordinary stored content row is 19,292 B. One caged run on a copy, with a
byte-identical payload so the answer cannot be confounded.

---

## 6. How to run a visual rung, given what this session cost

Five of seven runs produced no usable verdict. The causes, so they are not repeated:

- **Run the positive control FIRST.** Runs 1–5 all rested on the assumption that the oracle
  worked, and it took until run 6 to check. One cheap control would have saved three runs.
- **Change SHAPE, not timing or motion.** "It feels different, I'm not sure" is a failed
  experiment. ×3 on bone lengths got a one-word answer; a retime got hedging.
- **Cover the animation the creature actually performs**, not a fraction of its set. Confirm
  which one that is before designing around it.
- **Spawn what must be looked at ~150u to the player's LEFT or RIGHT** — in front, the
  player model occludes it (owner's instruction, 2026-08-18).
- **Check `--shots` actually landed.** It skips silently with `client not foreground`, and
  run 1 lost every screenshot that way.
- **Ask for a video.** Reading frames settled in one minute what four runs of prose had not.

The harness command that works:

```bash
python toolkit/harness/session.py --enemy --warn 0 --walk "zoom:-12 pitch:300 wait:4" --shots 10 --hold 240
```
