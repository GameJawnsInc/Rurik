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

## 5a. R1–R3 RAN, same day — H1 confirmed sharper than predicted (2026-08-24)

Operator-driven, loopback, Isle pin, captures
`authsrv-20260824T095712` (R1), `100352` (R2), `100643` (R3);
`score_runs`-style readout of every cancel instant, press, answer and the
motion after.

- **R1 suppress: FROZEN, 2 of 2** — burst-only answers, 0.0 u at the release
  report both times. **CANCELWALK-H2 is REFUTED** (it predicted a walk).
- **R2 retail-lead: WALKS, 3 of 3 — to the granted point exactly.** Cancel 3
  lands at **+768.1 u, the granted coordinate to the decimal, and parks
  there** (four consecutive reports at the same point). The release arrives
  mid-glide (`0x0047` at +0.08 s, +19 u) and the body glides on regardless.
  The leg is straight and unclipped — the operator walked through stair
  collision. **H3/H4 in their strong form ("no cancel-instant answer can
  unfreeze") are REFUTED.**
- **R3 lead:16: WALKS 16.0 u exactly and parks, 2 of 3** — key still held,
  nothing until a fresh edge. (The third cast's 96 u run contains a second
  press: a mid-walk `0x003D` edge at +0.25 s.)

**CANCELWALK-F7 — OBSERVED, and it reframes H1.** At the cancel instant our
client (build 38797) executes the answering `0x0029` as a **click-order**:
it walks the granted leg to completion, straight-line, key state ignored,
and parks at the granted point. Zero-lead = "click where you stand" = the
freeze. This is the click arm's own mechanism expressing on the heading arm
at the one instant the client is not self-driving. Two corollaries: the mid-
cast vec2 on OUR build is **live**, not retail's latch (every walk went the
way the operator pressed — R2 cancel 2's vec2 points where the operator had
turned), and the pre-registered warp cost never materialised — the body
walks the leg WITH the copy, so nothing diverges to snap.

**The residual retail divergence stands, now cleanly bounded**: retail's
38849 client walked its own live direction *against* the grant (F3) and
stopped on release; our 38797 walks the grant and ignores release. Same
answer shape, different client behaviour — build drift (H4) or unread
client state (H3), and for OUR pinned build it no longer matters: the
contract is measured, and the server can be built against it.

### CANCELWALK-R4 · `--cancel-answer=<lead-form>,stop` — pre-registered before its run

What stock feel still lacks under a bare lead: release-to-stop. R2's own
capture supplies the trigger — the client **reports the release mid-glide**
— and retail's stop arm answers every such report with `0x002B [1.0, 9]` +
a zero-distance `0x0029` re-pin (F4/F5). R4 sends exactly that pair,
**scoped to the in-flight cancel leg**: a window armed at the lead send
(leg ÷ 288 u/s + 1 s slack), consumed by the first `0x0047` inside it,
cleared by any subsequent grant. The general stop arm stays silent —
`--stop-echo`'s refutation (teleport 9.9 s later, walk back) was measured
in ordinary self-driven play, which the window never covers, and the re-pin
is a zero-distance order at the client's **own** reported point, which
cannot move anybody even if this reading is wrong.

*Predictions:* release mid-leg **stops the body at the reported point**; a
press held past the leg still parks at the lead, its window expiring
unconsumed; the leg still cannot be steered mid-flight and still crosses
geometry (unclipped — a ship-time clip is a named open term, priced by the
stairs observation). If the body
does **not** stop, a zero-distance order does not supersede an executing
leg, and the stop side moves to a client read. *Registered lead for the
run: 288 u ≈ one second of walking — long enough that a normal press-and-
release never parks, short enough that a hold parks in ~1 s.*

### 5b. R4 RAN — every prediction confirmed, operator and wire agreeing (2026-08-24)

