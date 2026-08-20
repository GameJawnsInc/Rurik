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

> **CORRECTED 2026-08-18.** The mechanism above stands — `ctx[0x44][0x2ac]` is the
> identity the commander model tests — but the VALUE retail puts there is the player
> **NUMBER**, not the agent id: the Factions capture separates the two id spaces for the
> first time (player 1, agents 27/395/311) and `0x0199` field 1 tracks the number on all
> four channels (heroes §22's CORRECTED block, `vault/captures/live/20260817T183756`).
> "Sends `PLAYER_AGENT_ID` for it" was our server's choice, indistinguishable from the
> number in a solo instance; the send site fills it with `PLAYER_NUMBER` as of 2026-08-18.
> Nothing in §13's conclusions moves — both values were 1 in every rig this section
> reasons about.

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
  **← THAT LAST SENTENCE IS BACKWARDS, corrected 2026-08-19 by reading the three files'
  own chunk tables (§28.13): `d1` is the FILE id — the one carrying the skeleton — and
  `d2` is the MODEL id, the geometry.** Every code fact above stands; only the two role
  names were wrong, and they came from the MdlBuild variant labels rather than from
  measuring what the files contain.
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

### 28.4 Both residue arms ran, agent-piloted — the pair is ORDER-SENSITIVE and prop 36 clears the sentinel (2026-08-19)

Three harness runs, all `RUN VERDICT: PASS`, all on the 38833 exe
(`vault/run/2026-08-13_64fae3b1369b/`), each clicking the party window's hero button at
window fraction `(0.9070, 0.3288)` — measured off a recon run's screenshot
(`20260819T082215/hold003.png`), not guessed. The click is fixed-position UI, so the
piloting is inside the agent-pilotable boundary (2026-08-17 precedent); the appearance
verdicts below are read from screenshots and the owner reviews them.

| run | arm | panel | doll | provenance |
|---|---|---|---|---|
| `20260819T082723` | `--hero-appearance 116703,116228` | opened, stable | **EMPTY** — flat white square, still empty 30s later | `2-click.png`, `hold005.png` |
| `20260819T083034` | `--hero-appearance 116228,116703` (the swap) | opened, stable | **RENDERED** — a humanoid head-and-shoulders bust, the shape a real hero portrait has | `hold005.png` |
| `20260819T083324` | `--hero-appearance 116366 --hero-level 20` | opened, stable | the 116366 composite | `hold005.png` |

**The pair finding — OBSERVED, and it sharpens §28.1.** Both orders of the hatcher pair
are assert-free, so `File.cpp:367` and the codec accept either file in either slot — but
only `d1=116228, d2=116703` builds a drawable: the other order renders an empty doll,
silently. Combined with §28.3 (`d1=116366, d2=0` rendered), d1 is the slot the composite
draws. The parsimonious reading is that the content rows' hatcher labels are swapped —
116228 is the drawable body and 116703 its skeleton, not the other way around — but that
is a claim about `content/npcs.toml`'s row naming, RECONSTRUCTION until the rows'
extraction is re-read. What is OBSERVED and matters for the wire: **the pair is
order-sensitive, the failure mode of the wrong order is an empty doll and not an
assert**, so "it didn't crash" is not a verdict on an appearance pair.

> **That RECONSTRUCTION was REFUTED the same day (§28.13): the content rows are labelled
> correctly and it was this arc's ordering that was wrong.** Left standing above because
> the guess and its refutation are both part of the record. The OBSERVED sentence holds.

**The level finding — OBSERVED, and it bought more than the title.** `--hero-level 20`
(`0x009F [36, 200, 20]`, sent through the hero pipeline before any body) cleared the
sentinel in BOTH stores at once — the panel title reads "Hero 1: Lvl 20 Norgu" and the
party roster row reads "Lvl 20 Norgu" — and the panel's health/energy bars, which
rendered as empty black strips in every previous run of this arc, now RENDER, reading
1 (red) over 0 (blue). Nothing ever sent health or energy for agent 200, so those are
the client's own floor values; the cheap follow-up is `0x009F` health (42, OBSERVED)
and energy (41, UPSTREAM) for the hero agent, which would put real numbers in bars
that demonstrably read per-agent stores a bodiless agent can carry.

### 28.5 THE C2S WALL FELL — three opcodes off the commander UI in one afternoon of piloted clicks (2026-08-19)

Heroes §3.3's "c2s direction NOT FOUND, three times" was a static floor, and the open
panel turned it into a clicking problem. Six more `RUN VERDICT: PASS` runs, same rig
plus `--hero-vitals 480,45` (new) and `--explorable` where noted. Every capture cited is
under `vault/captures/gamesrv/`, every screenshot under `vault/captures/harness/`.

**Vitals (run `20260819T090643`).** `--hero-vitals 480,45` (`0x009F` 42/41, the MAX
setters) put exactly 480/45 in the panel's bars, rendered full. With neither sent the
bars read 1/0 (§28.4), so the panel vitals read the per-agent max stores — a bodiless
agent carries them fine.

**The appearance pair, settled by the dat (desk check, `modelfile.py`).** Chunk walks
of the three files: 116366 = `FA0+FA5+FA6+FA1` (geometry AND skeleton — the
self-contained file that renders alone); 116228 = `FA6+FA1+FA8` (skeleton/animation,
NO geometry); 116703 = `FA0+FA5` (geometry, NO skeleton). That REFUTES §28.4's
swapped-labels speculation — the content rows were right — and corrects §28.1's
reading: **d1 (+0x14) must carry the FA1 skeleton/animation chunk** (2/2 rendering
cases have it in d1, the 1 empty-doll case does not), and **d2 (+0x18) supplies the
geometry** in the two-file form. The humanoid bust the swap drew is 116703's mesh
riding 116228's skeleton.

**Stance: `GAME_CMSG 0x0015`, now named HERO_AI_MODE (capture
`authsrv-20260819T090943-c1.jsonl`).** Each of the three stance buttons emitted exactly
one frame, `[agent=200, mode]`, mode tracking the click order Guard=1 / Avoid=2 /
Fight=0 — the enum `0x0072`'s own format string calls `aiMode`. Two things the static
trace could not see: the send lives on the BUTTON path (not the GmAgentCommander setter
§3.3 traced to a dead end), and the client does NOT move its own stance ring on click.
An echo arm now answers `0x0015` with `0x0072` carrying the requested mode (authsrv
dispatch, always-on, inert off-rig) — the echo fires (`hero stance echo: agent 200 ->
aiMode 1`, run `20260819T093153`) but the ring STILL does not move, so the ring's
display store is NOT satisfied by a re-sent `0x0072`. Where the ring reads from is a
new, open question; stance is server-authoritative either way.

**The crosshair button is TARGET-LOCK, not the flag.** Clicked in the outpost it said
"Norgu cannot have a target while in an outpost"; clicked in the explorable it said
"You must select a foe before you can lock No[rgu's target]". Its c2s (if any) needs a
foe on screen — a staged `--enemy` arm, not run.

**Flags: `0x001A` HERO_FLAG_PLACE and `0x001B` PARTY_FLAG_PLACE (capture
`authsrv-20260819T093801-c1.jsonl`).** The real flag controls are the widget strip
under the compass (all-party flag + one numbered flag per hero; hero 1's lit, 2/3
greyed because those heroes don't exist). Arm-then-ground, one arm each: the hero-1
flag's ground click emitted `[agent=200, coords, plane]` (0x001A) and the all-flag's
emitted `[coords, plane]` (0x001B) — no agent field is what distinguishes the pair —
and BOTH ground clicks were consumed (zero MOVE_TO_COORD in the run). The client drew
no flag in the world or on the compass: like the stance ring, flag rendering waits for
a server echo nobody has found or built yet. Both names are in `schema/overrides.json`
at medium confidence — n=1 each, cancel/recall variants untested.

**The greyed Norgu row — owner's reading, and it fits everything.** In the explorable
party list Norgu's name renders greyed/dark: that is the client's out-of-COMPASS-RANGE
rendering, and agent 200 has no body and no position, so he scores as permanently out
of range. Prediction it stages for free: give the hero a body (`--hero-body`) or
whatever store feeds compass range, and the row lights up.

Scoreboard for heroes §3.3 after today: stance FOUND (3/3, named, echo-armed), hero
flag FOUND (n=1, named), party flag FOUND (n=1, named), target-lock located and gated
(needs a foe), hiring still NOT FOUND. What the client does with all three is
send-and-wait — every confirmed display (stance ring, flag marker) waits on a s2c echo
that is now the arc's next mechanism to find.

### 28.6 THE LOOP CLOSED — every echo found by desk work, then confirmed by the client drawing it (2026-08-19, same day)

Three parallel static tracers on the 38833 image found every echo §28.5 left open, and
one wire run confirmed all of them (`RUN VERDICT: PASS`, run `20260819T101254`):

**The stance ring, explained to the byte and then moved.** `0x0072`'s aiMode lands at
activation-record+0xC but raises frame event `0x10000038` — an event GmAgentCommander
has NO case for, which is the measured §28.5 inert-echo, now explained. The ring itself
is a UI-local member (`ctrl+8`, painted by `0x004FC9D0`, highlight images
0xAC7C/D/E) whose only writer is the panel's child-message 0x57. The dedicated setter
the client listens for is **s2c `0x0062` — now named `HERO_AI_MODE_SET`
`[agent_id, dword aiMode]`** (handler `0x0091E060` → `ChCliHero::SetAiMode`
`0x0081D990`): writes the same rec+0xC but raises `0x1000003A`, the one event the panel
subscribes to. The authsrv stance echo now answers `0x0015` with `0x0062`, and the wire
verdict was better than predicted: **the ring moved to Guard AND Norgu spoke his
Guard acknowledgment line in chat** — the stance loop renders and narrates.

**The flags, traced store-to-model and then planted.** **s2c `0x0066` HERO_FLAG_SET
`[agent_id, vec2, word plane]`** (handler `0x0091E0E0`): writes the hero ACTIVATION
record's +0x10..0x1C — the same `ctx[+0x2C]+0x584` record `0x0072` creates, so the
store is gated on activation existing, and ArenaNet's own failure trace names the
action `CommandMoveToPoint` — posts frame event `0x100000A0`, and Compass.cpp
(`0x008BB520` → `CompassCanvas_SetFlag 0x008BF730`) creates BOTH the compass marker and
the world flag model. CompassCanvas is the sole image-wide caller of AvFlag
create/destroy: the world flag is downstream of the compass widget, one event feeds
both displays. **s2c `0x0067` PARTY_FLAG_SET `[vec2, word plane]`** is the twin (store
`charCtx+0x9C..0xA8`, event `0x100000A1`, compass slot 0). Per-slot flag models ride an
8-entry file-id table at `0x00A94358` (party 11092856; heroes 1–3 11092864/72/80). The
clear/remove form is coords `(+INF, +INF)` with plane 0. Wire verdict: **both flags
planted** — the hero triangle and the party pennant, visibly different models, plus
both compass markers and the cancel widget lighting up. The authsrv echo arms answer
`0x001A`→`0x0066` and `0x001B`→`0x0067`.

**Target-lock, static only (medium).** The crosshair sends **c2s `0x0016`
HERO_LOCK_TARGET `[heroAgent, targetAgent]`** / **`0x0017` HERO_UNLOCK_TARGET
`[heroAgent]`** from GmAgentCommander's msg-0x24 handler `0x004FBD20` (lock reads the
selected target via AvApi `0x007E1090`; re-lock same target is local-only). The
foe/outpost gate sits upstream of msg 0x24 and its error strings are string-table ids,
not .text literals. Live confirm needs an `--enemy` run with a foe selected — staged.

**Hiring, still NOT FOUND, with a much stronger floor:** all 174 callers of the
channel-send `0x007DCF00` were enumerated and their opcode immediates recovered — the
commander/flag UI family sends ONLY 0x15/0x16/0x17/0x1A/0x1B, and the party-add
opcodes (0x01BF/0x01C2) do not use this send path at all (they ride the party-build
batcher, a different helper whose callers are the place to look next).

All five opcodes are named in `schema/overrides.json` — the three s2c at high
confidence (static chain + the client drawing it), the two lock c2s at medium (static
only). The commander UI is now round-trip complete: stance, hero flag, and party flag
each close click → c2s → server echo → render, on a server that knows all six messages
by name.

### 28.7 The lock, captured and closed — and the toggle-off is `0x16 [hero, 0]`, not `0x17` (2026-08-19, still the same day)

Three runs, an instrument correction between each, every deviation informative:

1. **No foe in the world** (runs `104437` and its outpost sibling): the crosshair click
   landed and the client refused locally with the exact string-table toast the static
   trace predicted — "You must select a foe before you can lock Norgu's target" — and
   sent nothing. Also a harness lesson re-learned: `session.py` defaults the world to
   `--no-enemy`; the opt-in is the session-level `--enemy`, not a game-arg.
2. **Foe present, no echo** (run `105048`): `C` targeted the practice target and the
   crosshair click sent **`0x0016 [200, 10]` — captured**, upgrading the name to wire
   confidence. The second click sent `0x0016 [200, 10]` AGAIN: the client's lock state
   is server-set, same pattern as the ring and the flags.
3. **Echo armed** (run `105652`): the lock echo is **s2c `0x0063` HERO_LOCK_TARGET_SET
   `[heroAgent, targetAgent]`** — found by desk work in minutes because §28.6's flag
   tracer had already mapped the record: handler `0x0091E080` → wrapper `0x008107E0`
   (hero container +0x584 AND pet container +0x6AC) → setter `0x0081D9C0`, writing
   activation-record **+0x20** and raising `0x1000003F`. Wire verdict: click 1 locked —
   crosshair lit gold, tooltip "**Hatcher [Collector] is locked as Norgu's target**"
   (the client resolves the target's name) — and click 2 sent **`0x0016 [200, 0]`**,
   the `rec+0x20 != 0` clear branch the static trace predicted, which our echo
   `[200, 0]` answered and the crosshair unlit.

So the lock protocol on this path is `0x16 [hero, target]` to lock and `0x16 [hero, 0]`
to clear, echoed by `0x0063` both ways; **`0x0017` never fired** — its guard (getter
`0x0080CEE0`) reads a state this rig does not set, with the pet container +0x6AC the
standing suspect. The activation record's map after today: +0 heroId, +4 agentId
(0x0072), +8 inventoryId (0x0072), +0xC aiMode (0x0062 / 0x0072), +0x10..0x1C flag
{x,y,plane,0} (0x0066), +0x20 lockedTarget (0x0063) — six wire-reachable fields, each
with its opcode and its event, every one confirmed by the client drawing something.

### 28.8 The body run — the row goes retail-format and the agent store outranks the record (2026-08-19)

Run `20260819T110510`, the full rig plus `--hero-body`. The scripted panel click
missed (`NO WINDOW`) and the commander panel appeared open in the hold shots anyway —
recorded at first as UNVERIFIED between two readings, both now REFUTED by controls
(§28.9): the frame almost certainly shows ANOTHER SESSION'S client. The substantive
verdicts below all reproduced on clean single-client runs the same day
(`20260819T123759`), so they stand; only the auto-open belonged to the artifact:

- **The party row upgraded to retail's format**: "Lvl 20 Norgu" (bodiless) became
  "**Mo20 Norgu**" — the profession segment reads the AGENT (heroes §23's roster-reads-
  the-agent claim, reconfirmed from the other side), and the level moved into the same
  profession+level rendering a real hero row has. Nothing greyed with the body in
  compass range; the greyed-row-means-out-of-range reading still wants its positive
  control (a body placed far away).
- **The panel's vitals re-sourced**: health reads 100 (the body's `create_agent_world`
  value), no longer the bodiless prop-42 store's 480 — when both exist, the AGENT's
  store outranks the activation-era property store. Energy stayed 45 (no agent-side
  energy was sent, so the prop-41 store still shows through — the two bars source
  independently).
- **The hero body stands in the world** (spawn offset, third in line behind the
  practice target), so `--hero-body` composes with the whole echo rig with no assert —
  activation, char-table, appearance, level, vitals, stance, flags, and lock all
  coexisted with a real agent in one session.

### 28.9 The panel does NOT auto-open — the 110510 anomaly was another session's window (2026-08-19)

Four controlled runs, one variable at a time, all `PASS`, zero clicks unless stated:

| run | rig | prior layout state | panel? |
|---|---|---|---|
| `123331` | bodiless | inherited "open" from 110510 | **NO** |
| `123525` | + `--hero-body` | inherited whatever 123331 saved | **NO** |
| `123759` | + `--hero-body`, WITH click | — | opens on click (control that the click path works) |
| `124040` | + `--hero-body`, no click | inherited "open" from 123759's clean `WM_CLOSE` | **NO** |

That kills all three candidate mechanisms: layout persistence (row 1 and row 4 —
row 4 directly followed a clean panel-open save and restored nothing), body-triggered
open (row 2), and persistence gated on a body (row 4 again). **The commander panel
opens only by click on this rig.** What actually happened in 110510: a parallel
session's client was still running (the harness's `--replace` clears stale Python
listeners, not clients), which is also why the scripted click reported `NO WINDOW` —
the hold screenshots captured the OTHER client's window, panel open from that
session's own use. The generalizable lesson, same family as the two-tree and
two-capture defects this repo already paid for: **a harness screenshot is not
attributed to a client by being taken — before believing a UI readout, be sure whose
window it is** (one `Gw.exe` in the process list, or an identifying element in frame).

