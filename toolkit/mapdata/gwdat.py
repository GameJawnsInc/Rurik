"""Port of the Guild Wars DAT huffman/LZ77 decompressor.

Ported from gw-preservation/fileserver-utils binutil/huffman.go + bitreader.go.
That is an independent lineage from xentax.cpp in GuildWarsMapBrowser, and the
static tables in the two projects are byte-identical -- checked element by
element, all 256 entries of Table2, not merely spot-checked. Two independently
maintained projects carrying the same tables is real corroboration; it is also
the only corroboration we have, since neither states where the tables came from.

Framing for compression-code-8 payloads follows GuildWarsMapBrowser
SourceFiles/xentax.cpp:136 -- the LAST u32 word of the stored payload is the
decompressed size.

HOW MUCH TO TRUST THIS, because it is easy to overstate:

"Produced exactly the declared number of bytes" is NOT evidence that this
decoder is correct. The loop below terminates at out_size by construction, so
that match is forced. Run it with the bound removed and it overshoots on every
file tried -- 91350 against a declared 91114, 20766 against 20649 -- because the
trailing u32 is a truncation length rather than a natural stopping point.
Fournux's DECOMPRESSION.md:26 says the same thing outright.

The real evidence is structural and independent of the length field: decompress a
map file and walk its FFNA chunk table, and the chunk sizes consume the output to
the exact byte. That holds on MFT row 7982 (24 chunks, 2925270 bytes) and row
20444 (22 chunks, 3389269 bytes). Separately, 628 of 628 cross-references
resolved to correctly-typed payloads. Two structural confirmations plus the
reference resolution is why this is considered good enough to build on.

A third structural confirmation now exists, and it is the strongest of the three
because the expected bytes are PREDICTED rather than merely self-consistent: all
1,089 text files decompress and split into exactly 1,024 records that tile the
blob, each ending in a two-byte (language_index, file_index) tail whose value the
decode has to get right and which differs per file. See test_gwdat.py.

WHERE BOTH REFERENCE IMPLEMENTATIONS ARE WRONG -- the zero-length code.

Twelve of those 1,089 files used to fail here outright. The cause is a real
defect shared by the Go reference and xentax.cpp, not a slip in this port: a
table holding one symbol encodes it in ZERO bits, build_table deliberately parks
that symbol at follow_root[0], and then both implementations begin code
assignment at length 1 and never read it back. Every lookup lands on an unfilled
node.

The failure modes differ, and ours was the useful one. Go's getNextCode has no
guard: it reads encLen 0, consumes no bits, returns node value 0, and does that
forever from a bit position that never advances -- filling the block with a
constant byte and returning silently. This port raised, which is the only reason
the defect was noticed. It is fixed below, and the fix cannot change any file
that already worked, because it only runs where the old code raised.

What has NOT been done: diffing this implementation's output against xentax.cpp's
on the same input. That is the check that would settle it, and it needs a C
compiler this environment does not have. Note that it would now be a diff against
a decoder we believe to be wrong on this one case.
"""
import struct

M = 0xFFFFFFFF


def shl(x, n):
    if n >= 32:
        return 0
    return (x << n) & M


def shr(x, n):
    if n >= 32:
        return 0
    return (x & M) >> n


table1 = [
    (0xa0000000, 2), (0x60000000, 6), (0x40000000, 10), (0x20000000, 18),
    (0x12000000, 25), (0x0c000000, 31), (0x07000000, 41), (0x03000000, 57),
    (0x01600000, 70), (0x00f00000, 77), (0x00c00000, 83), (0x00b00000, 87),
    (0x00a00000, 95), (0x00000000, 255),
]

table2 = [
    0x08, 0x09, 0x0A, 0x00, 0x07, 0x0B, 0x0C, 0x06, 0x29, 0x2A, 0xE0, 0x04, 0x05, 0x20, 0x28, 0x2B, 0x2C, 0x40,
    0x4A, 0x03, 0x0D, 0x25, 0x26, 0x27, 0x48, 0x49, 0x24, 0x47, 0x4B, 0x4C, 0x69, 0x6A, 0x23, 0x46, 0x60, 0x63,
    0x67, 0x68, 0x88, 0x89, 0xA0, 0xE8, 0x01, 0x02, 0x2D, 0x43, 0x44, 0x45, 0x65, 0x66, 0x80, 0x87, 0x8A, 0xA8,
    0xA9, 0xC0, 0xC9, 0xE9, 0x0E, 0x4D, 0x64, 0x6B, 0x6C, 0x84, 0x85, 0x8B, 0xA4, 0xA5, 0xAA, 0xC8, 0xE5, 0x83,
    0x86, 0xA6, 0xA7, 0xC7, 0xCA, 0xE7, 0x22, 0x2E, 0x8C, 0xC4, 0xE4, 0xE6, 0x4E, 0x6D, 0xC6, 0xEC, 0x0F, 0x10,
    0x11, 0x8D, 0xAB, 0xAC, 0xCC, 0xEA, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D,
    0x1E, 0x1F, 0x21, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D,
    0x3E, 0x3F, 0x41, 0x42, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C,
    0x5D, 0x5E, 0x5F, 0x61, 0x62, 0x6E, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A,
    0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x81, 0x82, 0x8E, 0x8F, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
    0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F, 0xA1, 0xA2, 0xA3, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4,
    0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xC1, 0xC2, 0xC3, 0xC5, 0xCB, 0xCD, 0xCE,
    0xCF, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE1,
    0xE2, 0xE3, 0xEB, 0xED, 0xEE, 0xEF, 0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB,
    0xFC, 0xFD, 0xFE, 0xFF,
]

