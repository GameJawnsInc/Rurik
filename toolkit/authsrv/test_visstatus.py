"""The inventory panel's per-slot DISPLAY MODE -- s2c 0x00EF CHAR_VISIBILITY_FLAGS,
c2s 0x0057 SET_CHAR_VISIBILITY_FLAGS, and the regime rule that strips a hidden
piece from the body's 0x006E (DESKWORK-D1, the owner's answer, 2026-09-23;
studies/cmsg/FINDINGS.md "The display mode"; visstatus.py's docstring for the
binary reads).

    python toolkit/authsrv/test_visstatus.py

  * §1 THE CLIENT'S TABLES AND ARITHMETIC (bare-machine): the four kind masks
    partition the CHAR_STATS_VIS byte; every menu row of every kind round-trips
    through the client's writer and its code lookup (0x008ECD90 reproduced);
    retail's default 0xFF draws the eye on all four and the unsent zero draws
    the circled bar on all four (the defect reproduced); the regime rule (the
    high bit in a town, the low bit in a field) with a KNOWN-BAD swapped rule
    that disagrees; the drop-down's own sends pass check_request and three
    malformed ones are refused; strip_visual and slot_changes in both regimes
    with a no-change control.
  * §2 RETAIL'S WIRE (vault-gated; LEDGER.skip on a bare machine, ~60 s): over
    every origin=LIVE game connection, 0x00EF once per connection on >= 90,
    never twice, always [0xFF, 0xFF], always right after 0x00E9; c2s 0x0057
    absent; the regime census -- outpost bodies bare-headed >= 500 times, field
    bodies never (n >= 40); the same for 0x0048's cape bit.
  * §3 THE SERVER: source locks (the dispatch arm behind VISIBILITY_STATUS_ENABLED,
    the 0x00EF send right after 0x00E9's, the 0x006E build through visible_worn,
    the flag in serverargs.py and main()); the real handler driven with a fake
    send in a town and in a field -- the 0x00EF echo, the 0x006F for the head
    when the current regime's view changed and nothing when it did not, three
    refusals sending nothing; the revert arm (KNOWN-BAD: the helm stays on the
    body under a mode that hides it, and no 0x0057 arm); --persist through a
    scratch store, the byte restored by the burst's rule, the store's validation
    refusing 256 and a string; the two schema names.
"""
import collections
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import charstore                                             # noqa: E402
import visstatus as vs                                       # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("display mode (DESKWORK-D1, the owner's answer)", floor=47)  # 2026-09-23, from the green run with RURIK_VAULT pointed at an empty directory (the bare-machine core); section 2's 9 ride the vault (56 vaulted)

VIS_S2C, VIS_C2S = 0x00EF, 0x0057
assert (VIS_S2C, VIS_C2S) == (authsrv.GAME_SMSG_CHAR_VISIBILITY_FLAGS,
                              authsrv.GAME_CMSG_SET_CHAR_VISIBILITY_FLAGS)
SLOT_VIS = authsrv.GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT           # 0x006F
HEAD, C_BODY, C_HEAD = vs.KIND_HEADGEAR, vs.KIND_COSTUME_BODY, vs.KIND_COSTUME_HEAD
UUID = "55555555555555555555555555555555"


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals)))
    return sent, send


# ---- §1 the client's tables and arithmetic ---------------------------------------------
masks = [vs.KIND_MASK[k] for k in sorted(vs.KIND_MASK)]
led.ok(masks == [0x03, 0x0C, 0x30, 0xC0]
       and sum(masks) == vs.FLAG_BITS == 0xFF
       and all((a & b) == 0 for i, a in enumerate(masks) for b in masks[i + 1:]),
       "the four kind masks (0xBA38D4) are 0x03/0x0C/0x30/0xC0: disjoint, and together the "
       "eight CHAR_STATS_VIS bits", f"{masks}")
led.ok(vs.DEFAULT_FLAGS == 0xFF and all(len(vs.KIND_MENU[k]) == 4 for k in vs.KIND_MASK),
       "retail's default is 0xFF and every kind's menu has four rows (0x008ECD00's tables)")
