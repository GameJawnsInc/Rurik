r"""Declarative archive profiles: the gate must FIND a planted co-reader before
any acknowledgement is believed, and must not demand one it cannot justify.

    python toolkit/mapdata/test_overlay.py

Builds its own archives, its own manifests and its own payloads in a temp
directory, and points `RURIK_VAULT` at a temp vault. There is no corpus to be
missing and nothing here reads the real one, so no section can legitimately
skip. Every fixture below is written from ITS OWN byte literals -- the container
framing, the reference-list record rule, the FA1 blk2C layout and the MFT itself
-- and imports nothing from `overlay` or `refindex` to build them, because a
test that asks the module under test to construct its own input can only
discover that the module agrees with itself.

SECTION 3 IS THE POSITIVE CONTROL AND IT IS THE POINT OF THE FILE. The refindex
gate's job is to refuse an edit whose file id is read by somebody else, and the
failure mode of a bounded query is the CONFIDENT EMPTY ANSWER -- which looks
exactly like "nobody reads it, go ahead". So the first thing section 3 does is
plant two FA8 links onto the edited row and require the gate to REFUSE, naming
both referrers, before any of the passing cases below it mean anything (MEMORY:
"a negative needs a positive control").

THE TIER IS MEASURED, NOT CHOSEN, and section 3 checks both halves of it. A
co-reader is a real reference and always needs acknowledging. A skeleton
co-wearer needs acknowledging only when the shared key carries a pose: applied
population-wide the bit-identical criterion also groups the degenerate arrays --
one node at (-0.0, -0.0, -0.0) -- and 572 retail heads sit in one such group, so
a gate that demanded 571 acknowledgements on the first real edit would be
teaching an operator to paste whatever the tool printed. Both cells are planted:
a real two-node shared rig that MUST refuse, and an all-zero group that must
pass with the note printed and nothing demanded.

EVERY SPELLING OF A ROW IS ONE ACKNOWLEDGEMENT. 38,396 retail rows carry two
file ids, 60% of the heads among them, so an operator's `acknowledge_shared_with
= [0x491C0]` and an index answering `0x138D1` are naming one row. Section 3
acknowledges a co-reader under its OTHER plain spelling and requires the plan to
PASS -- a gate that refused a complete declaration is a gate that gets a
`--force` bolted onto it.

SECTION 3b IS THE SECOND POSITIVE CONTROL, AND IT IS ABOUT THE INDEX RATHER
THAN THE ARCHIVE. A stamped, current, non-partial index still answers EMPTY for
a row whose only referrers are heads it could not READ -- and the first version
of this gate treated that exactly like an honest empty answer. So 3b plants the
state: A and B keep their real FA8 lists naming C and have their container magic
damaged to `ffnX`. The archive stays healthy (all ten rules, every crc), the
index builds and is current, `who_reads(C)` answers `[]`, and the plan must
still REFUSE until the manifest declares the blind spot by COUNT. Then the
contrast that names the defect: the same edit against the archive whose
containers do read is refused for a real FA5 referrer, so the empty answer was
the damage and not the truth. A partial index gets no acknowledgement at all,
and an id the index resolves to a different row than the archive does -- a
file-id table edited in place, which the MFT stamp cannot see -- is refused.

SECTION 7 IS A SEQUENCE WITH NO CLIENT IN IT. `--build`, `--deploy --yes`,
`--retail --yes`, `--verify-after` used to end with the post-flight naming a row
`--retail` had rewritten seconds earlier as one "the client wrote to", because
the comparand was the BUILD record -- what was staged -- rather than the
before-image the deploy took. The section runs that exact sequence and requires
a refusal, runs the re-build variant of it and requires another, and checks that
the two halves of a before-image have to describe one deploy.

THE GROW CELL IS NOT DEAD CODE AND SECTION 5 PROVES IT AGAINST A REAL WRITE. On
a fresh copy of RETAIL a row's current reservation IS the donor's, so the fit is
binary and the middle cell is unreachable; it exists for the staged copy that
has already been written once and shrank. Section 5 builds exactly that -- a row
whose size field is 100 B while its own 1,024 B of blocks stand free -- and
requires `datwrite.replace` to grow it back with a `grow_to` sourced from the
donor row, not invented to make the write fit.

THE SABOTAGES are section 4's doctored build record and section 2's duplicate
file id. The first hand-edits a fingerprint after the build and requires every
verb that reads it to refuse; the second puts two file-id records on one id, the
state `archive.file_id_table` resolves by taking whichever comes first, and
requires the plan to refuse rather than pick.
"""

import binascii
import contextlib
import io
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive                                  # noqa: E402
import datcheck                                              # noqa: E402
import datwrite                                              # noqa: E402
import gwenc                                                 # noqa: E402
from mapchunks import dependency_pair                        # noqa: E402
import overlay                                               # noqa: E402
from overlay import (GROW_BACK, IN_RESERVATION, TOO_BIG,      # noqa: E402
                     apply_edits, build, deploy, deployed_state,
                     fit_of, load_manifest, plan, restore_retail,
                     verify_after)
import refindex                                              # noqa: E402
import vaultpath                                             # noqa: E402
import checks                                                # noqa: E402

# FLOOR: 133, RE-MEASURED from a real green run on 2026-08-20 after the review
# fixes, not guessed. Every section builds its own archives, manifests and
# payloads in a tempdir and points RURIK_VAULT at a temp vault, so there is no
# corpus to be missing and nothing that can legitimately skip. Per section,
# counted from the log rather than predicted:
# {0: 15, 1: 11, 2: 13, 3: 18, 3b: 22, 4: 5, 4b: 11, 5: 7, 6: 13, 7: 12, 8: 6}.
#
# SABOTAGES, applied one at a time as in-memory patches to a name the real code
# path resolves through, then reverted. Nothing on disk was edited, and these
# are the reds OBSERVED, not predicted:
#
#   fit_of returns in-reservation whenever the row exists             15 red
#   the refindex gate never refuses (unack is always empty)           10 red
#   index_faults never refuses (a blind index answers for a whole one) 8 red
#   an answer's floor sentence collapses to a bare count               5 red
#   the gate's notes are dropped (the contentless tier goes silent)    5 red
#   co-wearers are gated even when the key is contentless              4 red
#   the deploy's before-image survives --retail and --build            4 red
#   the post-flight's before-image is the BUILD record                 3 red   *
#   --deploy stops requiring --yes                                     3 red
#   deployed_state answers the overlay name whenever it is not retail  3 red
#   the fingerprints self-digest is not checked on load                3 red   +
#   an accept_unread declaration is accepted without matching the count 2 red
#   the index/archive row cross-check is dropped                       2 red
#   the gate stops normalising through refindex.canonical_id           2 red   +
#   the two halves of the before-image are not tied together           1 red
#   the "no record of this row" note is dropped                        1 red
#   the "this row is itself unreadable" note is dropped                1 red
#   grow_to is invented from the payload instead of the donor          1 red
#   looks_like_retail always returns False                             1 red
#   an ambiguous file id resolves to the first row rather than refusing 1 red
#   an unknown [overlay] key is accepted instead of refused            1 red   +
#
#   * 3 with the pre-fix shape reproduced exactly -- the build record read in
#     and the pair check made vacuous rather than removed; 6 if the pair check
#     is disabled outright, which is a second defect and is measured as one.
#     The four SEQUENCE reds for this finding are the row above it: what stops
#     the post-flight blaming the client for --retail's own bytes is the
#     before-image being deleted, and reading the right record is what stops it
#     answering about the wrong moment.
#
#   + PATCH THE LEAF, NOT `overlay`. These three sabotages patch a name that is
#     read from INSIDE a unit the refactor moved out, so `overlay.<name> = fake`
#     now patches a re-exported alias that nothing reads: the sabotage goes
#     GREEN and a counted refutation silently stops refuting. Re-run them
#     against the module that owns the read -- `_self_sha` (read by
#     load_fingerprints) and `MANIFEST_KEYS` (read by load_manifest) in
#     overlaystate.py, `canonical_id` (read bare inside gate_edit) in
#     overlayrefgate.py. The rule, once, for the whole ledger: a name read from
#     inside a moved unit loses its `overlay.<name>` patch handle; a name
#     overlay.py still CALLS keeps it -- fit_of, gate_edit, index_faults,
#     index_row_fault, looks_like_retail, id_records, rows_named_by and
#     load_fingerprints stay patchable through `overlay`, which is why every
#     call site in overlay.py stayed byte-identical. `overlay._self_sha` is the
#     sharp one: it stays a LIVE re-export because datcheck.py calls it, so the
#     alias has two meanings now -- real for that caller, dead for this patcher.
#
# Three readings worth keeping rather than tidying away.
#
# EVERY SABOTAGE RAN ALL 133 CHECKS, and that took a rewrite to be true. The
# first pass measured three of them at ran=46, ran=51 and ran=74 with 0, 0 and 7
# red: a defect that makes a gate refuse something CORRECT ends the run at
# whatever check comes next, and a test that only crashes has said the machine
# is unhappy rather than what broke. `Ran`, `state_of`, `health` and a
# defensive `row_bytes` exist for exactly that, and the numbers moved 0->2, 0->4
# and 7->11 when they landed. A sabotage that stops the run under-reports
# coverage, which is a way to conclude a check is weak when it is fine.
#
# THE SIX NEW SABOTAGES ARE THE REVIEW'S TWO FINDINGS, MEASURED. Both were
# reachable from the CLI with every existing guard green: an index that could
# not READ the two heads referencing the edited row cleared the gate exactly
# like an index that answered honestly-empty, and a post-flight compared the
# live archive against the BUILD record and reported bytes `--retail` had
# written as "the client wrote to a row this overlay owns". Section 3b and the
# rewritten section 7 exist for those two and nothing else.
#
# THE canonical_id SABOTAGE IS THE ONE THE FIXTURE HAD TO BE BUILT FOR. It
# scores 2, and it would score ZERO on a fixture where no row carried two file
# ids -- which is why row A has two plain spellings and why both a COMPLETE
# declaration in the other spelling and a PARTIAL one are asked. On retail
# 38,396 rows are multiply named and 60% of the heads are among them, so the
# case the fixture would otherwise have missed is the common one.
#
# THE FOUR ONE-RED SABOTAGES ARE THIN AND ARE NAMED AS THIN. Each is caught by
# exactly the one check pointed at it, because each is a single refusal that
# nothing else in the file depends on. The count is not the measure of what they
# are worth: `--yes` is the only thing between a read-only-looking invocation
# and a whole-file overwrite of an archive other sessions share, and an
# ambiguous file id resolved silently lands an edit on whichever record happens
# to sort first.
LEDGER = checks.Ledger("declarative archive profiles", floor=133)
check = checks.adopt(LEDGER)

