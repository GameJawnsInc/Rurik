"""Where a character finally persists: one JSON file per account, in the vault.

studies/character/STORAGE.md §6, built out. Until 2026-08-18 nothing about the
character survived a server restart -- every value the server sends is a
literal, a CLI flag or a content row, and the client's own
UPDATE_CHARACTER_SETTINGS write was acked and dropped (the recon that
established this is §5 of that study). This module is the §6 sketch made
real: an ACCOUNT record scoped the way retail scopes it (faction currents AND
maxima, title ranks and tracks -- account-wide per GWW and both reference
servers that model faction at all) and CHARACTER records under it (name, the
client's own char-select settings blob served back verbatim, level, xp,
skill points, attribute ranks).

SCOPE v1, deliberate: under authsrv's --persist the store drives the roster,
the settings write-back, and the character sheet. Professions, skillbar and
unlocks STAY FLAG-DRIVEN -- their CLI flags carry reskin-arc semantics this
module must not silently shadow, and argparse cannot distinguish an explicit
flag from its default. The boundary is recorded here so nobody rediscovers
it as a bug.

SCOPE v2, 2026-09-15 -- THE SKILL LIBRARY CROSSED THAT BOUNDARY, on the
owner's ask, and the sentence above is left standing because the reasoning
in it is still what governs the OTHER two. What changed for unlocks is that
the flag could not express the thing at all: retail keeps TWO libraries and
`--unlocks` is one bitmap, sent to both messages.

  * `account.unlocked_skills` -- the ACCOUNT-wide library, wire 0x001D.
    OBSERVED byte-identical on every connection of one account across the
    live corpus, whichever character and whichever map.
  * `characters[uuid].learned_skills` -- ONE character's own learned set,
    wire 0x00DB. OBSERVED on 20260817T231139 as 21 ids against the same
    account's 19, with TWO of them (364, 384) in no account set: a
    character can know a skill the account never unlocked, so neither set
    contains the other and one bitmap cannot stand in for both.

THE ARGPARSE PROBLEM IS SOLVED BY ABSENCE, NOT BY PRECEDENCE. Each list is
independently optional. Absent means "not authored" and the --unlocks flag
still answers for that half, so every run predating this change is
byte-identical; present means the store answers and the flag is ignored for
it. An EMPTY list is a real authored answer -- an account that has unlocked
nothing -- and is not the same as absence. That distinction is why the
mutators refuse to CREATE a list from a single id without a seed: turning
absence into `[40]` because a quest granted skill 40 would replace a
1,333-skill library with a 1-skill one at the next login.

A FLAT FILE IS ENOUGH. One JSON per account under vault/state/characters/
(the vault is personal data and never leaves the machine; the server path
stays stdlib-only). Writes are atomic -- tmp then os.replace -- because a
half-written store that half-loads is worse than either whole state.

TWO PROCESSES WRITE ONE FILE, AND A STALE SNAPSHOT MUST NOT WIN (2026-09-15,
studies/heroes/RUN-HEROLIB.md §10). The auth process opens a Store at login
and holds it for the whole session; the game process opens its own at every
instance load. The client sends UPDATE_CHARACTER_SETTINGS at exactly the
moment a game connection ends -- 319 of 319 in the harness corpus sit within
2 s of a game connection's edge, none mid-session -- and the auth arm
persisted it by saving its login-time snapshot over the file. RUN-HEROLIB's
twelve hero edits, on disk at 00:34:09Z, were gone at 00:34:09Z: the next
game connection opened the file in the same second and read the seed. Three
things guard it now:
  * every save() prints one line naming the path, the caller and the
    mtime before and after -- the instrument the study asked for;
  * save() REFUSES, loudly, when the file changed since this object last
    read or wrote it (StaleWrite is printed, not raised: a raise on the
    game thread stops the world for the rest of the session, and the
    refusal already loses nothing that is on disk);
  * update_settings() re-reads the file before applying the blob, so the
    auth roster's write is a read-modify-write of the freshest state.
The mutators all save at once, so a Store holds unsaved data only between
a caller's direct row edit and its save(); those callers are the game
process's per-connection store, which is that process's only writer.

TWO CRASH RULES ARE ENFORCED AT LOAD, NOT AT SEND (both MEASURED 2026-08-18,
studies/character/RUNS.md §Run 2):
  * A title/rank display string rides a string16(8) wire field that admits
    AT MOST 7 UTF-16 units, and template framing spends 3 -- so names here
    are capped at 4 characters. An at-cap string is an instant client
    hangup (Code=007, no assert).
  * Every rank id a title references must exist in title_ranks. A 0x00F6
    referencing an unseeded rank is accepted silently and kills the client
    at first render -- Assertion: index < m_count, Array.h(587).
A store violating either is REFUSED loudly. Refuse-to-guess applies to the
whole file: corrupt JSON, a wrong version, a malformed row -- all raise with
the path named. Falling back to defaults on a bad store would turn a typo
into a silently different character.
"""

import json
import os
import re
import sys
import time

_TOOLKIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _TOOLKIT not in sys.path:
    sys.path.insert(0, _TOOLKIT)
from vaultpath import vault_path  # noqa: E402

STORE_VERSION = 1
# string16(8) admits 7 units on receive; template framing costs 3 of them.
MAX_NAME_CHARS = 4
FACTIONS = ("kurzick", "luxon", "balthazar", "imperial")
# 0x00DA's array is eight wide; the client asserts
# `hotKey < arrsize(hotKeyState->hotKey)` (ChCliSkill.cpp:681) past it.
HERO_BAR_SLOTS = 8
# s_heroClientData's row count (studies/heroes/FINDINGS.md 2). Index 0 is
# not a hero, the same way skill id 0 is not a skill.
MAX_HERO_INDEX = 39
# Mirrored from attribcolumns.py rather than imported: that module pulls in
# `agents` (the content store) and this one must stay loadable on a bare
# machine with no content at all. Both cite the same client asserts, and
# test_charstore checks the two agree so the copies cannot drift.
CHAR_ATTRIBS = 51
ATTRIBUTE_RANK_MAX = 12


