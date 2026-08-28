"""Generate `sites.h` for movehook.c from content/movecode.toml — and VERIFY it.

    python toolkit/clientscan/movehook/gensites.py            # write sites.h
    python toolkit/clientscan/movehook/gensites.py --check     # verify only

WHY A GENERATOR AND NOT TWO COPIES. Owner's ruling, PLAN.md §7 Q12(a): client-derived
constants live in `content/*.toml` with `source = "client-table"`, because a row there
inherits `content.py`'s refusals automatically -- the extractor must be named and
present, and `NEEDS_BUILD` forces the build stamp -- while a `#define` in a .c file
inherits nothing at all. The ruling's one hard refusal is SPLITTING a struct's offsets
across two homes, and a hand-maintained header beside a TOML table is exactly that
split with a promise attached. So the header is generated, it says so at the top, and
nothing but this script may write it.

WHAT MAKES THIS MORE THAN A TRANSCRIBER, and it is the whole point. Every address in
`movecode.toml` is build 38797 and every one of them MOVES when ArenaNet ships. A
generator that only copied numbers would happily arm a breakpoint in the middle of an
unrelated instruction after a build bump, and the first sign would be the client
dying in a way nobody could attribute. So each row carries `first_byte`, and this
script RE-READS that byte out of the pinned client and refuses to emit anything if a
single row disagrees.

That check is cheap and it is falsifiable in the direction that matters: all four
sites are function entries beginning `55` (`push ebp`), which is what lets movehook's
handler re-emulate ONE instruction shape (PLAN.md §7 Q12(d)). A row whose first byte
is no longer `0x55` is either a moved address or a site that is no longer an entry,
and both must stop the build rather than be papered over.

STDLIB ONLY, deliberately. It reads bytes at a virtual address through `toolkit/gwpe.py`
and needs no disassembler, so it stays outside the capstone/pefile carve-out that
Q12(c) ruled must stay file-scoped. This runs on a bare machine.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "clientscan"))

import content as content_mod                                  # noqa: E402
import gwpe                                                    # noqa: E402
import pinned                                                  # noqa: E402

HEADER = os.path.join(HERE, "sites.h")

# The build these rows are measured against. Read from the rows themselves rather
# than pinned here, so the TOML stays the single home (Q12(a)) -- this constant is
# only the value we REFUSE to differ from.
EXPECT_FIRST_BYTE = 0x55            # push ebp; see the module docstring


class GenError(Exception):
    """A row that cannot be turned into a header line. Never a warning."""


def rows():
    """(hook_sites, agent_offsets) from content/movecode.toml, provenance-checked.

    `content.load()` is what enforces the provenance conditions, so going through it
    rather than reading the TOML directly is the point: a row that lost its extractor
    or its build stamp fails HERE, before a single byte is generated.
    """
    tables = content_mod.load()
    tables = tables.tables if hasattr(tables, "tables") else tables
    sites = tables.get("hook_site") or {}
    offs = tables.get("agent_offset") or {}
    if not sites:
        raise GenError("no [hook_site] rows in the content store. Refusing to "
                       "generate an empty site table -- a hook with no sites is a "
                       "run that measures nothing.")
    return sites, offs


def verify(sites, exe=None):
    """Re-read every site's first byte from the pinned client. Returns [(name, why)].

    An empty list means every row agrees with the binary. Anything else is a refusal
    reason, and the caller must not write a header.
    """
    path, why = (exe, "given") if exe else pinned.find()
    pe = gwpe.PE(path)
    bad = []
    for name in sorted(sites):
        row = sites[name]
        va, rva = row["va"], row["rva"]
        want = row["first_byte"]
        if va - pe.image_base != rva:
            bad.append((name, f"va 0x{va:08X} - image base 0x{pe.image_base:08X} "
                              f"= 0x{va - pe.image_base:08X}, but the row says rva "
                              f"0x{rva:08X}. One of the two is wrong."))
            continue
        off = pe.rva_to_off(rva)
        if off is None:
            bad.append((name, f"rva 0x{rva:08X} is not backed by file bytes in any "
                              f"section -- it cannot be read, let alone patched."))
            continue
        got = pe.data[off]
        if got != want:
            bad.append((name, f"first byte at 0x{va:08X} is 0x{got:02X}, the row "
                              f"says 0x{want:02X}. The address moved, or the site "
                              f"is no longer a function entry."))
        elif got != EXPECT_FIRST_BYTE:
            bad.append((name, f"first byte 0x{got:02X} is not `push ebp` (0x55). "
                              f"movehook re-emulates exactly one instruction shape; "
                              f"a site that is not an entry needs its own emulation "
                              f"and must not be armed by this generator."))
    return bad, path


def emit(sites, offs, exe_path):
    out = []
    a = out.append
    a("/* GENERATED by toolkit/clientscan/movehook/gensites.py -- DO NOT EDIT.")
    a(" *")
    a(" * Source of truth: content/movecode.toml, whose rows carry their own")
    a(" * provenance and are checked by content.py. Owner's ruling PLAN.md §7 Q12(a).")
    a(" * Every first byte below was re-read from the pinned client and matched.")
    a(f" * Verified against: {os.path.basename(os.path.dirname(exe_path))}")
    a(" */")
    a("#ifndef MOVEHOOK_SITES_H")
    a("#define MOVEHOOK_SITES_H")
    a("")
    a("/* All sites are function entries beginning `55` (push ebp), so the handler")
    a(" * re-emulates ONE instruction shape. See PLAN.md §7 Q12(d). */")
    a("#define SITE_FIRST_BYTE 0x55u")
    a("")
    names = sorted(sites)
    a(f"#define NSITES {len(names)}u")
    a("")
    a("typedef struct {")
    a("    unsigned long rva;")
    a("    const char   *name;")
    a("    int           deref_agent;   /* is ecx an agent pointer at entry? */")
    a("    int           deref_a;       /* arg index (1-6) to deref as a point, 0=none */")
    a("    int           deref_b;")
    a("    int           deref_agent_arg; /* arg index holding a SECOND agent, 0=none */")
    a("    int           deref_fence;   /* read AgTrack's per-agent clientControlled */")
    a("    unsigned      stride;        /* store 1 hit in N; 0/1 = every hit. The")
    a("                                    HIT COUNT is unaffected and is what the")
    a("                                    sidecar reports, so a strided site still")
    a("                                    gives an exact denominator -- see the")
    a("                                    note at the stride test in movehook.c. */")
    a("} site_t;")
    a("")
    a("static const site_t SITES[NSITES] = {")
    for n in names:
        r = sites[n]
        a(f"    {{ 0x{r['rva']:08X}u, \"{n}\", "
          f"{1 if r.get('deref_agent') else 0}, "
          f"{int(r.get('deref_arg_a') or 0)}, "
          f"{int(r.get('deref_arg_b') or 0)}, "
          f"{int(r.get('deref_agent_arg') or 0)}, "
          f"{1 if r.get('deref_fence') else 0}, "
          f"{int(r.get('stride') or 0)}u }},   /* 0x{r['va']:08X} */")
    a("};")
    a("")
    a("/* Agent struct offsets the handler reads at each hit. */")
    for n in sorted(offs):
        r = offs[n]
        a(f"#define A_{n.upper():<20} 0x{r['offset']:02X}u"
          f"   /* {r.get('name','')} */")
    a("")
    a("#endif /* MOVEHOOK_SITES_H */")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default=None, help="client to verify against")
    ap.add_argument("--check", action="store_true",
                    help="verify only; write nothing and exit non-zero on a mismatch")
    args = ap.parse_args()

    sites, offs = rows()
    bad, path = verify(sites, args.exe)
    print(f"client: {path}")
    print(f"{len(sites)} hook site(s), {len(offs)} agent offset(s)")
    if bad:
        print("\nREFUSING TO GENERATE -- these rows disagree with the binary:")
        for name, whyname in bad:
            print(f"  {name}: {whyname}")
        print("\nA build bump moves every address in content/movecode.toml. Re-derive "
              "them with codescan and update the rows; do not edit sites.h.")
        return 1
    for n in sorted(sites):
        print(f"  {n:10} 0x{sites[n]['va']:08X}  first byte 0x{sites[n]['first_byte']:02X}  OK")
    if args.check:
        print("\n--check: every row agrees with the binary. Nothing written.")
        return 0
    text = emit(sites, offs, path)
    # IDEMPOTENT: an unchanged header is NOT rewritten, and that is a bug fix
    # rather than tidiness. `attach.py` refuses to inject when sites.h is NEWER
    # than the DLL, on the sound reasoning that a regenerated header means the DLL
    # was built against a different site set. But this script used to rewrite the
    # file unconditionally -- so merely RUNNING it, which RUN-R4.md's own
    # preconditions tell the operator to do as a read-only-looking check, bumped
    # the mtime past the DLL and armed that refusal against a DLL that was
    # perfectly current. The operator hit exactly that mid-session, after a
    # verified build, on a header whose bytes had not changed.
    try:
        current = open(HEADER, encoding="utf-8", newline="").read()
    except OSError:
        current = None
    if current == text:
        print(f"\n{HEADER} is already current ({len(text)} bytes) -- not "
              f"rewritten, so the DLL's build stamp stays valid.")
        return 0
    with open(HEADER, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"\nwrote {HEADER} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
