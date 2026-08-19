"""Read the client's LIVE field of view, and its camera position and target.

    python toolkit/clientscan/fovread.py                 # one sample
    python toolkit/clientscan/fovread.py --watch 60      # sample for 60s

READ-ONLY, and deliberately the cheapest instrument that could answer this:
`OpenProcess(PROCESS_VM_READ)` and `ReadProcessMemory`, the same primitive
`keytap.py` already uses. Nothing is injected, no byte of the client is
written, and there is no breakpoint to miss a window with.

WHY A GLOBAL AND NOT A CONSTANT. `tools/blender/gwcam.py` has carried a
28 mm lens marked NOT MEASURED since it was written, on the grounds that the
client has an `oldfov` command-line flag so the value exists and changed.
Chasing it statically (build 38797) ends at a variable, not a literal:

    GmView.cpp -- the frustum builder at 0x004ED3C0 takes `fov` as its FOURTH
    argument and asserts `fov != 0.0f` (GmView.cpp:3737). Its two callers,
    0x004E2866 and 0x004E29F8, both push the float at **0x00C078C4**, and the
    same site passes `0x00C07860` and `0x00C0786C` -- which the function's own
    failure path prints as `Position = %f, %f, %f` and `Target = %f, %f, %f`
    under the heading `Invalid frustum:`. The value is COMPUTED, by the camera
    update at 0x004F6360 -> 0x004F3420 (`this` = 0x00C079A8), which is handed
    `&fov` to fill and asserts it again at GmCam.cpp:1728.

So there is no single number in the image to read, and a static answer would
have been a guess about which constant the camera happens to land on. That is
the shape of claim this arc has retracted four times. **A live read is the
measurement**, and sampling it while the camera moves is what decides whether
the field of view is fixed at all or varies with zoom -- which no disassembly
of a variable can tell you.

`--watch` therefore matters more than the single sample: hold still, then zoom
all the way in and all the way out. A value that never moves is a constant we
can hand Blender; one that moves is a function we have to model, and either
answer is worth having.

Addresses are RVAs off the module base at run time, so ASLR is handled the way
`keytap.py` handles it -- never a hardcoded 0x00C078C4.
"""

import argparse
import math
import os
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))

import keytap  # noqa: E402

#: Preferred base of the pinned build; every address below is quoted as the VA
#: a disassembler shows and converted to an RVA here.
IMAGE_BASE = 0x00400000
VA_FOV = 0x00C078C4          # GmView.cpp's frustum arg 4
VA_POSITION = 0x00C07860     # printed as `Position = %f, %f, %f`
VA_TARGET = 0x00C0786C       # printed as `Target = %f, %f, %f`
#: The far plane the frustum builder loads as a literal, 0x00946EBC.
FAR_PLANE = 48000.0


def find_pid(image="Gw.exe"):
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}",
                          "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return max(pids) if pids else None


def sample(pid, base):
    def f32(va, n=1):
        raw = keytap.read_at(pid, base + (va - IMAGE_BASE), 4 * n)
        if raw is None or len(raw) < 4 * n:
            return None
        return struct.unpack(f"<{n}f", raw)
    fov = f32(VA_FOV)
    pos = f32(VA_POSITION, 3)
    tgt = f32(VA_TARGET, 3)
    return (fov[0] if fov else None, pos, tgt)


def describe(fov):
    """Every reading of one float, because which one it is is NOT established."""
    out = []
    for label, full in (("as a FULL angle", fov), ("as a HALF angle", fov * 2)):
        deg = math.degrees(full)
        # Blender's lens for a 36 mm sensor: f = (sensor/2) / tan(angle/2)
        lens = (36.0 / 2.0) / math.tan(full / 2.0) if 0 < full < math.pi else None
        out.append(f"    {label}: {deg:7.3f} deg"
                   + (f"   -> Blender lens {lens:6.2f} mm (36 mm sensor)"
                      if lens else "   -> outside a sane range"))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--watch", type=float, default=0.0,
                    help="sample for this many seconds and report the RANGE, "
                         "which is what decides fixed-vs-varying")
    ap.add_argument("--interval", type=float, default=0.25)
    args = ap.parse_args(argv)

    pid = find_pid()
    if not pid:
        raise SystemExit("[FAIL] no Gw.exe running")
    base = keytap.module_base(pid, "Gw.exe")
    if not base:
        raise SystemExit(f"[FAIL] no Gw.exe module base in pid {pid}")
    print(f"[ok] pid {pid}, Gw.exe base 0x{base:08X} "
          f"(preferred 0x{IMAGE_BASE:08X}, slide {base - IMAGE_BASE:+#x})")

    fov, pos, tgt = sample(pid, base)
    if fov is None:
        raise SystemExit("[FAIL] could not read the fov global")
    print(f"[ok] fov  = {fov!r} rad")
    print(describe(fov))
    print(f"[ok] position = {pos}")
    print(f"[ok] target   = {tgt}")
    print(f"[ok] far plane (static literal, 0x00946EBC) = {FAR_PLANE}")
    if fov == 0.0:
        print("[WARN] fov is 0.0 -- the client asserts this cannot happen in a "
              "built frustum, so the camera is probably not up yet "
              "(character select, loading). Sample again in a map.")

    if args.watch <= 0:
        return 0

    print(f"\n[ok] watching {args.watch:.0f}s -- MOVE THE CAMERA: hold still, "
          f"then zoom fully in and fully out")
    seen = {}
    t0 = time.time()
    while time.time() - t0 < args.watch:
        f, _p, _t = sample(pid, base)
        if f is not None:
            seen[round(f, 6)] = seen.get(round(f, 6), 0) + 1
        time.sleep(args.interval)
    if not seen:
        raise SystemExit("[FAIL] no samples")
    lo, hi = min(seen), max(seen)
    print(f"[ok] {sum(seen.values())} samples, {len(seen)} distinct value(s)")
    print(f"     min {lo!r} rad = {math.degrees(lo):.3f} deg")
    print(f"     max {hi!r} rad = {math.degrees(hi):.3f} deg")
    if len(seen) == 1:
        print("  => FIXED across this run. One number Blender can take.")
    else:
        print("  => it VARIES. The field of view is a function, not a "
              "constant, and gwcam.py needs the rule rather than a lens.")
        for v, n in sorted(seen.items())[:12]:
            print(f"       {v!r} rad = {math.degrees(v):7.3f} deg   x{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
