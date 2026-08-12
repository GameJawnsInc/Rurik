"""Prove the off-wire capture's parsing and reassembly, without the driver.

wirecapture.py's driver half needs WinDivert and an elevated shell, but its correctness
lives in the pure half -- turning raw IPv4/TCP packets into ordered per-direction byte
streams, and writing a capture that reads back as LIVE. That half is what a wrong decrypt
would trace to, and it is fully testable here against synthetic packets:

  1. parse_ipv4_tcp pulls the right fields, and rejects non-IPv4 / non-TCP / runt packets;
  2. direction_of decides c2s/s2c from the endpoints, not from capture metadata;
  3. reassemble orders by TCP seq, drops duplicates, and REPORTS gaps rather than hiding
     them -- a lost segment desyncs the keystream and a decryptor must see it;
  4. a written capture reads back with the streams intact and stamped origin: LIVE, which
     origin.py never infers, so forgetting it would make every live capture UNKNOWN;
  4b. the LIVE shape specifically -- direction decided by port when the server's address is
     not knowable in advance, and SEVERAL connections kept on separate sequence spaces,
     with the single-stream reader refusing rather than merging them.

The driver itself is checked only for an honest refusal when WinDivert is absent.

standard library only.
"""
import json
import os
import socket
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import origin  # noqa: E402
import wirecapture as wc  # noqa: E402

# 42 is the measured total of a green run with WinDivert present (section 5 then declares
# a skip); without the driver that skip becomes a check and the run scores 43. It was 28
# until 2026-08-11, when §9 added the clock binding -- the epoch, the marks channel and
# the five ways the two can disagree. Set from a real run, never from a guess.
LEDGER = checks.Ledger("wirecapture", floor=42)


def ipv4_tcp(src, dst, sport, dport, seq, payload=b"", proto=6, ver=4):
    """A minimal well-formed IPv4/TCP packet (checksums zeroed -- the parser ignores them)."""
    tcp = struct.pack(">HHIIBBHHH", sport, dport, seq, 0, (5 << 4), 0, 0xFFFF, 0, 0) + payload
    total = 20 + len(tcp)
    ip = struct.pack(">BBHHHBBH4s4s", (ver << 4) | 5, 0, total, 1, 0, 64, proto, 0,
                     socket.inet_aton(src), socket.inet_aton(dst))
    return ip + tcp


