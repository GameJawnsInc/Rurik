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

## Provenance

All figures are measurements over the owner's own live captures via extractors in this
repo (`animgrammar.py`, this arc; `tape.py`/`codec.py`, prior arcs); scratch probes and
the referent JSONL are under `vault/research/animref/`. No asset bytes, no client
launch, no upstream derivation — no §6.1 register row required.
