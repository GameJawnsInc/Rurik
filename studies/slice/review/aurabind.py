#!/usr/bin/env python3
"""SLICE-F4: does `s_aura`'s second column bind as a CLIENT file id?

The claim under test: each `s_aura` row is (aura id, file id, tint/scale word).
The refutable half is the middle column -- if those 44 numbers are file ids, the
client can find every one of them in its own archive.

THE CONTROLS ARE THE WHOLE DESIGN, and without them this proves nothing. The
archive is dense in that numeric band: roughly half of ANY id drawn from it
binds. So "44 of 44 bind" is only evidence against a measured background, and
this script measures the background two ways -- the same ids + 1, and random
draws from the same range. If a control binds at the same rate the run says
DISCRIMINATES NOTHING rather than claiming a win.

    python studies/slice/review/aurabind.py
    python studies/slice/review/aurabind.py --dat <some Gw.dat>

Reads the pinned pristine client and a vault archive. Writes nothing.
"""
import argparse
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in (os.path.join(ROOT, "toolkit"),
          os.path.join(ROOT, "toolkit", "mapdata"),
          os.path.join(ROOT, "toolkit", "clientscan")):
    if p not in sys.path:
        sys.path.insert(0, p)

import archive as ar_mod  # noqa: E402
from consttable import PE, find_exe, table_for  # noqa: E402
from vaultpath import vault_path  # noqa: E402

DEFAULT_DAT = ("run", "2026-08-20_21511009c460", "Gw.dat")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", help="client to read; defaults to the pinned build")
    ap.add_argument("--dat", help="archive to bind against")
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args(argv)

    exe, why = ((a.exe, "given on the command line") if a.exe else find_exe())
    print(f"client: {exe}\n        ({why})")
    pe = PE(exe)
    t = table_for(pe, "s_aura")
    rows = [struct.unpack_from("<" + "I" * (t.stride // 4), t.record(pe, i))
            for i in range(t.count)]
    print(f"s_aura: {len(rows)} rows x {t.stride} B")

    third = {r[2] for r in rows}
    print(f"column 3 distinct values: {len(third)} -> "
          + ", ".join(f"0x{v:08X}" for v in sorted(third)))

    dat = a.dat or vault_path(*DEFAULT_DAT)
    if not os.path.exists(dat):
        # A fixture that resolves to nothing turns every assertion behind it
        # into a no-op; say so and exit non-zero rather than scoring zero rows.
        print(f"\nNO ARCHIVE at {dat} -- nothing was measured.")
        return 2
    ar = ar_mod.Archive(dat)
    print(f"archive: {dat}")

    test = [r[1] for r in rows]
    plus1 = [v + 1 for v in test]
    random.seed(a.seed)
    wild = [random.randrange(min(test), max(test) + 1) for _ in test]

    def rate(ids, label):
        hit = [i for i in ids if ar_mod.binds_plainly(ar, i) is not None]
        print(f"  {label:<30} {len(hit):>3} of {len(ids):>3} bind")
        return len(hit)

    print("\nbinds_plainly (what the CLIENT can address):")
    n_test = rate(test, "s_aura column 2")
    n_p1 = rate(plus1, "control: those ids + 1")
    n_rand = rate(wild, f"control: random in range (seed {a.seed})")

    print()
    if n_test == len(test) and n_p1 < len(test) and n_rand < len(test):
        print("VERDICT: column 2 binds as a client file id; neither control does.")
        rc = 0
    elif n_test == n_p1 == n_rand:
        print("VERDICT: DISCRIMINATES NOTHING -- every id in this band binds.")
        rc = 1
    else:
        print(f"VERDICT: partial -- test {n_test}, +1 {n_p1}, random {n_rand}.")
        rc = 1

    miss = [i for i in test if ar_mod.binds_plainly(ar, i) is None]
    if miss:
        print(f"unbound s_aura ids ({len(miss)}): {miss}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
