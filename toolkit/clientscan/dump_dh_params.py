"""Locate the pinned Diffie-Hellman parameter struct in a Guild Wars client.

This is R1's go/no-go probe, and its whole virtue is that it needs no network and
does not launch anything. Read-only against the owner's own install.

Why it decides R1
-----------------
The client's auth/game channels are RC4 keyed by a static-ephemeral Diffie-Hellman
exchange in which the SERVER's public value B is never transmitted -- the client
already has it, compiled in. The client sends A = g^a mod p and derives the shared
secret locally as B^a mod p.

A server we control cannot reproduce that shared secret, because doing so needs b,
the discrete log of B, which ArenaNet never shipped. So a local server MUST replace
the client's baked-in (g, p, B) with a triple whose private exponent we hold. That
makes a patched client a permanent, mandatory build step -- and it falsifies
HANDOFF.md section 4's claim that "R1 needs no binary patching."

This tool answers the prerequisite question: is that struct still where the public
tooling expects it in OUR pinned build?

  found, g == 4, 512-bit prime  ->  the scheme is unchanged; R1 proceeds as planned
  found, different shape        ->  Reforged altered the parameters; re-plan R1
  not found                     ->  the accessor was recompiled; re-derive the
                                    signature before trusting any patching tool

Method
------
Scan .text for the accessor's prologue. The signature is public knowledge, used by
both Headquarter's dump_key.py (which reads the struct) and OpenTyria's patch-gw.py
(which writes it) -- two independent implementations that agree, which is why it is
trustworthy. The instruction `C7 00 88 00 00 00` is `mov dword [eax], 0x88`: the
function stamps the struct's own size, 136 bytes, which is a useful sanity anchor.
The `B8` that follows is `mov eax, <imm32>` carrying the struct's virtual address.

Layout, from the struct base:
    +0   u32   always 1 in observed builds
    +4   u32   generator g
    +8   64    prime modulus p, little-endian
    +72  64    server public value B, little-endian

Provenance
----------
Prints only shapes, bit lengths and short fingerprints by default. The parameters
are ArenaNet-derived; `--full` writes them to a file, and that file belongs in the
vault. Never commit the output.
"""

import argparse
import hashlib
import struct
import sys

# Prologue of the accessor that returns the DH parameter struct.
# Ends just before the `mov eax, imm32` whose operand is the struct's VA.
SIG_KEYS = bytes.fromhex("8B4508C700880000 00B8".replace(" ", ""))
SIG_KEYS_PTR_OFFSET = 0x0A

STRUCT_SIZE = 0x88  # 136, and the value the accessor writes


class PE:
    """Minimal PE reader: enough to map an RVA to a file offset."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        if d[:2] != b"MZ":
            raise ValueError("not a PE file")
        e = struct.unpack_from("<I", d, 0x3C)[0]
        if d[e:e + 4] != b"PE\0\0":
            raise ValueError("bad PE signature")
        self.machine = struct.unpack_from("<H", d, e + 4)[0]
        nsec = struct.unpack_from("<H", d, e + 6)[0]
        opt_size = struct.unpack_from("<H", d, e + 20)[0]
        magic = struct.unpack_from("<H", d, e + 24)[0]
        if magic != 0x10B:
            raise ValueError("expected a 32-bit PE32 image")
        self.image_base = struct.unpack_from("<I", d, e + 52)[0]
        sec_off = e + 24 + opt_size
        self.sections = []
        for i in range(nsec):
            o = sec_off + i * 40
            name = d[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", d, o + 8)
            chars = struct.unpack_from("<I", d, o + 36)[0]
            self.sections.append({"name": name, "vaddr": vaddr, "vsize": vsize,
                                  "rawptr": rawptr, "rawsize": rawsize,
                                  "exec": bool(chars & 0x20000000)})

    def rva_to_off(self, rva):
        for s in self.sections:
            if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
                delta = rva - s["vaddr"]
                if delta < s["rawsize"]:
                    return s["rawptr"] + delta
                return None  # inside virtual padding, not backed by file bytes
        return None

    def section_of(self, rva):
        for s in self.sections:
            if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
                return s["name"]
        return "?"


def find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


def fingerprint(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exe", nargs="?", default=r"C:\gw\Gw.exe")
    ap.add_argument("--full", metavar="PATH",
                    help="write the actual parameters here (vault only, never the repo)")
    a = ap.parse_args()

    pe = PE(a.exe)
    print(f"file       : {a.exe}")
    print(f"machine    : 0x{pe.machine:x} ({'x86' if pe.machine == 0x14c else 'other'})")
    print(f"image base : 0x{pe.image_base:08x}")
    print(f"sections   : {', '.join(s['name'] for s in pe.sections)}")
    print()

    hits = find_all(pe.data, SIG_KEYS)
    print(f"accessor signature: {len(hits)} match(es)")
    if not hits:
        print("\nNOT FOUND. The accessor was recompiled or the scheme changed.")
        print("Do NOT trust any published patching tool against this build until the")
        print("signature is re-derived. This is a real R1 finding, not a tool failure.")
        return 2

    ok = False
    for off in hits:
        ptr_off = off + SIG_KEYS_PTR_OFFSET
        va = struct.unpack_from("<I", pe.data, ptr_off)[0]
        rva = va - pe.image_base
        target = pe.rva_to_off(rva)
        print(f"\n  match at file 0x{off:08x} -> struct VA 0x{va:08x} "
              f"(RVA 0x{rva:06x}, section {pe.section_of(rva)})")
        if target is None or target + STRUCT_SIZE > len(pe.data):
            print("    pointer does not resolve into file-backed data; skipping")
            continue

        blob = pe.data[target:target + STRUCT_SIZE]
        root, gen = struct.unpack_from("<II", blob, 0)
        prime = int.from_bytes(blob[8:72], "little")
        pubkey = int.from_bytes(blob[72:136], "little")

        print(f"    word0 (expect 1)  : {root}")
        print(f"    generator g       : {gen}")
        print(f"    prime p           : {prime.bit_length()} bits, "
              f"fingerprint {fingerprint(blob[8:72])}")
        print(f"    server public B   : {pubkey.bit_length()} bits, "
              f"fingerprint {fingerprint(blob[72:136])}")

        checks = {
            "word0 == 1": root == 1,
            "generator == 4": gen == 4,
            "prime is 512-bit": prime.bit_length() == 512,
            "prime is odd": prime % 2 == 1,
            "B in range 1 < B < p": 1 < pubkey < prime,
            "B is not tiny": pubkey.bit_length() > 480,
        }
        for k, v in checks.items():
            print(f"    [{'ok' if v else 'FAIL'}] {k}")

        if all(checks.values()):
            ok = True
            if a.full:
                with open(a.full, "w") as f:
                    f.write(f"# ArenaNet-derived. VAULT ONLY -- never commit.\n"
                            f"# from {a.exe}\nroot = {root}\ngenerator = {gen}\n"
                            f"prime = {prime}\nserver_public = {pubkey}\n")
                print(f"    parameters written to {a.full}")

    print()
    if ok:
        print("GO. The static-ephemeral DH scheme is intact in this build: g = 4 over a")
        print("512-bit prime, with the server's public value compiled in. R1 proceeds as")
        print("planned, and a patched client is confirmed as a mandatory, permanent step")
        print("-- HANDOFF.md section 4's 'no binary patching' is falsified against our own")
        print("binary, not just on someone else's authority.")
        return 0
    print("FOUND BUT SHAPE DIFFERS. Reforged may have changed the parameters.")
    print("Re-plan R1 before relying on published tooling.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
