"""Prove movehook's plumbing works, and that it REFUSES rather than lying.

    python toolkit/clientscan/movehook/test_movehook.py

WHY THIS FILE EXISTS AT ALL. `trnhook/` has no test, and `srclint` therefore imposes
nothing on it -- which was **silence, not a ruling**, until the owner made it one:
PLAN.md §7 Q12(b), 2026-08-26. A hook DLL is an instrument whose entire output is a
ledger, and the interesting answer is often a small number. That is the worst shape
for a tool to be quietly broken in, because "the hook was dead" and "the client never
did it" produce the same zero. `test_commandertrap.py` is the precedent this copies:
exercise the machinery against a process this machine controls, where the right
answer is KNOWN, and reserve skips for what genuinely needs the vaulted client.

WHAT IS CHECKED, and which of them need what:

  §1  the generated header agrees with content/movecode.toml     needs the client
  §2  every site's first byte really is 0x55 in the pinned image needs the client
  §3  the provenance rules actually refuse a bad row             process-free
  §4  the reader parses a synthetic capture correctly            process-free
  §5  the reader REFUSES when control A failed                   process-free
  §6  the DLL builds, and it is x86                              needs a compiler
  §7  inject into a throwaway 32-bit cmd.exe and read it back    needs cmd.exe
  §8  movehook.cfg beats the environment                         rides on §7
  §9  attach.py refuses a client that is not build 38797         process-free
  §10 pathdiff replays queries through the REAL Ascalon mesh     needs the archive
  §11 the reader's field layout matches rec_t in movehook.c      process-free
  §12 the world-copy census: two objects per id, and a non-agent process-free
  §13 the displacement count -- what K1's prediction is refuted by process-free
  §14 the 2026-08-28 sites, the refusal that shaped them, and v6  mostly pf

§7 IS THE ONE THAT MATTERS AND IT IS THE ONE THAT COULD NOT EXIST WITHOUT THE
RULING. It injects the real DLL into a real 32-bit process, waits for the run to
end, and reads the sidecar. The four hook RVAs are ~2 MB into the image and cmd.exe
is far smaller, so **every site fails to arm** -- which is exactly the property worth
testing: the DLL must survive sites that do not resolve, must not corrupt its host,
and must report `hits 0` honestly rather than crashing or claiming success. Control A
must still fire, because it touches no host byte. That is a control on the control.

§5 is the negative control for the whole file. A reader that scores a capture whose
handler never ran is worse than no reader, so the refusal is exercised on purpose.
"""
import os
import re
import math
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENTSCAN = os.path.dirname(HERE)
TOOLKIT = os.path.dirname(CLIENTSCAN)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, CLIENTSCAN)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
import checks                                                   # noqa: E402

# MEASURED off a real green run, 2026-08-27 -- counted per section out of the
# banner, never computed by addition. A whole green run on this machine is 81:
#
#   §1   6   sites.h is what the generator emits     needs the vaulted client
#   §2  10   first bytes vs the pinned image         needs the vaulted client
#   §3   4   the provenance rules really refuse      process-free
#   §4  16   the reader's parse, v1..v4, scoring      process-free
#   §5   6   dead-control refusal + the commit flag  process-free
#   §6   2   the DLL builds, and it is x86           needs a compiler
#   §7   5   inject into a live 32-bit cmd.exe       needs a 32-bit cmd.exe
#   §8   2   movehook.cfg beats the environment      rides on §7's injected run
#   §9  11   attach.py's build guard + the stale check process-free
#   §10  8   pathdiff replays vs the REAL mesh       needs the vaulted archive
#   §11  4   the reader's layout vs rec_t IN THE C   process-free
#   §12  6   the world-copy census, both directions  process-free
#   §13  5   the displacement count, both directions process-free
#   §14 59   2026-08-28 sites, v6, setposition, the tick + its STRIDE  50 pf + 9 client
#   §15  3   the dispatch loop reaches its emulation  process-free
#   ----    process-free core = 105, and THAT is the floor.
#
# §12 and §13 both read `gensites.rows()`, which goes to `content.load()` and never
# opens the client, so their eleven are process-free and the core moved with them.
# A whole green run on this machine is now 153.
#
# §14 SPLITS, and the split was counted out of the banner rather than reasoned
# about: 25 checks, of which the 8 non-entry refusals and their 1 control call
# `gensites.verify()` and therefore need the vaulted image, while the row
# assertions and the whole v6 round-trip go through `content.load()` and a
# synthesised capture and never open it. 59 - 9 = 50 process-free, so the core
# moves 46 -> 102, and §15's three take it to 105.
#
# The first draft of this comment guessed 16 by adding up what the sections
# looked like they contained, and it was two low -- which would have let two
# checks stop running with the suite still green. The rule the repo already has
# ("set the floor from a real green run, never from a guess") is not about
# arithmetic being hard; it is that a floor derived from the code rather than
# from the output drifts the moment either changes. `skip()` lowers the floor by
# ZERO, so a bare machine must still clear 105.
#
# 2026-08-29, THE RETURN TAP. Re-counted per section out of a real green run on
# this machine, which is now 285 (was 215):
#
#   §1   6  §2  39  §3   4  §4  16  §5   6  §6   2  §7  11  §8   2  §9  13
#   §10  8  §11  4  §12  6  §13  5  §14 63  §15  3  §15b 4  §16 25
#   §17 43  §17e 7  §17f 4  §18 8  §19 6
#
# CLIENT-DEPENDENT (opens the vaulted image): §1, §2, and the three
# `gensites.verify()` blocks inside §14 and the six inside §17.
# COMPILER / cmd.exe / ARCHIVE: §6, §7, §8, §10, §16.
# PROCESS-FREE CORE, which is what the floor is:
#   §3 4 + §4 16 + §5 6 + §9 13 + §11 4 + §12 6 + §13 5 + §14 54 + §15 3
#   + §15b 4 + §17 37 + §17e 7 + §17f 4 + §19 6 = 169.
#
# §18 (map identification, 8 checks) needs the vaulted archive AND the r7
# capture, so it is NOT in the core and the floor does not move for it --
# it skips cleanly on a machine without them.
#
# §17 SPLITS the way §14 does and the split was read off the banner, not
# reasoned about: 37 checks, of which 6 (the generator's own gate plus its five
# refusals) call `gensites.verify()` and need the image, while the 21 row
# assertions, the 4 layout checks and the 6 synthetic-capture checks go through
# `content.load()` and a fixture built from readhook's own layout. §17(b) SKIPS
# rather than dying when the image is absent -- `pinned.find()` exits the
# process rather than raising, so an `except Exception` around it catches
# nothing, which is a trap §2 is still standing in.
LEDGER = checks.Ledger("movehook", floor=169)
check = checks.adopt(LEDGER)

WOW64_CMD = r"C:\Windows\SysWOW64\cmd.exe"
NO_CLIENT = "the pinned 38797 client is not in the vault"


def eq(got, want, label):
    return check(got == want, label,
                 "" if got == want else f"got {got!r}, want {want!r}")


# ---------------------------------------------------------------- §1, §2
def section_1_2():
    """The header is generated from the rows, and the rows match the binary."""
    try:
        import gensites
    except Exception as ex:                                      # pragma: no cover
        LEDGER.skip("1-2. header vs rows vs binary", f"cannot import gensites: {ex}")
        return
    try:
        sites, offs, _coffs = gensites.rows()
    except Exception as ex:
        LEDGER.skip("1-2. header vs rows vs binary", f"content store: {ex}")
        return

    check(len(sites) >= 4, "1. at least the four MOVECODE hook sites are rowed",
          f"{len(sites)}: {sorted(sites)}")
    for want in ("bake", "teleport", "setter", "agtrack"):
        check(want in sites, f"1. `{want}` has a row")

    try:
        bad, path = gensites.verify(sites)
    except Exception as ex:
        LEDGER.skip("2. first bytes vs the pinned image", f"{NO_CLIENT}: {ex}")
        return
    check(not bad, "2. every row's first byte matches the pinned 38797 image",
          "; ".join(f"{n}: {w}" for n, w in bad) if bad else f"read {path}")
    # The load-bearing one: every site's byte must be ITS OWN SHAPE's, because
    # that byte is the instruction the handler will re-emulate. This was a flat
    # `== 0x55` until 2026-08-29, when the MapFindPath ret tap added SHAPE_RET;
    # note it did NOT become "0x55 or 0xC3", which would let a ret's emulation
    # be armed on an entry byte -- the pairing is per row and checked as a pair.
    for name in sorted(sites):
        shape = sites[name].get("shape", gensites.DEFAULT_SHAPE)
        want = gensites.SHAPE_BYTE.get(shape)
        check(want is not None,
              f"2. {name} declares a shape the handler emulates",
              f"shape {shape!r} is not in {sorted(gensites.SHAPE_BYTE)}")
        eq(sites[name]["first_byte"], want,
           f"2. {name} begins with shape {shape!r}'s own byte "
           f"(0x{want:02X})" if want else f"2. {name} has a known shape")

    # §1: the checked-in header must BE what the generator produces. A hand-edited
    # sites.h is the split the ruling refuses, and it would be invisible otherwise.
    hdr = os.path.join(HERE, "sites.h")
    if os.path.isfile(hdr):
        want = gensites.emit(sites, offs, _coffs, path)
        got = open(hdr, encoding="utf-8").read()
        check(got.replace("\r\n", "\n") == want.replace("\r\n", "\n"),
              "1. the checked-in sites.h is exactly what gensites.py emits",
              "it is not -- someone edited the generated header, which is the "
              "two-homes split PLAN.md §7 Q12(a) refuses")
    else:
        LEDGER.skip("1. sites.h is in sync", "sites.h not generated yet")


# ---------------------------------------------------------------- §3
def section_3():
    """The provenance rules refuse a row that drops its conditions.

    THE POINT OF PUTTING THE ADDRESSES IN TOML (Q12(a)) is that `content.py`
    enforces this automatically. If it does not, the ruling bought nothing and the
    rows may as well have been #defines.
    """
    import content as C
    good = {
        "hook_site": {"x": {"va": 1, "rva": 1, "first_byte": 0x55, "provenance": {
            "source": "client-table",
            "extractor": "toolkit/clientscan/codescan.py",
            "build": 38797, "verified": "y"}}}}
    try:
        C.load_mapping(good) if hasattr(C, "load_mapping") else None
    except Exception:
        pass

    def refuses(prov, why):
        row = {"va": 1, "provenance": dict(prov)}
        try:
            C._check_provenance("hook_site", "x", row)
            return False
        except Exception:
            return True

    base = {"source": "client-table",
            "extractor": "toolkit/clientscan/codescan.py",
            "build": 38797, "verified": "y"}
    check(not refuses(base, ""), "3. a well-formed client-table row LOADS",
          "if this fails the other three below prove nothing")
    no_build = {k: v for k, v in base.items() if k != "build"}
    check(refuses(no_build, ""), "3. a client-table row with NO BUILD is refused",
          "NEEDS_BUILD must cover hook_site rows -- every address is build-specific")
    no_ex = {k: v for k, v in base.items() if k != "extractor"}
    check(refuses(no_ex, ""), "3. a row with NO EXTRACTOR is refused")
    ghost = dict(base, extractor="toolkit/clientscan/does_not_exist.py")
    check(refuses(ghost, ""),
          "3. a row naming an extractor that is NOT IN THE REPO is refused",
          "the gate's condition is that the extractor regenerates the row here")


# ---------------------------------------------------------------- §4, §5
REC_N = 14          # scalar fields, must match readhook.FIELDS
def _synth(recs, sites_hits, base=0x00400000, ver=None):
    """A capture file exactly as movehook.c writes one.

    BUILT FROM THE LAYOUT SPEC, not from a hand-kept field order. The first version
    of this walked `FIELDS` and then appended the point blocks, which is the very
    shape that let v3's `have_pts` drift out of position between the C and the
    reader -- a fixture that encodes the layout a SECOND time can agree with a wrong
    reader and prove nothing. Walking `readhook._LAYOUTS[ver]` means the fixture and
    the parser share one description, and §11 checks that description against the C.
    """
    import readhook
    ver = ver or max(readhook._LAYOUTS)
    spec = readhook._LAYOUTS[ver]
    fmt = "<" + "I" * sum(c for _n, c in spec)
    out = bytearray()
    out += b"MVHK"
    out += struct.pack("<IIIII", ver, base, len(sites_hits),
                       struct.calcsize(fmt), len(recs))
    for rva, hits in sites_hits:
        out += struct.pack("<II", rva, hits)
    for r in recs:
        r = dict(r)
        # `tick` is the DLL's commit flag; a fixture leaving it 0 is an UNCOMMITTED
        # record and readhook drops it. A test wanting that path sets it explicitly.
        r.setdefault("tick", 1000 + r.get("seq", 0))
        vals = []
        for name, count in spec:
            v = r.get(name, 0 if count == 1 else (0,) * count)
            vals.extend([v] if count == 1 else list(v))
        out += struct.pack(fmt, *vals)
    return bytes(out)


