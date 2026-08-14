"""Find and disassemble the client's own handler for a message.

    python toolkit/clientscan/msghandler.py 0x0029
    python toolkit/clientscan/msghandler.py 0x0029 --follow      # + called fn
    python toolkit/clientscan/msghandler.py --table 0xa52d70     # whole table
    python toolkit/clientscan/msghandler.py 0x00E5 --follow --annotate
    python toolkit/clientscan/msghandler.py --callers 0x00822b80 # who calls it

WHY THIS EXISTS. Every other source we have for what a message MEANS is a
reconstruction, and on the one message this project needed most -- 0x0029
AGENT_MOVE_TO_POINT -- the two best reconstructions gave contradictory answers
and both were shipped and playtested before anyone thought to ask the client.
Field SHAPES we can already recover (schema/messages.json came from the binary's
own format tables). Field MEANINGS live in the code that consumes them, and this
is the shortest path to reading it.

HOW IT WORKS. The msgtable study recovered the message-format tables and the two
descriptor layouts. The receive descriptor is 12 bytes and its third member is a
dispatch function pointer:

    struct MsgFormatRecv { uint32 *cmds; uint32 count; void *dispatch; };
    struct MsgFormatSend { uint32 *cmds; uint32 count; };   // 8 bytes, no dispatch

so a handler is a table lookup, not a search. cmds[0] is the opcode.

Only RECEIVE tables have handlers -- from the client's point of view that is
everything the server sends, which is what we care about. Send tables are listed
so a lookup can say "that message has no handler because the client only ever
transmits it" rather than "not found".

A WARNING THIS TOOL CANNOT GIVE YOU, so read it here. The `cmds` arrays it
prints are, for more than half the catalogue, ZERO in the file and written at
load time -- and a zero decodes as a legal four-byte field. Do not read wire
shapes off the raw `cmds` this prints. `msgshape.py` next door recovers the
load-time writes and refuses to guess past a slot it could not account for;
that is the module to ask about shapes.

DEPENDENCIES. capstone and pefile. This used to be an unresolved exception to
CLAUDE.md's standard-library-only rule; **the owner settled it on 2026-08-06 as
an explicit carve-out for read-only client analysis**, and it now covers this
file and `codescan.py` next door and nothing else. `asserts.py`, `msgshape.py`,
`areatable.py` and `genericvalue.py` stay stdlib on purpose, so a bare machine
keeps every tool whose byte patterns are fixed, and a *claim* still wants a
stdlib checker even when a disassembler found it.

READ ONLY. Opens Gw.exe for reading and does nothing else. The install at
C:\\gw is the player's own and is never written, patched or launched from here.
"""

import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    import capstone
    import pefile
except ImportError:                                           # pragma: no cover
    sys.exit("needs capstone and pefile: python -m pip install capstone pefile")

import msgshape                                              # noqa: E402
from gwpe import PE as _StdlibPE                             # noqa: E402
import pinned                                                # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory, and names the copy it returned so a surprising result can be
# diagnosed in one line. This module used to spell it `C:\gw\Gw.exe` -- the
# owner's live install, which auto-updates and is therefore not necessarily the
# build every address in the studies is measured against.
find_exe = pinned.find


