"""The post-flight half -- take a snapshot, diff two of them, and say what
changed in the client's own terms.

`datcheck.py` asks whether a copy is one the client will open without repairing
it; this module answers the other half, what the client changed while it had it.
Nothing here opens an archive for writing and nothing here is a `Check`: `scan`
reads every raw structure once, `snapshot` stamps the three tiers, `classify_row`
and `diff` compare two of them, and `format_diff` is the page an operator
actually reads. `datcheck.py` re-exports every name below, so
`datcheck.write_snapshot`, `datcheck.load_snapshot`, `datcheck.diff`,
`datcheck.format_diff` and the seven diff kinds still resolve for `overlay.py`,
`test_overlay.py` and `test_datcheck.py`, which read them off that module.

POINTERS FOR THE COMMENTS BELOW, whose referents stayed in `datcheck.py` and
which are reproduced here word for word rather than reworded. `diff`'s docstring
names `_main` as the caller that never passes `after` -- `_main` and the whole
CLI are still there, and so is the paragraph recording that the `--diff` layout
changed on 2026-08-13 and that the old output is no longer line-comparable with
a re-run. The row numbers every verb here prints are in `ROW_CONVENTION`'s
convention, the raw MFT index, which `datread.py`'s docstring is now the place
that explains; both verbs print it above their numbers.

WHAT THE SNAPSHOT HOLDS (FINDINGS 18.5):

  Tier 0, 48 bytes           `header[0x10:0x20]` (mftOffset u64, mftSize u32,
                             flags u32) and the MFT descriptor's u32 at +0x04.
                             **Read the header FIRST** -- the MFT itself moves,
                             so a snapshot that seeks to a remembered offset
                             reads the wrong table. That counter is the part
                             carrying the signal; `mftOffset` alone is not a
                             change signal (it was byte-identical across 159
                             flushes in one diffed pair).

  Tier 1                     All 24 bytes of every MFT row. Stored whole, zlib'd
                             and base64'd, because the classification in
                             `diff()` needs the bytes and not a digest.

  Tier 2                     The directory invariant's result, plus a digest of
                             the file-id table -- the only check that catches a
                             reconcile-triggered delete, and the one thing the
                             client ENFORCES rather than repairs past.

`test_datcheck.py` builds a synthetic archive, changes one row at a time and
checks both the classification and the page this module prints. It never touches
a real one.
"""

import base64
import hashlib
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import (ENTRY_SIZE, row_label,  # noqa: E402
                     FILE_ID_TABLE_ROW, MFT_SELF_ROW)
from datread import (ROW_CONVENTION, DESCRIPTOR_COUNTER_OFF,  # noqa: E402
                     DESCRIPTOR_COUNT_OFF, read_header, read_mft, row_bytes,
                     row_fields, row_count, file_id_records,
                     directory_invariant, row_identity, label_row)

SNAPSHOT_VERSION = 1


# ----------------------------------------------------------------- snapshot --

def scan(path):
    """(header, mft, records, id_blob) -- every raw structure, read ONCE.

    Extracted 2026-08-14 because `diff()` needs the file-id RECORDS to label its
    rows and `snapshot()` had already parsed them in the same call.

    WHAT LABELLING COSTS, MEASURED on `vault/dat_study/Gw.dat` (4.2 GB, 177,342
    rows), best of two runs each, `tracemalloc` peak:

        1.51 s /  36.9 MB   no labels at all (the pre-2026-08-13 diff)
        3.77 s / 117.3 MB   labels, re-reading and re-parsing the id table
        3.06 s / 121.4 MB   labels, sharing this one scan

    So the duplicate read was ~0.7 s of the 2.3 s and this removes it. The rest
    is `row_identity` itself, and the memory is nearly all of it: a dict of
    177,342 dicts. Both are RECORDED rather than optimised away, because `--diff`
    is the verb run around a timed client session and the next person to wonder
    should find a number instead of a shrug. Making the identity map lazy would
    buy the memory back and is not worth doing until something needs it.
    """
    header = read_header(path)
    mft = read_mft(path, header)
    records, id_blob = file_id_records(path, mft, header)
    return header, mft, records, id_blob


