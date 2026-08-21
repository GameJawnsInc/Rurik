# REALFIX — the real warp fix: candidates, harness, one live A/B

Written 2026-08-20 from the round-5 research workflow (five research lanes, three
adversarial skeptic lanes, no client run). The research record with every number's
derivation is [FINDINGS.md](FINDINGS.md) §"2026-08-20, round 5"; this file is the
buildable spec that round produced.

**Identifiers.** `REALFIX-P<n>` = candidate grant policies. `REALFIX-O<n>` = the
invariant's obligations. `REALFIX-C<n>` = the offline harness's calibration gates.
`REALFIX-M<n>` = exposure metrics. `REALFIX-D<n>` = pre-registered predictions,
numbered by candidate. `REALFIX-H<n>` = harness builds. `REALFIX-L<n>` = live runs.
`REALFIX-U<n>` = substrate and instrument gaps. `REALFIX-Q<n>` = open questions.
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

## REALFIX — the buildable spec

**Status: NOTHING HERE HAS BEEN BUILT OR RUN.** Every number cited is from the round-5 research draft above and traces to a lane or a FINDINGS line. Origins are marked; `ours` and `live` are never pooled.

**Read this first, or you will rebuild a refuted thing:** `--stop-echo`, `--heading-grant` and `--client-endpoint` are all built, run and REFUTED (`authsrv.py:1004-1023`, `:1049-1075`, `:1090-1099`). A stop-arm `0x0029` **is** `--stop-echo`. A heading grant at the client's own unclipped endpoint **is** `--client-endpoint`. Neither is a fresh idea.

---

## 1. Candidates

Attachment points are lines in `toolkit/authsrv/authsrv.py` in this tree.

### REALFIX-P2 · `--zero-lead`

Attachment: heading arm `:9625-9878`, as a third named block after `:9843`. **Stop arm `:10235` untouched. Click arm `:9879` untouched.**

```python
# --- heading arm, authsrv.py:9625, inside `if moving:` ---------------------
reported = tuple(values[1]); plane = values[2]; mt = values[4]
u        = unit(values[3])                 # |vec2| ∈ 765.0..768.0, ours+live

# TRIGGER: every 0x003D while moving. This DROPS the shipped gate at :9758
# (`turned or walking is not True`). NAMED VARIABLE #2 -- on click-free play
# that gate opens on only 11.1/24.3/61.2/80.8% of moving reports (ours,
# 182554/182934/100340/173940), a 1.24x-9x cadence delta; on the click-heavy
# refuted runs it is invisible (182652: 193/193, 171153: 447/447).
# It is cheap HERE and only here: a zero-distance grant takes the <=1.0 u
# short-circuit at 0x005FEA92 and dispatches nothing.

if not _heading_grant_ok(state, now):      # NOT _grant_verdict -- see note
    record("rate-limited"); return

send(GAME_SMSG_AGENT_MOVE_DIRECTION, [PLAYER_AGENT_ID, u, mt], ...)   # :9797 already
send(GAME_SMSG_AGENT_MOVE_TO_POINT,
     [PLAYER_AGENT_ID, list(reported), plane, plane], ...)
#   NO lead.   NO clip: a point the client reported STANDING ON is walkable
#              by witness (O5).   NO staleness gate: age 0 by construction.
#              NO straight-shot gate: the segment is zero-length.
#   NO STOP-ARM GRANT. That is --stop-echo and it is REFUTED (:1012-1017).
```

**⚠ `_grant_verdict` must NOT be called from the heading arm.** It is the *click* arm's policy (`:3004-3011`) and its Rule 1 refuses whenever the local-driving latch is younger than `GRANT_LOCAL_WINDOW = 3.0 s` (`:2942`, `:3027-3029`) — a latch the heading arm arms **ten lines earlier**, at `state["kbd_moving_at"] = time.time() if moving else None` (`:9715`). Age ≈ 0.0 on every call, so under `--grant-suppress` P2/P3 would emit **zero** grants and degenerate into P6 wearing a new name. `TESTS.md:3220-3225` independently prices the same window at 87% of one capture's span. **Build `_heading_grant_ok` as a new pure predicate carrying Rule 2 only (`GRANT_MIN_INTERVAL`), with its own reason string, and record refusals to the same telemetry channel.**

### REALFIX-P3 · `--short-lead=<u|adaptive>`

Attachment: same block. **Identical to P2 except one line.**

