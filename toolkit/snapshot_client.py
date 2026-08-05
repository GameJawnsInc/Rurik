"""Snapshot the pinned Guild Wars client into the gitignored vault.

HANDOFF.md section 11 step 2, and section 9's "pin the client version and back it up".
The ground truth for this project is a moving target maintained by someone else:
Reforged auto-upgraded existing owners, and Gw.dat is repatched in place. Every hour
this is not snapshotted is an hour where an ArenaNet patch can silently destroy the
reference we are building against.

Copy only. Nothing in C:\\gw is modified, moved, or deleted.
The destination is vault/, which .gitignore excludes at commit one.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time

SRC = r"C:\gw"
VAULT = r"C:\gd\Rurik\vault\client"

# Small files first so a failure on the 4 GB copy still leaves the important
# metadata behind; Gw.dat last.
FILES = [
    "Gw.exe",
    "GwLoginClient.dll",
    "GWToolbox.exe",
    "gMod.dll",
    "steam_api.dll",
    "steam_appid.txt",
    "Settings.json",
    "THIRD-PARTY-LICENSES.md",
    "Gw.dat",
]

# Deliberately NOT copied: Accounts.json (credential material — see HANDOFF section 9;
# the vault is for game ground truth, not for the owner's login secrets).
EXCLUDED = {"Accounts.json": "credential material, intentionally not vaulted"}


def sha256(path, bufsize=8 << 20):
    h = hashlib.sha256()
    total = os.path.getsize(path)
    done = 0
    t0 = time.time()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
            done += len(b)
            if total > (1 << 30) and done % (512 << 20) < bufsize:
                pct = 100.0 * done / total
                print(f"      hashing {pct:5.1f}%  ({done/1e9:.2f}/{total/1e9:.2f} GB)", flush=True)
    return h.hexdigest(), round(time.time() - t0, 1)


def pe_info(path):
    try:
        with open(path, "rb") as f:
            b = f.read(0x400)
        e = struct.unpack_from("<I", b, 0x3C)[0]
        machine = struct.unpack_from("<H", b, e + 4)[0]
        ts = struct.unpack_from("<I", b, e + 8)[0]
        magic = struct.unpack_from("<H", b, e + 24)[0]
        return {
            "machine": hex(machine),
            "arch": {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64"}.get(machine, "unknown"),
            "pe_format": "PE32" if magic == 0x10B else "PE32+",
            "pe_timestamp_unix": ts,
            "pe_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        }
    except Exception as ex:
        return {"error": str(ex)}


def version_info(path):
    ps = (
        "$v=(Get-Item -LiteralPath '%s').VersionInfo; "
        "[Console]::Out.Write(($v.FileVersion,$v.ProductVersion,$v.CompanyName,"
        "$v.FileDescription -join '|'))" % path
    )
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        keys = ["FileVersion", "ProductVersion", "CompanyName", "FileDescription"]
        return dict(zip(keys, out.split("|")))
    except Exception as ex:
        return {"error": str(ex)}


def main():
    gwexe = os.path.join(SRC, "Gw.exe")
    pe = pe_info(gwexe)
    # Build id: the client's own PE build date plus a short content hash of Gw.exe.
    # Stable, meaningful, and sorts chronologically.
    print("identifying client build...", flush=True)
    exe_hash, _ = sha256(gwexe)
    build_id = f"{pe['pe_timestamp_utc'][:10]}_{exe_hash[:12]}"
    dest = os.path.join(VAULT, build_id)
    os.makedirs(dest, exist_ok=True)
    print(f"build id: {build_id}")
    print(f"dest    : {dest}\n", flush=True)

    manifest = {
        "build_id": build_id,
        "snapshot_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_dir": SRC,
        "note": ("Pinned client snapshot. The live service repatches C:\\gw in place; this "
                 "is the frozen reference every capture manifest cites by build_id."),
        "gw_exe_pe": pe,
        "gw_exe_version": version_info(gwexe),
        "excluded": EXCLUDED,
        "files": [],
    }

    for name in FILES:
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            print(f"  MISSING {name}")
            manifest["files"].append({"name": name, "status": "missing"})
            continue
        size = os.path.getsize(src)
        dst = os.path.join(dest, name)
        print(f"  {name}  ({size/1e6:.1f} MB)", flush=True)
        if os.path.exists(dst) and os.path.getsize(dst) == size:
            print("      already present, verifying instead of recopying", flush=True)
        else:
            t0 = time.time()
            try:
                shutil.copy2(src, dst)
            except PermissionError as ex:
                # The live client holds Gw.dat open. Never abort the whole snapshot
                # for one locked file: the rest is still worth having, and a run that
                # dies without writing a manifest is worse than useless -- it leaves a
                # directory that LOOKS like a backup. Record the gap and carry on.
                print(f"      LOCKED (client running?): {ex.strerror}", flush=True)
                manifest["files"].append({"name": name, "size": size,
                                          "status": "locked", "error": str(ex)})
                continue
            print(f"      copied in {time.time()-t0:.1f}s", flush=True)
        digest, secs = sha256(dst)
        src_digest, _ = sha256(src)
        ok = digest == src_digest
        print(f"      sha256 {digest[:24]}...  match={ok}  ({secs}s)", flush=True)
        manifest["files"].append({
            "name": name, "size": size, "sha256": digest,
            "verified_against_source": ok,
            "pe": pe_info(src) if name.lower().endswith((".exe", ".dll")) else None,
        })

    mpath = os.path.join(dest, "MANIFEST.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nmanifest -> {mpath}")

    bad = [f for f in manifest["files"] if f.get("verified_against_source") is False]
    locked = [f for f in manifest["files"] if f.get("status") == "locked"]
    missing = [f for f in manifest["files"] if f.get("status") == "missing"]

    if bad:
        print(f"!! {len(bad)} file(s) FAILED verification: {[f['name'] for f in bad]}")
        return 1
    if locked:
        print(f"\n!! INCOMPLETE SNAPSHOT — {len(locked)} file(s) locked: "
              f"{[f['name'] for f in locked]}")
        print("   Close Guild Wars and re-run. This directory is NOT a complete backup yet;")
        print("   the manifest records the gap so it cannot be mistaken for one.")
        return 3
    if missing:
        print(f"note: {len(missing)} expected file(s) absent from source: "
              f"{[f['name'] for f in missing]}")
    print("all copies verified byte-identical to source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
