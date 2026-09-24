"""World-map travel: which maps our world offers as travel destinations, the
unlock bitmap that makes the client's world map show them, and the refusal a
travel request gets. DESKWORK-D1 step 7, studies/cmsg/FINDINGS.md
DESKWORK-D1 "World-map travel".

Pure: reads content map rows (passed in as `world`, i.e. agents.WORLD), and
returns the travelable set, a bitmap, or a refusal reason. No server import,
no sockets -- the whole policy is tested against content on a bare machine, and
the retail 0x00B1 batches on disk are replayed against it.

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
unlike a portal transfer where the moving body is stopped first.

WHAT THE UNLOCK STATE IS. s2c 0x0094 carries FIVE map-id bitmaps (schema 148:
five array32; handler 0x0091eb10 -> 0x008122f0 copies them into charCtx
+0x5cc/+0x5dc/+0x5ec/+0x5fc/+0x60c through Array::CopyBits 0x00473550 -- no
create-once, no ordering gate, asserts only Array:130 bounds, so it is safe to
send in any load state). On every live tape arr0-3 are EMPTY and arr4 holds map
ids, bit index == map id: across 22 connections EVERY map the client then sent
c2s 0x00B1 to had its arr4 bit set at load, and the set GROWS as the session
unlocks more (20260817T231139 map 281 clear at load, set the next day once
visited). Our server sends NO 0x0094 today (grep authsrv.py), so the client's
unlocked set starts empty and the world map offers nothing to click -- which is
why travel needed the unlock state, not only the arm. The client already models
this id space: c2s 0x0148 MISSION_MASK_REPORT reports one bit per map id back
(authsrv.mission_mask_bytes). LABELS: arr4 == the unlocked map set is OBSERVED
(bit == map id, every travel destination set, over 22 connections); arr0-3 are
UNVERIFIED (empty on every tape) so we send them empty; that arr4 IS the world
map's travel gate is CORROBORATED by that correlation and stays RECONSTRUCTION
until the owner opens M on our client and sees our outposts.
"""


def _enabled(row):
    return bool(row.get("enabled", True))


def _explorable(row):
    return bool(row.get("explorable", False))


def travelable_maps(world):
    """Sorted map ids our world offers as travel destinations: enabled and NOT
    explorable (the world map lists outposts/towns; an explorable is entered by
    walking out of one). The operator's content is the world -- Rurik is a mod
    platform -- so every enabled non-explorable map row is a destination."""
    out = []
    for key, row in world.rows("map").items():
        try:
            mid = int(key)
        except (TypeError, ValueError):
            continue
        if _enabled(row) and not _explorable(row):
            out.append(mid)
    return sorted(set(out))


def is_travelable(world, map_id):
    return int(map_id) in set(travelable_maps(world))


def unlock_bitmap_words(world, n_words):
    """arr4 of s2c 0x0094: `n_words` dwords, bit index == map id, set for every
    travelable map. A map id at or past the bitmap's width (n_words*32) is
    SKIPPED and returned in the overflow list, never dropped silently -- a
    too-narrow mask would offer fewer maps than the content declares.
    -> (words, overflow)."""
    n = int(n_words)
    words = [0] * n
    overflow = []
    cap = n * 32
    for mid in travelable_maps(world):
        if 0 <= mid < cap:
            words[mid // 32] |= (1 << (mid % 32))
        else:
            overflow.append(mid)
    return words, overflow


def plan_travel(world, cur_map, dest_map):
    """The refusal gate for a c2s 0x00B1 to `dest_map` from `cur_map`.
    -> (ok, reason): ok True means send 0x01D9 then the transfer; ok False
    means send NOTHING (retail's refusal reply is NOT FOUND on any tape).

    Refuses, with nothing sent:
      * the map you are already on (no tape shows retail travelling to it);
      * a map with no enabled content row (the transfer would strand the
        client on an unbuilt map -- the reason 0x00B1 was DROPPED_ON_PURPOSE);
      * an explorable (you reach one by walking out of an outpost, not from
        the world map).
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
    return True, None
