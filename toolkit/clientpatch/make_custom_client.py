"""Build a patched Guild Wars client that will talk to our server.

R1 needs this and there is no way around it. The client's auth channel is keyed by
a static-ephemeral Diffie-Hellman exchange in which the SERVER's public value B is
compiled into the executable and never sent on the wire; the client derives the
shared secret locally as B^a mod p. Our server cannot reproduce that secret without
b, the discrete log of B, which ArenaNet never shipped. So the client's (g, p, B)
triple has to be replaced with one whose private exponent we hold.

That is why HANDOFF.md section 4's "R1 needs no binary patching" is wrong, and it
was confirmed against this owner's own binary -- see studies/handshake/PLAN.md.

**The parameters rotate per client build.** The 2026-08-04 update moved the struct
from RVA 0x6843e8 to 0x6910d8 and changed both the prime and B. So keys are
build-stamped here, and this tool is meant to be re-run after every update rather
than once.

Two further patches, both from the same public tooling, both wanted here:
  * NOP the CreateMutexA single-instance check, and
  * rename the mutex string,
so several clients can run at once. That is not a nicety -- capture at scale wants
many clients, and this is what makes multiboxing possible.

TWO CONFIGURATIONS, and only one of them is disqualified from the real service.
`--live-capture` builds the other one: updater kill switch and mutex patches, with
the Diffie-Hellman substitution deliberately WITHHELD. PLAN.md §6.2 §7 Q4 authorize
capture against ArenaNet on the secondary account, and that authorized use had no
legal target until this flag existed -- the launch sites refuse anything outside
`vault/run`, and everything in `vault/run` carried our parameters.

The distinction is not "how many patches": it is whose parameters the binary holds.

  default          our DH + updater + mutex   loopback ONLY, and must be caged
  --live-capture   updater + mutex            the real service ONLY, and never caged

Note that the withheld patch is withheld, not undone. Building `--live-capture` from
an already-patched client would produce a binary that reads as live by filename and is
disqualified by bytes, so the input's parameters are checked before anything is
written and the output's are checked after -- both through `buildid.dh_verdict`, the
same function the launch gate calls.

Safety
------
Writes a COPY and refuses to write anywhere inside the live install. The live
client is the owner's only source of truth (HANDOFF.md section 9); a patcher that
can overwrite it is one typo away from costing a reinstall.

Dependency-free: no openssl, no pefile.
"""

import argparse
import hashlib
import json
import os
import secrets
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from gwpe import PE  # noqa: E402
import buildid  # noqa: E402

# The patch sites are defined once, in buildid.py, because identifying a build is
# more fundamental than patching one -- the launch gate has to read these signatures
# out of binaries this patcher never touched. Imported back here under their old
# names so this file reads the same as it always did.
SIG_KEYS = buildid.SIG_KEYS
SIG_KEYS_PTR_OFF = buildid.SIG_KEYS_PTR_OFF
SIG_MUTEX = buildid.SIG_MUTEX
SIG_DOWNLOAD = buildid.SIG_DOWNLOAD
SIG_DOWNLOAD_PATCHED = buildid.SIG_DOWNLOAD_PATCHED
DOWNLOAD_PATCH_OFF = buildid.DOWNLOAD_PATCH_OFF
DOWNLOAD_PATCH = buildid.DOWNLOAD_PATCH
MUTEX_PATCH_OFF = buildid.MUTEX_PATCH_OFF
MUTEX_PATCH = buildid.MUTEX_PATCH
MUTEX_NAME_OLD = buildid.MUTEX_NAME_OLD
MUTEX_NAME_NEW = buildid.MUTEX_NAME_NEW

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))


# ---------------------------------------------------------------- primes ----
def _is_probable_prime(n, rounds=40):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def gen_prime(bits=512):
    while True:
        c = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(c):
            return c


def gen_keys(bits=512, generator=4):
    """A fresh DH triple. Matches the client's shape: g=4 over a 512-bit prime.

    512 bits is weak by modern standards and that is not a defect here -- it is
    dictated by the client's fixed 64-byte field, and this key protects a loopback
    connection between the owner and their own server. It must never be reused
    anywhere that matters.
    """
    p = gen_prime(bits)
    b = secrets.randbits(bits) % (p - 2) + 1
    B = pow(generator, b, p)
    return {"generator": generator, "prime": p, "server_private": b, "server_public": B}


