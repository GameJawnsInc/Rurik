"""The wire's two shapes and how a capture is assembled: VERSION headers, direction bit, key.

Split out of `toolkit/harness/livesession.py`, where every name below is still re-exported
at the site it used to occupy. `livesession.split_c2s`, `livesession.assemble_live`,
`livesession.prune_wire` and the rest keep working: `toolkit/harness/test_livesession.py`
reads 13 of them as `ls.<name>`, `toolkit/harness/dryrun_keycapture.py` reads
`ls.split_c2s` and `ls.decrypt_stream`, and `livesession.run()` calls `prune_wire` and
`assemble_live` as bare globals.

WHY THIS IS ITS OWN MODULE. `toolkit/authsrv/cmsgstream.py` is imported by nine analysis
modules and wanted three pure functions from here -- `split_c2s`, `split_s2c`,
`decrypt_stream`, which take bytes and return bytes. Importing `livesession` to reach them
loaded `accounts`, `marks` and the whole live orchestration on every one of those nine, and
pushed `clientpatch` and `mapdata` onto `sys.path` behind them. MEASURED after the repoint:
`import cmsgstream` loads neither `livesession` nor `accounts` nor `marks`, and neither
`clientpatch` nor `mapdata` is on `sys.path`. What it loads instead is what it was already
using -- `wirecapture`, `vaultpath`, `codec` -- plus `origin`, `gwcrypto` and `liveerror`.

Four `sys.path` inserts, not six. HERE reaches `wirecapture` and `liveerror`, the toolkit
root reaches `origin`, `authsrv` reaches `gwcrypto` (and the late `import tape` in
`build_for`), `schema` reaches `codec`. `clientpatch` and `mapdata` are livesession's, for
`keytap_patch` and `datcheck`, and copying them would push both onto `sys.path` for every
analysis module downstream of `cmsgstream` -- which is the cost this split exists to remove.

THE REFERENTS OF THREE MOVED COMMENTS STAY IN `livesession.py`, and the comments below are
verbatim, so the pointers are here instead of reworded there:

  * `assemble_live`'s docstring -- "that is why run() records a keyring (every distinct
    value the slot took, in order) rather than one key" -- is about `livesession.run()`.
  * the dedup comment inside it names `load_keyring`, which labels a keyring entry
    "tap@?s" when its `t` is missing; that reader is `livesession.load_keyring`.
  * `LIVE_PORTS` and its 39-line comment deliberately stay in `livesession.py` (the port
    list is the sniffer's argument, not the splitter's), and that comment ends by naming
    `prune_wire`, which is here.

READ AND WRITE, but nothing live: every function here takes a path or bytes. The capture
is read through `wirecapture`, the decrypted channels are written beside it, and nothing
in this module launches, sniffs or taps.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import origin  # noqa: E402
import wirecapture as wc  # noqa: E402
from gwcrypto import ARC4  # noqa: E402
from codec import Codec  # noqa: E402  -- the full-stream key tie-break, _frames_completely
from liveerror import SplitError  # noqa: E402

# Handshake framing, plaintext on the wire, from authsrv.py's own reader:
#   c2s: VERSION (u32 header + body) then CLIENT_SEED (u16 0x4200 + 64B A)
#   s2c: SERVER_SEED (u16 0x1601 + 20B)
#
# THE VERSION MESSAGE HAS TWO SHAPES, and we only knew one until a live session showed the
# other. OBSERVED 2026-08-07 from the first live capture (7 connections to ArenaNet, build
# 38797 on the wire in every one):
#
#   auth  header 0x000C0400, 12-byte body: <u32 build> <u32 1> <u32 4>
#   game  header 0x000C0500, 60-byte body: <u32 build> <u32 1> <u32 id> <u32 n> <u32 n>
#                                          <16B account uuid> <16B character uuid> <8B 0>
#
# so CLIENT_SEED sits at offset 16 on auth and offset 64 on game. MEASURED: `00 42` occurs
# exactly once in the first 200 bytes of every one of the seven streams, at 16 for the auth
# connection and at 64 for all six game connections -- there is no ambiguity to resolve.
# The two 16-byte fields read as uuids because they are CONSTANT across connections in the
# way uuids would be: the first is identical in all six, and the second is identical in five
# and ZERO in the earliest one -- which is the connection made before the new character
# existed. That reading is RECONSTRUCTION; the offsets are OBSERVED and are all this code
# depends on.
#
# Our own server only ever speaks the auth shape, so no loopback capture could have shown
# this. The first live run decrypted 1 of 7 connections because of it.
AUTH_VERSION_HEADER = 0x000C0400
GAME_VERSION_HEADER = 0x000C0500
VERSION_BODY_LEN = {AUTH_VERSION_HEADER: 12, GAME_VERSION_HEADER: 60}
CLIENT_SEED_HEADER = 0x4200
SERVER_SEED_HEADER = 0x1601
VERSION_LEN = 4 + VERSION_BODY_LEN[AUTH_VERSION_HEADER]   # the auth shape, for callers
CLIENT_SEED_LEN = 2 + 64
SERVER_SEED_LEN = 2 + 20

# WHICH CHANNEL a connection is comes from its VERSION header, which is the field that
# actually carries it -- not from guessing at an opcode.
VERSION_CHANNEL = {AUTH_VERSION_HEADER: "auth", GAME_VERSION_HEADER: "game"}

# WHETHER A KEY IS RIGHT is a separate question, and this is the test.
#
# The first version of this listed literal opcodes -- auth 0x8001, game 0x808a -- taken
# from our own captures. It was wrong, and the live capture of 2026-08-07 proved it: the
# real service's game channels opened with 0x800a and 0x8091, so two connections whose keys
# we HAD were reported undecryptable. A criterion derived from one server's flow does not
# generalise to another's, and the fix is to test a structural property instead of a value.
#
# MEASURED over 534 captures (loopback plus both live ones): the first client->server u16
# has bit 15 SET in 400 of 409 -- the nine exceptions are the 2026-08-04 synthetic
# RURIK-HANDSHAKE markers, not real traffic -- while server->client never sets it. So bit
# 15 is a direction flag, and the remaining 15 bits are an opcode: strip it from every
# observed first message (0x8001, 0x800a, 0x8091, 0x808a -> 1, 10, 145, 138) and all of
# them land inside schema/messages.json's own range, which spans 0x0000-0x01E6 across 777
# entries.
#
# So a candidate key is accepted only if its plaintext starts with the direction bit set
# AND an opcode the catalog could hold. That is 487 of 65536 values, ~1 in 135 for a wrong
# key -- weaker per-trial than a literal match but it accepts the traffic that exists, and
# on the live capture it picks exactly one key per connection, right every time, out of
# three candidates each. Still a check that CAN fail, which is the requirement.
CMSG_DIRECTION_BIT = 0x8000
MAX_CATALOG_OPCODE = 0x01E6


# ------------------------------------------------------- the offline assembly --
def split_c2s(stream):
    """(A, ciphertext) from a client->server stream that starts with the handshake.

    Parses rather than trusts a fixed offset, so a stream that is not the handshake is a
    loud SplitError instead of 82 bytes of something else fed to the decryptor.
    """
    if len(stream) < 4:
        raise SplitError(f"c2s stream is {len(stream)} bytes, too short for a header")
    header = int.from_bytes(stream[0:4], "little")
    if header not in VERSION_BODY_LEN:
        raise SplitError(f"c2s does not start with VERSION (got header 0x{header:08x}; "
                         f"known: " +
                         ", ".join(f"0x{h:08x}" for h in sorted(VERSION_BODY_LEN)) + ")")
    version_len = 4 + VERSION_BODY_LEN[header]
    if len(stream) < version_len + CLIENT_SEED_LEN:
        raise SplitError(f"c2s stream is {len(stream)} bytes, too short for the handshake")
    seed_hdr = int.from_bytes(stream[version_len:version_len + 2], "little")
    if seed_hdr != CLIENT_SEED_HEADER:
        raise SplitError(f"CLIENT_SEED header is 0x{seed_hdr:04x} at offset {version_len}, "
                         f"expected 0x4200")
    a_off = version_len + 2
    A = stream[a_off:a_off + 64]
    return A, stream[version_len + CLIENT_SEED_LEN:]


def split_s2c(stream):
    """(server_seed, ciphertext) from a server->client stream starting with SERVER_SEED."""
    if len(stream) < SERVER_SEED_LEN:
        raise SplitError(f"s2c stream is {len(stream)} bytes, too short for SERVER_SEED")
    header = int.from_bytes(stream[0:2], "little")
    if header != SERVER_SEED_HEADER:
        raise SplitError(f"s2c does not start with SERVER_SEED (got 0x{header:04x})")
    seed = stream[2:2 + 20]
    return seed, stream[SERVER_SEED_LEN:]


def decrypt_stream(cipher, key):
    """Plaintext for one direction: ARC4(key) run continuously over the ciphertext."""
    return ARC4(key).crypt(cipher)


def assemble(wire_path, key, out_path):
    """Turn a wire capture + the tapped key into a decrypted, replayable, LIVE capture.

    Returns a dict of what it produced. Raises SplitError if either direction does not
    carry the handshake it must. The output mirrors the server's own capture shape so
    replay.py and the scrub both already understand it, and it records A / server_seed /
    arc4_key under the field names scrub_captures.py already treats as secret.
    """
    meta, streams, gaps = wc.load_wire(wire_path)
    A, c2s_cipher = split_c2s(streams[wc.C2S])
    seed, s2c_cipher = split_s2c(streams[wc.S2C])
    c2s_plain = decrypt_stream(c2s_cipher, key)
    s2c_plain = decrypt_stream(s2c_cipher, key)

    # There is deliberately NO "re-encrypt and compare" self-check here: ARC4 is symmetric,
    # so decrypt(decrypt(cipher)) == cipher for EVERY key, right or wrong -- it would be a
    # check that cannot fail. Validating the key needs an independent oracle: on loopback,
    # our server's own logged plaintext (dryrun_keycapture.py); on a live capture there is
    # none, so the key's correctness rests on the keytap having been proven on loopback and
    # on the decrypted stream framing cleanly downstream, not on anything provable here.

    # DERIVE the stamp, and RECORD what it was derived from. This site hardcoded LIVE and
    # wrote no address at all, which is the worst of both: dryrun_keycapture.py drives it
    # against 127.0.0.1, so vault/dryrun/dryrun_decrypted.jsonl claimed to be live traffic,
    # and because it named no endpoint the contradiction check had nothing to catch it
    # with. Deriving without recording would have left it merely unfalsifiable; the
    # `endpoints` record below is what lets a reader disagree with the stamp.
    endpoints = [str(meta.get("client", "")), str(meta.get("server", ""))] if meta else []
    addrs = [e for e in endpoints if origin.is_address(e)]
    who = origin.OURS if addrs and all(origin.is_loopback(a) for a in addrs) else origin.LIVE
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(origin.record("toolkit/harness/livesession.py", who,
                                          note="decrypted from an off-wire capture")) + "\n")
        fh.write(json.dumps({"kind": "endpoints", "client": endpoints[0] if endpoints else "",
                             "server": endpoints[1] if len(endpoints) > 1 else ""}) + "\n")
        fh.write(json.dumps({"kind": "session_key", "arc4_key": key.hex()}) + "\n")
        fh.write(json.dumps({"kind": "client_seed", "a": A.hex()}) + "\n")
        fh.write(json.dumps({"kind": "server_seed", "sent": seed.hex()}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "c2s",
                             "plain": c2s_plain.hex()}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                             "plain": s2c_plain.hex()}) + "\n")
    return {"out": out_path, "c2s_bytes": len(c2s_plain), "s2c_bytes": len(s2c_plain),
            "gaps": {k: gaps[k] for k in gaps if gaps[k]},
            "A": A.hex(), "server_seed": seed.hex()}


def key_fits(plain):
    """Does this decrypted c2s stream look like real client traffic? See CMSG_DIRECTION_BIT.

    Two bytes decide it: the direction bit must be set and the opcode must be one the
    catalog could hold. Deliberately NOT a channel verdict -- the channel comes from the
    VERSION header, which is the field that carries it.
    """
    if len(plain) < 2:
        return False
    op = int.from_bytes(plain[:2], "little")
    return bool(op & CMSG_DIRECTION_BIT) and (op & ~CMSG_DIRECTION_BIT) <= MAX_CATALOG_OPCODE


def _frames_completely(s2c_cipher, key):
    """Does this key decrypt the WHOLE server stream into messages, to the last byte?

    The tie-break `key_fits` cannot be: it reads two bytes, and two bytes are cheap to
    spell by accident. This walks the entire decrypted stream through the real catalog and
    demands `consumed == len(plain)` with no error -- the same standard `tape.decode_all`
    holds every tape in the vault to. A wrong ARC4 key produces noise from the first
    message onward, and noise does not frame to an exact landing.

    Deliberately answers only True/False and swallows nothing else: any decode failure IS
    the answer this returns, so a catalog gap and a wrong key look the same here. That is
    acceptable ONLY because the caller uses this to NARROW a set it already has, never to
    accept a key on its own -- a genuinely unknown opcode mid-stream would make every
    candidate fail and the caller refuses, which is the safe direction.
    """
    try:
        plain = decrypt_stream(s2c_cipher, key)
        _msgs, consumed, err = Codec().decode_stream_at("GAME_SMSG", plain, 0)
    except Exception:                                    # noqa: BLE001 -- see docstring
        return False
    return err is None and consumed == len(plain) and consumed > 0


def channel_of_stream(c2s_stream):
    """'auth' / 'game' from a c2s stream's VERSION header, or None if it has none."""
    if len(c2s_stream) < 4:
        return None
    return VERSION_CHANNEL.get(int.from_bytes(c2s_stream[0:4], "little"))


