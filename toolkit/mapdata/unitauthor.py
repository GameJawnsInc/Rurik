"""Add an animation to a creature: a 16th linked file, and a sequence that names it.

Rung A4 of [studies/archivewrite/PLAN via FINDINGS.md §3]. This module builds the
edit; it does not apply it to any real archive and it launches nothing.

WHY THIS SHAPE AND NOT THE OBVIOUS ONE. The obvious plan, and the one the
unit-model arc carried until 2026-08-17, was to rewrite the file that holds the
animations -- for the hatcher that is file 15018, 1,514,855 B decompressed,
which cannot be written back because we have no compression-8 encoder. A1's
blind replication killed that plan and replaced it with a much smaller one:

  * The sequence index space is PER-FILE, not global (`MdlSeq:300`
    `seqIndex < m_skel->m_seqCount`; the key lookup is a `lower_bound` over ONE
    file's array with no fall-through to links).
  * A sequence record's disk `u8@+0x00` is a 1-BASED index into the model's FA8
    link array -- 0 means "this file". `links[sel-1]` scores 31,700/0 across all
    252 FA8 shells, against a 0-based rival at 0.82%.
  * So a linked file is only reachable through a sequence record IN THE SHELL
    that names it. Adding a link alone is inert -- and *safe*, because retail
    itself ships 410 unselected links across 63 shells.

Therefore the file we must rewrite is the SHELL, and for the hatcher the shell
is 29,802 B in a 20,480 B reservation -- the same file U7 already rewrote and
put on screen. Retail's 1 MB link is never touched. The wall is not on this path.

THE ORACLE THIS BUYS, and it is why the sequence carries an EXISTING key.
`0x00804240` is not a lookup, it is a variant PICKER: it resolves a key to a run
of equal-key records and returns `start + rand() % count` when the caller passes
selector 0, which `AvChar:8212`'s call site does (`push 0` at `0x007FD5DB`).
Measured on the hatcher's shell: 242 records over 224 keys, run sizes
`{1: 216, 2: 4, 3: 1, 4: 1, 5: 1, 6: 1}`. So appending one record on a
single-variant key makes the client flip a coin between retail's animation and
ours on every play. That is a self-controlling client-run oracle -- the failure
mode "nothing happened" and the success mode "it changed half the time" are
distinguishable by eye, and no invented key and no wire question are involved.

THE HARD CONSTRAINT, and it falls straight out of the same disassembly. The
sequence array is searched with `std::lower_bound` (`0x00792DC0`), which is only
correct on a sorted array -- MEASURED, 3,000/3,000 files and 40,226 sequences are
non-decreasing in `u32@+0x01`. A record is therefore INSERTED IN KEY ORDER, never
appended. A tail append with a low key silently breaks the search for every key
after it, and nothing we own would report it: the file still decodes, every
checksum still holds, and the creature simply stops playing some animations.
`insert_sequence` refuses to append out of order rather than trusting a caller.

    python toolkit/mapdata/unitauthor.py --shell 116228 --plan
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mdlrefs                                                    # noqa: E402
import skelfile                                                   # noqa: E402
import skelwrite                                                  # noqa: E402
from archive import ffna_chunks, FFNA_MAGIC                       # noqa: E402
from mapchunks import dependency_pair, dependency_file_id         # noqa: E402

LINK_CHUNK = 0xFA8
SKELETON_CHUNK = skelfile.SKELETON_CHUNK

# A sequence record's key-table span is a BYTE pair at +0x0D/+0x0E, so a span
# endpoint cannot exceed 255 whatever the key table's real length is. Checked
# rather than assumed: `skelwrite.encode` packs them with `rec[0x0D] = lo`,
# which would raise on 256 anyway, but a refusal that names the reason is worth
# more at the call site than a ValueError out of a struct pack.
SPAN_MAX = 0xFF


class Unauthorable(ValueError):
    """The edit cannot be made. Never a silent fallback."""


def _need(cond, what):
    if not cond:
        raise Unauthorable(what)


# --------------------------------------------------------------- the FA8 --

def links_of(container):
    """The file ids this container's FA8 chunk names, in record order.

    Order IS the selector: `links[sel-1]`. A caller that reorders this list has
    changed which file every existing sequence record points at.
    """
    for cid, off, size in ffna_chunks(container):
        if cid == LINK_CHUNK:
            recs = mdlrefs.decode_records(bytes(container[off:off + size]))
            return [mdlrefs.record_file_id(r) for r in recs]
    return []


def encode_records(records):
    """The inverse of `mdlrefs.decode_records`: u32 count, then null-terminated
    u16 records. Round-tripped against the corpus by the test, not asserted."""
    out = bytearray(struct.pack("<I", len(records)))
    for rec in records:
        for w in rec:
            _need(w != 0, "a zero word inside a record would terminate it early")
            out += struct.pack("<H", w)
        out += b"\x00\x00"
    return bytes(out)


def add_link(container, file_id):
    """Append `file_id` to the FA8 list. Returns (new_container, selector).

    The selector is 1-based and is what a sequence record must carry to reach
    the new file. Appending is correct here and inserting would not be: the FA8
    list is positional, so putting a record anywhere but the end would renumber
    every selector already in use.
    """
    chunks = list(ffna_chunks(container))
    fa8 = [c for c in chunks if c[0] == LINK_CHUNK]
    _need(fa8, "this container has no 0xFA8 chunk to add a link to")
    _need(len(fa8) == 1, f"{len(fa8)} FA8 chunks; ambiguous")
    _cid, off, size = fa8[0]

    payload = bytes(container[off:off + size])
    records = mdlrefs.decode_records(payload)
    _need(encode_records(records) == payload,
          "the FA8 chunk does not re-encode to its own bytes; refusing to "
          "rewrite a chunk this module cannot reproduce")

    id0, id1 = dependency_pair(file_id)
    _need(dependency_file_id(id0, id1) == file_id,
          f"the dependency pair for {file_id} does not round-trip")
    new_records = records + [(id0, id1)]
    new_payload = encode_records(new_records)

    out = bytearray(FFNA_MAGIC)
    out.append(container[4])
    for cid, coff, csize in chunks:
        body = (new_payload if cid == LINK_CHUNK
                else bytes(container[coff:coff + csize]))
        out += struct.pack("<II", cid, len(body))
        out += body
    return bytes(out), len(new_records)


# ---------------------------------------------------------- the sequence --

def key_runs(t):
    """key -> number of records carrying it, in table order."""
    runs = {}
    for s in t["sequences"]:
        runs[s["u32_01"]] = runs.get(s["u32_01"], 0) + 1
    return runs


def single_variant_keys(t):
    """Keys with exactly one record. Appending a variant to one of these is
    what turns the client's own random picker into a 50/50 A/B oracle."""
    return [k for k, n in sorted(key_runs(t).items()) if n == 1]


