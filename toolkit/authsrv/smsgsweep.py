r"""Send the opcodes ArenaNet never showed us to a real client, and read what happens.

A third of the GAME_SMSG catalogue has a field layout and no behaviour: 324 of the
client's 477 receive-table entries have never been observed from ArenaNet
(`studies/reconstruction/FINDINGS.md` §4.11, and `msghandler.py --classify` for the
denominator, which is 324 rather than the 332 that paper first quoted). This is the
loopback half of closing that: our own server sends each one to a client we control, on
127.0.0.1, and the client's own reaction is the measurement.

    python toolkit/authsrv/smsgsweep.py --plan --resume     # next batch; sends nothing
    python toolkit/authsrv/smsgsweep.py --from-report R.json --record   # score + record
    python toolkit/authsrv/smsgsweep.py --report           # what the sweep knows so far

    # the run itself, once the harness has a client up against our server:
    python toolkit/harness/session.py --game-args "--probe smsgsweep" --keep-open --hold 90

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

WHAT THE PILOT OF 2026-08-12 COST, because every one of its four defects printed a
confident number rather than an error, and three of them printed the WRONG one:

  1. **The readout could not see its own stimulus.** `analyse` read s2c `frame` events,
     but the recorder writes our sends as `sent` events and only the RECEIVE path writes
     frames. It found zero stimuli in a run that sent twelve and reported a clean
     "nothing happened".
  2. **The stimulus landed inside the client's own load traffic.** The first packet went
     out 3.66 s in, while the client was still sending `INSTANCE_LOAD_REQUEST_SPAWN_POINT`,
     `MISSION_MASK_REPORT` and `TARGET_SELECT`. A c2s `0x0000` arriving 5 ms after our
     first send was scored REPLIED. It may well be one; the run had no way to tell, and
     neither did the report. Hence `settle` and the CONTROL WINDOW below.
  3. **"DIED" was reported for a client that did not die.** The run recorded
     `ConnectionResetError` after `0x000B` and called it a crash. The session report's
     own endpoint table says the AUTH connection stayed ESTABLISHED for another 42 s, no
     assert reached `Gw.log`, and no fatal-error dialog was ever raised -- the final
     screenshot is a live client sitting on the Ascalon City loading screen at 0%,
     "Connecting". `0x000B` tore down the GAME CHANNEL and left the client running. That
     is a better-specified result than a crash, and the word for it is DROPPED_CHANNEL.
  4. **The ten table-less opcodes were in the plan.** `0x000B` is one of them, it was
     step 12 of 24, and it ended the run. They are now excluded by default and reachable
     only through `--table-less`, deliberately, because they are handled below the
     message table and behave nothing like the 324 this sweep is about.

THE READOUT, and why it needs nothing new. The capture the server already writes holds
both directions with timestamps, so a run is scored by joining it to itself: find our
sweep send in the s2c stream, then attribute the client's c2s messages that follow it.
Attribution is by IDENTITY rather than by timing, which is what makes it sound -- but
identity is only sound against a floor of what the client says WITHOUT being asked, and
that floor is now MEASURED IN THE RUN ITSELF rather than inherited from another session:

    CONTROL WINDOW   the `control` seconds immediately before the first send, after
                     `settle` seconds of doing nothing at all. Whatever arrives there
                     arrived unprompted, in this client, in this map, in this session.
                     Any "reply" on an opcode the control window also produced is
                     downgraded to CONTESTED and never counted as a binding.

A run with no control window can attribute nothing and says so with a non-zero exit.

WHAT COUNTS AS AN EFFECT, in decreasing order of how much it tells you:

    REPLIED    the client sent a c2s message that neither the idle floor nor this run's
               own control window accounts for. The strongest result: it names the
               request an opcode's panel makes, which is the binding a live session
               would otherwise have to discover.
    UNDECODABLE the client answered on an opcode our catalogue cannot frame. STRONGER
               than REPLIED as evidence that something happened, weaker as a binding,
               and it must never be confused with the connection dying -- the recorder
               writes those as two different record kinds and this module reads both.
    DROPPED_CHANNEL  the client closed the game channel. A result, not a crash: see
               defect 3 above. Check the session report's endpoint table before ever
               upgrading this word to "crashed".
    CONTESTED  a reply on an opcode this run's own control window also produced.
    SILENT     nothing. NOT "no handler": see above. Worth least, and it is most of them.
    UNREACHED  the plan named it and the capture has no send for it -- or the send came
               after the connection was already gone. NOT a measurement of the opcode,
               and it is kept out of the ledger so a resumed run tries it again.

DEGENERATE VALUES ARE THE POINT AND THE LIMIT. Every field goes out zeroed, so this
measures what an opcode does with an EMPTY payload, and a handler that early-outs on a
zero id is indistinguishable here from one that does nothing at all. That is a real
ceiling on what a silent row means and it is stated rather than discovered later.

RESUME IS THE CAPTURE, NOT A CURSOR. The sweep survives a dropped channel by keeping a
ledger of opcodes that have actually been MEASURED, rebuilt from captures rather than
written as the probe goes: a cursor advanced at send time records opcodes the client may
never have received. `--plan --resume` then skips what the ledger holds, so an operator
loops launch/score/replan until `--report` says nothing is left.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# A parked loopback client sends only these. MEASURED over 47 idle sessions and 2,822 s:
# 0x0009 at 0.082/s and 0x0008 at 0.013/s, and nothing else. This is the PRIOR, and it is
# no longer trusted alone -- every run measures its own floor in a control window, because
# the pilot's floor was measured on a parked client and the sweep's client is one that has
# just finished loading a map. See CONTROL WINDOW above.
IDLE_FLOOR = {0x0008, 0x0009}

# GAME_SMSG 0x00F1, which our own server sends to kill and to revive the player. Its
# presence in a sweep capture means the map was NOT QUIET -- see `combat` in `analyse`.
AGENT_LIFE = 0x00F1

# GAME_SMSG 0x0197 MANIFEST_DONE, whose phase-0 row names the map the client is loading.
MANIFEST_DONE = 0x0197
# The map every reading in the ledger was taken in: Ascalon City. MEASURED -- it is what
# authsrv serves a fresh login. A connection that loads anything else is a DIFFERENT
# WORLD and its rows cannot be pooled with these; see `record`.
BASELINE_MAP = 148

# The ten opcodes the schema catalogues with NO entry in the client's receive table,
# MEASURED on build 38797 (toolkit/clientscan/test_msghandler.py pins this same literal,
# and `_check_table_less` refuses if the disassembler disagrees). They are handled below
# the message table -- 0x000C/0x000D are the latency round trip, which the client acts on
# unmistakably -- so they are neither part of the 324 nor safe to walk into: 0x000B tore
# the game channel down in the pilot.
NOT_IN_RECV_TABLE = {0x000A, 0x000B, 0x000C, 0x000D, 0x000E, 0x004F, 0x0055, 0x007F,
                     0x014A, 0x01DA}

# Seconds of doing NOTHING after the probe starts, before the control window opens. The
# pilot fired its first packet 3.66 s in and landed inside the client's own load traffic;
# that load was still arriving at 3.44 s. 6 s is that with room, and it costs one dwell
# per run rather than one per opcode.
SETTLE = 6.0
# Seconds of measured quiet immediately before the first send. Everything the client says
# here is unprompted BY CONSTRUCTION, and that is the run's own floor.
CONTROL = 4.0
# Between sends. Only has to exceed the client's reaction time, not a person's -- the
# readout is the capture, not the screen.
DWELL = 0.4

PLAN_NAME = "smsgsweep-plan.json"
LEDGER_NAME = "smsgsweep-results.json"
SEEN_NAME = "smsgsweep-seen.txt"

# Effects that mean the opcode was actually put to a client that PROVED it was still
# running afterwards, and is therefore done with. There is deliberately no entry here for
# the run ending: a crash belongs to a window of opcodes, never to one, so it cannot
# retire a row.
MEASURED = ("REPLIED", "UNDECODABLE", "CONTESTED", "SILENT")
# What a single-suspect crash is filed as, once the dialog has been read.
# ASSERTED is a guard ArenaNet wrote; FAULTED is the absence of one.
CRASH_KINDS = ("ASSERTED", "FAULTED", "CRASHED", "DROPPED_CHANNEL")


def degenerate(codec, opcode, channel="GAME_SMSG", encstring=None):
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
            vals.append(encstring if encstring is not None else "")
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


def corpus_encstring():
    """The SHORTEST real encoded string in the live corpus, read at run time.

    PROVENANCE. This is ArenaNet's authored text, so it is never written into a source
    file, a test or a commit -- it is read from the owner's own captures when the plan is
    built, lands in the vault's plan JSON and in the vault's capture, and nothing else.
    Same pattern `mapbuild.py` uses for FINDINGS 14's mandatory chunks: commit the code
    that fetches it, never the bytes.

    Shortest, because the experiment is about the FORMAT gate and a long string drags in
    whatever else its contents reference. Measured over the corpus: `string16` splits
    cleanly into plain names (0x01DE) and encoded strings (0x0049, 0x004C, 0x0050,
    0x007A), whose first code unit is never below 0x09C4 in 105 samples.
    """
    import tape
    root = vaultpath.require_dir("captures", "live",
                                 why="a real encoded string to test the format gate")
    codec, best = Codec(), None
    ENCODED = (0x0049, 0x004C, 0x0050, 0x007A)
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or not any(f.startswith("game-")
                                           for f in os.listdir(d)):
            continue
        for ch in tape.channel_files(d):
            try:
                _i, ev = tape.load_tape(d, connection=ch["connection"])
                msgs, _r = tape.decode_all(ev, codec, "GAME_SMSG")
            except Exception:
                continue
            for _t, op, vals in msgs:
                if op not in ENCODED:
                    continue
                for f, v in zip([x for x in codec.fields_for("GAME_SMSG", op)
                                 if x["type"] != "msg_header"], vals):
                    if f["type"] == "string16" and isinstance(v, str) and v:
                        if best is None or len(v) < len(best):
                            best = v
    if best is None:
        raise ValueError("no encoded string found in the live corpus; refusing to "
                         "invent one, because the whole question is what the client "
                         "accepts and a guess would answer it wrong in both directions")
    return best


def set_type(codec, opcode, idx, channel="GAME_SMSG"):
    """The declared type of an opcode's 1-based field `idx`, header excluded."""
    fields = [f for f in codec.fields_for(channel, opcode)
              if f["type"] != "msg_header"]
    if not 1 <= idx <= len(fields):
        raise ValueError(f"0x{opcode:04X} has {len(fields)} field(s); {idx} is outside "
                         f"1..{len(fields)}")
    return fields[idx - 1]["type"]


