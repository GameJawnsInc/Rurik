# studies/handshake — R1: getting the client to talk to us

**Status: R1 ACHIEVED, 2026-08-04.** A real Guild Wars client, build 38797, reached the character
select screen against this server and displayed a character that exists nowhere but in our source
code. HANDOFF.md's R1 acceptance criterion — *"Client reaches character select against your
server"* — is met.

The full path, all of it ours: portal on 6601 → Diffie-Hellman with a client patched to carry our
parameters → ARC4 → computer info → session info → portal account login validated against a token
our own webgate issued → the five-message character burst → the client renders "Test Warrior".
Elapsed from the first byte captured to a character on screen: a few hours.

Two things are worth writing down because they will not be obvious later. The client sat at the
screen sending heartbeats with a rising tick counter, which is what a healthy idle client does —
so the connection was genuinely stable, not merely rendered once. And the EULA dialog that appeared
just before it was *progress*, not a fault: it is client-side UI, and accepting it sent three bytes
to loopback.

See §0 for the wire-level detail; §5b for the runbook.
**Client under study:** build **38797**, read off the wire. Note the client auto-updated mid-session
— see §0.4.

---

## 0. The probe result (2026-08-04)

The owner ran the three-run probe. Both stages connected, the client spoke first on both, and the
bytes match the predicted model exactly. Everything in §3 below moves from hypothesis to fact.

### 0.1 Stage A confirmed: the portal really is plaintext HTTP on 6601

```
GET /Spawned/WebGate/session/create.xml HTTP/1.1
Connection: Keep-Alive
Authorization: Arena 0
User-Agent: Gw/38797.0 (Win32)
Host: 127.0.0.1:6601
```

No TLS — no `0x16` handshake byte, just an HTTP request in the clear. The path is exactly
`/Spawned/WebGate/...` as predicted. `Authorization: Arena 0` is the token slot, still zero because
no session exists yet. **This request body is the specification for our webgate**: answer this one
endpoint and Stage A is done.

The client held the connection open for 32 seconds and closed it when we never replied.

### 0.2 The build number is on the wire, in the clear

`User-Agent: Gw/38797.0 (Win32)`. HANDOFF.md §9 asks for a way to stamp a build id into every
capture manifest and never says how. Here it is, free, in the first request of every session, no
binary parsing required. **Adopt this as the canonical build stamp.**

### 0.3 Stage B confirmed: AuthSrv speaks DH exactly as documented

82 bytes on port 6112, in two writes, and they decode cleanly:

| Offset | Bytes | Meaning |
|---|---|---|
| `0x00` | `00 04` | message header `0x0400` |
| `0x02` | `0c 00` | payload length, 12 |
| `0x04` | `8d 97 00 00` | **38797** — the build number again, as a little-endian dword |
| `0x08` | `01 00 00 00` | 1 |
| `0x0c` | `04 00 00 00` | **4 — the generator `g`**, matching the value read out of `.rdata` |
| `0x10` | `00 42` | message header `0x4200` — the client-seed message |
| `0x12` | 64 bytes | **`A = g^a mod p`**, the client's DH public value |

That is 2 + 64 = 66 bytes for the second message, precisely the shape the public research
predicted. The client opens with a hello carrying its build, then immediately sends its DH public
value. It never receives a reply from our silent listener, so it stalls and reports `Code=058`.

**`Code=058` after a successful connection is the expected, correct outcome of this probe.** It
means "connected, spoke, got nothing back" — not "the flag is dead."

Ordering note worth keeping: the client hit **6112 at t+4.4s and 6601 at t+6.5s** — AuthSrv *before*
the portal. The three stages are not a strict sequential chain; do not assume the portal must
complete before the auth socket opens.

### 0.4 The client auto-updated mid-session, and the DH parameters rotated with it

The Reforged update checker replaced `Gw.exe` while this work was in progress.

| | Pre-update snapshot | Build 38797 |
|---|---|---|
| SHA256 | `b174de1f2d8d…` | `221c13772c7a…` |
| Size | 10,404,032 | 10,483,904 |
| DH struct RVA | `0x6843e8` | `0x6910d8` |
| Prime fingerprint | `bb8f43af990fe21f` | `fccfed6d897593eb` |
| Server public B | `9d8485c9466d66bd` | `dc1b568d13a81438` |

