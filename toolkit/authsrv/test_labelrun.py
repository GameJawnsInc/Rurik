"""Prove the labelled run attributes a message to the RIGHT human action, or refuses to.

`labelrun.py` exists to turn client traffic into named actions, and a naming tool that
misattributes is worse than none: a wrong name enters `schema/overrides.json` and every
later reader inherits it as fact. The load-bearing properties are therefore about
BOUNDARIES, not about the script.

  * A message belongs to the step whose window contains it, and windows are
    half-open [mark, next_mark) so no message lands in two steps and none is dropped
    between them.
  * Traffic that arrived BEFORE the first step -- the tape, the instance load -- is
    reported separately and never folded into step 1, which would inflate the first
    action by however long the load took.
  * The two idle steps are CONTROLS. Traffic in a window the operator was told to sit
    out means the marks and the messages disagree, and the run must be thrown away
    rather than read. Section 4 breaks that on purpose to prove it can go red.

The keepalive is counted, never silently dropped: it has nothing to do with what the
operator is doing, so it means nothing about the window it lands in. A filter you
cannot see is a filter you cannot check -- and counting it rather than dropping it is
what showed that it stops entirely once the server goes quiet
(studies/cmsg/FINDINGS.md section 3).

standard library only.

    python toolkit/authsrv/test_labelrun.py
"""
import json
import os
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import labelrun  # noqa: E402

LEDGER = checks.Ledger("labelrun", floor=30)


class FakeRec:
    """Records like authsrv's Recorder but into a list, and stamps t from a clock."""

    def __init__(self):
        self.events = []
        self.t = 0.0

    def event(self, kind, **kw):
        kw["kind"] = kind
        kw["t"] = self.t
        self.events.append(kw)


def msg(t, opcode):
    return {"kind": "decoded", "t": t, "opcode": opcode, "name": "?"}


