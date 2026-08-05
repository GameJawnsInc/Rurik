"""Exercise the webgate the way the real client does, without the real client.

Stage A is the only part of the login we can test end to end offline, because the
probe captured the client's actual first request verbatim (studies/handshake/PLAN.md
§0.1). This replays that request byte-for-byte and then walks the rest of the
sequence, so a broken webgate is caught here rather than by a human staring at a
"Connecting..." dialog.

The first request below is not invented. It is what build 38797 sent.
"""

import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from base64 import b64encode

HOST, PORT = "127.0.0.1", 6601

# Verbatim from the capture. Kept byte-exact on purpose: if our server only works
# against a politely-formed request from `requests`, it does not work.
REAL_FIRST_REQUEST = (
    b"GET /Spawned/WebGate/session/create.xml HTTP/1.1\r\n"
    b"Connection: Keep-Alive\r\n"
    b"Authorization: Arena 0\r\n"
    b"User-Agent: Gw/38797.0 (Win32)\r\n"
    b"Host: 127.0.0.1:6601\r\n"
    b"\r\n"
)


def send_raw(payload, keep=None):
    s = keep or socket.create_connection((HOST, PORT), timeout=5)
    s.sendall(payload)
    buf = b""
    s.settimeout(5)
    try:
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        head, _, rest = buf.partition(b"\r\n\r\n")
        length = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":")[1])
        while len(rest) < length:
            chunk = s.recv(65536)
            if not chunk:
                break
            rest += chunk
    finally:
        if keep is None:
            s.close()
    return head.decode("latin1"), rest.decode("utf-8", "replace")


def post(path, body, session):
    payload = body.encode()
    req = (f"POST {path} HTTP/1.1\r\n"
           f"Connection: Keep-Alive\r\n"
           f"Authorization: Arena {session}\r\n"
           f"User-Agent: Gw/38797.0 (Win32)\r\n"
           f"Host: {HOST}:{PORT}\r\n"
           f"Content-Length: {len(payload)}\r\n\r\n").encode() + payload
    return send_raw(req)


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    return cond


def main():
    proc = subprocess.Popen(
        [sys.executable, "toolkit/portal/webgate.py"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ok = True
    try:
        for _ in range(50):
            try:
                socket.create_connection((HOST, PORT), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            print("webgate never came up")
            return 1

        print("\n1. the client's real session/create request")
        head, body = send_raw(REAL_FIRST_REQUEST)
        ok &= check("200 response", "200" in head.split("\r\n")[0], head.split("\r\n")[0])
        session = ""
        try:
            session = ET.fromstring(body).findtext("Session") or ""
        except Exception as ex:
            check("parses as XML", False, repr(ex))
            ok = False
        ok &= check("returns a Session id", len(session) == 36, session)

        print("\n2. users/login")
        head, body = post("/Spawned/WebGate/users/login.xml", f"""<Request>
<Provider>Portal</Provider>
<LoginName>owner@example.com</LoginName>
<Password>{b64encode(b'hunter2').decode()}</Password>
<GameCode>gw1</GameCode>
</Request>""", session)
        ok &= check("200 response", "200" in head.split("\r\n")[0])
        uid = ET.fromstring(body).findtext("UserId") if body.strip() else None
        ok &= check("returns a UserId", bool(uid and len(uid) == 36), str(uid))

        print("\n3. my_account/game_accounts")
        head, body = post("/Spawned/WebGate/my_account/game_accounts.xml",
                          "<Request><GameCode>gw1</GameCode></Request>", session)
        ok &= check("200 response", "200" in head.split("\r\n")[0])
        ok &= check("lists a game account", "<Alias>gw1</Alias>" in body)

        print("\n4. my_account/token")
        head, body = post("/Spawned/WebGate/my_account/token.xml",
                          "<Request><GameCode>gw1</GameCode>"
                          "<AccountAlias>gw1</AccountAlias></Request>", session)
        ok &= check("200 response", "200" in head.split("\r\n")[0])
        token = ET.fromstring(body).findtext("Token") if body.strip() else None
        ok &= check("issues a game token", bool(token and len(token) == 36), str(token))

        print("\n5. a bad session must be rejected (proving the check can go red)")
        head, _ = post("/Spawned/WebGate/my_account/token.xml",
                       "<Request><GameCode>gw1</GameCode></Request>", "not-a-session")
        ok &= check("401 for unknown session", "401" in head.split("\r\n")[0],
                    head.split("\r\n")[0])

        print(f"\n{'ALL CHECKS PASSED' if ok else 'FAILURES ABOVE'}")
        return 0 if ok else 1
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=5)
            tail = [l for l in (out or "").splitlines() if l.strip()][-14:]
            if tail:
                print("\n--- webgate log ---")
                for l in tail:
                    print("   ", l)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
