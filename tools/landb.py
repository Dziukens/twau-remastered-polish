"""Parse and rebuild Telltale LanguageDB (.landb) files, MSV6 layout used by TWAU Remastered.

Default section layout:
    block u32, block u32, map block { u32 count, entries... }, trailing fields
Each map entry: u32 key, LanguageResource:
    u64 ?, u32 id, u32 ?, block, block, block, u32 ?,
    LanguageResLocal block { String prefix (speaker), String text, block flags },
    block, u32 flags
Strings are serialized as a block: u32 blockSize (incl. itself), u32 len, utf-8 bytes.
"""
import struct


def _u32(d, p):
    return struct.unpack_from('<I', d, p)[0]


class Landb:
    def __init__(self, data):
        d = self.data = data
        assert d[:4] == b'6VSM', d[:4]
        self.def_size, self.dbg_size, self.async_size, nver = struct.unpack_from('<IIII', d, 4)
        self.ds = 20 + 12 * nver
        p = self.ds
        p += _u32(d, p)  # block
        p += _u32(d, p)  # block
        self.map_pos = p
        map_end = p + _u32(d, p)
        count = _u32(d, p + 4)
        p += 8
        self.entries = []
        for _ in range(count):
            key, _sym, rid = struct.unpack_from('<IQI', d, p)
            q = p + 20
            for _ in range(3):
                q += _u32(d, q)
            q += 4
            lrl = q
            lrl_end = q + _u32(d, q)
            sp = lrl + 4
            speaker_pos = sp
            sp += _u32(d, sp)
            text_pos = sp
            sp += _u32(d, sp)
            sp += _u32(d, sp)
            assert sp == lrl_end, 'LanguageResLocal layout mismatch'
            q = lrl_end
            q += _u32(d, q)
            q += 4
            self.entries.append(dict(key=key, id=rid, lrl=lrl, speaker_pos=speaker_pos, text_pos=text_pos,
                                     speaker=self._str(speaker_pos), text=self._str(text_pos), start=p, end=q))
            p = q
        assert p == map_end, 'map size mismatch'
        self.map_end = map_end
        assert self.ds + self.def_size + self.dbg_size + self.async_size == len(d)
        # debug section: three plain strings per entry (resource name, anim and voice debug names)
        p = self.ds + self.def_size
        for e in self.entries:
            s = p
            for _ in range(3):
                p += 4 + _u32(d, p)
            e['dbg'] = d[s:p]
        # some files append registry debug names (build folder names) after the per-entry records
        self.dbg_tail = d[p:self.ds + self.def_size + self.dbg_size]
        self.dbg_ok = p <= self.ds + self.def_size + self.dbg_size and not self.async_size

    def _str(self, pos):
        n = _u32(self.data, pos + 4)
        raw = self.data[pos + 8:pos + 8 + n]
        try:
            return raw.decode('utf-8')
        except UnicodeDecodeError:  # a few original lines are stored as cp1252
            return raw.decode('cp1252', errors='replace')

    def entry_bytes(self, e, new_text=None):
        """Raw serialized map entry, optionally with its text replaced."""
        d = self.data
        if new_text is None:
            return d[e['start']:e['end']]
        new = new_text.encode('utf-8')
        old_len = _u32(d, e['text_pos'] + 4)
        delta = len(new) - old_len
        out = bytearray(d[e['start']:e['text_pos']])
        out += struct.pack('<II', 8 + len(new), len(new)) + new
        out += d[e['text_pos'] + 8 + old_len:e['end']]
        lrl = e['lrl'] - e['start']
        struct.pack_into('<I', out, lrl, _u32(out, lrl) + delta)
        return bytes(out)

    @staticmethod
    def merge(landbs, texts):
        """One landb holding the entries of all given files (first occurrence of an id wins),
        with texts {id: new_text} applied. Header and trailing fields come from the first file."""
        base = landbs[0]
        assert all(L.dbg_ok for L in landbs)
        seen = {}
        for L in landbs:
            for e in L.entries:
                if e['id'] not in seen:
                    seen[e['id']] = (L, e)
        items = sorted(seen.values(), key=lambda x: x[1]['key'])
        body = bytearray()
        dbg = bytearray()
        for L, e in items:
            body += L.entry_bytes(e, texts.get(e['id']))
            dbg += e['dbg']
        d = base.data
        out = bytearray(d[:base.map_pos])
        out += struct.pack('<II', 8 + len(body), len(items)) + body
        out += d[base.map_end:base.ds + base.def_size]
        dbg += base.dbg_tail
        def_size = len(out) - base.ds
        struct.pack_into('<III', out, 4, def_size, len(dbg), 0)
        return bytes(out + dbg)

    def rebuild(self, texts):
        """texts: {id: new_text}. Returns new file bytes."""
        d = self.data
        out = bytearray()
        cur = 0
        delta_total = 0
        lrl_fix = []  # (new lrl position, delta)
        for e in self.entries:
            if e['id'] not in texts:
                continue
            new = texts[e['id']].encode('utf-8')
            old_len = _u32(d, e['text_pos'] + 4)
            out += d[cur:e['text_pos']]
            out += struct.pack('<II', 8 + len(new), len(new)) + new
            cur = e['text_pos'] + 8 + old_len
            lrl_fix.append((e['lrl'] + delta_total, len(new) - old_len))
            delta_total += len(new) - old_len
        out += d[cur:]
        for pos, delta in lrl_fix:
            struct.pack_into('<I', out, pos, _u32(out, pos) + delta)
        struct.pack_into('<I', out, self.map_pos, _u32(out, self.map_pos) + delta_total)
        struct.pack_into('<I', out, 4, self.def_size + delta_total)
        return bytes(out)
