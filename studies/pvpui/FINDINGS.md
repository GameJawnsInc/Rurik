# The PvP-UI arc: what constructs `GmPosseRoster`, and is any of it server-reachable

**Opened 2026-08-17**, out of `studies/heroes/FINDINGS.md` §36.10. Labels per
`studies/character/FINDINGS.md`: OBSERVED, UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED,
UNVERIFIED, NOT FOUND.

## 0. Why this arc exists, and what it inherits as SETTLED

The heroes arc ended on a measured negative: our server can author a hero completely — roster
row, archive-resolved name, level, profession, attributes, skill bar, lit commander flag — and
**cannot bind a commander**, so the party-window hero button asserts `commander` /
`GmView.cpp(5890)`. The reason is not a wire field. It is that the commander event
`0x1000011E` is **raised into nothing**.

> **§10.2 relocates that assert.** `GmView:5890` is at `0x004E38F0`, in the case for event
> **`0x100001A4`** — not `0x1000011E`. `0x100001A4`'s only raise is `0x00524FD0`, local to
> the commander model, not a message handler. The paragraph above is the heroes arc's
> framing and is kept for the record; read §10 before acting on it.

Inherited from heroes, all OBSERVED, and none of it needs re-deriving:

- `0x01C2`'s worker raises `0x1000011E` at `0x008590CA`, gated on a party-cache miss (§26.2,
  §33.4). It is the **only** raise site in the image; there are **eight** subscribe sites
  (§36.4).
- Read out of the client's own lookup (`eax` at `0x0064CA47`), the event has **no subscriber**
  when we raise it (§34.1), control-verified against a 4000-hit census where 23 of 54 distinct
  events *were* subscribed (§34.2).
- The two subscribers that DO register in an explorable session are **GmView** (`0x004ED055`)
  and **Compass** (`0x008BB6B0`), measured by frame walk and cross-checked to the byte against
  a static scan (§36.7).
- **`GmPosseRoster` is not one of them**, and its handler `0x005392A0` is **never entered
  once** in a 115-second session with the party window open and a hero row rendering — not
  message 9, not any message (§36.10).
- ~~Its gate is not the reason: `[ctx[0x2c]+0x67C]` reads **1** (§36.8/36.10), so
  `0x00815E90` returns non-zero and the guarded install site `0x00578BF0` would have proceeded
  had it been reached.~~ **RETRACTED 2026-08-17, §7.** `0x00815EA0` is the gate's
  early-out, not its verdict, and the gate has 14 callers so the hits on it attribute
  to nobody. The install site is never reached — that part stands, on its own site —
  but whether the gate would have passed is UNVERIFIED.

**So the subscriber is not merely unregistered — its whole construction path is absent.**
That path is this arc's subject.

## 1. The construction chain, as far as it is read (OBSERVED)

```
GmPosseRoster handler        0x005392A0   switch on [esi+4]; message 9 -> subscribe block
  subscribe block            0x00539374   registers 0x10000114, 0x1000011E,
                                          0x1000011F, 0x100001C5 -- four events, one block
  installed from 3 sites     0x0050145C   GmDeckBuilder   (behind `test byte [esi+8],1`)
                             0x00578C0C   UiCtlInstance   (behind the 0x00815E90 gate)
                             0x008E3264   UiCtlInstance
  0x00578BF0 has NO callers  its VA sits in ONE aligned .rdata word
  the table                  0x00956264 .. 0x009562F0, 36 entries, index [7]
                             mostly one shared default (0x004A0AE0); the only other real
                             entries are [26] 0x00578F30 and [32] 0x00579260, same module
  who installs the table     0x005782C7 and 0x00578390, both `mov [eax], 0x956264`
                             -- a vtable pointer written into an object, i.e. a constructor
  and those live in          UiCtlInstance (asserts :95 `!*hdr.param`, :114 `hdr.param`)
```

The `hdr.param` asserts say those constructors are themselves **message handlers** — this is
the generic "create a UI control of this type" path, and index `[7]` is the posse-roster type.

**Read §6 before using this block.** Two of its lines are wrong in ways that matter:
`0x00578BF0` does have a caller (it is vtable slot [7], reached by an indirect
`call [eax+0x1C]`, which `--xrefs` says up front it does not search), and the three
"install sites" install the thunk `0x00539980`, not `0x005392A0` — the handler VA
itself has no direct reference at all. The chain is right; the mechanism is
indirect-call, and the table is a vtable dispatched by UI message number.

## 2. The questions, in the order they should be answered

1. **What message, with what parameter, drives `UiCtlInstance` to construct type `[7]`?**
   The constructors are handlers; the selector is `hdr.param`. Read it, then ask whether
   anything on the wire can reach it. *(This is the one that decides the whole arc.)*
   — **ANSWERED 2026-08-17 in §6: the message is 9, and there is no selector.**
   `hdr.param` is the instance slot (`T**`), not a type code; the sentence above
   misread the two asserts that name it. Type is fixed at compile time.
2. **Is `GmDeckBuilder`'s site the real path in retail?** It is behind
   `test byte [esi+8],1`. GmDeckBuilder is the PvP build UI, which an explorable PvE session
   has no reason to build — but that is a guess about *retail* until measured.
3. **Does any of this run in an OUTPOST?** Every heroes measurement was taken on an explorable
   map (90). Heroes §32 already blocks `0x01BF`'s remaining question behind RESKIN §18.1's
   explorable gate, and this arc plausibly shares that gate. **If it does, both arcs unblock
   together and that is worth knowing early.**
4. **Is the commander panel server-reachable at all?** The honest prior after heroes is **no**,
   and this arc's job is to convert that prior into a measured yes or no rather than leave it
   as five refuted fixes.

## 3. Method notes carried over, because they were expensive

- **`commandertrap.py` is the instrument** (hardware breakpoints in DR0..DR3, nothing written
  into the client). Its four defects and the three control gaps that hid them are in heroes
  §33.8 and §36.6 — in particular: a captured pointer needs its **frame** justified, not just
  its base, and a control that samples badly does not fail loudly, it agrees with whatever you
  were about to conclude.
- **Five hypotheses were refuted on the heroes question, and the static reading was right every
  time.** What was wrong every time was the guess about *which branch is cold*. Prefer one
  cheap measurement over a fourth guess.
- Client runs serialise on one harness and one `Gw.exe`; parallel agents collide rather than
  help. Fan out on static analysis only.

## 4. FIRST, THE BUILD. Every VA in this arc is build 38833, and the tools default to 38797

The static tools (`codescan.py`, `asserts.py`, `consttable.py`, …) resolve their client
through `pinned.find()`, which is the **pinned pristine build 38797**. Heroes §33–36 and §1
above are all 38833 numbers, taken with `--exe` pointed at the 38833 snapshot.

> **CORRECTED 2026-08-17, §15.0.** This paragraph used to continue "The harness runs
> whatever is staged in `vault/run/`, and on this machine that is 38833" — **wrong on both
> halves.** `drive_client.py:87` selects by *build*, and :167 records that 38833 is
> deliberately excluded so the newest 38797 copy wins. Running 38833 takes `--exe` **and**
> `RURIK_DAT`; the recipe is in §15.0.

The two are not interchangeable and the drift is per-region, not a constant:

| what | 38797 | 38833 |
|---|---|---|
| `GmPosseRoster` handler | `0x005392D0` | `0x005392A0` |
| its jump thunk | `0x005399B0` | `0x00539980` |
| slot-7 installer | `0x00578C10` | `0x00578BF0` |
| the gate | `0x00815FF0` | `0x00815E90` |
| `UiCtlInstance<T>` handler | `0x005782A0` | `0x00578280` |

−0x30, −0x30, −0x20, −0x160, −0x20. On 38797 `0x00578BF0` is not a function at all: it
is a six-entry switch jump table, so `--xrefs` correctly answers "no callers" and a
reader who does not check the build concludes the install site is dead code. This arc
nearly published that as a correction to §1. It is not a correction; it is a build slip.

**So: pass `--exe` explicitly, and stamp the build on every VA row.** A run:

```bash
python toolkit/clientscan/codescan.py --exe vault/client/2026-08-13_64fae3b1369b/Gw.exe --dis 0x00578BF0
```

Same family as the stale-worktree rule in `CLAUDE.md`: the tool does not error, it
returns a confident number from the wrong image.

## 5. `s_floatingDialogs` — the named-window registry (OBSERVED, build 38833)

The client's own assert names the array: `GmView:2073  dialog < arrsize(s_floatingDialogs)`
at `0x004E1E99`. The bound is the literal it guards, `cmp edi, 0x3a` — **58 entries**.

```
0x004E1E80  GmView::ShowFloatingDialog(parent, dialog, show, arg4)
  esi = dialog*0x24                lea esi,[edi+edi*8]; shl esi,2   -- stride 36
  assert dialog < 0x3A
  ebx = dialog + 0x13              the frame id
  find child frame ebx under parent
  show == 0  -> destroy that frame, return
  else       -> FrApi create-frame(parent, rec+0x0C, ebx, rec+0x00, arg4, rec+0x04)
```

Record layout, 36 bytes, base `0x0094BEE8`:

| off | what it is |
|---|---|
| +0x00 | the frame handler (a chain head) |
| +0x04 | wide name, e.g. `PvpItemCreate` |
| +0x08 | flags — `0x159` or `0x563`, one record `0` |
| +0x0C | `0x20` for every record; passed to frame-create |
| +0x10 | bit 0 gates an extra call through `rec+0x20` |
| +0x14 | a string id (`0x187CA` on most) |
| +0x18, +0x1C, +0x20 | UNVERIFIED — plausibly id/category/index, not read |

**A check that could have refuted this and did not:** both sites that open dialog 39
first probe for child frame **`0x3A`** and show the dialog only if it is absent. 39 +
0x13 = 0x3A, exactly. The frame-id rule is the artifact's, not our decoder's.

Indices that matter here — `DeckBuilder` 10, `MercenaryRoster` 24, `PartyBattle` 27,
`PartyContextMenu` 28, `PartyMinions` 29, `PartySearch` 30, **`PetCommanderPlayer` 31,
`PetCommanderHero0..6` 32..38**, **`PvpItemCreate` 39**.

*Provenance note, so the next session does not re-litigate it.* These names are cited as
the evidence for specific claims, the way `CLAUDE.md` permits a single assert to be —
the extractor is scratch and the table is **not** dumped into the repo. If the whole
registry is ever wanted, it goes to `vault/` through an in-repo extractor with per-row
provenance, per the gate's three conditions. It is not needed for this arc.

## 6. Q1 ANSWERED: the message is 9, and nothing selects the type

Whole chain, measured, build 38833:

```
GmView::ShowFloatingDialog(parent, 39, show=1)          0x004E1E80
  -> FrApi create frame id 0x3A, handler 0x00579A00     0x00630C90   (FrApi.cpp)
  -> frame creation delivers UI message 9 down the chain
0x00579A00   'PvpItemCreate' chain head; keyed on events 0x100000FA / 0x100000FC,
             forwards everything else onward
0x00578280   UiCtlInstance<T>::Handler -- `cmp dword [hdr+4], 9`
               operator new(16), vtable 0x00956264, *hdr.param = obj, obj+4 = hdr[0]
               then forwards hdr to the object's own handler as a thiscall
0x0087DC60   the control dispatcher:  idx = message-1, bound 0x51,
               byte table 0x0087E06C -> case table 0x0087DFE8
               message 9 -> case[4] at 0x0087DD27 -> `call [eax+0x1C]` = vtable slot 7
0x00578BF0   slot 7: gate 0x00815E90, then create child frame with handler
             0x00539980 (`jmp 0x005392A0`) = GmPosseRoster
```

`hdr` is `{+0: …, +4: message, +8: T** instance slot}`. Message **9 = create** and
**0xB = destroy** — 0xB is the branch that calls `operator delete` with size 0x10 after
re-installing the vtable, which is what makes the pair unambiguous.

**There is no type selector anywhere on that path.** `hdr.param` is the instance slot;
the asserts `!*hdr.param` (`UiCtlInstance.h:95`, "not already constructed") and
`hdr.param` (`:114`) are about that slot's nullness, not about a type code. Which type
gets built is fixed at compile time by which `UiCtlInstance<T>` the linker instantiated
and which vtable its `mov [eax], <table>` writes. **The only runtime choice in the whole
chain is which `s_floatingDialogs` index was opened.**

