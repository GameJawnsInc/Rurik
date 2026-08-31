# ANIMREF — the retail animation referent: replicate the north star before tuning anything

**Written 2026-08-30, at the resumption of the attack/cast animation work.** The word
`ANIMREF` is registered by this document (checked free per
[../idents/CONVENTION.md](../idents/CONVENTION.md) §2 on 2026-08-30); tokens minted here
are `ANIMREF-R<n>` (rungs) and `ANIMREF-Q<n>` (questions).

## 0. The direction, and why the arc restarts this way

The owner's 2026-08-30 ruling on the movement arc governs this one too: **derive, don't
iterate**. No run-stat loops, no per-run metric targets, no repetitive human-driven
sessions while constants get tuned; a client run is a SINGLE verbatim check of a derived
object, its purpose stated before anyone's minutes are asked for. The movement arc's
winning shape — decode the mechanism → transcribe it server-side → validate by replaying
the whole corpus offline with zero client runs → retrodict every known defect → ship
default-ON with one revert flag (`studies/movecode/FINDINGS.md` §1z-q/r/s) — is the
template. Its animation-arc translation:

> **Before any animation-adjacent constant is tuned and before any acceptance run asks
> for eyes, build the retail referent: the complete attack/cast episode grammar, every
> agent, every live capture, as a typed and counted artifact — then diff our own wire
> against it and fix by derivation.**

This is not a cold start. `studies/castmech/FINDINGS.md` already did exactly this for
the E4/E5 instants and the cancel bursts (measured burst orders, wired 2026-08-22,
commits `238ebb9`/`507d10a`/`639d1b4`/`5a08252`), and the state of every neighboring
claim was re-mapped on 2026-08-30 by a six-lane recon workflow (this section's citations
are its output, each spot-verified against the tree at `2f00ea5`). What was NEVER done
is the systematic version: castmech checked specific instants against two captures; no
artifact yet extracts EVERY episode from EVERY live capture and scores our emission
against the population.

## 1. What is already retail-derived (do not re-derive)

- **The E4 press burst and E5 batch orders**, per family (spell 60/58/59 vs attack-skill
  50/46/49; the attack-skill E5 is SILENT — no 58, no 46, no prop-8 pulse, 2/2):
  castmech §3c. Wired.
- **The cancel bursts**: begun cast → `[8→0, 59, E2]` (4/4, capture `20260824T074002`);
  swing cancel `[3, 8→0]` at the movement/Esc doors vs `[8→0, 3]` at the retarget/press
  doors — per-door orders deliberately un-reconciled. Wired.
- **The timing law**: E4 fires on press-accept; the cast BEGINS when the caster frees;
  E5 = begin + activation (fits 4/4 Necromancer cycles ≤14 ms); E3 = E5 + aftercast
  (0.748–0.765 s measured vs table 0.75); E6 = E5 + recharge (13.7 ms, 6/6).
  `toolkit/authsrv/castgaps.py` is the measuring tool.
- **The swing**: ATTACK_STARTED(4) opens, the hit lands at ~0.45–0.47 of the declared
  interval (NPC 0.4540 n=41; player clean autos 0.4583/0.4669 n=2; Power Shot E4→E5
  0.4601/0.4595 n=2 — three populations converging), FINISHED(1) and damage are the SAME
  wire instant (40/40), the backswing has no wire event, and the client holds NO windup
  constant at all (`combat/PLAN.md` §17d: only `m_attackInterval`/`m_attackModifier`
  exist — attack timing is SERVER-AUTHORED). `SWING_WINDUP_RATIO = 0.4458` is our fit,
  CORROBORATED by the corpus.
- **What drives the animation**: agent property 60 (spells) / 50 (attack skills) via the
  int-agentview dispatch → AvApi `0x007E0200` → AgentView event kind 0x19 — for ANY
  agent; opcode 0x00E4 reaches no animation path (self-suppressed). OBSERVED for the
  body animation by the 2026-08-15 operator run (`combat/PLAN.md` §16 — property 60
  played the full per-skill body animation; 228 drove nothing); the static read is
  `skillcast/FINDINGS.md` §15–§16. Property 8 is the view's action-hold; its CLEAR
  schedules a deferred "return-to-ready" at +250 units of an unresolved clock
  (skillcast §16.2).
- **Attack-speed modifiers**: IAS/DAS cut the DURATION multiplicatively
  (`duration × (1−p/100)`), NOT rate division — corroborated wiki + GWCA + disassembly;
  modelled in `attack_interval_factor()`.

## 2. The divergence census — what is still synthetic, thin, or absent

Labels per `studies/character/FINDINGS.md`; every row spot-checked in the tree 2026-08-30.

