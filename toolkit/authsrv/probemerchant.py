"""Merchant window, stock declaration, prices, gold purse, the accumulator drains.

The shop arm of the probe family, lifted verbatim from `probes.py` on
2026-09-11: the stock table and the flags override that is the 2026-08-18 test's
one variable, the `0x00C3` window-kind sweep, the merchant window itself, the
gold purse, the price-scale arm, the two accumulator-drain arms, and the six
registry entries that fire them.

It is leaf shaped by the same rule `probebase.py` is -- standard library plus
`agents` and `probebase` -- and it MUST NOT import `probes`: `probes.py` runs as
`__main__` under `python toolkit/authsrv/probes.py`, so a leaf importing it back
would load a SECOND copy of that module, with its own `PROBES` dict and its own
flags.

`import os` is DUPLICATED here rather than moved. `_WINDOW_KINDS` reads
`RURIK_C3_KINDS` out of `os.environ` at import and is the only `os` user among
the lines that moved, but `probes.py` needs `os` for its own `sys.path.insert`
two lines under its imports -- and `authsrv.py` imports `probes`, so taking `os`
out of there would stop the server at import with a `NameError`.

WHERE THE REFERENTS WENT. `_DRAIN_ITEM_A/B/C` are the three ids the drain arms
declare; they live in `probebase.py` under the 2026-08-27 collision banner that
names them, they are imported here, and `probes.py` still re-exports them
because `test_armour.py` section 2 scores the whole family's `_*_ITEM` band and
reads that band off every `probe*.py` module on disk. Every "below" and "above"
in the comments that travel with this code points INSIDE this file -- they are
step orderings and readings within one arm, not pointers into `probes.py` -- so
none of them is reworded. The one outward reference, `_STOCK_FLAGS`' note that
the override lives here rather than in `content/items.toml`, is as true in this
file as it was in the last one.

`PROBES` here holds only the six merchant entries. `probes.py` opens its own
dict, merges this one in with a duplicate-key raise, and keeps `get`, `names`,
`describe` and `check_encodable` -- so `probes.get("merchant_window", ...)`
answers exactly as it did, and `names()` is still `sorted(PROBES)` and still
returns the same 97 names in the same order. Every name this module binds except
`PROBES` is also re-exported by `probes.py`, at the site it was cut from, so
`vars(probes)` still answers for all of them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, CHAR_CLASS_MONSTER_BASE, HATCHER,
    create_agent, item_template, named_item)
from probebase import (                                     # noqa: E402
    PROBE_DEFINITION, Probe, Step,
    _DRAIN_ITEM_A, _DRAIN_ITEM_B, _DRAIN_ITEM_C)


# THE ONE VARIABLE OF THE 2026-08-18 test. Our content rows carry
# flags = 0x20001006; every one of retail's 14 priced-stock declarations has
# bit 2 CLEAR and bit 0 SET, and bit 2 is SOURCED to gate the item-detail
# fetch (0x00848450: `test cl,4 / jne` skips the call to 0x84be50 when set).
# So a stock item we declare is telling the client "detail already loaded"
# and the client never loads it. This clears bit 2 and sets bit 0 and touches
# NOTHING else -- bits 1 and 12 stay, so whatever they encode is held fixed.
# Overridden here rather than in content/items.toml on purpose: the toml rows
# are measured starter gear with their own provenance, and this is a
# hypothesis, not a correction to them.
_STOCK_FLAGS = 0x20001003
_MERCHANT_NPC_AGENT = 21
# Mirrors authsrv.py: the ONE container this server registers (0x013F).
EQUIPPED_BAG_ID = 1
# THE PURSE IS THE INVENTORY KEY, NOT A BAG -- and this name was wrong even
# though the number was right. `0x0140 [1, 500]` funded the shop and the code
# said `EQUIPPED_BAG_ID`, which is a bag id that happens to also be 1 on this
# server. The corpus separates them: on three live connections `0x0140` named
# **4 / 159 / 183**, which are the `0x0144 ITEM_STREAM_CREATE` keys, while the
# bag ids on those same connections were 8..16, 474.., and 570.. -- two
# different namespaces that only collide here because we allocate 1 in both.
# studies/newopcodes/FINDINGS.md, the merchant-capture section.
PLAYER_INVENTORY = 1


# Prices for the stock arm. OUR OWN numbers, deliberately not retail's table --
# nothing here needs to match a real shop, and three DISTINCT round values make
# the readout unambiguous: each row's price identifies which row it came from.
# content/items.toml carries value = 0 on every row (correct for starter gear,
# and what put "0" in every price column of the 20260818T211036 panel), so the
# price is overridden here rather than written into the content rows.
#
# ELEVEN ROWS, and the count is the experiment rather than a garnish. Every
# merchant window in the live corpus -- 6 of 6, three connections, two
# different shopkeepers with entirely different stock -- stages exactly ELEVEN
# ids and is followed by `0x00C3 [11, 0]`. This project has sent `0x00C3` three
# times and never once with retail's own shape behind it (3 staged / field 3,
# 3 staged / field 40, both dead). This restores the shape.
#
# The panel renders TWICE the declared value (measured `20260819T140723`:
# 25 / 50 / 100 went up as 50 / 100 / 200), so these show as 10, 20, ... 110 --
# eleven distinct quotes, so the gold a purchase debits names the row it bought.
# content/items.toml carries value = 0 on every row (correct for starter gear),
# so the price is overridden here and not written back into the content rows.
_STOCK_TEMPLATES = ("warrior_legs", "warrior_boots", "warrior_gloves",
                    "warrior_body", "warrior_head")
_STOCK_FIRST_ID = 40
_STOCK_COUNT = 11
_STOCK = tuple((_STOCK_FIRST_ID + i,
                _STOCK_TEMPLATES[i % len(_STOCK_TEMPLATES)],
                5 * (i + 1))
               for i in range(_STOCK_COUNT))


def _stock_item(key, value):
    """A content item re-declared as merchant stock: a real per-item price.

    THE FLAGS OVERRIDE IS OFF, and the reason is measured rather than argued.
    `_STOCK_FLAGS` clears F8 bit 2 to match retail, and bit 2 is SOURCED to gate
    the client's item-detail fetch. Run `20260818T233955` shows what that costs
    us: with bit 2 cleared the client DOES request detail, this server never
    answers, and all three rows render as **hourglass placeholders that never
    resolve** -- still hourglasses 35 s after the shop opened. With the content
    row's own flags (bit 2 SET, "detail already present") the same three items
    render their real armour icons (`20260818T211036`). So retail's bit pattern
    is only correct for a server that implements the detail response, and ours
    does not. The override also did NOT fix the `0x00C3` crash, which was its
    whole reason for existing -- so it buys nothing and costs the icons.
    Kept as a named constant so the next arm can switch it on deliberately.
    """
    row = dict(item_template(key))
    row["value"] = value
    return row


# The 0x00C3 field-1 values to sweep. 11 is the merchant (Buy/Sell tabs,
# OBSERVED 20260819T173300) and is included as the run's POSITIVE CONTROL --
# without it, a run where every arm draws nothing is indistinguishable from a
# run where the rig is broken.
#
# WIKI (GWW, "NPC service", rev. 2026) lists the services a Guild Wars NPC can
# offer, and the ones that plausibly need a window of their own are: Merchant,
# the six Traders (dye, material, rare material, rare scroll, rune, sigil),
# Collector, the Crafters (armorer, weaponsmith, artisan, consumable), Skill
# trainer, Xunlai storage, Guild registrar/Emblemer, Map travel, Mercenary
# registrar, Profession changer, Pet tamer. That is ~16 kinds, which is why
# this sweep runs 0..15 -- a range chosen from the game's own service list
# rather than from a guess about the enum's width.
#
# ONE UNKNOWN PER RUN IS THE REAL COST, learned by getting it wrong: the first
# sweep queued sixteen arms and the client died on the SECOND (kind 0,
# `Assertion: item` ItCliApi.cpp(859), site 0x00845B8D -- an item-detail
# accessor whose neighbours assert `item->IsDetailHigh()`). The remaining
# fourteen arms went to a corpse and the log looked exactly like sixteen
# successful sends. The capture is what caught it: the client's last c2s was at
# t=38.1 and arms three onward were all sent after that. So an invalid kind
# ENDS the run, a sweep advances only as far as its first fatal value, and any
# run must be read against the client's last c2s rather than against the send
# log.
#
# RESUMABLE: set RURIK_C3_KINDS to the ascending list still to test. The
# control is prepended automatically and is not optional.
_WINDOW_KIND_CONTROL = 11
_WINDOW_KINDS = tuple(
    [_WINDOW_KIND_CONTROL]
    + [int(x) for x in os.environ.get("RURIK_C3_KINDS", "1,2,3,4,5").split(",")
       if x.strip()])


def _shop_window_kinds_steps(agent_id, origin):
    """What ELSE can `0x00C3` field 1 make the merchant window into?

    `0x00C3 [11, 0]` adds a **Buy/Sell tab pair** to the panel `0x00CA` opens
    (`20260819T173300`), so field 1 is a transaction KIND rather than a count,
    and 11 is the same constant the client sends on `0x004A` and receives back
    on `0x00CC`. This sweeps the rest of the small integers to see which other
    windows the client already knows how to draw.

    EACH ARM RE-ARMS, and that is not optional: `0x00C3` and `0x00CA` are two of
    the eight readers that consume-and-clear the owner register `0x00C4` writes,
    so an arm that skipped `0x00C4` would test a cleared register instead of a
    kind.

    HOW TO READ IT -- the readout is the TAB STRIP and the instruction line,
    both fixed-position UI:

      * a different tab set, or a differently-worded instruction, is a distinct
        window kind and names itself on screen (the merchant's reads
        *"Select an item from my list below, then press \"Buy.\""*);
      * an unchanged buy-only panel means the kind is inert or unimplemented;
      * a crash names the kind that did it, with the arm bracketed in the log.

    A DEATH TRUNCATES THE RUN, so 11 goes FIRST as the positive control and the
    unknowns follow in ascending order: whatever the client does with kind k,
    every arm before it has already been photographed. Two prior `0x00C3`
    deaths were at 3 and 40 -- but both were sent over a THREE-item list by a
    client with no bags and no funds, so they are not evidence about the kind.
    """
    ox, oy, plane = origin
    h = HATCHER
    a = _MERCHANT_NPC_AGENT
    ids = [i for i, _k, _v in _STOCK]
    steps = [
        Step(2.0, 0x0140, [PLAYER_INVENTORY, 2000],
             f"0x0140 [inventory {PLAYER_INVENTORY}, +2000] -- fund the player",
             "'Your Funds' reads 2000 on every window that shows funds."),
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(2.0, 0x0020,
             create_agent(a, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                          AGENT_KIND_NPC, ox + 250, oy, plane,
                          allegiance=0x706C6179),
             f"create the shopkeeper: agent {a}", "a Hatcher stands there."),
    ]
    steps += [
        Step(3.0 if n == 0 else 0.6, 0x0161,
             named_item(item_id, _stock_item(key, value)),
             f"0x0161: declare stock {item_id} ({key}), value {value}",
             "nothing -- declarations are quiet.")
        for n, (item_id, key, value) in enumerate(_STOCK)]
    for n, kind in enumerate(_WINDOW_KINDS):
        note = (" -- POSITIVE CONTROL, known to draw Buy/Sell tabs"
                if kind == 11 else "")
        steps += [
            Step(2.0, 0x00C4, [a],
                 f"ARM {n + 1}/{len(_WINDOW_KINDS)}: re-arm the owner register",
                 "the character turns to face the NPC; the previous panel may "
                 "close."),
            Step(0.5, 0x0084, [ids],
                 f"stage {len(ids)} stock ids", "nothing."),
            Step(0.5, 0x00CA, [1, 0x3F800000],
                 "0x00CA [1, 1.0f] -- open the base panel",
                 "a buy-only panel, the same on every arm. This is the "
                 "BASELINE each 0x00C3 below is read against."),
            # TEN SECONDS, and the number is the attribution rule rather than
            # padding. The client keep-alives every ~5 s, so a kind that does
            # NOT kill it is followed by at least two c2s messages; a kind that
            # does is followed by none. At the 4 s spacing this probe shipped
            # with, a fatal arm and the arm after it both landed inside one
            # keep-alive period and the capture could not say which was which.
            Step(10.0, 0x00C3, [kind, 0],
                 f"0x00C3 [{kind}, 0]{note}",
                 f"THE ARM. Kind {kind}: does the tab strip change, does the "
                 f"instruction line change, or is the panel identical to the "
                 f"0x00CA baseline three seconds ago?"),
        ]
    steps.append(
        Step(10.0, 0x0000, [],
             "END: quiet frames after the last arm",
             "the final panel state, and whether the client is still alive.",
             sends=False))
    return steps


def _merchant_window_steps(agent_id, origin):
    """Two questions in one run, the client-killer last.

    Q1 -- CAN THE PLAYER BUY? `20260819T140723` built a complete, funded,
    correctly-priced shop on our own NPC and the operator watched a Buy click
    land and produce **zero** c2s traffic. The operator then pressed I and
    found the cause: **no backpack**. The client refuses a purchase it has
    nowhere to put, and refuses it LOCALLY, so the null cost no wire message
    and looked exactly like a missed click. Retail sends all nine bags during
    LOAD, right after `0x0144`, so they moved into the login burst
    (`authsrv.PLAYER_BAGS`) -- this probe no longer sends `0x013F` at all, and
    a 20-slot grid under `I` is the login burst's acceptance test rather than
    one of these steps. What this probe wants is `GAME_CMSG 0x4D`, which would
    be the first purchase request this project has ever RECEIVED rather than
    watched somebody else receive.

    Q2 -- WHAT IS `0x00C3` FIELD 1? A row this arc created and left CONTESTED.
    Three readings were live: an item id (ours, from the crashes), the COUNT of
    staged items, or a TYPE constant. **The corpus killed the first one**: the
    field is 11 on six windows across three connections, and item ids on those
    same connections are per-connection handles that vary wildly (the bag ids
    alone drew 8..16 on one and 570/496/398.. on another), so a constant 11 is
    not a handle. The corpus cannot separate the other two, because all six
    windows staged exactly eleven items -- count and type predict the same
    number every time.

    So this run does the thing nobody has done: **send retail's own shape**.
    Eleven items staged, `0x00C3 [11, 0]`, in retail's exact order
    (`0x00C4` -> `0x0084` -> `0x00CA` -> `0x00C3`, back to back). Every prior
    attempt sent 3 or 40 over a 3-item list.

      * If it SURVIVES, both survivors stay alive and one more run separates
        them (5 staged with `[11,0]` against 5 staged with `[5,0]`). It also
        retires "0x00C3 is not authorable by a server".
      * If it DIES on the same `c0000005`, that is an answer too, and a
        stronger one: with retail's own count, retail's own order, a funded
        purse and a working shop behind it, no field we send is the problem --
        the earlier disassembly stands (the message reaches the WRONG
        SUBSCRIBER, which reads a fifth dword and calls the stack cookie),
        field 1 carries nothing recoverable from the wire, and the CONTESTED
        row closes as "unknowable from this side" instead of sitting open.

    THE SHOP IS OPENED TWICE ON PURPOSE. `0x00CA` alone opens it (measured
    twice), so opening 1 carries the Buy test with `0x00C3` withheld and banks
    everything valuable; opening 2 replays retail's four-message burst with
    `0x00C3` restored. Re-arming is proven (`20260818T234622`, three arms,
    three windows), and this ordering means a death on Q2 cannot cost Q1.

    THE BUILT-IN CONTROL, unchanged and still the reason a null is readable:
    `0x00C4`'s handler is SOURCED to call `0x00817950`, which fetches both
    agents' positions and TURNS THE PLAYER TO FACE the named agent. A run where
    nothing opens AND the character never turns is a delivery failure, not a
    null.

    `0x00C5` is deliberately never sent: it asserts
    `accumIntList[0].Count() >= 1` at `ChCliApi.cpp:2956` and composes a string
    embedding an item name we cannot build. The `0x00E1` drain tail that used
    to hang off this probe is gone -- that question closed, the drain being as
    quiet with a merchant window open as with none.
    """
    ox, oy, plane = origin
    h = HATCHER
    a = _MERCHANT_NPC_AGENT
    ids = [i for i, _k, _v in _STOCK]
    declarations = [
        Step(3.0 if n == 0 else 0.6, 0x0161,
             named_item(item_id, _stock_item(key, value)),
             f"0x0161: declare stock {item_id} ({key}), value {value} "
             f"-> quoted {value * 2}",
             "nothing -- declarations are quiet." if n == 0 else "nothing.")
        for n, (item_id, key, value) in enumerate(_STOCK)]
    return [
        Step(2.0, 0x0140, [PLAYER_INVENTORY, 2000],
             f"0x0140 [inventory {PLAYER_INVENTORY}, +2000] -- FUND THE PLAYER",
             "'Your Funds' reads 2000 when the shop opens, and the inventory "
             "window's own gold field agrees (both measured at 500 in "
             "20260819T140723). 2000 covers every quote on the list, so a "
             "refusal to buy cannot be blamed on funds. 0x0140's setter is "
             "`add [ecx+0x90], eax` -- it CREDITS, and its field 1 is the "
             "INVENTORY key, not a bag id."),
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(2.0, 0x0020,
             create_agent(a, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                          AGENT_KIND_NPC, ox + 250, oy, plane,
                          allegiance=0x706C6179),
             f"create the shopkeeper: agent {a}, 250u to the side, 'play' token",
             "a Hatcher stands there, green. A body, not yet a merchant."),
    ] + declarations + [
        Step(4.0, 0x00C4, [a],
             f"OPENING 1 -- 0x00C4 WINDOW_OWNER = agent {a}",
             "THE CONTROL: the character should TURN TO FACE the NPC. If it "
             "turns, the owner register was written even if no window draws."),
        Step(1.0, 0x0084, [ids],
             f"0x0084: stage all {len(ids)} stock ids into accumIntList[0]",
             "nothing -- the appender is QUIET, measured twice."),
        Step(1.0, 0x00CA, [1, 0x3F800000],
             "0x00CA [1, 1.0f] -- THE SHOP OPENER (0x00C3 WITHHELD here)",
             f"a panel titled 'Hatcher [Collector]' listing {len(ids)} rows "
             f"quoted 10, 20 ... {len(ids) * 10}, 'Your Funds: 2000', and Buy "
             f"ENABLED. This is the Q1 arm and it must not be risked, so the "
             f"message that has killed the client three times is withheld "
             f"until opening 2."),
        Step(2.0, 0x00C3, [_STOCK_COUNT, 0],
             f"0x00C3 [{_STOCK_COUNT}, 0] in OPENING 1 -- the sell-capability test",
             "THE COUNT-VS-TYPE DISCRIMINATOR, from a direction that does not "
             "need a crash. 20260819T172944 opened this window with 0x00CA "
             "alone, bought twice, and could NOT sell: clicking a backpack item "
             "resolved its tooltip and the panel stayed 'press Buy' with no "
             "Sell control and no 0x004A on the wire. The one message retail "
             "sends that we withheld from that window is this one, and its "
             "field 1 is 11 -- which is ALSO the sell transaction kind on "
             "0x004A and 0x00CC, 8 of 8. ANSWERED 20260819T173300: a Buy/Sell "
             "TAB PAIR appears. Field 1 is a TRANSACTION KIND, the count "
             "reading is dead, and the upstream name WINDOW_MERCHANT is "
             "earned -- 0x00CA opens a buy-only panel and this is what makes "
             "it a merchant. The round trip then closed (20260819T173604): "
             "buy at 10, sell back at 5, funds 2000 -> 1990 -> 1995 on screen.",
             ),
        Step(28.0, 0x0000, [],
             "THE BUY/SELL WINDOW: click a row, Buy, then try to sell",
             "THE QUESTION OF THIS RUN. With bags now created during LOAD, a "
             "click on Buy should put GAME_CMSG 0x4D on the wire -- the first "
             "purchase request this project has ever received. Retail's own "
             "is 0x4D [1, 40, [], b'', 0, [item], b'\\x01']: quantity 1, "
             "price 40, one item id. Watch the gamesrv log for a c2s 0x004D, "
             "and watch the funds line fall by the quoted price -- the client "
             "debits ITSELF, measured on retail, where no server message "
             "carries the debit. Silence here means the backpack was not the "
             "whole story.", sends=False),
        Step(4.0, 0x00C4, [a],
             f"OPENING 2 -- re-arm the owner register on agent {a}",
             "the panel may close and reopen; re-arming three times in one "
             "session is proven (20260818T234622). From here the four "
             "messages go out back-to-back, in retail's order."),
        Step(0.5, 0x0084, [ids],
             f"restage all {len(ids)} ids -- every reader drains this buffer",
             "nothing."),
        Step(0.5, 0x00CA, [1, 0x3F800000],
             "0x00CA [1, 1.0f] -- reopen", "the shop opens again."),
        Step(3.0, 0x00C3, [_STOCK_COUNT, 0],
             f"0x00C3 [{_STOCK_COUNT}, 0] -- RETAIL'S OWN SHAPE, never tried",
             "THE Q2 TEST, and both outcomes are answers. SURVIVES: the count "
             "and type readings both live, one more run separates them, and "
             "'0x00C3 is not authorable by a server' is retired. DIES on the "
             "same c0000005 writing 0x2e67736d: with retail's count, retail's "
             "order and a working shop behind it, nothing we send is the "
             "problem -- the wrong-subscriber disassembly stands and field 1 "
             "is unknowable from the wire. Prior deaths: [3,0] -> "
             "`Assertion: item` ItCliApi.cpp(859); [40,0] -> c0000005. Both "
             "were 3 staged."),
        Step(12.0, 0x0000, [],
             "END: quiet frames so the last send has coverage after it",
             "the run's final state. Note whether the character is still "
             "facing the NPC, and whether the panel survived.", sends=False),
    ]


def _gold_purse_steps(agent_id, origin):
    """Which purse does the shop's `Your Funds` read, and what does `0x0141`
    field 1 select?

    THE ERROR THIS EXISTS TO FIX. `20260818T235758` sent `0x0141 [1, 500]` to
    fund a purchase, `Your Funds` stayed **0**, Buy stayed greyed, and the run
    re-measured the unfunded case. The `1` was copied from the login burst's own
    `send(GAME_SMSG_UPDATE_GOLD_STORAGE, [1, 0])` without anyone testing what it
    selects -- and the opcode is named `UPDATE_GOLD_**STORAGE**`, while Guild
    Wars separates carried gold from Xunlai storage. So `[1, N]` is measured NOT
    to feed the merchant's purse, and this varies the selector.

    THE ARMS. Distinct amounts, so the number on screen names the arm that
    produced it -- no arm can be credited with another's effect:

        A  field1 = 0   amount 111
        B  field1 = 2   amount 222
        C  field1 = 1   amount 333   <- the control: the value already REFUTED
                                        at 500, re-sent at a different amount
                                        so "wrong selector" and "wrong amount"
                                        cannot be confused

    Each arm re-opens the shop (`0x00C4` -> `0x0084` -> `0x00CA`), because the
    funds line is drawn when the panel is built and nothing here knows whether
    it re-renders in place. Re-arming is proven to work (`20260818T234622`,
    three arms, three windows).

    READING IT. `Your Funds` showing 111 / 222 / 333 identifies the selector
    outright. **All three staying 0 is the informative negative**: it would mean
    `0x0141` does not drive this display at all and the merchant's purse is fed
    by something else -- and there is already a suspect, since the login burst
    also sends `CHARACTER_UPDATE_INFO ["", 0, 0, 1000, 0, 0, 0]`, whose `1000`
    nobody has ever explained. That would be the next arm, not this one.
    """
    ox, oy, plane = origin
    h = HATCHER
    a = _MERCHANT_NPC_AGENT
    ids = [_DRAIN_ITEM_A, _DRAIN_ITEM_B, _DRAIN_ITEM_C]
    steps = [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(2.0, 0x0020,
             create_agent(a, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                          AGENT_KIND_NPC, ox + 250, oy, plane,
                          allegiance=0x706C6179),
             f"create the shopkeeper: agent {a}", "a Hatcher stands there."),
        Step(4.0, 0x0161, named_item(_DRAIN_ITEM_A, _stock_item("warrior_legs", 25)),
             "0x0161: leggings, value 25 (quotes at 50)", "nothing."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_B, _stock_item("warrior_boots", 50)),
             "0x0161: boots, value 50 (quotes at 100)", "nothing."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_C, _stock_item("warrior_gloves", 100)),
             "0x0161: gauntlets, value 100 (quotes at 200)", "nothing."),
    ]
    # field1 = 0 IS A CLIENT-KILLER: `Assertion: inventory`,
    # ItCliApi.cpp(1969), same-second attribution, run 20260819T002038. It took
    # arms B and C down with it (the probe sends on a timer, so the rest of that
    # run went into a dead client). Field 1 names a CONTAINER that must exist,
    # so 0 is refused by the client, not merely ignored. Arms start at 2.
    for tag, f1, amount in (("A", 2, 222), ("B", 3, 333), ("C", 1, 444)):
        note = (" -- the CONTROL: this selector is already refuted at 500, so a "
                "change here would mean the amount mattered, not the selector"
                if f1 == 1 else "")
        steps += [
            Step(8.0, 0x0141, [f1, amount],
                 f"ARM {tag}: 0x0141 [field1={f1}, {amount}]{note}",
                 "nothing yet -- the shop below is what renders the number."),
            Step(2.0, 0x00C4, [a],
                 f"ARM {tag}: re-arm the window owner",
                 "the character turns to face the NPC."),
            Step(1.0, 0x0084, [ids], f"ARM {tag}: restage the ids", "nothing."),
            Step(2.0, 0x00CA, [1, 0x3F800000],
                 f"ARM {tag}: open the shop and READ 'Your Funds'",
                 f"THE READOUT, one line only: `Your Funds: {amount}` means "
                 f"field 1 = {f1} is the merchant's purse. Still 0 means this "
                 f"selector is not it. Prices stay 50/100/200 either way -- if "
                 f"THOSE move, something is wrong with the run, not the purse."),
        ]
    steps.append(
        Step(10.0, 0x0000, [],
             "END: quiet frames so arm C has coverage after it",
             "if all three read 0, 0x0141 does not feed this display and the "
             "next suspect is CHARACTER_UPDATE_INFO's unexplained 1000.",
             sends=False))
    return steps


def _shop_price_scale_steps(agent_id, origin):
    """Is `0x00CA`'s second field a PRICE MULTIPLIER, or is the 2x a fixed
    client markup? The one question the priced-stock run could not answer.

    WHAT IS ALREADY MEASURED (`20260818T233955`): with `F9` = 25 / 50 / 100 the
    shop quoted **50 / 100 / 200** -- exactly 2x, on three distinct values. The
    second field carried `0x3F800000` (1.0f) in that run because retail sends
    1.0f, so a multiplier of 1.0 and a fixed 2x markup predict the SAME numbers
    and nothing separates them. This varies the field and only the field.

    THE ARMS, and their predictions, on record before the run:

        A  1.0f  0x3F800000   control, must reproduce 50 / 100 / 200
        B  2.0f  0x40000000   multiplier -> 100 / 200 / 400
        C  0.5f  0x3F000000   multiplier -> 25 / 50 / 100  (== what we SENT)

    Arm C is the sharp one: if the field scales, C's prices collapse onto the
    raw `F9` values, which is a shape change no rounding can fake. If all three
    arms read 50 / 100 / 200, the field is INERT for price and the 2x belongs to
    the client's own merchant markup -- also a real answer.

    WHY EACH ARM RE-SENDS `0x00C4` AND `0x0084`: `0x00CA` is one of the eight
    readers that CONSUME the window-owner register and then write
    `[0x010876CC] = 0` (this document's `0x00C4` section). A second `0x00CA`
    with the register cleared is a different experiment from the first, so each
    arm re-arms the owner and restages the id list. If arms B and C draw
    nothing at all, THAT is the finding -- the register is single-shot and the
    price question needs a fresh window per value.

    Items are declared ONCE, with the content rows' own flags (bit 2 set): the
    `_STOCK_FLAGS` override is off because clearing bit 2 makes every row an
    hourglass placeholder this server never resolves (same run, above).
    """
    ox, oy, plane = origin
    h = HATCHER
    a = _MERCHANT_NPC_AGENT
    ids = [_DRAIN_ITEM_A, _DRAIN_ITEM_B, _DRAIN_ITEM_C]
    steps = [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(2.0, 0x0020,
             create_agent(a, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                          AGENT_KIND_NPC, ox + 250, oy, plane,
                          allegiance=0x706C6179),
             f"create the shopkeeper: agent {a}", "a Hatcher stands there."),
        Step(4.0, 0x0161, named_item(_DRAIN_ITEM_A, _stock_item("warrior_legs", 25)),
             "0x0161: leggings, value 25", "nothing."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_B, _stock_item("warrior_boots", 50)),
             "0x0161: boots, value 50", "nothing."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_C, _stock_item("warrior_gloves", 100)),
             "0x0161: gauntlets, value 100", "nothing."),
    ]
    arms = [("A", 0x3F800000, "1.0f", "50 / 100 / 200 -- the CONTROL; if this "
             "arm does not reproduce the measured prices, stop and read no "
             "other arm as a verdict"),
            ("B", 0x40000000, "2.0f", "100 / 200 / 400 if the field is a "
             "multiplier; 50 / 100 / 200 if it is inert"),
            ("C", 0x3F000000, "0.5f", "25 / 50 / 100 if the field is a "
             "multiplier -- prices collapsing onto the RAW values we sent is "
             "the unmistakable shape; 50 / 100 / 200 if inert")]
    for tag, bits, label, expect in arms:
        steps += [
            Step(8.0, 0x00C4, [a],
                 f"ARM {tag}: re-arm 0x00C4 (the owner register is consumed by "
                 f"each 0x00CA)",
                 "the character turns to face the NPC -- the control that "
                 "proves the register was written."),
            Step(2.0, 0x0084, [ids],
                 f"ARM {tag}: restage the three ids", "nothing."),
            Step(2.0, 0x00CA, [1, bits],
                 f"ARM {tag}: 0x00CA [1, {label}]  (0x{bits:08X})",
                 f"THE READOUT: expect {expect}. Read the PRICE COLUMN, not "
                 f"the item names."),
        ]
    steps.append(
        Step(10.0, 0x0000, [],
             "END: quiet frames so arm C has coverage after it",
             "compare the three price columns. If B and C never drew a window, "
             "say so -- that is the single-shot answer, not a null.",
             sends=False))
    return steps


def _accum_drain_e1_steps(agent_id):
    """`0x00E1` with real ids staged, THREE times -- the arm nobody photographed.

    WHY THIS EXISTS. `accum_drains` (harness 20260818T171920) measured three of
    its four drains QUIET and never observed the fourth: the client left the OS
    foreground for ~23 s and `shot_if_foreground` correctly declined to
    photograph whatever was in front, so the ten frames spanning `0x00E1` do
    not exist. An unmeasured arm and a quiet arm look identical in a summary,
    which is the whole reason this is a separate run rather than a footnote.
    `0x00E1` is also the one worth the launch: upstream calls it
    `SKILL_ADD_TO_WINDOWS_END`, and its worker (`0x00814860`) reads BOTH accum
    lists and zeroes both counts, so an upstream name pointing at the skill
    list is testable against a buffer we filled with ITEM ids.

    THE FIX IS REPETITION, NOT A HARNESS CHANGE. Three identical arms, ~11 s
    apart, each restaging both columns before draining. Frame coverage is the
    failure mode, so three widely-spaced chances beat one; and since each drain
    zeroes both counts, the arms are independent by construction rather than by
    assumption. It also buys a reproducibility check the single-shot design
    could not give: three sends, three verdicts, and a disagreement among them
    would be worth more than any of them.

    Deliberately NOT done: forcing the client to the foreground before each
    shot. That guard exists because a run once photographed an unrelated
    window, and weakening a safety check to make an experiment convenient is
    the wrong trade -- especially in shared harness code other sessions run.

    READING THE RESULT. The stated null stands from the prior run: the only
    observed reader of this buffer (the `0x00C5` flow) rides a window context
    and this run opens none, so QUIET refutes nothing about the opcode -- it
    bounds what a bare drain does with no window open. What WOULD be new: any
    surface gaining three rows, or anything skill-flavoured, which is the half
    of upstream's name this run can actually address.

    ARTIFACT WARNING, earned the hard way. The prior run's one non-zero frame
    was a **skill tooltip** raised by the mouse resting over the skill bar, not
    a drain effect -- 7,172 changed pixels landing exactly on a send. Score the
    bottom HUD strip separately and crop before believing any spike.
    """
    ids = [_DRAIN_ITEM_A, _DRAIN_ITEM_B, _DRAIN_ITEM_C]
    steps = [
        Step(4.0, 0x0161, named_item(_DRAIN_ITEM_A,
                                     item_template("warrior_legs")),
             "0x0161: declare item 40 (leggings name)",
             "nothing -- declarations render nothing, 621/621."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_B,
                                     item_template("warrior_boots")),
             "0x0161: declare item 41 (boots name)", "nothing."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_C,
                                     item_template("warrior_gloves")),
             "0x0161: declare item 42 (gloves name)", "nothing."),
    ]
    for rep in (1, 2, 3):
        steps += [
            Step(8.0, 0x0084, [ids],
                 f"rep {rep}/3: 0x0084 stages column 0 with the three item ids",
                 "nothing -- the appender is QUIET, measured."),
            Step(1.0, 0x00D8, [[1, 1, 1]],
                 f"rep {rep}/3: 0x00D8 stages column 1 = [1,1,1], equal length",
                 "nothing -- list 1's appender was QUIET too."),
            Step(2.0, 0x00E1,  [0],
                 f"rep {rep}/3: 0x00E1 DRAIN, event 0x100000BA "
                 f"(upstream: SKILL_ADD_TO_WINDOWS_END)",
                 "THE VERDICT FRAME for this rep. Any window, list, toast or "
                 "chat line gaining three rows named like armor pieces -- or "
                 "anything on a SKILL surface, which is what upstream's name "
                 "predicts. Ignore the bottom HUD strip unless the change "
                 "survives cropping: a resting mouse raises a skill tooltip "
                 "there and it already faked one hit."),
        ]
    steps.append(
        Step(10.0, 0x0000, [],
             "END: quiet frames, so the last drain has coverage after it too",
             "nothing new. If all three reps agree, that is the answer; if "
             "they disagree, THAT is the finding and this run is n=3.",
             sends=False))
    return steps


def _accum_drains_steps(agent_id):
    """Which UI surface does each accum-table DRAIN event drive, with real ids
    staged? The redesign of studies/newopcodes/FINDINGS.md section-4 item 7,
    after the desk read that item asked for came back and changed it.

    WHAT THE DESK READ SETTLED FIRST (2026-08-18, all four drain workers
    disassembled, the load-bearing one re-verified by hand): the ladder's
    proposed experiment -- '0x0084 then 0x0086; separately 0x00D7 then 0x00E1;
    see which surface receives each' -- had two false premises. (1) The
    appenders CANNOT be separated by any experiment: 0x0084 and 0x00D7 share
    one handler VA (0x0091E820) and one worker appending into the same list;
    the client never sees which opcode it was. This probe deliberately uses
    only 0x0084. (2) The drains do not pair off one-per-list: 0x0085 (worker
    0x008119C0, event 0x100000B8) drains list 0 ONLY and zeroes only count 0;
    0x00D4 (0x008145C0, event 0x10000052) and 0x00E1 (0x00814860, event
    0x100000BA) read both lists and zero both counts; and 0x0086 (0x00811A00,
    event 0x100000B9) ASSERTS the two counts EQUAL --
    `context->accumIntList[0].Count() == context->accumIntList[1].Count()`,
    ChCliApi.cpp(1587) -- then posts ONE count with BOTH base pointers: its
    consumer reads the two lists as parallel COLUMNS of one table. So the
    ladder's 0x0086 arm as written would have crashed (3 != 0), and the only
    reason the 2026-08-13 screen pass survived 0x0086 is that empty == empty
    passes the assert.

    WHAT IS LEFT TO MEASURE is which surface each drain EVENT drives when the
    buffer holds real, declared, distinctly-named item ids -- the screen pass
    proved every drain QUIET on an EMPTY buffer, which measured the events
    subscriber-side only at zero rows. Three items with three different names
    (legs/boots/gloves) so whichever surface renders says WHICH rows reached
    it. Every multi-list arm stages column 1 with [1, 1, 1] -- equal length by
    construction, value 1 because the column's meaning (quantity? id?) is
    exactly what the render would reveal. The 0x0086 arm runs LAST: it is the
    only assert-carrying drain, so if the run dies there the frames from the
    first three arms are already banked.

    KNOWN CONFOUND, stated up front: a null result refutes nothing. The
    subscribers may exist only while some window is open (retail's only
    staged-buffer use observed, the 0x00C5 flow, rides a window context), and
    this run opens none. Nothing-lights is 'no subscriber in this state', not
    'the events are dead'.
    """
    ids = [_DRAIN_ITEM_A, _DRAIN_ITEM_B, _DRAIN_ITEM_C]
    return [
        Step(4.0, 0x0161, named_item(_DRAIN_ITEM_A,
                                     item_template("warrior_legs")),
             "0x0161: declare item 40 (leggings name)",
             "nothing -- a declaration renders nothing, measured 621/621."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_B,
                                     item_template("warrior_boots")),
             "0x0161: declare item 41 (boots name)", "nothing."),
        Step(1.0, 0x0161, named_item(_DRAIN_ITEM_C,
                                     item_template("warrior_gloves")),
             "0x0161: declare item 42 (gloves name)", "nothing."),
        Step(8.0, 0x0084, [ids],
             "0x0084: stage column 0 with the three item ids",
             "nothing -- the appender is QUIET, measured; the drain is the "
             "experiment."),
        Step(2.0, 0x0085, [0],
             "0x0085: DRAIN, event 0x100000B8 -- the only single-list drain",
             "ARM 1's verdict frame. Any window, toast, chat line or list "
             "gaining three rows named like armor pieces. Nothing is also an "
             "answer (no subscriber in this state)."),
        Step(10.0, 0x0084, [ids],
             "0x0084: restage column 0", "nothing."),
        Step(1.0, 0x00D8, [[1, 1, 1]],
             "0x00D8: stage column 1 = [1,1,1], equal length",
             "nothing -- list 1's appender was QUIET too."),
        Step(2.0, 0x00D4, [],
             "0x00D4: DRAIN, event 0x10000052 (bare trigger, no payload field)",
             "ARM 2's verdict frame, same watch as arm 1."),
        Step(10.0, 0x0084, [ids],
             "0x0084: restage column 0", "nothing."),
        Step(1.0, 0x00D8, [[1, 1, 1]],
             "0x00D8: restage column 1", "nothing."),
        Step(2.0, 0x00E1, [0],
             "0x00E1: DRAIN, event 0x100000BA -- upstream calls this "
             "SKILL_ADD_TO_WINDOWS_END",
             "ARM 3's verdict frame. If upstream's name is honest, a SKILL "
             "surface moves here -- and column 1 is all 1s, so 'skill id 1' "
             "appearing would also name which column that surface reads."),
        Step(10.0, 0x0084, [ids],
             "0x0084: restage column 0", "nothing."),
        Step(1.0, 0x00D8, [[1, 1, 1]],
             "0x00D8: restage column 1 -- 3 == 3, the assert passes by "
             "construction", "nothing."),
        Step(2.0, 0x0086, [0],
             "0x0086: DRAIN, event 0x100000B9 -- the assert-carrying, "
             "paired-columns drain, deliberately LAST",
             "ARM 4's verdict frame. A crash naming ChCliApi.cpp(1587) here "
             "means the count bookkeeping differs from the disassembly's "
             "reading and is itself a finding; the first three arms are "
             "already on disk either way."),
    ]


PROBES = {
    "gold_purse": lambda a, o: Probe(
        question="Which purse does the shop's 'Your Funds' read, and what does "
                 "0x0141 field 1 select?",
        predicts="Three arms with DISTINCT amounts so the number names its own "
                 "arm: field1=0 -> 111, field1=2 -> 222, field1=1 -> 333 (the "
                 "control, already refuted at 500). Whichever amount appears "
                 "identifies the selector. All three staying 0 is the "
                 "informative negative -- 0x0141 would not drive this display "
                 "at all, and the next suspect is CHARACTER_UPDATE_INFO's "
                 "unexplained 1000 in the login burst.",
        steps=_gold_purse_steps(a, o),
        note="Fixes a measured mistake rather than opening new ground: "
             "20260818T235758 sent 0x0141 [1, 500], Your Funds stayed 0, Buy "
             "stayed greyed, and the run re-measured the unfunded case. The 1 "
             "was copied from the login burst without testing what it selects, "
             "and the opcode is UPDATE_GOLD_STORAGE while GW separates carried "
             "gold from Xunlai storage. Each arm re-opens the shop because the "
             "funds line is drawn when the panel is built; re-arming is proven "
             "(20260818T234622). Buy is NOT clicked here -- one question.",
    ),
    "shop_price_scale": lambda a, o: Probe(
        question="Is 0x00CA's second field a price multiplier, or is the "
                 "measured 2x a fixed client markup?",
        predicts="Three arms at 1.0f / 2.0f / 0.5f against items valued "
                 "25/50/100. If the field scales price: 50/100/200, then "
                 "100/200/400, then 25/50/100 -- arm C collapsing onto the raw "
                 "values is a shape change no rounding can fake. If all three "
                 "read 50/100/200 the field is inert for price and the 2x is "
                 "the client's own merchant markup. Arm A is the control and "
                 "must reproduce 20260818T233955's numbers.",
        steps=_shop_price_scale_steps(a, o),
        note="Each arm re-sends 0x00C4 and 0x0084 because 0x00CA CONSUMES the "
             "window-owner register and writes [0x010876CC]=0 -- a second "
             "0x00CA on a cleared register is a different experiment. If arms "
             "B and C draw nothing, the register is single-shot per window and "
             "the price question needs one window per value; that is a result, "
             "not a null. Items use the content rows' own flags: clearing F8 "
             "bit 2 makes every row an hourglass this server never resolves.",
    ),
    "shop_window_kinds": lambda a, o: Probe(
        question="0x00C3 field 1 is a transaction KIND -- what kinds are "
                 "there? Sweep 0..15 and photograph the tab strip.",
        predicts="11 draws Buy/Sell tabs (OBSERVED 20260819T173300) and runs "
                 "FIRST as the positive control, so an all-null run cannot be "
                 "confused with a broken rig. WIKI (GWW, 'NPC service') lists "
                 "merchant, six traders, collector, four crafters, skill "
                 "trainer, Xunlai storage, guild registrar, map travel, "
                 "mercenary registrar -- so if the enum follows the game's own "
                 "services, several more of 0..15 should draw SOMETHING, and a "
                 "different tab strip or instruction line names the kind on "
                 "screen. The informative negative is a sweep where only 11 "
                 "draws: that would mean the other windows are opened by other "
                 "opcodes in the eight-reader family, not by this field.",
        steps=_shop_window_kinds_steps(a, o),
        note="EACH ARM RE-ARMS 0x00C4 -> 0x0084 -> 0x00CA before its 0x00C3, "
             "because both 0x00C3 and 0x00CA consume-and-clear the owner "
             "register. Arms are 7 s and the client is photographed "
             "throughout, so an arm that kills the client is bracketed by the "
             "log and everything before it is already banked. Prior 0x00C3 "
             "deaths at 3 and 40 are NOT evidence about the kind: both were "
             "sent over a three-item list by a client with no bags and no "
             "funds, which is a different experiment.",
    ),
    "merchant_window": lambda a, o: Probe(
        question="Two, and the second cannot cost the first. (Q1) With the "
                 "player's bags now created during LOAD rather than after "
                 "spawn, does pressing Buy on our own authored shop finally "
                 "put GAME_CMSG 0x4D on the wire? (Q2) What is 0x00C3 field "
                 "1 -- a COUNT of staged items or a TYPE constant -- when the "
                 "message is finally sent in retail's own shape?",
        predicts="Q1: 20260819T140723 had a funded purse, correct prices and "
                 "Buy ENABLED, and an operator-watched click produced ZERO "
                 "c2s traffic because the client had nowhere to put the item. "
                 "authsrv.PLAYER_BAGS now sends retail's nine bags in the "
                 "login burst, so a click on Buy should emit 0x004D and the "
                 "funds line should fall by the quoted price WITHOUT any "
                 "server message carrying the debit. Silence means the "
                 "backpack was not the whole story. Q2: prior 0x00C3 sends "
                 "carried 3 and 40 over a THREE-item list and both died; the "
                 "corpus has 0x00C3 [11, 0] over ELEVEN staged items, 6 of 6, "
                 "and that shape has never been tried here. Survival keeps "
                 "count and type alive for one more run to separate; another "
                 "c0000005 says no field we send is the problem and closes "
                 "the row as unknowable from the wire.",
        steps=_merchant_window_steps(a, o),
        note="THE ITEM-ID READING IS ALREADY DEAD, and the corpus killed it "
             "at the desk rather than on the client: 0x00C3 field 1 is 11 on "
             "six windows across three connections and two different "
             "shopkeepers, while item handles on those same connections vary "
             "per connection (the bag ids alone drew 8..16 on one and "
             "570/496/398.. on another). A constant is not a handle. What "
             "the corpus CANNOT do is separate count from type, because all "
             "six windows staged exactly eleven -- which is why this run "
             "stages eleven too. ORDER IS THE RISK, not the payload: 0x00C3 "
             "and 0x00CA are two of eight readers that consume-and-clear the "
             "owner register 0x00C4 writes, so opening 2 sends all four "
             "back-to-back the way retail does. 0x00C5 is deliberately never "
             "sent -- it asserts accumIntList[0].Count() >= 1 and composes a "
             "string embedding an item name we cannot build.",
    ),
    "accum_drain_e1": lambda a, o: Probe(
        question="What does the 0x00E1 drain (event 0x100000BA, upstream "
                 "SKILL_ADD_TO_WINDOWS_END) do with three real declared item "
                 "ids staged in BOTH accum columns? The 2026-08-18 run never "
                 "photographed this arm.",
        predicts="Most likely QUIET, like its three siblings -- and QUIET "
                 "refutes nothing, because the one observed reader of this "
                 "buffer rides a window context and this run opens none. What "
                 "would be new is any surface gaining three rows, or anything "
                 "SKILL-flavoured, since the buffer is full of ITEM ids and "
                 "upstream's name points at skills. Three reps must agree; a "
                 "disagreement among them outranks any single verdict.",
        steps=_accum_drain_e1_steps(a),
        note="Re-run for coverage, not for a new idea: accum_drains measured "
             "0x0085/0x00D4/0x0086 quiet and lost 0x00E1 when the client left "
             "the OS foreground and shot_if_foreground rightly declined to "
             "photograph another window -- an unmeasured arm and a quiet arm "
             "read identically in a summary. Fixed by repetition (three arms "
             "~11 s apart, each restaging both columns, independent because "
             "every drain zeroes both counts) rather than by weakening the "
             "foreground guard, which exists because a run once photographed "
             "an unrelated window. Score the bottom HUD strip separately: the "
             "prior run's only spike was a skill tooltip from a resting mouse.",
    ),
    "accum_drains": lambda a, o: Probe(
        question="Which UI surface does each accum-table drain event drive "
                 "(0x100000B8/52/BA/B9), with three declared, distinctly "
                 "named item ids actually staged?",
        predicts="If upstream's WINDOW_ADD_ITEMS / SKILL_ADD_TO_WINDOWS_END "
                 "family names are honest, at least one drain renders the "
                 "three item names on some window surface and 0x00E1's "
                 "surface is skill-flavoured. The stated null -- nothing "
                 "lights on any arm -- refutes NOTHING (the 2026-08-13 "
                 "screen pass already proved all four QUIET on an empty "
                 "buffer; subscribers may need an open window), and says the "
                 "follow-up needs a window context, not that the events are "
                 "dead. A ChCliApi.cpp(1587) assert on the LAST arm would "
                 "contradict the verified count bookkeeping and reopen the "
                 "disassembly.",
        steps=_accum_drains_steps(a),
        note="Replaces newopcodes section-4 item 7 as written: the desk read "
             "it asked for showed the appenders share one handler "
             "(0x0084 == 0x00D7 to the client, so only 0x0084 is used), "
             "0x0085 is the only single-list drain, 0x00D4/0x00E1 drain "
             "both lists, and 0x0086 ASSERTS equal counts then posts the "
             "lists as parallel columns -- the ladder's arm would have "
             "crashed on 3 != 0. Every multi-list arm here stages column 1 "
             "as [1,1,1]; the assert-carrying drain runs last so three arms "
             "bank frames before the risky one. No aiming: the readout is "
             "whatever fixed UI moves, bracketed by the gamesrv log.",
    ),
}
