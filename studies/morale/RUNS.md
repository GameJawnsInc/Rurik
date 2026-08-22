# Morale probe runs

## Run 1 — `--probe morale`, 2026-08-20, GREEN

```bash
python toolkit/harness/session.py --keep-open --shots 3 --hold 75 --warn 8 \
    --game-args "--probe morale --map 146"
```

Agent-piloted, loopback, no operator input after the countdown. Harness
`vault/captures/harness/20260820T220732`, game channel
`vault/captures/gamesrv/authsrv-20260820T220800-c1.jsonl`, client build 38797
(`vault/run/2026-07-29_221c13772c7a`, ours-DH, CAGED, chosen by build and never
by mtime). `RUN VERDICT: PASS (target: map)`, 0 undecodable, clean client exit.

**All six steps fired and the gamesrv log printed each one** — the check that
comes before reading a pixel, because a probe that half-runs looks like a
refutation. Send times off the capture, and the frames that read them:

| step | sent | what | frame that first shows the change |
|---|---|---|---|
| 1 | t+3.81 | `0x00EE [10, −15]` alone | — nothing, through hold002/003/004 (t+6.2, 9.6, 13.0) |
| 2 | t+13.81 | `0x009C [player, 70]` alone | **hold005, t+16.4** — a red chevron reading **−30%** |
| 3 | t+23.82 | property 41 = 14 | **hold008, t+26.5** — energy bar reads **14** |
| 4 | t+25.83 | property 42 = 70 | **hold009, t+29.9** — health bar reads **70** |
| 5 | t+35.85 | `0x009C [player, 110]` | **hold012, t+40.1** — a teal chevron reading **+10%** |
| 6 | t+41.86 | `0x00EE [10, 0]` control | — nothing changed, hold013…hold023 (t+43.5…77.4) |