def write_capture(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def main():
    # ---- 1. the script itself is well formed -----------------------------------
    print("1. the script is well formed")
    keys = [s.key for s in labelrun.STEPS]
    LEDGER.ok(len(keys) == len(set(keys)),
              "every step key is unique -- they name columns in the report",
              f"{len(keys)} steps")
    LEDGER.ok(all(s.seconds > 0 for s in labelrun.STEPS),
              "every step has a positive duration")
    LEDGER.ok(all(s.expect in (labelrun.SILENCE, labelrun.TRAFFIC)
                  for s in labelrun.STEPS),
              "every step states a prediction, per the house rule",
              "a step with no stated expectation can be rationalised into agreeing "
              "with whatever happened")
    silent = [s.key for s in labelrun.STEPS if s.expect == labelrun.SILENCE]
    LEDGER.ok(len(silent) >= 2 and "idle_a" in silent and "idle_b" in silent,
              "there are idle CONTROLS at both ends, not just the start",
              f"silent-predicted: {', '.join(silent)}")
    LEDGER.ok(labelrun.STEPS[-1].key == "gateway",
              "the step that may end the connection is LAST",
              "the client dials ArenaNet from a recorded GAME_SERVER_INFO and the "
              "cage refuses it; anything after it would be lost")
    try:
        labelrun.Step("bad", "x", 5, "maybe")
        rejected = False
    except ValueError:
        rejected = True
    LEDGER.ok(rejected, "a step with an unknown prediction is refused at construction")
    try:
        labelrun.Step("bad", "x", 0, labelrun.TRAFFIC)
        zero_rejected = False
    except ValueError:
        zero_rejected = True
    LEDGER.ok(zero_rejected, "and so is a zero-length step")

    # ---- 2. run() marks every step, in order, before prompting -----------------
    print("\n2. run() marks each step into the capture before it prompts")
    rec, stop, said = FakeRec(), threading.Event(), []
    steps = [labelrun.Step("one", "do one", 0.01, labelrun.TRAFFIC),
             labelrun.Step("two", "do two", 0.01, labelrun.SILENCE)]
    ok = labelrun.run(rec, 1, stop, steps=steps, out=said.append, ready=0.01)
    marks = [e for e in rec.events if e["kind"] == "label_step"]
    LEDGER.ok(ok and len(marks) == 2,
              "one label_step per step, and the run reports completion",
              f"{len(marks)} marks from {len(steps)} steps")
    LEDGER.ok([m["key"] for m in marks] == ["one", "two"]
              and [m["index"] for m in marks] == [1, 2],
              "marks carry the key and the 1-based index, in script order")
    LEDGER.ok(any(e["kind"] == "label_run_end" for e in rec.events),
              "and a closing mark bounds the last step",
              "without it the final window would run to infinity and swallow "
              "everything after the run")
    LEDGER.ok(all(m["expect"] in (labelrun.SILENCE, labelrun.TRAFFIC) for m in marks),
              "the prediction is recorded WITH the mark",
              "so the capture can be judged later without the script that made it")

    # ---- 3. a stopped run says where it stopped --------------------------------
    print("\n3. a run cut short is recorded as cut short")
    rec2, stop2, said2 = FakeRec(), threading.Event(), []
    stop2.set()
    ok2 = labelrun.run(rec2, 1, stop2, steps=steps, out=said2.append, ready=0.01)
    LEDGER.ok(not ok2, "run() reports failure when it is stopped")
    LEDGER.ok(any(e["kind"] in ("label_run_stopped",) for e in rec2.events)
              or not [e for e in rec2.events if e["kind"] == "label_step"],
              "and it does not leave a half-finished run looking complete",
              "no label_run_end is written")

    # ---- 4. segmentation: the property the whole tool rests on -----------------
    print("\n4. a message lands in exactly one window, and only the right one")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cap.jsonl")
        records = [
            msg(1.0, 0x0029), msg(2.0, 0x0029),          # the tape / load: BEFORE
            {"kind": "label_step", "t": 10.0, "index": 1, "key": "idle_a",
             "prompt": "", "seconds": 5, "expect": labelrun.SILENCE},
            msg(11.0, labelrun.KEEPALIVE),                # keepalive only: control ok
            {"kind": "label_step", "t": 15.0, "index": 2, "key": "skill_1",
             "prompt": "", "seconds": 5, "expect": labelrun.TRAFFIC},
            msg(15.0, 0x0046),                            # exactly ON the mark
            msg(19.999, 0x0046),
            {"kind": "label_step", "t": 20.0, "index": 3, "key": "camera",
             "prompt": "", "seconds": 5, "expect": labelrun.SILENCE},
            msg(21.0, labelrun.KEEPALIVE),
            {"kind": "label_run_end", "t": 25.0, "steps": 3},
            msg(26.0, 0x00C1),                            # after the run: not attributed
        ]
        write_capture(path, records)
        marks3, msgs3 = labelrun.load(path)
        segs, before = labelrun.segment(marks3, msgs3)

        LEDGER.ok(len(segs) == 3, "one segment per prompted step", f"{len(segs)}")
        LEDGER.ok(len(before) == 2,
                  "traffic before the first step is reported separately, not as step 1",
                  "folding the instance load into the first action would inflate it "
                  "by however long the load took")
        LEDGER.ok(sum(len(v) for v in segs[1]["opcodes"].values()) == 2
                  and 0x0046 in segs[1]["opcodes"],
                  "both skill messages land in the skill window",
                  "including the one whose timestamp EQUALS the mark -- windows are "
                  "half-open [mark, next), so a message on the boundary belongs to "
                  "the step that just started, not the one that just ended")
        LEDGER.ok(sum(len(v) for v in segs[0]["opcodes"].values()) == 0
                  and segs[0]["keepalives"] == 1,
                  "the keepalive is COUNTED, not folded into the step's opcodes",
                  "it fires every 5s regardless of the operator and means nothing "
                  "about the window it lands in")
        total = sum(len(s["messages"]) for s in segs) + len(before)
        after = [r for r in msgs3 if r["t"] >= 25.0]
        LEDGER.ok(total + len(after) == len(msgs3),
                  "every message is accounted for exactly once: before, in a step, "
                  "or after the run", f"{len(before)} + {total - len(before)} + "
                                      f"{len(after)} = {len(msgs3)}")

        violations, _ref, silent_steps = labelrun.report(segs, before, say=lambda _s: None)
        LEDGER.ok(not violations,
                  "a clean run reports no control violation",
                  "idle_a and camera each saw only keepalives")
        LEDGER.ok(silent_steps == [],
                  "and no step predicted TRAFFIC came up empty here")

    # ---- 5. THE CONTROL CAN GO RED ---------------------------------------------
    print("\n5. traffic in a window predicted silent is caught, not passed")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "dirty.jsonl")
        write_capture(path, [
            {"kind": "label_step", "t": 10.0, "index": 1, "key": "idle_a",
             "prompt": "", "seconds": 5, "expect": labelrun.SILENCE,
             "control": True},
            msg(11.0, 0x003E),                      # the operator moved. Or the marks lie.
            {"kind": "label_run_end", "t": 15.0, "steps": 1},
        ])
        marks5, msgs5 = labelrun.load(path)
        segs5, before5 = labelrun.segment(marks5, msgs5)
        violations5, _r5, _s5 = labelrun.report(segs5, before5, say=lambda _s: None)
        LEDGER.ok(len(violations5) == 1 and violations5[0][0] == "idle_a",
                  "a dirty idle window is REPORTED as a refuted prediction",
                  "either the operator moved or the timestamps are wrong; both mean "
                  "no opcode from this run may be named")
        LEDGER.ok(labelrun.main(["--analyse", path]) == 1,
                  "and the CLI exits non-zero on it, so a script cannot ignore it")

    # ---- 5b. a refuted PREDICTION is not a control failure ---------------------
    print("\n5b. refuting a prediction is a finding, not a fault")
    # 2026-08-10: the operator's `camera` step -- predicted client-side -- sent ten
    # messages, and both idle windows were spotless. The tool reported "CONTROL
    # FAILURE ... every attribution in this run is suspect" and told them to throw
    # away the best run the project had produced. A step predicting SILENCE because
    # we have a HYPOTHESIS is a different thing from one predicting silence because
    # the operator was told to sit still, and only the second can invalidate a run.
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "refuted.jsonl")
        write_capture(path, [
            {"kind": "label_step", "t": 10.0, "index": 1, "key": "idle_a",
             "prompt": "", "seconds": 5, "expect": labelrun.SILENCE,
             "control": True},
            {"kind": "label_step", "t": 15.0, "index": 2, "key": "camera",
             "prompt": "", "seconds": 5, "expect": labelrun.SILENCE,
             "control": False},
            msg(16.0, 0x0040), msg(16.5, 0x0040),
            {"kind": "label_run_end", "t": 20.0, "steps": 2},
        ])
        m5b, x5b = labelrun.load(path)
        s5b, b5b = labelrun.segment(m5b, x5b)
        fails, refuted, _sil = labelrun.report(s5b, b5b, say=lambda _s: None)
        LEDGER.ok(not fails,
                  "a clean CONTROL keeps the run valid even when a prediction falls",
                  "idle_a was silent, so the attributions stand")
        LEDGER.ok(len(refuted) == 1 and refuted[0][0] == "camera",
                  "the refuted prediction is reported separately, as a FINDING",
                  "this is what the exercise is FOR")
        LEDGER.ok(labelrun.main(["--analyse", path]) == 0,
                  "and the CLI exits ZERO -- a refuted hypothesis is a result, "
                  "not an error")
    try:
        labelrun.Step("bad", "x", 5, labelrun.TRAFFIC, control=True)
        ctl_rejected = False
    except ValueError:
        ctl_rejected = True
    LEDGER.ok(ctl_rejected,
              "and a control that predicts TRAFFIC is refused at construction",
              "a control is only a control because doing nothing must produce nothing")

    # ---- 6. the prompts must survive a PIPE ------------------------------------
    print("\n6. the prompts reach an operator reading them through session.py")
    # THE BUG THIS EXISTS FOR. labelrun runs inside the GAMESRV, which session.py
    # spawns as a child and reads with `for line in proc.stdout` -- a call that
    # blocks until a newline arrives. The first version drew its countdown with
    # carriage returns and no newline, so a real operator saw NOTHING: not a
    # garbled countdown, nothing at all, for the entire run. Any output this
    # module produces has to be newline-terminated or it does not exist.
    import contextlib
    import io as _io
    buf = _io.StringIO()
    rec6, stop6 = FakeRec(), threading.Event()
    quick = [labelrun.Step("q", "do the thing", 0.05, labelrun.TRAFFIC)]
    with contextlib.redirect_stdout(buf):
        labelrun.run(rec6, 1, stop6, steps=quick, out=None, ready=0.05)
    text = buf.getvalue()
    LEDGER.ok(bool(text.strip()), "a live run writes to stdout at all", f"{len(text)}B")
    LEDGER.ok("\r" not in text,
              "and writes NO carriage returns -- an in-place redraw is invisible "
              "through a line-buffered pipe",
              "session.py reads the gamesrv with `for line in proc.stdout`, which "
              "blocks until a newline; a \\r countdown displays nothing at all")
    LEDGER.ok(text.endswith("\n"),
              "every write is newline-terminated, so nothing sits in the pipe "
              "waiting for the next step to flush it")

    # ---- 7. a capture with no marks is refused, not analysed as empty ----------
    print("\n7. a capture that was not a labelled run is refused")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plain.jsonl")
        write_capture(path, [msg(1.0, 0x0029), msg(2.0, 0x0046)])
        LEDGER.ok(labelrun.main(["--analyse", path]) == 1,
                  "no label_step marks means a loud failure, never a green empty run",
                  "an analysis of nothing that prints nothing would read as 'no "
                  "traffic', which is the opposite of the truth")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
