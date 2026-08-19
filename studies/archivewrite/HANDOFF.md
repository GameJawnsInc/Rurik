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
property we tested in a linked file is the one linked files do not own. **That is run 7, and
it is STAGED as of 2026-08-19** — §5-A for how to run it, §11.6 for what it says.

**Row 3 of that table is now itself out of date, in the good direction.** "An encoder is not
on the critical path for shape authoring" was true and remains true; what A7a/A7b/A8 added is
that the encoder **exists, and the retail client reads its output** — which turns the
unwritable files writable and takes run 7 from 12 of 15 links to 14 of 15.

**What is PROVEN read-only, 2026-08-18 (A6, §10):** our Huffman + meta layer re-costs
retail's own token stream to **+8 B on 1,029,564**; retail's stored row can be **re-emitted
byte-identically** (428 rows, CRC-matched); **ArenaNet's table encoder is longest-run
greedy**, bit-exact on 2,194/2,194 tables; and a literal-only encoder is **dead** by
391,648 B. **Not shown:** anything about the LZ77 matcher, which is where the whole
remaining risk sits — see §10.2's block-overhead arithmetic before pricing A7. **That
sentence is superseded: A7a, A7b and A8 have all run.** The matcher ties retail's within 12
tokens in a million, the encoder emits real bits, and **the retail client read a row we
compressed** — §5-B.

---

## 2. State of the machine

**DEPLOYED: RETAIL.** End of 2026-08-18, **verified rather than assumed** — row 11196 of
`vault/run/2026-07-29_221c13772c7a/Gw.dat` is back to 1,029,564 B / crc `0xf862d5c4`, five
key rows are byte-identical to `Gw.dat.retail`, preflight 10/10, 177,319 payload CRCs 0 bad,
4,198,489,600 B. **Nothing is running**: no client, no server, no background task (`tasklist`
shows no `Gw.exe`).

That line has been wrong before and it is cheap to re-check, so **re-check it**: this file
claimed "the deployed archive is run 6" for hours after another session had restored the
baseline at 21:34 that evening, which is exactly the staleness the top of `CLAUDE.md` is
about. **The run directory is shared.** Attribute before you touch, and never kill a process
you have not attributed.

**A8 ran against this machine earlier the same evening and PASSED** — §16, launched 22:16,
loopback, build 38797. `RUN VERDICT: PASS`, 8 of 8 checkpoints, **no assert anywhere**; the
Hatcher walked, attacked and cast for the full 150 s hold while row 11196 sat in the archive
**compressed by us**, and the row came through the launch intact. Retail was restored
afterwards, which is why the state above reads as it does.

Swapping either way, with the client closed:

```bash
python C:\gd\Rurik\vault\research\archivewrite\a4stage8.py --deploy
```

and `--retail` puts the baseline back. (`a4stage6.py --retail` restores the same file; either
script works, and both re-run the full gate sweep on the way in and out.)

**Seven** staged archives exist under `vault/exports/archivewrite/` (a4, a4run2…a4run6,
**a4run8** — the A8 one, still built and ready to redeploy), each 4.2 GB and each rebuildable
from its script. **Delete them when disk matters** — they are outputs, not inputs. 270 GB was
free on 2026-08-18.

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
| `toolkit/mapdata/gwentropy.py` | **A6** — recovers retail's own token stream and re-costs it; no bitstream writer | `test_gwentropy.py`, 91 |
| `toolkit/mapdata/gwmatch.py` | **A7a** — size-only LZ77 + an exact block-partition DP, costed through `gwentropy`; still no bitstream | `test_gwmatch.py`, 62 |
| `toolkit/mapdata/gwenc.py` | **A7b** — the bitstream writer. Re-emits retail byte-identically; encodes our own | `test_gwenc.py`, 55 |
| `datwrite.replace(..., compression=, expect=)` | writes compression 8 **and decompresses to verify before committing**; `declaration_fault` is shared with `datmove` | `test_datwrite.py`, 87→138 |
| `datmove.move(..., compression=, expect=)` | the safe relocation verb for compressed rows that **C-6 said did not exist** | `test_datmove.py`, 46 |
| `datalloc` comp-8 gate | decodes instead of matching a two-byte marker — the row **creation** path | `test_datalloc.py`, 98→100 |

