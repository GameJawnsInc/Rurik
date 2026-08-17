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
- Its gate is not the reason: `[ctx[0x2c]+0x67C]` reads **1** (§36.8/36.10), so
  `0x00815E90` returns non-zero and the guarded install site `0x00578BF0` would have proceeded
  had it been reached. It is never reached.

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

## 2. The questions, in the order they should be answered

1. **What message, with what parameter, drives `UiCtlInstance` to construct type `[7]`?**
   The constructors are handlers; the selector is `hdr.param`. Read it, then ask whether
   anything on the wire can reach it. *(This is the one that decides the whole arc.)*
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