def sets_for(sets, opcode):
    """The {idx: val} that apply to ONE opcode: the global ones plus its own.

    `--set 2=1` is global and must name the same declared type everywhere (check_sets).
    `--set 0x0083:2=1` names one opcode and needs no such agreement, which is what lets
    six different second-gate experiments share one client launch instead of six.
    """
    out = dict(sets.get(None, {}))
    out.update(sets.get(opcode, {}))
    return out


def check_sets(codec, opcodes, sets, channel="GAME_SMSG"):
    """Refuse a --set that means a DIFFERENT field in different opcodes.

    A field index is not a field. `--set 1=1` across the ten opcodes whose first field is
    an `agent_id` is one experiment; across a mixed plan it is ten unrelated ones sharing
    a report, and the SILENT rows would be attributed to a change that never happened in
    them. So the index must name the same declared type in every opcode planned, and the
    refusal names the disagreement rather than dropping the odd one out.
    """
    for opcode, per in (sets or {}).items():
        if opcode is None:
            continue
        for idx in per:                       # a qualified set only has to fit ITS opcode
            set_type(codec, opcode, idx, channel)
    for idx in sorted((sets or {}).get(None, {})):
        kinds = {}
        for opcode in opcodes:
            kinds.setdefault(set_type(codec, opcode, idx), []).append(opcode)
        if len(kinds) > 1:
            raise ValueError(
                f"--set {idx}= names a different field in different opcodes: "
                + "; ".join(f"{t} in {' '.join('0x%04X' % o for o in v[:6])}"
                            for t, v in sorted(kinds.items()))
                + ". A field index is not a field -- plan them separately.")
    return True


def apply_set(values, sets):
    """Override individual fields by 1-based index: `--set 5=1`.

    THE POINT IS TO CHANGE ONE THING. The degenerate payload selects the ZERO branch of
    every gate a handler has, which is what the sweep's asserts have all turned out to be
    -- 0x0017's handler tests its fifth field against zero and skips a whole resource
    load when it is non-zero (0x00807d90, and the crash trace carries that chain by
    address). Filling every field with ones would test that gate and four other things at
    once, and a run that then behaved differently would not say which.
    """
    out = list(values)
    for idx, val in (sets or {}).items():
        if not 1 <= idx <= len(out):
            raise ValueError(f"field {idx} is outside this opcode's 1..{len(out)}")
        cur = out[idx - 1]
        if isinstance(cur, bool) or not isinstance(cur, (int, float)):
            raise ValueError(
                f"field {idx} holds {type(cur).__name__}, and --set only writes numbers. "
                f"A string16 gate wants a real encoded string, not a number cast to one.")
        out[idx - 1] = type(cur)(val)
    return out


