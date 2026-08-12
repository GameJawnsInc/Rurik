r"""Turn a live capture into NPC definition rows: the first capture -> content compiler.

WHAT THIS IS FOR. `PLAN.md` R4c-2 wants monster types with real stats. Every fact it
needs has been sitting in `vault/captures/live/` since 2026-08-07 and nothing in this
repo could turn a capture into a content row -- `studies/reconstruction/FINDINGS.md`
§8.6 calls that "the half nobody owns", and the industry comparable is explicit:
WowPacketParser is not a sniffer, it is a compiler. This is the compiler, for one
message family.

WHAT IT EMITS, and the boundary it sits on. Everything here is a fact MEASURED off
ArenaNet's own bytes -- a definition index, a file id, a scale word, a flags word, a
level byte, a speed. Under the owner's ruling of 2026-08-11 (`PLAN.md` §7 Q3) that is
the permitted side of the provenance gate: measurement, not expression. `enc_name` is
the ruling's other half made concrete -- **the ids are committed and the string is
resolved at run time by the client's own text system**, so no ArenaNet text is ever
written to a file here. Nothing in this module reads or writes a name.

THE ONE NON-OBVIOUS PIECE, and it is the reason the module exists rather than a
twenty-line script: **a property message must be joined to the create IN EFFECT AT ITS
TIMESTAMP, not to the agent's last create.** Agent ids are recycled -- `studies/tape`
T3 and `studies/divergence` D1 both measure it, 19 of 45 ids in one tape re-created,
agent 281 nineteen times -- so "agent 38's definition" is not a fact, it is a fact
about an interval. MEASURED consequence, and it is live in the corpus today:

    20260807T143055  connection :62994  agent 38  t=18.169  PROP_HEALTH_MAX = 8
        interval join    -> definition slot 1434, class `mon1`     <- correct
        last-create-wins -> definition slot 1343, class `anim`     <- wrong

Agent 38 is re-created as an `anim` at t=74.779, 56 seconds after the reading. That is
**one of the five NPC health observations in existence**, so the naive join corrupts
20% of the strongest evidence this project has about a server-only stat -- while being
green on 99.8% of creates and looking perfectly reasonable in review. The error has
been made three times in this repo's history by three different readers, which is why
`test_npcdefs.py` asserts BOTH answers: the interval join must give 1434 and the naive
join must give 1343, so the day they agree the control announces itself instead of
passing.

WHAT IT REFUSES TO EMIT, each for a measured reason rather than caution:

  * `armor` and `energy` -- no property id for either appears in any channel across
    22,524 messages. A column that is always absent reads as "not done yet" and invites
    a session that cannot succeed.
  * `name` -- a name comes from a rendered nameplate or it does not exist. See the
    `lakeside_worm` row in `content/npcs.toml`, which says this about itself.
  * `allegiance` -- hostility is a fact about a SPAWN, not about a type. Slot 1480 is
    created 49 times `nonc` and 9 times `play` from a byte-identical declaration.
  * create field 10 -- it takes two values inside slots 1420, 1421 and 1343, so it is
    per-instance. Field 9 (`move_speed`) is single-valued per slot at n = 7..202.

REFORGED MODE rides on every stat row as `mode`. It scales enemy health and armour
~20%, leaves no mark on the wire, and cannot be recovered afterwards, so a capture that
did not record it gets `"unrecorded"` -- which `content.py` accepts and will never
promote. `livesession.py --mode` has been required since 2026-08-11; captures older
than that are honestly unrecorded and stay that way.

    python toolkit/authsrv/npcdefs.py                 # census, writes nothing
    python toolkit/authsrv/npcdefs.py --emit          # -> vault/content/npcs.toml
"""
import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import origin  # noqa: E402
import tape  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# The message family. Named opcodes only -- an unnamed one has no business defining a
# content row, and `schema/overrides.json` is where a name gets earned.
CREATE_AGENT = 0x0020           # WORLD_CREATE_AGENT
NPC_PROPERTIES = 0x0056         # NPC_UPDATE_PROPERTIES -- the definition itself
MONSTER_COMPOSITE = 0x0057      # the model files for a definition
ATTACK_RATE = 0x0035            # attack interval + modifier, both dword-holding-float
GENERIC_VALUE = 0x009F          # [property_id, agent_id, value]
PROP_HEALTH_MAX = 42

