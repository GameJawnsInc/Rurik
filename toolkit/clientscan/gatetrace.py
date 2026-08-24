"""CANCELWALK-R7: read the local walk-start's GATE OPERANDS at the press.

*** DO NOT POINT THIS AT A CLIENT. IT WILL KILL IT. ***  (2026-08-24)

An adversarial review measured five BLOCKERS in this file on a real WOW64
target, each with a positive control, and every one of them is fatal to the
operator's session rather than merely wrong:

  1. A 64-bit debugger attached to a WOW64 target receives
     STATUS_WX86_SINGLE_STEP (0x4000001E), NOT EXCEPTION_SINGLE_STEP
     (0x80000004). The dispatch below matches ZERO hits, falls through to
     DBG_EXCEPTION_NOT_HANDLED, and the client -- which has no handler --
     is TERMINATED on the first breakpoint hit, i.e. on the first
     PeekMessageW, within one frame of arming, having measured nothing.
     `commandertrap.py` IN THIS DIRECTORY already defines both WX86
     constants and its header already explains this exact failure. This
     file was modelled on `trnhook/debugread.py`, which carries the same
     latent defect. Grepping the directory first would have prevented it.
  2. `DebugSetProcessKillOnExit(False)` is called BEFORE
     `DebugActiveProcess`, where it fails with ERROR_INVALID_HANDLE and does
     nothing -- so kill-on-exit stays TRUE and any error takes the client
     with it. There is no try/finally, and `keytap.read_at` RAISES rather
     than returning None, so an in-loop raise is a live path.
  3. The debug registers are never cleared on detach. The client is left
     carrying four enabled execute breakpoints with no debugger to receive
     the exception -- the next PeekMessageW kills it.
  4. The control is disarmed through the WOW64 SHADOW while it was armed in
     the NATIVE context, which by this file's own thesis is a different
     register set. Both outcomes are silent.
  5. No EFLAGS.RF, so a hardware execute breakpoint re-faults on the same
     instruction forever: measured 230,759 traps in 8 s against the 8 the
     victim's real executions warranted.

AND THE REASON IT EXISTS IS ALSO WRONG. The claim that these operands need a
breakpoint -- "they live on an object movetap cannot resolve and are read and
discarded inside one frame" -- is false on both halves. They are PERSISTENT
OBJECT FIELDS, and the object is two dereferences from a `ctx` that
`movetap.resolve()` already returns: MOVE-DISPATCH's own first instructions
are `call 0x0047F660 / mov eax,[eax+0x2C] / mov esi,[eax+0x680]`. **The poll
is built and shipped -- `movetap.controller_read()`, CANCELWALK-R7's operands
without a debugger at all.** Use that.

WHAT THIS FILE IS STILL FOR, and why it is kept rather than deleted: a poll
at ~11 Hz cannot see a bit that is SET and CLEARED inside one frame. If the
movetap read comes back with the gates clear at a frozen press, that residual
is the remaining question and a trap is the only way to close it. Reviving
this file means fixing all five blockers -- and the right way is to delete the
hand-rolled debugger loop below and drive `commandertrap.py`'s `HwTrap`, which
already has the WX86 codes, EFLAGS.RF, a runaway guard, disarm-all and a
tested detach. The pure half (`gate_verdict`, `reconcile`, `run_verdict`) and
its guard are sound and survive as-is; it is only the process half that is
unsafe.

    python toolkit/clientscan/gatetrace.py --selftest        # safe, no client
    python toolkit/clientscan/gatetrace.py <pid> [seconds]   # REFUSED, see above

WHAT THIS ANSWERS, and why nothing cheaper can. The arc's question is why a
movement key pressed mid-cast sometimes does not walk the player. Every wire
hypothesis is closed (CANCELWALK.md 7.1-7.2: the pre-press inventories are at
value parity and the cancel-instant answer is byte-identical between a press
that froze and one that walked). Every state `movetap` can sample is closed too
(7.4d: the sharpest pair matches on all of them). What is left is the applier's
own gate operands, which live on a DIFFERENT OBJECT that movetap does not
resolve, and which are read and discarded inside one frame. So they have to be
caught at the instruction that reads them.

THE FUNCTION AND ITS GATES, all OBSERVED and twice-verified from build 38797
(CANCELWALK-F10, and the adversarial re-read that confirmed it
instruction-by-instruction):

    0x0081A8F0  the local walk-start applier, thiscall, ecx = the controller
                (`this == context->playerControlledChar`, its own assert at
                0x0081AD1A/0x0081AD22, ChCliBase.cpp line 164)
    0x0081A931  GATE A   test eax,0x100        eax = [this+0x10C]  SET -> bail
    0x0081A93C  GATE B   test byte[ebx+0x64],1                     SET -> bail
    0x0081A946  GATE C   shr eax,4 / not / test al,1               SET -> bail
    0x0081A96C  the navmesh query 0x709D30; a 0 return exits at 0x0081ACFA
    0x0081AD0F  the shared bail for A, B and C
    0x0081ACFA  the navmesh-empty exit

WHY THE ENTRY READ IS THE MEASUREMENT AND THE EXITS ARE THE CHECK. At the entry
breakpoint `ecx` is the controller, so both operands can be read with an
ordinary cross-process read and ALL THREE gates evaluated here, in Python,
before the client has branched. The exit breakpoints then say which way it
actually went. That is a check the artifact can refute: if this file computes
"gate A bails" and the client leaves through the navmesh exit instead, the
model is wrong and the row says so (`agrees: false`). A tool that only watched
the exits could never notice.

Do NOT try to tell a gate bail from a success by the RETURN VALUE. Measured:
the gate bail at 0x0081AD0F calls 0x005FCA80 and returns 1, and the SUCCESS
path also returns 1; only the navmesh-empty exit returns 0. The return value
does not separate the two cases the arc cares about.

THE CONTROL IS NOT OPTIONAL, and this file inherits that rule from
`debugread.py`, which earned it: a DLL-hosted vectored handler NEVER receives
the hardware-breakpoint exception in a WOW64 process (49 verified threads, zero
hits, two commits of conclusions retracted). The debug-register exception is
raised on the 64-bit side and must be collected there -- `DebugActiveProcess` +
`WaitForDebugEvent` from this 64-bit interpreter, with the breakpoints armed in
the NATIVE context (`Wow64SetThreadContext` writes the 32-bit SHADOW, which is
not where the CPU keeps Dr0-Dr7). Dr3 therefore watches `PeekMessageW`, which
any Windows game loop calls every frame:

    control fires, applier does not  -> the route WORKS and the applier really
                                        did not run; a real measurement
    control never fires              -> THE RUN IS VOID. It says nothing about
                                        the client, and this file refuses to
                                        summarise it as if it did
    applier fires                    -> the operands are in the row

`DebugSetProcessKillOnExit(FALSE)` so detaching leaves the client alive. The
control disarms itself after one hit so it cannot flood the loop.

SCOPE. Read-only against the client: no code is patched, nothing is written
into the process, and the only writes anywhere are this file's own capture
under the vault. The applier is not a per-frame function -- one direct caller
(0x00816470) and 8 firings in the 60 s of the R5 run -- so the debugger loop is
cheap. It is loopback-only tooling by construction: it needs a pid, and the
only client this repo ever attaches to is the one the harness launched.
"""
import argparse
import ctypes
import json
import os
import struct
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, os.path.join(HERE, "trnhook"))

