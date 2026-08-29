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

# The record, as movehook.c writes it, PER VERSION. `reclen` in the header is
# authoritative and the version selects the layout -- so an old capture stays
# readable after the record grows, which is the whole reason this is versioned
# rather than assumed. v1 carried three args; v2 carries six, because B3's
# `MapFindPath` is a navmesh query whose output buffer is among its parameters and
# an entry hook that cannot see arg4 cannot record where the answer was written.
# THE RECORD, PER VERSION, AS AN ORDERED FIELD LIST -- name and dword count.
#
# WHY ORDERED PAIRS AND NOT "SCALARS THEN BLOCKS". v3 was first described here as
# `scalars + [point, segment, target, pt_a, pt_b]`, with `have_pts` appended to the
# scalars. movehook.c actually declares `have_pts` AFTER target[4]. Both spellings
# total 38 dwords, so `reclen` matched and the length check -- whose own message
# warns about "a record whose fields would silently shift" -- could not fire. Every
# point block read one dword late: `have_pts` came back as m_point.x, which is 0 for
# a site with no agent, so `pathdiff` reported "no coordinates" on a capture that
# had them, and run 2's teleport distances came out plausible and WRONG.
#
# A layout is now a SEQUENCE, so the order is stated once and cannot drift from the
# C by accident; `test_movehook.py` §11 parses `rec_t` out of movehook.c and
# compares it to this table, which is the check the length test could never be.
_SCALARS_V1 = ["seq", "tick", "site", "tid", "retaddr", "ecx",
               "arg1", "arg2", "arg3",
               "have_agent", "id", "flags", "stop", "x98"]
_SCALARS_V2 = ["seq", "tick", "site", "tid", "retaddr", "ecx",
               "arg1", "arg2", "arg3", "arg4", "arg5", "arg6",
               "have_agent", "id", "flags", "stop", "x98"]
_POINTS = [("point", 4), ("segment", 4), ("target", 4)]

_LAYOUTS = {
    1: [(n, 1) for n in _SCALARS_V1] + _POINTS,
    2: [(n, 1) for n in _SCALARS_V2] + _POINTS,
    3: [(n, 1) for n in _SCALARS_V2] + _POINTS
       + [("have_pts", 1), ("pt_a", 4), ("pt_b", 4)],
    # v4 adds what it takes to see a WARP rather than a leg: velocity and the
    # timestamp m_point is valid at. See the note in movehook.c's rec_t.
    4: [(n, 1) for n in _SCALARS_V2] + _POINTS
       + [("have_pts", 1), ("pt_a", 4), ("pt_b", 4),
          ("vel", 2), ("ptime", 1)],
    # v5 adds the SECOND agent both snap sites take as an argument -- the other
    # side of a correction. See the note in movehook.c's rec_t.
    5: [(n, 1) for n in _SCALARS_V2] + _POINTS
       + [("have_pts", 1), ("pt_a", 4), ("pt_b", 4),
          ("vel", 2), ("ptime", 1),
          ("have_src", 1), ("src_id", 1), ("src_flags", 1), ("src_stop", 1),
          ("src_ptime", 1), ("src_point", 4), ("src_segment", 4),
          ("src_target", 4), ("src_vel", 2)],
    # v6 adds the world field, the facing, and AgTrack's fence dword. All three
    # are APPENDED rather than grouped where they belong, deliberately -- see the
    # note in movehook.c's rec_t. `world` closes §1i.7's "the sync side is
    # identified from call-site structure rather than from the record"; `facing`
    # is the second half of snaptest's pre-gate early-out (its first half,
    # m_timeStopMovement, is already `src_stop`); `fence` is the operand of
    # agtrack's own branch at 0x00606009, read at the entry rather than sampled.
    6: [(n, 1) for n in _SCALARS_V2] + _POINTS
       + [("have_pts", 1), ("pt_a", 4), ("pt_b", 4),
          ("vel", 2), ("ptime", 1),
          ("have_src", 1), ("src_id", 1), ("src_flags", 1), ("src_stop", 1),
          ("src_ptime", 1), ("src_point", 4), ("src_segment", 4),
          ("src_target", 4), ("src_vel", 2),
          ("world", 1), ("facing", 1), ("src_world", 1), ("src_facing", 1),
          ("have_fence", 1), ("fence", 1)],
}
# v7, 2026-08-29: THE MapFindPath RETURN TAP -- the ANSWER, where every version
# before it captured only the question. Spelled as `_LAYOUTS[6] + [...]` rather
# than retyped, so "APPENDED, never inserted" is structural here instead of a
# promise a future editor has to keep (the v6 note in movehook.c's rec_t explains
# why a length check cannot catch a reorder).
#
#   esp        the entry<->ret JOIN KEY, stored on every site. All four exits are
#              `8B E5 5D C3`, so esp at a ret is exactly the entry esp -- and a
#              pair whose two values disagree REFUTES that premise rather than
#              being a bad record. pathdiff refuses such a pair, loudly.
#   have_out   bit 0 = out_count was read, bit 1 = out_path was. The `have_fence`
#              distinction again, and here it IS the measurement: "could not read"
#              and "the client answered ZERO" must not merge, because pathCount
#              == 0 under a lock is the registered prediction.
#   out_count  the client's own pathCount.
#   out_n      how many points this record kept (<= out_count). Truncation is
#              RECORDED, not hidden: RET_MAX_POINTS is 4, click-to-move asks 9.
_LAYOUTS[7] = _LAYOUTS[6] + [("esp", 1), ("have_out", 1), ("out_count", 1),
                             ("out_n", 1), ("out_path", 16)]
# v8, 2026-08-29: out_path grows 4 -> 9 POINTS, so it cannot truncate for
# either known caller (9 is click-to-move's own maxCount, 4 is snap gate 2's).
#
# A NEW VERSION RATHER THAN A WIDER v7, and that is the whole point of the
# scheme. r7 -- the arc's only capture carrying the client's own answers -- is
# a v7 file with a 16-dword out_path. Redefining v7 in place would have made
# `reclen` disagree and orphaned it, which is exactly the failure §4 pins with
# "a v1 capture still parses": versioning that orphans the evidence is worse
# than not versioning. Both layouts live here and both parse.
_LAYOUTS[8] = _LAYOUTS[6] + [("esp", 1), ("have_out", 1), ("out_count", 1),
                             ("out_n", 1), ("out_path", 36)]
