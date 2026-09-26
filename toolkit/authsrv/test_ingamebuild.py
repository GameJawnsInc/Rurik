"""A build made in-game from nothing -- the three defects SANDBOX-U5's first run met.

    python toolkit/authsrv/test_ingamebuild.py

THE RUN (harness 20260925T230749, 2026-09-25, the owner's launch of a scripted walk):
a sandbox spec whose character and hero start with EMPTY bars and no ranks, built in
the K panel in outpost 148 (a raise and a dragged skill each), then backed through the
148 -> 168 portal to fight. Three things went wrong, none of them the panel's:

  D1 the character's bar was NOT empty at load: `player_skills = []` reached
     PARTY_SKILLBAR as an answer, and default_skillbar's `if PARTY_SKILLBAR:` read the
     empty list as no field -- SKILLBAR_UPDATE[351, 359, 352, 356, 322, 346, 1, 2], the
     content [player.skillbar].
  D2 one dragged slot cost the other seven on the next load: the set handler stored
     the ONE slot, the store's slot writer seeds a missing bar as eight empties, and
     the corridor's load ("a stored bar wins") sent [2067, 0, 0, 0, 0, 0, 0, 0] for a
     bar the panel had shown as [2067, 359, 352, ...]. The swap handler already
     stored the whole bar.
  D3 the hero's BODY acted at rank 12: its create read the ROW's ranks (`[]`), not
     the spend state, so agent_skill_rank fell to ENEMY_SKILL_RANK and Heal Party
     healed 66 per cast, where the client's own tooltip at Healing Prayers 1 read
     "Heals entire party for 33" (walk19-shot.png). An in-game raise never reached a
     body at all.

WHAT EACH SECTION RESTS ON -- every one drives the REAL code: `_handle_request_players`
with a send that encodes every message (test_attribbudget's rig), the 0x005C and
0x000F handlers themselves, and a scratch store found by --persist's own lookup.
  §1 D1: default_skillbar over an authored empty bar, and the load's 0x00DA.
  §2 D2: a slot set with no stored bar -- the store, and the next load's 0x00DA --
     for the character and for a hero whose bar is its row's; a stored bar as control.
  §3 D3: the hero body in a FIELD load: its ranks against the spend state's, the rank
     Heal Party (287, Healing Prayers) scales at, and skill_heal at that rank against
     the two numbers the run read (33 on the client's tooltip, 66 on our wire); a raise
     reaching the body; the SLICE-shaped row and the JARIN fallback as controls.

SABOTAGE HOOK: RURIK_INGAMEBUILD_AUTHSRV=<path> loads THAT copy of authsrv.py (place it
in toolkit/authsrv/ so its sibling imports resolve). Pointed at 6a7ffe04's, the
treatment checks go red and the controls stay green; the counts are in TESTS.md.

Vault-backed (the skill and attribute tables are client-table content); no socket, no
client.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import charstore                                             # noqa: E402
import agents                                                # noqa: E402

_ALT = os.environ.get("RURIK_INGAMEBUILD_AUTHSRV")
if _ALT:
    _spec = importlib.util.spec_from_file_location("authsrv", _ALT)
    authsrv = importlib.util.module_from_spec(_spec)
    sys.modules["authsrv"] = authsrv
    with contextlib.redirect_stdout(io.StringIO()):
        _spec.loader.exec_module(authsrv)
    print(f"SABOTAGE HOOK: authsrv loaded from {_ALT}")
else:
    with contextlib.redirect_stdout(io.StringIO()):
        import authsrv                                       # noqa: E402

led = checks.Ledger("a build made in-game reaches the wire, the store and the body", floor=19)   # 2026-09-25: 19 from the first green run

UUID = "55555555555555555555555555555555"
NAME = "Built In Game"
EMAIL = "ingamebuild@rurik.invalid"
BAR, ATTRS = 0x00DA, 0x003A
HERO_ID, HERO_AGENT = 6, 200
HEAL_PARTY = 287                     # Healing Prayers (13) on the client's table
HEALING = 13
MONK_ATTRS = {13, 14, 15, 16}        # the four attributes profession 3 owns
assert authsrv.GAME_SMSG_SKILLBAR_UPDATE == BAR

_SAVED_NAMES = ("PERSIST", "SPAWN_PROFESSION", "SPAWN_SECONDARY", "SECONDARY_BITS",
                "HERO_IDS", "HERO_AGENT_ID", "HERO_ROWS", "EXPLORABLE", "OUTPOST",
                "HERO_BODY", "HERO_ATTRIBUTES", "HERO", "HERO_BODY_NPC",
                "HERO_ACTIVATE", "HERO_PIPELINE_FIRST", "HERO_CHAR", "HERO_INVENTORY",
                "HERO_BAGS", "HERO_RIG_RETAIL", "PARTY_SKILLBAR")
_saved = {k: getattr(authsrv, k) for k in _SAVED_NAMES}
_saved_bar = list(authsrv.SKILLBAR)
_saved_store_dir = charstore.store_dir
base = tempfile.mkdtemp(prefix="ingamebuild-test-")


class FakeRec:
    def event(self, kind, **kw):
        pass


def quiet(fn, *a, **k):
    buf, err, out = io.StringIO(), None, None
    with contextlib.redirect_stdout(buf):
        try:
            out = fn(*a, **k)
        except Exception as e:                             # noqa: BLE001
            err = e
    return out, buf.getvalue(), err


def launch(persist, party_bar):
    """The globals main() leaves behind: SKILLBAR is default_skillbar() at startup."""
    for k in _SAVED_NAMES:
        setattr(authsrv, k, _saved[k])
    authsrv.PERSIST = persist
    authsrv.SPAWN_PROFESSION, authsrv.SPAWN_SECONDARY, authsrv.SECONDARY_BITS = 1, 0, 0
    authsrv.PARTY_SKILLBAR = party_bar
    authsrv.SKILLBAR[:] = authsrv.default_skillbar()


def write_store(player_bar=None, hero_bar=None, hero_attrs=None):
    """A fresh scratch store: one character (no ranks), and hero 6's build when
    given. `None` leaves the field ABSENT, which is the defect's precondition."""
    for f in os.listdir(base):
        os.remove(os.path.join(base, f))
    store = charstore.Store.open(EMAIL, base=base)
    row = store.ensure_character(UUID, NAME)
    row["attributes"] = []
    if player_bar is not None:
        row["skillbar"] = list(player_bar)
    else:
        row.pop("skillbar", None)
    if hero_bar is not None or hero_attrs is not None:
        h = store.ensure_hero(UUID, HERO_ID)
        if hero_bar is not None:
            h["skillbar"] = list(hero_bar)
        if hero_attrs is not None:
            h["attributes"] = [list(p) for p in hero_attrs]
    store.save()


