"""Proves a capture of ArenaNet's server cannot be pooled with a capture of ours.

The failure being guarded is quiet, which is why it needs a test rather than a rule.
`test_movement_fidelity.py` pools every game-channel capture and prints one fidelity
number. If one of those files came from ArenaNet's server, that number would be a blend
of two different oracles, it would look entirely normal, and nothing would say so.

The vault now holds real live captures (R0b, 2026-08-07), and the census section pools
them against ours by name. The constructed cases stay because they cover shapes the vault
does not happen to contain -- a guard whose refusal has never been observed is the same
class of thing as a green test that asserts nothing.

And the stamp is CHECKED, not trusted: a `live` stamp on a file whose every recorded
address is loopback is refused. That case is not hypothetical either --
vault/dryrun/dryrun_wire.jsonl is exactly it, and it read as `live` for a day.

Also asserted: UNKNOWN is a real third value and never silently becomes OURS. A
two-valued scheme would force an unstamped file to be called one or the other, and
whichever default you pick is wrong exactly when it matters -- the first live capture
written by a tool that forgot to stamp.

AND SINCE 2026-08-13, WHICH BUILD, which is the same argument one level down.
`HANDOFF.md`:237 has required a build id in every capture manifest since day one and
nothing recorded one; that was survivable only while there was one build, and
`MOVE_TO_COORD` is 0x003C in one client and 0x003E in another. The stamp is CHECKED the
same way the origin stamp is -- a stated build the file's own VERSION record refutes is
REFUSED -- and UNKNOWN is again a distinct third value rather than "probably the pinned
one". The vault census answers the question `studies/crossbuild/PLAN.md` §10 left
UNVERIFIED -- no corpus figure pools two builds -- and SINCE 2026-08-14 it answers it the
way the origin half answers "is there a live capture": not by asserting the second
build's absence. "The whole vault is at most ONE build" went red the day the
build-38,833 arc's out-of-sample selftests landed, which is the same defect this file
already documents for `not groups[LIVE]` -- a check that goes red when the legitimate
thing arrives, whose obvious cure is to move the evidence or soften the guard. So the
census now covers every off-pin capture with a NAMED row -- an exact path, or a dated
campaign -- proves the pooling guard refuses the real files, and checks that everything
outside those rows still names the pin.

    python toolkit/test_origin.py
"""
import fnmatch
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import origin  # noqa: E402
import vaultpath  # noqa: E402

# 5 classification + 4 stamp-vs-contents + 4 refusal + 3 vault-corpus = 16, measured green
# 2026-08-07. 2026-08-13 added the BUILD stamp: 11 constructed + 2 vault-census, for 28
# with a vault; 2026-08-14 the build census grew from 2 checks to 4 when the vault gained
# its first off-pin captures, for 30 with a vault, measured. Both vault sections declare
# a skip when there are no captures, and a vault-less run scores 23 -- MEASURED with
# RURIK_VAULT pointed at an empty directory, not derived by subtraction, because a floor
# computed from a floor is how a section quietly stops running. The floor sits at 23 so a
# vault-less run still passes; the census checks are the only ones that need real
# captures.
LEDGER = checks.Ledger("capture origin", floor=23)

# The pinned client build -- cross-checked against clientscan/pinned.py in the census,
# because two authorities that can drift apart silently is this repo's oldest defect --
# and every vault capture of any OTHER build, acknowledged by a row here. A row is an
# fnmatch pattern over the path relative to captures/: an exact path for a stray, or a
# DATED CAMPAIGN (one directory, one producer, one day) for an authorized run. It is
# consulted ONLY for files whose own VERSION frame names an off-pin build, so a wide
# date pattern cannot launder anything -- a pin-build file is never tested against it.
# This exists because "at most one build in the vault" stopped being true on 2026-08-14
# and SILENT ACCUMULATION is the failure mode that replaced it; the granularity is the
# campaign rather than the file because the first day proved the finer grain is an
# outage, not a guard -- the parallel session's selftest campaign added a fourth 38833
# capture DURING this test's first green suite run, and a check that goes red on every
# rerun of authorized work is a check somebody deletes.
#
# 38833: ArenaNet's 2026-08-13 update. Loopback selftests recorded by authsrv.py on
# 2026-08-14 during the build-38,833 arc's out-of-sample campaign -- origin `ours`,
# channel `auth`, and the build is the client's OWN number off its VERSION frame, not
# our label (4 files when this row was written). The pin deliberately did not move
# (every address in studies/ is measured on 38797), so these are named exceptions, not
# the new corpus. No pooled figure reads them: they sit under captures/selftest/, and
# the one pooling consumer (test_movement_fidelity) selects game-channel files from
# authsrv/ and gamesrv/ and routes through require_single_build besides.
PIN = 38797
OFF_PIN_CAPTURES = {
    38833: (
        "selftest/authsrv-20260814T*-c1.jsonl",
    ),
}