for kind in sorted(vs.KIND_MASK):
    codes = [c for c, _b in vs.KIND_MENU[kind]]
    ok = True
    for code in codes:
        bits = vs.mode_bits(kind, code)
        flags = vs.apply(vs.DEFAULT_FLAGS, bits, vs.KIND_MASK[kind])
        ok = ok and vs.mode_code(flags, kind) == code and (bits & ~vs.KIND_MASK[kind]) == 0
    led.ok(ok, f"kind {kind} ({vs.KIND_NAMES[kind]}): each of its menu codes {codes} round-trips "
               f"through the writer (0x00814BE0) and the code lookup (0x008ECD90)")
led.ok([vs.mode_code(0xFF, k) for k in range(4)] == [0, 0, 1, 1]
       and all(vs.CODE_ICON[vs.mode_code(0xFF, k)] == 0 for k in range(4)),
       "0xFF (retail's load) draws icon 0, the eye, beside all four slots -- the owner's retail "
       "screenshot")
led.ok([vs.mode_code(0x00, k) for k in range(4)] == [6, 3, 3, 3]
       and all(vs.CODE_ICON[vs.mode_code(0x00, k)] == 3 for k in range(4))
       and vs.mode_code(vs.CODE_NONE and 0x00, HEAD) != vs.CODE_NONE,
       "the UNSENT ZERO draws icon 3, the circled bar (Always Hide), beside all four -- ours on "
       "20260923T185124, reproduced")
led.ok([vs.CODE_ICON[c] for c, _b in vs.KIND_MENU[HEAD]] == [0, 1, 2, 3]
       and [vs.ICON_LABEL[i] for i in range(4)] == ["Always Show", "Hide in Towns and Outposts",
                                                    "Hide in Combat Areas", "Always Hide"],
       "the headgear menu's four rows draw the four icons in the owner's screenshot order")
def swapped_shown(flags, kind, explorable):
    """KNOWN-BAD: the pair read the other way round (low bit = town)."""
    bit = 2 * int(kind) + (1 if explorable else 0)
    return bool((int(flags) >> bit) & 1)


led.ok(vs.shown(0x08, HEAD, explorable=False) and not vs.shown(0x08, HEAD, explorable=True)
       and not vs.shown(0x04, HEAD, explorable=False) and vs.shown(0x04, HEAD, explorable=True),
       "the regime rule (0x005384B0): the headgear's HIGH bit (0x8) shows it in a town, its LOW "
       "bit (0x4) in a field")
led.ok(swapped_shown(0x08, HEAD, explorable=False) != vs.shown(0x08, HEAD, explorable=False)
       and swapped_shown(0x04, HEAD, explorable=True) != vs.shown(0x04, HEAD, explorable=True),
       "KNOWN-BAD: the swapped rule disagrees on both half-modes (the check can go red)")
led.ok(vs.hidden_kinds(0xFF, False) == [] and vs.hidden_kinds(0xFF, True) == []
       and vs.hidden_kinds(0x00, False) == [0, 1, 2, 3]
       and vs.hidden_kinds(0xF7, False) == [HEAD] and vs.hidden_kinds(0xF7, True) == []
       and vs.hidden_kinds(0xFB, True) == [HEAD] and vs.hidden_kinds(0xFB, False) == [],
       "hidden_kinds: 0xFF hides nothing anywhere, 0x00 everything, 0xF7 (headgear Hide in Towns) "
       "the headgear in a town only, 0xFB (Hide in Combat) in a field only")
sends_ok = all(vs.check_request(vs.mode_bits(k, c), vs.KIND_MASK[k]) is None
               for k in vs.KIND_MASK for c, _b in vs.KIND_MENU[k])
led.ok(sends_ok, "every send the drop-down can make -- (bits & mask, mask) for each row of each "
                 "kind -- passes check_request")
led.ok(vs.check_request(0x4, 0x0) is not None and vs.check_request(0x5, 0xC) is not None
       and vs.check_request(0x100, 0x100) is not None and vs.check_request(0x0, 0xC) is None,
       "refused: an empty mask, a value outside its mask, a bit beyond the eight; Always Hide "
       "(value 0 under a mask) is a request")
led.ok(vs.apply(0xFF, 0x4, 0xC) == 0xF7 and vs.apply(0xF7, 0xC, 0xC) == 0xFF
       and vs.apply(0xFF, 0x0, 0xC) == 0xF3 and vs.apply(0x00, 0x100, 0x100) == 0x00,
       "apply is the client's `(flags & ~mask) | value` kept to eight bits")
