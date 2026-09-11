"""Drive one authorized live-capture session, and turn its wire bytes into an artifact.

    (ELEVATED)  python toolkit/harness/livesession.py --account capture \
                    --exe <vault>/run-live/<build>/Gw.exe --confirm

This is the R0b driver: it ties together the parts each proven on their own -- the launch
gate (`cage.assert_launch_safe`, stock->live), the account selector (`accounts.for_automation`,
refuses the primary), the key-tap (`keytap.py` reads what the code cave stashed), the
off-wire capture (`wirecapture.py`), the decryptor (`replay.py`/`gwcrypto`), the origin
stamp (`origin.py`), and the scrub (`scrub_captures.py`). It launches the stock-DH live
client at the real service, sniffs the ciphertext, reads the session key out of the client,
and assembles a decrypted capture stamped `origin: live` and byte-replayable from disk.

TWO HALVES, and only one is testable without a live account:

  * ASSEMBLE (offline, pure) -- reassembled wire streams + the tapped keys -> decrypted
    captures. The DH handshake is plaintext on the wire (ARC4 starts only after the key is
    derived), so this splits VERSION/CLIENT_SEED/SERVER_SEED off the front of each
    direction and decrypts the rest. Verified against real captured bytes in
    test_livesession.py.
  * RUN (live) -- launch, sniff, tap, hold, stop, assemble, scrub. Needs WinDivert, an
    elevated shell, and the secondary account, and it never runs except behind --confirm.

TWO WAYS A LIVE SESSION IS NOT THE LOOPBACK DRY-RUN, both of which shape the code below:

  1. **Several connections, unknown addresses.** Login is three stages (PLAN §1.6), and two
     of them are capturable: the auth channel, then the game server on a DIFFERENT
     address, both on 6112 (see LIVE_PORTS for why Stage A is not). Nobody knows those
     addresses until the client connects -- Stage C's arrives inside the encrypted
     AUTH_SMSG_GAME_SERVER_INFO -- and by then the plaintext handshake has already crossed
     the wire. So the sniff filters by PORT, on any host, and starts before the launch.
     Each connection is reassembled on its own sequence space
     (wirecapture.load_connections); merging them would interleave two sequence spaces into
     a byte string that looks like a stream and decrypts to nothing.
  2. **Several keys.** Each DH-keyed channel derives its own master_secret through the same
     code, so the single tap slot is OVERWRITTEN at every handshake. The driver keeps a
     keyring -- every distinct value the slot ever held -- and assemble_live pairs keys to
     connections by a criterion the artifact can refute (FIRST_C2S_OPCODE).

AND THE DRIVER DOES NOT PLAY THE GAME. No scripted keystrokes, no clicks. See run().

THE PRE-REGISTRATION SEAL, and WHY IT IS TAKEN WHERE IT IS. `--plan` names the
operator-mark plan that `toolkit/harness/marks.py` will read in a SECOND SHELL (F9
advance / F10 repeat / F11 note). The plan IS the pre-registered prediction, so its
sha256 belongs in `manifest.json` -- studies/reconstruction/FINDINGS.md §10.5.1 -- and
the ONE thing that makes that hash worth anything is WHEN it was taken. `manifest.json`
is written at the END of the run, after assembly; hashing there would seal whatever the
plan said AFTERWARDS, so an operator who edited it mid-session would get a manifest
certifying the edited prediction and the seal would be worse than nothing (it would look
like evidence). So `seal_plan` runs at the TOP of `run()` -- before `preflight`, before
the account is resolved, before the sniffer subprocess, and long before
`subprocess.Popen([exe] + args)` -- and the manifest is written from that CARRIED value.
`test_livesession.py` asks the syntax tree about that ordering, because "the hash is
before the launch" and "the hash is after it" are invisible to a grep and the ordering is
the whole feature.

`--plan` IS OPTIONAL, AND THAT IS A JUDGEMENT, not an oversight. `--mode` is refused when
absent because a wrong or missing mode POISONS the data unrecoverably -- every health
number in the capture becomes base-or-base*0.8 forever. A missing plan poisons nothing:
it produces an UNLABELLED capture, which is exactly what every live capture before
2026-08-13 is, and those are the corpus. Refusing would convert "the operator forgot to
pre-register" into "the one authorized live session did not happen", which is the more
expensive error. So this follows D9(a)'s shape instead: make the drop VISIBLE rather than
refused -- a loud console block before the operator logs in, and `"plan_sealed": false`
written into the manifest EXPLICITLY. An omitted key and a false one read the same only
if nothing distinguishes them, and here they are different facts: a manifest with no
`plan_sealed` key at all predates this flag, while `plan_sealed: false` is an operator who
had it and did not use it.

THE SECOND WITNESS IS FREE, AND IT IS NOW SPENT ON THE LIVE PATH. `marks.py` writes its
OWN `plan_sha256` into `marks_meta`, from its own read of the file, in a different process
at a later moment. Two independent seals of one file is a claim the artifact can refute --
if they disagree, the plan changed between the driver's read and the marker's, or the
operator typed a different file into the second shell. `marks.bind()` cannot see either:
it compares `marks_meta` against the plan file AS IT IS NOW, so an edit made before the
marker started is invisible to both of its reads. `compare_plan_seals()` below is the
missing leg, three-valued for the same reason `origin.py` is -- "no marker was run" is not
"the seals agree".

This module argued for a whole day that `run()` could not make that comparison, on the
grounds that `plan_marks.jsonl` might not exist when the manifest is written and a check
that skips in every real run cannot fail. Two rounds of adversarial review took that apart
on 2026-08-13 and they were right twice over. It is not a check, it is a RECORDED
THREE-VALUED FIELD, and `UNCHECKED` is a value rather than a skip. And the timing does not
bite: the driver prints `--pid <client.pid>`, `marks.run` ends on that pid, and the
manifest is written after teardown, pruning, assembly and the scrub. Meanwhile the verdict
was reachable only from `--assemble`, where it was PRINTED and reached no artifact -- so an
operator could seal `plan_A.txt`, mark against `plan_B.txt`, and get a manifest reading
`plan_sealed: true, plan_A.txt` with nothing anywhere contradicting it. `run()` records the
verdict now and `reassemble()` recomputes and rewrites it.

AND THE DRIVER IS CHECKED AGAINST ITSELF. `manifest.json` and `plan_seal.json` are
rendered from ONE `PlanSeal`, so they cannot legitimately disagree; `internal_seal_conflict`
says so out loud. That exists because the sabotage that beat the first round of checks --
a manifest re-hashing the plan at the end via this module's own `sha256()` helper -- left
its own evidence in the capture directory, in two files, with nothing reading the second.

WHAT IS STILL MISSING, so the next session does not have to rediscover it: `marks.py` is
handed the capture directory that already holds `plan_seal.json` and never opens it. A
refusal THERE -- the marker declining to start against a capture whose sealed sha does not
match the plan it was given -- costs the operator one retype before they log in, where
everything here can only report the mismatch afterwards. That is a change to `marks.py`
and is not in this file's remit.

BEHAVIOURAL GUARDS, the controls PLAN §6.1 says actually protect an account: exactly one
live client (a second is refused), a session-length ceiling, and an explicit --confirm --
because what closes accounts is a traffic pattern no person produces, and the cheap
structural parts of "human cadence, one client" are worth enforcing even though the
judgement itself stays with the operator.

standard library only (the WinDivert dependency lives in wirecapture.py).
"""
import argparse
import collections
import hashlib
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
import accounts  # noqa: E402
import marks  # noqa: E402
import origin  # noqa: E402
import vaultpath  # noqa: E402
import wirecapture as wc  # noqa: E402
# BOTH OF THESE STAY, and neither is used by this file's own code any more: `ARC4`'s and
# `Codec`'s only callers -- `decrypt_stream` and `_frames_completely` -- moved to
# `wiresplit.py`. They are still read off THIS module by name:
# toolkit/harness/test_livesession.py:1589 builds its key-fit fixture with
# `ls.ARC4(good_key).crypt(plain)`, so an "unused import" tidy here reddens section 5h.
# The `codec` line's own trailing note named the tie-break that used to sit below it; that
# reader is `wiresplit._frames_completely` now, and the note is corrected to say so.
from gwcrypto import ARC4  # noqa: F401,E402 -- read as `ls.ARC4` by test_livesession.py
from codec import Codec  # noqa: F401,E402  -- the tie-break, wiresplit._frames_completely

