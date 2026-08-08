"""Whose Diffie-Hellman parameters is this client carrying, and therefore where may it point?

    python toolkit/clientpatch/dhbuild.py        # every build in the vault, and what it is

WHY THIS EXISTS. Since §7 Q4 authorized live automation there are two client
configurations on this machine, they are the same size, they differ in 64 bytes that
matter, and they have **opposite** safety rules:

    OURS  (g, p, B) replaced   loopback ONLY.  Must be caged. Pointing it at ArenaNet
                               completes a REAL Stage A login with the autofilled
                               credential and only then delivers garbage frames.
    STOCK (g, p, B) untouched  live ONLY.      Cannot be caged and cannot key against
                               our server -- it derives its ARC4 key from ArenaNet's B.

Everything else the patcher does -- the updater kill switch, the NOPed mutex guard, the
renamed mutex -- is wanted on BOTH, so "patched" is not the property any rule wants.
PLAN.md §6.2 says this in prose; this module is the part a program can call.

WHAT WENT WRONG WITHOUT IT. On 2026-08-06 the stock-DH build landed in
`vault/client-patched/` as `Gw.live.<tag>.exe`, beside the DH-patched `Gw.custom.<tag>.exe`.
Two tools pick "the patched client" out of that directory with `sorted(...)[-1]`, and `l`
sorts after `c`, so both silently switched to the wrong binary:

  * `test_handshake.py` went red with four failures and a short check count, all of which
    read as a crypto regression in code that had not changed.
  * `make_run_dir.py` would have assembled the STOCK build into `vault/run/`, where
    `drive_client.assert_safe` accepts anything under that root -- a loopback launch
    target that cannot key, whose symptom is an undecryptable channel.

Filename order is not a safety property. Ask the bytes.

HOW IT DECIDES. It reads the pinned (g, p, B) struct out of the PE, exactly as the client
does, and compares against the vault's own key material:

    vault/keys/rurik_dh_*.json      OURS   -- we hold server_private for these
    vault/keys/dh_params_*.txt      STOCK  -- dumped from ArenaNet's own binary

A binary matching neither is `unknown` and is refused rather than guessed at, the same
fail-closed rule `cage.py` applies to a hash it does not recognise. A binary whose prime
matches a record but whose B does not gets its own message: that is the four-byte field
shift `make_custom_client.py`'s own comment records catching during development, and it
must never be quietly filed under "unrecognised".

Read-only, standard library only.
"""

import glob
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from gwpe import PE  # noqa: E402
import vaultpath  # noqa: E402

# Same accessor prologue make_custom_client.py patches through and dump_dh_params.py
# reads. Re-derived from the owner's own binary every patch run; upstream agreement is
# a convenience, not the evidence.
SIG_KEYS = bytes.fromhex("8B4508C70088000000B8")
SIG_KEYS_PTR_OFF = 0x0A

OURS = "ours"
STOCK = "stock"
UNKNOWN = "unknown"

# The non-DH patch sites. These decide NOTHING about where a client may point -- the
# updater kill switch and both mutex patches are wanted on ours and stock alike -- and
# they are read here so a launch can log what it let through rather than merely that it
# let something through. `patch_state` is also how a caged run proves the updater is
# actually off: a live updater behind the cage stalls the client forever on a blocked
# check, which looks like a hang and not like a configuration error.
SIG_MUTEX = bytes.fromhex("8BF885FF7411FFD63DB7")
MUTEX_NAME_OLD = b"AN-Mutex-Window"
MUTEX_NAME_NEW = b"AN-Futex"
# DnSetEnabled's prologue, unpatched and patched. See studies/handshake/PLAN.md §9.
SIG_DOWNLOAD = bytes.fromhex("558bec8b4d0833c085c90f94c0a3")
SIG_DOWNLOAD_PATCHED = bytes.fromhex("558bec8b4d0833c085c9b00190a3")
# The fixed prologue of the R0b key-tap cave (keytap_patch.build_cave): pushfd; pushad;
# cld; call $+5; pop eax; lea edi,[eax+... . Distinctive enough to be a positive
# key-tapped signal. See studies/livekey/CODECAVE.md.
KEY_TAP_CAVE_SIG = bytes.fromhex("9c60fce80000000058" "8db8")

# The staging directories, and the whole point of there being two of them. These names
# mirror the run directories one step downstream -- vault/run holds ours, vault/run-live
# holds stock -- so the pairing is the same at both layers and a listing of the vault
# reads top to bottom.
LOOPBACK_DIR = "client-patched"
LIVE_DIR = "client-patched-live"

