#!/usr/bin/env python3
"""Check the authored-text writer -- mostly the ways it could destroy 4 GB.

    python toolkit/mapdata/test_textwrite.py

`textwrite.py` is the first COMMITTED thing in this repo that writes strings into
the archive. Every string this project has put on a retail screen was written by
an ad-hoc script, which is why `RESKIN.md` can quote the words but not the
arithmetic -- so this file is the arithmetic, and it is mostly refusals.

THE CLAIM THAT EARNS THE FILE is that `merge` keeps untouched records VERBATIM.
The alternative -- decode every record and re-encode it from text -- looks
identical on everything we have written (our records are all PLAIN: base 0, bits
0x10, which is `encode_record`'s default) and silently rewrites anything that is
not. Four of the twelve records already on screen are written down nowhere, so
losing them would be unrecoverable and invisible. Section 1 builds a file with
NON-DEFAULT base and bits, runs both versions, and requires them to differ --
without that record the check passes against the wrong implementation.

Sections 0-4 build their own files out of `struct` and need no vault, no archive
and no client. Section 5 reads the real archive and declares a skip without it.
"""

import ast
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
import checks                                                    # noqa: E402
import textrec                                                   # noqa: E402
import textwrite as tw                                           # noqa: E402
import vaultpath                                                 # noqa: E402

# MEASURED 2026-08-14 by running it both ways: 31 with no vault, 41 with one.
# (The draft of this line said 29/34 and both were guesses, in the same session
# that had already recorded three of those -- see test_skillnames.py's floor
# comment. Run it, read the banner, paste the number.)
LEDGER = checks.Ledger("authored text writer", floor=31)
check = checks.adopt(LEDGER)

N = textrec.RECORDS_PER_FILE


def guarded(fn):
    try:
        fn()
    except Exception as exc:                                     # noqa: BLE001
        check(False, "section %s completed" % fn.__name__,
              "%s: %s" % (type(exc).__name__, exc))


def synthetic(mixed=False):
    """A tiling 1,024-record file. `mixed` gives some records non-default coding.

    The mixed form is what separates a verbatim merge from a re-encoding one, so
    it is built here rather than borrowed from the archive: the property has to
    hold on a bare machine.
    """
    out = []
    for i in range(N):
        if mixed and i % 7 == 3:
            # A payload that is NOT UTF-16 text, with a base and a bit width the
            # encoder would never choose on its own.
            out.append(textrec.encode_record(payload=bytes([i % 251, 7, 9]),
                                             base=0x20 + (i % 5), bits=8))
        elif i < 12:
            out.append(textrec.encode_record("record %d" % i))
        else:
            out.append(textrec.encode_record())
    return b"".join(out) + struct.pack("<BB", 0, tw.FILE_INDEX)


# --------------------------------------------------------------------------


def section_identity():
    print("\n== 0. an empty merge is a byte-for-byte identity ==")
    for label, blob in (("plain", synthetic()), ("mixed", synthetic(True))):
        recs, tail, tiled = textrec.walk(blob)
        check(tiled and len(recs) == N,
              "the %s fixture is a tiling %d-record file" % (label, N),
              (len(recs), tiled, len(tail)))
        check(tw.merge(blob, {}) == blob,
              "merge(%s, {}) returns the input byte-for-byte" % label,
              len(blob))
    big = synthetic(True)
    out = tw.merge(big, {50: "Warding Starburst"})
    recs, _t, tiled = textrec.walk(out)
    check(tiled and len(recs) == N,
          "and a real merge still tiles at %d records" % N, (len(recs), tiled))
    check(recs[50][2] == "Warding Starburst".encode("utf-16-le"),
          "the written record carries the UTF-16 the caller asked for")


