"""Prove the Stage B handshake works, end to end, without the game client.

This is a calibration test, in the sense HANDOFF.md §8 means it: an instrument
that cannot reproduce the lifecycle cannot falsify a bug in it. So the test client
here does not use the key file's parameters directly. It reads (g, p, B) **out of
the patched executable**, exactly as the real client does, and only the server
side is allowed to know the private exponent.

That makes the whole chain load-bearing:

    make_custom_client.py  ->  patched Gw.exe  ->  this client reads (g,p,B)
                                                        |
    vault/keys/*.json  ->  authsrv.py  ->  server holds b
                                                        |
                            both must derive the same ARC4 key

If the patcher wrote to the wrong offsets, if endianness is flipped anywhere, or
if arc4_hash is subtly wrong, the derived keys differ and the final check fails.
A green result here means the real client should key up too.
"""

import os
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gwcrypto import ARC4, arc4_hash, recover_master_secret  # noqa: E402
from gwpe import PE  # noqa: E402

SIG_KEYS = bytes.fromhex("8B4508C70088000000B8")
PORT = 6112
BUILD = 38797


def read_client_params(exe):
    """Read (g, p, B) from a client binary the way the client itself would."""
    pe = PE(exe)
    hits = pe.find(SIG_KEYS, ".text")
    if not hits:
        raise SystemExit(f"{exe}: DH accessor signature not found")
    va = struct.unpack_from("<I", pe.data, hits[0] + 0x0A)[0]
    off = pe.rva_to_off(va - pe.image_base)
    g = int.from_bytes(pe.data[off + 4:off + 8], "little")
    p = int.from_bytes(pe.data[off + 8:off + 72], "little")
    B = int.from_bytes(pe.data[off + 72:off + 136], "little")
    return g, p, B


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    return cond


def main():
    patched_dir = r"C:\gd\Rurik\vault\client-patched"
    exes = [f for f in os.listdir(patched_dir) if f.endswith(".exe")]
    if not exes:
        raise SystemExit("no patched client in vault/client-patched — "
                         "run toolkit/clientpatch/make_custom_client.py")
    exe = os.path.join(patched_dir, sorted(exes)[-1])
    print(f"patched client : {os.path.basename(exe)}")

    g, p, B = read_client_params(exe)
    print(f"read from exe  : g={g}, prime {p.bit_length()} bits, B {B.bit_length()} bits")

    srv = subprocess.Popen([sys.executable, "toolkit/authsrv/authsrv.py", "--once"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ok = True
    try:
        for _ in range(60):
            try:
                s = socket.create_connection(("127.0.0.1", PORT), timeout=0.3)
                break
            except OSError:
                time.sleep(0.1)
        else:
            print("authsrv never came up")
            return 1

        # ---- client side of the handshake -------------------------------
        print("\n1. version")
        s.sendall(struct.pack("<4I", 0x000C0400, BUILD, 1, g))

        print("2. client seed")
        import secrets
        a_priv = secrets.randbits(512) % (p - 2) + 1
        A = pow(g, a_priv, p)
        s.sendall(struct.pack("<H", 0x4200) + A.to_bytes(64, "little"))

        print("3. server seed")
        s.settimeout(10)
        resp = b""
        while len(resp) < 22:
            chunk = s.recv(22 - len(resp))
            if not chunk:
                break
            resp += chunk
        ok &= check("server replied 22 bytes", len(resp) == 22, f"{len(resp)}")
        if len(resp) < 22:
            return 1
        hdr = struct.unpack("<H", resp[:2])[0]
        ok &= check("header is 0x1601", hdr == 0x1601, hex(hdr))

        # ---- derive, exactly as the client does -------------------------
        shared = pow(B, a_priv, p).to_bytes(64, "little")
        master = recover_master_secret(resp[2:], shared)
        derived = arc4_hash(master)
        print(f"   client-derived ARC4 key: {derived.hex()[:16]}…")

        print("\n4. speak encrypted and let the server decrypt it")
        c2s = ARC4(derived)
        probe = struct.pack("<H", 0x0001) + b"RURIK-HANDSHAKE-SELFTEST"
        s.sendall(c2s.crypt(probe))
        time.sleep(1.0)
        s.close()

        out, _ = srv.communicate(timeout=20)
        srv_key = ""
        for line in out.splitlines():
            if "ARC4 key" in line:
                srv_key = line.split("ARC4 key")[1].strip().rstrip("…").strip()
        ok &= check("server completed key exchange", "key exchange OK" in out)
        ok &= check("server and client derived the SAME key",
                    bool(srv_key) and derived.hex().startswith(srv_key),
                    f"server {srv_key} vs client {derived.hex()[:16]}")
        seen = "; ".join(l.strip() for l in out.splitlines() if "first header" in l)
        ok &= check("server decrypted our probe to the right header",
                    "first header 0x0001" in out, seen or "no frame logged")

        # ---- negative control -------------------------------------------
        # A test that only ever goes green proves nothing. An UNPATCHED client
        # keys against ArenaNet's compiled-in B, so its shared secret — and
        # therefore its ARC4 key — must NOT match ours. If this comes out equal,
        # the test is measuring something other than what it claims to.
        print("\n5. negative control: an unpatched client must NOT match")
        stock = None
        cdir = r"C:\gd\Rurik\vault\client"
        for build in sorted(os.listdir(cdir), reverse=True):
            cand = os.path.join(cdir, build, "Gw.exe")
            if os.path.exists(cand):
                try:
                    sg, sp, sB = read_client_params(cand)
                except SystemExit:
                    continue
                if sB != B:
                    stock = (build, sg, sp, sB)
                    break
        if stock is None:
            print("  [SKIP] no unpatched client with different parameters in the vault")
        else:
            build, sg, sp, sB = stock
            stock_shared = pow(sB, a_priv, sp).to_bytes(64, "little")
            stock_key = arc4_hash(recover_master_secret(resp[2:], stock_shared))
            ok &= check("stock client derives a DIFFERENT key",
                        stock_key != derived,
                        f"stock {stock_key.hex()[:16]} vs patched {derived.hex()[:16]}")
            print(f"         (control build: {build})")

        verdict = ("HANDSHAKE VERIFIED — the real client should key up too"
                   if ok else "FAILURES ABOVE")
        print(f"\n{verdict}")
        print("\n--- server log ---")
        for line in out.splitlines():
            if line.strip():
                print("   ", line)
        return 0 if ok else 1
    finally:
        if srv.poll() is None:
            srv.kill()


if __name__ == "__main__":
    sys.exit(main())