```python
MATCH_RADIUS = 99.919968     # UNVERIFIED IN-TREE until §2.6 lands. See note.
REFRESH      = 0.30          # our own report cadence p50, ours, click-heavy
LEAD_FIXED   = min(RUN_SPEED * REFRESH, MATCH_RADIUS - 14.0)   # = 86.0 u

def lead(state):
    if MODE == "fixed": return LEAD_FIXED
    return min(766.0, RUN_SPEED * state["report_gap_p50"])      # adaptive arm

L = lead(state)
D = (reported[0] + L*u[0], reported[1] + L*u[1])
send(GAME_SMSG_AGENT_MOVE_TO_POINT, [PLAYER_AGENT_ID, list(D), plane, plane], ...)
#   UNCLIPPED, deliberately -- so P2 / P3 / --client-endpoint differ on ONE axis:
#   lead = 0 / 86 / 766. Adding clip_to_walkable makes it two variables against
#   BOTH neighbours, and our heading-arm clip suspends collision entirely when
#   our mesh does not cover the player (FINDINGS:3428-3432) so it would not even
#   express retail's D2.
```

**Known exposure before it runs, `ours`, n = 852:** at arrival `q = D` exactly, and `|D(86) − the client's next report|` is p50 **89.4 u**, p90 **136.4 u**, with **45.7% at or beyond the match radius** (turn-conditioned n = 291: p50 41.1 / p90 116.8, 14.8%). **P3 is expected to fail the match on ~46% of arrivals and land in gate-2/gate-3 territory, which nothing offline can price.**

### REALFIX-P1 · `--retail-grant` — fidelity reference, NOT an experiment

```python
state["move_family"] = None                        # NEW KEY -- nothing tracks this today
FAMILY_RATE = {1:1.00,2:1.00,3:1.00, 4:0.66,5:0.66,6:0.66, 7:0.75,8:0.75}   # CONTESTED

# heading arm
endpoint = reported + vec2 + 0.5*u                                  # D1, live, ADJUDICATED
dest, _  = clip_to_walkable(state, endpoint)                        # D2 approximation only
send(0x0025, [PLAYER_AGENT_ID, u, mt])                              # S1
if mt != state["move_family"]:
    send(0x002B, agents.agent_update_speed(PLAYER_AGENT_ID, FAMILY_RATE[mt], mt))
    state["move_family"] = mt                                       # S2
send(0x0029, [PLAYER_AGENT_ID, list(dest), dest_plane, state["plane"]])   # S3, ALWAYS LAST

# stop arm :10235      -- 0x002B then a ZERO-DISTANCE 0x0029. NEVER 0x0028.
# click arm :9879      -- grant the clicked point verbatim, do NOT hold it.
# idle                 -- re-grant on a heading OLDER than 1.0 s (retail's 73 rows,
#                         lag p50 2.58 s). Do NOT build an unsolicited-grant channel.
```

**Planes are `(dest_plane, cur_plane)`, never `(0, 0)`** — field 3 = destination plane, field 4 = current plane, closed from the binary three times (`FINDINGS:3364`, `:3428`, `studies/smsg/FINDINGS.md:130-135`); forcing 0 writes a wrong map index into `agent+0x80`. `authsrv.py:9987` already orders them correctly. `FAMILY_RATE` is **CONTESTED**; the decider is `movetap.py` on `agent+0x5C`/`+0x60` during sustained backpedalling, not the wire.

**Four-variable delta from `--client-endpoint`. Do not run before the lead family; a bad result names none of the four.**

### REALFIX-P5 · `--resync` (built, never run) · REALFIX-P6 · `--grant-suppress` (built, run once) · REALFIX-P0 (shipped)

No new code. P5 needs `RESYNC_MAX_REPORT_AGE = 100.0/288 = 0.347 s` (already at `:2665`) and the plane refusal already present; score it on `resyncscore`'s yank column, never on the hard bar.

### REALFIX-P4 · `0x0027` re-arm — **DO NOT BUILD**

New SMSG constant + new builder + new wire test, for a candidate the mechanism read grades FAILS provably (`0x00602910` rewrites `+0x78` to the runaway point) and the harness cannot score. If it is ever revisited, the schema row is `schema/overrides.json` GAME_SMSG `"39"`: `msg_header + dword(agent) + float(maxSpeed)`, `declared_unpack_size 10`, assert `AgAgent.cpp:2317 maxSpeed >= 0`.

---

## 2. REALFIX-H1 — the offline harness

**New module `toolkit/clientscan/grantsim.py`; new test `toolkit/clientscan/test_grantsim.py`.** Obeys the house rule of its neighbours: *opens vault captures and writes nothing*, never imports `authsrv.py`, defines no bar of its own.

### 2.1 What it is for

**A calibration instrument, a refusal instrument, and an exposure meter — not a ranker.** §6.4 of the research draft is the reason. Any output that orders two candidates on a common scale is out of scope; the file prints exposure per candidate on the candidate's own axis.