# --- the addresses, as VAs from the study, converted once -------------------
# RVA = VA - IMAGE_BASE, and the runtime address is module_base + RVA so ASLR
# is handled. Written as VAs because that is what every line of CANCELWALK.md
# and every codescan invocation quotes; a table of bare RVAs would not be
# checkable against the document that derived them.
IMAGE_BASE = 0x00400000
VA_APPLIER = 0x0081A8F0        # entry; ecx = the controller
VA_GATE_BAIL = 0x0081AD0F      # A, B and C all land here
VA_NAVMESH_EXIT = 0x0081ACFA   # the navmesh query returned 0

# The operands, on the CONTROLLER object (NOT the agent -- ChCliBase+0x64 is a
# different field from AgAgent+0x64 and from the AgentView's +0x64; conflating
# them is a named trap in CANCELWALK-F10).
OFF_STATUS = 0x10C             # the word GATE A and GATE C test
OFF_FLAGBYTE = 0x64            # the byte GATE B tests
BIT_GATE_A = 0x100             # suppress-self-walk; read at only two sites
BIT_GATE_C = 0x10              # the same bit MOVE-DISPATCH tests before sending
BIT_GATE_B = 0x01

# `mt` (movement type 1..8) is the applier's last argument. MOVE-DISPATCH
# pushes it first of four, so at the entry breakpoint -- before the prologue --
# it sits at [esp+0x10] with the return address at [esp+0].
ARG_MT_ESP_OFF = 0x10