def stored():
    s = charstore.Store.open(EMAIL, base=base)
    return s.character_skillbar(UUID), (s.hero_row(UUID, HERO_ID) or {}).get("skillbar")


def drive_load(*, town, hero_row):
    for k, v in {"OUTPOST": bool(town), "EXPLORABLE": not town,
                 "HERO": HERO_ID, "HERO_IDS": [HERO_ID], "HERO_AGENT_ID": HERO_AGENT,
                 "HERO_ROWS": {HERO_ID: dict({"hero": HERO_ID, "body": "academy_monk",
                                              "profession": 3}, **hero_row)},
                 "HERO_BODY": True, "HERO_BODY_NPC": "academy_monk", "HERO_ACTIVATE": True,
                 "HERO_PIPELINE_FIRST": True, "HERO_CHAR": True,
                 "HERO_INVENTORY": 2, "HERO_BAGS": True, "HERO_RIG_RETAIL": True}.items():
        setattr(authsrv, k, v)
    st = {"agents": {}, "char_uuid": UUID, "map_id": 148 if town else 168}
    sent = []

    def send(op, vals, label=None):
        sent.append((op, vals, label))
        authsrv.codec.encode("GAME_SMSG", op, vals)
    _r, out, err = quiet(authsrv._handle_request_players, send, st, 0,
                         threading.Event(), FakeRec())
    return sent, st, out, err


def bar_of(sent, agent):
    got = [v for op, v, _l in sent if op == BAR and v and v[0] == agent]
    return list(got[-1][1]) if got else None


def a_skill_not_in(library, bar):
    free = sorted(int(s) for s in library if int(s) > 0 and int(s) not in bar)
    return free[0] if free else None