### 2.2 Reuse vs. new

Reuse verbatim: `movesync.load_wire_reports / load_grants / steps / hard_steps / denominator / pair / offset_from_stamps`, `resyncscore.sync_track / validate_sync_model / track_from_capture` (whose origin refusal is the gate), `origin.origin_of`, `vaultpath.require_dir`, `checks.Ledger`. New: a `c2s_moves(path)` reader keeping `values[3]` and `values[4]` (which `load_wire_reports` drops); the `≤ 1.0 u` short-circuit; the `+0x48` arrival tick; test-instant enumeration; the match proxy; the reseed; and the two new metrics. **Do not fork `sync_track`'s glide.**

### 2.3 Pipeline

1. **LOAD** — reports and as-sent grants through `movesync` unchanged (a second decoder is a second chance to disagree about what the client said).
2. **SYNTHESIZE** — one pure `policy_<name>(c2s, state) -> [(t, D, plane_dest, plane_cur, kind)]` per candidate.
3. **SIMULATE** the bake byte-exact: `d = D − [+0x78]`; `S = [+0x60]*[+0x5C]`; if `|d|² ≤ 1.0` write `+0x78 = D`, zero velocity, arm `+0x48 = now+1`, **return with no dispatch and no fan-out**; else `vel = unit(d)*S`, `[+0x58] = now`, `[+0x48] = now + trunc(|d|*1000/S)` clamped ≥ 1; read `[+0x78] + vel*((t−[+0x58])*0.001)`; park on arrival.
4. **TEST INSTANTS** — class A (bake, one per grant with `|d| > 1.0`) and class B (arrival SetPosition). **Print as a FLOOR** and label it: child recursion (`0x0060221E`) and the bake's post-dispatch fan-out (`0x005FEC7E`/`0x005FEC9A`/`0x005FECAC`, `0x00602BE5`) multiply both.
5. **MATCH PROXY** — `q` against the client's own report track over `[max(armed_since, t − 5.0), t]`, radius `MATCH_RADIUS`, **straight-line only**. That is correct in this regime, not a simplification: a degenerate segment skips the walkable conjunct, and segment 0 is degenerate exactly when `+0x48 == 0`.
6. **GATE-1 PROXY** — `sep ≥ 299.332591 u` ⇒ SNAP. Exact cut, three independent exhaustive derivations; exactly 300.0 u snaps.
7. **RESEED** — sim ← client position, `armed_since ← t`, modelling the roster-wide wipe at `0x006060A2`/`0x006060A9`.
8. **SCORE** — see 2.4.

### 2.4 Metrics — every capture, every candidate, origins never pooled

- **PRIMARY: survival time and survival distance to first violation**, over `[start, min(first predicted snap, first measured hard step))`, with the censor instant named.
- **REALFIX-M1 · lag age** — the age, in seconds of client travel, of the newest polyline point within the radius of `q`, reported p50/p90/max against the chain's ~5 s block-recycle bound. **This is P2's axis.**
- **REALFIX-M2 · arrival exposure** — fraction of class-B instants with `|D − client track| ≥ MATCH_RADIUS`. **This is P3's axis.**
- **A BRACKET, always, never a skip:** `[snaps with the match test ON, snaps with it OFF]`. The match-on figure is a lower bound and the match-off figure an upper bound. **This replaces the drafted "skip the match test when chord p90 > radius" rule, which fires on 4 of 4 counterfactual and 7 of 11 calibration captures and would degrade the whole plan to the refuted separation-only scorer.**
- Secondary: censored snap count; rate on **both** denominators (per minute of span, and per minute of active time **with the 2.0 s threshold named**); u displaced per active second; separation p50/p90/max; instant count (floor); **and the capture's own report gap p50/p90 and chord p50/p90 printed beside every row.**

### 2.5 Inputs

**CALIBRATION (`ours`):** `20260820T182554 / 182934 / 183311 / 195137 / 195315`; the five movetap pairs `145717·145939`, `150336·150349`, `150522·150537`, `152716·152723`, `171153·171436`; `20260819T182652`; `20260814T100340`; `20260811T173940`. The three undocumented pairs have UNVERIFIED run configuration (no argv in the jsonl headers) — **use them for C1 only, never for a policy attribution.**

**COUNTERFACTUAL (`ours`, zero-grant, §4 of the draft):** `173940` (100.0 s, 158 reports, 9,353 u, chord p50 49.6 / p90 141.6 u — the best), `182934` (114.8 s, 79, 22,586 u, 127.5/514.4), `100340` (719.0 s clean, 274, 43,177 u, 94.8/477.5), `182554` (26.2 s, 21, 6,433 u, **445.9/516.1**).

