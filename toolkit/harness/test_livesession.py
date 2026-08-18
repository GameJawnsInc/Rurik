"""Prove the live driver's offline half and its guards, without a live account.

The driver's RUN half (launch at the real service, sniff, read the key) needs WinDivert,
an elevated shell, and the secondary account, and never runs except behind --confirm. Its
ASSEMBLE half -- reassembled wire streams + the tapped key -> a decrypted, replayable,
LIVE-stamped capture -- is pure, and is where a wrong decrypt would live, so it is grounded
here against REAL captured bytes:

  1. split_c2s / split_s2c parse the plaintext handshake off the front and REFUSE a stream
     that is not the handshake, rather than feeding 82 bytes of something else to ARC4;
  2. on a real loopback session's own c2s ciphertext, split + decrypt reproduce the
     plaintext the server logged -- the same bytes replay.py verifies, reached the wire way;
  3. a full assemble() round-trips both directions to a LIVE capture whose self-consistency
     check (re-encrypt == captured ciphertext) holds, carrying A / server_seed / arc4_key
     under the field names the scrub already treats as secret;
  3b. assemble_live handles the shape a REAL session has and the dry-run never did -- three
     connections (auth, game, and one joined mid-stream) and a keyring of two keys, one per
     DH-keyed channel, because the single tap slot is overwritten at every handshake. It
     must pair each connection with the right key, report the headless one rather than
     crash on it, and -- the one that matters most -- decrypt NOTHING and write NO FILE
     when the right key is absent. ARC4 is symmetric, so "it decrypted" is never evidence;
     the client's own first opcode is;
  4. the guards refuse: the primary account, a non-stock (loopback) launch client, a
     live run with no --confirm, and -- since 2026-08-11 -- one with no --mode.
     Reforged Mode changes enemy health and armour ~20% and leaves no mark on the
     recorded stream, so an unstamped capture's stats can never be graded; the
     refusal has to land before the client launches because it cannot be asked
     afterwards. Its CONTROL is that a VALID mode gets past the gate and fails
     later, which is what separates a check from a wall.
  5. (2026-08-13) THE PRE-REGISTRATION SEAL, and the whole of it is a claim about WHEN.
     READ THE SECOND HALF OF THIS ENTRY FIRST if you are here to change §5: the version
     of it that shipped at 09:00 had 75 green checks and SIX sabotages walked through
     them, found by two independent adversarial reviews on the same day.
     `--plan` names the operator-mark plan `marks.py` reads in a second shell, and
     FINDINGS §10.5.1 asks for its sha256 in `manifest.json`. The manifest is written at
     the END of the run, after assembly, so a hash taken THERE would certify whatever the
     plan said afterwards -- a signature on the answer sheet rather than a
     pre-registration. So §5a asks the SYNTAX TREE whether the seal precedes
     `subprocess.Popen([exe] + args)`, because "before the launch" and "after it" are
     invisible to a grep and the ordering IS the feature; the two sabotages that move it
     are BUILT AND RUN here and must redden DIFFERENT checks. §5a also carries the
     vacuity guard the ordering claim needs: the manifest write must be AFTER the launch,
     or "the seal is before the launch" would prove nothing about the manifest.
     §5b drives the actual scenario -- seal, edit the file, render the manifest -- and
     requires the ORIGINAL hash, with the control that the edit really moved it. §5c is
     the refusals, each with a positive control, because a guard that refuses everything
     means the driver never runs and the session is lost to a typo. §5d is the
     asymmetry: a run with no plan WARNS and records the absence explicitly, a run with
     one does NOT warn -- `test_harness.py` earned that pair on `--enemy`, where a
     warning firing either way is noise. §5e is the second witness, which is free:
     `marks.py` hashes the same file in a different process at a later moment, so two
     seals of one file is something the artifact can refute. §5f is where that verdict
     LANDS -- an artifact field rather than console scrollback -- plus the narrowness of
     the one function in this project that edits a live run's manifest. §5g is the
     ordering again, OBSERVED: `subprocess.Popen` patched to log and raise, `run()` driven
     for real, and the recorded order compared against three sabotaged modules.

WHICH OF §5's CHECKS ARE LOAD-BEARING WAS MEASURED, not argued. Ten sabotages were built
as one-line edits to `livesession.py`, backed up and restored, the restore verified by
sha256, and RUN on 2026-08-13 against the first green baseline of 75; all ten reddened:

  * the manifest re-hashing the plan instead of using the carried seal   -- 3 red
  * the unsealed branch OMITTING its keys rather than writing them       -- 2 red
  * the warning fired on BOTH branches                                   -- 1 red
  * `seal_plan` hashing without PARSING (so empty/malformed get through) -- 2 red
  * a missing marker folded into AGREE instead of UNCHECKED              -- 1 red
  * `plan_manifest(None)` at the manifest site, ignoring the seal        -- 1 red
  * no seal call in `run()` at all                                       -- 4 red
  * `recorded_seal` dropping its `plan_seal.json` fallback               -- 1 red

AND THEN SIX MORE WERE BUILT THAT DID NOT. Two adversarial reviews the same afternoon put
these through the identical 75-check file and every one printed ALL CHECKS PASSED, exit 0:

  * `"plan_sha256": sha256(seal.path)` appended to run()'s manifest literal -- the exact
    defect this feature exists to prevent, using livesession's OWN file hasher, which is
    already called three times in that same dict. §5a matched callees NAMED `seal_plan`
    and `plan_sha256`; `sha256` is neither, and cannot be added to a denylist for the
    reason just given. Both reviews found this one independently.
  * the same with `steps` re-derived too, which additionally made `compare_plan_seals`
    print "two independent seals ... agree ... one before the client launched" about a
    plan that had been rewritten mid-session -- while `plan_seal.json`, in the same
    directory, held the original hash and contradicted it with nothing reading it.
  * `client = subprocess.Popen([exe])` inserted one line ABOVE the seal. `seal_order`
    kept the LAST-walked launch and `ast.walk` is breadth-first, so the shallow early
    spawn was overwritten by the real one nested inside `try:`.
  * the seal moved into a nested `def` and called after the launch: textually early,
    executed late, and INVISIBLE to a syntax tree by construction. §5a went fully green;
    the only red was §5c's refusal-placement check, and only because `seal_plan` happens
    to carry the refusals as well as the hash.
  * deleting `write_seal_file(outdir, seal)` -- its ONLY call site. §5b calls the function
    directly and §5e's `died` fixture builds `plan_seal.json` by hand, so neither noticed.
  * deleting `compare_plan_seals`'s only call site, which was in `reassemble()` -- i.e.
    the second witness was never spent on the live path at all, and its verdict was a
    `print` that reached no artifact.

ALL SIX REDDEN NOW, and so do nine more built the same way. MEASURED 2026-08-13 by
injecting each sabotaged module under THIS file (pre-binding `sys.modules["livesession"]`,
so both `import livesession as ls` and `open(ls.__file__)` read the saboteur) against a
green baseline of 106; every one exits 1 and every one reaches its verdict banner:

  a relaunch spawned above the seal                                12 red
  the seal deferred into a nested def, executed after the launch    8 red
  `if plan` truthiness instead of `if plan is not None`             6 red
  `write_seal_file`'s only call site deleted                        3 red
  `plan_manifest`'s branch-specific keys, back to asymmetric        2 red
  `seal_plan` catching only `marks.MarksError` again                2 red
  the manifest-time `compare_plan_seals` removed                    2 red
  `"plan_sha256": sha256(seal.path)` in the manifest literal        2 red
  the same plus `plan_steps` re-derived                             2 red
  `write_seal_file` no longer archiving `plan_body`                 1 red
  `internal_seal_conflict` never firing                             1 red
  `reassemble()` printing the verdict without writing it back       1 red
  the DISAGREE message asserting one cause again                    1 red
  `seal_plan` back to two independent reads                         1 red
  `update_manifest` willing to CREATE a manifest                    1 red

Three of those first runs went red with a TRACEBACK rather than a verdict, and fixing that
is why `refusal()` exists: a bare `except ls.LiveError` around a call that escapes as
`UnicodeDecodeError` or `OSError` kills the process before `LEDGER.verdict()`, so a test
that caught a real defect printed a stack trace and no ledger, no floor and no banner --
`test_content.py`'s failure, one file over. The escaping exception IS the finding in two of
these sabotages, so it has to arrive as a red check that names it.

THE COMMON SHAPE, and it is the lesson rather than the list: every check in the 75 either
compared two LINE NUMBERS or called a function in ISOLATION. Nothing read a manifest that
`run()` produced, nothing observed `run()` running, and nothing compared the two seal
records the driver itself writes. So the repairs are three, and they are what §5f, §5g and
`internal_seal_conflict` are: assert on the ARGUMENT (`seal.path`, the one thing
re-deriving a seal cannot do without) rather than on the callee's name; OBSERVE the order
instead of reading it; and make the artifact carry the contradiction so somebody can find
it later. Six sabotages, four of them one-liners, is what it took to learn that a
syntax-tree check is a claim about a source file and not about a program.

standard library only.
"""
import ast
import glob
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import checks  # noqa: E402
import marks  # noqa: E402
import origin  # noqa: E402
import livesession as ls  # noqa: E402
import wirecapture as wc  # noqa: E402
from gwcrypto import ARC4, arc4_hash  # noqa: E402

# Bound once, by NAME rather than by `ls.LiveError` at each call site, so `refusal()` reads
# the same class the module under test raises even when a sabotage is injected in its place.
LiveErrorType = ls.LiveError

# 106 is the MEASURED count of a full green run on a vaulted machine (42 before the plan
# seal landed, 33 added by §5a-5e, and 31 more on 2026-08-13 when two adversarial reviews
# put SIX green sabotages through the 75-check version -- see the header). Sections 2/3
# and the stock gate declare skips without a vault, so a vault-less run goes red -- the
# same choice this file has made since the floor was 42, and the reason is that its
# headline claims are about REAL captured bytes.
# FLOOR: 112, MEASURED from a green run 2026-08-17 after section 12 (the
# launch-build guard) landed -- read off the run, never computed.
LEDGER = checks.Ledger("livesession", floor=120)