# ---------------------------------------------------------------------------
# Fixture literals. Nothing below is imported from the module under test.
# ---------------------------------------------------------------------------

BLOCK = 512
ENTRY_SIZE = 24
ENTRY_CRC = 0x14
FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
FIRST_ROW = 16                   # rows 0..15 are structural (datcheck rule 9)

HEAD = 515                       # "addressable model-file head"
PLAIN_FILE = 3                   # USED|FIRST_STREAM: a texture, not a model

GEOMETRY, SKELETON = 0xFA0, 0xFA1
FA5, FA8 = 0xFA5, 0xFA8
SKEL_VERSION = 0x26              # 0x0079495D  cmp dword ptr [ecx], 0x26

#: A carries TWO plain spellings -- the 60%-of-heads case -- so acknowledging
#: it under either one has to work.
FID_A, FID_A2 = 120001, 320001
FID_B, FID_C, FID_D = 120002, 130003, 140004
FID_Z1, FID_Z2 = 200011, 200012
FID_TEX = 210015
FID_ABSENT = 999999

ROW_A, ROW_B, ROW_C, ROW_D = 16, 17, 18, 19
ROW_Z1, ROW_Z2, ROW_TEX = 20, 21, 22

BASES1 = ((1.0, 2.0, 3.0), (4.5, -5.25, 6.125))     # A and B wear this one
BASES2 = ((7.0, 8.0, 9.0), (0.5, 0.25, 0.125))      # C alone
BASES3 = ((-1.0, 0.0, 11.5), (2.75, 2.75, 2.75))    # D alone
#: The degenerate key, in retail's own spelling: one node, every component
#: NEGATIVE zero. `-0.0 == 0.0` is true, so the key carries no pose.
BASES_ZERO = ((-0.0, -0.0, -0.0),)

#: Row D is GIVEN 1,024 B and uses 900 of them, so a shrunk copy of it has its
#: own freed block standing free and claimed by nobody -- the grow-back case.
D_SIZE = 900
D_RESERVE = 1024


def container(*chunks):
    """An ffna type-2 container: magic, type byte, then (id, size, payload)."""
    out = bytearray(b"ffna" + bytes([2]))
    for cid, payload in chunks:
        out += struct.pack("<II", cid, len(payload)) + payload
    return bytes(out)


def reflist(*fids):
    """A reference-list chunk payload, by its own arithmetic.

    u32 count, then one record per id: the two-wchar file-id spelling followed
    by an explicit zero terminator word.
    """
    out = bytearray(struct.pack("<I", len(fids)))
    for fid in fids:
        out += struct.pack("<HH", *dependency_pair(fid)) + b"\x00\x00"
    return bytes(out)


def fa1(bases, seq_count=0):
    """A minimal 0xFA1 skeleton payload with the given per-node blk2C bases."""
    h = bytearray(0x58)
    struct.pack_into("<I", h, 0x00, SKEL_VERSION)
    struct.pack_into("<I", h, 0x18, seq_count)      # n18 = m_seqCount
    struct.pack_into("<I", h, 0x2C, len(bases))     # n2C = node count
    out = bytearray(h)
    for base in bases:
        out += struct.pack("<3f", *base) + struct.pack("<I", 0)
    out += b"\x00\x00\x00\x00\x00\x00" * len(bases)
    out += bytes(0x17 * seq_count)      # n18 sequence records, empty
    return bytes(out)


def pad_to(data, n):
    """A container padded out to exactly `n` bytes with a trailing junk chunk.

    The chunk walk still closes on the final byte, which is `archive.ffna_chunks`
    own assertion -- so a padded container is still a decodable one and the
    reference index still reads it.
    """
    body = len(data)
    if n == body:
        return data
    room = n - body - 8
    if room < 0:
        raise ValueError(f"cannot pad {body} B up to {n}")
    return data + struct.pack("<II", 0xFFF0, room) + b"\x77" * room


