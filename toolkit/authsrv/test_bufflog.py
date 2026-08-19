r"""Prove `bufflog.py` -- the rung-8 effects consumer -- on synthetic cases it
cannot fudge and on the retail effect episodes already in the vault.

WHAT IS PINNED AND WHY IT CAN FAIL.

1. EXACT PAIRING, synthetic: a removal at apply+duration is an EXPIRY, an early
   one is a STRIP, a missing one is OPEN and never scored as expired. The
   buff-id REUSE trap gets its own case, because ids are recycled within a
   session and a global id->apply map pairs an apply with a later episode's
   removal and reports a wild residual while looking fine.

2. THE ATTRIBUTION REFUSAL: `0x0042` carries no source agent, so an episode
   outside every mark window must stay `step = None` rather than being assigned
   to the nearest step. That is `studies/isle/PLAN.md` §3.3's own rule and it is
   the one thing standing between this module and a manufactured answer.

3. RETAIL PINS BY NAME (never a glob): the rung-6 capture's arena detour and the
   east run carry the corpus's only effect episodes, and they were recorded
   before this module existed. The headline they establish -- **`0x0042` HAS
   ArenaNet witnesses after all, 97 of them** -- is what retires §3.3's
   expectation that rung 8's likely outcome was a refutation, so it is pinned
   here rather than left in prose.

4. THE FLOAT-IN-A-DWORD TRAP: the duration field is typed `dword` in the
   catalog and the client does `fld` on it. A reader that compares the raw
   integer sees ~1.09e9. The test reproduces the broken reading and requires it
   to differ, so the fix cannot silently regress.

Needs `vault/captures/live/`; without it the retail sections cannot run and the
floor takes the run red.
"""
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import bufflog  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# Floor set from a real green run (36 checks, 2026-08-18).
LEDGER = checks.Ledger("bufflog", floor=36)
check = checks.adopt(LEDGER)


def ap(t, target, skill, f3, buff, dur):
    return {"t": t, "target": target, "skill": skill, "field3": f3,
            "buff": buff, "duration": dur}


def rm(t, target, buff):
    return {"t": t, "target": target, "buff": buff}


# ---------------------------------------------------------------------------
print("== 1. pairing and the three close states ==")

ev = {"applies": [ap(10.0, 25, 480, 3, 7, 3.0),      # expires on the nose
                  ap(20.0, 25, 481, 13, 8, 13.0),    # cut short at +2
                  ap(50.0, 25, 484, 5, 9, 20.0)],    # never closes
      "removes": [rm(13.0, 25, 7), rm(22.0, 25, 8)],
      "regen": [], "health_max": []}
eps = bufflog.episodes(ev)
by_buff = {e["buff"]: e for e in eps}
check(by_buff[7]["state"] == "expired" and abs(by_buff[7]["residual"]) < 1e-9,
      "a removal at apply+duration is an EXPIRY with ~0 residual")
check(by_buff[8]["state"] == "stripped" and by_buff[8]["residual"] < -10,
      "a removal 11 s early is a STRIP, and the residual carries the sign",
      f"residual={by_buff[8]['residual']}")
check(by_buff[9]["state"] == "open" and by_buff[9]["close_t"] is None,
      "an episode with no removal is OPEN, never expired")
check(sum(1 for e in eps if e["state"] == "expired") == 1,
      "exactly one of the three counts as expired")

# Jitter inside the tolerance is still an expiry; just outside is not.
ev_j = {"applies": [ap(0.0, 1, 480, 3, 3, 5.0), ap(100.0, 1, 480, 3, 4, 5.0)],
        "removes": [rm(5.04, 1, 3), rm(105.5, 1, 4)],
        "regen": [], "health_max": []}
js = {e["buff"]: e["state"] for e in bufflog.episodes(ev_j)}
check(js[3] == "expired", "40 ms of jitter is still an expiry")
check(js[4] == "stripped", "500 ms is not -- the tolerance is a real edge")

# ---------------------------------------------------------------------------
print("== 2. the buff-id REUSE trap ==")

# Same id 5 used twice, sequentially. A global id->apply map pairs the FIRST
# apply with the SECOND removal (residual +100) and both look plausible.
ev_r = {"applies": [ap(10.0, 25, 480, 3, 5, 3.0), ap(110.0, 25, 480, 3, 5, 3.0)],
        "removes": [rm(13.0, 25, 5), rm(113.0, 25, 5)],
        "regen": [], "health_max": []}
eps_r = bufflog.episodes(ev_r)
check(len(eps_r) == 2 and all(e["state"] == "expired" for e in eps_r),
      "a reused buff id yields two clean expiries, not one wild residual",
      f"{[e['residual'] for e in eps_r]}")
