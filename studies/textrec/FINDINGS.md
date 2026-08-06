# The text-record codec: read all the way down, and readable 28% of the way

What a `Gw.dat` text record is, settled by reading the client's own decoder
rather than by fitting hypotheses to the bytes. The session that produced this
was asked to decode the record kinds we could not read. The format is now read
completely; most records still do not decode, and the reason is a specific
missing input, not a gap in the reading.

No client was launched. `C:\gw` was not touched at all — the pinned inputs were
the vault snapshot `vault/run/2026-07-29_221c13772c7a/Gw.exe` (build 38797) and
`vault/dat_study/Gw.dat`, both opened read-only. No network. No ArenaNet bytes
entered the repo: the escape table this study turns on is read out of the image
at runtime by `toolkit/clientscan/textrec.py` and is not transcribed into
source.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | We checked real bytes on this machine — the PE, the archive, or our own output. |
| **SOURCED** | ArenaNet's own words, compiled into the shipped image: assert expressions and `P:\Code\...` paths. |
| **INFERRED** | Our reasoning from measured parts. Sound, but nobody's primary artifact says it. |
| **UPSTREAM** | A third-party reimplementation says so. A reconstruction, not a fact about retail. |
| **NOT ESTABLISHED** | We looked, we have specific refuted readings, and we do not have the answer. |

---

## The answer in one page

**The field this repo called `kind` is a bit width.** Calling it a kind is what
made the census look like a taxonomy of record types and sent three prior
hypotheses after the wrong thing. The 6-byte record header is ArenaNet's own
`StringHeader`:

```
+0  u16  bytes    total record length, header included
+2  u16  base     base codepoint of the symbol alphabet
+4  u8   bits     bit width of one packed symbol, 1..0x10
+5  u8   zero in all 101,376 language-0 records
```

**SOURCED.** The decoder is `P:\Code\Engine\Text\TextDecode.cpp` at
**VA 0x007cb000**, and its first act is `cmp word ptr [edi], 6` guarding the
assert `data->bytes >= sizeof(StringHeader)`. That is ArenaNet naming both the
struct and its size.

**A record decodes as:** read `bits` bits at a time, LSB-first; symbol 0 becomes
U+0000; symbols 1..31 index a 32-entry table in the image; symbols ≥ 0x20 become
`base - 0x20 + symbol`.

**But only 28.0% of records are readable from the archive alone.** The client
copies a payload out verbatim only when `base == 0 and bits == 0x10`, which is
plain UTF-16LE. Every other record is **RC4 ciphertext** — `CptRc4.cpp`,
algorithm 2 of `CptApi.cpp` — and the key is not in the record. It is an 8-byte
pair the *caller* obtained by parsing the coded string that referenced the
record. **NOT ESTABLISHED:** where that pair comes from for a given record.

**This does not block anything the repo currently wants.** MEASURED: all 10,329
skill string ids and all 888 area string ids resolve to plain records. The only
9 exceptions belong to three dead skill rows whose every stat is zero and whose
`linked_id` points past the end of the table. **Every string id any `Gw.exe`
table actually points at is readable today.**

### Corrections to what this repo believed

`toolkit/clientscan/textrec.py`'s own docstring said, before this session:

> kind 0x07 66,330 65.4% the majority. High-entropy payload, `aux` non-zero and
> varying -- shaped like a per-record compression with `aux` as the decoded
> size. NOT ESTABLISHED.

Three things in that sentence are wrong and one is right.

- "kind" — **wrong**, it is a bit width.
- "`aux` as the decoded size" — **already refuted** before this session by the
  brief's own counterexample, and now explained: `aux` is a base codepoint.
- "per-record compression" — **wrong**. It is encryption, not compression.
- "High-entropy payload" — **right**, and it is the clue that was there all
  along. MEASURED at 8.000 bits/byte over 4,934,260 payload bytes.

The task brief's own framing also needs correcting, because it would send the
next session the wrong way:

> Kind 0x07 is very likely item names, NPC dialogue and quest text — skill and
> map names are all 0x10 and already readable.

**The observation is right and the inference from it is backwards.** Skill and
map names are plain *because* they are reached by a bare id from a table in the
PE, and a bare id carries no key. Whatever the encrypted records are, they are
things the client only ever reaches through a coded string that brought a key
with it. That is a statement about the access path, not the subject matter.

---

## 1. The decoder, instruction by instruction

**SOURCED + MEASURED.** `studies/datwrite/FINDINGS.md` located VA 0x007cb000 by
matching Fournux/Tyria-Extractor's 9-byte trampoline signature and recorded that
nobody had ever read what the function does. Reading it is what this study is.

The function is `fn(context, data, keyLo, keyHi)`. It branches once, at
`0x7cb02f`:

```
mov  eax, [ebp+0x10]        ; keyLo
or   eax, [ebp+0x14]        ; | keyHi
je   0x7cb082               ; both zero -> copy the payload verbatim
```

**With a key** (`0x7cb034`) it hashes the 8 bytes at `&keyLo` into a 20-byte
buffer, builds an RC4 key from that buffer, and decrypts the payload into
`context+0x150`. **Without one** it memcpys the payload there unchanged.

Either way it then reaches `0x7cb15a`, which reads the header:

```
movzx eax, word ptr [edi+2]   ; base
test  ax, ax
jne   general                 ; base != 0 -> the symbol path
cmp   byte ptr [edi+4], 0x10
jne   general                 ; bits != 16 -> the symbol path
```

so the verbatim path needs **both** conditions. That is why three records with
`bits == 0x10` and a non-zero base are *not* plain text, and why our decoder
must test both — testing only the width silently mis-decodes them.

The general path at `0x7cb1ae`:

```
movzx ecx, byte ptr [edi+4]   ; bits
mov   eax, [ebx+8]            ; payload byte count
shl   eax, 3                  ; * 8
div   ecx                     ; / bits
inc   eax                     ; symbol count = bytes*8/bits + 1
```

**This is the whole reason `bits` cannot be a type tag: it is a divisor.** The
value is then used three more ways — `shl edx, cl` to build the mask,
`shr edi, cl` to advance the accumulator, `sub eax, ecx` to decrement the bit
count. A type tag is not shifted by.

The symbol loop, `0x7cb207`–`0x7cb263`, refills the accumulator a byte at a time
while fewer than 25 bits are available (`cmp eax, 0x18 / jbe`), so the maximum
shift is 24 and nothing overflows the 32-bit register. Past the end of the
payload it stops advancing the source pointer but keeps incrementing the
counter, which is zero-padding. Then:

```
test edx, edx                             ; symbol 0
jne  .nz
xor  ecx, ecx                             ;   -> U+0000
.nz: cmp edx, 0x20
jae  .high
movzx ecx, word ptr [edx*2 + 0xa89e8e]    ; 1..31 -> escape table
jmp  .store
.high: mov ecx, [ebp-4]                   ; base
add  ecx, -0x20
add  ecx, edx                             ; -> base - 0x20 + symbol
movzx ecx, cx
```

### The escape table

**MEASURED.** 32 `u16` at VA 0x00a89e8e, and it is bounded on both sides: slot 0
is the unused zero the decoder branches around, and the 64 bytes end — after
exactly 2 bytes of alignment padding — where `P:\Code\Engine\Text\TextDecode.cpp`
begins. An array that merely looked long enough would prove nothing; one whose
last entry abuts a known string is a different kind of evidence. Slots 1..31, in
order, are the characters

```
0 1 2 3 4 5 6 s t r n u m ( ) [ ] < > % # / : - ' " ␠ , . ! \n
```

which is the alphabet of the client's own markup — `<str>`, `<num>`, `%`, `#`,
bracketed indices — plus the punctuation and space that dominate running text.
Digits stop at 6 and no letter but `strnum` appears, so this is a
frequency-ranked escape set, not a character class.

`toolkit/clientscan/textrec.py` locates it from the assert string, never from
the address, and re-reads it out of the image on every run. Hardcoding it would
both go stale silently on the next client build and put ArenaNet's bytes in the
repo.

---

## 2. Why `bits` is a width, proved by something our decoder cannot force

This is the load-bearing evidence, and it is the good kind: the prediction is
made by the reading, and the artifact was free to refute it.

**The client's own gate.** SOURCED, `0x7ca382`, in the function that walks a
decompressed text file into records:

```
cmp byte ptr [edi+4], 0x10
ja  invalid                 ; -> "Invalid text string file data at language %u string %u"
```

The client rejects the whole file if that byte exceeds 0x10. A maximum of 16 is
what you write for a width when your output element is a `u16`. It is not
something you write for a type tag.

**The cross-language survey.** MEASURED over all 101,376 records in each of the
11 languages, by `studies/textrec/tools/census.py`. Three results.

**The widths take every value from 5 to 16, with no gaps.** Language 0 alone
uses only `{5, 6, 7, 8, 13, 14, 16}`, and that gappy set is exactly what made
the original census read as a taxonomy of seven record types. It is a sampling
artefact of looking at one language. Widths 9, 10, 11 and 12 appear in Korean,
Chinese, Polish and English-2; width 15 appears in Chinese and Japanese. A type
tag has no reason to fill a dense range; a per-record optimal packing has no way
not to.

Every language encrypts **exactly the same 72,969 slots** — set equality, not
merely equal counts. Whether a record is plain is a property of the slot, the
same in Korean as in French. Every language has exactly 28,407 plain records.