def section_verbatim():
    print("\n== 1. untouched records are VERBATIM, not re-encoded ==")
    blob = synthetic(True)
    recs, tail, _ = textrec.walk(blob)
    odd = [i for i, (bits, base, _p) in enumerate(recs)
           if (bits, base) != (textrec.MAX_BITS, 0)]
    check(len(odd) > 100,
          "the fixture really does carry records with non-default coding -- "
          "without them this section cannot fail", len(odd))
    out = tw.merge(blob, {12: "Keen Trident"})
    got, _t2, _ok = textrec.walk(out)
    same = sum(1 for i in range(N) if i != 12 and got[i] == recs[i])
    check(same == N - 1,
          "every record except the written one is byte-identical",
          "%d of %d" % (same, N - 1))

    # THE CONTROL. A merge that re-encodes from the payload but DROPS base and
    # bits is the natural wrong version -- it is an identity on everything this
    # project has ever written, because our records are all plain.
    def merge_naive(b, strings):
        rs, tl, _ = textrec.walk(b)
        parts = []
        for i, (_bits, _base, payload) in enumerate(rs):
            if i in strings:
                parts.append(textrec.encode_record(strings[i]))
            else:
                parts.append(textrec.encode_record(payload=payload))
        return b"".join(parts) + tl

    naive = merge_naive(blob, {12: "Keen Trident"})
    first = next((i for i in range(min(len(naive), len(out)))
                  if naive[i] != out[i]), None)
    check(naive != out,
          "and the version that drops base/bits DIFFERS -- the control that "
          "makes the check above mean something. Reported as the first differing "
          "OFFSET, because the two are the same LENGTH (base and bits live in the "
          "header, so dropping them corrupts in place rather than resizing) and a "
          "length comparison would read as agreement",
          "first differs at byte %s of %d" % (first, len(out)))
    plain_only = synthetic(False)
    check(merge_naive(plain_only, {12: "x"}) == tw.merge(plain_only, {12: "x"}),
          "...while on an all-PLAIN file the two AGREE, which is why this "
          "defect would never show up against anything we have written")


def section_refusals():
    print("\n== 2. what merge refuses ==")
    blob = synthetic()
    # Not tiling.
    try:
        tw.merge(blob[:-1], {12: "x"})
        check(False, "a file that does not tile is refused")
    except ValueError as exc:
        check("tile" in str(exc), "a file that does not tile is refused",
              str(exc)[:50])
    # Out of range.
    for bad in (-1, N, N + 5):
        try:
            tw.merge(blob, {bad: "x"})
            check(False, "record index %d is refused" % bad)
        except ValueError:
            check(True, "record index %d is refused" % bad)
    # The identity tier.
    for r in (0, 3, tw.FIRST_FREE_RECORD - 1):
        try:
            tw.merge(blob, {r: "x"})
            check(False, "record %d is refused as the identity tier" % r)
        except ValueError as exc:
            check("IDENTITY" in str(exc),
                  "record %d is refused as the identity tier" % r, str(exc)[:40])
    # ...and permitted when asked, or the guard just makes the tool unusable.
    ok = tw.merge(blob, {3: "Renamed"}, allow_identity=True)
    got, _t, _ = textrec.walk(ok)
    check(got[3][2] == "Renamed".encode("utf-16-le"),
          "--allow-identity permits it -- the positive control")
    check(tw.merge(blob, {tw.FIRST_FREE_RECORD: "x"}) != blob,
          "and the first FREE record needs no flag", tw.FIRST_FREE_RECORD)


def section_guards():
    print("\n== 3. the write guards ==")
    for bad, why in ((r"C:\gw\Gw.dat", "the owner's install"),
                     (r"C:\gw\sub\deep\Gw.dat", "below the owner's install"),
                     (os.path.join("x", "vault", "dat_study", "Gw.dat"),
                      "the reference copy")):
        try:
            tw.guard(bad)
            check(False, "refuses %s (%s)" % (bad, why))
        except tw.Refused:
            check(True, "refuses %s (%s)" % (bad, why))
    # POSITIVE CONTROLS. A guard that refuses everything protects nothing,
    # because the tool then never runs.
    for good in (os.path.join("x", "vault", "run", "reskin-roster", "Gw.dat"),
                 os.path.join("C:", "tmp", "Gw.dat")):
        try:
            tw.guard(good)
            check(True, "allows an ordinary run copy: %s" % good)
        except tw.Refused:
            check(False, "allows an ordinary run copy: %s" % good)
    # `C:\gwsomething` is NOT inside `C:\gw`.
    try:
        tw.guard(r"C:\gwtest\Gw.dat")
        check(True, "a sibling directory named gwtest is not refused")
    except tw.Refused:
        check(False, "a sibling directory named gwtest is not refused")


def section_arithmetic():
    print("\n== 4. the id arithmetic and the plan-before-write ordering ==")
    check(tw.string_id(0) == tw.FILE_INDEX * N,
          "record 0 of file %d is string id %d"
          % (tw.FILE_INDEX, tw.FILE_INDEX * N), tw.string_id(0))
    check(tw.string_id(12) == 100364,
          "and record 12 is 100364, the first free id after the identity tier",
          tw.string_id(12))
    check(tw.string_id(N - 1) - tw.string_id(0) == N - 1,
          "the map is linear across the whole file")
    # THE ORDERING, ON THE SYNTAX TREE. `plan` must be complete before any Writer
    # is constructed -- otherwise a refusal lands after some rows are written,
    # which is the defect test_iconset.py exists for one module over.
    src = open(os.path.join(HERE, "textwrite.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "plan")
    opens = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in ("Writer", "move", "replace")]
    check(not opens,
          "plan() constructs no Writer and calls no move/replace -- it is "
          "read-only by construction", [n.func.attr for n in opens])
    main = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    plan_line = min(n.lineno for n in ast.walk(main)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "plan")
    write_lines = [n.lineno for n in ast.walk(main)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in ("Writer", "move")]
    check(write_lines and plan_line < min(write_lines),
          "and main() completes the plan BEFORE the first write call",
          (plan_line, write_lines))
    # merge() is what the plan validates, so it must run inside plan().
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "merge"]
    check(calls, "plan() calls merge(), so every refusal fires before any write")


