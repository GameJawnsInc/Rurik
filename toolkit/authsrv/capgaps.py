"""A capture's own word that one of its connections has a hole in it -- and the ONE way
a corpus iterator sets such a connection aside.

WHY THIS EXISTS. The first gapped live connection (20260928T103123, CASTAI-Z1's match 2,
10.0.0.210:65009->98.95.137.136:80: the sniffer never saw 38 + 20 s2c bytes at stream
offsets 38045 / 38548) is REFUSED by `tape.load_tape` and by `livewire.decode_conn`, BY
DESIGN: a stream with a hole dates every message after it with the wrong bytes. That
refusal stays. What broke was everything AROUND it -- one capture fact turned nineteen
suite files red, crashed four corpus iterators and disabled four whole sections of a
fifth under a false "no live captures" label. This module is the set-aside: a corpus
iterator asks it, BY NAME, whether the capture's OWN manifest declares a connection
gapped, and only then steps past it, printing the name.

WHAT IT IS NOT. It is not a catch. Nothing here, and nothing that uses it, may turn a
`TapeError` or a failed decode into a skip: a connection the manifest does not declare
is still decoded, and still reddens its census if it will not close. And a connection
ABSENT from `declared_gaps` is NOT certified whole -- only the manifest's own report
says so, and an old capture may predate the field (three of the vault's live captures
have no manifest at all).

A LEAF (CLAUDE.md, "Leaf modules"): stdlib only, no `sys.path` header, imports neither
`tape` nor `livewire` -- `livewire` imports `tape`, and both need this, so it sits below
both. `conn_name` and `declared_gaps` were cut from `livewire.py` (commit d69bf7a0) and
are re-exported there, at the site they left.
"""
import json
import os

# EVERY connection the vault's manifests declare gapped, as of the last review. A census
# that iterates the whole live corpus asserts the manifests' declared set EQUALS this --
# not "is a subset of" -- so the next gapped connection turns that census red and is SEEN,
# named, and added here by a reviewer after checking it still refuses; it is never
# absorbed by the set-aside. (stamp, connection) in the manifest's spelling.
KNOWN_GAPPED = frozenset({
    ("20260928T103123", "10.0.0.210:65009->98.95.137.136:80"),
})


def conn_name(conn_file):
    """'game-10.0.0.210_65009-to-98.95.137.136_80.jsonl' -> '10.0.0.210:65009->98.95.137.136:80'
    (the manifest's and the version row's spelling), or None for a name of another shape."""
    base = os.path.basename(conn_file)
    if not (base.startswith("game-") and base.endswith(".jsonl")) or "-to-" not in base:
        return None
    left, right = base[len("game-"):-len(".jsonl")].split("-to-", 1)
    if "_" not in left or "_" not in right:
        return None
    return "%s:%s->%s:%s" % (*left.rsplit("_", 1), *right.rsplit("_", 1))


def declared_gaps(capdir):
    """{connection: {direction: [[stream offset, bytes missing], ...]}} for every connection
    the capture's OWN manifest reports as gapped -- livesession's reassembly found TCP bytes
    the sniffer never saw.

    A gapped direction cannot close its byte accounting, so decode_conn refuses it, BY
    DESIGN, and that refusal stays: a stream with a hole in it dates messages after the hole
    with the wrong bytes. What this adds is the WHY, read from the capture's own record
    rather than inferred from the refusal, so a census can set such a connection aside BY
    NAME instead of counting a capture fact as a decoder regression. The first one:
    20260928T103123 :65009 (CASTAI-Z1's match 2), 38 + 20 s2c bytes lost at stream offsets
    38045 / 38548 (studies/monsterai 18). A connection absent here is NOT certified whole --
    only the manifest's own report says so, and an old capture may predate the field."""
    try:
        with open(os.path.join(capdir, "manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError):
        return {}
    out = {}
    for c in (((m.get("report") or {}).get("connections")) or ()):
        g = {d: v for d, v in (c.get("gaps") or {}).items() if v}
        if g and c.get("connection"):
            out[c["connection"]] = g
    return out


def set_aside(capdir, connection, gaps, into=None):
    """True when `gaps` (this capture's `declared_gaps`) names `connection` -- and then
    PRINTS the set-aside by name and appends {capture, connection, gaps} to `into`.

    `connection` is the "client->server" string (a `game-*.jsonl` basename is accepted
    and spelled through `conn_name`). The caller passes `gaps` so a capture's manifest is
    read once per capture, not once per connection."""
    name = connection if "->" in connection else conn_name(connection)
    if name not in gaps:
        return False
    stamp = os.path.basename(os.path.normpath(capdir))
    lost = "; ".join(f"{d} " + ", ".join(f"{n} B at {off}" for off, n in v)
                     for d, v in sorted(gaps[name].items()))
    print(f"   SET ASIDE {stamp} {name}: its manifest declares it gapped ({lost}) -- "
          f"refused by design, not decoded")
    if into is not None:
        into.append({"capture": stamp, "connection": name, "gaps": gaps[name]})
    return True


def corpus_declared(capdirs):
    """{(stamp, connection)} every manifest under `capdirs` declares gapped AND that has a
    `game-*.jsonl` channel file to iterate -- counted fresh from the manifests and the
    directory, independent of any iterator's set-aside list."""
    out = set()
    for c in capdirs:
        try:
            files = {conn_name(f) for f in os.listdir(c)}
        except OSError:
            continue
        stamp = os.path.basename(os.path.normpath(c))
        out |= {(stamp, name) for name in declared_gaps(c) if name in files}
    return out


def audit(into, capdirs, refuses):
    """(ok, detail) for the second half of every amended "every connection decodes" check:
    the connections an iterator set aside are EXACTLY the ones the manifests under
    `capdirs` declare, that set is EXACTLY `KNOWN_GAPPED` restricted to the captures in
    `capdirs` (a NEW declared gap is red until a reviewer names it there; a known one whose
    capture is present but whose manifest stopped declaring it is red too), and every one
    of them STILL refuses (`refuses(capdir, connection)` -> bool, the consumer's own
    refusal: `tape.load_tape` raising, or `decode_conn`'s ok being False). Any of the three
    failing is a red, not a skip."""
    by_stamp = {os.path.basename(os.path.normpath(c)): c for c in capdirs}
    got = {(r["capture"], r["connection"]) for r in into}
    declared = corpus_declared(capdirs)
    known = {k for k in KNOWN_GAPPED if k[0] in by_stamp}
    still = {k: bool(refuses(by_stamp[k[0]], k[1])) for k in sorted(got) if k[0] in by_stamp}
    ok = bool(got == declared == known and len(still) == len(got) and all(still.values()))
    detail = (f"set aside {sorted(got)}; manifests declare {sorted(declared)}; "
              f"known {sorted(known)}; still refused {still}")
    return ok, detail
