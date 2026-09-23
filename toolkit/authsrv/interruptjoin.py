r"""The interrupt on retail's wire: every stop property classified, every [35] in full.

    python toolkit/authsrv/interruptjoin.py            # every live capture
    python toolkit/authsrv/interruptjoin.py --json
    python toolkit/authsrv/interruptjoin.py --batches  # print every [35] batch in wire order

WHY THIS EXISTS. `studies/castmech/FINDINGS.md` P1 and `studies/animref/FINDINGS.md`
D5 both say "no interrupt has ever been captured" and predict the wire shape from the
decoded handlers: the measured cancel burst (`[8, agent, 0]`, the family's stop, `0x00E2`)
PLUS a property-35 stagger on the interrupted agent, plus a recharge start (wiki:
"interrupted skills go on full recharge"). Two tapes recorded after those sentences
carry property 35 (DESKWORK-D5's survey). This reader re-derives both from the bytes,
on `deepwoundjoin.sequence`'s absolute base, and gives the two a DENOMINATOR: every
stop property in the corpus -- 59 (a spell's stop), 49 (an attack skill's stop), 3 (a
plain attack's stop) -- classified by what else the batch carries.

THE CLASSIFICATION, per stop word, by the SAME agent's companions inside one batch
(healjoin.batches, the corpus's 50 ms shoulder):

  knockdown   a [63, agent, f32] rides the batch  (prop 63 = knocked_down, animref 6)
  interrupt   a [35, agent, 0]   rides the batch  (prop 35 = interrupted, animref D5)
  cancel      neither -- NO [35] and NO [63] in the batch. The name is the cancel
              family's (castmech 3f); it does NOT mean "the player's own release":
              most stops are addressed to agents OTHER than the observer (the
              own / other split per property is printed), whose c2s this reader
              cannot see, so only the observer's own can be read as an Esc, a move
              or a retarget -- and of those, few sit near a c2s 0x0028 (printed).
              (Fix pass 2026-09-23, D5B-R6: the first cut's docstring and log
              called them all "the player's own release".)

THE PREDICTIONS, stated before the numbers (the survey's counts are the priors; a
reader that finds a third [35] refutes the write-up, not the tape):

  P1  DENOMINATORS: the corpus holds exactly 34 [59] and 12 [49] (the survey), and
      exactly 2 [35]. A third [35] FAILS the route's acceptance (b).
  P2  BOTH [35] name the connection's OWN player as the interrupted agent; the FIRST
      message of the interrupt FAMILY addressed to the victim in the batch ([8],
      [59] / [49] / [3], [35], E2, E5) IS the hold release `[8, agent, 0]` (the
      cancel burst's own first message, castmech 3f, 4 of 4 -- a stop or a bar
      message ahead of it FAILS this); and the run from there to the family's last
      is CONTIGUOUS: nothing addressed to anyone else sits inside it. (First cut,
      2026-09-23: "both BATCHES open with" -- FAILED as phrased, twice: the 50 ms
      batch carries the INTERRUPTER's landing ahead of the run ([46, 104, 0], the
      gain, [10, 25, 340], the word on the cast witness; two [20] impact visuals and
      the 0x00A7 on the swing witness), and the victim's [10] and word name the
      victim too, so "the victim's messages" also opens with the landing. The
      operand was wrong both times; the claim is about the interrupt's run.
      Re-stated, not fitted -- both other readings are printed. Fix pass, ENG-7:
      the re-statement's "the run opens with [8]" was TRUE BY CONSTRUCTION -- the
      run is sliced from the first [8, agent, 0] -- so the conjunct now reads the
      batch: nothing of the family precedes that hold release.)
  P3  THE CAST INTERRUPT (`20260916T213125` conn 57894, t ~ 484.333): the victim was
      mid-activation on a skill; the batch carries `[59, agent, 0]`, `0x00E2 [agent,
      skill, copy]` and an `0x00E5 [agent, skill, copy, recharge]` -- the recharge start
      castmech P1 predicted -- whose recharge is the skill's table recharge PLUS the
      interrupter's extra (Disrupting Chop 340: +20). The interrupter is named by the
      `[10, victim, skill]` skill-damage word in the same batch and by an `0x00A0 [50,
      interrupter, victim, 340]` announcement just before.
  P4  THE SWING INTERRUPT (`20260917T224104` conn 62557, t ~ 434.658): the victim was
      auto-attacking (no skill); the batch carries `[3, agent, 0]` (the plain attack's
      stop) and NO 0x00E2 / 0x00E5 -- there is no bar entry to release and nothing to
      recharge -- and names the interrupter through `[10, victim, 230]` (Lightning
      Javelin, "interrupts attacking foes").
  P5  A KNOCKDOWN IS NOT AN INTERRUPT ON THE WIRE: no batch holds both a [63] and a
      [35] on one agent (animref D5: one AvChar method, two durations, the value column
      the discriminator).

What this reader does NOT settle: an interrupt landing on a body or a hero (both
witnesses have the PLAYER as victim -- a body's interrupt batch is RECONSTRUCTION);
whether the +20 applies to a non-spell on other interrupters; the wire for a
knockdown-caused interrupt of a cast (no [63] rides a [59]/[49] batch, see P5).

Standard library only; reads the vault through `vaultpath`; refuses a tape that does
not frame whole (`deepwoundjoin.sequence`).
"""
import argparse
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import healjoin         # noqa: E402
import livewire         # noqa: E402
import spellhitjoin     # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_FLOAT = 0x00A2          # [prop, agent, f32]
OP_FLOAT_TARGET = 0x00A3   # [prop, target, cause, f32]
OP_SKILL_REFUSED = 0x00E2  # [agent, skill, copy]
OP_SKILL_RECHARGE = 0x00E5  # [agent, skill, copy, recharge]
OP_CMSG_CANCEL = 0x0028    # c2s: the Esc / cancel-action request
PROP_ATTACK_STOPPED = 3
PROP_HOLD = 8
PROP_SKILL_DAMAGE = 10
PROP_INTERRUPTED = 35
PROP_CAST_DROPPED = 45
PROP_ATTACK_SKILL_STOPPED = 49
PROP_ATTACK_SKILL_ACTIVATED = 50
PROP_SKILL_STOPPED = 59
PROP_SKILL_ACTIVATED = 60
PROP_KNOCKED_DOWN = 63
STOPS = (PROP_SKILL_STOPPED, PROP_ATTACK_SKILL_STOPPED, PROP_ATTACK_STOPPED)
ANNOUNCE_WINDOW = 4.0      # s; the interrupter's announce before the landing
CANCEL_WINDOW = 0.5        # s; a c2s cancel request before the stop

