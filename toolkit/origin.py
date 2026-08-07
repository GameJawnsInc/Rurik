"""Whose server produced a capture: ours, or ArenaNet's. Never guessed, never mixed.

WHY. Every capture in the vault today is Rurik talking to Rurik -- 413 files, and MEASURED
2026-08-06, every `peer` in all of them is 127.0.0.1 or 127.0.0.3. Nothing records that
fact, because until `PLAN.md` §7 Q4 authorized live automation there was no other
possibility and no reason to write it down.

The moment one capture is ArenaNet's, that stops being true and the distinction becomes
**the most valuable metadata in the vault**. A recording of the real server is the only
artifact this project cannot reproduce; a recording of our own server is a regression
fixture we can make again any afternoon. Conflating them is not untidiness, it is an
evidence defect of the exact class this repo keeps catching in other people's work:
`toolkit/authsrv/test_movement_fidelity.py` already pools *every* game-channel capture
and scores our simulation against "the client", and if one of those files came from
ArenaNet's server the number it prints would be a blend of two different oracles with no
indication which.

THE VOCABULARY, deliberately three-valued.

  OURS     produced by a Rurik server. A fixture.
  LIVE     produced against ArenaNet's real service. Irreplaceable.
  UNKNOWN  we cannot tell. NOT a synonym for OURS.

UNKNOWN being distinct is the whole point. A two-valued scheme forces an unstamped file
to be called one or the other, and whichever default you pick is wrong exactly when it
matters -- the first live capture written by a tool that forgot to stamp would silently
join the fixture pool.

HOW A FILE IS CLASSIFIED, in order:

1. An explicit `origin` record. Written at session start by whatever produced the file.
   `toolkit/authsrv/authsrv.py` writes OURS because it *is* our server and can never
   produce anything else. A future live-capture tool writes LIVE.
2. Failing that, inference, and only in the one direction that is sound: a file whose
   every recorded peer/host is a 127/8 address, and which carries our server's own
   session markers, is OURS. That covers the 413 files that predate this module, and it
   is safe because a capture of ArenaNet's server cannot have a loopback peer.
3. Otherwise UNKNOWN. Including a file with no peers at all -- absence of evidence.

There is deliberately NO inference toward LIVE. A non-loopback address appears in
`vault/captures/patcher/` (endpoint metadata the patcher talked to) and calling that a
live game capture would be worse than admitting ignorance.
"""
import json
import os

OURS = "ours"
LIVE = "live"
UNKNOWN = "unknown"

RECORD_KIND = "origin"

# Fields anywhere in a record that name a network peer. Checked by value, not by
# position, because the shape has already drifted once (`peer`, then `host`, then
# `addr` in the patcher captures).
PEER_FIELDS = ("peer", "host", "addr", "remote")

# Our server's own session markers. A file carrying these was produced by a Rurik
# listener, which is the corroboration that makes the loopback inference sound rather
# than merely consistent.
OURS_MARKERS = ("key_exchange_ok", "server_seed", "login_ok")


def record(produced_by, origin=OURS, **extra):
    """The record a capture writes at session start. Write it FIRST, before frames.

    Kept as data rather than a comment so a reader can classify a file in one pass
    without knowing which tool wrote it.
    """
    out = {"kind": RECORD_KIND, "origin": origin, "produced_by": produced_by}
    out.update(extra)
    return out


def is_loopback(value):
    host = str(value).rsplit(":", 1)[0].strip("[]")
    parts = host.split(".")
    return (len(parts) == 4 and parts[0] == "127"
            and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts))


def origin_of(path):
    """(origin, why) for one capture file. `why` is meant to be printed."""
    stated = None
    peers, markers = set(), set()
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get("kind") == RECORD_KIND and rec.get("origin"):
                    stated = rec["origin"]
                    break
                if rec.get("kind") in OURS_MARKERS:
                    markers.add(rec["kind"])
                for f in PEER_FIELDS:
                    v = rec.get(f)
                    if isinstance(v, str) and v:
                        peers.add(v)
    except OSError as exc:
        return UNKNOWN, f"unreadable: {exc}"

    if stated in (OURS, LIVE):
        return stated, f"stated in the file's own {RECORD_KIND} record"
    if stated:
        return UNKNOWN, f"{RECORD_KIND} record says {stated!r}, which is not a known origin"

    if peers and all(is_loopback(p) for p in peers) and markers:
        return OURS, (f"inferred: {len(peers)} peer(s), all loopback, plus our own "
                      f"session markers ({', '.join(sorted(markers))})")
    if peers and all(is_loopback(p) for p in peers):
        return UNKNOWN, (f"every peer is loopback but none of our server's session "
                         f"markers are present -- not enough to call it ours")
    if peers:
        return UNKNOWN, (f"carries a non-loopback peer; this module never infers LIVE, "
                         f"because the patcher captures hold public addresses too")
    return UNKNOWN, "no peer recorded at all"


def partition(paths):
    """{origin: [path, ...]} over a set of captures."""
    out = {OURS: [], LIVE: [], UNKNOWN: []}
    for p in paths:
        out[origin_of(p)[0]].append(p)
    return out


class MixedCorpora(SystemExit):
    """Refusing to pool captures of two different servers."""


def require_single(paths, want=OURS, what="this measurement"):
    """Every path must share one origin, or refuse loudly. Returns the kept paths.

    The default is OURS because every consumer that exists today scores our own
    simulation against our own captures. A live corpus is not a bigger version of that
    corpus -- it answers a different question -- so the refusal is the point rather
    than an inconvenience.
    """
    groups = partition(paths)
    others = {k: v for k, v in groups.items() if k != want and v}
    if others:
        lines = [f"REFUSING to pool captures of different origins for {what}."]
        lines.append(f"  wanted: {want} ({len(groups[want])} file(s))")
        for kind, files in sorted(others.items()):
            lines.append(f"  found {kind}: {len(files)} file(s), e.g.")
            for f in files[:3]:
                lines.append(f"      {os.path.basename(f)}  -- {origin_of(f)[1]}")
        lines.append("  A recording of ArenaNet's server and a recording of ours answer")
        lines.append("  different questions. Averaging them produces a number that is")
        lines.append("  about neither. Select one corpus explicitly.")
        raise MixedCorpora("\n".join(lines))
    return groups[want]


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vaultpath
    root = vaultpath.require_dir("captures", why="classifying capture origins")
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("captures-scrubbed",)]
        found += [os.path.join(base, f) for f in files if f.endswith(".jsonl")]
    groups = partition(found)
    for kind in (OURS, LIVE, UNKNOWN):
        print(f"{kind:8s} {len(groups[kind])}")
    if groups[UNKNOWN]:
        print("\nunknown, with the reason each could not be classified:")
        for p in groups[UNKNOWN][:10]:
            print(f"  {os.path.relpath(p, root)}\n      {origin_of(p)[1]}")
        if len(groups[UNKNOWN]) > 10:
            print(f"  ... and {len(groups[UNKNOWN]) - 10} more")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
