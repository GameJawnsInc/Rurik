"""Per-process TCP snapshots straight from iphlpapi.GetExtendedTcpTable.

Dependency-free on purpose, the same choice as gwpe.py. The alternative -- shelling
out to `netstat -ano` or `Get-NetTCPConnection` -- costs 30-80 ms per sample, and a
connect that is refused instantly on loopback lives for far less than that. A
sampler built on those tools reports "no sockets" for a process that is dialling
several times a second, which is exactly the false conclusion that cost this
project an hour on 2026-08-05.

Reading this table is cheap enough to poll at 20 ms without loading a core.
"""

import ctypes
import socket
from ctypes import wintypes

TCP_TABLE_OWNER_PID_ALL = 5
AF_INET = 2

# Not an exhaustive MIB_TCP_STATE list -- these are the ones a client connect
# passes through. SYN_SENT is the one that matters: a connect to an unreachable
# ROUTED address sits there for ~21 s, while a connect to a closed LOOPBACK port
# is reset in microseconds and may never be sampled at all.
STATES = {
    1: "CLOSED", 2: "LISTEN", 3: "SYN_SENT", 4: "SYN_RCVD", 5: "ESTABLISHED",
    6: "FIN_WAIT1", 7: "FIN_WAIT2", 8: "CLOSE_WAIT", 9: "CLOSING",
    10: "LAST_ACK", 11: "TIME_WAIT", 12: "DELETE_TCB",
}


class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwState", wintypes.DWORD),
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    ]


_iphlpapi = ctypes.WinDLL("iphlpapi")
_ROW_SIZE = ctypes.sizeof(MIB_TCPROW_OWNER_PID)


def _ip(dw):
    # The address is already in network byte order inside the DWORD.
    return socket.inet_ntoa(dw.to_bytes(4, "little"))


def _port(dw):
    # Only the low word is the port, and it is network byte order.
    return socket.ntohs(dw & 0xFFFF)


def connections(pid=None):
    """Every IPv4 TCP row, optionally filtered to one pid.

    Returns dicts with state/local/remote. Never raises on a transient failure --
    the table can be resized between the sizing call and the read, and a sampler
    that dies mid-run is worse than one that drops a sample.
    """
    size = wintypes.DWORD(0)
    _iphlpapi.GetExtendedTcpTable(None, ctypes.byref(size), False, AF_INET,
                                  TCP_TABLE_OWNER_PID_ALL, 0)
    buf = ctypes.create_string_buffer(size.value)
    if _iphlpapi.GetExtendedTcpTable(buf, ctypes.byref(size), False, AF_INET,
                                     TCP_TABLE_OWNER_PID_ALL, 0) != 0:
        return []

    n = int.from_bytes(buf[:4], "little")
    out = []
    for i in range(n):
        off = 4 + i * _ROW_SIZE
        if off + _ROW_SIZE > len(buf):
            break
        row = MIB_TCPROW_OWNER_PID.from_buffer_copy(buf, off)
        if pid is not None and row.dwOwningPid != pid:
            continue
        out.append({
            "state": STATES.get(row.dwState, str(row.dwState)),
            "local": f"{_ip(row.dwLocalAddr)}:{_port(row.dwLocalPort)}",
            "remote": f"{_ip(row.dwRemoteAddr)}:{_port(row.dwRemotePort)}",
            "remote_port": _port(row.dwRemotePort),
            "pid": row.dwOwningPid,
        })
    return out


if __name__ == "__main__":
    import sys
    want = int(sys.argv[1]) if len(sys.argv) > 1 else None
    for c in connections(want):
        print(f"  {c['state']:12s} {c['local']:24s} -> {c['remote']:24s} pid {c['pid']}")