# The survey's priors (DESKWORK-D5, studies/deskwork/PLAN.md), carried as the
# reader's own predictions so the acceptance can redden.
EXPECT_59 = 34
EXPECT_49 = 12
EXPECT_35 = 2
WITNESSES = (("20260916T213125", "57894", 484.333, "cast"),
             ("20260917T224104", "62557", 434.658, "swing"))


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def _c2s(cap_dir, conn_file):
    """[(t, opcode)] of the client's own requests, on the capture clock, or []."""
    _conn, events, err = livewire.build_events(cap_dir, conn_file, "c2s")
    if err is not None or not events:
        return []
    msgs, _receipt = tape.decode_all(events, livewire._get_codec(),
                                     channel="GAME_CMSG", mask=livewire.CMSG_MASK,
                                     strict=False)
    return [(t, op) for t, op, _v in msgs]


def rows_of(seq, player, c2s=()):
    """(stops, thirty_fives) for one framed sequence.

    A STOP row: {"t", "prop", "agent", "own" (the connection's player),
    "kind" (knockdown / interrupt / cancel), "e2" (an 0x00E2 on the agent in
    the batch), "e5" (its recharges), "hold" (a [8, agent, 0] ahead of it),
    "c2s_cancel" (a c2s 0x0028 inside CANCEL_WINDOW before it)}.

    A [35] row: {"t", "agent", "own", "batch" (every message of the batch, in
    wire order, as (dt_ms, op, values)), "stop" (which stop rides with it),
    "e2" (the released skill), "e5" (the recharge starts), "interrupter" (the
    skill the [10] word names, or the 0x00A0 announce onto the victim inside
    ANNOUNCE_WINDOW), "interrupter_agent"}.
    """
    stops, thirty_fives = [], []
    ann = {}                 # victim -> (caster, skill, t) of the last announce ONTO it
    cancels = sorted(t for t, op in c2s if op == OP_CMSG_CANCEL)
    for batch in healjoin.batches(seq):
        t0 = batch[0][1]
        by_agent = collections.defaultdict(list)
        for _i, t, op, v in batch:
            if op == OP_INT_TARGET and v[1] in (PROP_ATTACK_SKILL_ACTIVATED,
                                                PROP_SKILL_ACTIVATED):
                ann[v[3]] = (v[2], v[4], t)
            if op in (OP_INT, OP_FLOAT) and len(v) > 2:
                by_agent[v[2]].append((op, v[1], v))
            elif op in (OP_SKILL_REFUSED, OP_SKILL_RECHARGE) and len(v) > 1:
                by_agent[v[1]].append((op, None, v))
        for _i, t, op, v in batch:
            if op != OP_INT or len(v) < 4:
                continue
            prop, agent = v[1], v[2]
            mates = by_agent.get(agent, ())
            props = {p for o, p, _v in mates if o in (OP_INT, OP_FLOAT)}
            e2 = [m[2][2] for m in mates if m[0] == OP_SKILL_REFUSED]
            e5 = [(m[2][2], m[2][4]) for m in mates if m[0] == OP_SKILL_RECHARGE]
            if prop in STOPS:
                if PROP_KNOCKED_DOWN in props:
                    kind = "knockdown"
                elif PROP_INTERRUPTED in props:
                    kind = "interrupt"
                else:
                    kind = "cancel"
                near = any(0.0 <= t - c <= CANCEL_WINDOW for c in cancels)
                stops.append({"t": round(t, 6), "prop": prop, "agent": agent,
                              "own": agent == player, "kind": kind,
                              "e2": e2, "e5": e5,
                              "hold": any(o == OP_INT and p == PROP_HOLD and _v[3] == 0
                                          for o, p, _v in mates),
                              "c2s_cancel": near})
            elif prop == PROP_INTERRUPTED:
                stop = [p for p in props if p in STOPS]
                word = [m[2][3] for m in mates
                        if m[0] == OP_INT and m[1] == PROP_SKILL_DAMAGE]
                a = ann.get(agent)
                by_ann = (a[1] if a is not None and 0.0 <= t - a[2] <= ANNOUNCE_WINDOW
                          else None)
                # TWO LISTS, both wire order, both as (op, values-after-opcode):
                #   victim_batch  every message ADDRESSED to the victim in the
                #                 batch -- the properties by their agent slot,
                #                 the 0x00CF gain, the E2/E5 by theirs. What a
                #                 server for THIS victim puts on the wire for
                #                 the whole event, the interrupter's landing
                #                 ([10] + word, the impacts) included.
                #   run           the INTERRUPT's own messages: from the first
                #                 [8, victim, 0] to the last of the family after
                #                 it ([59]/[49]/[3], E2, [35], E5, [8, victim, 1]),
                #                 contiguous in the batch. P2 is about this list.
                flat = [(bop, list(bv[1:])) for _bi, _bt, bop, bv in batch]

                def _names(bop, vals):
                    if bop in (OP_INT, OP_FLOAT, OP_FLOAT_TARGET, OP_INT_TARGET):
                        return len(vals) > 1 and vals[1] == agent
                    if bop in (OP_SKILL_REFUSED, OP_SKILL_RECHARGE, 0x00CF):
                        return len(vals) > 0 and vals[0] == agent
                    return False
                victim_batch = [(bop, vals) for bop, vals in flat if _names(bop, vals)]
                fam = {PROP_HOLD, PROP_INTERRUPTED, PROP_ATTACK_STOPPED,
                       PROP_ATTACK_SKILL_STOPPED, PROP_SKILL_STOPPED}
                starts = [k for k, (bop, vals) in enumerate(flat)
                          if bop == OP_INT and vals[:3] == [PROP_HOLD, agent, 0]]
                # P2's real conjunct: the first FAMILY message at the victim in
                # the whole batch is the hold release (a [59]/[49]/[3]/[35] or an
                # E2/E5 ahead of it would fail this; the run's own first message
                # cannot, it is sliced from the [8]).
                fam_first = next((k for k, (bop, vals) in enumerate(flat)
                                  if (bop == OP_INT and len(vals) > 1 and vals[1] == agent
                                      and vals[0] in fam)
                                  or (bop in (OP_SKILL_REFUSED, OP_SKILL_RECHARGE)
                                      and vals and vals[0] == agent)), None)
                run = []
                if starts:
                    i = starts[0]
                    j = i
                    for k in range(i, len(flat)):
                        bop, vals = flat[k]
                        if ((bop == OP_INT and len(vals) > 1 and vals[1] == agent
                             and vals[0] in fam)
                                or (bop in (OP_SKILL_REFUSED, OP_SKILL_RECHARGE)
                                    and vals and vals[0] == agent)):
                            j = k
                    run = flat[i:j + 1]
                thirty_fives.append({
                    "t": round(t, 6), "agent": agent, "own": agent == player,
                    "batch": [(round((bt - t0) * 1000.0, 1), bop, list(bv))
                              for _bi, bt, bop, bv in batch],
                    "victim_batch": victim_batch,
                    "run": run,
                    "run_contiguous": bool(run) and all(_names(bop, vals)
                                                        for bop, vals in run),
                    "run_opens_family": bool(starts) and fam_first == starts[0],
                    "stop": sorted(stop), "e2": e2, "e5": e5,
                    "interrupter": word[0] if word else by_ann,
                    "interrupter_agent": (a[0] if a is not None
                                          and 0.0 <= t - a[2] <= ANNOUNCE_WINDOW
                                          else None),
                    "knockdown_too": PROP_KNOCKED_DOWN in props})
    return stops, thirty_fives