**Both the prime and the server's public key changed, and the struct moved.** ArenaNet rotates the
Diffie-Hellman parameters per build. That is why Headquarter carries 107 server public keys, one
per client build, rather than a single constant.

Three consequences, all of them operational:

1. **The client patch is not a one-time step.** It must be redone after every ArenaNet update, and
   the parameters are build-specific. Budget this permanently.
2. **Every capture, schema revision, and key file must be build-stamped**, and §0.2 gives the stamp
   for free.
3. **The pin-and-snapshot law earned its keep within hours.** HANDOFF.md §9 says the ground truth is
   "a moving target maintained by someone else"; it moved the same day. Re-snapshot before, not
   after, any update prompt.

The accessor signature still matched in the new build, so `toolkit/clientscan/dump_dh_params.py`
found the relocated struct on its own. Keep using it as the post-update check.

---

**Client originally studied:** build `2026-04-30_b174de1f2d8d`, vaulted with a verified manifest.
Superseded by 38797 but retained — two builds is the beginning of the key history this project
needs.

This arc owns one question: *what does it take to get the Guild Wars client to complete a
handshake against something we control?* HANDOFF.md §4 assumed the answer was "nothing —
`-authsrv <ip>` is documented and R1 needs no binary patching." That assumption predates
Reforged. This file records what we have actually established.

---

## 1. The client is still 32-bit — the tooling lineage survives

| Binary | Arch | PE format | PE timestamp (UTC) | Size |
|---|---|---|---|---|
| `Gw.exe` | x86 (`0x14c`) | PE32 | 2026-04-30 22:17:11 | 10,404,032 |
| `GwLoginClient.dll` | x86 (`0x14c`) | PE32 | 2024-09-11 19:38:07 | 2,150,664 |
| `GWToolbox.exe` | x86 (`0x14c`) | PE32 | 2025-06-10 06:46:20 | 3,720,192 |

This was the single largest architectural risk to the whole plan and it has resolved in our
favour. Reforged did **not** rebuild the client as x64. Every existing 32-bit in-process tool —
GWCA, GWToolbox++, and the entire injection lineage the capture harness depends on — remains
architecturally viable. Had this gone the other way, HANDOFF.md §3's "build it as a
GWToolbox-lineage module" would have been dead and R0 would have started from nothing.

The `Gw.exe` PE timestamp is post-Reforged, so this is a current client, not a stale copy.

---

## 2. `-authsrv` exists in the current client

It is present in `Gw.exe` as a **UTF-16LE** string at file offset `0x005371cc`. A plain ASCII
`grep` reports zero hits and will mislead you — every flag name in this client is stored wide.

More usefully, the flag names sit in one contiguous, alphabetically sorted run from `0x005371cc`
to roughly `0x00537438`, which is the standard layout for a binary-search argument lookup table.
`authsrv` is the first entry. The full table, in file order:

```
authsrv    autologin  bmp        character  diag       dsound     email
exit       fps        fqdn       lodfull    image      log        map
mce        mock       mute       nofqdn     nopatchui  noshaders  nosound
noui       oldfov     fmod       password   perf       port       portal
portaldll  prefresetlocal        repair     resetmap   sndasio    sndfastbuf
sndwinmm   sai        stress     uisizenormal          uninstall  update
windowed
```

41 entries. Presence in the table is strong evidence the flag is still *parsed*; it is **not**
evidence that it still *works end to end*. That distinction is the whole point of §5.

Several of these are interesting beyond `-authsrv`:

- **`portaldll`** — the client appears to load a login/portal DLL by name. `Gw.exe` also carries
  the format strings `%s\%s*.dll`, `Dll %s load fail err=%u`, and `Dll %s retrying in temp`,
  which reads like dynamic `LoadLibrary` of a DLL matched by pattern rather than a static import.
  If this flag accepts an arbitrary path, substituting our own portal DLL may be dramatically
  cheaper than implementing the real auth protocol. **This is the most valuable lead in this file.**
- **`mock`** — unexplained. A developer mock mode would be extraordinarily valuable.
- **`port`** — a port override distinct from `authsrv`, so the endpoint is likely `<host>` + `<port>`.
- **`map`, `resetmap`, `autologin`, `noui`, `stress`, `fqdn`/`nofqdn`** — all plausibly relevant to
  driving a client at scale for the capture campaign (see the capture arc).

