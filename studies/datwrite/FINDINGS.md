# Can we write Gw.dat, or hook around it?

Seven reading tracks against the shipped client, the archive, and 21 mirrored
prior-art repositories, each then adversarially re-verified by a second reader who
re-derived every disassembly, re-ran every corpus scan, and re-opened every cited
file. This document records what survived. Where a verifier refuted a track, the
refutation wins and the original claim is not reinstated.

No client was launched. `C:\gw` was read and never written. No ArenaNet bytes
entered the repo; everything below describes and cites, and pastes nothing.

Skills are the worked example throughout, because they are the hardest case: a
skill needs a PE row, two `Gw.dat` text records and two `Gw.dat` textures, and the
prior study concluded all four were out of reach.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | We checked real bytes on this machine ourselves — the archive, the PE, or our own captures. |
| **CLIENT-DATA** | Read out of the shipped client by a third-party tool whose code we read. Somebody else's reading of a primary artifact. |
| **UPSTREAM** | A reimplementation's code says so, and a verifier confirmed the line. A reconstruction, not a fact about retail. |
| **RECONSTRUCTION** | The source signals it is guessing, or the reasoning is ours from measured parts. |
| **CONTESTED** | Sources disagree and this document does not pick a winner. |
| **UNVERIFIED** | Claimed, and the verifier could not confirm it. Do not build on it. |
| **NOT FOUND** | We looked and there is no answer in what we have. |

Nothing here is OBSERVED in the sense `studies/skills/FINDINGS.md` uses it: no
client was run, so no claim about what the client *displays* has been watched.

**The lineage rule still binds.** "ldufr" (OpenTyria, Headquarter) and "GWCA"
(GregLando113, JaborGW, gwdevhub/GWToolboxpp) share an author and count as **one
witness** — a verifier confirmed this from git history this pass: 444 of
JaborGW/GWCA's commits are Laurent Dufresne's, and GWToolboxpp and Headquarter
share committers. Two further collapses found this pass: `gw-preservation/server`
and `gw-preservation/fileserver-utils` are the same GitHub identity, and
Fournux/Tyria-Extractor's own `README.md:209-217` credits GWToolbox++/GWCA as an
input — so Fournux is a separate author but **not clean-room** for client
structures.

---

## The answer in one page

**Yes, `Gw.dat` can be written.** Every rule a writer must satisfy is now measured
against real bytes, and each one was reproduced against the client's own code that
enforces it:

- the file header's `+0x0C` word is CRC-32/ISO-HDLC over the **first 12 bytes
  only**, verified three independent ways;
- each MFT entry's `+0x14` word is CRC-32/ISO-HDLC over that file's **stored**
  (still-compressed) bytes, verified on 3,000 random rows and against the client's
  own write-side computation;
- the MFT's own CRC is `crc32(mft[0x00:0x48])` continued over
  `mft[0x60 : count*24]` — skipping its own 24-byte self-entry — reproduced
  byte-exactly on **two different archives** with different values;
- the complete list of invariants the loader checks at open is disassembled and
  every one holds on the real file.

There is no third-party writer anywhere in the evidence base — the prior study's
narrow claim survives, and I checked it again from a different angle. But the
reason that mattered has evaporated: **the client itself is a full allocating
storage manager**, it rewrote 27 MFT rows in a single caged session, and we can
now reproduce every checksum it computes.

**But writing `Gw.dat` is not the answer to the skill question, and it is not the
first thing to do.** Three findings reorder the problem:

1. **The description is already fixable with no dat write at all.** GWToolbox's
   `GmTipSkill` hook is production code that intercepts the encoded string the
   client is about to hand the tooltip's body frame, blanks it, and appends its
   own. Replacing it wholesale is the same call. The client's encoded-string
   grammar has a literal escape (`\x108\x107<UTF-16>\x1`) that renders arbitrary
   text with no string record in the archive.
2. **No append is needed for text.** The prior study assumed a new skill name
   means growing a text file. It does not: **678 string ids are empty plain
   records in all eleven languages simultaneously**, in contiguous runs of up to
   329 (`string_id` 81476..81804). Those are unallocated slots waiting to be
   filled, not space that has to be made.
3. **The icon is the unsolved half, and it is unsolved on every route.** Nothing
   in the entire evidence base makes the game's own skillbar draw a texture that
   is not already in `Gw.dat`, and the dat route into it is blocked on a
   mip-chain framing nobody has reversed and on `DXTL`, an ArenaNet fourcc with no
   DirectX equivalent that 3,292 of 3,439 skill icons use.

**What still blocks us, in one sentence each.**

- **Durability is the decisive unknown and it is genuinely unanswered.** The
  client relocates rows, its free-space list is not persisted (it is rederived
  from the entry table at every open), and we do not know whether a botched write
  is recoverable — the "Repairing corrupt archive" rescan was located but not
  followed to completion, so we cannot say whether it can rebuild the
  fileId→mftIndex map or whether it is a one-way door.
- **We have no compression-8 encoder.** This bullet also used to argue we did not
  understand the format, on the evidence that our decompressor failed on 12 of
  1,089 text files with a huffman table hole. **That evidence is withdrawn as of
  2026-08-06** — the hole was a zero-length code that both reference
  implementations drop on the floor, and all 1,089 files now decompress and tile
  exactly (§2). The encoder is still missing; the argument against our
  understanding is not.
- **A genuinely new skill id still needs a PE patch**, and it is harder than the
  prior study thought: all 3,443 rows are populated, the table base is referenced
  by **nine** relocated absolute addresses across three base constants plus a
  row-count immediate, and the table's tail abuts ArenaNet's own
  `P:\Code\Gw\Const\ConstSkill.cpp` and `index < arrsize(s_skill)` strings — so
  appending in place overwrites the anchor every scanner uses to find the array.

**Recommended route: static PE patch + side-hook first; direct dat write second;
the wire for everything that is not a skill.** The PE patch gets every stat and
the icon/name/description *pointers*; the hook gets authored description text
today; the dat write is the only thing that gets authored *art* and authored
*name* text, and it should not be attempted until the durability experiment below
has run.

---

## The routes, compared

Five ways in. What each can and cannot deliver for one skill:

| | name | description | icon | stats | genuinely new id |
|---|---|---|---|---|---|
| **1. Write `Gw.dat` directly** | authored, once a codec or a stored-row rewrite works | authored, same | authored art — **blocked** on the mip chain and on `DXTL` | no (stats are in the PE) | no on its own |
| **2. Client writes it for us via the file-server path** | no | no | no | no | no |
| **3. Side-hook / injected DLL** | **untried** — no skill-name hook exists anywhere | **PROVEN** in production | **untried** — best candidate is hooking the client's own dat read | yes, by patching the row in memory | no |
| **4. Static PE patch** | borrowed only (repoint at an existing string id) | borrowed only | borrowed only (repoint at an existing dat file id) | **yes, all of it** | yes in principle — nine relocations |
| **5. The wire, unmodified client** | no | no | no | no | no |

Two combinations are worth naming because they are what a plan would actually be:

- **Route 4 + Route 3** delivers correct stats and an authored description with no
  archive write at all, reversibly, today. The name and the icon stay wrong.
- **Route 4 + Route 1** delivers everything except the icon, and inherits the
  whole durability question.

### Route 1 — write the archive directly

**Feasible; the mechanism is fully measured.** Every checksum reproduces, every
load-time invariant is known, and the allocator's behaviour is disassembled.

What it cannot do: touch a skill's stats, which live in the PE and not the
archive. What blocks it in practice: no compression-8 encoder, and for the icon
case an unreversed container.

**Two costs the prior thinking overstated, both arithmetic errors caught this
pass.** MEASURED: `entry[2]` (the fileId→mftIndex table) is 1,368,200 bytes, which
rounds up to 2,673 × 512 = 1,368,576 — leaving **376 spare bytes inside its own
extent, room for 47 more 8-byte pairs**. The MFT itself is 4,256,208 bytes
rounding to 4,256,256, leaving 48 bytes = **2 more 24-byte rows**. So adding the
first new file id forces no reallocation at all. And the MFT has 14,719,024 bytes
of contiguous headroom above it (613,292 rows' worth) before the next allocated
entry, so even growing it properly is not the wall it looked like.

### Route 2 — get the client to write it for us

**Not viable for new content, and possibly not reachable at all.** This is the
weakest of the five and the evidence for it got worse under verification.

- gw-preservation's file service implements hello, initial-data (a seven-`u32`
  manifest), loading-status and heartbeat, and **has no handler for the
  file-request opcode** — the request falls through to "unhandled message"
  (`fileservice/conn.go:103-113`). Its `fileservice` package is the only one in
  that server with no `*_test.go`. There is no known-good response to imitate.
  UPSTREAM.
- Every client-side reimplementation shows **client-initiated pull only**. Nothing
  anywhere shows the client can be made to request a file id it was not already
  going to ask for. So "push new content" may be structurally impossible on this
  channel even if it works perfectly.
- **CONTESTED — is the legacy TCP:6112 file service still live in a 2026 build?**
  `jean-humann/gwnative/src/net.rs:13-15` carries the comment "6112 is the Guild
  Wars game/login port; 80 and 443 cover the file and web services", which reads
  as *dead*; the same file at `:109-119` and its accepted-destination test at
  `:417` treat `File7.ArenaNetworks.com:6112` as a legitimate destination in an
  August-2026 codebase, which reads as *live*. Separately,
  `gw-preservation/fileserver-utils` is an **operated** tool — a retriever, a
  scraper and a Discord manifest-watcher pointed at "the official file servers"
  (`README.md:3,7,9`) — which is the strongest evidence in the vault that the
  channel answered real requests. This document does not pick a winner.
- **A claim from this pass that must not be carried forward.** An earlier reading
  held that our own 12 caged captures show zero connections to
  `file*.arenanetworks.com` and therefore the protocol is dead. REFUTED twice:
  seven of the twelve capture files contain **no endpoint events at all**, and
  `toolkit/clientpatch/launch_caged.ps1:12-17` records in this repo's own words
  that a firewall-blocked `connect()` "fails immediately rather than
  black-holing it, so the socket never reaches SYN_SENT and never appears in a
  sample… Zero sockets looked like evidence AGAINST the firewall. It was not."
  The sampler is also a 200 ms poll that breaks out after ~1–8 seconds. Absence
  here is not evidence of absence.

The one genuinely useful fact this route contributes: **the checksum the file
server sends is a different quantity from the MFT crc.** MEASURED at
`Gw.exe 0x7d78fb-0x7d791e`: it is CRC-32 over the file data *continued over the
4-byte little-endian fileId*. Anyone confusing the two will get a working local
edit and a failing download, or vice versa.

### Route 3 — side-hook / injected DLL

**The strongest short-term route for text, and the only untried route to a new
icon that does not touch the archive.**

- **Description: PROVEN.** GWToolbox hooks the client's `GmTipSkill` description
  routine (anchored on the assertion string `GmTipSkill.cpp` /
  `"No valid case for switch variable 'm_powerType'"`), takes the child frame
  `0xb`, sends `L"\x101"` to blank it, calls the original, then appends its own
  literal encoded string — and it really does `CreateHook`, unlike two other hooks
  in the same codebase that turned out to be dead code. UPSTREAM, and both anchor
  strings are MEASURED present exactly once in our own `Gw.exe`.
- **Name: untried, and there is no adjacent proof.** The `GmTipSkill` hook reaches
  the description body only. The item name/description hook that *is*
  production-proven works on a different function whose signature literally hands
  out `wchar_t** out_name, wchar_t** out_desc`; there is no skill-side equivalent
  in the evidence base.
- **The deepest seam, untried by anyone: the text-record decoder.**
  Fournux/Tyria-Extractor installs a trampoline on the function that turns a raw
  `Gw.dat` text record into decoded UTF-16 — signature
  `fn(context, record_bytes, substitute_start, substitute_end) -> *const u16`, 9
  bytes stolen. MEASURED on our own binary: its byte pattern hits exactly once, at
  a function starting **VA 0x007cb000**, whose first 9 bytes are exactly three
  whole instructions, so the steal is instruction-aligned. Tyria only *reads*
  there. Substituting would make **all** game text authorable — skill names, item
  names, dialogue — with zero archive writes. Nobody has tried, and whether the
  client tolerates a substituted output pointer (versus requiring an in-place
  write into its own buffer at `context+0x170`, count of `u16`s at `+0x178`) is
  NOT FOUND.
