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

The two builds, and why one tool makes both
-------------------------------------------
Only the DH substitution decides where a client may point (PLAN.md §6.2). The updater
kill switch and the mutex patches are wanted on BOTH configurations, so `--no-dh-patch`
produces the live-capture build R0b/A1 needs -- ArenaNet's own parameters, everything
else patched -- rather than leaving it to be assembled by hand. It was assembled by hand
once, on 2026-08-06, and it landed in `vault/client-patched/` beside the DH-patched copy,
where two tools that picked "the patched client" by filename order silently switched to
it. Each build now has its own directory and this tool refuses to cross them:

    vault/client-patched/       OUR DH.   Loopback only. `Gw.custom.<tag>.exe`
    vault/client-patched-live/  stock DH. Live only.     `Gw.live.<tag>.exe`

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gwpe import PE  # noqa: E402
import dhbuild  # noqa: E402
import vaultpath  # noqa: E402

# Prologue of the accessor returning the DH struct; the `mov eax, imm32` that
# follows carries the struct's virtual address. Used identically by Headquarter's
# reader and OpenTyria's writer -- which is ONE witness, not two: both are ldufr.
# An earlier version of this comment called them "two independent implementations
# that agree" and that was the house's own lineage rule being broken in a
# load-bearing place. What actually justifies this signature is that we re-derive
# it from the owner's own binary every run (dump_dh_params.py) and check the
# struct's shape; upstream agreement is a convenience, not the evidence.
# RE-EXPORTED, not re-typed. These bytes were spelled out in three modules --
# here, `dhbuild.py` and `clientscan/dump_dh_params.py` -- and three copies of a
# signature is the same defect as three copies of a policy, one level down: they
# agree until one of them is edited. `dhbuild` owns them because `cage.py`
# already trusts it to answer ours/stock from these very bytes.
SIG_KEYS = dhbuild.SIG_KEYS
SIG_KEYS_PTR_OFF = dhbuild.SIG_KEYS_PTR_OFF

# The single-instance guard around CreateMutexA.
SIG_MUTEX = bytes.fromhex("8BF885FF7411FFD63DB7")

# DnSetEnabled's whole prologue, through the `mov [global], eax` opcode. Verified
# unique in .text of build 38797 (1 hit, VA 0x00833ec0, global 0x01087810, which
# has 4 guard sites). See studies/handshake/PLAN.md §9.
SIG_DOWNLOAD = bytes.fromhex("558bec8b4d0833c085c90f94c0a3")
SIG_DOWNLOAD_PATCHED = bytes.fromhex("558bec8b4d0833c085c9b00190a3")
DOWNLOAD_PATCH_OFF = 10            # the `sete al` inside that prologue
DOWNLOAD_PATCH = bytes.fromhex("b00190")   # mov al,1 ; nop
MUTEX_PATCH_OFF = 0x08
MUTEX_PATCH = bytes.fromhex("31C0909090 0F84".replace(" ", ""))

