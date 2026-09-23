"""The hero skill SUPPRESS toggle, c2s 0x0019 HERO_SKILL_TOGGLE -- DESKWORK-D1
step 6 (studies/cmsg/FINDINGS.md DESKWORK-D1 "The hero skill toggle").

    python toolkit/authsrv/test_heroskilltoggle.py

WHAT THIS PINS. The message is RECONSTRUCTION end to end -- no retail tape
and no loopback log carries a c2s 0x0019 -- so nothing here compares to a
tape chunk. What it pins is the reading the arm rests on and that the arm
does exactly that reading:

  * §1 THE TOGGLE: a click on an occupied panel slot flips one bit of the
    hero's mask and is answered with the whole mask, 0x0065 [hero agent, mask]
    (retail's only observed writer of the client's hotKeyState mask, 8 of 8 at
    load, all zero); the second click releases it; under
    --hero-skill-toggle-per-bit the reply is 0x0064 [agent, slot, value]
    instead (the route's pre-registered reply; never on retail's wire); two
    slots compose into one mask.
  * §2 REFUSALS send NOTHING: an agent that is not a party hero, a kicked
    hero, a hotKey outside 0..7 (the client asserts `hotKey < 8` itself,
    ChCliApi:4359), an EMPTY panel slot (both client senders check the slot
    holds a skill first), a malformed request.
  * §3 THE BODY STOPS CASTING IT: pick_skill never returns a suppressed skill
    (GWW's one rule for the mask), the join is by SKILL ID through the
    PANEL's eight slots -- a bar with a hole ([322, 0, 348, ...]) suppressed
    at panel slot 2 removes skill 348, not the body's list index 2 -- and the
    KNOWN-BAD arm (indexing the body's compacted list) picks the wrong skill;
    releasing restores the pick; all-suppressed picks None. THE CLIENT'S OWN
    BAR EDITS MOVE THE MASK (the fix pass, EVID-D1C-1): a 0x005E swap through
    the real handler EXCHANGES the two slots' bits (the client's 0x00821460
    does, ChCliSkill:332/333), so suppression follows the SKILL -- the
    KNOWN-BAD per-SLOT reading (the first cut's) disagrees with the screen;
    a 0x005C set CLEARS the set slot's bit (0x008212C0, ChCliSkill:258).
    §3b a SUPPRESSED RESURRECTION is never cast by ally_cast_tick's dead-first
    branch, and is cast once released (ENG-B2). §3c without --persist the
    toggle reads the SESSION's edited bar, so a slot the client just filled
    is answered, not refused as EMPTY (ENG-M1).
  * §4 PERSIST: a toggle under --persist writes `disabled_slots` to the
    hero's row; a fresh connection reads it back and its load block's two
    0x0065 rows carry the mask; the store's setter and validate() refuse 256,
    -1 and a bool (the setter left the stored mask unchanged); with
    --no-hero-skill-toggle a stored mask is neither read nor sent.
  * §5 BYTE-IDENTITY: with no toggle the load block's 0x0065 rows are
    [agent, 0] twice, retail's 8-of-8 value, and hero_panel_bar_ids equals the
    expression hero_character_block sent before this step for the stored-bar,
    authored-row and fallback cases.
  * §6 SOURCE LOCKS (syntax tree over authsrv.py, each with a mutation that
    reddens it): the 0x0019 arm calls the handler only under
    HERO_SKILL_TOGGLE_ENABLED; main() wires both flags; pick_skill reads
    skill_disabled_ids; hero_body_create passes it; sync_hero_body_bar
    refreshes it; the block's two 0x0065 rows carry the mask; serverargs
    defines both flags; both hero bar-edit handlers call hero_mask_write;
    ally_cast_tick's dead-first loop skips a suppressed id; the legacy rig's
    0x00DA is followed by a 0x0065 carrying a stored mask (the 0x00DA setter
    zeroes the client's mask, EVID-D1C-3); hero_panel_bar_ids reads the
    session's bar first.

Drives the real handler with a fake send and a scratch store, like
test_heroadd.py. Floor from the green run (see the ledger line).
"""
import ast
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import charstore                                             # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("hero skill toggle (DESKWORK-D1 step 6)", floor=71)   # 2026-09-23, from the green run (53 -> 71 at the fix pass)

