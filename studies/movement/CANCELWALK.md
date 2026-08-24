# CANCELWALK — the single press that cancels the cast but does not move

**Opened 2026-08-24**, on the handover at the end of
[../castmech/FINDINGS.md](../castmech/FINDINGS.md) §3g: pressing a movement key
mid-cast cancels the cast (landed, verified at a client) but does **not** move
the player on our server; a second press is needed. Stock Guild Wars moves on
the single press (owner-verified against retail 2026-08-23). §3g registered
this as a movement-policy question because the obvious fix — grant a lead —
is REALFIX's refuted family.

**Evidence reader: `toolkit/authsrv/cancelwalk.py`** — read-only over the
vault; every number in §3 reproduces by running it. Captures: **live**
`20260824T074002` (origin `live`, build 38849, the castmech cancel-family run,
sealed plan) and **ours** `captures/gamesrv/authsrv-20260824T081335-c1.jsonl`
(origin `ours`, build 38797, the §3g acceptance run on the Isle of the
Nameless).

**Identifiers.** `CANCELWALK-F<n>` = findings, labelled per
[../character/FINDINGS.md](../character/FINDINGS.md). `CANCELWALK-H<n>` =
rival hypotheses for the freeze. `CANCELWALK-R<n>` = pre-registered runs;
their predictions are stated here before any run happens. Convention:
[../idents/CONVENTION.md](../idents/CONVENTION.md).

## 1. Method, and why order claims here are readings rather than inferences

