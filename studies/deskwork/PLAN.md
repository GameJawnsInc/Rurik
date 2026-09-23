# Desk work: the non-harness routes

**Written 2026-09-22**, from a read-only survey of the tree at `cd254c51` (`main`). Eight
scout lanes, a verifier pass per lane, one critic and three judges; nothing in the repo or
the vault was changed, and no client was launched. This is a decision document: the desk
routes, ranked, for the owner to pick from.

**Identifiers.** `DESKWORK-D<n>` = a route, a bundle of desk work with a first session and
an acceptance that can fail. `DESKWORK-Q<n>` = a quick win, one session or less.
`DESKWORK-D<n>` keeps the survey's `R-D<n>` number so the lane and judge notes resolve;
the ranking is §2's table, not the number. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

Status authority is [`PLAN.md` §3](../../PLAN.md) and nothing here restates it. Every
route below cites where its items are recorded as open; where a gap was found by the
survey itself, the section says so and gives the evidence. Labels are the repo's:
OBSERVED, UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

---

## 1. What "desk work" means here, and why now

The harness is one physical resource. Several Claude sessions and the owner share the
loopback client, the owner drives most client runs by hand, and a live capture against
ArenaNet is a campaign on the secondary account, not a test mode. Everything whose
progress needs the retail client running is **harness work** and waits its turn.

**Desk work** is everything else: static analysis of the client snapshot
(`toolkit/clientscan`), mining the ~1,671 harness runs, 36 live sessions and ~3,100
gamesrv logs already in `vault/captures`, server code and tests, running the server with
no client, content rows, the tools and headless renders, instruments validated against
tapes on disk, docs and test infrastructure, and wiki reads through the browser. It
proceeds in parallel and without the owner.

Three findings made the survey worth running now. Four `PLAN.md` §8 items were
answerable from tapes three to eight days old (the adrenaline gate, the hero kick,
RUN-R8, MORALE-Q6's outpost half). About fifteen §8 lines are closed with no log entry,
five more than the section's own header admits. And the owner frames Rurik as a private
server plus a build-your-own-mod platform, so the surface the operator authors against
counts as much as retail fidelity does.

Each route carries a **client dependency**: `none` (desk end to end), `prep-only` (desk
work whose payoff arrives when a run happens), or `final-confirmation-needs-run` (ships
desk-side; the final verdict needs a client). Roughly 41 of the surviving candidates end
in a confirmation run, which is why D12's run ledger exists: it bundles them into a few
runsheets instead of ~41 single-question runs.

---

## 2. The ranking

Three judges scored every route 1–10 on value and feasibility and gave an overall, each
through one lens: **F** fidelity and the engine (does a RECONSTRUCTION become OBSERVED;
does a §3 rung move), **O** the operator and the platform (what the owner can play,
configure or author, and how soon they notice), **L** leverage and risk (the cost of every
later session, what it unblocks, evidence bought per session). Combined = mean of the
three overalls; ties broken by fewer sessions.

| Rank | Route | F | O | L | Combined | Spread | Cost | Sessions | Client dependency |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **D1** c2s: send-site census, N2 hero kick/add, travel, inventory | 8 | 8 | 8 | **8.00** | 0 | L (S+S+M+M) | 4–6 | final-confirmation-needs-run |
| 2 | **D5** retail combat batches on disk: adrenaline gate, interrupts, prop 10, recharge, shouts | 9 | 6 | 8 | **7.67** | 3 | M | 3–4 | none for 5 of 7 steps |
| 3 | **D4** skill coverage in bulk from the archive's own description templates | 6 | 9 | 6 | **7.00** | 3 | M | 2–4 | none for labels |
| 4 | **D7** the character sheet: primaries, energy, item words, custom professions | 7 | 7 | 5 | **6.33** | 2 | M | 3–4 | final-confirmation-needs-run |
| 5 | **D12** status you can trust: corpus index, run ledger, mechanics ledger, PLAN compaction | 6 | 5 | 8 | **6.33** | 3 | L (pieces stand alone) | 5–7 | none |
| 6 | **D9** the authoring loop: N1 picker, template codes, hot reload, quest verbs, gold, loot | 5 | 8 | 6 | **6.33** | 3 | L | 6–8 | none for steps 1–3 |
| 7 | **D14** operational readiness: vault backup tier, build-landing RUNBOOK, stale-install check | 4 | 6 | 8 | **6.00** | 4 | M | 2–3 | none |
| 8 | **D6** area spells and the last two conditions | 8 | 6 | 4 | **6.00** | 4 | L | 3–4 | final-confirmation-needs-run |
| 9 | **D8** hostiles like retail: ethogram, leash, caster opening, populations, gadgets | 7 | 6 | 5 | **6.00** | 2 | L | 6–8 | final-confirmation-needs-run |
| 10 | **D10** movement: Q14 from the corpus, a warp row, tap rate, follow frame, STATE page | 6 | 4 | 7 | **5.67** | 3 | M | 4–6 | none for 5 of 7 steps |
| 11 | **D2** protocol bookkeeping: earned names, D-list, cross-build shape guard, msgmix | 6 | 4 | 6 | **5.33** | 2 | M | 2–3 | none |
| 12 | **D3** load prologue fidelity: replyjoin ratchet, twelve names, unlock bracket, 0x008A | 7 | 4 | 5 | **5.33** | 3 | L | 4–6 | final-confirmation-needs-run for anything newly sent |
| 13 | **D13** suite cost and honesty: scrub, buildpins, census, --since, bare machine | 4 | 3 | 9 | **5.33** | 6 | L (steps 1–3 one session) | 5–8 | none |
| 14 | **D11** authored places at the desk: cliffs, palette, water, compass, walkability | 5 | 5 | 4 | **4.67** | 1 | L | 8–12 | final-confirmation-needs-run |

**Where the lenses disagree, and why that is the decision.**

- **D13 (spread 6)** is the leverage judge's first pick and the operator judge's last.
  Both are right about different things: steps 1–3 take about 28 minutes off every full
  suite for one session's work with the fix already probed row-identical, and the owner
  feels none of it. The question is whether one session of infrastructure goes before
  any fidelity route. (§8 Q2.)
- **D14 (spread 4)**: the fidelity judge scored it low and said in the same breath that
  its absolute priority is higher than the score, because it is the one irreversible risk
  in the list. The pinned builds and their DH keys have no second copy off this disk, the
  last mirror is same-disk and 47 days old, and C: is 86 % full. It needs the owner's
  decision on a medium before it protects anything. (§8 Q1.)
- **D6 (spread 4)**: rich retail witness (17 Fire Storm casts on one tape) but almost no
  leverage for other sessions, and every behaviour needs a look on a client.
- **D4 (spread 3)** is the operator judge's first pick because it is the largest gap
  between what the sandbox offers (1,333 unlockable skills) and what it plays (54). The
  other two judges scored it on the route as submitted, which depended on a third-party
  dataset and a licence question; the operator judge's probe removes most of that (§3
  D4), so the combined score here is likely low.
- **D9 (spread 3)**: the owner's named next item (N1) and the per-run iteration cost, but
  little retail fidelity and a hot-reload scope the owner must set first.
- **D1 (spread 0)** is the one unanimous route: the owner's queued ask N2, with retail's
  own reply on tape, plus a census tool that retires a whole error class.

**Sequencing, because most routes edit `authsrv.py`.** About 40 tests read that file as
text, so parallel sessions on D1, D5, D6, D7, D8 and D9 collide. The safe parallel set is
the one that never touches it: D13 steps 1–3, D14, D12 step 1, Q1 and Q3. Among the
`authsrv.py` routes, D5 goes before D6 (Dazed's interrupt arm rides D5 step 2) and D5
step 4 before D8 step 6 (cast policy sits on the measured recharge). Q1 lands before
D12's compaction so stale lines do not move into history.

---

## 3. The routes

### DESKWORK-D1 — the c2s side: one send-site census, N2 shipped from the ChCliApi family, then the other player actions the server ignores

**Thesis.** Every "c2s NOT FOUND" in the repo rested on a scratch enumeration that was
never committed and once searched the wrong family (s2c ids in a c2s census). A stdlib
byte scan reproduces every send site in about a second (two verify lanes). Sitting on
disk already: hero kick (0x001F, OBSERVED with its reply batch), hero add (0x001E, static
in ChCliApi), henchman add (0x9F, 3/3), travel (0xB1, 10/10) and inventory moves. The
server has no handler for 0x001E or 0x001F (it arms HERO_AI_MODE, LOCK_TARGET,
FLAG_PLACE and PARTY_FLAG_PLACE only), and the loopback wire already carries an unhandled
0x001F [3]/[40] pair (`authsrv-20260913T093718-c1`).

**Keys.** REX-1, REX-V1, REX-V2, PRO-V1, BEH-5, CRP-2, PRO-7, REX-2, REX-6, BEH-6, REX-3,
REX-V3, PRO-V3; plus the 0x0018 half of PRO-11 (from D3), which the operator judge showed
belongs with the add. Open at `PLAN.md` §8.1 "The sandbox" N2 (heroes §3.3 says NOT
FOUND; refuted in §6 below), pvpui §28.6, studies/cmsg.

**Steps** (reordered from the submitted route: the owner's ask does not wait on the
census).

1. **Kick.** Name c2s 0x001F `HERO_KICK` (medium). OBSERVED n=1: `20260916T150306` conn
   `10.0.0.210:62321`, t=158.676 c2s [6] → s2c 0x0075 [379], 0x01C3 [28,68,379], 0x00F8,
   0x003E, 0x00B0 [68,1], 0x0145 [96] at 158.718; 40 = all. Arm it: drop the hero from
   party state, despawn the body in a field, persist through charstore so the kick holds
   across zone changes (the tape's next two loads carry 0x0073 for hero 6 but no
   0x0072/0x01C2). `test_herolib` replays the batch in byte order.
2. **Census.** `codescan.py --send-sites` as a stdlib byte pattern (E8 rel32 to the
   framer; C7 45 xx imm32 within 64 bytes before; push len) over **both** send functions:
   0x007DCF00 (174 sites) and 0x007DCB10 (40 sites), 214 in all — the submitted route
   counted only the first, and a census that claims it cannot go stale must enumerate
   both. One row per site with wrapper VA, callers and nearest assert module; a coverage
   footer; a known-bad arm (a wrong framer VA yields 0 rows); a test pinning five
   anchors by masked signature per build (0x0040→0x009207B0, 0x0016→0x0091FD60,
   0xB1→0x0085C280, 0x001E→0x0091FF00, 0x001F→0x0091FF30 on 38797; 38888 moved every
   address).
3. **Retail c2s triage.** A livewire census of every c2s over the 96 connections: count,
   captures, handled/named, first s2c reply within 1.5 s; each of the ~19 unhandled and
   unnamed opcodes gets an overrides row with its retail reply or a `DROPPED_ON_PURPOSE`
   reason; `test_dispatch` gains the reverse guard (seen on retail, unnamed → red).
4. **Add.** Name c2s 0x001E `HERO_ADD` (static: wrapper 0x0091FF00 ← 0x0080E250,
   ChCliApi:4446/4447; callers PtSearch 0x00562FB0 after `m_activeList == LIST_HEROES`
   and UiCtlInstance 0x00577A3F). Arm mid-session with the load-time hero batch in the
   tape's order (0x0073, 0x0037, 0x00DA, 0x0065, 0x003A, 0x0072, 0x01C2 at
   t+0.76–0.80); refuse an unowned hero and the eighth. RECONSTRUCTION — no retail add on
   any tape. **Ship with it** 0x0018 as a hero bitmask built from the sandbox's
   hero-unlock ticks (bit 6 = Koss OBSERVED; 64 → 224 on 20260913): today the client
   gets OpenTyria's all-ones mask verbatim, so the Party Search list may offer heroes the
   Party tab never unlocked and the add becomes a refusal of what the client offered.
   Flag-gated — a duplicate sender of unlock state once wiped a library and crashed a
   client.
5. **Party family 0x98–0xB2.** 0x9F add-henchman [agent_id], OBSERVED 3/3 on
   `20260819T132414` → 0x00B0 + 0x01BF within 0.03–0.13 s; the other 8-byte wrappers
   (invite, leave, henchman kick) through their PyCliParty/PtButtons callers. GWCA only to
   cross-check a derived name.
6. **Hero skill toggle** c2s 0x0019 [hero, slot<8] (wrapper 0x0091FD80 ← 0x0080E000,
   ChCliApi:4359 `hotKey < CHAR_SKILL_HOTKEYS`; callers GmSkSlot 0x005434D7 and
   0x004E8ACF): toggle vs "hero use skill" from the callers' branches and the 0x1000005A
   subscriber; a per-hero mask, persisted; reply 0x0064 per bit (pre-registered; 0x0065
   whole-mask is the alternative); pvpui §30.2 for the mask.
7. **Travel** c2s 0xB1 [map,0,0,0,1] → 0x01D9 [2,1,''] then the transfer (0x01A5,
   0x0099), 10 of 10 on retail. Static first: what the world map's click gates on (the
   one caller 0x004A791F, UiGame:557/558) and the unlocked-outpost state nothing models;
   refuse a map with no content row.
8. **Inventory.** Name 0x004F (move item to bag/slot); arm it with EQUIP_ITEM 0x0030 on
   the tape replies (0x014B [1,213,2,1] + 0x006F [25,6,0]; 0x0030 [213] → 0x014B
   [1,213,3,4] + 0x006F [25,6,213]); a per-slot equip store replacing the once-at-login
   dress; retire `test_dispatch.py:191`'s stale "(0 loopback, 1 live)". The PvP
   equipment panel (0x0085 → 0x015C, 0x0086 → 0x015D) only after the owner confirms the
   want.

**Acceptance.** (a) The census reproduces all 214 call sites across both framers and the
five anchors, and a wrong framer VA yields zero rows. (b) `test_herolib` replays the kick
batch byte-order, and a kick of hero 6 on a `--persist` store leaves the next zone-in with
0x0073 for hero 6 and no 0x0072/0x01C2. (c) After step 3, zero c2s opcodes on retail's wire
are neither named nor `DROPPED_ON_PURPOSE` with a reason. **FAILS** if any ChCliApi or
0x98–0xB2 wrapper's recovered argument width disagrees with msgshape's SEND descriptor, or
if the retail kick batch cannot be produced from our party rig without inventing a
message.

**Value.** The owner's queued ask (N2) with retail's exact reply; a permanent answer to
"which client actions does our server ignore" that cannot go stale unnoticed; three NOT
FOUND floors retired (heroes §3.3, pvpui §28.6, sandbox N2); travel and inventory in game
for R-SANDBOX; four earned names for D2.

**Cost.** S (kick) + S (census) + S (triage) + M (add, hero controls) + M (travel,
inventory); ~2 sessions for steps 1–3. **Client dependency:** final-confirmation-needs-run
— one loopback click each (Kick, Add Hero, ctrl-click a hero skill, a world-map travel);
the census and triage are desk end to end. **Dependencies:** none to start; D2's naming
convention before static-only names are promoted (OBSERVED ones go in at medium now).

