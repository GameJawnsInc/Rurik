<#
.SYNOPSIS
    Launch the patched client through its update check, then slam the cage shut.

.DESCRIPTION
    The client will not reach its login screen until the pre-login patcher (the
    "Guild Wars Reforged / Connecting to ArenaNet" screen, which shares a string
    block with "Downloading %u.%uMB (%uKB/sec)") completes one outbound check.
    With isolate_client.ps1's block rule active that check can never succeed, so
    the client sits on that screen forever.

    Measured, 2026-08-04: a Windows Firewall OUTBOUND BLOCK fails connect()
    immediately rather than black-holing it, so the socket never reaches
    SYN_SENT and never appears in a sample. Twenty-four samples over twenty
    seconds found no sockets at all while the client sat there, with two threads
    parked in ExecutionDelay -- try, denied instantly, sleep, retry, forever.
    Zero sockets looked like evidence AGAINST the firewall. It was not.

    So: drop the block, let the client through the patcher, then restore the
    block the moment its outbound work finishes. Everything after that point --
    portal, auth, character select -- is loopback only and runs caged, which is
    how "Test Warrior" was reached on 2026-08-04.

    The re-cage is in a finally block. Ctrl-C, a throw, or a client crash all
    still close it. The one way to leave it open is to kill this shell outright.

    On the way past, every non-loopback endpoint the client touches is recorded
    to vault/captures/patcher/. That is the point of the exercise as much as the
    launch is: an earlier session watched this client establish a connection to
    3.65.211.216:80 (AWS eu-central-1) that matched no hostname in the binary and
    could not be identified. This is the window in which that happens.

.NOTES
    Needs an elevated PowerShell -- changing firewall rules requires admin.
    Requires isolate_client.ps1 to have been run once to create the rules.
#>
param(
    [string]$Exe = "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe",
    [string[]]$ClientArgs = @("-authsrv", "127.0.0.1", "-portal", "127.0.0.1", "-windowed", "-log"),
    [int]$TimeoutSeconds = 90,
    [string]$CaptureDir = "C:\gd\Rurik\vault\captures\patcher"
)

$ErrorActionPreference = "Stop"
$RuleName = "Rurik - patched GW client: block outbound"

if (-not ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Run this from an elevated PowerShell (firewall rules need admin)."
    exit 1
}

# Same guard as make_custom_client.py: never operate on the live install.
if ($Exe -like "C:\gw\*" -or $Exe -like "C:\gw") {
    Write-Error "Refusing to run against the live install at C:\gw. Pass the run-dir copy."
    exit 1
}
if (-not (Test-Path -LiteralPath $Exe)) {
    Write-Error "Not found: $Exe`nRun toolkit\clientpatch\make_run_dir.py first, or pass -Exe."
    exit 1
}

$block = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if (-not $block) {
    Write-Error "No block rule named '$RuleName'.`nRun toolkit\clientpatch\isolate_client.ps1 first."
    exit 1
}

# The rule is scoped to a program path. If it names a different exe than the one
# we are about to launch, caging it afterwards would protect the wrong binary --
# and would do so silently.
$ruleExe = ($block | Get-NetFirewallApplicationFilter).Program
if ($ruleExe -ne $Exe) {
    Write-Error "The cage covers a different binary.`n  rule:   $ruleExe`n  launch: $Exe`nRe-run isolate_client.ps1 -Exe '$Exe'."
    exit 1
}

if (-not (Test-Path -LiteralPath $CaptureDir)) {
    New-Item -ItemType Directory -Path $CaptureDir -Force | Out-Null
}
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmss")
$log = Join-Path $CaptureDir "patcher-$stamp.jsonl"

function Write-Event($obj) {
    ($obj | ConvertTo-Json -Compress -Depth 5) | Add-Content -Path $log -Encoding utf8
}

Write-Event @{ event = "launch"; exe = $Exe; clientArgs = ($ClientArgs -join " "); wall = (Get-Date).ToUniversalTime().ToString("o") }

$LOOPBACK = @("127.0.0.1", "::1", "0.0.0.0", "::")
$endpoints = @{}
$proc = $null

