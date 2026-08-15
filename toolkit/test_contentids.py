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

# MEASURED 2026-08-13: a healthy run against the vault executes 15. Set from
# that run, not from counting `check(` calls in the source -- which is how the
# neighbouring test_maprows.py got a floor one too high and went red naming the
# shortfall on its first green run.
FLOOR = 15

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

    # -- 1. the real loopback pair must pass CLEAN ---------------------------
    print("\n1. the pair a loopback run actually uses")
    findings, skips = contentids.check(client)
    for label, why in [(s, s) for s in skips]:
        LEDGER.skip("an archive", why)
    check(bool(findings), "the check produced findings at all",
          f"{len(findings)} row(s) -- zero would mean it measured nothing")
    fatal = [f for f in findings if f.level == "fatal"]
    check(not fatal, "no FATAL against the real loopback pair",
          "; ".join(repr(f) for f in fatal) if fatal else "clean")
    check(all(f.level == "ok" for f in findings),
          "every content row agrees across both archives",
          f"{sum(1 for f in findings if f.level == 'ok')} of {len(findings)}")
    # `preflight` must not raise on the good pair -- the guard has to be silent
    # when nothing is wrong, or it will be removed.
    try:
        contentids.preflight(client, say=lambda _m: None)
        raised = False
    except SystemExit:
        raised = True
    check(not raised, "preflight() does NOT refuse the good pair")

    # -- 2. the positive control, on a real archive --------------------------
    print("\n2. POSITIVE CONTROL: an archive that really does not bind the id")
    live = None
    root = os.path.join(vaultpath.vault_root(), "run-live")
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            cand = os.path.join(root, name, "Gw.dat")
            if os.path.isfile(cand):
                live = cand
                break
    if live is None:
        LEDGER.skip("the positive control",
                    "no vault/run-live/<stamp>/Gw.dat -- without it this file "
                    "cannot show the guard fires on anything")
    else:
        lf, _ls = contentids.check(live)
        bad = sorted(f.map_id for f in lf if f.level == "fatal")
        check(tuple(bad) == PRESEARING_ROWS,
              "FATAL on exactly the two Pre-Searing rows",
              f"{bad} -- not all ten, which is what makes it a check")
        check(sum(1 for f in lf if f.level == "ok") == len(lf) - len(bad),
              "every other row still passes",
              f"{sum(1 for f in lf if f.level == 'ok')} of {len(lf)}")
        try:
            contentids.preflight(live, say=lambda _m: None)
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

    # -- 3. identity is size+crc, not 'it resolved' --------------------------
    print("\n3. two archives binding one id to DIFFERENT files is FATAL")
    tab, rows = contentids.index(client)
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

        def fake_index(dat):
            t, r = real_index(dat)
            if t is None or dat != client:
                return t, r
            r = dict(r)
            r[row] = Bent(r[row])
            return t, r

        ci.index = fake_index
        try:
            mf = [f for f in ci.check(client)[0] if f.level == "fatal"]
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

    print(f"\nread the archives in {time.perf_counter() - t0:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
