"""Prove the whole live-capture pipeline on loopback, elevated, in one command.

    (ELEVATED)  python toolkit/harness/dryrun_keycapture.py

This runs the entire R0b pipeline against OUR OWN server, where every byte is checkable,
so the one link that has never run -- WinDivert's off-wire capture and the full assembly --
is proven before anything is pointed at ArenaNet:

    key-tap cave  ->  off-wire WinDivert capture  ->  keytap read  ->  assemble  ->  decrypt

and the decrypted wire ciphertext is required to equal, byte for byte, what our server
independently recorded. Nothing here touches ArenaNet: loopback, caged client, our server,
the synthetic credential. It just exercises the live machinery in a place with an oracle.

WHY ELEVATED. The first WinDivertOpen loads a kernel driver, which needs admin. Everything
else (build, launch, keytap) is unprivileged; they are bundled here so it is one command.

WHAT IT DOES, and cleans up after:
  1. build + stage a key-tapped LOOPBACK client at the caged run path;
  2. start the off-wire capture on 127.0.0.1:6112 (before the client connects, to catch
     the plaintext handshake);
  3. bring up the stack and drive the client to the auth handshake (session.py);
  4. read the session key out of the running client (keytap), cross-checked against the
     master_secret our server derived;
  5. stop everything, then assemble the wire capture with that key and verify it decrypts
     to the server's own logged plaintext, and that the captured ciphertext IS the server's.

standard library only (WinDivert via wirecapture.py).
"""
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import keytap  # noqa: E402
import keytap_patch  # noqa: E402
import livesession as ls  # noqa: E402
import replay  # noqa: E402
import vaultpath  # noqa: E402
import wirecapture as wc  # noqa: E402
from gwpe import PE  # noqa: E402

PY = [sys.executable]
TOOLKIT = os.path.dirname(HERE)
RUN_TAG = "2026-07-29_221c13772c7a"
RUN_EXE = vaultpath.vault_path("run", RUN_TAG, "Gw.exe")
KEYFILE = vaultpath.vault_path("keys", "rurik_dh_2026-07-29_221c13772c7a.json")
PRISTINE = None  # resolved from pinned at runtime


class Stage:
    """A tiny staged pass/fail, so the script reads as a checklist and stops honestly."""
    def __init__(self):
        self.failed = []
    def ok(self, cond, label, detail=""):
        mark = "PASS" if cond else "FAIL"
        print(f"  [{mark}] {label}" + (f"  --  {detail}" if detail else ""), flush=True)
        if not cond:
            self.failed.append(label)
        return cond


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def running_clients():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"Name='Gw.exe'\" | Measure-Object).Count"],
        capture_output=True, text=True, timeout=30)
    try:
        return int(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return -1


def client_pid():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='Gw.exe'\" | "
         "Select-Object -First 1 -ExpandProperty ProcessId"],
        capture_output=True, text=True, timeout=30)
    try:
        return int(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def newest_auth_capture(since):
    """The AUTH-channel .jsonl from this run that completed the handshake, or None.

    Must be the auth channel specifically -- the wire capture sniffs 127.0.0.1:6112 (auth),
    and a game-channel capture (127.0.0.3, which also carries server_seed + key_exchange_ok)
    would be the wrong oracle. The `version` record names its channel, so we require it.
    """
    best = None
    for p in glob.glob(os.path.join(vaultpath.vault_path("captures"), "**", "*.jsonl"),
                       recursive=True):
        try:
            if os.path.getmtime(p) < since:
                continue
        except OSError:
            continue
        is_auth = has_seed = has_key = False
        for line in open(p, encoding="utf-8", errors="replace"):
            if '"channel": "auth"' in line:
                is_auth = True
            if '"server_seed"' in line:
                has_seed = True
            if '"key_exchange_ok"' in line:
                has_key = True
        if is_auth and has_seed and has_key:
            if best is None or os.path.getmtime(p) > os.path.getmtime(best):
                best = p
    return best


def stop(procs):
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    for p in procs:
        try:
            p.wait(timeout=10)          # give each a moment to run its own cleanup
        except Exception:
            pass
    # And make sure no client or stack listener is left behind.
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'Gw.exe' -or "
         "($_.Name -eq 'python.exe' -and $_.CommandLine -match 'session.py|webgate.py|"
         "authsrv.py|wirecapture.py') } | ForEach-Object { Stop-Process -Id $_.ProcessId "
         "-Force -ErrorAction SilentlyContinue }"],
        capture_output=True, text=True, timeout=60)


