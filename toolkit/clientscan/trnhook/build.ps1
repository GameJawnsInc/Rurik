# Build trnhook.dll as 32-bit, because Gw.exe is 32-bit and a 64-bit DLL
# cannot be injected into it. MSVC only; no third-party library is linked, so
# CLAUDE.md carve-out 3 covers this and the second gate needs no new row.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$msvc = Get-ChildItem "C:\Program Files (x86)\Microsoft Visual Studio\*\BuildTools\VC\Tools\MSVC\*" -Directory |
        Sort-Object Name | Select-Object -Last 1
if (-not $msvc) { throw "no MSVC toolchain found" }
$cl = Join-Path $msvc.FullName "bin\Hostx64\x86\cl.exe"
if (-not (Test-Path $cl)) { throw "no x86 cl.exe at $cl" }

$sdkRoot = "C:\Program Files (x86)\Windows Kits\10"
$sdk = (Get-ChildItem "$sdkRoot\Include" -Directory | Sort-Object Name | Select-Object -Last 1).Name

$inc = @("$($msvc.FullName)\include", "$sdkRoot\Include\$sdk\ucrt",
         "$sdkRoot\Include\$sdk\shared", "$sdkRoot\Include\$sdk\um")
$lib = @("$($msvc.FullName)\lib\x86", "$sdkRoot\Lib\$sdk\ucrt\x86",
         "$sdkRoot\Lib\$sdk\um\x86")
$env:INCLUDE = ($inc -join ";")
$env:LIB = ($lib -join ";")
$env:PATH = "$($msvc.FullName)\bin\Hostx64\x86;$env:PATH"

Push-Location $here
try {
    & $cl /nologo /W3 /O2 /LD /MT trnhook.c /Fe:trnhook.dll `
        /link /SUBSYSTEM:WINDOWS kernel32.lib
    if ($LASTEXITCODE -ne 0) { throw "cl failed with $LASTEXITCODE" }
    $dll = Join-Path $here "trnhook.dll"
    $bytes = [IO.File]::ReadAllBytes($dll)
    $pe = [BitConverter]::ToInt32($bytes, 0x3C)
    $machine = [BitConverter]::ToUInt16($bytes, $pe + 4)
    # 0x014C = IMAGE_FILE_MACHINE_I386. A 64-bit DLL here would fail to inject
    # with a useless error, so the check is worth the three lines.
    if ($machine -ne 0x014C) { throw ("built {0:X4}, need 014C (x86)" -f $machine) }
    "built $dll  machine=014C (x86)  $((Get-Item $dll).Length) bytes"
} finally { Pop-Location }
