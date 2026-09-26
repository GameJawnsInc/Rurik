"""A stored attribute spend the launch's budget cannot pay for -- the load survives it.

    python toolkit/authsrv/test_attribbudget.py

THE DEFECT (2026-09-25, harness run 20260925T210048, the client's Code=007): the
store held ranks [[19, 2], [20, 4]] -- Hammer Mastery 2 + Swordsmanship 4 = 3 + 10
= 13 points, spent under the content row's 200-point budget -- and the run loaded
them under `--party slice`, whose budget is 10. `attribute_state` took the STORE's
ranks and the LAUNCH's budget, so available = 10 - 13 = -3, and the load's 0x0037,
whose field is a byte, raised struct.error inside send() and killed the thread.

THE CHOSEN OUTCOME (RECONSTRUCTION; attribspend.fit_ranks says why this and not a
raised or a trimmed budget): the budget binds, and a stored build over it yields to
the launch's own ranks, then to none; one loud line names the character, the stored
spend and the budget; the store is not written. The hero's 0x0037 has the same shape
and the same rule, through one resolver (hero_seed_ranks) that the spend state and
both load blocks read.

WHAT EACH SECTION RESTS ON:
  §1 fit_ranks on the client's own cost table (content `attribute_cost`): the
     defect's 13 is priced with no free parameter, then each tier and the boundary.
  §2 attribute_state over a scratch store: the overspent build, the control within
     budget, the fresh character (an empty stored list = never spent), both tiers
     past the first, and a budget outside 0x0037's byte (clamped, loudly), with
     ATTRIBUTE_POINTS_WIRE_MAX tied to the schema's own field widths.
  §3 the REAL load burst (_handle_request_players, found through --persist's own
     store lookup) on the retail rig (hero_character_block) and the legacy rig (the
     inline hero block), town and field: every 0x0037 / 0x0038 in the burst ENCODES
     through the real codec -- the actual failure mode -- the player's and the
     hero's values are the fitted ones, the 0x003A columns carry the same ranks the
     spend state holds, and the store on disk is untouched. The control within
     budget keeps the stored ranks and prints no line.

SABOTAGE HOOK: RURIK_ATTRIBBUDGET_AUTHSRV=<path> loads THAT copy of authsrv.py as
`authsrv` (siblings still from toolkit/authsrv). Pointed at the pre-fix file
(`git show 3de069a9:toolkit/authsrv/authsrv.py`), §2's and §3's overspent checks go
red and the controls stay green; the counts are in TESTS.md.

Vault-backed (the attribute tables are client-table content); no socket, no client.
"""
import contextlib
import importlib.util
import io
import json
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
import attribspend                                           # noqa: E402
import charstore                                             # noqa: E402
import agents                                                # noqa: E402

_ALT = os.environ.get("RURIK_ATTRIBBUDGET_AUTHSRV")
if _ALT:
    _spec = importlib.util.spec_from_file_location("authsrv", _ALT)
    authsrv = importlib.util.module_from_spec(_spec)
    sys.modules["authsrv"] = authsrv
    _spec.loader.exec_module(authsrv)
    print(f"SABOTAGE HOOK: authsrv loaded from {_ALT}")
else:
    import authsrv                                           # noqa: E402

led = checks.Ledger("attribute budget binds the stored ranks", floor=56)   # 2026-09-25: 56 from the first green run (the pre-fix authsrv.py reds 37 of them)

UUID = "44444444444444444444444444444444"
NAME = "Budget Fitter"
EMAIL = "attribbudget@rurik.invalid"
POINTS, AVAIL, ATTRS = 0x0037, 0x0038, 0x003A
HERO_ID, HERO_AGENT = 6, 200
assert authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS == POINTS
assert authsrv.GAME_SMSG_ATTRIBUTE_POINTS_AVAILABLE == AVAIL
assert authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTES == ATTRS

