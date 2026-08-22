r"""The respawn analyser: death -> revive intervals keyed so churn cannot fake one.

    python toolkit/authsrv/respawn.py                    # the live corpus, keyed
    python toolkit/authsrv/respawn.py --capture <dir>    # one capture (rung-9 mode)
    python toolkit/authsrv/respawn.py --naive            # the WRONG answer, printed
    python toolkit/authsrv/respawn.py --json             # for another tool

WHAT IT IS FOR. ISLE rung 9 measures respawn timers (GWW: practice targets 30 s,
Masters "will resurrect after two minutes ... at the location he/she was
defeated"). `studies/isle/PLAN.md` 3.4's skeptic pass found the naive reading
manufactures results, and this module is the consumer that rung's own rule says
must exist BEFORE the run is designed. Key on (definition slot, spawn position)
with a preceding-death bit required -- never on agent id.

THE THREE TRAPS, EACH ONE MEASURED IN THE VAULT:

1. AGENT IDS ARE RECYCLED ACROSS CREATURES. 20260807T143055 conn :62994: agent
   38 dies at 19.912 as definition slot 1434, is removed, and is re-created at
   74.779 as slot 1343 -- a DIFFERENT creature on the same id. Keyed on agent
   id that is a 54.9 s "respawn" for a creature that never respawned. Keyed on
   (slot, position) it is an open death and a separate creature, which is what
   it was. `naive_intervals()` computes the wrong answer on purpose so the test
   can demand the two disagree -- same pattern as `npcdefs.Intervals.last`.

2. VISIBILITY CHURN OUTNUMBERS DEATH ~40:1. A create is an agent entering the
   client's view and a remove is it leaving; neither says anything about dying.
   20260817T231139 conn :63805: agent 69 (slot 161) is created at the exact
   same position four times in 410 s with three removes between -- alive
   through all of it (its create-tick property 34 carries the CURRENT health
   fraction: 0.0685, 0.9572, 0.0065). A death->next-create join without the
   death bit would read any of those gaps as a respawn. Corpus-wide the vault
   holds ~2,900 NPC creates and 24 NPC deaths.

3. A CORPSE RE-ENTERING VIEW IS A CREATE TOO, and it is the create that most
   resembles a respawn. WORLD_CREATE_AGENT field 4 (`kind`) is 9 for a living
   NPC and 8 for a dead one: 20260810T235916 conn :61624 agent 43 dies at
   36.330, is removed at 52.437 (the player walked away), and is re-created at
   79.186 with kind 8 and health fraction 0.0 -- the corpse, still lying
   there. Death->create scores that as a 42.9 s respawn; it is evidence the
   creature is STILL DEAD, and this module uses it as exactly that (a lower
   bound on the interval).

WHAT A RESPAWN ACTUALLY LOOKS LIKE, OBSERVED. Retail revives the SAME agent in
place; it does not remove-and-recreate. The wire signature is `0x0026` (a
life-state byte, see below) flipping dead -> alive, with `0x00F1`'s dead bit
(0x10) confirming on the same tick:

  * Agent 69 above: killed at 419.149, corpse re-created kind 8 at 530.641,
    then STATUS 0x0 + FLAGS 9 at 539.648 -- a measured death->revive interval
    of 120.499 s, on the wire, against GWW's "two minutes" for the Zaishen
    sparring NPCs' shared mechanic.
  * 20260817T231139 conn :54071 (Isle of the Nameless): 19 deaths across five
    level-20 sparring NPCs, every one revived in place seconds later.

THE LIFE-STATE BYTE `0x0026` IS TWO TRACKS, and the NPC-only reading in
`authsrv.py` (histogram {9: 200, 8: 4}, "no other value exists in 204
samples") predates the captures that refute it. OBSERVED 2026-08-22 over the
grown corpus: NPC death/alive = 8/9, PLAYER death/alive = 4/5 (20260817T183756
conn :52294, agent 27: FLAGS 4 on the death tick, FLAGS 5 on the revive tick
10.044 s later, both with the 0x00F1 dead bit agreeing). Bit 0 reads as
"alive" on all four values; that pattern is RECONSTRUCTION, the four values
themselves are OBSERVED. Player deaths are tracked here but kept OUT of the
NPC key census -- player revive is its own mechanic (and rung 9 schedules
deliberate player deaths LAST because death penalty moves every denominator).

THE KEY. A creature's identity across id recycling is (definition slot, the
position of its first living create in this connection). Positions join by
EXACT float equality by default -- a stationary spawn repeats its coordinates
exactly (agent 69: four creates, 0.0 u apart; agent 278: three creates, 0.0 u
apart) and there is no free parameter. A wandering creature re-enters view at
a moved position and therefore FRAGMENTS into one key per witnessed position
(slot 115 does, in the Isle capture). That is deliberate: fragmentation can
only lose joins, never fabricate an interval. `--radius` merges keys within a
stated distance and prints every merge it makes; use it when a rung-9 report
needs the wanderers pooled, and read what it printed.

EVERY DEATH RESOLVES TO EXACTLY ONE OF:
  revived      FLAGS alive on the same chain: exact interval, the real number.
  recreated    a LIVING create later joins the same key after the corpse left
               view: the revive happened off-screen, so the interval is an
               UPPER BOUND, reported as one and never pooled with exact ones.
  open         nothing witnessed after the death (or the id was recycled to
               another creature): `dead_at_least` carries the last moment the
               corpse was seen still dead. A bound, not a failure.
A revive with NO open death on its chain (create-burst tails carry FLAGS 9
too, e.g. the burrow worms) claims nothing and is counted, not guessed about.

READ-ONLY. Opens capture directories, writes nothing. Standard library only.
Pooled runs refuse to mix capture origins (`toolkit/origin.py`) -- a census
over "the corpus" must not silently average our own server into retail.
"""
import argparse
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