Floors: datcheck 84→112, datwrite 78→87, datplan 38→44. Run scripts live in
`vault/research/archivewrite/` (`a4stage.py` … `a4stage6.py`, **`a4stage8.py`**), each with
its prediction stated in its own docstring. They are gitignored by design, so they do not
travel with a clone. **`a4stage8.py` takes `--toolkit` and PRINTS the tree and HEAD it
loaded**; `a4stage6.py` hardcodes a foreign worktree 42 commits behind, which is the reason
that argument exists.

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

**A. Show a linked file's CONTENT changing the screen — STAGED 2026-08-19, §11.6.
`vault/research/archivewrite/a4stage7.py`. Not deployed, not launched: it needs the
owner at the keyboard, because its readout is a model-appearance verdict.**

Run it with `--plan-only` first (costs every edit against retail and stops without
copying anything), then bare to build the staged archive, then `--deploy` with the
client closed. `--retail` puts the baseline back.

**What it does.** Composes a 180° rotation onto every rotation key of fourteen of the
hatcher's fifteen linked animation files — 232,764 keys — and scales the shell's head
cluster (nodes 51–64) ×3 as the positive control in the same archive. Nothing else:
no sequence record, no key table, no playback window, no link list, no new file.

**A8 rewrote this design and §11.5 is superseded.** 11.5 assumed writes go in
uncompressed, which is what runs 4–6 did through `datmove`; under that assumption
15018 and 87333 are unreachable and coverage is 12 of 15 links with several
relocations. Costed through `gwenc`, **fourteen of fifteen links fit their OWN
existing reservation compressed — including both files 11.5 called unreachable**
(15018 at +16,544 B of slack, 87333 at +15,020). So the run **relocates nothing,
grows nothing, consumes no free run, and changes exactly 15 rows in place**. Coverage
is **234 of 242 sequence records (96.7%)**. The one exclusion is 222949, 12 B over at
every quality dial.

**The geometry this arc has been using is wrong — correction C-10, and read it before
quoting any distance from §11.4.** `blk2C` bases are **absolute model-space rest
positions**, not the bone lengths §9.3g called them. ArenaNet's own mesh is the
referee: file 116703's bbox is 72.6 u, the absolute reading seats all 86 joints inside
the skin (median 1.40 u from a real vertex) and the accumulated reading puts them
532 u away. Every distance in §11.4 is ~11× too large, and the corrected numbers are
**better**: head ×3 moves the cluster **1.98× the whole creature's extent**, the flip
moves the average joint **1.55×**, and with the flip already firing the head scale
still moves head nodes 2.09× and non-head nodes **exactly 0.0**. The two instruments
are additive and disjoint, which is what retired a skeptic's charge that the flip
destroys the control.

**Three things to know before the launch, each of which would have cost the run.**

1. **`--practice-target` is FORBIDDEN.** It sets `ENEMY_ATTACKS_BACK` False and the
   chase loop `continue`s before a single `MOVE_TO_POINT` goes out, so the creature
   never walks. Use:
   `python toolkit/harness/session.py --enemy --hold 420 --shots 5 --walk "zoom:-12 pitch:300 alt:3 shot:1 wait:4"`
2. **Never score a negative from a still.** Two of the creature's records carry
   selector 0 — served by the shell, not by any link — and one is a 2.000 s whole-body
   cycle over 46 of 86 nodes, the shape of a standing idle. Giant head + normal limbs
   on a stationary hatcher is consistent with the run working perfectly. The negative
   needs **≥3 logged `walks to` cycles**, and the server prints that line every time
   the >120 u re-chase fires.
