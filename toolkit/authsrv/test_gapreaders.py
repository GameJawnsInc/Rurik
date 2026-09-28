"""The corpus readers outside livewire honour a capture's declared gap -- and nothing else.

    python toolkit/authsrv/test_gapreaders.py

WHY THIS EXISTS (2026-09-28, CASTAI-Z1, the cms lane). The first gapped live
connection, 20260928T103123 10.0.0.210:65009 (38 + 20 s2c bytes the sniffer never
saw), is refused by `tape.load_tape` BY DESIGN. `livewire` and `tape` grew the one
set-aside for it (`capgaps.py`, commit 1644c6a3), but three shared corpus readers
kept their own way past it:

  - `adrenjoin.bars / scan / by_connection` wrapped the load in `except Exception:
    continue`, and discarded `decode_all`'s receipt;
  - `deepwoundjoin.census / weakness_attributes / weakness_lifts / status_census`
    wrapped `sequence` in `except (BuffLogError, TapeError): continue`;
  - `cmsgstream` discarded `reassemble`'s hole list and `decode_stream_at`'s error
    (its own test, `test_cmsgnames.py` sections 0 and 0b, covers it).

Each dropped :65009 with nothing said, and would have dropped ANY refused connection
the same way. Now each sets aside ONLY an s2c direction its capture's manifest
declares gapped, prints it by name, appends it to a `set_aside` list the caller can
assert with `capgaps.audit`, and lets every other refusal raise.

WHAT CAN GO RED. Section 1 (bare, synthetic captures): a declared s2c gap is set
aside by name by all seven walks, a c2s-only declaration leaves the s2c read, and
an UNDECLARED gap raises out of every walk naming its connection. Section 2 (vault):
each walk's set-aside over the whole corpus is exactly `capgaps.KNOWN_GAPPED`, still
refused; KNOWN-BAD: with the manifest's declaration withheld, the walks raise on
:65009 rather than skipping it.
"""
import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import adrenjoin      # noqa: E402
import capgaps        # noqa: E402
import checks         # noqa: E402
import deepwoundjoin  # noqa: E402
import tape           # noqa: E402
import vaultpath      # noqa: E402
from codec import Codec  # noqa: E402

# MEASURED from the first green run, 2026-09-28: 4 (2 bare + 2 vault). A bare run is 2.
LEDGER = checks.Ledger("corpus readers honour the declared gap", floor=4)

GAPPED_STAMP = "20260928T103123"
GAPPED_CONN = "10.0.0.210:65009->98.95.137.136:80"


def _walks(set_aside):
    """The seven corpus walks changed, each called with the SAME set_aside list
    semantics: name -> thunk. `costs={}` keeps the adrenjoin walks off the content
    tables (the bar arithmetic is not what is under test)."""
    return {
        "adrenjoin.bars": lambda: adrenjoin.bars(set_aside=set_aside["adrenjoin.bars"]),
        "adrenjoin.scan": lambda: adrenjoin.scan(costs={}, set_aside=set_aside["adrenjoin.scan"]),
        "adrenjoin.by_connection": lambda: adrenjoin.by_connection(
            costs={}, set_aside=set_aside["adrenjoin.by_connection"]),
        "deepwoundjoin.census": lambda: deepwoundjoin.census(
            set_aside=set_aside["deepwoundjoin.census"]),
        "deepwoundjoin.status_census": lambda: deepwoundjoin.status_census(
            set_aside=set_aside["deepwoundjoin.status_census"]),
        "deepwoundjoin.weakness_attributes": lambda: deepwoundjoin.weakness_attributes(
            set_aside=set_aside["deepwoundjoin.weakness_attributes"]),
        "deepwoundjoin.weakness_lifts": lambda: deepwoundjoin.weakness_lifts(
            set_aside=set_aside["deepwoundjoin.weakness_lifts"]),
    }


WALKS = ("adrenjoin.bars", "adrenjoin.scan", "adrenjoin.by_connection",
         "deepwoundjoin.census", "deepwoundjoin.status_census",
         "deepwoundjoin.weakness_attributes", "deepwoundjoin.weakness_lifts")


