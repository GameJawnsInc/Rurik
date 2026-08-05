"""Accept on a port and record exactly what arrives, assuming nothing about it.

Written because a webgate on port 80 saw the client ESTABLISH a connection and then
logged no request at all. An HTTP server only tells you about traffic that parses as
HTTP; anything else -- a raw protocol, a TLS ClientHello, or a client that connects
and waits for the SERVER to speak first -- is invisible to it, and looks identical
to "nothing happened".

Threaded, so one silent connection cannot wedge the listener. That is not
hypothetical: a stock HTTPServer is strictly serial, so a client that opens a
socket and sends nothing blocks every later request forever.
"""

import argparse
import binascii
import json
import os
import socket
import threading
import time


def dump(b, width=16):
    out = []
    for i in range(0, min(len(b), 512), width):
        chunk = b[i:i + width]
        hexs = binascii.hexlify(chunk).decode()
        hexs = " ".join(hexs[j:j + 2] for j in range(0, len(hexs), 2))
        text = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append(f"    {i:04x}  {hexs:<47s}  {text}")
    return "\n".join(out)


def serve(conn, addr, n, rec, hold, greet):
    t0 = time.time()
    print(f"\n*** connection {n} from {addr[0]}:{addr[1]}", flush=True)
    rec({"event": "connect", "n": n, "peer": f"{addr[0]}:{addr[1]}"})
    if greet:
        conn.sendall(greet)
        print(f"    (sent {len(greet)} greeting bytes)", flush=True)
    conn.settimeout(hold)
    total = b""
    try:
        while True:
            b = conn.recv(65536)
            if not b:
                print(f"    peer closed after {len(total)}B", flush=True)
                rec({"event": "close", "n": n, "bytes": len(total)})
                break
            total += b
            print(f"    +{len(b)}B at t+{time.time()-t0:.2f}s", flush=True)
            print(dump(b), flush=True)
            rec({"event": "data", "n": n, "t": round(time.time() - t0, 3),
                 "hex": binascii.hexlify(b[:2048]).decode()})
    except socket.timeout:
        print(f"    silent for {hold}s, {len(total)}B total -- the client is "
              f"waiting for US to speak first", flush=True)
        rec({"event": "silent", "n": n, "bytes": len(total), "waited": hold})
    except OSError as ex:
        rec({"event": "error", "n": n, "error": repr(ex)})
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--hold", type=float, default=15.0,
                    help="Seconds to wait for bytes before declaring the peer silent.")
    ap.add_argument("--greet", default="",
                    help="Hex bytes to send on accept, to test whether the client "
                         "is waiting for the server to speak first.")
    ap.add_argument("--vault", default=r"C:\gd\Rurik\vault\captures\raw")
    a = ap.parse_args()

    os.makedirs(a.vault, exist_ok=True)
    path = os.path.join(a.vault, f"raw-{a.port}-{time.strftime('%Y%m%dT%H%M%S')}.jsonl")
    lock = threading.Lock()

    def rec(obj):
        obj["wall"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with lock, open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj) + "\n")

    greet = binascii.unhexlify(a.greet) if a.greet else b""

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        srv.bind(("127.0.0.1", a.port))
    except OSError as ex:
        raise SystemExit(f"Could not bind 127.0.0.1:{a.port} - {ex.strerror}.\n"
                         f"Something else is already serving it; stop that first.")
    srv.listen(16)
    print(f"raw listener on 127.0.0.1:{a.port}  ->  {path}")
    print("recording everything, assuming nothing\n")

    n = 0
    try:
        while True:
            conn, addr = srv.accept()
            n += 1
            threading.Thread(target=serve,
                             args=(conn, addr, n, rec, a.hold, greet),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