WHERE = {
    OURS: (LOOPBACK_DIR, "loopback only -- never point this at ArenaNet"),
    STOCK: (LIVE_DIR, "live capture only -- cannot key against our server"),
}


def read_params(exe):
    """(g, p, B) as the client itself would read them. Raises if the struct is not there.

    The accessor is found by a 10-byte signature, and a signature can match more than
    once: the real client carries duplicate matches (make_custom_client's own locate()
    notes it), and bytes an adversary controls -- a code cave, alignment padding -- can
    carry a decoy. `pe.find` returns matches in ascending file offset, so taking hits[0]
    blindly hands the whole ours/stock verdict to whichever copy sorts first, which is
    the exact "filename order is not a safety property" mistake one layer down in the
    bytes. classify() then compares the result to ArenaNet's parameters, and a decoy
    pointing at those would file an OURS build as stock -- the launch gate's worst
    single outcome (ours->live, uncaged; PLAN.md §6.2).

    So do not trust position. Resolve EVERY match and keep only the ones whose struct
    actually has this scheme's shape -- g == 4 over a 512-bit prime, 1 < B < p -- the
    same gate make_custom_client.py applies before it will patch. Exactly one such match
    is the answer; zero or several is undecidable from the bytes and is refused, never
    guessed, the same fail-closed rule the rest of this module runs on. A garbage-pointed
    decoy is skipped because it fails the shape gate; a decoy that reproduces the shape
    is out of scope for a bytes-only reader and would need code-reference analysis, but
    it can no longer win merely by sorting first.
    """
    pe = PE(exe)
    hits = pe.find(SIG_KEYS, ".text")
    if not hits:
        raise SystemExit(
            f"{exe}: the DH accessor signature is not in .text.\n"
            f"  The client was recompiled or the scheme changed. That is a real finding,\n"
            f"  not a tool bug -- re-derive the signature (toolkit/clientscan/dump_dh_params.py)\n"
            f"  before trusting any patching tool against this build.")
    shaped = []
    for h in hits:
        va = struct.unpack_from("<I", pe.data, h + SIG_KEYS_PTR_OFF)[0]
        off = pe.rva_to_off(va - pe.image_base)
        if off is None or off + 136 > len(pe.data):
            continue
        g = int.from_bytes(pe.data[off + 4:off + 8], "little")
        p = int.from_bytes(pe.data[off + 8:off + 72], "little")
        B = int.from_bytes(pe.data[off + 72:off + 136], "little")
        if g == 4 and p.bit_length() == 512 and 1 < B < p:
            shaped.append((va, (g, p, B)))
    if not shaped:
        raise SystemExit(
            f"{exe}: {len(hits)} accessor signature(s) in .text, none pointing at a\n"
            f"  struct shaped like this scheme (g=4, 512-bit prime, 1 < B < p). The\n"
            f"  build changed or the signature now matches only decoy bytes -- a real\n"
            f"  finding, not a tool bug. Re-derive with dump_dh_params.py before trusting\n"
            f"  any patching or launch tool against this build.")
    if len({va for va, _ in shaped}) > 1:
        raise SystemExit(
            f"{exe}: {len(shaped)} accessor signatures resolve to DIFFERENT DH-shaped\n"
            f"  structs (VAs {', '.join('0x%08x' % va for va, _ in shaped)}). Which one\n"
            f"  the client actually reads cannot be decided from the bytes alone, so this\n"
            f"  is REFUSED rather than guessed -- picking one could file an OURS build as\n"
            f"  stock and clear it for the live service. Investigate before launching.")
    return shaped[0][1]


def _ours_records():
    """Every key file we hold the private half of, PROVEN. (kind, label, prime, public).

    "We hold server_private for these" was asserted in this module's docstring from the
    day it was written and checked nowhere: the original required only that `prime` and
    `server_public` be present and parseable. A key file that was stale, hand-edited, or
    truncated mid-write still classified a real client as `ours -- OUR parameters`, with
    the same confidence as a good one.

    That matters because `ours` is not a filing label, it is an operational claim:
    THIS CLIENT CAN KEY AGAINST OUR SERVER. The only thing that makes it true is holding
    the exponent, so the exponent is what gets checked -- B == g^b mod p, against the
    file's own numbers. A matching (prime, public) pair alone proves someone wrote a
    number down.

    A file that fails is skipped rather than reported here, and `classify()` then falls
    through to `unknown`, which every caller refuses. Silence would be wrong for the
    common cause -- a key file for a build we no longer have -- so `key_faults()` exists
    to say what was passed over and why, and `main()` prints it.

    Imported from buildid.py, 2026-08-07, which had it from the start; the two modules
    were written the same afternoon by sessions that could not see each other.
    """
    return [rec for rec, _fault in _ours_candidates() if rec is not None]


