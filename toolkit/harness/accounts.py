"""Which account a launch logs in as — chosen explicitly, never inherited.

THE PROBLEM. The Guild Wars client autofills a saved credential, so every automated run
this project has ever done logged in as **the owner's real primary account**. Against our
own webgate that looked harmless, and it is how the credential ended up in 206 capture
records: `toolkit/portal/webgate.py` does not check the password, but it does record what
the client sent, and the client sent the real one.

It stops being harmless the moment a launch can reach the live service. `PLAN.md` §7 Q4
authorizes automation on a SECONDARY account; nothing in the launch path had any concept
of an account at all, so "never automate on the primary" was an intention rather than a
control. This module is the control.

THE THREE RULES, enforced here rather than remembered:

1. **Loopback runs use a synthetic credential and no real one.** Our webgate says yes to
   anyone — its own comment says so — so a real account buys nothing and costs a
   credential in the capture. `synthetic()` needs no vault file and no secret.
2. **A live run must NAME its account, and the account must be marked for automation.**
   No default, because a default is how the primary gets used by accident.
3. **An account not marked `automation: true` is REFUSED**, and the message says which
   accounts are eligible. The owner's primary is expected to sit in the same file with
   the flag absent, so the refusal is the normal state for it rather than a special case.

WHERE THE SECRETS LIVE. `vault/keys/accounts.json`, gitignored like the rest of the
vault, resolved through `toolkit/vaultpath.py` so a worktree finds the one vault. Never
in the repo, never in a conversation, never printed. The file does not exist until the
owner writes it, and its absence is a clear error rather than a fallback:

    {
      "primary":  {"email": "...", "password": "...",
                   "note": "the owner's own account. No automation flag: refused."},
      "capture":  {"email": "...", "password": "...", "automation": true,
                   "note": "the secondary bought 2026-08-06 for the capture campaign"}
    }

ON PASSING A PASSWORD ON THE COMMAND LINE. The client's own argument table carries
`email`, `password` and `autologin` **[measured — toolkit/clientscan/argtable.py, build
38797]**, and that is the only unattended-login mechanism it offers. The cost is that an
argv is visible to any process that can read the process list on this machine. That is a
real exposure and it is accepted deliberately for the LOCAL machine, because the
alternative — leaving autofill in charge — means the primary account's credential instead
of a synthetic or secondary one. What is NOT accepted is that exposure spreading: `redact`
below exists because `drive_client.py` and `session.py` both print their argv and
`session.py` writes it into a run manifest, and a password belongs in neither.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import vaultpath  # noqa: E402

ACCOUNTS_FILE = ("keys", "accounts.json")

# The credential used against our own server. Not a secret, not an account, and
# deliberately in an unregistrable domain so it cannot collide with a real login.
# `.invalid` is reserved for exactly this by RFC 2606.
SYNTHETIC = {
    "label": "synthetic",
    "email": "loopback@rurik.invalid",
    "password": "not-a-real-password",
    # Our loopback server serves exactly one character (authsrv.TEST_CHAR_NAME). Naming it
    # with -character is what turns -email/-password into an actual auto-login: the client's
    # own rule (wiki UPSTREAM, corroborated -- `character` is in the arg table, MEASURED
    # argtable.py) is that -password auto-logs-in only WITH -character and -email. Without
    # it the login screen comes up with an empty password field and a dead Log In button,
    # which is exactly what we saw. With it, the client goes straight into the world.
    "character": "Test Warrior",
    "automation": True,
    "live": False,
}

SECRET_KEYS = ("password",)
# Written to a FILE, the bar is higher than written to a terminal. toolkit/scrub_captures.py
# already counts `email` as a secret -- the scrubber exists because 206 capture records
# carried the owner's address -- and a run manifest sitting in vault/captures is the same
# kind of file. It is not covered by the same sweep, though: the scrubber matches JSON
# KEYS, and in a manifest the address is a VALUE inside an argv list, so `-email
# someone@example.com` would survive a tree-wide scrub untouched.
#
# The console keeps the address on purpose (test_accounts.py pins that: it is how a run
# is identified while you are watching it), so the two audiences get two functions rather
# than one compromise.
FILE_SECRET_KEYS = ("password", "email")


class AccountError(SystemExit):
    """Refusing to launch. Never a warning."""


def synthetic():
    """The credential for a run against our own server. No vault file needed."""
    return dict(SYNTHETIC)


def _read():
    path = vaultpath.vault_path(*ACCOUNTS_FILE)
    if not os.path.isfile(path):
        raise AccountError(
            f"no account file at {path}\n"
            f"  A live run must name a real account, and this project never stores one\n"
            f"  in the repo or accepts one on a prompt. Create that file yourself:\n"
            f"      {{\"capture\": {{\"email\": \"...\", \"password\": \"...\",\n"
            f"                    \"automation\": true}}}}\n"
            f"  It is under vault/, so the provenance gate and the gitignore already\n"
            f"  cover it. Do not add the primary account's automation flag.")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise AccountError(f"{path}: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise AccountError(f"{path}: expected a non-empty object of label -> account")
    return data, path


def load(label):
    """One account by label, with its fields validated. Does not check eligibility."""
    data, path = _read()
    if label not in data:
        raise AccountError(
            f"no account labelled {label!r} in {path}\n"
            f"  known labels: {', '.join(sorted(data))}")
    acct = dict(data[label])
    for field in ("email", "password"):
        if not str(acct.get(field) or "").strip():
            raise AccountError(f"account {label!r} in {path} has no {field}")
    acct["label"] = label
    return acct


def for_automation(label):
    """An account cleared for automated login, or a refusal naming what is eligible.

    The eligibility flag is opt-IN and per account. An account with no flag is refused,
    which makes the owner's primary refused by default rather than by remembering to
    exclude it -- the failure mode that matters is adding a new account and forgetting,
    and this way forgetting is safe.
    """
    acct = load(label)
    if not acct.get("automation"):
        data, path = _read()
        eligible = sorted(k for k, v in data.items()
                          if isinstance(v, dict) and v.get("automation"))
        raise AccountError(
            f"REFUSING to automate as account {label!r}\n"
            f"  It is not marked for automation in {path}.\n"
            f"  PLAN.md §6.2 and §7 Q4: automation runs on the SECONDARY account. The\n"
            f"  owner's primary is expected to live in this file with no automation\n"
            f"  flag, so this refusal is its normal state.\n"
            f"  Eligible: {', '.join(eligible) if eligible else 'none -- no account is flagged'}")
    return acct


def for_target(host, label=None):
    """The account to launch with, decided by where the client is being pointed.

    Loopback gets the synthetic credential unless a label is forced, because our own
    webgate says yes to anyone and a real credential there is pure downside. Anything
    else must name an automation-eligible account -- there is no default, since a
    default is exactly how the primary would get used by accident.
    """
    if _is_loopback(host):
        return for_automation(label) if label else synthetic()
    if not label:
        raise AccountError(
            f"REFUSING to launch at {host!r} with no account named.\n"
            f"  That is not a loopback address, so this is a LIVE run, and a live run\n"
            f"  must say which account it is. There is no default on purpose: the\n"
            f"  client autofills the owner's primary, and inheriting that is the\n"
            f"  failure this check exists to prevent.\n"
            f"  Pass --account <label>.")
    return for_automation(label)


def _is_loopback(host):
    parts = str(host).split(".")
    return (len(parts) == 4 and parts[0] == "127"
            and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts))


def login_args(acct):
    """The client flags that log this account in without touching the saved one.

    MEASURED (toolkit/clientscan/argtable.py, build 38797): `email`, `password`,
    `character` and `autologin` are all in the client's own 41-entry argument table.

    `-character` is what makes it an AUTO-login rather than a pre-filled login screen: the
    client auto-logs-in only when -password is paired with -character and -email. An
    account with a `character` gets all three and goes straight into the world; one without
    gets the login screen (a live account that has not named its character, say).
    """
    args = ["-email", acct["email"], "-password", acct["password"]]
    if str(acct.get("character") or "").strip():
        # -character selects the account's character and -autologin carries it INTO the
        # world -- but only while the client window is the active foreground one: GW does
        # not advance an inactive window past character select, which is why -autologin
        # alone looked like it did nothing until the harness started raising the window.
        # MEASURED both are in the client's arg table (argtable.py). The driver's job is
        # then just to keep the window foreground until it enters -- no click, no
        # coordinates (session.py `_play`).
        args += ["-character", acct["character"], "-autologin"]
    return args


def redact(argv):
    """A copy of argv safe to print, log, or write into a manifest.

    Exists because both launch sites print their argv and session.py stores it. A
    password that is merely 'not supposed to be logged' ends up logged.
    """
    return _redact(argv, SECRET_KEYS)


def redact_for_file(argv):
    """A copy of argv safe to write to disk. Strictly more redacted than redact().

    Use this for anything persisted. drive_client.py's report.json stored the RAW argv
    -- password and all -- while the console print of the same list two lines later was
    redacted; found 2026-08-06, before a real automation account had ever used it.
    """
    return _redact(argv, FILE_SECRET_KEYS)


def _redact(argv, keys):
    out = list(argv)
    for i, a in enumerate(out[:-1]):
        if isinstance(a, str) and a.lower().lstrip("-") in keys:
            out[i + 1] = "<redacted>"
    return out


def describe(acct):
    """One line naming the account, without its secret."""
    kind = "synthetic" if acct.get("label") == "synthetic" else "vault"
    return f"{acct['label']} ({kind}) <{acct['email']}>"
