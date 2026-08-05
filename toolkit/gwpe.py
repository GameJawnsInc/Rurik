"""Minimal PE reader for the 32-bit Guild Wars client.

Deliberately dependency-free. `pefile` would do this too, but the client tools in
this repo are the ones the owner runs on a fresh machine at 2am after an ArenaNet
update breaks something, and every pip install between them and an answer is a
reason the check does not get run.

Only what the client tools actually need: section table, RVA to file offset, and
signature search. Not a general PE library.
"""

import struct

MACHINE_NAMES = {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64"}


class PE:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        if d[:2] != b"MZ":
            raise ValueError(f"{path}: not a PE file")
        e = struct.unpack_from("<I", d, 0x3C)[0]
        if d[e:e + 4] != b"PE\0\0":
            raise ValueError(f"{path}: bad PE signature")
        self.machine = struct.unpack_from("<H", d, e + 4)[0]
        nsec = struct.unpack_from("<H", d, e + 6)[0]
        self.timestamp = struct.unpack_from("<I", d, e + 8)[0]
        opt_size = struct.unpack_from("<H", d, e + 20)[0]
        magic = struct.unpack_from("<H", d, e + 24)[0]
        if magic != 0x10B:
            raise ValueError(f"{path}: expected PE32 (32-bit); got magic 0x{magic:x}")
        self.image_base = struct.unpack_from("<I", d, e + 52)[0]
        sec_off = e + 24 + opt_size
        self.sections = []
        for i in range(nsec):
            o = sec_off + i * 40
            self.sections.append({
                "name": d[o:o + 8].rstrip(b"\0").decode("ascii", "replace"),
                "vsize": struct.unpack_from("<I", d, o + 8)[0],
                "vaddr": struct.unpack_from("<I", d, o + 12)[0],
                "rawsize": struct.unpack_from("<I", d, o + 16)[0],
                "rawptr": struct.unpack_from("<I", d, o + 20)[0],
            })

    @property
    def arch(self):
        return MACHINE_NAMES.get(self.machine, f"0x{self.machine:x}")

    def section(self, name):
        for s in self.sections:
            if s["name"] == name:
                return s
        return None

    def section_of_rva(self, rva):
        for s in self.sections:
            if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
                return s
        return None

    def rva_to_off(self, rva):
        s = self.section_of_rva(rva)
        if not s:
            return None
        delta = rva - s["vaddr"]
        # Inside virtual padding: addressable at runtime, not backed by file bytes.
        # Returning a plausible-looking offset here would silently corrupt a patch.
        if delta >= s["rawsize"]:
            return None
        return s["rawptr"] + delta

    def find(self, needle, section=None):
        """Every file offset where `needle` occurs, optionally within one section."""
        if section:
            s = self.section(section)
            if not s:
                return []
            lo, hi = s["rawptr"], s["rawptr"] + s["rawsize"]
        else:
            lo, hi = 0, len(self.data)
        out, i = [], self.data.find(needle, lo, hi)
        while i != -1:
            out.append(i)
            i = self.data.find(needle, i + 1, hi)
        return out

    def off_to_rva(self, off):
        for s in self.sections:
            if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
                return s["vaddr"] + (off - s["rawptr"])
        return None