- **Icon: untried.** Py4GW resolves the client's own file layer
  (`OpenFileByFileId`, `GetRecObjectBytes`, `DecodeImage`, `AllocateImage`,
  `Depalletize`) and calls those functions; nobody hooks them. All four anchor
  literals are MEASURED present in our binary. If `GetRecObjectBytes` were hooked
  to return our own ATEX buffer for a chosen file id, the client's own texture
  pipeline would decode our art with no archive write. UNVERIFIED.
- **REFUTED, do not build on it:** GWToolbox does *not* hook `SetTooltip` (it only
  reads a pointer at `+0x9` from the located function), and it no longer calls
  `RequestFiles` at all — commit `1ad8f56b`, "refactor(dat): read from disk only;
  drop all game-streaming machinery", removed the whole mechanism. Upstream tried
  the client-streaming route and deliberately abandoned it.
- **Posture cost is near zero; engineering cost is not.** MEASURED: `Gw.exe`
  delay-loads `steam_api.dll`, `libEGL.dll`, `libGLESv2.dll` and `OpenAL32.dll`,
  and the run dir already carries `OpenAL32.dll` and `steam_api.dll` — so a
  forwarding shim beside the exe loads by the client's own name resolution with
  **no binary patch**. But any hook is a C++ or Rust artifact with its own
  toolchain, against a toolkit that is Python-3-stdlib-only. That is a real scope
  increase.

### Route 4 — static PE patch

**The route we already own.** `toolkit/clientpatch/make_custom_client.py` already
signature-scans and byte-patches a copy of `Gw.exe`, including into `.rdata` (the
DH struct at RVA 0x6910d8) — the same class of operation as rewriting a skill row
at RVA 0x588ed0.

MEASURED, and independently by two tracks from two different sources, which is
the strongest single corroboration in this study:

- The skill constant table sits at **`.rdata` RVA 0x588ed0 / VA 0x988ed0 / file
  offset 0x587ed0**, **3,443 rows of stride 0xA4**, `skill_id` strictly sequential
  0..3442, with the row after the last not continuing the sequence.
- Track 5 measured it in `vault/run/2026-07-29_221c13772c7a/Gw.exe`. Track 4
  measured it in the PE **extracted from `Gw.dat` file id 4102**, at the same file
  offset, with the same 3,443 count and the same row-5 field values
  (`icon=54986 name=24805 concise=59517 desc=24806`). Two tracks, two sources, one
  answer.
- Two further witnesses in the binary that the reading is right, neither of which
  our own decoder could force: the bytes immediately after the last row are
  ArenaNet's own source path `P:\Code\Gw\Const\ConstSkill.cpp`, and the row count
  is also a code immediate — `mov esi, 0xD73` (= 3443) at VA 0x5a8623, seven bytes
  after the `mov eax, 0x988ed0` at 0x5a861d.

What it delivers: **every stat**. Energy, adrenaline, cast, aftercast, recharge,
attribute, profession, type, elite flag, the rank-0/rank-15 scaling shown in the
tooltip, and the animation ids. All of it is a field of a 164-byte row in a file
we already patch.

What it cannot deliver alone: authored *content*. Repointing `name` at another
skill's string id gives borrowed text; repointing `icon_file_id` at another dat
file gives a re-skin. To author, this route must be combined with route 1 or
route 3.

**Relocating or extending the table is harder than a two-byte patch.** REFUTED
this pass by parsing `.reloc` (140,862 HIGHLOW entries) rather than grepping
`.text` for a literal: **nine** relocated absolute values land inside the table's
span, using three base constants — `0x988ed0` at VA 0x5a861d and 0x5a88db;
`0x988ee0` (base + 0x10, the `special` field) at 0x5a8a0f, 0x5a8a1f, 0x5a8a2a,
0x5a8a40; and `0x988efa` (base + 0x2a) at 0x5a8a5d, 0x5a8a68, 0x5a8a76. Add the
row-count immediate and the tail collision with ArenaNet's own assertion strings,
and this is a careful patch, not a trivial one. *The relocation table is the right
instrument for any "how many places reference this address" question and should
become the standard tool for it in this repo.*

### Route 5 — the wire, with a completely unmodified client

**Delivers nothing for a skill, and a great deal for everything else.**

MEASURED: **not one skill-related message carries a string16.** All fifteen
GAME_SMSG opcodes whose upstream name contains "SKILL" (0x001D, 0x0064, 0x0065,
0x00D9–0x00DC, 0x00E0–0x00E6, 0x0154) carry only agent ids, bare skill ids,
dwords and id arrays. The skill's name, description and icon are read by the
client from its own PE row and its own archive, and never appear on the wire. This
is exactly where the wire route stops, and it confirms `studies/skills/FINDINGS.md`
§5's table by a fourth method.

What it *does* deliver is worth recording because it is large and it is available
now: the client's encoded-string grammar has a literal escape, and a **server**
can emit it.

- **CORROBORATED (ldufr grammar × Fournux client capture).** A faithful port of
  GWCA's `EncStr_Validate` accepts **1,409 of 1,409** encoded strings captured at
  a live client's own decoder boundary, landing exactly on the terminator every
  time; a deliberately incomplete port of the same walker rejects 530. A check
  that could fail, and did not.
- Three server lineages with three different authors (ldufr/OpenTyria in C,
  GameRevision/GWLP-R in Java, gw-preservation in Go) all build the identical
  framing `0x0108, 0x0107, <UTF-16>, 0x0001`.
- MEASURED on this machine: **Rurik's codec already encodes it with no code
  change.** `GAME_SMSG 0x005D` carrying that sequence round-trips byte-exactly.
  **82 of the 87 string16-carrying GAME_SMSGs are buildable today**; the 5 that
  refuse (0x0160, 0x0161, 0x0162, 0x0192, 0x019D) all fail on one unimplemented
  `nested_struct` field, whose element layout turns out to already be in our own
  schema.

Three cautions, all of which would have bitten:

- **`0x0003 CONCAT_LITERAL` at top level is the documented crash case, not a
  fallback.** GWCA's validator skips the control-character read on the first loop
  iteration and then demands a value word, so a string beginning `0x0003` fails
  outright — and the source comment says the client's own validator accepts a
  leading control character "but that later crashes string decoding". Encodability
  by our codec says nothing about it.
- **Several attractive-looking candidate fields are `string16(8)`** —
  `QUEST_ADD` (0x0049), `QUEST_GENERAL_INFO` (0x0050), `CHAT_MESSAGE_NPC`
  (0x005F). After the mandatory 3 words of framing that leaves five characters.
  They are sized for encoded references, not text.
- **Opcode numbers drift by −1 against gw-preservation** in 35 of 40
  discriminating cases, including `0x009B`. Use ours: they are the ones arbitrated
  against build 38797's own message tables, and Fournux's live-client sniffer
  independently agrees with us at 0x009B, 0x0161 and 0x0162.

---

## What is now MEASURED about the archive write path

All of this is new since `studies/mapdata/FORMAT.md`, and all of it was re-derived
by a second reader from the binary and the bytes.

### The file header

```
+0x00  u32  magic       0x1A4E4133
+0x04  u32  headerSize  must be >= 0x20; is 0x20
+0x08  u32  blockSize   power of two <= 0x10000; is 512
+0x0C  u32  crc         CRC-32/ISO-HDLC over bytes 0x00..0x0C ONLY
+0x10  u64  mftOffset
+0x18  u32  mftSize
+0x1C  u32  flags       bit1 = modification in progress
```

The `+0x0C` field has **three independent witnesses**: the read gate at
`Gw.exe 0x47b6cd` (`push 0xc; push esi; push 0; call CrcUpdate` then
`cmp [esi+0xc], eax`), the **archive-creation writer** at `0x47a3a4-0x47a3c6`
which CRCs exactly `0xC` bytes before storing to `[edi+0xc]`, and byte agreement
on two different archives (`0x4CCBAD70` in both `C:\gw\Gw.dat` and
`vault/dat_study/Gw.dat`). Control: CRCing the first 4/8/12/16/20/24/28/32 bytes,
**only N=12 matches**.

`CrcUpdate` is at `Gw.exe 0x4716a0`, signature `(u32 crc, const void* data, u32
bytes)`, reflected CRC-32/ISO-HDLC with its 1 KiB table at VA 0x93d8a0 — all 256
entries rebuilt in Python and compared, identical. Semantically it is
`zlib.crc32(data, crc)`. The non-reflected 0x04C11DB7 table is absent from the
file. 17 call sites.

Note the crash-safety design: the client sets `flags` bit1 and rewrites the
**16 bytes at file offset 0x10..0x20** before mutating — deliberately outside the
CRC's 12-byte span, so the dirty flag costs no checksum update.

### The MFT entry, with ArenaNet's own field names

```
+0x00  u64  alloc.offset      always blockSize-aligned
+0x08  u32  alloc.size        the exact byte length; the extent is rounded up
+0x0C  u16  alloc.extraBytes  (our toolkit calls this "compression")
+0x0E  u16  alloc.flags       bit0 FLAG_ENTRY_USED, bit1 FLAG_FIRST_STREAM
+0x10  u32  alloc.nextStream  (our toolkit calls this "counter")
+0x14  u32  alloc.crc
```

The names are ArenaNet's, recovered from its own assertion strings compiled into
the PE: `extraBytes <= size` at VA 0x93f2fc, `curr->alloc.nextStream < count` at
0x93f0b8, `FLAG_ENTRY_USED` and `FLAG_FIRST_STREAM` at several sites,
`IsFixedLocation`, `size > offsetToFirstFile`, `firstMftIndex >= INDEX_FIRST_FILE`,
`descriptor.descriptor.signature == SIGNATURE`. The whole archive layer is
`P:\Code\Base\Rtl\Exe\ExeArchive.cpp`; CRC is `P:\Code\Base\Rtl\Crc.cpp`;
compression is `P:\Code\Base\Compress\{CmpApi,CmpDict,CmpHuff}.cpp`. There is **no
literal `Gw.dat` string anywhere in the exe** — the filename is composed from
`.dat`/`.exe`/`.snapshot` suffixes, and the table is identified only by the
numeric signature `0x1A74664D`.

**`nextStream` is a perfect corpus-wide bijection**, and this is a check the
artifact could easily have refuted. Exactly 44,700 entries are USED-but-not-
FIRST_STREAM; exactly 44,700 entries carry a nonzero in-range `+0x10`; the two
sets are mutually subset with no target referenced twice; min target 18, max
177,341. At a finer grain: all 21,420 `flags=1` rows with a nonzero link point at
a `flags=2817` row, injectively, and every one of the 21,420 `flags=2817` rows is
targeted exactly once.

**`extraBytes` remains only half understood.** MEASURED: the histogram is
`{0: 38633, 8: 138708}`, and 400 random rows with `extraBytes==0` all begin with a
plain container magic (380 `ffna`, 20 `ATEX`) while 400 random rows with
`extraBytes==8` all carry `0x0102` at bytes 2..4 and none begins with a plain
magic. ArenaNet's name and the assert `extraBytes <= size` are certain; whether it
counts a prefix, a suffix or padding is **NOT FOUND**. Do not read our toolkit's
"compression" label as ArenaNet's intent.

### The entry CRC — and the client verifies it

**The `+0x14` word is CRC-32/ISO-HDLC over the STORED bytes** — the compressed
form on disk, not the decompressed payload. Evidence, four ways:

- 177,327 of 177,329 non-empty rows match across the whole archive. The two
  exceptions are self-referential: row 1 (the 32-byte file header, which stores
  crc 0 because `IsFixedLocation` forbids a nonzero one) and row 3 (the MFT, which
  cannot checksum itself while being written).
- An independent 3,000-row random sample: 3,000/3,000, split 674 uncompressed /
  2,326 compressed — both classes clean.
- The client's **write side**: `Gw.exe 0x479c22` CRCs the buffer about to be
  written and hands the result straight to `SetEntry`.
- The client's **read side**: `ExeFile.cpp 0x474bfb-0x474c2c` computes CRC-32 over
  the stored bytes it just read and compares against the value the archive layer
  copied out of the MFT entry; on mismatch it zeroes the byte count and sets an
  error flag, which the stream layer surfaces as `File 0x%x stream 0x%x is
  corrupt` (VA 0x93eb40). A stored crc of **0 disables the check for that entry**,
  and zero USED entries with size>0 carry crc 0, so shipped data never exercises
  that state.