def _ours_candidates():
    """[(record | None, fault | None)] over rurik_dh_*.json -- the raw pass."""
    found = []
    for path in sorted(glob.glob(vaultpath.vault_path("keys", "rurik_dh_*.json"))):
        label = os.path.basename(path)
        try:
            with open(path) as fh:
                d = json.load(fh)
        except (OSError, ValueError) as exc:
            found.append((None, f"keys/{label}: unreadable ({exc.__class__.__name__})"))
            continue
        try:
            g, p = int(d["generator"]), int(d["prime"])
            b, B = int(d["server_private"]), int(d["server_public"])
        except (KeyError, TypeError, ValueError):
            missing = [k for k in ("generator", "prime", "server_private", "server_public")
                       if k not in d]
            found.append((None, f"keys/{label}: no usable exponent"
                                + (f" (missing {', '.join(missing)})" if missing else "")))
            continue
        if pow(g, b, p) != B:
            found.append((None, f"keys/{label}: B != g^b mod p -- the file's own numbers "
                                f"disagree, so we do NOT hold this exponent"))
            continue
        found.append(((OURS, label, p, B), None))
    return found


def key_faults():
    """Why any rurik_dh_*.json was not counted as ours. Printed, never silent."""
    return [fault for rec, fault in _ours_candidates() if fault]


def _stock_records():
    """Every set of ArenaNet parameters dumped from a shipped binary."""
    out = []
    for path in sorted(glob.glob(vaultpath.vault_path("keys", "dh_params_*.txt"))):
        vals = {}
        try:
            with open(path) as fh:
                for line in fh:
                    m = re.match(r"\s*(\w+)\s*=\s*(\d+)\s*$", line)
                    if m:
                        vals[m.group(1)] = int(m.group(2))
        except OSError:
            continue
        if "prime" in vals and "server_public" in vals:
            out.append((STOCK, os.path.basename(path), vals["prime"],
                        vals["server_public"]))
    return out


def records():
    """All known parameter sets. Ours first, so a collision would surface as ours."""
    return _ours_records() + _stock_records()


def classify(exe, known=None):
    """('ours' | 'stock' | 'unknown', human-readable detail).

    `known` is injectable so a test can classify against parameters it controls rather
    than against whatever the vault happens to hold today.
    """
    g, p, B = read_params(exe)
    known = records() if known is None else known
    for kind, label, prime, public in known:
        if p == prime and B == public:
            whose = "OUR" if kind == OURS else "ArenaNet's"
            return kind, f"{whose} parameters, keys/{label}"

    # A half-match is not "unrecognised". Writing the prime at the right offset and B at
    # the wrong one is exactly the four-byte struct shift make_custom_client.py guards
    # against, and it produces a binary that looks patched and cannot key.
    for kind, label, prime, public in known:
        if p == prime:
            return UNKNOWN, (f"prime matches keys/{label} but B does NOT -- the struct is "
                             f"half-written, which is the field-shift bug, not a new build")
        if B == public:
            return UNKNOWN, (f"B matches keys/{label} but the prime does NOT -- the struct "
                             f"is half-written")

    return UNKNOWN, (f"g={g}, {p.bit_length()}-bit prime matching no key material in "
                     f"{vaultpath.vault_path('keys')}")


def patch_state(exe):
    """What non-DH modifications a binary carries. Measured, never assumed.

    Each value is three-valued where the bytes allow it: `updater_killed` is None when
    both signatures are absent or both present, because neither is a state this patcher
    produces and rounding an impossible reading to True or False is how a wrong one
    survives. Ported from buildid.py, 2026-08-07.
    """
    try:
        pe = PE(exe)
    except (OSError, ValueError):
        return {}
    live = len(pe.find(SIG_DOWNLOAD, ".text"))
    killed = len(pe.find(SIG_DOWNLOAD_PATCHED, ".text"))
    return {
        "updater_killed": True if (killed == 1 and live == 0)
                          else (False if (live == 1 and killed == 0) else None),
        "mutex_guard_nopped": not pe.find(SIG_MUTEX, ".text"),
        "mutex_renamed": bool(pe.find(MUTEX_NAME_NEW, ".rdata"))
                         and not pe.find(MUTEX_NAME_OLD, ".rdata"),
        # Detected by the cave's own prologue (pushfd;pushad;cld;call $+5;pop eax;lea edi),
        # a positive signal our patcher writes and nothing else does -- not by the ABSENCE
        # of the tap signature, which a different client build would also lack.
        "key_tapped": bool(pe.find(KEY_TAP_CAVE_SIG, ".text")),
    }


