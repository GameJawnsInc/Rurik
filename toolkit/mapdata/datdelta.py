"""Keep the difference, delete the copy. A staged archive IS its delta from retail.

Every staged run in this project has produced a whole archive.
`vault/exports/archivewrite/` holds ten staged run directories, and what each
one actually SAYS is small: A9's is a three-row chain at rows 35301/177335/177336
(`datalloc.py`'s own docstring, FINDINGS 18.6). A whole archive to carry three
rows. This module captures the byte difference, reconstitutes it byte-identically
on demand, and PROVES it did so before anybody deletes the original. Nothing here
is a backup format: the proof is the point, and `prove()` is the gate the delete
has to clear.

    python toolkit/mapdata/datdelta.py --capture a9/Gw.dat \
        --retail Gw.dat.retail --out vault/deltas/archivewrite
    python toolkit/mapdata/datdelta.py --prove vault/deltas/archivewrite \
        --retail Gw.dat.retail
    python toolkit/mapdata/datdelta.py --apply vault/deltas/archivewrite \
        --target scratch/Gw.dat --direction retail --name a9

SPAN-BASED, NOT MFT-SEMANTIC, and that is the load-bearing decision. A
row-by-row delta would need to know what a row IS: which rows moved, which grew
into blocks a shrunk neighbour freed, that a row's true reservation is a field
the format does not have (`datwrite._grow_gate`, citing `datalloc.py:127-132`),
that the MFT itself relocates during ordinary play and takes every row's address
with it. Every one of those subtleties is a chance to be confidently wrong. A
whole-file span diff knows none of them and cannot be wrong about any of them:
it is two files, some ranges of bytes that differ, and one sha256 that settles
whether the reconstitution worked. The MFT rows a span lands in are recorded as
an ANNOTATION for a human reading the manifest -- they are never consulted by
`apply()`, and if the archive cannot be opened at all the annotation is a note
and the delta still captures.

BOTH DIRECTIONS ARE STORED. A delta that only goes retail -> staged is a
one-way door: the staged copy is gone and the only way back to retail is the
retail file, which is exactly the thing an operator is most likely to also
delete. Each span carries the staged bytes and the retail bytes, so the store
alone can put either generation back onto a copy of the other.

THE MANIFEST IS NOT TRUSTED; THE OUTPUT IS VERIFIED. There is no self-hash on
the manifest, and adding one would be theatre -- anybody who can edit the span
table can recompute a hash over it. What cannot be faked is the destination:
`apply()` refuses unless the file it produced hashes to the identity the delta
recorded for that direction, so a doctored offset, a truncated span table or a
swapped blob all land as a refusal rather than a plausible archive. The
structural checks that CAN run before the write (span order, no overlaps, side
lengths consistent with the two file sizes, nothing past the end) do run first,
because a refusal that arrives after the write has already half-happened is a
worse refusal even when it is correct.

EVERY BLOB IS VERIFIED BEFORE THE TARGET IS OPENED FOR WRITING. The store is
small by construction (the caps below), so the whole delta is read and hashed in
one pass first. `bit31.py` learned this the same way -- it wrote `--json` and
then refused the baseline -- and here the cost of getting it wrong is a
half-reconstituted archive that no checksum in this repo would flag as such.

THE CAPS ARE A PREMISE CHECK, NOT A LIMIT. 4,096 spans or 256 MiB of difference
means the two files are not a staged copy and its baseline; they are two
different archives, and a "delta" of them is a slow, misleading way to store the
second one. Refused, naming the number, rather than grinding out a 3 GB store.

ALL OUTPUT LIVES UNDER THE VAULT. A span of a retail row is ArenaNet's bytes
verbatim -- the provenance gate's own words, `CLAUDE.md` -- so the store is
refused anywhere but under `vaultpath.vault_root()`, `vault/dat_study` and the
owner's install refused ahead of that. The repo carries the tool and nothing
else.

THE STORE IS SHARED AND CONTENT-ADDRESSED. Blobs are `blobs/<sha256>.bin` and
manifests are `<name>.delta.json`, so several staged archives cut from the same
retail baseline can live in one store and pay once for whatever they have in
common. A store with more than one manifest and no `--name` is a REFUSAL, never
a guess: `sorted(...)[-1]` has picked the wrong artifact three times in this
repo, in three different files. The WRITE side is gated the same way and for
the same reason -- capturing over a manifest that describes a different pair of
archives is refused, naming both, because the default stem is a basename and
`run/Gw.dat` and `run-live/Gw.dat` are both `gw`. The blobs of a clobbered
delta survive with nothing naming them; the span table that assembles them does
not, and that table is what licenses the delete.

Exit codes follow `datcheck.py` and `bit31.py`: 0 the verb ran and verified, 2
refused or unreadable. There is deliberately no 1 -- this tool has no "a result,
not an error" outcome to report.
"""

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive                            # noqa: E402
# The two path refusals are IMPORTED rather than restated. `datwrite.guard`
# refuses `C:\gw` and `guard_source` refuses `vault/dat_study`; both already
# carry the wording and the reasoning, and a second copy of a refusal is a
# second copy that can drift out of agreement with the first. `datwrite` imports
# `archive` and `gwdat` and nothing else, so this is no new dependency chain.
import datwrite                                        # noqa: E402
import vaultpath                                       # noqa: E402

