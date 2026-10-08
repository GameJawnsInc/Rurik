# RIDERS — one live session, six outpost riders and CASTAI-H1 (2026-10-08)

*The run record for live capture `20261008T132845`. Labels per
[studies/character/FINDINGS.md](../character/FINDINGS.md). The H1 half is scored in
[studies/monsterai/FINDINGS.md](../monsterai/FINDINGS.md) §18.6; this document carries the
riders, what the run delivered beyond its plan, and what each result changed.*

**Identifiers.** `RIDERS-R<n>` = a step of the sealed plan or an unplanned action in the
outpost, and its result. `RIDERS-F<n>` = a finding the run delivered beyond its plan.
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

## 1. The run

- **Capture** `vault/captures/live/20261008T132845`, the owner, the secondary account,
  build **38974**, `--mode base`, plan `vault/plans/live_riders_h1.txt` sealed before launch
  (sha256 `4b653596…`, two seals in agreement), exe unchanged across the run. Three keys
  tapped, three connections decrypted, **zero capture gaps**.
- **Connections.** `:65410` Kamadan (map 449, the outpost: t 50.2–288.7 s) and `:51409` the
  Plains of Jarin (map 430, t 288.9–604.0 s), plus the auth channel.
- **The party.** The owner had no Monk hero unlocked, so the healer was **Koss, a Warrior
  hero given a Monk secondary** (c2s `0x0041 [253, 3]`) and four heals: Orison of Healing
  281, Healing Breeze 288, Healing Touch 313 and 1396, which the owner's screen named Word of
  Comfort. Koss ran in **Avoid Combat** for the whole explorable (c2s `0x0015 [30, 2]` at
  308.6 s).
- **The owner's notes** (F11 ordinals): 1 — the first bar was built out of order, cleared
  and rebuilt (the F10 at 125.3 s); 2 — at the full party the Add button was NOT greyed and
  the screen said the merged party would be too large; 3 — the fights, below. The `front`
  and `calm` steps were pressed through: their cases happened inside `fights`.

## 2. The riders

