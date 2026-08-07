"""Proves the account selector refuses, and that a loopback run needs no real account.

Two failures this guards, and both have already happened in some form:

  * Every automated run logged in as the owner's PRIMARY account, because the client
    autofills and nothing in the launch path had any concept of an account. That is how
    the real credential reached 206 capture records.
  * A live run is now possible (PLAN.md §7 Q4). "Never automate on the primary" was an
    intention with nothing enforcing it.

So the assertions are mostly refusals, and the eligibility flag is opt-IN: an account
with no `automation` flag is refused. That way forgetting to exclude a new account is
safe, which is the opposite of a blocklist.

    python toolkit/harness/test_accounts.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import vaultpath  # noqa: E402
import accounts  # noqa: E402

# 4 synthetic/loopback + 6 refusal + 3 redaction + 2 eligibility = 15, measured green.
LEDGER = checks.Ledger("account selector", floor=15)


def refused(fn, *a):
    try:
        fn(*a)
        return False
    except SystemExit:
        return True


class fake_vault:
    """Point vaultpath at a temp dir. It caches, so the cache has to be cleared."""

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="rurik-acct-")
        if self.payload is not None:
            os.makedirs(os.path.join(self.tmp, "keys"), exist_ok=True)
            with open(os.path.join(self.tmp, "keys", "accounts.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(self.payload, fh)
        self.saved_env = os.environ.get("RURIK_VAULT")
        os.environ["RURIK_VAULT"] = self.tmp
        vaultpath._resolved = None
        return self.tmp

    def __exit__(self, *exc):
        if self.saved_env is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = self.saved_env
        vaultpath._resolved = None
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


PRIMARY = {"email": "owner@example.com", "password": "hunter2",
           "note": "no automation flag -- must be refused"}
CAPTURE = {"email": "capture@example.com", "password": "s3cret", "automation": True}


def main():
    # --- a loopback run needs no vault file and no real account ------------------
    with fake_vault(None):
        acct = accounts.for_target("127.0.0.1")
        LEDGER.ok(acct["label"] == "synthetic",
                  "a loopback run with no --account uses the synthetic credential",
                  accounts.describe(acct))
        LEDGER.ok(acct["email"].endswith(".invalid"),
                  "and its address is in an unregistrable domain",
                  "RFC 2606 .invalid -- cannot collide with a real login")
        LEDGER.ok(accounts.for_target("127.0.0.3")["label"] == "synthetic",
                  "any 127/8 alias counts as loopback", "the gamesrv host is 127.0.0.3")

        # ...and the absence of the vault file is not a silent fallback for a live run.
        LEDGER.ok(refused(accounts.for_target, "1.2.3.4", "capture"),
                  "a live run with no account file is REFUSED")

    # --- the refusals that matter -------------------------------------------------
    with fake_vault({"primary": PRIMARY, "capture": CAPTURE}):
        LEDGER.ok(refused(accounts.for_target, "1.2.3.4"),
                  "a NON-loopback target with no --account is REFUSED",
                  "there is no default, because a default would be the primary")
        LEDGER.ok(refused(accounts.for_automation, "primary"),
                  "an account with no automation flag is REFUSED",
                  "the owner's primary, and this is its normal state")
        LEDGER.ok(refused(accounts.for_automation, "nosuch"),
                  "an unknown label is REFUSED")

        try:
            accounts.for_automation("primary")
            msg = ""
        except SystemExit as exc:
            msg = str(exc)
        LEDGER.ok("capture" in msg,
                  "and the refusal names which accounts ARE eligible",
                  "so the fix is obvious without reading the source")
        LEDGER.ok("hunter2" not in msg and "s3cret" not in msg,
                  "no refusal message ever contains a password")

        acct = accounts.for_automation("capture")
        LEDGER.ok(acct["email"] == "capture@example.com",
                  "an account marked for automation is accepted",
                  accounts.describe(acct))
        LEDGER.ok(accounts.for_target("1.2.3.4", "capture")["label"] == "capture",
                  "and a live target with that account resolves")
        LEDGER.ok(refused(accounts.for_target, "1.2.3.4", "primary"),
                  "while a live target with the PRIMARY is REFUSED",
                  "this is the check the whole module exists for")

        # A malformed row is refused rather than half-used.
        with fake_vault({"broken": {"email": "x@y.z", "automation": True}}):
            LEDGER.ok(refused(accounts.load, "broken"),
                      "an account missing its password is REFUSED, not half-loaded")

    # --- redaction, because both launch sites print their argv --------------------
    acct = accounts.synthetic()
    argv = ["-authsrv", "127.0.0.1"] + accounts.login_args(acct)
    red = accounts.redact(argv)
    LEDGER.ok("-password" in red and acct["password"] not in red,
              "redact removes the password from an argv", " ".join(red))
    LEDGER.ok(acct["email"] in red,
              "but keeps the email, which is how a run is identified afterwards")
    LEDGER.ok(len(red) == len(argv) and argv[0] == red[0],
              "and does not otherwise change the argv")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
