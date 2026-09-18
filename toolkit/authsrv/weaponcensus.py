"""weaponcensus.py -- what every body on a retail tape HOLDS, and how it attacks with it.

    python toolkit/authsrv/weaponcensus.py                     # the whole live corpus
    python toolkit/authsrv/weaponcensus.py --capture 20260914T005758
    python toolkit/authsrv/weaponcensus.py --shooters          # one row per ranged attacker
    python toolkit/authsrv/weaponcensus.py --attackers         # one row per attacker
    python toolkit/authsrv/weaponcensus.py --skill-shots       # one row per SKILL shot

THE HOLE THIS FILLS (studies/weapons/PLAN.md, WEAPONS-W0). The server wires four
weapon types and took every other type's numbers from the wiki. The tapes already
name every body's weapon and nobody had joined the two halves:

  0x006D [agent, leadhand, offhand]   which ITEM ids a body holds (every NPC, never
                                      a player)
  0x006E [agent, leadhand, offhand, five armour pieces]
                                      the same for a PLAYER's body -- WEAPONS-Q8; the
                                      observer's own 0x0147 weapon set names the same
                                      two items
  0x0161 [item, file, TYPE, ..., model, ..., [words]]
                                      that item's type and its modifier words
  0x0035 [agent, f32 base, f32 modifier]
                                      the body's ATTACK DURATION, in retail's own
                                      words -- sent at a body's attack start, so the
                                      base per weapon type needs no stopwatch at all
  0x00A0 [4, agent, target, 0]        a swing (or a shot) starts
  0x00A4 [shooter, aim, u16, flight, PROJECTILE, handle, arrow]
                                      the projectile leaves
  0x00A7 [shooter, handle, KIND]      ... and arrives; KIND is the held weapon's
                                      587 damage type (WEAPONS-C9)
  0x00A3 [16 | 17, target, source, -x]  the hit's word

Five questions, each answered per body and never in aggregate:

  SPEEDS     0x0035's base duration joined to the type the body held when it was told

  TYPES      which item types sit in leadhands and offhands, and which modifier
             identifiers each type carries (633 requirement, 587 damage type,
             584 range, 609, 617 ...)
  ATTACKERS  each attacker's clean start-to-start gaps, joined to the type it holds
  SHOOTERS   each ranged attacker: the start->launch delay (WEAPONS-C1: it is the
             swing's WINDUP), launch + flight against the word, the launch closed by
             its 0x00A7, and 0x00A4 field 5 against the held weapon's own 617 word
             (WEAPONS-C3: they are the same number)
  A WEAPON SHOT is a launch whose shooter's latest event is a swing start, not a
  skill's (0x00E3 / 0x00E4 / 0x00E5, or the 0x00A0 property 50 / 60 a hostile's skill
  announces itself by) -- a spell's projectile (field 5 in the hundreds) and a bow
  attack skill's arrow are different objects and are counted apart.
  SKILL SHOTS  the complement (WEAPONS-W2c): a launch whose shooter's latest event is
             a skill's -- a player's 0x00E5 (its launch rides the E5's own batch) or
             a body's announcement -- joined to the skill id, the projectile, the
             arrow flag, the arrival's kind, whether a 46 sits beside the launch
             (retail: never), and the event-to-launch delay (a body's is the
             weapon's windup)

Nothing here knows a right answer; the test pins what the tapes said.

Standard library only. The pure functions take a decoded s2c list and are tested
without a vault; the CLI needs the live corpus.
"""
import argparse
import collections
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ITEM, HANDS, PLAYER_HANDS, SPEED = 0x0161, 0x006D, 0x006E, 0x0035
PINT, PINT_T, PFLOAT_T = 0x009F, 0x00A0, 0x00A3
LAUNCH, ARRIVE = 0x00A4, 0x00A7
E3, E4, E5 = 0x00E3, 0x00E4, 0x00E5
START, FAIL = 4, 38
ANNOUNCED = (50, 60)            # 0x00A0: an attack skill / a spell names itself
WORDS = (16, 17, 55)            # damage, critical, armour-ignoring
CLEAN_GAP = 4.0                 # a longer gap is a pause, not a swing interval
SHOT_WINDOW = 3.0               # a launch belongs to a start at most this far back
PROJECTILE, REQUIREMENT, DAMAGE_TYPE, DAMAGE_RANGE = 617, 633, 587, 584