The enclosing function's own asserts name the codes — `ExeFile.cpp:131
(code == NOTIFY_FILE_READ) || (code == NOTIFY_FILE_WRITE)`, `:132`, `:133` — which
proves the CRC path is the *read*-completion path and that write completion skips
it.

### The MFT's own CRC

`crc = CRC32(mft[0x00:0x48])` continued over `mft[0x60 : count*24]`. Bytes
0x48..0x60 — entry index 3, the MFT's self-entry — are skipped because they are
what is being written. Guarded by the assert `INDEX_MFT < m_entryArray.Count()`
(`ExeArchive.cpp:1480`).

Reproduced on **two different archives with different values**: `9bffd25c` for the
study copy's 177,342-entry table, `f35761c3` for the install copy's 177,335-entry
table. Controls that must not match and do not: whole-MFT crc `12494021`,
zero-filled-entry-3 `022fbfab`, from-0x18 `e7b37cf0`.

### What the loader checks at open

In order, all at `ArchiveOpen 0x47b650` and `LoadMft 0x47c160`: header magic,
`headerSize >= 0x20`, `blockSize` power-of-two and `<= 0xFFFF`, the 12-byte header
CRC, `mftSize % 24 == 0`, `count >= 16`, `mftOffset + mftSize <= file size`,
descriptor signature `0x1A74664D`, `descriptor[+8] == 0`, `descriptor[+0xC] ==
count`, entries 1/2/3 all USED, `entry[1].offset == 0 && entry[1].size == 0x20`,
`entry[3]` describing the MFT, the MFT self-CRC, every entry's offset
blockSize-aligned and `offset+size` within the file, every `nextStream` link in
`[16, count)` and acyclic (genuine Floyd tortoise/hare), then the fileId table
(entry 2) with `extraBytes == 0`, `size % 8 == 0` and its own CRC.

Any failure logs **"Repairing corrupt archive"** (VA 0x93f428) and triggers a full
rescan of the 4 GB file in 1 MiB blocks. Whether that rescan can rebuild the
fileId→mftIndex mapping is **NOT FOUND**, and it is the single most important
open question in this study.

MEASURED on the real file: all of these invariants hold, and 177,329 of 177,329
non-empty USED entries are 512-byte aligned while only 1,082 have sizes that are
512-multiples — confirming `size` is the exact byte length and the extent is the
rounded-up one.

### The reserved slots

MFT indices 0..15 are reserved and fixed: **0** = the descriptor (not an entry at
all — its `+0x08` word is a zero field, not a size), **1** = the 32-byte file
header (offset 0, size 32, crc 0), **2** = the fileId→mftIndex table, **3** = the
MFT itself, **4..15** = twelve unused reserved slots. `INDEX_FIRST_FILE = 16`,
`offsetToFirstFile = 0x180`.

This explains, and corrects, an earlier reading: the "12 rows with size==0" are
not erased slots, they are the reserved header block. MEASURED: entries 4..15 are
all size 0 / flags 0, and they are the only size-0 rows apart from index 0.

### The allocator

`AllocSpace` (`0x478c50`) rounds the request up to `blockSize` and searches a
free-extent structure keyed by size at `archive+0x34`; on a miss it bumps a `u64`
end-of-file cursor at `archive+0x08`. A hit is removed from both the by-size index
and a by-offset index at `archive+0x50`, and the remainder is split and
reinserted. `FreeSpace` (`0x47b500`) coalesces. **There is no compaction,
defragmentation or scavenge code** — those words do not occur anywhere in the
binary.

**Crucially, the free list is not persisted.** The header describes only
`mftOffset`/`mftSize`/`flags`, and MFT rows carry no free-extent records, so free
space is rederived from the entry table at every open. That is what makes a
third-party writer possible at all: we do not have to maintain a structure the
client will read back.

MEASURED on the study copy: 98.0% of the file is allocated; 85,261,813 bytes free
across 176,248 fragmented regions; the MFT ends at 0xF8FFEFD0 and the next
allocated entry starts at 0xF9E08800, giving 14,719,024 bytes of contiguous
headroom.

### The `flags` vocabulary, and what is still unexplained

MEASURED, exhaustive over all 177,342 rows of the study copy:

| flags | count | extraBytes split | content, sampled |
|---|---|---|---|
| `0x0003` | 110,852 | 0: 22,188 / 8: 88,664 | mixed — ATEX all fourccs, `ffna` type 8, **MPEG-1 Layer III audio**, `AMAT`, the file header |
| `0x0001` | 21,769 | 8: 21,769 | `ffna` Model (21,420) + map stage-2 payloads (349) |
| `0x0203` | 21,421 | 0: 1 / 8: 21,420 | `ffna` Model (standard layout) |
| `0x0B01` | 21,420 | 0: 16,188 / 8: 5,232 | `ffna` — the small reference-stub class |
| `0x0101` | 1,118 | 0: 1 / 8: 1,117 | ATEX DXT3 (599 of 600 sampled; one 24-byte outlier) |
| `0x0C01` | 393 | 0: 236 / 8: 157 | ATEX DXTA |
| `0x0103` | 349 | 8: 349 | `ffna` Map — confirms `FORMAT.md`'s map claim |
| `0xFF03` | 7 | 0: 7 | a pre-sized cache/scratch slot class — see below |
| `0x0000` | 12 | 0: 12 | the reserved slots 4..15 |

Two results here are new and load-bearing.

**Audio lives in `Gw.dat`, and this is an identification, not a sniff.** Walking
the MPEG-1 Layer III frame chain with the real bitrate/sample-rate tables consumes
the payload to **100.0% of its length with an integral frame count** on every
entry tested (e.g. 196 frames / 84,672 of 84,672 bytes). A wrong hypothesis
desyncs within a frame or two. Two independent lineages already documented this
(Jonathan-Greve/GuildWarsMapBrowser's `AnimationSoundManager.h:21` "Raw MP3 data
from DAT"; Fournux/Tyria-Extractor's `dat.rs` unit test case "MP3 frame sound"),
and an earlier claim that nobody had is **REFUTED**.

**`flags` does not decompose into two independent bytes.** `FORMAT.md`'s
"high byte is the stream, low byte is the entry flags" is CONTESTED: the low byte
is genuinely `FLAG_ENTRY_USED | FLAG_FIRST_STREAM` per ArenaNet's own asserts, but
the high byte is unexplained by them, and the observed values are 0x00, 0x01,
0x02, 0x0B, 0x0C and 0xFF. A separate lineage (Jonathan-Greve/GuildWarsMapBrowser
`GWUnpacker.h:55-66`, gwdevhub `GwDatModule.h:88`) reads it as "this entry's
stream number within its file". **A writer that copies `flags` verbatim is safe
either way**; a writer that synthesises one is not.

### What the client wrote during one caged session

This is the durability evidence, and it is the most alarming section of the study.

MEASURED, full MFT diff of `C:\gw\Gw.dat` (177,335 entries) against the run-dir
copy (177,342) after one session: **27 rows differ**, not 7.

- **7 appended** (177335–177341).
- **12 pre-existing `flags=0xFF03` rows consumed** (177320–177331), contiguous,
  every one stored before and huffman after. That class had **19** rows in the
  install copy and **7** in the study copy — 63% of it went in one run. It behaves
  like a pre-sized, pre-allocated cache/scratch pool.
- **1 zero-size slot filled** (35301) — and notably *not* the contiguous low block
  at rows 4–15, which is never touched, refuting any "lowest free row first"
  allocator.
- **2 pre-existing ordinary rows repurposed** (11957, 177254).
- **3 unrelated rows touched** (8315, 8316, 8317).
- **Row 2** (the fileId table) **relocated** 0xF77B6000 → 0x35335600 despite being
  exactly the same size (1,368,200 bytes) in both copies.
- **Row 3** (the MFT) **grew in place** by exactly 7 × 24 = 168 bytes and did
  **not** move — `mftOffset` is 0xF8BEFE00 in both copies, because 4,256,040 and
  4,256,208 both round into the same 8,313-block extent.

The file did not grow: both copies are 4,198,489,600 bytes. The client reused free
space.

**REFUTED, and worth stating because it was an appealing story:** "SetEntry always
frees then allocates, so entries 2 and 3 relocate on every flush". Entry 3 grew
across 168 flushes and stayed put; entry 2 kept its exact size and moved. The
honest statement is **entries 2 and 3 MAY relocate on any flush, and any offset we
record is valid only against the exact copy we measured**.

What the client actually wrote: five identical instances of a three-layer object.
A `flags=515` root (2,452 bytes, standard `ffna` model layout, all five
byte-identical) → via `nextStream` → a `flags=1` "Other"-format model (fixed
2,077-byte geometry, 8-byte metadata, 14-byte texture-filename stub, 112-byte
animation chunk, all byte-identical across instances, with only an inline 64×64
DXT3 ATEX texture differing) → via `nextStream` → a 73-byte `flags=2817` reference
stub, byte-identical in all five places. **The root rows are file-id addressable
and their ids already existed in the install copy**, so this is the client
refreshing content into pre-reserved slots, not minting new addressable files.

Because our loopback server never shipped asset bytes and the cage blocks all
non-loopback traffic, this content was **not downloaded**. Whether it was
generated from nothing or derived/transcoded from other archive content is
**RECONSTRUCTION** either way and the two are not distinguished by anything
measured.

**One more durability signal nobody has pulled on.** Only 29 of 171,025 file ids
in the install copy have bit 31 set, and 25 in the study copy. This session
cleared bit 31 on two of them **in place, at the same table slot**, retargeting
each from an old row to a freshly filled cache row, and zeroed two aliases. A
~29-member set of file ids the client itself rewrites looks like a
stale/needs-refresh watchlist, and for a study about durability it is the single
most interesting thing in the diff.

---

## What each route would actually require, in dependency order

### Route 1: our own archive writer

1. **Decide same-length-in-place vs. reallocate.** In-place is dramatically
   cheaper: no allocator, no offset change, no fileId-table change. Only two
   words change — the entry's `+0x14` crc and `entry[3]`'s `+0x14` crc.
2. **Reallocation, if needed**, requires implementing enough of `AllocSpace` to
   pick a legal free extent: round to 512, find a fitting free region (rederived
   from the entry table, since the free list is not persisted), split the
   remainder, write blockSize-aligned. `FreeSpace` on the old extent is optional
   for correctness because the free list is rederived — but leaving it out leaks
   space permanently across sessions.
3. **Adding a new file id** means writing an 8-byte pair into `entry[2]` and
   recomputing its crc. MEASURED: 47 pairs fit inside its existing extent, so the
   first 47 additions force no relocation.
4. **Never violate**: offsets 512-aligned; `offset+size` within the file;
   `nextStream` links `>= 16`, `< count`, acyclic; `entry[1]` fixed at offset 0 /
   size 32 / crc 0; `descriptor[+0xC] == count == mftSize/24`; header `flags`
   bit1 clear on exit (MEASURED: it is already 0x00000000 in both copies, so there
   is nothing to clear on a cold edit).
5. **Only then** worry about compression. Stored (`extraBytes == 0`) sidesteps the
   codec entirely — but see the blocker on class precedent below.

### Route 3: a hook DLL

1. Build a forwarding shim for `OpenAL32.dll` (delay-loaded, present in the run
   dir, no binary patch needed) — or accept a remote-thread injector.
2. Re-derive every anchor from our own binary with `toolkit/gwpe.py` rather than
   transcribing GWCA's. This is feasible: one track did 16 anchors in an
   afternoon, and it also sidesteps GWCA's licence, which is **MIT-minus-
   distribution** (grant reads "use, copy, modify, and/or merge" and deliberately
   omits "publish, distribute, sublicense, and/or sell").
3. Prefer **assertion-string anchors**. MEASURED survival against our build:
   assertion 71/75 (94.7%), string 28/30 (93.3%), unbounded raw byte patterns
   71/79 clean (89.9%), with 5 more matching in multiple places. Not one anchor on
   the text/tooltip/dat path is broken. Three of the *public* GWCA forks' raw
   patterns are already dead against this build.
4. Hook the description first (proven), then the text-record decoder at
   VA 0x007cb000 (the decisive experiment for text), then `GetRecObjectBytes` (the
   only untried route to a genuinely new icon).

### Route 4: the PE patch

1. Patch stats in the existing row — trivial, and we already have the tooling.
2. To repoint text or art, write the new string id / file id into `+0x98`,
   `+0x9C`, `+0xA0`, `+0x8C`, `+0x90`, `+0x94`.
3. To extend the table: patch all **nine** relocated references, the
   `mov esi, 0xD73` row-count immediate, and relocate the table away from the
   `ConstSkill.cpp` / `arrsize(s_skill)` strings it currently abuts.

---

## The blockers, ranked

**1. Durability. We can write it; we do not know it stays written.** This is the
decisive question and nothing in this study answers it.

- The client is a full allocating writer and it touched 27 rows in one session,
  including relocating the fileId table and consuming 63% of a slot class.
- The free list is rederived at every open, so the client's allocator will happily
  hand out any extent we vacate — and any extent it thinks we vacated.
- **NOT FOUND: whether a botched write is recoverable.** The "Repairing corrupt
  archive" entry point and its 1 MiB rescan loop were located but not followed to
  completion. If the rescan cannot rebuild the fileId→mftIndex map, a bad write is
  a one-way door and the vault copy must be re-cut from `C:\gw`.
- **The one piece of good news, and it needs checking.** In that 27-row diff the
  client touched no text row we know of and no ordinary skill-icon row. But three
  of the touched rows — **8315, 8316, 8317** — sit in the same MFT neighbourhood
  as the text-resource band (confirmed text files at rows 6167..8172, and the
  file-index-98 text files at rows 8295..8305). **Whether 8315–8317 are text rows
  was never checked, and it is the cheapest thing in this document to check.** If
  they are, in-place text editing is in direct contention with the client.

**2. No compression-8 encoder, and an incomplete decompressor.** Every one of the
1,077 real text files and all 223 DDS entries ship compressed. `toolkit/mapdata/
gwdat.py` has `decompress()` and nothing else; a grep across all 21 mirrors finds
no encoder anywhere. The stored fallback is real but its precedent is
class-specific: MEASURED, `flags=1` is **100% compression-8 with zero stored
examples in the whole archive**, as is `flags=259`; `flags=515` is 21,420:1 and
`flags=257` is 1,117:1. Stored is only common in `flags=3` (22,188 of 110,852) and
`flags=2817` (16,188 of 21,420). Text records live in `flags=3`, which is the good
case; **the flags class of skill-icon rows was never measured, and it should be
before anyone plans an icon write.**

The decompressor half of this is **RESOLVED, 2026-08-06.** It raised
"zero-length code (table hole)" on 12 of the 1,089 text files, and this section
read that as evidence we did not understand the format. The real cause was
narrower and more useful: a Huffman table holding a single symbol encodes it in
**zero bits**, `build_table` parks that symbol at `follow_root[0]`, and both the
Go reference and `xentax.cpp` begin code assignment at length 1 and never read it
back — so the table comes out completely empty. It is a defect in both upstream
lineages, not in the port. Go has no guard for it and silently fills the block
with a constant byte from a bit position that never advances; our port raised,
which is the only reason it was found.

With the symbol installed, **all 1,089 text files decompress and every one splits
into exactly 1,024 records that tile the blob, ending in the predicted
(language, file) tail.** All 349 maps and a strided archive sample are unchanged,
because the fix only runs where the old code raised. See
`toolkit/mapdata/test_gwdat.py`. The encoder is still missing — but the specific
evidence cited here for "we do not understand the format" no longer stands.

**3. The icon, on every route.** The dat route needs the ATEX container, and it is
a **mip chain**, not a single image. MEASURED with predictions stated in advance:
the header's `+12` word equals `8 + blocks × block_bytes` in 60/60 samples (0/40
on a compressed control), while the payload is always strictly longer; the next
level's `data_size` sits at offset `12 + data_size` in 85/85 (control 1/85). The
sub-level framing does not close to EOF under any simple stride and is **NOT
FOUND**. Meanwhile 3,292 of 3,439 skill icons are **`DXTL`**, an ArenaNet fourcc
with no DirectX equivalent, so "author a plain uncompressed DDS instead" takes a
loader branch that no real skill icon takes — and all 223 DDS entries ship with
compression 8, so even that has no stored precedent. The hook route (hooking
`GetRecObjectBytes`) is the only clean answer and nobody has tried it.

**4. The skill name.** The description is fixable today; the name is not. The
`GmTipSkill` hook reaches child frame `0xb` only, no source anywhere writes a
skill tooltip's *name*, and no skill-side equivalent of the item
`out_name`/`out_desc` hook exists. Reaching it means either a dat write into one
of the 678 empty slots plus a PE repoint, or the untried text-record-decoder
substitution.

**5. A genuinely new id is a nine-relocation PE patch.** All 3,443 rows populated;
no spare slots; nine relocated absolute references across three base constants;
one row-count immediate; and the table's tail abuts the very assertion string
every scanner uses to find it.

**6. Native code.** Any hook is a C++/Rust artifact with its own toolchain, CI and
crash surface inside the game process, against a Python-stdlib-only toolkit. The
posture cost is near zero (delay-loaded shim, no binary patch); the engineering
cost is not.

**7. Provenance.** Signature constants and, more so, quoted assertion strings like
`"No valid case for switch variable 'm_powerType'"` are literal excerpts of
ArenaNet's binary. `toolkit/clientpatch/make_custom_client.py:46-66` already
embeds three byte signatures, so precedent exists — but assertion strings are
longer, more expressive quotations and **this needs an explicit owner ruling
before dozens land in the repo**. Mitigation: every anchor used in this pass was
re-derived from the owner's own binary with `toolkit/gwpe.py`, so we can generate
our own rather than transcribe GWCA's — which we must do anyway, because GWCA's
licence forbids redistribution.

---

## Corrections to our own documents

Recorded rather than quietly overwritten, per house style.

### `studies/mapdata/FORMAT.md`

**Line 99-100 currently says:**

> `crc` is **NOT FOUND**. GWUnpacker calls it CRC, OpenTyria calls it checksum,
> neither computes or verifies it, and no polynomial was tested. Do not assume.

**Replace with:** the u32 at entry+0x14 is **CRC-32/ISO-HDLC over the STORED
bytes** — `zlib.crc32` of the on-disk, still-compressed form. MEASURED four ways:
177,327 of 177,329 non-empty rows (the two exceptions self-referential), an
independent 3,000-row sample at 3,000/3,000 across both compression classes, the
client's own write-side computation at `Gw.exe 0x479c22`, and the client's own
read-side verification at `ExeFile.cpp 0x474bfb`. **The client checks it on every
read** and logs `File 0x%x stream 0x%x is corrupt` on mismatch. A stored value of
0 disables the check for that entry.

**Line 101 currently says:**

> The header field at 0x0C is likewise unexplained by every source and by us.

**Replace with:** it is **CRC-32/ISO-HDLC over the first 12 bytes only**. Three
witnesses: the read gate at `0x47b6cd`, the archive-creation writer at
`0x47a3a4-0x47a3c6` which CRCs exactly `0xC` bytes, and byte agreement
(`0x4CCBAD70`) on two different archives — with a control showing only N=12
matches. Note also gwdevhub's `GwDatModule.h:70` already named this field `crc1`;
the earlier "unexplained by every source" was a search failure, not an absence.

**Line 94-95 currently says:**

> Entry layout, 24 bytes: `offset u64, size u32, compression u16, flags u16,
> counter u32, crc u32`.

**Replace with:** ArenaNet's own names, recovered from its assertion strings, are
`offset u64, size u32, extraBytes u16, flags u16, nextStream u32, crc u32`. Our
"compression" is `extraBytes` and is only half understood; our "counter" is
`nextStream` and is a **link to another MFT row** — a perfect corpus-wide
injective bijection. Note this document already calls the same field `next` at
line 153; the repo names one field two ways and should unify on `nextStream`.

**Line 97-98 currently says:**

> Compression is 0 (stored) or 8 (huffman/LZ77). Tally across the whole archive:
> **{0: 38633, 8: 138708}**, reproduced independently by our own reader.

**Correction:** the tally is right and reproduces exactly, but it sums to 177,341
against a 177,342-row table. The missing row is index 0, the `Mft\x1a` descriptor,
which is not an entry at all — its `+0x0C` word is `0xB4BE` parsed as a size. State
the exclusion rather than dropping it silently.

**Line 149-150 currently says:**

> The high byte is the stream (1, which carries maps) and the low byte is the
> entry flags (3).

**Mark CONTESTED.** The low byte is confirmed: bit0 `FLAG_ENTRY_USED`, bit1
`FLAG_FIRST_STREAM`, from ArenaNet's own asserts. The high byte is **not**
explained by any of them; observed values are 0x00, 0x01, 0x02, 0x0B, 0x0C, 0xFF,
and a separate lineage reads it as a per-file stream number. The `flags=259` →
maps result stands (349/349, 100% in sample).

**Line 382, open-questions table:**

> | What is the u32 at entry+0x14? | Test CRC polynomials against known payloads.
> Nobody has. |

**Answered.** Remove the row; see above.

**Line 103-109, "Two archives are not the same archive"** — stands, and is now
much better characterised: **27** rows differ across one session, not 7, and the
list of what moved is above. The warning that raw MFT row indices are only
meaningful against the copy they were measured on is, if anything, understated.

### `studies/skills/FINDINGS.md` §5

**Lines 856-861 currently say:**

> **The blocker is step 2 and step 3, and it is concrete: neither mirrored dat
> tool can write.** Tyria-Extractor and GuildWarsMapBrowser both open the archive
> strictly read-only. There is no repack, no MFT insert and no hash-row insert
> anywhere in either codebase. Writing to `Gw.dat` is not a demonstrated
> capability in our entire evidence base — it is unexplored territory, not a
> solved problem someone else has tooling for.

**The narrow claim survives; the conclusion does not.** No mirror opens a live
`Gw.dat` and edits an entry in place — re-checked two ways, and two of the best
proofs are new (`ldufr__OpenTyria/code/FaArchive.c:84` is `fopen(path, "rb")` and
is the archive module's *only* file-open;
`Jonathan-Greve__GuildWarsMapBrowser/SourceFiles/draw_hex_editor_panel.cpp:11`
sets `mem_edit.ReadOnly = true`). But:

- **`Gw.dat` writing is no longer unexplored territory.** Every checksum rule and
  every load-time invariant is now measured against the client's own code, and the
  client itself is a full allocating writer whose behaviour we have diffed.
- **The evidence base is not as empty as stated.**
  `Fournux__Tyria-Extractor/src/tests.rs:45-231` builds a byte-valid synthetic
  archive from scratch — file header, MFT header, 24-byte MFT rows — and its own
  reader parses it back. It is a unit-test fixture generator with fabricated CRCs,
  so it would not survive the real client; but it is readable, MIT-licensed
  starting material and it is where a writer should start.
- **An adjacent claim from this pass must not be carried forward.** "GWCA's
  archive knowledge is zero" is REFUTED: `gwdevhub__GWToolboxpp/GWToolboxdll/
  Modules/GwDatModule.h` is a full `Gw.dat` reader that memory-maps the client's
  archive, declares a `#pragma pack(1)` 24-byte `MftEntry` with a `static_assert`,
  and at line 90 already names `+0x10` "slot index of the next stream in the
  file's chain". That NOT FOUND came from searching an index of PE-address scan
  anchors, which by construction could never contain a file-format parser.