BUILD = 38797                  # the build every address above was read from

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

CTX_SIZE = 1232
CONTEXT_AMD64 = 0x00100000
CONTEXT_DEBUG_REGISTERS_64 = CONTEXT_AMD64 | 0x10
OFF_FLAGS, OFF_DR0, OFF_DR7 = 0x30, 0x48, 0x70
# L0|L1|L2|L3, every slot execute/1-byte (the RW and LEN nibbles stay zero).
DR7_FOUR_EXEC = 0x55

k32 = ctypes.windll.kernel32


# --------------------------------------------------------------------------
# THE PURE HALF. Everything below this line up to the debugger loop decides
# things from numbers and can be driven without a client, which is what
# test_gatetrace.py does. The tree's rule: a verdict nobody can reproduce from
# the row it ships with is a verdict nobody can audit.
# --------------------------------------------------------------------------
GATE_A, GATE_B, GATE_C = "A:suppress-self-walk", "B:flagbyte0", "C:bit4"
EXIT_GATE_BAIL, EXIT_NAVMESH, EXIT_UNSEEN = "gate-bail", "navmesh-empty", "none"


def gate_verdict(status_word, flag_byte):
    """Pure: the three gates, evaluated exactly as the applier evaluates them.

    `status_word` is [controller+0x10C], `flag_byte` is byte[controller+0x64].
    Returns which gates BAIL (SET means bail for all three) and which one the
    client would hit FIRST -- order matters because the applier tests A, then
    B, then C, and only the first one reached explains the frame.

    GATE C is special and the row says so: MOVE-DISPATCH tests the SAME bit
    before it sends 0x003D (0x008163BD), so a press that reached the wire
    proves bit 4 was clear. C bailing here would mean the two reads disagree
    within one frame, which is a finding about the model, not about the press.
    """
    if status_word is None or flag_byte is None:
        return {"gates_bail": None, "first_bail": None, "predicted_exit": None,
                "why": "operands-unread"}
    bail = []
    if status_word & BIT_GATE_A:
        bail.append(GATE_A)
    if flag_byte & BIT_GATE_B:
        bail.append(GATE_B)
    if status_word & BIT_GATE_C:
        bail.append(GATE_C)
    return {"gates_bail": bail,
            "first_bail": bail[0] if bail else None,
            # No gate set does NOT mean the body walks: the navmesh query and
            # the dedup sit downstream, and either can still produce no walk.
            # Predict only what the gates decide.
            "predicted_exit": EXIT_GATE_BAIL if bail else None,
            "why": "gates-read"}


def reconcile(verdict, observed_exit):
    """Pure: did the client leave the way the operand read said it would?

    This is the file's own falsifier. `observed_exit` is one of the EXIT_*
    constants. Returns (agrees, note). A row where the gates say "bail" and the
    client left through the navmesh exit is the model being wrong, and it is
    reported rather than smoothed: the whole point of reading operands at the
    entry is that the exits can contradict them.
    """
    if verdict.get("why") != "gates-read":
        return None, "operands-unread"
    predicted = verdict["predicted_exit"]
    if observed_exit == EXIT_UNSEEN:
        # The applier ran and neither exit breakpoint fired: it reached the
        # success path (or an exit this file does not watch).
        return (predicted is None), (
            "no gate set and no bail seen -- the applier ran through"
            if predicted is None else
            f"{verdict['first_bail']} was SET but no bail exit fired")
    if predicted is None and observed_exit == EXIT_NAVMESH:
        return True, "gates all clear and the navmesh query came back empty"
    if predicted == EXIT_GATE_BAIL and observed_exit == EXIT_GATE_BAIL:
        return True, f"{verdict['first_bail']} bailed, as the operands said"
    return False, (f"operands predicted {predicted or 'no bail'} but the "
                   f"client left via {observed_exit}")