---

## 3. Auth is layered, and `-authsrv` reaches only the middle stage

```
Stage A  PORTAL    Gw.exe's own GcPortal --HTTP(S)+XML-->  account.arena.net    <- -portal, -email, -password
                   returns a user id, a session, and a game token
Stage B  AUTHSRV   GcConn "auth"  --DH + ARC4-->  Auth1.ArenaNetworks.com:6112  <- -authsrv, -character
                   the portal's token is carried in; returns game server info
Stage C  GAMESRV   GcConn "game"  --DH + ARC4-->  address handed over by Stage B  <- no flag
```

Three consequences, each of which corrects something.

**`-portal <addr>` turns Stage A into plain HTTP.** When the flag is set the client switches to
port **6601**, prefixes every request path with `/Spawned/WebGate`, and *sets its TLS flag to
zero*. Unset, it is HTTPS with certificate validation. So a local Stage A needs no TLS, no
certificate, and no SRP — just an HTTP server on 6601 answering a handful of XML endpoints. This
is why OpenTyria's `webgate.py` is a couple of hundred lines of plain `HTTPServer`. It is the
cheapest single opening in the entire R1 problem.

**R1 is not patch-free, and HANDOFF.md §4 needs amending.** `Gw.exe`'s `.rdata` carries a pinned
136-byte crypto blob: two header words plus two 64-byte high-entropy values, being the
Diffie-Hellman modulus and **the server's public key**. Because the server's public key is baked
into the client, no server we control can key Stage B without patching that blob. OpenTyria's
`tools/patch-gw.py` does exactly this, and the byte pattern it keys on still matches this
2026-04-30 build. The patch is small and the tooling exists — but R1 acquires a patched-client
build step, and the patched binary is a derived ArenaNet artifact that must stay out of the repo
and in the vault.

**Steam is a storefront, not an auth path.** Every Steam symbol in the client sits in shop and
checkout code (`GcTransShopInit`, `ShopValidateReceipt`), and `steam_api.dll` is delay-loaded
through the same generic helper as OpenAL. Login is Portal → AuthSrv regardless of distribution.

### Correction: `GwLoginClient.dll` is not on the client's login path

An earlier revision of this file identified `GwLoginClient.dll` as the client's auth stack. That
was wrong, and the error is worth recording because the evidence looked strong.

The DLL is real and it is what it appeared to be — NCSoft's SRP/STS/SSO stack, internally named
`PortalClient.dll`, exporting 23 `Portal*` functions (`PortalLogin`, `PortalLoginGw1Hash`,
`PortalRequestGameToken`, `PortalLoginSecondaryAuth`, and so on). But **`Gw.exe` never calls it**:
the DLL's filename, its internal name, and all 23 export names are absent from `Gw.exe` in both
ASCII and UTF-16, and it is neither a static nor a delay import. `Gw.exe` carries its own,
separate portal client that speaks HTTP and XML over WinHTTP. The SRP stack belongs to
*third-party launchers* — `GW_Launcher.exe` in `C:\gw` is gwdevhub's launcher, which uses the DLL
to log in on the user's behalf and knows nothing about the game protocol.

The lesson generalises: co-location in an install directory is not evidence of a call graph.
String and symbol mining tells you what a binary *contains*, never what it *uses*. Confirm the
import table or the call site before believing a dependency.

### Also dead: `-portaldll`

The flag is parsed and stored but never read. The argument table is a 41-record structure of
`{u32 flags, wchar_t* name, u32 id}` where `flags & 0xff00` selects the type — `0x000` boolean,
`0x300` string, `0x400` integer. `-portaldll` is id `0x36`, class `0x300`, so it genuinely takes
a path-sized string; but none of the 17 string-accessor call sites passes `0x36`, and its buffer
is referenced nowhere in the image. `-map`, `-port` and `-sai` are dead by the same test.

The `%s\%s*.dll` format string that suggested a pluggable loader was a red herring: the glob
prefix is the literal `GwA`, and the routine is a generic copy-to-`%TEMP%`-and-retry DLL loader
whose callers are OpenAL, `steam_api` and GLES. **`-portal` replaced `-portaldll` as the cheap
path**, and it is a better one.

### Undocumented-flag delta