**Step 2 (lines 845-847) currently says:**

> **Add name and description records to a `Gw.dat` text file** at
> `(string_id / 1024, string_id % 1024)`, for as many of the 11 languages as you
> care about — and update the 1,089-pointer language table in the PE if the target
> text file does not already exist.

**Replace with: you do not need to add records, and you do not need to touch the
language table.** MEASURED at population scale, not sampled — the 11 × 99 pointer
table was located structurally in our own client's PE at **VA 0xbf0210** (which
matches Fournux's stated address for the 2026-07-26 client, upgrading that claim
from UPSTREAM to MEASURED), all 1,089 pointers decode, and 1,077 resolve:

- Every one of the 1,077 files holds **exactly 1,024 records**, then exactly 2
  trailing bytes. Record-count histogram `{1024: 1077}`, remainder histogram
  `{2: 1077}`. No file has spare capacity — the ceiling is real.
- Those 2 trailing bytes are **`(language_index, file_index)`** — the file names
  itself. Predicted before testing, 1,077/1,077, zero misses. An earlier reading
  called them an unexplained non-constant.
- **7,459 of 300,789 plain records have a zero-length payload**, and **678
  `(file_index, record_index)` slots are empty in all eleven languages
  simultaneously**, with only 1 slot of 99,328 empty in some-but-not-all. They come
  in contiguous runs: file 79 records 580..908 (**329 slots, string ids
  81476..81804**), 306..419 (114), 204..296 (93), 122..189 (68); file 97 records
  970..1023 (54). Internal check: 678 × 11 + 1 = 7,459, matching the independent
  per-record count exactly.
