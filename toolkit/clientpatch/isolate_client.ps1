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
    [switch]$Remove
)

$RuleName = "Rurik - patched GW client: block outbound"

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
    $gone = @(Get-NetFirewallRule -DisplayName "$RuleName*" -ErrorAction SilentlyContinue)
    $gone | Remove-NetFirewallRule
    "Removed $($gone.Count) rule(s) matching '$RuleName*'"
    exit 0
}

if (-not (Test-Path -LiteralPath $Exe)) {
    Write-Error "Not found: $Exe`nRun toolkit\clientpatch\make_run_dir.py first, or pass -Exe."
    exit 1
}

# Same trailing * as above: without it the allow rule survives this cleanup and
# a second copy is created below, stacking one more on every re-run.
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

Undo with:  .\isolate_client.ps1 -Remove
"@