So the wire cannot ask for a posse roster. The most it could ever do is cause dialog 39
to be shown, and then the client builds the roster as that dialog's child.

Corroborating the ownership of that vtable, two ways: the `__FILE__` string the compiler
placed immediately after the table at `0x009562F4` is
`P:\Code\Gw\Ui\Game\PvpItem\PvpItemInt.cpp`, and slot [32] (`0x00579260`) carries an
assert from `PvpItemCreate:786`. The class is a **PvpItem** control.

## 7. Two corrections to heroes §36.8 / §36.10, both about the gate

Heroes read `[ctx[0x2c]+0x67C] == 1` at `0x00815EA0` and concluded "the gate passes, so
the roster handler would have installed". Neither half of that survives the full body:

```
0x00815E90  eax = <globals>                    call 0x47F660
            edi = [eax+0x2c]
            esi = [edi+0x67C]
0x00815EA0  test esi,esi ; jne ...              <- the trap sat HERE
            return 0                            <- esi == 0 is the early-out
            assert esi < [edi+0x814]
            eax = [edi+0x80C]                   base of an 80-byte-stride array
            return ([eax + esi*80 + 0x14] >> 11) & 1
```

1. **`0x00815EA0` is the early-out, not the verdict.** `esi == 1` means only "not zero,
   keep going". The value actually returned is **bit 11 of a record field** that the
   trap never read. The gate's answer is UNVERIFIED, not "passes".
2. **The gate has 14 callers** (`0x004A8C3B, 0x004E9413, 0x004E957D, 0x004E959F,
   0x004EAA62, 0x004FAA78, 0x0054DAD3, 0x0054E300, 0x00578BF9, 0x0058A9DF, 0x0058ABBF,
   0x0058AD68, 0x0058AEEB, 0x008EB810`). Five hits on an address *inside* it attribute
   to none of them. The run printed `chain: posseMsg=0 -> posseGate=5`; those two
   numbers are not a chain, and the word invited exactly the reading it got.

Neither defect overturns heroes' conclusion — "the handler is never entered" rests on
its own site, `0x005392AC`, and that address is confirmed correct for 38833 (`mov
eax,[esi+4]; cmp eax,0x56`, the handler's own message switch). What does not survive is
the *reason* offered for it. The honest statement is: **the handler never ran, and we
never measured whether the gate would have let it.**

## 8. The commander panel is `GmPetCommander`, and it is not on the posse path at all

The registry has eight commander records, and they are opened by a computed index:

```
0x004E8990   (one caller, 0x004E3D16)
  esi = 0x1F                                   default: PetCommanderPlayer (31)
  if target != the player agent:
      eax = 0x00524DB0(agentId)                the hero-record lookup
      esi = [eax+4] + 0x20                     dialog = 32 + heroIndex
  ShowFloatingDialog(parent, esi, show=1, …)
```

`s_floatingDialogs[31..38].handler` is `0x0050E540` → `jmp 0x0050DC50`, whose asserts are
`GmPetCommander:368 petAiMode != CHAR_AI_MODES` and `GmPetCommander:738 success`. The
split in the record ids — hero0..2 at `0xE0,0xE1,0xE2` and hero3..6 at
`0xFE,0xFF,0x100,0x101` — is the three-heroes-then-four shape of the game's own history,
which is a second, independent reason to believe the reading.

**This is a different mechanism from the `0x1000011E` event heroes spent the arc on.**
The commander window is opened by dialog index through `GmView`, and what it needs is
`0x00524DB0` returning a hero record for the agent — a sibling of `0x00524C40`, the
function heroes measured as never running. `GmPosseRoster` is a child of the PvP
windows (`PvpItemCreate`, `DeckBuilder`), not the commander panel.

## 9. Where this leaves the questions

- **Q1 — answered (§6).** Message 9; no selector; the only runtime choice is the dialog
  index. **Q2 — answered in the same breath**: both install sites are PvP windows, now
  name-confirmed, so a PvE explorable session has no reason to build either.
- **Q4 is now sharp and cheap**: it is no longer "is the panel reachable" but "can
  anything on the wire reach `ShowFloatingDialog`". 77 call sites, all in `GmView`; 18
  pass a literal dialog and 10 compute it. Walk up from `0x004E3D16` and from the two
  dialog-39 sites (`0x004E9450`, `0x004EAAA2`, both toggles) and find out whether any
  caller is a message handler rather than a control code.
- **The heroes question changed shape.** Before spending anything more on `0x1000011E`,
  read `0x00524DB0` and ask what it needs in order to return a record — that, not the
  event, is what stands between us and `PetCommanderHero0`.

## 10. Q4 ANSWERED, and it moves the heroes arc off `0x1000011E`

`GmView`'s frame handler is `0x004E27D0`, installed by **`UiGame.cpp`** at `0x004A7AD5` as
frame id 6 under the game root. It splits its own dispatch in two:

```
0x004E284E  eax = hdr.message
            cmp eax, 0x10000001 ; ja -> the EVENT half at 0x004E366A
            sub eax, 4 ; cmp eax, 0x4E     small UI messages 4..0x52
                       byte table 0x004E636C -> case table 0x004E6308   (25 cases)
0x004E366A  sub eax, 0x10000007 ; cmp eax, 0x1C7
                       byte table 0x004E66C4 -> case table 0x004E6480   (145 cases)
                       events 0x10000007 .. 0x100001CE
```

Both tables are two-level MSVC switches, so a call site inside the function can be mapped
back to the exact selector that reaches it: find the case block it falls in, then the
selector slots whose index byte picks that case. Three sites, each landing in a block of
0x1C–0xAC bytes with **exactly one** selector:

| site | what it does | reached by |
|---|---|---|
| `0x004E3D16` | calls `0x004E8990`, the commander-window opener | event **`0x100001C2`** |
| `0x004E38F0` | `assert commander` — **`GmView:5890`, the heroes crash** | event **`0x100001A4`** |
| `0x004E387F` | `assert commander` — `GmView:5875` | event **`0x100001A3`** |
| `0x004E2BE3` | the branch reaching both dialog-39 toggles | UI message **0x20** |

### 10.1 The commander window is opened by a CLICK, not by the wire

Event `0x100001C2` has exactly two sites in the whole image: a subscribe inside GmView's
block at `0x004ED26C`, and **one raise** at `0x00567069`:

```
0x00567052   cmp [hdr+4], 1          UI message 1
0x0056705F   cmp [hdr+8], 8          param 8
0x00567064   push 0 ; push [eax+0x20]        the agent id
0x00567069   push 0x100001C2 ; call 0x00633D70      RAISE
```

That function's asserts are `PtTeamAgent:237 petFrame`, `:250 petFrame`, `:273 agentId` —
**the party window's team-agent row**. So the whole route is:

```
click a party row (UI message 1, param 8)
  -> PtTeamAgent raises 0x100001C2 carrying the agent id
  -> GmView case[136] -> 0x004E8990
       dialog = 31 if the agent is the player,
                else 32 + [0x00524DB0(agentId) + 4]
  -> ShowFloatingDialog(dialog, show=1) -> s_floatingDialogs[31..38] -> GmPetCommander
```

**Nothing on the wire raises `0x100001C2`.** The two sites are this raise, inside a UI
click handler, and GmView's own subscribe. **Q4: the commander window is not
server-openable — it is opened by the player clicking, and the server's only influence is
over what `0x00524DB0` finds.** That is a much better place to be than "not reachable":
the server does not need to open the window, it needs the lookup to succeed.

### 10.2 The heroes crash is on a different event than the arc assumed

`GmView:5890 commander` sits at `0x004E38F0`, in the case for event **`0x100001A4`** — not
`0x1000011E`. Its neighbours name the shape of what is missing:

```
0x004E387F  GmView:5875  commander
0x004E3899  GmView:5876  commander->slotIndex < DLG_AGENT_COMMANDERS
0x004E38F0  GmView:5890  commander                    <- the crash
0x004E390A  GmView:5891  commander->slotIndex < DLG_AGENT_COMMANDERS
0x004E393C  GmView:5897  heroData
0x004E3956  GmView:5898  heroData->agentId
```

`DLG_AGENT_COMMANDERS` is the registry's **`AgentCommander0..6`** family (indices 0..6,
handler `0x004FB490`) — a *second* commander UI, distinct from `PetCommander*`. So the
client wants a `commander` record carrying a `slotIndex` that selects one of seven
`AgentCommander` dialogs, plus `heroData` with an `agentId`.

`0x100001A4` also has exactly three sites: GmView's subscribe (`0x004ED1E5`), a PvpItem
subscribe (`0x00577E33`), and **one raise at `0x00524FD0`** —

```
0x00524FC1  call 0x0049C4B0 ; test eax,eax ; je skip
0x00524FCD  push 0 ; push edi
0x00524FD0  push 0x100001A4 ; call 0x00633D70      RAISE
0x00524FDD  add esi, 0xc                            ... looping over 12-byte records
```

— inside the same function region as `0x00524DB0` (the hero-record lookup §8 uses) and
`0x00524C40` (heroes §26 measured as never running). **That module is the commander
model.** It walks a table of 12-byte records and raises `0x100001A4` per record that
passes `0x0049C4B0`.

### 10.3 What this means for the heroes arc

Heroes spent the arc on `0x1000011E` because that is what `0x01C2`'s worker raises. Nothing
measured here contradicts that raise — but the assert the player actually hits is on
`0x100001A4`'s path, and `0x100001A4` is raised **locally**, by the commander model
iterating its own records, not by a message handler. The chain the server needs is
therefore:

```
our 0x01C2 (or whatever populates the model)
   -> the 12-byte records at 0x00524xxx get filled
   -> 0x00524FD0 raises 0x100001A4 once per record
   -> GmView case[125] finds `commander` non-null and slotIndex < 7
   -> AgentCommander{slotIndex} renders; the party row click then opens PetCommanderHero{n}
```

**The next measurement is not on the wire and not on the event bus.** It is: what does
`0x0049C4B0` test, and what fills the 12-byte record table that `0x00524FD0` walks? That
is the thing standing between us and a bound commander, and it is desk work.

RECONSTRUCTION, flagged as such: the arrow from `0x01C2` to those records is inferred from
adjacency (`0x00524C40`, `0x00524DB0`, `0x00524FD0` in one region) and is **not** measured.
Do not carry it forward as OBSERVED.

### 10.4 One coincidence, named so nobody spends a day on it

Event `0x100001C2` and network opcode `0x01C2` share their low bits. The event space is
`0x10000007..0x100001CE` and opcodes run to about `0x01FF`, so the two numbering spaces
overlap by construction and collisions are expected. There is no measured relationship,
and `0x100001C2`'s only raise is a UI click handler in `PtTeamAgent`. Treat it as
coincidence unless something measures otherwise.

## 11. `0x00524C40` does not "never run" — it runs once per record, and the list is empty

Heroes §26 measured `0x00524C40` as never entered and read that as the commander never being
created. The call site says something more useful: it is **inside a loop**, once per element
of a **local** array the same function built moments earlier.

```
0x00524E00  the commander model's rebuild
  esi  = 0x004E0B90()                      the view
  eax  = 0x0084DD70()   -> [ebp-0x5c]      MsCliApi: our own identity
  edi  = 0x008563B0(0, 0)                  first item of the default container
  ebx  = 0                                 slot counter
  while (edi):
      if ([edi+4] == [ebp-0x5c]):          the item is OURS
          assert ebx != 7                  (:214) -- at most SEVEN slots
          rec = &[ebp-0x58] + ebx*12
          rec[0] = ebx                     slotIndex
          rec[1] = -1
          rec[2] = [edi+8]                 the agent id
          ebx++
      edi = 0x008563B0(0, ++esi)
  [ebp-0x64] = ebx                         the count

  … then, for each of those `ebx` records:
0x00524FA4  eax = 0x00524C40(rec.agentId)          <- HEROES' "never runs"
0x00524FAE  eax[0] = rec.slotIndex
0x00524FB0  eax = eax[4]
0x00524FB3  eax = (eax >= 3) ? eax+0x5F : eax+0x37    the 3-then-4 split again
0x00524FC1  if (0x0049C4B0(eax)):
0x00524FD0      raise 0x100001A4 with the agent id
```

**So "the commander is never created" and "the loop body never ran" are the same
observation, and the cause is upstream of both: `ebx == 0`.** Either `0x008563B0(0, n)`
returns nothing, or nothing it returns has `[+4]` equal to our identity.