table3 = [
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x14, 0x18, 0x1C,
    0x20, 0x28, 0x30, 0x38, 0x40, 0x50, 0x60, 0x70, 0x80, 0xA0, 0xC0, 0xE0, 0xFF, 0x00, 0x00, 0x00,
]

extraBitsLength = [
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
    3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0,
]

extraBitsDist = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
    7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14,
]

backtrackTable = [
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0006, 0x0008, 0x000C,
    0x0010, 0x0018, 0x0020, 0x0030, 0x0040, 0x0060, 0x0080, 0x00C0,
    0x0100, 0x0180, 0x0200, 0x0300, 0x0400, 0x0600, 0x0800, 0x0C00,
    0x1000, 0x1800, 0x2000, 0x3000, 0x4000, 0x6000, 0x0100, 0x0302,
    0x0504, 0x0706, 0x0A08, 0x0E0C, 0x1410, 0x1C18, 0x2820, 0x3830,
    0x5040, 0x7060, 0xA080, 0xE0C0, 0x00FF, 0x0000,
]


class Eof(Exception):
    pass


class BitReader:
    __slots__ = ('data', 'buf1', 'buf2', 'idx', 'avail')

    def __init__(self, data):
        if len(data) < 8:
            raise ValueError('need >= 8 bytes')
        self.data = data
        self.buf1 = struct.unpack_from('<I', data, 0)[0]
        self.buf2 = struct.unpack_from('<I', data, 4)[0]
        self.idx = 8
        self.avail = 32

    def peek(self, count):
        return shr(self.buf1, 32 - count)

    def read(self, count):
        v = self.peek(count)
        self.consume(count)
        return v

    def consume(self, count):
        self.buf1 = (shr(self.buf2, 32 - count) | shl(self.buf1, count)) & M
        if self.avail < count:
            if self.idx + 4 > len(self.data):
                raise Eof()
            self.buf2 = struct.unpack_from('<I', self.data, self.idx)[0]
            self.idx += 4
            new_avail = self.avail + 32 - count
            self.buf1 = (self.buf1 + shr(self.buf2, new_avail)) & M
            self.buf2 = shl(self.buf2, count - self.avail)
            self.avail = new_avail
        else:
            self.avail -= count
            self.buf2 = shl(self.buf2, count)


class HuffTable:
    __slots__ = ('nodes', 'trans', 'vals', 'zero_len')

    def __init__(self):
        self.nodes = [[0, 0] for _ in range(256)]
        self.trans = [[0, 0, 0] for _ in range(24)]  # firstEncoding, lastIndex, encLen
        self.vals = []
        # A table holding exactly one symbol encoded in zero bits. See
        # build_table: upstream parks such a symbol at follow_root[0] and then
        # never reads it back.
        self.zero_len = False

    def next_code(self, r):
        bits = r.peek(8)
        enc_len = self.nodes[bits][0]
        enc_val = self.nodes[bits][1]
        if enc_len == 0xFFFFFFFF:
            b = r.peek(32)
            hit = None
            for v in self.trans:
                if v[0] > b:
                    continue
                hit = v
                break
            if hit is None:
                raise ValueError('no largeSymbolTranslation match')
            first_enc, last_index, enc_length = hit
            enc_len = enc_length
            group = shr((b - first_enc) & M, 32 - enc_length)
            large_idx = last_index - group
            if large_idx < 0 or large_idx >= len(self.vals):
                raise ValueError('largeEncIndex out of range')
            enc_val = self.vals[large_idx]
        if enc_len == 0:
            if not self.zero_len:
                raise ValueError('zero-length code (table hole)')
            return enc_val          # zero-length code: consumes no bits
        r.consume(enc_len)
        return enc_val