worn = [1, 0, 3, 4, 5, 6, 7, 8, 9]
out, hid = vs.strip_visual(worn, 0xFF, False)
out2, hid2 = vs.strip_visual(worn, 0xFF, True)
led.ok(out == worn and hid == [] and out2 == worn and hid2 == [],
       "CONTROL: 0xFF strips nothing from the array in either regime")
out, hid = vs.strip_visual(worn, 0xF7, False)
outf, hidf = vs.strip_visual(worn, 0xF7, True)
led.ok(out == [1, 0, 3, 4, 5, 6, 0, 8, 9] and hid == [(HEAD, 6, 7)] and outf == worn and hidf == [],
       "headgear Hide in Towns (0xF7): visual slot 6 leaves the array in a town, stays in a field",
       f"{out} {hid} / {outf} {hidf}")
out, hid = vs.strip_visual(worn, 0xF3, False)
outf, hidf = vs.strip_visual(worn, 0xF3, True)
led.ok(out[6] == 0 and outf[6] == 0 and hid == hidf == [(HEAD, 6, 7)],
       "headgear Always Hide (0xF3): slot 6 leaves the array in both regimes")
out, hid = vs.strip_visual(worn, 0x0F, False)
led.ok(out == [1, 0, 3, 4, 5, 6, 7, 0, 0] and hid == [(C_BODY, 7, 8), (C_HEAD, 8, 9)],
       "both costumes Always Hide (0x0F): slots 7 and 8 leave the array; the armour stays")
out, hid = vs.strip_visual(worn, 0xFC, False)
led.ok(out == worn and hid == [], "the cape (0xFC: kind 0 hidden) touches no visual slot -- it is "
                                  "0x0048's, not the array's")
out, hid = vs.strip_visual([1, 0, 3, 4, 5, 6, 0, 0, 0], 0x00, False)
led.ok(out == [1, 0, 3, 4, 5, 6, 0, 0, 0] and hid == [],
       "VACUITY: a hidden kind whose slot is already empty reports nothing hidden")
led.ok(vs.slot_changes(0xFF, 0xF7, worn, False) == [(HEAD, 6, 0)]
       and vs.slot_changes(0xFF, 0xF7, worn, True) == []
       and vs.slot_changes(0xF7, 0xFF, worn, False) == [(HEAD, 6, 7)]
       and vs.slot_changes(0xFF, 0xF7, [1, 0, 3, 4, 5, 6, 0, 0, 0], False) == []
       and vs.slot_changes(0xFF, 0xCF, worn, True) == [(C_BODY, 7, 0)]
       and vs.slot_changes(0xFF, 0xFF, worn, False) == [],
       "slot_changes: the head's 0x006F in a town on Hide in Towns and nothing in a field; the "
       "item back on Always Show; nothing for an empty slot; a worn costume's slot 7; no change "
       "no write")
led.ok(vs.describe(0xFF) == "cape Always Show, headgear Always Show, costume body Always Show, "
                            "costume head Always Show"
       and vs.mode_label(0xF7, HEAD) == "Hide in Towns and Outposts"
       and vs.mode_label(0xFB, HEAD) == "Hide in Combat Areas"
       and vs.mode_label(0xF3, HEAD) == "Always Hide",
       "the log labels name the four modes")
led.ok(vs.kinds_in(0xC) == [HEAD] and vs.kinds_in(0xFF) == [0, 1, 2, 3] and vs.kinds_in(0x30) == [C_BODY],
       "kinds_in reads a mask back to its kinds")

# ---- §2 retail's wire ------------------------------------------------------------------
import vaultpath                                             # noqa: E402
import livewire                                              # noqa: E402
live_root = vaultpath.vault_path("captures", "live")
conns = list(livewire.live_connections()) if os.path.isdir(live_root) else []
if not conns:
    led.skip("section 2, retail's wire", f"no live captures under {live_root}")
