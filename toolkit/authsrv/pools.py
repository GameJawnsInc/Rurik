"""The two pools a skill spends: ENERGY, which the wire carries, and ADRENALINE,
which it does not.

R4b's other half. `effects.py` models what a skill PUTS ON somebody; this models
what it COSTS. Until 2026-08-20 the server modelled neither: every skill on the
default bar costs 5 energy or 4-5 adrenaline, the player's energy orb sat flat at
25 through eight presses including Flare, and nothing anywhere tracked a strike.

ENERGY HAS NO OPCODE OF ITS OWN. It rides the generic property channel, and the
whole model is three properties and one arithmetic quantum:

  * MAX energy  -- int property 41 on `0x009F`. OBSERVED 97 times across the
    live corpus, sent at agent create. `authsrv.py` already sends it
    (`agents.PROP_ENERGY_MAX`, `agents.PLAYER_ENERGY` = 25).
  * REGEN RATE  -- float property 43 on `0x00A2`, a FRACTION OF MAX per second,
    sent ONCE on change and never streamed. OBSERVED 52 times. The client
    animates the orb from it, exactly as it animates health from property 44
    (`studies/isle` B4, and `effects.py`'s degeneration section).
  * DISCRETE SPEND -- float property 62 on `0x00A2` (`agents.GV_ENERGY_SPENT`,
    defined since the GWCA import and with ZERO call sites in this server until
    now), value = -(energy_cost / max_energy), one per completed cast BY THE
    OBSERVING PLAYER'S OWN AGENT and by nobody else. See the 2x2 below.
  * DISCRETE GAIN  -- float property 52 (`agents.GV_ENERGY_GAIN`). OBSERVED
    once, at a resurrect, with the value exactly 1.0: a full refill.

AND THERE IS NO ABSOLUTE SETTER. Property 33 -- the obvious "current energy is
now N" -- appears **0 times in 13,378 property messages** across the whole live
corpus, and the positive control passes (the same scan finds 97 property-41s and
52 property-43s in the same messages). So the client INTEGRATES current energy
itself from max, rate and deltas, and a server that wants the orb to move must
send the deltas. Ours did not, which is why two harness runs on 2026-08-20 show
the bar flat at 25 through eight presses.

THE QUANTUM, and this is the finding this module exists to carry:

    rate = f32(0.33) * pips / max_energy

MEASURED 2026-08-20 against every distinct property-43 value in the corpus. It
reproduces ALL FIVE observed clusters BIT-EXACTLY -- 0.032999999821186066,
0.03959999978542328, 0.04400000348687172, 0.052800003439188004,
0.06000000238418579 -- while the NOMINAL rule every source states, one third of
a point of energy per second (p / (3*m)), reproduces ZERO of the five. So the
client's constant is a float literal 0.33f and not 1/3, and the difference is
1% of the regeneration rate, which is 40 seconds over a 20-minute run.

  * THE PRE-ROUNDING IS ITSELF EVIDENCE. `f32(0.33 * p / m)` computed from the
    DOUBLE 0.33 gets only 2 of 5; rounding 0.33 to f32 FIRST gets 5 of 5. That
    is what says the client holds a `float` constant rather than a `double`.
    (`f32(f32(f32(0.33)*p)/m)`, which rounds the intermediate product too,
    agrees on all five as well -- the corpus does not separate those two, and
    nothing here pretends it does.)

  * AND THE PIPS ARE INTEGERS, WHICH IS THE CHECK WITH NO FREE PARAMETER.
    Join each of the 52 property-43 events to that agent's OWN property-41 max
    (52 of 52 join; none is orphaned) and solve for pips:

        pips = rate * max / f32(0.33)

    Every one lands on an integer: 2.0 at max 20 (x30), 3.0 at max 25 (x4),
    4.0 at max 25 (x11), 4.0 at max 30 (x4), 4.0 at max 22 (x1), and 0.0 twice
    at death. Fifty-two of fifty-two, no residue. A wrong constant has no reason
    to produce integers at all, let alone the ones GWW's armour table predicts:
    WIKI (GWW, "Energy", rev. 2026-03-15) base 20 energy / 2 pips, Warrior
    +0/+0, Ranger +1 pip/+5 energy, Dervish and Assassin +2/+5, casters +2/+10.
    (2,20) is a warrior, (3,25) a ranger, (4,25) a dervish or assassin, (4,30) a
    caster.

  * THE DENOMINATOR IS THE CURRENT MAX, not the one the agent was created with.
    Agent 27 of capture `20260817T183756` ran at rate 0.0528 with max 25 -- four
    pips -- died, took the death penalty down to max 22, and had property 43
    re-sent as 0.06, which is the SAME FOUR PIPS over the new denominator. One
    witness, and it is the reason `set_maximum` recomputes rather than clamping.

WHO PAYS ON THE WIRE, AND FOR WHAT. Cross every skill activation in the corpus
(properties 48/50/60) against whether a property 62 rode the same batch, split
by whether that agent ever received a property 41. Two of the four cells are
EMPTY, which is what makes this a rule rather than a tendency:

                          spend    silent
    own agent, paid cast     45         0
    own agent, free cast      0        44
    any other agent         0 (of 722, 579 of them paid)

  * SCOPE. Property 62 is the observing player's OWN agent's and nobody else's.
    579 PAID casts by other agents -- a whole PvP arena's worth -- carry not one
    spend. So our server must not emit one for an enemy: "one property 62 per
    cast" is the rule this corpus refutes, and it is the rule a reader who only
    counted spends would have written.
  * ZERO-COST CASTS SEND NOTHING, 44 of 44. `spend` returns None for those
    rather than 0.0, so a caller cannot put a -0.0 on the wire -- a value that
    reads as a spend in every log we have and that retail never sends.

WHILE WE ARE HERE, AND UNEXPLAINED: property 41 arrives as the PAIR (1,
real_max) for all 48 own agents in the corpus -- 30 x (1,20), 13 x (1,25),
4 x (1,30) and one (1,25,22) where the death penalty landed. Our own spawn sends
a single property 41. What the leading 1 is for is NOT FOUND, nothing here reads
it, and it is written down because it is a difference between our stream and
retail's that a client run could be pointed at.

ADRENALINE IS NOT ON THE WIRE AT ALL, and that is a finding rather than a gap.
`schema/messages.json` has no adrenaline opcode; GWCA's `Opcodes.h` has none;
GWCA reads `adrenaline_a`/`adrenaline_b` out of client MEMORY, from the
`SkillbarSkill` struct. So either the client animates the icons itself from the
combat it can already see, or the charge state is invisible to it. **That is an
open question a client run answers, and it does not block this module**: the
server tracks the pools authoritatively and sends nothing for them, which is the
only reading that is right under either answer.

The rules are GWW's -- WIKI (GWW, "Adrenaline", rev. 2026-07-02):

  * 25 units (one strike) per successful weapon hit on an opponent.
  * 1 unit per 1% of maximum health lost to damage, FLOORED -- and zero damage
    grants nothing AND does not count as combat.
  * Every adrenal skill has its OWN pool and they all fill at once.
  * Using an adrenal skill zeroes its own pool and costs every OTHER pool one
    strike, whether or not the skill is interrupted or fails.
  * All adrenaline is lost on death, and after 25 seconds out of combat.

COSTS ARE RAW UNITS, NOT THE NUMBER ON THE ICON. The client's skill table holds
the raw unit total at +0x38 and the client DISPLAYS `ceil(units/25)`
(`clientscan/skilltable.py:180`). Battle Rage (317) is 80 raw units and shows 4;
Defy Pain (318) is 120 and shows 5; Rush (319) is 80; Sever Artery (382) is 100.
The distinction is load-bearing and GWW says so in Battle Rage's own Notes:
"exactly requires 80 units... 3 strikes and 5 units". Four strikes is 100 units
and would be wrong by a whole hit.

THE CONTENT STORE CARRIES BOTH COLUMNS since 2026-08-20:
`vault/content/skills.toml` has the DISPLAYED `adrenaline` (ceil, lossy -- 4
covers everything from 76 to 100) and the raw `adrenaline_units` (317 reads
80), regenerated with the extractor in the same change set that added this
module. Consumers read `adrenaline_units` and never reconstruct from the
displayed column: `displayed * 25` would demand 100 units for a skill that
needs 80, which is exactly the error this section is about
(`authsrv.skill_cost` refuses that reconstruction and says so per id).

Standard library only, and NOTHING from `authsrv.py`: like `effects.py` this is
a pure state machine plus arithmetic, so its tests need no socket and no client.

TWO THREADS. The PLAYER's pools are the one place `authsrv.py`'s single-writer
discipline does not hold: the gate reads-and-spends on the connection thread
while `energy_tick` regenerates on the world tick. So every mutating or
reading method below takes the pool's own RLock. The one cross-call invariant
that matters -- `can_pay` at the gate, `spend` a few lines later, NOT atomic
as a pair -- is safe anyway, because the world tick only ever ADDS energy:
nothing between the two calls can lower `current`, so a passed gate cannot
overdraw. (Enemy pools are touched by the world tick alone.)
"""

