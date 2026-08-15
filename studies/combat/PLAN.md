# Combat end-to-end: the gate map, and the plan it orders

**2026-08-14.** Produced in worktree `combat-end-to-end-a2242b` at `b1590c6` (suite
baseline that HEAD: 94 green / 0 red, 4,584 checks). Method: a ten-agent workflow —
eight parallel readers (server combat core, skills substrate, cast lifecycle,
attribute wire, live-capture s2c mining, c2s corpus mining, studies-wide gap sweep,
harness verification), one synthesis, one completeness critic — under a standing
order from the owner for this arc: **verbatim/stock behavior confirmed first, before
inventing structures from memory; a new capture run is an acceptable cost.** Five
load-bearing line claims were re-verified a third time by the orchestrator before
this file was written (`_fraction`'s raise at `authsrv.py:110`, the 42-zero send at
`:5196-5198`, the 0x00E4 self-discard comment at `:1101-1103`, the ValueError-free
except tuple at `:5514`, `ATTRIBUTE_POINTS = 50` at `:561`).

Labels per [studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED,
UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. Capture
citations name the capture dir, connection, time and hex where the reader recorded
them; the two live captures are `vault/captures/live/20260807T143055` and
`20260810T235916` (8 game connections, 21,543 GAME_SMSG decoded whole,
consumed==total on every connection, via `tape.py` + `schema/codec.py`).

The session handoff named four gates, in order: (1) attribute ranks unmodeled;
(2) rung L6, `0x003A` as 42 zeros; (3) `s_skill +0x44..+0x68` undecoded;
(4) the connection-thread hazard. All four survived verification. None survived
unrefined, and the map found five hard gates and ten fidelity gates it did not name.

---

## 1. The four handoff gates, verified against this tree

### Gate 1 — Attribute ranks: the server models none; `2 * rank` is 0 today
**VERIFIED, and REFINED — the real blocker is the SOURCE of ranks, not the storage.**

- VERIFIED (OBSERVED): no attribute-rank state of any kind exists. No dict key named
  `attributes` or `rank` in any state/agent construction; `ATTRIBUTE_COUNT` /
  `ATTRIBUTE_POINTS` feed exactly one send pair (`authsrv.py:5196-5198`, `:5134-5136`).
  Independently re-verified against `studies/profession/RESKIN.md:2078-2079` ("No
  attribute rank, in any form...") by reading the full CMSG dispatch chain (no
  attribute opcode among the ~16 handled arms) and grepping all five `content/*.toml`
  (zero hits).
- REFINED (1): **there is nowhere for ranks to COME FROM.** NOT FOUND: c2s attribute
  allocation anywhere — 0 of 52,778 decoded c2s messages vault-wide; the tape
  sessions never touched the Attributes panel; no character-creation flow exists
  (`studies/divergence/FINDINGS.md` D10). Initial rank state must be OURS (a config
  or content row), labeled as such.
- REFINED (2): the numbering scheme under any emission is **CONTESTED and currently
  pointed the weaker way.** `ATTRIBUTE_COUNT = 42` follows OpenTyria's single-witness
  contiguous 0–41 enumeration; a gapped 0–44 scheme (ids 26/27/28 reserved, +3 offset
  from Dagger Mastery on) is CORROBORATED by three independent lineages plus a
  client-derived text-id table, and matches the client's own measured 51-row table
  (`studies/character/FINDINGS.md:589-652`; `studies/profession/ATTRIBUTES.md` §3).
  Naive wiring of today's constant silently misattributes ranks for
  assassin/ritualist/dervish/paragon attributes.
- REFINED (3): combat does **not** need L6's full generality. A real build references
  at most 12 distinct attribute entries (`cmp .,0xc` at three sites, two builds —
  OBSERVED, `ATTRIBUTES.md:128`), which fits one 16-triple `0x003A` message. The
  `ceil(N/16)` batching and the >51-id ceiling are RESKIN's concern, not combat's.

### Gate 2 — Rung L6: `0x003A` goes out as 42 zeros
**VERIFIED byte-exact, and REFINED three ways that change what "fix it" means.**

- VERIFIED (OBSERVED): `send(GAME_SMSG_AGENT_UPDATE_ATTRIBUTES, [PLAYER_AGENT_ID,
  [0] * ATTRIBUTE_COUNT], ...)` at `authsrv.py:5196-5198`, once in the spawn burst,
  never again, nothing reads it back.
- REFINED (1) — what the client does with it: the payload is parsed as fourteen
  (0,0,0) **TRIPLES**, not 42 slots. OBSERVED on our pinned build 38797: handler
  `0x0091D8C0` divides the wire count by 3 (the `0xAAAAAAAB` idiom) and forwards
  base+0 / base+n*4 / base+n*8 through `0x0080EB40` into a per-index loop calling the
  attribute writer `0x00819220` (`ATTRIBUTES.md:135-139`). The code comment at
  `authsrv.py:552-557` still frames triples-vs-flat as open — STALE since `e4fc9963`
  (2026-08-05). **Which position is id vs rank_base vs rank_bonus remains
  UNVERIFIED** — inherited from Headquarter, a single out-of-lineage source reading a
  different build (`studies/character/FINDINGS.md:704-731`).
- REFINED (2) — **the verbatim record does not show ArenaNet sending `0x003A` at all
  in ordinary play**: 0 of 21,543 GAME_SMSG across all 8 connections of both live
  captures, and the neighbor family `0x0038/0x0039/0x003B` is 0 too (decode_all with
  consumed==total; corroborated by `msgmix.py`: "0x003A 0.0 [ArenaNet] / 1.6 [ours] —
  ours only"). Both sessions were short with no Attributes-panel interaction, so this
  is NOT-IN-CORPUS rather than "never sent" — but **no verbatim template for a
  correct `0x003A` exists anywhere in the vault today.** A loopback sweep
  (`studies/smsgsweep/FINDINGS.md` §5b) shows a valid-agent zero-triple `0x003A` is
  at least SILENT, not crashing.
- REFINED (3) — an adjacent verbatim contradiction the handoff missed: **`0x0037`
  (AGENT_UPDATE_ATTRIBUTE_POINTS) IS on the real wire, once per connection at load,
  and all 8 real samples carry [0,0]** — never our [50,50]. OBSERVED, e.g.
  `20260807T143055` conn `:64103`, t=0.722016, hex `37001f0000000000` = agent 31,
  [0,0]. `authsrv.py:561`'s `ATTRIBUTE_POINTS = 50` is UPSTREAM ("an uncited
  literal", GmPlayer.c:125) and is contradicted by every live sample.

### Gate 3 — `s_skill +0x44..+0x68` undecoded; replaces `ENEMY_SKILL_FRACTION = 0.25`
> **CLOSED 2026-08-15 (§12), and with one premise of it REFUTED.** The window is
> decoded (step 4) and wired (step 8). But "it replaces `ENEMY_SKILL_FRACTION`"
> was true only for the skills whose scale actually *is* damage — three of the
> enemy's four are a heal, a hex and an enchantment, and the client's table
> never says which is which. Read §12 before treating a scale endpoint as a
> damage number.
**VERIFIED on the facts; REFINED on "cheapest real win" — cheapest OFFLINE win, not
the first combat-visible one, and it has two unpriced dependencies.**

- VERIFIED (OBSERVED): inside +0x44..+0x68, `skilltable.py` decodes exactly one
  field — recharge at +0x4C (`skilltable.py:224`). duration0 (+0x44), duration15
  (+0x48), h0050[4] (+0x50, unnamed by both upstream sources — NOT FOUND),
  skill_arguments (+0x58), scale0 (+0x5C), scale15 (+0x60), bonusScale0 (+0x64),
  bonusScale15 (+0x68) are read by NO committed tool. The offsets are CORROBORATED
  (GWCA C++ struct and Tyria-Extractor Rust parser agree on every covered offset,
  `studies/skills/FINDINGS.md:175-179`); the client provably reads this window at
  tooltip time (OBSERVED: skill 322 wearing 318's text still showed 322's own
  numbers, `FINDINGS.md:1335-1354`). A 4-skill anecdotal dataset for the window
  exists at `FINDINGS.md:1356-1376`, reproducible by no script in the repo. And
  `ENEMY_SKILL_FRACTION = 0.25` is self-declared invention ("flat on purpose",
  `authsrv.py:1761-1766`).
- REFINED (1) — dependency: decoded scaling is useless to combat math until a rank
  exists to scale BY (gate 1), and the ENEMY's rank is OURS no matter how good the
  decode — the Hatcher's bar is already admitted invention (`authsrv.py:1715-1766`).
  The decode converts one invented number into table-true endpoints scaled by an
  invented rank: strictly better, not verbatim end-to-end.
- REFINED (2) — a cheaper verbatim-grounded combat win exists that the handoff did
  not name: **the cast lifecycle (H1 below)** — implementable today from existing
  captures with zero new evidence and zero rank dependency.
- Cautions: the adrenaline precedent (raw +0x38 needed `ceil(raw/25)`) warns the
  window's raw values may not be display-literal across ~1,333 skills (UNVERIFIED at
  scale); recharge +0x4C — the one decoded field — now has a free live cross-check
  ({153:8, 105:6, 394:3} matched exactly one of 41 dword columns —
  OBSERVED/CORROBORATED, `studies/reconstruction/FINDINGS.md:646-656`).

### Gate 4 — Connection-thread hazard: guards after effects, ValueError asymmetry
**VERIFIED structurally, and REFINED: DORMANT today, and the guard-after-effect
violation is confirmed in 4 of the 5 `_fraction`-calling functions.**

- VERIFIED (OBSERVED): `hit_enemy` has exactly two call sites — `attack_tick`
  (world-tick thread, `authsrv.py:1902` via `:4164`) and the USE_SKILL/ATTACK_SKILL
  arm (connection thread, `:4460`). A `_fraction` ValueError on the world-tick path
  is caught and logged (`:4188-4197`, "world tick REFUSED a value"); on the
  connection path there is NO matching except between `handle`'s outer try (`:3823`)
  and its tuple (`:5514` — ConnectionError/socket.timeout/OSError only), so it runs
  `finally` (closing the socket = the disconnect) and kills that thread. The
  thread-termination reading is RECONSTRUCTION from CPython semantics — no test has
  exercised it (see critic amendment C8b).
- REFINED (1): **DORMANT** — all seven `_fraction` call sites pass fixed constants
  inside [-1.0, 1.0] (`:1947, :2042, :2374, :2472, :2534, :2554, :2574`). The
  asymmetry becomes live exactly when computed fractions arrive (gate 3 wiring).
  Guards must land BEFORE the scaling wiring — the handoff's ordering rule, confirmed.
- REFINED (2): "guards before any effect" is currently violated: `hit_enemy` sends
  unguarded GV_ATTACK_STARTED before the guarded PROP_DAMAGE (`:1934-1948`);
  `land_swing` sends unguarded MELEE_ATTACK_FINISHED first (`:2366-2375`);
  `revive_due` / `player_revive_due` send unguarded revive-status/PROP_HEALTH_MAX
  before their guarded refill (`:1993-2043`, `:2511-2534`). Only `land_skill`'s
  guarded damage is its own first send (`:2470-2474`) — the template.
- REFINED (3) — an unnamed sibling: **no lock protects the state/agent dicts both
  threads read-modify-write**; the file's only locks are `send_lock` (wire bytes,
  `:3914-3918`) and `_PATHMAP_LOCK` (`:832`); no test exercises concurrent entry into
  `hit_enemy`. F10 below.

---

## 2. Gates the handoff did NOT name

### Hard gates (blocks-any-effect)

