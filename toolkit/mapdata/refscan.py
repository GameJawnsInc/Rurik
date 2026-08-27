"""What the tag-4 and tag-6 `value` words are — measured over all 349 maps.

WHAT THIS SETTLES. `studies/customarea/FINDINGS.md` "What is still UNVERIFIED"
item 1, and the same sentence in `props.py`'s own header:

> The `value` u16 of tags 4 and 6 recurs across maps, so those are ids rather
> than per-map hashes -- not measured.

It is measured now, and **that reading is right for tag 4 and WRONG for tag 6**.
The recurrence argument it rests on cannot tell the two apart: small indices
collide across maps for the same reason small integers do, so "recurs across
maps" is equally true of a local index and of a global id. What separates them
is the BOUND.

    tag 6   value < len(props) on 10,647 of 10,647 rows in 149 maps
    tag 4   value < len(props) on 212 of 6,355 rows in 335 maps

**A `PropRef` is `{u16 value, u16 prop}`, and for tag 6 BOTH words index the same
prop array** — `prop` does so 10,647 of 10,647 and so does `value`. `props.py`
documents only `prop` as an index. So tag 6 is a prop-to-prop RELATION, and what
it relates is not decided here (see the limits below).

**WHY 10,647 OF 10,647 IS NOT ENOUGH ON ITS OWN, and what makes it a finding.**
If maps held thousands of props and the values were all under a hundred, the
inequality would hold by construction and say nothing. Two controls settle that:

  * **TIGHTNESS.** `max(value) / (len(props) - 1)` per map: median **0.939**,
    p75 0.981, max 1.000, with **90 of 149 maps above 0.9** and 7 landing on
    `len(props) - 1` exactly. The values SATURATE the array rather than sitting
    in a small corner of it. Tag 4's same ratio has a median of **94.6** — its
    values are about ninety-five times the prop count, topping out at 65,521.
  * **THE SHUFFLE CONTROL.** Re-score each map's values against a DIFFERENT
    map's prop count and **32.2%** fall out of range. The bound is a fact about
    *this map's* array, not a universal small-number ceiling. (Tag 4 reads 97.1%
    there, which is not informative — it was already out of range.)

**WHAT THIS DOES NOT ESTABLISH**, and the limits are real:

  * That `value` indexes the PROP array specifically, rather than some other
    per-map array of the same length. Bounds and saturation cannot separate
    those; only a consumer read can.
  * What the relation MEANS. Nothing here says whether `value` is a parent, a
    group leader, an LOD substitute or a sort key.
  * Tag 4's namespace is shown to be wide and cross-map, not what it indexes.
    The join candidate named by `studies/customarea` is the deps chunk / MFT and
    is untested here.

**Ten rows of tag 6 are SELF-REFERENCES** (`value == prop`), against zero in tag
4. A sample-sized pass over 40 maps reported none, which is how a rare row
disappears; over the whole corpus they exist and any reading of the relation has
to survive them.

    python toolkit/mapdata/refscan.py
    python toolkit/mapdata/refscan.py --json

standard library only.
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mapfile as mfile  # noqa: E402
from archive import Archive  # noqa: E402
from mapchunks import MapIndex  # noqa: E402
from props import StrippedProps  # noqa: E402

PROPS_CHUNK = 0x10000004
#: The shuffle control's seed. Fixed so the percentage is reproducible; the
#: result is not sensitive to it (any pairing of unequal counts breaks the
#: bound), and a wandering number would look like a measurement changing.
SHUFFLE_SEED = 20260827


def corpus(dat=None):
    """[(row index, StrippedProps)] for every map with a props chunk."""
    ar = Archive(dat) if dat else Archive()
    try:
        mi = MapIndex(ar)
        out = []
        for head, _p in mi.pairs:
            partner = mi.partner(head)
            if partner is None:
                continue
            try:
                m = mfile.MapFile.decode(ar.read(partner), strict=False)
                chunk = m.find(PROPS_CHUNK)
                if chunk is None:
                    continue
                out.append((head.index, StrippedProps.decode(chunk.payload())))
            except Exception:
                continue
        return out
    finally:
        ar.close()


def score(rows, which):
    """Every rival reading of `which`'s value word, scored on the same rows."""
    maps = 0
    v_in = v_out = p_in = p_out = 0
    model_in = self_ref = 0
    ratios, exact = [], 0
    per_map = []
    values = set()
    maxval = 0
    for idx, sp in rows:
        refs = getattr(sp, which)
        if not refs:
            continue
        npr = len(sp.props)
        if npr == 0:
            continue
        maps += 1
        models = {p.model for p in sp.props}
        vs = []
        for r in refs:
            vs.append(r.value)
            values.add(r.value)
            maxval = max(maxval, r.value)
            if r.value < npr:
                v_in += 1
            else:
                v_out += 1
            if r.prop < npr:
                p_in += 1
            else:
                p_out += 1
            if r.value in models:
                model_in += 1
            if r.value == r.prop:
                self_ref += 1
        per_map.append((idx, npr, vs))
        if npr > 1:
            ratios.append(max(vs) / (npr - 1))
            if max(vs) == npr - 1:
                exact += 1

    ratios.sort()
    n = len(ratios) or 1
    rnd = random.Random(SHUFFLE_SEED)
    counts = [npr for _i, npr, _v in per_map]
    sh_out = sh_tot = 0
    for _i, _npr, vs in per_map:
        other = counts[rnd.randrange(len(counts))] if counts else 0
        for v in vs:
            sh_tot += 1
            if v >= other:
                sh_out += 1

    return {
        "tag": int(which[-1]), "maps": maps, "rows": v_in + v_out,
        "max_value": maxval, "distinct_values": len(values),
        "value_in_range": v_in, "value_out_of_range": v_out,
        "prop_in_range": p_in, "prop_out_of_range": p_out,
        "value_is_a_model_id": model_in, "self_references": self_ref,
        "tightness": {
            "maps": len(ratios),
            "min": round(ratios[0], 4) if ratios else None,
            "p25": round(ratios[n // 4], 4) if ratios else None,
            "median": round(ratios[n // 2], 4) if ratios else None,
            "p75": round(ratios[3 * n // 4], 4) if ratios else None,
            "max": round(ratios[-1], 4) if ratios else None,
            "exact_last_index": exact,
            "above_0_9": sum(1 for r in ratios if r > 0.9),
        },
        "shuffle_control": {
            "rows": sh_tot, "out_of_range": sh_out,
            "pct": round(100.0 * sh_out / sh_tot, 2) if sh_tot else None,
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dat", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = corpus(args.dat)
    out = {w: score(rows, w) for w in ("refs4", "refs6")}
    out["maps_decoded"] = len(rows)
    if args.json:
        print(json.dumps(out, indent=1))
        return 0

    print(f"{len(rows)} maps decoded\n")
    for w in ("refs4", "refs6"):
        s = out[w]
        t, sh = s["tightness"], s["shuffle_control"]
        print(f"tag {s['tag']}: {s['maps']} maps, {s['rows']} rows, "
              f"max value {s['max_value']}, {s['distinct_values']} distinct")
        print(f"  value < len(props) : {s['value_in_range']} yes / "
              f"{s['value_out_of_range']} no")
        print(f"  prop  < len(props) : {s['prop_in_range']} yes / "
              f"{s['prop_out_of_range']} no")
        print(f"  value is a model id: {s['value_is_a_model_id']}")
        print(f"  self-references    : {s['self_references']}")
        print(f"  tightness max(value)/(len(props)-1): median {t['median']}, "
              f"p75 {t['p75']}, max {t['max']}, "
              f"{t['above_0_9']}/{t['maps']} over 0.9, "
              f"{t['exact_last_index']} exact")
        print(f"  SHUFFLE CONTROL    : {sh['out_of_range']}/{sh['rows']} "
              f"({sh['pct']}%) out of range against another map's count\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
