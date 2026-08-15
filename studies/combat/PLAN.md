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
| Attribute numbering | contiguous 0–41 (OpenTyria, single witness; current code) | gapped 0–44/51-row (3 lineages + client text-id table + measured table — CORROBORATED) | Step 5 (client-table); step 6 item 1 (wire) |
| ~~`0x003A` triple positions~~ | **RESOLVED for slots 1–2, §8a**: slot 1 = `attrib` (id), slot 2 = `baseValue` (rank), both named by the client's own asserts | slot 3 remains NOT NAMED — moves in lockstep with `baseValue`; Headquarter's `rank_bonus` still UNVERIFIED | step 6 item 1, or a rendered check |
| ~~Panel reads the array `0x00819220` writes?~~ | **RESOLVED YES, §8b** — same TLS singleton, same locator, chain ends in `AttribBtns.cpp` vtable code | residual: the panel control's runtime `agentId` is an ASSUMPTION static analysis cannot close | step 7's operator check |
| Tooltip rank interpolation | **RESOLVED, §8c**: `max(0, round(lo + (hi−lo)·rank/15.0))`, literal 15.0, no upper clamp | the rounding TIE-BREAK (half-up vs half-even) is unresolved — ±1.0 adjust, not ±0.5 | a rendered check on a .5-landing pair (skill 316) |
| Client energy gate on USE_SKILL | sender disassembly: no energy check (skillcast §7) | agents.py comment: empty pool refuses all eight (5048f6a; commit msg blames missing weapon) | Loopback drain-pool probe with positive control (C10) |
| "One cast per skill per session" without E5/E6 | skillcast study's own synthesis | flagged UNVERIFIED by both capture readers | Step 3 repeat-press acceptance (C10) |
| E6 scheduler: keyed to E5 + recharge? | one measured cycle says yes (+3 ms) | unmeasured on the other 13+ cycles | Step 0b |
| `0x00E4` in the self-cast cycle: consumed or discarded? | live server sends it in every cycle | in-tree MEASURED: handler returns early on self | Step 0a + step 3's discriminating operator check (C1) |
| `0x00EE` attr_id 10 ([10,0], Wolf kill only) | — | — (wholly unknown) | Registry only; watch step 6 |
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
| 3 | 🔶 offline half ✅ 2026-08-14, `f5f65b2`+`77b65d1` — emitter (1,333 client-table rows, build stamped from bytes), the four-opcode cycle on the observed template, THE QUEUE LAW (E4 at accept, cast begins when the caster frees — fits 4/4 Necro cycles ≤14 ms; the naive press+activation model is refuted by +0.64 s/+0.57 s residuals), overrides names 227–230, cross-thread cast-timer test (200 presses → exactly 200 of each phase). Attack-skill E5 timing rides the weapon — recorded as unmodeled divergence. GV 58 deliberately unsent (0 of 21,543 live). **Loopback acceptance BLOCKED — see §7** |
| 4 | ✅ 2026-08-14, `0ddfbd0`+`9d97f45`+`a7971b1` — `+0x44..+0x68` decoded as u32 (duration0/15, skill_arguments bitfield, scale0/15, bonus_scale0/15; +0x50 stays NOT FOUND). Reproduces the 4-skill FINDINGS anecdote byte-exact and asserts its green-render rule. **C7's wiki third witness ran and agrees with all 14 endpoint values GWW lists**, plus costs and recharge — and checks the other direction too (no unlisted set may render green), which is what makes Rush's constant-25-with-bit-clear a real discriminator. Emitted to the content rows; **nothing consumes them until step 8**. `test_skilltable` floor 26→46 |
| 5 | 🔶 **research half ✅ 2026-08-14, §8** — the triple's slots 1–2 named by ArenaNet's own asserts (`attrib`, `baseValue`), the panel's read path traced to `AttribBtns.cpp` (C8a closed), the tooltip formula measured (C6 closed). **Still to do in code**: adopt the gapped numbering, replace `ATTRIBUTE_COUNT = 42`, retire the stale `authsrv.py:552-557` comment, and pin the handler constants in a test |
| 6–10 | ⬜ |

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
