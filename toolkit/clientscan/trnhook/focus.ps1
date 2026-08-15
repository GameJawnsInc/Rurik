# Bring the client's window to the foreground and report whether it is
# actually visible, because the previous run's negative result ("the terrain
# draw never executes") has "the client skipped drawing an occluded window" as
# its live alternative, and a control that does not verify the window state is
# not a control.
param([Parameter(Mandatory=$true)][int]$Pid_)
$ErrorActionPreference = "Stop"
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  public struct R { public int L, T, Rt, B; }
}
"@
$p = Get-Process -Id $Pid_
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { throw "pid $Pid_ has no main window yet" }
if ([W]::IsIconic($h)) { [W]::ShowWindow($h, 9) | Out-Null }   # SW_RESTORE
[W]::ShowWindow($h, 5) | Out-Null                               # SW_SHOW
[W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 800
$r = New-Object W+R
[W]::GetWindowRect($h, [ref]$r) | Out-Null
$fg = [W]::GetForegroundWindow()
[PSCustomObject]@{
  Handle      = "0x{0:X}" -f $h.ToInt64()
  Visible     = [W]::IsWindowVisible($h)
  Minimised   = [W]::IsIconic($h)
  IsForeground= ($fg -eq $h)
  Rect        = "$($r.L),$($r.T) $($r.Rt - $r.L)x$($r.B - $r.T)"
} | Format-List
