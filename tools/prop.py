"""Read and rewrite strings in Telltale PropertySet (.prop) files, MSV6 layout.

PropertySet: u32 version, u32 flags, u32 size (from this field to the end of the set), u32 ?,
    u32 type count, per type { u64 type symbol, u32 count, count x (u64 key symbol, value) }
Values handled: String (u32 length + utf-8 bytes) and nested PropertySet; other types are not used
by the files this module is applied to (choice.prop), so meeting one is an error.
"""
import struct

T_STRING = 0xCD9C6E605F5AF4B4
T_PROPSET = 0xCD75DC4F6B9F15D2
LANG_EN = 0x51B8A88CAD6DA2B1  # language key of the English text in choice.prop string maps


class Prop:
    def __init__(self, data):
        d = self.data = data
        assert d[:4] == b'6VSM', d[:4]
        self.def_size, self.dbg_size, self.async_size, nver = struct.unpack_from('<IIII', d, 4)
        self.ds = 20 + 12 * nver
        self.strings = []  # (key, text) in file order
        end = self._walk(self.ds, bytearray(), collect=True)
        assert end == self.ds + self.def_size, (end, self.ds + self.def_size)

    def _walk(self, pos, out, replace=None, collect=False):
        d = self.data
        size = struct.unpack_from('<I', d, pos + 8)[0]
        end = pos + 8 + size
        ntypes = struct.unpack_from('<I', d, pos + 16)[0]
        p = pos + 20
        body = bytearray()
        for _ in range(ntypes):
            tsym, count = struct.unpack_from('<QI', d, p)
            body += d[p:p + 12]
            p += 12
            for _ in range(count):
                key = struct.unpack_from('<Q', d, p)[0]
                body += d[p:p + 8]
                p += 8
                if tsym == T_STRING:
                    n = struct.unpack_from('<I', d, p)[0]
                    raw = d[p + 4:p + 4 + n]
                    p += 4 + n
                    if collect:
                        self.strings.append((key, raw.decode('utf-8')))
                    new = replace(key, raw.decode('utf-8')) if replace else None
                    if new is not None:
                        raw = new.encode('utf-8')
                    body += struct.pack('<I', len(raw)) + raw
                elif tsym == T_PROPSET:
                    sub = bytearray()
                    p = self._walk(p, sub, replace, collect)
                    body += sub
                else:
                    raise ValueError('unsupported property type %016x at %d' % (tsym, p))
        assert p == end, (p, end)
        hdr = bytearray(d[pos:pos + 20])
        struct.pack_into('<I', hdr, 8, len(body) + 12)
        out += hdr + body
        return end

    def rebuild(self, replace):
        """replace(key, text) -> new text or None. Returns new file bytes."""
        d = self.data
        top = bytearray()
        self._walk(self.ds, top, replace)
        out = bytearray(d[:self.ds]) + top
        struct.pack_into('<I', out, 4, len(top))
        return bytes(out) + d[self.ds + self.def_size:]
