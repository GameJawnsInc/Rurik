# NOMESH — a map served with no navmesh, and the client's own map edge

**Written 2026-09-25**, from one crash the DESKWORK pass-6 re-check tripped over
(`studies/deskwork/CONFIRM-2026-09-24.md`, the backpedal correction) and a second one
nobody had joined to it. Labels per
[studies/character/FINDINGS.md](../character/FINDINGS.md).

**Identifiers.** `NOMESH-F<n>` = a finding, below. `NOMESH-RECT` = the fix that
landed from them (the bound and the portal refusal), the tag its code and console
lines carry. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

## The specimen

Harness `20260925T083808`, loopback, build 38797, main `069635de`, no `--map`, the
default archive (`vault/dat_study/Gw.dat`), the client from
`vault/run/2026-07-29_221c13772c7a`. `--walk "wait:3 S:3 W:3"`.

1. The S hold backpedalled the player 120 u into `ascalon_to_corridor` (map 148,
   (9326, 8077), radius 200) and the portal fired: `0x0028 → 0x01A5 → 0x0099`,
   map 168.
2. Map 168 is the slice's authored corridor, file `0x5F0B3`, which exists only in the
   slice archive (`vault/run/slice/Gw.dat`; `content/world.toml`'s own note on the
   portal says so). The server: `[map] no navmesh for 0x5F0B3: 'no file id 0x5F0B3 in
   the archive'`, collision OFF.
3. The W hold armed a lead (2056, 1536) from the spawn (1536, 1536), `clip_why
   no-mesh`, and the 1z-di arrival re-grant chain then sent eight more chords east,
   2576 … 6216, one per 1.8 s arrival, the client silent.
4. The client died at 08:39:14 local — the same second RE-GRANT 4 went out (12:39:14.75
   UTC). RE-GRANTs 5–8 went to a dead client; the server learned of it at the reset.

## Findings

| Token | Label | Finding |
|---|---|---|
| **NOMESH-F1** | OBSERVED ×2 | **A client handed a map whose file it cannot load builds a DEFAULT map, and that map's rect is (−3072, −3072, 3072, 3072).** 083808's `report.json` `gw_log`: `Map file '0x05f0b3' failed to load. Attempting to re-bloat.` → `Error: Map '0x05f0b3' failed to load` → `Error: Creating default map`, then every `MapQueryAltitude()` line prints `mapRect=(-3072.000000,-3072.000000,3072.000000,3072.000000)`. Harness `20260914T085004` logged the same three lines for the same file. `studies/customarea/FINDINGS.md` had recorded the fallback's existence ("`MapLoad` falls back to the empty default map") from the disassembly; this is its rect. |
| **NOMESH-F2** | OBSERVED | **The 0x0029 handler asserts on a grant point past the map: `pos.x <= worldDims.x1`, `P:\Code\Engine\Agent\agint.h(929)`.** The crash's Trace has the message dispatcher called with argument `0x00000029`, and `esi` points at the float pair `0x45814000 0x44C00000` = **(4136.0, 1536.0)** — RE-GRANT 4's own point, sent the same second. RE-GRANT 3's (3616, 1536) was ACCEPTED, so on the default map `worldDims.x1` lies in **[3616, 4136)** — bracketed, not measured, and larger than the rect. |
| **NOMESH-F3** | OBSERVED | **Between the rect and `worldDims` the client does not die; it logs.** 108 consecutive `MapQueryAltitude() invalid params` lines, x 3073.6 → 3580.8 at y 1536, 4.03–5.76 u apart (the body walking RE-GRANT 3's chord at 288 u/s). So the rect (F1) is the tighter of the two things the client enforces, and the one worth bounding to. |
| **NOMESH-F4** | OBSERVED | **The same default map breaks an agent CREATE too.** 085004 died on `pos.y <= worldDims.y1`, agint.h(929), creating `corridor_boss` at (1536, 10400) (the crash's `esi` block opens `0x20`, `0x5E` = agent 94). A lead bound cannot help an authored population; only not zoning there can. |
| **NOMESH-F5** | OBSERVED | **The server had no bound at all.** `_a2_clip_lead_ray`'s no-mesh door returned the ray unchanged ("disables clipping rather than freezing the lead"), and the 1z-di chain re-granted from each arrival along the held heading until `KBD_LEAD_CHAIN_MAX` (12). `test_nomeshrect.py` §4a replays the leg from the capture's own `kbd_leg act=arm` row through the real `kbd_lead_chain_tick` and reproduces the run's eight wire points exactly. |
| **NOMESH-F6** | OBSERVED | **Nothing stopped the portal.** `portal_tick` had no servability check; the portal-destination prewarm runs only under `--map`, and the harness's plain `session.py` passes none. Travel's `TRAVEL_UNSERVABLE` withheld unwarmed maps; portals had no sibling. |
| **NOMESH-F7** | OBSERVED ×2, cause NOT FOUND | **On the default map a W key-up sends no movement report.** 083808: nothing between the W hold's end (12:39:10.56) and the crash 4.2 s later, so every re-grant after the release went into a silence the chain reads as "still walking" — how a 3 s hold (~864 u at 288 u/s) became grants reaching 2,600 u from the spawn. 095537 (the confirmation's Run B, same map, same hold): again nothing but `0x8009` after the release. The CONTROL, 095407 (Run A, same session, map 148 with its mesh): both key-ups were answered by a report and a `KBD STOP-ECHO`. Why the default map's client stays silent is not settled; NOMESH-RECT makes it harmless (the chain stops at the bound) rather than explaining it. |

## NOMESH-RECT — what landed

1. **The bound** (`toolkit/authsrv/maprect.py`, stdlib, pure). With no mesh loaded, the
   lead's no-mesh door stops the ray at the map's rect inset by 32 u, keeping its
   heading, and names the door `no-mesh-rect`; the re-grant from the bound then makes no
   progress and the chain stops (`regrant-stop`, `no-progress`). Without a known rect
   the door gives the historical unbounded answer, and a meshed instance never reads the
   rect at all.
   - The rect's SOURCE is labelled per case. `client-default` — the archive holds no such
     file id, so the client (holding the same archive, the prewarm doctrine) builds its
     default map: F1's rect, **OBSERVED**. `map-params` — the file is present and only
     its mesh is missing: the file's own Map Parameters rect (`0x2000000C`, read through
     `mapexport.map_rect`), which the client copies verbatim
     ([customarea FINDINGS](../customarea/FINDINGS.md), "Map Parameters"). Positive
     control: all 6,120 trapezoids of map 148's own mesh lie inside the rect its own
     file declares. A client-held archive records no rect and says why.
   - The inset, 32 u, is **RECONSTRUCTION**: over five of F3's largest per-frame steps,
     so a copy arriving on the bound never samples past the edge. Nothing says the edge
     itself is unsafe.
   - It is read where the mesh fails (`load_pathmap`, while the archive is still ours)
     and recorded; instance load reads the record, never the archive.
