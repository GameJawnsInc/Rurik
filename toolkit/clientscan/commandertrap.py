"""Trap the commander-create chain in a live client, to answer the one question
static reading and a memory read both left open.

WHY THIS EXISTS. `studies/heroes/FINDINGS.md` §32 stops the heroes arc at a
single unmeasured fact. The party-window hero button asserts `commander` /
`GmView.cpp(5890)` because no commander object exists for our hero -- §27
MEASURED that, reading the container header out of the live process: `cap=7
count=0`, seven empty slots. But an empty container cannot distinguish

    (a) the event that would create one is never RAISED, from
    (b) it is raised, and the handler's my-id filter REJECTS our entry.

Both leave the container at zero, and four hypotheses have already been killed
by experiment here (`inventoryId` §16, `msg+0x10` §19, the party-cache gate §26,
the subscriber map §28). §26.4 named the instrument that separates them and the
arc never spent it: a trap on `0x008590CA`.

WHAT IT DOES, and what it deliberately does not. It is a debugger: it attaches
with `DebugActiveProcess` and sets EXECUTE breakpoints in the processor's DEBUG
REGISTERS (DR0..DR3), which are per-thread state, not memory. **Nothing is
written into the client.** No `int3` is patched over an instruction, no code
cave is assembled, no DLL is injected, no thread is created in the target. That
matters beyond tidiness: an `int3` patch mutates the very bytes this arc has
been reading, and every address in `studies/heroes/` was measured against the
unmodified image. `CLAUDE.md` carve-out 3 permits a compiler; this did not need
one, which is the cheaper end of the same permission.

THE CHAIN, and every address below is OBSERVED on build 38833 -- disassembled,
with the bytes recorded here and re-verified against the RUNNING process before
a single breakpoint is armed:

    0x00859010  the 0x01C2 worker entry            <- THE CONTROL
    0x008590CA  `push 0x1000011e` -- the raise      (a) above
    0x004E5DE1  dispatch case 93, the handler body
    0x004E5DF2  `cmp [esi+4],eax` -- the my-id filter, WITH BOTH OPERANDS  (b)

THE PREDICTION, stated before the run because a probe with no stated expectation
can be rationalised into agreeing with anything afterwards. `0x00524CC0`
(`GmHeroCommander`, the roster-index search) reaches the get-or-create
`0x00524C40` on BOTH of its exits -- found, via `0x00524D2C` -> `0x00524D1A`,
and NOT-found, via `0x00524D03` -> the `GmHeroCommander:140`
`rosterIndex != (unsigned)-1` assert -> `0x00524D1A`. So if that search had ever
run for our hero a commander would exist whatever the key, and a miss would have
raised its own assert at instance-load time. We see neither. **Therefore the
break is upstream of the search, and the trap should show the chain stopping at
the raise, at the dispatch, or at the filter.** If instead `filter` hits and
PASSES, the prediction is dead and the fault is inside the search -- which is a
result, and a different arc.

THE CONTROL, and it is the §28 lesson wired in rather than written down. §28's
subscriber reader produced a clean, memorable, completely WRONG answer -- "the
commander event has no subscriber" -- and only a control caught it. So: the
worker site MUST hit. If our `0x01C2` never reaches `0x00859010`, the trap
machinery is unproven and NO verdict is given about the sites downstream of it,
because "it never fired" and "we cannot see it fire" look identical from here.

    python toolkit/clientscan/commandertrap.py --wait --seconds 180
    python toolkit/clientscan/commandertrap.py --pid 1234 --sites worker,search,create,notfound

Windows, standard library only (`ctypes`). Read-only against the target's
memory; the only thing it writes anywhere is DR0..DR3/DR7 in the target's own
thread contexts, and it clears them again on detach.
"""
import argparse
import ctypes
import os
import struct
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
sys.path.insert(0, HERE)
import keytap                                                   # noqa: E402

