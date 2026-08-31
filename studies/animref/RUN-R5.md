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
| NPC cast finish `[58, agent, 0]` | ✅ presence + batch order (**already green**, R2's diff) | deferred — the Hatcher's bar is emptied for this run, §2b |

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
| ~~P6~~ | ~~The Hatcher returns to its ready stance at cast end (the new prop-58)~~ | **NOT OBSERVABLE THIS RUN** — `--no-enemy-skills` empties the Hatcher's bar, so it never casts (§2b). Its wire half is already green from R2's offline diff; re-runnable in a minute by dropping the flag |
| P7 | **No assert dialog, no disconnect, for the whole session** | any `Assertion:` box — capture the text verbatim, it names the file and line |
| P8 (D11, exploratory) | after a cast ends there is a **brief hold before the body is ready again** (the property-8 250-unit deferral, `skillcast` §16.2) | nothing distinguishable — records as NOT OBSERVED, which is a real answer for a hedged static read |

P4 and P8 are the two where "no difference" is the *expected* answer; they are
here so a null is recorded as a null rather than read as a failed run.

## 2. The run

**One command.** PowerShell, from `C:\gd\Rurik` (main — the fixes are merged).
It brings the stack up, drives the client into an explorable map, then holds for
four minutes while the owner plays, screenshotting every 15 s.

```powershell
python toolkit/harness/session.py --enemy --hold 240 --shots 15 --game-args "--map 146 --explorable --no-enemy-skills --skills 105,153,148,322"
```

Every argument, and why:

- **`--map 146 --explorable`** — Lakeside County. **Guild Wars forbids attacking
  and casting in a town**, and the default spawn is an outpost, so without this
  the run cannot produce P1–P5 at all. 146 is the map `authsrv.py`'s own `--map`
  help calls "explorable and therefore the first place combat can be tested";
  `--explorable` forces the map-type byte with it, which is the pairing the
  CANCELWALK cast runs used. The hostile is placed **relative to the player's
  arrival point** (`content/world.toml`: "300 units east … in any Guild Wars
  map"), so changing the map does not lose it.
- **`--no-enemy-skills`** — the Hatcher's bar is emptied: it swings and casts
  nothing. Built for this run (`test_agentlife` §4b pins both halves: casts
  nothing, and still swings). **This costs P6** — see §2b.
- **`--skills 105,153,148,322`** — the bar the run needs, because the default
  bar is all instants (types 14/15/16 and stances at activation 0.00) and
  **cannot produce a cast animation at all**:

  | slot | id | what it is | why it is here |
  |---|---|---|---|
  | 1 | **105** | foe spell, 2.00 s cast, 0.75 aftercast, 6 s recharge, 10 energy | **P2**, and it is the very skill castmech measured retail's own cycles on — the comparison is direct, not analogous |
  | 2 | **153** | foe spell, 1.00 s cast, 8 s recharge | 105's live-corpus partner; a second, shorter targeted cast |
  | 3 | **148** | **self** enchantment, 2.00 s cast, 5 s recharge, 5 energy | **P1** — a self-targeted spell is what makes the client send target 0, which is the untargeted-form path the whole run exists to check |
  | 4 | **322** | attack skill, activation **0.00**, 3 s recharge | **P5** — a zero-activation attack skill is exactly the branch the E5 fix added |

  Cross-profession is fine and **proven, not assumed**: the CANCELWALK runs cast
  105 and 153 repeatedly on this same default Warrior character
  (`studies/movement/CANCELWALK.md` §5 and §8.3f use `--skills 105,153,322`), so
  the client does not gate casting on profession. Ids 105/153/148 are profession
  4's; 322 is the default bar's own.
- `--enemy` spawns the hostile; it engages on its own (300 u out, aggro 1200).
- `--hold 240` **bounds the run** — the session tears itself down four minutes
  after the map verdict, so no window is left parked
  (`[[feedback-bound-the-client-run]]`).
- `--shots 15` screenshots during the hold, so reaching for a screenshot key mid
  fight is never necessary.
- **Not** `--practice-target`: it stops the hostile chasing *and* attacking,
  which would delete P3's NPC half and P4.
- No `--account`: loopback uses the synthetic credential, no real account. The
  launch is caged and loopback-only by the DH binding
  (`cage.assert_launch_safe`) — nothing here points at ArenaNet.

**This is a test launch of the patched loopback client**, announced per
`[[feedback-announce-harness-launches]]` since the machine is shared.

**Confirm before playing:** the gamesrv banner must print
`ENEMY BAR: EMPTY` — if it does not, the bar is still loaded and P6's absence
below is not what you are looking at.

### 2b. What emptying the Hatcher's bar costs, stated

**P6 cannot be observed this run.** P6 was the NPC cast finish — the fourth
shipped fix (`land_skill` now opens its landing batch with `[58, agent, 0]`,
where retail closes 709/709 other-agent casts with a 58-led batch). With an
empty bar the Hatcher never casts, so nothing exercises it.

That is an acceptable trade and not a silent one: **the fix's wire half is
already validated offline** (R2's diff, FINDINGS §9 — our era had 0 finishes
against retail's 709), and what P6 would have added is only the *visual*
confirmation that the caster returns to its ready stance. It is re-runnable in
sixty seconds whenever wanted — the same command with `--no-enemy-skills`
dropped — and is better done separately anyway, since a casting Hatcher is the
thing that makes the player's own cast observations noisy. **P8's NPC half goes
with it**; P8 can still be attempted on the player's own casts.

## 3. What the owner does in those 4 minutes

Six actions, in order. Nothing is timed; each need happen only once.

1. **Let the Hatcher reach you and swing a few times.** Watch *its* swings
   (P4), and whether its damage lands mid-swing (P3's NPC half). It will only
   ever swing now — no casting.
2. **Attack it back** (click it). Watch your own swing: does the number land
   mid-animation (P3)?
3. **Press slot 1 (skill 105) with the Hatcher targeted** — a 2-second cast,
   the most visible animation on the bar (P2).
4. **Press slot 3 (skill 148) with NOTHING targeted** — click empty ground
   first to clear the target, then press it. It is a self-enchantment, so it
   needs no target. **This is P1, the run's whole point.** Does your character
   perform a cast animation?
5. **Press slot 4 (skill 322)** with the Hatcher targeted (P5) — does the
   strike connect at the strike, or instantly on the keypress?
6. **After any of your own casts ends**, watch whether the body holds briefly
   before it is ready again (P8, exploratory — "no difference" is a real
   answer here).

If the client asserts at any point, that is P7 and the run is over — the dialog
text is the result and is worth more than the rest of this sheet.

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
- **Using `--practice-target`** (stops the hostile chasing and attacking, which
  kills P3's NPC half and P4).
- **Forgetting `--map 146 --explorable`.** In an outpost the game refuses
  attacks and casts outright, and P1–P5 all evaporate — this is the correction
  that produced this version of the sheet.
- **Reading P6's absence as a failure.** It is designed out of this run (§2b),
  not broken.
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
