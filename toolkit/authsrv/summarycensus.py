"""summarycensus: every character summary in the vault, decoded, ours and live apart.

    python toolkit/authsrv/summarycensus.py            # both origins, separately
    python toolkit/authsrv/summarycensus.py --live     # retail's only
    python toolkit/authsrv/summarycensus.py --ours     # our loopback server's only

WHY. `charsummary.py` is a byte map read out of the client's packer, and a
byte map read out of a disassembly is a claim until real records fit it. This
walks every summary the vault holds -- the ones our server SERVED
(`CHARACTER_INFO`), the ones the client SENT back
(`UPDATE_CHARACTER_SETTINGS`), and the same two directions in the owner's
live captures -- and prints per-field distributions. What it looks for, and
what it found on 2026-09-16 (studies/heroes/RUN-HEROLIB.md §22):

  * zero malformed across 6 + 525 ours and 161 + 23 live;
  * the level field reads 20 exactly where the owner's characters are 20;
  * every last_outpost value is an outpost;
  * the tag reads as four ASCII characters or a decimal map id;
  * the unwritten positions carry 0xDD allocator fill in 92 of retail's 161
    served blobs and nothing else does.

ORIGINS ARE NEVER POOLED. Ours and live are censused and printed separately;
a blob's origin is the capture's `origin` record, and a capture without one
is skipped by name.

Reads the vault; prints numbers; never prints a live blob's bytes.
"""

import collections
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import charsummary as cs  # noqa: E402
import vaultpath  # noqa: E402


def find_summaries(plain_hex):
    """Every blob inside a plain frame with the summary's own shape: a u16
    length, a version word of 8, and 0x25 + 5 * count == length."""
    b = bytes.fromhex(plain_hex)
    out = []
    for L in range(cs.HEADER, cs.length_for(cs.MAX_ITEMS) + 1, cs.ITEM):
        for i in range(0, len(b) - L - 1):
            if struct.unpack_from("<H", b, i)[0] != L:
                continue
            blob = b[i + 2:i + 2 + L]
            if struct.unpack_from("<H", blob, 0)[0] != cs.VERSION:
                continue
            if cs.length_for(blob[32]) != L:
                continue
            out.append(blob)
    return out


def _events(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _origin(path):
    for e in _events(path):
        if e.get("kind") == "origin":
            return e.get("origin")
        break
    return None


def ours():
    """(served, sent, malformed, files) from our authsrv captures. Served
    summaries are those with the version-8 shape; the version-6 literal the
    server used to serve is counted separately."""
    served, sent, malformed = [], [], []
    v6 = 0
    files = 0
    pairs = []
    for f in sorted(glob.glob(str(vaultpath.vault_path("captures", "authsrv",
                                                       "*.jsonl")))):
        if _origin(f) != "ours":
            continue
        files += 1
        sv, st = [], []
        for e in _events(f):
            if e.get("kind") == "sent" and e.get("opcode") == 7:
                hits = find_summaries(e["plain"])
                if hits:
                    sv += hits
                elif "0600" in e["plain"][-80:]:
                    v6 += 1
            elif e.get("kind") == "character_settings":
                st.append(bytes.fromhex(e["blob"]))
        for blob in sv + st:
            try:
                cs.decode(blob)
            except cs.Malformed as ex:
                malformed.append((os.path.basename(f), str(ex)))
        served += sv
        sent += st
        if sv and st:
            pairs.append((os.path.basename(f), sv[0], st))
    return served, sent, malformed, files, v6, pairs


def live():
    served, sent, malformed = [], [], []
    files = 0
    for f in sorted(glob.glob(str(vaultpath.vault_path("captures", "live", "*",
                                                       "auth-*.jsonl")))):
        if _origin(f) != "live":
            continue
        files += 1
        for e in _events(f):
            if e.get("kind") != "frame":
                continue
            hits = find_summaries(e["plain"])
            if not hits:
                continue
            (served if e.get("direction") == "s2c" else sent).extend(hits)
    for blob in served + sent:
        try:
            cs.decode(blob)
        except cs.Malformed as ex:
            malformed.append(str(ex))
    return served, sent, malformed, files


def _dist(name, values, fmt=str, limit=12):
    c = collections.Counter(values)
    if len(c) > limit:
        top = c.most_common(limit)
        rest = len(c) - limit
        body = ", ".join(f"{fmt(k)}: {v}" for k, v in top)
        print(f"    {name}: {body}, ... {rest} more distinct")
    else:
        body = ", ".join(f"{fmt(k)}: {v}" for k, v in sorted(c.items(),
                                                            key=lambda kv: -kv[1]))
        print(f"    {name}: {body}")


def census(title, blobs):
    dec = []
    for b in blobs:
        try:
            dec.append(cs.decode(b))
        except cs.Malformed:
            pass
    print(f"  {title}: {len(dec)} decoded of {len(blobs)}")
    if not dec:
        return
    _dist("length", [d["length"] for d in dec])
    _dist("count", [d["count"] for d in dec])
    _dist("level", [d["level"] for d in dec])
    _dist("profession nibble", [d["profession"] for d in dec])
    _dist("last_outpost", [d["last_outpost"] for d in dec])
    _dist("tag", [d["tag_text"] or f"{d['tag']:#x}" for d in dec], repr)
    _dist("campaign", [d["campaign"] for d in dec])
    _dist("is_pvp", [d["is_pvp"] for d in dec])
    _dist("secondary", [d["secondary"] for d in dec])
    _dist("helm_shown", [d["helm_shown"] for d in dec])
    _dist("pflag0/1/2", [f"{d['pflag0']}{d['pflag1']}{d['pflag2']}" for d in dec])
    _dist("guild_hall_id zero", [d["guild_hall_id"] == bytes(16) for d in dec])
    _dist("bytes 33-36", [d["unwritten"].hex() for d in dec], limit=6)
    _dist("flag bits 18-31", [d["flags_unwritten"] for d in dec], hex, limit=6)
    _dist("surplus", [d["surplus"] for d in dec])
    _dist("(level, campaign, is_pvp)",
          [(d["level"], d["campaign"], d["is_pvp"]) for d in dec])


def main(argv):
    want_ours = "--live" not in argv
    want_live = "--ours" not in argv
    if want_ours:
        served, sent, malformed, files, v6, pairs = ours()
        print(f"OURS: {files} captures with origin ours; {len(served)} served "
              f"version-8 summaries, {v6} served version-6 literals, "
              f"{len(sent)} client-sent, {len(malformed)} malformed")
        for m in malformed[:5]:
            print("    malformed:", m)
        census("served (version 8)", served)
        census("client-sent", sent)
        print(f"  {len(pairs)} capture(s) hold both a served summary and a "
              f"client-sent one:")
        for name, sv, sts in pairs:
            for st in sts:
                print(f"    {name}: differing {cs.differing(sv, st)}, "
                      f"compared {cs.compared_differing(sv, st)}")
    if want_live:
        served, sent, malformed, files = live()
        print(f"\nLIVE: {files} auth captures with origin live; {len(served)} "
              f"served, {len(sent)} client-sent, {len(malformed)} malformed")
        census("served", served)
        census("client-sent", sent)


if __name__ == "__main__":
    main(sys.argv[1:])
