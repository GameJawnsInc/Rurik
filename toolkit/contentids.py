r"""Do `content/maps.toml`'s file ids mean the same thing to the server and the client?

    python toolkit/contentids.py                     # both archives a loopback run uses
    python toolkit/contentids.py --client <Gw.dat> --server <Gw.dat>

Standard library only. Read-only on every archive it opens.

WHY THIS EXISTS, and it is one measured near-miss rather than a general worry.

A `file_id` is **archive STATE, not a property of the map.** Bit 31 on a stored
id means `FcArchive` has renamed that row away because it requested a replacement,
and the plain id genuinely stops resolving until `DnArchive` installs it and
re-links (studies/maprows/FINDINGS.md 8). So the same map is `0x8001B97D` in one
copy of `Gw.dat` and `0x1B97D` on a different row in another, and **both are
correct for their own copy**.

That matters here because a run uses TWO archives and nothing checked they agree:

    the server   reads `vault/dat_study/Gw.dat` (or `RURIK_DAT`) for the navmesh
    the client   opens the `Gw.dat` in its own run directory, for the geometry

`content/maps.toml` records ONE id, the server sends it, and **the client
resolves it against a file the server never looks at**. Today the pair agrees --
`0x8001B97D` binds to a map row in `dat_study` and in `vault/run/` both -- so
nothing is broken. But the two copies have already drifted apart in the field
that decides this: 25 bit-31 ids against 29. And `vault/run-live/`, the copy a
client actually played live from, has 9 and does not bind `0x8001B97D` at all.

The failure this refuses is therefore specific and it is one action away:
refresh `vault/run/` from a live-updated archive and the server starts sending an
id its client cannot open. That is LOUD on the client (`failed to load` ->
`re-bloat` -> `Creating default map` -> an assert) and **silent in the server
log**, which is the shape that costs a session to diagnose.

THE CHECK THAT EARNS THE FILE IS NOT "DOES IT RESOLVE". Both archives resolving
the id is necessary and weak -- they could resolve it to different FILES. Row
indices cannot be compared across copies (`archive.py` says so: they do not
survive a patch), so identity is taken from the MFT entry's own `size` and `crc`
over the stored bytes. Same size and crc is the same file; different means the
server is pathing against geometry the client is not drawing, which no amount of
"it loaded" would reveal.

REFUSE vs WARN, and the split is deliberate:

  * the CLIENT cannot bind an id            -> FATAL. The map cannot load at all.
  * the two archives bind it to DIFFERENT bytes -> FATAL. Silent wrong geometry
    is worse than a failure to launch, because the run produces data.
  * the SERVER cannot bind it               -> warn. Collision falls back to off
    and `authsrv.py` already prints that; the run is degraded, not wrong.
  * an archive is missing or unreadable     -> skip, named. A machine with no
    vault must still be able to drive a client.

Nothing here writes, launches, or needs a client.
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "mapdata"))

import content                                                # noqa: E402
from archive import Archive, file_id_table, DEFAULT_DAT       # noqa: E402

MAP_FLAGS = 259


class Finding:
    """One row's verdict. `level` is 'fatal', 'warn' or 'ok'."""

    __slots__ = ("level", "map_id", "file_id", "text")

    def __init__(self, level, map_id, file_id, text):
        self.level, self.map_id = level, map_id
        self.file_id, self.text = file_id, text

    def __repr__(self):
        fid = "-" if self.file_id is None else f"0x{self.file_id:X}"
        return f"[{self.level.upper()}] map {self.map_id} {fid}: {self.text}"


def index(dat):
    """({file_id: mft_row}, {row: entry}) for one archive, or (None, None).

    None rather than an exception: a machine with no vault must still be able to
    drive a client, and `check` reports the absence as a skip.
    """
    try:
        ar = Archive(dat)
    except (OSError, ValueError):
        return None, None
    try:
        return file_id_table(ar), {e.index: e for e in ar.entries}
    except (OSError, ValueError):
        return None, None
    finally:
        ar.close()


def default_client_dat():
    """The loopback client's own archive: `vault/run/<stamp>/Gw.dat`, or None.

    Found by walking the vault rather than by naming a build stamp, so it does
    not go stale on the next client update. `run-live/` is deliberately NOT a
    fallback -- that directory is ArenaNet's DH and never a loopback target.
    """
    try:
        import vaultpath
        root = os.path.join(vaultpath.vault_root(), "run")
    except (ImportError, SystemExit, OSError):
        return None
    if not os.path.isdir(root):
        return None
    for name in sorted(os.listdir(root)):
        cand = os.path.join(root, name, "Gw.dat")
        if os.path.isfile(cand):
            return cand
    return None


def content_file_ids(world=None):
    """{map_id: file_id} for every content map row that carries one."""
    world = world or content.load()
    out = {}
    for map_id, cfg in world.map_static_config().items():
        fid = cfg[0]
        if fid:
            out[map_id] = fid
    return out


