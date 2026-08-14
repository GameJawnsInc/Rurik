#!/usr/bin/env python3
"""Author a name for every skill of a custom profession.

    python toolkit/mapdata/skillnames.py --dump
    python toolkit/mapdata/skillnames.py --check

`glyphs.py` draws 132 pictures and `iconset.py` puts them on 125 archive rows, so
after 2026-08-14 a Stormcaller's bar is our art carrying ArenaNet's words. This is
the other half: 188 names, ours, generated rather than typed.

WHY GENERATED. The same reason the icons are. 188 hand-written names is a day of
typing that rots the moment the roster moves, and the roster is a function of the
client build. Generated names are a function of the same inputs the icons are, so
the two can be made to AGREE -- which is the whole design below.

THE NAME IS TWO WORDS, AND EACH ONE IS AN AXIS THAT ALREADY EXISTS.

  noun      <- the MOTIF of the icon the skill draws (`glyphs.py`, i % 22).
               So a skill whose icon draws a forked bolt is called some kind of
               bolt. This agrees with the picture BY CONSTRUCTION rather than by
               a mapping somebody has to maintain.
  adjective <- the skill's ATTRIBUTE (row+0x29), which is what the Skills panel
               GROUPS BY. So a Windward skill reads as sheltering and a Tempest
               skill reads as furious, and the five groups on the panel each have
               their own register.

Neither axis is unique on its own and NEITHER IS THE PAIR -- that is measured, not
assumed. Over profession 8 on build 38797: motif alone gives 22 groups with a
worst case of 12 skills; the whole glyph index gives 125 with a worst case of 7;
adding the attribute moves that to 126 and 6, because skills sharing an icon
overwhelmingly share an attribute too (the 7-skill icon is six Thunderhead skills
and one Galecraft). So **a per-skill discriminator is mandatory**, and pretending
otherwise would have produced 50 duplicate names.

THE DISCRIMINATOR IS `j`, the skill's rank by id within its own (motif, attribute)
group. It indexes the NOUN, so two skills in one group cannot collide. Uniqueness
is then structural rather than hoped for:

  * same motif, same attribute, different j  -> different noun
  * same motif, different attribute          -> different adjective
  * different motif                          -> different noun pool

which reduces the whole question to "are the 176 nouns distinct", and `--check`
asserts exactly that. The measured worst group is 8 and every pool carries POOL=10,
so `j` has room; a group past POOL is a REFUSAL, because silently wrapping would
mint the duplicate this design exists to prevent.

THE TWELVE WITHOUT A GLYPH. 176 of the 188 skills draw an icon we armed; the other
12 draw an icon SHARED with another profession, which `iconset.py` skips on purpose
so it does not repaint a bar nobody asked us to touch. Those skills get a name from
`UNGLYPHED` instead, and the split is deliberate: their picture is ArenaNet's, so
their name must not claim to agree with it.

PROVENANCE. Every word here is ours. Nothing is read from the client, nothing is
derived from ArenaNet's own skill text, and the temptation to seed from it "as a
starting point" is exactly the bulk extraction the gate refuses. The inputs are two
integers per skill -- a motif index and an attribute id.
"""

import argparse
import sys

# TWO NUMBERS, NOT ONE, and the first draft of this file conflated them.
#
# MEASURED_WORST_GROUP is a fact about profession 8 on build 38797: partition its
# 188 skills by (motif, attribute) and the biggest cell holds 8. POOL is a DESIGN
# CHOICE -- how many words each pool carries -- and it must exceed the measurement
# or the generator sits exactly on its own boundary, which is where the first
# version sat: 8 against 8, so a single skill moving into that cell turned a
# working generator into a refusal. The margin is now an asserted claim rather
# than a coincidence (`vocabulary_check`), and the two can drift apart on purpose:
# a new client build may move the measurement without anybody rewriting the words.
MEASURED_WORST_GROUP = 8
POOL = 10

# The attribute with no attribute. Skills that scale with nothing carry 51 in
# row+0x29; the client's own table uses it as the "none" sentinel.
NO_ATTRIBUTE = 51