def build_for(wire_path, connection):
    """The client build for one connection, or None. NEVER a guess.

    Closes the asymmetry `tape.client_version`'s own docstring records: the
    decrypted `game-*.jsonl` did not carry the build, so `origin.build_of` had
    nothing to infer from and every live capture in the vault classifies as
    build-unknown. The number is the CLIENT's, parsed from its own VERSION frame
    in `wire.jsonl` -- not from anything we wrote, and not from `pinned.BUILD`,
    which would be us telling ourselves what we already assumed.

    Any failure returns None and the field is omitted. An unstamped capture is a
    known gap; a wrongly stamped one is a fact nobody can refute later.
    """
    try:
        import tape                                          # noqa: PLC0415
        return tape.client_version(os.path.dirname(wire_path), connection)["build"]
    except Exception:                                        # noqa: BLE001
        return None


def assemble_live(wire_path, keyring, out_dir):
    """Turn ONE live wire capture (several connections) + a keyring into decrypted files.

    A real session is not the dry-run's single loopback socket. The client opens the portal
    (Stage A), then the auth channel, then the game server on a different address (PLAN
    §1.6) -- and each DH-keyed channel derives its OWN master_secret, so the single tap slot
    holds a DIFFERENT value at different moments. That is why run() records a keyring (every
    distinct value the slot took, in order) rather than one key: a run that reaches the world
    has already overwritten the auth channel's secret by the time it stops.

    Pairing keys to connections is therefore a search, not a lookup, and it is settled by a
    criterion the artifact can refute: try every key against every connection and accept the
    pair only when the decrypted c2s stream starts with the opcode the client always sends.
    A connection nothing decrypts is reported as undecrypted and its raw bytes are KEPT --
    never dropped, and never written out under a key that did not fit.

    Returns a report dict. Writes one file per decrypted connection into out_dir.
    """
    meta, conns = wc.load_connections(wire_path)
    keys = [(label, k) for label, k in keyring if k]
    results = []
    for key_name, entry in sorted(conns.items(), key=lambda kv: str(kv[0])):
        row = {"connection": key_name,
               "c2s_wire_bytes": len(entry[wc.C2S]), "s2c_wire_bytes": len(entry[wc.S2C]),
               "gaps": {d: entry["gaps"][d] for d in entry["gaps"] if entry["gaps"][d]}}
        try:
            A, c2s_cipher = split_c2s(entry[wc.C2S])
            seed, s2c_cipher = split_s2c(entry[wc.S2C])
        except SplitError as exc:
            # Expected for the portal connection: Stage A is not a DH-keyed channel at all.
            row.update({"decrypted": False, "why": f"no GW handshake on this connection: {exc}"})
            results.append(row)
            continue
        row["A"] = A.hex()
        row["server_seed"] = seed.hex()
        # The channel is read from the VERSION header -- the field that carries it -- not
        # inferred from whatever the first opcode happens to be.
        channel = channel_of_stream(entry[wc.C2S]) or "unknown"
        row["channel"] = channel

        fits = [(label, key) for label, key in keys
                if key_fits(decrypt_stream(c2s_cipher, key))]
        if not fits:
            row.update({"decrypted": False,
                        "why": f"none of the {len(keys)} tapped key(s) decrypt this "
                               f"connection to a plausible client opcode"})
            results.append(row)
            continue
        # Dedup on the KEY BYTES, not the label. This tested `{f[0] for f in fits}` -- the
        # label -- and labels are `tap@{t}s` with t rounded to 2dp, so two genuinely
        # different keys sharing a rounded timestamp (or any entry whose `t` is missing,
        # which load_keyring labels "tap@?s") collapsed to one and the refusal silently
        # became "take fits[0]". Found by adversarial review 2026-08-07; not triggered by
        # any real capture yet, and it is the one guard this module advertises as a check
        # that can fail.
        if len({f[1] for f in fits}) > 1:
            # More than one key passing means `key_fits` is not discriminating here -- it
            # reads TWO BYTES, and with a dozen keys and a dozen connections a wrong key
            # spelling a plausible opcode is ordinary luck rather than a surprise. So ask a
            # question two bytes cannot fake: DOES THE WHOLE STREAM FRAME TO ITS FINAL BYTE
            # under this key? ARC4 is a stream cipher, so a wrong key is wrong for every
            # byte after the first message, and the framer walks message-by-message off a
            # length it read from the plaintext. It cannot walk 122,432 bytes of noise and
            # land exactly on the end.
            #
            # OBSERVED 2026-08-17 on capture 20260817T231139, which is the reason this
            # exists: two connections, two leftover keys, and each key passed `key_fits` on
            # BOTH connections -- a clean 2x2 ambiguity that refused the largest connection
            # in the corpus (122 KB, the whole of an Isle of the Nameless walk). Under this
            # test the pairing is not close: 100.0% vs 0.01% and 100.0% vs 0.11%.
            #
            # This is still a check that can fail. If the full-stream test leaves more than
            # one key -- or none -- we refuse exactly as before, and the `why` says which
            # of the two questions did not separate them. Never pick; only ever narrow.
            framed = [(label, key) for label, key in fits
                      if _frames_completely(s2c_cipher, key)]
            if len({f[1] for f in framed}) != 1:
                row.update({"decrypted": False,
                            "why": f"{len(fits)} different keys all fit the opcode test and "
                                   f"{len(framed)} frame the whole s2c stream; refusing to "
                                   f"choose"})
                results.append(row)
                continue
            fits = framed
        label, key = fits[0]
        safe = str(key_name).replace(":", "_").replace("->", "-to-")
        out_path = os.path.join(out_dir, f"{channel}-{safe}.jsonl")
        c2s_plain = decrypt_stream(c2s_cipher, key)
        s2c_plain = decrypt_stream(s2c_cipher, key)
        # DERIVE the stamp from the endpoints this connection actually had, rather than
        # asserting LIVE because this file is called livesession.py. The dry-run drives the
        # very same code against 127.0.0.1, so an asserted LIVE is wrong every time it runs
        # -- and origin.py now REFUSES a live stamp on an all-loopback file, so asserting it
        # here would produce artifacts that classify UNKNOWN and look like a defect.
        who = origin.OURS if all(origin.is_loopback(h) for h in str(key_name).split("->")
                                 if origin.is_address(h)) else origin.LIVE
        build = build_for(wire_path, key_name)
        stamp = {} if build is None else {"build": build}
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(origin.record("toolkit/harness/livesession.py", who,
                                              note=f"decrypted from an off-wire capture of "
                                                   f"{key_name}", **stamp)) + "\n")
            fh.write(json.dumps({"kind": "version", "channel": channel,
                                 "connection": key_name, "key_from": label,
                                 **stamp}) + "\n")
            fh.write(json.dumps({"kind": "session_key", "arc4_key": key.hex()}) + "\n")
            fh.write(json.dumps({"kind": "client_seed", "a": A.hex()}) + "\n")
            fh.write(json.dumps({"kind": "server_seed", "sent": seed.hex()}) + "\n")
            fh.write(json.dumps({"kind": "frame", "direction": "c2s",
                                 "plain": c2s_plain.hex()}) + "\n")
            fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                                 "plain": s2c_plain.hex()}) + "\n")
        row.update({"decrypted": True, "channel": channel, "key_from": label,
                    "out": out_path, "c2s_bytes": len(c2s_plain), "s2c_bytes": len(s2c_plain)})
        results.append(row)
    # Clear channel files this run did NOT write. Without this, a re-assemble that decrypts
    # fewer connections leaves the previous run's files sitting beside the new report --
    # MEASURED by adversarial review: re-assembling with 1 of 6 keys prints "1/6" while all
    # six decrypted files are still on disk. Anyone checking replayability by "the six
    # files are there" gets a false pass. That is exactly R0a's failure shape, where a row
    # stood on artifacts that were not the thing being claimed. Deleted only AFTER the new
    # files are written, so a failed assembly cannot destroy a good one.
    written = {os.path.basename(r["out"]) for r in results if r.get("out")}
    stale = sorted(f for f in os.listdir(out_dir)
                   if f.endswith(".jsonl") and f.split("-")[0] in VERSION_CHANNEL.values()
                   and f not in written)
    removed, kept = [], []
    if written and stale:
        # This run produced a real result, so its file set is the truth and leftovers from
        # a previous one must go.
        for f in stale:
            os.remove(os.path.join(out_dir, f))
        removed = stale
    elif stale:
        # This run produced NOTHING. Deleting here would let a failed check destroy a good
        # decryption -- the verification step must not be the risk. Keep them and say
        # loudly that they do not belong to this report.
        kept = stale
        print(f"  WARNING: this assembly decrypted nothing, and {len(kept)} channel file(s)"
              f" from an EARLIER run are still here.\n"
              f"           They are NOT this report's output: {', '.join(kept)}",
              flush=True)
    return {"wire": wire_path, "meta": meta, "connections": results,
            "decrypted": sum(1 for r in results if r.get("decrypted")),
            "total": len(results), "stale_removed": removed, "stale_kept": kept}


def prune_wire(wire_path):
    """Drop every captured connection that carries no GW handshake. Returns (kept, dropped).

    Sniffing port 80 is what finally caught the live channels, and port 80 also carries
    whatever else the machine is doing. Those connections are not evidence of anything this
    project wants, they are the owner's own browsing, and they should not sit in the vault
    because a filter had to be wide enough to work.

    The test is the same one assemble_live uses -- does the c2s stream begin with a VERSION
    header we recognise -- so a GW connection is kept even when no key decrypts it. The raw
    bytes of a channel we could not open are still the only recording of a real session.
    """
    meta, conns = wc.load_connections(wire_path)
    keep = {k for k, e in conns.items() if channel_of_stream(e[wc.C2S])}
    if len(keep) == len(conns):
        return len(keep), 0
    tmp = wire_path + ".pruned"
    dropped = 0
    with open(wire_path, encoding="utf-8", errors="replace") as src, \
            open(tmp, "w", encoding="utf-8") as dst:
        for line in src:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if r.get("kind") == "wire":
                if wc.conn_key(r) not in keep:
                    dropped += 1
                    continue
            dst.write(line if line.endswith("\n") else line + "\n")
    os.replace(tmp, wire_path)
    return len(keep), dropped