import origin       # noqa: E402
import tape         # noqa: E402
import vaultpath    # noqa: E402
from codec import Codec  # noqa: E402

CREATE = 0x0020             # WORLD_CREATE_AGENT
REMOVE = 0x0021             # WORLD_REMOVE_AGENT
FLAGS = 0x0026              # AGENT_UPDATE_FLAGS -- the life-state byte
STATUS = 0x00F1             # AGENT_UPDATE_STATUS -- effect bitfield
PROP_FLOAT_SELF = 0x00A2    # [prop, agent, f32]
PROP_HEALTH_FRACTION = 34   # rides the create tick; 0.0 on every corpse create

STATUS_DEAD_BIT = 0x10

# The life-state values. 8/9 are the pair authsrv.py already names
# (AGENT_FLAGS_KILLED / BURROW_TAIL_0026_VALUE); 4/5 are the player track,
# OBSERVED 2026-08-22 (module docstring).
FLAGS_NPC_DEAD, FLAGS_NPC_ALIVE = 8, 9
FLAGS_PLAYER_DEAD, FLAGS_PLAYER_ALIVE = 4, 5
DEAD_VALUES = (FLAGS_NPC_DEAD, FLAGS_PLAYER_DEAD)
ALIVE_VALUES = (FLAGS_NPC_ALIVE, FLAGS_PLAYER_ALIVE)

# WORLD_CREATE_AGENT decoding, same reading as npcdefs.py: field 2's top
# nibble is the class tag (0x2 NPC, 0x3 player), low 16 bits the definition
# slot -- the mask is meaningless on a player create. Field 4 is `kind`:
# 9 = living NPC, 8 = dead NPC (corpse), 5 = player.
NPC_CLASS_TAG = 0x2
PLAYER_CLASS_TAG = 0x3
DEFINITION_MASK = 0xFFFF
KIND_NPC_ALIVE = 9
KIND_NPC_DEAD = 8


def _f32(dw):
    """Four bytes read as the float they are; as an int they never error."""
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


class _Chain:
    """One agent id's current occupant: who it is and whether they are alive."""

    __slots__ = ("tag", "slot", "anchor", "plane", "alive", "in_view",
                 "death", "seen_dead_until")

    def __init__(self, tag, slot, anchor, plane, alive):
        self.tag = tag
        self.slot = slot
        self.anchor = anchor        # (x, y) of the first living create
        self.plane = plane
        self.alive = alive
        self.in_view = True
        self.death = None           # the OPEN death record, if any
        self.seen_dead_until = None


