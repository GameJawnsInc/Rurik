"""Census the PLANE channel over the gamesrv capture corpus, and replay the repair.

The server-side counterpart to `noclipscore.py` section C. That one scores the
plane word a movehook capture recorded at the CLIENT; this one scores the plane
word on every `position_report` the SERVER accepted, which is a corpus three
orders of magnitude larger (11,754 scorable reports against a handful).

Born from HANDOFF §D, which asked for exactly this and named four things it
would settle. What it actually settled, and what it overturned on the way:

THE MESH IS PINNED, NEVER SELECTED -- and the pin is IN BAND.
`noclipscore.py` states the first half of that rule and then hand-pins map 280,
because the coverage-score selector demonstrably picks the wrong map (§1v.3).
`pathdiff.py` refuses outright and makes `--map` a value a human types from
memory. Neither is necessary: the capture records the mesh itself.

DO NOT use the `version` record's `map_id`. It says 148 in 1,206 of 1,212 files
and it is what the CLIENT ASKED FOR, emitted before `--map`/`--file-id` rewrite
anything -- grep `client asked for map` in `authsrv.py`. Map 148's own spawn is
15,000 u from where most of the corpus's reports are.

THE AUTHORITY IS THE SERVER'S OWN LOAD MESSAGE. Every capture carries a `sent`
record with opcode 405 (0x0195) whose label reads

    INSTANCE_LOAD_SPAWN_POINT(file 165811)

which is the file id the server actually sent. Measured over all 1,212 files:
zero captures carry two distinct ids, and **all 12,215 position_reports are
ATTRIBUTED**, across 8 id spellings / 7 meshes. Attributed is not scoreable:
12,077 have a mesh in the default archive and 11,754 survive the stub guard. The harness `gamesrv.log` is
kept as a SECOND WITNESS and agrees on 172 of 172 it can see -- two independent
records of one fact, which is how a pin stops rotting. (It read 171-of-172
until this file's harness reader stopped truncating at 4 KB; fifteen logs print
their navmesh line past byte 4000, and the lone "disagreement" was that
truncation. A third key exists if ever needed: the harness log's
`[c1] GAME version: ... world_id=... player_id=...` joins 1:1 to the capture's
own `version` record, 1,201 keys with zero collisions.)

THE ARCHIVE IS PART OF THE PIN. A file id does not name geometry on its own:
0x287D3 decodes to 27 trapezoids in `vault/dat_study/Gw.dat` and 2 in the
`-probe` copy, and 0x5F0B2 (138 reports) binds in `-probe` ALONE. Scoring
0x287D3's 318 reports against a 1-plane, 27-trapezoid stub reports 61.3%
OFF-MESH (195 of 318),
which reads as a decode failure and is really an empty mesh. So this prints what
each mesh decoded to and REFUSES to fold a stub into the headline.

WHY NOT THE GEOMETRIC IDENTIFIER, which already exists in `pathdiff.map_scores`:
because a real label set lets it be SCORED for the first time, and `--identify`
does. Of 58 identifications it ACCEPTS, 16 are wrong. The split is stark --
28 accepted WITH non-zero plane signal, 0 wrong; 30 accepted on the all-plane
fallback, 16 wrong -- and its own docstring already expects that fallback to be
worthless and the refusal bar to catch it. The bar does not: at n = 3-5 points
one mesh reaches 1.000 while the runner falls below 0.8, so the margin passes.

BUT DO NOT READ THAT AS "REFUSE WHEN nz_land == 0 AND YOU ARE DONE." All 16
failures share a second property exactly: their TRUE mesh is 0x287D3, the
27-trapezoid stub. "No plane signal" and "the right answer is a nearly empty
mesh that loses on coverage to anything" are perfectly confounded here, so this
corpus CANNOT separate them and the cause is not identified. The observation is
solid; the fix it implies is not. Treat it as a measurement, not a mandate.

THREE WRONG TURNS ARE RECORDED HERE SO THEY ARE NOT RETAKEN, and each was
caught by a control rather than by review:
  1. Scoring the tripwire from `grant_verdict.plane_dest` at
     `grant_verdict.dest` looked structural and right; the control against the
     live tripwire's own sessions read 0/0/5 against a logged 4/30/9.
  2. Reading 0x0029's trailing dword as ONE u32 plane published 15.29%. It is
     TWO u16s -- the tell was "we emit plane 1703962", which is 0x001A001A, the
     label's own "26->26".
  3. Scoring 0x0029 ALONE and skipping the tripwire's `values[0] !=
     PLAYER_AGENT_ID` gate. `_note_wire_move` says its surface is THREE opcodes
     and only the player's agent; the corrected rate is 282/7,543 -- quote it as
     ~3.7%, since two careful independent re-derivations of the same quantity
     landed on 3.74% and 3.78% and differ on a labelling convention alone.
The label's own orientation is worth stating once: on the arrow form
("... on plane X->Y") X is planeB and Y is planeA, 507/507 among the rows that
can discriminate; on the single-plane form ("ZERO LEAD ... plane N") N is
planeA, 322/322.

Usage:
  python toolkit/clientscan/planecensus.py                    # census + replay
  python toolkit/clientscan/planecensus.py --identify         # score the
                                                              # geometric
                                                              # identifier
  python toolkit/clientscan/planecensus.py --echo             # tripwire, with
                                                              # a denominator
  python toolkit/clientscan/planecensus.py --max-lag 60       # tighter pairing
  python toolkit/clientscan/planecensus.py --archive <Gw.dat>  # 0x287D3 and
                                                               # 0x5F0B2 move
                                                               # between archives
  python toolkit/clientscan/planecensus.py --focus <capture>   # ONE session
                                                               # against the
                                                               # corpus
  python toolkit/clientscan/planecensus.py --armed             # split by
                                                               # whether the
                                                               # repair RAN

WHY `--armed` EXISTS. The census reads 134 captures as one population and it is
two. The repair shipped at `dcf9484`, 2026-08-29 11:22:45; everything earlier is
REPLAY. Split that way, 3 captures and 549 reports are prospective and 131 and
11,205 are not -- and the two halves of the repair's case do not overlap at all:
every logged echo is armed, every replayed fire is not. Nothing in the record
both fired and was watched. Armed-ness is read from the BANNER, never the date,
because a run can pass --no-plane-repair (FINDINGS 1z-o.10).

WHY `--focus` EXISTS, since a per-capture count looks like something you could
read off the census yourself: a session's disagreement count is uninterpretable
without knowing what ELSE was exposed to the same geometry. R7 supplies every
`offered [37]` disagreement in the corpus, which sounds decisive until you ask
whether anyone else stood there -- three sessions did, one of them with nearly
twice the exposure, and none of them disagreed (FINDINGS 1z-o.7). The exposure
block is the part that separates "the map does this" from "this session did
this", and it is the reason this is a mode rather than a spreadsheet.

Every section prints its denominator, and a section with nothing to score says
so rather than printing a reassuring zero -- `noclipscore.py`'s rule, inherited
for the same reason it was written.
"""
import argparse
import collections
import datetime as dt
import glob
import json
import math
import os
import re
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLKIT = os.path.dirname(_HERE)
for _p in (_TOOLKIT, os.path.join(_TOOLKIT, "mapdata")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pathmap import PathingMap                          # noqa: E402
from archive import Archive, file_id_table              # noqa: E402
import vaultpath                                        # noqa: E402

_TS = re.compile(r"(\d{8}T\d{6})")
_OVERRIDE = re.compile(r"MAP OVERRIDE:\s*(\d+)")
_NAVMESH = re.compile(r"\[map\]\s+navmesh\s+0x([0-9A-Fa-f]+)")
# The in-band pin: the server's own INSTANCE_LOAD_SPAWN_POINT, opcode 0x0195.
_LOADFILE = re.compile(r"INSTANCE_LOAD_SPAWN_POINT\(file (\d+)\)")
INSTANCE_LOAD = 405

# A mesh with fewer trapezoids than this is a stub, not geometry: 0x287D3
# decodes to 27 in dat_study and 2 in -probe, and either way its reports score
# as OFF-MESH for a reason that says nothing about the client.
STUB_TRAPS = 200

# Read from authsrv.py -- grep "PLANE_REPAIR_HOLD = ". Mirrored, not imported:
# authsrv.py opens sockets at import time.
HOLD = 5.0
GAP = 5.0
MIN_INTERVAL = 10.0

# THE TRIPWIRE'S WHOLE SURFACE IS THREE OPCODES, not one. `_note_wire_move` in
# authsrv.py says so in as many words -- "Three opcodes move the authoritative
# copy of the PLAYER's agent and no others do (0x0025 and 0x002B do not name a
# point)". Scoring only 0x0029 undercounts. Corpus census: 9,168 sends of
# 0x0029, 1 of 0x002A, 30 of 0x002C.
MOVE_TO_POINT = 41            # 0x0029, 18 bytes
UPDATE_DESTINATION = 42       # 0x002A, 22 bytes
UPDATE_POSITION = 44          # 0x002C, 16 bytes
TRIPWIRE_OPS = (MOVE_TO_POINT, UPDATE_DESTINATION, UPDATE_POSITION)

# Layout shared by all three: opcode u16 | agent u32 | x f32 | y f32 | plane u16
# [| planeB u16 on 0x0029]. In authsrv's terms `values` is
# [agent, (x, y), planeA, planeB], so the tripwire's `values[2]` IS planeA at
# offset 14 -- which the schema settles structurally and a control against the
# live tripwire's own sessions confirms at 4/30/9.
_PLANE_A = 14
_PLANE_B = 16

# `if not values or values[0] != PLAYER_AGENT_ID: return` -- the tripwire never
# speaks about anyone but the player. grep "^PLAYER_AGENT_ID" in authsrv.py.
PLAYER_AGENT_ID = 1


# ---------------------------------------------------------------- corpus ----

def default_vault():
    """The vault, via toolkit/vaultpath.py -- never <this tree>/vault.

    A git worktree has no vault of its own, so joining THIS tree's root with
    "vault" names a directory that does not exist there, and the census refuses
    having read zero captures (this happened on 2026-08-30, the day after this
    file was written). vaultpath resolves the one real vault beside the main
    working tree from any tree, and honours RURIK_VAULT.
    """
    return vaultpath.vault_root()


def harness_labels(vault):
    """-> {datetime: (map_id, navmesh_fid, dirname)} from harness gamesrv.logs."""
    out = {}
    base = os.path.join(vault, "captures", "harness")
    if not os.path.isdir(base):
        return out
    for d in sorted(os.listdir(base)):
        m = _TS.fullmatch(d)
        if not m:
            continue
        log = os.path.join(base, d, "gamesrv.log")
        if not os.path.isfile(log):
            continue
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                # NOT read(4000). Fifteen harness logs print their
                # "[map] navmesh 0x..." line at byte 4087-10239, and a 4 KB
                # window silently loses them -- which drops 7 captures and 21
                # disagreements and moves the headline from 259 to 238. A
                # truncated read here does not error, it under-reports.
                head = fh.read(65536)
        except OSError:
            continue
        mo, nm = _OVERRIDE.search(head), _NAVMESH.search(head)
        if not mo and not nm:
            continue
        out[dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")] = (
            int(mo.group(1)) if mo else None,
            int(nm.group(1), 16) if nm else None, d)
    return out


def read_capture(path):
    """-> (reports, sends, logged_echoes, file_ids). One pass, four populations."""
    reports, sends, echoes, fids = [], [], 0, set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if ('"position_report"' not in line and '"sent"' not in line
                    and '"plane_echo"' not in line):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            kind = r.get("kind")
            if kind == "sent" and r.get("opcode") == INSTANCE_LOAD:
                m = _LOADFILE.search(r.get("label") or "")
                if m:
                    fids.add(int(m.group(1)))
                continue
            if kind == "plane_echo":
                echoes += 1
            elif kind == "position_report":
                rp = r.get("reported")
                if not rp or r.get("plane") is None:
                    continue
                reports.append({
                    "t": r.get("t", 0.0), "x": float(rp[0]), "y": float(rp[1]),
                    "plane": int(r["plane"]), "source": r.get("source"),
                    "accepted": bool(r.get("accepted")),
                    "reason": r.get("reason")})
            elif kind == "sent" and r.get("opcode") in TRIPWIRE_OPS:
                got = parse_move(r.get("plain") or "")
                if got:
                    sends.append({"t": r.get("t", 0.0), "x": got[0],
                                  "y": got[1], "plane": got[2],
                                  "plane_b": got[3], "opcode": got[4],
                                  "label": r.get("label")})
    return reports, sends, echoes, fids


def parse_move(plain):
    """-> (x, y, planeA, planeB, opcode) or None. THE PLAYER'S AGENT ONLY.

    Returns None for another agent, mirroring the tripwire's own first line
    (`values[0] != PLAYER_AGENT_ID: return`). Without that gate the denominator
    counts sends the tripwire never judged.
    """
    try:
        b = bytes.fromhex(plain)
    except ValueError:
        return None
    if len(b) < 16:
        return None
    op = struct.unpack_from("<H", b, 0)[0]
    if op not in TRIPWIRE_OPS:
        return None
    if struct.unpack_from("<I", b, 2)[0] != PLAYER_AGENT_ID:
        return None
    x, y = struct.unpack_from("<ff", b, 6)
    a = struct.unpack_from("<H", b, _PLANE_A)[0]
    bb = (struct.unpack_from("<H", b, _PLANE_B)[0]
          if len(b) >= _PLANE_B + 2 else a)
    return (x, y, a, bb, op)


def label_captures(vault, max_lag):
    """-> ({capture: label}, [unlabelled], crosscheck).

    The label comes from the capture's OWN opcode-405 load message. The harness
    log is read too, but only to cross-check: two independent witnesses to the
    same fact, and a disagreement between them is a finding, not a tie to break.
    """
    harness = harness_labels(vault)
    keys = sorted(harness)
    out, unlabelled = {}, []
    cross = collections.Counter()
    pat = os.path.join(vault, "captures", "gamesrv", "*.jsonl")
    for f in sorted(glob.glob(pat)):
        name = os.path.basename(f)
        reports, sends, _e, fids = read_capture(f)
        # A capture with no position_reports still has SENDS, and the echo
        # channel scores sends. Dropping it here silently shrank --echo's
        # denominator: `authsrv-20260819T111858` holds zero reports and exactly
        # one tripwire-eligible send -- the corpus's ONLY 0x002A -- and that
        # send is a TRIP. The bug read 281/7,542 where the truth is 282/7,543.
        # Keep anything that carries EITHER population.
        if not reports and not sends:
            continue
        if len(fids) > 1:
            cross["capture declares MORE THAN ONE file id"] += 1
        if not fids:
            unlabelled.append(name)
            continue
        fid = sorted(fids)[0]

        hf = hm = None
        lag = None
        m = _TS.search(name)
        if m:
            stamp = dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
            cand = [k for k in keys
                    if k <= stamp and (stamp - k).total_seconds() <= max_lag]
            if cand:
                k = max(cand)
                hm, hf = harness[k][0], harness[k][1]
                lag = (stamp - k).total_seconds()
        if hf is None:
            cross["no harness witness"] += 1
        elif (hf & 0x7FFFFFFF) == (fid & 0x7FFFFFFF):
            cross["harness AGREES"] += 1
        else:
            cross["harness DISAGREES"] += 1

        out[name] = {"path": f, "fid": fid, "map_id": hm,
                     "harness_fid": hf, "lag": lag, "n": len(reports)}
    return out, unlabelled, cross


class Meshes:
    """Load-once cache, bound to ONE archive.

    THE ARCHIVE IS PART OF THE ANSWER, not a detail. `0x287D3` decodes to 27
    trapezoids in `dat_study`, 55 in `-c2`, 2 in `-probe` and 64 in
    `reskin-roster`, and `0x5F0B2` binds in `-probe` ALONE. Any number this
    file prints about those two meshes is archive-scoped and must be quoted
    with the archive named. The meshes that carry the corpus -- `0x1B97D`,
    `0x287B3`, `0x345CC`, `0xB602`, `0x5D037` -- are identical across all 17
    vaulted archives, which is why the headline survives the choice.
    """

    def __init__(self, path=None):
        self._ar = Archive(path) if path else Archive()
        self._table = file_id_table(self._ar)
        self._cache = {}

    def get(self, fid):
        if fid is None:
            return None
        if fid not in self._cache:
            pm = None
            # TWENTY-FIVE IDS CARRY BIT 31 and the client does not mask (see
            # file_id_table's docstring). 0x8001B97D binds nothing here; masked
            # it is 0x1B97D. Try the id as sent first, then masked.
            for cand in (fid, fid & 0x7FFFFFFF):
                try:
                    pm = PathingMap.load(cand, archive=self._ar,
                                         table=self._table)
                    break
                except Exception:
                    continue
            self._cache[fid] = pm
        return self._cache[fid]

    def key(self, fid):
        """A stable display name that carries the geometry's own size."""
        pm = self.get(fid)
        if pm is None:
            return f"0x{fid:X}/UNBOUND"
        return f"0x{fid & 0x7FFFFFFF:X}/{len(pm.trapezoids)}t"

    def is_stub(self, fid):
        pm = self.get(fid)
        return pm is not None and len(pm.trapezoids) < STUB_TRAPS

    def archive_path(self):
        for a in ("path", "_path", "filename", "_filename"):
            v = getattr(self._ar, a, None)
            if isinstance(v, str):
                return v
        return "(unknown)"


# ---------------------------------------------------------------- census ----

def census(paired, meshes):
    """Score every accepted report's declared plane against what the mesh offers."""
    tot = collections.Counter()
    bymap = collections.defaultdict(collections.Counter)
    percap = collections.Counter()
    offered_hist = collections.Counter()
    direction = collections.Counter()
    rows = []
    for name, lab in sorted(paired.items()):
        pm = meshes.get(lab["fid"])
        if pm is None:
            tot["reports on a mesh this archive does not bind"] += lab["n"]
            continue
        reports, _sends, _e, _f = read_capture(lab["path"])
        if not reports:
            continue
        mk = meshes.key(lab["fid"])
        stub = meshes.is_stub(lab["fid"])
        for r in reports:
            bymap[mk]["reports"] += 1
            offered = sorted({t.plane for t in pm.containing(r["x"], r["y"])})
            bymap[mk]["reports_"] += 1
            if stub:
                # A 27-trapezoid mesh cannot speak about a player's plane. Its
                # reports are counted where they can be seen and kept OUT of
                # the headline, rather than averaged in as 69% off-mesh.
                tot["reports on a STUB mesh (excluded from headline)"] += 1
                if not offered:
                    bymap[mk]["off-mesh"] += 1
                elif r["plane"] in offered:
                    bymap[mk]["AGREE"] += 1
                else:
                    bymap[mk]["DISAGREE"] += 1
                continue
            tot["reports"] += 1
            offered_hist[len(offered)] += 1
            if not offered:
                tot["off-mesh"] += 1
                bymap[mk]["off-mesh"] += 1
                continue
            tot["on-mesh"] += 1
            bymap[mk]["on-mesh"] += 1
            zero = "declared 0" if r["plane"] == 0 else "declared non-zero"
            if r["plane"] in offered:
                tot["AGREE"] += 1
                tot[f"AGREE, {zero}"] += 1
                bymap[mk]["AGREE"] += 1
                continue
            tot["DISAGREE"] += 1
            tot[f"DISAGREE, {zero}"] += 1
            bymap[mk]["DISAGREE"] += 1
            percap[name] += 1
            fix = pm.plane_at(r["x"], r["y"], prefer=r["plane"])
            # THE TRIGGER NEVER SEES ALL OF THEM. `_maybe_plane_repair` is
            # called from the 0x003D arm only and the track drops a refused
            # report, so a stop-report or a reject is not evidence about the
            # repair at all -- 20 of the corpus's disagreements are exactly
            # that, and counting them inflates the exposure.
            gated = r["accepted"] and r["source"] == "0x003D"
            if fix is None:
                tot["DISAGREE on a STACK -> repair DISARMS"] += 1
            else:
                tot["DISAGREE unambiguous -> trigger proceeds"] += 1
                if gated:
                    tot["DISAGREE unambiguous AND reaching the trigger"] += 1
            if r["plane"] != 0 and offered == [0]:
                direction["client declares N, mesh offers only 0"] += 1
            elif r["plane"] == 0 and 0 not in offered:
                direction["client declares 0, mesh offers only N"] += 1
            else:
                direction["client declares N, mesh offers a different N"] += 1
            rows.append({"cap": name, "map": mk, "t": r["t"],
                         "x": r["x"], "y": r["y"], "plane": r["plane"],
                         "offered": offered, "fix": fix,
                         "accepted": r["accepted"], "source": r["source"]})
    return tot, bymap, percap, offered_hist, direction, rows


# ---------------------------------------------------------------- replay ----

def replay(reports, pm):
    """`plane_repair_track`, transcribed clause for clause. -> (fires, best, why).

    Mirrored rather than imported for the reason the constants are: importing
    authsrv.py opens sockets. If that function changes, this goes stale -- which
    is what `test_planecensus.py` section 3 exists to catch.
    """
    st = {"pt": None, "since": None, "last": None, "fired_at": None}
    fires, best = [], 0.0
    why = collections.Counter()
    for r in reports:
        now = r["t"]
        # `_maybe_plane_repair` is called from the 0x003D arm only, so a stop
        # report never reaches the track and cannot reset it.
        if r["source"] != "0x003D":
            why["ignored: not a 0x003D report"] += 1
            continue
        if not r["accepted"]:
            st["pt"] = None
            why["report-refused"] += 1
            continue
        pt = (r["x"], r["y"])
        if not (math.isfinite(pt[0]) and math.isfinite(pt[1])):
            st["pt"] = None
            why["bad-point"] += 1
            continue
        offered = {t.plane for t in pm.containing(pt[0], pt[1])}
        if not offered:
            st["pt"] = None
            why["off-mesh"] += 1
            continue
        if r["plane"] in offered:
            st["pt"] = None
            why["plane-legal"] += 1
            continue
        fix = pm.plane_at(pt[0], pt[1], prefer=r["plane"])
        if fix is None:
            st["pt"] = None
            why["ambiguous"] += 1
            continue
        gap_from = st["last"]
        st["last"] = now
        if st["pt"] != pt:
            st.update(pt=pt, since=now)
            why["arming"] += 1
            continue
        if gap_from is not None and now - gap_from > GAP:
            st["since"] = now
            why["stale-stream"] += 1
            continue
        streak = now - st["since"]
        best = max(best, streak)
        if streak < HOLD:
            why["holding"] += 1
            continue
        if st["fired_at"] is not None and now - st["fired_at"] < MIN_INTERVAL:
            why["rate-limited"] += 1
            continue
        st["fired_at"] = now
        why["WOULD FIRE"] += 1
        fires.append({"t": now, "point": list(pt), "plane": r["plane"],
                      "fix": fix, "offered": sorted(offered),
                      "held": round(streak, 2)})
    return fires, best, why


# ------------------------------------------------------------------ echo ----

def echo_census(paired, meshes):
    """The plane_echo tripwire's missing denominator, scored from the wire."""
    tot = collections.Counter()
    logged = collections.Counter()
    trips = collections.Counter()
    pat = collections.Counter()
    for name, lab in sorted(paired.items()):
        pm = meshes.get(lab["fid"])
        if pm is None:
            continue
        _r, sends, echoes, _f = read_capture(lab["path"])
        if echoes:
            logged[name] = echoes
        for s in sends:
            if s["plane"] != s["plane_b"]:
                tot["the two plane words differ"] += 1
            if not (math.isfinite(s["x"]) and math.isfinite(s["y"])):
                tot["non-finite point (tripwire skips)"] += 1
                continue
            tot["0x0029 sends with a finite point"] += 1
            offered = sorted({t.plane for t in pm.containing(s["x"], s["y"])})
            if not offered:
                tot["point off-mesh (tripwire silent by design)"] += 1
                continue
            tot["point on-mesh (DENOMINATOR)"] += 1
            if s["plane"] in offered:
                tot["emitted plane is offered"] += 1
            else:
                tot["emitted plane NOT offered (TRIP)"] += 1
                trips[name] += 1
                pat[(s["plane"], tuple(offered))] += 1
    return tot, logged, trips, pat


# ---------------------------------------------------------------- output ----

def _bar(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vault", default=default_vault(),
                    help="the vault (default: resolved by toolkit/vaultpath.py, "
                         "which finds the real one from inside a worktree; "
                         "RURIK_VAULT overrides)")
    ap.add_argument("--archive",
                    help="Gw.dat to decode meshes from. The default binds every "
                         "mesh the corpus needs except 0x5F0B2 (138 reports); "
                         "vault/run/2026-07-29_221c13772c7a-probe/Gw.dat binds "
                         "that one. Numbers for 0x287D3 and 0x5F0B2 are "
                         "archive-scoped -- name the archive when quoting them.")
    ap.add_argument("--max-lag", type=float, default=600.0,
                    help="seconds a capture may trail its harness dir (default 600)")
    ap.add_argument("--echo", action="store_true",
                    help="score the plane_echo tripwire and give it a denominator")
    ap.add_argument("--identify", action="store_true",
                    help="score pathdiff's geometric identifier against the labels")
    ap.add_argument("--armed", action="store_true",
                    help="split every headline by whether the repair was "
                         "actually RUNNING. The census reads over 134 captures "
                         "as one population; it is two, and the live one is 3 "
                         "sessions. Banner-confirmed, not date-inferred.")
    ap.add_argument("--focus", metavar="CAPTURE",
                    help="score ONE capture against the corpus: its rank, its "
                         "rate against the corpus rate, its direction split, "
                         "and -- the part that decides whether its signature "
                         "is geometry or session -- how much EXPOSURE other "
                         "captures had to the same offered planes")
    ap.add_argument("--json", help="write the full row set here")
    a = ap.parse_args(argv)

    paired, unlabelled, cross = label_captures(a.vault, a.max_lag)
    meshes = Meshes(a.archive)

    _bar("MESH PIN -- in band, from the server's own load message")
    print(f"  archive: {meshes.archive_path()}")
    scored = sum(v["n"] for v in paired.values())
    print(f"  captures carrying reports AND a file id : {len(paired)}")
    print(f"  captures carrying reports but NO file id: {len(unlabelled)}")
    print(f"  position_reports attributed to a mesh   : {scored}")
    print("\n  cross-check against the harness gamesrv.log (a second witness):")
    for k, v in cross.most_common():
        print(f"    {k:>42s} : {v}")
    if cross["harness DISAGREES"]:
        print("    ^ a DISAGREEMENT between two witnesses is a finding. The "
              "in-band id is the\n      one the server actually sent; the "
              "harness line can be a mispaired run.")
    print("\n  what each pinned mesh actually decoded to:")
    seen = collections.Counter()
    for v in paired.values():
        seen[v["fid"]] += v["n"]
    for fid, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        pm = meshes.get(fid)
        if pm is None:
            note = "UNBOUND in this archive -- these reports cannot be scored"
        else:
            note = f"{len(pm.planes)} planes, {len(pm.trapezoids)} trapezoids"
            if meshes.is_stub(fid):
                note += "  <-- STUB, excluded from the headline"
        print(f"    0x{fid:<10X} reports={n:<6d} {note}")

    if a.armed:
        return _armed(paired, meshes, a.vault)
    if a.focus:
        return _focus(paired, meshes, a.focus)
    if a.identify:
        return _identify(paired, meshes)
    if a.echo:
        return _echo(paired, meshes)

    tot, bymap, percap, offered_hist, direction, rows = census(paired, meshes)

    _bar("THE PLANE CENSUS")
    n = tot["reports"]
    if not n:
        print("  NOTHING TO SCORE: no captures carried position_reports with a "
              "plane and a pinned mesh. This is not a clean result.")
        return 1
    print(f"  position_reports scored : {n}")
    print(f"    off-mesh, mesh offers nothing : {tot['off-mesh']:6d}  "
          f"({100.0 * tot['off-mesh'] / n:.1f}%)")
    on = tot["on-mesh"]
    print(f"    on-mesh                       : {on:6d}  "
          f"({100.0 * on / n:.1f}%)")
    if on:
        print(f"      AGREE    : {tot['AGREE']:6d}  "
              f"({100.0 * tot['AGREE'] / on:.2f}% of on-mesh)")
        print(f"      DISAGREE : {tot['DISAGREE']:6d}  "
              f"({100.0 * tot['DISAGREE'] / on:.2f}% of on-mesh)")

    print("\n  by the declared plane -- HANDOFF section D item 2:")
    for k in ("AGREE, declared 0", "DISAGREE, declared 0",
              "AGREE, declared non-zero", "DISAGREE, declared non-zero"):
        print(f"    {k:>28s} : {tot[k]}")
    d0 = tot["AGREE, declared 0"] + tot["DISAGREE, declared 0"]
    dn = tot["AGREE, declared non-zero"] + tot["DISAGREE, declared non-zero"]
    if d0 and dn:
        r0 = 100.0 * tot["DISAGREE, declared 0"] / d0
        rn = 100.0 * tot["DISAGREE, declared non-zero"] / dn
        print(f"    a declared 0 disagrees {r0:.2f}% of the time; a declared "
              f"non-zero, {rn:.2f}%")

    print("\n  what the repair would do with each disagreement -- item 1:")
    print(f"    unambiguous, plane_at names a fix : "
          f"{tot['DISAGREE unambiguous -> trigger proceeds']}")
    print(f"      ...and actually REACHING the trigger : "
          f"{tot['DISAGREE unambiguous AND reaching the trigger']}")
    print(f"    on a stack, plane_at says None -> DISARMS : "
          f"{tot['DISAGREE on a STACK -> repair DISARMS']}")
    print("    ^ the second row is the honest one: the track is called from the"
          " 0x003D arm only\n      and drops refused reports, so stop-reports "
          "and rejects are not evidence about\n      the repair. And the verb "
          "is not 'arms' -- passing the ambiguity door returns\n      "
          "\"arming\", which RESETS the hold clock rather than advancing it.")
    if tot["DISAGREE"] and not tot["DISAGREE on a STACK -> repair DISARMS"]:
        print("    THE DISARM CLAUSE NEVER ENGAGED. That is not a reassuring "
              "zero: at this call site\n    plane_at has already been told the "
              "declared plane is not offered, so its `prefer`\n    branch is "
              "dead and it reduces to 'one candidate or None'. The clause can "
              "only\n    fire on STACKED ground, and stacked ground is a "
              "fraction of a percent of the map.")

    print("\n  |offered| over every scored point (stacking is what the "
          "disarm needs):")
    for k, v in sorted(offered_hist.items()):
        print(f"    {k} plane(s) : {v}")

    print("\n  direction of the disagreement -- the two classes "
          "test_noclipscore.py names:")
    for k, v in direction.most_common():
        print(f"    {k:>44s} : {v}")

    print("\n  by map:")
    print(f"    {'map/navmesh':>16s} {'reports':>8s} {'off-mesh':>9s} "
          f"{'AGREE':>7s} {'DISAGREE':>9s}")
    for m, c in sorted(bymap.items(), key=lambda kv: -kv[1]["reports"]):
        print(f"    {m:>16s} {c['reports']:8d} {c['off-mesh']:9d} "
              f"{c['AGREE']:7d} {c['DISAGREE']:9d}")

    print("\n  IS THIS A RATE OR AN EPISODE? -- the denominator is part of the "
          "measurement:")
    withany = len(percap)
    pts, bycap_pts = set(), collections.Counter()
    for r in rows:
        k = (r["cap"], round(r["x"], 3), round(r["y"], 3))
        if k not in pts:
            pts.add(k)
            bycap_pts[r["cap"]] += 1
    print(f"    disagreeing REPORTS : {len(rows)}")
    print(f"    distinct POINTS     : {len(pts)}")
    print("    ^ different quantities, and the second is the honest one for "
          "'how often'.\n      A frozen client re-reports one coordinate for "
          "as long as it is stuck, so a\n      single stuck episode inflates "
          "the row count without adding evidence.")
    print(f"    captures with at least one disagreement : {withany} of "
          f"{len(paired)}")
    print(f"    captures with exactly zero              : "
          f"{len(paired) - withany}")
    print(f"      {'capture':44s} {'rows':>5s} {'points':>7s}")
    for cap, c in percap.most_common(8):
        print(f"      {cap:44s} {c:5d} {bycap_pts[cap]:7d}")

    # ---- replay -------------------------------------------------------
    _bar("REPLAY of plane_repair_track over the same corpus")
    print(f"  HOLD={HOLD}s GAP={GAP}s MIN_INTERVAL={MIN_INTERVAL}s")
    allwhy = collections.Counter()
    fires, streaks = [], []
    for name, lab in sorted(paired.items()):
        pm = meshes.get(lab["fid"])
        if pm is None:
            continue
        reports, _s, _e, _f = read_capture(lab["path"])
        if not reports:
            continue
        reports.sort(key=lambda r: r["t"])
        f, best, why = replay(reports, pm)
        allwhy.update(why)
        if best > 0:
            streaks.append((best, name))
        for x in f:
            x["cap"] = name
            x["map"] = meshes.key(lab["fid"])
            fires.append(x)
    print("\n  clause outcomes:")
    for k, v in allwhy.most_common():
        print(f"    {k:>28s} : {v}")
    print(f"\n  WOULD-FIRE COUNT : {len(fires)}")
    print("  (the LIVE fire count is a different quantity -- grep the corpus "
          "for kind\n   'plane_repair'. The repair shipped 2026-08-29 at "
          "dcf9484; captures older than\n   that ran with it disarmed, so a "
          "live zero does not mean the trigger stayed quiet.)")
    streaks.sort(reverse=True)
    if streaks:
        print(f"\n  longest streak accumulated (needs {HOLD}s to fire):")
        for s, nm in streaks[:8]:
            print(f"    {s:6.2f}s  {nm}")
    for x in fires:
        print(f"    FIRE  {x['cap']}  t={x['t']:.2f}  held={x['held']}s  "
              f"declared {x['plane']} at ({x['point'][0]:.1f},"
              f"{x['point'][1]:.1f})  mesh offers {x['offered']}  "
              f"-> would restamp to {x['fix']}")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"totals": dict(tot), "direction": dict(direction),
                       "by_map": {k: dict(v) for k, v in bymap.items()},
                       "per_capture": dict(percap), "rows": rows,
                       "fires": fires,
                       "streaks": [{"s": s, "cap": c} for s, c in streaks]},
                      fh, indent=1)
        print(f"\nwrote {a.json}")
    return 0


