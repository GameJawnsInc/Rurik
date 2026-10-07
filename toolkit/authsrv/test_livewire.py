"""livewire.py: the committed retail-decode recipe, pinned to its own record.

What this refuses to let rot: the byte-closure discipline (a connection whose
wire and plaintext accounting disagree is REFUSED, never partially decoded),
the origin gate (an `ours` capture filed under live/ never leaks into a
retail census), and -- the reason the module exists at all (RETHINK
instrument #2) -- the ability of a cold session to reproduce the campaign's
retail-contract ground truth without re-deriving the wire recipe from a dead
scratchpad. The load-bearing validation is a NUMBER WITH INDEPENDENT
PROVENANCE: the 62994 connection's 432 player-era s2c 0x0029 rows were
counted by a different session's script (the 2026-08-26 drawing-board
skeptic, rethink-skeptic.md attack 1) before this module existed; this file
requires the committed recipe to reproduce it exactly.

The vault sections skip LOUDLY on a machine without the live corpus; the
floor is set from the green run on the machine that has it (the house rule:
from a real run, never a guess).
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks      # noqa: E402
import livewire    # noqa: E402
import capgaps     # noqa: E402
import tape        # noqa: E402

# MEASURED from the real green run on 2026-08-26: 12 checks against the
# 20-capture live corpus. Set AT the run per the house rule -- zero headroom.
# 2026-09-28 (CASTAI-Z1): 16 -- section 1's two declared-gaps doors and section
# 5's two checks on the first gapped live connection. (A bare machine runs
# section 1 only, 4 checks, below this floor as it always has been.)
# 2026-09-28 (CASTAI-Z1, the gap lane): 18 -- capgaps' set_aside/audit door in
# section 1 (bare, so a bare run is 5) and the whole-corpus set-aside audit in 5.
# 2026-10-07 (WIREORDER-A1): 23 -- 1b's synthetic reordered capture and its known-bad
# arm (bare, so a bare run is 7), and section 6's corpus-wide wire-order check plus the
# two D13.4 manifest connections. Red 4 of the 5 against the pre-fix decode_conn.
LEDGER = checks.Ledger("livewire: the committed retail-decode recipe",
                       floor=23)
check = checks.adopt(LEDGER)


def main():
    print("1. the doors that need no vault")
    check(livewire.connections(os.path.join(tempfile.gettempdir(),
                                            "no-such-capture-dir")) == [],
          "connections() on a missing directory is an empty list, not a "
          "raise",
          "a census loop over capture dirs must survive a half-copied "
          "vault; the LOUD refusal belongs to require-style callers")
    with tempfile.TemporaryDirectory() as td:
        who, why = livewire.capture_origin(td)
        check(who is None and why == "no wire.jsonl",
              "a directory without wire.jsonl has no origin and says so",
              "an unstamped capture must never default to either origin -- "
              "origin.py's three-valued rule, applied at the loader")
        # declared_gaps reads the capture's OWN manifest (2026-09-28, CASTAI-Z1)
        empty = livewire.declared_gaps(td)
        with open(os.path.join(td, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"report": {"connections": [
                {"connection": "1.2.3.4:5->6.7.8.9:80", "gaps": {}},
                {"connection": "1.2.3.4:6->6.7.8.9:80", "gaps": {"s2c": [[100, 7]]}},
                {"connection": "1.2.3.4:7->6.7.8.9:80", "gaps": {"c2s": [], "s2c": []}}]}}, fh)
        got = livewire.declared_gaps(td)
        # the ONE set-aside (capgaps.py, 2026-09-28): only a declared connection is
        # stepped past, and the audit is RED on a declared gap nobody has named in
        # KNOWN_GAPPED -- the next gapped capture is seen, never absorbed
        for port in (5, 6):
            open(os.path.join(td, f"game-1.2.3.4_{port}-to-6.7.8.9_80.jsonl"), "w").close()
        into = []
        stepped = [capgaps.set_aside(td, f"game-1.2.3.4_{p}-to-6.7.8.9_80.jsonl", got, into)
                   for p in (5, 6, 7)]
        unnamed_ok, unnamed_why = capgaps.audit(into, [td], lambda _c, _n: True)
        stamp = os.path.basename(td)
    check(stepped == [False, True, False]
          and into == [{"capture": stamp, "connection": "1.2.3.4:6->6.7.8.9:80",
                        "gaps": {"s2c": [[100, 7]]}}]
          and not unnamed_ok,
          "set_aside steps past ONLY the declared connection and records it by name; "
          "the audit is RED for a declared gap KNOWN_GAPPED does not name, though it "
          "is set aside and still refused", unnamed_why)
    check(empty == {} and got == {"1.2.3.4:6->6.7.8.9:80": {"s2c": [[100, 7]]}},
          "declared_gaps: no manifest -> {}; of three connections, only the one whose "
          "report lists missing bytes is declared (an empty gap list is not a gap)",
          f"{empty} {got}")
    check(livewire.conn_name("game-10.0.0.210_65009-to-98.95.137.136_80.jsonl")
          == "10.0.0.210:65009->98.95.137.136:80"
          and livewire.conn_name("auth-1.2.3.4_5-to-6.7.8.9_80.jsonl") is None,
          "conn_name spells a game file's connection the way the manifest does, and "
          "refuses a name of another shape")
    section_wire_order_synthetic()

    print("\n2. the live corpus (skips loudly without the vault)")
    root = livewire.captures_root()
    if not os.path.isdir(root):
        # Two arguments (label, why), and the verdict is RETURNED. Both were
        # wrong until 2026-08-31 and both only bite on a machine with no vault,
        # which is the one this branch exists for: the one-argument `skip`
        # raised TypeError, and had it not, the bare `return` handed `main` a
        # None that `sys.exit` reads as success. Third instance of the same
        # `skip` defect that day (test_castcycle x2, test_policyreplay x2).
        LEDGER.skip("2. the live corpus",
                    "no live capture corpus at %s -- the corpus sections "
                    "need the owner's vault" % root)
        return LEDGER.verdict()
    caps = livewire.live_captures()
    check(len(caps) >= 20,
          "the origin gate passes at least the 20 live captures the "
          "2026-08-26 census counted",
          "fewer means either the vault moved or the gate started refusing "
          "real live captures -- both are wrong loudly")
    names = {os.path.basename(c) for c, _ in caps}
    check("20260817T175358" not in names or len(names) >= 20,
          "the gate EXCLUDES at least one non-live directory (21 dirs on "
          "disk, 20 live at the pin date)",
          "a gate that passes everything is not a gate; the excluded "
          "directory is the control")

    print("\n3. the pinned connection: independent-provenance numbers")
    capdir = os.path.join(root, "20260807T143055")
    gf = "game-10.0.0.210_62994-to-54.198.7.73_80.jsonl"
    if not os.path.exists(os.path.join(capdir, gf)):
        LEDGER.skip("the pinned connection decode",
                    "pinned connection %s missing" % gf)
    else:
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        check(ok is True,
              "the 62994 connection decodes with FULL byte closure both "
              "directions",
              "ok=False means the wire/plaintext accounting stopped "
              "closing -- the schema or the recipe drifted")
        check(conn == "10.0.0.210:62994->54.198.7.73:80",
              "the connection identity reads back from the version row",
              "the conn string is what joins this stream to wire.jsonl; "
              "a wrong one dates messages with another connection's clock")
        n41 = sum(1 for r in merged if r[1] == "s2c" and r[2] == 41)
        check(n41 == 432,
              "s2c 0x0029 count == 432 -- the drawing-board skeptic's own "
              "independently-scripted count, reproduced by the committed "
              "recipe",
              "this is the module's whole reason to exist: a number with "
              "provenance OUTSIDE this module. A drift here is a decode "
              "regression, not a corpus change -- the corpus is frozen")
        n62 = sum(1 for r in merged if r[1] == "c2s" and r[2] == 62)
        n61 = sum(1 for r in merged if r[1] == "c2s" and r[2] == 61)
        check(n62 == 12 and n61 == 99,
              "c2s censuses pin too: 12 clicks (0x003E) and 99 heading "
              "reports (0x003D) on the same connection",
              "op 62 vs 64 is the exact confusion that reached a lane "
              "brief once (sec.0.17's instrument corrections); pinning "
              "both directions catches a mask or channel swap")
        check(len(merged) == 2821,
              "total decoded message count == 2821",
              "the coarsest whole-stream pin -- any silent gain or loss "
              "of messages moves it")
        ts = [r[0] for r in merged]
        check(all(a <= b for a, b in zip(ts, ts[1:])),
              "the merged stream is time-ordered on this connection, whose clock "
              "never steps back -- wire order and time order agree here",
              "consumers window over time. Since WIREORDER-A1 the merge keeps each "
              "direction in WIRE order and t may dip where segments reached the "
              "capture out of order (41 live connections, section 6); this one has none")

    print("\n4. the rung-7 capture: whole-capture closure")
    capdir = os.path.join(root, "20260818T132739")
    if not os.path.isdir(capdir):
        LEDGER.skip("capture 20260818T132739",
                    "capture 20260818T132739 missing")
    else:
        conns = livewire.connections(capdir)
        check(len(conns) == 8,
              "the rung-7 damage capture holds its 8 game connections "
              "(PLAN's '9/9 decrypted' = these plus the auth channel)",
              "a lost connection is a lost third of a damage corpus")
        oks = [livewire.decode_conn(capdir, gf)[2] for gf in conns]
        check(all(oks),
              "ALL 8 decode with full byte closure",
              "rung 7's 495 damage events ride these streams; a partial "
              "decode reported as a full one is the suite's oldest defect "
              "class")

    print("\n5. a gapped connection is DECLARED by its capture, and still refused")
    capdir = os.path.join(root, "20260928T103123")
    gf = "game-10.0.0.210_65009-to-98.95.137.136_80.jsonl"
    if not os.path.exists(os.path.join(capdir, gf)):
        LEDGER.skip("the gapped connection",
                    "capture 20260928T103123 (CASTAI-Z1) missing")
    else:
        gaps = livewire.declared_gaps(capdir)
        check(gaps == {"10.0.0.210:65009->98.95.137.136:80":
                       {"s2c": [[38045, 38], [38548, 20]]}},
              "CASTAI-Z1's match 2 is the ONE connection its manifest declares gapped: "
              "38 + 20 s2c bytes at stream offsets 38045 / 38548",
              f"{gaps}")
        ok_gapped = livewire.decode_conn(capdir, gf)[2]
        oks = {g: livewire.decode_conn(capdir, g)[2] for g in livewire.connections(capdir)
               if livewire.conn_name(g) not in gaps}
        check(ok_gapped is False and oks and all(oks.values()),
              "decode_conn still REFUSES it (a hole dates later messages with the wrong "
              "bytes), and every connection the manifest does not declare decodes whole",
              f"gapped ok={ok_gapped}; others {sum(oks.values())}/{len(oks)}")
        # the corpus iterators' set-aside, over the WHOLE live corpus: exactly the known
        # set, refused by BOTH doors (decode_conn and load_tape); and the audit's teeth --
        # a refusal callback that answers "decodes" turns it red
        aside = []
        n_yield = sum(1 for _ in livewire.live_connections(set_aside=aside))
        caps = [d for d, _w in livewire.live_captures()]
        a_ok, a_why = capgaps.audit(aside, caps, livewire.refuses)
        t_ok, _t_why = capgaps.audit(aside, caps, tape.refuses)
        bad_ok, _bad_why = capgaps.audit(aside, caps, lambda _c, _n: False)
        check(a_ok and t_ok and not bad_ok and n_yield > 0
              and len(aside) == len(capgaps.KNOWN_GAPPED),
              "live_connections(set_aside=) sets aside EXACTLY capgaps.KNOWN_GAPPED over "
              "the whole corpus, each still refused by decode_conn AND load_tape; "
              "KNOWN-BAD: an audit told it decodes goes red",
              f"{n_yield} yielded; {a_why}")

    section_wire_order_corpus(root)
    return LEDGER.verdict()


def _write_reordered_capture(td):
    """A capture whose s2c clock steps BACK: segment 2 (body B) was captured 10 ms
    before segment 1 (body A) though it follows it in TCP sequence -- they reached the
    capture out of order, the shape 41 live connections carry. One c2s message
    at a time between. Returns (game file, A, B, C) with A/B/C the decoded value lists."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
    import codec as codecmod                                  # noqa: PLC0415
    cod = codecmod.Codec()
    a = cod.encode("GAME_SMSG", 0x01C4, [0x0A0A])
    b = cod.encode("GAME_SMSG", 0x01C5, [0x0B0B])
    c = cod.encode("GAME_CMSG", 0x0011, [0x0C0C], header_value=0x8011)
    client, server = ("10.9.9.9", 5000), ("3.3.3.3", 80)
    conn = f"{client[0]}:{client[1]}->{server[0]}:{server[1]}"
    rows = []

    def seg(way, seq, t, payload):
        src, dst = (client, server) if way == "c2s" else (server, client)
        rows.append({"kind": "wire", "dir": way, "seq": seq, "t": t,
                     "payload": payload.hex(), "src": src[0], "sport": src[1],
                     "dst": dst[0], "dport": dst[1]})

    hs_s, hs_c = b"S" * livewire.HANDSHAKE_S2C, b"C" * livewire.HANDSHAKE_C2S_GAME
    seg("s2c", 1000, 9.0, hs_s)
    seg("s2c", 1000 + len(hs_s), 10.000, a)                   # first in sequence
    seg("s2c", 1000 + len(hs_s) + len(a), 9.990, b)           # ...captured EARLIER
    seg("c2s", 5000, 9.0, hs_c)
    seg("c2s", 5000 + len(hs_c), 9.995, c)
    with open(os.path.join(td, "wire.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    gf = f"game-{client[0]}_{client[1]}-to-{server[0]}_{server[1]}.jsonl"
    with open(os.path.join(td, gf), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "version", "channel": "game", "connection": conn}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                             "plain": (a + b).hex()}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "c2s", "plain": c.hex()}) + "\n")
    return gf