NPOINT = 4
# The four MapFindPath exits, in one place. Anything keyed on the single name
# "mapfindpath" sees the QUESTION only; these four carry the ANSWER.
MFP_ENTRY = "mapfindpath"
MFP_RETS = ("mapfindpath_ret1", "mapfindpath_ret2",
            "mapfindpath_ret3", "mapfindpath_ret4")
# The CURRENT writer's out_path capacity, in points; movehook.c owns the value.
# NEVER use this to describe a record you are holding -- a v7 record has a
# capacity of 4 and a v8 record 9, and quoting the writer's constant at a v7
# record is how a reader ends up reporting a capacity the file does not have.
# `ret_capacity(r)` asks the record instead.
RET_MAX_POINTS = 9


def ret_capacity(r):
    """How many points THIS record's out_path can hold. Per record, not global."""
    p = r.get("out_path")
    return (len(p) // NPOINT) if p else 0
# The facing value that, together with a non-zero m_timeStopMovement, returns
# NO SNAP from snaptest before any gate runs (0x0060563A / 0x00605641).
FACING_EARLY_OUT = 9


def _layout(ver):
    spec = _LAYOUTS.get(ver)
    if spec is None:
        raise CaptureError(f"capture version {ver}: this reader knows "
                           f"{sorted(_LAYOUTS)}")
    fmt = "<" + "I" * sum(c for _n, c in spec)
    return spec, fmt, struct.calcsize(fmt)


def _unpack(spec, vals):
    out, i = {}, 0
    for name, count in spec:
        out[name] = vals[i] if count == 1 else tuple(vals[i:i + count])
        i += count
    return out


# The current writer's layout, for anything that builds a capture (the tests do).
# Bump BOTH of these with the version, or the tests keep synthesising the OLD
# record while the DLL writes the new one and every parse silently disagrees.
CURRENT_VER = 8
FIELDS = [n for n, c in _LAYOUTS[CURRENT_VER] if c == 1]
_SPEC5, REC_FMT, REC_LEN = _layout(CURRENT_VER)

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
        self.version = ver
        fields, fmt, want_len = _layout(ver)
        off = 24
        self.sites = []
        for _ in range(nsites):
            rva, hits = struct.unpack_from("<II", blob, off)
            self.sites.append({"rva": rva, "va": self.base + rva, "hits": hits})
            off += 8
        if self.reclen != want_len:
            raise CaptureError(
                f"{path}: header says version {ver} (record {want_len} B) but the "
                f"record length is {self.reclen}. The DLL and this file disagree; "
                f"regenerate one of them rather than parsing a record whose fields "
                f"would silently shift.")
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
            vals = struct.unpack_from(fmt, blob, off + i * self.reclen)
            r = _unpack(fields, vals)
            if not r["tick"]:
                self.partial += 1
                continue
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


def site_names(cap=None):
    """Names for a capture's site indices.

    RESOLVED BY RVA, NOT BY POSITION, when a capture is given -- and that is a
    defect fix rather than a nicety. `gensites.py` emits sites sorted by key, so
    ADDING A ROW RENUMBERS EVERY INDEX AFTER IT. Run 1's capture has four sites;
    B3 added five more, three of which sort before `bake`. Indexing that old
    capture against today's row list silently relabels every record in it —
    `bake` becomes `chcli_b`, and the report reads as confidently as ever.

    The capture stores its OWN rva per site in its header, so the mapping is
    recoverable exactly. A site whose rva is not in the current rows is named by
    its address rather than guessed at.
    """
    try:
        import content as content_mod
        t = content_mod.load()
        t = t.tables if hasattr(t, "tables") else t
        rows = t.get("hook_site") or {}
    except Exception:
        rows = {}
    if cap is None:
        return sorted(rows)
    by_rva = {r["rva"]: n for n, r in rows.items()}
    return [by_rva.get(s["rva"], f"rva_{s['rva']:08X}") for s in cap.sites]


def _union_ms(ivs):
    """Total length of the union of [start, end] millisecond intervals.

    Union, not sum, and that is the whole point: an agent sampled twice during one
    leg declares that leg twice, so a sum would count it twice and would scale with
    how often our hook happened to fire on that object. The two world copies are
    sampled ~10x apart in this capture, so any sample-weighted statistic comparing
    them measures our hook placement rather than the client.
    """
    if not ivs:
        return 0
    ivs = sorted(ivs)
    merged = [list(ivs[0])]
    for lo, hi in ivs[1:]:
        if lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return sum(hi - lo for lo, hi in merged)


def _by_object(cap, names):
    """{this-pointer: [its records, in capture order]} for every agent-bearing hit.

    ONE grouping, used by both the world census and the displacement count. Two
    copies of this would be two places to disagree about what an object is --
    the same defect `_synth` was rebuilt to avoid, from the other side.

    Keyed on the ADDRESS and never on the id, because one agent id names TWO
    objects (the two world copies) and grouping on it interleaves bodies that
    genuinely sit hundreds of units apart.
    """
    objs = {}
    for i, r in enumerate(cap.recs):
        if not r.get("have_agent"):
            continue
        r.setdefault("_i", i)
        objs.setdefault(r["ecx"], []).append(r)
    return objs


def _worlds(cap, names):
    """The world-copy census: how many OBJECTS carry each agent id, and what drives each.

    WHY THIS IS A SECTION AND NOT A FOOTNOTE. `GAME_SMSG_WORLD_CREATE_AGENT` runs its
    body TWICE with the agent array base advanced 0x64 -- AgAgent.cpp:312 names them
    m_world 0 and 1 -- so **one agent id names TWO objects**. Every per-agent
    trajectory in this file's history filtered on `id == 1` and treated the result as
    one body. It is not one body, and the artifact is not subtle: in the run 5 capture
    the two copies sit 940 u apart, so an id-filtered walk crosses between them and
    reports a 940 u displacement inside a single 15 ms GetTickCount tick. FINDINGS 1h.2
    scored the warp rate that way.

    `id` cannot distinguish them and `ecx` can -- it is the object's address. So the
    grouping key here is the ADDRESS, and the id is only a label. Nothing below is
    inferred; each object's motion is read from its own declared legs.
    """
    out = []
    a = out.append
    bysite = {nm: i for i, nm in enumerate(names)}
    objs = {}
    for r in cap.recs:
        if not r.get("have_agent"):
            continue
        o = objs.setdefault(r["ecx"], {"id": r["id"], "recs": [], "sites": {}})
        o["recs"].append(r)
        nm = names[r["site"]] if r["site"] < len(names) else str(r["site"])
        o["sites"][nm] = o["sites"].get(nm, 0) + 1
    if not objs:
        return "world copies: no record carries an agent, so nothing to census."

    # Which object is the SYNC one is not guessed: the source argument of a desync
    # test / correction is asserted WORLD_SYNC by the client itself
    # (AgTrack.cpp:458 `source.GetWorld() == WORLD_SYNC`), and the DLL records that
    # agent's address in the same record.
    sync = set()
    for r in cap.recs:
        if not r.get("have_src"):
            continue
        nm = names[r["site"]] if r["site"] < len(names) else ""
        key = r["arg1"] if nm == "reseed" else r["arg2"]
        sync.add(key)

    byid = {}
    for addr, o in objs.items():
        byid.setdefault(o["id"], []).append(addr)
    multi = {i: v for i, v in byid.items() if len(v) > 1}

    # NOT EVERY `this` IS AN AGENT, and a census that lists a non-agent beside the
    # two real world copies invites exactly the reading that cost run 5 a headline:
    # `snaptest`'s ecx was marked thiscall because 0x006055FB saves ecx to a local,
    # and it produced 70 records with agent ids 574588536 / 459313176 and a p50
    # separation of 7,197 u that looked like a catastrophic desync.
    #
    # The test compares two MEASUREMENTS from this capture rather than a literal
    # threshold, because a literal is the thing that goes stale: an agent's declared
    # leg [ptime, stop] cannot outlast the capture that observed it. The bogus object
    # above declares a leg of 28 hours inside a 192 s run.
    wall = max((r["tick"] for r in cap.recs), default=0) - \
        min((r["tick"] for r in cap.recs), default=0)
    for addr, o in objs.items():
        o["impossible"] = 0
        if wall <= 0:
            continue
        for r in o["recs"]:
            # `.get`, because v1-v3 records have no `ptime` field at all and this
            # line used to KeyError on them -- `readhook.py --bin` CRASHED on run
            # 1, the arc's only v1 capture, while §4 pinned "a v1 capture still
            # parses" and was true only of the PARSE. See the note at the span.
            pt, st = r.get("ptime"), r.get("stop")
            if pt and st and st > pt and (st - pt) > wall:
                o["impossible"] += 1

    a("world copies (grouped by OBJECT ADDRESS, because one agent id names two):")
    for aid in sorted(byid):
        for addr in sorted(byid[aid]):
            o = objs[addr]
            tag = "WORLD_SYNC" if addr in sync else "other world"
            if not multi:
                tag = "only copy seen" if addr not in sync else tag
            ivs, path, zero = [], 0.0, 0
            seq = o["recs"]
            for i, r in enumerate(seq):
                pt, st = r.get("ptime"), r.get("stop")
                v = (_f(r["vel"][0]) ** 2 + _f(r["vel"][1]) ** 2) ** 0.5 \
                    if "vel" in r else 0.0
                if v > 1.0 and pt and st and st > pt:
                    ivs.append((pt, st))
                if i:
                    p, q = seq[i - 1], r
                    d = ((_f(q["point"][0]) - _f(p["point"][0])) ** 2
                         + (_f(q["point"][1]) - _f(p["point"][1])) ** 2) ** 0.5
                    if math.isfinite(d):
                        path += d
                        # A step that MOVED but did not advance +0x58, the stamp
                        # saying when m_point was valid. A walk always advances
                        # both; this is the signature of a write, not a walk.
                        if p.get("ptime") and q.get("ptime") == p.get("ptime") \
                                and d > 1.0:
                            zero += 1
            # THE MOTION WINDOW, AND THREE DEFECTS THIS BLOCK USED TO CARRY.
            #
            # It was `max(ptime) - min(ptime)` over every record, and that is
            # wrong three ways -- all three found by R7's scoring pass (§1z-k):
            #
            # (1) AN UNSET STAMP IS NOT A TIMESTAMP. Exactly two records per
            #     object -- the run's first `setter` and `bake`, both at t+0 --
            #     carry `ptime == 0`: an agent stamp the client had never set.
            #     They drag `min` to zero and inflate the denominator by the
            #     whole pre-capture uptime. On r7 that turned 193.5 s into
            #     280.6 s and printed "in motion 61.8%" where the truth is
            #     89.7% -- a 27-POINT ERROR FROM 2 RECORDS IN 1,785, and it is
            #     in EVERY v4+ capture in the corpus, not just this one.
            #     The existing "impossible leg" guard above cannot catch it:
            #     those records have `stop == 0` too, so `stop > ptime` is false
            #     and they are never examined. THAT GUARD TESTS THE LEG; THIS
            #     DEFECT IS IN THE STAMP.
            # (2) MOTION COULD EXCEED ITS OWN WINDOW. `stop` is a FUTURE arrival
            #     the client has predicted, so a leg can legitimately end after
            #     the last observation -- and merely dropping the zeros produced
            #     percentages over 100 (107.9% on run3-isle). We can only claim
            #     motion during the window we actually observed, so the legs are
            #     CLIPPED into it rather than the window stretched to fit them.
            # (3) IT CRASHED ON v1-v3, which have no `ptime` field at all.
            #     `readhook.py --bin` raised KeyError on run 1 -- the arc's only
            #     v1 capture -- while §4 pinned "a v1 capture still parses",
            #     which was true of the PARSE and not of the REPORT.
            #
            # The dropped stamps are COUNTED AND PRINTED, never silently
            # excluded: "we ignored 2 records" and "there were none" are
            # different facts, and the first is the one that explains a number.
            stamps = sorted(p for p in (r.get("ptime") for r in seq) if p)
            unset = sum(1 for r in seq if "ptime" in r and not r["ptime"])
            no_field = seq and "ptime" not in seq[0]
            a(f"  0x{addr:08X}  id {o['id']:<6} {tag}")
            a(f"      {len(seq):5} record(s)   "
              + ", ".join(f"{k} x{v}" for k, v in
                          sorted(o["sites"].items(), key=lambda kv: -kv[1])))
            span = (stamps[-1] - stamps[0]) if len(stamps) >= 2 else 0
            if span > 0:
                lo, hi = stamps[0], stamps[-1]
                clipped = [(max(s, lo), min(e, hi)) for s, e in ivs]
                moving = _union_ms([(s, e) for s, e in clipped if e > s])
                a(f"      in motion {moving / 1000.0:7.1f} s of {span / 1000.0:.1f} s "
                  f"({100.0 * moving / span:.1f}%), path {path:.0f} u")
                if unset:
                    a(f"      ({unset} record(s) carried an UNSET position stamp "
                      f"(+0x58 == 0) and are excluded from")
                    a("       the window -- an unset stamp is not a time. "
                      "Counting them put the")
                    a("       denominator before the capture began.)")
            elif no_field:
                a(f"      in motion: UNAVAILABLE -- a v{cap.version} record has "
                  f"no position stamp (+0x58),")
                a(f"       so this object has no motion window. path {path:.0f} u")
            else:
                a(f"      in motion: UNAVAILABLE -- fewer than 2 set position "
                  f"stamps. path {path:.0f} u")
            if no_field:
                a("      steps that moved but did NOT advance the position "
                  "stamp: UNAVAILABLE (no stamp)")
            else:
                a(f"      steps that moved but did NOT advance the position "
                  f"stamp: {zero}")
            if o.get("impossible"):
                a(f"      !! NOT AN AGENT: {o['impossible']} of {len(seq)} record(s) "
                  f"declare a movement leg")
                a(f"         longer than the whole {wall / 1000.0:.0f} s capture. "
                  f"Whatever this pointer is,")
                a("         it is not an agent, and its id and position are "
                  "meaningless. Check the")
                a("         site's `thiscall` row -- a register being SAVED does not "
                  "make it `this`.")
    if multi:
        a("")
        a(f"  !! {len(multi)} agent id(s) name MORE THAN ONE object: "
          + ", ".join(str(i) for i in sorted(multi)))
        a("     Do not build a trajectory by filtering on the id -- it interleaves")
        a("     two bodies, and the two copies genuinely sit hundreds of units")
        a("     apart. Group on the address, as this section does.")
    setter_i = bysite.get("setter")
    if setter_i is not None and sync:
        for addr in sorted(sync):
            if addr not in objs:
                continue
            o = objs[addr]
            n = o["sites"].get("setter", 0)
            a("")
            a(f"  the WORLD_SYNC copy 0x{addr:08X} took {n} setter call(s) -- "
              f"that is its ONLY")
            a("  source of destinations, so it is the count our server's "
              "movement grants")
            a("  have to be compared against.")
            # THE CADENCE, which is the quantity MOVECODE-K1 is built against
            # and the one a runsheet has to be able to read in one command.
            # Retail's figures are the control and are quoted beside ours so a
            # reader does not have to go and find them: FINDINGS §1i.4, 118 live
            # agents, denominators built the same way on both sides.
            ticks = sorted(r["tick"] for r in o["recs"]
                           if names[r["site"]] == "setter"
                           if r["site"] < len(names))
            if len(ticks) > 1:
                gaps = sorted((ticks[i] - ticks[i - 1]) / 1000.0
                              for i in range(1, len(ticks)))
                a(f"      grant gaps s: min {gaps[0]:.2f}  "
                  f"p50 {gaps[len(gaps) // 2]:.2f}  "
                  f"p90 {gaps[int(len(gaps) * 0.9)]:.2f}  max {gaps[-1]:.2f}"
                  f"   [retail p50 0.82]")
            # Density against the copy's OWN walked path. This is the sampled
            # chord sum and it UNDER-reads a curved path -- the sync copy is
            # sampled far more sparsely than the local one -- so it is labelled
            # rather than quietly compared against retail's granted-chain figure.
            path = 0.0
            seq = o["recs"]
            for i in range(1, len(seq)):
                d = ((_f(seq[i]["point"][0]) - _f(seq[i - 1]["point"][0])) ** 2
                     + (_f(seq[i]["point"][1]) - _f(seq[i - 1]["point"][1])) ** 2) ** 0.5
                if math.isfinite(d):
                    path += d
            if path > 0:
                a(f"      grants per 1000 u of its own SAMPLED path: "
                  f"{1000.0 * n / path:.2f}")
                a("        (a chord sum under-reads a curved path, and this copy "
                  "is sampled sparsely,")
                a("         so compare cadence above rather than this against "
                  "retail's 4.30 granted-chain)")
    return "\n".join(out)


def _pair_mfp(cap, names):
    """Join MapFindPath answers to their questions. -> (pairs, orphan_rets, esp_bad).

    THE KEY IS (tid, esp), AND IT AUDITS ITSELF. All four exits are
    `mov esp,ebp / pop ebp / ret`, so esp at a ret is EXACTLY the esp the entry
    hook saw for that invocation -- which makes esp both the join key and the
    check on the premise the join rests on. A candidate pair whose esp values
    disagree is NOT paired and is COUNTED: it refutes the epilogue reading rather
    than being a bad record, and a consumer must be able to see that happen.

    Per thread, entries are a STACK and a ret pops the innermost open one. The
    disassembly shows no self-call, so a non-empty stack at a second entry means
    the ring dropped a ret (or the function recursed after all, which would be a
    finding in itself) -- either way the older entry is abandoned rather than
    paired to a later answer.

    `pairs` are (entry, ret). Anything this cannot join with confidence is left
    out and counted, never guessed into a pair.
    """
    idx = {n: i for i, n in enumerate(names)}
    ei = idx.get(MFP_ENTRY)
    rset = {idx[n] for n in MFP_RETS if n in idx}
    if ei is None or not rset:
        return [], 0, 0
    open_by_tid, pairs, orphan, esp_bad = {}, [], 0, 0
    for r in sorted(cap.recs, key=lambda r: r["seq"]):
        if r["site"] == ei:
            open_by_tid.setdefault(r["tid"], []).append(r)
        elif r["site"] in rset:
            stack = open_by_tid.get(r["tid"]) or []
            if not stack:
                orphan += 1
                continue
            ent = stack.pop()
            if ent.get("esp") != r.get("esp"):
                esp_bad += 1
                continue
            pairs.append((ent, r))
    return pairs, orphan, esp_bad


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
      f"{cap.stored} record(s) stored, capture v{cap.version}")
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
    # A STRIDED SITE'S `stored` IS A SAMPLE, NOT A COUNT, and conflating the two
    # would break every rate in this arc silently. `hits` is always the census --
    # movehook increments it BEFORE the stride test -- so the row says which
    # number to use rather than leaving it to be inferred from the gap.
    strides = {}
    try:
        import gensites
        for _n, _r in gensites.rows()[0].items():
            if int(_r.get("stride") or 0) > 1:
                strides[int(_r["rva"])] = int(_r["stride"])
    except Exception:                                            # pragma: no cover
        pass
    for i, s in enumerate(cap.sites):
        nm = names[i] if i < len(names) else f"site{i}"
        stored = sum(1 for r in cap.recs if r["site"] == i)
        st = strides.get(int(s["rva"]))
        note = (f"   STRIDE 1-in-{st}: `stored` is a SAMPLE, use `hits`"
                if st else "")
        a(f"  {nm:10} va 0x{s['va']:08X}  hits {s['hits']:7}  "
          f"stored {stored}{note}")
    a("")

    idx = {nm: i for i, nm in enumerate(names)}

    a(_worlds(cap, names))
    a("")

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
            a(f"     m_point -> m_targetPoint at the teleport, {len(moved)} sample(s):")
            a(f"       min {moved[0]:8.1f}  p50 {moved[len(moved) // 2]:8.1f}  "
              f"max {moved[-1]:8.1f} units")
            # THIS IS LEG LENGTH, NOT WARP, AND THE CHAIN TEST BELOW IS WHY.
            # It was labelled "a visible warp" for two runs. `m_point` (+0x78) is
            # the last COMMITTED position -- the extrapolator only brings it forward
            # on demand -- so at the arrival tick it still holds where the leg
            # STARTED. The teleport commits the body to the leg's end. Measured
            # 2026-08-27 run 2: 25 of 25 consecutive teleports chain to EXACTLY
            # 0.00 (target[N] == m_point[N+1] to the bit), and the elapsed times
            # give ~282 u/s, ordinary walking speed. A 2,677 u warp in one tick
            # would be absurd; a 2,677 u leg over 9.5 s is a walk.
            # GROUPED BY OBJECT ADDRESS, because "consecutive" across a pooled
            # list is not consecutive for either body. ONE AGENT ID NAMES TWO
            # OBJECTS, and the pooled form interleaved them: on the R2 capture it
            # printed 25/124 while the two copies separately are 4/66 (local) and
            # 31/57 (sync). Every "did NOT chain" row it produced across that seam
            # is a comparison between one copy's target and the OTHER copy's next
            # point -- which is guaranteed not to link and means nothing. The line
            # below then read the total out as "candidates for a real divergence",
            # which is the same id-pooling defect sec.1i.1 already retracted a whole
            # analysis for, arriving in a second place.
            chain, per_obj = [], {}
            for r in sorted(tps, key=lambda x: x["seq"]):
                if not r["have_agent"]:
                    continue
                px, py = _f(r["point"][0]), _f(r["point"][1])
                prev = per_obj.get(r["ecx"])
                if prev is not None and all(map(math.isfinite, (px, py) + prev)):
                    chain.append(((px - prev[0]) ** 2 + (py - prev[1]) ** 2) ** 0.5)
                tx, ty = _f(r["target"][0]), _f(r["target"][1])
                per_obj[r["ecx"]] = ((tx, ty)
                                     if all(map(math.isfinite, (tx, ty))) else None)
            if chain:
                linked = sum(1 for d in chain if d < 0.01)
                a(f"       consecutive teleports that CHAIN exactly: "
                  f"{linked}/{len(chain)}   (per OBJECT, not pooled)")
                if linked == len(chain):
                    a("       -> every one links end-to-start, so the figures above")
                    a("          are LEG LENGTHS, not warps. A warp is the body")
                    a("          being somewhere the client did not walk it to, and")
                    a("          this tap cannot see that: it would need m_point")
                    a("          extrapolated by velocity (+0xB0/+0xB4) to the")
                    a("          arrival tick, which the record does not yet carry.")
                else:
                    a(f"       -> {len(chain) - linked} did NOT chain. Those are the")
                    a("          candidates for a real divergence; the rest are legs.")
    a("")

    # ---- v6: the FENCE, the FACING, and the two reseed ROUTES ----------------
    #
    # These fields were captured from the first v6 run and NOT printed, which is
    # the same class of defect as a field that was never captured: the answer sat
    # in the file and the readout said nothing. Run R2's five registered
    # predictions were scored out of a scratchpad script because of it.
    if cap.version >= 6:
        ai = idx.get("agtrack")
        ag = [r for r in cap.recs if r["site"] == ai] if ai is not None else []
        if ag:
            have = [r for r in ag if r.get("have_fence")]
            shut = [r for r in have if r["fence"] == 0]
            a("")
            a(f"FENCE  AgTrack's per-agent `clientControlled`, READ AT THE "
              f"DECISION over {len(ag)} agtrack entr(y|ies)")
            a(f"      read successfully : {len(have)}"
              f"  ({100.0 * len(have) / len(ag):.1f}%)")
            a(f"      SHUT (== 0)       : {len(shut)}")
            a(f"      OPEN (!= 0)       : {len(have) - len(shut)}")
            if len(have) < len(ag):
                a(f"      could NOT be read : {len(ag) - len(have)}"
                  f" -- `have_fence` keeps these OUT of the shut count, because")
                a("                          `could not read it` and `it was shut`"
                  " are different facts.")
            # THE BRANCH ORDER IS LOAD-BEARING, and a reader who does not know it
            # will build the wrong derived count. agtrack tests the fence at
            # 0x00606009 and the world at 0x00606013 -- FENCE FIRST -- so a shut
            # fence on a world-1 agent is a real suppression of a test that would
            # have been diverted anyway, and only a DIRECT read can see it.
            wshut = sum(1 for r in shut if r.get("src_world") == 1)
            if shut:
                a(f"      of the shut, on a world-1 (local) agent: {wshut}"
                  f", on a sync agent: {len(shut) - wshut}")
                a("      The fence is tested BEFORE the world check (0x00606009 vs")
                a("      0x00606013), so only the sync-side shuts suppressed a test")
                a("      that would otherwise have RUN. That is the number that")
                a("      bears on whether the fence suppresses anything.")
        # The two reseed routes. sec.1s.1: 0x00605EF6 is ResyncAllAsync, which
        # calls snaptest ZERO times -- so those reseeds passed NO gate. Pooling
        # them with the gated ones is what made every prior separation statistic
        # in this arc a mixture (readhook did exactly that until 2026-08-28).
        ri2 = idx.get("reseed")
        rr = [r for r in cap.recs if r["site"] == ri2] if ri2 is not None else []
        if rr:
            gated = [r for r in rr if reb(r["retaddr"]) == 0x006060E7]
            free = [r for r in rr if reb(r["retaddr"]) == 0x00605EF6]
            a("")
            a(f"RESEED ROUTES  {len(gated)} GATED (agtrack's loop, downstream of "
              f"snaptest), {len(free)} GATELESS (ResyncAllAsync)")
            if free:
                a("      A gateless reseed passed NO gate. sec.1s.1 found these are")
                a("      39.6% of the corpus and were a no-op there -- every one")
                a("      following closely on a gated snap that had just glued the")
                a("      copies, so that corpus could not see one fire COLD.")
        # The facing-9 early-out: snaptest returns 1 (NO SNAP) before any gate
        # when m_timeStopMovement != 0 AND facing == 9 (0x00605634 -> 0x00605641
        # -> 0x00605683 `mov eax, 1`). Both operands are on its arg2.
        s_i = idx.get("snaptest")
        sr = [r for r in cap.recs if r["site"] == s_i and r.get("have_src")] \
            if s_i is not None else []
        if sr:
            early = [r for r in sr if r.get("src_stop")
                     and r.get("src_facing") == FACING_EARLY_OUT]
            facs = {}
            for r in sr:
                facs[r.get("src_facing")] = facs.get(r.get("src_facing"), 0) + 1
            a("")
            a(f"FACING  snaptest's pre-gate early-out over {len(sr)} test(s) "
              f"carrying a source agent")
            a(f"      facing values seen: "
              + ", ".join(f"{k}x{v}" for k, v in
                          sorted(facs.items(), key=lambda kv: -kv[1])))
            a(f"      stop != 0 AND facing == {FACING_EARLY_OUT} (NO SNAP before "
              f"any gate): {len(early)}")
            if not early:
                a("      Zero means the client never entered that state here --")
                a("      NOT that the early-out does not exist. It is one walk.")
        # THE SetPosition CENSUS -- the backstop for the displacement detector,
        # and it is a RECALL check the detector cannot perform on itself.
        #
        # `reseed` reaches `SetPosition` (0x00602B20) at 0x00602369, and that
        # function is the only path that writes m_point (0x00602B7B) WITHOUT
        # stamping +0x58 -- which is exactly the signature the displacement
        # detector keys on. Its direct-write branch then calls agtrack
        # UNCONDITIONALLY at 0x00602BBD, so every such write returns to
        # 0x00602BC2 and is countable here with no threshold at all.
        #
        # WHY IT MATTERS: on the R2 capture the detector found 11 and this census
        # finds 15 -- 13 reseed-driven plus 2 the detector MISSED because the
        # stamp happened to advance across the record gap. 47.4% of local-copy
        # record gaps have the stamp advancing, so the detector is structurally
        # blind there; this count is not. A detector that cannot state its own
        # recall is the shape this arc keeps getting caught by.
        if ai is not None:
            sp = [r for r in cap.recs
                  if r["site"] == ai and reb(r["retaddr"]) == 0x00602BC2]
            if sp:
                a("")
                a(f"SetPosition CENSUS  {len(sp)} unstamped m_point write(s)")
                a("      Every one is a body relocated without a walk. This is the")
                a("      RECALL backstop for the DISPLACEMENT count below: compare")
                a("      the two, and if the displacement count is lower, the")
                a("      difference is warps the stamp-comparison could not see.")
        # ...AND WHICH CALLER, WHICH IS THE WHOLE REASON THE SITE EXISTS.
        #
        # THE TRAP, and it caught the orchestrator on the very first R3 readout:
        # the record stores the RETURN address, and every one of SetPosition's
        # seven callers is a 5-byte `call rel32`. A table keyed on the CALL
        # addresses -- which is how --xrefs prints them, and how FINDINGS and
        # content/movecode.toml both cite them -- reports every known caller as
        # UNKNOWN. reseed calls at 0x00602369 and returns to 0x0060236E.
        SP_CALLERS = {
            0x0060236E: "reseed 0x006022B0 -- the known warp path",
            0x00604A55: "0x00604880, called from AgApi (0x005FC110/0x005FC24A)",
            0x00606399: "0x00606120, called from AgTrack (0x006040BA/0x0060413A)",
            0x005FDAEA: "0x005FDAE5 -- never observed firing",
            0x005FDB4E: "0x005FDB49 -- never observed firing",
            0x005FF750: "0x005FF74B -- never observed firing",
            0x00602904: "0x006028FF -- never observed firing",
        }
        spi = idx.get("setposition")
        spr = [r for r in cap.recs if r["site"] == spi] if spi is not None else []
        if spr:
            a("")
            a(f"SetPosition CALLERS  {len(spr)} record(s) at the writer itself")
            by = {}
            for r in spr:
                by[reb(r["retaddr"])] = by.get(reb(r["retaddr"]), 0) + 1
            for v, n in sorted(by.items(), key=lambda kv: -kv[1]):
                who = SP_CALLERS.get(v, "!! NOT one of the seven known callers")
                a(f"      ret 0x{v:08X}  x{n:<4} {who}")
            unknown = [v for v in by if v not in SP_CALLERS]
            if unknown:
                a("      An unlisted return address is a caller --xrefs could not")
                a("      see, which is the same shape as MOVECODE-Q4. Check it is")
                a("      not simply a call site quoted where a RETURN belongs.")
            elif set(by) == {0x0060236E}:
                a("      ONLY reseed fired. The other six callers exist in the")
                a("      image and did not run on this walk -- which is a fact")
                a("      about the walk, not about the site.")

        # Gate 3, which has to be filtered: 0x005FEF70 has TWO direct callers and
        # only 0x0060581E is the gate. An unfiltered count is not a gate-3 count.
        ci = idx.get("stepclear")
        cr = [r for r in cap.recs if r["site"] == ci] if ci is not None else []
        if cr:
            g3 = [r for r in cr if reb(r["retaddr"]) == 0x0060581E]
            a("")
            a(f"GATE 3  {len(cr)} stepclear hit(s), of which {len(g3)} are GATE 3")
            a("      (retaddr 0x0060581E, inside snaptest). The rest are the")
            a("      obstacle-sidestep caller 0x006007A9 -- a real second caller,")
            a("      NOT a phantom, so an unfiltered count over-reads gate 3.")

    # ---- v7: THE ANSWER -- MapFindPath's four exits and their pathCount ------
    #
    # Every version before this captured the QUESTION and nothing else. The four
    # ret rows carry `out_count`, which is the client's own pathCount, and the
    # registered prediction (HANDOFF-PLANE.md §4.2, FINDINGS §1z-d.3) is scored
    # off it: a locked client's queries return 0, and the first query after a
    # repair's restamp returns > 0.
    #
    # THE PAIRING IS PRINTED AS A RATE, not assumed. A ret record joins its entry
    # on (tid, esp) -- see the note on `esp` above -- and an unpaired ret means
    # the ring dropped the question or the run armed mid-call. A low pairing rate
    # makes every comparison below it a statement about a biased subset, so it is
    # a headline rather than a footnote.
    if cap.version >= 7:
        ei = idx.get(MFP_ENTRY)
        rets = {n: idx.get(n) for n in MFP_RETS if idx.get(n) is not None}
        ents = [r for r in cap.recs if r["site"] == ei] if ei is not None else []
        rrs = [r for r in cap.recs if r["site"] in set(rets.values())]
        if ents or rrs:
            a("")
            a(f"MapFindPath ANSWERS  {len(ents)} question(s), {len(rrs)} answer(s) "
              f"over {len(rets)} armed exit(s)")
            pairs, unpaired_ret, mismatch = _pair_mfp(cap, names)
            if ents:
                a(f"      paired to their question : {len(pairs)} of {len(ents)}"
                  f"  ({100.0 * len(pairs) / len(ents):.1f}%)")
            if unpaired_ret:
                a(f"      answers with NO question : {unpaired_ret}"
                  f" -- the ring dropped it, or the hook armed mid-call")
            if mismatch:
                a(f"      *** esp MISMATCH on {mismatch} pair(s): the entry and the")
                a("          ret disagree about esp, which REFUTES the premise this")
                a("          tap rests on (all four exits are `8B E5 5D C3`, so the")
                a("          two must be equal). These are NOT paired. Re-read the")
                a("          epilogues before trusting any comparison here.")
            got = [r for r in rrs if r.get("have_out", 0) & 1]
            zero = [r for r in got if r["out_count"] == 0]
            a(f"      pathCount READ           : {len(got)} of {len(rrs)}")
            if len(got) < len(rrs):
                a(f"      could NOT be read        : {len(rrs) - len(got)}"
                  f" -- `have_out` keeps these OUT of the zero count, because")
                a("                                 `could not read it` and `the")
                a("                                 client answered ZERO` are")
                a("                                 different facts, and the zero")
                a("                                 IS the registered prediction.")
            a(f"      pathCount == 0 (no path) : {len(zero)}")
            a(f"      pathCount >  0           : {len(got) - len(zero)}")
            trunc = [r for r in rrs if (r.get("have_out", 0) & 2)
                     and r["out_n"] < r["out_count"]]
            if trunc:
                a(f"      path TRUNCATED by the record : {len(trunc)}"
                  f" (out_n < out_count; capacity "
                  f"{ret_capacity(trunc[0])} points in a v{cap.version} record)")
                a("          The COUNT is still exact -- only the stored waypoints")
                a("          are short. Compare counts freely; compare shapes only")
                a("          on the untruncated ones.")
            # WHICH ARM, and it is deliberately NOT captioned as an outcome.
            # 0x0070A0D4 is TWO exits sharing one epilogue (the ordinary
            # completion and the fallback-solver path), so the four sites do not
            # partition the answers -- content/movecode.toml's ret4 `limits` says
            # so, and a report that implied otherwise would be inventing a
            # taxonomy the code does not have.
            a("      by exit arm (WHICH DOOR, not which outcome -- ret4 is two):")
            for n in MFP_RETS:
                si2 = idx.get(n)
                if si2 is None:
                    continue
                arm = [r for r in rrs if r["site"] == si2]
                az = sum(1 for r in arm
                         if (r.get("have_out", 0) & 1) and r["out_count"] == 0)
                a(f"        {n:18s} {len(arm):5d}   pathCount==0: {az}")

    a("")

    # ---- the SNAP: a correction decided, applied, and how far it moved -------
    si, ri = idx.get("snaptest"), idx.get("reseed")
    if si is not None or ri is not None:
        tests = [r for r in cap.recs if r["site"] == si] if si is not None else []
        seeds = [r for r in cap.recs if r["site"] == ri] if ri is not None else []
        a("")
        a(f"SNAP  {len(tests)} desync test(s) -> {len(seeds)} reseed(s) APPLIED")
        if tests and not seeds:
            a("      Every test passed: the client judged itself in sync and")
            a("      corrected nothing. That is a real absence, not a miss.")
        for label, rows in (("test", tests), ("reseed", seeds)):
            if not rows:
                continue
            by = {}
            for r in rows:
                by[reb(r["retaddr"])] = by.get(reb(r["retaddr"]), 0) + 1
            a(f"      {label} caller(s): "
              + ", ".join(f"0x{v:08X} x{n}" for v, n in
                          sorted(by.items(), key=lambda kv: -kv[1])))
        # SEPARATION is what gate 1 judges, and with both agents captured it can be
        # recomputed here rather than inferred -- an entry hook cannot see which
        # gate the function chose.
        # ONLY WHERE BOTH SIDES ARE THE SAME AGENT. A separation between two
        # DIFFERENT agents is not a desync, it is the distance between two
        # characters -- and run 5 produced exactly that trap: 70 records whose
        # `this` block was readable memory that is not an agent at all (ids
        # 574588536 and 459313176), giving a p50 of 7,197 u that looked like a
        # catastrophic desync and was nothing of the kind. Pairing on the id is
        # what makes the number mean what its label says.
        sep, mismatched = [], 0
        for r in tests + seeds:
            if not (r.get("have_agent") and r.get("have_src")):
                continue
            if r["id"] != r["src_id"]:
                mismatched += 1
                continue
            ax, ay = _f(r["point"][0]), _f(r["point"][1])
            bx, by_ = _f(r["src_point"][0]), _f(r["src_point"][1])
            if all(map(math.isfinite, (ax, ay, bx, by_))):
                sep.append(((ax - bx) ** 2 + (ay - by_) ** 2) ** 0.5)
        if mismatched:
            a(f"      ({mismatched} record(s) EXCLUDED: `this` and the source are "
              f"different agent ids,")
            a("       so their distance is not a desync. Check the site's row "
              "before reading")
            a("       this as a client-side fact -- it usually means something is "
              "being")
            a("       dereferenced that is not an agent.)")
        if sep:
            sep.sort()
            a(f"      separation `this` vs the SOURCE agent, {len(sep)} sample(s):")
            a(f"        min {sep[0]:8.1f}  p50 {sep[len(sep) // 2]:8.1f}  "
              f"max {sep[-1]:8.1f} units")
            a(f"        over 100.0 (the history band): "
              f"{sum(1 for d in sep if d > 100.0)}")
            a(f"        over 299.33 (gate 1's effective cut): "
              f"{sum(1 for d in sep if d > 299.332591)}")
        elif tests or seeds:
            a("      !! no record carries BOTH agents, so the separation gate 1")
            a("         judges cannot be recomputed. A capture before v5 records")
            a("         only `this`, which is half of a correction.")
        # WHICH RESEEDS ACTUALLY MOVED THE PLAYER, and this is the number
        # MOVECODE-K1's prediction is REFUTED by. A reseed that fires is not a
        # warp -- run 5 had 14 reseeds and 2 displacements -- so counting
        # reseeds alone would score a candidate that fires less but warps more
        # as an improvement, which is how four of the five dead candidates in
        # the authsrv graveyard flattered themselves.
        #
        # The signature is exact and needs no threshold: a WALK always advances
        # both m_point (+0x78) and the stamp at +0x58 saying when m_point was
        # valid. A displacement moves the point with the stamp STANDING STILL.
        # FINDINGS §1j.4: 10 such steps on the local copy, 0 on the sync copy,
        # and the two after a reseed are the two real warps.
        moved = []
        for addr, seq in _by_object(cap, names).items():
            for i in range(1, len(seq)):
                p, q = seq[i - 1], seq[i]
                # The displacement signature IS the stamp standing still, so a
                # record with no stamp cannot carry it -- and reading the field
                # unguarded is the second half of the v1-v3 KeyError that made
                # `readhook.py --bin` crash on run 1. An absent stamp is not a
                # stamp that failed to advance.
                if not p.get("ptime") or q.get("ptime") != p.get("ptime"):
                    continue
                d = ((_f(q["point"][0]) - _f(p["point"][0])) ** 2
                     + (_f(q["point"][1]) - _f(p["point"][1])) ** 2) ** 0.5
                if not (math.isfinite(d) and d > 1.0):
                    continue
                prev_site = (names[p["site"]] if p["site"] < len(names)
                             else str(p["site"]))
                moved.append((prev_site, d, q["_i"] if "_i" in q else i))
        # THE HEADLINE IS THE SIZE, NOT THE ATTRIBUTION, and that ordering is a
        # correction paid for in a real run. MOVECODE-K1's arm A printed
        # "following a RESEED: 0" and read as clean, while the operator watched
        # the character warp to spawn twice -- because both warps went through
        # the TELEPORT arm (`teleport -> setter`) rather than landing on the
        # record straight after a reseed. They were counted and then buried
        # under a subcount that happened to be zero.
        #
        # A displacement is a displacement whichever site performed it. The
        # attribution is detail; the magnitude is the finding, and arm A's
        # 5,970 u against run 5's largest of 1,871 u is not a rounding
        # difference -- it is 3.2x, and it landed on the spawn point.
        by_site = {}
        for site, d, _i in moved:
            by_site.setdefault(site, []).append(d)
        a(f"      DISPLACEMENTS -- the point moved with its stamp STANDING "
          f"STILL: {len(moved)}")
        if moved:
            ds = sorted((d for _s, d, _i in moved), reverse=True)
            a(f"        largest {ds[0]:.0f} u   total {sum(ds):.0f} u   "
              f"all: " + ", ".join(f"{d:.0f}" for d in ds[:8])
              + (" …" if len(ds) > 8 else ""))
            for site in sorted(by_site, key=lambda s: -max(by_site[s])):
                v = sorted(by_site[site], reverse=True)
                a(f"        after {site:<10} x{len(v):<3} largest {v[0]:.0f} u")
            # ...AND THE PRECEDING-SITE LABEL IS NOT THE CAUSE. Read literally it
            # says two mechanisms; on the R2 capture it printed "after teleport
            # x10, after reseed x1" and there is only ONE. `reseed` calls the
            # halt-in-place 0x00602540 at 0x006022E7 when the body is moving, and
            # THAT calls the teleport at 0x006025A6 -- so the teleport sitting in
            # front of a displacement is reseed's own child, not a rival cause.
            # Every displacement in that run followed a GATED reseed, 1:1 with the
            # 11 gated reseeds. The label is a position in the record, not an
            # attribution, and it is printed that way from 2026-08-28.
            if "teleport" in by_site or "reseed" in by_site:
                a("        (`after <site>` is the PRECEDING RECORD, not the cause:")
                a("         reseed -> 0x00602540 halt-in-place -> teleport is one")
                a("         chain, so `after teleport` and `after reseed` are the")
                a("         same event seen at two points. Attribute on the reseed")
                a("         caller -- gated 0x006060E7 vs gateless 0x00605EF6.)")
        a("        A reseed that FIRES is not a warp -- but a displacement IS "
          "one, whatever")
        a("        site performed it. MOVECODE-K1 (FINDINGS §1k.3) is refuted "
          "by the SIZE")
        a("        and COUNT here, not by the reseed row alone. RUN 5 "
          "BASELINE: 10 displacements,")
        a("        largest 1871 u, total 8527 u. (691 u was run 5's largest "
          "RESEED-attributed one,")
        a("        which is the subcount that read as clean while arm A warped "
          "to spawn.)")

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
    text, rc = report(cap, site_names(cap), args.dump)
    print(text)
    return rc


if __name__ == "__main__":
    sys.exit(main())
