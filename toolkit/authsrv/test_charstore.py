"""charstore: the §6 persistence layer, exercised against a scratch vault.

What this is really checking, beyond round-trips: that the store REFUSES the
two inputs measured to kill a real client (an at-cap display string, a title
referencing an unseeded rank -- studies/character/RUNS.md §Run 2), that a
corrupt or wrong-version file raises instead of silently becoming defaults,
and that ensure_character never clobbers a row that already exists -- the
failure where every restart quietly resets a character is the exact disease
persistence exists to cure.

Everything runs against a temp directory passed as `base=`; the real vault is
never touched, and no server is started.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks  # noqa: E402
import charstore  # noqa: E402

led = checks.Ledger("charstore", floor=50)
base = tempfile.mkdtemp(prefix="charstore-test-")
UUID = "11111111111111111111111111111111"

try:
    # -- fresh open, seed, save, reopen ------------------------------------
    st = charstore.Store.open("loopback@rurik.invalid", base=base)
    led.ok(not os.path.exists(st.path), "open() alone writes nothing")
    row = st.ensure_character(UUID, "Test Warrior", "aa" * 37)
    led.ok(row["level"] == 1 and row["xp"] == 0,
           "ensure_character seeds a level-1 zero-xp row")
    st.save()
    led.ok(os.path.exists(st.path), "save() creates the account file")

    st2 = charstore.Store.open("loopback@rurik.invalid", base=base)
    led.ok(st2.character_by_uuid(UUID)["name"] == "Test Warrior",
           "a second open() sees the saved character")

    # -- ensure never overwrites; the settings write-back round-trips ------
    st2.character_by_uuid(UUID)["level"] = 7
    st2.ensure_character(UUID, "Test Warrior")
    led.ok(st2.character_by_uuid(UUID)["level"] == 7,
           "ensure_character never resets an existing row")
    blob = bytes(range(37))
    led.ok(st2.update_settings("Test Warrior", blob) is True,
           "update_settings matches by name")
    led.ok(charstore.Store.open("loopback@rurik.invalid", base=base)
           .character_by_uuid(UUID)["settings_blob"] == blob.hex(),
           "the client's settings blob round-trips through disk verbatim")
    led.ok(st2.update_settings("Nobody", b"\x00") is False,
           "update_settings on an unknown name says so instead of inventing")

    # -- the two measured crash rules are refused at load ------------------
    acct = st2.account()
    acct["title_ranks"]["1"] = {"value": 1000, "name": "Ruri"}
    acct["titles"]["7"] = {"points": 6000, "current_rank": 1,
                           "next_rank": 2, "max_rank": 2}
    try:
        st2.save()
        led.ok(False, "a title referencing an unseeded rank is refused")
    except ValueError as exc:
        led.ok("Array.h(587)" in str(exc),
               "a title referencing an unseeded rank is refused",
               "and the refusal cites the measured crash")
    acct["title_ranks"]["2"] = {"value": 8400, "name": "Eldr"}
    st2.save()
    led.ok(True, "the same title saves once every rank it references exists")

    acct["title_ranks"]["3"] = {"value": 1, "name": "Elder"}
    try:
        st2.save()
        led.ok(False, "a 5-char rank name is refused")
    except ValueError as exc:
        led.ok("at-cap" in str(exc) or "units" in str(exc),
               "a 5-char rank name is refused",
               "4 chars + 3 framing units = the field's admissible 7")
    del acct["title_ranks"]["3"]

    acct["factions"]["kurzick"] = {"current": 1001, "max": 31000}
    st2.save()
    led.ok(True, "faction rows save")
    try:
        acct["factions"]["zaishen"] = {"current": 0, "max": 0}
        st2.save()
        led.ok(False, "an unknown faction is refused")
    except ValueError:
        led.ok(True, "an unknown faction is refused")
    del acct["factions"]["zaishen"]

    # -- corrupt and wrong-version files raise; no silent defaults --------
    with open(st2.path, "w", encoding="utf-8") as f:
        f.write("{ not json")
    try:
        charstore.Store.open("loopback@rurik.invalid", base=base)
        led.ok(False, "corrupt JSON is refused")
    except ValueError as exc:
        led.ok("corrupt" in str(exc), "corrupt JSON is refused loudly")
    st2.save()  # restore a good file
    good = charstore.Store.open("loopback@rurik.invalid", base=base)
    good.data["version"] = 2
    try:
        charstore.validate(good.data, good.path)
        led.ok(False, "a wrong store version is refused")
    except ValueError:
        led.ok(True, "a wrong store version is refused")

    # -- the game channel's uuid lookup ------------------------------------
    other = charstore.Store.open("second@rurik.invalid", base=base)
    other.ensure_character("22" * 16, "Second")
    other.save()
    found_store, found_row = charstore.find_character(UUID, base=base)
    led.ok(found_row is not None and found_row["name"] == "Test Warrior",
           "find_character resolves a uuid across account files")
    led.ok(charstore.find_character("33" * 16, base=base) == (None, None),
           "an unknown uuid finds nothing rather than something")

    try:
        charstore.path_for("   ")
        led.ok(False, "an empty email cannot name a store")
    except ValueError:
        led.ok(True, "an empty email cannot name a store")

    # -- kill accrual: the reward lands in the store, capped where retail
    # -- caps it, and is a strict no-op when persistence is off -------------
    import authsrv  # noqa: E402  (heavy, but the accrual lives there)
    sent = []

    def fake_send(op, values, label=""):
        sent.append((op, list(values) if isinstance(values, list) else values))

    st3 = charstore.Store.open("loopback@rurik.invalid", base=base)
    st3.account()["factions"]["balthazar"] = {"current": 9990, "max": 10000}
    st3.save()
    xp0 = st3.character_by_uuid(UUID)["xp"]
    game_state = {"charstore_game": st3, "char_uuid": UUID}

    authsrv.PERSIST = False
    authsrv.accrue_kill_rewards(fake_send, game_state, 0)
    led.ok(st3.character_by_uuid(UUID)["xp"] == xp0 and not sent,
           "accrual is a strict no-op with persistence off")

    # The DEFAULT world awards no faction anywhere: no shipped map row
    # carries balthazar_per_kill, so even with a balthazar account row the
    # kill yields xp only. This is the check the first version failed --
    # it put faction gains on everything (owner's catch, 2026-08-18).
    authsrv.PERSIST = True
    try:
        authsrv.accrue_kill_rewards(fake_send, game_state, 0)
    finally:
        authsrv.PERSIST = False
    led.ok(not sent
           and st3.character_by_uuid(UUID)["xp"]
           == xp0 + authsrv.KILL_REWARD_VALUE,
           "on an unflagged map a kill yields xp and NO faction",
           "retail awards Balthazar in arena/PvP contexts only")
    xp0 = st3.character_by_uuid(UUID)["xp"]

    _real_rate = authsrv.balthazar_rate
    authsrv.balthazar_rate = lambda m: 40   # a map row that awards, faked
    authsrv.PERSIST = True
    try:
        authsrv.accrue_kill_rewards(fake_send, game_state, 0)
    finally:
        authsrv.PERSIST = False
        authsrv.balthazar_rate = _real_rate
    led.ok(st3.character_by_uuid(UUID)["xp"]
           == xp0 + authsrv.KILL_REWARD_VALUE,
           "a kill accrues KILL_REWARD_VALUE xp in the store")
    led.ok(sent == [(authsrv.GAME_SMSG_AGENT_KILL_REWARD, [11, 10]),
                    (authsrv.GAME_SMSG_AGENT_KILL_REWARD, [12, 40])],
           "current is CAPPED at the stored max, total is not",
           f"sent {sent} -- 10 of room, full 40 to total; the cap is what "
           f"0x00EA-0x00ED declare and a current past its denominator is a "
           f"bar the client has never been shown")
    back = charstore.Store.open("loopback@rurik.invalid", base=base)
    led.ok(back.account()["factions"]["balthazar"]
           == {"current": 10000, "max": 10000, "total": 40},
           "the accrued faction state is on DISK, not just in memory")
    led.ok(back.character_by_uuid(UUID)["xp"]
           == xp0 + authsrv.KILL_REWARD_VALUE,
           "the accrued xp is on disk too")

    del st3.account()["factions"]["balthazar"]
    st3.save()
    sent.clear()
    authsrv.PERSIST = True
    try:
        authsrv.accrue_kill_rewards(fake_send, game_state, 0)
    finally:
        authsrv.PERSIST = False
    led.ok(not sent and st3.character_by_uuid(UUID)["xp"]
           == xp0 + 2 * authsrv.KILL_REWARD_VALUE,
           "no balthazar row: xp still accrues, no faction delta is invented")

    # -- the skill library: two sets, account-wide and per-character --------
    #
    # WHAT THIS IS REALLY CHECKING. Retail keeps TWO libraries and this repo
    # sent one bitmap to both messages until 2026-09-15. The checks below are
    # built so that collapsing them back into one set REDDENS: the account and
    # character lists are given deliberately DIFFERENT contents, including an
    # id the character knows and the account has not unlocked, which is the
    # shape OBSERVED on capture 20260817T231139 (character 21 ids, account 19,
    # two of the character's in neither containment direction).
    #
    # The seed guard gets a negative control of its own, because the failure
    # it prevents is silent: an absent list plus a one-id unlock would write a
    # one-skill library over a 1,333-skill one and nothing would say so until
    # a player opened the panel.

    lib = charstore.Store.open("library@rurik.invalid", base=base)
    lib.ensure_character(UUID, "Library Test", "")
    lib.save()

    led.ok(lib.account_unlocked_skills() is None
           and lib.character_learned_skills(UUID) is None,
           "an unauthored library reads as None, NOT as an empty list -- the "
           "server falls back to --unlocks only on the None")

    # The seed guard: no seed, no list created, nothing persisted.
    led.ok(lib.unlock_account_skill(316) is None
           and lib.account_unlocked_skills() is None,
           "unlock with no seed REFUSES to create the account list, so a "
           "quest reward cannot shrink a flag-driven library to one skill")
    led.ok(lib.learn_character_skill(UUID, 316) is None
           and lib.character_learned_skills(UUID) is None,
           "learn with no seed refuses the same way for the character list")

    # With a seed, the whole standing library is captured plus the new id.
    led.ok(lib.unlock_account_skill(999, seed=[316, 317, 318]) is True
           and lib.account_unlocked_skills() == [316, 317, 318, 999],
           "a seeded unlock stores the STANDING library plus the new id")
    led.ok(lib.unlock_account_skill(999, seed=[1]) is False
           and lib.account_unlocked_skills() == [316, 317, 318, 999],
           "re-unlocking an id the account holds is False and the seed is "
           "ignored once a list exists")

    # The character learns a DIFFERENT set, including one the account lacks.
    lib.set_character_learned_skills(UUID, [316, 364])
    led.ok(lib.character_learned_skills(UUID) == [316, 364],
           "the character's learned list is authored independently")
    acct_now = lib.account_unlocked_skills()
    char_now = lib.character_learned_skills(UUID)
    led.ok(364 in char_now and 364 not in acct_now,
           "a character can know a skill the account never unlocked -- the "
           "20260817T231139 shape, and the reason one bitmap cannot serve both")
    led.ok(999 in acct_now and 999 not in char_now,
           "...and the account can hold one the character has not learned, so "
           "neither set contains the other")

    # Independence: writing one must not touch the other.
    lib.unlock_account_skill(400, seed=None)
    led.ok(400 in lib.account_unlocked_skills()
           and 400 not in lib.character_learned_skills(UUID),
           "an account unlock does NOT learn the skill on the character")
    lib.learn_character_skill(UUID, 401, seed=None)
    led.ok(401 in lib.character_learned_skills(UUID)
           and 401 not in lib.account_unlocked_skills(),
           "a character learn does NOT unlock the skill account-wide")

    # Both halves survive a round trip through disk.
    reread = charstore.Store.open("library@rurik.invalid", base=base)
    led.ok(reread.account_unlocked_skills() == lib.account_unlocked_skills()
           and reread.character_learned_skills(UUID)
           == lib.character_learned_skills(UUID),
           "both libraries round-trip through disk unchanged")

    # An EMPTY list is an authored answer and must not read back as absent.
    lib.set_account_unlocked_skills([])
    led.ok(charstore.Store.open("library@rurik.invalid", base=base)
           .account_unlocked_skills() == [],
           "an empty library is [] on reload, never None -- 'unlocked "
           "nothing' and 'not authored' are different answers")

    # -- what the store REFUSES ---------------------------------------------
    for bad, why in (
            ({"unlocked_skills": [0, 1]}, "skill id 0"),
            ({"unlocked_skills": [1, 1]}, "a duplicate id"),
            ({"unlocked_skills": [1, "2"]}, "a non-int id"),
            ({"unlocked_skills": {"1": True}}, "a non-list"),
    ):
        broken = charstore._fresh("bad@rurik.invalid")
        broken["account"].update(bad)
        try:
            charstore.validate(broken, "bad.json")
            led.ok(False, f"the store must refuse {why} in the account library")
        except ValueError:
            led.ok(True, f"the store refuses {why} in the account library")

    broken = charstore._fresh("bad@rurik.invalid")
    broken["characters"][UUID] = {"name": "X", "level": 1, "xp": 0,
                                  "skill_points": 0, "learned_skills": [0]}
    try:
        charstore.validate(broken, "bad.json")
        led.ok(False, "the store must refuse skill id 0 in a learned list")
    except ValueError:
        led.ok(True, "the store refuses skill id 0 in a learned list too")

    # -- the bitmap the wire actually carries -------------------------------
    #
    # A stored list has to pass the SAME crash gate the --unlocks flag passes,
    # and the round trip is the check with no free parameter: ids in, bitmap
    # out, the same ids back.
    led.ok(authsrv.ids_from_words(authsrv.words_from_ids([1, 316, 3442]))
           == [1, 316, 3442],
           "a stored id list round-trips through the wire bitmap exactly")
    try:
        authsrv.words_from_ids([authsrv.SKILL_TABLE_ROWS])
        led.ok(False, "an id past the build's skill table must be refused")
    except SystemExit:
        led.ok(True, "an id past the build's skill table is refused before it "
                     "can assert ChCliSkill.cpp on the client")
    led.ok(authsrv.words_from_ids([316])[316 // 32] == 1 << (316 % 32),
           "the bitmap sets exactly the bit its id names")


    # -- what the instance-load burst actually sends -------------------------
    #
    # The integration check, and it is built to REDDEN if the two libraries
    # are ever collapsed back into one bitmap: the account and the character
    # are given different lists, and the two resulting bitmaps must DIFFER.
    # A check that only asserted "the account bitmap is right" would pass
    # against a server that sent that same bitmap to both messages, which is
    # exactly what this repo did until 2026-09-15.

    flag_words = authsrv.words_from_ids([1, 2, 3])
    two = charstore.Store.open("burst@rurik.invalid", base=base)
    two.ensure_character(UUID, "Burst Test", "")
    two.save()

    aw, al, cw, cl = authsrv.skillunlock.resolve_library(
        two, UUID, flag_words, "flagged")
    led.ok(aw is flag_words and cw is flag_words
           and "--unlocks" in al and "--unlocks" in cl,
           "with neither list authored BOTH messages carry the --unlocks "
           "bitmap -- the pre-store behaviour, unchanged")

    two.set_account_unlocked_skills([316, 317, 999])
    aw, al, cw, cl = authsrv.skillunlock.resolve_library(
        two, UUID, flag_words, "flagged")
    led.ok(authsrv.ids_from_words(aw) == [316, 317, 999] and cw is flag_words,
           "authoring ONLY the account list moves 0x001D to the store and "
           "leaves 0x00DB on the flag -- the halves fall back independently")

    two.set_character_learned_skills(UUID, [316, 364])
    aw, al, cw, cl = authsrv.skillunlock.resolve_library(
        two, UUID, flag_words, "flagged")
    led.ok(authsrv.ids_from_words(aw) == [316, 317, 999]
           and authsrv.ids_from_words(cw) == [316, 364],
           "with both authored, each message carries its OWN library")
    led.ok(aw != cw,
           "and the two bitmaps DIFFER -- a server that sent one set to both "
           "messages would fail here, which is the point of the check")

    two.set_account_unlocked_skills([])
    aw, al, cw, cl = authsrv.skillunlock.resolve_library(
        two, UUID, flag_words, "flagged")
    led.ok(authsrv.ids_from_words(aw) == [] and "stored" in al,
           "an authored-empty account library sends an EMPTY bitmap and does "
           "NOT fall back to the flag")

finally:
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
