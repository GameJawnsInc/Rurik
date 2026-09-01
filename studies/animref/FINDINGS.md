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

## 18. Prop 55 is already wired, and the corpus's "double 55" is two gains, not a shape we lack

**2026-08-31.** `PLAN.md` carried "prop 55 (health_gain) is the one R2
divergence whose value IS derivable — a clean R3-style fix" as the next
shippable item. **It is stale: `heal_agent` has sent property 55 on
`0x00A3` as a signed fraction of maximum health since the heal path
existed** (`authsrv.py`, `GV_HEALTH_GAIN`), and the R8 verbatim run shows it
on the wire (`heal 22 on agent 10`). R2's "effect-property channel absent"
line covered 6/7/20/21/55/44 as a group; 55 was the member already present,
and nobody re-checked before queueing it.

What the re-check did turn up is the batch shape. Census over the corpus:
**861 prop-55 events; of 637 (batch, agent) groups, 413 carry one and 224
carry TWO** — always the same source agent, always different values, mostly
in a cast-finish batch (prop-set `(21, 55, 58)` ×191, `(20, 55, 58)` ×17).

That looked like a shape we lack, and it is not, on the corpus's own
evidence: the ordering is mixed (176 first-smaller, 48 first-larger, so not
`(gain, running total)`), there are only 12 distinct value pairs, and **one
value recurs as the second member across four different first members**
(0.0757 pairs with 0.1135, 0.3441, 0.2901, 0.1568). A constant alongside a
varying partner reads as **two independent health gains resolving in one
instant** — one per gain, which is exactly the rule our server already
follows; we would send two the same way if two heals landed in one tick.

**So: no fix, and no divergence row.** Stated as the weaker claim it is —
the two-gains reading explains the pairs and no rival survives the ordering
and the recurring constant, but the skills behind them were not identified,
so it is RECONSTRUCTION, not OBSERVED. What would settle it is attributing
each 55 to its own cast, which needs the per-skill heal magnitudes the
`skill_effect` table only covers for our 20 served skills.

## 19. D20 tested: the premise is REFUTED, the fix is not shipped, and the refusals are a charge gate

**2026-08-31.** §2 recorded D20 — "retail's client does not produce an
attack-skill press without a target" — and filed the honest fix as *refuse a
targetless attack-skill press*, unwired because our harness's own presses use
target 0. Tested before building, and the premise does not survive.

Every c2s `0x0027`/`0x0046` in the corpus, scored for whether the server
answered with an E4 for that skill on the player's own agent (clocks aligned
per connection, as §13):

| | accepted | REFUSED |
|---|---|---|
| `0x0027` attack-skill, target ≠ 0 | 51 | **42** |
| `0x0027` attack-skill, target = 0 | 0 | **1** |
| `0x0046` use-skill, target ≠ 0 | 16 | 0 |
| `0x0046` use-skill, target = 0 | **36** | 0 |

**Three results, and the first two pull in opposite directions:**

1. **The premise is REFUTED, n=1.** Retail's client *does* send a targetless
   attack-skill press — `20260819T132414` t=238.50, skill 780,
   `[…, 780, 0, 0, 0]`. §2's claim was made from an absence in a smaller
   scan; one counterexample is enough to retire it.
2. **The conclusion survives, also n=1**: that press was refused. So
   "targetless attack-skill press → refused" is 1 for 1 — and one witness is
   not a law. Non-attack skills are freely targetless (36 of 36 accepted), so
   whatever the rule is, it is attack-specific.
3. **Targetlessness is NOT what the server refuses.** 42 of the 43 refusals
   carry a real target. The refusal population is a different mechanism
   entirely, and D20 would explain 1 case of it.

**What the refusals actually are.** They concentrate in exactly four skills —
382 (22 accepted / 20 refused), 384 (14/13), 385 (8/8), 780 (3/2) — and
**every other skill in the corpus has zero refusals** (364: 27/0, 105: 7/0,
1: 6/0, 858: 6/0, …). The same skill is sometimes accepted and sometimes
refused, so the discriminator is *state*, not the skill or the targeting: a
per-skill **charge gate**, which is the adrenaline mechanic this server
already implements (`refuse_press`, `REFUSE_NOT_ENOUGH_ADRENALINE`).

The direction of the evidence agrees — summing the player's own `0x00CF`
adrenaline gains between the previous accepted press of a skill and this one,
accepted presses follow **median 206 units** against refused **137.5**, and
only 2 of 33 accepted presses follow under 100 units against 6 of 28 refused.
But the distributions **overlap and there is no threshold**, so this stays
RECONSTRUCTION. The overlap is expected rather than embarrassing: in Guild
Wars *any* adrenal use drains **every** adrenaline bar, so "units since the
last press of this skill" is the wrong denominator — the right one needs a
per-bar simulation with cross-drain, which is what would upgrade this.

**Decision: the fix is NOT shipped, and the item leaves the queue.** Refusing
targetless attack-skill presses would rest on a single witness, would cost us
our own harness presses, and would address 1 of 43 refusals. Recording that
is the whole return here — the item's premise was wrong, and building it
first would have hidden that.

## 20. Props 22/23/28 are NOT a per-skill id space — R8's method does not port

**2026-08-31.** The queue carried these as "the id-space method may port,
but test per-skill-ness first, do not assume R8's success." Tested; it does
not port, and the reason is structural rather than a shortage of data.