def check(client_dat, server_dat=None, world=None):
    """[Finding] for every content map row, plus a list of skip reasons.

    `client_dat` is the archive the CLIENT will open -- the one in its run
    directory -- and it is the required argument because it is the one whose
    disagreement is fatal.
    """
    server_dat = server_dat or DEFAULT_DAT
    ids = content_file_ids(world)
    findings, skips = [], []

    c_tab, c_rows = index(client_dat)
    s_tab, s_rows = index(server_dat)
    if c_tab is None:
        skips.append(f"client archive unreadable or absent: {client_dat}")
    if s_tab is None:
        skips.append(f"server archive unreadable or absent: {server_dat}")
    if c_tab is None:
        # Without the client's copy there is no check to make -- the server's
        # half alone cannot say anything about what the client will open.
        return findings, skips

    for map_id in sorted(ids):
        fid = ids[map_id]
        c_row = c_tab.get(fid)
        if c_row is None:
            findings.append(Finding(
                "fatal", map_id, fid,
                f"the CLIENT's archive does not bind this id, so the map cannot "
                f"load. Its copy is in a different state -- a bit-31 id means a "
                f"replacement is pending, and the plain id binds only after "
                f"DnArchive installs it. Archive: {client_dat}"))
            continue
        c_ent = c_rows.get(c_row)
        if c_ent is None or c_ent.flags != MAP_FLAGS:
            got = "no such row" if c_ent is None else f"flags {c_ent.flags}"
            findings.append(Finding(
                "fatal", map_id, fid,
                f"in the CLIENT's archive this id names row {c_row}, which is "
                f"not a map ({got}, expected {MAP_FLAGS})."))
            continue

        if s_tab is None:
            findings.append(Finding(
                "warn", map_id, fid,
                "the client binds it; the server's archive could not be read, "
                "so collision will fall back to off."))
            continue
        s_row = s_tab.get(fid)
        if s_row is None:
            findings.append(Finding(
                "warn", map_id, fid,
                f"the client binds it (row {c_row}) but the SERVER's archive "
                f"does not, so there is no navmesh and collision is off."))
            continue
        s_ent = s_rows.get(s_row)
        if s_ent is None:
            findings.append(Finding(
                "warn", map_id, fid,
                f"the server's archive names row {s_row}, which is not in its "
                f"own MFT."))
            continue

        # IDENTITY, not row equality. Row indices do not survive a patch, so
        # comparing them across copies would be noise; `size` and `crc` are over
        # the stored bytes and are the same iff the file is.
        if (s_ent.size, s_ent.crc) != (c_ent.size, c_ent.crc):
            findings.append(Finding(
                "fatal", map_id, fid,
                f"the two archives bind this id to DIFFERENT FILES -- server "
                f"row {s_row} is {s_ent.size:,} B crc 0x{s_ent.crc:08X}, client "
                f"row {c_row} is {c_ent.size:,} B crc 0x{c_ent.crc:08X}. The "
                f"server would path against geometry the client is not drawing, "
                f"and the run would look like it worked."))
            continue

        findings.append(Finding(
            "ok", map_id, fid,
            f"server row {s_row}, client row {c_row}, same {c_ent.size:,} B "
            f"crc 0x{c_ent.crc:08X}"))
    return findings, skips


def preflight(client_dat, server_dat=None, say=print, refuse=True):
    """Print the verdict; raise SystemExit on a fatal finding when `refuse`.

    Called from `drive_client.assert_safe`, beside the other launch refusals, so
    that a divergence is caught before a client is started rather than as an
    assert thirty seconds later.
    """
    findings, skips = check(client_dat, server_dat, None)
    fatal = [f for f in findings if f.level == "fatal"]
    warn = [f for f in findings if f.level == "warn"]
    for s in skips:
        say(f"  [SKIP] content file ids -- {s}")
    for f in warn:
        say(f"  [WARN] {f!r}")
    if not fatal:
        if findings:
            say(f"  content file ids: {len(findings) - len(warn)} of "
                f"{len(findings)} map row(s) agree across both archives")
        return findings
    lines = "\n".join(f"  {f!r}" for f in fatal)
    if refuse:
        raise SystemExit(
            f"REFUSING to launch: content/maps.toml disagrees with the archives "
            f"this run would use.\n{lines}\n"
            f"  A file id is archive STATE, not a property of the map "
            f"(studies/maprows/FINDINGS.md 8).\n"
            f"  server archive: {server_dat or DEFAULT_DAT}\n"
            f"  client archive: {client_dat}")
    for f in fatal:
        say(f"  [FATAL] {f!r}")
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", default=None,
                    help="the archive the CLIENT opens (its run directory's)")
    ap.add_argument("--server", default=DEFAULT_DAT,
                    help="the archive the SERVER reads")
    a = ap.parse_args()

    client = a.client or default_client_dat()
    if client is None:
        sys.exit("no client archive found under the vault's run/ directory; "
                 "pass --client. (This tool is about the archive the CLIENT "
                 "opens, so guessing one would defeat it.)")
    print(f"server archive: {a.server}")
    print(f"client archive: {client}\n")
    findings, skips = check(client, a.server)
    for s in skips:
        print(f"[SKIP] {s}")
    for f in findings:
        print(repr(f))
    fatal = sum(1 for f in findings if f.level == "fatal")
    warn = sum(1 for f in findings if f.level == "warn")
    print(f"\n{len(findings)} map row(s): {len(findings) - fatal - warn} agree, "
          f"{warn} warn, {fatal} FATAL")
    return 2 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