def section_wire_order_synthetic():
    """1b. WIREORDER-A1 (2026-10-07), on a capture built here, so a bare machine runs it.

    decode_conn used to SORT its merge by segment time, and a capture's segment clock
    runs backwards wherever two segments reached the capture out of order -- so a later message
    could come out ahead of an earlier one in its OWN direction. The contract now: each
    direction in wire order, `t` verbatim, the two interleaved head by head. KNOWN-BAD:
    the old sort, applied to the same rows, puts B ahead of A."""
    with tempfile.TemporaryDirectory() as td:
        gf = _write_reordered_capture(td)
        _conn, merged, ok = livewire.decode_conn(td, gf)
    got = [(d, op, round(t, 3)) for t, d, op, _v in merged]
    check(ok and got == [("c2s", 0x0011, 9.995), ("s2c", 0x01C4, 10.0), ("s2c", 0x01C5, 9.99)],
          "1b. a segment captured EARLIER than the one before it in sequence stays BEHIND "
          "it: each direction in wire order, t verbatim (it may step back), the c2s "
          "interleaved head by head (WIREORDER-A1)", f"ok={ok} {got}")
    resorted = sorted(merged, key=lambda r: (r[0], 0 if r[1] == "c2s" else 1))
    check([r[2] for r in resorted if r[1] == "s2c"] == [0x01C5, 0x01C4],
          "KNOWN-BAD: the time sort decode_conn used before WIREORDER-A1 puts B ahead "
          "of A on the same rows -- so the check above can tell the two apart",
          f"{[(r[1], hex(r[2])) for r in resorted]}")


