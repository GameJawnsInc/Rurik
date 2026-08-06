# Runbook — driving the real client against Rurik

Copy-pasteable from `C:\gd\Rurik` **in PowerShell**, the shell this project is
driven from. Every `python …` line works unchanged in PowerShell, `cmd.exe` and
bash alike; the one shell-sensitive line is launching the client, which needs a
leading `&` (step 3).

**State of play (2026-08-04): R1 is done.** A real client, build 38797, reaches
character select and displays "Test Warrior". Clicking *Play* is unimplemented —
the client will ask for a game instance and get nothing back. That is the current
edge, and its questions land in the vault in plaintext.

---

## TL;DR — the daily loop

One command, once the one-time setup below has been done:

```bash
python toolkit/harness/session.py
```

It pre-flights the ports (a stale listener is named by pid and image;
`--replace` stops it if it is a python server, and refuses to touch anything
else), starts all three servers and proves each owns its port, drives the
client through login → EULA → Play with focus-verified clicks, and judges the
run from the client's own messages — one `[PASS]`/`[FAIL]` line per checkpoint,
ending at the spawn request. `--until login` stops sooner, `--serve` runs just
the stack in one terminal, and the report, server logs and screenshots land in
`vault/captures/harness/<stamp>/`. The harness's own offline tests:

```bash
python toolkit/harness/test_harness.py
```

Two things it knows that the terminals below do not say:

- The game channel is served by a **second authsrv.py instance** — the client
  declares its channel in its version header, so the same code decodes the game
  catalog with no extra flag.
- OBSERVED build 38797 (2026-08-06, handshake PLAN §10): the client dials the
  GAME_SERVER_INFO **host** at hardcoded port **6112**; the advertised port is
  decorative. The stack therefore gives the game catalog a loopback alias of
  its own: the handoff advertises `127.0.0.3`, the gamesrv listens on
  `127.0.0.3:6112`, and game traffic records to `vault/captures/gamesrv/`
  instead of mixing into the auth capture. The harness's map checkpoints watch
  only that dir, so a handoff pointing back at the auth host fails loudly.

### The same loop by hand

Four terminals, in this order. Nothing here needs admin except the client.

```bash
python toolkit/portal/webgate.py
```

```bash
python toolkit/authsrv/authsrv.py --game-host 127.0.0.3
```

```bash
python toolkit/authsrv/authsrv.py --bind 127.0.0.3 --port 6112 --vault vault/captures/gamesrv
```

(That third terminal is the game catalog. Without it — or with the handoff left
at its `127.0.0.1` default — the game dial lands back on the auth listener,
whose catalog self-selection still serves the game but records it into
`vault/captures/authsrv/`, mixed with auth traffic.)

Terminal 4 is the client, and it must be **elevated** — the launcher changes
firewall rules:

```bash
& "C:\gd\Rurik\toolkit\clientpatch\launch_caged.ps1"
```

Do **not** launch the exe directly while the cage is up. The pre-login patcher
needs one outbound check to succeed before it will show the login screen, and the
block rule denies it instantly and forever — the client sits on *Connecting to
ArenaNet* with no socket to explain why. `launch_caged.ps1` opens the cage, walks
it through the patcher, records every non-loopback endpoint it touched to
`vault/captures/patcher/`, and closes the cage again before you log in. The
re-cage is in a `finally`, so Ctrl-C and crashes still close it.

Then log in at the client's own screen with **any** account name and password —
the webgate authenticates nobody by design. Accept the User Agreement if it
appears; that is client-side UI and accepting it sends three bytes to loopback.

Afterwards, see what the client said:

```bash
python toolkit/authsrv/summarize_capture.py
```

---

## Before that: check it works without the game

Always. A red test names the broken thing; the game says `Connecting…` for thirty
seconds and then `Code=058`, which tells you nothing.

```bash
python toolkit/authsrv/test_handshake.py
```