Frame strips kept out of the repo (they are screenshots of ArenaNet's client):
`vault/research/morale/dp_series.png` (the corner, all 23 frames) and
`bars_series.png` (the two pools, all 23 frames).

### Results, against the predictions registered before the run

| id | predicted | result |
|---|---|---|
| MORALE-P1 | `0x00EE [10, −15]` draws the indicator | **REFUTED.** Nothing appeared, for 9.2 s and three frames, and neither pool moved |
| MORALE-P2 | `0x009C [player, 70]` draws it instead | **CONFIRMED.** Red downward chevron, `−30%`, top-left corner at (10,32)–(60,82) |
| MORALE-P3 | the pools do not move until properties 41/42, and then they read OUR numbers | **CONFIRMED, twice over.** See below |
| MORALE-P4 | `0x009C [player, 110]` draws a BOOST rather than a penalty | **CONFIRMED.** The chevron flips up and turns teal: `+10%` |
| control | `0x00EE [10, 0]` changes nothing | **HELD.** Eleven frames over 34 s, no change |

**MORALE-Q1 is answered: `0x009C` is the display channel.** The one thing this
run cannot separate is whether `0x00EE`'s delta silently updates the client's
stored morale without repainting — the corner is the only readout here. What it
does establish is that the delta alone does not reach the screen, over nine
seconds and three repaint opportunities.

**MORALE-Q2 is answered, and one frame carries the whole answer.** At t+16.4 the
corner reads **−30%** while the health and energy bars still read **100** and
**25**. The client displays the penalty and does not apply it: it recomputes
neither pool from morale. Then properties 41/42 land and the bars read **14**
and **70** — and 14 is the number that makes this a measurement rather than a
coincidence, because −30% of base 20 is 6, so a client doing its own arithmetic
would have shown **19**. It showed ours.

**So the maxima are the server's job, and a server that sends morale without
them ships a death penalty that costs nothing.** Which is what `push_morale`
does, and now for a measured reason rather than a cautious one.

### Two things measured in passing

- **The HUD repaints on a delay, not on the packet.** Three independent cases:
  the corner at 2.6 s (step 2) and between 0.9 s and 4.3 s (step 5), the health
  bar between 0.7 s and 4.1 s (step 4), the energy bar within 2.7 s (step 3). In
  every case the frame taken under a second after the send still showed the old
  value. Whether that is a UI poll or screenshot lag is not separated here; the
  practical consequence is that **a probe reading this HUD needs ≥5 s between a
  send and its screenshot**, and this run's 10 s spacing was right by luck
  rather than by design.
- **The indicator lives at the very top-left corner, under the title bar** —
  (10,32)–(60,82) at 1936×1040 windowed. The first crop of this run's frames
  started at y=100 and found nothing, which read for several minutes like a
  refutation of both P1 and P2. Screenshot readouts want the frame looked at
  whole before they want a crop.

---

## Run 2 — `--probe morale_store` + a memory read, 2026-08-20, GREEN

**MORALE-Q7: does `0x00EE [attr 10, delta]` write the client's stored morale, or
is it ignored?** Run 1 established that it draws nothing; that is not the same
claim, and a screenshot cannot tell a silent write from a no-op.

```bash
python toolkit/harness/session.py --keep-open --hold 130 --shots 0 --warn 8 \
    --game-args "--probe morale_store --map 146"
python toolkit/clientscan/moralestore.py --wait-for-client 150 \
    --anchor 424242 --span 0x80 --seconds 100 --period 0.5 --tries 120
```

Harness `20260820T224356`, `RUN VERDICT: PASS`, all eight steps printed in the
gamesrv log. Full scanner output: `vault/research/morale/MORALE-Q7-RUN.txt`.

**NOBODY'S OFFSETS WERE USED.** The probe walks the attribute store through
three values only we could have chosen and holds the experience field constant
at 424242; the scanner finds that constant (2 hits in 271 MB — the two halves of
one dupe pair) and watches ±0x80 around it. What the block is, is then read off
our own numbers rather than off a header.

### The answer: it writes, and only the repaint was missing

| probe step | sent | the watched dword |
|---|---|---|
| 1 | `0x00E9` field 10 = 77 | 77 |
| 2 | `0x00E9` field 10 = 88 | **88** |
| 3 | `0x00E9` field 10 = 66 | **66** |
| 4 | **`0x00EE [10, −13]`** | **53** — 66 − 13, applied |
| 5 | `0x009C [player, 41]` | **no change** |
| 6 | **`0x00EE [10, +7]`** | **60** — 53 + 7, both directions |
| 7 | `0x00E9` field 10 = 100 | **100** — the control held |

So **MORALE-Q7 is answered: the delta is applied, `+=`, in both directions, and
within one 0.5 s sample of the packet.** `0x00E9`'s full set is an absolute
store to the same slot. What `0x00EE` does not do is repaint the corner — that
is `0x009C`'s, and step 5 proves the two are *different stores*: the per-agent
message moved the indicator in Run 1 and moves nothing in this block.

Two channels, two stores, one number:

- **`0x00EE` / `0x00E9` → the player's attribute block**, which is what the Hero
  window reads. Delta and absolute.
- **`0x009C` → the per-agent morale**, which is what the corner and (by its
  shape) the party window read. Absolute, and it names an agent because a party
  member's penalty has to be drawable too.

A server that sends only one of them leaves the other stale. Ours sends both.

### The block's own shape, measured

The dwords that hold our values sit at exactly `attr_id × 8` from the experience
field, each **stored twice, adjacent**:

```
+0/+4    424242   experience     attr 0    0 × 8 = 0
+72/+76  17       level          attr 9    9 × 8 = 72
+80/+84  morale   morale         attr 10  10 × 8 = 80
+104/+108 13      skill points   attr 13  13 × 8 = 104
```

**The wire's `attr_id` is literally an index into this array**, and every entry
is a value/dupe pair — which is the layout `studies/character/STORAGE.md` §2
described from GWCA's header and could not check. It is checked now, from the
client's own memory, against numbers we chose: three fields at three predicted
offsets, and nothing else in ±0x80 moved.

### What went wrong first, and it was ours

The attempt before this one (harness `20260820T223937`, run itself PASS, all
eight steps landed) measured nothing: the scanner's first scan looked for the
value under test, ran while the client was still loading, and locked onto ~900
coincidental `77`s that no later step could rescue. **Locate on a constant the
experiment never changes, then watch a window around it** — there is no race in
that shape, and it is what the anchor mode does now.

---

## Run 3 — a REAL death, penalty armed, 2026-08-22, GREEN (two arms)

The runs above put morale on the wire by hand. This one lets the game do it: an
enemy kills the player, `kill_player` charges the penalty, and the client is
never told anything except what the mechanic itself produces.

```bash
# arm A -- the grace window HOLDS
python toolkit/harness/session.py --keep-open --hold 105 --shots 3 --warn 8 --enemy \
    --game-args "--death-penalty --enemy-hit 0.35 --map 146"
# arm B -- the grace window EXPIRES
python toolkit/harness/session.py --keep-open --hold 125 --shots 3 --warn 8 --enemy \
    --game-args "--death-penalty --enemy-skills 276 --map 146"
```

Captures `20260822T140922` (A) and `20260822T141510` (B). Agent-piloted, no
operator input, loopback, ours-DH client, cage verified. Both PASS to the map
verdict, and every death below is in the gamesrv log before a pixel was read.

### Arm A — the waiver, watched

Four deaths, ~12.6 s apart from each resurrection. The first charged; **every
later one was waived**, and the log says so in as many words:

```
[c1] morale 100 -> 85 (-15%, died): max health 85, max energy 22
[c1] death penalty WAIVED: 12.6s since the resurrection, inside the 14s grace window
[c1] death penalty WAIVED: 12.7s since the resurrection, inside the 14s grace window
[c1] death penalty WAIVED: 12.6s since the resurrection, inside the 14s grace window
```

On screen: the corner goes from empty to `−15%` about 3 s after the death and
**stays −15% for the remaining 27 frames (81 s)** across four more deaths. The
health bar reads `85` at a full bar after each revive, where the same bar read
`100` before the first death — the penalty as a number the client itself prints.

**`--enemy-hit` was not what set that cadence, and the run says so.** The kills
came from the hostile's *skill* (46 damage a cast), not its swing, so the flag
scaled a channel that never landed the killing blow. It is still the right knob
for arm A's purpose — a fast death — but the honest reading is that arm A
demonstrates the waiver at a 12.6 s cadence that the SKILL produced.

### Arm B — the expiry, and the whole ladder

Limiting the hostile to a self-heal (`--enemy-skills 276`) leaves only the melee
swing, which needs eight hits: deaths land **16.1 s** after each resurrection,
just outside the window. So every death charges, and the run walks the entire
mechanic:

| death | t | since revive | morale | max health | max energy |
|---|---|---|---|---|---|
| 1 | 17.9 s | — (first) | −15% | 85 | 22 |
| 2 | 44.1 s | 16.1 s | −30% | 70 | 19 |
| 3 | 70.4 s | 16.1 s | −45% | 55 | 16 |
| 4 | ~96 s | 16.1 s | **−60%** | 40 | 13 |

The corner draws each rung in turn — `−15%`, `−30%`, `−45%`, `−60%` — and then
**stops at −60% for the last 27 s and eight frames**, which is the cap holding,
watched rather than asserted. The health bar reads `85` and `70` at a full bar
after revives 1 and 2, and 47/55 and 34/40 mid-fight later.

**The energy ladder is the discriminating measurement, four times over.**
25 → 22 → 19 → 16 → 13 is −3 per rung: 15% of BASE energy 20, not of the 25
total. Total-scaling predicts 21.25 / 18.06 / 15.35 / 13.05 and matches at no
rung. §2.2 rested on one retail observation; it now has four of our own, and the
client accepted every one.

### One thing this run does not explain — ANSWERED in Run 4

The player's ENERGY readout drains on its own — 25 → 10 → 0 in arm A, and it
does not track the maxima we send. This server sends no energy debit at all, so
the drain is the client's own model reacting to something else in the session.
It was passed to the energy/adrenaline arc, which supplied the difference: these
two arms sent property 43 on `0x00A3`, and the fix to `0x00A2` landed at 14:24,
*after* both. **Run 4 re-ran arm A on the fixed tree and the drain is gone** —
energy reads 0 while dead and the full 22 while alive. Which of the two changes
in that merge fixed it is not established; see Run 4.

---

## Run 4 — does the energy readout still drain? 2026-08-22, ANSWERED: no

Run 3 recorded one thing it could not explain: the player's ENERGY readout fell
to 10 and then 0 while alive, and did not track the maxima we send. The
energy/adrenaline session supplied the difference — **Run 3 sent property 43 on
`0x00A3`, and the channel fix to `0x00A2` landed in `b788ac1` at 14:24, after
both arms had run** — and asked for the decisive re-run.

```bash
python toolkit/harness/session.py --keep-open --hold 105 --shots 3 --warn 8 --enemy \
    --game-args "--death-penalty --enemy-hit 0.35 --map 146"
```

Capture `20260822T143508`, current `main`, arm A's command verbatim so the two
runs differ in the tree and nothing else. Every property-43 send in the log is
now `(0x00a2, 14B)`.

**It does not reproduce.** The energy readout across 32 frames is only ever two
values: **0 while the player is dead**, and **22 — the full penalised maximum —
whenever they are alive**, at t+23, t+53, t+74 and t+104, spanning four
death/revive cycles. Run 3's 10 and 13 at equivalent points are gone.

**What that does NOT establish is which change fixed it.** The energy arc's
merge carried two things at once: the channel move, and new handling that stops
regeneration on death and restores it at the revive ("energy regeneration stops:
the player is dead" / "back to 3 pip(s) (revived, deferred)"). Either could
account for the difference, and this run cannot separate them. What is settled
is that the behaviour Run 3 flagged is not present in the tree we ship.

### The separation arm, assessed 2026-08-22 — designed, and ruled not owed

Nothing downstream consumes the answer. The channel move is pinned to retail's
own wire — every corpus sighting of property 43 rides `0x00A2`, zero ride
`0x00A3` (`authsrv.py`'s channel note at the death batch) — and the death-stop
/ revive-restore is retail-corroborated from the same batches (43 = 0.0 in the
death tick, the rate re-sent at the resurrect). Neither change would be
reverted whichever of them cured the drain, and no open item — MORALE-Q4–Q6,
`PLAN.md` §8's list — depends on knowing which. What the arm would buy is one
fact about the client's `0x00A3` parser, with no consumer waiting for it.

The arm itself, recorded so nobody re-derives it: re-run this run's command on
a tree with ONLY the channel hunk of `b788ac1` reverted — property 43 back on
`0x00A3`, the death/revive regen handling kept. Drain reproduces → the channel
was the cure (and the client's `0x00A3` handler mis-takes a property retail
never sends it on that opcode); readout stays 0-dead / 22-alive → the regen
handling was. One flag apart if anyone ever builds it, per the
`--refusal-silent` precedent. MORALE-Q3 stays open as a client-behaviour
question, not as debt.

**Answered later the same day.** The client-behaviour question this section left open fell to a cheaper instrument than the arm it designed: a desk re-read of Run 3 arm A's own frames plus one probe run, with no revert built — Run 5 below. The handling was the cure; the channel was never the disease.

---

## Run 5 — `--probe regen_channel`, 2026-08-22, GREEN: both channels write one store

**MORALE-Q3.** Before this run, the desk work re-read Run 3 arm A
(`20260822T140922`) against its own wire, and the "drain" dissolved:

- That tree sent property 43 **only** on `0x00A3` (0.0396 at spawn; 0.045,
  nonzero, inside death 1's batch) and **no revive ever refilled energy** —
  no property 52, nothing.
- The frames, joined to the capture by mtime: energy **25 with three regen
  arrows** through the pre-death window — three arrows for a 3-pip rate the
  client only ever heard on `0x00A3`. After revive 1 the readout **climbed
  10 → 13 → 17 → 20** across four frames, slope 0.99/s — exactly the
  A3-sent 0.045 × 22. After death 2 (grace-waived, so no batch, so no fresh
  property 43) the readout is **0 in every later alive window**: the client's
  own death path kills regeneration and nothing ever re-armed it.
- So Run 3's "25 → 10 → 0" was never a drain. It was a full pool, then the one
  re-armed climb sampled at 3.4 s cadence, then flat zero — **cured by the
  merge's handling (revive refill + rate re-send), not by the channel move.**
  The channel had demonstrably delivered its value the whole time.

That consumption was observed inside a death batch, and the context is part of
the claim — so the probe asked the same question with no death anywhere near
it, one variable at a time:

```bash
python toolkit/harness/session.py --keep-open --hold 70 --shots 2 --warn 8 \
    --game-args "--probe regen_channel --map 146"
```

Harness `20260822T160301`, gamesrv `authsrv-20260822T160333-c1.jsonl`,
`RUN VERDICT: PASS`, all five steps in the log before a pixel was read.
Sends at t=4.8 (43 = 0.0 on `0x00A2`), 10.8 (62 = −0.88), 20.8
(**43 = 0.0792 on `0x00A3`**, 6 pips), 32.8 (43 = 0.0 on `0x00A2`), 40.9
(43 = 0.0396 restore). Frames every 2.3 s; the strip is
`vault/research/morale/q3_energy_series.png`.

| id | predicted | result |
|---|---|---|
| Q3-P1 | zeroing the rate on `0x00A2` clears the arrows | **CONFIRMED** — `>>>` at t 2.5–4.8, gone by 7.2 |
| Q3-P2 | drained bar sits flat at zero rate | **CONFIRMED** — **3**, five consecutive frames, 11.8–21.1 |
| Q3-P3 | 6 pips on `0x00A3` restarts the climb at ~2/s | **CONFIRMED** — **6 → 11 → 15 → 20 → 24** over 9.3 s = **1.94/s** against the 1.98 sent, with the arrow count jumping 0 → **six** |
| Q3-P4 | a `0x00A2` zero stops what `0x00A3` started | **CONFIRMED** — arrows gone at 35.0 (the bar had already capped at 25, so the freeze itself is invisible; the arrows carry this one) |

**MORALE-Q3 is answered: `0x00A2` and `0x00A3` are two doors to the same
regeneration store.** The client's shared dispatcher (`0x00818210` case 3,
studies/agentprops) said so statically; arm A's frames said so in a death
batch; this run says so in isolation, both directions, with the arrow count
tracking the sent pip value. Retail's exclusive use of `0x00A2` (52 of 52) is
a fidelity fact about retail, not a functional constraint on the client — the
spawn-burst move to `0x00A2` stays correct and stays cosmetic. Scope: the one
field this run does not vary is `0x00A3`'s cause slot (sent = target = player).

Honest residue: hold025/026 were skipped ("client not foreground") — after
step 5, nothing unmeasured.

---

## Run 6 — `--probe prop54`, 2026-08-22, GREEN: property 54 is a floating "+N"

**MORALE-Q4.** The desk half came first and changed the prediction: the int
path's pool dispatch (`0x00818170`) returns for 54, but the shim behind it
carries **two more property switches** the 2026-08-11 walk did not read, and
54 has a real arm in the third (`0x00812E57`). The arm writes **no store**: it
calls AvApi `0x007E0290`, which queues AgentView EFFECT event kind **0x0D**
`{which=0, value}` (`avevents.py --id 54` reproduces this), whose drain
(`0x007FA42B → 0x007EBD30`) posts **UI event `0x1000000F`** with the value,
behind three gates (a global, an FP screen-space check, `byte [char+0x71] > 1`).
A notification, not state — but whether its face is a floating number, an orb
flash or a swallowed event, only a client can say.

```bash
python toolkit/harness/session.py --keep-open --hold 70 --shots 2 --warn 8 \
    --game-args "--probe prop54 --map 146"
```

Harness `20260822T160555`, gamesrv `authsrv-20260822T160628-c1.jsonl`,
`RUN VERDICT: PASS`, all six steps logged. `0x009F [54, player, 13]` at t=4.8
and 12.8, `[54, player, 5]` at 20.8 and 28.8, then the control pair
`[41, player, 19]` at 36.9 and `[41, player, 25]` at 42.9. Frames every 2.3 s;
strips in `vault/research/morale/q4_bars_series.png` and
`q4_body_region.png`.

- **The face: a magenta floating "+13"** above the player's head at t=14.0 —
  1.2 s after the second send — and a **"+5"** at t=30.3, 1.5 s after the
  fourth. The number tracks the payload exactly. Each callout is **gone by the
  next frame** (~2.3 s later), which is why every value was sent twice: the
  first "+13" died entirely inside the 2.3 s between the send and its frame.
- **No store moves.** Both bars, both numbers, the arrows, the corner and the
  chat hold pixel-still through all four sends — the adjacent-frame diff
  census puts every hot cell on the player's idle animation, present in
  send-free windows too.
- **The instrument was live.** Property 41 = 19 moved the energy maximum to
  **19** on the very next frame window and the restore put back 25. A null
  from a dead channel would have been unreadable; this null has a positive
  control.

**MORALE-Q4 is answered: int property 54 is the floating energy-gain callout,
display-only.** Retail's one sighting — `[54, 27, 22]` in the resurrect
batch — is the "+22" a shrine refill draws, and the value equalled the new
maximum because a refill from the client's death-zeroed pool gains exactly the
maximum. The server now sends it in `restore_player_energy`, in retail's
position after the property-52 gain (`test_pools.py` §8b pins it). The gates
pass for the player in an explorable; which of them retail's other contexts
can fail is not probed here.
