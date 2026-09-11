"""The live driver's two refusal classes: a run that was stopped, and a stream that was not.

Split out of `toolkit/harness/livesession.py`, where both were defined and where both are
still re-exported at the site they used to occupy -- `livesession.LiveError` and
`livesession.SplitError` keep working, and `toolkit/harness/dryrun_keycapture.py` and
`toolkit/harness/test_livesession.py` read them under those names.

This module imports NOTHING, on purpose. Everything that raises these -- the preflight
gates, the key ring, the plan seal, the stream splitters -- sits downstream of a
packet-capture backend, a key-tapped binary or a vault; a module that only has to say
"refused" must not drag any of that in to say it. That also means a leaf which raises a
refusal can take this dependency without inheriting the live driver's import cost.

The referents of the docstrings below stay in `livesession.py`: "before the account is
used" is `preflight()` and the `--mode` gate in `run()`, and "never guessed past" is
`split_c2s` / `split_s2c`, which parse the handshake rather than trusting an offset.
"""


class LiveError(SystemExit):
    """A live run was refused. The whole point is that it stops before the account is used."""


class SplitError(Exception):
    """A captured stream did not begin with the handshake we require. Never guessed past."""