SRC_PATH = os.path.join(HERE, "authsrv.py")
ARGS_PATH = os.path.join(HERE, "serverargs.py")
TOGGLE = authsrv.GAME_CMSG_HERO_SKILL_TOGGLE
MASK_MSG, BIT_MSG = authsrv.GAME_SMSG_HERO_UNNAMED_0065, authsrv.GAME_SMSG_SKILLBAR_SLOT_FLAG
UUID = "33333333333333333333333333333333"
assert TOGGLE == 0x0019 and MASK_MSG == 0x0065 and BIT_MSG == 0x0064


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals) if isinstance(vals, (list, tuple)) else vals))
    return sent, send


def fresh_state(**kw):
    st = {"agents": {}, "char_uuid": UUID}
    st.update(kw)
    return st


class Rec:
    """The bar-edit handlers' recorder; nothing here reads what it records."""
    def event(self, *a, **k):
        pass


_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "PERSIST", "HERO_AGENT_ID", "HERO_SKILL_TOGGLE_ENABLED",
           "HERO_SKILL_TOGGLE_PER_BIT", "HERO_RIG_0065")}
base = tempfile.mkdtemp(prefix="heroskilltoggle-test-")
try:
    authsrv.HERO_IDS = [6]
    authsrv.HERO_AGENT_ID = 200
    authsrv.PERSIST = False
    authsrv.HERO_SKILL_TOGGLE_ENABLED = True
    authsrv.HERO_SKILL_TOGGLE_PER_BIT = False
    authsrv.HERO_RIG_0065 = True

    # -- §1 the toggle -----------------------------------------------------------
    st = fresh_state()
    bar = authsrv.hero_panel_bar_ids(st, 6)
    led.ok(len(bar) == 8 and bar[0] and bar[1],
           "the default hero's panel bar has eight slots with slots 0 and 1 occupied "
           "(the JARIN fallback: the player's SKILLBAR)", f"bar {bar}")
    sent, send = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], send, st, 0)
    led.ok(sent == [(MASK_MSG, [200, 0b10])],
           "a suppress click on slot 1 answers with ONE 0x0065 [hero agent, mask] and "
           "mask bit 1 set", f"sent {sent}")
    led.ok(authsrv.hero_disabled_mask(st, 6) == 2
           and authsrv.hero_disabled_skill_ids(st, 6) == frozenset({bar[1]}),
           "the session's mask is 0b10 and the suppressed skill id is the slot's skill",
           f"mask {authsrv.hero_disabled_mask(st, 6)} ids {authsrv.hero_disabled_skill_ids(st, 6)}")
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 0], send, st, 0)
    led.ok(sent[-1] == (MASK_MSG, [200, 0b11]),
           "a second slot composes into the same mask: 0x0065 [200, 0b11]", f"{sent[-1]}")
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], send, st, 0)
    led.ok(sent[-1] == (MASK_MSG, [200, 0b01]) and authsrv.hero_disabled_mask(st, 6) == 1,
           "clicking slot 1 again RELEASES it: the mask drops the bit", f"{sent[-1]}")
    led.ok(len(sent) == 3, "three clicks, three messages -- nothing else went out")
    # the per-bit alternative
    authsrv.HERO_SKILL_TOGGLE_PER_BIT = True
    st2 = fresh_state()
    sent2, send2 = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], send2, st2, 0)
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], send2, st2, 0)
    led.ok(sent2 == [(BIT_MSG, [200, 1, 1]), (BIT_MSG, [200, 1, 0])],
           "--hero-skill-toggle-per-bit answers 0x0064 [agent, slot, 1] then [agent, slot, 0]",
           f"sent {sent2}")
    led.ok(authsrv.hero_disabled_mask(st2, 6) == 0, "...and the mask is back to 0")
    authsrv.HERO_SKILL_TOGGLE_PER_BIT = False

    # -- §2 refusals ---------------------------------------------------------------
    for req, why in (([TOGGLE, 201, 1], "an agent that is no hero of this run"),
                     ([TOGGLE, 200, 8], "hotKey 8 (the client's own bound is < 8)"),
                     ([TOGGLE, 200, -1], "a negative hotKey"),
                     ([TOGGLE, 200, 7], "an EMPTY panel slot"),
                     ([TOGGLE, 200], "a malformed request")):
        st3 = fresh_state()
        sent3, send3 = fake_send_factory()
        authsrv.handle_hero_skill_toggle(req, send3, st3, 0)
        led.ok(sent3 == [] and authsrv.hero_disabled_mask(st3, 6) == 0,
               f"REFUSED with nothing sent and no mask change: {why}", f"sent {sent3}")
    st4 = fresh_state(kicked_heroes={6})
    sent4, send4 = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], send4, st4, 0)
    led.ok(sent4 == [], "REFUSED: a KICKED hero's agent is not a party hero")
    st5 = fresh_state()
    sent5, send5 = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], send5, st5, 0)
    led.ok(sent5 != [], "CONTROL: the same click on the un-kicked hero is answered")

    # -- §3 the body stops casting it ----------------------------------------------
    # A stored bar WITH A HOLE, so the panel's slot index and the body's list index
    # differ -- the case a naive join gets wrong.
    store = charstore.Store.open("toggle@rurik.invalid", base=base)
    store.ensure_character(UUID, "Toggler", "cc" * 37)
    store.set_hero_skillbar(UUID, 6, [322, 0, 348, 1, 385, 0, 0, 2])
    st6 = fresh_state(charstore_game=store)
    panel = authsrv.hero_panel_bar_ids(st6, 6)
    led.ok(panel == [322, 0, 348, 1, 385, 0, 0, 2],
           "the panel bar is the STORED bar, holes kept", f"{panel}")
    body = {"hero": 6, "skills": authsrv.bar_triples(panel),
            "skill_ready": [0.0] * 5, "last_slot": -1}
    st6["agents"][200] = body
    led.ok([s[0] for s in body["skills"]] == [322, 348, 1, 385, 2],
           "the BODY's skill list drops the holes (5 of 8) -- list index != panel slot")
    sent6, send6 = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 2], send6, st6, 0)      # panel slot 2 = 348
    led.ok(sent6 == [(MASK_MSG, [200, 0b100])], "panel slot 2 suppressed: 0x0065 [200, 4]")
    led.ok(body.get("skill_disabled_ids") == frozenset({348}),
           "the body row now carries {348} -- the PANEL slot's skill, joined by id",
           f"{body.get('skill_disabled_ids')}")
    picks = []
    for _ in range(5):
        slot = authsrv.pick_skill(body, 1.0)
        picks.append(body["skills"][slot][0] if slot is not None else None)
        body["last_slot"] = slot if slot is not None else -1
    led.ok(348 not in picks and set(picks) == {322, 1, 385, 2},
           "pick_skill cycles every OTHER skill and never 348", f"picks {picks}")
    # KNOWN-BAD: a join by the body's list index would suppress list[2] = 1, not 348.
    bad = dict(body, skill_disabled_ids=frozenset({body["skills"][2][0]}), last_slot=-1)
    bad_picks = []
    for _ in range(5):
        slot = authsrv.pick_skill(bad, 1.0)
        bad_picks.append(bad["skills"][slot][0] if slot is not None else None)
        bad["last_slot"] = slot if slot is not None else -1
    led.ok(348 in bad_picks and 1 not in bad_picks,
           "KNOWN-BAD: joining by the body's list index suppresses skill 1 and still casts "
           "348 -- the defect the id join exists for", f"picks {bad_picks}")
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 2], send6, st6, 0)      # release
    body["last_slot"] = -1
    all_picks = []
    for _ in range(5):
        slot = authsrv.pick_skill(body, 1.0)
        all_picks.append(body["skills"][slot][0])
        body["last_slot"] = slot
    led.ok(body["skill_disabled_ids"] == frozenset() and 348 in all_picks,
           "released: the body picks 348 again", f"{all_picks}")
    for slot in (0, 2, 3, 4, 7):
        authsrv.handle_hero_skill_toggle([TOGGLE, 200, slot], send6, st6, 0)
    led.ok(authsrv.hero_disabled_mask(st6, 6) == 0b10011101
           and authsrv.pick_skill(body, 1.0) is None,
           "every occupied slot suppressed (mask 0x9D): pick_skill returns None -- the "
           "hero stands", f"mask {authsrv.hero_disabled_mask(st6, 6):#x}")
    led.ok(dict(store.hero_row(UUID, 6)).get("disabled_slots") is None,
           "without --persist nothing was written to the store")
    # -- the client's own bar edits move the mask (the fix pass, EVID-D1C-1) ----------
    # The client's swap routine (0x00821460, ChCliSkill:332/333) sends 0x005E and
    # then EXCHANGES the two slots' bits of its hotKeyState mask (+0xA4), so
    # suppression follows the SKILL. The first cut kept the bit on the SLOT and
    # pinned that here; the reviewer's swap_demo showed the body casting the
    # skill the client draws struck through. Through the REAL swap handler:
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 0], send6, st6, 0)     # release 322 -> mask 0x9C
    led.ok(authsrv.hero_disabled_mask(st6, 6) == 0x9C and 348 in body["skill_disabled_ids"]
           and 322 not in body["skill_disabled_ids"],
           "before the swap: 348 (slot 2) suppressed, 322 (slot 0) not; mask 0x9C")
    authsrv.handle_skillbar_skill_swap([0x5E, 200, 322, 0, 348, 0], send6, st6, 0, Rec())
    led.ok(authsrv.hero_panel_bar_ids(st6, 6) == [348, 0, 322, 1, 385, 0, 0, 2]
           and store.hero_skillbar(UUID, 6) == [348, 0, 322, 1, 385, 0, 0, 2],
           "0x005E [200, 322, 0, 348, 0] swapped slots 0 and 2 on the panel bar and in the store")
    led.ok(authsrv.hero_disabled_mask(st6, 6) == 0x99,
           "...and the server's mask EXCHANGED bits 0 and 2 the way the client's routine does: "
           "0x9C -> 0x99", f"mask {authsrv.hero_disabled_mask(st6, 6):#x}")
    led.ok(body["skill_disabled_ids"] == frozenset({348, 1, 385, 2}),
           "the body still skips 348 (now in slot 0) and may cast 322 -- suppression followed "
           "the skill", f"{body['skill_disabled_ids']}")
    per_slot = frozenset(s for i, s in enumerate([348, 0, 322, 1, 385, 0, 0, 2])
                         if (0x9C >> i) & 1 and s)
    led.ok(per_slot == frozenset({322, 1, 385, 2}) and per_slot != body["skill_disabled_ids"],
           "KNOWN-BAD: the per-SLOT reading (the old mask on the new bar) would suppress 322 "
           "and cast 348 -- the client draws 348 struck through, so that body disagrees "
           "with the screen", f"{per_slot}")
    # a 0x005C SET into a suppressed slot clears its bit (0x008212C0, ChCliSkill:258: btr)
    lib6 = sorted(authsrv.hero_usable_library(st6, 6, authsrv.hero_bar_ids(6)))
    new6 = next(s for s in lib6 if s not in [348, 0, 322, 1, 385, 0, 0, 2])
    authsrv.handle_skillbar_skill_set([0x5C, 200, 0, new6, 0], send6, st6, 0, Rec())
    led.ok(authsrv.hero_panel_bar_ids(st6, 6)[0] == new6
           and authsrv.hero_disabled_mask(st6, 6) == 0x98
           and body["skill_disabled_ids"] == frozenset({1, 385, 2}),
           f"0x005C set skill {new6} into the SUPPRESSED slot 0: the bit is cleared (0x99 -> "
           f"0x98) and the body may cast the new skill", f"mask {authsrv.hero_disabled_mask(st6, 6):#x}")
    authsrv.handle_skillbar_skill_set([0x5C, 200, 3, 1, 0], send6, st6, 0, Rec())   # same skill, same slot
    led.ok(authsrv.hero_disabled_mask(st6, 6) == 0x90,
           "...a set into suppressed slot 3 clears bit 3 too (the client clears whatever slot it "
           "writes)", f"mask {authsrv.hero_disabled_mask(st6, 6):#x}")
    authsrv.handle_skillbar_skill_swap([0x5E, 200, 322, 0, 385, 0], send6, st6, 0, Rec())
    led.ok(authsrv.hero_disabled_mask(st6, 6) == 0x84,
           "a swap of an unsuppressed skill (322, slot 2) with a suppressed one (385, slot 4) "
           "moves the bit: 0x90 -> 0x84", f"mask {authsrv.hero_disabled_mask(st6, 6):#x}")
    authsrv.handle_skillbar_skill_swap([0x5E, 200, 385, 0, 322, 0], send6, st6, 0, Rec())
    led.ok(authsrv.hero_disabled_mask(st6, 6) == 0x90,
           "...and swapping them back restores it (0x84 -> 0x90)")

    # -- §3b a SUPPRESSED resurrection is never cast (the fix pass, ENG-B2) -------------
    # ally_cast_tick's "THE DEAD FIRST" branch picks a resurrection off the bar
    # itself, bypassing pick_skill's gate; the first cut let a struck-through
    # Resurrection Signet raise the player.
    _saved_energy = authsrv.ENERGY
    authsrv.ENERGY = False
    store_r = charstore.Store.open("rez@rurik.invalid", base=base)
    store_r.ensure_character(UUID, "Raiser", "cc" * 37)
    store_r.set_hero_skillbar(UUID, 6, [322, 0, 348, 1, 385, 0, 0, 2])
    str_ = fresh_state(charstore_game=store_r)
    panel_r = authsrv.hero_panel_bar_ids(str_, 6)
    led.ok(authsrv.skill_resurrects(2) and panel_r[7] == 2,
           "the stored bar's slot 7 holds skill 2, which resurrects")
    skills_r = authsrv.bar_triples(panel_r)
    body_r = {"hero": 6, "name": "Raiser", "allegiance": authsrv.agents.ALLEGIANCE_PLAYER,
              "pos": (0.0, 0.0), "plane": 0, "skills": skills_r,
              "skill_ready": [0.0] * len(skills_r), "last_slot": -1,
              "health": 100.0, "max_health": 100.0,
              "skill_disabled_ids": authsrv.hero_disabled_skill_ids(str_, 6)}
    str_["agents"][200] = body_r
    str_["player_dead"] = True
    sent_r, send_r = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 7], send_r, str_, 0)     # suppress the rez
    led.ok(sent_r == [(MASK_MSG, [200, 0x80])] and body_r["skill_disabled_ids"] == frozenset({2}),
           "Shift-click on slot 7: 0x0065 [200, 0x80], the body suppresses skill 2")
    sent_r.clear()
    authsrv.ally_cast_tick(send_r, str_, 0)
    led.ok(body_r.get("casting") is None and body_r.get("cast_lands_at") is None
           and not any(2 in v for _op, v in sent_r if isinstance(v, list)),
           "with the player dead the tick does NOT cast the suppressed resurrection "
           "(nothing casting, no message naming skill 2)",
           f"casting {body_r.get('casting')} sent {sent_r}")
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 7], send_r, str_, 0)     # release
    sent_r.clear()
    body_r["last_slot"] = -1
    authsrv.ally_cast_tick(send_r, str_, 0)
    led.ok(body_r.get("casting") is not None and skills_r[body_r["casting"]][0] == 2,
           "CONTROL: released, the same tick casts skill 2 at the dead player (the dead first)",
           f"casting {body_r.get('casting')} sent {sent_r[:2]}")
    authsrv.ENERGY = _saved_energy

    # -- §3c without --persist the toggle reads the session's EDITED bar (ENG-M1) -------
    st_e = fresh_state()
    panel_e = authsrv.hero_panel_bar_ids(st_e, 6)
    body_e = {"hero": 6, "skills": authsrv.bar_triples(panel_e), "skill_ready": [0.0] * 8,
              "last_slot": -1, "skill_disabled_ids": frozenset()}
    st_e["agents"][200] = body_e
    lib_e = sorted(authsrv.hero_usable_library(st_e, 6, authsrv.hero_bar_ids(6)))
    new_e = next(s for s in lib_e if s not in panel_e)
    empty_e = panel_e.index(0)
    sent_e, send_e = fake_send_factory()
    authsrv.handle_skillbar_skill_set([0x5C, 200, empty_e, new_e, 0], send_e, st_e, 0, Rec())
    led.ok(authsrv.hero_panel_bar_ids(st_e, 6)[empty_e] == new_e
           and [s[0] for s in body_e["skills"]].count(new_e) == 1,
           f"no store: 0x005C put skill {new_e} into empty slot {empty_e}; hero_panel_bar_ids "
           f"reads the SESSION's bar (the first cut re-read the row's and saw the slot empty)")
    sent_e.clear()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, empty_e], send_e, st_e, 0)
    led.ok(sent_e == [(MASK_MSG, [200, 1 << empty_e])]
           and body_e["skill_disabled_ids"] == frozenset({new_e}),
           "...and a Shift-click on that slot is ANSWERED (not refused as EMPTY) and the body "
           "skips the new skill", f"sent {sent_e}")

    # -- §4 persist ------------------------------------------------------------------
    authsrv.PERSIST = True
    store_p = charstore.Store.open("persist@rurik.invalid", base=base)
    store_p.ensure_character(UUID, "Keeper", "dd" * 37)
    stp = fresh_state(charstore_game=store_p)
    sentp, sendp = fake_send_factory()
    authsrv.handle_hero_skill_toggle([TOGGLE, 200, 1], sendp, stp, 0)
    led.ok(store_p.hero_disabled_slots(UUID, 6) == 2
           and charstore.Store.open("persist@rurik.invalid", base=base).hero_disabled_slots(UUID, 6) == 2,
           "under --persist the toggle writes disabled_slots = 2 to the hero's row, on disk")
    fresh = fresh_state(charstore_game=charstore.Store.open("persist@rurik.invalid", base=base))
    led.ok(authsrv.hero_disabled_mask(fresh, 6) == 2,
           "a FRESH connection reads the stored mask back")
    rows = [v for op, v, _l in authsrv.hero_character_block(fresh, 200, 6) if op == MASK_MSG]
    led.ok(rows == [[200, 2], [200, 2]],
           "...and its load block's TWO 0x0065 rows carry it (the load re-draws the "
           "struck-through slot)", f"{rows}")
    led.ok(authsrv.hero_disabled_skill_ids(fresh, 6) == frozenset({authsrv.hero_panel_bar_ids(fresh, 6)[1]}),
           "the fresh connection's body set is the panel slot's skill")
    # the revert arm reads nothing stored
    authsrv.HERO_SKILL_TOGGLE_ENABLED = False
    off = fresh_state(charstore_game=charstore.Store.open("persist@rurik.invalid", base=base))
    rows_off = [v for op, v, _l in authsrv.hero_character_block(off, 200, 6) if op == MASK_MSG]
    led.ok(authsrv.hero_disabled_mask(off, 6) == 0 and rows_off == [[200, 0], [200, 0]]
           and authsrv.hero_disabled_skill_ids(off, 6) == frozenset(),
           "--no-hero-skill-toggle: the stored mask is NOT read; the block sends [200, 0]; "
           "the body suppresses nothing (the pre-step-6 wire)", f"{rows_off}")
    authsrv.HERO_SKILL_TOGGLE_ENABLED = True
    for bad_mask in (256, -1, True):
        try:
            store_p.set_hero_disabled_slots(UUID, 6, bad_mask)
            refused = False
        except ValueError:
            refused = True
        led.ok(refused and store_p.hero_disabled_slots(UUID, 6) == 2,
               f"the setter refuses a mask of {bad_mask!r} and the stored mask is unchanged "
               f"(the first cut's check passed a bool that stored 1 -- ENG-M3)")
    for bad_mask in (256, -1, True):
        data = {"version": charstore.STORE_VERSION, "account": {}, "characters": {
            UUID: {"name": "X", "level": 1, "xp": 0, "skill_points": 0,
                   "heroes": {"6": {"disabled_slots": bad_mask}}}}}
        try:
            charstore.validate(data, "<mem>")
            refused = False
        except ValueError:
            refused = True
        led.ok(refused, f"validate() refuses disabled_slots = {bad_mask!r}")
    data_ok = {"version": charstore.STORE_VERSION, "account": {}, "characters": {
        UUID: {"name": "X", "level": 1, "xp": 0, "skill_points": 0,
               "heroes": {"6": {"disabled_slots": 0x9D}}}}}
    try:
        charstore.validate(data_ok, "<mem>")
        accepted = True
    except ValueError:
        accepted = False
    led.ok(accepted, "CONTROL: validate() accepts disabled_slots = 0x9D")
    authsrv.PERSIST = False

    # -- §5 byte-identity ---------------------------------------------------------------
    st7 = fresh_state()
    rows7 = [v for op, v, _l in authsrv.hero_character_block(st7, 200, 6) if op == MASK_MSG]
    led.ok(rows7 == [[200, 0], [200, 0]],
           "with no toggle the load block's 0x0065 rows are [agent, 0] twice -- retail's "
           "value on all 8 sightings", f"{rows7}")

    def legacy(hs_bar, hid):
        h = (list(hs_bar) if hs_bar is not None
             else authsrv.hero_bar_ids(hid) if authsrv.hero_bar_authored(hid)
             else authsrv.hero_bar_ids(hid) or list(authsrv.SKILLBAR))
        h = h[:authsrv.SKILLBAR_SLOTS]
        h += [0] * (authsrv.SKILLBAR_SLOTS - len(h))
        return h
    led.ok(authsrv.hero_panel_bar_ids(st7, 6) == legacy(None, 6),
           "hero_panel_bar_ids == the block's pre-step expression (no stored bar)")
    cur6 = store.hero_skillbar(UUID, 6)
    led.ok(authsrv.hero_panel_bar_ids(fresh_state(charstore_game=store), 6) == legacy(cur6, 6)
           == authsrv.hero_panel_bar_ids(st6, 6) and cur6[1] == 0 and cur6[5] == 0,
           "...and for a stored bar with holes (the store's CURRENT bar wins on a fresh "
           "connection, holes kept; the session that edited it reads the same bar)", f"{cur6}")
    led.ok(authsrv.hero_panel_bar_ids(st7, 6, [1, 2, 3]) == [1, 2, 3, 0, 0, 0, 0, 0],
           "...and a short bar handed in is padded to eight")

    # -- §6 source locks ---------------------------------------------------------------
    with open(SRC_PATH, encoding="utf-8") as f:
        SRC = f.read()
    TREE = ast.parse(SRC)

    def _func(tree, name):
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return n
        return None

    def _calls(node):
        return {c.func.id for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}

    def dispatch_lock(tree, const, flag, handler):
        handle = _func(tree, "handle")
        for n in ast.walk(handle):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)):
                continue
            t = n.test
            if not (isinstance(t.left, ast.Name) and t.left.id == "opcode"
                    and len(t.comparators) == 1
                    and isinstance(t.comparators[0], ast.Name)
                    and t.comparators[0].id == const):
                continue
            inner = [s for s in n.body if isinstance(s, ast.If)]
            direct = any(handler in _calls(s) for s in n.body if not isinstance(s, ast.If))
            return (len(inner) == 1 and not direct
                    and isinstance(inner[0].test, ast.Name) and inner[0].test.id == flag
                    and any(handler in _calls(s) for s in inner[0].body)
                    and not any(handler in _calls(s) for s in inner[0].orelse))
        return False

    def main_flags(tree, attrs):
        main = _func(tree, "main")
        flags = {}
        for n in ast.walk(main):
            if (isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
                    and n.test.attr in attrs):
                for s in n.body:
                    if (isinstance(s, ast.Assign) and len(s.targets) == 1
                            and isinstance(s.targets[0], ast.Name)
                            and isinstance(s.value, ast.Constant)):
                        flags[n.test.attr] = (s.targets[0].id, s.value.value)
        return flags

    led.ok(dispatch_lock(TREE, "GAME_CMSG_HERO_SKILL_TOGGLE", "HERO_SKILL_TOGGLE_ENABLED",
                         "handle_hero_skill_toggle"),
           "LOCK: the GAME_CMSG_HERO_SKILL_TOGGLE arm calls handle_hero_skill_toggle ONLY "
           "under `if HERO_SKILL_TOGGLE_ENABLED:` (and never in its else)")
    led.ok(SRC.count("if HERO_SKILL_TOGGLE_ENABLED:") == 1,
           "the arm's condition appears once (so the mutation below hits it)")
    mut1 = ast.parse(SRC.replace("if HERO_SKILL_TOGGLE_ENABLED:", "if True:", 1))
    led.ok(not dispatch_lock(mut1, "GAME_CMSG_HERO_SKILL_TOGGLE", "HERO_SKILL_TOGGLE_ENABLED",
                             "handle_hero_skill_toggle"),
           "KNOWN-BAD: an arm that ignores the flag fails the lock")
    flags = main_flags(TREE, ("no_hero_skill_toggle", "hero_skill_toggle_per_bit"))
    led.ok(flags == {"no_hero_skill_toggle": ("HERO_SKILL_TOGGLE_ENABLED", False),
                     "hero_skill_toggle_per_bit": ("HERO_SKILL_TOGGLE_PER_BIT", True)},
           "LOCK: main() wires --no-hero-skill-toggle and --hero-skill-toggle-per-bit",
           f"got {flags}")
    led.ok(_saved["HERO_SKILL_TOGGLE_ENABLED"] is True and _saved["HERO_SKILL_TOGGLE_PER_BIT"] is False,
           "the arm is ON and the per-bit reply OFF by default (the flags are the revert "
           "and the alternative)")
    pick_src = ast.get_source_segment(SRC, _func(TREE, "pick_skill"))
    led.ok('agent.get("skill_disabled_ids")' in pick_src and "in disabled" in pick_src,
           "LOCK: pick_skill reads the row's skill_disabled_ids and skips a member")
    mut2 = pick_src.replace("        if skills[slot][0] in disabled:\n            continue\n", "", 1)
    led.ok(mut2 != pick_src, "the skip has the expected text (so a mutation that removes it is real)")
    body_src = ast.get_source_segment(SRC, _func(TREE, "hero_body_create"))
    led.ok('"skill_disabled_ids": hero_disabled_skill_ids(state, _hid)' in body_src,
           "LOCK: hero_body_create seeds the body's skill_disabled_ids from the mask")
    sync_src = ast.get_source_segment(SRC, _func(TREE, "sync_hero_body_bar"))
    led.ok("hero_disabled_skill_ids" in _calls(_func(TREE, "sync_hero_body_bar"))
           and 'row["skill_disabled_ids"]' in sync_src,
           "LOCK: sync_hero_body_bar re-reads the join after a bar edit")
    blk_fn = _func(TREE, "hero_character_block")
    blk_src = ast.get_source_segment(SRC, blk_fn)
    led.ok("hero_disabled_mask" in _calls(blk_fn) and "hero_panel_bar_ids" in _calls(blk_fn)
           and blk_src.count("[haid, _hmask]") == 2 and "[haid, 0]" not in blk_src,
           "LOCK: hero_character_block's two 0x0065 rows carry hero_disabled_mask and its "
           "bar comes from hero_panel_bar_ids (one expression for the panel and the mask)")
    tog_fn = _func(TREE, "handle_hero_skill_toggle")
    led.ok({"hero_index_for_agent", "hero_kicked", "hero_panel_bar_ids",
            "hero_body_sync_disabled"} <= _calls(tog_fn),
           "LOCK: the handler checks the agent is a party hero, reads the PANEL bar for the "
           "empty-slot refusal and syncs the body")
    with open(ARGS_PATH, encoding="utf-8") as f:
        ARGS = f.read()
    led.ok('"--no-hero-skill-toggle"' in ARGS and '"--hero-skill-toggle-per-bit"' in ARGS,
           "LOCK: serverargs.py defines both flags")
    # the fix pass's locks
    swap_fn, set_fn = _func(TREE, "handle_skillbar_skill_swap"), _func(TREE, "handle_skillbar_skill_set")
    led.ok("hero_mask_write" in _calls(swap_fn) and "hero_mask_write" in _calls(set_fn),
           "LOCK: both hero bar-edit handlers move the mask through hero_mask_write (the swap "
           "exchanges two bits, the set clears one -- the client's 0x00821460 / 0x008212C0)")
    tick_src = ast.get_source_segment(SRC, _func(TREE, "ally_cast_tick"))
    led.ok("_s[0] not in _dis" in tick_src and 'agent.get("skill_disabled_ids")' in tick_src,
           "LOCK: ally_cast_tick's dead-first loop skips a suppressed resurrection (ENG-B2)")
    players_src = ast.get_source_segment(SRC, _func(TREE, "_handle_request_players"))
    led.ok("GAME_SMSG_HERO_UNNAMED_0065, [_haid, _hmask_legacy]" in players_src
           and players_src.index("[_haid, _hmask_legacy]") > players_src.index("SKILLBAR_PVP_MASKS, SKILLBAR_TRAILER],"),
           "LOCK: the legacy rig's 0x00DA is followed by a 0x0065 carrying a stored mask "
           "(0x008223B0 zeroes the client's mask on every 0x00DA -- EVID-D1C-3)")
    panel_src = ast.get_source_segment(SRC, _func(TREE, "hero_panel_bar_ids"))
    led.ok('state.get("hero_bars")' in panel_src
           and panel_src.index('state.get("hero_bars")') < panel_src.index("hero_build(state, hid)"),
           "LOCK: hero_panel_bar_ids reads the session's edited bar before the store's (ENG-M1)")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