# --------------------------------------------------- the syntax-tree readout --
def seal_order(src):
    """Where the seal, every spawn and the manifest sit in `run()`, STRUCTURALLY.

    Nothing here matches text. Calls are found by callee name, so a mention in a comment
    or a docstring is not one.

    THREE THINGS IN THIS READER ARE REPAIRS, and each was a green sabotage on 2026-08-13.

    1. THE LAUNCH IS THE EARLIEST ONE, not the last walked. The first version did
       `launch = n.lineno` on every `ast.Assign` binding `client` to a `.Popen`, keeping
       whichever `ast.walk` reached last -- and `ast.walk` is breadth-first, so a SHALLOW
       relaunch inserted above the seal was walked before the real one nested inside
       `try:` and was then overwritten. A sabotage adding `client = subprocess.Popen([exe])`
       one line ABOVE the seal passed all 75 checks. It is `min()` now.
    2. A LAUNCH IS A `Popen` WHOSE ARGUMENT NAMES `exe`, not one assigned to `client`.
       The old shape test was on the assignment TARGET, so `procs.append(Popen([exe]))` or
       any relaunch bound to another name was not a launch at all as far as it was
       concerned. `spawns` is every `.Popen` in `run()` regardless, because the strongest
       ordering claim available here is against the FIRST of those.
    3. `rereads` IS THE ARGUMENT TEST, and it is the one that matters most. The old reader
       collected callees named `seal_plan` and `plan_sha256` and nothing else, while
       `livesession.py` carries its own file hasher called `sha256` and calls it three
       times AFTER the launch in the same manifest literal. Appending
       `"plan_sha256": sha256(seal.path)` to that literal -- the exact defect the feature
       exists to prevent -- passed 75 of 75, twice, found independently by both reviews.
       Matching callee names cannot close that: the set of ways to spell "read a file" is
       open. What is NOT open is what re-deriving the seal NEEDS, which is the plan's PATH.
       So this collects every post-launch reference to `seal.path` or to the `plan`
       parameter, at any depth and in any expression -- which catches an alias assignment
       (`_p = seal.path`) as readily as a direct call, because the alias is itself such a
       reference.
    """
    tree = ast.parse(src)
    empty = {"launch": None, "spawns": [], "seals": [], "hashes": [], "seal_files": [],
             "manifest_lines": [], "manifest_args": [], "rereads": []}
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    if not fns:
        return empty
    fn = fns[0]
    spawns, launches, seals, hashes, seal_files, rendered = [], [], [], [], [], []
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
        if name == "Popen":
            spawns.append(n.lineno)
            if any(isinstance(k, ast.Name) and k.id == "exe"
                   for a in n.args for k in ast.walk(a)):
                launches.append(n.lineno)
        elif name == "seal_plan":
            seals.append(n.lineno)
        elif name == "plan_sha256":
            hashes.append(n.lineno)
        elif name == "write_seal_file":
            seal_files.append(n.lineno)
        elif name == "plan_manifest":
            rendered.append(n)
    launch = min(launches) if launches else None
    rereads = []
    for n in ast.walk(fn):
        ln = getattr(n, "lineno", None)
        if launch is None or ln is None or ln <= launch:
            continue
        if isinstance(n, ast.Attribute) and n.attr == "path" \
                and isinstance(n.value, ast.Name) and n.value.id == "seal":
            rereads.append(("seal.path", ln))
        elif isinstance(n, ast.Name) and n.id == "plan":
            rereads.append(("plan", ln))
    return {"launch": launch, "spawns": sorted(spawns), "seals": sorted(seals),
            "hashes": sorted(hashes), "seal_files": sorted(seal_files),
            "manifest_lines": sorted(c.lineno for c in rendered),
            "manifest_args": [[type(a).__name__ for a in c.args] for c in rendered],
            "rereads": sorted(rereads, key=lambda r: r[1])}


def seal_claims(src):
    """{claim: bool} -- the nine structural claims, over ANY livesession source.

    One function so the real module and a saboteur are two live answers from one reader,
    rather than a number the test asks the code to confirm about itself.
    """
    i = seal_order(src)
    late = [ln for ln in i["seals"] + i["hashes"]
            if i["launch"] is not None and ln > i["launch"]]
    first_spawn = min(i["spawns"]) if i["spawns"] else None
    return {
        "launch_found": i["launch"] is not None,
        "one_seal": len(i["seals"]) == 1,
        "seal_before_launch": bool(i["seals"]) and i["launch"] is not None
                              and max(i["seals"]) < i["launch"],
        # Stronger than the line above and deliberately kept beside it: the seal precedes
        # EVERY subprocess this function spawns, sniffer included, so an early relaunch
        # under any name reddens this even if it is not recognisable as a client launch.
        "seal_before_first_spawn": bool(i["seals"]) and first_spawn is not None
                                   and min(i["seals"]) < first_spawn,
        "seal_file_before_spawn": bool(i["seal_files"]) and first_spawn is not None
                                  and min(i["seal_files"]) < first_spawn,
        "no_hash_after_launch": i["launch"] is not None and not late,
        "no_plan_reread_after_launch": i["launch"] is not None and not i["rereads"],
        "manifest_after_launch": bool(i["manifest_lines"]) and i["launch"] is not None
                                 and min(i["manifest_lines"]) > i["launch"],
        "manifest_takes_carried": i["manifest_args"] == [["Name"]],
    }


def manifest_literal(src):
    """(the manifest dict's string keys, the lineno of run()'s compare_plan_seals call).

    Asked of the syntax tree rather than of a manifest, because no test in this file can
    reach one: `run()` writes it only after a live client, so §5b/§5d/§5e all call
    `plan_manifest()` in isolation. That gap is exactly how a manifest re-hashing the plan
    passed 75 of 75 -- nothing anywhere read a manifest `run()` produced -- and while this
    does not close it, it does pin the two things about the literal that a test CAN know:
    which keys it carries, and that the verdict beside them is computed from the DIRECTORY
    one statement above rather than inside the dict.
    """
    tree = ast.parse(src)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    if not fns:
        return set(), None
    keys, call = set(), None
    for n in ast.walk(fns[0]):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "manifest" for t in n.targets) \
                and isinstance(n.value, ast.Dict):
            keys |= {k.value for k in n.value.keys
                     if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        if isinstance(n, ast.Call):
            name = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", None)
            if name == "compare_plan_seals":
                call = n.lineno if call is None else min(call, n.lineno)
    return keys, call


def calls_in(src, fname):
    """The set of callee names inside a named module-level function."""
    tree = ast.parse(src)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fname]
    if not fns:
        return set()
    out = set()
    for n in ast.walk(fns[0]):
        if isinstance(n, ast.Call):
            f = n.func
            out.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", None))
    return out