### 28.10 The greyed row tracks the BODY, not the distance — the owner's reading confirmed, its mechanism one level down (2026-08-19)

The owner's game-knowledge reading of the dim Norgu row, recorded in §28.5: *"norgu's
name being greyed out in the party members menu means he's more than a compass range
away from the player."* Two arms plus a seven-run sweep, and the measurement is a
GLYPH-COLOUR one, not an eyeball — the first pass sampled the whole row, whose red bar
swamped the signal and read as "no greying anywhere", which was wrong:

| rig | hero name text | player name text (same frame) |
|---|---|---|
| bodiless (4 runs: `092640`, `101254`, `105652`, `123331`) | **(182, 148, 148)** | (220, 181, 181) |
| body at default −150u (`123525`, `123759`, `124040`) | (223, 184, 184) | (220, 181, 181) |
| body at −3000u (`124945`, the positive control) | (223, 184, 184) | (220, 181, 181) |

**The greying is real and reproducible** — a bodiless hero's name renders ~17% darker
than the player's in the same frame, four runs, identical to the byte. **A body lights
it**, exactly as the owner's reading predicted. **Distance does not re-grey it**, and
the same frame proves the body was genuinely out of range: the compass shows two green
marks in the near run (player + body) and **one** in the far run — the client dropped
the 3000u body from the compass while keeping its party row lit. So the compass and
the row do not share a predicate.

**The reconciliation, and it makes retail and our rig one rule (RECONSTRUCTION).** The
row's predicate is *does this party member have a live agent in my table*, not *how far
away is it*. On retail a player only ever meets that dim state at range because the
SERVER culls out-of-range agents — `agentroster.py` measured exactly this in the live
corpus, "visibility churn re-creates a body every time it re-enters compass range"
(agent 44, four creates per session at one position). Retail's distance greying is
agent-absence greying with a server-side cull in front of it. Our server has no
culling, so a 3000u body stays in the table and stays lit. The owner identified the
retail behaviour correctly; the client-side mechanism is one level below it, and the
difference is a server feature we have not built rather than a message we have not
sent. Cheap confirmation available whenever wanted: destroy agent 200 mid-session and
watch the row dim without touching a position.

`--hero-body-offset DX[,DY]` (new) places the body; it refuses without `--hero-body`,
because a placement flag on a rig with no body would measure the default and read as a
null result for the offset.

### 28.11 `0x0017` IS NOT THE UNLOCK — a name this arc published, and retracted the same day (2026-08-19)

§28.6 named c2s `0x0017` **HERO_UNLOCK_TARGET** at medium confidence, on the reasoning
that it is the other branch of the crosshair handler that sends `0x0016`. §28.7 already
found it never fires and guessed the pet container as the missing state. Both were
wrong, and the guard is not a lock state at all.

The branch in `0x004FBD20` (38833) is chosen by **`0x0080CEE0`, which reads neither
store this arc knows.** It resolves the agent through AgApi `0x005FC380`, requires
`targetDef == GW_AGENTDEF_CHAR` (the constant is named by its own asserting twin,
`ChCliApi:3873 targetDef == GW_AGENTDEF_CHAR`) and `obj+0x48 == 6`, and returns
**`obj+0x24`** — a per-agent ChCliApi field, no `+0x584` or `+0x6AC` displacement
anywhere in the function. What that field means is settled by its other readers, all
three named from their own asserts: **GmBundle** (`GmBundle:98 ptr`), **GmWeaponBar**
(`GmWeaponBar:373 currSlot < ITEM_PLAYER_EQUIP_SETS`, which on non-zero drops the
carried thing *instead of* switching weapon sets) and **GmCoreAction**
(`GmCoreAction:933 action < WORLD_ACTIONS`, which disables world actions while it is
non-zero). Weapon-swap-drops-your-bundle and no-world-actions-while-carrying are retail
behaviours a player would recognise. So `obj+0x24` is a **carried-bundle** store, and
the crosshair's real structure is:

```
bundle store != 0 ?  -> is this hero MY OWN agent ?  yes -> local drop, c2s 0x002E (empty body)
                                                     no  -> c2s 0x0017 [heroAgent]
bundle store == 0 ?  -> hero record +0x20 != 0 ?      yes -> c2s 0x0016 [hero, 0]   (the clear)
                                                     no  -> c2s 0x0016 [hero, target]
```

Both `0x0016` sends live under the bundle-clear arm, which is exactly what our capture
showed. **The paint routine `0x004FC0C0` reads both stores in the same priority order**
into a four-state image index, so the gold crosshair we lit was state 1 (record +0x20),
not the bundle state — paint and branch agree, and there was never a store
disagreement to find. `0x0017` sits behind a state this arc has never entered and
*cannot* enter: nothing in `0x0062/0x0063/0x0066/0x0067/0x0072` touches `obj+0x24`, and
its writer was searched on four surfaces and is **NOT FOUND** (a `--field 0x48` sweep
of ChCliApi, an image-wide byte scan for `mov dword [reg+0x48], 6`, all 33 callers of
the AgApi resolver, and the 477-handler receive map — floors, not censuses).

**The name is retracted rather than replaced.** `HERO_DROP_BUNDLE` fits the mechanism,
but the mechanism is OBSERVED and the *name* would be inference, so the schema entry is
deleted and `0x0017` goes back to being a held PARTIAL with its story recorded — the
repo's own pattern for an opcode whose behaviour is known and whose name is not earned.
`0x0016`'s entry keeps its high confidence and gains the correction: **the toggle-off is
`0x0016 [hero, 0]`, its own zero form**, not a second opcode.

Method note, because this is the second correction in two days: the name came from
structure ("it's the other branch"), and structure is a hypothesis. The refutation cost
one tracer and would have cost nothing had the name waited for the branch to be read.

