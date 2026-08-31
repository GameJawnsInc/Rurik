# ANIMREF findings — what the live corpus says about attack/cast animation wire

**2026-08-30.** Instrument: `toolkit/authsrv/animgrammar.py` (ANIMREF-R1, this arc's
episode extractor), run over the complete `vault/captures/live/` corpus as of this date:
**21 capture directories, 61 connections, 61/61 fully framed, 0 refused** — a partial
frame refuses the whole connection out loud, so these figures carry no silently-dropped
tail. Referent artifact: `vault/research/animref/episodes_live.jsonl` (2,354 episodes)
+ `census_live.json`. The tool's own correctness gates: `--control` pins the
castmech-overlap figures (7 checks — castgaps' seven cycles, the four 0.74–0.77 s
aftercast gaps, the Power Shot windup gaps to 0.1 ms), and
`test_animgrammar.py` (41 bare-machine checks) pins the machines on synthetic streams.
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

**Every form the fix can emit has a retail witness — with one edge it does not, and
auditing the fix is what found it.** Restricting the census to the OBSERVING PLAYER's
own agent (the case our press path produces): prop 60 self-targeted 16, prop 60 self
**untargeted 8** (skills 1 and 814, three captures), prop 50 self-targeted 45, prop 50
self-untargeted **0**. So the targetless self spell — the form our fix newly emits where
we used to send `A0`-with-target-0 — is retail's own shape, which is the fix's strongest
single piece of evidence. But **prop 50 untargeted is a form retail never sends** (222/222
targeted, self and other alike), and our pre-fix logs carried 12 attack-skill opens with
no target, which the fix converts into exactly that unwitnessed shape. **D20, recorded:**
retail's client does not produce an attack-skill press without a target, so those 12 are
our own synthetic presses; the server currently accepts a press the real client would not
make, and neither the old form nor the new one is right for it. The honest fix is upstream
(refuse a targetless attack-skill press), not a third channel rule — filed, not wired,
because the harness's own test presses use target 0 and would need moving first.

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

## 9. ANIMREF-R2: our own wire against the referent (2026-08-30, same session)

Instrument: `animgrammar.py --ours / --diff` — `scan_ours()` walks the gamesrv
`.jsonl` corpus (1,217 files; per-file origin check via `origin.origin_of`, 19
tape-replay sessions excluded by their `tape[...]` labels — a tape's game channel
is ArenaNet's stream played back, and scoring it as our emitter would grade
retail against retail; 0 refused rows), decodes every `sent` row's plaintext
through the same Codec, and runs the same episode machines. Ours-side batches
are re-clustered at eps=5 ms (`assign_batches` — each of our sends stamps its
own clock where a wire batch shares one; 5 ms is two orders under the closest
legitimate neighbours). Era filters on the filename stamp make the control
possible. Diff artifact: `vault/research/animref/diff_ours_20260822_now.json`.

**The known-bad control PASSES** (`--before 20260822`, 1,045 files): the diff
flags exactly what castmech later fixed — properties 3/8/58/59/50 all
NEVER-SENT-BY-US, 21 cast opens in the `A0_target0` form retail never uses, the
player's zero-windup era at −774.7 ms off the law and the NPC era at +130.5 ms
(the pre-2026-08-11 fixed-0.899 mixture). A diff that scored this era clean
would have been measuring nothing.

