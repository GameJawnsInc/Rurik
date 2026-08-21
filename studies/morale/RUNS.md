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
