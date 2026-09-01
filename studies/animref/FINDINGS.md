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
