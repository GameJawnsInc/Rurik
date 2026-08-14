# The ATEX texture container

**Status: the texture layer is open, end to end.** On 2026-08-06 the retail
client drew a skill icon this project authored from nothing — the image, the
DXT1 encoding, the container, the archive write, all of it ours. Everything in
this document is either MEASURED from the client's own code and the archive's
own bytes, or OBSERVED on screen.

This arc was split out of [../datwrite/FINDINGS.md](../datwrite/FINDINGS.md),
which established that the *archive* can be written and left the *texture* as the
remaining blocker. That framing is now spent: both are solved, and the honest
summary is that the texture container was much smaller than the study feared.

Labels are the project vocabulary from
[../character/FINDINGS.md](../character/FINDINGS.md).

---

## 1. The container

```
ATEX file
    +0x00  4  magic "ATEX"      ("ATTX" also parses; it carries a trailer)
    +0x04  4  fourcc            DXT1 DXT2 DXT3 DXT4 DXT5 DXTA DXTL DXTN
    +0x08  2  width  u16
    +0x0A  2  height u16
    +0x0C     level records, to the end of the buffer

level record
    +0x00  4  size u32   -- the record's TOTAL size, its own 8 bytes included
    +0x04  4  code u32   -- compression code; 0 means the payload is raw blocks
    +0x08     payload, size-8 bytes

    The next record starts at this record's offset + size. The walk ends when
    the running offset equals the buffer length EXACTLY.
```

**MEASURED**, two ways that cannot both be wrong in the same direction:

- **From the client.** The validating probe at VA `0x6c3050` checks the magic,
  switches on the fourcc, and walks 8-byte records from offset 12, counting them
  out through a pointer the caller supplies. ArenaNet's own assertion string
  `"offset + sizeof(AtexLevel) <= bytes"` from `ImgAtex.cpp:1560` sits in the
  binary and fixes the record at 8 bytes. Read independently by two agents, and
  a third wrote a small x86 decoder rather than trust either.
- **From the corpus.** The walk closes to the exact final byte on every ATEX
  file our decompressor can produce — 52,253 closed exactly out of 53,922 rows
  scanned, the remainder being files whose mip dimensions exhaust first, plus 4
  rows that cannot be decompressed at all (a known huffman table hole, already
  documented against text files).

Level payload size, for a level whose own `code` is 0:

```
w, h  = max(width >> level, 1), max(height >> level, 1)
bytes = roundup4(w) * roundup4(h) * bits_per_pixel / 8
```

`bits_per_pixel` comes from the client's table at VA `0xa5dd60`: **4** for DXT1
and DXTA, **8** for DXT2/3/4/5, DXTL and DXTN. Every dimension rounds up to a
whole 4x4 block, so a 1x1 level still costs a full block — which is why the 2x2
and 1x1 records of a chain are the same size.

## 2. Two of this project's NOT FOUNDs were the same mistake

[../datwrite/FINDINGS.md](../datwrite/FINDINGS.md) recorded, from a 150-entry
sample:

> `+12` `u32` == `payload_len - 12`, a **size** (150/150); `+16` `u32` taking
> only the values 10 and 4 with dimensions held constant — an unidentified
> discriminator, and specifically **not** a mip count.

**Both were level 0's record fields, read as though they were header fields.**
The header is 12 bytes. `+12` is level 0's `size` and `+16` is level 0's `code`.

Everything strange about them dissolves at once:

- `+12 == payload_len - 12` holds exactly when level 0 consumes the whole
  buffer — i.e. on **single-level files**. The 150-entry sample was drawn from a
  population where that was common; across the archive-stored population it
  fails, and it should.
- `+16` does not take "only 10 and 4". Across the stored ATEX population it
  takes **0, 1, 2, 4, 8, 9, 10 and 12** — exactly the shape of a bitfield, which
  is what a compression code is. The earlier reading held dimensions constant,
  which held the *level 0 encoding* constant with them.

The lesson is not about ATEX. A field at a fixed offset is only a "header field"
if you know where the header ends, and we had assumed a 20-byte header because
`12 + 8` is also `20`. The corpus could not refute that; only the client's own
record walk could.