`cmsgstream.timed()` decodes both directions of the live game channel onto one
clock. Messages in one TCP segment share a timestamp, Python's sort is stable,
and per-connection input order is stream-offset order — so equal-time rows
print in **byte order**. Every burst below is one segment. The framing is
exact (the castmech run's connections frame to the last byte, §3f).

## 2. What the handover believed, in three sentences

Mid-cast the client is held and its key-down edge is spent on the cancel;
retail moves the player anyway because its `0x0029` carries a real destination
(+768 u along the heading), a server-authoritative move order; ours grants the
player's own reported position, so there is nothing to walk to. §3g's one
proposed no-warp experiment was message ORDER (grant before vs after the
release burst). §2 of this document exists to be measured against; §3 is what
the measurements actually say, and they overturn most of it.

## 3. Findings

**CANCELWALK-F1 — OBSERVED. Retail's movement answer rides AFTER the release
burst, and our order already matches.** All three movement-triggered cancels
(t=81.660 W, 98.779 click, 128.805 W) and the mid-windup stop (114.641) put
`[8→0, 59(/3), E2]` first and the movement tail (`0x0025`/`0x002B`/`0x0029`)
last, `0x0029` always final. Our §3g answer is the same shape in the same
order (seq 224–228: 8→0, 59, E2, 0025, 0029). This **corrects castmech §3f's
"retail puts the grant first in both" (it had it backwards) and closes §3g's
order experiment at a desk: there is no order delta to test.** The click-arm
note in §3f ("we place the grant before the burst on the click arm") remains a
real fidelity mismatch on that arm, cosmetic until shown otherwise.

**CANCELWALK-F2 — OBSERVED. The mid-action `0x003D` reports a LATCHED heading,
and retail's cancel-instant grant is that stale vector applied blind.** vec2 is
bit-identical `(13.093545913696289, 767.5670776367188)` at t=64.757 (the last
report of the pre-cast walk), 81.625, 114.609 and 128.774 — three presses
across 47 s carrying one stale value — and the backpedal press at 108.336
carries its exact negation with mt=4. The granted destination is
`reported + vec2 + 0.5·û` **exactly, 3 of 3** (2315.182, 2779.766, 2780.207
in y) — REALFIX's D1 formula, confirmed at cancel instants. So retail's
"lead" points wherever the client last walked, not where the player is going:
ordinary heading-arm bookkeeping, not an authored move order.

**CANCELWALK-F3 — OBSERVED. The retail client does NOT walk toward the
granted point; it self-walks its own live direction the moment the burst
clears the hold.** At t=128.805 the grant points `(+0.017, +1.000)` and the
client walks 23.8 u in `(-0.787, +0.617)`; at t=114.641 same grant direction
and the client walks 28.8 u due west (cos ≈ 0). At t=81.660 the walk tracks
the grant ray exactly (cos = +1.000) — but that is the unmoved-camera case:
the player had just walked north and never turned, so own-direction ≡ the
latched vec2 ≡ the grant direction, all one quantum. Walk distances match the
key-held window at run speed (95.9 u ≈ 0.33 s × 288; 23.8 u ≈ 0.10 s × 288),
and each release produces `0x0047`, answered by a stop re-pin. **This refutes
§2's mechanism sentence: the destination does not steer the body. The
`0x0029` moves the sync copy and nothing else — REALFIX-O1's model, holding
even at the cancel instant.**

**CANCELWALK-F4 — OBSERVED. `0x002B` is movement-family bookkeeping, not a
cancel message, and it is not the enabler.** It appears exactly on family
transitions: `[1.0, 1]` when a stop-family gives way to movement (98.779,
128.805), `[1.0, 9]` answering `0x0047` stops (64.356, 82.037, 109.376,
114.782, 128.955), `[0.66, 4]` at the backpedal press (108.376) — **a live
wire witness for REALFIX-P1's CONTESTED `FAMILY_RATE` row 4:0.66**. The W
cancel at 81.660 carries **no** `0x002B` and the client walks; our client has
never received one and self-walks normally. Refused as the missing message.

**CANCELWALK-F5 — OBSERVED. Retail's stop answer has a second form.** At
65.095 a `0x0047` stop is answered by bare s2c `0x0028 [agent]` — no
`0x002B`, no re-pin — where every other observed stop gets
`0x002B [1.0, 9]` + zero-distance `0x0029`. What selects between them is
unread. Caveat to REALFIX-P1's stop-arm note ("NEVER `0x0028`"), which is
right about the c2s side and now needs this s2c footnote.

**CANCELWALK-F6 — OBSERVED. The freeze survives ~25 client frames, killing
every timing hypothesis.** Ours, t=5.417: the mid-cast W arrives as `0x003D`
(mt=1), our answer goes out in the same instant in retail's order, and the
client holds the movement episode open to t=6.234 (`0x0047`, **same
coordinate, 0.0 u**) — 0.818 s with the key down, the hold released (§3g:
the animation stops on screen), and zero motion. A same-frame race cannot
explain 25 frames of stillness. The second press (t=7.502, mt=4) gets the
same-shaped zero-lead answer and walks immediately — so nothing about our
answer freezes an ordinary press; only the cancel instant is broken.

## 4. Elimination

Four observations bound the answer: retail cancel 1 walks, retail cancel 4
walks, our cancel press freezes, our ordinary press walks.

| candidate delta | vs retail c1 (walks) | vs retail c4 (walks) | verdict |
|---|---|---|---|
| message order | identical (F1) | identical (F1) | **eliminated** |
| `0x0025` presence | retail c1 has none, we send one | retail c4 sends one too | eliminated — present and absent both walk |
| `0x002B` missing | c1 walks without it | c4 has it | eliminated (F4) |
| answer timing | +35 ms vs same-instant | same | **eliminated** (F6: 25 frames) |
| `0x0029` destination | **they lead, we zero** | **they lead, we zero** | **the only delta present against BOTH** |
| build 38849 vs 38797 | — | — | residual; unfalsifiable on loopback |
| cast-start state | start bursts match structurally (E4/A2 62/A0 60/9F 8→1; retail adds A2 44 on the *target*) | same | residual |

The destination delta survives — but F3 forbids the handover's reading of it
(the client does not walk *to* the grant). What is left is a narrower claim:

**CANCELWALK-H1 (primary) — RECONSTRUCTION.** While the client has a mid-hold
movement request outstanding (its `0x003D` sent during an action hold), a
`0x0029` granting a point at its own reported position reads as *refusal —
stay put*, and a grant strictly ahead reads as *permission* — after which the
client self-walks its own direction (F3). Ordinary presses are not gated
because no request is outstanding (F6's second press).

**CANCELWALK-H2** — the compound (a `0x0025` present with no `0x002B`)
freezes it; needs two coincidences retail never exhibits together; disfavored.

**CANCELWALK-H3** — the client's movement lock is set wrong at CAST START,
and no cancel-instant answer can clear it; the visible candidates (A2 44
rides the target; property 62's value encoding) touch nothing movement-shaped.

**CANCELWALK-H4** — build drift between 38849 and 38797 in the resume path.
Movement code this old drifting between adjacent builds is unlikely; noted
because nothing here can falsify it.

## 5. Pre-registered runs — predictions first, one change per run

All on loopback, operator-driven (world-anchored input; the §3g protocol),
Isle of the Nameless, ≥3 cancelled casts per run. **Readout is the wire, not
the screen**: a run PASSES a cast if the client's own reports move ≥ 30 u
within 0.5 s of the cancel press with no second press; ≤ 5 u is a freeze.
Each run also includes one **direction-discriminator cast**: rotate the
camera ≳ 90° after the previous walk, then W mid-cast — the latched vec2 (and
so any granted lead) then points away from the camera's W, and the walk
vector names which one the client obeyed.

- **CANCELWALK-R1 · `--cancel-answer=suppress`** — the release burst alone at
  the cancel instant; no `0x0025`, no `0x0029` on that report. Zero warp
  exposure (we send less; the copy just keeps its park).
  *Predictions:* H1 → **freeze** (no permission at all; sharpest H1 test in
  the refusal direction). H2 → **walk** (the freezer is withheld). H3/H4 →
  freeze.
- **CANCELWALK-R2 · `--cancel-answer=retail-lead`** — retail-verbatim tail at
  the cancel instant only: `0x0025` (heading-change-gated as now), `0x002B
  [1.0, mt]` on family transition, `0x0029` at `reported + vec2 + 0.5·û`.
  **Diagnostic, never ship** — this is the refuted lead family, licensed for
  one instant on loopback because the readout completes before any cost
  lands. *Predictions:* H1 → **walk on the single press**, and the
  discriminator cast walks in the CLIENT's direction, not the grant's (F3
  reproduced on our build). H2 → walk (the `0x002B` completes the compound) —
  R1 separates. H3/H4 → freeze.
  *Pre-registered cost:* the copy bakes a ≤ 768.5 u leg along a stale vector.
  Under `--zero-lead` + no stop echo nothing re-pins it until the next
  accepted report's grant (rate floor 0.5 s), so a `+0x48` resync inside that
  window may snap visibly (p50 re-arm 2.89 s says usually it will not). A
  warp AFTER the walk readout does not bear on the walk verdict; it is the
  known price of leads and the reason R2 cannot ship.
- **CANCELWALK-R3 · `--cancel-answer=lead:16`** — run only if R2 walks and R1
  froze: same tail with the lead cut to 16 u. *Predictions:* H1-binary (any
  nonzero offset is permission) → walk; H1-with-threshold → freeze, and the
  threshold gets bisected. A 16 u lead at a provably-stationary instant is
  the only form with a shippable safety story: the copy's excursion (≤ 16 u
  past the player) is smaller than the ~86 u park-lag the shipped
  configuration already carries at every stop (measured in the §3g capture:
  the copy parks at the last granted point, 86.2 u behind where the player
  stopped), and the next report re-pins it.

**Decision table.** R1 walks → the fix is deletion (suppress the
cancel-instant grant); ship after a REALFIX-style composition audit. R1
freezes + R2 walks → H1 confirmed; bisect with R3 toward the smallest
permission that walks; any shipped form needs its own REALFIX audit (O5 is
not by-witness for a led point; the stop-arm re-pin question re-opens because
retail's own hygiene pairs cancel-leads with stop re-pins). R1 and R2 both
freeze → content at the cancel instant is insufficient; the arc moves to H3
(compare cast-start values field-by-field against retail's; then the client's
input latch via the clientscan/trnhook tooling) with H4 logged as the
residual. **No arm ships from this ladder directly; a run's PASS licenses a
candidate, and shipping stays a separate, audited step** — the lead family's
refutation stands for every steady-state grant regardless of outcome.

## 6. Against the handover's three questions

1. *Is a lead grant safe in this one instant?* Reframed: the lead does not
   steer the body (F3), so "safe" is the wrong first question — the live
   question is whether it is the **permission** the client waits for (H1).
   Safety-wise, a bounded lead at a stationary instant costs less than the
   copy's existing ~86 u stop-lag; 768 u along a stale vector remains
   diagnostic-only.
2. *Does order matter?* No — closed at a desk (F1). The §3f order claim was
   backwards; ours already matches retail.
3. *Is there a third message?* No. `0x002B` is family bookkeeping (F4),
   refuted as the enabler by retail's own cancel 1; the only other batch
   member is the heartbeat `0x001E`. Retail's cancel answers contain nothing
   else.
