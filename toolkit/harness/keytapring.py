"""Where the tap cave stashed the secret, the poller that keeps every value the slot held, and the reader that gets them back off disk.

Split out of `toolkit/harness/livesession.py`, where all three names below are still
re-exported at the site they used to occupy. `livesession.slot_rva`,
`livesession.KeyRing` and `livesession.load_keyring` keep working:
`toolkit/harness/test_livesession.py` reads `ls.KeyRing` and `ls.load_keyring` in section
3c and patches `mod.slot_rva` onto the livesession module object in section 5g, and
`livesession.run()` calls `slot_rva` and constructs `KeyRing` as bare globals while
`livesession.reassemble()` calls `load_keyring` as one. That last part is load-bearing
rather than incidental: §5g stubs `mod.slot_rva = lambda _exe: 0x1000` and then runs
`run()` to watch the order the seal and the launch fire in, which works because the
re-export binds the name in `livesession`'s own namespace and `run()` resolves it there.

WHY THIS IS ITS OWN MODULE. These three are the key half of a live capture and they read
one thing: a 20-byte slot in a key-tapped client's own memory, and the file that slot's
values are written to. `slot_rva` locates it by parsing the PE, `KeyRing` polls it
read-only and appends each distinct value to disk, `load_keyring` reads that file back.
Nothing here sniffs the wire, splits a stream, seals a plan, checks a build or talks to
`accounts` -- the driver they came out of does all of that, and a reader who wants to know
how the keys are obtained should not have to load the packet-capture backend to find out.

FOUR `sys.path` inserts, not the driver's six, and not the two this lane was scoped with
-- the extra one is `authsrv`, and it is needed because `KeyRing` derives the ARC4 key
itself. `HERE` reaches `keytap` (the read-only cross-process reader) and `liveerror`; the
toolkit root reaches `gwpe` (the PE parser `slot_rva` needs) and `origin`; `clientpatch`
reaches `keytap_patch` (the cave's own locator, so the reader and the writer agree on
where the slot is by construction rather than by a duplicated constant); `authsrv` reaches
`gwcrypto.arc4_hash`, imported late in `KeyRing.run` and `KeyRing.keyring`. `schema` and
`mapdata` are the driver's, for `codec` and `datcheck`, and are not copied. MEASURED
2026-09-11, on the modules rather than only on the path, because `planseal.py`'s first
draft made a path claim that `marks.py` quietly falsified for it: `import keytapring`
loads exactly `origin` and `liveerror` of this repo's modules and none of `livesession`,
`wirecapture`, `accounts`, `marks`, `vaultpath`, `codec`, `gwcrypto`, `wiresplit` or
`planseal`, and adds exactly the four directories named above to `sys.path` and no fifth.
This module does not import its origin (R4): the live driver runs as
`python livesession.py`, so importing it back would load a second copy whose flags
`main()` never set.

THE `origin.record` LITERAL BELOW STILL SAYS `toolkit/harness/livesession.py`, AND THAT IS
DELIBERATE. It is the `produced_by` field on every `keyring.jsonl` already in the vault,
and changing it would split the corpus in two on a field whose whole purpose is to let a
reader classify a file in one pass. `origin.record` is a pure dict builder that neither
validates that string nor inspects its caller (`origin.py:98-106`), and no consumer
branches on the literal, so a live run after this split writes a keyring byte-identical to
one written before it. The driver is still what runs this code; only the `def` moved.

THE REFERENT OF ONE MOVED COMMENT STAYS IN `livesession.py`. `slot_rva`'s comment travels
verbatim, so the pointer is written down here instead of reworded there: "preflight
already refuses an untapped build, so reaching here means the binary changed under us" is
about `livesession.preflight`, which stays, and `livesession.check_build_matches_service`
carries the matching note from the other side ("`slot_rva` re-reads the slot and raises").

`LiveError` is imported rather than redefined, and after the refusal split there is exactly
one such class object in the process, so `test_livesession.py`'s `LiveErrorType = ls.LiveError`
still catches everything `slot_rva` raises.

standard library only, plus this repo's own `keytap`/`keytap_patch`/`gwpe`/`gwcrypto`.
"""
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import origin  # noqa: E402
from liveerror import LiveError  # noqa: E402


def slot_rva(exe):
    """Where the key-tap cave stashes master_secret in this binary. Raises if untapped."""
    import keytap_patch          # toolkit/clientpatch, already on sys.path above
    from gwpe import PE          # toolkit/gwpe.py
    pe = PE(exe)
    try:
        rva, _ = keytap_patch.locate_slot(pe.data, pe)
    except keytap_patch.KeyTapError as exc:
        # preflight already refuses an untapped build, so reaching here means the binary
        # changed under us. Re-raise as a LiveError rather than a bare traceback.
        raise LiveError(f"cannot locate the key-tap slot in {exe}: {exc}\n"
                        f"  Rebuild: make_custom_client.py --no-dh-patch --key-tap, then "
                        f"make_run_dir.py --live") from exc
    return rva


