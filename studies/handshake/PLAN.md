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
- ~~**`mock`** — unexplained. A developer mock mode would be extraordinarily valuable.~~
  **Closed: it is a mock *graphics device*.** Three strings in the image contain "mock" —
  `mockDevice`, the flag itself, and `MockDevice` among a run of window names — and the one assert
  site is `MainCli:176 mockDevice`, in `Gw\Main\MainCli.cpp`'s argument handling. No offline mode,
  no mock server. The salvage is real though: a null render device is what you want for running
  many clients at once during capture. See
  [studies/srvtree/FINDINGS.md](../srvtree/FINDINGS.md) §7.
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
- Establish whether `DispatchStream` is the message chokepoint (capture arc, not this one).

Closed since the first revision: `-portaldll` is dead code; `GwLoginClient.dll` is not on the
client's login path; the flag-table delta against public documentation is recorded in §3; and
**`-mock` is a mock graphics device, not a mock server** (§3, and
[studies/srvtree/FINDINGS.md](../srvtree/FINDINGS.md) §7) — which retires the last unexplained flag
in the table and leaves the argument list with no remaining leads on it.
- Confirm whether `DispatchStream` is the message chokepoint (capture arc, not this one).

---

## §7. The client's own message tables (build 38797) — [measured 2026-08-05]

Dumped by static analysis of `vault/run/2026-07-29_221c13772c7a/Gw.exe` (ImageBase
0x400000) and independently re-verified byte-for-byte. This is the packet-template
table PLAN.md §8 asked for, for the auth direction.

The auth `MsgChannel` is registered at **VA 0x00492570**:

    push 0x20; push 0xBEC540; push 0x2E; push 0xBEC3D0; push 0; push 3; call 0x7DE010

| | |
|---|---|
| send table | **VA 0xBEC3D0**, 46 entries × 8 bytes — `{const u32 *cmds, u32 count}` |
| recv table | **VA 0xBEC540**, 32 entries × 12 bytes — `{const u32 *cmds, u32 count, handler}` |

They are contiguous: `0xBEC3D0 + 46*8 = 0xBEC540`, and `0xBEC540 + 32*12 = 0xBEC6C0`.

**The message id is `cmds[0]`, not the array index.** Ids run out of order in both
tables, so anything that indexes them positionally is silently wrong.

Field tags are `(byte_count << 8) | type_code`:

| code | meaning |
|---|---|
| `0x04` | scalar |
| `0x05` | fixed blob |
| `0x17` | UTF-16 string |
| `0x0B` | length-prefixed array |

### AUTH_SMSG_GAME_SERVER_INFO (0x0009) is confirmed byte-exact

Recv record 16 at VA 0xBEC600 = `{cmds 0xBF91EC, 0, handler 0x00493E00}`. The
template at VA 0xBF91EC is `[9, 0x404, 0x404, 0x404, 0x1805, 0x404]` — five fields,
`2+4+4+4+24+4 = 42` bytes, matching `declared_unpack_size` in `schema/messages.json`
and matching what `authsrv.py` sends. **The 42 bytes we emit are provably right.**

### What gates the client acting on it

`0x00493E00` is a trampoline into **`0x0048D6D0`**, the sole consumer. There is no
state enum — the real precondition is a live GcApi transaction:

1. walk the intrusive list at head `[0xC0312C]`, link offset `[0xC03124]`;
2. find the node whose `+0x20` equals the message's `req_id`;
3. require `word [node+0x0C] == 0x0F` (the transaction type).

**Both failures return silently** — no log, no assert, no event (`0x0048D703`,
`0x0048D74F`). On success it stores `host[24]` at `trans+0x5C`, `world_id` at
`+0x28`, `map_id` at `+0x2C`, `player_id` at `+0x74`, and sets `trans+0x14 = 1`.

`trans+0x20` is assigned in the `GcTransBase` ctor at `0x0048C065` from the global
counter `[0xC034D0]` (pre-increment, skipping zero), and the send path at
`0x004909D0` puts that same field on the wire as the first dword. **So the wire
`req_id` IS the transaction id, and echoing it back is correct.**

The type-0x0F transaction is built at `0x0048ED20`, called only from
`0x0085105E` / `0x00851122` / `0x008511D8` in `P:\Code\Gw\Mission\Cli\MsCliGame.cpp`.

### Why this mattered less than expected

This was commissioned to explain why the client "never dialled" our game server. It
proved our message was correct, which relocated the fault — and the wire then
showed the real cause: **the client dials port 80, not the port in the handoff.**
The static work still stands on its own; it is the arbiter table for the auth
channel, and it says the encoding is right.