**H1. Cast-lifecycle opcodes unsent — `0x00E4/0x00E5/0x00E6` (and properties
58/59/60) never leave our server. IN-CORPUS.** The single largest unnamed gate and
the best-evidenced. We send only `0x00E3` SKILL_ACTIVATED, once, immediately, per
press (`:4403-4460`); constants for `0x00E2/0x00E4-0x00E8` do not exist in the file.
ArenaNet's wire shows the full template, six complete cycles (plus 8 Necromancer
cycles): c2s `0x0046` (or `0x0027` for attack skills) → s2c `0x00E4` (+34-54 ms) →
`0x00E5` carrying the recharge seconds → `0x00E3` → `0x00E6` recharge-seconds after
`0x00E5` (e.g. `0x00E5 [229,31,153,0,8]` at t=9.744, `0x00E6` at t=17.747, conn
`:64103`, cap `20260807T143055` — OBSERVED; but see amendment C2: the delta is
measured on ONE cycle so far). The recharge field is CORROBORATED against client
table +0x4C. Blocks: cooldown correctness, repeatable casting, any interrupt. The
"one cast per skill per session without E5/E6" corollary is the skillcast study's own
synthesis — UNVERIFIED; test it as a by-product. The animation half is SOURCED: cast
animation rides agent property 60 (CastSkill) with 58/59 as siblings
(`studies/skillcast/FINDINGS.md` §6, §16.3); our own comment records properties
60/58 ALONE changed nothing visible (`:4444-4454`) — the untested combination is
properties WITH the opcode sequence. **The "separate branch" that comment defers to
does not exist** (full ref scan: zero unmerged completion commits). See amendment C1
before treating `0x00E4` as part of the player's own feedback loop.

**H2. Per-skill effect resolution is absent — R4b is n=0 of 9 families.** Every
skill press resolves to the same flat-fraction `hit_enemy` swing (`:4460`). The
umbrella gate; gates 1/3 plus H1 are its prerequisites.

**H3. Source of ranks — nothing can populate rank state.** NOT FOUND on any wire,
no creation flow, no content row. Closable only by NEEDS-CAPTURE (a session that
spends attribute points) or by an OURS config decision, labeled.

**H4. Attribute numbering scheme — CONTESTED; today's constant follows the
single-witness side.** Must be settled before, not after, any real emission.
CLIENT-TABLE: the 51-row table is already measured (`ATTRIBUTES.md` §3).

**H5. Rendered-output verification gap — no tool reads the HUD/panel.** Probe
`watch` instructions are for humans; `shotlabel.py` detects THAT pixels changed,
never WHAT; `textrec` is an archive decoder, not OCR; `read_error_dialog` reads only
Win32 dialogs. Rendered acceptances stay operator-confirmed; wire/state assertions
carry the automated weight. Amendment C5 (Gw.log) may narrow this.

### Fidelity gates (makes-numbers-wrong)

**F1. `0x0037` sends [50,50]; every live sample is [0,0]. IN-CORPUS** (8/8, both
captures). Cheapest verbatim fix in the arc. The used/max byte-order CONTEST is moot
only while the value is symmetric zeros (amendment C12).

**F2. Energy/adrenaline: not modeled server-side, and the wire says the client
tracks them itself.** PROP_ENERGY_MAX sent once at load, never again; energy debit
is 0 of 22,524 live s2c messages; properties 33/52 have zero observations ever;
property 62 (the only energy-moving float seen) is negative in all 6 occurrences;
adrenaline is 0 of 22,524, while its client-side cost table is fully decoded and
wiki-CORROBORATED (`ceil(raw/25)`). Server-side enforcement is a refusal-behavior
question, not a wire-mirroring one. CONTESTED, unreconciled in-repo: whether the
client gates USE_SKILL on energy at all — sender disassembly shows three bail
conditions and no energy check (`studies/skillcast/FINDINGS.md:519-533`) vs
`agents.py`'s comment that an empty pool refuses all eight skills (whose own commit
message blames a missing weapon, `5048f6a`). A loopback drain-pool probe settles it —
with a positive control (amendment C10).

**F3. Armor / mitigation / weapon damage.** No armor property id in any channel
across 22,524 live messages; PLAN.md:247-249 names armor genuinely server-only.
Monster armor/HP absolutes: NOT-RECOVERABLE (monsterai precedent). Player weapon
damage lives in item modifier words (UPSTREAM shape, OpenTyria); nobody has decoded
one (`content/items.toml:27-42` says so) — GWCA's ItemModifier struct is second-gate
territory (§6.1 row first). The retail damage formula is at best WIKI/RECONSTRUCTION.

**F4. Per-model reach — `ENEMY_MELEE_RANGE = 150` is refuted from both directions.
IN-CORPUS:** ~65 / ~599 / ~706 units for three models (`studies/monsterai/FINDINGS.md`
§3.3). Also: 4 of 5 live fights player-initiated (refutes hostile-initiates); leash
UNCOMPUTABLE from current state (no spawn anchor, `:844`); aggro radius
NEEDS-CAPTURE; AI mechanism NOT-RECOVERABLE.

**F5. Conditions/hexes/enchantments — one bare arrival in the whole corpus.** Only
`0x0041` of the six EFFECT_* opcodes ever observed live (4×); durations are
SERVER-ONLY, in no client table; GV add/remove-effect ids never occur. Discriminant
field CONTESTED (Headquarter effect_type vs GWCA attribute_level, TargetBuff+0x04).
NEEDS-CAPTURE — nothing in the vault grounds a bleed tick today.