# The handshake framing constants, the splitters, the key tie-break and the whole offline
# assembly moved to `wiresplit.py`, so that `toolkit/authsrv/cmsgstream.py` -- imported by
# nine analysis modules -- can reach `split_c2s`/`split_s2c`/`decrypt_stream` without
# dragging the packet-capture backend, `accounts`, `marks` and the live orchestration in
# behind them. The re-export sits HERE, at the site the VERSION constants were defined,
# because these names are read off THIS module: `ls.<name>` throughout
# toolkit/harness/test_livesession.py, `ls.split_c2s`/`ls.decrypt_stream`/`ls.assemble` in
# toolkit/harness/dryrun_keycapture.py, and `prune_wire`/`assemble_live` as bare globals in
# `run()` and `reassemble()` below.
from wiresplit import (  # noqa: F401,E402
    AUTH_VERSION_HEADER, GAME_VERSION_HEADER, VERSION_BODY_LEN, CLIENT_SEED_HEADER,
    SERVER_SEED_HEADER, VERSION_LEN, CLIENT_SEED_LEN, SERVER_SEED_LEN, VERSION_CHANNEL,
    CMSG_DIRECTION_BIT, MAX_CATALOG_OPCODE,
    split_c2s, split_s2c, decrypt_stream, assemble, key_fits, _frames_completely,
    channel_of_stream, build_for, assemble_live, prune_wire,
)

# The ports a LIVE session may put capturable bytes on.
#
# THIS WAS `(6112,)` AND IT COST A SESSION. Runs one and two captured fine on 6112, so the
# third was run with the same narrow filter; it recorded ZERO bytes across ten minutes
# while nine keys were tapped, and a WinDivert smoke test on port 443 immediately
# afterwards returned recv=238 parsed=238 recorded=137 -- so the driver, the parser and the
# direction logic were all healthy and the filter was simply not where the traffic was.
# The difference from runs one and two is that the client now has its updater enabled, so
# it streams content; the key tap fires on every DH-keyed MsgConn connection, and nothing
# says those all live on 6112.
#
# THE COSTS ARE WILDLY ASYMMETRIC, which is the whole argument. A port in this list that
# carries nothing costs a few bytes of filter. A port MISSING from it costs an authorized
# live session, unrecoverably, because the ciphertext is never recorded and the keys that
# were tapped decrypt nothing. So the list is now GW's whole known port range, taken from
# this repo's own probe design (studies/handshake/PLAN.md: the probe binds 6601, 6112,
# 6600, 6113, 80, 443, 6111 and 6114 precisely because those are the ports the client might
# dial), minus 80/443 -- Stage A is TLS to account.arena.net under a key we do not hold,
# and sniffing 443 would record the machine's entire web traffic to no purpose.
#
# The previous comment argued 6601 should be excluded because it is only used when
# `-portal` is SET. That reasoning is still correct and is now irrelevant: being right
# about a port that carries nothing saves nothing, and being wrong about one loses a
# session. `_hold` samples the client's own connections and the capture's watchdog reports
# per-stage counters, so what actually carried traffic is now MEASURED per run rather than
# assumed here.
#
# AND 80, WHICH IS WHERE IT ACTUALLY WAS. Run four (2026-08-07 14:17) tapped six keys and
# captured nothing on the whole 6111-6601 range, while the driver's new connection sampler
# named the client's real peers: `52.3.40.244:80` and `52.55.104.238:80`. Those are the
# SAME two ArenaNet addresses that carried 6112 in runs one and two -- same servers,
# different port. Guild Wars can run its channels over 80 (the firewall-friendly path), and
# on this machine it now does. That is the whole reason three sessions recorded zero bytes.
#
# 443 is still excluded: the portal is TLS under a key we do not hold, and 443 is where a
# machine's other traffic lives. Port 80 is comparatively quiet now that the web is HTTPS,
# and `prune_wire` drops every captured connection that carries no GW handshake, so
# unrelated HTTP does not survive into the artifact.
LIVE_PORTS = (80, 6111, 6112, 6113, 6114, 6600, 6601)

# `VERSION_CHANNEL`, `CMSG_DIRECTION_BIT` and `MAX_CATALOG_OPCODE` moved to `wiresplit.py`
# with the 534-capture measurement that earned the direction bit; re-exported above.


# Both refusal classes moved to `liveerror.py` -- a module that imports nothing, so a leaf
# which only has to say "refused" does not drag the packet-capture backend in with it. The
# re-export sits HERE, at the site they were defined, because they are read as
# `ls.LiveError` / `ls.SplitError` by toolkit/harness/test_livesession.py and
# toolkit/harness/dryrun_keycapture.py, and as bare globals throughout this file.
from liveerror import LiveError, SplitError  # noqa: F401,E402


# The offline assembly -- `split_c2s`, `split_s2c`, `decrypt_stream`, `assemble`,
# `key_fits`, `_frames_completely`, `channel_of_stream`, `build_for` and `assemble_live` --
# moved to `wiresplit.py` and is re-exported above. `run()` and `reassemble()` below call
# `assemble_live` as a bare global.


# The whole pre-registration seal -- `PlanSeal`, `seal_plan`, `plan_manifest`,
# `write_seal_file`, `marks_instructions` and the second-witness comparison -- moved to
# `planseal.py`, a module that reads the operator's plan file and a capture directory and
# nothing else, so the seal no longer has to be reached through a driver that loads the
# packet-capture backend, the codec, ARC4, `accounts`, `origin` and `vaultpath`. The
# re-export sits HERE, at the site the seal was defined, because these names are read off
# THIS module: `ls.seal_plan`, `ls.plan_manifest`, `ls.write_seal_file`,
# `ls.marks_instructions`, `ls.MARKS_BANNER`, `ls.compare_plan_seals`,
# `ls.internal_seal_conflict` and the three `ls.SEAL_*` verdicts in
# toolkit/harness/test_livesession.py -- and because `run()` and `reassemble()` below call
# `seal_plan`, `write_seal_file`, `marks_instructions`, `plan_manifest` and
# `compare_plan_seals` as BARE GLOBALS, which is what lets that file's section 5g patch
# `mod.seal_plan` / `mod.write_seal_file` and watch run() pick the stubs up.
from planseal import (  # noqa: F401,E402
    PlanSeal, _plan_bytes, seal_plan, _plan_refusal, plan_manifest, write_seal_file,
    MARKS_BANNER, marks_instructions, SEAL_AGREE, SEAL_DISAGREE, SEAL_UNCHECKED,
    SEAL_FILES, seal_records, recorded_seal, internal_seal_conflict, compare_plan_seals,
)


