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

# 14 = the MANDATORY core, counted from a real green run: 5 in section 1, 3 in
# section 5, 6 in section 6, none of which need the vault or a 32-bit Windows.
# A whole green run is 29; sections 2 (8), 3 (5) and 4 (2) declare skips instead,
# which is `checks.py`'s own guidance -- "set the floor to its mandatory core and
# let the optional sections declare skips."
LEDGER = checks.Ledger("commandertrap", floor=14)

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
    except Exception as ex:
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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
