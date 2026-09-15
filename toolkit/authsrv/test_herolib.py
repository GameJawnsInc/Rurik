"""herolib: a hero's usable library, and the referee on one bar slot.

WHAT THIS IS REALLY CHECKING. The union rule has a plausible WRONG answer --
that a hero draws on the character's learned skills, since the hero belongs to
the character -- and the corpus says otherwise. So the fixture below is built
from the two captures that separate them, with the account id and the
character-only id chosen so that getting the rule backwards reddens rather
than passing quietly:

  * 20260914T005758: Koss's bar carries 346; 346 is in the ACCOUNT's 0x001D
    set and in NEITHER his own 0x0073 list nor the character's 0x00DB set.
  * 20260817T231139: the PLAYER's bar carries 364 and 384, both in the
    character's 0x00DB set and in NO account set.

A rule that used the character set would admit 364 to a hero's bar, and a rule
that used only the hero's own skills would refuse 346. Both are checked.

No vault, no client, no server: herolib is pure.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks  # noqa: E402
import herolib  # noqa: E402

led = checks.Ledger("herolib", floor=24)

# The capture's own numbers.
KOSS_OWN = [322, 382, 348, 1, 385, 2]
KOSS_BAR = [322, 382, 348, 1, 385, 346, 0, 2]
ACCOUNT = [1, 2, 322, 346, 348, 382, 385]       # holds 346, not 364/384
CHARACTER_ONLY = [364, 384]                     # the plausible wrong source

lib = herolib.hero_library(KOSS_OWN, ACCOUNT)

led.ok(346 in lib,
       "346 IS in the hero's library -- it is an ACCOUNT unlock, and a rule "
       "built from the hero's own skills alone would refuse the very id "
       "retail put on Koss's bar")
led.ok(all(s in lib for s in KOSS_OWN),
       "every one of the hero's own skills is in its library")
led.ok(364 not in lib and 384 not in lib,
       "the CHARACTER's learned-only ids are NOT in a hero's library -- the "
       "plausible wrong answer, and the check that reddens if the union is "
       "built from the character's set instead of the account's")
led.ok(set(KOSS_BAR) - {0} <= lib,
       "every occupied slot of retail's own Koss bar is inside the library "
       "this rule computes -- the whole point, on the capture's numbers")

led.ok(herolib.hero_library(None, ACCOUNT) == set(ACCOUNT),
       "a hero with no authored skills of its own has the account's library")
led.ok(herolib.hero_library(KOSS_OWN, None) == set(KOSS_OWN),
       "and with no account library it has only its own -- None means "
       "'nothing known', never 'everything'")
led.ok(herolib.hero_library(None, None) == set(),
       "both absent is the EMPTY library, not a permissive one")

# -- the slot referee -------------------------------------------------------
led.ok(herolib.refuse_bar_slot(0, 346, lib) is None,
       "an account-unlocked skill may be equipped into slot 0")
led.ok(herolib.refuse_bar_slot(7, 322, lib) is None,
       "slot 7 is the last legal slot")
why = herolib.refuse_bar_slot(8, 322, lib)
led.ok(why is not None and "hotKey" in why,
       "slot 8 is refused and the reason names the client's own guard")
led.ok(herolib.refuse_bar_slot(-1, 322, lib) is not None,
       "a negative slot is refused")
why = herolib.refuse_bar_slot(0, 364, lib)
led.ok(why is not None and "library" in why,
       "a skill outside the library is refused, and the reason says so")
led.ok("GmSkSlot" in (why or ""),
       "...and it cites the equip validator that would assert on the client, "
       "so the log says WHY it matters rather than only that it was refused")
led.ok(herolib.refuse_bar_slot(3, 0, lib) is None,
       "clearing a slot with 0 is always legal -- that is how retail spells "
       "an empty slot, and Koss's own bar has one at index 6")
led.ok(herolib.refuse_bar_slot(3, -5, lib) is not None,
       "a negative skill id is refused")
led.ok(herolib.refuse_bar_slot(0, 99999, None) is None,
       "with NO library known, membership is not enforced -- a caller that "
       "cannot say what is unlocked must not refuse everything")

# -- applying a slot --------------------------------------------------------
bar = list(KOSS_BAR)
after = herolib.apply_bar_slot(bar, 6, 400)
led.ok(after[6] == 400 and bar[6] == 0,
       "apply_bar_slot returns a NEW bar and does not mutate the caller's -- "
       "an in-place write made the before/after log print the same value twice")
led.ok(len(herolib.apply_bar_slot([], 0, 1)) == herolib.BAR_SLOTS,
       "a short bar is padded to eight slots")
led.ok(herolib.apply_bar_slot([1, 2, 3], 7, 9)[7] == 9,
       "the last slot of a short bar is writable after padding")
led.ok(len(herolib.apply_bar_slot(list(range(1, 20)), 0, 5))
       == herolib.BAR_SLOTS,
       "an over-long bar is truncated to eight, never sent wide")

# -- the duplicate report ---------------------------------------------------
led.ok(herolib.duplicate_of(KOSS_BAR, 6, 322) == 0,
       "a skill already in another slot is reported with that slot's index")
led.ok(herolib.duplicate_of(KOSS_BAR, 0, 322) is None,
       "a skill in the slot being written is not its own duplicate")
led.ok(herolib.duplicate_of(KOSS_BAR, 6, 400) is None,
       "a skill on no other slot has no duplicate")
led.ok(herolib.duplicate_of(KOSS_BAR, 1, 0) is None,
       "clearing a slot never reports a duplicate, though the bar holds "
       "another 0 at index 6 -- empties are not skills")

sys.exit(led.verdict())
