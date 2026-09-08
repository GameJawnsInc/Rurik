# RUN-1zAB — the keyboard lead under its four gates: is the body FREE?

**One question, one arm, ~90 seconds of client time, no human aiming.**
Registered before the run, per the probe rule. This is the run
`studies/movecode/FINDINGS.md` §1z-u.5 named as the last step before `--kbd-lead`
can be argued for as the default, and §1z-ab confirmed as the only step left.

Behaviour under test: `MOVECODE-1z-t` term 1 (`--kbd-lead`, 520 u) composed with the
four gates built for it — §1z-y (a rate-refused re-aim HELD and re-baked at the
floor; an in-flight lead KILLED on a press or a click), §1z-z (the lead grant's
field 4 MATCHED to field 3), §1z-aa (no lead into a fence the server shut with a
`0x002C`) — and §1z-ab's length (520 unchanged). Everything else is the shipped
default of `main` at `a0fc059` or later: the router, the plane repair, the AgTrack
guard and its re-pin, the stop echo, the family rate.

**Status: RAN TWICE. 2026-09-03 18:39 INCONCLUSIVE; the 19:12 rerun on the fixed
detector **REFUTES** — the lead armed REALFIX §0.11's lock on five of eight legs.
Both result blocks are below; `--kbd-lead` stays OFF.**

---

## ★ RESULT — RAN 2026-09-03 18:39, **INCONCLUSIVE** (agent-driven, hands off)

`agenttap-20260903T183943` / `authsrv-20260903T183941-c1` / harness `20260903T183905`.
Full record: `studies/movecode/FINDINGS.md` §1z-ac.

| §2 required | measured |
|---|---|
| p50 < 150 u | **1.0 u** ✅ |
| per-leg travel scales with hold | W 1,062 / 1,155 / 1,045 u (5 s), S 543 / 677 (4 s), Q 620, E 589 (3 s) ✅ |
| the detector reads FREE | **MIXED** ❌ |

**⇒ INCONCLUSIVE by this sheet's own bounds, and the bar is not moved after the fact.**
Not REFUTED: nothing read ENSLAVED, no held-key leg parked, no new warp class. Exposure
well over floor (5,869 u over 278 moving samples; 22 `KBD LEAD`; 13 lead legs ≥ 300 u).

**The MIXED was 88 % instrument.** As shipped the detector flagged 50 of 278 samples;
44 of them are a FREE body whose own co-directional target sits 0.53 u from our grant —
inside `GRANT_EPS` — because the 520 u length was derived from the client's own report
chord. The decode separates them (a grant with the fence open writes world-0 ONLY), so
enslavement is the drawn copy's target being **bit-identical** to world-0's, and that
discriminator shipped as §1z-ac: RUN-1zT stays ENSLAVED 113/114, this run re-reads
**6 of 278 (2.2 %)**, seven of eight legs FREE.

**The residual six are real: the lead maturing.** On the Q leg the drawn body reached our
520 u endpoint and parked for one sample before the next grant re-aimed it — 520 / speed
is within 0.01 s of the report gap in all three families, so maturation and the re-aim are
a photo finish. Cost ~26 u and one sample of stall. **No lock**: every release was reported,
the body stopped where the player let go (385 u and 34 u short of our grant), no `0x002C`,
no re-pin fire, max separation 155.6 u.

