r"""The armour RATING: our five pieces against ArenaNet's own wire.

    python toolkit/authsrv/test_armour.py

WHY THIS FILE EXISTS. `studies/character/FINDINGS.md` §2 asked on 2026-08-06
where an item's armour rating lives, wrote that the modifier words carrying it
were "the largest hole", and closed with a plan it never ran: *send the warrior
chest with OpenTyria's three literal words and read the rating out of the
client's own item tooltip.* Two things were in the way. The words were opaque
until `studies/itemmods` decoded them on 2026-08-20 (rating = identifier 572's
argument), and **this server was not sending the armour at all** -- the
character stood in every capture bare-chested with five empty slots on the
paper doll, so there was nothing to hover.

Both are fixed, and the tooltip now reads `Armor: 25` / `Armor +20 (vs.
physical damage)` on a caged client (`20260820T125155`). What this file does is
make the claim survive without a run.

THE CHECK WORTH HAVING IS §3, and it is not about our code. Every one of these
five rows came from OpenTyria's hand-written `GmDefaultArmors` table, and
`content/items.toml` says so in place: *"NOT VERIFIED ... no capture of ours has
ever carried these bytes."* That sentence is refutable, and the live corpus
refutes it -- ArenaNet's own server sent us `0x0161` declarations for **the same
model ids**, nine sightings each, and this file requires every field to agree.
An UPSTREAM row that a capture reproduces field-for-field is no longer UPSTREAM.

`dye_colors` is compared as MEMBERSHIP rather than equality on purpose: it is
what a player dyed that instance, and retail shows four values for one model.
Requiring equality there would fail on a field that is *meant* to vary, which is
how a real agreement gets reported as a mismatch.

Sections 1, 2 and 4 hold with no vault. Section 3 declares a skip without one
rather than passing on no data.
"""
import ast
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
import agents  # noqa: E402
import authsrv  # noqa: E402
import checks  # noqa: E402
import content  # noqa: E402
import itemmods  # noqa: E402

LEDGER = checks.Ledger("armour rating", floor=16)

ARMOR_RATING = 572          # `Armor` + `%str1%: %num1%`
ARMOR_VS_TYPE = 527         # `Armor` + `%str1% +%num1%`
VS_PHYSICAL = 4             # the string 2480 `vs. physical damage`
# head[i] -> the content key holding the same fact. head[0] is the opcode and
# head[1] the per-instance item id, so neither is here.
FIELDS = {2: "file_id", 3: "item_type", 4: "dye_tint", 6: "materials",
          7: "unk1", 8: "flags", 9: "value", 10: "model_id", 11: "quantity"}
PER_INSTANCE = {5: "dye_colors"}


def decoded(row):
    out = []
    for w in row.get("modifiers", []):
        d = itemmods.decode(w)
        if not d["skipped_high"] and not d["skipped_bit18"]:
            out.append((d["identifier"], d["arg"], d["arg2"]))
    return out