**F6. Kill-reward `0x00EE` fires at the death tick on 3/3 observed kills; we never
send it.** IN-CORPUS for timing; **the template is NOT uniform** (amendment C3): the
Wolf kill fired TWO messages ([10,0] then [0,126]); the Worm and Queen kills one each
([0,26]). Semantics (attr_id 0 = experience, applied +=) UPSTREAM/UNVERIFIED;
attr_id 10 UNKNOWN — registry row. `0x009C` is n=1, first-witness, uncatalogued
([31,100] at the Wolf's death tick) — too thin to act on.

**F7. Health/energy regen pips.** Client dispatch arms for properties 43/44 exist
(SOURCED) but never probed, never observed on any wire. NEEDS-CAPTURE / loopback.

**F8. Creature stat table (R4c-2).** 7 hostile definition slots witnessed from one
568 s capture; health known for 3/7, mode-ambiguous (Reforged ~20% delta, mode
unrecorded); monster energy 0 observed; monster skill bars STRUCTURALLY
UNREACHABLE — ArenaNet never sends them (0 of 11 `0x00DA` name a hostile): bars are
infer-from-casts forever.

**F9. Projectiles — `0x00A4` has two unreconciled readings. CONTESTED:** GWCA's
AGENT_PROJECTILE_LAUNCHED (nobody sends it) vs monsterai's positional-oracle reading
(13 live instances, Vec2 = target's world position). The studies never cross-checked.
IN-CORPUS (13 samples) for whoever reconciles them.

**F10. Unsynchronized shared combat state across the two live threads.** No lock, no
concurrency test; the snapshot-for-iteration comments guard dict-resize, not
single-agent read-modify-write. Needs a test, not a capture.

### Polish

**P1.** Weapon-swap `0x0032`, empty-payload `0x0028`, inventory-move `0x004F` fall
through D9(a) silently — shapes observed once each, names UNVERIFIED. **P2.** The
c2s game-channel handshake constant (130 bytes, 10/10 connections — OBSERVED)
deserves a named constant in tape/cmsgstream tooling. **P3.** Death-tick fidelity:
live kills pair `0x00F1` (bit 0x10) with same-tick `0x0026` value=8 (3/3, the only
non-9 value that opcode carries); worth a conformance check on our kill window.
**P4.** Server-initiated interrupt `0x00E2` (n=1, burrow-correlated, RECONSTRUCTION
on cause) — after H1's happy path.

---

## 3. What existing captures answer vs the capture shopping list

### Already answered (no new run needed)
- Full cast-lifecycle order, both c2s halves (`0x0046` and `0x0027`), six complete
  cycles + 8 Necromancer cycles, recharge echo values. (E6-timing spread across all
  cycles: measured for ONE — step 0 closes this.)
- Recharge +0x4C is the recharge column: 1-of-41-columns match against live values.
- Death wire shape: `0x00F1` status 0x10 + same-tick `0x0026`=8, 3/3; kill-tick
  `0x00EE` pairing 3/3 (with the Wolf's two-message deviation); loot burst 2/4.
- `0x0037` = [0,0] 8/8; `0x003A/0x0038/0x0039/0x003B` absent 0/21,543;
  energy/adrenaline/regen absent 0/22,524 — the absences are findings.
- Per-model reach (~65/~599/~706), swing windup ratio (n=42), burrow timings
  (n=140/373), player-initiates 4/5, one interrupted cast (`0x00E2`, n=1).
- Loopback-answerable without ArenaNet: properties 60/58/59 WITH the full opcode
  sequence; the six committed-but-unrun skillcast probes; the F2 energy-gate
  contradiction (drain-pool probe with positive control).

### Shopping list for ONE targeted live session
Operator-driven per RUNBOOK "Capturing a live session"; `--mode` declared
(Reforged/base — no wire mark distinguishes them, ~20% stat delta); pre-registered
marks plan; human cadence. Each item names what must literally happen:

1. **Attributes panel, on-camera**: log in on a character with nonzero ranks; open
   Skills & Attributes; mark; spend at least one point; refund (in town) and
   re-spend a different spread; zone into an explorable. Closes: does ArenaNet send
   `0x003A` at load or on change, with what triples (H3/H4, gate 2 semantics); does
   a c2s spend opcode exist; what `0x0037` carries when points are genuinely unspent.
2. **Same skill at two known ranks**: one rank-scaled skill at rank R1, respec, cast
   at R2, same target type, marked. Closes: binds decoded scale0/scale15 endpoints
   to on-wire resolved values (the adrenaline-precedent transform check).
3. **Conditions**: a build applying at least Bleeding and Poison plus one knockdown;
   apply, let expire, reapply, marked per event. Closes F5.
4. **Sustained fight**: long multi-hit exchange, taking damage, casting until the
   energy orb visibly bottoms, then standing still to full. Closes F2/F7 at n>>now.
5. **Engineered interrupts, n≥2 distinct causes**: target dies mid-cast; ESC-cancel;
   move-cancel. Closes: does `0x00E2` generalize (P4); does the client ever send a
   cancel c2s (none observed).
6. **An adrenaline skill**: count hits to charge; spend. Closes: client-side-accrual
   reading (expects zero wire traffic — an absence worth confirming under marks).

Items 1+2 are arc-critical; 3–6 ride along at near-zero marginal cost.

---

## 4. The critic pass — twelve amendments

A completeness critic ran over the synthesis with the tree open. Every item below
was verified against the tree before being folded into §5's plan. Numbered C1–C12;
the plan cites them where they bind.

- **C1 — `0x00E4` is measured in-tree as how you see OTHER people cast.**
  `authsrv.py:1101-1103` (MEASURED, pinned at `test_agentlife.py:1277-1278`): the
  handler returns early when the named agent is your own. The six live `0x00E4`s
  may be discarded by the receiving client. Step 0 decodes their agent_id offline;
  step 3 keeps emitting `0x00E4` for wire fidelity but attributes animation to
  property 60 / `0x00E3` / `0x00E5`, and the operator check must discriminate.
- **C2 — "E6−E5 == recharge" is OBSERVED at n=1**, dressed as six-cycle fact.
  Step 0 measures the delta for every complete cycle (14+) before the scheduler is
  written; only then is the acceptance equality pinned.
- **C3 — the `0x00EE` template is 2/3 single-message, 1/3 two-message** ([10,0] then
  [0,126], Wolf kill). Step 9 states it honestly; attr_id 10 joins the registry.
- **C4 — the guard contract is wrong for overkill.** `_fraction` refuses outside
  [-1,1] by design (`:108-116`); damage is a fraction of MAX health; the client
  assert is one-sided (`fraction <= 1.0f`). A decoded damage exceeding a weak
  target's max_health yields fraction < −1.0 → refusal-with-no-sends → **a lethal
  hit that silently no-ops.** Fix at the damage call sites:
  `fraction = -min(1.0, dealt / max_health)` — clamp-to-kill where overkill is a
  VALID game event, keep `_fraction` behind it as the invariant net. Explicit
  overkill test (decoded damage > max_health → exactly −1.0 sent, target dies).
- **C5 — Gw.log was never examined**, yet the harness already ships it in every run
  record (`drive_client.py:837`, `:948`, `:740-753`). Step 0 catalogs combat-relevant
  line shapes from existing run records; a positive finding converts part of H5's
  manual burden into string assertions.
- **C6 — the client's own rank→display computation is reachable by clientscan
  today** (the 322/318 experiment proves a reader of +0x5C/+0x60 exists). Step 5
  extends the disassembly to name the interpolation formula with VA citations —
  the client-byte tier the evidence ordering ranks ABOVE captures. Step 6 item 2
  becomes confirmation, not sole source. Capstone stays inside carve-out (1)'s two
  files or the scope gets extended first; prefer a stdlib checker for the claim.
- **C7 — the wiki third witness was never run** for recharge/activation/scale
  endpoints ({153:8, 105:6, 394:3} etc.), and `studies/reconstruction` 2.9.2's
  recommended promotion of `0x00E5` in `schema/overrides.json` was never landed (no
  227/228/229 row — verified). Step 4 runs the pinned-crawl pattern
  (`test_skilltable.py:59-100` — dated literals, no suite-time network); step 3's
  commit lands the overrides promotion citing the live captures as independent leg.
- **C8 — two handoff claims NO reader verified:** (a) "the panel would show rank R"
  — the write chain is MEASURED to `0x00819220`, but the panel's READ path is NOT
  FOUND anywhere; step 5 adds the xref pass, and step 7's acceptance names the
  assumption. (b) "ValueError disconnects the client" — RECONSTRUCTION, never
  exercised; step 2 writes the injected-fraction test against CURRENT code first,
  records the observed failure mode (converting to OBSERVED), then lands the fix
  that turns the same test green.
- **C9 — step 2 as synthesized bundled ≥3 behavior changes**; split into one commit
  per function, the injected-fraction test parameterized per path. And step 3's
  pending-E6 timer is new cross-thread state — its commit extends the concurrency
  test (cast on connection thread while world_tick fires expiries; no lost/double E6).
- **C10 — absence-based acceptances need positive controls in the same script**
  (repeat-press check; drain-pool probe). Alongside each expected-absence press,
  press a known-good different skill and require ITS `0x0046` on the tape, and the
  gamesrv log to show every scripted step, before any absence reads as refusal.
- **C11 — the plan never landed.** There is no "L6" rung in PLAN.md §3 — L6 is the
  profession arc's ladder (`ATTRIBUTES.md:574`), which also carries an open pre-L6
  s_attrib write-safety question (`FINDINGS.md:1277`) that concerns client patching,
  NOT this arc's server-side emission. Step 10: merge to main at the tested
  milestone, update PLAN.md §3/§8 dated and commit-stamped, and annotate the
  profession ladder's L6 row with what this arc delivered and deliberately did not.
- **C12 — `0x0037` [0,0] is a state-conditional observation, not a universal.** All
  8 samples are from characters in unknown spend state. Step 1 ships the fix with a
  comment saying exactly that, pointing at shopping-list item 1; the used/max
  byte-order CONTEST stays open in the registry, moot only at zero.

---

## 5. The ordered plan, as amended

Ordering logic: the owner's standing order (verbatim first; existing evidence before
new evidence before RECONSTRUCTION) plus two confirmed dependencies — guards before
any computed-fraction path (gate 4 is dormant until then), and scaling/rank emission
useless until semantics + numbering + rank state exist. The handoff's 1→2→3→4 is
ADJUSTED: gate 4 moves ahead of everything that would trigger it; gate 3's decode
runs early as offline tooling but its combat WIRING moves late; H1 (better-evidenced
than any handoff gate) runs before rank work; gates 1/2 land semantics → state →
emission with the capture run between evidence and reconstruction.

House rules binding every step: verdicts through `toolkit/checks.py` with a floor
from a real green run; TESTS.md entry in the same commit as the test; one change per
test, one behavior change per commit (C9); client-table content rows carry
extractor+build per row (`content.py` enforces); server path stays stdlib-only
(extraction output flows through `vault/content/*.toml`, never a runtime clientscan
import); captures pooled only through `origin.require_single()`.

- **Step 0 — Offline verifications (C1, C2, C3, C5). Zero new evidence.**
  (a) agent_id of every live-cycle `0x00E4` vs that connection's player agent;
  (b) E5→E6 delta for every complete cycle, n and spread recorded;
  (c) `0x00EE` full recount — every occurrence, payload, same-tick context;
  (d) Gw.log combat-line catalog from existing loopback run records.
  Results land in this file as §6.
- **Step 1 — `0x0037` → [0,0]** (F1, C12). Constant + pinned test literal + the
  state-conditional comment. Acceptance: spawn-burst test asserts [agent, 0, 0].
- **Step 2 — Guard symmetry and guard-before-effect** (gate 4; C4, C8b, C9). One
  commit per function: red-first injected-fraction test on the connection path
  (observe the actual failure mode), then the dispatch-level catch matching
  world_tick's contract; reorder `hit_enemy`, `land_swing`, `revive_due`,
  `player_revive_due` so guards precede ANY send (`land_skill` is the template);
  the damage→fraction conversion `-min(1.0, dealt/max_health)` with the overkill
  test; first two-thread test into `hit_enemy` (F10).
- **Step 3 — Cast lifecycle from the observed template** (H1; C1, C2, C9, C10).
  Emit `0x00E4 → 0x00E5(recharge) → 0x00E3 → 0x00E6` per the measured cycles
  (scheduler per step 0b's finding); recharge from a `vault/content/skills.toml`
  row extracted by `skilltable.py` (client-table provenance); properties 60/58
  alongside (the untested combination). Same commit: `overrides.json` 0x00E5
  promotion (C7). Concurrency test extended to the E6 timer state (C9).
  Acceptance: offline sequence/field/timing test; loopback repeat-press with
  positive control (C10); operator confirms recharge sweep + animation, designed to
  discriminate `0x00E4`'s role (C1).
- **Step 4 — Decode `+0x44..+0x68`** (gate 3, offline half; C7). Extend
  `parse_record` (+0x50 stays named-unknown); tests: reproduce the 4-skill
  FINDINGS anecdote exactly; the free recharge-vs-live check; wiki third witness
  via the pinned-crawl pattern. Bulk rows to `vault/content/` with per-row
  extractor+build.
- **Step 5 — Pin `0x003A` semantics and numbering** (gates 1/2 evidence half; C6,
  C8a). Disassembly: which parallel array is the id (writer `0x00819220`'s argument
  use); the panel's read path xref (C8a); the tooltip formatter's interpolation
  formula (C6). Adopt the CORROBORATED gapped 0–44/51-row scheme, replacing
  `ATTRIBUTE_COUNT = 42` and the stale `:552-557` comment; id-mapping as a
  client-table row set. Acceptance: binary check pins the handler constants on the
  pinned build; mapping test matches the client text-id table.
- **Step 6 — The targeted live capture** (§3 shopping list). Operator-driven.
  Deliberately after all in-corpus/client-byte work, before any
  RECONSTRUCTION-grade emission. Acceptance: capture dir with pre-registered
  plan_marks, mode declared, decode_all consumed==total; per-item presence/absence
  verdicts recorded.
- **Step 7 — Rank state + real `0x003A` emission** (gates 1/2 reconstruction half).
  Rank source OURS (content row, labeled invented) unless step 6 produced the real
  shape, in which case verbatim wins. One message of real triples per step 5's
  semantics. Acceptance: wire test asserts count%3==0, gapped ids, rank in the
  pinned position; operator panel check, with the C8a assumption named in the test's
  own comment.
- **Step 8 — Wire scaling into combat math** (gate 3, combat half; C4). Behind
  step 2's guards: replace `ENEMY_SKILL_FRACTION` with decoded per-skill values at
  a declared OURS enemy rank; player damage scaled by rank at table endpoints.
  Acceptance: dealt fraction equals the table endpoint at rank 0 and rank 15
  (endpoints verbatim; interpolation per step 5's C6 finding, else UNVERIFIED);
  changing the content row reddens the test; overkill test re-run against computed
  fractions.
- **Step 9 — Kill-tick `0x00EE`** (F6; C3). Emit per the honest template: 2/3
  single [0,N], 1/3 pair — implement single-message labeled OURS at the call site,
  the pair recorded as known deviation; attr_id 10 in the registry. Acceptance: our
  kill window contains same-tick {`0x00F1` bit 0x10, `0x0026`=8, `0x00EE`} matching
  the live template; `0x009C` explicitly deferred at n=1.
- **Step 10 — Land the arc** (C11). Merge to main at the tested milestone; PLAN.md
  §3 (R4a/R4b rows) and §8 updated, dated, commit-stamped; profession ladder's L6
  row annotated (delivered: server-side emission, gapped ids; deliberately not:
  s_attrib writes, ceil(N/16) batching, >51 ids).

Deferred beyond this arc, with reasons: conditions/hexes (F5 — gated on step 6
item 3), armor/weapon-damage decode (F3 — second-gate licensing question first),
per-model reach/aggro campaign (F4 — behaviourrun.py's own arc), regen (F7 —
capture-first), projectile reconciliation (F9 — research, not build).

---

## Appendix A — CONTESTED / UNVERIFIED registry (do not silently resolve)

| Question | Side A | Side B | Settles via |
|---|---|---|---|
| ~~Attribute numbering~~ | **DISSOLVED, §10** — both sides are right about different sets: the index space is contiguous 0..50 (51 rows, what the wire is bound-checked against), and 42 is the count owned by the ten playable professions | nothing residual; profession 11's 9 rows are nameless and unowned | closed by `attribtable.py` |
| ~~`0x003A` triple positions~~ | **RESOLVED for slots 1–2, §8a**: slot 1 = `attrib` (id), slot 2 = `baseValue` (rank), both named by the client's own asserts | slot 3 remains NOT NAMED — moves in lockstep with `baseValue`; Headquarter's `rank_bonus` still UNVERIFIED | step 6 item 1, or a rendered check |
| ~~Panel reads the array `0x00819220` writes?~~ | **RESOLVED YES, §8b** — same TLS singleton, same locator, chain ends in `AttribBtns.cpp` vtable code | residual: the panel control's runtime `agentId` is an ASSUMPTION static analysis cannot close | step 7's operator check |
| Tooltip rank interpolation | **RESOLVED, §8c**: `max(0, round(lo + (hi−lo)·rank/15.0))`, literal 15.0, no upper clamp | the rounding TIE-BREAK (half-up vs half-even) is unresolved — ±1.0 adjust, not ±0.5 | a rendered check on a .5-landing pair (skill 316) |
| Client energy gate on USE_SKILL | sender disassembly: no energy check (skillcast §7) | agents.py comment: empty pool refuses all eight (5048f6a; commit msg blames missing weapon) | Loopback drain-pool probe with positive control (C10) |
| "One cast per skill per session" without E5/E6 | skillcast study's own synthesis | flagged UNVERIFIED by both capture readers | Step 3 repeat-press acceptance (C10) |
| E6 scheduler: keyed to E5 + recharge? | one measured cycle says yes (+3 ms) | unmeasured on the other 13+ cycles | Step 0b |
| `0x00E4` in the self-cast cycle: consumed or discarded? | live server sends it in every cycle | in-tree MEASURED: handler returns early on self | Step 0a + step 3's discriminating operator check (C1) |
| ~~`0x00EE` attr_id 10~~ | **RESOLVED as NOT-A-KILL-SHAPE, §13**: the `[10,0]`+`[0,X]` pair is a broadcast burst marked by `0x009C`, 6 of 7 sightings far from any death | what the burst itself IS remains unknown, and what attr_id 10 means inside it | a capture with marks on the burst |
| `0x00A4` meaning | GWCA: AGENT_PROJECTILE_LAUNCHED, never sent by anyone | monsterai: positional oracle, 13 live instances | Cross-check both readings against the 13 samples |
| TargetBuff+0x04 | effect_type (Headquarter) | attribute_level (GWCA) | Step 6 item 3 |
| ~~Scaling-window values display-literal at scale?~~ | **RESOLVED, §8c + step 4**: the endpoints ARE the displayed values (the interpolator consumes them raw at rank 0 and 15), and GWW's progression templates match all 14 | no transform like `ceil(raw/25)` appears in the path | closed |
| `0x0037` bytes: used/max or max/used? | contested between lineages | moot only while the value is [0,0] (C12) | Step 6 item 1 |
| ValueError on connection thread = client disconnect? | RECONSTRUCTION from CPython semantics | never exercised | Step 2's red-first test (C8b) |
| Windup: scales with declared speed or per-creature? | ratio model (n=42, 2 speeds) | confounded with allegiance class | future capture; not this arc |

Time-base note: the two capture readers cite the same Ranger cast events at
different absolute times (t≈21.5 s vs t≈276.7 s) — a connection-relative vs
session-clock artifact, not a contradiction; inter-event deltas agree.

## §6. Step 0 results (measured 2026-08-14, four offline agents over the existing corpus)

All four ran read-only over `vault/captures/live/20260807T143055` +
`20260810T235916` (all 10 game connections decode consumed==total via `tape.py` +
`codec.py`) and the 636 harness run records. Corrections below OVERRIDE the prose
above where they conflict.

**0a — `0x00E4` names the player, 7 of 7 (C1 CLOSED).** Every `0x00E4` in the live
corpus carries agent_id 31 — the connection's own player agent, identified two
independent ways (first `0x0037` at load; `0x0022` [agent, 3]). OBSERVED, e.g.
`e4001f000000990000000000` (agent 31, skill 153) at t=8.741, conn `:64103`. So the
real server broadcasts `0x00E4` uniformly and relies on the client's self-discard —
our `authsrv.py:1101-1103` measurement models real behavior. `0x00E4` contributes
NOTHING to the caster's own feedback; step 3 emits it for wire fidelity only and
attributes animation to `0x00E3`/`0x00E5`/property 60. Counts correction: **7 raw
`0x00E4`s, not 6** (on exactly 2 of 10 connections; zero name an NPC), one of them
an ORPHAN with no E5/E3/E6 tail anywhere after it — a cast attempt with no
confirmed activation, n=1. Which E4 is the orphan is CONTESTED between the two
readers (0a says t=21.543, 0b says t=5.027 on conn `:49163`); 0b's pairing gives
uniform ~1.1 s E4→E5 gaps and is the better reading, but the disagreement is
recorded rather than resolved.

**0b — E6−E5 == recharge on ALL complete cycles, and n is 6, not 14 (C2 CLOSED).**
The corpus holds exactly **6 complete cycles** — H1's "six plus 8 Necromancer" was
wrong; the Necromancer cycles ARE four of the six (skills 153×2, 105×2, cap
20260807T143055 conn `:64103`), the Ranger the other two (394×2, cap 20260810T235916
conn `:49163`). **Session identities were swapped in this file's §3 framing and are
corrected here**: 20260807 is the NECROMANCER session, 20260810 the Ranger —
per `authsrv.py:1070-1079` and independently per the client table's own profession
field (153/105 → profession 4, 394 → profession 2). On all 6 cycles
|delta − recharge| ≤ 13.7 ms (spread −0.3 ms to +13.7 ms, mean +5.3 ms); no cycle
supports E6-keyed-to-cast-end or tick quantization. Recharge units are whole
seconds, triple-witnessed: wire field, client table +0x4C, and the E6 timing.
Zero E5s lack an E6; no cycle was cut by zoning. Step 3's scheduler is therefore
**E6 at E5 + recharge**, OBSERVED n=6.

**0c — the `0x00EE` census rewrites step 9 (C3 CLOSED, and then some).** 17
occurrences total, exactly two payload shapes: `[10, 0]` (7×) and `[0, X]`,
X ∈ {26, 100, 126, 250, 500} (10×); attr_id is NEVER anything but {0, 10}. Every
`[10,0]` is immediately followed byte-adjacent by an `[0,X]` — a fixed PAIR, always
in that order. The death trio (`0x00F1` bit 0x10 + `0x0026`=8 + `0x00EE`, same tick,
same agent) fired on **4 of 4 kills** — a fourth kill nobody had catalogued sits on
conn `:62994` (agent 38, t=19.912, single `[0,26]`). 3 of 4 kills carry a single
`[0,26]`; only the Wolf carries the pair (`[10,0]`+`[0,126]`). **And the pair is not
a kill shape**: 6 of its 7 occurrences are 6.8–31.5 s from any death marker, inside
a recurring ~20-message other-player broadcast burst (name blobs "character C" /
"character D", 0x005D/0x005E, 0x007E pairs) that is always preceded by
`0x009C [agent, 100]` — and `0x009C` fires 13× (once per connection at load, once
before each non-kill burst), never near a lone kill. The X values {100, 250, 500}
reproduce EXACTLY at matching map/slot positions across the two independently
played sessions — structural, not incidental. **Step 9 as amended: emit a single
`[0, N]` at the kill tick (the 3-of-4 shape); the pair belongs to a different,
non-kill mechanism and must NOT be modeled as kill reward.**

**0d — Gw.log is not a combat log (C5 CLOSED, negative).** 636 run records,
11,368 lines, 49 distinct shapes: zero lines for skill activation, cast fail, or
attribute anything. The one candidate death line (`Health non-zero on resurrect`)
fires in only 25/636 runs AND in bare spawn probes with no combat, so it tracks
some resurrect/spawn-state desync, not a kill. **H5 stands in full**: rendered
acceptances stay operator-confirmed; the automated weight stays on wire and state
assertions. (Incidental: `frames-*` dirs carry no Gw.log of their own — they pair
with the report.json run ~2 s later; and the two harness generations write
different report.json shapes into the same tree, for any future cataloger.)

### Progress ledger
| Step | Status |
|---|---|
| 0 | ✅ 2026-08-14, this section |
| 1 | ✅ 2026-08-14, `07c22b0` — 0x0037 → [0,0], binding check proven red-then-green |
| 2 | ✅ 2026-08-14, `cdefe83`…`e9f7b7d` (10 commits) — extraction, red-first guard contract on all seven `_fraction` functions, connection-thread catch, overkill clamp-to-kill (`_damage_fraction`), first two-thread test. `test_guards.py`, floor 35 |
| 3 | ✅ **BOTH HALVES** — offline 2026-08-14, `f5f65b2`+`77b65d1` — emitter (1,333 client-table rows, build stamped from bytes), the four-opcode cycle on the observed template, THE QUEUE LAW (E4 at accept, cast begins when the caster frees — fits 4/4 Necro cycles ≤14 ms; the naive press+activation model is refuted by +0.64 s/+0.57 s residuals), overrides names 227–230, cross-thread cast-timer test (200 presses → exactly 200 of each phase). Attack-skill E5 timing rides the weapon — recorded as unmodeled divergence. GV 58 deliberately unsent (0 of 21,543 live). **Loopback acceptance ✅ 2026-08-15, §15** — both halves: the client accepts E4/E5/E3/E6 without asserting, a repeat press after E6 produces a full second cycle, recharge is per-skill with concurrent timers (four cycles, max error 36 ms), and the operator confirms **both slots swept with slot 6 clearly longer than slot 7** — the comparison that shows the client honours the message's DURATION rather than just flashing an icon. §7's blocker (a new ArenaNet build's fresh archive) is gone. Cast ANIMATION remains unmeasured and belongs to the unrun `cast_anim` probe, §15c. ~~BLOCKED — see §7~~ |
| 4 | ✅ 2026-08-14, `0ddfbd0`+`9d97f45`+`a7971b1` — `+0x44..+0x68` decoded as u32 (duration0/15, skill_arguments bitfield, scale0/15, bonus_scale0/15; +0x50 stays NOT FOUND). Reproduces the 4-skill FINDINGS anecdote byte-exact and asserts its green-render rule. **C7's wiki third witness ran and agrees with all 14 endpoint values GWW lists**, plus costs and recharge — and checks the other direction too (no unlisted set may render green), which is what makes Rush's constant-25-with-bit-clear a real discriminator. Emitted to the content rows; **nothing consumes them until step 8**. `test_skilltable` floor 26→46 |
| 5 | 🔶 **research half ✅ 2026-08-14, §8** — the triple's slots 1–2 named by ArenaNet's own asserts (`attrib`, `baseValue`), the panel's read path traced to `AttribBtns.cpp` (C8a closed), the tooltip formula measured (C6 closed). **Still to do in code**: adopt the gapped numbering, replace `ATTRIBUTE_COUNT = 42`, retire the stale `authsrv.py:552-557` comment, and pin the handler constants in a test |
| 5 (cont.) | **code half ✅ 2026-08-15, `043e395`** — `attribtable.py` reads `s_attrib` and DISSOLVES the numbering contest (§10): index space contiguous 0..50, 42 owned by playable professions, 26/27/28 are profession 11's. 51 content rows emitted. Still open in code: `ATTRIBUTE_COUNT = 42` is a count of the wrong thing for a wire payload and step 7 replaces it |
| 6 | ⬜ — the targeted live capture. Operator-driven; §3's shopping list |
| 7 | ✅ **BOTH HALVES 2026-08-15** — wire `1339bfe` (§11), layout fixed and panel confirmed (§14g). **L6's attributability criterion is MET**: `--probe attributes` ran caged, the panel followed all three steps and the ranks matched the names, which also closes §8b's runtime-agent-binding gap by observation. Original wire note follows. 🔶→✅ (§11) — five real triples, bounds refused not clamped, payload bound to its content row and proven red. **L6's panel criterion is UNVERIFIED and needs one caged loopback run**: `--probe attributes`, whose step 3 reverses the ranks as the discriminator |
| 7 (fix) | ⚠️→✅ **2026-08-15** (§14) — the payload shipped INTERLEAVED and `0x003A` is column-major, so every session since died on `CharData.cpp:202`. `attribute_triples` → `attribute_columns`; `arrsize(s_attribPoints)` read at last (13, correcting `consttable.py`'s 14) by the new `attribpoints.py`. Diagnosed statically from the crash dump's own stack — no client run, no int3. **Cure VERIFIED §14g**: caged run, 1,716 messages, t=78.2 s, no assert |
| 8 | ✅ **2026-08-15, `e4bb222`** (§12) — `ENEMY_SKILL_FRACTION` retired; damage is the client's endpoints at the player's own attribute rank. **The step's premise was refuted mid-flight**: scale is not damage, 3 of the enemy's 4 skills are a heal/hex/enchantment, so meaning is GWW-sourced per skill and unmodelled skills return None. `test_skilldamage` 25 checks, sabotage-proven |
| 9 | ✅ **2026-08-15, `34ee86b`** (§13) — the kill window is three messages in ArenaNet's order, reward byte-identical. The richer-looking `0x00EE` PAIR is refused as a non-kill mechanism, and two of this arc's own counts were corrected (5 deaths not 4; `0x0026`=8 four times not once). `test_killwindow` takes the corpus as its oracle, 21 checks |
| 10 | ✅ **2026-08-15, `2610aa3`+merge** — `PLAN.md` §3 (R4a, R4b) and §8 updated dated and stamped; the profession ladder's L6 row annotated so the two ledgers agree. **Landing suite: 100 green / 1 red of 101, 4,947 checks.** The red is `test_contentids`, and it is ENVIRONMENTAL and attributed: `vault/run/2026-08-13_64fae3b1369b/Gw.dat` is held open by **another session's client, PID 16340, running from that directory since 11:47** — the archive is present (4.2 GB) and unreadable, which is the same "the client holds its own archive open" note main's own §8 carries. `test_contentids` passed at 23 checks earlier the same day with the archive free, and nothing in this arc touches archives, map content or `contentids.py`. Not killed, per the parallel-sessions rule |

## §16. The `cast_anim` probe ran: step 4 confirmed in the client's own words, the animation still needs eyes (2026-08-15)

Caged loopback, build 38833 against its own archive
(`--exe vault/run/2026-08-13_64fae3b1369b/Gw.exe`,
`RURIK_DAT=vault/dat_study_38833/Gw.dat`), map 90 explorable, synthetic
credential. `RUN VERDICT: PASS`, **zero Undecodable**, no assert in `Gw.log`.
Run: `vault/captures/harness/20260815T182423`.

This was the one combat item §15 left open, and the probe's question is
whether the cast animation is driven by opcode 228 or by agent property 60.

**CONFIRMED, verbatim and machine-readable — step 4's prediction.** The probe
said `Gw.log` should carry the client's own `Pending skill %u copy %d not
found`. It does:

```
Error: Pending skill 320 copy 0 not found
```

320 is `bar[4]`, the skill the probe sent, and `copy 0` is the field. So the
client is telling us in words what `0x00E3`'s third field is called and that it
matches an entry it never created for us — which is the same mechanism
`handle_skill_press`'s echo relies on, now witnessed from the client's side.

**ALSO ESTABLISHED, and it is a safety result rather than a semantic one:** the
client accepted `0x00E4` addressed to the LOCAL PLAYER, then property 60, then
`0x00E3`, and ran on without asserting. Given §14's crash — an interleaved
`0x003A` killed it on `CharData.cpp:202` — "these three do not kill it" is
worth having explicitly.

**NOT SETTLED: whether property 60 plays the animation.** The prediction is
that 228 does nothing visible locally (its handler returns early on self, which
§6's step 0a corroborated from the wire: all 7 live `0x00E4`s name the
receiving connection's own player) and that property 60 is the one that
animates. **Nobody was watching the screen**, and the frame instrument cannot
substitute:

| what | result |
|---|---|
| 24 hold frames at 1.0 s, per-frame pixel change | **12.77 %–15.35 %, flat** |
| the frame after 228 (`hold005`) | 14.66 % |
| the frame after property 60 (`hold008`) | 14.26 % |

The idle scene churns at ~14.5 % a frame all by itself — water, foliage, the
character's idle animation, camera drift — so a cast animation on one body does
not separate from the baseline. **This is H5 measured rather than asserted:**
`shotlabel.py` detects THAT pixels changed, never WHAT, and at this baseline
that is not enough. `shotlabel --run` also declines the run outright ("no sweep
sends in the capture") because it is built for the opcode sweep, not for probes.

So the animation half stays operator-visual, which is what H5 said it would.

### §16a. SETTLED the same day, by splitting the variable

The combined probe then failed for a reason worth recording: **the operator saw
a sparkle and could not attribute it.** They lost count of the gaps, and an
observation that cannot be tied to a message is not evidence about either one.
The agent had also quoted the gaps wrong — as ~3 s, when `Step`'s first field
is a DELAY from the previous step, making the real gaps ~5 s and ~8 s. Both
halves of that failure are in `_cast_one_steps`' docstring.

The fix was not better timing but **one variable per run**. Two probes,
`cast_228_only` and `cast_prop60_only`: same bar, same map 90, same hold, the
message under test firing at **t≈10.85 in both**, and nothing else sent at all.
The operator answers yes or no, with no counting.

| run | capture | fired at t≈10.9 | operator saw |
|---|---|---|---|
| `cast_228_only` | `authsrv-20260815T184213-c1.jsonl` | `0x00E4` (228) | **nothing** |
| `cast_prop60_only` | `authsrv-20260815T184317-c1.jsonl` | `0x009F` property 60 | **the cast sparkle on the weapon** |

**ANSWERED for the DRIVER, and OVERCLAIMED for the CONTENT — corrected below.**
Each run is the other's control, and the pair settles which message drives a
skill's visible effect: **property 60 does, 228 does not.** That closes
`studies/skills` §8's question of *what triggers* it, by the very method that
row prescribed — "send each in isolation and watch" — and refutes its own
guess that the client predicts the animation itself.

> **§16b. THE OWNER CAUGHT AN OVERCLAIM, and the probe's skill choice is why
> (2026-08-15).** This section first read "property 60 plays the cast
> animation". The owner's objection: *"there's more to a cast animation than a
> simple sparkle on the weapon. it probably also has varying animations on the
> player models themselves."* Correct, and the experiment could not have shown
> otherwise — **`PROBE_BAR_SKILL + 4` is skill 320, Hamstring: `type_code` 14,
> an ATTACK skill with `activation = 0.0 s`.** It does not cast at all. A
> weapon sparkle is the whole of what it has, so "the cast animation" was
> tested with a skill that has no cast.
>
> The client's own table says the same thing, and says it per skill. The six
> animation ids at `+0x74..+0x88` — resolved as `s_effect` indices by
> `studies/reconstruction/FINDINGS.md` §2.9.3, with 2077 as the null:
>
> | skill | activation | ids at `+0x74..+0x88` |
> |---|---|---|
> | 320 Hamstring (tested) | 0.0 s | `[566, –, –, –, –, –]` — one |
> | 322 Power Attack | 0.0 s | `[568, –, –, –, –, –]` — one, different |
> | 153 Vampiric Gaze | 1.0 s | `[277, –, 276, –, –, –]` — two |
> | 105 Deathly Swarm | 2.0 s | `[204, –, 201, –, –, 199]` — three |
> | 318 Defy Pain | 0.0 s | `[–, 595, –, –, –, –]` — one, different SLOT |
>
> So animation content is per-skill and multi-part, spells populate more slots
> than attack skills, and the slot index carries role. **What is established is
> the DRIVER (property 60, not 228); what is NOT is that one property-60 send
> reproduces a full cast** — body animation included. `cast_spell_only` is the
> follow-up: property 60 with **105 Deathly Swarm**, a 2.0 s spell with three
> animation components, where a casting stance would be unmistakable.
>
> **RAN, and the model animated (2026-08-15).** `cast_spell_only`, caged
> loopback on 38833, map 90: bar with 105 in slot 5 at t=2.85, property 60 with
> skill 105 at t=10.86, nothing else sent. Capture
> `authsrv-20260815T190337-c1.jsonl`, `RUN VERDICT: PASS`. **The operator
> reports the model itself performed an animation** — not the weapon-only
> sparkle Hamstring produced.
>
> So the corrected claim, with its scope now earned rather than assumed:
> **property 60 drives the cast, body animation included, and what renders is
> per-skill** — one animation component for an attack skill, a full casting
> animation for a 2.0 s spell with three. 228 drives nothing. The overclaim was
> real but the conclusion survives a properly designed test; what changed is
> that it is now supported by the experiment rather than by a skill that could
> not have shown it.

**Three independent witnesses now agree**, which is the part worth keeping:

1. **The handler** — 228 compares the named agent against the local player and
   returns before reaching AgentView (static, `studies/skills` §8).
2. **The wire** — all 7 `0x00E4` in the live corpus name the receiving
   connection's OWN player (§6, step 0a), so ArenaNet broadcasts it uniformly
   and relies on the client discarding its own.
3. **The screen** — 228 alone renders nothing; property 60 alone renders the
   cast.

That also retires the worry §6 step 0a raised against itself: 228 is not the
caster's own feedback, and our server's use of it for wire fidelity while
driving the animation from property 60 is the correct shape.

## §15. Step 3's loopback acceptance RAN, and both halves pass (2026-08-15)

**§7's blocker is gone and its acceptance is met.** Two caged runs, build
38833, map 90 explorable, `--enemy --practice-target`, synthetic credential,
each watched with `crashwatch.ps1`. `RUN VERDICT: PASS` both times, zero
`Undecodable`.

### 15a. The wire half — OBSERVED

`vault/captures/gamesrv/authsrv-20260815T180701-c1.jsonl`, 3,158 messages,
t = 107.7 s. Four complete cycles, `E4 → E5 → E3 → … → E6` every time, and the
client accepted all of them without asserting:

| cycle | declared | measured | error |
|---|---|---|---|
| 322 | 3.0 s | 2.989 s | −0.011 |
| 321 | 8.0 s | 7.993 s | −0.007 |
| 322 | 3.0 s | 2.990 s | −0.010 |
| 322 | 3.0 s | 3.036 s | +0.036 |

**The repeat-press acceptance passes.** Press 2 (t = 38.559) lands after cycle
1's `E6` (t = 30.747) and produces a full second cycle; press 3 does it again.

**And a result C10 did not ask for: recharge state is PER-SKILL and the timers
run concurrently.** Slot 6's 8 s recharge overlaps slot 7's second and third
cycles, and the opcode stream interleaves correctly — `228 229 227 230 230`
across t = 38.5–41.6 is 322's cycle opening, then **321's** `E6`, then
**322's**, each naming its own skill. Two independent timers, observed rather
than assumed.

Incidental, and it confirms step 8 from the other side: the player
auto-attacks the practice target for 15 a swing, and at t = 42.479 one swing
lands **49** — the skill damage from the client's own scale endpoints. The
target is killed and reset (`restore max health on agent 10`, t = 41.5). Note
the magnitude arrives at the PRESS, which is the timing divergence step 8
already records as unmodelled.

### 15b. The rendered half — OBSERVED, operator-confirmed

`vault/captures/gamesrv/authsrv-20260815T181338-c1.jsonl`, second run, with the
operator watching the skill bar (H5: no tool here can read the HUD).

> **Both slots swept, and slot 6 was clearly longer than slot 7.**

That is the acceptance, and the *comparison* is what makes it one. A client
merely flashing an icon on `E5` would look the same for both slots; 8 s
visibly longer than 3 s means the client is honouring the DURATION the message
carries. Wire for that run: slot 7 `E5 recharge 3s` at t = 27.715 with its
`E6` at 30.704, slot 6 `E5 recharge 8s` at t = 31.615.

**This capture is the shorter of the two and deliberately so cited.** The
operator closed the client at t ≈ 39.4 s once the comparison was made, so
slot 6's `E6` (due 39.615 s) is NOT in it — the harness confirms the exit was
clean (`client exited with code 0 during the hold`, `no error dialog within
12s`). The complete four-cycle wire evidence is §15a's run; this one carries
the rendered result. Neither is asked to carry both.

### 15c. What this does NOT settle

**The cast animation is NOT measured.** The operator was directed at the bar
and told to ignore the character's body unless something surprised them, so
nothing was reported about it — and **silence is not a negative result**. It
also is not this acceptance's question: the unrun `cast_anim` probe states the
prediction outright, that opcode `228` "does nothing visible at all when
addressed to the local player", and `228` is what these runs send. Whatever
animates, `cast_anim` (agent property 60) is the probe that would show it, and
it is still UNRUN.

## §14. `0x003A` is COLUMN-MAJOR, and step 7 sent it interleaved (2026-08-15)

**The bug §11 shipped, found from the outside by the terrain arc.** A loopback
harness session on build 38833 killed the client with

```
Assertion: level < arrsize(s_attribPoints)
P:\Code\Gw\Char\CharData.cpp(202)
App: Gw.exe   BaseAddr: 00090000   Build: 38833
```

reproduced, seen at least twice, and **caused by this arc**: step 7 replaced
`0x003A`'s fourteen zero triples with five real ones on 2026-08-15, and its
payload layout is wrong. Nothing else in the burst is implicated.

Settled **statically, with no client run and no int3**. The suggested route was
an injected breakpoint at the assert site; it was not needed, because the crash
dump's own stack names every frame once the addresses are rebased
(`- 0x00090000 + 0x00400000`) and the client's asserts say which source file
each one is in. The whole diagnosis is `asserts.py`, `codescan.py` and the
receive table.

### 14a. The stack, rebased and named — OBSERVED

| # | dump | rebased | function | module, from the asserts inside it |
|---|---|---|---|---|
| 0 | `00117bdb` | `0x00487BDB` | — | the assert routine itself (`asserts.py` derives `0x00487BC0`) |
| 1 | `005ad580` | `0x0091D580` | `0x0091D560` | **`CharData.cpp:202`**, the failing site |
| 2 | `004a9323` | `0x00819323` | `0x00819270` | `ChCliAttrib.cpp` — the attribute writer |
| 3 | `004a9e5c` | `0x00819E5C` | `0x00819C00` | `ChCliAttrib.cpp` — the per-index loop |
| 4 | `0049eb65` | `0x0080EB65` | `0x0080EB40` | `ChCliApi.cpp` — a five-argument forwarder |
| 5 | `005ad94b` | `0x0091D94B` | `0x0091D920` | **the `0x003A` handler** |
| 6–7 | `0046c5d6`, `0046ca94` | `0x007DC5D6`, `0x007DCA94` | | `MsgConn.cpp` |
| 8–9 | `00121cdb`, `0012237d` | `0x00491CDB`, `0x0049237D` | | `GcGameCmd.cpp`, `GcSrv.cpp` |
| 10 | `002bdf68` | `0x0062DF68` | | `EvtDispatch.cpp` |

Frame 5 names the message without a capture: `0x0091D920` is stored in exactly
one `.rdata` word, `0x00BC8FE8`, which is the `dispatch` member of the 12-byte
receive descriptor at `0x00BC8FE0` — and that descriptor's `cmds[0]` is
**`0x003A`**. (`{uint32 *cmds; uint32 count; void *dispatch;}`, the layout
`msghandler.py` already uses.) The worker thread the dump names is consistent:
`MsgConn`/`EvtDispatch` frames, not the render thread.

### 14b. The wire layout — OBSERVED, and §8a already had it right

The handler is eleven instructions and it is the whole answer:

```
0091D923  mov ecx, [ebp+8]          ; the decoded message
0091D926  mov eax, 0xAAAAAAAB
0091D92B  mul dword ptr [ecx+8]     ; count
0091D931  shr edx, 1                ; edx = n = count / 3
0091D933  lea eax, [eax + edx*8]    ; arr3 = payload+0x0C + n*8
0091D93A  lea eax, [eax + edx*4]    ; arr2 = payload+0x0C + n*4
0091D93E  lea eax, [ecx+0xc]        ; arr1 = payload+0x0C
0091D946  call 0x80eb40             ; (agentId, n, arr1, arr2, arr3)
```

**Three contiguous columns of `n` dwords, not `n` interleaved triples.**
Element `i` of each column is `n*4` bytes from the last, never 4. The loop at
`0x00819C00` confirms it and shows why the shape is easy to misread: MSVC
converts the three cursors into induction variables, holding `arr2 - arr1` and
`arr3 - arr2` as deltas (`sub [ebp+0x18], eax` / `sub eax, ebx` at
`0x00819CFC`–`0x00819D07`) and re-adding them at the call, so the call site
reads `push [ebx] / push [eax] / push [ecx+eax]` and looks like pointer
arithmetic on three unrelated things.

§8a said "three parallel n-dword arrays" and named them `payload+0xc`,
`+0xc+4n`, `+0xc+8n` on 2026-08-14. **The study was right and the
implementation ignored it.** `attribute_triples()` shipped the next day with a
docstring that repeated §8a correctly above a body doing `out += [attrib_id,
rank, rank]`. The name was the tell, and nothing checked the name against the
docstring.

### 14c. Why it is fatal rather than merely wrong — OBSERVED

Writer `0x00819270` stores `arr2[i]` at `slot+8` (`baseValue`, §8a) and then
passes that same dword to `CharData.cpp:202`:

```
00819315  push dword ptr [esi+8]    ; the rank, after pending-change deltas
0091931E  call 0x91d560             ; <-- level < arrsize(s_attribPoints)
```

So **column 2 is indexed straight into `s_attribPoints`**, whose `arrsize` is
**13** (§14d). Interleaving `(id, rank, rank)` puts the flat array's second
third into column 2, which for our five attributes is a mix of ids and ranks —
and attribute ids run to 50. Reproduced by hand and then as a test control:

```
content ranks  [(17,12), (18,9), (19,6), (20,3), (21,1)]
interleaved    [17,12,12, 18,9,9, 19,6,6, 20,3,3, 21,1,1]   n = 5
  column 1     [17, 12, 12, 18, 9]     ids   -- all < 51, so ChCliAttrib:249 stays quiet
  column 2     [9, 19, 6, 6, 20]       ranks -- 19 at i=1 is >= 13
```

The client asserts at **i = 1 on the value 19**, which is exactly where and what
the dump shows. Two predictions fall out and both hold: the `attrib < 51`
assert (`ChCliAttrib:249`) must NOT fire first, and it did not; and the failure
is deterministic on every spawn, which is why it was seen twice rather than
intermittently.

**It hid for a day because the previous payload was all zeros.** Fourteen
`(0,0,0)` triples and five column-major zeros are the same fifteen dwords —
the layout is unobservable until a nonzero value exists. The moment step 7 put
real ranks in, the layout became load-bearing and the client said so.

**And it hid twice more because of the watcher, not the payload.** The assert
box is a modal window *inside* the client process, so `Get-Process` reports
ALIVE for as long as it is up; two instrumented runs were reported clean while
the owner was looking at the crash dialog. `Crash.dmp` is no better — none was
written on 2026-08-15, anywhere. The signal is the dialog itself
(`crashwatch.ps1`, §14f).

### 14d. `arrsize(s_attribPoints)` is 13, and it was recorded as 14 — CORRECTED

`arrsize` was a number this repo did not have, and the one it did have was
wrong. `consttable.py` carried the table as **14 x 4**; it is **13 x 4**:

```
s_attribPoints = { 1, 2, 3, 4, 5, 6, 7, 9, 11, 13, 16, 20, -1 }
```

Indexed by an attribute's **RANK**, not by a character level, despite
ArenaNet naming the parameter `level` — which is why `START_LEVEL = 1` and
`PLAYER_ATTR_LEVEL = 9` were never suspects. `s_attribPoints[r]` is the cost of
raising an attribute from rank `r` to `r+1`; `-1` at [12] means rank 12 is the
last. UPSTREAM: those twelve are retail's published per-rank costs and sum to
**97**, the cost of a rank-12 attribute.

The two accessors differ by exactly the thing that caused the error:

```
0x0091D560  CharData:202   cmp esi,0Dh ; mov eax,[esi*4 + base-4]   s_attribPoints[level-1], 0 at level 0
0x0091D5A0  CharData:208   cmp esi,0Dh ; mov eax,[esi*4 + base  ]   s_attribPoints[level]
```

MSVC folded the `- 1` into the displacement, so `CharData:202` encodes an
address **four bytes below** the array. Read that as the base — the obvious
move, and effectively what happened — and the table starts one element early
and must be 14 long to reach its anchor. **Both readings close on the anchor**,
so `consttable.py`'s arithmetic could never have chosen between them: it had
`pad=None` for this row, meaning no left-edge witness, so its base was derived
from its count and its count from the biased displacement. Two errors that are
the same error.

Refuted three ways, in `toolkit/clientscan/attribpoints.py`, none of them the
anchor arithmetic:

1. **the client's own `arrsize`** — both accessors `cmp esi, 0Dh` before the
   lookup, at the exact site whose assert expression is
   `level < arrsize(s_attribPoints)`;
2. **the unbiased accessor** — `CharData:208` applies no `- 1`, and its
   displacement sits exactly 4 above `CharData:202`'s;
3. **the neighbour's right edge** — `s_appearanceSlot` (own asserts at
   `CharData:165/178`, own `cmp esi, 8`, stride 12 from
   `lea edi,[esi+esi*2]`) ends its 8 records exactly on the corrected base, so
   the dword the old reading absorbed is that table's last column.

and the content agrees: 13 gives a strictly increasing run terminated by `-1`;
14 opens on a `5` that breaks it. `consttable.py`'s own row had *noticed* that
— it called the `5` "what `dead data` looks like from the outside" — and
noticing was not enough to overturn a closure. **A closure is only evidence for
the term you did not derive from it.** Same defect as §7b's `s_worldData`
(a free stride), arriving from the left edge instead.

All three vaulted ArenaNet builds agree at 13, with the base at a *different*
address on 38519 — which is what makes the locator structural rather than an
address that still happens to work.

### 14e. What changed

| Where | Change |
|---|---|
| `authsrv.attribute_triples` | → **`attribute_columns`**, emitting `ids + ranks + ranks`. The name is part of the fix: it was the only thing in the file asserting the wrong shape, and it outvoted a correct docstring |
| `authsrv.ATTRIBUTE_TRIPLES_MAX` | → `ATTRIBUTE_COLUMN_MAX` (same 16) |
| `probes.py --probe attributes` | follows the rename; its note now says a mis-built layout never reaches the panel check because it asserts the client dead first |
| `toolkit/clientscan/attribpoints.py` | NEW — the structural locator, stdlib only, `--all-builds` |
| `toolkit/clientscan/test_attribpoints.py` | NEW — 20 checks, 7 sabotages, three-build cross-check |
| `consttable.py` | `s_attribPoints` 14 → 13, base +4, and the docstring records why the closure could not catch it |
| `test_consttable.py` §7c | NEW — binds the row to `attribpoints.py`; floor 69 → 74 |
| `test_spawn_burst.py` §4 | slices the payload the CLIENT's way, and its last check is a control requiring the interleaved layout to produce an out-of-range rank; floor 34 → 38 |

The step-7 wire half is **still ✅** — the ids, the bounds, the refusals and
the content binding were all right. Only the ordering was wrong.

### 14g. The cure is VERIFIED, and it closed L6 on the way — OBSERVED

**Run 2026-08-15, caged loopback, build 38833, map 90 explorable, synthetic
credential.** `vault/captures/gamesrv/authsrv-20260815T180007-c1.jsonl`,
1,716 messages, last at **t = 78.2 s**, no `Undecodable`, no disconnect. The
client was watched with `crashwatch.ps1` rather than `Get-Process`, which is
the only reason a clean result here means anything (§14c):

```
VERDICT: HEALTHY (pid 22192, watched 201s, no dialog)
```

That line is the verdict, and it is the one the two earlier runs could not
have produced honestly — they were scored by liveness, which reports ALIVE
through a modal assert box. The harness agrees independently:
`RUN VERDICT: PASS (target: map)`, report at
`vault/captures/harness/20260815T175950`.

**The screenshots are NOT evidence here and the report says so** — every
`--shots` frame was skipped, `client not foreground`, because the operator had
the attribute panel up and focused for the whole hold. The panel result below
is operator-confirmed, which is what H5 requires anyway; the frames would have
been a bonus and there are none. Recorded rather than glossed, because a
future reader finding an empty `frames-` dir should not conclude the run was
partial.

**No assert.** The spawn burst's `0x003A` goes out at t = 0.85 s and the
client runs on for another seventy-seven seconds. On the interleaved payload
it died there every time.

The wire, decoded out of the capture — column-major, count 15:

```
t= 2.876  count= 0                                    step 1, the control
t= 8.884  ids=[17,18,19,20,21]  ranks=[12,9,6,3,1]    step 2
t=14.896  ids=[17,18,19,20,21]  ranks=[1,3,6,9,12]    step 3, ranks REVERSED
```

**The panel followed all three steps, and the ranks matched the names**
(operator-confirmed; per H5 no tool here can read the HUD). That is L6's
attributability criterion **MET**, and it settles three things at once:

1. **The cure works end to end** — not just "no crash", but the values
   arriving where they belong.
2. **§8a's reading of column 2 as `baseValue` is confirmed positionally.**
   Step 3 holds the id column *in the same order* and reverses only the rank
   column. If the two were swapped, mis-aligned, or read at a stride, step 3
   would have put the right numbers against the wrong names — the failure the
   distinct ranks (12/9/6/3/1) were chosen to make visible.
3. **§8b's one honest gap is closed by observation.** That section could prove
   the write chain and the panel's read chain share a record and a locator,
   but not that the panel control's `agentId` holds the local player at
   runtime — "a runtime value, not a byte pattern". The panel moving on step 3
   is that value, measured.

Step 1 is worth its own line: an empty `0x003A` (count 0) **clears** the
record — the handler zeroes `+0x400/+0x404/+0x408` before its loop — so the
control is the panel going blank *after* the spawn burst already filled it,
which is a stronger control than a panel that was never written.

### 14f. What is still open

- ~~**L6's panel criterion remains UNVERIFIED.**~~ **CLOSED by the run in
  §14g** — the panel followed all three steps with the ranks against the
  right names.
- ~~**The fix is verified statically only.**~~ **CLOSED by the same run.**
  The diagnosis was OBSERVED before it; the cure is OBSERVED now.
- ~~**`crashwatch.ps1` is untracked**, committed by nobody.~~ **CLOSED the
  same day**: the terrain arc landed it as `d0899cf`, "Crash detection,
  because liveness polling could never have caught it". It is the instrument
  that caught this crash after liveness polling missed it twice, and the
  verification run above should be watched with it rather than `Get-Process`.
- **Column 3 is still RECONSTRUCTION**, exactly as §8a left it. Sending the
  rank there reproduces an invariant the client maintains; no assert names it.

## §13. Step 9: the kill window, and the template that looked richer (2026-08-15, `34ee86b`)

A kill sent one message — `0x00F1` with the death bit. It now sends the three
the real service sends, same tick, same agent, in ArenaNet's order:

```
0x00F1 [agent, 0x10]     the death status
0x00EE [0, 26]           the reward -- a SINGLE message
0x0026 [agent, 8]        the flags byte
```

The reward encodes to `ee00000000001a000000`, byte-identical to the capture.

**The pair is a trap, and refusing it is the finding.** The corpus holds a
richer-*looking* `0x00EE` template — `[10, 0]` followed byte-adjacent by
`[0, X]`, X ∈ {100, 126, 250, 500}. It is **not** a kill shape: 6 of its 7
sightings fire 6.8–31.5 s from any death, inside a recurring broadcast burst
that is always preceded by `0x009C [agent, 100]`. The seventh landed on the
Wolf's kill tick — **and that tick carries the `0x009C` marker too**, which is
what gives the coincidence away. The three clean kills carry one message and no
`0x009C`. Copying the pair would have looked like more fidelity and been less.

**Two counts this arc had wrong, re-measured over both captures:**

| claim | was | is |
|---|---|---|
| deaths in the corpus | 4 (§6, step 0c) | **5** — agent 38 dies twice on one connection |
| `0x0026` value 8 | "exactly once, on the Wolf" (`authsrv.py`) | **4**, `{9: 200, 8: 4}`, every one a death |

The second was one capture's count written before the second capture existed.
The first matters more than a number: **agent 38's second death carries neither
reward nor flags**, so a repeated `EFFECT_DEAD` on an already-dead agent awards
nothing (n=1) — which is also a hint that the reward is per-kill rather than
per-status-message.

**`test_killwindow.py` takes the CORPUS as its oracle**, re-deriving the live
template from `vault/captures/live/*` every run rather than pinning a literal,
so adding or re-decoding a capture moves the expectation instead of leaving a
stale constant behind. 21 checks, floor 6 (the vault-less section), proven red
by setting the reward to the Wolf's contaminated 126.

**Left open, deliberately:** `attr_id 0 = experience` stays UPSTREAM/UNVERIFIED
— 26 is copied from the wire, not derived. Whether it varies by creature is
UNMEASURED, though three different creatures all gave 26. `0x009C` is still
n=1 as a kill signal and is not sent. And one element of the live kill window
is observed but unsent: **`0x009F [3, agent, 0]`** — `GV_ATTACK_STOPPED` on the
dying agent, on 3 of the 4 rewarded kills. It is a separate mechanism (an agent
ceasing its attack) and is the obvious next candidate.

## §12. Step 8: the premise was wrong, and the data said so (2026-08-15, `e4bb222`)

`ENEMY_SKILL_FRACTION = 0.25` is gone. Damage is now the skill's own scale
endpoints interpolated by the client's own formula at a rank.

**Step 8 as planned would have shipped an invention.** The plan — and gate 3 —
assumed `scale0/scale15` is damage. It is not. The client's table gives a
*magnitude* and never says what it means, and `type_code` cannot discriminate
because it is the skill's TYPE (a Spell can heal or harm). Measured on our own
enemy's bar:

| id | skill | client scale | GWW progression var | damage? |
|---|---|---|---|---|
| 276 | Restore Condition | 10→70 | **Healing** | no |
| 253 | Scourge Sacrifice | (dur 8→20) | **Duration** | no |
| 312 | Holy Strike | 10→55 | **Holy damage** | **yes** |
| 289 | Vital Blessing | 40→200 | **+ Maximum health** | no |

**Three of the four are not damage.** Wiring scale-as-damage would have had the
enemy hurting the player with a heal for 10–70 and an enchantment for 40–200 —
worse than the flat fraction it replaced, because it would have looked
principled. This is the gate map's own rule biting the gate map.

**So the split is: magnitude measured, meaning sourced.** The meaning comes from
GWW's own `{{Skill progression}}` variable names, quoted verbatim into
`content/world.toml` with a per-skill citation, for all twelve skills the two
bars touch. Every wiki endpoint matches the client's table exactly — two
witnesses, no shared ancestry. The server models only the labels named in
`SCALE_MEANS_DAMAGE`; everything else lands as "no modelled effect" and says so.
`skill_damage()` returns **None, not 0**, so a caller must decide what an
unmodelled skill means rather than silently dealing nothing.

**The plus is load-bearing.** `"Holy damage"` IS the skill's damage;
`"+ Damage"` is ADDED to the attack it rides. So Power Attack's bonus goes
through `hit_enemy` as one damage message — two would draw two numbers on
screen for one swing.

**The chain gate 1 was about now closes.** The skill record names its attribute
(+0x29), the attribute indexes `s_attrib`, and the rank comes from the same
content row `0x003A` is built from:

- Power Attack → Strength, player rank **12** → **34** damage
- Desperation Blow → Tactics, player rank **1** → **12** damage

Identical 10→40 tables, 22 points apart, purely because the ranks differ. That
is exactly what "the server models none, so `2 * rank` is 0" cost.

**Consequence recorded, not hidden: most of the enemy's bar no longer damages.**
That is the correct answer. R4a's criterion still holds — the player dies to
`land_swing`, which this does not touch. If the owner wants a dangerous enemy,
that is now a *content* decision (pick a damage bar), not a code one.

**Still open here:** the rounding tie-break stays UNRESOLVED, and
`test_skilldamage` §5 proves it cannot bite — no skill in the effect table
lands on a .5 at any rank 0–15. Damage also still lands AT PRESS rather than at
cast end; magnitudes moved, timing did not.

## §11. Step 7 landed: the wire half of L6 (2026-08-15, `1339bfe`)

> **PARTLY SUPERSEDED by §14, same day.** Everything below about the ids, the
> bounds, the refusals and the content binding stands. The **ORDERING does
> not**: this section says "triples" throughout, and `0x003A` is column-major
> — `ids | ranks | ranks`, not `(id, rank, rank)` apiece. The interleaved
> payload it describes asserted the client dead on `CharData.cpp:202` in every
> session that ran it. Two names below have moved with the fix:
> `attribute_triples()` → `attribute_columns()` and `ATTRIBUTE_TRIPLES_MAX` →
> `ATTRIBUTE_COLUMN_MAX`. This section is left as written rather than edited,
> because what it got right and what it got wrong came from the same pass.

`0x003A` now carries five real triples instead of `[0] * 42`. What that
constant actually was, once the handler's divide-by-three is applied: **fourteen
(0,0,0) triples — fourteen writes of rank 0 to attribute 0**, accepted in
silence, which is why nothing ever caught it.

**Emitted:** `(17,12,12) (18,9,9) (19,6,6) (20,3,3) (21,1,1)` — profession 1's
five attributes with distinct ranks. Ids measured (`s_attrib`), ranks OURS.

**Slot 3 is the load-bearing uncertainty and is labelled as such at the call
site.** No assert names it. What is measured is that the client's own
pending-change apply adds the *identical* delta to it and to `baseValue`, so
sending the rank in both reproduces the client's invariant rather than
inventing a second number. The reading that fits everything seen is
base-rank vs effective-rank-including-bonuses — equal for a character wearing
no runes, and ours wears none. **If a capture ever shows the two differing,
that is the line that was wrong.**

**`ATTRIBUTE_COUNT = 42` was renamed, not deleted**, to
`REAL_PROFESSION_ATTRIBUTE_COUNT`: it was a true statement about a different
set all along. Three client-asserted bounds now sit beside it —
`CHAR_ATTRIBS = 51`, `ATTRIBUTE_RANK_MAX = 12` (AcctTemplate:441),
`ATTRIBUTE_TRIPLES_MAX = 16`. That last is corroborated twice, by the
`array32`'s declared 48 elements and by `AcctTemplate:423`'s `attribCount < 16`.
**Both agree, so one message always suffices for a real character** (primary +
secondary ≤ ~10 attributes) and the `ceil(N/16)` batching `ATTRIBUTES.md` §6
describes belongs to RESKIN's custom tables, not to combat.

`attribute_triples()` refuses rather than clamps on every bound the client
asserts, plus a duplicate id — which would otherwise mean "last one wins"
while wearing a perfectly valid shape.

**What is NOT done, and needs the harness.** The wire half is testable offline
and tested (`test_spawn_burst` §4, floor 34; the payload is bound to the
content row and proven red by changing one rank). **L6's actual criterion —
the panel showing rank R — is unverified**, and per H5 no tool can read the
HUD, so it stays operator-confirmed. The `attributes` probe was rewritten for
exactly this and is ready to run:

```bash
python toolkit/harness/session.py --probe attributes --explorable
```

Its step 2 sends the five ranks; **step 3 reverses them across the same names**,
so a panel that does not follow means step 2 passing was a coincidence. That
reversal is the discriminator, and it is why the ranks are distinct.

The residual from §8b stands: the write chain and the panel's read chain
provably share one record, one locator and one TLS-resolved manager, but the
control's runtime agent binding is not a byte pattern. This probe is what
closes it.

## §10. `s_attrib`, and the numbering contest that dissolved (2026-08-15)

H4 and the registry's top row are closed, and not by picking a winner. Reading
the client's own attribute table showed the two rival schemes were answering
**different questions**, which is why both had good witnesses.

Found from `ConstAttrib.cpp`'s own `index < arrsize(s_attrib)` asserts
(`0x005a92a1`, `0x005a92d1`, `0x005a9301`, `0x005a9331`), then the four
accessors' shared idiom — `cmp esi, 0x33` then
`lea eax,[esi+esi*4]; mov eax,[eax*4 + <base>]` — giving **base `0x00A35740`,
stride 20, 51 rows**, columns at `+0x00`, `+0x08`, `+0x0C`, `+0x10`.

| offset | meaning |
|---|---|
| `+0x00` | profession id (1–10 playable, 11 = none) |
| `+0x04` | the row's own index — self-declared, and what makes the locator refutable |
| `+0x08` | name string id |
| `+0x0C` | description string id |
| `+0x10` | 1 if the profession's PRIMARY attribute |

**The verdict, both halves:**

- The **index space is contiguous 0..50**. No gaps. This is what `0x003A`'s
  first array is bound-checked against and what the per-agent record is indexed
  by — so it is the numbering the **wire** wants, and what step 7 emits.
- The **ten playable professions own exactly 42 rows** — precisely OpenTyria's
  `Attribute_Count`. It counts attributes, not indices, and was never a claim
  about the id space.
- The remaining 9 belong to **profession 11**, which has no primary and no
  resolvable name. Three of them are **26/27/28**, sitting immediately before
  Dagger Mastery at 29 — exactly the "+3 offset from Dagger Mastery on" that
  the gapped scheme described. Enumerate only real attributes in id order and
  you skip three in the middle; that is the whole of the "gap".

Per-profession, every count and primary matches retail: Warrior 5 (Strength
17), Elementalist 5 (Energy Storage 12), the other eight 4 apiece — Mesmer
(Fast Casting 0), Necromancer (Soul Reaping 6), Monk (Divine Favor 16), Ranger
(Expertise 23), Assassin (Critical Strikes 35), Ritualist (Spawning Power 36),
Paragon (Leadership 40), Dervish (Mysticism 44).

**The independent leg.** The profession column lives in `Gw.exe`; the names
live in the owner's `Gw.dat` and come back through `textrec`, a decoder written
for an unrelated arc. The 42 rows the EXE assigns a profession are **exactly**
the 42 the ARCHIVE can name — `named-not-real=[]`, `real-not-named=[]`. One
partition, drawn twice, by two mechanisms that share nothing.

Also recovered on the way, and directly useful to step 7: **`AcctTemplate:441
data.attribValue[index] <= 12` caps a rank at 12**, matching `CharData:202`'s
`cmp esi, 0xd` bound of 13 (0..12) on the downstream `s_attribPoints` lookup.
`AcctTemplate:423 data.attribCount < 16` bounds a build template's attribute
count, which is the ceiling one `0x003A` message of 16 triples has to clear.

Tooling: `toolkit/clientscan/attribtable.py` (stdlib only, structural locator,
`--emit-content`) and `test_attribtable.py` (29 checks, floor 25 archive-less;
three sabotages prove the locator refuses rather than guessing). Rows emitted
to `vault/content/attributes.toml`, 51 of them, name ids only — no authored
text, per the provenance rule.

## §9. The suite's one red is REAL, is NOT this arc's, and names a new client build

**Final full run: 95 green / 1 red of 96, 4,641 checks** (`python toolkit/run_suite.py`,
2,722 s). The baseline at the start of this session was 94 green / 0 red / 4,584
checks, so this arc added two test files and no failure. The red is
`test_origin.py`, 2 checks:

```
[FAIL] the whole vault is at most ONE client build   {38797: 1833, 38833: 4} + 919 unknown
[FAIL] and that build is 38797
```

**This is the guard doing precisely its job.** `TESTS.md` says of it: every
capture that names a build names 38797, "asserted as an invariant so the first
capture from a second build turns it red." That first capture has now arrived.

The four 38833 files are `vault/captures/selftest/authsrv-2026081⁠4T{185031,
185208,190427,195052}-c1.jsonl`, and they are **another session's**: this tree's
`test_handshake.py` hard-codes `BUILD = 38797`, while the
`crossbuild-plan-snapshot-7e3bae` worktree sets `BUILD = None` and derives it
from the exe it selects. The vault is shared, the selftest capture path is
absolute, and their run stamped 38833. Timing corroborates: the earliest is
18:50, after this session's own baseline suite had already passed green.

**Two consequences that outlive this arc, neither of them combat's to fix:**

1. `test_origin.py`'s message claims the single-build census "resolves
   `PLAN.md` §10's UNVERIFIED flag". **That claim is now false** and the census
   needs re-deciding — tolerate a second build, or scope the census. It is a
   real decision, not a lint fix, so it is named here rather than made here.
2. The 38833 snapshot exists but `pinned.py` does not know it, so every tool
   that resolves "the pinned client" still reads 38797. That is *correct* for
   this arc — every address in `studies/` was measured against 38797, and §8's
   results are stamped to it — but it is a fork in the road the crossbuild arc
   owns.

**Nothing was deleted or rewritten.** Removing another session's captures, or
loosening the invariant to make a red go away, is exactly what the guard exists
to prevent.

## §8. Step 5's client-byte results — both critic amendments CLOSED (2026-08-14)

Three read-only digs on pinned build 38797. The two headline answers come from
**ArenaNet's own compiled assert text**, which is the strongest evidence
available here and needs no capture.

### 8a. The triple is (attrib, baseValue, ?) — two of three named by the client

`0x003A`'s payload is three parallel n-dword arrays, and the writer
`0x00819220` takes them as `(record, id, value_a, value_b)` (`ret 0x10`, four
4-byte args). Slot identities, from the wire arrays through the writer to the
record:

| wire array | writer arg | record slot | identity | evidence |
|---|---|---|---|---|
| 1st (`payload+0xc`) | `[ebp+0xc]` | index, `record + id*20` | **attribute id** | bound-checked `cmp ebx, 0x33` (51) at `0x00819241`, then `lea eax,[ebx+ebx*4]; lea esi,[edi+eax*4]`. `ChCliAttrib:249 attrib < arrsize(attribState->attrib)` at `0x0081924e` — **ArenaNet's own word is `attrib`** |
| 2nd (`+0xc+4n`) | `[ebp+0x10]` | `slot+8` | **the rank** — ArenaNet calls it **`baseValue`** | `ChCliAttrib:42 (int)attribState->attrib[attrib].baseValue >= 0` at `0x008187a7`, whose `cmp` at `0x0081879E` reads **`[esi + attrib*20 + 8]`** — that arithmetic is what ties the name to this exact slot. Separately bound-checked ≤ 12 downstream: `CharData:202 level < arrsize(s_attribPoints)` at `0x0091d511` guards `cmp esi, 0xd` before the table lookup |
| 3rd (`+0xc+8n`) | `[ebp+0x14]` | `slot+0xc` | **NOT NAMED** | stored unmodified at `0x0081926F`; **receives the identical delta as `baseValue`** in the pending-change apply (`0x0081877C` adds the clamped delta to `+8`, `0x00818789-0x0081878C` adds the same `[edx+8]` to `+0xc`); never bound-checked, never used as an index, and not read by the reader's derived path. No assert names it |

Also recovered from the same asserts: `attribState->attribPointsAvail` is
`[record+0x434]` (`ChCliAttrib:43` at `0x008187c1`), and it takes its **own**
delta (`[edx+0xc]`), separate from the rank's.

**What this decides for step 7.** Emit the attribute id in slot 1 and the rank
in slot 2 — both OBSERVED. Slot 3 is the open one; since the client's own apply
path moves it in lockstep with `baseValue` from a common zero, **sending the
rank there too reproduces the invariant the client maintains** — but that is
RECONSTRUCTION, is labelled so at the call site, and the operator's panel check
is what would discriminate it. Headquarter's `rank_bonus` naming stays
UNVERIFIED; this pass neither confirms nor adopts it.

### 8b. The panel DOES read what `0x003A` writes (amendment C8a — closed)

The L6 acceptance criterion is sound. The read chain: reader `0x00818C90`
(mirrors the writer's slot arithmetic exactly, `cmp ebx,0x33; lea eax,[ebx+ebx*4];
lea esi,[edi+eax*4]`) ← its **only** caller, a `ChCliApi.cpp` thunk
`0x0080D990` ← its **only** caller `0x008AAFA0` ← reached only through a C++
vtable slot at `0x00B9F7F0`, inside a function cluster carrying
`AttribBtns:268` at `0x008aaf04` — source `P:\Code\Gw\Ui\Game\Attributes\
AttribBtns.cpp`, **the Skills & Attributes panel's own source folder**.

The strongest part is that the two paths provably share one object: the write
forwarder `0x0080EB40` (from the `0x003A` handler) and the read forwarder
`0x0080D990` resolve their manager through **byte-identical** code —
`call 0x0047F660` (a TLS per-thread singleton: `mov ecx,[0xc0f300]; mov eax,
fs:[0x2c]; …`) then `ecx = [eax+0x2c] + 0xac` — and both then hand it to the
same by-agent-id locator `0x00819340`.

**The one gap, and it is honest:** whether the panel control's own `agentId`
field (`this+8`) holds the local player's agent id while the panel is open is a
runtime value, not a byte pattern. Static analysis cannot close it. It is the
obvious reading (the panel only ever shows your own character, and `0x003A`
only ever syncs the local agent) but it is an ASSUMPTION, and step 7's
acceptance names it.

> **CLOSED 2026-08-15 by measurement, §14g.** `--probe attributes` ran caged
> and the panel followed all three steps — including step 3, which reverses
> the rank column while holding the id column's order — with the ranks against
> the right names. The assumption above is now an observation.

### 8c. The tooltip's rank formula (amendment C6 — closed)

**OBSERVED**, at `0x005A8920`, ArenaNet's one general-purpose per-rank
interpolator — called three times from a single caller `0x004F98D0` for
`scale0/15` (`+0x5C/+0x60`), `bonus_scale0/15` (`+0x64/+0x68`) and
`duration0/15` (`+0x44/+0x48`), so it is not scale-specific:

```
value(rank) = max(0, round(lo + (hi - lo) * rank / 15.0))
```

- The divisor is the **literal double 15.0** — verified by a stdlib read of
  `0x0094B930`: bytes `0000000000002e40` decode to exactly `15.0`.
- **No upper clamp on rank.** Nothing compares the rank operand between
  function entry and the `imul`, so ranks above 15 **linearly extrapolate**
  rather than saturating. This matters: GW ranks exceed 12 with runes/headgear.
- The floor at zero is ArenaNet's own assert: `ConstSkill:3769 (int)result >= 0`
  at `0x005a8966`. The module is `ConstSkill.cpp`, identified by its own
  asserts rather than inferred.

**UNRESOLVED, and left that way:** the rounding tie-break. The CRT helper chain
(`0x0046DF80` → `0x005B6E0B` → `_ftol2` at `0x005AEB20`) adjusts by ±**1.0**
(verified by stdlib read of `0x0093C1D0`: `000000000000f03f` = `1.0`), not the
textbook ±0.5, before truncating toward zero. Half-up vs half-even is not
settled. It only bites where an endpoint pair lands on a .5 — skill 316's max
health (10→60, 3.33/rank) is a ready discriminator whenever a rendered check is
possible.

**Tangent worth keeping:** `ConstSkill:3762 index < arrsize(s_energyTable)`
names the energy-cost byte's lookup table — the `11→15, 12→25` encoding in
`studies/skills` §1 is a real table in the client, not a formula.

---

## §7. The loopback validation is blocked on a vault archive-state mismatch (2026-08-14)

> **RESOLVED 2026-08-15 — the acceptance ran and both halves pass, §15.** The
> blocker was real and the diagnosis below is correct: a new ArenaNet build
> arrived mid-session and the harness selected its fresh archive. What
> unblocked it is the first option this section lists — name the build and the
> archive explicitly (`--exe vault/run/2026-08-13_64fae3b1369b/Gw.exe`,
> `RURIK_DAT=vault/dat_study_38833/Gw.dat`) — plus `391e8ca`, which made
> `session.py` pick by BUILD and NAME instead of by newest. The command below
> is what ran, with `--map 90 --explorable` added and a longer hold.

Step 3's acceptance has two halves: an automated loopback run (does the client
accept E4/E5/E6 without asserting; does a second press after E6 produce a second
full cycle) and an operator's rendered check (recharge sweep on the bar,
animation) — the second is manual by design (H5). **Neither ran: the harness
refuses to launch, for a reason entirely outside combat.**

`session.py`'s pre-flight compares `content/maps.toml` against the client archive
and refuses the whole run when any map's id will not bind. Maps 146 and 148 carry
`file_id = 0x8001B97D` — bit 31 set, "replacement pending" — which is **committed
content** (HEAD, working tree clean; the row's own `verified` note explains the
masked-vs-pending distinction). It binds only after `DnArchive` installs the
replacement into the client archive, and the archive the harness selects
(`vault/run/2026-08-13_64fae3b1369b/Gw.dat`, the newest) does **not** have it
installed. The refusal fires for ANY `--map`, because the guard validates the
whole table, not the map being loaded.

**CORRECTED 2026-08-14, later the same day — the cause is not the map arc, it is
that ARENANET SHIPPED A NEW CLIENT BUILD mid-session.** The first write of this
section blamed shared archive state and filed it under the custom-map arc. That
was wrong, and the real cause is worth more than the guess:

- The owner's live install is now **build 38833** (`buildid.py` on `C:\gw\Gw.exe`,
  read-only). `pinned.py`'s `BUILDS` knows only 38519 and 38797.
- A parallel session snapshotted it into the vault **today at 18:14** as
  `client/2026-08-13_64fae3b1369b` — **and a `run/` directory with it**
  (`buildid.py` confirms both are 38833).
- `session.py` picks the **newest** run directory, so it selected the 38833 one.
  Its `Gw.dat` is fresh from ArenaNet and has **never** had the map replacement
  installed — which is exactly what the pre-flight reported. The 38797 run dir
  (`2026-07-29_221c13772c7a`) is the one the map work was done against.

So nothing is corrupt and nothing needs repairing: the harness pointed a brand
new client at a content table prepared for the previous build. **This is the
`RUNBOOK` "an ArenaNet update means redoing that setup in full" case**, and it is
the crossbuild arc's live concern rather than combat's.

**What unblocks it, cheapest first:** point the run at the 38797 build that
already carries the installed replacement (the run directory still exists), OR
install the pending replacement for 146/148 into the 38833 archive with
`DnArchive` (per `studies/maprows`). Then run the loopback acceptance:

```bash
python toolkit/harness/session.py --enemy --keep-open \
  --game-args "--ping-seconds 0.5 --practice-target --explorable" --hold 32 \
  --shots 2.0 \
  --actions "0:play 20:vk:0x43 1:vk:0x20 4:key:7 3:key:6 6:key:7 3:key:7"
```

Slot 7 is skill 322, recharge 3 s; the two presses are 9 s apart so the second
falls AFTER the first's E6 (the repeat-press acceptance — amendment C10's
positive control is slot 6, skill 321, pressed between them). Watch the gamesrv
log for `SKILL_RECHARGE`/`SKILL_RECHARGED` pairs and the client for the recharge
sweep; confirm the second slot-7 press produces a full second cycle. The offline
tests already pin every message shape, order and the timing law, so this run adds
only the two things offline cannot: the client's acceptance of the opcodes, and
the rendered sweep.