---

## §8. Why the client dials port 80 — [measured 2026-08-05]

The client never dialled the port we put in `AUTH_SMSG_GAME_SERVER_INFO`. The
numbers `6113` and `6120` appeared only in its **error dialog text**, which is
formatted from our field; the one time a 20 ms sampler watched the actual moment,
it dialled **`127.0.0.1:80`** — the `-portal` address on the default HTTP port.

Reading an error dialog as evidence of a connection attempt cost several hours.
The dialog proved only that the client had *parsed* our bytes.

**The host field encoding is not the cause.** Tested both readings of the 24-byte
field:

| encoding | result |
|---|---|
| `sockaddr` (family LE, port BE, 4 addr bytes) — what both references do | client dials `127.0.0.1:80` |
| NUL-padded `"host:port"` ASCII string | **client makes no game connection at all** |

The string form is strictly worse, so the sockaddr reading is right. Static
analysis agrees independently: §7 shows the client parses the message against its
own template and stores `host[24]` at `trans+0x5C`, and the template proves our 42
bytes are byte-exact.

**Standing explanation — SUPERSEDED by §10 (2026-08-06):** this section read the
port-80 dial as "the client routes the game connection to the portal address".
The host-separation probes proved the host is the **handoff sockaddr's**, not
the portal's — the two were the same address in every run this section had to
work with — and on the current run exe the port is 6112, first try, every run.
The port-80 landings above were real but belong to an earlier state of the run
exe/stack; see §10 for the three-run discrimination and what remains open about
port 80.

---

## §9. The updater kill switch — verified, not yet applied [2026-08-05]

The firewall cage and the pre-login patcher are in direct conflict: the patcher
needs one outbound check to succeed before it will show the login screen, and a
block denies it forever (§ RUNBOOK, "The patcher stall"). `launch_caged.ps1` works
around it by opening the cage during startup, but connections established inside
that window survive the re-cage for the life of the process — Windows offers no
supported way to tear down an established TCP connection. So the workaround leaks
by construction.

The real fix is to stop the updater running at all, using the client's own
"nothing to do" branch.

**Independently verified against `vault/run/2026-07-29_221c13772c7a/Gw.exe`:**

| fact | status |
|---|---|
| `DnSetEnabled` prologue `558bec8b4d0833c085c90f94c0a3` | unique — exactly 1 hit in .text |
| function VA | `0x00833ec0` (file `0x4332c0`) |
| writes a single BSS global | `0x01087810` |
| `cmp [0x01087810], 0` guard sites | 4 |

The body is:

    mov ecx,[ebp+8]      ; the bool argument
    xor eax,eax
    test ecx,ecx
    sete al              ; eax = 1 when the argument is FALSE
    mov [0x01087810], eax

so the global is a *disabled* flag. Patching the 3 bytes of `sete al` at file
offset **`0x4332ca`** from `0f 94 c0` to `b0 01 90` (`mov al,1` ; `nop`) forces it
set on every call. `DnInit()` then returns immediately and `DnRun()` returns 1 —
"done, nothing to do" — which its caller reads as patching finished.

**Not yet applied.** It belongs in `toolkit/clientpatch/make_custom_client.py`
beside the DH patch, signature-matched rather than offset-hardcoded, since the
address moves per build (`0x0082dab0` in the 2026-04-30 build). Once applied, the
cage never needs to open and `launch_caged.ps1` becomes unnecessary.

---

## §10. Which endpoint the client dials for the game channel [2026-08-06]

§8 left a standing explanation — "the client routes the game connection to the
portal address on port 80" — and flagged it not yet proven. The 2026-08-06 runs
then landed the game channel somewhere else entirely: **127.0.0.1:6112**, the
`-authsrv` port (capture `vault/captures/authsrv/authsrv-20260806T151251-c2.jsonl`,
timeline `vault/captures/harness/20260806T151236/report.json`). This section
separates the candidate readings.

### What the artifacts already settle, before any new run

- **OBSERVED (2026-08-06, 15:12 run):** the handoff advertised `127.0.0.1:6113`
  (sockaddr encoding) and a game-catalog listener was provably up on 6113 — the
  stack proves LISTEN per-pid before the client launches, and
  `harness/20260806T151236/gamesrv.log` shows the banner and **no connection
  ever**. The game channel arrived as a second connection to `127.0.0.1:6112`.
  So the client did not dial the advertised port **even when it answered** —
  "the client gave up on a refused endpoint" is excluded for this run.
