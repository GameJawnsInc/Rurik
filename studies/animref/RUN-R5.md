# ANIMREF-R5 — the acceptance look. ONE caged loopback run, pre-registered.

**Status: STAGED, not run.** Written 2026-08-30 after R1/R2/R4. This is the
whole ask: **one session, ~6 minutes of the owner's attention**, no campaign, no
A/B, no repeat. It is the single verbatim check of a derived object that
`[[derive-dont-iterate]]` permits — four wire behaviours were derived from the
retail corpus and shipped default-ON without a client ever seeing them, and this
run is where a human confirms the client agrees.

Everything the wire can answer is scored **offline afterwards, by me, from the
run's own capture** — the owner is asked only for what a capture cannot hold:
what the bodies on screen actually did.

---

## 0. Why this needs eyes at all (and what it does NOT need)

Per `[[feedback-owner-drives-client-runs]]` the boundary is **aiming, not
seeing** — but this run's verdicts are *model-appearance* verdicts, which sit on
the owner's side of that line regardless of who drives. Four fixes changed what
the client is told about animation, and none of them has been seen:

| shipped fix | wire-scoreable offline? | needs eyes? |
|---|---|---|
| windup law `interval/2 − 0.1 s` | ✅ timing in the capture | ✅ does the hit land mid-swing |
| cast-open form rule (9F/A0) | ✅ channel per open | ✅ **does the animation still play** |
| attack-skill E5 rides the weapon | ✅ E4→E5 gap | ✅ does the strike look timed |
| NPC cast finish `[58, agent, 0]` | ✅ presence + batch order | ✅ does the caster return to ready |

**The one genuinely risky change is the form rule.** It moved targetless self
casts from `0x00A0`-with-target-0 onto `0x009F`. If the client's untargeted path
does not animate the local player, we will have made the wire more retail-correct
and the game visibly worse — a "more correct, looks broken" outcome that only a
person can catch. (Pre-registered expectation: it animates. Retail sends exactly
this form for the observing player's own agent **8 times across 3 captures**,
skills 1 and 814 — FINDINGS §2. That evidence is why this is a check and not an
experiment.)

## 1. Predictions, stated before the run

House rule: a probe with no stated expectation can be rationalised into agreeing
with anything. Each line names what refutes it.

| # | prediction | REFUTED IF |
|---|---|---|
| P1 | A targetless self spell **plays its cast animation** (the 9F form) | the body stands inert while the bar/energy still react — the form rule is wrong for self and `--legacy-cast-form` goes back on |
| P2 | A **targeted** spell animates exactly as before (A0 form, unchanged) | it differs from P1's case in any visible way other than facing |
| P3 | The player's auto-attack **hit lands mid-swing**, not at the swing's start or end | damage numbers appear at the animation's first or last frame |
| P4 | The Hatcher's swings look **unchanged** in rhythm (0.593 → 0.565 s windup is a 28 ms shift — below what an eye resolves) | the owner can *see* a difference; that would mean something other than the windup moved |
| P5 | An attack skill's strike **connects at the strike**, not instantly on press | the number appears the instant the key goes down |
| P6 | The Hatcher **returns to its ready stance at cast end** (the new prop-58) rather than holding the cast pose until its next action | it holds the pose, or the stance change is visibly late |
| P7 | **No assert dialog, no disconnect, for the whole session** | any `Assertion:` box — capture the text verbatim, it names the file and line |
| P8 (D11, exploratory) | after a cast ends there is a **brief hold before the body is ready again** (the property-8 250-unit deferral, `skillcast` §16.2) | nothing distinguishable — records as NOT OBSERVED, which is a real answer for a hedged static read |

P4 and P8 are the two where "no difference" is the *expected* answer; they are
here so a null is recorded as a null rather than read as a failed run.

## 2. The run

**One command.** PowerShell, from `C:\gd\Rurik` (main — the fixes are merged).
It brings the stack up, drives the client to the map, then holds for four
minutes while the owner plays and screenshots every 15 s.

