"""The c2s send-site census, pinned against two builds.

    python toolkit/clientscan/test_sendsites.py

WHAT THIS PINS, and why each section can go red.

  * §0: each snapshot is identified by `buildid.of_image`, not by its directory
    name -- the route required the toolkit's own build identification, and
    "sorted-last" has picked the wrong build twice in this repo.
  * §1: the two framers are found by the MASKED PROLOGUE SIGNATURE, not by a
    hardcoded VA -- exactly two on each build, at the known VAs. The dword
    framer is the LOWER VA on both builds (the first cut claimed they swapped
    order between 38797 and 38888; they did not).
  * §2: 214 call sites, 40 + 174 across the two framers, reproduced on both
    builds; ALL 214 resolve to an opcode, all CONFIDENT, one of them a STATIC
    .rdata buffer -- the first cut left 7 "unresolved (register thunks)", which
    was false: six stored the opcode beyond its 64-byte window (the farthest
    235 bytes before the call) and one pushed a static buffer.
  * §3: THE CHANNEL IS PER ROW, from the connection argument, not per framer.
    The dword framer carries THREE game-channel sites (0x0009, 0x0092 and the
    static 0x0008) -- the first cut called that framer "the AUTH framer" and so
    reported GAME 0x0009 (2,687 c2s on the live wire) as having no send site.
    Four rows are `?` (the connection arrives as a parameter or a struct field,
    so the window cannot name it) and they are named, not guessed.
  * §4: THE FIVE ANCHORS, pinned per build. Each of 0x0040, 0x0016, 0x00B1,
    0x001E, 0x001F resolves to exactly ONE game-channel wrapper, at the VA
    measured here. 38888 moved every wrapper, so the anchor is the
    OPCODE-to-wrapper binding found by the census on each build, and the
    per-build VA is the regression pin. The route CORRECTION lives here too:
    the D1 survey put 0x0016's 38797 wrapper at 0x0091FD60; that VA is 16 bytes
    INSIDE the 0x0017 wrapper (entry 0x0091FD50), is nobody's wrapper start,
    and is the 38833/38849 0x0016 entry. The true 38797 wrapper is 0x0091FD00.
    Lengths ride here as well: 0x001F/0x001E push 8, 0x0016 pushes 12, and
    0x00A2 (whose length push comes AFTER its opcode store) pushes 4.
  * §5: THE KNOWN-BAD ARMS. A wrong framer VA yields zero rows from `census`,
    and the CLI REFUSES it with exit status 2 (the first cut exited 0 on
    "coverage: 0 sites", which on a drifted build reads as a clean "no c2s
    opcodes"). The AUTH homonym of 0x0016 is on the wire's other connection
    and does not reach the anchors.
  * §6: THE CALLERS COLUMN COUNTS EVERY REL32 BRANCH, each labelled `call`,
    `jmp` or `jcc` (2026-09-25). Until then it counted `E8` sites alone, and
    82 of 214 rows read "0 callers" on both builds, 75 of them wrongly:
    studies/cmsg/FINDINGS.md read the MAP_TRAVEL wrapper's zero as "reached
    through a pointer" while its one caller was the `jmp` thunk 0x008576E0.
    Pinned per build: the tally (132 rows reached by a call, 75 by jmp/jcc
    only, 7 by nothing); no jmp/jcc into either framer, so the send SITES
    stay `call`-only by measurement (the same check aimed at the MAP_TRAVEL
    wrapper finds its jmp, so that zero can fail); and seven rows by kind --
    0x0013, 0x00B0, 0x00B1 and 0x00B2 by `jmp`, 0x00A2 and 0x00AB by `jcc`,
    0x009F by `call` -- with 0x0009's pointer-reached wrapper still at zero.
    THE KNOWN-BAD ARM is the old `E8`-only rule, reproduced inline, not
    imported: it finds nothing for the six jmp/jcc rows and reads exactly 82
    rows as zero, and its positive control finds 0x009F's `call`. The fixed
    scan minus its jmp/jcc rows must equal the old rule on EVERY row -- the
    change added forms and moved nothing else. The printed scope names the
    forms searched and the ones not (rel8, stored pointers). Reverting the
    scan to `E8`-only reddens 16 checks.

Needs the vault (two client snapshots). Floor 128, ~8 s.
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
import checks                                                # noqa: E402
import vaultpath                                             # noqa: E402
import buildid                                               # noqa: E402
import sendsites                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

# 85 -> 128 on 2026-09-25 with §6 (19 per build, 5 build-independent), from
# the green run; reverting the scan to E8-only reddens 16 of them.
LEDGER = checks.Ledger("c2s send-site census", floor=128)

# The two builds this test pins, and everything MEASURED on them 2026-09-22.
BUILDS = {
    "2026-07-29_221c13772c7a": {
        "build": 38797,
        "framers": {0x007DCB10, 0x007DCF00},
        "bytes": 0x007DCF00,        # (conn, nbytes, buf), 174 sites
        "dwords": 0x007DCB10,       # (conn, buf, ndwords), 40 sites
        "getter": 0x00491DE0, "game_conn": 0x00C034D4, "auth_struct": 0x00C03524,
        "anchors": {0x0040: 0x009207B0, 0x0016: 0x0091FD00, 0x00B1: 0x0085C280,
                    0x001E: 0x0091FF00, 0x001F: 0x0091FF30},
        # game-channel sites on the DWORD framer (per-row attribution)
        "dword_game": {0x0009: 0x00491E50, 0x0092: 0x00852930, 0x0008: 0x00491D30},
        # the six the 64-byte window could not see, plus their wrappers
        "far": {0x002B: 0x00920230, 0x0045: 0x00920980, 0x004D: 0x00920A70,
                0x004C: 0x00920C80, 0x000A: 0x00491820, 0x000B: 0x00491820},
        "unknown_wrappers": {0x004923D0, 0x006047A0},
        "op17": 0x0091FD50, "opA2": 0x0085BEF0, "auth16": 0x00493560,
        "not_a_wrapper": 0x0091FD60,
        # §6: game opcode -> (wrapper, [(caller site, kind)]), MEASURED
        # 2026-09-25 and each one agreed by `codescan --xrefs <wrapper>`.
        "callers": {
            0x0013: (0x0091FC30, [(0x0080DAC3, "jmp")]),
            0x00A2: (0x0085BEF0, [(0x008585FD, "jcc")]),
            0x00AB: (0x0085C010, [(0x0085A8C4, "jcc")]),
            0x00B0: (0x0085C220, [(0x008576D0, "jmp")]),
            0x00B1: (0x0085C280, [(0x008576E0, "jmp")]),
            0x00B2: (0x0085C2E0, [(0x008576F0, "jmp")]),
            0x009F: (0x0085BE40, [(0x0085843A, "call")]),
            0x0009: (0x00491E50, []),   # a .data word holds it
        },
    },
    "2026-09-01_44fbd68767a8": {
        "build": 38888,
        "framers": {0x007DCF70, 0x007DD360},
        "bytes": 0x007DD360,
        "dwords": 0x007DCF70,
        "getter": 0x00491DE0, "game_conn": 0x00C06514, "auth_struct": 0x00C06564,
        "anchors": {0x0040: 0x00921130, 0x0016: 0x00920680, 0x00B1: 0x0085C7C0,
                    0x001E: 0x00920880, 0x001F: 0x009208B0},
        "dword_game": {0x0009: 0x00491E50, 0x0092: 0x00852E80, 0x0008: 0x00491D30},
        "far": {0x002B: 0x00920BB0, 0x0045: 0x00921300, 0x004D: 0x009213F0,
                0x004C: 0x00921600, 0x000A: 0x00491820, 0x000B: 0x00491820},
        "unknown_wrappers": {0x004923D0, 0x00604C00},
        "op17": 0x009206D0, "opA2": 0x0085C430, "auth16": 0x00493560,
        "not_a_wrapper": None,
        "callers": {
            0x0013: (0x009205B0, [(0x0080DF33, "jmp")]),
            0x00A2: (0x0085C430, [(0x00858B4D, "jcc")]),
            0x00AB: (0x0085C550, [(0x0085AE04, "jcc")]),
            0x00B0: (0x0085C760, [(0x00857C20, "jmp")]),
            0x00B1: (0x0085C7C0, [(0x00857C30, "jmp")]),
            0x00B2: (0x0085C820, [(0x00857C40, "jmp")]),
            0x009F: (0x0085C380, [(0x0085898A, "call")]),
            0x0009: (0x00491E50, []),
        },
    },
}
# §6, both builds: rows reached by at least one call / by jmp or jcc only / by
# no rel32 branch. 82 = 75 + 7 is what the E8-only column read as zero.
CALLER_TALLY = {"call": 132, "branch_only": 75, "none": 7}
OLD_ZEROS = 82


def _e8_only(data, base):
    """The KNOWN-BAD rule, the callers column as it was until 2026-09-25:
    {target: sorted [site]} over `E8 rel32` sites, and nothing else.
    Reproduced here rather than imported, so a later change to the module
    cannot move this arm."""
    out = {}
    p = data.find(b"\xe8")
    while p != -1:
        if p + 5 <= len(data):
            rel = struct.unpack_from("<i", data, p + 1)[0]
            out.setdefault((base + p + 5 + rel) & 0xFFFFFFFF, []).append(base + p)
        p = data.find(b"\xe8", p + 1)
    return out
LENGTHS = {0x001F: 8, 0x001E: 8, 0x0016: 12, 0x00A2: 4}   # game rows, bytes
FAR_MAX = 235                                             # bytes, both builds


def _exe(stamp):
    root = vaultpath.require_dir("client")
    return os.path.join(root, stamp, "Gw.exe")


try:
    EXES = {stamp: _exe(stamp) for stamp in BUILDS}
    MISSING = [s for s, p in EXES.items() if not os.path.exists(p)]
except Exception as exc:                                     # noqa: BLE001
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")
    sys.exit(LEDGER.verdict())

if MISSING:
    LEDGER.skip("every section",
                f"missing client snapshot(s): {', '.join(MISSING)}")
    sys.exit(LEDGER.verdict())


def _game(rows, op):
    return [r for r in rows if r["opcode"] == op and r["channel"] == "game"
            and r["confident"]]


for stamp, want in BUILDS.items():
    exe = EXES[stamp]
    pe = PE(exe)
    b = want["build"]

    # -- §0 the build, by the toolkit's own identification ------------------
    got_build = buildid.of_image(exe)[0]
    LEDGER.ok(got_build == b,
              f"[{b}] buildid.of_image names the snapshot {stamp} as {b}",
              f"got {got_build}")

    # -- §1 the framers, by signature --------------------------------------
    fr = sendsites.find_framers(pe)
    LEDGER.ok(len(fr) == 2,
              f"[{b}] the masked prologue signature finds exactly two framers",
              f"found {['0x%08X' % x for x in fr]}")
    LEDGER.ok(set(fr) == want["framers"],
              f"[{b}] and they are the known VAs",
              f"{sorted('0x%08X' % x for x in fr)} != "
              f"{sorted('0x%08X' % x for x in want['framers'])}")

    rows = sendsites.census(pe)
    cov = sendsites.coverage(rows)
    roles = sendsites.framer_roles(rows)
    LEDGER.ok(roles == {"bytes": want["bytes"], "dwords": want["dwords"]},
              f"[{b}] the (conn, nbytes, buf) framer is the busier one at "
              f"0x{want['bytes']:08X}; (conn, buf, ndwords) at 0x{want['dwords']:08X}",
              f"got {roles}")
    LEDGER.ok(want["dwords"] < want["bytes"],
              f"[{b}] the dword framer is the LOWER VA -- the two did not swap "
              f"order between builds", f"{roles}")

    # -- §2 the site count, and every site resolved ------------------------
    LEDGER.ok(cov["sites"] == 214,
              f"[{b}] 214 call sites across both framers", f"got {cov['sites']}")
    LEDGER.ok(sorted(cov["per_framer"].values()) == [40, 174],
              f"[{b}] 40 + 174 across the two framers",
              f"got {sorted(cov['per_framer'].values())}")
    LEDGER.ok(cov["unresolved"] == 0 and cov["resolved"] == 214,
              f"[{b}] every one of the 214 sites resolves to an opcode -- the "
              f"'7 register thunks' were a 64-byte window, not thunks",
              f"resolved {cov['resolved']}, unresolved {cov['unresolved']}")
    LEDGER.ok(cov["confident"] == 214,
              f"[{b}] and every row is CONFIDENT (store tied to the pushed slot, "
              f"or a static buffer)", f"got {cov['confident']}")
    LEDGER.ok(cov["max_store_distance"] == FAR_MAX,
              f"[{b}] the farthest opcode store sits {FAR_MAX} bytes before its "
              f"call -- what the old 64-byte window could not reach",
              f"got {cov['max_store_distance']}")
    statics = [r for r in rows if r["static"]]
    LEDGER.ok(len(statics) == 1 and statics[0]["opcode"] == 0x0008
              and statics[0]["wrapper_va"] == 0x00491D30
              and statics[0]["channel"] == "game",
              f"[{b}] exactly one STATIC buffer site: 0x00491D30 sends opcode "
              f"0x0008 from .rdata on the game connection",
              f"got {[(hex(r['opcode'] or 0), hex(r['wrapper_va'] or 0)) for r in statics]}")
    for op, wrap in want["far"].items():
        got = sorted({r["wrapper_va"] for r in _game(rows, op)})
        LEDGER.ok(wrap in got,
                  f"[{b}] 0x{op:04X} is recovered from wrapper 0x{wrap:08X} "
                  f"(a store outside the old 64-byte window)",
                  f"got {['0x%08X' % x for x in got]}")

    # -- §3 the channel, per row from the connection argument --------------
    data, base = sendsites._text(pe)
    conns = sendsites.connection_globals(pe, data, base,
                                         [r["site_va"] for r in rows])
    LEDGER.ok(conns == {"getter": want["getter"], "game_conn": want["game_conn"],
                        "auth_struct": want["auth_struct"]},
              f"[{b}] the connection map is derived from the sites: getter "
              f"0x{want['getter']:08X} -> [0x{want['game_conn']:08X}], auth "
              f"[[0x{want['auth_struct']:08X}]+0x14]",
              f"got { {k: hex(v) for k, v in conns.items()} }")
    LEDGER.ok(cov["per_channel"] == {"game": 175, "auth": 35, "?": 4},
              f"[{b}] channels: 175 game, 35 auth, 4 unknown",
              f"got {cov['per_channel']}")
    dg = {(r["opcode"], r["wrapper_va"]) for r in rows
          if r["framer_va"] == want["dwords"] and r["channel"] == "game"}
    LEDGER.ok(dg == set(want["dword_game"].items()),
              f"[{b}] the DWORD framer carries three GAME-channel sites "
              f"(0x0009, 0x0092, static 0x0008) -- per-framer attribution "
              f"would call them auth and lose GAME 0x0009's only sender",
              f"got {sorted((hex(o), hex(w)) for o, w in dg)}")
    LEDGER.ok(not any(r["channel"] == "auth" for r in rows
                      if r["framer_va"] == want["bytes"]),
              f"[{b}] no auth-channel site calls the byte framer",
              f"{[hex(r['site_va']) for r in rows if r['framer_va'] == want['bytes'] and r['channel'] == 'auth']}")
    unk = {r["wrapper_va"] for r in rows if r["channel"] == "?"}
    LEDGER.ok(unk == want["unknown_wrappers"],
              f"[{b}] the 4 unknown-channel rows sit in exactly two functions "
              f"whose connection arrives as a parameter/struct field",
              f"got {sorted('0x%08X' % x for x in unk)}")

    # -- §4 the five anchors, pinned per build -----------------------------
    an = sendsites.anchors(rows)
    for op, va in want["anchors"].items():
        got = an.get(op) or []
        LEDGER.ok(got == [va],
                  f"[{b}] 0x{op:04X} -> one game-channel wrapper at 0x{va:08X}",
                  f"got {['0x%08X' % x for x in got]}")
        # The wrapper is a real function: it opens with a prologue.
        off = pe.rva_to_off(va - pe.image_base)
        head = pe.data[off:off + 3] if off is not None else b""
        LEDGER.ok(head == b"\x55\x8b\xec",
                  f"[{b}] 0x{op:04X}'s wrapper 0x{va:08X} is a real prologue",
                  f"head {head.hex()}")
    for op, ln in LENGTHS.items():
        got = {r["length"] for r in _game(rows, op)}
        LEDGER.ok(got == {ln},
                  f"[{b}] 0x{op:04X}'s game wrapper pushes length {ln}",
                  f"got {got}")
    wraps = {r["wrapper_va"] for r in rows}
    LEDGER.ok(any(r["opcode"] == 0x0017 and r["wrapper_va"] == want["op17"]
                  and r["channel"] == "game" for r in rows),
              f"[{b}] the 0x0017 wrapper starts at 0x{want['op17']:08X}",
              f"{[hex(r['wrapper_va']) for r in rows if r['opcode'] == 0x0017]}")
    if want["not_a_wrapper"] is not None:
        LEDGER.ok(want["not_a_wrapper"] not in wraps,
                  f"[{b}] 0x{want['not_a_wrapper']:08X} (the survey's 0x0016 "
                  f"address) is nobody's wrapper start -- it lies inside the "
                  f"0x0017 wrapper", "it is a wrapper start")
    LEDGER.ok(any(r["opcode"] == 0x00A2 and r["wrapper_va"] == want["opA2"]
                  for r in rows),
              f"[{b}] 0x00A2's wrapper 0x{want['opA2']:08X} is censused (its "
              f"length push follows the opcode store)", "missing")

    # -- §5 the AUTH homonym is scoped out --------------------------------
    auth_16 = [r for r in rows if r["opcode"] == 0x0016
               and r["channel"] == "auth" and r["confident"]]
    LEDGER.ok([r["wrapper_va"] for r in auth_16] == [want["auth16"]],
              f"[{b}] the AUTH channel also carries a 0x16 sender "
              f"(0x{want['auth16']:08X}) -- the homonym the anchor's channel "
              f"scope excludes", f"found {[hex(r['wrapper_va']) for r in auth_16]}")

    # -- §6 the callers column: every rel32 branch, by kind -----------------
    tally = {"call": cov["callers_call"],
             "branch_only": cov["callers_branch_only"],
             "none": cov["callers_none"]}
    LEDGER.ok(tally == CALLER_TALLY,
              f"[{b}] callers: {CALLER_TALLY['call']} rows reached by a call, "
              f"{CALLER_TALLY['branch_only']} by jmp/jcc only, "
              f"{CALLER_TALLY['none']} by no rel32 branch", f"got {tally}")
    tails = sendsites.framer_tail_refs(pe, fr)
    LEDGER.ok(tails == [],
              f"[{b}] no jmp or jcc lands on either framer -- the send SITES "
              f"are `call`s by measurement, not by assumption",
              f"got {[(hex(s), k) for s, k in tails]}")
    for op, (wrap, want_callers) in want["callers"].items():
        got = [r["callers"] for r in _game(rows, op) if r["wrapper_va"] == wrap]
        LEDGER.ok(got == [want_callers],
                  f"[{b}] 0x{op:04X}'s wrapper 0x{wrap:08X} is reached by "
                  + (", ".join(f"{k} 0x{s:08X}" for s, k in want_callers)
                     or "no rel32 branch (a stored pointer)"),
                  f"got {[[(hex(s), k) for s, k in c] for c in got]}")

    # The KNOWN-BAD arm: the E8-only column, over the same rows.
    old = _e8_only(data, base)
    for op, (wrap, want_callers) in want["callers"].items():
        if want_callers and all(k != "call" for _s, k in want_callers):
            LEDGER.ok(old.get(wrap, []) == [],
                      f"[{b}] KNOWN-BAD: the E8-only rule finds nothing for "
                      f"0x{op:04X}'s wrapper 0x{wrap:08X} -- the zero the "
                      f"table read", f"got {[hex(s) for s in old.get(wrap, [])]}")
    w9f, c9f = want["callers"][0x009F]
    LEDGER.ok(old.get(w9f, []) == [s for s, _k in c9f],
              f"[{b}] and it does find a call -- 0x009F's wrapper "
              f"0x{w9f:08X} <- 0x{c9f[0][0]:08X}, so its zeros are the defect "
              f"and not a broken reproduction",
              f"got {[hex(s) for s in old.get(w9f, [])]}")
    olds = [sorted(old.get(r["wrapper_va"], [])) if r["wrapper_va"] else []
            for r in rows]
    LEDGER.ok(sum(1 for o in olds if not o) == OLD_ZEROS,
              f"[{b}] the E8-only rule read {OLD_ZEROS} rows as 0 callers",
              f"got {sum(1 for o in olds if not o)}")
    moved = [hex(r["site_va"]) for r, o in zip(rows, olds)
             if [s for s, k in r["callers"] if k == "call"] != o]
    LEDGER.ok(not moved,
              f"[{b}] on every one of the {len(rows)} rows the fixed column "
              f"minus its jmp/jcc callers IS the old one -- forms were added, "
              f"nothing else moved", f"differs at sites {moved[:5]}")


# -- §6 the callers column's printed scope (build-independent) ---------------
# The framer-tail check's zero needs a positive control: pointed at a function
# that IS reached by a jmp, it must say so.
_pe = PE(EXES["2026-07-29_221c13772c7a"])
got = sendsites.framer_tail_refs(_pe, [0x0085C280])
LEDGER.ok(got == [(0x008576E0, "jmp")],
          "the framer-tail check finds a jmp where one exists: aimed at the "
          "MAP_TRAVEL wrapper 0x0085C280 it reports jmp 0x008576E0",
          f"got {[(hex(s), k) for s, k in got]}")
searched, blind = sendsites.caller_scope()
LEDGER.ok([n for n, _d in searched] == ["call rel32", "jmp rel32", "jcc rel32"],
          "the callers column states the three rel32 branch forms it searched",
          f"got {[n for n, _d in searched]}")
LEDGER.ok({"rel8 short branches", "stored pointers"}
          <= {n for n, _d in blind},
          "and names what it did not: rel8 short branches and stored pointers",
          f"got {[n for n, _d in blind]}")


# -- §5 the known-bad arms (build-independent) ------------------------------
exe97 = EXES["2026-07-29_221c13772c7a"]
pe97 = PE(exe97)
bad = sendsites.census(pe97, framers=[0xDEADBEEF])
LEDGER.ok(bad == [],
          "a wrong framer VA yields zero rows from census()")
bad_an = sendsites.anchors(bad)
LEDGER.ok(all(not v for v in bad_an.values()),
          "and its anchors are all empty rather than defaulting to a VA")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = sendsites.main(["--exe", exe97, "--framer", "0xDEADBEEF"])
LEDGER.ok(rc == 2 and "REFUSED" in buf.getvalue(),
          "the CLI REFUSES a zero-row census with exit status 2 -- never a "
          "clean 'coverage: 0 sites' at exit 0",
          f"rc {rc}: {buf.getvalue()[-200:]}")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = sendsites.main(["--exe", exe97, "--framer", "0xDEADBEEF", "--anchors"])
LEDGER.ok(rc == 2,
          "and --anchors on a zero-row census is refused too, not five NOT FOUNDs "
          "at exit 0", f"rc {rc}")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = sendsites.main(["--exe", exe97, "--anchors"])
LEDGER.ok(rc == 0 and "0x001F -> 0x0091FF30" in buf.getvalue(),
          "the positive control: the real CLI run exits 0 and prints the kick "
          "anchor", f"rc {rc}: {buf.getvalue()[-300:]}")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = sendsites.main(["--exe", exe97, "--opcode", "0x00B1"])
out = buf.getvalue()
LEDGER.ok(rc == 0 and "callers 1 (jmp 0x008576E0)" in out,
          "§6: the CLI prints MAP_TRAVEL's caller as `jmp 0x008576E0`, where "
          "it printed `callers 0`", f"rc {rc}: {out[-400:]}")
LEDGER.ok("callers NOT searched: stored pointers" in out
          and "not 'unreachable'" in out,
          "§6: and its footer says what a 0 does not cover",
          f"{out[-400:]}")

# -- vacuity guard ---------------------------------------------------------
full = sendsites.census(pe97)
LEDGER.ok(len(full) > 200 and sendsites.coverage(full)["confident"] > 200,
          "the census is non-empty and confident -- a run that measured "
          "nothing is a failure, not a pass")

sys.exit(LEDGER.verdict())