def _echo(paired, meshes):
    tot, logged, trips, pat = echo_census(paired, meshes)
    _bar("CONTROL FIRST -- recomputation against the live tripwire")
    if not logged:
        print("  the live tripwire logged NOTHING in this corpus, so there is "
              "no control to run\n  and the numbers below are UNVALIDATED.")
        ok = False
    else:
        ok = True
        for cap in sorted(logged):
            good = trips[cap] == logged[cap]
            ok &= good
            print(f"    {cap:44s} live={logged[cap]:<4d} "
                  f"recomputed={trips[cap]:<4d} {'MATCH' if good else 'DIFFER'}")
        print(f"\n  CONTROL {'PASSES' if ok else 'FAILS'} -- the rate below is "
              f"{'quotable' if ok else 'NOT quotable'}")
    _bar("plane_echo, WITH A DENOMINATOR")
    for k in ("0x0029 sends with a finite point", "point on-mesh (DENOMINATOR)",
              "point off-mesh (tripwire silent by design)",
              "emitted plane is offered", "emitted plane NOT offered (TRIP)",
              "the two plane words differ", "non-finite point (tripwire skips)"):
        print(f"  {k:>46s} : {tot[k]}")
    den = tot["point on-mesh (DENOMINATOR)"]
    if den and ok:
        print(f"\n  TRIPWIRE RATE = {tot['emitted plane NOT offered (TRIP)']}"
              f" / {den} = "
              f"{100.0 * tot['emitted plane NOT offered (TRIP)'] / den:.2f}%")
    elif den:
        print(f"\n  {tot['emitted plane NOT offered (TRIP)']} trips over {den} "
              f"on-mesh sends -- a COUNT, printed without a rate because the "
              f"control did not pass.")
    print(f"  the live tripwire logged {sum(logged.values())} rows, across "
          f"{len(logged)} capture(s).")
    print("\n  emitted vs offered, top 10:")
    for (pd, off), n in pat.most_common(10):
        print(f"    we emit plane {pd:<5d} mesh offers {str(list(off)):<12s} : {n}")
    return 0