Ends `HANDSHAKE VERIFIED`. It drives the entire login offline — key exchange,
computer info, portal login, and the five-message character burst — using a test
client that reads the DH parameters **out of the patched executable**, so the whole
chain is exercised. Its last check is a negative control: an unpatched client must
derive a *different* key.

```bash
python toolkit/portal/test_webgate.py     # portal endpoints
python toolkit/schema/test_codec.py       # wire codec, against real captured bytes
```

---

## One-time setup, and again after every ArenaNet update

The client auto-updates and **the Diffie-Hellman parameters rotate with every
build** — a patched copy from last week keys to nothing. Order matters: snapshot
*before* accepting an update, or you have already lost the build you were working
against.

**1. Confirm the crypto scheme is still where we think it is.** Reads
`C:\gw\Gw.exe`, touches nothing.

```bash
python toolkit/clientscan/dump_dh_params.py
```

Expect `generator g : 4`, a 512-bit prime, and a final `GO.` line.
If it says **NOT FOUND**, stop: the accessor signature changed, and no patching
tool in this repo or anyone else's can be trusted until it is re-derived. That is
a finding to write up in `studies/handshake/PLAN.md`, not a thing to work around.

**2. Snapshot the client.**

```bash
python toolkit/snapshot_client.py
```

Exit `0` means every file verified byte-identical; exit `3` means something was
locked — close Guild Wars and re-run. An incomplete snapshot is recorded as such
in the manifest so it cannot be mistaken for a complete one.

**3. Patch a copy and build a directory it can run from.**

```bash
python toolkit/clientpatch/make_custom_client.py
```

```bash
python toolkit/clientpatch/make_run_dir.py
```

The first writes a fresh DH triple into a **copy** (it refuses to write anywhere
under `C:\gw`), saves the private half to `vault/keys/rurik_dh_<build>.json`, and
ends with `B == g^b mod p -> True`. If that says `False`, do not launch the binary.
The second assembles `vault/run/<build>/` with the exe, `Gw.dat` and the DLLs
(~4.2 GB, a few seconds) and **prints the exact launch command** — use that, since
the path is build-specific.

**Keep the key file.** The server needs `server_private` to decrypt. Lose it and
the patched client is a brick.

**4. Cage the patched client** (elevated PowerShell, one time per patched exe):

```bash
powershell -ExecutionPolicy Bypass -File C:\gd\Rurik\toolkit\clientpatch\isolate_client.ps1
```

Blocks all outbound traffic from the patched exe except loopback. `C:\gw` is
untouched, so the real client still reaches the live service normally — capture
sessions will need that. Undo with `-Remove`.

---

## What a good run looks like

Terminal 2, in order:

```
[c1] auth version: build=38797 h0008=1 h000C=4
[c1] key exchange OK — ARC4 key …
[c1] c2s 0x8001 SEND_COMPUTER_INFO
[c1] c2s 0x8002 SEND_COMPUTER_HASH
[c1] s2c SESSION_INFO (0x0001, 10B)
[c1] c2s 0x8038 PORTAL_ACCOUNT_LOGIN
[c1] login OK — <your account name>
[c1] s2c CHARACTER_INFO / ACCOUNT_SETTINGS / FRIEND_STREAM_END / ACCOUNT_INFO
[c1] s2c REQUEST_RESPONSE(OK)
```

Then heartbeats with a rising tick counter, which is a healthy idle client.

---

## When it goes wrong

