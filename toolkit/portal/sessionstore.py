"""Shared state between the portal and AuthSrv.

The two run as separate processes: the portal issues a user id and a game token
over HTTP, and the client then presents both to AuthSrv over the encrypted auth
channel. AuthSrv has to recognise them.

Confirmed empirically from our own logs plus a live capture of build 38797:

    portal /users/login.xml        issued user_id  E696B44C-04FC-DF92-9EE1-B0CC329B424A
    portal /my_account/token.xml   issued token    233B382E-3CD2-E5B6-7018-7F547D2760A7

    client AUTH_CMSG_PORTAL_ACCOUNT_LOGIN carried
        user_id    blob 4cb496e6fc0492df9ee1b0cc329b424a
        session_id blob 2e383b23d23cb6e570187f547d2760a7

Two things fall out of that, neither of which is obvious from reading the C sources:

  * The blobs are `uuid.UUID(...).bytes_le` -- the Microsoft GUID layout, where the
    first three fields are little-endian and the last two are not. Plain `.bytes`
    does not match.
  * The field the reference implementations call `session_id` carries the GAME
    TOKEN, not the portal session id. Validating it against the session id would
    reject every legitimate login.

A JSON file is the right weight here. This is one human on loopback; a database
would be ceremony. The file is small, human-readable when something goes wrong,
and survives restarting either process independently -- which matters because the
two are started in separate terminals and either may be restarted mid-debugging.
"""

import json
import os
import tempfile
import time
import uuid

DEFAULT_PATH = r"C:\gd\Rurik\vault\state\sessions.json"


def uuid_to_wire(u) -> bytes:
    """Textual UUID -> the 16 wire bytes the client sends."""
    if isinstance(u, str):
        u = uuid.UUID(u)
    return u.bytes_le


def wire_to_uuid(b: bytes) -> str:
    """The 16 wire bytes -> uppercase textual UUID."""
    if len(b) != 16:
        raise ValueError(f"expected 16 bytes, got {len(b)}")
    return str(uuid.UUID(bytes_le=bytes(b))).upper()


class SessionStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"sessions": {}}

    def _write(self, data):
        # Write-then-rename so a reader never sees a half-written file. The two
        # processes poll this independently and a torn read would look like a
        # rejected login, which is a miserable thing to debug.
        d = os.path.dirname(self.path)
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def issue(self, email, user_id, token):
        """Record what the portal handed out. Keyed by token."""
        data = self._read()
        data["sessions"][token.upper()] = {
            "email": email,
            "user_id": user_id.upper(),
            "token": token.upper(),
            "issued_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # Keep the file from growing without bound across months of sessions.
        if len(data["sessions"]) > 200:
            oldest = sorted(data["sessions"].items(),
                            key=lambda kv: kv[1].get("issued_utc", ""))[:100]
            for k, _ in oldest:
                data["sessions"].pop(k, None)
        self._write(data)

    def lookup(self, user_id_wire: bytes, token_wire: bytes):
        """Validate what the client presented. Returns the record or None."""
        user_id = wire_to_uuid(user_id_wire)
        token = wire_to_uuid(token_wire)
        rec = self._read()["sessions"].get(token)
        if rec is None:
            return None
        if rec["user_id"] != user_id:
            return None
        return rec
