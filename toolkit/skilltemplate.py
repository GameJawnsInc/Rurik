"""The Guild Wars skill-template code: the bit format, and the client's own
validity rule for a pasted one.

    python toolkit/skilltemplate.py OgAAQHIIIJIKIVIAAAAAAA
    python toolkit/skilltemplate.py --explain OQAAQoB/MafqiIC9gRbyZA

WHY THIS EXISTS. `studies/profession/MODDABLE.md` §9 carried "does the
skill-template codec's profession field have its own width?" as **NOT FOUND --
never asked, and it is a serialisation ceiling that leaves the machine**, with
"read the template encoder" as the thing that would answer it. This module is
the answer, transcribed instruction by instruction from the pinned build; the
derivation, the addresses and what each clause settles are in
[studies/templates/FINDINGS.md](../studies/templates/FINDINGS.md).

WHAT IS HERE AND WHAT IS DELIBERATELY NOT. Two halves, kept apart because they
have different dependencies and different lifetimes:

  * **The FORMAT** -- `decode`, `encode`, `Template`. Pure arithmetic over a
    bit string. It knows nothing about any skill, needs no client and no vault,
    and is the half a server can use on a bare machine.
  * **The RULE** -- `validate`. The conjunction the client's own decoder
    computes before it will show you a bar. It needs to know, per skill id,
    whether the id is player-loadable and which profession owns it, and per
    attribute id, which profession owns it and whether it is that profession's
    primary. Those are facts about ArenaNet's tables, so this module does not
    hold them: `validate` takes a `Tables` of three callables and the CLI fills
    it from `clientscan/skilltable.py` when a vault is present. That keeps the
    stdlib rule and stops the format half rotting when a build moves a table.

THE FORMAT, as the encoder writes it (`0x0091CD50`, build 38797). Every field
is a little-endian bit run, least-significant bit first, and the code string is
those bits six at a time through the standard base64 alphabet -- which is read
out of the image at `0x00BC87D8` rather than assumed.

    4 bits   0xE          header, literally pushed at 0x0091CD5C
    4 bits   0x0          header
    2 bits   profSel      profession field width selector
    w bits   profPrimary  w = profSel * 2 + 4
    w bits   profSecondary
    4 bits   attribCount
    4 bits   attribSel    attribute id width selector
      per attribute, attribCount times:
    a bits     attribId   a = attribSel + 4
    4 bits     rank
    4 bits   skillSel     skill id width selector
      per slot, always 8:
    s bits     skillId    s = skillSel + 8

A width selector is the smallest that fits the largest value the field must
carry: `bsr(max(values, 1)) + 1` bits, rounded up into the selector's own
grid (2 per step for professions, 1 per step for attributes and skills). So
**the profession field is 4 to 10 bits wide and is not a byte** -- MODDABLE's
question, answered: a custom profession id up to 1023 serialises, which is far
past `CHAR_PROFESSIONS`.

THE THREE CEILINGS THE ENCODER ASSERTS, each cited to its own site because a
server that emits a template inherits them:
  * `AcctTemplate:406  bitCountEncoding < 4`     -- profSel, so w <= 10
  * `AcctTemplate:423  data.attribCount < 16`    -- and :422 bounds it at 12
  * `AcctTemplate:465  data.skill[index] < SKILLS`

WHAT THE ENCODER DOES NOT DO, and it is the finding the whole arc turns on: it
never looks a skill up. `0x0091CD50` calls exactly two functions in its whole
body -- `bsr` and the bit writer -- so it cannot filter by anything. It will
happily encode a monster skill, and the decoder will then refuse the code it
just produced. See `validate`.

Python 3 standard library only. Read-only: nothing here opens a client.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# OBSERVED at 0x00BC87D8 on build 38797, and it is the standard base64
# alphabet. The client indexes into this string with `strchr` and writes the
# INDEX as six bits (0x0091C394), so the code's characters are digits, not
# bytes: there is no padding and no '=' anywhere in the format.
ALPHABET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789+/")

SKILLS = 3443            # ConstSkill:3833 `index < arrsize(s_skill)`
CHAR_ATTRIBS = 51        # ConstAttrib, `index < 0x33`
CHAR_PROFESSIONS = 11    # AcctTemplate:411 `data.profPrimary < CHAR_PROFESSIONS`
CHAR_PROFESSION_NONE = 0
MAX_ATTRIBS = 12         # marrsize(AccountTemplateDataSkill, attrib)
SLOTS = 8
HEADER = (0xE, 0x0)


class BadTemplate(Exception):
    """The string is not a skill-template code at all."""


# -- the bit string -------------------------------------------------------
# The client's reader RETURNS ZERO and raises an overrun flag when it is asked
# for bits that are not there (0x005E87D3), and the decoder's last validity
# term is that flag being clear (0x004C9A20 reads it at reader+0x00). So a
# truncated code decodes to something -- it just decodes to something invalid,
# and `Template.overran` is how a caller tells the two apart.

class _Bits:
    def __init__(self, bits=None):
        self.bits = list(bits or ())
        self.pos = 0
        self.overran = False

    def read(self, n):
        v = 0
        for k in range(n):
            if self.pos >= len(self.bits):
                if n:
                    self.overran = True
            else:
                v |= self.bits[self.pos] << k
            self.pos += 1
        return v

    def write(self, n, value):
        for k in range(n):
            self.bits.append((value >> k) & 1)


def _bitwidth(value):
    """`bsr(v) + 1` -- the client's own width, via 0x0046E110 (a bare `bsr`).

    `bsr(0)` is undefined, which is why every call site maxes with 1 first.
    """
    v = max(int(value), 1)
    return v.bit_length()


class Template:
    """One `AccountTemplateDataSkill`, 140 bytes in the client."""

    def __init__(self, prof_primary=0, prof_secondary=0,
                 attributes=(), skills=()):
        self.prof_primary = int(prof_primary)
        self.prof_secondary = int(prof_secondary)
        self.attributes = [(int(a), int(r)) for a, r in attributes]
        self.skills = [int(s) for s in skills]
        while len(self.skills) < SLOTS:
            self.skills.append(0)
        # Set by `decode`; None when the Template was built by hand.
        self.overran = None
        self.header = None
        self.widths = None

    def __repr__(self):
        return ("Template(prof=%d/%d, attributes=%r, skills=%r)"
                % (self.prof_primary, self.prof_secondary,
                   self.attributes, self.skills))


def decode(code):
    """A code string -> a Template. Refuses only what is not a code at all.

    Everything the client would REJECT still decodes here, on purpose: the
    point of this module is to say WHY a code the client blanks is being
    blanked, and you cannot say that about a decode that threw.
    """
    if not isinstance(code, str) or not code:
        raise BadTemplate("empty")
    b = _Bits()
    for ch in code:
        i = ALPHABET.find(ch)
        if i < 0:
            # 0x0091C385: the client STOPS at the first character outside the
            # alphabet rather than refusing the string, so trailing junk (a
            # quote, a cursor, a newline) truncates instead of failing.
            break
        b.write(6, i)
    if not b.bits:
        raise BadTemplate("no base64 characters in %r" % (code[:16],))

    t = Template()
    h0 = b.read(4)
    h1 = None
    if (h0 & 0xE) == 0xE:
        if h0 & 1:
            # 0x0091D268 `test eax, 0xFFFFFFF1` -- nibble 0xF is refused
            # outright, before anything else is read.
            raise BadTemplate("header nibble 0x%X is refused by the client" % h0)
        h1 = b.read(4)
        if h1 != 0:
            raise BadTemplate("header 0x%X,0x%X is not a skill template"
                              % (h0, h1))
    # else: nibble <= 13 falls straight through to the fields (0x0091D266).
    # Nothing the current encoder writes takes that path; it is kept because
    # the client accepts it and this module is a transcription, not a design.
    t.header = (h0, h1)

    sel = b.read(2)
    w = sel * 2 + 4
    t.prof_primary = b.read(w)
    t.prof_secondary = b.read(w)

    count = b.read(4)
    asel = b.read(4)
    aw = asel + 4
    # 0x0091CC0E clamps the LOOP to 12 while leaving `attribCount` as read --
    # a count of 12..15 reads twelve entries and fails the count term.
    for _ in range(min(count, MAX_ATTRIBS)):
        attr = b.read(aw)
        t.attributes.append((attr, b.read(4)))
    t.attrib_count = count

    ssel = b.read(4)
    sw = ssel + 8
    t.skills = [b.read(sw) for _ in range(SLOTS)]

    t.widths = dict(prof=w, attrib=aw, skill=sw)
    t.overran = b.overran
    return t


def encode(t):
    """A Template -> a code string, by the encoder's own width rules.

    Deliberately as unfiltered as `0x0091CD50`: it will encode a monster skill,
    because the client does. The asserts it would trip are raised as
    ValueError, since on a retail client they are dialogs rather than guards.
    """
    b = _Bits()
    b.write(4, HEADER[0])
    b.write(4, HEADER[1])

    n = _bitwidth(max(t.prof_primary, t.prof_secondary, 1))
    sel = 0 if n < 5 else (n - 3) >> 1
    if sel >= 4:
        raise ValueError("AcctTemplate:406 bitCountEncoding < 4: profession "
                         "ids %d/%d need a %d-bit field"
                         % (t.prof_primary, t.prof_secondary, sel * 2 + 4))
    w = sel * 2 + 4
    b.write(2, sel)
    b.write(w, t.prof_primary)
    b.write(w, t.prof_secondary)

    count = len(t.attributes)
    if count >= 16:
        raise ValueError("AcctTemplate:423 data.attribCount < 16: %d" % count)
    b.write(4, count)
    amax = max([a for a, _ in t.attributes] + [1])
    m = _bitwidth(amax)
    asel = 0 if m < 5 else m - 4
    if asel >= 16:
        raise ValueError("AcctTemplate:434 bitCountEncoding < 16")
    b.write(4, asel)
    for attr, rank in t.attributes:
        b.write(asel + 4, attr)
        b.write(4, rank)

    skills = (list(t.skills) + [0] * SLOTS)[:SLOTS]
    for s in skills:
        if not 0 <= s < SKILLS:
            raise ValueError("AcctTemplate:465 data.skill[index] < SKILLS: %d"
                             % s)
    k = _bitwidth(max(skills + [1]))
    ssel = 0 if k < 9 else k - 8
    if ssel >= 16:
        raise ValueError("AcctTemplate:459 bitCountEncoding < 16")
    b.write(4, ssel)
    for s in skills:
        b.write(ssel + 8, s)

    # 0x0091C3B0 drains the bit buffer six at a time until it reports empty,
    # and the buffer's granularity is a BYTE -- `0x005E8A40` pads the partial
    # one on flush. So the character count is ceil(pad8(bits) / 6), which is
    # why a 126-bit template is 22 characters and not 21.
    bits = list(b.bits)
    while len(bits) % 8:
        bits.append(0)
    out = []
    for i in range(0, len(bits), 6):
        v = 0
        for k, bit in enumerate(bits[i:i + 6]):
            v |= bit << k
        out.append(ALPHABET[v])
    return "".join(out)


# -- the client's validity rule -------------------------------------------

class Tables:
    """The three lookups `0x0091CB90` makes, injected rather than imported.

    `skill_row(id)` -> a mapping with `equip_family` and `profession`, or None
    `attrib_profession(id)` -> the owning profession id (11 == none)
    `attrib_is_primary(id)` -> 1 when the attribute is a primary attribute
    """

    def __init__(self, skill_row, attrib_profession, attrib_is_primary):
        self.skill_row = skill_row
        self.attrib_profession = attrib_profession
        self.attrib_is_primary = attrib_is_primary


def validate(t, tables):
    """Return (ok, reasons) -- the conjunction at `0x0091CB90`, clause by clause.

    The client computes ONE boolean by AND-ing these together and shows an
    empty window when it comes out false; it never says which clause failed,
    which is the whole reason this returns a list. Clause order and content
    follow the disassembly; `studies/templates/FINDINGS.md` §3 maps each one to
    its instruction.
    """
    why = []

    if t.prof_primary == CHAR_PROFESSION_NONE:
        why.append("profPrimary is CHAR_PROFESSION_NONE (0x0091CBC6)")
    if t.prof_primary >= CHAR_PROFESSIONS:
        why.append("profPrimary %d >= CHAR_PROFESSIONS" % t.prof_primary)
    if t.prof_secondary >= CHAR_PROFESSIONS:
        why.append("profSecondary %d >= CHAR_PROFESSIONS" % t.prof_secondary)

    count = getattr(t, "attrib_count", len(t.attributes))
    if count >= MAX_ATTRIBS:
        why.append("attribCount %d >= %d (0x0091CBE9)" % (count, MAX_ATTRIBS))

    pair = {t.prof_primary, t.prof_secondary}
    for attr, rank in t.attributes:
        if rank > 12:
            why.append("attribute %d rank %d > 12" % (attr, rank))
        if attr >= CHAR_ATTRIBS:
            why.append("attribute %d >= CHAR_ATTRIBS" % attr)
            continue
        owner = tables.attrib_profession(attr)
        if owner == CHAR_PROFESSIONS:
            why.append("attribute %d belongs to no profession" % attr)
        elif owner not in pair:
            why.append("attribute %d is %s's, not %s"
                       % (attr, owner, sorted(pair)))
        if tables.attrib_is_primary(attr) == 1 and owner != t.prof_primary:
            why.append("attribute %d is a PRIMARY attribute of %s, which is "
                       "not the primary profession" % (attr, owner))

    for slot, sid in enumerate(t.skills):
        if sid == 0:
            continue                       # 0x0091CCD1: an empty slot is legal
        if sid >= SKILLS:
            why.append("slot %d: skill %d >= SKILLS" % (slot, sid))
            continue
        row = tables.skill_row(sid)
        if row is None:
            why.append("slot %d: skill %d has no row" % (slot, sid))
            continue
        if row["equip_family"] != 1:
            why.append("slot %d: skill %d is not loadable "
                       "(equip_family %d, the client wants 1 -- 0x0091CCF8)"
                       % (slot, sid, row["equip_family"]))
        prof = row["profession"]
        if prof != 0 and prof not in pair:
            why.append("slot %d: skill %d is profession %d, and the template "
                       "is %d/%d" % (slot, sid, prof,
                                     t.prof_primary, t.prof_secondary))

    if t.overran:
        why.append("the code ran out of bits (0x004C9A20)")

    return (not why), why


# -- CLI ------------------------------------------------------------------

def _tables_from_vault(exe=None):
    """Fill a `Tables` from the pinned client. CLI only -- see the docstring."""
    sys.path.insert(0, os.path.join(HERE, "clientscan"))
    import skilltable                                        # noqa: E402
    import attribtable                                       # noqa: E402
    if exe:
        why = "given on the command line"
    else:
        exe, why = skilltable.find_exe()
    with open(exe, "rb") as fh:
        data = fh.read()
    sbase, scount, _score = skilltable.locate_table(data)
    rows = {i: skilltable.parse_record(data, sbase, i) for i in range(scount)}
    abase, acount = attribtable.locate_table(data)
    attrs = {i: attribtable.parse_record(data, abase, i) for i in range(acount)}

    def owner(a):
        r = attrs.get(a)
        return CHAR_PROFESSIONS if r is None else r["profession"]

    def primary(a):
        r = attrs.get(a)
        return 0 if r is None else int(bool(r.get("is_primary")))

    return Tables(rows.get, owner, primary), "%s (%s)" % (exe, why)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="Decode a Guild Wars skill-template code.")
    ap.add_argument("code", nargs="+")
    ap.add_argument("--exe", help="client to read the tables from")
    ap.add_argument("--explain", action="store_true",
                    help="also print the client's validity verdict")
    a = ap.parse_args(argv)

    tables = None
    if a.explain:
        try:
            tables, why = _tables_from_vault(a.exe)
            print("tables: %s" % why)
        except BaseException as exc:                         # noqa: BLE001
            print("tables unavailable, verdict skipped: %s" % exc)

    for code in a.code:
        print("\n%s" % code)
        try:
            t = decode(code)
        except BadTemplate as exc:
            print("  not a skill template: %s" % exc)
            continue
        print("  header      0x%X,%s" % (t.header[0],
              "-" if t.header[1] is None else "0x%X" % t.header[1]))
        print("  professions %d / %d   (field %d bits)"
              % (t.prof_primary, t.prof_secondary, t.widths["prof"]))
        print("  attributes  %r   (field %d bits)"
              % (t.attributes, t.widths["attrib"]))
        print("  skills      %r   (field %d bits)"
              % (t.skills, t.widths["skill"]))
        print("  overran     %s" % t.overran)
        back = encode(t)
        print("  re-encodes  %s%s" % (back, "" if back == code
                                      else "   <- DIFFERS from the input"))
        if tables is not None:
            ok, why = validate(t, tables)
            print("  the client would %s this code"
                  % ("ACCEPT" if ok else "BLANK"))
            for w in why:
                print("     - %s" % w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
