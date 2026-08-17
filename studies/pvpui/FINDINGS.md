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