# -------------------------------------------------------------------- the words
#
# ADJECTIVES are keyed by ATTRIBUTE ID, and the five real ids are the Stormcaller
# design's own (studies/profession/RESKIN.md 19.5): 26 Tempest (the primary), 32
# Galecraft, 33 Windward, 34 Thunderhead, 36 Storm Calling. Each pool is a
# REGISTER rather than a synonym list -- the point is that the five groups on the
# Skills panel sound different from each other, not that the words mean the same
# thing.
ADJECTIVES = {
    26: ("Raging", "Savage", "Riotous", "Furious", "Wrathful",
         "Seething", "Howling", "Unbound", "Rampant", "Violent"),
    32: ("Keen", "Deft", "Sweeping", "Cunning", "Sudden",
         "Veering", "Sly", "Nimble", "Adroit", "Fleet"),
    33: ("Warding", "Sheltering", "Abiding", "Steadfast", "Kindly",
         "Guarded", "Patient", "Enduring", "Constant", "Watchful"),
    34: ("Looming", "Leaden", "Brooding", "Sullen", "Grim",
         "Massing", "Thunderous", "Darkening", "Ponderous", "Overcast"),
    36: ("Called", "Summoned", "Bidden", "Answering", "Beckoned",
         "Spoken", "Risen", "Wakened", "Invoked", "Uttered"),
    NO_ATTRIBUTE: ("Wandering", "Errant", "Idle", "Stray", "Common",
                   "Quiet", "Loose", "Vagrant", "Aimless", "Drifting"),
}

# NOUNS are keyed by MOTIF INDEX and the order is `glyphs._MOTIFS`'s own, so
# NOUNS[i][*] describes the shape `glyphs.icon(k)` draws when k % 22 == i. That
# correspondence is the reason the names agree with the pictures, and
# `test_skillnames.py` pins it against the motif function names rather than
# against this comment.
NOUNS = (
    # 0 bolt
    ("Bolt", "Levin", "Stroke", "Lash", "Brand",
     "Spark", "Fulmination", "Smite", "Thunderbolt", "Jag"),
    # 1 spiral
    ("Spiral", "Coil", "Gyre", "Helix", "Whorl",
     "Twist", "Curl", "Volute", "Corkscrew", "Scroll"),
    # 2 chevrons
    ("Chevron", "Barb", "Fletching", "Notch", "Rafter",
     "Zigzag", "Dart", "Quill", "Herringbone", "Vane"),
    # 3 wheel
    ("Wheel", "Rotor", "Nave", "Circuit", "Turning",
     "Roundel", "Cartwheel", "Orbit", "Hub", "Spoke"),
    # 4 crescent
    ("Crescent", "Sickle", "Scythe", "Waning", "Hornbow",
     "Lune", "Reaping", "Curve", "Meniscus", "Horn"),
    # 5 trident
    ("Trident", "Fork", "Prong", "Tine", "Spear",
     "Pitchfork", "Leister", "Trefoil", "Trine", "Pike"),
    # 6 vortex
    ("Vortex", "Maelstrom", "Eddy", "Whirl", "Swirl",
     "Cyclone", "Drain", "Churn", "Twister", "Spin"),
    # 7 cross
    ("Cross", "Saltire", "Crux", "Quarter", "Intersect",
     "Crossing", "Fourfold", "Junction", "Chiasm", "Transept"),
    # 8 wave
    ("Wave", "Surge", "Swell", "Breaker", "Roller",
     "Crest", "Undertow", "Billow", "Comber", "Seiche"),
    # 9 triangle
    ("Wedge", "Prism", "Delta", "Spire", "Shard",
     "Cusp", "Gable", "Pyramid", "Trigon", "Peak"),
    # 10 drop
    ("Drop", "Bead", "Teardrop", "Droplet", "Rain",
     "Dew", "Weeping", "Cloudburst", "Globule", "Drizzle"),
    # 11 starburst
    ("Starburst", "Radiance", "Nova", "Corona", "Blaze",
     "Flare", "Scintilla", "Sunburst", "Glory", "Effulgence"),
    # 12 rhombus
    ("Rhombus", "Lozenge", "Diamond", "Facet", "Kite",
     "Rhomb", "Pane", "Tessera", "Harlequin", "Quadrangle"),
    # 13 hook
    ("Hook", "Talon", "Crook", "Claw", "Grapple",
     "Snag", "Barbhook", "Gaff", "Cleek", "Tenterhook"),
    # 14 hourglass
    ("Hourglass", "Reckoning", "Ebb", "Waist", "Cinch",
     "Sandglass", "Halving", "Pinch", "Attenuation", "Neck"),
    # 15 concentric
    ("Rings", "Ripple", "Halo", "Aureole", "Echo",
     "Concentric", "Girdle", "Banding", "Annulus", "Wavefront"),
    # 16 lens
    ("Lens", "Eye", "Aperture", "Focus", "Pupil",
     "Iris", "Glass", "Sighting", "Ocellus", "Objective"),
    # 17 tau
    ("Tau", "Standard", "Gallows", "Crosstree", "Yoke",
     "Mast", "Lintel", "Ensign", "Gibbet", "Crossbar"),
    # 18 sigmoid
    ("Sigmoid", "Serpentine", "Meander", "Sinuous", "Wend",
     "Snake", "Slalom", "Weaving", "Switchback", "Ess"),
    # 19 crown
    ("Crown", "Diadem", "Coronet", "Circlet", "Tiara",
     "Regalia", "Sovereign", "Wreath", "Chaplet", "Garland"),
    # 20 funnel
    ("Funnel", "Spout", "Downdraft", "Chimney", "Flue",
     "Throat", "Waterspout", "Tunnel", "Hopper", "Vent"),
    # 21 arrow
    ("Arrow", "Shaft", "Vector", "Course", "Bearing",
     "Loosing", "Flight", "Heading", "Trajectory", "Quiver"),
)

