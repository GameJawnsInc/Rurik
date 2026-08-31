"""Prove the live commander reader refuses to answer when its instrument is wrong.

`commanderpeek.py` reads a LIVE client, so almost nothing here can exercise it
end to end. What CAN be tested offline is the part that actually failed: on
2026-08-16 its `--events` mode walked the UI subscriber map and reported **NO
SUBSCRIBER** for all three commander events, including `0x100001A4` -- which is
known live, because the party-window button raises it and the client asserts
inside its handler (`GmView.cpp(5890)`). The reading was false and fitted the
arc's story so neatly it would probably have survived review.

The fix was a positive control INSIDE the tool: find `0x100001A4` or give no
answer at all. This file exists to keep that control honest, because a gate
that has never been seen to refuse is indistinguishable from one that always
passes.

  §1 the gate REFUSES when the control is absent  -- the 2026-08-16 defect
  §2 and ANSWERS when it is present               -- so §1 is not vacuous
  §3 the address constants still match the binary -- a check the exe can refute
  §4 a NULL context is reported, not dereferenced

Standard library only.

    python toolkit/clientscan/test_commanderpeek.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "harness"))
sys.path.insert(0, HERE)
import checks            # noqa: E402
import keytap            # noqa: E402
import commanderpeek     # noqa: E402

LEDGER = checks.Ledger("commanderpeek", floor=7)

CONTROL = 0x100001A4     # the known-live event the gate must find


def _fake_map(entries, n=8):
    """A synthetic subscriber map: header at one address, buckets at another."""
    raw = bytearray(n * 12)
    for i, row in enumerate(entries):
        struct.pack_into("<3I", raw, i * 12, *row)
    hdr = bytearray(0x20)
    struct.pack_into("<I", hdr, commanderpeek.EVMAP_BUCKETS, 0x1000)
    struct.pack_into("<I", hdr, commanderpeek.EVMAP_COUNT, n)

    def read_at(_pid, addr, size):
        return bytes(raw[:size]) if addr == 0x1000 else bytes(hdr[:size])
    return read_at


def with_reader(read_at, fn):
    """Run `fn` with keytap's readers stubbed, restoring them afterwards."""
    old_read, old_base = keytap.read_at, keytap.module_base
    keytap.read_at = read_at
    keytap.module_base = lambda _pid, _m: commanderpeek.IMAGE_BASE
    try:
        return fn()
    finally:
        keytap.read_at, keytap.module_base = old_read, old_base


def main():
    # ---- 1. THE DEFECT: no control, no answer ---------------------------------
    print("1. the gate refuses when its control is absent")
    absent = _fake_map([(0x1000011E, 0, 7), (0xDEADBEEF, 1, 7)])
    _b, _n, hits = with_reader(
        absent, lambda: commanderpeek.event_subscribers(0, (0x1000011E,)))
    LEDGER.ok(hits is None,
              "control missing -> no subscriber verdict at all",
              f"got {hits!r} -- this is the 2026-08-16 shape: 0x1000011E IS in "
              f"this table, so a reader without the control would happily "
              f"report it SUBSCRIBED and be believed")

    # ---- 2. and it is not simply always-None ---------------------------------
    print("\n2. and answers when the control is present")
    present = _fake_map([(CONTROL, 0, 7), (0x1000011E, 0, 7)])
    _b, _n, hits = with_reader(
        present, lambda: commanderpeek.event_subscribers(
            0, (0x1000011E, 0x10000114)))
    LEDGER.ok(hits is not None, "control found -> an answer is given",
              "if this ever fails the gate is vacuous and section 1 proves nothing")
    LEDGER.ok(hits and hits.get(0x1000011E) == 1,
              "a subscribed event is counted", f"{hits!r}")
    LEDGER.ok(hits and hits.get(0x10000114) == 0,
              "and an absent one reads zero rather than going missing",
              f"{hits!r}")

    # ---- 3. the constants are still the binary's -----------------------------
    print("\n3. the address constants against the client itself")
    try:
        sys.path.insert(0, TOOLKIT)
        import vaultpath
        exe = os.path.join(vaultpath.require_dir("client"),
                           "2026-08-13_64fae3b1369b", "Gw.exe")
        blob = open(exe, "rb").read() if os.path.exists(exe) else None
    except (Exception, SystemExit):
        blob = None
    if blob is None:
        LEDGER.skip("the context global matches 0x004E0B90",
                    "needs vault/client/2026-08-13_64fae3b1369b/Gw.exe")
    else:
        # 0x004E0B90 is `mov eax, [0x00C07850]` = A1 50 78 C0 00. Find that exact
        # byte string; if the client is ever rebuilt this check goes red rather
        # than the tool silently reading a stale address.
        want = b"\xA1" + struct.pack("<I", commanderpeek.CTX_GLOBAL_VA)
        LEDGER.ok(blob.count(want) >= 1,
                  "the commander-context global is still loaded by `mov eax,imm32`",
                  f"0x{commanderpeek.CTX_GLOBAL_VA:08X} -- if this goes red the "
                  f"tool is reading an address the client no longer uses")
        want2 = b"\xB9" + struct.pack("<I", commanderpeek.EVENTMAP_VA)
        LEDGER.ok(blob.count(want2) >= 1,
                  "and the event map is still loaded by `mov ecx,imm32`",
                  f"0x{commanderpeek.EVENTMAP_VA:08X}")

    # ---- 4. a NULL context is reported, not dereferenced ---------------------
    print("\n4. a client whose UI has not initialised")
    def null_ctx(_pid, _mod, _rva, _size):
        return struct.pack("<I", 0)
    old = keytap.read_rva
    keytap.read_rva = null_ctx
    try:
        s = commanderpeek.peek(0)
    finally:
        keytap.read_rva = old
    LEDGER.ok(s == {"ctx": 0},
              "a NULL context returns {'ctx': 0} instead of reading off it",
              f"{s!r} -- the caller prints 'nothing below would mean anything', "
              f"which is the honest output for a client mid-startup")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
