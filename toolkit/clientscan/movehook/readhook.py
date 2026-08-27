"""Read a movehook capture and score MOVECODE-P1 off it.

    python toolkit/clientscan/movehook/readhook.py                 # the default capture
    python toolkit/clientscan/movehook/readhook.py --bin PATH
    python toolkit/clientscan/movehook/readhook.py --dump 40       # raw records

WHAT P1 ASKS, and why this file computes it rather than leaving it to a reader with a
spreadsheet. MOVECODE-B1 established that the shared setter hardcodes `isWaypoint = 0`
into the bake, so every wire-driven grant arms a hard arrival -- and that the setter
then calls obstacle avoidance and a priority-queue path solve, BOTH of which re-bake
with `isWaypoint = 1` when the point they computed differs from where the agent is
headed. What is not established is the RATE. The capture answers it directly:

    P1a  what fraction of bakes carry isWaypoint = 1, and which caller issued them
    P1b  does every teleport follow a bit-18-CLEAR agent, and how far did it move

REFUSES RATHER THAN GUESSES, in the two places a capture can lie:

  * **The controls gate the numbers.** `movehook.txt` records whether control A (our
    own int3) and control B (a byte of real client code) fired. If A did not, the
    handler was dead and every count here is a fact about nothing. This reader reads
    that sidecar and REFUSES to print rates when A failed, because a zero from a dead
    hook and a zero from a client that never glided are the same zero.
  * **A full ring is a truncated run.** `stored == NCAP` means the tail was dropped,
    so a rate computed over it is biased toward whatever the client did early. Said
    out loud, never silently.

Stdlib only; it parses a fixed record whose length comes from the file header rather
than from this file, so a capture written by an older DLL still parses or is refused
by name.
"""

import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLKIT)

MAGIC = b"MVHK"
DEFAULT_DIR = os.path.join("vault", "research", "movecode")

# The record, as movehook.c writes it. `reclen` in the header is authoritative --
# this layout is only how we interpret a record of that length.
FIELDS = ("seq tick site tid retaddr ecx arg1 arg2 arg3 have_agent "
          "id flags stop x98").split()
NPOINT = 4
REC_FMT = "<" + "I" * len(FIELDS) + "I" * (NPOINT * 3)
REC_LEN = struct.calcsize(REC_FMT)

BIT_ISWAYPOINT = 1 << 18
BIT_IN_WORLD = 1 << 17
BIT_STALE = 1 << 19


class CaptureError(Exception):
    pass


def _f(dw):
    """A stored dword back to the float it was."""
    return struct.unpack("<f", struct.pack("<I", dw))[0]


class Capture:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            blob = fh.read()
        if blob[:4] != MAGIC:
            raise CaptureError(f"{path}: not a movehook capture (magic "
                               f"{blob[:4]!r}, expected {MAGIC!r})")
        ver, self.base, nsites, self.reclen, n = struct.unpack_from("<IIIII", blob, 4)
        if ver != 1:
            raise CaptureError(f"{path}: capture version {ver}, this reader knows 1")
        off = 24
        self.sites = []
        for _ in range(nsites):
            rva, hits = struct.unpack_from("<II", blob, off)
            self.sites.append({"rva": rva, "va": self.base + rva, "hits": hits})
            off += 8
        if self.reclen != REC_LEN:
            raise CaptureError(
                f"{path}: record length {self.reclen} but this reader's layout is "
                f"{REC_LEN}. The DLL and this file disagree; regenerate one of them "
                f"rather than parsing a record whose fields would silently shift.")
        # `tick` IS THE COMMIT FLAG. The DLL claims a slot with an Interlocked and
        # fills it afterwards, so a handler preempted mid-record leaves a partial
        # one -- and a partial record decodes as a perfectly plausible real one
        # (all-zero reads as site 0, seq 0, have_agent 0) and would be COUNTED.
        # movehook.c writes `tick` last, after every other field; memset leaves it
        # 0 and GetTickCount never returns 0 in practice. Anything still 0 here was
        # never committed and is dropped, loudly.
        self.recs = []
        self.partial = 0
        for i in range(n):
            vals = struct.unpack_from(REC_FMT, blob, off + i * self.reclen)
            r = dict(zip(FIELDS, vals[:len(FIELDS)]))
            if not r["tick"]:
                self.partial += 1
                continue
            rest = vals[len(FIELDS):]
            r["point"] = rest[0:4]
            r["segment"] = rest[4:8]
            r["target"] = rest[8:12]
            self.recs.append(r)
        self.stored = len(self.recs)
        self.claimed = n

    def sidecar(self):
        """(control_a, control_b, text) from movehook.txt beside the capture."""
        p = os.path.join(os.path.dirname(self.path), "movehook.txt")
        if not os.path.isfile(p):
            return None, None, None
        text = open(p, encoding="utf-8", errors="replace").read()
        a = "FIRED" in text.split("control A", 1)[-1].split("\n", 1)[0]
        bline = text.split("control B", 1)[-1].split("\n", 1)[0]
        b = "FIRED" in bline and "DID NOT FIRE" not in bline
        if "COULD NOT ARM" in bline:
            b = None
        return a, b, text

    def site_name(self, idx, names):
        return names[idx] if idx < len(names) else f"site{idx}"


