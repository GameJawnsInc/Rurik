# The capture writer — `authsrv.Recorder`, and what it promises the threads that write to it

**2026-09-18.** `Recorder` (`toolkit/authsrv/authsrv.py`, one per connection) is the
per-connection capture: an `authsrv-<stamp>-c<n>.jsonl` of events and a `.raw` sidecar of
c2s ciphertext, opened by `handle()` on connect and closed in its `finally`. Its readers
are `replay.py`, `movesync.load_wire_reports`, `timingjoin.py` and every corpus test over
`vault/captures/`. This file is where its contract with the threads that write to it is
written down, because until today that contract lived in one property's docstring and
was half of the defence it described.

**Identifiers.** `RECORDER-D<n>` = a defect of the capture writer: the symptom, the
mechanism, the fix and the check that pins it. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

Claim labels are the vocabulary in [../character/FINDINGS.md](../character/FINDINGS.md).
Everything here is about our own code and is OBSERVED in the tree and in the harness logs
it names; nothing here is a claim about the client.

---

## The contract

- **Three writer threads are the model, not one.** `send()` is called from the receive
  loop, the world tick and any probe; the tape player and the labelled run write through
  `rec.event` on threads of their own. The capture line is written OUTSIDE the send lock on
  purpose (`send()`'s own comment: serialising the 20 Hz ticker against the filesystem was
  the alternative, and the `seq` counter is what keeps keystream order recoverable), so the
  recorder is reached concurrently by design.
- **Teardown joins nothing.** `handle(sock, addr, keys, vault, conn_id, stop, …)`'s `stop`
  is the SERVER's shutdown event (`main()` sets it on KeyboardInterrupt), not a
  per-connection one; the world tick's thread handle is not kept; the tape, label and probe
  threads are daemon threads expected to notice on their own that the connection is gone —
  the tick by `OSError` from `sendall`, the labelled run by asking `rec.closed` before it
  starts. That is the pattern every per-connection resource follows, and D1's fix follows
  it rather than adding a join.
- **A write after `close()` is dropped and counted, never raised** (D1). `closed` remains
  the right question for a thread with a whole run to skip. It cannot protect a single
  write, because the handler can close between the ask and the write.

## RECORDER-D1 — the teardown window: a tick's `sent` row on a closed file

| | |
|---|---|
| **Symptom** | `Exception in thread Thread-N (world_tick)` … `authsrv.py, in event: self.meta.write(...)` … `ValueError: I/O operation on closed file`, in `gamesrv.log`, always after the client's own `ConnectionResetError`. |
| **Where** | 19 of 1,654 harness logs (`vault/captures/harness/*/gamesrv.log`, counted 2026-09-18). 16 name `world_tick` — 2026-08-13 to 2026-09-18, the last two `20260918T170928` and `20260918T172315`, 2 of that day's 19 runs, one log (`20260914T115833`) with two tick threads. 3 name `_tape_then_labels`, all 2026-08-10: the case the `closed` property was added for, and closed by its ask. |
| **Mechanism** | `handle()`'s `finally` runs `report_unhandled`, `report_ping`, `rec.close()`, then `sock.close()`. The tick loops `while not stop.is_set()` and leaves only on `OSError` from `send`. A `sendall` that lands between the two closes succeeds — the socket is still ours — so `send` goes on to `rec.event("sent", …)`, which writes to the closed file. `ValueError` is not `OSError`, so the tick's guard misses it and the thread dies with the traceback. Swapping the two closes narrows the window and does not close it: a `sendall` that completed just before `sock.close()` still records after `rec.close()`, and the handler's own `except` writes `rec.event("error")` after the socket has already failed, so the recorder has to outlive the socket anyway. |
| **Fix** | At the recorder, matching the contract's second bullet. `event` asks `meta.closed` first and drops; the write itself is then wrapped for the one-line residual (closed between the ask and the write) and drops the same way, with `json.dumps` outside the wrap so a circular reference is still heard. `frame` asks — its only caller is the receive loop, on the same thread that later closes, so the ask is sufficient there. Drops are counted in `rec.dropped`; the first is printed once, with the connection id and the kind, and the rest are counted, not printed, because the tick runs at 20 Hz. `closed`'s docstring now says which half of the defence it is. `handle()`, `send()` and `world_tick` are untouched. |
| **What was never wrong** | The capture. The file was closed before the row arrived, so the row was not written before the fix and is not written after it; the handler's own `error` (or `disconnect`) row, written before `rec.close()`, is the last one either way. The defect was the traceback and a dead tick thread — cosmetic to the run, misleading to a reader of the log, and stacked on top of the `ConnectionResetError` that is the real end of every one of these sessions. |
| **Check** | `toolkit/clientscan/test_movesync.py` §21, on the real class: `dropped == 0` over 200 rows while open (the positive control — the guard is keyed on `close()`, not always on); `closed` True after `close()`; an `event` and a `frame` after it return `None` and count 2; the file's row count unchanged; the first drop printed once naming `[c9]` and `` `sent` ``. 189 → 194 vaulted, floor 135 → 140 measured bare. |
