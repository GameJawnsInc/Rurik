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

1. An explicit `origin` record, CHECKED AGAINST THE FILE'S OWN CONTENTS. Written at
   session start by whatever produced the file. A stamp that contradicts the addresses
   recorded beneath it is REFUSED, not believed -- see below.
2. Failing that, inference, and only in the one direction that is sound: a file whose
   every recorded peer/host is a 127/8 address, and which carries our server's own
   session markers, is OURS. That covers the 413 files that predate this module, and it
   is safe because a capture of ArenaNet's server cannot have a loopback peer.
3. Otherwise UNKNOWN. Including a file with no peers at all -- absence of evidence.

There is deliberately NO inference toward LIVE. A non-loopback address appears in
`vault/captures/patcher/` (endpoint metadata the patcher talked to) and calling that a
live game capture would be worse than admitting ignorance.

WHY STEP 1 CHECKS RATHER THAN TRUSTS. Until 2026-08-07 it returned the stated value and
stopped reading -- so the stamp was an unfalsifiable self-declaration, and it was already
wrong on disk. `vault/dryrun/dryrun_wire.jsonl` is a LOOPBACK capture stamped `live`,
because `wirecapture.py` hardcoded the value; the response at the time was to move the
mislabelled files outside the directory the suite scans, which makes the guard against a
false LIVE green by construction. Both halves are fixed: producers now DERIVE the stamp
from the endpoint, and this reader refuses a `live` stamp on a file whose every recorded
address is loopback. A capture of ArenaNet cannot look like that.

The reverse is NOT symmetric and is not implemented. A `ours` stamp on a file with public
addresses is not a contradiction -- our own tooling legitimately records ArenaNet endpoint
metadata -- so it is reported as corroborated-or-not, never overridden.