def load_sabotage(src, tag, tmp):
    """Import a sabotaged copy of livesession.py as its own module. Returns the module.

    §5f runs `run()` for real (with every subprocess intercepted), so its sabotages have to
    EXECUTE rather than merely parse -- which is the whole difference between it and §5a.
    `sys.path` is snapshotted and restored because the copy inserts its own directory at
    import time, and leaving a temp directory on the path would change what every later
    import in this process resolves to.
    """
    import importlib.util
    path = os.path.join(tmp, "sab_%s.py" % tag)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    saved_path, saved_mods = list(sys.path), set(sys.modules)
    try:
        spec = importlib.util.spec_from_file_location("sab_%s" % tag, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = saved_path
        for name in set(sys.modules) - saved_mods:
            sys.modules.pop(name, None)
    return mod


def refusal(fn, *a, **k):
    """(refused, why) for a call expected to raise LiveError. NOTHING escapes this.

    A `LiveError` is a refusal and is what every gate in `livesession.py` raises. Anything
    else -- `UnicodeDecodeError` from an unwrapped read, `OSError` from a spawn that should
    never have happened -- is NOT a refusal, and this reports it as one that failed while
    NAMING what came out instead.

    That distinction is the entire point of the helper, and it is worth the six lines
    because it is a defect this file had. The refusal checks used to be written as bare
    `try/except ls.LiveError`, so the moment a sabotage made a plan escape as a
    `UnicodeDecodeError` the test DIED at that line: no verdict banner, no ledger, no floor
    shortfall, and a run that caught a real defect printed a traceback instead of naming
    it. Same failure `test_content.py` records at the first line of its own `main()`, and
    the same reason it is worth fixing -- "a run that measured nothing failed" cannot fire
    in a process that never reaches its verdict. The escaping exception is the FINDING
    here, so it has to arrive as a red check rather than as a crash.
    """
    try:
        fn(*a, **k)
        return False, "no exception at all: the call was ACCEPTED"
    except LiveErrorType as exc:
        return True, str(exc)
    except BaseException as exc:                      # noqa: BLE001 -- see the docstring
        return False, "ESCAPED as %s (not a refusal): %s" % (type(exc).__name__, exc)


class _NoSubprocess(Exception):
    """Raised in place of every spawn, so `run()` stops at its first one."""


def runtime_order(mod, tmp, plan):
    """['SEAL', 'SEAL_FILE', 'POPEN', ...] -- what `run()` ACTUALLY did, in order.

    §5a compares two line numbers. This compares two live answers, and it exists because
    §5a cannot see the textually-early / runtime-late split: move the seal into a nested
    `def` and call it after the launch, and `ast.walk` still reports the `seal_plan` call
    at its early line while the code executes it late. That sabotage passed every one of
    §5a's claims on 2026-08-13; the only thing that caught it was §5c's refusal-placement
    check, and then only because `seal_plan` happens to carry the refusals as well as the
    hash -- decouple those and nothing was left.

    `subprocess.Popen` is patched to log and RAISE, so `run()` gets no further than its
    first spawn, which is the sniffer and is already past everything this measures. Every
    gate between the seal and there is stubbed: `preflight` (which needs the real account,
    the firewall and WinDivert), `slot_rva` (which needs a key-tapped binary) and the two
    `accounts` readers. Stubbing is safe HERE precisely because those gates are checked
    on their own in §4 -- this section asks about ORDER and nothing else.

    `drive_client` and `cage` are imported BEFORE the patch on purpose: `run()` imports
    them mid-function, and `drive_client` resolves the vault at import time, which shells
    out to `git rev-parse`. That spawn is `vaultpath`'s and not the driver's, and the first
    version of this harness reported it as `run()`'s own launch -- so the log read
    ['SEAL', 'POPEN'] and `write_seal_file` looked as though it were never called.
    """
    log = []
    import accounts
    import drive_client  # noqa: F401  -- see the docstring: import-time git subprocess
    import cage          # noqa: F401
    real_popen = subprocess.Popen
    saved = {n: getattr(mod, n) for n in ("preflight", "slot_rva", "seal_plan",
                                          "write_seal_file")}
    saved_acct = (accounts.for_automation, accounts.describe)

    def fake_popen(*_a, **_k):
        log.append("POPEN")
        raise _NoSubprocess("no subprocess is spawned in this test")

    def tagged(name, tag):
        real = saved[name]

        def wrapper(*a, **k):
            log.append(tag)
            return real(*a, **k)
        return wrapper

    mod.preflight = lambda *a, **k: {"account": "capture", "dh": "stock"}
    mod.slot_rva = lambda _exe: 0x1000
    mod.seal_plan = tagged("seal_plan", "SEAL")
    mod.write_seal_file = tagged("write_seal_file", "SEAL_FILE")
    accounts.for_automation = lambda _label: {"label": "capture"}
    accounts.describe = lambda _acct: "capture (stubbed for the order harness)"
    subprocess.Popen = fake_popen
    try:
        mod.run("capture", os.path.join(tmp, "Gw.exe"), "live", {6112}, 1,
                confirm=True, mode="base",
                out_root=os.path.join(tmp, "out_" + os.path.basename(plan)), plan=plan)
    except BaseException as exc:                      # noqa: BLE001 -- the point is order
        log.append("EXC:" + type(exc).__name__)
    finally:
        subprocess.Popen = real_popen
        for name, fn in saved.items():
            setattr(mod, name, fn)
        accounts.for_automation, accounts.describe = saved_acct
    return log


PLAN_TEXT = ("# a pre-registered plan, written before the client launched\n"
             "open\tmerchant Sanura, first open\n"
             "buy\tone salvage kit\n")
PLAN_EDITED = PLAN_TEXT + "regret\tadded halfway through the session\n"


def write_plan(path, text=PLAN_TEXT):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return path


def real_session():
    """A loopback capture we hold the key for: (key, A, seed, c2s_cipher, first_plain) or None."""
    try:
        import vaultpath
        root = vaultpath.require_dir("captures", why="a real session for the assemble test")
    except SystemExit:
        return None
    import replay
    for jl in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        raw = jl[:-6] + ".raw"
        if not os.path.isfile(raw) or os.path.getsize(raw) == 0:
            continue
        A_hex = seed_hex = None
        first_plain = None
        for line in open(jl, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "client_seed":
                A_hex = r.get("a")
            elif r.get("kind") == "server_seed":
                seed_hex = r.get("sent")
            elif r.get("kind") == "frame" and r.get("direction") == "c2s" and first_plain is None:
                first_plain = r.get("plain")
        if not (A_hex and seed_hex and first_plain):
            continue
        try:
            cands = replay.key_from_our_capture(jl)
        except replay.ReplayError:
            continue
        # Concatenate the c2s ciphertext chunks in file order == the continuous stream.
        c2s_cipher = b"".join(c for _i, d, _t, c in replay.read_raw(raw) if d == "c2s")
        for _label, key in cands:
            # The right key is the one that decrypts the first chunk to the logged plain.
            probe = ARC4(key).crypt(c2s_cipher)
            if probe[:len(bytes.fromhex(first_plain))] == bytes.fromhex(first_plain):
                return key, bytes.fromhex(A_hex), bytes.fromhex(seed_hex), c2s_cipher, \
                       bytes.fromhex(first_plain)
    return None


def c2s_handshake(A):
    return (struct.pack("<I", ls.AUTH_VERSION_HEADER) + struct.pack("<III", 38797, 1, 4)
            + struct.pack("<H", ls.CLIENT_SEED_HEADER) + A)


def game_c2s_handshake(A, acct=b"\xaa" * 16, char=b"\xbb" * 16):
    """The GAME channel's VERSION, whose body is 60 bytes rather than the auth shape's 12.

    Built from the live capture of 2026-08-07: header 0x000C0500, then build/1/id/n/n, two
    16-byte uuid-shaped fields and eight zero bytes, and only THEN CLIENT_SEED -- at offset
    64 instead of 16. Our own server never speaks this shape, so nothing on loopback could
    have produced it and the first live run decrypted 1 of 7 connections because of it.
    """
    body = (struct.pack("<IIIII", 38797, 1, 0xE10DEFA9, 0x0202, 0x3D534856)
            + acct + char + b"\x00" * 8)
    assert len(body) == 60, len(body)
    return (struct.pack("<I", ls.GAME_VERSION_HEADER) + body
            + struct.pack("<H", ls.CLIENT_SEED_HEADER) + A)


def s2c_handshake(seed):
    return struct.pack("<H", ls.SERVER_SEED_HEADER) + seed


def write_wire(path, c2s, s2c, client="10.0.0.9:5000", server="3.65.1.1:6112"):
    fh, record = wc.open_capture(path, client, server, 4242, {6112},
                                 lambda: 0.0)
    record(wc.C2S, 0, c2s)
    record(wc.S2C, 0, s2c)
    fh.close()


def main():
    # ---- 1. split parses and refuses ------------------------------------------
    print("1. split_c2s / split_s2c parse the handshake and refuse what is not")
    A = bytes(range(64))
    seed = bytes(range(100, 120))
    a_got, cipher = ls.split_c2s(c2s_handshake(A) + b"CIPHERC2S")
    LEDGER.ok(a_got == A and cipher == b"CIPHERC2S",
              "split_c2s returns A and the ciphertext after the handshake", a_got.hex()[:16])
    s_got, s_cipher = ls.split_s2c(s2c_handshake(seed) + b"CIPHERS2C")
    LEDGER.ok(s_got == seed and s_cipher == b"CIPHERS2C",
              "split_s2c returns the server seed and the ciphertext after it")
    try:
        ls.split_c2s(b"\x00\x00\x00\x00not a handshake at all............")
        refused = False
    except ls.SplitError:
        refused = True
    LEDGER.ok(refused, "a c2s stream not starting with VERSION is refused, not decrypted")

    # The GAME shape. Its body is 60 bytes, not 12, so CLIENT_SEED is at offset 64 -- and
    # a reader that assumes the auth shape refuses every game connection in a live capture.
    g_got, g_cipher = ls.split_c2s(game_c2s_handshake(A) + b"GAMECIPHER")
    LEDGER.ok(g_got == A and g_cipher == b"GAMECIPHER",
              "split_c2s parses the GAME version shape too (CLIENT_SEED at 64, not 16)",
              "OBSERVED from the 2026-08-07 live capture: 6 of its 7 connections")
    try:
        ls.split_c2s(struct.pack("<I", 0x000C0600) + b"\x00" * 200)
        unknown_ok = False
        why = ""
    except ls.SplitError as ex:
        unknown_ok, why = True, str(ex)
    LEDGER.ok(unknown_ok and "0x000c0400" in why and "0x000c0500" in why,
              "an UNKNOWN version header is still refused, and the refusal names what it "
              "does know", "a third shape must stop the reader, not be guessed past")

    # ---- 2. real bytes: split + decrypt reproduce the logged plaintext ---------
    print("\n2. on a real session's own c2s ciphertext, split+decrypt match the log")
    real = real_session()
    if not real:
        LEDGER.skip("real assemble", "no vaulted loopback session with a .raw and a key")
    else:
        key, A, seed, c2s_cipher, first_plain = real
        # Build the c2s WIRE stream: handshake + the real ciphertext.
        _a, cipher = ls.split_c2s(c2s_handshake(A) + c2s_cipher)
        LEDGER.ok(cipher == c2s_cipher,
                  "split recovers exactly the real ciphertext after the handshake",
                  f"{len(cipher)} bytes")
        plain = ls.decrypt_stream(cipher, key)
        LEDGER.ok(plain[:len(first_plain)] == first_plain,
                  "decrypting the wire ciphertext reproduces the server's logged plaintext",
                  "the same bytes replay.py verifies, reached from the wire side")

        # ---- 3. full assemble() round-trips both directions --------------------
        print("\n3. assemble() writes a LIVE, both-direction capture that decrypts correctly")
        # s2c has no vaulted ciphertext (the .raw is c2s only), so synthesise one the
        # honest way: real key, known plaintext, real ARC4. There is deliberately no
        # "re-encrypt matches" assertion -- ARC4 is symmetric, so that holds for any key
        # and would be a check that cannot fail. The real check is that assemble's output
        # equals the KNOWN plaintext, below, which a wrong key would not reproduce.
        s2c_plain_src = b"the server said this, and it must come back out" * 3
        s2c_cipher = ARC4(key).crypt(s2c_plain_src)
        with tempfile.TemporaryDirectory() as tmp:
            wire = os.path.join(tmp, "live.jsonl")
            out = os.path.join(tmp, "decrypted.jsonl")
            write_wire(wire, c2s_handshake(A) + c2s_cipher, s2c_handshake(seed) + s2c_cipher)
            rep = ls.assemble(wire, key, out)
            LEDGER.ok(rep["A"] == A.hex() and rep["server_seed"] == seed.hex(),
                      "the handshake A and server seed are carried into the artifact")
            who, why = origin.origin_of(out)
            LEDGER.ok(who == origin.LIVE, "the assembled capture is stamped origin: live", why)
            LEDGER.ok("UNCORROBORATED" not in why,
                      "and it records the endpoints that stamp was derived from",
                      "deriving the stamp without recording its basis is still "
                      "unfalsifiable -- a reader must be able to disagree")

            # The SAME function against loopback must not say live. dryrun_keycapture.py
            # drives exactly this path at 127.0.0.1, and it stamped LIVE for a day.
            lb_wire = os.path.join(tmp, "lb_wire.jsonl")
            lb_out = os.path.join(tmp, "lb_out.jsonl")
            write_wire(lb_wire, c2s_handshake(A) + c2s_cipher,
                       s2c_handshake(seed) + s2c_cipher,
                       client="127.0.0.1:51000", server="127.0.0.1:6112")
            ls.assemble(lb_wire, key, lb_out)
            lb_who, lb_why = origin.origin_of(lb_out)
            LEDGER.ok(lb_who == origin.OURS,
                      "the same assemble() against LOOPBACK stamps ours, not live", lb_why)
            recs = [json.loads(l) for l in open(out, encoding="utf-8")]
            c2s_rec = [r for r in recs if r.get("direction") == "c2s"][0]
            LEDGER.ok(bytes.fromhex(c2s_rec["plain"])[:len(first_plain)] == first_plain,
                      "the c2s direction decrypts to the server's real logged plaintext",
                      "a wrong key could not reproduce these bytes")
            s2c = [r for r in recs if r.get("direction") == "s2c"][0]
            LEDGER.ok(bytes.fromhex(s2c["plain"]) == s2c_plain_src,
                      "the s2c direction decrypts back to the known plaintext")
            keys_present = {r.get("kind") for r in recs}
            LEDGER.ok({"session_key", "client_seed", "server_seed"} <= keys_present,
                      "arc4_key / a / sent are recorded under the scrub's own field names",
                      "so scrub_captures.py redacts them before the capture leaves the vault")

    # ---- 3b. the LIVE shape: several connections, several keys -----------------
    print("\n3b. assemble_live pairs keys to connections, and refuses when none fits")
    # A real session is two DH-keyed channels on separate connections with DIFFERENT keys,
    # plus one carrying no handshake. The single tap slot is overwritten at each handshake,
    # so the driver carries a keyring; the channel comes from each connection's VERSION
    # header and the KEY is settled by key_fits, which a wrong key rarely satisfies.
    auth_key = arc4_hash(bytes(range(20)))
    game_key = arc4_hash(bytes(range(20, 40)))
    auth_plain = struct.pack("<H", 0x8001) + b"\x05\x00hello-auth"     # OBSERVED live
    game_plain = struct.pack("<H", 0x808a) + b"\x91\x80walking"        # OBSERVED loopback
    # key_fits passes 487 of 65536 values, so a fixed "wrong" key could pass by luck and
    # make the refusal test vacuous. Pick one that demonstrably fails BOTH connections,
    # and fail loudly if no candidate does rather than testing nothing.
    wrong_key = None
    for n in range(64):
        cand = arc4_hash(bytes([n]) * 20)
        if cand not in (auth_key, game_key) and not any(
                ls.key_fits(ARC4(cand).crypt(ARC4(k).crypt(p)))
                for k, p in ((auth_key, auth_plain), (game_key, game_plain))):
            wrong_key = cand
            break
    A1, A2 = bytes(range(64)), bytes(range(64, 128))
    seed1, seed2 = bytes(range(20)), bytes(range(40, 60))

    def wire_conn(record, cip, cport, sip, sport, c2s, s2c):
        for direction, payload, a, b, pa, pb in (
                (wc.C2S, c2s, cip, sip, cport, sport),
                (wc.S2C, s2c, sip, cip, sport, cport)):
            record(direction, 1000, payload,
                   {"src": a, "sport": pa, "dst": b, "dport": pb})

    with tempfile.TemporaryDirectory() as tmp:
        wire = os.path.join(tmp, "wire.jsonl")
        fh, record = wc.open_capture(wire, "10.0.0.9:*", None, 4242, {6112, 6601},
                                     lambda: 0.0)
        wire_conn(record, "10.0.0.9", 51000, "3.65.1.1", 6112,
                  c2s_handshake(A1) + ARC4(auth_key).crypt(auth_plain),
                  s2c_handshake(seed1) + ARC4(auth_key).crypt(b"auth said this"))
        wire_conn(record, "10.0.0.9", 51001, "3.65.9.9", 6112,
                  game_c2s_handshake(A2) + ARC4(game_key).crypt(game_plain),
                  s2c_handshake(seed2) + ARC4(game_key).crypt(b"game said this"))
        # A third connection on a sniffed port whose handshake is NOT at the front -- the
        # realistic live case is a connection the sniff joined mid-stream, or a reconnect.
        # It must be reported, not crashed on, and not fed to ARC4 as if it were a channel.
        wire_conn(record, "10.0.0.9", 51002, "3.65.1.1", 6112,
                  b"\x99\x99 not a handshake, joined mid-stream", b"\x88\x88 nor is this")
        fh.close()

        keyring = [("tap@1.0s", auth_key), ("tap@9.0s", game_key)]
        rep = ls.assemble_live(wire, keyring, tmp)
        by_channel = {r.get("channel"): r for r in rep["connections"] if r.get("decrypted")}
        LEDGER.ok(rep["decrypted"] == 2 and set(by_channel) == {"auth", "game"},
                  "both DH-keyed connections decrypt, each under its own tapped key",
                  f"{rep['decrypted']}/{rep['total']} connections")
        LEDGER.ok(by_channel.get("auth", {}).get("key_from") == "tap@1.0s"
                  and by_channel.get("game", {}).get("key_from") == "tap@9.0s",
                  "each connection is paired with the RIGHT key, not the first one",
                  "swapping them would decrypt to a wrong first opcode")
        auth_out = [json.loads(l) for l in open(by_channel["auth"]["out"], encoding="utf-8")]
        LEDGER.ok(bytes.fromhex([r for r in auth_out
                                 if r.get("direction") == "c2s"][0]["plain"]) == auth_plain,
                  "the auth connection decrypts back to its exact plaintext")
        LEDGER.ok(origin.origin_of(by_channel["game"]["out"])[0] == origin.LIVE,
                  "every file assemble_live writes is stamped origin: live")
        stray = [r for r in rep["connections"] if r["connection"].startswith("10.0.0.9:51002")]
        LEDGER.ok(len(stray) == 1 and not stray[0]["decrypted"]
                  and "no GW handshake" in stray[0]["why"],
                  "a connection with no handshake at its front is reported, not crashed on",
                  "a mid-stream join is a normal outcome of a sniff, not an error")

        # And the case that matters most: a keyring that does NOT hold the right key must
        # produce NOTHING, rather than a plausible-looking file full of garbage.
        LEDGER.ok(wrong_key is not None,
                  "a genuinely non-fitting key was found for the refusal test below",
                  "otherwise that assertion would pass without testing anything")
        before = set(os.listdir(tmp))
        bad = ls.assemble_live(wire, [("tap@0.0s", wrong_key)], tmp)
        LEDGER.ok(bad["decrypted"] == 0,
                  "a keyring with only a WRONG key decrypts nothing at all",
                  "ARC4 is symmetric, so 'it decrypted' is not evidence -- the first "
                  "opcode is")
        LEDGER.ok(not any(f.startswith(("auth-", "game-")) and f not in before
                          for f in os.listdir(tmp)),
                  "and it writes no NEW file, so a bad run leaves no believable artifact")
        LEDGER.ok(bad.get("stale_kept") and not bad.get("stale_removed"),
                  "a run that decrypts NOTHING keeps the earlier files and flags them",
                  "deleting here would let a failed verification destroy a good decryption")
        good = ls.assemble_live(wire, keyring, tmp)
        LEDGER.ok(good["decrypted"] == 2 and not good.get("stale_kept"),
                  "a run that DOES decrypt owns the directory again",
                  "so a partial re-assemble cannot leave files that fake a full one")

        # prune_wire: the filter has to include port 80 to catch GW at all, and port 80
        # also carries whatever else the machine is doing. That must not reach the vault.
        kept, dropped = ls.prune_wire(wire)
        LEDGER.ok(kept == 2 and dropped > 0,
                  "prune_wire keeps the GW connections and drops the rest",
                  f"{kept} kept, {dropped} record(s) dropped")
        _m, after = wc.load_connections(wire)
        LEDGER.ok(all(ls.channel_of_stream(e[wc.C2S]) for e in after.values()),
                  "every connection left in the pruned capture carries a GW handshake",
                  "unrelated HTTP is the owner's own traffic, not evidence")
        LEDGER.ok(ls.assemble_live(wire, keyring, tmp)["decrypted"] == 2,
                  "and the pruned capture still assembles both channels",
                  "pruning must not cost a single GW byte")
        LEDGER.ok(all("none of the 1 tapped key(s)" in r["why"]
                      for r in bad["connections"] if r.get("A")),
                  "the refusal names how many keys were tried")

    LEDGER.ok(ls.channel_of_stream(c2s_handshake(A)) == "auth"
              and ls.channel_of_stream(game_c2s_handshake(A)) == "game",
              "the channel is read from the VERSION header, the field that carries it",
              "not guessed from whichever opcode the first message happens to be")
    LEDGER.ok(all(ls.key_fits(struct.pack("<H", op))
                  for op in (0x8001, 0x800a, 0x8091, 0x808a)),
              "key_fits accepts every first opcode OBSERVED, live and on loopback",
              "the old literal-value table rejected 0x800a and 0x8091 and reported two "
              "live connections undecryptable whose keys we were holding")
    LEDGER.ok(not ls.key_fits(struct.pack("<H", 0x0001))
              and not ls.key_fits(struct.pack("<H", 0xcad4))
              and not ls.key_fits(b""),
              "and rejects a clear direction bit, an out-of-catalog opcode, and no bytes",
              "487 of 65536 values pass, so a wrong key still has roughly 1 in 135")

    # ---- 3c. the keyring reaches DISK, and a capture re-assembles from it -------
    print("\n3c. the keyring is persisted per key, and re-assembly works without a client")
    # The first live run held its keyring in memory: 7 keys tapped, 1 written (by the one
    # connection that assembled), and 6 channels of real ArenaNet ciphertext became
    # permanently undecryptable when the process exited. There is no recovering those --
    # the key derives from ArenaNet's private exponent. So the keyring is written as each
    # key appears, and a capture directory can be decoded again from its own two files.
    with tempfile.TemporaryDirectory() as tmp:
        kr = os.path.join(tmp, "keyring.jsonl")
        ring = ls.KeyRing.__new__(ls.KeyRing)      # no live process to poll
        ring.path, ring.errors = kr, 0
        with open(kr, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(origin.record("test", origin.LIVE)) + "\n")
        ring._persist(1.04, bytes(range(20)), auth_key)
        ring._persist(9.10, bytes(range(20, 40)), game_key)
        back = ls.load_keyring(kr)
        LEDGER.ok([k for _l, k in back] == [auth_key, game_key],
                  "every tapped key is on disk, in order, and reads back exactly",
                  f"{len(back)} keys -- written per key, not per run")
        LEDGER.ok(origin.origin_of(kr)[0] == origin.LIVE,
                  "the keyring file is itself stamped origin: live")
        raw = open(kr, encoding="utf-8").read()
        LEDGER.ok("master_secret" in raw and "arc4_key" in raw,
                  "it records master_secret AND the derived key, under names the scrub "
                  "treats as secret", "so a re-derivation is possible if arc4_hash changes")

        # A whole capture directory, decoded again from nothing but its own two files.
        rd = os.path.join(tmp, "capture")
        os.makedirs(rd)
        fh, record = wc.open_capture(os.path.join(rd, "wire.jsonl"), "10.0.0.9:*", None,
                                     0, {6112}, lambda: 0.0)
        wire_conn(record, "10.0.0.9", 51000, "3.65.1.1", 6112,
                  c2s_handshake(A1) + ARC4(auth_key).crypt(auth_plain),
                  s2c_handshake(seed1) + ARC4(auth_key).crypt(b"auth said this"))
        wire_conn(record, "10.0.0.9", 51001, "3.65.9.9", 6112,
                  game_c2s_handshake(A2) + ARC4(game_key).crypt(game_plain),
                  s2c_handshake(seed2) + ARC4(game_key).crypt(b"game said this"))
        fh.close()
        import shutil
        shutil.copy(kr, os.path.join(rd, "keyring.jsonl"))
        rc = ls.reassemble(rd)
        LEDGER.ok(rc == 0, "reassemble() decodes a capture directory with no client, no "
                           "network and no account", "R0b's 'byte-replayable from disk'")
        outs = sorted(f for f in os.listdir(rd) if f.startswith(("auth-", "game-")))
        LEDGER.ok(len(outs) == 2,
                  "both an auth-shaped and a GAME-shaped connection come back",
                  ", ".join(outs))

        # AND THE MANIFEST HAS TO AGREE WITH THE DIRECTORY. reassemble() recomputed the
        # whole report, printed it and dropped it until 2026-08-18, so a capture that
        # gained connections on a re-run went on advertising the old refusal forever --
        # observed on 20260817T231139, which reached 15/15 on disk while its manifest
        # still said `decrypted: false` for the largest connection in the corpus.
        import json as _json
        man = os.path.join(rd, "manifest.json")
        with open(man, "w", encoding="utf-8") as fh:
            _json.dump({"stamp": "fixture", "keep_me": 7,
                        "report": {"decrypted": 0, "total": 0, "connections": []},
                        "report_from": None}, fh)
        rc2 = ls.reassemble(rd)
        with open(man, encoding="utf-8") as fh:
            after = _json.load(fh)
        LEDGER.ok(rc2 == 0 and after["report"]["decrypted"] == 2,
                  "reassemble() WRITES the recomputed report back into manifest.json",
                  "a stale report is a consumer skipping a file that is sitting right "
                  "there and frames cleanly")
        LEDGER.ok(after.get("report_from") == "reassemble",
                  "and stamps WHICH writer produced it",
                  "absent means run() wrote it and it was never re-assembled")
        LEDGER.ok(after.get("keep_me") == 7 and after.get("stamp") == "fixture",
                  "every other manifest field survives the rewrite untouched",
                  "update_manifest is the only code that edits a run's primary artifact")

    # ---- 4. the guards refuse --------------------------------------------------
    print("\n4. the guards refuse the primary, a non-stock client, and no --confirm")
    try:
        accounts_primary_refused = False
        import accounts
        try:
            accounts.for_automation("primary")
        except SystemExit:
            accounts_primary_refused = True
    except Exception:
        accounts_primary_refused = True
    LEDGER.ok(accounts_primary_refused, "for_automation refuses the primary account")

    try:
        ls.run("capture", "x", "3.65.1.1", {6112}, 20, confirm=False)
        no_confirm = False
    except ls.LiveError as e:
        no_confirm = "--confirm" in str(e)
    LEDGER.ok(no_confirm, "a live run with no --confirm is refused, naming --confirm")

    # --mode, and it is refused for the same reason --confirm is: a value the operator
    # must state, never guessed. Reforged Mode changes enemy health and armour ~20% and
    # leaves NO mark on the recorded stream, so an unstamped capture's stats can never be
    # graded -- base or base x 0.8, forever, at a size that reads as a plausible base
    # value rather than an obvious error. The refusal must land BEFORE the client
    # launches, because it cannot be asked afterwards.
    # Through `refusal()`, which folds the old three-arm try/except and adds the arm it
    # did not have: anything that is neither a LiveError nor a SystemExit used to KILL the
    # run here, verdict and ledger and all. A sabotage that spawns a client above the seal
    # reached this line and died on an OSError from the fake exe, so a test that had caught
    # a real defect printed a traceback instead of naming it.
    refused, why = refusal(ls.run, "capture", "x", "3.65.1.1", {6112}, 20, confirm=True)
    no_mode = refused and "--mode" in why      # a SystemExit is past the gate, so not one
    LEDGER.ok(no_mode, "a live run with no --mode is refused, naming --mode",
              "and it refuses BEFORE preflight -- a SystemExit here would mean the run "
              "reached the launch path with the mode unstated")

    # An invented mode must be refused too. A free-string flag would let `--mode reforge`
    # or `--mode Base` through to the manifest and stamp a capture with a value nothing
    # downstream knows how to read; `choices` catches it at the CLI and this catches it
    # at the API, which is the half a caller can reach.
    refused, why = refusal(ls.run, "capture", "x", "3.65.1.1", {6112}, 20,
                           confirm=True, mode="reforge")
    bad_mode = refused and "--mode" in why
    LEDGER.ok(bad_mode, "and a mode outside base|reforged is refused rather than stamped",
              f"the vocabulary is {'|'.join(ls.GAME_MODES)}")

    # THE CONTROL, and without it the two checks above pass for a run() that refuses
    # everything. A VALID mode must get past the mode gate -- it then fails later, in
    # preflight, on the fake exe, which is a different failure and is what proves the gate
    # is specific rather than a wall.
    refused, why = refusal(ls.run, "capture", "x", "3.65.1.1", {6112}, 20,
                           confirm=True, mode="base")
    # Past the gate = anything that is not the MODE refusal: preflight's own LiveError,
    # its SystemExit, or the fake exe failing. Only "--mode" in a LiveError is a wall.
    valid_passed = not (refused and "--mode" in why)
    LEDGER.ok(valid_passed,
              "CONTROL: a VALID mode passes the gate and fails later on the fake client",
              "otherwise both refusals above are satisfied by a run() that refuses "
              "everything, which is a wall rather than a check")

    # A loopback (ours-DH) client aimed live must be refused by preflight's stock check.
    try:
        import vaultpath
        loop_exe = os.path.join(vaultpath.vault_path("run", "2026-07-29_221c13772c7a"), "Gw.exe")
        have = os.path.isfile(loop_exe)
    except SystemExit:
        have = False
    if not have:
        LEDGER.skip("stock gate", "no loopback client staged to try against a live host")
    else:
        try:
            ls.preflight("capture", loop_exe, "3.65.1.1", want_windivert=False)
            gate = False
        except SystemExit:
            gate = True          # refused: an ours-DH client may never be aimed live
        LEDGER.ok(gate, "an ours-DH loopback client is refused when aimed at a live host",
                  "the stock->live cell is the only one preflight accepts")

    # ---- 5a. the seal is taken BEFORE the launch, asked of the syntax tree ------
    print("\n5a. the plan seal precedes the client launch, and the manifest does not re-hash")
    src = open(ls.__file__, encoding="utf-8").read()
    real = seal_claims(src)
    info = seal_order(src)
    # The anchor first. Every ordering claim under it is vacuous if the launch statement
    # is not found -- a renamed local or a different spawn idiom would silently turn all
    # of section 5a green while measuring nothing.
    LEDGER.ok(real["launch_found"],
              "the client launch statement is located in run() by SHAPE",
              f"the EARLIEST `*.Popen(...)` whose argument names `exe`, line "
              f"{info['launch']}, out of spawns {info['spawns']} -- not the sniffer's, "
              f"which a text search cannot tell apart, and not the last one walked")
    # The other half of the vacuity guard, and it is the one that makes the ordering mean
    # something: the manifest really is written at the END. If it moved above the launch,
    # "the seal is before the launch" would say nothing at all about what the manifest
    # records, which is the actual claim.
    LEDGER.ok(real["manifest_after_launch"],
              "and the manifest is rendered AFTER it, so the ordering claim is not trivial",
              f"plan_manifest at line {info['manifest_lines']} > launch {info['launch']}")
    LEDGER.ok(real["one_seal"],
              "run() seals the plan exactly once", f"seal_plan at line {info['seals']}")
    LEDGER.ok(real["seal_before_launch"],
              "THE SEAL IS TAKEN BEFORE THE CLIENT LAUNCHES",
              "a hash taken at manifest time would certify whatever the plan said "
              "AFTERWARDS, which is a signature on the answer sheet")
    LEDGER.ok(real["seal_before_first_spawn"],
              "and before EVERY subprocess run() spawns, not merely the client one",
              f"seals {info['seals']} < first spawn {min(info['spawns'])} of "
              f"{info['spawns']} -- a relaunch bound to some other name is still a spawn")
    LEDGER.ok(real["seal_file_before_spawn"],
              "write_seal_file is CALLED in run(), before the first spawn",
              f"line {info['seal_files']}: deleting this one call left the whole suite "
              f"green on 2026-08-13, and a run that died then had no seal at all")
    LEDGER.ok(real["no_hash_after_launch"],
              "and nothing re-hashes the plan after the launch, at any depth",
              "the manifest must read the CARRIED value; re-reading the file at the end "
              "is the same defect wearing a different call")
    LEDGER.ok(real["no_plan_reread_after_launch"],
              "NOTHING AFTER THE LAUNCH MENTIONS seal.path OR plan, at any depth",
              f"rereads {info['rereads']} -- the callee-name rule above cannot close "
              f"this: livesession.py has its own file hasher called `sha256` and calls "
              f"it three times in the manifest literal, so `sha256(seal.path)` passed "
              f"75 of 75 twice. Re-deriving needs the PATH; that set is closed")
    LEDGER.ok(real["manifest_takes_carried"],
              "plan_manifest is handed a bare name, never a path or a call",
              f"args {info['manifest_args']} -- a path argument would let this site "
              f"re-open the file and the seal would silently become a late one")

    # THE SABOTAGES, built out of one-line moves of the LIVE source and run through the
    # same reader. They need only parse: the claims above are structural, so a source
    # that would not execute is still exactly the input this check takes. (§5f's four
    # have to EXECUTE, which is why they are built separately down there.)
    seal_stmt = "    seal = seal_plan(plan) if plan is not None else None\n"
    manifest_stmt = "    manifest = {\"stamp\": stamp,"
    sab_move = src.replace(seal_stmt, "    seal = None\n", 1)
    sab_move = sab_move.replace(manifest_stmt, seal_stmt + manifest_stmt, 1)
    sab_late = src.replace(
        manifest_stmt,
        "    _late = marks.plan_sha256(plan) if plan else None\n" + manifest_stmt, 1)
    # THE ONE BOTH REVIEWS FOUND, and neither old check could see: the manifest re-hashing
    # the plan through livesession's OWN `sha256()` helper, which is already called three
    # times in the same dict and cannot be added to a callee denylist for that reason.
    sab_ownhash = src.replace(
        "                **plan_manifest(seal),",
        "                **plan_manifest(seal),\n"
        "                \"plan_sha256\": sha256(seal.path) if seal else None,", 1)
    # And the earliest-launch one: a crash-relaunch ABOVE the seal, which the old reader
    # walked first and then overwrote with the real launch nested inside `try:`.
    sab_early = src.replace(
        seal_stmt,
        "    import subprocess as _sp\n"
        "    _relaunch = _sp.Popen([exe], cwd=os.path.dirname(exe))\n" + seal_stmt, 1)
    LEDGER.ok(len({src, sab_move, sab_late, sab_ownhash, sab_early}) == 5,
              "CONTROL: all four sabotage edits actually applied to the live source",
              "an edit that missed its anchor is a saboteur that proves the code is fine")
    moved, lated = seal_claims(sab_move), seal_claims(sab_late)
    owned, early = seal_claims(sab_ownhash), seal_claims(sab_early)
    LEDGER.ok(not moved["seal_before_launch"] and not moved["no_hash_after_launch"]
              and moved["launch_found"] and moved["manifest_after_launch"],
              "SABOTAGE: the seal moved to manifest time reddens the ordering check",
              "and only it -- the anchors stay green, so the failure names the defect")
    LEDGER.ok(lated["seal_before_launch"] and not lated["no_hash_after_launch"],
              "SABOTAGE: a second hash at manifest time reddens ONE other check",
              "the seal is still early, so an ordering check alone would pass a driver "
              "that seals early and then overwrites it with a late hash")
    LEDGER.ok(not owned["no_plan_reread_after_launch"]
              and owned["seal_before_launch"] and owned["no_hash_after_launch"]
              and owned["manifest_takes_carried"],
              "SABOTAGE: the manifest re-hashing via sha256(seal.path) reddens the "
              "ARGUMENT check, and nothing else in 5a",
              f"it re-derives at {seal_order(sab_ownhash)['rereads']} while every "
              f"callee-name claim stays green -- which is exactly how it passed 75/75")
    # It reddens a THIRD, and that is the reader being right rather than being noisy: with
    # a launch at the top of the function the seal statement itself is now post-launch, so
    # its own `plan` reference is a re-read. Asserted as measured -- the first version of
    # this check demanded `no_plan_reread_after_launch` stay GREEN and went red for a
    # correct answer, which is how a check ends up loosened to match a defect.
    LEDGER.ok(not early["seal_before_launch"] and not early["seal_before_first_spawn"]
              and not early["no_plan_reread_after_launch"] and early["launch_found"]
              and early["manifest_after_launch"],
              "SABOTAGE: a relaunch inserted ABOVE the seal reddens both ordering checks",
              f"launch now {seal_order(sab_early)['launch']} < seal "
              f"{seal_order(sab_early)['seals']}; the old reader kept the LAST-walked "
              f"launch and reported the one nested in `try:` instead, so this passed "
              f"75/75 with a client spawning one line before the seal")

    # ---- 5b. an edit after the seal does not move what the manifest records -----
    print("\n5b. a plan edited between the seal and the manifest keeps the sealed hash")
    with tempfile.TemporaryDirectory() as tmp:
        plan = write_plan(os.path.join(tmp, "plan.txt"))
        seal = ls.seal_plan(plan)
        sealed_sha, sealed_steps = seal.sha256, seal.steps
        # The independent witness for the hash itself: hashlib over the raw bytes, in this
        # file, sharing no code with marks.plan_sha256 beyond the library.
        LEDGER.ok(sealed_sha == hashlib.sha256(open(plan, "rb").read()).hexdigest()
                  and sealed_steps == 2,
                  "seal_plan hashes the plan's RAW BYTES and parses its steps",
                  f"{sealed_steps} steps (the comment line is not one), "
                  f"sha256 {sealed_sha[:16]}...")
        # Now the operator edits the plan mid-session, which is the whole scenario.
        write_plan(plan, PLAN_EDITED)
        LEDGER.ok(ls.seal_plan(plan).sha256 != sealed_sha,
                  "CONTROL: editing the plan really does change its sha256",
                  "otherwise the check below passes against a file that never moved")
        man = ls.plan_manifest(seal)
        LEDGER.ok(man["plan_sha256"] == sealed_sha,
                  "the manifest records the PRE-LAUNCH hash, not the edited file's",
                  "this is the whole feature: the seal is what the plan said BEFORE")
        LEDGER.ok(man["plan_steps"] == 2,
                  "and the sealed step count too, not the edited file's 3",
                  "a consumer comparing steps against marks_meta would otherwise be "
                  "comparing two readings of two different files")
        # And the on-disk copy, which is what survives a run that never reaches its
        # manifest -- the failure _install_sigint's docstring already records.
        os.makedirs(os.path.join(tmp, "cap"))
        sp = ls.write_seal_file(os.path.join(tmp, "cap"), seal)
        rec = json.load(open(sp, encoding="utf-8"))
        LEDGER.ok(rec["plan_sha256"] == sealed_sha,
                  "plan_seal.json holds the same pre-launch hash",
                  "written when the capture directory appears, so a run killed before "
                  "assembly still has its seal")
        # THE PREDICTION IS ARCHIVED, not merely hashed. Until 2026-08-13 the capture held
        # a hash of a file living somewhere else, so an operator who rewrote or deleted the
        # plan afterwards left a pre-registration that could only be FAILED against and
        # never READ. The body is self-checking against the seal, which is what makes it
        # evidence rather than a copy: same bytes, same sha256.
        LEDGER.ok(rec.get("plan_body") == PLAN_TEXT
                  and hashlib.sha256(rec["plan_body"].encode("utf-8")).hexdigest()
                  == sealed_sha,
                  "and the plan's TEXT, which re-hashes to the sealed sha256",
                  "a hash of a file that no longer exists is a pre-registration nobody "
                  "can read; the round trip is what makes the archived copy the sealed one")

        # THE SEAL'S OWN WINDOW. seal_plan used to make TWO independent reads -- parse,
        # then hash -- and adversarial review 2026-08-13 drove a rewrite between them, so
        # `steps` described the original file and `sha256` the replacement. Reproduce that
        # exactly, by making the PARSE itself rewrite the file.
        window = write_plan(os.path.join(tmp, "window.txt"))
        real_load = marks.load_plan

        def load_then_rewrite(path):
            out = real_load(path)
            write_plan(path, PLAN_EDITED)      # the file moves under the seal
            return out
        marks.load_plan = load_then_rewrite
        try:
            caught, why = refusal(ls.seal_plan, window)
        finally:
            marks.load_plan = real_load
        LEDGER.ok(caught and "CHANGED WHILE IT WAS BEING SEALED" in why,
                  "a plan that moves BETWEEN the parse and the hash is refused",
                  "the old two-read seal recorded a hash of bytes that were never "
                  "parsed beside a step count describing a different file -- and "
                  "compare_plan_seals then blamed 'the two parsers', which is backwards")
        # THE POSITIVE CONTROL for it, because a re-hash guard that fires on every plan
        # would refuse every run. Same file, same wrapper shape, no rewrite.
        marks.load_plan = lambda path: real_load(path)
        try:
            steady = ls.seal_plan(window).steps == 3
        except BaseException:                          # noqa: BLE001 -- red, never fatal
            steady = False
        finally:
            marks.load_plan = real_load
        LEDGER.ok(steady,
                  "CONTROL: a plan that does NOT move is sealed normally",
                  "the guard is on the file changing, not on the second read happening")

    # ---- 5c. the refusals, and the control that they are not a wall -------------
    print("\n5c. a plan that cannot be a pre-registration is refused before anything launches")
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "nope.txt")
        empty = write_plan(os.path.join(tmp, "empty.txt"), "\n# only a comment\n\n")
        malformed = write_plan(os.path.join(tmp, "bad.txt"), "open\tfine\n\tno kind here\n")
        good = write_plan(os.path.join(tmp, "good.txt"))
        # A text editor's "Unicode" save. `marks.load_plan` opens encoding="utf-8" and
        # wraps nothing, so this used to escape seal_plan as a bare UnicodeDecodeError
        # with no mention of --plan -- and the remedy the generic message offers
        # (`--check-plan`) reads the file with the same loader and dies on the same bytes.
        utf16 = os.path.join(tmp, "utf16.txt")
        open(utf16, "wb").write(PLAN_TEXT.encode("utf-16"))
        # And the other half of the same class: a cp1252 smart quote pasted in.
        cp1252 = os.path.join(tmp, "cp1252.txt")
        open(cp1252, "wb").write(b"open\tmerchant Sanura\x92s stall\n")
        for label, path, detail in (
                ("a --plan that does not exist", missing,
                 "an unlabelled run must not be reachable by accident"),
                ("an EMPTY plan", empty,
                 "the unlabelled run wearing a file -- comments do not make a prediction"),
                ("a plan that does not PARSE", malformed,
                 "a step whose kind is empty names nothing and cannot be a prediction"),
                ("a plan saved as UTF-16", utf16,
                 "a text editor's \"Unicode\" save used to escape as a bare "
                 "UnicodeDecodeError with no mention of --plan"),
                ("a plan holding a cp1252 smart quote", cp1252,
                 "the same class from the other side: one pasted character, and the "
                 "loader the refusal message recommends fails on the same bytes"),
                ("a --plan that is the EMPTY STRING", "",
                 "`--plan \"$PLAN\"` with the variable unset: run()'s guard used to be "
                 "truthiness, so this became an unlabelled run whose manifest gave the "
                 "FALSE reason \"no --plan was passed\"")):
            refused, why = refusal(ls.seal_plan, path)
            LEDGER.ok(refused and "--plan" in why,
                      f"{label} is refused, naming --plan",
                      detail if refused else why[:120])
        # THE POSITIVE CONTROL. Without it all three above are satisfied by a seal_plan
        # that refuses everything, and the cost of that lands on the one run that cannot
        # be repeated: the operator loses the session to a guard, not to a typo.
        try:
            ok_seal = ls.seal_plan(good)
            accepted = ok_seal.steps == 2 and len(ok_seal.sha256) == 64
        except BaseException:                          # noqa: BLE001 -- red, never fatal
            accepted = False
        LEDGER.ok(accepted,
                  "CONTROL: a VALID plan is accepted and sealed",
                  "a guard that refuses everything protects nothing, because the driver "
                  "then never runs")

        # And through run(), where the refusal has to land BEFORE preflight -- the same
        # shape as the --mode gate above. Anything that is not a LiveError means the run
        # reached preflight with the plan unread, which is a gate in the wrong place.
        def try_run(plan_arg):
            return refusal(ls.run, "capture", "x", "3.65.1.1", {6112}, 20,
                           confirm=True, mode="base", plan=plan_arg)

        refused, why = try_run(missing)
        LEDGER.ok(refused and "--plan" in why,
                  "run() refuses a bad --plan before preflight touches the account",
                  "a malformed plan costs a retype here and an unrepeatable session "
                  "anywhere later")
        # THE EMPTY STRING, THROUGH run(), which is where the defect actually lived: the
        # refusal above proves seal_plan handles it, and the old guard
        # `seal = seal_plan(plan) if plan else None` never called seal_plan at all.
        refused, why = try_run("")
        LEDGER.ok(refused and "--plan" in why,
                  "run() refuses --plan \"\" instead of silently running UNLABELLED",
                  "`--plan \"$PLAN\"` with the variable unset is the by-accident case the "
                  "spec forbids, and the manifest then stated the false reason \"no "
                  "--plan was passed\" about an operator who had passed one")
        # THE POSITIVE CONTROLS, and there are two because there are two ways to be past
        # this gate: a VALID plan, and NO plan at all. Both must reach preflight and fail
        # there on the fake exe, or the refusals above are satisfied by a run() that
        # refuses everything -- a wall rather than a check, paid for by the one session
        # that cannot be repeated. The second one is the whole reason --plan is optional.
        for label, arg, detail in (
                ("a VALID --plan", good,
                 "otherwise the refusals above are satisfied by a run() that refuses "
                 "every plan"),
                ("no --plan at all", None,
                 "refusing here would convert 'the operator forgot to pre-register' "
                 "into 'the one authorized live session did not happen'")):
            refused, why = try_run(arg)
            LEDGER.ok(not (refused and "--plan" in why),
                      f"CONTROL: {label} passes the gate and fails later on the fake exe",
                      detail)

    # ---- 5d. absent WARNS and is recorded; present does NOT warn ----------------
    print("\n5d. the absence of a plan is loud and explicit, and its presence is quiet")
    with tempfile.TemporaryDirectory() as tmp:
        outdir = os.path.join(tmp, "20260813T120000")
        os.makedirs(outdir)
        seal = ls.seal_plan(write_plan(os.path.join(tmp, "plan.txt")))
        quiet = ls.marks_instructions(seal, outdir, pid=4242)
        loud = ls.marks_instructions(None, outdir)
        LEDGER.ok(any(ls.MARKS_BANNER in ln for ln in loud)
                  and any("--plan" in ln for ln in loud),
                  "a run with NO plan prints the banner and names --plan")
        LEDGER.ok(not any(ls.MARKS_BANNER in ln for ln in quiet),
                  "and a run WITH one does not warn at all",
                  "test_harness.py's --enemy lesson: a warning that fires either way is "
                  "noise, so both branches have to be checked")
        joined = "\n".join(quiet)
        LEDGER.ok("marks.py" in joined and os.path.abspath(outdir) in joined
                  and seal.path in joined and "--pid 4242" in joined
                  and seal.sha256[:16] in joined,
                  "the printed command names marks.py, the RESOLVED capture dir, the "
                  "plan, the pid and the sealed hash",
                  "the operator types it into a DIFFERENT shell while a client is coming "
                  "up, so a relative path or an unresolved dir is a command that fails")
        LEDGER.ok(not any("marks.py" in ln and "--capture" in ln for ln in loud),
                  "the unsealed branch offers NO runnable marks.py command",
                  "a plan written after the client launched is a label, not a "
                  "pre-registration, and printing the command would invite exactly that")
        absent, present = ls.plan_manifest(None), ls.plan_manifest(seal)
        LEDGER.ok(absent["plan_sealed"] is False and "plan_sha256" in absent
                  and absent["plan_sha256"] is None and absent.get("plan_unsealed_reason"),
                  "the manifest records the ABSENCE explicitly, keys and all",
                  "an omitted key and a false one read the same only if nothing "
                  "distinguishes them: no key at all means a manifest older than --plan")
        # SEVEN, not five, and the two that were added are the ones that used to be
        # branch-specific: `plan_sealed_utc` appeared only when sealed and
        # `plan_unsealed_reason` only when not, so a consumer reading either by name got a
        # KeyError on the other half of the corpus. That is this section's own rule --
        # an omitted key is not a null one -- applied one level down.
        common = {"plan_sealed", "plan", "plan_path", "plan_sha256", "plan_steps",
                  "plan_sealed_utc", "plan_unsealed_reason"}
        LEDGER.ok(set(absent) == common and set(present) == common,
                  "and both branches carry the same seven keys under the same names",
                  "so a consumer reads one shape, and `plan_sealed` is the discriminator")
        # `.get()` throughout, because the version that indexed died with a KeyError on the
        # very sabotage this check exists to catch, printing no verdict at all.
        LEDGER.ok(present.get("plan_unsealed_reason", "MISSING") is None
                  and absent.get("plan_sealed_utc", "MISSING") is None
                  and present.get("plan_sealed_utc") and absent.get("plan_unsealed_reason"),
                  "and each branch's inapplicable key is null rather than missing",
                  "a key present-and-null says 'this driver considered it'; a key absent "
                  "says 'this driver predates it', and they are different facts")

    # ---- 5e. the second witness: two seals of one file, from two processes ------
    print("\n5e. the driver's pre-launch seal against marks.py's own, three-valued")
    with tempfile.TemporaryDirectory() as tmp:
        def capture(name, plan_text=PLAN_TEXT, edit=None, manifest="manifest.json",
                    seal_it=True, marker=True):
            """Build a capture directory the way the two tools really write one."""
            d = os.path.join(tmp, name)
            os.makedirs(d)
            plan = write_plan(os.path.join(d, "plan.txt"), plan_text)
            seal = ls.seal_plan(plan) if seal_it else None
            if edit:
                write_plan(plan, edit)            # the operator edits it AFTER the seal
            if manifest:
                with open(os.path.join(d, manifest), "w", encoding="utf-8") as fh:
                    json.dump({"stamp": name, **ls.plan_manifest(seal)}, fh)
            if marker:
                # marks.py's own read, in its own writer -- never a hand-rolled record,
                # because two writers of one format is how they drift.
                marks.open_marks(d, plan, wire_path="").close()
            return d

        agree = capture("agree")
        v, why = ls.compare_plan_seals(agree)
        LEDGER.ok(v == ls.SEAL_AGREE and "manifest.json" in why,
                  "two independent seals of an untouched plan AGREE, per manifest.json",
                  why[:100])
        edited = capture("edited", edit=PLAN_EDITED)
        v, why = ls.compare_plan_seals(edited)
        LEDGER.ok(v == ls.SEAL_DISAGREE and "DIFFERENT BYTES" in why,
                  "a plan edited between the launch and the marker is caught, and only "
                  "this pre-launch hash can catch it",
                  "marks.bind() compares the marker's hash to the file as it stands NOW, "
                  "and after this edit both of those are the edited version")
        # THE MESSAGE MUST NAME BOTH CAUSES, and this is the second one: the operator
        # typed a DIFFERENT file into the second shell. The first version's headline was
        # "THE PLAN CHANGED BETWEEN THE TWO READS", asserted in capitals about two files
        # that were both untouched and both still on disk -- a confident wrong diagnosis,
        # which is worse than none because it sends the reader looking for an edit.
        swap = os.path.join(tmp, "swap")
        os.makedirs(swap)
        plan_a = write_plan(os.path.join(swap, "plan_A.txt"))
        plan_b = write_plan(os.path.join(swap, "plan_B.txt"), PLAN_EDITED)
        with open(os.path.join(swap, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"stamp": "swap", **ls.plan_manifest(ls.seal_plan(plan_a))}, fh)
        marks.open_marks(swap, plan_b, wire_path="").close()
        v, why = ls.compare_plan_seals(swap)
        LEDGER.ok(v == ls.SEAL_DISAGREE and "EDITED" in why and "DIFFERENT file" in why
                  and "plan_A.txt" in why and "plan_B.txt" in why,
                  "a marker pointed at a DIFFERENT file is caught, and the message names "
                  "BOTH causes and BOTH plans",
                  "the artifact cannot tell an edit from a swap on its own, so asserting "
                  "one of the two is a diagnosis the evidence does not support")
        v, why = ls.compare_plan_seals(capture("nomarker", marker=False))
        LEDGER.ok(v == ls.SEAL_UNCHECKED and "never run" in why,
                  "no plan_marks.jsonl is UNCHECKED, never agree",
                  "the operator may legitimately not have marked; folding that into a "
                  "pass makes the comparison green whenever it is absent")
        v, why = ls.compare_plan_seals(capture("noplan", seal_it=False, marker=False))
        LEDGER.ok(v == ls.SEAL_UNCHECKED and "plan_sealed false" in why,
                  "a run driven without --plan is UNCHECKED and says which of the two "
                  "reasons it is")
        old = os.path.join(tmp, "prefeature")
        os.makedirs(old)
        with open(os.path.join(old, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"stamp": "20260807T143055", "keys_tapped": 6}, fh)
        v, why = ls.compare_plan_seals(old)
        LEDGER.ok(v == ls.SEAL_UNCHECKED and "before --plan existed" in why,
                  "and a manifest predating the flag is named as that, not as a false",
                  "unsealed by construction and unsealed by choice are different facts "
                  "about a capture")
        # THE THIRD REASON, which the two above would otherwise swallow. An UNREADABLE
        # manifest is not a manifest older than --plan, and reporting it as one is a
        # confident wrong statement about provenance -- the same defect as a DISAGREE
        # asserting one cause of two. This is the case the first draft of `seal_records`
        # got wrong on its way to fixing something else.
        torn = os.path.join(tmp, "torn")
        os.makedirs(torn)
        with open(os.path.join(torn, "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write('{"stamp": "20260813T1200')          # the run died mid-write
        v, why = ls.compare_plan_seals(torn)
        LEDGER.ok(v == ls.SEAL_UNCHECKED and "cannot be read as JSON" in why
                  and "before --plan existed" not in why,
                  "and a TRUNCATED manifest is named as unreadable, not as pre-flag",
                  why[:100])
        # The fallback that makes write_seal_file worth having: a run killed before its
        # manifest still answers.
        died = capture("died", manifest=None)
        ls.write_seal_file(died, ls.seal_plan(os.path.join(died, "plan.txt")))
        v, why = ls.compare_plan_seals(died)
        LEDGER.ok(v == ls.SEAL_AGREE and "plan_seal.json" in why,
                  "a capture with no manifest still compares, and NAMES plan_seal.json "
                  "as where it read the seal",
                  "without the source in the message this check passes against a reader "
                  "that quietly found a manifest, so the fallback would be untested")
        # Matching bytes, disagreeing counts. This cannot arise from a real pair, which
        # is the point: it is the branch that separates "the file moved" from "the two
        # parsers disagree", and only a hand-edited marks_meta can reach it.
        skew = capture("stepskew")
        mpath = os.path.join(skew, marks.PLAN_MARKS_NAME)
        lines = open(mpath, encoding="utf-8").read().splitlines()
        rec = json.loads(lines[0])
        rec["steps"] = 99
        lines[0] = json.dumps(rec)
        open(mpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        v, why = ls.compare_plan_seals(skew)
        LEDGER.ok(v == ls.SEAL_DISAGREE and "parsers" in why,
                  "matching bytes with disagreeing step counts is a DISAGREE that names "
                  "the parsers, not the file")
        # THE DRIVER AGAINST ITSELF. manifest.json and plan_seal.json are rendered from
        # ONE PlanSeal, so a disagreement is a fact about the DRIVER. This is the artifact
        # the `sha256(seal.path)` sabotage leaves behind -- it was on disk in two files
        # for the whole of 2026-08-13 with nothing reading the second one.
        conflict = capture("conflict")
        man_path = os.path.join(conflict, "manifest.json")
        rec = json.load(open(man_path, encoding="utf-8"))
        ls.write_seal_file(conflict, ls.seal_plan(os.path.join(conflict, "plan.txt")))
        rec["plan_sha256"] = "f" * 64          # the manifest re-hashed a moved plan
        json.dump(rec, open(man_path, "w", encoding="utf-8"))
        flag, cwhy = ls.internal_seal_conflict(conflict)
        v, why = ls.compare_plan_seals(conflict)
        LEDGER.ok(flag and v == ls.SEAL_DISAGREE and "CONTRADICTS ITSELF" in why
                  and "plan_seal.json" in why and "manifest.json" in why,
                  "a manifest disagreeing with this run's OWN plan_seal.json is a "
                  "DISAGREE naming both files",
                  cwhy[:90])
        # AND ITS CONTROL, which is what stops it being 'report a conflict always': the
        # agreeing capture above has both files and must stay quiet. Checked through
        # internal_seal_conflict rather than through the verdict, because the verdict
        # would be AGREE either way once the marker matches.
        ls.write_seal_file(agree, ls.seal_plan(os.path.join(agree, "plan.txt")))
        flag2, why2 = ls.internal_seal_conflict(agree)
        LEDGER.ok(not flag2 and "agree" in why2 and ls.compare_plan_seals(agree)[0]
                  == ls.SEAL_AGREE,
                  "CONTROL: two seal records written from one PlanSeal do NOT conflict",
                  "both files are present here, so the check above is not passing on "
                  "absence")

    # ---- 5f. the verdict is RECORDED, not printed, and the manifest edit is narrow ----
    print("\n5f. the second witness reaches an artifact, and update_manifest is surgical")
    man_keys, man_call = manifest_literal(src)
    LEDGER.ok("plan_seals" in man_keys and "plan_seals_why" in man_keys,
              "run()'s manifest literal carries the seal verdict as a FIELD",
              f"{sorted(k for k in man_keys if k.startswith('plan'))} -- until "
              f"2026-08-13 compare_plan_seals had exactly one call site, reassemble(), "
              f"so a live run that completed normally never spent the witness at all")
    LEDGER.ok(man_call is not None and man_call < min(seal_order(src)["manifest_lines"]),
              "and it is computed one statement ABOVE the literal, from the directory",
              f"compare_plan_seals at line {man_call}: it reads plan_seal.json and "
              f"marks_meta and never the plan file, which is what lets it sit after the "
              f"launch at all -- see §5a's argument check")
    LEDGER.ok("update_manifest" in calls_in(src, "reassemble")
              and "compare_plan_seals" in calls_in(src, "reassemble"),
              "and reassemble() RECOMPUTES it and writes it back",
              "this is the one place the answer can change after the run -- a marker "
              "started late, or a capture assembled months later -- and printing it "
              "left the verdict in console scrollback where no consumer can reach it")
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "cap")
        os.makedirs(d)
        original = {"stamp": "20260813T120000", "keys_tapped": 6,
                    "report": {"decrypted": 2, "total": 3}, "plan_seals": "unchecked"}
        with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(original, fh, indent=1)
        wrote = ls.update_manifest(d, {"plan_seals": "agree", "plan_seals_why": "x"})
        after = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
        LEDGER.ok(wrote and after["plan_seals"] == "agree" and after["plan_seals_why"] == "x",
                  "update_manifest merges the two fields it is given")
        LEDGER.ok(all(after[k] == v for k, v in original.items() if k != "plan_seals")
                  and set(after) == set(original) | {"plan_seals_why"},
                  "and EVERY other key survives, value for value",
                  "this is the only code in the project that edits the primary artifact "
                  "of a run that cannot be repeated, so 'it used dict.update' is not the "
                  "check -- the surviving values are")
        LEDGER.ok(not ls.update_manifest(os.path.join(tmp, "nothing"), {"plan_seals": "x"})
                  and not os.path.exists(os.path.join(tmp, "nothing", "manifest.json")),
                  "it REFUSES to create a manifest where there is none",
                  "a capture with no manifest is a run that died before assembly, and "
                  "plan_seal.json is that run's record -- inventing one here would "
                  "fabricate a manifest for a session that never finished")
        broken = os.path.join(tmp, "broken")
        os.makedirs(broken)
        with open(os.path.join(broken, "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json at all")
        LEDGER.ok(not ls.update_manifest(broken, {"plan_seals": "x"})
                  and open(os.path.join(broken, "manifest.json"),
                           encoding="utf-8").read() == "{not json at all",
                  "and leaves an unparseable manifest byte-for-byte alone",
                  "truncating a manifest we could not read would destroy the only "
                  "record of the run to add one field to it")

    # ---- 5g. the ordering as the RUNTIME saw it, not as two line numbers -------
    print("\n5g. run() really does seal before it spawns anything, observed")
    with tempfile.TemporaryDirectory() as tmp:
        plan = write_plan(os.path.join(tmp, "plan.txt"))
        got = runtime_order(ls, tmp, plan)
        LEDGER.ok(got[:3] == ["SEAL", "SEAL_FILE", "POPEN"],
                  "OBSERVED: seal, then the seal on disk, then the first spawn",
                  f"{got} -- §5a compares two line numbers; this is a difference "
                  f"between two live answers, and it is what catches a seal that is "
                  f"textually early and executed late")
        # THE FOUR SABOTAGES, and these have to EXECUTE, so each is imported as its own
        # module rather than merely parsed. Each must move the LOG.
        sab_defer = src.replace(
            seal_stmt,
            "    def _seal_when_ready():\n"
            "        return seal_plan(plan) if plan is not None else None\n"
            "    seal = None\n", 1).replace(
            "        procs.append(client)\n",
            "        procs.append(client)\n        seal = _seal_when_ready()\n", 1)
        sab_noseal_file = src.replace("    write_seal_file(outdir, seal)\n", "", 1)
        LEDGER.ok(len({src, sab_defer, sab_noseal_file, sab_early}) == 4,
                  "CONTROL: the runtime sabotage edits applied to the live source")
        deferred = runtime_order(load_sabotage(sab_defer, "defer", tmp), tmp, plan)
        LEDGER.ok("SEAL" not in deferred and "POPEN" in deferred,
                  "SABOTAGE: a seal deferred into a nested function never runs before "
                  "the spawn, and the runtime log says so",
                  f"{deferred} -- §5a passes this one COMPLETELY: `ast.walk` descends "
                  f"into the nested def, so the seal_plan call keeps its early line "
                  f"number while executing after the launch")
        LEDGER.ok(all(seal_claims(sab_defer)[k] for k in
                      ("seal_before_launch", "seal_before_first_spawn",
                       "no_hash_after_launch", "no_plan_reread_after_launch",
                       "one_seal", "launch_found")),
                  "and §5a is GREEN on that same source, which is why §5g exists",
                  "measured rather than asserted: the syntax tree cannot see a call "
                  "whose line number is early and whose execution is late")
        nofile = runtime_order(load_sabotage(sab_noseal_file, "nofile", tmp), tmp, plan)
        LEDGER.ok("SEAL" in nofile and "SEAL_FILE" not in nofile,
                  "SABOTAGE: deleting write_seal_file's one call site is visible at "
                  "runtime",
                  f"{nofile} -- that deletion passed 75 of 75, because §5b calls "
                  f"write_seal_file directly and §5e's died fixture builds "
                  f"plan_seal.json by hand, so neither noticed run() had stopped")
        relaunch = runtime_order(load_sabotage(sab_early, "early", tmp), tmp, plan)
        LEDGER.ok(relaunch and relaunch[0] == "POPEN",
                  "SABOTAGE: a spawn above the seal is the FIRST thing in the log",
                  f"{relaunch} -- the client is up before anything has been sealed")

    # ---- 12. the launch build must be the build the service is serving ---------
    print("\n12. the build guard: a stale live build is refused BEFORE the login")
    real_service = ls.service_build

    def fake_service(n, why="fixture"):
        return lambda: (n, why)

    class FakeImage:
        """buildid.of_image for a path we never have to own on disk."""

        def __init__(self, table):
            self.table = table

        def __call__(self, path):
            for frag, n in self.table.items():
                if frag in path.replace("\\", "/"):
                    return n, "fixture"
            return None, "fixture: unknown image"

    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(ls.__file__)),
                                     "..", "clientscan"))
    import buildid
    real_of_image = buildid.of_image
    try:
        buildid.of_image = FakeImage({"CURRENT/Gw.exe": 38833, "STALE/Gw.exe": 38797})

        ls.service_build = fake_service(38833)
        ok = ls.check_build_matches_service("C:/x/run-live/CURRENT/Gw.exe")
        LEDGER.ok(ok["checked"] and ok["launch_build"] == 38833,
                  "the matching build is ACCEPTED",
                  "the positive control -- a guard that refuses everything "
                  "protects nothing")

        try:
            ls.check_build_matches_service("C:/x/run-live/STALE/Gw.exe")
            refused, msg = False, ""
        except ls.LiveError as exc:
            refused, msg = True, str(exc)
        LEDGER.ok(refused and "38797" in msg and "38833" in msg,
                  "a build OLDER than the service is REFUSED, naming both numbers",
                  "the updater is LIVE on run-live builds by design, so a stale "
                  "exe updates itself and loses the key-tap cave -- after the "
                  "login, which is the authorized session gone")

        # The refusal must NAME the build that would work. A refusal that only
        # says no leaves the operator where the hedge did.
        real_scan = ls._run_live_builds
        try:
            ls._run_live_builds = lambda: {38833: ["2026-08-13_64fae3b1369b"]}
            try:
                ls.check_build_matches_service("C:/x/run-live/STALE/Gw.exe")
                named = ""
            except ls.LiveError as exc:
                named = str(exc)
            LEDGER.ok("2026-08-13_64fae3b1369b" in named,
                      "and the refusal NAMES the staged build that would work",
                      "a refusal that only says no leaves the operator exactly "
                      "where the unmeasured hedge did")
            ls._run_live_builds = lambda: {}
            try:
                ls.check_build_matches_service("C:/x/run-live/STALE/Gw.exe")
                nostage = ""
            except ls.LiveError as exc:
                nostage = str(exc)
            LEDGER.ok("make_custom_client.py" in nostage,
                      "and with NO staged build at that number it prints the "
                      "rebuild command instead")
        finally:
            ls._run_live_builds = real_scan

        # The owner's install is not on every machine. Absent must SKIP loudly,
        # never pass quietly -- unchecked is not the same as checked and fine.
        ls.service_build = fake_service(None, "no install at C:\\gw\\Gw.exe")
        skipped = ls.check_build_matches_service("C:/x/run-live/CURRENT/Gw.exe")
        LEDGER.ok(skipped["checked"] is False and skipped["launch_build"] == 38833,
                  "with no owner install to compare against, the check SKIPS and "
                  "says so rather than passing",
                  "checks.py's own rule: a section that cannot run is printed, "
                  "never silent")

        # An unreadable launch binary is a refusal, not a shrug.
        ls.service_build = fake_service(38833)
        try:
            ls.check_build_matches_service("C:/x/run-live/MYSTERY/Gw.exe")
            refused_unknown = False
        except ls.LiveError:
            refused_unknown = True
        LEDGER.ok(refused_unknown,
                  "a launch binary whose build cannot be read is REFUSED",
                  "an unidentified binary at the real service is the one thing "
                  "worse than the wrong identified one")
    finally:
        buildid.of_image = real_of_image
        ls.service_build = real_service

    # ---------------------------------------------------------------- 13. the
    # full-stream tie-break. `key_fits` reads TWO BYTES, and on capture
    # 20260817T231139 two leftover keys each spelled a plausible opcode on each of
    # two leftover connections -- a clean 2x2 ambiguity that refused the largest
    # connection in the corpus (122 KB, an entire Isle of the Nameless walk). The
    # tie-break asks whether the WHOLE stream frames to its final byte, which a
    # wrong ARC4 key cannot fake. These checks drive the real helper.
    from codec import Codec as _Codec
    codec = _Codec()

    def stream_for(msgs):
        """A GAME_SMSG byte stream built by the REAL encoder, so it frames exactly."""
        return b"".join(codec.encode("GAME_SMSG", op, vals) for op, vals in msgs)

    good_key = bytes([0x11]) * 20
    other_key = bytes([0x22]) * 20
    plain = stream_for([(0x0115, [277, 7]),
                        (0x0115, [277, 8]),
                        (0x0115, [277, 9])])
    LEDGER.ok(len(plain) > 0,
              "the tie-break fixture encodes through the real codec",
              str(len(plain)) + " bytes")

    cipher = ls.ARC4(good_key).crypt(plain)      # what the wire would carry

    LEDGER.ok(ls._frames_completely(cipher, good_key),
              "the RIGHT key frames the whole stream to its final byte",
              "the positive control: without it the tie-break could be vacuously "
              "false and still look like it works, by refusing everything")
    LEDGER.ok(not ls._frames_completely(cipher, other_key),
              "a WRONG key does not frame the whole stream",
              "ARC4 is wrong for every byte after the first, and noise does not "
              "walk message-by-message onto an exact landing")
    LEDGER.ok(not ls._frames_completely(cipher[:len(cipher) - 3], good_key),
              "even the RIGHT key fails when the stream does not END on a boundary",
              "consumed == len(plain) is the half that catches a truncated or "
              "gap-holed capture rather than a wrong key")
    LEDGER.ok(not ls._frames_completely(b"", good_key),
              "an empty stream is not complete",
              "consumed > 0, or a zero-byte connection would look decidable")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