def store_dir():
    return vault_path("state", "characters")


def path_for(email, base=None):
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", (email or "").strip().lower())
    if not slug:
        raise ValueError("charstore: an empty email cannot name a store file")
    return os.path.join(base or store_dir(), slug + ".json")


def _fresh(email):
    return {
        "version": STORE_VERSION,
        "email": email,
        "account": {"factions": {}, "title_ranks": {}, "titles": {}},
        "characters": {},
    }


def _refuse(path, why):
    raise ValueError(f"charstore: {path}: {why}")


def _validate_skill_ids(path, where, ids):
    """A stored skill-id list: ints, all >= 1, no duplicates.

    STRUCTURAL ONLY, and the boundary is deliberate. The other crash rule --
    an id past the end of THIS BUILD's skill table asserts in the client's
    ChCliSkill.cpp the moment the Skills panel opens -- is build-specific
    (3,443 rows on 38797), and a store file outlives the build it was
    authored against. That bound is enforced where the bitmap is BUILT, by
    skillunlock.build_unlock_bitmap, which already refuses it with the assert
    named and is tested for the refusal. Duplicating a build constant here
    would give the two copies somewhere to disagree.

    Id 0 is refused HERE as well as there, because it is not build-specific
    and it is the most expensive bit in this repo's history: bit 0 set means
    the client's find-next-set-bit iterator enumerates id 0 and asserts
    `*skill` (ChCliSkill.cpp:1022) the instant the panel opens. Six client
    sessions were spent on it. See skillunlock.refuse_skill_zero.
    """
    if not isinstance(ids, list):
        _refuse(path, f"{where}: must be a list of skill ids, not "
                      f"{type(ids).__name__}")
    for sid in ids:
        if isinstance(sid, bool) or not isinstance(sid, int):
            _refuse(path, f"{where}: skill id {sid!r} is not an int")
        if sid <= 0:
            _refuse(path, f"{where}: skill id {sid} -- ids start at 1, and a "
                          f"set bit 0 asserts `*skill` (ChCliSkill.cpp:1022) "
                          f"the moment the Skills panel opens")
    if len(set(ids)) != len(ids):
        dupes = sorted({s for s in ids if ids.count(s) > 1})
        _refuse(path, f"{where}: duplicate skill ids {dupes} -- the wire "
                      f"carries a BITMAP, so a duplicate is a silent no-op "
                      f"that makes the file disagree with what is sent")


def _validate_hero_bar(path, where, bar):
    """A hero's 8 slots. UNLIKE a library list, 0 is legal and means EMPTY.

    The two shapes are validated separately on purpose. A library is a SET and
    a 0 in it would set bit 0 of a bitmap, which asserts the client; a bar is a
    POSITIONAL array of 8 slots where 0 is how retail spells an empty one --
    OBSERVED, capture 20260914T005758: Koss's bar is
    [322, 382, 348, 1, 385, 346, 0, 2], with slot 6 empty and slot 7 occupied,
    so an empty slot is not merely trailing padding and cannot be dropped.
    """
    if not isinstance(bar, list):
        _refuse(path, f"{where}: skillbar must be a list of slots, not "
                      f"{type(bar).__name__}")
    if len(bar) > HERO_BAR_SLOTS:
        _refuse(path, f"{where}: {len(bar)} slots, the bar has "
                      f"{HERO_BAR_SLOTS} -- 0x00DA's array is eight wide and "
                      f"the client asserts `hotKey < arrsize(hotKeyState->"
                      f"hotKey)` (ChCliSkill.cpp:681) on anything past it")
    for sid in bar:
        if isinstance(sid, bool) or not isinstance(sid, int):
            _refuse(path, f"{where}: slot value {sid!r} is not an int")
        if sid < 0:
            _refuse(path, f"{where}: slot value {sid} is negative; 0 is the "
                          f"empty slot and ids start at 1")
    occupied = [s for s in bar if s]
    if len(set(occupied)) != len(occupied):
        _refuse(path, f"{where}: the same skill occupies two slots "
                      f"{sorted({s for s in occupied if occupied.count(s) > 1})}"
                      f" -- the client's own equip guard is "
                      f"`targetSkill != sourceSkill` (ChCliSkill.cpp:515)")


def _validate_rank_pairs(path, where, pairs):
    if not all(isinstance(p, list) and len(p) == 2
               and all(isinstance(v, int) and not isinstance(v, bool)
                       for v in p) for p in pairs):
        _refuse(path, f"{where}: attributes must be [attribute_id, rank] "
                      f"int pairs")
    for aid, rank in pairs:
        if not 0 <= aid < CHAR_ATTRIBS:
            _refuse(path, f"{where}: attribute id {aid} outside the client's "
                          f"{CHAR_ATTRIBS}-row s_attrib table; its writer "
                          f"asserts `attrib < arrsize(attribState->attrib)` "
                          f"(ChCliAttrib.cpp:249)")
        if not 0 <= rank <= ATTRIBUTE_RANK_MAX:
            _refuse(path, f"{where}: rank {rank} for attribute {aid} is "
                          f"outside 0..{ATTRIBUTE_RANK_MAX}; ArenaNet's own "
                          f"cap is AcctTemplate:441 and CharData:202 bounds "
                          f"the s_attribPoints lookup at 0..12")
    ids = [a for a, _r in pairs]
    if len(set(ids)) != len(ids):
        _refuse(path, f"{where}: attribute {sorted({a for a in ids if ids.count(a) > 1})}"
                      f" appears twice -- each 0x003A triple WRITES its slot, "
                      f"so a duplicate silently means last-one-wins")


