r"""The player's containers: retail's nine bags, and WHERE the burst sends them.

    python toolkit/authsrv/test_playerbags.py

WHY THIS FILE EXISTS. Until 2026-08-19 this server created ONE bag, and the
symptom was not a missing grid -- it was a missing PURCHASE. With a funded
purse, a priced shop and Buy rendered ENABLED, an operator watched a click on
Buy land and produce ZERO c2s traffic (`20260819T141246`). The client refuses a
purchase it has nowhere to put and refuses it LOCALLY, so ArenaNet's
"inventory full" path costs no wire message and the null looked exactly like a
missed click. Two things were wrong at once and each hid the other:

  * the bag SET was one ninth of retail's, and
  * the one bag we did send was created INSIDE `if EQUIP_WEAPON:`, so an
    inventory question silently depended on a weapon flag.

WHAT IS ASSERTED, and it is deliberately two different kinds of claim:

  1-4. `authsrv.PLAYER_BAGS` reproduces ArenaNet's own set. `invcensus.py` is
       the extractor -- ONE code path, shared with the tool a human runs, so a
       census printed by hand and a census asserted here cannot disagree. The
       corpus is not a sample here: **49 of 49 live connections carry the same
       nine (type, model, slots) triples**, so a mismatch is a defect in our
       table rather than a difference between characters.
  5-7. the SHAPE rules that hold with no vault at all -- ids unique, the
       equipped bag reachable by the id `ITEM_MOVED_TO_LOCATION` names, and the
       trailing item field 0 on every bag we send (the corpus has it nonzero on
       the type-1 backpack and NOTHING else, 49/49, always an item declared in
       the same tape; we declare no bag item, so 0 is retail's own value for
       the other five types rather than an invention).
  8-9. the SYNTAX TREE, which is where both real defects lived and neither is
       visible in a value. The burst must iterate `PLAYER_BAGS` OUTSIDE any
       `if EQUIP_WEAPON`; and no loop TARGET may shadow a name the enclosing
       handler already binds. Naming one of them `kind` overwrote the
       connection's channel discriminator with the last bag's TYPE, so every
       later c2s message missed `if kind == "game"` -- the client's
       INSTANCE_LOAD_REQUEST_SPAWN_POINT went unanswered (hung at 100% on the
       load screen) and its keep-alive was decoded as an auth message whose
       handler died on `values[3]` (`Code=007`). Two run failures, one loop
       variable, and every number in the table correct throughout.

Each positive check has a control beside it that breaks the table on purpose,
because a comparison that cannot fail is not a comparison.

The vault is required for sections 1-4 only, and their absence is a printed
`skip`, never a silent pass. Standard library only. No socket, no client.
"""
import ast
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agents  # noqa: E402
import authsrv  # noqa: E402
import checks  # noqa: E402

LEDGER = checks.Ledger("player bags vs ArenaNet's own set", floor=18)

# (type, model, slots), in retail's own send order. Duplicated here rather than
# imported from authsrv so the check has two independent sides: if someone
# edits PLAYER_BAGS, this file is what notices.
RETAIL_SHAPES = ((1, 0, 20), (2, 21, 9), (3, 6, 12),
                 (4, 7, 25), (4, 8, 25), (4, 9, 25), (4, 10, 25), (4, 11, 25),
                 (5, 5, 42))


def freeze(v):
    """Hashable copy of a decoded payload -- the modifier tail is a list of lists."""
    if isinstance(v, (list, tuple)):
        return tuple(freeze(x) for x in v)
    return v


def ours():
    """[(type, model, slots)] as authsrv would put them on the wire."""
    return [(kind, model, slots)
            for _bag, kind, model, slots, _item in authsrv.PLAYER_BAGS]


