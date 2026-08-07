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

So the rule this module enforces is the one PLAN.md §6.2 states: **a patched client must
be caged, every time it is launched, and we refuse rather than assume.**

WHAT COUNTS AS PATCHED. `toolkit/clientscan/pinned.py` already answers this, exactly, by
whole-file hash: `pristine`, `patched`, or `unknown`. `unknown` is the interesting one --
a freshly generated patched copy carries fresh DH parameters and therefore a hash nobody
has recorded. That returns `unknown`, and `unknown` REFUSES. A guard that waved through
every binary it did not recognise would be worthless precisely when a new one appears.

FAIL CLOSED, everywhere. If PowerShell will not run, if the firewall cannot be
enumerated, if the rules are ambiguous -- refuse. The cost of a false refusal is an
annoyed operator reading one error message. The cost of a false pass is an account.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
import pinned  # noqa: E402

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


def assert_caged(exe, why="launch"):
    """Refuse unless `exe` is a client we recognise AND, if patched, properly caged.

    Returns the pinned.identify() kind on success, so callers can log what they let
    through rather than merely that they let something through.
    """
    kind, detail = pinned.identify(exe)

    if kind == "unknown":
        raise CageError(
            f"REFUSING to {why} {exe}\n"
            f"  This is not a client we recognise: {detail}\n"
            f"  toolkit/clientscan/pinned.py knows the pinned build's pristine and\n"
            f"  patched hashes. An unrecognised binary is refused rather than waved\n"
            f"  through, because a freshly patched copy carries fresh DH parameters\n"
            f"  and a hash nobody recorded -- which is exactly when this check earns\n"
            f"  its keep. If this copy is legitimate, record its hash in pinned.py in\n"
            f"  the same commit that creates it.")

    if kind == "pristine":
        raise CageError(
            f"REFUSING to {why} {exe}\n"
            f"  This is the PRISTINE client, as ArenaNet shipped it. It cannot key\n"
            f"  against our server -- it carries ArenaNet's Diffie-Hellman parameters,\n"
            f"  not ours -- so driving it at loopback produces the garbage-frame\n"
            f"  failure RUNBOOK records, and driving it anywhere else is not this\n"
            f"  tool's job. Launch the patched copy under vault/run.")

    state = cage_state(exe)
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
            f"  This is a PATCHED client ({detail}). PLAN.md §6.2: a client carrying\n"
            f"  our Diffie-Hellman parameters must never reach the real service, and\n"
            f"  it does not fail cleanly if it does -- Stage A completes first.\n"
            f"  Cage every patched client with, in an ELEVATED shell:\n"
            f"      & toolkit\\clientpatch\\isolate_client.ps1\n"
            f"  (no arguments: it enumerates every client under vault/run, which is\n"
            f"  the fix for the single-hardcoded-path default that let one sit\n"
            f"  uncaged for a day.)")
    return kind


def main():
    """Report the cage state of every patched client. Exit non-zero if any is wrong."""
    import vaultpath
    root = vaultpath.vault_path("run")
    if not os.path.isdir(root):
        raise SystemExit(f"no run directory at {root}")
    bad = 0
    found = 0
    for name in sorted(os.listdir(root)):
        exe = os.path.join(root, name, "Gw.exe")
        if not os.path.isfile(exe):
            continue
        found += 1
        kind, detail = pinned.identify(exe)
        state = cage_state(exe)
        ok = kind == "patched" and state == "CAGED"
        if not ok:
            bad += 1
        print(f"  [{'ok' if ok else '!!'}] {name}")
        print(f"       identify: {kind} -- {detail}")
        print(f"       cage:     {state}")
    if not found:
        raise SystemExit(f"no Gw.exe under {root}")
    print(f"\n{found} client(s), {bad} not properly caged.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
