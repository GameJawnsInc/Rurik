# The source tree behind the client, and the shape of the missing server

Build 38797 (`vault/client/2026-07-29_221c13772c7a/Gw.exe`, sha256 `221c1377…`)
and the build before it (`vault/client/2026-04-30_b174de1f2d8d/Gw.exe`). Static
analysis of both as files — the client was never launched, no debugger attached,
no process memory read, no network touched.

This corrects [HANDOFF.md](../../HANDOFF.md) §1 and answers a question that was
asked directly: *is the server binary just the game itself?* It is not, and the
way it is not gives R2–R4 a map — which of ArenaNet's code we can read, which we
cannot, and why the line falls where it does.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine. The offset or count is given so it can be re-read. |
| **INFERRED** | Our reading of measured bytes. The bytes are real; the interpretation is ours. |
| **UPSTREAM** | A reconstruction says it. Not ground truth. |
| **NOT ESTABLISHED** | We looked and could not settle it. Listed in §9 rather than glossed. |

Tool: `toolkit/clientscan/srctree.py`. Everything here is checked by
`toolkit/clientscan/test_srctree.py`, including a section whose only job is to
prove the negative result below can go red — see §2.

---

## 1. The answer in one page

- The shipped client carries **937 distinct `P:\Code\…` source paths** —
  ArenaNet's own build-machine paths, left in the image by `assert()` and a
  handful of other macros. 899 `.cpp`, 37 `.h`, one `.pdb`. MEASURED (936 on the
  older build).
- **Twelve `Gw\` subsystems ship a client half and only a client half:** Account,
  Char, Cinematic, Comm, Gadget, Guild, Item, Main, Mission, Net, Party, Trade.
  Ten mark it with a `Cli\` directory, two with a `…Cli.cpp` filename. MEASURED,
  identical on both builds.
- **No path in either image lies under a `Srv\` directory** — nor is any named
  `SrvXxx`, `SvXxx`, `GameSrv*`, `HostXxx` or `SimXxx`, nor does any contain
  "Server". Six spellings, zero hits, two builds four months apart. MEASURED.
- **So the client and the server were two build targets over one source tree.**
  The linker's own PDB path says so from the other direction:
  `P:\Code\.build\target\Gw\vs2022\builder_x32\bin\Gw.pdb` — one `.build`, a
  directory per target, and `Gw` is this target's name. INFERRED.
- **HANDOFF.md §1 is wrong in its second sentence.** *"There is no server
  binary"* is true of what we can hold. *"There never was one to have"* is false:
  it was built, out of the other half of this tree, and it is running right now.
  The correction is worth having because it changes the job from **invention**
  into **reimplementing the missing half of a tree whose other half we can
  read** — which is the discipline this repo is actually good at.
- **The shared trees have no Cli/Srv split at all:** `Base\` (79 files),
  `Engine\` (297), `Net\` (18), `Gw\Const\` (37). Both targets compiled these, so
  reading them is reading the server's own code rather than a client's view of
  it. MEASURED for the absence of any `Cli` directory; INFERRED that the server
  compiled them.
- **`-mock` is closed, and it is a mock *graphics device*.** No offline mode, no
  mock server. PLAN.md's Probe 5 is answered NO without launching anything — §7.

---

## 2. How a source path survives, and what that limits — MEASURED

MSVC compiles `assert()` with the file path in `.rdata`, handed to the assert
routine in a register; `toolkit/clientscan/asserts.py` already exploits this and
finds **19,758 sites on this build, all calling one routine** (19,620 until
2026-08-10, when the scan learned the two shapes it had been walking past —
see `studies/skillcast/FINDINGS.md` §1). A few other macros
emit paths the same way, which is why the path census (937) runs a little ahead
of the set of files carrying asserts (855).

**The limit, stated before the result rather than after it.** A source path
survives only if some macro in that translation unit emitted one. So *"no `Srv\`
path in the image"* is evidence that **no server-side translation unit is linked
into the client — not proof.** A linked TU emitting no path at all would be
invisible. The inference is strong, because every client-side subsystem here does
emit paths and a whole game server would be many translation units, but it is
INFERRED rather than MEASURED.

A path also never says what was in the file. Everything below about the
*contents* of the missing half is inference from names, and is marked so.

**The detector is tested against fabricated input, on purpose.** A negative
result is the one kind a broken instrument produces for free, and this one nearly
did: the first version of the pattern set had a lone backslash in a regex and
raised instead of matching, which from one step back is indistinguishable from
"no hits". Section 1 of `test_srctree.py` therefore feeds the detector six
fabricated server-side paths and requires all six to be caught. Blinding the
detector deliberately makes that section fail **while the census section still
reports its comfortable zeroes** — which is exactly the failure this guards.

---

## 3. The twelve split subsystems — MEASURED

```
                  files  Cli\  *Cli
  Gw\Char            14    11     0      Gw\Ui             375     0     0
  Gw\Net             11    11     0      Gw\Const           37     0     0
  Gw\Mission         12    10     0      Gw\AgentView       21     0     0
  Gw\Item            13     9     0      Gw\Download         9     0     0
  Gw\Guild            7     7     0      Gw\Composite        8     0     0
  Gw\Account          5     4     0      Gw\Chat             4     0     0
  Gw\Cinematic        5     4     0      Gw\Friend           3     0     0
  Gw\Party            3     3     0      Gw\Pref             3     0     0
  Gw\Gadget           2     2     0      Gw\Alert            2     0     0
  Gw\Trade            2     2     0      Gw\Lang             1     0     0
  Gw\Main             2     0     1      Gw\Param            1     0     0
  Gw\Comm             1     0     1
