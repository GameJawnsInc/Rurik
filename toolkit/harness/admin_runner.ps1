<#
.SYNOPSIS
    A long-lived elevated worker, so firewall work costs one UAC prompt per session
    instead of one per command.

.DESCRIPTION
    Watches a queue directory for request files and runs ONLY a fixed set of named
    actions. It deliberately does not execute arbitrary text: this is an elevated
    process reading instructions off disk, and any non-admin process on the machine
    can write to that directory. An allowlist of four actions is the whole point --
    a generic "run this command as admin" service would be a genuine local
    privilege-escalation hole, dressed up as a convenience.

    Request:  <queue>\<id>.req   containing one action name and nothing else
    Reply:    <queue>\<id>.res   containing the action's output, then a status line

    Stop it with Ctrl-C in its window, or by writing the action "stop".

.NOTES
    Launch once, elevated:
      Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile',
        '-ExecutionPolicy','Bypass','-File',
        'C:\gd\Rurik\toolkit\harness\admin_runner.ps1'
#>
param(
    [string]$Queue = "C:\gd\Rurik\vault\admin-queue"
)

$ErrorActionPreference = "Continue"
$Clientpatch = "C:\gd\Rurik\toolkit\clientpatch"

if (-not ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This must be started elevated, or it cannot do the one job it has."
    exit 1
}

if (-not (Test-Path -LiteralPath $Queue)) {
    New-Item -ItemType Directory -Path $Queue -Force | Out-Null
}

# The entire vocabulary. Adding to it is a deliberate act, not a parameter.
#
# `cage-off` WAS HERE AND WAS REMOVED, 2026-08-06. It ran isolate_client.ps1 -Remove,
# which by design takes down EVERY cage on the machine rather than the one named -- a
# good property for "I asked for the cages to be gone", and a terrible one to expose
# through a queue that any unelevated process can write to. `python
# toolkit/harness/admin.py cage-off` was one word, no UAC prompt, no exe named, no
# confirmation, and nothing anywhere noticed afterwards. This allowlist is the security
# boundary for this runner (see the header), so an action that removes the boundary
# does not belong inside it.
#
# Uncaging is now a deliberate elevated act: run
#   & toolkit\clientpatch\isolate_client.ps1 -Remove
# in an admin shell, where the UAC prompt is the confirmation. Live capture on the
# secondary account needs an UNCAGED client, which makes this the single control
# standing between a patched client and ArenaNet -- see PLAN.md §6.2.
$Actions = @{
    "cage-on"      = { & "$Clientpatch\isolate_client.ps1" }
    "launch-caged" = { & "$Clientpatch\launch_caged.ps1" }
    "rules"        = {
        $r = @(Get-NetFirewallRule -DisplayName "Rurik*" -ErrorAction SilentlyContinue)
        if ($r.Count -eq 0) { "no Rurik rules" }
        else { $r | Select-Object DisplayName, Enabled, Action | Format-Table -AutoSize | Out-String }
    }
}

Write-Host "admin runner up. queue: $Queue"
Write-Host "actions: $($Actions.Keys -join ', '), stop"
Write-Host ""

while ($true) {
    $reqs = @(Get-ChildItem -Path $Queue -Filter "*.req" -File -ErrorAction SilentlyContinue |
              Sort-Object CreationTime)
    foreach ($req in $reqs) {
        $id = [System.IO.Path]::GetFileNameWithoutExtension($req.Name)
        $action = (Get-Content -LiteralPath $req.FullName -Raw -ErrorAction SilentlyContinue).Trim()
        Remove-Item -LiteralPath $req.FullName -Force -ErrorAction SilentlyContinue

        $res = Join-Path $Queue "$id.res"
        Write-Host "[$([datetime]::Now.ToString('HH:mm:ss'))] $id -> $action"

        if ($action -eq "stop") {
            Set-Content -LiteralPath $res -Value "stopping" -Encoding utf8
            Write-Host "stopping on request"
            exit 0
        }
        if (-not $Actions.ContainsKey($action)) {
            # Refused, not attempted. The allowlist is the security boundary.
            Set-Content -LiteralPath $res -Encoding utf8 -Value @"
REFUSED: '$action' is not an allowed action.
allowed: $($Actions.Keys -join ', '), stop
STATUS=refused
"@
            continue
        }

        try {
            $out = & $Actions[$action] 2>&1 | Out-String
            Set-Content -LiteralPath $res -Value ($out + "`nSTATUS=ok") -Encoding utf8
        } catch {
            Set-Content -LiteralPath $res -Encoding utf8 `
                -Value ("ERROR: " + $_.Exception.Message + "`nSTATUS=error")
        }
    }
    Start-Sleep -Milliseconds 400
}