def bag_loop_sites(tree):
    """[(iterates PLAYER_BAGS, guarded by EQUIP_WEAPON)] for every for-loop.

    Structural, not textual: a `for ... in PLAYER_BAGS` whose ancestors include
    `if EQUIP_WEAPON` is the shipped bug, and it reads identically to the fix in
    a diff of values.
    """
    sites = []
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        names = {n.id for n in ast.walk(node.iter) if isinstance(n, ast.Name)}
        if "PLAYER_BAGS" not in names:
            continue
        guarded, cur = False, node
        while getattr(cur, "parent", None) is not None:
            cur = cur.parent
            if isinstance(cur, ast.If):
                if any(isinstance(n, ast.Name) and n.id == "EQUIP_WEAPON"
                       for n in ast.walk(cur.test)):
                    guarded = True
        sends = any(isinstance(n, ast.Name) and n.id == "send"
                    for n in ast.walk(node))
        sites.append((sends, guarded))
    return sites


def shadowed_by_bag_loop(tree):
    """Loop-target names the bag loop STEALS from its enclosing function.

    The bag burst is a `for` at the bottom of a thousand-line handler, and
    Python has no block scope: a target named after something the handler
    already uses silently rebinds it for the rest of the call. That is not
    hypothetical -- naming one of them `kind` overwrote the connection's
    `kind = "auth" if ... else "game"` with the last bag's TYPE, so every
    later c2s message missed `if kind == "game"`, the client's spawn request
    went unanswered and its keep-alive was decoded as an auth message whose
    handler died on `values[3]`. Two run failures from one loop variable, and
    no value in the table was wrong.
    """
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not any(isinstance(n, ast.Name) and n.id == "PLAYER_BAGS"
                   for n in ast.walk(node.iter)):
            continue
        targets = {n.id for n in ast.walk(node.target)
                   if isinstance(n, ast.Name)}
        fn = node
        while getattr(fn, "parent", None) is not None:
            fn = fn.parent
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
        inside = {id(n) for n in ast.walk(node)}
        outside = {n.id for n in ast.walk(fn)
                   if isinstance(n, ast.Name)
                   and isinstance(n.ctx, ast.Store)
                   and id(n) not in inside}
        out |= targets & outside
    return out