def snapshot(path, scanned=None):
    """Tier 0 + Tier 1 + Tier 2, with the header read before the MFT.

    `scanned` is a `scan()` result a caller already paid for. It is never a
    DIFFERENT archive's -- `diff()` is the only caller that passes one and it
    passes the one it just took from `path`.
    """
    header, mft, records, id_blob = scanned if scanned else scan(path)
    inv = directory_invariant(mft, records)
    desc = row_bytes(mft, 0)
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "dat": os.path.abspath(path),
        "size_on_disk": os.path.getsize(path),
        "tier0": {
            "header_0x10_0x20": header["tier0"].hex(),
            "mft_offset": header["mft_offset"],
            "mft_size": header["mft_size"],
            "header_flags_0x1C": header["mod_flags"],
            "descriptor_counter": struct.unpack_from(
                "<I", desc, DESCRIPTOR_COUNTER_OFF)[0],
            "descriptor_count": struct.unpack_from(
                "<I", desc, DESCRIPTOR_COUNT_OFF)[0],
        },
        "tier1": {
            "rows": row_count(mft),
            "encoding": "zlib+base64",
            "mft": base64.b64encode(zlib.compress(mft, 6)).decode("ascii"),
            "mft_sha256": hashlib.sha256(mft).hexdigest(),
        },
        "tier2": {
            "records": inv["records"],
            "released_records": inv["released_records"],
            "first_stream_rows": inv["first_stream_rows"],
            "rows_named": inv["rows_named"],
            "orphan_rows": inv["orphan_rows"][:64],
            "orphan_count": len(inv["orphan_rows"]),
            "dangling_count": len(inv["dangling_records"]),
            "file_id_sha256": hashlib.sha256(id_blob).hexdigest(),
        },
    }


def write_snapshot(path, out_path):
    snap = snapshot(path)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1)
    return snap


def load_snapshot(out_path):
    with open(out_path, "r", encoding="utf-8") as fh:
        snap = json.load(fh)
    if snap.get("snapshot_version") != SNAPSHOT_VERSION:
        raise ValueError("snapshot version %r; this tool writes %d"
                         % (snap.get("snapshot_version"), SNAPSHOT_VERSION))
    return snap


def _snapshot_mft(snap):
    mft = zlib.decompress(base64.b64decode(snap["tier1"]["mft"]))
    if hashlib.sha256(mft).hexdigest() != snap["tier1"]["mft_sha256"]:
        raise ValueError("snapshot MFT does not match its own digest")
    return mft


# --------------------------------------------------------------------- diff --

RELOCATED = "new extent (silent relocation)"
RECYCLED = "row recycled"
DELETED = "deleted"
RELINKED = "sibling relinked"
UNCLASSIFIED = "changed, unclassified"
ADDED = "row added"
REMOVED = "row removed"

_ZERO_ROW = b"\x00" * ENTRY_SIZE
CORROBORATION_ROWS = (0, FILE_ID_TABLE_ROW, MFT_SELF_ROW)


def classify_row(before, after):
    """FINDINGS 18.5's Tier 1 table, in the order the shapes exclude each other.

    Never returns None for a changed row. A shape the table does not name is
    `UNCLASSIFIED` and is reported -- dropping it is how a relocation gets
    called a no-op.
    """
    if before == after:
        return None
    if after == _ZERO_ROW:
        return DELETED
    identity_changed = before[0x0E:0x10] != after[0x0E:0x10]
    if identity_changed:
        return RECYCLED
    link_changed = before[0x10:0x14] != after[0x10:0x14]
    extent_changed = (before[0x00:0x0E] != after[0x00:0x0E]
                      or before[0x14:0x18] != after[0x14:0x18])
    if link_changed and not extent_changed:
        return RELINKED
    if extent_changed and not link_changed:
        return RELOCATED
    return UNCLASSIFIED