import math
import struct
import threading


def _locked(method):
    """Run `method` under the instance's `_lock` (see "TWO THREADS" above)."""
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    wrapped.__name__ = method.__name__
    wrapped.__doc__ = method.__doc__
    return wrapped

# ------------------------------------------------------------------ vocabulary
#
# The property ids. UPSTREAM as names -- GWCA, Py4GW and gw-preservation each
# carry a `GenericValueID` enum and 43/52/62 appear in all three -- but the
# BEHAVIOUR below is OBSERVED on our own captures and cited per line. 52 and 62
# are already declared in `agents.py` (`GV_ENERGY_GAIN`, `GV_ENERGY_SPENT`, at
# lines 1220 and 1250); they are restated here rather than imported so this
# module keeps `effects.py`'s property of importing nothing from the server, and
# `test_pools.py` checks the two copies still agree.
GV_ENERGY_REGEN = 43        # f32 fraction of max per second, on 0x00A2
GV_ENERGY_GAIN = 52         # f32 fraction of max, positive. OBSERVED once: 1.0
GV_ENERGY_SPENT = 62        # f32 fraction of max, negative, one per cast

# 0.33, and it is MEASURED rather than the 1/3 every source states. See the
# docstring: as an f32 constant it reproduces all five of retail's regeneration
# rates bit-exactly and 1/3 reproduces none of them. Kept as a plain literal so
# a reader sees the number the client holds; `wire_regen_rate` does the f32
# rounding, which is the part that matters.
PIP_ENERGY_PER_SECOND = 0.33