def self_crc_of(mft, count):
    """Row 3's own crc: the table either side of row 3's 24 bytes."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:count * ENTRY_SIZE]), acc)


def build_archive(path, rows):
    """An archive whose data rows are `rows` = [(file_ids, payload, flags, reserve)].

    `reserve` is what the row is GIVEN, which the MFT has no field for: it only
    moves where the NEXT row starts. That is the whole mechanism a grow-back
    depends on -- a row's entitlement survives a shrink in the geometry and
    nowhere else -- so the fixture has to be able to express it.
    """
    entry_count = FIRST_ROW + len(rows)
    mft_size = entry_count * ENTRY_SIZE
    idtable = b"".join(
        struct.pack("<II", fid, FIRST_ROW + i)
        for i, (fids, _p, _f, _r) in enumerate(rows) for fid in fids)

    extents = {ROW_HEADER: (0, 32), ROW_IDTABLE: (BLOCK, len(idtable))}
    payloads = {ROW_IDTABLE: idtable}
    off = BLOCK + max(1, -(-len(idtable) // BLOCK)) * BLOCK
    for i, (_fids, payload, _flags, reserve) in enumerate(rows):
        extents[FIRST_ROW + i] = (off, len(payload))
        payloads[FIRST_ROW + i] = payload
        want = max(len(payload), reserve or 0)
        off += max(1, -(-want // BLOCK)) * BLOCK
    mft_off = off
    buf = bytearray(mft_off + mft_size)

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, mft_off)
    struct.pack_into("<I", head, 0x18, mft_size)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head
    for row, payload in payloads.items():
        o = extents[row][0]
        buf[o:o + len(payload)] = payload

    fields = {ROW_HEADER: (0, 32, 3), ROW_IDTABLE: (BLOCK, len(idtable), 3),
              ROW_SELF: (mft_off, mft_size, 3)}
    for i, (_fids, payload, flags, _r) in enumerate(rows):
        fields[FIRST_ROW + i] = (extents[FIRST_ROW + i][0], len(payload), flags)

    mft = bytearray(mft_size)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, entry_count)
    for row, (o, size, flags) in fields.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[o:o + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         o, size, 0, flags, 0, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC,
                     self_crc_of(mft, entry_count))
    buf[mft_off:mft_off + mft_size] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


def rows_spec(d_payload=None, dup=None):
    """The population every section reads.

    A and B both link to C -- the planted reference the gate must FIND -- and
    both wear a bit-identical two-node rig, which is the real shared skeleton.
    A carries two plain spellings. Z1 and Z2 wear the degenerate all-zero one.
    D is reached by nothing and wears a rig nobody else does: the clean edit.
    `dup` adds a second file-id record for one id on a second row, which is the
    state a plan must refuse rather than resolve.
    """
    d = d_payload if d_payload is not None else pad_to(
        container((GEOMETRY, b"\xBB" * 8), (SKELETON, fa1(BASES3))), D_SIZE)
    a_fids = [FID_A, FID_A2] + ([dup] if dup else [])
    b_fids = [FID_B] + ([dup] if dup else [])
    return [
        (a_fids, container((FA8, reflist(FID_C)),
                           (FA5, reflist(FID_TEX)),
                           (SKELETON, fa1(BASES1, seq_count=3))), HEAD, 0),
        (b_fids, container((FA8, reflist(FID_C)),
                           (SKELETON, fa1(BASES1, seq_count=1))), HEAD, 0),
        ([FID_C], container((SKELETON, fa1(BASES2))), HEAD, 2048),
        ([FID_D], d, HEAD, D_RESERVE),
        ([FID_Z1], container((GEOMETRY, b"\xCC" * 8),
                             (SKELETON, fa1(BASES_ZERO))), HEAD, 0),
        ([FID_Z2], container((GEOMETRY, b"\xCC" * 8),
                             (SKELETON, fa1(BASES_ZERO))), HEAD, 0),
        ([FID_TEX], b"ATEX-ish bytes, not a model", PLAIN_FILE, 0),
    ]


# ------------------------------------------------------------------ plumbing

@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def use_vault(path):
    """Point the vault at `path` for the rest of the run.

    `vaultpath` memoizes its answer in a module global on the first call, so
    setting the environment variable alone is not enough -- the memo goes with
    it (test_datdelta.py's reading of the same problem).
    """
    os.makedirs(path, exist_ok=True)
    os.environ["RURIK_VAULT"] = path
    vaultpath._resolved = None
    return path


def refusal(fn, *a, **kw):
    """Run and return the refusal text, or "" if it did not refuse."""
    try:
        with quiet():
            fn(*a, **kw)
    except SystemExit as exc:
        return str(exc)
    return ""


class Ran:
    """The result of a call that was EXPECTED to succeed, plus what it printed.

    `value` is None when it refused instead, and `refused` is the text. This
    exists because three of the sabotages below turned a named `[FAIL]` into a
    traceback: a defect that makes a gate refuse something correct stops the
    run at whatever check comes next, and a test that only crashes has said the
    machine is unhappy rather than what broke. MEASURED here: the
    `canonical_id` sabotage ended the run at check 46 of 103 and scored ZERO
    reds against a defect two checks were pointed straight at.
    """

    __slots__ = ("value", "out", "refused")

    def __init__(self, value, out, refused):
        self.value = value
        self.out = out
        self.refused = refused

    def why(self, want=None):
        return line_of(self.refused, want) if self.refused else ""

    def edit(self, n, attr):
        """One field of the n-th planned edit, or None if there is no plan."""
        try:
            return getattr(self.value.edits[n], attr)
        except (AttributeError, IndexError, TypeError):
            return None


def ran(fn, *a, **kw):
    """Run something that should NOT refuse. -> Ran. Never raises."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return Ran(fn(*a, **kw), buf.getvalue(), "")
    except SystemExit as exc:
        return Ran(None, buf.getvalue(), str(exc) or "(refused, no message)")


def line_of(text, want=None, default="-- nothing was printed"):
    """The first line of `text` (or the first containing `want`). Never raises.

    A detail expression that raises turns a named `[FAIL]` into a nameless
    crash, and a test that only crashes has said the machine is unhappy rather
    than what broke.
    """
    lines = [ln for ln in (text or "").splitlines()
             if ln.strip() and (want is None or want in ln)]
    return (lines[0] if lines else default).strip()[:100]


def spill(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def blob(path):
    with open(path, "rb") as fh:
        return fh.read()


def row_bytes(path, row):
    """One row's stored bytes, or b"" if the archive will not open.

    Defensive for `Ran`'s reason: when a sabotage stops a build from happening
    the checks BELOW it should each go red naming their own subject, not
    disappear behind the first FileNotFoundError.
    """
    try:
        with Archive(path) as ar:
            return bytes(ar.raw(ar.row(row)))
    except (OSError, ValueError, struct.error):
        return b""


def health(path):
    """(preflight failures, bad crc rows) for `path`. Never raises."""
    try:
        chk, _f = datcheck.preflight(path)
        sweep = datcheck.crc_sweep(path)
    except (OSError, ValueError, KeyError, struct.error) as exc:
        return [f"{type(exc).__name__}: {exc}"], ["unreadable"], 0
    return ([c.name for c in chk if not c.ok], sweep["bad"], sweep["checked"])


def toml_edit(fid, compression=0, plain="payloads/p.bin", stored=None, ack=()):
    lines = ["[[edit]]",
             f"file_id = 0x{fid:X}",
             f"compression = {compression}",
             f'plain = "{plain}"']
    if stored:
        lines.append(f'stored = "{stored}"')
    lines.append("acknowledge_shared_with = ["
                 + ", ".join(f"0x{a:X}" for a in ack) + "]")
    return "\n".join(lines)


def write_manifest(path, name, active, retail, edits, refindex_path=None,
                   extra=""):
    body = ["[overlay]", f'name = "{name}"',
            f'active = "{active}"'.replace("\\", "/"),
            f'retail = "{retail}"'.replace("\\", "/")]
    if refindex_path:
        body.append(f'refindex = "{refindex_path}"'.replace("\\", "/"))
    if extra:
        body.append(extra)
    body += list(edits)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body) + "\n")
    return path


class World:
    """One temp directory holding a run dir, a manifest dir and a vault."""

    def __init__(self, tmp):
        self.tmp = tmp
        self.run = os.path.join(tmp, "run")
        self.man = os.path.join(tmp, "overlays")
        self.vault = use_vault(os.path.join(tmp, "vault"))
        os.makedirs(self.run, exist_ok=True)
        os.makedirs(os.path.join(self.man, "payloads"), exist_ok=True)
        self.retail = build_archive(os.path.join(self.run, "Gw.dat.retail"),
                                    rows_spec())
        self.active = os.path.join(self.run, "Gw.dat")
        self.reset_active()

    def reset_active(self):
        with open(self.retail, "rb") as src, open(self.active, "wb") as dst:
            dst.write(src.read())
        return self.active

    def payload(self, name, data):
        return spill(os.path.join(self.man, "payloads", name), data)

    def manifest(self, name, edits, refindex_path=None, retail=None,
                 active=None, extra=""):
        return write_manifest(
            os.path.join(self.man, f"{name}.toml"), name,
            active or "../run/Gw.dat", retail or "../run/Gw.dat.retail",
            edits, refindex_path=refindex_path, extra=extra)

    def index(self):
        with Archive(self.retail) as ar:
            return refindex.build(ar)


# ---------------------------------------------------------------------------

def section0(w):
    print("\n== section 0: the fixture, and what a manifest may not say ==")
    # THE FIXTURE MUST BE A HEALTHY ARCHIVE before anything measured off it
    # means a thing -- otherwise every refusal below could be the fixture.
    checks_, _facts = datcheck.preflight(w.retail)
    check(all(c.ok for c in checks_),
          f"the fixture archive passes all {len(checks_)} of datcheck's "
          "open-time rules, so nothing below is refusing the fixture",
          "; ".join(c.name for c in checks_ if not c.ok))
    sweep = datcheck.crc_sweep(w.retail)
    check(not sweep["bad"] and sweep["checked"] >= 8,
          f"and every one of its {sweep['checked']} checked rows carries the "
          "crc of its own stored bytes", f"bad: {sweep['bad']}")

    w.payload("p.bin", b"OVERLAY-D-" + b"\x11" * 190)
    good = w.manifest("clean", [toml_edit(FID_D)])
    m = load_manifest(good)
    check(m.name == "clean" and len(m.edits) == 1
          and m.edits[0].file_id == FID_D and m.edits[0].compression == 0,
          "a manifest parses into a name and one edit naming a file id")
    check(os.path.normcase(m.active) == os.path.normcase(
        os.path.abspath(w.active))
        and os.path.normcase(m.retail) == os.path.normcase(
            os.path.abspath(w.retail)),
          "and its paths resolve against the MANIFEST's own directory, never "
          "the shell's", f"{m.active} / {m.retail}")
    check(m.sha256 and len(m.sha256) == 64,
          "the manifest carries the sha256 of its own bytes, which is what a "
          "build record is matched against later")
    check(m.edits[0].data == m.edits[0].plain,
          "a compression-0 edit's stored bytes ARE its payload -- one file, "
          "not two that can differ")

    bad = w.manifest("nokey", [toml_edit(FID_D)], extra='refindx = "x.json"')
    msg = refusal(load_manifest, bad)
    check("unknown key" in msg and "refindx" in msg,
          "a misspelled [overlay] key is REFUSED, not ignored: `refindx` would "
          "leave the manifest naming no index and this tool would go and build "
          "one for fifteen minutes", line_of(msg, "unknown"))
    bad = w.manifest("badname", [toml_edit(FID_D)])
    with open(bad, "r+", encoding="utf-8") as fh:
        text = fh.read().replace('name = "badname"', 'name = "Bad Name"')
        fh.seek(0), fh.truncate(), fh.write(text)
    check("[a-z0-9-]+" in refusal(load_manifest, bad),
          "a name that is not [a-z0-9-]+ is refused at the door -- it becomes "
          "a directory and four filenames")
    same = write_manifest(os.path.join(w.man, "same.toml"), "same",
                          "../run/Gw.dat.retail", "../run/Gw.dat.retail",
                          [toml_edit(FID_D)])
    msg = refusal(load_manifest, same)
    check("SAME file" in msg and "first deploy destroys it" in msg,
          "active and retail naming one file is refused: the baseline a deploy "
          "is measured against cannot also be the deploy target",
          line_of(msg, "SAME"))
    dup = w.manifest("dupedit", [toml_edit(FID_D), toml_edit(FID_D)])
    check("Two edits of one row" in refusal(load_manifest, dup),
          "two [[edit]] blocks naming one file id are refused: they cannot "
          "both be the payload a reader gets back")
    nope = w.manifest("noedit", [])
    check("not one [[edit]]" in refusal(load_manifest, nope),
          "a manifest with no edits is refused -- there would be nothing to "
          "deploy")
    badcomp = w.manifest("badcomp", [toml_edit(FID_D, compression=3)])
    check("compression 3" in refusal(load_manifest, badcomp),
          "and a compression code the archive does not know is refused rather "
          "than written")
    both = w.manifest("both", [toml_edit(FID_D, compression=0,
                                         stored="payloads/p.bin")])
    msg = refusal(load_manifest, both)
    check("compression 0 and also names a `stored`" in msg,
          "a stored row naming BOTH a plain and a stored file is refused: only "
          "one of them can be written and nothing says which",
          line_of(msg, "stored"))
    gone = w.manifest("gone", [toml_edit(FID_D, plain="payloads/missing.bin")])
    check("cannot read" in refusal(load_manifest, gone),
          "a payload that is not on disk is named, not tripped over")

    live = write_manifest(os.path.join(w.man, "live.toml"), "live",
                          r"C:\gw\Gw.dat", "../run/Gw.dat.retail",
                          [toml_edit(FID_D)])
    msg = refusal(load_manifest, live)
    check("live install" in msg and "deploy loop" in msg,
          "naming the owner's own install as either archive is refused -- both "
          "of them take part in whole-file copies", line_of(msg, "Refusing"))
    return m