FORMAT = "rurik-datdelta"
FORMAT_VERSION = 1

CHUNK = 1 << 20             # the compare/copy unit. Never read a whole archive.
MERGE_GAP = 64              # two differing runs closer than this are one span
MAX_SPANS = 4096            # premise check, not a limit -- see the docstring
MAX_DELTA_BYTES = 256 << 20
ANNOTATE_MAX = 32           # rows listed per span; the count is always exact
PROGRESS_EVERY = 512 << 20  # only ever fires on real archives

# 0 -> 0, everything else -> 1. `bytes.translate` does this at C speed, which is
# what makes the run finder below a handful of `find`/`rfind` calls instead of a
# Python loop over every differing byte (256 MiB of those is minutes).
NONZERO = bytes(0 if i == 0 else 1 for i in range(256))

MANIFEST_SUFFIX = ".delta.json"
BLOB_SUFFIX = ".bin"


# --------------------------------------------------------------- small parts

def _read_exact(fh, n):
    """`n` bytes or fewer at EOF. `read(n)` alone is allowed to return short."""
    out = bytearray()
    while len(out) < n:
        block = fh.read(n - len(out))
        if not block:
            break
        out += block
    return bytes(out)


def sha256_file(path, chunk=CHUNK):
    """Whole-file digest, chunked. Seconds on 4.2 GB, and never resident."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def identity(path):
    """What a file IS, for the purposes of refusing to write onto the wrong one."""
    return {"path": os.path.abspath(path),
            "size": os.path.getsize(path),
            "sha256": sha256_file(path)}


def _require_file(path, what):
    """A named refusal instead of a FileNotFoundError three frames down."""
    if not os.path.isfile(path):
        raise SystemExit(f"no {what} at {os.path.abspath(path)}")
    return path


def _safe_name(text):
    """A manifest stem that is a filename and nothing else."""
    keep = "abcdefghijklmnopqrstuvwxyz0123456789._-"
    out = "".join(c if c in keep else "-" for c in str(text).lower()).strip("-.")
    if not out:
        raise SystemExit(
            f"cannot make a delta name out of {text!r}\n"
            f"  Names are [a-z0-9._-]; pass --name explicitly.")
    return out


def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded, and REALPATH'd.

    Spelled out rather than imported from `bit31`/`atex`: it is four lines, and
    importing a private name across modules is a coupling that breaks silently.
    The realpath is not decoration -- a junction pointing out of the vault
    defeats a pure `abspath` compare, and this guard's whole job is to keep
    ArenaNet's bytes where the gitignore can see them.
    """
    path = os.path.normcase(os.path.realpath(path))
    root = os.path.normcase(os.path.realpath(root))
    return path == root or path.startswith(root + os.sep)


# ------------------------------------------------------------------- guards

def resolve_store(path, create=False):
    """Where a delta may live: under the vault, and nowhere else.

    THE ORDER IS LOAD-BEARING, and it is `bit31.resolve_out`'s order for the
    same reason: `dat_study` is INSIDE the vault, so the allow at the bottom
    would swallow it if it were tested second.
    """
    full = os.path.abspath(path)
    parts = os.path.normcase(os.path.realpath(full)).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise SystemExit(
            f"refusing to put a delta store at {full}\n"
            f"  vault/dat_study is the SOURCE snapshot every other archive in "
            f"the vault is cut from, and nothing in this repo can put it back.\n"
            f"  Name a directory under vault/exports/ or vault/research/ "
            f"instead.")
    if _inside(full, datwrite.LIVE_INSTALL):
        raise SystemExit(
            f"refusing to put a delta store at {full}\n"
            f"  That is the owner's own install at {datwrite.LIVE_INSTALL}, "
            f"which is read-only to this project, permanently (CLAUDE.md).")
    vault = vaultpath.require_dir(
        why="a delta of a retail row is ArenaNet's bytes verbatim, so the "
            "store belongs in the gitignored vault")
    if not _inside(full, vault):
        raise SystemExit(
            f"refusing to put a delta store at {full}\n"
            f"  The spans in a delta are ArenaNet's bytes, copied verbatim out "
            f"of the archive. They live under the vault ({vault}) or nowhere -- "
            f"the repo carries this tool and no derived bytes at all.\n"
            f"  Point --out at a directory under {vault}, or set RURIK_VAULT if "
            f"the vault has moved.")
    if create:
        os.makedirs(os.path.join(full, "blobs"), exist_ok=True)
    elif not os.path.isdir(full):
        raise SystemExit(f"no delta store at {full}\n"
                         f"  Nothing to read. Capture one first with --capture.")
    return full


