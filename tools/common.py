import glob
import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.environ.get('TWAU_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\The Wolf Among Us Remastered')
ARCHIVES = os.path.join(GAME, 'Archives')
TRANS_DIR = os.path.join(ROOT, 'translations')
TAG = re.compile(r'\{[^}]*\}')
# achievements are shown by Steam from its own servers, so the project does not translate them
SKIP_LANDB = {'ui_achievements_english.landb'}


def ensure_outside_game(path):
    """The tools only read the game; installing the patch is left to the user, by hand."""
    game = os.path.normcase(os.path.realpath(GAME))
    target = os.path.normcase(os.path.realpath(path))
    try:
        inside = os.path.commonpath([game, target]) == game
    except ValueError:  # different drives
        inside = False
    if inside:
        raise SystemExit('refusing to write into the game folder: %s\n'
                         'keep the project outside the game and copy output/Archives by hand' % path)


def text_key(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:10]


def english_landb_archives():
    """Archives that contain *_english.landb files (data archives + Project)."""
    out = sorted(glob.glob(os.path.join(ARCHIVES, '*_ar_data.ttarch2')))
    out.append(os.path.join(ARCHIVES, 'Fables_pc_Project_ar_all.ttarch2'))
    return out


def esc(s):
    return s.replace('\\', '\\\\').replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n')


def unesc(s):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}.get(m.group(1), '\\' + m.group(1)), s)


def load_tm(conflicts=None):
    """translations/*.tsv: lines 'key<TAB>polish'. Later files win; differing redefinitions are
    appended to `conflicts` as (key, earlier_location, later_location)."""
    tm = {}
    for path in sorted(glob.glob(os.path.join(TRANS_DIR, '*.tsv'))):
        with open(path, encoding='utf-8') as f:
            for n, line in enumerate(f, 1):
                line = line.rstrip('\n')
                if not line or line.startswith('#'):
                    continue
                key, _, pl = line.partition('\t')
                key, entry = key.strip(), (unesc(pl), '%s:%d' % (os.path.basename(path), n))
                if conflicts is not None and key in tm and tm[key][0] != entry[0]:
                    conflicts.append((key, tm[key][1], entry[1]))
                tm[key] = entry
    return tm
