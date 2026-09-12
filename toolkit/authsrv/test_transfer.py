"""SLICE-B8: the transfer, sent by us -- the portal trigger, the three messages,
the re-entry, and the area that stays on its own map.

The completion of zoning is a CLIENT question (does it re-dial, does the next
map load) and is a run. What this file pins is everything the run would
otherwise be measuring for the first time: that a portal fires only for a
player who LEFT it, that the three messages are the three the corpus shows in
the order it shows them, that 0x01A5's sockaddr is the tape rewriter's own
byte layout and its ids are this connection's, that the whole sequence
ENCODES through the real codec, that a re-entry after our own transfer is
served the map we named while a fresh entry still takes --map, and that an
area's population stays on the map its row names.
"""
import os
import socket
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import authsrv                                                   # noqa: E402
import agents                                                    # noqa: E402

# MEASURED from a green run, 2026-09-12.
LEDGER = checks.Ledger("the transfer, sent by us", floor=22)
check = checks.adopt(LEDGER)

OP_STOP = authsrv.GAME_SMSG_AGENT_STOP_MOVING
OP_XFER = authsrv.GAME_SMSG_GAME_SERVER_TRANSFER
OP_MAP = authsrv.GAME_SMSG_MAP_UPDATE_CURRENT


class FakeWorld:
    def __init__(self, tables):
        self._t = tables

    def rows(self, kind):
        return dict(self._t.get(kind, {}))

    def get(self, kind, key):
        return self._t[kind][key]


def fresh(pos, map_id=148, world_id=777, player_id=4242):
    sent = []
    state = {"pos": pos, "map_id": map_id, "world_id": world_id,
             "player_id": player_id, "plane": 0}
    return (lambda op, vals, label="", **kw: sent.append((op, list(vals) if not isinstance(vals, (bytes, bytearray)) else vals, label)),
            state, sent)