def guard_target(path):
    """Where a reconstituted archive may land. `datwrite`'s two refusals, reused.

    A reconstitution is a full-file overwrite with no journal behind it -- this
    is a vault-copy operation, not a `datwrite.Writer` -- so the two paths that
    can never be rebuilt from anything in this repo are refused outright.
    """
    try:
        datwrite.guard(path)
        datwrite.guard_source(path)
    except SystemExit as exc:
        raise SystemExit(
            f"refusing to reconstitute onto {path}\n"
            f"{exc}\n"
            f"  A delta apply is an unjournalled whole-file overwrite. "
            f"Reconstitute into a scratch copy and move it yourself if that is "
            f"really what you mean.") from None
    return os.path.abspath(path)


# ---------------------------------------------------------------- the diff

def _differing_runs(a, b, gap):
    """[(start, length)] where two equal-length buffers differ, merged over < gap.

    All C speed: XOR through two big ints, `translate` to a 0/1 map, then
    `find`/`rfind`. The obvious byte loop is correct and takes minutes on a
    delta the size this module is willing to accept.
    """
    n = len(a)
    x = (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(n, "big")
    t = x.translate(NONZERO)
    sep = b"\x00" * gap                 # a zero run this long ENDS a span
    out, i = [], 0
    while i < n:
        s = t.find(b"\x01", i)
        if s < 0:
            break
        k = t.find(sep, s)
        if k < 0:
            out.append((s, t.rfind(b"\x01") + 1 - s))
            break
        out.append((s, t.rfind(b"\x01", s, k) + 1 - s))
        i = k + gap
    return out


def _merge(spans, gap):
    """Fold spans closer than `gap` together. Also closes the chunk seams."""
    out = []
    for start, length in spans:
        if out and start - (out[-1][0] + out[-1][1]) < gap:
            prev_start, _prev_len = out[-1]
            out[-1] = (prev_start, start + length - prev_start)
        else:
            out.append((start, length))
    return out


def diff_spans(a_path, b_path, chunk=CHUNK, gap=MERGE_GAP, progress=False):
    """[(offset, length)] covering every byte where the two files differ.

    Sizes may differ: everything past `min(size)` is ONE span, because a grown
    archive's tail is new by definition and there is nothing on the other side
    to compare it with. The per-chunk runs are merged again at the end, which is
    what keeps a difference straddling a chunk seam from being reported as two.
    """
    if gap < 1:
        raise SystemExit("a merge gap below 1 byte cannot separate two spans")
    size_a, size_b = os.path.getsize(a_path), os.path.getsize(b_path)
    common = min(size_a, size_b)
    spans, base, shout = [], 0, PROGRESS_EVERY
    with open(a_path, "rb") as fa, open(b_path, "rb") as fb:
        while base < common:
            n = min(chunk, common - base)
            ba, bb = _read_exact(fa, n), _read_exact(fb, n)
            if len(ba) != n or len(bb) != n:
                raise SystemExit(
                    f"short read at 0x{base:X}: {len(ba)}/{len(bb)} of {n} B\n"
                    f"  {a_path}\n  {b_path}\n"
                    f"  A file that shrank underneath the compare cannot be "
                    f"differenced. Is a client holding one of them open?")
            if ba != bb:
                for start, length in _differing_runs(ba, bb, gap):
                    spans.append((base + start, length))
            base += n
            if progress and base >= shout:
                print(f"  compared {base >> 20} MiB, {len(spans)} span(s) so far")
                shout += PROGRESS_EVERY
    if size_a != size_b:
        spans.append((common, max(size_a, size_b) - common))
    return _merge(spans, gap)


def _side_len(size, offset, length):
    """How much of a span a file of `size` bytes actually has. 0 past its end."""
    return max(0, min(size, offset + length) - offset)


def annotate_rows(spans, dat_path):
    """Which MFT rows each span lands in. ANNOTATION ONLY -- never load-bearing.

    `apply()` does not read this and does not need it: the delta is bytes and
    offsets. It exists so a human reading a manifest can see that a10's one
    span is row 8295 and not wonder. Best effort by construction -- a staged
    archive mid-experiment may not open at all, and that is a note, not a
    refusal.

    Rows are RAW one-based MFT indices via `Archive.row(n)`, per the repo's one
    addressing rule; `entries[n]` is a different row and has produced real false
    conclusions here. NOT `archive.row_of_position`, despite the name: that
    converts a position in `entries` to a row number and knows nothing about
    byte addresses. There is no byte-position-to-row helper in `archive.py`, so
    the extent sweep below is spelled out -- sorted extents against sorted spans,
    which is why `j` only ever moves forward.
    """
    blank = [{"rows": [], "row_count": 0, "mft": False} for _ in spans]
    try:
        ar = Archive(dat_path)
    except Exception as exc:                                   # noqa: BLE001
        return blank, f"{type(exc).__name__}: {exc}"
    try:
        extents = []
        for i in range(1, ar.row_count):        # 1..row_count-1: every real row
            e = ar.row(i)
            if e.size:
                extents.append((e.offset, e.offset + e.size, i))
        mft_lo, mft_hi = ar.mft_offset, ar.mft_offset + ar.mft_size
    except Exception as exc:                                   # noqa: BLE001
        return blank, f"{type(exc).__name__}: {exc}"
    finally:
        ar.close()

    extents.sort()
    out, j = [], 0
    for start, length in spans:                 # spans are already in address order
        end = start + length
        while j < len(extents) and extents[j][1] <= start:
            j += 1                              # ends before this span; and before
        k, rows = j, []                         # every later one, so drop it for good
        while k < len(extents) and extents[k][0] < end:
            if extents[k][1] > start:
                rows.append(extents[k][2])
            k += 1
        out.append({"rows": rows[:ANNOTATE_MAX], "row_count": len(rows),
                    "mft": start < mft_hi and end > mft_lo})
    return out, ""


# ------------------------------------------------------------------ capture

def _stash(blobs, fh, offset, length):
    """Copy a span out of `fh` into the content-addressed store. -> (sha, reused).

    Streamed through a temp file rather than held in memory: one span of a grown
    archive is the whole tail, and the point of chunking everything is that a
    4.2 GB archive never becomes 4.2 GB of Python bytes.
    """
    h = hashlib.sha256()
    tmp = os.path.join(blobs, ".incoming.tmp")
    fh.seek(offset)
    left = length
    with open(tmp, "wb") as out:
        while left > 0:
            block = fh.read(min(CHUNK, left))
            if not block:
                raise SystemExit(
                    f"short read stashing {length} B at 0x{offset:X}: "
                    f"{left} B missing. The file changed under the capture.")
            h.update(block)
            out.write(block)
            left -= len(block)
        out.flush()
        os.fsync(out.fileno())
    digest = h.hexdigest()
    dest = os.path.join(blobs, digest + BLOB_SUFFIX)
    # The size test is not paranoia about hash collisions -- it is about a torn
    # earlier run leaving a short file under a name that says otherwise.
    if os.path.isfile(dest) and os.path.getsize(dest) == length:
        os.remove(tmp)
        return digest, True
    os.replace(tmp, dest)
    return digest, False


def _write_json(path, doc):
    """Complete on disk at every instant: temp, fsync, replace."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _refuse_clobber(man_path, staged_id, retail_id, replace, whose_name):
    """Refuse to overwrite a DIFFERENT delta filed under the same name.

    THIS IS `sorted(...)[-1]` FROM THE WRITE SIDE. `manifest_path` already
    refuses to GUESS which of several deltas an operator meant; until this
    existed, `capture` was free to silently make it one. The default stem is the
    staged archive's basename and `_safe_name` folds case and punctuation, so
    `run/Gw.dat` and `run-live/Gw.dat` -- ours and ArenaNet's, the one
    distinction `CLAUDE.md` is most emphatic about -- are both `gw`, and so are
    `A9`, `a 9` and `a/9`.

    What an overwrite destroys is exactly the part that cannot be rebuilt. The
    blobs survive, content-addressed and now named by nothing; the span table
    that assembles them is gone. This module exists so a 4.2 GB original can be
    deleted on the strength of that table, so losing it silently is the one
    failure that cannot be walked back.

    A re-capture of the SAME pair is not a clobber -- it recomputes the same
    answer, and refusing it would make an interrupted capture unrepeatable.
    """
    if not os.path.isfile(man_path):
        return
    try:
        with open(man_path, "r", encoding="utf-8") as fh:
            old = json.load(fh)
        old_s, old_r = old["staged"]["sha256"], old["retail"]["sha256"]
    except (OSError, ValueError, KeyError, TypeError):
        # Unreadable is not "no delta here": it is a manifest this build cannot
        # compare against, which is the case for taking the loud road, not the
        # quiet one.
        old_s = old_r = "(unreadable -- " + os.path.basename(man_path) + ")"
    if old_s == staged_id["sha256"] and old_r == retail_id["sha256"]:
        print(f"  re-capturing {os.path.basename(man_path)}: same staged and "
              f"same retail, so this overwrites its own answer")
        return
    if replace:
        print(f"  --replace: {os.path.basename(man_path)} described staged "
              f"{old_s[:16]}... and is being overwritten")
        return
    raise SystemExit(
        f"{man_path}\n  already describes a DIFFERENT pair of archives.\n"
        f"  on disk    staged {old_s}\n"
        f"             retail {old_r}\n"
        f"  capturing  staged {staged_id['sha256']}\n"
        f"             retail {retail_id['sha256']}\n"
        f"  Overwriting it would leave that delta's blobs in the store with "
        f"nothing naming them, and no way back to the archive it stood in "
        f"for.\n"
        f"  The name came from {whose_name}. Pass --name SOMETHING-ELSE to "
        f"file this delta beside the one already there, or --replace to "
        f"overwrite it deliberately.")


def capture(staged, retail, out_dir, name=None, progress=False, replace=False):
    """Record what makes `staged` different from `retail`. Returns the manifest.

    Every refusal about the CALLER's premise -- same file, no difference, a
    name already taken by a different pair, too many spans, too many bytes --
    is decided before a byte is written into the
    store, which is why the caps live here and not inside `diff_spans`: the span
    table is a fact about two files, and whether that fact means the premise is
    wrong is this verb's judgement to make. (`_check_span_table` runs at the end
    too, but that one is a self-check on our own output rather than a gate on
    the caller's, and it fires after the blobs are down. Content-addressed blobs
    nobody's manifest names are inert.)
    """
    if os.path.abspath(staged) == os.path.abspath(retail):
        raise SystemExit(
            f"--capture and --retail name the same file ({staged})\n"
            f"  A file has no delta from itself.")
    _require_file(staged, "staged archive")
    _require_file(retail, "retail baseline")
    store = resolve_store(out_dir, create=True)
    stem = _safe_name(name or os.path.splitext(os.path.basename(staged))[0])
    man_path = os.path.join(store, stem + MANIFEST_SUFFIX)

    staged_id, retail_id = identity(staged), identity(retail)
    if staged_id["sha256"] == retail_id["sha256"]:
        raise SystemExit(
            f"{staged} is byte-identical to {retail}\n"
            f"  There is no delta here, which means either the staging never "
            f"landed or this is already the baseline. Nothing was written.\n"
            f"  If the staged copy really is retail, it carries no information "
            f"and can be deleted without this tool.")
    _refuse_clobber(man_path, staged_id, retail_id, replace,
                    "--name" if name else
                    f"the staged filename {os.path.basename(staged)!r}")

    spans = diff_spans(staged, retail, progress=progress)
    covered = sum(length for _off, length in spans)
    if len(spans) > MAX_SPANS:
        raise SystemExit(
            f"{len(spans)} differing spans between\n"
            f"    {staged}\n    {retail}\n"
            f"  more than the sanity cap of {MAX_SPANS}. A delta this shredded "
            f"means the premise is wrong: these are two different archives, not "
            f"a staged copy and the baseline it was cut from.\n"
            f"  Check that --retail names the archive --capture was copied from.")
    if covered > MAX_DELTA_BYTES:
        raise SystemExit(
            f"{covered} B differ between\n"
            f"    {staged}\n    {retail}\n"
            f"  more than the sanity cap of {MAX_DELTA_BYTES} B. Storing that "
            f"as a 'delta' is a slow way to store the second archive.\n"
            f"  Check that --retail names the archive --capture was copied from.")

    notes, note = annotate_rows(spans, staged)
    if note:
        notes, note2 = annotate_rows(spans, retail)
        note = (f"rows annotated from the retail baseline; the staged copy "
                f"would not open ({note})") if not note2 else \
               (f"rows NOT annotated: neither archive opened "
                f"(staged: {note}; retail: {note2})")

    table, written, reused = [], 0, 0
    with open(staged, "rb") as fs, open(retail, "rb") as fr:
        for (offset, length), ann in zip(spans, notes):
            s_len = _side_len(staged_id["size"], offset, length)
            r_len = _side_len(retail_id["size"], offset, length)
            s_sha, s_re = _stash(os.path.join(store, "blobs"), fs, offset, s_len)
            r_sha, r_re = _stash(os.path.join(store, "blobs"), fr, offset, r_len)
            for was_reused in (s_re, r_re):
                reused += 1 if was_reused else 0
                written += 0 if was_reused else 1
            row = {"offset": offset, "length": length,
                   "staged": {"length": s_len, "sha256": s_sha},
                   "retail": {"length": r_len, "sha256": r_sha}}
            row.update(ann)
            table.append(row)

    doc = {"format": FORMAT, "version": FORMAT_VERSION, "name": stem,
           "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "chunk": CHUNK, "merge_gap": MERGE_GAP,
           "staged": staged_id, "retail": retail_id,
           "spans": table,
           "totals": {"spans": len(table), "covered_bytes": covered,
                      "staged_bytes": sum(s["staged"]["length"] for s in table),
                      "retail_bytes": sum(s["retail"]["length"] for s in table),
                      "blobs_written": written, "blobs_reused": reused},
           "note": note}
    _check_span_table(doc)      # the same gate `apply` runs, before we claim green
    _write_json(man_path, doc)
    doc["manifest"] = man_path
    return doc


# -------------------------------------------------------------------- apply

def manifest_path(store, name=None):
    """The one manifest in a store, or a refusal naming the ambiguity.

    NEVER `sorted(...)[-1]`. Picking the last of several artifacts by name has
    chosen the wrong build three times in this repo, in three different files,
    and a store is explicitly allowed to hold several deltas.
    """
    if not os.path.isdir(store):
        raise SystemExit(f"no delta store at {store}\n"
                         f"  Nothing to read. Capture one first with --capture.")
    if name:
        path = os.path.join(store, _safe_name(name) + MANIFEST_SUFFIX)
        if not os.path.isfile(path):
            raise SystemExit(f"no delta named {name!r} in {store}\n"
                             f"  looked for {path}")
        return path
    found = sorted(f for f in os.listdir(store) if f.endswith(MANIFEST_SUFFIX))
    if not found:
        raise SystemExit(f"no delta manifest (*{MANIFEST_SUFFIX}) in {store}\n"
                         f"  Capture one first with --capture.")
    if len(found) > 1:
        listed = "\n".join(f"    {f}" for f in found)
        raise SystemExit(
            f"{len(found)} deltas in {store} and no --name to choose between "
            f"them:\n{listed}\n"
            f"  Name one with --name. This tool does not pick the last one.")
    return os.path.join(store, found[0])


def load(store, name=None):
    """(manifest path, document). Refuses anything that is not one of ours."""
    path = manifest_path(store, name)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"cannot read the delta manifest {path}\n"
                         f"  {type(exc).__name__}: {exc}") from None
    if doc.get("format") != FORMAT or doc.get("version") != FORMAT_VERSION:
        raise SystemExit(
            f"{path} is not a datdelta manifest this build understands\n"
            f"  format {doc.get('format')!r} version {doc.get('version')!r}, "
            f"expected {FORMAT!r} version {FORMAT_VERSION}")
    return path, doc


def _check_span_table(doc):
    """Everything about the span table that can be refuted without writing.

    This is the cheap half of the gate. The expensive half -- and the one that
    cannot be walked around -- is the destination hash in `apply()`; a manifest
    doctored consistently will pass everything here and still be refused there.
    """
    s_size, r_size = doc["staged"]["size"], doc["retail"]["size"]
    end = 0
    for i, span in enumerate(doc["spans"]):
        off, length = span["offset"], span["length"]
        if length <= 0:
            raise SystemExit(f"span {i} of {doc['name']} is {length} B long")
        if off < end:
            raise SystemExit(
                f"span {i} of {doc['name']} starts at 0x{off:X}, inside or "
                f"behind the span before it (which ends at 0x{end:X}).\n"
                f"  The span table is written in address order and never "
                f"overlaps; this manifest has been edited or is not ours.")
        if off + length > max(s_size, r_size):
            raise SystemExit(
                f"span {i} of {doc['name']} runs to 0x{off + length:X}, past "
                f"the end of both archives ({s_size} / {r_size} B).")
        for side, size in (("staged", s_size), ("retail", r_size)):
            want = _side_len(size, off, length)
            if span[side]["length"] != want:
                raise SystemExit(
                    f"span {i} of {doc['name']} says its {side} side is "
                    f"{span[side]['length']} B, but a {size} B file has {want} "
                    f"B there.\n  This manifest does not describe the files it "
                    f"names.")
        end = off + length


def _verify_blobs(store, doc, side):
    """Read and hash every blob one direction needs. Returns {sha: path}.

    BEFORE the target is opened for writing, always. A tampered blob caught
    halfway through a reconstitution leaves an archive that is neither
    generation and that nothing in this repo can name.

    EXISTENCE AND LENGTH ARE PER SPAN; ONLY THE HASHING IS DEDUPED, and the
    distinction is the whole point. A blob's length is a claim the SPAN makes,
    and two spans naming one blob are perfectly entitled to disagree about it --
    the store is content-addressed, so the same bytes staged at two offsets are
    ONE blob named by TWO spans, which is the dedupe this tool advertises rather
    than an exotic case. Skipping the second span's check because the first had
    already cleared the blob saved a `stat` and cost an INFINITE LOOP in
    `apply`'s write below, filling a 400 B span from a 4 B file. Hashing is the
    expensive half and is still paid once per blob.
    """
    blobs, found = os.path.join(store, "blobs"), {}
    for i, span in enumerate(doc["spans"]):
        sha, length = span[side]["sha256"], span[side]["length"]
        path = os.path.join(blobs, sha + BLOB_SUFFIX)
        if not os.path.isfile(path):
            raise SystemExit(
                f"span {i} of {doc['name']} needs blob {sha[:16]}... and it is "
                f"not in the store\n  looked for {path}")
        size = os.path.getsize(path)
        if size != length:
            raise SystemExit(
                f"blob {sha[:16]}... is {size} B; span {i} of {doc['name']} "
                f"declares {length} B\n  {path}\n"
                f"  A blob is named by its own sha256, so its length is not "
                f"negotiable. Either the store was edited or the span table "
                f"was; neither can be reconstituted from.")
        if sha in found:
            continue                    # same blob: read and hashed already
        got = sha256_file(path)
        if got != sha:
            raise SystemExit(
                f"blob {path}\n  hashes to {got}\n  but is filed under {sha}\n"
                f"  The store has been edited or damaged. Re-capture from the "
                f"staged archive if it still exists; this delta cannot be "
                f"trusted to reconstitute anything.")
        found[sha] = path
    return found


def apply(delta_dir, target, direction="staged", name=None):
    """Turn `target` into the delta's `direction` generation, and prove it.

    The source identity is checked first and the destination identity last, and
    both are whole-file sha256: a delta reconstituted onto the wrong generation
    would produce a file that is neither, and no CRC rule, no preflight rule and
    no overlap sweep in this project would call that archive damaged.
    """
    if direction not in ("staged", "retail"):
        raise SystemExit(f"--direction {direction!r} is neither 'staged' nor "
                         f"'retail'; those are the two generations a delta has")
    store = resolve_store(delta_dir)
    path, doc = load(store, name)
    _check_span_table(doc)
    other = "retail" if direction == "staged" else "staged"
    dest_id, src_id = doc[direction], doc[other]

    full = guard_target(target)
    if not os.path.isfile(full):
        raise SystemExit(f"no file at {full} to reconstitute onto\n"
                         f"  Copy the {other} archive there first.")
    blobs = _verify_blobs(store, doc, direction)

    have = sha256_file(full)
    if have != src_id["sha256"]:
        if have == dest_id["sha256"]:
            raise SystemExit(
                f"{full} is ALREADY the {direction} generation of "
                f"{doc['name']} ({have[:16]}...).\n"
                f"  Nothing to do. Pass --direction {other} to go the other "
                f"way.")
        raise SystemExit(
            f"{full}\n  hashes to   {have}\n"
            f"  expected    {src_id['sha256']}  (the {other} generation of "
            f"{doc['name']}, {src_id['size']} B)\n"
            f"  This delta only reconstitutes onto the generation it was cut "
            f"from. Refusing to write spans onto an archive that is neither.\n"
            f"  Manifest: {path}")

    written = 0
    with open(full, "r+b") as fh:
        for span in doc["spans"]:
            length = span[direction]["length"]
            if length:
                fh.seek(span["offset"])
                sha = span[direction]["sha256"]
                with open(blobs[sha], "rb") as src:
                    left = length
                    while left > 0:
                        block = src.read(min(CHUNK, left))
                        if not block:
                            # `_stash` has carried this guard from the start and
                            # this loop did not, and the difference was not a
                            # short write -- it was a HANG. `read()` past the
                            # end of a file returns b"" for ever, `left` never
                            # moves, and the target sits open "r+b" and half
                            # written while the process spins. A hang is not a
                            # refusal, and this module's contract is that
                            # everything wrong lands as one.
                            raise SystemExit(
                                f"blob {sha[:16]}... ran out {left} B short of "
                                f"the {length} B span at 0x{span['offset']:X}\n"
                                f"  {blobs[sha]}\n"
                                f"  It was the right length when the store was "
                                f"verified moments ago, so something is writing "
                                f"in the store while this runs.\n"
                                f"  {full} IS NOW NEITHER GENERATION. Delete it "
                                f"and copy the {other} archive back.")
                        fh.write(block)
                        left -= len(block)
                written += length
        fh.truncate(dest_id["size"])
        fh.flush()
        os.fsync(fh.fileno())

    got = sha256_file(full)
    if got != dest_id["sha256"]:
        raise SystemExit(
            f"RECONSTITUTION FAILED and {full} IS NOW NEITHER GENERATION.\n"
            f"  produced {got}\n"
            f"  wanted   {dest_id['sha256']}  ({direction} of {doc['name']})\n"
            f"  Every blob hashed correctly before the write, so the span table "
            f"in {path} does not describe these two archives -- it has been "
            f"edited, or it was captured against a different pair.\n"
            f"  Delete {full} and copy the {other} archive back before "
            f"retrying.")
    return {"manifest": path, "name": doc["name"], "direction": direction,
            "target": full, "spans": len(doc["spans"]), "bytes_written": written,
            "size": dest_id["size"], "sha256": got}


# -------------------------------------------------------------------- prove

def store_bytes(store):
    """What the delta actually costs on disk: manifests plus blobs."""
    total = 0
    for root, _dirs, files in os.walk(store):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
        # A proof copy under the store would dwarf the answer and is transient.
        _dirs[:] = [d for d in _dirs if d != "proof"]
    return total


def prove(delta_dir, retail, out_dir=None, name=None, keep=False):
    """Reconstitute a fresh copy of retail and hash it. The gate before a delete.

    Deliberately hashes the file ITSELF rather than believing `apply()`'s
    report: `apply` verifying its own output is one witness, and this verb
    exists precisely for the moment somebody is about to throw away the only
    other copy of the thing being verified.

    The 4.2 GB proof copy is DELETED on success and KEPT on failure -- keeping
    it on success defeats the purpose, and deleting it on failure throws away
    the only evidence of what went wrong.
    """
    store = resolve_store(delta_dir)
    path, doc = load(store, name)
    proof_dir = resolve_store(out_dir, create=True) if out_dir else \
        os.path.join(store, "proof")
    os.makedirs(proof_dir, exist_ok=True)
    copy = os.path.join(proof_dir, doc["name"] + ".proof.dat")

    _require_file(retail, "retail baseline")
    retail_id = identity(retail)
    if retail_id["sha256"] != doc["retail"]["sha256"]:
        raise SystemExit(
            f"{retail}\n  hashes to {retail_id['sha256']}\n"
            f"  but {doc['name']} was cut against {doc['retail']['sha256']}\n"
            f"  Proving a delta against the wrong baseline proves nothing. "
            f"Name the archive the staged copy was made from.")

    print(f"copying {retail} -> {copy}")
    _copy_file(retail, copy)
    report = apply(store, copy, "staged", name=doc["name"])
    got = sha256_file(copy)                 # the independent witness
    ok = got == doc["staged"]["sha256"]
    delta = store_bytes(store)
    if ok and not keep:
        os.remove(copy)
    print("")
    if not ok:
        raise SystemExit(
            f"NOT PROVEN. The reconstituted copy hashes to {got}, not "
            f"{doc['staged']['sha256']}.\n"
            f"  The copy has been KEPT at {copy} so it can be examined.\n"
            f"  Do not delete the staged original.")
    print(f"PROVEN: {doc['name']} reconstitutes byte-identically")
    print(f"  staged archive  {doc['staged']['size']:>14,} B  "
          f"{doc['staged']['sha256'][:16]}...")
    print(f"  delta store     {delta:>14,} B  "
          f"{report['spans']} span(s), {report['bytes_written']:,} B written")
    if doc["staged"]["size"]:
        print(f"  the store is {100.0 * delta / doc['staged']['size']:.4f}% of "
              f"the archive it stands in for")
    print(f"  the staged original at {doc['staged']['path']} can be deleted")
    return {"proven": True, "name": doc["name"], "manifest": path,
            "sha256": got, "store_bytes": delta,
            "archive_bytes": doc["staged"]["size"],
            "proof": copy if keep else None}


def _copy_file(src, dst):
    with open(src, "rb") as a, open(dst, "wb") as b:
        for block in iter(lambda: a.read(CHUNK), b""):
            b.write(block)
        b.flush()
        os.fsync(b.fileno())


# ---------------------------------------------------------------------- CLI

def format_capture(doc):
    t = doc["totals"]
    lines = [f"{doc['name']}  ->  {doc.get('manifest', '(not written)')}",
             f"  staged  {doc['staged']['size']:>14,} B  "
             f"{doc['staged']['sha256'][:16]}...  {doc['staged']['path']}",
             f"  retail  {doc['retail']['size']:>14,} B  "
             f"{doc['retail']['sha256'][:16]}...  {doc['retail']['path']}",
             f"  {t['spans']} span(s) covering {t['covered_bytes']:,} B; "
             f"{t['blobs_written']} blob(s) written, {t['blobs_reused']} reused"]
    for i, span in enumerate(doc["spans"]):
        if i == 20:
            lines.append(f"  ... {len(doc['spans']) - 20} more span(s)")
            break
        rows = ",".join(str(r) for r in span["rows"])
        if span["row_count"] > len(span["rows"]):
            rows += f",+{span['row_count'] - len(span['rows'])}"
        where = f"rows {rows}" if rows else "no row"
        lines.append(f"    0x{span['offset']:012X}  {span['length']:>10,} B  "
                     f"staged {span['staged']['length']:>10,} / retail "
                     f"{span['retail']['length']:>10,}  {where}"
                     + ("  MFT" if span["mft"] else ""))
    if doc.get("note"):
        lines.append(f"  NOTE: {doc['note']}")
    return lines


def _run(args):
    verbs = [bool(args.capture), bool(args.apply), bool(args.prove)]
    if sum(verbs) != 1:
        raise SystemExit(
            "name exactly one of --capture, --apply, --prove\n"
            "  Each one is a different thing to do to a 4 GB file and they are "
            "never combined.")
    if args.capture:
        if not args.retail or not args.out:
            raise SystemExit("--capture needs --retail BASELINE and --out DIR")
        doc = capture(args.capture, args.retail, args.out, name=args.name,
                      progress=True, replace=args.replace)
        print("\n".join(format_capture(doc)))
        return 0
    if args.apply:
        if not args.target:
            raise SystemExit("--apply needs --target FILE to reconstitute onto")
        rep = apply(args.apply, args.target, args.direction, name=args.name)
        print(f"{rep['target']} is now the {rep['direction']} generation of "
              f"{rep['name']}")
        print(f"  {rep['spans']} span(s), {rep['bytes_written']:,} B written, "
              f"{rep['size']:,} B total, {rep['sha256'][:16]}...")
        return 0
    if not args.retail:
        raise SystemExit("--prove needs --retail BASELINE to reconstitute from")
    prove(args.prove, args.retail, out_dir=args.out, name=args.name,
          keep=args.keep)
    return 0


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", metavar="STAGED",
                    help="the staged archive to record the difference of")
    ap.add_argument("--retail", metavar="BASELINE",
                    help="the pristine archive it was copied from")
    ap.add_argument("--out", metavar="DIR",
                    help="the delta store (must be under the vault)")
    ap.add_argument("--apply", metavar="DIR", help="reconstitute from this store")
    ap.add_argument("--target", metavar="FILE",
                    help="the file --apply writes; must already BE the other "
                         "generation")
    ap.add_argument("--direction", choices=("staged", "retail"),
                    default="staged", help="which generation to produce")
    ap.add_argument("--prove", metavar="DIR",
                    help="reconstitute a fresh copy and hash it")
    ap.add_argument("--name", help="which delta, when a store holds several")
    ap.add_argument("--replace", action="store_true",
                    help="--capture: overwrite a manifest of this name that "
                         "describes a DIFFERENT pair of archives")
    ap.add_argument("--keep", action="store_true",
                    help="--prove: keep the reconstituted copy")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except SystemExit as exc:
        # `SystemExit` is this tree's refusal (`atex.Refused` subclasses it), so
        # a string payload is a refusal and an int is somebody's exit code.
        if isinstance(exc.code, int):
            return exc.code
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:                                   # noqa: BLE001
        # BROAD ON PURPOSE, `bit31.py`'s reasoning: a delta that could not be
        # taken, or a reconstitution that did not happen, must never leave this
        # process with the exit code that means it did.
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main())
