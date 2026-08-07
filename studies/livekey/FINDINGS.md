# Live session key: locating and tapping it in the real client

*Arc opened 2026-08-07. This is the R0b driver's first deliverable: a read-only study of
where the genuine `Gw.exe` forms its ARC4 session key, so a signature-anchored patch can
log it and `toolkit/authsrv/replay.py` can decrypt a live capture offline. Labels per
[studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED / MEASURED /
RECONSTRUCTION / UNVERIFIED / NOT FOUND.*

## The decision this rests on

**Route: patch the real client to log its own key.** Owner's call, 2026-08-07, over a
headless client (whose client→server bytes would be our reconstruction, not ArenaNet's) or
a DLL reading plaintext (unlicensed technique, C, per-build). The owner also confirmed
**both directions of ground truth matter**, which is what eliminates the headless route.

The decryption half is already built and proven: `toolkit/authsrv/replay.py` decrypts a
captured `.raw` from ONE 20-byte value — `arc4_key`, or the `master_secret` it derives from
(it runs `arc4_hash` itself), or the client's exponent `a`. MEASURED 2026-08-07: 329 vault
captures decrypt to exactly their logged plaintext. **So this study's job is to find where
one such value is formed in the live client, and how to get it out.**

## Correction: the anchor this study opened with was the wrong function

The first pass anchored the key derivation at the SHA-1 `Init` at VA `0x0090a02c`
(`CptSha.cpp`), by its five init constants appearing once in `.text`. A disassembly
fan-out then showed that is a **full, standard 80-round SHA-1** — `SHA1_Transform` at
`0x0090a103` carries all four round constants (`0x5A827999 0x6ED9EBA1 0x8F1BBCDC
0xCA62C1D6`) 20× each — reached through a general crypto-API dispatcher (`CptApi.cpp`'s
`algorithm` switch). Our `arc4_hash`, which reproduces real keys, is **5 rounds**. They are
distinct routines; the session key does **not** go through `CptSha.cpp`. Recorded rather
than quietly overwritten, because verbatim-first is exactly what caught it: the constants
were real, the identification was wrong, and disassembling the function refuted it. **[the
80-round finding: MEASURED; the "wrong anchor" conclusion: OBSERVED]**

## OBSERVED — the real key-derivation site

Two independent readers converged on it from different directions (one tracing the DH
accessor forward, one tracing the RC4 state backward), and it is **independently
re-verified this session** by disassembling the two functions directly:

**`0x007DE690` — the arc4_hash + RC4 key schedule, in `MsgUtil.cpp`.** Its own assert names
`P:\Code\Net\Msg\MsgUtil.cpp`, expression `"init"`, and its prologue checks the input
length `arg1 (esi) <= 0x14` — a 20-byte input. It runs the 5-round pseudo-SHA-1 in place
(matching `gwcrypto.arc4_hash`, arc4_key complete at `0x007DE787`) and immediately keys an
RC4 state (KSA at `0x007DE78C–0x007DE7F5`). **[OBSERVED — assert string and prologue read
directly]**

**`0x007DC030` — its single caller, in `MsgConn.cpp`.** It gates on the connection object's
stage field `[ebx+0x60] == 1` and an incoming message-type `== 0x16` — i.e. the
`SMSG_SERVER_SEED` (header `0x1601`) arriving in state 1. Immediately before the call it
forms `master_secret = server_seed XOR shared_secret` over 20 bytes (the
`server_seed`/`recover_master_secret` operation `gwcrypto.py` models), complete in a
20-byte stack buffer at `0x007DC0CE`. **[OBSERVED caller + gating; RECONSTRUCTION for the
XOR being server_seed⊕shared specifically, from the surrounding structure]**

After keying, the client **duplicates the 264-byte RC4 state** (2 counters + 256-byte
S-box) `0x108` bytes further into the connection object — one derived key seeding two
independent per-direction ciphers, exactly as `gwcrypto`/`authsrv` model. The states live
at `conn+0x7C` and `conn+0x184`. **[OBSERVED]**

### The two clean tap values

| Value | Where, when formed | Note |
|---|---|---|
| `master_secret` (20 B) | `[ebp-0x18]` in the `0x007DC030` frame, complete at `0x007DC0CE` | `replay.py` runs `arc4_hash` itself — this is the preferred tap |
| `arc4_key` (20 B) | `[ebp-0x18]` in the `0x007DE690` frame, complete at `0x007DE787` | feeds `ARC4(key)` directly |

Either alone yields the full session key without reimplementing DH modexp offline.

### Side finding — the client's exponent `a`

`a` is **128-bit, not 512** (four DWORD globals at `0x00C034EC–0x00C034FB`), filled by
`ole32!CoCreateGuid` (which is why the binary imports no `CryptGenRandom`), zero-filled on
failure. **[OBSERVED]** We do not tap `a` — `master_secret` is downstream and cleaner — but
it is worth recording that the ephemeral secret is GUID-derived and half the width the
protocol's 512-bit field allows; a separate question from this study, flagged not pursued.

## Two facts that reshape the mechanism

**ASLR is on.** The PE sets `IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE` and carries a real
295,424-byte `.reloc`. Every tap address must be computed as `runtime_module_base + RVA`,
resolved from the module list at read time — a fixed `image_base+RVA` will not hold across
launches. **[MEASURED]**

**Passive ciphertext capture is not available, which the earlier plan assumed it was.**
`rawlisten.py` is a loopback `accept()` server — it catches what a client sends to *our*
endpoints, not a connection the client makes outbound to ArenaNet's remote IP.
`tcptable.py` reads per-socket state/PID only, no payload. The repo takes no packet-capture
dependency (Npcap/WinDivert are third-party kernel drivers, excluded by the stdlib-only
rule). **So the live ciphertext, like the key, has to come from in-process
instrumentation.** This is the one open design decision the disassembly surfaced — see
below. **[OBSERVED]**

## The tap design

**Mechanism — duplicate-store to a BSS slot + external `ReadProcessMemory`, not a code
cave.** The four existing patches (DH struct, updater, mutex NOP, mutex rename) are all
same-length in-place edits with no new code and no control-flow diversion, re-verified by
reading the written file. A code-cave trampoline writing to a file would be this toolkit's
first code injection — a hand-assembled `CreateFile`/`WriteFile` with no assembler on hand
(capstone only disassembles), landing its crash risk on the single authorized live client.
Instead: a signature-anchored patch inserts a duplicate store of the 20-byte value to a
fixed RVA we pick in the `.data` slack (**MEASURED: ~5.54 MB of zero-init RW space beyond
what the file backs**, so no new PE section), and a small `toolkit/harness/keytap.py` uses
`OpenProcess(PROCESS_VM_READ)` + `ReadProcessMemory` — resolving the runtime base via the
toolhelp module list because of ASLR — to read it. This keeps the "no new code in the
client" idiom and is verifiable on loopback. **[RECONSTRUCTION — design, not yet built]**

**Value — `master_secret`.** 20 bytes, `replay.py` derives the rest. The persistent RC4
S-box at `conn+0x7C` is a tempting alternative (it is guaranteed addressable), but it is
only byte-replayable-from-frame-0 as the *first* snapshot after KSA and before any PRGA
byte is consumed; a mid-stream snapshot decrypts forward but not backward. Better used as a
cross-check than as the source.

**When the patch lands:** add its VA range to `pinned.PATCHED_TEXT` and
`dhbuild.patch_state()`, the way the existing patches are tracked, so a future study
pinning an address there is warned.

## The gate needs no change

`cage.assert_launch_safe`/`dhbuild.classify` read only the DH-struct bytes, so a key-tap
patch near `MsgUtil.cpp`/`MsgConn.cpp` does not perturb DH classification, and the
`stock→live` cell already passes the real launch this route makes (a stock client aimed
straight at the live service, key logged locally). A relay through a local host is not just
unneeded, it is **structurally unexpressible**: `drive_client.intended_target()` refuses an
argv naming both a loopback and a routable host, and `cage.py`'s `stock→loopback` cell
independently refuses a stock client at `127.x`. The only care needed is confirming the new
patch does not change the binary's DH classification. **[OBSERVED across cage.py/dhbuild.py;
the "no change needed" is the recommendation]**

## Provenance and secrets

Read-only analysis of the shipped client is permitted (CLAUDE.md carve-out; `capstone`/
`pefile` for exactly this). **Zero ArenaNet bytes are committed** — this doc records VAs,
signatures, struct offsets and behaviour, the shape [studies/handshake](../handshake/PLAN.md)
already uses, never verbatim disassembly to transcribe. The patch overwrites our own copy
under `vault/`, never `C:\gw`.

A live capture makes new secrets real: `scrub_captures.py` has no field for `master_secret`
and would silently miss a non-`.jsonl` tap sidecar — so the tap should be written as a
JSONL line inside the existing scrubbed capture file, and `master_secret`/`a` added to the
scrub list. `origin.record()` defaults to `origin=OURS`; the live writer **must** pass
`origin=LIVE` explicitly or the file falls to UNKNOWN by `origin.py`'s no-inference rule.

## The behavioural rule, and how much of it is code

The rule — human cadence, human hours, one client, never in a competitive context — has no
code today, and the multi-instance mutex patch is in direct tension with "one client"
during a live run. Recommendation: encode only the cheap structural parts (a
one-live-instance lock, a session-length ceiling, an explicit start confirmation) and leave
the genuinely behavioural judgments as documented operator discipline — the harness has no
view of in-game state to check them meaningfully, and a control that pretends to is worse
than an honest note.

## What remains, in order

1. **Pin the exact store instruction** at `0x007DC0CE` (or `0x007DE787`) to duplicate, pick
   the BSS RVA, and derive the byte signature — the last static-analysis step before code.
2. **Add the key-tap patch** to `make_custom_client.py` behind its own flag, and
   `keytap.py` (the RPM reader). **Verify on loopback:** our DH-patched client keys against
   our server, we already know that key, `keytap.py` must read the same 20 bytes.
3. **Resolve the in-process ciphertext capture** — the open fork above — since neither
   loopback tools nor a passive sniffer can see the outbound connection.
4. **The driver script**: cage + account + live launch + tap + capture + `replay.py` +
   `origin: live`, plus the scrub extension and whatever behavioural guards are chosen.
5. **The live verification run** — last, human-driven, on the secondary account.