# THE DEBUGGER MOVED TO hwtrap.py ON 2026-09-11 -- the image base, the ASLR
# slide, `unslide`, the Win32 block, `TrapError`, `dr7_for` and `HwTrap` all
# live there now, unchanged. `import hwtrap` is not decoration: SLIDE is
# MUTABLE MODULE STATE with exactly one owner, so `main()` below writes
# `hwtrap.SLIDE` through the module object. A `from hwtrap import SLIDE` would
# bind a copy that stays 0 while the real one moves, and `unslide` would then
# answer with un-slid VAs SILENTLY -- the failure the comment on SLIDE was
# written against, arriving by a new route.
import hwtrap                                                   # noqa: E402
# Re-exported at the site the names were cut from, for THIS file's `_cap_*`
# readers, `SITES` and `main()`, and for `test_commandertrap.py`, which reaches
# `dr7_for`, `TrapError`, `THREADENTRY32`, `TH32CS_SNAPTHREAD` and
# `INVALID_HANDLE_VALUE` through `ct.` and would otherwise find nothing.
from hwtrap import (                                            # noqa: F401,E402
    IMAGE_BASE, MAX_SLOTS, INVALID_HANDLE_VALUE, TH32CS_SNAPTHREAD,
    THREADENTRY32, TrapError, dr7_for, kernel32, unslide)


# `HwTrap` moved to hwtrap.py on 2026-09-11. Read here by `main()` below and
# by `test_commandertrap.py` (`ct.HwTrap`, sections 3, 8, 9 and 10).
from hwtrap import HwTrap                                       # noqa: F401,E402


# ---------------------------------------------------------------------------
# The sites
# ---------------------------------------------------------------------------
# `Site` moved to hwtrap.py on 2026-09-11. Read here by SITES below and by
# `test_commandertrap.py` (`ct.Site`).
from hwtrap import Site                                         # noqa: F401,E402


# `_dw` moved to hwtrap.py on 2026-09-11. Read by every `_cap_*` reader below,
# by `SITES`'s `create` lambda, and by `compositetrap.py` as `ct._dw`.
from hwtrap import _dw                                          # noqa: F401,E402


def _cap_worker(ctx, reader):
    """At `push ebp`, the seven args are still on the stack at [esp+4..].

    `ret 0x1c` = 28 bytes = 7 arguments, and 25.1 decoded which wire field each
    one is. Reading them here checks that decode against the live stack rather
    than against our own sender.
    """
    a = _dw(reader, ctx.Esp, 8)
    if not a:
        return {"esp": ctx.Esp, "args": None}
    return {"this(ecx)": ctx.Ecx, "party_id": a[1], "msg+8 owner": a[2],
            "msg+0xc agent": a[3], "msg+0x10 heroId": a[4],
            "hardcoded0": (a[5], a[6]), "msg+0x14": a[7]}


def _cap_raise(ctx, reader):
    """At `push 0x1000011e`, `ecx` still holds the entry (26.1) and `esi` the
    party id or 0. So this dumps the row the client actually stored."""
    e = _dw(reader, ctx.Ecx, 6)
    return {"entry(ecx)": ctx.Ecx, "esi": ctx.Esi,
            "entry+0 agent": e[0] if e else None,
            "entry+4 owner": e[1] if e else None,
            "entry+8 heroId": e[2] if e else None,
            "entry+0xc": e[3] if e else None,
            "entry+0x10": e[4] if e else None,
            "entry+0x14": e[5] if e else None}


def _cap_case93(ctx, reader):
    """`edi` is the dispatcher's payload; `[edi+4]` is the entry pointer, which
    is what `0x004E5DE7 mov esi,[edi+4]` reads one instruction later. That
    single instruction is what closes 25.4's loose end."""
    p = _dw(reader, ctx.Edi, 2)
    return {"payload(edi)": ctx.Edi,
            "payload+0": p[0] if p else None,
            "payload+4 entry": p[1] if p else None}


def _cap_filter(ctx, reader):
    """THE measurement. `cmp [esi+4],eax`: eax is the my-id from `0x0084DD70`
    and `[esi+4]` is the entry's owner. Both operands, at the instant the
    client compares them -- and 27.2 said reading the my-id needed a TLS walk,
    which is true from outside and irrelevant from in here."""
    e = _dw(reader, ctx.Esi + 4, 2)
    owner = e[0] if e else None
    return {"entry(esi)": ctx.Esi, "my_id(eax)": ctx.Eax,
            "entry+4 owner": owner, "entry+8 heroId": e[1] if e else None,
            "VERDICT": ("PASSES -- falls through to call 0x524cc0"
                        if owner == ctx.Eax else
                        "REJECTS -- jne 0x4e62f4, the handler returns")}


def _cap_posse(ctx, reader):
    """GmPosseRoster's handler, with the message it was handed.

    At `0x005392AC` esi is the message struct (loaded at `0x005392A8`) and
    `[esi+4]` is the switch selector. 36.9 left three possibilities and this
    separates the first two by itself: NO hits means the handler is not
    installed; hits WITHOUT message 9 mean it is installed and never created;
    a message 9 hit would contradict 36.7's census and put the fault elsewhere.
    """
    m = _dw(reader, ctx.Esi + 4, 1)
    v = m[0] if m else None
    return {"message([esi+4])": v,
            "VERDICT": ("MESSAGE 9 -- instance create, the subscribe path"
                        if v == 9 else f"message {v}, not the create path")}