| Symptom | Meaning | Do this |
|---|---|---|
| Stuck on `Connecting to ArenaNet`, no sockets, servers see nothing | The cage is blocking the pre-login patcher's update check | Launch via `launch_caged.ps1`, not the exe directly. See below |
| `Unexpected token '-authsrv'` | PowerShell parsed the quoted path as a value | Add the leading `&`. Nothing launched; the flags are fine |
| `Could not bind … Another AuthSrv is almost certainly still running` | Working as intended | `netstat -ano \| findstr :6112`, stop the old one. Note a healthy stack shows TWO 6112 listeners — auth on `127.0.0.1`, game on `127.0.0.3`; the stale one is at the host you are trying to bind. This replaced a silent-shadowing bug that cost two sessions |
| `Code=058`, nothing in terminal 2 | Client never reached us | Both flags present? Launched the **run-dir** copy, not `C:\gw\Gw.exe`? |
| `expected 0x4200, got …` | Key exchange never started | Almost always an unpatched client |
| `login REJECTED — no session` | Portal and AuthSrv disagree | Restart the webgate so it re-issues, or use `--allow-any-session` to prove the rest of the path works |
| Client hangs after login | A reply field is wrong | `ACCOUNT_INFO` has three fields marked low-confidence at the call site — start there. See below |
| Roster empty but login succeeded | Campaign gate | Try the all-campaigns bitmask `b'\x3f' + b'\x00'*7` in `ACCOUNT_INFO` |
| `undecodable` in terminal 2 | Unknown opcode, framing stopped | Correct behaviour — it refuses to guess. The printed leading bytes are the next thing to identify |
| Anything at all after an ArenaNet update | Parameters rotated | Redo the one-time setup in full |

**Never point a patched client at the real service.** It carries our DH values, so
it cannot key with ArenaNet's — and the attempt is exactly the kind of malformed
traffic worth not sending.

---

## The patcher stall, and why it read as innocent

Diagnosed 2026-08-04. Worth writing down because the evidence pointed the wrong
way for half an hour.

The client hung on *Connecting to ArenaNet* — which is the **patcher**, not the
login: that string sits in the same localized block as `Downloading...` and
`Downloading %u.%uMB (%uKB/sec)`. The cause was the cage's outbound block denying
the patcher's update check.

What made it hard: **a Windows Firewall outbound block fails `connect()`
immediately rather than black-holing it.** The socket never reaches `SYN_SENT`,
so it never appears in a sample. Twenty-four samples over twenty seconds found no
sockets at all, which reads as *the process is not using the network* — the exact
opposite of the truth. The tell was two threads parked in `ExecutionDelay`, i.e.
`Sleep()`: try, denied instantly, sleep, retry, forever.

Two other traps in the same hour:

- `Get-Process().Modules` against `Gw.exe` returns only `ntdll` and the wow64
  shims. That is not a half-initialised process — it is a 64-bit query against a
  32-bit process, which cannot see the 32-bit module list. It means nothing.
- `Gw.tmp` appearing at 0 bytes next to the exe looks like an interrupted
  download. It is a normal startup scratch file; the live install has one too.

What actually settled it was an A/B: the **unpatched, uncaged** client at
`C:\gw\Gw.exe` with the same flags walked straight past the patcher to the login
screen, then died at key exchange exactly as the negative control predicts
(`AUTH_CMSG has no opcode 26763` — our ARC4 keystream against its ArenaNet-keyed
one). Same machine, same flags, one variable.

The client's own log is the fastest way in. `-log` is live and writes `Gw.log`
beside the exe, but it **buffers and only flushes on exit** — a stuck client shows
0 bytes. Close it, then read.

---

## Where the pieces live

| Path | What it is |
|---|---|
| `toolkit/portal/webgate.py` | Stage A, the portal (HTTP, 6601) |
| `toolkit/authsrv/authsrv.py` | Stage B, auth + the encrypted channel (6112) |
| `toolkit/portal/sessionstore.py` | Shared state between the two, plus the UUID wire encoding |
| `toolkit/schema/` | The 777-message catalog and the codec |
| `schema/messages.json` | The wire schema itself (tracked in git) |
| `toolkit/clientscan/` | Read-only client analysis |
| `toolkit/clientpatch/` | Patching, run-dir assembly, the firewall cage |
| `toolkit/clientpatch/launch_caged.ps1` | Elevated launcher: opens the cage for the patcher, shuts it before login |
| `vault/` | Gitignored. Client snapshots, keys, captures, prior-art mirrors |
| `vault/dat_study/Gw.dat` | A third copy of the archive, for reading map data. See below |
| `studies/handshake/PLAN.md` | How R1 was actually solved, wire detail included |
| `studies/movement/FINDINGS.md` | What we know about movement, and from whom |
| `studies/mapdata/FORMAT.md` | Reading map geometry out of the archive |
| `PLAN.md` | Strategy, the ladder, ranked angles of attack |

