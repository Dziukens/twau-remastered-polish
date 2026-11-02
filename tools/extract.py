"""Dump English lines for translation: work/en/<archive>__<file>.tsv with 'key<TAB>speaker<TAB>english'.

Each unique English text appears once (in the first file that uses it); keys already in the
translation memory are marked with '*' in front of the key.
"""
import os

from common import ROOT, SKIP_LANDB, english_landb_archives, ensure_outside_game, esc, load_tm, text_key
from landb import Landb
from prop import LANG_EN, Prop
from ttarch2 import Archive


def main():
    out_dir = os.path.join(ROOT, 'work', 'en')
    ensure_outside_game(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    tm = load_tm()
    seen = set()
    total = done = 0
    for path in english_landb_archives():
        a = Archive(path)
        tag = os.path.basename(path).replace('Fables_pc_', '').replace('.ttarch2', '')
        for name, *_ in a.entries:
            if not name.endswith('_english.landb') or name in SKIP_LANDB:
                continue
            rows = []
            for e in Landb(a.read(name)).entries:
                t = e['text']
                if not t.strip():
                    continue
                k = text_key(t)
                if k in seen:
                    continue
                seen.add(k)
                total += 1
                done += k in tm
                rows.append('%s%s\t%s\t%s' % ('*' if k in tm else '', k, e['speaker'], esc(t)))
            if rows:
                with open(os.path.join(out_dir, '%s__%s.tsv' % (tag, name[:-6])), 'w', encoding='utf-8') as f:
                    f.write('\n'.join(rows) + '\n')
    # end-of-episode choice statistics: English entries of the per-language string maps in choice.prop
    project = Archive(english_landb_archives()[-1])
    rows = []
    for key, t in Prop(project.read('choice.prop')).strings:
        k = text_key(t)
        if key != LANG_EN or not t.strip() or k in seen:
            continue
        seen.add(k)
        total += 1
        done += k in tm
        rows.append('%s%s\t\t%s' % ('*' if k in tm else '', k, esc(t)))
    with open(os.path.join(out_dir, 'Project_ar_all__choice_prop.tsv'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(rows) + '\n')
    print('unique lines: %d, translated: %d (%.1f%%)' % (total, done, 100.0 * done / max(total, 1)))


if __name__ == '__main__':
    main()
