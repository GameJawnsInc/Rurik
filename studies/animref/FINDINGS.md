# ANIMREF findings — what the live corpus says about attack/cast animation wire

**2026-08-30.** Instrument: `toolkit/authsrv/animgrammar.py` (ANIMREF-R1, this arc's
episode extractor), run over the complete `vault/captures/live/` corpus as of this date:
**21 capture directories, 61 connections, 61/61 fully framed, 0 refused** — a partial
frame refuses the whole connection out loud, so these figures carry no silently-dropped
tail. Referent artifact: `vault/research/animref/episodes_live.jsonl` (2,354 episodes)
+ `census_live.json`. The tool's own correctness gates: `--control` pins the
castmech-overlap figures (7 checks — castgaps' seven cycles, the four 0.74–0.77 s
aftercast gaps, the Power Shot windup gaps to 0.1 ms), and
`test_animgrammar.py` (35 bare-machine checks) pins the machines on synthetic streams.
Labels per `studies/character/FINDINGS.md`. Corpus counts below are FLOORS pinned
as-of 2026-08-30 (the corpus grows); the two castmech captures are the immutable
signature set.

Populations: **1,332 swing opens** (1,042 landed / 150 stopped / 125 reopened /
15 censored), **1,022 cast episodes** (self 106, other agents 916).

---

## 1. The windup is NOT a constant fraction — it is `interval/2 − 0.1 s` (OBSERVED)

The shipped `SWING_WINDUP_RATIO = 0.4458` (fit 2026-08-07/15 on n=42, declared speeds
1.75/2.0 only) does not survive the population. Landed-swing windup over the declared
`0x0035` interval (base × modifier):

| declared interval | n | ratio mean | sd |
|---|---|---|---|
| 1.33 s | 998 | 0.4250 | 0.0077 |
| 1.75 s | 25 | 0.4408 | 0.0102 |
| 2.00 s | 18 | 0.4502 | 0.0060 |
| 3.00 s | 1 | 0.4719 | — |

The fraction RISES with the interval — no constant ratio fits. The additive law does:

> **windup = interval/2 − 0.1 s**

Per-swing |residual| against three rivals, whole corpus (n=1,042):

| law | 1.33 (n=998) | 1.75 (n=25) | 2.0 (n=18) | 3.0 (n=1) | ALL mean |
|---|---|---|---|---|---|
| **interval/2 − 0.1** | **6.3 ms** | **10.4 ms** | **10.4 ms** | **15.7 ms** | **6.5 ms** |
| 0.4458 × interval (shipped) | 28.1 | 11.3 | 12.1 | 78.3 | 27.5 |
| 0.4250 × interval (refit) | 6.3 | 30.9 | 50.4 | 140.7 | 7.8 |

Only the additive law's residuals are flat across intervals — the refit constant is the
classic overfit (perfect on its own population, 141 ms off at 3.0 s). **Cross-family
retrodiction it was never fit to**: the Power Shot attack-skill E4→E5 gaps (bow, 2.475 s,
a fifth interval) measure 1.1374/1.1387 s; the law predicts 0.5×2.475 − 0.1 =
**1.1375 s** — within 1.3 ms. This also retro-explains castmech M1's three "converging"
ratios (0.4540 @ 2.0 declared ≈ 0.45, 0.4583–0.4669 player @ 1.75, 0.4601 @ 2.475) as
one law sampled at three intervals, not one constant measured thrice.

**Caveats, stated**: every corpus swing rides modifier 1.0 — whether IAS/DAS scales the
−0.1 term (i.e. `mod×base/2 − 0.1` vs `mod×(base/2 − 0.1)` vs `mod × base − 0.2)/2`…)
is **UNVERIFIED**; the parameterisation `(interval − 0.2)/2` is wire-indistinguishable
from `interval/2 − 0.1`; and weapon class is confounded with interval except for the
bow cross-check. The residual floor (~3–15 ms p50) is consistent with server-side
scheduling quantisation and is not modelled.

## 2. The cast-open FORM rule: the channel follows the target (OBSERVED, 758/758)

Corpus-wide census of every cast-animation property open:

| form | prop 50 (attack skill) | prop 60 (spell) |
|---|---|---|
| `0x009F [prop, agent, skill]` (untargeted int channel) | 0 | 531 |
| `0x00A0 [prop, agent, target, skill]`, target ≠ 0 | **222** | 227 |
| `0x00A0` with target = 0 | 0 | **0** |

**Retail never sends a zero target on the targeted channel — it switches channels.**
Attack skills always have a target (222/222 targeted). Our two send sites both break
this rule (divergences D15/D4, `studies/animref/PLAN.md` §2):
`authsrv.py` player press/begin sends `0x00A0 [... , target or 0, skill]` — the
`target=0` form retail uses **zero** times in 758 opens — and the NPC cast site sends
`0x009F [60, agent, skill]` untargeted for casts that have a target. The derived fix is
mechanical: **A0 iff the cast names a target, else 9F.**

## 3. The attack-skill trio exists at scale — castmech's "silent E5" was a bow artifact