**The current era** (`--after 20260822`, 122 files — all predating this
session's R3 fixes, so the three fixed rows double as regression detectors):

- **VALIDATED at signature level**: our self-cast grammar matches retail's
  shape-for-shape — top open `['E4','62','60T','8:1']` (ours 59, live 9), top
  finish `['E5','58','8:0','8:1']` (ours 22, live 6), cancel `['8:0','59','E2']`
  both sides. The castmech wiring holds at population scale.
- **D15's observable**: ours 12 (`50/A0_target0`) + 9 (`60/A0_target0`) vs
  retail 0/758 — fixed this session (`5a8907e`); the rows must go to zero in
  post-fix logs.
- **D18 (NEW): the tick tail.** Our landed windups sit +16/+34 ms above our own
  ratio model (iv 1.33 n=54, iv 1.75 n=12) — the 20 Hz world tick delays the
  landing by 0–50 ms after `swing_lands_at` fires. Retail's residuals are ±6 ms
  flat: its scheduler is finer than our tick. Post-fix wire will read
  ≈ law + ~25 ms until the landing leaves the tick. Recorded, not yet fixed.
- **D19 (NEW, FIXED same session): our NPC casts were OPEN-ONLY.** Retail
  closes every other-agent cast with a 58-led batch (709/709 finished; top
  shapes `['58','55']`, `['58','21','21','55','55']`); our NPC episodes closed
  with NOTHING — 0 finishes, 145 closed only by the next cast opening. The
  client's view of an NPC caster had no cast-end instant. `land_skill` now
  opens its landing batch with `[58, agent, 0]` (test_agentlife pins it).
- **The effect-property channel is absent from our wire**: 6/7/20/21/55/44 all
  zero ours vs 539–916 live. We announce effects only on the dedicated
  0x0042/0x0044 opcodes; retail sends BOTH the opcodes and the property rows,
  and the property rows ride the finish batches. Whether 20/21 drive visuals
  the opcodes don't is an R4 decode question — do not wire blind.
- 46/48/49 (the attack-skill trio + instant family), 22/23/28 (scripted
  animation), 63 (knockdown), 45 — never-sent confirmed in-era (§3/§4/§6).
- Retail re-declares `atkspeed` (0x0035) inside 16 attack-skill open batches;
  we declare it only at spawn. Minor, recorded.
- **Instrument note resolved**: live attack-skill opens carry no `62` token
  because the bench Warrior's attack skills are ADRENAL — spends ride 0x00D2,
  which the extractor does not yet track (future: add 0x00CF/0x00D0/0x00D2 to
  the event model before reading spend grammar off signatures).

## 10. ANIMREF-R4: the corpus-silent behaviours decoded — and why none ships yet

Method: `genericvalue.py` maps each id to its case body, `codescan.py --dis`
reads the handler, and the corpus supplies the value semantics. Pinned build
38797 (`vault/client/2026-07-29_221c13772c7a/Gw.exe`); no client launched. The
result is a **decode-complete, wire-nothing** rung — the disciplined outcome the
plan named ("do not wire blind"): every candidate is either blocked on an
undecoded id space or needs a game mechanic this server does not have.

**Effect-on-agent visual (props 20/21) — DECODED, value UNDERIVABLE, do NOT wire.**
Both case bodies call the same AvApi `0x007DFBF0`: prop 20 pushes `(agent,
target, value)` at `0x00812B6C`, prop 21 pushes `(agent, agent, value)` at
`0x00812B7E` — GWCA's `effect_on_target` / `effect_on_agent`, confirmed at the
instruction (skillcast §15.2). `0x007DFBF0` resolves the agent and calls the
AvChar method `0x007F6F70`, which allocates an **AgentView event of kind 9**
(`push 9; call 0x007F5340`) storing target at +0x1C and value at +0x20 — a
distinct visual event from property 60's cast animation (kind 0x19) and entirely
separate from the `0x0042`/`0x0044` effect-table opcodes that draw the buff-bar
icon. **So retail's on-body effect visual is a real channel our server is
missing** (our `apply_effect` at `authsrv.py:11646` sends only `0x0042`). **But
the value cannot be derived**: the corpus values are NOT the cast skill id —
they are a wide id space (prop 20 top values 344×145, 284×60, 855×28; prop 21
the pair 557/558 ×176 each riding cast 313), which reads as a per-skill
**visual-component id table** (the `s_effect` space `studies/skillcast` §16 and
`studies/anim`'s n3C tags explicitly left unread). Wiring 20/21 means inventing
those ids or decoding that table first. Filed as the arc's next real decode
target; NOT wired.

**Interrupt (D5) and knockdown (D7) — DECODED, no server mechanic to drive them.**
Props 35 and 63 call the same AvChar method `0x007E0490(agent, duration)`, and
the two case bodies differ in exactly one respect — where the float comes from.
Prop 35 (int switch, `0x00812D17`) loads a compiled-in `0.4f` from `0x00948DAC`
(`fld [0x948dac]; fstp [esp]; push edi; call 0x7e0490`) — the interrupt stagger.
Prop 63 (FLOAT switch, `0x00813239`) pushes the wire's own float
(`fld [ebp+0x14]; fstp [esp]; push esi; call 0x7e0490`); the corpus carries
**2.0 s on all three occurrences**, a real knockdown duration where 0.4 s is a
stagger. One animation, two durations, and the value column is the
discriminator — which settles skillcast's CONTESTED 35/63 pairing by mechanism
and supports GWCA's naming (35 `interrupted`, 63 `knocked_down`) over
OpenTyria's undifferentiated `Knockdown1`/`Knockdown2`. An interrupt on the wire is
therefore the measured cancel burst `[8:0, 59, E2]` (R1 §8) **plus** a prop-35
stagger on the interrupted agent. Both are fully decoded and both are unwireable
today for the same reason: this server has **no interrupt mechanic and no
knockdown mechanic** — nothing computes when a cast is interrupted or a body
knocked down, so there is no event to attach the visual to. Decoded and parked;
wiring waits on the mechanic, not on more reading.

**Prop 45 — DECODED as NOT cast-lifecycle.** Case body `0x00812DE5` calls
`0x007E0080`, which resolves the agent and tail-jumps `0x0047F480(this=agent)`
with no value argument — a per-agent trigger of a game-object method well below
the AvApi cast-family range (0x7DFA20–0x7E01B0). Corpus value is 0 on all 79
occurrences (§7), cadence ~1 Hz on PvP casters. It is not a member of the
finished/stopped family despite sitting between their case bodies; its semantics
stay NOT FOUND, but it is now excluded from the cast register rather than an open
question inside it.

**The one derivable near-miss, and why it is R3 not R4: prop 55 (health_gain).**
The R2 diff flagged 55 absent from our wire (861 live / 0 ours). Unlike 20/21 its
value IS derivable — it rides `0x00A3` as a signed fraction of max health, the
same encoding as damage prop 16 (necro capture `[55, 31, 31, f32≈0.18]`), i.e.
the floating heal number. Our heal path sends the health mutation but not the
number. This is a clean, corpus-grounded R3-style diff fix (value known, batch
position known from the `['58','55']` finish signature) — deliberately left for
an R3 follow-up rather than folded into this decode rung, and gated behind R5's
look at whether our heals already read correctly without it.

## 11. The quarterstep regression, reproduced UNATTENDED — and fix 3 is cleared

**2026-08-31.** The R5 operator reported *"i can't quarterstep, attacks block
movement longer than stock"* and then went away, so this was settled by three
scripted harness runs with **no human in the loop and no visual judgement** —
the readout is the CLIENT's own c2s movement messages under a mechanically held
key. That removes the confound that made R5's own capture unable to answer it:
a gap to the next movement message only BOUNDS the block, because it also
contains the operator's reaction time.

Method: `session.py --walk "attack:10 wait:3 1:0.3 W:6"` — order a swing at the
Hatcher, press skill slot 1, then **hold W for six seconds**. The harness's step
clock says when the key went down; the capture says when the client acted. No
aiming is involved: `attack:10` orders the swing programmatically and a skill
slot is a number key, so nothing needs a world-anchored click.

| run | while W was held | client c2s movement msgs |
|---|---|---|
| **auto-attack only** (`--skills 0,0,0,0`) | client moved **0.2 s** after the key went down — the same latency as the no-attack baseline leg in the same session | **9** |
| **attack skill, as shipped** | **nothing, for the whole 6 s** | **1** (the press itself) |
| **attack skill, `--legacy-attack-e5`** | **nothing, for the whole 6 s** | **1** |

**Three results, and the middle one is why the missing flag was worth adding
before anything else:**

1. ~~**The regression is real and reproducible** — 2 of 2 attack-skill runs —
   and it is specific to attack SKILLS.~~ **WITHDRAWN by §11a below: the same
   block appears with a non-attack spell, and the common factor is the
   harness's own input path, not the game.** What survives is the narrower
   fact that a plain auto-attack does not block movement (9 client moves, 0.2 s
   latency) — that run pressed no number key, so it is the one arm the artifact
   does not touch.
2. **ANIMREF-R3 fix 3 is NOT the cause. Measured, not argued.** The block is
   identical with the fix reverted, and the revert demonstrably works (E5/E3
   move from +0.783 s to +0.042 s at the press). The mechanism agrees: fix 3
   moves E5/E3 only, while property 50 and the `0x0035` attack-speed
   declaration — the two things that could drive a client-side animation lock —
   go out at the identical instant in both arms. Without the revert arm this
   change would have stayed the prime suspect on plausibility alone.
3. **Property 8 is cleared too.** The hold is set at the attack-skill press and
   never released, which made it the obvious culprit — but the auto-attack run
   sets the hold at 12.785 and the client moves anyway at 14.540. A flag that is
   set in both runs and blocks in only one is not the blocker. That corroborates
   `action_hold`'s own docstring (skillcast §16.2: animation plumbing, no
   gameplay state) from the wire rather than from the disassembly.

### 11a. The bisect arm ran, and it DISSOLVES result 1 — read this before quoting the table

The named next arm — slot 1 a non-attack SPELL (148) instead of an attack
skill — was run immediately (`20260831T093028`). It blocks **identically**:
the press goes out at 10.777, the cast completes normally (E5 +2.05 s, E3
+2.76 s), and the held W produces **no `MOVE_SET_HEADING` at all**.

So the discriminator is **not** "attack skill". It is not even "skill": the one
run that moved freely is the one run that **pressed no number key**. Every
blocked run pressed `1`. That makes the leading explanation the mundane rival
named above — **the harness's held `W` stops reaching the client after a
number-key press** — an input-path artifact, not a game behaviour.

**Consequences, stated plainly rather than buried:**

* **Result 1 above is WITHDRAWN.** "The regression is real and reproducible,
  and specific to attack skills" is not supported: the same block appears with
  a spell, and the common factor is the instrument. These three runs did not
  reproduce the operator's complaint — they reproduced a property of the
  harness. The operator pressed keys by hand, so this artifact does not
  explain what they felt, and **their report stands unexplained**.
* **Results 2 and 3 SURVIVE**, because both are within-instrument comparisons
  that the artifact affects equally: arm A and arm B pressed the same key the
  same way, so fix 3 is still cleared, and property 8 is still cleared by the
  auto-attack run moving with the hold set.
* **The instrument needs fixing before it is trusted again.** A `--walk` plan
  whose key steps silently stop working after a number key makes every
  subsequent step a false negative, and nothing in the harness reports it. The
  check it lacks: a plan step that produces no client message at all should
  say so, rather than being scored as "held for 6.00035 of 6".

This is the whole reason the arm was run rather than assumed. One more run
would have shipped a wrong cause into the record.

Captures: `20260831T092113` (auto-attack, moved), `20260831T092437` (arm A),
`20260831T092714` (arm B, reverted), `20260831T093028` (spell — the one that
dissolved it).

### 11b. §11a's explanation was ALSO wrong — the player was DEAD, and the real regression reproduces on a living character

**2026-08-31, same day.** §11a blamed the harness input path ("held `W` stops
reaching the client after a number-key press"). The full timeline of the same
captures refutes that too: **the Hatcher had killed the player before the `W`
keydown in every blocked run.** `--enemy-hit` defaults to 0.10, the Hatcher
lands a swing every ~1.37 s starting during map load, and death arrives ~7.5 s
into the plan — between the skill press and the movement leg of every arm that
pressed a skill:

| run | W keydown at | player state at keydown |
|---|---|---|
| `20260831T092113` (auto-attack) | +0.0 / +10.2 | **ALIVE both legs** (run too short to die) — moved |
| `20260831T092437` (arm A) | +8.5 | **DEAD** (died +7.6, revives +17.6) |
| `20260831T092714` (arm B) | +8.5 | **DEAD** (died +7.5, revives +17.5) |
| `20260831T093028` (spell) | +13.2 | **DEAD** (died +7.5, revives +17.6) |

A corpse does not walk. The extractor that "checked" these runs filtered to
movement opcodes and attack labels, so the `0x00F1 KILL the player` rows never
reached the analysis — the safety-filter defect again, the filter deleting
exactly the anomaly. Nothing about movement after a skill press was measured by
those three runs, in either direction.

**Consequences for §11's scoreboard, re-scored:**

* §11a's input-path artifact: **WITHDRAWN**. `1:` and `W:` dispatch to the same
  `hold_key` path, the `1` demonstrably arrived (0x0027 + E4 in both arms), and
  the number key was never the discriminator — death was.
* §11 result 2 (fix 3 cleared): **VOIDED, not restored.** Arm A vs arm B
  compared corpse to corpse, which is vacuous for a movement question. What
  survives of it is only the E5/E3 timing shift itself (+0.783 s → +0.042 s),
  which was measured from the server sends. Fix 3 goes back to UNTESTED as a
  movement-lock suspect — see the living-character run below, which retests
  the shipped arm and reproduces the block, so the A/B rerun is still owed.
* §11 result 3 (property 8 cleared): **SURVIVES** — the auto-attack run had the
  hold set, a living player, and free movement.
* The instrument note stands with a sharper spec: the missing check is not
  "did the step yield messages" but **"was the subject alive, and did the
  client's own reported position move"** — a walking client can legitimately
  send almost no `0x003D` while in combat (the auto-attack W:6 leg traveled
  767 u on one heading message and a stop report), so message counts score
  wrongly in BOTH directions.

**The regression itself: REPRODUCED, on a living character.** Run
`20260831T102623` / capture `20260831T102651`, same shape plus
`--enemy-hit 0.02` (~50 swings to a death — unkillable inside the run), with
in-session controls. Travel is scored from the client's own reported
coordinates, press verified (c2s `0x0027`, E4 for 322), zero deaths:

| leg | keydown (post-press) | travel |
|---|---|---|
| `W:3` baseline (pre-combat) | — | **607 u** @ 202 u/s |
| `W:6` | **+2.1 s** | **0.0 u** in 6 s |
| `W:3` | **+12.5 s** | **618 u** @ 206 u/s |
| `S:2` | +20 s | 372 u @ 186 u/s |

OBSERVED, from the dead window's own traffic:

* The client's input path is fine: at the +2.1 s keydown it **sent**
  `0x003D`, the server answered `attack_stopped: the player moves` +
  `action released` + the `0x0025` direction echo + a zero-lead pin — and the
  client then stood still and went silent for six seconds, stop-reporting its
  **unchanged** coordinates at keyup (server-side drift 767 u = the server
  extrapolated, the client never left). The refusal is the client's.
* The working leg at +12.5 s received the **identical** server response
  (`0x0025` echo + zero-lead, same tags) and walked — so the discriminating
  state is client-side, armed by the skill press.
* The un-arm moment is bounded to **(+8.1 s, +12.5 s)** post-press for a fresh
  keydown — OR earlier with a fresh-keydown requirement: E6 SKILL_RECHARGED
  landed at +3.8 s *inside* the dead hold and movement did not start, so a
  level-triggered unlock before +8 s is excluded.
* **No server message at all arrived between +4.5 s and the keyup** (perf
  pings aside), so whatever un-arms the client is **client-local** (a timer or
  an animation completing), not a message we sent late.

This matches the operator's report in kind — attacks block movement — and
exceeds it in degree (they could move again by re-pressing; a single synthetic
keydown never re-presses, so the harness sees the full lock where a human
feels a delay). Open: what retail sends around a press→move sequence that we
do not (corpus diff), and which client state field roots locomotion (decode).
Instrument runs: `20260831T102623`; analysis in `studies/animref/` history and
the leg scorer (travel + alive per leg) being folded into the harness.

## 12. What R1, R2 and R4 do NOT settle

- The IAS/DAS interaction with the windup law (§1 caveat) — no modified-speed swing
  exists in the corpus. A derivation from the client's `0x007F82C0` duration math
  (`modifier × base`, the 1.25 literal) may settle which term the −0.1 attaches to
  without any run.
- ~~Interrupt wire shape~~ — R4 (§10) decoded the CLIENT half (prop 35's fixed
  0.4 s stagger, `0x007E0490`); what is still open is the SERVER half, which is
  a missing mechanic (nothing computes an interrupt) rather than a reading.
  E7/E8 remain unexamined.
- **Props 20/21's VALUE space** — §10 decoded the mechanism (AgentView event
  kind 9) and refuted the obvious reading (the value is not the cast skill id);
  the wide id space it does use (557/558 on cast 313, 344, 284, 855…) is the
  per-skill visual-component table `studies/skillcast` §16 and `studies/anim`'s
  n3C tags both leave unread. **That table is the arc's next decode target** —
  and until it is read, 20/21 cannot be wired without inventing ids.
- Prop 22/23/28 payload semantics (§6): §10 did not read these; skillcast §15.2
  already has the sticky-parameter mechanism (23–27 store to +0x550..+0x560,
  22 and 28 consume and clear), so what is missing is again the id space.
- Prop 45 (§7): §10 excluded it from the cast register (it tail-jumps
  `0x0047F480`, agent-only, value discarded) — its own semantics stay NOT FOUND.
- The projectile-flight join for bow attack skills (§3) — needs a projectile-events
  extractor pass, desk-only. Add 0x00CF/0x00D0/0x00D2 to the event model first
  (§9's adrenal note).
- The tick tail (D18, §9) — landing precision is bounded by the 20 Hz world
  tick; fixing it means sub-tick scheduling, a server-architecture question.
- ~~Whether our own wire matches ANY of this~~ — R2 ran (§9): self grammar
  matches signature-for-signature; the divergence rows are D15 (fixed), D18
  (recorded), D19 (fixed), and the effect-property channel (open).

## 13. ANIMREF-R6: the execution batch, derived — and the movement lock it explains

**2026-08-31, from §11b's reproduction.** The client-side movement root was
chased into the corpus rather than tuned around, per the arc's method:

**Retail's law (OBSERVED).** Across the live corpus, every ACCEPTED attack-skill
press was aligned to its E4 on the s2c clock (per-connection offset from the
press↔E4 histogram, 42-anchor refinement, consistent to ±3 ms) and scored for
the gap to the player's next c2s movement message. n=53 accepted presses with a
later move: the 8 sub-second cases all put the first move **within ±0.25 s of
E3** (E3→move −0.147/+0.071/+0.249/+0.237/−0.087/+0.171 s…) — the root opens at
the strike's execution, not at the press and not an aftercast later. The two
small negatives say the client's un-root is its own animation clock, with E3 in
flight. (First pass without E4 validation was WRONG and is kept as a lesson:
its fastest "quarterstep", 0.568 s, was a press retail **refused** — no E4 —
including a targetless press, which is D20 observed live. 41 refused presses in
the corpus.)

**Our divergence (OBSERVED, run `20260831T102651`).** Our client's W keydown at
E3+1.26 s moved 0.0 u for six seconds; a fresh keydown at press+12.5 s walked at
full rate; no server message arrived in between — the un-arm is client-local.
The client's input path is fine (it sent its 0x3D; the server's reply is
byte-identical in the dead and the working windows). The state that roots it is
armed by the press and never disarmed by us.

**The missing disarm, from the corpus (§3 + a 40/40 batch census).** Retail's
attack-skill execution batch: `0x009F [46, agent, 0]` OPENS it — INT form,
value 0, 40 of 40 self episodes across 60 connections — then the 0x00CF
adrenaline strike, the damage (16, or 17 on a critical), the victim's health
bookkeeping, then E3. **No attack_started, no melee_attack_finished**: the
skill replaces the swing its windup announced. Our server: never sent 46
(defined-unsent since castmech's bow artifact, §3), and delivered the damage
through the interval-gated ordinary swing path — so a press mid-chain dealt
**no skill damage at all** (hit_enemy's gate returned before its first send),
and when the gate allowed, a second phantom swing opened.

**Shipped (ANIMREF-R6, default ON, revert `--legacy-attack-finish`):** at the
attack cast's E5 instant the server now sends `[46, PLAYER, 0]` first —
unconditionally for attack casts, whiff included (it closes the player's
ACTION, not the hit; the whiff case is RECONSTRUCTION, every corpus 46 rides a
hit) — then the strike via `hit_enemy(skill_strike=True)`: full weapon terms
(roll, armour, critical, adrenaline, preparation), no swing brackets, no
interval gate, timer still consumed so the chain's next swing paces one
interval later, where the corpus puts it. `test_castcycle` §2b/§2c pin both
arms, legacy defect included; `land_skill`'s 58-first batch was reconciled
with the guard contract in the same change (fraction computed before the
first send, 58 still leading — test_guards §4).

**The verbatim check ran (`20260831T105013`/`105042`) and REFUTED "46 is the
whole disarm" — while confirming it is half of it.** The same protocol,
fix ON: W:6 at press+2.1 s traveled **49.2 u** — from the keydown to
**exactly** the client's next-swing instant (execution 14.75 + the 1.75
interval = 16.50, to the centisecond) — where the pre-fix leg traveled 0.0 u
ever. So 46 closed the skill state and the client resumed its AUTO-ATTACK
CHAIN; what roots it now is the chain: the between-swings quarterstep window
exists, and the swing instant consumes the held key. Consistently, `S:2`
(backing out of melee) traveled at full rate while the second `W:3` froze —
the client was chaining at a target our server had *stopped serving* (we
declared `attack_stopped: the player moves` at the first 0x3D and killed our
loop; the client kept its schedule). The remaining divergence was therefore
the CHAIN's behaviour around movement — §14.

## 14. ANIMREF-R7: the two chain laws around movement — the old door was one witness counted twice

**2026-08-31, from §13's verbatim refutation.** The re-rooting agent is the
auto-attack chain, so the chain's own grammar was put against the corpus.
Both laws OBSERVED, live corpus only:

**LAW A — movement does not close the chain.** Of 100 player movement
messages sent within 2 s of the player's own `attack_started`, **87 carry no
prop-3 within 0.5 s** (the entire corpus holds just 28 self prop-3s; the 13
that do ride a move are the genuine closes). Our movement door sent
`[3, agent, 0]` and forgot the target on **every** move — a rule built from
the wiki's sentence ("moving cancels auto-attacking") plus a 2-of-2 measured
on **our own** door (capture `20260824T074002` is ours-origin), one witness
counted twice. The retail quarterstep rides the chain and the chain survives
it.

**LAW B — the post-execution restart is paced.** The gap from a self prop-46
to the player's next `attack_started`: n=38, with a tight modal cluster at
**0.749–0.783 s** (21/38) against `swing_windup(1.75) = 0.775` — one weapon
windup, never the same instant. The tail (0.94–5.5 s) is the players who
stepped or paused. Our server reopened the chain in the execution tick.

**Built — and then the verbatim check REVERSED R7a's default.**

* **R7b (`--legacy-chain-restart`, default ON):** after an attack skill's
  execution the swing clock is stamped `exec + windup − interval`, so the
  START-to-START gate opens exactly one windup out (LAW B), instead of the
  same tick. Shipped.
* **R7a (`--move-keeps-chain`, default OFF):** LAW A's wire — no prop-3 on
  movement, target and armed swing survive, `attack_tick`'s range gate the
  deferred judge; cast half and the movement prop-8 release untouched. The
  tap-train verbatim check (`20260831T110116`/`110144`) ran it default-ON
  and **every movement key died**: three `W:0.4` taps (one squarely in the
  backswing window) and a held `W:6` all traveled **0.0 u** while `S:2`
  walked 375 u — strictly worse than R6-alone, whose first W moved 49 u the
  instant our prop-3 went out. Across all four instrumented runs one client
  model survives: **the client cannot START movement while its attack
  action is open, and the prop-3 LAW A removes is the only closer we send.**
  Retail's client moves without that prop-3 (87/100). This paragraph first
  guessed retail sends "a grant we have not identified" (candidate `0x002B`
  and friends) — **§15 decoded it and REFUTED that guess: there is no such
  grant.** Retail sends no return-to-movable property after a skill; its
  CLIENT is movable in the skill-finished animation state where ours is not.
  Shipping LAW A without a client-side complement is "more retail-correct
  wire, visibly worse game" — R5's P1 lesson — so the wire fact is
  recorded, the flag exists, and the default keeps the door that moves.

Pins: `test_castcancel` §5 (default door + the opt-in arm, with the
measured reason in the check text), `test_castcycle` §2c (the restart
pacing rides the batch pin).

**The shipped default's own verbatim row (`20260831T110714`/`110743` — R6
ON, R7b ON, R7a off).** Same protocol, zero deaths, press verified:
baseline `W:3` 614 u @ 205 u/s; **tap at press+2.1 s: 19 u (moves — was
0.0 u before R6)**; **tap at press+4.2 s: 79 u @ 196 u/s — full stride**;
**held `W:6` at press+9 s: 1248 u @ 208 u/s for the entire hold** (was
0.0 u); `S:2` 376 u. The operator's regression — every movement key dead
after an attack-skill press — is resolved in the shipped configuration.
The remaining gap to retail is the first tap's partial rate (the client
engages partway through it, on our prop-3 close, where retail's client
moves under its own control within ±0.25 s of E3 with the chain
surviving) — that is the movement-start-gate decode, §14's named target.