def section1():
    print("\n== section 1: fit, by arithmetic a reader can redo ==")
    # Hand-computed, block 512: a row of 900 B is GIVEN 1,024.
    f = fit_of(900, 900, 400, 512)
    check(f.verdict == IN_RESERVATION and f.cur_res == 1024
          and f.want_res == 512 and f.grow_to is None,
          "400 B into a row holding 900 fits its 1,024 B reservation: no gate "
          "runs and no grow is stated", repr(f))
    f = fit_of(900, 900, 1024, 512)
    check(f.verdict == IN_RESERVATION and f.want_res == 1024,
          "and so does exactly 1,024 B -- the boundary is the reservation, not "
          "the size field", repr(f))
    f = fit_of(900, 900, 1025, 512)
    check(f.verdict == TOO_BIG and f.want_res == 1536 and f.ceiling == 1024,
          "one byte more needs a second block and is a relocation", repr(f))
    f = fit_of(100, 900, 900, 512)
    check(f.verdict == GROW_BACK and f.cur_res == 512 and f.want_res == 1024
          and f.ceiling == 1024 and f.grow_to == 900,
          "a row SHRUNK to 100 B growing back to 900 is the middle cell, and "
          "the grow_to is the DONOR's 900 -- not the payload's length, not the "
          "reservation, and never invented to make the write fit", repr(f))
    f = fit_of(100, 900, 600, 512)
    check(f.verdict == GROW_BACK and f.grow_to == 900,
          "and a 600 B payload into that same shrunk row still states 900 -- "
          "the grow_to is the DONOR's size and not the payload's, which is the "
          "only pair of numbers that can tell those two rules apart", repr(f))
    f = fit_of(100, 900, 1025, 512)
    check(f.verdict == TOO_BIG and f.grow_to is None,
          "a shrunk row cannot be grown PAST what retail gave it: the "
          "entitlement is the donor's, not the geometry's", repr(f))
    check(fit_of(900, 900, 900, 512).ceiling
          == fit_of(900, 900, 900, 512).cur_res,
          "ON A FRESH RETAIL COPY THE MIDDLE CELL IS UNREACHABLE -- cur_size "
          "IS donor_size, so the ceiling IS the current reservation and the "
          "fit is binary. This is why section 5 exists")
    check(fit_of(0, 0, 1, 512).verdict == TOO_BIG
          and fit_of(0, 0, 1, 512).cur_res == 0,
          "a zero-length row reserves nothing, so any payload at all is a "
          "relocation out of it")
    f = fit_of(2048, 900, 1500, 512)
    check(f.verdict == IN_RESERVATION and f.ceiling == 2048,
          "and a row LARGER than its donor keeps its own reservation: "
          "max(cur, donor) never lets a stated entitlement shrink one",
          repr(f))
    check(fit_of(900, 900, 400, 512).cur_res
          == datwrite.reservation_for(900, 512),
          "the arithmetic is datwrite.reservation_for's, imported rather than "
          "re-derived -- there is one definition of a reservation in this tree")
    check(overlay.reservation_for is datwrite.reservation_for,
          "and it is literally the same function object, not a copy that can "
          "drift")


def section2(w):
    print("\n== section 2: resolving a file id, and refusing to guess ==")
    idx = w.index()
    w.payload("d200.bin", b"D200-" + b"\x22" * 195)
    good = load_manifest(w.manifest("clean2", [toml_edit(FID_D,
                                                        plain="payloads/d200.bin")]))
    r = ran(plan, good, index=idx, echo=False)
    check(r.value is not None and len(r.value.edits) == 1
          and r.edit(0, "row") == ROW_D,
          f"POSITIVE FIRST: file id 0x{FID_D:X} resolves to row {ROW_D} "
          "through the RAW table -- what the CLIENT can address",
          r.why() or f"got row {r.edit(0, 'row')}")
    check(r.edit(0, "fit") is not None
          and r.edit(0, "fit").verdict == IN_RESERVATION
          and r.edit(0, "donor_size") == D_SIZE,
          f"and the plan records the RETAIL donor's {D_SIZE} B beside the fit",
          repr(r.edit(0, "fit")))
    check(r.value is not None
          and r.value.retail_identity["mft_sha256"]
          and r.value.retail_identity["row_count"],
          "the plan carries the retail archive's identity, which is what makes "
          "a build record detectably stale later", r.why())
    out = "\n".join(overlay.format_plan(r.value)) if r.value else ""
    check(f"0x{FID_D:X}" in out and f"row {ROW_D}" in out
          and IN_RESERVATION in out,
          "and it prints as a plan a person can read before anything is copied",
          r.why())

    absent = load_manifest(w.manifest("absent", [toml_edit(FID_ABSENT,
                                                           plain="payloads/d200.bin")]))
    msg = refusal(plan, absent, index=idx, echo=False)
    check("no record" in msg and "exact 32-bit compare" in msg,
          "a file id no record names is refused, naming the client's own exact "
          "compare -- a bit-31 spelling and its plain form are two ids",
          line_of(msg))
    check("bit31.py" in msg,
          "and the refusal names the tool that lists the renamed ones")

    # SABOTAGE: two file-id records on one id, naming two rows. This is the
    # state `archive.file_id_table` resolves by taking whichever comes first.
    dup_retail = build_archive(os.path.join(w.run, "dup.dat"),
                               rows_spec(dup=555000))
    with Archive(dup_retail) as ar:
        from archive import file_id_table
        silent = file_id_table(ar, raw=True).get(555000)
    check(silent == ROW_A,
          "SABOTAGE PREMISE: with 555000 on two rows, file_id_table answers "
          f"row {ROW_A} and says nothing about the other", f"got {silent}")
    dup_man = load_manifest(write_manifest(
        os.path.join(w.man, "dup.toml"), "dup", "../run/Gw.dat",
        "../run/dup.dat", [toml_edit(555000, plain="payloads/d200.bin")]))
    msg = refusal(plan, dup_man, echo=False)
    check("2 records" in msg and f"[{ROW_A}, {ROW_B}]" in msg,
          "and the plan REFUSES it, naming both rows rather than landing the "
          "edit on whichever record sorts first", line_of(msg))

    w.payload("toobig.bin", b"X" * 1200)
    big = load_manifest(w.manifest("toobig", [toml_edit(FID_D,
                                                        plain="payloads/toobig.bin")]))
    msg = refusal(plan, big, index=idx, echo=False)
    check("relocation, not a replacement" in msg and "datmove.py" in msg,
          "a payload bigger than retail gave the row is refused as a "
          "relocation, naming datmove.py as the MANUAL remedy -- v1 does not "
          "relocate", line_of(msg))
    check("1024 B by RETAIL" in msg,
          "and it names the ceiling it measured rather than a rounded story",
          line_of(msg, "RETAIL"))

    # declaration_fault, wired: a comp-8 stream that decodes to something else.
    w.payload("plainA.bin", b"AAAA" * 40)
    w.payload("storedB.gwe", gwenc.encode(b"BBBB" * 40))
    lying = load_manifest(w.manifest(
        "lying", [toml_edit(FID_D, compression=8, plain="payloads/plainA.bin",
                            stored="payloads/storedB.gwe")]))
    msg = refusal(plan, lying, index=idx, echo=False)
    check("cannot be written as compression 8" in msg,
          "a compression-8 edit whose stream decodes to bytes other than its "
          "declared payload is REFUSED before anything is copied",
          line_of(msg))
    check("only refutation" in msg or "checksum rules" in msg,
          "and the refusal says why it is the only check there is: the entry "
          "crc is over the STORED bytes, so a wrong payload verifies",
          line_of(msg, "crc"))
    w.payload("storedA.gwe", gwenc.encode(b"AAAA" * 40))
    honest = load_manifest(w.manifest(
        "honest", [toml_edit(FID_D, compression=8, plain="payloads/plainA.bin",
                             stored="payloads/storedA.gwe")]))
    r = ran(plan, honest, index=idx, echo=False)
    e = r.edit(0, "edit")
    check(e is not None and e.compression == 8 and e.data != e.plain,
          "while the same edit with the MATCHING stream plans, stored bytes "
          "and payload being two different things", r.why())
    return idx