## 3. OBSERVED: the client rendered our bytes

Four arms in one frame, four untouched controls interleaved with them, on a real
character in a real map. Predictions were written down before the launch.

| Slot | Arm | What was written | Predicted | **OBSERVED** |
|---|---|---|---|---|
| 1,3,5,7 | controls | nothing | normal icons | normal icons |
| 2 | **0** — real bytes | row 174086 decompressed, written **stored** | skill 4's real icon | **skill 4's real icon** (a developer texture reading "Dev Hax") |
| 4 | **A** — full chain | 11,012 B, 8 levels, all `code 0`, authored | solid magenta, faint dashes | **magenta, dotted grid** |
| 6 | **B** — single level | 8,212 B, 1 level, `code 0`, authored | solid green | **green, dotted grid** |
| 8 | **D** — negative control | 8,212 B, 1 level, **`code 1`**, authored | **not** clean red | **red with black bands** |

Four for four. What each one bought:

**Arm 0 proves the write path, not the format.** It is real ArenaNet bytes, so
the only thing under test is the archive plumbing: payload replaced in place,
size field rewritten, compression flipped 8 to 0, entry crc recomputed, MFT
self-crc recomputed. Five things that must all be right, any one of which fails
identically to a malformed texture from the bar's point of view. It exists so
that a failure in slots 4/6/8 would have been interpretable. It passed, so they
are.

**Arm A proves the container.** Header, `{size, code}` framing, the size formula
and the raw path, all authored by `toolkit/mapdata/atex.py` and all correct.

**Arm B is the answer this arc was chasing.** *"How is an ATEX mip chain framed
below the first level?"* was NOT FOUND and gating. **It does not need to be.**
A single-level file renders, at full quality, in the slot the skillbar draws.
The codec accepting one level was MEASURED from the disassembly beforehand — the
probe's loop tail at `0x6c3198` succeeds the instant the offset equals the buffer
length, with no requirement that mip dimensions be exhausted — but whether the
*texture layer above it* would accept one was genuinely open, because
`GrTex2d.cpp` asserts on a level count and nobody traced which flags the icon
path passes. Now observed.

**Arm D is the arm that could have caught us fooling ourselves.** If `code = 1`
had rendered clean red, the client would not have been reading the code field
and our whole model of the record would have been decoration over a client that
ignores it. It came back wrong — red broken by black bands, our raw blocks fed
to a compressed sub-codec and partly surviving. The field is read, and it means
what we think.

The **dotted grid** in arms A and B is predicted, not a defect. The fill is one
repeated dword, `0x0000F81F` for magenta; the low half is `color0`, the high
half `color1 = 0`, and the same dword reused as the index word gives every 4x4
block an identical two-tone pattern. A solid fill would have needed a different
value in the index word.

## 4. Why the fill was uniform, and what is still untested

**The one RECONSTRUCTION in the model is the raw payload's internal ordering** —
whether a raw level stores every block's colour words and then every block's
index words (planar), or complete blocks back to back (interleaved). One witness,
and it fails *silently*: the wrong ordering renders noise, not an error.

So the fill was chosen to make it unobservable. **If every dword in the payload
is identical, planar and interleaved produce byte-identical files.** Arms A and B
therefore tested the header, the framing, the size formula, the raw path and the
whole write path, and could not be confounded by the ordering question — and
equally, they say nothing about it.

### OBSERVED, later the same day: the ordering is PLANAR

The two-tone plan above was replaced by a better one. Rather than infer the
answer from what garbage looks like, **encode the same image both ways and ask
which slot is a picture.** Two files, byte-identical headers, identical length,
differing in 5,226 of 8,212 payload bytes, with the layout as the only variable.

| Slot | Layout | **OBSERVED** |
|---|---|---|
| 6 | **planar** | a coherent image |
| 8 | interleaved | noise |

Then the two were swapped between rows and relaunched: the slot that had been
noise rendered the image, which rules out the slot, the skill row and the MFT row
as explanations and leaves only the bytes.