- **OBSERVED (2026-08-05 morning runs):** with a game-catalog listener on
  `127.0.0.1:80`, the game channel ESTABLISHED to `127.0.0.1:80` ~26 s in,
  right after Play, while 6112 was also listening (harness reports
  `20260805T013415/015317/091032/092415` + the matching
  `vault/captures/gamesrv/authsrv-20260805T*` game-channel captures). When 80
  answers, 80 wins over 6112.
- Together: the client walks some preference list of endpoints it already
  knows, and the advertised sockaddr is either absent from it or below every
  tier we have seen win. Two readings survive for the 6112 landing:
  **(a)** it reuses the `-authsrv` endpoint; **(b)** it transforms the
  advertised port — and 6113−1 = 6112 **is** the auth port, so yesterday's run
  cannot tell the two apart. The host question is equally open: portal host and
  authsrv host have both always been `127.0.0.1`.

### Probe A — does the advertised port influence the dial at all?

One change against the daily config: `--game-port 6200`, so the handoff
advertises `127.0.0.1:6200` and the gamesrv listens there. Canary listeners
(accept, log, never reply — `studies/handshake/authsrv_probe.py --ports
6199,6201`) sit on the ±1 neighbours, because a SYN met by an instant loopback
RST can fall between two 20 ms samples of the TCP table, and an unwatched
refusal would read as "no dial".

Predictions, stated before the run:

- **(a) endpoint reuse:** game channel lands on `127.0.0.1:6112` again; the
  6200 listener and both canaries stay silent; the run passes to the spawn rung.
  *This is the expected outcome.*
- **(b) port−1 transform:** the 6199 canary receives a connection opening with
  the game version header; the run stalls at "game channel keyed".
- **sockaddr honoured:** the game channel lands on 6200 — which would mean
  yesterday's 6113 was refused for some other reason, and §8 needs rereading.

### Probe B — which configured HOST does the 6112 dial follow?

One change against the daily config: `--auth-host 127.0.0.2` (authsrv binds
there; the client is launched with `-authsrv 127.0.0.2`), while `-portal` stays
`127.0.0.1` and the handoff still says `127.0.0.1`. Whatever host the game dial
aims at names its source.

Predictions, stated before the run:

- **authsrv-host reuse:** game channel arrives at `127.0.0.2:6112`; run passes.
  *This is the expected outcome, jointly with (a) above: the client reuses the
  whole `-authsrv` endpoint.*
- **portal-host at 6112:** the dial goes to `127.0.0.1:6112`, where nothing now
  listens; the run fails at "client opened its game channel". Follow-up: canary
  on `127.0.0.1:6112` to turn the refusal into a recorded connection.
- **handoff-host:** indistinguishable from portal-host here (both `127.0.0.1`);
  separated only if the previous bullet fires, by a third run advertising
  `127.0.0.3`.

### Probe A result — OBSERVED 2026-08-06, run `harness/20260806T153830`

The handoff advertised `127.0.0.1:6200` (recorded in
`captures/authsrv/authsrv-20260806T153830-c1.jsonl`); a game-catalog listener
owned 6200, canaries owned 6199 and 6201. The game channel arrived on
`127.0.0.1:6112` 1.5 s after Play and the run passed to the spawn rung. The
6200 listener logged **no connection ever**; the canary summary
(`vault/probes/handoff-A-20260806/summary.json`) shows **zero connections** over
its 300 s. **The advertised port does not influence the dial. The port-transform
reading (b) is dead** — 6113→6112 was the auth port's doing, not arithmetic.

Bonus, and load-bearing for what "ignores" means: the game version header on
6112 echoed the handoff's `world_id` 743702691 and `player_id` 1971349722. The
client **parsed GAME_SERVER_INFO and used its ids while discarding its
address** — the message is read, the sockaddr is not acted on.

### Probe B result — OBSERVED 2026-08-06, run `harness/20260806T153938`

Auth on `127.0.0.2:6112` worked end to end — keyed, logged in, requested the
game instance — so the client honours `-authsrv` for the auth channel. Then the
game dial went to **`127.0.0.1:6112`**, where nothing listened: the sampler
caught `SYN_SENT 127.0.0.1:6112` at t+15.6, 17.6 and 19.6 s (a fresh attempt
every ~2 s), `Gw.log` ends with repeated `Error: Retrying game server
connection`, and `127.0.0.2` never received a second connection. The run failed
at "client opened its game channel", as this outcome predicted.
**Authsrv-endpoint reuse (a) is dead.** The client walked AWAY from the host it
was launched against and dialled a `127.0.0.1`-flavoured host at hardcoded
port 6112.