def _cap_gate(ctx, reader):
    """THE GATE on GmPosseRoster's existence. `0x00815E90` resolves the root
    context, takes `ctx[0x2c]` (the same character context 14 read `+0x6BC`
    from) and loads `[+0x67C]` into esi; zero returns 0 and the caller at
    `0x00578BFE` skips installing the posse-roster handler entirely. No handler
    means no `message 9`, no subscribe block, and therefore no roster
    subscriber for 0x1000011E -- which is exactly what 36.7 measured."""
    return {"field ctx[0x2c]+0x67C (esi)": ctx.Esi,
            "bound-holder (edi)": ctx.Edi,
            "VERDICT": ("ZERO -- gate FAILS, GmPosseRoster is never installed"
                        if ctx.Esi == 0 else
                        "non-zero -- gate passes, the roster handler installs")}


def _cap_subscribe(ctx, reader):
    """WHO registers WHAT. `esi` holds the event id (it is stored to the scratch
    slot at `0x0064CDA0` and passed to the lookup by address), and `[ebp+4]` is
    the caller's return address -- so a census here names both the event and the
    code that subscribed to it. 34 could read whether a subscriber EXISTS; this
    reads where it came from."""
    # TWO FRAMES, and the second is the one that answers the question. 36.6:
    # capturing only `[ebp+4]` returned the SAME value for every event --
    # 0x00633C07, inside the subscribe WRAPPER 0x00633BD0 -- because the
    # trapped function is the wrapper's callee, so its return address is the
    # wrapper by construction and identifies nothing. The subscriber is one
    # frame further up: `[[ebp]+4]`. Both are reported so the inner value stays
    # visible as its own control: if `inner` ever varies, this reasoning about
    # the frame layout is wrong and `outer` cannot be trusted either.
    inner = _dw(reader, ctx.Ebp + 4, 1)
    saved = _dw(reader, ctx.Ebp, 1)
    outer = _dw(reader, saved[0] + 4, 1) if saved and saved[0] else None
    return {"event(esi)": ctx.Esi,
            "inner(wrapper)": inner[0] if inner else None,
            "SUBSCRIBER(outer)": outer[0] if outer else None}


def _cap_lookup(ctx, reader):
    """THE subscriber answer, read out of the client's own lookup.

    At `0x0064CA47`, `ebp` is set up and `[ebp+8]` still holds the event id
    (stored back at `0x0064CA3B`), while `eax` is whatever `0x00491F20`
    returned for it. 28 could not walk this map -- its keys hash through
    `0x004920B0` and a plain bucket walk finds nothing -- and this sidesteps
    the whole problem: let the client hash it, and read the answer.
    """
    ev = _dw(reader, ctx.Ebp + 8, 1)
    return {"event(ebp+8)": ev[0] if ev else None,
            "subscribers(eax)": ctx.Eax,
            "VERDICT": ("NO SUBSCRIBER -- takes `je 0x64ca58`, the raise "
                        "returns having called nothing"
                        if ctx.Eax == 0 else
                        "SUBSCRIBED -- falls through to `call 0x64c7d0` "
                        "with the list")}