`0x008563B0(container, index)` is a plain two-level accessor, no asserts:

```
g = globals(); c = [g+0x4C]
container == 0 ?  c = [c+0x54]                      the default container
               :  bounds-check against [c+0x48], c = [[c+0x40] + container*4]
index >= [c+0x2C] ? return 0                        the count
return [c+0x24] + index*12                          12-byte records
```

**RECONSTRUCTION** (well-supported, not measured): this is the hero-owner list. The cap of
seven, the `slotIndex` it produces, and the 3-vs-4 split downstream all match the hero
slots exactly, and `[+4] == our identity` is the ownership test. What is OBSERVED is the
structure walk and the loop; the name is inference.

### 11.1 The one thing to measure next

The whole heroes question now reduces to a single, cheap, *local* reading:

> **After our server sends the hero pipeline, is `[[globals+0x4C]+0x54]`'s count
> (`+0x2C`) non-zero, and do any of its 12-byte records carry `[+4] == 0x0084DD70()`?**

That is one `commandertrap.py` capture at `0x00524E40` (the compare) with the two values
read out — or, cheaper still, a `commanderpeek.py`-style read of the two structure fields
with no breakpoint at all. Both are far cheaper than another wire hypothesis, and either
outcome is decisive:

- **count == 0** → nothing populates the container; find its writer and the message behind it.
- **count > 0 but no `[+4]` match** → we populate it with the wrong owner id, which is a
  field bug in a message we already send.

Five hypotheses were refuted on this question by guessing at the wire. This is the first
version of it that names a specific number to go and look at.

### 11.2 What is now known NOT to be the blocker

- **Not `0x1000011E`.** The assert the player hits is on `0x100001A4`'s path (§10.2).
- **Not `GmPosseRoster`.** That is a child of the PvP windows (§6), and the commander UI is
  `GmPetCommander` / `AgentCommander*` (§8, §10.2).
- **Not the wire opening a window.** The window is opened by a party-row click (§10.1).
- **Not `0x00524C40` being cold.** It is cold because its loop has no iterations (§11).

## 12. `0x01C2` fills that container, and here is the field that decides it

**Correction to §11 first.** §11 called the container's items 12 bytes. They are **24**:
`0x008563E3 lea ecx,[edi+edi*2]` then `0x008563E8 lea eax,[eax+ecx*8]` — index×3×8. The
*local* array in the commander model is genuinely 12 bytes per record (`lea ecx,[ebx+ebx*2]`
then `[ebp+ecx*4-0x58]`), and I conflated the two. Nothing downstream changes: the
commander model still reads `[item+4]` and `[item+8]` out of the container, and still
writes 12-byte records of its own.

`msghandler.py` puts opcode `0x01C2` on handler **`0x00856C40`**, and it lands on the same
subsystem the commander model reads:

```
0x00856C40   [RECV] 0x01C2
  eax = globals()
  ecx = [eax+0x4C] + 4                  <- the subsystem, +4
  push [msg+0x14]  [0]  [0]  [msg+0x10]  [msg+0x0C]  [msg+0x08]  [msg+0x04]
  call 0x00859010
```

```
0x00859010(this = [g+0x4C]+4, container, a, b, c, d, e, f)
  esi = container
  edi = [this+0x4C]                     the one-entry cache
  if (!edi || [edi] != esi):
      esi == 0 ? edi = [this+0x50]      <- == [[g+0x4C]+0x54], THE DEFAULT CONTAINER,
                                           the exact one 0x008563B0(0, n) walks
               : bounds-check [this+0x44], edi = [[this+0x3C] + esi*4]
  if (!edi) bail
  [edi+0x78] = 1
  grow [edi+0x24] if [edi+0x2C]+1 > [edi+0x28]        base / count / capacity
  item = [edi+0x24] + ([edi+0x2C]-1)*24
      item[+0x04] = a        (msg+0x08)
      item[+0x00] = b        (msg+0x0C)
      item[+0x08] = c        (msg+0x10)
      item[+0x0C] = d        (0)
      item[+0x10] = e        (0)
      item[+0x14] = f        (msg+0x14)
  if (edi != [this+0x4C]) … raise 0x1000011E at 0x008590CA
```

The container's `+0x24 / +0x28 / +0x2C` are exactly the base / capacity / count that
`0x008563B0` reads back. **This is the same object, written by `0x01C2` and read by the
commander model, `GmPosseRoster` and `PvpItem`** (the accessor's eight call sites are in
those three places and nowhere else).

### 12.1 The field that decides whether a commander binds

Cross-referencing §11's ownership test with the mapping above:

| the commander model reads | which is the container item at | which `0x01C2` fills from |
|---|---|---|
| `[edi+4] == 0x0084DD70()` — **the ownership test** | `item+0x04` | **`msg+0x08`** |
| `[edi+8]` — the agent id it stores as the hero's | `item+0x08` | **`msg+0x10`** |

So: **for a hero to get a commander, our `0x01C2` must carry, at `msg+0x08`, the same value
`MsCliApi`'s `0x0084DD70()` returns for us — and the hero's agent id at `msg+0x10`.** If
`msg+0x08` is anything else, the item is appended, the list is non-empty, and the commander
model's loop still produces zero records, because every item fails the ownership test.

That is a **field bug in a message we already send**, not a missing message — and it is the
second of the two outcomes §11.1 predicted, reached without the harness.

**RECONSTRUCTION, and the distinction matters:** the offsets are OBSERVED, the arrow from
"our `0x01C2` payload" to "these argument slots" is not. `msg+0x04/0x08/0x0C/0x10/0x14` are
*decoded-struct* offsets in the client's own message struct, which are not the same thing as
byte offsets in our wire payload — `schema/messages.json` is what maps one to the other, and
nothing here read it. **Do that mapping before changing a line of `authsrv.py`.**

### 12.2 Why `0x1000011E` looked like the answer for so long

The raise heroes chased is at `0x008590CA`, **inside this very function**, on the branch
taken when the container written is *not* the cached one. It is a cache-invalidation
notification, and it fires whether or not the item that was just appended belongs to us.
That is why it was observable, and why it led nowhere: **it reports that the list changed,
not that a commander exists.** The commander asserts hang off `0x100001A4` (§10.2), which is
raised only after the ownership test has already produced a record.

## 13. ~~THE CONTAINER IS THE WRONG ONE~~ — PARTLY REFUTED, see §14

> **Read §14 first.** §13.2's headline does not survive a measurement already in
> this repo (RESKIN §18). §13.1 stands; §13.3 stands as a static fact but now
> CONTESTS RESKIN and may not be quoted either way. §13.4's experiment is withdrawn.
> The section is kept unedited below because the retraction is the useful part.

### 13.0 (original heading) `0x01C2`'s first field selects the container, and we send 1

Everything above converges here, and it is a two-line experiment.

### 13.1 What heroes already had, re-derived from the other end

Working forward from the UI, this session reached `[[globals+0x44]+0x2AC]` as the identity
the commander model tests against — and heroes §22 was already there, from the wire:
`agents.py:5567` names handler `0x0084EF00`, the field `ctx[0x44][0x2ac]`, and the
comparison against `0x01C2`'s `msg+8`, and sends `PLAYER_AGENT_ID` for it. **Two
independent derivations, opposite directions, same answer** — CORROBORATED, and not news.
The opcode is `0x0199`, `GAME_SMSG_INSTANCE_LOAD_INFO`, which we already send.

So the identity is not the problem. Heroes §21 measured that with `--player-number 2` the
roster row renders when `msg+8` equals the declared player number, while the commander
binding vanishes, and called the two "DIFFERENT `my id` notions". With both values at 1 in
the default rig they should agree — and the commander still does not bind. **So the
ownership test was never the blocker.** The list is empty before the test runs.

### 13.2 The branch heroes read as "silent" is the one that matters

`0x01C2`'s **first field** is not a label, it is the container selector, and the worker
branches on it:

```
0x00859010(this = [g+0x4C]+4, container, …)
  0085902B  container != 0 -> 0x859032  bounds-check [this+0x44],
                                        edi = [[this+0x3C] + container*4]   a NUMBERED container
  0085902D  container == 0 -> edi = [this+0x50]                             the DEFAULT container
```

And `[this+0x50]` is `[[g+0x4C]+0x54]` — **byte for byte the container the accessor's
`container == 0` path resolves**, and therefore **the only container the commander model
ever reads** (§11: it calls `0x008563B0(0, n)`, arg0 literal zero).

`agents.py:560` refuses `party_id = 0` with the reasoning that it hits "the same
silent-on-zero branch as `party_henchman_add`". The branch is real; the reading of it is
not. **Zero is not a no-op — it is the default-container branch.** We send `party_id = 1`
(`authsrv.py:8159`), which appends to numbered container 1. The roster UI reads that one,
which is why the row renders. The commander model reads container 0, which is why it finds
nothing, why its loop has no iterations, and why `0x00524C40` is cold.

**That single mismatch is consistent with every measurement in the heroes arc**, including
the ones that made the five refuted hypotheses look plausible: the row rendering, the
commander vanishing, `0x00524C40` never running, and `0x1000011E` being raised into nothing
(it is raised on the cache-miss branch either way, §12.2).

### 13.3 Who creates the default container, and whether we ever ask

`[c+0x54]` has exactly two pointer stores in the image, both in `0x0085A340`, which is
called from exactly one place — `0x00857226`, inside `0x00857200`, whose VA sits in the
receive table at `0x00BCB964`:

```
opcode 0x01D9 -> 0x00857200(msg)
   0x0085A340([msg+4], [msg+8], word[msg+0xC] ? &msg[0xC] : 0)
     ... raise 0x1000012D, then [[g+0x4C]+0x54] = the new container
```

`schema/messages.json` gives `GAME_SMSG_0473` as `[byte, byte, string16(122)]`, matching
the handler's three reads — a party id, a flag, and a name. **Nothing in `toolkit/` sends
`0x01D9`.**

### 13.4 The experiment, with its prediction stated first

Per `CLAUDE.md`: the prediction goes on the record before the run, because a probe with no
stated expectation can be rationalised into agreeing with anything.

> **Send `0x01D9` to create the default party, then send `0x01C2` with `party_id = 0`
> instead of 1.**
>
> **Predicted:** `0x008563B0(0, n)` starts returning items; the commander model's loop
> gains one record per hero whose `msg+8` equals `PLAYER_AGENT_ID`; `0x00524C40` runs (it
> has never run once in this project); `0x100001A4` is raised; and the party-row click
> stops asserting `commander` at `GmView:5890`.
>
> **What would refute it:** `0x00524C40` still cold with a non-empty container — then the
> ownership test *is* failing and §13.1's CORROBORATED identity is wrong somewhere.
> Container still empty after `0x01D9` — then `0x01D9` is not sufficient to install it and
> the `[c+0x54]` store is gated on something inside `0x0085A340` we have not read.
> **Row stops rendering** — then the roster UI and the commander model genuinely do read
> different containers, retail sends `0x01C2` twice, and heroes §21.2's tension is real
> rather than an artifact of us picking the wrong container.

The third refutation is the interesting one, and it is cheap to pre-empt: send the hero row
**both ways**, `party_id = 0` and `party_id = 1`, and see whether row and commander can be
lit at the same time. That costs one extra message and settles §21.2 either way.

**Two guards must move to run this at all**, and both are heroes' own, both documented as
inheriting a belief rather than a measurement: `agents.py:560`'s `1 <= party_id <= 20` and
whatever refuses an unknown opcode on the send path. Relax the first to `0 <= party_id`,
citing this section — do not delete it.

### 13.5 Status of this section

The addresses, the branch, the two stores, the table entry and the schema shapes are
**OBSERVED** on build 38833. That `0x01D9` is *sufficient* to install the container is
**UNVERIFIED** — `0x0085A340` has a body we did not read past the store. The prediction in
13.4 is a **PREDICTION** and nothing more until a run either meets or refutes it. Nothing in
this section has been near a client; it is all static reading, and the arc's history says
that is exactly when to be most careful about calling it settled.

## 14. §13 IS PARTLY REFUTED, by a measurement already in this repo

§13 was written without searching the tree for the pointer it had just found. That search
takes thirty seconds and it changes the answer. Recording the retraction in full, because
the arc's own §3 says the static reading has been right every time and the *guess about
which branch is cold* has been wrong every time — and §13.2 was exactly such a guess.

### 14.1 What is refuted