def diff(before, path=None, after=None):
    """Compare a live archive (or a second snapshot) against a snapshot.

    Returns a dict. `changes` is one record per changed row, classified; rows 0,
    2 and 3 change on any flush and are separated out as corroboration rather
    than counted as findings.

    Every changed row is labelled by `row_identity` when `path` is given -- read
    from the LIVE archive rather than from the snapshot, because a snapshot
    carries only a digest of the file-id table and not its pairs. Comparing two
    snapshots is still allowed and still works; it reports `identified: False`
    and the formatter says so, rather than printing a row number that looks
    identified and is not.

    AND THE LABELS ARE GATED ON THE ARCHIVE BEING THE ONE `after` DESCRIBES.
    The sentence above was false for one parameter combination when it was
    written: `diff(before, path=X, after=<snapshot of Y>)` took its ROWS from Y
    and its IDENTITY from X and reported `identified: True`. MEASURED 2026-08-14
    with X = `vault/dat_study` and Y = `vault/client/2026-04-30_b174de1f2d8d`:
    **308 of 315 changed rows carried a label naming a file the after-image does
    not hold** -- row 3721 labelled `file id 0x5EE9A, 0x2D459` where the
    after-image's own table says `0x2D451, 0x5E503`. Guarded, the same call now
    reports `identified: False` and 0 labels carry a file id at all.
    No shipped caller reaches it -- `_main` never passes `after` -- which
    is exactly why it survived review: it is a latent trap in a public function,
    and it is the precise failure `row_label`'s own docstring exists to prevent.
    The gate is the MFT ITSELF, byte for byte, not a comparison of path strings:
    a stale snapshot of the very same path is the same defect wearing the right
    name, and the archive is the only thing that can refute it.
    """
    scanned = None
    if after is None:
        scanned = scan(path)
        after = snapshot(path, scanned)
    b_mft = _snapshot_mft(before)
    a_mft = _snapshot_mft(after)
    nb, na = row_count(b_mft), row_count(a_mft)

    identity = None
    identity_note = None
    if path is not None:
        if scanned is None:
            scanned = scan(path)
        _hdr, live_mft, records, _blob = scanned
        if bytes(live_mft) == bytes(a_mft):
            identity = row_identity(live_mft, records)
        else:
            identity_note = (
                "the archive at %s is NOT the one `after` describes -- its MFT "
                "differs (%d rows on disk, %d in the snapshot) -- so no row "
                "below carries a file id or a role. Labelling from the wrong "
                "archive is worse than a bare number: it reads as "
                "identification." % (path, row_count(live_mft), na))

    tier0 = {}
    for key in ("mft_offset", "mft_size", "header_flags_0x1C",
                "descriptor_counter", "descriptor_count"):
        bv, av = before["tier0"][key], after["tier0"][key]
        if bv != av:
            tier0[key] = {"before": bv, "after": av}

    changes, corroboration = [], []
    for i in range(min(nb, na)):
        rb, ra = row_bytes(b_mft, i), row_bytes(a_mft, i)
        kind = classify_row(rb, ra)
        if kind is None:
            continue
        rec = {"row": i, "kind": kind, "label": label_row(identity, i),
               "before": row_fields(rb), "after": row_fields(ra),
               "before_hex": rb.hex(), "after_hex": ra.hex()}
        (corroboration if i in CORROBORATION_ROWS else changes).append(rec)
    for i in range(na, nb):
        # A REMOVED row is gone from the after-image, so it has no identity
        # there. Labelling it from the before-image would be the one place this
        # could print a file id that no longer resolves.
        changes.append({"row": i, "kind": REMOVED, "label": row_label(i),
                        "before": row_fields(row_bytes(b_mft, i)), "after": None,
                        "before_hex": row_bytes(b_mft, i).hex(), "after_hex": None})
    for i in range(nb, na):
        changes.append({"row": i, "kind": ADDED, "label": label_row(identity, i),
                        "before": None,
                        "after": row_fields(row_bytes(a_mft, i)),
                        "before_hex": None, "after_hex": row_bytes(a_mft, i).hex()})

    counts = {}
    for rec in changes:
        counts[rec["kind"]] = counts.get(rec["kind"], 0) + 1

    tier2 = {}
    for key in ("records", "released_records", "first_stream_rows", "rows_named",
                "orphan_count", "dangling_count", "file_id_sha256"):
        bv, av = before["tier2"][key], after["tier2"][key]
        if bv != av:
            tier2[key] = {"before": bv, "after": av}

    # THE FILE'S OWN LENGTH, which no other tier carries. `snapshot()` has
    # recorded `size_on_disk` since it was written and nothing ever compared it,
    # so an archive that GREW read as unchanged -- and growth is precisely the
    # signal studies/archivewrite Route B is about, precisely what the client
    # did NOT do in the caged session (studies/datwrite measured both copies at
    # 4,198,489,600 B), and the one change a 24-byte MFT diff cannot see because
    # appended bytes past every extent touch no row at all.
    size_before = before.get("size_on_disk")
    size_after = after.get("size_on_disk")
    growth = None
    if size_before is not None and size_after is not None \
            and size_before != size_after:
        growth = {"before": size_before, "after": size_after,
                  "delta": size_after - size_before}

    return {
        "before": before.get("dat"), "after": after.get("dat"),
        "rows_before": nb, "rows_after": na,
        "identified": identity is not None,
        "identity_note": identity_note,
        "tier0": tier0, "tier2": tier2, "growth": growth,
        "changes": changes, "counts": counts,
        "corroboration": corroboration,
        # `unchanged` means the table is byte for byte what it was, and rows 0,
        # 2 and 3 count towards that. They are separated out of `changes`
        # because they move on ANY flush and a post-flight that reported them as
        # findings would report three every time -- but "the client flushed" is
        # itself a fact about the run, so it may not be rounded down to nothing.
        "unchanged": not (tier0 or tier2 or changes or corroboration
                          or growth),
    }


