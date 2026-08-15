# Detect an ArenaNet assert/crash dialog while a probe run is in flight.
#
# WHY THIS EXISTS. Two instrumented runs crashed the client and BOTH were
# reported clean, because the only check in the loop was "does the process
# still exist". It does: the assert dialog is a modal window inside the SAME
# process, so `Get-Process` says ALIVE for as long as the dialog is up. The
# owner saw the crash box on screen while the log said the client was healthy.
#
# The signal is the dialog itself. `Crash.dmp` is NOT reliable -- after the
# 2026-08-15 crash no dump existed anywhere under the run directory or %TEMP%,
# so a file-based check would have reported clean too.
#
# Usage:  crashwatch.ps1 <pid>            -> one shot, prints VERDICT line
#         crashwatch.ps1 <pid> <seconds>  -> poll until crash or timeout
#
# Exit 0 = healthy, 1 = crash dialog seen, 2 = process gone.

param([Parameter(Mandatory=$true)][int]$ClientPid, [int]$Seconds = 0)

Add-Type @"
using System;using System.Runtime.InteropServices;using System.Text;
public class CW {
 [DllImport("user32.dll")] public static extern bool EnumWindows(D f, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
 [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int m);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int m);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 public delegate bool D(IntPtr h, IntPtr l);
}
"@

# The render window. ANY OTHER visible top-level window owned by the client is
# a dialog it does not have in normal play -- which is the assert box.
$RENDER = 'ArenaNet_Dx_Window_Class'

function Get-Dialogs([int]$target) {
    $found = New-Object System.Collections.ArrayList
    $cb = [CW+D]{
        param($h, $l)
        $p = 0
        [CW]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
        if ($p -eq $target -and [CW]::IsWindowVisible($h)) {
            $c = New-Object Text.StringBuilder 256
            [CW]::GetClassName($h, $c, 256) | Out-Null
            if ($c.ToString() -ne $RENDER) {
                $t = New-Object Text.StringBuilder 512
                [CW]::GetWindowText($h, $t, 512) | Out-Null
                $txt = $t.ToString()
                # Untitled tool/IME windows are normal; a titled dialog is not.
                if ($txt.Trim()) {
                    [void]$found.Add("class=$($c.ToString()) title=$txt")
                }
            }
        }
        return $true
    }
    [CW]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
    return $found
}

$sw = [Diagnostics.Stopwatch]::StartNew()
do {
    $proc = Get-Process -Id $ClientPid -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Output "VERDICT: PROCESS GONE (pid $ClientPid)"
        exit 2
    }
    $dlg = Get-Dialogs $ClientPid
    if ($dlg.Count -gt 0) {
        Write-Output "VERDICT: CRASH DIALOG (pid $ClientPid)"
        $dlg | ForEach-Object { Write-Output "  $_" }
        Write-Output "  -- the process is still ALIVE; liveness alone would have missed this"
        exit 1
    }
    if ($Seconds -gt 0) { Start-Sleep -Seconds 2 }
} while ($sw.Elapsed.TotalSeconds -lt $Seconds)

Write-Output ("VERDICT: HEALTHY (pid {0}, watched {1:N0}s, no dialog)" -f $ClientPid, $sw.Elapsed.TotalSeconds)
exit 0
