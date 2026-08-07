# The key-tap code cave, designed and verified on paper

*2026-08-07. The signature-anchored patch that makes the transient `master_secret`
persistent so `keytap.py` can read it. Every byte here was encoded and round-tripped
through capstone against the pinned build-38797 client; nothing is applied and nothing is
launched — that is the loopback verification step, deliberately left for a human-in-the-loop
launch. Companion to [FINDINGS.md](FINDINGS.md) (where the key lives) and
[CAPTURE.md](CAPTURE.md) (why route C).*

## Why a cave, and the honesty correction

The key must be captured at the moment it is formed, for the whole session including the
first frames — a mid-session snapshot of the persistent RC4 S-box loses everything before
it. But `master_secret` is a transient stack buffer at `[ebp-0x18]`, gone microseconds
later. Making it readable means copying it somewhere stable at derivation time, and copying
20 bytes is *new code*: a small code cave, not the zero-new-code in-place edit the DH /
updater / mutex patches are. CAPTURE.md's "duplicate-store, no new code" was optimistic and
is corrected here. It is still far smaller and safer than the ciphertext options — 38 bytes
that only read a stack buffer and write a data slot — but it is injection, and it is named
as such.

## The tap point (OBSERVED, re-verified by disassembly)

Inside `0x007DC030` (`MsgConn.cpp`), which handles the `SERVER_SEED` message
(`[ebx+0x60]==1`, message type `0x16`). A 4-iteration unrolled loop XORs
`server_seed [ebx+0x69]` with the DH shared secret into `master_secret` at `[ebp-0x18]`,
20 bytes, **complete at `0x007DC0CE`** — the loop exits there and the value is immediately
pushed into the RC4 key-schedule thiscall at `0x007DC0E3`. `ebp` is the frame pointer, set
at entry and untouched until the epilogue, so `[ebp-0x18]` is valid at the tap.

## The patch

**Steal 6 bytes at `0x007DC0CE`:**

```
0x007DC0CE  8B 5D DC        mov ebx, [ebp-0x24]     ; stolen #1
0x007DC0D1  8D 45 E8        lea eax, [ebp-0x18]     ; stolen #2
```

**Overwrite with a jump to the cave** (`E9 rel32` + one `90` to fill the 6th byte):

```
0x007DC0CE  E9 0F 54 C7 FF  jmp 0x004514E2
0x007DC0D3  90              nop
```

Execution resumes at `0x007DC0D4` (`push eax`) — the two stolen instructions run inside the
cave first, so the client's behaviour is byte-identical.

**Safety check before patching:** the 6 bytes at the tap must equal `8B 5D DC 8D 45 E8`
exactly, or refuse. They are hardcoded into the cave (it replays them), so a build where
they differ would both mis-locate the patch and replay the wrong instructions — refuse
rather than corrupt.

## The cave (38 bytes, in the 78-byte `0xCC` run at RVA `0x514E2`)

`.text` carries a 78-byte int3 (`0xCC`) padding run at RVA `0x514E2` (VA `0x004514E2`) —
executable, never executed. The cave is 38 bytes and fits with room to spare. Encoded and
round-tripped through capstone:

```
0x004514E2  9C              pushfd                     ; save flags (incl. DF)
0x004514E3  60              pushad                     ; save all GP registers
0x004514E4  FC              cld                        ; movsd must increment
0x004514E5  E8 00000000     call 0x004514EA            ; PIC: push EIP
0x004514EA  58              pop eax                    ; eax = runtime addr of this insn
0x004514EB  8D B8 B6027A00  lea edi, [eax+0x7A02B6]    ; edi = runtime SLOT (ASLR-safe)
0x004514F1  8D 75 E8        lea esi, [ebp-0x18]        ; esi = &master_secret
0x004514F4  B9 05000000     mov ecx, 5
0x004514F9  F3 A5           rep movsd                  ; copy 20 bytes -> SLOT
0x004514FB  61              popad                      ; restore registers
0x004514FC  9D              popfd                      ; restore flags
0x004514FD  8B 5D DC        mov ebx, [ebp-0x24]        ; stolen #1, replayed
0x00451500  8D 45 E8        lea eax, [ebp-0x18]        ; stolen #2, replayed
0x00451503  E9 CCAB3800     jmp 0x007DC0D4             ; back
```

**ASLR-safe by construction.** The client sets `DYNAMIC_BASE` and ships a real `.reloc`, so
its load base moves per launch and a hardcoded absolute address in the cave would break. The
`call/pop eax` reads the runtime EIP; `lea edi,[eax+0x39FF16]` reaches the slot by a
*link-time-constant delta* (`SLOT - 0x004514EA`), correct at any load base. No new
relocation entry needed. `keytap.py` correspondingly reads the slot as
`runtime_module_base + RVA`, never `image_base + RVA`.

**State-clean.** `pushad`/`popad` + `pushfd`/`popfd` bracket everything, `cld` is inside the
flag save, and the `call/pop` is stack-balanced — after the cave, only the slot memory has
changed. The stolen instructions then execute exactly as they would have.

## The slot: found in `.data`, VA `0x00BF17A0` on build 38797