def census(codec=None):
    """Every live capture, every game connection that frames whole."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="interruptjoin reads live captures")
    out = {"stops": [], "thirty_fives": [], "connections": 0, "refused": [],
           "p10": 0, "p63": 0}
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError) as exc:
                out["refused"].append((stamp, ch["connection"], str(exc)[:80]))
                continue
            out["connections"] += 1
            player = spellhitjoin.player_of(seq)
            out["p10"] += sum(1 for _i, _t, op, v in seq
                              if op == OP_INT and len(v) > 3 and v[1] == PROP_SKILL_DAMAGE)
            out["p63"] += sum(1 for _i, _t, op, v in seq
                              if op == OP_FLOAT and len(v) > 3 and v[1] == PROP_KNOCKED_DOWN)
            stops, tfs = rows_of(seq, player, _c2s(cap_dir, ch["file"]))
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
            for r in stops + tfs:
                r.update(capture=stamp, connection=ch["connection"], port=port,
                         player=player)
            out["stops"].extend(stops)
            out["thirty_fives"].extend(tfs)
    return out


def score(c):
    """The numbers P1-P5 are judged on."""
    stops = c["stops"]
    tfs = c["thirty_fives"]
    by_prop = collections.Counter(r["prop"] for r in stops)
    by_kind = collections.defaultdict(collections.Counter)
    for r in stops:
        by_kind[r["prop"]][r["kind"]] += 1
    witnesses = {}
    for stamp, port, t, what in WITNESSES:
        hit = [r for r in tfs if r["capture"] == stamp and r["port"] == port
               and abs(r["t"] - t) <= 0.5]
        witnesses[f"{stamp} {port} {what}"] = hit[0] if hit else None
    cast = witnesses.get(f"{WITNESSES[0][0]} {WITNESSES[0][1]} cast")
    swing = witnesses.get(f"{WITNESSES[1][0]} {WITNESSES[1][1]} swing")
    return {
        "connections": c["connections"],
        "refused": len(c["refused"]),
        "n59": by_prop.get(PROP_SKILL_STOPPED, 0),
        "n49": by_prop.get(PROP_ATTACK_SKILL_STOPPED, 0),
        "n3": by_prop.get(PROP_ATTACK_STOPPED, 0),
        "n35": len(tfs),
        "n63": c["p63"],
        "n10": c["p10"],
        "kinds": {p: dict(k) for p, k in sorted(by_kind.items())},
        "p1": (by_prop.get(PROP_SKILL_STOPPED, 0) == EXPECT_59
               and by_prop.get(PROP_ATTACK_SKILL_STOPPED, 0) == EXPECT_49
               and len(tfs) == EXPECT_35),
        "p2": bool(tfs) and all(r["own"] for r in tfs)
        and all(r["run"] and r["run_opens_family"] and r["run_contiguous"] for r in tfs),
        "p2_batch_opens_with_hold": sum(
            1 for r in tfs if r["batch"] and r["batch"][0][1] == OP_INT
            and r["batch"][0][2][1] == PROP_HOLD and r["batch"][0][2][2] == r["agent"]),
        "runs": {f"{r['capture']} {r['port']}": r["run"] for r in tfs},
        "p3": (cast is not None and PROP_SKILL_STOPPED in cast["stop"]
               and bool(cast["e2"]) and bool(cast["e5"]) and cast["interrupter"] == 340),
        "p3_detail": None if cast is None else {
            "released_skill": cast["e2"], "recharges": cast["e5"],
            "interrupter": cast["interrupter"],
            "interrupter_agent": cast["interrupter_agent"], "t": cast["t"]},
        "p4": (swing is not None and PROP_ATTACK_STOPPED in swing["stop"]
               and not swing["e2"] and not swing["e5"] and swing["interrupter"] == 230),
        "p4_detail": None if swing is None else {
            "stops": swing["stop"], "e2": swing["e2"], "e5": swing["e5"],
            "interrupter": swing["interrupter"], "t": swing["t"]},
        # P5 as registered: no batch holds a [63] and a [35] on one agent. (The
        # first cut ended this in `or True`, which made it no predicate at all --
        # fix pass, ENG-7. Whether a stop ever rides a [63] is `kinds`.)
        "p5": not any(r["knockdown_too"] for r in tfs),
        "knockdown_with_35": sum(1 for r in tfs if r["knockdown_too"]),
        "cancels_with_c2s_0028": sum(1 for r in stops if r["kind"] == "cancel"
                                     and r["c2s_cancel"]),
        "cancels": sum(1 for r in stops if r["kind"] == "cancel"),
        "own_stops": sum(1 for r in stops if r["own"]),
        # Per property: (addressed to the observer, addressed to another agent).
        # Only the first column can be the observer's own release.
        "own_by_prop": {p: (sum(1 for r in stops if r["prop"] == p and r["own"]),
                            sum(1 for r in stops if r["prop"] == p and not r["own"]))
                        for p in sorted(by_prop)},
        "own_cancels_with_c2s_0028": sum(1 for r in stops if r["kind"] == "cancel"
                                         and r["own"] and r["c2s_cancel"]),
        "witnesses": witnesses,
    }


def print_batch(r):
    print(f"   {r['capture']} conn {r['connection']} (player {r['player']}) "
          f"[35] at t={r['t']:.3f}, victim {r['agent']} "
          f"{'(the observer)' if r['own'] else '(NOT the observer)'}; stop {r['stop']}, "
          f"E2 releases {r['e2']}, E5 recharges {r['e5']}, interrupter skill "
          f"{r['interrupter']} by agent {r['interrupter_agent']}")
    for dt, op, v in r["batch"]:
        print(f"      +{dt:6.1f} ms  0x{op:04X} {v[1:]}")
    print(f"      the victim's messages ({len(r['victim_batch'])}): "
          + " ".join(f"0x{op:02X}{vals}" for op, vals in r["victim_batch"]))
    print(f"      the interrupt's run ({len(r['run'])}, contiguous {r['run_contiguous']}, "
          f"the family's first message at the victim is its [8] {r['run_opens_family']}): "
          + " ".join(f"0x{op:02X}{vals}" for op, vals in r["run"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--batches", action="store_true",
                    help="print every [35] batch in wire order")
    ap.add_argument("--stops", action="store_true",
                    help="print every stop row")
    args = ap.parse_args()
    c = census()
    sc = score(c)
    if args.json:
        sc["witnesses"] = {k: (None if v is None else {kk: vv for kk, vv in v.items()})
                           for k, v in sc["witnesses"].items()}
        print(json.dumps({"score": sc, "stops": c["stops"],
                          "thirty_fives": c["thirty_fives"]}, indent=1, default=str))
        return
    print(f"connections framed whole {sc['connections']} (refused {sc['refused']})")
    print(f"P1 denominators: [59] {sc['n59']} (expect {EXPECT_59}), [49] {sc['n49']} "
          f"(expect {EXPECT_49}), [3] {sc['n3']}, [35] {sc['n35']} (expect {EXPECT_35}), "
          f"[63] {sc['n63']}, [10] {sc['n10']} -> {'HOLDS' if sc['p1'] else 'FAILS'}")
    print(f"   by kind: {sc['kinds']}; per property (on the observer, on another agent): "
          f"{sc['own_by_prop']}; cancels {sc['cancels']}, of which a c2s 0x0028 inside "
          f"{CANCEL_WINDOW} s {sc['cancels_with_c2s_0028']} (the observer's own cancels "
          f"with one: {sc['own_cancels_with_c2s_0028']})")
    print(f"P2 both [35] on the observer, the FIRST family message at the victim the hold "
          f"release [8, agent, 0], the run contiguous: "
          f"{'HOLDS' if sc['p2'] else 'FAILS'} (batches whose FIRST message is the "
          f"victim's hold release: {sc['p2_batch_opens_with_hold']} of {sc['n35']} -- "
          f"the interrupter's landing precedes the run)")
    print(f"P3 the cast interrupt ([59] + E2 + E5, interrupter 340): "
          f"{'HOLDS' if sc['p3'] else 'FAILS'} {sc['p3_detail']}")
    print(f"P4 the swing interrupt ([3], no E2/E5, interrupter 230): "
          f"{'HOLDS' if sc['p4'] else 'FAILS'} {sc['p4_detail']}")
    print(f"P5 [63] riding a [35] batch: {sc['knockdown_with_35']} "
          f"(0 predicted) -> {'HOLDS' if sc['p5'] else 'FAILS'}")
    if args.batches:
        print("the [35] batches, wire order, dt from the batch's first message:")
        for r in c["thirty_fives"]:
            print_batch(r)
    if args.stops:
        for r in sorted(c["stops"], key=lambda r: (r["capture"], r["connection"], r["t"])):
            print(f"   {r['capture']} {r['port']} t={r['t']:.3f} [{r['prop']}, {r['agent']}] "
                  f"{r['kind']:9s} own={r['own']} hold={r['hold']} e2={r['e2']} "
                  f"e5={r['e5']} c2s0028={r['c2s_cancel']}")


if __name__ == "__main__":
    main()
