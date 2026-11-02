"""Read/write Telltale .ttarch2 archives (NCTT / ZCTT containers with a TTA4 body)."""
import struct
import zlib

CHUNK = 0x10000


class Archive:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        magic = self.f.read(4)
        self.compressed = magic == b'ZCTT'
        if magic == b'ZCTT':
            cs, n = struct.unpack('<II', self.f.read(8))
            self.chunk_size = cs
            self.chunk_offs = struct.unpack('<%dQ' % (n + 1), self.f.read(8 * (n + 1)))
            self._cache = {}
        elif magic == b'NCTT':
            (self.body_size,) = struct.unpack('<Q', self.f.read(8))
            self.body_start = 12
        else:
            raise ValueError('unsupported container %r' % magic)
        self._parse_tta4()

    # --- body access (uncompressed TTA4 stream) ---
    def _chunk(self, i):
        c = self._cache.get(i)
        if c is None:
            self.f.seek(self.chunk_offs[i])
            raw = self.f.read(self.chunk_offs[i + 1] - self.chunk_offs[i])
            c = zlib.decompress(raw, -15)
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[i] = c
        return c

    def read_body(self, pos, size):
        if not self.compressed:
            self.f.seek(self.body_start + pos)
            return self.f.read(size)
        out = bytearray()
        while size > 0:
            i, o = divmod(pos, self.chunk_size)
            c = self._chunk(i)
            take = c[o:o + size]
            out += take
            pos += len(take)
            size -= len(take)
            if not take:
                raise EOFError
        return bytes(out)

    def _parse_tta4(self):
        hdr = self.read_body(0, 12)
        magic, name_size, n = struct.unpack('<4sII', hdr)
        if magic != b'4ATT':
            raise ValueError('expected TTA4, got %r' % magic)
        raw = self.read_body(12, 28 * n)
        names = self.read_body(12 + 28 * n, name_size)
        self.data_start = 12 + 28 * n + name_size
        self.entries = []
        for i in range(n):
            crc, off, size, unk, page, noff = struct.unpack_from('<QQIIHH', raw, 28 * i)
            p = page * CHUNK + noff
            name = names[p:names.index(b'\0', p)].decode('latin-1')
            self.entries.append((name, off, size, crc))
        self.by_name = {e[0].lower(): e for e in self.entries}

    def read(self, name):
        e = self.by_name[name.lower()]
        return self.read_body(self.data_start + e[1], e[2])


# --- CRC64 (ECMA-182, as used by Telltale for file name hashes) ---
_POLY = 0x42F0E1EBA9EA3693
_TABLE = []
for _i in range(256):
    _c = _i << 56
    for _ in range(8):
        _c = ((_c << 1) ^ _POLY) if _c & (1 << 63) else (_c << 1)
        _c &= 0xFFFFFFFFFFFFFFFF
    _TABLE.append(_c)


def crc64(data, crc=0):
    for b in data:
        crc = _TABLE[((crc >> 56) ^ b) & 0xFF] ^ ((crc << 8) & 0xFFFFFFFFFFFFFFFF)
    return crc


def write_archive(path, files, compress=True):
    """files: list of (name, bytes). Writes a TTA4 archive (ZCTT when compress)."""
    files = sorted(files, key=lambda x: crc64(x[0].lower().encode('latin-1')))
    # name table split into 64 KiB pages; a name never straddles a page boundary
    names = bytearray()
    locs = []
    for name, _ in files:
        nb = name.encode('latin-1') + b'\0'
        page_left = CHUNK - (len(names) % CHUNK)
        if len(nb) > page_left:
            names += b'\0' * page_left
        locs.append(divmod(len(names), CHUNK))
        names += nb
    name_size = ((len(names) + CHUNK - 1) // CHUNK) * CHUNK
    names += b'\0' * (name_size - len(names))
    table = bytearray()
    data = bytearray()
    for (name, blob), (page, noff) in zip(files, locs):
        table += struct.pack('<QQIIHH', crc64(name.lower().encode('latin-1')), len(data), len(blob), 0, page, noff)
        data += blob
    body = struct.pack('<4sII', b'4ATT', name_size, len(files)) + table + bytes(names) + data
    # the game's archives pad the body to whole chunks; the engine fails to read a file
    # that lies in a short final chunk (blank dialog choices, no voice)
    body += b'\0' * (-len(body) % CHUNK)
    with open(path, 'wb') as out:
        if not compress:
            out.write(b'NCTT' + struct.pack('<Q', len(body)) + body)
            return
        chunks = []
        for i in range(0, len(body), CHUNK):
            co = zlib.compressobj(9, zlib.DEFLATED, -15)
            chunks.append(co.compress(body[i:i + CHUNK]) + co.flush())
        hdr_len = 12 + 8 * (len(chunks) + 1)
        offs = [hdr_len]
        for c in chunks:
            offs.append(offs[-1] + len(c))
        out.write(b'ZCTT' + struct.pack('<II', CHUNK, len(chunks)) + struct.pack('<%dQ' % len(offs), *offs))
        for c in chunks:
            out.write(c)
