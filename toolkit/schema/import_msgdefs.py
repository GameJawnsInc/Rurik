"""Import OpenTyria's message field tables into a schema Rurik owns.

HANDOFF.md §5 says to keep the packet catalog in one machine-readable place and
codegen from it, because hand-maintaining parallel copies of 400+ definitions is
how the project dies of paper cuts. The catalog already exists: OpenTyria's
`code/msgdefs.c` declares 777 messages over a 15-type field vocabulary, and
OpenTyria is released under the Unlicense — public domain, no attribution burden,
no copyleft. So this is an import, not a rewrite.

It is deliberately NOT authoritative. Four public corpora disagree about this
protocol, and the arbiter is the client's own deserializer table (PLAN.md §1.2),
which we have not dumped yet. Two independent signals already show why that
matters:

  * `AUTH_SMSG_0001` declares header + 2 dwords, while the C struct next to it has
    3 fields. The format table is what packs the wire, so the struct's third field
    is never sent.
  * `MOVE_TO_COORD` is documented as having drifted 0x003C -> 0x003E between
    client builds.

Hence every emitted schema carries `authority: imported` and the source commit.
When the client's table is dumped, that becomes the authority and this becomes a
naming layer — the disagreements are then mechanically detectable rather than a
matter of judgement, which is what makes reconciliation safe to delegate.
"""

import argparse
import json
import os
import re
import subprocess

FIELD_TYPES = {
    1: "msg_header", 2: "agent_id", 3: "float", 4: "vec2", 5: "vec3",
    6: "byte", 7: "word", 8: "dword", 9: "blob", 10: "string16",
    11: "array8", 12: "array16", 13: "array32", 14: "nested_struct",
}

# Wire size of each fixed-width type. Variable-length types are marked None:
# their size depends on a count read from the stream, so a schema that pretends
# otherwise would produce confidently wrong framing.
FIXED_SIZE = {
    "msg_header": 2, "word": 2, "byte": 1, "dword": 4, "float": 4,
    "agent_id": 4, "vec2": 8, "vec3": 12,
    "blob": None, "string16": None, "array8": None, "array16": None,
    "array32": None, "nested_struct": None,
}

TABLE_RE = re.compile(
    r"MsgField\s+([A-Z0-9_]+)\s*\[\s*(\d+)\s*\]\s*=\s*\{(.*?)\}\s*;", re.S)
ENTRY_RE = re.compile(r"\{\s*TYPE_([A-Z0-9_]+)\s*,\s*(\d+)\s*\}")
FORMAT_RE = re.compile(
    r"MsgFormat\s+([A-Z0-9_]+)_FORMATS\s*\[\s*(\d+)\s*\]\s*=\s*\{(.*?)\n\};", re.S)
FMT_ENTRY_RE = re.compile(
    r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*([A-Z0-9_]+)\s*,\s*(\d+)\s*\}")

TYPE_BY_NAME = {v.upper().replace("VEC2", "VECT2").replace("VEC3", "VECT3"): k
                for k, v in FIELD_TYPES.items()}
# The C names do not all match our snake_case; map explicitly rather than guess.
C_NAME_TO_TYPE = {
    "MSG_HEADER": "msg_header", "AGENT_ID": "agent_id", "FLOAT": "float",
    "VECT2": "vec2", "VECT3": "vec3", "BYTE": "byte", "WORD": "word",
    "DWORD": "dword", "BLOB": "blob", "STRING_16": "string16",
    "ARRAY_8": "array8", "ARRAY_16": "array16", "ARRAY_32": "array32",
    "NESTED_STRUCT": "nested_struct",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=r"C:\gd\Rurik\vault\mirrors\ldufr__OpenTyria")
    ap.add_argument("--out", default=r"C:\gd\Rurik\schema\messages.json")
    a = ap.parse_args()

    path = os.path.join(a.src, "code", "msgdefs.c")
    text = open(path, encoding="utf-8", errors="replace").read()

    try:
        commit = subprocess.run(["git", "-C", a.src, "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"

    tables = {}
    for name, count, body in TABLE_RE.findall(text):
        fields = []
        for tname, length in ENTRY_RE.findall(body):
            ftype = C_NAME_TO_TYPE.get(tname)
            if ftype is None:
                raise SystemExit(f"unknown field type TYPE_{tname} in {name}")
            fields.append({"type": ftype, "length": int(length)})
        if len(fields) != int(count):
            print(f"  warn: {name} declares {count} fields, parsed {len(fields)}")
        tables[name] = fields

    schema = {
        "provenance": {
            "imported_from": "ldufr/OpenTyria code/msgdefs.c",
            "license": "Unlicense (public domain)",
            "source_commit": commit,
            "authority": "imported",
            "note": ("NOT authoritative. The arbiter is the client's own packet-template "
                     "table (PLAN.md §1.2), not yet dumped. Opcodes are known to drift "
                     "between client builds, so any use of this schema must be stamped "
                     "with the build it was validated against."),
            "validated_against_build": None,
        },
        "field_types": FIELD_TYPES,
        "channels": {},
    }

    total = 0
    for chan, count, body in FORMAT_RE.findall(text):
        msgs = {}
        for opcode, nfields, table, size in FMT_ENTRY_RE.findall(body):
            fields = tables.get(table)
            if fields is None:
                continue
            variable = any(FIXED_SIZE[f["type"]] is None for f in fields)
            msgs[str(int(opcode))] = {
                "opcode": int(opcode),
                "table": table,
                "declared_unpack_size": int(size),
                "variable_length": variable,
                "fields": fields,
            }
        schema["channels"][chan] = {"declared_count": int(count), "messages": msgs}
        total += len(msgs)
        print(f"  {chan:10s} {len(msgs):4d} messages (declared {count})")

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=1)
    print(f"\n{total} messages -> {a.out}")

    # A histogram is a cheap sanity check on the import: an obviously skewed or
    # empty distribution means the regex matched something other than intended.
    from collections import Counter
    hist = Counter(fl["type"] for c in schema["channels"].values()
                   for m in c["messages"].values() for fl in m["fields"])
    print("\nfield-type usage:")
    for t, n in hist.most_common():
        print(f"  {t:15s} {n}")


if __name__ == "__main__":
    main()