# Build 38833. Disassembled, not copied from a study: every `code` below is the
# instruction's own bytes as `codescan --dis` printed them.
SITES = {
    "worker": Site(
        "worker", 0x00859010, bytes.fromhex("558bec83ec08"),
        "0x01C2's worker entry -- THE CONTROL. If this never fires, nothing "
        "below it means anything.", _cap_worker),
    "raise": Site(
        "raise", 0x008590CA, bytes.fromhex("681e010010"),
        "`push 0x1000011e` -- the commander event being raised, gated on the "
        "party-cache miss at 0x008590AF (26.2)", _cap_raise),
    "case93": Site(
        "case93", 0x004E5DE1, bytes.fromhex("57e849383e00"),
        "dispatch case 93 -- the handler the raise reaches (25.2)",
        _cap_case93),
    "filter": Site(
        "filter", 0x004E5DF2, bytes.fromhex("394604"),
        "`cmp [esi+4],eax` -- the my-id filter, with BOTH operands",
        _cap_filter),
    # THE BISECT SITE, added 2026-08-23 for an anomaly this file's own verdict
    # refused to believe. A `--hero-late` run reported case93=1 filter=0, and
    # the verdict says that "should be impossible -- they are four
    # instructions apart with no branch between them". Re-read on 38833, that
    # is correct: 0x004E5DE1 `push edi; call 0x8c9630; mov esi,[edi+4]; add
    # esp,4; call 0x84dd70; cmp [esi+4],eax` is straight-line with TWO calls
    # in it. So execution either stopped inside a call or the trap missed the
    # hit, and this site separates those: it is the instruction the FIRST call
    # returns to. case93 hit + postcall miss => 0x8c9630 did not return;
    # case93 + postcall hit + filter miss => 0x84dd70 (the identity getter,
    # which reaches through TLS at 0x0047F660) did not return; all three hit
    # => the earlier miss was the trap, not the client.
    "postcall": Site(
        "postcall", 0x004E5DE7, bytes.fromhex("8b770483c404"),
        "`mov esi,[edi+4]` -- where case 93's first call RETURNS. Bisects a "
        "case93-without-filter run into 'a call did not return' versus 'the "
        "trap missed it'",
        capture=lambda ctx, rd: {"esi(entry) after load": None,
                                 "edi(payload)": ctx.Edi,
                                 "VERDICT": "the first call returned"}),
    # Downstream. Not in the default set because the prediction says the chain
    # stops before them -- so they are the flags a SECOND run uses if it does not.
    "search": Site(
        "search", 0x00524CC0, bytes.fromhex("558bec515356"),
        "GmHeroCommander's roster-index search, which reaches get-or-create on "
        "BOTH exits"),
    "notfound": Site(
        "notfound", 0x00524D06, bytes.fromhex("688c000000"),
        "the `GmHeroCommander:140 rosterIndex != (unsigned)-1` assert -- the "
        "search ran and found no entry"),
    "create": Site(
        "create", 0x00524C40, bytes.fromhex("558bec5153"),
        "get-or-create. If this fires, a commander object exists and 27's "
        "count=0 is about a later teardown, not a create that never ran",
        # WHICH AGENT, and it is the question left after the fix worked.
        # studies/pvpui/FINDINGS.md 20 measured a commander existing for the
        # first time -- count 0 -> 1 -- but `heroCommanderSlot` holds container
        # KEYS, not agent ids, so it cannot say WHOSE. The caller at 0x00524FA3
        # pushes `edi = [rec+8]`, the agent id the rebuild copied out of the
        # party container (11), so the argument here names it directly.
        #
        # At the breakpoint `push ebp` has NOT executed, so [esp] is the return
        # address and [esp+4] is arg0. Both are read: a return address that is
        # not 0x00524FA9 means the call came from somewhere other than the
        # rebuild loop, and then the id is about something else.
        capture=lambda ctx, rd: (lambda w: {
            "return address (VA)": None if not w else unslide(w[0]),
            "from the rebuild loop": None if not w else
                unslide(w[0]) == 0x00524FA9,
            "key (arg0)": None if not w else w[1],
            # NOT an agent id, and the first version of this string said
            # it was. The rebuild passes `[item+8]`, and `agents.py`
            # names item+8 as 0x01C2's `scan_key` (msg+0x10) -- which
            # callers fill with the HERO ID, not an agent id. So a 1 here
            # is hero 1, not the player's agent 1; the two collide on the
            # default rig, which is exactly the trap `--player-number`
            # exists to break.
            "VERDICT": "unreadable stack" if not w else (
                f"the commander is filed under key {w[1]} -- this is "
                f"0x01C2's scan_key (msg+0x10), the value --hero-roster-id "
                f"overrides, NOT an agent id"),
        })(_dw(rd, ctx.Esp, 2))),
    "bulk": Site(
        "bulk", 0x004E5D20, bytes.fromhex("8b1eff37895da8"),
        "dispatch case 90, the bulk activeHeroes scan -- the path that DOES "
        "create commanders. 25.2 says all eight callers of its raiser are UI"),
    "lookup": Site(
        "lookup", 0x0064CA47, bytes.fromhex("85c0740dff75"),
        "`test eax,eax` one instruction after the subscriber-map lookup in the "
        "raise (0x0064CA30). EAX IS THE SUBSCRIBER LIST for the event in "
        "[ebp+8]: zero takes `je 0x64ca58` and the raise returns having called "
        "nothing. This answers 28's question WITHOUT replicating the 0x004920B0 "
        "hash -- the client does the lookup and we read its result.",
        capture=lambda ctx, rd: _cap_lookup(ctx, rd),
        arm_after="raise", oneshot=True),
    # THE SAME QUESTION, ASKED OF THE EVENT THAT ACTUALLY DRIVES THE COMMANDER.
    # `studies/pvpui/FINDINGS.md` §14.3: the rebuild `0x00524E00` has exactly ONE
    # caller, inside GmView's event case 90, selected by exactly one event --
    # `0x10000114`, NOT the `0x1000011E` the heroes arc spent itself on. Run 1
    # (2026-08-17) measured `bulkraise` (0x00858850's entry) firing once while
    # `bulk` (that case) never fired at all, with `worker` green as the control.
    # BOTH branches of 0x00858850 raise 0x10000114 -- the arg1 != 0 path at
    # 0x008588AD below, and the arg1 == 0 path via `mov eax,0x10000114` at
    # 0x008588D1 into the shared tail -- so the entry firing means the event WAS
    # raised. `agents.py:434` sends PARTY_SET_MINE with arg1 = 1, which is this
    # path, so THIS is the site that fires on our wire.
    "raise114": Site(
        "raise114", 0x008588AD, bytes.fromhex("6814010010"),
        "`push 0x10000114` inside 0x00858850, reached from the 0x01B2 "
        "PARTY_SET_MINE handler. The event whose GmView case calls the "
        "commander-model rebuild."),
    "lookup114": Site(
        "lookup114", 0x0064CA47, bytes.fromhex("85c0740dff75"),
        "the same subscriber-map read as `lookup`, armed off `raise114` instead "
        "of `raise`. EAX is the subscriber list for 0x10000114 at the moment we "
        "raise it; zero means raised into nothing, which would explain case 90 "
        "never running without any appeal to ordering.",
        capture=lambda ctx, rd: _cap_lookup(ctx, rd),
        arm_after="raise114", oneshot=True),
    # AND IF IT IS SUBSCRIBED, WHO GOT IT. Run 2 (2026-08-17) measured
    # `lookup114` SUBSCRIBED while `bulk` -- GmView's case for that very event --
    # never fired. Exactly one of three things is then true: the subscriber is
    # not GmView, GmView's dispatch routes 0x10000114 somewhere other than case
    # 90, or `bulk`'s address is not that case body. This site separates them by
    # reading the event id GmView's own event half is entered with.
    #
    # `0x004E366A` is `sub eax, 0x10000007`, the first instruction of the event
    # half of GmView's frame handler 0x004E27D0, so EAX still holds the RAW
    # event id when the breakpoint fires. It is hot -- every UI event GmView
    # receives passes here -- which is why it is deferred behind `raise114` and
    # oneshot: the raise is a synchronous call chain on one thread, so the first
    # entry after it is ours. Same argument `lookup` rests on (§33.6).
    "gmvEvent": Site(
        "gmvEvent", 0x004E366A, bytes.fromhex("2d07000010"),
        "the event half of GmView's frame handler, entered with the raw event "
        "id in EAX. Armed off `raise114`, so it names the event GmView is "
        "handed at the moment we raise 0x10000114.",
        capture=lambda ctx, rd: {
            "event id (eax)": ctx.Eax,
            "is 0x10000114": ctx.Eax == 0x10000114,
            "VERDICT": ("GmView WAS handed 0x10000114 -- so the break is in its "
                        "own dispatch, not in delivery"
                        if ctx.Eax == 0x10000114 else
                        "GmView was handed a DIFFERENT event -- ours went to "
                        "some other subscriber, or not to GmView at all"),
        },
        arm_after="raise114", oneshot=True),
    # THE CENSUS FORM OF THE SAME SITE, and it exists because run 3's oneshot
    # cannot carry the weight the deferred argument gives `lookup`.
    #
    # `lookup` is sound deferred-and-oneshot because `0x0064CA47` sits INSIDE the
    # raise's own synchronous call chain -- the first hit after the trigger is
    # necessarily ours. `0x004E366A` is not: it is only reached if GmView's frame
    # handler is entered for the event at all, so "the next hit was some other
    # event" is consistent with BOTH "GmView never got ours" and "GmView got ours
    # by a path that does not pass here". Heroes §36.7 named GmView's SUBSCRIBER
    # as `0x004ED055`, which is not this function -- so the subscriber callback
    # and the frame-handler event half are two different doors, and a oneshot at
    # one of them cannot speak for the other.
    #
    # Armed for the whole session with a high `--max-hits`, this answers the
    # question the oneshot only gestured at: does 0x10000114 EVER reach GmView's
    # frame handler? Same shape as `lookupany`, and for the same reason.
    "gmvEventAny": Site(
        "gmvEventAny", 0x004E366A, bytes.fromhex("2d07000010"),
        "the event half of GmView's frame handler, armed for the whole session. "
        "A census of every event id GmView's frame dispatch is entered with -- "
        "0x10000114's presence or absence in it is the measurement.",
        capture=lambda ctx, rd: {"event id (eax)": ctx.Eax}),
    # GMVIEW'S OWN SUBSCRIBE OF 0x10000114, TIMESTAMPED AGAINST OUR RAISE.
    #
    # Run 5's `subscribe` census DID find GmView registering 0x10000114 (outer
    # return address 0x004ED03F un-slid, which is this call's return), so §18.1
    # holds: we are on the non-observer branch and GmView takes the event we
    # raise. What the census could not say is WHEN -- it aggregates, and
    # aggregated rows carry no timestamps, while the ordered hit list showed
    # only `worker` and `raise114`, both at +1.710s.
    #
    # This site is the same subscribe, anchored on the `call` so it lands in the
    # ORDERED list. Run it beside `raise114` and the two timestamps answer the
    # only question left: does GmView subscribe before or after we raise.
    #
    # `0x004ED03A` is `call 0x00633BD0` with EAX already holding the computed
    # event id from `add eax, 0x10000114` five instructions earlier, so the
    # capture also re-reads which branch of §18's conditional was taken --
    # making this its own control rather than trusting the static reading.
    "gmvSub114": Site(
        "gmvSub114", 0x004ED03A, bytes.fromhex("e8916b1400"),
        "GmView's CONDITIONAL subscribe call. EAX is the event id it is "
        "registering -- 0x10000114 on the normal branch, 0x1000012B in observer "
        "mode. Timestamped against `raise114`.",
        capture=lambda ctx, rd: {
            "event being subscribed (eax)": ctx.Eax,
            "branch": ("NORMAL -- 0x10000114, the event we raise"
                       if ctx.Eax == 0x10000114 else
                       "OBSERVER -- 0x1000012B, not the event we raise"
                       if ctx.Eax == 0x1000012B else "UNEXPECTED"),
        }),
    "posseMsg": Site(
        "posseMsg", 0x005392AC, bytes.fromhex("8b460483f856"),
        "GmPosseRoster's handler at its switch selector, esi already loaded. "
        "Reads WHICH message the roster handler receives -- the discriminator "
        "for 36.9's surviving possibilities.",
        capture=lambda ctx, rd: _cap_posse(ctx, rd)),
    "posseGate": Site(
        "posseGate", 0x00815EA0, bytes.fromhex("85f67505"),
        "`test esi,esi` inside 0x00815E90, where esi IS ctx[0x2c]+0x67C. This is "
        "the guard at 0x00578BFE that decides whether GmPosseRoster's message "
        "handler is installed at all -- and 36.7 measured that the roster never "
        "subscribes to the commander event despite its window being on screen.",
        capture=lambda ctx, rd: _cap_gate(ctx, rd)),
    "subscribe": Site(
        # ANCHORED ON THE `call`, NOT THE `mov` FIVE BYTES EARLIER, and the
        # reason is a defect this guard caught in itself. `0x0064CDA4` is
        # `mov ecx, 0x00C11BC4` -- an absolute DATA address, which the loader
        # RELOCATES. Live it reads `b9c41be200` = 0x00E21BC4, and
        # 0xE21BC4 - 0xC11BC4 = 0x210000 is exactly the ASLR slide, so the
        # verification refused a site that was perfectly correct. A byte anchor
        # must not contain a relocated absolute address. `call rel32` is
        # PC-relative and therefore identical in the file and in memory, and at
        # this instruction `esi` and `[ebp+4]` hold the same values they held
        # five bytes earlier.
        "subscribe", 0x0064CDA9, bytes.fromhex("e87251e4ff"),
        "the subscriber-map INSERT path: it looks the event up and, when absent, "
        "allocates a list and stores the id (`mov [ebx],esi`). Census it to learn "
        "which UI construction registers 0x1000011E and when -- the question 34.4 "
        "and 35 could not reach by watching the raise. HOT: raise --max-hits.",
        capture=lambda ctx, rd: _cap_subscribe(ctx, rd)),
    "lookupany": Site(
        "lookupany", 0x0064CA47, bytes.fromhex("85c0740dff75"),
        "THE POSITIVE CONTROL for `lookup`, and the same address armed with no "
        "trigger. A reader that only ever prints NO SUBSCRIBER is 28 again, so "
        "this censuses whatever events the client raises on its own and must "
        "show some of them SUBSCRIBED. Hot by construction -- it is capped by "
        "max_hits and the report says so.",
        capture=lambda ctx, rd: _cap_lookup(ctx, rd)),
    "bulkraise": Site(
        "bulkraise", 0x00858850, bytes.fromhex("558bec568bf157"),
        "the function that raises 0x10000114, reached through 0x00856920. If "
        "this never runs, no UI action in our session asks for the scan"),
}