def analyse(msgs, radius=None):
    """Walk one connection's decoded GAME_SMSG stream. Returns a result dict.

    `radius`: None joins spawn positions by exact equality (the default, no
    free parameter). A number merges keys within that distance and records
    every merge in result["merges"] -- nothing is merged silently.
    """
    chains = {}                       # agent id -> _Chain
    keys = {}                         # (slot, anchor) -> key dict
    counters = collections.Counter()
    player_deaths = []                # kept OUT of the key census on purpose
    unattributed = []                 # deaths of agents never seen created
    merges = []

    # Same-tick corroboration: STATUS and health-fraction values by (t, agent).
    status_at = collections.defaultdict(list)
    frac_at = {}
    for t, op, v in msgs:
        if op == STATUS and len(v) > 2:
            status_at[(t, int(v[1]))].append(int(v[2]))
        elif (op == PROP_FLOAT_SELF and len(v) > 3
              and int(v[1]) == PROP_HEALTH_FRACTION):
            frac_at[(t, int(v[2]))] = _f32(v[3])

    def key_for(slot, pos, plane):
        k = (slot, pos)
        if k not in keys:
            if radius is not None:
                for (s2, p2), existing in keys.items():
                    d = math.dist(pos, p2)
                    if s2 == slot and d <= radius:
                        merges.append({"slot": slot, "into": p2, "from": pos,
                                       "distance": d})
                        return existing
            keys[k] = {"slot": slot, "anchor": pos, "plane": plane,
                       "living_creates": 0, "corpse_creates": 0,
                       "removes": 0, "deaths": []}
        return keys[k]

    def dead_corroborated(t, agent, expect_dead):
        vals = status_at.get((t, agent))
        if not vals:
            return None
        return any(bool(s & STATUS_DEAD_BIT) == expect_dead for s in vals)

    for t, op, v in msgs:
        if op == CREATE and len(v) > 6:
            agent, ref, kind = int(v[1]), int(v[2]) & 0xFFFFFFFF, int(v[4])
            tag = (ref >> 28) & 0xF
            pos = (float(v[5][0]), float(v[5][1]))
            plane = int(v[6])
            if tag != NPC_CLASS_TAG:
                counters["non_npc_creates"] += 1
                chains[agent] = _Chain(tag, None, pos, plane, True)
                continue
            slot = ref & DEFINITION_MASK
            prior = chains.get(agent)
            if kind == KIND_NPC_DEAD:
                counters["corpse_creates"] += 1
                frac = frac_at.get((t, agent))
                if frac is not None and frac != 0.0:
                    counters["corpse_creates_health_nonzero"] += 1
                if (prior is not None and prior.slot == slot
                        and prior.death is not None):
                    # The corpse of a known death, back in view: the creature
                    # is STILL DEAD at t. Extend the bound -- unless the death
                    # itself was never witnessed (corpse churn), where there is
                    # no anchor to measure from.
                    if prior.death["t"] is not None:
                        prior.death["dead_at_least"] = t - prior.death["t"]
                    prior.in_view = True
                    continue
                # A corpse whose death we never saw. A later FLAGS-alive on
                # this chain is a revive with an UNKNOWN death time.
                ch = _Chain(tag, slot, pos, plane, alive=False)
                ch.death = {"t": None, "resolution": "open",
                            "unwitnessed": True, "dead_at_least": None}
                key_for(slot, pos, plane)["corpse_creates"] += 1
                key_for(slot, pos, plane)["deaths"].append(ch.death)
                chains[agent] = ch
                continue
            if kind != KIND_NPC_ALIVE:
                counters[f"npc_create_kind_{kind}"] += 1
            # A LIVING create. If this id carries an open death, this create
            # either closes it (same key: the revive happened off-screen,
            # upper bound) or breaks the chain (the id was recycled).
            if prior is not None and prior.death is not None:
                same_key = (prior.slot == slot and
                            (prior.anchor == pos or
                             (radius is not None
                              and math.dist(prior.anchor, pos) <= radius)))
                if same_key and prior.death["t"] is not None:
                    prior.death["resolution"] = "recreated"
                    prior.death["interval_upper"] = t - prior.death["t"]
                    counters["deaths_recreated"] += 1
                else:
                    counters["id_recycled_over_open_death"] += 1
            key = key_for(slot, pos, plane)
            key["living_creates"] += 1
            frac = frac_at.get((t, agent))
            if frac is not None and frac == 0.0:
                counters["living_create_health_zero"] += 1
            chains[agent] = _Chain(NPC_CLASS_TAG, slot, pos, plane, alive=True)

        elif op == REMOVE and len(v) > 1:
            ch = chains.get(int(v[1]))
            if ch is not None:
                ch.in_view = False
                if ch.tag == NPC_CLASS_TAG and ch.slot is not None:
                    k = keys.get((ch.slot, ch.anchor))
                    if k is not None:
                        k["removes"] += 1
                        if ch.death is None and ch.alive:
                            counters["churn_removes"] += 1

        elif op == FLAGS and len(v) > 2:
            agent, val = int(v[1]), int(v[2])
            ch = chains.get(agent)
            # The chain's class tag routes the track; the value is checked
            # against it rather than trusted (8/9 NPC, 4/5 player -- a
            # disagreement between value and tag is counted, never resolved
            # by guessing which one is right).
            if val in DEAD_VALUES:
                if ch is None:
                    unattributed.append({"t": t, "agent": agent, "flags": val})
                    counters["deaths_unattributed"] += 1
                elif ch.tag != NPC_CLASS_TAG:
                    if val != FLAGS_PLAYER_DEAD:
                        counters["flags_value_tag_mismatch"] += 1
                    ch.alive = False
                    player_deaths.append(
                        {"t": t, "agent": agent, "revive_t": None,
                         "interval": None,
                         "corroborated": dead_corroborated(t, agent, True)})
                elif ch.death is not None:
                    counters["double_death"] += 1
                else:
                    if val != FLAGS_NPC_DEAD:
                        counters["flags_value_tag_mismatch"] += 1
                    rec = {"t": t, "agent": agent, "resolution": "open",
                           "unwitnessed": False, "dead_at_least": 0.0,
                           "corroborated": dead_corroborated(t, agent, True)}
                    ch.alive = False
                    ch.death = rec
                    key_for(ch.slot, ch.anchor, ch.plane)["deaths"].append(rec)
                    counters["npc_deaths"] += 1
            elif val in ALIVE_VALUES:
                if ch is not None and ch.tag != NPC_CLASS_TAG:
                    if val != FLAGS_PLAYER_ALIVE:
                        counters["flags_value_tag_mismatch"] += 1
                    closed = False
                    for rec in reversed(player_deaths):
                        if rec["agent"] == agent and rec["revive_t"] is None:
                            rec["revive_t"] = t
                            rec["interval"] = t - rec["t"]
                            closed = True
                            break
                    if not closed:
                        counters["alive_flag_no_open_death"] += 1
                    ch.death = None
                    ch.alive = True
                elif ch is None or ch.death is None:
                    # Create-burst tails (the burrow worms) land here. Not a
                    # revive; there is no death to close.
                    counters["alive_flag_no_open_death"] += 1
                else:
                    if val != FLAGS_NPC_ALIVE:
                        counters["flags_value_tag_mismatch"] += 1
                    rec = ch.death
                    rec["resolution"] = "revived"
                    rec["revive_t"] = t
                    if rec["t"] is not None:
                        rec["interval"] = t - rec["t"]
                    else:
                        rec["interval"] = None   # corpse-first: death unseen
                        counters["revives_of_unwitnessed_death"] += 1
                    rec["revive_corroborated"] = dead_corroborated(
                        t, agent, False)
                    ch.death = None
                    ch.alive = True
                    counters["npc_revives"] += 1
            else:
                counters[f"flags_value_{val}"] += 1

    return {"keys": keys, "counters": counters, "player_deaths": player_deaths,
            "unattributed": unattributed, "merges": merges}