try:
    charstore.store_dir = lambda: base
    CONTENT_BAR = [int(s) for s in agents.WORLD.get("player", "skillbar")["skills"]]
    led.ok(len(CONTENT_BAR) == 8 and all(CONTENT_BAR),
           "PREMISE: the content [player.skillbar] is eight skills -- the bar D1 loaded "
           "(the run's [351, 359, 352, 356, 322, 346, 1, 2])", f"{CONTENT_BAR}")

    # -- §1 D1: the authored empty bar -------------------------------------------
    print("\n1. an authored EMPTY player_skills is an empty bar")
    launch(False, [])
    led.ok(authsrv.default_skillbar() == [],
           "default_skillbar() with PARTY_SKILLBAR = [] is [] -- the sandbox's empty bar, "
           "not the content default", f"{authsrv.default_skillbar()}")
    sent, st, out, err = drive_load(town=True, hero_row={"attributes": [], "points": 10})
    led.ok(err is None and bar_of(sent, authsrv.PLAYER_AGENT_ID) == [0] * 8,
           "...and the load's player 0x00DA is eight empties (the run sent the content bar)",
           f"{bar_of(sent, authsrv.PLAYER_AGENT_ID)} {err!r}")
    launch(False, None)
    led.ok(authsrv.default_skillbar() == CONTENT_BAR,
           "CONTROL: no player_skills at all (None) is still the content bar",
           f"{authsrv.default_skillbar()}")
    launch(False, [322, 346])
    led.ok(authsrv.default_skillbar() == [322, 346],
           "CONTROL: an authored bar is that bar", f"{authsrv.default_skillbar()}")

    # -- §2 D2: one slot set, the whole bar stored -------------------------------
    print("\n2. a slot set with no stored bar stores the WHOLE bar the client holds")
    launch(True, None)                                   # the content bar on screen
    write_store()                                        # no stored bar: D2's precondition
    sent, st, out, err = drive_load(town=True, hero_row={"skills": [281, 276, 2]})
    shown = bar_of(sent, authsrv.PLAYER_AGENT_ID)
    led.ok(err is None and shown == CONTENT_BAR and stored()[0] is None,
           "PREMISE: a fresh store holds no bar and the load drew the content bar",
           f"{shown} {stored()} {err!r}")
    lib = authsrv.player_usable_library(st)
    pick = a_skill_not_in(lib, CONTENT_BAR)
    got = []
    _r, out, err = quiet(authsrv.handle_skillbar_skill_set,
                         [0x5C, authsrv.PLAYER_AGENT_ID, 0, pick, 0],
                         lambda op, vals, label=None: got.append((op, vals)), st, 0, FakeRec())
    want = [pick] + CONTENT_BAR[1:]
    led.ok(err is None and pick is not None and "REFUSED" not in out,
           f"the set is honoured (skill {pick} from the player's library into slot 0)",
           f"{out.strip()[-200:]} {err!r}")
    led.ok(stored()[0] == want,
           "the store holds the WHOLE bar the client now shows -- slot 0 replaced, the "
           "other seven kept (the run stored [2067, 0, 0, 0, 0, 0, 0, 0])", f"{stored()[0]}")
    sent2, _st2, _o2, err2 = drive_load(town=True, hero_row={"skills": [281, 276, 2]})
    led.ok(err2 is None and bar_of(sent2, authsrv.PLAYER_AGENT_ID) == want,
           "...and the NEXT load's 0x00DA is that bar, not one slot and seven empties",
           f"{bar_of(sent2, authsrv.PLAYER_AGENT_ID)}")

    # the hero whose bar is its row's
    hlib = authsrv.hero_usable_library(st, HERO_ID, [281, 276, 2])
    hpick = a_skill_not_in(hlib, [281, 276, 2])
    _r, out, err = quiet(authsrv.handle_skillbar_skill_set,
                         [0x5C, HERO_AGENT, 1, hpick, 0],
                         lambda op, vals, label=None: None, st, 0, FakeRec())
    led.ok(err is None and "REFUSED" not in out
           and stored()[1] == [281, hpick, 2, 0, 0, 0, 0, 0],
           "a HERO with its row's bar [281, 276, 2] and none stored: slot 1 set stores "
           "[281, X, 2, 0, ...], not [0, X, 0, ...]", f"{stored()[1]} {err!r}")

    # CONTROL: a stored bar present
    write_store(player_bar=[322, 0, 0, 0, 0, 0, 0, 0])
    sent, st, out, err = drive_load(town=True, hero_row={"skills": [281, 276, 2]})
    _r, out, err = quiet(authsrv.handle_skillbar_skill_set,
                         [0x5C, authsrv.PLAYER_AGENT_ID, 1, pick, 0],
                         lambda op, vals, label=None: None, st, 0, FakeRec())
    led.ok(err is None and stored()[0] == [322, pick, 0, 0, 0, 0, 0, 0],
           "CONTROL: over a stored bar, the set replaces its one slot (both writers agree "
           "here)", f"{stored()[0]}")

    # -- §3 D3: the hero body acts at the panel's ranks ---------------------------
    print("\n3. the hero's BODY acts at its spend state's ranks")

    def body_case(persist, hero_attrs, hero_row, raise_it=False):
        launch(persist, [])
        write_store(hero_attrs=hero_attrs)
        sent, st, out, err = drive_load(town=False, hero_row=hero_row)
        body = (st.get("agents") or {}).get(HERO_AGENT)
        if raise_it and body is not None:
            quiet(authsrv.handle_attribute_spend, [0x0F, HERO_AGENT, 0, HEALING],
                  lambda op, vals, label=None: None, st, 0, FakeRec(), True)
        rank = authsrv.agent_skill_rank(body, HEAL_PARTY) if body is not None else None
        return st, body, rank, err

    # the run's own state: a rankless sandbox hero, 13=1 spent in-game and stored
    st, body, rank, err = body_case(True, [[HEALING, 1]], {"attributes": [], "points": 10})
    led.ok(err is None and body is not None and body.get("hero") == HERO_ID,
           "PREMISE: a field load creates the hero's body (agent 200, hero 6)", f"{err!r}")
    hs = authsrv.hero_attribute_state(st, HERO_ID) if body is not None else None
    ranks = authsrv.agent_attributes(body) if body is not None else {}
    led.ok(hs is not None and hs.ranks == {HEALING: 1}
           and {a: r for a, r in ranks.items() if r} == hs.ranks
           and set(ranks) == MONK_ATTRS,
           "the body carries the spend state's 13=1 and the monk's other three attributes "
           "at 0 -- the build the panel shows", f"{ranks} vs {hs.ranks if hs else None}")
    led.ok(rank == 1 and authsrv.skill_heal(HEAL_PARTY, rank) == 33,
           "Heal Party scales at Healing Prayers 1 and heals 33 -- the client's own tooltip "
           "(walk19-shot.png); the run healed 66, rank 12", f"rank {rank}, "
           f"heal {authsrv.skill_heal(HEAL_PARTY, rank) if rank is not None else None}")
    led.ok(authsrv.skill_heal(HEAL_PARTY, authsrv.ENEMY_SKILL_RANK) == 66,
           "the defect's number, priced: skill_heal at ENEMY_SKILL_RANK (12) is the 66 "
           "the run's wire carried", f"{authsrv.skill_heal(HEAL_PARTY, authsrv.ENEMY_SKILL_RANK)}")

    st, body, rank, err = body_case(False, None, {"attributes": [], "points": 10})
    led.ok(err is None and rank == 0,
           "a rankless hero with nothing spent acts at 0, not 12 (--persist off)",
           f"rank {rank} {err!r}")
    st, body, rank, err = body_case(False, None, {"attributes": [], "points": 10},
                                    raise_it=True)
    led.ok(err is None and rank == 1 and authsrv.hero_attribute_state(st, HERO_ID).ranks
           == {HEALING: 1},
           "a raise of 13 on the hero reaches its body at once (rank 0 -> 1)",
           f"rank {rank}")

    st, body, rank, err = body_case(False, None, {"attributes": [[13, 3], [15, 2]]})
    led.ok(err is None and rank == 3,
           "CONTROL: a row with ranks and nothing stored (the SLICE shape) acts at the "
           "row's 13=3, as before", f"rank {rank} {err!r}")
    st, body, rank, err = body_case(False, None, {})
    led.ok(err is None and rank == authsrv.ENEMY_SKILL_RANK
           and authsrv.hero_borrows_player_build(st, HERO_ID),
           "CONTROL: the JARIN fallback (no `attributes` field, no budget) acts at "
           "ENEMY_SKILL_RANK, as it always has", f"rank {rank} {err!r}")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    authsrv.SKILLBAR[:] = _saved_bar
    charstore.store_dir = _saved_store_dir
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