DEFAULT_SITES = ("worker", "raise", "case93", "filter")
CONTROL = "worker"


# `wait_for_module` and `verify_sites` moved to hwtrap.py on 2026-09-11.
# `wait_for_module` is NOT re-exported: its only caller anywhere is
# `verify_sites`, inside that module. `verify_sites` is read by `main()` below,
# by `test_commandertrap.py` and by `compositetrap.py` as `ct.verify_sites`.
from hwtrap import verify_sites                                 # noqa: F401,E402


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
# `_report` moved to hwtrap.py on 2026-09-11. Read by `main()` below, by
# `test_commandertrap.py` and by `compositetrap.py` as `ct._report`.
from hwtrap import _report                                      # noqa: F401,E402


def _verdict(counts, sites, out=sys.stdout):
    """The control gate. 28's lesson, wired in rather than written down."""
    w = out.write
    names = [s.name for s in sites]
    w("\n" + "=" * 72 + "\nVERDICT\n" + "=" * 72 + "\n")
    if CONTROL in names and not counts.get(CONTROL):
        w("  REFUSING TO ANSWER.\n"
          "  The control site `worker` (0x00859010, 0x01C2's own worker) never\n"
          "  fired. Either the server sent no hero-add this run, or this trap\n"
          "  does not see what it thinks it sees. Every site below the control\n"
          "  reads the same either way, so 'the raise never fired' would be\n"
          "  indistinguishable from 'the trap is broken' -- which is exactly the\n"
          "  false reading 28 caught in the subscriber reader.\n")
        return 2
    stops = []
    for n in names:
        stops.append((n, counts.get(n, 0)))
    w("  chain: " + " -> ".join(f"{n}={c}" for n, c in stops) + "\n\n")
    if counts.get(CONTROL) and not counts.get("raise", 1):
        w("  The worker RAN and the raise did NOT. The event is never raised,\n"
          "  so no handler runs and nothing is ever created. 27.2's branch (a).\n")
    elif counts.get("raise") and not counts.get("case93", 1):
        w("  The raise RAN and case 93 did NOT. The event is raised into\n"
          "  nothing -- which is 28's subscriber question, answered by trap\n"
          "  rather than by walking a map we could not read.\n")
    elif counts.get("case93") and not counts.get("filter", 1):
        w("  Case 93 ran and the filter site did not. There is no BRANCH\n"
          "  between them -- but there are two CALLS, and this verdict used\n"
          "  to say the gap was impossible and to suspect the trap.\n"
          "  MEASURED 2026-08-23: the trap was right and that reading was\n"
          "  wrong. Case 93's first call (0x8c9630) forwards the event to the\n"
          "  SkillListContext singleton (ecx = 0x10886d0, then 0x8d2500),\n"
          "  whose OWN my-id test passes and calls 0x8d26d0, which ASSERTS\n"
          "  `SKILL_LIST_USERS != skillListUser` at 0x8d270a\n"
          "  (GmCtlSkListContext.cpp:574). The client raises its crash dialog\n"
          "  there, so the call never returns and the two later sites never\n"
          "  execute. Check the session log for that assert before doubting\n"
          "  the instrument; add --sites ...,postcall to see which of the two\n"
          "  calls swallowed the thread.\n")
    elif counts.get("filter"):
        w("  The filter RAN. Its two operands are printed above and they are\n"
          "  the answer: equal means the chain continues into 0x524cc0 and the\n"
          "  fault is downstream (re-run with --sites worker,search,notfound,\n"
          "  create); unequal means 27.2's branch (b), the my-id filter rejects.\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--wait", action="store_true",
                    help="wait for a Gw.exe to appear and attach to it. Start "
                         "this BEFORE the harness so the attach lands well "
                         "before the instance load.")
    ap.add_argument("--seconds", type=float, default=180.0,
                    help="how long to hold the debug loop open")
    ap.add_argument("--max-hits", type=int, default=32,
                    help="per-slot ceiling before the slot is disarmed "
                         "(default 32). RAISE IT for a census site: 32 hits of "
                         "a hot address can all land inside one 4ms burst of a "
                         "single event, which looks like a sample and is not.")
    ap.add_argument("--sites", default=",".join(DEFAULT_SITES),
                    help=f"up to {MAX_SLOTS} of: {', '.join(SITES)}")
    ap.add_argument("--out", default=None, help="also write the report here")
    a = ap.parse_args(argv)

    want = [s.strip() for s in a.sites.split(",") if s.strip()]
    for n in want:
        if n not in SITES:
            raise SystemExit(f"no such site {n!r}; have {', '.join(SITES)}")
    if len(want) > MAX_SLOTS:
        raise SystemExit(f"{len(want)} sites; the processor has {MAX_SLOTS} "
                         f"debug registers. Split the run.")
    sites = [SITES[n] for n in want]

    import commanderpeek
    pid = a.pid
    if pid is None:
        t_end = time.time() + (120 if a.wait else 0)
        while True:
            pids = commanderpeek.find_client_pids()
            if pids:
                if len(pids) > 1:
                    raise SystemExit(
                        f"{len(pids)} clients running {pids}. Refusing to guess "
                        f"which one -- pass --pid. Two clients is how a run "
                        f"measures the wrong process.")
                pid = pids[0]
                break
            if time.time() >= t_end:
                raise SystemExit("no Gw.exe. Start the session, or --wait.")
            time.sleep(0.25)

    print(f"pid {pid}")
    base, checks = verify_sites(pid, sites)
    hwtrap.SLIDE = base - IMAGE_BASE
    print(f"Gw.exe base 0x{base:08X}  (image base 0x{IMAGE_BASE:08X}, "
          f"slide 0x{base - IMAGE_BASE:X})")
    bad = []
    for s, ok, detail in checks:
        mark = {True: "ok  ", False: "BAD ", None: "??  "}[ok]
        print(f"  {mark}{s.name:9} va 0x{s.va:08X}  {detail}")
        if ok is False:
            bad.append(s.name)
    if bad:
        raise SystemExit(
            f"\nREFUSING to arm: {', '.join(bad)} do not hold the instruction "
            f"bytes\nrecorded for them. These addresses were measured on build "
            f"38833; a hardware\nbreakpoint on the wrong build does not error, "
            f"it arms on whatever is there\nand reports it as the chain.")

    reader_h = keytap.open_read(pid)

    def reader(addr, size):
        return keytap.read_handle(reader_h, addr, size)

    def on_hit(trap, hit):
        site = sites[hit["slot"]]
        if site.capture and hit["ctx"] is not None:
            hit["cap"] = site.capture(hit["ctx"], reader)
        # flush: a run of this thing is minutes long and its output is normally
        # redirected, where Python block-buffers and the live progress a watcher
        # wants arrives only at exit.
        print(f"  HIT {site.name} (0x{site.va:08X}) tid {hit['tid']}"
              + (f"  {hit['cap'].get('VERDICT', '')}" if hit.get("cap") else ""),
              flush=True)

    trap = HwTrap(on_hit=on_hit, verbose=True)
    trap.max_hits = a.max_hits
    trap.addrs = [0 if s.kind == "w" else base + (s.va - IMAGE_BASE)
                  for s in sites]
    trap.kinds = [s.kind for s in sites]
    trap.sizes = [s.size for s in sites]
    for i, s in enumerate(sites):
        if s.oneshot:
            trap.oneshot.add(i)
        if s.arm_after:
            if s.arm_after not in want:
                raise SystemExit(
                    f"site {s.name!r} arms after {s.arm_after!r}, which is not "
                    f"in this run's site list -- it would never arm, and a site "
                    f"that never arms reports the same silence as a real "
                    f"negative.")
            trap.deferred[i] = want.index(s.arm_after)
            trap.disarmed.add(i)          # starts down; the trigger raises it
            print(f"  {s.name} is DEFERRED: armed when {s.arm_after} fires"
                  + (", one shot" if s.oneshot else ""))
    trap.attach(pid)
    print(f"attached; armed {len(sites)} execute breakpoints, holding "
          f"{a.seconds:.0f}s", flush=True)
    try:
        trap.pump(a.seconds)
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        trap.detach()
        kernel32.CloseHandle(reader_h)
        print("detached, debug registers cleared")

    counts = _report(sites, trap.hits, base, trap=trap)
    rc = _verdict(counts, sites)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            _report(sites, trap.hits, base, out=fh, trap=trap)
            _verdict(counts, sites, out=fh)
        print(f"\nwritten to {a.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