**Gate exposure, reported not assumed:** HOLD fired 12 (`deferred-heading` re-bakes); KILL
and FENCE GATE had **zero exposure by the script's construction**; `agtrack_repin blocked
arrival-risk` ×6 as §1z-ab.5b predicted. Enemy control p50 0.6 / max 63.6 u.

**`--kbd-lead` stays opt-in.** The registered confirmation did not land, and the only
failing clause was an instrument defect now closed — a rerun on the fixed detector is the
owner's call, not a session's.


---

## ★ RERUN — registered 2026-09-03 before launching, on the §1z-ac detector

Same script, same build, same flags, verbatim. The only change is the instrument:
the enslavement test is now the two world targets being **bit-identical**
(§1z-ac), not the body's target being within `GRANT_EPS` of the grant.

**Why rerun at all.** The first run's only failing clause was scored by an
instrument with a known false positive, and the fixed instrument has never been
exercised on a capture it did not help produce. A second sample also puts a
number on the maturation photo finish, which is a per-leg coin flip by
construction.

**The original bounds in §2 stand and are NOT relaxed.** FREE confirms, ENSLAVED
refutes, MIXED is inconclusive. What follows is an additional prediction, so a
MIXED result cannot be talked into agreeing with §1z-ac afterwards.

| registered before the run | |
|---|---|
| **Expected verdict** | FREE, or MIXED **under 5 %** — the first run read 2.2 % on the fixed detector |
| **Every flagged sample will be a MATURATION PARK** | both copies bit-identical, the body **resumes** on the next grant, and that leg's release is **reported** |
| **Which legs** | the flagged leg(s) will differ from the first run's (Q strafe) — maturation vs the re-aim is a photo finish, 520/speed within 0.01 s of the report gap in every family |
| **p50** | under 150 u (first run 1.0 u) |
| **Travel scales with hold** | W ≈ 1,050–1,155 u at 5 s, S ≈ 540–680 at 4 s, Q/E ≈ 590–650 at 3 s |
| **REFUTES the §1z-ac reading** | any flagged run whose leg has an **unreported release**, or a held-key leg moving ≤ 50 u, or travel not scaling — that is the lock, not a park |
| **REFUTES the fix** | ENSLAVED (≥ 25 %) |
| **Would surprise me** | 0 flagged samples on every leg — the photo finish says maturation should win sometimes |

**Exposure floors unchanged** (§3): 500 u over 20 moving samples, ≥ 8 `KBD LEAD`,
≥ 3 lead legs ≥ 300 u. KILL and FENCE GATE again have zero exposure by the
script's construction and are reported as zero, not as passes.

### ★★ RERUN RESULT — RAN 2026-09-03 19:12, **REFUTED**

`agenttap-20260903T191321` / `authsrv-20260903T191320-c1` / harness `20260903T191246`.
Full record: FINDINGS §1z-ad.

| registered above | measured |
|---|---|
| REFUTES the fix: ENSLAVED ≥ 25 % | **ENSLAVED, 29 of 60 (48.3 %)**, onset 15.40 s |
| REFUTES the §1z-ac reading: a held-key leg ≤ 50 u, or an unreported release | **five of eight legs parked** (35, 0, 0, 0, 0 u); **1 reported stop for 7 key legs** |
| expected FREE or MIXED < 5 %, every flag a maturation park | wrong on both counts |
| travel scales with hold | fails — 1,347 u total against run 1's 5,869 u |

**The door, to the second.** Not a `0x002C` and not a dropped re-aim: **a lead matured
while the key was still held.** The 16.80 s lead was 520 u of backpedal, unclipped, so it
matured at 16.80 + 520/190 = **19.54 s**; the player released `S` at **19.80 s**, 0.26 s
too late. No `0x0047` was ever sent, the next report came back at our lead's endpoint
exactly, and the client stayed locked for the remaining five legs while still reporting
`mt` 7/8/4 — keys pressed, body still. That is REALFIX §0.11 stage 2 verbatim.

**No gate covers this.** The FENCE GATE only acts on a fence *we* shut (it worked
correctly afterwards, degrading four leads to `ZERO LEAD (fence-shut)`); the HOLD and the
KILL had zero exposure. The arming path — a lead maturing unanswered with the fence open —
is uncovered.

**§1z-ac's "~26 u and no lock" is corrected**: the maturation park and the lock are the
same event, and run 1 merely won every coin flip. **`--kbd-lead` stays OFF.**


---

## ★★ THE ARMER RUN — registered 2026-09-03 before launching (MOVECODE-1z-ag)

`movetap.py` reads AgTrack's `clientControlled` dword directly; `agenttap` cannot see
the fence at all (§1z-aa.1). Four scored `--kbd-lead` runs have locked three times and
§1z-af left the armer **UNIDENTIFIED**, so this run points the one instrument that can
see the fence at the one arm that locks. Same script, same flags, `--kbd-lead`, refresh
OFF (its shipped default since §1z-af).

**The question:** what shuts the fence on the keyboard lead path, now that §1z-z has
killed §0.11's plane route?

| registered before the run | |
|---|---|
| **Exposure floor** | the run must LOCK (a parked held-key leg, or stops < 7 of 7). Three of four prior runs did. **No lock = this measured nothing about the armer**, and I say exactly that rather than reading a null |
| **The fence flips open→shut ONCE and stays shut** | §0.11 measured 351/325 subsequent samples with no re-arm |
| **§0.11's fingerprint REPRODUCES on this arm** | at the shut sample `async_reqtoken` — the keyboard walk-start applier's own token — resets to 0 and stays 0, while `mode`/`speed`/`stop` keep re-arming normally |
| **A position snap rides the same sample** | §0.11 saw ~15 u |
| **The plane words are ALREADY equal before the shut** | §1z-z matches field 4 to field 3 on this path, so §0.11's L1 trigger ("the drawn body's plane word catches up to the sync copy's") should not be available. **If the plane words DO converge at the shut edge, §1z-z's armer-kill is not reaching this path** — that is a finding about the fix, not about the client |
| **No server message rides the shut edge** | neither a `0x0029` nor a `0x002C` within one sample either side. Our own `0x002C` is already modelled by §1z-aa's tracker, so if the armer were ours the tracker would have caught it |
| **Would re-open the arrival reading** | if the shut edge sits at the in-flight lead's own `+0x48` instant, the arrival IS a route after all and §1z-af.3's "not sufficient" needs qualifying to "not the only one" |

**Not a fix run.** Nothing is being tested; this is an instrument pointed at a named
unknown, and its output is a mechanism, not a verdict.

---

## 1. The question

> With the four gates on, does the keyboard lead keep the client's WORLD-0 copy
> near the body BECAUSE world-0 follows the body — not because the body has been
> enslaved to world-0?

RUN-1zT asked only the first half and read p50 0.0 u; §1z-x's detector then read
that capture ENSLAVED from 17.77 s (115 of 193 moving samples), and §1z-u made the
lead opt-in. The number is not the verdict; the detector's verdict is.

## 2. The prediction, registered

| | |
|---|---|
| **Prior, same script, no gates** (`agenttap-20260903T073122`, RUN-1zT) | ENSLAVED, 59.6 %, onset 17.77 s; p50 0.0 / max 198.9 u |
| **Prior, zero-lead default** (`agenttap-20260902T213401`) | FREE, 0 of 130; p50 237 / max 516 u |
| **CONFIRMS** | `w0score` verdict **FREE** for the whole capture, **and** world-0 vs body p50 **< 150 u**, **and** every held W/S/Q/E leg's body travel scales with its hold (a W:5 leg ≈ 1,300–1,440 u, an S:4 leg ≈ 700–760 u — not ~520 u regardless of hold) |
| **REFUTES** | **ENSLAVED** at any onset, or any held-key leg that moved the body ≤ 50 u (HELD KEY, BODY PARKED) |
| **INCONCLUSIVE** | MIXED (the detector's 15 % bar), or exposure under the floor in §3 — say so, do not round |
| The decode says | no arrival can snap in cruise or at a turn under the hold (§1z-ab.2); the copy has 0–14 u to go at each cruise re-aim (§1z-ab.3) |

**Not a scoreboard and not a length sweep.** If it refutes, the length is not
tuned (§1z-ab.4): the rows in §5 localise WHICH door opened, and the first enslaved
sample is where to read.

## 3. The exposure floor — this run can fail by measuring nothing

- `w0score` refuses a verdict under **500 u** of body translation across **20**
  moving samples (RUN-1zT had 3,572 u over 193).
- The wire must carry **≥ 8 `KBD LEAD`** grants (RUN-1zT: 12 fired, 3 refused,
  7 `KBD SPEED-TRUTH`, 1 `KBD STOP-ECHO`) — under 8 the lead was barely on the
  wire and the verdict is about something else.
- `leadmargin --tap` must find **≥ 3 lead legs ≥ 300 u** for the maturation
  reading.
- **A and D turn in place; Q and E strafe.** The walk is W/S for translation and
  Q/E for strafe for that reason, and it includes backpedal so a non-1.0 family
  occurs (world-0's speed set must contain 190, as it did on RUN-1zT).

**The gates' own exposure is reported, never assumed.** The script has no press
and no click, so the KILL has **zero exposure by design**; the HOLD fires only
if a re-aim is rate-refused (RUN-1zT: 3); the FENCE GATE fires only if a `0x002C`
lands during a walk (RUN-1zT: one `AGTRACK RE-PIN` at 12.93 s). A zero in §5's
census is zero exposure for that gate, not a pass for it.

## 4. The run

**Announce it first — the machine is shared and `Gw.exe` fights for input focus.**
Pre-flight on 2026-09-03: nothing bound on 6112/6601, no `Gw.exe` running, the
build is `ours` (`dhbuild.py`), the scorer's positive control passes.

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> **`--walk` drives every keypress. The script's own presses ARE the arm.** The
> run opens with `wait:3` and the character stands still — it is not waiting for
> you. A helpful press produces a double-driven regime (RUN-1zT's first attempt:
> 720 u of travel no script asked for, max separation 854 u). There is nothing
> to do while it runs but watch — and it needs no human aiming, so it does not
> have to be handed over at all (§8).

**Terminal A — the scorer's control, then the tap.** The tap waits for a client
to reach a map, so starting it early is free.

```powershell
python toolkit/clientscan/w0score.py --baseline
```

Must print `[PASS] control reproduces: live p50 237.0 / max 516.1`, `the zero-lead
baseline reads FREE` and `RUN-1zT's registered arm reads ENSLAVED from 17.77 s`.
If any of the three is missing, stop: the detector cannot find the known
contamination and cannot clear a new run.

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

