# Live session key: locating and tapping it in the real client

*Arc opened 2026-08-07. This is the R0b driver's first deliverable: a read-only study of
where the genuine `Gw.exe` forms its ARC4 session key, so a signature-anchored patch can
log it and `toolkit/authsrv/replay.py` can decrypt a live capture offline. Labels per
[studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED / MEASURED /
RECONSTRUCTION / UNVERIFIED / NOT FOUND.*

## The decision this rests on

**Route: patch the real client to log its own key.** Owner's call, 2026-08-07, from the
three candidates the recon surfaced:

| Route | c2s ground truth | Provenance | Cost |
|---|---|---|---|
| **Patch the real client (chosen)** | yes | clean — our own patch | a disassembly study (this doc), then a signature patch; verifiable on loopback before any live run |
| Headless client (Headquarter-style) | **no** — c2s is our own reconstruction | ours, but leans on the protocol shape we are verifying | lower, but the c2s half is fiction |
| DLL reading plaintext in-process | yes | technique from an unlicensed repo; reimplement clean | C, per-build signatures, closest to anti-cheat |

The owner also confirmed **both directions matter** — the capture→row content pipeline and
R1.5's tape need the real client's outbound packets, not a reconstruction — which is what
eliminates the headless route for the parts that count.

Why this route is safe to develop: the whole chain except the final step runs on loopback
against our own server, where we already know the key (`test_replay.py` proves it). The
patch is written and verified against a build we can decrypt independently; only the very
last verification — that ArenaNet's `server_seed` behaves like ours — needs a live run,
and that is R0b's acceptance, not its development.

## What is already true (the decryption half)

`toolkit/authsrv/replay.py` derives the ARC4 key and decrypts a captured `.raw` offline.
MEASURED 2026-08-07: 329 vault captures decrypt to exactly their logged plaintext,
all-or-nothing across 375 keyable captures. It needs, per session, ONE of: the 20-byte
`arc4_key`, the 20-byte `master_secret` (it runs `arc4_hash` itself), or the client's
ephemeral exponent `a` (with the server `B` from the binary it derives the rest). **So the
tap has to surface exactly one 20-byte value.** The engine is done; this study is about
getting that value out of a live client.

## OBSERVED — the crypto surface, named by the client's own asserts

The client compiled its assertion expressions, source paths and line numbers into the
shipping image; `toolkit/clientscan/asserts.py` reads them back. This is how identity is
established here — the client names its own code — not by pattern-guessing.

`P:\Code\Base\Crypt\` holds three named units (build 38797, `221c1377…`):

| Unit | What it is | Relevance |
|---|---|---|
| `CptApi.cpp` | the crypto API layer | the entry points the key exchange calls |
| `CptRc4.cpp` | the RC4/ARC4 stream cipher | **the plaintext↔ciphertext boundary** — network-logger's tap point, and where a per-direction cipher state (256-byte sbox) persists for the whole connection |
| `CptSha.cpp` | the SHA-1 used in key derivation | anchored below; its output feeds `arc4_hash` |

### The SHA-1 anchor

**`SHA1_Init(shsInfo* edi, digest* esi)` at VA `0x0090a02c`** — OBSERVED, disassembled
this session. It writes the five SHA-1 init constants
(`0x67452301 0xEFCDAB89 0x98BADCFE 0x10325476 0xC3D2E1F0`) to `[esi+0 .. esi+0x10]`, so
`esi` is the 20-byte state, and zeroes `[edi]`/`[edi+4]`, an 8-byte length/count in the
context. Those five constants appear **exactly once** in `.text`, which is what makes this
the unique anchor for the whole crypto region. The function's own asserts name the file
`P:\Code\Base\Crypt\CptSha.cpp` and the parameters `shsInfo` and `digest` — the identity
is the client's, not ours.

The round constant `0x5A827999` follows at VA ~`0x0090a147` (file `0x509547`) and appears
~20× across `.text` (many hash-like sites); `0x6ED9EBA1` ~21×. Only the init cluster is
unique, so it is the signature to relocate from.

### The reconciliation question this study must close

Our own `gwcrypto.arc4_hash` — which reproduces **real** captured keys — is a **5-round**
truncation, not full 80-round SHA-1: `A..E =` the init constants, one pass of 5
SHA-1-style rounds, return `w[i]+state[i]`. Yet the client has a full `CptSha.cpp` with the
Init/Update/Final shape. **UNVERIFIED:** whether the ARC4 key is derived by this full
SHA-1 used in some specific way, or by a separate 5-round routine, and if the latter, why
the init constants appear only once. The single-init-site fact points at reuse of one
init; the 5-round reproduction points at a distinct finalizer. Resolving this names the
exact instruction where `master_secret` becomes `arc4_key`. *(Under study — see the open
questions; a disassembly fan-out is running as this is written.)*

## The plan, end to end

1. **Locate the value** (this study): the instruction where `a` / `master_secret` /
   `arc4_key` is fully formed, and where each lives (register / stack / global / the
   persistent RC4 sbox).
2. **Choose the tap value by lifetime.** `a` and `master_secret` are transient; the
   `arc4_key` and the RC4 sbox persist for the connection. A value still resident when an
   external reader polls is worth more than one computed and discarded — UNVERIFIED which
   wins, pending the disassembly.
3. **Add a signature-anchored patch** to `make_custom_client.py`, in the same style as the
   DH / updater / mutex patches: no hardcoded addresses, relocated from a byte signature so
   it survives a rebuild the way `dump_dh_params.py` relocates the DH accessor.
4. **Capture ciphertext passively** — `rawlisten.py` / `tcptable.py` exist.
5. **Decrypt offline** with `replay.py`, already proven.
6. **Stamp `origin: live`** ([toolkit/origin.py](../../toolkit/origin.py)) as the first
   record, so `require_single` refuses to pool it with the 329 OURS captures, and **extend
   `scrub_captures.py`**: a live session makes the session key a genuine secret, and adds
   `a` / `master_secret` / any tap sidecar to the scrub list.

## Provenance

Read-only analysis of the shipped client is permitted (CLAUDE.md carve-out; `capstone`/
`pefile` for exactly this). **Zero ArenaNet bytes are committed:** this doc records VAs,
signatures, struct layouts and behaviour — the same shape as
[studies/handshake/PLAN.md](../handshake/PLAN.md) — never verbatim disassembly to
transcribe. The patch we design overwrites our own copy under `vault/`, never `C:\gw`.

## Open questions (being resolved by the running disassembly fan-out)

- Is the ARC4 key derived by the full `CptSha` SHA-1 or a distinct 5-round routine, and at
  which instruction is the 20-byte key fully formed?
- Where does the client generate `a` (which RNG), and is it a strong CSPRNG or something
  weaker? (Bears on whether `a` is even the right tap.)
- Which single value — `a`, `master_secret`, `arc4_key`, or the live RC4 sbox — is the
  cleanest and most persistent tap for an external `ReadProcessMemory` reader vs. a
  patch-to-global?
- Does `cage.assert_launch_safe` pass the actual launch this route makes (real stock client
  aimed straight at the live service, key logged locally), or does any relay reintroduce
  the stock→loopback refusal? What, if anything, must the gate learn — without weakening
  the four cells?
- Should the behavioural rule (human cadence, one client, never competitive) get any code,
  or stay operator discipline?
