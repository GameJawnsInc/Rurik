<#
.SYNOPSIS
    Confine the patched Guild Wars client to loopback.

.DESCRIPTION
    The patched client only ever needs to reach 127.0.0.1: our webgate on 6601 and
    our AuthSrv on 6112. It has no legitimate reason to talk to the internet.

    But it does anyway. Observed during a live session: an established connection
    from Gw.exe to 3.65.211.216:80 (AWS eu-central-1) that matched none of the
    hostnames compiled into the binary, was not Sentry, and refused a plain HTTP
    probe. It could not be identified. Separately, the client embeds Sentry crash
    reporting (SENTRY_DSN, sentry.native are both present in this build), and the
    working method for this project is inject, patch, malform, crash.

    Rather than reason about each channel, remove the question: block ALL outbound
    traffic from the patched executable except loopback. Then nothing this client
    does can reach anyone, whatever it intends.

    This does NOT touch C:\gw. The real client keeps working normally for playing
    the actual game and for capture sessions against the live service.

.NOTES
    Needs an elevated PowerShell. Reverse with -Remove.
#>
param(
    [string]$Exe = "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe",
    [switch]$Remove,
    [switch]$List
)

# ONE CAGE PER RUN DIRECTORY, and that is a fix rather than a flourish.
#
# This script used to name every rule the same thing and delete all rules
# matching that name before creating new ones. Caging a second client therefore
# UNCAGED the first, silently, with a success message. It happened for real on
# 2026-08-06: a second run directory was built so a parallel session could keep
# reading the archive, caging it dropped the cage on the original, and nobody
# would have noticed until something reached the internet from a binary we had
# already malformed packets at.
#
# The rule name now carries the run directory, so cages are independent and
# re-running for the same client is still idempotent.
$RuleBase = "Rurik - patched GW client: block outbound"
$Tag = Split-Path -Leaf (Split-Path -Parent $Exe)
$RuleName = "$RuleBase [$Tag]"

if ($List) {
    $rules = @(Get-NetFirewallRule -DisplayName "$RuleBase*" -ErrorAction SilentlyContinue |
               Where-Object { $_.Action -eq 'Block' })
    if (-not $rules) { "No cages are active."; exit 0 }
    "Active cages:"
    foreach ($r in $rules) {
        $app = ($r | Get-NetFirewallApplicationFilter).Program
        "  {0,-8} {1}" -f $r.Enabled, $app
    }
    exit 0
}

if (-not ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Run this from an elevated PowerShell (firewall rules need admin)."
    exit 1
}

if ($Remove) {
    # Both rules have to go, and they do NOT share a display name -- the allow
    # rule carries a " (allow loopback)" suffix. Matching the bare name removes
    # the block and silently leaves the allow behind, so a later -Remove looks
    # like it cleaned up while the machine still carries a rule for a binary
    # that may no longer exist. The trailing * catches the pair.
    #
    # -Remove takes down EVERY cage, including ones this invocation's -Exe does
    # not name and any left over from before the per-directory naming. Removing
    # only the named one would be the tidier API and the worse safety property:
    # "I asked for the cages to be gone" should not leave some of them up.
    $gone = @(Get-NetFirewallRule -DisplayName "$RuleBase*" -ErrorAction SilentlyContinue)
    $gone | Remove-NetFirewallRule
    "Removed $($gone.Count) rule(s) matching '$RuleBase*' -- ALL cages are now down."
    exit 0
}

if (-not (Test-Path -LiteralPath $Exe)) {
    Write-Error "Not found: $Exe`nRun toolkit\clientpatch\make_run_dir.py first, or pass -Exe."
    exit 1
}

# Same trailing * as above: without it the allow rule survives this cleanup and
# a second copy is created below, stacking one more on every re-run.
#
# Scoped to THIS run directory's rules by the tag in $RuleName, so re-caging one
# client leaves every other cage standing. That scoping is the whole fix.
Get-NetFirewallRule -DisplayName "$RuleName*" -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule

# Allow loopback explicitly first. Windows evaluates block rules ahead of allow
# rules, so the allow has to be scoped to 127.0.0.1 and the block left broad --
# an allow-all-then-block-some ordering would silently do nothing here.
New-NetFirewallRule -DisplayName "$RuleName (allow loopback)" `
    -Direction Outbound -Action Allow -Program $Exe `
    -RemoteAddress 127.0.0.1 -Profile Any | Out-Null

New-NetFirewallRule -DisplayName $RuleName `
    -Direction Outbound -Action Block -Program $Exe -Profile Any | Out-Null

@"
Confined to loopback: $Exe

  allow  -> 127.0.0.1 (our webgate 6601, our AuthSrv 6112)
  block  -> everything else

C:\gw is untouched; the real client still reaches the live service normally.
Verify while the patched client runs, with:
    netstat -ano | findstr <its pid>
Only 127.0.0.1 entries should appear.

Do NOT launch the client directly while this is active. The pre-login patcher
needs one outbound check to complete before it will show the login screen, and
a block denies it instantly and forever -- the client sits on "Connecting to
ArenaNet" with no visible socket to explain why. Launch with:

    .\launch_caged.ps1

which opens the cage, walks the client through the patcher, records whatever it
talked to, and closes the cage again before you log in.

Each run directory gets its own cage, so caging a second client no longer
uncages the first. See what is active with:

    .\isolate_client.ps1 -List

Undo with:  .\isolate_client.ps1 -Remove   (takes down ALL cages, not just this one)
"@
