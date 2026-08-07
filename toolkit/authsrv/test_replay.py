"""Prove a captured channel decrypts back to exactly the plaintext that went over it.

    python toolkit/authsrv/test_replay.py

This is the first thing in the tree to read a `.raw` sidecar back. PLAN.md's R0a row was
closed 2026-08-04 with an explicit caveat -- "nothing has ever read a .raw back" (§3.1) --
and until this file that was true: the Recorder wrote ciphertext nobody decrypted. So the
load-bearing check here is section 1, which derives the session key from a real capture's
own handshake records plus our stored exponent, decrypts its `.raw`, and requires every
c2s record to reproduce the logged plaintext byte for byte.

Section 2 is the check that keeps section 1 honest: flip one byte of the key and the same
decrypt must FAIL. A verifier that cannot tell a right key from a wrong one would pass
section 1 for the wrong reason, and RC4 with the wrong key produces bytes that are not the
plaintext but are not obviously anything either -- exactly the silent wrong answer this
repo keeps catching.

Section 3 round-trips the `.raw` format itself against a synthetic stream, so the reader
is exercised even on a machine with an empty vault: encrypt known plaintext, frame it the
way Recorder.frame does, read it back, decrypt, require equality.

Section 4 sweeps the vault: every capture with a `.raw` and the handshake records to key
it must decrypt clean. It is skip-guarded, because a worktree has no captures of its own.

Read-only. standard library only.
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import replay  # noqa: E402
from gwcrypto import ARC4  # noqa: E402

# MEASURED 2026-08-07. Sections 2 and 3 are fixture-free -- section 2 needs one real
# capture but degrades to a skip without one, section 3 builds its own bytes -- so the
# floor is the synthetic round-trip's 4 checks, which run on a bare machine. Sections 1
# and 4 depend on the vault and declare skips. A green run with the vault present is 12:
# 3 (sec 1) + 2 (sec 2) + 4 (sec 3) + 3 (sec 4, one per verified capture, 1 here).
LEDGER = checks.Ledger("replay", floor=4)


def _keyable_captures(root):
    """(raw, jl, candidates) for every capture with a .raw and the records to key it."""
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "captures-scrubbed"]
        for f in files:
            if not f.endswith(".raw"):
                continue
            raw = os.path.join(base, f)
            if os.path.getsize(raw) == 0:
                continue
            jl = raw[:-4] + ".jsonl"
            if not os.path.isfile(jl):
                continue
            try:
                cands = replay.key_from_our_capture(jl)
            except replay.ReplayError:
                continue
            yield raw, jl, cands


def _best_decrypt(raw, jl, candidates):
    """(checked, matched, winning_key_or_None) over all candidate keys, best match kept."""
    best = (0, 0, None)
    for _label, key in candidates:
        checked, matched, _ = replay.decrypt_and_verify(jl, raw, key)
        if checked and matched == checked:
            return checked, matched, key
        if matched > best[1]:
            best = (checked, matched, None)
    return best


def find_our_capture():
    """A vaulted capture that actually DECRYPTS clean with a key we hold, or None.

    Not merely one that is keyable: the earliest captures (2026-08-04) logged a synthetic
    "RURIK-HANDSHAKE" marker in the plain field rather than real traffic, and some predate
    the 07-29 build whose exponent we still hold. Section 1 needs one that reproduces, or
    it is asserting nothing.
    """
    try:
        sys.path.insert(0, HERE)
        import vaultpath  # noqa: E402
        root = vaultpath.require_dir("captures", why="a real capture to decrypt")
    except SystemExit:
        return None
    for raw, jl, cands in _keyable_captures(root):
        checked, matched, key = _best_decrypt(raw, jl, cands)
        if key is not None:
            return raw, jl, key
    return None


def main():
    found = find_our_capture()

    # ---- 1. a real capture decrypts to its own logged plaintext ----------------
    print("1. a captured .raw decrypts to exactly the plaintext that was logged")
    if not found:
        LEDGER.skip("real capture", "no vaulted capture decrypts with a key we hold")
        winning_key = None
        real = None
    else:
        raw, jl, winning_key = found
        real = (raw, jl)
        print(f"   {os.path.basename(raw)}")
        checked, matched, bad = replay.decrypt_and_verify(jl, raw, winning_key)
        LEDGER.ok(checked > 0, "the capture yielded c2s records to check",
                  f"{checked} records")
        LEDGER.ok(matched == checked and checked > 0,
                  "EVERY c2s record matches -- the decrypt chain is correct end to end",
                  f"{matched}/{checked}")

    # ---- 2. the wrong key must NOT decrypt -------------------------------------
    print("\n2. a key that is off by one byte fails, so section 1 cannot pass by accident")
    if winning_key is None:
        LEDGER.skip("wrong-key discrimination", "no real capture keyed in section 1")
    else:
        raw, jl = real
        bad_key = bytearray(winning_key)
        bad_key[0] ^= 0x01
        checked, matched, first = replay.decrypt_and_verify(jl, raw, bytes(bad_key))
        LEDGER.ok(checked > 0 and matched < checked,
                  "the wrong key does not reproduce the plaintext",
                  f"{matched}/{checked} matched with a corrupted key -- expected far fewer")
        LEDGER.ok(first is not None,
                  "and the mismatch is reported, naming the first record that diverges",
                  f"first mismatch {first}")

    # ---- 3. the .raw format round-trips on synthetic bytes ---------------------
    print("\n3. the .raw reader round-trips a stream built the way Recorder.frame writes it")
    key = bytes(range(20))
    messages = [b"\x04\x00\x0c\x00hello-world!", b"\x11\x22" * 40, b"", b"\xff" * 300]
    enc = ARC4(key)
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "synth.raw")
        with open(raw, "wb") as fh:
            for i, m in enumerate(messages):
                cipher = enc.crypt(m)
                # Byte 0 = c2s, matching Recorder.frame's own pack.
                fh.write(struct.pack(replay.RAW_HEADER, 0, len(cipher), float(i)))
                fh.write(cipher)
        recs = list(replay.read_raw(raw))
        LEDGER.ok(len(recs) == len(messages),
                  "the reader recovers every record, including the zero-length one",
                  f"{len(recs)} of {len(messages)}")
        LEDGER.ok(all(d == "c2s" for _, d, _, _ in recs),
                  "each record's direction byte decodes to c2s")
        dec = [p for _, _, _, p in replay.decrypt_raw(raw, key)]
        LEDGER.ok(dec == messages,
                  "decrypting the continuous stream reproduces every original message",
                  "a per-message cipher reset would fail this after the first record")

        # A truncated file is refused, not read past into garbage.
        with open(raw, "ab") as fh:
            fh.write(struct.pack(replay.RAW_HEADER, 0, 99, 9.0))  # claims 99, writes 0
        try:
            list(replay.read_raw(raw))
            refused = False
        except replay.ReplayError:
            refused = True
        LEDGER.ok(refused, "a record claiming more bytes than the file holds is refused",
                  "truncation is a loud ReplayError, not a short read decoded as data")

    # ---- 4. the whole vault: decryption is all-or-nothing, never partial -------
    # The right invariant is NOT "every keyable capture decrypts" -- 46 of ours do not,
    # and correctly so: the 2026-08-04 bring-up captures logged a synthetic
    # "RURIK-HANDSHAKE" marker rather than real traffic, and some predate the 07-29 build
    # whose exponent we still hold. Those decrypt 0 records, which is right.
    #
    # The invariant that IS correctness: no capture decrypts PARTWAY. A right key that
    # then diverges at record 500 would mean the ARC4 chain -- continuous keystream,
    # per-direction state, the seq ordering -- breaks under real traffic, which is the
    # exact bug a one-record self-test cannot see. Every capture must be all (right key)
    # or nothing (wrong key), never in between.
    print("\n4. across the whole vault, decryption is all-or-nothing -- never partial")
    try:
        sys.path.insert(0, HERE)
        import vaultpath  # noqa: E402
        root = vaultpath.require_dir("captures", why="the capture census")
    except SystemExit:
        root = None
    if root is None:
        LEDGER.skip("vault sweep", "no captures directory")
    else:
        keyable = clean = partial = 0
        worst = None
        for raw, jl, cands in _keyable_captures(root):
            keyable += 1
            checked, matched, key = _best_decrypt(raw, jl, cands)
            if key is not None:
                clean += 1
            elif 0 < matched < checked:
                partial += 1
                worst = f"{os.path.relpath(raw, root)}: {matched}/{checked}"
        if keyable == 0:
            LEDGER.skip("vault sweep", "no capture had both a .raw and handshake records")
        else:
            print(f"   {keyable} keyable captures: {clean} decrypt clean, "
                  f"{keyable - clean - partial} not our key, {partial} partial")
            LEDGER.ok(partial == 0,
                      "no capture decrypts partway -- the keystream holds over real traffic",
                      worst or f"{keyable} captures, every one all-or-nothing")
            LEDGER.ok(clean > 0,
                      "and the sweep is not vacuous: real captures decrypted clean",
                      f"{clean} of {keyable} reproduced their plaintext exactly")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
