#!/usr/bin/env python3
"""The interact path: the walk order, and the interact that is HELD not dropped.

    python toolkit/authsrv/test_interact.py

WHAT EARNS THIS FILE. Until 2026-08-19 nothing in the suite exercised
`_handle_interact` at all -- `test_dispatch.py` names it once, in a docstring,
to explain that an arm may delegate its body. So the range gate, the silent
drop, and every consequence of talking to an NPC were carried by no check, and
the bug below lived from 2026-08-16 to 2026-08-19 in exactly that blind spot.

THE BUG, and why the test is shaped the way it is. Clicking a distant NPC did
not move the player. The recorded diagnosis said the CLIENT walks you over on
its own and our only fault was the range number. Both halves were wrong,
measured off five keyed live captures:

  * the stock client sends NO movement order of its own on an NPC click --
    46 c2s INTERACTs, 0 of them with a `0x003E MOVE_TO_COORD` within 100 ms;
  * ArenaNet's server sends `GAME_SMSG 0x002A AGENT_UPDATE_DESTINATION` naming
    the player's own agent (17 in the corpus, 16 of them within one round trip
    of an INTERACT or ATTACK naming the agent walked to);
  * and it does not DROP the out-of-range interact -- it answers it late, after
    about `(gap - range) / 288 u/s`, the time the walk itself takes (agent 99 at
    1054 u: predicted 2.79 s, observed 2.56 s), with no new client packet in the
    gap.

So the fix is two behaviours, and this file asserts them apart: ORDER THE WALK,
and HOLD THE INTERACT until the client's own position report says it arrived.

THE CONTROL THAT MATTERS is section 4. `_order_walk` deliberately does not set
`state["dest"]`, because the server's integrator would then advance our idea of
the player's position whether or not the client actually moved -- and the held
interact is gated on that position, so a client stopped by its own collision
would get a dialog opened at a distance while standing still. That is the same
shape as the warp the tick's own comment records (a position GRANT overriding
the client by 765 units). A test that only checked "the interact eventually
fires" would pass just as well with the bug in.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks    # noqa: E402
import authsrv   # noqa: E402

# MEASURED from the first green run: 6 sections, 19 unconditional checks (3+5+
# 4+2+3+2), no vault and no client needed -- this is pure state machinery, so
# the floor IS the count rather than a bare-machine subset of it. It was written
# as 18 from a count in my head and corrected against the run, which is the
# whole of why CLAUDE.md says to set a floor from a green run and not a guess.
LEDGER = checks.Ledger("the interact path: walk order and held interact",
                       floor=29)   # section 5 (the routed walk, 2026-09-12) +7; from the green run
check = checks.adopt(LEDGER)

NPC = 99
FAR = (5000.0, 0.0)      # where the NPC stands: 5000 u out, far past the range
NEAR = (100.0, 0.0)      # an NPC standing inside the range instead
ARRIVED = (4900.0, 0.0)  # the PLAYER, 100 u from the NPC at FAR -- in range.
# Named rather than inlined because the first draft of this file moved the
# player to NEAR and called it arrival, leaving 4,900 u between the two and
# three checks red. The test caught it; a test that asserted only "the hold is
# eventually released" would have been satisfied by never releasing it.


def fresh(pos=(0.0, 0.0), spot=FAR):
    """A recording `send` and the minimum state the interact path reads."""
    sent = []
    state = {"pos": pos, "plane": 0, "agent_pos": {NPC: spot},
             "quests": set(), "objectives_done": set(), "desc_sent": set()}
    return (lambda op, vals, label="", quiet=False: sent.append((op, vals)),
            state, sent)


def main():
    print("0. the walk order ships OFF, and the hold does not")
    check(authsrv.INTERACT_WALK is False,
          "INTERACT_WALK defaults to False",
          "MEASURED BROKEN on run 20260819T111841: a lone 0x002A drags the "
          "character along a STRAIGHT LINE through geometry -- the operator "
          "watched it walk through a staircase and stop clipping underneath -- "
          "and the client sends no position report during it, so the held "
          "interact never sees an arrival. The corpus correlation is real; our "
          "reconstruction of what to send is not stock behaviour, and a player "
          "dragged through a staircase is worse than one who does not move")
    send, state, sent = fresh()
    authsrv._handle_interact(send, state, 1, NPC)
    check(authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
          not in [op for op, _v in sent],
          "so by default no walk order goes out",
          f"{[hex(o) for o, _v in sent]}")
    check(state.get("pending_interact") == (NPC, 0),
          "but the interact is still HELD -- the two halves are independent",
          "the hold is measured (ArenaNet answers a distant interact late "
          "rather than dropping it) and it works today for a player walking "
          "over on the KEYBOARD, which does report position")

    print("\n1. with --interact-walk, the order goes out and the interact holds")
    authsrv.INTERACT_WALK = True
    try:
        send, state, sent = fresh()
        authsrv._handle_interact(send, state, 1, NPC)
        ops = [op for op, _v in sent]
        check(authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION in ops,
              "the walk order goes out",
              f"{[hex(o) for o in ops]} -- kept runnable behind the flag so the "
              f"next measurement of what carries the PATHING is one argument "
              f"away rather than a rebuild")
        check(state.get("pending_interact") == (NPC, 0),
              "and the interact is HELD rather than dropped",
              f"{state.get('pending_interact')} -- ArenaNet answers it late "
              f"rather than refusing it; dropping it is why arriving on foot "
              f"used to do nothing")
        check(state.get("interacting") is None,
              "and is NOT served yet",
              f"{state.get('interacting')} -- serving it here would open a "
              f"dialog across the map, which is the range gate's whole job")
    finally:
        authsrv.INTERACT_WALK = False

    print("\n2. the walk order's payload is the one the corpus shows")
    walk = [v for op, v in sent if op == authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION]
    check(len(walk) == 1, "exactly one order", f"{len(walk)}")
    vals = walk[0]
    check(vals[0] == authsrv.PLAYER_AGENT_ID,
          "addressed to the PLAYER's own agent",
          f"{vals[0]} -- addressing the NPC would order the NPC to walk")
    check(tuple(vals[1]) == FAR,
          "carrying the target's own position as the destination",
          f"{vals[1]} -- equal to the target's position in 12 of 23 corpus "
          f"sightings")
    check(vals[4] == NPC,
          "and naming the target in the follow slot",
          f"{vals[4]} -- 0x0029 hardcodes this field to zero; 0x002A is where "
          f"the target actually rides")
    from schema.codec import Codec
    check(len(Codec().encode("GAME_SMSG",
                             authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION,
                             vals)) == 22,
          "and it encodes to the declared 22 bytes",
          "a payload the codec cannot frame would desync the channel rather "
          "than fail here")

    print("\n3. the held interact is served on arrival, and only then")
    send, state, sent = fresh()
    authsrv._handle_interact(send, state, 1, NPC)
    sent.clear()
    authsrv.interact_pending_tick(send, state, 1)
    check(state.get("pending_interact") == (NPC, 0),
          "a tick with the player still far away serves nothing",
          f"{state.get('pending_interact')}")
    check(sent == [],
          "and sends nothing -- no re-order every tick",
          f"{[hex(o) for o, _v in sent]} -- re-sending the destination at 20 Hz "
          f"would be a packet storm no capture shows")

    state["pos"] = ARRIVED       # the CLIENT reports it arrived
    authsrv.interact_pending_tick(send, state, 1)
    check(state.get("pending_interact") is None,
          "once the client reports arrival the hold is released",
          f"{state.get('pending_interact')}")
    check(state.get("interacting") == NPC,
          "and the interact is served",
          f"{state.get('interacting')} -- this is the whole point of the "
          f"rung: walking over and being talked to")

    print("\n4. CONTROL: the walk order does not touch state['dest']")
    send, state, _sent = fresh()
    authsrv._handle_interact(send, state, 1, NPC)
    check(state.get("dest") is None,
          "the server does not start integrating the player toward the NPC",
          "setting dest would advance OUR idea of the player's position "
          "whether or not the client moved -- and the held interact is gated "
          "on exactly that position, so a client stopped by its own collision "
          "would get a dialog opened while standing still. Same shape as the "
          "765-unit warp the world tick's own comment records")
    # And prove the gate really is the client's report: move only `pos`.
    state["pos"] = ARRIVED
    authsrv.interact_pending_tick(send, state, 1)
    check(state.get("interacting") == NPC,
          "and arrival is decided by the reported position alone",
          "the client's report is the authority the receive path writes")

    print("\n5. an in-range interact is served at once, with no walk order")
    send, state, sent = fresh(pos=(0.0, 0.0), spot=NEAR)
    authsrv._handle_interact(send, state, 1, NPC)
    ops = [op for op, _v in sent]
    check(authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION not in ops,
          "no destination is ordered for someone already standing there",
          f"{[hex(o) for o in ops]} -- ArenaNet's own answered interacts carry "
          f"no walk order when the player is already in range")
    check(state.get("interacting") == NPC, "and it is served immediately",
          f"{state.get('interacting')}")
    check("pending_interact" not in state,
          "and nothing is held", f"{state.get('pending_interact')}")

    print("\n6. the two ways a hold must not outlive its reason")
    send, state, _sent = fresh()
    authsrv._handle_interact(send, state, 1, NPC)          # hold NPC
    state["agent_pos"][77] = NEAR
    authsrv._handle_interact(send, state, 1, 77)           # talk to someone else
    check(state.get("pending_interact") is None,
          "serving any interact cancels a held one",
          f"{state.get('pending_interact')} -- the player changed their mind, "
          f"and firing the stale hold on arrival would open a window they no "
          f"longer asked for")

    send, state, _sent = fresh()
    authsrv._handle_interact(send, state, 1, NPC)
    del state["agent_pos"][NPC]                            # it despawned
    authsrv.interact_pending_tick(send, state, 1)
    check(state.get("pending_interact") is None,
          "and a hold whose agent left the world is dropped, not carried",
          "a despawn, a kill or a map change all land here; carrying the id "
          "would leave a reference to a body the world no longer has")

    print("\n5. the ROUTED interact-walk (2026-09-12): the approach point, and "
          "the hold alone where there is no mesh")
    ap = authsrv.interact_approach_point
    p = ap(FAR, (0.0, 0.0))
    check(abs(p[0] - (FAR[0] - authsrv.INTERACT_STOP)) < 1e-6 and abs(p[1]) < 1e-6,
          f"the approach point is INTERACT_STOP ({authsrv.INTERACT_STOP:.0f} u) "
          f"short of the NPC on the player's side", f"{p}")
    check(authsrv.INTERACT_STOP < authsrv.INTERACT_RANGE,
          "and it lies INSIDE the interact range, so arriving there serves the "
          "hold", f"stop {authsrv.INTERACT_STOP} < range {authsrv.INTERACT_RANGE}")
    check(ap(FAR, FAR) == FAR and ap(FAR, (FAR[0] - 50.0, FAR[1])) == FAR,
          "a player already inside the stop distance -- or on the NPC -- gets "
          "the NPC's own spot, and the arithmetic never divides by zero")
    check(authsrv.INTERACT_RANGE == 144.0,
          "INTERACT_RANGE is the wiki's touch range, 144 -- the owner read the "
          "old 250 as 'probably 2x' stock, and 250/144 is 1.7",
          f"{authsrv.INTERACT_RANGE}")
    check(authsrv.INTERACT_ROUTE is True,
          "the routed walk ships ON (--no-interact-route reverts)")
    send, state, sent = fresh()
    check(authsrv.interact_route(send, state, 1, NPC, FAR) is False
          and not sent,
          "with NO mesh the router has nothing to route over: no walk, "
          "nothing sent, and the caller holds the interact alone",
          f"{[hex(o) for o, _v in sent]}")
    send, state, sent = fresh()
    authsrv._handle_interact(send, state, 1, NPC)
    check(state.get("pending_interact") == (NPC, 0)
          and authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
          not in [op for op, _v in sent],
          "and the out-of-range interact is still HELD, with no 0x002B either "
          "-- the two halves stay independent, as section 0 says of 0x002A")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