def run_verdict(control_hits, applier_hits):
    """Pure: is this run READABLE at all? Returns (rc, headline).

    The control rule from `debugread.py`, enforced rather than described. A run
    whose control never fired cannot distinguish "the applier did not run" from
    "the breakpoints never worked", and the second is this route's OWN known
    failure mode -- so it is a refusal (rc 2), never a null.
    """
    if not control_hits:
        return 2, ("VOID: the PeekMessageW control never fired, so the "
                   "breakpoint route did not deliver. This run says NOTHING "
                   "about the client -- do not record it as a null.")
    if not applier_hits:
        return 1, ("READABLE and EMPTY: the control fired but the applier "
                   "never ran. That is a real measurement -- no movement key "
                   "edge reached 0x0081A8F0 in the window.")
    return 0, f"READABLE: {applier_hits} applier hit(s)."


def resolve_addrs(module_base):
    """Pure: VA table -> runtime addresses for a module loaded at `base`."""
    return {name: module_base + (va - IMAGE_BASE) for name, va in (
        ("applier", VA_APPLIER), ("gate_bail", VA_GATE_BAIL),
        ("navmesh_exit", VA_NAVMESH_EXIT))}


# --------------------------------------------------------------------------
# THE PROCESS HALF.
# --------------------------------------------------------------------------
class EXCEPTION_RECORD(ctypes.Structure):
    pass


EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", wintypes.DWORD), ("ExceptionFlags", wintypes.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", ctypes.c_void_p),
    ("NumberParameters", wintypes.DWORD),
    ("ExceptionInformation", ctypes.c_void_p * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD),
                ("dwFirstChance", wintypes.DWORD)]


class DEBUG_EVENT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("Exception", EXCEPTION_DEBUG_INFO),
                    ("pad", ctypes.c_byte * 256)]
    _fields_ = [("dwDebugEventCode", wintypes.DWORD),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD), ("u", _U)]


def _ctx_buf():
    raw = ctypes.create_string_buffer(CTX_SIZE + 16)
    addr = ctypes.addressof(raw)
    return raw, addr + ((16 - (addr % 16)) % 16)


def _put(p, off, val):
    ctypes.memmove(p + off, struct.pack("<Q", val), 8)


def _get(p, off):
    b = (ctypes.c_char * 8).from_address(p + off)
    return struct.unpack("<Q", bytes(b))[0]


def arm_native(tid, slots):
    """Arm Dr0..Dr3 in the NATIVE context. Returns (accepted, verified).

    `slots` is four absolute addresses. The read-back is against the NATIVE
    context on purpose: arming the WOW64 shadow and reading the shadow back is
    a check that passes while the CPU holds nothing, which is the exact failure
    `debugread.py`'s header records.
    """
    import arm64
    h = k32.OpenThread(arm64.THREAD_ACCESS, False, tid)
    if not h:
        return False, False
    raw, p = _ctx_buf()
    k32.SuspendThread(h)
    try:
        ctypes.memset(p, 0, CTX_SIZE)
        ctypes.memmove(p + OFF_FLAGS,
                       struct.pack("<I", CONTEXT_DEBUG_REGISTERS_64), 4)
        if not k32.GetThreadContext(h, ctypes.c_void_p(p)):
            return False, False
        for i, addr in enumerate(slots):
            _put(p, OFF_DR0 + 8 * i, addr)
        _put(p, OFF_DR7, (_get(p, OFF_DR7) & ~0xFFFFFF00) | DR7_FOUR_EXEC)
        ctypes.memmove(p + OFF_FLAGS,
                       struct.pack("<I", CONTEXT_DEBUG_REGISTERS_64), 4)
        if not k32.SetThreadContext(h, ctypes.c_void_p(p)):
            return False, False
        raw2, p2 = _ctx_buf()
        ctypes.memset(p2, 0, CTX_SIZE)
        ctypes.memmove(p2 + OFF_FLAGS,
                       struct.pack("<I", CONTEXT_DEBUG_REGISTERS_64), 4)
        if k32.GetThreadContext(h, ctypes.c_void_p(p2)):
            return True, _get(p2, OFF_DR0) == slots[0]
        return True, False
    finally:
        k32.ResumeThread(h)
        k32.CloseHandle(h)


