r"""Per-agent roster of a capture: every create, WITH its coordinates, partitioned by
class tag -- the reader `studies/isle/PLAN.md` rung 1 asked for.

WHY THIS EXISTS WHEN `npcdefs.py` ALREADY READS CREATES. npcdefs is a TYPE compiler:
it collapses creates into per-definition rows and deliberately discards where each
body stood ("hostility is a fact about a SPAWN, not about a type" -- and so is a
position). The Isle arc needs the other half: WORLD_CREATE_AGENT field 5 is a clean
world vec2 that was measured, sent, decoded and then dropped on the floor by every
consumer in this repo. For the Isle's range markers the coordinates ARE the constants
-- `Short Bow Target` stands at the maximum shortbow range from the firing spot, so
reading its spawn position out of a capture is the measurement, no combat required.

WHAT A ROSTER ROW IS. One create event: time, agent id, class tag, definition slot
(NPC class only -- see below), position, plane, move speed, allegiance token. Creates
repeat -- visibility churn re-creates a body every time it re-enters compass range
(agent 44 is created four times per session at the identical position), so a roster
also offers STATIONS: creates grouped by (tag, definition, model, position, plane).
A stationary NPC is one station with many creates; a wanderer is many stations with
one create each. That distinction is measured, not configured.

THE PARTITION RULE, and why it is a refusal rather than a filter. Create field 2 is a
tagged reference: top nibble = class tag, low 16 bits = definition index -- but the
mask is only MEANINGFUL for the NPC class. Applying it to a player create yields a
number that looks like a definition and is not one (`npcdefs.py` has warned about this
since it was written), which is exactly the `tuple(v[3:5])` class of bug from the
other direction. So this module partitions FIRST and masks only tag 2. The corpus
holds tags {0 item/gadget, 2 NPC, 3 player} and nothing else; an unseen tag stops the
read loudly, because a new class of agent is a finding about the wire, not a row to
guess into an existing bucket.

CROSS-SESSION IDENTITY is the check that earns the module. Agent ids are recycled
per-instance handles, so "agent 44" means nothing across captures -- but stations
travel: two live sessions three days apart on map 148 declare byte-identical
(slot, model, position) for every static NPC. MEASURED, and pinned in
`test_agentroster.py`: slot 1470, model 116698, pos (8436.0, 4819.0) in both. That
reproducibility is what makes an Isle roster a TABLE rather than a session log, and
`cross_session()` computes the join -- keyed on the station, never on the agent id.

Origins never mix: `cross_session` refuses to compare captures whose `origin` labels
differ, same rule as every pooled consumer since `toolkit/origin.py`.

Output is a census on stdout, or JSON via --out. Send JSON to the vault, never the
repo: positions and ids measured off ArenaNet's wire are provenance-gated content and
graduate to `content/*.toml` only through an emitter with per-row provenance.

    python toolkit/authsrv/agentroster.py                    # census of live captures
    python toolkit/authsrv/agentroster.py --capture 20260810T235916
    python toolkit/authsrv/agentroster.py --out roster.json  # refuses paths in the repo
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import npcdefs  # noqa: E402
import tape  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# Class tags observed in create field 2's top nibble. MEASURED over every decoded
# live game connection (22,524 GAME_SMSG): {0, 2, 3} and nothing else.
TAG_ITEM = 0x0        # item/gadget class -- 117 creates over 32 agents in the corpus
TAG_NPC = 0x2         # the only class whose low 16 bits are a definition index
TAG_PLAYER = 0x3
KNOWN_TAGS = {TAG_ITEM, TAG_NPC, TAG_PLAYER}
TAG_NAMES = {TAG_ITEM: "item", TAG_NPC: "npc", TAG_PLAYER: "player"}


class RosterError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


def create_row(t, values, capture="?", connection="?"):
    """One WORLD_CREATE_AGENT, decoded values (opcode at index 0), as a roster row.

    Partition FIRST, mask only the NPC class. Split out of `read_roster` so the
    refusal is testable without a fixture capture -- a guard nothing can reach is a
    wish (`test_agentroster.py` feeds it a tag the corpus has never carried).
    """
    tagged = values[2]
    tag = tagged >> 28
    if tag not in KNOWN_TAGS:
        raise RosterError(
            f"{capture} {connection}: create at t={t:.3f} for agent "
            f"{values[1]} carries class tag {tag:#x} (field 2 = "
            f"{tagged:#010x}). The corpus holds tags 0/2/3 only; a "
            f"fourth class is a finding about the wire, not a row to "
            f"file under the nearest bucket.")
    x, y = values[5]
    return {
        "t": round(t, 4),
        "agent": values[1],
        "tag": tag,
        # The mask is meaningful ONLY for the NPC class; a masked
        # player word looks like a definition and is not one.
        "definition": (tagged & npcdefs.DEFINITION_MASK
                       if tag == TAG_NPC else None),
        "raw": tagged,
        "pos": (float(x), float(y)),
        "plane": values[6],
        "speed": round(float(values[9]), 4),
        "token": npcdefs._fourcc(values[12])
        if tag in (TAG_NPC, TAG_PLAYER) else None,
    }


def read_roster(capture_dirs, codec=None):
    """[connection roster] for every game channel in `capture_dirs`.

    Each roster is a dict:
        capture, connection, origin, map_id (or None when the wire has no VERSION
        frame to read), creates (list of create rows in wire order), and
        definitions {slot: {model_id, file_id, level, profession, enc_name}}.

    The whole tape must frame to its final byte, same rule as `npcdefs.read`:
    a partial decode silently drops the tail and every create after the break.
    """
    codec = codec or Codec()
    rosters = []
    for capture_dir in capture_dirs:
        for row in tape.channel_files(capture_dir):
            connection = row["connection"]
            info, events = tape.load_tape(capture_dir, connection)
            capture = info.get("capture") or os.path.basename(capture_dir)
            try:
                map_id = tape.client_version(capture_dir, connection)["map_id"]
            except tape.TapeError:
                map_id = None       # no c2s VERSION on this hop; honest absence
            msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            consumed, total, err = receipt
            if err is not None or consumed != total:
                raise RosterError(
                    f"{capture} {connection} did not frame to its final byte "
                    f"({consumed}/{total}, {err}). A partial roster is a roster "
                    f"missing whoever spawned after the break, silently.")

            defs = {}
            creates = []
            for t, opcode, values in msgs:
                if opcode == npcdefs.NPC_PROPERTIES:
                    d = defs.setdefault(values[1], npcdefs.Definition(values[1]))
                    d.declare(values, capture, connection)
                elif opcode == npcdefs.MONSTER_COMPOSITE:
                    d = defs.setdefault(values[1], npcdefs.Definition(values[1]))
                    models = values[2] if isinstance(values[2], list) else [values[2]]
                    if models:
                        d.model_id = models[0]
                elif opcode == npcdefs.CREATE_AGENT:
                    creates.append(create_row(t, values, capture, connection))
            rosters.append({
                "capture": capture,
                "connection": connection,
                "origin": info.get("origin", "unknown"),
                "map_id": map_id,
                "creates": creates,
                "definitions": {
                    index: d.row() for index, d in defs.items() if d.declared},
            })
    return rosters


def stations(roster):
    """Creates grouped by WHERE and WHAT: {(tag, definition, model, pos, plane): row}.

    The station key deliberately excludes the agent id -- ids are per-instance
    handles the server recycles. `model` is joined from the connection's own 0x0057
    declarations and is None when the definition never got one.
    """
    defs = roster["definitions"]
    out = {}
    for c in roster["creates"]:
        model = None
        if c["definition"] is not None and c["definition"] in defs:
            model = defs[c["definition"]].get("model_id")
        key = (c["tag"], c["definition"], model, c["pos"], c["plane"])
        row = out.setdefault(key, {
            "tag": c["tag"], "definition": c["definition"], "model_id": model,
            "pos": c["pos"], "plane": c["plane"], "creates": 0,
            "agents": set(), "tokens": set(), "first_t": c["t"], "last_t": c["t"],
        })
        row["creates"] += 1
        row["agents"].add(c["agent"])
        if c["token"]:
            row["tokens"].add(c["token"])
        row["first_t"] = min(row["first_t"], c["t"])
        row["last_t"] = max(row["last_t"], c["t"])
    return out


def cross_session(roster_a, roster_b):
    """Station keys present in both rosters, and each side's exclusives.

    Refuses to compare rosters of different origin: ours and live are two datasets
    and only one of them is an oracle (`toolkit/origin.py`).
    Player stations are excluded from the join -- a player is wherever the player
    walked, and two sessions agreeing on one would be a coincidence, not identity.
    """
    if roster_a["origin"] != roster_b["origin"]:
        raise RosterError(
            f"refusing to join rosters of different origin: "
            f"{roster_a['origin']!r} vs {roster_b['origin']!r}.")
    a = {k for k in stations(roster_a) if k[0] != TAG_PLAYER}
    b = {k for k in stations(roster_b) if k[0] != TAG_PLAYER}
    return {"both": a & b, "only_a": a - b, "only_b": b - a}


# ---------------------------------------------------------------- cli

def _census(rosters):
    for r in rosters:
        st = stations(r)
        tags = {}
        for c in r["creates"]:
            tags[c["tag"]] = tags.get(c["tag"], 0) + 1
        tag_text = ", ".join(f"{TAG_NAMES[t]}={n}" for t, n in sorted(tags.items()))
        print(f"\n{r['capture']}  {r['connection']}  map={r['map_id']}  "
              f"origin={r['origin']}")
        print(f"  {len(r['creates'])} create(s) [{tag_text or 'none'}], "
              f"{len(st)} station(s), {len(r['definitions'])} definition(s) declared")
        npc = sorted((k, v) for k, v in st.items() if k[0] == TAG_NPC)
        for _key, row in npc:
            print(f"    slot {row['definition']:>5}  model {row['model_id'] or '-':>7}"
                  f"  pos {row['pos']}  plane {row['plane']:>2}  "
                  f"x{row['creates']}  {','.join(sorted(row['tokens'])) or '-'}")

    # cross-session joins, per shared live map
    by_map = {}
    for r in rosters:
        if r["map_id"] and r["creates"]:
            by_map.setdefault((r["origin"], r["map_id"]), []).append(r)
    for (origin, map_id), group in sorted(by_map.items()):
        caps = {r["capture"] for r in group}
        if len(caps) < 2:
            continue
        a, b = group[0], group[-1]
        j = cross_session(a, b)
        print(f"\nmap {map_id} ({origin}): {a['capture']} vs {b['capture']} -- "
              f"{len(j['both'])} station(s) in both, "
              f"{len(j['only_a'])} only first, {len(j['only_b'])} only second")


def _jsonable(rosters):
    out = []
    for r in rosters:
        st = [dict(v, agents=sorted(v["agents"]), tokens=sorted(v["tokens"]),
                   pos=list(v["pos"]))
              for v in stations(r).values()]
        out.append({**r,
                    "creates": [dict(c, pos=list(c["pos"])) for c in r["creates"]],
                    "stations": st})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", action="append", default=None,
                    help="capture directory name under vault/captures/live/ "
                         "(repeatable; default: every keyed live capture)")
    ap.add_argument("--out", default=None,
                    help="write the full roster as JSON. Refused inside the repo: "
                         "measured ids and positions are vault material until an "
                         "emitter gives them per-row provenance.")
    a = ap.parse_args()

    # npcdefs.live_captures owns the selection AND the refusal -- a name that
    # matches nothing raises there rather than yielding an empty census here.
    caps = npcdefs.live_captures(names=a.capture)
    rosters = read_roster(caps)
    _census(rosters)

    if a.out:
        out = os.path.abspath(a.out)
        repo = os.path.dirname(os.path.dirname(HERE))
        if out.startswith(os.path.abspath(repo) + os.sep) and \
                not out.startswith(os.path.abspath(
                    vaultpath.vault()) + os.sep):
            raise RosterError(
                f"refusing to write {out} inside the repo. Positions and ids "
                f"measured off the wire go to the vault; content/*.toml rows go "
                f"through an emitter that stamps per-row provenance.")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(_jsonable(rosters), fh, indent=1)
        print(f"\nwrote {sum(len(r['creates']) for r in rosters)} create(s) "
              f"across {len(rosters)} connection(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
