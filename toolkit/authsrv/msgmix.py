"""What our server sends, against what ArenaNet's does, per named opcode.

    python toolkit/authsrv/msgmix.py

WHY THIS EXISTS. Until 2026-08-10 this comparison could not be READ: one
GAME_SMSG opcode of 487 had a name, so a table of counts was a table of numbers.
With 21 named it becomes a ranked list of what our server does not do, measured
against ArenaNet's own traffic rather than against anyone's opinion.

WHAT IT IS NOT. Rates depend on what happened in the session. Ours comes from
scripted loopback runs whose clicks mostly land outside the server's 1-second
position-freshness window, so AGENT_MOVE_TO_POINT reads 0 -- that is a true
statement about those runs, not a claim that the server can never issue a move.
Read a 0 as "did not happen here", and go and look at why before believing it
means "cannot".

Both sides are real captures: ours from vault/captures/gamesrv (an in-world
loopback session), theirs from the two live tapes. 21 GAME_SMSG opcodes now have
names, so for the first time this comparison can be read rather than decoded.

Rates are per 100 seconds of in-world time, because the sessions differ in
length by an order of magnitude and raw counts would say nothing.
"""
import collections
import json
import os
import sys

ROOT = r"C:\gd\Rurik"
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))
os.chdir(ROOT)
import tape
import codec

C = codec.Codec(overrides="schema/overrides.json")
OV = json.load(open("schema/overrides.json", encoding="utf-8"))["channels"]["GAME_SMSG"]


def name(op):
    r = OV.get(str(op))
    return r["name"] if r and "name" in r else ""


# ---- ArenaNet ------------------------------------------------------------
theirs, their_secs = collections.Counter(), 0.0
for stamp in ("20260807T143055", "20260810T235916"):
    cap = tape.resolve_capture(stamp)
    for conn in tape.chain(cap):
        meta, events = tape.load_tape(cap, conn)
        their_secs += meta["seconds"]
        carry = b""
        for _t, blob in events:
            buf = carry + blob
            msgs, used, _r = C.decode_stream("GAME_SMSG", buf)
            carry = buf[used:]
            theirs.update(op for op, _v in msgs)

# ---- ours ----------------------------------------------------------------
# The gamesrv capture logs one record per message with its opcode already
# decoded, so this reads the log rather than re-framing a stream.
ours, our_secs = collections.Counter(), 0.0
files = sorted(
    (os.path.join("vault", "captures", "gamesrv", f)
     for f in os.listdir(os.path.join("vault", "captures", "gamesrv"))
     if f.endswith(".jsonl")),
    key=os.path.getmtime)[-6:]
used_files = []
for path in files:
    n_before = sum(ours.values())
    lo = hi = None
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        # 'sent' IS the s2c side: the server logs one record per message it
        # sends, with the opcode already decoded. Fields are strings.
        if r.get("kind") != "sent":
            continue
        try:
            op = int(r["opcode"])
            t = float(r["t"])
        except (KeyError, TypeError, ValueError):
            continue
        ours[op] += 1
        lo = t if lo is None else min(lo, t)
        hi = t if hi is None else max(hi, t)
    if sum(ours.values()) > n_before:
        used_files.append(os.path.basename(path))
        if lo is not None and hi is not None:
            our_secs += max(hi - lo, 0.0)

print(f"ArenaNet: {sum(theirs.values())} s2c msgs over {their_secs:.0f}s "
      f"({len(theirs)} opcodes)")
print(f"ours    : {sum(ours.values())} s2c msgs over {our_secs:.0f}s "
      f"({len(ours)} opcodes) from {len(used_files)} capture(s)")
if not ours:
    print("\nNO s2c RECORDS FOUND -- the field names below are what was looked for.")
    p = files[-1]
    for line in list(open(p, encoding="utf-8"))[:3]:
        print("  sample record keys:", sorted(json.loads(line)))
    sys.exit(1)

tr = 100.0 / their_secs if their_secs else 0.0
orr = 100.0 / our_secs if our_secs else 0.0
rows = []
for op in set(theirs) | set(ours):
    rows.append((theirs[op] * tr, ours[op] * orr, op, theirs[op], ours[op]))
rows.sort(key=lambda r: -r[0])

print(f"\n{'opcode':8} {'name':30} {'ArenaNet/100s':>14} {'ours/100s':>10}  gap")
print("-" * 78)
for their_rate, our_rate, op, tn, on_ in rows[:26]:
    if their_rate < 1 and our_rate < 1:
        continue
    if our_rate == 0 and their_rate > 0:
        gap = "NEVER SENT"
    elif their_rate == 0:
        gap = "ours only"
    else:
        gap = f"{our_rate / their_rate:5.2f}x"
    print(f"0x{op:04X}   {name(op)[:30]:30} {their_rate:14.1f} {our_rate:10.1f}  {gap}")

never = [(r[0], r[2]) for r in rows if r[1] == 0 and r[0] >= 1.0]
print(f"\nnamed opcodes ArenaNet sends at >=1/100s that we NEVER send: "
      f"{sum(1 for r, op in never if name(op))}")
for rate, op in never:
    if name(op):
        print(f"  0x{op:04X}  {name(op):32} {rate:7.1f}/100s")
