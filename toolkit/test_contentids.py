#!/usr/bin/env python3
"""Check the content-id pre-flight: does it fire, and does it fire ALONE?

    python toolkit/test_contentids.py

WHAT EARNS THIS FILE. A pre-flight that refuses nothing is decoration, and one
that refuses everything gets deleted the first time it blocks a run. So the
sections that matter are the two directions:

  * Section 2 is the POSITIVE CONTROL, and it is not synthetic. `vault/run-live/`
    is a real archive that a real client really played from, and it genuinely
    does not bind `0x8001B97D` -- because that client completed the pending
    replacement and DnArchive re-linked the plain id to a different row. Handed
    that copy as the client archive, the check must go FATAL on exactly the two
    Pre-Searing rows and stay OK on the other eight. "Exactly" is the check: a
    guard that reddens on all ten is telling you nothing.
  * Section 1 requires the real loopback pair to pass CLEAN. If it did not, the
    guard would be blocking the very configuration it was written to protect.

Section 3 is the identity rule, and it is the half a "does it resolve" check
would miss. Row indices do NOT survive a patch (`archive.py` says so), so
identity comes from the MFT entry's own size and crc over the stored bytes. The
test mutates a copy of one entry's crc in memory and requires the verdict to
turn FATAL -- because two archives resolving an id to different FILES is worse
than a failure to launch: the run produces data and looks like it worked.

Section 4 asserts the LOOPBACK GATE on the syntax tree. A live run answers to
ArenaNet's server and must never be refused on our content rows, and "the call
sits inside the RUN_ROOT branch" is invisible to a grep -- the string
`contentids.preflight(dat)` is present either way.

No client, no socket, no launch. Sections 0-1 need the vault; section 2 needs
`vault/run-live/` and skips loudly without it.
"""

import ast
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "mapdata"))

import checks                                                 # noqa: E402
import contentids                                             # noqa: E402
import vaultpath                                              # noqa: E402

# MEASURED 2026-08-14: a healthy run against THIS vault executes 23 (it was 15
# before the raw-table fix added sections 1b and 2b). The floor is deliberately
# NOT 23, per checks.py's own rule -- "pin the floor to its mandatory core and
# let the optional sections declare skips."
#
# Sections 1b, 2 and 2b all require the vault to hold an archive that is
# MID-REPLACEMENT on a content id. That is true today and it is a condition we
# actively want to go away: once every copy has caught up they will skip, and a
# floor of 23 would then turn a HEALED vault into a red suite. The mandatory
# core once a vault exists is section 0 (3) + section 1 (4) + section 3 (2) +
# section 4 (3) = 12, and the skips are printed either way.
#
# 2026-08-15: +7 for section 5, which is SYNTHETIC -- it fakes `check`'s return
# and needs no vault at all, so unlike 1b/2/2b it can never skip and belongs in
# the mandatory core rather than above it. 12 + 7 = 19.
FLOOR = 19

LEDGER = checks.Ledger("content file ids vs the archives a run uses",
                       floor=FLOOR)
check = checks.adopt(LEDGER)

# The two content rows that share the one Pre-Searing map file. Named here as
# literals so the test states its own expectation instead of computing it from
# the module under test -- `test_agentlife.py` earned that rule the hard way.
#
# THEY USED TO BE "the two rows that carry a bit-31 id", and section 0 asserted
# exactly that. As of 2026-08-14 no content row carries one, and that is the fix
# rather than a regression: bit 31 is FcArchive announcing that a row's
# REPLACEMENT IS PENDING, so it is a transient property of one archive copy and
# never the map's name. Build 38833 installed that replacement, after which the
# renamed form binds in no archive at all. Section 0 now asserts the invariant
# that actually holds, which is also the stronger one -- "no content row names
# archive state" cannot be satisfied by naming the wrong archive's state.
PRESEARING_ROWS = (146, 148)
PRESEARING_FILE_ID = 0x1B97D


def _run_archives():
    """Every `vault/run/<stamp>/Gw.dat`, alphabetically. [] if there is no vault."""
    try:
        root = os.path.join(vaultpath.vault_root(), "run")
    except (SystemExit, OSError):
        return []
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        cand = os.path.join(root, name, "Gw.dat")
        if os.path.isfile(cand):
            out.append(cand)
    return out