def describe(exe, known=None):
    """Everything measurable about one binary, as a dict. `dh` is the safety answer.

    The launch gate's view: it wants the verdict AND enough context to say what it let
    through. Ported from buildid.py, 2026-08-07, unchanged in shape so cage.py reads the
    same either way.
    """
    out = {"path": os.path.abspath(exe), "dh": UNKNOWN, "dh_detail": "",
           "patches": {}, "build_ok": False}
    if not os.path.isfile(exe):
        out["dh_detail"] = "no such file"
        return out
    try:
        out["dh"], out["dh_detail"] = classify(exe, known)
    except SystemExit as exc:
        # classify() raises SystemExit through read_params when the accessor signature
        # is missing, when no match points at a struct of this scheme's shape, or when
        # several point at DIFFERENT shaped structs (undecidable from bytes) -- each a
        # real finding, but not a verdict, and never a reason for a LAUNCH gate to exit
        # the process out from under its caller. Left as `unknown`, which is refused.
        out["dh_detail"] = str(exc).splitlines()[0]
    except (OSError, ValueError) as exc:
        # Not a PE at all, or truncated. `unknown` is already the value in `out`, and
        # unknown is refused everywhere -- but it has to be REACHED rather than raised
        # past, or the gate crashes instead of refusing and the traceback reads as a
        # tool bug rather than as a rejected binary. test_cage.py hands this function a
        # deliberately malformed file for exactly this reason.
        out["dh_detail"] = f"could not read DH parameters: {exc}"
    try:
        pe = PE(exe)
        out["patches"] = patch_state(exe)
        out["sha256"] = hashlib.sha256(pe.data).hexdigest()
        out["build_ok"] = True
    except (OSError, ValueError) as exc:
        out["dh_detail"] += f" (and the PE would not parse: {exc})"
    return out


def inventory(directory):
    """[(path, kind, detail)] for every .exe in `directory`, newest first.

    Newest-first rather than sorted by name, because name order is the thing that broke.
    """
    if not os.path.isdir(directory):
        return []
    exes = [os.path.join(directory, f) for f in os.listdir(directory)
            if f.lower().endswith(".exe")]
    exes.sort(key=os.path.getmtime, reverse=True)
    out = []
    for path in exes:
        try:
            kind, detail = classify(path)
        except SystemExit as e:
            kind, detail = UNKNOWN, str(e).splitlines()[0]
        out.append((path, kind, detail))
    return out