### 28.12 Pets share the commander messages — and need one declaration we have never sent (2026-08-19)

The pet-side mirror in both echo wrappers is real and now read end to end. Correction
to §28.6's note first: the two wrappers call **different** setters — `0x008107A0`
(aiMode) calls `0x0081F6D0`, `0x008107E0` (lock) calls `0x0081F710` — not one shared
one.

The container at `charCtx[+0x2C]+0x6AC` is a sorted `rtl` Array of **28-byte records**,
binary-searched on the first dword: **+0 pet agent id (key), +4 owner agent id, +8
name, +0xC/+0x10 unread, +0x14 aiMode, +0x18 lockedTarget**. Its events are
`0x10000049` (add), `0x1000004B` (aiMode), `0x1000004C` (lock) — the pet twins of the
hero's `0x1000003A`/`0x1000003F`.

**So the answer to "do pets share the commander messages" is yes, keyed identically:**
s2c `0x0062` and `0x0063` each write the hero container AND the pet container with the
same `agent_id` field, and `GmPetCommander` shares the hero side's `CHAR_AI_MODE` enum
(`GmPetCommander:161 petAiMode != CHAR_AI_MODES`). **But a pet needs a declaration we
have never sent:** s2c **`0x00B2 PET_ADD`**, `[agent_id pet, agent_id owner,
string16(32) name, u32, u32, u32 aiMode]`, 88 wire bytes. Without a record for that
agent, both mirror writes hit a NULL find and **silently do nothing** — no log, no
assert, no return value (`0x0081F6E4`, `0x0081F724`). That silence is why the pet half
of every run this arc has done was invisible.

Named with it, from the client's own log format strings rather than from asserts —
there is no `ChCliPet.cpp`, the code sits in the `ChCliApi.cpp` layer: **`0x00B3
PET_REMOVE`** `[agent_id]` and **`0x00B4 PET_RENAME`** `[agent_id, string16(32)]`.
`PetAdd`'s string also names its own sixth field: *"PetAdd (agent %d, aiMode %d): Pet
already added"*. All three are in `schema/overrides.json` at medium confidence —
static-only, and this repo has never sent or captured one.

Frontier, recorded rather than chased: the despawn sweep `0x00F8` clears ~~six~~
**SEVEN (corrected §31.3 — a seventh walked inline at `+0x5BC`, missed here)** sibling
containers off the same context with one agent id (`+0xAC`, `+0x508`, `+0x584`
hero, `+0x6AC` pet, `+0x6BC`, `+0x6F0`), and the last two are wholly unread —
`PtMinionRoster.cpp` is in the assert surface and is the obvious candidate for one.
The method that cracked the pet container in one call is the one to repeat: read the
log format string on the not-found path. *(Settled §30.4/§31: the minion guess was
refuted, and both "unread" rows were already read in neighbouring studies.)*


### 28.13 The appearance pair IS the content row's `(file_id, model_id)` — §28.1's role names were backwards (2026-08-19)

One desk check, no client: read the three appearance files' own chunk tables out of the
owner's archive with `toolkit/mapdata/modelfile.py`, where `0xFA0` is geometry and
`0xFA1` the skeleton/animation chunk.

| file | chunks | geometry? | skeleton? |
|---|---|---|---|
| 116366 (burrower) | `0xFA0, 0xFA5, 0xFA6, 0xFA1` | yes | yes |
| 116228 (hatcher `file_id`) | `0xFA6, 0xFA1, 0xFA8` | **no** | yes |
| 116703 (hatcher `model_id`) | `0xFA0, 0xFA5` | yes | **no** |

Line that up with §28.4's three arms and one rule fits all of them: **`d1` must be a file
carrying a `0xFA1` skeleton.** 116366 has one and rendered alone; 116228 has one and
rendered with 116703 supplying the geometry; 116703 has none and rendered an empty doll
even though it is the file with the actual body in it. So `d1` is the skeleton-bearing
FILE and `d2` supplies the MODEL — **the reverse of §28.1's role names**, which were
assigned from the MdlBuild variant labels (`build with skeleton file`) rather than from
looking inside the files. Corrected in place there.

**And the pair is not a new concept at all — it is the pair `content/npcs.toml` already
carries.** The hatcher row's own field names are `file_id = 116228` and
`model_id = 116703`, and the working order is exactly that order. The burrower row is
the control that makes it airtight: it has **no `model_id` on purpose**, with a comment
recording that ArenaNet declares it with `0x0056` and sends **no** `0x0057`
MONSTER_COMPOSITE — 8 of 44 definitions in the capture are `0x0056`-only. A
self-contained file needs no model, which is precisely why `--hero-appearance 116366`
worked with `d2 = 0`. The same rule governs both the NPC path and the hero path.

**Two consequences.** §28.4's guess that the content rows were mislabelled is REFUTED —
the rows were right and this arc's ordering was wrong. And hero appearance authoring
collapses to a rule with no new measurement in it: *to dress a hero as any NPC we
already have a row for, send that row's `file_id` and `model_id` as `d1`/`d2`, and send
`d2 = 0` where the row has no `model_id`.* Cheapest confirmation available: any third
content row with both ids, one click.

## 29. `0x0074` MERCENARY_INFO, read field by field — the record is a HERO POOL entry, and two of our own refutations were surface errors (2026-08-19)

Seventeen agents on build 38833: one mapping the worker's every store, four hunting the
readers of each field group, and a skeptic on every meaning claim carrying the lens the
day's two retractions earned — *does the evidence show code READING this offset and
acting on it, or does it rest on a label, a struct position or an upstream guess?*
Three claims came back downgraded by that pass and are labelled accordingly below.

### 29.1 The container, finally disambiguated — and the two-container trap named

`charCtx[+0x2C]+0x584` is not a record array at all. It is a **ChCliHero aggregate
holding two arrays**: `+0x00` is `Array<activation>`, **stride 0x24**, keyed by AGENT and
written by `0x0072`; `+0x10` — i.e. `+0x594` — is `Array<heroData>`, **stride 0x9C**,
keyed by HERO ID, sorted ascending, binary-searched, and written by `0x0074`. Every
public getter reaches the data array by taking `+0x584` and re-biasing `+0x10`
(`0x0080E370` → `0x0081D4B0` → `0x0081D410`), which is exactly the "caller passes an
already-biased `this`" case `codescan`'s own banner warns about, running in reverse. That
is why the two containers appeared to have overlapping offsets, and why this arc tripped
over it once: **`0x0081DB47`, cited in §28.1 as the hero-id store, belongs to the `0x0072`
activation record, not to this one.** ArenaNet names the thing twice — `ChCliHero:245
heroData` and `PtSearchHero:171 charHeroData`.

**A hazard worth carrying forward (RECONSTRUCTION, read from code): the insert does not
zero a new slot.** It memmoves the tail up by one and writes only the id, so every byte
the worker does not write inherits **stale bytes from whatever record previously sat at
that index** — which on this opcode means `+0x24..+0x43` always, and `+0x74..+0x9B`
whenever `d3 == 0`.

> **Corrected §30.3, same day:** the stale-bytes mechanism is real, but `+0x24..+0x43` is
> not permanently stale — the sibling opcode `0x0073` writes it in full through the same
> worker. What is true, and worse, is that **`0x0073` and `0x0074` are mutually
> destructive**: each zeroes the fields the other carries.

### 29.2 The map, and what reads each field

| rec | wire | meaning | label |
|---|---|---|---|
| `+0x00` | hero_id | the array's sort key | OBSERVED |
| `+0x04` | zeroed | the AGENT id — `0x0072` writes it here, `HeroDeactivate` re-zeroes it. `0x0074` zeroing it means *created, not yet activated* | OBSERVED |
| `+0x08` | b1 | **LEVEL** | OBSERVED |
| `+0x0C` | b2 | **a profession index, 0..10** (primary — see below) | OBSERVED / CONTESTED label |
| `+0x10` | b3 | **secondary profession, 0 = none** | OBSERVED |
| `+0x14` | d1 | appearance `file_id` (§28.13) | OBSERVED |
| `+0x18` | d2 | appearance `model_id` (§28.13) | OBSERVED |
| `+0x1C` | b4 | **nothing reads it** | NOT FOUND |
| `+0x20` | — | **a COUNT for the array below**; the *`0x0074` handler* hardcodes it to 0, but the shared worker writes whatever its caller passes — `0x0073` passes a real one (corrected §30.3) | OBSERVED |
| `+0x24..+0x43` | — | **eight SKILL IDs**, written in full by **`0x0073`** through the same worker; they seed the deck builder's available-skills bitset (corrected §30.3) | OBSERVED |
| `+0x44` bit 0 | b5 | **hero-DISABLED flag** | OBSERVED (b5 as its initial value: RECONSTRUCTION) |
| `+0x48` | d3 | **a packed CHARACTER-APPEARANCE dword** (the `s_appearanceSlot` bitfield, 8 slots), 0 = none; gates the name AND the equipment block (sharpened §30.3) | OBSERVED |
| `+0x4C`, `+0x60` | chunk[0..4], [5..9] | **an EQUIPPED-ITEM snapshot**, five slots | OBSERVED |
| `+0x74..+0x9B` | name | **overrides the hero's default name**, gated by `d3` | OBSERVED |

**`b1` is the level, and the client says so.** The worker's already-added early-out logs
*"HeroDataAdd (hero %d, level %d): Hero already added"* (VA `0x00A958DC`) and its second
vararg is the value stored at `+0x08`. Confirmed independently from the read side: the
label builder takes it as a numeric argument with **-1 as the omit-the-level sentinel**.
The upstream guess was right, and this is the first time it has been *read* rather than
inherited.