def _validate_heroes(path, who, heroes):
    """One character's heroes: index -> {skills, skillbar, attributes, ...}.

    HEROES BELONG TO THE CHARACTER, not to the account, and that is retail's
    scoping rather than a choice made here: each character owns its own copy
    of a hero with its own build. The ACCOUNT's contribution is the unlock
    library every hero draws on (see account unlocked_skills) -- OBSERVED,
    capture 20260914T005758: Koss's bar carries 346, which is in the account's
    0x001D set, absent from his own 0x0073 skill list, and absent from the
    CHARACTER's 0x00DB set.
    """
    if not isinstance(heroes, dict):
        _refuse(path, f"character {who}: heroes must be an object keyed by "
                      f"hero index")
    for hid, row in heroes.items():
        if not str(hid).isdigit() or not 1 <= int(hid) <= MAX_HERO_INDEX:
            _refuse(path, f"character {who}: hero index {hid!r} outside "
                          f"1..{MAX_HERO_INDEX} (s_heroClientData's rows; "
                          f"index 0 is not a hero)")
        if not isinstance(row, dict):
            _refuse(path, f"character {who}: hero {hid} must be an object")
        where = f"character {who} hero {hid}"
        if "skills" in row:
            _validate_skill_ids(path, f"{where} skills", row["skills"])
        if "skillbar" in row:
            _validate_hero_bar(path, where, row["skillbar"])
        if "attributes" in row:
            _validate_rank_pairs(path, where, row["attributes"])
        for key in ("level", "attribute_points"):
            if key in row and (isinstance(row[key], bool)
                               or not isinstance(row[key], int)
                               or row[key] < 0):
                _refuse(path, f"{where}: {key} must be a non-negative int")
        if "disabled_slots" in row:
            m = row["disabled_slots"]
            if isinstance(m, bool) or not isinstance(m, int) or not 0 <= m <= 0xFF:
                _refuse(path, f"{where}: disabled_slots must be an int 0..255 "
                              f"(the hero panel's suppress mask, one bit per "
                              f"slot; DESKWORK-D1 step 6)")


def validate(data, path):
    """Refuse a store that would lie to the roster or crash the client."""
    if data.get("version") != STORE_VERSION:
        _refuse(path, f"version {data.get('version')!r}, this code speaks "
                      f"{STORE_VERSION}; migrate deliberately, do not guess")
    acct = data.get("account")
    chars = data.get("characters")
    if not isinstance(acct, dict) or not isinstance(chars, dict):
        _refuse(path, "account/characters missing or not objects")
    ranks = acct.get("title_ranks", {})
    for rid, rk in ranks.items():
        if not str(rid).isdigit():
            _refuse(path, f"title rank id {rid!r} is not an integer")
        if not isinstance(rk.get("value"), int):
            _refuse(path, f"rank {rid}: value must be an int")
        name = rk.get("name", "")
        if not isinstance(name, str) or not (1 <= len(name) <= MAX_NAME_CHARS):
            _refuse(path, f"rank {rid}: name {name!r} must be 1.."
                          f"{MAX_NAME_CHARS} chars -- template framing spends "
                          f"3 of the wire field's 7 admissible units, and an "
                          f"at-cap string HANGS UP the client (RUNS.md Run 2)")
    for tid, t in acct.get("titles", {}).items():
        if not str(tid).isdigit() or not 0 <= int(tid) <= 47:
            _refuse(path, f"title id {tid!r} outside the client's 48-row "
                          f"table (s_titleClientData)")
        if not isinstance(t.get("points"), int):
            _refuse(path, f"title {tid}: points must be an int")
        for key in ("current_rank", "next_rank", "max_rank"):
            rid = t.get(key)
            if str(rid) not in ranks:
                _refuse(path, f"title {tid}: {key}={rid!r} references a rank "
                              f"title_ranks does not define -- unseeded rank "
                              f"ids are silent on receive and KILL the client "
                              f"at render (Array.h(587); RUNS.md Run 2)")
    for fac, row in acct.get("factions", {}).items():
        if fac not in FACTIONS:
            _refuse(path, f"faction {fac!r}; the four are {FACTIONS}")
        if not isinstance(row.get("current"), int) \
                or not isinstance(row.get("max"), int):
            _refuse(path, f"faction {fac}: current/max must be ints")
        if "total" in row and not isinstance(row["total"], int):
            _refuse(path, f"faction {fac}: total must be an int when present")
    # The ACCOUNT-WIDE skill library -- what this account has ever unlocked,
    # shared by every character on it. OBSERVED on the wire as 0x001D
    # PVP_UPDATE_UNLOCKED_SKILLS: byte-identical across every connection of
    # one account regardless of which character or map, on 6 live captures.
    # ABSENT is not the same as EMPTY: absent means "not authored here" and
    # the server falls back to its --unlocks flag, which is what keeps every
    # pre-existing run byte-identical. An empty list means "this account has
    # unlocked nothing" and is sent as such.
    if "unlocked_skills" in acct:
        _validate_skill_ids(path, "account unlocked_skills",
                            acct["unlocked_skills"])
    for uuid_hex, row in chars.items():
        if len(uuid_hex) != 32 or any(c not in "0123456789abcdef"
                                      for c in uuid_hex.lower()):
            _refuse(path, f"character key {uuid_hex!r} is not a 16-byte uuid "
                          f"in hex")
        if not isinstance(row.get("name"), str) or not row["name"]:
            _refuse(path, f"character {uuid_hex}: name missing")
        for key in ("level", "xp", "skill_points"):
            if not isinstance(row.get(key), int):
                _refuse(path, f"character {row['name']!r}: {key} must be an "
                              f"int")
        attrs = row.get("attributes", [])
        if not all(isinstance(p, list) and len(p) == 2
                   and all(isinstance(v, int) for v in p) for p in attrs):
            _refuse(path, f"character {row['name']!r}: attributes must be "
                          f"[attribute_id, rank] int pairs")
        # THIS CHARACTER's learned skills -- a SEPARATE set from the account
        # library above, and the separation is retail's, not ours. OBSERVED,
        # capture 20260817T231139: the character's 0x00DB carries 21 ids while
        # the same account's 0x001D carries 19, and TWO of the character's
        # (364, 384) are absent from the account set -- so a character can
        # know a skill the account has not unlocked, and neither set contains
        # the other. Same absent-vs-empty rule as the account list.
        if "learned_skills" in row:
            _validate_skill_ids(path, f"character {row['name']!r} "
                                      f"learned_skills", row["learned_skills"])
        if "heroes" in row:
            _validate_heroes(path, repr(row["name"]), row["heroes"])
        if "kicked_heroes" in row:
            kk = row["kicked_heroes"]
            if not isinstance(kk, list) or not all(
                    isinstance(h, int) and 1 <= h <= MAX_HERO_INDEX
                    for h in kk):
                _refuse(path, f"character {row['name']!r}: kicked_heroes must "
                              f"be a list of hero indices 1..{MAX_HERO_INDEX} "
                              f"(SANDBOX-N2; index 0 is not a hero)")
        if "skillbar" in row:
            _validate_hero_bar(path, f"character {row['name']!r}",
                               row["skillbar"])
        if "item_locations" in row:
            locs = row["item_locations"]
            if not isinstance(locs, dict):
                _refuse(path, f"character {row['name']!r}: item_locations must "
                              f"be an object keyed by item id (DESKWORK-D1 step 8)")
            for iid, cell in locs.items():
                if (not str(iid).isdigit() or not isinstance(cell, list)
                        or len(cell) != 2
                        or not all(isinstance(v, int) and not isinstance(v, bool)
                                   and v >= 0 for v in cell)):
                    _refuse(path, f"character {row['name']!r}: item_locations["
                                  f"{iid!r}] must be [bag, slot], two non-negative "
                                  f"ints under an integer item id")
        blob = row.get("settings_blob", "")
        if blob:
            try:
                bytes.fromhex(blob)
            except ValueError:
                _refuse(path, f"character {row['name']!r}: settings_blob is "
                              f"not hex")
    return data