def _disarm_slot(h, arm64, index):
    """Turn off one Dr slot on a thread (used to silence the control)."""
    c = arm64.WOW64_CONTEXT()
    c.ContextFlags = arm64.WOW64_CONTEXT_DEBUG_REGISTERS
    if not k32.Wow64GetThreadContext(h, ctypes.byref(c)):
        return
    c.Dr7 &= ~(1 << (2 * index))
    c.ContextFlags = arm64.WOW64_CONTEXT_DEBUG_REGISTERS
    k32.Wow64SetThreadContext(h, ctypes.byref(c))


# The five measured blockers, as a refusal rather than a warning. A file whose
# header says "do not run this" and whose main() runs it anyway is a file that
# gets run: the operator types the command the docstring shows. Clearing this
# flag is the deliberate act of someone who has fixed the process half.
UNSAFE_TO_RUN = (
    "gatetrace's debugger loop is REFUSED: an adversarial review measured five "
    "blockers on a real WOW64 target, and the first one KILLS THE CLIENT on "
    "the first breakpoint hit (it dispatches on EXCEPTION_SINGLE_STEP, but a "
    "64-bit debugger attached to a WOW64 target receives "
    "STATUS_WX86_SINGLE_STEP 0x4000001E, so every hit is handed back to a "
    "client that has no handler for it). The others: kill-on-exit is set "
    "before the attach where it no-ops, the debug registers are never cleared "
    "on detach, the control is disarmed through the wrong context, and "
    "EFLAGS.RF is never set so the breakpoint re-faults ~29,000 times a "
    "second. See this module's docstring.\n\n"
    "USE THE POLL INSTEAD -- it needs no debugger and is already shipped:\n"
    "    python toolkit/clientscan/movetap.py --seconds 180\n"
    "whose rows now carry ctrl_status / ctrl_flagbyte / gate_a / gate_b / "
    "gate_c / walk_suppressed, the same operands this file was built to trap. "
    "Only revive this file if the poll shows the gates CLEAR at a frozen "
    "press, and revive it on commandertrap.py's HwTrap rather than on the "
    "loop below.")