**Terminal B — the session.** The same script as RUN-1zT, verbatim, plus one
flag. Total ≈ 90 s from launch to the window closing; nothing is left parked.

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

`--exe` is not optional (every address in this arc is build 38797).
`--enemy-hit 0.02` keeps the Hatcher chasing without killing the player.
**Do not add `--resync`**: its model holds the client at its last report and reads
a whole lead of separation on every leg (§1z-ab.3 ii).

**Watch the gamesrv console for the banner.** It must say all of:

```
[map] MOVECODE-1z-t KBD_SYNC ON by default -- ...
      TERMS LIVE  lead 520 u + navmesh clip, 0x002B family rate, 0x0047 stop echo
      1z-y GATES  rate-refused re-aims HELD and re-baked at the floor, an in-flight lead KILLED on press/click by a zero-lead grant at the body, the lead grant's field 4 MATCHED to field 3 (the 0.11 armer-kill), no lead into a fence we shut with a 0x002C (the fence-shutter audit)
      THE LEAD IS ON (--kbd-lead) -- an OPT-IN arm since 1z-u ...
```

If `1z-y GATES` names fewer than four, or `TERMS LIVE` fewer than three, the run
is a diagnostic arm and not this sheet's — say so.

## 5. Scoring

Three commands, all read-only, in this order.