def main():
    st = Stage()
    scratch = vaultpath.vault_path("captures", "live")
    os.makedirs(scratch, exist_ok=True)
    wire = os.path.join(scratch, "dryrun_wire.jsonl")
    decrypted = os.path.join(scratch, "dryrun_decrypted.jsonl")
    for p in (wire, decrypted):
        if os.path.exists(p):
            os.remove(p)

    print("0. preconditions")
    if not st.ok(is_admin(), "running elevated (the first WinDivertOpen loads a driver)"):
        print("\nRe-run from an elevated shell. Nothing was started.")
        return 2
    try:
        wc._load_windivert()
        st.ok(True, "WinDivert loads", "vault/tools/windivert")
    except wc.WinDivertError as e:
        st.ok(False, "WinDivert loads", str(e).splitlines()[0])
        return 2
    if not st.ok(running_clients() == 0, "no Gw.exe already running"):
        print("\nClose every client first. Nothing was started.")
        return 2

    procs = []
    logs = []
    arc4_key = None
    try:
        print("\n1. build + stage a key-tapped loopback client")
        clientpatch = os.path.join(TOOLKIT, "clientpatch")
        b = subprocess.run(PY + [os.path.join(clientpatch, "make_custom_client.py"),
                                 "--input", os.path.abspath(pinned_pristine()),
                                 "--keys", KEYFILE, "--key-tap"],
                           capture_output=True, text=True, timeout=300)
        # Guard, don't just record: RUN_EXE would not exist after a failed build, and the
        # next line (PE(RUN_EXE)) would crash on a first-ever run with nothing to fall back on.
        if not st.ok(b.returncode == 0, "make_custom_client --key-tap",
                     (b.stdout.strip().splitlines() or [""])[-1] if b.stdout
                     else b.stderr[-120:]):
            return 1
        r = subprocess.run(PY + [os.path.join(clientpatch, "make_run_dir.py")],
                          capture_output=True, text=True, timeout=300)
        if not st.ok(r.returncode == 0, "make_run_dir (into the caged run path)",
                     (r.stdout.strip().splitlines() or [""])[-1] if r.stdout
                     else r.stderr[-120:]):
            return 1
        pe = PE(RUN_EXE)
        slot_rva, _ = keytap_patch.locate_slot(pe.data, pe)
        st.ok(True, "the run client is key-tapped", f"slot at Gw.exe+0x{slot_rva:x}")

        print("\n2. start the off-wire capture (before the client connects)")
        # Subprocess output goes to log files, never to an unread PIPE: session.py prints a
        # "...holding" line every second under --keep-open, and an unread pipe would fill
        # its OS buffer and DEADLOCK the child mid-run. The logs are also the post-mortem.
        cap_log = open(os.path.join(scratch, "dryrun_wirecapture.log"), "w")
        sess_log = open(os.path.join(scratch, "dryrun_session.log"), "w")
        logs.extend([cap_log, sess_log])
        cap = subprocess.Popen(PY + [os.path.join(HERE, "wirecapture.py"),
                                     "--server", "127.0.0.1:6112", "--seconds", "120",
                                     "--out", wire],
                               stdout=cap_log, stderr=subprocess.STDOUT, text=True)
        procs.append(cap)
        # Wait for a real readiness signal, not a fixed sleep: open_capture writes the
        # wire_meta line only AFTER WinDivertOpen succeeds, so its presence proves the sniff
        # is live before we let the client connect. A dead subprocess is caught too.
        ready = False
        rdl = time.time() + 20
        while time.time() < rdl:
            if cap.poll() is not None:
                break
            if os.path.exists(wire) and '"wire_meta"' in open(wire, encoding="utf-8",
                                                              errors="replace").read():
                ready = True
                break
            time.sleep(0.3)
        live_ok = ready and cap.poll() is None
        if not st.ok(live_ok, "the off-wire capture is live and sniffing",
                     "" if live_ok else "died or never opened -- see dryrun_wirecapture.log "
                     "(elevated?)"):
            return 1

        print("\n3. bring up the stack and drive to the handshake")
        since = time.time()
        sess = subprocess.Popen(PY + [os.path.join(HERE, "session.py"),
                                      "--until", "login", "--keep-open"],
                                stdout=sess_log, stderr=subprocess.STDOUT, text=True)
        procs.append(sess)

        auth = None
        deadline = time.time() + 150
        while time.time() < deadline:
            auth = newest_auth_capture(since)
            if auth:
                break
            if sess.poll() is not None:
                break
            time.sleep(2)
        st.ok(auth is not None, "the client keyed the auth channel (key_exchange_ok)",
              os.path.basename(auth) if auth else "no handshake within 150s")
        if not auth:
            return 1

        print("\n4. read the session key out of the running client")
        pid = client_pid()
        st.ok(pid is not None, "found the client pid", str(pid))
        # The cave taps [ebp-0x18], which is master_secret BEFORE the key schedule -- so the
        # slot holds master_secret, and the ARC4 key is arc4_hash(master_secret). keytap
        # reads the former; we derive the latter to decrypt.
        #
        # Retry: the server logs key_exchange_ok when IT finishes the handshake, but the
        # slot is written on the CLIENT side, which may lag by a moment -- so a single read
        # can catch an all-zero slot that is about to be filled.
        tapped = None
        for _ in range(20):
            if not pid:
                break
            tapped = keytap.read_rva(pid, "Gw.exe", slot_rva, 20)
            if tapped and any(tapped):
                break
            time.sleep(0.25)
        st.ok(tapped is not None and any(tapped),
              "keytap read a non-zero master_secret from the slot",
              tapped.hex() if tapped else "None (still zero after retries)")
        master, label = derive_master(auth)
        st.ok(tapped == master, "the tapped master_secret equals what our server derived",
              f"{'match' if tapped == master else 'MISMATCH'} ({label})")
        from gwcrypto import arc4_hash  # noqa: E402
        arc4_key = arc4_hash(tapped) if tapped else None

        # Let a little more traffic flow so there is ciphertext beyond the handshake.
        time.sleep(5)

        print("\n5. stop everything, then assemble and verify")
    finally:
        stop(procs)
        time.sleep(1)
        for fh in logs:
            try:
                fh.close()
            except Exception:
                pass

    # --- offline: assemble the wire capture with the key, and check it against the server
    if not os.path.exists(wire):
        st.ok(False, "the wire capture file exists", "wirecapture wrote nothing at all")
        return 1
    # open_capture writes the origin + wire_meta lines immediately, so the file is never
    # empty -- the real question is whether any wire RECORDS were captured. If WinDivert
    # cannot see 127/8 traffic here, this is where it surfaces, named.
    meta, streams, gaps = wc.load_wire(wire)
    if not st.ok(len(streams[wc.C2S]) > 0, "the off-wire capture recorded a c2s stream",
                 f"{len(streams[wc.C2S])} bytes, gaps={gaps[wc.C2S]}" if streams[wc.C2S]
                 else "0 bytes -- WinDivert saw no 127.0.0.1:6112 traffic (does it capture "
                      "loopback on this machine?)"):
        return 1
    if not st.ok(arc4_key is not None, "have the ARC4 key to decrypt with"):
        return 1

    try:
        rep = ls.assemble(wire, arc4_key, decrypted)
        assembled = True
    except ls.SplitError as e:
        assembled = False
        st.ok(False, "assemble split the handshake off the wire stream", str(e))
    if assembled:
        # No "re-encrypt matches" check -- ARC4 is symmetric, so that is true for any key.
        # The real checks are against the server's own bytes: the ciphertext IS what our
        # server recorded, and it decrypts to the plaintext our server logged.
        _a, wire_cipher = ls.split_c2s(streams[wc.C2S])
        raw = auth[:-6] + ".raw"
        srv_cipher = b"".join(c for _i, d, _t, c in replay.read_raw(raw) if d == "c2s") \
            if os.path.exists(raw) else b""
        # Both must be non-empty and agree over their common length -- an empty wire capture
        # (WinDivert saw nothing) must FAIL here, not pass because "" is a prefix of anything.
        n = min(len(wire_cipher), len(srv_cipher))
        st.ok(n > 0 and wire_cipher[:n] == srv_cipher[:n],
              "the off-wire ciphertext matches the server's own .raw over its common length",
              f"wire {len(wire_cipher)}B vs server {len(srv_cipher)}B, compared {n}B")
        first_plain = first_c2s_plain(auth)
        plain = ls.decrypt_stream(wire_cipher, arc4_key)
        st.ok(first_plain and plain[:len(first_plain)] == first_plain,
              "the off-wire capture decrypts to the server's logged plaintext",
              "the whole live pipeline is proven on loopback")

    # Restore the canonical loopback client: the key-tap is opt-in for capture, and leaving
    # vault/run/ tapped would silently change the default a cold session launches. Rebuild
    # plain (same caged path, path-based cage unaffected). Slow but honest.
    print("\n6. restore the plain (non-tapped) loopback client")
    clientpatch = os.path.join(TOOLKIT, "clientpatch")
    b = subprocess.run(PY + [os.path.join(clientpatch, "make_custom_client.py"),
                             "--input", os.path.abspath(pinned_pristine()),
                             "--keys", KEYFILE], capture_output=True, text=True, timeout=300)
    r = subprocess.run(PY + [os.path.join(clientpatch, "make_run_dir.py")],
                       capture_output=True, text=True, timeout=300)
    from keytap_patch import KeyTapError  # noqa: E402
    try:
        keytap_patch.locate_slot(PE(RUN_EXE).data, PE(RUN_EXE))
        still_tapped = True
    except KeyTapError:
        still_tapped = False
    st.ok(b.returncode == 0 and r.returncode == 0 and not still_tapped,
          "the loopback run client is restored to plain (tap is opt-in)",
          "still tapped -- rebuild vault/run manually" if still_tapped else "rebuilt plain")

    print()
    if st.failed:
        print(f"DRY-RUN FAILED: {len(st.failed)} check(s) -- {', '.join(st.failed)}")
        return 1
    print("DRY-RUN GREEN: key-tap -> off-wire capture -> keytap -> assemble -> decrypt, "
          "proven end to end against our own server. The live pipeline is ready.")
    return 0


def pinned_pristine():
    sys.path.insert(0, os.path.join(TOOLKIT, "clientscan"))
    import pinned
    return pinned.find()[0]


def derive_master(auth_jsonl):
    import binascii
    from gwcrypto import arc4_hash  # noqa
    A_hex = seed_hex = None
    for line in open(auth_jsonl, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") == "client_seed":
            A_hex = r.get("a")
        elif r.get("kind") == "server_seed":
            seed_hex = r.get("sent")
    A, seed = binascii.unhexlify(A_hex), binascii.unhexlify(seed_hex)
    k = json.load(open(KEYFILE, encoding="utf-8"))
    shared = pow(int.from_bytes(A, "little"), int(k["server_private"]),
                 int(k["prime"])).to_bytes(64, "little")
    return bytes(m ^ s for m, s in zip(seed, shared[:20])), os.path.basename(KEYFILE)


def first_c2s_plain(auth_jsonl):
    for line in open(auth_jsonl, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") == "frame" and r.get("direction") == "c2s":
            import binascii
            return binascii.unhexlify(r.get("plain", ""))
    return None


if __name__ == "__main__":
    sys.exit(main())