| # | divergence | state | evidence |
|---|---|---|---|
| D1 | **Attack-skill E5 timing**: we send E5 at begin+activation (=instantly, activation 0.0); retail's rides the weapon interval — observed gap ~1.14 s = 0.46 × 2.475 bow | KNOWN, recorded as OURS in `authsrv.py:7554-7561`; `e5_at = begin + activation` at `authsrv.py:10941` | Power Shot cycles, castmech M1 |
| D2 | **Player windup at scale**: our ratio rests on n=2 clean player autos | THIN (CASTMECH-P6 open) — but the isle bench capture `20260818T132739` holds ~495 damage events at 1.330 s median gap, auto-attack only, NEVER mined for windup | mine before registering a run |
| D3 | **Other-agents' cast grammar**: castmech's register is player-centric; the isle PvP detour (`20260817T231139`, maps 310–312) holds other players' casts at scale, never mined for the property-burst grammar | NOT MINED | corpus lane recon 2026-08-30 |
| D4 | **NPC cast animation shape**: our NPC skill send is `[GV_SKILL_ACTIVATED, agent_id, skill_id]` (3 values, `authsrv.py:12749`) vs the player-form `[60, agent, target, skill]` (4) | UNVERIFIED against retail's other-agent form — D3's mining answers it |
| D5 | **Interrupt wire shape** (CASTMECH-P1): zero interrupts ever captured; GV 35/46/48/49 are 0/22,137; we can't express one | OPEN, corpus-silent |
| D6 | **Miss vs cancel**: zero observed misses (42/42 FINISHED paired with damage) | OPEN, corpus-silent |
| D7 | **Knockdown**: GV_KNOCKED_DOWN=63, ANIMATION 22/23/28 defined, never sent by us; retail shape unknown | OPEN, corpus-silent (check D3's mining — PvP had warriors) |
| D8 | **Mid-cast death**: `kill_player` never cancels `pending_casts` (absence-of-code, confirmed 2026-08-30); retail's behavior on a caster dying mid-cast unknown | BUG-CANDIDATE + corpus question — the PvP captures held deaths |
| D9 | **Movement policing during aftercast** (CASTMECH-P5): we apply movement whenever it arrives | KNOWN divergence, unpoliced |
| D10 | **Property 8's full state machine**: a live E3 carried 8→0 (`castmech` §3f) contradicting §3c's "never"; unresolved | CONTESTED |
| D11 | **Property-8 return-to-ready**: the one client-side effect the static read predicts (250-unit deferral) that no run has ever looked at | UNVERIFIED |
| D12 | **Burrow stale swing timer**: `swing_lands_at`/`cast_lands_at` survive a burrow remove/recreate cycle; no test covers it | BUG, confirmed still present 2026-08-30 |
| D13 | Aftercast per-skill sweep vs the wiki's exception lists (CASTMECH-P4) | DEFERRED, needs skilltable regeneration |
| D14 | Quarterstepping/swing-gate re-press model (CASTMECH-M4/P3) | INFERRED, unrun |

Rows D2/D3/D4 are answerable **from disk today**. That is the arc's first move.

**R1 UPDATE (2026-08-30, [FINDINGS.md](FINDINGS.md)):** D1's law is DERIVED
(windup = interval/2 − 0.1 s — the E5 rides it for melee attack skills too);
D2 is ANSWERED at n=1,042 (the "constant ratio" itself was the artifact);
D3/D4 are ANSWERED (the form rule: channel follows the target, 758/758 — both
our send sites break it); D6 MOVED (7 landed-no-damage misses found; a miss is
FINISHED-without-damage, a cancel is 3); D7 has corpus witnesses (prop 63 ×3);
D5 confirmed corpus-silent (35 at 0/all) — decode-only. NEW divergences:
**D15** player cast sends A0-with-target-0 (a form retail never uses),
**D16** melee attack-skill finish should carry 46+damage at E5 (we never send
46/49), **D17** the instant-skill family (prop 48, one-batch cycle) is absent
from our wire.

## 3. The ladder

| Rung | Deliverable | Acceptance | Status |
|---|---|---|---|
| **ANIMREF-R1** | The episode extractor + the retail referent. `toolkit/authsrv/animgrammar.py` (+ test): walks every LIVE capture via `vaultpath`/`origin` (refuses to pool origins), extracts every cast episode (property-60/50-opened, any agent; E4-opened for self) and every swing episode (property-4-opened) as ordered event lists with dts; emits per-episode JSONL to `vault/research/animref/` and a grammar census | POSITIVE CONTROL: reproduces castmech's pinned figures on the overlap (the 6 E-cycles' gaps, 7 E4s, the 4/4 cancel burst). NEW: player windup at bench-capture scale (D2), other-agent cast grammar (D3/D4), swing census beyond n=42 | ✅ **2026-08-30**, `a26d7b6` (extractor, control 7/7) + the test commit; results in [FINDINGS.md](FINDINGS.md) — the windup LAW (`interval/2 − 0.1 s`, replaces the ratio), the cast-open form rule (758/758), the attack-skill trio at scale, the instant-skill family, 7 misses, props 22/23/28/63 live, 45 at n=79 |
| **ANIMREF-R2** | The same extractor over OUR wire (gamesrv `.jsonl` corpus + loopback capture `20260823T101329`), plus a `--diff` mode: missing/extra events, order flips, timing-law residuals, per row retail-count vs ours-count | KNOWN-BAD CONTROL: the diff over pre-castmech gamesrv logs must flag the divergences castmech fixed; a diff scoring old and new wire alike measures nothing | ✅ **2026-08-30**, same session ([FINDINGS §9](FINDINGS.md)): control PASSES on the pre-castmech era; current era VALIDATES the self grammar signature-for-signature and yields **D18** (the +~25 ms tick tail on landings, recorded) and **D19** (NPC casts were open-only — 0 finishes vs retail's 709 — FIXED: `land_skill` opens its batch with `[58, agent, 0]`) |
| **ANIMREF-R3** | Fixes derived from R1's referent, shipped default-ON, one revert flag each, tests in the same commit. First: D1 (attack-skill E5 = begin + windup×modified-interval — the law the Power Shot data already states). Then whatever R2's table surfaces, in derivation order, never tuning order | each fix cites the referent rows that derive it; suite floors updated | 🔶 **four landed 2026-08-30**: the windup law (`fc24bd2`, `--windup-ratio` reverts), the cast-open form rule at all three send sites (`5a8907e`, `--legacy-cast-form`), the attack-skill E5 riding the weapon windup (`ef7c268`), and R2's D19 — the NPC cast finish `[58, agent, 0]`. Remaining rows need R4's decode first (effect-props 20/21, scripted-anim 22/23/28, interrupts) — do not wire blind |
| **ANIMREF-R4** | The corpus-silent behaviors (D5/D6/D7/D8), decoded not invented: client-handler reads first (the skillcast §16 seven-switch map places the ids); where decode can't settle it, ONE pre-registered live capture ask (secondary account, marks plan, all four questions in a single session). No campaign | the ask names its predictions before the run | ✅ **2026-08-30** ([FINDINGS §10](FINDINGS.md)) — **decode-complete, wire-nothing**, which is the rule working. Props 20/21 reach AgentView event **kind 9** (a real on-body visual the `0x0042`/`0x0044` buff opcodes do not draw) but their VALUE is not the skill id — it is an unread visual-component id space, so wiring means inventing ids. Props 35/63 are one call `0x007E0490(agent, duration)` differing only in fixed `0.4f` vs wire float (corpus 2.0 s, n=3) — decoded, but we have no interrupt or knockdown mechanic to attach them to. Prop 45 is excluded from the cast register (tail-jumps `0x0047F480`, agent-only). **No live-capture ask is needed** — the decode answered every question the ask would have posed |
| **ANIMREF-R5** | ONE caged loopback acceptance look (castmech's own NEXT item, never run): the client consumes the full derived grammar without asserting; the property-8 hold's return-to-ready deferral (D11) observed or refuted | single run; animation verdicts are the owner's (fixed-position HUD readouts may be agent-piloted) | 🔶 **STAGED 2026-08-30 — [RUN-R5.md](RUN-R5.md)**, pre-registered P1–P8 with refutations, one bounded command (`--enemy --hold 240 --shots 15`), six owner actions, ~6 min. The wire half is scored offline afterwards by `animgrammar.py --diff`; the owner is asked only for what a capture cannot hold. **P1 is the run's point**: the form rule moved targetless self casts to `0x009F`, and only eyes can catch "more correct wire, visibly worse game" |

D12 (burrow timer) and D8's code half are ordinary bugs, not rungs — fix when touched or
spin off. D13/D14 stay parked behind the rungs above.

## 4. Standing cautions inherited by this arc

- **Origin discipline**: live and ours are never pooled; `origin.py` is the gate; the
  `selftest/` tree is excluded from every walk. Corpus counts are FLOORS — pin a
  signature set and re-scan as-of-pin before calling a moved number drift.
- **Sample-and-hold / denominators**: score on the event stream's own timestamps; every
  rate names its denominator; a filter that drops malformed episodes must COUNT them.
- **A check that cannot fail is not a check**: every census section declares a
  `checks.py` floor; the diff runs its known-bad arm.
- **The gamesrv `t` clock**: `wall_unix` is the full-resolution instant; `wall` is
  truncated (`authsrv.py` REALFIX-T1 comment). Use `wall_unix` for cross-stream joins.
- **Owner minutes are scarce**: R1–R3 ask for none. R4 asks once, R5 once.

## 5. Open questions

- **ANIMREF-Q1**: does retail's other-agent cast burst carry a target field (D4), and
  does the property-8 bracket appear for NPCs the way castmech saw on agents 725/176?
- **ANIMREF-Q2**: what does retail send when a caster dies mid-cast (D8)? Check R1's
  episode output for a death-terminated cast before asking for any run.
- **ANIMREF-Q3**: the property-8 deferral's clock unit (250 of WHAT — skillcast §16.2
  left it open). A disassembly question, not a run question.
- **ANIMREF-Q4**: whether the model-file sequence semantics (`studies/anim` — n3C tags
  unread) are needed at all for wire fidelity. Working assumption: NO — the client picks
  its own animation from property 60/50 + skill id; revisit only if R5 shows a
  wrong-animation (not wrong-timing) defect.