**§13.2's conclusion — "we write a numbered container, the commander model reads the
default one, so it sees an empty list" — does not survive.** `agents.py:369`'s
`party_build` docstring and `studies/profession/RESKIN.md` §17.1 both name
`[[ctx+0x4C]+0x54]` as `PyCliGetMyPartyId` at `0x00856250`, the *same pointer*, and
RESKIN §18 **measured it** after the party build:

> "with the party record built that value is 1, the arm reaches the FrameCreate at
> `0x004EC1BF`… Prediction stated before the run, hit."

Non-null, dereferencing to **1**. So the default container exists and it *is* party 1 —
the container our `0x01C2(party_id=1)` writes, reached either through the worker's
one-entry cache (`[edi] == esi`) or the numbered array. **The commander model is reading
our rows, not an empty list.** §13.4's experiment would therefore change nothing, and
§13's headline is withdrawn.

### 14.2 What survives, and one genuine contradiction

- **§13.1 stands** — `ctx[0x44][0x2AC]` reached from the UI side here and from the wire
  side in heroes §22. CORROBORATED, and the identity is not the blocker.
- **§13.3's static fact stands, and now CONTESTS RESKIN.** `[c+0x54]` has exactly **two**
  pointer stores in the image, both inside `0x0085A340`, called from exactly one site,
  inside the handler for opcode **`0x01D9`** — which nothing in `toolkit/` sends. Yet
  RESKIN measured the pointer non-null after a build that never sends `0x01D9`.

  **CONTESTED**, and the two candidate resolutions are cheap to separate:
  1. My scan missed a store. `codescan.py` says so itself in its own footer — a constant
     held in a register, or an address built in two steps, is invisible to it. **That is
     the way to bet**, and `--xrefs` on the party-build handlers is the check.
  2. `PyCliGetMyPartyId` does not read that pointer the way §17.1 describes, and RESKIN's
     "1" came from somewhere else.

  Until one of those is settled, **neither "0x01D9 installs the container" nor "the
  container is never installed" may be quoted as fact.**

### 14.3 The corrected chain, and where the cold path actually starts

Working back from `0x00524C40` instead of forward from the container:

```
0x00524C40   heroes' "never runs"
  called only from 0x00524FA4, in the rebuild loop
0x00524E00   the rebuild -- ONE caller in the whole image
  0x004E5D85, inside GmView's event dispatcher
  case[90], selected by exactly one event: 0x10000114
0x10000114   raised at 0x008588AD, inside 0x00858850
  0x00858850 has ONE caller, 0x008569F7, inside the handler for opcode 0x01B2
0x01B2       PARTY_SET_MINE -- and `agents.py:434` shows WE ALREADY SEND IT
```

So the rebuild is not unreachable and its trigger is a message we send. **The live
question is ordering, not presence:** the rebuild is driven by `0x01B2`, and our hero rows
`0x01C2` go out *inside* the `0x01D2..0x01D3` build window. If they land after the rebuild
has already run over an empty container, and nothing re-raises `0x10000114` afterwards,
the model stays empty and `0x00524C40` stays cold — with every other measurement in the
heroes arc unchanged.