def section3(w, idx):
    print("\n== section 3: THE REFINDEX GATE, and its two tiers ==")
    w.payload("c.bin", b"NEW-C-" + b"\x33" * 60)
    naked = load_manifest(w.manifest("naked", [toml_edit(FID_C,
                                                         plain="payloads/c.bin")]))
    msg = refusal(plan, naked, index=idx, echo=False)
    check("2 co-consumer" in msg and f"0x{FID_A:X}" in msg
          and f"0x{FID_B:X}" in msg,
          f"POSITIVE CONTROL: A and B both link to C, and editing C is REFUSED "
          f"naming both -- the planted reference is FOUND before any pass "
          f"below is believed", line_of(msg))
    check("via FA8" in msg,
          "and each is named with the mechanism that reaches it")
    check("at least 2 referrer" in msg and "FA5/FA6/FA8/FAD/FAE" in msg,
          "the refusal prints refindex's OWN floor sentence verbatim, not a "
          "recomposed count -- the number alone reads as a census and this "
          "index cannot take one", line_of(msg, "at least 2"))
    check("BLIND SPOT" in msg,
          "including the blind spots, so a reader can see what the floor is a "
          "floor OF")
    check("acknowledge_shared_with = [" in msg
          and f"0x{FID_A:X}, 0x{FID_B:X}" in msg,
          "and it prints the exact line to paste into THIS edit -- a per-edit "
          "declaration, the way stored_lookalike_ok is per-call and not a "
          "global flag", line_of(msg, "acknowledge_shared_with = ["))

    half = load_manifest(w.manifest("half", [toml_edit(FID_C,
                                                       plain="payloads/c.bin",
                                                       ack=(FID_A,))]))
    msg = refusal(plan, half, index=idx, echo=False)
    check("1 co-consumer" in msg and f"0x{FID_B:X}" in msg
          and f"0x{FID_A:X} ({FID_A})" not in msg,
          "acknowledging ONE of two still refuses, naming only the one that is "
          "missing", line_of(msg))

    full = load_manifest(w.manifest("full", [toml_edit(FID_C,
                                                       plain="payloads/c.bin",
                                                       ack=(FID_A, FID_B))]))
    r = ran(plan, full, index=idx, echo=False)
    check(r.edit(0, "co_readers") == [FID_A, FID_B],
          "a complete acknowledgement PASSES, and the plan still records who "
          "the co-readers are", r.why() or f"got {r.edit(0, 'co_readers')}")

    # AMENDMENT 1: every spelling of a row is one acknowledgement.
    other = load_manifest(w.manifest("other", [toml_edit(FID_C,
                                                         plain="payloads/c.bin",
                                                         ack=(FID_A2, FID_B))]))
    r2 = ran(plan, other, index=idx, echo=False)
    check(r2.edit(0, "co_readers") == [FID_A, FID_B],
          f"and so does the SAME declaration written in row {ROW_A}'s OTHER "
          f"spelling 0x{FID_A2:X}: both sides go through "
          f"refindex.canonical_id, so a complete declaration is never reported "
          f"as incomplete", r2.why() or f"got {r2.edit(0, 'co_readers')}")
    check(refindex.canonical_id(idx, FID_A2) == FID_A
          and refindex.canonical_id(idx, FID_A) == FID_A,
          f"(0x{FID_A2:X} and 0x{FID_A:X} are one row and normalise to one id, "
          "which is what makes that possible)")
    alias_half = load_manifest(w.manifest("aliashalf",
                                          [toml_edit(FID_C,
                                                     plain="payloads/c.bin",
                                                     ack=(FID_A2,))]))
    msg = refusal(plan, alias_half, index=idx, echo=False)
    check("1 co-consumer" in msg and f"0x{FID_B:X}" in msg
          and f"0x{FID_A:X} ({FID_A})" not in msg,
          f"and the alias 0x{FID_A2:X} SATISFIES A's half of the declaration "
          f"while B's is still missing -- normalising is not a blanket pass, "
          f"it resolves each id to the row it names", line_of(msg))

    # TIER, half one: a real shared rig must be acknowledged.
    w.payload("a.bin", b"NEW-A-" + b"\x44" * 60)
    skel = load_manifest(w.manifest("skel", [toml_edit(FID_A,
                                                       plain="payloads/a.bin")]))
    msg = refusal(plan, skel, index=idx, echo=False)
    check(f"0x{FID_B:X}" in msg and "blk2C base array" in msg,
          "editing A is refused for a co-WEARER: B's blk2C base array is "
          "bit-identical, so editing one rig edits both (studies/unitmodels "
          "3.11, six of seven pairs at 0.0000 u)", line_of(msg, "blk2C"))
    check("at least 1 co-wearer" in msg,
          "and the skeleton answer's own floor sentence is printed too, naming "
          "ITS mechanism rather than the reference one",
          line_of(msg, "co-wearer"))
    ok_skel = load_manifest(w.manifest("skelok", [toml_edit(FID_A,
                                                            plain="payloads/a.bin",
                                                            ack=(FID_B,))]))
    r3 = ran(plan, ok_skel, index=idx, echo=False)
    check(r3.edit(0, "co_wearers") == [FID_B],
          "acknowledged, it plans", r3.why())

    # TIER, half two: a CONTENTLESS key must not demand anything.
    w.payload("z.bin", b"NEW-Z-" + b"\x55" * 20)
    zed = load_manifest(w.manifest("zed", [toml_edit(FID_Z1,
                                                     plain="payloads/z.bin")]))
    rz = ran(plan, zed, index=idx, echo=True)
    check(rz.edit(0, "co_wearers") == [FID_Z2],
          f"Z1 and Z2 DO group -- the bit-identity criterion is not weakened "
          f"-- and the plan records the co-wearer",
          rz.why() or f"got {rz.edit(0, 'co_wearers')}")
    joined = "\n".join(rz.edit(0, "notes") or [rz.why()])
    check("EVERY base in that array is zero" in joined,
          "but the edit is NOT refused: the shared key is one node at "
          "(-0.0,-0.0,-0.0) and carries no pose, so those heads group because "
          "none of them has one", line_of(joined))
    check("NOT required in acknowledge_shared_with" in joined,
          "and the note says so in as many words -- on retail this group is "
          "572 heads, and demanding 571 acknowledgements teaches an operator "
          "to paste whatever the tool printed", line_of(joined, "NOT required"))
    check("contentless" in "\n".join(overlay.format_plan(rz.value))
          if rz.value else False,
          "the plan prints it, so the tiering is visible rather than silent",
          rz.why())

    stale = load_manifest(w.manifest("stale", [toml_edit(FID_D,
                                                         plain="payloads/d200.bin",
                                                         ack=(FID_ABSENT,))]))
    rs = ran(plan, stale, index=idx, echo=False)
    check(any("not a co-consumer" in n for n in (rs.edit(0, "notes") or [])),
          "an acknowledgement of an id that is not a co-consumer is a NOTE and "
          "not a refusal -- worth checking for a typo, not worth blocking on",
          rs.why())


def damaged_rows():
    """`rows_spec`, with A's and B's container MAGIC damaged and nothing else.

    Their FA8 lists still name C, byte for byte; the archive is still healthy
    (the MFT records each payload's own crc, so a damaged payload is a
    consistent one); and `refindex` walks both heads, indexes neither, and
    records both in `index.problems`. What `who_reads(C)` then answers is the
    empty list -- with the stamp green, the archive green and the index current.
    That is the state this section exists for.
    """
    out = []
    for i, (fids, payload, flags, reserve) in enumerate(rows_spec()):
        if i in (0, 1):
            payload = b"ffnX" + payload[4:]
        out.append((fids, payload, flags, reserve))
    return out