castmech (two captures) had property 46 and 49 at zero occurrences and scoped the
attack-skill E5 as "silent — no 58, no 46, 2/2". The full corpus:
**46 (attack_skill_finished): 164 · 49 (attack_skill_stopped): 12 · 50: 222.**
The self attack-skill finish signatures include `['E5','46','dmg','E3']` and
`['E5','46','crit','E3']` — **the melee attack-skill E5 carries 46 + the damage in one
batch**. The Power Shot pair's silence is the projectile in flight: for a bow the
46+damage ride the ARROW's landing, not the E5 instant. (One capture shows
`['E5','46','38','E5','E3']` — overlapping cycles, kept as-is.) OBSERVED; the per-family
timing split (melee at E5, projectile at impact) is RECONSTRUCTION pending a
projectile-flight join. Our server never sends 46 or 49 (both defined-unsent).

## 4. The INSTANT-SKILL family (prop 48) — a whole cycle in one batch, 62 occurrences

`['E4','62','E5','48','21','E3']` — one batch, 27+ occurrences (plus variants), closing
complete at the later E6: press-accept, energy spend, cast-end, **property 48**, the
effect application, aftercast-end, all at ONE instant. This is the stance/shout family
("Charge!" etc.). skillcast §15 read 48's handler as UI-only/no-animation — consistent:
an instant skill has no cast animation to drive. **We never send 48**; our instant
skills (if any ride the generic path) would emit a spell-shaped cycle. OBSERVED.

## 5. Misses exist — 7 landed swings carry no damage (D6 moves)

`combat/PLAN.md` §17c: "the corpus contains zero observed misses — all 42
MELEE_ATTACK_FINISHED are paired with damage." At n=1,042: **1,035/1,042 pair;
7 do not** — all seven in the PvP captures (20260817T231139, 20260819T132414), all at
full windup (dt 0.563–0.574 over 1.33), varied attacker/victim pairs. A swing that
completes its windup and lands NO damage is the miss/block shape §17c said was
indistinguishable from a cancel — it is distinguishable: **a miss closes with
FINISHED-and-no-damage; a cancel closes with 3 (ATTACK_STOPPED)**. OBSERVED n=7,
mechanism (miss vs block vs evade) UNVERIFIED — the PvP context has all three.

## 6. The scripted-animation channel is live in retail traffic

Properties our code defines and never sends, now witnessed: **22 (ApplyAnimation):
60 occurrences** — mostly standalone `['22']` with a dword payload that reads
float-shaped, some with `['22','11','11']` / `['22','12','12']` companions;
**23+28 (param + ApplyAnimationLoop): 17 paired occurrences** (always together, e.g.
value 8 on the ranger capture); **63 (knocked_down): 3**. And the negative that
matters: **35 (interrupted): 0 in the whole corpus** — D5 stays a decode question, not
a mining question. OBSERVED counts; semantics UNVERIFIED (R4's decode targets).

## 7. Property 45 at n=79 — a ~1 Hz per-agent mark, plus the E2 adjacency

castmech had ONE occurrence. The corpus has 79: **67 standalone `['45']`, value always
0**, on PvP casters at ~1 s cadence (agent 8: t=41.258, 42.268, 43.257, 45.257…), plus
4 riding E2 instants (the terminated-cast adjacency castmech saw) and a few in
death/effect batches. Cadence-mark-shaped (cast progress? charge?), UNVERIFIED —
now decodable with real n. Stays unsent.

## 8. Grammar confirmations and smaller yields

- **Self press/E5/cancel bursts at scale confirm castmech §3c**: the E5 batch closes
  with the `8:0,8:1` pulse on every complete self spell cycle (19/19 signature rows);
  press bursts show the transition-only hold exactly as measured; the begun-cast cancel
  is `['8:0','59','E2']` 4/4.
- **Queued attack-skill presses** are the majority self attack-skill open
  (`['E4','8:0','8:1']` ×23, no spend, no animation property at press) — the animation
  and debit ride the begin, retail's own queue law, our wiring's shape.
- **Other-agent cancels: n=18**, dt-at-cancel spread 0.54–3.0 s.
- **Status-marked cast episodes** (0x00F1 during the episode): dozens, including
  `cancelled` closes whose cancel batch carries the status change — the ANIMREF-Q2
  material (does death cancel the cast? the co-occurrence says yes in several cases;
  the 0x00F1 value semantics need the isle life-state decode before this is OBSERVED).
- **Zero-gap identity** extends: FINISHED and damage share the wire instant on
  1,035/1,042 landed swings (the 7 exceptions are §5's misses, not timing spread).

## 9. What this run does NOT settle

- The IAS/DAS interaction with the windup law (§1 caveat) — no modified-speed swing
  exists in the corpus. A derivation from the client's `0x007F82C0` duration math
  (`modifier × base`, the 1.25 literal) may settle which term the −0.1 attaches to
  without any run.
- Interrupt wire shape (35 at zero, E7/E8 unexamined here) — D5, client decode.
- Prop 22/23/28 payload semantics (§6) and prop 45's trigger (§7) — R4 decode targets.
- The projectile-flight join for bow attack skills (§3) — needs a projectile-events
  extractor pass, desk-only.
- Whether our own wire matches ANY of this — that is ANIMREF-R2 (the gamesrv-corpus
  extraction + diff), deliberately a separate entry point so origins cannot pool.

## Provenance

All figures are measurements over the owner's own live captures via extractors in this
repo (`animgrammar.py`, this arc; `tape.py`/`codec.py`, prior arcs); scratch probes and
the referent JSONL are under `vault/research/animref/`. No asset bytes, no client
launch, no upstream derivation — no §6.1 register row required.