3. **`flip(flip(q))` is bit-exactly `−q`, the same rotation.** Re-running the stage
   against an already-deployed archive would restore retail limbs while taking the
   head to ×9 — landing on the NEGATIVE cell, produced by a bug. The script reads only
   from `Gw.dat.retail` and fingerprints all sixteen rows against retail's own stored
   sizes first.

**The decision table is replaced, because §11.5's sent a positive result to ABORT** —
see §11.6e for all six cells. The change that matters: **head NORMAL + limbs
contorted is ANSWERED with an invalid control, not an abort.** And the control's
premise is now measured rather than trusted — 308 of ArenaNet's own 1,463 mesh
vertices (21.1%) sit nearest a node in 51–64, all fourteen own geometry, two whole
submodels are head-dominated.

**Do NOT decimate keyframes for this run** even though it works — §11.3. It fits in
place, it needs no free run, and it would unblock 73940; but its rotation error is
**p99 46.6°, max 169.3°**, the same order as the flip that is supposed to *be* the
readout. And do not take the arms-only dose a lens proposed: it was aimed at
protecting the control, and the corrected geometry shows the control needs no
protecting.

**B. ~~Decide the encoder on its real merits.~~ A6 RAN, 2026-08-18 — see §10. It did NOT
kill the encoder, and the risk is now entirely the LZ77 matcher.** Re-costing retail's own
token stream for row 11196 gives **+8 B on 1,029,564**. But read §10.2 before quoting that:
the token term is 95.6% of the stream and Huffman optimality is a theorem, so it *had* to
tie — A6 excluded a defect in our own cost model, not a risk in the encoder. **The figure
that decides A7 is the block overhead:** table transmission is 1,686 B = **25× the row's
68 B of slack**, one extra block ≈ **1.5× the whole authoring budget**, and a matcher only
**+2.7%** worse in token count overflows the reservation on table cost alone.
**What the skeptics left behind is worth more than the verdict:** retail's stored row was
**re-emitted byte-identically** (428 rows, zero failures, CRC matching the MFT), and
**ArenaNet's table encoder is identified as longest-run greedy** (bit-exact on 2,194/2,194
tables). Every piece of a compression-8 encoder now exists **except the matcher**. Also
settled: a literal-only encoder is **DEAD** — 1,421,280 B, 391,648 B over the reservation.
**A7a RAN — 2026-08-18, §12. A7_VIABLE, and the surprise is where the win comes from.**
`toolkit/mapdata/gwmatch.py`, size-only, 62 checks. Row 11196 comes out at **1,011,244 B
against a 1,029,632 B bar — 18,388 B of slack, and 6,394 B better than the best of 18
raw-deflate configurations.** Our token stream is **12 tokens** from retail's in a million:
the matcher is a dead heat. The win is bought by the **block partition** — 109 blocks
against retail's 16, spending 74,777 more table bits to save 221,778 token bits. **Note the
skeptic's correction:** at the best dial setting we fit even on retail's own partition
(60 B), so the partition buys the *size* of the win and robustness across the dial, not
fail→pass. Population evidence reverses §1.2's risk: **25 of 25 random 200 KB–1.5 MB rows
beat retail and fit, where deflate fits only 14 of 25**, and the three rows §1.2 named as
zlib's worst overflows all fit. Honest counterweight: on hard rows the margin is
0.003–0.01%, so 11196's 1.8% is a favourable draw. **The budget in payload terms: 18,388 B
of slack ≈ 34,273 B of extra payload — 2.26% growth, against retail's own 127 B.**