## 15. The movement gate is a CLIENT animation state — decoded, and it dissolves §14's "grant" guess

**2026-08-31, static read of the pinned client (38797) + a corpus scan; no
launch.** §14 left the movement-start gate as the arc's sharpest target and
guessed retail feeds an unidentified wire grant. Both halves resolved:

**The generic-property switch dispatches each animation property into one
call, `0x7F2E90(agent, N)`, that enqueues a per-agent animation-state node**
(a linked-list splice at `[agent+0xC4]`, node = `{state N, [agent+0x2c],
timestamp}`). The state code per property, read from the case bodies:

| prop | GWCA name | AvChar body | state N | global `0x10874AC/B0` |
|---|---|---|---|---|
| 1 | melee_finished | `0x7F6BC0` | **0** | set AC=0, B0=agent |
| 3 | attack_stopped | `0x7F6C00` | **2** | — |
| 4 | attack_started | `0x7F6C10` | **3** | clear (B0=0, A8=0) |
| 46 | attack_skill_finished | `0x7F74F0` | **0x11** | set AC=0x11, B0=agent |
| 49 | attack_skill_stopped | `0x7F7510` | **0x12** | set AC=0x12, B0=agent |
| 50 | attack_skill_activated | `0x7F7540` | **0x15** | clear |