`--cancel-answer=lead:288,stop`, capture `authsrv-20260824T103556-c1`, three
cancelled casts. **Tap:** the release reports +97.6 u mid-glide, the
`CANCELWALK STOP` re-pin answers it (t=9.555), and the next report three
seconds later is at the **same point** — release-to-stop works, and R2's
identical release (answered with nothing, glide to 768) is the control.
**Held:** both casts park at **+288.0 u exactly, the granted point to the
decimal**, stop windows expiring unconsumed (0x0047 at +3.76 s and +2.05 s,
both past the 2.0 s window, neither needing an answer). Operator report:
"worked as you described." **CANCELWALK-R4 PASSES.** The licensed ship
candidate is: cancel-instant lead + scoped stop re-pin. Ship-time terms,
unchanged: clip the leg (the stairs phasing is real — and the clip must
measure from the REPORTED point, not our model's), choose the lead
(288 = park after ~1 s of held walking; retail's 766 triples the runaway),
promote the flag out of the experiment namespace, and the audited-exception
review against REALFIX's zero-lead invariants. **Defaults are an owner
ruling in this repo; none is made here.**

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

## 7. The state-diff round — the wire closes, and the gate asymmetry is read (2026-08-24)

R2–R4 solved the freeze on our pinned build; what they left is §5a's residual —
at the cancel instant our 38797 client executes the grant as a click-order while
retail's 38849 self-walks its live direction — and the premise, forced by R1/F1/F6,
that the differentiator is PRIOR STATE, not the cancel-instant answer. This round
diffed that prior state from both ends at a desk: the wire (retail `20260824T074002`
vs ours `captures/gamesrv/authsrv-20260824T081335-c1` and R1's `…095712-c1`) and
the pinned 38797 binary (`vault/client/2026-07-29_221c13772c7a/Gw.exe`, read-only).
Method notes that carry: the retail capture holds TWO game connections and the
outpost's own "agent 25" is an unrelated creature — every row below is the
explorable connection's, split first; ours decoded 617/617 and 5364/5364 with zero
residual bytes. Every load-bearing claim was adversarially re-derived by an
independent agent (the wire diff by raw-histogram recount; the two binary reads
instruction-by-instruction), and the client-side reads were in fact performed
TWICE by independent readers — every structural claim below reproduced in both.

### 7.1 Findings

**CANCELWALK-F8 — OBSERVED (skill identity UPSTREAM/CORROBORATED). The `0x0027`
"best lead" is dead: the pre-first-cast cluster is the scheduled expiry of a
Windborne Speed enchantment, not cast preparation.** The apply burst sits at
t=53.605: `0x0042` BUFF_ADD `[25, skill 160, rank 15, buffId 54, f32 13.0]`, two
prop-6 visual-effect adds (ids 13, 11), `0x00F1 [25, 128]`, `0x0027 [25, 383.04]`
(= 288 × 1.33). t=66.587 is its exact mirror — `0x0044 [25, 54]`, prop-7 removes
of the same ids, `0x00F1 [25, 0]`, `0x0027 [25, 288.0]` — at Δ = 12.982 s against
the decoded 13.0 s duration. Skill 160 = Windborne Speed (UPSTREAM, GWCA
`Skills.h`; the +33%/13 s arithmetic is OBSERVED). Corpus scale: 473 `0x0027`
across 20 live captures, **281 targeting non-player agents**, cycling ~13.0 s
wherever the buff is maintained, never cast-adjacent; in `074002` the session
holds three `0x0027`, all in the first 15 s of the connection, and nothing recurs
within ±5 s of any later cancel. The first cast landing 277 ms after the expiry
is an independent 13 s clock coinciding, not a trigger. The expiry precedes the
first cancel press by 15.0 s of silence.

**CANCELWALK-F9 — OBSERVED. The pre-press state diff, verified by independent
recount: value-parity on every wire-written field checked, AND three retail-only
movement-machine regimes we have never sent.** Parity first: `0x0020`
WORLD_CREATE_AGENT is byte-identical bar agent id and facing — same type dword,
**same 288.0 base speed** (our `agents.py` DEFAULT_RUN_SPEED seeds it; there is
no client-side 288.0 default — `0x43900000` appears nowhere in the image, positive
control 100.0f found 264×, and the constructor `0x005FDE30` seeds BOTH world
copies from the create message); `0x0199` INSTANCE_LOAD_INFO identical
`[409,1,280,1,0,0,0]`; both status words 0 at press; both buff lists empty at
press. Our two captures' pre-press inventories are structurally identical to each
other, so the hand-off is deterministic. The retail-only movement set (full-file
census on ours, positive-controlled):

- **`0x0028` AGENT_STOP_MOVING `[25]` ×1 at t=65.0948**, 36.8 ms after the
  player's own `0x0047` stop — the LAST movement-family s2c before the casts
  (F5's second stop form). Ours: zero, ever; our pre-cast stop was answered by
  nothing but heartbeat.
- **`0x002B [rate, family]` ×4** to the player, including `[1.0, 9]` at 64.3555
  answering a stop, **paired with a zero-distance `0x0029` re-pin at the stop's
  reported point** (0.0 u). Ours: zero, ever.
- **The led/re-grant regime**: 18 player grants pre-burst for 13 `0x003D` +
  3 `0x0047`, leads 169.6–1086.4 u, plus 4 strictly-unsolicited mid-leg re-grants
  (54.786, 57.524, 59.872, 64.273) keeping the sync copy continuously led. Ours:
  strictly one zero-lead grant per accepted report, plane 0, throughout.

Two textures recorded, not elevated: our `0x0025` sometimes rides reports that
get no `0x0029` (retail's six all co-time with grants) — cadence is plausibly
exposure, UNVERIFIED as mechanism; and an exposure confounder — retail cancels
its SECOND cast after a completed first, ours cancels the first-ever cast of the
session — closable in one loopback run (complete one cast before the cancelled
one). A prior inventory's "missing prop62" delta was a mis-decode and is
corrected: both sides send prop62 (retail −0.5 = 10/20 pool, ours −0.4 = 10/25);
the cast-start bursts match structurally.

**CANCELWALK-F10 — OBSERVED, twice-read and twice-verified. The `0x003D` emitter
funnel is unique, and the SEND gate and the WALK gates are different tests on the
same controller object — the exact shape of "sends the report, does not walk."**
The only 0x003D wire-buffer builder in the image is the 28-byte packer
`0x009206D0` (`{op 0x3D, pos.xy, plane, dir.xy, mt}`; the adjacent `0x00920720`
is the 16-byte `0x003E` builder — the family is a positive control). Its single
caller chain: key-edge layer (5 sites + one vtable slot) → MOVE-CMD `0x00535380`
(direction-changed flag, last-dir cache `0xC07C2C/30/34`) → MOVE-DISPATCH
`0x008163A0` → packer → channel send `0x007DCF00`. The report's POSITION operand
is sampled from the **ASYNC (drawn) body** (`[mgr+0x14C]` via `0x005FC400`) — the
binary root of "a held client reports a latched point." Inside MOVE-DISPATCH the
local self-walk is applied by `0x0081A8F0` on `context->playerControlledChar`
(assert-witnessed) BEFORE the send, and the send fires iff the direction-changed
flag is set — **independent of whether the walk started**. The walk applier
bails to `0x0081AD0F` (which stashes an +inf "no heading" sentinel into
controller `+0x694/+0x698`, arms nothing, and still returns into the send path)
on any of: **GATE A** `[ChCliBase+0x10C] & 0x100` (`0x0081A931`) — read at
exactly TWO sites image-wide, this applier and the `0x003E` applier `0x0081AEE4`,
against a 285-site census of `+0x10C` accesses: a dedicated suppress-self-walk
bit; **GATE B** `byte [ChCliBase+0x64] & 1` (`0x0081A93C`) — semantics
UNVERIFIED, and a DIFFERENT field from AgAgent+0x64 and from AgentView+0x64, do
not conflate; **GATE C** bit 4 of the same word — excluded at cancel instants
because the pre-send gate tests the same bit and the send fired. Deeper in the
survivor path sit the navmesh query (`0x709D30` == 0 exits early with no flag
set) and **GATE-A′, the dedup**: `0x0081AA5B` skips ASYNC-MOVE-START when the
new direction is within epsilon of the cached one AND the mode is unchanged.
**No writer of GATE A's bit or GATE B's bit was found** — no `or`/`bts` idiom
touches them; `+0x10C` is initialized wholesale from an agent-type template at
construction (`0x0081A609`) and reassigned wholesale (`0x00F1`'s handler stores
the word, F9: value 0 on both clients at press). The suppress state, whatever
sets it, is a **local client write no capture can carry**.

**CANCELWALK-F11 — OBSERVED (mechanism), CORROBORATED (in-tree prior). The async
body's drivability is a latch: ASYNC-MOVE-START `0x005FC6E0` arms
`clientControlled = 1` (AgTrack record +0x00, setter `0x00605F10`, input-only
call sites — the `0x0081AA88 → 0x005FC6E0` chain PROBE-GATEFIRE already named)
and writes the body's facing via `0x00602660`; the clearer `0x00605F70` runs on
the server-grant SNAP branch (`0x0060602E`).** An unarmed body is grant-driven —
which is F7's click-order shape. Two scope notes, both load-bearing: the latch is
armed only through the gated applier path, so "latch clear at the press" is the
downstream OBSERVABLE of any upstream bail, not a rival cause; and press-time
snap-clear cannot be the freeze mechanism — R1 sent ZERO bytes at its cancel
instants and froze anyway.

**CANCELWALK-F12 — OBSERVED. Property 59 is AgentView-only and closes as a
movement candidate.** Full depth, both readers agreeing: `0x007E01B0` →
`0x00802160` (resolver, type-1 check, silent no-op on miss) → `0x007F76A0`
(kind 0x17 skill_stopped) → `0x007F2E90`: one 0x48-byte event record spliced
onto the per-view action queue and the global sequence list. Complete store set
= the record + two queue tails. No movement field, no command-layer call, no
`+0x64`, no `+0x10C`; the hold release belongs to property 8's `→0` (§16.2's
read). Positive control: the same method finds the sibling paths' extra stores.

**CANCELWALK-F13 — OBSERVED, verifier corrections carried. The s2c `0x0027`
receive path is read to its leaves and the store is value-equal on both builds;
the message is dead as a differentiator in both directions.** Handler
`0x005FD700` applies setter `0x00602910` to the SYNC then the ASYNC copy; the
setter's only direct field store is an unconditional `fstp [esi+0x5C]`
(`0x00602947`); it calls the settle `0x005FF880` (which dead-reckons `+0x78`
ONLY when `+0x48 ≠ 0` — **REALFIX-P4's "`0x00602910` rewrites `+0x78`" is
refined: the rewrite is the settle it calls, gated on an armed leg**) and
re-issues the outstanding grant only when the target is not the +inf sentinel.
On a parked agent the message reduces to storing 288 over 288. Readers of
`+0x5C`: the destination bake and the avoidance predicate (shared by every
movement path including the self-walk) **plus a third reader the first census
missed, in AgTrack at `0x00605897/9F`** — the unqualified "only readers" form is
retired. The elimination is reader-independent: both copies hold 288.0 from our
own create (F9), measured 4,115/4,115 in movetap samples on a build that has
never received a `0x0027`. Do not build a `0x0027` sender to fix cancelwalk;
REALFIX-P4's DO-NOT-BUILD stands reinforced.

**CANCELWALK-F14 — OBSERVED. The cancel-instant zero-lead grant takes the
ordinary BAKE arm at 86.18 u — the handover's ≤1.0 u short-circuit
reconstruction is refuted — and the freeze reframes: the drawn body is already
standing on the destination.** Instrumented replay of `grantsim.simulate()`'s
own locals (arm counts cross-validated against the function's own tallies):
`081335`'s four player grants are `t=3.466 |d|=0.0` (seed), **`t=5.418
|d|=86.18` BAKE (the cancel instant)**, `t=7.502 |d|=0.0` (post-arrival
re-issue), `t=12.308 |d|=89.53` (ordinary heading grant). The copy was parked at
the seed because keyboard walking had sent it nothing (one report refused
`heading-rate`); the grant's destination is the player's own reported point, so
the sync copy walks an invisible 86 u catch-up leg that ends under the player's
feet while the screen shows nothing. R1's capture confirms zero cancel-instant
bytes at the verdict log (`cancelwalk-suppress, fired:false`), with five
ordinary pre-cancel grants (0.0/173.5/56.6/103.0/37.0 u).

**CANCELWALK-F15 — OBSERVED. The frozen press fired BOTH dedup legs, so the
bail is upstream of the dedup — the suppress gates (or the navmesh exit), not
the direction cache.** At the canonical freeze (`081335` t=5.417) the press
carried vec2 `(765.2, −46.0)` (≈east), mt=1; the pre-cast walk's last leg
(t=3.748) was `(555.5, −529.1)` (≈SE), mt=3 — **cos ≈ 0.76 (~40°) off the cache
AND a mode change**. GATE-A′ skips only on direction-within-epsilon AND
mode-unchanged, so had control reached it, ASYNC-MOVE-START would have run and
armed the body. Zero motion for 25 frames says control never got there. The
navmesh variant survives only in a direction-dependent form: the second press
walked from the bit-identical coordinate 2.085 s later (mt=4, ≈NW), so a
position-keyed navmesh zero is excluded by F6's own instants.

### 7.2 The join

The wire says (F9) retail's client entered its cast with the movement machine
explicitly closed — a `0x0028` stop-ack, `0x002B` family writes, a continuously
led sync copy — and ours entered with none of that ever written, at value-parity
on every field a message carries. The binary says (F10/F11) the local walk-start
reads controller state the send path never reads, its writers are local, and the
body's drivability is a latch armed only through that gated path. Those are one
claim from two ends: **the differentiator is client-local state the walk gate
reads and the wire does not carry; the only wire-shaped candidates left are the
stop-closure/family messages whose HANDLERS may write that state — unread — and
everything value-carried is eliminated.** The wire front is otherwise closed.

### 7.3 Surviving candidates, ranked

Constraints any candidate must satisfy: R1 froze with zero cancel-instant bytes;
the second press walks ~2 s later from the same coordinate; retail self-walks
the same edge; F15's bail is upstream of the dedup.

1. **CANCELWALK-H5 (primary) — RECONSTRUCTION.** GATE A (`+0x10C` bit 0x100) or
   GATE B (`+0x64` bit0) is SET on our build when the cancel edge runs the
   applier — set at/for the cast hold, cleared by the time an ordinary press
   works — while retail's client reaches its cancel edge with the bit already
   clear. The writer is untraced (F10: wholesale template/word stores only).
   *Refuted by:* the bit reading CLEAR at a frozen press (R7), or R5 showing the
   walk-start signature present.
2. **CANCELWALK-H6 — RECONSTRUCTION.** Stop-closure prior state: our client
   enters the cast with its last movement episode never server-closed (no
   `0x0028`, no `[1.0,9]`+re-pin — F9), and whatever state that leaves is what
   keeps H5's bit set (or otherwise blocks the applier) at the cancel edge on
   our build only. This is the only surviving candidate the SERVER can act on,
   and it is cheap to test (R6). *Strained by:* the second press walking with
   the episode equally unclosed. *Refuted by:* R6 still freezing.
3. **CANCELWALK-H7 — RECONSTRUCTION, weak.** Direction-dependent navmesh/path
   degeneracy at the press instant (the query's inputs include the heading;
   position-keyed forms are excluded by F15). *Refuted by:* R5 showing no
   walk-start signature (a gate bailed before the query), or R7's bit read.
4. **CANCELWALK-H4 (residual, carried).** Build drift in the cast-hold/resume
   path. Unfalsifiable on loopback; moot for our pinned build (the R4 contract
   stands regardless).

Episode-level companion, not a press-time rival: the latch snap-clear (F11)
explains why the body stays grant-driven for a whole R2–R4 leg, but R1 kills it
as the freeze mechanism.

### 7.4 The next instruments — pre-registered before any run

**CANCELWALK-R5 · the movetap state poll (the owner-offered run).** Loopback,
Isle pin, shipped `--zero-lead` (the freeze must occur), ≥3 cancelled casts plus
one ordinary-press positive control in-session; cast/cancel input operator-driven
per the §3g protocol; the poll is a fixed memory readout and agent-pilotable.
movetap already fetches the full 0xD0-byte AgAgent block for BOTH copies every
poll, so **Tier 1 is decode-only, zero new cross-process reads**: expose async
`+0x48/+0x78/+0x7C/+0xB0/+0xB4/+0x9C/+0xC4`, plus `+0xBC/+0xC0` (facing cache)
and `+0x50` (the planner's movement-type store, written at the walk-start,
zeroed by the halt `0x005FC5C0`) on both copies. **Tier 2** (only if Tier 1
leaves the ranking open): `clientControlled` = AgTrack record +0x00 — movetap
already resolves AgTrack for its fence walk, check whether rec+0x00 is already
in hand before plumbing anything. The ChCliBase bits themselves are a different
object movetap does not resolve; that read is R7's.
*Predictions:* H5/H6 (bit set) → walk-start signature ABSENT at the frozen
press: async `+0x50/+0xC4/+0x60` unchanged across the press, velocity stays 0,
`clientControlled` stays 0 — while the ordinary-press control shows all of them
change within one poll (control fails ⇒ the run is void, not confirmatory).
H7 → signature PRESENT but degenerate: `+0x50` takes the press's mt yet no leg
bakes. Either way the facing pair classifies its own writer: updating at the
frozen press puts it before the gates (timeline marker); only at the ordinary
press, behind them (second signature bit).

**CANCELWALK-R6 · the stop-closure run (cheapest, and the only server-side
lever left).** One loopback run with a diagnostic arm that answers the pre-cast
`0x0047` the way retail answered its last one — a one-shot `0x0028 [agent]`
(and, as a second arm, retail's other form: `0x002B [1.0, 9]` + zero-distance
re-pin) — everything else the shipped zero-lead configuration. *Predictions:*
H6 → the single mid-cast press now WALKS; H5-without-H6, H7, H4 → still
freezes. A freeze here also retires F5's residual ("the one unread player-
targeting pre-press delta") as a cancelwalk candidate. The same session can
close F9's exposure confounder: complete one cast before the cancelled one.

**CANCELWALK-R7 · the flag read at the edge.** If R5 lands signature-absent and
R6 freezes: read `[ChCliBase+0x10C]` bit8 and `[ChCliBase+0x64]` bit0 at a
frozen press — one-shot int3/trnhook at `0x0081A931`/`0x0081A93C` (arm before
launch; the injection window is map-load), or plumb the controller object into
movetap. This separates H5's two bits from each other and from H7 directly.

### 7.5 Measured dead this round — do not retry

- `0x0027`/speed-base as differentiator, trigger, or fix (F8/F13) — and the
  buff cluster wholesale: a baseline-restore 15 s pre-press on an independent
  clock. REALFIX-P4 stands, with its mechanism sentence refined (F13).
- Property 59 as a movement candidate (F12).
- The ≤1.0 u short-circuit reconstruction of the cancel grant (F14 — it is an
  86 u bake to the player's own feet).
- The GATE-A′ dedup as the freeze mechanism (F15 — both legs fired and it froze
  anyway), and position-keyed navmesh zeros (F15).
- Press-time latch snap-clear (F11 scope note — R1 froze on zero bytes).
- Value-carried wire state as the differentiator (F9 — parity verified by
  independent recount). What stays live on the wire side is exactly one thing:
  the stop-closure HANDLER state, and R6 prices it.