def build_table(r):
    follow_root = [0xFFFFFFFF] * 32
    symbol_count = r.read(16)
    follow = [0] * max(symbol_count, 1)
    total = 0
    sym_idx = symbol_count - 1
    while sym_idx != -1:
        b = r.peek(32)
        for i, (thr, _) in enumerate(table1):
            if thr <= b:
                idx = i
                break
        bit_count = idx + 3
        offset = shr((b - table1[idx][0]) & M, 32 - bit_count)
        r.consume(bit_count)
        temp = table2[table1[idx][1] - offset]
        n_sym = temp >> 5
        sym_len = temp & 0x1F
        if sym_len != 0 or symbol_count < 2:
            n_sym += 1
            total += n_sym
            for _ in range(n_sym):
                if sym_idx < 0:
                    raise ValueError('symbol underflow')
                follow[sym_idx] = follow_root[sym_len]
                follow_root[sym_len] = sym_idx
                sym_idx -= 1
        else:
            sym_idx -= (n_sym + 1)
            if sym_idx < -1:
                raise ValueError('symbol index underflow')
    if total == 0:
        follow[symbol_count - 1] = follow_root[0]
        follow_root[0] = symbol_count - 1
        total = 1

    # THE ZERO-LENGTH CODE, which is where both reference implementations stop.
    #
    # follow_root[0] is the chain of symbols encoded in ZERO bits -- one symbol
    # that is always the answer. It is reachable two ways: the fallback directly
    # above, and a table declaring fewer than two symbols (the `symbol_count < 2`
    # arm of the length walk is the only way sym_len == 0 enters that branch).
    #
    # Neither upstream reads it. Go's buildHuffmanTable and xentax.cpp both begin
    # code assignment at length 1, so the symbol they had just deliberately
    # parked at length 0 never enters the table and every lookup lands on an
    # unfilled node. The consequences differ and ours was the better failure:
    # Go's getNextCode has no guard, so it reads encLen 0, consumes no bits and
    # returns node value 0 -- forever, filling the block with a constant byte
    # from a bit position that never advances. Our port raised instead, which is
    # how this was found at all.
    #
    # MEASURED: 12 of the 1,089 text files hit this, and every one of them is a
    # distance table. With the symbol installed they decompress and the result
    # passes the record walk exactly. See test_gwdat.py.
    zero_symbol = None
    cur = follow_root[0]
    while cur != 0xFFFFFFFF:
        zero_symbol = cur
        cur = follow[cur]

    next_bits = 1
    in_table = 0
    t = HuffTable()
    for enc_len in range(1, 9):
        cur = follow_root[enc_len]
        while cur != 0xFFFFFFFF:
            if cur >= symbol_count:
                raise ValueError('currentSymbol >= symbolCount')
            if next_bits >= (1 << enc_len):
                raise ValueError('nextBitsEncoding overflow')
            first = next_bits << (8 - enc_len)
            for i in range(first, first + (1 << (8 - enc_len))):
                t.nodes[i][0] = enc_len
                t.nodes[i][1] = cur
            cur = follow[cur]
            in_table += 1
            next_bits -= 1
        next_bits = (next_bits << 1) + 1

    if in_table == 0 and zero_symbol is not None:
        # Every 8-bit prefix maps to the one symbol, and reading it costs
        # nothing. Filling all 256 nodes rather than special-casing the lookup
        # keeps next_code's fast path unchanged.
        for i in range(256):
            t.nodes[i][0] = 0
            t.nodes[i][1] = zero_symbol
        t.zero_len = True
        return t
    if in_table == total:
        return t
    for enc_len in range(9, 32):
        cur = follow_root[enc_len]
        while cur != 0xFFFFFFFF:
            if cur >= symbol_count:
                raise ValueError('currentSymbol >= symbolCount (large)')
            if next_bits >= (1 << enc_len):
                raise ValueError('nextBitsEncoding overflow (large)')
            partial = next_bits >> (enc_len - 8)
            t.nodes[partial][0] = 0xFFFFFFFF
            t.nodes[partial][1] = 0
            t.vals.append(cur)
            cur = follow[cur]
            next_bits -= 1
        first_enc = shl((next_bits + 1) & M, 32 - enc_len)
        t.trans[enc_len - 9] = [first_enc, len(t.vals) - 1, enc_len]
        next_bits = (next_bits << 1) + 1
    return t


def decompress(data, out_size=None):
    """Decompress a Gw.dat compression-code-8 payload.

    If out_size is None, take it from the last u32 word (the DAT framing).
    """
    if out_size is None:
        out_size = struct.unpack_from('<I', data, (len(data) // 4) * 4 - 4)[0]
    r = BitReader(data)
    out = bytearray()
    r.consume(4)
    first_four = r.read(4)
    try:
        while r.idx < len(data) and len(out) < out_size:
            lit = build_table(r)
            dist = build_table(r)
            block_size = (r.read(4) + 1) * 4096
            for _ in range(block_size):
                if len(out) >= out_size:
                    break
                code = lit.next_code(r)
                if code < 0x100:
                    out.append(code)
                else:
                    k = code - 256
                    blen = extraBitsLength[k]
                    code = table3[k]
                    if blen:
                        code |= r.read(blen)
                    count = first_four + code + 1
                    code = dist.next_code(r)
                    blen = extraBitsDist[code]
                    back = backtrackTable[code]
                    if blen:
                        back |= r.read(blen)
                    if back >= len(out):
                        raise ValueError('backtrack %d >= produced %d' % (back, len(out)))
                    src = len(out) - (back + 1)
                    for j in range(src, src + count):
                        out.append(out[j])
    except Eof:
        pass
    return bytes(out), out_size
