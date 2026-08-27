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
import checks                                                   # noqa: E402

# MEASURED off a real green run, 2026-08-26 -- counted per section out of the
# banner, never computed by addition. A whole green run on this machine is 47:
#
#   §1  6   sites.h is what the generator emits    needs the vaulted client
#   §2  5   first bytes vs the pinned image        needs the vaulted client
#   §3  4   the provenance rules really refuse     process-free
#   §4 12   the reader's parse and its scoring     process-free
#   §5  6   the dead-control refusal + the commit flag   process-free
#   §6  2   the DLL builds, and it is x86          needs a compiler
#   §7  5   inject into a live 32-bit cmd.exe      needs SysWOW64\cmd.exe
#   §8  2   movehook.cfg beats the environment     rides on §7's injected run
#   §9  5   attach.py's build guard, both ways   process-free
#   ----   process-free core = 27, and THAT is the floor.  A whole run is 47.
#
# The first draft of this comment guessed 16 by adding up what the sections
# looked like they contained, and it was two low -- which would have let two
# checks stop running with the suite still green. The rule the repo already has
# ("set the floor from a real green run, never from a guess") is not about
# arithmetic being hard; it is that a floor derived from the code rather than
# from the output drifts the moment either changes. `skip()` lowers the floor by
# ZERO, so a bare machine must still clear 27.
LEDGER = checks.Ledger("movehook", floor=27)
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
def _synth(recs, sites_hits, base=0x00400000):
    """A capture file exactly as movehook.c writes one."""
    import readhook
    out = bytearray()
    out += b"MVHK"
    out += struct.pack("<IIIII", 2, base, len(sites_hits), readhook.REC_LEN, len(recs))
    for rva, hits in sites_hits:
        out += struct.pack("<II", rva, hits)
    for r in recs:
        # `tick` is the DLL's commit flag, so a fixture that leaves it 0 is an
        # UNCOMMITTED record and readhook drops it. Default it to something
        # non-zero; a test that wants the drop path sets it to 0 explicitly.
        r = dict(r)
        r.setdefault("tick", 1000 + r.get("seq", 0))
        vals = [r.get(k, 0) for k in readhook.FIELDS]
        vals += list(r.get("point", (0, 0, 0, 0)))
        vals += list(r.get("segment", (0, 0, 0, 0)))
        vals += list(r.get("target", (0, 0, 0, 0)))
        out += struct.pack(readhook.REC_FMT, *vals)
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
    v1_fields = readhook._V1
    v1_fmt = "<" + "I" * len(v1_fields) + "I" * (readhook.NPOINT * 3)
    v1 = bytearray(b"MVHK")
    v1 += struct.pack("<IIIII", 1, 0x00400000, 1, struct.calcsize(v1_fmt), 1)
    v1 += struct.pack("<II", 0x1FE950, 1)
    v1rec = {"seq": 0, "tick": 999, "site": 0, "retaddr": 0x00602AD8, "arg2": 0}
    v1 += struct.pack(v1_fmt, *([v1rec.get(k, 0) for k in v1_fields] + [0] * 12))
    v1path = os.path.join(tmp, "v1.bin")
    with open(v1path, "wb") as fh:
        fh.write(bytes(v1))
    v1cap = readhook.Capture(v1path)
    eq(v1cap.version, 1, "4. a v1 capture still parses after the record grew")
    eq(v1cap.stored, 1, "4. and its records survive the version bump")
    check("arg4" not in v1cap.recs[0],
          "4. and a v1 record does NOT sprout the fields it never carried",
          "reading v2 fields out of a v1 record would invent data")

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


def main():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="movehook-test-")
    section_1_2()
    section_3()
    section_4_5(tmp)
    section_6_7(tmp)
    section_9()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