class Image:
    def __init__(self, path=None):
        path = path or find_exe()[0]
        self.path = path
        # The tables are DERIVED from this image rather than imported as a
        # constant -- `studies/crossbuild/PLAN.md` §3. They used to come from
        # `msgshape.TABLES`, 25 addresses measured on build 38797, so against
        # any other build this classifier read whatever happened to sit at
        # those addresses. The derivation is stdlib, hence the second PE reader:
        # `msgshape` deliberately takes no disassembler, and this module is one
        # of the two files allowed to.
        self.tables = msgshape.derive_tables(_StdlibPE(path))
        self.pe = pefile.PE(path, fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        with open(path, "rb") as fh:
            self.blob = fh.read()

    def off(self, va):
        rva = va - self.base
        for s in self.pe.sections:
            size = max(s.Misc_VirtualSize, s.SizeOfRawData)
            if s.VirtualAddress <= rva < s.VirtualAddress + size:
                return s.PointerToRawData + (rva - s.VirtualAddress)
        return None

    def u32(self, va):
        o = self.off(va)
        return None if o is None else int.from_bytes(self.blob[o:o + 4], "little")


def read_table(img, va, count, direction):
    """Yield (opcode, cmds, dispatch_or_None) for one table."""
    stride = 12 if direction == "RECV" else 8
    for i in range(count):
        e = va + stride * i
        cmds_va = img.u32(e)
        n = img.u32(e + 4)
        dispatch = img.u32(e + 8) if direction == "RECV" else None
        if not cmds_va or n is None or n > 64 or img.off(cmds_va) is None:
            continue
        cmds = [img.u32(cmds_va + 4 * k) for k in range(n)]
        if not cmds or cmds[0] is None:
            continue
        # NO & 0xFF HERE, and the mask that used to be here was a real defect.
        # MEASURED on build 38797: 229 of the 477 receive opcodes are above
        # 0xFF, so masking to a byte collapsed 0x0129 onto 0x0029 and a lookup
        # returned whichever entry the table walk reached first. Nearly half the
        # catalogue could resolve to somebody else's handler, and it would have
        # looked like a successful read -- the failure mode this repository
        # cares about most, since nothing in the output says which one you got.
        yield cmds[0], cmds, dispatch


def _cstr(img, va, cap=140):
    """The ASCII string at a VA, or None. Used only to annotate operands."""
    o = img.off(va)
    if o is None:
        return None
    b = img.blob[o:o + cap]
    z = b.find(b"\0")
    if z < 1:
        return None
    b = b[:z]
    if len(b) < 4 or not all(32 <= c < 127 for c in b):
        return None
    return b.decode("ascii")


def _annotator(img, exe):
    """A per-instruction comment: the client's own asserts and strings.

    A handler that logs `"Pending skill %u copy %d not found"` has told you
    what its arguments are called. That one string settled `skill_instance`
    after every written source had it as NOT FOUND, so surfacing them is worth
    a flag.
    """
    from asserts import Asserts
    az = Asserts(exe)
    by_va = {a.va: a for a in az.items}

    def note(ins):
        out = []
        a = by_va.get(ins.address)
        if a:
            out.append(f"ASSERT {a.module}:{a.line} {a.expr}")
        for tok in ins.op_str.replace(",", " ").replace("[", " ") \
                             .replace("]", " ").split():
            if tok.startswith("0x") and len(tok) >= 8:
                try:
                    s = _cstr(img, int(tok, 16))
                except ValueError:
                    s = None
                if s:
                    out.append(f'"{s[:100]}"')
        return ("   ; " + "  ".join(out)) if out else ""
    return note


def disasm(img, va, limit=90, indent="  ", note=None):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = img.off(va)
    if o is None:
        print(f"{indent}(0x{va:08x} is not mapped)")
        return []
    calls = []
    for n, ins in enumerate(md.disasm(img.blob[o:o + limit * 8], va)):
        print(f"{indent}0x{ins.address:08x}  {ins.mnemonic:<7} {ins.op_str}"
              f"{note(ins) if note else ''}")
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                calls.append(int(ins.op_str, 16))
            except ValueError:
                pass
        # A one-line `push ebp / mov ebp,esp / pop ebp / jmp target` is MSVC's
        # tail-call thunk. Following it is the difference between reading a
        # trampoline and reading the function.
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x") and n <= 4:
            try:
                calls.append(int(ins.op_str, 16))
            except ValueError:
                pass
            break
        if ins.mnemonic == "ret" or n >= limit:
            break
    return calls


def shape(img, va, limit=64):
    """A receive handler's SHAPE, without reading a line of it as English.

    (instructions, [callee VAs], terminates) for the handler at `va`. Silent -- the
    printing disassembler above is for a human reading one handler; this is for
    classifying 477 of them, and a classifier that prints 477 disassemblies has
    classified nothing.

    Deliberately shallow. It does not follow calls and does not try to understand a
    body: what it recovers is the handler's own instruction count and the set of
    functions it hands off to. That is enough to PARTITION the catalogue, which is all
    the sweep needs -- see classify().
    """
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = img.off(va)
    if o is None:
        return None
    calls, n, ended = [], 0, False
    for n, ins in enumerate(md.disasm(img.blob[o:o + limit * 8], va), start=1):
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            try:
                calls.append(int(ins.op_str, 16))
            except ValueError:
                pass
            if ins.mnemonic == "jmp" and n <= 4:
                ended = True       # MSVC tail-call thunk: the jmp IS the handoff
                break
        if ins.mnemonic == "ret":
            ended = True
            break
        if n >= limit:
            break
    return n, calls, ended


def classify(img):
    """Partition every receive opcode by what its handler DOES, structurally.

    THE POINT, and why this is not a curiosity. `studies/reconstruction/FINDINGS.md`
    measures that **332 of the 487 catalogued GAME_SMSG opcodes have never been seen
    from ArenaNet** -- a third of the protocol, for which we hold a field layout and no
    behaviour. The sweep that fixes that sends each one to a real client on loopback and
    records what happens. But a sweep with no stated prediction is a fishing trip, and
    the repo's own rule is that a probe states its expectation FIRST
    (`toolkit/authsrv/probes.py`). This is that prediction, and it is computed from the
    binary rather than guessed:

      FORWARDER    a short handler whose whole body hands off to exactly one function.
                   PREDICTS: whatever that callee does -- so opcodes sharing a callee
                   should behave alike, which is a check the sweep can fail.
      BODY         a handler that does its own work, or calls several functions.
                   PREDICTS: nothing specific; these are the ones worth watching.

    EVERY entry in the receive table carries a non-null dispatch pointer -- MEASURED,
    477 of 477, so there is no NO_HANDLER class and the sweep cannot expect a "this one
    cannot possibly do anything" bucket from the table. The opcodes that are genuinely
    absent are absent from the TABLE, not null within it: `schema/messages.json` holds
    487 and the receive table holds 477, so ten are catalogued with no receive entry.
    Pass the schema set to see them (`missing` in the returned dict).

    AND "NOT IN THE TABLE" DOES NOT MEAN "NO EFFECT", which is the correction that
    matters and it comes free with the corpus. Two of those ten -- `0x000C` and
    `0x000D` -- are sent by ArenaNet 145 and 144 times and are unmistakably acted on:
    they are the latency round trip `0x000C -> 0x0009 -> 0x000D` that drives the
    client's net graph (`toolkit/authsrv/test_ping.py`). So they are handled BELOW the
    message table, in the transport, which is exactly where a keepalive belongs. The
    honest prediction for the other eight is therefore "no MESSAGE-TABLE effect", and
    `0x000C`/`0x000D` are a standing counterexample to the stronger reading -- one this
    project already holds rather than one the sweep would have to discover.

    The partition is a PREDICTION, not a result. Scored against the dynamic sweep it is
    a real experiment; on its own it is a map of the catalogue and nothing more.
    """
    out = {}
    for va, count, direction, _caller, _chan in img.tables:
        if direction != "RECV":
            continue
        for opcode, cmds, dispatch in read_table(img, va, count, direction):
            if not dispatch or img.off(dispatch) is None:
                out[opcode] = {"class": "NO_HANDLER", "handler": dispatch or 0,
                               "instructions": 0, "callees": [], "fields": len(cmds)}
                continue
            got = shape(img, dispatch)
            if got is None:
                out[opcode] = {"class": "NO_HANDLER", "handler": dispatch,
                               "instructions": 0, "callees": [], "fields": len(cmds)}
                continue
            n, calls, _ended = got
            kind = "FORWARDER" if len(calls) == 1 else "BODY"
            out[opcode] = {"class": kind, "handler": dispatch, "instructions": n,
                           "callees": calls, "fields": len(cmds)}
    return out


def print_classify(img, seen=None):
    """The partition, plus the callee groups that make it falsifiable."""
    table = classify(img)
    buckets = collections.Counter(v["class"] for v in table.values())
    print(f"\n{len(table)} receive opcodes classified by handler shape")
    for kind in ("NO_HANDLER", "FORWARDER", "BODY"):
        print(f"  {kind:<11} {buckets.get(kind, 0)}")

    # Handlers that hand off to the SAME function are the same kind of message. This is
    # the group that makes the prediction refutable: if two opcodes share a callee and
    # the sweep sees an effect for one and silence for the other, either the partition
    # is wrong or the readout missed it -- and both are findings.
    groups = collections.defaultdict(list)
    for opcode, v in table.items():
        if v["class"] == "FORWARDER":
            groups[v["callees"][0]].append(opcode)
    shared = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"\n{len(groups)} distinct forwarder callees; {len(shared)} are shared by "
          f"more than one opcode")
    for callee in sorted(shared, key=lambda c: -len(shared[c]))[:10]:
        ops = " ".join(f"0x{o:04X}" for o in sorted(shared[callee])[:12])
        more = "" if len(shared[callee]) <= 12 else f" (+{len(shared[callee]) - 12})"
        print(f"  0x{callee:08x}  {len(shared[callee]):>3} opcodes  {ops}{more}")

    if seen:
        unseen = sorted(set(table) - set(seen))
        outside = sorted(set(seen) - set(table))
        print(f"\nof {len(table)} table entries, {len(set(seen) & set(table))} have been "
              f"observed from ArenaNet and {len(unseen)} never have")
        b = collections.Counter(table[o]["class"] for o in unseen)
        for kind in ("FORWARDER", "BODY"):
            print(f"  never-seen {kind:<11} {b.get(kind, 0)}")
        if outside:
            print(f"\n  and {len(outside)} OBSERVED opcode(s) are not in the receive "
                  f"table at all: {' '.join(f'0x{o:04X}' for o in outside)}")
            print(f"  -- ArenaNet sends them and the client acts on them, so they are "
                  f"handled BELOW\n     the message table. Any prediction of the form "
                  f"'absent from the table => inert'\n     is refuted by these before "
                  f"the sweep runs.")
        print(f"\nPREDICTION, stated before the sweep: all {len(unseen)} never-seen "
              f"opcodes reach a\n  handler, so NONE of them is inert by construction "
              f"and a silent result is a fact\n  about the READOUT or about the "
              f"client's state, never about reachability.\n"
              f"  {b.get('FORWARDER', 0)} forward to one function and should behave "
              f"like the other opcodes\n  sharing that callee -- which is the half "
              f"this can fail on.")
    return table


