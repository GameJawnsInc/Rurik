# How to capture a live session: the four options, scored

*2026-08-07. A decision doc, requested before building. The question is narrow and it
arrived from a disassembly finding: **passive ciphertext capture is not available** — the
outbound connection to ArenaNet's remote IP cannot be seen by `rawlisten` (loopback only),
`tcptable` (metadata only), or any packet sniffer the repo is willing to depend on. So the
live traffic must come from somewhere deliberate. This compares the ways and recommends
one. Companion to [FINDINGS.md](FINDINGS.md), which located the key.*

## What every option must produce

R0b's acceptance: a live session, **both directions**, stamped `origin: live`, and
**byte-replayable from disk**. Two data streams are needed — the wire bytes, and (unless we
capture plaintext) the session key. The decryption engine `toolkit/authsrv/replay.py` is
built and proven (329 captures decrypt exactly), and needs exactly one 20-byte value:
`master_secret`, `arc4_key`, or the client exponent `a`.

One property decides a lot: **the key tap is verifiable on loopback, against a value we
already hold.** For any loopback session, we independently derive `master_secret` and
`arc4_key` (MEASURED 2026-08-07 — e.g. session `…215723-c2`: master
`e26e71c9…`, key `12c1e5df…`). So any key-acquisition mechanism can be *proven correct
before a single live packet*, by requiring it to read those exact 20 bytes off a loopback
run. Only the final end-to-end confirmation needs the live service.

## The dividing questions