def _fl(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def section_4_5(tmp):
    import readhook

    # sites in gensites' order (sorted by key): agtrack, bake, setter, teleport
    names = ["agtrack", "bake", "setter", "teleport"]
    BAKE, TELE = 1, 3
    recs = [
        # three bakes: two hard arrivals from the setter, one glide from the solver
        {"seq": 0, "site": BAKE, "retaddr": 0x00602AD8, "arg2": 0, "have_agent": 1,
         "flags": 0x00020000, "id": 7},
        {"seq": 1, "site": BAKE, "retaddr": 0x00602AD8, "arg2": 0, "have_agent": 1,
         "flags": 0x00020000, "id": 7},
        {"seq": 2, "site": BAKE, "retaddr": 0x0060193B, "arg2": 1, "have_agent": 1,
         "flags": 0x00060000, "id": 7},
        # one teleport, bit 18 CLEAR, body 300 units from its target
        {"seq": 3, "site": TELE, "retaddr": 0x0060032E, "have_agent": 1,
         "flags": 0x00020000, "id": 7,
         "point": (_fl(0.0), _fl(0.0), 0, 0),
         "target": (_fl(300.0), _fl(0.0), 0, 0)},
    ]
    blob = _synth(recs, [(0x205FC0, 0), (0x1FE950, 3), (0x202A40, 2), (0x2020B0, 1)])
    path = os.path.join(tmp, "movehook.bin")
    with open(path, "wb") as fh:
        fh.write(blob)

    cap = readhook.Capture(path)
    eq(cap.stored, 4, "4. every record round-trips")
    eq(getattr(cap, "partial", -1), 0, "4. and none is flagged uncommitted")
    eq(cap.base, 0x00400000, "4. the image base round-trips")
    eq(len(cap.sites), 4, "4. the per-site hit table round-trips")
    eq(cap.sites[1]["hits"], 3, "4. a site's hit count round-trips")
    eq(cap.recs[2]["arg2"], 1, "4. arg2 -- the isWaypoint the whole arc turns on")
    eq(cap.recs[2]["retaddr"], 0x0060193B, "4. the return address round-trips")
    eq(cap.recs[3]["flags"] & (1 << 18), 0, "4. bit 18 reads CLEAR on the teleport")

    # BACKWARD COMPATIBILITY, and it is not hypothetical: run 1's capture
    # (2026-08-27 Ascalon, the arc's only live evidence) is v1, and a reader that
    # orphaned it would have destroyed the thing the instrument was built to get.
    v1 = _synth([{"seq": 0, "tick": 999, "site": 0, "retaddr": 0x00602AD8}],
                [(0x1FE950, 1)], ver=1)
    v1path = os.path.join(tmp, "v1.bin")
    with open(v1path, "wb") as fh:
        fh.write(v1)
    v1cap = readhook.Capture(v1path)
    eq(v1cap.version, 1, "4. a v1 capture still parses after the record grew twice")
    eq(v1cap.stored, 1, "4. and its records survive the version bumps")
    check("arg4" not in v1cap.recs[0],
          "4. and a v1 record does NOT sprout the fields it never carried",
          "reading later fields out of a v1 record would invent data")
    check("vel" not in v1cap.recs[0],
          "4. nor v4's velocity",
          "a v1 record has no velocity; producing one would be fabrication")

    # THE COMMIT FLAG, in the direction that can fail. A partial record decodes as
    # a perfectly plausible real one -- all-zero reads as site 0, seq 0 -- so a
    # reader that does not check would COUNT it. Adversarial lane A3-F5.
    torn = list(recs) + [{"seq": 4, "site": BAKE, "tick": 0, "arg2": 1}]
    tpath = os.path.join(tmp, "torn.bin")
    with open(tpath, "wb") as fh:
        fh.write(_synth(torn, [(0x205FC0, 0), (0x1FE950, 4), (0x202A40, 2),
                               (0x2020B0, 1)]))
    tcap = readhook.Capture(tpath)
    eq(tcap.stored, 4, "5. an UNCOMMITTED record (tick==0) is DROPPED, not counted")
    eq(tcap.partial, 1, "5. and it is reported rather than silently discarded")
    eq(tcap.claimed, 5, "5. while the claimed-slot count still shows it existed")

    # A capture with a control-A-FAILED sidecar must be REFUSED, not scored.
    with open(os.path.join(tmp, "movehook.txt"), "w", encoding="utf-8") as fh:
        fh.write("movehook\ncontrol A (our own int3): DID NOT FIRE -- dead\n"
                 "control B (client code): COULD NOT ARM\n")
    text, rc = readhook.report(readhook.Capture(path), names)
    check(rc != 0, "5. a capture whose control A failed is REFUSED, not scored",
          f"rc={rc}")
    check("REFUSING" in text, "5. and it says so in words")
    check("33.3%" not in text and "glide" not in text.split("REFUSING")[-1],
          "5. and no rate is printed after the refusal",
          "printing a rate under a dead handler is the exact failure this guards")

    # ...and with control A green it DOES score, or §5 proved nothing.
    with open(os.path.join(tmp, "movehook.txt"), "w", encoding="utf-8") as fh:
        fh.write("movehook\ncontrol A (our own int3): FIRED\n"
                 "control B (client code at 0x00401000): FIRED\n")
    text, rc = readhook.report(readhook.Capture(path), names)
    eq(rc, 0, "4. with controls green the same capture scores")
    check("33.3% glide" in text, "4. and the isWaypoint rate is 1 of 3",
          f"rate line missing from:\n{text}")
    check("0x0060193B" in text, "4. and the gliding bake's caller is named")
    check("300.0" in text or "300" in text,
          "4. and the teleport's body-to-target distance is measured")


# ---------------------------------------------------------------- §6, §7
def section_6_7(tmp):
    dll = os.path.join(HERE, "movehook.dll")
    ps = os.path.join(HERE, "build.ps1")
    if not os.path.isfile(dll):
        if not os.path.isfile(ps):
            LEDGER.skip("6-7. build and inject", "no build.ps1")
            return
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", ps, "movehook.c"], cwd=HERE,
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(dll):
            LEDGER.skip("6-7. build and inject",
                        f"no compiler / build failed: {r.stderr.strip()[:120]}")
            return
    blob = open(dll, "rb").read()
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    machine = struct.unpack_from("<H", blob, e + 4)[0]
    eq(machine, 0x014C, "6. the DLL is x86 -- Gw.exe is 32-bit and a 64-bit DLL "
                        "cannot be injected into it")
    check(os.path.getsize(dll) > 4096, "6. and it is not an empty stub")

    if not os.path.isfile(WOW64_CMD):
        LEDGER.skip("7. inject into a live 32-bit process", f"no {WOW64_CMD}")
        return
    try:
        import inject
    except Exception as ex:
        LEDGER.skip("7. inject into a live 32-bit process", f"cannot import: {ex}")
        return

    # §8 rides along on §7's injected run: the CONFIG FILE beside the DLL must
    # beat the environment, because that is the only channel `attach.py` has --
    # an injected DLL reads the TARGET's environment, not the injector's. The two
    # are set to different output directories on purpose, so whichever the DLL
    # actually honoured is visible in where the sidecar lands.
    outdir = os.path.join(tmp, "hookout")
    envdir = os.path.join(tmp, "hookout-env-loses")
    cfg = os.path.join(HERE, "movehook.cfg")
    cfg_saved = open(cfg, encoding="ascii").read() if os.path.isfile(cfg) else None
    with open(cfg, "w", encoding="ascii", newline="\n") as fh:
        fh.write("ms=1500\nout=" + outdir + "\n")
    env = dict(os.environ, RURIK_MOVEHOOK_OUT=envdir, RURIK_MOVEHOOK_MS="600000")
    # A throwaway host that will sit still. STDIN MUST BE A HELD-OPEN PIPE, not
    # DEVNULL: `cmd /k` reads EOF from DEVNULL and exits within half a second, and
    # the injector then fails with a WOW64-looking `WinError 299` on the module
    # snapshot that reads exactly like a 64-bit-enumerating-a-32-bit-target bug.
    # MEASURED 2026-08-26: DEVNULL -> host dead at t=0.50s, never resolves; a held
    # pipe -> kernel32 resolves at t=0.25s. The error was about the corpse.
    proc = subprocess.Popen([WOW64_CMD, "/k", "rem movehook test host"],
                            env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=0x08000000)
    try:
        # Wait for the 32-bit side to finish loading rather than guessing a sleep.
        sys.path.insert(0, os.path.join(TOOLKIT, "harness"))
        import keytap
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                keytap.module_base(proc.pid, "KERNEL32.DLL")
                break
            except Exception:
                time.sleep(0.2)
        try:
            rc = inject.main([str(proc.pid), dll])
        except SystemExit as ex:
            LEDGER.skip("7. inject into a live 32-bit process",
                        f"injector refused: {ex}")
            return
        except Exception as ex:
            LEDGER.skip("7. inject into a live 32-bit process", f"inject raised: {ex}")
            return
        check(rc == 0, "7. the DLL injects into a live 32-bit process",
              f"inject.main returned {rc}")
        # control B samples for up to ~1 s, then the run is 1.5 s, then it writes.
        deadline = time.time() + 25
        side = os.path.join(outdir, "movehook.txt")
        while time.time() < deadline and not os.path.isfile(side):
            time.sleep(0.25)
        check(os.path.isfile(side),
              "7. and it writes its sidecar -- the run completed and disarmed",
              f"nothing at {side}")
        if not os.path.isfile(side):
            return
        text = open(side, encoding="utf-8", errors="replace").read()
        check("control A" in text and "FIRED" in text.split("control A", 1)[1]
              .split("\n", 1)[0],
              "7. CONTROL A FIRED inside a real injected process",
              f"sidecar said:\n{text}")
        # The whole point of using cmd.exe: the sites are ~2 MB into an image that
        # small, so none of them can arm. The DLL must survive that and say zero.
        check("hits 0" in text or "hits       0" in text or "hits 0\n" in text
              or all(f"hits {n}" not in text for n in range(1, 5)),
              "7. sites that could not arm report ZERO hits rather than crashing",
              f"sidecar said:\n{text}")
        check(proc.poll() is None,
              "7. and the host process is STILL ALIVE -- the hook did not kill it",
              "the host died, which is the failure mode that matters most")
        # THE .bin, WHICH THIS SECTION NEVER CHECKED. It asserted the .txt
        # sidecar and stopped -- and the .txt is the SUMMARY, while the .bin is
        # the data. MOVECODE R5 lost a whole 8-minute capture to a write that
        # never happened, and no test in this file would have caught it,
        # because none of them ever asked whether the capture exists.
        binfile = os.path.join(outdir, "movehook.bin")
        check(os.path.isfile(binfile),
              "7. AND THE CAPTURE ITSELF LANDS -- the .bin, not just the sidecar",
              f"nothing at {binfile}; a run whose summary exists and whose data "
              f"does not is exactly the R5 failure")
        if os.path.isfile(binfile):
            head = open(binfile, "rb").read(24)
            check(head[:4] == b"MVHK" and len(head) >= 24,
                  "7. and it is a v6 capture with a complete header",
                  f"first bytes {head[:8]!r}")
            check(not os.path.exists(binfile + ".part"),
                  "7. and no .part temp file is left behind -- the write is "
                  "atomic (write-then-rename), so a reader never sees a "
                  "half-flushed snapshot",
                  f"{binfile}.part still exists")
            # AND THE READER MUST ACCEPT IT. Magic plus a header length would
            # pass on a file readhook cannot parse; the writer was rewritten
            # from stdio to Win32 under this change, and "the bytes still mean
            # what readhook thinks" is the property that rewrite could break.
            try:
                import readhook as _rh
                cap_live = _rh.Capture(binfile)
                ok, why = True, f"{len(cap_live.recs)} records, v{cap_live.version}"
            except Exception as ex:                            # noqa: BLE001
                ok, why = False, f"readhook refused it: {ex}"
            check(ok, "7. and readhook.py parses what the DLL just wrote", why)
        # The status file, which is the channel that reports a FAILED write --
        # deliberately beside the DLL, because when the output path is the
        # broken thing it is the only place still writable.
        status = os.path.join(HERE, "movehook.status")
        check(os.path.isfile(status),
              "7. the DLL leaves a status file beside itself",
              f"nothing at {status}")
        if os.path.isfile(status):
            stext = open(status, encoding="ascii", errors="replace").read()
            check("bin writes that succeeded: 1" in stext
                  or "bin writes that succeeded: " in stext
                  and " 0\n" not in stext.split("bin writes that succeeded:")[1][:4],
                  "7. and it reports a write that actually succeeded",
                  f"status said:\n{stext}")
        check(not os.path.isdir(envdir),
              "8. the config FILE beat the environment for the output directory",
              f"the DLL wrote to the env's dir -- attach.py's only channel is the "
              f"file, so this landing in {envdir} means a live capture would "
              f"silently ignore --out and --minutes")
        check(os.path.isfile(side),
              "8. and the run honoured ms=1500 from the file rather than the "
              "env's 600000 -- it finished inside the deadline")
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        if cfg_saved is None:
            if os.path.isfile(cfg):
                os.remove(cfg)
        else:
            with open(cfg, "w", encoding="ascii", newline="\n") as fh:
                fh.write(cfg_saved)


# ---------------------------------------------------------------- §9
def section_9():
    """attach.py's build guard REFUSES a client whose bytes are not 0x55.

    WHY THIS IS THE MOST IMPORTANT GUARD IN THE DIRECTORY. `session.py --exe`
    defaults to the NEWEST build under `vault/run/` -- the `sorted()[-1]` trap this
    repo has hit three times in three files -- while every movehook address is
    38797. `gensites.py --check` reads the PINNED FILE, so it says OK regardless of
    which client is actually running: it is checking the wrong artifact to catch
    this. Arming a 38797 RVA in a 38833 image writes 0xCC into the middle of some
    unrelated instruction and kills the client with our patch in it.

    BOTH DIRECTIONS ARE EXERCISED, because a guard that only ever refuses is
    indistinguishable from one that is broken. `keytap` is monkeypatched so the
    'client' can be made to hold 0x55 everywhere (must ACCEPT) or one wrong byte
    (must REFUSE). A live positive control was tried first and only reached the
    'no Gw.exe module' path, which proves the weaker half.
    """
    try:
        import attach
        import keytap
    except Exception as ex:
        LEDGER.skip("9. the build guard", f"cannot import: {ex}")
        return

    real_base, real_read = keytap.module_base, keytap.read_at
    try:
        import gensites
        keytap.module_base = lambda pid, name: 0x00400000

        # A CORRECT CLIENT NOW SERVES TWO BYTES, and serving 0x55 everywhere is
        # a WRONG client since 2026-08-29 -- the four MapFindPath ret sites hold
        # 0xC3. This control is built from the rows' own shapes for the same
        # reason `nsites` below is derived: a literal here goes stale the moment
        # the site set changes, and a stale positive control fails in the
        # direction that looks like the feature is broken.
        _rows = gensites.rows()[0]
        byshape = {}
        for _n, _r in _rows.items():
            _shape = _r.get("shape", gensites.DEFAULT_SHAPE)
            byshape[0x00400000 + _r["rva"]] = gensites.SHAPE_BYTE[_shape]
        def _serve(pid, addr, n, _m=byshape):
            return bytes([_m.get(addr, 0x55)]) * n
        keytap.read_at = _serve
        bad, base = attach.verify_running_build(1234)
        check(bad == [], "9. a client holding each site's OWN shape byte is "
                         "ACCEPTED (0x55 at entries, 0xC3 at the ret sites)",
              f"refused a correct client: {bad}")
        eq(base, 0x00400000, "9. and the image base is reported")

        # AND THE OTHER DIRECTION, which is the one this file's own history
        # argues for: a client serving 0x55 at a NON-ENTRY site is a wrong
        # client and must be refused. Before the shape column this was the
        # accepted case. Counted over every shape whose byte is not 0x55 --
        # the ret sites (0xC3) and, since ANIMREF-RE, resume_arm (0x57
        # pushedi) -- so a new shape reddens the count rather than sliding
        # under a literal `== "ret"`.
        nnon55 = sum(1 for _r in _rows.values()
                     if gensites.SHAPE_BYTE[
                         _r.get("shape", gensites.DEFAULT_SHAPE)] != 0x55)
        if nnon55:
            keytap.read_at = lambda pid, addr, n: b"\x55" * n
            bad, _ = attach.verify_running_build(1234)
            check(len(bad) == nnon55,
                  "9. a client serving 0x55 at every non-entry site is "
                  "REFUSED (the ret sites need 0xC3; resume_arm needs 0x57)",
                  f"expected {nnon55} refusal(s), got {bad}")
            check(all(any(tok in b for tok in ("0xC3", "0x57")) for b in bad),
                  "9. and each refusal names the byte its SHAPE required",
                  f"{bad}")

        # One site wrong is enough: this is what a build bump looks like.
        wrong = {0x00400000 + 0x001FE950: b"\x8b"}
        keytap.read_at = lambda pid, addr, n: wrong.get(addr, _serve(pid, addr, n))
        bad, _ = attach.verify_running_build(1234)
        check(len(bad) == 1, "9. ONE wrong byte is enough to refuse the whole run",
              f"expected exactly one refusal, got {bad}")
        check(any("0x8B" in b for b in bad),
              "9. and the refusal names the byte it actually found",
              f"{bad}")

        # A read that fails is a refusal too, not an accept-by-default.
        keytap.read_at = lambda pid, addr, n: None
        bad, _ = attach.verify_running_build(1234)
        # Derived, not literal: this said `== 4` and went red the moment B3 added
        # five sites. A count that has to be edited whenever the thing it measures
        # grows is a tripwire for maintenance, not for defects.
        nsites = len(_rows)
        eq(len(bad), nsites,
           "9. EVERY unreadable site refuses rather than passing")
    finally:
        keytap.module_base, keytap.read_at = real_base, real_read


# ---------------------------------------------------------------- §10
def section_10(tmp):
    """pathdiff replays a v3 capture through the REAL Ascalon mesh.

    MOVECODE-B3's whole output is a verdict per query, and the two verdicts that
    matter (`OURS-FAILED`, `OFF-MESH`) are claims that OUR decode is wrong. A
    harness that cannot tell those apart from `BOTH-OK` would launder our own bugs
    into a clean bill of health, so both directions are exercised against real map
    data rather than a stub: a point pair the mesh really does connect must score
    BOTH-OK, and a goal a million units away must score OFF-MESH.

    Needs the vaulted archive; skips with its reason otherwise.
    """
    try:
        import gensites
        import pathdiff
        import readhook as rh
        from pathmap import PathingMap
    except Exception as ex:
        LEDGER.skip("10. the pathdiff replay", f"cannot import: {ex}")
        return
    try:
        rows, _offs, _coffs = gensites.rows()
        names = sorted(rows)
        if "mapfindpath" not in names:
            LEDGER.skip("10. the pathdiff replay", "no mapfindpath row")
            return
        pm = PathingMap.load(0x1B97D)
    except Exception as ex:
        LEDGER.skip("10. the pathdiff replay", f"needs the vaulted archive: {ex}")
        return

    check(len(pm.trapezoids) > 100, "10. Ascalon's mesh loaded",
          f"{len(pm.trapezoids)} trapezoid(s)")

    # (9826, 8077) is map 148's spawn, pinned in content/maps.toml as landing in
    # exactly 1 trapezoid -- so it is a known-good point, not a hopeful one.
    good = (9826.0, 8077.0, 9900.0, 8100.0)
    far = (9826.0, 8077.0, 1.0e6, 1.0e6)
    _rows, tally = pathdiff.score(pm, [good], 0)
    eq(tally["BOTH-OK"], 1, "10. a connected pair scores BOTH-OK")
    _rows, tally = pathdiff.score(pm, [far], 0)
    eq(tally["OFF-MESH"], 1, "10. a goal off the mesh scores OFF-MESH")
    check(tally["BOTH-OK"] == 0,
          "10. and does NOT quietly score as fine",
          "an off-mesh goal reading BOTH-OK would launder our own decode gaps")

    # And the whole path: a synthetic v3 capture must parse and replay.
    mi = names.index("mapfindpath")
    sites = [(rows[n]["rva"], 0) for n in names]

    def fl(x):
        return struct.unpack("<I", struct.pack("<f", x))[0]

    # Same single source of truth as the reader -- see _synth's docstring.
    blob = _synth([{"seq": 0, "tick": 1000, "site": mi, "retaddr": 0x00709000,
                    "have_pts": 3, "arg3": fl(64.0),
                    "pt_a": (fl(good[0]), fl(good[1]), 0, 0),
                    "pt_b": (fl(good[2]), fl(good[3]), 0, 0)}],
                  [(rows[n]["rva"], 0) for n in names])
    p = os.path.join(tmp, "v3.bin")
    with open(p, "wb") as fh:
        fh.write(blob)

    cap = rh.Capture(p)
    qs = pathdiff.queries(cap, rh.site_names(cap))
    eq(len(qs), 1, "10. a v3 capture yields its MapFindPath query")
    check(qs[0].src is not None and qs[0].dst is not None,
          "10. and the DEREFERENCED coordinates survive the round trip",
          "have_pts said both points were read; if they are None the v3 layout "
          "and the DLL disagree and every replay would be empty")
    eq(round(qs[0].src[0], 1), 9826.0, "10. and the `from` point is exact")
    eq(round(qs[0].rng, 1), 64.0, "10. and the float range argument decodes")


# ---------------------------------------------------------------- §11
def section_11():
    """The reader's CURRENT layout must match `rec_t` in movehook.c, FIELD BY FIELD.

    THE CHECK THE LENGTH TEST COULD NEVER BE, and it exists because the failure
    already happened. v3 was described in readhook.py as `scalars + [point, segment,
    target, pt_a, pt_b]` with `have_pts` appended to the scalars; movehook.c declares
    `have_pts` AFTER target[4]. Both spellings total 38 dwords, so `reclen` matched
    and the guard whose own message warns about "a record whose fields would silently
    shift" could not fire. Every point block read one dword late. `pathdiff` reported
    "no coordinates" on a capture that had them, and run 2's teleport figures came
    out plausible and wrong.

    A length check cannot catch a reorder. Parsing the struct can, so this does: the
    C is the source of truth and the Python table has to agree with it by NAME and by
    ORDER, not merely by size.
    """
    import re
    import readhook as rh
    src = os.path.join(HERE, "movehook.c")
    if not os.path.isfile(src):
        LEDGER.skip("11. reader layout vs rec_t", "no movehook.c")
        return
    text = open(src, encoding="utf-8", errors="replace").read()
    m = re.search(r"\}\s*rec_t\s*;", text)
    start = text.rfind("typedef struct", 0, m.start()) if m else -1
    if start < 0:
        LEDGER.skip("11. reader layout vs rec_t", "could not find rec_t")
        return
    body = text[start:m.start()]
    # Strip comments so a field name mentioned in prose cannot be picked up.
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    fields = []
    for decl in re.finditer(r"\bDWORD\s+([^;]+);", body):
        for part in decl.group(1).split(","):
            part = part.strip()
            am = re.match(r"^(\w+)\s*(?:\[\s*(\d+)\s*\])?$", part)
            if am:
                fields.append((am.group(1), int(am.group(2) or 1)))
    check(len(fields) > 10, "11. rec_t parsed out of movehook.c",
          f"got {len(fields)} field(s)")
    want = rh._LAYOUTS[max(rh._LAYOUTS)]
    eq([n for n, _c in fields], [n for n, _c in want],
       "11. the reader's newest layout has rec_t's fields IN ORDER")
    eq([c for _n, c in fields], [c for _n, c in want],
       "11. and every field's dword WIDTH matches")
    eq(sum(c for _n, c in fields) * 4, rh.REC_LEN,
       "11. and the sizes agree, which is the weaker check that missed the reorder")


# ---------------------------------------------------------------- §12
def section_12(tmp):
    """The world-copy census: two objects per id, and a non-agent that says so.

    THE DEFECT THIS IS AGAINST is not hypothetical -- it is how FINDINGS 1h.2 scored
    the warp rate. `WORLD_CREATE_AGENT` builds each agent in BOTH worlds, so ONE id
    names TWO objects; a trajectory filtered on `id == 1` crosses between two bodies
    that genuinely sit hundreds of units apart, and reports the crossing as a
    displacement. The census must therefore group on the OBJECT ADDRESS and must SAY
    when an id is ambiguous -- a census that silently merged them would read exactly
    as clean as a correct one.

    Both directions are exercised, because a warning that cannot stay quiet is as
    useless as one that cannot fire: a capture with one object per id must NOT raise
    the ambiguity warning.
    """
    import readhook as rh
    try:
        import gensites
        rows, _offs, _coffs = gensites.rows()
        names = sorted(rows)
    except Exception as ex:
        LEDGER.skip("12. the world-copy census", f"cannot read the rows: {ex}")
        return
    for need in ("setter", "reseed"):
        if need not in names:
            LEDGER.skip("12. the world-copy census", f"no {need} row")
            return
    sites = [(rows[n]["rva"], 0) for n in names]
    si, ri = names.index("setter"), names.index("reseed")
    A, B = 0x21E20128, 0x21E208D8          # two objects, one id -- the real shape

    # The tick spacing is deliberately WIDER than the declared legs. A real capture
    # runs for minutes and its legs last seconds; a fixture spaced 10 ms apart makes
    # every honest agent look like it declares a leg longer than the capture, and
    # would have forced the non-agent guard to be loosened to accommodate the
    # fixture rather than the client.
    def rec(i, site, ecx, x, ptime, stop, **kw):
        r = {"seq": i, "tick": 1000 + i * 2000, "site": site, "ecx": ecx,
             "have_agent": 1, "id": 1, "ptime": ptime, "stop": stop,
             "point": (_fl(x), _fl(0.0), 0, 0), "vel": (_fl(288.0), _fl(0.0))}
        r.update(kw)
        return r

    # A walks; B is the sync copy, named as such by being reseed's arg1.
    recs = [rec(0, si, A, 0.0, 1000, 2000),
            rec(1, si, A, 288.0, 2000, 3000),
            rec(2, si, B, 0.0, 1000, 2000),
            rec(3, ri, A, 288.0, 2000, 3000,
                arg1=B, have_src=1, src_id=1, src_ptime=1000,
                src_point=(_fl(0.0), _fl(0.0), 0, 0))]
    p = os.path.join(tmp, "worlds.bin")
    with open(p, "wb") as fh:
        fh.write(_synth(recs, sites))
    cap = rh.Capture(p)
    txt = rh._worlds(cap, rh.site_names(cap))

    check(f"0x{A:08X}" in txt and f"0x{B:08X}" in txt,
          "12. both world copies are listed by ADDRESS",
          "an id-keyed census would show one row and hide the split")
    check("WORLD_SYNC" in txt,
          "12. and the sync copy is NAMED from reseed's source argument",
          "which side is authoritative must be read off the record, not assumed")
    check("MORE THAN ONE object" in txt,
          "12. and the ambiguous id RAISES the warning",
          "this is the warning whose absence let 1h.2 score two bodies as one")

    # The other direction: one object per id must stay quiet.
    p2 = os.path.join(tmp, "oneworld.bin")
    with open(p2, "wb") as fh:
        fh.write(_synth([rec(0, si, A, 0.0, 1000, 2000),
                         rec(1, si, A, 288.0, 2000, 3000)], sites))
    txt2 = rh._worlds(rh.Capture(p2), names)
    check("MORE THAN ONE object" not in txt2,
          "12. and a capture with ONE object per id does NOT warn",
          "a warning that always fires carries no information")

    # THE NON-AGENT GUARD. Compared against the capture's own wall span, never a
    # literal -- a literal is what goes stale. `snaptest`'s ecx produced 70 such
    # records in run 5 and they read as a 7,197 u desync.
    p3 = os.path.join(tmp, "notagent.bin")
    with open(p3, "wb") as fh:
        fh.write(_synth([rec(0, si, A, 0.0, 1000, 2000),
                         rec(1, si, 0x060C9B6C, 0.0, 12, 101489588,
                             id=574588536)], sites))
    txt3 = rh._worlds(rh.Capture(p3), names)
    check("NOT AN AGENT" in txt3,
          "12. a leg longer than the whole capture is called out as NOT AN AGENT",
          "a register being SAVED does not make it `this`")
    check("NOT AN AGENT" not in txt,
          "12. and a real agent is NOT flagged by that guard",
          "a guard that fires on everything would have to be ignored")


# ---------------------------------------------------------------- §13
def section_13(tmp):
    """The DISPLACEMENT count -- the number MOVECODE-K1 is refuted by.

    A reseed that FIRES is not a warp: run 5 had 14 reseeds and 2 displacements.
    Counting reseeds alone would score a candidate that fires less but warps more as
    an improvement, which is how four of the five dead candidates in authsrv's
    graveyard flattered themselves. So the readout has to separate the two, and the
    separation must be exercised in BOTH directions -- a counter that can only go up
    is not a counter.

    The signature needs no threshold: a WALK advances both m_point and the +0x58
    stamp saying when m_point was valid; a DISPLACEMENT moves the point with the
    stamp standing still.
    """
    import readhook as rh
    try:
        import gensites
        rows, _offs, _coffs = gensites.rows()
        names = sorted(rows)
    except Exception as ex:
        LEDGER.skip("13. the displacement count", f"cannot read the rows: {ex}")
        return
    for need in ("setter", "reseed"):
        if need not in names:
            LEDGER.skip("13. the displacement count", f"no {need} row")
            return
    sites = [(rows[n]["rva"], 0) for n in names]
    si, ri = names.index("setter"), names.index("reseed")
    A = 0x21E20128

    def rec(i, site, x, ptime, stop):
        return {"seq": i, "tick": 1000 + i * 2000, "site": site, "ecx": A,
                "have_agent": 1, "id": 1, "ptime": ptime, "stop": stop,
                "point": (_fl(x), _fl(0.0), 0, 0),
                "vel": (_fl(288.0), _fl(0.0))}

    # A WALK: the point moves and the stamp moves with it. Must NOT count.
    p = os.path.join(tmp, "walk.bin")
    with open(p, "wb") as fh:
        fh.write(_synth([rec(0, ri, 0.0, 1000, 4000),
                         rec(1, si, 288.0, 2000, 4000)], sites))
    txt, _rc = rh.report(rh.Capture(p), rh.site_names(rh.Capture(p)))
    check("STANDING STILL: 0" in txt,
          "13. a WALK (point and stamp both advance) is NOT a displacement",
          "if this counted, every ordinary leg would read as a warp")

    # A DISPLACEMENT after a reseed: the point moves, the stamp does not.
    p2 = os.path.join(tmp, "warp.bin")
    with open(p2, "wb") as fh:
        fh.write(_synth([rec(0, ri, 0.0, 1000, 4000),
                         rec(1, si, 691.0, 1000, 4000)], sites))
    cap2 = rh.Capture(p2)
    txt2, _rc = rh.report(cap2, rh.site_names(cap2))
    check("STANDING STILL: 1" in txt2,
          "13. a point that moves with the stamp FROZEN is a displacement",
          "this is the exact signature of run 5's two real warps")
    check("after reseed" in txt2,
          "13. and it is attributed to the RESEED that preceded it",
          "a displacement after a teleport is a different event -- run 5 had 10 "
          "displacements and only 2 followed a reseed")
    check("largest 691 u" in txt2,
          "13. and the MAGNITUDE leads, not the attribution",
          "MOVECODE-K1's arm A printed `following a RESEED: 0` and read as clean "
          "while the operator watched the character warp to spawn twice -- both "
          "warps went through the teleport arm, so they were counted and then "
          "buried under a subcount that happened to be zero")

    # Sub-unit noise must not count: the guard is > 1.0 u.
    p3 = os.path.join(tmp, "noise.bin")
    with open(p3, "wb") as fh:
        fh.write(_synth([rec(0, ri, 0.0, 1000, 4000),
                         rec(1, si, 0.5, 1000, 4000)], sites))
    cap3 = rh.Capture(p3)
    txt3, _rc = rh.report(cap3, rh.site_names(cap3))
    check("STANDING STILL: 0" in txt3,
          "13. and sub-unit float noise does NOT count as a displacement",
          "two reads of a parked agent differ in the low bits")


def section_14(tmp):
    """The 2026-08-28 sites and the v6 fields -- and the refusal that shaped them.

    FINDINGS 1s.9 asked for four hook sites and named five addresses. FOUR OF THE
    FIVE ARE NOT FUNCTION ENTRIES -- 0x00606009 is a `je`, 0x00605634 a `cmp`,
    0x00605683 a `pop esi`, and 0x005FCAA0 a `call` (the ResyncAllAsync THUNK, not
    its body) -- so `gensites` would have refused all four at generation time under
    PLAN.md 7 Q12(d), which requires one emulation shape.

    So the FIRST thing this section does is prove that refusal FIRES, using the
    real address the record proposed rather than an invented one. 2 checks every
    site's byte IS 0x55; that is the positive side and it cannot show the gate
    works. A gate nothing has ever tripped is a gate nobody has tested.

    What replaced those three refused addresses is not a relaxed rule -- it is that
    each wanted a VALUE the existing entry hooks already reach:

      the facing-9 early-out  both operands sit on snaptest's arg2, which the
                              snaptest row ALREADY dereferences, and one of them
                              (m_timeStopMovement) was already captured. One new
                              offset finished it.
      the AgTrack fence       the operand of agtrack's own branch, computable at
                              its entry from ecx and arg1.
      ResyncAllAsync          0x00605E40, the body the thunk jumps to.
    """
    import readhook as rh
    try:
        import gensites
        rows, offs, _coffs = gensites.rows()
        names = sorted(rows)
    except Exception as ex:
        LEDGER.skip("14. the 2026-08-28 sites", f"cannot read the rows: {ex}")
        return

    for need in ("resync", "stepclear", "agtrack", "snaptest"):
        eq(need in names, True, f"14. the `{need}` row is present")

    # MOVECODE-R3: the SetPosition row. FINDINGS §1t.8 asked for TWO sites,
    # 0x00604A50 and 0x00606394, and NEITHER can be hooked -- both are
    # `e8 call 0x602b20`, and gensites refuses anything whose first byte is not
    # 0x55. Hooking the CALLEE instead names whichever of its seven callers
    # fired, from the return address the record already carries, so one row is a
    # superset of the request. These checks pin the two things that would break
    # it SILENTLY: the row disappearing, and arg1 no longer being dereferenced --
    # in which case the landing position stops being captured and every warp
    # measurement quietly reverts to inferring it from the next record.
    eq("setposition" in names, True, "14. the `setposition` row is present")
    if "setposition" in rows:
        sp = rows["setposition"]
        eq(sp.get("va"), 0x00602B20,
           "14. setposition is the CALLEE 0x00602B20, not a call site")
        eq(sp.get("deref_agent"), True,
           "14. and ecx is dereferenced as the agent -- 0x00602B29 `mov ebx,ecx`")
        eq(sp.get("deref_arg_a"), 1,
           "14. and arg1 IS dereferenced -- without it the installed point is "
           "not captured and the landing reverts to an inference")
        # The row's whole justification is that the two addresses §1t.8 named are
        # among this function's callers. If a future edit drops them, the row
        # still generates and the reasoning is gone. Checked against
        # `why_hooked` rather than the provenance block because `gensites.rows()`
        # returns only the site fields -- the nested [.provenance] table is
        # `content.py`'s business and never reaches here. A first draft asserted
        # on `provenance.verified` and went red for exactly that reason, which is
        # the check catching the test's own wrong operand rather than the row's.
        why = sp.get("why_hooked", "") or ""
        for addr in ("0x00604A50", "0x00606394"):
            check(addr in why,
                  f"14. setposition's `why_hooked` still names {addr}",
                  "the row exists BECAUSE these two call sites cannot be hooked "
                  "and this callee reaches both; drop them and the row looks "
                  "arbitrary")

    # THE OFF-BY-FIVE, pinned. readhook's SetPosition caller table is keyed on
    # RETURN addresses, because that is what the record stores -- and every one of
    # the seven callers is a 5-byte `call rel32`. The orchestrator's first R3
    # analysis keyed on the CALL addresses, which is how --xrefs prints them and
    # how both FINDINGS and content/movecode.toml cite them, and every known
    # caller came back "UNKNOWN". A future edit "correcting" the table to the
    # cited addresses would silently do the same thing, so the relationship is
    # asserted here rather than trusted to a comment.
    CALLS = (0x00602369, 0x00604A50, 0x00606394, 0x005FDAE5,
             0x005FDB49, 0x005FF74B, 0x006028FF)
    tbl = getattr(rh, "SP_CALLERS", None)
    if tbl is None:
        # It lives inside report(); read it off the source rather than skipping,
        # because a skip here would hide the very drift this check exists for.
        src = open(os.path.join(HERE, "readhook.py"), encoding="utf-8").read()
        keys = set()
        for line in src.splitlines():
            ls = line.strip()
            if ls.startswith("0x00") and ":" in ls and '"' in ls:
                try:
                    keys.add(int(ls.split(":")[0], 16))
                except ValueError:
                    pass
    else:
        keys = set(tbl)
    eq(len(keys & {c + 5 for c in CALLS}), 7,
       "14. the SetPosition caller table is keyed on RETURN addresses (call+5)")
    check(not (keys & set(CALLS)),
          "14. and NOT on the call addresses --xrefs prints",
          f"call addresses present as keys: "
          f"{sorted(hex(v) for v in keys & set(CALLS))} -- that is the off-by-five "
          "that reported reseed as an unknown caller on the first R3 readout")

    # THE STALE-DLL GUARD, both directions, on throwaway files. It refused a
    # perfectly current DLL in the MIDDLE OF A LIVE RUN on 2026-08-28, twice over,
    # because it compared MTIMES on a generated, git-managed header: `gensites.py`
    # rewrote a byte-identical sites.h (which RUN-R4.md's preconditions ask the
    # operator to do) and git normalised its line endings on commit. Neither
    # changed a byte. It is content-based now, and both arms are exercised here
    # because a guard that cannot refuse is as bad as one that always does.
    import attach as _at
    sub = os.path.join(tmp, "stalecheck")
    os.makedirs(sub, exist_ok=True)
    hdr_p = os.path.join(sub, "sites.h")
    dll_p = os.path.join(sub, "movehook.dll")
    stamp_p = os.path.join(sub, "movehook.sites.sha256")
    with open(hdr_p, "w", encoding="utf-8") as fh:
        fh.write("/* pretend header */\n")
    with open(dll_p, "wb") as fh:
        fh.write(b"MZ")
    import hashlib
    good = hashlib.sha256(open(hdr_p, "rb").read()).hexdigest()
    with open(stamp_p, "w", encoding="ascii") as fh:
        fh.write(good)

    st, why = _at.sites_stale(sub, dll_p)
    check(st is False, "9. a matching build stamp passes",
          f"{why}")
    # ...and it passes even when the header is NEWER, which is the false alarm.
    os.utime(hdr_p, (time.time() + 3600, time.time() + 3600))
    st, why = _at.sites_stale(sub, dll_p)
    check(st is False,
          "9. and STILL passes when sites.h is newer but byte-identical",
          "this is the exact false alarm that stopped a live run: an untouched "
          "header with a bumped mtime")
    # A real change must still refuse.
    with open(hdr_p, "w", encoding="utf-8") as fh:
        fh.write("/* pretend header, EDITED */\n")
    st, why = _at.sites_stale(sub, dll_p)
    check(st is True, "9. CONTROL: an actually-changed sites.h is REFUSED",
          "the guard exists for a header regenerated while the old DLL was locked "
          "by a running client, and it must still catch that")
    check(any("DIFFERENT" in ln for ln in why),
          "9. and it says the header differs, not that it is older",
          f"{why}")
    # With no stamp at all it must fall back to mtime rather than passing blindly.
    os.remove(stamp_p)
    os.utime(hdr_p, (time.time() + 3600, time.time() + 3600))
    st, why = _at.sites_stale(sub, dll_p)
    check(st is True, "9. with NO stamp it falls back to mtime and still refuses",
          "a DLL built before stamping existed must not be silently trusted")
    check(any("no build stamp" in ln for ln in why),
          "9. and says so, because that arm CAN be a false alarm",
          f"{why}")

    # MOVECODE-R4: the tick, and the STRIDE it forced into existence.
    eq("tick" in names, True, "14. the `tick` row is present")
    if "tick" in rows:
        tk = rows["tick"]
        eq(tk.get("va"), 0x00600140, "14. tick is the movement tick 0x00600140")
        # NOT strided, and the history matters more than the value. It was 64,
        # sized for a per-frame reading of this site that RUN A REFUTED at 0.62
        # hits/s -- so 1-in-64 stored 2 records of 97 and cost R4-P2 most of its
        # evidence. The stride MECHANISM is kept (a genuine per-frame site would
        # need it, and sec.1u.6 still wants one) but NO SITE USES IT today; its
        # logic is covered by the arithmetic mirror below and its crash mode by
        # sec.15, neither of which needs a strided row.
        eq(int(tk.get("stride") or 0), 0,
           "14. and it is NOT strided -- the per-frame premise was refuted at "
           "0.62 hits/s, and 1-in-64 was discarding 95 of 97 records")

    # THE GUARD THAT MATTERS MORE THAN THE ROW. A stride on a site whose RECORDS
    # are counted turns every rate in this arc into a silent undercount -- the
    # displacement census, the reseed split, P1a's bake rate and the gate-3 filter
    # all count stored records. `hits` is unaffected by the stride, `stored` is
    # not, and nothing in the file would announce the change. So the sites whose
    # records are counted are named here and required to be unstrided.
    #
    # THE FOUR RET SITES ARE HERE FOR A SECOND REASON ON TOP OF THAT ONE: a
    # stride on either half of the MapFindPath pair DECIMATES THE PAIRING. The
    # entry and the ret are joined on (tid, esp), so striding one side drops the
    # partner of N-1 of every N invocations and the pairing rate collapses --
    # while `hits` stays whole on both sides and nothing in the readout would
    # say the answers had been unpaired rather than absent.
    COUNTED = ("bake", "teleport", "setter", "reseed", "resync", "snaptest",
               "stepclear", "setposition", "agtrack", "mapfindpath",
               "mapfindpath_ret1", "mapfindpath_ret2", "mapfindpath_ret3",
               "mapfindpath_ret4",
               "chcli_point", "chcli_dir", "chcli_advance", "agapi_setdest")
    for nm in COUNTED:
        if nm in rows:
            check(int(rows[nm].get("stride") or 0) in (0, 1),
                  f"14. `{nm}` is NOT strided -- its records are counted",
                  f"stride {rows[nm].get('stride')} would make every count over "
                  f"this site a 1-in-N sample while `hits` stayed whole, and no "
                  f"reader would say so")

    # THE STRIDE ARITHMETIC, mirrored from movehook.c's own expression so the
    # two properties it is relied on for are pinned rather than assumed:
    # the FIRST occurrence is always stored (a site that fired once still appears
    # in the capture), and storage is evenly spaced thereafter.
    def _stores(nth, stride):
        return not (stride > 1 and ((nth - 1) % stride) != 0)
    eq([n for n in range(1, 12) if _stores(n, 4)], [1, 5, 9],
       "14. stride 4 stores occurrences 1, 5, 9 -- first hit always kept")
    eq([n for n in range(1, 6) if _stores(n, 1)], [1, 2, 3, 4, 5],
       "14. stride 1 stores everything")
    eq([n for n in range(1, 6) if _stores(n, 0)], [1, 2, 3, 4, 5],
       "14. and stride 0 means unset, not `store nothing`")
    src_c = open(os.path.join(HERE, "movehook.c"), encoding="utf-8").read()
    check("(nth - 1) % SITES[i].stride" in src_c,
          "14. and movehook.c uses that exact expression",
          "the C and this mirror must not drift; `nth % stride` would drop the "
          "first hit and a site that fired once would vanish from the capture")

    # The two offsets the early-out and the world census need.
    eq(offs.get("facing", {}).get("offset"), 0xC4,
       "14. `facing` is +0xC4 -- snaptest reads it at 0x0060563A")
    eq(offs.get("world", {}).get("offset"), 0x24,
       "14. `world` is +0x24 -- agtrack reads it at 0x00605FD1")

    # agtrack must now deref arg1 as an agent AND declare the fence, or the run
    # answers neither of the two questions it was re-armed for.
    eq(rows["agtrack"].get("deref_agent_arg"), 1,
       "14. agtrack dereferences arg1 as an agent (id at +0x10, world at +0x24)")
    eq(bool(rows["agtrack"].get("deref_fence")), True,
       "14. and declares the fence read")
    eq(bool(rows["snaptest"].get("deref_fence")), False,
       "14. while a row that does NOT declare it stays off -- the flag is per row")

    # THE REFUSAL, on the real proposed addresses. Each is a genuine mid-function
    # byte in the pinned image, so this is the case that actually arose.
    # The real first byte at each address, re-read from the pinned image and
    # quoted here so the refusal is exercised on the actual case, not a fiction.
    PROPOSED = ((0x00606009, 0x0F, "the AgTrack fence branch, a `je`"),
                (0x00605634, 0x83, "the facing-9 compare, a `cmp`"),
                (0x00605683, 0x5E, "the facing-9 return tail, a `pop esi`"),
                (0x005FCAA0, 0xE8, "the ResyncAllAsync THUNK, a `call`"))
    try:
        # CONTROL FIRST: the row these are cloned from must be ACCEPTED, or every
        # refusal below is about the cloning rather than about the address.
        ctl_bad, _p = gensites.verify({"resync": dict(rows["resync"])})
    except Exception as ex:
        LEDGER.skip("14. the non-entry refusal", f"{NO_CLIENT}: {ex}")
    else:
        eq(ctl_bad, [],
           "14. CONTROL: the row these are cloned from is ACCEPTED at its real "
           "address")
        for va, real, why in PROPOSED:
            # (a) the row as anyone would first write it -- address changed,
            #     first_byte left at 0x55. Caught by the byte-mismatch guard.
            naive = {"x": dict(rows["resync"])}
            naive["x"]["va"] = va
            naive["x"]["rva"] = va - 0x00400000
            bad_a, _ = gensites.verify(naive)
            check(bool(bad_a),
                  f"14. gensites REFUSES 0x{va:08X} -- {why}",
                  "a site table that accepted a mid-function byte would arm a "
                  "breakpoint the handler cannot re-emulate; the client would die "
                  "inside our own vectored handler with no attribution")
            # (b) the row `fixed` to match reality -- first_byte set to the byte
            #     that is actually there. This is the one that matters: it is what
            #     a session does after reading the refusal in (a), and the ruling
            #     has to survive it. Caught by the EXPECT_FIRST_BYTE guard.
            fixed = {"x": dict(naive["x"])}
            fixed["x"]["first_byte"] = real
            bad_b, _ = gensites.verify(fixed)
            check(bool(bad_b),
                  f"14. and still refuses 0x{va:08X} with first_byte `fixed` to "
                  f"0x{real:02X}",
                  "PLAN.md 7 Q12(d) is a constraint on the HANDLER, not a typo in "
                  "the row -- matching the row to the binary does not make a `je` "
                  "emulable as a `push ebp`")

    # v6 round-trip. A field that does not survive the write/read is a field the
    # run will not have, and it would look exactly like a client that never set it.
    sites = [(rows[n]["rva"], 0) for n in names]
    ai, si = names.index("agtrack"), names.index("snaptest")
    p = os.path.join(tmp, "v6.bin")
    with open(p, "wb") as fh:
        fh.write(_synth([
            # agtrack: fence READ and shut, on a world-0 (sync) agent.
            {"seq": 0, "tick": 1000, "site": ai, "ecx": 0x0AAA0000,
             "have_src": 1, "src_id": 1, "src_world": 0, "src_facing": 3,
             "have_fence": 1, "fence": 0},
            # agtrack: fence read and OPEN.
            {"seq": 1, "tick": 2000, "site": ai, "ecx": 0x0AAA0000,
             "have_src": 1, "src_id": 1, "src_world": 0, "src_facing": 3,
             "have_fence": 1, "fence": 1},
            # snaptest on an agent in the facing-9 early-out: stop != 0, facing 9.
            {"seq": 2, "tick": 3000, "site": si, "ecx": 0x0BBB0000,
             "have_src": 1, "src_id": 1, "src_world": 0,
             "src_stop": 5000, "src_facing": 9},
            # BOTH reseed routes, so the gated/gateless split has something to
            # split. The retaddrs are the real ones; `_synth` bases the capture
            # at 0x00400000, so they go in already rebased.
            {"seq": 3, "tick": 4000, "site": names.index("reseed"),
             "ecx": 0x0CCC0000, "retaddr": 0x006060E7,
             "have_agent": 1, "id": 1, "world": 1},
            {"seq": 4, "tick": 5000, "site": names.index("reseed"),
             "ecx": 0x0CCC0000, "retaddr": 0x00605EF6,
             "have_agent": 1, "id": 1, "world": 1},
            # Gate 3 AND its other caller, so the filter has something to filter.
            {"seq": 5, "tick": 6000, "site": names.index("stepclear"),
             "ecx": 0x0DDD0000, "retaddr": 0x0060581E},
            {"seq": 6, "tick": 7000, "site": names.index("stepclear"),
             "ecx": 0x0DDD0000, "retaddr": 0x006007AE},
        ], sites))
    cap = rh.Capture(p)
    # The fixture is built at the WRITER's current version, so this tracks
    # `CURRENT_VER` rather than pinning a literal that goes red on every bump
    # -- the same reason §9's site count is derived. The v6-specific fields it
    # then asserts are still present, because versions only ever APPEND.
    eq(cap.version, rh.CURRENT_VER,
       "14. the capture declares the writer's current version")
    r0, r1, r2 = cap.recs[0], cap.recs[1], cap.recs[2]
    eq((r0["have_fence"], r0["fence"]), (1, 0),
       "14. a fence READ AS ZERO round-trips as read-and-zero")
    eq((r1["have_fence"], r1["fence"]), (1, 1),
       "14. and an open fence round-trips as open")
    eq(r0["src_world"], 0,
       "14. the world field survives -- WORLD_SYNC is the literal 0")
    eq(r2["src_facing"], rh.FACING_EARLY_OUT,
       "14. and the facing value the early-out tests survives")

    # THE DISTINCTION THAT IS THE WHOLE MEASUREMENT: a fence that could not be
    # read must not read as a fence that was zero. 1s.8 item 1's defect was
    # exactly this class -- a state that was never observed scored as a state.
    p2 = os.path.join(tmp, "v6-unread.bin")
    with open(p2, "wb") as fh:
        fh.write(_synth([{"seq": 0, "tick": 1000, "site": ai, "ecx": 0x0AAA0000,
                          "have_src": 1, "src_id": 1, "have_fence": 0,
                          "fence": 0}], sites))
    cap2 = rh.Capture(p2)
    eq(cap2.recs[0]["have_fence"], 0,
       "14. an UNREAD fence is distinguishable from a fence read as zero",
       )
    check(cap2.recs[0]["have_fence"] != cap.recs[0]["have_fence"],
          "14. and the two are not the same record",
          "if have_fence were dropped, `could not read` and `shut` would be one "
          "value and the fence count would be silently inflated")

    # A FIELD CAPTURED AND NEVER PRINTED IS A FIELD THE RUN DOES NOT HAVE, and
    # that is not hypothetical: v6 shipped with all six fields written correctly
    # and NO report section, so run R2's five registered predictions had to be
    # scored out of a scratchpad script while the readout said nothing about the
    # fence, the facing or the gate-3 filter. The answer was in the file and the
    # instrument was silent. Round-tripping the fields (above) cannot catch that
    # -- only asking the REPORT can.
    txt, _rc = rh.report(cap, rh.site_names(cap))
    for want, why in (("FENCE", "the fence census"),
                      ("RESEED ROUTES", "the gated/gateless split"),
                      ("FACING", "the pre-gate early-out"),
                      ("GATE 3", "gate 3 and its mandatory retaddr filter")):
        check(want in txt, f"14. the v6 report prints {why}",
              "the field round-trips but the readout is silent, which is how "
              "R2 came back needing a scratchpad script to score itself")
    # ...and the same report on a v5 capture must NOT print them, or a reader of
    # an old capture is shown a section built from fields it does not carry.
    p3 = os.path.join(tmp, "v5-quiet.bin")
    with open(p3, "wb") as fh:
        fh.write(_synth([{"seq": 0, "tick": 1000, "site": ai, "ecx": 0x0AAA0000}],
                        sites, ver=5))
    txt5, _rc5 = rh.report(rh.Capture(p3), names)
    check("FENCE" not in txt5 and "GATE 3" not in txt5,
          "14. CONTROL: a v5 capture prints NO v6 section",
          "a section built from absent fields would read as a measurement of "
          "zero rather than of nothing")


# ---------------------------------------------------------------- §15
def section_15():
    """The dispatch loop must reach its emulation on EVERY matched hit.

    THIS SECTION EXISTS BECAUSE THE CLIENT CRASHED. The stride added on
    2026-08-28 was written as `if (strided out) continue;` directly above the
    `push ebp` emulation whose own comment reads "this must happen on every hit
    -- a skipped prologue is a corrupted frame, not a missing sample". `continue`
    leaves the for-loop, so EIP never advanced past the 0xCC and the frame was
    never built; 63 of every 64 tick hits took that path and the client died with
    c0000005 within seconds of arming.

    Nothing in the suite could have caught it: §7 injects into a throwaway
    cmd.exe where every site FAILS TO ARM, which is deliberate and is exactly why
    the handler's hot path is never executed by a test. The property is
    structural, so it is checked structurally -- between the address match and
    the emulation there may be no `continue`, no `break`, and no `return` other
    than the emulation's own.
    """
    c_path = os.path.join(HERE, "movehook.c")
    if not os.path.isfile(c_path):
        LEDGER.skip("15. the dispatch loop", "movehook.c is not here")
        return
    src = open(c_path, encoding="utf-8").read()
    bad = _loop_escapes(src)
    check(bad == [], "15. no early exit between the site match and the emulation",
          f"found {bad} -- each one is a hit that never emulates its shape's "
          f"instruction, never advances EIP past the 0xCC, and crashes the client")

    # CONTROL: the check must catch the exact statement that crashed it.
    planted = src.replace(
        "        if (!(SITES[i].stride > 1u",
        "        if (SITES[i].stride > 1u) continue;\n        if (!(SITES[i].stride > 1u",
        1)
    check(planted != src, "15. CONTROL: the crashing form could be planted")
    check(_loop_escapes(planted) != [],
          "15. CONTROL: and planting it is DETECTED",
          "a checker that cannot find the bug it was written for is decoration")

    # ---- 15b: EVERY SHAPE ARM MUST ASSIGN Eip ---------------------------
    #
    # THE ESCAPE CHECK ABOVE CANNOT SEE THE BUG THIS ONE IS FOR. Since
    # 2026-08-29 the emulation is a two-armed branch on SITES[i].shape, and the
    # way to break it is not a `continue` -- it is an arm that falls through
    # without assigning c->Eip (a missing `else`, or a new shape added with no
    # arm). EIP then stays on the 0xCC and the site re-traps forever; at
    # 0x0070A0D4 the eleven bytes that follow are the compiler's own int3
    # padding, so the failure is not even loud. `_loop_escapes` scans for
    # continue/break/return and a missing else is none of those.
    #
    # So: count the arms and count the assignments, and require them equal.
    arms, assigns = _shape_arms(src)
    check(arms >= 2, "15b. the emulation dispatches on at least two shapes",
          f"found {arms} arm(s) -- if the ret shape was removed, remove this "
          f"check with it rather than letting it pass vacuously")
    check(arms == assigns,
          "15b. every shape arm assigns c->Eip",
          f"{arms} arm(s) but {assigns} assignment(s) to c->Eip -- an arm that "
          f"does not set EIP leaves it on the 0xCC and the site re-traps forever")

    # CONTROL, in the same posture as §15's: delete the else-arm's assignment
    # and prove the checker goes red.
    planted2 = src.replace("            c->Eip = a + 1;\n", "", 1)
    check(planted2 != src, "15b. CONTROL: the defective form could be planted")
    a2, s2 = _shape_arms(planted2)
    check(a2 != s2,
          "15b. CONTROL: and planting it is DETECTED",
          f"planted source reports {a2} arm(s) and {s2} assignment(s) -- the "
          f"checker cannot see the bug it exists for")


def _shape_arms(src):
    """(shape arms, c->Eip assignments) in the emulation block. See §15b.

    The block runs from the shape dispatch to the loop's own
    `return EXCEPTION_CONTINUE_EXECUTION;` -- anchored on the dispatch rather
    than on any one arm's text, so removing an arm's assignment (the bug) does
    not also move the window and hide itself.
    """
    import re
    try:
        i = src.index("if (SITES[i].shape == SHAPE_RET) {")
        j = src.index("return EXCEPTION_CONTINUE_EXECUTION;", i)
    except ValueError:
        return 0, 0
    body = re.sub(r"/\*.*?\*/", "", src[i:j], flags=re.S)
    # EVERY branch counts, nested ones included -- the ret arm's own
    # readable() fallback is an arm for this purpose, because it is a path a
    # hit can take and every path must leave EIP somewhere other than the
    # 0xCC. Counting only the top-level dispatch would let a fallback that
    # forgot its assignment pass. Currently 3 and 3: ret-ok, ret-fallback,
    # entry.
    arms = 1 + len(re.findall(r"\}\s*else\b", body))
    assigns = len(re.findall(r"c->Eip\s*=", body))
    return arms, assigns


def _loop_escapes(src):
    """[offending statements] between the address match and the emulation."""
    import re
    try:
        i = src.index("for (i = 0; i < NSITES; i++) {")
        j = src.index("c->Eip = a + 1;", i)
    except ValueError:
        return ["could not locate the dispatch loop or its emulation"]
    body = re.sub(r"/\*.*?\*/", "", src[i:j], flags=re.S)   # strip comments
    body = body[body.index("if (a != g_addr[i]) continue;")
                + len("if (a != g_addr[i]) continue;"):]
    out = []
    for line in body.splitlines():
        s = line.strip()
        if re.search(r"\b(continue|break)\s*;", s) or re.search(r"\breturn\b", s):
            out.append(s)
    return out


# ---------------------------------------------------------------- §16
def section_16(tmp):
    """DURABILITY: a run must not be able to end with nothing on disk.

    THIS SECTION EXISTS BECAUSE AN 8-MINUTE CAPTURE WAS LOST. MOVECODE R5,
    2026-08-28: the operator armed, played, ran `--stop`, and got no
    movehook.bin, no movehook.txt, and no output directory at all. The whole
    run had to be scored from the server log instead. Three defects behind it,
    and each gets a check here:

      * the DLL wrote EXACTLY ONCE, past the end of the poll loop, so any
        ending that loop did not reach discarded every record;
      * nothing was written when the process exited;
      * a failed write was SILENT -- fopen's NULL was dropped, so an unwritable
        path was indistinguishable from a run that captured nothing.

    The first two are checked structurally against the C source, because the
    behaviour needs a live client and a real crash to exercise; §7 covers the
    write path end to end in a real injected process. The third is checked
    against attach.py, which now refuses BEFORE spending a run.
    """
    src_path = os.path.join(HERE, "movehook.c")
    if not os.path.isfile(src_path):
        LEDGER.skip("16. durability", "movehook.c not beside the test")
        return
    src = open(src_path, encoding="utf-8", errors="replace").read()
    # Read the flush interval OUT OF THE SOURCE rather than restating it: a
    # test that hardcodes 15000 keeps passing after someone changes FLUSH_MS
    # and starts measuring a window that no longer exists.
    m_flush = re.search(r"#define\s+FLUSH_MS\s+(\d+)u?", src)
    FLUSH_MS_S = (int(m_flush.group(1)) / 1000.0) if m_flush else 15.0
    check(m_flush is not None, "16. movehook.c declares FLUSH_MS",
          "the flush interval has to be a named constant the test can read")

    # (a) the poll loop flushes on a timer.
    try:
        lo = src.index("while (waited < run_ms")
        hi = src.index("g_why =", lo)
        loop = src[lo:hi]
    except ValueError:
        loop = ""
    check("snapshot(" in loop,
          "16. the poll loop takes a periodic snapshot",
          "without it the only write is past the end of the loop, which is "
          "exactly how R5 lost 8 minutes of play")
    check("FLUSH_MS" in loop,
          "16. and it is on a bounded timer, not a guess",
          "the loss window has to be a named number")

    # (b) process exit writes.
    try:
        dm = src[src.index("BOOL WINAPI DllMain"):]
    except ValueError:
        dm = ""
    check("DLL_PROCESS_DETACH" in dm
          and ("write_bin(" in dm or "snapshot(" in dm),
          "16. DllMain writes the capture when the process EXITS",
          "a client that closes or crashes with a run armed must not take the "
          "records with it")
    check("g_final_written" in dm,
          "16. and it does NOT overwrite a completed capture with a short one",
          "the detach path must stand down once the worker's own final write "
          "has happened")

    # (c) the writer is Win32, because DllMain at shutdown cannot trust stdio.
    # The slice starts at `put`, not at `write_bin`: the WriteFile call lives in
    # that one-line helper, and slicing from write_bin alone made this check go
    # red against a function that is already pure Win32 -- a wrong OPERAND, not
    # a wrong claim, and the second time this arc has paid for one.
    try:
        wb = src[src.index("static int put(HANDLE"):src.index("#define FLUSH_SLACK")]
    except ValueError:
        wb = ""
    check("CreateFileA" in wb and "WriteFile" in wb,
          "16. the capture writer uses Win32, not CRT stdio",
          "it is called from DLL_PROCESS_DETACH, where the CRT may already be "
          "torn down and stdio can deadlock under the loader lock")
    check("fopen" not in wb and "fwrite" not in wb,
          "16. CONTROL: and no stdio slipped back into it",
          f"found stdio in write_bin:\n{wb[:400]}")
    check("MoveFileExA" in wb and ".part" in wb,
          "16. and the write is atomic (temp file, then rename)",
          "a snapshot interrupted mid-write must not replace a good capture "
          "with a truncated one")

    # (d) failures are reported rather than swallowed.
    check("g_werr" in src and "write_status" in src,
          "16. a failed write is RECORDED and reported",
          "R5's fopen returned NULL into a void; the error has to reach a human")
    try:
        ws = src[src.index("static void write_status"):]
        ws = ws[:ws.index("\n}")]
    except ValueError:
        ws = ""
    check("beside_dll" in ws,
          "16. and the status file sits BESIDE THE DLL, not in the output dir",
          "when the configured output path is the broken thing, writing the "
          "complaint into it reports nothing")

    # (e) attach.py refuses an unwritable output directory BEFORE injecting.
    try:
        import attach
    except Exception as ex:                                   # noqa: BLE001
        LEDGER.skip("16. attach.py pre-flight", f"cannot import: {ex}")
        return
    asrc = open(os.path.join(HERE, "attach.py"), encoding="utf-8").read()
    check("makedirs" in asrc and "REFUSING TO INJECT -- cannot write" in asrc,
          "16. attach.py proves the output path is writable before injecting",
          "eight minutes of the operator's play is worth two syscalls up front")
    # And --stop must WAIT for the artifact rather than announce it. The old
    # text promised the DLL 'will disarm and write within a second'; on R5 that
    # sentence was false and the operator believed it.
    stop_blk = asrc[asrc.index("if a.stop:"):asrc.index("if not os.path.isfile(DLL)")]
    check("NO CAPTURE APPEARED" in stop_blk,
          "16. --stop reports a MISSING capture instead of promising one",
          "an instrument that announces an artifact it has not seen is how a "
          "lost run goes unnoticed until the client is closed")
    check("os.path.getsize" in stop_blk or "getmtime" in stop_blk,
          "16. and it confirms the file by looking at it",
          "existence alone would pass on a stale file from a previous run")
    # --stop MUST look where the ARMED RUN is writing, which is the cfg's `out=`
    # and not this script's default. `attach.py --stop` with no --out is exactly
    # what the operator typed on R5; resolving that to the default vault dir
    # would report a MISSING capture for a run that wrote correctly.
    check("armed_outdir" in stop_blk,
          "16. --stop resolves the output dir from the CFG, not from its default",
          "a bare --stop after `--out vault/.../r5` would look in the wrong "
          "place and call a good capture missing")
    # A SECOND --stop ON A FINISHED RUN IS NOT A FAILURE. The first version
    # demanded a FRESH write, so running --stop twice reported "NO CAPTURE
    # APPEARED" about a complete capture sitting right there (2026-08-29).
    # A false alarm from a tool whose whole job is telling you the truth about
    # the artifact is worse than the silence it replaced.
    check("run_finished" in stop_blk,
          "16. --stop distinguishes a FINISHED run from a missing capture",
          "waiting for a fresh write is right while a run is live and nonsense "
          "once it has ended")
    fin = asrc[asrc.index("def run_finished"):asrc.index("def report_status")]
    # STRIP THE DOCSTRING AND COMMENTS FIRST. The first draft of this check
    # grepped the whole function and went red on its own docstring, which says
    # "NOT decided by the presence of movehook.bin" -- reading the PROSE that
    # states the property as a violation of it. A structural check has to look
    # at code.
    fin = re.sub(r'""".*?"""', "", fin, flags=re.S)
    fin = "\n".join(ln for ln in fin.splitlines()
                    if not ln.strip().startswith("#"))
    check("movehook.bin" not in fin and "binpath" not in fin,
          "16. and it does NOT decide that from the .bin's existence",
          "the periodic snapshot writes that file MID-RUN, so its presence "
          "proves the path works and never that the run is over -- deciding "
          "'finished' from it would stop a live run's wait immediately")
    try:
        cfgp = os.path.join(HERE, "movehook.cfg")
        saved_cfg = open(cfgp, encoding="ascii").read() \
            if os.path.isfile(cfgp) else None
        with open(cfgp, "w", encoding="ascii", newline="\n") as fh:
            fh.write("ms=1000\nout=" + os.path.join(tmp, "cfgwins") + "\n")
        got = attach.armed_outdir(None)
        check(os.path.normcase(got) == os.path.normcase(
                  os.path.abspath(os.path.join(tmp, "cfgwins"))),
              "16. CONTROL: and it really reads that value back",
              f"armed_outdir() returned {got!r}")
        check(os.path.normcase(attach.armed_outdir(os.path.join(tmp, "explicit")))
              == os.path.normcase(os.path.abspath(os.path.join(tmp, "explicit"))),
              "16. CONTROL: an explicit --out still wins over the cfg",
              "the override has to survive, or a re-read of an old run is "
              "impossible")
    finally:
        if saved_cfg is None:
            if os.path.isfile(cfgp):
                os.remove(cfgp)
        else:
            with open(cfgp, "w", encoding="ascii", newline="\n") as fh:
                fh.write(saved_cfg)

    # (f) THE PROCESS-EXIT WRITE, FOR REAL. Everything above is structural;
    # this is the R5 scenario itself -- a run still armed when the host exits.
    # `cmd /k` with a held-open stdin exits GRACEFULLY when that pipe closes,
    # which is what runs DLL_PROCESS_DETACH (TerminateProcess would not, and a
    # test built on kill() would prove nothing).
    dllpath = os.path.join(HERE, "movehook.dll")
    if not os.path.isfile(WOW64_CMD) or not os.path.isfile(dllpath):
        LEDGER.skip("16. the process-exit write",
                    "needs a 32-bit cmd.exe and a built DLL")
    else:
        exitdir = os.path.join(tmp, "hookout-exit")
        cfg = os.path.join(HERE, "movehook.cfg")
        saved = open(cfg, encoding="ascii").read() if os.path.isfile(cfg) else None
        # ms is LONG on purpose: the worker must still be in its poll loop when
        # the host exits, so the only thing that can write is the detach path.
        with open(cfg, "w", encoding="ascii", newline="\n") as fh:
            fh.write("ms=600000\nout=" + exitdir + "\n")
        proc = subprocess.Popen([WOW64_CMD, "/k", "rem movehook exit test"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=0x08000000)
        try:
            sys.path.insert(0, os.path.join(TOOLKIT, "harness"))
            import keytap
            import inject
            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    keytap.module_base(proc.pid, "KERNEL32.DLL")
                    break
                except Exception:
                    time.sleep(0.2)
            rc = inject.main([str(proc.pid), dllpath])
            binfile = os.path.join(exitdir, "movehook.bin")
            # Let the worker get past its controls and INTO the poll loop, then
            # confirm nothing has been written yet -- otherwise a file produced
            # by the normal ending would be mistaken for the detach path's.
            time.sleep(6.0)
            pre = os.path.isfile(binfile)
            check(rc == 0 and not pre,
                  "16. CONTROL: mid-run, with a long timer, nothing is written yet",
                  f"inject rc={rc}; bin present already: {pre} -- if it is, this "
                  f"section cannot attribute the file to the exit path")
            proc.stdin.close()                    # graceful exit -> DllMain
            proc.wait(timeout=20)
            deadline = time.time() + 10
            while time.time() < deadline and not os.path.isfile(binfile):
                time.sleep(0.25)
            check(os.path.isfile(binfile),
                  "16. AND THE CAPTURE IS WRITTEN WHEN THE HOST EXITS MID-RUN",
                  f"nothing at {binfile} (exit code {proc.returncode}) -- this "
                  f"is the R5 failure exactly: a run still armed when the "
                  f"client goes away")
            if os.path.isfile(binfile):
                check(open(binfile, "rb").read(4) == b"MVHK",
                      "16. and it is a real capture, not a stub",
                      "the exit path must write the same format as any other")
        except Exception as ex:                                # noqa: BLE001
            LEDGER.skip("16. the process-exit write", f"host/inject failed: {ex}")
        finally:
            try:
                proc.kill()
            except Exception:
                pass
            if saved is None:
                if os.path.isfile(cfg):
                    os.remove(cfg)
            else:
                with open(cfg, "w", encoding="ascii", newline="\n") as fh:
                    fh.write(saved)

    # (g) THE PERIODIC SNAPSHOT, AND THE HARD KILL IT EXISTS FOR.
    #
    # A SEPARATE HOST FROM (f), DELIBERATELY. The first version of this tested
    # both mechanisms through ONE file and compared mtimes to tell them apart,
    # and it went red for a reason that was neither mechanism failing: the
    # snapshot and the exit write landed 86 ms apart, so the "before" reading
    # was already the exit write's. Two mechanisms racing through one artifact
    # cannot be attributed by looking at the artifact. One host, one mechanism.
    #
    # What this one covers is the case (f) cannot: `TerminateProcess` does NOT
    # run DllMain, so on a hard kill -- the harness's own fallback when WM_CLOSE
    # times out, or an operator's taskkill -- the periodic snapshot is the only
    # thing standing between the run and another R5.
    if not os.path.isfile(WOW64_CMD) or not os.path.isfile(dllpath):
        LEDGER.skip("16. the periodic snapshot", "needs cmd.exe and a built DLL")
    else:
        snapdir = os.path.join(tmp, "hookout-snap")
        cfg = os.path.join(HERE, "movehook.cfg")
        saved = open(cfg, encoding="ascii").read() if os.path.isfile(cfg) else None
        with open(cfg, "w", encoding="ascii", newline="\n") as fh:
            fh.write("ms=600000\nout=" + snapdir + "\n")
        proc = subprocess.Popen([WOW64_CMD, "/k", "rem movehook snapshot test"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=0x08000000)
        try:
            import keytap
            import inject
            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    keytap.module_base(proc.pid, "KERNEL32.DLL")
                    break
                except Exception:
                    time.sleep(0.2)
            inject.main([str(proc.pid), dllpath])
            binfile = os.path.join(snapdir, "movehook.bin")
            # The worker only reaches its poll loop after control B, which can
            # wait CTLB_MS for its own hit -- so the first flush is FLUSH_MS
            # AFTER that, not after injection. Budget both, generously.
            deadline = time.time() + FLUSH_MS_S + 25
            while time.time() < deadline and not os.path.isfile(binfile):
                time.sleep(0.5)
            alive = proc.poll() is None
            check(os.path.isfile(binfile) and alive,
                  "16. THE PERIODIC SNAPSHOT LANDS MID-RUN, host still alive",
                  f"file={os.path.isfile(binfile)} alive={alive} -- without a "
                  f"mid-run flush, a hard kill still loses the whole run and "
                  f"the fix would only cover a graceful close")
            # NOW KILL IT HARD. TerminateProcess runs no DllMain, so nothing
            # more can be written: whatever is on disk is the snapshot's, and
            # it has to be a usable capture.
            proc.kill()
            proc.wait(timeout=10)
            time.sleep(1.0)
            ok = os.path.isfile(binfile)
            check(ok, "16. AND IT SURVIVES A HARD KILL (no DllMain runs at all)",
                  f"nothing at {binfile} after TerminateProcess")
            if ok:
                try:
                    import readhook as _rh2
                    n = len(_rh2.Capture(binfile).recs)
                    good, why = True, f"{n} records"
                except Exception as ex:                        # noqa: BLE001
                    good, why = False, f"readhook refused it: {ex}"
                check(good,
                      "16. and what survived is a capture readhook can parse",
                      why)
        except Exception as ex:                                # noqa: BLE001
            LEDGER.skip("16. the periodic snapshot", f"host/inject failed: {ex}")
        finally:
            try:
                proc.kill()
            except Exception:
                pass
            if saved is None:
                if os.path.isfile(cfg):
                    os.remove(cfg)
            else:
                with open(cfg, "w", encoding="ascii", newline="\n") as fh:
                    fh.write(saved)

    # (h) THE TWO DEFAULT PATHS MUST AGREE. attach.py --stop looks for the
    # artifact at its own default; the DLL writes at DEFDIR. If they diverge,
    # --stop reports a missing capture that is sitting on disk somewhere else.
    m = re.search(r'#define\s+DEFDIR\s+"([^"]+)"', src)
    check(m is not None, "16. movehook.c still declares DEFDIR")
    if m:
        c_default = m.group(1).replace("\\\\", "\\").rstrip("\\").lower()
        py_default = attach.default_outdir().rstrip("\\").lower()
        check(os.path.normcase(os.path.normpath(c_default))
              == os.path.normcase(os.path.normpath(py_default)),
              "16. and attach.py's default output dir AGREES with it",
              f"C says {c_default!r}, attach.py says {py_default!r} -- a "
              f"divergence makes --stop report a missing capture that exists")


# ---------------------------------------------------------------- §17
def section_17(tmp):
    """THE RETURN TAP: the second emulation shape, and the answer it captures.

    WHAT THIS CAN AND CANNOT PROVE, stated first because §16's own trick does
    not transfer. §7 injects into a throwaway 32-bit cmd.exe where EVERY SITE
    FAILS TO ARM -- deliberately, and §15's docstring says that is exactly why
    the handler's hot path is never executed by a test. So a cmd.exe host proves
    the DLL survives non-resolving ret rows and NOTHING about the emulation
    itself. What is checkable offline is: the rows are what they claim against
    the pinned client's own bytes (§1/§2 already do the byte half), the
    structural refusals fire, the reader's v7 layout matches the C, the pairing
    joins and REFUSES correctly, and the out-param semantics survive a synthetic
    capture. Whether a persistent 0xCC at 0x00709F0F resumes correctly on real
    hardware is a live-run question, and no offline check substitutes for it.
    """
    try:
        import gensites
        import readhook
    except Exception as ex:
        LEDGER.skip("17. the return tap", f"cannot import: {ex}")
        return
    rows = gensites.rows()[0]
    rets = {n: r for n, r in rows.items()
            if r.get("shape") == "ret"}

    # ---- (a) the rows exist and declare the shape ------------------------
    eq(len(rets), 4, "17. four MapFindPath ret rows are registered")
    for n, r in sorted(rets.items()):
        eq(r["first_byte"], 0xC3, f"17. `{n}` declares first_byte 0xC3")
        # THE ONE THAT WOULD HAVE CORRUPTED THE CAPTURE. arg2's slot holds FPU
        # scratch at every ret, so a ret row inheriting the entry row's
        # deref_arg_b = 2 would deref a float as a pointer -- and readable()
        # can ACCEPT it (10000.0f is 0x461C4000, a plausible address).
        eq(int(r.get("deref_arg_b") or 0), 0,
           f"17. `{n}` does NOT deref arg2 -- the callee overwrites that slot")
        check(not r.get("deref_agent"),
              f"17. `{n}` does NOT deref ecx -- it is scratch at a return")
        eq(int(r.get("deref_out") or 0), 5, f"17. `{n}` reads outCount from arg5")
        eq(int(r.get("deref_out_path") or 0), 6,
           f"17. `{n}` reads outPath from arg6")

    # ---- (b) the REFUSALS, each proven to fire ---------------------------
    # A gate nobody has watched refuse is a wish. Every one of these is a
    # silent-garbage bug rather than a loud one, which is why they are refusals
    # in the generator rather than comments in the row.
    import copy
    # `pinned.find()` EXITS THE PROCESS rather than raising when the vaulted
    # image is missing, so `except Exception` around it catches nothing -- which
    # is why a vault-less machine dies at §2 today instead of skipping. Ask
    # first, and skip this block cleanly rather than taking the suite down.
    try:
        import pinned
        _have_image = bool(pinned.find())
    except BaseException:                                   # noqa: BLE001
        _have_image = False
    # NOT a `return` -- (c) and (d) below are process-free and must still run on
    # a machine with no vaulted image, or the floor's own arithmetic is wrong.
    if not _have_image:
        LEDGER.skip("17b. the generator's refusals", NO_CLIENT)
    else:
        base_bad, _ = gensites.verify(rows)
        check(base_bad == [], "17. the real rows pass the generator's own gate",
              f"{base_bad}")
        victim = sorted(rets)[0]
        for label, patch, expect in (
                ("an unknown shape", {"shape": "middle-of-a-loop"},
                 "not one movehook"),
                ("a ret row dereffing ecx", {"deref_agent": True}, "SCRATCH"),
                ("a ret row dereffing arg2", {"deref_arg_b": 2}, "FPU scratch"),
                ("a ret row claiming 0x55", {"first_byte": 0x55}, "0xC3")):
            s = copy.deepcopy(rows)
            s[victim].update(patch)
            bad, _ = gensites.verify(s)
            hit = [b for b in bad if b[0] == victim]
            check(hit and expect in hit[0][1],
                  f"17. the generator REFUSES {label}",
                  f"got {hit or 'no refusal at all'}")
        # And the byte check alone must refuse a shape swap on a row that trips
        # no structural rule -- otherwise the byte half is untested, having
        # always been short-circuited by the deref refusals.
        s = copy.deepcopy(rows)
        s["chcli_dir"]["shape"] = "ret"
        bad, _ = gensites.verify(s)
        hit = [b for b in bad if b[0] == "chcli_dir"]
        check(hit and "0xC3" in hit[0][1],
              "17. and an ENTRY row relabelled `ret` is refused ON THE BYTE",
              f"got {hit or 'no refusal'} -- chcli_dir sets no deref, so only "
              f"the byte check can catch this one")

    # ---- (c) the ret-tap layouts are APPENDED, not inserted ---------------
    v6 = readhook._LAYOUTS[6]
    # A reorder keeps `reclen` plausible while shifting every field -- the
    # defect the v6 note in movehook.c was written for. Appending is what makes
    # a mismatched reader fail loudly instead.
    for ver in (7, 8):
        lay = readhook._LAYOUTS[ver]
        check(lay[:len(v6)] == v6,
              f"17. v{ver} is v6 plus a tail -- APPENDED, never inserted",
              f"v{ver}'s first {len(v6)} fields are {lay[:len(v6)]}, "
              f"not v6's {v6}")
        added = [n for n, _c in lay[len(v6):]]
        eq(added, ["esp", "have_out", "out_count", "out_n", "out_path"],
           f"17. and v{ver}'s tail is exactly the ret tap's fields")
    # v8 WIDENS out_path AND KEEPS v7 READABLE. r7 -- the arc's only capture
    # carrying the client's own answers -- is a v7 file, and redefining v7 in
    # place would have made `reclen` disagree and ORPHANED it. That is the
    # failure §4 pins with "a v1 capture still parses": versioning that
    # orphans the evidence is worse than not versioning at all.
    cap7 = dict(readhook._LAYOUTS[7])["out_path"]
    cap8 = dict(readhook._LAYOUTS[8])["out_path"]
    eq((cap7, cap8), (16, 36),
       "17. v7 holds 4 points and v8 holds 9 -- BOTH layouts still exist")
    # v9 APPENDS the two walk-gate words and must not orphan either older
    # layout: r7 and r8 are real captures on disk and both must still parse.
    eq(len(readhook._LAYOUTS[9]) - len(readhook._LAYOUTS[8]), 3,
       "17. v9 appends exactly three fields (have_gate, gate_flags, gate_status)")
    eq([n for n, _ in readhook._LAYOUTS[9]][:len(readhook._LAYOUTS[8])],
       [n for n, _ in readhook._LAYOUTS[8]],
       "17. and v9 is v8 with fields APPENDED, never inserted or reordered")
    eq(readhook.CURRENT_VER, 9, "17. the writer's version is 9")
    src_c = open(os.path.join(HERE, "movehook.c"), encoding="utf-8").read()
    check("DWORD ver = 9" in src_c,
          "17. and movehook.c writes version 9 into the header",
          "the C and the reader must agree or every parse shifts")
    check("#define RET_MAX_POINTS 9u" in src_c,
          "17. and RET_MAX_POINTS is 9 -- click-to-move's own maxCount, so "
          "the buffer cannot truncate for either known caller",
          "9 is not a percentile; it is read from both callers' frames")
    # THE CAPACITY A READER QUOTES MUST COME FROM THE RECORD, NOT THE WRITER.
    # `RET_MAX_POINTS` describes the CURRENT writer; a v7 record holds 4. A
    # reader that quotes the module constant at a v7 record reports a capacity
    # the file does not have.
    eq(readhook.ret_capacity({"out_path": (0,) * 16}), 4,
       "17. ret_capacity() reads a v7 record as 4 points")
    eq(readhook.ret_capacity({"out_path": (0,) * 36}), 9,
       "17. and a v8 record as 9 -- per record, never the global")

    # ---- (d) the OUT-PARAM semantics, on a synthetic capture -------------
    # `have_out` is the measurement, not bookkeeping: pathCount == 0 IS the
    # registered prediction (HANDOFF-PLANE §4.2), so "could not read it" and
    # "the client answered zero" must never merge into one number.
    import gensites as gs
    names = list(gs.rows()[0])
    ret_i = names.index(sorted(rets)[3])          # ret4, the common arm
    ent_i = names.index("mapfindpath")
    recs = [
        # a paired question and answer, same tid, same esp: pathCount 2
        {"seq": 0, "tick": 1000, "site": ent_i, "tid": 7, "esp": 0x1000},
        {"seq": 1, "tick": 1001, "site": ret_i, "tid": 7, "esp": 0x1000,
         "have_out": 3, "out_count": 2, "out_n": 2},
        # a pair whose esp DISAGREES -- refutes the premise, must not pair
        {"seq": 2, "tick": 1002, "site": ent_i, "tid": 7, "esp": 0x2000},
        {"seq": 3, "tick": 1003, "site": ret_i, "tid": 7, "esp": 0x2ff0,
         "have_out": 1, "out_count": 0},
        # an answer with no question at all
        {"seq": 4, "tick": 1004, "site": ret_i, "tid": 9, "esp": 0x3000,
         "have_out": 1, "out_count": 0},
    ]
    path = _synth_capture(tmp, "rettap.bin", recs, len(names))
    cap = readhook.Capture(path)
    eq(cap.version, 7, "17. the synthetic v7 capture parses")
    pairs, orphan, esp_bad = readhook._pair_mfp(cap, names)
    eq(len(pairs), 1, "17. exactly the one well-formed pair is joined")
    eq(orphan, 1, "17. an answer with no question is COUNTED, not paired")
    # Pairing an esp mismatch anyway would compare two different invocations;
    # the mismatch refutes the epilogue reading and must be visible as that.
    eq(esp_bad, 1,
       "17. an esp MISMATCH refuses the pair and is counted separately")
    txt, _ = readhook.report(cap, names)
    check("MapFindPath ANSWERS" in txt,
          "17. and the v7 report SECTION prints",
          "a field captured and never printed is a field the run does not have")
    check("esp MISMATCH" in txt,
          "17. and the report says so out loud when the premise is refuted",
          f"{txt[-1500:]}")

    # ---- (e) THE SPLIT THAT WAS THE POINT: BOTH-FAILED is not OURS ------
    #
    # The three-valued scorer counted "we found no route" as OURS-FAILED
    # WITHOUT KNOWING whether the client found one -- so every query neither
    # side could answer inflated our own decode-gap number by an unknown
    # amount. That is the MOVECODE-Q2 headline, and it is what the ret tap
    # actually buys. A stub mesh keeps this process-free: the assertion is
    # about the VERDICT LOGIC, not about any map's geometry.
    try:
        import pathdiff
    except Exception as ex:                                  # noqa: BLE001
        LEDGER.skip("17e. the five-valued split", f"cannot import pathdiff: {ex}")
        return

    class _StubMesh:
        """walkable() everywhere; route() succeeds only from x == 0."""
        def walkable(self, x, y):
            return abs(x) < 1e5 and abs(y) < 1e5
        def route(self, x0, y0, x1, y1):
            return [(x0, y0), (x1, y1)] if x0 == 0.0 else []

    def _q(sx, sy, dx, dy):
        return pathdiff.Query({"seq": 0, "tick": 1, "arg3": 0, "arg4": 0,
                               "have_pts": 3,
                               "pt_a": (_flt(sx), _flt(sy), 0, 0),
                               "pt_b": (_flt(dx), _flt(dy), 0, 0)},
                              lambda v: v)

    def _ret(count, n=0, path=()):
        return {"have_out": 3 if path else 1, "out_count": count, "out_n": n,
                "out_path": tuple(path) + (0,) * (16 - len(path))}

    cases = [
        # (ours routes?, client count) -> verdict
        (_q(0.0, 0.0, 10.0, 0.0), _ret(0), "THEIRS-FAILED"),
        (_q(5.0, 0.0, 10.0, 0.0), _ret(2, 2, (_flt(7.0), _flt(0.0), 0, 0,
                                              _flt(10.0), _flt(0.0), 0, 0)),
         "OURS-FAILED"),
        (_q(5.0, 0.0, 10.0, 0.0), _ret(0), "BOTH-FAILED"),
        (_q(0.0, 0.0, 10.0, 0.0), _ret(2, 2, (_flt(3.0), _flt(0.0), 0, 0,
                                              _flt(10.0), _flt(0.0), 0, 0)),
         "AGREE"),
        (_q(0.0, 0.0, 10.0, 0.0), _ret(2, 2, (_flt(3.0), _flt(0.0), 0, 0,
                                              _flt(900.0), _flt(0.0), 0, 0)),
         "DIFFER"),
        # have_out bit 0 clear: the count could NOT be read. Must NOT become a
        # zero -- pathCount == 0 is the registered prediction, and merging
        # "unreadable" into it would manufacture evidence for it.
        (_q(0.0, 0.0, 10.0, 0.0), {"have_out": 0, "out_count": 0, "out_n": 0,
                                   "out_path": (0,) * 16}, "UNREADABLE"),
    ]
    stub = _StubMesh()
    for q, r, want in cases:
        _rows, t = pathdiff.score_paired(stub, [(q, r)])
        got = [k for k, v in t.items() if v]
        check(got == [want], f"17e. a query scores {want}",
              f"scored {got or 'nothing'} instead")

    # THE CONTROL THAT MATTERS: the same BOTH-FAILED query, scored by the OLD
    # three-valued path, must come out OURS-FAILED -- otherwise this section is
    # asserting a distinction that never existed and proves nothing.
    _rows, old = pathdiff.score(stub, [(5.0, 0.0, 10.0, 0.0)])
    eq(old["OURS-FAILED"], 1,
       "17e. CONTROL: the three-valued scorer calls that same query OURS-FAILED")

    # ---- (f) THE SHAPE METRIC MUST RANK A KNOWN-BAD ARM BADLY -----------
    #
    # THIS SECTION EXISTS BECAUSE THE FIRST ONE SHIPPED A TAUTOLOGY. R7's
    # scorer compared our route's LAST point to the client's LAST waypoint --
    # and the callee OVERWRITES outPath[count-1] with the requested
    # destination verbatim (0x0070A04E/0x0070A053), while route() ends at the
    # goal by construction. Both operands were the destination, so the test
    # could not fail: 129 of 131 comparisons read exactly 0.0 u, DIFFER never
    # fired once in 214 live queries, and a deliberate 800 u detour scored
    # PERFECT AGREEMENT. The repo's own rule is the check: a metric that
    # cannot rank a known-bad arm badly is disqualified before it is used.
    #
    # The known-bad arm is the client's own answer with BOTH ENDPOINTS
    # PRESERVED and the interior waypoints shoved sideways -- exactly what a
    # last-point test cannot see and a shape test must.
    def _ret_path(pts, count):
        flat = []
        for (px, py) in pts:
            flat += [_flt(px), _flt(py), 0, 0]
        flat += [0] * (16 - len(flat))
        return {"have_out": 3, "out_count": count, "out_n": count,
                "out_path": tuple(flat)}

    class _BendMesh:
        """route() returns a path that bends the SAME way the client's does."""
        def walkable(self, x, y):
            return True
        def route(self, x0, y0, x1, y1):
            return [(x0, y0), (50.0, 40.0), (x1, y1)]

    q = _q(0.0, 0.0, 100.0, 0.0)
    truthful = _ret_path([(50.0, 40.0), (100.0, 0.0)], 2)
    # Same endpoints, interior waypoint displaced 200 u perpendicular.
    known_bad = _ret_path([(50.0, -160.0), (100.0, 0.0)], 2)
    bend = _BendMesh()
    _r1, t_true = pathdiff.score_paired(bend, [(q, truthful)])
    _r2, t_bad = pathdiff.score_paired(bend, [(q, known_bad)])
    check(t_true["AGREE"] == 1,
          "17f. the shape metric AGREES with a matching polyline",
          f"scored {[k for k, v in t_true.items() if v]}")
    check(t_bad["DIFFER"] == 1,
          "17f. and RANKS A KNOWN-BAD ARM BADLY -- same endpoints, interior "
          "waypoint moved 200 u",
          f"scored {[k for k, v in t_bad.items() if v]} -- this is the exact "
          f"shape the shipped last-point metric called perfect agreement")

    # And the tautology itself, pinned: a last-point comparison CANNOT tell
    # those two apart, which is why the check above is the one that matters.
    last_true = math.hypot(100.0 - 100.0, 0.0 - 0.0)
    last_bad = math.hypot(100.0 - 100.0, 0.0 - 0.0)
    check(last_true == last_bad == 0.0,
          "17f. CONTROL: a LAST-POINT metric scores both identically (0.0 u) "
          "-- the disqualified form, demonstrated",
          "if these differ the fixture no longer reproduces the tautology")

    # Truncation is its own verdict, not agreement.
    trunc = {"have_out": 3, "out_count": 6, "out_n": 4,
             "out_path": tuple([_flt(1.0), _flt(1.0), 0, 0] * 4)}
    _r3, t_tr = pathdiff.score_paired(bend, [(q, trunc)])
    check(t_tr["UNCOMPARED"] == 1,
          "17f. a TRUNCATED path scores UNCOMPARED, never AGREE",
          f"scored {[k for k, v in t_tr.items() if v]} -- scoring a "
          f"non-comparison as agreement inflated r7's AGREE by 13 rows")


def _flt(f):
    """A float as the dword movehook would have stored."""
    return struct.unpack("<I", struct.pack("<f", f))[0]


# ---------------------------------------------------------------- §19
def section_19(tmp):
    """THE MOTION WINDOW: an unset stamp is not a time, and a leg is clipped.

    THREE DEFECTS IN ONE EXPRESSION, all found by R7's scoring pass. The world
    census computed `max(ptime) - min(ptime)` over every record:

      (1) Exactly two records per object -- the run's first setter and bake --
          carry `ptime == 0`, an agent stamp the client had never set. They drag
          `min` to zero and inflate the denominator by the whole pre-capture
          uptime: r7 printed "in motion 61.8%" where the truth is 87.8%, a
          27-POINT ERROR FROM 2 RECORDS IN 1,785 -- and it is in EVERY v4+
          capture in the corpus. The existing "impossible leg" guard cannot see
          it, because those records have `stop == 0` too: that guard tests the
          LEG, and this defect is in the STAMP.
      (2) `stop` is a FUTURE arrival, so a leg can end after the last
          observation and merely dropping the zeros still produced percentages
          OVER 100 (107.9% on run3-isle). Legs are clipped into the observed
          window rather than the window stretched to fit them.
      (3) It raised KeyError on v1-v3, which have no `ptime` field -- so
          `readhook.py --bin` CRASHED on run 1, the arc's only v1 capture,
          while §4 pinned "a v1 capture still parses". That was true of the
          PARSE and never of the REPORT.

    Each gets a check, and (1) gets the control that matters: the OLD
    expression, applied to the same fixture, must produce the inflated number.
    """
    try:
        import readhook as rh
        import gensites
        names = list(gensites.rows()[0])
    except Exception as ex:                                  # noqa: BLE001
        LEDGER.skip("19. the motion window", f"cannot import: {ex}")
        return
    site = names.index("setter")
    A = 0x0BAD1000

    def rec(seq, ptime, stop, vx, x, ver_has_stamp=True):
        r = {"seq": seq, "tick": 1000 + seq, "site": site, "ecx": A,
             "have_agent": 1, "id": 1, "world": 1,
             "point": (_flt(x), _flt(0.0), 0, 0),
             "vel": (_flt(vx), _flt(0.0))}
        if ver_has_stamp:
            r["ptime"] = ptime
            r["stop"] = stop
        return r

    # ---- (1) the UNSET stamp -------------------------------------------
    # One zero-stamp record, then a 10 s window with a 1 s leg in it.
    recs = [rec(0, 0, 0, 0.0, 0.0),                 # the unset stamp
            rec(1, 100000, 101000, 300.0, 100.0),   # a 1 s leg
            rec(2, 110000, 110000, 0.0, 200.0)]
    p = _synth_capture(tmp, "window.bin", recs, len(names))
    cap = rh.Capture(p)
    txt, _ = rh.report(cap, names)
    check("of 10.0 s" in txt,
          "19. the window EXCLUDES the unset stamp (10.0 s, not 110.0 s)",
          f"the census said:\n{_census(txt)}")
    check("UNSET position stamp" in txt,
          "19. and the exclusion is REPORTED, not silent",
          "'we ignored 2 records' and 'there were none' are different facts, "
          "and the first is the one that explains a number")
    # THE CONTROL: the shipped expression, on this same fixture, must produce
    # the inflated denominator -- or this section pins nothing.
    old_span = max(r["ptime"] for r in recs) - min(r["ptime"] for r in recs)
    eq(old_span, 110000,
       "19. CONTROL: the OLD expression inflates this same fixture to 110.0 s")

    # ---- (2) a leg that outlives the window is CLIPPED -------------------
    # One leg running 100 s past the last observation. Unclipped it would read
    # 1000%; the honest answer is that we observed 10 s and it moved for all
    # of them.
    recs2 = [rec(0, 100000, 200000, 300.0, 0.0),
             rec(1, 110000, 110000, 0.0, 100.0)]
    p2 = _synth_capture(tmp, "clip.bin", recs2, len(names))
    txt2, _ = rh.report(rh.Capture(p2), names)
    check("(100.0%)" in txt2,
          "19. a leg outlasting the window is CLIPPED to it, never over 100%",
          f"the census said:\n{_census(txt2)}")

    # ---- (3) a pre-stamp capture reports rather than crashing ------------
    # v3 has no `ptime`/`stop` field at all. This raised KeyError before.
    recs3 = [{"seq": 0, "tick": 1000, "site": site, "ecx": A, "have_agent": 1,
              "id": 1, "point": (_flt(0.0), _flt(0.0), 0, 0)},
             {"seq": 1, "tick": 1100, "site": site, "ecx": A, "have_agent": 1,
              "id": 1, "point": (_flt(50.0), _flt(0.0), 0, 0)}]
    p3 = _synth_capture(tmp, "nostamp.bin", recs3, len(names), ver=3)
    try:
        txt3, _ = rh.report(rh.Capture(p3), names)
        crashed = None
    except Exception as ex:                                  # noqa: BLE001
        txt3, crashed = "", ex
    check(crashed is None,
          "19. a v3 capture (no position stamp) does NOT crash the report",
          f"raised {crashed!r} -- this is the KeyError that made "
          f"`readhook.py --bin` unusable on run 1")
    check("UNAVAILABLE" in txt3,
          "19. and it says UNAVAILABLE rather than inventing a window",
          f"{_census(txt3)}")


def _census(txt):
    """The world-copy block of a report, for a failure message."""
    i = txt.find("world copies")
    return txt[i:i + 600] if i >= 0 else txt[-600:]


# ---------------------------------------------------------------- §18
def section_18():
    """MAP IDENTIFICATION: the score must not be won by mesh SIZE.

    THIS SECTION EXISTS BECAUSE THE SHIPPED SCORER PICKED THE WRONG MAP AND
    THE GUARD BESIDE IT COULD NOT SEE THAT HAPPEN. `--map auto` scored the
    fraction of captured endpoints landing on each candidate mesh, which has an
    area term by construction -- a bigger mesh swallows any point cloud. On r7,
    a map-280 capture, Sparkfly Swamp scored 99.3% against map 280's own 81.8%
    and WON; `auto` refused only on its margin rule, with 2.5 points to spare.
    Believed, it would have reported OFF-MESH 3 instead of 63 -- the wrong map
    makes our decode look 20x BETTER, and OFF-MESH is the very signal this tool
    exists to produce. The old cross-check could not catch it either: it fired
    only below 50% coverage, i.e. only when a wrong map looked BAD.

    The fix adds the client's own PLANE word as a second term -- conditioned on
    the points that landed, so mesh size cancels -- restricted to NON-ZERO
    planes, because plane 0 exists on every mesh and agrees by coincidence.

    Both halves are checked here, and the second is the one that matters: a
    guard that only fires when the answer already looks wrong is not a guard.
    """
    try:
        import pathdiff
        import readhook as rh
        import pinned
        if not pinned.find():
            raise RuntimeError("no pinned client")
    except BaseException as ex:                              # noqa: BLE001
        LEDGER.skip("18. map identification", f"needs the vault: {ex}")
        return
    binp = os.path.join(r"C:\gd\Rurik\vault\research\movecode\r7", "movehook.bin")
    if not os.path.isfile(binp):
        LEDGER.skip("18. map identification", "the r7 capture is not in the vault")
        return
    try:
        cap = rh.Capture(binp)
        names = rh.site_names(cap)
        qs = [q for q in (pathdiff.queries(cap, names) or []) if q.src and q.dst]
        scored = pathdiff.map_scores(qs)
    except Exception as ex:                                  # noqa: BLE001
        LEDGER.skip("18. map identification", f"could not score: {ex}")
        return
    check(bool(scored), "18. the r7 capture scores against the candidate meshes")
    if not scored:
        return
    TRUE, BIG = 0x287B3, 0x46305         # map 280; Sparkfly, the 99.3% impostor
    rank = [r[1] for r in scored]
    eq(rank[0], TRUE, "18. the TRUE map (0x287B3) ranks first")
    # THE KNOWN-BAD ARM, and it is a real one rather than a constructed one:
    # the mesh that beat the true map under the old score must now lose.
    if BIG in rank:
        big_pos = rank.index(BIG) + 1
        check(big_pos > 1,
              f"18. and the impostor mesh 0x{BIG:X} -- which WON under the "
              f"area-biased score at 99.3% coverage -- now ranks #{big_pos}",
              "a scorer that still prefers the larger mesh is the shipped bug")
        big = scored[big_pos - 1]
        check(big[0] < scored[0][0],
              "18. the impostor's SCORE is below the true map's",
              f"impostor {big[0]:.3f} vs true {scored[0][0]:.3f}")
    # The margin must clear the module's own refusal bar, or `auto` refuses on
    # a capture it can actually identify.
    margin = scored[0][0] - (scored[1][0] if len(scored) > 1 else 0.0)
    check(scored[0][0] >= 0.6 and margin >= 0.2,
          f"18. and the win clears the refusal bar (score {scored[0][0]:.3f}, "
          f"margin {margin:.3f}) -- thresholds UNCHANGED by the fix",
          "the score was the broken part, not the guard; if this fails the "
          "thresholds were loosened to make a weak score pass")
    # THE OTHER HALF: the explicit-map cross-check must SPEAK when the named
    # map loses. It printed nothing in the flattering direction before.
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pathdiff.cross_check_map(qs, BIG)
    said = buf.getvalue()
    check("ANOTHER MESH FITS THIS CAPTURE BETTER" in said,
          "18. naming the impostor map explicitly is CALLED OUT",
          f"the cross-check said:\n{said}")
    check(f"0x{TRUE:X}" in said,
          "18. and the warning names the mesh that fits better",
          f"{said}")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pathdiff.cross_check_map(qs, TRUE)
    quiet = buf.getvalue()
    check("ANOTHER MESH FITS" not in quiet,
          "18. CONTROL: naming the CORRECT map is not called out",
          f"a guard that fires on the right answer too is noise:\n{quiet}")


def _synth_capture(tmp, name, recs, nsites, ver=7):
    """A movehook capture built from readhook's OWN layout for `ver`.

    Fixture and parser share one description of the record -- §11's discipline,
    and the reason a fixture cannot drift from the C without §11 going red.
    """
    import readhook
    spec, fmt, _ln = readhook._layout(ver)
    flat = []
    for n, c in spec:
        flat.extend([n] * c)
    out = bytearray(b"MVHK")
    out += struct.pack("<IIIII", ver, 0x00400000, nsites,
                       struct.calcsize(fmt), len(recs))
    for i in range(nsites):
        out += struct.pack("<II", i, 0)
    for r in recs:
        vals, seen = [], {}
        for n, c in spec:
            v = r.get(n, 0)
            if c == 1:
                vals.append(v if isinstance(v, int) else 0)
            else:
                seq = v if isinstance(v, (list, tuple)) else ()
                vals.extend(list(seq) + [0] * (c - len(seq)))
            seen[n] = True
        out += struct.pack(fmt, *vals)
    p = os.path.join(tmp, name)
    with open(p, "wb") as fh:
        fh.write(bytes(out))
    return p


def main():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="movehook-test-")
    section_1_2()
    section_3()
    section_4_5(tmp)
    section_6_7(tmp)
    section_9()
    section_10(tmp)
    section_11()
    section_12(tmp)
    section_13(tmp)
    section_14(tmp)
    section_15()
    section_16(tmp)
    section_17(tmp)
    section_18()
    section_19(tmp)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