def write(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return path


OURS_SESSION = [
    {"kind": "connect", "peer": "127.0.0.1:51000"},
    {"kind": "key_exchange_ok", "arc4_key": "a" * 40},
]
LIVE_SESSION = [
    origin.record("toolkit/capture/headless.py", origin.LIVE,
                  note="synthesised by test_origin.py; no real capture exists yet"),
    {"kind": "connect", "peer": "Auth1.ArenaNetworks.com:6112"},
]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        # --- classification ------------------------------------------------------
        stamped = write(os.path.join(tmp, "stamped.jsonl"),
                        [origin.record("toolkit/authsrv/authsrv.py", origin.OURS)]
                        + OURS_SESSION)
        LEDGER.ok(origin.origin_of(stamped)[0] == origin.OURS,
                  "a file with an OURS stamp reads as ours",
                  origin.origin_of(stamped)[1])

        live = write(os.path.join(tmp, "live.jsonl"), LIVE_SESSION)
        LEDGER.ok(origin.origin_of(live)[0] == origin.LIVE,
                  "a file with a LIVE stamp reads as live",
                  origin.origin_of(live)[1])

        legacy = write(os.path.join(tmp, "legacy.jsonl"), OURS_SESSION)
        LEDGER.ok(origin.origin_of(legacy)[0] == origin.OURS,
                  "an UNSTAMPED loopback file with our session markers infers ours",
                  "this is what keeps the 413 pre-existing captures usable")

        bare = write(os.path.join(tmp, "bare.jsonl"),
                     [{"kind": "connect", "peer": "127.0.0.1:1"}])
        LEDGER.ok(origin.origin_of(bare)[0] == origin.UNKNOWN,
                  "loopback alone is NOT enough to call a file ours",
                  "without our own session markers it stays unknown")

        remote = write(os.path.join(tmp, "remote.jsonl"),
                       [{"kind": "connect", "peer": "3.65.211.216:80"}])
        LEDGER.ok(origin.origin_of(remote)[0] == origin.UNKNOWN,
                  "a non-loopback peer is UNKNOWN, never inferred LIVE",
                  "the patcher captures hold public addresses too")

        # --- the stamp is a claim the file's own bytes can refute -----------------
        # Until 2026-08-07 origin_of returned the stated value and stopped reading, so
        # `live` was unfalsifiable -- and vault/dryrun/dryrun_wire.jsonl really is a
        # loopback capture stamped live. These are the checks that can now go red on it.
        lying = write(os.path.join(tmp, "lying.jsonl"),
                      [origin.record("a-tool", origin.LIVE),
                       {"kind": "wire", "src": "127.0.0.1:51000", "dst": "127.0.0.1:6112"}])
        who, why = origin.origin_of(lying)
        LEDGER.ok(who == origin.UNKNOWN and "CONTRADICTED" in why,
                  "a LIVE stamp on an all-loopback file is REFUSED, not believed", why)

        # The placeholder that defeated this check on its first real test: a non-address
        # in a peer field reads as "not loopback", which is exactly backwards.
        placeholder = write(os.path.join(tmp, "placeholder.jsonl"),
                            [origin.record("a-tool", origin.LIVE),
                             {"kind": "wire_meta", "client": "unknown", "server": "*:6112"},
                             {"kind": "wire", "src": "127.0.0.1", "dst": "127.0.0.1:6112"}])
        LEDGER.ok(origin.origin_of(placeholder)[0] == origin.UNKNOWN,
                  "and a placeholder like \"unknown\" cannot launder it past the check",
                  "is_address excludes non-addresses from the loopback vote")

        # The fields have to be the ones producers actually write. Strip the stamp from a
        # live-shaped capture: the addresses are right there and must be seen.
        unstamped_live = write(os.path.join(tmp, "unstamped_live.jsonl"),
                               [{"kind": "wire", "src": "10.0.0.210:63155",
                                 "dst": "54.164.212.177:80"},
                                {"kind": "version", "connection":
                                 "10.0.0.210:63155->54.164.212.177:80"}])
        who2, why2 = origin.origin_of(unstamped_live)
        LEDGER.ok(who2 == origin.UNKNOWN and "no peer" not in why2,
                  "src/dst/connection are read as peers, so a stamp-less live capture "
                  "is not reported as peerless", why2)
        LEDGER.ok(origin.origin_of(write(os.path.join(tmp, "pretty.json"),
                                         []) ) [1].startswith("no JSON records"),
                  "and 'I could not read anything' is not reported as 'there was nothing'",
                  "a pretty-printed .json parses as zero records, which is not zero peers")

        # --- the refusal, which is the reason this module exists ------------------
        try:
            origin.require_single([stamped, live], origin.OURS)
            refused = ""
        except SystemExit as exc:
            refused = str(exc)
        LEDGER.ok(bool(refused),
                  "pooling a LIVE capture with an OURS capture is REFUSED")
        LEDGER.ok("live" in refused and os.path.basename(live) in refused,
                  "and the refusal names the offending file and its origin")

        try:
            origin.require_single([stamped, bare], origin.OURS)
            refused_unknown = ""
        except SystemExit as exc:
            refused_unknown = str(exc)
        LEDGER.ok(bool(refused_unknown),
                  "an UNKNOWN file in an OURS pool is REFUSED too",
                  "unknown is not a synonym for ours")

        kept = origin.require_single([stamped, legacy], origin.OURS)
        LEDGER.ok(len(kept) == 2,
                  "a pool that really is all ours passes through unchanged",
                  "a guard that refuses the legitimate case is an outage")

    # --- and the real corpus, which is what the guard is protecting ---------------
    try:
        root = vaultpath.require_dir("captures", why="origin census")
    except SystemExit:
        root = None
    if not root:
        LEDGER.skip("vault corpus", "no captures directory")
    else:
        found = []
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ("captures-scrubbed",)]
            found += [os.path.join(base, f) for f in files if f.endswith(".jsonl")]
        if not found:
            LEDGER.skip("vault corpus", "no .jsonl captures on disk")
        else:
            groups = origin.partition(found)
            # This used to assert `not groups[LIVE]` -- "no live capture exists yet, so
            # nothing is at risk today". That is a check that goes RED on success: the first
            # real R0b capture landing in the vault is the project's biggest win and it
            # would have been reported as a regression, with the obvious cure being to move
            # the evidence or soften the guard. What the corpus is actually protected by is
            # below: a live file present must be REFUSED by the pooling guard, not absent.
            # So the assertion now holds in both states and gets stronger in the second.
            live = groups[origin.LIVE]
            census = (f"{len(found)} files: {len(groups[origin.OURS])} ours, "
                      f"{len(live)} live, {len(groups[origin.UNKNOWN])} unknown")
            if not live:
                LEDGER.ok(True, "no live capture in the corpus yet -- nothing to mix", census)
            else:
                refused = ""
                try:
                    origin.require_single([groups[origin.OURS][0], live[0]], origin.OURS)
                except SystemExit as exc:
                    refused = str(exc)
                LEDGER.ok(os.path.basename(live[0]) in refused,
                          "a live capture EXISTS, and pooling it with ours is refused by name",
                          census)
            LEDGER.ok(len(groups[origin.OURS]) > 100,
                      "the pre-existing corpus classifies as ours rather than unknown",
                      f"{len(groups[origin.OURS])} classified -- if this collapses, the "
                      f"inference rule broke and every consumer silently lost its corpus")
            # The one that actually matters: the pooled consumer's own selection.
            sys.path.insert(0, os.path.join(HERE, "authsrv"))
            import test_movement_fidelity as mf  # noqa: E402
            picked = mf.game_channel_captures()
            LEDGER.ok(all(origin.origin_of(p)[0] == origin.OURS for p in picked),
                      "every capture the movement score pools is ours",
                      f"{len(picked)} game-channel files")

    section_build()
    return LEDGER.verdict()