def encodable(codec, channel="GAME_SMSG", encstring=None):
    """{opcode: values} for every opcode that encodes. Refusals are returned, not hidden."""
    good, refused = {}, {}
    for key in codec.channels[channel]["messages"]:
        opcode = int(key)
        try:
            vals = degenerate(codec, opcode, channel, encstring)
            codec.encode(channel, opcode, list(vals))
        except Exception as exc:                      # a refusal is a result
            refused[opcode] = f"{type(exc).__name__}: {exc}"
            continue
        good[opcode] = vals
    return good, refused


def check_table_less(classified, schema_opcodes):
    """The literal ten against the disassembler, when the disassembler is there.

    A constant nothing checks is a wish. `classified` is the receive table read out of
    build 38797; the opcodes the schema carries that it does not hold must be exactly
    NOT_IN_RECV_TABLE. Returns None when there is nothing to check against.
    """
    if not classified:
        return None
    missing = set(schema_opcodes) - set(classified)
    if missing != NOT_IN_RECV_TABLE:
        raise ValueError(
            "the receive table disagrees with NOT_IN_RECV_TABLE: the client is missing "
            f"{sorted(hex(o) for o in missing)}, this module says "
            f"{sorted(hex(o) for o in NOT_IN_RECV_TABLE)}. Refusing to plan a sweep "
            "against a constant that no longer describes the binary.")
    return len(missing)


def plan(codec, seen=(), classified=None, done=(), table_less=False,
         settle=SETTLE, control=CONTROL, dwell=DWELL, limit=0, only=None,
         sets=None, reverse=False, encstring=None):
    """The ordered send list: never-seen opcodes first, each with its prediction.

    `seen` is the set observed from ArenaNet -- excluded, because the point is the third
    of the catalogue nothing has ever watched. `done` is the ledger: opcodes a previous
    run already measured, which is how a sweep resumes after a dropped channel.
    `classified` is `msghandler.classify()`'s output if the disassembler is available;
    without it the plan still runs and carries no prediction to score against, which is a
    weaker experiment and says so in the file.

    The ten table-less opcodes are EXCLUDED unless `table_less`, in which case they are
    the only thing in the plan. They are not part of the 324 and one of them ended the
    pilot at step 12.
    """
    good, refused = encodable(codec, encstring=encstring)
    check_table_less(classified, [int(k) for k in codec.channels["GAME_SMSG"]["messages"]])
    seen, done = set(seen), set(done)
    rows, skipped = [], {"seen": 0, "done": 0, "table_less": 0, "not_only": 0}
    for opcode in sorted(good):
        # `only` bisects a crash window, so it overrides every other filter INCLUDING the
        # table-less exclusion and the ledger -- the whole point is to re-send opcodes a
        # previous run could not clear.
        if only is not None:
            if opcode not in only:
                skipped["not_only"] += 1
                continue
            c = (classified or {}).get(opcode) or {}
            vals = apply_set(good[opcode], sets_for(sets or {}, opcode))
            rows.append({"opcode": opcode,
                         "predicted": c.get("class", "UNKNOWN"),
                         "callee": (c.get("callees") or [None])[0],
                         "set": {str(k): v for k, v in
                                 sets_for(sets or {}, opcode).items()},
                         "bytes": len(codec.encode("GAME_SMSG", opcode, list(vals)))})
            continue
        if opcode in seen:
            skipped["seen"] += 1
            continue
        if (opcode in NOT_IN_RECV_TABLE) != bool(table_less):
            skipped["table_less"] += 1
            continue
        if opcode in done:
            skipped["done"] += 1
            continue
        c = (classified or {}).get(opcode) or {}
        rows.append({"opcode": opcode,
                     "predicted": c.get("class", "UNKNOWN"),
                     "callee": c.get("callees", [None])[0] if c.get("callees") else None,
                     "bytes": len(codec.encode("GAME_SMSG", opcode, list(good[opcode])))})
    remaining = len(rows)
    # REVERSE EXISTS FOR ONE CONTROL. The plan is sorted, so 0x0000 is always the FIRST
    # thing the sweep sends, and "the client answers 0x0000" and "the client answers the
    # first message of a sweep" were never separated -- three reproductions and still
    # CONTESTED. Sending it last, behind opcodes already measured SILENT, separates them.
    if reverse:
        rows = rows[::-1]
    if limit:
        rows = rows[:limit]
    return {"rows": rows,
            "remaining": remaining,
            "skipped": skipped,
            "refused": {f"0x{k:04X}": v for k, v in refused.items()},
            "idle_floor": sorted(IDLE_FLOOR),
            "settle": settle,
            "control": control,
            "dwell": dwell,
            "table_less": bool(table_less),
            "encstring": encstring,
            "predicted": bool(classified),
            "note": "degenerate (all-zero) payloads; a handler that early-outs on a "
                    "zero id is indistinguishable here from one that does nothing"}


def plan_path():
    return os.path.join(vaultpath.vault_path("probes"), PLAN_NAME)


def ledger_path():
    return os.path.join(vaultpath.vault_path("probes"), LEDGER_NAME)


def load_plan():
    return _load_json(plan_path())


def load_ledger():
    return _load_json(ledger_path()) or {}


def _load_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)


# ---------------------------------------------------------------- analysis

