r"""The loopback opcode sweep's READOUT, against captures this file builds out of dicts.

The sweep sends GAME_SMSG opcodes ArenaNet has never shown us to a client we control and
scores what comes back. Everything hard about it is in the scoring, and the pilot of
2026-08-12 proved that the hard part fails SILENTLY: all four of its defects printed a
confident number instead of an error, and three printed the wrong one. So this file is
mostly negative controls -- for each defect, the broken behaviour is reproduced inline
and required to differ from the fixed one.

    python toolkit/authsrv/test_smsgsweep.py

NO VAULT, NO SOCKET, NO CLIENT. A scoring defect is not a property of any one capture,
and a test that needs a client to find one can only run on days a client is up.

THE FIVE THINGS IT PINS:

  1. **The stimulus is `sent`, not an s2c `frame`.** The recorder logs the two directions
     differently and only the receive path writes frames. The pilot's analyser read
     frames, found zero stimuli in a run that sent twelve, and reported "nothing
     happened". The control is a capture holding both kinds, where the frame reader
     scores 0.

  2. **The control window is the run's own noise floor.** The inherited floor
     {0x0008, 0x0009} was measured on a PARKED client; the sweep's client has just
     finished loading a map. An opcode the client emits unprompted in the quiet window
     before the first send is not a reply to anything, and a "reply" on it is CONTESTED.

  3. **Nothing sent after the channel went away is scored.** The send loop catches and
     continues, so a dead socket can still produce `sent` records; scoring those SILENT
     reports the client's opinion of opcodes it never received. They come back UNREACHED.

  4. **UNDECODABLE is a reply, not a death.** A c2s message our catalogue cannot frame is
     the client answering on an opcode we do not know -- the strongest evidence anything
     happened at all. The recorder writes `undecodable` and `error` as different kinds
     and folding them together loses exactly the result the sweep is for.

  5. **The ledger records only what was measured**, which is the whole resume mechanism.
     A cursor advanced at send time would record opcodes the client never received and
     the sweep would walk past them for good.

AND A SIXTH, ADDED 2026-08-13, WHICH IS THE ONE THAT COST THE MOST. **A ledger row is a
measurement of an opcode AND of the payload it was sent with**, and for a day it was
keyed by the opcode alone. Four opcodes -- 0x0033, 0x009E, 0x00B9, 0x00C0 -- crashed the
client on an all-zero payload and went SILENT when the same opcode carried a real encoded
string, two of them naming a guard that is ABOUT the string. Nine runs measured that and
none could be recorded: `record` is first-write-wins, every key was already taken, and
`--record` printed `recorded 0`, which reads as "nothing new" and meant "your measurement
was discarded". Section 9 pins the whole dimension, and its load-bearing check is the
SABOTAGE: the regime-less key is reproduced inline, run on the same two fixtures, and
required to lose one of the two results -- so "the key needs a regime in it" is a
difference between two live answers rather than an assertion about the code.

AND ONE THAT IS NOT ABOUT SCORING. `degenerate` must read the CODEC, never
`schema/messages.json` -- `overrides.json` changes the field list of exactly three
opcodes, so a builder reading the base catalogue gets the arity wrong for those three
and only those three. Section 0 measures both and requires the difference to be exactly
{140, 146, 421}: a check that names the three is a check that can fail if a fourth is
added, which is the point.

AND ONE THAT IS NOT ABOUT smsgsweep AT ALL (section 9, 2026-08-13). Everything above runs
inside this module -- plan() resolves the overrides, apply_set applies them, encodable()
encodes them -- so the module agreed with itself perfectly while `--set` was putting the
DEGENERATE payload on the wire. The consumer is `probes._smsgsweep_steps`, which built the
Steps the server actually sends and read the overrides off the PLAN when plan() writes
them per ROW.

The regression is the shape worth remembering: `p.get("set")` was CORRECT when --set
shipped (f3e0d95, 2026-08-12 10:59), and became a no-op an hour later when the qualified
`--set 0x0083:2=1` form replaced the top-level key with sets_for (c7c7da6, 12:00). One
side of a two-module contract moved and the other was not touched, so nothing errored and
nothing downstream could catch it: the plan file is right, the capture is right, and
`record` scores the capture -- so a --set run reads as a measurement of the all-zero
payload wearing the label of the experiment. Five of studies/smsgsweep/FINDINGS.md §5c's
gate experiments were retracted for it; the server's own `plain=` hexdumps settled which,
because the bytes were recorded even though nothing was reading them. Section 9 is the
only place the two halves are made to meet, and it goes through a REAL FILE because the
plan reaches the probe as JSON.

FIVE SABOTAGES WERE BUILT AND RUN (2026-08-13), and the last one is the reason steps_for
is written the way it is:

    1. the original defect, `p.get("set")`                        3 red
    2. `rows[0]["set"]` for every row                             1 red  <- the per-row check alone
    3. drop the `int(k)` cast (str keys straight from JSON)       2 red, naming the TypeError
    4. wrong key name, `row.get("sets")`                          3 red
    5. sabotage 3 with a fixture that skips the file              0 red -- ALL 72 PASS

Number 5 breaks the TEST rather than the source: hand the builder an in-memory dict with
int keys and the missing cast is invisible, green, and raises on the first real run. The
JSON round trip is the only thing standing there. Number 3 also found a defect in this
section's own first draft -- steps_for returned [] and a later check indexed got[0], so a
caught defect was reported as a bare traceback with no verdict banner at all.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402
import smsgsweep as sw  # noqa: E402
from codec import Codec  # noqa: E402

# Floor 118, MEASURED from a green run on 2026-08-13 on the merged file. THREE arcs raised
# it the same day and no number survives alone: 64 -> 75 when section 7b pinned the
# planner's exit code, 64 -> 99 when section 9 added the regime, and 110 -> 118 when
# section 10 met the probe. Each was RE-MEASURED on the merged file rather than added up,
# because a floor computed from branch numbers is a guess about a file no branch ran.
# Sections 0 and 2-7b and 9 need no vault, no socket and no client -- because a scoring
# defect is not a property of any one capture, and neither is a key format. Section 10
# needs none of the three either, but it DOES need `content.load()` to succeed, because
# the step builder it checks lives in probes.py, which imports the world at module scope.
# Two sections
# do need more and both declare their skips: section 1's cross-check of NOT_IN_RECV_TABLE
# against the client's own receive table wants capstone and the pinned client (2), and
# section 8's rebuild of the observed set wants the live captures (3). A machine missing
# either lands under the floor and goes RED, deliberately, the way test_mapexport treats a
# vault-less run: those two sections are the ones that pin the sweep's DENOMINATOR and the
# ten opcodes that tear the game channel down, and a plan built on a constant nothing
# confirmed is exactly the wish this repo keeps refusing.
LEDGER = checks.Ledger("smsgsweep: the loopback sweep's readout", floor=118)

# The three captures the canon-12 denominator was measured on. Named because a pin is
# a fact about ITS corpus: the vault now also holds two live Factions captures
# (2026-08-17), which take the unfiltered pool to 177 opcodes over 20 connections --
# 22 opcodes ArenaNet had never sent us before. That is new evidence for a new check,
# not a reason for this one to move; the same rule test_npcdefs, test_agentroster and
# test_unitassembly already follow.
CANON_CAPTURES = ("20260807T133758", "20260807T143055", "20260810T235916")

# MEASURED 2026-08-12: the opcodes whose field list `overrides.json` changes. Written as
# literals rather than recomputed from the module under test.
OVERRIDDEN = {140, 146, 421}
# MEASURED 2026-08-13 over build 38797's catalogue: how many GAME_SMSG opcodes carry a
# `string16` field at all, and how many `--encstring` can actually FILL. They are not the
# same number, and the gap is the finding this section produced on its first run:
# `degenerate` stops at a `nested_struct` (the tail after it is the element layout, and an
# empty element list emits none of it), and 0x019D hides its `string16` behind one. So 87
# carry the field, 86 can be moved, and 401 -- not 400 -- go out byte-identically either
# way. Written as literals because the whole design rests on the regime coming from the
# PAYLOAD rather than from the flag, and this is the case where the flag lies.
WITH_STRING16 = 87
FILLABLE = 86
NESTED_STRING16 = {0x019D}
# A string of OUR OWN for the encstring fixtures. Deliberately not the corpus one:
# `corpus_encstring()` reads ArenaNet's authored text out of the vault, and the regime
# axis is "the string16 fields are empty" versus "they are not", which any string
# exercises. So this file needs no vault for section 9 and commits no borrowed bytes.
OURS = "A"
# The ten with no receive-table entry on build 38797. Same literal as
# toolkit/clientscan/test_msghandler.py, deliberately: two files asserting one measured
# fact is how a constant that drifts gets caught in the tree that still cares.
TABLE_LESS = {0x000A, 0x000B, 0x000C, 0x000D, 0x000E, 0x004F, 0x0055, 0x007F,
              0x014A, 0x01DA}


def capture(records, map_id=148):
    """Write a capture jsonl the way the recorder does, and return its path.

    Every capture carries a phase-0 MANIFEST_DONE naming its map, because a real one does
    and `record` refuses a connection whose world it cannot name. `map_id=None` writes
    none, which is the fixture for that refusal.
    """
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                     encoding="utf-8")
    rows = list(records)
    if map_id is not None and not any(r.get("opcode") == 0x0197 for r in rows):
        rows.insert(0, manifest(map_id))
    for rec in rows:
        fh.write(json.dumps(rec) + "\n")
    fh.close()
    return fh.name


def manifest(map_id=148):
    """The server's phase-0 MANIFEST_DONE, which is how a capture names its map."""
    return {"kind": "sent", "t": 1.0, "opcode": 0x0197,
            "label": f"MANIFEST_DONE[0, map {map_id}]"}


