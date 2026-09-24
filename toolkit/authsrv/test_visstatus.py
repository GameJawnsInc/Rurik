"""The inventory panel's per-slot DISPLAY MODE -- s2c 0x00EF CHAR_VISIBILITY_FLAGS,
c2s 0x0057 SET_CHAR_VISIBILITY_FLAGS, and the regime rule that strips a hidden
piece from the body's 0x006E (DESKWORK-D1, the owner's answer, 2026-09-23;
studies/cmsg/FINDINGS.md "The display mode"; visstatus.py's docstring for the
binary reads; the fix pass of the same day for what the two reviews moved).

    python toolkit/authsrv/test_visstatus.py

  * §1 THE CLIENT'S TABLES AND ARITHMETIC (bare-machine): the four kind masks
    partition the CHAR_STATS_VIS byte; every menu row of every kind round-trips
    through the client's writer and its code lookup (0x008ECD90 reproduced);
    retail's default 0xFF draws the eye on all four and the unsent zero draws
    the circled bar on all four (the defect reproduced); the regime rule (the
    high bit in a town, the low bit in a field) with a KNOWN-BAD swapped rule
    that disagrees; the code->string table read through its jump table against
    the KNOWN-BAD address order; the drop-down's own sends pass check_request
    and three malformed ones are refused; strip_visual and slot_changes in both
    regimes with a no-change control; load_flags (the store's int, else 0xFF,
    never zero -- the KNOWN-BAD zero draws the defect) and load_message; the
    0x006F write filter with a KNOWN-BAD unfiltered arm.
  * §2 RETAIL'S WIRE (vault-gated; LEDGER.skip on a bare machine, ~10 s): over
    every origin=LIVE game connection, 0x00EF once per connection on >= 90,
    never twice, always [0xFF, 0xFF], always right after 0x00E9; c2s 0x0057
    absent; the OWN body (its armour ids all in the connection's equipped bag)
    carries its helm on every outpost and field load under Always Show --
    consistent with the strip, not discriminating; the confound named (every
    bare-headed outpost body is a stranger, every field body the owner's own);
    the OBSERVED per-regime tailoring of the own array: no outpost 0x006E
    carries a weapon, every field body whose bag holds one carries it.
  * §3 THE SERVER: source locks (the dispatch arm behind VISIBILITY_STATUS_ENABLED,
    the 0x00EF send right after 0x00E9's through load_message, the byte loaded
    through load_flags, the 0x006E build through visible_worn over the ONE
    worn-array copy, the item batch through visible_slot_writes, the flag in
    serverargs.py and main()); the real handler driven with a fake send in a
    town and in a field -- the 0x00EF echo, the 0x006F for the head when the
    current regime's view changed and nothing when it did not, three refusals
    sending nothing; the EQUIP PATH in a field under Hide in Combat Areas: an
    unequip and re-equip of the helm sends its 0x006F as item 0 (the revert arm
    KNOWN-BAD: item back on the body), an Always-Show helm passes, a town equip
    has no 0x006F to filter; the revert arm on the 0x006E; --persist through a
    scratch store, the byte restored by load_flags, the store's validation
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

led = checks.Ledger("display mode (DESKWORK-D1, the owner's answer)", floor=64)  # 2026-09-24 (CLEANUP-3's review, RV-1: the town equip re-cut to the zeroed pair, +1 for its KNOWN-BAD arm), from the green run with RURIK_VAULT pointed at an empty directory (the bare-machine core); section 2's 10 ride the vault (74 vaulted); 63 / 73 at the 2026-09-23 fix pass

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
       and all(vs.CODE_ICON[vs.mode_code(0x00, k)] == 3 for k in range(4)),
       "the UNSENT ZERO draws icon 3, the circled bar (Always Hide), beside all four -- ours on "
       "20260923T185124, reproduced")
led.ok([vs.CODE_ICON[c] for c, _b in vs.KIND_MENU[HEAD]] == [0, 1, 2, 3]
       and [vs.ICON_LABEL[i] for i in range(4)] == ["Always Show", "Hide in Towns and Outposts",
                                                    "Hide in Combat Areas", "Always Hide"],
       "the headgear menu's four rows draw the four icons in the owner's screenshot order")
# the code->string table THROUGH the jump table (0x008ECE3C; the menu builder's copy at
# 0x008ED080 agrees): the headgear's rows read 0x32C, 0x32D, 0x32E, 0x330 and the cape's
# own third and fourth rows 0x32F, 0x331. KNOWN-BAD: the case bodies in ADDRESS order,
# which is what the landing shipped for codes 3/4/5 (the fix pass, EVR-VIS-3).
head_strings = [vs.CODE_STRING_ID[c] for c, _b in vs.KIND_MENU[HEAD]]
cape_strings = [vs.CODE_STRING_ID[c] for c, _b in vs.KIND_MENU[vs.KIND_CAPE]]
led.ok(head_strings == [0x32C, 0x32D, 0x32E, 0x330] and cape_strings == [0x32C, 0x32D, 0x32F, 0x331]
       and vs.CODE_STRING_ID[1] == 0x15BDE and len(set(vs.CODE_STRING_ID.values())) == 7,
       "CODE_STRING_ID through the jump table: the headgear menu 0x32C/0x32D/0x32E/0x330, the "
       "cape's third and fourth 0x32F/0x331, seven distinct strings", f"{head_strings} {cape_strings}")
led.ok(tuple(vs.CODE_STRING_ID[c] for c in range(7)) != vs.CODE_STRING_ADDRESS_ORDER
       and sorted(vs.CODE_STRING_ID.values()) == sorted(vs.CODE_STRING_ADDRESS_ORDER)
       and [c for c in range(7) if vs.CODE_STRING_ID[c] != vs.CODE_STRING_ADDRESS_ORDER[c]] == [3, 4, 5],
       "KNOWN-BAD: the address order is the same seven strings with codes 3, 4 and 5 permuted -- "
       "the landing's table, and the pin can tell them apart")


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
# the load (the fix pass, ENG-VIS-4): what the burst starts a connection with
led.ok(vs.load_flags(None) == 0xFF and vs.load_flags(0xF7) == 0xF7 and vs.load_flags(0) == 0
       and vs.load_flags("eye") == 0xFF and vs.load_flags(True) == 0xFF and vs.load_flags(0x1F7) == 0xF7,
       "load_flags: no row value -> 0xFF (retail's 95 of 95), a stored int kept to the eight bits, "
       "a string or a bool -> the default; a stored 0 is honoured (Always Hide everywhere is a mode)")
led.ok(vs.load_message(vs.load_flags(None)) == [0xFF, 0xFF] and vs.load_message(0xF7) == [0xF7, 0xFF]
       and vs.load_message(0x1F7) == [0xF7, 0xFF],
       "load_message: [flags, 0xFF] -- retail's own [0xFF, 0xFF] for a fresh character, the "
       "stored byte under the full mask otherwise")
bad_default = vs.load_message(0)
led.ok(bad_default == [0, 0xFF] and all(vs.CODE_ICON[vs.mode_code(bad_default[0], k)] == 3 for k in range(4))
       and vs.load_message(vs.load_flags(None)) != bad_default,
       "KNOWN-BAD: a burst defaulting to ZERO would send [0, 0xFF] -- the circled bar on all four, "
       "the defect's own bytes -- and the default the burst loads is not that")
# the 0x006F write filter (the fix pass, ENG-VIS-1/EVR-VIS-2)
led.ok(vs.slot_kind(6) == HEAD and vs.slot_kind(7) == C_BODY and vs.slot_kind(8) == C_HEAD
       and vs.slot_kind(0) is None and vs.slot_kind(1) is None and vs.slot_kind(5) is None,
       "slot_kind: visuals 6/7/8 belong to the headgear and the two costumes; the hands and the "
       "armour carry no display mode")
led.ok(vs.filter_slot_writes([(6, 7), (0, 1), (7, 8)], 0xFB, True) == ([(6, 0), (0, 1), (7, 8)], [(HEAD, 6, 7)])
       and vs.filter_slot_writes([(6, 7), (0, 1), (7, 8)], 0xFB, False) == ([(6, 7), (0, 1), (7, 8)], [])
       and vs.filter_slot_writes([(6, 7)], 0xF7, False) == ([(6, 0)], [(HEAD, 6, 7)])
       and vs.filter_slot_writes([(7, 8), (8, 9)], 0xCF, True) == ([(7, 0), (8, 9)], [(C_BODY, 7, 8)]),
       "filter_slot_writes: a helm entering visual 6 in a field under Hide in Combat Areas goes out "
       "as 0 while the weapon and a costume pass; the same helm passes in a town; Hide in Towns "
       "withholds it in a town; a hidden costume body's slot 7 goes out as 0")
led.ok(vs.filter_slot_writes([(6, 7), (7, 8)], 0xFF, True) == ([(6, 7), (7, 8)], [])
       and vs.filter_slot_writes([(6, 0)], 0x00, True) == ([(6, 0)], []),
       "CONTROL and VACUITY: Always Show passes every write; an unequip's 0 is never 'hidden'")
led.ok([(s, i) for s, i in [(6, 7)]] != vs.filter_slot_writes([(6, 7)], 0xFB, True)[0],
       "KNOWN-BAD: the unfiltered batch (the landing's equip path) disagrees with the filter -- the "
       "item stays in the write")

# ---- §2 retail's wire ------------------------------------------------------------------
import vaultpath                                             # noqa: E402
import livewire                                              # noqa: E402
live_root = vaultpath.vault_path("captures", "live")
conns = list(livewire.live_connections()) if os.path.isdir(live_root) else []
if not conns:
    led.skip("section 2, retail's wire", f"no live captures under {live_root}")
if conns:
    per_conn = []
    decoded = 0
    ef_vals = collections.Counter()
    prev_ops = collections.Counter()
    c2s_vis = 0
    own_head = collections.Counter()      # (regime, own helm carried?)
    who_bare = collections.Counter()      # (regime, own/other, head0?)
    weapon = collections.Counter()        # (regime, own/other, bag has weapon?, visual 0 carries?)
    for capdir, gf in conns:
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        decoded += 1 if ok else 0
        s2c = [(op, v) for (_t, d, op, v) in merged if d == "s2c"]
        c2s_vis += sum(1 for (_t, d, op, _v) in merged if d == "c2s" and op == VIS_C2S)
        regime = next((v[3] for op, v in s2c if op == 0x0199 and len(v) > 3), None)
        efs = [i for i, (op, _v) in enumerate(s2c) if op == VIS_S2C]
        per_conn.append(len(efs))
        for i in efs:
            ef_vals[(s2c[i][1][1], s2c[i][1][2])] += 1
            prev_ops[s2c[i - 1][0] if i else None] += 1
        # the OWN body: the 0x006E whose armour ids (visual 2..5) all sit in this
        # connection's EQUIPPED bag (0x013F type 2 declares it; 0x013E/0x014B place
        # items; 0x0152 swaps two) -- the item study's join, test_itemmoves 1c
        equipped, cells, own_ids = set(), {}, set()
        for op, v in s2c:
            if op == 0x013F and int(v[2]) == 2:
                equipped.add(int(v[4]))
            elif op in (0x013E, 0x014B):
                cells[int(v[2])] = (int(v[3]), int(v[4]))
            elif op == 0x0152:
                a, b = cells.get(int(v[2])), cells.get(int(v[3]))
                if a and b:
                    cells[int(v[2])], cells[int(v[3])] = b, a
            elif op == 0x006E and len(v) > 10:
                eq = {i: s for i, (b, s) in cells.items() if b in equipped}
                armour = [int(x) for x in v[4:8] if int(x)]
                is_own = bool(armour) and all(a in eq for a in armour)
                if is_own:
                    own_ids.add(v[1])
                own = is_own or v[1] in own_ids
                who_bare[(regime, "own" if own else "other", int(v[8]) == 0)] += 1
                bag_weapon = [i for i, s in eq.items() if s == 0] if own else []
                weapon[(regime, "own" if own else "other", bool(bag_weapon), int(v[2]) != 0)] += 1
                if own:
                    bag_head = [i for i, s in eq.items() if s == 4]
                    own_head[(regime, int(v[8]) in bag_head if bag_head else None)] += 1
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
    o_own, f_own = own_head[(0, True)], own_head[(1, True)]
    led.ok(o_own >= 40 and f_own >= 40 and own_head[(0, False)] == 0 and own_head[(1, False)] == 0
           and own_head[(0, None)] == 0 and own_head[(1, None)] == 0,
           f"the OWN body carries its equipped helm on {o_own} of {o_own + own_head[(0, False)]} "
           f"outpost loads and {f_own} of {f_own + own_head[(1, False)]} field loads, all under "
           f"[0xFF, 0xFF] -- consistent with the regime strip, NOT discriminating", f"{dict(own_head)}")
    bare_other = who_bare[(0, "other", True)]
    led.ok(bare_other >= 500 and who_bare[(0, "own", True)] == 0
           and who_bare[(1, "other", True)] + who_bare[(1, "other", False)] == 0
           and who_bare[(1, "own", False)] >= 40,
           f"THE CONFOUND named: every bare-headed outpost body ({bare_other}) is a STRANGER whose "
           f"mode the tape does not carry, and every field body ({who_bare[(1, 'own', False)]}) is the "
           f"owner's own Always-Show body -- the landing's 756-vs-0 compared strangers in towns with "
           f"the owner in fields", f"{dict(who_bare)}")
    o_bodies = sum(n for (r, _w, _b, _c), n in weapon.items() if r == 0)
    o_armed = sum(n for (r, _w, _b, c), n in weapon.items() if r == 0 and c)
    o_own_bag = weapon[(0, "own", True, False)]
    f_carry = weapon[(1, "own", True, True)]
    f_miss = weapon[(1, "own", True, False)]
    led.ok(o_bodies >= 2000 and o_armed == 0 and o_own_bag >= 40 and f_carry >= 30 and f_miss == 0,
           f"OBSERVED per-regime tailoring of the own array, on the WEAPON: no outpost 0x006E carries "
           f"one ({o_armed} of {o_bodies} bodies; the owner's own {o_own_bag} with a weapon in the "
           f"equipped bag among them), and every field body whose bag holds one carries it "
           f"({f_carry} of {f_carry + f_miss})", f"{dict(weapon)}")
    led.ok(weapon[(1, "own", False, False)] >= 1 and weapon[(1, "own", False, True)] == 0,
           f"...and a field load with NO bag weapon carries none ({weapon[(1, 'own', False, False)]}): "
           f"the array reflects the bag, not a constant")
    led.ok(decoded == len(conns), f"every connection decoded ok ({decoded} of {len(conns)})")
    led.ok(o_own + f_own == who_bare[(0, "own", False)] + who_bare[(1, "own", False)],
           "the own-body tallies agree between the head join and the census (one identification)")

# ---- §3 the server ---------------------------------------------------------------------
SRC = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
ARGS = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()


def func_src(name):
    start = SRC.find(f"\ndef {name}(")
    end = SRC.find("\ndef ", start + 1)
    return SRC[start:end] if start > 0 else ""


arm = SRC.find("elif opcode == GAME_CMSG_SET_CHAR_VISIBILITY_FLAGS:")
led.ok(arm > 0 and "if VISIBILITY_STATUS_ENABLED:" in SRC[arm:arm + 500]
       and "handle_visibility_flags(values, send, state, conn_id)" in SRC[arm:arm + 600]
       and "--no-visibility-status" in SRC[arm:arm + 900],
       "SOURCE LOCK: the dispatch arm for 0x0057 exists, is gated by VISIBILITY_STATUS_ENABLED and "
       "names the revert flag when it ignores")
players = func_src("_handle_request_players")
e9 = players.find("send(GAME_SMSG_CHARACTER_UPDATE_FACTIONS, player_attrs,")
ef = players.find("send(GAME_SMSG_CHAR_VISIBILITY_FLAGS,", e9)
led.ok(0 < e9 < ef < e9 + 1400 and "if VISIBILITY_STATUS_ENABLED:" in players[e9:ef]
       and 'visstatus.load_message(state["vis_flags"])' in players[ef:ef + 200],
       "SOURCE LOCK: the load's 0x00EF send sits right after the 0x00E9 send (retail's position "
       "relative to 0x00E9, 95 of 95), behind the flag, and its payload is load_message's",
       f"e9 {e9} ef {ef}")
led.ok('state["vis_flags"] = visstatus.load_flags((_ps_row or {}).get("vis_flags"))' in players
       and players.find("visstatus.load_flags(") < e9,
       "SOURCE LOCK: the burst loads the byte through load_flags from the store row, before the send")
w6e = players.find("send(GAME_SMSG_UPDATE_AGENT_VISUAL_EQUIPMENT,\n             [PLAYER_AGENT_ID] + worn,")
led.ok(w6e > 0 and "worn = visible_worn(player_worn_array(state), state, conn_id)" in players[w6e - 1200:w6e]
       and "itemstore.worn_array(" not in players
       and 'itemstore.worn_array(state["items"], EQUIPPED_BAG_ID,' in func_src("player_worn_array"),
       "SOURCE LOCK: the player's 0x006E is visible_worn over player_worn_array -- the ONE copy of "
       "the dressed array, which reads itemstore.worn_array; the burst has no inline copy left")
led.ok("\n    out = visible_slot_writes(batch, state, conn_id)\n" in func_src("_item_moves_commit")
       and "for op, vals, label in out:" in func_src("_item_moves_commit")
       and func_src("_item_moves_commit").count("visible_slot_writes(") == 1
       and all("_item_moves_commit(send, state, conn_id, batch, changes," in func_src(h)
               for h in ("handle_item_move", "handle_equip_item", "handle_item_move_by_id")),
       "SOURCE LOCK: every item handler commits through _item_moves_commit, which sends the batch "
       "through visible_slot_writes ONCE -- one gate for every consumer -- and sends what it returned "
       "(the CLEANUP-3 review's RV-3 re-shaped the loop)")
led.ok('"--no-visibility-status"' in ARGS and "a.no_visibility_status" in SRC
       and "VISIBILITY_STATUS_ENABLED = False" in SRC,
       "SOURCE LOCK: the revert flag is declared in serverargs.py and wired in main()")

saved = (authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST, authsrv.VISIBILITY_STATUS_ENABLED,
         authsrv.TOWN_WEAPON_STRIP_ENABLED, authsrv.TOWN_ARMOUR_VISUALS_ENABLED)
try:
    authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST = True, False, False
    authsrv.VISIBILITY_STATUS_ENABLED = True
    # The TOWN WEAPON (DESKWORK-D1, 2026-09-23; townweapon.py) shares visible_worn and
    # visible_slot_writes with the display mode and zeroes the hands in a town. This
    # section's subject is the display mode's own slots (6/7/8), so the hands' rule is
    # held off here and its composition with the mode is test_townweapon.py's §3.
    authsrv.TOWN_WEAPON_STRIP_ENABLED = False
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

    # THE EQUIP PATH (the fix pass, ENG-VIS-1/EVR-VIS-2): a field, the dress's layout,
    # headgear Hide in Combat Areas; the helm dragged to the backpack (0x004F) and
    # double-clicked back (0x0030). The landing sent the re-equip's 0x006F with the
    # helm in it -- the world body re-helmed while the doll and the load hid it.
    MOVE, EQUIP = authsrv.GAME_CMSG_ITEM_MOVE, authsrv.GAME_CMSG_EQUIP_ITEM
    ITEM_LOC = authsrv.GAME_SMSG_ITEM_CHANGE_LOCATION

    def drive_reequip(flags, enabled, outpost):
        authsrv.VISIBILITY_STATUS_ENABLED = enabled
        authsrv.OUTPOST, authsrv.EXPLORABLE = outpost, not outpost
        s = {"agents": {}, "char_uuid": UUID, "map_id": 145}
        authsrv.item_layout_begin(s, 0)
        s["vis_flags"] = flags
        helm = authsrv.player_worn_array(s)[6]
        got, snd = fake_send_factory()
        authsrv.handle_item_move([MOVE, 4, 2, 1], snd, s, 0)       # the head's bag cell 4 -> backpack 1
        authsrv.handle_equip_item([EQUIP, helm], snd, s, 0)         # and back on
        return helm, got, authsrv.player_worn_array(s), authsrv.visible_worn(authsrv.player_worn_array(s), s)

    helm, got, after, vis = drive_reequip(0xFB, True, outpost=False)
    led.ok(helm and after[6] == helm and vis[6] == 0
           and [op for op, _v in got] == [ITEM_LOC, SLOT_VIS, ITEM_LOC, SLOT_VIS]
           and got[1][1] == [1, 6, 0] and got[3][1] == [1, 6, 0],
           f"FIELD, Hide in Combat Areas, unequip then re-equip the helm (item {helm}): the bag "
           f"wears it again, the load's array would hide it, and the re-equip's 0x006F goes out as "
           f"[player, 6, 0] -- the body stays bare", f"{got}")
    helm2, got2, _after2, _vis2 = drive_reequip(0xFB, False, outpost=False)
    led.ok(helm2 == helm and [op for op, _v in got2] == [ITEM_LOC, SLOT_VIS, ITEM_LOC, SLOT_VIS]
           and got2[3][1] == [1, 6, helm],
           "KNOWN-BAD (--no-visibility-status, the landing's path): the same re-equip sends 0x006F "
           "[player, 6, helm] -- the world body re-helmed under a mode that hides it", f"{got2}")
    helm3, got3, _a3, vis3 = drive_reequip(0xFF, True, outpost=False)
    led.ok(helm3 == helm and got3[3][1] == [1, 6, helm] and vis3[6] == helm,
           "CONTROL: under Always Show the re-equip's 0x006F carries the helm -- the filter passes "
           "a shown piece", f"{got3}")
    authsrv.TOWN_ARMOUR_VISUALS_ENABLED = True
    helm4, got4, _a4, vis4 = drive_reequip(0xF7, True, outpost=True)
    led.ok(helm4 == helm and [op for op, _v in got4] == [ITEM_LOC, SLOT_VIS, ITEM_LOC, SLOT_VIS]
           and got4[1][1] == [1, 6, 0] and got4[3][1] == [1, 6, 0] and vis4[6] == 0,
           "TOWN, Hide in Towns: since CLEANUP-3 (2026-09-24) an outpost ARMOUR equip plans its 0x006F "
           "(retail's outpost armour writes) and the filter sends both as [player, 6, 0] -- the display "
           "mode's idempotent zero, neither dropped nor the item -- while the load's array hides the helm "
           "too (the review's RV-1: this check pinned the pre-lane 0x014B alone and was RED at the lane's "
           "commit)", f"{got4}")
    authsrv.TOWN_ARMOUR_VISUALS_ENABLED = False
    helm5, got5, _a5, vis5 = drive_reequip(0xF7, True, outpost=True)
    led.ok(helm5 == helm and [op for op, _v in got5] == [ITEM_LOC, ITEM_LOC] and vis5[6] == 0,
           "KNOWN-BAD (--no-town-armour-visuals): the same town equip rides no 0x006F -- every run before "
           "CLEANUP-3 -- so the filter has nothing to withhold; and it disagrees with the default", f"{got5}")
    authsrv.TOWN_ARMOUR_VISUALS_ENABLED = True
    authsrv.OUTPOST, authsrv.EXPLORABLE = False, True
    plain = [(ITEM_LOC, [1, 2, 3, 4], "x"), (SLOT_VIS, [1, 0, 9], "hand"), (SLOT_VIS, [2, 6, 9], "npc")]
    led.ok(authsrv.visible_slot_writes(plain, {"vis_flags": 0x00}) == plain,
           "visible_slot_writes leaves the hands and another agent's slot 6 alone even under Always "
           "Hide everywhere -- the filter is the PLAYER's visuals 6/7/8 only")
    # the revert arm on the load's array
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
        led.ok(store.character_vis_flags(UUID) is None
               and vs.load_flags(store.character_by_uuid(UUID).get("vis_flags")) == 0xFF,
               "a fresh row stores no byte, and load_flags reads that as retail's default, not zero")
        authsrv.OUTPOST, authsrv.EXPLORABLE, authsrv.PERSIST = True, False, True
        stp = {"map_id": 148, "char_uuid": UUID, "charstore_game": store}
        sent.clear()
        authsrv.handle_visibility_flags([VIS_C2S, 0x4, 0xC], send, stp, 9)
        back = charstore.Store.open("visstatus@rurik.invalid", base=base)
        led.ok(back.character_vis_flags(UUID) == 0xF7,
               "--persist: the handler writes vis_flags 0xF7 and a fresh open reads it back")
        row = back.character_by_uuid(UUID)
        led.ok(vs.load_flags(row.get("vis_flags")) == 0xF7
               and vs.load_message(vs.load_flags(row.get("vis_flags"))) == [0xF7, 0xFF],
               "the burst's own load (load_flags over the row, load_message) restores 0xF7 and "
               "would send 0x00EF [0xF7, 0xFF]")
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
     authsrv.VISIBILITY_STATUS_ENABLED, authsrv.TOWN_WEAPON_STRIP_ENABLED,
     authsrv.TOWN_ARMOUR_VISUALS_ENABLED) = saved

ov = json.load(open(os.path.join(os.path.dirname(HERE), "..", "schema", "overrides.json"),
                    encoding="utf-8"))["channels"]
led.ok(ov["GAME_CMSG"].get("87", {}).get("name") == "SET_CHAR_VISIBILITY_FLAGS"
       and ov["GAME_SMSG"].get("239", {}).get("name") == "CHAR_VISIBILITY_FLAGS"
       and "0x00814BE0" in ov["GAME_SMSG"]["239"]["why"]
       and "RECONSTRUCTION" in ov["GAME_CMSG"]["87"]["why"],
       "the schema names both halves and their `why` carries the writer and the label")

sys.exit(led.verdict())
