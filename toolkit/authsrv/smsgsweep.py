r"""Send the opcodes ArenaNet never showed us to a real client, and read what happens.

A third of the GAME_SMSG catalogue has a field layout and no behaviour: 324 of the
client's 477 receive-table entries have never been observed from ArenaNet
(`studies/reconstruction/FINDINGS.md` §4.11, and `msghandler.py --classify` for the
denominator, which is 324 rather than the 332 that paper first quoted). This is the
loopback half of closing that: our own server sends each one to a client we control, on
127.0.0.1, and the client's own reaction is the measurement.

    python toolkit/authsrv/smsgsweep.py --plan            # write the plan, send nothing
    python toolkit/authsrv/smsgsweep.py --analyse <cap>   # score a run

    # the run itself, once a client is up against our server:
    python toolkit/authsrv/authsrv.py --probe smsgsweep

**No live service is involved at any point.** Both endpoints are ours, the client is an
ours-DH build under `vault/run/`, and `cage.assert_launch_safe(exe, "127.0.0.1")` is the
gate. Nothing here may be pointed at ArenaNet and nothing here needs to be.

THE PREDICTION IS STATED BEFORE THE RUN, and it is computed rather than guessed --
`msghandler.py --classify` partitions every handler by shape, and this module carries
that partition into the plan so each row is scored against what the binary predicted.
Three things that partition already settled, each of which had been assumed otherwise:

  * **There is no inert bucket.** All 477 entries carry a non-null dispatch pointer, so
    silence is never explained by "nothing to reach" -- it is a fact about the readout
    or about the client's state.
  * **Absent from the table does not mean inert.** `0x000C`/`0x000D` are catalogued with
    no receive entry and are unmistakably acted on -- they are the latency round trip.
    They are handled below the message table.
  * **The values must come from `codec.fields_for()`, never from `messages.json`.**
    `overrides.json` changes the field list of exactly three opcodes (140, 146, 421), so
    a builder reading the base catalogue produces the wrong arity for those three and
    only those three -- measured, 484 of 487 instead of 487 of 487.

THE READOUT, and why it needs nothing new. The capture the server already writes holds
both directions with timestamps, so a run is scored by joining it to itself: find our
sweep send in the s2c stream, then attribute the client's c2s messages that follow it.
Attribution is by IDENTITY rather than by timing, which is what makes it sound -- a
parked loopback client's idle traffic is only `0x0008` and `0x0009`, so anything else
arriving after a stimulus is a reply to it.

WHAT COUNTS AS AN EFFECT, in decreasing order of how much it tells you:

    REPLIED    the client sent a c2s message that is not the idle floor. The strongest
               result: it names the request an opcode's panel makes, which is the
               binding a live session would otherwise have to discover.
    DIED       the connection dropped, or the client asserted. Also a result -- the
               assert names a source file and a bound, which is a spec fragment.
    SILENT     nothing. NOT "no handler": see above. Worth least, and it is most of
               them.

DEGENERATE VALUES ARE THE POINT AND THE LIMIT. Every field goes out zeroed, so this
measures what an opcode does with an EMPTY payload, and a handler that early-outs on a
zero id is indistinguishable here from one that does nothing at all. That is a real
ceiling on what a silent row means and it is stated rather than discovered later.
"""
import argparse
import binascii
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# A parked loopback client sends only these. MEASURED over 47 idle sessions and 2,822 s:
# 0x0009 at 0.082/s and 0x0008 at 0.013/s, and nothing else. That is what makes
# attribution by identity sound -- any other opcode arriving after a stimulus is a reply
# to it, and no timing argument is needed.
IDLE_FLOOR = {0x0008, 0x0009}

PLAN_NAME = "smsgsweep-plan.json"


def degenerate(codec, opcode, channel="GAME_SMSG"):
    """A zeroed value for every field the codec says this opcode has.

    Read the field list from the CODEC, never from `schema/messages.json`: overrides
    change three field lists and a builder reading the base catalogue gets the arity
    wrong for exactly those three. Measured before this docstring was written.
    """
    vals = []
    for f in codec.fields_for(channel, opcode):
        t, length = f["type"], f["length"]
        if t == "msg_header":
            continue
        if t in ("byte", "word", "dword", "agent_id"):
            vals.append(0)
        elif t == "float":
            vals.append(0.0)
        elif t == "vec2":
            vals.append((0.0, 0.0))
        elif t == "vec3":
            vals.append((0.0, 0.0, 0.0))
        elif t == "blob":
            vals.append(b"\x00" * length)
        elif t == "string16":
            vals.append("")
        elif t in ("array8", "array16", "array32"):
            vals.append([])
        elif t == "nested_struct":
            # A nested_struct swallows the whole tail as its element layout, so the
            # caller supplies one value for it and none for the fields after it.
            vals.append([])
            break
        else:
            raise ValueError(f"0x{opcode:04X} has field type {t!r}, which this builder "
                             f"does not know how to zero. Refusing to guess a value.")
    return vals


def encodable(codec, channel="GAME_SMSG"):
    """{opcode: values} for every opcode that encodes. Refusals are returned, not hidden."""
    good, refused = {}, {}
    for key in codec.channels[channel]["messages"]:
        opcode = int(key)
        try:
            vals = degenerate(codec, opcode, channel)
            codec.encode(channel, opcode, list(vals))
        except Exception as exc:                      # a refusal is a result
            refused[opcode] = f"{type(exc).__name__}: {exc}"
            continue
        good[opcode] = vals
    return good, refused