def main():
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    # ---- 1-4. against ArenaNet's own wire -------------------------------
    try:
        import invcensus
        rows = invcensus.bag_shapes()
    except Exception as exc:                                # pragma: no cover
        rows = []
        LEDGER.skip("1-4. the corpus sections", f"no live captures: {exc}")
    if rows:
        sets = collections.Counter(tuple(s) for _c, _n, s, _i in rows)
        LEDGER.ok(len(sets) == 1,
                  "ArenaNet sends ONE bag set, not a per-character one",
                  f"{len(sets)} distinct set(s) over {len(rows)} live "
                  f"connection(s). A second set here would mean the table "
                  f"below is a fact about one character, and every claim "
                  f"resting on it would be scoped to that character")
        theirs = list(sets.most_common(1)[0][0])
        LEDGER.ok(theirs == list(RETAIL_SHAPES),
                  "and the set this file pins IS the corpus's",
                  f"{len(theirs)} bags: {theirs}")
        LEDGER.ok(ours() == list(RETAIL_SHAPES),
                  "authsrv.PLAYER_BAGS reproduces it, in order",
                  f"{len(ours())} bags, (type, model, slots) equal "
                  f"triple-for-triple. Only these are ArenaNet's data -- the "
                  f"bag IDS are ours, because retail's are arbitrary "
                  f"per-connection handles (8..16 on one connection, "
                  f"570/496/398.. on another)")
        nonzero = [(kind, ok) for _c, _n, _s, items in rows
                   for (kind, _i), ok in items.items()]
        LEDGER.ok(nonzero and {k for k, _ok in nonzero} == {1}
                  and all(ok for _k, ok in nonzero),
                  "the trailing field is the BACKPACK'S OWN ITEM",
                  f"nonzero {len(nonzero)} time(s), on bag type(s) "
                  f"{sorted({k for k, _ok in nonzero})} and no other, and "
                  f"{sum(1 for _k, ok in nonzero if ok)}/{len(nonzero)} of "
                  f"those values are an item id DECLARED BY 0x0161 IN THE "
                  f"SAME TAPE. Guild Wars agrees: the Backpack is a real "
                  f"item, the equipped/storage/material containers are not")

        packs = invcensus.backpack_items()
        theirs_item = {freeze(d[1:]) for _c, _n, d in packs}
        ours_item = freeze(agents.named_item(
            authsrv.BACKPACK_ITEM_ID,
            agents.item_template("backpack"))[1:])
        LEDGER.ok(len(theirs_item) == 1 and packs,
                  "ArenaNet's BACKPACK item is ONE row, not a per-character one",
                  f"{len(theirs_item)} distinct declaration(s) over "
                  f"{len(packs)} connection(s), identical but for the item id, "
                  f"which is a per-connection handle like the bag ids and the "
                  f"0x0144 key")
        LEDGER.ok(ours_item in theirs_item,
                  "and content/items.toml reproduces it FIELD FOR FIELD",
                  f"file id, type, dyes, flags 0x{ours_item[6]:08X}, value, "
                  f"model, the encoded name and the single modifier word -- all "
                  f"as retail declares them. Three of these were mistyped on "
                  f"first write and the encode is what caught it, which is why "
                  f"this check exists rather than a reading of the table")

    # ---- 5-7. shape rules, no vault needed ------------------------------
    ids = [b[0] for b in authsrv.PLAYER_BAGS]
    LEDGER.ok(len(set(ids)) == len(ids) == 9,
              "nine bags, nine distinct ids",
              f"ids {ids}. ItCliBag:167's collision search walks the OWNING "
              f"inventory's m_bagArray, so a duplicate is a real collision")
    equipped = [b for b in authsrv.PLAYER_BAGS
                if b[1] == authsrv.BAG_TYPE_EQUIPPED]
    LEDGER.ok(len(equipped) == 1
              and equipped[0][0] == authsrv.EQUIPPED_BAG_ID
              and equipped[0][3] == authsrv.EQUIPPED_SLOT_COUNT
              and authsrv.EQUIPPED_SLOT_WEAPON < equipped[0][3],
              "the equipped bag is the id ITEM_MOVED_TO_LOCATION names",
              f"bag {authsrv.EQUIPPED_BAG_ID}, "
              f"{authsrv.EQUIPPED_SLOT_COUNT} slots, weapon in slot "
              f"{authsrv.EQUIPPED_SLOT_WEAPON}. The hammer is placed by id, so "
              f"renumbering this bag silently unequips it")
    stray = [b for b in authsrv.PLAYER_BAGS if b[4] and b[1] != 1]
    pack = [b for b in authsrv.PLAYER_BAGS if b[1] == 1]
    LEDGER.ok(not stray and len(pack) == 1
              and pack[0][4] == authsrv.BACKPACK_ITEM_ID,
              "the item field is set on the BACKPACK and on nothing else",
              f"backpack cites item {pack[0][4] if pack else None}, the other "
              f"{len(authsrv.PLAYER_BAGS) - 1} send 0. That is the corpus's own "
              f"rule -- nonzero on the type-1 container and no other, 49/49 an "
              f"id declared in the same tape. Sending 0 here produced eight "
              f"containers and NO Backpack on 2026-08-19")
    decl_line = min(
        (n.lineno for n in ast.walk(ast.parse(src))
         if isinstance(n, ast.Call)
         and isinstance(n.func, ast.Name) and n.func.id == "send"
         and any(isinstance(a, ast.Name) and a.id == "BACKPACK_ITEM_ID"
                 for a in ast.walk(n))
         and any(isinstance(a, ast.Name)
                 and a.id == "GAME_SMSG_CREATE_NAMED_ITEM"
                 for a in ast.walk(n))), default=None)
    loop_line = min((n.lineno for n in ast.walk(ast.parse(src))
                     if isinstance(n, ast.For)
                     and any(isinstance(x, ast.Name) and x.id == "PLAYER_BAGS"
                             for x in ast.walk(n.iter))), default=None)
    LEDGER.ok(decl_line is not None and loop_line is not None
              and decl_line < loop_line,
              "and the burst DECLARES that item before the bag that cites it",
              f"0x0161 at line {decl_line}, the bag loop at {loop_line}. A "
              f"container citing an undeclared item is the state that drew no "
              f"Backpack; retail declares it first, in the same frame")

    # ---- 8. the syntax tree: WHERE the burst sends them ------------------
    sites = bag_loop_sites(ast.parse(src))
    LEDGER.ok(len(sites) == 1 and sites[0][0],
              "the login burst iterates PLAYER_BAGS and sends each one",
              f"{len(sites)} loop site(s) over the table, "
              f"{'sending' if sites and sites[0][0] else 'NOT sending'}")
    LEDGER.ok(sites and not any(guarded for _s, guarded in sites),
              "and NOT inside `if EQUIP_WEAPON` -- the bug that shipped",
              "the equipped bag lived under that flag until 2026-08-19, so "
              "--no-weapon left the character with no containers at all and "
              "every inventory question depended on a weapon flag")

    stolen = shadowed_by_bag_loop(ast.parse(src))
    LEDGER.ok(not stolen,
              "and no loop target SHADOWS a name the handler already uses",
              "Python has no block scope, so a target named after something "
              "the enclosing handler binds rebinds it for the rest of the "
              "call. Naming one `kind` overwrote the connection's channel "
              "discriminator with the last bag's TYPE: every later c2s "
              "message missed `if kind == \"game\"`, the client's "
              "INSTANCE_LOAD_REQUEST_SPAWN_POINT went unanswered and its "
              "keep-alive was decoded as an auth message whose handler died "
              "on values[3]. Two run failures, and no value in the table was "
              f"wrong. Stolen now: {sorted(stolen) or 'none'}")

    # ---- controls: each check above can go red --------------------------
    broken = [b for b in authsrv.PLAYER_BAGS if b[1] != 1]      # no backpack
    LEDGER.ok([(k, m, s) for _b, k, m, s, _i in broken] != list(RETAIL_SHAPES),
              "CONTROL: a table with the backpack removed is REFUSED",
              f"{len(broken)} bags -- the comparison in section 3 is the one "
              f"that would have caught the shipped defect, so it must fail on "
              f"a table that carries it")
    resized = [(k, m, s + 1) for _b, k, m, s, _i in authsrv.PLAYER_BAGS]
    LEDGER.ok(resized != list(RETAIL_SHAPES),
              "CONTROL: a table with every slot count off by one is REFUSED",
              "slots are the half of the triple a plausible typo touches")
    LEDGER.ok(bag_loop_sites(ast.parse(
        "if EQUIP_WEAPON:\n"
        "    for a, b, c, d, e in PLAYER_BAGS:\n"
        "        send(1)\n")) == [(True, True)],
              "CONTROL: the guard detector SEES a loop nested under the flag",
              "otherwise section 8's second check passes because the detector "
              "is blind, not because the code is right")
    LEDGER.ok(shadowed_by_bag_loop(ast.parse(
        "def handle():\n"
        "    kind = 'game'\n"
        "    for bag_id, kind, model, slots, item in PLAYER_BAGS:\n"
        "        send(kind)\n"
        "    return kind\n")) == {"kind"},
              "CONTROL: the shadow detector SEES the bug that cost two runs",
              "this is the exact source that shipped -- `kind` bound by the "
              "handler, stolen by the loop. Without this control the check "
              "above is green because nothing looks, not because nothing "
              "shadows")
    LEDGER.ok(bag_loop_sites(ast.parse("x = 1")) == [],
              "CONTROL: and finds nothing where there is no loop",
              "a detector that reports a site in unrelated source would make "
              "the count check meaningless")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