def trace(pid, budget, out_path):
    """The run. Returns (rc, summary dict). REFUSES while UNSAFE_TO_RUN is set."""
    if UNSAFE_TO_RUN:
        raise SystemExit(UNSAFE_TO_RUN)
    import arm64
    import inject
    import keytap

    base = keytap.module_base(pid, "Gw.exe")
    if not base:
        raise SystemExit(f"Gw.exe not found in pid {pid}")
    addr = resolve_addrs(base)
    ub, ur = inject.export_rva(pid, "USER32.DLL", "PeekMessageW")
    control = ub + ur
    slots = [addr["applier"], addr["gate_bail"], addr["navmesh_exit"], control]
    print(f"Gw.exe base 0x{base:08X} (build {BUILD} addresses)")
    for k, v in addr.items():
        print(f"  {k:13} 0x{v:08X}")
    print(f"  {'CONTROL':13} 0x{control:08X}  PeekMessageW")

    k32.DebugSetProcessKillOnExit(False)
    if not k32.DebugActiveProcess(pid):
        raise SystemExit(f"DebugActiveProcess failed: {ctypes.GetLastError()} "
                         f"(this needs an elevated shell)")
    print("attached")
    accepted = verified = 0
    for t in arm64.threads_of(pid):
        a, v = arm_native(t, slots)
        accepted += 1 if a else 0
        verified += 1 if v else 0
    print(f"NATIVE arm: {accepted} accepted, {verified} verified by read-back")
    if not verified:
        print("  native arming FAILED -- the result would be void either way")

    rows = []
    control_hits = 0
    pending = None          # the applier hit waiting for its exit
    t0 = time.time()
    ev = DEBUG_EVENT()
    while time.time() - t0 < budget:
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 400):
            continue
        status = DBG_CONTINUE
        if ev.dwDebugEventCode == CREATE_THREAD_DEBUG_EVENT:
            arm_native(ev.dwThreadId, slots)
        elif ev.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
            code = ev.u.Exception.ExceptionRecord.ExceptionCode
            if code == EXCEPTION_SINGLE_STEP:
                h = k32.OpenThread(arm64.THREAD_ACCESS, False, ev.dwThreadId)
                c = arm64.WOW64_CONTEXT()
                c.ContextFlags = (arm64.WOW64_CONTEXT_DEBUG_REGISTERS
                                  | arm64.WOW64_CONTEXT_i386 | 0x1 | 0x2)
                if h and k32.Wow64GetThreadContext(h, ctypes.byref(c)):
                    eip = c.Eip
                    now = round(time.time() - t0, 4)
                    if eip == addr["applier"]:
                        # Close any previous hit that never saw an exit.
                        if pending is not None:
                            rows.append(_close(pending, EXIT_UNSEEN))
                        this = c.Ecx
                        sw = keytap.read_at(pid, this + OFF_STATUS, 4)
                        fb = keytap.read_at(pid, this + OFF_FLAGBYTE, 1)
                        mt = keytap.read_at(pid, c.Esp + ARG_MT_ESP_OFF, 4)
                        pending = {
                            "kind": "applier", "t": now, "tid": ev.dwThreadId,
                            "this": this,
                            "status_word": (int.from_bytes(sw, "little")
                                            if sw else None),
                            "flag_byte": fb[0] if fb else None,
                            "mt": (int.from_bytes(mt, "little")
                                   if mt else None),
                        }
                        print(f"  [{now:7.3f}] APPLIER this=0x{this:08X} "
                              f"+0x10C={pending['status_word']} "
                              f"+0x64={pending['flag_byte']} "
                              f"mt={pending['mt']}")
                    elif eip in (addr["gate_bail"], addr["navmesh_exit"]):
                        which = (EXIT_GATE_BAIL if eip == addr["gate_bail"]
                                 else EXIT_NAVMESH)
                        if pending is not None:
                            rows.append(_close(pending, which))
                            pending = None
                        else:
                            rows.append({"kind": "orphan-exit", "t": now,
                                         "exit": which})
                        print(f"  [{now:7.3f}] EXIT {which}")
                    elif eip == control:
                        control_hits += 1
                        print(f"  [{now:7.3f}] CONTROL fired -- the "
                              f"breakpoint route DELIVERS; disarming it")
                        _disarm_slot(h, arm64, 3)
                if h:
                    k32.CloseHandle(h)
            elif code != EXCEPTION_BREAKPOINT:
                status = DBG_EXCEPTION_NOT_HANDLED
        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, status)

    if pending is not None:
        rows.append(_close(pending, EXIT_UNSEEN))
    k32.DebugActiveProcessStop(pid)
    print("detached")

    applier_rows = [r for r in rows if r["kind"] == "applier"]
    rc, headline = run_verdict(control_hits, len(applier_rows))
    summary = {"kind": "summary", "rc": rc, "headline": headline,
               "control_hits": control_hits, "applier_hits": len(applier_rows),
               "build": BUILD, "pid": pid, "base": base,
               "threads_armed": accepted, "threads_verified": verified}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "head", "pid": pid, "build": BUILD,
                             "base": base, "addrs": addr,
                             "control": control}) + "\n")
        for r in rows:
            fh.write(json.dumps(r) + "\n")
        fh.write(json.dumps(summary) + "\n")
    print(f"\n{headline}")
    for r in applier_rows:
        print(f"  t={r['t']:7.3f} mt={r['mt']} "
              f"gates_bail={r['gates_bail']} exit={r['exit']} "
              f"agrees={r['agrees']}  {r['note']}")
    print(f"\nwrote {out_path}")
    return rc, summary


def _close(pending, observed_exit):
    """Finish an applier row once its exit is known (or known to be absent)."""
    v = gate_verdict(pending["status_word"], pending["flag_byte"])
    agrees, note = reconcile(v, observed_exit)
    row = dict(pending)
    row.update(v)
    row["exit"] = observed_exit
    row["agrees"] = agrees
    row["note"] = note
    return row


def default_out():
    import vaultpath
    return os.path.join(vaultpath.require_dir(), "captures", "gatetrace",
                        "gatetrace-" + time.strftime("%Y%m%dT%H%M%S")
                        + ".jsonl")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pid", nargs="?", type=int)
    ap.add_argument("seconds", nargs="?", type=int, default=120)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.selftest:
        import test_gatetrace
        return test_gatetrace.main()
    if a.pid is None:
        print(__doc__)
        return 2
    rc, _ = trace(a.pid, a.seconds, a.out or default_out())
    return rc


if __name__ == "__main__":
    sys.exit(main())