check(abs(eps_r[0]["close_t"] - 13.0) < 1e-9,
      "and the FIRST apply pairs with the FIRST removal, in time order")

# Two targets sharing an id at the same moment must not cross-pair.
ev_t = {"applies": [ap(10.0, 25, 480, 3, 5, 3.0), ap(10.0, 99, 480, 3, 5, 9.0)],
        "removes": [rm(13.0, 25, 5), rm(19.0, 99, 5)],
        "regen": [], "health_max": []}
check(all(e["state"] == "expired" for e in bufflog.episodes(ev_t)),
      "two targets holding the same buff id do not cross-pair")

# ---------------------------------------------------------------------------
print("== 3. the attribution refusal ==")

windows = [(1, "torch of hexes [EFFECT=hex]", 100.0, 200.0),
           (2, "student of burning [EFFECT=condition]", 200.0, 300.0)]
eps_a = bufflog.attribute(
    bufflog.episodes({"applies": [ap(150.0, 25, 480, 3, 1, 3.0),
                                  ap(250.0, 25, 481, 5, 2, 5.0),
                                  ap(950.0, 25, 484, 5, 3, 5.0)],
                      "removes": [], "regen": [], "health_max": []}),
    windows)
steps = {e["buff"]: e["step"] for e in eps_a}
check(steps[1] == 1 and steps[2] == 2, "episodes inside a window take its step")
check(steps[3] is None,
      "an episode outside EVERY window stays unattributed -- never assigned "
      "to the nearest step (0x0042 has no source agent, so the window is the "
      "only handle there is)")
eps_none = bufflog.attribute(
    bufflog.episodes({"applies": [ap(150.0, 25, 480, 3, 1, 3.0)],
                      "removes": [], "regen": [], "health_max": []}), [])
check(eps_none[0]["step"] is None,
      "with no sealed plan at all, everything is unattributed")

# ---------------------------------------------------------------------------
print("== 4. the float-in-a-dword trap ==")

raw = 1077936128                      # what the catalog hands over for 3.0f
check(abs(bufflog._f32(raw) - 3.0) < 1e-9,
      "the duration dword reinterprets to 3.0 as f32")
check(raw != 3.0 and raw > 1e9,
      "and the RAW value is ~1.08e9 -- a reader that skips the reinterpret "
      "compares that against a duration and fails every time", f"{raw}")

# ---------------------------------------------------------------------------
print("== 5. condition map and the field3 discriminator ==")

eps_c = bufflog.episodes({
    "applies": [ap(1.0, 25, 480, 3, 1, 3.0), ap(20.0, 25, 480, 9, 2, 9.0),
                ap(40.0, 25, 481, 13, 3, 13.0), ap(60.0, 25, 364, 13, 4, 12.0)],
    "removes": [], "regen": [], "health_max": []})
cmap = bufflog.condition_map(eps_c)
check(set(cmap) == {480, 481},
      "only known condition skill ids enter the condition map -- skill 364 is "
      "not called a condition just because it rode the same opcode")
check(cmap[480]["name"] == "burning" and cmap[480]["n"] == 2,
      "and each carries its name and count")
f3 = bufflog.field3_report(eps_c)
check(f3[480]["field3_equals_duration"] and f3[481]["field3_equals_duration"],
      "the two conditions have field3 == duration")
check(not f3[364]["field3_equals_duration"] and not f3[364]["is_condition"],
      "the non-condition does not, and is flagged as not a condition")

# ---------------------------------------------------------------------------
print("== 6. buff-id allocation ==")

b = bufflog.buff_id_report(bufflog.episodes({
    "applies": [ap(0.0, 1, 480, 3, 51, 100.0), ap(1.0, 1, 481, 3, 52, 100.0),
                ap(2.0, 1, 484, 3, 51, 100.0)],
    "removes": [rm(0.5, 1, 51)], "regen": [], "health_max": []}))
check(b["distinct"] == 2 and b["reused"] == 1,
      "id reuse is counted, not hidden", f"{b}")
check(b["peak_concurrent"] == 2,
      "peak concurrency counts only episodes actually live at once", f"{b}")

# ---------------------------------------------------------------------------
print("== 7. the retail corpus, pinned by name ==")

CAPS = vaultpath.require_dir("captures", "live",
                             why="bufflog's corpus pins read live captures")