def plan(codec, seen, classified=None):
    """The ordered send list: never-seen opcodes first, each with its prediction.

    `seen` is the set observed from ArenaNet -- those are excluded, because the point is
    the third of the catalogue nothing has ever watched. `classified` is
    `msghandler.classify()`'s output if the disassembler is available; without it the
    plan still runs and simply carries no prediction to score against, which is a
    weaker experiment and says so in the file.
    """
    good, refused = encodable(codec)
    rows = []
    for opcode in sorted(good):
        if opcode in seen:
            continue
        c = (classified or {}).get(opcode) or {}
        rows.append({"opcode": opcode,
                     "predicted": c.get("class", "UNKNOWN"),
                     "callee": c.get("callees", [None])[0] if c.get("callees") else None,
                     "bytes": len(codec.encode("GAME_SMSG", opcode, list(good[opcode])))})
    return {"rows": rows,
            "refused": {f"0x{k:04X}": v for k, v in refused.items()},
            "idle_floor": sorted(IDLE_FLOOR),
            "note": "degenerate (all-zero) payloads; a handler that early-outs on a "
                    "zero id is indistinguishable here from one that does nothing"}


def plan_path():
    return os.path.join(vaultpath.vault_path("probes"), PLAN_NAME)


def load_plan():
    path = plan_path()
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- analysis

def analyse(capture_jsonl, codec=None):
    """Score a run from the server's own capture: sent opcode -> what came back.

    Joins the capture to itself. Our sweep sends are in the s2c stream and the client's
    replies are in the c2s stream, both stamped, so every c2s message is attributed to
    the most recent sweep send before it -- and then filtered by IDENTITY against the
    idle floor, which is what keeps the attribution honest at a 0.4 s dwell.
    """
    codec = codec or Codec()
    sends, replies, died = [], [], None
    with open(capture_jsonl, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            kind = rec.get("kind")
            # OUR sends are `sent` events, NOT s2c `frame` events -- the recorder logs
            # the two directions differently and only the receive path writes frames.
            # Reading s2c frames finds zero stimuli and reports a clean, wrong "nothing
            # happened", which is what the first version of this function did.
            if kind == "sent" and "PROBE[smsgsweep]" in (rec.get("label") or ""):
                sends.append((float(rec.get("t", 0.0)), int(rec.get("opcode", 0))))
            elif kind == "decoded":
                replies.append((float(rec.get("t", 0.0)), int(rec.get("opcode", 0))))
            elif kind == "error" and died is None:
                died = (float(rec.get("t", 0.0)), str(rec.get("error", ""))[:120])

    out = {}
    for i, (t, opcode) in enumerate(sends):
        end = sends[i + 1][0] if i + 1 < len(sends) else float("inf")
        got = [op for rt, op in replies if t <= rt < end and op not in IDLE_FLOOR]
        row = out.setdefault(opcode, {"sent": 0, "replies": []})
        row["sent"] += 1
        row["replies"].extend(got)
    for opcode, row in out.items():
        row["effect"] = "REPLIED" if row["replies"] else "SILENT"
    # The connection dying IS a result, and it belongs to the LAST opcode sent before
    # it -- attributing it to nothing at all is how a crash gets read as a clean run.
    if died and sends:
        last = max(sends, key=lambda s: s[0])
        out[last[1]]["effect"] = "DIED"
        out[last[1]]["died"] = died
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true", help="write the plan and exit")
    ap.add_argument("--analyse", metavar="CAPTURE_JSONL", default=None,
                    help="score a completed run from the server's capture")
    ap.add_argument("--seen", default=None, metavar="FILE",
                    help="opcodes observed from ArenaNet, one per line")
    ap.add_argument("--limit", type=int, default=0,
                    help="pilot: keep only the first N rows of the plan")
    a = ap.parse_args()
    codec = Codec()

    if a.analyse:
        table = analyse(a.analyse, codec)
        replied = {k: v for k, v in table.items() if v["effect"] == "REPLIED"}
        dead = {k: v for k, v in table.items() if v["effect"] == "DIED"}
        print(f"{len(table)} opcode(s) stimulated, {len(replied)} produced a reply, "
              f"{len(dead)} ended the connection")
        for opcode in sorted(replied):
            got = " ".join(f"0x{o:04X}" for o in sorted(set(replied[opcode]["replies"])))
            print(f"  REPLIED  0x{opcode:04X} -> {got}")
        for opcode in sorted(dead):
            print(f"  DIED     0x{opcode:04X} -> {dead[opcode]['died'][1]}")
        if not replied:
            print("  (no replies. With all-zero payloads that is the expected common "
                  "case, and it is NOT evidence of a missing handler -- every entry in "
                  "the receive table dispatches.)")
        return 0

    seen = set()
    if a.seen:
        for line in open(a.seen, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                seen.add(int(line, 0))
    classified = None
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
        import msghandler
        classified = msghandler.classify(msghandler.Image())
    except (ImportError, SystemExit, OSError) as exc:
        print(f"(no static prediction: {type(exc).__name__}: {exc})")

    p = plan(codec, seen, classified)
    if a.limit:
        p["rows"] = p["rows"][:a.limit]
        p["note"] += f"  PILOT: first {a.limit} rows only."
    os.makedirs(os.path.dirname(plan_path()), exist_ok=True)
    with open(plan_path(), "w", encoding="utf-8") as fh:
        json.dump(p, fh, indent=1)
    kinds = {}
    for r in p["rows"]:
        kinds[r["predicted"]] = kinds.get(r["predicted"], 0) + 1
    print(f"{len(p['rows'])} opcode(s) planned -> {plan_path()}")
    print(f"  predicted: {kinds}")
    if p["refused"]:
        print(f"  {len(p['refused'])} refused to encode: {list(p['refused'])[:6]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