**The professions — and heroes §13.2's refutation was a SURFACE error, not a field
error.** `+0x0C` and `+0x10` both flow unmodified into `0x005AB7D0`, a bound-checked
table read whose own guard is the client's assert `profession <
arrsize(s_charProfessionAbbrev)` (`ConstChar.cpp:1290`) — ArenaNet naming the parameter
`profession`, which is as direct as this repo's evidence ever gets. `+0x10`'s zero-ness
picks a one-name vs two-name label template, so it is the SECONDARY and `+0x0C` the
primary; the skeptic accepted "a profession index" as OBSERVED but marked the
PRIMARY/SECONDARY assignment as resting on argument order, so the ordering is recorded
as strong-but-inferred rather than measured. **The reconciliation with §13.2 is the
finding:** the consumers are `PtSearchHero.cpp` and `PtHero.cpp` — the hero-pool and
party-search lists — *not* the roster row. §13.2 varied these bytes and watched the
ROSTER, which reads the AGENT's profession (heroes §14, §23). Both results are true and
neither is about the other. A field is only refuted on the surface you looked at.

**`b5` → `+0x44` bit 0 is the hero-disabled flag.** A one-line accessor returns
`[rec+0x44] & 1`, exported through ChCliApi, and its single caller branches on it to pick
between two different render calls for the same hero label. Bit 0 is the only bit
anything reads.

**`b4` is NOT FOUND** — a measured floor, not a shrug: the store at `0x0081DBED` is the
only instruction in the image that touches that offset. Two senders write it
(`0x0074` and `0x0073`) and nothing reads it.

### 29.3 The ten-dword chunk is an EQUIPPED-ITEM SNAPSHOT — and the naming came from the sibling branch

Two parallel five-element arrays, `A[i]` at `+0x4C` and `B[i]` at `+0x60`, paired
`chunk[i]`↔`chunk[5+i]`. Two independent readers in the `GmMercenaryRoster` band walk
exactly five entries, split `A[i]` at bit 16, and push `{low16, high16, B[i]}` into UI
message `0x63` — one message per non-zero entry.

**What they ARE comes from the alternative branch of the same reader, which is why this
is a measurement rather than a guess.** When `d3 == 0`, `0x0050CD60` does not read the
record at all — it walks the **live item container** through ItCliApi's equip-slot getter
`0x00845530` for slots 0..8, skipping 0 and 1 and gating 7 and 8 on flag bits. So the
record's five entries are the frozen form of the same thing the live path fetches:
`A[i] = (byte[item+5] << 16) | dword[item+0]`, `B[i] = word[item+6]`, for item-container
slots **2..6**. The write side agrees exactly — the packer at `0x0081DE8B..0x0081DEF8`
looks each slot up through the same `0x00845530`.

**And the packer is `0x0081DE20`, which is the function §24.2 named as "the next thing to
read, and it is desk work".** It is read: `HeroEnable`, named by its own log string
*"HeroEnable (hero %d): Hero not in hero pool"* (VA `0x00A95970`). Two long-standing
items closed by one disassembly.

The attribute-block hypothesis (heroes §12) stays refuted, and now has a positive
replacement rather than a hole.

### 29.4 `d3` gates the name — which explains heroes §30.2's inert EncString

`d3` is an id with 0 = none, and it is the predicate on **both sides of the name**: the
worker copies the wire name into `+0x74` **only when `d3 != 0`** (`0x0081DC1F`), and four
readers test the same dword before touching `+0x74`, substituting a default otherwise.
The default is `s_heroClientData[hero_id]+0x0C` through TextApi — the table heroes §2
already located — so **the record's name is an OVERRIDE, not a fallback**: when `d3` is
non-zero the record's own buffer replaces the table lookup and the TextApi selector flips
from 11 to 8.
**That is a direct, testable explanation for heroes 30.2**, where a real EncString sent
on `0x0074` was inert: every run this arc has ever made sent `d3 = 0`, so the string was
never copied into the record and no reader would have looked at it if it had been. The
prediction is sharp: `--hero-info-name` with a NON-ZERO `--hero-flag` should change the
displayed name in the pool and search lists, and `--hero-info-name` alone should keep
doing nothing.

`d3` has a second use that is not about the name: one site passes its full 32-bit value
into a UI call with tag `0x57`, in the same slot where a `d3 == 0` client substitutes the
first dword of a struct built by `0x0082DD30` -- the module adjacent to the `CpsMonster`
factory the appearance pair already runs through. So `d3` plausibly names an
appearance/composite entity, RECONSTRUCTION, and it also has a local non-wire writer.

### 29.5 What this changes for the server

- **`--hero-info-name` has never been able to work.** Sending a name without `d3` copies
  nothing. The two flags are coupled and the code now says so.
- **The record is a HERO POOL entry**, and its readers are the hero-pool/search UI --
  `PtHero`, `PtSearchHero`, `GmMercenaryRoster` -- not the party roster. That is why so
  much of this message measured as inert: the arc was watching the wrong window.
- **Frame event `0x10000039`** carries the record POINTER as payload, so a subscriber
  reads every field; `PtHero` is a confirmed subscriber.
- Fields worth authoring now that each is named: level (`b1`), the two professions
  (`b2`/`b3`), the disabled bit (`b5`), and a five-slot equipment display (the chunk).

Remaining genuinely open in this message: `b4` (nothing reads it), `+0x24..+0x43` (this
opcode never writes it, so another message must), and what `d3`'s value *is* beyond
non-zero.

## 30. The sibling containers, read — a profession table, a skill-bar store, and the minion answer (2026-08-19)

Four tracers, eight meaning claims, **all eight CONFIRMED by their skeptics**. Two of the
six containers hanging off `charCtx[+0x2C]` are no longer unread, and one long-standing
guess is refuted. Two of the claims correct §29, published earlier the same day.

### 30.1 `+0x6BC` is the per-agent PROFESSION table — and this server has been writing it blind

The log-string trick again, in one call: the not-found path of the `+0x0C` setter
(`0x0081FD50`) logs *"OnProfessionSecondaryBits (agent %d, secondaryBits %d): Agent not
found in sort array"* (`0x00A95A70`) — naming the API, the container ("sort array") and
the parameter at once.

A sorted 20-byte-record array keyed on agent id: **`+0x00` agent, `+0x04` primary
profession, `+0x08` secondary, `+0x0C` a profession BITMASK, `+0x10` a boolean**. Both
profession getters return **11** (`CHAR_PROFESSIONS`, ids 0..10) for an absent agent, an
out-of-band "unknown" sentinel, and a predicate answers *does this agent have profession
X, primary or secondary*. The mask at `+0x0C` is proven a mask by its consumer, which
shifts and tests it bit by bit, and by the literal `0x7FF` (eleven bits) the same code
substitutes as an all-professions override.

Two opcodes reach it: **`0x00B7`** `[agent, u8, u8, u8]` inserts/updates the professions,
and **`0x00B6`** `[agent, u32]` writes the bitmask. Events `0x1000004D`/`0x1000004E`.

**This is the container the hero attribute pair already depends on.** `authsrv.py`'s
`HERO_ATTRIBS` comment has said since 2026-08-16 that "`0x00B7` writes the array at
`ctx[0x2c]+0x6BC` — what the ATTRIBUTE code reads", and that an agent missing from it
asserts `ConstChar:1296`. That was true and blind: we knew the write and not the record.
Now the layout is read, `0x00B6` is a second door into the same table we never knew
existed, and the primary/secondary assignment rests on ArenaNet's own assert
`agentPrimaryProf != agentSecondaryProf` (`GmDeckBuilder.cpp:2321`) sitting in the one
function that calls both getters back to back — strong, but ORDERING evidence, so it is
labelled RECONSTRUCTION rather than measured, with the arm that would settle it named.
`+0x10`'s boolean is a fenced NOT FOUND: one reader, reached only for the local player.

### 30.2 `+0x6F0` is the per-agent SKILL BAR — `hotKeyState`, named by containment

The client names it `hotKeyState` in `ChCliSkill.cpp`, and the name is earned by
CONTAINMENT rather than proximity: the assert `hotKeyState` (`ChCliSkill:718`) sits
inside the function reached with `ecx = charCtx[+0x2C]+0x6F0`, with two more containments
backing it. As with the pet container there is no dedicated `.cpp` — the thin wrappers
are `ChCliApi`.

Stride **0xBC**, keyed on agent id, holding **eight 0x14-byte entries** from `+0x04`
closing exactly on `+0xA4` — a count measured from a walk in the client that sets its own
terminator at `+0xA4` and steps by `0x14`, not inferred from arithmetic alone. Inside an
entry, `+0x0C` is a **skill id** and `+0x10` a **skill copy index**, named by the writer's
own guards `ChCliSkill:515 targetSkill != sourceSkill` and `:516 sourceSkillCopy >= 0`.
`+0xA4` is an **8-bit mask, one bit per slot**.

Two more opcodes, and one of them closes an old loose end: **`0x0064`** `[agent, u8, u8]`
sets a single bit (`bts`/`btr` by index, event `0x1000005A` carrying
`{agent, bit, value}`, silently dropped on an unknown agent), and **`0x0065`**
`[agent, u8]` writes the whole mask and diffs it bit by bit, firing one event per changed
bit. **`0x0065` was one of the four "adjacent unnamed SMSGs" §28.6 listed as candidates
for the stance echo** — it was never that; it is the skill-bar mask.

### 30.3 `0x0074`'s leftovers — and two corrections to §29

**§29 got two rows wrong and they are fixed above.** The premise "`0x0074` never writes
`+0x24..+0x43`" was true of the OPCODE and false of the FIELD: the shared worker takes a
**count** in one argument and a **pointer** in another and memcpys `count*4` bytes into
`+0x24`. The `0x0074` handler passes a literal zero — which is why the span looked
unwritten from where §29 stood — and the sibling **`0x0073`** passes a real count and a
real array. So `+0x20` is that count, not a property of the handler that happened to zero
it.

**The eight dwords are SKILL IDS**, used as bit indices to build the deck builder's
available-skills bitset — and the naming comes from the sibling branch again: when the
count is zero, `GmDeckBuilder` does not read the record at all but fetches the
account/character list instead, whose result the client's own assert calls
`unlockedSkills`.

**`d3` is a packed CHARACTER-APPEARANCE dword** — the same 32-bit bitfield
`CharData.cpp` addresses through `s_appearanceSlot` (8 slots, `slot <
arrsize(s_appearanceSlot)`) — not an entity id and not a content-row id. That explains
why one field gates both the name and the equipment: **a record with an appearance is a
character-derived, mercenary-style hero**, so it carries that character's own name and
gear; a record without one falls back to `s_heroClientData`. The bit layout was not
decoded — the type is named, a specific value is not.

**An operational hazard, and it is sharp: `0x0073` and `0x0074` are mutually destructive
on the same record.** They share one worker and each zeroes what the other carries —
`0x0073` forces `d3 = 0`, the name to NULL and both equipment arrays to zero; `0x0074`
forces the skill count to 0 and its pointer to NULL. Neither is a partial update, and
order decides what survives. Our server sends `0x0074`; anything that later adds `0x0073`
must know this.

Second hazard, server-side: the worker's memcpy is `count*4` with **no bound check of its
own**. Eight dwords end at `+0x43`, so a count above 8 walks over the disabled bit, `d3`
and the equipment block. The wire descriptor caps it at 8, so a conformant sender cannot
trip it — ours must respect that cap deliberately rather than by luck.

### 30.4 The minion answer: no minion message declares MEMBERSHIP, and PtMinionRoster is not in this family

*(Heading corrected 2026-08-19 by §33. It read "there is no minion message", which was one
generalisation too far: `0x0093` is a minion message carrying a per-agent COUNT. Everything
below is about MEMBERSHIP -- which agents ARE minions -- and stands unchanged.)*

The standing guess that `PtMinionRoster.cpp` consumes one of the unread containers is
**REFUTED by reading its consumer.** Both of its list accessors resolve the TLS root and
take `[root+0x4C]` — the PARTY CLIENT context (`PyCliParty.cpp`), not `charCtx[+0x2C]` at
all. It iterates a party entry's `Array<agentId>` ("teamAgent") and subscribes to
`0x1000013B` (added) / `0x1000013C` (removed), both emitted by PyCliParty and shared with
`PtRoster.cpp`, whose asserts name three sibling lists — **member, henchman, teamAgent** —
of which this panel handles only the third.

**Minion-ness is not declared by a minion opcode.** The panel decides it itself: the agent
must be in the party's teamAgent array, and its monster-definition flags word must pass a
bit test (`0x100` or `0x4000`, with `0x4000` choosing which of two sub-lists the row lands
in, plus a conditional `0x400` under one frame style). The teamAgent list is filled by
whatever message creates the agent's char display record — the chain is traced link by
link to a forwarder handler, and **the opcode number is a deliberate NOT FOUND**, not a
guess.

One payload detail worth keeping for anyone replaying these events: on the ADD event
`msg+4` is a POINTER to the array slot, while on REMOVE it is the agent id BY VALUE.

### 30.5 Where the family stands

*(Table completed in place 2026-08-19, same day — the two open rows and a seventh the
sweep walks inline that this section did not know about. Full record: §31.)*

| container | what it is | opcodes | status |
|---|---|---|---|
| `+0xAC` | per-agent ATTRIBUTES (`attribState`, ChCliAttrib) | `0x0036`..`0x003B` — six, contiguous | read (§31.1) |
| `+0x508` | per-agent BUFFS (`BuffState`, ChCliBuff) | `0x003F`..`0x0044` — six, contiguous | read (§31.2) |
| `+0x584` / `+0x594` | hero activation / hero pool | `0x0072`, `0x0074`, `0x0073` | read (§29) |
| `+0x5BC` | per-agent MINION COUNT (GmEffect's feed) | `0x0093` | read (§31.3, named §33) |
| `+0x6AC` | pets | `0x00B2`/`B3`/`B4`, mirrored by `0x0062`/`0x0063` | read (§28.12) |
| `+0x6BC` | per-agent professions | `0x00B7`, `0x00B6` | read (§30.1) |
| `+0x6F0` | per-agent skill bar (`hotKeyState`) | `0x0064`, `0x0065` | read (§30.2) |

~~Four of six read, six new opcodes named across today, and the two that remain are the
cheapest next targets~~ — **all seven are now read (§31), and the closing prediction
half-missed**: the method was run and worked, but neither remaining container needed new
reading. Both were already read, in full, in neighbouring studies that this table never
joined.

## 31. The last two containers — both were ALREADY READ, and the join was the missing work (2026-08-19)

One workflow: five tracers over build 38833, three skeptics re-deriving every load-bearing
claim from fresh disassembly. Some forty claims; three refuted, four downgraded, the
structural core confirmed throughout — the refutations are recorded in-line below where
they changed a reading.

**The headline is not the containers, it is the repo.** `+0xAC` is the `attribState`
structure [heroes §12.1/§13.1](../heroes/FINDINGS.md) mapped byte-by-byte on 2026-08-16.
`+0x508` is the `BuffState` structure [skillcast §14](../skillcast/FINDINGS.md) mapped on
build 38797 — a section whose own prose says *"reached through a sub-object at
`charContext + 0x508`"*. §30.5 filed both as "unread" while sitting in the same repository
as both answers. That is the heroes-§13.1 failure — *"the thing was known, in a
neighbouring study, and not connected"* — twice more, and this time the disconnect was
cheap only because the re-derivation was: the tracers reproduced skillcast §14's wire
table field-for-field before anyone noticed §14 existed.

What the session genuinely adds: the joins; the **full ChCliAttrib opcode family** (six,
where heroes knew two); meanings for heroes §13.1's three anonymous sub-arrays; the
BuffState record byte-complete with its event set; a **seventh container** the sweep
walks inline that §28.12 miscounted past; and six earned schema names.

### 31.1 `+0xAC` = `attribState` — and the family is SIX opcodes, not two

**OBSERVED, skeptic-confirmed with a positive control.** The `0x00F8` sweep's `+0xAC`
remover `0x00819850` (stride `0x43C`, finder `0x00819390(agent, &idx)`) asserts in
`ChCliAttrib.cpp`, and every path — creator, resolver, finder, remover, dequeuer —
consumes `charCtx[+0x2C]+0xAC` directly, no re-bias. The §29.1 aggregate trap was tested,
not assumed: the skeptic first re-read the `+0x584` remover `0x0081D8D0`, which VISIBLY
commits the trap (`lea ecx,[ebx+0x10]` into a second array mid-function), proving the
method can see one, then found nothing of the kind in `0x00819850`.

**Six contiguous thunks at `0x0080EA80`–`0x0080EB65`, each `add ecx,0xAC` and nothing
else, map one-to-one onto opcodes `0x0036`–`0x003B`** (each thunk has exactly one caller
in the `0x0091D8xx`–`0x0091D97x` handler band; matched against table `0x00bc8f68`; the
block ends cleanly at `0x0080EB70`, which biases `+0x80C` — a different module):

| opcode | worker | what it does | event |
|---|---|---|---|
| `0x0036` | `0x008198D0` | **dequeue + UNAPPLY** the front pending modifier, asserting `ChCliAttrib:295` `mod->sequence == sequence`; reverts via `0x0081A460` (subtracts from `attrib[i]+8/+0xC` and `attribPointsAvail`, floors at 0); appends the sequence to record`+0x410` | — |
| `0x0037` | `0x008199C0` | the CREATOR (`:313` `!attribState`) — known, heroes §13.1 | — |
| `0x0038` | `0x00819A30` | sets `attribPointsAvail`, then REPLAYS the queued deltas (`:327`) | `0x1000002E` |
| `0x0039` | `0x00819AF0` | writes one wire dword to record`+0x438` (`:352`) | `0x1000002F` |
| `0x003A` | `0x00819C00` | BULK FILL (`:368`): drains the `+0x400` queue, binary-inserts into `+0x424`, mints fresh modifiers via `0x00819270`, calls `0x00819EF0` — known, heroes §13.1 | `0x10000030` per element |
| `0x003B` | `0x00819B50` | SINGLE-attribute set into `+0x424` (`:409`), calls `0x00819EF0` | `0x10000030` |

**This gives heroes §13.1's three anonymous Array headers their meanings**: `+0x400` is a
**pending-modifier queue** (16-byte stride, sequence-carrying), `+0x410` collects
**processed sequences**, `+0x424` is **the attribute store** the setters binary-insert
into. The sequence/queue/revert shape reads like the server-reject half of a client-side
attribute-spend prediction (RECONSTRUCTION — the c2s side has not been read; whether a
c2s spend message carries a matching sequence is the cheapest test). `+0x438`'s meaning
stays NOT FOUND — `0x0039` exists to write it and nothing read names it.

> **BOTH SETTLED THE SAME DAY, §32 — the cheapest test was the right one.** The
> RECONSTRUCTION is **CONFIRMED**: c2s `0x000E`/`0x000F` carry exactly
> `[agent, sequence, attribute]`, the client predicts locally before sending, and
> `0x0036` is the ACK that retires the prediction. Two refinements to this paragraph:
> `+0x410` is a **LIFO stack of retired sequences the allocator pops from**, not a
> write-only log, and `+0x420` is its fresh counter. **`+0x438` is the attribute-point
> TOTAL** (§32.5) — 200 in all 8 live sightings of `0x0037`, and corroborated by
> `studies/unitsetup`, which named `0x0039` from a level-up burst by a different route.

Two more wire facts. `0x00B7` AGENT_PROFESSIONS reaches attribState exactly as heroes §14
said from the other side: its handler's worker `0x00813980` writes the `+0x6BC` profession
store, then biases `+0xAC` and calls the `:435` checker — one opcode, both stores, in that
order. And the non-wire setter family behind `ChCliAttrib:42/:43/:102` (`0x00818A90` →
Apply `0x00818780`) is reached through a four-instruction shim at `0x008AB070` with
**zero direct callers** — vtable-reached from somewhere unread, so "not wired to any
opcode" is DOWNGRADED to "not directly wired; indirect caller unknown" (the skeptic's
correction — the tracer's chain was right, the conclusion overreached).
*(**Read the same day, §32.6:** `0x008AB070`'s address occurs exactly once in the image,
in a six-entry function-pointer table immediately after the string
`P:\Code\Gw\Ui\Game\Attributes\AttribBtns.cpp` — it is the attribute panel's **minus
button**, and `0x008AB080` the plus. The original "not wired to any opcode" was right
after all, now with a closed ancestor set and a positive control behind it.)*

**Names: held.** No log format string names these APIs (this module asserts, it does not
log), so there is no client-own name to take, and the mechanisms alone would make the
names inference — the `0x0017` lesson. `0x0037`/`0x003A` keep their working names in
`authsrv.py`; the other four are recorded here by mechanism and wait for either the c2s
read or a probe.

### 31.2 `+0x508` = `BuffState` — skillcast §14, joined, re-derived on 38833, and finished

**OBSERVED, and independently re-derived before the collision was noticed.** The tracers
walked remover → log strings → thunks → handlers → table and reproduced
[skillcast §14](../skillcast/FINDINGS.md)'s entire result on the second build: opcodes
**`0x003F`–`0x0044`**, six contiguous, 1:1:1 chains with zero fan-in (every thunk and
every API body has exactly ONE direct caller), APIs named by the client's own log format
strings — `BuffSourceAdd`, `BuffSourceRemove`, `BuffTargetAdd` (two overloads, one pooled
string), `BuffTargetExtendTimed`, `BuffTargetRemove`. 38833 VAs: bodies
`0x0081CC80`/`0x0081CDF0`/`0x0081CEC0`(sourced)/`0x0081CF70`(timed)/`0x0081D020`/`0x0081D100`;
thunks `0x0080EEC0`/`EEF0`/`EF10`/`EF40`/`EF70`/`EFA0` — **byte-identical VAs to 38797**;
handlers `0x0091DA00`..`DAE0`, the whole block shifted +0x60 from 38797, bodies ~+0x50.
Wire shapes match `schema/messages.json`'s imported descriptors and skillcast §14.3
field-for-field.

**The record, now byte-complete** (skillcast §14.2 had the two lists; the header
internals are new):

```
+0x00  agent id (outer sort key -- the array is kept sorted: the insert
       reuses the finder 0x0064AAE0's out-param index)
+0x04  SOURCE array {ptr, capacity, count, growIncrement}, elements 0x10:
         {+0x00 skill, +0x04 CONTESTED, +0x08 buffId, +0x0C targetAgent*}
+0x14  TARGET array {ptr, capacity, count, growIncrement}, elements 0x18:
         {+0x00 skill, +0x04 CONTESTED, +0x08 buffId, +0x0C sourceAgent,
          +0x10 duration float, +0x14 timestamp from 0x0046B4E0}
```

`sourceAgent` at target-entry `+0x0C` is named by the client's own assert
(`ChCliBuff:235` `!buffTarget->sourceAgent`); `targetAgent` at source-entry `+0x0C` is
RECONSTRUCTION by symmetry — nothing reads it back in any function read. The embedded
arrays are sorted by **buffId**: the dup-check `0x0081C7C0` is a binary search on entry
`+0x08`. The two `+0x04` dwords were skillcast §14.4's CONTESTED field
(Headquarter `effect_type` vs GWCA `attribute_level`) — **settled the same day by the
`buff_type_field` probe: it is the ATTRIBUTE RANK the effect's tooltip renders at,
GWCA confirmed, Headquarter refuted twice over (skillcast §14.7)** — with one correction
from the wire skeptic: on `0x3F`/`0x41` that field rides **wire field 4**
(`struct+0x10`); field 3 is the skill.

**The frame-bus event set, new** (skillcast §14 had only `0x10000055`):

| opcode | event | payload |
|---|---|---|
| `0x3F` SourceAdd | `0x10000062` | `{agent, entry*}` |
| `0x40` SourceRemove | `0x10000063` | `{agent, buffId}` |
| `0x41`/`0x42` TargetAdd (both) | `0x10000055` | `{agent, entry*}` |
| `0x43` ExtendTimed | `0x10000056` | `{buffId, wire f2, new duration}` |
| `0x44` TargetRemove | `0x10000057` | buffId by value |

The two TargetAdd overloads hold skillcast §14's structural split exactly, from the
bytes: the sourced form (`0x41`) hardcodes duration `0.0f` (`fldz`) and timestamp 0 and
never calls the clock; the timed form (`0x42`) hardcodes `sourceAgent = 0` and stamps
`+0x14` from `0x0046B4E0`. `0x43`'s wire field 2 is stored nowhere — it is forwarded ONLY
into the event payload, a field that exists for the UI and never touches the record.

**Two previously-unread enumerator getters close the loop to the UI**: `0x0081C6A0`
(walks the source array, stride 16) and `0x0081C6E0` (target, stride 24), thunks
`0x0080DA60`/`0x0080DA80`, called from four sites in the `0x0052xxxx` GmEffect band and
from nowhere in the handler band — an independent corroboration of both strides and both
header offsets from code none of the prior passes had read.

Mechanics worth keeping: the remover `0x0081CBC0`'s gap-closer `0x0081C230` is a
**per-record deep-copy assignment** (one 0x24 record per iteration), not a memmove, and
the tail-slot free is ownership-correct — though the tracer's mechanism for WHY was
refuted (`0x007207B0` skips its free entirely when capacities already match; the
no-double-free conclusion survives on that different basis, RECONSTRUCTION). `0x007207B0`
itself is the 16-byte-element instantiation (`shl eax,4` hardcoded), not a generic — the
24-byte target array reaches `0x00478970` instead.

Completeness, measured: **seven** opcodes touch this container (the six plus the `0x00F8`
sweep), and every `charCtx+0x508`-forming instruction in the image is accounted for
(eight `add`-form sites, four `lea`-form). Live corpus (prior counts, not re-measured):
`0x41` ×4, the other five ×0 — so `0x41`'s field map has retail witnesses and the rest
are static-plus-two-builds.

**Named in `schema/overrides.json`**: `BUFF_SOURCE_ADD` (0x3F), `BUFF_SOURCE_REMOVE`
(0x40), `BUFF_TARGET_ADD` (0x41), `BUFF_TARGET_ADD_TIMED` (0x42),
`BUFF_TARGET_EXTEND_TIMED` (0x43), `BUFF_TARGET_REMOVE` (0x44). The four whose names are
the client's own strings verbatim file at high (two independent derivations, two builds,
skeptic-verified); `0x41`/`0x42` file at medium because the client pools one name over
both overloads and the `_TIMED` split, though measured, is our annotation. ldufr's
`EFFECT_UPKEEP_*`/`EFFECT_*` names stay recorded as UPSTREAM-directionally-wrong per
skillcast §14.1.

### 31.3 The sweep clears SEVEN, not six — `+0x5BC` is GmEffect's per-agent value feed

§28.12 said "six sibling containers" and the sweep walks a seventh, inline, between the
remover calls: `charCtx+0x5BC` is a standard array header (`{ptr +0x5BC, capacity +0x5C0,
count +0x5C4, allocCtx +0x5C8}` — the skeptic's addition; the sweep's bare
`+0x5BC`/`+0x5C4` pair is that header, not ad-hoc fields) of **8-byte `{agentId, value}`
entries**. The sweep removes the FIRST match by swap-with-last and silently no-ops on a
miss (`Array:951` guards the hit path only — all OBSERVED, re-derived instruction by
instruction).

Its writer is **opcode `0x0093`** (`[agent_id, dword]`, 10 bytes; single chain
`0x0091EB5C` → `0x00812060`), and the writer's real semantics are the skeptic's find, not
the tracer's: the scan **updates EVERY matching entry and then falls through to an
UNCONDITIONAL append** — there is no else. Repeated `0x0093` sends for one agent append
duplicates; the getter and the sweep each act on the first match only. So the structure is
an append-style list with first-match-wins reads, not a keyed table — and that is an
operational hazard for any server that re-sends state on reconnect. The writer posts frame
event `0x10000046`.

The consumer side: getter `0x0080E660` (`Find(agentId) -> value-or-0`), three callers in
GmEffect.cpp — and one of them (`0x005246E0`) carries the identification alone: it guards
on `GmEffect:3039` `m_agentId` and pushes that exact field as the getter's key. "Per-agent,
keyed by the field ArenaNet calls `m_agentId`, consumed by GmEffect" is therefore
OBSERVED; **"upkeep/maintained-effect value" is band-level RECONSTRUCTION** — the
`CTL_EFFECT_UPKEEP` assert the tracer cited sits ~0x650 bytes and several functions away
from the caller it was attributed to. **REFUTED and replaced 2026-08-19, §33: the value is a
MINION COUNT**, named by the client's own display template (`'You are currently controlling
%num1% minion[s].'`) with the value as `%num1%`. Being wary of the band-level guess was
right — the guess was wrong. *(Sharpened by the `buff_side` probe the same day,
skillcast §14.8: the upkeep monitor's icon draws from the SOURCE list alone with no
`0x0093` sent, so whatever this table feeds GmEffect, it does not gate that icon.)*
That mis-attribution is the `asserts.py --at`
function-boundary overrun, which this session hit **twice** (it also over-scans past
BuffSourceAdd/Remove's real ends) — the tool's own floor caveat, now with two more
sightings. What the value dword IS stays NOT FOUND; `0x0093`'s name is held with it.

### 31.4 What the skeptics changed, and the method note

Three refutations that mattered: the wire tracer's roll-up misplace of the contested
field (§31.2); the `+0x5BC` writer's "upsert" (§31.3 — it is update-all-then-append);
and a capacity-grow formula clean-up (`0x004739C0` returns `growIncrement +
currentCapacity` on one path and DOUBLES the stored growIncrement through the caller's
pointer as a side effect — recorded here because anyone modelling these arrays will hit
it). Downgrades: the `0x008AB070` shim (§31.1), `0x007207B0`'s genericity, the
double-free reasoning, and the ChCliBuff completeness framing (six opcodes → seven
touchers plus two enumerator APIs).

Method: the "routine method" held — remover → module attribution → log string → sibling
branch — but the step that actually closed both rows was `asserts.py --at` on the
remover, which named the MODULE, which named the study that had already done the work.
**Check the studies index for the module name before tracing anything.** The join is
cheaper than the re-derivation, and this repo now has three data points saying the join
is the step that gets skipped.

## 32. The c2s side of the attribute family — a CLIENT-PREDICTION protocol, and the sequence is its handle (2026-08-19)

§31.1 left `0x0036` read but unexplained: it dequeues a pending modifier and asserts
`mod->sequence == sequence`, so *something* must mint that sequence, and the section's own
next action was "read the c2s side for a sequence-carrying spend first." It does, and the
answer is bigger than the sequence: **the attribute panel is a client-side prediction
system with server reconciliation**, and this is the first such protocol identified
anywhere in this repo.

Five tracer reads plus a full skeptic pass on build 38833, then the whole thing found in a
live retail capture. Four of the eight static claims came back corrected — all recorded
below where they land, because two of them were mine.

### 32.1 The loop

```
player clicks + or - on the attribute panel
  | client, in this order (the order is measured, and it is not the obvious one)
  |   1. append a 16-byte modifier slot to the pending queue at attribState+0x400
  |   2. THEN allocate its sequence   (§32.2 -- the slot comes first)
  |   3. write the modifier {sequence, attribute, rank delta, points delta}
  |   4. APPLY it locally            0x00818780
  |   5. recompute the derived costs 0x00818E40   (§32.4)
  |   6. post frame 0x10000030 {agent, ENTRY POINTER}
  |   7. send
  c2s -> 0x000F ATTRIBUTE_INCREASE  [agent, sequence, attribute]   0x00818CE0
         0x000E ATTRIBUTE_DECREASE  [agent, sequence, attribute]   0x00818A90
  s2c <- 0x0036  [agent, sequence]                   retire prediction #sequence
         0x0038  [agent, pointsAvailable]            authoritative
         0x003B  [agent, attribute, base, effective] authoritative
```

**The three-message reply is an invariant, not a tendency: 14 of 14** in capture
`20260818T132739`, every one at the same timestamp on the same connection. The other
grouping in that corpus is `(0x0037, 0x003A)` — create-then-bulk-fill — **8 of 8**. Those
two shapes are the entire s2c attribute vocabulary as retail uses it.

`0x0036` is the ACK. Its worker **reverts first, then erases** (a correction to the order
§31.1 implied), and pushes the retired sequence back onto the stack it came from — the
client discards its guess precisely because the authoritative `0x0038`/`0x003B` are
arriving in the same frame.

### 32.2 The sequence is a LIFO stack index, which is why the corpus only ever shows 0

**CORRECTED from §31.1, twice.** `+0x410` is not merely "processed sequences" and not a
free *list*: it is a **LIFO stack** (`dec count; index` to pop, `store; inc count` to
push), and `+0x420` is a fresh counter the constructor initialises to **0**. So a player
spending one point at a time pops nothing, takes fresh sequence 0, and gets it handed
straight back by the ACK — forever.

The corpus agrees and explains itself: **all 14 spends carry sequence 0**, and the timing
says why rather than leaving it a coincidence — acks land **25-48 ms** after each send
while consecutive sends are **128-167 ms** apart, so the queue is never more than one
deep. **Refutable prediction on record:** click faster than the round trip and sequence 1
must appear.

### 32.3 The arithmetic — nine transitions, both directions, zero free parameters

The modifier's points delta is `+[record+i*20+0x10]` on the decrease path and
`-[record+i*20+0x14]` on the increase path, and §32.4 shows both are recomputed from
`s_attribPoints`. So the wire is fully predicted by a table read out of the same binary:

| direction | series (capture `20260818T132739`) | rule |
|---|---|---|
| **increase** `0x0F` | points 74 -> 65 -> 54 -> 41 -> 25 -> 5 while rank climbs 7 -> 12 | spend = cost of the rank REACHED |
| **decrease** `0x0E` | points 5 -> 25 -> 41 while rank drops 12 -> 10 | refund = cost of the rank LEFT |

`s_attribPoints` = `[1,2,3,4,5,6,7,9,11,13,16,20,-1]` (`attribpoints.py`, sum 97 to rank
12 — the published figure, corroborated against GWW in
[heroes §12.4](../heroes/FINDINGS.md)). Nine transitions, every one exact. This is the
check the house style asks for: it has no fitted parameter and the artifact could have
refuted it at any of the nine.

`0x003B`'s two values are `base` and `base + item bonus`: attribute 20 ran (10,11),
(11,12), (12,13) across the series while 17 and 21 stayed (8,8) and (10,10). Cross-checked
against `0x003A`'s column-major array, whose three parallel runs are **ids, base values,
effective values** — `[17,20,21, 8,12,10, 8,13,10]` — which is what `authsrv.py`'s
"measured column-major builder" has been emitting blind.

### 32.4 `0x00818E40`, the piece nobody had read — costs are DERIVED, and it enforces the primary rule

Both setters call it right after applying, and it is the reason `+0x10`/`+0x14` are always
right: it **recomputes them from the new rank** via two thin readers of `s_attribPoints`
one dword apart (`s_attribPoints[rank-1]` = the refund for the rank you hold,
`s_attribPoints[rank]` = the price of the next). Then it prices the attribute **-1 —
refuse — in three cases**: no profession, a profession this character does not have, or
*an attribute that is some profession's PRIMARY when that profession is not this
character's primary*. That last is the game's own "you cannot raise Strength as a
secondary Warrior" rule, sitting in the client as one flag test.

The flag comes from `s_attrib` (`ConstAttrib.cpp`, 51 x 20 B at `0x00A35740`,
`{profession, selfIndex, nameStringId, descStringId, isPrimary}`) — and the check with no
free parameter is that **isPrimary is set on exactly ten rows, one per profession 1..10**:
attributes 0, 6, 12, 16, 17, 23, 35, 36, 40, 44 — Fast Casting, Soul Reaping, Energy
Storage, Divine Favor, Strength, Expertise, Critical Strikes, Spawning Power, Leadership,
Mysticism, in the published attribute-id order. [heroes §14.2](../heroes/FINDINGS.md)
found the same ten rows from the other end; this is that reading confirmed by its
consumer.

**`s_attribPoints[12] = -1` is the rank cap**, so at rank 12 the increase path is refused
by the very same test that refuses an unowned attribute. One sentinel, two rules.

### 32.5 `+0x438` is the attribute-point TOTAL — §31.1's last NOT FOUND, closed by a cross-arc join

Two lines settle it: `0x0037`'s creator writes its 3rd wire field to `+0x434`
(`attribPointsAvail`) and its **4th to `+0x438`**, and `0x0039`'s worker writes its single
wire dword to that same `+0x438`. In the live corpus `0x0037`'s 4th field is **200 in all
8 sightings** — the wiki's level-20 attribute-point maximum, the number
[heroes §12.4](../heroes/FINDINGS.md) recorded as what `attribPointsAvail` counts down
from.

And [studies/unitsetup](../unitsetup/FINDINGS.md) named `0x0039` **total attribute points**
one day earlier, from a level-up burst checked against the wiki's per-level table
(`0x0039 [agent, 10]` at a level-up to 3) — a completely different route, different
capture, different arc. Two witnesses that share no method name the same field. **This is
the third time in two days that a §31 question was answered by a study that already had
it**, which is now less a coincidence than a finding about how this repo loses work.

### 32.6 Reached only from the UI, proven with a positive control

None of the three senders is reachable from the receive-handler band. The skeptic did not
take `codescan --xrefs` for this: an independent scanner recovered 26,282 function starts
from int3 runs, attributed every `E8`/`E9` rel32 to its enclosing function, swept all five
sections at every alignment for each target's literal bytes, and reverse-BFSed the call
graph. All three ancestor sets are **closed and tiny**, terminating in two UI modules:

| sender | ancestors | terminal module |
|---|---|---|
| `0x00818A90` decrease | `0x0080D8D0` -> `0x008AB070` | `Ui\Game\Attributes\AttribBtns.cpp` |
| `0x00818CE0` increase | `0x0080D990` -> `0x008AB080` | same, sibling slot |
| `0x00818DF0` template | `0x0080D9B0` -> `0x0058ACC0` | `Ui\Game\Templates\TemplatesHelpers.cpp` |

**Two corrections to §31.1 here.** The increase thunk is `0x0080D990`, **not** the
`0x0080D970` this arc has been carrying (that is a different one-argument function). And
§31.1's `0x008AB070` "vtable-reached from somewhere unread" is now read: its address
appears **once** in the image, in a **six-entry function-pointer table immediately
following the string `P:\Code\Gw\Ui\Game\Attributes\AttribBtns.cpp`** — the plus/minus
button handlers. Not a mystery, a button.

The positive control matters and was run: the same scanner against `0x008198D0` — a
function independently proven network-reached — finds its caller and walks up to the
`0x0036` table entry. A negative from a tool that cannot find a known positive is worth
nothing.

### 32.7 The third sender: `0x0010` is a template apply, and it is NOT predicted

`0x00818DF0` (args: agent, count, attribute-id array, rank array) asserts the record
exists, **discards it**, and forwards everything to the `0x0010` framer. It appends no
modifier, calls neither the applier nor `0x00818E40`, and posts no frame — so a template
apply is **send-only, with no local prediction at all**, unlike every single-point spend.
Its caller passes a build template's two 12-dword arrays (ids, then ranks) after checking
`targetPrimaryProf == templateData.profPrimary`.

That also refines a verdict from [heroes §13](../heroes/FINDINGS.md): the template system
was called "a RED HERRING… the player's save-my-build UI, not a delivery mechanism," on a
reachability closure containing zero message handlers. Correct about *delivery* — and it
does reach the wire, outbound, by this path. That closure was over s2c handlers; this is
c2s.

### 32.8 Two latent defects in the client, recorded because they are load-bearing for a server

- **`0x0010`'s clamp exceeds its buffer.** The framer clamps each count to `0x40` but its
  stack buffer holds **16** entries per array: `count >= 17` corrupts the second length
  prefix and `count >= 32` walks the return address. Unreachable today (its only caller
  passes 12), but **a server must never invite a client to send more than 16** — and our
  server, if it ever emits attribute templates, inherits that cap as a hard rule.
- **The decrease path has no bound check.** `0x00818CE0` asserts
  `attrib < arrsize(attribState->attrib)` (`ChCliAttrib:177`); `0x00818A90` indexes
  `[record + attrib*20 + 8]` with no check at all, and its thunk does not check either.
  Latent rather than live — the button handler cannot produce a bad index.

### 32.9 What this gives the server, and what it costs

`studies/review` flagged long ago that **"you sat there spending attribute points and the
server had nowhere to put them"** — `0x000E`/`0x000F` arriving x9 and unhandled. Our
server still has no arm for any of the three. It now has a complete spec:

> On `0x000F [agent, seq, attr]`: validate `attr < 51`, that the character owns the
> attribute's profession and that a primary attribute belongs to the primary profession,
> and that `pointsAvailable >= s_attribPoints[rank]`. Then reply, in one frame:
> `0x0036 [agent, seq]`, `0x0038 [agent, pointsAvailable]`,
> `0x003B [agent, attr, base, base+bonus]`. `0x000E` is the mirror with
> `s_attribPoints[rank-1]` refunded.

**The client will keep its prediction if the ACK never comes** — the modifier stays queued
and `0x00819270` *re-applies every pending modifier for an attribute on top of each fresh
authoritative value* (which is the single strongest piece of evidence that this queue is
what this section says it is). So a server that sends `0x0038`/`0x003B` without `0x0036`
does not merely leak a queue entry: it gets the client's guess re-stacked on top of its own
authority, every time.

### 32.10 Corrections this section owes

Four claims of mine fell to the skeptic and are fixed above rather than quietly dropped:
the increase thunk address (§32.6), the step order and the `0x10000030` payload — which
carries the **entry pointer**, not the sequence (§32.1) — the "free list" that is a LIFO
stack (§32.2), and the send pipeline: `0x00491DE0` is a **nullary getter for the connection
object**, not a packet builder, so the real shape is `0x007DCF00(conn, len, buf)` and the
two pushes before the getter belong to *its* call. Also confirmed-with-precision: the
applier's clamps are **one-sided**, running only when a delta is negative.

Named in `schema/overrides.json`: c2s `ATTRIBUTE_DECREASE` / `ATTRIBUTE_INCREASE` /
`ATTRIBUTE_LOAD` (0x0E/0x0F/0x10 — upstream's names, previously its weakest evidence tier
and now measured), and s2c `ATTRIBUTE_SPEND_ACK` (0x36), `ATTRIBUTE_POINTS_AVAILABLE`
(0x38), `ATTRIBUTE_POINTS_TOTAL` (0x39, high — two independent arcs) and
`AGENT_UPDATE_ATTRIBUTE` (0x3B).

## 33. `0x0093`'s value dword is a MINION COUNT — the client's own sentence says so (2026-08-19)

§31.3 left this as the container family's last open field: `charCtx+0x5BC` holds 8-byte
`{agentId, value}` entries, `0x0093` writes them, GmEffect reads them, and what the value
*is* was **NOT FOUND**, with "upkeep/maintained-effect value" recorded as band-level
RECONSTRUCTION. **That RECONSTRUCTION is REFUTED, the field is OBSERVED, and as of 2026-08-20 it is
CONFIRMED ON A CLIENT (§33.5).**

### 33.1 The answer, and how it was reached without guessing

The corpus could not help: **0 of 114,985 s2c messages across 13 live captures** carry
`0x0093` (one 14th capture has no `wire.jsonl` and could not be read — a floor, not a
census). So the meaning had to come from the consumer, and the consumer states it in
words. Caller `0x00521520` reads the value for an agent and hands it to **TextApi**
(`0x007C9410`) as the numeric parameter of one of two templates, chosen by whether that
agent is the local player:

```
value = GetMinionCount(agentId)             ; getter 0x0080E660, Find -> [entry+4] or 0
if (agentId == LocalAgentId())              ; 0x0080D3E0
     TextApi(50499, num1 = value)
else TextApi(50498, num1 = value, str1 = AgentName(agentId))   ; 0x0080D120
```

Resolved from the owner's own archive, exactly the two ids the code pushes:

```
50499 (0xC543)  'You are currently controlling %num1% minion[s].'
50498 (0xC542)  '%str1% is currently controlling %num1% minion[s].'
```

> **`0x0093` is `[agent_id, u32 minionCount]`: the number of minions that agent is
> currently controlling.** The value is the template's `%num1%`, and the branch that
> substitutes `%str1%` passes that same agent's NAME — so both the quantity and its owner
> are named by ArenaNet's own display text rather than inferred from position.

This is the "commit the id, resolve the string at run time" pattern working as evidence:
two single resolutions cited for a specific claim, which the provenance gate permits.

### 33.2 The other two consumers agree, and one of them is a numeric display

All three readers of the getter sit in `GmEffect.cpp` and treat the value consistently:

| reader | what it does with the value |
|---|---|
| `0x00521520` | renders it as `%num1%` in the two minion sentences above |
| `0x005244F0` | non-zero -> formats it through TextApi into a UI element and sets frame code **7**; zero -> sets frame code **8** and renders no number |
| `0x005246E0` | uses it only as a **non-zero gate** (asserting `GmEffect:3039 m_agentId` first), then acts on the AGENT id, not the value |

Two of the three therefore treat "0" as *"this agent controls no minions"* — which is
also what the getter returns for an agent that is simply absent from the array, making
absence and zero deliberately indistinguishable.

### 33.3 The wiring, end to end

```
s2c 0x0093 [agent_id, u32]   handler 0x0091EB50 -> worker 0x00812060
    -> upserts {agent, value} into the array at charCtx[+0x2C]+0x5BC
    -> posts frame 0x10000046
       subscribers: 0x0052349F, 0x005239A5  (both GmEffect)
    readers: getter 0x0080E660 -> the three consumers above
    removal: the 0x00F8 despawn sweep clears the agent's entry (§31.3)
```

A single POST and two SUBSCRIBEs are the only three `push 0x10000046` sites in the image,
so the event's producer/consumer set is closed.

### 33.4 What this does and does not do to §30.4

§30.4 answered a *membership* question — "which agents ARE minions" — and its body claim
stands untouched: `PtMinionRoster` reads the PARTY client at `[root+0x4C]`, and a row's
minion-ness is a monster-definition **flag test the panel performs itself**, with no
declaration opcode. Nothing here contradicts that.

**But that section's HEADING — "there is no minion message" — is one generalisation too
far, and it is corrected in place.** There *is* a minion message; it carries a COUNT, not
a membership, and it feeds the effects monitor rather than the roster panel. Membership
and cardinality are different facts with different mechanisms, and the heading collapsed
them. The honest form: *no minion message declares which agents are minions; `0x0093`
declares how many one agent has.*

### 33.5 CONFIRMED ON SCREEN — the client renders the number we send, and the plural with it

**MEASURED 2026-08-20, caged loopback, two runs** (`20260820T081504` bare,
`20260820T082018` with a buff alongside). Every clause of the prediction held, and the
readout is the client's own sentence rather than a pixel score:

| sent | effects monitor | tooltip |
|---|---|---|
| `0x0093 [agent, 7]` | a **minion icon appears**, the number **7** drawn on it | *"You are currently controlling 7 minions."* |
| `0x0093 [agent, 1]` | same icon, number **1** | *"You are currently controlling 1 minion."* |
| `0x0093 [agent, 0]` | icon **gone** | — |

**`AGENT_MINION_COUNT` is raised from medium to high.** Three things make this stronger
than "a number appeared":

- **The number is ours.** 7 was chosen because it is not 0, not 1 and not a plausible
  default; the client drew exactly 7, then exactly 1 when told 1.
- **The plural machinery moved with it** — *"7 minions"* against *"1 minion."* That is the
  `[s]` in template 50499 resolving, which no other field could have driven.
- **Zero removes the row, and the second run proves the removal is SPECIFIC.** With a buff
  icon present alongside, `0x0093 [agent, 0]` cleared the minion row and **left the buff
  icon standing** — so "the row went" is not "the monitor went". That matches the static
  read exactly: `0x005246E0` fetches the count, returns without creating its child frame
  when it is 0, and the child-create at `0x00521260` asserts `GmEffect:2985
  !FrameGetChild(ThisFrame(), effectCode)`.

The icon is a fleshy-creature artwork with the count drawn over it, sitting to the LEFT of
the buff icons in the same monitor — a sibling row, not a decoration on an existing one.

### 33.6 A method failure worth more than the result: I read the wrong frames and invented a mechanism to explain it

**The first run was called a null, and it was not.** It had already rendered all three
arms perfectly. `session.py` writes screenshots under **two** names — `w*.png` during the
`--walk` plan and `hold*.png` during the `--hold` that follows it — and with a 28–36 s
hover the walk consumes the entire probe schedule, so **every `hold*` frame is taken after
the probe has finished and cleaned up**. The analysis globbed `hold*`, measured zero
changed pixels in every HUD region, and reported a clean null.

What makes this worth writing down is what came next: rather than doubting the readout,
the null got a *mechanism*. A plausible one, built from real disassembly — the minion row
is a child frame created during a rebuild that walks the agent's buff lists, therefore an
effects monitor must exist first, therefore a bare `0x0093` has nothing to attach to. A
second run "confirmed" it by adding a buff and drawing the row. **Both halves were wrong:
the row needs no buff, and the second run only looked like a fix because it was the first
one whose frames were read from the right window.** The static reading it was built on is
still true; the inference stacked on top of it was invention, and it survived because it
explained an artifact.

Three rules this pays for, all of which already existed in this repo and none of which was
applied:

- **Anchor frames by timestamp, not by filename glob.** The memory note says exactly this
  and it was not consulted.
- **A negative needs a positive control** — and one was *available for free*: the same
  glob, on the same run, showed no buff icon either in the run that sent a buff. A
  precondition step that visibly fails to fire is the readout telling you it is broken,
  and it was read as data instead.
- **Two failed explanations is the stop-and-study line.** The invented mechanism was the
  second explanation; the first should have been "check the instrument."

**Harness trap, recorded for the next session: `--walk` and `--shots` do not overlap.**
`--shots` belongs to the hold, which begins only after the walk plan finishes. To watch a
probe while hovering, read `w*.png`; to watch it without a walk, `hold*.png` is right.

## 34. THE ARMS LANDED — a player can spend attribute points on a server we wrote (2026-08-20)

§32.9 ended with a spec and a gap: the protocol was fully read, and this server still had
nowhere to put a spend. `studies/review` had flagged that years earlier — *"you sat there
spending attribute points and the server had nowhere to put them"* — and the blocker was
never knowledge. It was **state**: ranks came from a content row and never moved, and the
point budget was one constant sent for both of `0x0037`'s fields.

**It works end to end.** Caged run `20260820T084923`: the operator's client opened its own
Skills and Attributes panel, clicked the **+** beside Tactics twice, and the panel followed.

| | unused points | Tactics | its arrows |
|---|---|---|---|
| before | **27** | 1 | ▼1 ▲2 |
| after click 1 | **25** | 2 | ▼2 ▲3 |
| after click 2 | **22** | 3 | ▼3 ▲4 |

Every number is the client's, drawn from what we sent. The wire:

```
c2s 0x000F ATTRIBUTE_INCREASE  [agent 1, seq 0, attr 21]
    ATTRIBUTE raise: 21 1 -> 2, 25 of 200 unspent (seq 0)
s2c 0x0036 ATTRIBUTE_SPEND_ACK(agent 1, seq 0)
s2c 0x0038 ATTRIBUTE_POINTS_AVAILABLE(25 of 200)
s2c 0x003B AGENT_UPDATE_ATTRIBUTE(attr 21 = 2)
```

**And the other direction, run `20260820T085218`:** one click on the same attribute's
DOWN chevron sent `0x000E`, and the server answered `lower: 21 1 -> 0, 28 of 200
unspent` -- the rank-1 refund of exactly 1 point, which is `s_attribPoints[1]`. Both
arms now have a live witness; `0x0010` does not (see 34.4).

### 34.1 Three predictions from the disassembly, confirmed by a player clicking a button

- **The sequence was 0 both times.** §32.2 predicted exactly this and said why: `+0x410`
  is a LIFO stack the allocator pops from and `+0x420` starts at 0, so one-at-a-time
  spending recycles sequence 0 forever. That was read out of a constructor and a
  `dec`/index pair; it is now a thing that happened.
- **The arrows RE-PRICED themselves after every click** — ▼1▲2 → ▼2▲3 → ▼3▲4. That is
  `0x00818E40`, the function §32.4 read and nobody had read before, recomputing an
  attribute's refund and next-rank cost from `s_attribPoints` after each change. The
  numbers on those chevrons are the client's own arithmetic agreeing with our content
  table, rank by rank.
- **Strength shows a ▼20 refund and NO up arrow at all.** `s_attribPoints[12] = -1` is the
  rank cap, and the client's increase path refuses rank 13 with the same test that refuses
  an attribute you do not own (§32.4). The panel renders that refusal as a missing button,
  which is the cheapest possible confirmation and it was visible before a single click.

### 34.2 What was built

- **`toolkit/authsrv/attribspend.py`** — the model, pure and stdlib-only: `AttributeRules`
  (the cost curve and the 51-row attribute table) and `AttributeState` (ranks, budget,
  and the client's refusals). No sockets, no content loading, no globals; it is handed the
  tables and answers questions, which is what makes it testable without a client.
- **The rules are the client's, and they are loaded rather than typed.** The cost curve
  comes from `s_attribPoints` via a new `attribpoints.py --emit-content`
  (`attribute_cost`, one row per rank, `client-table` provenance); the profession and
  `is_primary` flags come from the `attribute` table `attribtable.py` already emitted.
- **`content/world.toml` gained `points_total = 200`** on the player row. The number is
  observed (the level-20 maximum, and `0x0037`'s fourth field in 34 of 48 live sightings);
  giving it to *this* character is a choice, so the row stays `invented` and says so. The
  shipped ranks sink 173 of it, which is why the panel opens with 27 to spend.
- **Three arms**: `0x000F`, `0x000E`, and `0x0010` (a template spread, validated
  all-or-nothing against the client's own sixteen-entry buffer).
- **`test_attribspend.py`**, 35 checks, floor 35, one declared skip.

### 34.3 Two rules the code now enforces that prose could not

**A refusal still answers.** Every path sends the whole triple, including the ones that
change nothing. The client has already drawn the spend on its own panel, so silence is the
one reply that leaves us disagreeing with the client believing itself — and worse, §32.9's
measured hazard applies: `0x00819270` re-applies every unretired prediction on top of each
fresh authoritative value, so a half-answer stacks the client's guess on our own numbers,
every time. `send_attribute_reply` has no path that skips the ack.

**`0x0037` carries `(available, total)`, not one constant twice.** This is where the change
paid a debt the arc did not know it had: `authsrv.py` carried a comment saying every live
`0x0037` is `[0, 0]`, "8 of 8 connections", with the two fields' meaning CONTESTED. That
was true of the two captures it was written against. The corpus is now **13 captures and 48
sightings**, and it says something better:

| payload | n | what it is |
|---|---|---|
| `[0, 0]` | 14 | characters with no attribute points at all |
| `[1, 5]`, `[6, 10]` | 8 | low level, most of the budget spent |
| `[5, 200]`, `[41, 200]`, `[65, 200]`, `[74, 200]` | 26 | level 20, 200 lifetime |

The eight `[0, 0]` samples were eight low-level characters, not a universal. And the field
order is settled a third way, independent of §32.5's static read: **field3 ≤ field4 in 48 of
48**, which an order swap would break on the first `[1, 5]`.

### 34.4 What is still not modelled, stated plainly

- **Base and effective are sent equal.** `0x003B`'s two values differ only by an item
  bonus, which this server does not model — live, attribute 20 ran (10,11) and (11,12)
  while 17 and 21 sat at (8,8) and (10,10), so retail sends them unequal exactly when a
  rune or weapon is involved. Equal is a stated simplification, not a reading of the wire.
- **The state is per connection and does not persist.** A spend survives a map change
  (the burst now sources ranks from the live state) and dies with the session.
- **`0x0010` has never been seen on a wire** — zero live occurrences anywhere in the
  corpus — so its arm is built to a static reading and has no witness. It is armed because
  refusing it would leave a third of the family undone, not because anything confirmed it.
- **The hero gets the player's budget**, because it is sent the player's default ranks; its
  own attribute state is not modelled, since nothing lets us spend a hero's points.

### 34.5 It PERSISTS — and the second source of truth it exposed (2026-08-20)

§34.4 recorded "the state is per connection and does not persist" as a known limit. It is
closed, and closing it flushed out a latent bug that had been invisible for exactly as
long as the feature was missing.

**The bug first, because it is the interesting half.** `charstore.py` has carried an
`attributes` field — `[id, rank]` int pairs, validated at load — since 2026-08-18, and the
spawn burst read it for `0x003A` while the balance in `0x0037` was computed from the
CONTENT row. Two sources for one fact. They agreed on every run ever made, because nothing
had ever written the store, and **persisting a spend is precisely the thing that pulls
them apart**: the client would have been told one spread and a balance computed from a
different one. The fix is not a patch but a deletion — `attribspend.seed_ranks` is now the
single answer to "which ranks does this session start from", both paths call it, and it is
tested from both sides.

**The run, three processes:**

| | wire | panel |
|---|---|---|
| seed from a store written by an earlier arc | `0x0037 (55 of 200)`, `0x003A 17=9, 19=12` | **55 unused**, Strength 9, Hammer Mastery 12 |
| click Axe Mastery's **+** | `raise: 18 0 -> 1, 54 of 200`; `PERSIST: attributes saved` | 54 unused, Axe Mastery 1 |
| **restart the server** | `0x0037 (54 of 200)`, `0x003A 17=9, 18=1, 19=12` | **54 unused**, Axe Mastery **1** |

The third row is the acceptance criterion: a brand-new process, seeded only from
`vault/state/characters/`, told the client the state the previous process had saved.

That first row is also the sharpest confirmation of the cost table this arc has produced,
and it came free. The store held `17=9, 19=12` — a spread nobody chose for this test —
and the server computed **55 unused** from it: `s_attribPoints` cumulative to rank 9 is 48,
to rank 12 is 97, and 200 − 145 = 55. The panel then priced every chevron to match:
Strength ▼11 ▲13 (`[9]` and `[10]`), Hammer Mastery ▼20 and **no up arrow** (the rank cap),
Axe Mastery ▲1 and **no down arrow** (the rank floor). Four independent numbers, none of
them typed anywhere in this repo.

**What is stored is ranks only.** The point budget stays a content fact: nothing in this
server changes a character's lifetime total, and storing a derived number invites the two
to disagree — the same failure this section just removed. `available` is recomputed from
the ranks on every read, which is why the reloaded character cannot drift from the one that
saved.

**Schema, same day:** `0x0038 ATTRIBUTE_POINTS_AVAILABLE` and `0x003B
AGENT_UPDATE_ATTRIBUTE` go **medium → high**. Both now have two lineages — the static read
of their handlers, and their values rendered on the client's own panel across the caged
runs above. `0x0036 ATTRIBUTE_SPEND_ACK` deliberately **stays medium**: its mechanism is
measured, but the word ACK is our summary of what it does and no client string names it.