def _run_all():
    """{walk: ("ok", set_aside list, result) | ("raised", "Type: message")}. Catches
    exactly the two refusals a walk may raise, so a crash of any other kind still
    crashes this test."""
    aside = {w: [] for w in WALKS}
    out = {}
    for name, thunk in _walks(aside).items():
        try:
            out[name] = ("ok", aside[name], thunk())
        except (tape.TapeError, adrenjoin.ScanRefused) as ex:
            out[name] = ("raised", f"{type(ex).__name__}: {ex}")
    return out


@contextlib.contextmanager
def _vault_at(root):
    """Point vaultpath at a synthetic vault for the duration, then restore it."""
    saved = vaultpath._resolved
    vaultpath._resolved = (root, "test_gapreaders synthetic vault")
    try:
        yield
    finally:
        vaultpath._resolved = saved


def _capture(live, stamp, conns, manifest):
    """A synthetic LIVE capture. `conns` is {port: (plain, [(seq, n), ...])}: the game
    channel file carries `plain` as s2c frames and wire.jsonl carries one s2c segment
    of n bytes at each seq (22 handshake bytes first; the ciphertext's content is not
    read by a tape, only its lengths)."""
    cap = os.path.join(live, stamp)
    os.makedirs(cap)
    with open(os.path.join(cap, "wire.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "origin", "origin": "live"}) + "\n")
        for port, (_plain, segs) in conns.items():
            for i, (seq, n) in enumerate(segs):
                fh.write(json.dumps({"kind": "wire", "dir": "s2c", "seq": seq,
                                     "t": 1.0 + i, "payload": "00" * n,
                                     "src": "198.51.100.1", "sport": 80,
                                     "dst": "192.0.2.1", "dport": port}) + "\n")
    for port, (plain, _segs) in conns.items():
        name = f"192.0.2.1:{port}->198.51.100.1:80"
        with open(os.path.join(cap, f"game-192.0.2.1_{port}-to-198.51.100.1_80.jsonl"),
                  "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": "origin", "origin": "live"}) + "\n")
            fh.write(json.dumps({"kind": "version", "channel": "game",
                                 "connection": name}) + "\n")
            fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                                 "plain": plain[:20].hex()}) + "\n")
            fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                                 "plain": plain[20:].hex()}) + "\n")
    with open(os.path.join(cap, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"report": {"connections": manifest}}, fh)
    return cap