_CODEC = None


def _codec():
    global _CODEC
    if _CODEC is None:
        _CODEC = Codec()
    return _CODEC


def send(t, opcode, encstring=None, plain=...):
    """A probe send, CARRYING ITS PLAINTEXT the way the recorder writes it.

    The fixture used to omit `plain`, which was fine while a row was keyed by opcode
    alone and is not fine now: the regime of a row is read out of the bytes that went on
    the wire, so a fixture with no bytes is a fixture that cannot exercise the thing this
    file exists to check. `plain=None` writes the record WITHOUT the field, which is the
    fixture for a capture from a recorder that logged no plaintext -- `record` must refuse
    such a row rather than file it under a guess.
    """
    rec = {"kind": "sent", "t": t, "opcode": opcode,
           "label": f"PROBE[smsgsweep] [1/9] 0x{opcode:04X} (BODY)"}
    if plain is ...:
        codec = _codec()
        plain = codec.encode("GAME_SMSG", opcode,
                             list(sw.degenerate(codec, opcode,
                                                encstring=encstring))).hex()
    if plain is not None:
        rec["plain"] = plain
    return rec


def c2s(t, opcode):
    return {"kind": "decoded", "t": t, "opcode": opcode, "name": "?"}


def frame(t, opcode):
    """An s2c frame -- what the pilot's analyser mistook for a stimulus."""
    return {"kind": "frame", "t": t, "opcode": opcode, "direction": "s2c", "n": 6}


def steps_for(pr, sw_mod, plan_obj):
    """The probe's Steps for a plan, reached THROUGH A REAL FILE.

    `probes._smsgsweep_steps` calls `smsgsweep.load_plan()`, which reads JSON off disk, so
    every key in a row's `set` arrives as a STRING. Handing the builder an in-memory dict
    would let a version that dropped the `int(k)` cast pass this whole section and then
    raise TypeError inside apply_set on the first real --set run -- the same shape of
    fixture-too-kind failure the sweep's own pilot kept producing.

    `plan_path()` is monkeypatched rather than used, so this needs no vault.

    A raising builder returns [] and PRINTS why, rather than propagating. `_smsgsweep_steps`
    catches only ValueError, so a builder that fed apply_set a string key would die of
    TypeError -- and an uncaught exception here would kill the run before the verdict
    banner, which is the trap SystemExit set for test_stripbuild: a control that aborts
    the process looks nothing like a control that goes red.
    """
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    fh.close()
    sw_mod._write_json(fh.name, plan_obj)
    real = sw_mod.plan_path
    sw_mod.plan_path = lambda: fh.name
    try:
        return [s for s in pr._smsgsweep_steps(None, None)]
    except Exception as exc:
        print(f"     (step builder raised {type(exc).__name__}: "
              f"{str(exc).splitlines()[0][:70]})")
        return []
    finally:
        sw_mod.plan_path = real
        os.unlink(fh.name)


def naive_frame_reader(path):
    """THE PILOT'S DEFECT, reproduced. Reads s2c frames as the stimulus stream."""
    n = 0
    for line in open(path, encoding="utf-8"):
        rec = json.loads(line)
        if rec.get("kind") == "frame" and rec.get("direction") == "s2c":
            n += 1
    return n


