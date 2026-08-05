"""The Guild Wars auth/game channel key exchange, in pure Python.

Two primitives, both small, both exactly specified by public reimplementations
(OpenTyria's server side and Headquarter's client side agree byte for byte).

1. Static-ephemeral Diffie-Hellman. The client holds (g, p, B) compiled into its
   binary and sends A = g^a mod p. Both sides derive `shared`. Because B is baked
   in and never transmitted, our server only sees a shared secret it can compute
   if the client was patched with a triple we hold the private half of -- which is
   what toolkit/clientpatch/make_custom_client.py is for.

2. `arc4_hash`, the key derivation. It looks like SHA-1 and is not: it runs only
   five rounds of the SHA-1 compression function over a single 20-byte block,
   reads and writes its words little-endian, and finishes with
   `output[i] = input[i] + state[i]` rather than a standard finalisation. Feeding
   the master secret to a real SHA-1 produces a plausible-looking wrong key and a
   handshake that fails with nothing to point at, so this is implemented from the
   specification rather than borrowed from hashlib.
"""

import struct

MASK = 0xFFFFFFFF


def rol32(x, n):
    x &= MASK
    return ((x << n) | (x >> (32 - n))) & MASK


def arc4_hash(key20: bytes) -> bytes:
    """Derive the 20-byte ARC4 key from the 20-byte master secret."""
    if len(key20) != 20:
        raise ValueError("arc4_hash expects exactly 20 bytes")

    A, B, C, D, E = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0
    w = list(struct.unpack("<5I", key20))

    F = D ^ (B & (C ^ D))
    E = (E + w[0] + rol32(A, 5) + F + 0x5A827999) & MASK
    B = rol32(B, 30)

    F = C ^ (A & (B ^ C))
    D = (D + w[1] + rol32(E, 5) + F + 0x5A827999) & MASK
    A = rol32(A, 30)

    F = B ^ (E & (A ^ B))
    C = (C + w[2] + rol32(D, 5) + F + 0x5A827999) & MASK
    E = rol32(E, 30)

    F = B ^ C ^ D
    E = (E + w[3] + rol32(A, 5) + F + 0x6ED9EBA1) & MASK
    B = rol32(B, 30)

    F = A ^ B ^ C
    D = (D + w[4] + rol32(E, 5) + F + 0x6ED9EBA1) & MASK
    A = rol32(A, 30)

    return struct.pack("<5I",
                       (w[0] + A) & MASK, (w[1] + B) & MASK, (w[2] + C) & MASK,
                       (w[3] + D) & MASK, (w[4] + E) & MASK)


class ARC4:
    """Standard RC4 with a persistent keystream position.

    One instance per direction. The two directions use the SAME derived key but
    MUST NOT share state -- a single instance used for both would consume one
    keystream across interleaved traffic and desync instantly.
    """

    def __init__(self, key: bytes):
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + key[i % len(key)]) & 0xFF
            s[i], s[j] = s[j], s[i]
        self.s = s
        self.i = 0
        self.j = 0

    def crypt(self, data: bytes) -> bytes:
        s, i, j = self.s, self.i, self.j
        out = bytearray(len(data))
        for n, b in enumerate(data):
            i = (i + 1) & 0xFF
            j = (j + s[i]) & 0xFF
            s[i], s[j] = s[j], s[i]
            out[n] = b ^ s[(s[i] + s[j]) & 0xFF]
        self.i, self.j = i, j
        return bytes(out)


def compute_shared(client_public_le: bytes, server_private: int, prime: int) -> bytes:
    """shared = A^b mod p, as 64 bytes little-endian.

    The wire carries A little-endian, and the shared secret is consumed
    little-endian too. Getting either endianness wrong yields a valid-looking
    64-byte value and a dead connection.
    """
    A = int.from_bytes(client_public_le, "little")
    shared = pow(A, server_private, prime)
    return shared.to_bytes(64, "little")


def make_server_seed(master_secret: bytes, shared_le: bytes) -> bytes:
    """The 20 bytes the server sends: master_secret XOR the first 20 of shared."""
    return bytes(m ^ s for m, s in zip(master_secret, shared_le[:20]))


def recover_master_secret(server_seed: bytes, shared_le: bytes) -> bytes:
    """The client's side of the same operation. Used by the test client."""
    return bytes(m ^ s for m, s in zip(server_seed, shared_le[:20]))
