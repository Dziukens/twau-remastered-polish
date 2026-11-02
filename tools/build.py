"""Build the Polish patch into output/Archives (never touches the game folder).

Produces:
  output/Archives/Fables_pc_Polish_ar_all.ttarch2  - translated *_english.landb + fonts with Polish glyphs
  output/Archives/_resdesc_50_Polish.lua           - registers the archive with a priority above the game's sets
"""
import collections
import os
import re
import sys

from common import ROOT, SKIP_LANDB, TAG, english_landb_archives, ensure_outside_game, load_tm, text_key
from landb import Landb
from polish_font import REMAP, patch_font
from prop import LANG_EN, Prop
from ttarch2 import Archive, write_archive

OUT = os.path.join(ROOT, 'output', 'Archives')
ARCHIVE_NAME = 'Fables_pc_Polish_ar_all.ttarch2'
MARKER = re.compile(r'<<[^>]*>>|\^[^^\n]*\^')

RESDESC = '''local set = {}
set.name = "Polish"
set.setName = "Polish"
set.descriptionFilenameOverride = ""
set.logicalName = "<Polish>"
set.logicalDestination = "<>"
set.priority = 950
set.localDir = _currentDirectory
set.enableMode = "constant"
set.version = "trunk"
set.descriptionPriority = 0
set.gameDataName = "Polish Game Data"
set.gameDataPriority = 0
set.gameDataEnableMode = "constant"
set.localDirIncludeBase = true
set.localDirRecurse = false
set.localDirIncludeOnly = nil
set.localDirExclude =
{
    "_dev/"
}
set.gameDataArchives =
{
    _currentDirectory .. "%s"
}
RegisterSetDescription(set)
''' % ARCHIVE_NAME


def tags(s):
    return sorted(t.lower().replace(' ', '') for t in TAG.findall(s)), sorted(MARKER.findall(s))


def main():
    conflicts = []
    tm = load_tm(conflicts)
    files = []
    problems = ['%s: redefined differently (first in %s)' % (later, first) for _, first, later in conflicts]
    stats = collections.Counter()
    seen_keys = set()

    # landb files whose name exists in several episode archives (ui_episode, ui_credits) are merged into
    # one file holding every episode's entries, since a single override replaces them in all episodes
    owners = collections.defaultdict(list)
    for path in english_landb_archives():
        for name, *_ in Archive(path).entries:
            if name.endswith('_english.landb'):
                owners[name].append(path)
    shared = collections.defaultdict(list)  # name -> [(Landb, texts)]
    for path in english_landb_archives():
        a = Archive(path)
        for name, *_ in a.entries:
            if not name.endswith('_english.landb') or name in SKIP_LANDB:
                continue
            L = Landb(a.read(name))
            new = {}
            for e in L.entries:
                t = e['text']
                if not t.strip():
                    continue
                stats['lines'] += 1
                seen_keys.add(text_key(t))
                hit = tm.get(text_key(t))
                if hit is None:
                    continue
                pl, where = hit
                if tags(pl) != tags(t):
                    problems.append('%s: tag mismatch, kept English\n    EN: %s\n    PL: %s' % (where, t, pl))
                    continue
                new[e['id']] = pl.translate(REMAP)
            stats['translated'] += len(new)
            if len(owners[name]) > 1:
                shared[name].append((L, new))
            elif new:
                files.append((name, L.rebuild(new)))
                Landb(files[-1][1])  # sanity: must parse back

    # "player choices" statistics live in Project's choice.prop, one string map per language;
    # the English entries are replaced (the game shows them for the English language setting)
    project = Archive(os.path.join(os.path.dirname(english_landb_archives()[0]), 'Fables_pc_Project_ar_all.ttarch2'))

    def choice_text(key, t):
        if key != LANG_EN or not t.strip():
            return None
        stats['lines'] += 1
        seen_keys.add(text_key(t))
        hit = tm.get(text_key(t))
        if hit is None:
            return None
        stats['translated'] += 1
        return hit[0].translate(REMAP)
    files.append(('choice.prop', Prop(project.read('choice.prop')).rebuild(choice_text)))
    Prop(files[-1][1])  # sanity: must parse back

    for key in sorted(set(tm) - seen_keys):
        problems.append('%s: key %s matches no English line (typo?)' % (tm[key][1], key))

    for name, parts in shared.items():
        texts = {}
        for _, new in parts:
            for rid, pl in new.items():
                texts.setdefault(rid, pl)
        if not texts:
            continue
        # base = a file without the build registry (all registries carry only build-folder metadata)
        parts.sort(key=lambda x: len(x[0].dbg_tail))
        files.append((name, Landb.merge([L for L, _ in parts], texts)))
        merged = Landb(files[-1][1])
        stats['merged_files'] += 1
        assert len(merged.entries) == len({e['id'] for L, _ in parts for e in L.entries})

    for name, *_ in project.entries:
        if name.endswith('.font'):
            data, built, aliased = patch_font(project.read(name))
            files.append((name, data))
            stats['fonts'] += 1
            if aliased:
                print('font %s: no style match for %s (uses plain letters)' % (name, ''.join(aliased)))

    ensure_outside_game(OUT)
    os.makedirs(OUT, exist_ok=True)
    write_archive(os.path.join(OUT, ARCHIVE_NAME), files)
    with open(os.path.join(OUT, '_resdesc_50_Polish.lua'), 'w', encoding='ascii', newline='\n') as f:
        f.write(RESDESC)

    check = Archive(os.path.join(OUT, ARCHIVE_NAME))
    for name, data in files:
        assert check.read(name) == data, name

    for p in problems:
        print(p)
    print('lines: %(lines)d, translated: %(translated)d, merged per-episode files: %(merged_files)d, '
          'fonts: %(fonts)d' % stats)
    print('landb files in patch: %d, tag problems: %d' % (sum(n.endswith('.landb') for n, _ in files), len(problems)))
    print('written to', OUT)
    return 1 if problems and '--strict' in sys.argv else 0


if __name__ == '__main__':
    sys.exit(main())