if conns:
    per_conn = []
    ef_vals = collections.Counter()
    prev_ops = collections.Counter()
    c2s_vis = 0
    head0 = collections.Counter()
    cape0 = collections.Counter()
    for capdir, gf in conns:
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        s2c = [(op, v) for (_t, d, op, v) in merged if d == "s2c"]
        c2s_vis += sum(1 for (_t, d, op, _v) in merged if d == "c2s" and op == VIS_C2S)
        regime = next((v[3] for op, v in s2c if op == 0x0199 and len(v) > 3), None)
        efs = [i for i, (op, _v) in enumerate(s2c) if op == VIS_S2C]
        per_conn.append(len(efs))
        for i in efs:
            ef_vals[(s2c[i][1][1], s2c[i][1][2])] += 1
            prev_ops[s2c[i - 1][0] if i else None] += 1
        for op, v in s2c:
            if op == 0x006E and len(v) > 10:
                head0[(regime, v[8] == 0)] += 1
            if op == 0x0048 and len(v) > 2:
                cape0[(regime, v[2] == 0)] += 1
    n_one = sum(1 for n in per_conn if n == 1)
    led.ok(len(conns) >= 90 and n_one >= 90 and max(per_conn) == 1 and per_conn.count(0) <= 2,
           f"0x00EF once per connection: {n_one} of {len(conns)} live connections carry exactly one, "
           f"{per_conn.count(0)} none, none two",
           f"{collections.Counter(per_conn)}")
    led.ok(set(ef_vals) == {(0xFF, 0xFF)},
           f"every retail 0x00EF is [0xFF, 0xFF] -- every slot Always Show ({sum(ef_vals.values())})",
           f"{ef_vals}")
    led.ok(set(prev_ops) == {0x00E9},
           f"every retail 0x00EF immediately follows 0x00E9 CHARACTER_UPDATE_FACTIONS "
           f"({prev_ops[0x00E9]} of {sum(prev_ops.values())})", f"{prev_ops}")
    led.ok(c2s_vis == 0, "c2s 0x0057 is on NO retail tape (the drop-down was never used live): the "
                         "reply is RECONSTRUCTION", f"{c2s_vis}")
    o_head0, o_head = head0[(0, True)], head0[(0, False)]
    f_head0, f_head = head0[(1, True)], head0[(1, False)]
    led.ok(o_head0 >= 500 and f_head0 == 0 and f_head >= 40,
           f"0x006E's head slot is empty on {o_head0} of {o_head0 + o_head} OUTPOST bodies and "
           f"{f_head0} of {f_head0 + f_head} FIELD bodies -- the regime pattern of a server-side "
           f"strip", f"{dict(head0)}")
    o_c0, o_c = cape0[(0, True)], cape0[(0, False)]
    f_c0, f_c = cape0[(1, True)], cape0[(1, False)]
    led.ok(o_c0 >= 500 and f_c0 == 0 and f_c >= 40,
           f"0x0048's cape bit is 0 on {o_c0} of {o_c0 + o_c} OUTPOST bodies and {f_c0} of "
           f"{f_c0 + f_c} FIELD bodies -- the same pattern on the cape's own message",
           f"{dict(cape0)}")
    led.ok(o_head0 < o_head0 + o_head and o_c0 < o_c0 + o_c,
           "and neither outpost share is 100% -- the strip is per player, not per regime alone")
    led.ok(sum(per_conn) == sum(ef_vals.values()) == sum(prev_ops.values()),
           "the three 0x00EF tallies agree")
    led.ok(len(per_conn) == len(conns), f"every connection was decoded ({len(conns)})")

# ---- §3 the server ---------------------------------------------------------------------
SRC = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
ARGS = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
arm = SRC.find("elif opcode == GAME_CMSG_SET_CHAR_VISIBILITY_FLAGS:")
led.ok(arm > 0 and "if VISIBILITY_STATUS_ENABLED:" in SRC[arm:arm + 500]
       and "handle_visibility_flags(values, send, state, conn_id)" in SRC[arm:arm + 600]
       and "--no-visibility-status" in SRC[arm:arm + 900],
       "SOURCE LOCK: the dispatch arm for 0x0057 exists, is gated by VISIBILITY_STATUS_ENABLED and "
       "names the revert flag when it ignores")
e9 = SRC.find("send(GAME_SMSG_CHARACTER_UPDATE_FACTIONS, player_attrs,")
ef = SRC.find("send(GAME_SMSG_CHAR_VISIBILITY_FLAGS,", e9)
led.ok(0 < e9 < ef < e9 + 1200 and "if VISIBILITY_STATUS_ENABLED:" in SRC[e9:ef],
       "SOURCE LOCK: the load's 0x00EF send sits right after the 0x00E9 send (retail's position, "
       "95 of 95) and behind the flag", f"e9 {e9} ef {ef}")
