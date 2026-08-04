"""Mirror the third-party prior art this project depends on into the gitignored vault.

Justification, concretely: `gwdevhub/gw_in_browser` returned 404 today while
`jean-humann/gwnative` still links to it as its upstream. A repo in this exact
ecosystem has already disappeared. These are small, public, open-source repos and
cloning them costs minutes; losing one costs a research direction.

They land in vault/ and are gitignored. They are NOT vendored into Rurik and NOT
redistributed — this is a local reference shelf, and every clone keeps its own
LICENSE so provenance stays legible.
"""
import json
import os
import subprocess
import time

DEST = r"C:\gd\Rurik\vault\mirrors"

REPOS = [
    # The two that matter most: a working GW1 server and a working GW1 headless client.
    ("ldufr/OpenTyria",              "GW1 server implementation, C, Unlicense"),
    ("ldufr/Headquarter",            "GW1 headless client, C, MIT — full NCSoft portal/TLS-SRP stack"),
    # The WASM ecosystem. gw_in_browser's gwdevhub original is ALREADY GONE.
    ("shiburito/gw_in_browser",      "WASM client harness + wasmscan/wasmdetour/gensyms tooling"),
    ("jean-humann/gwnative",         "Rust native host for the official WASM client"),
    ("toboshii/gw-web-player",       "Python proxy: CDN + webgate + account + raw TCP over WebSocket"),
    # Live Reforged-era client RE.
    ("apoguita/Py4GW_Reforged_Native", "C++ backend replacing GWCA; offsets/*.json for current client"),
    ("apoguita/Py4GW",               "Python scripting layer + PacketSniffer"),
    # The classic lineage — naming corpus and packet catalog.
    ("GregLando113/GWCA",            "ARCHIVED 2023-11-14. Still the best StoC naming corpus."),
    ("gwdevhub/GWToolboxpp",         "Actively maintained; vendors the closed-source gwca.dll"),
    ("gwdevhub/GuildWarsMapBrowser", "Gw.dat extraction and map viewing"),
    # The dead emulators, for their protocol notes.
    ("GameRevision/GWLP-R",          "Dead Java emulator; wiki carries the packet catalog"),
    ("th0br0/sgwlpr",                "Dead Scala emulator"),
]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900, **kw)


def main():
    os.makedirs(DEST, exist_ok=True)
    manifest = {
        "purpose": ("Local reference mirrors of third-party prior art. Gitignored, not vendored, "
                    "not redistributed. Motivated by gwdevhub/gw_in_browser 404ing while still "
                    "being referenced as an upstream."),
        "mirrored_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repos": [],
    }

    for slug, why in REPOS:
        name = slug.split("/")[1]
        path = os.path.join(DEST, name)
        print(f"\n=== {slug} — {why}")
        if os.path.isdir(os.path.join(path, ".git")):
            print("    already mirrored; fetching updates")
            r = run(["git", "-C", path, "fetch", "--all", "--tags", "--prune"])
        else:
            r = run(["git", "clone", "--quiet", f"https://github.com/{slug}.git", path])
        ok = r.returncode == 0
        if not ok:
            print(f"    FAILED: {(r.stderr or '').strip()[:200]}")
            manifest["repos"].append({"slug": slug, "why": why, "status": "failed",
                                      "error": (r.stderr or "").strip()[:300]})
            continue

        sha = run(["git", "-C", path, "rev-parse", "HEAD"]).stdout.strip()
        when = run(["git", "-C", path, "log", "-1", "--format=%cI"]).stdout.strip()
        count = run(["git", "-C", path, "rev-list", "--count", "HEAD"]).stdout.strip()
        lic = next((f for f in os.listdir(path)
                    if f.lower().startswith(("license", "licence", "unlicense", "copying"))), None)
        size = sum(os.path.getsize(os.path.join(dp, f))
                   for dp, _, fn in os.walk(path) for f in fn
                   if os.path.exists(os.path.join(dp, f)))
        print(f"    ok  {sha[:12]}  {count} commits  last {when[:10]}  {size/1e6:.1f} MB  license={lic}")
        manifest["repos"].append({
            "slug": slug, "why": why, "status": "ok", "head": sha,
            "head_date": when, "commits": int(count or 0),
            "license_file": lic, "bytes": size,
        })

    with open(os.path.join(DEST, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    ok = sum(1 for r in manifest["repos"] if r["status"] == "ok")
    print(f"\n{ok}/{len(REPOS)} mirrored -> {DEST}")


if __name__ == "__main__":
    main()