ARMED_BANNER = "plane repair (default ON)"


def armed_runs(vault):
    """Harness dirs whose banner says the repair was ARMED.

    Read from the BANNER, never from the ship date: a run can pass
    --no-plane-repair, and a banner is an artifact where a date is an
    inference. This is HANDOFF section C's rule applied to the one flag whose
    default-ON status is the open question.
    """
    out = set()
    base = os.path.join(vault, "captures", "harness")
    if not os.path.isdir(base):
        return out
    for d in sorted(os.listdir(base)):
        if not _TS.fullmatch(d):
            continue
        log = os.path.join(base, d, "gamesrv.log")
        if not os.path.isfile(log):
            continue
        try:
            head = open(log, encoding="utf-8", errors="replace").read(65536)
        except OSError:
            continue
        if ARMED_BANNER in head:
            out.add(d)
    return out


def _armed(paired, meshes, vault):
    """Split the census by whether the trigger was running. See FINDINGS 1z-o.10."""
    dirs = armed_runs(vault)
    stamps = sorted(dt.datetime.strptime(d, "%Y%m%dT%H%M%S") for d in dirs)

    def is_armed(name):
        m = _TS.search(name)
        if not m:
            return False
        t = dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
        return any(s <= t and (t - s).total_seconds() <= 600 for s in stamps)

    agg = {True: collections.Counter(), False: collections.Counter()}
    caps = {True: [], False: []}
    for name, lab in sorted(paired.items()):
        pm = meshes.get(lab["fid"])
        if pm is None or meshes.is_stub(lab["fid"]):
            continue
        reports, sends, echoes, _f = read_capture(lab["path"])
        if not reports:
            continue
        a = is_armed(name)
        caps[a].append(name)
        c = agg[a]
        c["captures"] += 1
        c["echo-logged"] += echoes
        for r in reports:
            off = frozenset(t.plane for t in pm.containing(r["x"], r["y"]))
            c["reports"] += 1
            if not off:
                c["off-mesh"] += 1
                continue
            c["on-mesh"] += 1
            if r["plane"] not in off:
                c["disagree"] += 1
        for snd in sends:
            off = frozenset(t.plane for t in pm.containing(snd["x"], snd["y"]))
            if not off:
                continue
            c["sends-on-mesh"] += 1
            if snd["plane"] not in off:
                c["echo-trips"] += 1
    A, U = agg[True], agg[False]

    def pct(x, y):
        return f"{100.0 * x / y:.2f}%" if y else "n/a"

    _bar("THE CENSUS, SPLIT BY WHETHER THE REPAIR WAS ACTUALLY RUNNING")
    print(f"  banner-confirmed ARMED harness runs : {len(dirs)}")
    print(f"  of those, runs with a scoreable capture : {A['captures']}")
    if len(dirs) > A["captures"]:
        print(f"  -> {len(dirs) - A['captures']} armed run(s) produced NO "
              f"capture. 'armed N times' and 'N armed\n     sessions have "
              f"data' are different claims; do not swap them.")
    for n in caps[True]:
        print(f"     {n}")
    print()
    print(f"  {'quantity':30s} {'ARMED':>10s} {'replay-only':>12s} {'armed %':>9s}")
    for lab, k in (("captures", "captures"), ("position_reports", "reports"),
                   ("on-mesh", "on-mesh"), ("off-mesh", "off-mesh"),
                   ("DISAGREE", "disagree"),
                   ("on-mesh sends", "sends-on-mesh"),
                   ("echo trips (recomputed)", "echo-trips"),
                   ("plane_echo rows LOGGED", "echo-logged")):
        print(f"  {lab:30s} {A[k]:10d} {U[k]:12d} "
              f"{pct(A[k], A[k] + U[k]):>9s}")
    print()
    print(f"  disagreement / on-mesh report : ARMED "
          f"{pct(A['disagree'], A['on-mesh'])}   replay-only "
          f"{pct(U['disagree'], U['on-mesh'])}")
    print(f"  echo trips / on-mesh send     : ARMED "
          f"{pct(A['echo-trips'], A['sends-on-mesh'])}   replay-only "
          f"{pct(U['echo-trips'], U['sends-on-mesh'])}")
    gd_a = A["sends-on-mesh"] / A["reports"] if A["reports"] else 0
    gd_u = U["sends-on-mesh"] / U["reports"] if U["reports"] else 0
    print(f"  grants per report             : ARMED {gd_a:.2f}   "
          f"replay-only {gd_u:.2f}"
          + (f"   ({gd_a / gd_u:.1f}x -- the echo channel is a function of "
             f"grants,\n     so the rate comparison above is between "
             f"populations that grant differently)" if gd_u else ""))
    print()
    print("  !! EVERY logged echo is armed and EVERY replayed fire is not.")
    print("     Nothing in the record both fired and was watched.")
    return 0


