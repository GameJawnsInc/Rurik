r"""Movement speed on retail's wire, pinned: speedwords.py's six predictions over the corpus.

    python toolkit/authsrv/test_speedwords.py

Reads the vault (every live capture); skips, loudly, without one. The floors are
from the first green run (2026-09-16, 501 speed words over 17 captures) and are
FLOORS on exposure -- a corpus that gained captures may raise them, one that
lost its witnesses goes red here rather than letting `push_speed`'s numbers
drift away from what retail sent.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks           # noqa: E402
import speedwords       # noqa: E402
import vaultpath        # noqa: E402

LEDGER = checks.Ledger("speed words on retail's wire", floor=12)  # 2026-09-16, from the green run
check = checks.adopt(LEDGER)


def main():
    print("== 1. the census ==")
    try:
        vaultpath.require_dir("captures", "live", why="test_speedwords")
    except (Exception, SystemExit) as ex:     # require_dir raises SystemExit on a bare machine
        LEDGER.skip("the whole file", f"no live captures here ({ex})")
        return LEDGER.verdict()
    rows = speedwords.census()
    caps = len(set(r["capture"] for r in rows))
    check(len(rows) >= 501, f"{len(rows)} speed words (floor 501)")
    check(caps >= 17, f"over {caps} captures (floor 17)")
    check(all(r["val"] >= 0.0 for r in rows), "no negative speed word")

    print("\n== 2. the predictions ==")
    s = speedwords.score(rows)
    hit, miss, _ = s["P1 boost x1.33"]
    check(hit >= 80 and miss == 0,
          f"P1: a 33% boost applied with nothing open is x1.33 ({hit} / {miss}, floor 80 / 0)")
    hit, miss, _ = s["P2 crippled x0.5"]
    check(hit >= 2 and miss == 0,
          f"P2: Crippled applied with nothing open is x0.5 ({hit} / {miss}, floor 2 / 0)")
    hit, miss, _ = s["P3 crippled x boost = x0.665"]
    check(hit >= 1 and miss == 0,
          f"P3: Crippled over a boost is x0.665, MULTIPLICATIVE ({hit} / {miss}, floor 1 / 0)")
    n665, n083, _ = s["P3b additive 0.83 never seen"]
    check(n665 >= 21 and n083 == 0,
          f"P3b: {n665} rows read x0.665 and {n083} read the additive x0.83 (floor 21 / 0)")
    hit, miss, _ = s["P4 second boost = x1.34 cap"]
    check(hit >= 8 and miss == 0,
          f"P4: a second 33% boost over an open one is x1.34, the cap ({hit} / {miss}, floor 8 / 0)")
    hit, miss, _ = s["P5 cure batch has 2 words"]
    check(hit >= 1 and miss == 0,
          f"P5: the Charge! cure batch carries two speed words ({hit} / {miss}, floor 1 / 0)")
    n288, n300, _ = s["P6 bases"]
    check(n288 >= 300 and n300 >= 150,
          f"P6: bases are 288 ({n288} words) and 300 ({n300} words); floors 300 / 150")

    print("\n== 3. the controls ==")
    ratios = set(r["ratio"] for r in rows if r["ratio"] is not None)
    check(1.77 not in ratios and 1.66 not in ratios,
          "no uncapped double boost (x1.66 / x1.77) anywhere in the corpus")
    check(all(r["ratio"] in (1.33, 1.34) for r in rows
              if any(s in speedwords.BOOST_SKILLS for s in r["apply"])
              and r["ratio"] is not None
              and not (r["prev"] is not None and r["prev"] < r["base"])),
          "every 160/364 apply not over a snare reads x1.33 or x1.34 -- nothing else")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