w6e = SRC.find("send(GAME_SMSG_UPDATE_AGENT_VISUAL_EQUIPMENT,\n             [PLAYER_AGENT_ID] + worn,")
led.ok(w6e > 0 and "worn = visible_worn(worn, state, conn_id)" in SRC[w6e - 800:w6e],
       "SOURCE LOCK: the player's 0x006E array goes through visible_worn just before its send")
led.ok('"--no-visibility-status"' in ARGS and "a.no_visibility_status" in SRC
       and "VISIBILITY_STATUS_ENABLED = False" in SRC,
       "SOURCE LOCK: the revert flag is declared in serverargs.py and wired in main()")

saved = (authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST, authsrv.VISIBILITY_STATUS_ENABLED)
try:
    authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST = True, False, False
    authsrv.VISIBILITY_STATUS_ENABLED = True
    st = {"map_id": 148}
    dressed = authsrv.player_worn_array(st)
    head_item = dressed[6]
    led.ok(head_item and dressed[0] and not st.get("items"),
           f"the launch constants dress a head at visual 6 (item {head_item}) and a weapon at 0",
           f"{dressed}")
    led.ok(authsrv.visible_worn(dressed, st) == dressed,
           "a fresh state (no flags key) dresses the full array -- the default is Always Show")
    sent, send = fake_send_factory()
    authsrv.handle_visibility_flags([VIS_C2S, 0x4, 0xC], send, st, 7)
    led.ok(st["vis_flags"] == 0xF7 and sent == [(VIS_S2C, [0x4, 0xC]), (SLOT_VIS, [1, 6, 0])],
           "TOWN, headgear -> Hide in Towns [0x4, 0xC]: the state takes 0xF7, the client gets "
           "0x00EF [0x4, 0xC] then 0x006F [player, 6, 0] -- the helm leaves the body", f"{sent}")
    led.ok(authsrv.visible_worn(dressed, st) == dressed[:6] + [0] + dressed[7:],
           "...and the next 0x006E build in this town leaves the head out")
    sent.clear()
    authsrv.handle_visibility_flags([VIS_C2S, 0xC, 0xC], send, st, 7)
    led.ok(st["vis_flags"] == 0xFF and sent == [(VIS_S2C, [0xC, 0xC]), (SLOT_VIS, [1, 6, head_item])],
           "TOWN, Always Show [0xC, 0xC]: 0x00EF then 0x006F [player, 6, head] -- the helm returns",
           f"{sent}")
    sent.clear()
    authsrv.handle_visibility_flags([VIS_C2S, 0x8, 0xC], send, st, 7)
    led.ok(st["vis_flags"] == 0xFB and sent == [(VIS_S2C, [0x8, 0xC])],
           "TOWN, Hide in Combat Areas [0x8, 0xC]: 0x00EF alone -- the town's view did not change",
           f"{sent}")
    sent.clear()
    authsrv.handle_visibility_flags([VIS_C2S, 0x0, 0xC], send, st, 7)
    led.ok(st["vis_flags"] == 0xF3 and sent == [(VIS_S2C, [0x0, 0xC]), (SLOT_VIS, [1, 6, 0])],
           "TOWN, Always Hide [0x0, 0xC]: 0x00EF then the head's 0x006F to 0", f"{sent}")
    sent.clear()
    for bad in ([VIS_C2S, 0x5, 0xC], [VIS_C2S, 0x0, 0x0], [VIS_C2S, 0x100, 0x100], [VIS_C2S, 0x4]):
        authsrv.handle_visibility_flags(bad, send, st, 7)
    led.ok(sent == [] and st["vis_flags"] == 0xF3,
           "REFUSED, nothing sent, state untouched: bits outside the mask, an empty mask, a bit "
           "beyond the eight, a short request")
    # the field
    authsrv.OUTPOST, authsrv.EXPLORABLE = False, True
    stf = {"map_id": 148}
    sent.clear()
    authsrv.handle_visibility_flags([VIS_C2S, 0x4, 0xC], send, stf, 8)
    led.ok(stf["vis_flags"] == 0xF7 and sent == [(VIS_S2C, [0x4, 0xC])]
           and authsrv.visible_worn(dressed, stf) == dressed,
           "FIELD, Hide in Towns [0x4, 0xC]: 0x00EF alone, and the field's 0x006E keeps the helm",
           f"{sent}")
    sent.clear()
    authsrv.handle_visibility_flags([VIS_C2S, 0x8, 0xC], send, stf, 8)
    led.ok(stf["vis_flags"] == 0xFB and sent == [(VIS_S2C, [0x8, 0xC]), (SLOT_VIS, [1, 6, 0])]
           and authsrv.visible_worn(dressed, stf)[6] == 0,
           "FIELD, Hide in Combat Areas [0x8, 0xC]: 0x00EF then the head's 0x006F to 0, and the "
           "field's 0x006E leaves it out", f"{sent}")
    # the revert arm
    authsrv.VISIBILITY_STATUS_ENABLED = False
    stx = {"map_id": 148, "vis_flags": 0x00}
    led.ok(authsrv.visible_worn(dressed, stx) == dressed,
           "KNOWN-BAD (--no-visibility-status): with every mode Always Hide the body still wears "
           "the helm -- today's behaviour, reproduced")
    authsrv.VISIBILITY_STATUS_ENABLED = True
    # --persist
    base = tempfile.mkdtemp(prefix="visstatus-test-")
    try:
        store = charstore.Store.open("visstatus@rurik.invalid", base=base)
        store.ensure_character(UUID, "Vis Tester")
        store.save()
        led.ok(store.character_vis_flags(UUID) is None,
               "a fresh row stores no byte: absence is retail's default, not zero")
        authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST = True, False, True
        stp = {"map_id": 148, "char_uuid": UUID, "charstore_game": store}
        sent.clear()
        authsrv.handle_visibility_flags([VIS_C2S, 0x4, 0xC], send, stp, 9)
        back = charstore.Store.open("visstatus@rurik.invalid", base=base)
        led.ok(back.character_vis_flags(UUID) == 0xF7,
               "--persist: the handler writes vis_flags 0xF7 and a fresh open reads it back")
        row = back.character_by_uuid(UUID)
        restored = vs.DEFAULT_FLAGS
        if row is not None and isinstance(row.get("vis_flags"), int):
            restored = int(row["vis_flags"]) & vs.FLAG_BITS
        led.ok(restored == 0xF7, "the burst's rule (the store's int, else the default) restores 0xF7")
        led.ok(store.set_character_vis_flags("no-such-uuid", 0x10) is None,
               "no row, nothing stored, None")
        try:
            store.set_character_vis_flags(UUID, 256)
            led.ok(False, "the setter refuses 256")
        except ValueError:
            led.ok(True, "the setter refuses 256 (CHAR_STATS_VIS is eight bits)")
        path = charstore.path_for("visstatus@rurik.invalid", base=base)
        data = json.load(open(path, encoding="utf-8"))
        data["characters"][UUID]["vis_flags"] = "eye"
        json.dump(data, open(path, "w", encoding="utf-8"))
        try:
            charstore.Store.open("visstatus@rurik.invalid", base=base)
            led.ok(False, "validation refuses a string vis_flags")
        except ValueError:
            led.ok(True, "validation refuses a string vis_flags")
        data["characters"][UUID]["vis_flags"] = 300
        json.dump(data, open(path, "w", encoding="utf-8"))
        try:
            charstore.Store.open("visstatus@rurik.invalid", base=base)
            led.ok(False, "validation refuses 300")
        except ValueError:
            led.ok(True, "validation refuses 300")
    finally:
        shutil.rmtree(base, ignore_errors=True)
finally:
    (authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST,
     authsrv.VISIBILITY_STATUS_ENABLED) = saved

ov = json.load(open(os.path.join(os.path.dirname(HERE), "..", "schema", "overrides.json"),
                    encoding="utf-8"))["channels"]
led.ok(ov["GAME_CMSG"].get("87", {}).get("name") == "SET_CHAR_VISIBILITY_FLAGS"
       and ov["GAME_SMSG"].get("239", {}).get("name") == "CHAR_VISIBILITY_FLAGS"
       and "0x00814BE0" in ov["GAME_SMSG"]["239"]["why"]
       and "RECONSTRUCTION" in ov["GAME_CMSG"]["87"]["why"],
       "the schema names both halves and their `why` carries the writer and the label")

sys.exit(led.verdict())
