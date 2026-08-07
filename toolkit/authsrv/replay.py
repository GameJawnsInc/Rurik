"""Read a captured ARC4 channel back into plaintext, from the ciphertext and one exponent.

    python toolkit/authsrv/replay.py <capture-basename-or-.raw>

WHAT THIS IS. The decryption engine R0b's live capture needs, and the tape R1.5 will
play. It takes a `.raw` sidecar (length-prefixed ciphertext, written by authsrv.py's
Recorder) plus the material to derive the session key, and reproduces the plaintext that
went over the wire -- in keystream order, byte for byte.

WHY IT EXISTS SEPARATELY FROM THE SERVER. `authsrv.py` logs plaintext directly because it
performed the handshake and holds the derived key. A LIVE capture never will: ArenaNet's
server holds its exponent and never ships it, and our instrument will hold the *client's*
ephemeral exponent instead. Either way the plaintext is not on the wire -- it is
reconstructed offline from the ciphertext and one private exponent. That reconstruction is
this module, and it is the same operation whichever end's exponent we happen to have.

HOW IT IS TRUSTED. The house rule is verbatim-first: real bytes, replicate one piece,
verify -- and "offline agreement between two of our own components proves nothing." This
does not fall foul of that. The `.raw` is ciphertext; the `.jsonl` beside it logged the
plaintext the server saw; the transform between them (derive the key, run ARC4) is exactly
what a live capture will depend on, and it is non-trivial -- the bespoke `arc4_hash`, the
little-endian shared secret, a continuous keystream per direction. The logged plaintext is
the ORACLE, not a second implementation of the same transform, the way test_codec.py
checks a codec against real captured bytes. Decrypting our own `.raw` back to exactly the
plaintext we recorded is what earns the right to trust this on a live `.raw`, where we
will hold the key but not the answer.

    MEASURED 2026-08-07: authsrv-20260805T215723-c2 decrypts 1068/1068 c2s records to the
    logged plaintext, exactly, with the key derived from rurik_dh_2026-07-29's exponent.

WHAT IT DOES NOT PROVE. That ArenaNet's real AuthSrv sizes and derives its master_secret
the way ours does. Our server_seed format was only ever round-tripped against our own
patched client; the first live capture is what settles it, and until one exists this
engine's correctness is established against our own oracle alone. Stated so a green test
here is not mistaken for a fact about retail.

THE DERIVATION is symmetric, and the module takes the general form:

    shared = peer_public ^ own_private  mod prime        (64 bytes, little-endian)
    master = server_seed  XOR  shared[:20]
    key    = arc4_hash(master)                           (20 bytes)

  a capture of OUR server:  peer_public = client A (on the wire), own_private = b (ours)
  a live capture:           peer_public = server B (in the binary), own_private = a
                            (the client's, from the instrument)

Same shared secret, same key; only which end holds the private exponent differs. There is
one derived key, and two independent ARC4 instances seeded from it -- one per direction --
because the keystream is continuous per direction for the connection's lifetime.

Standard library only. Read-only: it opens capture files and key files, and writes
nothing unless asked for a plaintext dump on an explicit --out.
"""
import binascii
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from gwcrypto import ARC4, arc4_hash  # noqa: E402
import origin  # noqa: E402

# The .raw record header authsrv.py's Recorder.frame writes: a direction byte
# (0 = c2s, 1 = s2c), a u32 ciphertext length, and a float64 capture-relative
# timestamp, followed by that many ciphertext bytes. Kept in ONE place so a reader and
# the writer cannot drift; if Recorder.frame's pack format changes, this constant is
# where the break should surface.
RAW_HEADER = "<BId"
RAW_HEADER_LEN = struct.calcsize(RAW_HEADER)
DIRECTION = {0: "c2s", 1: "s2c"}


class ReplayError(Exception):
    """A capture could not be read or decrypted. Never silently returns garbage."""


def derive_key(peer_public_le, own_private, prime, server_seed):
    """The 20-byte ARC4 key for a session. Symmetric -- see the module docstring.

    `peer_public_le` and `server_seed` are bytes; `own_private` and `prime` are ints.
    Raises rather than returning a plausible-looking wrong key: a 64-byte shared secret
    computed with the wrong endianness or exponent is indistinguishable from a right one
    until the stream fails to decode, far from here.
    """
    if len(server_seed) != 20:
        raise ReplayError(f"server_seed is {len(server_seed)} bytes, expected 20")
    if len(peer_public_le) != 64:
        raise ReplayError(f"peer public value is {len(peer_public_le)} bytes, expected 64")
    A = int.from_bytes(peer_public_le, "little")
    shared = pow(A, own_private, prime).to_bytes(64, "little")
    master = bytes(m ^ s for m, s in zip(server_seed, shared[:20]))
    return arc4_hash(master)


def read_raw(path):
    """Yield (index, direction, t, cipher) for every record in a .raw file, in order.

    Order is the file's own order, which for c2s is keystream order -- Recorder.frame
    takes its seq before the write, and the single c2s decrypt site writes in sequence.
    """
    with open(path, "rb") as fh:
        idx = 0
        while True:
            hdr = fh.read(RAW_HEADER_LEN)
            if not hdr:
                return
            if len(hdr) < RAW_HEADER_LEN:
                raise ReplayError(f"{os.path.basename(path)}: truncated record header "
                                  f"at record {idx} ({len(hdr)} of {RAW_HEADER_LEN} bytes)")
            dbyte, n, t = struct.unpack(RAW_HEADER, hdr)
            cipher = fh.read(n)
            if len(cipher) < n:
                raise ReplayError(f"{os.path.basename(path)}: record {idx} claims {n} "
                                  f"cipher bytes, file holds {len(cipher)}")
            yield idx, DIRECTION.get(dbyte, dbyte), t, cipher
            idx += 1


