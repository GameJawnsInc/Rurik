r"""The morale census over the live corpus: `0x00EE` attr 10 and `0x009C`.

    python toolkit/authsrv/moralescan.py               # the census
    python toolkit/authsrv/moralescan.py --window      # + the death tick, in full

WHAT IT IS FOR. `studies/morale/FINDINGS.md` rests on two negatives and one
positive, and all three are counts over ArenaNet's own captures:

  * `0x00EE` carries attr 10 forty times and the ONLY non-zero delta in the
    corpus is a single -15,
  * `0x009C` fires 83 times and the ONLY value that is not 100 is a single 85,
  * and both land on the same tick, on the same agent, in the same tape.

A claim of the form "the only X in the corpus" decays the moment a capture is
added, which is exactly what happened to the sentence this replaces: the kill
study wrote `0x009C` off as "n=1, first-witness, uncatalogued" over two captures,
and there are fourteen now. So the census is a script rather than a number in a
document -- re-run it and the paragraph either still holds or names its own
counter-example.

READ-ONLY. It opens `vault/captures/live/` and writes nothing anywhere.
Standard library only, like everything else on this path.
"""
import argparse
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

import codec        # noqa: E402
import tape         # noqa: E402
import vaultpath    # noqa: E402

OVERRIDES = os.path.join(ROOT, "schema", "overrides.json")
OV = json.load(open(OVERRIDES, encoding="utf-8"))["channels"]

# The three opcodes this is about, plus the two the death tick moves.
PLAYER_ATTR_UPDATE = 0x00EE     # [attr_id, delta] -- PLAYER-scoped, no agent id
PLAYER_ATTR_SET = 0x00E9        # 15 dwords, field 10 = morale, absolute
AGENT_MORALE = 0x009C           # [agent_id, percent] -- per AGENT, absolute
PROP_INT = 0x009F               # [prop, agent, value]  41 = energy, 42 = health
PROP_FLOAT = 0x00A2             # [prop, agent, f32]    43 = energy regen
PLAYER_INFO = 0x0059            # AGENT_CREATE_PLAYER -- see WHOSE_AGENT below
PROP_MAX_ENERGY = 41            # property 41 on 0x009F: SELF-SCOPED (see below)
ATTR_MORALE = 10
MORALE_BASELINE = 100


def name(op):
    r = OV.get("GAME_SMSG", {}).get(str(op))
    return r["name"] if r and "name" in r else f"0x{op:04X}"


def s32(v):
    """A dword field read as SIGNED -- attr deltas are negative half the time.

    The same trap `_f32_of` documents on the server: whether four bytes are
    signed, unsigned or a float is a fact about the message, and reading -15 as
    4,294,967,281 never errors.
    """
    v = int(v) & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def f32(v):
    return struct.unpack("<f", struct.pack("<I", int(v) & 0xFFFFFFFF))[0]


def live_captures():
    """Every live capture directory, oldest first."""
    root = vaultpath.require_dir("captures", "live")
    return [os.path.join(root, d) for d in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, d))]


def scan(codec_obj):
    """(rows, stats) -- one row per morale-bearing message in the corpus."""
    rows, stats = [], collections.Counter()
    for cap in live_captures():
        stamp = os.path.basename(cap)
        try:
            conns = tape.chain(cap)
        except Exception as exc:                      # noqa: BLE001
            stats["captures_unreadable"] += 1
            rows.append({"kind": "error", "capture": stamp, "why": str(exc)})
            continue
        for conn in conns:
            try:
                meta, events = tape.load_tape(cap, conn)
                msgs, receipt = tape.decode_all(events, codec_obj, "GAME_SMSG")
            except Exception as exc:                  # noqa: BLE001
                stats["connections_unreadable"] += 1
                rows.append({"kind": "error", "capture": stamp,
                             "connection": conn, "why": str(exc)})
                continue
            stats["connections"] += 1
            stats["messages"] += len(msgs)
            # WHOSE AGENT IS OURS, so a per-agent value can say whether it is
            # about US or about a party member.
            #
            # CORRECTED 2026-08-21, and the old rule was wrong 20 times in 44.
            # This used to take the FIRST 0x0059 and call its agent id ours,
            # with a comment asserting "field 2 is the receiving player's own
            # agent id". 0x0059 is AGENT_CREATE_PLAYER and the server
            # broadcasts one for EVERY player in the instance -- 16 to 56 of
            # them in a busy outpost -- so the first one is whoever the server
            # happened to send first. MEASURED over the live corpus: the two
            # rules agree on 24 connections and DISAGREE on 20, e.g. this rule
            # said agent 16 where the observer is 767.
            #
            # PROPERTY 41 (MAX ENERGY) IS THE SOUND ANCHOR because it is
            # self-scoped: studies/skills/FINDINGS.md 23 measured 97 of them in
            # the corpus and every one names the observing player's own agent.
            # An independent second route -- 0x0199 INSTANCE_LOAD_INFO's player
            # number mapped through 0x0059's (player_number, agent_id) pairs --
            # agrees with it on every connection where both resolve.
            #
            # NO FALLBACK TO THE OLD RULE. A connection with no property 41
            # leaves `me` None and its rows unflagged, which is the honest
            # answer; guessing would put the label back on the 45% that were
            # wrong. Nothing published from this scanner depended on `mine` --
            # studies/morale's census claims count VALUES across all agents --
            # so this corrects a latent defect rather than a wrong result.
            me = None
            for _t, op, vals in msgs:
                if op == PROP_INT and len(vals) > 2 and int(vals[1]) == PROP_MAX_ENERGY:
                    me = int(vals[2])
                    break
            for t, op, vals in msgs:
                v = vals[1:]
                if op == PLAYER_ATTR_UPDATE and int(v[0]) == ATTR_MORALE:
                    rows.append({"kind": "delta", "capture": stamp,
                                 "connection": conn, "t": t,
                                 "value": s32(v[1])})
                elif op == AGENT_MORALE:
                    rows.append({"kind": "agent", "capture": stamp,
                                 "connection": conn, "t": t,
                                 "agent": int(v[0]), "value": int(v[1]),
                                 "mine": me is not None and int(v[0]) == me})
                elif op == PLAYER_ATTR_SET:
                    rows.append({"kind": "set", "capture": stamp,
                                 "connection": conn, "t": t,
                                 "value": int(v[ATTR_MORALE]),
                                 "level": int(v[9])})
                elif op == PROP_INT and int(v[0]) in (41, 42):
                    rows.append({"kind": "max", "capture": stamp,
                                 "connection": conn, "t": t,
                                 "prop": int(v[0]), "agent": int(v[1]),
                                 "value": s32(v[2]),
                                 "mine": me is not None and int(v[1]) == me})
                elif op == PROP_FLOAT and int(v[0]) == 43:
                    rows.append({"kind": "regen", "capture": stamp,
                                 "connection": conn, "t": t,
                                 "agent": int(v[1]), "value": f32(v[2]),
                                 "mine": me is not None and int(v[1]) == me})
    return rows, stats


