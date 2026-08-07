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
    """(g, p, B) as the client itself would read them. Raises if the struct is not there."""
    pe = PE(exe)
    hits = pe.find(SIG_KEYS, ".text")
    if not hits:
        raise SystemExit(
            f"{exe}: the DH accessor signature is not in .text.\n"
            f"  The client was recompiled or the scheme changed. That is a real finding,\n"
            f"  not a tool bug -- re-derive the signature (toolkit/clientscan/dump_dh_params.py)\n"
            f"  before trusting any patching tool against this build.")
    va = struct.unpack_from("<I", pe.data, hits[0] + SIG_KEYS_PTR_OFF)[0]
    off = pe.rva_to_off(va - pe.image_base)
    if off is None:
        raise SystemExit(f"{exe}: DH struct VA 0x{va:08x} is not backed by file bytes")
    return (int.from_bytes(pe.data[off + 4:off + 8], "little"),
            int.from_bytes(pe.data[off + 8:off + 72], "little"),
            int.from_bytes(pe.data[off + 72:off + 136], "little"))


def _ours_records():
    """Every key file we hold the private half of. (kind, label, prime, public)."""
    out = []
    for path in sorted(glob.glob(vaultpath.vault_path("keys", "rurik_dh_*.json"))):
        try:
            with open(path) as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue                      # a truncated key file is not a stock build
        if "prime" in d and "server_public" in d:
            out.append((OURS, os.path.basename(path), int(d["prime"]),
                        int(d["server_public"])))
    return out


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


def select(kind, directory=None, why=""):
    """The newest build in `directory` carrying `kind`'s parameters. Raises, never guesses.

    The message is the product here. A test that picks the wrong artifact and then reports
    a key mismatch sends whoever reads it into gwcrypto.py, and that is where the last one
    cost an afternoon -- so this says ARTIFACT in the first line and lists what it found.
    """
    subdir, rule = WHERE[kind]
    directory = directory or vaultpath.vault_path(subdir)
    found = inventory(directory)
    for path, k, _ in found:
        if k == kind:
            return path

    whose = "OUR" if kind == OURS else "ArenaNet's stock"
    lines = [f"WRONG ARTIFACT -- this is not a crypto failure, so do not go reading "
             f"gwcrypto.py.",
             f"  Nothing in {directory} carries {whose} Diffie-Hellman parameters"
             + (f" ({why})." if why else ".")]
    if found:
        lines.append("  What is there:")
        for path, k, detail in found:
            lines.append(f"    {os.path.basename(path):44s} {k:8s} {detail}")
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
    raise SystemExit("\n".join(lines))


def main():
    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})\n")
    known = records()
    print(f"key material: {len(known)} parameter set(s)")
    for kind, label, prime, _ in known:
        print(f"  {kind:8s} keys/{label}  ({prime.bit_length()}-bit prime)")

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

    print(f"\n{bad} build(s) in the wrong place." if bad else "\nEvery build is where it belongs.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