def main():
    saved = (authsrv.agents.WORLD, list(authsrv.TRANSFER_HOSTS),
             authsrv.TRANSFER_PORT, dict(authsrv.TRANSFERS_ISSUED),
             authsrv.PORTALS)
    portal = {"map": 148, "x": 1000.0, "y": 0.0, "radius": 200.0,
              "to_map": 146, "enabled": True}
    world = FakeWorld({
        "portal": {"gate": dict(portal),
                   "off": dict(portal, enabled=False, to_map=999),
                   "elsewhere": dict(portal, map=146, to_map=148)},
        "map": {"146": {"explorable": True, "file_id": 1},
                "148": {"explorable": False, "file_id": 1}},
        "area": {"corridor": {"map_id": 168}},
        "spawn": {},
    })
    try:
        authsrv.agents.WORLD = world
        authsrv.TRANSFER_HOSTS[:] = ["127.0.0.3", "127.0.0.33"]
        authsrv.TRANSFER_PORT = 6112
        authsrv.TRANSFERS_ISSUED.clear()
        authsrv.PORTALS = True

        print("1. the portal rows, per map")
        keys = [k for k, _r in authsrv.portal_rows(148)]
        check(keys == ["gate"],
              "map 148 has ONE enabled portal: the disabled row and the other "
              "map's row are not it", keys)
        check([k for k, _r in authsrv.portal_rows(146)] == ["elsewhere"],
              "and map 146 has its own", [k for k, _r in authsrv.portal_rows(146)])

        print("\n2. ARMED BY LEAVING: a portal fires only for a player who was outside")
        send, state, sent = fresh((1050.0, 0.0))          # inside at load
        fired = authsrv.portal_tick(send, state, 1, "127.0.0.3")
        check(fired is False and not sent,
              "a player who loads INSIDE the circle does not fire it -- the "
              "arrival point cannot bounce", f"fired {fired}, sent {len(sent)}")
        state["pos"] = (1230.0, 0.0)                        # outside r*1.0, inside r*1.25
        check(authsrv.portal_tick(send, state, 1, "127.0.0.3") is False
              and not state["portal_armed"].get("gate"),
              "230 u out is not yet ARMED: the re-arm band is radius x 1.25")
        state["pos"] = (1300.0, 0.0)
        authsrv.portal_tick(send, state, 1, "127.0.0.3")
        check(state["portal_armed"].get("gate") is True and not sent,
              "300 u out arms it, and arming sends nothing")
        state["pos"] = (1150.0, 0.0)
        fired = authsrv.portal_tick(send, state, 1, "127.0.0.3")
        check(fired is True and len(sent) == 3,
              "walking back in FIRES it: three messages", len(sent))
        again = authsrv.portal_tick(send, state, 1, "127.0.0.3")
        check(again is False and len(sent) == 3,
              "and never twice on one connection -- transfer_sent stands")

        print("\n3. the three messages, in the corpus's order, with this connection's ids")
        ops = [op for op, _v, _l in sent]
        check(ops == [OP_STOP, OP_XFER, OP_MAP],
              "0x0028 -> 0x01A5 -> 0x0099, the order SLICE-F8 names",
              [hex(o) for o in ops])
        check(list(sent[0][1]) == list(agents.agent_stop_moving(authsrv.PLAYER_AGENT_ID)),
              "the halt is the bare stop-ack for the PLAYER, agents' own shape",
              sent[0][1])
        x = sent[1][1]
        blob = bytes(x[0])
        fam, port = struct.unpack("<H", blob[:2])[0], struct.unpack(">H", blob[2:4])[0]
        host = socket.inet_ntoa(blob[4:8])
        check(len(blob) == 24 and fam == socket.AF_INET and port == 6112
              and blob[8:] == b"\x00" * 16,
              "0x01A5's blob is a 24-byte sockaddr_in: AF_INET little-endian, "
              "the port BIG-endian, a 16-byte zero tail -- tape.rewrite_transfer's "
              "own layout", f"fam {fam} port {port} host {host} len {len(blob)}")
        check(host == "127.0.0.33",
              "and it advertises the alias the client is NOT on -- T9's "
              "unmeasured same-endpoint re-dial, avoided", host)
        check(x[1] == 777 and x[3] == 146 and x[5] == 4242,
              "world_id, map_id and player_id are THIS connection's and the "
              "destination's -- the three fields the next VERSION frame repeats",
              x)
        check(x[4] == 1,
              "the byte after map_id is the destination row's explorable flag "
              "(146: true) -- the 1/0/1 reading, UNVERIFIED at n=3 and sent as "
              "the row says", x[4])
        check(list(sent[2][1]) == [146, 0],
              "0x0099 names the destination, in the shape every instance load "
              "sends it", sent[2][1])
        raw = authsrv.codec.encode("GAME_SMSG", OP_XFER, x)
        check(len(raw) == 39,
              "and the whole 0x01A5 ENCODES through the real codec to the 39 "
              "bytes overrides.json corrected the catalog to", len(raw))
        for op, vals, _l in (sent[0], sent[2]):
            authsrv.codec.encode("GAME_SMSG", op, vals)
        check(True, "the other two encode as well")

        print("\n4. the alias choice, and its honest fallback")
        check(authsrv.transfer_host_for("127.0.0.33") == ("127.0.0.3", True),
              "a client on the alt alias is sent back to the main one")
        authsrv.TRANSFER_HOSTS[:] = ["127.0.0.3"]
        check(authsrv.transfer_host_for("127.0.0.3") == ("127.0.0.3", False),
              "with ONE listener the only answer is the same alias, flagged "
              "unchanged -- the send prints T9's NOT FOUND rather than hiding it")
        authsrv.TRANSFER_HOSTS[:] = ["127.0.0.3", "127.0.0.33"]

        print("\n5. re-entry: --map pins the FIRST entry, not a map we handed out")
        check(authsrv.transfer_reentry(777, 4242, 146) is True,
              "the VERSION frame repeating our 0x01A5's ids IS a re-entry")
        check(authsrv.transfer_reentry(777, 4242, 148) is False
              and authsrv.transfer_reentry(1, 2, 146) is False,
              "another map, or another session's ids, is not")

        print("\n6. an area is its MAP's population")
        recorded = []
        st = {"agents": {}, "pos": (0.0, 0.0), "pathmap": None, "map_id": 148}
        n = authsrv.spawn_population(
            lambda op, vals, label="", **kw: recorded.append(op),
            st, (0.0, 0.0, 0), 1, area="corridor")
        check(n == 0 and not recorded,
              "--area corridor (map 168) places NOTHING on an instance serving "
              "map 148 -- the transfer serves other maps on one process",
              f"placed {n}, sent {len(recorded)}")

        print("\n7. --no-portals is a revert")
        authsrv.PORTALS = False
        send, state, sent = fresh((1300.0, 0.0))
        authsrv.portal_tick(send, state, 1, "127.0.0.3")
        state["pos"] = (1150.0, 0.0)
        check(authsrv.portal_tick(send, state, 1, "127.0.0.3") is False
              and not sent,
              "with PORTALS off nothing arms and nothing fires")
    finally:
        (authsrv.agents.WORLD, hosts, authsrv.TRANSFER_PORT, issued,
         authsrv.PORTALS) = saved
        authsrv.TRANSFER_HOSTS[:] = hosts
        authsrv.TRANSFERS_ISSUED.clear()
        authsrv.TRANSFERS_ISSUED.update(issued)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
