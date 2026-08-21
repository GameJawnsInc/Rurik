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
        # The rank-0/rank-15 scaling window +0x44..+0x68, all u32 (dwords).
        # OBSERVED to reproduce studies/skills/FINDINGS.md section 4's 4-skill
        # anecdote byte-exact (318/322/316/319 -- test_skilltable section 7).
        # skill_arguments is a bitfield: 1 = duration set, 2 = scale set,
        # 4 = bonus-scale set (GWCA's Skill.h comment). A value renders green
        # when its set is enabled AND its two endpoints differ; both are
        # needed, which is why the endpoints are carried rather than a
        # single "scales?" flag. +0x50 (h0050) stays named-unknown -- neither
        # upstream source names it and nothing here resolves it (NOT FOUND).
        "duration0": u32(data, r + 0x44),
        "duration15": u32(data, r + 0x48),
        "recharge": u32(data, r + 0x4C),
        "skill_arguments": u32(data, r + 0x58),
        "scale0": u32(data, r + 0x5C),
        "scale15": u32(data, r + 0x60),
        "bonus_scale0": u32(data, r + 0x64),
        "bonus_scale15": u32(data, r + 0x68),
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


def build_of(data: bytes):
    """The build number of this exact image, from its own bytes, or None.

    The emitter stamps every content row with a `build`, and a stamp nothing
    checks is an unfalsifiable self-declaration (toolkit/test_origin.py learned
    this the hard way one layer up). So the number is derived by hashing the
    image against `pinned.BUILDS`' PRISTINE hashes -- a patched copy or an
    unknown build gets None, and the emitter refuses rather than guessing,
    because a row stamped with the wrong build survives every later audit.
    """
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    for b in pinned.BUILDS:
        if digest == b.pristine:
            return b.number
    return None


# The row fields the server consumes, in emit order. Everything here is a
# MEASUREMENT (a number read out of the owner's own client) carried with
# per-row provenance -- the boundary CLAUDE.md's gate draws. The scaling
# window (skill_arguments + the four endpoint pairs) is what step 8 will scale
# damage BY once a rank exists; it is emitted now so the capture run has the
# endpoints to bind against, but nothing consumes it until then.
#
# `type_code` and `target` were added 2026-08-20, for the effect substrate.
# Without them the server cannot DISPATCH: a stance, a hex and an enchantment
# are three different things done with the same message, and the id alone does
# not say which. Both are raw enums ArenaNet never named -- what the server may
# rely on is only what the table itself corroborates:
#   * `type_code` -- `studies/presearing/MANIFEST.md` 8 decoded 10 of the 21
#     player values by Rosetta-stone against skills whose wiki type was known.
#   * `target` -- 0 is SELF and 5 is the cast's target, and the type column is
#     the witness: all 199 Attacks are 5, 75 of 76 Stances are 0, and every
#     Glyph, Preparation and type-16 skill is 0. Codes 1, 3, 4, 6, 14 and 16
#     are NOT resolved here and nothing reads them.
#
# `adrenaline_units` was added 2026-08-20, alongside the existing `adrenaline`
# (the ceil(units/25) DISPLAYED strike count). The server-side mechanic needs
# the raw unit total, not the display: Battle Rage (skill 317; OBSERVED here,
# name resolved via textrec against this same build) charges at 80 raw units
# per +0x38, which ceil(80/25) displays as 4 strikes -- WIKI, GWW "Battle
# Rage" Notes, "exactly requires 80 units", checked 2026-08-20. `parse_record()`
# already decodes the raw total at +0x38 as `adrenaline_units`; this only adds
# it to the emitted set.
CONTENT_FIELDS = ("activation", "aftercast", "recharge",
                  "energy", "adrenaline", "adrenaline_units",
                  "attribute", "profession",
                  "type_code", "target",
                  "skill_arguments", "duration0", "duration15",
                  "scale0", "scale15", "bonus_scale0", "bonus_scale15")


def emit_content(rows, ids, build, exe, out_path) -> int:
    """Write vault/content/skills.toml: the per-skill numbers the server reads.

    One `[skills.<id>]` table per corpus skill, each carrying its own
    `client-table` provenance (extractor named, build recorded -- the two
    conditions `toolkit/content.py` enforces and `test_content.py` proves the
    refusals of). The float fields are formatted with repr(), which for the
    table's f32-derived values round-trips exactly through tomllib.
    """
    keep = {r["id"]: r for r in rows}
    lines = [
        "# GENERATED -- do not hand-edit. toolkit/clientscan/skilltable.py "
        "--emit-content",
        f"# exe: {exe}",
        f"# build: {build} (derived from the image's own sha256 via "
        f"clientscan/pinned.py, never typed in)",
        f"# rows: {len(ids)} (the player-usable corpus: equip_family 1, "
        f"PvP-only excluded)",
        "# Loaded by toolkit/content.py as kind 'skills', merged over the "
        "repo's content/*.toml.",
        "",
    ]
    for skill_id in sorted(ids):
        r = keep[skill_id]
        lines.append(f"[skills.{skill_id}]")
        for f in CONTENT_FIELDS:
            v = r[f]
            lines.append(f"{f} = {v!r}" if isinstance(v, float)
                         else f"{f} = {int(v)}")
        lines.append(f"[skills.{skill_id}.provenance]")
        lines.append('source = "client-table"')
        lines.append('extractor = "toolkit/clientscan/skilltable.py"')
        lines.append(f"build = {build}")
        lines.append("")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return len(ids)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", default=None,
                   help="client binary to read (read-only); defaults to the "
                        "pinned pristine build")
    p.add_argument("--out", help="write JSON here (keep it out of the repo)")
    p.add_argument("--summary", action="store_true",
                   help="print a summary instead of the full dump")
    p.add_argument("--emit-content", metavar="PATH",
                   help="write the server's per-skill content rows (TOML) "
                        "here -- vault/content/skills.toml is the intended "
                        "home. Refuses an exe whose bytes match no pristine "
                        "build in clientscan/pinned.py, because every row is "
                        "stamped with the build it was read from.")
    a = p.parse_args(argv)
    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    print(f"client: {a.exe}\n        ({why})\n", file=sys.stderr)

    data = Path(a.exe).read_bytes()
    base, count, score = locate_table(data)
    rows = [parse_record(data, base, i) for i in range(count)]
    corpus = player_corpus(rows)

    if a.emit_content:
        build = build_of(data)
        if build is None:
            print("REFUSED: this exe's sha256 matches no PRISTINE build in "
                  "clientscan/pinned.py, so no honest `build` stamp exists "
                  "for the rows. Point --exe at a pristine snapshot.",
                  file=sys.stderr)
            return 2
        n = emit_content(rows, corpus, build, a.exe, a.emit_content)
        print(f"wrote {a.emit_content}: {n} skill rows, build {build}",
              file=sys.stderr)
        return 0

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
