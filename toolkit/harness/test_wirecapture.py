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
     origin.py never infers, so forgetting it would make every live capture UNKNOWN.

The driver itself is checked only for an honest refusal when WinDivert is absent.

standard library only.
"""
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

LEDGER = checks.Ledger("wirecapture", floor=12)


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
        LEDGER.ok(who == origin.LIVE, "the capture classifies as LIVE by its own stamp", why)

        meta, streams, gaps = wc.load_wire(path)
        LEDGER.ok(meta and meta["pid"] == 4242 and meta["client"] == "127.0.0.1:5000",
                  "wire_meta round-trips", str(meta))
        LEDGER.ok(streams[wc.C2S] == b"AAAABBBB", "c2s stream reassembles from the file",
                  streams[wc.C2S].hex())
        LEDGER.ok(streams[wc.S2C] == b"zzzz", "s2c stream reassembles from the file",
                  streams[wc.S2C].hex())

    # ---- 5. the driver refuses honestly when absent ------------------------
    print("\n5. the WinDivert layer refuses (or works) -- never a silent empty capture")
    try:
        wc._load_windivert()
        LEDGER.skip("driver refusal", "WinDivert is present -- cannot test the absent path")
    except wc.WinDivertError as e:
        LEDGER.ok("WinDivert.dll" in str(e) and "elevated" in str(e).lower(),
                  "absent WinDivert refuses with the install + elevation step",
                  "names the DLL and the elevated-shell requirement")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