def _focus(paired, meshes, want):
    """Score ONE capture against the corpus it sits in.

    A single session's disagreement count means nothing on its own -- the
    corpus is bimodal, so "11 disagreements" is either unremarkable or the
    whole story depending on the denominator and on what else was exposed to
    the same geometry. The exposure block at the end is the one that decides
    it: if other captures stood on the same offered planes and never
    disagreed, the signature belongs to the SESSION, not the map.
    """
    match = [n for n in paired if want in n]
    if len(match) != 1:
        print(f"\n--focus {want!r} matched {len(match)} captures"
              f"{': ' + ', '.join(match[:6]) if match else ''}. Name one.")
        return 1
    target = match[0]

    per, offered_seen = {}, collections.defaultdict(collections.Counter)
    for name, lab in sorted(paired.items()):
        pm = meshes.get(lab["fid"])
        if pm is None or meshes.is_stub(lab["fid"]):
            continue
        reports, sends, echoes, _f = read_capture(lab["path"])
        if not reports:
            continue
        c = collections.Counter()
        pts = set()
        for r in reports:
            off = frozenset(t.plane for t in pm.containing(r["x"], r["y"]))
            c["reports"] += 1
            if not off:
                c["off-mesh"] += 1
                continue
            c["on-mesh"] += 1
            offered_seen[off][name] += 1
            if r["plane"] in off:
                c["agree"] += 1
                continue
            c["disagree"] += 1
            pts.add((round(r["x"], 3), round(r["y"], 3)))
            offered_seen[off][name + "  (DISAGREED)"] += 1
            if r["plane"] != 0 and off == frozenset({0}):
                c["N->0"] += 1
            elif r["plane"] == 0 and 0 not in off:
                c["0->N"] += 1
            else:
                c["other-dir"] += 1
        c["echo-logged"] = echoes
        per[name] = (c, len(pts))

    tot = collections.Counter()
    for c, _p in per.values():
        tot.update(c)
    me, mypts = per[target]

    def rate(a, b):
        return f"{100.0 * a / b:.2f}%" if b else "n/a"

    def rank(key):
        order = sorted(((c[key], n) for n, (c, _p) in per.items()), reverse=True)
        return next((f"{i} of {len(order)}"
                     for i, (_v, n) in enumerate(order, 1) if n == target), "-")

    _bar(f"{target}  SCORED AGAINST THE CORPUS")
    print(f"  corpus: {len(per)} captures on non-stub meshes, "
          f"{tot['reports']} reports, {tot['disagree']} disagreements")
    print()
    print(f"  {'quantity':32s} {'this':>10s} {'corpus':>10s} {'rank':>11s}")
    for lab, k in (("position_reports", "reports"), ("off-mesh", "off-mesh"),
                   ("DISAGREE", "disagree"),
                   ("direction N->0", "N->0"), ("direction 0->N", "0->N"),
                   ("plane_echo rows logged", "echo-logged")):
        print(f"  {lab:32s} {me[k]:10d} {tot[k]:10d} {rank(k):>11s}")
    print(f"  {'distinct disagreeing points':32s} {mypts:10d}")
    print()
    print(f"  disagreement per on-mesh report : {rate(me['disagree'], me['on-mesh'])}"
          f"   (corpus {rate(tot['disagree'], tot['on-mesh'])})")

    if not me["disagree"]:
        print("\n  This capture has NO disagreements, so there is no "
              "signature to place. That is a real observation, not an "
              "empty one -- see the exposure block for whether it was ever "
              "in a position to disagree.")
    print()
    print("  EXPOSURE -- who else stood on the same offered planes?")
    print("  (this is what separates 'the map does this' from 'this session "
          "did this')")
    mine = {off for off, who in offered_seen.items() if who.get(target)}
    for off in sorted(mine, key=lambda o: -offered_seen[o].get(target, 0)):
        who = offered_seen[off]
        others = {n: v for n, v in who.items()
                  if not n.startswith(target) and not n.endswith("(DISAGREED)")}
        dis = {n[:-13]: v for n, v in who.items() if n.endswith("(DISAGREED)")}
        print(f"    offered {sorted(off)}: this capture "
              f"{who.get(target, 0)} report(s), "
              f"{dis.get(target, 0)} disagreeing")
        if not others:
            print("        NO other capture ever stood here -- 'only this "
                  "one disagreed' would be vacuous for this plane set.")
            continue
        tot_o = sum(others.values())
        dis_o = sum(v for n, v in dis.items() if n != target)
        print(f"        {len(others)} other capture(s), {tot_o} report(s), "
              f"{dis_o} disagreeing")
        for n, v in sorted(others.items(), key=lambda kv: -kv[1])[:4]:
            print(f"          {n[-34:]:36s} {v:5d} reports, "
                  f"{dis.get(n, 0)} disagreeing")
    return 0