**A raw ATEX level is PLANAR** — every block's colour dword, then every block's
index dword. Upstream said so, in a lineage that counts as one witness (§7); it
is now OBSERVED against the running client, twice, and the corpus could never
have settled it because both layouts are the same length.

`toolkit/mapdata/dxt1.py` implements both and keeps the loser, because the fastest
way to check this again on a future build is to render the image both ways.

## 4a. The skillbar does not draw the whole texture

The first authored image came back **"cropped/off-center"**, which no source we
have mentions and which would put authored art permanently in the wrong place if
left as folklore. So it was measured with a ruler.

**Coarse target** — four differently-coloured 12×12 corners (so a mirror or a
rotation could not masquerade as a crop) and 2px frames at insets 0, 4, 8, 16
and 32. OBSERVED: corners **gone**, inset 0 **gone**, inset 4 **gone**, inset 8
**gone**, inset 16 **visible**, inset 32 **visible**, centre cross centred. No
mirroring: the crop is symmetric.

**Fine target** — six adjacent 2px bands from inset 10 to 21. OBSERVED: red at
**inset 10 is barely visible**, and the owner identified why — *the bar's own
bevelled frame overlaps the icon edge, which is stock behaviour for real icons
too.*

So, MEASURED:

| Region | Fate |
|---|---|
| inset 0–9 | not drawn |
| inset 10–15 | drawn, but partly under the bar's frame chrome |
| inset ≥ 16 | fully visible |

**The safe area for authored art is the central 96×96 of a 128×128 texture**, and
`pattern_icon` in `dxt1.py` is drawn to it.

The mechanism is worth stating because it changes what the number means: this is
**not** a UV crop of the texture, it is the skillbar's frame drawn over the icon.
Retail icons lose their edges the same way, which is why every shipped skill icon
has its subject centred with margin. We were not seeing a bug in our file; we
were seeing the UI behaving normally against art that ignored the margin.

## 4b. OBSERVED: an authored icon, on the bar

The point of the arc, rather than another test pattern. `dxt1.pattern_icon` draws
a rising sun over a horizon — warm foreground against a deep sky, vignetted,
entirely inside the safe area — which was encoded to DXT1, packed planar, wrapped
in a single-level ATEX, written into the archive as a stored row, and pointed at
by a skill's `+0x90`.

**It rendered. The owner's description: "8 does appear as a sunset."**

The whole path is ours and every stage is checkable alone: image → DXT1 blocks
(`dxt1.encode`) → planar payload (`dxt1.pack`) → ATEX container (`atex.build_image`)
→ archive row (`datwrite --replace`) → skill row (`repoint_skill --set`). Standard
library only, no ArenaNet bytes anywhere in it.

DXT1 round-trip error on this art is **1.00/255 mean absolute per channel** —
effectively lossless for flat UI work, which is what a skill icon is.

## 5. What we can and cannot author today

**Can, and observed:** any DXT1 texture at any legal dimension, single-level or
full chain, written into the archive as a stored entry and drawn by the client.
That is enough for a genuinely new skill icon, which is what the skills arc
wanted and what [../datwrite/FINDINGS.md](../datwrite/FINDINGS.md) listed as
blocker #3.

**Can, untested:** the same for DXTA (4 bpp) and DXT3/5/DXTL/DXTN (8 bpp). The
size formula covers them and the fourcc switch accepts them; nothing else about
the container changes. DXTL was feared because it has no DirectX equivalent, but
**the skillbar reads `+0x90`, which is DXT1 128x128** — DXTL lives at `+0x8c` and
is not on the critical path for a bar icon.

**Cannot, and do not need to:** produce a *compressed* ATEX level. The four
sub-codecs at `0x6c2420`, `0x6c1990`, `0x6c1cd0` and `0x6c2010`, and the 256x256
special case at `0x6c22a0`, are unread. `code = 0` makes them unnecessary for
writing; they are needed only to read retail art back out, which is a different
project and not one we need.

**Cannot yet:** turn an ordinary image into DXT1 blocks. Nothing here does colour
quantisation — `atex.py` writes the blocks it is given. A minimal DXT1 encoder is
ordinary work with no unknowns in it, and it is the next thing to write if we
want art rather than test patterns.

