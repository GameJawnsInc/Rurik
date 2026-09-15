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
        blob = row.get("settings_blob", "")
        if blob:
            try:
                bytes.fromhex(blob)
            except ValueError:
                _refuse(path, f"character {row['name']!r}: settings_blob is "
                              f"not hex")
    return data


class Store:
    """One account's persistent state. Load with open(); every write saves."""

    def __init__(self, path, data):
        self.path = path
        self.data = data

    @classmethod
    def open(cls, email, base=None):
        path = path_for(email, base)
        if not os.path.exists(path):
            return cls(path, _fresh(email))
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            _refuse(path, f"corrupt JSON ({exc}); fix or delete it -- "
                          f"defaults will not be silently substituted")
        return cls(path, validate(data, path))

    def save(self):
        validate(self.data, self.path)  # never persist what open() would refuse
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

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
        """
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
        with open(os.path.join(root, fname), encoding="utf-8") as f:
            data = validate(json.load(f), fname)
        row = data["characters"].get(uuid_hex.lower())
        if row is not None:
            return Store(os.path.join(root, fname), data), row
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
    acct = st.account_unlocked_skills()
    unset = "NOT AUTHORED (--unlocks flag answers)"
    print(f"store: {st.path}")
    print(f"  account unlocked_skills: {unset if acct is None else acct}")
    for u, row in sorted(st.characters()):
        learned = st.character_learned_skills(u)
        print(f"  {row['name']} learned_skills: "
              f"{unset if learned is None else learned}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
