#!/usr/bin/env python3
r"""CASTAI-H1 scored off the live healer capture (monsterai FINDINGS 18.6).

    python studies/monsterai/review/healerrun.py                  # 20261008T132845
    python studies/monsterai/review/healerrun.py --rows           # plus one line per heal
    python studies/monsterai/review/healerrun.py --capture STAMP

WHAT THIS SCORES. One capture (default 20261008T132845, the owner's RIDERS run of
2026-10-08 on the secondary account, build 38974, plan live_riders_h1.txt, whose steps
setup / zone / fights / front / calm are castai_h1_healer.txt's verbatim): every game
connection that carries a party HERO (0x01C2) which completes a heal. On that tape it is
one connection, the Plains of Jarin (map 430), the observer and the hero Koss -- a
Warrior with a Monk secondary and four heals on his bar, NOT a Monk primary (the owner
had no Monk hero unlocked; recorded, not hidden). The hero ran in Avoid Combat
(c2s 0x0015 [hero, 2] at the fights step) for the whole explorable.

READERS REUSED: castethogram (Conn, build_casts, health_before -- [32]-aware since
2026-10-08, see PROP_MAX_HP_REACHED there -- applies_live_before), rechargeprobe
(activation / recharge out of the capture's own build's exe), shoutjoin (the observer),
zaishenrun (HEAL_SKILLS, ORISON, the Z1 floors' house style).

THE HEALS are a completed cast by the hero of a skill in zaishenrun.HEAL_SKILLS, or
1396, the skill the owner's screen named Word of Comfort; its heal is OBSERVED on the
wire (the targeted [55] at its landing), which is what puts it in the set, not the name.

THE PREDICTIONS are FINDINGS 18's, registered 2026-09-28 before the run:

  H1.P1  every heal lands on a HURT ally (the target's health_before < 0.99 at the
         announce), the most-hurt first in >= 80 % of casts where two or more are hurt.
         Floor: 20 heals on ANOTHER ally (not the caster).
  H1.P2  Orison of Healing (281) only once the ally has lost at least what it heals --
         scored on the OBSERVER only, where health is exact; the deficit at the announce
         against the heal word the cast landed. No floor was registered.
  H1.P3  no enchantment re-cast on an ally still carrying it (applies_live_before on the
         target at the announce, the same skill). No floor was registered.
  H1.P4  out of combat the healer heals the hurt party and then stops; nothing is cast at
         a full-health ally. SCORER'S RULE, written after the run (the plan's 'calm'
         step was pressed through and its case happened inside 'fights' -- the owner's
         notes; so the windows are chosen POST HOC and are labelled so): a calm window is
         a stretch of >= 15 s after a party member's last damage word with no further
         damage word on the party; inside it every heal must land on a hurt ally, and
         none may follow the moment the whole party reads full.

Below a registered floor a verdict is NULL and its numbers are still printed.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _p in (HERE, os.path.join(ROOT, "toolkit"), os.path.join(ROOT, "toolkit", "authsrv"),
           os.path.join(ROOT, "toolkit", "schema"), os.path.join(ROOT, "toolkit", "clientscan")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import castethogram as ce                                    # noqa: E402
import livewire                                              # noqa: E402
import rechargeprobe                                         # noqa: E402
import shoutjoin                                             # noqa: E402
import tape                                                  # noqa: E402
import zaishenrun                                            # noqa: E402

DEFAULT_CAPTURE = "20261008T132845"
WORD_OF_COMFORT = 1396          # named by the owner's screen; its heal is on the wire
HEALS = set(zaishenrun.HEAL_SKILLS) | {WORD_OF_COMFORT}
ORISON = 281
HURT = 0.99
FLOOR_P1 = 20                   # FINDINGS 18, H1.P1
CALM_S = 15.0                   # H1.P4, SCORER'S RULE (post hoc)


def connections(capdir, stamp):
    """[(port, Conn, rows)] for every whole game connection with a party hero."""
    table = ce.skill_rows()
    exe = rechargeprobe._exe_tables()
    out = []
    for ch in tape.channel_files(capdir):
        if not ch["file"].startswith("game-"):
            continue
        _c, merged, ok = livewire.decode_conn(capdir, ch["file"])
        if not ok:
            print(f"  [refused] {ch['file']}: byte accounting open", flush=True)
            continue
        ver = tape.client_version(capdir, ch["connection"])
        observer, _p, _why = shoutjoin.observer_of(merged)
        if observer is None:
            continue
        port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
        conn = ce.Conn(stamp, port, merged, observer, ver["build"], ver["map_id"])
        if not conn.heroes:
            continue
        rows = ce.build_casts(conn, table, rechargeprobe.table_for(ver["build"], exe), None)
        if heals_of(conn, rows):          # an outpost carries the hero but no heal
            out.append((port, conn, rows))
    return out


def heals_of(conn, rows):
    party = set(conn.heroes)
    return [r for r in rows if r["caster"] in party and r["skill"] in HEALS
            and r.get("end_prop") == ce.PROP_FINISHED]


def party_of(conn):
    return sorted({conn.observer} | set(conn.party))


def health(conn, agent, i):
    """The agent's health fraction strictly before s2c message i (RECONSTRUCTION, exact on
    the observer between anchors), or None with no create on the connection."""
    if conn.health_ev.get(agent) is None:
        return None
    return conn.health_before(agent, i)[0]


def landing_heal(conn, r):
    """The targeted heal word of this cast on its target: (t, fraction) or None."""
    for (t, src, x) in conn.heals.get(r["target"], ()):
        if src == r["caster"] and r["t"] < t <= r["t"] + 3.0:
            return t, x
    return None


def score(conn, rows):
    heals = heals_of(conn, rows)
    party = party_of(conn)
    other = [r for r in heals if r["target"] != r["caster"]]
    unhurt, two_hurt, lowest = [], 0, 0
    for r in heals:
        hp = {a: health(conn, a, r["i"]) for a in party}
        t_h = hp.get(r["target"])
        if t_h is None or t_h >= HURT:
            unhurt.append((round(r["t"], 2), r["skill"], r["target"], t_h))
        hurt = {a: x for a, x in hp.items() if x is not None and 0.0 < x < HURT}
        if len(hurt) >= 2:
            two_hurt += 1
            lowest += t_h is not None and t_h <= min(hurt.values()) + 1e-3
    share = None if not two_hurt else lowest / two_hurt
    p1 = ("NULL" if len(other) < FLOOR_P1 else
          "HELD" if not unhurt and (share is None or share >= 0.8) else "FAILED")
    p1_text = (f"heals {len(heals)}, on another ally {len(other)} (floor {FLOOR_P1}); on an unhurt "
               f"ally {len(unhurt)}; the most-hurt chosen where >= 2 hurt {lowest} of {two_hurt}")

    orisons = []
    for r in heals:
        if r["skill"] != ORISON or r["target"] != conn.observer:
            continue
        deficit = 1.0 - (health(conn, conn.observer, r["i"]) or 0.0)
        land = landing_heal(conn, r)
        heal = land[1] if land else None
        orisons.append((round(r["t"], 2), round(deficit, 4), heal,
                        None if heal is None else deficit + 1e-3 >= heal))
    waited = [o for o in orisons if o[3]]
    p2 = "NULL" if not orisons else ("HELD" if len(waited) == len(orisons) else "FAILED")
    p2_text = (f"Orison on the observer n={len(orisons)}; cast with deficit >= its heal "
               f"{len(waited)} of {len(orisons)}; deficits "
               f"{[o[1] for o in orisons]} against heals {[round(o[2], 4) for o in orisons if o[2]]}")

    recast = []
    enchants = [r for r in heals if r.get("type_name") == "Enchant"]
    for r in enchants:
        live = [s for s, _age in ce.applies_live_before(conn, r["target"], r["i"])]
        if r["skill"] in live:
            recast.append((round(r["t"], 2), r["skill"], r["target"]))
    p3 = "NULL" if not enchants else ("HELD" if not recast else "FAILED")
    p3_text = f"enchantment casts {len(enchants)}; onto a target still carrying it {len(recast)}"

    dmg = sorted(t for a in party for (t, kind, v) in conn.health_ev.get(a, ())
                 if kind == "delta" and v < 0)
    end_t = conn.s2c[-1][0] if conn.s2c else 0.0
    windows = []
    for k, t in enumerate(dmg):
        nxt = dmg[k + 1] if k + 1 < len(dmg) else end_t
        if nxt - t >= CALM_S:
            windows.append((t, nxt))
    calm_rows, calm_bad = [], []
    for (a, b) in windows:
        inside = [r for r in heals if a < r["t"] < b]
        for r in inside:
            t_h = health(conn, r["target"], r["i"])
            alive = [h for h in (health(conn, x, r["i"]) for x in party) if h]
            full = bool(alive) and all(h >= HURT for h in alive)
            calm_rows.append((round(a, 2), round(b, 2), round(r["t"], 2), r["skill"], r["target"], t_h))
            if t_h is None or t_h >= HURT or full:
                calm_bad.append(calm_rows[-1])
    p4 = ("NULL" if not calm_rows else "HELD" if not calm_bad else "FAILED") + " (post hoc)"
    p4_text = (f"calm windows (>= {CALM_S:.0f} s without a party damage word) "
               f"{[(round(a, 1), round(b, 1)) for a, b in windows]}; heals inside {len(calm_rows)}; "
               f"on a full target or a full party {len(calm_bad)}")
    return [("H1.P1", p1, p1_text), ("H1.P2", p2, p2_text), ("H1.P3", p3, p3_text),
            ("H1.P4", p4, p4_text)], heals, party


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default=DEFAULT_CAPTURE)
    ap.add_argument("--rows", action="store_true")
    a = ap.parse_args(argv)
    capdir = os.path.join(livewire.captures_root(), a.capture)
    if not os.path.isdir(capdir):
        print(f"no capture {a.capture} under {livewire.captures_root()}")
        return 2
    found = connections(capdir, a.capture)
    if not found:
        print("no game connection with a party hero that heals -- nothing to score")
        return 1
    for port, conn, rows in found:
        verdicts, heals, party = score(conn, rows)
        print(f"\n:{port} map {conn.map_id} build {conn.build} observer {conn.observer} "
              f"heroes {sorted(conn.heroes)} party {party}")
        for pid, v, text in verdicts:
            print(f"  [{v}] {pid}: {text}")
        if a.rows:
            for r in heals:
                hp = {x: health(conn, x, r["i"]) for x in party}
                print(f"    {r['t']:8.2f} {r['skill']:5d} -> {r['target']}  health {hp}  "
                      f"({r.get('h_target_how')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