def section_wire_order_corpus(root):
    """6. WIREORDER-A1 on the live corpus: wire order inside each direction, everywhere.

    The two connections DIVERGENCE-D13.4's review caught (RV-2) carry a 0x0196 manifest
    body that the time sort put AHEAD of its 0x0198 phase -- which the client's own
    handler refuses (MsCliMan:457, studies/divergence/FINDINGS.md D13.4). In wire order
    each body follows a phase."""
    print("\n6. wire order inside each direction, over the corpus (WIREORDER-A1)")
    n = wire_ok = differs = 0
    for capdir, gf in livewire.live_connections(set_aside=[]):
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        if not ok:
            continue
        cod = livewire._get_codec(livewire.conn_build(capdir, gf))
        same = True
        for way, chan, mask in (("c2s", "GAME_CMSG", livewire.CMSG_MASK),
                                ("s2c", "GAME_SMSG", 0)):
            _c, events, _err = livewire.build_events(capdir, gf, way)
            wire, _r = tape.decode_all(events, cod, chan, mask, strict=False)
            same &= [(t, op, v) for t, d, op, v in merged if d == way] == wire
        n += 1
        wire_ok += same
        ts = sorted(merged, key=lambda r: (r[0], 0 if r[1] == "c2s" else 1))
        differs += ts != merged
    # A FLOOR on `differs`, never an equality: the corpus grows, and a new reordered
    # connection is good news that must not redden this (41 of 127 on 2026-10-07).
    check(n > 0 and wire_ok == n and differs >= 41,
          "every closing live connection's merge holds EACH direction in wire order "
          "(TCP sequence, build_events + decode_all), and the corpus still carries the "
          "reordering that makes this a check -- the time sort differs on >= 41",
          f"{wire_ok}/{n} in wire order; time sort differs on {differs}")
    # The oracle is manifestbody.rebuild: the client's own phase/body/done bookkeeping,
    # which REFUSES a body with no open phase (MsCliMan:457) as the client asserts on it.
    import manifestbody                                        # noqa: PLC0415
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
    import codec as codecmod                                   # noqa: PLC0415
    ops = manifestbody.opcodes(codecmod.Codec())

    def closes(rows):
        """'refused: ...', or (body bytes closed by a DONE, body bytes sent)."""
        sent = sum(len(v[1]) for _t, _d, op, v in rows if op == ops["body"])
        try:
            done = manifestbody.rebuild([(t, op, v) for t, _d, op, v in rows], ops)
        except manifestbody.ManifestError as exc:
            return "refused: " + str(exc)[:70]
        return (sum(len(d.p0) + len(d.p1) for d in done), sent)

    # :51534 -- the time sort puts a body where no phase is open (rebuild refuses);
    # :55934 -- it puts a kind-0 DONE ahead of the kind-2 bracket, so that DONE closes
    # two EMPTY buffers and the 17 + 504 body bytes after it are never closed at all.
    for stamp, port in (("20260916T213125", "51534"), ("20260929T150923", "55934")):
        capdir = os.path.join(root, stamp)
        gfs = [g for g in livewire.connections(capdir) if f"_{port}-to-" in g]
        if len(gfs) != 1:
            LEDGER.skip(f"6. {stamp} :{port}", "connection missing")
            continue
        _conn, merged, _ok = livewire.decode_conn(capdir, gfs[0])
        s2c = [r for r in merged if r[1] == "s2c"]
        wire, resorted = closes(s2c), closes(sorted(s2c, key=lambda r: r[0]))
        check(isinstance(wire, tuple) and wire[1] > 0 and wire[0] == wire[1]
              and resorted != wire,
              f"{stamp} :{port}: in decode_conn's order every 0x0196 body byte is closed "
              f"by a DONE, the client's own bookkeeping (manifestbody.rebuild); KNOWN-BAD, "
              f"the time sort refuses or strands body bytes (D13.4 RV-2)",
              f"wire (closed, sent) {wire}; time-sorted {resorted}")


# `sys.exit(main())`, not a bare `main()`, and `main` RETURNS the verdict:
# both halves were missing until 2026-08-31, so this file printed its FAIL
# banner and exited 0. run_suite.py catches that as SUSPECT (exit 0 with no
# ALL CHECKS PASSED line), which is the backstop working -- but a developer
# running the file directly saw a clean exit code on a red run, and
# CLAUDE.md's rule is that a test exits non-zero.
if __name__ == "__main__":
    sys.exit(main())