- **Editing is cheap in principle**: there is no offset or index table — records
  are located by cumulative walk — so a same-length replacement leaves every later
  record where it was. Only the entry's own crc and the MFT self-crc change.
- **And blocked in practice**: all 1,077 text files use compression 8, and we have
  no encoder. Flipping the row to stored is the escape hatch, and it is cheaper
  than previously thought — MEASURED, the decompressed/stored ratio is median
  **1.18×**, aggregate 1.36×, with only 5.2% of files reaching 4×. The earlier
  "roughly 4x-10x growth" figure was wrong, and was computed partly from a row its
  own author had already rejected as a false positive.

Two honest caveats: cross-language emptiness is strong evidence a slot is
unallocated, **not proof** it is unreferenced by every live table; and a twelfth
language row exists in the archive (23 files carrying language tag 17, file
indices 52..74) that the shipped PE table cannot address, so the eleven-language
picture is not the whole archive.

**Step 3 (lines 848-853) currently says:**

> **Add ATEX/ATTX icon textures to `Gw.dat`** and wire their file numbers into the
> row. This means producing the container: 4-byte magic, FourCC, dimensions,
> data-range size, subcode bitfield, then the bitstream and planar tail — ATEX
> stores undecoded block components in separate planes rather than complete DXT
> blocks.

**Partly right, and the correction cuts both ways.** MEASURED header, over 150
corpus entries: `+0` `ATEX`; `+4` fourcc (`DXT1`/`DXT3`/`DXT5`/`DXTA`/`DXTL`/
`DXTN`); `+8` width `u16`; `+10` height `u16`; `+12` `u32` == `payload_len - 12`,
a **size** (150/150); `+16` `u32` taking only the values 10 and 4 with dimensions
held constant — an unidentified discriminator, and specifically **not** a mip
count (a 64×64 texture has at most 7 levels).

- **Better than stated:** the bitstream does not have to be authored. Setting the
  inner `compression_code` to 0 falls through to a raw planar read — and this is
  not a deduction from Rust source, it **ships**: 2,909 of 52,274 ATEX entries in
  retail carry a `compression_code` with none of bits 1/2/4/8 set, spanning every
  fourcc and 4×4 up to 512×512.
- **Worse than stated:** a real ATEX file is a **mip chain**, and its sub-level
  framing is NOT FOUND (see blocker 3). And 3,292 of 3,439 skill icons are
  `DXTL`, which has no DirectX equivalent, so the DDS shortcut does not apply to
  the skill-icon slot.

**Lines 800-804 currently say:**

> **The consequence worth stating out loud:** a re-skinned skill's tooltip will
> lie. The client renders the *shipped* description from its own table… That is a
> design constraint on re-skinning, not a technical obstacle.

**No longer a hard constraint for the description.** GWToolbox's `GmTipSkill` hook
is production code that blanks and replaces the tooltip body, and the client's
encoded-string grammar has a literal escape that renders arbitrary text with no
archive record. A re-skinned skill's **description** can tell the truth today, via
a DLL, with no archive write and no PE patch. The **name** and the **icon** still
lie, and no proven mechanism changes either.

**Line 881, the summary table:**

> | Tooling we have | all of it | PE patching only; **no dat writer exists
> anywhere** |

**Replace the right-hand cell with:** PE patching; a measured, reproducible
archive-write ruleset; MIT-licensed synthetic-archive construction code to start
from; a proven text-substitution hook. Still missing: a compression-8 encoder, an
ATEX mip-chain writer, and any answer at all on durability.

**Line 1078, open questions:**

> | Can `Gw.dat` be written at all? | No tool in our evidence base can. This gates
> the entire "new skill id" project and is unexplored. |

**Answered in the mechanism, open in the durability.** Replace with the question
that actually gates the project: *does a hand-written entry survive a play
session, and is a botched write recoverable?*

**Line 1079:**

> | Is the dat's file 4102 the same image as the `Gw.exe` we run? | Compare
> hashes. |

**Narrowed, not closed.** MEASURED: dat file id 4102 decompresses to a
10,483,904-byte MZ/PE32 image, image base 0x400000, 5 sections — the same size as
`C:\gw\Gw.exe`. Two tracks independently located the skill table at the **same
file offset 0x587ed0** with the **same 3,443 count** and the **same row-5 field
values** in the dat-extracted image and in the run-dir `Gw.exe`. That is the same
build, near-certainly the same image; the direct hash comparison was still not
run.

**One more §1 item this pass moves.** The CONTESTED question at lines 279-286 —
which of `+0x90` and `+0x94` is the high-resolution icon — is **narrowed in
Tyria-Extractor's favour**: MEASURED, `+0x8C` resolves to a real ATEX in
3,439/3,439 rows and is exactly 64×64 in 3,438 of them, while `+0x90` resolves to
ATEX and is exactly 128×128 in 3,426. `+0x94` was not measured, so GWCA's
`icon_file_id_hi_res` naming is not yet refuted — but `+0x90` is empirically the
hi-res slot.

**A tension, not a correction.** §3 line 710-713 says "Ids run 0..3442 … with 405
unused slots scattered through the range". Two tracks measured **all 3,443 rows
populated** (3,443 distinct name string ids, zero fully-empty rows, `id` == row
index throughout). "Unused" in the source probably means *not a player skill*
rather than *empty*; the two counts are not directly comparable and the §3 wording
invites the wrong reading.

### `toolkit/clientpatch/make_custom_client.py`

Not a study document, but it carries the exact error this project rules against.
Lines 45-46 justify `SIG_KEYS` with: *"Used identically by Headquarter's reader and
OpenTyria's writer -- two independent implementations that agree."* **Headquarter
and OpenTyria are both ldufr.** That is one witness counted twice, in a
load-bearing comment in our own patcher, and it should be fixed.

---

## The recommended first experiment

**Prediction stated before the result**, per the house rule.

### What to run

A **same-length in-place overwrite of one existing archive entry**, on a scratch
copy, judged by the client's own log — run as **three arms with three different
predicted outcomes**, so that silence in one arm is not the only possible result.

Preparation, common to all arms: re-cut the scratch copy from
`C:\gd\Rurik\vault\dat_study\Gw.dat` for **each** attempt. A caged run mutates the
archive; the two copies we compared already differ by 168 modification-counter
ticks from ordinary play. Pick an entry with index ≥ 16, `flags == 3`
(USED|FIRST_STREAM), `extraBytes == 0` (stored), and a small size. The header
`flags` word is already `0x00000000` in both copies, so there is nothing to clear.

**Arm A — correct write.** Overwrite the entry's stored bytes with the same number
of modified bytes at the same offset, write `zlib.crc32` of the new bytes into that
entry's `+0x14`, then recompute the MFT self-crc as
`crc32(mft[0:0x48])` continued over `mft[0x60 : count*24]` and write it into
`entry[3]`'s `+0x14`. Touch nothing else — not the header, not the fileId table,
no offset.

> **PREDICTION:** the caged client opens the archive with **no
> `Repairing corrupt archive` line in `Gw.log`**, and serves the modified bytes.
> The only three read-time gates on this path are the header crc (untouched, and
> it covers only bytes 0..12), the MFT self-crc (recomputed) and that file's own
> entry crc (recomputed).

**Arm B — deliberately wrong entry crc, correct MFT self-crc.** Same edit, but
store a crc that is off by one.

> **PREDICTION:** the archive still opens cleanly — the entry crc is checked at
> *read completion*, not at open — and when that file is read the client logs
> **`File 0x%x stream 0x%x is corrupt`** naming that file id. This arm is the
> positive control: it is what turns Arm A's silence into evidence.
>
> **Caveat, stated up front:** Arm B is only informative if the client actually
> reads that file during the session. If nothing logs, we have learned nothing
> about the CRC and only that the file was not touched. Choose a target we can
> independently show is read (a map or UI texture loaded at spawn), and if in
> doubt run Arm B before Arm A.

**Arm C — deliberately wrong MFT self-crc.** Run **last**, on an expendable copy,
after the vault copy has been re-cut from `C:\gw`.

> **PREDICTION:** the client logs **`Repairing corrupt archive`** at open and
> begins a full 1 MiB-block rescan of the 4 GB file. What we are actually watching
> for is what happens *after* the rescan: whether file ids still resolve. This arm
> is the only cheap way to answer the study's top open question — **is a botched
> write a one-way door?** — and it is the reason to run it at all.

### Why this and not something else

- It is the load-bearing claim of the whole write route reduced to one
  observation, and it is refutable in three directions.
- Cost: one file copy, ~30 lines of Python, one caged client launch per arm, and
  the oracle is a single grep of `Gw.log`.
- A pure-offline pre-flight — re-running the loader's invariants in Python — is
  cheaper still, but it is our own decoder forcing the answer true. Run it as a
  smoke test, never as the experiment.

### The free pre-flight to run first

Before any of the above, spend ten minutes on this, because it costs nothing and
it can invalidate the whole in-place-text plan:

> **Are MFT rows 8315, 8316 and 8317 text-resource rows?** They are three of the
> 27 rows the client rewrote in one caged session, and they sit in the same
> neighbourhood as confirmed text files (rows 6167..8172) and the file-index-98
> text files (8295..8305).
>
> **PREDICTION:** they are **not** text files — the other 24 touched rows are all
> models, textures and cache slots, and the 11 × 99 table's resolved rows are a
> known set that can simply be checked for membership. If the prediction is
> **wrong** and any of the three is a text row, then the client rewrites text rows
> during ordinary play, in-place text editing is in direct contention with it, and
> the text plan needs a different target class before anything else proceeds.

### And after that

If Arm A holds, the next experiment is the one that decides whether the archive
route is needed at all: **a trampoline on the text-record decoder at VA 0x007cb000
rewriting the output for one known string id**, predicting that all text bearing
that id changes everywhere in the game at once. If that works, the entire text
half of the skill problem is solved with no archive write, permanently and
reversibly, and route 1 narrows to the icon alone.

---

## Open questions

| Question | What would answer it |
|---|---|
| **Does a hand-written entry survive a play session?** | Write one, play, diff. The decisive question and nothing here answers it. |
| **Can the "Repairing corrupt archive" rescan rebuild the fileId→mftIndex map?** | Follow the rescan at `Gw.exe 0x47b7e2` to completion, or run Arm C on an expendable copy. Decides whether a bad write is recoverable. |
| Are MFT rows 8315–8317 text rows? | Ten-minute set-membership check against the 1,077 resolved text rows. Gates the in-place text plan. |
| Which `flags` class do skill-icon rows carry, and does that class ever ship stored? | Resolve the 3,439 icon file ids to MFT rows and histogram their flags and `extraBytes`. Decides whether the stored escape hatch exists for icons. |
| How is an ATEX mip chain framed below the first level? | No simple stride closes it to EOF and the smallest levels use a shorter record. Needs the client's own decoder read, not more corpus fitting. |
| Can a compression-8 encoder be written at all with stdlib Python? | Nobody has tried. The prerequisite this row named — "our decompressor fails on 12 of 1,089 text files with a huffman table hole" — is **done, 2026-08-06**: the hole was a zero-length code that both reference implementations drop, and all 1,089 files now decompress and tile. |
| Are any of the 678 all-empty string ids genuinely unreferenced by every live table? | Cross-language emptiness is strong evidence, not proof. Cross-reference every skill, item, npc, quest and UI table that can hold a string id. |
| Can the text-record decoder's output be **substituted**, or only observed? | Hook VA 0x007cb000 and try returning a different pointer. Tyria only reads there; nobody has written. |
| Does hooking `GetRecObjectBytes` feed the game's own texture pipeline? | The only untried route to a genuinely new in-game icon. Py4GW calls those functions; nobody hooks them. |
| Is the skill tooltip's **title** reachable from any hook? | `GmTipSkill` reaches child frame `0xb` (the body) only. Enumerate the tooltip's other child frames with a running client. |
| Is the legacy TCP:6112 file service still live in a 2026 build? | CONTESTED. A loopback listener that **accepts** on 6112 (a blocked connect never appears in a sample — see `launch_caged.ps1:12-17`), with the redirect covering file1..file12 and no early break. |
| What is the ~29-entry bit-31 file-id watchlist? | The client cleared bit 31 on two of them in place in one session. A second session's diff would characterise it, and it is a durability signal. |
| What does `extraBytes` actually count — prefix, suffix, or padding? | ArenaNet's name and `extraBytes <= size` are certain; the semantics are not. |
| What is the ATEX header's `+16` word, which takes only 10 and 4 with dimensions held constant? | Not a mip count. No mirrored source reads it. |
| What is the `flags` high byte? | Unexplained by ArenaNet's own asserts; one lineage reads it as a stream number. A writer that copies it verbatim is safe either way. |
| Does the `-repair` command line do what its string suggests? | UNVERIFIED — the string is present, the argument parser was never read. |