def death_window(codec_obj, row, before=1.0, after=12.0):
    """Every message within a window of one morale event, for reading by eye."""
    cap = os.path.join(vaultpath.require_dir("captures", "live"), row["capture"])
    _meta, events = tape.load_tape(cap, row["connection"])
    msgs, _receipt = tape.decode_all(events, codec_obj, "GAME_SMSG")
    t0 = row["t"]
    out = []
    for t, op, vals in msgs:
        if t0 - before <= t <= t0 + after:
            out.append((t, op, list(vals[1:])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--window", action="store_true",
                    help="also print every message around each non-baseline "
                         "morale event")
    ap.add_argument("--json", action="store_true",
                    help="the rows, for a consumer rather than a reader")
    args = ap.parse_args(argv)

    codec_obj = codec.Codec(overrides=OVERRIDES)
    rows, stats = scan(codec_obj)
    if args.json:
        print(json.dumps({"rows": rows, "stats": dict(stats)}, indent=1))
        return 0

    deltas = [r for r in rows if r["kind"] == "delta"]
    agents_ = [r for r in rows if r["kind"] == "agent"]
    sets = [r for r in rows if r["kind"] == "set"]
    errors = [r for r in rows if r["kind"] == "error"]

    print(f"{stats['connections']} game connections, "
          f"{stats['messages']:,} messages")
    if errors:
        print(f"  {len(errors)} unreadable tape(s):")
        for r in errors:
            print(f"    {r['capture']} {r.get('connection', '')}: {r['why']}")

    dh = collections.Counter(r["value"] for r in deltas)
    ah = collections.Counter(r["value"] for r in agents_)
    sh = collections.Counter(r["value"] for r in sets)
    print(f"\n0x00EE attr {ATTR_MORALE} (morale delta): {len(deltas)} sighting(s)"
          f"  values {dict(sorted(dh.items()))}")
    print(f"0x009C (per-agent morale):     {len(agents_)} sighting(s)"
          f"  values {dict(sorted(ah.items()))}")
    print(f"0x00E9 field {ATTR_MORALE} (morale, absolute): {len(sets)} sighting(s)"
          f"  values {dict(sorted(sh.items()))}")

    odd = [r for r in deltas if r["value"] != 0]
    odd += [r for r in agents_ if r["value"] != MORALE_BASELINE]
    odd += [r for r in sets if r["value"] != MORALE_BASELINE]
    print(f"\nEVERY departure from baseline in the corpus ({len(odd)}):")
    for r in sorted(odd, key=lambda r: (r["capture"], r["t"])):
        who = f" agent {r['agent']}" if "agent" in r else ""
        print(f"  {r['capture']} {r['connection']} t={r['t']:8.3f} "
              f"{r['kind']}{who} = {r['value']}")
    if not odd:
        print("  none -- every morale value in the corpus is the neutral 100")

    if args.window:
        for r in sorted(odd, key=lambda r: (r["capture"], r["t"])):
            print(f"\n===== {r['capture']} {r['connection']} "
                  f"t={r['t']:.3f} {r['kind']} = {r['value']} =====")
            for t, op, body in death_window(codec_obj, r):
                print(f"  t={t:9.3f} 0x{op:04X} {name(op):34s} {body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