# WIKI (GWW, "Adrenaline", rev. 2026-07-02): one successful hit is one strike,
# and a strike is 25 units. This is also what makes the client's displayed cost
# `ceil(raw/25)` -- see `clientscan/skilltable.py:180`, which was derived from
# the same rule and cross-checked against the wiki's own cost column.
STRIKE_UNITS = 25

# WIKI, same page: "adrenaline is lost ... after 25 seconds of not being in
# combat". Combat means an attack landing or damage taken; see
# `AdrenalinePool.on_damage_taken` for the case where nothing counts.
ADRENALINE_TIMEOUT_S = 25.0


class PoolError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


def f32(value):
    """A Python float rounded to the float32 the wire actually carries.

    Every comparison against a capture goes through this. A predictor that
    compares in double precision agrees with retail to about seven digits and
    then disagrees on the bits, which is the difference between "our model is
    right" and "our model is close", and only the first is worth anything.
    """
    return struct.unpack("<f", struct.pack("<f", value))[0]


def wire_regen_rate(pips, max_energy):
    """The f32 property-43 value for `pips` pips over a pool of `max_energy`.

        f32( f32(0.33) * pips / max_energy )

    MEASURED: reproduces all five of the corpus's distinct nonzero rates
    bit-exactly, and the inverse (rate * max / 0.33) lands on an integer for 52
    of 52 property-43 events joined to their own agent's max. The nominal
    1/3 energy per second reproduces none of the five. Full evidence in the
    module docstring; `test_pools.py` section 1 re-runs both halves.

    NEGATIVE PIPS ARE PERMITTED -- energy DEGENERATION is a real mechanic and
    this is the channel it would ride, by symmetry with property 44's health
    degeneration. Nothing in our corpus witnesses one, so nothing here claims to
    know what the client does with it; it simply is not refused on our say-so.
    """
    if max_energy <= 0:
        raise PoolError(
            f"max_energy {max_energy!r} -- the rate is a FRACTION OF THE POOL "
            f"and a pool of zero has no fractions. Refusing rather than "
            f"dividing: an inf or a nan reinterpreted into the dword slot is a "
            f"value the client will happily animate towards.")
    return f32(f32(PIP_ENERGY_PER_SECOND) * pips / max_energy)