class KeyRing(threading.Thread):
    """Poll the tap slot and keep EVERY distinct value it holds, in order, with timestamps.

    Not "read the key once". Each DH-keyed channel derives its own master_secret through the
    same code, so the one slot is overwritten at every handshake: a session that reaches the
    world has replaced the auth channel's secret with the game channel's before it ends.
    Reading once yields whichever handshake happened last and silently loses the other, and
    an off-wire capture of a channel whose key we threw away is unrecoverable -- there is no
    second chance at a live session.

    Read-only throughout (keytap holds PROCESS_VM_READ and nothing else), and a failed read
    is a retry, never a crash: the slot is legitimately all-zero until the first handshake.
    """

    def __init__(self, pid, rva, module="Gw.exe", interval=0.25, path=None):
        super().__init__(daemon=True)
        self.pid, self.rva, self.module, self.interval = pid, rva, module, interval
        self.values = []          # [(t, master_secret_bytes)] -- distinct, in order
        self.errors = 0
        self.path = path          # persist here the INSTANT a key appears -- see _persist
        self._seen = set()
        self._stop = threading.Event()
        self.t0 = time.monotonic()
        if self.path:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(origin.record("toolkit/harness/livesession.py",
                                                  origin.LIVE,
                                                  note="tapped session keys, one per "
                                                       "DH-keyed channel")) + "\n")

    def _persist(self, t, master, key):
        """Append one key to disk and FLUSH, the moment it is read.

        This exists because the first live run lost six of seven keys. The keyring was held
        in memory and only the keys that survived assembly reached disk, so six connections
        of real ArenaNet ciphertext -- already captured, gap-free -- became permanently
        undecryptable the moment the process exited. There is no recovering them: the key
        derives from ArenaNet's private exponent.

        So: written per key, not per run, and flushed rather than buffered. A crash, a
        Ctrl-C, a power cut or an exception anywhere downstream now costs at most the key
        being read at that instant, and never a key already seen. Recorded under the field
        names scrub_captures.py treats as secret.
        """
        if not self.path:
            return
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"kind": "session_key", "t": t,
                                     "master_secret": master.hex(),
                                     "arc4_key": key.hex()}) + "\n")
                fh.flush()
        except OSError:
            # Never let a disk problem kill the poller: an in-memory key is still better
            # than no key, and the caller's report says how many were persisted.
            self.errors += 1

    def run(self):
        import keytap
        # Resolve the base and open the handle ONCE. keytap.read_rva re-snapshots the
        # toolhelp module list and re-opens the process on every call, which is right for
        # a one-shot read and wrong four times a second for twenty minutes -- that is
        # ~4800 OpenProcess calls against the one client we are trying not to perturb.
        # ASLR rebases per LAUNCH, not during a process's life, so caching inside a thread
        # that is bound to one pid keeps the property keytap's docstring is protecting.
        handle = base = None
        while not self._stop.is_set():
            got = None
            try:
                if handle is None:
                    base = keytap.module_base(self.pid, self.module)
                    handle = keytap.open_read(self.pid)
                got = keytap.read_handle(handle, base + self.rva, 20)
            except keytap.TapError:
                # The process is gone, or the module is not mapped yet. Both are
                # transient-or-terminal and the caller decides which by watching the
                # client, not by us guessing. Drop the handle so the next tick re-resolves.
                self.errors += 1
                handle = base = None
            if got and any(got) and got not in self._seen:
                from gwcrypto import arc4_hash
                self._seen.add(got)
                t = round(time.monotonic() - self.t0, 2)
                self.values.append((t, got))
                self._persist(t, got, arc4_hash(got))
            self._stop.wait(self.interval)
        if handle is not None:
            keytap.kernel32.CloseHandle(handle)

    def stop(self):
        self._stop.set()

    def keyring(self):
        """[(label, arc4_key)] -- the ARC4 keys, derived from each tapped master_secret.

        The cave taps master_secret BEFORE the key schedule, so the ARC4 key is
        arc4_hash(master_secret). Proven on loopback by dryrun_keycapture.py, which required
        the tapped value to equal the master_secret our own server independently derived.
        """
        from gwcrypto import arc4_hash
        return [(f"tap@{t}s", arc4_hash(v)) for t, v in self.values]


def load_keyring(path):
    """[(label, arc4_key)] read back from a persisted keyring.jsonl.

    This is what makes a capture re-assemblable from disk without a second live session --
    the property R0b's criterion asks for and the first run did not have.
    """
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(r, dict) and r.get("kind") == "session_key" and r.get("arc4_key"):
                out.append((f"tap@{r.get('t', '?')}s", bytes.fromhex(r["arc4_key"])))
    return out