def decrypt_raw(raw_path, key):
    """Decrypt a .raw stream. Yields (index, direction, t, plaintext).

    One ARC4 per direction, created once and advanced continuously, because that is how
    the channel runs: the keystream is not reset per message. Feeding two directions'
    ciphertext through one cipher -- the obvious shortcut when a .raw holds only c2s --
    would desync the instant an s2c record appeared, so the split is kept even though
    today's captures are one-directional.
    """
    ciphers = {"c2s": ARC4(key), "s2c": ARC4(key)}
    for idx, direction, t, cipher in read_raw(raw_path):
        c = ciphers.get(direction)
        if c is None:
            raise ReplayError(f"record {idx} has unknown direction byte {direction!r}")
        yield idx, direction, t, c.crypt(cipher)


def _sibling_jsonl(raw_path):
    jl = raw_path[:-4] + ".jsonl" if raw_path.endswith(".raw") else raw_path + ".jsonl"
    return jl if os.path.isfile(jl) else None


def key_from_our_capture(jsonl_path, keydir=None):
    """Derive the session key for a capture OF OUR OWN SERVER, from its .jsonl + our keys.

    The .jsonl carries the client's public A (`client_seed`) and the seed the server sent
    (`server_seed`); the key file carries the exponent b and the prime. This is the
    server-side framing, and it exists so the engine can be exercised against the vault
    we already hold. A live capture will NOT use this -- it has no server exponent -- and
    supplies its key material directly to derive_key() instead.

    Returns (key, detail) or raises ReplayError naming what was missing.
    """
    import glob
    if keydir is None:
        sys.path.insert(0, HERE)
        import vaultpath  # noqa: E402
        keydir = vaultpath.vault_path("keys")

    A_hex = seed_hex = None
    with open(jsonl_path, encoding="utf-8", errors="replace") as fh:
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
        raise ReplayError(f"{os.path.basename(jsonl_path)}: no client_seed/server_seed "
                          f"records -- cannot derive a key from this capture")
    A = binascii.unhexlify(A_hex)
    seed = binascii.unhexlify(seed_hex)

    tried = []
    for kf in sorted(glob.glob(os.path.join(keydir, "rurik_dh_*.json"))):
        try:
            k = json.load(open(kf, encoding="utf-8"))
            prime, b = int(k["prime"]), int(k["server_private"])
        except (OSError, ValueError, KeyError):
            continue
        key = derive_key(A, b, prime, seed)
        # Whether it is the RIGHT key is decided by decrypt_and_verify, not here; but if
        # there are several key files, the caller wants the one that actually decrypts.
        # Return each as a candidate with its label so the caller can pick.
        tried.append((os.path.basename(kf), key))
    if not tried:
        raise ReplayError(f"no usable rurik_dh_*.json in {keydir}")
    return tried


def decrypt_and_verify(jsonl_path, raw_path, key):
    """Decrypt the .raw and check every c2s record against the .jsonl's logged plaintext.

    Returns (checked, matched, first_mismatch). first_mismatch is None on a clean run, or
    (index, want_hex, got_hex) -- this is the assertion the artifact can refute: the
    plaintext came from the server's own log, the ciphertext from the wire, and nothing
    here forces them to agree.
    """
    logged = []
    with open(jsonl_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(r, dict) and r.get("kind") == "frame" and r.get("direction") == "c2s":
                logged.append(r.get("plain", ""))

    checked = matched = 0
    first_mismatch = None
    li = 0
    for idx, direction, t, plain in decrypt_raw(raw_path, key):
        if direction != "c2s":
            continue
        if li >= len(logged):
            break
        want = binascii.unhexlify(logged[li])
        li += 1
        # The .jsonl stores only the first 512 plaintext bytes of each frame (Recorder
        # truncates the hex for size); compare over that prefix, which is what exists to
        # compare against.
        got = plain[:len(want)]
        checked += 1
        if got == want:
            matched += 1
        elif first_mismatch is None:
            first_mismatch = (idx, want[:16].hex(), got[:16].hex())
    return checked, matched, first_mismatch


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("\n  python toolkit/authsrv/replay.py <capture-basename-or-.raw>")
        return 2
    arg = sys.argv[1]
    raw_path = arg if arg.endswith(".raw") else arg + ".raw"
    if not os.path.isfile(raw_path):
        raise SystemExit(f"no such .raw file: {raw_path}")
    jsonl_path = _sibling_jsonl(raw_path)
    if not jsonl_path:
        raise SystemExit(f"no .jsonl beside {os.path.basename(raw_path)} -- this reader "
                         f"needs it both for the key and for the plaintext to check against")

    who, why = origin.origin_of(jsonl_path)
    print(f"capture : {os.path.relpath(raw_path, os.getcwd())}")
    print(f"origin  : {who} ({why})")
    if who == origin.LIVE:
        print("          A live capture holds no server exponent; this CLI derives the key")
        print("          the server-side way and will not find one. Supply the client's")
        print("          exponent to derive_key() directly -- see the module docstring.")

    candidates = key_from_our_capture(jsonl_path)
    for label, key in candidates:
        checked, matched, bad = decrypt_and_verify(jsonl_path, raw_path, key)
        tag = "MATCH" if (checked and matched == checked) else "no"
        print(f"  key {label}: {matched}/{checked} c2s records reproduce the log  [{tag}]")
        if bad:
            print(f"      first mismatch at #{bad[0]}: want {bad[1]} got {bad[2]}")
        if checked and matched == checked:
            return 0
    print("No key file reproduced the logged plaintext. If this capture is ours, the "
          "exponent that keyed it is not in vault/keys.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
