"""Prove a client build is placed by its bytes, and that the old failure cannot recur.

    python toolkit/clientpatch/test_dhbuild.py

WHAT THIS IS DEFENDING. On 2026-08-06 a live-capture build -- ArenaNet's stock DH,
correct and wanted -- was written into `vault/client-patched/` as `Gw.live.<tag>.exe`,
beside the DH-patched `Gw.custom.<tag>.exe`. Two tools chose "the patched client" from
that directory with `sorted(...)[-1]`, `l` sorts after `c`, and both silently changed
which binary they were talking about. `test_handshake.py` reported four failures and a
short check count that read as a crypto regression; `make_run_dir.py` would have
assembled a client that cannot key into `vault/run/`, which `drive_client.assert_safe`
treats as the set of legal loopback targets.

So the load-bearing test here is section 3, which rebuilds that directory -- both builds
together, the stock one named so it sorts LAST -- and requires selection to still return
the DH-patched one. A fix for a name-ordering bug that is never shown a hostile ordering
has not been tested.

Sections 1 and 2 are the classifier itself, including the half-written struct, because a
classifier that only ever answers on well-formed input is not one. Section 4 asserts the
live invariant: every build in the vault sits in the directory its parameters say it
belongs in.

Section 5 asserts the other half of that, and it is a different claim. Section 4 says
every build is filed correctly TODAY; section 5 says the tool cannot file one wrongly
TOMORROW. Until 2026-08-07 it could: `make_run_dir.py` classified the source exe
byte-for-byte and accepted `--dest` on trust, so `--dest <vault>/run-live/<tag>` with no
`--live` assembled a DH-patched client into the one directory that must not be caged --
no flag in that command sounds dangerous, and every existing guard passed it.

Read-only. Reads client binaries and key files out of the vault and launches nothing.
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import dhbuild  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED, not guessed: a green run on 2026-08-07 with every fixture present reports
# 34 checks -- 4 + 4 (sections 1-2), 6 (section 3), one per build on disk in section 4
# (5 here), 5 (section 5), 5 (section 6), 5 (section 7).
#
# The floor is 23: sections 1, 2, 5, 6 and 7. Sections 1 and 2 need only a pristine
# client and the vault's key files; section 5 is pure path arithmetic; section 6 builds
# its own synthetic vault under RURIK_VAULT; section 7 builds synthetic PE fixtures in a
# tempdir. None of the five can be thinned by a machine's fixtures, so all five are the
# mandatory core.
#
# It stays below 34 because the two richer sections are genuinely fixture-dependent
# and both declare skips: section 3 needs one build of EACH kind, and a machine that has
# not built the live client yet is a legal state (it was this repo's state until
# 2026-08-06), while section 4 counts whatever is on disk. checks.py asks a floor to be
# the mandatory core for exactly this case; the skips are what keep a thin run from
# reading as a thorough one, and the ledger prints them in the verdict.
#
# Section 3 is still outside the floor and that is a known weakness, not a decision this
# comment is defending: it is the only section that proves the 2026-08-06 regression is
# fixed, and a machine missing either build silently does not run it.
LEDGER = checks.Ledger("dhbuild", floor=23)


def scratch_copy(src, dst):
    """Copy a client binary into a scratch directory. A COPY, deliberately.

    The first version hardlinked, to save writing 10 MB twice. A hardlink is the same
    inode under two names, so the `os.utime` below -- which exists to make the scratch
    file the newest one -- rewrote the mtime of the VAULT artifact instead. Harmless in
    itself and exactly the class of thing a read-only test must not do; make_run_dir.py's
    own header makes the same argument about Gw.dat. 10 MB is cheap.
    """
    shutil.copy2(src, dst)
    return dst


def _dh_struct(g, p, B):
    """The 136-byte pinned struct as read_params reads it: word0, g, p (64B), B (64B)."""
    return (struct.pack("<I", 1) + struct.pack("<I", g)
            + p.to_bytes(64, "little") + B.to_bytes(64, "little"))


def _synth_pe(structs):
    """A minimal PE32 gwpe.PE can parse, carrying one accessor signature per entry.

    `structs` is a list; each entry is a 136-byte struct or None. For each, a SIG_KEYS
    match is planted in .text followed by a VA (at +SIG_KEYS_PTR_OFF) pointing at that
    struct in .rdata -- or an unbacked VA for None, the "decoy that resolves nowhere"
    case. IDENTICAL structs share ONE address, because that is what a real duplicated
    accessor does: the same function inlined twice carries the same immediate, so
    read_params must treat same-VA duplicates as one answer and only refuse when the
    matches disagree. Writing each copy to its own address would test a scenario the
    binary never produces.
    """
    IB = 0x400000
    text = bytearray(b"\x90" * 0x400)
    rdata = bytearray(0x800)
    cur, rcur, placed = 0x10, 0x10, {}
    for st in structs:
        text[cur:cur + len(dhbuild.SIG_KEYS)] = dhbuild.SIG_KEYS
        if st is None:
            va = 0                                   # not backed by any section
        elif bytes(st) in placed:
            va = placed[bytes(st)]                    # real duplicate -> same VA
        else:
            rdata[rcur:rcur + len(st)] = st
            va = IB + 0x2000 + rcur
            placed[bytes(st)] = va
            rcur += len(st) + 8
        off = cur + dhbuild.SIG_KEYS_PTR_OFF
        text[off:off + 4] = struct.pack("<I", va)
        cur += 0x40
    e, opt = 0x80, 0xE0
    hdr = bytearray(0x400)
    hdr[0:2] = b"MZ"
    struct.pack_into("<I", hdr, 0x3C, e)
    hdr[e:e + 4] = b"PE\x00\x00"
    struct.pack_into("<H", hdr, e + 4, 0x14C)        # x86
    struct.pack_into("<H", hdr, e + 6, 2)            # 2 sections
    struct.pack_into("<H", hdr, e + 20, opt)
    struct.pack_into("<H", hdr, e + 24, 0x10B)       # PE32
    struct.pack_into("<I", hdr, e + 52, IB)          # image base
    base = e + 24 + opt
    for i, (name, va, vs, rp, rs) in enumerate(
            [(".text", 0x1000, 0x400, 0x400, 0x400),
             (".rdata", 0x2000, 0x800, 0x800, 0x800)]):
        o = base + i * 40
        hdr[o:o + 8] = name.encode().ljust(8, b"\0")
        struct.pack_into("<I", hdr, o + 8, vs)
        struct.pack_into("<I", hdr, o + 12, va)
        struct.pack_into("<I", hdr, o + 16, rs)
        struct.pack_into("<I", hdr, o + 20, rp)
    return bytes(hdr) + bytes(text) + bytes(rdata)


def main():
    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})")

    # ---- 1. read the struct out of a binary we did not write ------------------
    print("\n1. the pinned struct, read from ArenaNet's own shipped client")
    cdir = vaultpath.require_dir("client", why="a pristine client to classify")
    pristine = None
    for build in sorted(os.listdir(cdir), reverse=True):
        cand = os.path.join(cdir, build, "Gw.exe")
        if os.path.isfile(cand):
            pristine = cand
            break
    if pristine is None:
        raise SystemExit(f"no Gw.exe under any build in {cdir} — see RUNBOOK.md")
    print(f"   {os.path.relpath(pristine, vaultpath.vault_root())}")

    g, p, B = dhbuild.read_params(pristine)
    LEDGER.ok(g == 4, "generator is 4", str(g))
    LEDGER.ok(p.bit_length() == 512, "prime is 512-bit", f"{p.bit_length()} bits")
    LEDGER.ok(1 < B < p, "B is in range 1 < B < p")

    # The shipped client must classify as stock. This is the check the artifact can
    # refute: the parameters come from the exe, the record they are compared against
    # came out of dump_dh_params.py on a different day, and nothing here forces
    # agreement.
    kind, detail = dhbuild.classify(pristine)
    LEDGER.ok(kind == dhbuild.STOCK, "the pristine client classifies as stock",
              f"{kind} -- {detail}")

    # ---- 2. the classifier, on parameters this test controls -------------------
    print("\n2. the classifier, against records it is handed")
    ours = [(dhbuild.OURS, "synthetic-ours.json", p, B)]
    kind, _ = dhbuild.classify(pristine, known=ours)
    LEDGER.ok(kind == dhbuild.OURS, "the same bytes classify as ours against an ours record",
              kind)

    # A prime that matches with a B that does not is the four-byte struct shift
    # make_custom_client.py's own comment records catching in development. It must be
    # named, not filed under "unrecognised build".
    half = [(dhbuild.OURS, "synthetic-half.json", p, B ^ 1)]
    kind, detail = dhbuild.classify(pristine, known=half)
    LEDGER.ok(kind == dhbuild.UNKNOWN, "a half-written struct is not accepted", kind)
    LEDGER.ok("half-written" in detail, "and it is reported AS half-written, not as new",
              detail)

    kind, detail = dhbuild.classify(pristine, known=[])
    LEDGER.ok(kind == dhbuild.UNKNOWN, "no key material at all means unknown", kind)

    # ---- 3. THE REGRESSION: hostile filename order ----------------------------
    print("\n3. both builds in one directory, stock sorting LAST")
    loop_dir = vaultpath.vault_path(dhbuild.LOOPBACK_DIR)
    live_dir = vaultpath.vault_path(dhbuild.LIVE_DIR)
    try:
        ours_exe = dhbuild.select(dhbuild.OURS, loop_dir)
        stock_exe = dhbuild.select(dhbuild.STOCK, live_dir)
    except SystemExit as e:
        ours_exe = stock_exe = None
        LEDGER.skip("hostile filename order",
                    f"need one build of each kind in the vault: {str(e).splitlines()[0]}")

    if ours_exe and stock_exe:
        with tempfile.TemporaryDirectory() as tmp:
            # `Gw.zzz...` sorts after `Gw.aaa...` under exactly the rule that broke
            # this -- and it is also the NEWER file by mtime, so neither the old
            # selection nor a naive "newest wins" would get it right.
            scratch_copy(ours_exe, os.path.join(tmp, "Gw.aaa.exe"))
            wrong = scratch_copy(stock_exe, os.path.join(tmp, "Gw.zzz.exe"))
            os.utime(wrong, None)

            names = sorted(os.listdir(tmp))
            LEDGER.ok(names[-1] == "Gw.zzz.exe",
                      "the scratch directory really does sort the stock build last",
                      str(names))

            picked = dhbuild.select(dhbuild.OURS, tmp)
            LEDGER.ok(os.path.basename(picked) == "Gw.aaa.exe",
                      "select(ours) ignores name order and returns the DH-patched build",
                      os.path.basename(picked))
            LEDGER.ok(dhbuild.classify(picked)[0] == dhbuild.OURS,
                      "and what it returned really does carry our parameters")

            picked = dhbuild.select(dhbuild.STOCK, tmp)
            LEDGER.ok(os.path.basename(picked) == "Gw.zzz.exe",
                      "select(stock) finds the live build in the same directory",
                      os.path.basename(picked))

        # A directory holding only the wrong kind must REFUSE, and the refusal is the
        # product: it has to say ARTIFACT loudly enough that nobody opens gwcrypto.py.
        with tempfile.TemporaryDirectory() as tmp:
            scratch_copy(stock_exe, os.path.join(tmp, "Gw.live.exe"))
            try:
                got = dhbuild.select(dhbuild.OURS, tmp)
                LEDGER.ok(False, "a stock-only directory refuses select(ours)",
                          f"returned {got}")
            except SystemExit as e:
                msg = str(e)
                LEDGER.ok(True, "a stock-only directory refuses select(ours)")
                LEDGER.ok("WRONG ARTIFACT" in msg and "gwcrypto" in msg,
                          "and the refusal names the artifact instead of the crypto",
                          msg.splitlines()[0])

    # ---- 4. the live invariant ------------------------------------------------
    print("\n4. every build in the vault is where its parameters say it belongs")
    seen = 0
    for subdir, expect in ((dhbuild.LOOPBACK_DIR, dhbuild.OURS),
                           (dhbuild.LIVE_DIR, dhbuild.STOCK),
                           ("run", dhbuild.OURS), ("run-live", dhbuild.STOCK)):
        root = vaultpath.vault_path(subdir)
        if not os.path.isdir(root):
            continue
        found = list(dhbuild.inventory(root))
        for name in sorted(os.listdir(root)):
            nested = os.path.join(root, name, "Gw.exe")
            if os.path.isfile(nested):
                found.append((nested,) + dhbuild.classify(nested))
        for path, kind, detail in found:
            seen += 1
            LEDGER.ok(kind == expect,
                      f"vault/{subdir}/{os.path.relpath(path, root)} is {expect}",
                      f"{kind} -- {detail}")
    if not seen:
        LEDGER.skip("vault placement", "no builds in any staging or run directory")

    # ---- 5. the destination is a safety assertion, and it is checked -----------
    # Section 4 proves every build on disk is filed correctly TODAY. This proves the
    # tool cannot file one wrongly TOMORROW, which is a different claim: until
    # 2026-08-07 make_run_dir.py classified the source exe byte-for-byte and took
    # --dest entirely on trust, so `--dest <vault>/run-live/<tag>` with no --live
    # assembled a DH-patched client into the directory that must not be caged.
    #
    # Pure-function checks, so no 4 GB copy is involved: the refusal happens before
    # anything is written.
    print("\n5. a run directory cannot be assembled into the other kind's root")
    import make_run_dir  # noqa: E402  -- imported here; it is a CLI, not a library

    for subdir, expect, why in (
            ("run", dhbuild.OURS, "vault/run means ours"),
            ("run-live", dhbuild.STOCK, "vault/run-live means stock"),
    ):
        got, _ = make_run_dir.root_meaning(vaultpath.vault_path(subdir, "2026-01-01_x"))
        LEDGER.ok(got == expect, why, f"got {got}")

    # The trap this function was written around: "run-live" starts with "run", so a
    # bare startswith would file every live build as a loopback one -- the failure
    # arriving through the check meant to catch it.
    got, _ = make_run_dir.root_meaning(vaultpath.vault_path("run-live"))
    LEDGER.ok(got == dhbuild.STOCK,
              "the run/run-live prefix trap: run-live does not read as run",
              f"got {got}")

    got, _ = make_run_dir.root_meaning(vaultpath.vault_path("runaway"))
    LEDGER.ok(got is None,
              "a sibling that merely starts with 'run' belongs to neither",
              f"got {got}")

    got, _ = make_run_dir.root_meaning(os.path.join(tempfile.gettempdir(), "elsewhere"))
    LEDGER.ok(got is None,
              "a path outside both roots is refused rather than defaulted",
              f"got {got} -- it would inherit no cage sweep and no assert_safe guarantee")

    # ---- 6. `ours` means we hold the exponent, and that is checked -------------
    # The claim "we hold server_private for these" sat in this module's docstring from
    # the day it was written and was checked nowhere. Run against a SYNTHETIC vault --
    # RURIK_VAULT, the override vaultpath.py exists for -- because the real vault
    # deliberately contains no broken key file, and a refusal nobody has watched fire
    # is the same class of thing as a green test that asserts nothing.
    print("\n6. a key file we cannot decrypt with does not make a build `ours`")
    g, p, b = 4, 0xE1F5A3B7C9D14E2F, 12345
    good_B = pow(g, b, p)
    fake = {
        "rurik_dh_good.json": dict(generator=g, prime=p,
                                   server_private=b, server_public=good_B),
        "rurik_dh_wrong_B.json": dict(generator=g, prime=p,
                                      server_private=b, server_public=good_B ^ 1),
        "rurik_dh_no_private.json": dict(generator=g, prime=p, server_public=good_B),
        "rurik_dh_truncated.json": None,        # written as a partial file below
    }
    with tempfile.TemporaryDirectory() as tmp:
        keys = os.path.join(tmp, "keys")
        os.makedirs(keys)
        for name, d in fake.items():
            with open(os.path.join(keys, name), "w") as fh:
                fh.write('{"generator": 4, "prime":' if d is None else json.dumps(d))

        code = ("import sys, json; sys.path[:0]=['toolkit','toolkit/clientpatch']\n"
                "import dhbuild\n"
                "print(json.dumps({'ours': [r[1] for r in dhbuild._ours_records()],\n"
                "                  'faults': dhbuild.key_faults()}))\n")
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=os.path.dirname(os.path.dirname(HERE)),
            env=dict(os.environ, RURIK_VAULT=tmp),
            capture_output=True, text=True, timeout=120)

        if proc.returncode != 0:
            LEDGER.skip("exponent proof", f"probe did not run: {proc.stderr.strip()[:120]}")
        else:
            got = json.loads(proc.stdout.strip().splitlines()[-1])
            LEDGER.ok(got["ours"] == ["rurik_dh_good.json"],
                      "only the key file whose B == g^b mod p counts as ours",
                      f"accepted {got['ours']}")
            blob = " | ".join(got["faults"])
            LEDGER.ok("rurik_dh_wrong_B.json" in blob and "g^b mod p" in blob,
                      "a key file whose own numbers disagree is refused, and says so",
                      "this is the case that used to pass: matching (prime, public) "
                      "with an exponent that does not produce them")
            LEDGER.ok("rurik_dh_no_private.json" in blob and "server_private" in blob,
                      "a key file with NO exponent at all is refused, naming the field")
            LEDGER.ok("rurik_dh_truncated.json" in blob,
                      "a half-written key file is refused rather than parsed past")
            LEDGER.ok(len(got["faults"]) == 3,
                      "every refusal is reported, so a bad key file is never silent",
                      f"{len(got['faults'])} faults: a build keyed to one of these drops "
                      f"to `unknown`, and the launch gate then blames the BINARY")

    # ---- 7. the accessor is chosen by shape, not by file position --------------
    # The signature can match more than once -- the real client duplicates it, and bytes
    # an adversary or an accident controls (a code cave, alignment padding) can carry a
    # decoy. read_params used to take the FIRST match (pe.find returns them in ascending
    # file offset), so a decoy sorting ahead of the real accessor and pointing at
    # ArenaNet's own parameters would make an OURS build read as stock -- and the launch
    # gate clears stock for the live service, uncaged, which is PLAN.md §6.2's
    # account-ending case reached through the classifier. The fix keeps only matches
    # whose struct has this scheme's shape (g=4, 512-bit prime, 1 < B < p) and refuses
    # when that is not exactly one. Synthetic PEs, so no vault fixture is needed and the
    # section is mandatory core. "Filename order is not a safety property" -- one layer
    # further down, in the bytes.
    print("\n7. a decoy accessor cannot win by sorting first")
    g, p = 4, (1 << 511) | (1 << 270) | 0x1234567 | 1
    while p.bit_length() != 512:
        p |= (1 << 511)
    B = pow(g, 987654321, p)
    real = _dh_struct(g, p, B)
    bad_shape = _dh_struct(0, p, B)                       # g != 4, fails the shape gate
    p2 = (1 << 511) | (1 << 300) | 0x55 | 1
    while p2.bit_length() != 512:
        p2 |= (1 << 511)
    other = _dh_struct(g, p2, pow(g, 111, p2))            # a DIFFERENT valid struct

    def reads_to(structs):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as fh:
            fh.write(_synth_pe(structs))
            path = fh.name
        try:
            return ("ok", dhbuild.read_params(path))
        except SystemExit as exc:
            return ("refused", str(exc).splitlines()[0])
        finally:
            os.unlink(path)

    LEDGER.ok(reads_to([real]) == ("ok", (g, p, B)),
              "a single well-formed accessor reads back its parameters")
    LEDGER.ok(reads_to([bad_shape, real]) == ("ok", (g, p, B)),
              "a shape-failing decoy sorted FIRST is skipped for the real accessor",
              "this is the misclassification the fix closes")
    LEDGER.ok(reads_to([None, real]) == ("ok", (g, p, B)),
              "a decoy whose VA resolves nowhere, sorted first, is likewise skipped")
    LEDGER.ok(reads_to([real, real]) == ("ok", (g, p, B)),
              "a genuine duplicate (same VA twice) is one answer, not a conflict",
              "the real client carries duplicate matches; this must not regress")
    LEDGER.ok(reads_to([real, other])[0] == "refused",
              "two DIFFERENT DH-shaped structs are undecidable from bytes and REFUSED",
              "picking one could file an ours build as stock and clear it for live")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
