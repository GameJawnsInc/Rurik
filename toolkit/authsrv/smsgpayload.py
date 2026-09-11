"""The payload and regime algebra: what a message's bytes mean, what regime a row
belongs to, and what the ledger key says.

Lifted VERBATIM out of `smsgsweep.py`, which still owns the sweep itself -- the plan,
the capture readout, the ledger, the report and the CLI. This is that file's FOUNDATION
layer rather than an independent leaf: `plan`, `record`, `done_opcodes`,
`measured_under`, `migrate`, `capture_resolver` and `print_report` all call into it, so
a reader of any of those now opens two files. What earns the split is the OUTSIDE
reader -- `probes.py:_smsgsweep_steps` builds every sweep step out of
`smsgsweep.degenerate` and `smsgsweep.apply_set`, and that is the payload algebra and
none of the sweep's plumbing.

THE COMMENTS BELOW POINT BACK AT `smsgsweep.py`, and they travelled unchanged rather
than being reworded: `record`, `plan`, `migrate`, `capture_resolver`, `--report`,
`--set`, `--encstring` and `test_smsgsweep.py` section 9 all still live there. The
referents did not move; only this code did.

Standard library only, and it NEVER imports `smsgsweep` -- that file runs as
`python toolkit/authsrv/smsgsweep.py`, so an import back would load a second copy whose
flags `main()` never set. `corpus_encstring` is the one function here that needs the
vault, and it defers BOTH `import tape` and `vaultpath.require_dir(...)` into its own
body, which is what keeps importing this module free on a machine with no vault
(`test_bareimport.py`).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                                   # tape, deferred into corpus_encstring
sys.path.insert(0, os.path.dirname(HERE))                  # vaultpath
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import vaultpath                                                   # noqa: E402
from codec import Codec                                            # noqa: E402


# ---------------------------------------------------------------- the regime
# WHAT A ROW IS A MEASUREMENT OF, and the day it turned out to be two things at once.
#
# An all-zero send and an `--encstring` send are DIFFERENT EXPERIMENTS on the same
# opcode. The ledger had no field for which one a row came from, `record` keyed a row by
# opcode alone, and `record` is FIRST-WRITE-WINS -- so the second experiment's result was
# dropped without a word. Measured 2026-08-12: 0x0033, 0x009E, 0x00B9 and 0x00C0 each
# crashed the client on an all-zero payload, and each went SILENT when the same opcode
# was sent carrying a real encoded string. Two of the four crash dialogs name the guard
# that fires, and it is a guard ABOUT THE STRING -- `(codedString[0] & ~WORD_BIT_MORE) >=
# WORD_VALUE_BASE`, TextApi -- so the empty string is not an incidental detail of that
# run, it is its cause. Nine runs measured the clearance on 2026-08-12 and NOT ONE could
# be recorded: `--record` printed `recorded 0` and changed nothing, because every key was
# already in the ledger. Re-running the recorder could never have fixed it; only a key
# with a regime in it can.
#
# THE AXIS IS THE PAYLOAD, NOT THE FLAG, and that distinction is load-bearing rather than
# fastidious. Of the 487 catalogued opcodes only 87 carry a `string16` field at all; for
# the other 400 an `--encstring` run puts BYTE-IDENTICAL bytes on the wire, so it is not
# a second experiment and must not become a second row. Reading the regime out of the
# bytes the capture recorded (`plain`) gets that right by construction, gets `--set` runs
# right too, and is the only version that can be CHECKED -- a flag is something we told
# ourselves and `plain` is what went out. It is also how the migration of 2026-08-13 was
# able to give 324 historical rows an explicit regime rather than a hopeful default: they
# were re-derived from their own captures, one row at a time.
#
# WHY NOT A SCHEMA SHORTCUT FOR THE TEN. It is true that an opcode with no `string16`
# field cannot be moved by `--encstring`, so nine of the ten table-less rows could be
# called `allzero` from the catalogue alone. They are `unknown` instead, because their
# capture ("table-less pass 2026-08-12") is a hand-attributed note and not a file: no
# payload was ever recorded for them, `--set` could have moved any field, and a regime
# inferred from what the tool COULD have sent is exactly the kind of claim this repo
# labels UNVERIFIED. One re-run closes them.
ALLZERO = "allzero"
ENCSTRING = "encstring"
# A payload that is neither -- a `--set` run, or a string that is not the plan's.
OTHER = "other"
# Not determined. NEVER a synonym for `allzero`: a row that never said and a row that
# said "all zero" must not share a key, or the first silently retires the second.
UNKNOWN = "unknown"
REGIMES = (ALLZERO, ENCSTRING, OTHER, UNKNOWN)


def degenerate(codec, opcode, channel="GAME_SMSG", encstring=None):
    """A zeroed value for every field the codec says this opcode has.

    Read the field list from the CODEC, never from `schema/messages.json`: overrides
    change three field lists and a builder reading the base catalogue gets the arity
    wrong for exactly those three. Measured before this docstring was written.
    """
    vals = []
    for f in codec.fields_for(channel, opcode):
        t, length = f["type"], f["length"]
        if t == "msg_header":
            continue
        if t in ("byte", "word", "dword", "agent_id"):
            vals.append(0)
        elif t == "float":
            vals.append(0.0)
        elif t == "vec2":
            vals.append((0.0, 0.0))
        elif t == "vec3":
            vals.append((0.0, 0.0, 0.0))
        elif t == "blob":
            vals.append(b"\x00" * length)
        elif t == "string16":
            vals.append(encstring if encstring is not None else "")
        elif t in ("array8", "array16", "array32"):
            vals.append([])
        elif t == "nested_struct":
            # A nested_struct swallows the whole tail as its element layout, so the
            # caller supplies one value for it and none for the fields after it.
            vals.append([])
            break
        else:
            raise ValueError(f"0x{opcode:04X} has field type {t!r}, which this builder "
                             f"does not know how to zero. Refusing to guess a value.")
    return vals


def corpus_encstring():
    """The SHORTEST real encoded string in the live corpus, read at run time.

    PROVENANCE. This is ArenaNet's authored text, so it is never written into a source
    file, a test or a commit -- it is read from the owner's own captures when the plan is
    built, lands in the vault's plan JSON and in the vault's capture, and nothing else.
    Same pattern `mapbuild.py` uses for FINDINGS 14's mandatory chunks: commit the code
    that fetches it, never the bytes.

    Shortest, because the experiment is about the FORMAT gate and a long string drags in
    whatever else its contents reference. Measured over the corpus: `string16` splits
    cleanly into plain names (0x01DE) and encoded strings (0x0049, 0x004C, 0x0050,
    0x007A), whose first code unit is never below 0x09C4 in 105 samples.
    """
    import tape
    root = vaultpath.require_dir("captures", "live",
                                 why="a real encoded string to test the format gate")
    codec, best = Codec(), None
    ENCODED = (0x0049, 0x004C, 0x0050, 0x007A)
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or not any(f.startswith("game-")
                                           for f in os.listdir(d)):
            continue
        for ch in tape.channel_files(d):
            try:
                _i, ev = tape.load_tape(d, connection=ch["connection"])
                msgs, _r = tape.decode_all(ev, codec, "GAME_SMSG")
            except Exception:
                continue
            for _t, op, vals in msgs:
                if op not in ENCODED:
                    continue
                for f, v in zip([x for x in codec.fields_for("GAME_SMSG", op)
                                 if x["type"] != "msg_header"], vals):
                    if f["type"] == "string16" and isinstance(v, str) and v:
                        if best is None or len(v) < len(best):
                            best = v
    if best is None:
        raise ValueError("no encoded string found in the live corpus; refusing to "
                         "invent one, because the whole question is what the client "
                         "accepts and a guess would answer it wrong in both directions")
    return best


def regime_of_payload(codec, opcode, payload, channel="GAME_SMSG"):
    """Which experiment these bytes ARE, read off the wire rather than off a flag.

    The capture records every sweep send's plaintext, so the regime of a row is a
    MEASUREMENT and not a label we attached: `ALLZERO` when the payload is exactly the
    degenerate encoding, `ENCSTRING` when the ONLY difference from it is that every
    `string16` carries the same non-empty string, `OTHER` when any other field moved
    (a `--set` run), and `UNKNOWN` when the bytes are missing or will not decode.

    THE ENCSTRING ARM RE-ENCODES AND REQUIRES BYTE IDENTITY rather than eyeballing the
    decoded fields. That is what makes it refutable: a payload whose strings look right
    but whose third dword was also nudged fails the re-encode and comes back `OTHER`,
    where a field-by-field comparison written by hand would have had to remember to look.
    It also means this needs no corpus and no vault -- the string is recovered from the
    bytes, so the check never has to know WHICH encoded string a run used, which is the
    one thing about it that is ArenaNet's authored text.
    """
    if not payload:
        return UNKNOWN
    try:
        zero = codec.encode(channel, opcode,
                            list(degenerate(codec, opcode, channel, None)))
    except Exception:
        return UNKNOWN
    if payload == zero:
        return ALLZERO
    try:
        _op, values, _end = codec.decode_one(channel, payload)
        fields = [f for f in codec.fields_for(channel, opcode)
                  if f["type"] != "msg_header"]
    except Exception:
        return UNKNOWN
    strings = [v for f, v in zip(fields, values[1:]) if f["type"] == "string16"]
    if not strings or not all(isinstance(s, str) and s for s in strings):
        return OTHER
    if len(set(strings)) != 1:
        return OTHER                       # two different strings is a third experiment
    try:
        again = codec.encode(channel, opcode,
                             list(degenerate(codec, opcode, channel, strings[0])))
    except Exception:
        return OTHER
    return ENCSTRING if again == payload else OTHER


def fills_a_string(codec, opcode, channel="GAME_SMSG"):
    """Whether an `--encstring` plan actually reaches a `string16` in this opcode.

    NOT "does the field list contain one", and the difference is a measured one rather
    than a hypothetical. `degenerate` STOPS at a `nested_struct` -- the tail after it is
    the element layout, so an empty element list emits none of it -- and GAME_SMSG
    `0x019D` puts its `string16` behind exactly that. 87 opcodes carry a `string16`;
    **86** can be filled. The naive field scan called 0x019D an encstring experiment and
    the bytes it produced were all-zero, which is a row filed under the wrong
    experiment, which is this whole item over again one level down. Caught by the
    predictor-versus-wire check in `test_smsgsweep.py` section 9, on its first run.
    """
    try:
        fields = codec.fields_for(channel, opcode)
    except Exception:
        return False
    for f in fields:
        if f["type"] == "nested_struct":
            return False
        if f["type"] == "string16":
            return True
    return False


def planned_regime(codec, opcode, encstring=None, sets=None, channel="GAME_SMSG"):
    """The regime a plan with these flags will ACTUALLY put on the wire for this opcode.

    Not "did the operator pass --encstring". An opcode whose payload `--encstring` cannot
    move is sent byte-identically either way, so under the flag it is still an `ALLZERO`
    measurement -- 401 of the 487 catalogued opcodes are in that position, and treating
    the flag as the regime would have filed 401 duplicate rows describing one experiment.

    This is a STRUCTURAL prediction: it walks the field list and never encodes anything,
    where `regime_of_payload` encodes, decodes and re-encodes. Two paths that share no
    code is what makes their agreement -- checked over every encodable opcode in both
    regimes, 974 comparisons -- worth its exit code rather than a tautology.
    """
    if sets:
        return OTHER
    try:
        codec.fields_for(channel, opcode)
    except Exception:
        return UNKNOWN
    if encstring and fills_a_string(codec, opcode, channel):
        return ENCSTRING
    return ALLZERO


def ledger_key(opcode, regime):
    """One key per EXPERIMENT: the opcode, and the payload regime it was sent under.

    `ALLZERO` keeps the bare `0x0033` key that all 334 historical rows already use, so a
    migrated ledger stays readable by anything that only walks rows -- `--report`, and
    the external scripts that scan for `effect == "SILENT"`. Every other regime is
    suffixed `0x0033@encstring`, which is what keeps the two experiments apart.

    THE SUFFIX BREAKS `int(key, 16)`, DELIBERATELY. Any reader that turns a key straight
    into an opcode is a reader that would otherwise pool two regimes into one number, and
    a ValueError naming the key is the loud version of that. `parse_key` is the fix and
    it is one line.
    """
    if regime == ALLZERO:
        return f"0x{opcode:04X}"
    if regime not in REGIMES:
        raise ValueError(f"{regime!r} is not one of {REGIMES}. Refusing to invent a "
                         f"regime: an unrecognised one would key a row nothing looks up.")
    return f"0x{opcode:04X}@{regime}"


def parse_key(key):
    """(opcode, regime) from a ledger key. A BARE key returns regime None.

    None rather than ALLZERO, because a bare key is a key that never said, and the whole
    defect this dimension fixes is a row that never said being read as though it had.
    `regime_of_row` prefers the row's own field, which is what `migrate` writes.
    """
    op, _, reg = str(key).partition("@")
    return int(op, 16), (reg or None)


def regime_of_row(key, row):
    """A row's regime: its own field first, then the key, then UNKNOWN.

    An UNMIGRATED row -- bare key, no `regime` field -- is UNKNOWN and not ALLZERO. That
    is why `--resume` refuses an unmigrated ledger instead of quietly treating 334 rows
    as all-zero measurements: they almost all are, and "almost all" is not a measurement.
    """
    reg = (row or {}).get("regime")
    if reg:
        return reg
    return parse_key(key)[1] or UNKNOWN


def set_type(codec, opcode, idx, channel="GAME_SMSG"):
    """The declared type of an opcode's 1-based field `idx`, header excluded."""
    fields = [f for f in codec.fields_for(channel, opcode)
              if f["type"] != "msg_header"]
    if not 1 <= idx <= len(fields):
        raise ValueError(f"0x{opcode:04X} has {len(fields)} field(s); {idx} is outside "
                         f"1..{len(fields)}")
    return fields[idx - 1]["type"]