try {
    Disable-NetFirewallRule -DisplayName $RuleName
    Write-Host "cage OPEN  -- block rule disabled" -ForegroundColor Yellow

    $proc = Start-Process -FilePath $Exe -ArgumentList $ClientArgs -PassThru
    Write-Host "launched   -- pid $($proc.Id)"
    Write-Event @{ event = "pid"; pid = $proc.Id }

    # Close the cage on whichever comes first: the client going quiet, or a hard
    # grace period after its first outbound connection.
    #
    # "Quiet" alone is not enough and assuming it was a bug. The patcher's
    # connections to the file CDN are HTTP keep-alive and simply do not close,
    # so the quiet counter never advanced and every launch held the cage open
    # for the full timeout instead of the intended couple of seconds. Worse,
    # firewall rules are evaluated at connection ESTABLISHMENT, so anything
    # opened inside the window survives the re-cage for the life of the process
    # -- a longer window means more established connections to ArenaNet, not
    # merely a longer wait.
    #
    # This bounds the exposure. It does not eliminate it: connections opened
    # during the grace period still survive, and Windows offers no supported way
    # to tear down an established TCP connection. The real fix is to stop the
    # updater from running at all, so the cage never has to open.
    $graceSeconds = 8
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $firstOutbound = $null
    $sawOutbound = $false
    $quiet = 0

    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) {
            Write-Host "client exited before the patcher finished" -ForegroundColor Red
            break
        }

        $conns = @(Get-NetTCPConnection -OwningProcess $proc.Id -ErrorAction SilentlyContinue |
            Where-Object { $LOOPBACK -notcontains $_.RemoteAddress })

        if ($conns.Count -gt 0) {
            if (-not $sawOutbound) { $firstOutbound = Get-Date }
            $sawOutbound = $true
            $quiet = 0
            foreach ($c in $conns) {
                $key = "$($c.RemoteAddress):$($c.RemotePort)"
                if (-not $endpoints.ContainsKey($key)) {
                    $endpoints[$key] = @{ addr = $c.RemoteAddress; port = $c.RemotePort; states = @() }
                    Write-Host "  outbound -> $key ($($c.State))" -ForegroundColor Cyan
                }
                if ($endpoints[$key].states -notcontains $c.State.ToString()) {
                    $endpoints[$key].states += $c.State.ToString()
                }
            }
        }
        else {
            if ($sawOutbound) { $quiet++ }
        }

        if ($sawOutbound -and $quiet -ge 5) { break }
        if ($sawOutbound -and ((Get-Date) - $firstOutbound).TotalSeconds -ge $graceSeconds) {
            Write-Host "  grace period reached - closing the cage on live connections" -ForegroundColor Yellow
            break
        }
        Start-Sleep -Milliseconds 200
    }

    if (-not $sawOutbound) {
        Write-Host "no outbound connection observed before the window closed." -ForegroundColor Yellow
        Write-Host "either the check was already satisfied, or it is not TCP." -ForegroundColor Yellow
    }
}
finally {
    # Whatever happened above -- timeout, crash, Ctrl-C -- the cage closes.
    Enable-NetFirewallRule -DisplayName $RuleName
    Write-Host "cage SHUT  -- block rule re-enabled" -ForegroundColor Green
    Write-Event @{ event = "recaged"; wall = (Get-Date).ToUniversalTime().ToString("o") }
}

foreach ($key in $endpoints.Keys) {
    $e = $endpoints[$key]
    $host_ = $null
    try { $host_ = [System.Net.Dns]::GetHostEntry($e.addr).HostName } catch { $host_ = $null }
    $e.reverse_dns = $host_
    Write-Event @{ event = "endpoint"; addr = $e.addr; port = $e.port; states = $e.states; reverse_dns = $host_ }
}

Write-Host ""
Write-Host "recorded: $log"
if ($endpoints.Count -gt 0) {
    Write-Host "non-loopback endpoints the patcher touched:"
    foreach ($key in $endpoints.Keys) {
        $e = $endpoints[$key]
        $rd = $e.reverse_dns
        if (-not $rd) { $rd = "(no reverse DNS)" }
        Write-Host "  $key  $rd  [$($e.states -join ',')]"
    }
}
Write-Host ""
Write-Host "The client is caged again. Log in normally -- everything from here is loopback."
