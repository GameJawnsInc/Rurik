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
# 2026-08-07. The vault section declares a skip when there are no captures, so the floor
# sits at 14 -- two below, not seven, because the census now finds real live files.
LEDGER = checks.Ledger("capture origin", floor=14)


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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