Against the publicly documented command-line list, this build's 41-entry table differs in three
ways. Absent from the wiki entirely: `-portal`, `-portaldll`, `-nofqdn`, `-fmod`, `-sai`,
`-uisizenormal`. Listed publicly but marked "no known use": `-authsrv`, `-exit`, `-map`, `-port`,
`-sndfastbuf`. Documented but gone from this build: `-dx8`, `-newauth`, `-oldauth`,
`-windowedfullscreen`. Two behaviours read directly from the binary: `-fmod` suppresses OpenAL
loading (it is an audio backend selector), and FQDN is **on** by default with `-nofqdn` as the
opt-out, which is the inverse of how the wiki frames it.

### The Stage B command surface, from the client's own symbols

`Gw.exe` names its own protocol commands, which is a large free head start on the AuthSrv message
catalog. `GcAuthCmd` plus a family of `GcAuthCmdSend*` covering account creation by key, CD-key
add, password change, name change, password reset, resend email, timed keys, character rename and
paid rename, friend updates, and the in-game shop (`ShopCheckout`, `ShopEnd`,
`ShopGetPromotionBits`, `ShopValidateReceipt`). The server-to-client direction is named too:
`RecvAuthSrv_AccessKeyType`, `RecvAuthSrv_AccountAddCdKeyResult`,
`RecvAuthSrv_AccountRightsUpdated`, `RecvAuthSrv_AccountTimedKeyData`,
`RecvAuthSrv_BetaInviteCount`, `RecvAuthSrv_ShopCatalogGenResponse`,
`RecvAuthSrv_ShopStatusResponse`. Stage C is named by `GcGameCmd`, `GcSrv`, `GcConn`, `FcSrv`,
and `DispatchStream`.

Almost all of the above is account and commerce plumbing that a local server can stub or refuse.
The minimum viable Stage B is much smaller than the command list suggests: accept the portal's
token, answer with game server info, and get out of the way.

**Incidental:** `Gw.exe` references `libEGL.dll` and `libGLESv2.dll` — ANGLE. The Reforged
renderer appears to go through an OpenGL ES translation layer. Not on the R1 path, but it
matters later for anything that hooks rendering, and it is a concrete "what Reforged changed."

---

## 4. `DispatchStream` — a hook-point lead for the capture harness

`Gw.exe` contains the symbol `DispatchStream` alongside `structCmdStartBytes`,
`GetUniqueStreamId`, `uniqueStreamId`, and `nextStream`. If `DispatchStream` is the central
message dispatch, it is exactly the chokepoint HANDOFF.md §3 wants the harness to hook — one
place that sees every incoming message, including ones no reverse engineer has named yet. That
is what makes "record raw, parse later" actually work rather than silently dropping unknown
message types. Hand this to the capture arc; do not chase it here.

---

## 5. The go/no-go probe — NOT YET RUN

**This is the open item. Nothing below has been observed. Do not treat §3 as settled until it is.**

The probe harness exists and is ready:

```bash
python studies/handshake/authsrv_probe.py --outdir vault/probes/authsrv-run1 --duration 100
```

It binds `127.0.0.1` on 6601, 6112, 6600, 6113, 80, 443, 6111 and 6114, accepts anything that
connects, records every byte received with timings, and never replies. It has been executed
successfully and bound every port; the client was never launched against it, so **there is no
result**. An agent session could not launch `Gw.exe` — the sandbox denied process launch — so
this needs a human.

Output goes to `vault/`, not into the repo, and **runs A and B below send real credentials to a
socket that logs them**. `-email` and `-password` on the command line are transmitted to whatever
answers. Scrub those runs before the capture goes anywhere, and never commit one.

Run three variants, in this order. Each answers a different question, and run C is the decisive one.

**Run A — is the portal really plain HTTP on 6601?**

```bash
C:\gw\Gw.exe -portal 127.0.0.1 -email <you> -password <pw> -log -windowed
```

Watch for a plaintext HTTP request on **6601** with a path beginning `/Spawned/WebGate`. If it
arrives, Stage A is solved cheaply and *that request body is the specification for our webgate*.
If instead the first bytes look like TLS — a leading `0x16` — then the read in §3 is wrong and
the downgrade does not happen.

**Run B — does the client proceed to Stage B?**

