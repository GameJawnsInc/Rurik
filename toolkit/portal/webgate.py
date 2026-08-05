"""Rurik webgate — Stage A of the Guild Wars login, served locally.

This answers the portal requests the client makes when launched with
`-portal 127.0.0.1`. The probe in studies/handshake/PLAN.md §0 established that
with that flag the client drops TLS entirely and speaks plain HTTP on port 6601,
prefixing every path with /Spawned/WebGate. So this is an ordinary HTTP server
and nothing more: no certificate, no trust store, no SRP.

Endpoints, in the order a login uses them:

    GET  /Spawned/WebGate/session/create.xml        -> mint a session id
    POST /Spawned/WebGate/users/login.xml           -> authenticate, return a user id
    POST /Spawned/WebGate/my_account/game_accounts.xml -> list game accounts
    POST /Spawned/WebGate/my_account/token.xml      -> issue the game token

The token from that last call is what the client carries to AuthSrv on 6112,
which is Stage B.

Everything is logged to the vault. Stage A traffic is capture too, and it is the
one part of the login we can record in full plaintext -- so we do, from the first
run, rather than adding it later.

WHAT THIS IS NOT: an authenticator. It accepts any account name and issues a
stable synthetic identity for it. That is correct for a private local server with
a single human user, and it is the reason this must never listen on a public
interface. It binds loopback only, deliberately, and refuses to do otherwise.
"""

import argparse
import hashlib
import json
import os
import time
import uuid
import xml.etree.ElementTree as ET
from base64 import b64decode
from http.server import BaseHTTPRequestHandler, HTTPServer

VAULT_DEFAULT = r"C:\gd\Rurik\vault\captures\portal"

sessions = {}
_log_path = None
_seen_builds = set()


def log(event, **kw):
    kw["event"] = event
    kw["t"] = round(time.time(), 3)
    line = json.dumps(kw)
    if _log_path:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    brief = {k: v for k, v in kw.items() if k not in ("t", "body", "response")}
    print(f"  {event:22s} {brief}", flush=True)


def stable_guid(seed: str) -> str:
    """A deterministic GUID per account name, so ids survive restarts.

    Random ids would work for one session, but a server whose account identity
    changes every launch makes captures from different days incomparable, and
    comparing captures across days is the whole point of the vault.
    """
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return str(uuid.UUID(h[:32])).upper()


class Session:
    def __init__(self):
        self.id = str(uuid.uuid4()).upper()
        self.email = None
        self.user_id = None
        self.token = None


class Handler(BaseHTTPRequestHandler):
    server_version = "RurikWebGate/0.1"

    def log_message(self, fmt, *a):
        pass  # we do our own, structured

    # -- helpers ----------------------------------------------------------
    def _note_build(self):
        ua = self.headers.get("User-Agent", "")
        # The probe found the build number rides here in the clear:
        #   User-Agent: Gw/38797.0 (Win32)
        # It is the cheapest build stamp available and every capture wants it.
        if ua.startswith("Gw/") and ua not in _seen_builds:
            _seen_builds.add(ua)
            log("client_build", user_agent=ua)
        return ua

    def _xml(self, body: str, code: int = 200):
        payload = body.strip().encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        log("reply", path=self.path, code=code, response=payload.decode("utf-8"))

    def _fail(self, code, msg):
        body = msg.encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        log("reply_error", path=self.path, code=code, msg=msg)

    def _read_xml(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        log("request", method=self.command, path=self.path,
            authorization=self.headers.get("Authorization"), body=raw)
        return ET.fromstring(raw) if raw else None

    def _session(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Arena "):
            return None
        return sessions.get(auth[len("Arena "):])

    # -- endpoints --------------------------------------------------------
    def do_GET(self):
        self._note_build()
        if self.path == "/Spawned/WebGate/session/create.xml":
            log("request", method="GET", path=self.path,
                authorization=self.headers.get("Authorization"))
            s = Session()
            sessions[s.id] = s
            # Authorization on this first call is "Arena 0" -- no session exists yet.
            self._xml(f"<Reply>\n<Session>{s.id}</Session>\n</Reply>")
        else:
            log("unhandled_get", path=self.path)
            self._fail(404, "unhandled")

    def do_POST(self):
        self._note_build()
        try:
            if self.path == "/Spawned/WebGate/users/login.xml":
                return self.login()
            if self.path == "/Spawned/WebGate/my_account/game_accounts.xml":
                return self.game_accounts()
            if self.path == "/Spawned/WebGate/my_account/token.xml":
                return self.game_token()
            log("unhandled_post", path=self.path)
            # Read the body anyway -- an unknown endpoint is exactly the thing we
            # most want recorded, and discarding it loses the observation.
            self._read_xml()
            self._fail(404, "unhandled")
        except Exception as ex:  # never let one bad request kill the server
            log("handler_error", path=self.path, error=repr(ex))
            self._fail(500, "error")

    def login(self):
        s = self._session()
        if s is None:
            return self._fail(401, "no session")
        root = self._read_xml()
        provider = root.findtext("Provider")
        if provider != "Portal":
            return self._fail(400, f"unsupported provider {provider}")

        s.email = root.findtext("LoginName") or "local@rurik"
        # The password arrives base64-encoded. We do not check it and we do not
        # store it -- this server exists to say yes to its single local user.
        try:
            b64decode(root.findtext("Password") or "")
        except Exception:
            pass
        s.user_id = stable_guid("user:" + s.email)
        s.token = stable_guid("token:" + s.email)
        log("login", email=s.email, user_id=s.user_id)

        self._xml(f"""
<Reply>
<UserId>{s.user_id}</UserId>
<UserCenter>1</UserCenter>
<UserName>:Rurik.1</UserName>
<Parts/>
<ResumeToken>{stable_guid('resume:' + s.email)}</ResumeToken>
<LoginName>{s.email}</LoginName>
<Provider>Portal</Provider>
<EmailVerified>1</EmailVerified>
</Reply>""")

    def game_accounts(self):
        s = self._session()
        if s is None:
            return self._fail(401, "no session")
        root = self._read_xml()
        game_code = root.findtext("GameCode") or "gw1"
        self._xml(f"""
<Reply type="array">
<Row>
<GameCode>{game_code}</GameCode>
<Alias>gw1</Alias>
<Created>2005-04-28T12:00:00Z</Created>
</Row>
</Reply>""")

    def game_token(self):
        s = self._session()
        if s is None:
            return self._fail(401, "no session")
        self._read_xml()
        log("token_issued", email=s.email, token=s.token)
        # This token is what the client presents to AuthSrv on 6112. Stage B has
        # to recognise it, so both stages must agree on how it is derived.
        self._xml(f"<Reply>\n<Token>{s.token}</Token>\n</Reply>")


def main():
    global _log_path
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=6601)
    ap.add_argument("--vault", default=VAULT_DEFAULT)
    a = ap.parse_args()

    os.makedirs(a.vault, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    _log_path = os.path.join(a.vault, f"portal-{stamp}.jsonl")

    # Loopback only. This server authenticates nobody; exposing it would be
    # handing out an identity endpoint. HANDOFF.md section 9: local and personal.
    srv = HTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Rurik webgate on http://127.0.0.1:{a.port}  (loopback only)")
    print(f"logging to {_log_path}")
    print("launch the client with:  -portal 127.0.0.1 -authsrv 127.0.0.1\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