def naive_intervals(msgs):
    """THE WRONG ANSWER: death -> next create of the same AGENT ID.

    Exported so the test can demand it disagree with `analyse()` on the real
    corpus (agent 38's 54.9 s). Same reasoning as `npcdefs.Intervals.last`:
    a sabotage a test reimplements is a sabotage that drifts.
    """
    out = []
    deaths = [(t, int(v[1])) for t, op, v in msgs
              if op == FLAGS and len(v) > 2 and int(v[2]) in DEAD_VALUES]
    for dt, agent in deaths:
        nxt = [t for t, op, v in msgs
               if op == CREATE and len(v) > 1 and int(v[1]) == agent and t > dt]
        if nxt:
            out.append({"agent": agent, "death_t": dt,
                        "interval": min(nxt) - dt})
    return out


def scan(captures=None, radius=None):
    """Analyse every connection of the given captures (default: the corpus).

    Returns (results, origins): one result per connection, plus the per-capture
    origin map. Raises SystemExit if the pool mixes origins -- select, don't
    blend.
    """
    if captures is None:
        live = vaultpath.require_dir("captures", "live",
                                     why="the respawn census")
        captures = [os.path.join(live, s) for s in sorted(os.listdir(live))
                    if os.path.isdir(os.path.join(live, s))]
    codec = Codec()
    results, origins = [], {}
    for cap in captures:
        stamp = os.path.basename(cap.rstrip("\\/"))
        for chan in tape.channel_files(cap):
            conn = chan["connection"]
            # Origin is per CHANNEL FILE -- each carries its own origin record
            # (`origin.py` corroborates it against the recorded peers), and the
            # capture directory itself is not a classifiable thing.
            who, _why = origin.origin_of(chan["path"])
            origins[f"{stamp} {conn}"] = who
            try:
                _info, events = tape.load_tape(cap, conn)
                msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                              # noqa: BLE001
                results.append({"capture": stamp, "connection": conn,
                                "origin": who, "skipped": "undecodable"})
                continue
            res = analyse(msgs, radius=radius)
            res["capture"], res["connection"], res["origin"] = stamp, conn, who
            res["naive"] = naive_intervals(msgs)
            results.append(res)
    refuse_mixed(results)
    return results, origins


