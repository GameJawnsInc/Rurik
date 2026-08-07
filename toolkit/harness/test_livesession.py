"""Prove the live driver's offline half and its guards, without a live account.

The driver's RUN half (launch at the real service, sniff, read the key) needs WinDivert,
an elevated shell, and the secondary account, and never runs except behind --confirm. Its
ASSEMBLE half -- reassembled wire streams + the tapped key -> a decrypted, replayable,
LIVE-stamped capture -- is pure, and is where a wrong decrypt would live, so it is grounded
here against REAL captured bytes:

  1. split_c2s / split_s2c parse the plaintext handshake off the front and REFUSE a stream
     that is not the handshake, rather than feeding 82 bytes of something else to ARC4;
  2. on a real loopback session's own c2s ciphertext, split + decrypt reproduce the
     plaintext the server logged -- the same bytes replay.py verifies, reached the wire way;
  3. a full assemble() round-trips both directions to a LIVE capture whose self-consistency
     check (re-encrypt == captured ciphertext) holds, carrying A / server_seed / arc4_key
     under the field names the scrub already treats as secret;
  3b. assemble_live handles the shape a REAL session has and the dry-run never did -- three
     connections (auth, game, and one joined mid-stream) and a keyring of two keys, one per
     DH-keyed channel, because the single tap slot is overwritten at every handshake. It
     must pair each connection with the right key, report the headless one rather than
     crash on it, and -- the one that matters most -- decrypt NOTHING and write NO FILE
     when the right key is absent. ARC4 is symmetric, so "it decrypted" is never evidence;
     the client's own first opcode is;
  4. the guards refuse: the primary account, a non-stock (loopback) launch client, and a
     live run with no --confirm.

standard library only.
"""
import glob
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import checks  # noqa: E402
import origin  # noqa: E402
import livesession as ls  # noqa: E402
import wirecapture as wc  # noqa: E402
from gwcrypto import ARC4, arc4_hash  # noqa: E402

LEDGER = checks.Ledger("livesession", floor=23)