def section3b(w, idx):
    print("\n== section 3b: an index that could not SEE it is not an empty "
          "answer ==")
    dmg = build_archive(os.path.join(w.run, "damaged.dat"), damaged_rows())
    bad_rules, bad_crc, checked = health(dmg)
    check(not bad_rules and not bad_crc and checked >= 8,
          "PREMISE: the damaged archive is HEALTHY -- all ten open-time rules "
          f"and every one of {checked} crc rows -- so nothing below is refusing "
          "a broken fixture", f"{bad_rules}; {bad_crc}")
    with Archive(dmg) as ar:
        didx = refindex.build(ar)
    check(len(didx.heads) == 4 and len(didx.problems) == 2
          and not didx.partial and didx.walked == 6,
          "PREMISE: refindex walks all 6 heads, indexes 4, and records both "
          "unreadable containers in index.problems -- it is CURRENT and it is "
          "NOT partial", f"{len(didx.heads)} heads, "
                         f"{len(didx.problems)} problems, walked {didx.walked}")
    answer = refindex.who_reads(didx, FID_C)
    check(list(answer) == [],
          f"AND THE WHOLE POINT: A and B still carry real FA8 lists naming C, "
          f"and who_reads(0x{FID_C:X}) answers EMPTY. Stamp green, archive "
          f"green, index current -- and the answer that would clear the gate is "
          f"the one refindex calls its one unacceptable output", str(list(answer)))

    w.payload("c2.bin", b"NEW-C2-" + b"\x99" * 60)
    blind = load_manifest(write_manifest(
        os.path.join(w.man, "blind.toml"), "blind", "../run/Gw.dat",
        "../run/damaged.dat", [toml_edit(FID_C, plain="payloads/c2.bin")]))
    msg = refusal(plan, blind, index=didx, echo=False)
    check("could not read 2 container(s) or list(s)" in msg
          and "accept_unread = 2" in msg,
          "so the plan REFUSES the edit: the index's blind spot is declared by "
          "COUNT before any answer off it is trusted, and the count is the one "
          "the index measured", line_of(msg))
    check(f"row {ROW_A}" in msg and f"row {ROW_B}" in msg and "ffnX" in msg,
          "and it names the rows it could not read and why, so 'look at them' "
          "is an instruction a person can follow", line_of(msg, "ffnX"))
    check("count and not a flag" in msg,
          "stating why it is a number: a `true` would go on covering the blind "
          "spot as it grew, where a count comes back when it moves",
          line_of(msg, "count and not"))

    declared = load_manifest(write_manifest(
        os.path.join(w.man, "blindok.toml"), "blindok", "../run/Gw.dat",
        "../run/damaged.dat", [toml_edit(FID_C, plain="payloads/c2.bin")],
        extra="accept_unread = 2"))
    r = ran(plan, declared, index=didx, echo=False)
    check(r.edit(0, "row") == ROW_C,
          "declared, the same edit plans -- the gate refuses an UNDECLARED "
          "blind spot, not a known one", r.why() or f"row {r.edit(0, 'row')}")
    moved = load_manifest(write_manifest(
        os.path.join(w.man, "blindmoved.toml"), "blindmoved", "../run/Gw.dat",
        "../run/damaged.dat", [toml_edit(FID_C, plain="payloads/c2.bin")],
        extra="accept_unread = 1"))
    msg = refusal(plan, moved, index=didx, echo=False)
    check("declares accept_unread = 1" in msg and "could not read 2" in msg,
          "and a declaration that no longer matches is refused BOTH ways: the "
          "set that cannot be seen is not the set that was looked at",
          line_of(msg))

    # THE OTHER HALF OF THE SAME DEFECT, and the contrast that names it.
    w.payload("tex.bin", b"TEX-" + b"\x21" * 100)
    tex_blind = load_manifest(write_manifest(
        os.path.join(w.man, "blindtex.toml"), "blindtex", "../run/Gw.dat",
        "../run/damaged.dat", [toml_edit(FID_TEX, plain="payloads/tex.bin")],
        extra="accept_unread = 2"))
    rt = ran(plan, tex_blind, index=didx, echo=False)
    joined = "\n".join(rt.edit(0, "notes") or [rt.why()])
    check(f"holds no record of row {ROW_TEX}" in joined,
          f"an edit the index resolves to NO ROW says so out loud -- refindex "
          f"cannot tell 'this archive does not hold that id' from 'nothing "
          f"references that row', and this caller resolved the id against the "
          f"archive first, so it can", line_of(joined))
    self_blind = load_manifest(write_manifest(
        os.path.join(w.man, "blindself.toml"), "blindself", "../run/Gw.dat",
        "../run/damaged.dat", [toml_edit(FID_A, plain="payloads/tex.bin")],
        extra="accept_unread = 2"))
    rsb = ran(plan, self_blind, index=didx, echo=False)
    joined = "\n".join(rsb.edit(0, "notes") or [rsb.why()])
    check(f"row {ROW_A} is ITSELF one of the 2" in joined
          and "never 'nobody else wears it'" in joined,
          f"and an edit of a row that is ITSELF unreadable says so: it carries "
          f"no skeleton hash, joins no sharing group, and its empty co-wearer "
          f"answer means 'not indexed' -- B wears A's rig bit-identically and "
          f"this index cannot see either of them", line_of(joined, "ITSELF"))

    tex_seen = load_manifest(w.manifest(
        "texseen", [toml_edit(FID_TEX, plain="payloads/tex.bin")]))
    msg = refusal(plan, tex_seen, index=idx, echo=False)
    check(f"0x{FID_A:X}" in msg and "via FA5" in msg,
          "THE CONTRAST: the same edit against the archive whose containers DO "
          "read is refused, because A's FA5 list names that texture. The empty "
          "answer above was the damage and not the truth, and one accept_unread "
          "is the whole difference", line_of(msg))

    # A PARTIAL INDEX. It clears the stamp, round-trips through JSON, and
    # cannot answer anything.
    with Archive(w.retail) as ar:
        part = refindex.build(ar, rows=[ROW_D])
    check(part.partial and part.walked == 1 and len(part.heads) == 1,
          "PREMISE: a spot-check index walked ONE head of six and is marked "
          "partial", f"walked {part.walked}, partial {part.partial}")
    clean = load_manifest(w.manifest(
        "partialgate", [toml_edit(FID_D, plain="payloads/d200.bin")]))
    full = ran(plan, clean, index=idx, echo=False)
    check(full.edit(0, "row") == ROW_D,
          "PREMISE: the FULL index passes this exact edit, so what follows is "
          "about the index and not about the edit", full.why())
    msg = refusal(plan, clean, index=part, echo=False)
    check("PARTIAL" in msg and "floor of a floor" in msg,
          "and the PARTIAL index REFUSES it: a floor computed over one head of "
          "six is not a floor anything can rest on", line_of(msg))
    check("no acknowledgement for this one" in msg,
          "with no acknowledgement offered -- a subset was a spot check and a "
          "gate is not", line_of(msg, "acknowledgement"))
    pj = refindex.save(part, os.path.join(w.tmp, "partial.refindex.json"))
    named = load_manifest(w.manifest(
        "partialnamed", [toml_edit(FID_D, plain="payloads/d200.bin")],
        refindex_path=os.path.relpath(pj, w.man)))
    check("PARTIAL" in refusal(plan, named, echo=False),
          "and so is one SAVED and NAMED by a manifest: it passes the stamp, "
          "survives the JSON round trip, and is still a floor of a floor")
    waive = load_manifest(w.manifest(
        "partialack", [toml_edit(FID_D, plain="payloads/d200.bin")],
        extra="accept_unread = 0"))
    check("PARTIAL" in refusal(plan, waive, index=part, echo=False),
          "and accept_unread does not waive it: the two blind spots are "
          "different and only one of them has a number to look at")

    # THE STAMP DOES NOT COVER THE FILE-ID TABLE'S CONTENT.
    data = bytearray(blob(w.retail))
    off = BLOCK + 4 * 8                      # the (FID_D, ROW_D) record
    check(struct.unpack_from("<II", data, off) == (FID_D, ROW_D),
          f"PREMISE: record 4 of the file-id table names 0x{FID_D:X} -> row "
          f"{ROW_D}", str(struct.unpack_from("<II", data, off)))
    struct.pack_into("<I", data, off + 4, ROW_C)
    poked = spill(os.path.join(w.run, "poked.dat"), bytes(data))
    with Archive(poked) as ar:
        stamp = refindex.stamp_of(ar)
    check(all(stamp[k] == idx.stamp[k] for k in refindex.IDENTITY_FIELDS),
          "PREMISE: pointing that record at another row leaves the MFT stamp "
          "IDENTICAL -- a payload edited in place without its row's crc is the "
          "one state refindex.check_stamp says outright it cannot see",
          str([k for k in refindex.IDENTITY_FIELDS if stamp[k] != idx.stamp[k]]))
    _r, poked_crc, _n = health(poked)
    check(len(poked_crc) == 1,
          "(datcheck --crc-sweep DOES see it, on exactly one row, which is why "
          "the refusal names that verb rather than shrugging)",
          f"bad rows: {[b[0] for b in poked_crc]}")
    pm = load_manifest(write_manifest(
        os.path.join(w.man, "poked.toml"), "poked", "../run/Gw.dat",
        "../run/poked.dat", [toml_edit(FID_D, plain="payloads/d200.bin")]))
    msg = refusal(plan, pm, index=idx, echo=False)
    check("disagree" in msg and f"row {ROW_D}" in msg and f"row {ROW_C}" in msg,
          "and the plan REFUSES the disagreement, naming both rows: the index "
          "would have answered about row 19 while the write landed on row 18",
          line_of(msg))
    check("--crc-sweep" in msg,
          "naming the one tool that can see the state underneath it",
          line_of(msg, "crc-sweep"))