# WORLD_CREATE_AGENT field[2] is a tagged model reference: the top nibble is a class
# tag (GmAgent.h) and the low bits are the definition index. 0x2 is the NPC family and
# 0x3 is the player family, so the mask is NOT unconditional -- applying it to a player
# create yields a meaningless "definition".
NPC_CLASS_TAG = 0x2
DEFINITION_MASK = 0xFFFF

# field[12] is a FourCC allegiance token carried little-endian: the dword 0x6D6F6E31
# spells `1nom` in wire order and reads `mon1` big-endian. Anyone grepping a capture
# for the literal bytes `mon1` finds zero, which is worth the two lines it costs here.
HOSTILE_TOKENS = ("mon1", "band")

# Fields Reforged Mode is known to move. Kept in step with content.MODE_SENSITIVE.
MODE_SENSITIVE = ("max_health",)


class NpcDefsError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


def _fourcc(dword):
    return dword.to_bytes(4, "big").decode("latin1")


def _f32(u32):
    """The float a dword-typed field is carrying.

    0x0035's two fields are `dword` in the client's own format tables and hold IEEE-754
    floats. The typing is CORRECT and reading them AS floats is the ROTATE_PLAYER trap
    from the other side: 1073741824 read as a float32 is 2.5e-39, not 2.0.
    """
    return struct.unpack("<f", struct.pack("<I", u32))[0]


class Intervals:
    """Which definition an agent id was, at a given moment.

    An agent id is a slot the server recycles, not an identity. Every lookup here is
    (agent, time) -> definition, and the module docstring records what happens when it
    is not.
    """

    def __init__(self):
        self._by_agent = collections.defaultdict(list)

    def add(self, agent, t, definition, token):
        self._by_agent[agent].append((t, definition, token))

    def at(self, agent, t):
        """The create in effect at `t`, or None if the agent had none by then."""
        found = None
        for t_create, definition, token in self._by_agent.get(agent, ()):
            if t_create <= t:
                found = (definition, token)
        return found

    def last(self, agent):
        """THE WRONG ANSWER, kept so the test can demand the two disagree.

        Exported deliberately: a sabotage a test has to reimplement is a sabotage that
        drifts away from the code it is meant to indict.
        """
        rec = self._by_agent.get(agent)
        return (rec[-1][1], rec[-1][2]) if rec else None

    def creates(self):
        for agent, recs in self._by_agent.items():
            for t, definition, token in recs:
                yield agent, t, definition, token


class Definition:
    """One NPC type, as the wire declared it."""

    def __init__(self, index):
        self.index = index
        self.payload = None          # the 0x0056 body, minus the definition index
        self.model_id = None
        self.move_speed = None
        self.attack = None           # (interval, modifier)
        self.health = []             # [(capture, value)]
        self.tokens = set()
        self.creates = 0
        self.captures = set()
        self.connections = set()

    # -- the declared half ---------------------------------------------------
    def declare(self, values, capture, connection):
        """0x0056: [definition, file_id, 0, scale, 0, flags, profession, level, name].

        A second declaration must be byte-identical. MEASURED: 126 declarations over 54
        definitions across three captures and twelve connections, with ZERO
        disagreements -- so a disagreement is a real event and must stop the run rather
        than pick a winner.
        """
        body = (values[2], values[3], values[4], values[5], values[6], values[7],
                values[8], tuple(ord(ch) for ch in values[9]))
        if self.payload is not None and self.payload != body:
            raise NpcDefsError(
                f"definition {self.index} is declared twice with different payloads:\n"
                f"  {self.payload}\n  {body}\n"
                f"126 of 126 declarations in the vault agree, so this is new. It is a "
                f"finding, not a merge conflict -- do not pick one.")
        self.payload = body
        self.captures.add(capture)
        self.connections.add(connection)

    @property
    def declared(self):
        return self.payload is not None

    def row(self):
        """The content row. Ids and numbers only -- no text, ever."""
        file_id, _f3, scale, _f5, flags, profession, level, enc = self.payload
        row = {"file_id": file_id, "definition": self.index, "scale": scale,
               "flags": flags, "profession": profession, "level": level,
               # A LIST OF IDS, never the decoded string. The wire type is string16 and
               # the codec hands back a str of code units -- several of which are lone
               # UTF-16 surrogates, which TOML cannot hold and a console cannot print.
               # `agents._encstring` packs the list back into that str on the way out.
               "enc_name": list(enc)}
        if self.model_id is not None:
            row["model_id"] = self.model_id
        if self.move_speed is not None:
            row["move_speed"] = self.move_speed
        if self.attack is not None:
            row["attack_interval"], row["attack_modifier"] = self.attack
        if self.health:
            row["max_health"] = self.health[0][1]
        return row

    @property
    def hostile(self):
        return bool(self.tokens & set(HOSTILE_TOKENS))


