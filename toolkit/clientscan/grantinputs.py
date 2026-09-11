#!/usr/bin/env python3
r"""The vault inputs and the refusal -- where a capture comes from, whether it
is ours, and the deferred handle on the server.

The five names `grantsim.py` and `field4screen.py` both need before either of
them can open anything: the refusal that is raised instead of printing a number
about nothing, the two vault path resolvers (`captures/gamesrv` for a capture,
`captures/movetap` for a tap), the origin gate that refuses a pooled corpus, and
the FIRST-USE handle on the real server module.

POINTER, because one docstring that moved here names a referent that stayed
behind. `_authsrv`'s "See deviation (1) in the module docstring" means
**`grantsim.py`'s** module docstring, deviation (1) -- the note that argues why
REALFIX-C3 imports the server at all rather than scoring a paraphrase of its
predicate. That argument is about `grantsim.py` and stays there; only the
handle moved.

WHY A LEAF RATHER THAN A HELPER LEFT IN `grantsim.py`. `field4screen.py` reads
exactly these five names out of `grantsim.py` and nothing else, and
`grantsim.py` runs as `python toolkit/clientscan/grantsim.py` -- module
`__main__`. A leaf that imported it back would load a SECOND copy of it whose
flags `main()` never set. The names move here instead and both files import
them.

`_AUTHSRV` is a MUTABLE MEMO and is deliberately re-exported NOWHERE: a
`from grantinputs import _AUTHSRV` binds the `None` it holds at import time and
never sees the memo fill, so the second copy is permanently stale. Callers use
`_authsrv()`.

READS ONLY, like its origin, and nothing here runs at import time: `_authsrv()`
defers the server's whole import chain to first use, and both path resolvers
touch the vault only when they are called.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLKIT = os.path.dirname(HERE)
if _TOOLKIT not in sys.path:
    sys.path.insert(0, _TOOLKIT)

import origin                                                  # noqa: E402
import vaultpath                                               # noqa: E402


class Refused(SystemExit):
    """This file refuses to print a number about nothing. See each raise site."""


def capture_path(stamp):
    root = vaultpath.require_dir(
        "captures", "gamesrv",
        why="REALFIX-H1 replays OUR captures' own c2s control stream; with no "
            "captures there is nothing to replay and no number to print")
    p = os.path.join(root, "authsrv-%s-c1.jsonl" % stamp)
    if not os.path.isfile(p):
        raise Refused(f"grantsim: no capture for {stamp} at {p}")
    return p


def movetap_path(name):
    root = vaultpath.require_dir(
        "captures", "movetap",
        why="REALFIX-C1 checks the forward model against a DIRECT MEMORY READ "
            "of the SYNC array; without it the model is unvalidated arithmetic")
    p = os.path.join(root, name)
    if not os.path.isfile(p):
        raise Refused(f"grantsim: no movetap trace at {p}")
    return p


def require_ours(paths, what="a grantsim measurement"):
    """Every path must be OURS, or raise. Pooling is a bug, not a wider sample.

    Delegates to `origin.require_single`, which raises `origin.MixedCorpora`.
    Retail is not an input to this file at all -- it has no `ours` grant stream
    to counterfactual against -- so there is no `want=` parameter to get wrong.
    """
    return origin.require_single(paths, want=origin.OURS, what=what)


_AUTHSRV = None


def _authsrv():
    """The REAL server module, imported on FIRST USE and never at import time.

    See deviation (1) in the module docstring. `test_bareimport.py` proves
    `import authsrv` succeeds with no vault, so this is safe wherever it is
    reached -- but it is still deferred, because a scanner that only wants
    `derive_match_radius()` should not pay for the server's import chain.
    """
    global _AUTHSRV
    if _AUTHSRV is None:
        srv = os.path.join(os.path.dirname(HERE), "authsrv")
        if srv not in sys.path:
            sys.path.insert(0, srv)
        import authsrv as A                                    # noqa: PLC0415
        _AUTHSRV = A
    return _AUTHSRV