# The defect's numbers, verbatim from the run: the slice's launch ranks and
# budget ([party.slice] player_attributes / player_points, the banner's line 2)
# and the store's ranks at the time of the crash.
SLICE_RANKS = ((20, 3), (17, 2), (21, 1))
SLICE_POINTS = 10
STORED_OVER = [[19, 2], [20, 4]]
STORED_FITS = [[20, 3]]
# The hero: a monk row priced 9 of 10, a stored build of 13 (over) and of 3 (fits).
HERO_ROW_RANKS = [[13, 3], [15, 2]]
HERO_STORED_OVER = [[13, 4], [15, 2]]
HERO_STORED_FITS = [[13, 2]]

_SAVED_NAMES = ("PERSIST", "SPAWN_PROFESSION", "SPAWN_SECONDARY", "SECONDARY_BITS",
                "HERO_IDS", "HERO_AGENT_ID", "HERO_ROWS", "EXPLORABLE", "OUTPOST",
                "HERO_BODY", "HERO_ATTRIBUTES", "HERO", "HERO_BODY_NPC",
                "HERO_ACTIVATE", "HERO_PIPELINE_FIRST", "HERO_CHAR", "HERO_INVENTORY",
                "HERO_BAGS", "HERO_RIG_RETAIL")
_saved = {k: getattr(authsrv, k) for k in _SAVED_NAMES}
_saved_agents = (agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS)
_saved_store_dir = charstore.store_dir
base = tempfile.mkdtemp(prefix="attribbudget-test-")


class FakeRec:
    def event(self, kind, **kw):
        pass


def quiet(fn, *a, **k):
    """(result, stdout, exception-or-None): the load's own prints are the
    loud lines under test, so they are captured rather than discarded."""
    buf = io.StringIO()
    err = None
    out = None
    with contextlib.redirect_stdout(buf):
        try:
            out = fn(*a, **k)
        except Exception as e:                             # noqa: BLE001
            err = e
    return out, buf.getvalue(), err


def apply(cfg):
    for k, v in cfg.items():
        setattr(authsrv, k, v)


def launch(ranks=SLICE_RANKS, points=SLICE_POINTS):
    apply({k: _saved[k] for k in _SAVED_NAMES})
    apply({"PERSIST": True, "SPAWN_PROFESSION": 1, "SPAWN_SECONDARY": 0,
           "SECONDARY_BITS": 0})
    agents.PLAYER_ATTRIBUTE_RANKS = tuple(ranks)
    agents.PLAYER_ATTRIBUTE_POINTS = points


def write_store(player=None, hero=None, hero_points=None):
    """A fresh scratch store holding one character (and optionally hero 6's
    build), saved to disk so the load's own --persist lookup finds it."""
    for f in os.listdir(base):
        os.remove(os.path.join(base, f))
    store = charstore.Store.open(EMAIL, base=base)
    row = store.ensure_character(UUID, NAME)
    row["attributes"] = [list(p) for p in (player or [])]
    if hero is not None or hero_points is not None:
        h = store.ensure_hero(UUID, HERO_ID)
        if hero is not None:
            h["attributes"] = [list(p) for p in hero]
        if hero_points is not None:
            h["attribute_points"] = int(hero_points)
    store.save()
    return charstore.Store.open(EMAIL, base=base)


def on_disk():
    data = json.load(open(charstore.path_for(EMAIL, base), encoding="utf-8"))
    row = data["characters"][UUID]
    return row.get("attributes"), (row.get("heroes") or {}).get(str(HERO_ID), {}).get("attributes")


def encodes(op, vals):
    try:
        authsrv.codec.encode("GAME_SMSG", op, vals)
        return None
    except Exception as e:                                 # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def columns(vals):
    """{attribute: base rank} out of a 0x003A's column-major array."""
    cols = vals[1]
    n = len(cols) // 3
    return dict(zip(cols[:n], cols[n:2 * n]))


def rules():
    return authsrv.attribute_state({"agents": {}}).rules


