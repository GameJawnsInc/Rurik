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

**What is PROVEN read-only, 2026-08-18 (A6, §10):** our Huffman + meta layer re-costs
retail's own token stream to **+8 B on 1,029,564**; retail's stored row can be **re-emitted
byte-identically** (428 rows, CRC-matched); **ArenaNet's table encoder is longest-run
greedy**, bit-exact on 2,194/2,194 tables; and a literal-only encoder is **dead** by
391,648 B. **Not shown:** anything about the LZ77 matcher, which is where the whole
remaining risk sits — see §10.2's block-overhead arithmetic before pricing A7.

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
| `toolkit/mapdata/gwentropy.py` | **A6** — recovers retail's own token stream and re-costs it; no bitstream writer | `test_gwentropy.py`, 91 |
| `toolkit/mapdata/gwmatch.py` | **A7a** — size-only LZ77 + an exact block-partition DP, costed through `gwentropy`; still no bitstream | `test_gwmatch.py`, 62 |
| `toolkit/mapdata/gwenc.py` | **A7b** — the bitstream writer. Re-emits retail byte-identically; encodes our own | `test_gwenc.py`, 55 |

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

**A. Show a linked file's CONTENT changing the screen — DESIGNED AND DE-RISKED 2026-08-18,
§11. It is ready to stage; it has not been staged or launched.** The trap named here (the
hatcher only plays its cast in the `--enemy` setup) is **solved, and not by finding the cast
file**: the creature's most universal animation is **base key 3,259,067,510, 1.067 s, present
in 26–32 of 32 corpus shells, and all six of its weapon-class variants are served by
selector 10 = file 109464 — 27,948 B stored, WRITABLE, already relocated in run 5.** That is
locomotion, and the harness re-triggers it on demand: the enemy re-chases whenever the player
moves >120 u (`ENEMY_DEST_RESEND`). **Provoke the WALK, not the cast.**

Ship the stripped version: compose a **180° quaternion flip onto every rotation key** of the
writable links (length-preserving, so nothing relocates and no record, key table or window
changes — §9.3g's rules 1/3/4/7 are untouched rather than satisfied), plus the **positive
control in the same archive** — the shell's head cluster, **nodes 51–64, bases ×3**, audited
as genuinely the head (subtree of node 50: mirrored horns, a jaw chain) and visible in the
first still before anything animates. Decision table: giant head + mangled limbs = answered;
giant head + normal limbs = the first real negative; **normal head = pipeline broken, abort,
and nothing else in the run means anything.**

**Do NOT decimate keyframes for this run** even though it works — §11.3. It fits in place,
it needs no free run, and it would unblock 73940 to reach 15-of-15 links; but its rotation
error is **p99 46.6°, max 169.3°**, the same order as the flip that is supposed to *be* the
readout. Stripping costs coverage of 73940 only (12 of 15 links), which does not matter
because the walk is 109464.

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
