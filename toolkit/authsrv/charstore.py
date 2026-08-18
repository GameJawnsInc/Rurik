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