def sets_for(sets, opcode):
    """The {idx: val} that apply to ONE opcode: the global ones plus its own.

    `--set 2=1` is global and must name the same declared type everywhere (check_sets).
    `--set 0x0083:2=1` names one opcode and needs no such agreement, which is what lets
    six different second-gate experiments share one client launch instead of six.
    """
    out = dict(sets.get(None, {}))
    out.update(sets.get(opcode, {}))
    return out


def check_sets(codec, opcodes, sets, channel="GAME_SMSG"):
    """Refuse a --set that means a DIFFERENT field in different opcodes.

    A field index is not a field. `--set 1=1` across the ten opcodes whose first field is
    an `agent_id` is one experiment; across a mixed plan it is ten unrelated ones sharing
    a report, and the SILENT rows would be attributed to a change that never happened in
    them. So the index must name the same declared type in every opcode planned, and the
    refusal names the disagreement rather than dropping the odd one out.
    """
    for opcode, per in (sets or {}).items():
        if opcode is None:
            continue
        for idx in per:                       # a qualified set only has to fit ITS opcode
            set_type(codec, opcode, idx, channel)
    for idx in sorted((sets or {}).get(None, {})):
        kinds = {}
        for opcode in opcodes:
            kinds.setdefault(set_type(codec, opcode, idx), []).append(opcode)
        if len(kinds) > 1:
            raise ValueError(
                f"--set {idx}= names a different field in different opcodes: "
                + "; ".join(f"{t} in {' '.join('0x%04X' % o for o in v[:6])}"
                            for t, v in sorted(kinds.items()))
                + ". A field index is not a field -- plan them separately.")
    return True