def read_capture(capture_jsonl):
    """The four streams a run is scored from, and nothing inferred.

    `sent` is OUR sweep sends -- NOT s2c `frame` events. The recorder logs the two
    directions differently and only the receive path writes frames; reading frames finds
    zero stimuli and reports a clean, wrong "nothing happened", which is what the pilot's
    first analyser did.

    `undecodable` is kept APART from `error`. A c2s message our catalogue cannot frame is
    the client answering on an opcode we do not know -- the strongest evidence that
    something happened -- and folding it into "the connection died" loses exactly the
    result the sweep is for.
    """
    sends, replies, undec, gone, life, map_id = [], [], [], None, [], None
    with open(capture_jsonl, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            kind, t = rec.get("kind"), float(rec.get("t", 0.0) or 0.0)
            if kind == "sent" and "PROBE[smsgsweep]" in (rec.get("label") or ""):
                sends.append((t, int(rec.get("opcode", 0))))
            elif kind == "sent" and int(rec.get("opcode", 0)) == MANIFEST_DONE:
                # THE LABEL IS THE ONLY WITNESS, and that is a real weakness stated
                # rather than hidden: `sent` records carry no decoded values, and the
                # recorder writes frames only on the RECEIVE path, so the payload of our
                # own s2c message is not in the capture at all. Parsing our own prose is
                # what `test_cmsgnames` warns about -- so this fails SAFE. No phase-0
                # match means `map_id` stays None and `record` refuses the connection,
                # rather than assuming the baseline and pooling two different worlds.
                m = re.search(r"\[0,\s*map\s+(\d+)\]", rec.get("label") or "")
                if m:
                    map_id = int(m.group(1))
            elif kind == "sent" and int(rec.get("opcode", 0)) == AGENT_LIFE:
                # Every 0x00F1 we sent -- the player dying or being revived. Detected by
                # OPCODE rather than by our own label text, which is prose and would let
                # a reworded log line silently retire the check.
                life.append((t, (rec.get("label") or "")[:40]))
            elif kind == "decoded":
                replies.append((t, int(rec.get("opcode", 0))))
            elif kind == "undecodable":
                undec.append((t, str(rec.get("error", ""))[:160]))
            elif kind in ("error", "disconnect") and gone is None:
                gone = (t, str(rec.get("error", "") or "disconnect")[:160])
    return sends, replies, undec, gone, life, map_id


def control_window(sends, replies, settle, control):
    """What the client said unprompted, measured in THIS run.

    The window is the `control` seconds immediately before the first sweep send. Nothing
    of ours goes out in it by construction, so every opcode in it is noise -- this
    client, this map, this session. Returns (opcodes, span) or (None, None) when there is
    no first send to anchor it, in which case the run can attribute nothing.
    """
    if not sends:
        return None, None
    t0 = min(t for t, _ in sends)
    lo = t0 - float(control)
    got = {op for t, op in replies if lo <= t < t0}
    return got, (lo, t0)


def analyse(capture_jsonl, codec=None, settle=SETTLE, control=CONTROL, planned=None,
            reconnected=False):
    """Score a run from the server's own capture: sent opcode -> what came back.

    Joins the capture to itself. Every c2s message is attributed to the most recent sweep
    send before it, then filtered by IDENTITY against the idle floor AND against this
    run's own control window.

    THE FENCE IS THE CLIENT'S OWN PROOF OF LIFE, NOT THE SOCKET. An opcode is scored only
    if a c2s message arrived AFTER it went out. Fencing on the connection instead was
    wrong by 31.6 seconds and 78 opcodes on 2026-08-12: a Guild Wars assert leaves the
    process ALIVE behind a modal dialog, its message pump stopped and its socket open, so
    the client stopped answering at t=17.16 and `ConnectionResetError` did not arrive
    until t=48.77. Everything between was scored SILENT -- 78 confident measurements of a
    client that was showing a crash dialog. `capture_error_dialog`'s own docstring says a
    ConnectionResetError appears on a clean teardown as readily as on a crash; the
    converse is what bit here, and the client's traffic is the only honest witness.

    WHAT THAT COSTS, stated rather than discovered: the proof of life is the client's
    reply to our ping, which `world_tick` issues every 5 s, so the last ~5 s of sends in
    every run have no proof and come back UNREACHED. At a 0.4 s dwell that is about
    twelve opcodes per run, retried next time. It also sets the CRASH LOCALISATION
    granularity -- a run that dies can only name the window between the last proof of
    life and the end, never a single opcode. Narrow it with a longer dwell, or bisect the
    window with `--only`.
    """
    codec = codec or Codec()
    sends, replies, undec, gone, life, map_id = read_capture(capture_jsonl)
    noise, span = control_window(sends, replies, settle, control)
    floor = set(IDLE_FLOOR) | set(noise or ())

    # The client demonstrably had its message pump running at this moment.
    beats = [t for t, _ in replies] + [t for t, _ in undec]
    alive_until = max(beats) if beats else None
    fence = alive_until if alive_until is not None else -1.0
    if gone is not None:
        fence = min(fence, gone[0])
    live = [(t, op) for t, op in sends if t < fence]
    dead = [op for t, op in sends if t >= fence]

    out = {}
    for i, (t, opcode) in enumerate(live):
        end = live[i + 1][0] if i + 1 < len(live) else float("inf")
        got = [op for rt, op in replies if t <= rt < end and op not in floor]
        contested = [op for rt, op in replies
                     if t <= rt < end and op in (noise or ()) and op not in IDLE_FLOOR]
        bad = [e for rt, e in undec if t <= rt < end]
        row = out.setdefault(opcode, {"sent": 0, "replies": [], "contested": [],
                                      "undecodable": []})
        row["sent"] += 1
        row["replies"].extend(got)
        row["contested"].extend(contested)
        row["undecodable"].extend(bad)

    for opcode, row in out.items():
        if row["replies"]:
            row["effect"] = "REPLIED"
        elif row["undecodable"]:
            row["effect"] = "UNDECODABLE"
        elif row["contested"]:
            row["effect"] = "CONTESTED"
        else:
            row["effect"] = "SILENT"

    # THE RUN ENDING IS A RESULT, AND IT BELONGS TO A WINDOW RATHER THAN TO ONE OPCODE.
    # Attributing it to the last opcode sent named 0x00A9 on 2026-08-12; the client had
    # actually asserted around 0x0012, seventy-eight sends earlier, and sat behind a modal
    # dialog with the socket open. The window is every send with no proof of life after
    # it, and naming one of them would be a guess dressed as a measurement. Bisect it.
    # THE HEARTBEAT SETS THE LOCALISATION, so it is measured and reported rather than
    # assumed from PING_SECONDS: the sweep can only ever name the opcodes between two
    # proofs of life, and how many that is depends on the cadence the run actually ran
    # at. Raise it with authsrv's --ping-seconds to narrow the window.
    beat_times = sorted(t for t in beats if span and t >= span[0])
    gaps = [b - a for a, b in zip(beat_times, beat_times[1:]) if b - a > 1e-6]
    heartbeat = sorted(gaps)[len(gaps) // 2] if gaps else None

    # A CRASH IS SILENCE THAT OUTLASTS THE SOCKET, not merely a tail with no proof.
    # EVERY run's last few sends lack a beat behind them -- that is the standing cost of
    # the fence -- so "dead is non-empty" is true of clean runs too, and treating it as a
    # crash would record the tail of every healthy run as ASSERTED. The discriminator is
    # the gap this whole section exists because of: when the client asserts, it stops
    # answering while the socket stays open (measured 31.6 s, then 120.8 s, then 30.1 s),
    # and when the harness kills a healthy client the two stop together.
    quiet = (gone[0] - alive_until) if (gone and alive_until is not None) else 0.0
    # WHY "THE PLAN DID NOT FINISH" IS NOT ADDED HERE, having been tried on 2026-08-12.
    # It looks like a clean discriminator -- the harness only kills the client after the
    # probe stops sending, so leftover rows mean the client ended the run. It is unsound:
    # a `--hold` shorter than the plan has the harness tearing down mid-send too, and the
    # rule would then blame whichever opcode happened to be last. That is the same false
    # positive the control below already guards, wearing a different hat. A run that ends
    # in one send and an instant close (0x01DA did) is unambiguous to a READER and stays
    # unattributed here on purpose: the refusal is what protects the other 324 rows.
    died = bool(dead) and gone is not None and quiet > max(3.0 * (heartbeat or 0.0), 2.0)
    crash = None
    if died:
        # THE SUSPECTS ARE NOT THE WHOLE WINDOW. Once the client is gone, every later
        # send goes to a dead socket and implicates nothing -- lumping them in reported
        # 78 suspects for a client that died on the sixth. The opcodes that could have
        # done it are the ones sent between the last proof of life and the beat that
        # never arrived: the client processes the stream IN ORDER, so anything it
        # answered a ping after is cleared, and anything sent after the missed beat was
        # never read. Everything else is UNREACHED, not evidence.
        # NO HEARTBEAT, NO SUSPECTS. Without a measured cadence there is no "beat that
        # should have arrived", so every send after the last reply is equally implicated
        # and naming any of them is a guess. Run with authsrv --ping-seconds.
        due = (alive_until + heartbeat) if heartbeat else None
        suspects = sorted({op for t, op in sends
                           if due is not None and alive_until < t <= due})
        crash = {"suspects": suspects,
                 "window": sorted(set(dead)),
                 "heartbeat": heartbeat,
                 "beat_due": due,
                 "alive_until": alive_until,
                 "socket_closed": gone[0] if gone else None,
                 "why": gone[1] if gone else "the client stopped answering"}

    # THE CHANNEL DROP IS A DIFFERENT SHAPE AND IT IS BETTER CONSTRAINED THAN A CRASH.
    # `died` above wants a long silence, which is what an assert behind a modal dialog
    # looks like. A client that answers a ping and closes the socket 19 ms later did not
    # stop -- measured 2026-08-12, when it re-established the channel 42 ms after and
    # went on taking the whole plan again. That case used to fall through with NO suspect
    # at all: the opcode that caused it went into `unreached` and was replanned forever,
    # which is what spun the unattended loop on one plan twice and stopped it. Here the
    # client was demonstrably processing right up to the close, so the sends between the
    # fence and the close are the suspects -- usually exactly one.
    # `reconnected` IS THE WHOLE DISCRIMINATOR, and without it this branch is a
    # false-positive generator. A healthy client killed by the harness at the end of a
    # hold stops its socket and its traffic together -- the same shape to the byte as a
    # client that dropped the channel deliberately. Blaming the last send would then
    # record the tail of EVERY clean run as a channel drop. `test_smsgsweep.py` has a
    # control for exactly that and it caught this branch the first time it was written.
    # What separates the two is what happened NEXT: a client that dropped the channel
    # opened a new one 42 ms later, and the caller can see that because the run produced
    # a second capture. Silence after the close means the harness ended the run.
    elif bool(dead) and gone is not None and reconnected:
        suspects = sorted({op for t, op in sends if fence <= t < gone[0]})
        crash = {"suspects": suspects,
                 "window": sorted(set(dead)),
                 "heartbeat": heartbeat,
                 "beat_due": None,
                 "dropped": True,
                 "alive_until": alive_until,
                 "socket_closed": gone[0],
                 "why": f"the client answered {quiet * 1000:.0f} ms before the socket "
                        f"closed, so it did not stop -- the channel did"}

    # A suspect is IMPLICATED, not unreached -- it demonstrably went out to a client that
    # was still answering. Listing it in both places let one run report 0x0017 as
    # ASSERTED and as "will be retried" in the same breath, which is two readings of one
    # opcode and the sort of thing a later session picks the wrong one of.
    unreached = set(dead) - set(crash["suspects"] if crash else ())
    if planned:
        unreached |= (set(planned) - {op for _, op in live}
                      - set(crash["suspects"] if crash else ()))
    unreached = sorted(unreached)
    # `noise` is EVERYTHING the client said unprompted, which makes the window a check on
    # IDLE_FLOOR as well as a filter: the prior was measured on a parked client, and this
    # one has just loaded a map. Splitting it is the honest report -- what corroborated
    # the prior, and what the prior did not know about.
    # THE MAP HAS TO BE QUIET, AND UNTIL 2026-08-12 IT WAS NOT. The default world spawns
    # a hostile, and it kills the player on a ~13 s cycle: measured over the first three
    # sweeps, KILL at t=7.4 and revive at t=17.4, repeating. Every reading those runs
    # produced was taken on a player who was DEAD -- the sends at 13.4-16.2 all landed
    # between a kill and a revive -- so "SILENT" meant "silent on a corpse", which is not
    # the measurement anyone wanted and is not what the ledger would have said. Run with
    # authsrv --no-enemy. Refusing to record is the only version of this check worth
    # having: a warning would be read once and the rows would go in anyway.
    return {"table": out,
            "map_id": map_id,
            "combat": [(t, why) for t, why in life],
            "crash": crash,
            "heartbeat": heartbeat,
            "alive_until": alive_until,
            "noise": sorted(noise) if noise is not None else None,
            "floor_seen": sorted(set(noise or ()) & IDLE_FLOOR) if noise is not None else None,
            "new_noise": sorted(set(noise or ()) - IDLE_FLOOR) if noise is not None else None,
            "control_span": span,
            "unreached": unreached,
            "gone": gone,
            "capture": os.path.basename(capture_jsonl)}


def record(result, ledger=None):
    """Merge a scored run into the ledger. UNREACHED opcodes are never recorded.

    An opcode is in the ledger only if the capture shows it went out on a live channel.
    That is the whole resume mechanism: a cursor advanced at send time would record
    opcodes the client may never have received, and the sweep would walk past them.
    """
    # THE WORLD HAS TO BE THE SAME ONE, and on 2026-08-12 it silently was not. An opcode
    # near 0x019B made the client drop its game channel; it reconnected 42 ms later and
    # our server handed the fresh connection **map 0** where every other reading in this
    # ledger was taken in map 148. Twenty opcodes were then measured in a different world
    # and pooled with the rest without a word. The operator noticed the map change on
    # screen -- nothing in the readout was looking, exactly as with the hostile.
    got = result.get("map_id")
    if got != BASELINE_MAP:
        raise ValueError(
            "REFUSING to record: this connection loaded "
            + (f"map {got}" if got is not None else "a map this readout could not name")
            + f", not the baseline map {BASELINE_MAP}. Every other row in the ledger was "
              f"measured in {BASELINE_MAP}, and an opcode's behaviour is a property of "
              f"the world it was sent in -- pooling two is the mistake toolkit/origin.py "
              f"exists to refuse one door along. Score it separately or discard it.")
    if result.get("combat"):
        raise ValueError(
            f"REFUSING to record: this run sent {len(result['combat'])} "
            f"0x{AGENT_LIFE:04X} message(s), so the player died or was revived during "
            f"the sweep. The default world spawns a hostile that kills the player on a "
            f"~13 s cycle, and every reading taken between a kill and a revive is a "
            f"measurement of a CORPSE -- 'SILENT' would mean 'silent while dead'. "
            f"Re-run with `authsrv.py --no-enemy`. First at t="
            f"{result['combat'][0][0]:.2f}s: {result['combat'][0][1]}")
    ledger = dict(ledger if ledger is not None else load_ledger())
    added = 0
    for opcode, row in result["table"].items():
        if row["effect"] not in MEASURED:
            continue
        key = f"0x{opcode:04X}"
        if key in ledger:
            continue
        ledger[key] = {"effect": row["effect"],
                       "replies": sorted(set(row["replies"])),
                       "contested": sorted(set(row["contested"])),
                       "undecodable": row["undecodable"][:2],
                       "capture": result["capture"]}
        added += 1
    # A crash window of ONE is the only case where the run ending is attributable, and
    # then it is the strongest result the sweep produces: this opcode stops the client.
    # Recording it is also what lets the sweep converge -- otherwise --resume replans the
    # opcode that killed the last run, and every run dies in the same place forever.
    # A window of two or more records NOTHING and must be bisected with --only.
    crash = result.get("crash")
    if crash and len(crash.get("suspects") or []) == 1:
        key = f"0x{crash['suspects'][0]:04X}"
        if key not in ledger:
            # THE DEFAULT COMES FROM THE MEASUREMENT, NOT FROM THE CALLER. `crash_kind`
            # is set by whoever read the crash dialog; without it a channel drop would
            # file as ASSERTED, which is the wrong word for a client that re-established
            # and kept playing. The `crash` dict already knows which shape it saw.
            kind = result.get("crash_kind") or (
                "DROPPED_CHANNEL" if crash.get("dropped") else "ASSERTED")
            ledger[key] = {"effect": kind, "replies": [], "contested": [],
                           "undecodable": [],
                           "why": result.get("crash_detail") or crash["why"],
                           "capture": result["capture"]}
            added += 1
    return ledger, added


def done_opcodes(ledger=None):
    ledger = ledger if ledger is not None else load_ledger()
    return {int(k, 16) for k in ledger}


def observed_from_live():
    """The GAME_SMSG opcodes ArenaNet has actually sent us, rebuilt from the tapes.

    THE DENOMINATOR HAS TO BE REPRODUCIBLE. The pilot's `seen` list was a text file
    somebody made once, in a scratch directory that does not survive the session -- and
    "324 never-seen opcodes" is a claim about that file as much as about the client. This
    recomputes it from the live captures with `tape.decode_all`, which frames the WHOLE
    stream: the per-event idiom it replaced lost 4,251 messages of 22,137 and invented
    117, and an opcode seen only in a lost message would be swept as never-seen.

    Live captures only. Pooling ours with ArenaNet's is the one thing `toolkit/origin.py`
    exists to refuse, and a sweep whose denominator counted our own server's sends would
    exclude exactly the opcodes it is meant to try.
    """
    import tape
    root = vaultpath.require_dir("captures", "live",
                                 why="the sweep's denominator is what ArenaNet has sent")
    codec = Codec()
    seen, dirs = set(), []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if not any(f.startswith("game-") and f.endswith(".jsonl")
                   for f in os.listdir(path)):
            continue
        for ch in tape.channel_files(path):
            conn = ch["connection"] if isinstance(ch, dict) else str(ch)
            # NOT FILTERED BY PORT, and this cost a wrong number before it was written
            # down: a `:6112` filter looks like the obvious way to keep the web gateway
            # out, and it silently cut the corpus from 155 opcodes to 52. ArenaNet serves
            # the GAME channel on port 80 in 10 of the 12 canon connections -- both
            # 20260807T143055 and 20260810T235916 are entirely port 80 -- so the port
            # says nothing about the protocol. `channel_files` selects decrypted game
            # channels by content and `load_tape` refuses any capture that is not live;
            # those are the discriminators, and the count is the check.
            try:
                _info, events = tape.load_tape(path, connection=conn)
                msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG")
            except Exception as exc:
                print(f"  SKIP {name}/{conn}: {type(exc).__name__}: "
                      f"{str(exc).splitlines()[0][:120]}")
                continue
            seen |= {op for _t, op, _v in msgs}
            dirs.append(f"{name}/{conn} ({len(msgs)} msgs, {receipt[0]:,}/{receipt[1]:,}B)")
    if not seen:
        raise ValueError(
            "no GAME_SMSG opcode was read from any live capture. Refusing to write an "
            "empty observed set: it would make the sweep plan EVERY opcode, including "
            "the 155 ArenaNet has already shown us, and the run would look bigger "
            "rather than broken.")
    return seen, dirs


def crash_kind(report_json):
    """(kind, detail) from the crash dialog the harness captured beside this report.

    ASSERT and FAULT ARE DIFFERENT RESULTS and conflating them cost a wrong paragraph in
    `studies/smsgsweep/FINDINGS.md`. An assert is a guard ArenaNet WROTE -- it names the
    condition that had to hold. An access violation is the absence of one: the handler
    dereferenced something the payload chose and nobody checked it. Three opcodes were
    reported as "assert text not captured" when their dialogs said `Exception: c0000005`
    the whole time; the reader only ever grepped for the word Assertion, so a whole class
    of result was invisible by construction.
    """
    dlg = os.path.join(os.path.dirname(report_json), "crash-dialog.txt")
    if not os.path.isfile(dlg):
        return None, None
    with open(dlg, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Assertion:"):
            return "ASSERTED", line.split(":", 1)[1].strip()
        if line.startswith("Exception:"):
            return "FAULTED", line.split(":", 1)[1].strip()
    return "CRASHED", "dialog captured, neither an assert nor an exception line in it"


def captures_from_report(report_json):
    """EVERY gamesrv capture this run produced, in the order the report lists them.

    Never the newest file in a directory. `sorted(...)[-1]` picked the wrong client on
    2026-08-06 and the same reasoning applies to a capture: the run that wrote the report
    is the run whose captures must be scored, and the report says which those are.

    MORE THAN ONE IS NORMAL AND IS ITSELF A RESULT. Measured 2026-08-12: an opcode in
    0x017E..0x019B made the client drop its game channel at t=36.16 and open a new one
    42 ms later, and the probe -- which runs per connection -- restarted from the top of
    the plan on the fresh channel. So the run holds TWO experiments, each with its own
    control window and its own fence, and they must be scored as two. An earlier version
    refused the whole run rather than pick one; that refusal was right about the danger
    and wrong about the remedy, and it spun the unattended loop on the same plan twice.
    """
    with open(report_json, encoding="utf-8") as fh:
        rep = json.load(fh)
    caps = [c for c in rep.get("captures", []) if "gamesrv" in c.replace("\\", "/")]
    if not caps:
        raise ValueError(f"{report_json} names no gamesrv capture at all")
    return caps


def capture_from_report(report_json):
    """The single gamesrv capture, refusing when the run made more than one."""
    caps = captures_from_report(report_json)
    if len(caps) != 1:
        raise ValueError(f"{report_json} names {len(caps)} gamesrv captures; "
                         f"expected exactly 1 -- use captures_from_report")
    return caps[0]


# ---------------------------------------------------------------- reporting

def print_run(result):
    table = result["table"]
    by = {}
    for row in table.values():
        by[row["effect"]] = by.get(row["effect"], 0) + 1
    if result["noise"] is None:
        print("NO CONTROL WINDOW: this run has no sweep send to anchor one, so nothing "
              "it saw can be attributed. Scoring stops here.")
        return 2
    span = result["control_span"]
    fs = " ".join("0x%04X" % o for o in result["floor_seen"]) or "-"
    nn = " ".join("0x%04X" % o for o in result["new_noise"]) or "-"
    print(f"control window {span[0]:.2f}..{span[1]:.2f}s "
          f"({span[1] - span[0]:.1f}s of nothing sent):")
    print(f"  known idle floor seen: {fs}   NEW unprompted this run: {nn}")
    if result["new_noise"]:
        print("  -> the prior floor {0x0008, 0x0009} was measured on a PARKED client; "
              "these are what a just-loaded one adds, and no reply on them counts.")
    if result.get("combat"):
        first = result["combat"][0]
        print(f"  *** THE MAP WAS NOT QUIET: {len(result['combat'])} kill/revive "
              f"message(s), first at t={first[0]:.2f}s ({first[1]}). Every reading below "
              f"was taken while the default hostile was killing the player on its ~13 s "
              f"cycle, so a SILENT row means 'silent while dead'. --record will refuse. "
              f"Re-run with authsrv --no-enemy.")
    hb = result.get("heartbeat")
    if hb:
        print(f"  heartbeat (client's proof of life): {hb:.2f}s median -- so a crash "
              f"localises to about {max(1, int(round(hb / DWELL)))} opcode(s). "
              f"Narrow it with authsrv --ping-seconds.")
    print(f"{len(table)} opcode(s) stimulated on a live channel -> "
          + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    for want in ("REPLIED", "UNDECODABLE", "CONTESTED"):
        for opcode in sorted(o for o, r in table.items() if r["effect"] == want):
            row = table[opcode]
            if want == "REPLIED":
                got = " ".join(f"0x{o:04X}" for o in sorted(set(row["replies"])))
                print(f"  REPLIED      0x{opcode:04X} -> {got}")
            elif want == "UNDECODABLE":
                print(f"  UNDECODABLE  0x{opcode:04X} -> {row['undecodable'][0]}")
            else:
                got = " ".join(f"0x{o:04X}" for o in sorted(set(row["contested"])))
                print(f"  CONTESTED    0x{opcode:04X} -> {got} (also unprompted)")
    c = result["crash"]
    if c:
        s, w = c["suspects"], c["window"]
        print(f"\nTHE RUN ENDED. Last proof of life t={c['alive_until']:.2f}s"
              + (f", next beat due t={c['beat_due']:.2f}s and never arrived"
                 if c["beat_due"] else "")
              + (f", socket closed t={c['socket_closed']:.2f}s "
                 f"({c['socket_closed'] - c['alive_until']:.1f}s later)"
                 if c["socket_closed"] else "") + ".")
        if len(s) == 1:
            k = result.get("crash_kind")
            if k:
                print(f"  {k}: {result.get('crash_detail')}")
            # The two cases are localised by DIFFERENT evidence and the line has to say
            # which, because "missed the ping behind it" is simply untrue of a drop --
            # the client answered, then closed the socket 19 ms later.
            why = ("the client answered a ping after the send before it and then closed "
                   "the channel with this one outstanding"
                   if c.get("dropped") else
                   "the client answered a ping after the send before it and missed the "
                   "ping behind it")
            print(f"  SUSPECT: 0x{s[0]:04X} -- ALONE. {why}, and it reads the stream in "
                  f"order. Recorded as {k or 'ASSERTED'}.")
        elif s:
            print(f"  SUSPECTS: {len(s)} opcode(s) sent between the last proof of life "
                  f"and the missed beat -- {' '.join('0x%04X' % o for o in s)}")
            print(f"  Bisect:  --plan --only {','.join('0x%04X' % o for o in s)}  "
                  f"with a dwell ABOVE the heartbeat so each gets its own beat")
        else:
            print("  NO SUSPECT: the client was never proved alive during the sweep.")
        print(f"  ({len(w) - len(s)} further send(s) went to a client that was already "
              f"gone. They implicate nothing and are UNREACHED, not evidence.)")
        print("  A Guild Wars assert leaves the process ALIVE behind a modal dialog with "
              "its socket open, so the socket time is an upper bound and nothing more.")
    if result["unreached"]:
        u = result["unreached"]
        print(f"  {len(u)} planned opcode(s) UNREACHED, not recorded, will be retried: "
              + " ".join(f"0x{o:04X}" for o in u[:12]) + (" ..." if len(u) > 12 else ""))
    if not by.get("REPLIED") and not by.get("UNDECODABLE"):
        print("  (no replies. With all-zero payloads that is the expected common case, "
              "and it is NOT evidence of a missing handler -- every entry in the receive "
              "table dispatches.)")
    return 0


def print_report(ledger, codec):
    total = len({int(k) for k in codec.channels["GAME_SMSG"]["messages"]})
    by = {}
    for row in ledger.values():
        by[row["effect"]] = by.get(row["effect"], 0) + 1
    print(f"ledger: {len(ledger)} opcode(s) measured of {total} catalogued")
    for k, v in sorted(by.items()):
        print(f"  {k:<16} {v}")
    for want in ("REPLIED", "UNDECODABLE", "DROPPED_CHANNEL", "CONTESTED"):
        for key in sorted(k for k, r in ledger.items() if r["effect"] == want):
            row = ledger[key]
            detail = (" ".join(f"0x{o:04X}" for o in row["replies"])
                      or " ".join(f"0x{o:04X}" for o in row["contested"])
                      or (row["undecodable"] or [""])[0])
            print(f"  {want:<16} {key} {detail}  [{row['capture']}]")
    return 0


def _classify():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
        import msghandler
        return msghandler.classify(msghandler.Image())
    except (ImportError, SystemExit, OSError) as exc:
        print(f"(no static prediction: {type(exc).__name__}: {exc})")
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true", help="write the plan and exit")
    ap.add_argument("--analyse", metavar="CAPTURE_JSONL", default=None,
                    help="score a completed run from the server's capture")
    ap.add_argument("--from-report", metavar="REPORT_JSON", default=None,
                    help="score the run this session report names (never the newest file)")
    ap.add_argument("--record", action="store_true",
                    help="merge the scored run into the ledger so --resume skips it")
    ap.add_argument("--report", action="store_true", help="print the ledger and exit")
    ap.add_argument("--resume", action="store_true",
                    help="plan only what the ledger has NOT measured")
    ap.add_argument("--table-less", action="store_true",
                    help="plan ONLY the ten opcodes with no receive-table entry. They "
                         "are handled below the message table and one of them tore the "
                         "game channel down; enter this deliberately, with --limit 1")
    ap.add_argument("--seen", default=None, metavar="FILE",
                    help="opcodes observed from ArenaNet, one per line")
    ap.add_argument("--write-seen", action="store_true",
                    help="recompute the observed set from the live tapes and write it "
                         "to the vault, then exit")
    ap.add_argument("--encstring", action="store_true",
                    help="fill every string16 field with a REAL encoded string read "
                         "from the live corpus at plan time, instead of an empty one. "
                         "Tests whether the format gate is the whole gate")
    ap.add_argument("--reverse", action="store_true",
                    help="send the plan in descending order. The control for 0x0000, "
                         "which is otherwise always the first message of every sweep")
    ap.add_argument("--limit", type=int, default=0,
                    help="keep only the first N rows of the plan")
    ap.add_argument("--set", default=None, metavar="IDX=VAL", action="append",
                    help="override one field: --set 5=1 applies to every planned opcode "
                         "(and is refused unless index 5 is the same declared type in "
                         "each); --set 0x0083:2=1 applies to one. Changes ONE thing per "
                         "field, because the sweep's asserts are zero-branch gates and "
                         "filling everything would test five things at once")
    ap.add_argument("--only", default=None, metavar="OPCODES",
                    help="plan exactly these (comma-separated, 0x ok), overriding every "
                         "filter. This is how a crash window is bisected down to the one "
                         "opcode that ended a run")
    ap.add_argument("--settle", type=float, default=SETTLE)
    ap.add_argument("--control", type=float, default=CONTROL)
    ap.add_argument("--dwell", type=float, default=DWELL)
    a = ap.parse_args()
    codec = Codec()

    if a.report:
        return print_report(load_ledger(), codec)

    if a.write_seen:
        seen, dirs = observed_from_live()
        path = os.path.join(vaultpath.vault_path("probes"), SEEN_NAME)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# GAME_SMSG opcodes OBSERVED from ArenaNet. Regenerate with\n"
                     "#   python toolkit/authsrv/smsgsweep.py --write-seen\n"
                     f"# {len(dirs)} live connection(s): {', '.join(dirs)}\n")
            for o in sorted(seen):
                fh.write(f"0x{o:04x}\n")
        print(f"{len(seen)} observed over {len(dirs)} live connection(s) -> {path}")
        return 0

    caps = [a.analyse] if a.analyse else []
    if a.from_report:
        caps = captures_from_report(a.from_report)
    if caps:
        p = load_plan() or {}
        rc, total = 0, 0
        for n, cap in enumerate(caps, 1):
            if len(caps) > 1:
                print(f"\n--- connection {n} of {len(caps)}: {os.path.basename(cap)}")
            result = analyse(cap, codec,
                             settle=p.get("settle", a.settle),
                             control=p.get("control", a.control),
                             planned=[r["opcode"] for r in p.get("rows", [])],
                             reconnected=(n < len(caps)))
            # THE DIALOG BELONGS TO THE LAST CONNECTION ONLY. The earlier ones ended
            # because the client dropped the channel and opened a NEW one 42 ms later --
            # it was alive and went on playing, so labelling their suspect with a crash
            # the last connection produced is the pilot's "DIED" mistake with more steps.
            if a.from_report and n == len(caps):
                kind, detail = crash_kind(a.from_report)
                result["crash_kind"], result["crash_detail"] = kind, detail
            elif a.from_report:
                result["crash_kind"] = "DROPPED_CHANNEL"
                result["crash_detail"] = ("the client re-established its game channel "
                                          "and kept running; it did not stop")
            one = print_run(result)
            rc = rc or one
            if a.record and one == 0:
                try:
                    ledger, added = record(result)
                except ValueError as exc:
                    print(f"\n{exc}", file=sys.stderr)
                    return 3
                _write_json(ledger_path(), ledger)
                total += added
        if a.record:
            print(f"\nrecorded {total} newly measured opcode(s) -> {ledger_path()}")
        return rc

    seen = set()
    if a.seen:
        with open(a.seen, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line:
                    seen.add(int(line, 0))
    done = done_opcodes() if a.resume else set()
    only = None
    if a.only:
        only = {int(x, 0) for x in a.only.replace(" ", "").split(",") if x}
    sets = {}
    for spec in (a.set or []):
        lhs, _, v = spec.partition("=")
        op, _, idx = lhs.rpartition(":")
        key = int(op, 0) if op else None
        sets.setdefault(key, {})[int(idx, 0)] = int(v, 0)
    if sets and only is None:
        print("REFUSED: --set without --only would apply one field index to every "
              "opcode in the plan, which means a different field in each.",
              file=sys.stderr)
        return 2
    if sets:
        try:
            check_sets(codec, sorted(only), sets)
        except ValueError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
    try:
        p = plan(codec, seen, _classify(), done=done, table_less=a.table_less,
                 settle=a.settle, control=a.control, dwell=a.dwell, limit=a.limit,
                 only=only, sets=sets, reverse=a.reverse,
                 encstring=corpus_encstring() if a.encstring else None)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    _write_json(plan_path(), p)
    kinds = {}
    for r in p["rows"]:
        kinds[r["predicted"]] = kinds.get(r["predicted"], 0) + 1
    mode = "TABLE-LESS (below the message table)" if p["table_less"] else "receive table"
    print(f"{len(p['rows'])} opcode(s) planned of {p['remaining']} remaining [{mode}] "
          f"-> {plan_path()}")
    print(f"  predicted: {kinds}")
    print(f"  skipped: {p['skipped']}")
    print(f"  settle {p['settle']}s, control window {p['control']}s, dwell {p['dwell']}s "
          f"-> about {p['settle'] + p['control'] + p['dwell'] * len(p['rows']):.0f}s")
    if p["refused"]:
        print(f"  {len(p['refused'])} refused to encode: {list(p['refused'])[:6]}")
    if not p["rows"]:
        print("  NOTHING TO SEND. A probe that sends nothing measures nothing; do not "
              "launch a client for this plan.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
