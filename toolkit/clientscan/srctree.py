"""Recover ArenaNet's own source-tree layout from the paths left in the client.

    python toolkit/clientscan/srctree.py                  # the whole census
    python toolkit/clientscan/srctree.py --cli            # the Cli/Srv split
    python toolkit/clientscan/srctree.py --shared         # trees both targets built
    python toolkit/clientscan/srctree.py --under Net/Msg  # one subtree, in full
    python toolkit/clientscan/srctree.py --exe <path> --json

WHY THIS EXISTS. The repository's founding brief says there is no server binary
and "there never was one to have" (HANDOFF.md §1). The second half of that is
wrong, and the correction changes the shape of the work. `Gw.exe` carries 937
distinct `P:\\Code\\...` source paths -- ArenaNet's own build-machine paths,
left in the image by assert() and a handful of other macros -- and every
gameplay subsystem in them sits under a `Cli\\` directory: `Gw\\Char\\Cli\\`,
`Gw\\Item\\Cli\\`, `Gw\\Party\\Cli\\`, and `Gw\\Main\\MainCli.cpp` for the entry
point. Not one path lies under a `Srv\\` directory.

So the client and the server were two build targets over one source tree. The
shipped client is the `Cli` half. That is a better position than inventing from
nothing, because it says exactly which code we can read and which we cannot:

  * `Gw\\<Subsystem>\\Cli\\`  client half, shipped -- readable
  * `Gw\\<Subsystem>\\Srv\\`  server half, never shipped -- the missing work
  * `Base\\`, `Engine\\`, `Net\\`, `Gw\\Const\\`  no Cli/Srv split at all, so
    both targets compiled these, and reading them here is reading the server's
    own code

WHAT IT CANNOT TELL YOU. A source path survives only if some macro in that
translation unit emitted one. So "no `Srv\\` path in the image" is evidence that
no server-side translation unit is linked into the client, not proof: a linked
TU that emits no path at all would be invisible. The inference is strong because
every client subsystem here does emit paths, but it is INFERRED, not MEASURED.
A path also proves a file existed, never what was in it.

READ ONLY. Opens the exe for reading. Standard library only.
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vaultpath                                             # noqa: E402

SEP = chr(92)                       # one backslash, spelled out to stay readable
PREFIX = "P:" + SEP + "Code" + SEP

# The build-machine root. Case varies in the image (`Code` and `code` both
# appear), so the scan is deliberately tolerant of it and the census is not.
PATH_RE = re.compile(rb"P:\\[Cc]ode\\[\x20-\x7e]{2,160}")

# Trees with no Cli/Srv split anywhere in them: shared between build targets.
SHARED_TREES = ["Base", "Engine", "Net", "Gw" + SEP + "Const"]

# Every way we know to spell a server-side translation unit. All must come back
# empty; a future build that ships one should make this tool say so loudly
# rather than quietly returning a census that still looks reasonable.
# A lone backslash is a bad escape in a pattern, so the separator is escaped.
RSEP = re.escape(SEP)
SRV_PATTERNS = [
    ("under a " + SEP + "Srv" + SEP + " directory", RSEP + "Srv" + RSEP),
    ("SrvXxx filename",                             RSEP + "Srv[A-Z]"),
    ("'Server' anywhere in the path",               "Server"),
    ("SvXxx filename",                              RSEP + "Sv[A-Z]"),
    ("GameSrv-style filename",                      RSEP + "GameSrv"),
    ("HostXxx / SimXxx filename",                   RSEP + "(Host|Sim)[A-Z]"),
]


def default_exe():
    """The pinned pristine client. Not the patched run-dir copy.

    This module was the ONLY one in clientscan/ that asked for the pristine
    copy, and it was right -- `pinned.py` now makes that everyone's default and
    hashes the answer. Kept as a function so the rest of this file is unchanged.
    """
    import pinned
    return pinned.find()[0]


def source_paths(blob):
    """Every distinct P:\\Code source path in the image, with hit counts."""
    hits = collections.Counter()
    for m in PATH_RE.finditer(blob):
        hits[m.group().decode("ascii")] += 1
    return hits


def segments(path):
    """`P:\\Code\\Gw\\Char\\Cli\\ChCliApi.cpp` -> ['Gw','Char','Cli','ChCliApi.cpp']"""
    return path[len(PREFIX):].split(SEP)


def subsystem(path):
    """The `<tree>\\<subsystem>` a path belongs to, e.g. `Gw\\Char`."""
    q = segments(path)
    return SEP.join(q[:2]) if len(q) >= 2 else q[0]


def cli_split(paths):
    """Per `Gw\\<subsystem>`: total files, and how many carry a `Cli` marker.

    A Cli marker is the fingerprint of a subsystem that was split into client and
    server halves, so it names a `Srv` sibling we do not have. It is spelled two
    ways and both count: a `Cli\\` directory (`Gw\\Char\\Cli\\ChCliApi.cpp`) and a
    `...Cli.cpp` filename (`Gw\\Main\\MainCli.cpp`).

    A subsystem with NO marker is not thereby shared -- it may equally be
    client-only, and the path alone does not say which. See §4 of the study.
    """
    out = collections.OrderedDict()
    for p in sorted(paths):
        q = segments(p)
        if q[0] != "Gw" or len(q) < 3:
            continue
        row = out.setdefault(q[1], {"files": 0, "cli_dir": 0, "cli_file": 0})
        row["files"] += 1
        if q[2] == "Cli":
            row["cli_dir"] += 1
        elif re.match(r"^\w+Cli\.(cpp|h)$", q[-1]):
            row["cli_file"] += 1
    for row in out.values():
        row["cli"] = row["cli_dir"] + row["cli_file"]
    return collections.OrderedDict(
        sorted(out.items(), key=lambda kv: (-kv[1]["cli"], -kv[1]["files"], kv[0])))


def srv_hits(paths):
    """For each way of spelling a server-side TU, the paths that match it."""
    return [(label, [p for p in sorted(paths) if re.search(rx, p)])
            for label, rx in SRV_PATTERNS]


def pdb_paths(paths):
    """The linker-embedded PDB path, which names the build TARGET."""
    return [p for p in sorted(paths) if p.lower().endswith(".pdb")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=None, help="default: the pinned vault client")
    ap.add_argument("--cli", action="store_true", help="only the Cli/Srv split")
    ap.add_argument("--shared", action="store_true", help="only the shared trees")
    ap.add_argument("--under", help="list one subtree in full, e.g. Net/Msg")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    exe = args.exe or default_exe()
    if not os.path.isfile(exe):
        print("no such exe: %s" % exe, file=sys.stderr)
        if args.exe is None:
            print("vault: %s (%s)" % (vaultpath.vault_root(), vaultpath.vault_why()),
                  file=sys.stderr)
        return 2
    with open(exe, "rb") as f:
        blob = f.read()
    paths = source_paths(blob)

    if args.json:
        print(json.dumps({
            "exe": exe,
            "size": len(blob),
            "paths": sorted(paths),
            "cli_split": cli_split(paths),
            "srv_hits": {k: v for k, v in srv_hits(paths)},
            "pdb": pdb_paths(paths),
        }, indent=1))
        return 0

    print("%s: %s bytes, %d distinct source paths"
          % (exe, format(len(blob), ","), len(paths)))

    if args.under:
        want = PREFIX + args.under.replace("/", SEP).strip(SEP) + SEP
        for p in sorted(paths):
            if p.startswith(want):
                print("  %s" % p)
        return 0

    if not (args.cli or args.shared):
        ext = collections.Counter(os.path.splitext(p)[1].lower() for p in paths)
        print("  by extension: %s" % dict(ext.most_common()))
        print()
        print("=== <tree>%s<subsystem> census ===" % SEP)
        seg = collections.Counter(subsystem(p) for p in paths)
        for k, v in sorted(seg.items(), key=lambda kv: (-kv[1], kv[0])):
            print("  %4d  %s" % (v, k))
        print()
        print("=== server-side translation units in the shipped image ===")
        for label, hit in srv_hits(paths):
            print("  %-34s %d" % (label, len(hit)))
            for p in hit:
                print("        %s" % p)
        print("  (paths containing 'Srv' at all, for contrast --")
        for p in sorted(paths):
            if "Srv" in p:
                print("        %s" % p)
        print("   both are client-side objects representing a server.)")
        print()
        print("=== build target, per the linker's PDB path ===")
        for p in pdb_paths(paths):
            print("  %s" % p)

    if args.cli or not (args.shared or args.under):
        print()
        print("=== Gw%s<subsystem>: a shipped Cli half means an unshipped Srv half ==="
              % SEP)
        print("  %-15s %5s %5s %5s" % ("", "files", "Cli" + SEP, "*Cli"))
        for name, row in cli_split(paths).items():
            print("  Gw%s%-12s %5d %5d %5d   %s"
                  % (SEP, name, row["files"], row["cli_dir"], row["cli_file"],
                     "<- Cli/Srv split" if row["cli"] else ""))

    if args.shared or not (args.cli or args.under):
        print()
        print("=== shared trees: no Cli/Srv split, so the server built these too ===")
        for tree in SHARED_TREES:
            owned = [p for p in sorted(paths) if p.startswith(PREFIX + tree + SEP)]
            print("  %-14s %4d files" % (PREFIX + tree, len(owned)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