**They are not cast-driven.** Attributing each event to a cast the way §16
did: **59 of 60 prop-22 events, 17 of 17 prop-23 and 17 of 17 prop-28 have
no cast-open by the same agent within 6 s.** Property 20/21's whole method
rests on that attribution, so there is nothing for it to bite on here. All
three ride the untargeted `0x009F` channel exclusively (0 targeted, against
prop 20's targeted-only form).

**23 and 28 are a PAIR, and 23 is the parameter.** Every prop-23 event
shares its batch and its agent with a prop-28: `23 → 8` (15 of 17; the other
two are 10) immediately followed by `28 → 831757499`. That is exactly
skillcast §15.2's sticky-parameter mechanism seen from the wire — 23 sets a
small parameter, 28 consumes it — and it is the first corpus confirmation of
that reading.

**The values are 32-bit resource ids, shared across agents.** Prop 22: 60
events, 16 distinct values, all large and unstructured (809791073,
3200618694, 1470797158 — neither small ids nor sensible floats). Prop 28: 3
distinct values over 17 events, and **the same id 831757499 goes to agents
63, 550, 302 and 658** in one capture. A per-skill table cannot be behind
that: the id is neither per-agent nor per-cast, and reads as a handle into an
animation-resource space.

**So: no fix, and the item leaves the queue.** Wiring 22/28 would mean
inventing 32-bit resource handles — the same refusal condition §10 named for
20/21, except that this time there is no `s_skill` field to read them out of,
because the channel is not keyed by skill at all. What it would take is
identifying the resource space those handles index, which is `Gw.dat`
territory and a different arc's question, not a value we can derive.

## 21. ANIMREF-RE step 1+2: the walk entries are GATED, and the gate pair is named

**All OBSERVED on the pinned build 38797, static, no launch.** `RE-PLAN.md` asked
for the client's local movement application and what it tests. Both walk entries
were found and decoded, and the answer is **not** the animation-state queue §15
pointed at — it is a pair of flags on the player's own char object.

### 21.1 Both walk entries refuse before they ever path

`chcli_dir 0x0081A8F0` (keyboard, `ecx = this = the char`) tests three predicates
in its first 30 bytes, all before the path query at `0x0081A96C`:

| VA | instruction | refuses when |
|---|---|---|
| `0x0081A931` | `test eax, 0x100` on `[this+0x10c]` | **m_status bit 8 SET** |
| `0x0081A93C` | `test byte [ebx+0x64], 1` | **`+0x64` bit 0 SET** |
| `0x0081A94B` | `shr 4 / not / test al,1` on `[this+0x10c]` | **m_status bit 4 SET** |

`chcli_point 0x0081ADB0` (click) tests **the same pair** thirty bytes apart —
`0x0081AEE4 test dword [esi+0x10c], 0x100` and `0x0081AEF4 test byte [esi+0x64], 1`
— and its caller `0x00816522` re-tests bit 4 in the identical
`shr 4 / not / test al,1` idiom before it even calls in. **Two independent entry
points, one gate pair.** That is the structural reason it presents as "the body
will not translate" rather than as a pathing failure: the walk never starts.

### 21.2 What the refusal DOES — it is not a silent return

All three keyboard gates jump to `0x0081AD0F`, which:

* `push [ebx+0x14]` (the agent id) → `call 0x005FCA80` → resolves
  `context->[+8]`, adds **`0x1CC` — the AgTrack manager** (MOVECODE's decode) —
  and calls `0x00605F70(agentId)`;
* `0x00605F70` bounds-checks against `[mgr+0x28]`, indexes `[mgr+0x20]` at
  `ecx = id*8 - id` scaled by 4 = **stride 0x1C, MOVECODE's state record exactly**,
  and zeroes `[record+0x00]` (**`clientControlled`**) and `[record+0x04]` (the
  history head);
* writes a facing vector to `[esi+0x694/+0x698]`, zeroes `[esi+0x69c/+0x6a0]`;
* and **returns `eax = 1` — success.**

**CORRECTION (§22's verify pass):** `esi` there is `[ctx+0x2c]` (`0x0081A922`), **not**
the context and not `playerControlledChar`. The correct spelling of the player is
`[[ctx+0x2c]+0x680]`, which `0x0081AD1A cmp ebx, [esi+0x680]` proves. Sampling
`+0x694` off `ChCliBase` would read a different struct.

So a refused walk **turns the character, relinquishes local movement authority,
and reports that it handled the input.** `ChCliBase:164
"this == context->playerControlledChar"` sits on that path at `0x0081AD27`, which
is what identifies `ebx` as the local player and `esi` as the context.

This closes a loop with the sister arc: MOVECODE §1z-c.2 measured a frozen client
with **`clientControlled` shut on 110 of 110 reads** against 804 open / 11 shut
healthy, and called it "the cleanest client-side discriminator the arc has."
**`0x00605F70` is a mechanism that shuts it, reached from a refused walk.**

### 21.3 `m_status` is at `char+0x10c`, and it is SERVER-DRIVEN ONLY

`0x00815830` is `ChCliInt:254 IS_TRUE(m_status & CHAR_STATUS_DEAD)`, guarded by
`0x00815822 test byte [edi+0x10c], 0x10` — so **`m_status` is the dword at
`+0x10c` and `CHAR_STATUS_DEAD = 0x10`**. (This half **replicates** rather than
discovers: `schema/overrides.json:2145` already reached the same identification
from the same assert. Recording it because the *gating* below is new and rests
on it.)

The runtime writer is `ChCliBase::SetStatus 0x0081C020`, and its shape matters:

```
eax = [this+0x10c] ^ newStatus        ; CHANGED
test al,0x10 / test bl,0x10           ; became DEAD -> 0x005FC5C0(id,0) + zero speed 0x0081BE90
eax = CHANGED & newStatus             ; bits that turned ON
bt  eax, 8   -> 0x0081C069            ; bit 8 0->1 -> 0x005FC5C0(id, 0)   <-- SAME halt as death
mov [this+0x10c], ebx                 ; commit
```

**Bit 8 turning on halts the agent through the identical AgApi call the client
uses for death** (`0x005FC5C0`, which bumps the version hash at `[mgr+0xC8]` and
indexes the async array `[mgr+0x14C]`). Then both walk entries refuse. That is a
complete, coherent "movement disabled" mechanism.

**And `m_status` has exactly three stores on the char object image-wide** —
`0x0081A551` (clear), `0x0081A609` (construction, seeded from a template row at
stride 0x34 field +0x30), `0x0081C076` (`SetStatus` commit) — with `SetStatus`
called from exactly two sites, `0x00814CAE` and `0x00814D3E`, both message
handlers. **Read off the dispatch table (`{fieldsPtr, count, handler}`, stride 12,
slots `0x00BC9844`/`0x00BC9850`), those are opcodes `0x00F0` and `0x00F1`.**
*Positive control:* the 305-row `--field 0x10c` census contains `chcli_dir`'s own
read `0x0081A925` and the click path's `0x0081AEE4`, so its silence elsewhere is
informative. Subject to the standing `--field` floor (a displacement in a
register, a two-step address, or a biased `this` are all invisible).

**Therefore the client cannot set `m_status` bit 8 on its own initiative.**

### 21.4 What this ELIMINATES, and what it leaves

Our server sends `0x00F1` with only `agents.EFFECT_DEAD` (`0x10`) or `0`
(`authsrv.py:10038, 12127, 12635, 13630, 13982, 13988`) and `0x00F0` with the
content row's `effects`, `0` for the player (`13881`, `18581`). **So we never set
bit 8**, and bit 4 only on a real kill.

* **Gate A (m_status bit 8) is NOT what freezes our player** — RECONSTRUCTION,
  resting on 21.3's writer census and our own send sites.
* **Gate C (m_status bit 4, DEAD) is not it either** while the player lives —
  though note it *was* the whole of the `--walk` "number-key trap"
  ([[rurik-harness-walk-numberkey-trap]]), so it must stay on the checklist for
  any scripted arm.
* **Gate B — `[char+0x64] bit 0` — is the surviving candidate**, and `+0x64` is a
  real flags word on the char (bit 1 set at `0x0081B2D6`/`0x0081B85C`, bit 3
  tested at `0x0081B45F`, bit 5 at `0x0081796D`, a computed `or` at `0x0081B38E`
  that sets bits 3–6 and provably **not** bit 0). ~~**NOT FOUND: any writer of bit
  0**~~ — **CLOSED by §22: `0x0081BD02` sets it and `0x0081BD14` clears it, both
  in property 8's case body.** The search that missed them was bounded
  `--in ChCliBase`, whose assert-derived range `0x0081AC3D..0x0081BA94` excludes
  **both** the gate read at `0x0081A93C` and the gate write at `0x0081BD02`. A
  module-bounded census can truncate at both ends and still read as a clean zero;
  this one did.
* **A fourth exit exists and is not a gate at all:** a path query returning zero
  waypoints leaves via `0x0081A987 je 0x0081ACFA`, a *different* address from the
  gate exit `0x0081AD0F`. That is MOVECODE §1z-c.2's plane-desync freeze class.
  Any dynamic run must distinguish the two exits, or it will confuse our freeze
  with theirs.

### 21.5 The dynamic step, with its prediction registered first

The static work has narrowed four candidate exits to one instrument read, and
this is where `RE-PLAN.md` step 3 now points. **Hook `chcli_dir 0x0081A8F0` at
entry** (`movehook` already taps function entries; `ecx` is `this`, no chasing
required) and record, per call: `[this+0x10c]`, `[this+0x64]`, and **which exit
the call takes** — `0x0081AD0F` (gated), `0x0081ACFA` (no path), or through to
`agapi_setdest`.

**Prediction, registered before the run:** in the frozen arm `chcli_dir` is
entered and leaves via `0x0081AD0F` with `[this+0x64] & 1` set and
`[this+0x10c] & 0x110` clear; in the moving arm the same call reaches the path
query. **Refuted if:** it leaves via `0x0081ACFA` (then our freeze is the
plane-desync class and this whole section is the wrong tree), or if it reaches
`agapi_setdest` in both arms (then the gate is downstream of the walk entry and
21.1's pair is a red herring), or if `+0x64` reads identically in both arms.

**No quarterstep verdict is available from this run** — it records which branch
the client took, which is a fact about the code path and not about feel
([[quarterstep-is-a-feel-thing]]).

## 22. ANIMREF-RE step 2 concluded: GATE B's writer is PROPERTY 8 — and §15 is REFUTED

A nine-agent static fan-out (four recon lanes, four adversarial skeptics, one
synthesis) closed §21.4's open question and killed the arc's standing mechanism.
**Every load-bearing claim below was re-derived by hand before being written
here**, because it corrects prior published work — including §21's own.

### 22.1 The writer, and the switch that reaches it

`ChCliApi::SetAgentProperty 0x008128F0` fans one property id into **two**
consumers: the AvChar animation dispatcher (`0x00812A0D call 0x007DFA00`, §15's
territory) **and** a separate `ChCliBase` switch at `0x0081BC60` — the object that
owns the walk gate.

```
0081BC69  add eax, -4
0081BC6F  cmp eax, 0x38 / ja 0x0081BD29        ; props 0..3 -> default
0081BC78  movzx eax, byte [eax + 0x0081BD44]   ; index table
0081BC7F  jmp dword [eax*4 + 0x0081BD30]       ; jump table
```

Both tables read from the image (`scratchpad/sw2.py`, a 30-line PE walk carrying a
byte-level control: the bytes at `0x0081BCF0` and `0x0081BD02` must equal
`837d1000` and `894664`, and do):

| prop | case body | effect |
|---|---|---|
| 4 attack_started, 50 attack_skill_activated | `0x0081BC86` | position/time anchor at `[esi+0xF0..0xFC]`; **touches neither gate** |
| **8 DISABLED / action_hold** | **`0x0081BCF0`** | **writes `[esi+0x64]` bit 0** |
| 13 | `0x0081BD23` | writes `[esi+0x20]` |
| **1, 3, 46, 49** | `0x0081BD29` | **DEFAULT — executes nothing at all** |

And the case body is unambiguous — the property VALUE is the gate:

```
0081BCF0  cmp dword [ebp+0x10], 0   ; the value
0081BCF4  mov eax, [esi+0x64]
0081BCFB  or  eax, 1                ; value != 0 -> SET   the walk gate
0081BD02  mov [esi+0x64], eax
0081BD11  and eax, 0xfffffffe       ; value == 0 -> CLEAR
0081BD14  mov [esi+0x64], eax
```

**So `[char+0x64] bit 0` IS property 8, and property 8 is the only animation
property that can reach either walk entry.** Corroborated structurally by
`0x0081BE90` (the speed setter prop 8 calls on the set path), which refuses on
`[+0x10C]` bit 4, `[+0x64]` bit 0 **set** and bit 1 **clear** — so the healthy
word is 2 and the held word 3.

### 22.2 What this kills

* **§15's mechanism is REFUTED.** "Our client's locomotion is gated on an
  animation state our attack-skill sequence leaves at 0x11/0x15" cannot be true:
  no walk entry reads any animation-state field, and **props 46/49/50 — the trio
  §15 built the whole model on — are a no-op on the gate object.** §15's *wire*
  observations survive intact (the 87/100 mid-chain law, `after46.py`'s 40 events,
  "no return-to-movable prop exists"); its causal reading does not.
* **§15's "prop 8 is NOT the differentiator" is REFUTED** in the same stroke. §15
  looked for prop 8 in the AvChar dispatcher, did not find a case body, and
  concluded it was handled elsewhere and irrelevant. "Elsewhere" is
  `0x0081BC60 → 0x0081BCF0`, and it is the entire mechanism.
* **§14's "the client cannot START movement while its attack action is open"
  SURVIVES, sharpened.** The "open attack action" is `[+0x64] bit 0`, which is
  *our property 8* — not the client's chain, and not a state the client derives.
* **The `0x003D` send is NOT a discriminator, and this weakens `RE-PLAN.md` §1.**
  Every arm of `chcli_dir` — all three flag gates, all three no-path exits, and
  the success path — converges on `0x0081649E cmp [ebp+0x18], 0`, and only that
  operand (forwarded verbatim from MOVE-CMD at `0x0053546D`) decides the packer
  `0x009206D9 mov [ebp-0x1c], 0x3d`. **"The client sent its `0x003D`" therefore
  excludes input, focus and key delivery — but it does not narrow which exit the
  applier took**, which §21.5's prediction had implicitly leaned on.

### 22.3 THE ARM DIFFERENCE, from our own wire — CONTESTED (§22.6); the MECHANISM is confirmed in §23

`action_hold` (`authsrv.py:9209`) is transition-only. It is called with **1** by
the swing loop at `:9805` (`attack_tick`, behind every `attack_started`) and
`:9944` (`hit_enemy`), and with **0** on movement at `:9353` — *outside* the
`MOVE_KEEPS_CHAIN` branch, so the release goes out in both arms exactly as §15
said. **What nobody looked at is the re-arm**, and the door at `:9356` is where
the two arms part:

```python
if state.get("attacking") and not MOVE_KEEPS_CHAIN:
    state["attacking"] = None          # default: the swing loop DIES
```

Under `--move-keeps-chain` the loop survives, `attack_tick` fires again, and
`action_hold(1)` **re-arms the walk gate before the next keypress**. Prop-8
transitions read out of the two captures §14 scored (OBSERVED):

```
frozen arm  20260831T110144  (--move-keeps-chain ON)
  holds   11.702 18.166 21.569 23.348 25.128     <- three re-arms
  release 18.165 20.234 22.354 24.488 29.379
moving arm  20260831T110743  (shipped default)
  holds   11.744 18.200                          <- never re-arms
  release 18.200 20.234
```

The body agrees: in the frozen arm all four `MOVE_CANCEL_REPORT_POSITION` are
**bit-identical to the press position**, 0.0 u, `accepted true`; the moving arm's
tap at 22.386 ran 78.6 u in 0.384 s ≈ 205 u/s. **And the frozen arm carries its
own positive control** — at `t=39.842`, ten seconds after the last release with
the chain long dead and the gate clear, an S press walked **375 u**. Same arm,
same build, same flag. *The arm does not freeze; the armed gate freezes.*

**RECONSTRUCTION — and §22.6 DOWNGRADES THIS TO CONTESTED; read it before
acting on this paragraph.** Attack skill → `action_hold(1)` →
`0x0081BCF0` sets `[+0x64] bit 0` → the movement press dispatches once,
`0x0081A93C` reads it set, `0x0081AD0F` halts the agent and returns success →
`0x008164AD` sends `0x003D` anyway → and under LAW A the swing loop re-arms the
bit before the next press. The prop-8 ⇒ bit ⇒ bail half is OBSERVED in CANCELWALK
F22/F23 on the *cast* case; extending it to the attack-skill case is the
reconstruction.

### 22.4 What this DOES and DOES NOT claim about the owner's complaint

**It explains why R7a froze**, and therefore unblocks LAW A — the retail-correct
wire (87 of 100 mid-chain moves carry no `attack_stopped`), which is the shape
that lets a player move *and keep attacking*, which is what a quarterstep is.

**It does not explain the shipped default's residual.** The owner's standing
verdict is against the **default**, which never re-arms — so §22.3's mechanism is
not that complaint's cause. What it does is make the better fix reachable. Do not
let this section be read as "the quarterstep is solved"; that verdict is the
owner's and has not been given.

### 22.5 Method notes worth keeping

* **`--in <module>` truncates at BOTH ends.** `--bounds ChCliBase` =
  `0x0081AC3D..0x0081BA94`, excluding both `0x0081A93C` (the gate read) and
  `0x0081BD02` (the gate write). A `--in ChCliBase` census of `+0x64` misses the
  entire mechanism and returns a clean, confident, wrong zero. This is
  `studies/enemy` §6o arriving again by a fifth road.
* **`+0xC4` is not the animation queue head.** It is `m_linkOffset` of an
  intrusive `TList`; the head is `+0xCC`. §15's map said otherwise and every
  document inheriting it needs the correction.
* **A PE section walk must use RAW size, not `max(vsz, rsz)`.** `.data` here has
  `vsz=0x5601B8` against `rsz=0x16A00`, so `max()` lets it swallow `.text` RVAs
  and every table read comes back plausible-looking garbage. Caught only because
  the reader carried a byte-level control on two known instructions.
* **Padding hints were wrong twice more** (`0x0081A850` for `chcli_dir`,
  `0x00816370` for the dispatcher). Confirm entries by `55 8b ec` plus `--xrefs`.

### 22.6 THE CORPUS WEAKENS §22.3, and it killed the fix I was about to write

Written after §22.1–22.5, and it walks part of them back. **The static chain
(§22.1) stands — it is re-derived byte by byte. §22.3's dynamic reading does
not, in the strong form I gave it.**

The fix §22.3 implies is "under LAW A, stop re-arming property 8". Before writing
it I measured retail's own prop-8 cadence (`scratchpad/p8d.py`, live corpus, 61
connections). *Positive control:* the same walk reproduces R9's census exactly —
prop 46×164, 49×12, 50×222.

**Retail re-arms property 8 constantly: 193 re-arms, p50 gap 0.503 s, 143 of 193
under 2 s.** "Do not re-arm" is not retail's rule, and shipping it would have been
an invented rule wearing a derivation's clothes — the exact failure
[[feedback-derive-dont-iterate]] names.

Worse for the strong model, hold **durations** (`p8e.py`, split by agent so the
player is not pooled with anyone else — 60 of 61 connections resolve a player,
and non-player prop-8 holds are n=0):

| | n | min | p50 | p90 | max | over 1.0 s |
|---|---|---|---|---|---|---|
| retail player holds | 213 | 0.000 | **1.032** | **22.618** | **92.775** | **117** |

**A living retail player is not immobile for 22 seconds.** Death does not explain
it either — `p8f.py` overlaps each hold with the `0x00F1` bit-4 windows and finds
**116 of 118 long holds with the player ALIVE** (2 overlapping).

So one of these must be true, and this dig has not settled which:
1. those long windows are genuinely immobile in retail (long casts, knockdown,
   cinematics, zoning) and the model survives intact; or
2. `[+0x64] bit 0` is not the absolute walk block `chcli_dir`'s `jne` makes it
   look like — some path re-clears it, or re-dispatches, that four lanes' xref
   scans cannot see (the event bus `0x00633D70` is the named blind spot).

**What I could NOT measure, stated rather than glossed:** whether the retail body
travels during those holds. `p8g.py` attempted it and **its own control returned
zero** — my guess at the position-stream opcodes and float layout was wrong, so
its null is worth nothing ([[feedback-negative-needs-positive-control]]). That
measurement is the cheapest thing that would discriminate 1 from 2, and it wants
the arc's real position decoder rather than a fresh guess at one.

**§23 CONFIRMED THE MECHANISM IN A LIVE CLIENT** — the gate fires, and the
movement press is eaten unlocking it. What §22.6 says here still stands
anyway: retail holds property 8 LONGER than we do, so the fix is not
"hold it for less time" and may be the client's re-dispatch instead.

**Consequence for the work: no server change ships from this dig.** §22.3 is
downgraded from "RECONSTRUCTION (high confidence)" to **CONTESTED** — the
mechanism is real and verified statically, its sufficiency as the cause of the
R7a freeze is not established, and the corpus actively resists the simplest fix
derived from it. The movehook run (§21.5, sharpened to four outcomes by the
`0x0081ACFA` no-path exit) remains the settling step, and it is now *more* clearly
worth its cost than before, because the desk cannot close this.

## 23. ANIMREF-RE RUN 1: the gate is CONFIRMED IN THE CLIENT, and the press is EATEN

**2026-08-31, owner-driven, loopback, shipped default server with a read-only
tap. All three registered predictions (`RUN-RE1.md`) CONFIRMED, and the run says
something sharper than they asked.** 482 records, both hook controls FIRED, 61
begin-move entries with the gate words read on **61 of 61**.

### 23.1 The scoreboard, against predictions registered before the run

| | Prediction | Result |
|---|---|---|
| P1 | non-moving presses report `E3-walk-gate` | **CONFIRMED** — 5 refusals, every one `gate & 1` SET |
| P2 | idle walks report `passed-flag-gates`, gate CLEAR | **CONFIRMED** — 56 passes; the reader's own control says OK |
| P3 | no `E4-dead` | **CONFIRMED**, and stronger: `m_status == 0x00000000` on **all 61** |

**The gate word takes exactly two values and they partition the capture
perfectly: `0x3` on all five refusals, `0x2` on all 56 passes.** §22.1 predicted
those two literals *before the run*, statically, from `0x0081BE90`'s refusal
conditions (bit 0 set, bit 1 clear) — "the healthy word is 2 and the held word
3". Measured, to the bit.

P3's by-product retires §21.4's inference: `m_status` reading zero on every
entry means gates A (bit 8) and C (`CHAR_STATUS_DEAD`) are eliminated **by
measurement in the client**, not by reasoning about our send sites.

### 23.2 The refusal and the release are ONE EVENT — the press is spent on the gate

Our server's own prop-8 transitions for the session
(`gamesrv/authsrv-20260831T203836-c1.jsonl`) against the client's refusals:

```
server HOLD  0.00  4.20  8.60 18.82 23.02     hold durations 0.43 0.28 0.33 0.31 0.32
server REL   0.43  4.48  8.93 19.13 23.34
client E3    0.83  4.89  9.33 19.53 23.73
```

| pairing | offsets | sd |
|---|---|---|
| E3 − HOLD | 0.83, 0.69, 0.73, 0.71, 0.71 | 0.0496 |
| **E3 − RELEASE** | **0.40, 0.41, 0.40, 0.40, 0.39** | **0.0063** |

**The refusals lock to the RELEASE, 8× tighter than to the hold**, and the
interval gaps agree without needing the offset at all (release 4.05/4.45/10.20/
4.21 against E3 4.06/4.44/10.20/4.20). The residual 0.400 s is the constant skew
between the hook's `GetTickCount` origin and the tape's.

**The causal direction is not read off the clocks — it is in our own source.**
`authsrv.py:9353` sends `action_hold(0, "the player moves")` *from the movement
message*, and `chcli_dir` emits its `0x003D` on **every** arm including the
refusal (§22.2). So the call that refused is the call that triggered the release:

> **The player's movement press is consumed unlocking the gate instead of moving
> the body.** One press, one round trip, no displacement.

### 23.3 WHAT THIS RUN MEASURED — and the scenario it did NOT (owner's catch)

**The runsheet asked for "press slot 1, immediately try to walk", and the owner
did exactly that — move-at-START, in the first ~0.4 s after the skill press,
before the swing resolves. That is NOT the quarterstep.** The quarterstep is a
move timed to the moment the attack animation *completes* — a different instant,
and the one that is "supposed to be enabled". The owner flagged this after the
run, and they are right: nothing here measured the quarterstep window. §23.3 as
first written tied the 0.3 s hold to the *"unreliable"* verdict; that connection
is **withdrawn** until the right window is captured (RUN-RE2).

What IS established, and it stands: **while the gate is set, a move press is
eaten and clears the gate without moving the body** — measured for move-at-start,
5/5. Whether the gate is *also* set at the quarterstep window (animation
complete, chain still live) is the open question RUN-RE2 exists to answer.

Two readings are now live and this run does not separate them:

1. **move-at-start being blocked may be CORRECT** — stock does not let you abort
   an attack-skill press by instantly walking off — in which case run 1 measured
   expected behaviour and the real bug is entirely in the quarterstep window;
2. **or the same gate is set across the whole swing**, in which case the
   quarterstep press is eaten too and run 1 is the same bug sampled early.

They predict different things at the animation-complete instant, so RUN-RE2
distinguishes them directly.

One mechanism detail that holds regardless of scenario: the eaten press does not
retry. MOVE-CMD is called **only when the movement direction changes**
(CANCELWALK F25, `0x005355C0`'s 50 ms evaluator) — so holding the same key after
a refusal produces no second `chcli_dir` call; the player must release and
re-press. That is a real friction, but it is not yet tied to the quarterstep
*feel* and must not be quoted as if it were ([[feedback-observed-context-is-part-of-the-claim]]).

### 23.4 What is now settled, and what is NOT

**SETTLED (OBSERVED):** the walk gate exists, is `[char+0x64]` bit 0, is written
by property 8, is read by both begin-move entries, refuses the walk when set, and
our server sets it for ~0.3 s after a skill press — where a **move-at-start**
press lands and is eaten. §15's animation-state model stays REFUTED; §22's chain
is now confirmed at both ends rather than statically at one.

**NOT YET MEASURED (owner's catch, §23.3):** whether the gate is set at the
**quarterstep window** — the move timed to the animation completing. That is the
window the owner's verdict is actually about, and run 1 sampled a different one.
RUN-RE2 captures it.

**NOT SETTLED, and §22.6's tension is untouched:** retail holds property 8 for
p50 1.03 s — *longer* than our 0.3 s — with the player alive, and retail players
quarterstep. So "hold it for less time" is not obviously the fix and may be
exactly backwards. The candidate that this run newly makes attractive is the
**re-dispatch**: if retail's client re-issues the movement after the gate clears
and ours does not, the divergence is not the hold at all. That is a client
question about `0x005355C0`'s latch, and it is the next cut.

**Not asked, not answered:** whether any of this feels like stock. No fix shipped.

### 23.5 A MOVECODE divergence this capture also carries, unclaimed

Our grant cadence to the sync copy is **p50 0.02 s between setter calls against
retail's 0.82 s** — roughly 40× over-granting — and 26 teleports fired with 6 not
chaining. Neither is this arc's question; both are recorded here so the next
MOVECODE session finds them rather than re-measuring.

## 24. RUN 2 (the real quarterstep window) — the gate refuses 14/14, and a fix I derived, shipped and REVERTED

**Owner-driven, loopback, shipped default, passive tap. The owner played and
quartersteped BY FEEL; nothing about the timing was scripted.** Their verdict
first, because it is the referent: *"got some quarterstep-ish results on hit 7
(didn't feel like a proper stock slide though), but mostly i just stood still."*

### 24.1 The capture matches that verdict exactly

120 begin-move entries, gate words read on 120. **14 refusals, all `E3-walk-gate`,
gate word `0x3`; 106 passes, gate `0x2`.** `m_status` `0x00000000` throughout.

The 14 refusals run from t=21.30 to t=45.70 at a **~1.85 s cadence** — the swing
interval — i.e. one per quarterstep attempt. And the owner's "hit 7" is in the
data:

| attempt | t | outcome |
|---|---|---|
| 1–6 | 21.30 … 31.08 | refused, **nothing follows** |
| **7** | 32.94 | refused, then **22 passes 0.16 s later** (33.09–33.44) |
| **8** | 34.83 | refused, then **28 passes 0.06 s later** (34.89–35.33) |
| 9–14 | 36.47 … 45.70 | refused, **nothing follows** |

So two of fourteen produced a **late** slide — the key was still down when the
gate cleared a round trip later and a second dispatch went through. That delay is
the *"didn't feel like a proper stock slide"*: a stutter-then-go, not a slide.

### 24.2 The server side, and the clock alignment that proves the loop

14 prop-8 hold windows, one per refusal. Aligning the hook's `GetTickCount` to the
tape (offset **4.596 s, sd 0.0062**, from gap sequences that agree to the
hundredth):

```
hold set   25.00 27.09 29.12 31.06 32.89 34.72 …
player tap 25.90 28.05 30.08 31.98 33.80 35.68 …   0.82-0.96 s after the set
release    25.90 28.05 30.09 31.97 33.79 35.68 …   SAME INSTANT as the tap
```

**Every one of the 14 releases in the tape reads "the player moves".** There is no
other release reason anywhere in it. So the ~0.9 s "hold duration" is **the
operator's reaction time, not a length we chose** — our hold has no natural end,
and the player's press is spent unlocking it (`authsrv.py:9353` releases *from*
the movement message; `chcli_dir` sends `0x003D` on every arm including the
refusal, §22.2).

### 24.3 ANIMREF-R10: derived, shipped, REFUTED and REVERTED in one sitting

From §24.2 the fix looked obvious — release the hold when the swing ends, at
`MELEE_ATTACK_FINISHED`, which we already send. I justified it with *"39 of
retail's 213 prop-8 releases sit within 0.25 s of `melee_finished`"*, implemented
it behind `--legacy-swing-hold`, wrote a both-arms test, and took the suite green.

**That statistic has the wrong denominator and the fix is wrong.** The question is
not "of the releases, how many are at a landing" but "of the landings, how many
carry a release":

| denominator | retail | ours |
|---|---|---|
| landings (`melee_finished`) carrying a release | **4.4%** (38/865) | 0% |
| swings (`attack_started`) that set the hold | **11.2%** (101/903) | 100% |
| **prop-8 state AT the landing: HELD** | **98.0%** (848/865) | **100%** (14/14) |
| prop-8 state at `attack_started`: HELD | **100%** (903/903) | 100% |

**Retail holds the gate through the landing, 98% of the time — we match it.** So
releasing there is not retail's behaviour; R10 would have made us *diverge*.
Reverted; the working tree carries no R10.

Two separate errors produced it, both the same shape and both already named in
this repo's own rules: a **subcount read as a rate**
([[feedback-safety-filters-drop-the-anomalies]]), then a **transition rate read as
a fraction of time** — `action_hold` is transition-only, so 11.2% of swings
*toggling* is not 11.2% of time held (measured duty cycle: retail **29.2%**
pooled, p50 19.1%; ours 49.7% across the batch).

### 24.4 What is left is a CONTRADICTION, and it is the arc's real question

Four measurements, each solid, that cannot all mean what they appear to:

1. **Our client refuses a walk when `[ChCliBase+0x64]` bit 0 is set** — OBSERVED
   at `0x0081A93C` (keyboard) and `0x0081AEF4` (click), and the bit is written
   only by property 8 (`0x0081BCF0`).
2. **14 of 14 refused in our client**, gate `0x3`, measured live.
3. **Retail's gate is SET at 98% of landings** and 100% at swing start.
4. **Retail players quarterstep at the damage instant.**

Same binary. So a set gate refuses in our client and appears not to in retail.
**At least one reading is wrong, or a mechanism is unfound.** Do not build a fix
on §24.2 until this resolves — that is exactly the mistake §24.3 records.

One static result already bears on it, and it cuts against the easiest escape:
**a third consumer of the gate exists.** `0x0081BADC`'s function — a movement
re-issue path — checks `m_status` bit 4, then `[+0x64] bit 0` at `0x0081BB02`,
then the speed at `0x0081BB08 fld [esi+0x100]`, and skips everything if the gate
is set. So the gate is not consulted only at begin-move. (`+0x100` is the char's
speed word: one reader, `0x0081BB08`; writes at `0x0081BECA` and `0x0081C005`,
the latter storing **zero** — and property 8's SET path reaches it, because
`0x0081BE90` bails at `0x0081BEB1` precisely when bit 0 is set. *Positive control:
the unbounded `--field 0x100` census contains both writes, which the
`--in ChCliBase` census did NOT — its range ends at `0x0081BA94` and truncated
them away.*)

Open hypotheses, none established: the quarterstep never calls begin-move because
the key is already held (F25: MOVE-CMD fires only on a direction CHANGE);
something else clears the bit locally in retail; the corpus attribution
(`whose_agent`) is wrong and finding 3 is void; retail's release lands
milliseconds after the landing sample; or the gate blocks starting but not
finishing a leg.

## 25. THE CONTRADICTION IS RESOLVED — and §24.4's finding 4 was mine, mis-stated

A nine-agent fan-out with adversarial verification (four lanes, four skeptics, one
synthesis) closed §24.4. **There is no missing mechanism. A set gate refuses in
retail too**; what was wrong was my inference from finding 4.

### 25.1 The retail quarterstep is the SAME two-step ours performs

Not "retail's gate permits the walk". Retail runs the identical sequence §24.2
measured on us: the press is refused at `0x0081A93C`, `chcli_dir` emits its
`0x003D` anyway (§22.2), the server clears property 8 — and the **still-held key**
produces the walk on the next dispatch. Scored on both sides with one metric and
one denominator (a prop-8 hold ending on a c2s move; unscorable attempts counted
as 0 u, never dropped):

| quarterstep attempts | n | travelled ≥50 u within 1.0 s |
|---|---|---|
| retail | 53 | **11 = 20.8%** |
| ours (run 2) | 14 | **2 = 14.3%** |

**Retail's own quarterstep succeeds about one time in five on the wire, and ours
is not distinguishable from it at these n.** Those two successes are §24.1's
attempts 7 and 8, and their client-side latency was **59 ms and 165 ms** after the
clear — the mechanism worked both times it was given the chance.

### 25.2 Why it looked like a paradox — three reading errors, no missing mechanism

1. **"Hold W" was scored as a tap.** In 12 of our 14 attempts the gate went clear
   within 10 ms of the refusal *and stayed clear*, yet nothing re-dispatched for
   1.775–2.152 s. During an actual walk `chcli_dir` fires at frame rate (gap after
   a gate-CLEAR entry: **p50 16 ms, 78/101 ≤20 ms**), so a held key would have
   re-dispatched at once. The key was up. **H1 is refuted — and the reason the
   attempts failed is that the press ended before the round trip did.**
2. **The 92-second holds were read as "a living player who must be moving".**
   §22.6's tension is settled, option 1, by three orders of magnitude: holds ≥5 s
   are **29 of 212 spans but 81.1% of all held time (1038 s), carrying SIX c2s
   movement messages, 23 of 29 carrying zero.** *Positive control:* the same
   decoder over clear-state pairs returns **289.0 u/s** — GW's run speed — so the
   instrument sees motion where motion exists. Long retail holds are immobile.
3. **The wire was read as the body.** Measured on run 2: **97 `chcli_dir` entries
   across five held-key bursts produced 5 wire messages — 19.4:1, ~2.6 msg/s of
   walking.** A 200–300 ms slide leaves at most one sample and often none. **The
   corpus cannot see a quarterstep by construction**, which is why four lanes
   could not settle this from tape.

### 25.3 What the server MUST NOT change, each with the number that forbids it

* **Not R10.** Releasing at `MELEE_ATTACK_FINISHED` is refuted at 848/865. Stays
  reverted (§24.3).
* **Not "hold it for less time".** Retail p50 **1.041 s**; our windows are the
  operator's reaction time, not a length we chose.
* **Not "stop re-arming".** Retail re-arms 193 times, p50 gap 0.503 s.
* **KEEP releasing on movement.** `authsrv.py:9353` *is* retail's rule —
  **62 of 66** c2s moves inside a hold are followed by that hold's release within
  0.25 s, **p50 34 ms**.

### 25.4 The one divergence left, with its denominator and its confound

**Retail's holds mostly end on something that is not the player moving; ours never
do.** Independently measured twice, by different proxies, agreeing in direction
and magnitude:

| | retail | ours (run 2) |
|---|---|---|
| holds ending WITHOUT a player move nearby | **159/212 = 75.0%** (c2s proxy) / **141/212 = 66.5%** (grant proxy) | **0 of 14 = 0%** |

Every `action_hold(send, state, 0, …)` site in our source is triggered by
something external — `:9264` retarget, `:9353` movement, `:9409` cancel-cast,
`:9487` cancel-action, `:9752` target gone, `:11185` skill press, `:11798` cast
completes. **There is no release tied to the melee action's own termination**,
where retail's 75% land on `attack_stopped` / skill-finished and friends.

**CONFOUND, stated rather than buried:** the owner was hitting a practice target
that never dies and never leaves range, so our chain had no natural end available.
This may be scenario, not defect. It is the only live server-side thread, and it
is **not R10 rephrased** — R10 asked "release at the landing" (refuted, 98–100%
held there); this asks *what ends the other 159*.

### 25.5 What is still unmeasured, and the cheap run before the expensive one

Genuinely open: retail's body inside a hold at sub-300 ms resolution (the wire
cannot supply it), and `m_flags` bit 2, which our client reads clear on 181/181
samples and which has never been sampled in a retail client.

The expensive answer is the movehook rig against `vault/run-live/` — a **live
session on the secondary account**, needing the owner's explicit go-ahead.
**Run RUN-RE3 first**, because it is loopback, free, and tests §25.2 item 1
directly: *hold* the movement key through the damage rather than tapping it. If
the slide then fires reliably, the mechanism is confirmed end to end and the
residual is feel; if it still fails with the key demonstrably down, item 1 is
wrong and the live run is justified.

**And a scoring rule this dig earned:** score run captures **per file, never
pooled** — a pooled bin ranked our known-bad arm as healthy, and a metric that
passes on the broken arm is measuring the wrong quantity.

## 26. RUN 3: holding WORKS (54% vs 14%) — and the warp is OURS, caught in the record

**2026-09-01, owner-driven, loopback, shipped default, passive tap.** Owner's
verdict: *"1 good slide but mostly either warping through the enemy or just not
moving."* 2126 records, 333 begin-move entries, gate words read on all of them.

### 26.1 All three registered predictions CONFIRMED

| # | Prediction | Result |
|---|---|---|
| P1 | with the key HELD, most attempts slide | **CONFIRMED** — the refused press gets its second dispatch **7 of 13 (54%)** against run 2's tap-only **2 of 14 (14%)** |
| P2 | the slide starts 50–200 ms after the clear | **CONFIRMED** — 47, 47, 47, 62, 63, 63, 172 ms |
| P3 | the gate still reads SET at the press | **CONFIRMED** — `0x3` on all 13 refusals, `m_status` `0x00000000` throughout |

**§25.2's reading is confirmed end to end**: the press is refused, the `0x003D`
goes out anyway, the server clears property 8, and a *still-held* key re-dispatches
within ~50 ms. Holding nearly quadruples the recovery rate. The mechanism is not
in doubt any more.

**And it is still not a stock slide** — the owner felt one good one out of ~8. So
a second dispatch firing is NECESSARY and NOT SUFFICIENT, and §26.2 is why.

### 26.2 THE WARP IS OURS, and the whole chain is in the record, twice

Only **three** relocations of the player's displayed body occurred — `setposition`
`0x00602B20`, 213/136/43 u, the "moved with its stamp standing still" detector.
Two sit *inside the gap between a refusal and its recovery*, and their structure is
identical:

```
2.922  chcli_dir     gate=0x3                                <- the press, REFUSED
2.938  setter  ret=0x005FD918  obj=SYNC   tgt=(9931,8203)     <- OUR 0x0029 GRANT
2.953  setposition   ret=0x00604A55  obj=LOCAL               <- THE BODY IS MOVED
2.953  setter  ret=0x00604A48  obj=LOCAL
2.953  bake    obj=LOCAL  pt=(9844,8099) tgt=(9931,8203)      <- re-aimed at our grant
2.969  chcli_dir     gate=0x2 -> agapi_setdest  tgt=(10382,7552)  <- client's own, ELSEWHERE
```

and at t=4.95 the same five steps, our grant aiming **north** to (9968,7965) while
the client's own walker then heads **south-east** to (10211,8434) — opposite
directions, 0.015 s apart. **That is "warping through the enemy".**

**The causal reading (RECONSTRUCTION on an OBSERVED sequence, 2 of 2 verified, 3 of
3 by the same retaddr `0x00604A55`):** because `chcli_dir` sends its `0x003D` on
*every* arm including the refusal (§22.2), **our server cannot tell a refused press
from a real one.** It grants a destination for a move the client declined to make;
the client applies that grant to the displayed body as a position correction; and
then the client's own walker pulls somewhere else.

Destination attribution for the run, by return address: **320 (80%) from the
client's own walker `0x005FC8F5`, 44 (11%) from our wire grant `0x005FD918`, 36
(9%) from the relocation path `0x00604A48`.**

**DO NOT repeat §1d.3's error here:** this capture also shows nine 600–763 u
"teleports" at `0x006025AB`, and they are **not** displacements. That is
MOVECODE's halt-in-place path, whose distance is `m_point` against a *stale*
`m_targetPoint` and measures nothing. The real count is three.

### 26.3 The derived candidate — with the denominator stated, and NOT shipped

Our server already knows the answer: it set the hold itself, so it knows the client
will refuse. What does retail do with a movement message while its own hold is set?

| retail `0x0029` grants to the player | count | window | **rate** |
|---|---|---|---|
| during a HELD window | 64 | 1279.2 s | **0.050 /s** |
| while CLEAR | 1612 | 3104.9 s | **0.519 /s** |

**Retail suppresses destination grants ~10:1 while the gate is held** — a rate, not
a count, because the two windows are very different lengths and that is precisely
the denominator error this arc has already made twice (§24.3).

So the candidate rule is: **while `state["action_hold"] == 1`, do not grant a
movement destination from a `0x003D`** — the press cannot have moved the body, so
the grant can only relocate it. Retail's 10:1 is suppression, not prohibition (64
grants do happen), so a total block would overshoot; the honest first form is to
suppress and measure what breaks.

**NOT SHIPPED, deliberately.** Two reasons, both earned today: a fix derived from a
statistic was shipped and reverted within the hour (§24.3), and this one reaches
into MOVECODE's grant path rather than ANIMREF's. It wants the owner's call and a
revert flag, and its verdict is the owner's by feel.

### 26.4 What this leaves

The gate mechanism is closed: it refuses, the hold releases on the press, a held
key recovers in ~50 ms, 54% of the time. **The residual "not a stock slide" is now
two separable things** — the 46% that never recover (the key came up, or the
direction never changed so F25 never re-dispatched), and the warp of §26.2, which
actively fights the slide by yanking the body the other way. The warp is the one
with a derived candidate behind it.

## 27. RUN 4 REFUTES R11 — and tells us the slide was the GRANT'S all along

**2026-09-01, owner-driven, ~12 attempts (8 hold, 4 tap), R11 shipped
(suppressing). Owner's verdict: "0 quartersteps."** Run 3, one day and one flag
earlier, scored 1.

### 27.1 What R11 actually changed, measured

| | run 3 (grant sent) | run 4 (grant suppressed) |
|---|---|---|
| refusals | 13 | 13 |
| recoveries within 1.0 s | 7 (54%) | 6 (46%) |
| **recovery lag** | 47–172 ms, **p50 62** | 313–828 ms, **p50 406** |
| begin-move dispatches | 333 | **59** |
| owner's score | 1 slide | **0** |

**Suppression did not cost recoveries — it cost their SPEED.** A 6.5× slower
second dispatch, 5.6× fewer dispatches overall, and a slide that arrives 400 ms
after the damage is not a slide. R11's default is reverted; the lever survives as
`--suppress-grant-during-hold` because the A/B is worth repeating.

### 27.2 THE FINDING, and it is bigger than the flag

**Our client re-dispatches promptly because OUR GRANT hands it a destination.**
Without one it waits for the input evaluator to notice a direction change
(CANCELWALK F25, `0x005355C0`), which is an order of magnitude slower.

So what we have been calling the quarterstep was substantially **our server
yanking the body** — and that is why the owner has said, every single time, that
it never felt like a stock slide. §26.2's relocation and §26.1's fast recovery
were **the same event seen from two instruments.** Removing the yank removed the
slide, because they were one thing.

This retires a reading that has survived three runs: that we had a working-ish
quarterstep with a latency problem. **We have never had one.** What we had was a
server-driven relocation that happened to move the body in roughly the right
direction, fast enough to read as motion.

### 27.3 What that means for the arc

* **§26's mechanism is unaffected and still correct** — the refused press, the
  `0x003D` it sends anyway, our grant, the AgTrack `setposition`. That chain is
  observed. What was wrong was assuming the *slide* was independent of it.
* **§25's "ours is not distinguishable from retail at these n" is now suspect
  from the other side.** Retail's 20.8% is a real client walking; a share of our
  14.3% was a relocation. The two metrics are not measuring the same thing, and
  the comparison should not be quoted again without this caveat.
* **The real quarterstep is still absent, and it is a client-side re-dispatch
  question.** Retail's client must re-issue movement after the gate clears
  without needing a server destination. Ours does not. That is `0x005355C0`'s
  latch, and it is the next target — a static one, needing no run.

### 27.4 Method note: the fix was audited, correct, tested, and wrong anyway

R11 was derived from two measurements with their denominators checked, shipped
with a revert flag, guarded so its own bookkeeping could not fire, and covered by
a test whose known-bad arm scored badly. **All of that was true and it was still
the wrong change**, because every measurement behind it scored the *relocation*
and none scored the *slide*. The run refuted it in one session.

That is the argument for shipping and measuring rather than deliberating: the
evidence that killed it was not available from the desk at any depth of analysis.
It is also the second time in two days that a correct-looking derivation was
refuted by the next measurement (§24.3 was the first, on a denominator).
**Ship, then measure, then believe the measurement over the derivation.**

## 28. THE RE-DISPATCH IS DECODED — the quarterstep is the client's own 250 ms resume poll, and §27.3's "static target, no run" is answered

> **⚠ READ §30 BEFORE USING THIS SECTION. Its central claim is REFUTED.**
> The 250 ms poll is real and every address below re-derives — but it resumes
> **STEERING, not translation**. `0x005FC900` → `0x00602CC0`, which writes
> `[agent+0xCC]` target heading and `[agent+0xC8]` angular rate and **never**
> `[agent+0x48]` (the translation field its sibling `0x00602B20` installs); and
> the payload's own guard at `0x0081BB08` requires the speed `[+0x100]` to be
> **zero**, so it only ever fires on a body that is already standing still.
> It turns a stationary body toward the held key and reports the turn as
> `GAME_CMSG 0x0040`. **It does not walk a held key out of an aftercast**, which
> is what this section says it does and what two shipped defaults were built on.
> §30 has the correction, the evidence, and what it cost.

§27.3 named the next target: retail's client re-issues movement after the walk
gate clears with no server destination and no new key edge, and "ours does not."
That is now read out of the binary rather than guessed, and two changes ship on
it. **No run was needed to find the mechanism — this whole section is static.**

### 28.1 The mechanism, three functions

Prop 8's ChCli case body (`0x0081BCF0`, §22) does more than flip the walk gate.
The **gate-CLEAR arm** (`0x0081BD14 and eax,~1` then `0x0081BD17 call 0x0081C090`)
calls a **resume-window armer**:

* **`0x0081C090`** (opens `57 push edi`): unless dead, and only with gate bit 0
  CLEAR and bit 1 SET, it ORs bit 0 into `[this+0x110]` and writes
  `[this+0x114] = clock() + 0xFA` — a **250 ms deadline** — registering the timer
  via `0x009217C0`. (`0x006044E0` resolves `clock()`: `[[singleton]+8]+0x148`.)
* **`0x0081B940`** is the deadline checker. When `now - [this+0x120] >= 0x7D0`
  (2000 ms) it calls, at `0x0081BA1E`, the payload; the `+0x110` bit is disarmed
  first (`0x0081B979`).
* **`0x0081BA80`** is the **payload**, and its guards are the whole finding. It
  proceeds only when: gate bit 5 clear, the **latched input vector** at
  `+0x4C/+0x50` is non-zero, **gate bit 2 (held input) is SET**, not dead, gate
  bit 0 clear, the **speed `+0x100` is ZERO** and the current motion vector is
  zero — i.e. *the player is holding a direction while the body stands still with
  the walk gate open*. It then `atan2`s the latched vector against the current
  heading (`0x005FC310`) and calls `0x005FC900` with the agent id and the angle —
  **a fresh directional move with no server destination and no key edge.** Every
  non-ripe branch RE-ARMS the 250 ms window (`0x0081BC43/45 → 0x0081C090`); the
  no-input branches let the poll die (`0x0081BC51/55`, plain return).

The **held-input bit 2** is set by `0x0081BE50(bool)` (sole caller `0x00816C08`,
whose singleton chain `[[0x47F660]+0x2C]+0x680` is the local player's ChCliBase):
arg≠0 ORs bit 2 **and arms the window itself** (via predicate `0x007E08C0`), arg=0
clears bit 2. Its caller `0x004F3800` is the **input-transition manager** — it
raises the bit when a movement control activates (`0x004F3842/0x004F386C`) and
clears it when the control releases. That is the client's own definition of a key
being *held*.

### 28.2 What this explains, all of it derived

* **Why holding W after a cast did nothing (run 3's 46% never-recover arm).** A
  key held across a whole cast produces **no wire report** — the client latches
  movement input on edges, and a hold has no edge after its keydown. So our server
  never released the action hold (prop 8 stayed 1), the walk gate stayed SET, and
  the resume poll's `gate bit 0 CLEAR` guard failed forever. The body rooted until
  the next edge. **This is not a server timing bug; it is a missing gate-clear.**
* **Why the "grant not yet identified" (the R7a/LAW-A blocker, FINDINGS §14) was
  never a grant.** Retail feeds a mid-chain mover nothing on the wire; the client
  walks the held key out of its own aftercast via this poll, armed by prop 8's
  gate-clear. The complement LAW A was waiting on is **client code plus prop 8
  itself**, both of which we already send.
* **Why the tap-train froze under LAW A and that was retail-correct.** The resume
  rescues **holds only** — a tap clears bit 2 and zeroes the latched vector at
  key-up, so the poll dies at its first tick. A tapped key in a rooted window
  genuinely does not resume in retail either; the freeze was tap behaviour, not a
  defect.

### 28.3 Two changes shipped, both derived, both with revert arms

* **ANIMREF_E3_RELEASE (default ON, `--no-e3-release`).** Release the action hold
  (`[8 → 0]`) in the **E3 batch** — the caster-freed instant — which is what
  clears the client's walk gate and arms the resume poll for a held key. Corpus
  evidence: **19 of 19** unmoved cast cycles carry `[8 → 0]` riding the E3, E3
  first (a `prop8timeline.py` scan over all 21 live captures; positive control =
  castmech P10's t=69.670 re-found). The older corpus's "silent E3s" were casts a
  movement instant had *already* released — transition-only elides a re-release —
  which **resolves castmech P10's "recorded, not resolved."** Not sent when a
  QUEUED cast begins at the same instant (the hold hands over cast-to-cast with no
  toggle, castmech 3b). Known-bad arm reproduces the root.
* **MOVE_KEEPS_CHAIN flipped to default ON (`--legacy-move-stops-chain`).** LAW A
  is now the default: movement no longer sends the prop-3 that **cancels the attack
  animation** — the message retail omits at 87/100 mid-chain moves, and the one
  the owner's runs kept reporting as "cancelling the animation instead of sliding
  while it plays." The blocker that kept it opt-in (§14) is gone: the complement is
  the resume poll above, and the `[8 → 0]` this door already sends is what arms it.

### 28.4 Instrumentation: the next ordinary run PROVES the poll fires

Three hook sites added to `content/movecode.toml` (via `codescan.py`, per-row
provenance, pinned build 38797), and a `pushedi` emulation shape added to the hook
(`movehook.c`/`gensites.py`) for `resume_arm`'s `57 push edi` entry:

* **`resume_arm` (`0x0081C090`)** — arms fire count; if it never hits after a cast,
  our prop-8 economy still isn't reaching the client's resume machinery.
* **`resume_fire` (`0x0081BA80`)** — the payload; its hit ratio against `resume_arm`
  is the poll's live/die rate, and its gate word at the hit shows which guard
  passed. `readhook.py`'s new ANIMREF-RE section scores exactly this, and flags a
  fire whose walk gate is SET (a decode contradiction).
* **`heldbit` (`0x0081BE50`)** — arg 1 at key-down, 0 at key-up: the client's own
  "held" edges, so a `resume_fire` that dies on bit 2 has its reason.

`test_movehook` 302 checks (floor 169). The owner's next normal run writes the
capture; `readhook.py` reads the poll's arm/fire ratio with no further work.

## 29. §28's DEFAULTS ARE REVERTED — the operator's verdict, same day

> *"it's bad. very floaty."*
> *"warping, etc. i think we may have to look at the movecode itself again."*
> — operator, 2026-09-01, playing the §28 defaults

**Both §28 defaults are opt-in again** (`--move-keeps-chain`, `--e3-release`).
The decode in §28 is **not withdrawn** — the resume poll is read out of the
binary and every address in it still audits. What is withdrawn is the claim that
the *wire built on it* was an improvement. It was worse than the door it
replaced, and a feel verdict outranks a derivation ([[quarterstep-is-a-feel-thing]]).

### 29.1 The process error, which is the real finding

**Two changes shipped in one commit, so neither is individually convicted.** LAW
A and the E3 release went out together; the operator played once; both come back.
That is the whole cost of the pairing — a single run could have convicted one of
them if they had shipped one at a time, and instead it convicted the pair.
`RUN-RE*.md`'s own discipline (one question, one A/B flag —
[[feedback-ask-run-questions-before-the-run]]) was written for exactly this and
was not followed here.

Worse, **neither shipped with a prediction about MOVEMENT QUALITY**. §28 predicted
the resume poll would fire; it did not predict what would happen to a body that
our own server is simultaneously re-pinning. "Floaty" and "warping" are not
outcomes any §28 check could have scored, because nothing measured the body.

### 29.2 Two named suspects, neither yet measured

**Suspect A — the walk-gate RE-HOLD on a walking body (explains "floaty").**
Under LAW A, `state["attacking"]` survives a movement press, so `attack_tick`
keeps opening swings while the player walks. Every open calls
`action_hold(send, state, 1, ...)` → generic-property 8 = 1 → **sets the walk
gate** (`ChCliBase+0x64` bit 0, `0x0081BCF0`) on a body that is mid-walk — against
`cancel_on_move`'s own `action_hold(0)` on the next report. Set, clear, set,
clear at the swing interval. A refused arm still runs `0x0081AD0F → 0x005FCA80 →
0x00605F70`, which **turns the body and zeroes AgTrack's `clientControlled` and
history head** — so the flicker is not merely a stutter, it also wipes the state
our re-pin reads. RECONSTRUCTION; `test_castcancel` §5's LAW-A arm now pins the
re-hold so it cannot go unnoticed twice.

**Suspect B — the resume poll moving the body with no c2s report (explains
"warping").** The E3 release exists to clear the gate, and the gate-clear arms
the poll (`0x0081BD17 → 0x0081C090`). The payload `0x0081BA80` re-issues movement
via `0x005FC900`. **Whether that path reaches the c2s send gate at `0x0081649E`
was never checked** — §28 asserted the poll walks the body and simply did not ask
whether the server is told. If it is not, our position belief goes stale and the
**active re-pin** (`2f00ea5`, on by default since days earlier) yanks the body
back. That is a discontinuous relocation: warping, by construction. UNVERIFIED —
and it is the cheapest thing to settle, because it is static.

### 29.3 What must NOT be concluded from this

* **Not "the §28 decode was wrong."** The addresses, the guards, the 250 ms
  deadline and the held-input bit are OBSERVED and re-derivable.
* **Not "LAW A's corpus fact was wrong."** 87 of 100 mid-chain moves carry no
  prop-3; that stands. What is now known is that removing our prop-3 without
  removing the *re-hold* leaves the chain fighting the walk gate.
* **Not "the E3 release is wrong."** 19 of 19 unmoved corpus cycles carry it.
  Retail sends it *and* survives, which means retail has something we do not —
  most likely a server that does not re-pin a body it cannot see.

### 29.4 The next check is STATIC and needs no run

**Does the resume-poll path reach the c2s send gate `0x0081649E`?** Trace
`0x005FC900` (and `0x009207B0`) to a send or prove it cannot reach one, with the
`chcli_dir → 0x0081649E` chain as the positive control. That single answer
decides suspect B, and it decides whether the fix is *in our re-pin's trigger*
(if the client walks silently) or *in the E3 release's placement* (if it does not
walk at all). Only after that is a client run worth spending, and then on **one
flag at a time**.

## 30. §28 IS REFUTED, AND THE OPERATOR'S OWN CAPTURE NAMES THE CAUSE

A 13-agent decode (four lanes, adversarial pass, synthesis) plus a direct read of
the operator's own session. **Every claim submitted to the adversarial pass was
refuted — 8 of 8.** The most important refutations are of my own §28 decode.

### 30.1 The correction: the resume poll TURNS, it does not WALK

`0x005FC900` → (validation, asserts `0x4D1`/`0x4D2`/`0x4D4`, singleton
`0x0047F660`, roster index bound-checked against `[esi+0x154]`) → **`0x00602CC0`**
at `0x005FCA6A`. `0x00602CC0` writes `[esi+0xCC]` (target heading) and
`[esi+0xC8]` (angular rate) and calls `0x005FF880`; it **never writes
`[esi+0x48]`** — the translation field its sibling `0x00602B20` installs. And the
payload's own precondition at `0x0081BB08` is `fld [esi+0x100] / fldz / fucom /
test ah,0x44 / jp 0x81BC43` — the MSVC "branch if not equal" idiom, so it
**re-arms and returns unless the speed is exactly zero**, with the same test
applied to both components of the motion vector from `0x005FC550`.

**A turn-in-place on a body required to be stationary cannot resume a walk.**
The poll also *does* report what it did (`GAME_CMSG 0x0040`, 12-byte struct via
`0x00491DE0` → `0x007DCF00`), so §29.2's "suspect B — the client walks silently
and the re-pin yanks it" is dead twice: it does not walk, and it does report.

**And the axis that kills the whole family at once:** every element of the poll
is static code in the pinned build. Neither default patches the client. The
armer's call sites include `0x0081AED2` (every click-to-move) and `0x0081BE70`
(every keyboard press), so it armed constantly in every prior session — 108
`ROTATE_PLAYER` arrivals were logged 2026-08-13, nineteen days before the flip.
**A constant cannot explain a change.** That test should have been applied to my
own decode before it shipped; it is cheap and it is decisive.

Two further corrections worth keeping: the poll is **not** a free-running 4 Hz
clock (arm-while-armed is a no-op at `0x0081C0AD/B5`, the checker clears the bit
at `0x0081B979`, and the *acting* path `0x0081BC0F → 0x0081BC42` contains zero
re-arm calls — it is a one-shot deadline armed by input events; corpus seal: of
63 consecutive `0x0040` gaps, **zero** fall in the [0.230, 0.270] s bin a 4 Hz
free-run must populate). And `0x003D` is **not** the only c2s message carrying
position — `GAME_CMSG 0x0047` is `header + vec2 + dword`, emitted by
`0x00920940`.

### 30.2 The operator's session is ON DISK, and it settles the cause

The §28 defaults shipped 06:51:26 and were reverted 07:20:54.
`vault/captures/gamesrv/authsrv-20260901T070557-c1.jsonl` opened **07:05:57 —
inside that window**. This is not a replay: it is the traffic the operator scored
"very floaty" and "warping", next to five sessions they did not.

| run | span | grants/s | reports/s | grants/report | swing-caused gate SETs | `attack_stopped` |
|---|---|---|---|---|---|---|
| **07:05 (LAW A live)** | 35.4 s | **2.06** | 0.82 | **2.52** | 13 | **0** |
| 05:57 pre-ship | 34.9 s | 1.43 | 0.89 | 1.61 | 13 | 13 |
| 05:21 pre-ship | 39.0 s | 1.74 | 0.87 | 2.00 | 14 | 13 |
| 04:51 pre-ship | 47.8 s | 1.69 | 0.96 | 1.76 | 14 | 13 |
| 08-31 21:02 | 63.6 s | 1.75 | 0.82 | 2.13 | 14 | 14 |

Positive control: 146 property-8 sends found across the six captures, so the
label scan sees the channel. (Its first version scored 0 and said so — the
records carry `opcode`/`label`, not `vals`.)

**Three results, and two of them are refusals:**

1. **The run is IDENTIFIED.** `attack_stopped` = 0 against 13/13/13/14. That is
   LAW A's signature and nothing else produces it. OBSERVED.
2. **`ANIMREF_E3_RELEASE` had ZERO EXPOSURE.** The session contains no cast at
   all — all 13 holds are `the swing at 10` — so the E3 release never fired
   once. It is **not** exonerated and **not** convicted: it ran zero trials
   ([[feedback-zero-exposure-is-not-a-null]]). Any future claim about it starts
   from nothing.
3. **The synthesis's own rank-1 mechanism is REFUTED as a differential.**
   Swing-caused gate SETs are **13 in the bad run and 13/14/14/14 in the
   pre-ship runs** — identical. The claim was that LAW A *creates* gate sets on
   a walking body where the old door created none; the simulation that produced
   "6 sets vs 0" assumed a player who never re-clicks the target. The operator
   re-clicks, the chain reopens, and the old arm set the gate just as often.
   **The gate toggle is not new.** Same axis-4 test that killed my six claims,
   applied to the workflow's own leading answer.

### 30.3 What IS the differential — CORRECTED, see §30.7

The only clean difference is `attack_stopped`: **13 → 0**. OBSERVED, and it is
LAW A's signature.

> **⚠ THE REST OF THIS SUBSECTION AS FIRST WRITTEN WAS WRONG, and §30.7 has the
> correction.** It said the bad run showed "the highest grant rate of the six
> sessions, 2.06/s against 1.43–1.75, and 2.52 grants per report". That rate was
> computed over the POOLED op set `{0x0025, 0x0029, 0x002B, 0x002C}` — and
> `0x0029`/`0x002B` are sent for **every agent in the instance**, so the pool is
> mostly NPC traffic and its rate tracks how many hostiles were awake. On the
> player's own destination sends the bad run is **0.565/s against 0.459–0.586**
> (not an outlier; 04:51 is higher), and on `grant_verdict` fires it is
> **0.424/s, the LOWEST of the five**. The bad run did not grant more.
> Denominator error, mine, in a session where I had already written the
> denominator lesson into memory.

What survives from this subsection is §14's sentence, which LAW A shipped opt-in
behind and which §28 removed on a decode error:

> *our client cannot START moving until its attack action closes, and this
> prop-3 is the only closer we send.*

**§14's blocker was correct in the sense that matters — removing prop 3 changes
the client's behaviour for the worse.** What §14 got wrong, and what §30.7
establishes, is the LAYER: prop 3 does not gate movement at all. It is an
animation event.

### 30.4 What retail actually does with property 8 — the one genuinely new fact

From the 21-capture corpus (61 connections, 61 of 61 framed to the last byte):

* **The release and the movement grant are ONE event.** Of 108 player point
  messages that appear to fall inside a hold, **103 land within one microsecond
  of the CLEAR instant** (|dt| p10 = p50 = p90 = 0.000000 s). Exactly **one**
  message in the whole corpus sits strictly inside a hold away from both edges.
* **Property 8 SET ⇒ essentially no grants**: 0.0039/s held (5 messages /
  1279.19 s / 212 windows) against 0.4793/s clear (634 / 1322.67 s / 192
  windows); paired sign test 11–0 across connections. Negative control passes:
  *other* agents' position messages flow at 0.510/s vs 0.699/s in the same
  windows (ratio 0.730) while the player's own ratio is 0.0082 — 89× more
  player-specific than stream-wide.
* **The §22.6 / §25 contradiction is settled with a third option.** Property 8
  gates the **issuing of new destinations** and the client's two begin-move
  *entries*; it does **not** cancel a leg already in flight. Long holds (≥5 s)
  show no motion (0/29, in-corpus ceiling 0.47 % of long-hold time), but **11 of
  200 short holds are arithmetically FORCED to contain travel** — a body cannot
  cover d units in less than d/288 s. Largest: hold 2.253 s, bracket 753.6 u
  needing ≥2.617 s of running with only 0.481 s outside the hold, so ≥2.136 s of
  motion inside a 2.253 s hold (94.8 %), turn 0.0000 rad.

**Our E3 release sent property 8 → 0 with nothing attached.** That is the inverse
of retail's 103/103 invariant, and it is the reason the release should not be
re-armed in its bare form even though its 19/19 corpus count was right.

### 30.5 Shipped from this section

* **Captures now record their own configuration.** `Recorder.__init__` emits a
  `flags` record — every SCREAMING_CASE module global, *discovered* rather than
  hand-listed, read from the live globals so a flag set by any route is caught.
  Identifying which of six 35-second sessions ran the §28 defaults cost an hour
  of inference from send labels, and it only ever worked for one of the two
  flags. `test_replay.py` §5 pins it, including the check that can fail: flip a
  real flag and the census must move. Floor 4 → 10.
* **Nothing else.** No behaviour change ships on this section. The two §28
  defaults stay opt-in.

### 30.7 CORRECTION AND DECODE: prop 3 is an ANIMATION EVENT, and that is what "floaty" is

Two things, one wrong and one new, both from the same follow-up pass.

**(a) The rate claim in §30.3 is refuted, by me, within the hour.** Three
denominators over the same five captures, spans 34.9–63.6 s:

| run | player destination sends/s | `grant_verdict` fired/s | POOLED/s *(what I published)* |
|---|---|---|---|
| **BAD 07:05 (LAW A)** | **0.565** | **0.424** | 2.063 |
| 05:57 pre-ship | 0.459 | 0.459 | 1.433 |
| 05:21 pre-ship | 0.513 | 0.513 | 1.743 |
| 04:51 pre-ship | **0.586** | 0.502 | 1.694 |
| 08-31 21:02 | 0.519 | 0.456 | 1.746 |

The player-destination rate is flat and the bad run is not its maximum; the fired
rate is the bad run's **minimum**. Positive control: the label census accounts
for every destination send in every file, and every one of them is
`AGENT_MOVE_DIRECTION` — there is no second grant family hiding in the mix. **So
"we kept granting into a refused client" is dead as a description of this
session.** It was a subcount-as-a-rate error of exactly the kind
[[feedback-safety-filters-drop-the-anomalies]] names, and the pooled figure
looked plausible because NPC traffic scales with the fight.

**(b) What prop 3 actually is.** `ChCliApi::SetAgentProperty` fans id 3 into the
AvChar side, `AvApi 0x007DFA60` → (agent→view lookup `0x00802160`) →
`0x007F6C00`, whose entire body is `push 2 / call 0x007F2E90 / ret`. And
`0x007F2E90` is not a flag-clear: it calls the allocator at `0x007E8D80`, writes
the kind into `[node]`, `[ebx+0x2c]` into `[node+4]` and a float into `[node+8]`,
then splices the node into the list at `[ebx+0xC4]`/`[ebx+0xC8]` (the
`action->queueLink` / `action->sequenceLink` pair `AvChar:1243/1251` names, with
the `0xDDDDDDDD` uninitialised-memory assert at `0x007F2EB3` guarding the link
offset). **Property 3 APPENDS an "attack stopped" event to the animation action
queue.** OBSERVED.

It writes nothing the two begin-move entries read: those test `m_status`
(`+0x10c`) and the walk gate (`+0x64` bit 0), and the ChCliBase property switch
sends ids 1/3/46/49 to its DEFAULT no-op arm (§22). **Prop 3 cannot gate
movement, and §14's "the client only starts moving once its attack action closes"
is a reading of a correlation, not of this code path.**

**So the mechanism for "floaty" is the animation layer, not the movement layer.**
Under LAW A the attack-stopped event is never queued, so AvChar never learns the
attack ended and the attack pose persists while the body translates. The result
is a character sliding without a walk cycle — which is what "floaty" describes,
and it is the exact thing the operator asked for one message earlier
(*"it's cancelling the animation instead of sliding while the animation plays"*)
delivered without the half that makes it look right. **RECONSTRUCTION**: the
queue append is OBSERVED, the consumer that would blend a walk cycle is not yet
read, and no frame of the bad run was scored visually.

**(c) "Warping" is NOT explained, and it should not be papered over.** The only
wire handle is the reports' own drift, and it is suggestive at best: the bad run
has the highest p50 (**29.3 u** against 5.7–15.1) and the highest fraction over
100 u (**10 of 29, 34.5 %** against 9.7/29.4/15.2/26.9 %), but 05:21 overlaps it
on both and n = 1 session. Every report in all five runs was ACCEPTED — we
refused none — so no server-side refusal produced a snap. UNVERIFIED. It may be
the same animation defect read as a warp by a viewer with no walk cycle to
anchor on, and that is a guess, recorded as one.

### 30.6 The next check — REWRITTEN by §30.7, which moved the question

§29.4 proposed re-shipping LAW A with the swing re-hold suppressed on a moving
body. **Unsupported** — §30.2 result 3 shows the re-hold is not the differential.

This subsection then asked *"what closes the client's attack action, if not
property 3?"*, framed as a hunt for a movement gate. **§30.7 dissolves that
framing**: property 3 is an append to the AvChar animation queue and touches no
field the begin-move entries read, so there is no movement gate to find. The
question was mine and it was the wrong one — inherited from §14's correlation
and never checked against the code path.

**The question that replaces it is about the ANIMATION consumer.** Retail keeps
the chain alive across a movement press (87 of 100) *and* the body walks looking
right, so retail's client must end the attack pose from something other than
property 3. Concretely, and both steps are static:

1. **Read the consumer of the action queue at `[AvChar+0xC4]/[+0xC8]`** — what
   retires an entry, and what selects the pose while one is live. That function
   decides whether a walking body shows a walk cycle.
2. **Then ask what a walk-start does to it.** If beginning a move retires or
   overrides the attack action by itself, our defect is elsewhere and LAW A is
   safe as wire; if it does not, retail sends a closer we have not identified,
   and the corpus can be asked which property rides the 87 mid-chain moves that
   carry no property 3.

**No client run until those are answered** — and the run that follows is a LOOK,
not a measurement ([[quarterstep-is-a-feel-thing]]): one arm,
`--move-keeps-chain`, one question — does the body walk, or slide?

## 31. THE WALK CYCLE IS REFUSED BY ANIMATION PRIORITY — and retail's answer is to STRETCH THE CHAIN, not to send anything

§30.6 asked what selects the pose while an action is live. **It is not the action
queue at all.** A 12-agent decode (four lanes, adversarial pass, 5 of 7 claims
refuted) plus three independent spot-checks of my own. This section ships the
change it derives.

### 31.1 The mechanism, verified byte-exact

The animation arbiter compares the **candidate's priority against the LATCHED
animation id at `[AvChar+0xDC]`** through a static table at `0x00A92ED8`, stride
`0x20`. The compare, hand-decoded from `0x007F34F9` (the disassembler desyncs on
the entry, the bytes do not):

```
8b 8e dc 00 00 00     mov ecx, [esi+0xDC]              ; the LATCHED animation
3b d1                 cmp edx, ecx
74 47                 je  +0x47
8b c2                 mov eax, edx
c1 e1 05              shl ecx, 5                       ; x 0x20 stride
c1 e0 05              shl eax, 5
8b 80 d8 2e a9 00     mov eax, [eax + 0x00A92ED8]      ; candidate's priority
3b 81 d8 2e a9 00     cmp eax, [ecx + 0x00A92ED8]      ; vs the latched one's
72 31                 jb  +0x31                        ; REFUSE if lower
```

Priorities read out of the table (`0x00A92ED8 + id*0x20`, first dword), **my own
spot-check, OBSERVED**: locomotion ids `0x11`, `0x14`, `0x1D` → `0x0040`; attack
ids `0x23` → `0x0110`; `0x29`, `0x2C` → `0x0120`. So **while an attack animation
is latched, every walk cycle loses the compare and is refused** — and the body
keeps translating, because position (`+0x84/+0x88/+0x8C`) and velocity
(`+0xA0/+0xA4`) live in entirely different fields. *That is a body sliding in an
attack pose, which is the operator's word.*

**The pose is not stuck forever.** When the attack animation completes, the
kind-`0x0C` arm (`0x007FC700` → `0x007FC7A8` → `0x007FCE10` → index table
`0x007FD0CC` → `0x007FCF42`) re-selects locomotion **with no priority test**. So
the visual under a free-running chain is *swing → a few walk frames → swing*.
Floaty, not frozen — and a much better fit for the report than a freeze.

The subsystems are decoupled, exhaustively: forward BFS from seven movement roots
(478–691 functions, 28,860–42,758 instructions each, depth ≤ 8) reaches **0**
functions in the AgentView band `0x007DF000..0x00804500`; AvChar makes **0** calls
to the game-context getter `0x0047F660` (positive control: the three movement
dispatchers *are* in its 1,089 callers). No indirect-call escape hatch either — 0
stored VA words for any of the six relevant entries.

### 31.2 Retail sends NO pose-ender. It stretches the chain.

| | n | p50 | p10 | p90 |
|---|---|---|---|---|
| retail attack-started gaps, **no move inside** | 816 | **1.330 s** | 1.318 | 1.345 |
| retail gaps **containing a move** | 40 | **2.007 s** | — | 3.853 |
| **ours** (as the operator played it), no move | 312 | 1.777 s | 1.771 | 1.781 |
| **ours**, containing a move | 112 | 1.783 s | 1.475 | 2.089 |

**Ratio of medians: retail 1.51, ours 1.003.** A chain that never noticed the
player walking. Absolute intervals differ legitimately (our
`WEAPON_ATTACK_SPEED` is the hammer's), so the dimensionless ratio is the
comparable.

It is a **pause, not a re-stamp**: `gap − moving_span` lands back on the
metronome (p50 **1.330**, 10/40 in band) while `next − last_move` does not
(**0/40** in band). Rate view on a shared denominator: attack-started **0.370/s
while moving against 0.730/s while still, ratio 0.51** — and that is a *floor*,
since mislabelled moving time can only dilute toward 1 (sweeping the episode tail
0 → 0.5 → 1.0 s walks it 0.51 → 0.65 → 0.74, exactly as an under-measured span
must).

**And no message is missing.** Retail's self-scoped property ids: 34. Ours: 22
observed on the wire, 35 emittable. Retail-minus-ours = {37, 39, 45, 57, 64, 65},
**17 self events corpus-wide**, none differentiating. **NOT FOUND: any property
retail sends about the player on a mid-chain move that we cannot emit.**

**The rival is dead, checked not assumed.** `AvApi 0x007E00E0` is a byte-for-byte
twin of property 3's entry, queues kind `0x13`, and its arm performs the
*identical* six-animation cancellation — so retail could have ended the pose with
that property instead. It is **property 49**, and it fires **3 times in the whole
live corpus** against 325 mid-chain moves. It cannot be the pose-ender.

### 31.3 SHIPPED: `CHAIN_PAUSES_WHILE_MOVING`, composed with LAW A as ONE arm

While the player's body is moving, the swing clock **freezes**: the next
attack-started fires one interval after motion *ends*, so `gap = interval +
moving_span`. That lets the attack animation finish and hand the pose back to
locomotion. **No new message; property 4's timing only.** Moving-ness comes from
the two latches the movement arc already maintains (`kbd_moving_at`,
`click_moving_at`) — nothing new to keep in sync.

**Both halves default ON and revert together on `--legacy-move-stops-chain`**,
because they are meaningless apart: with the chain closed on every move there is
no chain to pace. That is §29's lesson wired in — one behaviour, one A/B, not two
independent defaults a single run cannot separate.

The freeze accumulates **above** the landing branch, which is measured rather
than tidy: the first cut put it below and silently skipped whatever part of the
moving span overlapped an in-flight swing's windup. `test_playerswing` §5's
residual check caught it. A landing still lands — what pauses is the *opening* of
the next swing.

`test_playerswing` §5 scores the retail metric on both arms: **shipped 1.83,
legacy 1.000** (fixed 1.5 s span against a 1.75 s interval, so 1.857 is the
arithmetic ideal), separation required, and the residual invariant pinned.
**The known-bad arm scores 1.000 — the metric ranks it badly, which is the only
thing that makes it a metric.** 30 checks, floor 30, identical bare.

### 31.4 Corrections this section forces

1. **`87/100` does not reproduce as a denominator.** The pinned cell is
   **325/343 = 94.8 %**; a 288-cell parameter grid puts every cell between 88 %
   and 95 %. Direction and conclusion unchanged; cite 325/343.
2. **`0x002C` never names the player** — 0 of 7,545 player move messages across
   the corpus. It occurs for other agents. Earlier sections list it as a
   player-move opcode; on this corpus it is not one.
3. **`0x007FBC20` is named by its parameter, not itself** (`AvChar:7159
   animation < CHAR_ANIMATIONS`, bound 0x3F). "PlayAnimation" stays
   RECONSTRUCTION. It does third-witness `CHAR_ANIMATIONS = 63`.
4. **`asserts.py --at` over-spans** in `0x007FD000..0x007FE000` — it attributed
   `AvChar:8673` to a function ending 0x300 bytes earlier. Treat `--at` there as
   a hint, not a naming.

### 31.5 The one question left, and it is the operator's

Everything static is answered. What remains is the thing only a person can score,
and it gets **one arm and one question** ([[quarterstep-is-a-feel-thing]],
[[feedback-ask-run-questions-before-the-run]]):

> **When you start walking in the middle of a swing, does the body play a walk
> cycle — or does it slide in the attack pose?**

Revert arm, same map, same weapon: `--legacy-move-stops-chain`. The prediction,
registered here so it can be falsified: **the default should now walk**, and the
legacy arm should show the animation being cancelled outright on every move (the
2026-09-01 report, *"cancelling the animation instead of sliding"*). If the
default still slides, §31.1's priority reading survives but the pause is too
short, and the next move is to measure the actual attack-animation duration
rather than to lengthen the pause by guess.

## 32. THE LANDING SPLIT — there are TWO regimes, and every door we ever shipped had ONE rule

§31's run answered, and the answer was *"the legs don't move, the attack
animation completes"* — plus the specification that makes sense of the whole arc.

### 32.1 The operator's spec, verbatim

> **note - this should only be the case when the attack actually hits.**
>
> stock behavior:
>
> 1. start casting/attacking → issue move command **before** attack lands (or
>    projectile is launched for spears/bows/staffs etc.) → casting/attacking
>    animation **stops**, and normal movement animation resumes
> 2. start casting/attacking → **wait** for attack landing or projectile
>    launching → issue move command → this is the quarterstep/slide. the
>    casting/attacking animation plays to completion, while the player slides
>    around the ground. if they keep holding the movekey, they'll go back into
>    normal walking animation after the casting/attacking animation completes

**The discriminator is the landing instant**, and this server already holds it
exactly: `player_swing["lands_at"]`, stamped one `swing_windup(interval)` after
the START. Nothing new had to be measured or invented.

### 32.2 This retroactively explains every result in this arc

**Both old doors were right — each about one regime, and each shipped as if it
were the whole rule:**

| door | regime 1 (pre-landing) | regime 2 (post-landing) | the operator's report |
|---|---|---|---|
| legacy (property 3 always) | ✅ cancels | ❌ cancels | *"cancelling the animation instead of sliding while the animation plays"* |
| LAW A (property 3 never) | ❌ completes | ✅ slides | *"the legs don't move, the attack animation completes"* |

Neither was a bad measurement. Each was **one rule where two are needed**, which
is why every A/B in this arc produced a real complaint from a real improvement —
and why §14's "the client only starts moving once its attack action closes"
(regime 1) and LAW A's 325/343 corpus finding (regime 2) were both true and
looked contradictory.

### 32.3 The strongest corroboration is internal: our CAST path already does this

`_mark_cancelled` skips any entry whose `e5_sent` is set. **E5 is the cast's
landing.** So a move before the cast completes releases it; a move after it
leaves the aftercast alone — the wiki's *"the aftercast cannot be reduced or
cancelled"*, pinned since 2026-08-23 by `test_castcancel` §2. **The cast half has
implemented the operator's rule all along; the swing half was the one still
all-or-nothing.** OBSERVED, in our own source, with a test already defending it.

### 32.4 The corpus corroborates the direction — and its control FAILED, so it is not proof

Over the mid-chain moves this scan could pair to a player, moves that **carry**
property 3 sit earlier in the swing than moves that do not:

| arm | n | p10 | p25 | **p50** | p75 | p90 |
|---|---|---|---|---|---|---|
| **with** property 3 | 14 | 0.095 | 0.513 | **0.803** | 0.900 | 1.156 |
| without | 85 | 0.662 | 0.790 | **1.099** | 1.518 | 1.806 |

Against a landing at **0.612 s** (castmech M1's 0.4604 × retail's 1.330 s
metronome): **42.9 % (6/14) of property-3-bearing moves fall before the landing,
against 7.1 % (6/85) — a six-fold enrichment**, in the predicted direction.

**But the positive control failed and that governs the label.** This scan pairs
only **99** mid-chain moves against the established **343**, because its
self-identification (`0x00E4`) reaches only 18 of 61 connections; a candidate
sweep found no better marker that decodes (`0x00CF` reaches 12 and agrees with
`0x00E4` on 8 of those). So the denominator does not reproduce. What survives:
the matcher is **identical for both arms**, so an undercount cannot manufacture a
6× split — the direction is CORROBORATION, the magnitude is UNVERIFIED, and
n=14 is thin. The spec itself is **OBSERVED by the operator on stock**, which is
the primary evidence here; the corpus is the supporting witness, not the case.

### 32.5 Shipped

`cancel_on_move` now splits on the landing:

```python
swing = state.get("player_swing")
pre_landing = swing is not None and now < swing["lands_at"]
if chain_live and (pre_landing or not MOVE_KEEPS_CHAIN):
    send(GV_ATTACK_STOPPED, ...)          # regime 1: the animation stops
```

and the target follows the same split — a pre-landing move forgets it (a cancel
is a real close; the 18 of 343 corpus moves that *do* carry property 3 are
these), a post-landing move keeps it so the chain can resume.

**§31's chain pause is the third part, not a rival.** In regime 2 the chain
survives, and freezing the swing clock while the body moves is what lets the
follow-through finish before the next swing re-latches a high-priority attack
animation — which is precisely the operator's *"if they keep holding the
movekey, they'll go back into normal walking animation after the animation
completes"*. Three mechanisms, one behaviour.

`test_castcancel` §7 pins **both regimes**, the known-bad arm (legacy cancels in
both), and the cast-path cross-check. 30 checks, floor 30, identical bare.

### 32.6 What is still unimplemented, and named rather than glossed

The operator's spec says **"or projectile is launched for spears/bows/staffs"**.
Our landing instant is the melee strike; for a ranged weapon the discriminator is
the **launch**, which is earlier than the projectile's arrival. This server's
`swing_windup` models the strike, and nothing distinguishes ranged from melee at
this door. **NOT IMPLEMENTED** — it will read as regime 2 slightly too early for
a bow. The fix needs the launch instant, which castmech M1 already touches
(Power Shot's E4→E5 at 0.4601/0.4595 of the declared bow speed), so the number is
probably already in hand; it is not wired.

## 33. THE STALL IS OURS — property 8 holds the walk gate past the landing

Twelve agents, four lanes, seven skeptic passes. **The `SURVIVED` set came back
EMPTY — all seven reviewed claims were refuted**, including two "established
facts" I put in the briefing myself. What follows is what the refutations left
standing, which is a smaller and much better-founded result.

### 33.1 The collision hypothesis: NO for this regime — and I was wrong that it was unexplored

> *"i'm thinking it could have to do with unit collision, something we haven't
> looked at too deeply as far as I'm aware"*

**Three parts, and the middle one is my error.**

**(a) You were right that the client does agent-vs-agent work.** `0x005FEF70` is a
real per-candidate loop over other agents — bitset iterator `0x004736B0`, skip-self
`cmp esi,[ebp-0x64]`, world-strided agent array `[edi+ebx+0xe8]` bounded by
`[edi+ebx+0xf0]`, ArenaNet's own `AgAgent:716 checkPtr` and `AgAgent:717
!(checkPtr->m_flags & AGENT_FLAG_INVISIBLE)`, each candidate dead-reckoned forward
along its own velocity before the test. The combined-radius comparison is
ArenaNet-named: **`AgAgent:1261 MathSqrt(combinedRadiusSq) + 1.0f >= distFromLine`**,
radius field `[AgAgent+0xD0]`. OBSERVED, re-derived by two skeptics each trying to
kill it.

**(b) I told the workflow "nobody has ever checked whether it fires against AGENTS."
That was false, and it is my claim, not a lane's.** `0x005FEF70` has been a movehook
site the whole time — `toolkit/clientscan/movehook/sites.h:69`, named `stepclear` —
firing 29–33 times across the captures that carry it, and
`studies/movecode/FINDINGS.md` already records **REFUTED — "gate 3 is agent-vs-agent
blocking, not a terrain test."** I asserted an unexplored area that the repo had
already explored, and a lane spent its budget re-deriving it. **The lesson is the
briefing's, not the lane's: an "established facts" block is exactly where an
unchecked assumption does the most damage, because agents take it as given.**

**(c) The mechanism did not fire in your session.** Your own movehook capture of
2026-09-01 10:51, taken while you fought beside the enemy: **310 bakes, ZERO from the
avoidance re-baker `0x00600B0F`** — 308 hard arrivals from the shared setter, 2 from
the path solver. Both controls fired, the ring was not full (8,290 of 32,768), and 26
other sites returned nonzero including `chcli_dir` ×296. Corpus-wide the re-baker is
**24 of 9,857 bakes = 0.244%, with 16 of 21 runs at exactly zero** — and **19 of
those 24 sit in captures predating the `stepclear` site**, so the corpus cannot
attribute a single avoid bake to an agent either.

**But your instinct about the LOCATION was right**, and `authsrv.py:1236` already
says why: *the client collides for itself and does it better than our navmesh does*.
A destination we grant that pushes you into an enemy is resisted by the client while
our model walks straight through — divergence, reconciliation, snap. **The symptom
lives where you said; the cause is our grant policy, not missing collision code.**

**NOT FOUND, with the search bounded:** no agent-vs-agent separation exists anywhere
on our server path (all 20 collision references in `authsrv.py` are terrain/navmesh).
Between the input dispatch `0x00535380` and the walk gate `0x0081A93C` there is **no
proximity test of any kind** — `chcli_dir` refuses on exactly three conditions
(`m_status` bit 8 at `0x0081A931`, the walk gate at `0x0081A93C`, DEAD bit 4 at
`0x0081A946`), none of which any other agent can set. And the corpus has **zero
exposure, not a null**: every position-bearing movehook record in all 21 captures
names agent id 1 (you, in two world copies), so the roster has literally never
contained a second agent.

### 33.2 The stall: it is OURS, it is property 8, and the number is your number

> *"moving mid-windup: works some of the time, other times theres a ~0.5-1s delay"*

`action_hold(1)` sets the client's walk gate. We send it at every swing open
(`authsrv.py:10041`, `:10180`) and **nothing released it at a landing** — the whole
`action_hold(...,0)` ledger is retarget, movement, cast-cancel, cancel-action,
target-gone, skill-press, cast-completes, and the opt-in E3 release. So the gate sat
shut straight through the window §32 had just declared movable.

| quantity | value | denominator |
|---|---|---|
| hold → first movement report | p10 **0.601 s**, p50 **0.869 s**, p90 **1.015 s** | n=104 hold windows |
| movement reports arriving *strictly inside* a hold | **0** | 188 windows / 215.3 s |
| hold spans ended by a movement press | **257 of 324 = 79.3 %** | closed spans, whole gamesrv corpus |
| property-8 duty cycle over fight time | **39.3 %** | 39.0 / 36.9 / 40.2 per run |

**p50 0.869 s against your "~0.5-1s".** OBSERVED.

**A lane disagreement, adjudicated rather than averaged.** One lane found 249
keyboard reports arriving while our hold was set; another found zero reports inside a
hold window. **Both are right and it is an identity**: the report that arrives during
a hold *is the report that releases it*, because `cancel_on_move` clears the flag on
that very message. The client is silent for the whole hold and then emits exactly one
report — and by decode that report goes out **even on the refused arm**
(`chcli_dir`'s refusal returns `mov eax,1` at `0x0081AD7D`, and `0x00816475 test
eax,eax / jne 0x81649e` sends anyway). We were reading our own release as evidence
the client was fine.

### 33.3 The warp: the first leg out of a hold does not travel, while our model runs full speed

Controlled on leg position — episode-opening legs against episode-opening legs:

| arm (2026-09-01) | client ground speed p50 | our drift p50 / p90 | n |
|---|---|---|---|
| opens **out of a hold** | **103 u/s** | **86.4 u** / 201.6 u | 97 |
| opens with **no hold** | 283 u/s | 8.1 u / 55.6 u | 33 |
| 2026-08-31, out of a hold | **0 u/s** | 158.4 u | 58 |
| 2026-08-31, no hold | 271 u/s | 20.3 u | 70 |

**Negative control:** 2026-08-30 sent no property 8 at all, and its ordinary openers
sit at 281 u/s / 18.5 u drift — the healthy place both "no hold" arms land. *The
effect appears only where the mechanism exists.* Drift is re-seeded on every accepted
report, so these are per-interval divergences once per swing, not accumulation.

So the warp and the stall are the **same defect seen from two sides**: we gate the
client, the client cannot travel, our model travels anyway, and the reconciliation is
visible as a snap.

### 33.4 SHIPPED: F1, one behaviour change, its own flag

**Release the hold at the landing** (`LANDING_HOLD_RELEASE`, default ON, revert
`--no-landing-hold-release`). The gate's live window becomes exactly
`[swing open, lands_at)` — **the same interval §32 already uses for property 3, from
the same predicate.** That is why this is a derivation and not a tuning: §32 shipped
the predicate and simply never applied it to the movement half of the latch.

Also shipped, **correctness only and named as such**: F4, the §31 pause accumulator
now resets above `attack_tick`'s four early returns. Leaving through dead / no-target
/ target-gone / out-of-range while moving used to charge the entire absence to the
swing clock on re-entry. RECONSTRUCTION, never observed firing, and it delays
**swings, not movement** — it cannot affect the question F1's run scores, which is
the only reason it travels with it.

`test_playerswing` §6 pins both arms; the known-bad arm reproduces the stall on
purpose. **Section 1's old assertion — "a landing releases nothing (the chain still
holds)" — was the defect written down as a test**, and it has been corrected in
place. 35 checks, floor 35, identical bare.

### 33.5 Derived and QUEUED, deliberately not shipped today

**F2 — the R11 grant guard is dead twice over.** `GRANT_DURING_HOLD = True` at
`:4325` short-circuits `zl_send_ok`, so the suppression has never evaluated and its
print line has never fired: 201 `(True,'zero-lead')`, 73 `(False,'heading-rate')`,
4 `(True,'grant')`, 2 `(False,'locally-moving')` — **zero suppressions**. And
**247 of 249 (99.2 %)** keyboard reports arriving into a set hold were answered by a
grant within 50 ms (p50 0.843 ms). **The second death is the one that matters:**
`cancel_on_move` clears `action_hold` at `:16790`, and the guard reads it at
`:17660` — ~870 lines later *in the same handler*. So flipping the constant alone
returns a null that would read as clearing the mechanism. The fix must snapshot the
flag at message arrival first. **This is the most valuable cross-lane result of the
arc**: one lane proposed the one-line test, another proved it would lie.

**F3 — `cancel_on_move` gate asymmetry.** `:9481` sends property 3 on
`chain_live and (pre_landing or not MOVE_KEEPS_CHAIN)`; `:9499` forgets the target on
`(pre_landing or not MOVE_KEEPS_CHAIN)` **alone**. With a cast pending short of its
E3 we drop the swing server-side and send **no** stop — the client keeps an attack id
latched at `[AvChar+0xDC]` and the walk cycle stays refused by animation priority.
`test_castcancel` §7 cannot reach it: its rig has no `pending_casts`, so `chain_live`
is always True there. Needs a new cell before it is believed.

**F5 — `click_moving_at` is unbounded** in `_player_body_moving` (`:9857`) while
every sibling reader bounds it. The comment licensing the sticky latch predates §31,
which made `attack_tick` a consumer — a stale click latch now freezes the chain
forever. **Zero trials** (all six click verdicts are `geo-unplaced`), so latent, not
yours. The keyboard latch was **REFUTED as sticky**: the first alarm was a scorer bug
counting `0x0047` as a stop; corrected, `kbd_age` is None on 36 of 36.

**Why none of these ship today:** two defaults in one run convicts the pair and
clears neither (§29). F1 is the arm.

### 33.6 What could NOT be measured, and why that matters

**No capture on disk carries the OFF arm of the §31 pause or the §32 landing split
*with a flags record*.** Exactly three logs in the newest sixty carry both the
111-key flags dump and combat, and all three are post-split; older logs carry a
5-key config line. So "the landing split raised property 8's duty cycle" is
**RECONSTRUCTION from source and cannot be closed retrospectively.** F1's revert arm
produces the first such pair the arc has ever had — a further reason to ship it
behind a flag rather than as an unconditional edit.

### 33.7 The next check

**Score F1, one arm, one question, using sites that already exist.** `chcli_dir`
(296 hits in your last capture) reads the walk-gate word at entry, which answers it
directly: was `[ChCliBase+0x64]` bit 0 **set** at the refused press (our hold — F1's
target) or **clear** (a client-side re-dispatch failure, which would send the arc to
the dispatch driver `0x005355C0` and its 750 ms / 100 ms clocks instead). No new
instrumentation is proposed.

**One caveat before that run:** the `heldbit` site recorded **0 hits** in the
2026-09-01 capture while holds were demonstrably being sent, so as hooked it is
probably not the entry the SET arm reaches. Check its address before relying on it —
`chcli_dir` does not depend on it.

**Pre-registered failure mode:** if the post-landing press still lags after F1, the
hold was not the whole stall, and `0x005355C0`'s clocks are next. That branch is
written down now so a surviving stall is a result rather than a surprise.

## 34. THE SPACEBAR BUG — a regression §31 introduced, found in the operator's own capture

> *"click-to-walk cancelled by spacebar [interact/attack] (which would normally
> walk-to-and-attack in stock) doesn't start attacking. if the last move command
> wasn't WASD, spacebar doesn't fire attacks at all."*

Located in one pass, from `authsrv-20260901T125928-c1.jsonl` — the operator's own
session, still warm.

### 34.1 The client is not withholding anything

| c2s opcode | name | count |
|---|---|---|
| `0x003D` | MOVE_SET_HEADING | 167 |
| **`0x0026`** | **ATTACK** | **101** |
| `0x0047` | MOVE_CANCEL_REPORT_POSITION | 66 |
| `0x003E` | MOVE_TO_COORD | 20 |

**101 attack messages arrived**, at a 90 % follow rate after click-moves (18/20)
against 85 % after WASD moves (142/167) — so the client sends the attack in *both*
regimes, and the "last move wasn't WASD" pattern is not the client withholding it.
And we do handle `0x0026`: the arm at `authsrv.py:16508` calls `begin_attack`.
**The order was accepted and then silently starved.** OBSERVED.

### 34.2 The starver is `_player_body_moving`, and §31 built it

`click_moving_at` is armed on **every** `0x003E` (`:17970`) and cleared **only** by a
later movement report (`:16947`) or a stop report (`:18511`). A click leg that simply
*arrives* clears nothing — the client reports nothing at all while click-walking,
which is the measured fact the arming site itself cites. So after any completed
click-to-walk the latch stays set forever.

Before §31 that cost nothing, and the arming site says so in its own comment: *"a
latch left stale by a completed click costs nothing, because the body it guards is
then parked."* True — while its only readers were the cast-stop send site and
`cast_stop_reckon`, **both of which want to refuse on a maybe-moving body.**

**§31 added a reader with the opposite polarity** — `attack_tick`'s
`if moving: return` — **and did not revisit that comment.** A stale latch now means
no swing ever opens. That is the whole defect, and it is mine.

### 34.3 The previous decode called this one wrong, and the reason is worth keeping

§33.5 listed exactly this as **F5**, labelled *"ZERO TRIALS, not a null … latent, not
your bug"*, on the evidence that all six `click_verdict` records were
`fired:false / 'geo-unplaced'`. **That measured the wrong thing.** Those verdicts are
about whether a click produced a *grant*; the latch is armed in the `0x003E` arm
**regardless of the verdict**, and the capture holds 20 of them. A zero-trials call
made on an adjacent quantity is not a zero-trials call — it is
[[feedback-zero-exposure-is-not-a-null]] applied to the wrong denominator, which is
the same defect the rule exists to prevent, one level up.

### 34.4 SHIPPED: bound the latch, and check BOTH directions

`_player_body_moving` now bounds the click latch by `GRANT_LOCAL_WINDOW` (3.0 s) —
**the existing constant its sibling reader already applies to the keyboard latch**,
not a new one. The keyboard latch stays unbounded deliberately: it has a real
terminator, the `0x0047` stop report, which the client does send (36 of 36 in the
corpus). Bounding only the latch that lacks one is the point.

**Both directions are pinned**, because the obvious fix has an obvious failure mode:
a latch that expires too eagerly stops §31's chain pause from pausing on click-walks
and regresses the quarterstep the operator just approved. `test_playerswing` §7
checks the fresh latch still reads as moving, the stale one does not, an ordered
attack after a completed click-walk **opens a swing end to end**, and — the known-bad
arm — a swing ordered during a live click leg still waits. 41 checks, floor 41,
identical bare.

### 34.5 A process note, because it happened twice in one turn

This fix landed in `main` twice before reaching the worktree: once because the shell
was in `main`, and once because a `sed` meant to repoint the patch script's path
never matched (backslash escaping) and the script re-applied to `main` after I had
reverted it. Both times a `grep -c` "confirmed" the worktree had it — **the pattern
`click = state.get` matches `_cs_click = state.get` as a substring**, so the check
that was supposed to catch the slip endorsed it. The tree was only settled by
grepping for a string unique to the new code. A verification whose pattern is a
substring of unrelated code is not a verification.

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

§21 and §22 are the same kind: addresses, field displacements, a dispatch-table layout and two
opcode numbers, all read from the pinned build with `codescan.py`/`asserts.py` and a
12-line struct walk over the PE section table — measurement, per-row, extractor in this
repo, build named. The three asserts it quotes (`ChCliInt:254`, `ChCliBase:164`,
`Array:587`) are single citations used as the evidence for specific claims, which the
boundary permits and the crash dialog shows any player anyway; there is no bulk dump.
No client launch, no upstream derivation, no §6.1 register row required.

§28 is the same again: six function addresses, the `+0x110/+0x114/+0x120` deadline
fields, gate bits 2 and 5, and the singleton/input-manager chains, all read with
`codescan.py` on build 38797 and recorded per-row in `content/movecode.toml`; the
two asserts touched (`ChCli:0x209`, `ChCli:0x1F2`) are single citations. The corpus
scan (`prop8timeline.py`, `swingbracket*.py`, `alonepairs.py` — session scratch over
the 21 live tapes via `tape.py`/`codec.py`) reports the 19/19 E3-release count with
its positive control named. No client launch on the RE side; the instrument runs on
the owner's own next session.
