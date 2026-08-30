"""Prove the hardware-breakpoint trap FIRES, and refuses when it cannot see.

THE FAILURE THIS IS AGAINST. `commandertrap.py` answers a question of the form
"does this instruction ever execute", and the interesting answer is NO. That is
the worst possible shape for a tool to be silently broken in: a trap that arms
nothing, arms the wrong bitness' CONTEXT, or arms a thread the code never runs
on produces **exactly the same output as the finding** -- no hits -- and the
finding is dramatic. `studies/heroes/FINDINGS.md` 28 is this arc's worked
example of believing one of those: a subscriber reader confidently reported
that a demonstrably-live event had no subscriber.

So the machinery is exercised against a process this machine controls, where
the right answer is KNOWN:

  1  DR7 encoding, and it must be execute-length-1, not a data breakpoint
  2  every site's bytes match the 38833 image ON DISK -- a typo'd address is
     caught here, without a client
  3  THE CONTROL: spawn a real 32-bit process, breakpoint the entry point the
     OS itself hands us, and require the hit. This is the whole reason the
     debugger is a separate generic class from the hero sites.
  4  a site whose bytes do not match is REFUSED against a live process
  5  the verdict refuses when its control site did not fire
  6  the capture decoders, including the filter verdict that is the headline

3 and 4 need `C:\\Windows\\SysWOW64\\cmd.exe`; 2 needs the vaulted 38833
client. Each skips with its reason rather than passing vacuously.

    python toolkit/clientscan/test_commandertrap.py
"""
import io
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, HERE)
import checks                                                   # noqa: E402

# THE MANDATORY CORE, counted from a real green run (2026-08-23, 71 checks):
#   §1  5   DR7 encoding                     process-free
#   §5  3   the verdict's control gate       process-free
#   §6  6   the capture decoders             process-free
#   §7  5   coverage, both samples           process-free
#   §8 12   the watchpoint's encoding        process-free
#   -----   = 31, and that is the floor.
# The rest need something this machine may not have and declare skips instead,
# per `checks.py`'s own guidance: §2 (21) the vaulted 38833 client, §3 (7),
# §3b (4), §4 (2) and §9 (6) a 32-bit `cmd.exe`. A whole green run is 71.
# Ladder: 14 -> 26 -> 27 -> 29 -> 31, each step re-read off a green run and
# never guessed.
#
# AND THE CORE IS NOW MEASURED, 2026-08-30, not just arithmetic. Two runs:
#   * no vault, this machine's 32-bit cmd.exe present:
#     **50 checks, 1 declared skip (§2), rc=0** -- 71 - 21, as the table says.
#   * no vault AND `WOW64_CMD` pointed at a path that does not exist:
#     **31 checks, 5 declared skips (§2, §3, §3b, §4, §9), rc=0** -- exactly
#     the floor, with zero slack. The core above was right to the check.
# Before that day neither run reached a verdict: `pinned.find()` raises
# `SystemExit`, which the `except Exception` at §2 did not catch, so §1 printed
# its five PASSes and the file then died with rc=1 and no banner at all.
LEDGER = checks.Ledger("commandertrap", floor=31)

WOW64_CMD = r"C:\Windows\SysWOW64\cmd.exe"