Among those encrypted records, the share needing more than 8 bits:

| English | French | German | Italian | Spanish | Chinese-S | **Polish** | Japanese | Chinese-T | Korean |
|---|---|---|---|---|---|---|---|---|---|
| 0.0% | 0.1% | 0.1% | 0.0% | 0.0% | 63.7% | **64.2%** | 73.7% | 78.9% | 97.4% |

**Polish is the observation that kills the type-tag reading.** Polish is a Latin
script. Any "these are CJK records" story predicts it sits with French at 0.1%.
It sits at 64.2%, because `ą ć ę ł ń ó ś ź ż` are scattered through Latin
Extended-A, far from ASCII, and a **contiguous** window `base .. base + 2^bits`
cannot cover both ends at 7 bits. Only a base-plus-width reading predicts that,
and it predicts it before you look.

Locked in as `toolkit/clientscan/test_textrec.py` section 4.

---

## 3. The rest is RC4, and it is the same RC4 the game channel uses

**SOURCED.** The key path from `0x7cb034` is
`CptApi.cpp` → `CptRc4.cpp`. The algorithm selector is checked with
`sub dword ptr [esp+4], 2; je` against the assert
`No valid case for switch variable 'algorithm'`, so **algorithm 2 is the only
one the shipped client implements**. The key object carries the magic `'cryp'`
and the handle type `HCryptKey`. The key schedule at `0x909ca1` fills
`S[i] = i` for 256 and runs the standard KSA; the crypt method at `0x909c20` is
the standard PRGA. Textbook RC4, no variation.

**The key derivation is `gwcrypto.arc4_hash`, which this repo already ships.**
MEASURED, and this is a pleasing collision. The hash at `0x909d63` repeats its
input to 20 bytes, then runs an unrolled five-round SHA-1-style compression at
`0x909db8` with the message schedule folded into immediates. Because the initial
state is the fixed SHA-1 IV, those immediates are computable from
`toolkit/authsrv/gwcrypto.py`'s specification — and they match:

| | computed from `arc4_hash` | immediate in the image |
|---|---|---|
| round 1 | `0x9FB498B3` | `0x9FB498B3` |
| round 2 | `0x66B0CD0D` | `0x66B0CD0D` |

So the cipher protecting text records is the same primitive pair a real client
has already accepted during a live handshake. `textrec.py` imports it rather
than carrying a second copy, and `test_textrec.py` section 5 re-derives the two
constants and finds them in the image, so the identity is checked rather than
asserted.

**A first hand-transcription of `0x909db8` disagreed with `arc4_hash` on
2000/2000 random inputs.** It was mine and it was wrong; the constants check is
what settled which. Recorded because a bad transcription would have turned every
negative result in §4 into an artefact of my own bug.

### The payloads really are ciphertext

MEASURED, and stated as a measurement because "we could not read it" is not one:

| | payload bytes | entropy |
|---|---|---|
| plain (`base == 0 && bits == 0x10`) | 2,872,100 | **3.408** bits/byte |
| everything else | 4,934,260 | **8.000** bits/byte |

8.000 over 4.9 MB is not compression, which leaves structure behind; it is a
stream cipher. The 16-bit non-plain records are byte-aligned, so their flatness
cannot be blamed on bit packing.

---

## 4. Where the key comes from, and what we refuted

**SOURCED, partially.** The caller is `0x7cb280`. It runs
`CParser::Validate` over its source buffer, then `TextParser.cpp`'s
`0x7cc4d0` → `0x7cc570`, which walks the **coded string** looking for a word
equal to the string index it was given, and on a match copies out a pair of
dwords parsed by `0x7ccb50`. That pair becomes the RC4 key.

So **the key travels with the reference, not with the record.** A bare string
id, of the kind every table in `Gw.exe` holds, produces the pair `(0, 0)`, takes
the verbatim path, and can only ever have been a plain record. Which is exactly
what we measure: 11,208 of 11,217 table ids are plain, and the 9 that are not
belong to dead rows.

### NOT ESTABLISHED: the pair for a given record

Refuted readings, so nobody repeats them:

- **A single key shared by all records — REFUTED.** MEASURED: the byte at each
  of positions 0..7, histogrammed across all 66,330 seven-bit records, has
  entropy 8.00. A shared keystream would make those distributions the plaintext
  distributions, which are not flat. Also 0 duplicate payloads in 4,000.
