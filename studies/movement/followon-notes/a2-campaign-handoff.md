# THE ACCURACY CAMPAIGN — handoff, 2026-08-26 session end

> **2026-08-26, second session — this file is now HISTORICAL.** Items 1–3
> below all landed as `REALFIX.md` **§0.17** (the wall-phase decoded to the
> unclipped lead, Q7 half-closed, the D2 clip + the leg-bounded immediate
> hold built; the literal item-1 candidate was REFUTED offline first). The
> same evening's P-17 run then refuted the pair in place and the owner
> ordered the drawing board — **the campaign's entry point is now
> `studies/movement/RETHINK.md`** (REALFIX §0.18 is the scoring of record).
> Status lives in `PLAN.md` §3/§8, per the house rule this file has no
> business duplicating.

**Entry point for a cold session.** Read in this order: `CLAUDE.md` (house rules
— the provenance boundary, the worktree rule, the label vocabulary, floors set
at green runs), `PLAN.md` §3/§8 (status authority), then
`studies/movement/REALFIX.md` **§0.9–0.16** — the whole `--d1-lead` arc lives
there, every section dated, every prediction registered before its run, every
refutation filed in place. The auto-memory at
`C:\Users\<user>\.claude\projects\C--gd-Rurik\memory\` is account-independent on
this machine and carries the instrument traps (read the movetap point-column
one before scoring ANY tape).

## Where the campaign stands

**Won and verified (keyboard side, §0.9–0.12):** `--d1-lead` — the bundle:
client-proposed D1 endpoints (band [700, 769]), edge-triggered `0x002B` speed
truth with stop re-arm, matched plane words on every bundle `0x0029` (the
§0.11 armer-kill; retail's nonzero pairs are bit-identical 222/222), the
retail stop-repin `[1.0, mt 9]` + zero-distance `0x0029` at every `0x0047`,
the ETA watchdog + leg model. The C1 warp recipe: 4/4 under the shipped
default → **0 under the bundle**; sign-of-lead CONFIRMED (13 maturations,
drag p50 0.0 u); the input lock decoded to the fence-shut mechanism and
killed; V-8 verified no-lock.

**The click side (§0.13–0.16) is where the work is.** Three policies were
tried in one day, each refuted by the next owner run — the record of WHY each
died is load-bearing, do not re-tread:
- F-B (answer everything verbatim, Rule 1 bypassed): refuted — retail never
  verbatim-echoes DISTANT mid-keyboard clicks (part-way routed points, n=4);
  the immediate answers raced the collision-blind copy through props.
- F-A (hold + eager void + flush fire): refuted — the flush's half-second-
  stale drag ticks were the direction-yank engine (35/44 sharp turns; the
  "382 clicks" were ~21 held mouse-drags).
- §0.15 (current, mostly deletion): keyboard-shadowed clicks DROP (retail's
  measured contract), channel-clear clicks answer through the shipped path,
  geometry passthrough + matched words + family re-arm + eager void retained,
  plus the outstanding-answer hold at the FLUSH.

**CRITICAL INSTRUMENT LESSON (§0.15, in memory too):** movetap's `point`
column is sample-and-hold raw m_point. Two full snap censuses (incl. §0.14's
"21 snaps") were artifacts of it — **the drawn body never teleported in those
runs**. Score body motion on the dead-reckoned live path only. Sep collapses
can be the ASYNC copy re-seating (harmless) — check which endpoint moved.

## The open items, in priority order

1. **R-3's residual hole (§0.16 item 2, candidate fix ~3 lines, UNBUILT):**
   the double-click-while-pathing terrain walk persists because the
   outstanding-answer hold gates only the flush — the IMMEDIATE click site
   fires click 2 once the floor reopens. **Verify from the final tape first**
   (`movetap-20260826T113833.jsonl` + the ~11:38 gamesrv log — census not yet
   run), then add the same `a2_click_answered_at > pos_seen` hold at the
   immediate site. Locks live in `test_d1lead.py` §4 (floor 72 — re-measure
   after any change; the floor history in its header is the pattern).
2. **The wall-phase specimen (§0.16 item 3, undecoded):** held-key +
   spam-click phased the body through a wall (under the plaza). Clicks DROP
   under keyboard in §0.15, so the D1 lead in the STUCK-AT-WALL cell is prime
   suspect (client pinned by prop collision, leads re-aiming 766 u beyond the
   wall, an arrival maturing while stuck orders the through-wall walk — the
   granted-order prop-collision bypass, owner-theorized and §0.15-confirmed,
   does the rest). Same tape holds it.
3. **The Q7 desk check → the D2 clip decision:** §0.15's S2-3 proved the D2
   boundary WORLD-ANCHORED (bit-identical clip coordinates repeating across
   live sessions a week apart — one corridor x∈[−6060,−5980]). Check those
   exact coordinates against OUR navmesh boundary (a script, no owner time).
   If they match, build the D2 clip for the lead (report-anchored along-ray,
   NOT state["pos"]-anchored — the --heading-grant graveyard, R2-1) — it is
   the fix item 2 likely needs. The extraction scripts and coordinate tables
   are in the dead session's scratchpad (survives on disk, cross-account):
   `C:\Users\<user>\AppData\Local\Temp\claude\C--gd-Rurik--claude-worktrees-resync-separation-run-setup\04ddd50c-5561-4ce5-9f73-cf19e48c8b6f\scratchpad\`
   (lane-*.md, skeptic-*.md, w2_clicks.py, sk_pull_verify*.py); re-derivable
   from the live corpus if gone.
4. **Standing optional items:** the mid-walk spoof cell (§0.8 — bogus-label
   veto-kill + gate-2 plane-keying, warp A's residual); the early-out-A/mode-9
   desk pass (§0.10 — why retail ships the [1.0,9] sentinel); movetap's
   `--seconds` early-exit and the fence-flap flicker (instrument debt).

## Standing state

Everything is merged to `main` (final commit of this session: see
`git log --oneline -1`; the arc is one linear chain of dated commits from
`ecb6c1a` to session end). Defaults unchanged: `--d1-lead` is OPT-IN; the
shipped default (`--zero-lead --grant-suppress --cast-stop=pin`, plane-carry
on) is byte-identical to pre-campaign behavior — every bundle change is
D1-gated and lock-tested. Test floors at session end: test_d1lead 72,
test_position_trust 219, test_cancelwalk 121, test_familyrate 26,
test_pcspoof 23, test_grantsim 86, srclint 22, provlint 19. Run only affected
tests (the suite is ~40 min and the owner runs it).

## How this campaign works (the part that made it work)

One worktree per session, merged to main at every landed step. Recon and
scoring fan out to Sonnet lanes; every substantive verdict gets a skeptic
re-deriving the numbers from raw rows — the skeptic refuted the orchestrator's
own framing four times this session (the Ctrl+C story, the F-B premise, both
snap censuses, a lane's "no scoring tool exists") and each refutation was the
day's most valuable output. Predictions registered BEFORE runs, with exposure
floors and REFUTED-IF clauses; zero-exposure is never a null; owner runs are
~10 minutes with concrete scripts and the tapes named back. The owner's
subjective reports ("feels jittery", "I phased through a wall") have been
reliable instruments all day — take them as data, decode them from the wire.
