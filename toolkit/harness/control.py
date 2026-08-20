"""A one-slot mailbox from the harness's action script to the running gamesrv.

    from harness import control
    control.request_interact(99)     # driver side
    agent = control.take_interact()  # server side, read-and-clear

WHY THIS EXISTS, and what it is NOT. Driving a quest through its states needs
the player to TALK TO a specific NPC, and the harness's only way to do that was
a click at a guessed screen position. That was attempted three times against two
NPCs and produced no interaction at all: the projection from world coordinates
to screen depends on a camera whose yaw the harness does not know and which
faces a different way each run. The failure is not subtle -- it is silent, and
looks exactly like the server ignoring the click.

**THIS DOES NOT SYNTHESISE INPUT AND MUST NEVER BE DESCRIBED AS A CLICK.** It
asks the SERVER to run its own `0x0039 INTERACT_AGENT` arm for a named agent, as
if the client had asked. So:

  * everything DOWNSTREAM is real -- the dialog messages go out on the real
    wire, the real client renders them, and what appears on screen is the same
    thing a click would have produced;
  * everything UPSTREAM is not -- no click happened, the client sent no
    `0x0039`, and this proves NOTHING about the client's own interact path.

That distinction is the whole reason this module has a docstring this long. The
client's interact path is separately OBSERVED -- 29 `0x0039` messages in the
live corpus, and a real click produced one against our own server in the Q4 run
-- so nothing is being papered over. But a run driven through here must say so,
and `session.py` prints a line to that effect every time the verb fires.

ONE SLOT, LAST WRITE WINS, and deliberately: a queue would let a script get
ahead of a server that is mid-dialog and deliver a burst of interacts with no
relation to what is on screen. A single slot makes the action script's timing
the thing that has to be right, which is where the operator can see it.

The mailbox is a file because the two halves are separate PROCESSES started at
different times by different code paths, and a file needs no port, no
handshake, and no cleanup if one side dies. It lives in the vault, which both
halves already resolve the same way.

Standard library only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vaultpath import vault_path  # noqa: E402

SLOT = os.path.join(vault_path("harness-control"), "interact")
# A SECOND SLOT, for ORDERING AN ATTACK, added 2026-08-20 for the same reason
# and with the same caveat. Watching a damage number needs the player to swing,
# the player swings when the client sends `0x0026 ATTACK_AGENT`, and the client
# sends that when someone CLICKS A HOSTILE -- a world-anchored click, which is
# the one thing the paragraph above says this harness cannot do. `interact`
# could not stand in: its server arm is `_handle_interact`, which is the NPC
# dialog path and deliberately never begins an attack (0 of 10 distinct 0x0039
# targets on ArenaNet's wire enter an auto-attack exchange, and authsrv.py's
# INTERACT_AGENT arm carries that measurement).
#
# Separate slot rather than a shared one, because "talk to it" and "hit it" are
# different orders and a run should not be able to fire one meaning the other.
ATTACK_SLOT = os.path.join(vault_path("harness-control"), "attack")


def _ensure_dir():
    os.makedirs(os.path.dirname(SLOT), exist_ok=True)


def request_interact(agent_id):
    """Driver side: ask the server to interact with `agent_id`."""
    _ensure_dir()
    tmp = SLOT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(str(int(agent_id)))
    # Replace rather than write in place: the reader polls, and a half-written
    # file would parse as a different agent id or as nothing.
    os.replace(tmp, SLOT)


def request_attack(agent_id):
    """Driver side: ask the server to ORDER AN ATTACK on `agent_id`.

    Same contract as request_interact and the same honesty requirement: the
    server runs its own `begin_attack`, exactly what the ATTACK_AGENT arm
    calls, so everything downstream -- the swing timer, the armour term, the
    critical, the damage property on the wire, the number the client draws --
    is real. What did not happen is the CLICK, and with it the client's own
    decision to send 0x0026. That decision is separately OBSERVED (four of
    them at our own Hatcher in one labelled run, 2026-08-11).
    """
    _ensure_dir()
    tmp = ATTACK_SLOT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(str(int(agent_id)))
    os.replace(tmp, ATTACK_SLOT)


def take_attack():
    """Server side: the pending attack target, or None. Read-and-clear."""
    try:
        with open(ATTACK_SLOT, encoding="utf-8") as fh:
            raw = fh.read().strip()
    except FileNotFoundError:
        return None
    try:
        os.remove(ATTACK_SLOT)
    except OSError:
        pass
    try:
        return int(raw)
    except ValueError:
        return None


def take_interact():
    """Server side: the pending agent id, or None. Clears the slot.

    Read-and-clear so one request fires once. A request that arrived while the
    server was not looking is simply the most recent one, which is the "last
    write wins" contract above.
    """
    try:
        with open(SLOT, encoding="utf-8") as fh:
            raw = fh.read().strip()
    except FileNotFoundError:
        return None
    try:
        os.remove(SLOT)
    except OSError:
        pass
    try:
        return int(raw)
    except ValueError:
        return None


def clear():
    """Drop any stale request. Called at session start.

    A leftover slot from a killed run would fire an interact into the next
    session's first seconds, which is the kind of ghost that gets blamed on the
    protocol.
    """
    for slot in (SLOT, ATTACK_SLOT):
        try:
            os.remove(slot)
        except OSError:
            pass