def main():
    t0 = time.perf_counter()

    # -- 0. the content rows -------------------------------------------------
    print("0. the content rows this checks")
    ids = contentids.content_file_ids()
    check(len(ids) >= 9, "content/maps.toml carries file ids", str(len(ids)))
    bit31 = sorted(m for m, f in ids.items() if f & 0x80000000)
    check(not bit31,
          "NO content row names a bit-31 id -- archive state is not a map's name",
          f"{bit31} carry one. Bit 31 means that copy has the row renamed away "
          f"pending a replacement, so it stops binding the moment the "
          f"replacement lands (build 38833 did exactly that). Record the plain "
          f"logical id; contentids checks the archives agree.")
    presearing = sorted(m for m, f in ids.items() if f == PRESEARING_FILE_ID)
    check(tuple(presearing) == PRESEARING_ROWS,
          f"and the two Pre-Searing rows share 0x{PRESEARING_FILE_ID:X}",
          f"{presearing} -- if this moves, the exposure moved with it")

    client = contentids.default_client_dat()
    if client is None:
        LEDGER.skip("everything from section 1 on",
                    "no vault/run/<stamp>/Gw.dat to check against")
        return LEDGER.verdict()

    # -- 1. a COHERENT pair must pass CLEAN ----------------------------------
    #
    # The server archive is the client's OWN, which makes the pair the same
    # generation by construction. That is not a convenience: it is the
    # configuration the 2026-08-14 run that first drew the compass actually used
    # (`RURIK_DAT` pointed at the client's archive), and it is the only pairing
    # in this vault that is coherent today. Section 2b asserts that the DEFAULT
    # server pairing is not, which is a fact about the vault rather than a bug.
    print("\n1. a same-generation pair -- the guard must be SILENT")
    findings, skips = contentids.check(client, client)
    for why in skips:
        LEDGER.skip("an archive", why)
    check(bool(findings), "the check produced findings at all",
          f"{len(findings)} row(s) -- zero would mean it measured nothing")
    fatal = [f for f in findings if f.level == "fatal"]
    check(not fatal, "no FATAL when both sides are the same generation",
          "; ".join(repr(f) for f in fatal) if fatal else "clean")
    check(all(f.level == "ok" for f in findings),
          "every content row agrees across both archives",
          f"{sum(1 for f in findings if f.level == 'ok')} of {len(findings)}")
    # `preflight` must not raise on the good pair -- the guard has to be silent
    # when nothing is wrong, or it will be removed.
    try:
        contentids.preflight(client, client, say=lambda _m: None)
        raised = False
    except SystemExit:
        raised = True
    check(not raised, "preflight() does NOT refuse the good pair")

    # -- 1b. the CLIENT's half must be the RAW table -------------------------
    #
    # THE ONE-LINE INVARIANT THAT WOULD HAVE CAUGHT ALL THREE FAILURES. Our
    # reader registers a bit-31 id under both spellings; the client compares 32
    # bits exactly. Any archive mid-replacement therefore answers DIFFERENTLY to
    # the two tables, and a launch-time question must use the raw one. Asserted
    # on a real archive rather than a fixture, and skipped loudly if the vault
    # holds no mid-replacement copy -- because then the check is vacuous.
    print("\n1b. the raw table is what models the client")
    from archive import Archive, file_id_table                  # noqa: PLC0415
    armed_dat = armed_id = None
    for cand in _run_archives():
        try:
            ar = Archive(cand)
        except (OSError, ValueError):
            continue
        try:
            rawt = file_id_table(ar, raw=True)
            dual = file_id_table(ar)
            for mid, f in sorted(ids.items()):
                if f in dual and f not in rawt:
                    armed_dat, armed_id = cand, f
                    break
        finally:
            ar.close()
        if armed_dat:
            break
    if armed_dat is None:
        LEDGER.skip("the raw-vs-dual invariant",
                    "no archive under vault/run/ is mid-replacement on a content "
                    "id, so there is nothing for the two tables to disagree about")
    else:
        with Archive(armed_dat) as ar:
            rawt, dual = file_id_table(ar, raw=True), file_id_table(ar)
        check(armed_id in dual and armed_id not in rawt,
              f"0x{armed_id:X}: the dual table binds it, the RAW table does not",
              f"{os.path.basename(os.path.dirname(armed_dat))} -- this is exactly "
              f"the gap that let a doomed pair through")
        check((armed_id ^ 0x80000000) in rawt,
              "and the archive really does hold the other spelling",
              "otherwise the id is simply absent and proves nothing about masking")
        # And the check itself must now refuse that archive.
        af = [f for f in contentids.check(armed_dat, armed_dat)[0]
              if f.level == "fatal"]
        check(bool(af),
              "contentids goes FATAL on it -- REGRESSION GUARD",
              "green here means the client half is reading the masked table "
              "again, which is the 2026-08-14 defect returning")

    # -- 2. the positive control, on a real archive --------------------------
    #
    # THE CONTROL MOVED, AND THE OLD ONE IS NOW USELESS. It was `vault/run-live/`,
    # chosen because that copy genuinely did not bind `0x8001B97D`. As of
    # 2026-08-14 both run-live archives bind every content id PLAINLY -- their
    # pending replacements landed -- so they refuse nothing and would have made
    # this section vacuously green. The archives that are mid-replacement now are
    # the 38797-era loopback ones, and they are a better control anyway: this is
    # the exact pairing that printed "10 of 10 agree" and then died at Code=007.
    # Found by PROPERTY (does not bind a content id raw) rather than by name, so
    # it does not go stale the next time the vault moves.
    print("\n2. POSITIVE CONTROL: an archive that really does not bind the id")
    live = None
    for cand in _run_archives():
        try:
            with contentids.Archive(cand) as ar:
                rawt = contentids.file_id_table(ar, raw=True)
        except (OSError, ValueError):
            continue
        if any(f not in rawt for f in ids.values()):
            live = cand
            break
    if live is None:
        LEDGER.skip("the positive control",
                    "no archive under vault/run/ fails to bind a content id, so "
                    "this file cannot show the guard fires on anything. That is "
                    "a healthy vault, not a healthy test")
    else:
        lf, _ls = contentids.check(live, live)
        bad = sorted(f.map_id for f in lf if f.level == "fatal")
        check(tuple(bad) == PRESEARING_ROWS,
              "FATAL on exactly the two Pre-Searing rows",
              f"{bad} -- not all ten, which is what makes it a check")
        check(sum(1 for f in lf if f.level == "ok") == len(lf) - len(bad),
              "every other row still passes",
              f"{sum(1 for f in lf if f.level == 'ok')} of {len(lf)}")
        check(any("EXACT 32-bit" in f.text for f in lf if f.level == "fatal"),
              "and it says WHY -- the client's compare is exact",
              "a refusal that does not name the mechanism gets worked around")
        check(any(f"0x{PRESEARING_FILE_ID | 0x80000000:X}" in f.text
                  for f in lf if f.level == "fatal"),
              "and it names the OTHER spelling the archive does hold",
              "that is the difference between 'map missing' and 'copy behind'")
        try:
            contentids.preflight(live, live, say=lambda _m: None)
            refused = False
        except SystemExit as exc:
            refused = True
            msg = str(exc)
        check(refused, "preflight() REFUSES that pair")
        if refused:
            # Was `"0x8001B97D" in msg`, which pinned the RENAMED spelling and
            # went red on 2026-08-14 when content started naming the plain id --
            # while the refusal itself was still correct and still naming the
            # right rows. The id the message must carry is whatever content
            # actually holds, so it is read from there rather than typed.
            # `Finding.__repr__` formats the id as `0x{:X}`, so match that exactly.
            # Do NOT reach for `msg.upper()` here: it uppercases the `0x` prefix
            # too, and the needle then matches nothing. That cost a green check a
            # red run while the refusal it was checking was perfectly correct.
            check("archive STATE" in msg
                  and f"0x{PRESEARING_FILE_ID:X}" in msg,
                  "and the refusal names the id and why",
                  f"a refusal that does not say what to do gets worked around. "
                  f"Wanted 'archive STATE' and 0x{PRESEARING_FILE_ID:X} in: {msg[:200]}")

    # -- 2b. the vault's DEFAULT pairing, stated rather than assumed ---------
    #
    # Not a bug in this module and not a failure: `DEFAULT_DAT` is a pre-update
    # study archive while the client the harness would launch is post-update, so
    # the two bind the same content id to genuinely different FILES. The guard
    # catching that is the guard working -- and it is why the 2026-08-14 compass
    # run had to pass `RURIK_DAT`. Asserted so that the day it changes, somebody
    # is told rather than surprised mid-run.
    print("\n2b. the DEFAULT server pairing, for the record")
    dflt, _ds = contentids.check(client)
    dbad = sorted(f.map_id for f in dflt if f.level == "fatal")
    if dbad:
        check(tuple(dbad) == PRESEARING_ROWS,
              "default server pairing is FATAL on exactly the Pre-Searing rows",
              f"{dbad} -- point RURIK_DAT at a same-generation archive to run")
        check(any("DIFFERENT FILES" in f.text for f in dflt if f.level == "fatal"),
              "and it is a DIFFERENT-FILE disagreement, not an unbindable id",
              "the client binds it; the two copies just disagree about what it is")
    else:
        LEDGER.skip("the default-pairing assertion",
                    "DEFAULT_DAT and the launchable client are the same "
                    "generation now -- nothing to state")

    # -- 3. identity is size+crc, not 'it resolved' --------------------------
    print("\n3. two archives binding one id to DIFFERENT files is FATAL")
    tab, rows = contentids.index(client, raw=True)
    if tab is None:
        LEDGER.skip("the identity rule", "client archive unreadable")
    else:
        fid = contentids.content_file_ids()[PRESEARING_ROWS[0]]
        row = tab[fid]

        class Bent:
            """The client's entry with ONE byte of its crc disturbed."""
            def __init__(self, e):
                self.index, self.offset = e.index, e.offset
                self.size, self.flags = e.size, e.flags
                self.compression, self.counter = e.compression, e.counter
                self.crc = e.crc ^ 1

        import contentids as ci
        real_index = ci.index

        # `raw` must be forwarded: `check()` asks the client's half with
        # raw=True, and a stub that swallowed the kwarg would either TypeError
        # or silently hand back the masked table -- reintroducing the very bug
        # this file now guards, from inside the test.
        def fake_index(dat, raw=False):
            t, r = real_index(dat, raw=raw)
            # BEND THE CLIENT'S HALF ONLY, and `raw` is what identifies it.
            # The pair here is same-generation, so both sides open the SAME
            # path -- a stub keyed on `dat` alone bends both, they agree
            # perfectly, and the section goes green while measuring nothing.
            # It did exactly that on the first run of this rewrite.
            if t is None or dat != client or not raw:
                return t, r
            r = dict(r)
            r[row] = Bent(r[row])
            return t, r

        ci.index = fake_index
        try:
            # Same-generation pair, so the ONLY disagreement is the bent crc.
            mf = [f for f in ci.check(client, client)[0] if f.level == "fatal"]
        finally:
            ci.index = real_index
        check(sorted(f.map_id for f in mf) == list(PRESEARING_ROWS),
              "a one-bit crc difference is caught, on both rows sharing the id",
              f"{sorted(f.map_id for f in mf)}")
        check(any("DIFFERENT FILES" in f.text for f in mf),
              "and it is reported as a different FILE, not a missing id")

    # -- 4. the loopback gate, on the syntax tree ----------------------------
    print("\n4. the pre-flight is gated to loopback runs")
    src = open(os.path.join(HERE, "harness", "drive_client.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "assert_safe"),
              None)
    check(fn is not None, "drive_client.assert_safe exists")
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "preflight"]
    check(len(calls) == 1, "it calls contentids.preflight exactly once",
          str(len(calls)))
    # The call must sit inside an `if` whose test mentions RUN_ROOT. A grep for
    # the call cannot tell a gated call from an ungated one, and an ungated one
    # would refuse LIVE runs on content rows that do not apply to them.
    gated = False
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        if "RUN_ROOT" in names and any(c in ast.walk(node) for c in calls):
            gated = True
    check(gated,
          "and the call sits inside an `if` testing RUN_ROOT",
          "a live run answers to ArenaNet and must never be refused on our rows")

    # -- 5. scoping to the map actually served ------------------------------
    # SYNTHETIC ON PURPOSE, and therefore mandatory core: it needs no vault, so
    # it cannot skip, and the semantics it pins are the ones that decide whether
    # this guard still guards. Real findings are driven by whatever state the
    # vault happens to be in; these are chosen so each rule can be broken alone.
    print("\n5. the pre-flight narrows to the served map, and fails closed")
    fatal_148 = contentids.Finding("fatal", 148, 0x1B97D, "different files")
    ok_449 = contentids.Finding("ok", 449, 0x345CC, "same 1 B crc 0x0")
    real_check = contentids.check
    try:
        contentids.check = lambda *a, **k: ([fatal_148, ok_449], [])

        def run(served):
            """(refused, printed lines, returned findings)."""
            out = []
            try:
                got = contentids.preflight("c.dat", "s.dat", say=out.append,
                                           served=served)
                return False, out, got
            except SystemExit:
                return True, out, None

        refused, _, _ = run(None)
        check(refused,
              "served=None still refuses -- the historical behaviour is the "
              "default, so a caller that passes nothing loses no protection")

        refused, lines, got = run({449})
        check(not refused,
              "a run serving only 449 is NOT refused by map 148's row",
              "the false positive that blocked every loopback run on 2026-08-15")
        check(any("not served" in ln for ln in lines),
              "and the out-of-scope disagreement is still PRINTED",
              "demoting it must not make the archive state invisible")
        check(got and any(f.level == "fatal" for f in got),
              "and it is returned with level 'fatal' intact",
              "the caller sees the same facts; only what BLOCKS changed")

        refused, _, _ = run({148})
        check(refused,
              "a run that actually serves 148 is still refused",
              "the positive control -- narrowing that cleared this would be a "
              "guard that no longer guards")

        refused, _, _ = run(set())
        check(refused,
              "AN EMPTY SET REFUSES, exactly as None does -- FAIL CLOSED",
              "a caller whose --map parse came back empty must not thereby "
              "clear the whole table; that is how a guard gets silently disarmed")

        refused, lines, _ = run({999})
        check(not refused and any("no content/maps.toml row" in ln
                                  for ln in lines),
              "a served map with no content row is reported, not passed in "
              "silence",
              "'nothing disagreed' and 'nothing was checked' must not look alike")
    finally:
        contentids.check = real_check

    print(f"\nread the archives in {time.perf_counter() - t0:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