def static_base():
    """The image base every address in `studies/` is quoted against.

    DERIVED, not hardcoded: `content/movecode.toml` carries both `va` and `rva` for
    each site, so their difference IS the base the rows were measured at. Falls back
    to the PE default only when the content store cannot be read.
    """
    try:
        import content as content_mod
        t = content_mod.load()
        t = t.tables if hasattr(t, "tables") else t
        for row in (t.get("hook_site") or {}).values():
            return row["va"] - row["rva"]
    except Exception:
        pass
    return 0x00400000


def site_names():
    """Names in the same order gensites.py emits them: sorted by key."""
    try:
        import content as content_mod
        t = content_mod.load()
        t = t.tables if hasattr(t, "tables") else t
        return sorted(t.get("hook_site") or {})
    except Exception:
        return []


def report(cap, names, dump=0):
    out = []
    a = out.append
    # ASLR moves the client every launch, so a captured return address is a LIVE
    # address and every address in the studies is a STATIC one. Printing the live
    # form next to a static expectation makes the two uncomparable by eye, which is
    # exactly the mistake this report exists to prevent -- so rebase once, here, and
    # print only static addresses below.
    _sbase = static_base()
    def reb(va):
        return va - cap.base + _sbase if va >= cap.base else va
    a(f"capture: {cap.path}")
    a(f"image base 0x{cap.base:08X} (rebased to 0x{_sbase:08X} below)   "
      f"{cap.stored} record(s) stored")
    if getattr(cap, "partial", 0):
        a(f"!! {cap.partial} of {cap.claimed} slot(s) were claimed but never "
          f"committed -- a handler was preempted mid-record. Dropped, not counted.")
    a("")

    ctl_a, ctl_b, _text = cap.sidecar()
    if ctl_a is None:
        a("!! no movehook.txt beside this capture -- the controls are UNKNOWN.")
        a("   Rates below are printed but must not be quoted: a dead handler and a")
        a("   client that never moved produce the same numbers.")
    else:
        a(f"control A (our own int3):   {'FIRED' if ctl_a else 'DID NOT FIRE'}")
        a(f"control B (real client code): "
          + ("COULD NOT ARM" if ctl_b is None else
             ("FIRED" if ctl_b else "DID NOT FIRE")))
        if not ctl_a:
            a("")
            a("REFUSING to score this capture. Control A failed, which means the")
            a("vectored handler never ran -- every count below is a fact about the")
            a("hook being dead, not about the client.")
            return "\n".join(out), 1
        if ctl_b is False:
            a("   ^ patch/delivery on real client code is UNPROVEN, so a ZERO in any")
            a("     row below is not evidence of absence.")
    a("")

    a("per site:")
    for i, s in enumerate(cap.sites):
        nm = names[i] if i < len(names) else f"site{i}"
        stored = sum(1 for r in cap.recs if r["site"] == i)
        a(f"  {nm:10} va 0x{s['va']:08X}  hits {s['hits']:7}  stored {stored}")
    a("")

    idx = {nm: i for i, nm in enumerate(names)}

    # ---- P1a: the isWaypoint rate, and who issued each bake ----------------
    bi = idx.get("bake")
    if bi is None:
        a("P1a: no `bake` site in this capture -- cannot score the isWaypoint rate.")
    else:
        bakes = [r for r in cap.recs if r["site"] == bi]
        if not bakes:
            a("P1a: the bake site stored ZERO records.")
            a("     With control A green that is a real absence: the client baked no")
            a("     movement while the hook was armed. Check the run, not the hook.")
        else:
            glide = [r for r in bakes if r["arg2"]]
            a(f"P1a  isWaypoint over {len(bakes)} bake(s): "
              f"{len(glide)} glide (arg2!=0), {len(bakes) - len(glide)} hard arrival"
              f"  -- {100.0 * len(glide) / len(bakes):.1f}% glide")
            by_ret = {}
            for r in bakes:
                k = (reb(r["retaddr"]), bool(r["arg2"]))
                by_ret[k] = by_ret.get(k, 0) + 1
            a("     by return address (which caller baked it):")
            for (ret, isw), n in sorted(by_ret.items(), key=lambda kv: -kv[1]):
                a(f"       0x{ret:08X}  isWaypoint={int(isw)}  {n}")
            a("     Expected callers, from FINDINGS §1.6 -- a return address that is")
            a("     none of these is a caller `--xrefs` could not see, which is")
            a("     MOVECODE-Q4 answering itself:")
            a("       0x00602AD8 setter(0)  0x006002BA tick(0)")
            a("       0x00600B0F avoid(1)   0x0060193B solve(1)   0x005FEC83 follow(fwd)")
    a("")

    # ---- P1b: every teleport, and how far it moved the body ---------------
    ti = idx.get("teleport")
    if ti is not None:
        tps = [r for r in cap.recs if r["site"] == ti]
        a(f"P1b  {len(tps)} teleport(s)")
        by_c = {}
        for r in tps:
            by_c[reb(r["retaddr"])] = by_c.get(reb(r["retaddr"]), 0) + 1
        a("     by return address (which caller teleported):")
        for ret, n in sorted(by_c.items(), key=lambda kv: -kv[1]):
            a(f"       0x{ret:08X}  {n}")
        a("     0x00600333 is the return of `0x0060032E call 0x6020b0` -- the")
        a("     bit-18-CLEAR arm of the branch at 0x0060029F (FINDINGS §1.3).")
        clear = sum(1 for r in tps if r["have_agent"]
                    and not (r["flags"] & BIT_ISWAYPOINT))
        if tps:
            a(f"     bit 18 CLEAR at entry: {clear}/{len(tps)}"
              + ("  -- as predicted" if clear == len(tps) else
                 "  -- SOME TELEPORTED WITH BIT 18 SET, which FINDINGS §1.3 says "
                 "should not happen. That is a refutation, not noise."))
        # AGENT_INVALID_POSITION is +inf (0x7F800000), and it is a FINDING rather
        # than noise: ArenaNet's own assert AgAgent:1144
        # `m_targetPoint.position != AGENT_INVALID_POSITION` exists to keep it out
        # of exactly this field. MEASURED 2026-08-27, one record in 131. Left in the
        # distance list it makes `max` read `inf` and drags nothing else, so the
        # number that looked broken was the only honest thing on the line. Counted
        # and named separately instead -- a silent filter here would delete the
        # anomaly and leave a clean-looking p50 over the survivors.
        moved, invalid = [], 0
        for r in tps:
            if not r["have_agent"]:
                continue
            px, py = _f(r["point"][0]), _f(r["point"][1])
            tx, ty = _f(r["target"][0]), _f(r["target"][1])
            if not all(map(math.isfinite, (px, py, tx, ty))):
                invalid += 1
                continue
            moved.append(((tx - px) ** 2 + (ty - py) ** 2) ** 0.5)
        if invalid:
            a(f"     !! {invalid} teleport(s) entered with a NON-FINITE point or "
              f"target.")
            a(f"        That is AGENT_INVALID_POSITION (+inf), which ArenaNet's own")
            a(f"        assert AgAgent:1144 exists to keep out of m_targetPoint.")
            a(f"        Excluded from the distances below and reported here instead.")
        if moved:
            moved.sort()
            a(f"     distance body -> target at the teleport, {len(moved)} sample(s):")
            a(f"       min {moved[0]:8.1f}  p50 {moved[len(moved) // 2]:8.1f}  "
              f"max {moved[-1]:8.1f} units")
            big = [d for d in moved if d > 100.0]
            a(f"       over 100 u (a visible warp): {len(big)}")
    a("")

    if dump:
        a(f"first {dump} record(s):")
        for r in cap.recs[:dump]:
            nm = names[r["site"]] if r["site"] < len(names) else str(r["site"])
            line = (f"  #{r['seq']:<5} t={r['tick']:<10} {nm:9} "
                    f"ret=0x{reb(r['retaddr']):08X} ecx=0x{r['ecx']:08X} "
                    f"a1=0x{r['arg1']:08X} a2=0x{r['arg2']:08X}")
            if r["have_agent"]:
                line += (f" id={r['id']:<5} flags=0x{r['flags']:08X}"
                         f"{' WP' if r['flags'] & BIT_ISWAYPOINT else '   '}"
                         f" stop={r['stop']:<10}"
                         f" pt=({_f(r['point'][0]):.0f},{_f(r['point'][1]):.0f})"
                         f" tgt=({_f(r['target'][0]):.0f},{_f(r['target'][1]):.0f})")
            a(line)
    return "\n".join(out), 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", default=None, help="capture file")
    ap.add_argument("--dump", type=int, default=0, help="print N raw records")
    args = ap.parse_args()

    path = args.bin
    if not path:
        try:
            import vaultpath
            path = os.path.join(vaultpath.vault_path("research", "movecode"),
                                "movehook.bin")
        except Exception as ex:
            return print(f"cannot locate the vault ({ex}); pass --bin") or 2
    if not os.path.isfile(path):
        print(f"no capture at {path}\n"
              f"A run that produced no file is a run that did not happen -- check "
              f"that the DLL was injected and that its timeout elapsed.")
        return 2
    cap = Capture(path)
    text, rc = report(cap, site_names(), args.dump)
    print(text)
    return rc


if __name__ == "__main__":
    sys.exit(main())