def main():
    world = content.load()
    items = world.rows("item")
    armour = [key for _id, key, _slot in authsrv.STARTER_ARMOUR]

    print("\n1. the five pieces carry an armour RATING, and it is 572's argument")
    for key in armour:
        mods = dict((i, (a, b)) for i, a, b in decoded(items[key]))
        LEDGER.ok(ARMOR_RATING in mods and mods[ARMOR_RATING][0] == 25,
                  f"{key}: Armor: {mods.get(ARMOR_RATING, ('?',))[0]}",
                  f"identifier {ARMOR_RATING} argument -- the field the client "
                  f"formats through string 2438 `%str1%: %num1%` with 2372 "
                  f"`Armor`. Read off the client's own tooltip on "
                  f"20260820T125155 as `Armor: 25`")
    body = dict((i, (a, b)) for i, a, b in decoded(items["warrior_body"]))
    LEDGER.ok(ARMOR_VS_TYPE in body and body[ARMOR_VS_TYPE][0] == 20
              and VS_PHYSICAL in body,
              "and the second line is 527 + identifier 4",
              f"527 argument {body.get(ARMOR_VS_TYPE, ('?',))[0]} with "
              f"identifier {VS_PHYSICAL}, whose only string is 2480 `vs. "
              f"physical damage` -- so the pair renders `Armor +20 (vs. "
              f"physical damage)`, which is what the tooltip drew")

    print("\n2. the burst DECLARES, PLACES and DRESSES -- three different jobs")
    slots = {slot for _id, _key, slot in authsrv.STARTER_ARMOUR}
    ids = [i for i, _k, _s in authsrv.STARTER_ARMOUR]
    LEDGER.ok(slots == {2, 3, 4, 5, 6},
              "the equipped-bag slots are retail's MEASURED ones",
              f"{sorted(slots)} -- Body 2, Boots 3, Legs 4, Gloves 5, Head 6, "
              f"read off seven 0x006F per-slot writes in 20260817T183756 with "
              f"the declaring 0x015E beside each. That refuted the reading two "
              f"lineages shared, which agreed because they make the same "
              f"assumption: one witness counted twice")
    reserved = {authsrv.WEAPON_ITEM_ID, authsrv.BACKPACK_ITEM_ID}
    LEDGER.ok(len(set(ids)) == len(ids) and not (set(ids) & reserved)
              and max(ids) < authsrv.PURCHASED_ITEM_ID_BASE,
              "the item ids collide with nothing this server already mints",
              f"{ids} against weapon {authsrv.WEAPON_ITEM_ID}, backpack "
              f"{authsrv.BACKPACK_ITEM_ID} and purchases from "
              f"{authsrv.PURCHASED_ITEM_ID_BASE}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    LEDGER.ok("EQUIP_ARMOUR" in names and "STARTER_ARMOUR" in names,
              "and the burst reads both constants rather than literals",
              "a slot number written twice is a slot number that drifts")

    print("\n3. CORPUS: our rows are ArenaNet's rows, field for field")
    try:
        sys.path.insert(0, os.path.dirname(HERE))
        import vaultpath
        import cmsgstream
        live = vaultpath.require_dir("captures", "live", why="armour rows")
    except Exception as exc:
        live = None
        LEDGER.skip(f"the live corpus is not reachable ({exc}), so the one "
                    f"check that can retire these rows' UPSTREAM label -- "
                    f"ArenaNet having sent us the same bytes -- cannot run")

    if live is not None:
        ours = {r.get("model_id"): k for k, r in items.items()}
        seen = collections.defaultdict(list)
        for stamp in sorted(os.listdir(live)):
            try:
                got = cmsgstream.timed(stamp, "s2c", "game")
            except Exception:
                continue
            for _t, _c, op, v in got:
                if op != 0x161 or not v or not isinstance(v[-1], list):
                    continue
                head = [x for x in v if not isinstance(x, list)]
                if len(head) < 12 or head[10] not in ours:
                    continue
                mods = []
                for e in v[-1]:
                    x = e[0] if isinstance(e, (list, tuple)) else e
                    if isinstance(x, int):
                        d = itemmods.decode(x)
                        if not d["skipped_high"] and not d["skipped_bit18"]:
                            mods.append((d["identifier"], d["arg"], d["arg2"]))
                seen[head[10]].append((head, tuple(mods)))

        covered = [k for k in armour if items[k].get("model_id") in seen]
        LEDGER.ok(len(covered) == len(armour),
                  "retail sent us all five of these exact models",
                  f"{len(covered)}/{len(armour)}, "
                  f"{sum(len(seen[items[k]['model_id']]) for k in covered)} "
                  f"sightings in total. This is what makes the comparison "
                  f"possible at all and it was not planned for -- the rows "
                  f"came from a hand-written upstream table")
        bad = []
        for key in covered:
            row = items[key]
            for head, _mods in seen[row["model_id"]]:
                for i, name in FIELDS.items():
                    if row.get(name) is not None and row[name] != head[i]:
                        bad.append((key, name, row[name], head[i]))
        LEDGER.ok(not bad,
                  "and every fixed field agrees, on every sighting",
                  f"{len(FIELDS)} fields x {len(covered)} pieces x every "
                  f"sighting, 0 disagreements. `content/items.toml` says of "
                  f"these rows: 'no capture of ours has ever carried these "
                  f"bytes'. One has"
                  if not bad else f"DISAGREE: {bad[:6]}")
        loose = []
        for key in covered:
            row = items[key]
            for i, name in PER_INSTANCE.items():
                vals = {h[i] for h, _m in seen[row["model_id"]]}
                if row.get(name) is not None and row[name] not in vals:
                    loose.append((key, name, row[name], sorted(vals)))
        LEDGER.ok(not loose,
                  "and dye_colors is one retail actually used for that model",
                  "compared as MEMBERSHIP, not equality -- it is what a player "
                  "dyed that instance and retail shows four values for one "
                  "model, so requiring equality would fail on a field that is "
                  "MEANT to vary"
                  if not loose else f"OUTSIDE: {loose}")
        modbad = []
        for key in covered:
            mine = tuple(decoded(items[key]))
            for _head, mods in seen[items[key]["model_id"]]:
                if mods != mine:
                    modbad.append((key, mine, mods))
        LEDGER.ok(not modbad,
                  "and the MODIFIER WORDS match byte for byte",
                  "which is the armour rating itself: retail sends identifier "
                  "572 argument 25 for these models, and so do we"
                  if not modbad else f"DIFFER: {modbad[:3]}")

    print("\n4. --no-armour is a real control")
    LEDGER.ok(authsrv.EQUIP_ARMOUR is True,
              "armour is ON by default",
              "a naked character was the state this server shipped in, and it "
              "made every armour question untestable")
    flags = [n for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and n.attr == "no_armour"]
    LEDGER.ok(flags,
              "and the flag exists to turn it off",
              "the control for any armour readout: with it the paper doll's "
              "five slots are empty and no tooltip can be hovered")
    LEDGER.ok(all(items[k].get("modifiers") for k in armour),
              "CONTROL: an empty modifier list would render nothing",
              "studies/character called that 'a legitimate first milestone but "
              "not the finished job' -- armour that renders and protects "
              "nothing. Every one of the five carries real words")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