def callers(exe, target):
    """Every direct `call` to a VA. One implementation, in asserts.py."""
    from asserts import Asserts
    return Asserts(exe).direct_callers(target)


def source_files(img, va, limit=400):
    """The ArenaNet source paths an assert inside this handler names.

    Every assert compiles to `mov edx, <expr string>; mov ecx, <file string>;
    call <assert>`, so the file a message is implemented in is readable straight
    out of its handler. That turns "which reconstruction do we believe" into
    "which file did ArenaNet write it in", and it is the strongest naming source
    this project has. Discovered while failing to find the death message.
    """
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = img.off(va)
    if o is None:
        return set()
    out = set()
    for n, ins in enumerate(md.disasm(img.blob[o:o + limit * 8], va)):
        if ins.mnemonic == "mov" and ins.op_str.startswith(("edx, 0x", "ecx, 0x")):
            so = img.off(int(ins.op_str.split("0x")[1], 16))
            if so is not None:
                text = img.blob[so:so + 120].split(b"\0")[0]
                if text.startswith(b"P:"):
                    out.add(text.decode("ascii", "replace"))
        if ins.mnemonic == "ret" or n >= limit:
            break
    return out


def print_map(img):
    """opcode -> the source file its handler asserts in, for every RECV table."""
    import collections
    byfile = collections.defaultdict(list)
    n = 0
    for tva, count, direction, _caller, _chan in img.tables:
        if direction != "RECV":
            continue
        for op, cmds, disp in read_table(img, tva, count, direction):
            if not disp:
                continue
            n += 1
            for f in source_files(img, disp):
                byfile[f].append(op)
    print(f"{n} receive handlers read; {len(byfile)} source files named\n")
    for f in sorted(byfile, key=lambda k: -len(byfile[k])):
        ops = sorted(set(byfile[f]))
        print(f"{len(ops):5}  {f}")
        print("       " + " ".join(f"0x{o:04X}" for o in ops))
    print("\nHandlers with no assert name no file. That is silence, not absence.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("opcode", nargs="?", help="e.g. 0x0029")
    ap.add_argument("--map", action="store_true",
                    help="map every receive opcode to the ArenaNet source file "
                         "its handler asserts in")
    ap.add_argument("--classify", action="store_true",
                    help="partition every receive opcode by handler SHAPE "
                         "(NO_HANDLER / FORWARDER / BODY). This is the loopback "
                         "sweep's prediction, stated before it runs")
    ap.add_argument("--seen", default=None, metavar="FILE",
                    help="a file of opcodes observed from ArenaNet (one per line, "
                         "hex or decimal); --classify then splits its prediction "
                         "over the never-seen set")
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--table", help="dump one table by VA instead")
    ap.add_argument("--follow", action="store_true",
                    help="also disassemble the functions the handler calls, "
                         "and step through MSVC tail-call thunks")
    ap.add_argument("--annotate", action="store_true",
                    help="comment each line with the assert or string it "
                         "references -- the client's own words")
    ap.add_argument("--callers", help="VA; list every direct call to it")
    ap.add_argument("--depth", type=int, default=1,
                    help="how many call levels --follow descends (default 1)")
    ap.add_argument("--limit", type=int, default=90)
    a = ap.parse_args()

    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    print(f"client: {a.exe}\n        ({why})\n")
    img = Image(a.exe)
    print(f"{a.exe}  {len(img.blob):,} bytes, image base 0x{img.base:08x}")
    note = _annotator(img, a.exe) if a.annotate else None

    if a.map:
        print_map(img)
        return 0

    if a.classify:
        seen = None
        if a.seen:
            seen = set()
            for line in open(a.seen, encoding="utf-8"):
                line = line.split("#", 1)[0].strip()
                if line:
                    seen.add(int(line, 0))
        print_classify(img, seen)
        return 0

    if a.callers:
        target = int(a.callers, 0)
        hits = callers(a.exe, target)
        print(f"{len(hits)} direct caller(s) of 0x{target:08x}")
        for h in hits:
            print(f"  0x{h:08x}")
        return 0

    if a.table:
        tva = int(a.table, 0)
        entry = next((t for t in img.tables if t.va == tva), None)
        if entry is None:
            sys.exit(f"0x{tva:08x} is not a table this build registers; "
                     f"run --map to list them")
        for op, cmds, disp in read_table(img, entry.va, entry.count,
                                         entry.direction):
            d = f"dispatch 0x{disp:08x}" if disp else "(send: no dispatch)"
            print(f"  0x{op:04x}  {d}  cmds {[hex(c) for c in cmds]}")
        return 0

    if not a.opcode:
        ap.error("give an opcode, or --table")
    want = int(a.opcode, 0)

    found = []
    for tva, count, direction, _caller, _chan in img.tables:
        for op, cmds, disp in read_table(img, tva, count, direction):
            if op == want:
                found.append((tva, direction, cmds, disp))
    if not found:
        sys.exit(f"opcode 0x{want:04x} is in no table")

    for tva, direction, cmds, disp in found:
        print(f"\ntable 0x{tva:08x} [{direction}]  cmds {[hex(c) for c in cmds]}")
        if disp is None:
            print("  the client only SENDS this one; there is no handler to read")
            continue
        print(f"  handler 0x{disp:08x}")
        print("  " + "-" * 66)
        calls = disasm(img, disp, a.limit, note=note)
        if a.follow:
            # Breadth-first to --depth. Depth 1 is the old behaviour. Depth 3
            # is what it takes to get from a skill opcode to the code that
            # means something: the handler is a trampoline into ChCliApi,
            # which is a trampoline into ChCliSkill, which is where the
            # asserts and the log strings live.
            seen, queue = set(), [(c, 1) for c in dict.fromkeys(calls)]
            while queue:
                c, depth = queue.pop(0)
                if c in seen or depth > a.depth:
                    continue
                seen.add(c)
                print(f"\n  depth {depth}, reached from the handler: 0x{c:08x}")
                print("  " + "-" * 66)
                for m in disasm(img, c, a.limit, indent="    ", note=note):
                    queue.append((m, depth + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