```powershell
python toolkit/clientscan/w0score.py --legs vault/captures/harness/<stamp>/report.json
```

The verdict against §2 (FREE / MIXED / ENSLAVED with the onset), the separation
number, the per-leg table with each leg's travel against its hold, and the two
speed sets. The newest tap and the gamesrv capture whose wall span overlaps it
are found by default.

```powershell
python toolkit/clientscan/leadmargin.py --tap vault/research/animref/agenttap-<stamp>.jsonl
```

The maturation reading per lead leg: distance still to go when the re-aim
landed, any park and its length, separation. §1z-ab predicts 0–14 u to go in
cruise and no park over one 33 ms sample.

```powershell
python studies/movecode/review/gatecensus.py
```

The gates' rows from the newest gamesrv capture: the heading arm's verdicts with
`lead_src` / `lead_clip_why` (a `fence-shut` row is the 1z-aa gate degrading a
lead), the held re-aims, the kills, the fence re-arms, every AgTrack guard row,
every `0x002C` by sender, and the wire labels. §1z-ab.5b predicts
`agtrack_repin blocked arrival-risk` about once per cruise leg — a `due` or a fire
with that reason is the guard's keyboard-glide gap firing live, and is reported
as such whatever the verdict.

## 6. What each outcome means

- **CONFIRMED (FREE, p50 < 150, travel scales with hold).** §1z-t's confirmation
  is restored on a clean read and the lead's four gates held under the shipped
  composition. Whether `--kbd-lead` becomes the default is then `PLAN.md` §7
  Q13's bundle question for the owner, with this capture as its evidence. Next
  is `0x005FCAA0`.
- **REFUTED (ENSLAVED).** Read the first enslaved sample's time and the rows
  around it in §5's census: a `0x002C` before it names the shutter and whether
  the gate degraded the next lead; a `heading_hold` re-bake before it is the
  hold's residual (§1z-ab.5a); an `agtrack` `snap` or `veto` before it is a
  gate-1 evaluation the decode said could not happen — that refutes §1z-ab.2,
  which matters more than the verdict. The length is not tuned.
- **INCONCLUSIVE (MIXED or under floor).** Say so. A second identical run is the
  only follow-up; no parameter moves.
- **The enemy control** (agent 10's two copies) should stay small (p50 5.2 / max
  27.9 on RUN-1zT); a change there is a separate finding.

## 7. Honest limits, before the fact

- **n is one map, one route, one build.** It is the same route as RUN-1zT, on
  purpose: the comparison is per leg on identical input.
- **Two of the four gates cannot fire here** by the script's construction (the
  kill needs a press or click; the fence gate needs a `0x002C` during a walk).
  Their absence in the census is not evidence for them.
- **The route has no wall.** The clip's wall behaviour (§1z-ab.3 iii) is not in
  play; a clipped lead's early park is unmeasured by this run.
- **This run cannot price the click path.** Nothing here clicks.

## 8. Who should drive this

**Nobody needs to aim, so it does not have to be handed over.** Every input is
scripted, the tap sends nothing (read-only `ReadProcessMemory`), and the session
closes itself. The repo's boundary is aiming, not seeing. RUN-1zT §8 records what
handing it over cost. The session that set this up can drive it on a go-ahead
(the machine is shared: the launch is announced first, ≈ 90 s of client time,
the window closes on its own). If the operator would rather watch, §4's block
says the one thing there is to do.
