# studies/handshake — R1: getting the client to talk to us

**Status:** static analysis done; live probe NOT YET RUN (blocked — see §5).
**Client under study:** build `2026-04-30_b174de1f2d8d`, vaulted at
`vault/client/2026-04-30_b174de1f2d8d/` with a verified manifest.

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

## 3. Auth is layered, and `-authsrv` is probably not the first hop

HANDOFF.md §4 treats authentication as one redirectable step. The symbol evidence says otherwise.
`Gw.exe` and `GwLoginClient.dll` name at least three distinct server roles:

**Portal / NCSoft platform login** — lives in `GwLoginClient.dll`, and it is an SRP-based NCSoft
platform stack, not the classic 2005 Guild Wars login. Symbols include `AUISrpServer`,
`AUISrp2Server`, `AVCSrpServer`, `AVCSrp2Server`, `Gw1ServerChallenge`, `StsServer`,
`AUIStsServer`, `Cli2Auth`, `Auth2f`, `Secure2fAuth`, `SecondaryAuthToken`,
`AuthenticationTokens`, `PortalGrantAuthz`, `PortalDenyAuthz`, `PortalLoginSecondaryAuth`,
`WaitForSsoAuthz`, `RequestAuthz`, `LongTermSession`, `RequireNoWebSession`. SRP means a
challenge-response password protocol with per-account verifiers; "STS" is a security token
service; `Auth2f`/`Secure2fAuth` is two-factor. `Gw.exe` mirrors this with `GcPortal`,
`PortalAuth`, and `GcPortalRequestAccountSiteLink`.

**Guild Wars AuthSrv** — the account-and-metadata service, in `Gw.exe`: `AuthSrv`, `GcAuthCmd`,
and a family of `GcAuthCmdSend*` commands covering account creation by key, CD-key add, password
change, name change, password reset, resend email, timed keys, character rename and paid rename,
friend updates, and the in-game shop (`ShopCheckout`, `ShopEnd`, `ShopGetPromotionBits`,
`ShopValidateReceipt`). The server-to-client side is named too: `RecvAuthSrv_AccessKeyType`,
`RecvAuthSrv_AccountAddCdKeyResult`, `RecvAuthSrv_AccountRightsUpdated`,
`RecvAuthSrv_AccountTimedKeyData`, `RecvAuthSrv_BetaInviteCount`,
`RecvAuthSrv_ShopCatalogGenResponse`, `RecvAuthSrv_ShopStatusResponse`.

**Game server** — `GcGameCmd`, `GcSrv`, `GcConn`, `FcSrv`, and `DispatchStream`.

The consequence: `-authsrv` most likely redirects only the middle role. If the client first
requires a successful NCSoft portal/SSO authentication that `-authsrv` does not touch, then R1
is not "point it at localhost and implement a documented handshake" — it is either implementing
an SRP server plus a token service, or bypassing the portal layer entirely. `-portaldll` is the
reason to think the bypass may be cheap.

**Confidence: medium.** This is read off symbol names, not off observed behaviour. It is a
hypothesis with good evidence, and §5 is how it gets settled.

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

It binds `127.0.0.1` on ports 80, 443, 6111, 6112, 6113 and 6114, accepts anything that connects,
records every byte received with timings, and never replies. It was executed successfully and
bound all six ports; the client was never launched against it, so **there is no result**.

Output goes to `vault/`, not into the repo. A listener standing in for an auth server receives
whatever the client would have sent the real one, and at this stage we do not know what that
includes — account identifier and credential material are both plausible. Treat every probe run
as sensitive until its contents have been read.

An agent session could not launch `Gw.exe` — the sandbox denied process launch. The client must
be started by hand. Procedure:

1. Start the listener with the command above and leave it running.
2. In another shell:

   ```bash
   C:\gw\Gw.exe -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed
   ```

   **Both flags, not just `-authsrv`.** `-portal` redirects the first hop (the NCSoft STS
   login) and `-authsrv` the second (the Guild Wars auth channel). Redirecting only `-authsrv`
   leaves the client talking to ArenaNet for the portal handshake, and if that stage fails or
   stalls the client may never reach the stage we are watching — producing a silent listener
   that means nothing. This is the invocation OpenTyria uses.
3. Let it sit for the full listener duration, then close the client.
4. Read `vault/probes/authsrv-run1/REPORT.md`.

Interpreting the outcome:

| Observation | Reading | Consequence |
|---|---|---|
| A connection arrives on 6112 and the client speaks first | `-authsrv` still redirects, and the client opens the conversation | Best case. R1 proceeds roughly as HANDOFF §4 assumed; start replying to the first message. |
| A connection arrives but the client waits for us to speak | Redirect works, server speaks first | R1 needs the server's opening message before anything else — that becomes the first capture target. |
| A connection arrives on 80/443 instead | Auth moved onto HTTP(S) | Likely the NCSoft portal path; expect TLS and a token service, not a raw game protocol. |
| **No connection at all** | **Inconclusive, not negative** | Could be: portal/SSO gating before `-authsrv` is ever reached; a crash; a Steam gate; a different port; UDP; or hostname resolution ignoring the override. Do not record this as "`-authsrv` is dead" — record it as "did not reach the auth stage," and escalate to the `-portaldll` line of attack. |

The last row is the one that matters. A null result here has at least five explanations and only
one of them is "the flag is gone." Treat a silent listener as a prompt to instrument, not as an
answer.

---

## 6. Open items

- Run the probe (§5). Everything else in this arc is downstream of it.
- Determine whether `-portaldll` accepts an arbitrary path, and what interface a substitute DLL
  would have to satisfy. Establish whether `Gw.exe` statically imports from `GwLoginClient.dll`
  or resolves it at runtime.
- Find out what `-mock` does.
- Compare the 41-entry flag table against the publicly documented command-line argument list.
  The delta is information nobody has written down.
- Confirm whether `DispatchStream` is the message chokepoint (capture arc, not this one).
