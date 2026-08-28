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
#   ----    process-free core = 102, and THAT is the floor.
#
# §12 and §13 both read `gensites.rows()`, which goes to `content.load()` and never
# opens the client, so their eleven are process-free and the core moved with them.
# A whole green run on this machine is now 150.
#
# §14 SPLITS, and the split was counted out of the banner rather than reasoned
# about: 25 checks, of which the 8 non-entry refusals and their 1 control call
# `gensites.verify()` and therefore need the vaulted image, while the row
# assertions and the whole v6 round-trip go through `content.load()` and a
# synthesised capture and never open it. 59 - 9 = 50 process-free, so the core
# moves 46 -> 102. A bare machine must still clear 102.
#
# The first draft of this comment guessed 16 by adding up what the sections
# looked like they contained, and it was two low -- which would have let two
# checks stop running with the suite still green. The rule the repo already has
# ("set the floor from a real green run, never from a guess") is not about
# arithmetic being hard; it is that a floor derived from the code rather than
# from the output drifts the moment either changes. `skip()` lowers the floor by
# ZERO, so a bare machine must still clear 102.
LEDGER = checks.Ledger("movehook", floor=102)
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
        sites, offs = gensites.rows()
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
    # The load-bearing one: the emulation is `push ebp` and nothing else, so a
    # site that is not an entry must never be armed by the generator.
    for name in sorted(sites):
        eq(sites[name]["first_byte"], 0x55,
           f"2. {name} begins `55 push ebp` -- the ONE shape the handler emulates")

    # §1: the checked-in header must BE what the generator produces. A hand-edited
    # sites.h is the split the ruling refuses, and it would be invisible otherwise.
    hdr = os.path.join(HERE, "sites.h")
    if os.path.isfile(hdr):
        want = gensites.emit(sites, offs, path)
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
        keytap.module_base = lambda pid, name: 0x00400000

        keytap.read_at = lambda pid, addr, n: b"\x55" * n
        bad, base = attach.verify_running_build(1234)
        check(bad == [], "9. a client holding 0x55 at every site is ACCEPTED",
              f"refused a correct client: {bad}")
        eq(base, 0x00400000, "9. and the image base is reported")

        # One site wrong is enough: this is what a build bump looks like.
        wrong = {0x00400000 + 0x001FE950: b"\x8b"}
        keytap.read_at = lambda pid, addr, n: wrong.get(addr, b"\x55" * n)
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
        import gensites
        nsites = len(gensites.rows()[0])
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
        rows, _offs = gensites.rows()
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
        rows, _offs = gensites.rows()
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
        rows, _offs = gensites.rows()
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
        rows, offs = gensites.rows()
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
        eq(int(tk.get("stride") or 0), 64,
           "14. and it is STRIDED -- movehook's worker ENDS THE RUN when the ring "
           "fills, so an unstrided per-frame site truncates the whole capture")

    # THE GUARD THAT MATTERS MORE THAN THE ROW. A stride on a site whose RECORDS
    # are counted turns every rate in this arc into a silent undercount -- the
    # displacement census, the reseed split, P1a's bake rate and the gate-3 filter
    # all count stored records. `hits` is unaffected by the stride, `stored` is
    # not, and nothing in the file would announce the change. So the sites whose
    # records are counted are named here and required to be unstrided.
    COUNTED = ("bake", "teleport", "setter", "reseed", "resync", "snaptest",
               "stepclear", "setposition", "agtrack", "mapfindpath",
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
    eq(cap.version, 6, "14. the capture declares v6")
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
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