def _write(tmp, name, records):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return p


def section_build():
    """WHICH BUILD -- the same argument as WHICH SERVER, one level down.

    `HANDOFF.md`:237 has required a build id in every capture manifest since day
    one and nothing recorded one. It was survivable only while there was one
    build, and the risk is not hypothetical: `MOVE_TO_COORD` is 0x003C in one
    client and 0x003E in another, so a figure pooled across two builds is about
    neither -- exactly what this module already refuses for two servers.
    """
    print("\nbuild stamp")
    with tempfile.TemporaryDirectory() as tmp:
        ver = {"kind": "version", "channel": "game", "build": 38797}

        p = _write(tmp, "inferred.jsonl", [origin.record("t"), ver])
        b, why = origin.build_of(p)
        LEDGER.ok(b == 38797, "a build is inferred from the client's own VERSION record", why)

        p = _write(tmp, "stamped.jsonl", [origin.record("t", build=38797), ver])
        b, why = origin.build_of(p)
        LEDGER.ok(b == 38797 and "corroborated" in why,
                  "an explicit stamp is corroborated by the contents", why)

        # THE control, and the lesson origin_of learned the hard way: a stamp
        # nothing checks is an unfalsifiable self-declaration.
        p = _write(tmp, "lying.jsonl", [origin.record("t", build=38519), ver])
        b, why = origin.build_of(p)
        LEDGER.ok(b is origin.BUILD_UNKNOWN and "CONTRADICTED" in why,
                  "a stamp the file's own contents refute is REFUSED, not believed", why)

        p = _write(tmp, "two.jsonl", [origin.record("t"), ver,
                                      {"kind": "version", "build": 38519}])
        b, why = origin.build_of(p)
        LEDGER.ok(b is origin.BUILD_UNKNOWN and "CONTRADICTED" in why,
                  "and one capture naming two builds is refused", why)

        p = _write(tmp, "silent.jsonl", [origin.record("t"), {"kind": "frame"}])
        b, why = origin.build_of(p)
        LEDGER.ok(b is origin.BUILD_UNKNOWN,
                  "a capture naming no build is UNKNOWN, not the pinned one", why)
        LEDGER.ok(origin.BUILD_UNKNOWN is None and 38797 is not origin.BUILD_UNKNOWN,
                  "and UNKNOWN is a distinct third value, as it is for origin")

        # Pooling.
        old = _write(tmp, "old.jsonl", [origin.record("t"),
                                        {"kind": "version", "build": 38519}])
        new = _write(tmp, "new.jsonl", [origin.record("t"), ver])
        try:
            origin.require_single_build([old, new], what="a test")
            LEDGER.ok(False, "two builds in one corpus are REFUSED", "it pooled them")
        except origin.MixedBuilds as exc:
            LEDGER.ok("MOVE_TO_COORD" in str(exc),
                      "two builds in one corpus are REFUSED",
                      "and the message says why it matters")

        # POSITIVE CONTROL: without it, the refusal above is satisfied by a
        # function that refuses every corpus.
        b, kept = origin.require_single_build([new, _write(
            tmp, "new2.jsonl", [origin.record("t"), ver])], what="a test")
        LEDGER.ok(b == 38797 and len(kept) == 2,
                  "while one build passes and keeps every file", str(b))

        # UNKNOWN is tolerated by default -- 555 of the vault's 1,675 files name
        # no build, because a frame log names it once per SESSION -- but never
        # silently, and a caller can refuse it.
        b, kept = origin.require_single_build([new, p], what="a test")
        LEDGER.ok(b == 38797 and len(kept) == 2,
                  "an unknown-build file does not break a single-build corpus")
        try:
            origin.require_single_build([new, p], what="a test", allow_unknown=False)
            LEDGER.ok(False, "and allow_unknown=False refuses it", "it allowed it")
        except origin.MixedBuilds:
            LEDGER.ok(True, "and allow_unknown=False refuses it")

    try:
        root = vaultpath.require_dir("captures", why="build census")
    except BaseException as exc:                             # noqa: BLE001
        LEDGER.skip("the vault build census", f"no captures: {exc}")
        return
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("captures-scrubbed",)]
        found += [os.path.join(base, f) for f in files if f.endswith(".jsonl")]
    groups = origin.partition_builds(found)
    known = {b: v for b, v in groups.items() if b is not origin.BUILD_UNKNOWN}
    census = (f"{ {b: len(v) for b, v in sorted(known.items())} } "
              f"+ {len(groups.get(origin.BUILD_UNKNOWN, []))} unknown")

    # This census asserted "the whole vault is at most ONE client build" until
    # 2026-08-14, when the three 38,833 selftests named in OFF_PIN_CAPTURES turned it
    # red. Same defect as the origin census's old `not groups[LIVE]`, documented above:
    # a check that goes RED when the legitimate thing arrives. What actually protects a
    # corpus figure is the guard at the pooling site, so the census now claims what is
    # true and stays checkable with a second build on disk: off-pin captures are NAMED
    # per file (accumulation is never silent), the refusal is EXERCISED on the real
    # files, and everything outside the named rows is still the pin.
    off_pin = {b: v for b, v in known.items() if b != PIN}

    def rel(p):
        return os.path.relpath(p, root).replace(os.sep, "/")

    stray = [rel(p) for b in sorted(off_pin) for p in off_pin[b]
             if not any(fnmatch.fnmatch(rel(p), pat)
                        for pat in OFF_PIN_CAPTURES.get(b, ()))]
    LEDGER.ok(not stray,
              "every off-pin capture is covered by a row this test NAMES",
              (f"UNLISTED: {', '.join(stray[:3])}"
               + (f" (+{len(stray) - 3} more)" if len(stray) > 3 else "")
               + " -- a second-build capture is a deliberate act: add its row to "
                 "OFF_PIN_CAPTURES with its provenance, or it is drift and the "
                 "producer needs finding") if stray else census)

    pin_files = known.get(PIN, [])
    off_files = [p for b in sorted(off_pin) for p in off_pin[b]]
    if not off_files:
        LEDGER.ok(True, "one build in the corpus -- nothing to mix", census)
    elif not pin_files:
        LEDGER.ok(False,
                  "a second build EXISTS, and pooling it with the pin is refused by name",
                  "no pinned-build capture left in the vault to exercise the refusal "
                  "against -- which is its own emergency")
    else:
        refused = ""
        try:
            origin.require_single_build([pin_files[0], off_files[0]],
                                        what="the build census")
        except origin.MixedBuilds as exc:
            refused = str(exc)
        LEDGER.ok(os.path.basename(off_files[0]) in refused,
                  "a second build EXISTS, and pooling it with the pin is refused by name",
                  census)

    LEDGER.ok(set(known) - set(OFF_PIN_CAPTURES) <= {PIN},
              f"outside those named exceptions the vault is at most ONE build, "
              f"the pin ({PIN})",
              "the surviving half of the old invariant -- it is what keeps every "
              "pooled figure in studies/ a figure about one client, which is what "
              "PLAN.md §10's UNVERIFIED flag asked")

    # And the pin this census is WRITTEN against must still be the registry's pin.
    # The literal above is deliberate -- this census states a measured fact about the
    # corpus, not a policy -- but the day clientscan/pinned.py moves its pin, that fact
    # needs re-deciding, and two authorities drifting apart silently is the exact
    # staleness failure the top of CLAUDE.md is about.
    sys.path.insert(0, os.path.join(HERE, "clientscan"))
    import pinned  # noqa: E402
    LEDGER.ok(pinned.BUILD == PIN,
              "and the pin this census is written against is still the registry's pin",
              f"clientscan/pinned.py says {pinned.BUILD}; if these disagree, the pin "
              f"moved and this census must be re-decided, not patched green")


if __name__ == "__main__":
    sys.exit(main())