def section4(w, idx):
    print("\n== section 4: the saved index, and what a stale one may not do ==")
    out = os.path.join(w.tmp, "retail.refindex.json")
    refindex.save(idx, out)
    named = load_manifest(w.manifest("named", [toml_edit(FID_D,
                                                         plain="payloads/d200.bin")],
                                     refindex_path=os.path.relpath(out, w.man)))
    r = ran(plan, named, echo=True)
    check(r.edit(0, "row") == ROW_D and "refindex <-" in r.out,
          "a manifest naming a saved index LOADS it instead of spending 15 "
          "minutes rebuilding one", r.why() or line_of(r.out, "refindex"))
    check("15.5 minutes" not in r.out,
          "and does not print the build-cost warning it did not incur")

    ru = ran(plan, load_manifest(w.manifest(
        "unnamed", [toml_edit(FID_D, plain="payloads/d200.bin")])), echo=True)
    text = ru.out
    check("names no refindex" in text and "15.5 minutes" in text
          and "--build-json" in text,
          "with no index named, the cost of building one is printed BEFORE the "
          "wait, with the command that avoids it next time",
          line_of(text, "15.5"))

    # A STALE INDEX MUST NOT ANSWER. One payload byte, same lengths.
    moved = build_archive(os.path.join(w.run, "moved.dat"),
                          rows_spec(d_payload=pad_to(
                              container((GEOMETRY, b"\xBB" * 8),
                                        (SKELETON, fa1(BASES2))), D_SIZE)))
    stale_man = load_manifest(write_manifest(
        os.path.join(w.man, "stalix.toml"), "stalix", "../run/Gw.dat",
        "../run/moved.dat", [toml_edit(FID_D, plain="payloads/d200.bin")],
        refindex_path=os.path.relpath(out, w.man)))
    msg = refusal(plan, stale_man, echo=False)
    check("REFUSING" in msg and "mft_sha256" in msg,
          "an index built from a DIFFERENT archive is refused against this "
          "one, naming the field that differs -- `refindex.load` is always "
          "called WITH the archive", line_of(msg))
    handed = refusal(plan, stale_man, index=idx, echo=False)
    check("REFUSING" in handed and "mft_sha256" in handed,
          "and so is one handed in directly: a caller passing an index does "
          "not get to skip the stamp", line_of(handed))

    print("\n== section 4b: build, and the record it leaves ==")
    m = load_manifest(w.manifest("stage", [toml_edit(FID_D,
                                                     plain="payloads/d200.bin")]))
    rb = ran(build, m, index=idx, echo=False)
    doc = rb.value or {"staged": os.path.join(w.tmp, "no-build"),
                       "rows": {}, "retail_rows": {}, "file_ids": {}}
    stage = doc["staged"]
    check(os.path.isfile(stage)
          and overlay._inside(stage, w.vault),
          "the staged copy lands under the vault and nowhere else -- it is a "
          "retail archive with one row changed, which is ArenaNet's bytes "
          "nearly all the way through", stage)
    check(row_bytes(stage, ROW_D) == blob(os.path.join(
        w.man, "payloads", "d200.bin")),
          "and row D of it holds exactly the payload the manifest declared",
          f"{len(row_bytes(stage, ROW_D))} B")
    check(row_bytes(stage, ROW_C) == row_bytes(w.retail, ROW_C)
          and os.path.getsize(stage) == os.path.getsize(w.retail),
          "every row the manifest did not name is retail's, byte for byte, and "
          "the file did not grow")
    check(doc["rows"].get(str(ROW_D), [None])[0] == 200
          and doc["retail_rows"].get(str(ROW_D), [None])[0] == D_SIZE
          and doc["rows"] != doc["retail_rows"],
          "the record fingerprints BOTH sides of every touched row, so 'is "
          "retail deployed?' and 'is this profile deployed?' are two questions "
          "with two answers", f"{doc['rows']} vs {doc['retail_rows']}")
    check(doc["file_ids"].get(str(ROW_D)) == FID_D,
          "and it records which file id named that row, because a row number "
          "is a position in one archive's table and the client moves rows",
          rb.why())
    bad_rules, bad_crc, checked = health(stage)
    check(not bad_crc,
          f"the staged archive still passes a full crc sweep over {checked} "
          f"rows -- the write fixed the entry crc and the MFT's own",
          f"bad: {bad_crc}")
    check(not bad_rules,
          "and all ten open-time rules", "; ".join(map(str, bad_rules)))
    check(os.path.isfile(overlay.journal_path(m)),
          "a journal sits beside it: every byte changed is recorded with its "
          "previous value, so the staged copy is revertible without a re-cut")

    # NOTHING TO DEPLOY looks exactly like a successful deploy.
    w.payload("same.bin", row_bytes(w.retail, ROW_D))
    noop = load_manifest(w.manifest("noop", [toml_edit(FID_D,
                                                       plain="payloads/same.bin")]))
    msg = refusal(build, noop, index=idx, echo=False)
    check("nothing here to deploy" in msg,
          "a build whose payload IS retail's bytes is refused: it changed "
          "nothing and looks exactly like a build that worked, right up until "
          "the experiment produces a null nobody can explain", line_of(msg))

    # SABOTAGE: hand-edit the record after the build.
    fp = overlay.fingerprints_path(m)
    doctored = json.loads(blob(fp).decode("utf-8")) if os.path.isfile(fp) \
        else {"rows": {}, "retail_rows": {}}
    doctored["rows"][str(ROW_D)] = doctored.get("retail_rows", {}).get(
        str(ROW_D), [0, "0", 0])
    with open(fp, "w", encoding="utf-8") as fh:
        json.dump(doctored, fh)
    msg = refusal(deployed_state, m)
    check("does not match its own digest" in msg,
          "SABOTAGE: a fingerprint edited after the build is caught by the "
          "record's own digest -- these rows are what --status reads the ACTIVE "
          "archive's identity out of", line_of(msg))
    check("--build" in msg,
          "and the refusal names the verb that fixes it")
    ran(build, m, index=idx, echo=False)
    return m


def state_of(m):
    """`deployed_state`, with a refusal turned into a readable string.

    Same reason as `Ran`: the state oracle is asked eleven times below, and one
    of those calls raising would take the other ten with it.
    """
    r = ran(deployed_state, m)
    return r.value if r.value is not None else f"REFUSED: {r.why()}"


def section5(w, idx, m):
    print("\n== section 5: the grow-back, against a row that was shrunk ==")
    # The staged copy of a profile that has already been written once: row D's
    # size field says 100 while its own 1,024 B of blocks stand free. This is
    # the state a fresh retail copy CANNOT be in, which is why the middle cell
    # of fit_of needs its own fixture.
    shrunk = build_archive(os.path.join(w.tmp, "shrunk.dat"),
                           rows_spec(d_payload=b"S" * 100))
    with Archive(shrunk) as ar:
        e = ar.row(ROW_D)
        nxt = ar.row(ROW_Z1)
        check(e.size == 100 and nxt.offset - e.offset == D_RESERVE,
              f"FIXTURE PREMISE: row {ROW_D} holds 100 B and the next row does "
              f"not start for {D_RESERVE} -- the row's own freed blocks, "
              f"claimed by nobody", f"size {e.size}, gap {nxt.offset - e.offset}")
    w.payload("d900.bin", b"D900-" + b"\x66" * (D_SIZE - 5))
    big = load_manifest(w.manifest("grow", [toml_edit(FID_D,
                                                      plain="payloads/d900.bin")]))
    rp = ran(plan, big, index=idx, echo=False)
    check(rp.edit(0, "fit") is not None
          and rp.edit(0, "fit").verdict == IN_RESERVATION,
          f"against RETAIL the plan says in-reservation ({D_SIZE} B into a row "
          f"holding {D_SIZE})", rp.why() or repr(rp.edit(0, "fit")))
    jrn = os.path.join(w.tmp, "grow.journal.json")
    ra = ran(apply_edits, shrunk, rp.value, jrn, echo=True)
    verdicts = ra.value or {}
    check(verdicts.get(ROW_D) == GROW_BACK,
          "but applied to the SHRUNK archive it is a grow-back: the fit is "
          "recomputed against the file being written, never taken from the "
          "plan", ra.why() or f"got {verdicts}")
    check("annexing" in ra.out,
          "and datwrite annexed the row's own blocks rather than refusing it "
          "as a relocation", line_of(ra.out, "annex"))
    check(row_bytes(shrunk, ROW_D) == blob(os.path.join(w.man, "payloads",
                                                        "d900.bin")),
          f"the full {D_SIZE} B are on disk and read back through the archive",
          f"{len(row_bytes(shrunk, ROW_D))} B")
    bad_rules, bad_crc, _n = health(shrunk)
    check(not bad_crc and not bad_rules,
          "and the grown archive still passes the crc sweep and all ten rules "
          "-- no two rows share a block",
          f"bad {bad_crc}; " + "; ".join(map(str, bad_rules)))
    doc = json.loads(blob(jrn).decode("utf-8")) if os.path.isfile(jrn) \
        else {"edits": []}
    check(any(rec["length"] == D_RESERVE for rec in doc["edits"]),
          f"the journal records the WHOLE {D_RESERVE} B reservation, so a "
          "revert puts back the annexed blocks too",
          f"lengths {[r['length'] for r in doc['edits']]}")