def main():
    import commandertrap as ct

    # ---- 1. DR7 -----------------------------------------------------------
    print("1. DR7 encoding")
    LEDGER.ok(ct.dr7_for(0) == 0, "no slots -> 0")
    LEDGER.ok(ct.dr7_for(1) == 0b01, "one slot -> L0", f"{ct.dr7_for(1):#b}")
    LEDGER.ok(ct.dr7_for(4) == 0b01010101, "four slots -> L0..L3",
              f"{ct.dr7_for(4):#b}")
    # The check that matters: the R/W and LEN fields (bits 16..31) must be ZERO.
    # A 1 in R/W turns an execute breakpoint into a data breakpoint on the same
    # address, which does not error -- it fires on reads of the instruction and
    # never on its execution.
    LEDGER.ok(ct.dr7_for(4) >> 16 == 0,
              "and bits 16+ are zero: execute, length 1",
              "a nonzero R/W field is a DATA breakpoint wearing this one's "
              "address")
    try:
        ct.dr7_for(5)
        LEDGER.ok(False, "five slots refused", "IT ACCEPTED FIVE")
    except ct.TrapError:
        LEDGER.ok(True, "five slots refused -- the processor has four")

    # ---- 2. the site table against the image on disk ----------------------
    print("\n2. the site bytes, against the 38833 image")
    try:
        sys.path.insert(0, TOOLKIT)
        from gwpe import PE
        import pinned
        path, why = pinned.find(38833)
        pe = PE(path)
    except (Exception, SystemExit) as ex:                       # noqa: BLE001
        # SystemExit, and it has to be named: `pinned.find()` RAISES one when
        # the build is not in the vault, and `Exception` does not catch it --
        # so on a machine without the vault this file printed section 1 and
        # then DIED with rc=1 and no verdict, rather than skipping section 2
        # and running the process-free core the floor above describes.
        LEDGER.skip("section 2", f"needs the vaulted 38833 client: {ex}")
    else:
        print(f"   {path}\n   ({why})")
        checked = 0
        for name, site in ct.SITES.items():
            if site.code is None:
                continue
            off = pe.rva_to_off(site.va - pe.image_base)
            with open(path, "rb") as fh:
                fh.seek(off)
                got = fh.read(len(site.code))
            LEDGER.ok(got == site.code,
                      f"{name:9} 0x{site.va:08X} = {site.code.hex()}",
                      f"image has {got.hex()}")
            checked += 1
        LEDGER.ok(checked >= 6, f"{checked} sites carry verifiable bytes",
                  "a site with no `code` cannot be checked against anything")

    # ---- 3. THE CONTROL: does a breakpoint actually fire? -----------------
    print("\n3. the machinery, against a 32-bit process we control")
    if not os.path.isfile(WOW64_CMD):
        LEDGER.skip("section 3", f"no {WOW64_CMD} -- cannot make a 32-bit "
                                 f"target, so the trap is UNPROVEN here")
    else:
        state = {"entry": None}

        def on_create(trap, info):
            # The OS hands us the image entry point. It is guaranteed to
            # execute, and we did not have to know anything about cmd.exe to
            # pick it -- which is what makes this a control and not a second
            # copy of the thing under test.
            state["entry"] = int(info.lpStartAddress)
            return [state["entry"]]

        trap = ct.HwTrap(on_create=on_create)
        trap.spawn(WOW64_CMD, "/c exit")
        try:
            # NO stop_when. The first version of this section stopped at the
            # first hit, which proved the breakpoint FIRES and said nothing
            # about whether the target RESUMES past it -- and that was the half
            # that was broken. Run to process exit instead: the entry point
            # executes exactly once, so anything above one hit is us re-trapping
            # an instruction that never retired.
            trap.pump(30.0)
        finally:
            trap.detach()
        LEDGER.ok(state["entry"], "the OS gave us an entry point",
                  f"0x{(state['entry'] or 0):08X}")
        LEDGER.ok(len(trap.hits) >= 1,
                  "AND THE BREAKPOINT FIRED at it",
                  "NO HIT. Every 'the instruction never executed' answer this "
                  "tool can give is now worthless -- that is this section's "
                  "entire job")
        # THE RESUME. An entry point runs once, so more than one hit means the
        # instruction never retired and we re-trapped it -- which is exactly
        # what the first live run did, 32 times in 4ms, and it read as "this
        # site executed 32 times" rather than as a broken resume.
        LEDGER.ok(len(trap.hits) == 1,
                  "EXACTLY ONCE -- the target resumed past the breakpoint",
                  f"{len(trap.hits)} hits on an entry point that runs once: "
                  f"EFLAGS.RF is not being honoured and every hit COUNT this "
                  f"tool reports is a count of our own re-entries")
        LEDGER.ok(trap.exited and not trap.resume_failures,
                  "and the process ran on to a normal exit",
                  f"exited={trap.exited} resume_failures={trap.resume_failures}")
        if trap.hits:
            h = trap.hits[0]
            LEDGER.ok(h["addr"] == state["entry"],
                      "at the address we armed, not another",
                      f"0x{h['addr']:08X} vs 0x{state['entry']:08X}")
            LEDGER.ok(h["ctx"] is not None and h["ctx"].Eip == state["entry"],
                      "and the thread's EIP agrees with it",
                      "EIP is how a hit is attributed to a site; if it were "
                      "wrong every site label in a report would be too")
            LEDGER.ok(h["dr6_agrees"],
                      "and DR6's slot bit agrees with EIP",
                      f"DR6 says slot {h['dr6_slot']}, EIP says {h['slot']} -- "
                      f"an independent cross-check, and it disagreed")

    # ---- 3b. DEFERRED arming ----------------------------------------------
    print("\n3b. deferred arming: a site that goes live only on a trigger")
    if not os.path.isfile(WOW64_CMD):
        LEDGER.skip("section 3b", "needs the 32-bit cmd.exe target")
    else:
        # THE HAZARD THIS COVERS: a deferred site that never arms is SILENT,
        # and silence is exactly what a real negative looks like. `lookup` is
        # deferred, and its whole purpose is to report "no subscriber" -- so a
        # deferral bug would manufacture that finding out of nothing.
        # Checked by READING THE DEBUG REGISTERS BACK out of the live thread,
        # not by watching a second address execute. The obvious behavioural
        # version -- trigger at the entry point, dependent at entry+1 -- cannot
        # work and it is worth writing down why: a hardware execute breakpoint
        # fires on an instruction's FIRST byte, and entry+1 is in the middle of
        # one, so it would be silent for a reason that has nothing to do with
        # deferral. `armed_now()` reads the registers the processor will
        # actually consult, so this is target state rather than a mock.
        st = {}

        def on_create2(trap, info):
            e = int(info.lpStartAddress)
            st["entry"] = e
            return [e, e + 0x20]

        t2 = ct.HwTrap(on_create=on_create2)
        t2.spawn(WOW64_CMD, "/c exit")
        t2.deferred = {1: 0}          # slot 1 arms when slot 0 fires
        t2.disarmed = {1}             # ...and starts down
        after = {}
        try:
            t2.pump(30.0, stop_when=lambda t: bool(t.hits))
            if t2.hits:
                h = t2.threads.get(t2.hits[0]["tid"])
                if h:
                    after["dr"] = t2.armed_now(h)
        finally:
            t2.detach()
        slots = [x["slot"] for x in t2.hits]
        LEDGER.ok(slots[:1] == [0],
                  "the deferred slot is SILENT until its trigger fires",
                  f"slots in order: {slots} -- slot 1 firing first would mean "
                  f"it was live all along")
        dr = after.get("dr")
        LEDGER.ok(dr and dr[1] == st["entry"] + 0x20,
                  "the trigger loads the deferred address into DR1",
                  f"DR1 = 0x{(dr[1] if dr else 0):08X}, wanted "
                  f"0x{(st.get('entry', 0) + 0x20):08X}")
        LEDGER.ok(dr and (dr[4] & 0b0100),
                  "and sets its ENABLE bit in DR7 -- it is genuinely live",
                  f"DR7 = {(dr[4] if dr else 0):#b}; without L1 the address sits "
                  f"in DR1 doing nothing, which is silence again")
        LEDGER.ok(1 not in t2.disarmed,
                  "and the bookkeeping agrees it is no longer disarmed")

    # ---- 4. a wrong site is refused against a live process ----------------
    print("\n4. byte verification refuses a wrong site")
    if not os.path.isfile(WOW64_CMD):
        LEDGER.skip("section 4", "needs the 32-bit cmd.exe target")
    else:
        # A PLAIN child, not one under the debugger. `verify_sites` is a memory
        # read and owes the debug loop nothing -- spawning it debugged left the
        # process stopped at its first debug event with no module list yet, and
        # the snapshot failed with ERROR_PARTIAL_COPY. Testing two mechanisms
        # through each other is how a green section stops meaning anything.
        import subprocess
        child = subprocess.Popen([WOW64_CMD, "/c", "ping -n 4 127.0.0.1 >nul"],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        pid = child.pid
        try:
            time.sleep(0.6)
            import keytap
            base = keytap.module_base(pid, "cmd.exe")
            real = keytap.read_at(pid, base + 0x1000, 6)
            good = ct.Site("good", ct.IMAGE_BASE + 0x1000, real, "as read")
            bad = ct.Site("bad", ct.IMAGE_BASE + 0x1000,
                          bytes(b ^ 0xFF for b in real), "deliberately wrong")
            _, res = ct.verify_sites(pid, [good, bad], module="cmd.exe")
            LEDGER.ok(res[0][1] is True, "the site whose bytes match passes",
                      "otherwise section 4 proves only that it always refuses")
            LEDGER.ok(res[1][1] is False,
                      "and the site whose bytes do not match is REFUSED",
                      "this is the cross-build guard -- 24 read a 38797 address "
                      "in a 38833 binary in this very arc")
        finally:
            child.kill()
            child.wait(timeout=5)

    # ---- 5. the verdict's control gate ------------------------------------
    print("\n5. the verdict refuses without its control")
    sites = [ct.SITES[n] for n in ct.DEFAULT_SITES]
    buf = io.StringIO()
    rc = ct._verdict({"worker": 0, "raise": 0, "case93": 0, "filter": 0},
                     sites, out=buf)
    LEDGER.ok(rc == 2 and "REFUSING TO ANSWER" in buf.getvalue(),
              "control never fired -> no verdict",
              "an unfired control and a real negative look identical, which is "
              "28's lesson and the reason this gate exists")
    buf2 = io.StringIO()
    rc2 = ct._verdict({"worker": 1, "raise": 0, "case93": 0, "filter": 0},
                      sites, out=buf2)
    LEDGER.ok(rc2 == 0 and "REFUSING" not in buf2.getvalue(),
              "and it DOES answer once the control fires",
              "otherwise the gate is always-on and proves nothing")
    LEDGER.ok("never raised" in buf2.getvalue()
              or "raise did NOT" in buf2.getvalue(),
              "naming which link of the chain broke",
              buf2.getvalue()[-160:])

    # ---- 6. the capture decoders ------------------------------------------
    print("\n6. the capture decoders")

    class Ctx:
        Esp = 0x0018F000
        Ecx = 0x0AAA0000
        Esi = 0x0BBB0000
        Eax = 22
        Edi = 0x0CCC0000

    mem = {}

    def reader(addr, size):
        return mem.get((addr, size))

    # filter: equal operands -> PASSES; unequal -> REJECTS. This string is the
    # headline of the whole run, so it is worth a test of its own.
    mem[(Ctx.Esi + 4, 8)] = struct.pack("<2I", 22, 2)
    v = ct._cap_filter(Ctx, reader)
    LEDGER.ok(v["VERDICT"].startswith("PASSES") and v["entry+8 heroId"] == 2,
              "filter: owner == my-id reads as PASSES", str(v["VERDICT"]))
    mem[(Ctx.Esi + 4, 8)] = struct.pack("<2I", 200, 2)
    LEDGER.ok(ct._cap_filter(Ctx, reader)["VERDICT"].startswith("REJECTS"),
              "filter: owner != my-id reads as REJECTS")

    # worker: seven args at [esp+4..], in 25.1's order
    mem[(Ctx.Esp, 32)] = struct.pack("<8I", 0xDEAD, 1, 1, 200, 2, 0, 0, 200)
    w = ct._cap_worker(Ctx, reader)
    LEDGER.ok(w["party_id"] == 1 and w["msg+8 owner"] == 1
              and w["msg+0xc agent"] == 200 and w["msg+0x10 heroId"] == 2
              and w["msg+0x14"] == 200,
              "worker: the seven stack args decode in 25.1's order",
              str(w))

    mem[(Ctx.Ecx, 24)] = struct.pack("<6I", 200, 1, 2, 0, 0, 200)
    r = ct._cap_raise(Ctx, reader)
    LEDGER.ok(r["entry+0 agent"] == 200 and r["entry+4 owner"] == 1
              and r["entry+8 heroId"] == 2, "raise: the entry row decodes",
              str(r))

    mem[(Ctx.Edi, 8)] = struct.pack("<2I", 1, 0x0BBB0000)
    LEDGER.ok(ct._cap_case93(Ctx, reader)["payload+4 entry"] == 0x0BBB0000,
              "case93: payload+4 is the entry pointer (26.1)")
    # A read that fails must not fabricate a row.
    LEDGER.ok(ct._cap_raise(type("C", (), {"Ecx": 0x1234, "Esi": 0})(),
                            lambda a, s: None)["entry+0 agent"] is None,
              "and an unreadable entry decodes to None, not to zeros",
              "a zeroed row would read as a real measurement of zeros")

    # ---------------------------------------------------------- coverage
    print("== 7. coverage: a zero hit count needs a witness ==")

    class _FakeTrap:
        """Enough of HwTrap for snapshot_coverage, with no process at all."""

        def __init__(self, addrs, dr_by_tid):
            self.addrs = list(addrs)
            self.threads = {tid: ("h", tid) for tid in dr_by_tid}
            self._dr = dr_by_tid
            self.coverage = None

        def armed_now(self, h):
            return self._dr[h[1]]

        snapshot_coverage = ct.HwTrap.snapshot_coverage

    A, B = 0x00401000, 0x00402000
    cov = _FakeTrap([A, B], {11: (A, B, 0, 0, 0x5),
                             12: (A, B, 0, 0, 0x5)}).snapshot_coverage()
    LEDGER.ok(cov["armed"] == 2 and cov["threads"] == 2 and not cov["bad"],
              "snapshot_coverage passes when every thread's DRs really hold "
              "our addresses -- READ BACK from the registers, never assumed "
              "from a SetThreadContext that returned TRUE", str(cov))

    cov = _FakeTrap([A, B], {11: (A, B, 0, 0, 0x5),
                             12: (A, 0, 0, 0, 0x1)}).snapshot_coverage()
    LEDGER.ok(cov["armed"] == 1 and len(cov["bad"]) == 1
              and "0x402000" in cov["bad"][0][1],
              "and it NAMES the thread missing a site. This is what makes "
              "'the site fired zero times' mean anything: without it, an "
              "unarmed thread and an event that never happened are the same "
              "report", str(cov))

    cov = _FakeTrap([A], {11: None}).snapshot_coverage()
    LEDGER.ok(cov["armed"] == 0 and cov["bad"][0][1] == "context unreadable",
              "a thread whose context cannot be read is reported unreadable "
              "rather than counted as armed")

    # TWO SAMPLES, and the second is the one an execute run never had. Coverage
    # was sampled only at ATTACH, so a run that started covered and lost its
    # registers at hit one -- which is what the resume path did to the row
    # watch -- printed "10 of 10" all the way through. The watch re-check
    # caught that for WATCHES only; execute slots had no equivalent.
    ft = _FakeTrap([A], {11: (A, 0, 0, 0, 0x1)})
    ft.snapshot_coverage()
    ft._dr[11] = (0, 0, 0, 0, 0)          # the registers go away mid-run
    ft.snapshot_coverage(store="coverage_end")
    LEDGER.ok(ft.coverage["armed"] == 1 and ft.coverage_end["armed"] == 0,
              "the two coverage samples are kept APART, so a run that started "
              "covered and ended uncovered cannot report the first number "
              "twice",
              f"attach={ft.coverage} end={ft.coverage_end}")
    buf2 = io.StringIO()
    ct._report([], [], 0x00400000, out=buf2,
               trap=type("T", (), {"bp_first": 0, "bp_second": 0,
                                   "foreign_steps": 0, "other_exceptions": 0,
                                   "arm_failures": 0, "resume_failures": 0,
                                   "capped": set(), "oneshot": set(),
                                   "adopted": None,
                                   "coverage": ft.coverage,
                                   "coverage_end": ft.coverage_end})())
    LEDGER.ok("COVERAGE WAS LOST DURING THE RUN" in buf2.getvalue(),
              "and the report SAYS SO, in those words, rather than printing a "
              "healthy attach-time number above a set of hit counts nobody can "
              "read",
              buf2.getvalue())

    # ------------------------------------------------- data watchpoints
    print("== 8. the DATA watchpoint's encoding and its refusals ==")
    LEDGER.ok(ct.dr7_for(2) == 0b0101 and ct.dr7_for(2) >> 16 == 0,
              "execute-only DR7 is still exactly the enable bits -- the "
              "watchpoint work must not have changed the default",
              f"{ct.dr7_for(2):#b}")
    w = ct.dr7_for(2, ["x", "w"], [4, 4])
    LEDGER.ok((w & 0b1111) == 0b0101 and ((w >> 20) & 0b11) == 0b01
              and ((w >> 22) & 0b11) == 0b11 and ((w >> 16) & 0b1111) == 0,
              "a 4-byte WRITE watch in slot 1 sets R/W=01 and LEN=11 for that "
              "slot and leaves slot 0's fields at 00 -- per-slot, not global",
              f"{w:#x}")
    for kinds, sizes, what in ((["w"], [3], "3-byte watch"),
                               (["q"], [4], "unknown kind")):
        try:
            ct.dr7_for(1, kinds, sizes)
            LEDGER.ok(False, f"{what} must be REFUSED")
        except ct.TrapError as exc:
            LEDGER.ok(True, f"{what} is refused by name, not silently "
                            f"encoded as something else", str(exc))

    class _ArmTrap:
        """arm_watch with no process: only the bookkeeping and the refusals."""

        def __init__(self):
            self.addrs, self.kinds, self.sizes = [0, 0], ["x", "x"], [4, 4]
            self.disarmed = set()
            self.threads = {1: "a", 2: "b"}
            self.watching = {}
            # DR7: L1 enabled (bit 2) and slot 1's R/W = 01 (bits 20-21).
            self.dr = {"a": (0, 0x0AB00044, 0, 0, 0b100 | (0b01 << 20)),
                       "b": (0, 0x0AB00044, 0, 0, 0b100 | (0b01 << 20))}

        def _arm_all(self):
            return len(self.threads)

        def armed_now(self, h):
            return self.dr.get(h)

        arm_watch = ct.HwTrap.arm_watch

    tr = _ArmTrap()
    ok, why = tr.arm_watch(1, 0x0AB00044, 4)
    LEDGER.ok(ok and tr.kinds == ["x", "w"] and tr.addrs[1] == 0x0AB00044
              and "VERIFIED live on 2" in why,
              "arm_watch points one slot at an address discovered mid-run, "
              "and VERIFIES by reading DR0-DR3/DR7 back rather than trusting "
              "a SetThreadContext that returned TRUE", why)
    blind = _ArmTrap()
    blind.dr = {}                      # nothing reads back
    ok, why = blind.arm_watch(1, 0x0AB00044, 4)
    LEDGER.ok(not ok and "VERIFIED on none" in why
              and "would mean nothing" in why,
              "and when the registers do NOT take it fails LOUDLY -- a watch "
              "that silently never armed is indistinguishable from a write "
              "that never happened, which is the whole question it exists to "
              "answer", why)
    ok, why = tr.arm_watch(1, 0x0AB00046, 4)
    LEDGER.ok(not ok and "not 4-byte aligned" in why,
              "and it REFUSES a misaligned address rather than arming it -- a "
              "misaligned DR does not error, it watches the wrong bytes and "
              "then reports silence, which is the worst possible failure for "
              "an instrument whose whole job is to catch a rare write", why)
    ok, why = tr.arm_watch(9, 0x0AB00044, 4)
    LEDGER.ok(not ok and "outside DR0" in why,
              "and refuses a slot the processor does not have")

    # THE ORDERING BUG, pinned. `_exception` reads the context, calls
    # on_hit, then writes the context back -- so anything a handler ARMED was
    # restored to the pre-handler DR state. dr_state() is what the resume path
    # re-stamps from, so it must reflect a mid-run arm_watch.
    tr2 = _ArmTrap()
    tr2.addrs = [0x401000, 0x402000, 0x403000, 0]
    tr2.kinds, tr2.sizes = ["x", "x", "x", "x"], [4, 4, 4, 4]
    tr2.dr_state = ct.HwTrap.dr_state.__get__(tr2)
    before = tr2.dr_state()
    LEDGER.ok(before[3] == 0 and before[4] == 0b010101,
              "three execute slots and an empty fourth give DR7 0x15 -- the "
              "exact state a live run found restored over its watch",
              f"{before[4]:#x}")
    tr2.arm_watch(3, 0x0AB00044, 4)
    after = tr2.dr_state()
    LEDGER.ok(after[3] == 0x0AB00044
              and (after[4] & (1 << 6))
              and ((after[4] >> 28) & 0b11) == 0b01,
              "and after a mid-run arm_watch, dr_state carries the watch -- "
              "so the resume path re-stamps it instead of restoring the old "
              "registers over it, which is what silently killed the first "
              "three watch runs", f"{after[4]:#x}")

    LEDGER.ok(ct.Site("w", 0, None, "why", None, kind="w").code is None
              and ct.Site("x", 1, b"\x90", "why").kind == "x",
              "a watch Site carries kind='w' with no bytes, and an ordinary "
              "Site still defaults to execute -- so nothing that was verified "
              "before stops being verified")

    buf = io.StringIO()
    ct._report([], [], 0x00400000, out=buf,
               trap=type("T", (), {"bp_first": 0, "bp_second": 0,
                                   "foreign_steps": 0, "other_exceptions": 0,
                                   "arm_failures": 0, "resume_failures": 0,
                                   "capped": set(), "oneshot": set(),
                                   "coverage": None})())
    LEDGER.ok("NOT SAMPLED" in buf.getvalue()
              and "not evidence of absence" in buf.getvalue(),
              "and a report with NO coverage snapshot says so IN THOSE WORDS, "
              "rather than printing hit counts that read as complete")

    # ---- 9. ATTACH REPORTS EVERY THREAD THE PROCESS ALREADY HAD -----------
    print("\n9. attaching to a running process: does the loop see its threads?")
    # WHY THIS SECTION EXISTS. On 2026-08-23 `adopt_existing_threads` was added
    # against a MEASUREMENT -- "after attaching to a running client,
    # `self.threads` held one thread" -- and that measurement was taken inside
    # the CREATE_PROCESS handler, the FIRST debug event after attach. One thread
    # at that instant is what you see WHETHER OR NOT the OS goes on to deliver a
    # CREATE_THREAD event per pre-existing thread. The number could not tell
    # "the loop never reports them" from "the loop had not reported them yet",
    # and it was read as the first. It is the second: Windows synthesises the
    # CREATE_THREAD events, the loop reaches every thread on its own, and no run
    # in this repo was ever short of coverage. Pinned here so the claim is a
    # measurement with a control rather than an inference from an event handler.
    #
    # The target is 32-bit, because that is what the client is and `_arm` writes
    # a WOW64_CONTEXT -- a 64-bit target would answer the enumeration half and
    # silently fail the arming half.
    if not os.path.isfile(WOW64_CMD):
        LEDGER.skip("section 9", "needs the 32-bit cmd.exe target")
    else:
        import subprocess
        child = subprocess.Popen([WOW64_CMD, "/c", "ping -n 20 127.0.0.1 >nul"],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        try:
            time.sleep(1.0)
            before = _count_threads(ct, child.pid)
            # THE POSITIVE CONTROL. A single-threaded target agrees with both
            # hypotheses and would make every check below vacuous.
            LEDGER.ok(before >= 3,
                      f"the target already has {before} threads before attach",
                      f"only {before} -- a target this thin cannot distinguish "
                      f"'the loop saw them all' from 'there was one'")

            base = {}

            def on_create3(trap, info):
                # The PE header. Never executed, so nothing can fire; the
                # question is only whether the registers HOLD it.
                base["addr"] = int(info.lpBaseOfImage)
                return [base["addr"]]

            t3 = ct.HwTrap(on_create=on_create3)
            # ADOPTION OFF: let the debug loop answer for itself. With it on,
            # every thread ends up armed either way and the section proves
            # nothing about which mechanism did it.
            t3.adopt_existing_threads = lambda: (0, 0)
            t3.attach(child.pid)
            try:
                t3.pump(4.0)
                seen = len(t3.threads)
                cov = t3.snapshot_coverage()
                fails = t3.arm_failures
            finally:
                t3.detach()

            LEDGER.ok(seen >= before,
                      f"AND THE DEBUG LOOP REACHED ALL {seen} OF THEM "
                      f"UNAIDED -- the OS synthesises CREATE_THREAD on attach",
                      f"the loop saw {seen} of {before}: pre-existing threads "
                      f"are a blind spot after all, and every zero-hit reading "
                      f"taken before adoption existed is unwitnessed")
            LEDGER.ok(cov["armed"] == cov["threads"] and not cov["bad"],
                      f"and every one of the {cov['threads']} holds the armed "
                      f"address -- coverage is complete, read back from the "
                      f"processor",
                      f"armed {cov['armed']} of {cov['threads']}: {cov['bad']}")
            LEDGER.ok(fails == 0,
                      "with no arming failures on any of them",
                      f"{fails} threads refused SetThreadContext")
            end = t3.coverage_end
            LEDGER.ok(end and end["armed"] == end["threads"] and end["threads"],
                      f"and the END-OF-RUN sample says it STAYED covered "
                      f"({end['armed'] if end else 0} of "
                      f"{end['threads'] if end else 0}) -- taken by pump(), "
                      f"while the process is still alive",
                      f"coverage_end={end}")

            # AND THE OTHER HALF: adoption still reports a large `armed` count,
            # because it runs INSIDE the CREATE_PROCESS event before the
            # synthetic ones arrive. That number is the one that was misread.
            t4 = ct.HwTrap(on_create=on_create3)
            t4.attach(child.pid)
            try:
                t4.pump(2.0)
                adopted = t4.adopted
            finally:
                t4.detach()
            LEDGER.ok(adopted and adopted[1] >= 1,
                      f"while adoption reports {adopted} -- found, newly armed. "
                      f"With the check above, that second number is NOT a count "
                      f"of unwatched threads; it is a count of threads the loop "
                      f"had not announced YET",
                      f"adopted={adopted}: if it newly armed none, the misread "
                      f"this section documents could not have happened and its "
                      f"premise is wrong")
        finally:
            child.kill()

    return LEDGER.verdict()


def _count_threads(ct, pid):
    """Toolhelp32's count, as ground truth independent of the debug loop."""
    import ctypes
    n = 0
    snap = ct.kernel32.CreateToolhelp32Snapshot(ct.TH32CS_SNAPTHREAD, 0)
    if snap == ct.INVALID_HANDLE_VALUE:
        return -1
    try:
        te = ct.THREADENTRY32()
        te.dwSize = ctypes.sizeof(ct.THREADENTRY32)
        ok = ct.kernel32.Thread32First(snap, ctypes.byref(te))
        while ok:
            if te.th32OwnerProcessID == pid:
                n += 1
            te.dwSize = ctypes.sizeof(ct.THREADENTRY32)
            ok = ct.kernel32.Thread32Next(snap, ctypes.byref(te))
    finally:
        ct.kernel32.CloseHandle(snap)
    return n


if __name__ == "__main__":
    sys.exit(main())