The genuinely subtle choice, and the one my first hand-analysis got wrong: I read the
section table's `vaddr` field (`0x7EC000`, an **RVA**) as a virtual address and placed the
slot at `0x7F1400` — which is actually an RVA landing in `.text`, not a `.data` VA at all.
`keytap_patch._find_slot` does it correctly, and applying the patch surfaced the slip: the
finder returns VA **`0x00BF17A0`** (RVA `0x7F17A0`, i.e. base `0x400000` + the `.data` RVA),
genuinely in file-backed `.data`, and the cave's `lea edi,[eax+0x7A02B6]` resolves exactly
to it. Recorded rather than quietly fixed — it is the same RVA/VA care the rest of the
toolkit takes, and running the patch is what caught it.

The mechanism the finder uses, which is the real design: the "5.5 MB of `.data` slack" is
the client's *own* zero-initialised globals, not free space, and `.data` cannot be extended
(its virtual end rounds up to `.rsrc`'s start). So the slot is a **verified-unreferenced
window** inside a large `.data` zero run — the finder centres a 32-byte window in a zero run
of at least ~160 bytes and confirms **no instruction in `.text` references any address in
it** (each candidate address appears nowhere in `.text`), so no static code path reads or
writes it.

This avoids adding a PE section (lower footprint, smaller anti-cheat surface). Its residual
risk — that the window is the tail of a buffer whose base lives in non-zero `.data` before
the run and extends in — is **caught by the loopback verify before any live run**: a
collision shows up as either client misbehaviour or a slot-read that does not match the key
we independently hold.

**Alternative if that risk is unacceptable:** append a one-page RW section (`.rurik`) for
the slot — collision-free by construction, at the cost of a new section header, a bumped
section count, and a corrected `SizeOfImage`. Recommended only if the loopback verify ever
shows the `.data` window is disturbed.

*(The exact slot VA and the `lea edi` displacement are computed per build by the finder,
never hardcoded; `0x00BF17A0` / `0x7A02B6` are build 38797's values. The cave structure is
unchanged whichever window or section holds the slot.)*

## The relocation signature

Anchored at the tap start, spanning the stolen bytes through the RC4-setup constants —
**unique in the image** (one hit, at `0x007DC0CE`):

```
8B 5D DC  8D 45 E8  50  6A 14  8D 73 7C  C7 43 60 02 00
mov ebx,[ebp-0x24]; lea eax,[ebp-0x18]; push eax; push 0x14;
lea esi,[ebx+0x7c]; mov [ebx+0x60], 2                      (17 bytes)
```

It encodes protocol constants unlikely to shift across a rebuild — the 20-byte key length
(`push 0x14`), the RC4 state offset (`[ebx+0x7c]`), and the stage transition to 2 — the same
"relocate from a byte signature, never a hardcoded address" idiom `dump_dh_params.py` uses
for the DH accessor. `make_custom_client.py` locates the tap by this signature, derives the
patch and back-jump displacements from where it lands, and refuses if the signature is
absent or not unique (a recompiled client is a real finding, not a tool bug).

## What `make_custom_client.py` gains

A new flag (say `--key-tap`) that, on the live-capture build only:

1. Finds the signature; confirms the 6 stolen bytes are `8B 5D DC 8D 45 E8`; refuses
   otherwise.
2. Finds a `>= 40`-byte `0xCC` run for the cave (the 78-byte run at `0x514E2` today; located
   by scan, not hardcoded).
3. Writes the cave, the tap jump, computing all three displacements from the located
   addresses.
4. Registers the two touched `.text` ranges (the tap patch and the cave) in
   `pinned.PATCHED_TEXT` and `dhbuild.patch_state()`, so a future study pinning an address
   there is warned — the way the existing patches are tracked.
5. Re-reads the written file and verifies the cave and jump disassemble as intended (the
   same read-back discipline `make_custom_client` already applies to the DH patch).

## The loopback verification — DONE, GREEN (2026-08-07)

Run entirely on our own server, and it passed end to end:

1. Built a **DH-patched** loopback client with `--key-tap`, assembled it at the existing
   caged run path (the cage is by program path, so no new elevation was needed), and
   confirmed `assert_launch_safe(ours → 127.0.0.1)` accepted it with `key_tapped: True`.
2. Ran the loopback stack (`session.py --until login --keep-open`). The client **keyed the
   auth channel at t+9.1s and did not crash** — so it processed `SERVER_SEED`, the cave ran
   on the path from `master_secret` to the RC4 key schedule, and the process stayed alive.
3. `keytap.py` read 20 bytes at `Gw.exe + 0x7F17A0` out of the live 32-bit client
   (ASLR-correct, cross-process from 64-bit Python).
4. **They equalled the `master_secret` our server independently derived** for that session
   (`48c3490b3661812979321628e876481c59872d52`, key
   `rurik_dh_2026-07-29_221c13772c7a.json`) — exactly.

So the whole key-acquisition path is proven on a live client, against a key we hold, with
zero trust in the live service: the PIC/ASLR-safe cave, the `.data` slot, the tap point, and
the `keytap.py` reader are all correct end to end. The loopback client was then rebuilt
without the tap (it is opt-in for capture), and the suite is green.

The **stock-DH live build** now gets the same `--key-tap` patch when the off-wire capture
side is ready; the live run itself stays human-driven.