def real_session():
    """A loopback capture we hold the key for: (key, A, seed, c2s_cipher, first_plain) or None."""
    try:
        import vaultpath
        root = vaultpath.require_dir("captures", why="a real session for the assemble test")
    except SystemExit:
        return None
    import replay
    for jl in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        raw = jl[:-6] + ".raw"
        if not os.path.isfile(raw) or os.path.getsize(raw) == 0:
            continue
        A_hex = seed_hex = None
        first_plain = None
        for line in open(jl, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "client_seed":
                A_hex = r.get("a")
            elif r.get("kind") == "server_seed":
                seed_hex = r.get("sent")
            elif r.get("kind") == "frame" and r.get("direction") == "c2s" and first_plain is None:
                first_plain = r.get("plain")
        if not (A_hex and seed_hex and first_plain):
            continue
        try:
            cands = replay.key_from_our_capture(jl)
        except replay.ReplayError:
            continue
        # Concatenate the c2s ciphertext chunks in file order == the continuous stream.
        c2s_cipher = b"".join(c for _i, d, _t, c in replay.read_raw(raw) if d == "c2s")
        for _label, key in cands:
            # The right key is the one that decrypts the first chunk to the logged plain.
            probe = ARC4(key).crypt(c2s_cipher)
            if probe[:len(bytes.fromhex(first_plain))] == bytes.fromhex(first_plain):
                return key, bytes.fromhex(A_hex), bytes.fromhex(seed_hex), c2s_cipher, \
                       bytes.fromhex(first_plain)
    return None


def c2s_handshake(A):
    return (struct.pack("<I", ls.AUTH_VERSION_HEADER) + struct.pack("<III", 38797, 1, 4)
            + struct.pack("<H", ls.CLIENT_SEED_HEADER) + A)


def s2c_handshake(seed):
    return struct.pack("<H", ls.SERVER_SEED_HEADER) + seed


def write_wire(path, c2s, s2c):
    fh, record = wc.open_capture(path, "10.0.0.9:5000", "3.65.1.1:6112", 4242, {6112},
                                 lambda: 0.0)
    record(wc.C2S, 0, c2s)
    record(wc.S2C, 0, s2c)
    fh.close()


def main():
    # ---- 1. split parses and refuses ------------------------------------------
    print("1. split_c2s / split_s2c parse the handshake and refuse what is not")
    A = bytes(range(64))
    seed = bytes(range(100, 120))
    a_got, cipher = ls.split_c2s(c2s_handshake(A) + b"CIPHERC2S")
    LEDGER.ok(a_got == A and cipher == b"CIPHERC2S",
              "split_c2s returns A and the ciphertext after the handshake", a_got.hex()[:16])
    s_got, s_cipher = ls.split_s2c(s2c_handshake(seed) + b"CIPHERS2C")
    LEDGER.ok(s_got == seed and s_cipher == b"CIPHERS2C",
              "split_s2c returns the server seed and the ciphertext after it")
    try:
        ls.split_c2s(b"\x00\x00\x00\x00not a handshake at all............")
        refused = False
    except ls.SplitError:
        refused = True
    LEDGER.ok(refused, "a c2s stream not starting with VERSION is refused, not decrypted")

    # ---- 2. real bytes: split + decrypt reproduce the logged plaintext ---------
    print("\n2. on a real session's own c2s ciphertext, split+decrypt match the log")
    real = real_session()
    if not real:
        LEDGER.skip("real assemble", "no vaulted loopback session with a .raw and a key")
    else:
        key, A, seed, c2s_cipher, first_plain = real
        # Build the c2s WIRE stream: handshake + the real ciphertext.
        _a, cipher = ls.split_c2s(c2s_handshake(A) + c2s_cipher)
        LEDGER.ok(cipher == c2s_cipher,
                  "split recovers exactly the real ciphertext after the handshake",
                  f"{len(cipher)} bytes")
        plain = ls.decrypt_stream(cipher, key)
        LEDGER.ok(plain[:len(first_plain)] == first_plain,
                  "decrypting the wire ciphertext reproduces the server's logged plaintext",
                  "the same bytes replay.py verifies, reached from the wire side")

        # ---- 3. full assemble() round-trips both directions --------------------
        print("\n3. assemble() writes a LIVE, both-direction capture that decrypts correctly")
        # s2c has no vaulted ciphertext (the .raw is c2s only), so synthesise one the
        # honest way: real key, known plaintext, real ARC4. There is deliberately no
        # "re-encrypt matches" assertion -- ARC4 is symmetric, so that holds for any key
        # and would be a check that cannot fail. The real check is that assemble's output
        # equals the KNOWN plaintext, below, which a wrong key would not reproduce.
        s2c_plain_src = b"the server said this, and it must come back out" * 3
        s2c_cipher = ARC4(key).crypt(s2c_plain_src)
        with tempfile.TemporaryDirectory() as tmp:
            wire = os.path.join(tmp, "live.jsonl")
            out = os.path.join(tmp, "decrypted.jsonl")
            write_wire(wire, c2s_handshake(A) + c2s_cipher, s2c_handshake(seed) + s2c_cipher)
            rep = ls.assemble(wire, key, out)
            LEDGER.ok(rep["A"] == A.hex() and rep["server_seed"] == seed.hex(),
                      "the handshake A and server seed are carried into the artifact")
            who, why = origin.origin_of(out)
            LEDGER.ok(who == origin.LIVE, "the assembled capture is stamped origin: live", why)
            recs = [json.loads(l) for l in open(out, encoding="utf-8")]
            c2s_rec = [r for r in recs if r.get("direction") == "c2s"][0]
            LEDGER.ok(bytes.fromhex(c2s_rec["plain"])[:len(first_plain)] == first_plain,
                      "the c2s direction decrypts to the server's real logged plaintext",
                      "a wrong key could not reproduce these bytes")
            s2c = [r for r in recs if r.get("direction") == "s2c"][0]
            LEDGER.ok(bytes.fromhex(s2c["plain"]) == s2c_plain_src,
                      "the s2c direction decrypts back to the known plaintext")
            keys_present = {r.get("kind") for r in recs}
            LEDGER.ok({"session_key", "client_seed", "server_seed"} <= keys_present,
                      "arc4_key / a / sent are recorded under the scrub's own field names",
                      "so scrub_captures.py redacts them before the capture leaves the vault")

    # ---- 3b. the LIVE shape: several connections, several keys -----------------
    print("\n3b. assemble_live pairs keys to connections, and refuses when none fits")
    # A real session is two DH-keyed channels on separate connections with DIFFERENT keys,
    # plus a portal connection that is not a GW channel at all. The single tap slot is
    # overwritten at each handshake, so the driver carries a keyring and the pairing is a
    # search settled by FIRST_C2S_OPCODE -- which a wrong key cannot satisfy.
    auth_key = arc4_hash(bytes(range(20)))
    game_key = arc4_hash(bytes(range(20, 40)))
    wrong_key = arc4_hash(b"\xff" * 20)
    auth_plain = struct.pack("<H", ls.FIRST_C2S_OPCODE["auth"]) + b"\x05\x00hello-auth"
    game_plain = struct.pack("<H", ls.FIRST_C2S_OPCODE["game"]) + b"\x91\x80walking"
    A1, A2 = bytes(range(64)), bytes(range(64, 128))
    seed1, seed2 = bytes(range(20)), bytes(range(40, 60))

    def wire_conn(record, cip, cport, sip, sport, c2s, s2c):
        for direction, payload, a, b, pa, pb in (
                (wc.C2S, c2s, cip, sip, cport, sport),
                (wc.S2C, s2c, sip, cip, sport, cport)):
            record(direction, 1000, payload,
                   {"src": a, "sport": pa, "dst": b, "dport": pb})

    with tempfile.TemporaryDirectory() as tmp:
        wire = os.path.join(tmp, "wire.jsonl")
        fh, record = wc.open_capture(wire, "10.0.0.9:*", None, 4242, {6112, 6601},
                                     lambda: 0.0)
        wire_conn(record, "10.0.0.9", 51000, "3.65.1.1", 6112,
                  c2s_handshake(A1) + ARC4(auth_key).crypt(auth_plain),
                  s2c_handshake(seed1) + ARC4(auth_key).crypt(b"auth said this"))
        wire_conn(record, "10.0.0.9", 51001, "3.65.9.9", 6112,
                  c2s_handshake(A2) + ARC4(game_key).crypt(game_plain),
                  s2c_handshake(seed2) + ARC4(game_key).crypt(b"game said this"))
        # A third connection on a sniffed port whose handshake is NOT at the front -- the
        # realistic live case is a connection the sniff joined mid-stream, or a reconnect.
        # It must be reported, not crashed on, and not fed to ARC4 as if it were a channel.
        wire_conn(record, "10.0.0.9", 51002, "3.65.1.1", 6112,
                  b"\x99\x99 not a handshake, joined mid-stream", b"\x88\x88 nor is this")
        fh.close()

        keyring = [("tap@1.0s", auth_key), ("tap@9.0s", game_key)]
        rep = ls.assemble_live(wire, keyring, tmp)
        by_channel = {r.get("channel"): r for r in rep["connections"] if r.get("decrypted")}
        LEDGER.ok(rep["decrypted"] == 2 and set(by_channel) == {"auth", "game"},
                  "both DH-keyed connections decrypt, each under its own tapped key",
                  f"{rep['decrypted']}/{rep['total']} connections")
        LEDGER.ok(by_channel.get("auth", {}).get("key_from") == "tap@1.0s"
                  and by_channel.get("game", {}).get("key_from") == "tap@9.0s",
                  "each connection is paired with the RIGHT key, not the first one",
                  "swapping them would decrypt to a wrong first opcode")
        auth_out = [json.loads(l) for l in open(by_channel["auth"]["out"], encoding="utf-8")]
        LEDGER.ok(bytes.fromhex([r for r in auth_out
                                 if r.get("direction") == "c2s"][0]["plain"]) == auth_plain,
                  "the auth connection decrypts back to its exact plaintext")
        LEDGER.ok(origin.origin_of(by_channel["game"]["out"])[0] == origin.LIVE,
                  "every file assemble_live writes is stamped origin: live")
        stray = [r for r in rep["connections"] if r["connection"].startswith("10.0.0.9:51002")]
        LEDGER.ok(len(stray) == 1 and not stray[0]["decrypted"]
                  and "no GW handshake" in stray[0]["why"],
                  "a connection with no handshake at its front is reported, not crashed on",
                  "a mid-stream join is a normal outcome of a sniff, not an error")

        # And the case that matters most: a keyring that does NOT hold the right key must
        # produce NOTHING, rather than a plausible-looking file full of garbage.
        before = set(os.listdir(tmp))
        bad = ls.assemble_live(wire, [("tap@0.0s", wrong_key)], tmp)
        LEDGER.ok(bad["decrypted"] == 0,
                  "a keyring with only a WRONG key decrypts nothing at all",
                  "ARC4 is symmetric, so 'it decrypted' is not evidence -- the first "
                  "opcode is")
        LEDGER.ok(set(os.listdir(tmp)) == before,
                  "and it writes no file, so a bad run cannot leave a believable artifact")
        LEDGER.ok(all("none of the 1 tapped key(s)" in r["why"]
                      for r in bad["connections"] if r.get("A")),
                  "the refusal names how many keys were tried")

    LEDGER.ok(ls.channel_of(auth_plain) == "auth" and ls.channel_of(game_plain) == "game",
              "channel_of names the channel from the client's own first opcode")
    LEDGER.ok(ls.channel_of(b"\x00\x00rubbish") is None and ls.channel_of(b"") is None,
              "channel_of refuses anything else, including a truncated stream")

    # ---- 4. the guards refuse --------------------------------------------------
    print("\n4. the guards refuse the primary, a non-stock client, and no --confirm")
    try:
        accounts_primary_refused = False
        import accounts
        try:
            accounts.for_automation("primary")
        except SystemExit:
            accounts_primary_refused = True
    except Exception:
        accounts_primary_refused = True
    LEDGER.ok(accounts_primary_refused, "for_automation refuses the primary account")

    try:
        ls.run("capture", "x", "3.65.1.1", {6112}, 20, confirm=False)
        no_confirm = False
    except ls.LiveError as e:
        no_confirm = "--confirm" in str(e)
    LEDGER.ok(no_confirm, "a live run with no --confirm is refused, naming --confirm")

    # A loopback (ours-DH) client aimed live must be refused by preflight's stock check.
    try:
        import vaultpath
        loop_exe = os.path.join(vaultpath.vault_path("run", "2026-07-29_221c13772c7a"), "Gw.exe")
        have = os.path.isfile(loop_exe)
    except SystemExit:
        have = False
    if not have:
        LEDGER.skip("stock gate", "no loopback client staged to try against a live host")
    else:
        try:
            ls.preflight("capture", loop_exe, "3.65.1.1", want_windivert=False)
            gate = False
        except SystemExit:
            gate = True          # refused: an ours-DH client may never be aimed live
        LEDGER.ok(gate, "an ours-DH loopback client is refused when aimed at a live host",
                  "the stock->live cell is the only one preflight accepts")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