def insert_sequence(t, key, selector, template=None):
    """Insert one sequence record carrying `key` and `selector`, IN KEY ORDER.

    Returns the index it landed at. `template` is the record whose playback
    fields are copied -- by default the first existing record with the same key,
    which is what makes the new record a genuine VARIANT of that animation
    rather than an arbitrary one.

    Refuses rather than repairs: an out-of-order insert, a span endpoint past a
    byte, or a header whose n18 no longer matches all raise. The array is
    `lower_bound`-searched and a silently unsorted table does not fail anything
    we own -- it just stops the creature playing some of its animations.
    """
    seqs = t["sequences"]
    _need(t["header"]["n18"] == len(seqs),
          f"header n18 {t['header']['n18']} != {len(seqs)} records before the "
          f"insert; the representation is already inconsistent")
    _need(0 <= selector <= 0xFF, f"selector {selector} is not a byte")

    if template is None:
        same = [s for s in seqs if s["u32_01"] == key]
        _need(same, f"no existing record carries key {key} and no template was "
                    f"given -- refusing to invent playback fields")
        template = same[0]

    rec = dict(template)
    rec["u32_01"] = key
    rec["u8_00"] = selector
    for a, b in (("start", "u32_05"), ("end", "u32_09")):
        rec[a] = rec[b]                      # keep encode()'s alias check happy
    _need(rec["lo"] <= SPAN_MAX and rec["hi"] <= SPAN_MAX,
          f"key span ({rec['lo']},{rec['hi']}) does not fit the byte pair at "
          f"+0x0D/+0x0E")

    # lower_bound semantics: the new record joins the END of its equal-key run,
    # which is the first index whose key is strictly greater.
    at = len(seqs)
    for i, s in enumerate(seqs):
        if s["u32_01"] > key:
            at = i
            break
    seqs.insert(at, rec)
    t["header"]["n18"] = len(seqs)

    keys = [s["u32_01"] for s in seqs]
    _need(all(b >= a for a, b in zip(keys, keys[1:])),
          "the insert left the sequence array unsorted -- lower_bound would be "
          "wrong and nothing we own would report it")
    return at