# The skills whose icon is SHARED with another profession and which `iconset.py`
# therefore does not repaint. Their picture is not ours, so their name is drawn
# from its own pool rather than from a motif -- see the module docstring.
UNGLYPHED = ("Remnant", "Vestige", "Holdover", "Carryover", "Relic",
             "Leftover", "Borrowing", "Inheritance", "Bequest", "Legacy")

MOTIFS = len(NOUNS)


class Collision(Exception):
    """Two skills would receive the same name, or a group ran past the pool."""


def motif_of(glyph_index):
    """Glyph index -> motif. `None` passes through.

    `iconset.skill_glyphs` hands back the GLYPH INDEX (0..124 for profession 8),
    which is a position in the armed row list; the noun pool is keyed by MOTIF
    (0..21). The conversion is `glyphs.py`'s own `i % MOTIFS` and it is a function
    here rather than an inline `%` because the two modules' MOTIFS must be the
    same number -- `test_skillnames.py` asserts that against `glyphs.MOTIFS`, since
    a silent modulo by the wrong constant would name every skill after the wrong
    picture and nothing else would notice.
    """
    return None if glyph_index is None else glyph_index % MOTIFS


def _pool(attr):
    """Adjectives for one attribute, falling back to the no-attribute register.

    An unknown attribute is NOT an error: a recipe may put a skill on a row this
    module has never heard of, and refusing would make the naming pass fail for a
    reason that has nothing to do with naming. It reads as unaffiliated, which is
    what it is.
    """
    return ADJECTIVES.get(attr, ADJECTIVES[NO_ATTRIBUTE])


def name_for(motif, attr, j):
    """One name. `motif` is None for a skill whose icon we did not arm.

    The NOUN is indexed by `j` directly, which is what makes two skills in one
    group unable to collide. The ADJECTIVE is offset by the motif as well, purely
    so the wider pools get used: with `j` alone the high-index adjectives never
    appeared, because most groups are small -- 29 of 48 words reached the output
    in the first version. Uniqueness does not depend on this and cannot be broken
    by it, since within a group the motif is fixed and the noun already differs.
    """
    if j >= POOL:
        raise Collision(
            "group index %d is past the %d words each pool carries. Widen NOUNS, "
            "UNGLYPHED and ADJECTIVES together and raise POOL -- wrapping would "
            "mint a duplicate name, which is the one thing this module exists to "
            "prevent." % (j, POOL))
    pool = _pool(attr)
    adj = pool[(j + (0 if motif is None else motif)) % len(pool)]
    noun = UNGLYPHED[j] if motif is None else NOUNS[motif][j]
    return "%s %s" % (adj, noun)