`authsrv.py:2322` shows this exact ordering already has a flag ("Send `0x01C2` AFTER
`0x01B2` instead of inside the `0x01D2..0x01D3` window", CLI at :7896). **Whether it has
ever been run together with a commander check is not recorded anywhere I can find, and
that — not a new hypothesis — is the next thing to establish.** If it has been run and the
commander still did not bind, then the trigger ordering is refuted too and the cold path
starts further up, at whether GmView's case[90] is reached at all.

### 14.4 The method note, because this is the second time in one session

§4 caught a build slip before it was published. §14 catches a repo-search slip **after**.
The rule that would have caught both is the same one and it is cheap: **before writing
down a new address, grep the tree for it.** `[[ctx+0x4C]+0x54]` was already named, in two
places, by an arc that had measured it — and the search cost nothing next to the section
that had to be retracted.

## 15. MEASURED, on the harness (2026-08-17). The break is not delivery and not ordering

Three runs, loopback, build **38833**, `--game-args "--hero 1"`, one hero. Every site's
bytes were verified in the running process before arming; every run reached its map
(`RUN VERDICT: PASS`), so `worker` firing is a live control rather than a hope.

### 15.0 Running 38833 at all, because this cost two false starts

**The harness does NOT default to 38833.** `drive_client.py:87` selects "the newest
`vault/run/<dir>/Gw.exe` **THAT IS `build`**", and :167 records that 38833 is deliberately
excluded so the newest 38797 copy wins. §4's sentence "the harness runs whatever is staged
in `vault/run/`, and on this machine that is 38833" is **wrong on both halves** — the
selection is by build, and the build is the pinned 38797. Heroes' 38833 traps must have
passed `--exe`.

The first attempt did not, and `commandertrap.py` refused to arm — all four sites reported
`BAD … expected … got …`. That guard is the reason this section exists rather than a page
of confident nonsense; it is the §4 hazard caught from the other side, by the tool.

Two flags are needed, and the second is not obvious:

```bash
RURIK_DAT="C:/gd/Rurik/vault/run/2026-08-13_64fae3b1369b/Gw.dat" python toolkit/harness/session.py --replace --keep-open --hold 180 --warn 0 --exe "C:/gd/Rurik/vault/run/2026-08-13_64fae3b1369b/Gw.exe" --game-args "--hero 1"
```

Without `RURIK_DAT`, `contentids.py` refuses the launch: `content/maps.toml` binds maps 146
and 148 to a file id that `vault/dat_study/Gw.dat` and the 38833 run archive resolve to
**different files** (row 7982, 1,300,036 B, crc 0xA0AE500A vs row 177262, 1,300,044 B, crc
0x33F1A289). Pointing the server at the client's own archive makes the pair identical,
which is what `test_contentids.py:129` already describes as the clean configuration.

### 15.1 Run 1 — the chain stops between the raise and GmView

Sites `worker, bulkraise, bulk, create`:

```
  +0.000s  worker    0x00859010   party_id 1, msg+8 owner 1, msg+0xc agent 200,
                                  msg+0x10 heroId 1, msg+0x14 0
  +0.000s  bulkraise 0x00858850
  TOTALS   worker 1   bulkraise 1   bulk 0   create 0
```

- **`worker` fired** — our `0x01C2` reached the client's party worker, with exactly the
  fields `agents.py` sends. The control holds, so the zeros below are measurements.
- **`bulkraise` fired** — `0x00858850` ran, and both of its branches raise `0x10000114`
  (the `arg1 != 0` path at `0x008588AD`, the `arg1 == 0` path via `mov eax,0x10000114` at
  `0x008588D1` into the shared tail). So the event was raised.
- **`bulk` did NOT fire** — GmView's case 90, the *only* caller of the commander rebuild
  `0x00524E00`, was never entered.
- **`create` did not fire**, which is now a consequence rather than a finding.

**And the order refutes §14.3's ordering hypothesis outright.** `worker` fires *before*
`bulkraise`: the hero row is already in the container when the event is raised. Lateness
was the obvious story and it is wrong.

### 15.2 Run 2 — and it is not "raised into nothing" either

Sites `raise114, lookup114, bulk, worker`. `lookup114` is `0x0064CA47` armed off the raise
and taken down after one hit — the client's own subscriber-map read, so no rehash of
`0x004920B0` is involved:

```
  HIT worker
  HIT raise114   (push 0x10000114)
  HIT lookup114  SUBSCRIBED -- falls through to `call 0x64c7d0` with the list
  TOTALS  bulk 0
```

**`0x10000114` HAS a subscriber at the moment we raise it.** That is the opposite of what
heroes measured for `0x1000011E` (§34.1), and it kills the second obvious story: the event
is raised, it is delivered, and GmView's case for it still does not run.

So exactly one of three things is true, and run 3 separates them: the subscriber is not
GmView; GmView receives it but routes it somewhere other than case 90; or `bulk`'s address
is not that case body.

### 15.3 The live commander state, read without a breakpoint

`commanderpeek.py --events`, with the client in the map:

```
  container ctx+0x20   ptr=0x01E8A2F0  cap=7  count=0  alloc=21
  heroCommanderSlot    ['0x0','0x0','0x0','0x0','0x0','0x0','0x0']
  => NO COMMANDER EXISTS.
```

Capacity **7** — the hero-slot count again — and **count 0**. The reader also refused to
answer the subscriber half, naming its own failed control (`0x100001A4` is known live and
was not found in the bucket walk). That refusal is why run 2 used the client's own lookup
instead.

## 16. §14.2's CONTESTED point is SETTLED, and RESKIN was right

`0x00858850` is a thiscall, and its caller is the `0x01B2` handler:

```
0x008569E0   [RECV] 0x01B2 PARTY_SET_MINE
  ecx = [globals+0x4C] + 4          <- this, PRE-BIASED BY FOUR
  push [msg+8] ; push [msg+4] ; call 0x00858850

0x00858850(partyId, flag)
  esi = ecx
  partyId == 0 ? eax = [esi+0x50] : eax = [[esi+0x3c] + partyId*4]
  0x00858872  mov [esi+0x50], eax          <- THE WRITE
```

`[esi+0x50]` with `esi = [globals+0x4C]+4` **is** `[[globals+0x4C]+0x54]` — the pointer
`agents.py:369` and RESKIN §17.1 both name as `PyCliGetMyPartyId`, and the one §13.3
claimed had only two stores in the image, both behind an opcode we never send.

**§13.3 is refuted and §14.2 is closed in RESKIN's favour.** `0x01B2 PARTY_SET_MINE`
writes it, `agents.py:434` already sends it, and RESKIN §18's measurement of "1 after the
party build" is exactly this store landing.

The scan missed it for the reason `codescan.py` prints in its own footer: **the
displacement in the instruction is `0x50`, not `0x54`**, because the object pointer is
biased by four before the field is addressed. A displacement-anchored search cannot see a
field whose constant never appears. Resolution (1) of §14.2 — "my scan missed a store,
that is the way to bet" — was the right bet.

`0x01D9` remains a *second* writer of the same pointer, unsent by us, and nothing here
requires it.

## 17. Run 3 and run 4 — `0x10000114` never reaches GmView's frame handler

### 17.1 Run 3, and why its own result is not enough

Sites `raise114, gmvEvent, bulk, worker`. `gmvEvent` is `0x004E366A`, the first instruction
of the event half of GmView's frame handler (`sub eax, 0x10000007`), so EAX still holds the
raw event id when it fires. Armed off `raise114`, oneshot:

```
  HIT worker
  HIT raise114
  HIT gmvEvent   event id (eax) 0x10000021   is 0x10000114: False
  TOTALS  bulk 0
```

**That reading is weaker than it looks, and the reason is worth keeping.** `lookup`'s
deferred-oneshot argument works because `0x0064CA47` sits *inside* the raise's own
synchronous call chain — the next hit after the trigger is necessarily ours. `0x004E366A`
is not inside that chain: it is reached only *if* GmView's frame handler is entered for the
event. So "the next hit was a different event" is consistent with both "GmView never got
ours" and "GmView got ours through a door that does not pass here" — and heroes §36.7
named GmView's **subscriber** as `0x004ED055`, which is not this function. Two doors.

### 17.2 Run 4 — the census, which is the measurement that counts

Same site armed for the whole session instead (`gmvEventAny`, `--max-hits 3000`, so nothing
was capped):

```
  TOTALS  gmvEventAny 12   raise114 1   bulk 0   worker 1
  arm failures / resume failures 0 / 0
  distinct event ids GmView's frame handler was entered with:
      0x10000030   x10
      0x10000022   x1
      0x10000021   x1
  0x10000114:  ABSENT
```

**`0x10000114` is raised once, has a subscriber, and never once enters GmView's frame
handler.** `bulk` — the case that would run if it did — is 0 across all four runs, and
`worker` is green in all of them, so the machinery is proven on every run that reports a
zero.

**The honest limit of this census:** twelve hits and three distinct ids is a *small* sample
for a whole session. It is not a 4000-hit census like heroes §34.2's. What makes it usable
anyway is that the thing being counted is not rare — `raise114` fired inside the same
window, so the event we care about happened *while this site was armed and uncapped*. A
site that saw 12 events including none of ours, during a window that provably contained our
raise, is evidence about our raise specifically rather than about the population.

### 17.3 Where that leaves it, stated as three live possibilities

The subscriber list for `0x10000114` is non-empty (run 2) and GmView's frame handler is not
in the delivery path (run 4). So:

1. **The subscriber is some other module.** `codescan --xrefs 0x10000114` gives eleven
   sites; the pushes that are not the raise sit at `0x004A36C4`, `0x00539374`
   (GmPosseRoster's block, which §0 measured as never installed), `0x00562D51`,
   `0x0056856C` and `0x00568A79`. One of those is the live subscriber.
2. **GmView subscribes but with a callback that is not the frame forwarder.**
   `0x004ED033` is `add eax, 0x10000114` inside GmView — the shape of a loop registering a
   *range* of events — so GmView plausibly does subscribe to it, and the callback it
   registers for that range is then the thing to read.
3. **`bulk` is not case 90's body.** Least likely — the byte table at `0x004E66C4[0x10D]`
   selects case table entry 90, which is `0x004E5D20`, and `commandertrap.py` independently
   labelled that address "dispatch case 90" long before this arc — but it is listed because
   two runs of a zero do not distinguish "never called" from "wrong address".

**The next measurement is static and cheap: read GmView's subscribe block around
`0x004ED000..0x004ED060` and find what callback it registers for the range containing
`0x10000114`.** That separates (1) from (2) without another client run. If it turns out
GmView registers a non-frame callback for that range, the whole chain is explained: the
event is delivered to a callback that does not forward it into the frame, so the case that
rebuilds the commander model can never run from our raise — and the fix is not a message we
are missing but a UI module that is not up.

### 17.4 What four runs have now removed from the board

- Not delivery — the event has a subscriber (run 2).
- Not ordering — the hero row lands before the raise (run 1).
- Not the container — `0x01B2` writes it and RESKIN measured it non-null (§16).
- Not the identity — `ctx[0x44][0x2AC]` is CORROBORATED from both directions (§13.1).
- Not `0x1000011E` — the assert the player hits is on `0x100001A4`'s path (§10.2).
- Not `GmPosseRoster` — that is PvP-window furniture (§6), and the commander UI is
  `GmPetCommander` / `AgentCommander*` (§8).

What is left is one link: **between a delivered `0x10000114` and GmView's case 90.**

## 18. GmView's subscribe is CONDITIONAL, and `0x0199` field 5 picks the branch

§17.3 named the cheap static separator. Here it is, and it is a two-way switch on an
observer-mode bit.

`0x004ED010` onward is GmView's subscribe run — a straight sequence of
`push <event>; push esi; call 0x00633BD0`, one per event. One of them is not a literal:

```
0x004ED027   call 0x0084E020
0x004ED02C   neg eax ; sbb eax,eax        eax = (result != 0) ? -1 : 0
0x004ED030   and eax, 0x17               eax = (result != 0) ? 0x17 : 0
0x004ED033   add eax, 0x10000114
0x004ED038   push eax ; push esi
0x004ED03A   call 0x00633BD0             SUBSCRIBE
```

**GmView subscribes to `0x10000114` OR `0x1000012B`, never both**, and the predicate
chooses. Its neighbours in the same run are plain literals — `0x100000F1`, `0x10000118`,
`0x10000119`, `0x1000011E` (this is `0x004ED055`, the site heroes §36.7 named), `0x1000011F`,
`0x10000123`, `0x1000012A` — so the conditional one is deliberate, not an artifact.

The predicate is four instructions:

```
0x0084E020   eax = <globals>
             eax = [eax+0x44]            the mission-client context
             eax = [eax+0x2A8]
             return (eax >> 4) & 1       BIT 4
```

`MsCliApi` (its only assert is `MsCliApi:821 context->observeTable.Find(gameKey)`), and
bit 4 of `[ctx+0x2A8]` is written in exactly one place — **`0x0199`'s handler**, which §12
already read:

```
0x0084EF00   [RECV] 0x0199 GAME_SMSG_INSTANCE_LOAD_INFO
             …
             if ([msg+0x18]) [ctx+0x2A8] |= 0x10        <- BIT 4
             else { [ctx+0x234] = [msg+0x08]; [ctx+0x23C] = [msg+0x0C]; }
```

`msg+0x18` is `0x0199`'s **sixth field**, and `authsrv.py:5566` names it in its own send:
`[PLAYER_AGENT_ID, map_id, is_explorable, district, language, **is_observer**]`.

### 18.1 We are on the right side of the switch, so this is NOT the cause

We send `is_observer = 0`. Bit 4 stays clear, `0x0084E020` returns 0, `eax` stays
`0x10000114`, and **GmView subscribes to the event we raise.** The conditional is
eliminated as the explanation, which is worth as much as finding it would have been — it
was the best remaining candidate and it is dead.

Two things fall out anyway and both are keepers:

- **`0x1000012B` is the observer-mode twin of `0x10000114`.** In an observer session GmView
  watches a different event for the same rebuild. Nothing in this project has needed that
  yet; it is written down so nobody re-derives it.
- **`0x0199` field 6 is load-bearing beyond the map type.** `authsrv.py` documents field 1
  (`PLAYER_AGENT_ID` → `ctx[0x2AC]`, heroes §22) and field 3 (the map-type byte,
  `--explorable`/`--outpost`). Field 6 also steers which event GmView listens on. A run
  that ever sets `is_observer = 1` should expect the commander rebuild to stop working,
  and now knows why.

### 18.2 What that leaves, and it is the one thing runs 1–4 did not time

GmView subscribes to `0x10000114`. We raise `0x10000114`. `lookup114` reads the list as
non-empty at raise time. And GmView's frame handler is never entered for it.

The one arrangement consistent with all four: **the subscriber present at raise time is not
GmView, because GmView has not subscribed yet.** Our raise fires at instance load —
`raise114` at `+0.000s`, alongside `worker` — and GmView's subscribe run is UI construction,
which happens when the UI comes up. Nothing re-raises `0x10000114` afterwards, so the
commander model is built once, from an empty container, and never again.

Note carefully that this is **not** §14.3's ordering hypothesis, which run 1 refuted. That
one was about our own messages' order relative to each other, and it is still dead: `worker`
fires before `bulkraise`. This is our raise's order relative to **the client's own UI
construction**, which we do not control and did not measure.

It is also the same shape heroes §34 measured for `0x1000011E` — raised at load into a map
that fills later — which would make it one cause behind two arcs' worth of symptoms.

**Run 5 times it directly**: the `subscribe` census armed for the whole session alongside
`raise114`, and the timestamps say which came first.

## 19. ANSWERED. GmView subscribes 53 ms after we raise, and nothing raises again

Run 6, sites `gmvSub114, raise114, bulk, worker`, all four in the ordered hit list so the
timestamps are directly comparable. `gmvSub114` is `0x004ED03A`, GmView's **conditional**
subscribe call, with EAX carrying the id it is about to register — so the site re-measures
§18's branch instead of trusting the static reading:

```
  +0.000s  worker     0x00859010   party_id 1, owner 1, agent 200, heroId 1
  +0.000s  raise114   0x008588AD   push 0x10000114
  +0.053s  gmvSub114  0x004ED03A   event being subscribed (eax) 0x10000114
                                   branch: NORMAL -- 0x10000114, the event we raise
  TOTALS   gmvSub114 1   raise114 1   bulk 0   worker 1
```

**GmView subscribes to `0x10000114` fifty-three milliseconds after we raise it.**

That is the whole chain, and every earlier zero falls out of it:

```
+0.000s   our 0x01C2 appends the hero row to the container          (worker)
+0.000s   our 0x01B2 raises 0x10000114                              (raise114)
             the subscriber map has SOMEONE in it (run 2) -- not GmView
             GmView's frame handler is not entered                  (bulk 0, run 4 census)
+0.053s   GmView subscribes to 0x10000114                           (gmvSub114)
             ...and nothing ever raises it again
          so the rebuild 0x00524E00 never runs
          so 0x00524C40 never runs                                  (create 0, run 1)
          so the commander container stays cap=7 count=0            (commanderpeek)
          so the party-row click asserts commander / GmView:5890
```

§18.2 predicted exactly this and named it as the one arrangement consistent with runs 1–4.
It is now measured rather than inferred, on the ordered list, with the branch re-read at the
site.

### 19.1 Why this is one cause behind two arcs

Heroes §34 measured `0x1000011E` raised with **no subscriber at all**. GmView's subscribe
run registers `0x1000011E` too, at `0x004ED055` — eleven instructions after the
`0x10000114` call this run timestamped, so within the same 53 ms window. Both events are
raised at instance load, into a map that fills immediately afterwards.

So heroes' finding and this one are the **same defect seen from two events**: our
party/hero messages arrive before the UI that listens for their consequences exists.
Nothing about the wire fields was ever wrong.

### 19.2 The fix, and its prediction stated first

**Re-send `0x01B2 PARTY_SET_MINE` a second or two after instance load.** Its handler
(`0x008569E0` → `0x00858850`) re-resolves the container and raises `0x10000114`
unconditionally on both branches (§15.1), so a second send is a second raise — this time
into a map that contains GmView.

> **Predicted:** `bulk` fires (GmView's case 90 entered for the first time in this
> project), the rebuild `0x00524E00` runs, `0x00524C40` runs once per hero row whose
> `msg+8` matches `ctx[0x2AC]`, `commanderpeek` reports a non-zero commander count, and the
> party-row click stops asserting.
>
> **Refuted if:** `bulk` fires and `create` does not — then the container the rebuild walks
> is not the one our rows went into, and §16's identification is wrong somewhere. Or
> `bulk` does not fire — then GmView's subscription is not what gates case 90 and something
> else in the frame path does. Or the client asserts on the second `0x01B2` — then
> PARTY_SET_MINE is once-per-connection like `0x01D2` is (`PyCliParty:1228`), and the
> re-raise has to come from somewhere else.

This is deliberately **not** `--hero-late`. Heroes already deferred the hero *pipeline* and
measured that it still asserted; what has never been deferred is the **raise**. The rows can
stay exactly where they are — §15.1 measured them landing before the raise, which is the
order the rebuild needs.

## 20. THE FIX WORKS. A commander exists for the first time in this project

`--party-mine-late 2.0`, one hero, build 38833, loopback. Sites `bulk, create,
raise114, worker`, all four in the ordered list:

```
  +0.000s  worker     0x00859010   party_id 1, owner 1, agent 200, heroId 1
  +0.000s  raise114   0x008588AD   the load-time raise -- into a map without GmView
  +2.048s  raise114   0x008588AD   OUR LATE RE-SEND
  +2.048s  bulk       0x004E5D20   GmView's case 90 ENTERED
  +2.054s  create     0x00524C40   the get-or-create RAN
  TOTALS   bulk 1   create 1   raise114 2   worker 1
```

**`0x00524C40` has never run once in this project before this line.** Heroes §26 measured
it cold; §11 explained the coldness as an empty loop; §19 found the reason the loop never
ran. Here it runs, 6 ms after the case that calls it, 0 ms after the raise that reaches the
case. The causal chain is not inferred — it is four timestamps in one list.

And the end state, `commanderpeek.py` with the client still in the map:

```
  container ctx+0x20   ptr=0x006B6538  cap=7  count=1  alloc=21
  heroCommanderSlot    ['0x1', '0x0', '0x0', '0x0', '0x0', '0x0', '0x0']
  => 1 commander(s) EXIST.
```

Against the same reading before the fix (§15.3): `count=0`, every slot `0x0`. **One
message, re-sent two seconds later, moves the commander container from empty to bound.**

§19.2's prediction is met on every clause it named: the rebuild ran, `0x00524C40` ran, and
the commander count is non-zero. None of the three refutations fired.

### 20.1 What is NOT claimed here

- **The party-window hero button has not been clicked.** Whether `GmView:5890` still fires
  is a separate measurement and it needs a click. Everything above is structure state read
  out of memory, which is the half that does not need a hand on the mouse.
- **`commanderpeek.py`'s closing line is a canned message, not a finding.** For `count > 0`
  it prints "the assert is NOT 'nothing was created' — it is a KEY MISMATCH between what
  the button passes and what the slots hold." That sentence was written when the tool's
  author expected the count-positive case to mean something specific; it is a hypothesis
  printed unconditionally, and nothing in this run tests it. Read it as a prompt, not a
  result. (Worth fixing in the tool: a verdict string that cannot be wrong is not a
  verdict.)
- **`n = 1`.** One run, one hero. The timeline is unambiguous and the before/after on the
  container is a clean contrast, but the arc's own §3 note stands: this project has had a
  memorable, clean, completely wrong answer before, and it took a control to catch. The
  control here is that `worker` and the first `raise114` fire identically in the runs
  where `bulk` and `create` do NOT (runs 1–6), so the only thing that changed is the
  second raise.

### 20.2 What this unblocks

The heroes arc's wall was `0x00524C40` never running, and behind it the belief that the
commander was not server-reachable. Both are gone. The remaining hero questions — whether
the button works, whether `AgentCommander{slotIndex}` renders, what `0x100001A3`/`0x100001A4`
do downstream — are now questions about a commander that EXISTS, which is a different and
much cheaper kind of question.

It also retires the framing this arc opened on. §0 inherited "the commander event
`0x1000011E` is raised into nothing" as the settled cause. The real cause was a *different*
event (`0x10000114`), raised into a subscriber map 53 ms too early, and fixed by re-sending
a message we were already sending. Nothing about the wire fields was ever wrong — §13.1's
identity, §16's container, §12's payload mapping all held up. What was wrong was **when**.

## 21. The `+4` trap: §13.3 and §16 both need correcting, in opposite directions

A four-agent static fan-out (read-only, build 38833, adversarially verified) went back over
§14.2's contested point and found something neither §13.3 nor §16 had: **every message
worker in the party subsystem is called with `this = party_object + 4`.** Verified here by
hand on the two load-bearing claims.

```
0x00856310   PyCliGetMyPartyId, and it is NOT 0x00856250
  call 0x47f660 ; mov eax,[eax+0x4c] ; mov eax,[eax+0x54]
  test eax,eax ; je -> return 0
  mov eax,[eax] ; ret          <- returns the container's OFFSET 0, which is partyId
```

So RESKIN §17.1's "`[[ctx+0x4C]+0x54]` dereferenced" is exactly right, and its measured "1"
means *m_partyClient is non-null and its partyId is 1*. The VA in `agents.py:369` and
RESKIN (`0x00856250`) is mid-body of an unrelated function on 38833 — a build slip of the
same family as §4, in the other direction.

### 21.1 §16 stands; its closing sentence does not

`0x00858872 mov [esi+0x50], eax` in `0x01B2`'s worker **is** the `m_partyClient` store —
§16 got that right, and the field now has ArenaNet's own name for it, four instructions
later: `PyCliParty:650 m_partyClient` at `0x00858887`.

But §16 ended "`0x01D9` remains a *second* writer of the same pointer." **That is wrong.**
`0x00857200`, the `0x01D9` handler, does `add ecx, 4` at `0x00857216` exactly like the
others — so `0x0085A340`'s `[esi+0x54]` stores are `party_object + 0x58`, a *different*
field holding an integer party id that is only ever compared, never dereferenced (a
constructor at `0x008578E5` zeroes `+0x58` separately). **`0x01D9` does not write the
container pointer at all**, and §13.4's whole experiment — "send `0x01D9` to create the
default party" — was aimed at a field that has nothing to do with it. Retracted for the
second time and now for the right reason.

The complete writer set of `m_partyClient`, by this method: `0x008578DE` (constructor,
zero), `0x00857DA0` (reset, zero), `0x00858872` (the `0x01B2` set), `0x0085887B` (the
`0x01B2` out-of-range clear). Four sites, one opcode.

### 21.2 So §14.2's two candidate resolutions were both wrong

§14.2 offered "(1) my scan missed a store — that is the way to bet" or "(2) RESKIN misreads
`PyCliGetMyPartyId`". **Neither.** `codescan --field 0x54` searched correctly and found the
two `+0x54` stores that exist off the *object* base; it simply cannot see a field addressed
through a `this` biased by four, where the same field is spelled `0x50`. And RESKIN read its
function correctly. Both artifacts were right about different things, and the disagreement
was an artifact of the C++ subobject convention sitting between them.

**The generalisable bit, and it is worth more than this arc:** in `PyCliParty`'s workers,
*every* displacement is four less than the field's name from the global. `[edi+0x50]` is
`+0x54`, `[ebx+0x3c]` is `+0x40`, `[edi+0x44]` is `+0x48`. A displacement-anchored search
over this subsystem must be run at **both** offsets, or it will produce a confident zero.
That belongs in `codescan.py`'s footer next to the other blind spots it already names.

## 22. WHOSE commander, and a defect in the probe that asked

Run 9 armed a capture on `create` (`0x00524C40`) reading its argument, because §20 could
show a commander existing but not whose — `heroCommanderSlot` holds container KEYS, not
agent ids.

```
  return address        0x00EC4FA9   ->  VA 0x00524FA9
  agent id (arg0)       0x00000001
  VERDICT               agent 1 gets the commander -- the PLAYER, not the hero
  TOTALS   create 1   bulk 1   worker 1
```

**Two things there are wrong, and both are mine.**

1. **`from the rebuild loop: False` was a bug in the probe.** It compared the *slid* runtime
   return address against the *static* `0x00524FA9`. Un-slid, `0x00EC4FA9` **is**
   `0x00524FA9` — the call came from exactly the rebuild loop the check was written to
   confirm. Fixed: `commandertrap.py` now carries the target's `SLIDE`, set once in `main`,
   and `unslide()` turns a runtime pointer back into a VA. A capture that silently answers
   the wrong question is the failure this module exists to prevent, and it had one.
2. **"the PLAYER, not the hero" was a misreading of what `arg0` is.** The rebuild passes
   `[item+8]`, and `agents.py:510` names `item+8` as `0x01C2`'s **`scan_key`** (msg+0x10) —
   which callers fill with the **hero id**, not an agent id. A `1` here is *hero 1*, not the
   player's agent 1. The two collide on the default rig, which is precisely the confusion
   `--player-number` was added to break.

### 22.1 What run 9 actually measured, and why it matters

**The commander is filed under `scan_key`.** We send `scan_key = hero_id = 1`, and that is
the key `0x00524C40` receives and the container is keyed by.

`agents.py:510`'s docstring says of that field: *"That the commander scan reads entry+0x8 as
its container key is SOURCED (17.1); every OBSERVABLE consequence is indifferent to the
value (19.2: a wrong value changes nothing, the right one fixed nothing), consistent with
the scan never running in our sessions."*

**That last clause is now obsolete.** The scan runs (§20). `scan_key` has become observable
for the first time in this project, and it is the key the commander is filed under. Heroes
§19.2's "a wrong value changes nothing" was true only while nothing read it.

### 22.2 The next experiment, prediction first

§10.1 measured the button's path: a party-row click raises `0x100001C2` carrying the agent
id, and GmView's case calls `0x00524DB0(<that>)` to find the record. If the lookup key is an
**agent id** and the container is filed under **hero id**, they cannot match — which is the
mismatch `commanderpeek`'s canned line guesses at without testing.

> **Send `scan_key = 200` (the hero's agent id) instead of the hero id**, via the existing
> `--hero-roster-id 200`, together with `--party-mine-late 2.0`.
>
> **Predicted:** `create` fires with `key (arg0) = 200`.
>
> **What that does NOT settle:** whether the button then works. `0x00524DB0`'s argument
> being an agent id is a RECONSTRUCTION from §10.1's disassembly, not a measurement — the
> call has never been observed running, because it needs a click. So a matching key is
> necessary-if-the-reconstruction-holds, and nothing more. **The click remains the owner's.**

## 23. Run 10: the key is steerable, and the probe's own fix verified itself

`--hero-roster-id 200 --party-mine-late 2.0`, same rig otherwise:

```
  return address (VA)    0x00524FA9      <- un-slid correctly this time
  from the rebuild loop  True
  key (arg0)             0x000000C8  (200)
  TOTALS   create 1   bulk 1   raise114 2   worker 1
```

Three things at once:

- **§22.2's prediction is met.** `scan_key` steers the key the commander is filed under, so
  the container can be keyed by the hero's agent id instead of the hero id.
- **The §22.1 probe fix verified itself.** The same site that reported
  `from the rebuild loop: False` for a call from `0x00524FA9` now un-slides and reports
  `True`. The bug was in the probe, not the client, and the repair is confirmed by the
  measurement it was blocking.
- **The chain is unchanged by the key.** `bulk`, `create` and the second `raise114` all
  still fire, so changing `scan_key` costs nothing that §20 established.

### 23.1 Retired: "scan_key is indifferent on every observable"

`agents.py:510` records, from heroes §19.2, that a wrong `scan_key` "changes nothing" and a
right one "fixed nothing" — correctly reasoned at the time, and explicitly hedged there as
*"consistent with the scan never running in our sessions."* The scan runs now (§20), and the
value it reads is this one. **The clause is retired, and the hedge is why it can be retired
cleanly rather than argued about.**

### 23.2 What is still NOT measured, and it is the same thing as in §22.2

A commander now exists, filed under a key we control. Whether the **button** works is
untouched:

- `0x00524DB0`'s argument being an **agent id** is a RECONSTRUCTION from §10.1's
  disassembly. That call has never been observed executing, because it runs only on a
  party-row click.
- So "key 200 matches what the button passes" is an inference resting on that
  reconstruction, not a measurement. Key 1 vs key 200 might both fail, or both work, for
  reasons the static read did not capture.
- `commanderpeek.py`'s "it is a KEY MISMATCH" line still asserts this without testing it,
  and still should not be quoted (§20.1).

**The click is the measurement, and `session.py --walk` has no click verb by deliberate
design** — "keyboard rather than a click on purpose", because a held key makes the server
answer with a direction while a click would be our own clip. So this last step belongs to
the owner, and the two arms worth running are `--hero-roster-id 200` against the default
`--hero-roster-id 1`, both with `--party-mine-late 2.0`.

## 24. THE ASSERT MOVED TWICE. The commander binds and the panel opens

Two owner-driven clicks on the party window's hero button, build 38833 (the crash dialog
states it), both with `--party-mine-late 2.0`. Quoting each crash dialog's own first two
lines, which is text the retail client shows any player who crashes:

| arm | click result |
|---|---|
| before this arc | `Assertion: commander` / `GmView.cpp(5890)` |
| `--hero-roster-id 200` | `Assertion: heroData` / `GmView.cpp(5897)` |
| default key (hero id 1) | `Assertion: heroData->agentId` / `GmView.cpp(5898)` |

**The commander assert is gone.** `GmView:5890` and `:5891` (`commander`,
`commander->slotIndex < DLG_AGENT_COMMANDERS`) both pass now. Reading the case confirms what
that buys:

```
0x004E38DA   ebx = payload[0]
             commander = 0x00524DB0(edi)
             assert commander                          :5890  <- WAS the crash, now passes
             assert commander->slotIndex < 7           :5891  <- passes
0x004E3921   ShowFloatingDialog(ebx, commander->slotIndex, show=1, 0)
                                                       <- THE PANEL IS OPENED
             heroData = 0x0080E370(edi)
             assert heroData                           :5897
             assert heroData->agentId  ([heroData+4])  :5898
```

`ShowFloatingDialog` runs *between* the two asserts, with `commander->slotIndex` as the
dialog index — so the `AgentCommander{n}` window is constructed before the failure. The
click now gets further than "no commander exists" by two asserts and one window.

### 24.1 The two arms are a matched pair, and they name the key rule

Both lookups in that case take **the same `edi`**. `0x00524DB0` finds the commander;
`0x0080E370` finds the hero-data record in `[globals+0x2c] + 0x584`.

- With `--hero-roster-id 200` the commander is filed under 200 (§23) and heroData under the
  hero id — so heroData misses, `:5897`.
- With the default the commander is filed under 1 and heroData under 1 — heroData is
  **found**, and the failure moves to its `agentId` field, `:5898`.

**So the commander container and the hero-data cache must be keyed alike, and the key is the
hero id.** §22.2's guess — that the button passes an agent id and `scan_key` should be 200 —
is refuted by its own experiment. `--hero-roster-id` should be left at its default.

### 24.2 What `heroData->agentId` is NOT

`0x0074`'s worker chain is `0x0091E350` → `0x00811560` → `0x0081DB70`, and the last one
writes the payload into the record starting at **`[rec+8]`**:

```
0x0081DBCC   [esi+0x08] = arg1 ; [esi+0x0C] = arg2 ; [esi+0x10] = arg3 ; [esi+0x14] = arg4 …
```

`+0` and `+4` are not among them — they belong to the record's creation
(`0x0081D700`, an array grow with stride **0x9C**). **So `agentId` at `+4` is not carried by
`0x0074`'s payload at all**, and no combination of `mercenary_info`'s arguments can set it.
The field is written by whatever links a hero record to its spawned agent.

**The lead, UNVERIFIED:** the container has 28 `+0x584` sites. One family sits at
`0x0080E460`, which does `0x0081DE20(container, hero_id, <something>)` and guards
`hero <= 0x28` with asserts `0x1178`/`0x1179` — the `ChCliApi` `hero < HEROES` family
heroes §1 already met (`HEROES = 40`). `0x0081DE20` is the next thing to read, and it is
desk work.

### 24.3 One loose observation from the screenshots

The party window renders the hero row as **`Lvl 255`**. Not investigated, not obviously
related to any of the above, and recorded here only so the next reader does not think it is
new — a level that reads 255 where 20 is the game's cap is the shape of an unset or
sign-extended byte, and `0x0074`'s level field is one of the arguments we send as zero.

### 24.4 Method correction: the harness reads the assert itself

§23.2 said "the click is the measurement" and left the whole readout with the owner. Half of
that is wrong, and it matters for how the remaining arms get run.

`session.py` **captures the crash dialog on its own** — the Arm B run wrote
`vault/captures/harness/20260817T170749/crash-dialog.txt` and printed
`>>> Assertion: heroData->agentId` into its own verdict, alongside `report.json` and
screenshots, and still finished `RUN VERDICT: PASS (target: map)` because the map rung was
reached before the crash.

So the owner-dependent part is **only the click**. The assert text, the dialog, the logs and
the screenshots all come back without anyone reading a screen — which means an arm costs one
click and nothing else, and the result is a file rather than a transcription. Future arms
should quote `crash-dialog.txt` rather than a screenshot, and can be diffed against each
other directly.

(The two arms of §24 are `20260817T170549` — `heroData` — and `20260817T170749` —
`heroData->agentId`.)

## 25. `0x0072` was never sent, and sending it clears the whole GmView chain

`GmView:5898` is `[heroData+4]`. Traced to its only writer, in four hops:

```
0x0081DA90(this, hero_id, agentId, …)      [rec+4] = arg1      assert :199 if no record
  one caller   0x00811530  (ecx = [globals+0x2c]+0x584, the same container)
  one caller   0x0091E2A0  = the RECV handler for opcode 0x0072
0x0072  HeroActivate (hero, agent, inventoryId, aiMode)   -- the client's own format string
```

**And `0x0074` zeroes that field itself.** `0x0081DBF8 mov [esi+4], 0` sits in the create
path of `0x0074`'s worker, so the data-cache message deliberately leaves `agentId` null for
someone else to fill. §24.2 concluded no `mercenary_info` argument could set it; this is why.

**We had never sent `0x0072`.** `authsrv.py:2298` is `HERO_ACTIVATE = False` and the send
site reads `for … in (hero_slots() if HERO_ACTIVATE else ())`. Not a payload bug, not a
missing message in the schema — an opt-in flag that no run of this arc had turned on.

With `--hero-activate` added, the click clears `:5898` and leaves `GmView` entirely.

### 25.1 Four asserts of progress, in one session

| arm | assert |
|---|---|
| before this arc | `commander` — `GmView.cpp(5890)` |
| `--party-mine-late` + `--hero-roster-id 200` | `heroData` — `GmView.cpp(5897)` |
| `--party-mine-late` | `heroData->agentId` — `GmView.cpp(5898)` |
| `--party-mine-late --hero-activate` | `inventory` — **`ItCliApi.cpp(488)`** |

The commander chain is **finished**: the commander binds, its `slotIndex` is in range, the
`AgentCommander` window is constructed, `heroData` resolves, and its `agentId` is set. Every
assert in `GmView`'s case for `0x100001A4` now passes.

### 25.2 The new blocker is a different subsystem, and probably a known one

`ItCliApi:488` is at `0x0084557C`, inside `0x00845530(owner, slot, out)`:

```
  [out] = 0
  assert slot < 9                       :485  ITEM_EQUIP_SLOTS = 9
  inventory = 0x00844660([globals+0x40] + 0xD4, owner)
  assert inventory                      :488   <- HERE
```

That is a **general** "equipped item in slot N" helper — **22 callers** across the UI — so
the failure is not specific to the commander panel: whatever is now drawing wants the hero's
gear, and the hero has no inventory registered in the item client's table.

**`--hero-inventory` is NOT the fix.** Its own help text targets `ItCliApi:1194`
(`inventoryTable.Get(inventoryId)`), a different site; ours is the equip walk, reached with
the owner rather than an inventory id.

**RECONSTRUCTION, and it should be checked before anyone spends a day on it:** this looks
like the item-authoring gap the unit-setup arc already listed as open — "`0x006D` NPC weapons
at create (needs item authoring the content store cannot do yet)". If so, the commander is
no longer the blocker and hero equipment is, which is a different arc with a known
prerequisite. Confirm that before treating it as new work.

### 25.3 ANSWERED the same day, by the arc that owns the other half

§25.2 asked for that check before anyone spent a day on it. The unit-setup arc ran it and
wrote the answer into `PLAN.md` §8's own entry (*"refined 2026-08-17 after the heroes arc
hit ItCliApi:488 and asked whether its blocker was this line"*). The verdict is **half**,
and the half matters:

- **Floor one — item RECORDS — already exists**, and my reconstruction was wrong to treat
  it as missing. The armor probe declares content-row items via `0x0161`, and a census over
  all three keyed captures found retail's `0x006D` ids are exactly such records: **375/375**
  non-zero ids declared earlier in the same stream by the `0x015E` family, zero exceptions.
  What `0x006D` still lacks is per-NPC-type weapon ROWS — content, not machinery. (And
  **210/585** retail `0x006D`s carry item **0**, a legal no-weapon value needing no
  authoring at all.)
- **Floor two — a per-OWNER inventory container in the item client's table at
  `[globals+0x40]+0xD4` — is what `ItCliApi:488` actually wants**, and it does not exist for
  the hero. Our `0x013F`/`0x013E` bag family has only ever been addressed to the local
  player. Same subsystem as the `0x006D` line, different missing piece.

So `ItCliApi:488` is **not** a duplicate of the unit-setup arc's open item line, and it is
not blocked behind it either. It is this arc's to price, and the shape of the work is now
named: find what registers an owner in that table and send it for the hero. Note the
pattern — this is the **fifth** time in the heroes lineage that the missing mechanism turned
out to be an existing agent-keyed message we only ever addressed to the player (after
`0x0037`, `0x003A`, `0x00B7`, `0x00DA`). Look for the bag family's owner argument before
concluding anything is absent.

(§26 priced it the next day, and one word above needs correcting on the way in: the table
is keyed by **inventory id**, not by owner — the owner indirection lives one hop earlier,
in the hero activation record. The registrar turned out not to be the bag family but their
prerequisite, `0x0144` — the sixth instance of the pattern, and this time the message was
not merely in the tree but already being sent, one line above the bags.)

## 26. `ItCliApi:488` priced: the chain is `0x0144` → activation record +8 → equip walk (2026-08-18)

Desk work and corpus only — no client launched. Every VA below is **build 38797** (the
pinned pristine build; §4's hazard, stamped as it demands). Tools: `codescan.py`,
`msghandler.py`, `asserts.py`, and a scratch census over the live captures via `tape.py`.

### 26.1 The table, and its one wire-side registrar — OBSERVED (static)

The `+0xD4` table §25.2 called "per-owner" is ArenaNet's **`inventoryTable`**, and their
own assert names it: `ItCliApi:1194 context->inventoryTable.Get(inventoryId)` sits in a
function (`0x00847E70`) doing the identical lookup — `0x8445A0` on `[globals+0x40]+0xD4` —
that the equip helper does. The key namespace is **inventory ids**.

The insert into that table is `0x84A060`, and it has **exactly one direct caller in the
image**: the `0x0144 ITEM_STREAM_CREATE` receive handler (`0x00846260`), which looks the
key up first and asserts `!inventory` (`ItCliApi:2010`) — a key may be declared once. So
the one message that can make the equip walk find anything is the one the server already
sends for the player, `authsrv.py`'s `ITEM_STREAM_CREATE [1, 0]`.

**The corpus agrees, 38/38 — OBSERVED** (`toolkit/authsrv/invcensus.py`, rerunnable; the
count was 20 when first measured and 38 by the time the tool landed the same day, because
the vault grew under the session — rerun it rather than quoting either number). Every
decodable live connection carries exactly
one `0x0144 [key, 0]`: field 2 is always 0, and all nine `0x013F` bags on that connection
cite the connection's key as their field 1. And the key is an **arbitrary per-connection
handle**, not a character id — the same character drew 1, 23, 184, 188, and 4 on different
connections, including three distinct keys inside one capture (`20260817T183756`). That
refutes `studies/smsg/FINDINGS.md`'s INFERRED reading of `0x013F` field 1 ("consistent
with the local character's id"), corrected there with a pointer here.

**Zero `0x0072` in the whole corpus (38 connections).** No retail tape ever activated a
hero, so the hero
half below is static tracing with a loopback experiment staged, not an observed wire
sequence — there is nothing in the vault to imitate.

### 26.2 The hero half: `0x0072` field 3 is stored, then read back by the party window — OBSERVED (static)

`0x0072`'s worker (`0x81DA40`, the function §25 traced for `agentId`) does three things
behind its `:199` record assert: writes `[record+4] = agentId` (§25), writes
**`[record+8] = inventoryId`** — field 3, the one `HERO_INVENTORY` sends as 0 — and raises
event `0x10000038` with that record as payload. Three modules subscribe: `GmView`
(`0x004ECD2A`), the search-party dispatcher (`PtSearchHeroList`/`PtSearchPartyList`,
whose case just relays UI message `0x59`), and **`PtHero.cpp`** (`0x005779BE`) — the
party-window hero row, the very UI the §25 click drives.

When PtHero draws a row's gear it resolves the equip-walk key through **`0x5265B0(agentId)`**:

```
assert agentId != 0
if agentId == localPlayerAgent():          0x80D3E0
    return *[itemctx+0xF8]                 0x845890, the local inventory (asserts :687)
rec = heroActivationRecord(agentId)        0x80E390
return rec ? [rec+8] : 0                   <- 0x0072 field 3, read back
```

and hands the result to the equip helper (`0x845470`: `:485 slot < ITEM_EQUIP_SLOTS`,
`:488 inventory`). With `HERO_INVENTORY = 0` the key is 0, the table holds no key 0, and
the lookup fails — **the model retrodicts §25.1's measured crash exactly, argument by
argument.**

Two neighbouring non-findings worth keeping: the hero-module equip callers
(`0x81DE86`/`0x81DEEB`/`0x81DFAD`) and `GmPartyContext`'s (`0x0050CE2C`) all key by the
**local** inventory via `0x845890` — mercenary-snapshot and context-menu paths drawing
*your* gear, not the hero's. And the slot walker `0x84AA50` returns empty **cleanly** when
`[inventory+0x58]` (the equip bag) is null, so the container alone is what `:488` needs —
bags matter only once there is gear to draw.

### 26.3 The staged experiment, predictions first — RECONSTRUCTION until clicked

`--hero-bags` (new, opt-in, refuses keys 0 and 1) sends `0x0144 [HERO_INVENTORY, 0]` plus
the equipped-items bag `0x013F`, in the REQUEST_ITEMS burst beside the player's own. The
rig is §25's — `--party-mine-late 2.0 --hero-activate` — plus the new arms, and the click
is the same party-window hero button the owner drove in §25:

| arm | prediction |
|---|---|
| `--hero-inventory 2` alone | still `ItCliApi:488` — the key flows but names nothing |
| `--hero-inventory 2 --hero-bags` | `:488` clears; the panel proceeds, empty gear being legal per `0x84AA50` |

Anything else the cleared click hits next is a new floor and belongs here when it lands.

## 27. The cleared click's next floor: `Array:587` in the char client, and `0x009A` is the registrar (2026-08-18)

§26.3's arm ran the same day. **`ItCliApi:488` CLEARED — both predictions held** — and the
click died one floor deeper: `Assertion: index < m_count / Array.h(587)`, build 38833
(dialog). The harness captured ArenaNet's **full crash report** including a 40-frame stack
(`vault/captures/harness/20260818T121224/crash-dialog.txt`), which is what made this floor
cheap: everything below is desk work over that stack, three fan-out rounds of it, with the
load-bearing hops re-verified by hand. Runtime base `0x00330000`, so static = PC +
`0xD0000`; the deepest frame rebases into the assert routine `0x00487BC0`, which anchors
the rebase. **All VAs in this section are 38833 static** (the click's own build, unlike
§26's 38797).

### 27.1 The chain, frame by frame — OBSERVED (static, retrodicting the dialog's stack)

```
PtTeamAgent (party-row click)  ->  GmView case 0x100001A4 [0x004E38DA..]
  :5890/:5891/:5897/:5898 all pass, ShowFloatingDialog opens AgentCommander{slot}
  0x004E396D  FrameSendMessage(dialogFrame, 0x56, heroData->agentId, 0)
AgentCommander proc 0x004FB500, case 0x56 [0x004FB5E2]
  stores agentId at commanderObj+4 (0x004FC7B6); title refresh 0x004FCB80
  (its three per-agent lookups all TOLERATED id 200); child sends;
  0x004FC884  child 3 (the paperdoll) <- msg 0x64, param agentId
GmAgentDoll proc 0x005374A0, msg 0x64 -> SetShownId 0x00538030
  stores id at doll+4; clears 9 slots; PushAppearance 0x005381F0
    id != localPlayer -> CharBy 0x0080CE60(200)
      cmp 200, [charctx+0x7D4]  ->  Array:587    <- THE CRASH
```

Two vocabulary facts fell out, named by the client's own assert `GmAgentDoll:1039`
(`!((hdr.msgId >= FRAME_MSG_EX) && (hdr.msgId < DOLL_MSG_EX))`): **`FRAME_MSG_EX = 0x56`**
(the `0x56` in the crash args is a frame-message id, not data) and **`DOLL_MSG_EX = 0x64`**.
The commander case's *last* act raises event `0x1000018E` with the agent id — it never got
that far.

### 27.2 The table, and who can grow it — OBSERVED, with one correction that kills the obvious fix

`CharBy` indexes the char client's **char-by-id table** at `[charctx+0x7CC]` (count
`+0x7D4`, stride 0x38). Its grower is the ensure-helper `0x00817A80`, and **all nine of
its direct callers are attributed**:

- **Four GAME_SMSG opcodes grow it from the wire**, all generic unnameds in our schema:
  **`0x009A`** `[agent_id, dword]` (setter `0x008124E0` — and the ensure runs **before**
  the bounds check, so one send registers the id, then writes `record+0x30`);
  **`0x009B`** `[agent_id, string16]` (`record+0x34`); **`0x009F`** and **`0x00A0`**
  (selected cases of the shared property setter `0x00812790`). The `0x009A` chain was
  re-verified by hand on the run's own exe (`msghandler.py 0x009A --follow`), byte for byte.
- The rest are the internal dispatcher path (`0x0081B270` case 0 → `0x0080D750`) plus one
  indirect-only sibling (`0x00815270`).

**The correction: `0x0020 WORLD_CREATE_AGENT` never grows this table.** Traced end to end:
the create handler (`0x005FD080`) is the *sole* static route into the per-class factory
table, and class 1 — which our creates select via field 3, `AGENT_TYPE_LIVING` — does build
a char **object** (`0x00824640`, agent id at `char+0x14`) and files it in a registry. But
nothing on that path touches `+0x7CC`. So **`--hero-body` is not this floor's fix**; the
first-instinct hypothesis is refuted in the disassembly. (Whether the runtime event pump
later posts the case-0 event that links created chars into the table is statically
unresolvable — the dispatcher is only ever invoked indirectly. A `--hero-body` click is the
cheap experiment that would answer it, filed as the science arm below.)

Two tolerances that shape the minimal fix, both OBSERVED: `CharBy` returns a
registered-but-empty slot's NULL **cleanly** (the assert is only the count bound), and
`PushAppearance` branches to a hero-record fallback (`0x00538308`) on NULL. So the fix
needs only the **count** to cover id 200 — no char object required. One catch:
`SetShownId` calls `CharBy` **twice** (again at `0x005380CB`), so tolerating the miss
client-side was never an option; the table must grow.

### 27.3 What retail does — OBSERVED census, 38 connections

None of the four grower opcodes is retail's per-character registrar for other players:
their keys match kind-5 create ids essentially never (`0x009A` 0/410, `0x009B` 0/1629; the
`0x009F`/`0x00A0` streams are generic per-agent traffic). The registrar-*shaped* pair on
retail wire is **`0x006E` + `0x0048`**: exactly one of each per kind-5 create — 650/650/650
corpus-wide, zero orphans, never for kind-9 — and neither handler is among the nine ensure
callers, so if they seed the char table it is via the indirect case-0 event
(RECONSTRUCTION; `0x0048 [agent, flag]` is the natural "char ready" candidate). For our
hero, none of that is needed: `0x009A`'s direct grow is sufficient by construction.

### 27.4 The staged arm — `--hero-char`

Sends `0x009A [hero agent id, 100<<24]` (retail's modal value) per hero slot, in the build
window before HERO_ACTIVATE. Predictions, on record before the next click:

| arm | prediction |
|---|---|
| §26.3's command (control — already measured) | `Array.h(587)`, the 2026-08-18 click |
| + `--hero-char` | both `CharBy(200)` calls pass and return NULL; the doll falls back to the hero record; the slot loop hits inventory 2 (exists, empty bag) through the same `ItCliApi:485/:488` helper §26 cleared; **the panel opens and stays** |
| + `--hero-body` instead of `--hero-char` (science, optional) | answers whether the create path's runtime event grows the table: no crash → it does; same `Array:587` → it does not |

### 27.5 The residuals, adversarially checked — every surface closed, one real trap recorded

An adversarial pass attacked "the fix arm completes without asserting" on four surfaces;
all four now close on bytes:

1. **Both `CharBy(200)` calls** pass with the grown table; neither result is ever
   dereferenced when NULL (the second is a pure loop boolean at `0x005380D6`). OBSERVED.
2. **The `PushAppearance` fallback is the one real find**: with a live hero record, the
   branch taken (`0x0053830C`) **unconditionally dereferences
   `0x0080E370(heroRecord[+0])`** — no NULL check, so a miss is a hard access violation,
   not an assert. Defused for our rig, on bytes: the `0x0072` worker writes the **hero id**
   at activation-record `+0` (`0x0081DB47 mov [edx], ebx`, 38833), so the lookup is
   `0x0080E370(1)` — the same heroData record GmView's `:5897` assert already passed and
   dereferenced upstream in the same click. **The trap, for future rigs:** `0x0072` sent
   for a hero id that has no `0x0074` record would fault here raw — but GmView's `:5897`
   gates the commander path before the doll can run, so the click cannot reach it; only a
   rig that opens the doll some other way could.
3. **Event `0x1000018E`** (the commander case's last act) has exactly one subscriber —
   PtHero — which equality-filters the payload id against its tracked hero and touches no
   by-id array. OBSERVED, three sites total in the image.
4. **The doll's slot loop** re-runs `ItCliApi:485/:488` with our key 2 (registered, §26)
   and `GetSlot` bounds `slot < slots->m_count` — our `0x013F` capacity field is 9 and the
   handler sizes and zeroes the array from it (smsg, SOURCED), so slots 0..8 hold and
   empty slots return NULL cleanly.

Whatever the next click hits past all of this belongs here.

## 28. Floor three: `File.cpp:367 fileId` — the hero's appearance pair, and it is a monster composite (2026-08-18)

§27.4's fix arm ran the same afternoon (capture `20260818T142252`). **`Array:587` CLEARED —
both `CharBy` predictions held** — and the doll rendered far enough to open a FILE:
`Assertion: fileId / File.cpp(367)`. The captured stack retrodicts §27.5's traced fallback
*exactly*, hop for hop (rebase −0x930000): PushAppearance's hero-record branch
(`0x00538331`) → the composite factory `0x0082DB40` → `CpsMonster` ctor → the
fileId→filename codec `0x004702B0` asserting on a **zero**.

### 28.1 The pair, both ends read — OBSERVED (38833)

- **Producer:** the `0x0074` worker (`0x81DB70`) stores wire fields `+0x14`/`+0x18` — the
  two u32s between the three leading u8s and the chunk, our builder's `d1`/`d2`, sent as
  zeros since the day the message existed — verbatim at hero-record `+0x14`/`+0x18`
  (stores `0x0081DBE1`/`0x0081DBE7`).
- **Consumer:** PushAppearance pushes the pair into `0x0082DB40(d1, d2, &zeroVec3, 0)`,
  which op-news 0x10C and runs `0x0082F510` — **unconditionally the `CpsMonster.cpp`
  constructor** (vtable hard-set; the CpsPlayer factory is the sibling `0x0082DBA0` and
  nothing on the hero path calls it). Inside: `d1` flows **untransformed** to
  `0x004702B0(d1, &out)`, the File.cpp codec, which asserts `fileId` at :367 on zero —
  no early-out exists, so **`d1 = 0` is never legal** and "no appearance" is expressed
  only by not calling. `d2` selects the MdlBuild variant: non-zero → build **with
  skeleton file** (`MdlBuild:1868`), **zero → legal**, the fileName-only build
  (`MdlBuild:1835`). So: **`d1` = the model file id, `d2` = an optional skeleton file id.**
- All four callers of the factory pass the pair from data, never literals — there is no
  zero-sentinel anywhere in the image.

**A finding beyond this arc:** the own-player branch does not use the pair at all — it
reads the persistent composite `s_controlledPlayer` (`[0x01087784]`, named by
`CpsApi.cpp`'s own assert) and serializes its five equip-slot records into an **outbound
`0x57`** — the client telling the server its own look. The hero/merc path instead expects
a **baked model file**, monster-style, which is consistent with retail rendering a
mercenary from a saved appearance snapshot rather than live composite state.

### 28.2 The staged arms — `--hero-appearance D1[,D2]`, values all measured content rows

| arm | pair | what it tests |
|---|---|---|
| **first click** | `116366` (burrower's self-contained unit file: FA0+FA1+FA5+FA6, `content/npcs.toml`) | the single-variable arm: one complete file, `d2=0` legal — File:367 clears and *something* renders, or the next assert names the file class the ctor wants |
| follow-up | `116703,116228` (hatcher body + shell) | the (model, skeleton) reading of (d1, d2) |
| order control | `116228,116703` | the swap, if the above asserts |

Prediction for the first click: `File.cpp:367` clears; the panel opens with a worm in the
paperdoll, or the next assert names the FFNA gate. Either way the field is named by
experiment: **`0x0074 +0x14` is the hero's appearance model file id.**

### 28.3 IT OPENED. Owner's click, 2026-08-18 — the commander panel is wire-authorable end to end

`--hero-appearance 116366` and the panel **opened and stayed**: title "Hero 1: Lvl 255
Norgu", health bar, the AI-mode buttons, the hero's eight-skill bar (the `0x00DA` ids,
rendered), and the paperdoll drawing the burrower — janky, but drawn, which is what the
arm predicted a worm in a humanoid pane would be. No assert. Owner's screenshot is the
verdict; the appearance-quality judgment stays with the owner per the standing rule.

**That closes the whole ladder this study opened in §24** — four floors, each a field or
message already in the tree that had only ever been sent as zero or never sent at all:

| floor | assert | fix |
|---|---|---|
| `GmView:5898` heroData->agentId | `0x0072` was never sent | `--hero-activate` (§25) |
| `ItCliApi:488` inventory | inventoryTable had no hero key | `--hero-inventory 2 --hero-bags` (§26) |
| `Array:587` char table | nothing grew `+0x7CC` past 200 | `--hero-char`, opcode `0x009A` (§27) |
| `File.cpp:367` fileId | `0x0074 +0x14/+0x18` sent as zeros | `--hero-appearance 116366` (§28) |

Cosmetic residue, deliberately not floors: the **Lvl 255** in the title is the known
no-agent sentinel (heroes §10.1 — the label reads the AGENT's level and agent 200 has no
body and no property-36 entry; unit-setup measured prop 36 as a per-agent store readable
without a create, so `0x009F [36, 200, N]` is the cheap arm, `--hero-body` the heavier
one). The **janky doll** is a burrower posed in a humanoid paperdoll; §28.2's follow-up
pair `116703,116228` (hatcher body + skeleton shell) is the staged humanoid arm, and a
real answer to "what file does retail bake for a mercenary" would need a live capture of
an account that owns one — no tape in the vault carries a single `0x0074`.