class StaleWrite(ValueError):
    """A save() that would have overwritten another writer's data.

    Constructed and PRINTED by save(), never raised by it (module docstring
    says why); exposed so a caller that wants to raise can `raise` the
    instance save() hands back through `last_stale`.
    """


# Every save prints `[charstore] SAVE ...`. The line is the instrument
# RUN-HEROLIB §6.5 asked for -- path, caller, mtime before and after -- and
# it is on by default because a store write is rare (a dozen per run) and
# the one time it mattered nobody could say which process had written last.
TRACE = True


def _disk_sig(path):
    """(mtime_ns, size) of the file on disk, or None if it does not exist."""
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return None
    return (st.st_mtime_ns, st.st_size)


def _fmt_sig(sig):
    if sig is None:
        return "absent"
    return time.strftime("%H:%M:%S", time.gmtime(sig[0] / 1e9)) \
        + f".{(sig[0] // 1000) % 1000000:06d}Z/{sig[1]}B"


def _caller():
    """`file:line in func` of the first frame outside this module."""
    here = os.path.abspath(__file__)
    frame = sys._getframe(1)
    while frame is not None:
        fn = os.path.abspath(frame.f_code.co_filename)
        if fn != here:
            return (f"{os.path.basename(fn)}:{frame.f_lineno} "
                    f"in {frame.f_code.co_name}")
        frame = frame.f_back
    return "?"


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        _refuse(path, f"corrupt JSON ({exc}); fix or delete it -- "
                      f"defaults will not be silently substituted")
    return validate(data, path)


