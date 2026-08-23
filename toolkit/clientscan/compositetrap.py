r"""Watch the composite pipeline resolve a character, in a LIVE client.

    python toolkit/clientscan/compositetrap.py --wait --seconds 240
    python toolkit/clientscan/compositetrap.py --pid 1234 --selftest

WHY THIS EXISTS. `studies/playercomposite/FINDINGS.md` §4.12 is the arc's last
honest unknown and it is one sentence: **"Nothing here was checked against a
running client. Every claim is static or archive-side. The cheapest
confirmation is a breakpoint on `0x00833420` during a character load, logging
`(id, record)` pairs."** Everything the arc built rests on two data files and a
disassembly: the composite table parsed off disk (§1.18), the type→component
map read out of `.rdata` (§1.20), the equipment path traced through
`m_slotItemData` (§9.2). All of it predicts what the CLIENT will ask for. None
of it has ever watched the client ask.

WHAT IT DOES. It is a debugger, and it is `commandertrap.py`'s machinery
re-used rather than re-written -- `DebugActiveProcess` plus EXECUTE breakpoints
in DR0..DR3. **Nothing is written into the client**: no `int3` patch, no code
cave, no DLL, no thread. That matters here more than usual, because the bytes
this arc reads are the bytes a patch would mutate.

THE TWO SITES, both `__cdecl`, both re-read from the image this session:

    0x008332E0  f(type, race, prof, *outCount) -- the BASE lookup.
                Bounds asserted by ArenaNet: `prof < 0xB` (CpsData:392) and
                `type < 0x14` (:393), out non-null (:394). This is the
                assembly ORDER: one call per component the identity needs.
    0x00833420  f(index) -> s_items + index*48 -- the RECORD resolver.
                `index < [0x00BF980C]` asserted (CpsData:432/:438 plus an
                inlined Array.h:587). The equipment path reaches HERE with
                `ItemData.fileId` unmodified (§2 step E), so an equipped
                armour piece's composite index arrives at this site and
                nowhere else.

At each breakpoint `push ebp` has NOT executed, so `[esp]` is the return
address and the arguments start at `[esp+4]`. The record site also reads the
resolved record out of the live process -- `[0x00BF9804] + index*48`, first
dword -- so the hit carries `hdr>>22`, the composite TYPE, which is the number
§9.2 says decides the component. That is the `(id, record)` pair §4.12 asked
for, resolved by the client's own table in the client's own memory.

THE PREDICTIONS, stated here before the run because a probe with no stated
expectation can be rationalised into agreeing with anything afterwards. On a
loopback character load with `EQUIP_ARMOUR` on, our server declares five
composite items (`content/items.toml`, masked file ids 91, 90, 94, 92, 93) and
wears them in slots 2..6:

  P1  The base lookup FIRES, and its `type` arguments are drawn from the
      static set {1 or 2 (shell), 3, 4, 5, 6 (base pieces), 9, 10, 11 (face),
      12, 13 (hair)} -- §2 step C's table. A type outside that set refutes the
      table.
  P2  The shell lookup asks type **1**, not 2 -- §7's arg0 answer ("author
      against type 1"), whose whole evidence is six static call sites.
  P3  `prof` and `race` are CONSTANT across one character's lookups and inside
      ArenaNet's own bounds (prof < 11, race < the runtime bound).
  P4  The record resolver fires with our five armour indices **91, 90, 94, 92,
      93**, and the record types read back from the client's own table are
      **15, 14, 18, 16, 17** in that order -- the exact pairs
      `test_wearmap.py` §4 pins from the archive. This is the one that makes
      the runtime check worth spending: it closes the loop archive -> wire ->
      client memory on the same five numbers.
  P5  No `0x00833420` index is >= 3803, and none carries bit 31 (§9.1) --
      the client asserts both; seeing it never approach them is the weaker
      but free half.

REFUTED IF: the shell lookup asks type 2 in world (kills §7); a record index
resolves to a type the static table does not pair with its wire type (kills
§9.2's "the record is authoritative" in the only place it could be tested);
or the base lookup never fires while the character visibly loads (kills the
site attribution, and no verdict is given about anything downstream).

THE CONTROL, and it is `commandertrap.py`'s lesson wired in rather than
restated: **the base lookup MUST fire.** It runs for every composited
character the client draws, ours included. If it never hits, the instrument is
unproven and NO verdict is given about the record site -- "it never happened"
and "we cannot see it happen" look identical from here.

Windows, standard library only (`ctypes`, via `commandertrap`'s machinery and
`harness/keytap.py`'s read-only reader). Read-only against the target's memory;
the only thing it writes anywhere is DR0..DR3/DR7 in the target's own thread
contexts, and it clears them on detach.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

import commandertrap as ct                                   # noqa: E402

IMAGE_BASE = ct.IMAGE_BASE

# The two globals the record resolver itself reads (0x0083347D / 0x0083343F).
RECORD_BASE_PTR = 0x00BF9804
RECORD_COUNT_PTR = 0x00BF980C
RECORD_STRIDE = 48          # `lea eax,[esi+esi*2]; shl eax,4` at 0x00833477
TYPE_SHIFT = 22             # hdr >> 22 -- cpsdata.Record.type
FILE_ID_RESERVED_BIT = 0x80000000

#: §2 step C's table: every composite type an identity's base lookup may ask
#: for. P1 is refuted by anything outside it.
BASE_TYPES = frozenset({1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13})

#: What our own server declares and wears (content/items.toml masked file ids
#: -> the record type test_wearmap §4 pins from the archive).
OUR_ARMOUR = {91: 15, 90: 14, 94: 18, 92: 16, 93: 17}


def _slid(va):
    return va + ct.SLIDE


def _cap_getids(ctx, reader):
    """(type, race, prof) off the live stack, plus the return address."""
    w = ct._dw(reader, ctx.Esp, 5)
    if not w:
        return {"VERDICT": "unreadable stack"}
    ret, ty, race, prof, out = w
    ok = ty in BASE_TYPES
    return {
        "return address (VA)": ct.unslide(ret),
        "type": ty, "race": race, "prof": prof,
        "out non-null": bool(out),
        "VERDICT": (f"type {ty} race {race} prof {prof}"
                    + ("" if ok else "  <-- OUTSIDE the step-C table (P1)")),
    }


def _cap_record(ctx, reader):
    """The index argument AND the record the client's own table resolves.

    This is §4.12's `(id, record)` pair. The record is read through the
    client's own base pointer rather than our parsed copy, so a disagreement
    would be a real finding rather than a bookkeeping error.
    """
    w = ct._dw(reader, ctx.Esp, 2)
    if not w:
        return {"VERDICT": "unreadable stack"}
    ret, idx = w
    base = ct._dw(reader, _slid(RECORD_BASE_PTR), 1)
    count = ct._dw(reader, _slid(RECORD_COUNT_PTR), 1)
    out = {"return address (VA)": ct.unslide(ret), "index": idx,
           "record count": count[0] if count else None}
    if idx & FILE_ID_RESERVED_BIT:
        out["VERDICT"] = f"index 0x{idx:08X} carries the RESERVED BIT (P5)"
        return out
    if not base or not base[0] or (count and idx >= count[0]):
        out["VERDICT"] = f"index {idx} out of range or table not loaded (P5)"
        return out
    hdr = ct._dw(reader, base[0] + idx * RECORD_STRIDE, 1)
    if not hdr:
        out["VERDICT"] = f"index {idx}: record unreadable"
        return out
    ctype = hdr[0] >> TYPE_SHIFT
    out["hdr"] = hdr[0]
    out["composite type"] = ctype
    note = ""
    if idx in OUR_ARMOUR:
        note = ("  <-- OUR armour piece, type MATCHES (P4)"
                if OUR_ARMOUR[idx] == ctype else
                f"  <-- OUR armour piece but type {ctype} != "
                f"{OUR_ARMOUR[idx]} (P4 REFUTED)")
    out["VERDICT"] = f"index {idx} -> composite type {ctype}{note}"
    return out


SITES = {
    "getids": ct.Site(
        "getids", 0x008332E0, bytes.fromhex("558bec538b5d10"),
        "the BASE lookup f(type, race, prof, *out) -- THE CONTROL and the "
        "assembly order (§2 step C). If this never fires, nothing below it "
        "means anything.", _cap_getids),
    "record": ct.Site(
        "record", 0x00833420, bytes.fromhex("558bec568b7508"),
        "the RECORD resolver f(index) -> s_items + index*48 -- §4.12's "
        "`(id, record)` pair, with the record read out of the client's own "
        "table", _cap_record),
}
DEFAULT_SITES = ("getids", "record")


def _analyse(sites, hits):
    """Score the five predictions from the hits. Returns (lines, verdict)."""
    order = [s.name for s in sites]
    caps = {n: [h["cap"] for h in hits
                if order[h["slot"]] == n and h.get("cap")] for n in order}
    L = []
    base_hits, rec_hits = caps.get("getids", []), caps.get("record", [])

    L.append(f"CONTROL: the base lookup fired {len(base_hits)} time(s)")
    if not base_hits:
        L.append("  -> the instrument is UNPROVEN. No verdict is given about "
                 "the record site: 'it never happened' and 'we cannot see it "
                 "happen' are indistinguishable from here.")
        return L, 2

    types = [c["type"] for c in base_hits if "type" in c]
    outside = sorted({t for t in types if t not in BASE_TYPES})
    p1 = "PASS" if not outside else f"REFUTED, outside={outside}"
    L.append(f"P1 base types within step C's table: {p1} "
             f"(seen {sorted(set(types))})")

    shell = sorted({t for t in types if t in (1, 2)})
    if not shell:
        p2 = "no shell lookup seen -- NO VERDICT"
    elif shell == [1]:
        p2 = "PASS -- type 1 only, in world (§7's arg0 answer holds live)"
    else:
        p2 = f"REFUTED or mixed: saw {shell}"
    L.append(f"P2 the in-world shell type: {p2}")

    profs = sorted({c.get("prof") for c in base_hits if "prof" in c})
    races = sorted({c.get("race") for c in base_hits if "race" in c})
    p3 = ("PASS" if len(profs) == 1 and len(races) == 1
          and all(p < 11 for p in profs) else "CHECK")
    L.append(f"P3 prof/race constant and in bounds: profs={profs} "
             f"races={races} {p3}")

    seen = {}
    for c in rec_hits:
        if "index" in c and "composite type" in c:
            seen[c["index"]] = c["composite type"]
    ours = {i: t for i, t in seen.items() if i in OUR_ARMOUR}
    wrong = {i: t for i, t in ours.items() if OUR_ARMOUR[i] != t}
    if wrong:
        p4 = f"REFUTED -- {wrong} against the archive's {OUR_ARMOUR}"
    elif ours:
        p4 = (f"PASS -- every resolved type matches the archive "
              f"({len(ours)} of {len(OUR_ARMOUR)} pieces seen)")
    else:
        p4 = "NOT SEEN -- no armour index reached the resolver, NO VERDICT"
    L.append(f"P4 our armour indices: resolved {sorted(ours)} of "
             f"{sorted(OUR_ARMOUR)} -- {p4}")

    cap = next((c.get("record count") for c in rec_hits
                if c.get("record count")), None)
    bad5 = [i for i in seen
            if (i & FILE_ID_RESERVED_BIT) or (cap is not None and i >= cap)]
    p5 = "PASS" if not bad5 else f"VIOLATED {bad5}"
    L.append(f"P5 every index in range (< {cap}) and no reserved bit: {p5} "
             f"({len(seen)} distinct indices)")
    return L, (0 if (not outside and not wrong) else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int)
    ap.add_argument("--wait", action="store_true",
                    help="wait for a Gw.exe to appear")
    ap.add_argument("--seconds", type=float, default=240.0)
    ap.add_argument("--sites", default=",".join(DEFAULT_SITES))
    ap.add_argument("--out", help="also write the report here")
    a = ap.parse_args(argv)

    want = [s.strip() for s in a.sites.split(",") if s.strip()]
    for n in want:
        if n not in SITES:
            ap.error(f"unknown site {n!r}; have {', '.join(SITES)}")
    sites = [SITES[n] for n in want]

    import time
    import commanderpeek
    pid = a.pid
    if pid is None:
        t_end = time.time() + (180 if a.wait else 0)
        while True:
            pids = commanderpeek.find_client_pids()
            if pids:
                if len(pids) > 1:
                    raise SystemExit(
                        f"{len(pids)} clients running {pids}. Refusing to "
                        f"guess which one -- pass --pid. Two clients is how a "
                        f"run measures the wrong process.")
                pid = pids[0]
                break
            if time.time() >= t_end:
                raise SystemExit("no Gw.exe. Start the session, or --wait.")
            time.sleep(0.25)
    print(f"pid {pid}")

    base, checked = ct.verify_sites(pid, sites)
    ct.SLIDE = base - IMAGE_BASE
    print(f"Gw.exe base 0x{base:08X} (slide 0x{ct.SLIDE:X})")
    bad = []
    for s, ok, detail in checked:
        mark = {True: "ok  ", False: "BAD ", None: "??  "}[ok]
        print(f"  {mark}{s.name:8} va 0x{s.va:08X}  {detail}")
        if ok is False:
            bad.append(s.name)
    if bad:
        raise SystemExit(
            f"REFUSING to arm: {', '.join(bad)} do not hold the instruction "
            f"bytes recorded for them. These addresses are build 38797's; a "
            f"hardware breakpoint on the wrong build does not error -- it "
            f"arms on whatever is there and reports it as the pipeline.")

    reader_h = ct.keytap.open_read(pid)

    def reader(addr, size):
        return ct.keytap.read_handle(reader_h, addr, size)

    def on_hit(trap, hit):
        site = sites[hit["slot"]]
        if site.capture and hit["ctx"] is not None:
            hit["cap"] = site.capture(hit["ctx"], reader)
        print(f"  HIT {site.name} (0x{site.va:08X})"
              + (f"  {hit['cap'].get('VERDICT', '')}" if hit.get("cap") else ""),
              flush=True)

    trap = ct.HwTrap(on_hit=on_hit)
    trap.max_hits = 400          # the base lookup runs per component
    trap.addrs = [base + (s.va - IMAGE_BASE) for s in sites]
    trap.attach(pid)
    print(f"attached; armed {len(sites)} execute breakpoints, holding "
          f"{a.seconds:.0f}s", flush=True)
    try:
        trap.pump(a.seconds)
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        trap.detach()
        ct.kernel32.CloseHandle(reader_h)
        print("detached, debug registers cleared")

    ct._report(sites, trap.hits, base, trap=trap)
    lines, rc = _analyse(sites, trap.hits)
    print("\n" + "=" * 72 + "\nPREDICTIONS\n" + "=" * 72)
    for ln in lines:
        print("  " + ln)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            ct._report(sites, trap.hits, base, out=fh, trap=trap)
            fh.write("\nPREDICTIONS\n")
            for ln in lines:
                fh.write("  " + ln + "\n")
        print(f"\nwritten to {a.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
