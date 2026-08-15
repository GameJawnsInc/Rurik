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
UNVERIFIED -- no corpus figure pools two builds -- and it is scoped to the RESEARCH
corpus: `selftest/` is excluded from the walk the way `captures-scrubbed/` already is.

SINCE 2026-08-14 that scoping is load-bearing. Build 38833 shipped, and the suite's own
runs began writing 38833-stamped fixtures into captures/selftest/ -- test_handshake
drives whichever client the newest key matches (`studies/crossbuild/FINDINGS.md` §7.7)
-- so a census over the whole vault went red over its own byproducts, and would go red
again on every future suite run. Two sessions hit that red in parallel and fixed it two
ways: one NAMED the off-pin files in an allowlist, which the producer refutes -- the
suite itself writes them, so the list stales on every run -- and one excluded the
fixtures, which stands: a self-test artifact is not research data, and counting it
re-creates one level up the very contamination `selftest/` was split out to prevent.
What survives from the allowlist branch: the pooling refusal is EXERCISED on a real
mixed pair (the fixtures supply a genuine 38833 file), and the census's 38797 is
cross-checked against `clientscan/pinned.py` so the pin cannot move without this
census going red until re-decided. A REAL second-build capture in the research corpus
still turns the census red -- that is the point, not a defect.

    python toolkit/test_origin.py
"""
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
        # `selftest` joined `captures-scrubbed` here on 2026-08-14, and the
        # reason is the one test_handshake.py already gives for the directory
        # existing at all: its output "used to share vault/captures/authsrv/
        # with real client sessions ... two self-test captures were read as
        # evidence of successful client logins that never happened." The files
        # were split out so they could not be mistaken for research data -- and
        # this census then walked the whole tree and counted them as exactly
        # that, re-creating the contamination one level up.
        #
        # It surfaced the moment the numbers could disagree: build 38833 was
        # patched, `test_handshake.py` began announcing 38833 (it had been
        # claiming a hardcoded 38797 while driving whatever client the newest
        # key matched -- see studies/crossbuild/FINDINGS.md §7.7), and three
        # runs of the SUITE ITSELF put three 38833-stamped files in the vault.
        # The corpus then read {38797: 1828, 38833: 3} and this check went red
        # over its own test fixtures.
        #
        # THE GUARD KEEPS ITS TEETH. The claim below is about the corpus the
        # figures in studies/ are computed over, and a self-test artifact is
        # not one of those. The day a REAL capture is taken on a second build,
        # this still goes red -- which is the whole point, since opcodes drift
        # between builds and pooling two builds' captures is the error
        # `origin.py` exists to prevent.
        dirs[:] = [d for d in dirs if d not in ("captures-scrubbed", "selftest")]
        found += [os.path.join(base, f) for f in files if f.endswith(".jsonl")]
    groups = origin.partition_builds(found)
    known = {b: v for b, v in groups.items() if b is not origin.BUILD_UNKNOWN}
    LEDGER.ok(len(known) <= 1,
              "the research corpus is at most ONE client build (selftest excluded)",
              f"{ {b: len(v) for b, v in known.items()} } "
              f"+ {len(groups.get(origin.BUILD_UNKNOWN, []))} unknown")
    if known:
        LEDGER.ok(set(known) == {38797},
                  "and that build is 38797",
                  "MEASURED 2026-08-13, still true on 2026-08-14 after build "
                  "38833 shipped: no RESEARCH capture has been taken on it. "
                  "Said precisely because it is not the same as 'no capture' -- "
                  "the suite's own test_handshake.py has put 38833-stamped "
                  "files in vault/captures/selftest/, which is why the walk "
                  "above excludes that directory. The corpus figures in "
                  "studies/ are not pooling builds, which resolves PLAN.md "
                  "§10's UNVERIFIED flag")

    # Two additions from the branch that fixed this same red in parallel (both
    # sessions hit it on 2026-08-14; the selftest exclusion above is the scoping
    # that stands, and these two survive it).
    #
    # The refusal, exercised on REAL files. The constructed pair earlier proves
    # `require_single_build` refuses in principle; the suite's own fixtures now
    # give the vault a real 38833 file, so the guard can also be proven against
    # actual captures -- the same upgrade the origin census made when the first
    # live capture landed, because a refusal that has never fired on a real
    # artifact is the same class of thing as a green test that asserts nothing.
    # The fixture is found by reading each candidate's bytes (`build_of`), never
    # by filename -- and if the fixtures age out, this degrades to "nothing to
    # mix", not to red.
    off_pin = None
    fixtures = os.path.join(root, "selftest")
    if os.path.isdir(fixtures):
        for name in sorted(os.listdir(fixtures), reverse=True):
            if name.endswith(".jsonl"):
                p = os.path.join(fixtures, name)
                b = origin.build_of(p)[0]
                if b is not origin.BUILD_UNKNOWN and b != 38797:
                    off_pin = p
                    break
    pin_files = known.get(38797, [])
    if off_pin is None or not pin_files:
        LEDGER.ok(True,
                  "no real mixed pair on disk -- the pooling refusal rests "
                  "on the constructed pair",
                  "an off-pin fixture and a pinned research capture are both needed")
    else:
        refused = ""
        try:
            origin.require_single_build([pin_files[0], off_pin],
                                        what="the build census")
        except origin.MixedBuilds as exc:
            refused = str(exc)
        LEDGER.ok(os.path.basename(off_pin) in refused,
                  "a real second-build file EXISTS (a selftest fixture), and "
                  "pooling it with the research corpus is refused by name",
                  origin.build_of(off_pin)[1])

    # And the 38797 above must still be the registry's pin. The literal is
    # deliberate -- this census states a measured fact about the corpus, not a
    # policy -- but the day clientscan/pinned.py moves its pin, that fact needs
    # re-deciding, and two authorities drifting apart silently is the exact
    # staleness failure the top of CLAUDE.md is about.
    sys.path.insert(0, os.path.join(HERE, "clientscan"))
    import pinned  # noqa: E402
    LEDGER.ok(pinned.BUILD == 38797,
              "and the build this census is written against is still the registry's pin",
              f"clientscan/pinned.py says {pinned.BUILD}; if these disagree, the pin "
              f"moved and this census must be re-decided, not patched green")


if __name__ == "__main__":
    sys.exit(main())