## 6. Open

| Question | What would settle it |
|---|---|
| ~~Is a raw level planar or block-interleaved?~~ | **Answered: planar.** See §4. |
| ~~Does the bar draw the whole texture?~~ | **Answered: no**, the frame covers everything inside inset ~10. See §4a. |
| What does the terminal `code = 8` 1x1 record's 4-byte payload mean? | It is a compact colour fill; read the `code & 8` branch at `0x6c2010`. Only needed to clone a retail file byte-for-byte, never to author one. |
| Does the `+0x8c` DXTL 64x64 slot have its own safe area? | Whatever consumes it is unidentified, so the question is downstream of finding that first. |
| ~~Is the bar's frame inset a fixed pixel count or a fraction of the texture?~~ | **Answered: the client stretches the WHOLE texture onto a fixed screen quad.** See §9. |
| Do the other fourccs author as predicted? | Repeat arm B at DXTA and DXT5. Cheap. |
| Does a texture larger than its reservation force a relocation we can survive? | Everything so far fits in place. Relocation is the one archive operation still unexercised. |
| What consumes `+0x8c`, given the bar reads `+0x90`? | Untested. Candidates: the effects monitor, the Skills panel, the party-window recharge overlay. |

## 7. Witness count

The prior art contributed **less than it appeared to**, and the appearance was
dangerous. Four repositories implement ATEX decoding and they are **one lineage**:
`Jonathan-Greve/GuildWarsMapBrowser` and `gwdevhub/GuildWarsMapBrowser` are the
same project mirrored twice; `gwdevhub/GWToolboxpp` names GuildWarsMapBrowser in
its own `CREDITS.txt` as the source of the derived files; and
`apoguita/Py4GW_Reforged_Native` embeds the legacy `AtexAsm` decompressor with
IDA-style labels intact. `Fournux/Tyria-Extractor` is an independent
implementation but its own source cites GuildWarsMapBrowser, so it is dependent
information at best.

Two agents in this pass independently presented pairs from that set as mutual
corroboration. They are one witness. Everything load-bearing in this document is
MEASURED from the client binary or from archive bytes instead, and the upstream
family is decoration on top of it.

## 8. Reproducing this

```bash
python toolkit/mapdata/atex.py --dat <archive> --row 174086
python toolkit/mapdata/atex.py --make out.atex --fourcc DXT1 --size 128 --levels 1 --fill 0x000007E0
python toolkit/mapdata/datwrite.py --dat <copy> --replace <row> --data out.atex
python toolkit/clientpatch/repoint_skill.py --exe <exe> --target <skill> --set icon2=<file id>
```

`datwrite.py --replace` journals the previous value of every byte it writes, so
an arm reverts without re-cutting 4.2 GB. It refuses to relocate: a payload
larger than the row's 512-byte-block reservation is an error, not a silent move.

## 9. OBSERVED 2026-08-14: the bar stretches the whole texture, so 64x64 works

§6 asked whether the frame inset is a fixed pixel count or a fraction, and noted
it "decides whether a 256x256 icon buys real detail". It decides something more
immediately useful: **whether a skill roster can be re-iconed without moving a
single archive row.** A 128x128 DXT1 needs an 8,704 B reservation and fits 16 of
profession 8's 132 distinct icon rows; a 64x64 needs 2,560 B and fits **132 of
132**, the smallest reservation in that roster being 6,656 B.

Harness `20260814T002445`, three in-place `datwrite --replace` arms against
`vault/run/reskin-roster/Gw.dat`, five untouched controls interleaved. RUN
VERDICT PASS, no assert, no crash dialog, client alive the full 70 s.

| Slot | Arm | Written | **OBSERVED** |
|---|---|---|---|
| 1,4,5,6,7 | controls | nothing | normal icons |
| 2 | **Q** | 64x64 DXT1, a box-filtered mipmap of arm S | **the same sunset as slot 8, softer** |
| 3 | **R** | 64x64 DXT1, `pattern_fine`'s inset ruler | all six bands, red included |
| 8 | **S** | 128x128 DXT1, `pattern_icon` | the sunset — the positive control |

