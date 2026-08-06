#!/usr/bin/env python3
"""Static disassembly helpers for the textrec study.

READ ONLY on the vault client snapshot. Never launches anything, never
touches C:\\gw, never opens a socket.

NOTE: imports capstone, which is a third-party dependency. This lives in
studies/, not toolkit/, deliberately: CLAUDE.md's stdlib-only rule is scoped
to toolkit/, and study tooling that needs a disassembler cannot meet it.
msghandler.py already carries the same tension inside toolkit/ — flagged for
an owner ruling; see the session that produced studies/textrec/.

    python studies/textrec/tools/dis.py fn 0x7cb000            # disassemble
    python studies/textrec/tools/dis.py fn 0x7cb000 -n 300
    python studies/textrec/tools/dis.py hex 0x93d8a0 64        # dump bytes
    python studies/textrec/tools/dis.py xref 0x7cb000          # who references
    python studies/textrec/tools/dis.py str 0x93f2fc           # C string at VA
"""

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "toolkit"))
from gwpe import PE  # noqa: E402

try:
    import capstone
except ImportError:  # pragma: no cover
    sys.exit("needs capstone: python -m pip install capstone")

DEFAULT_EXE = r"C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe"


def va_off(pe, va):
    off = pe.rva_to_off(va - pe.image_base)
    if off is None:
        sys.exit(f"VA 0x{va:08x} is not file-backed")
    return off


def cmd_fn(pe, args):
    """Linear disassembly from a VA. Stops at ret unless --past-ret."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    off = va_off(pe, args.va)
    n = 0
    for ins in md.disasm(pe.data[off:off + args.n * 12], args.va):
        line = f"0x{ins.address:08x}  {ins.bytes.hex():<20}  {ins.mnemonic:<7} {ins.op_str}"
        # annotate immediates that point at readable strings
        for tok in ins.op_str.replace(",", " ").replace("[", " ").replace("]", " ").split():
            if tok.startswith("0x"):
                try:
                    tva = int(tok, 16)
                except ValueError:
                    continue
                if tva > pe.image_base:
                    toff = pe.rva_to_off(tva - pe.image_base)
                    if toff is not None:
                        raw = pe.data[toff:toff + 80].split(b"\0")[0]
                        if len(raw) >= 4 and all(32 <= c < 127 for c in raw):
                            line += f'   ; "{raw.decode()}"'
                            break
                        # wide string?
                        wraw = pe.data[toff:toff + 160]
                        try:
                            w = wraw.decode("utf-16-le", "strict")
                        except UnicodeDecodeError:
                            w = ""
                        w = w.split("\0")[0]
                        if len(w) >= 4 and all(32 <= ord(c) < 127 for c in w):
                            line += f'   ; L"{w}"'
                            break
        print(line)
        n += 1
        if ins.mnemonic == "ret" and not args.past_ret:
            break
        if n >= args.n:
            break


def cmd_hex(pe, args):
    off = va_off(pe, args.va)
    data = pe.data[off:off + args.count]
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        hexs = " ".join(f"{b:02x}" for b in row)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"0x{args.va + i:08x}  {hexs:<48}  {text}")


def cmd_xref(pe, args):
    """File offsets holding this VA as a little-endian dword (abs refs),
    plus rel32 call/jmp targets that land on it."""
    needle = struct.pack("<I", args.va)
    hits = pe.find(needle)
    for h in hits:
        rva = pe.off_to_rva(h)
        print(f"abs   file 0x{h:06x}  va 0x{(rva + pe.image_base) if rva is not None else 0:08x}")
    # rel32: scan .text for E8/E9 whose target is va
    for sec in pe.sections:
        if sec["name"] != ".text":
            continue
        d = pe.data
        lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
        for opc, kind in ((0xE8, "call"), (0xE9, "jmp ")):
            i = lo
            while True:
                i = d.find(bytes([opc]), i, hi - 4)
                if i == -1:
                    break
                rel = struct.unpack_from("<i", d, i + 1)[0]
                src_va = pe.off_to_rva(i) + pe.image_base
                if src_va + 5 + rel == args.va:
                    print(f"{kind}  file 0x{i:06x}  va 0x{src_va:08x}")
                i += 1


def cmd_str(pe, args):
    off = va_off(pe, args.va)
    raw = pe.data[off:off + 200].split(b"\0")[0]
    print(repr(raw))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=DEFAULT_EXE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fn")
    p.add_argument("va", type=lambda s: int(s, 0))
    p.add_argument("-n", type=int, default=120)
    p.add_argument("--past-ret", action="store_true")
    p = sub.add_parser("hex")
    p.add_argument("va", type=lambda s: int(s, 0))
    p.add_argument("count", type=int, nargs="?", default=64)
    p = sub.add_parser("xref")
    p.add_argument("va", type=lambda s: int(s, 0))
    p = sub.add_parser("str")
    p.add_argument("va", type=lambda s: int(s, 0))
    args = ap.parse_args()
    pe = PE(args.exe)
    {"fn": cmd_fn, "hex": cmd_hex, "xref": cmd_xref, "str": cmd_str}[args.cmd](pe, args)


if __name__ == "__main__":
    main()