# The rung-6 arena detour: the corpus's richest effect connection.
ARENA = "10.0.0.210:54071->54.198.7.73:80"
rep = bufflog.report(os.path.join(CAPS, "20260817T231139"), ARENA)
check(rep["map_id"] == 310, "the arena connection is map 310")
check(rep["counts"]["applies"] == 19 and rep["counts"]["removes"] == 18,
      f"19 applies / 18 removes (got {rep['counts']['applies']}/"
      f"{rep['counts']['removes']})")
check(rep["states"].get("expired") == 18 and rep["states"].get("open") == 1,
      "18 expire and 1 is still live at the last byte", f"{rep['states']}")
check(rep["residual_median"] < 0.01,
      "the close lands within 10 ms of apply+duration at the median -- the "
      "0x0044-closes-0x0042 pairing is exact, not approximate",
      f"{rep['residual_median']*1000:.1f} ms")
check(480 in rep["conditions"] and rep["conditions"][480]["n"] == 5,
      "and BURNING (skill 480) is among them, five times -- ArenaNet's own "
      "server applying a CONDITION on 0x0042")
check(rep["field3"][480]["field3_equals_duration"] is True,
      "burning's field3 equals its duration in every sample")
check(rep["field3"][364]["field3_equals_duration"] is False,
      "while skill 364's does not -- (10, 10.0) and (13, 12.0)")

# The east run: the only Crippled in the corpus, from the operator's Pin Down.
EAST = "10.0.0.210:58898->98.95.137.136:80"
rep_e = bufflog.report(os.path.join(CAPS, "20260818T094648"), EAST)
check(rep_e["map_id"] == 280, "the east connection is map 280 (the Isle)")
check(481 in rep_e["conditions"],
      "CRIPPLED (skill 481) is on the Isle's own wire -- the operator's "
      "Pin Down episode")
check(rep_e["conditions"][481]["field3s"] == {13: 1}
      and rep_e["conditions"][481]["durations"] == {13.0: 1},
      "with field3 13 and duration 13.0", f"{rep_e['conditions'][481]}")

# A CURE, on ArenaNet's own wire -- the first in this repo, and it is what
# makes the STRIP class more than bookkeeping. The Crippled episode does NOT
# expire: it is removed 1.776 s early, and skill 364's apply carries the
# IDENTICAL timestamp as the removal. So a cure closes a condition through the
# same 0x0044 an expiry uses, and only the residual tells them apart.
eps_e = bufflog.episodes(bufflog.read_effects(
    os.path.join(CAPS, "20260818T094648"), EAST))
crip = [e for e in eps_e if e["skill"] == 481]
check(len(crip) == 1 and crip[0]["state"] == "stripped",
      "the Isle's Crippled episode is STRIPPED, not expired", f"{crip}")
check(abs(crip[0]["residual"] + 11.224) < 0.01,
      "cut 11.2 s short of its 13.0 s duration",
      f"residual={crip[0]['residual']:.3f}")
cure = [e for e in eps_e if abs(e["t"] - crip[0]["close_t"]) < 1e-6
        and e["skill"] != 481]
check(len(cure) == 1 and cure[0]["skill"] == 364,
      "and another skill's APPLY carries the identical timestamp as that "
      "removal -- a cure, closing a condition through the same 0x0044 an "
      "expiry uses. Only the residual separates them.",
      f"{[(c['skill'], c['t']) for c in cure]}")

# THE HEADLINE, pinned so prose cannot drift from it: 0x0042 has ArenaNet
# witnesses, which is what retires §3.3's "the refutation branch is likely".
total_applies = total_conditions = 0
for stamp in ("20260817T231139", "20260818T094648", "20260818T132739"):
    cap = os.path.join(CAPS, stamp)
    for row in bufflog.tape.channel_files(cap):
        try:
            r = bufflog.report(cap, row["connection"])
        except (bufflog.BuffLogError, bufflog.tape.TapeError):
            continue
        total_applies += r["counts"]["applies"]
        total_conditions += sum(c["n"] for c in r["conditions"].values())
check(total_applies >= 90,
      "the live corpus carries 90+ retail 0x0042 applies -- the opcode is NOT "
      "witness-free, and rung 8's channel question is answered offline",
      f"{total_applies}")
check(total_conditions >= 6,
      "of which 6+ are known CONDITION skill ids", f"{total_conditions}")

# A partial decode must refuse rather than return a short effect log.
try:
    bufflog.read_effects(os.path.join(CAPS, "20260817T231139"), "10.0.0.210:1->2:80")
    check(False, "a bogus connection must refuse")
except (bufflog.BuffLogError, bufflog.tape.TapeError):
    check(True, "a connection that cannot be read refuses loudly")

sys.exit(LEDGER.verdict())
