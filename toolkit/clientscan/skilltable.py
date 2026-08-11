#!/usr/bin/env python3
"""Read the client's `s_skill` table out of Gw.exe.

Python 3 standard library only, per the house rules. Read-only: it opens the
client binary, never writes to it, and never launches it.

The table is located **structurally**, not by address. Build-specific addresses
are not part of any file format and must not be carried between builds -- so we
scan every PE section at 4-byte steps for a candidate that satisfies several
independent constraints at once:

  * the u32 at row-0 offset 0x00 is 0
  * the u32 at row-0 offset 0x2c equals the record count (the table declares
    its own length in row 0, which is otherwise a linked-skill-id field)
  * row 1's offset-0x00 u32 is 1
  * row 1's description string id is exactly its name string id plus one
  * across the first 256 rows, at least 32 look live, and campaign/type/
    profession/equip codes fall in their known small ranges

That conjunction is the point: any one of those could coincide, but a false
positive would have to satisfy all of them. A check that cannot fail is not a
check.

Record layout per Fournux/Tyria-Extractor `doc/SKILL_EXTRACTION.md` -- read and
re-derived here, not copied. CLIENT-DATA: it is somebody else's reading of the
binary, and our agreement with it is one witness plus our own parse.

Output is JSON on stdout or to --out. Never write it into the repo: extracted
client values are ArenaNet's, and the provenance gate is absolute. Send it to
vault/ (gitignored).
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinned  # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory, and names the copy it returned. This module used to spell it
# `C:\gw\Gw.exe` -- the owner's live install, which auto-updates and is
# therefore not necessarily the build every address below is measured against.
find_exe = pinned.find

RECORD_SIZE = 0xA4  # 164

# Flag bits at +0x10 that we rely on.
FLAG_OVERCAST_VALID = 0x00000001
FLAG_TOUCH_RANGE    = 0x00000002
FLAG_ELITE          = 0x00000004
FLAG_HALF_RANGE     = 0x00000008
FLAG_STACKING       = 0x00010000
FLAG_NON_STACKING   = 0x00020000
FLAG_PVE_ONLY       = 0x00080000
FLAG_PVP_ONLY       = 0x00400000
FLAG_NOT_PLAYABLE   = 0x02000000


def u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]


def u16(b: bytes, off: int) -> int:
    return struct.unpack_from("<H", b, off)[0]


def f32(b: bytes, off: int) -> float:
    return struct.unpack_from("<f", b, off)[0]


# --------------------------------------------------------------------------
# minimal PE section walk
# --------------------------------------------------------------------------

def pe_sections(data: bytes) -> list[tuple[str, int, int]]:
    """Yield (name, raw_pointer, raw_size) for each section."""
    if data[:2] != b"MZ":
        raise ValueError("not an MZ image")
    e_lfanew = u32(data, 0x3C)
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise ValueError("no PE signature")
    coff = e_lfanew + 4
    n_sections = u16(data, coff + 2)
    opt_size = u16(data, coff + 16)
    table = coff + 20 + opt_size

    out = []
    for i in range(n_sections):
        h = table + i * 40
        name = data[h:h + 8].rstrip(b"\0").decode("ascii", "replace")
        raw_size = u32(data, h + 16)
        raw_ptr = u32(data, h + 20)
        out.append((name, raw_ptr, raw_size))
    return out


# --------------------------------------------------------------------------
# structural table location
# --------------------------------------------------------------------------

def probe_score(data: bytes, offset: int, count: int) -> int | None:
    if offset + count * RECORD_SIZE > len(data):
        return None
    if u32(data, offset) != 0:
        return None
    if u32(data, offset + 0x2C) != count:
        return None

    row1 = offset + RECORD_SIZE
    if u32(data, row1) != 1:
        return None
    name1 = u32(data, row1 + 0x98)
    desc1 = u32(data, row1 + 0xA0)
    if name1 == 0 or desc1 != name1 + 1:
        return None

    score = 0
    live = 0
    for i in range(1, min(count, 256)):
        rec = offset + i * RECORD_SIZE
        name_id = u32(data, rec + 0x98)
        if name_id == 0:
            continue
        if u32(data, rec + 0xA0) == name_id + 1:
            score += 4
            live += 1
        if u32(data, rec + 0x08) <= 4:
            score += 1
        if u32(data, rec + 0x0C) <= 29:
            score += 1
        if data[rec + 0x28] <= 10:
            score += 1
        if data[rec + 0x33] <= 3:
            score += 1

    if live < 32:
        return None
    return score


def locate_table(data: bytes) -> tuple[int, int, int]:
    """Return (file_offset, record_count, score) of the best candidate."""
    best = None
    for _name, raw_ptr, raw_size in pe_sections(data):
        start = raw_ptr
        end = min(raw_ptr + raw_size, len(data))
        if end <= start + RECORD_SIZE * 2:
            continue
        off = start
        while off + RECORD_SIZE * 2 <= end:
            try:
                count = u32(data, off + 0x2C)
            except struct.error:
                break
            if 512 <= count <= 10000 and off + count * RECORD_SIZE <= end:
                s = probe_score(data, off, count)
                if s is not None and (best is None or s > best[2]):
                    best = (off, count, s)
            off += 4
    if best is None:
        raise RuntimeError("failed to locate s_skill table structurally")
    return best


# --------------------------------------------------------------------------
# record decoding
# --------------------------------------------------------------------------

def decode_energy(raw: int) -> int:
    """Encoded energy byte at +0x35: 11 means 15, 12 means 25, else literal."""
    return {11: 15, 12: 25}.get(raw, raw)


def displayed_adrenaline(units: int) -> int:
    """Strikes the client shows for a raw unit total.

    ceil(units/25): gain is a flat 25 units per hit, so the displayed cost is
    the number of hits needed. See studies/skills/FINDINGS.md.
    """
    return math.ceil(units / 25) if units else 0


def parse_record(data: bytes, base: int, skill_id: int) -> dict:
    # `base` is the TABLE base from locate_table(), not the row's offset -- the
    # row arithmetic happens here. Passing an already-advanced offset reads at
    # base + 2*skill_id*RECORD_SIZE, which decodes cleanly for the first half of
    # the table and then walks off the end into whatever follows it, so the
    # damage shows up as "the tail of the table is garbage" rather than as an
    # error. Ask how a bad row index compares to count/2 before believing it.
    r = base + skill_id * RECORD_SIZE
    flags = u32(data, r + 0x10)
    units = u32(data, r + 0x38)
    energy_raw = data[r + 0x35]
    return {
        "id": skill_id,
        "campaign": u32(data, r + 0x08),
        "type_code": u32(data, r + 0x0C),
        "flags": flags,
        "elite": bool(flags & FLAG_ELITE),
        "pve_only": bool(flags & FLAG_PVE_ONLY),
        "pvp_only": bool(flags & FLAG_PVP_ONLY),
        "not_playable": bool(flags & FLAG_NOT_PLAYABLE),
        "profession": data[r + 0x28],
        "attribute": data[r + 0x29],
        "title_track": u16(data, r + 0x2A),
        "linked_id": u32(data, r + 0x2C),
        "combo": data[r + 0x30],
        "target": data[r + 0x31],
        "equip_family": data[r + 0x33],
        "overcast": data[r + 0x34] if flags & FLAG_OVERCAST_VALID else 0,
        "energy_raw": energy_raw,
        "energy": decode_energy(energy_raw),
        "health_cost": data[r + 0x36],
        "adrenaline_units": units,
        "adrenaline": displayed_adrenaline(units),
        "activation": round(f32(data, r + 0x3C), 4),
        "aftercast": round(f32(data, r + 0x40), 4),
        "recharge": u32(data, r + 0x4C),
        "name_id": u32(data, r + 0x98),
        "concise_id": u32(data, r + 0x9C),
        "description_id": u32(data, r + 0xA0),
    }


def player_corpus(rows: list[dict]) -> list[int]:
    """Ids that make up the player-usable skill corpus.

    Per SKILL_EXTRACTION.md section 4: equip/use-family 1 with the PvP flag
    clear. The table is broader than the skill corpus -- it also holds weapon
    modifiers and other non-player definitions -- so a nonzero name id is not
    membership.
    """
    return [r["id"] for r in rows
            if r["equip_family"] == 1 and not r["pvp_only"]]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", default=None,
                   help="client binary to read (read-only); defaults to the "
                        "pinned pristine build")
    p.add_argument("--out", help="write JSON here (keep it out of the repo)")
    p.add_argument("--summary", action="store_true",
                   help="print a summary instead of the full dump")
    a = p.parse_args(argv)
    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    print(f"client: {a.exe}\n        ({why})\n", file=sys.stderr)

    data = Path(a.exe).read_bytes()
    base, count, score = locate_table(data)
    rows = [parse_record(data, base, i) for i in range(count)]
    corpus = player_corpus(rows)

    meta = {
        "exe": str(a.exe),
        "exe_bytes": len(data),
        "table_file_offset": base,
        "record_count": count,
        "detection_score": score,
        "player_corpus_size": len(corpus),
    }

    if a.summary:
        for k, v in meta.items():
            print(f"{k}: {v}")
        return 0

    payload = {"meta": meta, "corpus_ids": corpus, "skills": rows}
    text = json.dumps(payload, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}: {count} rows, {len(corpus)} in corpus", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
