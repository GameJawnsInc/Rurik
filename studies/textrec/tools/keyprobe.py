"""Probe 2: is the RC4 key of a non-plain text record a function of its identity?

Uses the repo's OWN validated primitives (toolkit/authsrv/gwcrypto.py) rather
than a fresh transcription: the folded round constants at Gw.exe 0x909db8 match
arc4_hash's exactly (0x9FB498B3, 0x66B0CD0D), so the text path and the auth
channel share a key-derivation function that a real client has already accepted.

PREDICTION  Pooled over thousands of records, a correct key yields a symbol
            histogram like natural language: entropy ~4.5 bits at 7 bits/symbol.
            A wrong key is indistinguishable from uniform: 7.00.
            The undecrypted baseline is the control and must read 7.00.
WATCH       pooled symbol entropy only.
"""
import collections
import math
import os
import struct
import sys

R = r'C:\gd\Rurik\.claude\worktrees\youthful-hypatia-fd6d35'
for p in ('toolkit', r'toolkit\mapdata', r'toolkit\clientscan', r'toolkit\authsrv'):
    sys.path.insert(0, os.path.join(R, p))
import textrec                                              # noqa: E402
from gwcrypto import arc4_hash, ARC4                        # noqa: E402

M = 0xFFFFFFFF
LANG = 0
NREC = 2500
BITS = 7


def kdf(a, b):
    blk = struct.pack('<II', a & M, b & M)
    return arc4_hash(bytes(blk[i % 8] for i in range(20)))


def unpack(bits, payload):
    n = (len(payload) * 8) // bits + 1
    mask = (1 << bits) - 1
    acc = avail = p = 0
    out = []
    for _ in range(n):
        while avail <= 24:
            if p < len(payload):
                acc |= payload[p] << avail
            p += 1
            avail += 8
        out.append(acc & mask)
        acc >>= bits
        avail -= bits
    return out


def entropy(counter):
    n = sum(counter.values())
    return -sum((v / n) * math.log2(v / n) for v in counter.values()) if n else 0.0


SCHEMES = {
    'sid,0':      lambda fi, ri, aux, aid: (fi * 1024 + ri, 0),
    '0,sid':      lambda fi, ri, aux, aid: (0, fi * 1024 + ri),
    'sid,lang':   lambda fi, ri, aux, aid: (fi * 1024 + ri, LANG),
    'lang,sid':   lambda fi, ri, aux, aid: (LANG, fi * 1024 + ri),
    'ri,lang':    lambda fi, ri, aux, aid: (ri, LANG),
    'lang,ri':    lambda fi, ri, aux, aid: (LANG, ri),
    'fi,ri':      lambda fi, ri, aux, aid: (fi, ri),
    'ri,fi':      lambda fi, ri, aux, aid: (ri, fi),
    'sid,sid':    lambda fi, ri, aux, aid: (fi * 1024 + ri, fi * 1024 + ri),
    'aid,ri':     lambda fi, ri, aux, aid: (aid, ri),
    'ri,aid':     lambda fi, ri, aux, aid: (ri, aid),
    'aid,0':      lambda fi, ri, aux, aid: (aid, 0),
    'sid,aux':    lambda fi, ri, aux, aid: (fi * 1024 + ri, aux),
    'aux,sid':    lambda fi, ri, aux, aid: (aux, fi * 1024 + ri),
    'aux,0':      lambda fi, ri, aux, aid: (aux, 0),
    'sid|hi,0':   lambda fi, ri, aux, aid: (0x8000_0000 | (fi * 1024 + ri), 0),
    'sid,-1':     lambda fi, ri, aux, aid: (fi * 1024 + ri, M),
}


def main():
    with textrec.TextIndex(language=LANG) as ix:
        recs = []
        for fi in range(99):
            aid = ix.archive_id(fi)
            for ri, (k, aux, p) in enumerate(ix.records(fi)):
                if k == BITS and len(p) >= 24:
                    recs.append((fi, ri, aux, aid, p))
                    if len(recs) >= NREC:
                        break
            if len(recs) >= NREC:
                break
    print(f"{len(recs)} kind-0x{BITS:02x} records, language {LANG}\n")

    base = collections.Counter()
    for fi, ri, aux, aid, p in recs:
        base.update(unpack(BITS, p))
    print(f"  control, no decryption          {entropy(base):.3f}")
    print(f"  (uniform over {1<<BITS} symbols would be {BITS}.000; "
          f"English text at {BITS} bits ~4.5)\n")

    for name, fn in SCHEMES.items():
        pool = collections.Counter()
        for fi, ri, aux, aid, p in recs:
            a, b = fn(fi, ri, aux, aid)
            pool.update(unpack(BITS, ARC4(kdf(a, b)).crypt(p)))
        print(f"  {name:12} {entropy(pool):.3f}")


if __name__ == '__main__':
    main()
