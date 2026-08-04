"""
Rurik go/no-go probe: does the post-Reforged Guild Wars client still honour
-authsrv <ip> and speak its documented handshake to an arbitrary address?

Binds a set of candidate auth ports on 127.0.0.1, accepts anything that shows
up, and records every byte the client sends without ever replying. We are not
trying to complete a handshake -- we only want to know:

  1. Does the client connect at all?           -> -authsrv still redirects
  2. Which port does it pick?                   -> tells us the auth endpoint
  3. Does it speak first, or wait for us?       -> tells us who opens the
                                                   handshake, which decides
                                                   whether R1 can start from
                                                   a passive listener
  4. What do the first bytes look like?         -> version/protocol fingerprint

Read-only with respect to C:\\gw. Writes only to its own output directory.
"""

import argparse
import binascii
import json
import os
import socket
import selectors
import threading
import time

# Guild Wars uses two separate server roles on two separate ports, and the probe
# has to watch both or it will report silence for the wrong reason:
#
#   6600  the NCSoft "portal" / STS login. Text protocol (STS/1.0) carrying XML,
#         wrapped in TLS-SRP. This is the FIRST hop and the one -portal targets.
#   6112  the Guild Wars auth/game channel. This is what -authsrv targets.
#
# 80 and 443 are watched because portal traffic is HTTP-shaped and may land there;
# the 611x neighbours are cheap insurance against the port having moved.
CANDIDATE_PORTS = [6600, 6112, 6113, 80, 443, 6111, 6114]


def hexdump(data: bytes, width: int = 16) -> str:
    lines = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hexpart = " ".join(f"{b:02x}" for b in chunk).ljust(width * 3 - 1)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{off:08x}  {hexpart}  |{asciipart}|")
    return "\n".join(lines)


class Probe:
    def __init__(self, outdir: str, duration: float):
        self.outdir = outdir
        self.duration = duration
        self.sel = selectors.DefaultSelector()
        self.listeners = {}
        self.events = []
        self.lock = threading.Lock()
        self.conn_seq = 0
        os.makedirs(outdir, exist_ok=True)

    def log(self, **kw):
        kw["t"] = round(time.time() - self.t0, 4)
        kw["wall"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            self.events.append(kw)
        print(f"[{kw['t']:8.3f}] {kw.get('event')}: "
              f"{ {k: v for k, v in kw.items() if k not in ('t', 'wall', 'event', 'hex')} }",
              flush=True)

    def bind_all(self):
        for port in CANDIDATE_PORTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                s.listen(8)
                s.setblocking(False)
                self.sel.register(s, selectors.EVENT_READ, ("listen", port))
                self.listeners[port] = s
                print(f"  bound 127.0.0.1:{port}", flush=True)
            except OSError as e:
                print(f"  SKIP  127.0.0.1:{port} -- {e.strerror}", flush=True)
                s.close()
        if not self.listeners:
            raise SystemExit("could not bind any candidate port")

    def run(self):
        self.t0 = time.time()
        print(f"listening on {sorted(self.listeners)} for {self.duration:.0f}s\n", flush=True)
        self.log(event="probe_start", ports=sorted(self.listeners))
        deadline = self.t0 + self.duration
        conns = {}

        while time.time() < deadline:
            for key, _ in self.sel.select(timeout=0.5):
                kind, meta = key.data
                if kind == "listen":
                    sock, addr = key.fileobj.accept()
                    sock.setblocking(False)
                    self.conn_seq += 1
                    cid = self.conn_seq
                    conns[cid] = {"port": meta, "peer": addr, "rx": bytearray(),
                                  "opened": time.time() - self.t0, "first_rx": None}
                    self.sel.register(sock, selectors.EVENT_READ, ("conn", cid))
                    self.log(event="connect", conn=cid, port=meta, peer=f"{addr[0]}:{addr[1]}")
                else:
                    cid = meta
                    try:
                        data = key.fileobj.recv(65536)
                    except (ConnectionResetError, OSError):
                        data = b""
                    if not data:
                        self.sel.unregister(key.fileobj)
                        key.fileobj.close()
                        self.log(event="close", conn=cid, total_rx=len(conns[cid]["rx"]))
                        continue
                    c = conns[cid]
                    if c["first_rx"] is None:
                        c["first_rx"] = time.time() - self.t0
                        self.log(event="first_bytes", conn=cid, port=c["port"],
                                 delay_after_connect=round(c["first_rx"] - c["opened"], 4),
                                 n=len(data))
                    c["rx"] += data
                    self.log(event="rx", conn=cid, n=len(data),
                             hex=binascii.hexlify(data[:256]).decode())

        self.log(event="probe_end")
        self.report(conns)

    def report(self, conns):
        summary = {
            "bound_ports": sorted(self.listeners),
            "duration_s": self.duration,
            "connections": [],
        }
        lines = ["# -authsrv probe result", ""]
        if not conns:
            lines += ["**NO CONNECTIONS.** The client never opened a TCP session to 127.0.0.1 on any",
                      f"of {sorted(self.listeners)}.", "",
                      "Possible reasons, in order of likelihood:",
                      "- -authsrv is no longer honoured post-Reforged (the go/no-go answer is NO)",
                      "- the client never got as far as an auth attempt (crash / launcher gate / Steam)",
                      "- auth moved to a port outside the candidate set",
                      "- auth moved to UDP, or off TCP entirely",
                      "- the client resolves a hostname and ignores the override"]
        for cid, c in sorted(conns.items()):
            rx = bytes(c["rx"])
            summary["connections"].append({
                "conn": cid, "port": c["port"], "peer": f"{c['peer'][0]}:{c['peer'][1]}",
                "opened_at_s": round(c["opened"], 4),
                "first_bytes_at_s": None if c["first_rx"] is None else round(c["first_rx"], 4),
                "client_spoke_first": c["first_rx"] is not None,
                "bytes_received": len(rx),
                "first_64_hex": binascii.hexlify(rx[:64]).decode(),
            })
            lines += [f"## connection {cid} -- port {c['port']}",
                      f"- peer: {c['peer'][0]}:{c['peer'][1]}",
                      f"- opened at t+{c['opened']:.3f}s",
                      f"- client spoke first: {c['first_rx'] is not None}",
                      f"- bytes received: {len(rx)}", ""]
            if rx:
                lines += ["```", hexdump(rx[:512]), "```", ""]
                if len(rx) > 512:
                    lines += [f"(+{len(rx) - 512} more bytes, see raw file)", ""]
            with open(os.path.join(self.outdir, f"conn{cid}_port{c['port']}.bin"), "wb") as f:
                f.write(rx)

        with open(os.path.join(self.outdir, "events.jsonl"), "w") as f:
            for e in self.events:
                f.write(json.dumps(e) + "\n")
        with open(os.path.join(self.outdir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        report = "\n".join(lines)
        with open(os.path.join(self.outdir, "REPORT.md"), "w") as f:
            f.write(report)
        print("\n" + report, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--duration", type=float, default=90.0)
    a = ap.parse_args()
    p = Probe(a.outdir, a.duration)
    p.bind_all()
    p.run()