The FINISHED family (1/46/49) writes the global latch `0x10874AC` (the local
player's standalone-animation slot); the STARTED family (4/50) clears it.
Prop 8 (`disabled`) has **no case body in this switch** — it is the separate
input-block flag, handled elsewhere, and its release (`[8→0]`) goes out on
movement in both arms, so it is NOT the differentiator.

**Empirically (the two verbatim captures, §14): our client becomes movable
after a lone `0x003D` only when it also received prop 3 (state 2).** Frozen
arm — `0x003D` + prop-8-release, no prop-3 → 0.0 u; moving arm — `0x003D` +
**prop-3** + prop-8-release → walks. State 2 (and states 0/3, the ordinary
auto-attack cycle, which move freely) are movable; the attack-SKILL states
0x15/0x11 are not, **on our client**.

**The corpus scan that kills the "grant" guess (`after46.py`, 40 self
prop-46 events):** the next self animation-state property after a skill's
execution is **prop 4 — the next auto-attack START (state 3) — 27 of 40**,
prop 50 (another skill) 6, nothing-within-3 s 7. **A self prop-1 or prop-3
appears zero times as the successor.** So retail sends NO return-to-movable
property after a skill; the sequence is `46(s11) → 4(s3) → 1(s0) → 4 → 1…`,
the chain simply resuming ~0.775 s later (LAW B). Retail's 87/100
moves-without-prop-3 are the player moving *while the client sits in s11 or
s3* — i.e. **retail's client is movable in the skill-finished state, and
ours is not.** This is a client animation-state-machine difference, not a
missing wire message.

**Consequence for the arc.** There is no server-only wire change that makes
LAW A's door (no prop-3) move our client — the block is that our client's
locomotion input is gated on an animation state our attack-skill sequence
leaves at 0x11/0x15, and only prop 3 (state 2) clears it for us. **The
shipped default — send prop-3 on movement — is therefore not a stopgap but
the correct pragmatic resolution given this client:** it forces state 2, the
one our client treats as movable, and the verbatim row (§14) shows it
restores the quarterstep. `--move-keeps-chain` stays as the recorded wire of
LAW A for a future study that instruments the client's locomotion-input read
directly (the open question narrows to: *which* field the local 0x003D path
tests, and why s11 passes it on retail but not on our build — a client
behaviour, possibly build-specific, not addressable from the server). The
per-agent state node (`0x7F2E90`, field `[agent+0xC4]`) and the global latch
`0x10874AC/B0` are the two concrete read targets for that dig.

## 16. ANIMREF-R8: the visual-component id space, READ — and the 20/21 channel wired

**2026-08-31.** §10 decoded properties 20/21's mechanism, refuted the obvious
value reading, and refused to wire the channel because the id space was
unread — "wiring 20/21 means inventing those ids or decoding that table
first," filed as the arc's next decode target. It is decoded. Nothing was
invented.

**Step 1 — the corpus says the value IS per-skill, and fixes a slot reading
on the way.** Each prop-20/21 event was attributed to the cast that produced
it (batch-tight: the event must share the cast-end batch of a caster whose
cast-open named the skill). Prop 20 is `INT_TARGET`, so which of its two
agent slots is the caster was an open question — §10 read it as
`(agent, target, value)`. Scored both ways:

| reading | attributed | skills | purity |
|---|---|---|---|
| A — `v[2]` is the caster | **0** | — | nothing attributes at all |
| B — `v[3]` is the caster | 156 | 13 | **100%**: every skill one value, every value one skill |

So **prop 20 is `[prop, RECIPIENT, CASTER, id]` — victim slot first**, the
same order `0x00A3` damage uses and the opposite of §10's reading. Prop 21
(`INT`, one agent) gave 17 skills, 16 with a ≥90% dominant value.

**Step 2 — the ids are in the client's own skill record.** 26 measured
(skill → id) pairs were tested against every offset of the `s_skill` record
(0xA4 bytes, `skilltable.py`) as u32/u16/u8. Two offsets answer, and **2077
is the table's own "no visual" default** (2567 of 3443 rows at +0x7c):

* **+0x78 — a visual played on the CASTER**
* **+0x7c — a visual played on the RECIPIENT**

Skill 179 is the clean case: `+0x78 = 347`, exactly the id the corpus saw on
the caster; `+0x7c = 348`, exactly the one on the recipient. **25 of 26
skills have all their observed ids inside {+0x78, +0x7c}.**

**Step 3 — the model predicts the CHANNEL too, which is what makes it
refutable.** The caster visual rides prop 21; the recipient visual rides
prop 20 when the recipient is somebody else and prop 21 when the skill is
self-cast — which is why one id shows on both channels for a heal aimed
sometimes at an ally, sometimes at yourself (281/282/288 do exactly that).
Scored over the whole corpus, predicting field **and** channel:
**656 of 658 attributable events, 99.7%.** Both misses are single events
(skill 83 n=1; a stray value 11 on skill 282) whose cast attribution is
itself unsafe — named, not smoothed away.

**Shipped (ANIMREF-R8, default ON, revert `--no-skill-visuals`).**
`skilltable.py` now emits `visual_caster`/`visual_recipient`;
`content/world.toml` gains a `skill_visual` block — 12 rows, one per served
skill that has a visual, each `source = "client-table"` with its extractor,
build 38797, and the corpus corroboration in `verified`; `send_skill_visual`
sends them at the cast's landing in the corpus's own batch slot (behind the
58, ahead of the target-facing properties — retail's `['58','21','21','55',
'55']` shape), for the player's casts and the NPC's alike. A skill whose row
omits a slot, or that has no row, **sends nothing** — silence rather than a
substitute id, which is the condition §10's refusal named.

Pins: `test_castcycle` §2d (all four channel branches + the off switch),
`test_guards` §4 (the NPC half, byte-exact: skill 312's `[20, player, 10,
556]` between the 58 and the damage), `test_skilltable` (46 checks green with
the two new fields).

**Verbatim check (`20260831T120723`/`120752`).** A real client took the new
channel without complaint: **0 undecodable, RUN VERDICT PASS, no assert and
no disconnect** across four NPC casts that each fired their own id — 253→464,
289→511, 276→491, 312→556 — in retail's batch order every time
(`58 finishes casting` → `effect visual … the target of skill …` →
`EFFECT_APPLY`/heal/damage). The player's own attack skill 322, whose client
row is all sentinel, correctly sent **nothing**. What the run does NOT show
is what the visuals look like on screen: that is a model-appearance verdict
and belongs to the owner, so the ids remain OBSERVED-as-wire and unclaimed
as pixels.

**What this does NOT settle.** The ids are carried **opaque** — nothing here
reads the visual-component space they index, so what any given id *looks
like* is unknown and unclaimed. The 8 served skills whose rows are all
sentinel play nothing, which is a fact about those skills rather than a gap.
And prop 21's dominant-value purity (16/17) is one skill short of the prop-20
figure; the residue is the same single stray event.

## 17. The IAS windup question CANNOT be settled desk-only — the queue item is refuted, not deferred

**2026-08-31.** `PLAN.md` §8 carried this as a decode that "may fall to the
client's `0x007F82C0` duration math, desk-only." It does not, and the two
halves of the reason are each worth having.

**The client's attack-duration math, decoded (pinned 38797, no launch).**
`0x007F82C0` asserts both operands non-zero (assert ids `0x12b7`, `0x12b8`),
then computes

> `duration = base[+0xEC] × modifier[+0xF0]`, and **× 1.25** when the
> caller's context field `[ctx+0x3c]` is non-zero (a `double` at
> `0x00950990`, read: exactly 1.25)

selects a per-weapon animation code (0x0C–0x15, with 0x29–0x2B on the
`[ctx+0x3c]`/`[ctx+0x38]` branches) and hands the float to the animation
player `0x007F3DA0`. The two fields are stored straight off the wire's
`0x0035` (`0x007FBD85`: `fld [ebp+8]; fstp [+0xEC]; fstp [+0xF0]`).
**There is no additive term anywhere in it.** The client's arithmetic is
purely multiplicative, so the −0.1 s of §1's law is not the client's
animation math — it is ArenaNet's server-side scheduling, which this binary
cannot show us. What `[ctx+0x3c]` means is NOT established; note only that
the corpus's one cross-family datum shows the 1.25 did **not** apply to
Power Shot (measured 1.1374/1.1387 against the law's 1.1375).

**And the corpus has ZERO exposure, verified rather than inherited.** §1's
caveat said every corpus swing rides modifier 1.0; re-scanned directly:
**62 `0x0035` declarations, all modifier 1.0** — bases 1.75 (×27), 1.33
(×23), 2.475 (×7), 2.0 (×3), 3.0 (×2) — and **0 landed swings at modifier
≠ 1.0**. That is zero trials, not a null result: nothing in the corpus
discriminates `m×base/2 − 0.1` from `m×(base/2 − 0.1)` from
`(m×base − 0.2)/2`, and no amount of re-reading it will.

**So the item leaves the desk queue as REFUTED-BY-METHOD.** What would
settle it is exposure, not analysis: a live capture with an attack-speed
stance actually running (Frenzy, Flurry, Tiger Stance) on the secondary
account — one line in an R0b runsheet, human-driven, and the first swing
under a modifier decides it. Until then, **note what we ship**: our server
scales the interval and then applies the law — `swing_windup(ATTACK_INTERVAL
× attack_interval_factor(...))`, i.e. candidate **A** (`m×base/2 − 0.1`) —
and that choice is UNVERIFIED, inherited from the code's shape rather than
measured. It is named here so it is visible rather than implied.

## Provenance

All figures are measurements over the owner's own live captures via extractors in this
repo (`animgrammar.py`, this arc; `tape.py`/`codec.py`, prior arcs) and static reads of
the pinned pristine client via `genericvalue.py`/`codescan.py` (carve-out 1, read-only,
no launch); scratch probes and the referent JSONL are under `vault/research/animref/`.
No asset bytes, no client launch, no upstream derivation — no §6.1 register row required.
§13–15's corpus scans (`pressmove2`, `batch46`, `chainmove`, `after46`) are session
scratch over the same tapes; their laws and n's are restated in full above. §15's
addresses are single-site measurements (one case body, one AvChar method each), the
MEASUREMENT side of the provenance boundary — the extractor is `codescan.py`, the build
is named, the values audit without the binary.