**A7b RAN — 2026-08-18, §13. GREEN. THE ENCODER EXISTS.** `toolkit/mapdata/gwenc.py`,
55 checks. Two results: **retail's own stored rows re-emit BYTE-IDENTICALLY** (row 11196 at
1,029,564 B with `crc32` matching the MFT's own 0xF862D5C4; **3,051 distinct rows across five
archives plus a skeptic's independent ~5,990 more across seven, zero failures, no failure
class**), and **our own encoder emits real bits that unmodified `gwdat.decompress` turns back
into the payload** — row 11196 at **1,011,244 B, equal to A7a's model to the byte, 18,388 B
under the reservation.** §12.6's remaining risk is retired: 328 encoder-implied tables were
serialized and rebuilt by `build_table` with 0 refusals and 0 mismatches.

**Two things that make `gwdat` much more trustworthy than §2.2 recorded.** The bit order is
corroborated from **ArenaNet's own source lines** — `P:\Code\Base\Compress\CmpIo.h`, and the
client has a bit *writer* whose preconditions are exactly ours (`CmpIo:138`, `CmpIo:139`).
And decoding ArenaNet's **own** row 8295 with an *upstream-faithful* `build_table` **FAILS**:
`gwdat`'s zero-length repair, long labelled a divergence from both upstreams, is **required
by ArenaNet's own archive**, so the shipping client must implement something equivalent.

**The one gap to carry into A8, with its fix already named.** Our encoder emits declared
`symbol_count == 1` on 3.4% of tables; retail does so **0 times in 138,708 first blocks**, so
byte-identical re-emission structurally cannot cover it and its correctness rests only on our
own decoder. **If the client refuses it, the fix is a two-symbol distance table inside
retail's attested envelope, costing a few bits — a size question, not a design one.**

**THE WRITE PATH IS BUILT TOO — 2026-08-18, §14.** `datwrite.replace(..., compression=8,
expect=payload)` writes a compressed row and **decompresses to verify before committing**,
which is the only refutation available because `datcheck` has no notion of a compression code
and the entry CRC is over the *stored* bytes. `datmove` gained the safe relocation verb for
compressed rows that **C-6 said did not exist**, and C-6 was reproduced live on a synthetic
archive first. Every existing caller — all six `a4stage*.py`, `deploy.py`'s subprocess,
`iconset`, `rebloat`, `textwrite` — is untouched by default.

**Read §14.2 before trusting any of it.** Skeptics found **four** ways to reach C-6's failure
class through code written to prevent it, including one reachable from the documented CLI in a
single command and one that made `Archive.read()` return **zero bytes** on a green archive.
All four are fixed. §14.3 is the pattern worth carrying forward: **this is the fourth
consecutive rung where a check claimed more than the artifact delivered, and sabotage — break
one arm, count which checks go red — is the only technique that has reliably caught it.**

**So the summit is now one rung away.** A8 needs: a staging script (`a4stage7.py`-shaped) that
`gwenc`-compresses an authored payload into row 11196 on a **copy**, the §5.6 gates
(`--preflight`, `--generations`, `--crc-sweep`, `--diff` against a pre-write snapshot, and the
3.91 GiB backup), and the owner at the keyboard. **Never launch on a suspect archive.**

**C. A1b, downgraded but real.** `schema/messages.json` has **zero** occurrences of `anim`,
`sequence`, `seq`, `emote`, `gesture` — *"the server tells the client to play sequence N"*
was never a measured wire fact. Find who fills the per-agent key array at `+0x2C`/`+0x34`.

**D. A5 — still unrun, and CHEAPER than this file said. Its premise expired (correction
C-9).** "That population is currently empty" was true of *retail* and is no longer true of
*us*: `datmove` writes compression 0 unconditionally, so **run 5 shipped eleven stored rows
above 19,292 B — the largest 765,378 B — and the owner deployed and launched it with no
assert.** So the honest bar is 11× the largest **proven-read** stored row and **0.5× the
largest already deployed without a crash**, not "unprecedented". Retail's own 19,292 B
ceiling still reproduces (0 of 38,621 rows above it), so the question is real — it is just
much better supported than the ladder priced it. One caged run on a copy, byte-identical
payload so the answer cannot be confounded.

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
