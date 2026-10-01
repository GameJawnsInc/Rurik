r"""test_shrinewarp -- the wipe's shrine placement ends the movement records the body left
behind, so the first attack press after it does not re-pin the player where it died
(SHRINEWARP, 2026-09-30; PLAN-LOG "SHRINEWARP").

WHAT IT IS REALLY CHECKING. On 20260930T224421 the owner, stood at the shrine after a
wipe, pressed C + space at the raider and "warp[ed] from where i resurrected to the
enemy instantly". The log: `PRESS ENDS THE WALK: 0x002C at the modelled body
(1348,3312)` -- the death spot, 1,786 u from the shrine at (1536,1536). The player had
died mid-approach; a corpse sends no 0x003D / 0x0047, so the click latch, its leg and the
last report outlived the death (by design: kill_player leaves the latches to the arms
that own them), and the wipe moved `pos` without retiring them. The press found a click
"in flight", lerped the stale leg and put a 0x002C on it. The fixture is that state.

  1  the run's state through the REAL wipe_to_shrine: the latch, the leg and the last
     report are gone; `_click_leg_start` answers from the placement (the shrine).
  2  the REAL press (_press_supersedes) after the wipe sends NO 0x002C and moves nothing.
  3  the KNOWN-BAD arm (--wipe-keeps-legs): the same press sends 0x002C at (1348,3312)
     and sets pos there -- the owner's warp, reproduced.
  4  a press on a LIVE click leg (no wipe) still ends it at the modelled body -- the
     ANIMREF-RE 39 behaviour the fix must not touch.
  5  the switch's wiring.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import leadgeom                                                # noqa: E402

# Floor from the green run of 2026-09-30, bare (RURIK_VAULT at an empty directory) and
# vaulted alike: 8 -- nothing here reads the vault. WIPE_PLACEMENT_ENDS_LEGS = False in
# the source reddens 4 (the warp itself among them).
LEDGER = checks.Ledger("shrine warp", floor=8)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
FOE = 110
POS = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
DEATH = (1348.0, 3312.0)            # where the player died (the run's re-pin point)
SHRINE = (1536.0, 1536.0, 0)        # the run's shrine (the sandbox spawn)


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals), label))


def _raider():
    return {"name": "Bandit Raider", "dead": False, "died_at": 0.0, "health": 3000.0,
            "max_health": 3000.0, "last_hit": 0.0, "pos": (1301.0, 3850.0), "plane": 0,
            "allegiance": agents.ALLEGIANCE_HOSTILE, "effects": 0, "attacks_back": True,
            "skills": (), "skill_ready": [], "npc": {"level": 10, "profession": 1}}


def _dead_mid_approach():
    """The state the run left at the death: the approach's click leg finished at the
    death spot 30 s ago, the client's last report there, the player down."""
    now = time.time()
    leg = leadgeom._leg_record((1300.0, 3000.0), DEATH, now - 30.0, 288.0)
    st = {"agents": {FOE: _raider()}, "pos": DEATH, "plane": 0,
          "spawn_point": SHRINE, "map_id": -1,
          "click_moving_at": leg["t0"], "click_leg": leg,
          "client_pos": DEATH, "client_plane": 0, "client_pos_at": now - 31.0,
          "player_dead": True, "player_died_at": now - 12.0, "player_health": 0.0}
    return st


def _wipe(st):
    w = Wire()
    authsrv.wipe_to_shrine(w, st, 1)
    return w.sent


def section_wipe():
    print("== 1. the real wipe retires what the corpse left ==")
    st = _dead_mid_approach()
    sent = _wipe(st)
    placed = [v for op, v, _l in sent if op == POS and v[0] == P]
    check(placed and tuple(placed[0][1]) == SHRINE[:2] and st["pos"] == SHRINE[:2],
          "the wipe puts the player at the shrine (0x002C and pos)", f"{placed}")
    check(st.get("click_moving_at") is None and st.get("click_leg") is None
          and st.get("client_pos") is None,
          "and the click latch, its leg and the last report are GONE -- the placement "
          "ended the walk and contradicts the report (the follow was already gone: "
          "kill_player abandons it at the death)",
          f"latch {st.get('click_moving_at')}, leg {st.get('click_leg')}, "
          f"report {st.get('client_pos')}")
    model = leadgeom._click_leg_start(st, time.time(), silent=st.get("click_moving_at") is not None)
    check(model is not None and tuple(model) == SHRINE[:2],
          "so the body model answers from the placement: the shrine", f"{model}")
    return st


def section_press(st):
    print("== 2. the press after the wipe re-pins nothing ==")
    w = Wire()
    authsrv._press_supersedes(w, st, 1, FOE)
    pins = [v for op, v, _l in w.sent if op == POS]
    check(pins == [] and st["pos"] == SHRINE[:2],
          "C + space after the wipe sends NO 0x002C and the player stays at the shrine",
          f"pins {pins}, pos {st['pos']}")


def section_known_bad():
    print("== 3. the known-bad arm: --wipe-keeps-legs reproduces the warp ==")
    saved = authsrv.WIPE_PLACEMENT_ENDS_LEGS
    authsrv.WIPE_PLACEMENT_ENDS_LEGS = False
    try:
        st = _dead_mid_approach()
        _wipe(st)
        check(st.get("click_moving_at") is not None and st.get("client_pos") == DEATH,
              "the wipe leaves the latch and the death-spot report standing", "")
        w = Wire()
        authsrv._press_supersedes(w, st, 1, FOE)
        pins = [v for op, v, _l in w.sent if op == POS]
        check(len(pins) == 1 and tuple(round(c) for c in pins[0][1]) == (1348, 3312)
              and tuple(round(c) for c in st["pos"]) == (1348, 3312),
              "and the press sends 0x002C at (1348,3312), the death spot -- the owner's "
              "warp from the shrine to the raider, as the run's log printed it",
              f"pins {pins}, pos {st['pos']}")
    finally:
        authsrv.WIPE_PLACEMENT_ENDS_LEGS = saved


def section_live_leg():
    print("== 4. a press on a LIVE click leg still ends it (ANIMREF-RE 39 untouched) ==")
    now = time.time()
    leg = leadgeom._leg_record((0.0, 0.0), (288.0, 0.0), now - 0.5, 288.0)
    st = {"agents": {FOE: _raider()}, "pos": (0.0, 0.0), "plane": 0,
          "click_moving_at": leg["t0"], "click_leg": leg}
    w = Wire()
    authsrv._press_supersedes(w, st, 1, FOE)
    pins = [v for op, v, _l in w.sent if op == POS]
    check(len(pins) == 1 and 120.0 < pins[0][1][0] < 170.0 and st.get("click_moving_at") is None,
          "a press half a second into a live 288 u/s click leg re-pins the body ~144 u along "
          "it and ends the leg -- the press contract the fix leaves alone",
          f"pins {pins}")


def section_wiring():
    print("== 5. the switch ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    wipe = src[src.index("def wipe_to_shrine("):]
    wipe = wipe[:wipe.index("\ndef ")]
    check(authsrv.WIPE_PLACEMENT_ENDS_LEGS is True and '"--wipe-keeps-legs"' in args
          and "if a.wipe_keeps_legs:" in src
          and '_forget_client_position(state, "the wipe placed the player at the shrine")' in wipe,
          "WIPE_PLACEMENT_ENDS_LEGS ships ON, --wipe-keeps-legs reverts it, and the wipe "
          "uses the placement helper rather than a second writer of the report", "")


def main():
    st = section_wipe()
    section_press(st)
    section_known_bad()
    section_live_leg()
    section_wiring()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