# ---------------------------------------------------------------- patching --
def locate(pe):
    hits = pe.find(SIG_KEYS, ".text")
    if not hits:
        raise SystemExit(
            "Could not find the DH accessor signature.\n"
            "The client was recompiled, or the scheme changed. This is a real R1\n"
            "finding, not a tool bug -- re-derive the signature before patching.")
    if len(hits) > 1:
        print(f"  note: {len(hits)} accessor matches; using the first")
    import struct
    va = struct.unpack_from("<I", pe.data, hits[0] + SIG_KEYS_PTR_OFF)[0]
    rva = va - pe.image_base
    off = pe.rva_to_off(rva)
    if off is None:
        raise SystemExit(f"DH struct RVA 0x{rva:x} is not backed by file bytes")
    return va, rva, off


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=r"C:\gw\Gw.exe")
    ap.add_argument("--output", help="default: vault/client-patched/Gw.custom.<build>.exe")
    ap.add_argument("--keys", help="reuse an existing key file instead of generating one")
    ap.add_argument("--keydir", default=r"C:\gd\Rurik\vault\keys")
    ap.add_argument("--no-mutex-patch", action="store_true",
                    help="skip the multi-client patch")
    ap.add_argument("--no-updater-patch", action="store_true",
                    help="leave the auto-updater ENABLED. Only useful for comparing "
                         "against an unpatched updater; a client with the updater "
                         "live cannot be run behind the firewall cage, because the "
                         "patcher stalls forever on its blocked update check.")
    ap.add_argument("--live-capture", action="store_true",
                    help="build the OTHER configuration: updater and mutex patches "
                         "only, Diffie-Hellman left exactly as ArenaNet shipped it. "
                         "This is the only build authorized to reach the real service "
                         "(PLAN.md §6.2), and it cannot talk to our server at all.")
    a = ap.parse_args()

    # The two configurations are mutually exclusive by construction, and saying so
    # here is cheaper than discovering it from a verify failure after a 512-bit prime
    # search. --keys only means anything when we are writing keys.
    if a.live_capture and a.keys:
        raise SystemExit(
            "--live-capture and --keys are contradictory: a live-capture client is "
            "defined by NOT carrying our Diffie-Hellman parameters.")

    pe = PE(a.input)
    print(f"input      : {a.input}")
    print(f"arch       : {pe.arch}   image base 0x{pe.image_base:08x}")
    exe_hash = hashlib.sha256(pe.data).hexdigest()
    build_tag = time.strftime("%Y-%m-%d", time.gmtime(pe.timestamp)) + "_" + exe_hash[:12]
    print(f"build tag  : {build_tag}")

    va, rva, off = locate(pe)
    print(f"DH struct  : VA 0x{va:08x}  RVA 0x{rva:06x}  file 0x{off:x}")

    # Show what we are replacing, so a wrong target is obvious before we write.
    old_g = int.from_bytes(pe.data[off + 4:off + 8], "little")
    old_p = int.from_bytes(pe.data[off + 8:off + 72], "little")
    print(f"current    : g={old_g}, prime {old_p.bit_length()} bits, "
          f"fp {hashlib.sha256(pe.data[off+8:off+72]).hexdigest()[:16]}")
    if old_g != 4 or old_p.bit_length() != 512:
        raise SystemExit("Unexpected parameter shape at the target. Refusing to patch.")

    if a.live_capture:
        # Refuse to build the live configuration out of a client that already carries
        # our parameters. Withholding the DH patch does not remove one already there,
        # so this path would otherwise mint a binary that reads as a live-capture build
        # by filename and is a disqualified one by bytes -- the exact confusion §6.2
        # says ends an account. Checked against the input, before anything is written.
        verdict, why = buildid.dh_verdict(a.input)
        if verdict != buildid.STOCK:
            raise SystemExit(
                f"REFUSING to build a live-capture client from {a.input}\n"
                f"  its Diffie-Hellman parameters read as {verdict!r}: {why}\n"
                f"  A live-capture build must start from a client carrying ArenaNet's\n"
                f"  own parameters, because this mode does not replace them -- it\n"
                f"  withholds the replacement. Build it from the live install.")
        keys = None
        print("keys       : NOT patched -- this is a live-capture build "
              "(PLAN.md §6.2)")
    elif a.keys:
        keys = json.load(open(a.keys))
        print(f"keys       : reusing {a.keys}")
    else:
        print("keys       : generating a 512-bit prime ...", flush=True)
        keys = gen_keys()
        keys["build_tag"] = build_tag
        keys["source_exe_sha256"] = exe_hash
        keys["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        os.makedirs(a.keydir, exist_ok=True)
        kp = os.path.join(a.keydir, f"rurik_dh_{build_tag}.json")
        with open(kp, "w") as f:
            json.dump(keys, f, indent=2)
        print(f"             wrote {kp}")
        print("             KEEP THIS. The server needs server_private to decrypt;")
        print("             lose it and the patched client is useless.")

    stem = "Gw.live" if a.live_capture else "Gw.custom"
    out = a.output or os.path.join(r"C:\gd\Rurik\vault\client-patched",
                                   f"{stem}.{build_tag}.exe")
    out_abs = os.path.normcase(os.path.abspath(out))
    if out_abs.startswith(LIVE_INSTALL):
        raise SystemExit(f"Refusing to write into the live install ({LIVE_INSTALL}).")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    data = bytearray(pe.data)

    def put(offset, blob, what):
        data[offset:offset + len(blob)] = blob
        print(f"  patched {what} at 0x{offset:x} ({len(blob)} bytes)")

    # Offsets are from the STRUCT BASE: word0 at +0 (left alone, always 1),
    # generator at +4, prime at +8, server public at +72. OpenTyria's patcher
    # advances its cursor past word0 first and then writes at +0/+4/+68, which is
    # the same place -- copying its literals without its cursor shifts every field
    # four bytes and silently corrupts the struct. The verify step below caught
    # exactly that during development.
    if a.live_capture:
        print("  Diffie-Hellman LEFT ALONE -- ArenaNet's parameters, untouched")
    else:
        put(off + 4, keys["generator"].to_bytes(4, "little"), "generator")
        put(off + 8, keys["prime"].to_bytes(64, "little"), "prime")
        put(off + 72, keys["server_public"].to_bytes(64, "little"), "server public")

    if not a.no_updater_patch:
        # The updater kill switch. DnSetEnabled(bool) is the only writer of one BSS
        # global that gates the whole download path:
        #
        #   mov ecx,[ebp+8] ; xor eax,eax ; test ecx,ecx ; sete al ; mov [g],eax
        #
        # so the global is a *disabled* flag -- it is set when the argument is
        # FALSE. Forcing `mov al,1` makes it set on every call, after which
        # DnInit() returns immediately and DnRun() returns 1, "done, nothing to
        # do", which its caller reads as patching finished.
        #
        # Why this matters beyond convenience: the firewall cage and the patcher
        # are in direct conflict. The patcher needs one outbound check to succeed
        # before the login screen appears, and a block denies it forever. The
        # workaround -- open the cage during startup, close it after -- leaks by
        # construction, because Windows firewall rules apply at connection
        # ESTABLISHMENT and there is no supported way to tear down an established
        # TCP connection. With the updater off, the cage never has to open.
        #
        # Signature-matched, not offset-hardcoded: the function sits at VA
        # 0x00833ec0 in build 38797 and 0x0082dab0 in the 2026-04-30 build.
        hits = pe.find(SIG_DOWNLOAD, ".text")
        if len(hits) == 1:
            put(hits[0] + DOWNLOAD_PATCH_OFF, DOWNLOAD_PATCH, "updater kill switch")
        elif not hits:
            print("  note: DnSetEnabled signature not found; updater left ENABLED")
        else:
            # Refuse rather than guess. Patching the wrong prologue would corrupt
            # an unrelated function, and the symptom would appear far from here.
            print(f"  note: {len(hits)} DnSetEnabled matches, expected 1; "
                  f"updater left ENABLED")

    if not a.no_mutex_patch:
        hits = pe.find(SIG_MUTEX, ".text")
        if hits:
            put(hits[0] + MUTEX_PATCH_OFF, MUTEX_PATCH, "CreateMutexA check")
        else:
            print("  note: mutex guard signature not found; multi-client not enabled")
        nm = pe.find(MUTEX_NAME_OLD, ".rdata")
        if nm:
            put(nm[0], MUTEX_NAME_NEW.ljust(len(MUTEX_NAME_OLD), b"\0"), "mutex name")

    with open(out, "wb") as f:
        f.write(bytes(data))
    print(f"\nwrote {out}")

    # Verify by re-reading the written file, not by trusting the buffer we wrote.
    #
    # Both branches end by asking the WRITTEN FILE the same question the launch gate
    # will ask it -- buildid.dh_verdict -- rather than a question only this tool knows
    # how to ask. A build that verifies against its own intentions and then gets
    # refused at launch has verified nothing useful.
    v = PE(out)
    _, _, voff = locate(v)
    g2 = int.from_bytes(v.data[voff + 4:voff + 8], "little")
    p2 = int.from_bytes(v.data[voff + 8:voff + 72], "little")
    B2 = int.from_bytes(v.data[voff + 72:voff + 136], "little")

    if a.live_capture:
        unchanged = (g2 == old_g
                     and p2 == int.from_bytes(pe.data[off + 8:off + 72], "little")
                     and B2 == int.from_bytes(pe.data[off + 72:off + 136], "little"))
        verdict, why = buildid.dh_verdict(out)
        print(f"verify     : DH bytes identical to the input -> {unchanged}")
        print(f"             launch gate reads this build as {verdict!r}")
        if not unchanged or verdict != buildid.STOCK:
            raise SystemExit(
                f"VERIFICATION FAILED — do not use this binary.\n"
                f"  unchanged={unchanged}, dh_verdict={verdict!r}: {why}\n"
                f"  A live-capture build whose parameters are not provably ArenaNet's\n"
                f"  is the one artifact this repo must never produce.")
    else:
        ok = (g2 == keys["generator"] and p2 == keys["prime"]
              and B2 == keys["server_public"]
              and pow(keys["generator"], keys["server_private"], keys["prime"]) == B2)
        print(f"verify     : parameters read back correctly and B == g^b mod p -> {ok}")
        if not ok:
            raise SystemExit("VERIFICATION FAILED — do not use this binary.")
        verdict, why = buildid.dh_verdict(out)
        print(f"             launch gate reads this build as {verdict!r}")
        if verdict != buildid.OURS:
            raise SystemExit(
                f"The binary is correct but the launch gate will refuse it: {why}\n"
                f"  buildid.our_keys() only trusts key files under the vault's keys/\n"
                f"  directory named rurik_dh_*.json. Put the key file there.")

    # Read the updater state back out of the file too. A kill switch that silently
    # did not apply is worse than one that was never attempted: the client would
    # look fine until the first caged launch stalled on the patcher, and the
    # symptom appears nowhere near this code.
    if not a.no_updater_patch:
        patched = len(v.find(SIG_DOWNLOAD_PATCHED, ".text"))
        remaining = len(v.find(SIG_DOWNLOAD, ".text"))
        print(f"updater    : disabled -> {patched == 1 and remaining == 0} "
              f"({patched} patched, {remaining} unpatched)")
        if patched != 1 or remaining:
            raise SystemExit("Updater patch did not take — this client will stall "
                             "behind the firewall cage. Do not use it caged.")
    if a.live_capture:
        print("\nThis build carries ArenaNet's Diffie-Hellman parameters. It CANNOT talk")
        print("to our server, and it must NOT be caged -- the cage pins to loopback and")
        print("this client has no business there. Stage it with:")
        print(f"  python toolkit/clientpatch/make_run_dir.py --live --exe {out}")
        print("Then read PLAN.md §6.2 before launching it: the behavioural rule is the")
        print("control that matters, and the account is named per launch, never autofilled.")
    else:
        print("\nNext: run toolkit/portal/webgate.py, then launch this patched copy with")
        print("  -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed")
        print("Cage it FIRST, in an elevated shell -- the launch gate refuses otherwise:")
        print("  & toolkit\\clientpatch\\isolate_client.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
