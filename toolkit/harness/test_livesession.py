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

LEDGER = checks.Ledger("livesession", floor=32)


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


def game_c2s_handshake(A, acct=b"\xaa" * 16, char=b"\xbb" * 16):
    """The GAME channel's VERSION, whose body is 60 bytes rather than the auth shape's 12.

    Built from the live capture of 2026-08-07: header 0x000C0500, then build/1/id/n/n, two
    16-byte uuid-shaped fields and eight zero bytes, and only THEN CLIENT_SEED -- at offset
    64 instead of 16. Our own server never speaks this shape, so nothing on loopback could
    have produced it and the first live run decrypted 1 of 7 connections because of it.
    """
    body = (struct.pack("<IIIII", 38797, 1, 0xE10DEFA9, 0x0202, 0x3D534856)
            + acct + char + b"\x00" * 8)
    assert len(body) == 60, len(body)
    return (struct.pack("<I", ls.GAME_VERSION_HEADER) + body
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

    # The GAME shape. Its body is 60 bytes, not 12, so CLIENT_SEED is at offset 64 -- and
    # a reader that assumes the auth shape refuses every game connection in a live capture.
    g_got, g_cipher = ls.split_c2s(game_c2s_handshake(A) + b"GAMECIPHER")
    LEDGER.ok(g_got == A and g_cipher == b"GAMECIPHER",
              "split_c2s parses the GAME version shape too (CLIENT_SEED at 64, not 16)",
              "OBSERVED from the 2026-08-07 live capture: 6 of its 7 connections")
    try:
        ls.split_c2s(struct.pack("<I", 0x000C0600) + b"\x00" * 200)
        unknown_ok = False
        why = ""
    except ls.SplitError as ex:
        unknown_ok, why = True, str(ex)
    LEDGER.ok(unknown_ok and "0x000c0400" in why and "0x000c0500" in why,
              "an UNKNOWN version header is still refused, and the refusal names what it "
              "does know", "a third shape must stop the reader, not be guessed past")

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
    # plus one carrying no handshake. The single tap slot is overwritten at each handshake,
    # so the driver carries a keyring; the channel comes from each connection's VERSION
    # header and the KEY is settled by key_fits, which a wrong key rarely satisfies.
    auth_key = arc4_hash(bytes(range(20)))
    game_key = arc4_hash(bytes(range(20, 40)))
    auth_plain = struct.pack("<H", 0x8001) + b"\x05\x00hello-auth"     # OBSERVED live
    game_plain = struct.pack("<H", 0x808a) + b"\x91\x80walking"        # OBSERVED loopback
    # key_fits passes 487 of 65536 values, so a fixed "wrong" key could pass by luck and
    # make the refusal test vacuous. Pick one that demonstrably fails BOTH connections,
    # and fail loudly if no candidate does rather than testing nothing.
    wrong_key = None
    for n in range(64):
        cand = arc4_hash(bytes([n]) * 20)
        if cand not in (auth_key, game_key) and not any(
                ls.key_fits(ARC4(cand).crypt(ARC4(k).crypt(p)))
                for k, p in ((auth_key, auth_plain), (game_key, game_plain))):
            wrong_key = cand
            break
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
                  game_c2s_handshake(A2) + ARC4(game_key).crypt(game_plain),
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
        LEDGER.ok(wrong_key is not None,
                  "a genuinely non-fitting key was found for the refusal test below",
                  "otherwise that assertion would pass without testing anything")
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

    LEDGER.ok(ls.channel_of_stream(c2s_handshake(A)) == "auth"
              and ls.channel_of_stream(game_c2s_handshake(A)) == "game",
              "the channel is read from the VERSION header, the field that carries it",
              "not guessed from whichever opcode the first message happens to be")
    LEDGER.ok(all(ls.key_fits(struct.pack("<H", op))
                  for op in (0x8001, 0x800a, 0x8091, 0x808a)),
              "key_fits accepts every first opcode OBSERVED, live and on loopback",
              "the old literal-value table rejected 0x800a and 0x8091 and reported two "
              "live connections undecryptable whose keys we were holding")
    LEDGER.ok(not ls.key_fits(struct.pack("<H", 0x0001))
              and not ls.key_fits(struct.pack("<H", 0xcad4))
              and not ls.key_fits(b""),
              "and rejects a clear direction bit, an out-of-catalog opcode, and no bytes",
              "487 of 65536 values pass, so a wrong key still has roughly 1 in 135")

    # ---- 3c. the keyring reaches DISK, and a capture re-assembles from it -------
    print("\n3c. the keyring is persisted per key, and re-assembly works without a client")
    # The first live run held its keyring in memory: 7 keys tapped, 1 written (by the one
    # connection that assembled), and 6 channels of real ArenaNet ciphertext became
    # permanently undecryptable when the process exited. There is no recovering those --
    # the key derives from ArenaNet's private exponent. So the keyring is written as each
    # key appears, and a capture directory can be decoded again from its own two files.
    with tempfile.TemporaryDirectory() as tmp:
        kr = os.path.join(tmp, "keyring.jsonl")
        ring = ls.KeyRing.__new__(ls.KeyRing)      # no live process to poll
        ring.path, ring.errors = kr, 0
        with open(kr, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(origin.record("test", origin.LIVE)) + "\n")
        ring._persist(1.04, bytes(range(20)), auth_key)
        ring._persist(9.10, bytes(range(20, 40)), game_key)
        back = ls.load_keyring(kr)
        LEDGER.ok([k for _l, k in back] == [auth_key, game_key],
                  "every tapped key is on disk, in order, and reads back exactly",
                  f"{len(back)} keys -- written per key, not per run")
        LEDGER.ok(origin.origin_of(kr)[0] == origin.LIVE,
                  "the keyring file is itself stamped origin: live")
        raw = open(kr, encoding="utf-8").read()
        LEDGER.ok("master_secret" in raw and "arc4_key" in raw,
                  "it records master_secret AND the derived key, under names the scrub "
                  "treats as secret", "so a re-derivation is possible if arc4_hash changes")

        # A whole capture directory, decoded again from nothing but its own two files.
        rd = os.path.join(tmp, "capture")
        os.makedirs(rd)
        fh, record = wc.open_capture(os.path.join(rd, "wire.jsonl"), "10.0.0.9:*", None,
                                     0, {6112}, lambda: 0.0)
        wire_conn(record, "10.0.0.9", 51000, "3.65.1.1", 6112,
                  c2s_handshake(A1) + ARC4(auth_key).crypt(auth_plain),
                  s2c_handshake(seed1) + ARC4(auth_key).crypt(b"auth said this"))
        wire_conn(record, "10.0.0.9", 51001, "3.65.9.9", 6112,
                  game_c2s_handshake(A2) + ARC4(game_key).crypt(game_plain),
                  s2c_handshake(seed2) + ARC4(game_key).crypt(b"game said this"))
        fh.close()
        import shutil
        shutil.copy(kr, os.path.join(rd, "keyring.jsonl"))
        rc = ls.reassemble(rd)
        LEDGER.ok(rc == 0, "reassemble() decodes a capture directory with no client, no "
                           "network and no account", "R0b's 'byte-replayable from disk'")
        outs = sorted(f for f in os.listdir(rd) if f.startswith(("auth-", "game-")))
        LEDGER.ok(len(outs) == 2,
                  "both an auth-shaped and a GAME-shaped connection come back",
                  ", ".join(outs))

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
