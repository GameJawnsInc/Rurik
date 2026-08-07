"""Is this client caged? Asked at launch time, and answered fail-closed.

WHY THIS EXISTS. `toolkit/clientpatch/isolate_client.ps1` confines a patched client to
loopback with a pair of Windows Firewall rules, and it is the strongest safety control in
this repo. Nothing has ever checked that it is actually in place.

On 2026-08-06 that cost exactly what it was always going to cost: two patched binaries
sat under `vault/run` and only one was caged. The uncaged one -- a `-probe` copy built so
a parallel session could keep reading the archive -- had been that way for a day, and it
was found by a person asking rather than by any gate. `assert_safe` in
`toolkit/harness/drive_client.py` checked the exe's path and the loopback flags, both of
which the uncaged copy passed.

WHY IT MATTERS MORE SINCE §7 Q4. Live automation on the secondary account is now
authorized, so the machine will soon carry a client that is *meant* to reach ArenaNet.
Two configurations with opposite requirements, and the failure that ends an account is
launching the wrong one:

  * A client carrying OUR Diffie-Hellman parameters **fails late** against the real
    service. The DH substitution touches Stage B only, so the client completes a REAL
    Stage A portal login with whatever credential it autofilled -- the owner's primary --
    and only then dies at Stage B, delivering garbage frames to ArenaNet's auth server.
    The account-visible event happens before the patch matters.
  * A live-capture client cannot be caged at all. The cage pins to loopback by program
    path; there is no partial setting.

So the rule this module enforces is no longer "a patched client must be caged". That
sentence cannot express the authorized case at all: the live-capture client is patched
and must NOT be caged. The rule is now a BINDING between a binary and a target --

    a client may only be launched at the server whose Diffie-Hellman exponent
    matches the parameters it carries

-- which covers both configurations, and both directions of getting it wrong. See
`assert_launch_safe`.

WHAT COUNTS AS WHICH. Not a whole-file hash. `toolkit/clientscan/pinned.py` answers
`pristine`/`patched`/`unknown` by SHA-256, which is right for a study asking "which copy
did I read" and wrong here for two reasons: it knows exactly ONE patched hash, so every
client `make_custom_client.py` builds reads as `unknown` until a human edits a constant;
and its `patched` bucket holds four independent modifications when only one of them --
the DH substitution -- decides anything.

`toolkit/clientpatch/buildid.py` reads the parameters out of the binary instead and
answers `ours` / `stock` / `unknown`, where `ours` means the triple matches a key file
that satisfies B == g^b mod p. That last clause is what makes it a check rather than a
label: it proves we hold the exponent, which is the operational meaning of "this client
can key against our server, and its traffic to anyone else is garbage."

FAIL CLOSED, everywhere the failure is an EXPOSURE. If PowerShell will not run, if the
firewall cannot be enumerated, if the parameters are unrecognised -- refuse. The cost of
a false refusal is an annoyed operator reading one error message. The cost of a false
pass is an account. The one documented exception is on the live-capture path, where the
firewall guards a stall rather than an exposure; `assert_launch_safe` says so at the
line where it applies.

"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import buildid  # noqa: E402
import origin  # noqa: E402

RULE_BASE = "Rurik - patched GW client: block outbound"

# One query, both directions, so a block rule with no matching loopback allow cannot
# read as "caged". isolate_client.ps1's own comment records that a -Remove matching the
# bare display name leaves the allow behind -- the orphan looks like cleanup and still
# permits traffic -- so the pair is what gets asserted, never just the block.
#
# The exe path is interpolated as a single-quoted PowerShell literal rather than passed
# as an argument: `powershell -Command <script> <arg>` does NOT bind trailing arguments
# to $args -- it appends them to the command text -- so the first version of this hung
# with an empty $exe. Single quotes mean no expansion, and a path cannot contain the one
# character that would break out, `'`, on Windows.
_PS = r"""
$ErrorActionPreference = 'Stop'
$exe = '%s'
$block = $false; $allow = $false
foreach ($r in (Get-NetFirewallRule -DisplayName '%s*' -ErrorAction SilentlyContinue)) {
    if (-not $r.Enabled) { continue }
    $p = ($r | Get-NetFirewallApplicationFilter).Program
    if ($p -ne $exe) { continue }
    if ($r.Action -eq 'Block') { $block = $true }
    if ($r.Action -eq 'Allow') {
        $a = ($r | Get-NetFirewallAddressFilter).RemoteAddress
        if ($a -contains '127.0.0.1') { $allow = $true }
    }
}
if ($block -and $allow) { 'CAGED' } elseif ($block) { 'BLOCK-ONLY' }
elseif ($allow) { 'ALLOW-ONLY' } else { 'UNCAGED' }
"""


class CageError(SystemExit):
    """Refusing to launch. Never a warning -- the whole point is that it stops."""


def cage_state(exe):
    """'CAGED' | 'BLOCK-ONLY' | 'ALLOW-ONLY' | 'UNCAGED', or None if undeterminable.

    None is not 'uncaged' and callers must not treat it as either answer -- it means the
    question could not be asked, which is its own failure and gets its own message.
    """
    exe = os.path.abspath(exe)
    if "'" in exe:
        return None          # cannot be quoted safely; refuse to guess
    script = _PS % (exe, RULE_BASE)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    state = out.stdout.strip().splitlines()[-1].strip() if out.stdout.strip() else ""
    return state if state in ("CAGED", "BLOCK-ONLY", "ALLOW-ONLY", "UNCAGED") else None


def assert_launch_safe(exe, host, why="launch"):
    """Refuse unless this binary's DH parameters match where it is being pointed.

    THE INVARIANT, and it is one sentence: **a client may only be launched at the
    server whose Diffie-Hellman exponent matches the parameters it carries.** Both
    directions are enforced, because both directions are real failures:

        binary   target      outcome
        ours     loopback    the daily loop. Requires a verified cage.
        ours     LIVE        REFUSED. Stage A completes against ArenaNet with the
                             autofilled credential BEFORE the DH mismatch bites, so
                             this is the failure that costs an account rather than a
                             session (PLAN.md §6.2).
        stock    LIVE        the authorized capture run (§7 Q4). Must NOT be caged.
        stock    loopback    REFUSED. It cannot key against us, so this can only mean
                             the wrong binary was staged -- and the operator would
                             otherwise learn that from `AUTH_CMSG has no opcode 26763`
                             thirty seconds later, which names nothing.
        unknown  anything    REFUSED.

    Read from the BYTES, via buildid.dh_verdict, never from a filename, a directory or
    a flag. That matters because everything else about these two builds is identical --
    same size, same other patches, same run-dir layout -- and the one thing that
    differs is the one thing that decides.

    Returns buildid.describe()'s dict on success, so a caller can log what it let
    through rather than merely that it let something through.
    """
    b = buildid.describe(exe)
    dh, detail = b["dh"], b["dh_detail"]
    live = not origin.is_loopback(host)
    where = f"{host} (the REAL service)" if live else f"{host} (loopback)"

    if dh == buildid.UNKNOWN:
        raise CageError(
            f"REFUSING to {why} {exe} at {where}\n"
            f"  Its Diffie-Hellman parameters match neither a key file we hold nor\n"
            f"  the owner's own install: {detail}\n"
            f"  An unrecognised binary is refused rather than waved through. If this\n"
            f"  copy is legitimate, the key file that goes with it belongs in the\n"
            f"  vault's keys/ directory, named rurik_dh_*.json.")

    if dh == buildid.OURS and live:
        raise CageError(
            f"REFUSING to {why} {exe} at {where}\n"
            f"  This client carries OUR Diffie-Hellman parameters. {detail}\n"
            f"  PLAN.md §6.2: it does not fail cleanly against the real service. The\n"
            f"  substitution touches Stage B only, so the client completes a REAL\n"
            f"  Stage A portal login first -- with whatever credential it autofilled,\n"
            f"  which is the owner's primary -- and only then delivers garbage frames\n"
            f"  to ArenaNet's auth server. The account-visible event happens before\n"
            f"  the patch matters.\n"
            f"  Build the live-capture configuration instead:\n"
            f"      python toolkit/clientpatch/make_custom_client.py --live-capture")

    if dh == buildid.STOCK and not live:
        raise CageError(
            f"REFUSING to {why} {exe} at {where}\n"
            f"  This client carries ArenaNet's Diffie-Hellman parameters, not ours.\n"
            f"  {detail}\n"
            f"  It cannot key against our server: our ARC4 keystream and its own would\n"
            f"  disagree from the first frame, which is the `AUTH_CMSG has no opcode\n"
            f"  26763` failure RUNBOOK records. Refusing here names the cause; letting\n"
            f"  it launch names nothing thirty seconds later.\n"
            f"  Launch the DH-patched copy under vault/run instead.")

    state = cage_state(exe)

    if dh == buildid.STOCK:
        # STOCK at a live target: the authorized capture run.
        #
        # The asymmetry below is deliberate rather than an oversight. Every refusal
        # above fails closed because it guards an EXPOSURE. The two here guard a
        # STALL: a caged live client cannot reach the service it was built for, and a
        # live updater would replace the build we pinned on purpose. So a firewall we
        # cannot enumerate is reported and allowed through -- the safety property for
        # this binary is that it carries ArenaNet's own parameters, established from
        # its bytes above, which does not depend on the firewall at all.
        if state == "CAGED":
            raise CageError(
                f"REFUSING to {why} {exe} at {where}\n"
                f"  This is the live-capture build, and it is CAGED -- pinned to\n"
                f"  loopback, the one place it cannot work. It would sit on\n"
                f"  `Connecting to ArenaNet` forever, and a Windows outbound block\n"
                f"  fails connect() instantly rather than black-holing it, so no socket\n"
                f"  would ever appear to explain why (RUNBOOK, 2026-08-04).\n"
                f"  The cage belongs on the DH-patched build, not this one. Stage this\n"
                f"  one under vault/run-live, which isolate_client.ps1 does not sweep.")
        if b["patches"].get("updater_killed") is not True:
            raise CageError(
                f"REFUSING to {why} {exe} at {where}\n"
                f"  The auto-updater is still live in this build\n"
                f"  (updater_killed={b['patches'].get('updater_killed')!r}).\n"
                f"  PLAN.md §6.2 wants the kill switch on BOTH configurations: it pins\n"
                f"  the build, and an update mid-capture would replace the ground truth\n"
                f"  the capture is being taken to establish -- silently, and after the\n"
                f"  fact nothing says which build produced which frames.\n"
                f"  Rebuild with:\n"
                f"      python toolkit/clientpatch/make_custom_client.py --live-capture")
        if state is None:
            print(f"  note: firewall state undeterminable for {os.path.basename(exe)}; "
                  f"proceeding -- this build carries ArenaNet's own parameters")
        return b

    # dh == OURS at a loopback target: fail closed on every uncertainty, because this
    # is the binary that must never reach the real service.
    if state is None:
        raise CageError(
            f"REFUSING to {why} {exe}\n"
            f"  Could not determine whether this client is caged -- the firewall\n"
            f"  query did not run or did not answer. That is not permission to\n"
            f"  proceed: this binary carries OUR DH parameters, and an uncaged one\n"
            f"  reaching the real service completes a REAL portal login with the\n"
            f"  autofilled credential before it fails.\n"
            f"  Check with:  toolkit\\clientpatch\\isolate_client.ps1 -List")

    if state != "CAGED":
        detail_line = {
            "UNCAGED": "no firewall cage names this binary at all.",
            "BLOCK-ONLY": ("a block rule exists but the loopback ALLOW does not, so the "
                           "client cannot reach our own server either."),
            "ALLOW-ONLY": ("only the loopback allow survives -- the BLOCK is missing, so "
                           "this binary can currently reach anything."),
        }[state]
        raise CageError(
            f"REFUSING to {why} {exe}\n"
            f"  {detail_line}\n"
            f"  This client carries OUR Diffie-Hellman parameters ({detail}).\n"
            f"  PLAN.md §6.2: a client carrying them must never reach the real service,\n"
            f"  and it does not fail cleanly if it does -- Stage A completes first.\n"
            f"  Cage every such client with, in an ELEVATED shell:\n"
            f"      & toolkit\\clientpatch\\isolate_client.ps1\n"
            f"  (no arguments: it enumerates every client under vault/run, which is\n"
            f"  the fix for the single-hardcoded-path default that let one sit\n"
            f"  uncaged for a day.)")
    return b


def assert_caged(exe, why="launch"):
    """The loopback case of assert_launch_safe, kept under its own name for its callers.

    Returns the DH verdict string, so `print(f"cage: {assert_caged(exe)} client")`
    still reads as a sentence.
    """
    return assert_launch_safe(exe, "127.0.0.1", why)["dh"]


def main():
    """Audit every staged client. Exit non-zero if any is in the wrong state.

    Both roots, and each is held to its OWN expectation -- `run/` must be caged,
    `run-live/` must not be. A single "is it caged" sweep would have to call one of
    the two wrong, and the interesting failure is a binary staged in the wrong root:
    that shows up here as a mismatch rather than as a launch that quietly works.
    """
    import vaultpath
    roots = [("run", buildid.OURS, "CAGED"), ("run-live", buildid.STOCK, "UNCAGED")]
    bad = found = 0
    for root, want_dh, want_state in roots:
        base = vaultpath.vault_path(root)
        if not os.path.isdir(base):
            print(f"  -- {root}/ does not exist")
            continue
        for name in sorted(os.listdir(base)):
            exe = os.path.join(base, name, "Gw.exe")
            if not os.path.isfile(exe):
                continue
            found += 1
            b = buildid.describe(exe)
            state = cage_state(exe)
            ok = b["dh"] == want_dh and state == want_state
            bad += not ok
            print(f"  [{'ok' if ok else '!!'}] {root}/{name}")
            print(f"       dh:    {b['dh']} (want {want_dh}) -- {b['dh_detail']}")
            print(f"       cage:  {state} (want {want_state})")
            print(f"       patch: {b['patches']}")
    if not found:
        raise SystemExit(f"no Gw.exe under {vaultpath.vault_path('run')} or run-live")
    print(f"\n{found} client(s), {bad} in the wrong state.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