def drive_load(*, town, rig, hero_row_extra=None):
    """The REAL load burst (_handle_request_players) with test_secondary's
    party rig -- hero 6 at agent 200 in the academy_monk body -- over the
    scratch store (PERSIST on, store_dir patched). Returns (sent, state,
    stdout, exception)."""
    apply({"OUTPOST": bool(town), "EXPLORABLE": not town,
           "HERO": HERO_ID, "HERO_IDS": [HERO_ID], "HERO_AGENT_ID": HERO_AGENT,
           "HERO_ROWS": {HERO_ID: dict({"hero": HERO_ID, "body": "academy_monk",
                                        "profession": 3, "skills": [105, 1, 2]},
                                       **(hero_row_extra or {}))},
           "HERO_BODY": True, "HERO_BODY_NPC": "academy_monk", "HERO_ACTIVATE": True,
           "HERO_PIPELINE_FIRST": rig == "retail", "HERO_CHAR": True,
           "HERO_INVENTORY": 2, "HERO_BAGS": True, "HERO_RIG_RETAIL": rig == "retail"})
    st = {"agents": {}, "char_uuid": UUID, "map_id": 148}
    sent = []

    def send(op, vals, label=None):
        # ENCODES, as the real send() does before it writes: the defect was
        # struct.error raised HERE, and a fake that only records values would
        # let the load "complete" on bytes no socket could carry.
        sent.append((op, vals, label))
        authsrv.codec.encode("GAME_SMSG", op, vals)
    _r, out, err = quiet(authsrv._handle_request_players, send, st, 0,
                         threading.Event(), FakeRec())
    return sent, st, out, err


def to_agent(sent, agent, op):
    return [vals for o, vals, _l in sent
            if o == op and isinstance(vals, list) and vals and vals[0] == agent]


def attribute_lines(out):
    return [ln for ln in out.splitlines() if ln.startswith("ATTRIBUTES:")]