2. **The backstop** (`_rect_bound_wire_point`, `send()`'s first statement). Every other
   sender of a point — 0x0029, 0x002A, 0x002C, any agent — is clamped into the same
   rect, labelled `RECT-CLAMPED` on its console line and recorded as a `rect_clamp`
   event. It clamps rather than drops, because a 0x0029 withheld after its 0x002B trips
   AgAgent.cpp:1198 (MOVECODE-1z-cm). Creates are not grants and are untouched (F4 is
   the portal's to prevent). No-op, returning the same object, on a meshed instance.
3. **The portal refusal.** At startup, with or without `--map`, one file-id-table read
   (~0.15 s) withholds every enabled portal destination whose map FILE the archive
   lacks (`PORTAL_UNSERVABLE`). Walking into such a portal is refused with nothing sent
   and the portal disarmed until the player leaves. A present file with a missing mesh
   is NOT withheld: the client has the real map there, and (1) bounds the lead to its
   own rect. On `vault/run/slice/Gw.dat` (`RURIK_DAT`) nothing is withheld.

## What it does not cover

- **`--map 168` served directly from an archive without the file** still hands the
  client its default map. The lead is bounded; an `--area` whose rows lie outside
  (−3072, 3072) still asserts on create (F4). The server prints `NO-MESH BOUND …
  [client-default …]` at instance load, which is the warning.
- **The client's own keyboard walk** on a meshless default map is the client's. The
  bound governs what WE name.
- **F7** is open.

## Client confirmation — 2026-09-25, both runs PASS

The owner's go-ahead; questions registered before either launch; the server from this
branch's tree (`source:` line in each gamesrv.log), build 38797, default archive.

**Run A — the owner's reproduction, `20260925T095407`.**
`python toolkit/harness/session.py --warn 5 --hold 8 --game-args "--explorable" --walk "wait:3 S:3 W:3"`

| Q | Registered | Result |
|---|---|---|
| A1 | startup prints `portal destination map 168 WITHHELD` | **yes**, gamesrv.log line 3 |
| A2 | the S hold reaches the circle and is `REFUSED`; no TRANSFER, one connection. No REFUSED line = inconclusive | **yes**: `PORTAL 'ascalon_to_corridor' REFUSED: the player is 120 u in` (the specimen's own 120 u), c1 only, no transfer; the W leg then walked back east on 148's mesh (`[clipped]` re-grant, `KBD STOP-ECHO`) |
| A3 | no crash-dialog.txt | **none** |

**Run B — the bound itself, `20260925T095537`.**
`python toolkit/harness/session.py --warn 5 --hold 8 --game-args "--explorable --map 168" --walk "wait:3 W:3"`

| Q | Registered | Result |
|---|---|---|
| B1 | instance load prints `NO-MESH BOUND … (-3072,-3072,3072,3072) [client-default` | **yes**, line 87 |
| B2 | the client logs `Creating default map` (the premise) | **yes**, after `Map '0x05f0b3' failed to load` |
| B3 | EXPOSURE: at least one grant `[no-mesh-rect]` at 3040. None = inconclusive | **yes**: `KBD LEAD RE-GRANT 2 (3040,1536) … [no-mesh-rect]` (moved 464 u, not 520) |
| B4 | nothing past 3040; no `RECT-CLAMPED`; the chain ends `regrant-stop` | **yes**: lead 2056, re-grants 2576 and 3040, then `regrant-stop / no-progress / no-mesh-rect` in the capture; zero `rect_clamp` events |
| B5 | no `MapQueryAltitude() invalid params`; no crash-dialog.txt | **zero** such lines (083808 had 108); no dialog |

The same leg that asserted in 083808 — the lead from (1536, 1536), the silent client, the
re-grant chain — stopped 32 u inside the default map's edge, and the client never logged
a point outside it.