def format_diff(d):
    out = []
    out.append("rows %d -> %d" % (d["rows_before"], d["rows_after"]))
    out.append("(%s)" % ROW_CONVENTION)
    if not d.get("identified"):
        out.append("NOT IDENTIFIED: %s Match these numbers against another "
                   "tool's with care."
                   % (d.get("identity_note")
                      or "two snapshots were compared with no archive behind "
                         "them, so no row below carries its file id or role."))
    if d.get("growth"):
        g = d["growth"]
        out.append("THE FILE'S LENGTH CHANGED: %d -> %d (%+d bytes)"
                   % (g["before"], g["after"], g["delta"]))
        out.append("   No row records this. The client did NOT grow the archive "
                   "in the one caged session measured (studies/datwrite),")
        out.append("   so growth is either ours or something nobody has seen "
                   "before -- either way it is not routine.")
    if d["tier0"]:
        out.append("TIER 0 changed:")
        for k, v in sorted(d["tier0"].items()):
            out.append("   %-20s %r -> %r" % (k, v["before"], v["after"]))
    else:
        out.append("TIER 0 unchanged (mftOffset alone is not a change signal; "
                   "the descriptor counter is)")
    if not d["changes"]:
        out.append("TIER 1: no row outside 0/2/3 changed")
    else:
        out.append("TIER 1: %d changed row(s) %s"
                   % (len(d["changes"]), d["counts"]))
        for rec in d["changes"][:40]:
            out.append("   %s" % rec.get("label", row_label(rec["row"])))
            out.append("      %s" % rec["kind"])
            if rec["before"] and rec["after"]:
                out.append("      before 0x%X %dB extra=%d flags=%d/%d next=%d "
                           "crc=0x%08X"
                           % (rec["before"]["offset"], rec["before"]["size"],
                              rec["before"]["extra_bytes"],
                              rec["before"]["alloc_flags"],
                              rec["before"]["alloc_stream"],
                              rec["before"]["next_stream"], rec["before"]["crc"]))
                out.append("      after  0x%X %dB extra=%d flags=%d/%d next=%d "
                           "crc=0x%08X"
                           % (rec["after"]["offset"], rec["after"]["size"],
                              rec["after"]["extra_bytes"],
                              rec["after"]["alloc_flags"],
                              rec["after"]["alloc_stream"],
                              rec["after"]["next_stream"], rec["after"]["crc"]))
        if len(d["changes"]) > 40:
            out.append("   ... %d more" % (len(d["changes"]) - 40))
    if d["corroboration"]:
        out.append("corroboration only (rows 0/2/3 change on any flush):")
        for r in d["corroboration"]:
            out.append("   %s" % r.get("label", row_label(r["row"])))
    if d["tier2"]:
        out.append("TIER 2 changed:")
        for k, v in sorted(d["tier2"].items()):
            out.append("   %-20s %r -> %r" % (k, v["before"], v["after"]))
    else:
        out.append("TIER 2 unchanged (the directory invariant, both ways)")
    out.append("")
    out.append("REMINDER: the entry CRC, the MFT self-CRC and the header CRC "
               "all still verify across a relocation. They are not detectors.")
    return "\n".join(out)
