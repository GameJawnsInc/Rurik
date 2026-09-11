"""The wire's own primitives -- bytes into things, and whether a frame is whole.

FIVE FUNCTIONS AND NO STATE. Four of them are four bytes seen from a different
angle (`_u32` and `_f32` on the send side, `_f32_of` on the receive side,
`_fraction` on the one float channel that can kill the client), and the fifth,
`frame_pending`, answers the only question the read loop asks of a buffer: how
much of this is a message yet. None of them knows an opcode, a socket, a state
dict or a flag; between them they read nothing but `struct`, which is why they
can sit here and be tested without a handshake.

WHAT EACH ONE IS EVIDENCE FOR is written in its own docstring below and travels
with it: the `CharPool.cpp(84)` assert that a real fight produced and that
`_fraction` exists to refuse in advance; the dword-versus-float trap that has
cost this project three times over and that `_f32_of` names all three of; and
`frame_pending`'s three-clause contract, each clause a thing the inline version
of that code got wrong.

THE MONKEYPATCH CHAIN, and it is the reason this module stops where it does.
`test_guards.py` rebinds `authsrv._fraction` at six paired sites to prove the
refusal reaches the live send path. That rebinds *authsrv's* global, so it only
reaches callers that resolve the name there at call time -- which is every
caller, because `_damage_fraction` (the one function that both calls `_fraction`
and is called by the damage path) deliberately STAYED in `authsrv.py` at the
line this unit's first half stops one line short of. Nothing in this file calls
`_fraction`. If that ever changes, six sections of `test_guards` go quietly
green while testing a copy of the function nobody patched, and they are 3
(`section_land_swing`), 4 (`section_land_skill`), 5 (`section_revive_due`), 6
(`section_player_revive_due`), 7 (`section_agent_refill_due`) and 8
(`section_player_refill_due`) -- re-derived from the tree, because the lane
brief and this commit's own predecessor message both named "3, 4, 5 and 9" and
9 (`section_overkill`) is the one section here that rebinds NOTHING: it calls
`authsrv._damage_fraction` against a pinned literal instead.

Standard library only, and no import of the server: `authsrv.py` imports these
names back through a re-export at the site they were cut from, and a leaf that
imported its origin would load a second copy of a module that runs as
`__main__`.
"""
import struct


def _u32(x):
    """A SIGNED integer as the dword the codec will put on the wire.

    The schema types these fields `dword` and the codec packs them `<I`, which
    refuses a negative outright rather than wrapping it -- so a message whose
    field is genuinely signed needs the two's-complement done here. Exactly one
    thing is signed today: `0x00EE`'s morale delta, which is -15 on a death and
    was read off ArenaNet's wire as `0xFFFFFFF1`.

    The mirror of `_f32_of`'s trap, from the send side: the wire has no idea
    which of its dwords are signed, and `struct.error` is the friendly failure
    here -- the unfriendly one is a caller who masks by hand somewhere else and
    gets it right by luck.
    """
    return int(x) & 0xFFFFFFFF


def _f32(x):
    """A float as the dword the codec will put on the wire.

    The schema types these fields `dword` because the client's own format
    tables do -- a float and a dword are the same four bytes to its generic
    deserializer, and only the handler knows which it is. So every float we
    send goes out through here.
    """
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _f32_of(dword):
    """`_f32` backwards: the float a `dword` field the client sent us is carrying.

    THE SAME TRAP, from the receive side, and it has now cost this project three
    times (GAME_SMSG 0x002E's "cos, sin", GAME_CMSG 0x0027's field order, and
    GAME_CMSG 0x0040 sitting unnamed for days). A dword-typed field is four
    bytes; whether they are an integer or a float is a fact about the MESSAGE,
    not about the marshalling, and reading one as the other never errors -- it
    hands back a confident wrong number. 0x0040's +inf sentinel reads as
    2,139,095,040 if you take `values[1]` at face value.

    Out-of-range input is masked rather than raised on. The codec only ever
    produces 0..2^32-1 here, so the mask is unreachable in practice; what it
    buys is that a future caller cannot turn a malformed field into a
    struct.error that tears down a live session inside the read loop.
    """
    return struct.unpack("<f", struct.pack("<I", int(dword) & 0xFFFFFFFF))[0]


def _fraction(x, prop, what):
    """A pool fraction for the 0x00A3 float channel, refused loudly if out of range.

    THE CRASH THIS EXISTS FOR, and it is the first client assert this project has
    captured from a real fight. OBSERVED 2026-08-11: two seconds after the Hatcher
    died, the client went down on

        Assertion: fraction <= 1.0f    P:\\Code\\Gw\\Char\\CharPool.cpp(84)

    and the crash trace carries our own message three frames below the assert --
    `Arg:00000022 0000000a 0000000a 42c80000`, which is property 34, agent 10,
    agent 10, and 42c80000 = 100.0f. That is `revive_due`'s "refill bar" send,
    which passed `max_health` where the client wanted a FRACTION of it.

    WHY EVERY EARLIER MEASUREMENT MISSED IT. The assert is `<=`, so it can only
    fire in the POSITIVE direction, and every value we had ever put on this channel
    was damage: `-HIT_FRACTION`, and the `-50.0` that `GV_HEALTH`'s comment is
    built on. A negative number passes `fraction <= 1.0f` no matter how absurd, so
    the whole damage side of the arc tested this bound VACUOUSLY. It took a kill
    and a revive -- the first positive value ever sent -- to reach it.

    Refusing here rather than clamping is deliberate: a clamp would turn a wrong
    number into a plausible one, and the next caller would never learn.
    """
    if not -1.0 <= x <= 1.0:
        raise ValueError(
            f"refusing to send {x!r} as property {prop} ({what}) on the 0x00A3 "
            f"float channel: values there are FRACTIONS of a pool, and the client "
            f"asserts `fraction <= 1.0f` at CharPool.cpp:84 -- it does not clamp, "
            f"it dies, two seconds later and with no server-side symptom.")
    return _f32(x)


def frame_pending(codec_obj, channel, pending, mask):
    """(messages, remaining, desync) for one buffer. `desync` is None or the reason.

    Extracted from the receive loop so the POLICY is testable without a socket, a
    handshake or a client. It was inline, which meant the fix below had no test
    covering it: the suite asserted what codec.decode_stream does, not what this
    server does with the answer, and those are different questions -- the whole
    defect was that the answer was correct and the caller mishandled it.

    THE CONTRACT, and each clause is a thing the old code got wrong:

      * whole messages are returned and their bytes consumed;
      * an INCOMPLETE trailing message is not an error. It is the normal case --
        a TCP read is not a message boundary -- and its bytes stay in `remaining`
        to be completed by the next read;
      * an UNFRAMEABLE message sets `desync` and leaves its bytes in `remaining`
        UNTOUCHED. The old code set `pending = b""` here, which reads like
        recovery and is not: with no length prefix nothing knows where the bad
        message ended, so every later read was framed from a non-boundary while
        ARC4 kept decrypting correctly and the bytes kept looking plausible.
        Returning them unconsumed is what lets the caller report exactly what it
        choked on instead of guessing past it.
    """
    msgs, consumed, err = codec_obj.decode_stream(channel, pending, mask=mask)
    remaining = pending[consumed:]
    if err and "incomplete" not in err:
        return msgs, remaining, err
    return msgs, remaining, None