def main():
    CLIENT, SERVER = "127.0.0.1", "127.0.0.3"
    PORTS = {6112}

    # ---- 1. parse ----------------------------------------------------------
    print("1. parse_ipv4_tcp pulls fields and rejects what it should")
    p = wc.parse_ipv4_tcp(ipv4_tcp(CLIENT, SERVER, 5000, 6112, 0x1000, b"hello"))
    LEDGER.ok(p and p["src"] == CLIENT and p["dst"] == SERVER, "src/dst parsed",
              str(p and (p["src"], p["dst"])))
    LEDGER.ok(p and p["sport"] == 5000 and p["dport"] == 6112 and p["seq"] == 0x1000,
              "ports and seq parsed", str(p and (p["sport"], p["dport"], hex(p["seq"]))))
    LEDGER.ok(p and p["payload"] == b"hello", "payload parsed", str(p and p["payload"]))
    LEDGER.ok(wc.parse_ipv4_tcp(ipv4_tcp(CLIENT, SERVER, 1, 2, 3, proto=17)) is None,
              "a non-TCP (UDP) packet is rejected")
    LEDGER.ok(wc.parse_ipv4_tcp(ipv4_tcp(CLIENT, SERVER, 1, 2, 3, ver=6)) is None,
              "a non-IPv4 packet is rejected")
    LEDGER.ok(wc.parse_ipv4_tcp(b"\x45\x00\x00") is None,
              "a runt packet is rejected, not indexed into")

    # ---- 2. direction ------------------------------------------------------
    print("\n2. direction_of decides from the endpoints")
    to_srv = wc.parse_ipv4_tcp(ipv4_tcp(CLIENT, SERVER, 5000, 6112, 1, b"x"))
    fr_srv = wc.parse_ipv4_tcp(ipv4_tcp(SERVER, CLIENT, 6112, 5000, 1, b"y"))
    other = wc.parse_ipv4_tcp(ipv4_tcp(CLIENT, "8.8.8.8", 5000, 443, 1, b"z"))
    LEDGER.ok(wc.direction_of(to_srv, SERVER, PORTS) == wc.C2S, "to server -> c2s")
    LEDGER.ok(wc.direction_of(fr_srv, SERVER, PORTS) == wc.S2C, "from server -> s2c")
    LEDGER.ok(wc.direction_of(other, SERVER, PORTS) is None,
              "traffic to a different host is neither direction")

    # ---- 3. reassembly -----------------------------------------------------
    print("\n3. reassemble orders by seq, drops dups, reports gaps")
    # Out of order + a duplicate; base seq 1000.
    segs = [(1000, b"AAAA"), (1008, b"CCCC"), (1004, b"BBBB"), (1004, b"BBBB")]
    data, gaps = wc.reassemble(segs)
    LEDGER.ok(data == b"AAAABBBBCCCC", "out-of-order segments reassemble in seq order",
              data.hex())
    LEDGER.ok(gaps == [], "a complete stream reports no gaps", str(gaps))

    # A hole: 1000..1004 present, 1004..1008 MISSING, 1008 present.
    hole = [(1000, b"AAAA"), (1008, b"CCCC")]
    d2, g2 = wc.reassemble(hole)
    LEDGER.ok(g2 == [(4, 4)], "a missing segment is reported as a gap, not closed",
              str(g2))
    LEDGER.ok(len(d2) == 12, "the gap is held as space so later bytes keep their offset",
              f"{len(d2)} bytes")

    # ---- 4. capture file round-trips, stamped LIVE -------------------------
    print("\n4. a written capture reads back intact and LIVE")
    ticks = iter([0.0, 0.0, 0.1, 0.2, 0.3, 0.4])   # deterministic clock
    clock = lambda: next(ticks)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "live.jsonl")
        fh, record = wc.open_capture(path, "127.0.0.1:5000", "127.0.0.3:6112", 4242,
                                     PORTS, clock)
        record(wc.C2S, 1000, b"AAAA")
        record(wc.C2S, 1004, b"BBBB")
        record(wc.S2C, 2000, b"zzzz")
        fh.close()

        who, why = origin.origin_of(path)
        LEDGER.ok(who == origin.OURS,
                  "a sniff pinned to LOOPBACK stamps itself ours, not live", why)

        meta, streams, gaps = wc.load_wire(path)
        LEDGER.ok(meta and meta["pid"] == 4242 and meta["client"] == "127.0.0.1:5000",
                  "wire_meta round-trips", str(meta))
        LEDGER.ok(streams[wc.C2S] == b"AAAABBBB", "c2s stream reassembles from the file",
                  streams[wc.C2S].hex())
        LEDGER.ok(streams[wc.S2C] == b"zzzz", "s2c stream reassembles from the file",
                  streams[wc.S2C].hex())

    # ---- 4b. the LIVE shape: unknown address, several connections ----------
    print("\n4b. port-only capture: direction by port, and connections kept apart")
    # A live sniff cannot name the server ip -- the client picks ArenaNet's address itself,
    # and the sniff must already be running when it does. So the port decides which end is
    # the server, on any host.
    live_srv = wc.parse_ipv4_tcp(ipv4_tcp("10.0.0.9", "3.65.1.1", 51000, 6112, 1, b"x"))
    live_cli = wc.parse_ipv4_tcp(ipv4_tcp("3.65.1.1", "10.0.0.9", 6112, 51000, 1, b"y"))
    LEDGER.ok(wc.direction_of(live_srv, None, PORTS) == wc.C2S,
              "port-only: a packet TO a server port is c2s, whatever the address",
              "this is the case a live run is entirely made of")
    LEDGER.ok(wc.direction_of(live_cli, None, PORTS) == wc.S2C,
              "port-only: a packet FROM a server port is s2c")
    both = wc.parse_ipv4_tcp(ipv4_tcp("1.1.1.1", "2.2.2.2", 6112, 6112, 1, b"?"))
    neither = wc.parse_ipv4_tcp(ipv4_tcp("1.1.1.1", "2.2.2.2", 4000, 5000, 1, b"?"))
    LEDGER.ok(wc.direction_of(both, None, PORTS) is None,
              "port-only: server-port on BOTH ends is undecidable, so neither direction",
              "a misfiled segment desyncs a keystream far from here")
    LEDGER.ok(wc.direction_of(neither, None, PORTS) is None,
              "port-only: server-port on neither end is neither direction")
    LEDGER.ok(b"SrcAddr" not in wc._filter(None, PORTS)
              and b"6112" in wc._filter(None, PORTS),
              "the port-only WinDivert filter pins no address", str(wc._filter(None, PORTS)))
    LEDGER.ok(b"ipv6" in wc._filter(None, PORTS),
              "and it accepts IPv6 packets even though the parser is IPv4-only",
              "dropped in the kernel they are invisible; received and rejected they show "
              "up as recv>0 parsed==0 and name the cause")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "multi.jsonl")
        fh, record = wc.open_capture(path, "10.0.0.9:*", None, 4242, {6112, 6601},
                                     lambda: 0.0)   # unpinned -> live
        # TWO connections, deliberately overlapping sequence spaces -- the auth channel and
        # then the game server on a different address, which is what a real login does.
        auth_c = ipv4_tcp("10.0.0.9", "3.65.1.1", 51000, 6112, 1000, b"AUTHc2s")
        auth_s = ipv4_tcp("3.65.1.1", "10.0.0.9", 6112, 51000, 7000, b"AUTHs2c")
        game_c = ipv4_tcp("10.0.0.9", "3.65.9.9", 51001, 6112, 1000, b"GAMEc2s")
        game_s = ipv4_tcp("3.65.9.9", "10.0.0.9", 6112, 51001, 7000, b"GAMEs2c")
        for raw, d in ((auth_c, wc.C2S), (auth_s, wc.S2C),
                       (game_c, wc.C2S), (game_s, wc.S2C)):
            pk = wc.parse_ipv4_tcp(raw)
            record(d, pk["seq"], pk["payload"], pk)
        fh.close()

        LEDGER.ok(origin.origin_of(path)[0] == origin.LIVE,
                  "an UNPINNED sniff still stamps live -- that mode is the live driver's",
                  "the stamp is derived from the endpoint, not asserted")
        _m, conns = wc.load_connections(path)
        LEDGER.ok(len(conns) == 2, "two connections are read back as two, not merged",
                  ", ".join(sorted(str(k) for k in conns)))
        auth_key = "10.0.0.9:51000->3.65.1.1:6112"
        game_key = "10.0.0.9:51001->3.65.9.9:6112"
        LEDGER.ok(conns.get(auth_key, {}).get(wc.C2S) == b"AUTHc2s"
                  and conns.get(game_key, {}).get(wc.C2S) == b"GAMEc2s",
                  "each connection reassembles on its OWN sequence space",
                  "both start at seq 1000; merged, one would land inside the other")
        LEDGER.ok(conns.get(auth_key, {}).get(wc.S2C) == b"AUTHs2c"
                  and conns.get(game_key, {}).get(wc.S2C) == b"GAMEs2c",
                  "the s2c direction is separated per connection too")
        refused = ""
        try:
            wc.load_wire(path)
        except wc.MultiConnectionError as exc:
            refused = str(exc)
        LEDGER.ok("2 TCP connections" in refused,
                  "the single-stream reader REFUSES a multi-connection capture",
                  "silently merging them yields bytes that decrypt to nothing -- "
                  "a crypto-shaped failure with a plumbing cause")

    # ---- 5. the driver refuses honestly when absent ------------------------
    print("\n5. the WinDivert layer refuses (or works) -- never a silent empty capture")
    try:
        wc._load_windivert()
        LEDGER.skip("driver refusal", "WinDivert is present -- cannot test the absent path")
    except wc.WinDivertError as e:
        LEDGER.ok("WinDivert.dll" in str(e) and "elevated" in str(e).lower(),
                  "absent WinDivert refuses with the install + elevation step",
                  "names the DLL and the elevated-shell requirement")

    # ---- 9. the clock binding: an epoch, a second witness, and the refusals --
    print("\n9. the clock binding (studies/monsterai §7.1)")
    # WHAT THIS IS ABOUT. Every segment is stamped `perf_counter() - t0` with `t0` taken
    # inside the SNIFFER SUBPROCESS, and CPython's contract says perf_counter's reference
    # point is undefined -- only differences within one call site mean anything. So until
    # `t0_wall` existed, a capture's `t` was an offset from an origin no other process
    # could name, and a narrated session could be aligned to its narration only post-hoc
    # and only to within seconds. Every check below is one this could get wrong quietly.
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "epoch.jsonl")
        ticks = iter([0.0, 10.0, 11.0, 12.0])
        fh, record = wc.open_capture(path, "127.0.0.1:5000", "127.0.0.3:6112", 7,
                                     PORTS, lambda: next(ticks),
                                     wall=lambda: 1_700_000_000.0)
        record(wc.C2S, 1000, b"AAAA")
        record(wc.C2S, 1004, b"BBBB")
        fh.close()
        meta, _streams, _gaps = wc.load_wire(path)

        LEDGER.ok(wc.capture_epoch(meta) == 1_700_000_000.0,
                  "a capture records the ABSOLUTE time its t=0 corresponds to",
                  f"t0_wall={wc.capture_epoch(meta)} -- without it `t` is an offset from "
                  "an origin no other process can name, which is the whole blocker")
        LEDGER.ok(wc.wall_of(meta, 10.0) == 1_700_000_010.0,
                  "so any segment's t converts to absolute UTC",
                  "t0_wall + t, and the subtraction stays inside the sniffer process")
        # THE ORDERING TRAP: t0 must be sampled BEFORE the first segment, or every
        # timestamp is shifted by however long the meta write took.
        recs = [json.loads(L) for L in open(path, encoding="utf-8")]
        firstwire = next(r for r in recs if r.get("kind") == "wire")
        LEDGER.ok(firstwire["t"] == 10.0,
                  "and t is measured from the epoch, not from the meta write",
                  f"first segment t={firstwire['t']} against the clock's second value")

        # THE REFUSAL THAT MATTERS: a capture written before 2026-08-11 has no epoch,
        # and nothing may invent one for it. manifest.json's stamp is the tempting
        # substitute and it is wrong by however long spawning the sniffer took.
        LEDGER.ok(wc.capture_epoch({"kind": "wire_meta", "pid": 1}) is None
                  and wc.wall_of({"kind": "wire_meta"}, 5.0) is None,
                  "a capture with no epoch refuses to be placed on a clock",
                  "None, not a guess -- manifest.json's stamp is taken in the PARENT "
                  "before the sniffer subprocess exists")

        # ---- the marks channel, and the four ways it can disagree -----------
        mpath = os.path.join(tmp, wc.MARKS_NAME)
        with open(mpath, "w", encoding="utf-8") as mfh:
            for i, (w, p, wt) in enumerate(
                    [(1_700_000_002.0, 500.0, 1.5),
                     (1_700_000_006.0, 504.0, 5.4),
                     (1_700_000_009.0, 507.0, 8.6)], start=1):
                wc.write_mark(mfh, i, f"step{i}", wt,
                              clock=lambda p=p: p, wall=lambda w=w: w)
        marks = wc.read_marks(mpath)
        LEDGER.ok(len(marks) == 3 and marks[0]["label"] == "step1"
                  and marks[2]["wire_t"] == 8.6,
                  "marks round-trip with both clocks and the wire anchor",
                  f"{len(marks)} marks, each carrying wall, perf and wire_t")

        rows, problems = wc.mark_skew(meta, marks)
        skews = [r[4] for r in rows]
        LEDGER.ok(not problems and len(rows) == 3,
                  "a well-formed session binds with no problems reported",
                  f"skews {[round(s, 2) for s in skews]}")
        LEDGER.ok(max(skews) - min(skews) < 0.2,
                  "and it is the SPREAD of skew that is small, not the offset",
                  f"spread {max(skews) - min(skews):.3f}s. A constant offset is expected "
                  "-- wire_t is the last segment SEEN, always a little behind the mark "
                  "-- so a check on the offset itself would fail for a healthy capture")

        # NEGATIVE CONTROL 1: no epoch -> refuse rather than bind against nothing.
        _rows, probs = wc.mark_skew({"kind": "wire_meta"}, marks)
        LEDGER.ok(_rows == [] and any("cannot be placed" in p for p in probs),
                  "marks against an epochless capture REFUSE rather than bind",
                  str(probs))

        # NEGATIVE CONTROL 2: the two channels disagree about order. No averaging can
        # fix this, so it must be named.
        swapped = [dict(marks[0]), dict(marks[1]), dict(marks[2])]
        swapped[2]["wire_t"] = 0.1
        _r, probs = wc.mark_skew(meta, swapped)
        LEDGER.ok(any("out of order on the wire clock" in p for p in probs),
                  "marks that go backwards on ONE channel are caught",
                  f"{probs} -- the two channels disagree about what happened first")

        # NEGATIVE CONTROL 3: the wall clock jumped mid-session (NTP, DST, a manual
        # change). perf_counter is monotonic and does not, so the pair catches it.
        jumped = [dict(m) for m in marks]
        jumped[2]["wall"] += 3600.0
        _r, probs = wc.mark_skew(meta, jumped)
        LEDGER.ok(any("the wall clock moved" in p for p in probs),
                  "a wall clock that jumps mid-session is caught by the perf pair",
                  "this is the entire reason a mark carries perf as well as wall")

        # NEGATIVE CONTROL 4: a single channel is not a check. Strip wire_t and the
        # binding must report the loss rather than proceed on the wall clock alone.
        halved = [{k: v for k, v in m.items() if k != "wire_t"} for m in marks]
        _r, probs = wc.mark_skew(meta, halved)
        LEDGER.ok(len(probs) == 3 and all("missing a channel" in p for p in probs),
                  "and a mark missing a channel is reported, not silently half-checked",
                  f"{len(probs)} of 3 marks named")

        # NEGATIVE CONTROL 5: a MISSING perf clock must not be reported as a MOVED one.
        # It was, until this check existed: absent perf defaulted to 0, so the difference
        # of two zeros lost to any real elapsed wall time and the operator was told their
        # clock had jumped. A wrong diagnosis is worse than a vague one.
        noperf = [{k: v for k, v in m.items() if k != "perf"} for m in marks]
        _r, probs = wc.mark_skew(meta, noperf)
        LEDGER.ok(probs and all("cannot be ruled out" in p for p in probs)
                  and not any("wall clock moved" in p for p in probs),
                  "a mark with NO perf clock says so, rather than crying 'clock moved'",
                  f"{probs[0]} -- the absent-field case and the moved-clock case are "
                  "different findings and must not share a message")

        LEDGER.ok(wc.last_wire_t(path) == 11.0,
                  "last_wire_t reads the capture's own progress off disk",
                  "the sniffer is a subprocess, so there is no shared state to read")
        LEDGER.ok(wc.last_wire_t(os.path.join(tmp, "nope.jsonl")) is None
                  and wc.read_marks(os.path.join(tmp, "nope.jsonl")) == [],
                  "and both readers answer None/[] for a file that is not there",
                  "a mark taken before any segment arrived is a real case")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