# --------------------------------------------------------------- the guards ----
def one_live_client():
    """Refuse if any Gw.exe is already running: a live run must be ONE client (PLAN §6.1).

    Returns the count for a caller that wants to log it. On a non-Windows box or if the
    query fails, returns None -- and run() treats None as 'cannot confirm', which is a
    refusal, not permission.
    """
    if sys.platform != "win32":
        return None
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='Gw.exe'\" | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        return int(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


# The owner's own install, which is the ONLY thing in reach that knows what build
# ArenaNet is serving today. Read-only, always: CLAUDE.md's rule is that this
# directory is never patched and never launched, and reading its bytes is allowed.
LIVE_INSTALL_EXE = r"C:\gw\Gw.exe"


def service_build():
    """(build, why) for the build the live service is currently serving.

    Derived from the owner's auto-updating install rather than from any pin --
    `buildid.of_image` names that install as a case it exists to handle. A pin
    cannot answer this question by construction: the pin is what we last chose,
    the service serves whatever it shipped this morning.
    """
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid                                   # stdlib + gwpe only
    if not os.path.isfile(LIVE_INSTALL_EXE):
        return None, f"no install at {LIVE_INSTALL_EXE}"
    return buildid.of_image(LIVE_INSTALL_EXE)


def _run_live_builds():
    """{build number: [directory, ...]} for every staged live build. Read from bytes."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid
    out = {}
    try:
        root = vaultpath.require_dir("run-live", why="naming the build that would work")
    except (Exception, SystemExit):                                          # noqa: BLE001
        return out
    for name in sorted(os.listdir(root)):
        exe = os.path.join(root, name, "Gw.exe")
        if os.path.isfile(exe):
            n, _ = buildid.of_image(exe)
            out.setdefault(n, []).append(name)
    return out


def check_build_matches_service(exe):
    """Refuse a live launch whose build is not the one the service is serving.

    WHY THIS IS A REFUSAL AND NOT A WARNING. The updater is LIVE on every
    `run-live/` build by design -- the live client must fetch content during a
    real session -- so an exe older than the service does not fail politely: it
    UPDATES ITSELF, and the key-tap cave is patched at a build-specific address,
    so the tap is gone in the copy that then runs. What that costs is the one
    thing this project rations: an authorized session against the real service,
    spent producing ciphertext with no key. The downstream refusals catch it
    (`slot_rva` re-reads the slot and raises), but they catch it AFTER the login.

    ADDED 2026-08-17, from a question rather than a failure. Asked which build
    to launch, a session hedged -- "whichever matches what ArenaNet serves
    today" -- when the answer was two commands away and doubly determined: the
    owner's install reads 38833 through its own build getter, and `run-live/`
    names its directories `<PE date>_<source sha256[:12]>`, so the directory
    `2026-08-13_64fae3b1369b` is literally named for the sha of the install it
    was patched from. Both witnesses agreed. A question the tools could answer
    and a human could not is exactly the shape that belongs in a preflight.

    SKIPS, LOUDLY, when the owner's install is not on this machine -- the
    checkable thing is absent, which is not the same as checked and fine.
    """
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid
    want, want_why = service_build()
    have, have_why = buildid.of_image(exe)
    if want is None:
        print(f"  [skip] cannot check the launch build against the service: {want_why}.\n"
              f"         The exe reads build {have}. Nothing verified this is the build "
              f"the service serves.", flush=True)
        return {"checked": False, "why": want_why, "launch_build": have}
    if have is None:
        raise LiveError(
            f"cannot read a build number out of the launch client ({have_why}), while the "
            f"service is serving {want}. Refusing rather than launching an unidentified "
            f"binary at the real service.")
    if have != want:
        staged = _run_live_builds()
        fix = (f"  vault/run-live/{staged[want][0]} is build {want} -- launch that one."
               if staged.get(want) else
               f"  NO staged live build is {want}. Rebuild:\n"
               f"    python toolkit/clientpatch/make_custom_client.py "
               f"--no-dh-patch --key-tap\n"
               f"    python toolkit/clientpatch/make_run_dir.py --live")
        raise LiveError(
            f"the launch client is build {have}; the live service is serving {want}.\n"
            f"  A stale live build does not fail politely -- its updater is LIVE by design, "
            f"so it updates ITSELF and the key-tap cave (a build-specific address) is lost "
            f"in the copy that runs. The session would spend the authorized login producing "
            f"ciphertext with no key.\n{fix}\n"
            f"  service: {want_why}\n  launch:  {have_why}")
    print(f"  [ok] launch build {have} matches the service ({want}).", flush=True)
    return {"checked": True, "launch_build": have, "service_build": want}


def preflight(account_label, exe, live_host, want_windivert=True):
    """Everything that must be true before a client is launched at the real service.

    Returns a plan dict on success; raises LiveError naming the first failure. This runs
    the real gates -- it is not a rehearsal -- so a test drives it with a loopback exe and
    expects the stock->live check to refuse, which is the correct answer for our build.
    """
    import cage
    acct = accounts.for_automation(account_label)   # refuses the primary / unflagged

    # The launch gate, from the bytes: a live run needs a STOCK-DH client aimed at the real
    # service, and it must NOT be caged. assert_launch_safe raises on any other cell.
    kind = cage.assert_launch_safe(exe, live_host)
    if kind.get("dh") != "stock":
        raise LiveError(f"the launch client is {kind.get('dh')}, not stock -- a live run "
                        f"needs the unpatched-DH build under vault/run-live")
    if not kind.get("patches", {}).get("key_tapped"):
        raise LiveError("the live build is not key-tapped: without the cave there is no key "
                        "to read, and the ciphertext cannot be decrypted. Rebuild with "
                        "make_custom_client.py --no-dh-patch --key-tap")

    check_build_matches_service(exe)

    running = one_live_client()
    if running is None:
        raise LiveError("could not confirm how many clients are running; refusing rather "
                        "than risk a second live client")
    if running != 0:
        raise LiveError(f"{running} Gw.exe already running -- a live run is ONE client. "
                        f"Close them first (PLAN §6.1: one client, human cadence).")

    # The archive half of the same gate, run HERE rather than trusted from the
    # loopback site -- session.py's own rule: a guard that only guards one of two
    # doors is the shape of the defect it is here to prevent. INTEGRITY ONLY, and
    # no fingerprints: run-live's updater is LIVE by design and streams new map
    # content into this very archive during a session, so it drifts on purpose
    # and a fingerprint check here would refuse the one configuration that works.
    # It verifies and never modifies -- nothing in datcheck opens a file to write.
    #
    # AFTER the client census, and the order is load-bearing rather than tidy. A
    # running client holds an EXCLUSIVE lock on the archive it was launched from,
    # so while one is up this file cannot be opened even for reading -- Python
    # raises PermissionError, not a partial read (RUNBOOK, "The third copy of
    # Gw.dat, and why it exists"). Written ABOVE the census -- as it was for one
    # revision -- the gate answers a left-open client with "the archive could not
    # be read far enough to have findings", which on run-live's 4.2 GB copy of
    # ArenaNet's own archive reads as corruption and names no action, and the
    # refusal written for exactly that case never runs. a10stage.swap's own order
    # is the precedent: probe the client first, read the archive second.
    # test_datcheck.py §12d checks this order, not just the call.
    import datcheck                     # toolkit/mapdata, already on sys.path
    live_dat = os.path.join(os.path.dirname(exe), "Gw.dat")
    cleared = datcheck.assert_archive_safe(live_dat, why="launch at the live service")
    print(f"  [ok] archive: {cleared['summary']}", flush=True)

    if want_windivert:
        wc._load_windivert()      # raises WinDivertError (a LiveError) if absent/unelevated

    return {"account": acct["label"], "exe": exe, "host": live_host, "dh": kind["dh"]}


# The key tap's three names -- `slot_rva` (where the cave stashed master_secret in this
# binary), `KeyRing` (the poller that keeps EVERY distinct value the slot held, written to
# disk as each one appears) and `load_keyring` (the reader that gets them back) -- moved to
# `keytapring.py`, a module that reads one 20-byte slot and one file and nothing else, so
# the key half of a live capture no longer has to be reached through a driver that loads
# the packet-capture backend, the codec, ARC4, `accounts`, `marks` and `vaultpath`. The
# re-export sits HERE, at the site they were defined, because these names are read off THIS
# module: `ls.KeyRing` and `ls.load_keyring` in toolkit/harness/test_livesession.py section
# 3c, and `mod.slot_rva` patched onto this module object by its section 5g -- and because
# `run()` below calls `slot_rva` and constructs `KeyRing` as BARE GLOBALS, and
# `reassemble()` calls `load_keyring` as one, which is what lets that stub land.
from keytapring import slot_rva, KeyRing, load_keyring  # noqa: F401,E402


GAME_MODES = ("base", "reforged")


def run(account_label, exe, live_host, live_ports, minutes, confirm, mode=None,
        out_root=None, plan=None):
    """The live orchestration: launch, sniff, tap, hold, stop, assemble, scrub.

    Refuses without --confirm; needs WinDivert, an elevated shell and the secondary account.

    THIS DRIVER DOES NOT PLAY THE GAME. It launches the client with the account's
    credentials pre-filled and then gets out of the way -- no scripted keystrokes, no
    clicks, no timed actions. That is not an omission. PLAN §6.1 is explicit that what
    closes an account is a traffic pattern no person could produce, and the loopback
    harness's three-Enters-and-a-Play-click is exactly such a pattern. The operator logs in
    and plays; the driver only instruments. The session ceiling is the one thing it does
    enforce, because an unattended client that outlives the operator is the same hazard.
    """
    if not confirm:
        raise LiveError("a live run points a client at ArenaNet's real service. Re-run with "
                        "--confirm once you have read PLAN §6.2 and are at the keyboard: "
                        "human cadence, human hours, one client, never competitive.")
    # --mode is required and has NO DEFAULT, deliberately, and it is the same shape as
    # --confirm one line above: a value the operator must state, refused rather than
    # guessed. See GAME_MODES and the manifest key below for why a default would be worse
    # than useless here.
    if mode not in GAME_MODES:
        raise LiveError(
            f"--mode is required and must be one of {'|'.join(GAME_MODES)} "
            f"(got {mode!r}).\n"
            f"  Reforged Mode changes enemy health and armour by roughly 20%, and NOTHING\n"
            f"  in the recorded stream says which mode produced it. It is not recoverable\n"
            f"  afterwards: every health number from an unstamped capture is base or\n"
            f"  base x 0.8 with nothing on this machine able to say which, forever.\n"
            f"  ~20% is the dangerous size -- it looks like a plausible base value rather\n"
            f"  than an obvious error, so a contaminated number is used rather than caught.\n"
            f"  This is asked BEFORE the client launches because it cannot be asked after,\n"
            f"  and a wrong answer is worse than a refusal: say what the account is\n"
            f"  actually set to, not what you intend it to be.\n"
            f"  The three monster health readings already in the vault (definition slots\n"
            f"  1346=96, 1434=8, 1442=40) predate this flag and are stamped\n"
            f"  mode='unrecorded' -- kept, never promoted. They are the reason this exists.")
    # THE SEAL, AND THIS LINE IS THE FEATURE. Not the hash -- the hash is six lines of
    # hashlib -- but the fact that it is taken HERE: above `preflight`, so before the
    # account is resolved, before `one_live_client` shells out, before the sniffer
    # subprocess and roughly a hundred lines before `subprocess.Popen([exe] + args)`. A
    # seal taken at manifest time (the end of the run, after assembly) would certify
    # whatever the plan said AFTERWARDS, which is not a pre-registration; it is a
    # signature on the answer sheet. Everything downstream reads this carried value and
    # nothing re-hashes the file. See the module header, and the syntax-tree check in
    # test_livesession.py that pins the ordering -- a grep cannot see it.
    #
    # It is also where the refusals land, for the same reason: a malformed plan costs a
    # retype here and an unrepeatable session anywhere later.
    #
    # `is not None`, NOT truthiness, and the difference is the whole unlabelled-by-accident
    # case. `--plan "$PLAN"` with the variable unset hands this an EMPTY STRING, which a
    # truthiness guard routes straight past `marks.load_plan`'s own refusal for exactly
    # that input ("no plan file. An unlabelled run must not be reachable by accident") and
    # into an unsealed run whose manifest then states the FALSE reason "no --plan was
    # passed" -- the operator did pass it. The one distinction this design is built on,
    # "had the flag and did not use it" versus "the tool could not", was silently miscoded
    # by one word. Found by adversarial review 2026-08-13; argparse's own default is None,
    # so absence and emptiness are already distinguishable at this line.
    seal = seal_plan(plan) if plan is not None else None
    preflight(account_label, exe, live_host)
    acct = accounts.for_automation(account_label)
    rva = slot_rva(exe)                      # raises if the live build is not key-tapped

    import subprocess
    import drive_client                     # imported here: it opens user32 at import time
    import cage

    stamp = time.strftime("%Y%m%dT%H%M%S")
    root = out_root or vaultpath.vault_path("captures", "live")
    outdir = os.path.join(root, stamp)
    os.makedirs(outdir, exist_ok=True)
    wire = os.path.join(outdir, "wire.jsonl")

    ports = sorted(set(live_ports))
    print(f"live capture {stamp}")
    print(f"  account : {accounts.describe(acct)}")
    print(f"  client  : {exe}")
    print(f"  tap slot: Gw.exe+0x{rva:x}")
    print(f"  sniffing: ports {','.join(map(str, ports))} on any host")
    print(f"  ceiling : {minutes} min")
    print(f"  output  : {outdir}")
    # On disk NOW, not only in the manifest an hour from now -- see write_seal_file.
    write_seal_file(outdir, seal)
    if seal:
        print(f"  plan    : {os.path.basename(seal.path)} -- {seal.steps} step(s), "
              f"sha256 {seal.sha256[:16]}... SEALED BEFORE LAUNCH")
    else:
        print("  plan    : NONE -- this run will be unlabelled (see the block below)")

    # The live build carries a LIVE auto-updater (owner's decision 2026-08-07 -- the kill
    # switch also disables map streaming and crashed a run on Map.cpp's `found` assert).
    # So the client can now patch ITSELF mid-session, which would replace the binary the
    # frames came from and take the key-tap cave with it. Hash before and after: the
    # question "which build produced these frames" then has an answer on the artifact
    # rather than a rule that used to forbid the situation.
    exe_sha_before = sha256(exe)
    print(f"  build   : sha256 {exe_sha_before[:16] if exe_sha_before else '??'}... "
          f"(re-checked after the run)")

    procs, ring, client, endpoints = [], None, None, set()
    args = []                       # bound in the try; the manifest below reads it either way
    marks_fh = None                 # same: the finally closes it either way
    log_path = os.path.join(os.path.dirname(exe), "Gw.log")
    cap_log = open(os.path.join(outdir, "wirecapture.log"), "w")
    try:
        # --- 1. the sniff starts FIRST, always. The DH handshake is the first thing on the
        # wire and it is the plaintext half; a capture started after the connect has already
        # lost A and the server seed, and no key can recover them. Same rule as
        # drive_client's sampler: an instrument that was not yet running produces absence of
        # evidence, never evidence of absence.
        #
        # And it filters by PORT ONLY -- there is deliberately no way to pin it to an
        # address. Pinning looks like a harmless refinement and silently costs the run its
        # point: Stage A's portal is on a different host, and Stage C's game-server address
        # arrives INSIDE the ARC4-encrypted AUTH_SMSG_GAME_SERVER_INFO, so it cannot be
        # known when the filter is opened and can never be added later. A pinned run
        # captures the auth channel, reports "1/1 connection(s) decrypted", exits 0, and
        # spends the one authorized live session on the one channel our loopback stack
        # already reproduces.
        cmd = [sys.executable, os.path.join(HERE, "wirecapture.py"),
               "--ports", ",".join(map(str, ports)),
               "--seconds", str(minutes * 60 + 120), "--out", wire]
        cap = subprocess.Popen(cmd, stdout=cap_log, stderr=subprocess.STDOUT, text=True)
        procs.append(cap)
        if not _wait_for_sniff(cap, wire):
            raise LiveError("the off-wire capture never opened -- see "
                            f"{os.path.join(outdir, 'wirecapture.log')} (elevated?). "
                            "Nothing was launched.")
        print("  [ok] the off-wire capture is live and sniffing")

        # --- 2. launch, with NO -portal and NO -authsrv: the client uses its own compiled-in
        # ArenaNet endpoints, which is the entire point of the run. drive_client.assert_safe
        # resolves that absence to the live target (an absent flag is not a neutral one) and
        # cage.assert_launch_safe then decides from the BYTES whether this binary may be
        # aimed there -- stock DH, uncaged. An ours-DH build never gets past that line.
        args = ["-windowed", "-log"] + accounts.login_args(acct)
        host = drive_client.assert_safe(exe, args)
        kind = cage.assert_launch_safe(exe, host)
        print(f"  [ok] cage: {kind['dh']} build, cleared for {host}")
        if os.path.exists(log_path):
            os.remove(log_path)
        client = subprocess.Popen([exe] + args, cwd=os.path.dirname(exe))
        procs.append(client)
        print(f"  [ok] launched pid {client.pid}: "
              f"{os.path.basename(exe)} {' '.join(accounts.redact(args))}")

        # --- 3. the keyring polls from now until the client stops, writing each key to
        # disk as it appears. See KeyRing._persist for why that is not an optimisation.
        ring = KeyRing(client.pid, rva, path=os.path.join(outdir, "keyring.jsonl"))
        ring.start()

        stop_file = os.path.join(outdir, "STOP")
        mark_file = os.path.join(outdir, "MARK")
        marks_fh = open(os.path.join(outdir, wc.MARKS_NAME), "w",
                        encoding="utf-8")
        print("\n  YOU drive from here: log in and play at human cadence.")
        print("  TO MARK A MOMENT (what you are about to do), from any shell:")
        print(f"    echo approach > \"{mark_file}\"")
        print("  The text becomes the label. Marks bind your narration to the capture's")
        print("  own clock; without them a session can only be aligned to within seconds")
        print("  after the fact. session_start and session_end are taken automatically.")
        # Two mark channels now reach the operator's eyes at once, so name the difference
        # here rather than leaving them to work it out mid-session. Owner's ruling
        # 2026-08-13: they stay SEPARATE, because free text typed during a run and an
        # ordinal into a plan sealed before launch are different kinds of evidence, and
        # merging them would put both under one "kind" where no consumer could split them.
        print("  That is the DRIVER's channel (marks.jsonl): free text, no prediction. The")
        print("  PRE-REGISTERED channel is the second shell below, and the two stay apart.")
        print("  THREE WAYS TO STOP, and the first only works if THIS WINDOW has focus:")
        print("    1. one Ctrl-C here (the shutdown takes ~30s; pressing again is absorbed)")
        print("    2. just close the Guild Wars window -- same clean path")
        print(f"    3. from any shell:  echo. > \"{stop_file}\"")
        print("  Nothing is lost by killing this process either: the keyring and the wire")
        print("  capture are flushed as they go, and `--assemble` rebuilds the rest.")
        # Printed HERE, with the pid bound and the directory resolved, because this is the
        # block the operator is actually reading before they log in -- not at the top,
        # where it scrolls past behind the launch. The two branches differ in exactly one
        # thing and marks_instructions is where that difference is asserted.
        print("")
        for line in marks_instructions(seal, outdir, pid=client.pid):
            print(line)
        print("")
        _install_sigint()
        endpoints = _hold(client, ring, wire, minutes, cap=cap,
                          stop_file=stop_file, marks_fh=marks_fh,
                          mark_file=mark_file)
    except KeyboardInterrupt:
        print("\n  stopping on Ctrl-C")
    finally:
        # Narrate every step. This phase used to print nothing at all for up to half a
        # minute, which is what made an operator press Ctrl-C again and lose the run.
        if ring:
            ring.stop()
        if client and client.poll() is None:
            print("  closing the client (WM_CLOSE, up to 20s, so Gw.log survives)...",
                  flush=True)
            drive_client.close_client(client)
        print("  stopping the off-wire capture...", flush=True)
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=15)
                except (OSError, subprocess.SubprocessError):
                    pass
        if marks_fh:
            marks_fh.close()
        cap_log.close()
        time.sleep(1)
        if os.path.exists(wire):
            print(f"  wire capture: {os.path.getsize(wire) / 1e6:.1f} MB", flush=True)

    # --- 4. offline: assemble what the wire and the keyring hold, then scrub.
    # Prune BEFORE assembling: the filter has to be wide enough to catch GW on port 80, and
    # everything else it caught is the owner's own traffic rather than evidence.
    pruned_records = 0
    if os.path.exists(wire):
        print("  pruning non-GW connections...", flush=True)
        kept, dropped = prune_wire(wire)
        pruned_records = dropped
        print(f"  pruned: {dropped} record(s) from non-GW connections dropped; "
              f"{kept} GW connection(s) kept", flush=True)

    keys = ring.keyring() if ring else []
    print(f"\n  keyring: {len(keys)} distinct session key(s) tapped")
    if not keys:
        print("  NOTE: no key was ever tapped. The wire capture is kept -- it is still the "
              "only recording of a real session -- but nothing can decrypt it.")
    print("  assembling and decrypting...", flush=True)
    report = assemble_live(wire, keys, outdir)
    for row in report["connections"]:
        if row.get("decrypted"):
            print(f"  [ok] {row['connection']}  {row['channel']}  "
                  f"c2s {row['c2s_bytes']}B / s2c {row['s2c_bytes']}B  ({row['key_from']})")
        else:
            print(f"  [--] {row['connection']}  {row.get('why', 'undecrypted')}")
        if row.get("gaps"):
            print(f"       GAPS in the wire capture: {row['gaps']} -- the keystream "
                  f"desyncs at each one")

    # Outside the capture tree entirely, under the canonical scrubbed root. Not a child of
    # outdir (scrub_tree walks its source, and an output inside that source is a directory
    # the walk descends into), and not a sibling either -- a sibling lands in
    # vault/captures/, where the TREE-WIDE scrub and every capture census then walk it as
    # if it were more evidence. `captures-scrubbed` is already on the skip list everything
    # else uses, so putting it there makes one rule cover both.
    import scrub_captures
    scrubbed = os.path.join(vaultpath.vault_path("captures-scrubbed"),
                            "live-" + stamp)
    files, records, stats, distinct, _un = scrub_captures.scrub_tree(outdir, scrubbed)
    print(f"  scrub: {files} file(s), {records} records, {distinct} distinct secrets "
          f"replaced -> {scrubbed}")
    if stats.get(scrub_captures.OPAQUE_STAT):
        n_opaque = stats[scrub_captures.OPAQUE_STAT]
        print(f"  scrub: {n_opaque} `plain` frame payload(s) could NOT be cleaned and were "
              f"copied through.")
        print("         The auth channel's first client message carries the account email "
              "as UTF-16")
        print("         inside that blob. This capture is vault-only -- not shareable, "
              "scrubbed or not.")
        # And say so where a person copying the TREE will see it. The per-session manifest
        # records this correctly and nobody copying a directory reads one level down; the
        # root manifest was giving an all-clear written before live captures existed.
        marker = scrub_captures.mark_tree_unsafe(
            os.path.dirname(scrubbed), stamp, [f for f in os.listdir(outdir)
                                               if f.endswith(".jsonl")], n_opaque)
        print(f"         Recorded at {marker}")

    exe_sha_after = sha256(exe)
    if exe_sha_before and exe_sha_after and exe_sha_before != exe_sha_after:
        print("\n  *** THE CLIENT BINARY CHANGED DURING THIS RUN ***")
        print(f"      before {exe_sha_before}")
        print(f"      after  {exe_sha_after}")
        print("      The auto-updater is live on this build (it has to be, for map")
        print("      streaming), so ArenaNet patched the client mid-session. The frames")
        print("      above did NOT all come from one binary, and the key-tap cave is gone")
        print("      from the new one -- rebuild before the next run:")
        print("        make_custom_client.py --no-dh-patch --key-tap --no-updater-patch")
        print("        make_run_dir.py --live")

    # Taken from the DIRECTORY, one statement above the manifest literal, so the literal
    # itself holds no logic. At this moment manifest.json does not exist, so `recorded_seal`
    # falls back to plan_seal.json -- the fallback `write_seal_file` was built for, now
    # exercised on the live path rather than only by a test fixture.
    seal_verdict, seal_verdict_why = compare_plan_seals(outdir)
    print(f"  plan seal: {seal_verdict.upper()} -- {seal_verdict_why}")

    manifest = {"stamp": stamp, "exe": exe, "account": acct["label"],
                # An OPERATOR DECLARATION, and labelled as one on purpose. Every other
                # field here is derived from an artifact; this one cannot be. Reforged
                # Mode leaves no mark on the wire that we have measured, so nothing can
                # check it and nothing should pretend to -- `origin.py`'s design rule is
                # derive-from-the-endpoint-never-self-declare, and mode has no endpoint,
                # so it must not be taught to infer this.
                #
                # THE COROBBORATION THAT WOULD MAKE IT REFUTABLE IS NOT BUILT, and is not
                # faked: a Reforged-only map id appearing on the wire would CONTRADICT a
                # `base` declaration, the same one-directional shape as `origin_of`
                # refusing a `live` stamp on an all-loopback file. It needs a measured
                # list of Reforged-only map ids, which this project does not have -- the
                # 12 decrypted connections load map ids 0, 146, 148 and 164 and none of
                # them is Reforged-only. Writing the check against a guessed list would
                # be a check that cannot fail in the direction that matters.
                "game_mode": mode, "game_mode_source": "operator-declared",
                # The pre-registration seal, rendered from the value CARRIED down from
                # before the launch. `plan_manifest` takes the seal and never a path, so
                # there is no file for this site to re-read: a hash taken here would be a
                # hash of the plan as it stands after the session, which is the one thing
                # the seal exists to rule out. FINDINGS §10.5.1 asks for the sha256; the
                # step count is beside it because `marks_meta` records its own and two
                # readings of one file are a claim rather than a note.
                #
                # NOTHING BELOW MAY MENTION `seal.path` OR `plan`. That is not a style
                # rule: re-deriving the seal needs the PATH, and every sabotage that beat
                # the first round of checks did it by reaching for one -- including
                # `sha256(seal.path)`, using this module's own file hasher, three lines
                # from here. §5a asks the syntax tree for exactly that and nothing else in
                # this function violates it.
                **plan_manifest(seal),
                # The second witness, SPENT, and recorded as a value rather than printed.
                # `compare_plan_seals` reads only artifacts -- this capture's own
                # plan_seal.json (manifest.json does not exist yet, so the fallback fires
                # here on the live path) against marks.py's marks_meta -- and never the
                # plan file, which is what lets it sit after the launch at all. Three
                # valued like `origin.py`: UNCHECKED is "the operator did not mark", which
                # is legitimate and is not agreement.
                "plan_seals": seal_verdict, "plan_seals_why": seal_verdict_why,
                "exe_sha256_before": exe_sha_before, "exe_sha256_after": exe_sha_after,
                "exe_unchanged": bool(exe_sha_before and exe_sha_before == exe_sha_after),
                "args": accounts.redact_for_file(args), "ports": ports,
                "client_endpoints": sorted(endpoints),
                # Bind the artifact to the bytes it came from. Without these, deleting a
                # single record from wire.jsonl still reports 6/6 and silently yields a
                # shorter stream -- MEASURED by adversarial review 2026-08-07. A capture
                # that cannot detect its own truncation is not replayable evidence, it is
                # a file that happens to parse.
                "wire_sha256": sha256(wire),
                "wire_bytes": os.path.getsize(wire) if os.path.exists(wire) else 0,
                "keyring_sha256": sha256(os.path.join(outdir, "keyring.jsonl")),
                "pruned_records": pruned_records,
                "keys_tapped": len(keys), "report": report,
                "gw_log": open(log_path, encoding="utf-8", errors="replace").read().splitlines()
                          if os.path.exists(log_path) else []}
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(f"\n  {report['decrypted']}/{report['total']} connection(s) decrypted -> {outdir}")
    return 0 if report["decrypted"] else 1


# `prune_wire` moved to `wiresplit.py` with the rest of the offline assembly and is
# re-exported above; `run()` calls it as a bare global, and `LIVE_PORTS`' comment above
# still names it because the two belong together -- the wide filter and the pruner.


def sha256(path):
    """SHA-256 of a file, or None if it cannot be read."""
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
    except OSError:
        return None
    return h.hexdigest()


_STOPPING = threading.Event()


def _install_sigint():
    """First Ctrl-C asks the hold loop to stop; every later one is ABSORBED.

    Because the obvious thing happened: the first Ctrl-C was caught, cleanup began, and
    `close_client` sat in a silent 20-second `proc.wait` waiting for the game to shut down.
    With nothing on screen the operator pressed Ctrl-C twice more, the second one landed
    INSIDE that wait, and the process died before it assembled or wrote a manifest -- so a
    ten-minute live session produced no artifact at all. The keyring survived only because
    it is written per key.

    Cleanup and assembly must not be interruptible by an impatient second press. They are
    the part that turns a session into a capture.
    """
    import signal
    def handler(_signum, _frame):
        if _STOPPING.is_set():
            print("\n  ...already stopping. Closing the client and assembling -- this takes"
                  "\n     up to ~30s. Ctrl-C again will THROW AWAY the capture; the keys are"
                  "\n     already safe on disk either way.", flush=True)
            return
        _STOPPING.set()
        print("\n  stopping: closing the client cleanly (up to ~20s), then assembling."
              "\n  Please wait -- do not press Ctrl-C again.", flush=True)
    try:
        signal.signal(signal.SIGINT, handler)
    except (ValueError, OSError):
        pass          # not the main thread, or no console; the old behaviour still applies


def _wait_for_sniff(cap, wire, timeout=25):
    """Wait for a real readiness signal, never a fixed sleep.

    open_capture writes the wire_meta line only AFTER WinDivertOpen succeeds, so its
    presence proves the sniff is live before the client is allowed to connect. A dead
    subprocess is caught too, which is the elevated-shell case.
    """
    end = time.time() + timeout
    while time.time() < end:
        if cap.poll() is not None:
            return False
        try:
            if os.path.exists(wire) and '"wire_meta"' in open(
                    wire, encoding="utf-8", errors="replace").read():
                return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def _take_mark(marks_fh, wire, n, label, at_wall=None, at_perf=None):
    """Write one operator mark, binding this instant to the capture's own clock.

    Reads the capture for its last segment `t` rather than sharing state with the
    sniffer, because the sniffer is a SUBPROCESS and there is no shared state to have.
    Cheap at human cadence: a mark is once per narration step, not once per packet.
    """
    if marks_fh is None:
        return
    wc.write_mark(marks_fh, n, label, wc.last_wire_t(wire),
                  at_wall=at_wall, at_perf=at_perf)


def _hold(client, ring, wire, minutes, cap=None, stop_file=None,
          marks_fh=None, mark_file=None):
    """Hold the session until the ceiling, the client exiting, or Ctrl-C.

    AND WATCH THE INSTRUMENTS, which this used to not do. A ten-minute live session
    reported `wire: 0 KiB` from the first tick to the last while nine keys were tapped,
    and nothing said why -- the sniff could have died, or been filtering a port the client
    was not using, and the status line looked the same either way. drive_client learned
    this in 2026-08-05 ("an instrument that was not yet running produces absence of
    evidence, never evidence of absence") and the live driver did not inherit it.

    So: sample the client's OWN connections and show what it is really talking to, notice
    a dead sniffer, and say something when bytes are not arriving instead of printing a
    zero forever. Returns the set of remote endpoints observed, for the manifest.
    """
    import tcptable
    ceiling = time.monotonic() + minutes * 60
    started = time.monotonic()
    seen, warned = set(), False
    # TWO ANCHORS EVEN IF THE OPERATOR NEVER MARKS. A session with zero marks is a
    # session nothing can bind, and the operator has a game to play; these cost nothing
    # and mean every capture is at least bracketed.
    marks = 1
    _take_mark(marks_fh, wire, marks, "session_start")
    while time.monotonic() < ceiling and not _STOPPING.is_set():
        if client.poll() is not None:
            print("\n  the client exited")
            break
        # A stop that does not depend on console focus. Ctrl-C only reaches Python when the
        # CONSOLE has focus, and the operator is by definition looking at the game window
        # -- so "Ctrl-C once to stop" is advice that fails exactly when it is needed. Any
        # shell, elevated or not, can now end the session:  echo. > <outdir>\STOP
        if stop_file and os.path.exists(stop_file):
            print("\n  STOP file seen -- ending the session")
            break
        # A NARRATION MARK, by the same file mechanism and for the same reason: the
        # operator is looking at the game window, so anything needing console focus is
        # advice that fails exactly when it is needed. `echo approach > <outdir>\MARK`
        # from any shell stamps this instant into marks.jsonl, and the file's contents
        # become the label. Deleted after reading so the next one is a fresh edge.
        if mark_file and os.path.exists(mark_file):
            label, at_wall, at_perf = "mark", None, None
            try:
                with open(mark_file, encoding="utf-8", errors="replace") as fh:
                    parts = fh.read().splitlines()
                label = (parts[0].strip() or "mark")
                # THE INSTANT THE OPERATOR ACTED, not the instant we noticed. This loop
                # polls every 5 s, so stamping at pickup is late by up to that much --
                # coarser than the binding is for. narrate() writes both clocks into the
                # file; a hand-written `echo label > MARK` has neither and falls back.
                if len(parts) >= 3:
                    at_wall, at_perf = float(parts[1]), float(parts[2])
            except (OSError, ValueError, IndexError):
                pass
            try:
                os.remove(mark_file)
            except OSError:
                pass
            marks += 1
            _take_mark(marks_fh, wire, marks, label,
                       at_wall=at_wall, at_perf=at_perf)
            print(f"\n  mark {marks}: {label}", flush=True)
        if cap is not None and cap.poll() is not None:
            print(f"\n  *** THE OFF-WIRE CAPTURE DIED (exit {cap.poll()}) -- nothing is "
                  f"being recorded.\n      See wirecapture.log. Keys are still being "
                  f"tapped and are safe on disk.", flush=True)
            cap = None                      # say it once, keep the session going
        try:
            for c in tcptable.connections(client.pid):
                if c["remote"] != "0.0.0.0:0":
                    seen.add(c["remote"])
        except Exception:
            pass
        left = int(ceiling - time.monotonic())
        size = os.path.getsize(wire) if os.path.exists(wire) else 0
        ports = sorted({int(r.rsplit(":", 1)[1]) for r in seen if ":" in r})
        print(f"\r  t-{left // 60:02d}:{left % 60:02d}  keys: {len(ring.values)}  "
              f"wire: {size / 1024:.0f} KiB  client ports: "
              f"{','.join(map(str, ports)) or 'none seen'}   ", end="", flush=True)
        # Bytes should arrive within seconds of the first handshake. If they have not
        # after a minute, the run is producing nothing and the operator should know while
        # there is still time to stop rather than at the end.
        if not warned and size < 1024 and time.monotonic() - started > 60:
            warned = True
            unmonitored = sorted(set(ports) - set(LIVE_PORTS))
            print(f"\n  *** NO WIRE BYTES after 60s, while {len(ring.values)} key(s) have "
                  f"been tapped.\n      Sniffing {sorted(LIVE_PORTS)} on IPv4. The client's "
                  f"own connections:\n      "
                  f"{', '.join(sorted(seen)) or 'NONE VISIBLE -- tcptable is IPv4-only, so '
                              'an IPv6 connection would look like this'}", flush=True)
            if unmonitored:
                # This is the whole diagnosis, so say it as one sentence rather than
                # leaving it to be read off two lists.
                print(f"      >>> THE CLIENT IS ON PORT(S) {unmonitored}, WHICH ARE NOT "
                      f"BEING SNIFFED. <<<\n      Add them to LIVE_PORTS and re-run; this "
                      f"capture will have no ciphertext.", flush=True)
            print("      Ctrl-C once to stop.", flush=True)
        _STOPPING.wait(5)
    else:
        if not _STOPPING.is_set():
            print("\n  session ceiling reached -- closing the client")
    _take_mark(marks_fh, wire, marks + 1, "session_end")
    return seen


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assemble", default=None, metavar="DIR",
                    help="re-assemble an existing capture directory from its own "
                         "wire.jsonl + keyring.jsonl and exit. No client, no network, no "
                         "account -- this is the offline half, and it is why the keyring "
                         "is persisted")
    ap.add_argument("--account", default=None, help="automation-flagged label in accounts.json")
    ap.add_argument("--exe", default=None, help="the stock-DH, key-tapped live build")
    # --host is accepted only to REFUSE it by name. RUNBOOK documented `--host <auth ip>`
    # as the live command for a day, and an operator working from a printed or remembered
    # copy of that line would otherwise get an argparse error that reads like a typo. What
    # it actually asked for is the one setting that quietly ruins the run -- see the
    # comment on the wirecapture launch in run().
    ap.add_argument("--host", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--ports", default=",".join(map(str, LIVE_PORTS)))
    ap.add_argument("--minutes", type=int, default=10,
                    help="session-length CEILING, not a duration -- Ctrl-C ends the run at "
                         "any point and still assembles and scrubs in full (default: 10)")
    ap.add_argument("--confirm", action="store_true", help="required for a real live run")
    # OPTIONAL, unlike --mode, and the module header argues why at length: a missing mode
    # poisons every number in the capture forever, a missing plan only leaves it
    # unlabelled. So this one is VISIBLE-when-absent rather than refused (D9(a)'s shape),
    # and the manifest says so in a key rather than by omitting one.
    ap.add_argument("--plan", default=None, metavar="PATH",
                    help="the PRE-REGISTERED operator-mark plan (kind<TAB>text per line) "
                         "that marks.py will read in a second shell. Hashed BEFORE the "
                         "client launches and the hash written to manifest.json; without "
                         "it the run is unlabelled and says so loudly")
    # No `default=`, and `choices` rather than a free string. argparse's own error is the
    # first refusal an operator meets; run()'s longer one explains why. Both exist because
    # a default here would be silently wrong on every run that did not think about it,
    # which is the entire failure this flag prevents.
    ap.add_argument("--mode", default=None, choices=GAME_MODES,
                    help="REQUIRED: the account's game mode, base or reforged. Reforged "
                         "changes enemy health and armour ~20%% and is UNRECOVERABLE "
                         "afterwards -- an unstamped capture's stats can never be graded")
    a = ap.parse_args()
    if a.assemble:
        return reassemble(a.assemble)
    if not a.account:
        raise LiveError("--account is required for a live run (or use --assemble DIR)")
    if not a.exe:
        raise LiveError("a live run needs --exe: the key-tapped, stock-DH build under "
                        "vault/run-live. Nothing here picks a client for you -- on "
                        "2026-08-06 two tools picked the wrong one by filename order.")
    if a.host:
        raise LiveError(
            f"--host {a.host} is refused, and this is not a naming quibble.\n"
            f"  It used to pin the sniff to one address. A live login is THREE stages on\n"
            f"  three endpoints: the portal (Stage A) is a different host, and the game\n"
            f"  server's address (Stage C) arrives inside the ARC4-encrypted\n"
            f"  AUTH_SMSG_GAME_SERVER_INFO -- so it is not knowable when the filter opens\n"
            f"  and cannot be added afterwards. A pinned run records the auth channel,\n"
            f"  prints '1/1 connection(s) decrypted', exits 0, and spends the one\n"
            f"  authorized live session on the only channel loopback already reproduces.\n"
            f"  Drop the flag: the sniff filters by port on any host, which is what the\n"
            f"  multi-connection reader exists for.")
    ports = {int(p) for p in a.ports.split(",") if p.strip()}
    return run(a.account, a.exe, drive_client_default(), ports, a.minutes, a.confirm,
               mode=a.mode, plan=a.plan)


def reassemble(outdir):
    """Re-run the offline half over a capture directory that already exists.

    The point of persisting the keyring: a capture is a THING ON DISK that can be decoded
    again -- after a framing fix, after a new opcode is understood, months later -- without
    a second live session. R0b's criterion says "byte-replayable from disk" and this is the
    function that makes that true rather than aspirational.
    """
    wire = os.path.join(outdir, "wire.jsonl")
    kr = os.path.join(outdir, "keyring.jsonl")
    if not os.path.isfile(wire):
        raise LiveError(f"no wire.jsonl in {outdir}")
    if not os.path.isfile(kr):
        raise LiveError(
            f"no keyring.jsonl in {outdir}.\n"
            f"  Captures written before 2026-08-07 held their keys in memory only, and\n"
            f"  whatever did not decrypt at the time cannot be decrypted now -- the key\n"
            f"  derives from ArenaNet's private exponent. The wire bytes are still there\n"
            f"  and still worth keeping; they just have no key.")
    keys = load_keyring(kr)
    print(f"re-assembling {outdir}\n  keyring: {len(keys)} key(s)")
    # The second witness, RECOMPUTED here and written back. A report and never a refusal:
    # a disagreement is a fact about the labels, not about the ciphertext, and refusing to
    # decode a real live capture over it would destroy the more valuable half to protect
    # the cheaper one.
    #
    # Recomputed rather than read, because this is the one place the answer can CHANGE
    # after the run: `run()` records it at manifest time, and a marker started late, a
    # plan_marks.jsonl copied in afterwards, or a capture assembled months later all move
    # it. Written back for the reason the whole comparison moved out of `reassemble()` in
    # the first place -- until 2026-08-13 this function only PRINTED the verdict, so the
    # single comparison this pair of tools makes possible lived in console scrollback and
    # reached no artifact at all.
    verdict, why = compare_plan_seals(outdir)
    print(f"  plan seal: {verdict.upper()} -- {why}")
    update_manifest(outdir, {"plan_seals": verdict, "plan_seals_why": why})
    report = assemble_live(wire, keys, outdir)
    # AND WRITE THE REPORT BACK, for exactly the reason the seal comment above gives.
    # Until 2026-08-18 this function recomputed the whole per-connection report, PRINTED
    # it, and dropped it on the floor -- so `manifest.json` kept whatever `run()` wrote
    # during the live session, forever. That is not cosmetic. Capture 20260817T231139 was
    # re-assembled after the key tie-break landed and went from 13/15 to 15/15 connections
    # on disk, while its manifest went on saying `decrypted: false`, `key_from: null` and
    # `"2 different keys all fit; refusing to choose"` for the two recovered ones -- one of
    # them the largest connection in the corpus. Any consumer trusting the manifest over
    # the directory would skip a file that is sitting right there and frames cleanly.
    # `report_from` distinguishes the two writers; a manifest without it was written by
    # `run()` and never re-assembled.
    update_manifest(outdir, {"report": report, "report_from": "reassemble"})
    for row in report["connections"]:
        if row.get("decrypted"):
            print(f"  [ok] {row['connection']}  {row['channel']}  "
                  f"c2s {row['c2s_bytes']}B / s2c {row['s2c_bytes']}B  ({row['key_from']})")
        else:
            print(f"  [--] {row['connection']}  {row.get('why', 'undecrypted')}")
    print(f"\n  {report['decrypted']}/{report['total']} connection(s) decrypted")
    return 0 if report["decrypted"] else 1


def update_manifest(outdir, fields):
    """Merge `fields` into an existing manifest.json. Returns True if it was rewritten.

    NARROW ON PURPOSE, because this is the only code in the project that edits the primary
    artifact of a run that cannot be repeated. It refuses to CREATE a manifest (a capture
    with none is a run that died before assembly, and `plan_seal.json` is that run's record
    -- inventing a manifest here would fabricate one), it refuses anything that does not
    already parse as a JSON object rather than truncating it, and it writes through a
    temporary file in the same directory plus `os.replace`, so a crash mid-write leaves the
    original whole. Every key it does not name survives untouched, which the test asserts
    field-for-field rather than trusting the `update` call.
    """
    path = os.path.join(outdir, "manifest.json")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(rec, dict):
        return False
    rec.update(fields)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, path)
    return True


def drive_client_default():
    """The symbolic 'wherever the client's own build points' target: ArenaNet.

    A live run passes no -portal and no -authsrv, so there is no address to name. This is
    the string the launch gate reasons about, and it is deliberately not loopback-shaped.
    """
    sys.path.insert(0, HERE)
    import drive_client
    return drive_client.ARENANET_DEFAULT


if __name__ == "__main__":
    sys.exit(main())