def spend_fraction(cost, max_energy):
    """The property-62 value for spending `cost` energy from a pool of that size.

    Negative, and a fraction of the pool rather than an absolute -- OBSERVED
    over all 45 property-62 events in the live corpus, which predict exactly
    from the client's own energy column with no exceptions: skill 364 at
    -0.25 with max 20 (cost 5), 780/814/858 at -0.2 with max 25 (cost 5),
    105/153 at -0.3333333 with max 30 (cost 10), and 394/783 at -0.4 with max
    25 (cost 10). Eight skills, three pool sizes, 45 of 45.

    Returned as a plain double; the sender rounds it to f32 on the way out, the
    same way `authsrv` already handles the duration slot on `0x0042`.
    """
    if max_energy <= 0:
        raise PoolError(f"max_energy {max_energy!r}: see wire_regen_rate")
    return -float(cost) / float(max_energy)


class EnergyPool:
    """One agent's energy: a maximum, a pip count, and a current value we integrate.

    THE SERVER INTEGRATES THE SAME NUMBER THE CLIENT DOES. `self.rate` is the
    f32 that goes on property 43, and `tick` integrates `rate * maximum` energy
    per second rather than `pips * 0.33` -- the two differ in the eighth digit,
    and using the wire value means the server's idea of the pool and the orb on
    screen cannot drift apart no matter how long the session runs. It also means
    the number to send is a field rather than something a caller recomputes.
    """

    def __init__(self, maximum, pips, now=0.0):
        if maximum <= 0:
            raise PoolError(f"an energy pool of {maximum!r} is not a pool")
        self.maximum = float(maximum)
        self.pips = pips
        self.rate = wire_regen_rate(pips, self.maximum)
        self.current = self.maximum          # OBSERVED: agents arrive full
        self._last = float(now)
        self._lock = threading.RLock()       # see "TWO THREADS", module top

    # -- the wire's own numbers ---------------------------------------------

    def energy_per_second(self):
        """Absolute energy per second, i.e. the fraction times the pool."""
        return self.rate * self.maximum

    @_locked
    def set_maximum(self, maximum):
        """Resize the pool and RECOMPUTE the rate, returning the new rate.

        The death penalty is the witnessed case: agent 27 of capture
        `20260817T183756` went from max 25 to max 22 and retail re-sent property
        43 as the same four pips over the NEW denominator (0.0528 -> 0.06). So
        the rate is not a property of the character, it is a property of the
        character AND the pool it is currently filling, and a server that
        resizes without re-sending leaves the orb filling at the old speed.
        """
        if maximum <= 0:
            raise PoolError(f"an energy pool of {maximum!r} is not a pool")
        self.maximum = float(maximum)
        self.rate = wire_regen_rate(self.pips, self.maximum)
        self.current = min(self.current, self.maximum)
        return self.rate

    # -- regeneration -------------------------------------------------------

    @_locked
    def tick(self, now):
        """Integrate regeneration up to `now`. Returns the energy actually gained.

        Clamped at the maximum, so the return value is what the pool took and
        not what the elapsed time was worth -- a full pool gains 0.0 however
        long the tick was. A clock that goes backwards contributes nothing
        rather than draining the pool.
        """
        dt = float(now) - self._last
        self._last = float(now)
        if dt <= 0:
            return 0.0
        before = self.current
        self.current = min(self.maximum, self.current + dt * self.energy_per_second())
        return self.current - before

    # -- spending -----------------------------------------------------------

    @_locked
    def can_pay(self, cost):
        """Whether a cast of this cost may start.

        The epsilon is for the integration above, not for the game: `current`
        is a float we accumulated a tick at a time, so a pool that is exactly
        full by construction can land a few ulps short of its own maximum and
        refuse a cast retail would allow.
        """
        return self.current + 1e-9 >= float(cost)

    @_locked
    def spend(self, cost):
        """Deduct `cost` and return the property-62 fraction -- or None.

        None for a ZERO-COST skill, and that is measured rather than tidy: 44 of
        44 zero-cost casts in the live corpus send no property 62 at all. A 0.0
        would be a message retail never sends, and -0.0 would be a message that
        reads as a spend in every log we have.

        RAISES on an unpayable cost rather than clamping or refusing quietly.
        The caller checks `can_pay` first and declines the cast there, where it
        can also tell the client why; a pool that silently paid what it could
        would let a cast complete for free and put the orb and the server's
        arithmetic permanently out of step -- which is the failure mode the
        whole "no absolute setter" finding says we cannot correct afterwards.
        """
        cost = float(cost)
        if cost < 0:
            raise PoolError(
                f"negative cost {cost!r} -- a skill that GIVES energy does it "
                f"through property 52, which is `gain`, not through a negative "
                f"spend. Nothing in the corpus carries a positive property 62.")
        if cost == 0:
            return None
        if not self.can_pay(cost):
            raise PoolError(
                f"cannot pay {cost} from {self.current:.3f}/{self.maximum:.0f}. "
                f"The caller checks can_pay() and declines the cast; this pool "
                f"does not part-pay.")
        self.current -= cost
        return spend_fraction(cost, self.maximum)

    @_locked
    def refill(self):
        """Fill the pool and return the property-52 gain for it: 1.0.

        OBSERVED n=1, and it is the resurrect batch of capture
        `20260817T183756`: the death bit clears, property 43 goes back to the
        agent's rate, property 52 arrives as exactly 1.0 and property 55 (the
        health half) as exactly 1.0 alongside it. A full pool is a gain of the
        whole pool, so 1.0 is the fraction and not a sentinel.
        """
        self.current = self.maximum
        return 1.0


