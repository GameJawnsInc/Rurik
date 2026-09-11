"""deploy's own refusal -- the exception class `deploy.py` raises and catches.

WHY THIS IS ITS OWN MODULE AND NOT A SHARED ONE. Four modules under
`toolkit/mapdata/` each define a class called `Refused`: `datalloc.py`,
`datmove.py`, `mapscale.py` and `deploy.py`. THAT SEPARATION IS THE CHECK.
`test_deploy.py` §10(e2) asserts TYPE identity -- `type(exc) is deploy.Refused`
-- because `deploy.__main__` catches `deploy.Refused` and nothing else, so a
raw `datalloc.Refused` escaping the create path reaches the operator as a
traceback rather than as a remedy. Its own comment says why the weaker check
would not do: "both classes are called `Refused`, so the bare name reads
identically whichever one was raised."

So this file is named for `deploy`, not for `mapdata`. A neutrally-named
shared `maprefuse.py` would be an open invitation to migrate the other three
onto it, and the day that happened §10(e2) would pass vacuously against every
refusal in the package. `datalloc`, `datmove` and `mapscale` keep theirs ON
PURPOSE.

One thing this move CHANGES, and it changes in the safe direction. Until now
`python toolkit/mapdata/deploy.py` ran deploy as `__main__` while
`propscan.py` and `tilerender.py` lazily `import deploy`, giving the process
two distinct classes both called `deploy.Refused` -- a refusal raised through
the second copy would not have been caught by `__main__`'s handler. Both
copies now import this module, so there is exactly one class. Nothing in the
suite was measuring the old split; it is stated here so nobody discovers it.
"""


class Refused(Exception):
    """A stage refused. The message says which and why."""
