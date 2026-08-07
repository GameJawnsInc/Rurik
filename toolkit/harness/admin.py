"""Send one named action to the long-lived elevated runner and wait for its reply.

Exists so firewall work costs a single UAC prompt per session. The runner accepts
only a fixed set of action names -- see admin_runner.ps1 for why that allowlist is
the security boundary rather than a convenience.

    python toolkit/harness/admin.py rules
    python toolkit/harness/admin.py cage-on
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vaultpath import vault_path  # noqa: E402

# admin_runner.ps1 hardcodes the same directory on its side; if RURIK_VAULT ever
# points the python half elsewhere, the runner stops seeing requests -- the
# stale .req files this leaves behind are the visible symptom.
QUEUE = vault_path("admin-queue")
# cage-off was removed from the runner 2026-08-06 -- uncaging is a deliberate elevated
# act now, not a queue message. See admin_runner.ps1 for why.
ACTIONS = ("cage-on", "launch-caged", "rules", "stop")


def send(action, timeout=180.0):
    if not os.path.isdir(QUEUE):
        raise SystemExit(f"No queue at {QUEUE} -- is the elevated runner started?\n"
                         f"  toolkit/harness/admin_runner.ps1, once, as admin.")
    ident = uuid.uuid4().hex[:12]
    req = os.path.join(QUEUE, ident + ".req")
    res = os.path.join(QUEUE, ident + ".res")
    with open(req, "w", encoding="utf-8") as f:
        f.write(action)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(res):
            time.sleep(0.15)          # let the writer finish
            # utf-8-sig: PowerShell's -Encoding utf8 writes a BOM, which otherwise
            # arrives as a leading U+FEFF and then fails to print on a cp1252
            # console -- a reply that worked, reported as a crash.
            with open(res, encoding="utf-8-sig", errors="replace") as f:
                out = f.read()
            os.remove(res)
            return out
        time.sleep(0.2)

    # Leave the request in place: if the runner is merely slow it will still run,
    # and a stale .req is a visible symptom rather than a silent no-op.
    raise SystemExit(f"No reply for {action!r} within {timeout:.0f}s. "
                     f"Is the elevated runner still running?")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ACTIONS:
        raise SystemExit(f"usage: admin.py <{'|'.join(ACTIONS)}>")
    out = send(sys.argv[1])
    # The console here is cp1252; box-drawing and dashes from PowerShell
    # tables would otherwise raise instead of printing.
    print(out.encode("ascii", "replace").decode("ascii"))