class Store:
    """One account's persistent state. Load with open(); every write saves.

    `sig` is what the file on disk looked like when this object last read
    or wrote it; save() compares against it and refuses a stale overwrite.
    """

    def __init__(self, path, data, sig=None):
        self.path = path
        self.data = data
        self._sig = sig if sig is not None else _disk_sig(path)
        self.last_stale = None

    @classmethod
    def open(cls, email, base=None):
        path = path_for(email, base)
        if not os.path.exists(path):
            return cls(path, _fresh(email), sig=None)
        # The signature is taken BEFORE the read on purpose: a write that
        # lands between the two makes the next save() refuse (a false stale,
        # which loses nothing on disk) rather than pass (a missed one).
        sig = _disk_sig(path)
        return cls(path, _read(path), sig=sig)

    def reload(self):
        """Re-read the file if another writer changed it. True if it did.

        Discards this object's unsaved edits -- see the module docstring for
        why no live caller holds any across another process's write.
        """
        sig = _disk_sig(self.path)
        if sig is None or sig == self._sig:
            return False
        self.data = _read(self.path)
        self._sig = sig
        return True

    def save(self):
        """Write the file. True if written; False (and a loud line) if the
        file changed under this object since it last read or wrote it."""
        validate(self.data, self.path)  # never persist what open() would refuse
        caller = _caller()
        before = _disk_sig(self.path)
        if before != self._sig:
            self.last_stale = StaleWrite(
                f"charstore: STALE WRITE REFUSED -- {self.path} changed on "
                f"disk since this Store read it (had {_fmt_sig(self._sig)}, "
                f"disk now {_fmt_sig(before)}); another writer's data would "
                f"have been overwritten by {caller}. Call reload() first.")
            print(f"[charstore] {self.last_stale}", flush=True)
            return False
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)
        self._sig = _disk_sig(self.path)
        if TRACE:
            print(f"[charstore] SAVE {self.path} by {caller} -- mtime "
                  f"{_fmt_sig(before)} -> {_fmt_sig(self._sig)}", flush=True)
        return True

    def account(self):
        return self.data["account"]

    def characters(self):
        return list(self.data["characters"].items())

    def character_by_name(self, name):
        for uuid_hex, row in self.data["characters"].items():
            if row["name"] == name:
                return uuid_hex, row
        return None

    def character_by_uuid(self, uuid_hex):
        return self.data["characters"].get((uuid_hex or "").lower())

    def ensure_character(self, uuid_hex, name, settings_blob_hex=""):
        """Seed a row if absent; never overwrite one that exists."""
        row = self.data["characters"].setdefault(uuid_hex.lower(), {
            "name": name,
            "settings_blob": settings_blob_hex,
            "level": 1, "xp": 0, "skill_points": 0,
            "attributes": [],
        })
        return row

    def update_settings(self, name, blob):
        """The client's own char-select settings write, persisted verbatim.

        Returns True if a row matched. The blob is the client's; it is not
        parsed here -- serving back exactly what the client saved is the one
        persistence behaviour that cannot invent anything.

        READ-MODIFY-WRITE, because the caller is the auth process holding a
        login-time snapshot and this message arrives when a game connection
        has just closed (RUN-HEROLIB §10): without the reload, the write
        put the seed back over a whole session's edits.
        """
        self.reload()
        found = self.character_by_name(name)
        if found is None:
            return False
        _, row = found
        row["settings_blob"] = bytes(blob).hex()
        row["last_saved_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())
        self.save()
        return True

    # ---- the skill library: account-wide unlocks + per-character learned ----
    #
    # TWO SETS, because retail keeps two and the wire shows both. The account
    # list rides 0x001D and is shared by every character; the character list
    # rides 0x00DB and is that character's own. Neither contains the other
    # (capture 20260817T231139: 21 character ids, 19 account ids, 2 of the
    # character's in neither direction of containment).
    #
    # EVERY READER GETS None FOR AN ABSENT LIST, and callers must treat that
    # as "not authored -- fall back to the server's --unlocks flag" rather
    # than as an empty library. An empty list is a real, authored answer.

    def account_unlocked_skills(self):
        """The account-wide unlocked ids, sorted -- or None if not authored."""
        ids = self.account().get("unlocked_skills")
        return None if ids is None else sorted(ids)

    def set_account_unlocked_skills(self, ids):
        """Author the account library outright. Saves."""
        self.account()["unlocked_skills"] = sorted({int(s) for s in ids})
        self.save()
        return self.account()["unlocked_skills"]

    def unlock_account_skill(self, skill_id, seed=None):
        """Account-wide unlock. Returns True if this is NEW to the account.

        `seed` EXISTS TO PREVENT A SILENT SHRINK, and it is the whole reason
        this is not a two-line method. A server running `--unlocks corpus`
        sends 1,333 ids from the flag while the store holds no list at all.
        If the first in-game unlock simply created `unlocked_skills = [40]`,
        the account would come back next login with ONE skill instead of
        1,333 -- a catastrophic loss written by a routine quest reward, and
        invisible until a player opened the panel.

        So: when the list is absent, the caller must hand over the set that
        is CURRENTLY in force, and the stored list is created as that set
        plus the new id. A caller with nothing to seed passes None and gets
        None back, meaning "not persisted, still flag-driven" -- never a
        truncated library.
        """
        skill_id = int(skill_id)
        ids = self.account().get("unlocked_skills")
        if ids is None:
            if seed is None:
                return None
            ids = sorted({int(s) for s in seed})
            self.account()["unlocked_skills"] = ids
        if skill_id in ids:
            return False
        ids.append(skill_id)
        ids.sort()
        self.save()
        return True

    def character_learned_skills(self, uuid_hex):
        """This character's learned ids, sorted -- or None if not authored."""
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        ids = row.get("learned_skills")
        return None if ids is None else sorted(ids)

    def set_character_learned_skills(self, uuid_hex, ids):
        """Author one character's learned list outright. Saves."""
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        row["learned_skills"] = sorted({int(s) for s in ids})
        self.save()
        return row["learned_skills"]

    def learn_character_skill(self, uuid_hex, skill_id, seed=None):
        """Per-character learn. Returns True if NEW to this character.

        Same absent-list contract and the same `seed` guard as
        unlock_account_skill -- see that docstring for why the seed is not
        optional in spirit. None means "not persisted".
        """
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        skill_id = int(skill_id)
        ids = row.get("learned_skills")
        if ids is None:
            if seed is None:
                return None
            ids = sorted({int(s) for s in seed})
            row["learned_skills"] = ids
        if skill_id in ids:
            return False
        ids.append(skill_id)
        ids.sort()
        self.save()
        return True

    # ---- the PLAYER's own eight slots ---------------------------------------
    #
    # Same shape as a hero's bar and validated by the same function, because
    # 0x00DA and 0x005C are AGENT-keyed and do not care which body they name.
    # What differs is the library each draws on: a player's bar may hold what
    # the CHARACTER has learned, a hero's may not (herolib's docstring).

    def character_skillbar(self, uuid_hex):
        row = self.character_by_uuid(uuid_hex)
        return None if row is None else row.get("skillbar")

    def set_character_skillbar(self, uuid_hex, bar):
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        bar = [int(s) for s in bar][:HERO_BAR_SLOTS]
        bar += [0] * (HERO_BAR_SLOTS - len(bar))
        row["skillbar"] = bar
        self.save()
        return bar

    def set_character_bar_slot(self, uuid_hex, slot, skill_id):
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        slot = int(slot)
        if not 0 <= slot < HERO_BAR_SLOTS:
            raise ValueError(
                f"slot {slot} outside 0..{HERO_BAR_SLOTS - 1}; the client's "
                f"own guard is `hotKey < arrsize(hotKeyState->hotKey)` "
                f"(ChCliSkill.cpp:681)")
        bar = list(row.get("skillbar") or [0] * HERO_BAR_SLOTS)
        bar += [0] * (HERO_BAR_SLOTS - len(bar))
        bar[slot] = int(skill_id)
        row["skillbar"] = bar
        self.save()
        return bar

    # ---- heroes: owned BY THE CHARACTER, drawing on the ACCOUNT's library ---
    #
    # Retail's scoping, not a choice made here. Each character owns its own
    # copy of a hero with its own build, so these hang off the character row;
    # what the ACCOUNT contributes is the unlock library every hero draws on.
    # OBSERVED, capture 20260914T005758: Koss's bar carries 346, which is in
    # the account's 0x001D set, absent from his own 0x0073 skill list, and
    # absent from the CHARACTER's 0x00DB set -- so a hero's usable library is
    # (his own skills) UNION (the account's unlocks), and NOT the character's
    # learned set. herolib.hero_library is where that union is computed.

    def heroes(self, uuid_hex):
        """{hero_index: row} for one character, or {} -- never None.

        Unlike the two skill libraries there is no absent-vs-empty question
        here: a character with no authored heroes simply has none, and the
        server's --hero flags still decide whether any are spawned at all.
        """
        row = self.character_by_uuid(uuid_hex)
        return {} if row is None else dict(row.get("heroes") or {})

    def hero_row(self, uuid_hex, hero_index):
        return self.heroes(uuid_hex).get(str(int(hero_index)))

    def ensure_hero(self, uuid_hex, hero_index):
        """The hero's row, created empty if absent. Does NOT save."""
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        return row.setdefault("heroes", {}).setdefault(
            str(int(hero_index)), {})

    def set_hero_skills(self, uuid_hex, hero_index, ids):
        """The hero's OWN skill list -- 0x0073 HERO_INFO field 7."""
        hero = self.ensure_hero(uuid_hex, hero_index)
        if hero is None:
            return None
        hero["skills"] = sorted({int(s) for s in ids})
        self.save()
        return hero["skills"]

    def hero_skillbar(self, uuid_hex, hero_index):
        hero = self.hero_row(uuid_hex, hero_index)
        return None if hero is None else hero.get("skillbar")

    def set_hero_skillbar(self, uuid_hex, hero_index, bar):
        """The hero's eight slots, 0 meaning empty. Padded to eight."""
        hero = self.ensure_hero(uuid_hex, hero_index)
        if hero is None:
            return None
        bar = [int(s) for s in bar][:HERO_BAR_SLOTS]
        bar += [0] * (HERO_BAR_SLOTS - len(bar))
        hero["skillbar"] = bar
        self.save()
        return bar

    def set_hero_bar_slot(self, uuid_hex, hero_index, slot, skill_id):
        """One slot, the way 0x005C writes one slot. Returns the whole bar.

        The bar is created as eight empties if the hero has none, which is
        SAFE here in a way the skill-library mutators were not: a bar is
        positional and eight slots wide whatever happens, so there is no
        standing set to shrink. The libraries needed a seed; this does not.
        """
        hero = self.ensure_hero(uuid_hex, hero_index)
        if hero is None:
            return None
        slot = int(slot)
        if not 0 <= slot < HERO_BAR_SLOTS:
            raise ValueError(
                f"slot {slot} outside 0..{HERO_BAR_SLOTS - 1}; the client's "
                f"own guard is `hotKey < arrsize(hotKeyState->hotKey)` "
                f"(ChCliSkill.cpp:681)")
        bar = list(hero.get("skillbar") or [0] * HERO_BAR_SLOTS)
        bar += [0] * (HERO_BAR_SLOTS - len(bar))
        bar[slot] = int(skill_id)
        hero["skillbar"] = bar
        self.save()
        return bar

    def hero_attributes(self, uuid_hex, hero_index):
        hero = self.hero_row(uuid_hex, hero_index)
        return None if hero is None else hero.get("attributes")

    def set_hero_attributes(self, uuid_hex, hero_index, pairs):
        hero = self.ensure_hero(uuid_hex, hero_index)
        if hero is None:
            return None
        hero["attributes"] = [[int(a), int(r)] for a, r in sorted(pairs)]
        self.save()
        return hero["attributes"]

    # ---- kicked heroes: owned but not in the party (SANDBOX-N2) ----------
    # A kicked hero stays OWNED -- retail keeps sending its 0x0073 HERO_INFO in
    # every load -- but leaves the party, so it is not activated (0x0072) and
    # gets no roster row (0x01C2). OBSERVED on 20260916T150306: after the kick
    # of hero 6, the tape's next two loads carry 0x0073 for hero 6 and neither
    # 0x0072 nor 0x01C2 (studies/cmsg/FINDINGS.md DESKWORK-D1). Persisted so the kick
    # holds across a zone. This is a CHARACTER-scoped set, like heroes, because
    # party membership is the character's, not the account's.
    def kicked_heroes(self, uuid_hex):
        """The hero indices this character has kicked -- [] when none."""
        row = self.character_by_uuid(uuid_hex)
        return list(row.get("kicked_heroes") or []) if row is not None else []

    def set_hero_kicked(self, uuid_hex, hero_index, kicked=True):
        """Add (or, kicked=False, remove) a hero from the kicked set; saves."""
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        have = set(int(h) for h in (row.get("kicked_heroes") or []))
        if kicked:
            have.add(int(hero_index))
        else:
            have.discard(int(hero_index))
        row["kicked_heroes"] = sorted(have)
        self.save()
        return row["kicked_heroes"]

    # ---- suppressed hero skills (DESKWORK-D1 step 6) ----------------------
    # The hero panel's suppress click (c2s 0x0019, hold the suppress key and
    # click a skill) toggles one bit of an 8-bit mask, bit = panel slot, and
    # the client draws it from s2c 0x0065 [agent, mask] -- the byte retail's
    # load block sends as 0 for every hero (8 of 8 on the live corpus). Per
    # HERO, per CHARACTER, like the bar it indexes: slot N means slot N of
    # THIS hero's `skillbar` as the panel shows it (authsrv.hero_panel_bar_ids).
    def hero_disabled_slots(self, uuid_hex, hero_index):
        """The hero's suppress mask, 0 when none is stored."""
        hero = self.hero_row(uuid_hex, hero_index)
        return 0 if hero is None else int(hero.get("disabled_slots") or 0)

    def set_hero_disabled_slots(self, uuid_hex, hero_index, mask):
        """Write the whole mask (0..255); saves. Returns the stored value."""
        hero = self.ensure_hero(uuid_hex, hero_index)
        if hero is None:
            return None
        if isinstance(mask, bool):
            # int(True) == 1 is a legal mask by accident; validate() refuses a
            # stored bool, so the setter refuses it too (the fix pass, ENG-M3).
            raise ValueError("suppress mask must be an int 0..255, not a bool")
        mask = int(mask)
        if not 0 <= mask <= 0xFF:
            raise ValueError(f"suppress mask {mask} outside 0..255; the "
                             f"client's mask is eight bits (hotKeyState +0xA4)")
        hero["disabled_slots"] = mask
        self.save()
        return mask

    # ---- where the character's items are (DESKWORK-D1 step 8) -------------
    # {item id: [bag, slot]} for the items the dress creates, written when an
    # in-game move (c2s 0x004F) or equip (0x0030) is accepted and read back by
    # the next dress so armour and set items are where the character left
    # them. Item ids are OURS (the dress's constants), so a stored cell for an
    # id this launch does not create is ignored at the dress, never a refusal.
    def item_locations(self, uuid_hex):
        """{int item_id: (bag, slot)}; {} when none is stored."""
        row = self.character_by_uuid(uuid_hex)
        locs = (row or {}).get("item_locations") or {}
        return {int(k): (int(v[0]), int(v[1])) for k, v in locs.items()}

    def set_item_location(self, uuid_hex, item_id, bag, slot):
        """Record one item's cell; saves. Returns the stored {id: [bag, slot]}."""
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return None
        bag, slot = int(bag), int(slot)
        if bag < 0 or slot < 0:
            raise ValueError(f"item {item_id}: bag {bag} slot {slot} -- a cell is "
                             f"two non-negative ints")
        locs = row.setdefault("item_locations", {})
        locs[str(int(item_id))] = [bag, slot]
        self.save()
        return dict(locs)

    def drop_item_location(self, uuid_hex, item_id):
        """Forget one item's stored cell; saves. True when a row was removed.
        The dress calls this for a stored EQUIPPED cell that is not the piece's
        type's (written under the pre-2026-09-23 visual numbering, or foreign):
        never reinterpreted, dropped with the reason in the log
        (itemstore.restore's `stale`)."""
        row = self.character_by_uuid(uuid_hex)
        if row is None:
            return False
        locs = row.get("item_locations") or {}
        if str(int(item_id)) not in locs:
            return False
        del locs[str(int(item_id))]
        self.save()
        return True


def find_character(uuid_hex, base=None):
    """(Store, row) for a character uuid, searching every account file.

    The game channel knows the character only by the uuid in the client's
    version frame -- no email, no session -- and a loopback vault holds a
    handful of accounts at most, so a directory scan is the honest lookup.
    Returns (None, None) when nothing matches; a store that fails validation
    propagates, because a broken file must not make its characters vanish.
    """
    root = base or store_dir()
    if not uuid_hex or not os.path.isdir(root):
        return None, None
    for fname in sorted(os.listdir(root)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(root, fname)
        sig = _disk_sig(path)  # before the read, as Store.open does
        with open(path, encoding="utf-8") as f:
            data = validate(json.load(f), fname)
        row = data["characters"].get(uuid_hex.lower())
        if row is not None:
            return Store(path, data, sig=sig), row
    return None, None


# ---------------------------------------------------------------------------
# The operator's read/write surface for the skill library.
#
# The library is ACCOUNT state living in the vault, not world content, so it
# does not belong in content/*.toml: content rows are facts about the world
# every operator shares, while this is one person's account. Authoring it by
# hand in the JSON works and is supported -- this CLI exists because the two
# footguns are easy to walk into unaided. It refuses id 0 through the same
# validator the server loads with, and it says out loud when adding one id
# would CREATE a list where none existed, because that converts the account
# from flag-driven (all 1,333 corpus skills) to store-driven (just that one).
# ---------------------------------------------------------------------------

def uuid_hex_required(ap, uuid_hex):
    if not uuid_hex:
        ap.error("--character NAME is required for the bar and hero options")
    return uuid_hex


def _ids_arg(spec):
    return [int(s, 0) for s in str(spec).split(",") if s.strip() != ""]


def _main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(
        description="Read and write the persisted skill library.")
    ap.add_argument("--list", action="store_true",
                    help="every account file in the vault, with its counts")
    ap.add_argument("--account", help="account email (names the store file)")
    ap.add_argument("--character", help="character name, for the learned list")
    ap.add_argument("--show", action="store_true",
                    help="print the account and character libraries")
    ap.add_argument("--unlock", help="add ids to the ACCOUNT-wide library")
    ap.add_argument("--lock", help="remove ids from the ACCOUNT-wide library")
    ap.add_argument("--set-unlocked",
                    help="replace the ACCOUNT-wide library outright")
    ap.add_argument("--learn", help="add ids to THIS CHARACTER's learned list")
    ap.add_argument("--unlearn",
                    help="remove ids from THIS CHARACTER's learned list")
    ap.add_argument("--set-learned",
                    help="replace THIS CHARACTER's learned list outright")
    ap.add_argument("--hero", type=int, metavar="INDEX",
                    help="hero index to author (requires --character)")
    ap.add_argument("--hero-skills",
                    help="replace the hero's OWN skill list (0x0073 field 7)")
    ap.add_argument("--hero-bar",
                    help="replace the hero's eight slots; 0 is an empty slot")
    ap.add_argument("--hero-attributes", metavar="ID:RANK,...",
                    help="replace the hero's attribute ranks")
    ap.add_argument("--hero-points", type=int, metavar="N",
                    help="the hero's LIFETIME attribute budget. Without one "
                         "the hero's total is whatever its ranks already "
                         "cost, so nothing is spendable; retail's level-3 "
                         "Koss carries 10 against 4 spent")
    ap.add_argument("--bar", help="replace the CHARACTER's own eight slots")
    a = ap.parse_args(argv)

    if a.list:
        root = store_dir()
        if not os.path.isdir(root):
            print(f"no store directory at {root}")
            return 0
        for fname in sorted(os.listdir(root)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(root, fname), encoding="utf-8") as f:
                data = validate(json.load(f), fname)
            acct = data["account"].get("unlocked_skills")
            print(f"{fname}: account unlocked="
                  f"{len(acct) if acct is not None else 'not authored'}, "
                  f"{len(data['characters'])} character(s)")
            for _u, row in sorted(data["characters"].items()):
                learned = row.get("learned_skills")
                print(f"    {row['name']}: learned="
                      f"{len(learned) if learned is not None else 'not authored'}")
        return 0

    if not a.account:
        ap.error("--account is required (or use --list)")
    st = Store.open(a.account)

    uuid_hex = None
    if a.character:
        found = st.character_by_name(a.character)
        if found is None:
            raise SystemExit(f"no character named {a.character!r} in "
                             f"{st.path}")
        uuid_hex = found[0]

    def _warn_if_creating(current, what):
        if current is None:
            print(f"NOTE: {what} had no stored list. Creating one makes it "
                  f"AUTHORITATIVE -- the server's --unlocks flag stops "
                  f"answering for it, so this list is now the whole library.")

    if a.set_unlocked is not None:
        st.set_account_unlocked_skills(_ids_arg(a.set_unlocked))
    if a.unlock:
        _warn_if_creating(st.account_unlocked_skills(), "the account library")
        cur = st.account_unlocked_skills() or []
        st.set_account_unlocked_skills(list(cur) + _ids_arg(a.unlock))
    if a.lock:
        cur = st.account_unlocked_skills()
        if cur is None:
            raise SystemExit("the account has no stored library to lock from")
        drop = set(_ids_arg(a.lock))
        st.set_account_unlocked_skills([s for s in cur if s not in drop])

    if a.set_learned is not None or a.learn or a.unlearn:
        if uuid_hex is None:
            ap.error("--character is required for --learn/--unlearn/"
                     "--set-learned")
    if a.set_learned is not None:
        st.set_character_learned_skills(uuid_hex, _ids_arg(a.set_learned))
    if a.learn:
        _warn_if_creating(st.character_learned_skills(uuid_hex),
                          f"character {a.character!r}")
        cur = st.character_learned_skills(uuid_hex) or []
        st.set_character_learned_skills(uuid_hex,
                                        list(cur) + _ids_arg(a.learn))
    if a.unlearn:
        cur = st.character_learned_skills(uuid_hex)
        if cur is None:
            raise SystemExit(f"character {a.character!r} has no stored "
                             f"learned list to remove from")
        drop = set(_ids_arg(a.unlearn))
        st.set_character_learned_skills(uuid_hex,
                                        [s for s in cur if s not in drop])

    # Always printed, mutation or not: the point of a write command is seeing
    # what the file now says. `--show` is the no-mutation spelling of it.
    if a.bar is not None:
        st.set_character_skillbar(uuid_hex_required(ap, uuid_hex), _ids_arg(a.bar))

    if a.hero is not None:
        uuid_hex_required(ap, uuid_hex)
        if a.hero_skills is not None:
            st.set_hero_skills(uuid_hex, a.hero, _ids_arg(a.hero_skills))
        if a.hero_bar is not None:
            st.set_hero_skillbar(uuid_hex, a.hero, _ids_arg(a.hero_bar))
        if a.hero_attributes is not None:
            st.set_hero_attributes(
                uuid_hex, a.hero,
                [[int(x.split(":")[0], 0), int(x.split(":")[1], 0)]
                 for x in a.hero_attributes.split(",") if x.strip()])
        if a.hero_points is not None:
            hero = st.ensure_hero(uuid_hex, a.hero)
            hero["attribute_points"] = int(a.hero_points)
            st.save()
    elif any(v is not None for v in (a.hero_skills, a.hero_bar,
                                     a.hero_attributes, a.hero_points)):
        ap.error("--hero INDEX is required for the --hero-* options")

    acct = st.account_unlocked_skills()
    unset = "NOT AUTHORED (--unlocks flag answers)"
    print(f"store: {st.path}")
    print(f"  account unlocked_skills: {unset if acct is None else acct}")
    for u, row in sorted(st.characters()):
        learned = st.character_learned_skills(u)
        print(f"  {row['name']} learned_skills: "
              f"{unset if learned is None else learned}")
        bar = st.character_skillbar(u)
        if bar is not None:
            print(f"  {row['name']} skillbar: {bar}")
        for hid, hero in sorted(st.heroes(u).items(), key=lambda kv: int(kv[0])):
            print(f"  {row['name']} hero {hid}: "
                  f"skills={hero.get('skills')} bar={hero.get('skillbar')} "
                  f"attributes={hero.get('attributes')} "
                  f"points={hero.get('attribute_points')}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