def _f32(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def word_fields(word):
    """(identifier, arg, arg2) of one modifier word, or None for a word the client's
    own walker skips -- the layout `clientscan/itemmods.decode` read out of the parser
    (bits 29-20, 17-8, 7-0; bits 31-30 == 3 or bit 18 set -> skipped)."""
    w = int(word) & 0xFFFFFFFF
    if (w >> 30) & 3 == 3 or (w >> 18) & 1:
        return None
    return (w >> 20) & 0x3FF, (w >> 8) & 0x3FF, w & 0xFF


def _flat(mods):
    for m in mods or ():
        yield int(m[0] if isinstance(m, (list, tuple)) else m)


def items_of(s2c):
    """{item id: {"type", "model", "words": [(identifier, arg, arg2)]}} -- last wins."""
    out = {}
    for _t, op, v in s2c:
        if op == ITEM and len(v) > 12:
            mods = v[-1] if isinstance(v[-1], (list, tuple)) else ()
            out[v[1]] = {"type": v[3], "model": v[10],
                         "words": [f for f in map(word_fields, _flat(mods)) if f]}
    return out


def hands_timeline(s2c):
    """{agent: [(t, leadhand item, offhand item)]} in wire order -- 0x006D for an NPC,
    0x006E for a player. A timeline, not a last-wins dict: a player swaps weapons."""
    out = collections.defaultdict(list)
    for t, op, v in s2c:
        if op in (HANDS, PLAYER_HANDS) and len(v) > 3:
            if not out[v[1]] or out[v[1]][-1][1:] != (v[2], v[3]):
                out[v[1]].append((t, v[2], v[3]))
    return out


def held_at(timeline, agent, t):
    """(leadhand, offhand) item ids `agent` held at `t`, or None if never told.
    Before its first message a body holds what that first message says -- retail
    sends the hands behind the body's create, and a swing cannot precede both."""
    rows = timeline.get(agent)
    if not rows:
        return None
    held = rows[0]
    for row in rows:
        if row[0] <= t:
            held = row
    return held[1], held[2]


def held_type(items, item_id):
    """The item type in a hand: 0 for an empty hand, None for an undeclared item."""
    if not item_id:
        return 0
    row = items.get(item_id)
    return row["type"] if row else None


def word_of(items, item_id, identifier):
    """The first (arg, arg2) of `identifier` on an item, or None."""
    for ident, arg, arg2 in (items.get(item_id) or {}).get("words", ()):
        if ident == identifier:
            return arg, arg2
    return None


def types_census(s2c):
    """(leadhand Counter, offhand Counter, {type: {identifier: Counter((arg, arg2))}})."""
    items, hands = items_of(s2c), hands_timeline(s2c)
    lead, off = collections.Counter(), collections.Counter()
    words = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for _agent, rows in hands.items():
        for _t, l, o in rows:                    # one count per HOLDING, swaps included
            lead[held_type(items, l)] += 1
            off[held_type(items, o)] += 1
            for it in (l, o):
                for ident, arg, arg2 in (items.get(it) or {}).get("words", ()):
                    words[items[it]["type"]][ident][(arg, arg2)] += 1
    return lead, off, words


def speeds(s2c):
    """One row per 0x0035: the body, its base duration and modifier as retail sent
    them, and the type (and a bow's 609 class) it held at that instant."""
    items, hands = items_of(s2c), hands_timeline(s2c)
    rows = []
    for t, op, v in s2c:
        if op == SPEED and len(v) > 3:
            held = held_at(hands, v[1], t)
            lead = held[0] if held else None
            rows.append({"agent": v[1], "t": t, "base": round(_f32(v[2]), 4),
                         "modifier": round(_f32(v[3]), 4), "lead": lead,
                         "type": None if held is None else held_type(items, lead),
                         "w609": (word_of(items, lead, 609) or (None,))[0]})
    return rows


def _events(s2c):
    starts = collections.defaultdict(list)       # agent -> [t]
    skills = collections.defaultdict(list)       # agent -> [t] of a skill's messages
    launches = collections.defaultdict(list)     # agent -> [(t, v)]
    arrivals = collections.defaultdict(list)     # agent -> [(t, handle)]
    words = collections.defaultdict(list)        # source -> [t]
    for t, op, v in s2c:
        if op == PINT_T and len(v) > 3 and v[1] == START:
            starts[v[2]].append(t)
        elif op == PINT_T and len(v) > 3 and v[1] == FAIL:
            words[v[3]].append(t)                # [38, TARGET, attacker, reason]
        elif op == PINT_T and len(v) > 3 and v[1] in ANNOUNCED:
            skills[v[2]].append(t)
        elif op in (E3, E4, E5) and len(v) > 1:
            skills[v[1]].append(t)
        elif op == LAUNCH and len(v) > 7:
            launches[v[1]].append((t, v))
        elif op == ARRIVE and len(v) > 3:
            arrivals[v[1]].append((t, v[2], v[3]))
        elif op == PFLOAT_T and len(v) > 4 and v[1] in WORDS:
            words[v[3]].append(t)
    return starts, skills, launches, arrivals, words


def _mode(gaps, width=0.02):
    """(centre, n) of the densest +-width cluster -- a hostile's gaps are a mixture."""
    best = max(gaps, key=lambda g: sum(1 for x in gaps if abs(x - g) < width))
    cluster = [x for x in gaps if abs(x - best) < width]
    return statistics.median(cluster), len(cluster)


def attackers(s2c, min_gaps=3):
    """One row per agent with >= min_gaps clean start-to-start gaps (no skill between)."""
    items, hands = items_of(s2c), hands_timeline(s2c)
    starts, skills, launches, _arr, _words = _events(s2c)
    rows = []
    for agent, ts in starts.items():
        sk = skills.get(agent, ())
        by_weapon = collections.defaultdict(list)       # lead item -> clean gaps
        for a, b in zip(ts, ts[1:]):
            held = held_at(hands, agent, a)
            if (b - a < CLEAN_GAP and not any(a <= k <= b for k in sk)
                    and held == held_at(hands, agent, b)):
                by_weapon[held[0] if held else None].append(b - a)
        for lead, gaps in by_weapon.items():
            if len(gaps) < min_gaps:
                continue
            mode, n_mode = _mode(gaps)
            rows.append({"agent": agent, "lead": lead, "gaps": gaps,
                         "mode": mode, "n_mode": n_mode,
                         "type": None if lead is None else held_type(items, lead),
                         "launches": len(launches.get(agent, ()))})
    return rows


def shooters(s2c):
    """One row per agent with a WEAPON shot (a launch behind a swing start)."""
    items, hands = items_of(s2c), hands_timeline(s2c)
    starts, skills, launches, arrivals, words = _events(s2c)
    table = {}

    def row_for(agent, lead):
        if (agent, lead) not in table:
            table[(agent, lead)] = {
                "agent": agent, "lead": lead,
                "type": None if lead is None else held_type(items, lead),
                "w617": (word_of(items, lead, PROJECTILE) or (None, None))[1],
                "w609": (word_of(items, lead, 609) or (None, None))[0],
                "w587": (word_of(items, lead, DAMAGE_TYPE) or (None, None))[0],
                "arrival_kind": collections.Counter(),
                "field5": collections.Counter(), "field7": collections.Counter(),
                "start_to_launch": [], "flight": [], "word_error": [],
                "closed": 0, "shots": 0}
        return table[(agent, lead)]

    for agent, shots in launches.items():
        ts, sk = starts.get(agent, ()), skills.get(agent, ())
        for t, v in shots:
            before = [s for s in ts if 0.0 <= t - s < SHOT_WINDOW]
            if not before or any(before[-1] < k <= t for k in sk):
                continue                                  # a skill's projectile
            held = held_at(hands, agent, t)
            row = row_for(agent, held[0] if held else None)
            flight = _f32(v[4])
            row["shots"] += 1
            row["field5"][v[5]] += 1
            row["field7"][v[7]] += 1
            row["start_to_launch"].append(t - before[-1])
            row["flight"].append(flight)
            hit = [w for w in words.get(agent, ()) if t <= w < t + flight + 0.25]
            if hit:
                row["word_error"].append(min(hit, key=lambda w: abs(w - t - flight))
                                         - t - flight)
            closing = [k for a, h, k in arrivals.get(agent, ())
                       if h == v[6] and t <= a < t + flight + 0.25]
            if closing:
                row["closed"] += 1
                row["arrival_kind"][closing[0]] += 1
    return [r for r in table.values() if r["shots"]]


def skill_shots(s2c):
    """One row per SKILL shot (WEAPONS-W2c): a launch whose shooter's latest event
    inside SHOT_WINDOW is a skill's -- a player's 0x00E4 / 0x00E5, or a body's
    [50 | 60, shooter, target, skill] announcement -- rather than a plain [4] start.
    The complement of shooters(). `event_to_launch` is measured from that event;
    `close46` says whether a [46, shooter, 0] sits within 50 ms of the launch."""
    items, hands = items_of(s2c), hands_timeline(s2c)
    players = {v[1] for _t, op, v in s2c if op == PLAYER_HANDS and len(v) > 3}
    events = collections.defaultdict(list)       # agent -> [(t, kind, skill)]
    arrivals = collections.defaultdict(list)     # agent -> [(t, handle, kind)]
    words = collections.defaultdict(list)        # source -> [t]
    closes = collections.defaultdict(list)       # agent -> [t] of a 46
    for t, op, v in s2c:
        if op == PINT_T and len(v) > 4 and v[1] == START:
            events[v[2]].append((t, "start", None))
        elif op == PINT_T and len(v) > 4 and v[1] in ANNOUNCED:
            events[v[2]].append((t, f"announce{v[1]}", v[4]))
        elif op in (E4, E5) and len(v) > 2:
            events[v[1]].append((t, "E4" if op == E4 else "E5", v[2]))
        elif op == ARRIVE and len(v) > 3:
            arrivals[v[1]].append((t, v[2], v[3]))
        elif op == PFLOAT_T and len(v) > 4 and v[1] in WORDS:
            words[v[3]].append(t)
        elif op == PINT and len(v) > 2 and v[1] == 46:
            closes[v[2]].append(t)
    rows = []
    for t, op, v in s2c:
        if op != LAUNCH or len(v) < 8:
            continue
        agent = v[1]
        before = [e for e in events.get(agent, ()) if 0.0 <= t - e[0] < SHOT_WINDOW]
        if not before or before[-1][1] == "start":
            continue                                  # a weapon shot: shooters()
        ev_t, kind, skill = before[-1]
        held = held_at(hands, agent, t)
        lead = held[0] if held else None
        flight = _f32(v[4])
        closing = [k for a, h, k in arrivals.get(agent, ())
                   if h == v[6] and t <= a < t + flight + 0.25]
        hit = [w for w in words.get(agent, ()) if t <= w < t + flight + 0.25]
        rows.append({
            "agent": agent, "player": agent in players, "skill": skill,
            "event": kind, "event_to_launch": t - ev_t,
            "type": None if lead is None else held_type(items, lead),
            "w617": ((word_of(items, lead, PROJECTILE) or (None, None))[1]
                     if lead is not None else None),
            "projectile": v[5], "arrow": v[7], "handle": v[6], "flight": flight,
            "kind": closing[0] if closing else None, "closed": bool(closing),
            "word_error": ((min(hit, key=lambda w: abs(w - t - flight)) - t - flight)
                           if hit else None),
            "close46": any(abs(c - t) < 0.05 for c in closes.get(agent, ()))})
    return rows


def arrival_verdict(row):
    """How a shooter's 0x00A7 third field compares with its weapon's 587 word."""
    if row["w587"] is None:
        return "weapon has no 587" if row["type"] is not None else "no weapon row"
    return "kind == 587" if set(row["arrival_kind"]) == {row["w587"]} else "MISMATCH"


def projectile_verdict(row):
    """How a shooter's 0x00A4 field 5 compares with the weapon it holds."""
    if row["type"] is None:
        return "no weapon row"
    if row["w617"] is None:
        return "weapon has no 617"
    return "field 5 == 617" if set(row["field5"]) == {row["w617"]} else "MISMATCH"


# ------------------------------------------------------------------ the corpus

def connections(stamp=None):
    import livewire                                           # noqa: PLC0415
    for capdir, gf in livewire.live_connections():
        name = os.path.basename(capdir)
        if stamp and name != stamp:
            continue
        try:
            _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        except Exception:                                       # noqa: BLE001
            continue
        yield name, gf, [(t, op, list(v)) for t, d, op, v in merged if d == "s2c"]


def corpus(stamp=None):
    """Everything the CLI prints, as one dict -- what test_weaponcensus pins."""
    lead, off = collections.Counter(), collections.Counter()
    words = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    att, sho, ssh = [], [], []
    spd = collections.defaultdict(collections.Counter)      # (type, 609) -> base
    for name, gf, s2c in connections(stamp):
        for r in speeds(s2c):
            spd[(r["type"], r["w609"])][r["base"]] += 1
        l, o, w = types_census(s2c)
        lead.update(l)
        off.update(o)
        for typ, idents in w.items():
            for ident, c in idents.items():
                words[typ][ident].update(c)
        for r in attackers(s2c):
            att.append(dict(r, capture=name, conn=gf))
        for r in shooters(s2c):
            sho.append(dict(r, capture=name, conn=gf))
        for r in skill_shots(s2c):
            ssh.append(dict(r, capture=name, conn=gf))
    return {"lead": lead, "off": off, "words": words, "attackers": att,
            "shooters": sho, "speeds": spd, "skill_shots": ssh}


def _p50(xs):
    return statistics.median(xs) if xs else None


def report(c, show_attackers=False, show_shooters=False, out=sys.stdout,
           show_skill_shots=False):
    p = lambda *a: print(*a, file=out)                          # noqa: E731
    p("LEADHAND item types (bodies):", sorted(c["lead"].items(), key=lambda kv: -kv[1]))
    p("OFFHAND  item types (bodies):", sorted(c["off"].items(), key=lambda kv: -kv[1]))
    p("\nmodifier identifiers per held type -- identifier: bodies (distinct args)")
    for typ in sorted(c["words"], key=str):
        cells = [f"{i}: {sum(k.values())} ({len(k)})"
                 for i, k in sorted(c["words"][typ].items())]
        p(f"  type {typ}: " + ", ".join(cells))
    p("\nSPEEDS: 0x0035's base duration by (held type, a bow's 609) -- retail's own number")
    for key, bases in sorted(c["speeds"].items(), key=str):
        p(f"  {key}: {sorted(bases.items(), key=lambda kv: -kv[1])}")
    by = collections.defaultdict(list)
    for r in c["attackers"]:
        by[r["type"]].append(r)
    p("\nATTACKERS by the type they hold (None = the tape never names that body's hands)")
    for typ, rows in sorted(by.items(), key=lambda kv: str(kv[0])):
        modes = collections.Counter(round(r["mode"], 2) for r in rows)
        p(f"  type {typ}: {len(rows)} attackers, {sum(len(r['gaps']) for r in rows)} "
          f"clean gaps, modes {sorted(modes.items())}")
        if show_attackers:
            for r in sorted(rows, key=lambda r: -len(r["gaps"])):
                p(f"     {r['capture']} agent {r['agent']:5d} gaps {len(r['gaps']):4d} "
                  f"mode {r['mode']:.3f} x{r['n_mode']:<4d} item {r['lead']} launches {r['launches']}")
    verdicts = collections.Counter(projectile_verdict(r) for r in c["shooters"])
    p(f"\nSHOOTERS: {len(c['shooters'])}, "
      f"{sum(r['shots'] for r in c['shooters'])} weapon shots;  0x00A4 field 5 vs the "
      f"held weapon's 617: {dict(verdicts)}")
    kinds = collections.Counter(arrival_verdict(r) for r in c["shooters"])
    p(f"  0x00A7 field 3 vs the held weapon's 587 damage type: {dict(kinds)}")
    windups = collections.defaultdict(list)
    for r in c["shooters"]:
        windups[round(_p50(r["start_to_launch"]), 2)].extend(r["start_to_launch"])
    for k, xs in sorted(windups.items()):
        p(f"  start->launch class {k:.2f}: n {len(xs)}  p50 {_p50(xs):.4f}")
    errs = [e for r in c["shooters"] for e in r["word_error"]]
    shots = sum(r["shots"] for r in c["shooters"])
    if errs:
        p(f"  launch + flight vs the word: n {len(errs)}  p50 |err| "
          f"{_p50([abs(e) for e in errs]) * 1000:.1f} ms;  closed by 0x00A7: "
          f"{sum(r['closed'] for r in c['shooters'])} of {shots}")
    arrow = collections.Counter()
    for r in c["shooters"]:
        for f5, n in r["field5"].items():
            for f7, m in r["field7"].items():
                if len(r["field5"]) == 1 and len(r["field7"]) == 1:
                    arrow[(f5, f7)] += n
    p(f"  (field 5, field 7) over single-valued shooters: {sorted(arrow.items())}")
    if show_shooters:
        for r in sorted(c["shooters"], key=lambda r: -r["shots"]):
            p(f"     {r['capture']} agent {r['agent']:5d} type {r['type']} 617 {r['w617']} "
              f"609 {r['w609']} shots {r['shots']:3d} field5 {dict(r['field5'])} "
              f"field7 {dict(r['field7'])} start->launch {_p50(r['start_to_launch']):.3f} "
              f"flight {min(r['flight']):.3f}..{max(r['flight']):.3f}  "
              f"{projectile_verdict(r)}")
    ss = c.get("skill_shots") or []
    p(f"\nSKILL SHOTS: {len(ss)} (a launch behind a skill's E5 / announcement, not a swing "
      f"start; WEAPONS-W2c);  closed by 0x00A7: {sum(r['closed'] for r in ss)};  "
      f"a 46 within 50 ms of the launch: {sum(r['close46'] for r in ss)}")
    by = collections.Counter((r["player"], r["type"], r["skill"], r["projectile"],
                              r["arrow"], r["kind"]) for r in ss)
    for k, n in sorted(by.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        p(f"  {n:4d}  {'player' if k[0] else 'body  '} type {k[1]} skill {k[2]} "
          f"projectile {k[3]} arrow {k[4]} kind {k[5]}")
    delays = collections.defaultdict(list)
    for r in ss:
        delays[(r["player"], r["skill"], r["event"])].append(r["event_to_launch"])
    for k, xs in sorted(delays.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
        p(f"  {'player' if k[0] else 'body  '} skill {k[1]} {k[2]}->launch: n {len(xs)}  "
          f"p50 {_p50(xs):.4f}  min {min(xs):.3f}  max {max(xs):.3f}")
    errs = [r["word_error"] for r in ss if r["word_error"] is not None]
    if errs:
        p(f"  launch + flight vs the word: n {len(errs)}  p50 |err| "
          f"{_p50([abs(e) for e in errs]) * 1000:.1f} ms")
    if show_skill_shots:
        for r in ss:
            p(f"     {r['capture']} agent {r['agent']:5d} {'player' if r['player'] else 'body'} "
              f"type {r['type']} skill {r['skill']} {r['event']} +{r['event_to_launch']:.3f} "
              f"projectile {r['projectile']} arrow {r['arrow']} handle {r['handle']} "
              f"flight {r['flight']:.3f} kind {r['kind']} 46 {r['close46']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", help="one live capture's stamp (default: all)")
    ap.add_argument("--attackers", action="store_true", help="one row per attacker")
    ap.add_argument("--shooters", action="store_true", help="one row per ranged attacker")
    ap.add_argument("--skill-shots", action="store_true", help="one row per SKILL shot")
    a = ap.parse_args(argv)
    report(corpus(a.capture), a.attackers, a.shooters, show_skill_shots=a.skill_shots)
    return 0


if __name__ == "__main__":
    sys.exit(main())