def section6(w, idx, m):
    print("\n== section 6: three-valued state, and what may write to ACTIVE ==")
    w.reset_active()
    check(state_of(m) == overlay.STATE_RETAIL,
          "a fresh copy of retail reads as 'retail' on the rows this profile "
          "owns", state_of(m))
    msg = refusal(deploy, m)
    check("--yes" in msg and state_of(m) == overlay.STATE_RETAIL,
          "--deploy without --yes refuses and writes nothing: consent is a "
          "flag because these run non-interactive", line_of(msg))
    rd = ran(deploy, m, yes=True, echo=True)
    check(rd.value == overlay.STATE_RETAIL,
          "with --yes it deploys, and the premise it recorded is the one it "
          "measured beforehand", rd.why() or str(rd.value))
    check("REPLACING" in rd.out and "SHARED" in rd.out,
          "printing a banner that says the ACTIVE archive is shared with other "
          "sessions", line_of(rd.out, "SHARED"))
    check(state_of(m) == m.name,
          f"and the state now reads {m.name!r}, from ACTIVE's own bytes",
          state_of(m))
    check(row_bytes(w.active, ROW_D) == row_bytes(
        overlay.staged_path(m), ROW_D) != b"",
          "the deployed archive carries the staged bytes on the touched row")
    check(os.path.isfile(overlay.prelaunch_snapshot_path(m))
          and os.path.isfile(overlay.prelaunch_fingerprints_path(m)),
          "a pre-launch snapshot and row record are written beside the staged "
          "copy -- a post-flight without its before-image is not a check")
    again = ran(deploy, m, yes=True, echo=False).value
    check(again == m.name,
          "re-deploying the same profile is allowed and says so: the premise "
          "is three-valued, and 'this profile already' is one of the three",
          again)

    # NEITHER: something else is in the archive.
    with quiet():
        w2 = datwrite.Writer(w.active, os.path.join(w.tmp, "third.journal.json"))
        try:
            w2.replace(ROW_D, b"THIRD-" + b"\x77" * 100)
        finally:
            w2.close()
    state = state_of(m)
    check(state.startswith(overlay.STATE_OTHER) and f"row {ROW_D}" in state,
          "a third payload on a touched row reads as neither retail nor this "
          "profile, and the answer NAMES the row that disagrees", state)
    msg = refusal(deploy, m, yes=True)
    check("neither retail nor" in msg and "unscoreable" in msg,
          "and a deploy onto it is a HARD refusal: an arm recorded on top of "
          "an unknown archive cannot be scored afterwards", line_of(msg))
    check("--retail" in msg,
          "naming the verb that makes the state known again", line_of(msg,
                                                                      "--retail"))
    check("--yes" in refusal(restore_retail, m),
          "--retail needs --yes too")
    ran(restore_retail, m, yes=True, echo=False)
    check(state_of(m) == overlay.STATE_RETAIL
          and blob(w.active) == blob(w.retail),
          "and it puts the whole baseline back, byte for byte -- no premise "
          "measured, because its job is to MAKE the state known")


def section7(w, idx, m):
    print("\n== section 7: the post-flight, and the moment it is measured "
          "against ==")
    snap = overlay.prelaunch_snapshot_path(m)
    fprint = overlay.prelaunch_fingerprints_path(m)
    # THE MEASURED REGRESSION, with no client anywhere near it. Section 6 ended
    # in --retail, which rewrote every touched row; before this was fixed the
    # post-flight compared ACTIVE against the BUILD record and reported those
    # bytes as "the client wrote to a row this overlay owns".
    check(not os.path.isfile(snap) and not os.path.isfile(fprint),
          "--retail DELETES the before-image rather than leaving one that is "
          "now untrue: it replaced the whole archive, so every touched row "
          "differs from what the deploy recorded", f"{snap}")
    msg = refusal(verify_after, m)
    check("no pre-launch snapshot" in msg and "not a check" in msg,
          "so the post-flight REFUSES. build -> deploy -> retail -> "
          "verify-after is a sequence with no client in it, and the only "
          "honest answer to it is that there is nothing to post-flight",
          line_of(msg))

    ran(deploy, m, yes=True, echo=False)
    check(os.path.isfile(snap) and os.path.isfile(fprint),
          "a deploy writes both halves of the image back", f"{fprint}")
    rb = ran(build, m, index=idx, echo=True)
    check(rb.value is not None and not os.path.isfile(snap)
          and not os.path.isfile(fprint) and "now untrue" in rb.out,
          "and a successful --build deletes them too, saying which files it "
          "removed: the image is an image OF a staged copy that has just been "
          "replaced", rb.why() or line_of(rb.out, "untrue"))
    msg = refusal(verify_after, m)
    check("no pre-launch snapshot" in msg,
          "so a post-flight after a re-build refuses, instead of comparing the "
          "live archive against the NEW build record and attributing the "
          "difference to the client", line_of(msg))

    ran(deploy, m, yes=True, echo=False)
    rv = ran(verify_after, m, echo=False)
    out = rv.value or {}
    check(out.get("unchanged") and not out.get("our_rows_changed")
          and not out.get("preflight_failed") and out.get("crc_bad") == 0,
          "straight after a deploy, nothing has changed and nothing is wrong",
          rv.why() or f"{out.get('changed_rows')} changed, "
                      f"{out.get('crc_bad')} bad crc")
    check(out.get("before_image") == fprint and out.get("deployed"),
          "and the result NAMES the before-image it was measured against, so "
          "the number cannot be read as being about some other deploy",
          f"{out.get('before_image')} @ {out.get('deployed')}")

    # THE TWO HALVES MUST DESCRIBE ONE DEPLOY.
    datcheck.write_snapshot(w.retail, snap)
    msg = refusal(verify_after, m)
    check("do not describe one deploy" in msg and "sha256" in msg,
          "a snapshot replaced under the record is refused: half of one deploy "
          "and half of another is a moment that never existed", line_of(msg))
    ran(deploy, m, yes=True, echo=False)
    doc = json.loads(blob(fprint).decode("utf-8"))
    doc["rows"] = dict(doc.get("retail_rows") or {})
    with open(fprint, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    msg = refusal(verify_after, m)
    check("does not match its own digest" in msg,
          "and a hand-edited before-image is caught by its own digest, the way "
          "the build record already was -- it is read as the truth about what "
          "the archive WAS", line_of(msg))
    ran(deploy, m, yes=True, echo=False)

    # A SIMULATED CLIENT WRITE, on a row this profile owns.
    with quiet():
        w2 = datwrite.Writer(w.active, os.path.join(w.tmp, "sim.journal.json"))
        try:
            w2.replace(ROW_D, b"CLIENT-WROTE-HERE" + b"\x88" * 50)
        finally:
            w2.close()
    rv = ran(verify_after, m, echo=True)
    out = rv.value or {}
    check(out.get("unchanged") is False and out.get("changed_rows", 0) >= 1,
          "a write to the archive after the snapshot is detected as a changed "
          "MFT row", rv.why() or f"{out.get('changed_rows')} changed")
    changed = out.get("our_rows_changed") or []
    check([r["row"] for r in changed] == [ROW_D]
          and ROW_D in (out.get("our_rows_in_diff") or []),
          f"and it is named as one of THIS overlay's rows -- row {ROW_D} was "
          f"{changed[0]['was'] if changed else '?'} and is not any more",
          f"got {changed}")
    check(not out.get("preflight_failed") and out.get("crc_bad") == 0,
          "while the archive itself is still structurally healthy: 'the client "
          "wrote here' and 'the archive is broken' are two different findings",
          rv.why())


def section8(w, m):
    print("\n== section 8: the CLI ==")
    path = m.path
    with quiet() as buf:
        rc = overlay.main(["--status", path])
    check(rc == 0 and "deployed state:" in buf.getvalue(),
          "--status prints what is deployed, read from ACTIVE's bytes",
          f"rc {rc}")
    with quiet() as buf:
        rc = overlay.main(["--plan", path])
    check(rc == 0 and f"row {ROW_D}" in buf.getvalue()
          and "at least" in buf.getvalue(),
          "--plan prints the resolved rows and the gate's floor sentences",
          f"rc {rc}")
    with quiet() as buf:
        rc = overlay.main(["--deploy", path])
    check(rc == 2 and "--yes" in buf.getvalue(),
          "--deploy without --yes exits 2 with the refusal, never 0", f"rc {rc}")
    with quiet() as buf:
        rc = overlay.main(["--plan", path, "--status", path])
    check(rc == 2 and "exactly one verb" in buf.getvalue(),
          "two verbs in one invocation are refused: the second one's premise "
          "would depend on the first", f"rc {rc}")
    with quiet() as buf:
        rc = overlay.main([])
    check(rc == 2 and "exactly one verb" in buf.getvalue(),
          "and so is none", f"rc {rc}")
    with quiet() as buf:
        rc = overlay.main(["--plan", os.path.join(w.tmp, "no-such.toml")])
    check(rc == 2 and "cannot read" in buf.getvalue(),
          "a manifest that is not there exits 2, never 0 with an empty plan",
          f"rc {rc}")


def main():
    was = os.environ.get("RURIK_VAULT")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp)
            section0(w)
            section1()
            idx = section2(w)
            section3(w, idx)
            section3b(w, idx)
            m = section4(w, idx)
            section5(w, idx, m)
            section6(w, idx, m)
            section7(w, idx, m)
            section8(w, m)
    finally:
        if was is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = was
        vaultpath._resolved = None
    sys.exit(LEDGER.verdict())


if __name__ == "__main__":
    main()