**Arm Q is a MIPMAP of arm S, and that is the whole design.** `pattern_icon`
draws to `safe = min(w,h)/2 - 16`, so calling it at 64 composes a *different*
picture; slots 2 and 8 would then differ for a reason that has nothing to do
with the client. Box-filtering the 128 down makes them the same image by
construction, so "are these the same picture?" is a question about UV mapping
alone. Measured over the inner 40% of each tile: slot 2 vs slot 8 is
**15.19/255** mean absolute per channel, against **68.9, 75.7, 79.9, 91.1 and
134.6** for the five untouched retail icons in the same frame. Same picture.

**Arm R turns that into a scale.** A scanline through slot 3 finds the white
band (source inset 20, so 12 texels from centre) at 11.5 px from centre and the
red band (inset 10, 22 texels) at 21.0 px:

```
white  11.5 px / 12 texels = 0.958 px per texel
red    21.0 px / 22 texels = 0.955 px per texel
predicted red from the white landmark: 21.1 px    OBSERVED 21.0 px
```

Two independent landmarks, agreeing to 0.1 px. **The texture maps LINEARLY onto
the quad across its whole width** — the client is not sampling a sub-rect, it is
stretching the entire texture onto a screen quad of fixed size (~61 px here).
The chrome then eats the outermost ~2.3 texels of a 64x64, i.e. **3.5% of the
edge**, which is *less* than the 7-11.7% §4a measured at 128x128.

That last comparison is the honest caveat: a constant *fraction* would predict
equal percentages and these are not equal. The two readings were taken on
different days and §4a's boundary was read by eye off nested frames ("not
drawn" versus "partly under chrome") rather than off a scanline, so the
discrepancy is as likely to be in that reading as in the model. What both agree
on, and what the roster question needs, is the direction: **a 64x64 loses no
more of its edge than a 128x128 does, and renders the same picture.**

**Consequence.** `pattern_icon`'s 16-pixel border was written for 128x128 and is
a *fraction* to be preserved, not a pixel count — 12.5%, so 8 px at 64x64.
`pattern_icon` divided by `safe` and therefore raised ZeroDivisionError at
32x32, where `min(w,h)/2 - 16` is 0; it was only valid at 40x40 and above.

**FIXED 2026-08-14** (`toolkit/mapdata/dxt1.py`). `safe` is now
`min(w,h) * 0.375` — the same 12.5% margin expressed as a proportion, which
reproduces 48.0 at 128x128 exactly, so *this section's arm S is unchanged
byte for byte* and only the sizes it was never valid at moved. Below
`MIN_ICON = 12` the function refuses rather than dividing by zero or a
negative; 12 is derived, being where the sun disc stops spanning one DXT1 4x4
block (`2 * 0.46 * 0.375 * n >= 4`), not chosen.

The fix carries an offline version of arm Q's argument, and it is worth
recording because it is the same measurement without a client. Under the
proportional rule a 2:1 box filter of the 128 and a direct call at 64 are the
same picture to **2.04/255** mean absolute; under the pixel-count rule they
are **17.74/255** apart, 8.7x. The residual is not zero and it is not one
thing: stubbing the ground dither out takes 2.04 to **1.25**, so the dither
(which indexes absolute pixel coordinates) is ~40% of it and the rest is the
box filter — averaging four samples is not the same as evaluating the picture
at half resolution, and the sun's rim, the horizon and the vignette all fall
between samples. So the reason arm Q had to
ship a *mipmap* of arm S rather than a second call to `pattern_icon` — see
above — no longer applies; a future roster arm can call the function at 64
directly and get arm S's picture.

`toolkit/mapdata/test_dxt1.py` section 6 pins all of it, with the retired rule
reproduced in the test file as a live function so both halves ("128 unchanged",
"64 changed") are differences between two live answers. Seven one-edit
sabotages were built and run and all seven redden.

**Still open:** whether a 256x256 buys detail. The quad is ~61 px wide on this
window, so a 128x128 is already supersampling it roughly 2:1 and a 256 would be
4:1. That predicts no visible gain, and it is now a cheap arm rather than a
question — but it has not been run.
