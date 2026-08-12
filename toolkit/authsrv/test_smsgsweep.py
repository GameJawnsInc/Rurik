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

AND ONE THAT IS NOT ABOUT SCORING. `degenerate` must read the CODEC, never
`schema/messages.json` -- `overrides.json` changes the field list of exactly three
opcodes, so a builder reading the base catalogue gets the arity wrong for those three
and only those three. Section 0 measures both and requires the difference to be exactly
{140, 146, 421}: a check that names the three is a check that can fail if a fourth is
added, which is the point.
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

# Floor 64, measured from a green run on 2026-08-12. Sections 0 and 2-7 need no vault, no
# socket and no client -- 32 checks -- because a scoring defect is not a property of any
# one capture. Two sections do need more and both declare their skips: section 1's
# cross-check of NOT_IN_RECV_TABLE against the client's own receive table wants capstone
# and the pinned client (2), and section 8's rebuild of the observed set wants the live
# captures (3). A machine missing either lands under the floor and goes RED, deliberately,
# the way test_mapexport treats a vault-less run: those two sections are the ones that
# pin the sweep's DENOMINATOR and the ten opcodes that tear the game channel down, and a
# plan built on a constant nothing confirmed is exactly the wish this repo keeps refusing.
LEDGER = checks.Ledger("smsgsweep: the loopback sweep's readout", floor=64)

# MEASURED 2026-08-12: the opcodes whose field list `overrides.json` changes. Written as
# literals rather than recomputed from the module under test.
OVERRIDDEN = {140, 146, 421}
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


def send(t, opcode):
    return {"kind": "sent", "t": t, "opcode": opcode,
            "label": f"PROBE[smsgsweep] [1/9] 0x{opcode:04X} (BODY)"}


def c2s(t, opcode):
    return {"kind": "decoded", "t": t, "opcode": opcode, "name": "?"}


def frame(t, opcode):
    """An s2c frame -- what the pilot's analyser mistook for a stimulus."""
    return {"kind": "frame", "t": t, "opcode": opcode, "direction": "s2c", "n": 6}


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
    LEDGER.ok(len(sends) == 2 and [o for _, o in sends] == [0x0100, 0x0101],
              "read_capture finds both sweep sends", f"{[hex(o) for _, o in sends]}")
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
    socket_fenced = [op for t, op in sw.read_capture(capture(recs))[0] if t < 42.0]
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
    led, added = sw.record(r, {})
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
    led2, added2 = sw.record(r, led)
    LEDGER.ok(added2 == 0 and led2 == led,
              "CONTROL: recording the same run twice adds nothing",
              "the ledger keeps the FIRST measurement; a re-score cannot overwrite it")
    # A window of ONE is the only attributable crash, and recording it is what makes the
    # sweep converge: otherwise --resume replans the killer and every run dies in the
    # same place forever.
    one = [c2s(9.6, 0x0009), send(10.0, 0x0100), c2s(10.1, 0x0088), send(10.4, 0x0101),
           {"kind": "error", "t": 40.0, "error": "ConnectionResetError(10054)"}]
    r1 = sw.analyse(capture(one), codec, control=4.0)
    l1, a1 = sw.record(r1, {})
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
    l2, _ = sw.record(sw.analyse(capture(two), codec, control=4.0), {})
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
    lt, _ = sw.record(rt, {})
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
    ld, _ = sw.record(rd, {})
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

    # ---- 8. the denominator, rebuilt from the tapes -------------------------
    print("\n8. the observed set is recomputed, not remembered")
    try:
        seen, conns = sw.observed_from_live()
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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