def main():
    codec = Codec()

    # ---- 0. the values come from the codec, not from the catalogue -----------
    print("0. degenerate values read the codec")
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "schema",
                           "messages.json"), encoding="utf-8") as fh:
        base = json.load(fh)["channels"]["GAME_SMSG"]["messages"]
    differ = set()
    for key in base:
        opcode = int(key)
        raw = [f for f in base[key]["fields"] if f["type"] != "msg_header"]
        try:
            cooked = [f for f in codec.fields_for("GAME_SMSG", opcode)
                      if f["type"] != "msg_header"]
        except Exception:
            continue
        if [f["type"] for f in raw] != [f["type"] for f in cooked]:
            differ.add(opcode)
    LEDGER.ok(differ == OVERRIDDEN,
              f"overrides.json changes the field list of exactly {sorted(OVERRIDDEN)}",
              f"{sorted(differ)} -- a builder reading the base catalogue would produce "
              f"the wrong arity for these and ONLY these, which is why degenerate() "
              f"reads fields_for()")
    good, refused = sw.encodable(codec)
    LEDGER.ok(len(good) + len(refused) == len(base),
              f"every one of the {len(base)} catalogued opcodes is accounted for",
              f"{len(good)} encode, {len(refused)} refuse -- refusals are RETURNED "
              f"rather than dropped, so a plan cannot silently shrink")
    for opcode in sorted(OVERRIDDEN):
        if opcode not in good:
            continue
        n_fields = len([f for f in codec.fields_for("GAME_SMSG", opcode)
                        if f["type"] != "msg_header"])
        LEDGER.ok(len(good[opcode]) == n_fields,
                  f"0x{opcode:04X} gets {n_fields} value(s), the OVERRIDDEN arity",
                  f"{len(good[opcode])}")

    # ---- 1. the plan, and the ten it must not walk into ----------------------
    print("\n1. the plan")
    p = sw.plan(codec)
    ops = {r["opcode"] for r in p["rows"]}
    LEDGER.ok(not (ops & TABLE_LESS),
              "the default plan holds NONE of the ten table-less opcodes",
              "they are handled below the message table, and 0x000B tore the game "
              "channel down at step 12 of the pilot")
    pt = sw.plan(codec, table_less=True)
    ops_t = {r["opcode"] for r in pt["rows"]}
    LEDGER.ok(ops_t and ops_t <= TABLE_LESS and not (ops_t & ops),
              f"--table-less plans ONLY those ({len(ops_t)} of them) and nothing else",
              f"{sorted(hex(o) for o in ops_t)}")
    LEDGER.ok(p["settle"] > 0 and p["control"] > 0
              and p["settle"] >= 4.0,
              f"the plan carries settle={p['settle']}s and control={p['control']}s",
              "the analyser reads both back from the plan, so the control window cannot "
              "silently move off the quiet part of the run")
    # The literal-vs-binary cross-check. Skips without capstone, and says so.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
        import msghandler
        table = msghandler.classify(msghandler.Image())
    except (ImportError, SystemExit, OSError) as exc:
        table = None
        LEDGER.skip("NOT_IN_RECV_TABLE against the client's own table",
                    f"no disassembler or no pinned client ({type(exc).__name__})")
    if table:
        n = sw.check_table_less(table, [int(k) for k in base])
        LEDGER.ok(n == len(TABLE_LESS),
                  f"the client's receive table is missing exactly those {n}",
                  "checked against the binary, so the literal cannot rot quietly")
        bad = dict(table)
        bad.pop(0x0011, None)
        try:
            sw.check_table_less(bad, [int(k) for k in base])
            ok = False
        except ValueError:
            ok = True
        LEDGER.ok(ok, "CONTROL: one extra missing entry is REFUSED",
                  "a constant nothing checks is a wish")

    # ---- 2. the stimulus stream is `sent`, never an s2c frame ---------------
    print("\n2. the readout can see its own stimulus")
    path = capture([send(10.0, 0x0100), frame(10.0, 0x0100),
                    send(10.4, 0x0101), frame(10.4, 0x0101),
                    c2s(6.5, 0x0009), c2s(10.5, 0x00C1)])
    sends, replies, undec, gone, _life, _map = sw.read_capture(path)
    LEDGER.ok(len(sends) == 2 and [o for _t, o, _b in sends] == [0x0100, 0x0101],
              "read_capture finds both sweep sends",
              f"{[hex(o) for _t, o, _b in sends]}")
    LEDGER.ok(naive_frame_reader(path) == 2 and len(sends) == 2,
              "CONTROL: this capture holds s2c frames too, so the pilot's reader would "
              "have found 2 as well -- the defect needs the shape below to show",
              "a capture where the server frames NOTHING back is the real case")
    quiet = capture([send(10.0, 0x0100), send(10.4, 0x0101), c2s(10.5, 0x00C1)])
    LEDGER.ok(naive_frame_reader(quiet) == 0 and len(sw.read_capture(quiet)[0]) == 2,
              "CONTROL: with no s2c frames the pilot's reader scores 0 stimuli where "
              "read_capture scores 2",
              "that is the run that printed a clean, wrong 'nothing happened'")

    # ---- 3. the control window -----------------------------------------------
    print("\n3. the control window is the run's own noise floor")
    # 0x00C1 arrives BEFORE the first send -- unprompted. It then arrives again after a
    # stimulus, where a floor of {0x0008,0x0009} alone would call it a reply.
    recs = [c2s(6.2, 0x00C1), c2s(7.0, 0x0009),
            send(10.0, 0x0100), c2s(10.1, 0x00C1),
            send(10.4, 0x0101), c2s(10.5, 0x0088)]
    r = sw.analyse(capture(recs), codec, control=4.0)
    LEDGER.ok(r["noise"] == [0x0009, 0x00C1],
              "the quiet window measures EVERYTHING unprompted, floor included",
              f"{[hex(o) for o in r['noise']]} -- which makes the window a check on "
              f"IDLE_FLOOR and not only a filter")
    LEDGER.ok(r["new_noise"] == [0x00C1] and r["floor_seen"] == [0x0009],
              "and it splits: 0x0009 corroborates the prior, 0x00C1 is new to this run",
              "the prior was measured on a PARKED client; the sweep's has just loaded a "
              "map, and reporting the split is what makes that visible")
    LEDGER.ok(r["table"][0x0100]["effect"] == "CONTESTED",
              "0x0100's 'reply' of 0x00C1 is CONTESTED, not REPLIED",
              "the client says 0x00C1 on its own in this map, so it is not a binding")
    LEDGER.ok(r["table"][0x0101]["effect"] == "REPLIED"
              and r["table"][0x0101]["replies"] == [0x0088],
              "0x0101's reply of 0x0088 stands: the control window did not produce it",
              "CONTROL -- the downgrade is opcode-specific, not a blanket suppression")
    LEDGER.ok(all(v["effect"] != "CONTESTED" or 0x0009 not in v["contested"]
                  for v in r["table"].values()),
              "an idle-floor opcode never CONTESTS anything",
              "0x0009 is in the control window, but contesting on it would flag every "
              "row in every run -- a filter that fires everywhere filters nothing")
    # No sends at all: nothing can be attributed, and that must be LOUD.
    r0 = sw.analyse(capture([c2s(6.2, 0x00C1)]), codec)
    LEDGER.ok(r0["noise"] is None and sw.print_run(r0) == 2,
              "a run with no sweep send attributes nothing and exits non-zero",
              "a green run that measured nothing is the failure this repo checks for")

    # ---- 4. the fence is PROOF OF LIFE, not the socket ----------------------
    print("\n4. the fence is the client's own traffic, not the connection")
    # THE 2026-08-12 SHAPE, to scale. A Guild Wars assert leaves the process ALIVE behind
    # a modal dialog: the message pump stops, the socket stays open. Measured that day --
    # last c2s at t=17.16, ConnectionResetError at t=48.77, and every opcode in the 31.6 s
    # between was scored SILENT. Seventy-eight confident measurements of a client that was
    # showing a crash dialog.
    recs = [send(10.0, 0x0100), c2s(10.1, 0x0088),
            send(10.4, 0x0101), send(10.8, 0x0102), send(11.2, 0x0103),
            {"kind": "error", "t": 42.0, "error": "ConnectionResetError(10054)"}]
    r = sw.analyse(capture(recs), codec, control=4.0)
    LEDGER.ok(list(r["table"]) == [0x0100],
              "only the opcode with a c2s message AFTER it is scored",
              "the client proved its pump was running past that send, and nothing else "
              "in this capture proves anything")
    LEDGER.ok(r["crash"] and r["crash"]["window"] == [0x0101, 0x0102, 0x0103],
              "the other three are the CRASH WINDOW, not results",
              f"{[hex(o) for o in r['crash']['window']]}")
    LEDGER.ok(r["crash"]["alive_until"] == 10.1
              and r["crash"]["socket_closed"] == 42.0,
              "and the report keeps both clocks apart: alive 10.1s, socket 42.0s",
              "the socket time is an UPPER BOUND on the crash and nothing more")
    LEDGER.ok(not any(v["effect"] == "DROPPED_CHANNEL" for v in r["table"].values()),
              "no single opcode is blamed for the run ending",
              "blaming the last one named 0x00A9 on 2026-08-12 when the client had "
              "asserted around 0x0012, seventy-eight sends earlier")
    socket_fenced = [op for t, op, _b in sw.read_capture(capture(recs))[0] if t < 42.0]
    LEDGER.ok(len(socket_fenced) == 4 and len(r["table"]) == 1,
              "CONTROL: a socket-fenced scorer scores 4 where 1 is provable",
              "which is the same defect as no fence at all, just later")
    # And the cost of the rule, stated as a check so it cannot be forgotten: a run that
    # ends CLEANLY still loses its tail, because the last sends have no heartbeat after.
    clean = [send(10.0, 0x0100), c2s(10.1, 0x0088), send(10.4, 0x0101)]
    rc = sw.analyse(capture(clean), codec, control=4.0)
    LEDGER.ok(list(rc["table"]) == [0x0100] and rc["unreached"] == [0x0101],
              "the tail of a CLEAN run is UNREACHED too, and retried",
              "about twelve opcodes per run at a 0.4s dwell against a 5s ping -- the "
              "price of never recording a measurement the client did not make")

    # ---- 5. undecodable is a reply, not a death -----------------------------
    print("\n5. UNDECODABLE is a reply, not a death")
    recs = [send(10.0, 0x0100),
            {"kind": "undecodable", "t": 10.1, "error": "Undecodable: GAME_CMSG 0x01FE",
             "unframeable_bytes": 12},
            send(10.4, 0x0101), c2s(10.5, 0x0009)]
    r = sw.analyse(capture(recs), codec, control=4.0)
    LEDGER.ok(r["table"][0x0100]["effect"] == "UNDECODABLE",
              "a c2s message we cannot frame scores against the opcode that drew it",
              "the client answered on an opcode our catalogue does not hold, which is "
              "the strongest evidence anything happened at all")
    LEDGER.ok(r["gone"] is None and r["crash"] is None,
              "and it did NOT end the run",
              "`undecodable` and `error` are different record kinds; folding them "
              "together loses exactly the result the sweep is for")
    LEDGER.ok(r["table"][0x0100]["effect"] == "UNDECODABLE"
              and r["alive_until"] == 10.5,
              "an unframeable c2s also counts as PROOF OF LIFE",
              "the client sent it, so its pump was running -- a fence that only "
              "believed messages it could decode would fence on our own catalogue")

    # ---- 6. the ledger, and what resume must not skip ------------------------
    print("\n6. the ledger records only what was measured")
    recs = [c2s(6.2, 0x00C1),
            send(10.0, 0x0100), c2s(10.1, 0x0088),
            send(10.4, 0x0101), c2s(10.5, 0x00C1),
            send(10.8, 0x0102),
            {"kind": "error", "t": 10.9, "error": "ConnectionResetError(10054)"},
            send(11.2, 0x0103)]
    r = sw.analyse(capture(recs), codec, control=4.0, planned=[0x0100, 0x0101, 0x0102,
                                                              0x0103, 0x0104])
    led, added, kept, refused = sw.record(r, {})
    LEDGER.ok(set(led) == {"0x0100", "0x0101"} and added == 2,
              "the two opcodes the client proved it survived are recorded",
              f"{sorted(led)}")
    LEDGER.ok("0x0102" not in led and "0x0103" not in led and "0x0104" not in led,
              "the crash window and the never-sent one are NOT",
              "a cursor advanced at send time would record all three and the sweep "
              "would walk past them for good")
    LEDGER.ok(r["unreached"] == [0x0102, 0x0103, 0x0104],
              "and all three come back UNREACHED so a resumed run tries them again",
              f"{[hex(o) for o in r['unreached']]}")
    LEDGER.ok(led["0x0100"]["effect"] == "REPLIED"
              and led["0x0101"]["effect"] == "CONTESTED",
              "each row carries the effect it was scored with",
              "and no row can carry a crash, because a crash belongs to a window")
    done = sw.done_opcodes(led)
    p2 = sw.plan(codec, done=done)
    LEDGER.ok(not ({0x0100, 0x0101} & {r["opcode"] for r in p2["rows"]}),
              "--resume drops both from the next plan", f"{p2['remaining']} left")
    LEDGER.ok(p2["remaining"] == p["remaining"] - 2,
              "and drops exactly two",
              f"{p['remaining']} -> {p2['remaining']}")
    # Bisection: --only overrides the ledger AND the table-less exclusion, because the
    # whole job is re-sending opcodes a previous run could not clear.
    p4 = sw.plan(codec, done=done, only={0x0100, 0x000B})
    LEDGER.ok({r["opcode"] for r in p4["rows"]} == {0x0100, 0x000B},
              "--only plans exactly what it names, ledger and table-less overridden",
              f"{sorted(hex(r['opcode']) for r in p4['rows'])} -- 0x0100 is already "
              f"recorded and 0x000B is table-less, and a bisection needs both")
    led2, added2, kept2, _ref2 = sw.record(r, led)
    LEDGER.ok(added2 == 0 and led2 == led,
              "CONTROL: recording the same run twice adds nothing",
              "the ledger keeps the FIRST measurement; a re-score cannot overwrite it")
    # A window of ONE is the only attributable crash, and recording it is what makes the
    # sweep converge: otherwise --resume replans the killer and every run dies in the
    # same place forever.
    one = [c2s(9.6, 0x0009), send(10.0, 0x0100), c2s(10.1, 0x0088), send(10.4, 0x0101),
           {"kind": "error", "t": 40.0, "error": "ConnectionResetError(10054)"}]
    r1 = sw.analyse(capture(one), codec, control=4.0)
    l1, a1, _k1, _r1 = sw.record(r1, {})
    LEDGER.ok(r1["crash"]["suspects"] == [0x0101]
              and l1["0x0101"]["effect"] == "ASSERTED",
              "a SUSPECT set of one is recorded as ASSERTED",
              "the strongest result the sweep produces -- this opcode stops the client")
    LEDGER.ok(0x0101 not in r1["unreached"],
              "and it is NOT also listed as UNREACHED",
              "one run reported 0x0017 as ASSERTED and as 'will be retried' in the same "
              "breath; a suspect is implicated, not unreached")
    LEDGER.ok(0x0101 not in {x["opcode"] for x in
                             sw.plan(codec, done=sw.done_opcodes(l1))["rows"]},
              "and --resume does not replan it",
              f"{a1} rows recorded; without this every run dies in the same place")
    two = one[:2] + [c2s(10.1, 0x0088), send(10.4, 0x0101), send(10.5, 0x0102),
                     {"kind": "error", "t": 40.0, "error": "ConnectionResetError(10054)"}]
    l2 = sw.record(sw.analyse(capture(two), codec, control=4.0), {})[0]
    LEDGER.ok("0x0101" not in l2 and "0x0102" not in l2,
              "CONTROL: a SUSPECT set of two records nothing at all",
              "one of them is innocent and the capture cannot say which; that is what "
              "--only with a dwell above the heartbeat is for")
    # THE CONTROL THAT MATTERS MOST HERE. Every run's tail lacks a beat behind it, so
    # "sends with no proof of life" is true of a healthy run too. A crash is silence that
    # OUTLASTS the socket -- measured at 31.6s, 120.8s and 30.1s on the three real runs.
    tidy = [c2s(9.6, 0x0009), send(10.0, 0x0100), c2s(10.1, 0x0088), send(10.4, 0x0101),
            {"kind": "error", "t": 10.6, "error": "ConnectionResetError(10054)"}]
    rt = sw.analyse(capture(tidy), codec, control=4.0)
    lt = sw.record(rt, {})[0]
    LEDGER.ok(rt["crash"] is None and "0x0101" not in lt,
              "CONTROL: a client killed while still answering is NOT a crash",
              "the harness kills a healthy client and its socket and its traffic stop "
              "together; without this the tail of EVERY clean run records as ASSERTED")
    # THE SAME BYTES, WITH A RECONNECT BEHIND THEM, ARE A RESULT. Measured 2026-08-12:
    # an opcode in 0x017E..0x019B closed the game channel at t=36.16 and the client
    # opened a new one 42 ms later, taking the whole plan again. The capture of a
    # deliberate drop and of a harness kill are identical to the byte, so the ONLY thing
    # that separates them is whether another connection followed -- which the caller
    # knows because the run produced a second capture, and `analyse` cannot know at all.
    rd = sw.analyse(capture(tidy), codec, control=4.0, reconnected=True)
    ld = sw.record(rd, {})[0]
    LEDGER.ok(rd["crash"] and rd["crash"]["suspects"] == [0x0101]
              and rd["crash"].get("dropped") is True,
              "the SAME capture with a reconnect behind it names 0x0101 -- DROPPED",
              "the client answered right up to the close, so the send left outstanding "
              "is far better constrained than a crash window")
    LEDGER.ok(ld.get("0x0101", {}).get("effect") == "DROPPED_CHANNEL",
              "and it records as DROPPED_CHANNEL rather than as a crash",
              "the client re-established and kept playing; calling that a crash is the "
              "pilot's mistake with more steps")
    LEDGER.ok(rt["crash"] is None and rd["crash"] is not None,
              "CONTROL: the two differ ONLY by `reconnected`",
              "same bytes, same fixture, one flag -- which is why the flag has to come "
              "from the report's capture list and never from the capture itself")
    blind = [send(10.0, 0x0100), c2s(10.1, 0x0088), send(10.4, 0x0101),
             {"kind": "error", "t": 40.0, "error": "ConnectionResetError(10054)"}]
    rb = sw.analyse(capture(blind), codec, control=4.0)
    LEDGER.ok(rb["crash"] and rb["crash"]["suspects"] == []
              and "0x0101" not in sw.record(rb, {})[0],
              "CONTROL: with no measured heartbeat there are NO suspects",
              "without a cadence there is no beat that should have arrived, so every "
              "send after the last reply is equally implicated and naming one is a guess")

    # ---- 6b. the map has to be quiet ----------------------------------------
    print("\n6b. a run in which the player died records NOTHING")
    # MEASURED on the first three real sweeps: the default world spawns a hostile that
    # kills the player at t=7.4 and revives at t=17.4, on a ~13 s cycle. Every send those
    # runs made landed between a kill and a revive, so every SILENT they produced meant
    # "silent on a corpse". Nobody noticed until the operator said the Hatcher was
    # attacking -- nothing in the capture was being read for it.
    peace = [c2s(9.6, 0x0009), send(10.0, 0x0100), c2s(10.1, 0x0088)]
    fought = peace + [{"kind": "sent", "t": 7.4, "opcode": 0x00F1,
                       "label": "KILL the player"}]
    rf = sw.analyse(capture(fought), codec, control=4.0)
    LEDGER.ok(len(rf["combat"]) == 1,
              "a 0x00F1 anywhere in the capture is detected",
              "by OPCODE, not by our own label prose, which a reword would retire")
    try:
        sw.record(rf, {})
        ok = False
    except ValueError:
        ok = True
    LEDGER.ok(ok, "and --record REFUSES the whole run",
              "a warning would be read once and the rows would go in anyway; the "
              "instruction is authsrv --no-enemy")
    # THE MAP MUST BE THE BASELINE ONE. Measured 2026-08-12: an opcode near 0x019B made
    # the client drop its channel, it reconnected 42 ms later, and our server handed the
    # fresh connection map 0 where every other row was measured in map 148. Twenty
    # opcodes were scored in a different world and pooled without a word. The operator
    # saw the map change on screen; nothing in the readout was looking.
    elsewhere = sw.analyse(capture(peace, map_id=0), codec, control=4.0)
    LEDGER.ok(elsewhere["map_id"] == 0, "the capture's own map is read back",
              "from the phase-0 MANIFEST_DONE the server logs")
    try:
        sw.record(elsewhere, {})
        ok = False
    except ValueError:
        ok = True
    LEDGER.ok(ok, "a connection in a different map records NOTHING",
              "an opcode's behaviour is a property of the world it was sent in")
    nameless = sw.analyse(capture(peace, map_id=None), codec, control=4.0)
    try:
        sw.record(nameless, {})
        ok2 = False
    except ValueError:
        ok2 = True
    LEDGER.ok(nameless["map_id"] is None and ok2,
              "CONTROL: a capture whose map cannot be NAMED is refused too",
              "the map comes from our own label prose -- the one witness there is -- so "
              "a reworded label must fail SAFE rather than assume the baseline")

    rp = sw.analyse(capture(peace), codec, control=4.0)
    LEDGER.ok(not rp["combat"] and sw.record(rp, {})[1] == 1,
              "CONTROL: the same run without the kill records normally",
              "the refusal is about the player dying, not about anything else in the "
              "capture")

    # ---- 7. the capture is named by the run's own report --------------------
    print("\n7. the capture is named by the report, never picked by name")
    rep = capture([])  # reuse the temp-file helper for a plain json file
    with open(rep, "w", encoding="utf-8") as fh:
        json.dump({"captures": [r"C:\v\captures\authsrv\a-c1.jsonl",
                                r"C:\v\captures\gamesrv\a-c1.jsonl"]}, fh)
    LEDGER.ok(sw.capture_from_report(rep).endswith("gamesrv\\a-c1.jsonl")
              or sw.capture_from_report(rep).endswith("gamesrv/a-c1.jsonl"),
              "the gamesrv capture is taken from the report's own list",
              "sorted(...)[-1] picked the wrong client on 2026-08-06; a capture is the "
              "same hazard")
    with open(rep, "w", encoding="utf-8") as fh:
        json.dump({"captures": [r"C:\v\captures\gamesrv\a-c1.jsonl",
                                r"C:\v\captures\gamesrv\a-c2.jsonl"]}, fh)
    try:
        sw.capture_from_report(rep)
        ok = False
    except ValueError:
        ok = True
    LEDGER.ok(ok, "CONTROL: two gamesrv captures in one report is REFUSED",
              "scoring one of two connections as though it were the run is worse than "
              "not scoring at all")

    # ---- 7b. the loop's stop conditions -------------------------------------
    print("\n7b. sweeploop stops rather than burning clients")
    import sweeploop as loop
    src = open(os.path.join(HERE, "sweeploop.py"), encoding="utf-8").read()
    LEDGER.ok(loop.decide([1, 2], 3, 0, False, 5)[0],
              "a round with work left and progress made continues", "")
    LEDGER.ok(not loop.decide([], 0, 0, False, 5)[0],
              "an empty plan stops -- the only good ending",
              "a probe that sends nothing prints 'complete' and measures nothing")
    LEDGER.ok(not loop.decide([1], 0, 2, False, 5)[0],
              "two rounds recording nothing stops",
              "the crash is not being localised, and a third round would burn another "
              "client to learn the same thing")
    LEDGER.ok(loop.decide([1], 0, 1, False, 5)[0],
              "CONTROL: ONE round recording nothing does NOT stop",
              "a single unlocalised crash is normal -- the suspects get bisected and the "
              "next round moves again; stopping at one would end most sweeps early")
    LEDGER.ok(not loop.decide([1], 5, 0, True, 5)[0],
              "a harness failure stops even with progress and work left",
              "that is a broken stack, not a sweep result, and looping hides it")
    LEDGER.ok(not loop.decide([1], 5, 0, False, 0)[0],
              "and the round ceiling stops an unattended run", "")
    LEDGER.ok(all(k in loop.GAME_ARGS for k in ("--no-enemy", "--ping-seconds",
                                                "--probe")),
              "every round passes --no-enemy, --ping-seconds and --probe",
              "leaving any to the operator is how a loop fails identically 17 times")
    # THE SYNTAX TREE, not a grep. The first version of this check searched the file text
    # for "assert_launch_safe" and went red on its own DOCSTRING, which names the gate to
    # explain why the module does not call it. test_cmsgnames.py has the same lesson from
    # the other side: a grep asserts formatting, not behaviour.
    import ast
    tree = ast.parse(src)
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                 for a in n.names}
    called = {n.func.attr if isinstance(n.func, ast.Attribute) else
              getattr(n.func, "id", None)
              for n in ast.walk(tree) if isinstance(n, ast.Call)}
    LEDGER.ok("cage" not in imported and "assert_launch_safe" not in called
              and "SESSION" in {t.id for n in ast.walk(tree)
                                if isinstance(n, ast.Assign) for t in n.targets
                                if isinstance(t, ast.Name)},
              "and it shells out to session.py rather than launching anything itself",
              "the cage gate stays in the one place test_cage.py covers; a second launch "
              "path is a second gate to get wrong. Asked of the SYNTAX TREE -- the grep "
              "version went red on the docstring that explains the rule")

    # THE PLANNER'S EXIT CODE, which the loop discarded until 2026-08-13. `load_plan()`
    # reads a file out of the vault and cannot tell this round's plan from the last one's,
    # so a planner that REFUSED left the loop holding a stale plan that still parsed like
    # a plan -- and it launched a real client against it and recorded what that client did
    # under this round's opcodes. All three refusals `smsgsweep --plan` has on 2026-08-13
    # exit 2 and write nothing: `--set` without `--only`, a `check_sets` disagreement, any
    # ValueError out of `plan()`. Nothing here enumerates them, deliberately -- the gate is
    # on the class, so a refusal added later is covered without editing this file.
    print("   and it refuses a plan this round did not produce")
    LEDGER.ok(loop.accept_plan(0, True)[0],
              "a planner that exited 0 and moved the plan file is accepted", "")
    refused, why_r = loop.accept_plan(2, False, "REFUSED: --set without --only ...")
    LEDGER.ok(not refused and "--set without --only" in why_r,
              "one that exited 2 without writing is refused, NAMING its stderr",
              "'exit 2' alone sends the operator back to the planner to ask what it "
              "already said")
    LEDGER.ok(loop.accept_plan(loop.PLAN_EMPTY_RC, True)[0],
              "CONTROL: exit 1 -- NOTHING TO SEND -- is NOT a refusal",
              "it WRITES an empty plan, and an empty plan is the sweep's only good "
              "ending; a blunt `rc != 0` stop would rename completion as breakage and "
              "the round after it would never be reached")
    LEDGER.ok(not loop.accept_plan(0, False)[0],
              "and one that exited 0 without moving the file is refused too",
              "the exit code alone misses a planner that dies after its own checks, or a "
              "future refusal that forgets to exit 2 -- 'it refused and the file did not "
              "move' is the shape of the whole failure")
    # BOTH of these are `moved=True` on purpose. The first version passed them False and
    # the `rc >= 2` sabotage went 0 red: with the file unmoved the freshness half refuses
    # anyway, so the check read green while measuring nothing about the rule it names.
    LEDGER.ok(not loop.accept_plan(-1073741819, True)[0],
              "CONTROL: a planner that DIED is refused even though the file moved",
              "Windows hands back the exception code (0xC0000005 here), which arrives "
              "NEGATIVE as a returncode, so an `rc >= 2` test accepts it -- and the file "
              "moving is not evidence the write finished, since `_write_json` truncates "
              "and then streams")
    LEDGER.ok(not loop.accept_plan(loop.PLAN_EMPTY_RC, False)[0],
              "CONTROL: and the exit-1 exemption does not bypass the freshness check",
              "the exemption is the loosening in this gate, so it gets its own control: "
              "'NOTHING TO SEND' is only believable from a planner that wrote one")

    # THE LOOP POINTED AT A PLANNER THAT REFUSES -- still no client and no vault:
    # `plan_path` is redirected at a temp file holding the PREVIOUS round's plan, which is
    # exactly what `load_plan()` would have handed back.
    tmp = tempfile.mkdtemp()
    stale = os.path.join(tmp, sw.PLAN_NAME)
    with open(stale, "w", encoding="utf-8") as fh:
        json.dump({"rows": [{"opcode": 0x0100}], "settle": 5.0, "control": 5.0,
                   "dwell": 0.8}, fh)

    def planner(body):
        path = os.path.join(tmp, f"planner{len(os.listdir(tmp))}.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    refuser = planner("import sys\n"
                      "sys.stderr.write('REFUSED: 0x0100 declares dword at index 2 and "
                      "0x0101 declares byte\\n')\n"
                      "sys.exit(2)\n")
    # TWO rows where the stale plan has one, so the file's SIZE moves as well as its
    # mtime: the positive control must not rest on the clock advancing between two writes
    # milliseconds apart, or it fails for a reason that has nothing to do with the gate.
    writer = planner("import json, sys\n"
                     "json.dump({'rows': [{'opcode': 512}, {'opcode': 513}], "
                     "'settle': 5.0, 'control': 5.0, 'dwell': 0.8}, "
                     f"open({stale!r}, 'w'))\n"
                     "sys.exit(0)\n")
    real_plan_path = sw.plan_path
    sw.plan_path = lambda: stale
    try:
        seen_arg = os.path.join(tmp, "seen.txt")
        got, why_p = loop.plan_round(seen_arg, 80, 0.8, sweep=refuser)
        would_have = (sw.load_plan() or {}).get("rows")
        fresh, why_f = loop.plan_round(seen_arg, 80, 0.8, sweep=writer)
    finally:
        sw.plan_path = real_plan_path
    LEDGER.ok(got is None and "0x0100 declares dword" in why_p
              and would_have == [{"opcode": 0x0100}],
              "the loop pointed at a refusing planner hands back NO plan",
              "and the check is a difference between two live answers: load_plan() "
              "answered from the previous round's file, in this same process, with the "
              "one row the old loop would have launched a client against")
    LEDGER.ok(fresh is not None and len(fresh["rows"]) == 2 and not why_f,
              "CONTROL: a planner that does write one is accepted",
              "a gate that refuses every plan protects nothing -- the loop never runs a "
              "round and the refusal is indistinguishable from the tool being broken")

    # THE ORDER, on the syntax tree. "It stops eventually" is not the fix: the whole point
    # is that the client must not go up, so the guard has to sit BEFORE the launch in the
    # round body. Both halves are sabotaged below, because a predicate that merely finds
    # two statements is satisfied by any file mentioning both.
    def guard_and_launch(body):
        def names(node):
            return {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}
        launch = next((i for i, st in enumerate(body) if "SESSION" in names(st)), None)
        guard = next((i for i, st in enumerate(body)
                      if isinstance(st, ast.If) and "plan" in names(st.test)
                      and any(isinstance(x, ast.Break) for x in ast.walk(st))), None)
        return guard, launch

    main_fn = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    round_body = next(n for n in ast.walk(main_fn) if isinstance(n, ast.For)).body
    guard_i, launch_i = guard_and_launch(round_body)
    LEDGER.ok(guard_i is not None and launch_i is not None and guard_i < launch_i,
              "the refusal is handled BEFORE the statement that launches a client",
              f"guard at statement {guard_i} of the round body, session.py at {launch_i}")
    deleted = [st for i, st in enumerate(round_body) if i != guard_i]
    LEDGER.ok(guard_and_launch(deleted)[0] is None,
              "CONTROL: the same predicate over that body with the guard DELETED fails",
              "which is the loop as it stood -- rc discarded, load_plan() trusted")
    moved_after = list(deleted)
    moved_after.insert(launch_i, round_body[guard_i])
    g2, l2 = guard_and_launch(moved_after)
    LEDGER.ok(g2 is not None and l2 is not None and not g2 < l2,
              "CONTROL: and with the guard moved one past the launch it fails too",
              "a client that goes up and is stopped afterwards has already measured the "
              "wrong opcodes; stopping is not the same as not launching")

    # ---- 8. the denominator, rebuilt from the tapes -------------------------
    print("\n8. the observed set is recomputed, not remembered")
    try:
        # NAMED, not the whole vault. The pin below is a fact about THESE THREE
        # captures; the sweep itself still uses every capture there is, because a
        # bigger denominator is a better answer to "what has ArenaNet never sent".
        # Unnamed, this reddened on 2026-08-17 when two live Factions captures took
        # the pool to 177 opcodes over 20 connections -- new evidence arriving as a
        # failure, which is the shape npcdefs.live_captures warned about.
        seen, conns = sw.observed_from_live(names=CANON_CAPTURES)
    except Exception as exc:
        LEDGER.skip("the observed set from the live tapes",
                    f"{type(exc).__name__}: {str(exc).splitlines()[0][:90]}")
        seen = conns = None
    if seen is not None:
        # THE CANON-12 FIGURES. If either moves, the sweep's "324 never-seen" moves with
        # it and the claim in every doc that quotes it is stale.
        LEDGER.ok(len(conns) == 12 and len(seen) == 155,
                  "155 GAME_SMSG opcodes over 12 live connections",
                  f"{len(seen)} over {len(conns)} -- the canon-12 corpus, rebuilt with "
                  f"tape.decode_all rather than read from a file somebody made once")
        # The defect that produced 52: filtering channels by port. ArenaNet serves the
        # GAME channel on 80 in 10 of the 12, so the port says nothing about the protocol
        # -- and the filter's failure direction is the bad one, marking real opcodes
        # never-seen... no: marking them SEEN would hide them. It EXCLUDED connections,
        # so the sweep would have tried 103 opcodes ArenaNet has already shown us.
        by_port = [c for c in conns if ":6112 " in c or c.endswith(":6112")]
        LEDGER.ok(len(by_port) == 2,
                  "CONTROL: only 2 of the 12 are on port 6112",
                  f"{len(by_port)} -- a `:6112` filter cut the corpus to 52 opcodes and "
                  f"reported that number without complaint")
        p3 = sw.plan(codec, seen=seen)
        LEDGER.ok(p3["remaining"] == 324,
                  "and the plan that excludes them is the stated 324",
                  f"{p3['remaining']} -- 487 catalogued, minus 153 observed that are in "
                  f"the receive table, minus the 10 with no entry")

    # ---- 9. the payload regime: one row per EXPERIMENT ----------------------
    print("\n9. a row is an opcode AND the payload it was sent with")
    # 9a. THE AXIS IS THE PAYLOAD, NOT THE FLAG. This is the whole design and it is the
    # first thing checked, because getting it from the flag is the obvious wrong answer:
    # `--encstring` sends BYTE-IDENTICAL bytes to every opcode with no string16 field, so
    # 400 of the 487 would have gained a duplicate row describing one experiment.
    s16 = {int(k) for k in codec.channels["GAME_SMSG"]["messages"]
           if any(f["type"] == "string16"
                  for f in codec.fields_for("GAME_SMSG", int(k)))}
    LEDGER.ok(len(s16) == WITH_STRING16,
              f"{WITH_STRING16} of the 487 catalogued opcodes carry a string16 field",
              f"{len(s16)} -- the candidates; the other {487 - len(s16)} go out "
              f"identically whatever the flag says")
    moved = {o for o in s16
             if codec.encode("GAME_SMSG", o, list(sw.degenerate(codec, o,
                                                                encstring=OURS)))
             != codec.encode("GAME_SMSG", o, list(sw.degenerate(codec, o)))}
    LEDGER.ok(len(moved) == FILLABLE and s16 - moved == NESTED_STRING16,
              f"but only {FILLABLE} ENCODE differently -- 0x019D's string16 is behind a "
              f"nested_struct",
              f"{sorted(hex(o) for o in s16 - moved)} -- `degenerate` stops at a "
              f"nested_struct because the tail after it is the element layout, so the "
              f"string is never reached and an --encstring run of 0x019D is an ALLZERO "
              f"experiment. The field-scan version of planned_regime called it encstring "
              f"and this check is what found it")
    LEDGER.ok({o for o in s16 if sw.fills_a_string(codec, o)} == moved,
              "and `fills_a_string` agrees with the encoder, opcode for opcode",
              "the structural walk is what the planner uses and the encoder is the "
              "artifact; a claim only one of them makes is the kind that reached the "
              "ledger last time")
    # 9b. THE PREDICTOR AND THE READER MUST NOT DRIFT. `planned_regime` says what a plan
    # will send; `regime_of_payload` reads what a capture DID send. They are separate
    # code paths and the ledger's whole meaning rests on them agreeing, so agreement is
    # measured over every encodable opcode, in both regimes -- 974 comparisons.
    good, _refused = sw.encodable(codec)
    agree, disagree = 0, []
    for opcode in sorted(good):
        for enc in (None, OURS):
            body = codec.encode("GAME_SMSG", opcode,
                                list(sw.degenerate(codec, opcode, encstring=enc)))
            want = sw.planned_regime(codec, opcode, encstring=enc)
            got = sw.regime_of_payload(codec, opcode, body)
            if want == got:
                agree += 1
            else:
                disagree.append((hex(opcode), enc, want, got))
    LEDGER.ok(not disagree and agree == 2 * len(good),
              f"the plan's predicted regime equals the wire's, {agree} of {2 * len(good)}",
              f"{disagree[:4]} -- two independent code paths over every encodable "
              f"opcode in both regimes, which is what stops the ledger's key drifting "
              f"away from what the capture says")
    LEDGER.ok(sw.planned_regime(codec, 0x0100, encstring=OURS) == sw.ALLZERO
              and sw.planned_regime(codec, 0x0102, encstring=OURS) == sw.ENCSTRING,
              "CONTROL: under --encstring 0x0100 is still an ALLZERO experiment",
              "it has no string16 field, so the flag changed nothing about what went "
              "out; 0x0102 has one and is a genuinely different send")
    # A --set run is a THIRD experiment, and must not be filed as either of the two.
    set_bytes = codec.encode("GAME_SMSG", 0x0100,
                             sw.apply_set(sw.degenerate(codec, 0x0100), {1: 1}))
    LEDGER.ok(sw.regime_of_payload(codec, 0x0100, set_bytes) == sw.OTHER
              and sw.planned_regime(codec, 0x0100, sets={1: 1}) == sw.OTHER,
              "a --set payload reads OTHER from both sides, never ALLZERO",
              "filing a one-field-changed run under the all-zero key would retire the "
              "degenerate measurement with a different experiment's answer")
    LEDGER.ok(sw.regime_of_payload(codec, 0x0102, None) == sw.UNKNOWN,
              "and a send with no plaintext is UNKNOWN, not assumed",
              "a capture from a recorder that logged no payload cannot say which "
              "experiment it was, and `record` refuses rather than guessing")

    # 9c. THE KEY. ALLZERO keeps the bare historical key; everything else is suffixed.
    LEDGER.ok(sw.ledger_key(0x0102, sw.ALLZERO) == "0x0102"
              and sw.ledger_key(0x0102, sw.ENCSTRING) == "0x0102@encstring"
              and sw.ledger_key(0x0102, sw.ALLZERO)
              != sw.ledger_key(0x0102, sw.ENCSTRING),
              "one opcode, two regimes, TWO keys -- and allzero keeps the bare one",
              "so 334 historical rows keep their names and anything that only walks "
              "rows keeps working; only a second regime introduces a new shape")
    LEDGER.ok(sw.parse_key("0x0102@encstring") == (0x0102, "encstring")
              and sw.parse_key("0x0102") == (0x0102, None),
              "and parse_key round-trips it, returning None for a BARE key",
              "None rather than 'allzero' -- a bare key is a key that never said, and "
              "reading it as though it had is the defect this section exists for")
    try:
        sw.ledger_key(0x0102, "whatever")
        ok = False
    except ValueError:
        ok = True
    LEDGER.ok(ok, "CONTROL: an unrecognised regime is REFUSED, not keyed",
              "a typo'd regime would key a row that no query ever finds again")

    # 9d. A ROW MEASURED UNDER ONE REGIME DOES NOT SATISFY A QUERY FOR THE OTHER.
    allzero_run = sw.analyse(capture(
        [c2s(6.2, 0x00C1), send(10.0, 0x0102), c2s(10.1, 0x0088),
         send(10.4, 0x0100), c2s(10.5, 0x0088)]), codec, control=4.0)
    enc_run = sw.analyse(capture(
        [c2s(6.2, 0x00C1), send(10.0, 0x0102, encstring=OURS), c2s(10.1, 0x0009),
         send(10.4, 0x0100, encstring=OURS), c2s(10.5, 0x0009)]), codec, control=4.0)
    LEDGER.ok(allzero_run["table"][0x0102]["regime"] == sw.ALLZERO
              and enc_run["table"][0x0102]["regime"] == sw.ENCSTRING
              and enc_run["table"][0x0100]["regime"] == sw.ALLZERO,
              "analyse reads each row's regime out of the capture's own bytes",
              "including that 0x0100 in the --encstring run is STILL an allzero "
              "measurement, which no flag written in a report could have told it")
    led9 = sw.record(allzero_run, {})[0]
    LEDGER.ok(sw.measured_under(codec, led9, encstring=None) == {0x0100, 0x0102}
              and sw.measured_under(codec, led9, encstring=OURS) == {0x0100},
              "an allzero row answers the allzero query and NOT the encstring one",
              "0x0100 answers both because its bytes are the same either way -- which "
              "is the point of reading the regime off the payload")
    p9 = sw.plan(codec, done=sw.measured_under(codec, led9, encstring=OURS),
                 encstring=OURS)
    LEDGER.ok(0x0102 in {r["opcode"] for r in p9["rows"]}
              and 0x0100 not in {r["opcode"] for r in p9["rows"]},
              "so --resume --encstring replans 0x0102 and still skips 0x0100",
              "the version that asked done_opcodes() instead skipped both and printed "
              "'nothing left' for a sweep that had never sent a string")
    led9b, added9b, kept9b, _r9b = sw.record(enc_run, led9)
    LEDGER.ok(added9b == 1 and "0x0102@encstring" in led9b
              and led9b["0x0102"]["effect"] != led9b["0x0102@encstring"]["effect"],
              "and the encstring run lands BESIDE the allzero row, not over it",
              f"{sorted(led9b)} -- 0x0102 is REPLIED on an empty payload and SILENT on "
              f"a filled one, which is exactly the shape 0x0033/0x009E/0x00B9/0x00C0 "
              f"had and which the old key could not hold")
    LEDGER.ok(kept9b == ["0x0100"],
              "CONTROL: 0x0100 collides and is reported KEPT rather than dropped quietly",
              "its bytes really were the same experiment; `recorded 0` with no second "
              "line is what made nine runs look like they had measured nothing")

    # 9e. THE SABOTAGE. Revert the key to the regime-less one -- the code as it stood --
    # and require the two experiments to COLLIDE. This is the check that makes the
    # regime load-bearing rather than decorative: without it, every assertion above is
    # about a field nothing depends on.
    def record_v1(result, ledger):
        """`record` AS IT WAS: keyed by opcode alone, first-write-wins, silent."""
        out, added = dict(ledger), 0
        for opcode, row in result["table"].items():
            if row["effect"] not in sw.MEASURED:
                continue
            key = f"0x{opcode:04X}"
            if key in out:
                continue
            out[key] = {"effect": row["effect"], "capture": result["capture"]}
            added += 1
        return out, added

    v1a, _ = record_v1(allzero_run, {})
    v1b, v1_added = record_v1(enc_run, v1a)
    LEDGER.ok(v1_added == 0 and set(v1b) == set(v1a)
              and v1b["0x0102"]["effect"] == v1a["0x0102"]["effect"],
              "SABOTAGE: the regime-less key records 0 and LOSES the encstring result",
              f"`recorded {v1_added}` -- the same line nine runs printed on 2026-08-12 "
              f"while four opcodes stayed filed as crashing. The two answers differ: "
              f"{len(led9b)} rows with the regime in the key, {len(v1b)} without")
    LEDGER.ok(len(led9b) == len(v1b) + 1
              and 0x0102 in {sw.parse_key(k)[0] for k in led9b
                             if sw.parse_key(k)[1] == "encstring"},
              "and the difference is exactly the experiment the old key could not name",
              "two live answers, not an assertion about the code -- test_codescan §8's "
              "pattern, because a sabotage nobody ran is a sentence in a comment")
    # THE CRASH PATH IS THE ONE THAT ACTUALLY BIT, so it gets its own collision. The four
    # cleared opcodes are ASSERTED rows written by the crash branch, not by the table.
    crash_all0 = sw.analyse(capture(
        [c2s(9.6, 0x0009), send(10.0, 0x0100), c2s(10.1, 0x0088),
         send(10.4, 0x0102),
         {"kind": "error", "t": 40.0, "error": "ConnectionResetError(10054)"}]),
        codec, control=4.0)
    LEDGER.ok(crash_all0["crash"]["suspects"] == [0x0102]
              and crash_all0["crash"]["regime"] == sw.ALLZERO,
              "a crash suspect carries the regime of the payload that produced it",
              "the ASSERTED rows this whole item is about were written by this branch, "
              "so a regime on the table rows alone would have fixed nothing")
    ledc = sw.record(crash_all0, {})[0]
    ledc2, addc, keptc, _rc = sw.record(enc_run, ledc)
    LEDGER.ok(ledc["0x0102"]["effect"] == "ASSERTED"
              and addc == 1 and ledc2["0x0102@encstring"]["effect"] == "SILENT",
              "and the encstring SILENT lands beside the allzero ASSERTED",
              "0x0033, 0x009E, 0x00B9 and 0x00C0 in one sentence: the ASSERTED row is "
              "not wrong, it is a measurement of a different payload")
    LEDGER.ok(record_v1(enc_run, ledc)[1] == 0
              and record_v1(enc_run, ledc)[0]["0x0102"]["effect"] == "ASSERTED",
              "SABOTAGE on the crash path: the old key keeps ASSERTED and drops SILENT",
              "which is the ledger as it stood at the start of 2026-08-13")

    # 9f. FIRST-WRITE-WINS IS THE POLICY AND IT IS PINNED, so nobody again believes that
    # re-running --record will correct a row. It is the RIGHT policy once the key names an
    # experiment; what was wrong was the silence.
    again, added_again, kept_again, _ra = sw.record(enc_run, led9b)
    LEDGER.ok(added_again == 0 and again == led9b
              and sorted(kept_again) == ["0x0100", "0x0102@encstring"],
              "recording the same experiment twice adds nothing and NAMES what it kept",
              f"{sorted(kept_again)} -- the ledger keeps the FIRST measurement, and a "
              f"re-score can never overwrite it. `--record` prints this list now; the "
              f"version that printed only `recorded 0` is why item 5 existed at all")

    # 9g. AN OLD-FORMAT LEDGER MUST STILL LOAD. There are 334 measured rows in the vault
    # and they cost a day of client launches; a format change that could not read them
    # would be far worse than the defect it fixes.
    old = {"0x0033": {"effect": "ASSERTED", "replies": [], "contested": [],
                      "undecodable": [], "capture": "a.jsonl", "why": "an assert"},
           "0x0100": {"effect": "SILENT", "replies": [], "contested": [],
                      "undecodable": [], "capture": "a.jsonl"}}
    LEDGER.ok(sw.done_opcodes(old) == {0x0033, 0x0100}
              and sw.regime_of_row("0x0033", old["0x0033"]) == sw.UNKNOWN
              and sorted(sw.unmigrated(old)) == ["0x0033", "0x0100"],
              "an unmigrated row loads, is readable, and is named as UNMIGRATED",
              "regime UNKNOWN rather than 'allzero': almost all of them are all-zero "
              "measurements and 'almost all' is not one")
    LEDGER.ok(sw.print_report(old, codec) == 0,
              "and --report prints it without raising",
              "the reporting path is what an operator reaches for first; a migration "
              "that broke it would be found by a person and not by a test")
    resolve = {0x0033: sw.ENCSTRING, 0x0100: sw.ALLZERO}
    new, changes = sw.migrate(old, lambda op, row: resolve[op])
    LEDGER.ok(len(new) == len(old) == 2 and len(changes) == 2
              and set(new) == {"0x0033@encstring", "0x0100"},
              "migrate gives every row an explicit regime and LOSES NONE",
              f"{sorted(new)} -- 334 rows in the real ledger, and the migration is a "
              f"rewrite of all of them, so 'nothing is dropped' is the first claim")
    LEDGER.ok(all(r["regime"] in sw.REGIMES for r in new.values())
              and new["0x0033@encstring"]["why"] == "an assert"
              and new["0x0100"]["effect"] == "SILENT",
              "and it carries every other field through untouched",
              "the row's evidence -- its capture, its assert text -- is the part that "
              "cannot be re-derived if it is lost")
    unk, _ch = sw.migrate(old, lambda op, row: None)
    LEDGER.ok(set(unk) == {"0x0033@unknown", "0x0100@unknown"}
              and all(r["regime"] == sw.UNKNOWN for r in unk.values()),
              "a row whose regime cannot be derived is written `unknown`, EXPLICITLY",
              "and gets its own key, so it can never silently satisfy a query for the "
              "all-zero experiment it probably but unprovably was")
    LEDGER.ok(sw.migrate(new, lambda op, row: sw.ALLZERO)[0] == new,
              "CONTROL: migrating an already-migrated ledger is a no-op",
              "rows that carry a regime keep it; the resolver is not consulted, so a "
              "second --migrate cannot re-key what the first one settled")
    try:
        sw.migrate({"0x0033": {"effect": "SILENT", "regime": sw.ALLZERO,
                               "capture": "a"},
                    "0x0033@encstring": {"effect": "SILENT", "capture": "b"}},
                   lambda op, row: sw.ALLZERO)
        ok = False
    except ValueError:
        ok = True
    LEDGER.ok(ok, "CONTROL: two rows resolving to ONE key is REFUSED, not merged",
              "silently letting one win is how a measurement disappears, and the whole "
              "point of the migration is that none does")

    # 9h. THE COST OF THE SUFFIX, STATED AS A CHECK RATHER THAN A HOPE. A reader that
    # turns a key straight into an opcode breaks on a suffixed one. That is deliberate --
    # such a reader would otherwise pool two regimes into one number -- but it is a real
    # break and it should be this file that says so.
    try:
        {int(k, 16) for k in led9b}
        loud = False
    except ValueError:
        loud = True
    LEDGER.ok(loud and sw.done_opcodes(led9b) == {0x0100, 0x0102},
              "int(key, 16) RAISES on a migrated ledger where parse_key does not",
              "the suffix is a loud break by design: a reader that cannot see the "
              "regime is a reader that would have conflated the two experiments")
    LEDGER.ok(all(isinstance(r.get("effect"), str) for r in led9b.values()),
              "CONTROL: every row is still a plain row with an `effect`",
              "no marker object and no nesting at the top level, so the external "
              "scripts that scan the ledger for SILENT rows keep working")

    # 9i. RECORD REFUSES WHAT IT CANNOT FILE. A row whose regime is unknown must not be
    # keyed at all: an `@unknown` key would block the real measurement for good.
    blind_run = sw.analyse(capture(
        [c2s(6.2, 0x00C1), send(10.0, 0x0102, plain=None), c2s(10.1, 0x0088)]),
        codec, control=4.0)
    lb, ab, _kb, rb9 = sw.record(blind_run, {})
    LEDGER.ok(blind_run["table"][0x0102]["regime"] == sw.UNKNOWN
              and ab == 0 and lb == {} and [o for o, _w in rb9] == [0x0102],
              "a send with no plaintext is REFUSED and reported, not filed",
              "the same shape as UNREACHED: kept out of the ledger so a later run can "
              "still measure it, and printed so the operator knows it happened")
    mixed = sw.analyse(capture(
        [c2s(6.2, 0x00C1), send(10.0, 0x0102), c2s(10.1, 0x0088),
         send(10.4, 0x0102, encstring=OURS), c2s(10.5, 0x0088)]), codec, control=4.0)
    lm, am, _km, rm = sw.record(mixed, {})
    LEDGER.ok(mixed["table"][0x0102]["regime"] == sw.UNKNOWN
              and mixed["table"][0x0102]["regime_mixed"] == [sw.ALLZERO, sw.ENCSTRING]
              and am == 0 and lm == {} and [o for o, _w in rm] == [0x0102],
              "and one opcode sent under TWO regimes in one connection is refused too",
              "its score pools two experiments and there is no honest way to split them "
              "afterwards, so the row is named rather than averaged")

    # 9j. THE WRITE. The ledger is a live vault artifact that other sessions read while a
    # sweep is running, so the write is all-or-nothing and refuses a file that moved.
    tmpd = tempfile.mkdtemp()
    lp = os.path.join(tmpd, "led.json")
    sw._write_json(lp, {"0x0100": {"effect": "SILENT", "regime": sw.ALLZERO}},
                   expect=None)
    tok = sw.stamp(lp)
    with open(lp, encoding="utf-8") as fh:
        back = json.load(fh)
    LEDGER.ok(back["0x0100"]["effect"] == "SILENT" and tok is not None
              and not [f for f in os.listdir(tmpd) if f.startswith(".tmp-")],
              "an atomic write lands the whole file and leaves no temp behind",
              "os.replace is atomic on Windows too, so a concurrent reader sees the old "
              "file or the new one and never a truncated one")
    sw._write_json(lp, {"0x0101": {"effect": "SILENT", "regime": sw.ALLZERO}},
                   expect=tok)
    LEDGER.ok(json.load(open(lp, encoding="utf-8")) == {"0x0101": {"effect": "SILENT",
                                                                  "regime": sw.ALLZERO}},
              "CONTROL: a write with the CURRENT stamp is allowed",
              "a guard that refuses every write protects nothing, because the tool "
              "stops being used")
    try:
        sw._write_json(lp, {"0x0102": {}}, expect=tok)
        ok = False
    except ValueError:
        ok = True
    LEDGER.ok(ok and "0x0101" in json.load(open(lp, encoding="utf-8")),
              "and a write against a STALE stamp is refused, leaving the file intact",
              "another session recording between our read and our write would otherwise "
              "have its row overwritten by our 334 -- silently, with no second copy")

    # ---- 10. the probe puts the plan's overrides ON THE WIRE ------------------
    print("\n10. --set reaches the wire")
    # Every check above this line runs inside smsgsweep: plan() resolves the overrides,
    # apply_set applies them, encodable() encodes them. The consumer is somewhere else
    # entirely -- probes._smsgsweep_steps builds the Steps the server actually sends --
    # and it read the overrides off the PLAN after plan() moved them per ROW (c7c7da6).
    # So the module agreed with itself perfectly while --set sent the degenerate payload.
    # This section is the only place the two halves are made to meet.
    try:
        import probes as pr
    except Exception as exc:                        # pragma: no cover - import guard
        LEDGER.skip("the probe's step builder against the plan",
                    f"probes did not import: {type(exc).__name__}: "
                    f"{str(exc).splitlines()[0][:80]}")
        pr = None
    if pr is not None:
        # 0x0017 because it is the experiment apply_set's own docstring describes: its
        # handler tests the FIFTH field against zero and skips a resource load when it is
        # non-zero, so `--set 5=1` is the one payload that reaches the other branch.
        OP_A, OP_B = 0x0017, 0x000F
        base_a, base_b = sw.degenerate(codec, OP_A), sw.degenerate(codec, OP_B)
        LEDGER.ok(base_a == [0, 0, 0, 0, 0] and base_b == [0, 0, 0],
                  "FIXTURE: both degenerate payloads are all-zero",
                  f"{base_a} / {base_b} -- an override is only a visible difference if "
                  f"the field it lands in was 0, so a non-zero here would make every "
                  f"check below unable to fail")
        p9 = sw.plan(codec, only={OP_A}, sets={OP_A: {5: 1}})
        LEDGER.ok(p9["rows"][0].get("set") == {"5": 1} and "set" not in p9,
                  "the plan writes overrides PER ROW and carries no top-level `set`",
                  f"row={p9['rows'][0].get('set')} top-level={'set' in p9} -- this is the "
                  f"level the step builder has to read, and the level it did not")
        # A LIST, never got[0]: steps_for returns [] when the builder raises, and indexing
        # it here would kill the run before the verdict banner -- which is how the first
        # version of this section reported a caught defect as a bare traceback.
        got = [s.values for s in steps_for(pr, sw, p9)]
        LEDGER.ok(got == [[0, 0, 0, 0, 1]],
                  "and the probe SENDS it: --set 5=1 puts a 1 in field 5",
                  f"{got} -- the 1-based index has to land on the "
                  f"fifth value and leave the other four alone")
        # THE DEFECT, reproduced inline out of the three lines it used to be, so the check
        # above is a difference between two live answers rather than a number this file
        # asked the code to confirm about itself.
        broken = sw.apply_set(sw.degenerate(codec, OP_A),
                              {int(k): v for k, v in (p9.get("set") or {}).items()})
        LEDGER.ok(broken == base_a and [broken] != got,
                  "CONTROL: the old plan-level lookup yields the DEGENERATE payload",
                  f"{broken} -- `p.get('set')` reads {{}} from every plan since c7c7da6 moved "
                  f"the overrides per row, so apply_set returned its input untouched "
                  f"and the run measured all-zero while the report said otherwise")
        # A fix that reads rows[0]["set"] for every row passes a one-row plan and is wrong
        # the moment a sweep sets a field on two opcodes at once.
        p9b = sw.plan(codec, only={OP_A, OP_B}, sets={OP_A: {5: 1}, OP_B: {2: 7}})
        vals = {s.opcode: s.values for s in steps_for(pr, sw, p9b)}
        LEDGER.ok(vals == {OP_A: [0, 0, 0, 0, 1], OP_B: [0, 7, 0]},
                  "each row gets ITS OWN override, not the first row's",
                  f"{ {hex(k): v for k, v in vals.items()} } -- --set is qualified per "
                  f"opcode (sets_for), so one row's dict must never reach another's step")
        # A row reaches the builder in two override-free shapes and it must not start
        # raising on either: the ordinary 324-opcode sweep writes NO `set` key at all,
        # while --only with no --set writes an EMPTY one. Both must still send degenerate.
        p9c = sw.plan(codec, limit=2)
        LEDGER.ok(all("set" not in r for r in p9c["rows"])
                  and ([s.values for s in steps_for(pr, sw, p9c)]
                       == [sw.degenerate(codec, r["opcode"]) for r in p9c["rows"]]),
                  "CONTROL: the ordinary sweep has no `set` key and is unaffected",
                  f"rows {[hex(r['opcode']) for r in p9c['rows']]} -- 324 of the sweep's "
                  f"324 rows look like this, so a builder that required the key would "
                  f"break every run that is not an experiment")
        p9d = sw.plan(codec, only={OP_A})
        LEDGER.ok(p9d["rows"][0].get("set") == {}
                  and [s.values for s in steps_for(pr, sw, p9d)] == [base_a],
                  "CONTROL: --only with no --set writes an EMPTY override and sends zeros",
                  f"set={p9d['rows'][0].get('set')} -- the other override-free shape, and "
                  f"the one a bisection run produces")
        # The plan reaches the probe as JSON, so its keys are STRINGS -- which is why the
        # builder casts them. steps_for() goes through a real file for exactly this
        # reason: handed an in-memory dict with int keys, a builder that dropped the
        # int(k) cast would pass every check above and raise TypeError inside apply_set
        # on the first real run.
        LEDGER.ok(list((json.loads(json.dumps(p9))["rows"][0]["set"] or {})) == ["5"],
                  "and the override survives JSON as a STRING key",
                  "the builder casts with int(k); a check that skipped the file would "
                  "not notice if it stopped")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