```powershell
python toolkit/harness/session.py --enemy --hold 240 --shots 15
```

- `--enemy` spawns the standing hostile (it engages on its own — 300 units out,
  aggro 1200), which is what produces P4's and P6's material.
- `--hold 240` **bounds the run**: the session tears itself down 4 minutes after
  the map verdict. It will not park a window on the screen — no `--keep-open`
  without a bound (`[[feedback-bound-the-client-run]]`).
- `--shots 15` writes periodic screenshots, so reaching for a screenshot key is
  never necessary mid-fight.
- **Not** `--practice-target`: that makes the hostile neither chase nor attack,
  which would delete P4 and P6 outright.
- No `--account`: a loopback run uses the synthetic credential, no real account.
- The launch is **caged and loopback-only** by the DH binding
  (`cage.assert_launch_safe`); nothing here points at ArenaNet.

**This is a test launch of the patched loopback client** — announcing it per
`[[feedback-announce-harness-launches]]`, since the machine is shared.

## 3. What the owner does in those 4 minutes

Six actions, in order. Nothing is timed; the point is that each happens once.

1. **Let the Hatcher reach you and swing a few times.** Watch *its* swings
   (P4) — and whether its damage lands mid-swing (P3's NPC half).
2. **Attack it back** (click it). Watch your own swing: does the number land
   mid-animation (P3)?
3. **Cast a spell with the Hatcher targeted** (P2).
4. **Cast a spell with nothing targeted** — click empty ground first to clear
   the target, then press the same skill. **This is P1, the run's whole
   point.** Does your character perform the cast animation?
5. **Press an attack skill** with the Hatcher targeted (P5).
6. **Watch the Hatcher cast** (it casts from its own bar) and note what its
   body does *at the end* of the cast (P6, P8).

If the client asserts at any point, that is P7 and the run is over — the dialog
text is the result, and it is worth more than the rest of the sheet.

## 4. What I do afterwards, with no further ask

The run writes `vault/captures/gamesrv/authsrv-<stamp>-c*.jsonl`, and the
extractor already reads exactly that:

```powershell
python toolkit/authsrv/animgrammar.py --diff --after <the run's stamp>
```

That scores, offline and unaided: the form rule (`cast_open_forms` — the
`A0_target0` rows must be **0**, where the pre-fix era had 21), the windup law
(residual per declared interval — expect ≈ law + ~25 ms, the D18 tick tail, not
+130 ms), the attack-skill E4→E5 gap against the weapon windup, and the NPC
finish (`spell/other/finished` must be **non-zero**, where the whole pre-run
gamesrv era is 0). The owner's six observations settle P1–P8; the capture
settles everything else.

## 5. What would make this run worthless

- **Running it from the worktree instead of `main`.** The fixes are merged; a
  worktree checkout that is behind would test the old wire and look fine.
  Check with `git log --oneline -1` before launching — it should name the
  ANIMREF-R2 merge or later.
- **Using `--practice-target`** (kills P4/P6, see above).
- **Not clearing the target before action 4** — a targeted cast is P2, not P1,
  and the two are indistinguishable in the report if the target state is
  unrecorded. If unsure whether the target cleared, say so; an ambiguous P1 is
  worth less than an admitted skip.
- **Reporting "it felt different"** for P4 — per
  `[[feedback-make-the-signal-unmistakable]]`, 28 ms is below the eye's floor
  and the honest answer there is "no visible difference", which is what P4
  predicts.

## 6. Known caveats carried into the run

- **D18 (the tick tail)**: our landings run ~25 ms late against the law because
  the world tick is 20 Hz. Expected, recorded, not a fix target here.
- **D20**: a targetless *attack-skill* press produces a form retail never sends
  (prop 50 untargeted). Action 5 targets the Hatcher, so the run does not
  exercise it; do not press an attack skill with no target and read the result
  as a verdict.
- The client may refuse a targetless attack-skill press outright — if action 5
  is attempted untargeted and nothing happens, that is a datum about the
  CLIENT, and it partially answers D20 for free.