def _identify(paired, meshes):
    """Score pathdiff's geometric identifier against the harness ground truth."""
    sys.path.insert(0, os.path.join(_HERE, "movehook"))
    acc = collections.Counter()
    detail = []
    for name, lab in sorted(paired.items()):
        if not lab["fid"]:
            continue
        reports, _s, _e, _f = read_capture(lab["path"])
        if not reports:
            continue
        best = None
        for fid in sorted({v["fid"] for v in paired.values() if v["fid"]}):
            pm = meshes.get(fid)
            if pm is None:
                continue
            on = sum(1 for r in reports if pm.walkable(r["x"], r["y"]))
            on /= len(reports)
            land = agree = nz_land = nz_agree = 0
            for r in reports:
                cont = pm.containing(r["x"], r["y"])
                if not cont:
                    continue
                offer = {t.plane for t in cont}
                land += 1
                agree += r["plane"] in offer
                if r["plane"]:
                    nz_land += 1
                    nz_agree += r["plane"] in offer
            allp = (agree / land) if land else 0.0
            plane = (nz_agree / nz_land) if nz_land else allp
            row = (on * plane, fid, nz_land)
            if best is None or row[0] > best[0][0]:
                best = (row, best[0] if best else (0.0, 0, 0))
            elif row[0] > best[1][0]:
                best = (best[0], row)
        if not best:
            continue
        (score, fid, nz), runner = best
        refused = score < 0.6 or score - runner[0] < 0.2
        right = fid == lab["fid"]
        key = ("refused" if refused else "accepted",
               "right" if right else "WRONG",
               "no plane signal" if nz == 0 else "has plane signal")
        acc[key] += 1
        if not refused and not right:
            detail.append((name, lab["fid"], fid, score, nz))
    _bar("THE GEOMETRIC IDENTIFIER, SCORED AGAINST THE HARNESS LABELS")
    print("  pathdiff.map_scores' product, judged by pathdiff.identify's bar")
    for k, v in sorted(acc.items()):
        print(f"    {k[0]:>8s}  {k[1]:>5s}  {k[2]:>16s} : {v}")
    accepted = sum(v for k, v in acc.items() if k[0] == "accepted")
    wrong = sum(v for k, v in acc.items()
                if k[0] == "accepted" and k[1] == "WRONG")
    if accepted:
        print(f"\n  of {accepted} ACCEPTED identifications, {wrong} were wrong "
              f"({100.0 * wrong / accepted:.1f}%)")
    nosig = sum(v for k, v in acc.items()
                if k[0] == "accepted" and k[2] == "no plane signal")
    nosig_wrong = sum(v for k, v in acc.items()
                      if k[0] == "accepted" and k[2] == "no plane signal"
                      and k[1] == "WRONG")
    print(f"  accepted WITHOUT plane signal: {nosig}, of which wrong: "
          f"{nosig_wrong}")
    print("  -- the all-plane fallback is the failure. Its own docstring "
          "expects the refusal\n     bar to catch it; at n = 3-5 points the "
          "margin rule lets it through.")
    for name, truth, guess, score, nz in detail:
        print(f"    {name:44s} truth=0x{truth:X} guess=0x{guess:X} "
              f"score={score:.3f} nz={nz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