def section_bare():
    print("1. the doors that need no vault (synthetic captures)")
    msg = Codec().encode("GAME_SMSG", 0x009F, [42, 7, 480])          # 14 bytes
    plain = msg * 3                                                   # 42 bytes
    whole = [(1000, 42), (1042, 22)]            # 22 handshake + 42 plain, no hole
    holed = [(1000, 42), (1046, 18)]            # a 4-byte hole at stream offset 42
    c = lambda p: f"192.0.2.1:{p}->198.51.100.1:80"                   # noqa: E731
    printed = io.StringIO()
    with tempfile.TemporaryDirectory() as td:
        live = os.path.join(td, "captures", "live")
        # port 5: s2c holed and DECLARED; port 6: whole s2c, only its c2s declared;
        # port 7: whole, nothing declared
        cap1 = _capture(live, "20990101T000001",
                        {5: (plain, holed), 6: (plain, whole), 7: (plain, whole)},
                        [{"connection": c(5), "gaps": {"s2c": [[42, 4]]}},
                         {"connection": c(6), "gaps": {"c2s": [[0, 5]]}},
                         {"connection": c(7), "gaps": {}}])
        with _vault_at(td), contextlib.redirect_stdout(printed):
            declared = _run_all()
            helpers = ({ch["connection"] for ch in adrenjoin._whole_s2c(cap1, None)},
                       {ch["connection"] for ch in deepwoundjoin.whole_s2c(cap1, None)})
        # port 8: s2c holed, NOT declared -- in a second capture, beside the first
        _capture(live, "20990101T000002", {8: (plain, holed)},
                 [{"connection": c(8), "gaps": {}}])
        with _vault_at(td), contextlib.redirect_stdout(io.StringIO()):
            undeclared = _run_all()
    want = [{"capture": "20990101T000001", "connection": c(5),
             "gaps": {"s2c": [[42, 4]]}}]
    good = {w: r[0] == "ok" and r[1] == want for w, r in declared.items()}
    skipped = declared["adrenjoin.scan"][2][2] if declared["adrenjoin.scan"][0] == "ok" else None
    read = sorted(r["connection"] for r in (skipped or ()))
    n_print = printed.getvalue().count(f"SET ASIDE 20990101T000001 {c(5)}")
    LEDGER.ok(all(good.values()) and read == [c(6), c(7)]
              and helpers == ({c(6), c(7)}, {c(6), c(7)}) and n_print >= len(WALKS),
              "all seven walks set aside ONLY the s2c gap their manifest declares, by "
              "name, and still read the connection whose c2s alone is declared",
              f"set-aside correct in {sum(good.values())}/{len(WALKS)} walks "
              f"({[w for w, g in good.items() if not g]} wrong); adrenjoin.scan read "
              f"{read}; helpers kept {sorted(helpers[0])}; {n_print} SET ASIDE lines")
    loud = {w: r[0] == "raised" and c(8) in r[1] for w, r in undeclared.items()}
    LEDGER.ok(all(loud.values()),
              "and an UNDECLARED gap raises out of every walk, naming its connection "
              "(the old `except ...: continue` dropped it without a word)",
              "; ".join(f"{w}: {undeclared[w][1] if undeclared[w][0] == 'raised' else 'NOT RAISED'}"
                        for w in WALKS)[:900])


def section_vault():
    print("2. the whole live corpus")
    live = vaultpath.require_dir("captures", "live", why="the gap readers' corpus audit")
    caps = [os.path.join(live, s) for s in sorted(os.listdir(live))
            if os.path.isdir(os.path.join(live, s))]
    got = _run_all()
    audits = {}
    for w, r in got.items():
        if r[0] != "ok":
            audits[w] = (False, r[1])
            continue
        audits[w] = capgaps.audit(r[1], caps, tape.refuses)
    bad = capgaps.audit(got["deepwoundjoin.census"][1], caps, lambda _c, _n: False) \
        if got["deepwoundjoin.census"][0] == "ok" else (True, "")
    LEDGER.ok(all(ok for ok, _w in audits.values()) and not bad[0]
              and all(len(r[1]) == len(capgaps.KNOWN_GAPPED) for r in got.values()
                      if r[0] == "ok"),
              "every walk's set-aside over the whole corpus is EXACTLY capgaps.KNOWN_GAPPED, "
              "each still refused by tape.load_tape (KNOWN-BAD: an audit told it loads "
              "goes red)",
              "; ".join(f"{w}: ok={ok}" for w, (ok, _why) in audits.items())
              + f" | {audits[WALKS[0]][1]}")
    # KNOWN-BAD on the real tape: withhold the manifest's declaration and the walks
    # must RAISE on :65009 -- the set-aside is the declaration, not a catch
    real = capgaps.declared_gaps
    capgaps.declared_gaps = lambda _capdir: {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            raised = {}
            for w in ("adrenjoin.bars", "deepwoundjoin.census"):
                try:
                    _walks({w2: [] for w2 in WALKS})[w]()
                    raised[w] = None
                except tape.TapeError as ex:
                    raised[w] = str(ex)
    finally:
        capgaps.declared_gaps = real
    LEDGER.ok(all(v and GAPPED_CONN in v for v in raised.values()),
              "KNOWN-BAD: with its declaration withheld, the gapped connection is LOUD "
              "(tape.TapeError naming it), not skipped",
              "; ".join(f"{w}: {(v or 'NOT RAISED')[:160]}" for w, v in raised.items()))


def main():
    section_bare()
    try:
        vaultpath.require_dir("captures", "live")
    except SystemExit as ex:
        LEDGER.skip("section 2 (the whole live corpus)", f"no vault: {ex}")
        return LEDGER.verdict()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