---

## Backing up the vault, and the one thing that blocks going off-disk

The vault is the only part of this project that cannot be rebuilt. Code regenerates
from git; two pinned ArenaNet builds do not, and ArenaNet's own updater has already
replaced one in place mid-session. `vault/client/` alone is 8 GB of that, and its
directory names are the sha256 prefixes of the binaries inside, so a copy verifies
itself.

**The mirror.** Same-disk, so it covers the failure with history here — an install or
a script overwriting files — but not the disk dying:

```bash
robocopy C:\gd\Rurik\vault C:\gd\Rurik-Backups\vault /MIR /R:1 /W:1 /MT:8 /NP /NFL /NDL
```

Robocopy exit codes 0–7 all mean success; 1 is "files were copied". Check `FAILED : 0`
in the summary rather than the exit code. Last full run: 20,855 files, 20.897 GB,
about three minutes, both client `Gw.exe` hashes verified equal afterwards.

**Off-disk is the copy that matters, and it needs the scrub first.** The client sends
the owner's real ArenaNet credential to our own webgate on every login and we record
it, so `vault/captures/portal/` carries the account email, the password as base64, and
every issued session token. Nothing has ever been in git — `vault/` was gitignored in
the first commit — but that set cannot leave the machine as it stands. It is a filter,
not a blocker:

```bash
python toolkit/scrub_captures.py
```

Writes `vault/captures/portal-scrubbed/` (387 KB) and never touches the originals,
which stay as recorded because an original capture is evidence about the protocol.
Placeholders are assigned sequentially rather than hashed — the password is short
and a hash of it would be brute-forceable — and are the same length as what they
replace, so `Content-Length` and the base64 width stay honest. `toolkit/test_scrub.py`
harvests the secrets out of the originals independently and asserts not one survives in
the output; that check found 181 values still leaking through the reply body the first
time it ran, which is why `SECRET_ELEMENTS` covers both directions. Re-run it after
touching that list.

For an off-disk copy, take everything except `run/` and `dat_study/` (11.9 GB, both
regenerate from `client/` plus the patcher and `Gw.dat`) and substitute
`portal-scrubbed/` for `portal/`. That is roughly 10.8 GB — a USB stick.

## The third copy of Gw.dat, and why it exists

A running client holds an **exclusive lock** on the archive it was launched from.
While `Gw.exe` is up, `vault/run/<build>/Gw.dat` cannot even be opened for
reading — Python raises `PermissionError`, not a partial read — so any attempt to
study map data during a play session fails outright.

Rather than close the game every time, keep a copy that is never used to run
anything:

```bash
Copy-Item "C:\gw\Gw.dat" "C:\gd\Rurik\vault\dat_study\Gw.dat"
```

3.9 GB, about a minute. It is under `vault/`, so the provenance gate covers it —
`git check-ignore` confirms it, and it must never move anywhere else in the tree.

**Never launch a client against this copy.** Its whole value is that nothing ever
locks it.

Verify a copy by parsing its header, which cross-checks itself:

```bash
python -c "import struct; f=open(r'C:\gd\Rurik\vault\dat_study\Gw.dat','rb'); h=f.read(32); mft,=struct.unpack('<I',h[16:20]); size,=struct.unpack('<I',h[24:28]); f.seek(mft); m=f.read(16); cnt,=struct.unpack('<I',m[12:16]); print(h[:4], m[:4], cnt, size==cnt*24)"
```

Expect `b'3AN\x1a' b'Mft\x1a' 177335 True`. The last value is the check that
matters: the entry count sits in the MFT header and the table size sits in the
file header, and the two agree only if the 24-byte entry layout is right.

`C:\gw` is the owner's real install. Reading bytes from it is acceptable —
strictly read-only, nothing written, nothing copied into the tracked tree — but
it is never a target for patching or launching.
