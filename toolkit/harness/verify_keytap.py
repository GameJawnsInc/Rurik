"""The loopback check the key-tap has to pass before it is ever used live.

    python toolkit/harness/verify_keytap.py --exe <run>/Gw.exe --pid <n> --capture <auth.jsonl>

The key-tap plants a cave that copies the session's master_secret to a data slot as it is
formed (studies/livekey/CODECAVE.md). This confirms the cave actually ran and wrote the
RIGHT bytes, the only way that can be checked without trusting the live service: on
loopback, OUR server logged the same session's client public value and server seed, so we
derive the master_secret independently and require the 20 bytes the client stashed to equal
it, exactly.

  the client's slot   read from process memory via keytap.py (ASLR-correct)
  the truth           master_secret = arc4_hash-input we derive from the capture + our key

A match proves the tap reads the real key material and the cave is correct end to end. A
mismatch, a zero read (cave never ran -- a crash, or the wrong instruction), or a client
that died before the handshake is a red result naming which. Only when this is green does
the same patch go on the stock-DH live build.

Read-only against the client (PROCESS_VM_READ). standard library only.
"""
import argparse
import binascii
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import keytap  # noqa: E402
import keytap_patch  # noqa: E402
from gwpe import PE  # noqa: E402
from gwcrypto import arc4_hash  # noqa: E402


def derive_master(capture_path, keydir):
    """The master_secret OUR server derived for the session in `capture_path`.

    From the capture's own client_seed (the client public A on the wire) and server_seed,
    plus the exponent b in our key file: shared = A^b mod p, master = server_seed XOR
    shared[:20]. This is the same derivation replay.py trusts, and the value the client's
    slot must match. Returns (master_bytes, key_label) or raises.
    """
    A_hex = seed_hex = None
    with open(capture_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(r, dict):
                continue
            if r.get("kind") == "client_seed" and r.get("a"):
                A_hex = r["a"]
            elif r.get("kind") == "server_seed" and r.get("sent"):
                seed_hex = r["sent"]
    if not A_hex or not seed_hex:
        raise SystemExit(f"{os.path.basename(capture_path)} has no client_seed/server_seed "
                         f"-- the handshake did not complete, so there is no key to check.")
    A = binascii.unhexlify(A_hex)
    seed = binascii.unhexlify(seed_hex)
    for kf in sorted(glob.glob(os.path.join(keydir, "rurik_dh_*.json"))):
        try:
            k = json.load(open(kf, encoding="utf-8"))
            p, b = int(k["prime"]), int(k["server_private"])
        except (OSError, ValueError, KeyError):
            continue
        shared = pow(int.from_bytes(A, "little"), b, p).to_bytes(64, "little")
        master = bytes(m ^ s for m, s in zip(seed, shared[:20]))
        # We do not know which key file keyed this session; return the first and let the
        # caller's equality check decide. In practice authsrv loads the newest by name.
        return master, os.path.basename(kf)
    raise SystemExit(f"no usable rurik_dh_*.json in {keydir}")


def check(exe, pid, capture, keydir):
    """(ok, detail). The comparison that can fail."""
    pe = PE(exe)
    try:
        slot_rva, slot_va = keytap_patch.locate_slot(pe.data, pe)
    except keytap_patch.KeyTapError as e:
        return False, f"this client is not key-tapped: {e}"

    module = os.path.basename(exe)
    got = keytap.read_rva(pid, module, slot_rva, keytap_patch.SLOT_SIZE)
    if got is None:
        return False, (f"could not read the slot at {module}+0x{slot_rva:x} in pid {pid} "
                       f"(is the client still alive?)")
    if not any(got):
        return False, (f"the slot is all zero: the cave never wrote it. The handshake may "
                       f"not have run, or the tap is on the wrong instruction.")

    master, label = derive_master(capture, keydir)
    if got == master:
        return True, (f"slot == derived master_secret ({got.hex()}), key {label} -- the "
                      f"tap read the real key material, cave correct end to end")
    return False, (f"MISMATCH\n  slot    : {got.hex()}\n  derived : {master.hex()} "
                   f"(key {label})\n  the cave ran but stashed the wrong bytes.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", required=True, help="the key-tapped run client on disk")
    ap.add_argument("--pid", type=int, required=True, help="the running client's pid")
    ap.add_argument("--capture", required=True,
                    help="the authsrv .jsonl for this session (for client_seed/server_seed)")
    ap.add_argument("--keydir", default=r"C:\gd\Rurik\vault\keys")
    a = ap.parse_args()
    ok, detail = check(a.exe, a.pid, a.capture, a.keydir)
    print(("[PASS] " if ok else "[FAIL] ") + detail)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