def apply_set(values, sets):
    """Override individual fields by 1-based index: `--set 5=1`.

    THE POINT IS TO CHANGE ONE THING. The degenerate payload selects the ZERO branch of
    every gate a handler has, which is what the sweep's asserts have all turned out to be
    -- 0x0017's handler tests its fifth field against zero and skips a whole resource
    load when it is non-zero (0x00807d90, and the crash trace carries that chain by
    address). Filling every field with ones would test that gate and four other things at
    once, and a run that then behaved differently would not say which.
    """
    out = list(values)
    for idx, val in (sets or {}).items():
        if not 1 <= idx <= len(out):
            raise ValueError(f"field {idx} is outside this opcode's 1..{len(out)}")
        cur = out[idx - 1]
        if isinstance(cur, bool) or not isinstance(cur, (int, float)):
            raise ValueError(
                f"field {idx} holds {type(cur).__name__}, and --set only writes numbers. "
                f"A string16 gate wants a real encoded string, not a number cast to one.")
        out[idx - 1] = type(cur)(val)
    return out


def encodable(codec, channel="GAME_SMSG", encstring=None):
    """{opcode: values} for every opcode that encodes. Refusals are returned, not hidden."""
    good, refused = {}, {}
    for key in codec.channels[channel]["messages"]:
        opcode = int(key)
        try:
            vals = degenerate(codec, opcode, channel, encstring)
            codec.encode(channel, opcode, list(vals))
        except Exception as exc:                      # a refusal is a result
            refused[opcode] = f"{type(exc).__name__}: {exc}"
            continue
        good[opcode] = vals
    return good, refused


def unmigrated(ledger):
    """Keys whose regime was never recorded. Non-empty means `--migrate` has not run."""
    return sorted(k for k, row in ledger.items() if not (row or {}).get("regime"))