try:
    charstore.store_dir = lambda: base
    R = rules()

    # -- §1 fit_ranks on the client's own cost table ---------------------------
    print("\n1. fit_ranks, priced on the client's cost table")
    led.ok(R.total_spent(dict(STORED_OVER)) == 13
           and R.spent_on(2) + R.spent_on(4) == 13,
           "the crash's stored ranks [[19, 2], [20, 4]] cost 3 + 10 = 13 on s_attribPoints",
           f"spent_on(2) {R.spent_on(2)}, spent_on(4) {R.spent_on(4)}")
    led.ok(R.total_spent(dict(SLICE_RANKS)) == SLICE_POINTS,
           "the slice's own ranks cost exactly its budget of 10 (6 + 3 + 1)",
           f"{R.total_spent(dict(SLICE_RANKS))}")
    got = attribspend.fit_ranks(R, 10, ("store", STORED_FITS), ("launch", SLICE_RANKS))
    led.ok(got == ({20: 3}, "store", []),
           "a stored build within the budget is the one taken, nothing refused", f"{got}")
    got = attribspend.fit_ranks(R, 10, ("store", STORED_OVER), ("launch", SLICE_RANKS))
    led.ok(got == ({20: 3, 17: 2, 21: 1}, "launch", [("store", 13)]),
           "a stored build of 13 against 10 yields to the launch's ranks, and says it cost 13",
           f"{got}")
    got = attribspend.fit_ranks(R, 5, ("store", STORED_OVER), ("launch", SLICE_RANKS))
    led.ok(got == ({}, "none", [("store", 13), ("launch", 10)]),
           "when the launch's ranks cannot pay either, no ranks: the whole budget unspent",
           f"{got}")
    got = attribspend.fit_ranks(R, 13, ("store", STORED_OVER), ("launch", SLICE_RANKS))
    led.ok(got[1] == "store" and not got[2],
           "the boundary: a spend EQUAL to the budget fits (available 0 is legal)", f"{got}")

    # -- §2 attribute_state over a scratch store --------------------------------
    print("\n2. attribute_state: the store's ranks against the launch's budget")
    launch()
    store = write_store(player=STORED_OVER)
    st2 = {"agents": {}, "char_uuid": UUID, "charstore_game": store}
    a, out, err = quiet(authsrv.attribute_state, st2)
    led.ok(err is None, "an overspent store builds the state without raising", f"{err!r}")
    led.ok(a is not None and 0 <= a.available <= a.points_total,
           "0 <= available <= points_total (the client asserts attribPointsAvail >= 0, "
           "ChCliAttrib.cpp:43)",
           f"{a.available if a else None} of {a.points_total if a else None}")
    led.ok(a is not None and a.ranks == {20: 3, 17: 2, 21: 1}
           and (a.available, a.points_total) == (0, 10),
           "the chosen outcome: the launch's ranks (17=2, 20=3, 21=1), 0 of 10 unspent",
           f"{a.ranks if a else None}")
    lines = attribute_lines(out)
    led.ok(len(lines) == 1 and NAME in lines[0] and "spend 13" in lines[0]
           and "budget is 10" in lines[0],
           "ONE loud line naming the character, the stored spend (13) and the budget (10)",
           f"{lines}")
    led.ok(on_disk()[0] == STORED_OVER,
           "the store on disk is untouched: the build comes back under a budget that fits it",
           f"{on_disk()[0]}")

    store = write_store(player=STORED_FITS)
    a, out, err = quiet(authsrv.attribute_state,
                        {"agents": {}, "char_uuid": UUID, "charstore_game": store})
    led.ok(err is None and a.ranks == {20: 3} and (a.available, a.points_total) == (4, 10)
           and not attribute_lines(out),
           "CONTROL: a stored build within budget still wins (20=3, 4 of 10), silently",
           f"{a.ranks if a else None} {attribute_lines(out)}")

    store = write_store(player=[])
    a, out, err = quiet(authsrv.attribute_state,
                        {"agents": {}, "char_uuid": UUID, "charstore_game": store})
    led.ok(err is None and a.ranks == {20: 3, 17: 2, 21: 1} and a.available == 0
           and not attribute_lines(out),
           "CONTROL: a fresh character (stored []) takes the launch's ranks, silently -- "
           "seed_ranks' never-spent rule", f"{a.ranks if a else None}")

    launch(ranks=SLICE_RANKS, points=5)
    store = write_store(player=STORED_OVER)
    a, out, err = quiet(authsrv.attribute_state,
                        {"agents": {}, "char_uuid": UUID, "charstore_game": store})
    lines = attribute_lines(out)
    led.ok(err is None and a.ranks == {} and (a.available, a.points_total) == (5, 5)
           and len(lines) == 1 and "NO ranks" in lines[0] and "spend 10" in lines[0],
           "the last tier: the launch's own 10 over a budget of 5 -> no ranks, 5 of 5 "
           "unspent, and the line says both spends", f"{a.ranks if a else None} {lines}")

    ov = json.load(open(os.path.join(os.path.dirname(HERE), "..", "schema", "messages.json"),
                        encoding="utf-8"))["channels"]["GAME_SMSG"]["messages"]
    widths = ([f["type"] for f in ov["55"]["fields"][2:]], [f["type"] for f in ov["56"]["fields"][2:]])
    led.ok(widths == (["byte", "byte"], ["byte"])
           and getattr(authsrv, "ATTRIBUTE_POINTS_WIRE_MAX", None) == 0xFF,
           "ATTRIBUTE_POINTS_WIRE_MAX is 255 because 0x0037's two value fields and "
           "0x0038's one are bytes in the schema", f"{widths}")
    launch(ranks=SLICE_RANKS, points=300)
    a, out, err = quiet(authsrv.attribute_state, {"agents": {}, "char_uuid": UUID})
    lines = attribute_lines(out)
    led.ok(err is None and a is not None and a.points_total == 255 and a.available == 245
           and len(lines) == 1 and "300" in lines[0],
           "a budget of 300 is clamped to 255 (245 unspent), loudly, not sent to the codec",
           f"{(a.available, a.points_total) if a else None} {lines}")
    launch(ranks=(), points=-5)
    a, out, err = quiet(authsrv.attribute_state, {"agents": {}, "char_uuid": UUID})
    led.ok(err is None and a is not None and (a.available, a.points_total) == (0, 0)
           and attribute_lines(out),
           "a negative budget is clamped to 0, loudly", f"{(a.available, a.points_total) if a else None}")

    # -- §3 the REAL load burst --------------------------------------------------
    print("\n3. the real load burst, over the scratch store found by --persist")
    for town, rig in ((True, "retail"), (True, "legacy"), (False, "retail")):
        where = f"{'town' if town else 'field'}/{rig}"
        launch()
        write_store(player=STORED_OVER, hero=HERO_STORED_OVER, hero_points=10)
        sent, st, out, err = drive_load(town=town, rig=rig,
                                        hero_row_extra={"attributes": HERO_ROW_RANKS})
        led.ok(err is None, f"[{where}] the load completes with a stored spend of 13 against 10",
               f"{err!r}")
        bad = [(hex(op), vals, e) for op, vals, _l in sent if op in (POINTS, AVAIL)
               for e in [encodes(op, vals)] if e]
        led.ok(sent and not bad and any(op == POINTS for op, _v, _l in sent),
               f"[{where}] EVERY 0x0037 / 0x0038 in the burst encodes through the real codec "
               f"(the crash was struct.error here)", f"{bad}")
        p37 = to_agent(sent, authsrv.PLAYER_AGENT_ID, POINTS)
        led.ok(p37 == [[authsrv.PLAYER_AGENT_ID, 0, 10]],
               f"[{where}] the player's 0x0037 is [1, 0, 10]: the launch's ranks, all 10 spent",
               f"{p37}")
        p3a = to_agent(sent, authsrv.PLAYER_AGENT_ID, ATTRS)
        led.ok(p3a and columns(p3a[-1]) == {17: 2, 20: 3, 21: 1},
               f"[{where}] ...and its 0x003A draws those same ranks",
               f"{columns(p3a[-1]) if p3a else None}")
        h37 = to_agent(sent, HERO_AGENT, POINTS)
        led.ok(h37 == [[HERO_AGENT, 1, 10]],
               f"[{where}] the hero's 0x0037 is [200, 1, 10]: its stored 13 against its stored "
               f"budget of 10 yields to the row's 13=3, 15=2 (9 spent)", f"{h37}")
        h3a = to_agent(sent, HERO_AGENT, ATTRS)
        led.ok(h3a and columns(h3a[-1]) == {13: 3, 15: 2},
               f"[{where}] ...and the hero's 0x003A draws the row's ranks",
               f"{columns(h3a[-1]) if h3a else None}")
        hs = authsrv.hero_attribute_state(st, HERO_ID)
        ps = authsrv.attribute_state(st)
        led.ok(hs.ranks == {13: 3, 15: 2} and (hs.available, hs.points_total) == (1, 10)
               and ps.ranks == {17: 2, 20: 3, 21: 1} and ps.available == 0,
               f"[{where}] the SPEND states hold what the load drew (one resolver): the panel's "
               f"next +/- is priced on the same build", f"hero {hs.ranks} {hs.available}/{hs.points_total}")
        lines = attribute_lines(out)
        led.ok(any(NAME in ln and "spend 13" in ln and "character" in ln
                   and "hero" not in ln for ln in lines)
               and any("hero 6" in ln and "spend 13" in ln
                       and "stored attribute_points is 10" in ln for ln in lines),
               f"[{where}] one loud line for the player and one for hero 6", f"{lines}")
        led.ok(on_disk() == (STORED_OVER, HERO_STORED_OVER),
               f"[{where}] the store on disk still holds both overspent builds", f"{on_disk()}")

    # The sandbox's shape (SANDBOX-B7): no stored budget, the hero ROW's
    # `points` (points_for_level) binds the stored ranks. The retail rig's
    # block and the spend state read the row's points; the legacy block never
    # has (its total is the spend, JARIN's answer), so only its bytes and its
    # ranks are asserted there.
    for rig in ("retail", "legacy"):
        where = f"row budget, town/{rig}"
        launch()
        write_store(player=STORED_FITS, hero=HERO_STORED_OVER)
        sent, st, out, err = drive_load(town=True, rig=rig,
                                        hero_row_extra={"attributes": HERO_ROW_RANKS,
                                                        "points": 10})
        h37 = to_agent(sent, HERO_AGENT, POINTS)
        h3a = to_agent(sent, HERO_AGENT, ATTRS)
        hs = authsrv.hero_attribute_state(st, HERO_ID)
        led.ok(err is None and h37 and all(encodes(POINTS, v) is None for v in h37)
               and h3a and columns(h3a[-1]) == {13: 3, 15: 2}
               and hs.ranks == {13: 3, 15: 2} and (hs.available, hs.points_total) == (1, 10),
               f"[{where}] a stored 13 against the hero row's points = 10 yields to the "
               f"row's ranks in the burst and in the spend state, and encodes",
               f"{h37} {columns(h3a[-1]) if h3a else None} {err!r}")
        if rig == "retail":
            led.ok(h37 == [[HERO_AGENT, 1, 10]],
                   f"[{where}] the retail block's 0x0037 is [200, 1, 10], the spend state's",
                   f"{h37}")
        led.ok(any("hero 6" in ln and "row's points is 10" in ln for ln in attribute_lines(out)),
               f"[{where}] the hero's line names the row's points as the budget",
               f"{attribute_lines(out)}")

    for town, rig in ((True, "retail"), (True, "legacy")):
        where = f"CONTROL {'town' if town else 'field'}/{rig}"
        launch()
        write_store(player=STORED_FITS, hero=HERO_STORED_FITS, hero_points=10)
        sent, st, out, err = drive_load(town=town, rig=rig,
                                        hero_row_extra={"attributes": HERO_ROW_RANKS})
        p37 = to_agent(sent, authsrv.PLAYER_AGENT_ID, POINTS)
        h37 = to_agent(sent, HERO_AGENT, POINTS)
        p3a = to_agent(sent, authsrv.PLAYER_AGENT_ID, ATTRS)
        h3a = to_agent(sent, HERO_AGENT, ATTRS)
        led.ok(err is None and p37 == [[1, 4, 10]] and p3a and columns(p3a[-1]) == {20: 3},
               f"[{where}] a stored build within budget still wins for the player: "
               f"[1, 4, 10], 20=3", f"{p37} {columns(p3a[-1]) if p3a else None} {err!r}")
        led.ok(h37 == [[HERO_AGENT, 7, 10]] and h3a and columns(h3a[-1]) == {13: 2},
               f"[{where}] ...and for the hero: [200, 7, 10], 13=2",
               f"{h37} {columns(h3a[-1]) if h3a else None}")
        led.ok(not attribute_lines(out), f"[{where}] no ATTRIBUTES line when nothing is over",
               f"{attribute_lines(out)}")

    # A budget outside the byte through the real burst, the player's and the hero's.
    launch(points=300)
    write_store(player=STORED_FITS, hero=HERO_STORED_FITS, hero_points=300)
    sent, st, out, err = drive_load(town=True, rig="retail",
                                    hero_row_extra={"attributes": HERO_ROW_RANKS})
    bad = [(hex(op), vals, e) for op, vals, _l in sent if op in (POINTS, AVAIL)
           for e in [encodes(op, vals)] if e]
    led.ok(err is None and not bad
           and to_agent(sent, 1, POINTS) == [[1, 249, 255]]
           and to_agent(sent, HERO_AGENT, POINTS) == [[HERO_AGENT, 252, 255]],
           "budgets of 300 (the player's row, the hero's store) load as 255 and encode",
           f"{to_agent(sent, 1, POINTS)} {to_agent(sent, HERO_AGENT, POINTS)} {bad} {err!r}")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS = _saved_agents
    charstore.store_dir = _saved_store_dir
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