| | Step | Prediction (sealed) | Result | What changed |
|---|---|---|---|---|
| **RIDERS-R1** | `swap` — two hero-bar slots swapped and swapped back | two c2s `0x005E`, mirror images; retail sends NOTHING | **c2s HELD** (`[253, 281, 0, 288, 0]` twice — the same words, because the skills changed slots). **Reply REFUTED**: each is answered at +37 / +44 ms by `0x00D9` for the SOURCE slot (where the picked-up skill was, now holding the target skill), `0x00D9` for the target slot, then `0x0065 [hero, mask]`. 2 of 2. OBSERVED | `BAR_EDIT_RETAIL_ECHO` (`--no-bar-edit-echo`); `test_heroskilltoggle` §5r, `test_charstore` |
| **RIDERS-R2** | `empty` — a skill dragged into an empty slot and back | c2s `0x005F`, no reply | **NOT EXERCISED.** The owner dragged from the skills PANEL, which sends `0x005C [253, 4, 301, 0]`, not from another bar slot; the plan never said "from the bar". `0x005F` stays on no retail tape | nothing; the next plan says it |
| **RIDERS-R3** | `full` — one Add click at the outpost's cap | the click DOES send `0x009F` and retail answers within ~1 s | **HELD.** At 4 of 4 (`0x00B0 [20, 4]`; Kamadan's `max_party` is 4) the client sent `0x009F [4]`; retail answered at +54 ms with exactly **one `0x01BC [64]`** and nothing else of the party's. The button was not greyed; the screen showed row 64's sentence (the owner's note 2). The refusal lives on the SERVER side. OBSERVED 1 of 1 | `henchparty.RETAIL_HENCH_FULL_CODE`; the default sends it (`--no-party-full-reply-retail`); the HERO add's refusal, on no tape, stays silent |
| **RIDERS-R4** | `kick` — each added henchman kicked | per kick `0x00A8`, answered by `0x01C0` then `0x00B0` (our RECONSTRUCTION) | **c2s HELD** (`0x00A8 [3] / [2] / [1]`, one word, the agent). **Order REFUTED**: `0x00B0 [20, n]` THEN `0x01C0 [36, agent]`, 3 of 3, at +34..47 ms — size before row, the add's own order. The words are ours | `henchman_kick_batch(size_first=True)` (`--hench-kick-row-first`); `test_henchparty` §1r |
| **RIDERS-R5** | `fkeys` — the held set's key, an empty set's key, a switch into an energy weapon and back | same-set and empty-set presses answered by nothing; the energy switch carries 41 then 43 | **Partly read.** Between the step's F9 (245.4 s) and the first switch (267.0 s) NO `0x0032` left the client — if the owner pressed the held and the empty keys there, the client refuses both locally and "retail's reply" is moot (owed: the owner's word that those presses happened). The switch `0x0032 [1]` and back `[0]` were answered at +46 / +33 ms by `0x0148 ITEM_SET_ACTIVE_EQUIP_SET [90, n]` and one `0x014B ITEM_CHANGE_LOCATION` (item 10573) — **no property 41 / 43**, so either the switched set moved no maximum energy or the prediction fails; which is UNVERIFIED (the item's modifiers are not read here). One unexplained c2s `0x0045` (a 53-byte blob) at 257.8 s | nothing shipped |
| **RIDERS-R6** | unplanned: the party window's **Leave** (before `full`, to clear Koss) | — | **First retail witness** of c2s `0x00A2`: sent with `0x001F [40]` at the same instant, as on our client. With only a hero in the party the reply at +38 ms is the hero kick's OBSERVED batch, once — `0x0075 [253]`, `0x01C3 [36, 20, 253]`, `0x00F8 [253]`, `0x00B0 [20, 1]`, `0x0145 [124]` — which is what ours sends. The Leave with hired henchmen stays RECONSTRUCTION | nothing; corroborates `handle_party_leave` |
| **RIDERS-R7** | unplanned: Koss re-added, c2s `0x001E [6]` | — | **First retail witness of HERO_ADD** (0 of 96 before): one batch at +41 ms — `0x00B0 [20, 2]`, `0x00B1 [0, 20]`, the hero's item stream (`0x0144`, `0x013F`, six `0x0162` + `0x013E`, `0x015A`), then `0x0037`, `0x00B7 [182, 1, 3, 0]`, `0x00DA`, `0x0065`, `[43]`, `[41]`, `[42]`, `0x009C`, `0x0065`, `0x003A`, `0x0072 [6, 182, 81, 2]`, `0x009A`, `[36]` and `0x01C2 [36, 20, 182, 6, 3]`. The hero's agent id changed, 253 → 182 | owed: a field-level comparison against ours (DESKWORK-D1's hero ADD, RECONSTRUCTION) |

## 3. Beyond the plan

- **RIDERS-F1 — the first live tape on build 38974.** Both game connections frame to their
  last byte in 38974's numbering (5,794 and 16,711 messages); the control — the same s2c
  bytes through the pinned numbering — stops at offset 1,139 on both; the new `0x0194`
  arrives once per connection. The 38974 key-tap cave, never run in a live client before,
  tapped all three keys. This is the verification `studies/crossbuild/FINDINGS.md` §11.5
  listed as "still to see". OBSERVED.
- **RIDERS-F2 — a hero's bar edits, the census.** Over every live game connection (129):
  `0x005C` on the PLAYER's bar is answered with one `0x00D9`, 7 of 7 (the observer's own
  agent on all seven captures); on a HERO's bar with `0x00D9` then `0x0065`, 17 of 17; and
  `0x005E` (hero only) as RIDERS-R1. Our server already matched the player; the hero's mask
  was missing and now ships with R1. OBSERVED.
- **RIDERS-F3 — the hero's suppress mask, on retail's wire.** Koss loaded with mask **8**
  (slot 3 suppressed on the account — every earlier hero load carried 0, 8 of 8). Retail's
  mask held 8 through the sets into slots 0, 1 and 2 and dropped to 0 on the set into slot 3:
  the set clears its own slot's bit, which is the client's `0x008212C0` `btr` that
  `hero_mask_write` follows (EVID-D1C-1). That rule was read from the binary only; it now has
  a retail witness, and `test_heroskilltoggle` §5r holds all 19 replies to it. OBSERVED.
- **RIDERS-F4 — `castethogram`'s health integrator ignored property 32.** `0x009F [32,
  agent, 0]` (GV_MAX_HP_REACHED) sets the bar full and the regeneration to zero on the client
  (skills FINDINGS §64.5); the integrator ran a closed Healing Breeze's rate on to the next
  `[44]`, so four of Koss's heals read as heals on a full-health player. Fixed (a `max32`
  event). Re-run over the committed Z1 and Z2 scores: **no verdict moved**, six Z3 spike-target
  and two Heal Area caster readings shifted. MEASURED.
- **RIDERS-F5 — death penalty on the wire.** The observer died at 443.42 s and stood again
  at 455.69 s at full health (the untargeted `[55]` setter, 1.0), Koss re-created at the same
  instant at 0.566 — a shrine warp's shape (`studies/movecode/`, SHRINEWARP), with the hero
  ALIVE throughout (his status never carried the dead bit); why it fired is not read here.
  Every damage word after it is in 1/119 units where before it was 1/140: maximum health
  140 → 119, −15 %. OBSERVED.

## 4. CASTAI-H1, in one line each

Scored by `studies/monsterai/review/healerrun.py`; the table is monsterai §18.6.
**H1.P1 NULL** (15 heals on another ally, floor 20 — but all 19 heals landed on a hurt
target and the most-hurt was chosen 2 of 2). **H1.P2 FAILED**, 0 of 6: every Orison on the
observer was cast with the deficit BELOW its heal (deficits 0.148–0.244 against heals
0.286–0.336) — the wiki's rule is refuted, and our server never modelled it.
**H1.P3 HELD**, 0 of 6 Healing Breezes onto a carrier. **H1.P4 HELD, post hoc**, 5 heals
in three calm windows, none on a full target. Retail's hero and ours agree on every scored
point: the hurt-most of caster and allies under `HERO_HEAL_AT` (all 19 retail heals at
≤ 0.852), and no enchantment onto a carrier.

## 5. Owed

- **R2**: one drag from a bar slot into an empty slot, for `0x005F`'s reply.
- **R5**: the owner's word on whether the held-set and empty-set keys were pressed; the
  switched set's item modifiers, to read the missing 41 / 43.
- **R7**: the hero add's batch against ours, field by field.
- **The Leave with hired henchmen** (R6 had only a hero): its per-row order, now that the
  kick it was modelled on turned out size-first.
- **R3's hero half**: a hero add at the cap, on retail.
- **The 0x0041 / 0x000F replies on a hero** (the secondary change and three attribute
  raises at 82.6–84.4 s): on the tape, unread.