AND THE FIELDS HAVE TO BE THE ONES ACTUALLY WRITTEN. `PEER_FIELDS` listed `peer`, `host`,
`addr`, `remote` and missed `src`/`dst` (wirecapture) and `connection` (decrypted
channels), so the entire first live capture recorded public ArenaNet endpoints on every
record and still classified as having "no peer recorded at all" once its stamp was
removed. A corroboration step is worth nothing if it does not read the corroborating
field. Placeholders in those fields (`"client": "unknown"`, `"server": "*:6112"`) are
excluded by `is_address`, because a non-address reads as "not loopback" and silently
defeats the check -- which is exactly how it failed its first real test.
"""
import json
import os

OURS = "ours"
LIVE = "live"
UNKNOWN = "unknown"

RECORD_KIND = "origin"

# Fields anywhere in a record that name a network peer. Checked by value, not by
# position, because the shape has already drifted once (`peer`, then `host`, then
# `addr` in the patcher captures) -- and then AGAIN, unnoticed, when the live capture
# tools arrived writing `src`/`dst` (wirecapture) and `connection` (the decrypted
# channels). MEASURED 2026-08-07 by adversarial review: strip the origin record from the
# first live capture and all eight files classified `unknown -- "no peer recorded at all"`
# while every record in them named a public ArenaNet endpoint. The corroboration was
# sitting in the artifact and this module was not looking at it.
PEER_FIELDS = ("peer", "host", "addr", "remote", "src", "dst", "connection",
               "server", "client")

# `connection` records a PAIR ("10.0.0.210:63155->54.164.212.177:80"). Both ends are
# collected: the test below asks whether EVERY address is loopback, and a live session
# always has at least one that is not, so including the local end cannot make a live file
# look local.
PAIR_SEP = "->"

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


# How many records to keep reading purely to corroborate a stamp. Corroboration does not
# need the whole file -- a handful of records settles whether the peers are loopback -- and
# a live wire.jsonl is megabytes.
CORROBORATE_RECORDS = 2000


def peers_in(rec):
    """Every peer-ish value named anywhere in one record, pairs split into both ends."""
    out = set()
    for f in PEER_FIELDS:
        v = rec.get(f)
        if not isinstance(v, str) or not v:
            continue
        for half in (v.split(PAIR_SEP) if PAIR_SEP in v else [v]):
            half = half.strip()
            if half:
                out.add(half)
    return out


def is_address(value):
    """Does this value actually name an IPv4 host, rather than stand in for one?

    The peer fields carry PLACEHOLDERS as well as addresses -- `"client": "unknown"` when
    the sniff has not identified the local end, `"server": "*:6112"` when it is filtering
    by port on any host. Those are not addresses and must not vote on whether a capture
    is loopback: `is_loopback("unknown")` is false, which reads as "a non-loopback peer",
    which is exactly backwards. That one placeholder defeated the contradiction check on
    its first real test -- vault/dryrun/dryrun_wire.jsonl, a loopback file stamped `live`,
    passed because `"unknown"` sat in the set beside two 127.0.0.1 addresses.
    """
    host = str(value).rsplit(":", 1)[0].strip("[]")
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def origin_of(path):
    """(origin, why) for one capture file. `why` is meant to be printed."""
    stated = None
    peers, markers = set(), set()
    parsed = 0
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
                parsed += 1
                if rec.get("kind") == RECORD_KIND and rec.get("origin"):
                    stated = stated or rec["origin"]
                    # Deliberately NO `break`. Reading on is what turns the stamp from an
                    # assertion into a claim the file's own contents can refute -- see the
                    # contradiction check below, which is the entire point of this change.
                    continue
                if rec.get("kind") in OURS_MARKERS:
                    markers.add(rec["kind"])
                peers |= peers_in(rec)
                if stated and parsed > CORROBORATE_RECORDS:
                    break
    except OSError as exc:
        return UNKNOWN, f"unreadable: {exc}"

    # A stamp is checked against the evidence, not taken on trust. The sound direction is
    # this one: a recording of ArenaNet's service CANNOT have every peer on 127/8. That is
    # not hypothetical -- vault/dryrun/dryrun_wire.jsonl is a loopback capture stamped
    # `live`, because wirecapture.py hardcoded the value, and the response at the time was
    # to move the file outside the directory the suite scans rather than fix the label.
    # A guard whose only counterexamples have been relocated is green by construction.
    addrs = {p for p in peers if is_address(p)}
    if stated == LIVE and addrs and all(is_loopback(a) for a in addrs):
        return UNKNOWN, (f"CONTRADICTED: states {LIVE!r}, but all {len(addrs)} recorded "
                         f"address(es) are loopback ({', '.join(sorted(addrs)[:3])}). "
                         f"A capture of ArenaNet cannot look like this.")
    if stated in (OURS, LIVE):
        if addrs:
            return stated, (f"stated in the file's own {RECORD_KIND} record, corroborated "
                            f"by {len(addrs)} recorded address(es)")
        return stated, (f"stated in the file's own {RECORD_KIND} record -- UNCORROBORATED, "
                        f"the file records no address to check it against")
    if stated:
        return UNKNOWN, f"{RECORD_KIND} record says {stated!r}, which is not a known origin"

    if addrs and all(is_loopback(a) for a in addrs) and markers:
        return OURS, (f"inferred: {len(addrs)} peer(s), all loopback, plus our own "
                      f"session markers ({', '.join(sorted(markers))})")
    if addrs and all(is_loopback(a) for a in addrs):
        return UNKNOWN, (f"every peer is loopback but none of our server's session "
                         f"markers are present -- not enough to call it ours")
    if peers:
        return UNKNOWN, (f"carries a non-loopback peer; this module never infers LIVE, "
                         f"because the patcher captures hold public addresses too")
    # These two were one branch reporting "no peer recorded at all", which is a confident
    # statement about the CONTENTS when the truth is often that nothing could be read at
    # all. MEASURED: a capture's own manifest.json is pretty-printed, so a line-by-line
    # reader parses ZERO records from it and then reported the file as peerless -- while
    # it in fact listed six public endpoints. A classifier that cannot tell "I looked and
    # found nothing" from "I could not look" states the first and means the second.
    if parsed == 0:
        return UNKNOWN, ("no JSON records could be read -- this reader takes one object "
                         "per line, so a pretty-printed .json parses as nothing. Absence "
                         "of records is not absence of peers.")
    return UNKNOWN, f"no peer recorded in any of the {parsed} record(s) read"


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