```

`P:\Code\Gw\Char\Cli\ChCliApi.cpp` is the client half of the character
subsystem. There is a `Gw\Char\Srv\` we do not have, and by the naming convention
its files are `ChSrv*.cpp`. Same for the other eleven. **That is the missing
work, enumerated** — twelve subsystem halves, not a whole game.

Two paths in the image do contain "Srv", and both are the other thing:
`Gw\Net\Cli\GcSrv.cpp` and `Net\FileCli\FcSrv.cpp` — the *client's* object
representing a server it connects to, each sitting under a client tree. The test
pins both, so the negative result cannot be a filter that is merely too narrow to
see anything.

Corroboration from a fourth direction, with its limits named: OpenTyria organises
its server as `GameSrv.c`, `GmPlayer.c` and so on, and
[studies/character/FINDINGS.md](../character/FINDINGS.md) cites `GameSrv.c` line
by line throughout. That is UPSTREAM. It corroborates that a server needs these
subsystems; it does **not** corroborate ArenaNet's names for them, because
OpenTyria's file names are its authors' choices.

---

## 4. What "no Cli marker" does *not* mean

Eleven `Gw\` subsystems carry no Cli marker, and two different things are mixed
together in that column. The path alone cannot separate them:

- **Client-only.** `Gw\Ui\` (375 files), `Gw\AgentView\`, `Gw\Download\`,
  `Gw\Composite\`, `Gw\Pref\`, `Gw\Alert\` are self-evidently the client's own —
  a UI tree, the *view* of an agent, the patcher, character-model compositing,
  local preferences, dialogs. There is no server half to be missing.
- **Shared.** `Gw\Const\` is 37 files of constants — `ConstSkill`, `ConstItem`,
  `ConstAttrib`, `ConstMission`, `ConstWorldMap`, `ConstChapter`, `ConstTitle`,
  `ConstHero`, `ConstEffect`, plus `Const\Programmer\` and `Const\Tool\`
  subtrees. These are what both ends had to agree on.

**`Gw\AgentView\` deserves its own sentence, because the split it implies is the
most useful structural fact here.** A tree called *AgentView* — 21 files,
`AvAgent`, `AvChar`, `AvGhost`, `AvProj`, `AvSelect`, `AvShadow` — is the
client's *rendering* of agents. The agent **model** is therefore somewhere else,
and it is: `Engine\Agent\`, ten files, in the shared engine, with no Cli marker
anywhere in it. INFERRED, and what it says is that the server's agent
representation was a build of the same `AgAgent.cpp` / `AgUpdate.cpp` /
`AgMsg.cpp` / `AgTimer.cpp` we can read today.

One honest complication: `Base\` carries at least one per-target specialization
by *filename* rather than directory — `Base\Os\Win32\Exe\ExeHeapCliRelease.cpp`.
So "shared" here means "not split into Cli/Srv wholesale", not "byte-identical
for both targets".

---

## 5. The shared layer, which is the part worth reading

| Tree | Files | What it is, and why it matters |
|---|---|---|
| `Net\Msg\` | 5 | `MsgChannel`, `MsgConn`, `MsgProp`, `MsgUtil`, `MsgPerf`. **The transport both ends spoke.** Already the highest-yield thing in the repo: [studies/msgtable](../msgtable/FINDINGS.md) recovered **751 messages across 25 tables** out of `MsgChannel.cpp`'s own structures, 4 of 4 oracle, and corrected OpenTyria's `MsgFormat` on both member set and size. |
| `Base\Crypt\` | 3 | `CptApi`, `CptRc4`, `CptSha`. The ARC4 our channel already implements is `CptRc4.cpp` — the server ran that same file. |
| `Net\GameLib\` | 2 | `GmName` (56 assert sites), `GmChatText`. A *game* library under `Net\` rather than under `Gw\`: shared between network endpoints. |
| `Engine\Agent\` | 10 | The agent model, per §4. |
| `Engine\Map\Path\` | 9 | `PathApi`, `PathBsp`, `PathBuild`, `PathData`, `PathDataImport`, `PathDir`, `PathFind`, `PathFlood`, `PathObstacle`. **R3's authority.** Read `PathDataImport` first — what it imports is in `Gw.dat`, which `toolkit/mapdata/` already reads. |
| `Gw\Const\` | 37 | The shared constants, per §4. |

---

## 6. What this changes, and what it does not

**"Reconstruct the server binary" is the wrong target.** Nothing recoverable is a
binary. The right target is the `Srv` half of `P:\Code`, and stated that way it
decomposes into four jobs of very different difficulty:

1. **Transport** — recovered. `Net\Msg\`, via studies/msgtable. 751 messages,
   arbitrated by the client's own tables rather than by a reconstruction.
2. **Constants and enums** — readable. `Gw\Const\`, and the whole assert corpus
   as a naming layer over it.
3. **Agent model and pathing** — readable, in the shared engine. `Engine\Agent\`,
   `Engine\Map\Path\`.
4. **The twelve `Srv` halves** — genuinely missing, and this is the work.
   Narrowed further by [PLAN.md](../../PLAN.md) §1.7: the *behaviour* that exists
   nowhere but the live service is absolute monster HP/energy/armor, spawn
   placement, drop tables, and AI decision logic.

**It changes no rung of the ladder and no priority in PLAN.md §8.** The capture
campaign is still the wasting asset and still comes first. What it changes is
what you expect to find when you go looking, and it retires a piece of fatalism:
the parts of the server that were shared with the client are not gone, and we
have been reading them for three studies already without naming what they were.

---

## 7. `-mock`, closed — MEASURED

[studies/handshake/PLAN.md](../handshake/PLAN.md) §3 carried `-mock` as
*"unexplained. A developer mock mode would be extraordinarily valuable"*, and
PLAN.md's **Probe 5** budgeted hours to it as *"the last unexplained flag with
real upside."*

Exactly three strings in the pinned image contain "mock", in either encoding:

```
ASCII 0x005400c8  'mockDevice'
UTF16 0x005421e8  'mock'          <- the flag itself, in the 41-entry table
UTF16 0x005454f0  'MockDevice'
```

Exactly one assert site names it — `MainCli:176  mockDevice` — inside
`Gw\Main\MainCli.cpp`'s command-line handling, alongside `MainCli:154/157 email`
and `MainCli:169/172 securityCharacterName`. And `MockDevice` sits in a run of
frame and window names: `BtnExit`, `BtnRestore`, `BtnMin`, `MockDevice`, `Game`,
`UiRoot`.

**`-mock` selects a mock graphics device. There is no mock server and no offline
mode. Probe 5 is answered NO, with no launch required.**

It is not worthless. A null render device is exactly what you want for running
many clients at once during the capture campaign, next to `-noui`, `-nosound`,
`-autologin` and the `CreateMutexA` NOP that already permits multiple instances.
That is a note for the capture arc, not this one.

The test pins the whole three-string set, so a future build that adds a real mock
server turns section 4 red — the outcome we would most want to be told about.

---

## 8. Two new leads, both small

**The client displays the server's own scheduler statistics.** A run of debug-HUD
labels at `0x0054535c`: `Current`, `Average`, `Bytes in`, `Bytes out`,
`Network Traffic`, `Ping (ms)`, `Last CPU`, `Last Tick Rate`, **`Srv Context
Cpu`**. MEASURED as strings. INFERRED: the server sends per-context CPU and a
tick rate, so its architecture is *contexts* driven by a *tick*, and some opcode
among the 751 carries those numbers. Finding it would be the server describing
its own scheduler. NOT ESTABLISHED: which opcode, or whether it is still sent.

**`Net\FileCli\` implies an unshipped `FileSrv`.** Five files — `FcApi`,
`FcArchive`, `FcDep`, `FcSrv`, `Win32FcImage` — the client of ArenaNet's asset
file service, which `gw-preservation/fileserver-utils` pulls from by file id. So
`P:\Code` built at least three network targets: the game client, the game server,
and the file service. Not actionable; it sets the scale of the tree.

---

## 9. Not established

1. **Whether the missing directories are actually named `Srv`.** `Cli` is
   MEASURED; `Srv` is the obvious complement and both OpenTyria and Headquarter
   use it, but no ArenaNet artifact we hold spells it. A symbol-bearing WASM
   build, if one is ever retrieved (PLAN.md §1.3), would settle it.
2. **Which no-marker subsystems are shared and which are client-only.** §4 sorts
   the obvious ones by name. Nothing measures it.
3. **Whether the server built the same `Engine\` and `Base\`, or forked
   variants.** `ExeHeapCliRelease.cpp` proves per-target specialization exists
   inside `Base\`, so "shared" is a default rather than a guarantee.
4. **The assert corpus on the older build.** `asserts.py` reports 19,680 sites
   (19,544 edx-first + 74 ecx-first + 62 shared-tail, so all three shapes are
   present on both builds) with `single-routine=False` and its own warning on
   `2026-04-30_b174de1f2d8d`, because its callee VA is pinned to the newer image.
   Nothing in this study depends on it — `srctree.py` does not use the assert
   idiom at all — but the older build's assert corpus is not currently
   trustworthy, and that is worth fixing before anyone leans on it.