def read(capture_dirs, codec=None):
    """Decode captures into {definition index: Definition}, plus the per-connection map.

    Refuses to pool captures of different origin. `toolkit/origin.py` is three-valued
    and a consumer that mixes them is comparing ArenaNet's behaviour with our own
    server's -- not weaker evidence, DIFFERENT evidence.
    """
    codec = codec or Codec()
    defs = {}
    intervals = {}
    origins = set()
    for capture_dir in capture_dirs:
        for row in tape.channel_files(capture_dir):
            connection = row["connection"]
            info, events = tape.load_tape(capture_dir, connection)
            origins.add(info.get("origin", "unknown"))
            if len(origins) > 1:
                raise NpcDefsError(
                    f"refusing to pool captures of different origin: {sorted(origins)}. "
                    f"toolkit/origin.py is three-valued for this reason -- ours and live "
                    f"are two datasets and only one of them is an oracle.")
            capture = info.get("capture") or os.path.basename(capture_dir)
            msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            consumed, total, err = receipt
            if err is not None or consumed != total:
                raise NpcDefsError(
                    f"{capture} {connection} did not frame to its final byte "
                    f"({consumed}/{total}, {err}). A partial decode silently drops the "
                    f"tail of the session; every definition after the break would be "
                    f"missing and nothing would say so.")
            iv = Intervals()
            intervals[(capture, connection)] = iv

            # Pass 1: declarations and creates. Both must be complete before any
            # property message is resolved, because a property can precede the create
            # it belongs to in wire order only by arriving in the same flush -- and a
            # half-built interval map would silently answer None for those.
            for t, opcode, values in msgs:
                if opcode == NPC_PROPERTIES:
                    d = defs.setdefault(values[1], Definition(values[1]))
                    d.declare(values, capture, connection)
                elif opcode == MONSTER_COMPOSITE:
                    d = defs.setdefault(values[1], Definition(values[1]))
                    models = values[2] if isinstance(values[2], list) else [values[2]]
                    if models:
                        d.model_id = models[0]
                elif opcode == CREATE_AGENT:
                    tagged = values[2]
                    if (tagged >> 28) != NPC_CLASS_TAG:
                        continue          # a player create; the mask would invent a slot
                    index = tagged & DEFINITION_MASK
                    token = _fourcc(values[12])
                    iv.add(values[1], t, index, token)
                    d = defs.setdefault(index, Definition(index))
                    d.tokens.add(token)
                    d.creates += 1
                    # field 9 is the type's speed; field 10 is per-instance. MEASURED:
                    # field 9 is single-valued for every definition at n = 7..202, and
                    # 1442's 12.0 in 202 of 202 reproduces the hand-written speed in
                    # content/npcs.toml from the other direction.
                    speed = round(float(values[9]), 4)
                    if d.move_speed is None:
                        d.move_speed = speed
                    elif d.move_speed != speed:
                        raise NpcDefsError(
                            f"definition {index} has two move speeds "
                            f"({d.move_speed}, {speed}). Field 9 is single-valued per "
                            f"definition in every capture measured; if that has "
                            f"changed it is a finding about the field, not a value to "
                            f"average.")

            # Pass 2: properties, resolved through the interval map.
            for t, opcode, values in msgs:
                if opcode == ATTACK_RATE:
                    hit = iv.at(values[1], t)
                    if hit:
                        defs[hit[0]].attack = (round(_f32(values[2]), 4),
                                               round(_f32(values[3]), 4))
                elif opcode == GENERIC_VALUE and values[1] == PROP_HEALTH_MAX:
                    hit = iv.at(values[2], t)
                    if hit:
                        defs[hit[0]].health.append((capture, values[3]))
    return defs, intervals


def hostile(defs):
    return {i: d for i, d in defs.items() if d.hostile and d.declared}


# ---------------------------------------------------------------- emit