def select(kind, directory=None, why="", match=None, verbose=True):
    """The newest build in `directory` carrying `kind`'s parameters. Raises, never guesses.

    `match` is an optional (prime, server_public) pair, for a caller that needs more than
    the right KIND: it needs the build keyed to one specific key file. `classify` answers
    "ours" for any build matching any `rurik_dh_*.json`, and with two of those in the
    vault the wrong one still derives a key the server cannot match. `test_handshake.py`
    passes the parameters `authsrv.load_keys` will actually load, so agreement is required
    rather than assumed. `g` is deliberately not part of the comparison -- generator 4 is
    ArenaNet's too, so every candidate on this machine agrees on it and it discriminates
    nothing.

    Rejected candidates are printed on the way past, not only on failure. A run that
    quietly skipped a binary and tested a different one is how the original afternoon was
    lost; saying which and why costs one line.

    The message is the product here. A caller that picks the wrong artifact and then
    reports a key mismatch sends whoever reads it into gwcrypto.py, so this says ARTIFACT
    in the first line and lists every candidate with the reason it was passed over.
    """
    subdir, rule = WHERE[kind]
    directory = directory or vaultpath.vault_path(subdir)
    found = inventory(directory)

    chosen, rejected = None, []
    for path, k, detail in found:
        if k != kind:
            rejected.append((path, f"{k} -- {detail}"))
            continue
        if match is not None:
            _, p, B = read_params(path)
            wrong = ([] if p == match[0] else ["prime"]) + \
                    ([] if B == match[1] else ["server public value"])
            if wrong:
                rejected.append((path, f"{kind}, but its {' and '.join(wrong)} is not "
                                       f"the one the server will load"))
                continue
        if chosen is None:
            chosen = path

    if verbose:
        for path, reason in rejected:
            print(f"  skipped      : {os.path.basename(path)}\n                 {reason}")
    if chosen is not None:
        return chosen

    whose = "OUR" if kind == OURS else "ArenaNet's stock"
    lines = [f"WRONG ARTIFACT -- this is not a crypto failure, so do not go reading "
             f"gwcrypto.py.",
             f"  Nothing in {directory} carries {whose} Diffie-Hellman parameters"
             + (f" ({why})." if why else ".")]
    if found:
        lines.append("  What is there:")
        for path, k, detail in found:
            lines.append(f"    {os.path.basename(path):44s} {k:8s} {detail}")
        if match is not None:
            lines.append("  ...and the caller additionally required the parameters the "
                         "server will load.")
    else:
        lines.append("  The directory is empty or absent.")
    lines.append(f"  A {kind}-DH client is {rule}.")
    if kind == OURS:
        lines.append("  Build one:  python toolkit/clientpatch/make_custom_client.py")
        lines.append(f"  A stock-DH build belongs in vault/{LIVE_DIR}/, not here -- "
                     f"see PLAN.md §6.2.")
    else:
        lines.append("  Build one:  python toolkit/clientpatch/make_custom_client.py "
                     "--no-dh-patch")
    lines.append("  NOTHING WAS TESTED.")
    raise SystemExit("\n".join(lines))


def main():
    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})\n")
    known = records()
    print(f"key material: {len(known)} parameter set(s)")
    for kind, label, prime, _ in known:
        print(f"  {kind:8s} keys/{label}  ({prime.bit_length()}-bit prime)")
    # A key file that failed the exponent proof is not a missing file, and the two look
    # identical from here unless one of them says so: a build keyed to it drops to
    # `unknown` and gets refused at the launch gate with a message about the BINARY,
    # which sends the reader to the wrong artifact entirely.
    faults = key_faults()
    if faults:
        print(f"\n  {len(faults)} key file(s) NOT counted as ours:")
        for f in faults:
            print(f"    {f}")
        print("    A build keyed to one of these classifies as `unknown` and is refused.")

    bad = 0
    for subdir, expect in ((LOOPBACK_DIR, OURS), (LIVE_DIR, STOCK),
                           ("run", OURS), ("run-live", STOCK)):
        root = vaultpath.vault_path(subdir)
        print(f"\nvault/{subdir}/   expects {expect}  ({WHERE[expect][1]})")
        if not os.path.isdir(root):
            print("  (absent)")
            continue
        # Staging dirs hold loose exes; run dirs hold <tag>/Gw.exe. Handle both.
        entries = inventory(root)
        for name in sorted(os.listdir(root)):
            nested = os.path.join(root, name, "Gw.exe")
            if os.path.isfile(nested):
                try:
                    kind, detail = classify(nested)
                except SystemExit as e:
                    kind, detail = UNKNOWN, str(e).splitlines()[0]
                entries.append((nested, kind, detail))
        if not entries:
            print("  (empty)")
        for path, kind, detail in entries:
            ok = kind == expect
            if not ok:
                bad += 1
            rel = os.path.relpath(path, root)
            print(f"  [{'ok' if ok else '!!'}] {rel:46s} {kind:8s} {detail}")
            # The non-DH patches decide nothing about placement, but RUNBOOK.md's
            # "stuck on Connecting to ArenaNet" row sends the reader here to check
            # exactly one of them: a client whose updater is still LIVE stalls forever
            # behind the cage on a blocked update check, which presents as a hang.
            # Printing it here is what makes that row's instruction true.
            ps = patch_state(path)
            if ps:
                upd = {True: "killed", False: "LIVE", None: "?"}[ps["updater_killed"]]
                print(f"       updater={upd:6s} "
                      f"mutex={'nopped' if ps['mutex_guard_nopped'] else 'intact':6s} "
                      f"name={'renamed' if ps['mutex_renamed'] else 'stock'}")

    print(f"\n{bad} build(s) in the wrong place." if bad else "\nEvery build is where it belongs.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
