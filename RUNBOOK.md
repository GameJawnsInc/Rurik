# Runbook — driving the real client against Rurik

Everything here is copy-pasteable from `C:\gd\Rurik`. Where a command produces
output worth checking, the expected output is shown.

Current state: the portal and the key exchange work. The client will connect, log
in, key up, then ask something we do not answer yet and give up. **That is the
expected end of the run today** — and the point of doing it is that its questions
land in the vault in plaintext.

---

## Step 0 — one-time, and again after every ArenaNet update

### 0.1 Confirm the crypto scheme is still where we think it is

```bash
python toolkit/clientscan/dump_dh_params.py
```

Expect `generator g : 4`, a 512-bit prime, and a final `GO.` line. This reads
`C:\gw\Gw.exe` and touches nothing.

If it says **NOT FOUND**, stop. The accessor signature changed, which means the
client was recompiled in a way that matters, and no patching tool in this repo or
anyone else's can be trusted until the signature is re-derived. That is a genuine
finding — write it up in `studies/handshake/PLAN.md` rather than working around it.

### 0.2 Snapshot the client *before* you let it update

```bash
python toolkit/snapshot_client.py
```

Exits `0` when every file verified byte-identical, `3` if something was locked
(close Guild Wars and re-run). The manifest records any gap, so an incomplete
snapshot cannot be mistaken for a complete one.

Order matters. The parameters rotate per build, so a snapshot taken after an
update has already lost the build you were working against.

### 0.3 Build a patched client and a directory it can run from

```bash
python toolkit/clientpatch/make_custom_client.py
```

```bash
python toolkit/clientpatch/make_run_dir.py
```

The first generates a fresh Diffie-Hellman triple, writes the private half to
`vault/keys/rurik_dh_<build>.json`, and patches a **copy**. It refuses to write
anywhere under `C:\gw`. It ends with:

```
verify     : parameters read back correctly and B == g^b mod p -> True
```

If that says `False`, the patch is wrong — do not launch the binary, and do not
"just try it." The second assembles `vault/run/<build>/` with `Gw.exe`, `Gw.dat`
and the DLLs, about 4.2 GB, taking a few seconds.

**Keep the key file.** The server needs `server_private` to decrypt. Lose it and
the patched client is a brick; you would have to re-patch and re-run everything.

---

## Step 1 — prove it works before involving the game

```bash
python toolkit/portal/test_webgate.py
```

```bash
python toolkit/authsrv/test_handshake.py
```

Both should end `ALL CHECKS PASSED` / `HANDSHAKE VERIFIED`. Run these first every
time. A red test names the broken thing; the game just says `Connecting…` for
thirty seconds and then `Code=058`, which tells you nothing.

The handshake test reads `(g, p, B)` out of the patched executable rather than
from the key file, so it exercises the real chain — patcher, binary, both sides of
the key derivation. Its last check is a negative control: an unpatched client must
derive a *different* key.

---

## Step 2 — the live run, three terminals

**Terminal 1 — the portal (Stage A):**

```bash
python toolkit/portal/webgate.py
```

**Terminal 2 — the auth server (Stage B):**

```bash
python toolkit/authsrv/authsrv.py
```

**Terminal 3 — the patched client:**

```bash
"C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe" -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed
```

That path is build-specific. After any re-patch, take the exact command printed at
the end of `make_run_dir.py`.

Then log in at the client's own screen. Any account name and password work — the
webgate authenticates nobody by design, because this is a private local server
with one user. That is also why it binds loopback only and refuses to do otherwise.

### What a good run looks like

Terminal 1:

```
  client_build     {'user_agent': 'Gw/38797.0 (Win32)', ...}
  request          {'method': 'GET', 'path': '/Spawned/WebGate/session/create.xml', 'authorization': 'Arena 0', ...}
  login            {'email': '...', 'user_id': '...'}
  token_issued     {'email': '...', 'token': '...'}
```

Terminal 2:

```
[c1] connect from 127.0.0.1:xxxxx
[c1] auth version: build=38797 h0008=1 h000C=4
[c1] key exchange OK — ARC4 key xxxxxxxxxxxxxxxx…
[c1] c2s    NNB  first header 0xNNNN
```

**That last line is the prize.** It is the client speaking to us in plaintext,
past the encryption, and those headers are the messages we have to learn to
answer next. The client will then time out — expected, for now.

---

## Step 3 — what you just collected

| Path | What it holds |
|---|---|
| `vault/captures/portal/portal-*.jsonl` | Every Stage A request and reply, in full |
| `vault/captures/authsrv/authsrv-*.jsonl` | Per-frame metadata plus decrypted hex |
| `vault/captures/authsrv/authsrv-*.raw` | Length-prefixed raw ciphertext frames |

Both the ciphertext and the plaintext are kept: raw because the parser will be
wrong for a while and raw bytes stay re-parseable, plaintext because it is what
makes the capture useful today.

To see what the client actually said:

```bash
python toolkit/authsrv/summarize_capture.py
```

It prints each decrypted client frame with its header and a hex/ASCII preview, and
ends with a histogram of first headers — which is precisely the list of messages we
still owe answers to.

One caveat it states rather than hides: a TCP read is not a message boundary, so a
frame may hold several messages or the tail of one. Until we can size messages
properly — which needs the client's own packet-template table (PLAN.md §1.2) — only
the first header per frame is trustworthy, and that is all it reports. Counting
every `u16` in the buffer would produce confident-looking nonsense.

---

## When it goes wrong

| Symptom | Meaning | Do this |
|---|---|---|
| `Code=058`, nothing in terminal 2 | The client never reached us | Confirm both flags are present and that you launched the **run-dir** copy, not `C:\gw\Gw.exe` |
| Terminal 2 shows connect but `unexpected first header` | Not the auth channel, or a protocol change | Record the header value; it is a real finding |
| `expected 0x4200, got …` | Key exchange never started | Almost always an unpatched client |
| Key exchange OK, then immediate disconnect | We failed to answer something required | Expected today. The plaintext is in the vault — that is the next work item |
| Client won't start / repairs itself | Run dir incomplete | Re-run `make_run_dir.py` |
| Anything at all after an ArenaNet update | Parameters rotated | Redo step 0 in full |

**Do not point a patched client at the real service.** It carries our
Diffie-Hellman values, not ArenaNet's, so it cannot key with them — and the
attempt is exactly the kind of malformed traffic worth not sending. Keep the
patched copy in the vault, away from `C:\gw`.

**Before any session that might crash the client,** neutralise the crash-telemetry
channel — `Gw.exe` embeds Sentry (`SENTRY_DSN`, `sentry.native`, verified in this
build). The working method here is inject, patch, malform, crash; the client has
an outbound reporting channel that HANDOFF.md §9 never considered.