def _toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_toml(defs, mode="unrecorded"):
    """The rows, as a `content/*.toml` fragment with provenance per row.

    Every row is `source = "capture"`, which `content.py` requires to carry `capture`
    and `origin` -- and `mode` too, for any row holding a stat Reforged Mode moves.
    """
    out = ["# GENERATED by toolkit/authsrv/npcdefs.py -- do not hand-edit.",
           "#",
           "# Definition rows compiled from live captures. Ids and numbers only: no",
           "# ArenaNet text is written here, and `enc_name` is a list of string IDS that",
           "# the client resolves against its own table at run time.",
           "#",
           "# NOT emitted, each for a measured reason -- see the module docstring:",
           "#   armor, energy  no property id in any channel over 22,524 messages",
           "#   name           a name comes from a rendered nameplate or it does not exist",
           "#   allegiance     hostility is a property of a spawn, not of a type",
           ""]
    for index in sorted(defs):
        d = defs[index]
        row = d.row()
        key = f"def_{index}"
        out.append(f"[npc.{key}]")
        for field in ("definition", "file_id", "model_id", "scale", "flags",
                      "profession", "level", "move_speed", "attack_interval",
                      "attack_modifier", "max_health", "enc_name"):
            if field in row:
                out.append(f"{field} = {_toml_value(row[field])}")
        out.append(f"[npc.{key}.provenance]")
        out.append('source = "capture"')
        out.append(f"capture = {_toml_value(sorted(d.captures)[0])}")
        out.append('origin = "live"')
        if any(f in row for f in MODE_SENSITIVE):
            out.append(f"mode = {_toml_value(mode)}")
        out.append('extractor = "toolkit/authsrv/npcdefs.py"')
        out.append(f'verified = """OBSERVED on ArenaNet\'s own wire. Definition {index} '
                   f'declared by GAME_SMSG 0x0056 in {len(d.connections)} connection(s) '
                   f'across {len(d.captures)} capture(s), payloads byte-identical; '
                   f'{d.creates} create(s) carried it. Every field is read from the '
                   f'declaration or joined to the create in effect at the message\'s '
                   f'own timestamp, never to the agent\'s last create."""')
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- cli

def live_captures():
    """Every live capture directory that has a decrypted game channel in it.

    Six live directories exist and only three carry decrypted game channels; the other
    three lost their keys to a memory-only keyring (fixed 2026-08-07, commit 17b34cc).
    Selecting by CONTENT rather than by name is the same rule test_codec.py's fixture
    picker learned the hard way -- a directory that looks like a capture and holds no
    channel would otherwise contribute silently nothing.
    """
    root = vaultpath.require_dir("captures", "live",
                                 why="npcdefs compiles definitions out of live captures")
    out = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if any(f.startswith("game-") and f.endswith(".jsonl") for f in os.listdir(path)):
            out.append(path)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true",
                    help="write vault/content/npcs.toml (gitignored; content.py merges "
                         "it over the tracked rows)")
    ap.add_argument("--hostile-only", action="store_true",
                    help="emit only definitions seen under a hostile allegiance token")
    ap.add_argument("--mode", default="unrecorded",
                    choices=("base", "reforged", "unrecorded"),
                    help="the game mode the captures were taken in. Defaults to "
                         "unrecorded, which is the honest value for every capture "
                         "predating livesession.py --mode")
    a = ap.parse_args()

    caps = live_captures()
    defs, _intervals = read(caps)
    declared = {i: d for i, d in defs.items() if d.declared}
    host = hostile(defs)
    print(f"{len(caps)} capture(s), {len(declared)} definition(s) declared, "
          f"{len(host)} hostile")
    print(f"  with a model id     : {sum(1 for d in declared.values() if d.model_id)}")
    print(f"  with an attack rate : {sum(1 for d in declared.values() if d.attack)}")
    print(f"  with a health value : {sum(1 for d in declared.values() if d.health)}")
    for index in sorted(host):
        d = host[index]
        r = d.row()
        print(f"  {index:>5}  file {r['file_id']:>7}  lvl {r['level']:>2}  "
              f"prof {r['profession']}  speed {r.get('move_speed')}  "
              f"hp {r.get('max_health', '-')}  atk {d.attack or '-'}  "
              f"{d.creates} create(s)  {','.join(sorted(d.tokens))}")

    if not a.emit:
        print("\n(census only -- pass --emit to write vault/content/npcs.toml)")
        return 0
    chosen = host if a.hostile_only else declared
    outdir = vaultpath.vault_path("content")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "npcs.toml")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_toml(chosen, mode=a.mode))
    print(f"\nwrote {len(chosen)} row(s) -> {path}")
    if a.mode == "unrecorded":
        print("  stats carry mode='unrecorded': Reforged Mode scales health ~20% and "
              "these captures predate livesession.py --mode. content.py will load them "
              "and will never promote them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
