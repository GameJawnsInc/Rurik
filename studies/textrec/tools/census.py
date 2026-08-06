#!/usr/bin/env python3
"""Dump the text-record census to the vault. Never into the repo.

    python studies/textrec/tools/census.py

Writes vault/textrec/census-<build>.json: per-language symbol-width histograms,
the escape table read out of the image, and the plain/encrypted slot split.
These are extracted client values, so they are gitignored vault contents and
the provenance gate keeps them there. The study doc cites aggregates only.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("toolkit", "toolkit/mapdata", "toolkit/clientscan", "toolkit/authsrv"):
    sys.path.insert(0, str(ROOT / p))
import textrec                                  # noqa: E402
from vaultpath import vault_path                # noqa: E402

LANGUAGES = {0: "English", 1: "Korean", 2: "French", 3: "German",
             4: "Italian", 5: "Spanish", 6: "Chinese-T", 7: "Chinese-S",
             8: "Japanese", 9: "Polish", 10: "English-2"}


def main():
    out = {"exe": textrec.DEFAULT_EXE, "languages": {}}
    plain_slots = None
    for lang, name in LANGUAGES.items():
        with textrec.TextIndex(textrec.DEFAULT_EXE, language=lang) as ix:
            if plain_slots is None:
                out["escape_table"] = ix.escape
            widths, slots = {}, set()
            for fi in range(textrec.FILES_PER_LANGUAGE):
                for ri, (bits, base, _p) in enumerate(ix.records(fi)):
                    widths[bits] = widths.get(bits, 0) + 1
                    if textrec.is_plain(bits, base):
                        slots.add((fi, ri))
            same = None if plain_slots is None else (slots == plain_slots)
            plain_slots = slots if plain_slots is None else plain_slots
            out["languages"][name] = {
                "index": lang,
                "widths": {str(k): v for k, v in sorted(widths.items())},
                "plain": len(slots),
                "plain_slots_match_english": same,
            }
            print(f"  {name:11} plain {len(slots):6}  widths "
                  f"{sorted(widths.items())}")
    dest = Path(vault_path("textrec"))
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "census-38797.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