def assign(skills):
    """Name every skill.

    `skills` maps skill id -> (GLYPH INDEX or None, attribute id) -- the shape
    `iconset.skill_glyphs` returns. Returns {skill id: name}. The group index `j`
    is the skill's RANK BY ID within its own (motif, attribute) partition, so the
    answer depends only on the input mapping and never on iteration order -- which
    matters, because the caller builds that mapping out of a dict.
    """
    groups = {}
    for sid in sorted(skills):
        glyph, attr = skills[sid]
        groups.setdefault((motif_of(glyph), attr), []).append(sid)
    out = {}
    for key, members in groups.items():
        motif, attr = key
        for j, sid in enumerate(members):
            out[sid] = name_for(motif, attr, j)
    dupes = {}
    for sid, nm in out.items():
        dupes.setdefault(nm, []).append(sid)
    clash = {nm: s for nm, s in dupes.items() if len(s) > 1}
    if clash:
        raise Collision("duplicate name(s): %s"
                        % ", ".join("%s -> %s" % (n, v) for n, v in
                                    sorted(clash.items())[:5]))
    return out


def vocabulary_check():
    """Every noun distinct, every pool wide enough. Returns a list of problems."""
    bad = []
    if POOL <= MEASURED_WORST_GROUP:
        bad.append("POOL is %d against a measured worst group of %d -- the "
                   "generator would sit on its own boundary, which is where the "
                   "first version sat" % (POOL, MEASURED_WORST_GROUP))
    seen = {}
    for m, pool in enumerate(NOUNS):
        if len(pool) < POOL:
            bad.append("motif %d carries %d nouns, needs %d"
                       % (m, len(pool), POOL))
        for w in pool:
            if w in seen:
                bad.append("noun %r appears in motif %d and motif %d"
                           % (w, seen[w], m))
            seen[w] = m
    for w in UNGLYPHED:
        if w in seen:
            bad.append("UNGLYPHED noun %r collides with motif %d" % (w, seen[w]))
    if len(UNGLYPHED) < POOL:
        bad.append("UNGLYPHED carries %d nouns, needs %d"
                   % (len(UNGLYPHED), POOL))
    for attr, pool in sorted(ADJECTIVES.items()):
        if len(pool) < POOL:
            bad.append("attribute %d carries %d adjectives, needs %d"
                       % (attr, len(pool), POOL))
        if len(set(pool)) != len(pool):
            bad.append("attribute %d repeats an adjective" % attr)
    return bad


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="Validate the vocabulary alone. No client, no archive.")
    ap.add_argument("--dump", action="store_true",
                    help="Name profession 8's real roster and print it. Needs the "
                         "pinned client and an archive to resolve icon ids.")
    ap.add_argument("--profession", type=int, default=8)
    a = ap.parse_args()

    if a.check or not a.dump:
        bad = vocabulary_check()
        print("%d motifs x %d nouns = %d nouns, %d adjective pools, "
              "POOL=%d against a measured worst group of %d"
              % (MOTIFS, POOL, sum(len(p) for p in NOUNS), len(ADJECTIVES),
                 POOL, MEASURED_WORST_GROUP))
        for b in bad:
            print("  PROBLEM: %s" % b)
        print("vocabulary: %s" % ("OK" if not bad else "%d problem(s)" % len(bad)))
        if not a.dump:
            return 1 if bad else 0

    import iconset                                              # noqa: E402
    mapping = iconset.skill_glyphs(a.profession)
    named = assign(mapping)
    unglyphed = sum(1 for m, _ in mapping.values() if m is None)
    print("\nprofession %d: %d skills, %d without an armed icon"
          % (a.profession, len(named), unglyphed))
    for sid in sorted(named):
        glyph, attr = mapping[sid]
        m = motif_of(glyph)
        print("  %5d  attr %2d  glyph %s  motif %s  %s"
              % (sid, attr, "---" if glyph is None else "%3d" % glyph,
                 "--" if m is None else "%2d" % m, named[sid]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
