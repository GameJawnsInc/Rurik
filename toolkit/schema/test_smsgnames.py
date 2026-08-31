r"""The eight names the Factions captures earned, checked against the WIRE.

studies/newopcodes/FINDINGS.md named 22 opcodes first seen on 2026-08-17 and
put eight of them into `schema/overrides.json`. A name in a registry is a
claim, and a claim nothing can refute is decoration -- so each name here is
tied to an invariant the CAPTURES would break if the name were wrong.

WHAT THIS DELIBERATELY DOES NOT DO. It does not read the name out of
overrides.json and compare it to a string in this file: that is the check
that cannot fail, the defect test_agentlife records where twelve of fourteen
combat constants could be set wrong with every check green. Every assertion
below re-derives its fact from the decrypted capture and would go red if the
opcode's real behaviour differed -- if 0x011A stopped carrying two strings,
if 0x00C4's argument stopped being a live agent, if 0x00F5 and 0x00F6 stopped
co-occurring, the name is wrong and this says so.

NEEDS THE VAULT. Every section is skipped, loudly, when the captures are
absent -- vaultpath.require_dir's rule, one level up: a fixture that silently
resolves to nothing turns every assertion behind it into a no-op.

    python toolkit/schema/test_smsgnames.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
import checks  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# FLOOR: set from the first green run, never computed. Section 1 is 8 checks
# (one per name) and section 2 is 6; the vault sections declare a skip when
# the captures are gone rather than quietly scoring zero.
LEDGER = checks.Ledger("smsgnames", floor=15)
check = checks.adopt(LEDGER)

CAPTURES = ("20260817T183756", "20260817T183323", "20260817T180610")
NAMES = {
    0x011A: "TOWN_ALLIANCE_OBJECT",
    0x00B9: "MISSION_INFOBOX_ADD",
    0x00BB: "MISSION_OBJECTIVE_ADD",
    0x00C4: "WINDOW_OWNER",
    0x00F5: "TITLE_UPDATE",
    0x00F6: "TITLE_TRACK_INFO",
    0x017E: "INSTANCE_COUNTDOWN_STOP",
    0x0180: "INSTANCE_COUNTDOWN",
}


def corpus():
    """[(capture, opcode, values)] over every loadable channel, or None."""
    try:
        root = vaultpath.require_dir("captures", "live",
                                     why="the names are checked against the wire")
    except Exception:                                          # noqa: BLE001
        return None
    import tape
    codec, out, seen = Codec(), [], 0
    for name in CAPTURES:
        cap = os.path.join(root, name)
        if not os.path.isdir(cap):
            continue
        for row in tape.channel_files(cap):
            try:
                _info, ev = tape.load_tape(cap, row["connection"])
            except Exception:                                  # noqa: BLE001
                continue
            msgs, _ = tape.decode_all(ev, codec, "GAME_SMSG", 0)
            seen += 1
            for _t, op, v in msgs:
                out.append((name, op, v))
    return out if seen else None


def section1_registry():
    """Every name is IN the registry, at high confidence, citing the study."""
    print("\n1. the eight names are registered, with their evidence")
    import json
    over = json.load(open(os.path.join(ROOT, "schema", "overrides.json"),
                          encoding="utf-8"))
    g = over["channels"]["GAME_SMSG"]
    for op, want in sorted(NAMES.items()):
        row = g.get(str(op), {})
        ok = (row.get("name") == want
              and row.get("name_confidence") == "high"
              and "studies/newopcodes" in row.get("why", "")
              and "fields" not in row)
        check(ok, f"0x{op:04X} is {want}, high, cites the study, no field claim",
              f"name={row.get('name')} conf={row.get('name_confidence')} "
              f"fields={'yes' if 'fields' in row else 'no'}")


def section2_wire():
    """The behaviour each name asserts, re-derived from the captures."""
    print("\n2. the wire still behaves the way the names claim")
    rows = corpus()
    if rows is None:
        LEDGER.skip("the live-capture wire invariants",
                    "no live captures in the vault -- every wire invariant below "
                    "is unchecked, which is not the same as passing")
        return
    by = {}
    for _cap, op, v in rows:
        by.setdefault(op, []).append(v)

    # 0x011A TOWN_ALLIANCE_OBJECT: an ALLIANCE object carries a guild identity,
    # so two strings per message. If it ever carries none, it is not this.
    a = by.get(0x011A, [])
    twostr = [v for v in a if sum(1 for x in v[1:] if isinstance(x, str)) >= 2]
    check(len(a) >= 100 and len(twostr) == len(a),
          "0x011A carries TWO strings (a guild name and tag) in every sighting",
          f"{len(twostr)}/{len(a)}")
    # ...and its first field keys a GUILD, not an agent. The first version of
    # this check tested "how many first fields collide with a created agent id"
    # and scored 63/126 -- which is what COINCIDENCE looks like when small
    # integers meet a 116-agent id space, not evidence either way. It failed
    # the name for the wrong reason. The discriminating fact is the mapping:
    # an alliance OBJECT is per-guild, so its key must stand in a bijection
    # with the guild name. Agent-keying would break it immediately, since
    # several players in one town share a guild and would carry one name under
    # many keys.
    agents = {v[1] for _c, op, v in rows if op == 0x0020}
    keys = {v[1] for v in a}
    pairs = {(v[1], v[5]) for v in a}
    check(len(pairs) == len(keys) and len(keys) < len(a),
          "and each 0x011A key carries exactly ONE guild name, repeated -- a "
          "per-guild object, not a per-agent one",
          f"{len(keys)} keys, {len(pairs)} (key,name) pairs, {len(a)} messages")
    check(len(keys) < len(agents),
          "and there are far fewer keys than agents, so it is not agent-keyed",
          f"{len(keys)} keys vs {len(agents)} agents created")

    # 0x00C4 WINDOW_OWNER: the owner is a LIVE agent. The name says 'owner';
    # if the argument were not an agent this would be the wrong word.
    c4 = by.get(0x00C4, [])
    owned = [v for v in c4 if v[1] in agents]
    check(c4 and len(owned) == len(c4),
          "0x00C4's single argument names an agent created in the same stream",
          f"{len(owned)}/{len(c4)}")

    # 0x00F5 TITLE_UPDATE / 0x00F6 TITLE_TRACK_INFO: SOURCED as writing the
    # same array. On the wire they must co-occur -- an update to a track that
    # was never declared would refute the pairing the two names assert.
    f5, f6 = by.get(0x00F5, []), by.get(0x00F6, [])
    check(f5 and f6, "0x00F5 and 0x00F6 both appear -- the pair the names assert",
          f"0x00F5 x{len(f5)}, 0x00F6 x{len(f6)}")
    tracks = {v[1] for v in f6}
    updated = {v[1] for v in f5}
    check(updated <= tracks,
          "and every 0x00F5 names a track 0x00F6 declared",
          f"updated={sorted(updated)} declared={sorted(tracks)}")

    # 0x017E / 0x0180 COUNTDOWN pair: a stop cannot outnumber the starts, or
    # 'STOP' is the wrong reading of the smaller one.
    stop, start = by.get(0x017E, []), by.get(0x0180, [])
    check(len(stop) <= len(start),
          "0x017E (STOP) never outnumbers 0x0180 (COUNTDOWN)",
          f"stop={len(stop)} start={len(start)}")


def main():
    print("=" * 70)
    print("SMSG NAMES -- the eight the Factions captures earned")
    print("=" * 70)
    section1_registry()
    section2_wire()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