# ------------------------------------------------------------- the whole --

def author_variant(container, new_file_id, key=None):
    """Add a link to `new_file_id` and one sequence record that selects it.

    Returns (new_container, info). Does not touch any archive.
    """
    fa1 = None
    for cid, off, size in ffna_chunks(container):
        if cid == SKELETON_CHUNK:
            fa1 = bytes(container[off:off + size])
            break
    _need(fa1 is not None, "no 0xFA1 chunk: this container carries no skeleton")

    t = skelwrite.extract(skelfile.Skeleton.decode(fa1))
    _need(skelwrite.encode(t) == fa1,
          "the FA1 does not round-trip byte-identically; refusing to modify a "
          "file this module cannot reproduce unchanged")

    if key is None:
        singles = single_variant_keys(t)
        _need(singles, "no single-variant key to attach a variant to")
        key = singles[0]
    before_run = key_runs(t).get(key, 0)

    linked, selector = add_link(container, new_file_id)
    at = insert_sequence(t, key, selector)
    out = skelwrite.rebuild_container(linked, skelwrite.encode(t))

    return out, {
        "file_id": new_file_id,
        "selector": selector,
        "key": key,
        "index": at,
        "links_before": selector - 1,
        "sequences_before": len(t["sequences"]) - 1,
        "run_before": before_run,
        "run_after": before_run + 1,
        "container_before": len(container),
        "container_after": len(out),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shell", type=int, default=116228,
                    help="file id of the COMPOSITED shell to author into")
    ap.add_argument("--new-file-id", type=int, default=0x5F200,
                    help="the file id the 16th link will name")
    ap.add_argument("--key", type=int, default=None)
    ap.add_argument("--plan", action="store_true",
                    help="read-only: report the edit without writing anything")
    args = ap.parse_args(argv)

    import archive as arch
    ar = arch.Archive()
    try:
        row = arch.file_id_table(ar, raw=True)[args.shell]
        container = ar.read(ar.row(row))
    finally:
        ar.close()

    out, info = author_variant(container, args.new_file_id, args.key)
    print(f"shell {args.shell} (row {row})")
    print(f"  links {info['links_before']} -> {info['selector']}, "
          f"new file id {info['file_id']} at selector {info['selector']}")
    print(f"  sequences {info['sequences_before']} -> "
          f"{info['sequences_before'] + 1}, inserted at index {info['index']}")
    print(f"  key {info['key']}: {info['run_before']} variant(s) -> "
          f"{info['run_after']} -- the client picks uniformly among them, so "
          f"this is a 1-in-{info['run_after']} chance per play")
    print(f"  container {info['container_before']} -> {info['container_after']} B "
          f"({info['container_after'] - info['container_before']:+d})")
    print("\nNOTHING WAS WRITTEN. This is a plan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
