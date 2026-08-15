"""What the client looked like before an ArenaNet update, and what moved after.

    python toolkit/updatecheck.py --before                 # capture, BEFORE accepting
    python toolkit/updatecheck.py --before --snapshot      # and copy the client too
    python toolkit/updatecheck.py --after <before.json>    # what moved

Exit codes, and the middle one is the point:

    0   --before captured cleanly; --after found nothing moved
    1   --after found CHANGES. That is a RESULT, not an error -- it is what an
        update looks like, and it is the answer the command exists to give.
    2   the run could not be made: a tool refused, the vault is missing, or a
        required measurement was unavailable. NOT a finding about the client.

That split is `datcheck.py`'s, deliberately, and it is not decoration: conflating
"the archive changed" with "the run could not be made" once cost a crash being
reported as a moved row.

WHY. `studies/crossbuild/PLAN.md` §11. An update is not schedulable, half the
measurements this arc depends on need a BEFORE state, and `RUNBOOK.md`:136-139
already warns that snapshotting after accepting an update means the build you
were working against is gone. Until now that warning was prose a session had to
remember to read, and the "before" work was six separate commands with six exit
conventions. This is one command, and the after-run prints one page.

WHAT IT RECORDS, all of it measurements rather than ArenaNet's expression:

  * every vaulted build's number (`buildid.py`), stamp, size and sha256
  * what the LIVE install at `C:\\gw` currently is -- the thing an update changes
  * the signature corpus: every anchor's hit count AND the addresses it resolves
    to (`sigcorpus.py`). This is the "what still resolves by signature" line, and
    it is the most useful thing in the report
  * the class-(a) address census (`buildpins.py --json`), so a moved pin is named
  * the schema's build stamp, from `messages.json` and `overrides.json`
  * the Diffie-Hellman parameters as a FINGERPRINT ONLY -- generator, prime bit
    length, and a sha256 prefix of the prime and of B. Never the values: those
    are ArenaNet key material, `dump_dh_params.py` prints only fingerprints by
    default for the same reason, and this file is a diffable record rather than
    a place to park a key

WHAT IT DOES NOT DO WITHOUT BEING ASKED. `--snapshot` copies `C:\\gw` into the
vault via `snapshot_client.py`; without it this command only READS. That is
opt-in because copying a live install is a real action with a real failure mode
(exit 3, a locked file, if the client is running) and because another session may
be driving the client right now. The reminder is printed either way, because the
snapshot is the single irreplaceable part of the before-state.

READ ONLY unless `--snapshot` is passed. Standard library only.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "clientscan"))
sys.path.insert(0, os.path.join(HERE, "clientpatch"))
sys.path.insert(0, os.path.join(HERE, "mapdata"))
import buildid                                               # noqa: E402
import buildpins                                             # noqa: E402
import dhbuild                                               # noqa: E402
import pinned                                                # noqa: E402
import sigcorpus                                             # noqa: E402
import vaultpath                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

REPO = os.path.dirname(HERE)
SCHEMA = os.path.join(REPO, "schema")


class CannotRun(SystemExit):
    """Exit 2: the run could not be made. Never a finding about the client."""


def _fingerprint(n, nbytes=64):
    """A sha256 prefix of an integer's little-endian bytes.

    The DH prime and the server's public value are ArenaNet-derived key material.
    A fingerprint diffs exactly as well -- it changes when they change, which is
    the whole question -- and carries none of the value.
    """
    return hashlib.sha256(int(n).to_bytes(nbytes, "little")).hexdigest()[:16]


def _schema_stamp(name):
    p = os.path.join(SCHEMA, name)
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    # Nested under `provenance` in both files, which is where the first reader
    # of this key looked second. See test_buildid.py §3.
    prov = d.get("provenance")
    stamp = prov.get("validated_against_build") if isinstance(prov, dict) else None
    return {"validated_against_build": stamp}


def capture(snapshot=False, dat=None):
    """The whole before-state, as a diffable dict."""
    out = {
        "captured": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "builds": {}, "live_install": {}, "schema": {}, "dh": {}, "archive": {},
    }

    for b in pinned.BUILDS:
        row = {"stamp": b.stamp, "recorded_number": b.number, "size": b.size}
        try:
            path, _why = pinned.find(b.stamp)
        except SystemExit as exc:
            row["error"] = str(exc).splitlines()[0]
            out["builds"][b.stamp] = row
            continue
        try:
            row["build"] = buildid.read(path)[0]
        except SystemExit as exc:
            row["build"] = None
            row["build_error"] = str(exc).splitlines()[0]
        pe = PE(path)
        row["signatures"] = {
            s.name: {"hits": hits,
                     "vas": sorted(pe.image_base + pe.off_to_rva(h)
                                   for h in pe.find(s.pattern, ".text"))}
            for s, hits, _ok in sigcorpus.verify(pe)}
        try:
            va, _rva, _off, (g, p, B) = dhbuild.locate_keys(pe, path)
            out["dh"][b.stamp] = {"struct_va": va, "generator": g,
                                  "prime_bits": p.bit_length(),
                                  "prime_fp": _fingerprint(p),
                                  "public_fp": _fingerprint(B)}
        except SystemExit as exc:
            out["dh"][b.stamp] = {"error": str(exc).splitlines()[0]}
        out["builds"][b.stamp] = row

    what, detail = pinned.identify(pinned.LIVE_INSTALL)
    out["live_install"] = {"path": pinned.LIVE_INSTALL, "identify": what,
                           "detail": detail}
    if os.path.isfile(pinned.LIVE_INSTALL):
        out["live_install"]["size"] = os.path.getsize(pinned.LIVE_INSTALL)
        try:
            out["live_install"]["build"] = buildid.read(pinned.LIVE_INSTALL)[0]
        except SystemExit as exc:
            out["live_install"]["build_error"] = str(exc).splitlines()[0]
        # READ THE SIGNATURES OFF THE LIVE INSTALL TOO. Until 2026-08-14 this
        # block recorded only identify/size/build, while `signatures` came from
        # `pinned.BUILDS` -- the VAULTED builds, which by definition did not
        # change across an update. So `_advice()`'s
        #   "Every signature in the corpus still resolves at its expected count"
        # compared the old builds against themselves and printed a PASS about a
        # build it had never opened. MEASURED: it printed exactly that on the
        # 38797 -> 38833 update, the first real firing of this tool, in the same
        # breath as "the live install moved to 38833".
        #
        # It is the repo's own named defect -- a check that cannot fail, worded
        # as reassurance -- and it is the one this arc built `msgshape.py`'s
        # vacuity guard to catch. The live install is the ONLY image that has
        # the new build in it before the snapshot lands, so it is the only place
        # the question can be asked at `--after` time.
        try:
            pe = PE(pinned.LIVE_INSTALL)
            out["live_install"]["signatures"] = {
                s.name: {"hits": hits, "expected": s.hits, "ok": ok,
                         "vas": sorted(pe.image_base + pe.off_to_rva(h)
                                       for h in pe.find(s.pattern, ".text"))}
                for s, hits, ok in sigcorpus.verify(pe)}
        except Exception as exc:                             # noqa: BLE001
            out["live_install"]["signature_error"] = f"{type(exc).__name__}: {exc}"

    rows, problems, _skipped = buildpins.scan(HERE)
    out["pins"] = buildpins.baseline(rows)
    out["pin_problems"] = problems

    for name in ("messages.json", "overrides.json"):
        out["schema"][name] = _schema_stamp(name)

    if dat:
        snap = os.path.join(os.path.dirname(_default_path()),
                            f"datcheck-{time.strftime('%Y%m%dT%H%M%S')}.json")
        rc = subprocess.call([sys.executable,
                              os.path.join(HERE, "mapdata", "datcheck.py"),
                              "--dat", dat, "--snapshot", snap])
        out["archive"] = {"dat": dat, "snapshot": snap, "datcheck_rc": rc}

    if snapshot:
        rc = subprocess.call([sys.executable,
                              os.path.join(HERE, "snapshot_client.py")])
        out["client_snapshot_rc"] = rc
        if rc == 3:
            raise CannotRun(
                "snapshot_client.py exited 3: a file is LOCKED, so the snapshot is\n"
                "  INCOMPLETE. Close Guild Wars and re-run. Do not accept an update\n"
                "  until this is 0 -- the build you are working against is what you\n"
                "  are about to lose.")
    return out


def _default_path():
    root = vaultpath.require_dir(why="the update-check baseline")
    d = os.path.join(root, "updatecheck")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"before-{time.strftime('%Y%m%dT%H%M%S')}.json")


def _refuse_repo(path):
    """The baseline goes in the vault, never into a checkout of this repo.

    It carries measurements rather than ArenaNet bytes, so this is a tidiness
    rule rather than the provenance gate -- but every checkout is refused, not
    just this one, because a git worktree's root is not the main checkout's and
    that distinction has already let a write land in the wrong tree.
    """
    sys.path.insert(0, os.path.join(HERE, "mapdata"))
    import mapbuild                                          # noqa: PLC0415
    path = os.path.abspath(path)
    vault = os.path.abspath(vaultpath.vault_root())
    if path.startswith(vault + os.sep):
        return path
    for root in mapbuild.working_tree_roots():
        if path == root or path.startswith(root + os.sep):
            raise CannotRun(
                f"refusing to write the baseline into a checkout of this repo:\n"
                f"  {path}\n  that tree is {root}\n"
                f"  It belongs in the vault; pass a path under "
                f"{vaultpath.vault_root()} or omit --out.")
    return path


def _diff_builds(before, after):
    lines = []
    for stamp, b in sorted(before.get("builds", {}).items()):
        a = after.get("builds", {}).get(stamp)
        if a is None:
            lines.append(f"  BUILD GONE   {stamp} is no longer in the vault")
            continue
        if b.get("build") != a.get("build"):
            lines.append(f"  BUILD MOVED  {stamp}: {b.get('build')} -> "
                         f"{a.get('build')}")
        for name, bs in sorted((b.get("signatures") or {}).items()):
            as_ = (a.get("signatures") or {}).get(name)
            if as_ is None:
                lines.append(f"  SIG GONE     {stamp} {name} no longer recorded")
            elif as_["hits"] != bs["hits"]:
                lines.append(f"  SIG COUNT    {stamp} {name}: {bs['hits']} -> "
                             f"{as_['hits']} hit(s)  <- RE-DERIVE THIS")
            elif as_["vas"] != bs["vas"]:
                lines.append(f"  sig moved    {stamp} {name}: still {as_['hits']} "
                             f"hit(s), addresses changed  <- resolves fine")
    for stamp in sorted(set(after.get("builds", {})) - set(before.get("builds", {}))):
        lines.append(f"  BUILD NEW    {stamp} appeared in the vault")
    return lines


def diff(before, after):
    """(lines, changed). `changed` is what decides exit 1 vs 0."""
    lines = _diff_builds(before, after)

    b, a = before.get("live_install", {}), after.get("live_install", {})
    for key in ("identify", "size", "build"):
        if b.get(key) != a.get(key):
            lines.append(f"  LIVE INSTALL {key}: {b.get(key)} -> {a.get(key)}")

    gone, arrived, moved = buildpins.diff(before.get("pins", []),
                                          after.get("pins", []))
    for r in gone:
        lines.append(f"  PIN GONE     {r['file']} {r['symbol']}")
    for r in arrived:
        lines.append(f"  PIN NEW      {r['file']} {r['symbol']} {r['value']:#x}")
    for x, y in moved:
        lines.append(f"  PIN MOVED    {x['file']} {x['symbol']} "
                     f"{x['value']:#x} -> {y['value']:#x}")

    for name in sorted(before.get("schema", {})):
        bs = before["schema"][name].get("validated_against_build")
        as_ = after.get("schema", {}).get(name, {}).get("validated_against_build")
        if bs != as_:
            lines.append(f"  SCHEMA       {name}: {bs} -> {as_}")

    for stamp, bd in sorted(before.get("dh", {}).items()):
        ad = after.get("dh", {}).get(stamp, {})
        for key in ("struct_va", "prime_fp", "public_fp", "generator"):
            if bd.get(key) != ad.get(key):
                lines.append(f"  DH           {stamp} {key}: {bd.get(key)} -> "
                             f"{ad.get(key)}")
    return lines, bool(lines)


def _advice(before, after):
    """The one page: what this means for the next session."""
    out = []
    live_b = before.get("live_install", {}).get("build")
    live_a = after.get("live_install", {}).get("build")
    if live_b != live_a:
        out.append(f"The live install moved from build {live_b} to {live_a}.")
        stamps = {v.get("build") for v in after.get("builds", {}).values()}
        if live_a not in stamps:
            out.append("  It is NOT in the vault. Snapshot it before anything else "
                       "-- RUNBOOK.md:136.")
        for name, d in sorted(after.get("schema", {}).items()):
            if d.get("validated_against_build") not in (None, live_a):
                out.append(f"  schema/{name} is stamped "
                           f"{d['validated_against_build']}: stamp a NEW revision "
                           f"rather than editing it in place (PLAN.md §4 A3:700).")
        out.append("  The DH parameters rotate per build, so the client patch must "
                   "be redone in full (RUNBOOK.md §'One-time setup').")
    broken = [ln for ln in _diff_builds(before, after) if "RE-DERIVE" in ln]
    if broken:
        out.append(f"{len(broken)} signature(s) changed hit count. Every tool that "
                   f"owns one is untrustworthy until re-derived:")
        out += [f"  {ln.strip()}" for ln in broken]

    # The corpus verdict for the NEW build, read off the live install itself.
    # It is stated separately from `broken` above, which can only ever speak
    # about the vaulted builds -- and those cannot move across an update.
    sigs = after.get("live_install", {}).get("signatures")
    err = after.get("live_install", {}).get("signature_error")
    if err:
        out.append(f"  The signature corpus could not be read off the live "
                   f"install: {err}. That is UNKNOWN, not a pass.")
    elif not sigs:
        # NOTE the direction: `sigs` is read off the AFTER capture, taken just
        # now, not off the stored baseline -- the question is what the corpus
        # does on the build that is installed at this moment. So a miss here
        # means this run could not read the live install (absent, or not a PE),
        # never that the baseline is an old format.
        out.append(f"  No signature reading for {pinned.LIVE_INSTALL} in THIS "
                   f"run, so the corpus verdict for the new build is UNKNOWN, "
                   f"not a pass. Check the file exists and is readable.")
    elif live_b != live_a:
        bad = sorted(n for n, d in sigs.items() if not d.get("ok"))
        if bad:
            out.append(f"  {len(bad)} of {len(sigs)} signature(s) do NOT resolve at "
                       f"their expected count on build {live_a} -- RE-DERIVE: "
                       f"{', '.join(bad)}")
        else:
            out.append(f"  All {len(sigs)} signatures in the corpus resolve at their "
                       f"expected hit count ON BUILD {live_a} itself -- the "
                       f"byte-shape anchors held. (Read off {pinned.LIVE_INSTALL}, "
                       f"not off the vaulted builds.)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--before", action="store_true",
                   help="capture the before-state; run BEFORE accepting an update")
    g.add_argument("--after", metavar="BEFORE",
                   help="re-capture and report what moved since that baseline")
    ap.add_argument("--out", help="where to write the baseline (default: the vault)")
    ap.add_argument("--snapshot", action="store_true",
                    help="also run snapshot_client.py, which COPIES C:\\gw")
    ap.add_argument("--dat", help="an archive to snapshot with datcheck.py")
    a = ap.parse_args(argv)

    if a.before:
        path = _refuse_repo(a.out) if a.out else _default_path()
        state = capture(snapshot=a.snapshot, dat=a.dat)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=1, sort_keys=True)
        print(f"baseline written: {path}")
        for stamp, b in sorted(state["builds"].items()):
            print(f"  {stamp}  build {b.get('build')}")
        live = state["live_install"]
        print(f"  live install: {live.get('identify')} "
              f"(build {live.get('build', '?')})")
        n = sum(len(v.get("signatures", {})) for v in state["builds"].values())
        print(f"  {n} signature reading(s), {len(state['pins'])} pinned address(es)")
        if not a.snapshot:
            print("\n  NOTE: the client was NOT copied. `--snapshot` does that, and it "
                  "is the one\n  part of the before-state that cannot be recovered "
                  "afterwards (RUNBOOK.md:136).")
        return 0

    try:
        with open(a.after, encoding="utf-8") as fh:
            before = json.load(fh)
    except (OSError, ValueError) as exc:
        raise CannotRun(f"cannot read the baseline {a.after}: "
                        f"{type(exc).__name__}: {exc}")
    after = capture()
    lines, changed = diff(before, after)
    print(f"baseline {a.after}\n  captured {before.get('captured')}\n"
          f"  compared {after['captured']}\n")
    if not changed:
        print("nothing moved.")
        return 0
    print("what moved:")
    for ln in lines:
        print(ln)
    advice = _advice(before, after)
    if advice:
        print("\nwhat that means:")
        for ln in advice:
            print(f"  {ln}" if not ln.startswith("  ") else ln)
    print("\n(exit 1 = the state changed, which is a RESULT.)")
    return 1


def cli(argv=None):
    """`main()`, with the exit-2 contract actually honoured.

    `CannotRun` subclasses `SystemExit`, and `SystemExit("some text")` carries
    the TEXT as its code -- so raising it exits the process with status 1, not 2.
    The docstring promised 2 and the first version of this file delivered 1,
    which would have made "could not run" indistinguishable from "something
    moved" to any script reading the exit code. Caught by testing the PROCESS
    exit rather than the exception's `.code`.
    """
    try:
        return main(argv)
    except CannotRun as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(cli())