**Risks.** 0x001E has no retail witness and the 0x84d9b0 gate suppressing its send is
unread; the add reuses a load-time batch mid-session (heroes §38's ordering blocker);
0x0019 may be "use skill" not "toggle"; the world map may offer no destination without
outpost-unlock state we do not send; wrapper VAs move per build so the test pins by
signature; 0x0018 is flag-gated for the reason above.

**First session.** Arm the kick from the tape (step 1) with its `test_herolib` replay, and
write `codescan.py --send-sites` over both framers with the five anchors and the known-bad
arm in a test named in `TESTS.md`; run it on 38797 and 38888. Commit with a studies/cmsg
section quoting the kick batch at t=158.676/158.718. Output: N2's kick half on the wire,
and the census tool. The triage (step 3) is session two.

### DESKWORK-D5 — retail combat batches already on disk: the adrenaline gate settled, interrupts built, property 10 and the [42]/[55] residue, NPC recharge from completion, party-wide shouts, the adrenaline replay relabelled

**Thesis.** Six combat rules the server gets wrong or lacks each have a retail witness in
the vault, several recorded after the negative that still stands in the study ("no
interrupt has ever been captured"; "no NPC in the corpus casts twice"; "the gate's
variable is CONFOUNDED"). Each is read-tape, write-rule, tape-locked test. The fidelity
judge's own probe (`python toolkit/authsrv/adrenjoin.py`, read-only): ARMED 46
connections with 1,163 gains; DARK 49 connections with 0 gains, 0 clears, 0 spends over
312 damage events, 367 landed hits and 210 melee completions — and `--bars` shows the
Warrior bar [346, 1] (Frenzy, Healing Signet) dark on five connections, which breaks the
confound SKILLS-B1 recorded on 08-21.

**Keys.** CRP-1, CMB-6, CMB-7, BEH-V1, CMB-V2, MOV-9, CMB-V1, REX-5. Open at `PLAN.md`
§8.2 SKILLS-B1; skills §34.10/§34.7; castmech P1; animref D5 and §19; daggers §8 ("property
10 unread" — answered, §6 below); monsterai FINDINGS:843; `authsrv.py:21437-21440`.

**Steps.**

1. **SKILLS-B1 gate** (CRP-1). Fold `--by-connection` into `adrenjoin.py`. WARRIOR-PRE
   (`20260914T180058` conn 56301: bar [1,346], 18 hits, 18 melee, 0 gains;
   `20260915T155656`: 17/17/0; profession 1 level 1 from charsummary and 0x00B7) refutes
   Gate B; `20260917T224104` conn 62557 (level-20 A/W, no adrenal skill on the bar, 127
   hits, 0 gains, while W/Mo bars on the same map gain) removes the level caveat. Before
   writing "Gate A CORROBORATED", rule out or name the third rival the fidelity judge
   raised — "the character's LEARNED set holds an adrenal skill" — against the A/W's
   library. Implement: no 0x00CF, 0x00D0, 0x00D2 and no AD4 zero to a player whose
   CURRENT bar holds no adrenal skill (bars edit in game since B7; the dark-to-armed
   transition is UNOBSERVED, said at the call site). Update `test_adrenwire` §12,
   `test_pools` §11d, skills §34.11; withdraw `vault/plans/adren_gate.txt`; PLAN-LOG entry;
   §8.2 keeps only the rounding band. Note the fidelity judge's caveat: the client repaints
   nothing on an unaccepted 0x00CF (SKILLS-B1, 86b7485a), so this is wire fidelity and a
   staged live run removed, not something the player sees.
2. **Interrupts** (CMB-6). An `interruptjoin` reader with predictions first; classify all
   34 [59]s and 12 [49]s as cancel, knockdown (63) or interrupt for the denominator; write
   both witnessed batches into castmech P1 and animref D5 on `deepwoodjoin.sequence`'s
   absolute base — `20260916T213125` conn `10.139.166.60:57894` t=484.333 (0xA0
   [50,104,25,340] then 0xCF [25,4], [10,25,340], 0xA3 [16,25,104,..], [8,25,0], E5
   [25,1,0,4], [59,25,0], E2 [25,1,0], [35,25,0], E5 [25,1,0,24]) and `20260917T224104`
   conn `10.0.0.210:62557` t=434.658 ([8,25,0], [3,25,0], [35,25,0], [8,25,1],
   [10,25,230], 0xA3). Record that Disrupting Chop's +20 landed on Healing SIGNET (recharge
   4 → 24), contradicting the wiki's "if that action was a spell" (OBSERVED n=1), before
   encoding the +20 either way. An `interrupts` row flag for 340 and 230: on a victim with
   an open cast or swing send the batch, start the FULL recharge, un-queue; Dazed's "any
   hit interrupts a spell" rides the same path. Tests lock both batches byte-order.
3. **Wire residue** (CMB-7). (b) send GV_SKILL_DAMAGE [10, victim, skill] immediately
   before the 16/17/55 word — a decoded client rule (skillcast §16.6; 0x008129DA stores
   it at charContext+0x640, the number bodies consume and clear it) broken on every skill
   hit since August, 91 of 92 retail batches; (a) the player branch of
   `armour_ignoring_damage` (`authsrv.py:19450`) stops declaring [42, max] unless the
   maximum moved; (c) a body's completion batch carries its [55] energy word; (d)
   `skill_effect.275` Mend Condition with `heal_if_removed` (WIKI); (e) optional,
   INFERRED: `hero_pool_gain` sends the zero gain as the player's does.
4. **NPC recharge anchor** (BEH-V1). Commit `rechargeprobe` beside `spellhitjoin.py`:
   per (connection, caster, skill) the gaps between consecutive 0x00A0 prop-60
   announcements (v[2] caster, v[4] skill) against recharge and recharge + activation from
   skilltable on the matching build; floor pre-registered (≥ 5 repeat gaps on ≥ 4 skills);
   split every (connection, agent) key at each re-create so recycled ids cannot
   manufacture a short gap (the likely source of skill 229's 5.25 vs 7.0). If it holds (8
   of 9 skills already land on rec + act: 186 8.51, 179 8.00, 230 6.00, 222 5.99), move
   `skill_ready` to the completion at both sites (`authsrv.py:21580` hostiles, `:21865`
   party bodies) behind a revert flag; correct `authsrv.py:21437-21440`, monsterai
   FINDINGS:843, isle PLAN:575.
5. **Party-wide shouts** (CMB-V2). Attribute every type-15 0x0042 on the observer (42
   self, 23 by another caster, all 364 on `20260817T231139`) by the announce within
   1.5 s; bound earshot from caster-to-observer distance (WIKI earshot is the rival);
   `skill_effect` flag `party_wide = 'earshot'` on 364; `apply_effect` opens one episode
   per living ally in radius (heroes get the arithmetic, the 0x0027 speed word and the
   Crippled cure; only the player's own 0x0042 goes out, F46.8); revert flag.
6. **Adrenaline replay relabel** (MOV-9 + CMB-V1). animref §19's charge gate is OBSERVED
   through retail's reason string 1960 "Not enough Adrenaline" (39 of 39, skills §38,
   `chatdefs.py:73-77`), so §19 is a relabel; the per-slot replay from the decoded
   handlers (skills §26.2) scores our `refuse_press` press by press against E4
   accept/refuse; any disagreement names a second gate rather than being fitted away.
7. **Refusal sentences** (REX-5). An id-to-condition table for the 1934–1993 block (60
   readable, 6 encrypted; ids committed, text resolved at run time; anchors 1960 39/39,
   1961 OBSERVED per skills §38.2, 1934 1/1), RECONSTRUCTION, behind a default-off flag;
   the weapon gate (`authsrv.py:17926-17932`) is the only real consumer.

**Acceptance.** (a) `adrenjoin --by-connection` reports 0 gains on all three dark-bar
connections and ≥ 280 on `20260818T132739`; a sandbox caster with no adrenal skill produces
no 0x00CF on a landed hit in `test_adrenwire`. (b) The interrupt reader reproduces exactly
2 property-35 messages corpus-wide (59 = 34, 49 = 12, 10 = 92 as denominators) and the
server's batch in `test_mechanics` is byte-order identical to batch 1. (c) The recharge
join prints per-skill minimum gaps and a synthetic re-created agent id does not produce a
sub-recharge gap. **FAILS** if the reader finds a third [35] (the denominator and the
write-up are wrong), or the recharge floor is not met after the re-create split (the anchor
stays RECONSTRUCTION).

**Value.** Four RECONSTRUCTIONs replaced by OBSERVED rules on the R4b substrate; R4b's
first Interrupt exemplar with an OBSERVED wire shape; floating numbers attributed to the
right skill on every hit; one staged live run out of the owner's queue; hostile casters at
retail cadence (today 20 % more casts for a 1 s / 5 s spell); "Charge!" reaching the heroes.

**Cost.** M overall (S + M + S + S + S + S + S). **Client dependency:** none for steps 1,
3(a–c), 4, 6, 7; final-confirmation-needs-run for step 2 (a body victim carrying [35] is
unwitnessed) and step 5 (the hero's cure on screen). **Dependencies:** none; D6's Dazed arm
rides step 2; D8's cast policy sits on step 4.

**Risks.** Interrupt n = 2, both with the PLAYER as victim; a third gate variable for
adrenaline is not excluded by any tape (step 1 names it); the recharge minimum gap bounds
AI policy as well as recharge; the shout attribution heuristic is ours and the context is
PvP.

**First session.** CRP-1 end to end: `adrenjoin --by-connection`, skills §34.11 with the
rivals named, the gate in `player_gains_adrenaline` reading the current bar with the
dark-to-armed caveat at the call site, the two tests updated, `adren_gate.txt` withdrawn,
PLAN-LOG entry, §8.2 trimmed to the rounding half. One commit, one live run fewer.

### DESKWORK-D4 — skill coverage in bulk: labels parsed from the archive's own description templates, refereed by the client table, served as a marked tier; then the timed effect types

**Thesis.** Only 54 of 1,333 player skills do anything beyond their icon, and the label
machinery (damage, heal, the condition join, armour-respecting types) is client-proven, so
coverage is a data problem. `PLAN.md` §4 A6 designed the referee — every progression must
equal the client table's endpoints — and nobody built it. **The submitted route rested on a
third-party dataset (gw-skilldata) and a licence gate; the operator judge's probe removes
most of that.** The owner's own archive holds every skill description as a TEMPLATE with
`%strN%` placeholders, which skills FINDINGS §3 OBSERVED filling from the row's own scale,
bonus and duration on the client. Probe (the operator judge's, **reproduced exactly by the orchestrator** the same day with
its own script: `textrec.TextIndex` + `skilltable.parse_record` over the 2026-07-29 client
snapshot `vault/client/2026-07-29_221c13772c7a`, counting `%strN%` in each description): 1,265 of 1,333 player-usable rows carry a
`%strN%` slot, 0 unreadable; str1 1,090, str2 582, str3 685; the words after a slot
include "fire damage" 33, "cold damage" 43, "lightning damage" 39, "holy damage" 35,
"earth damage" 29, "health" 84, "energy" 70, "health regeneration" 35, "health
degeneration" 32, "second(s)" 872.

**Keys.** CRIT-4 (amended), CMB-1, CMB-2. Open at `PLAN.md` §4 A6 (never executed);
review §3.3 ("skill transcript" never defined); `PLAN.md` §3.2's dissent on R4b
generality; skills §16, §47.

**Steps.**

1. **Reproduce the probe, then map the slots.** Re-run it in the tree; then the one
   check before anything relies on it: which `%strN%` index maps to which field, through
   the `skill_arguments` bitfield (some templates put "seconds" after a non-duration slot;
   some carry constants as literals — Deep Freeze's "66%%" is text while its bonus_scale is
   66/66). Correct `PLAN.md:35` and `:801` (gw-skilldata recorded as MIT; the critic's
   unrepeated fetch says the data is GFDL / CC BY-NC-SA) as a docs fix — the dataset is
   now the fallback, not the source, so no §6.1 row is owed until it is used.
2. **Coverage census** (CMB-1 step 0; also Q7). For each of the 1,333 `skills.toml` rows,
   whether it resolves an episode (EFFECT_TYPES), a damage, heal or condition label, or
   nothing, by `type_code` (probe: 517 cast-resolving types with a scale bit, 37
   modelled; foe spells with scale 145 / 7 modelled; attacks with scale 166 / 17;
   ally/self spells 96). Grades for the sandbox's "modelled" mark. Ships alone at S.
3. **Parser + referee.** A stdlib reader of each template's slots and the words around
   them into a label ("Fire damage", "Heal", a condition name) and a slot index; every
   slot must equal scale0/scale15, bonus_scale0/15 or duration0/15 of the SAME client id
   (PvP/PvE split ids joined correctly); a disagreement is a hard conflict listed, never
   fitted; a classifier flags conditional or compound skills ("if", "for each", "while",
   "adjacent", "when...") and area skills ("All foes in this area", which D6 needs) as an
   enum per row, exporting no text.
4. **Emit** `vault/content/skill_labels.toml` (`source = "client-table"`, extractor and
   build per row, `verified` = the slot match) merged UNDER `world.toml`'s 54 hand rows;
   the server reads `scale_means` / `bonus_scale_means` / condition labels carrying
   `tier = 'label'` so the log and the sandbox's "modelled" grade say "label-only" — the
   fidelity judge's condition: a skill that deals its damage and drops its "if" clause
   must not read as modelled. Every generated row gated by `type_code` as well as label
   (`authsrv` ~3262 "A LABEL DOES NOT SAY WHEN": Ignite Arrows' "Fire damage" is a
   preparation). The gate: descriptions are ArenaNet's authored text; what leaves the parse
   is a label enum, a slot index and numbers, into the vault, never git.
5. **Residue** — the 68 rows with no slot and any referee conflict — via the dataset
   (after its licence is settled and the owner's go-ahead) or the browser crawl
   (`/api.php generator=categorymembers`, 50 pages a call, revid recorded). Final Thrust
   (client 1..40 vs wiki 5..40) is the precedent for a currency mismatch.
6. **EFFECT_TYPES** (CMB-2). Admit 24 Item Spell, 25 Weapon Spell, 26 Form, 28 Echo and
   16 "Skill" (80 rows; `effects.resolve_duration` corroboration at rank 12: 14/17,
   20/22, 8/8, 12/12, 21/21); a GWW read for each type's one-at-a-time rule before it
   joins EXCLUSIVE_TYPES; weapon spells on the ALLY_TARGET path (18 of 22 ally); leave
   wells and wards (D6), Chant 27 and type 22 out; flag revert; register the loopback
   press-one-of-each run.

**Acceptance.** (a) The referee runs over all 1,333 rows and reports agreements, hard
conflicts and unparsed by `type_code`; a run in which Sever Artery and Faintheartedness
(hand-verified slot agreements) disagree with their client slots is a broken referee, not
a finding. (b) The served overlay changes none of the 54 hand rows' behaviour
(`test_skilltable`, `test_skilldamage` green with the overlay loaded). (c) A second weapon
spell on one target replaces rather than stacks, per the GWW rule, in `test_effects`.
**FAILS** at step 3 if fewer than half the slot-bearing templates land in the server's
label vocabulary — then the label route is refuted for the residue and coverage is
per-skill work.

**Value.** R-SANDBOX from 54 skills that act toward an estimated 300–400 (step 2
measures it) — the owner's ability to play any bar they slot; R4b generality past the
Pre-Searing families; 80 skills gain an icon, timer and expiry; the substrate D7's costs,
D8's cast policy and D9's "modelled" grade hang on.

**Cost.** M (was M-with-dataset / L-with-crawl). **Client dependency:** none for the
labels; final-confirmation-needs-run for step 6's icon and timer (an unwitnessed effect
type might assert on apply, so it stays flag-gated). **Dependencies:** none.

**Risks.** The probe is one judge's, unreproduced; the str-index mapping may not be
uniform; label-only rows over-simplify conditional skills (the tier flag and the enum
exist for that); zero retail episodes of types 24–28 in the corpus (bufflog census: 313
episodes, none); the dataset fallback still needs the second gate paid.

**First session.** Reproduce the probe; write the coverage census and paste its
by-`type_code` table into studies/skills; do the slot-to-field mapping check; then the
parser + referee and report agreement / conflict / unparsed before any overlay is emitted.
Output: the census, the mapping, the referee's first numbers, the `PLAN.md:35/:801` fix.

### DESKWORK-D7 — the character sheet computes right: eight primary attributes, energy pools by profession, item words on worn pieces, and the custom-profession rung put back on PLAN

**Thesis.** R-SANDBOX's Party tab offers ten professions; the server models only Strength
and Critical Strikes among the primaries, recalls eight of ten energy rows from memory
(`ENERGY_BY_PROFESSION`, `sandbox.py:103`), and reads attribute bonuses from a declared
field instead of the item's own 542/543 words. No non-test module mentions Expertise,
Energy Storage, Fast Casting, Soul Reaping, Divine Favor, Spawning Power or Mysticism
(grep, three lanes). Every build other than Warrior or Assassin plays with the wrong
energy, costs or cast times. The same hooks are where a custom profession's passive goes
(RESKIN §20), so the MODDABLE arc belongs here.

**Keys.** CRIT-3, BEH-11, CRP-9, CMB-8, CRIT-7 (amended). Open at `PLAN.md` §8.1 (the
energy item); `test_pools.py:140/631` EXPERTISE_SPENDS as a scoring aside; itemmods §5.7,
§7; profession MODDABLE §9 (`## 9. Open items and NOT FOUND`, line 898) — no §3 row, no §8
line.

**Steps.**

1. **Energy.** Relabel five rows OBSERVED from the wire, each naming its connection and
   stating that the value includes the profession armour's bonus (W 20/0.033 → 2 pips; R
   25/0.0396 → 3; N 30/0.044 → 4; Me 30/0.044 → 4; A 25/0.0528 → 4; the bare 20/0.033
   appears on other connections of the same characters as the no-armour base); exclude
   connections whose 41/43 changed for morale; browser-read GWW "Energy" for Mo, E, Rt, P,
   D (recall disagrees on P and D); pin literals in `test_sandbox`; PLAN-LOG line.
2. **Primaries**, each with a `--no-<attr>` switch, applied to player, heroes and bodies
   alike (SKILLS-WK's lesson: Weakness reached only the player's wire): Energy Storage +3
   max per rank in `player_max_energy` (`authsrv.py:21348`) and body pools, resent as
   0x009F 41 on a rank change; Expertise 4 %/rank off attack skills, touch skills,
   preparations, rituals, with JARIN's 14 of 15 for skill 392 at rank 1
   (`20260914T005758`) as the OBSERVED check; Fast Casting on activation and Mesmer
   signet recharge; Soul Reaping on a nearby non-spirit death with the cap; Divine Favor
   on a Monk spell cast on an ally. Spawning Power, Leadership and Mysticism recorded as
   waiting on unmodelled families.
3. **Item words.** `equipped_attribute_bonuses` (`authsrv.py:17586`) decodes each
   equipped item's `modifiers` through `itemmods.attribute_bonuses` over weapon, offhand
   AND `agents.PLAYER_ARMOUR` (543 stacks, 542 takes the max per attribute, bit-31 words
   refused — the WORN rune form is unmeasured); the declared `attribute_bonus` becomes a
   cross-check; 574 armour penetration only after a codescan of handler 0x009241AB says
   which argument is the percent and which the chance.
4. **Custom professions.** Ask the owner whether "arbitrary N custom professions" still
   stands (§8 Q5); if so, a `PLAN.md` §3 row from RESKIN §13 and one §8 line pointing at
   MODDABLE §9; run §9's static rows with `codescan --dis/--xrefs` on 38797 and the newer
   builds (which of the 19 0x33 sites are BOUND checks vs SENTINEL compares; attribute
   ids ≥ 51; whether the two 3,443-entry arrays at 0x00C07E20/0x00C0B3EC can grow; who
   builds the 0x0059 dword), each MEASURED or a floor.

**Acceptance.** (a) An Elementalist at Energy Storage 12 shows max energy = base + 36 in
its 0x009F 41 word, and the JARIN spend replays as 14 of 15 through `pools.spend_fraction`
under Expertise 1 — a positive assertion in `test_pools`. (b) A composed headpiece word
raises the panel column and a 542 pair does not stack, in `test_itemmods`. (c) Every
relabelled energy row names a connection whose 41/43 pair reproduces it. **FAILS** if the
wiki's Expertise curve does not reproduce 14 of 15 at rank 1 — the OBSERVED point refutes
the WIKI rule and the route stops to ask the tape.

**Value.** Fidelity of something shipped (R-SANDBOX for eight professions, every hero
pool); the item authoring surface for the mod platform; a two-sources-of-truth hazard the
hammer row itself flags removed; the custom-profession target visible to cold sessions.

**Cost.** M. **Client dependency:** final-confirmation-needs-run (the client may compute
displayed costs itself; the 0x003A/0x003B panel columns followed the server's words on
`20260820T113942`). **Dependencies:** D4's labels for the skills Expertise touches.

**Risks.** Five of eight attributes are WIKI-only on this corpus (0x003A shows Strength on
13 captures, Expertise on 2, Critical Strikes on 2, the rest on 0); the wire energy values
include armour (a wrong constant if relabelled without the caveat); the 574 half needs the
handler read first; the owner may have parked custom professions.

**First session.** Step 1 end to end (relabel with connection citations and the armour
caveat; browser-read GWW Energy; pin in `test_sandbox`; PLAN-LOG line), then Energy Storage
and Expertise with switches and the JARIN check. Output: a trustworthy energy table and
two primaries live.

### DESKWORK-D12 — status you can trust: one index over captures, plans, switches and open client questions, a negatives register, then PLAN.md back inside Read's limits and HANDOFF current

**Thesis.** Four §8 items were answerable from tapes 3–8 days old; 33 staged plans in
`vault/plans` have no index and two pre-registrations (`refusal_feedback_e11`,
`refusal_animation_e12`) are cited nowhere; 105 `--no-*` switches have no exposure record
so "zero exposure is not a null" has no instrument; §3.2 quotes counts from 08-27 the
tree no longer produces (`python toolkit/content.py` → map 19, npc 60, quest 2, spawn 20,
skill_effect 54 against "map 15, npc 56"); and `PLAN.md` (303,720 B, 2,174 lines) fails a
plain Read outright and cuts §8 at line 2,000 — the failure the 09-17 split existed to fix.

**Keys.** CRP-4, CRP-5, CRIT-1, CRIT-2, INF-1, INF-V1, INF-11. Open at `PLAN.md` §8.2 (the
run questions), §3.2 (stale counts), §7 Q1/Q2/Q5 (no ruling prep); review §1d (the
"sunset shopping list" never written); the gap is the survey's own for the ledgers.

**Steps.**

1. **`toolkit/authsrv/corpus.py`** (stdlib): one row per connection — capture, origin,
   build from the c2s 0x000B user-agent "Gw/NNNNN.0 (Win32)" (29 of 36 live: 38797 ×3,
   38833 ×7, 38849 ×6, 38888 ×13; exe sha256 fallback; never a directory name), plan and
   planseal seals, marks, map id (0x0199 f2), file id (0x0195 f1), arrival, duration, the
   player agent, profession and level, bars, hero ids, deaths, zone sequence, weapon sets,
   opcode histograms; for ours the recorder's line-2 flags dict and the harness banner.
   Computed on demand (~5 s live, ~50 s ours), a disposable scratch cache, no state of
   record; a `--where` small enough for "c2s 0x001F present", "death then a later
   connection", "bar has no adrenal skill and prof=1"; `test_corpus.py` with floors and a
   vacuity guard.
2. **`--negatives` register.** Every study-level absence claim as a named query with
   today's count — MORALE-Q5 boosts, the 542 on a worn piece, retail's 0x005E reply,
   0x0191, the SLIDE class (0 of 363), Isle definitions 130/139/146 (unseen in 96
   connections while 129 and 131 are seen), the adrenal dark-bar set, hero adds — each
   moved count written into its study with corpus size and date.
3. **The run ledger** (CRIT-1). Join `vault/plans` (33) to live manifests and the
   harness/gamesrv directories (23 RAN by manifest; 10 with no live capture, some likely
   loopback); mark each RAN, MOOT or OPEN with evidence; sweep §8, §8.2, sandbox PLAN §3,
   weapons RUNSHEET, isle HANDOFF §4 and every final-confirmation-needs-run step in this
   document into one row per client-only question (prediction site, exposure floor, regime:
   loopback fixed-UI agent-pilotable / loopback owner-driven / live secondary); pack into
   the fewest runsheets by shared rig, sealed by planseal; live-only rows get review
   §1d's substitute and priority columns; point §8.2 at it under the same-commit rule.
4. **The mechanics ledger** (CRIT-2). Parse `serverargs.py`'s 105 `--no-*` switches; per
   switch the captures where it was on (314 of 1,553 carry the flags dict; 181 distinct
   flags; 29 never true such as ANIMREF_E3_RELEASE, D1_LEAD, HERO_SWAP, RESYNC; the newest
   weapons switches on in 3 captures each), "armed" distinguished from "fired"; join to
   the tests and content rows naming each (MONSTERAI-J passive/group: none); compute
   §3.2's counts from the same inputs and print a dated table; a check modelled on
   `test_checks`' §8 ceiling that reddens when §3.2 quotes a number the tool no longer
   produces.
5. **PLAN.md compaction.** §3 (lines 338–726, 148,903 B, 49 % of the file; R3's cell
   43,636 B) becomes one row per rung — marker, dated criterion evidence with commit
   stamp, pointer to the arc doc — with each cell's history moved byte for byte to
   PLAN-LOG under a "§3 history" header using 01639d69's kept-plus-moved reassembly
   assert; re-derive the R4a ("half" beside "BOTH MET 2026-08-11"), R4c ("not started",
   newest date 08-20, while the slice's AI, spawns, boss and quest landed 09-12) and R5
   markers as PROPOSED wording for the owner; the closed §7 questions (43,049 B over 605
   lines) keep the ruling paragraph and lose the argument to a "§7 history" header; a
   whole-file ceiling under 256 KB and ~1,800 lines in `test_checks.py`; citelint,
   identlint, provlint, seclint green. Q1 lands first.
6. **Orientation** (INF-11). Ruling-prep memos for §7 Q1, Q2 (no `.wasm` anywhere in
   the vault; cost the symbol-bearing archived build as a function-name source for D1
   under the second gate) and Q5 (step 4's table is the current scorecard; presearing
   MANIFEST's gap table is dated 08-06); rewrite `HANDOFF.md`'s top annotation (last
   edited 08-20: "~18,000 lines of Python server" against 35,232; the language decision
   "still open" resolving only in PLAN-LOG) to private server plus mod platform with
   nothing deleted; propose ONE sentence on what the project is for HANDOFF's top and
   CLAUDE.md's first line.

**Acceptance.** (a) `corpus.py --where 'c2s 0x001F present'` returns exactly one
connection (`20260916T150306` conn `10.0.0.210:62321`) and `--where 'bar has no adrenal
skill and prof=1'` the two WARRIOR-PRE connections and nothing else. (b) The mechanics
ledger's §3.2 numbers equal `python toolkit/content.py`'s and its check goes red on a
fixture quoting "map 15". (c) After step 5, `Read(PLAN.md)` with no offset succeeds, §8's
last line sits inside the first 2,000, and kept + moved reassembles byte for byte.
**FAILS** if the run ledger cannot classify every one of the 33 plans (the join is
incomplete), or a moved §7 argument breaks a CLAUDE.md or study citation.

**Value.** The cost of every future session: "is there a tape where X" and "has this arm
ever met a client" become one command; the owner's client time bundled into three or four
runsheets; the status authority derivable instead of transcribed and readable in one Read.

**Cost.** L overall (M + S + M + M + M + S), every piece standing alone. **Client
dependency:** none (CRIT-1 is prep-only). **Dependencies:** Q1 before step 5; D10 and D13
consume the index; D11's landings need the R5/R5m rows rewritten here.

**Risks.** Scope creep into a database (a stdlib CLI over existing decoders, no state of
record); a ledger nobody updates becomes a second stale §8 (it rides the same-commit
rule); the §3 move touches a table parallel sessions stamp at every landing (one short
commit between arcs); the flags dict exists only in newer captures, so earlier exposure is
unknown, not zero.

**First session.** `corpus.py` over live and ours with the row schema and the 0x000B build
read, three `--where` queries as tests, the `TESTS.md` entry; the `vault/plans` join
printing RAN/MOOT/OPEN for all 33 with the two orphaned pre-registrations flagged. Output:
the tool, its test, the plan-status table in a new studies/method section.

### DESKWORK-D9 — the operator's authoring loop: the Enemies-tab picker with passive and group, template codes as the build format, content hot reload on a zone change, quest verbs, gold, loot

**Thesis.** The sandbox is where the owner plays and authors, and the loop today is edit,
relaunch the stack, look. N1, the owner's named next item, is a picker; a template code defines a
whole bar with ranks faster than any picker and `skilltemplate` is written, verified on two
client-produced codes (TEMPLATES §7.1) and has no consumer; hot reload is R5's unmet
server-side leg (`authsrv.py:149`: none exists); quests can only be "talk" or "kill one
named spawn", pay no gold, drop no loot. The operator judge found N1 smaller than framed:
the rank rows already name attributes through `attr_label` (orchestrator.py ~245) and
`passive`/`group` are already compiled (`sandbox.py:672-673`); what is missing is the
filterable list and the checkbox.

**Keys.** BEH-10, CRIT-5, WLD-7, BEH-9, BEH-7, BEH-8, BEH-V4. Open at `PLAN.md` §8.1 "The
sandbox" N1; sandbox PLAN §2; `PLAN.md` §3 R5's "hot-reloaded" clause; presearing
MANIFEST:707 (TIMER); quests HANDOFF §1; `content/quests.toml`'s commented `reward_gold`.

**Steps.**

1. **N1.** Replace the eight `QComboBox` slots (orchestrator.py ~186–280, 554–583) with
   the Skills tab's list widget (profession filter, text search, D4's "modelled" grade)
   plus a rank editor; a per-member `passive` checkbox and group exposure; `test_sandbox`
   asserts the overlay carries `passive = true` and the group key; `--smoke` drives the
   widgets (offscreen QPA hangs).
2. **Template codes.** An optional `template = "..."` on enemy and hero rows;
   `skilltemplate.decode` → pair, eight skills, ranks; `validate()` refuses a bad code
   naming the clause; export any row and the player's stored bar to a code; a paste box;
   tests on the two §7.1 codes. For the PLAYER the in-game Load Template window is the
   route since B7 moved bars in game — a U5-shaped client question.
3. **Hot reload.** Put the scope to the owner FIRST (§8 Q4): rows hot, geometry per
   launch (the client holds `Gw.dat` exclusively, AUTHORING §5). `content.reload()`
   re-reads `content/`, `vault/content` and `RURIK_CONTENT_EXTRA` into a fresh World,
   validates completely, swaps `agents.WORLD` only when valid; triggers: every new game
   connection and an operator chat line with a reserved prefix; clear `_QUEST_ROWS`; list
   at startup the import-time globals that do NOT reload (ENEMY_*, HERO_ROWS, PLAYER_* at
   `authsrv.py:10811, 11436-11652`) — spawn rows are read from `agents.WORLD` at
   population time, so a spawn-and-quest-only reload already covers the Enemies-tab loop;
   never re-place agents mid-instance; tests in `test_population` style.
4. **Quest verbs.** An ordered list of objectives (talk / kill / kill_count(definition or
   group, N) / enter_area / timer / deliver); kill_count as a tally at `kill_agent`'s one
   choke point with live 0x0054 text; enter_area against the player's position each tick;
   TIMER per MANIFEST:707 (a server-side schedule) or say why a countdown was chosen;
   each verb ships WITH a quest row using it (`authsrv.py:413-418` refuses a mechanism
   nothing exercises); 0x004C before 0x0054; `test_quests` per verb.
5. **Gold.** Pay `reward_gold` with 0x0140 [key, gold] (`merchant.py:109`; the sell arm
   already sends it); check field 1 of the tape's [2, 25] against that connection's
   0x0144 stream key to make "gold is the guess" OBSERVED; reorder the hand-in to quests
   §12's observed batch; a persisted purse in charstore or say there is none; fix
   `authsrv.py:355/374`'s "NOT GRANTED" and quests HANDOFF §1.
6. **Loot** (low confidence). Census the death drop burst (0x0135, 0x0168, the kind-0
   create 25 u away; 12 records in 4 captures) and the pickup (c2s 0x003F, UPSTREAM; 4 in
   2 captures); a drop row on spawn or npc templates (rates are the operator's, not
   recoverable), the burst at `kill_agent`, a pickup handler into the backpack.

**Acceptance.** (a) `--smoke` passes with the picker; a pasted client-produced code
populates a row `validate()` accepts, and a code with a skill outside the run's unlocks is
refused naming the clause. (b) A spawn row edited on disk appears in the next zone-in
without a restart; a malformed row leaves the old world with a logged refusal; no agent is
re-created before a zone change. (c) A kill-count quest advances on the Nth kill and not
the (N-1)th, and the hand-in batch order matches quests §12's tape. **FAILS** if the
import-time-global list is empty (the inventory was not done and the reload silently
misses party and hero rows).

**Value.** The owner's iteration cost on every sandbox run; their named N1; R5's
"hot-reloaded" clause; operators get quest verbs, rewards and the build format the
community already trades in.

**Cost.** L overall (M + S + M + L + S + M); steps 1–3 ~3 sessions. **Client dependency:**
none for the machinery of 1–3 and 5; final-confirmation-needs-run for "walked after a
reload", the Load Template window against our writes, the count placeholder's wire form,
loot on screen. **Dependencies:** D4's census for the grade; D8 for leash and patrol
fields; D12 for the R5 row rewrite.

**Risks.** PySide6 offscreen hangs (`--smoke`); a reload touching the ~40 source-locked
functions reddens unrelated locks; the owner may read "hot-reloaded" as including geometry;
loot evidence is thin; TIMER's two readings must be settled first.

**First session.** Ship N1 (picker, checkbox, overlay check, a `--smoke` step), the
template paste/export path with tests on the two §7.1 codes, and write the §7 hot-reload
scoping question. Output: a working Enemies tab, template codes in specs, one owner
question.

### DESKWORK-D14 — operational readiness: back up the irreplaceable vault tier, write the build-landing half RUNBOOK lacks, and let updatecheck see a stale install

**Thesis.** The vault is "the only part of this project that cannot be rebuilt"
(RUNBOOK §"Backing up the vault"). Its mirror is **same-disk by its own description**
(`C:\gd\Rurik-Backups\vault`, RUNBOOK:859), last run 2026-08-06 at 20.9 GB, on a disk 86 %
full with ~273 GB free; it covers an overwrite and not the disk dying. The next ArenaNet
build is due on cadence (Jul 29, Aug 13, Aug 20, Sep 1); the registration half of landing
one lives in a single auto-memory note and took two sessions for 38888; when 38849 arrived
mid-run via `run-live`, `updatecheck` truthfully reported "nothing changed" and 0 keys were
tapped. **No protection exists until the owner picks a medium** (§8 Q1) — the desk output
is a census, a manifest and a recipe.

**Keys.** INF-6, INF-7, INF-V2; PRO-10 (the cross-build shape guard, from D2) belongs
beside the landing checklist. Open at RUNBOOK §"Backing up the vault" (the "one thing that
blocks going off-disk"); RUNBOOK's update section (276–531) ends at the cage; crossbuild
FINDINGS §7.6; the 38849 incident is the survey's own finding.

**Steps.**

1. **`vaulttier.py`**, read-only: classify every top-level vault path IRREPLACEABLE /
   REGENERABLE (with the regenerating command) / EXPERIMENT RESIDUE, sizes by `lstat`
   (junctions lie to `islink()`); a sha256 manifest of the irreplaceable tier (`client/`
   ~20 GB across five build snapshots named by sha prefix, `keys/`, captures
   jsonl/json/log ~0.9 GB not the PNGs, `captures/live`, `mirrors/` 2.2 GB with
   `gw_in_browser` 404 upstream, `research/` 675 MB, `labelling/`, `content/`,
   `updatecheck/`, `state/`); a robocopy recipe limited to that tier (~24 GB) with a
   verify pass against the manifest and the scrub's exclusions; a retention proposal
   (harness PNG 57.4 GB in 19,309 frames; exports/archivewrite 40 GB over 10 run dirs;
   `dat_*` 20 GB; `run/` 52 GB) — nothing deleted, nothing copied off-disk without the
   owner.
2. **RUNBOOK's registration half.** The list the 38888 landing actually needed: the
   `pinned.BUILDS` row with both patched copies' sha256, `test_buildid` EXPECT, the
   dh_params fingerprint via `dump_dh_params.py --full`, both `make_run_dir` builds, the
   SUITE-family rows (`test_msgshape`, `test_avevents`, `test_srctree`), buildpins +1,
   `test_quests` MAP_ID_COUNT_BY_BUILD, `framebus.TABLES`, VA relocation by masked byte
   search — from the memory note and crossbuild §7.6. Add PRO-10 here: a `test_catalog`
   section diffing `msgshape --all` across `pinned.BUILDS` against the schema with a
   per-build exception table (38888: SEND 0x0092 0x700b → 0x740b; 2026-04-30 → 38797:
   RECV 0x008C +u8, RECV 0x0092 +u16, SEND 0x0090 +u8) — verified at exactly one change
   38849 → 38888, and only useful if it exists before the next build.
3. **Relocation helper** as a `sigcorpus.py` extension: masked abs32-in-image and
   rel32-after-E8 search; a test relocating the recorded 38797 → 38888 pairs (11 of 11,
   4 of 4); optionally `toolkit/newbuild.py --plan <stamp>`, a read-only DONE/MISSING
   checklist. Never launches or patches under `C:\gw`; never picks a build by sort order.
4. **`updatecheck --exe <path>`** and stale-install detection: a read-only diagnosis
   (buildid, DH fingerprint via `dhbuild.read_params`, a `keytap_patch.TAP_SIG` hit
   count) that never writes a baseline for a binary with no vault snapshot; in the live
   driver's preflight and `dhbuild`'s audit: if any `run-live` build reads HIGHER than
   `pinned.identify(C:\gw)`, print "your install is behind; launch it once"; a synthetic
   pair test; RUNBOOK 436–441's manual diagnosis replaced by the flag.

**Acceptance.** (a) The manifest verifies byte for byte against the copied tier and the
copy's size is within 10 % of the census total. (b) A synthetic vault with `run-live` at
N+1 and an install at N makes the preflight print the stale line, and equal builds do not.
(c) The relocation test reproduces all 15 recorded pairings, and the shape guard reports
exactly one change 38797 → 38888 and zero across 38797 → 38833 → 38849. **FAILS** if
`updatecheck --exe` on the pinned 38797 snapshot reports anything but build 38797, DH
"stock" and TAP_SIG 0.

**Value.** Protects the one asset no future update brings back; frees disk that archive
and harness work need; the 38849 failure becomes a one-command diagnosis; the next
field-width change is caught by a scanner instead of a stopped framer (0x0092 cost a
session); R0b resumes sooner after the next update.

**Cost.** M. **Client dependency:** none. **Dependencies:** none.

**Risks.** Deleting data and choosing media are the owner's; an off-disk copy still needs
the scrub; the runner must never touch `C:\gw` or rank builds by filename.

**First session.** `vaulttier.py`'s census and manifest, the tiered recipe written but not
run and handed to the owner with the retention proposal and the medium question, RUNBOOK's
registration half with the shape guard. Output: a census table, a manifest in the vault, a
RUNBOOK section, one owner question.

### DESKWORK-D6 — area spells and the last two conditions: Fire Storm as the areas-over-time template, the seven area hexes with Deep Freeze's snare row, Dazed and Cracked Armor

**Thesis.** Point-blank bursts and Fireball's splash landed 09-20 (SPELL_AREAS,
`authsrv.py:12769`); areas over TIME and the area hexes are unbuilt (`authsrv.py` ~13004;
`PLAN.md` §8's W4 line). The one such mechanism with a retail witness (15 skills: Meteor
Shower, Maelstrom, Chaos Storm...) is dense on `20260817T231139` — 17 Fire Storm casts,
each with the caster's [58] at +2.0 s, three ground-350 0x00A1s, then damage words at +3,
+4, +5 s onto up to four foes with no 58 on the ticks. Deep Freeze's -66 % sits in the
client's own bonus slot (CORROBORATED), and the two icon-only conditions take R4b from 8
to 10 of 10.

**Keys.** CMB-3, CRP-8, CMB-4, CMB-5. Open at `PLAN.md` §8.1 W4; weapons PLAN §38, §40;
SLICE-F48's "no content row" half; `PLAN.md` §3 R4b's condition count.

**Steps.**

1. **`aotjoin`** over `20260817T231139` with predictions stated first: the completion
   batch ([55], [58, caster, 0], ground 0x00A1 [point,0,0,350,0,0] three per cast), tick
   period and count against the record's 10 s, per-target words against property 16 and
   the armour model, who stands inside aoe 156 at each tick; lock the shape in
   `test_weapons` as §38 and §40 did.
2. **`area_over_time`** keyed on target byte 16 + a duration: one ground visual at
   completion, a 1 s tick scheduler on the SLICE-F50 deadline thread striking every foe
   within `aoe_range` of the point for duration0/15 s, phase checked against the tape's
   1 s spacing, a `--no-spell-areas`-style revert.
3. **Mind Burn 185** (the energy-comparison second packet is spellhitjoin P4) and **hex
   179** (hex plus area damage): a row each.
4. **Area hexes.** Type 4 + target 16 + `aoe_range` rows (52 Panic 240, 56 Soothing
   Images 156, 108 Suffering 240, 136 Shadow of Fear 156, 204 Rust 156, 211 Ice Spikes
   156, 234 Deep Freeze 312): apply the hex through the existing path to every foe inside
   the radius, each with its own buff id — RECONSTRUCTION stated in the lock (no area hex
   was ever cast on a live tape); Deep Freeze 234: `scale_means = 'Cold damage'`,
   `bonus_scale_means = 'Movement speed decrease'` on `episodemods.move_speed_terms`'
   existing arm (66/66 in the client table; Storm Chaser 455 is the precedent); the snare
   run closes only SLICE-F48's content-row half; slice 48.3's boost × snare rule is about
   RETAIL and stays CONTESTED.
5. **Conditions.** Cracked Armor 2077 = -20 armour with the wiki's floor, entering where
   Healing Signet's -40 enters (`casting_armour_penalty`, after the cap); Dazed 485 =
   spell activation ×2 on the E4/E3 clock, its interrupt half riding D5 step 2; GWW read
   through the browser; flag-gated; `test_mechanics` with the no-condition rival as
   control; re-tally §3's R4b row to 10 of 10.

**Acceptance.** (a) `aotjoin` reports exactly 17 Fire Storm announces (13+2+1+1 over
four connections), each with a single caster [58] at +2.0 s and words at 1.0 s spacing —
a phase drift over 100 ms or a 58 on any tick refutes the scheduler design. (b)
`test_weapons` locks the completion batch and a three-foe cluster inside 156 u takes 10
words at 1 s while a foe at 200 u takes none. (c) Deep Freeze's 0x0027 word equals Storm
Chaser's arithmetic with the sign inverted; Cracked Armor lowers panel armour by exactly
20 after the cap. **FAILS** if any of the 17 casts shows a [58] from a second agent, or a
0x00A1 350 appears with no preceding announce.

**Value.** Fifteen area skills from one template; Elementalist, Mesmer, Necromancer and
Water bars act on groups; R4b conditions 10 of 10; the Isle Students' Dazed and Cracked
Armor rings stop being cosmetic; SLICE-F48's open arm closes.

**Cost.** L overall (M + M + S). **Client dependency:** final-confirmation-needs-run (the
ground visual and per-foe hex order; the boost × snare run exercises our arithmetic, not
retail's rule). **Dependencies:** D5 step 2 for Dazed; D4's area enum for the other
twelve areas over time.

**Risks.** The tape's casters and targets are PvP players, so per-foe numbers come from
the armour model and scatter is human behaviour, not AI; no area hex was ever cast live;
Dazed and Cracked Armor have no retail EFFECT witness (a scratch `condwin.py` found none
inside the three retail episodes), so both are WIKI-only.

**First session.** `aotjoin` with the pre-registered predictions, the per-cast table, the
`test_weapons` lock, weapons PLAN §41. No server change until the shape is locked.

### DESKWORK-D8 — hostiles like retail: an ethogram over the tapes, definitions scoped per build, the leash and the caster opening, transcribed populations with patrols, a first cast-policy slice, gadgets on retail maps

**Thesis.** The retail leash (a stander walks home; a patroller resumes its leg), the
caster's leg-to-range-halt-cast opening, the patrol vocabulary and group co-movement are
measured on tape (monsterai N4, N7, N9, §12) and the server models none: a kited hostile
freezes where the leash snapped (`authsrv.py:13838-13839` still says "nothing has measured
retail's leash"), a monk charges into melee, no patrols exist. ~10k unused ambient legs
and 549 hostile casts are a behaviour spec waiting for one instrument. `npcdefs.py` has no
`--build`, so a bare census still refuses on the cross-build drift SUITE-FIXES diagnosed
(7809 is file 141285 at level 5 on 38797-era captures and 16271 at level 20 on 389xx).

**Keys.** BEH-12, BEH-2, BEH-1, BEH-V2, BEH-3, CRP-V1, BEH-4, BEH-V3. Open at monsterai
§7.3, §8.6, §12.9, Q9/Q13/Q15; R4C2-FEASIBILITY §7; `PLAN.md` §3.2 ("skill bars: 0");
`PLAN.md` §3 R4a's spawn-table absence; heroes §5.6 (cast policy deferred deliberately);
enemy PLAN §12.4-12.5 (`ENEMY_MELEE_RANGE = 150` still "Ours"; `content/ai.toml` unbuilt).

**Steps.**

1. **`npcdefs --build`** (also Q5): definition identity scoped by client build; default
   refuses when a pool spans builds and names them; re-emit `vault/content/npcs.toml` per
   build with `build` per row; reconcile `wireshells.py`'s docstring with SUITE-FIXES;
   recount the pre-Searing hostile roster over the September map-146 tapes (1397, 1431,
   1432, 1437); update R4C2 §7 and §3.2; fix `agentroster`'s cp1252 crash on piped stdout
   (`:226`).
2. **Ethogram** (`studies/monsterai/review/ethogram.py`, reusing noticeradius's decode):
   per definition and per map, never pooled across model ids — (a) ambient patrol legs
   EXCLUDING every leg inside a `noticeradius.engagements()` window, leg length, the 2 s
   re-issue, 0x002B speed fractions (0.3472, 1.0, 0.2778, 0.3333), dwell, loop closure,
   correlation with the player (Q9); (b) groups by ≥ 3 simultaneous leg buckets, mates
   joining within N s (Q15); (c) casts per skill per definition (caster v[2], skill v[4]),
   inter-cast gaps, re-casts of a hex already on the target (Q13); pre-registered minimum
   samples.
3. **Leash**, STANDER arm first: spawn anchor at `create_agent_world`; a `leash` row
   field; give-up as distance plus time RECONSTRUCTION (three chases: 1,358/2,111/2,886 u
   over 10/22/14 s); the retail return: 0x002B to walking speed, 0x0029 legs at 2 s to the
   anchor through the A* corridor; check N9's in-chase swings (8, 3, 3) against
   SLICE-F22's halt-swing-follow before touching the mid-follow refusal; the N4 opening
   behind a flag; correct `authsrv.py:13838-13839`; `test_agentlife` drives a fleeing
   player past the leash.
4. **Caster opening**: a "caster" mode for a spell-bar hostile with no ranged weapon:
   inside the first ready spell's range cast from where it stands (4440's shape),
   otherwise 0x002B 1.0 plus ONE 0x0029 leg to range, a halt, the cast (1432's shape); no
   0x002A before the first cast; the range rule RECONSTRUCTION.
5. **Populations**: `agentroster cross_session` on the 11 maps with ≥ 2 sessions (146
   has 9; 148 has 10); static stations vs hostile first-creates (the compass-range entry,
   so any spawn point is RECONSTRUCTION); prediction first (fixed groups vs randomized);
   `toolkit/authsrv/spawnrows.py` writes vault/content rows with ids and positions only
   and per-row provenance (capture, build from 0x000B, extractor), `patrol = [[x,y],...]`
   from step 2, `group` from co-movement; a patrol tick for unengaged rows; serve map 146
   with `--area`; rows say plainly they carry no bars and health for few definitions.
6. **Cast policy, first slice**: re-ask the owner (heroes §5.6); ship only "skip a slot
   whose effect the target already carries" behind a flag (skills §16.1's Hatcher defect;
   `enemy_attack_tick` ~21441 is the waster); the full `usage` engine waits on D4 and the
   answer.
7. **Gadgets on retail maps**: census the gadget creates with their 0x0111/0x010E pairs
   per (map, build), deduplicated across visibility re-creates (606 and 664 messages in
   28 captures); `msghandler` on both to name the fields; an emitter to vault/content
   rows sent at zone-in; INTERACT_GADGET 0x0051 (UPSTREAM) stays unarmed.

**Acceptance.** (a) `npcdefs` runs green over the full corpus with `--build` and refuses
without it, naming both builds. (b) The ethogram reproduces patrolprobe's counts (460
kind-9 patrollers, 9,771 ambient legs, the four top speeds) and reports zero ambient legs
inside any engagement window. (c) `test_agentlife` drives a fleeing player past the leash
and the stander returns with legs at 2 s cadence; a spell-bar hostile opens with one leg
ending at range and never parks at the melee disc. (d) A map with transcribed rows loads
with per-row provenance; one without stays byte-identical. **FAILS** if the engagement
exclusion removes more than half the "ambient" legs (the patrol picture was chase legs),
or cross-session clusters do not repeat within a map (the honest output is a
distribution).

**Value.** The feel of every fight (the owner's own "the Bull had a much shorter return");
R4a past "aggro, chase and swing" and its spawn-table absence; retail explorables served
with retail's placements as the reference population an operator copies.

**Cost.** L (S + M + M + M + L + S + M). **Client dependency:** final-confirmation-needs-run
(feel is the owner's instrument, monsterai §8.6). **Dependencies:** D4 for a fuller cast
policy; D5 step 4 for cadence; D9's tab exposes leash and patrol.

**Risks.** Transcribed creatures carry no bars — Hatchers in retail costumes; the caster
shape is n = 3 over 2 definitions with 4440's positions dead-reckoned; co-movement grouping
is a heuristic; MONSTERAI-J's five retail definitions (§12.9) should be drafted as rows for
the operator.

**First session.** BEH-12 end to end plus the ethogram skeleton reproducing patrolprobe's
numbers with the engagement exclusion printed, not yet written into monsterai. Output: a
working extractor, an honest R4c-2 count, the instrument's first table.

### DESKWORK-D10 — movement: score RUN-R8 and §7 Q14 from the corpus, then the warp instruments, the post-ship exposure that already happened, the tap rate, the out-of-sample re-grant, the follow frame and a STATE page

**Thesis.** Q14 argues from n = 3 armed sessions and "nothing both fired and was watched"
(`planecensus.py:955-956`, hardcoded), while 197 armed captures and one WATCHED fire
(`20260904T110025`: the 0x002C restamp did NOT free the frozen client) sit on disk; the
movement scorecard has no warp row, so four post-ship hard rows on 09-13 — three within
3 s of a wall-slide re-grant, one a 288.6 u snap BACK onto the re-grant's destination —
went unread nine days; every tape'd null under the harness is void because movetap takes a
system-wide thread snapshot on every poll (54–57 ms, a 17.5 Hz ceiling) and both loops
sleep after work.

**Keys.** MOV-4, CRP-3, INF-8, MOV-V1, MOV-11, MOV-1, MOV-3, MOV-8, MOV-7. Open at
`PLAN.md` §8.2 RUN-R8; §7 Q14 (~1615–1623); movecode 1z-di.1, 1z-dd.8; weapons §22 / W2g;
movement HANDOFF §A ("current at 22bfe86", 917 commits behind).

**Steps.**

1. **RUN-R8 and Q14 in one corpus scoring.** Split the 310 banner-confirmed armed runs
   by router banner (251 "ROUTER ON by default" since 1z-v on 09-03; ~55 with no router
   line 08-30..09-03 = R8's "armed, router off" cell, which R8 counted as 2); exclude the
   provoked-lock scripts; score P1 (≥ 15 fire-free minutes) and P3 (plane-37 deck
   crossings, likely UNREAD — say so) on the router-off population; adjudicate the one
   watched fire (the harness pressing 0x003D headings every ~4.7 s from (9783.75,
   8285.95) on plane 29, every grant a fence-shut zero-lead fallback, the body frozen
   ~21–62 s, the restamp at 37.6 not healing it: our own fence-shut echo, not a plane
   lock — MOV-verify's reading); replace the hardcoded line with a computed count; write
   1z-p "scored from the corpus" or withdraw R8 keeping R8b; rewrite Q14 item 1 with the
   numbers.
2. **A warp row in `sessionscore`.** `resyncscore.track_from_capture` per capture; hard
   rows (count, magnitude, per active minute against the quiet-day band — 0 on 09-09 and
   09-12 — and the retail control's 0); attribute each to the nearest preceding movement
   send within 3 s, labelled "suspect", never "cause"; positive control: `--since` on the
   09-13 sessions must flag `authsrv-20260913T174629-c4` and `190815-c5`.
3. **Adjudicate the post-ship warps.** For the 4 hard rows since 20260910T160000, causal
   vs coincident (190815-c5 t=171.48: "KBD LEAD RE-GRANT 1" along the wall turning
   north-west, the body kept north-east, drift 323 u past gate 1's 299.33, then a 288.6 u
   snap at 172.59 onto the re-grant's destination; 174629-c4 t=118.15: sent while the
   guard read gate1-red, jump 438.6 u 0.25 s later); the unattributed 190815-c5 t=142.57
   (649 u in 68 ms); if causal, a gate behind a flag; the slide law's concave-corner
   behaviour RECONSTRUCTION.
4. **Tap rate.** Memoise `tls_blocks`/`_threads_of` per (pid, tls_index) in `movetap.py`,
   re-enumerating only when the TEB32 self-check fails; `calibrate()` times a full poll;
   both loops pace to a deadline (`agenttap.py:352`; at 30 Hz today 33 ms sleep + 57 ms
   snapshot ≈ 11 Hz); a fake-memory selftest shows reuse and invalidation. No agenttap
   tape exists since 09-10, so this pays when tape'd runs resume.
5. **Out-of-sample re-grant.** 1z-di.1's per-grant SHAPE table on the 35 connections
   after 09-10 only (36 new silences with 26 re-grants, 72 %, against 65 % fitted); a
   1z-do section; the SLIDE class still 0 of 363.
6. **`_reach_frame` through a client-walked follow.** The client's follow stop is decoded
   with no weapon term (park at (r1 + r2 + TABLE[kind])² with the target's world-0 as
   destination); a small follow model walks the mirror's copy toward the target and parks
   at that disc so `_npc_mirror_pos`, `_npc_frame` (24188) and `_reach_frame` (24279)
   track the body; retrodict on the weapons runs with a leg row (`20260918T205759`
   onward: the frame should cross weapon range at the swing open, 134.70 vs the leg's
   halt at 134.72); known-bad arm first; check whether the target's own reach gate reads
   the stale range point (UNVERIFIED); only then W2g's split.
7. **STATE page.** `studies/movecode/STATE.md`: every shipped movement arm with constant,
   default, revert flag and landing section, taken from `serverargs.py`; the superseded
   sections; the open list equal to §8's Movement block; re-stamp movement HANDOFF §A; a
   srclint-style check that STATE.md names every movement flag.

**Acceptance.** (a) The router-split census totals equal `planecensus --armed`'s 197
captures / 9,163 position reports / 74 disagreements, names exactly 4 PLANE-REPAIR fires
(20260903T191246, 202051, 214957, 20260904T105954), all in the router-on provoked set.
(b) `sessionscore` on `190815-c5` reads RED with the 288.6 u row at 172.59 attributed to the
re-grant at 171.48; a 09-12 capture reads OK. (c) The fake-memory selftest shows one
snapshot per N polls and an invalidation after a forced failure; the next tape'd run's
agenttap rate ≥ 25 Hz. **FAILS** if the router-off population holds fewer than 15
fire-free minutes outside provoked scripts (P1 unscoreable, R8 withdrawn not scored), or
the cached thread list goes stale without tripping the self-check.

**Value.** Q14 gets a ruling input with data; every session becomes a scored regression
check for the arc's headline defect; certified nulls under the harness for the first time;
a possible snap in the owner's corner regime caught at the desk; the repo's largest arc
(19,928 lines, no index) gets a bounded, checked state page.

**Cost.** M overall (S + S + S + S + S + M + M). **Client dependency:** none for 1, 2, 3,
5, 7; final-confirmation-needs-run for 4, 6 and any gate step 3 derives.
**Dependencies:** Q1 rewords the §8 lines steps 1 and 5 close.

**Risks.** The post-09-03 corpus is scripted open-ground runs, so P3 likely stays UNREAD; a
nearest-send attribution is a suspect; W2g regressed once on the client (1.17 s → 6.03 s);
a hand-written STATE page goes stale unless the lint holds it.

**First session.** Step 1 end to end: the census, the watched-fire adjudication with the
capture and tape quoted, the hardcoded line replaced, 1z-p written or R8 withdrawn, Q14
item 1 rewritten, the PLAN-LOG entry. One commit and a Q14 the owner can rule on.

### DESKWORK-D2 — protocol bookkeeping: earned names into the schema, the D-list and the deck-builder flag closed at the desk, a cross-build shape guard, msgmix on the whole corpus

**Thesis.** Names earned by runs are findable only by grepping sixteen studies; the gamesrv
log prints "?" for 0x0090/0x0091 every session; `test_dispatch` guards one direction only;
the divergence D-list presents landed work as open. One convention decision unblocks a
single reconciliation; the GmDeckBuilder question is already answered in the binary and
needs a write-up. (The cross-build shape guard PRO-10 is scheduled with D14 step 2, where
it pays before the next build.)

**Keys.** PRO-4, PRO-V2, PRO-10 (moved), PRO-3, PRO-6, REX-4, CMB-9. Open at smsgnames
FINDINGS; divergence D1–D8; newopcodes; skills §47.3/§47.5 and `PLAN.md` §8.1's
deck-builder line; `test_msgmix`'s 2-capture retail line; the 0x0020 field-7 contradiction
(mapload §9 / isle HANDOFF §4.4 unit vector vs `overrides.json:1208` world position) the
critic found.

**Steps.**

1. **Convention first**, in smsgnames FINDINGS: how UPSTREAM-only names are held (a
   labelled tier the tests understand, or kept out with a code-side label). Then promote
   the EARNED set with a wire invariant each: 0x002F AGENT_UPDATE_ALLEGIANCE, 0x0191 (map
   change), 0x0084/0x009E/0x003A at medium, D1's four c2s names; resolve the 10
   constant-vs-schema disagreements toward the earned name; add `test_dispatch`'s
   reverse guard; bump the couplings (`test_agentlife` AXIS 3, `test_codec`'s dict,
   `test_dispatch` §7); absorb the 0x0020 field-7 contradiction with a verdict.
2. **D-list sweep**: per item the send site and its count over the 71 recent gamesrv
   sessions (D1 0x0021 0 because nothing despawned; D2 0x00F0 71/71; D5 0x0048 71/71; D8
   0x002B 60/71); a dated status line with commit; D6 a one-paragraph decision citing
   reconstruction §7.8; one PLAN-LOG line.
3. **msgmix widening**: `LIVE_STAMPS` → `livewire.live_captures()` (29 captures, 287,696
   s2c, 241 opcodes), rates split outpost vs explorable, the NEVER-SENT and 0.0x lists
   re-ranked; a floor on corpus size.
4. **newopcodes re-score** over all 29 captures for 0x003A, 0x009E, 0x0071, 0x00B5,
   0x00C3, 0x00C5, 0x00CA and 0x011A fields 3/4 (moved on two tapes, turning two
   RECONSTRUCTIONs into OBSERVED).
5. **GmDeckBuilder closure**: write into skills §47.3/47.5 that the set selector is bit 1
   (value 2) of the word 0x003C writes (0x00815A80 returns [[ctx+0x2C]+0x80C + i*0x50 +
   0x34]; `test al,2` → 0x00817080 character set 0x00DB, else 0x00804840 account set
   0x001D), clear on every identifiable retail local player, so retail and our server
   (word 0) both enumerate the ACCOUNT set; do NOT send 0x003C by default (RESKIN §18.9);
   "bit 2 = PvE vs PvP character" CONTESTED (confounded with map).

**Acceptance.** (a) A gamesrv "decoded" record for c2s 0x0009/0x0090/0x0091/0x008A prints
a name, and the reverse guard goes red on a synthetic armed-but-unnamed arm. (b)
`test_msgmix`'s retail line reads 29 captures. **FAILS** if any promoted row's citation
resolves only to OpenTyria or GWCA — the reviewer checks each promotion's own evidence.

**Value.** Every census tool and log line readable; the D-list, newopcodes and skills §47
stop sending sessions to redo closed work; the deck-builder answer confirms the sandbox's
account-wide Skills tab as the right lever.

**Cost.** M. **Client dependency:** none. **Dependencies:** D1 supplies four c2s names;
D3's ratchet starts from step 2's refreshed D-list.

**Risks.** Upstream names leaking into the schema as if earned; couplings redden unless
bumped in the same commit; the naming convention may need an owner ruling.

**First session.** The constants-vs-overrides join (124 GAME_SMSG constants, 42 unnamed,
10 disagreements) and the dispatch_arms AST (33 GAME_CMSG arms, 11 unnamed); the
convention decision; the EARNED promotions with invariants; the reverse guard; the bumped
counts. One commit, green `test_smsgnames*`/`test_dispatch`/`test_codec`/`test_agentlife`.

### DESKWORK-D3 — load prologue fidelity: a reply-conformance ratchet, the twelve load opcodes named, the unlock bracket and the manifest cache read, and why our client asks 0x008A on every load

**Thesis.** Retail's load prologue (38 opcodes in a fixed order) has never been held
against our server; 17 s2c opcodes retail sends on 97–100 % of loads are never sent, most
unnamed, and two more are ORDER divergences a naive follow-window mislabels as absences.
One instrument scoring presence, order and per-trigger follow, pinned as a ratchet, ranks
the gaps; 0x008A (71/71 of our sessions; only 5 creation connections on retail) is an
unexplained state divergence one function away from its predicate. Its fidelity payoff
arrives only when newly named opcodes are SENT, each with assert risk — score its output as
an instrument and a backlog.

**Keys.** PRO-2, PRO-5, PRO-11 (the 0x001A half; the 0x0018 half moved to D1), PRO-1,
PRO-8. Open at divergence FINDINGS D3, D13.3; smsg §4; tape; `PLAN.md` §3 R2's presence
criterion.

**Steps.**

1. **`toolkit/authsrv/replyjoin.py`**: retail over the 29 live captures, ours over the
   gamesrv "decoded"/"sent" records; per (c2s trigger, s2c) three columns — PRESENCE,
   ORDER against smsg §4's 38-opcode template re-derived over ~90 loads, FOLLOW within a
   window; one reason per row (never sent / sent elsewhere / gated by PLAYER_FLAGS,
   SECONDARY_BITS or the UI overlay / not applicable solo); reuse msgmix's sweep-vs-probe
   split; `test_replyjoin` pins the MISSING set by identity as a ratchet.
2. **Name the 12** on retail's load reply we never send (0x007C, 0x007D, 0x006B, 0x0119,
   0x011C, 0x01BD, 0x01BE, 0x00EF, 0x0107, 0x013A, 0x015A, 0x0115) with the house method
   (grep studies first — 0x0115 gadget-only per GdCliApi:429/430; 0x0107 precedes 0x0020
   26/26; 0x013A PARTIAL, 0x015A WITHHELD; `msghandler --follow --annotate --depth 3`;
   msgshape widths as authority; framebus subscribers; wire distributions); adversarial
   refutation then a critic; `test_smsgnames4` invariants.
3. **The unlock bracket** (AcctCliUnlock): `framebus.py` for the one subscriber of
   0x100000BF and the readers of obj+0x10/+0x20; send the 68 constant 0x001A rows once
   the read says what they gate, as one account's state with per-row provenance.
4. **Manifest, split**: the S half recovers the RIFF fileId the 0x019F handler writes
   (File.cpp:310/311/314; Riff.cpp:128–325) and reads it read-only out of
   `vault/run-live/2026-09-01_44fbd68767a8/Gw.dat` to answer D13.3's 5-of-17; redo the
   digest check over all 136 kind-3 replies; the M half (0x0196's body layout) waits until
   an archive needs a 0x0093 answer.
5. **0x008A**: read the predicate at 0x0084EA20 (the ONE caller of wrapper 0x00852710,
   between MsCliApi:821 and :1900) against what our login/load sets vs retail's; propose
   one field change with the prediction "the 138s disappear" for a later run.

**Acceptance.** (a) `replyjoin` scores s2c 0x008A/0x008B as ORDER divergences (sent in 60
of 71 sessions before the first c2s 0x0090), not absences, and files 0x003C and 0x00B6 as
flag-gated. (b) The ratchet goes red when a currently-sent reply is removed and green when
a missing one is added. (c) The RIFF read yields {map, hash} pairs accounting for the 5 of
17, or records why it cannot. **FAILS** if the 38-opcode template cannot be re-derived
consistently over ~90 loads (order variance refutes "fixed order").

**Value.** Retail fidelity of the load and of NPC and quest interaction (0x003B's missing
0x005D/0x005E chat line, retail 70 % vs ours 0 %); one ranked, machine-checked backlog.

**Cost.** L overall (M + M + M + S + M); the ratchet alone is one session. **Client
dependency:** final-confirmation-needs-run for anything newly sent; the instrument, the
naming, the RIFF read and the 0x008A trace are desk. **Dependencies:** D2 (convention;
D-list refresh as step 0).

**Risks.** A following message is not proven a reply; many names stay PARTIAL; 0x008A's gate
may be client-internal; the `run-live` archive has been played since 09-13.

**First session.** Promote the scratch `pro_replies.py` into `replyjoin.py`; run it over
29 live captures and 71 gamesrv sessions; the ranked table; the ratchet with a removal
sabotage; the `TESTS.md` entry; a studies/divergence section.

### DESKWORK-D13 — suite cost and honesty: the scrub's aligned-block index, buildpins' offset cache, a fresh full census, --since read-site edges, a corpus lane after every capture, a bare-machine pass, the 24 untested instruments, and a line ceiling on authsrv.py

**Thesis.** The full suite is ~44 minutes and two tests account for ~28 of them
(`toolkit/.suite-timings.json`: `test_scrub` 1,203.1 s, `test_updatecheck` 478.4 s;
5,646.6 serial seconds over 212 entries) through costs that grew with the corpus (a
quadratic secret scan, three full calls per run) and with `authsrv.py`
(`get_source_segment` re-splitting 35k lines per literal); `--since` escalates to FULL on
40 of 40 recent commits; corpus-reading tests redden on new tapes and sit red for days;
nothing exercises a no-vault machine; `authsrv.py` regrew 7,887 lines and 271 definitions
in eleven days with no tripwire.

**Keys.** INF-3, INF-2, INF-4, INF-5, CRP-11, INF-V3, INF-9, INF-14, CRIT-6 (the ceiling
only; see §6 on CRIT-6 vs INF-12). Open at `TESTS.md`'s stale docstrings ("~60 s",
"183 s"); `run_suite`'s docstring ("eleven" untested modules; now 24); the bare-machine
invariant in CLAUDE.md that no test exercises; the survey's own finding for the rest.

**Steps.**

1. **buildpins**: precompute the line list and offsets once per file, matching
   `ast.get_source_segment`'s semantics exactly; a differential over the whole tree proves
   the rows identical (2,925 rows, 295 live = `test_buildpins.py:196`'s literal) pinned
   with a sabotage; re-time and fix the docstrings (probe: `scan_file(authsrv.py)`
   54–68 s → 3.4–3.8 s).
2. **scrub**: step 0 passes `check_corpus`'s `leaked()` into §13 instead of recomputing
   (`test_scrub.py:873`; one of three ~250 s calls); then the aligned-block index — for
   secrets of length L any occurrence contains a whole aligned block of size
   B ≤ floor((L+1)/2), so B = 18 covers the 36/40/128 classes (13,955 secrets; the ~12
   short ones keep `find`); §14's real-corpus equivalence with the naive scan must stay
   green and a planted embedded secret must be found; nothing cached or skipped.
3. **Full census**: announce to parallel sessions (disk-bound, 4 workers, WRITES selftest
   captures); run `run_suite.py` against the 09-19 baseline (7000f4d5: 214 green / 2 red of
   216, 13,322 checks, 2,623 s); classify every red before fixing any; record count and
   timings in the commit and PLAN-LOG.
4. **Selection**: read-site edges for non-.py paths from tests' string literals, so a
   docs-only commit selects the lint tests and a `content/*.toml` change the tests
   reaching `content.py` (147 of 218 reach both `authsrv.py` and `content.py` — about half
   the suite for a typical server commit, and only 8 of the last 40 non-merge commits are
   docs-only, so this is worth less than it claims); an unnamed file still escalates; a
   `--corpus` lane over the 35 tests tagged by static scan with a per-tape delta step
   (which pinned counts a new capture moves); RUNBOOK's live-capture procedure gains it.
5. **Bare machine**: two fixtures — `RURIK_VAULT` at a nonexistent path, and a
   fresh-operator vault (client + keys, no captures); classify every test; fix the three
   recorded defect shapes; `run_suite --bare`; a README "fresh clone" paragraph.
6. **Untested instruments**: the 24 modules no test reaches, prioritised by study
   citations (moralescan 5, castgaps 4, warpscan 4, createburst 3, summarycensus 3): a
   smoke test with floor and vacuity guard, or a recorded retire decision; trnhook's
   missing `test_*.py` against Q12(b).
7. **Line ceiling** on `authsrv.py` in `test_srclint` that goes red with "move code out,
   do not raise the number". The carve-out itself (modularize pass 2) is the owner's call
   and is NOT scheduled here — see §6.

**Acceptance.** (a) After steps 1–2, `test_scrub` and `test_updatecheck` each run under
200 s with §14's equivalence and the planted-secret sabotage green, and the buildpins
differential row-identical. (b) `--since` on a docs-only commit selects only the lint tests
and an unnamed file escalates naming itself. (c) `--bare` classifies all 218 tests with
zero tracebacks under both fixtures. **FAILS** if the aligned-block index and the naive
scan disagree on the real corpus — the optimisation is refused, since it is a security
check.

**Value.** About 28 minutes off every full suite and the scrub stops growing with the
corpus; scoped runs honest instead of hand-picked; corpus reds named the day their tape
lands; the bare-machine invariant tested for the first time since the repo went public.

**Cost.** L overall; steps 1–3 are one session. **Client dependency:** none.
**Dependencies:** none; step 3 after 1–2 so one run measures both.

**Risks.** Optimising a security check (prove equal, never assume); under-selection is the
dangerous direction for `--since`; the suite writes captures and contends for disk with
parallel sessions.

**First session.** INF-3 (the cached slicer, the differential with a sabotage, the three
tests re-timed), INF-2's step 0 and the aligned-block index with §14 green, then the full
run announced, every red classified, timings refreshed. One commit per fix plus the census
commit with its count named.

### DESKWORK-D11 — authored places at the desk: cliffs on the corridor, a rendered prop palette and preview, water, compass footprints, the PathFlood walkability predictor, the viewer's reverse index, the archive budget and stale-MFT guard, and map-row naming from the atlas

**Thesis.** W24's five failures were all visible to the owner in thirty seconds and no desk
instrument showed any of them. The verification found the diagnoses sharper than the
seeds: every authored cell on every authored map is tile 0 because deploy passes no tiles;
water HAS rendered on an authored map with no Water chunk (W11); the two created maps have
no footprint, so no compass art can exist for them; the client's own flood classifier is
7.6 KB of readable code with every compiled oracle already on disk. The arc is paused, so
the corridor the owner walks every sandbox run is the target. Ranked last: 8–12 sessions,
visual verdicts on a client, and an arc with four terrain retractions behind it. **Its one
S-cost safety item, the stale-MFT guard, is pulled out as Q4 and should not wait on this
rank.**

**Keys.** WLD-4, WLD-6, WLD-10, WLD-3, WLD-5, WLD-1, MOV-10, WLD-11, WLD-12, MOV-12,
WLD-2, WLD-V1, WLD-9. Open at worldmaps W24-RUN, W11, W23, W25; customarea §28.1, §34, §37;
terrain §10, §13.2/13.3; minimap §6b.2; archivewrite §2.4; `PLAN.md` §3 R5/R5m; maprows
(308 ambiguous rows).

**Steps** (compressed; the route notes carry the full form).

1. **Cliffs**: a corpus pass over retail maps for per-tile slope affinity (dep[tile +
   tag3b], 349/349); `deploy.assemble` passes `tiles` so a steep cell takes the donor's
   highest-affinity cliff tile (today `StrippedTerrain.build` defaults every cell to
   tile 0); multi-cell faces at 60–75° replacing the one-cell 1008 u walls; the
   forbidden-band validator per triangle; the corridor (map 168) first.
2. **Palette and the y-flip**: render every donor prop model (229 in Pre-Searing) with
   `modelviewer --shot` as a contact sheet beside propscan's extents, into the vault
   cache; settle W25's "is model 77 a tree" at RECONSTRUCTION strength; adjudicate the
   tree-placement y-flip (FINDINGS 4, W21–W23) against Ashcoil's compiled head (probe
   archive row 177338); the model → maps reverse index in `modelcatalog.py` (cached under
   `vault/cache` by MFT sha; ~7 min first build) so the Maps tab stops paying ~19 s.
3. **Preview**: `mapexport` accepts a Stripped-only authored build (equals Bloated
   heights on 349/349, customarea §37); headless `import_gwmap` + `gwcam` at the spawn
   (75.000° horizontal FOV, 400 u); a PNG plus a report; every render labelled
   RECONSTRUCTION, never cited as client output.
4. **Water**: step 0 reconciles W11 with W24 (the donor env's two tag6 records decode to
   mode 1, base height 0.0, fresnel gate ON — compare that plane against the plaza dip and
   Ashcoil's pool heights); then the cheapest arm: carry the donor's Water pair verbatim
   (0x20000006 plus the 32 dep ids, the FINDINGS-14 pattern) plus an authorable `water_z`.
5. **Compass**: a created explorable needs a footprint before compass art (maps 167 and
   168 are world 3 with rect (0,0,0,0)); route (a) `footprint.py` rewrites
   `s_missionClientData` in the LOOPBACK exe (world 6's 47 unaddressed tiles) or (b)
   label the area with a map id that has a footprint and accept tilerender's collateral;
   then tilerender on two axes for the 32×128 corridor, datmove journalled, the three
   checksum rules, `datcheck --assert-safe`.
6. **Walkability predictor**: FIRST the cheap refutation the leverage judge asked for —
   retrodict the compiled heads already on disk (Ashcoil row 177338, the corridor, the
   W13 arm heads) with the known thresholds at flood+0x90 plus a slope cut, and see which
   of W24-RUN P3's two slope readings survives; only then `codescan --dis` over PathFlood
   0x0072D144..0x0072EED7 and the six callees customarea §34 names as never disassembled;
   a stdlib predictor validated against every compiled head and 349 retail maps'
   terrain-only plane-0 regions; wired into deploy as a pre-install report.
   `pathmap.locate(x, y, plane)` walking the file's DAG falls out here.
7. **Archive**: Q4's guard first, then `compose --plan` prints the MFT row budget and names
   `--fresh` (the slice archive has 0 slack rows and 1 free row; `--fresh` restores 17);
   AUTHORING/RUNBOOK record that client sessions spend rows.
8. **Map rows**: crop each continent's chunk-tier atlas at 1 texel per cell (OBSERVED,
   minimap §6b.2) for all 632 footprints; rasterise each row's terrain at the same scale;
   score pairs by correlation with pre-registered controls (the 20 forced rows rank their
   own footprint first; shuffled footprints as the null); CORROBORATED at best; the 30
   rows with no footprint stay out of reach.
9. **Optional last**: animation playback rung 1 through the decoded blk2C channels (bases
   ABSOLUTE per archivewrite FINDINGS:1561; unitexport §6 item 3 is stale) with the
   identity-rotation control; rung 2 only if statically decodable.

**Acceptance.** (a) A Stripped build of the corridor carries non-zero tile indices on every
cell steeper than 60° and zero triangles in the 40–45° band. (b) The palette renders all
229 props without a decoder refusal; the y-flip re-score lands props on terrain in one
frame or stays CONTESTED with the residual stated. (c) The predictor reproduces the
walkable set of every compiled head within a stated tolerance and disagrees with
Ashcoil's coil under exactly one slope reading. **FAILS** if the predictor cannot
reproduce the corridor's own compiled mesh — nothing ships to AUTHORING.

**Value.** Authored places that read as terrain in the corridor the owner walks every
run; W24 failures 1, 3, 4 and 5 addressed at the desk; a client compile taken out of every
authoring iteration once walkability is predictable; a desk route to naming many of the
308 ambiguous map rows.

**Cost.** L (M + S + M + M + M + L + S + M + optional M). **Client dependency:**
final-confirmation-needs-run for the visual verdicts (D12's ledger bundles them); none for
the predictor's validation, the archive guard, the reverse index and map-row naming.
**Dependencies:** D12's R5/R5m row rewrite; step 1's render needs step 3 or an existing
compiled head.

**Risks.** Disassembly read and not tested is this arc's signature failure; Blender's
colour space differs from the client's; footprint patching touches the loopback exe and
must coexist with `pinned.py`; the MFT is the one row whose corruption costs the whole
4 GB file (copies only, journal first, never consume `dat_study_38833`); W24's water
diagnosis is CONTESTED by W11.

**First session.** Q4 (the stale-MFT guard) and step 7's budget line as one commit; then
the slope-affinity pass and deploy's `tiles` wiring for the corridor, rendered headless
from a compiled head if one exists. Output: a safe allocator, a visible row budget, the
first textured cliff.

---

## 4. Quick wins

Each is one session or less and stands alone. Q4–Q7 are S-cost pieces the judges asked to
pull out of L routes so they do not wait on their route's rank.

**DESKWORK-Q1 — the §8 and study staleness sweep: one pass, one commit, one PLAN-LOG
entry** (MOV-2, PRO-9, REX-7, CRP-6, BEH-13, WLD-8, CMB-10; S). Seven lanes each proposed a
commit against the same 40 KB section. Retire, with PLAN-LOG entries in the same commit,
the lines §6 lists as closed; **reword, do not close** 1z-dd.8 ("retail half needs a live
corner"; the SLIDE class is NOT FOUND, 0 of 363) and N2 (the kick is on tape; the add is
static); re-tally §3's R4b row to conditions 8 of 10 and strike §3.2's dissolved
owner-ruling sentence. Fix the stale comments — `effects.py:283-287` ("none of them is
modelled"), `authsrv.py:13838-13839` (retail's leash), `:21437-21440` ("no NPC casts
twice"), `:4906-4913` HERO_RIG_0065 ("under test"), `chatdefs.py:79` (1961 is OBSERVED) —
and the study lines: heroes §3.3/§40.6 and RUN-HEROLIB 12.6, quests HANDOFF §1 ("no
reward is granted"), morale row 496, daggers §8 ("property 10 unread"), plansplit's
"(confirmed)" tags, unitexport §6 item 3 (bases ABSOLUTE), minimap §6g.4 ("STILL OPEN",
closed by A3), datwrite's open-questions rows, crossbuild §4d item 3, handshake PLAN §6
("run the three probes"; R1 landed 08-04), `PLAN.md` §3 R5m's "elevation still open",
§8.3 "The archive" (3 of 4 clauses), `test_dispatch.py:191`'s EQUIP_ITEM "(0 loopback, 1
live)" (now 8 across 3 captures), `wireshells.py`'s 7809 explanation. Make `agentroster`
print tokens safely on cp1252. Do not sweep other citations (CLAUDE.md forbids
re-pointing); keep §8 under `test_checks`' 40,000-byte ceiling; run the ~40 source-lock
tests that read `authsrv.py` as text. **Lands before D12's compaction.**

**DESKWORK-Q2 — the movement review's owed corrections: audit all of
MOVEMENT-2026-09-04 §4, not only 1z-bh.7's nine** (MOV-6, INF-13; S). All nine are still
unfixed at HEAD (RETHINK.md:6 "NO policy code until the owner lifts it";
`content/movecode.toml:528` "prunes leading waypoints" with no decode behind it;
`pathmap.py:54-56`; `authsrv.py:23272/:23526` "stand against the wall"; the TICK_SECONDS
comment ~4055 "the client SNAPS"; movetap `calibrate()`'s floor; movesync's owed ~80 %
silence sentence; movement HANDOFF.md:166 "current at 22bfe86"; HANDOFF-WARP.md:37/:100
`--router` REFUTED rows unmarked and :237 citing a PLAN sentence that does not exist).
Review §4 has ~45 correction lines, some applied 09-05 (ROUTER.md:216,
agtrack_guard.py:50), others of unknown status — audit by content, since the line numbers
predate the split. Cite where RETHINK's rule was lifted rather than declaring it lifted.

**DESKWORK-Q3 — late stamps on our tapes: log the answer (0 of 274) and retire the §8
line** (CRP-10, MOV-5; S). The measurement is done: `movesync.late_stamp` over all 1,553
recorder captures finds 274 speed-arm hard rows (71 captures) and 0 late stamps within the
67 ms bound, with a real denominator (207 rows still at or above the arm across the pair;
59 reach the delta test; 8 gated by neighbours). Write it into movement FINDINGS under the
2026-09-17 entry with corpus size, the caveat that our recorder stamps at receive time (the
artifact may be structurally absent), and the 11 stamp-shaped rows implying 85–250 ms
delays as the one residue; update "61 → 64 over 961" to "280 over 1,552"; drop the §8.1
line. MOV-5 needs no separate pass. Optionally commit the probe as `movesync
--late-stamps`.

**DESKWORK-Q4 — the stale-MFT allocator guard** (WLD-V1, from D11 step 7; S). On the slice
archive the largest usable free run is a stale MFT generation (0xF8A5E200, 1,365 of 1,365
records matching live rows), so the next compose there writes into a region the client's
table rotation may reclaim — a silent path to corrupting a 4 GB file.
`datplan.classify_runs` gains a content detector that withholds any free run whose blocks
parse (best of 6 24-byte phases) as a large NON-ZERO majority of records identical to live
MFT rows, all-zero records excluded; regression: `vault/dat_study_38833` withholds
0xF5923800 (2,892,800 B) and the slice/38833-line archives their 0xF8A5E200 (285,184 B) and
0xF8FD7C00 runs, ordinary zero or stale-content space stays usable; a synthetic fixture in
`test_datplan` whose generation head mark is OVERWRITTEN (the 08-17 fix never reached this
case); re-measure every vault run archive; record the W6 decision.

**DESKWORK-Q5 — `npcdefs --build` and the honest R4c-2 count** (BEH-12, from D8 step 1;
S). SUITE-FIXES shipped `capture_build()`/`live_captures(build=)` on 09-16 but `main()`
has no `--build`, so a bare census still refuses. Add it, re-emit `vault/content/npcs.toml`
per build, recount the pre-Searing roster over the September map-146 tapes, update R4C2
§7 and `PLAN.md` §3.2, reconcile `wireshells.py`'s docstring, fix `agentroster`'s cp1252
crash.

**DESKWORK-Q6 — the cross-build shape guard** (PRO-10, from D2; S). Scheduled with D14
step 2 because it pays only if it exists before the next ArenaNet build: `msgshape --all`
diffed across `pinned.BUILDS` against the schema with a per-build exception table;
verified at exactly one change 38849 → 38888 (SEND 0x0092 0x700b → 0x740b).

**DESKWORK-Q7 — the skill coverage census** (CMB-1 step 0, from D4 step 2; S). For each
of the 1,333 `skills.toml` rows, what it resolves and by `type_code`; grades for the
sandbox's "modelled" mark; the by-type table into studies/skills. Ships alone and measures
D4's headline before D4 is chosen.

---

## 5. Parked: needs a client run

One line each, so nobody re-surveys them. D12's run ledger is where they get packed into
runsheets.

- **SANDBOX-B6 and U1–U5**: the owner's first run through the orchestrator window
  (secondary label, two hero bodies, body vs declared profession, four-member pull, an
  in-game build persisting) — also the verdict for D1's N2 arms and D9's picker and
  templates.
- **The Frenzy arm** (skills §48.8): only the RB tape has Frenzy 346 and Reversal of
  Fortune 307 overlapping (5 overlaps) and it is spent; a designed tape with a known-size
  hit under both multipliers.
- **R-ISLE rung 8d's bench half**: a requirement-MET block at effective rank 13 (RUN-1A's
  axe, scythe and spear blocks were all UNMET).
- **MORALE-Q5** (0x009C never exceeds 100 in 159 sightings) and **Q6's field-to-field
  half**: live captures; the outpost half closes in Q1.
- **The 542 rune on a WORN piece** (itemmods §5.7): all 84 words sit on 0x0161 type 8, none
  with bit 31; one capture of a runed character.
- **SKILLS-AD4's clock half** and **SKILLS-B1's (0, 0.5 %) rounding band**: a staged
  low-damage armed hit.
- **Retail's reply to 0x005E** (hero bar swap): 0 in 96 connections; a swap on the
  secondary at human cadence.
- **RUN-WEAPONS-1B, -2, -3** (bow, staff and wand speeds; the burst's retail shape; 570;
  Strength's 1 %; the dodge; set replies; divisor vs strike-level drop) — D10 step 6 is
  RUN-2's desk half.
- **DAGGERS after RUN-2**: a dual whose first strike lands and second misses; the short
  gap on swords; one Javelin for 45 (n = 1).
- **1z-dd.8's SLIDE class on retail** (0 of 363) and the 1z-di/1z-dj corner predictions: a
  staged live wall-slide or a tape'd corner session D10 step 3 pre-registers.
- **RUN-R8b**: the provoked under-deck plane lock and the first deliberate heal trial — the
  only Q14 question D10 step 1 cannot score from the corpus.
- **GROUNDZ-Q1**: which of F6's three candidates causes the sink — a live read at a known
  stair position.
- **ANIMREF §16** (the wired visual ids' appearance) and **§17** (the IAS windup with an
  attack-speed stance running).
- **0x0060 CHAT global/guild** (zero sightings), the unobserved channel bytes (UPSTREAM
  only), and whether the client renders its own typed line before our echo (chat §8).
- **The five account-name selectors** 0x00C3/C7/C8/C9/CA (the static chain ends at a
  runtime callback list, smsgsweep §7.9) and **0x0191's loopback run** (§7.5).
- **0x0014 QUEST_SET_ACTIVE's labelled run** — worth arming once a second quest exists
  (D9 step 4).
- **R5m residuals 10(h) and 10(i)**; allocator pressure over many sessions; the bit-31
  watchlist's durability.
- **W24's discriminators** ((a) widen the gate and recompile; (b) 0x02000001 vs
  0x02000000 on a staircase map) and the visual verdicts after D11; archivewrite A5; U7's
  retimed-animation summit.
- **Terrain §13.3** (whether the baked lightmap reaches v0): a live capture of a terrain
  `DrawIndexedPrimitive` vertex declaration; D11 step 3's `--no-lightmap` arm is the only
  desk evidence.
- **Minimap C3's 20 two-rect rows** and what a map-type flip draws (maprows §9 item 4).
- **The live-capture route to the 296 ambiguous map rows** (§8.2): one capture on a known
  zone yields one exact pair; D11 step 8 is the desk alternative.
- **Map 888 on a 38888 client, arm A** (quests §11.4).
- **Manifest D13.3's 5 of 17**: a live session with known archive state, unless D3 step 4's
  RIFF read answers it.
- **Monster skill selection at 30 casts per type** (monsterai Q13), scatter (Q14), absolute
  max health from life steal (§7.5), 0x01BF's trailing bytes and the henchman outpost UI
  (heroes Q5/Q8).
- **A visible resurrection shrine in the corridor** (SLICE-F43 / F40.2): a prop in an
  authored map the client must render.
- **"Does it feel like Guild Wars"** on any AI or movement change (monsterai §8.6) — the
  owner at the client, by definition.
- **NPCTRACK Q8 and Q10** (observations with no symptom; the owner's eye to call) and
  **Q3's wedge run**.
- **The account-posture call** (may a live session run against an archive holding an
  authored map; §8.2): an owner ruling, not work.
- **The next ArenaNet build landing** and `test_cage`'s live half: ArenaNet's schedule and
  the owner's UAC; D14 is the preparation.
- **Any on-screen verdict for a newly named or newly sent opcode** (D3's prologue fixes,
  D1's arms, D2's 0x003C prediction): the desk ships and predicts; the client confirms.

---

## 6. Corrections found along the way

### 6.1 `PLAN.md` §8 lines the verifiers found already closed

Fifteen distinct lines after deduplication (the lanes overlapped heavily, which is the
corroboration). "Lanes" counts independent verifier lanes that reached the same
conclusion; a single lane is one witness. Disposition is what Q1 does with the line.

| # | §8 line (location) | What closed it, with evidence | Lanes | Disposition |
|---|---|---|---|---|
| 1 | §8.1 Movement, "§1z-dj, leg B: the mirror still diverges 514 u ... undecoded; registered as a codescan question" (`PLAN.md:2075`) | MOVECODE-1z-dk, 2026-09-10, commit 501e9c43, PLAN-LOG:1510: "there is no gate", 72 of 72; 1z-dk.4 corrects leg B as the sample-and-hold column; the residue (11 of 303 leads; one mesh lip) has its own line via 1z-dl | MOV, REX, CRP | retire |
| 2 | §8.1 Movement, "§1z-dd.8, registered, no run" (`:2077`) | The registered check ran as desk work in 1z-dh (d2771a39, 2026-09-10, PLAN-LOG:1516): SLIDE 0 of 236, 0 of 363 on today's re-run — NOT FOUND, not unrun | MOV, CRP | reword: "retail half needs a live corner" |
| 3 | §8.1 Movement, "§1z-cw.5: 39 % of refused-lag accrued with the copy PARKED ... Unexplained" (`:2082`) | 1z-cw.6 (movecode FINDINGS:18329): the copy arrived at a lead the wall or fence cut short, 255 episodes, 172 on the granted point; 1z-cy and 1z-di addressed it | MOV, CRP | retire |
| 4 | §8.1 Movement, "NPCTRACK ... Q3 needs a wedge run" (`:2084`) | npctrack FINDINGS:763: "CLOSED on the owner's own route, 2026-09-06 15:48"; F12 corrected it; Q9 closed with F16 | MOV | retire |
| 5 | §8.1 Movement, "ANIMREF's desk queue: §15's movement-start gate" (`:2173`) | animref §22.2 (FINDINGS:1103): "§15's mechanism is REFUTED"; the gate is property 8, confirmed in §23 | MOV | retire |
| 6 | §8.1 Movement, "ANIMREF's desk queue: §19's per-bar adrenaline simulation" (`:2173`) | skills §38 (304e6cab, 2026-08-22): retail's reason string 1960 "Not enough Adrenaline" 39 of 39 (`chatdefs.py:73-77`); §19's charge gate is OBSERVED; only the replay scoring remains (D5 step 6) | MOV | relabel |
| 7 | §8.2 RUN-R8 "Run it or withdraw it" (`:2093`) and §7 Q14 item 1 "(armed, router off) has never once been run" / "Nothing in the record both fired and was watched" (~1615–1623) | The R8 line itself is accurate; its PREMISE is stale: 1z-v (09-03) made the router the default; 251 router-on and ~55 router-off armed runs exist; four armed PLANE-REPAIR fires on a watched client (20260903T191246, 202051, 214957, 20260904T105954; 1z-ad:10310); `planecensus.py:955-956` prints the stale sentence hardcoded | MOV, CRP | D10 step 1 rewrites |
| 8 | §8.3 "The silent-opcode sweep: 3 of the 34 CHANGED screens have been read and named; 0x0191 has no usable run" (`:2169-2171`) | smsgsweep §7.5 "READ 2026-08-13 ... 0x0191 CHANGES THE MAP" (run 20260813T153707); §7.6 (line 570) 22 named + 13 hover artifacts, owner-labelled in `vault/labelling/labels-20260813.json`; plansplit FINDINGS:231's "(confirmed)" is wrong. Residue: the five selectors (§7.9), 0x0191's overrides row, the medium animation names | PRO, REX, CRP | retire; residue re-stated |
| 9 | §8.1 Heroes, "0x0065 and the hero-family 0x001B are unmodelled (§11–12)" (`:2060-2062`) | c2s 0x001B = PARTY_FLAG_PLACE, named 7f0cd7c1 / 60cb865c (merge 6ac781d3, PLAN-LOG:7879, 2026-08-19), handled `authsrv.py:10022/:22706` with the 0x0067 echo, P12 CONFIRMED on retail (RUN-LIVE-HERO:240); s2c 0x0065 [hero, 0] sent verbatim since 4ece28bb (`:4913, :22549, :22562`), named AGENT_SKILLBAR_SLOT_FLAGS medium, handler read statically (pvpui §30.2). Open: 0x0065's server model, 0x005E's retail reply | PRO, BEH, REX, CRP | reword |
| 10 | §8.1 The sandbox, "N2 ... whose client message is NOT FOUND (heroes §3.3)" (`:2120-2122`) | KICK: c2s 0x001F [6] on `20260916T150306` conn `10.0.0.210:62321` t=158.676 → 0x0075, 0x01C3 [28,68,379], 0x00B0 at 158.718 (OBSERVED 1/1); a 0x001F [3]/[40] pair already in `authsrv-20260913T093718-c1`, unhandled. ADD: c2s 0x001E static via ChCliApi 0x0080E250 (guard `hero < HEROES`, HEROES = 0x28). Henchman add 0x9F OBSERVED 3/3. The ITEM stays open | PRO, BEH, REX, CRP | reword, do not remove |
| 11 | §8.3 "The archive", three of four clauses (`~2164-2168`) | (a) "no explicit-restore verb" closed 95f550ef (2026-08-14, `restore` at `datwrite.py:913`, a method of the archive writer); (b) "no compressor" closed c4a9fe03 (2026-08-18, `gwenc.py` reproduces ArenaNet's bytes) and W1/W2 (a retail client read the compression-8 row); (c) option C durable key REFUTED b8d5ecf2 (2026-08-27, maprows §10.11/10.12). Open: allocator pressure. crossbuild §4d item 3 is stale the same way | WLD | retire 3 of 4 |
| 12 | §8.1 Monster AI, "passive and group are built and tested and nothing uses them" (`:2054-2056`) | `sandbox.py:672-673` (60f913a7, 2026-09-20) writes `group = 'g{N}'` on every generated hostile row and `passive` on request. The "no content rows" clause is still true | BEH | reword |
| 13 | §8.2 MORALE-Q5/Q6, "the corpus holds no death followed by a zone" | False on disk: `20260914T005758` deaths on map 430 (71/72) then a Kamadan load reading 0x009C 100; `20260916T150306` conn 56865 [29, 85] then conn 50807 [73, 100]. The outpost clear ships (`zone_carry_apply:22653`; slice FINDINGS:2310 row 7). Open: Q5, the field-to-field half | CRP | reword |
| 14 | §8.2 SKILLS-B1, "the armed/dark gate still wants its staged live capture (skills §34.10)" | The separating capture is on disk: `20260914T180058` level-1 Warrior, bar [1, 346], 18 hits, 0 gains; `20260917T224104` level-20 A/W, dark bar, 127 hits, 0 gains. Reproduced independently by the fidelity judge's `adrenjoin.py` run (DARK 49 connections, 0 gains over 367 landed hits; Warrior bars dark on five). `vault/plans/adren_gate.txt` moot; the rounding half stays | CRP + judge | D5 step 1 closes |
| 15 | §8.1 Daggers, "property 10 on the victim (the foe's skill, 229 / 230 unread)" | Property 10 is DECODED as the skill responsible for the next damage number (skillcast FINDINGS:1190-1203: 0x008129DA stores it at charContext+0x640); 229 and 230 are Lightning Orb and Lightning Javelin (`world.toml:2393, :2410`, weapons §34). The bullet's other items stay open. daggers FINDINGS:481/:546 carry the same "UNREAD" | CMB | reword |

### 6.2 Candidates killed, and why

All nine were founded and all nine are LOW-VALUE; none was "not desk" or "unfounded".

- **REX-8** decode the 0x0196 manifest body through MsCliMan — D13.3 itself prices it:
  "the gap costs nothing today"; 0 loopback requests in September. (D3 step 4 keeps the S
  half.)
- **REX-9** name 0x0191 from its handler — confirmed (0x0084EB30) but 0 of 96 live
  connections carry it and retail's travel uses 0x01A5, which we send; only the stale
  wording at `PLAN.md:2170` remains (Q1).
- **REX-10** SLICE-F46.9's Deep Wound number consumer — §46.10 already shipped retail's
  wire rule; a static read of the drawer cannot lead to a server change.
- **REX-11** skills static residue (AvChar 0x19, GmSkSlot 0x00543020, Type 14) — skills §37
  explains the loop; the GmSkSlot fragment is better read as part of D1 step 6.
- **CRP-7** fold retail-witnessed (map, file, arrival) triples into maprows — mapload §1
  already lists them; one new pair (430 → 321293), "not exact" by the scout's own probe;
  a one-line table row rides with Q1.
- **CRP-12** manifest re-test on 8 more sessions — the pattern is real (0x0093 [146] on
  every session whose first load is 148, at an unchanged dword) and changes nothing until a
  served map is missing from an archive; one sentence in D13.3.
- **CRP-13** W9's empty-set press re-read — weapons §27 already reads those map-248 presses
  as sets being FILLED from the panel; RUN-1B keeps both presses whatever the re-read says.
- **INF-10** an operator's authoring guide (docs/ is empty) — conflicts with the owner's
  README lines 22–37 ("not meant for human consumption ... open the checkout in your
  coding harness and just ask"); a smaller agent-facing authoring index could ride with
  D12 step 6.
- **INF-12** MODULARIZE-2 — the size figures hold (35,232 lines, 505 defs, 109 commits since
  513cf3b3) but the arc's closing assessment stands ("further splits cost a lock census
  each ... not worth it"); the lock-free part is ~5 % of the file; the one size-driven
  cost (buildpins 67.8 s) is removed by D13 step 1 at S.

### 6.3 Contradictions and single-witness claims to carry knowingly

- **CRIT-6 vs INF-12.** The critic KEPT modularize pass 2 (CRIT-6, verified sizes, "L in a
  worktree between arcs"); the INF lane KILLED the same work as LOW-VALUE, and the
  leverage judge asked for it to be split out and deferred. This document keeps only the
  line-ceiling tripwire (D13 step 7) and leaves the carve-out to the owner.
- **CRIT-4's licence claim** ("the data is GFDL / CC BY-NC-SA") rests on the critic's
  WebFetch of gw-skilldata's README, repeated by no lane. It matters less now that D4's
  source is the owner's own archive, but `PLAN.md:35/:801`'s "MIT" is still corrected only
  after a re-read.
- **D4's textrec probe** was one judge's run (1,265 of 1,333 rows with a `%strN%` slot); the
  orchestrator reproduced it with its own script (1,265; str1 1,090, str2 582, str3 685;
  0 unreadable). What neither run checked is the slot-to-field mapping, which is why D4's
  first step still does it before anything is built on the labels.
- **D1's second framer** (0x007DCB10, 40 sites) is one verify lane's count relayed by the
  leverage judge; D1's census either reproduces it or reports the difference.
- **0x0020 field 7**: mapload §9 and isle HANDOFF §4.4 measure it as a unit vector (|f7| =
  1.0 in 182 of 182); `overrides.json:1208` says "agint.h:929 bounds-checks fields 5/7 as a
  world position". Both readings are in the repo; D2 step 1 rules.
- **CRIT-7** (custom professions): `PLAN.md` has no §3 row and no §8 line for the MODDABLE
  arc (grep hits only :354 inside R4c's cell, :1332, :1807); it may be parked. D7 step 4
  asks before writing the row.
- **Checked and dropped by the critic**, recorded so nobody re-checks: Isle definitions
  130/139/146 are unseen in 96 connections (129 and 131 are seen, so the probe works); a
  traceback census over 1,609 harness gamesrv logs found 34 with tracebacks, all already
  fixed (RECORDER-D1, the `_pbody` UnboundLocalError).

---

## 7. Method, briefly

**Lanes.** Eight scout lanes, each read-only in `C:/gd/Rurik` at `cd254c51`: REX (client
statics and the send side), PRO (protocol and naming), BEH (behaviour and the sandbox), CRP
(the capture corpus), CMB (combat and skills), MOV (movement), WLD (authored places and the
archive), INF (infrastructure, tests, docs). A verifier pass per lane re-ran the scouts'
probes and added its own candidates (`*-V*` keys). One critic read the studies no lane
touched and added seven candidates (CRIT-1..7). Three judges scored the assembled routes
through the lenses in §2 and spot-checked the premises that moved a score (the adrenjoin
run, the suite timings, `PLAN.md`'s size, the disk, `vault/plans`, the absent handlers and
flags, the textrec probe). This lane assembled the document; it changed the ordering of D1's
steps, rewrote D4 around the textrec probe, moved PRO-10 to D14 and the 0x0018 half of
PRO-11 to D1, and pulled Q4–Q7 out of their routes, each on a judge's stated reason.

**Counts.** Scouted 114 (kept + killed); kept 105 (18 verifier-found; 0 unverified after
the verifier pass); killed 9; critic additions 7 (all kept, two amended). The fourteen
routes bundle 101 candidate keys and the three input quick wins 11; several keys are the
same work filed by two lanes and are listed under one route (CMB-V1 = MOV-9, CMB-3 =
CRP-8, BEH-11 = CRP-9, WLD-7 = BEH-9, MOV-12 = WLD-12, CRP-11 = INF-V3, MOV-6 = INF-13; N2
was filed seven times and RUN-R8 three). Dead lanes: none.

**Not verified.** Verifier-found and critic-added candidates are single-witness. The
tractability probes cited in the routes (send-site scan ~1 s, buildpins 67.8 s → 3.8 s,
the aligned-block index, the textrec templates, the second framer's 40 sites, adrenjoin's
DARK set) were each run by one lane or one judge; the SKILLS-B1 dark-bar finding is the one
with two independent runs. No web read was repeated by this survey, so every wiki- or
licence-dependent claim stays as its lane labelled it. Stale-line rows found by one lane
(§6.1 #4, 5, 6, 11, 12, 13, 15) are one witness each; rows found by three or four lanes
are as corroborated as a read-only survey gets.

**The orchestrator's own checks**, run the same day against the tree and the vault before
this document was committed, one per load-bearing premise of the top routes and the two
decision questions that cost something:

- **D1** — `livewire.decode_conn` on `20260916T150306` conn `10.0.0.210:62321`: c2s
  `0x001F [6]` at t=158.676, then `0x0075 [379]`, `0x01C3 [28, 68, 379]`, `0x00F8`,
  `0x003E`, `0x00B0 [68, 1]`, `0x0145 [96]` at 158.718 (OBSERVED). Across all 36 live
  captures that is the ONLY c2s `0x001F`, and there is no c2s `0x001E` at all — the kick
  is n = 1 and the add has no retail witness, as D1 says. No `GAME_CMSG_*` constant in
  `toolkit/authsrv` is `0x001E` or `0x001F`.
- **D5 step 1** — `python toolkit/authsrv/adrenjoin.py`: ARMED 46 connections, 1,163 gains;
  DARK 49 connections, 0 gains, 0 clears, 0 spends over 367 landed hits and 210 melee
  completions. `--bars` lists the `[346, 1]` bars on `20260914T180058` and
  `20260915T155656`, and `adrenal_costs()` scores both skills at 0, so a Warrior bar sits in
  the dark set. Three independent runs now (the CRP lane, the fidelity judge, this one).
- **D4** — reproduced above; `python toolkit/content.py` reports `skill_effect 54` and
  `skills 1333`.
- **D13** — `toolkit/.suite-timings.json` (untracked, main's tree, written 2026-09-16):
  212 entries, 5,646.6 serial seconds; `test_scrub` 1,203.1 s, `test_updatecheck` 478.4 s.
- **D14** — `C:\gd\Rurik-Backups\robocopy-latest.log` ends Thursday 2026-08-06 19:12,
  21,462 files, 22.249 GB, FAILED 0; RUNBOOK:858 calls the mirror same-disk; `df` on C:
  reads 87 % used, 258 GB free.
- **§6.1 samples** — #1 (`501e9c43`, PLAN-LOG:1510 "there is no gate"), #4
  (npctrack FINDINGS:763 "CLOSED on the owner's own route"), #5 (animref FINDINGS:1054
  "§15 is REFUTED") and #11(a) (`restore`, `datwrite.py:913`) each read as the
  table says.

**Where the notes are.** Each lane's `NOTES.md` sat in the session scratchpad, which does
not outlive the session; the operator judge's saved `descprobe.py` was an earlier version
that counts non-printing tokens (0) rather than `%strN%`. Everything a later session needs
is in this document's route steps, stated so each probe can be re-run from the tree.

---

## 8. Decision questions for the owner

**The owner's answer, 2026-09-22: take D1, D5 and D4.** Q1 is answered by circumstance —
there is no second disk available, so the off-disk copy waits and D14 is not taken (its
line is in `PLAN.md` §8.2). Q3 is yes, given by taking D4 as written. Q2, Q4 and Q5 are
unanswered; Q4 and Q5 belong to routes not taken. The three routes' open lines are in
`PLAN.md` §8.1 under "Desk routes the owner took"; their landings go in `PLAN-LOG.md`.

Each answerable in a word.

1. **Backup off-disk now?** May the irreplaceable vault tier (~24 GB: pinned builds, keys,
   captures without PNGs, live captures, mirrors, research) be copied to a medium other
   than C: as D14's first act — yes or no? (The medium follows; the same-disk mirror
   protects against overwrite only.)
2. **Suite cost first?** Spend one session on D13 steps 1–3 (about 28 minutes off every full
   run, the fix already probed row-identical) before any fidelity route — yes or no?
3. **Label-only skills?** May D4 serve skills whose numbers come from the archive's own
   description templates as a marked `label` tier in the sandbox (the "modelled" grade
   says so), so most of the 1,333 act rather than 54 — yes or no?
4. **Hot reload = rows only?** Spawn and quest rows reload on a zone change; geometry stays
   per launch (the client holds `Gw.dat`) — yes or no? (D9 step 3.)
5. **Custom professions still a target?** If yes, D7 step 4 writes the `PLAN.md` §3 row
   from RESKIN §13 and costs the static rows; if no, MODDABLE §9 is marked parked — yes or
   no?