- **The key as a function of the record's identity — REFUTED, 17 readings.**
  MEASURED with the probe in `toolkit/clientscan/test_textrec.py` §7 and its
  scratch predecessor: `(sid,0)`, `(0,sid)`, `(sid,lang)`, `(lang,sid)`,
  `(ri,lang)`, `(lang,ri)`, `(fi,ri)`, `(ri,fi)`, `(sid,sid)`, `(archiveId,ri)`,
  `(ri,archiveId)`, `(archiveId,0)`, `(sid,base)`, `(base,sid)`, `(base,0)`,
  `(sid|0x80000000, 0)`, `(sid,0xFFFFFFFF)`.
  Prediction stated before running: a correct key drops pooled symbol entropy
  from 7.00 to roughly 4.5, because natural language is not uniform. Result:
  every one of the 17 read **6.999**, against an undecrypted control of
  **6.999**. Six are kept as live checks that must fail if one ever succeeds.
- **`aux` is the decoded size — REFUTED** before this session by the brief's own
  counterexample, and now explained rather than merely denied.

### The honest shape of the remaining question

The client can decode these records because something handed it a coded string
carrying the key. Nothing in this study establishes what produces those coded
strings for the 72,969 encrypted slots. The candidates, none tested:

1. The server sends them. This is what happens for item names and chat.
2. They come from another record that is itself plain.
3. They come from a table in `Gw.exe` that pairs an id with two dwords.

Candidate 3 is the cheapest to test and would settle it: scan `.rdata` for
12-byte records whose first dword is a string id in the encrypted set. Candidate
1 is the most likely and is directly relevant to R2 — if true, **a server must
send the key alongside the string id**, and Rurik will need to know it.

---

## 5. What changed in the toolkit

- `toolkit/clientscan/textrec.py` — header fields renamed to ArenaNet's
  (`bits`, `base`); `find_escape_table()` / `escape_table()` locate the table
  structurally from the assert anchor; `unpack_symbols()`, `map_symbols()`,
  `record_key()` and `decode()` implement the full codec including the RC4 step;
  `get(sid, key_pair=None)` returns text for plain records and `None` — never
  bytes dressed as a string — for encrypted ones; `needs_key()` distinguishes
  "encrypted" from "absent". The `(kind, aux, payload)` tuple shape and
  `kind_of()` are kept so existing callers do not break.
- `toolkit/clientscan/test_textrec.py` — new, 9 sections, all refutable.
- `studies/textrec/tools/gwdis.py` — the disassembly harness this study ran on.
- `studies/textrec/tools/keyprobe.py` — the 17-reading key probe of §4, kept so
  the refutation is reproducible and extendable rather than just asserted here.
- `studies/textrec/tools/census.py` — writes the per-language census to
  `vault/textrec/census-38797.json`. Extracted client values go to the vault.

### A house-rule tension that needs an owner ruling

`CLAUDE.md` says **"Python 3, standard library only. No third-party dependencies
anywhere in `toolkit/`"**, but `toolkit/clientscan/msghandler.py` already imports
`capstone` and `pefile`. This study needed a disassembler and could not have been
done without one.

What was done here, as the least-bad option and not as a decision: the
disassembly tool lives in **`studies/textrec/tools/gwdis.py`**, outside
`toolkit/`, so the stdlib rule is not further eroded where it is written. Nothing
in `toolkit/` gained a dependency — `textrec.py` and `test_textrec.py` are pure
stdlib. The tool is **committed rather than left in scratch**, because the
`msgtable` study's tooling was left uncommitted and lost, and this study would
have had to rebuild it.

**The ruling that is actually needed:** either analysis tools get an explicit
carve-out from the stdlib rule (and `msghandler.py` moves under it), or
`msghandler.py` is the violation and should move to `studies/`. Both are the
owner's call. This study did not make it.

---

## 6. Open questions

| Question | How to settle it |
|---|---|
| **Where does the 8-byte key come from?** | The three candidates in §4. Start with the `.rdata` scan for `(string_id, dword, dword)` triples — cheapest, and falsifiable in an hour. |
| What are the 72,969 encrypted slots *for*? | Currently unknown, and the brief's guess (item names, dialogue, quest text) is an inference from a false premise. Once one key is found, one decode answers it. |
| Does the server send the key with a string reference? | Directly relevant to R2. Look for a string16 field in a GAME_SMSG whose contents parse as a coded string with a parameter pair, against our own captures. |
| Is the 12th language row (23 files, language tag 17) also this format? | `studies/datwrite/FINDINGS.md` records it as unaddressable by the shipped PE table. The record walk should still apply. |
| What is `StringHeader`'s `+5` byte? | Zero in all 101,376 language-0 records. Probably padding; the decoder never reads it. Not worth chasing until something is non-zero. |
| Are the three dead skill rows really dead? | All stats zero and `linked_id == 3443` with 3,443 rows, so it indexes one past the end. Consistent, not proven. Cross-check against the wiki's skill list. |
