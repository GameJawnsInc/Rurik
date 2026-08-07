"""What a `Gw.exe` actually IS -- read out of its bytes, not looked up by hash.

    python toolkit/clientpatch/buildid.py            # every client on this machine

WHY THIS EXISTS. `toolkit/clientscan/pinned.py` answers "which copy am I reading" for
static analysis, by whole-file SHA-256 against two recorded digests. That is the right
answer for a *study* -- a study wants to know it read the pristine client -- and the
wrong one for a *launch gate*, for two reasons that both bite now rather than later:

  * It has one `PATCHED_SHA256`, so it recognises exactly one patched copy. Every
    client `make_custom_client.py` builds carries freshly generated Diffie-Hellman
    parameters and therefore a hash nobody has recorded, which reads as `unknown`.
    `cage.py` refuses `unknown`, correctly -- but that means the safety gate refuses
    every new client until a human edits a constant, and a gate you must disarm to do
    your job is a gate that gets disarmed.
  * It conflates the patches. `patched` is one bucket holding four independent
    modifications, and PLAN.md §6.2 turns on the fact that **only one of them
    matters**: a client carrying OUR DH parameters must never reach the real service;
    the updater kill switch and the mutex patches are wanted on both configurations.
    A gate that cannot tell those apart can only ever answer "refuse everything", which
    is what the launch sites do today and why §7 Q4's authorized use has no legal
    target.

WHAT THIS READS INSTEAD -- the four sites, by signature, in any build:

  DH parameters   the (generator, prime, server public) triple at the struct the
                  accessor points to. THE question. See `dh_verdict()`.
  updater         DnSetEnabled's `sete al`, forced or not.
  mutex guard     the CreateMutexA single-instance check, NOPed or intact.
  mutex name      `AN-Mutex-Window` or our replacement.

HOW `dh_verdict` DECIDES, and why it is a check rather than a label:

  OURS     the binary's triple equals one in `vault/keys/rurik_dh_*.json` AND that key
           file satisfies B == g^b mod p. The second half is the point: it proves we
           hold the private exponent, which is the operational meaning of "ours" --
           this client can key against our server, and its traffic to anyone else is
           garbage. A matching blob alone would only prove someone wrote a number.
  STOCK    the binary's triple equals the one in the owner's own live install at
           `C:\\gw\\Gw.exe`, read at check time. This is the configuration that may
           talk to the real service and may not talk to ours.
  UNKNOWN  neither. Refused everywhere.

The reference is read live and never cached. If `C:\\gw` is gone, or has auto-updated
past the build in hand, STOCK cannot be confirmed and the answer is UNKNOWN -- which is
the correct refusal rather than an inconvenience, because ArenaNet would refuse a stale
build too. Caching a fingerprint would buy nothing and could only ever go stale
silently.

PROVENANCE. This module stores no ArenaNet bytes. It reads the owner's install at run
time and compares; nothing derived from it is written down. The signatures below are our
own, re-derived from the owner's binary -- see `studies/handshake/PLAN.md`.

MEASURED 2026-08-06, build 38797 (`221c13772c7a`), all three copies on this machine:

    live install   DH stock   updater live    mutex guard intact
    vault/run/...  DH ours    updater killed  mutex guard NOPed
    ...-probe      DH ours    updater killed  mutex guard NOPed

Standard library only, and no disassembler: every site here is a fixed byte pattern, so
this keeps working on a bare machine. CLAUDE.md binds the launch path to that.
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from gwpe import PE  # noqa: E402
import vaultpath  # noqa: E402

# ------------------------------------------------------------------ signatures --
# These live here rather than in make_custom_client.py because identifying a build is
# more fundamental than patching one: the gate has to work on binaries the patcher
# never touched. make_custom_client imports them back, so there is one definition.

# Prologue of the accessor returning the DH struct; the `mov eax, imm32` that follows
# carries the struct's virtual address. Re-derived from the owner's own binary every
# run by dump_dh_params.py -- upstream agreement (Headquarter's reader, OpenTyria's
# writer) is a convenience and NOT the evidence, because both are ldufr: one witness.
SIG_KEYS = bytes.fromhex("8B4508C70088000000B8")
SIG_KEYS_PTR_OFF = 0x0A

# Offsets from the struct base. word0 at +0 is always 1 and is left alone.
DH_GENERATOR_OFF = 4
DH_PRIME_OFF = 8
DH_PUBLIC_OFF = 72
DH_FIELD_LEN = 64

# The single-instance guard around CreateMutexA.
SIG_MUTEX = bytes.fromhex("8BF885FF7411FFD63DB7")
MUTEX_PATCH_OFF = 0x08
MUTEX_PATCH = bytes.fromhex("31C0909090" "0F84")

# DnSetEnabled's whole prologue, through the `mov [global], eax`. Verified unique in
# .text of build 38797 (1 hit, VA 0x00833ec0). See studies/handshake/PLAN.md §9.
SIG_DOWNLOAD = bytes.fromhex("558bec8b4d0833c085c90f94c0a3")
SIG_DOWNLOAD_PATCHED = bytes.fromhex("558bec8b4d0833c085c9b00190a3")
DOWNLOAD_PATCH_OFF = 10
DOWNLOAD_PATCH = bytes.fromhex("b00190")  # mov al,1 ; nop

MUTEX_NAME_OLD = b"AN-Mutex-Window"
MUTEX_NAME_NEW = b"AN-Futex"

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw\Gw.exe"))

OURS = "ours"
STOCK = "stock"
UNKNOWN = "unknown"


class BuildReadError(Exception):
    """The binary could not be read as a client at all. Never a verdict."""


# ------------------------------------------------------------------- the sites --
def locate_dh(pe):
    """(va, rva, file offset) of the Diffie-Hellman parameter struct."""
    hits = pe.find(SIG_KEYS, ".text")
    if not hits:
        raise BuildReadError(
            "no Diffie-Hellman accessor signature in .text -- this is not a client "
            "build we can read, or the scheme changed. Re-derive before trusting it.")
    va = struct.unpack_from("<I", pe.data, hits[0] + SIG_KEYS_PTR_OFF)[0]
    rva = va - pe.image_base
    off = pe.rva_to_off(rva)
    if off is None:
        raise BuildReadError(f"DH struct RVA 0x{rva:x} is not backed by file bytes")
    return va, rva, off


def read_dh(pe):
    """{'generator', 'prime', 'public', 'offset'} -- the triple as integers."""
    _, _, off = locate_dh(pe)
    return {
        "generator": int.from_bytes(
            pe.data[off + DH_GENERATOR_OFF:off + DH_GENERATOR_OFF + 4], "little"),
        "prime": int.from_bytes(
            pe.data[off + DH_PRIME_OFF:off + DH_PRIME_OFF + DH_FIELD_LEN], "little"),
        "public": int.from_bytes(
            pe.data[off + DH_PUBLIC_OFF:off + DH_PUBLIC_OFF + DH_FIELD_LEN], "little"),
        "offset": off,
    }


def dh_fingerprint(dh):
    """A short, printable digest of a triple. Safe to log: one-way, and no secret."""
    blob = b"%d|%d|%d" % (dh["generator"], dh["prime"], dh["public"])
    return hashlib.sha256(blob).hexdigest()[:16]


def patch_state(pe):
    """What non-DH modifications this binary carries. Each value is measured, not assumed."""
    live = len(pe.find(SIG_DOWNLOAD, ".text"))
    killed = len(pe.find(SIG_DOWNLOAD_PATCHED, ".text"))
    return {
        # None means "cannot tell" -- both signatures absent, or both present. Neither
        # is a state this patcher produces, so it is reported rather than rounded off.
        "updater_killed": True if (killed == 1 and live == 0)
                          else (False if (live == 1 and killed == 0) else None),
        "mutex_guard_nopped": not pe.find(SIG_MUTEX, ".text"),
        "mutex_renamed": bool(pe.find(MUTEX_NAME_NEW, ".rdata"))
                         and not pe.find(MUTEX_NAME_OLD, ".rdata"),
    }


# ----------------------------------------------------------------- the verdict --
def our_keys(keydir=None):
    """Every DH triple we hold the private exponent for, proven by B == g^b mod p.

    A key file that fails that check is skipped, not trusted: it would be a triple we
    cannot actually decrypt, and calling it ours would let a client we cannot key
    against pass the loopback gate.
    """
    if keydir is None:
        keydir = vaultpath.vault_path("keys")
    out = []
    if not os.path.isdir(keydir):
        return out
    for name in sorted(os.listdir(keydir)):
        if not (name.startswith("rurik_dh_") and name.endswith(".json")):
            continue
        path = os.path.join(keydir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                k = json.load(fh)
            g, p = int(k["generator"]), int(k["prime"])
            b, B = int(k["server_private"]), int(k["server_public"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if pow(g, b, p) != B:          # we do not actually hold this exponent
            continue
        out.append({"name": name, "generator": g, "prime": p, "public": B})
    return out


def stock_dh(reference=LIVE_INSTALL):
    """The triple in the owner's own install, read now. None if it cannot be read.

    Read-only, every time, and never written down anywhere: CLAUDE.md's provenance gate
    is that no ArenaNet bytes enter the repo, and a cached fingerprint would be both a
    derived artifact and a thing that goes stale without saying so.
    """
    if not os.path.isfile(reference):
        return None
    try:
        return read_dh(PE(reference))
    except (BuildReadError, OSError, ValueError):
        return None


def dh_verdict(exe, keydir=None, reference=LIVE_INSTALL):
    """(OURS | STOCK | UNKNOWN, detail). The one question the launch gate turns on."""
    try:
        dh = read_dh(PE(exe))
    except (BuildReadError, OSError, ValueError) as exc:
        return UNKNOWN, f"could not read DH parameters: {exc}"

    for k in our_keys(keydir):
        if (k["generator"] == dh["generator"] and k["prime"] == dh["prime"]
                and k["public"] == dh["public"]):
            return OURS, (f"carries OUR parameters ({k['name']}), and that key file "
                          f"satisfies B == g^b mod p, so we hold the exponent")

    ref = stock_dh(reference)
    if ref is None:
        return UNKNOWN, (f"not ours, and the reference install {reference} could not be "
                         f"read, so 'stock' cannot be confirmed either")
    if (ref["generator"] == dh["generator"] and ref["prime"] == dh["prime"]
            and ref["public"] == dh["public"]):
        return STOCK, (f"matches the parameters in {reference} exactly "
                       f"(fp {dh_fingerprint(dh)}) -- ArenaNet's, not ours")
    return UNKNOWN, (f"fp {dh_fingerprint(dh)} matches neither a key file we hold nor "
                     f"{reference}. It may be an older build, another party's patch, or "
                     f"a key file that was lost.")


def describe(exe, keydir=None, reference=LIVE_INSTALL):
    """Everything measurable about one binary, as a dict. `dh` is the safety answer."""
    out = {"path": os.path.abspath(exe), "dh": UNKNOWN, "dh_detail": "", "patches": {},
           "build_ok": False}
    if not os.path.isfile(exe):
        out["dh_detail"] = "no such file"
        return out
    out["dh"], out["dh_detail"] = dh_verdict(exe, keydir, reference)
    try:
        pe = PE(exe)
        out["patches"] = patch_state(pe)
        out["build_ok"] = True
        out["sha256"] = hashlib.sha256(pe.data).hexdigest()
    except (OSError, ValueError) as exc:
        out["dh_detail"] += f" (and the PE would not parse: {exc})"
    return out


# ------------------------------------------------------------------------ main --
def _line(label, path):
    d = describe(path)
    p = d["patches"]
    upd = {True: "killed", False: "LIVE", None: "?"}[p.get("updater_killed")]
    print(f"  {label:22s} dh={d['dh']:7s} updater={upd:6s} "
          f"mutex={'nopped' if p.get('mutex_guard_nopped') else 'intact':6s} "
          f"name={'renamed' if p.get('mutex_renamed') else 'stock'}")
    print(f"      {path}")
    print(f"      {d['dh_detail']}")
    return d


def main():
    # --json exists so the PowerShell launchers can ask this module rather than
    # carrying a second copy of the signatures. Two definitions of where the updater
    # patch lives is exactly the drift this file was made to remove.
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        if i + 1 >= len(sys.argv):
            print(json.dumps({"error": "--json needs a path"}))
            return 2
        print(json.dumps(describe(sys.argv[i + 1]), indent=2))
        return 0

    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})")
    keys = our_keys()
    print(f"key files with a verified exponent: {len(keys)} "
          f"({', '.join(k['name'] for k in keys) or 'none'})\n")
    _line("live install", LIVE_INSTALL)
    for root in ("run", "run-live"):
        base = vaultpath.vault_path(root)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            exe = os.path.join(base, name, "Gw.exe")
            if os.path.isfile(exe):
                _line(f"{root}/{name}", exe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