def section_real():
    print("\n== 5. the real archive ==")
    try:
        exe = vaultpath.vault_path("run", "reskin-roster", "Gw.exe")
        dat = vaultpath.vault_path("run", "reskin-roster", "Gw.dat")
    except SystemExit:
        exe = dat = None
    if not (exe and dat and os.path.exists(str(exe)) and os.path.exists(str(dat))):
        LEDGER.skip("section 5: no vault",
                    "the resolved row and the real size arithmetic")
        return
    fid, row, blob = tw.resolve_row(str(exe), str(dat))
    check(row > 0 and fid > 0,
          "text file %d resolves through the client's own pointer table"
          % tw.FILE_INDEX, "id 0x%X -> row %d" % (fid, row))
    recs, _t, tiled = textrec.walk(blob)
    check(tiled and len(recs) == N,
          "the live file tiles at %d records" % N, (len(recs), tiled))
    used = sum(1 for _b, _ba, p in recs if p)
    check(used == 12,
          "12 records are written -- the identity tier, and nothing else", used)
    # The size model, from the module docstring, verified against the artifact.
    empty = N * textrec.HEADER_SIZE + 2
    chars = sum(len(p) for _b, _ba, p in recs) // 2
    check(len(blob) == empty + 2 * chars,
          "size == 1024*6 + 2 + 2*chars, exactly",
          "%d == %d + %d" % (len(blob), empty, 2 * chars))
    strings = tw.skill_name_strings(8, str(exe), str(dat))
    check(len(strings) == 188, "188 names to write", len(strings))
    check(min(strings) == tw.FIRST_FREE_RECORD,
          "starting at the first free record", min(strings))
    p = tw.plan(str(dat), str(exe), strings)
    added = 2 * sum(len(v) for v in strings.values())
    check(p["new"] == len(blob) + added,
          "the planned size is the old size plus 2 bytes per character, with "
          "no per-record cost -- the 6-byte headers are already paid",
          "%d = %d + %d" % (p["new"], len(blob), added))
    check(p["relocate"] and p["placement"] is not None,
          "it is a relocation and datmove will place it",
          "%d B vs a %d B reservation" % (p["new"], p["reserved"]))

    # THE JOIN. The archive gets a string at a record; the client gets that
    # record's string ID in the skill's row+0x98. NOTHING joins them at run time
    # -- the client reads whatever number is in the row -- so if the two halves
    # disagree, every skill on the bar wears another skill's name and no check
    # anywhere fires. Both halves are read back through their REAL parsers here
    # (reskin's recipe loader, textwrite's record map), never compared in memory.
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
    import reskin                                                # noqa: E402
    frag = os.path.join(os.path.dirname(HERE), "clientpatch", "recipes",
                        "stormcaller-skills.toml")
    if not os.path.isfile(frag):
        LEDGER.skip("the recipe join", "no emitted fragment at %s" % frag)
        return
    sstr = reskin.load_recipe(frag)[8]
    client = {sid: val for sid, field, val in sstr if field == "name"}
    archive = {tw.string_id(r): nm for r, nm in strings.items()}
    truth = {sid: nm for sid, _r, nm in tw.name_assignment(8, str(exe), str(dat))}
    good = sum(1 for s in truth if archive.get(client.get(s)) == truth[s])
    check(good == len(truth),
          "every skill's recipe string id resolves to ITS OWN generated name",
          "%d of %d" % (good, len(truth)))
    shifted = sum(1 for s in truth
                  if archive.get(client.get(s, 0) + 1) == truth[s])
    check(shifted == 0,
          "and shifting the recipe by one id collapses it to zero -- the control "
          "that stops the check above passing on any consistent-looking map",
          "%d of %d" % (shifted, len(truth)))


def main():
    print("=" * 70)
    print("AUTHORED TEXT WRITER -- the first committed writer of archive strings")
    print("=" * 70)
    for fn in (section_identity, section_verbatim, section_refusals,
               section_guards, section_arithmetic, section_real):
        guarded(fn)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
