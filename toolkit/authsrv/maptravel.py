"""World-map travel: which maps our world offers as travel destinations, the
unlock bitmap that makes the client's world map show them, the refusal a
travel request gets, and the shape of retail's reply. DESKWORK-D1 step 7,
studies/cmsg/FINDINGS.md DESKWORK-D1 "World-map travel" (corrected by the fix
pass the same day; the paragraph "The fix pass" there names what moved).

Pure: reads content map rows (passed in as `world`, i.e. agents.WORLD) and an
optional exclusion dict, and returns the travelable set, a bitmap, a payload,
a refusal reason or a predicate's verdict. No server import, no sockets -- the
whole policy is tested against content on a bare machine, and the retail
0x00B1 batches on disk are replayed against it.

WHAT c2s 0x00B1 MAP_TRAVEL IS (OBSERVED, 10 of 10 on 10 live connections over
6 captures; toolkit/authsrv/c2striage.py, studies/cmsg DESKWORK-D1 step 3):
[map_id, 0, 0, 0, 1] (word, byte, word, byte, byte) -- the world map's travel
to another outpost. The three trailing zeroes and the trailing 1 are constant
across all 10 (region / district / language / a flag are candidates; UNVERIFIED,
never varied on tape). Retail answers 0x01D9 [2, 1, ''] then the transfer pair
0x01A5 GAME_SERVER_TRANSFER and 0x0099 MAP_UPDATE_CURRENT -- 10 of 10 in
sequence, 9 of 10 as the very first non-clock s2c -- then hangs up; the client
re-dials the transfer address (c2s 0x0008 every time) and loads the destination.
No 0x0028 AGENT_STOP_MOVING precedes it (the player is standing in an outpost),
unlike a portal transfer where the moving body is stopped first. Retail's
0x01D9 rides its own TCP segment 18.6-42.2 ms before the pair (10 of 10); ours
go out back to back -- the gap is UNREPRODUCED, and only worth reproducing if
the client run shows a UI race.

WHAT THE UNLOCK STATE IS. s2c 0x0094 carries FIVE map-id bitmaps (schema 148:
five array32; handler 0x0091eb10 -> 0x008122f0 copies them into charCtx
+0x5cc/+0x5dc/+0x5ec/+0x5fc/+0x60c through Array::CopyBits 0x00473550, which
REPLACES each array -- no create-once, no ordering gate, asserts only Array:130
bounds, so it is safe to send in any load state). MEASURED over the 96 live
connections (29 sightings): arr4 is a map-id bitmap, bit index == map id,
27 dwords wide on 29 of 29; arr0-3 are empty on 27 of 29, and on the two
Kamadan (449) logins arr0 and arr1 carry 18 dwords with bit 544 set --
UNVERIFIED what they are (mission completion is a candidate), so we send all
four empty as a labelled choice. arr4 is the client's KNOWN-MAPS set, not an
outpost list: ids our content marks explorable are set in it (280 Isle of the
Nameless on 14 of 29, 146 Lakeside County on 5 of 29). Offering only enabled
non-explorable content maps is OUR policy (RECONSTRUCTION), not an observation.

THERE ARE TWO WRITERS OF arr4, and the fix pass found the second. s2c 0x0099
MAP_UPDATE_CURRENT's handler 0x0091ec20 -> 0x00812600 loads the SAME store
(charCtx+0x2c + 0x60c) and calls 0x0059d130, which ends `bts eax, edx` at
0x0059d239 -- ONE bit set, word map_id>>5, bit map_id&31 (OBSERVED in the
binary). Our server has always sent 0x0099 [map, 0] at every load and in every
transfer, so the client's arr4 was NEVER empty before this arc: it held the
current map plus every map zoned into. What 0x0094 adds is the OTHER served
outposts, all at once. Retail's cadence: 0x0094 once per LOGIN, on the first
map-loading connection (28 of 29 first-of-capture, the 29th a second login in
20260919T103604), 0 of 61 transfer arrivals, sitting after 0x0199 and before
the fog pair 0x008B/0x008A on 29 of 29; in-session unlocks then arrive as
0x0099 [map, 1] (one on tape: [281, 1] on 20260817T231139, 24 s before the
owner travelled there). The travel join: every one of the 10 destinations had
its bit set BEFORE the click -- 9 by the login's 0x0094, the tenth (281) by
that 0x0099 -- so "arr4 gates the world map" is CORROBORATED by the join and
RECONSTRUCTION until the owner's M press; the click's OTHER preconditions are
the getters inside 0x004A78C0 (an immediate-vs-deferred branch, not a drop).
"""
import re


def _enabled(row):
    return bool(row.get("enabled", True))


def _explorable(row):
    return bool(row.get("explorable", False))


def _spawn_known(row):
    """A content row whose spawn is the (0, 0) PLACEHOLDER has no spawn point
    ([map.194] and [map.55] say so in their own notes: "(0, 0) is a placeholder,
    not a coordinate"); a travel there would put the body wherever (0, 0)
    happens to be, off the mesh for most maps. Withheld from the offer."""
    try:
        return not (float(row.get("spawn_x", 0.0)) == 0.0
                    and float(row.get("spawn_y", 0.0)) == 0.0)
    except (TypeError, ValueError):
        return False


def travelable_maps(world, exclude=None):
    """Sorted map ids our world offers as travel destinations: enabled, NOT
    explorable (the world map lists outposts/towns; an explorable is entered by
    walking out of one), with a KNOWN spawn (not the (0, 0) placeholder), and
    not in `exclude` -- the server's {map_id: reason} of destinations whose
    navmesh did not load at startup (a travel there would serve no collision).
    The operator's content is the world -- Rurik is a mod platform -- so every
    such map row is a destination."""
    ex = exclude or {}
    out = []
    for key, row in world.rows("map").items():
        try:
            mid = int(key)
        except (TypeError, ValueError):
            continue
        if mid in ex:
            continue
        if _enabled(row) and not _explorable(row) and _spawn_known(row):
            out.append(mid)
    return sorted(set(out))


