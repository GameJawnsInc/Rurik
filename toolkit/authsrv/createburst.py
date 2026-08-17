r"""The create-burst census: what retail sends around WORLD_CREATE_AGENT, by kind.

Desk work for `studies/unitsetup/FINDINGS.md` §8, questions 2 and 7. Reads the
decrypted live captures and nothing else; writes nothing; launches nothing.

PREDICTIONS ON RECORD, stated before the first run (the probes.py rule -- a census
with no stated expectation can be rationalised into agreeing with anything):

  Q2 -- the 0x00F0 payload, split by the kind byte of the create it precedes.
  The corpus-wide distribution is already measured (studies/smsg/FINDINGS.md:
  0x0000 x315, 0x1000 x153, 0x2000 x4; never 0x10): what nobody has split is
  WHICH KIND carries the non-zero payloads. PREDICTION: they concentrate on
  kind-9 (NPC) creates -- 0x1000-shaped state reads like an ambient/burrow
  flag, and a player's own body arrives before anything can be true of it. If
  kind-5 creates ever carry non-zero, "always send 0 for the player" is the
  wrong v1 and divergence D2 needs a payload model, not just a send site.

  Q7 -- ordering among same-agent messages around a create. PREDICTION: no
  strict pairwise rule beyond the one already measured (0x00F0 immediately
  before its own 0x0020, 472/472) -- the study's most common full template
  (009F 00F0 0020 006D 0026) covers only 132/527 creates, so the post-create
  tail should vary, in which case OUR burst order (health -> profession ->
  flags) is a legal choice rather than a divergence. If some pair instead
  holds at 100% with n large, that pair is a RULE and the server must match it.

DECODED-VALUES CONVENTION, verified at run time before any counting (_sanity):
the codec's decoded list is offset +1 from the builder lists in agents.py --
npcdefs.py reads agent=v[1], model=v[2], speed=v[9], allegiance=v[12] for
0x0020, and property=v[1], agent=v[2], value=v[3] for 0x009F. The kind byte is
0x0020 v[4] (the value studies/smsg/FINDINGS.md's per-kind partition keys on).
_sanity refuses the run if 0x00F0's subject fails to match its paired create's
v[1] at >= 99%, because a wrong subject index here would produce a confident
census of nothing.

BUILD POOLING. Captures are pooled only if origin == "live" for every
connection (the npcdefs refusal, same reason). Counts are reported PER CAPTURE
as well as pooled, because the vault now holds captures from more than one
client build and a pooled-only figure would hide a per-build split.

    python toolkit/authsrv/createburst.py            # the census, writes nothing
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import npcdefs  # noqa: E402
import tape  # noqa: E402
from codec import Codec  # noqa: E402

CREATE = 0x0020
INITIAL_STATUS = 0x00F0
UPDATE_STATUS = 0x00F1
PROP_INT = 0x009F
SET_PROFESSION = 0x00A6
UPDATE_FLAGS = 0x0026
ATTACK_RATE = 0x0035
REMOVE = 0x0021

# Subject (agent id) index per opcode, decoded convention. 0x009F carries its
# agent second because the property id rides first.
SUBJECT = {
    CREATE: 1, INITIAL_STATUS: 1, UPDATE_STATUS: 1, SET_PROFESSION: 1,
    UPDATE_FLAGS: 1, ATTACK_RATE: 1, REMOVE: 1, 0x006D: 1,
    PROP_INT: 2,
}
KIND_FIELD = 4          # 0x0020 v[4]; smsg's 130 kind-5 / 342 kind-9 partition
PAYLOAD_FIELD = 2       # 0x00F0 [_, agent, effects]

# Q7's window around a create: generous in messages (the load burst packs 800
# messages into 0.79 s) and tight in time (so a mid-combat health update an
# hour later never reads as part of a spawn burst).
WINDOW_MSGS = 25
WINDOW_SECS = 2.0


def load_corpus():
    codec = Codec()
    corpus = []     # (capture, connection, [(t, op, values), ...])
    for capture_dir in npcdefs.live_captures():
        for row in tape.channel_files(capture_dir):
            connection = row["connection"]
            info, events = tape.load_tape(capture_dir, connection)
            origin = info.get("origin", "unknown")
            if origin != "live":
                raise SystemExit(
                    f"{capture_dir} {connection}: origin={origin!r}. This census "
                    f"is a claim about ArenaNet's server; one non-live connection "
                    f"in the pool and every number below is about something else.")
            msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            consumed, total, err = receipt
            if err is not None or consumed != total:
                raise SystemExit(
                    f"{capture_dir} {connection} framed {consumed}/{total} "
                    f"({err}); a partial decode drops the tail silently.")
            capture = info.get("capture") or os.path.basename(capture_dir)
            corpus.append((capture, connection, msgs))
    if not corpus:
        raise SystemExit("zero decodable live connections: the census measured "
                         "nothing, which is a failure, not an empty answer.")
    return corpus


def _sanity(corpus):
    """Pin the subject convention against the corpus before counting anything."""
    paired = matched = 0
    kinds = collections.Counter()
    for _, _, msgs in corpus:
        for i, (t, op, v) in enumerate(msgs):
            if op == CREATE:
                kinds[v[KIND_FIELD]] += 1
            if op != INITIAL_STATUS:
                continue
            subj = v[SUBJECT[INITIAL_STATUS]]
            for t2, op2, v2 in msgs[i + 1:i + 1 + 10]:
                if op2 == CREATE:
                    paired += 1
                    matched += (v2[SUBJECT[CREATE]] == subj)
                    break
    if paired and matched / paired < 0.99:
        raise SystemExit(
            f"subject convention FAILED: 0x00F0 v[1] matched the next create's "
            f"v[1] in only {matched}/{paired}. The +1 decode offset this census "
            f"assumes is wrong for this corpus; fix SUBJECT before trusting it.")
    bad = [k for k in kinds if k not in (0, 1, 5, 9)]
    print(f"sanity: 0x00F0->next-create subject match {matched}/{paired}; "
          f"create kinds {dict(sorted(kinds.items()))}"
          + (f"; UNEXPECTED kinds {bad}" if bad else ""))


def census_q2(corpus):
    """0x00F0 payload x kind of the create it immediately precedes."""
    per = {}    # capture -> Counter[(kind, payload)]
    orphans = collections.Counter()
    for capture, _, msgs in corpus:
        tally = per.setdefault(capture, collections.Counter())
        for i, (t, op, v) in enumerate(msgs):
            if op != INITIAL_STATUS:
                continue
            subj, payload = v[SUBJECT[INITIAL_STATUS]], v[PAYLOAD_FIELD]
            create = None
            for t2, op2, v2 in msgs[i + 1:i + 1 + 10]:
                if op2 == CREATE and v2[SUBJECT[CREATE]] == subj:
                    create = v2
                    break
            if create is None:
                orphans[capture] += 1
                continue
            tally[(create[KIND_FIELD], payload)] += 1
    print("\n== Q2: 0x00F0 payload by kind of the create it precedes ==")
    pooled = collections.Counter()
    for capture in sorted(per):
        pooled.update(per[capture])
        line = ", ".join(f"kind {k}: 0x{p:04X} x{n}"
                         for (k, p), n in sorted(per[capture].items()))
        print(f"  {capture}: {line or '(none)'}"
              + (f"  [{orphans[capture]} without a following create]"
                 if orphans[capture] else ""))
    print("  POOLED: " + ", ".join(f"kind {k}: 0x{p:04X} x{n}"
                                   for (k, p), n in sorted(pooled.items())))
    return pooled


def census_q7(corpus):
    """Same-agent opcode order around each create, and the pairwise verdicts."""
    templates = collections.Counter()   # (kind, pre-tuple, post-tuple)
    pairs = collections.Counter()       # (op_a, op_b) meaning a BEFORE b, post-create only
    n_creates = 0
    for _, _, msgs in corpus:
        for i, (t, op, v) in enumerate(msgs):
            if op != CREATE:
                continue
            n_creates += 1
            agent, kind = v[SUBJECT[CREATE]], v[KIND_FIELD]
            pre, post = [], []
            lo = max(0, i - WINDOW_MSGS)
            for j in range(lo, min(len(msgs), i + 1 + WINDOW_MSGS)):
                if j == i:
                    continue
                t2, op2, v2 = msgs[j]
                if abs(t2 - t) > WINDOW_SECS:
                    continue
                if op2 == CREATE and v2[SUBJECT[CREATE]] == agent:
                    # a re-create bounds this body's burst on that side
                    if j < i:
                        pre = []
                        continue
                    break
                si = SUBJECT.get(op2)
                if si is None or len(v2) <= si or v2[si] != agent:
                    continue
                label = (f"009F:{v2[1]}" if op2 == PROP_INT else f"{op2:04X}")
                (pre if j < i else post).append(label)
            templates[(kind, tuple(pre), tuple(post))] += 1
            for a in range(len(post)):
                for b in range(a + 1, len(post)):
                    if post[a] != post[b]:
                        pairs[(post[a], post[b])] += 1
    print(f"\n== Q7: same-agent order around {n_creates} creates "
          f"(window +/-{WINDOW_MSGS} msgs and {WINDOW_SECS:.0f} s) ==")
    print("  top templates (kind | before create | after create):")
    for (kind, pre, post), n in templates.most_common(12):
        print(f"    x{n:<4} kind {kind} | {' '.join(pre) or '-'} | "
              f"{' '.join(post) or '-'}")
    print("  pairwise order among post-create same-agent messages "
          "(a<b: a came first):")
    seen = set()
    for (a, b), n in sorted(pairs.items()):
        if (b, a) in seen:
            continue
        seen.add((a, b))
        rev = pairs.get((b, a), 0)
        total = n + rev
        verdict = ("RULE" if min(n, rev) == 0 and total >= 20 else
                   "lean" if max(n, rev) / total >= 0.9 else "free")
        print(f"    {a} before {b}: {n}/{total}  reverse {rev}  [{verdict}]")
    return templates, pairs


def main():
    corpus = load_corpus()
    for capture, connection, msgs in corpus:
        print(f"corpus: {capture} {connection}: {len(msgs)} GAME_SMSG messages")
    _sanity(corpus)
    census_q2(corpus)
    census_q7(corpus)


if __name__ == "__main__":
    main()