1. **Ciphertext, or plaintext?** Capturing ciphertext needs the key and uses `replay.py`
   (proven, reusable for R1.5's tape, and a crypto cross-check). Capturing plaintext skips
   the key and the decryption entirely, but taps the client's cleartext directly and
   throws away the cross-check.
2. **In-process, or off-wire?** In-process means patching/hooking the client; off-wire
   means a packet-capture driver. In-process keeps us dependency-free but must solve
   "stream a variable-length capture out of the process." Off-wire adds a third-party
   kernel driver but makes the capture lossless and external.
3. **How much new code in the client?** The existing four patches are same-length in-place
   edits — no new code, no control-flow diversion. Every option is measured against that
   bar: a duplicate-store of 20 bytes stays under it; a hook or a file-writing tap does not.

## The options

### A — Instrument the client, capture ciphertext in-process, decrypt offline

The literal continuation of the chosen route. Key: a signature-anchored **duplicate-store**
of `master_secret` to a BSS slot, read by `keytap.py` via `ReadProcessMemory`. *(Correction,
2026-08-07: adding a store is new code — a small code cave — not the zero-new-code in-place
edit the DH/updater/mutex patches are. Recorded honestly rather than sold as free. The
reader `keytap.py` is built and tested; the store-and-cave is the remaining work.)*
Ciphertext: a second in-process tap at the socket send/recv boundary, duplicating each
buffer out.

The catch is the ciphertext *stream*. A session is many variable-length messages, both
directions, possibly megabytes. Getting that out of the process is where the "no new code"
idiom breaks:
- **A-ring:** a fixed BSS ring buffer the client writes and `keytap.py` drains by polling.
  No injected code, but bounded — a burst that outruns the drain drops bytes. Gaps are
  detectable (the `seq` work) but the capture is then incomplete, and this is the *only*
  recording of the real server.
- **A-file:** patch send/recv to `WriteFile` the bytes to disk. Reliable and unbounded, but
  it is the toolkit's **first code injection** — a hand-assembled call with no assembler on
  hand — landing its crash risk on the one authorized live client.

### B — Tap plaintext at the RC4 boundary (the network-logger approach)

Since we must be in-process anyway, hook `CptRc4.cpp`'s crypt function and read the
plaintext buffer at each call — `src` before an outbound encrypt, `dst` after an inbound
decrypt. One tap, simplest data flow, no key and no decryption.

Costs: it is an **inline hook on a hot function** (control-flow diversion, the most
detectable change), it reads the client's **plaintext** (the sensitive material), it is
the exact technique of an **unlicensed** repo (`gw-preservation/network-logger` — we may
learn the approach but must reimplement clean, and "reimplement clean" of a distinctive
hook is thin ice), and it discards the crypto cross-check `replay.py` gives — the live path
would never exercise the decryption that makes a capture trustworthy. It still has the same
stream-it-out problem as A.

### C — Off-wire ciphertext (packet driver) + key duplicate-store

Capture the raw TCP stream from **outside** the process with a user-space packet-capture
driver (WinDivert or Npcap); acquire the key with the same tiny duplicate-store patch as A.
Decrypt offline with `replay.py`.

This is the **least invasive to the client** of all four — the only change to `Gw.exe` is a
20-byte duplicate-store, no hook, no control-flow diversion, and the hard part (a lossless,
unbounded, variable-length stream) is handled by a tool built for exactly that. Cost: a
**third-party kernel-mode dependency**, which the stdlib-only rule forbids without an
explicit carve-out — though there is precedent (capstone/pefile were carved out for
read-only client analysis 2026-08-06), and this one would be scoped identically: the
live-capture driver only, never the server path, never a bare-machine requirement.

### A-file′ — the dependency-free middle

Worth naming as its own option because it is the sweet spot if dependency-freedom is the
priority: key via duplicate-store (clean), ciphertext via **one** accepted piece of code
injection at send/recv writing to a file. It keeps everything in-process and adds no
dependency, at the cost of the toolkit's first (small, well-scoped) injected call.

## Scored

Higher is better; the two costs (dependency, injection) are called out rather than scored
away.

| | A-ring | A-file | B (plaintext) | C (off-wire) |
|---|---|---|---|---|
| Client invasiveness (less is better) | key store + racy buffer | key store + **injected WriteFile** | **inline hook + reads plaintext** | **key store only** |
| Reliability of the capture | poor (burst loss) | good | good | **best** (lossless, external) |
| Reuses proven `replay.py` end-to-end | yes | yes | **no** (tape-only) | yes |
| Provenance | clean | clean | **leans on unlicensed hook** | needs a scoped driver carve-out |
| Anti-cheat *surface* (less is better) | patch + RPM | patch + injection | **hook on hot fn + plaintext read** | **minimal patch + external + RPM** |
| New dependency | none | none | none | **packet driver** |
| First code injection into the client | no | **yes** | yes (hook) | **no** |
| Loopback-verifiable before live | yes | yes | yes | yes |

*Anti-cheat is scored as* surface *— what is theoretically detectable — not as a
prediction. The account-safety control that actually matters is the behavioural rule
(human cadence, one client, never competitive), per PLAN §6.1; no instrumentation choice
substitutes for it, and none should be sold as "stealthier" in a way that invites relaxing
it.*

## Recommendation: **C**, with A-file′ as the dependency-free fallback

The chosen route was "log the key, decrypt offline" *specifically to avoid invasive
hooking*. Option **C honors that intent better than A does**: A's ciphertext stream drags
back either a lossy race (A-ring) or the very code injection we were avoiding (A-file),
whereas C keeps the client change to a single 20-byte store — provably correct on loopback
— and hands the hard, lossy-if-done-wrong streaming problem to a driver built for it. C is
the least invasive to the binary, the most reliable capture, keeps the proven engine, and
carries the lowest anti-cheat *surface*. Its one real cost is a scoped packet-capture
dependency, and the repo already set the precedent for exactly that kind of carve-out.

**If a kernel-mode dependency is unacceptable** — the repo's "runs on a bare machine" pride
is a legitimate reason — then **A-file′**: the clean key store plus one small, well-scoped
`WriteFile` tap. That accepts the toolkit's first code injection deliberately and in the
open, rather than smuggling it in behind a hook.

**Not recommended: B.** It is the most detectable change, reads plaintext, leans hardest on
an unlicensed technique, and is the only option that throws away the decryption cross-check
that makes a capture trustworthy — for a data-flow simplification we do not need, because
the key tap is already proven.

## Either way, the shared next steps

The key tap is common to C, A, and A-file′, and it is the decision-independent piece worth
building first — fully verifiable on loopback:

1. ✅ **The reader is built.** `toolkit/harness/keytap.py`: `OpenProcess(PROCESS_VM_READ)` +
   `ReadProcessMemory`, resolving the runtime base from the toolhelp module list because
   ASLR is on. `test_keytap.py` proves the RPM machinery (round-trip, base resolution,
   cross-process, clean unmapped-read failure) against processes this machine controls — no
   game client needed. The remaining loopback check, once a tap exists: read the 20 bytes
   off a loopback session and require them to equal the `master_secret` we independently
   derive.
2. **The tap itself** (remaining): pin the store instruction to duplicate (`master_secret`
   at `0x007DC0CE`), pick the BSS RVA in the `.data` slack, cut the small code cave, derive
   the byte signature; add the patch to `make_custom_client.py` behind a flag and register
   its VA in `pinned.PATCHED_TEXT` / `dhbuild.patch_state()`.

Only the ciphertext half differs by option (route C: an off-wire packet-capture backend,
carve-out recorded in CLAUDE.md), and only the final run is live.