The shape of this document is the inverse of the prior study's. `studies/skills/
FINDINGS.md` concluded that writing `Gw.dat` was the unexplored blocker. It is now
the best-measured surface in the project — every checksum, every invariant, the
allocator, the flush protocol — and the blocker has moved one level up, to a
question no amount of reading can settle: **whether what we write stays written.**
That is an experiment, and it costs one caged launch.

---

## Appendix: measurements made alongside the tracks, and one error corrected

The seven tracks above ran in parallel with direct measurement against the archive
and the PE. Most of it converged — two independent routes reaching the 376 spare
bytes in the file-id table's extent, the 14,719,024-byte MFT headroom, the skill
table at `.rdata` RVA `0x588ed0` with 3,443 rows, and its tail abutting
`ConstSkill.cpp`. What follows is what did **not** appear above, plus a mistake
worth recording.

### The error, recorded rather than overwritten

Measurement here concluded that MFT row 3 — the table describing itself — carried
a checksum that **no rule reproduced**; therefore that it was "stale by
construction"; therefore that the client had been loading an archive failing its
own checksum on every launch; therefore that **the crc was not a gate on load**.

Every step after the first was wrong, and the chain ran in a convenient direction:
it concluded that the thing standing between us and writing the archive did not
really matter.

The rule exists, and Track 1 found it by disassembly:

```
crc32(mft[0x00:0x48]) continued over mft[0x60 : count*24]
```

— the table with its own 24-byte self-entry removed from the stream. The search
here had tried zeroing row 3's crc field and zeroing the whole row, but never
*removing* the row. Re-checked against both archives, on two different stored
values: **it reproduces exactly.** The file header's `+0x0C` word likewise
reproduces as CRC-32 over its first 12 bytes.

**The correct position is the less convenient one: the archive is fully
self-checking, nothing in it fails its own checksum, and a writer must maintain
all three.** `toolkit/mapdata/test_datcrc.py` asserted the false version and
*passed*, because "row 3's crc is not crc32(the whole table)" is true and
meaningless — a check that could not fail, which is the exact failure mode
`CLAUDE.md` warns about. It now asserts the real rules.

### Allocator rules a writer must obey — MEASURED

| Rule | Evidence |
|---|---|
| Offsets are **512-byte aligned** | all 177,329 non-empty rows; the **GCD of every offset is exactly 512**, so 512 is the granularity and not merely a divisor of it |
| Space is reserved in **whole blocks**, size rounded up | 176,033 of 177,329 entries sit exactly that far from their neighbour |
| No two entries share storage | zero overlapping extents |
| Erased rows (`size == 0`) | 12, at rows 4–15, contiguous — **but see below** |

**Count free space in blocks, not bytes.** By bytes the archive looks like it has
85,261,813 free. It does not: 52,733,429 of that is dead space *inside* entries'
own block reservations and cannot hold a new file. Counted in whole blocks the
gap between reservations is **32,528,384 bytes in 214 runs**, of which 12 runs are
64 KB or larger, totalling 30,822,912.

**And that figure is still nine times too big — CORRECTED 2026-08-10.** The
paragraph above called 32,528,384 "the real figure". It is not: it is the same
mistake one level down. The gap-between-reservations measure asks only whether an
MFT row points at a block, and the client's **containers do not answer to that
question**. It rotates its MFT and its file-id table between a small set of
recurring slots — writing the new generation into one, leaving the previous
generation intact in the other — and the previous generation is pointed at by no
row, so it reads as free.

MEASURED on `vault/dat_study/Gw.dat`. **Six of the 214 runs carry a container
signature, and they hold 29,160,448 of the 32,528,384 bytes — 89.6%.** Each of
the five largest begins with one: three shadow MFTs (`0xF8FFF000`, `0xF57D5000`,
`0xF8699A00`), a **byte-for-byte** copy of the live file-id table (`0xF77B6000`,
zero bytes differing over 1,368,200), and a near-copy (`0xF8290400`, 171 bytes
differing). 58.2% of the bytes inside the 214 runs are non-zero.

Two details that a head-of-run check would miss, and both are load-bearing:

- **The largest run is a container arena, not a container.** `0xF8FFF000` is
  14,718,976 bytes holding *three whole MFT generations laid end to end* followed
  by file-id table generations — and the tiling is exact, not approximate. Each
  header declares 177,342 entries = 8,313 blocks, and the next header sits at
  precisely +8313, the third at +16626, and the id-table stretch begins at
  +24939 = 3 × 8313. Three predictions that could each have missed and did not.
  This slot is not incidentally occupied; it is where the table lives.
- **One container hides 428 blocks into its run.** `0xF6772800` (374,784 bytes)
  opens with ordinary stale data and only then a file-id table generation, so a
  head-only test hands the run to a writer. It is the sixth run, and the reason
  `scan_run()` checks every block boundary rather than the first.

Genuinely unclaimed space is **3,367,936 bytes in 208 runs, largest 953,856** —
and that is the number that changes what a writer can plan, because the median
reservation of the 349 map-flagged (`flags == 259`) rows is **961,536**, just
above it. **176 of the 349 map heads are larger than the largest run a writer
could now place them in.** Relocating a map is therefore not a matter of finding
room; for half the maps in the archive there is no room, and an insert has to
grow the file or reclaim genuinely dead extents.

`datplan.py` placed every insert at the head of the largest run, so it aimed at
the shadow MFT at `0xF8FFF000` every time; it applies nothing, so nothing was
damaged. It is best fit over withheld-run classification now, and
`toolkit/mapdata/test_datplan.py` pins both.

**And `0xF8FFF000` is not hypothetical — the rotation is visible across the three
copies of the archive on this machine.** `vault/dat_study/Gw.dat` (177,342 rows)
and `vault/run/2026-07-29_221c13772c7a/Gw.dat` (177,476) both keep the live MFT at
`0xF8BEFE00`; `vault/run/2026-07-29_221c13772c7a-probe/Gw.dat` (177,335) keeps it
at `0xF8FFF000`. Two slots, three copies, and whichever one is not in use holds
the previous generation and reads as free.

The same measure is wrong in a second place, and it was worth chasing: the plan's
"the MFT can grow in place" note bounded itself by the next *allocated* entry and
reported **613,292 rows** of headroom for `dat_study`. The next 14 MB past the
table is the container arena, so the honest figure is **2 rows** — 48 bytes.

**Rows 4–15 are reserved, not available.** They are erased in *both* archives and
stayed that way, while the client — needing a slot — took **row 35301**, the only
other erased row in the file, reaching past twelve nearer ones. Twelve zeroed rows
sitting immediately after the three container rows, which a working allocator
declines to use, are reserved. `toolkit/mapdata/datplan.py` claimed row 4 in its
first version; that was a plausible-looking wrong answer and is now excluded.

### What an insert actually costs — `toolkit/mapdata/datplan.py`

Committed as a **planner**: it computes the byte-level edit and applies nothing.
Separating "is the edit computable" from "does the client accept it" is the point.
The first is now settled; the second is what the experiment above is for.

For a new 4,096-byte addressable file: **7 edits, 4,184 bytes** — the payload into
a free block run, one appended MFT row, the MFT header's entry count, the file
header's MFT size, MFT row 3 (the table restating its own size), MFT row 2, and
one 8-byte `(file_id, row)` pair appended inside the file-id table's existing
extent.

The id space is not a constraint: 171,025 pairs occupy a range spanning
`0 .. 2,147,870,504`, and unused ids start at **4**.

### The three icon fields, across all 3,443 rows

| Field | Non-zero | Distinct | Range |
|---|---|---|---|
| `+0x8c` | 3,439 | 1,981 | 12,394 .. 388,755 |
| `+0x90` | 3,438 | 1,981 | 265,290 .. 388,759 |
| `+0x94` | **86** | 73 | 265,641 .. 279,135 |

`+0x8c` and `+0x90` map **strictly one-to-one** — 1,981 distinct values each, zero
many-to-one in either direction — with near-disjoint bands: 1,384 of `+0x8c`'s
values fall below `+0x90`'s minimum. Two encodings of one icon, the second added
later, which supports Tyria-Extractor's reading that `+0x90` is the hi-res slot.

`+0x94` is populated in 86 rows across **65 non-contiguous runs**, spanning every
profession, campaign and equip-type in the table. It is neither GWCA's universal
`icon_file_id_hi_res` nor Tyria-Extractor's undocumented nothing. Its purpose is
**NOT FOUND**. *A prediction that these 86 rows would form a coherent group was
stated in advance and refuted.*

**A new skill needs two icon files, not one.**

### Where skill strings live

Names and full descriptions span **67 distinct text files** (18, then 24–97 with
gaps) — busiest file 25 (494 records), 24 (443), 26 (374). Concise descriptions
occupy a different, smaller set of **33** files — busiest file 59 (932), 58 (715),
74 (519). Record indices reach 1023. All 3,443 rows carry all three ids and none
is blank, so no row can be repurposed invisibly. `desc == name + 1` in 3,353 of
3,443 rows (97.4%), so a donor skill for any experiment should be chosen from a
row where the pair is genuinely consecutive.

### The command-line table, re-derived

`PLAN.md` §1.5b records "a contiguous, alphabetically sorted 41-entry argument
table at file offset `0x005371cc`" on an earlier build. On ours the flags are
**UTF-16, not ASCII**, in a block at `0x0054212C..0x00542398`, and there are again
exactly **41**:

```
authsrv autologin bmp character diag dsound email exit fps fqdn lodfull image
log map mce mock mute nofqdn nopatchui noshaders nosound noui oldfov fmod
password perf port portal portaldll prefresetlocal repair resetmap sndasio
sndfastbuf sndwinmm sai stress uisizenormal uninstall update windowed
```

It is *nearly* sorted — `lodfull` precedes `image`, and `fmod` follows `oldfov` —
so "alphabetically sorted" should be softened where it appears.

*A prediction that the table would contain a file-server redirect flag, the way
`-authsrv` and `-portal` redirect their own clients, was stated and refuted.*
There is none. Pointing the file client at a server we control would need a
hosts-file or DNS redirect rather than a switch, which is a materially worse
position for Route 2 than a flag would have been.

What the table does contain is **`repair`**, **`update`** and **`nopatchui`** —
the shape of the durability answer. Validation looks like a mode the client is
*asked* to enter.

### The client was not phoning home on our recent launches

`vault/captures/patcher/*.jsonl` records every non-loopback endpoint the client
touches during the uncaged pre-login window. The earliest session (2026-08-05
04:19) caught three — port 443 to a Google-hosted address and port 80 to two EC2
addresses — so the sampler demonstrably works. **The seven most recent sessions
recorded none at all.**

This is evidence, not proof. A sampler can miss a short-lived socket, and this
project has burned itself before by treating an instrument's silence as a finding.
Note also that the sampler only watches the roughly 90 seconds before
`launch_caged.ps1` re-cages; after that the firewall blocks everything regardless.
It points the same way as `repair` being an explicit mode, and it is worth exactly
that much.

### Tooling added by this pass

- `toolkit/mapdata/test_datcrc.py` — asserts all three checksum rules, the
  512-byte alignment, the offset GCD and non-overlap, against the corpus. Strided
  by default; `--full` checks every row.
- `toolkit/mapdata/datplan.py` — computes insert and overwrite plans and applies
  none of them. `--free` reports the block-level free map, the claimable erased
  rows and the file-id table's spare capacity.

---

## Update, same day: the pre-flight ran, and blocker #1 is much smaller than stated

Two checks, both read-only, both cheap. Together they remove most of the durability
blocker this document ranks first — and one of them contradicts a prediction made
here in advance.

### The pre-flight: rows 8315–8317 are not text resources

Blocker #1 flagged this as "the cheapest thing in this document to check": the
client rewrote MFT rows 8315, 8316 and 8317 in one caged session, and they sit
just past the text band, so **if they were text rows, in-place text editing would
be in direct contention with the client.**

**They are not.** MEASURED:

| Row | Stored | Decompressed | What it is |
|---|---|---|---|
| 8315 | 92 B (was 96) | 3,705 B | `ffna` container |
| 8316 | 28 B, `comp=0`, `flags=515` | — | 28 raw bytes, `counter=8318` |
| 8317 | 1,012 B | 3,050 B | **UTF-16LE with BOM, one `[Prefs]` section, 89 lines, 87 `key=value` pairs** |

Row 8317 is the client's own **preferences blob**. It is UTF-16 text, which is why
it sits so close to the localisation band and why it looked alarming, but it is not
a string table. The contrast is unambiguous — a real localisation row (row 7500,
inside the confirmed 6167..8172 band) has **no BOM, no bracketed sections, and 487
embedded NULs**: a NUL-separated record table, a completely different shape. Row
8319, the untouched neighbour, is another BOM-led settings file.

*A prediction was stated here that these three rows would not be text. Half wrong:
8317 IS text, just not the kind that matters.* Worth recording, because "not text"
and "not a localisation resource" are different claims and only the second holds.

**Consequence: the client does not rewrite localisation resources at runtime.**
Writing a skill name into one of the 678 empty string slots is not in contention
with it. The plan stands.

**A bonus that is better than the answer.** Row 8317 has the *same stored size*
(1,012), the *same decompressed size* (3,050) and a *different CRC* in the two
archives. That is the client performing, on itself, exactly the operation this
document's recommended experiment proposes: **a same-length in-place content
rewrite with a recomputed CRC.** The operation is not hypothetical and the format
tolerates it — the only implementation of it we have is ArenaNet's.

### The patched client cannot download, and we did that ourselves

Blocker #1 rests on the client re-fetching assets and reverting our write. **The
client we actually launch cannot fetch anything.** `toolkit/clientpatch/
make_custom_client.py:213-243` already patches `DnSetEnabled`, the only writer of
the BSS global gating the whole download path, so the "disabled" flag is set on
every call; `DnInit()` then returns immediately and `DnRun()` returns 1, which its
caller reads as "patching finished".

MEASURED, comparing the two binaries with `toolkit/gwpe.py`:

| | `C:\gw\Gw.exe` | `vault/run/…/Gw.exe` |
|---|---|---|
| `DnSetEnabled` prologue, unpatched | 1 | **0** |
| `DnSetEnabled` prologue, patched | 0 | **1** |
| `CreateMutexA` guard signature | present | **absent** (patched) |
| mutex name | `AN-Mutex-Window` | **`AN-Futex`** |

This also retires the hedge in the appendix above about the patcher captures. Seven
recent sessions recorded no outbound endpoints not because a sampler got lucky, but
because **the download path is dead in that binary**. Two independent observations
of the same cause.

**What this does and does not settle.**

- **Settled:** the "client re-downloads over our write" risk, for the patched
  client. It has no download path to do it with.
- **Not settled:** whether the client's own *local* allocator relocates or reuses
  an extent we wrote. That is still open, and it is now the whole of blocker #1.
  The evidence narrows it: in one session the client touched its prefs blob, two
  small rows, and appended seven entries — and touched **no** row in the text band
  and **no** skill icon.
- **Newly relevant:** Route 2 (get the client to write it for us via the
  file-server path) is blocked **by our own patch**, not by the client. Reversible
  with `--no-updater-patch`, at the cost of reopening the outbound exposure the
  patch exists to close. That trade should be made deliberately if Route 2 is ever
  wanted.

### Where that leaves the recommended experiment

Arm B (wrong entry CRC → does the client reject it?) is unchanged and still worth
running; the read-side verification at `ExeFile.cpp 0x474bfb` predicts
`File 0x%x stream 0x%x is corrupt`.

Arm C — deliberately corrupting the MFT self-CRC to find out whether "Repairing
corrupt archive" is a one-way door — is **less urgent than it was**, because a
client with no download path cannot repair by re-fetching whatever it decides is
broken. It may still be worth knowing, but it is no longer gating.

---

## Update, same day: Route 4 ran against a real client, and it works

This document recommended "static PE patch + side-hook first; direct dat write
second". The PE patch half has now been executed and observed. Full detail is in
`studies/skills/FINDINGS.md` under **OBSERVED, 2026-08-05**; what matters here:

**Route 4 delivers more than this document credited it with.** The comparison
table above marks name, description and icon as "borrowed only" under Route 4,
with a footnote that borrowing means repointing at an existing string id or dat
file id. That is exactly what was done, and all three borrowed cleanly:

- a skill was given another skill's **name and description** and rendered them;
- a skill was given another skill's **skillbar icon** and rendered it;
- in both cases every *number* — energy, adrenaline, recharge, attribute, and the
  values substituted into the description's placeholders — stayed with the target
  row.

**The icon field this document should have named is `+0x90`, not `+0x8c`.**
Repointing `+0x8c` alone changes nothing on the bar; repointing `+0x90` alone
changes it. Both Tyria-Extractor and GWCA describe `+0x8c` as the standard or
primary icon. Anyone planning an icon write — Route 1 — must target the file id
in `+0x90`, and the ATEX/`DXTL` problem this document ranks as blocker #3 applies
to that file, not to `+0x8c`'s.

**Blocker #4, "the skill name", is smaller than stated.** It says the description
is fixable today but the name is not, and that reaching the name means "either a
dat write into one of the 678 empty slots plus a PE repoint, or the untried
text-record-decoder substitution". A third option was missed and it is the cheap
one: **repoint the name string id at an existing record.** That needs no dat write
and no hook. It cannot produce text no shipped skill contains — but for a
re-skinned skill it is very often enough, and it was never listed.

**What Route 1 is still needed for**, unchanged: text that does not exist anywhere
in the archive, and genuinely new art. Both remain gated on the blockers above,
and the durability experiment is ~~still unrun~~ **armed but not deliverable —
corrected 2026-08-13.** It was armed, byte-verified, reverted and re-armed the same
day this sentence was last true, and nothing wrote it down: `vault/dat_durability/`
holds the tracer, the pre-arm baseline and a full cross-build diff, and
[studies/crossbuild/FINDINGS.md](../crossbuild/FINDINGS.md) is the record plus the
prediction that closes rung 6. What is genuinely open is **delivery** — the tracer
sits on a copy no update can reach, and moving it onto one costs either a search for
an uncompressed row or one broken map. "Unrun" and "armed on the wrong archive" point
at different next actions, which is why the correction is worth the line.

**A correction to this document's own framing.** The comparison table's Route 4
row reads "borrowed only" as though it were a limitation. Against the actual
question — a re-skinned skill whose tooltip lies — borrowing is a solution, not a
compromise: ~1,300 shipped names, descriptions and icons are all addressable by a
4-byte write to a row we already patch. The prior study's conclusion that "a
re-skinned skill's tooltip will lie, because the client renders the shipped text"
is now **false as stated**: the client renders whatever shipped text the row
points at, and the row is ours.

---

# OBSERVED, 2026-08-06: the archive was written to, and the client was watched

Everything above this line was written without modifying a single byte of
`Gw.dat`. This section is the experiment this document spent its whole length
recommending. It is labelled **OBSERVED** — we watched it happen — and where it
contradicts what is above, the observation wins and the earlier text stands for
the record.

Tooling: `toolkit/mapdata/datwrite.py`, the first thing in this project that
opens the archive `r+b`. It refuses any path under `C:\gw`, journals the previous
value of every byte it changes before changing it, and re-checks all three
checksum rules on demand.

Target: `vault/run/2026-07-29_221c13772c7a/Gw.dat`, the copy the caged client
actually opens. Verified clean before the write.

## 1. The experiment that was run, and why it was not the one recommended

The recommended Arm A was a same-length content overwrite of a **stored** entry,
judged by silence in `Gw.log`. Two things argued against running that first.

**`Gw.log` is a weak oracle.** The file carries `Perf:` lines and little else, so
"nothing was logged" could mean the CRC is unchecked, or that the message goes
somewhere we are not looking, or that the file was never read. The document
already flagged the third; the first two are worse because they are silent.

**A cleaner design was available.** Corrupt a row's **crc only, changing zero
content bytes**. The file then decompresses perfectly and the only thing wrong
with it is its checksum, which isolates the crc as a gate with no risk of feeding
the client malformed data. Then pick a target the server can *force* the client
to read — a skillbar icon — and put seven untouched icons beside it as controls
in the same frame.

**Target: MFT row 174325**, which backs file id **383105 = `0x5D881`**, the
`+0x90` skillbar icon of skill 319 (Rush). Bar was `316..323`; slot 4 is the
broken one and slots 1,2,3,5,6,7,8 are controls.

> **PREDICTION, stated before the run.** The read-side verification at
> `ExeFile.cpp 0x474bfb` means slot 4's icon fails to draw while the other seven
> render, and/or `Gw.log` gains a `File 0x%x stream 0x%x is corrupt` line.
> **Refutation:** all eight draw and nothing logs, which would mean the crc is
> not enforced on this path and hand-written edits are cheaper than assumed.

## 2. The entry crc IS a read gate, and it fires on read, not on open

**OBSERVED.** The archive with a deliberately wrong entry crc **opened normally**
— no `Repairing corrupt archive`, no rescan, no delay — and the client walked all
the way to the login screen and into a map. The failure appeared only when the
skillbar drew:

```
Error: File 0x5d881 stream 0x0 is corrupt
Error: Texture '0x05d881' format unrecognized
```

`0x5d881` is 383105, exactly and only the file whose row we broke. The predicted
string appeared **verbatim**, naming the right file, with seven untouched controls
rendering correctly in the same frame.

Both halves matter and they are separate claims:

- **Not an open-time gate.** A bad content write cannot brick the archive at
  startup. The client will load it and run.
- **A read-time gate.** It is checked at read completion and it is enforced. Any
  writer must get the crc right or the file it wrote is refused.

## 3. The failure is scoped, but it is not uniformly graceful

**OBSERVED, from the owner at the screen:** slot 4 rendered **blank**, the other
seven rendered normally, and **the tooltip was completely intact** — "Rush.
Stance. (8 seconds.) You move 25% faster. (Attrib: Strength)". Name, type,
duration and attribute all present on a skill whose art the client had just
refused to load.

**Text and art resolve through independent paths.** The string ids never touch
the archive read that failed. This corroborates §3 of the skills study from the
opposite direction: there, text was borrowed while numbers stayed; here, art was
destroyed while text survived.

**Opening the Skills and Attributes panel then crashed the client — and that was
our fault, not the archive's.** ~~Same texture, different consumer, and that
consumer does not tolerate the failure the skillbar absorbed.~~ **RETRACTED
within the day; see §10.** The crash reproduced with a clean archive and a stock
binary, so it was never about the texture. The corrupt asset degraded gracefully
on every path we exercised.

## 4. The write survived the session — the decisive question, answered

This document's top open question was *"Does a hand-written entry survive a play
session? Write one, play, diff. The decisive question and nothing here answers
it."*

**MEASURED, by diffing a pre-write snapshot of the whole MFT against the archive
after the client exited:**

- **Our corrupted crc was still there.** `0xABC51BFB`, exactly as written.
- **The content bytes were byte-identical** to the pre-write snapshot.
- **The client did not repair it**, despite having detected it, named it in the
  log, and crashed over it.

A write survives. A *bad* write is not auto-repaired — which is the same coin's
other face, and consistent with a binary whose download path we killed ourselves.

## 5. The client recomputed the MFT self-crc, and our rule predicted its output

This is the strongest verification in the study, and it was free.

Five rows changed during the session. Three were the client's own work:

| Row | What the client did |
|---|---|
| MFT header | u32 at **+0x04** ticked 26988 → 26991 |
| 8315 | **relocated** 0x461AA00 → 0x46C9C00 and **resized** 92 → 96 bytes |
| 8316 | **relocated** 0x3983600 → 0x395BE00, size unchanged |
| 3 (the MFT itself) | **recomputed its self-crc** to `0xDB258D15` |

**Our reconstructed rule computes `0xDB258D15`.** So does our entry-crc rule for
the two rows it relocated, both matching what the client wrote.

Why this is different in kind from everything before it: every prior confirmation
of these rules was our decoder reproducing a checksum over bytes ArenaNet shipped.
This is **ArenaNet's own writer producing a checksum over a table state that had
never existed anywhere** — a state *we* manufactured, with our corrupted row
174325 sitting inside the very byte range it checksummed — and our formula
predicting its output exactly. It is the difference between fitting a corpus and
predicting an experiment, and it is the standard `CLAUDE.md` asks for when it says
a check that cannot fail is not a check.

**It also retires the last trace of an error this document used to rest on.** An
earlier pass concluded no rule reproduced row 3's crc, called it "stale by
construction", and read the client's tolerance of it as evidence that crcs go
unchecked. Every step of that was wrong: the rule exists, the client maintains it,
and §2 above shows crcs are very much checked. `toolkit/mapdata/datplan.py` still
carried that claim in its module docstring and in a note it printed on every
plan; both are corrected in this pass.

## 6. The client relocates rows — the remaining durability risk, narrowed

Rows 8315 and 8316 did not merely change, they **moved**, and 8315 grew from 92
to 96 bytes. So the allocator does relocate live entries during ordinary play,
and blocker #1's surviving half — "whether the client's own local allocator
relocates or reuses an extent we wrote" — is **confirmed as a real mechanism**,
not a hypothetical.

What narrows it: both rows are from the scratch/prefs class this document already
identified (8315–8317, characterised in the earlier pre-flight as containers and
the settings blob). Across this session the client touched **no** row in the text
band, **no** skill icon, and **no** content row of any kind. Two sessions now
agree on that.

So the honest position is: relocation happens, it has only ever been observed on
the client's own scratch rows, and a writer should still treat "the row I wrote
is where I left it" as something to re-check rather than assume.

## 7. Two answers on the way past

**Skill icons never ship stored.** Resolving every icon file id in the PE skill
table through the file-id table: **1,981 distinct ids** behind `+0x8c`, `+0x90`
and `+0x94`, and every single one lands on a row with `compression=8, flags=3`.
This closes the open question *"Which flags class do skill-icon rows carry, and
does that class ever ship stored?"* with a **negative**: there is no stored escape
hatch for icons. A new icon needs a compression-8 encoder, or a hook, or nothing.

**But the texture class does ship stored.** Sampling 3,000 of the 22,185 stored
`flags==3` rows: 2,795 `ffna` and **205 `ATEX`**, so roughly 1,500 stored textures
archive-wide. Stored ATEX exists; it is just never a skill icon. Whether any of
them is player-visible is untested and is the obvious way to build a *visible*
Arm A.

## 8. Where this leaves the write route

| Was | Now |
|---|---|
| "No tool in our evidence base can write to `Gw.dat`" | `toolkit/mapdata/datwrite.py`, journalled and reversible |
| Durability: decisive unknown | **A write survives a full session, unrepaired** |
| Does the client validate on read? | **Yes**, at read completion, per-entry, enforced |
| Would a bad write brick the archive? | **No** at open; **yes** it can crash a UI path |
| MFT self-crc rule | Confirmed against **ArenaNet's own writer** on novel state |
| Does the allocator move things? | **Yes**, observed — on scratch rows only, twice |

**The write route is open.** What still gates a genuinely new skill icon is not
the archive — it is the compression-8 encoder and the ATEX mip framing, both
unchanged by this pass. What is no longer in doubt is that if we can produce the
bytes, we can put them in the file, the client will read them, and they will
still be there tomorrow.

## 9. Reproducing this

```bash
python toolkit/mapdata/datwrite.py --dat <copy> --verify
python toolkit/mapdata/datwrite.py --dat <copy> --corrupt-crc 174325
python toolkit/mapdata/datwrite.py --dat <copy> --revert <copy>.journal.json
```

Arms B and C as originally specified are now **partly redundant**: this run was
Arm B in a cleaner form and answered it positively. Arm C — corrupting the MFT
self-crc to find out whether "Repairing corrupt archive" is a one-way door — is
still unrun and is now the only arm left with an unknown outcome, though §5 makes
it less alarming than it was: the client rewrites that field itself, in the
ordinary course of play, using a rule we can compute.

---

## 10. Same day, later: stored content is served, and two things above are wrong

Three results from one more launch. The experiment was cheap because it needed
**no archive write at all**: point a skill row's `+0x90` at a file id that is
already stored, with `repoint_skill.py --set icon2=<file id>`, and see whether
the icon pipeline draws it.

### The compression field is honoured per entry

`compression` is a per-row field, so if the client reads it per row rather than
assuming a class-wide format, **new content can be written stored and the
compression-8 encoder is never needed** — the blocker this document ranks as the
long pole for everything new.

Three slots were repointed at stored (`compression=0`) ATEX files, in two size
classes, with a replicate; five slots left as shipped icons for controls.

| Slot | Skill | `+0x90` → | Stored file | **OBSERVED** |
|---|---|---|---|---|
| 2 | 317 | 8957 | 32×32 DXT1, 348 B | **drew a mouse cursor** |
| 4 | 319 | 248637 | 64×64 DXT1, 280 B | drew faint content |
| 6 | 321 | 252331 | 64×64 DXT1, 280 B | appeared blank |
| 1,3,5,7,8 | — | unchanged | 128×128 DXT1, compressed | drew normally |

**Slot 2 settles it.** A recognisable mouse cursor — an actual UI asset, clearly
not skill art — rendered on the skillbar out of an uncompressed archive entry.
The pipeline read a `compression=0` row and drew what was in it.

Slots 4 and 6 looked empty, and **the log is what distinguishes "empty" from
"rejected"**: §2's genuine failure produced two explicit `Error:` lines naming
the file id. This run produced **none** for either id. The client accepted and
decoded both; 280 bytes for a 64×64 is what near-uniform art compresses to, and
near-uniform art looks like nothing on a dark bar.

*The limit of the claim:* this proves the **archive layer** serves stored
entries. It says nothing about ATEX's own internal compression — those 280-byte
files are heavily compressed *inside* the container — so `DXTL` and the mip
framing remain exactly as blocked as they were. What is removed is the need to
write a Huffman/LZ77 encoder for the archive.

### The panel crash was ours, and §3's reading of it is retracted

§3 concluded that a corrupt asset "degrades gracefully on one path and dies on
another". **Wrong.** The crash reproduced with a clean archive and a stock
binary, and the crash log names the real cause:

```
Assertion: *skill
P:\Code\Gw\Char\Cli\ChCliSkill.cpp(1022)
```

A null **skill** pointer, not a texture. `authsrv.py --unlocks all` set all 4,096
bits of the unlock bitmap, but this build's skill table has **3,443 rows**, so
653 bits named skills that do not exist. The Skills panel walks the unlocked ids
and dereferences each one. Re-running with `--unlocks bar` — eight real ids — the
panel **opened without crashing**, on the same binary and the same archive.

Two lessons, and the second is the expensive one:

- **The corrupt asset was survivable on every path we exercised.** §3's stronger
  claim is withdrawn.
- **Two failures in one session are not one failure.** The texture corruption and
  the panel crash happened minutes apart, so the second was read as a consequence
  of the first. It was an independent bug in *our* server, sitting in the same
  session. A planted fault makes a very tempting explanation for any crash that
  follows it, which is exactly when a control run is worth its cost.

`authsrv.py` now clamps `--unlocks all` to `SKILL_TABLE_ROWS` and refuses an
explicit id past the end of the table, with the assertion text in the comment.

### "Repairing corrupt archive" fired on a clean archive, and was harmless

This launch logged `Repairing corrupt archive` at startup — on an archive that had
verified **PASS on all three rules minutes earlier**, with nothing corrupted.

The likely trigger is that the *previous* session ended in a crash, leaving the
archive marked dirty; the message is a rescan-on-unclean-shutdown, not a verdict
that anything is wrong. That is a hypothesis, not a measurement.

What *is* measured is the outcome, and it answers this document's #2 open
question — *"Can the rescan rebuild the fileId→mftIndex map? Decides whether a
bad write is recoverable."* After the repair:

- all three checksum rules **PASS** (the client rewrote the MFT self-crc again,
  to a third value, and our rule predicts it again);
- all **171,023** file-id pairs resolve;
- map file ids from three campaigns still land on their rows;
- the stored textures we had repointed at still rendered.

**"Repairing corrupt archive" is not a one-way door.** The archive came out the
other side valid, addressable and playable. Arm C is now much less interesting
than it was — we have watched the repair path run and survive it.

**A free test for the next session, stated now so it cannot be rationalised
afterwards.** The unclean-shutdown hypothesis makes a sharp prediction. The three
launches so far:

| Launch | Ended | Logged `Repairing corrupt archive` at start? |
|---|---|---|
| 1 — planted bad crc | crash, exit 1 | no |
| 2 — stored icons | crash, exit 1 | **yes** |
| 3 — clean controls | **clean, exit 0** | no |

Launch 2 logged it and was preceded by a crash; launch 3 did not and was preceded
by a crash too — *which already strains the hypothesis*. Either the trigger is not
simply "the last session crashed", or the repair itself cleared the flag and
launch 3 inherited a clean one. Those are distinguishable:

> **PREDICTION:** the next launch, following launch 3's **clean** exit, logs **no**
> `Repairing corrupt archive`. If it does log one, the trigger has nothing to do
> with shutdown cleanliness and the hypothesis is dead.

Cost: read one line of `Gw.log` next time the client runs, for any reason.

**And a third independent confirmation of the self-crc rule.** Each of the three
sessions left the table in a state that had never existed, and the client wrote a
different self-crc each time — `0xDB258D15`, `0x2A16CEC7`, `0x5AF54752`. Our rule
predicted all three, plus the shipped value it was derived from. A reconstruction
that survives four novel inputs from the original implementation is no longer a
reconstruction in any interesting sense.

### A correction to §2 of the skills study's icon finding

The two icon fields are not rival guesses at one asset. MEASURED from the ATEX
headers:

| Field | Container | Format | Size |
|---|---|---|---|
| `+0x8c` | ATEX | **DXTL** | 64×64 |
| `+0x90` | ATEX | **DXT1** | **128×128** |

Tyria-Extractor calls `+0x8c` the standard icon and `+0x90` the high-resolution
one, and **by dimensions that is exactly right** — so its field labels are
CORROBORATED, not refuted. The error was ours: "standard" was read as "the one
the bar uses", and the bar uses the hi-res one. GWCA's `+0x94 = icon_file_id_hi_res`
is the label that is actually misplaced.

The useful claim from that pass is unchanged and still ours: **the skillbar draws
`+0x90`**, which no source states.

---

## 11. Next day: blocker #3 is gone, and the arc moves to its own study

This document ranks the ATEX container and its mip-chain framing as **blocker
#3**, and the open-questions table above carries *"How is an ATEX mip chain framed
below the first level?"* as NOT FOUND and gating.

**Both are settled, and the framing question turned out not to matter.** On
2026-08-06 the client rendered a 128x128 DXT1 texture this project authored from
nothing, in a skillbar slot, in a map — and it rendered just as well from a
**single-level** file, so the sub-level framing that was NOT FOUND is not on the
path to a new icon at all.

Two of this document's own measurements were wrong in the same way and are
corrected there: the ATEX header is **12 bytes**, not 20, and the fields recorded
here as `+12` (a size, 150/150) and `+16` (an unidentified discriminator taking
only 10 and 4) are **level 0's `size` and `code`**. The `150/150` held only
because the sample was single-level files; `+16` takes 0/1/2/4/8/9/10/12 across
the stored population, as a compression bitfield should.

**The full account is [../texture/FINDINGS.md](../texture/FINDINGS.md).** What it
means here: every blocker this document raised against writing a new skill icon
is now either solved or shown not to apply. The archive can be written, the
client verifies and accepts it, the write survives, and the texture can be
authored.