def refuse_mixed(results):
    """Raise rather than pool analysed connections of different origins."""
    pooled = {r["origin"] for r in results if not r.get("skipped")}
    if len(pooled) > 1:
        raise SystemExit(
            f"refusing to pool connections of mixed origin {sorted(pooled)}.\n"
            "A respawn census over 'the corpus' must not average our own "
            "server into retail. Pass --capture to select one capture.")
    return pooled


def _fmt_death(d):
    parts = [f"t={d['t']:.3f}" if d["t"] is not None else "t=unseen(corpse)"]
    res = d["resolution"]
    if res == "revived":
        iv = d.get("interval")
        parts.append(f"REVIVED at {d['revive_t']:.3f}"
                     + (f"  interval {iv:.3f} s" if iv is not None
                        else "  interval UNKNOWN (death unseen)"))
    elif res == "recreated":
        parts.append(f"recreated alive: interval <= {d['interval_upper']:.3f} s"
                     " (revive off-screen, upper bound)")
    else:
        dal = d.get("dead_at_least")
        parts.append("open"
                     + (f", still dead {dal:.3f} s after death"
                        if dal else ""))
    if d.get("corroborated") is False:
        parts.append("STATUS-DISAGREES")
    return "  ".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", help="one capture directory instead of the corpus")
    ap.add_argument("--radius", type=float, default=None,
                    help="merge spawn keys within this distance (printed, "
                         "never silent); default exact-match")
    ap.add_argument("--naive", action="store_true",
                    help="also print the agent-id-keyed WRONG answer")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    caps = [args.capture] if args.capture else None
    results, origins = scan(captures=caps, radius=args.radius)

    if args.json:
        def clean(r):
            r = dict(r)
            if "keys" in r:
                r["keys"] = [dict(v, key=[k[0], list(k[1])])
                             for k, v in r["keys"].items()]
                r["counters"] = dict(r["counters"])
            return r
        print(json.dumps({"origins": origins,
                          "connections": [clean(r) for r in results]}, indent=1))
        return 0

    total = collections.Counter()
    for r in results:
        if r.get("skipped"):
            print(f"{r['capture']} {r['connection']}: SKIPPED ({r['skipped']})")
            continue
        total.update(r["counters"])
        interesting = (r["counters"]["npc_deaths"]
                       or r["counters"]["deaths_unattributed"]
                       or r["player_deaths"])
        if not interesting:
            continue
        print(f"\n== {r['capture']} {r['connection']} "
              f"[origin {r['origin']}]")
        for merge in r["merges"]:
            print(f"   MERGED slot {merge['slot']} {merge['from']} -> "
                  f"{merge['into']} ({merge['distance']:.1f} u)")
        for (slot, pos), key in sorted(r["keys"].items()):
            if not key["deaths"]:
                continue
            print(f"   slot {slot} @ ({pos[0]:.2f},{pos[1]:.2f})  "
                  f"creates {key['living_creates']} corpse {key['corpse_creates']}"
                  f" removes {key['removes']}")
            for d in key["deaths"]:
                print(f"      {_fmt_death(d)}")
        for pd in r["player_deaths"]:
            iv = (f"revived at {pd['revive_t']:.3f}  interval "
                  f"{pd['interval']:.3f} s" if pd["revive_t"] is not None
                  else "no revive witnessed")
            print(f"   PLAYER death t={pd['t']:.3f}  {iv}")
        for u in r["unattributed"]:
            print(f"   UNATTRIBUTED death t={u['t']:.3f} agent {u['agent']} "
                  f"(no create in this connection; refusing to key it)")
        if args.naive:
            for n in r["naive"]:
                print(f"   [naive would claim] agent {n['agent']} death "
                      f"{n['death_t']:.3f} -> create +{n['interval']:.3f} s")

    print("\n-- corpus totals --")
    for k in sorted(total):
        print(f"   {k:36} {total[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