```bash
C:\gw\Gw.exe -portal 127.0.0.1 -authsrv 127.0.0.1 -email <you> -password <pw> -log -windowed
```

Expect a stall, because the probe never replies to the portal. The datum is simply whether a
connection is attempted, and where.

**Run C — does `-authsrv` still work at all?** (no credentials needed on the command line)

```bash
C:\gw\Gw.exe -authsrv 127.0.0.1 -windowed
```

Stage A goes to the real service and succeeds normally, so a connection landing on **6112**
proves both that `-authsrv` still redirects *and* that Stage B is reached only after a successful
portal login. If the client's log says `AuthSrv invalid`, retry with `host:port` syntax. Silence
here, with a successful real login, is the one outcome that genuinely suggests `-authsrv` is dead.

Interpreting the outcome:

| Observation | Reading | Consequence |
|---|---|---|
| Run A: plaintext HTTP on 6601 under `/Spawned/WebGate` | The portal downgrade is real | Best case. Build the webgate against the captured request. Stage A costs days, not months. |
| Run A: TLS bytes (leading `0x16`) on 6601 | No downgrade; portal wants TLS | Stage A needs a certificate the client will accept, or the TLS-SRP path. Much more expensive — re-plan. |
| Run C: connection on 6112 | `-authsrv` lives, and Stage B is gated behind Stage A | Confirms the three-stage model. Proceed with portal-first sequencing. |
| Run C: nothing, but the game logs in normally | `-authsrv` is parsed and ignored | R1 changes shape: redirect by other means (hosts file, patched endpoint strings). |
| **Nothing anywhere, in any run** | **Inconclusive, not negative** | A crash, a launcher gate, a moved port, UDP, or resolution ignoring the override all produce silence. Record it as "did not reach the stage," never as "the flag is dead," and instrument the client's own `-log` output before concluding anything. |

That last row is the one that matters. A null result has several explanations and only one of
them is "the flag is gone." Treat a silent listener as a prompt to instrument, not as an answer.

---

## 5b. Run it — the current state of R1

Both stages are implemented and self-tested. Neither test needs the game, so run
them first; if either is red, the game will only tell you "Connecting…" and then
`Code=058`, which is a much worse error message.

```bash
python toolkit/portal/test_webgate.py
python toolkit/authsrv/test_handshake.py
```

The handshake test is the interesting one. Its client side reads `(g, p, B)` **out of the patched
executable** rather than from our key file, so a wrong patch offset, a flipped endianness, or a
subtly wrong `arc4_hash` all show up as mismatched keys rather than as a mystery later. It carries
a negative control too: an unpatched client must derive a *different* key, and does.

To drive the real client, three terminals:

```bash
python toolkit/portal/webgate.py
```

```bash
python toolkit/authsrv/authsrv.py
```

```bash
C:\gd\Rurik\vault\client-patched\Gw.custom.<build>.exe -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed
```

**It must be the patched copy.** A stock client keys against ArenaNet's compiled-in public value,
so the handshake completes and every byte after it is undecryptable. `toolkit/clientpatch/
make_custom_client.py` builds the copy and refuses to write anywhere under `C:\gw`.

What to expect right now: the portal answers, the client logs in, AuthSrv completes the key
exchange, and then the client asks something we do not yet answer and eventually gives up. That is
the current edge. The win is that its questions are now written to
`vault/captures/authsrv/*.jsonl` **in plaintext** — which is the prerequisite for answering them,
and the first plaintext CtoS this project has ever had.

Re-run `toolkit/clientpatch/make_custom_client.py` after every ArenaNet update. The parameters
rotate per build (§0.4), so a patched copy from last week keys to nothing.

---

## 6. Open items

- Run the three probes (§5). Everything else in this arc is downstream of them.
- Read `ldufr/OpenTyria`'s `tools/webgate.py` and treat it as the reference Stage A. Confirm its
  `tools/patch-gw.py` byte pattern still matches our pinned build before relying on it.
- Find out what `-mock` does. It is the last unexplained flag with real upside.
- Establish whether `DispatchStream` is the message chokepoint (capture arc, not this one).

Closed since the first revision: `-portaldll` is dead code; `GwLoginClient.dll` is not on the
client's login path; the flag-table delta against public documentation is recorded in §3.
- Confirm whether `DispatchStream` is the message chokepoint (capture arc, not this one).