**Retail (`live`) is never an input** — it has no `ours` grant stream to counterfactual against.

**⚠ Print with every counterfactual result:** the substrate is fast-running (`v_player` p50 262–283 u/s against a declared 288) and click-free (0/5/21/0 clicks), so it is the regime where any lead policy is *least* harmful and where P0 sends ~0 grants and survives by doing nothing. **The instrument prices harm added; it cannot price harm removed.**

### 2.6 THE CALIBRATION GATE — must pass before any counterfactual number is printed

- **REALFIX-C0 · the radius derivation must land first.** `MATCH_RADIUS = 99.919968` has **zero occurrences anywhere in this tree**, no committed reimplementation of the `0x0046E870` LUT sqrt exists to re-derive it (the doc-level ~99.6 figures were corrected with round 5's write-up commit, but a number whose derivation is not committed anywhere is UNVERIFIED in-tree). **Land the exhaustive scan (nine instructions at `0x0046E870`, 256-dword LUT at `0x0093CAC8`) as a committed function with its own check, with gate 1's `89600.0f` → 299.332591 u as the positive control.** Until it lands, carry the nominal `100.0f` (`authsrv.py:2617-2619`) and label the constant UNVERIFIED. **And stop describing the proxy as having "zero free parameters"** — the 5 s window is a block-recycle rule, not a per-node match window.
- **REALFIX-C1 · simulator vs memory, glide-conditioned.** Publish the parked fraction beside every pair (53.0 / 58.6 / 83.1 / 8.5 / 3.8%) and the glide-conditioned p50 (27.55 / 23.54 / 24.53 / 20.68 / 14.62 u). **Set the bar from the two high-grant pairs only** (`152716`, `171153` — the regime the candidates create): accept `glide p50 ≤ 25.0 u` and `max ≤ 75.0 u` on those two, with the parked-dominated three reported and not gated. Do not gate on the unconditioned p50; it is diluted.
- **REALFIX-C2 · snap reproduction on as-sent streams.** **(a) STRUCTURAL ZEROS — `173940`, `182554`, `182934` must predict exactly 0.** This is the gate the separation-only scorer fails at 16/12/34 and it is the check that carries. **(b) TOTAL — pinned to a golden fixture, not a band.** Two implementations of the drafted spec gave 69 and 80 against 60 measured; a `[0.7,1.5]×` band drawn after seeing 1.15 is not a gate. Commit a fixture capture with an expected per-capture vector and assert equality. **(c) SEPARATION — `{182652, 195137}` must exceed `{145717, 195315}` by ≥ 3×.** Do **not** gate on the `145717`-vs-`195315` order: it inverts (predicted 1.69 > 1.39, measured 1.31 < 1.39). Print the inversion.
- **REALFIX-C3 · policy replay at message level.** `20260820T195137` carries 199 `grant_verdict` rows, all `(fired=true, reason="off")`, and 199 sent `0x0029`; `20260820T195315` carries 154 rows — **152 `locally-moving` + 2 `grant`** — and 2 sent `0x0029`. Accept exact reproduction, reason for reason. **⚠ This covers the CLICK arm only** (`195137` has 132 decoded `0x003D` and zero heading grants), i.e. only P0 and P6. **Extend it to the heading arm by importing the real `_heading_grant_ok` predicate** — `_grant_verdict`'s own docstring (`:3006-3011`) says it was made side-effect-free so an offline scorer could run the decision rather than a paraphrase that agrees with it by construction — **or stop calling C3 the policy gate.**
- **REALFIX-C4 · nulls.** Match-test deletion must inflate ≥ 1.5× (measured 122 vs 69, 2.0×). Destination rotation must inflate monotonically (69/73/99/133 at k = 0/1/5/17). **Time shift is NOT a valid null on the total** — +0.35 s scores 60, dead on the measured total — so gate it per capture at +3.0 s only (`195137` 8→0 against a measured 8; `182652` 12→5 against 13) and **print the failure**. **And do not claim a geometry/cadence asymmetry**: at matched perturbation scale, rotate-1 is +5.8% and shift-−0.35 s is +10.1%.
- **REALFIX-C5 · sensitivity band.** window {2.5, 5, 10} s × radius {50, 100, 200} u × gate {250, 299.33, 400} u **× match test {ON, OFF}**. Totals over the first three axes span 51–80 against a base of 69; the fourth axis is the one the ranking is not invariant on (§6.4). **Accept: any ordering claim survives the full band including the match-test axis, or no ordering is printed.**

### 2.7 Floors — `toolkit/checks.py`

```python
led = checks.Ledger("grantsim", floor=<PIN FROM THE FIRST GREEN RUN>)
```

Enumerated expectation, ~44: fixtures + origin refusal (2) · C0 radius derivation + gate-1 positive control (2) · C1 two gated pairs × (p50, max) + three reported + n-floors (9) · C2 (a) 3 + (b) golden vector 1 + (c) 1 + inversion printed 1 (6) · C3 click arm 4 + heading arm 2 (6) · C4 match-null 1 + rotation 3 + per-capture shift 2 + matched-scale statement 1 (7) · C5 ranking invariance incl. match-test axis (4) · structural asserts — a ≤1.0 u grant produces no instant, arrival parks, reseed clears `armed_since`, `instants ≥ |{grants: |d| > 1}|`, M1 and M2 both non-empty on their own candidate (6) · refusals that must go red — pooled origins, unknown policy name, a ranking printed outside the invariance band (3). **`CLAUDE.md` is explicit: set the floor from a real green run, never from a guess, and never above what one produces. The 44 is an expectation. Do not ship the literal.**

### 2.8 TESTS.md entry (add in the same commit as the test — `test_srclint.py` §7 checks both directions)

> `toolkit/clientscan/test_grantsim.py` (**WOULD A DIFFERENT GRANT POLICY HAVE SNAPPED — AND THE ANSWER IS THAT THIS FILE CANNOT TELL YOU, ON PURPOSE.** The guard on `toolkit/clientscan/grantsim.py`, which replays a capture's own c2s `0x003D`/`0x003E`/`0x0047` through each candidate policy, drives a byte-exact rebuild of the client's `0x005FE950` bake, and asks the client's own question at the client's own two caller classes. Where `resyncscore` prices an ADDITIVE fix and `grantsuppress` prices the SUBTRACTION, this prices a SUBSTITUTION. **IT IS NOT A RANKER AND ITS TESTS REFUSE TO LET IT BECOME ONE.** §C5 sweeps the match test's PRESENCE alongside its radius, because that is the axis where the ranking inverts: with the match test on, leads 0 and 86 score identically on three of four counterfactual captures (0/0, 0/0, 2/2, 3/2) and only the already-refuted 766 u lead separates; with it off, 766 WINS on three of four (3 vs 10 on `20260820T182554`, 22 vs 23 on `182934`, 30 vs 48 on `20260814T100340`). Any ordering printed outside that band is a red check. **THE HEADLINE IS THE CALIBRATION.** §C2 requires reproducing the measured hard-jump census on eleven `ours` captures across five configurations — 60 measured — and, the check that separates this from its own first draft, **exactly zero** on the three captures that sent zero grants, where an earlier separation-only scorer predicted 16, 12 and 34 because `20260819T145717`'s real separation is p50 1,164 u, movetap-confirmed, with 7 jumps in 320 s. §C2(b) asserts against a golden per-capture vector rather than a ratio band, because two independent implementations of the same written spec gave 69 and 80 against that 60. **§C4 IS WHERE IT ADMITS WHAT IT CANNOT SEE:** deleting the match test doubles the prediction and rotating destinations inflates it monotonically, but shifting every grant by +0.35 s — destroying causality outright — scores 60, dead on the measured total, and at matched perturbation scale the file is MORE cadence-sensitive than geometry-sensitive (rotate-1 +5.8%, shift-−0.35 s +10.1%). **§C1 GATES ON THE GLIDE-CONDITIONED RESIDUAL**, from the two high-grant pairs only, because three of the five calibration pairs are 53–83% parked and their p50 of 0.00 measures the parking, not the model. **AND THE INPUT PLAN INVERTS THE OBVIOUS ONE:** the refuted-run captures carry real grants and real snaps and are therefore CALIBRATION substrate, while the COUNTERFACTUAL substrate is the zero-grant set — because `20260819T182652`, the capture that refuted `--client-endpoint`, yields **3.2 s and 259 u** of client track before its own first teleport contaminates everything after it, and because that zero-grant substrate is fast-running and click-free, which is the regime where every lead candidate is least harmful and where the shipped default survives by sending nothing at all.)

---

## 3. Pre-registered predictions

**Both denominators, per capture, `ours` only, written before any counterfactual stream is synthesized.** Substrate minutes: `173940` 1.667 span / 0.861 active (cov 51.7%); `182554` 0.437 / 0.437 (100%); `182934` 1.913 / 1.018 (53.2%); `100340` 11.98 span, **active coverage unmeasured — span only, and say so**. Baselines to beat: 0 / 0 / 0 jumps and 0 grants on the first three; 2 jumps and 2 grants on `100340`. **Any candidate predicting > 0 on the first three predicts harm the zero-grant control did not have.**

**REALFIX-D2 · P2-ZEROLEAD.** *Structural, and I state it as such rather than dressing it as a discovery:* under zero lead `q` at every class-A instant is a past reported position and at every class-B instant `q = D` is the reported position, so the match passes at distance 0 and **P2 predicts 0.00 snaps/min span and 0.00/min active on all four captures**, match-on. Match-off (the upper bracket) it predicts 10 / 23 / 48 on `182554` / `182934` / `100340` and 0 on `173940`, i.e. **23 / 23 / 4 per minute of span** — publish the bracket, not the arm. **The real prediction is REALFIX-M1, lag age: p90 ≤ 1.2 s on the seven fine-cadence captures and ≥ 1.785 s (one report interval) on `182554`, max ≤ 3.0 s everywhere, against the ~5 s chain bound.** ⇒ **FAILS if** any class-A snap is predicted on a capture whose report gap p90 < 1.0 s, **or if** M1 max reaches 5.0 s on any capture. (The drafted prediction of "≥ 3 snaps on `182554`" is **withdrawn before the run**: no setting of the match test satisfies it together with the other three per-capture claims, and the structural argument says it must be 0.)

**REALFIX-D3 · P3-SHORTLEAD (fixed 86 u).** Same 0.00/min on all four match-on, for the same gate-1 reason (86 ≪ 299.33). **The prediction is REALFIX-M2: arrival exposure 40–50% pooled and 10–20% on turn-conditioned intervals**, from the measured 45.7% / 14.8%. ⇒ **FAILS if** M2 < 20% or > 70%; **FAILS as a candidate** if M2 exceeds P2's (structurally 0%) by more than 50 points, which it is predicted to do — i.e. **P3 is pre-registered as strictly more exposed than P2, and the live A/B should therefore run P2 first.** The adaptive arm (`lead = min(766, 288 × gap_p50)`) is predicted to be indistinguishable from fixed on the seven fine-cadence captures and to raise M2 on `182554` (long gap ⇒ long lead ⇒ more drift), **which is the opposite of the intent it was drafted with** — record that before it runs.

**REALFIX-D1 · P1-RETAIL.** **NOT SCOREABLE by this harness** (it models no `0x002B`, so a BACK leg would run at 190.1 u/s while the harness bakes 288 — 1.51× in the operand of both tests). The geometric term only, with S fixed: cycle `766/(288 − v_player)` at the measured p50s = **31.0 / 29.8 / 159 / 95.8 s** ⇒ **1.93 / 2.01 / 0.38 / 0.63 per minute of span** on `173940` / `182934` / `182554` / `100340`, i.e. ≈ 3 / 4 / 0 / 7 snaps, magnitude p50 in the 500–770 u band (heading grants cap the step at 767.7 u, p90 757.5). Per minute of *active* time: 3.72 / 3.78 / 0.38 / (span only). ⇒ **FAILS if** it survives all of `173940` with zero predicted snaps, or if magnitude p50 lands outside 400–800 u. **⚠ carry the substrate bias with every one of these: this is the regime where P1 is least harmful, so a low score is not an acquittal.**

**REALFIX-D5 · P5-CLIENTPIN.** Predicted **0 snaps on every capture** (`0x002C` clears the record before writing). On the clean substrate at a 100.0 u trigger: **20–30 fires per minute of span**, ~40% of reports, `mints_hard` (yank ≥ 520 u) on **< 5%** of fires. ⇒ **FAILS if** `mints_hard` > 10% of fires, or fire rate > 40/min (a per-report teleport channel). **Its own committed pre-registration (1,998 fires, 25.4/min, 42.2% of reports, separations p50 183 / p90 514 / p99 1,415 / max 4,633 u, `authsrv.py:2628-2638`) is pooled over 66 captures across configurations including two refuted ones and its own text says "treat it as a magnitude, not a score" — quote it as a magnitude, never as a baseline.**

**REALFIX-D6 · P6-GRANTSUPPRESS (control).** Must reproduce its own measured A/B (1.39 vs 11.49/min span; 1.54 vs 11.49/min active) and C3's message-level identity. **On the clean substrate it must predict exactly 0 and change nothing; a control that moves here is a bug.**

**REALFIX-D0 · P0-DEFAULT (control).** 0 grants on `173940` and `182554` (0 clicks), ~5 on `182934`, ~21 on `100340` ⇒ **near-perfect survival on the substrate by doing nothing.** ⇒ **The drafted set-level falsifier "the whole set FAILS if P2 and P3 do not both beat P0 on survival" is WITHDRAWN: it fires by construction.** The replacement set-level falsifier: **the set fails if any candidate predicts a class-A snap on a zero-grant capture**, i.e. if a candidate manufactures harm where the control had none.

---

## 4. Run plan

**Offline first, and the offline pass answers a smaller question than it was drafted to answer.**

1. **Land REALFIX-C0** (the radius derivation + the three document corrections). Nothing downstream is quotable without it.
2. **Land `grantsim.py` + `test_grantsim.py` and pass C1–C5.** Deliverable: the calibration table, the two exposure metrics, the bracket per capture, and an explicit refusal to rank. **Expected outcome: P2 and P3 both score 0 snaps match-on and separate only on M1/M2 — that is a successful run, not a failed one.**
3. **Price P5 with the existing `resyncscore`** on its yank column (no new code).
4. **Do not build P4. Do not run P1 before the lead family.**

**THE ONE LIVE A/B — REALFIX-L1, owner-driven.** `--zero-lead` (P2, no stop grant, no `turned` gate) against the shipped default, on one map, one session, arms alternated at fixed intervals, **`movetap.py` running throughout** so the run is two-sided.

- **Traffic conditions, from the record's own lessons:** **click-free** (the `turned` gate and the substrate bias both hinge on it), **keyboard held through the whole waiting period** (`FINDINGS:1785-1789` — "any future warp run must keep the keyboard moving through the whole waiting period, or the instrument goes blind exactly when the phenomenon fires"; the default build is blind for 220 of 320 s), and **including a deliberate sustained backpedal leg**, because backpedalling is where `S − v_player` is largest (retail's own backpedal rate is 189.8 u/s = 0.659 × 288, `live`, n = 32) and it is the regime no capture in the vault covers — a substrate gap this leg discharges, named **REALFIX-U4**.
- **PRE-REGISTERED PREDICTION.** P0 arm: 3–6 hard jumps per minute of **active** time (bracketing the measured 4.19) and 100–170 u displaced per active second (bracketing 137.8). **P2 arm: ≤ 1.0/min active and ≤ 40 u per active second.** Separation (movetap-measured, SYNC vs the client's report): P0 arm p50 ≥ 800 u; **P2 arm p50 ≤ 150 u and p90 ≤ 520 u.**
- **PRE-REGISTERED FAILURE SIGNATURE.** If P2 fails, it must fail as **frequent small displacements at the report-chord scale** (33–70 u fine cadence, ~500 u on a keyboard hold), **not** as a rare large teleport. **A P2 arm whose displacement p50 exceeds 520 u refutes the "lag is on the polyline" reading** and sends the arc back to §2.2.
- **WHAT WOULD REFUTE THE INVARIANT ITSELF:** a P2-arm snap recorded while movetap shows separation < 299.33 u and the copy behind the player on ground already walked. That is gate 2, gate 3, or the gate-free `ResyncAllAsync` — and it is the outcome that would make every policy in this document beside the point.
- **RIDE-ALONG, and it is the highest-value item in the arc:** while the client is up, set the breakpoint at `0x0060580D` / `0x00605820` and log `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation. It says which gate fires, whether gate 2 is ever reached, and it can refute the `clientControlled` mechanism outright. **Named in FINDINGS twice, unrun for three rounds.**

**Ladder after L1:** P2 green ⇒ ship it and P3 is unnecessary. P2 green on movement but costly on the non-movement axis (aggro/interaction, because the copy's velocity is zeroed) ⇒ P3 at 86 u is the next rung, carrying its 46% arrival exposure. P2 red ⇒ the invariant's O1 asymmetry is wrong and the arc restarts at §2.2, not at a new policy.

---

---

## 5. Open questions, ranked

**REALFIX-Q1 · Which gate actually fires, and is the `clientControlled` fence real?**
Named in FINDINGS twice, unrun for three rounds, and it is the difference between "the
mechanism predicts 13.8/min" and "the mechanism predicts 176/min and something throttles
it". It can refute the fence mechanism outright and it would give gate 2 its first
observed firing (or confirm n = 0).
**Cheapest: a runtime breakpoint at `0x0060580D` and `0x00605820` during a live desync,
logging `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation.
Ride it along with REALFIX-L1 — the client is already up.**

**REALFIX-Q2 · Does zero lead hold at a client?** Everything in §5–6 says P2 is the only
family that satisfies O1 and O3 with no assumption about the player's speed, and the
offline harness proves it only by tautology (§6.5). Its two named assumptions — the
`now+1` arrival dispatches (RECONSTRUCTION for the 1 ms case), and `RTT × v_player < 100 u`
(UNVERIFIED off loopback) — are both live-only.
**Cheapest: REALFIX-L1 itself, with its pre-registered failure signature (frequent small
displacements at the report-chord scale, p50 ≤ 520 u).**

**REALFIX-Q3 · Do history nodes expire, and is lag strictly safer than lead?** The whole
invariant rests on the asymmetry, and nothing measures it. `seg_match` applies no time
filter, but the 250 ms constant at `0x00604F09` sits in a different function with an
UNVERIFIED role, and the 5000 ms recycle is per *block*, not per node, so the true chain
span is looser and unmeasured.
**Cheapest (static, ~30 min, no client): `codescan --xrefs` on the function containing
`0x00604F09` to establish whether `0x006055E0` or `0x00605840` reach it, then read
`0x00604BB0`/`0x00604C03`'s allocator and sweep end to end. Positive control required —
make the same xref filter find a call site you already know, e.g. `0x00605AF0`'s single
caller.**

**REALFIX-Q4 · Which agent array does gate 3 enumerate?** It decides whether a
server-side crowding guard is even expressible: world[1] means the relevant crowding is
what the *player* sees, world[0] what *we* believe. Nobody has read it, and a second
unknown sits in the same function — the predicate is applied at tens of units by the
sidestep site and at `pathArray[0]` distance by gate 3, and whether its internals are
scale-sensitive (the 60° cone and the 0.0005 s cut both plausibly are) is UNVERIFIED.
**Cheapest (static, ~45 min): read `0x005FEF70` end to end for (i) the neighbour loop's
array base and (ii) how `|to − from|` is consumed.**

**REALFIX-Q5 · Which of the 13 SetPosition sites can fire with no server message at
all?** This is the question `--grant-suppress` needs answered: round 4 measured 1.39
hard rows/min with 2 grants and never explained the residue. `0x00604A50`, `0x00606394`,
`0x005FF74B` and `0x006028FF` are unexamined, and `0x005FCAA0`'s gate-free reseed is
UNVERIFIED as a live route and is a candidate for the unexplained snaps 12–59 s after the
last grant.
**Cheapest (static, ~30–45 min): walk `--xrefs` up from each unexamined site until it
reaches either a receive-handler VA in the 18-row table at `0x00A52D70` or a non-message
entry point; attribute by module with `asserts.py`. State the indirect-call caveat —
`--xrefs` finds direct branches and stored VAs only.**

**REALFIX-Q6 · Does `0x002B`'s float track the movement family, or is it a buff/snare
channel?** Both arms are simultaneously present (71% modal per family, 214 distinct
floats corpus-wide), no wire rule can arbitrate, and P1's `FAMILY_RATE` table is
unshippable until it is settled. It is also the term the tree blames for
`--client-endpoint`'s failure.
**Cheapest, unchanged from `FINDINGS:1688`: `movetap.py` on `agent+0x5C`/`+0x60` during
deliberate sustained backpedalling, wire logged alongside. Fold it into REALFIX-L1's
backpedal leg — the instrument is already running.**

**REALFIX-Q7 · Is retail's clipped boundary our navmesh?** D2 is the one retail term we
cannot compute, and its identification is RECONSTRUCTION whose stated evidence was
withdrawn this round.
**Cheapest (~2 h incl. a client run, design given): one loopback capture on a map whose
navmesh we have, run TEST E and TEST F against our own `clip_to_walkable` output
(`origin=ours`, scored separately, never pooled). Reproducing ratio ≈ 0.12 and angle
≈ 79° says the mechanism is the same; collinear at 0° says our clip is a leash and
retail's is geometry.**

**REALFIX-Q8 · The three undocumented movetap pairs' run configuration.** `150336`/`150349`,
`150522`/`150537` and **`152716`/`152723`** are all two-sided and none is named in any
study document; `152716` is the `--heading-grant` decisive trial and is currently
recorded as wire-only.
**Cheapest (~20 min, no client): the gamesrv jsonl headers carry no argv, so recover the
configuration from behaviour — the presence and destination geometry of heading-triggered
`0x0029` distinguishes DEFAULT from `--heading-grant` from `--client-endpoint` outright.
Then record the argv in the capture header going forward, so the next arc does not pay
this again.**

**REALFIX-Q9 · The five of twelve corpus teleports landing nowhere near a granted point,
and the 9-of-26 unadjudicated impossible-step rows.** Untouched since round 2, and they
are the population any "the grant stream is the cause" claim has to survive.
**Cheapest: re-run the landing-geometry test with the caller-aware model from §2.3
rather than the grant-proximity heuristic — a class-B arrival instant explains a
teleport with no nearby grant, which the old test could not represent.**

**REALFIX-Q10 · Retail's blind budget.** 268 of 3,098 player grants (8.7%) sit outside
any watched interval and the detector demonstrably misses the corpus's one real retail
teleport. Nothing in the corpus buys this back.
**Cheapest: not a measurement but a procedure — every future warp run keeps the keyboard
moving through the whole waiting period. Already folded into REALFIX-L1.**