def is_travelable(world, map_id, exclude=None):
    return int(map_id) in set(travelable_maps(world, exclude))


def unlock_bitmap_words(world, n_words, exclude=None):
    """arr4 of s2c 0x0094: `n_words` dwords, bit index == map id, set for every
    travelable map. A map id at or past the bitmap's width (n_words*32) is
    SKIPPED and returned in the overflow list, never dropped silently -- a
    too-narrow mask would offer fewer maps than the content declares.
    -> (words, overflow)."""
    n = int(n_words)
    words = [0] * n
    overflow = []
    cap = n * 32
    for mid in travelable_maps(world, exclude):
        if 0 <= mid < cap:
            words[mid // 32] |= (1 << (mid % 32))
        else:
            overflow.append(mid)
    return words, overflow


def unlock_message(world, n_words, exclude=None):
    """The whole s2c 0x0094 the load sends: -> (payload, label, overflow).
    payload is the five arrays with arr0-3 EMPTY (UNVERIFIED on tape, see the
    module docstring) and arr4 the travelable bitmap. One function so the
    server's send site and the test read the same shape."""
    words, overflow = unlock_bitmap_words(world, n_words, exclude)
    payload = [[], [], [], [], words]
    nbits = sum(bin(w).count("1") for w in words)
    label = f"MAP_TRAVEL_UNLOCK [{nbits} destination(s) in arr4]"
    return payload, label, overflow


def unlock_payload_ok(payload, words):
    """Is `payload` the 0x0094 shape retail's arr4 reading needs -- the bitmap
    in the FIFTH array and the first four empty? A payload that put the words
    in arr0 (the client's +0x5cc store, whatever it is) fails this."""
    return (isinstance(payload, list) and len(payload) == 5
            and all(payload[i] == [] for i in range(4))
            and payload[4] == list(words) and any(words))


def plan_travel(world, cur_map, dest_map, exclude=None):
    """The refusal gate for a c2s 0x00B1 to `dest_map` from `cur_map`.
    -> (ok, reason): ok True means send 0x01D9 then the transfer; ok False
    means send NOTHING (retail's refusal reply is NOT FOUND on any tape: no
    live 0x00B1 went unanswered, none targeted the current map).

    Refuses, with nothing sent:
      * the map you are already on (no tape shows retail travelling to it);
      * a map with no enabled content row (the transfer would strand the
        client on an unbuilt map -- the reason 0x00B1 was DROPPED_ON_PURPOSE);
      * an explorable (you reach one by walking out of an outpost, not from
        the world map);
      * a row with the (0, 0) placeholder spawn (no spawn point is known);
      * a destination in `exclude` -- its navmesh did not load at startup.
    """
    try:
        dest = int(dest_map)
    except (TypeError, ValueError):
        return False, f"malformed destination {dest_map!r}"
    if cur_map is not None:
        try:
            if dest == int(cur_map):
                return False, f"already on map {dest}"
        except (TypeError, ValueError):
            pass
    row = world.rows("map").get(str(dest))
    if row is None:
        return False, f"map {dest} has no content row"
    if not _enabled(row):
        return False, f"map {dest} is disabled"
    if _explorable(row):
        return False, f"map {dest} is an explorable (walk out of an outpost)"
    if not _spawn_known(row):
        return False, f"map {dest} has no spawn point (the (0, 0) placeholder)"
    ex = exclude or {}
    if dest in ex:
        return False, f"map {dest} is withheld: {ex[dest]}"
    return True, None


# Retail's reply to an accepted travel, in order (OBSERVED 10 of 10): the
# travel-ready byte pair, then the transfer pair. No 0x0028 in the batch.
TRAVEL_BATCH = (0x01D9, 0x01A5, 0x0099)


def travel_batch_ok(ops):
    """Is `ops` (the s2c opcodes a travel produced, in send order) exactly
    retail's batch? False for a reordered batch, a missing 0x01D9, or a stray
    0x0028 -- the shapes a naive arm produces."""
    return list(ops) == list(TRAVEL_BATCH)


def arrival_skips_unlock(arrivals, key, map_id, now, ttl=300.0):
    """Is the load for `key` (world_id, player_id) landing on `map_id` the
    client coming BACK from a transfer we sent, so the login's 0x0094 must not
    be resent? Retail sends 0x0094 once per login and never on an arrival
    (0 of 61 on tape); a resend would REPLACE arr4 and wipe the bits 0x0099
    accumulated for maps outside our travelable set. `arrivals` is the
    server's {key: (dest_map, issued_at)} written at send_transfer time; the
    entry is CONSUMED here whatever the answer (one shot), so a relaunch that
    asks for the same map later gets its 0x0094. An entry older than `ttl`
    seconds is stale (the re-dial never came) and is ignored."""
    got = arrivals.pop(key, None)
    if not got:
        return False
    dest, issued_at = got
    try:
        if float(now) - float(issued_at) > float(ttl):
            return False
        return int(dest) == int(map_id)
    except (TypeError, ValueError):
        return False


# Every spelling a second sender of 0x0094 could take in a server source; the
# one-sender guard counts these across toolkit/authsrv/*.py (non-test). A
# duplicate sender of unlock state wiped a skill library and crashed a client
# on 2026-09-15; with two writers of arr4 the question is sharper still.
UNLOCK_SEND_RE = re.compile(
    r"send\(\s*(GAME_SMSG_MAP_TRAVEL_UNLOCK|0x0094|0x94|148)\s*,")
