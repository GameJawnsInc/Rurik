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

That check is cheap and it is falsifiable in the direction that matters: a row whose
first byte is not what its SHAPE requires is either a moved address or a site that is
no longer what the row says it is, and both must stop the build rather than be papered
over.

TWO SHAPES SINCE 2026-08-29, AND THE CHECK GOT STRONGER RATHER THAN WEAKER. Every site
used to be a `55 push ebp` entry, which is what let the handler re-emulate ONE
instruction (PLAN.md §7 Q12(d)). The MapFindPath RETURN tap needed a second: `C3 ret`.
The loosening that would have been wrong is a check that accepts "0x55 or 0xC3"
anywhere -- it would arm a ret's emulation on an entry byte and corrupt the frame. So
the shape is DECLARED PER ROW and the byte is checked against THAT shape's byte only,
which is a tighter constraint than the single global one it replaced: an entry row
that decays into a ret is now caught, and before it would have been caught only
because 0xC3 != 0x55. An unrecognised shape REFUSES rather than defaulting, because
defaulting to `entry` would arm the push-ebp emulation on whatever byte is there.

TWO STRUCTURAL REFUSALS THE BYTES CANNOT CATCH, both specific to `ret` rows and both
paid for in advance by the disassembly (content/movecode.toml's ret block): at a ret
`ecx` is scratch, so `deref_agent` is meaningless there; and MapFindPath overwrites
its caller's arg2 slot with FPU scratch, so a ret row that inherited the entry row's
`deref_arg_b = 2` would dereference a float bit pattern as a point pointer -- and
`readable()` can ACCEPT it, because 10000.0f is 0x461C4000, a plausible address. That
is a silent-garbage-coordinates bug, so it is refused here rather than trusted to a
row's value.

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

# THE SHAPES THE HANDLER EMULATES, and the byte each one REQUIRES. This is the
# single home for that pairing: movehook.c emulates by shape, attach.py's live
# pre-flight imports this map rather than restating the bytes (Q12(a) refuses two
# homes for one fact), and a row naming a shape outside this dict is refused.
SHAPE_BYTE = {
    "entry": 0x55,      # push ebp -> esp -= 4; [esp] = ebp; eip = a + 1
    "ret":   0xC3,      # ret      -> eip = [esp]; esp += 4
}
DEFAULT_SHAPE = "entry"     # every row that predates the shape column


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
        shape = row.get("shape", DEFAULT_SHAPE)
        need = SHAPE_BYTE.get(shape)
        if need is None:
            bad.append((name, f"shape {shape!r} is not one movehook emulates. Known: "
                              f"{sorted(SHAPE_BYTE)}. An unrecognised shape REFUSES "
                              f"rather than defaulting to {DEFAULT_SHAPE!r} -- a "
                              f"default would arm the push-ebp emulation on whatever "
                              f"byte is actually there."))
            continue
        # STRUCTURAL REFUSALS FOR `ret` ROWS. Neither is visible in a byte; both
        # are silent-garbage bugs rather than mistakes a reader would notice. See
        # the module docstring and content/movecode.toml's ret block.
        if shape == "ret" and row.get("deref_agent"):
            bad.append((name, "a `ret` row sets deref_agent, but ecx is SCRATCH at a "
                              "return -- the handler would read a stale register as "
                              "an agent pointer and store whatever it found."))
            continue
        if shape == "ret" and int(row.get("deref_arg_b") or 0):
            bad.append((name, f"a `ret` row sets deref_arg_b = "
                              f"{int(row.get('deref_arg_b') or 0)}. MapFindPath "
                              f"overwrites its caller's arg2 slot with FPU scratch "
                              f"before any branch, so that slot holds a FLOAT at "
                              f"every ret -- and readable() can accept it (10000.0f "
                              f"is 0x461C4000), handing back 16 bytes of unrelated "
                              f"memory as a coordinate. Read `to` at the entry row."))
            continue
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
                              f"is no longer a {shape}."))
        elif got != need:
            bad.append((name, f"first byte 0x{got:02X} is not the 0x{need:02X} that "
                              f"shape {shape!r} requires. movehook emulates exactly "
                              f"the shapes in SHAPE_BYTE; a byte outside its own "
                              f"shape needs its own emulation and must not be armed "
                              f"by this generator."))
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
    a("/* THE SHAPES THE HANDLER EMULATES. Every site's byte was re-read from the")
    a(" * pinned client and matched against ITS OWN shape's byte before this file")
    a(" * was written; a byte outside its shape stops generation. Two shapes, not")
    a(" * one free-for-all: an entry row that decayed into a ret is still caught.")
    a(" * See PLAN.md §7 Q12(d) and content/movecode.toml's ret block. */")
    a("#define SHAPE_ENTRY 0u   /* 0x55 push ebp -> esp -= 4; [esp] = ebp; eip = a+1 */")
    a("#define SHAPE_RET   1u   /* 0xC3 ret      -> eip = [esp]; esp += 4           */")
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
    a("    int           deref_out;     /* arg index of `int* outCount`, 0=none */")
    a("    int           deref_out_path;/* arg index of `point* outPath`, 0=none */")
    a("    unsigned      shape;         /* SHAPE_ENTRY or SHAPE_RET -- selects which")
    a("                                    ONE instruction the handler re-emulates. */")
    a("} site_t;")
    a("")
    a("/* rva, name, deref_agent, deref_a, deref_b, deref_agent_arg, deref_fence,")
    a(" * stride, deref_out, deref_out_path, shape */")
    a("static const site_t SITES[NSITES] = {")
    for n in names:
        r = sites[n]
        shape = r.get("shape", DEFAULT_SHAPE)
        a(f"    {{ 0x{r['rva']:08X}u, \"{n}\", "
          f"{1 if r.get('deref_agent') else 0}, "
          f"{int(r.get('deref_arg_a') or 0)}, "
          f"{int(r.get('deref_arg_b') or 0)}, "
          f"{int(r.get('deref_agent_arg') or 0)}, "
          f"{1 if r.get('deref_fence') else 0}, "
          f"{int(r.get('stride') or 0)}u, "
          f"{int(r.get('deref_out') or 0)}, "
          f"{int(r.get('deref_out_path') or 0)}, "
          f"{'SHAPE_RET  ' if shape == 'ret' else 'SHAPE_ENTRY'} }},"
          f"   /* 0x{r['va']:08X} */")
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