MUTEX_NAME_OLD = b"AN-Mutex-Window"
MUTEX_NAME_NEW = b"AN-Futex"

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
    """(va, rva, file offset) of the DH struct, via `dhbuild.locate_keys`.

    DELEGATED 2026-08-13 -- `studies/crossbuild/PLAN.md` §7 rule 1. This function
    used to carry its own copy of the search and, on more than one match, print
    `note: N accessor matches; using the first` and patch that one. Of the three
    modules holding these bytes it was the one that mattered most: it WRITES
    CLIENT BINARIES, and picking the wrong struct means patching a decoy while
    the client keeps reading ArenaNet's parameters -- a build that would then be
    filed as ours and, per `cage.assert_launch_safe`, cleared for loopback while
    behaving like stock.

    `dhbuild` is already the module `cage.py` trusts to answer ours/stock, so it
    is the one implementation and this is a call site. It refuses on 0 matches,
    on matches that point at nothing DH-shaped, and on 2+ resolving to different
    structs.
    """
    return dhbuild.locate_keys(pe)[:3]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=r"C:\gw\Gw.exe")
    ap.add_argument("--output", help="default: vault/client-patched/Gw.custom.<build>.exe")
    ap.add_argument("--keys", help="reuse an existing key file instead of generating one")
    ap.add_argument("--keydir", default=r"C:\gd\Rurik\vault\keys")
    ap.add_argument("--no-dh-patch", action="store_true",
                    help="LEAVE ArenaNet's Diffie-Hellman parameters in place. Produces "
                         "the live-capture build (PLAN.md §6.2 item 1): updater off, "
                         "multi-instance on, stock DH. It CANNOT key against our server, "
                         "and it is the only configuration that may be pointed at the "
                         "real service. Defaults to vault/client-patched-live/.")
    ap.add_argument("--key-tap", action="store_true",
                    help="plant the R0b key-tap: a code cave that copies the session's "
                         "master_secret to a data slot as it is formed, for keytap.py to "
                         "read. Signature-anchored, ASLR-safe. On the loopback build it is "
                         "verifiable against a key we already hold; on the live build it is "
                         "how a real session is decrypted. See studies/livekey/CODECAVE.md.")
    ap.add_argument("--no-mutex-patch", action="store_true",
                    help="skip the multi-client patch")
    ap.add_argument("--no-updater-patch", action="store_true",
                    help="leave the auto-updater ENABLED. Only useful for comparing "
                         "against an unpatched updater; a client with the updater "
                         "live cannot be run behind the firewall cage, because the "
                         "patcher stalls forever on its blocked update check.")
    a = ap.parse_args()

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

    if a.no_dh_patch:
        if a.keys:
            raise SystemExit(
                "--keys and --no-dh-patch contradict each other: one supplies OUR\n"
                "parameters to write, the other says write none. Pick the build you\n"
                "want -- --keys for the loopback client, --no-dh-patch for the live one.")
        keys = None
        print("keys       : NONE -- ArenaNet's parameters stay in place (--no-dh-patch)")
        print("             This build CANNOT key against our server. It is the")
        print("             live-capture configuration and nothing else.")
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

    subdir = dhbuild.LIVE_DIR if a.no_dh_patch else dhbuild.LOOPBACK_DIR
    stem = "Gw.live" if a.no_dh_patch else "Gw.custom"
    out = a.output or vaultpath.vault_path(subdir, f"{stem}.{build_tag}.exe")
    out_abs = os.path.normcase(os.path.abspath(out))
    if out_abs.startswith(LIVE_INSTALL):
        raise SystemExit(f"Refusing to write into the live install ({LIVE_INSTALL}).")

    # The two staging directories are read as safety guarantees downstream --
    # dhbuild.select, make_run_dir and test_handshake all take "what is in this
    # directory" as "what kind of build this is". So writing the wrong kind into either
    # is refused here, at the only place that knows for certain which one it just built.
    # This is the exact mistake of 2026-08-06: a stock-DH build placed by hand into
    # vault/client-patched/, where filename-order selection then found it.
    wrong = dhbuild.LOOPBACK_DIR if a.no_dh_patch else dhbuild.LIVE_DIR
    if os.path.normcase(os.sep + wrong + os.sep) in out_abs + os.sep:
        raise SystemExit(
            f"Refusing to write a {'stock-DH' if a.no_dh_patch else 'DH-patched'} build "
            f"into vault/{wrong}/.\n"
            f"  That directory means {'OUR parameters, loopback only' if a.no_dh_patch else 'stock parameters, live only'}, "
            f"and tools read it as such.\n"
            f"  The default for this build is vault/{subdir}/ -- drop --output, or point "
            f"it there.")
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
    if keys is None:
        print("  DH struct left untouched (live-capture build)")
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

    key_tap_report = None
    if a.key_tap:
        # The one patch that adds code, and it says so. keytap_patch relocates the tap,
        # the cave and the slot from byte signatures, refuses if the client changed, and
        # verify() follows the three control-flow edges arithmetically before we trust it.
        import keytap_patch  # noqa: E402
        tapped, key_tap_report = keytap_patch.plant(bytes(data), pe)
        keytap_patch.verify(tapped, pe, key_tap_report)
        data = bytearray(tapped)
        print(f"  key-tap    : tap 0x{key_tap_report['tap_va']:08x} -> cave "
              f"0x{key_tap_report['cave_va']:08x}, slot 0x{key_tap_report['slot_va']:08x}")
        print(f"               keytap.py reads {keytap_patch.SLOT_SIZE} bytes at "
              f"Gw.exe + 0x{key_tap_report['slot_va'] - pe.image_base:x}")

    with open(out, "wb") as f:
        f.write(bytes(data))
    print(f"\nwrote {out}")

    if key_tap_report is not None:
        # Re-read from disk and re-verify, the same discipline the DH patch uses: a patch
        # that did not survive the write is worse than one never attempted.
        keytap_patch.verify(PE(out).data, pe, key_tap_report)
        print("key-tap    : re-read from disk and every edge still resolves")

    # Verify by re-reading the written file, not by trusting the buffer we wrote.
    v = PE(out)
    _, _, voff = locate(v)
    g2 = int.from_bytes(v.data[voff + 4:voff + 8], "little")
    p2 = int.from_bytes(v.data[voff + 8:voff + 72], "little")
    B2 = int.from_bytes(v.data[voff + 72:voff + 136], "little")
    old_B = int.from_bytes(pe.data[off + 72:off + 136], "little")
    if keys is None:
        # The negative of the usual check, and it has to be asserted rather than assumed:
        # "we did not write there" is a claim about code, and this is a claim about bytes.
        ok = (g2, p2, B2) == (old_g, old_p, old_B)
        print(f"verify     : DH parameters are byte-identical to the input -> {ok}")
        if not ok:
            raise SystemExit("VERIFICATION FAILED — the DH struct changed and this build "
                             "was supposed to leave it alone. Do not use this binary.")
    else:
        ok = (g2 == keys["generator"] and p2 == keys["prime"]
              and B2 == keys["server_public"]
              and pow(keys["generator"], keys["server_private"], keys["prime"]) == B2)
        print(f"verify     : parameters read back correctly and B == g^b mod p -> {ok}")
        if not ok:
            raise SystemExit("VERIFICATION FAILED — do not use this binary.")

    # Second opinion, from key material this run did not produce: dhbuild compares the
    # written struct against vault/keys/. For the live build that is dh_params_*.txt,
    # dumped from ArenaNet's binary by a different tool on a different day, so agreement
    # is evidence rather than our own arithmetic handed back to us.
    want = dhbuild.STOCK if keys is None else dhbuild.OURS
    kind, detail = dhbuild.classify(out)
    print(f"classify   : {kind} -- {detail}")
    if kind != want:
        raise SystemExit(
            f"VERIFICATION FAILED — this build classifies as {kind}, expected {want}.\n"
            f"  Everything downstream picks builds by that classification, so a binary\n"
            f"  the vault cannot place is refused here rather than filed anywhere.")

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
    if keys is None:
        print("\nThis is the LIVE-CAPTURE build. It carries ArenaNet's parameters, so it")
        print("cannot key against our server and loopback is not a use for it.")
        print("\nNext: python toolkit/clientpatch/make_run_dir.py --live")
        print("Then read PLAN.md §6.2 -- having this build is ONE precondition, not all")
        print("of them. Do not cage it, do not drive it with drive_client.py, and use the")
        print("secondary account only.")
    else:
        print("\nNext: run toolkit/portal/webgate.py, then launch this patched copy with")
        print("  -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
