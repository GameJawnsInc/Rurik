"""Follow the servers' capture files while they are being written, so a run can
assert on what the client actually said the moment it says it.

progress.py already established the principle: run state is read from the
capture ladder, not from pixels, because two runs produced byte-identical
screenshots while stopping at different rungs. What it cannot do is tell a run
IN FLIGHT how far the client has got -- drive_client lingers a fixed 25 s and
hopes. This module closes that gap: a verb like "log in" advances the moment
the capture shows the client's own message and fails loudly when the deadline
passes without it.

The unit is the Recorder's jsonl line (one event per line, flushed per event,
one file per connection). A tail opened BEFORE the client launches sees only
files created after it -- files already present belong to earlier sessions,
and matching against them would let last week's successful login satisfy
today's assertion, which is exactly the check-that-cannot-fail the house rules
forbid.
"""

import glob
import json
import os
import time


def by(**want):
    """Predicate over an event dict: by(kind="decoded", name="PORTAL_ACCOUNT_LOGIN").

    Missing keys never match -- an event with no "channel" field is not evidence
    about any channel.
    """
    def pred(ev):
        return all(ev.get(k) == v for k, v in want.items())
    return pred


class CaptureTail:
    """Incremental reader over every *.jsonl that APPEARS in the given dirs."""

    def __init__(self, *dirs):
        self.dirs = [d for d in dirs if d]
        # Snapshot what already exists so it can be excluded. The dirs may not
        # exist yet -- the Recorder creates them on first connection.
        self._old = set(self._glob())
        self._buf = {}       # path -> (byte offset, partial trailing line)
        self.events = []     # every event seen, in arrival order, with _file set

    def _glob(self):
        out = []
        for d in self.dirs:
            out.extend(glob.glob(os.path.join(d, "*.jsonl")))
        return out

    def poll(self):
        """Read whatever is new. Returns the newly seen events."""
        fresh = []
        for path in self._glob():
            if path in self._old:
                continue
            off, part = self._buf.get(path, (0, ""))
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(off)
                    chunk = f.read()
                    off = f.tell()
            except OSError:
                continue                 # mid-create; next poll gets it
            text = part + chunk
            # The writer flushes whole lines, but a read can still land mid-write.
            # Carry the unterminated tail instead of json-failing on half a line.
            lines = text.split("\n")
            part = lines.pop()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ev["_file"] = path
                fresh.append(ev)
            self._buf[path] = (off, part)
        self.events.extend(fresh)
        return fresh

    def wait_for(self, pred, timeout, since=0, interval=0.05):
        """First event matching pred at index >= since, or None on deadline.

        Returns (event, next_index). `since` is how a caller enforces order:
        pass the index returned by the previous checkpoint and an event from
        before it can never satisfy this one, so a ladder walked out of order
        is reported as the failure it is.
        """
        deadline = time.monotonic() + timeout
        while True:
            self.poll()
            for i in range(since, len(self.events)):
                if pred(self.events[i]):
                    return self.events[i], i + 1
            if time.monotonic() >= deadline:
                return None, since
            time.sleep(interval)

    def files(self):
        """The capture files this run produced, for the report."""
        return sorted(self._buf)