Also settled by the two runs together: `6112` is not "the port auth actually
used" in any per-connection sense — auth USED `.2:6112` in probe B and the game
dial still went to `.1:6112`. The port is a constant; only the HOST question
remains, and in probe B portal host and handoff host were both `127.0.0.1`, so
they are still confounded.

### Probe C — which 127-host is the game dial's: the handoff's or the portal's?

One change against probe B: the handoff advertises **`127.0.0.3`** (authsrv
`--game-host 127.0.0.3`), with `-authsrv 127.0.0.2` and `-portal 127.0.0.1`
unchanged. Three hosts, three meanings. Game-catalog listeners sit on BOTH
candidates — `127.0.0.3:6112` and `127.0.0.1:6112` — so the landing is a
recorded connection either way, not another invisible refusal. (session.py's
preflight is host-blind on ports, so this run uses the stack by hand +
`drive_client --authsrv 127.0.0.2`.)

Predictions, stated before the run:

- **handoff-host rule:** game lands on `127.0.0.3:6112`. *Expected*, because it
  is the only reading under which retail could work at all — a real game server
  handoff must carry a host the client actually uses, and probe A showed the
  message IS parsed (the ids come out of it).
- **portal-host rule:** game lands on `127.0.0.1:6112`. If this fires it is
  ambiguous with a third reading — a cached/default host — since the portal has
  always been `127.0.0.1` in every run this client has ever made.
- **neither:** the retry loop aims somewhere else again; sampler + `Gw.log`
  record it.

### Probe C result — OBSERVED 2026-08-06, run `harness/20260806T154607`

The game channel **ESTABLISHED to `127.0.0.3:6112`** 0.2 s after Play, keyed
ARC4, and ran a full game session — 669 decoded events including the 0x0088
spawn rung (`captures/gamesrv/authsrv-20260806T154623-c1.jsonl`). The
portal-host listener on `127.0.0.1:6112` recorded **no connection ever**, and
the sampler shows exactly two dials: auth to `.2`, game to `.3`. The
handoff-host prediction fired; the portal-host and cached-host readings are
dead.

### The rule, and what it supersedes

**OBSERVED, three runs, 2026-08-06, build 38797:** for the game channel the
client dials **`<GAME_SERVER_INFO sockaddr host> : 6112`**, first try, within
~2 s of Play. The sockaddr's HOST field is honoured; its PORT field is
decorative; `world_id`/`player_id` from the same message are echoed back on the
game channel's version header. When `host:6112` refuses, the client retries the
same endpoint every ~2 s (`Error: Retrying game server connection`) — probe B
watched 45 s of that and it never fell back to any other endpoint, including
port 80.

This kills §8's standing explanation ("the client routes the game connection to
the portal address on port 80"): the portal host and the handoff host were the
same address in every §8-era run, and the port-80 landings of 2026-08-05
(handoffs advertising 6120, game served and accepted on `127.0.0.1:80` —
`captures/gamesrv/authsrv-20260805T*`) were produced by an earlier state of the
run exe/stack that no current run reproduces. Between those runs and 2026-08-06
the run copy was re-patched (§9's updater kill switch applied), the webgate's
XML answers changed, and every run since dials `host:6112` — which of those
changes moved the port is NOT FOUND, recorded here so nobody chases port 80
again on today's binary. UNVERIFIED and untested: whether the current exe would
try port 80 under some failure mode probe B's 45 s did not reach.

**Consequence for the stack:** the game catalog must be served on **port 6112
at a host of its own**, and that host goes in the handoff. The daily
three-server stack "works" today only because the handoff says `127.0.0.1`, so
the game dial lands on the AUTH listener, whose catalog self-selection then
serves the game — the gamesrv instance on 6113 has never received a connection.
Moving the default stack to advertise a dedicated loopback alias (e.g.
`--game-host 127.0.0.3` + gamesrv bound `127.0.0.3:6112`) would land the game
channel on the actual game server and un-mix the capture directories.

**Done 2026-08-06:** the harness default is now exactly that — handoff
advertises `127.0.0.3`, gamesrv binds `127.0.0.3:6112`, preflight went
host-aware so the two 6112 listeners coexist, and the map checkpoints watch
only `captures/gamesrv`. OBSERVED on the first run (`harness/20260806T155742`):
game channel SYN → ESTABLISHED `127.0.0.3:6112` 1.4 s after the Play click,
version header echoing the handoff's `world_id`/`player_id`, full pass to the
spawn rung, game capture in `captures/gamesrv/authsrv-20260806T155758-c1.jsonl`
with the auth capture clean of game traffic.