class AdrenalinePool:
    """Every adrenal skill on one bar, each with its own units, all filling at once.

    `costs` maps skill id -> RAW UNITS (the client table's +0x38, not the number
    on the icon -- see the module docstring). Skills with no adrenaline cost are
    dropped at construction, so a bar of eight energy skills makes an inert pool
    rather than eight counters that never matter, and `{}` is legal.
    """

    def __init__(self, costs):
        self.costs = {int(sid): int(units) for sid, units in dict(costs).items()
                      if int(units) > 0}
        self.units = dict.fromkeys(self.costs, 0)
        self._last_combat = None
        self._lock = threading.RLock()       # see "TWO THREADS", module top

    # -- gaining ------------------------------------------------------------

    @_locked
    def _grant(self, amount, now):
        """Add `amount` units to every pool, capped, and mark combat. -> newly charged.

        THE CAP IS A RECONSTRUCTION and is labelled as one. GWW states the gain
        and the cost but never says what happens to the surplus; the reason to
        cap is Dragon Slash's Notes, which describe recharging adrenaline
        skills' pools in a way that only reads as a fill-to-full if a pool does
        not carry an overcharge. Capping is also the conservative direction: an
        uncapped pool would let a skill fire twice off one long fight, which is
        a mechanic no source describes.
        """
        self._last_combat = float(now)
        newly = []
        for sid, cost in self.costs.items():
            if self.units[sid] >= cost:
                continue
            self.units[sid] = min(cost, self.units[sid] + amount)
            if self.units[sid] >= cost:
                newly.append(sid)
        return sorted(newly)

    @_locked
    def on_hit_landed(self, now):
        """A successful weapon hit on an opponent: one strike into every pool.

        WIKI (GWW, "Adrenaline", rev. 2026-07-02). "Successful" is the caller's
        judgement -- a blocked or missed attack is not a hit -- and a multi-hit
        skill calls this once per hit, which is the wiki's own rule for them.
        """
        return self._grant(STRIKE_UNITS, now)

    @_locked
    def on_damage_taken(self, fraction_of_max_health, now):
        """Damage taken: one unit per 1% of maximum health, FLOORED.

        WIKI, same page. The floor is the whole rule: a hit for less than 1% of
        the pool grants nothing, and the wiki is explicit that zero damage "does
        not count as being in combat" either -- so a no-op here must NOT touch
        the timeout clock, or a stream of harmless pings would keep a bar
        charged forever. That is why this returns before `_grant`.

        The 1e-9 is arithmetic hygiene, not a game rule: 0.29 * 100 is
        28.999999999999996 in binary, and flooring that to 28 would lose a unit
        to the representation rather than to the mechanic.
        """
        gained = int(math.floor(float(fraction_of_max_health) * 100.0 + 1e-9))
        if gained <= 0:
            return []
        return self._grant(gained, now)

    # -- spending -----------------------------------------------------------

    @_locked
    def charged(self, skill_id):
        """Whether this skill's own pool has reached its RAW unit cost.

        Battle Rage is the case that makes the raw/displayed distinction matter:
        80 units, displayed as 4, and GWW's own Notes say it "exactly requires
        80 units of adrenaline (3 strikes and 5 units)". Comparing against the
        displayed 4 strikes would demand 100 and leave the skill dark through a
        fight it should have fired in.
        """
        sid = int(skill_id)
        return sid in self.costs and self.units[sid] >= self.costs[sid]

    @_locked
    def use(self, skill_id):
        """Spend it: own pool to zero, every OTHER pool down one strike.

        WIKI, same page, and the second half is the part that gets forgotten:
        the cross-cost applies "whether or not the skill is interrupted or
        fails", so this is called at the moment of USE and not on completion --
        the opposite of `EnergyPool.spend`, which the corpus shows firing once
        per COMPLETED cast.

        Refuses a skill that is not on this bar's adrenal list, loudly, because
        the alternative is a caller that wires every keypress here and quietly
        drains three pools every time the player casts a spell.
        """
        sid = int(skill_id)
        if sid not in self.costs:
            raise PoolError(
                f"skill {sid} has no adrenaline cost on this bar -- using a "
                f"non-adrenal skill costs the other pools NOTHING. Check "
                f"`skill_id in pool.costs` before calling.")
        self.units[sid] = 0
        for other in self.units:
            if other != sid:
                self.units[other] = max(0, self.units[other] - STRIKE_UNITS)

    # -- losing it ----------------------------------------------------------

    @_locked
    def clear(self):
        """Every pool to zero and the combat clock forgotten. Death does this.

        WIKI: "all adrenaline is lost upon death". Forgetting the clock as well
        is what stops `tick` reporting a timeout wipe for a bar that a death
        already emptied.
        """
        for sid in self.units:
            self.units[sid] = 0
        self._last_combat = None

    @_locked
    def tick(self, now):
        """True exactly once, when 25 s out of combat wipes a bar that had charge.

        WIKI: adrenaline decays to nothing after 25 seconds without an attack
        landing or damage taken. Returns True only when something was actually
        lost, so the caller can log a real event rather than a heartbeat; the
        clock is dropped either way, so a second tick returns False.
        """
        if self._last_combat is None:
            return False
        if float(now) - self._last_combat < ADRENALINE_TIMEOUT_S:
            return False
        had = any(self.units.values())
        self.clear()
        return had
