"""Validate translations/*.tsv against the extracted English text (work/en) and the built patch.

Writes work/validation_report.txt and prints a summary. Checks:
  orphan      key matches no English line
  tags        {emotion} tags / <<markers>> / ^font^ differ (build keeps English for these)
  brackets    [stage directions] in a mixed line not kept verbatim
  same        Polish identical to English
  english     English words left outside brackets
  chars       characters outside ASCII + Polish letters that the English line does not use
  font        characters used in Polish missing from a patched font
  newlines    different number of line breaks than the English (subtitles may drop forced breaks)
  spaces      double / leading / trailing spaces, space before punctuation
  repeat      repeated word that the English does not repeat
  question    English asks a question, Polish does not (or the reverse)
  cutoff      English line is cut off ("--"), Polish is not
  glossary    untranslated proper names (Fabletown, Business Office, ...)
  gender      first-person verb form does not match the speaker's gender
  length      choice/UI line much longer than the English (button overflow risk)
  wrap        character above U+00FF left after the Latin-1 remap (engine breaks lines there)
  archive     every landb in the patch parses and keeps the original entry count; chunks are full
"""
import collections
import glob
import os
import re
import sys

from common import ROOT, TAG, ensure_outside_game, load_tm, unesc, english_landb_archives
from build import tags
from font import Font
from landb import Landb
from polish_font import REMAP
from ttarch2 import Archive

sys.stdout.reconfigure(encoding='utf-8')
EN_DIR = os.path.join(ROOT, 'work', 'en')
OUT_ARCH = os.path.join(ROOT, 'output', 'Archives', 'Fables_pc_Polish_ar_all.ttarch2')
REPORT = os.path.join(ROOT, 'work', 'validation_report.txt')

BRACKET = re.compile(r'\[[^\]]*\]')
POLISH = set('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ')
EN_WORDS = re.compile(r"\b(the|you|and|what|that|this|with|have|are|don't|it's|i'm|your|just|about|there|would)\b", re.I)
GLOSSARY = ['Fabletown', 'Business Office', 'Witching Well', 'Crooked Man', 'Snow White', 'Bluebeard',
            'Woodsman', 'Glamour', 'mundy', 'mundies', 'Homeland', 'Flycatcher', 'Bloody Mary', 'Mr. Toad',
            'Deputy Mayor', 'Thirteenth Floor', 'Book of Fables', 'Little Mermaid']
FEMALE = {'SNOW', 'HOLLY', 'HOLLYTROLL', 'BEAUTY', 'NERISSA', 'VIVIAN', 'MARY', 'GREENLEAF', 'KELSEY',
          'FAITH', 'RACHEL'}
MALE = {'BIGBY', 'BIGBYWERE', 'CRANE', 'TOAD', 'COLIN', 'BEAST', 'WOODSMAN', 'GREN', 'GRENDEL', 'JACK',
        'BLUEBEARD', 'BUFKIN', 'DEE', 'DUM', 'PORGIE', 'GEORGIE', 'SWINEHEART', 'FLYCATCHER', 'CROOKEDMAN',
        'JERSEY', 'JERSEYDEVIL', 'BUTCHER', 'TIM', 'CAKEPRINCE', 'KIDTOAD', 'MIRROR', 'HANS'}
FEM_1P = re.compile(r'\b\w+(łam|łabym|łam się)\b')
MASC_1P = re.compile(r'\b\w+(łem|łbym)\b')


def strip(s):
    return BRACKET.sub('', TAG.sub('', s))


def load_english():
    """key -> (speaker, text, [scene files])"""
    eng = {}
    for path in sorted(glob.glob(os.path.join(EN_DIR, '*.tsv'))):
        scene = os.path.basename(path)[:-4]
        with open(path, encoding='utf-8') as f:
            for line in f:
                key, speaker, text = line.rstrip('\n').split('\t', 2)
                key = key.lstrip('*')
                if key in eng:
                    eng[key][2].append(scene)
                else:
                    eng[key] = (speaker, unesc(text), [scene])
    return eng


def end_char(s):
    s = re.sub(r'(\s*(\{[^}]*\}|\[[^\]]*\]))+\s*$', '', s).rstrip()
    return s[-1:] if s else ''


def check_text(key, en, pl, speaker, add):
    if tags(en) != tags(pl):
        add('tags', 'EN: %s' % en)

    en_br, pl_br = BRACKET.findall(en), BRACKET.findall(pl)
    if strip(en).strip() and collections.Counter(en_br) != collections.Counter(pl_br):
        add('brackets', 'EN %s vs PL %s' % (en_br, pl_br))

    body_en, body_pl = strip(en).strip(), strip(pl).strip()
    if pl == en and re.search(r'[a-z]{3}', body_en) and len(body_en.split()) > 1:
        add('same', '')

    hits = EN_WORDS.findall(body_pl)
    # the credits roll keeps names and thank-you lists ("The Watkins Family", "Jen and Noah") in English
    if len(hits) >= 2 and en.count('\n') < 50:
        add('english', 'words: %s' % ', '.join(sorted(set(h.lower() for h in hits))))

    odd = sorted({c for c in pl if ord(c) > 127 and c not in POLISH and c not in en})
    if odd:
        add('chars', ' '.join('%s(U+%04X)' % (c, ord(c)) for c in odd))

    wide = sorted({c for c in pl.translate(REMAP) if ord(c) > 0xFF} - {c for c in en if ord(c) > 0xFF})
    if wide:
        add('wrap', 'characters above U+00FF (the game may break the line inside the word): ' + ' '.join(wide))

    # spoken subtitles wrap on their own, so a forced English break may be dropped there
    if pl.count('\n') > en.count('\n') or (pl.count('\n') < en.count('\n') and not speaker):
        add('newlines', 'EN %d vs PL %d' % (en.count('\n'), pl.count('\n')))

    probs = []
    if '  ' in pl and '  ' not in en:
        probs.append('double space')
    if pl != pl.strip() and en == en.strip():
        probs.append('leading/trailing space')
    if re.search(r'\w \?|\w \!(?!\!)|\w ,|\w \.(?!\.)', body_pl) and not re.search(r'\w [?!,.]', body_en):
        probs.append('space before punctuation')
    if probs:
        add('spaces', ', '.join(probs))

    rep_pl = {m.lower() for m in re.findall(r'\b(\w{3,}) \1\b', body_pl, re.I)}
    if rep_pl and not re.search(r'\b(\w+)[ ,.-]+\1\b', body_en, re.I):
        add('repeat', ', '.join(sorted(rep_pl)))

    e_en, e_pl = end_char(en), end_char(pl)
    if (e_en == '?') != (e_pl == '?') and e_en and e_pl:
        add('question', 'EN ends %r, PL ends %r' % (e_en, e_pl))
    if re.search(r'--\s*$', strip(en)) and not re.search(r'(--|-|\.\.\.)\s*$', strip(pl)):
        add('cutoff', '')

    for term in GLOSSARY:
        if re.search(r'\b%s\b' % re.escape(term), body_pl) and not re.search(r'\b%s\b' % re.escape(term), 'Lucky Pawn A Cut Above Open Arms Pudding Woodlands'):
            add('glossary', term)

    sp = speaker.upper()
    if sp in MALE and FEM_1P.search(body_pl):
        add('gender', '%s (male) uses %s' % (sp, FEM_1P.search(body_pl).group(0)))
    if sp in FEMALE and MASC_1P.search(body_pl):
        add('gender', '%s (female) uses %s' % (sp, MASC_1P.search(body_pl).group(0)))

    if not speaker and '\n' not in en and len(body_en) <= 40 and len(body_pl) > max(len(body_en) * 1.6, 30):
        add('length', '%d -> %d chars' % (len(body_en), len(body_pl)))


def check_fonts(used, add_global):
    arch = Archive(OUT_ARCH)
    for name, *_ in arch.entries:
        if not name.endswith('.font'):
            continue
        glyphs = Font(arch.read(name)).glyphs
        missing = sorted(c for c in used if ord(c) not in glyphs and c not in '\n\t')
        if missing:
            add_global('font', '%s: missing %s' % (name, ' '.join('%s(%d uses)' % (c, used[c]) for c in missing)))
        unmapped = [chr(src) for src, dst in REMAP.items() if src in glyphs and glyphs.get(dst) != glyphs[src]]
        if unmapped:
            add_global('font', '%s: Latin-1 substitute not drawn as %s' % (name, ' '.join(unmapped)))


def check_archive(add_global):
    out = Archive(OUT_ARCH)
    if out.compressed and len(out._chunk(len(out.chunk_offs) - 2)) != out.chunk_size:
        add_global('archive', 'last chunk is short; the game cannot read files stored in it')
    originals = {}
    for path in english_landb_archives():
        a = Archive(path)
        for name, *_ in a.entries:
            if name.endswith('_english.landb'):
                originals.setdefault(name, []).append(len(Landb(a.read(name)).entries))
    n = 0
    for name, *_ in out.entries:
        if not name.endswith('.landb'):
            continue
        n += 1
        try:
            count = len(Landb(out.read(name)).entries)
        except Exception as e:  # noqa: BLE001 - report any parse failure
            add_global('archive', '%s: parse error %s' % (name, e))
            continue
        orig = originals.get(name)
        if orig and len(orig) == 1 and count != orig[0]:
            add_global('archive', '%s: %d entries, original %d' % (name, count, orig[0]))
        if orig and len(orig) > 1 and count < max(orig):
            add_global('archive', '%s (merged): %d entries < largest original %d' % (name, count, max(orig)))
    return n


def main():
    eng = load_english()
    conflicts = []
    tm = load_tm(conflicts)
    findings = collections.defaultdict(list)
    used = collections.Counter()

    for key, (pl, loc) in tm.items():
        if key not in eng:
            findings['orphan'].append((loc, key, '', ''))
            continue
        speaker, en, scenes = eng[key]
        used.update(pl)

        def add(check, detail, loc=loc, key=key, pl=pl, scene=scenes[0]):
            findings[check].append((loc, key, detail, pl, scene))
        check_text(key, en, pl, speaker, add)

    def add_global(check, detail):
        findings[check].append(('', '', detail, ''))
    check_fonts(used, add_global)
    n_landb = check_archive(add_global)

    order = ['orphan', 'tags', 'archive', 'font', 'wrap', 'chars', 'newlines', 'brackets', 'gender', 'glossary',
             'english', 'same', 'question', 'cutoff', 'repeat', 'spaces', 'length']
    ensure_outside_game(REPORT)
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write('Validation report: %d translated keys, %d landb files in patch, %d conflicts\n\n'
                % (len(tm), n_landb, len(conflicts)))
        for c in conflicts:
            f.write('CONFLICT %s: %s vs %s\n' % c)
        for check in order:
            items = findings.get(check, [])
            f.write('=== %s (%d)\n' % (check, len(items)))
            for it in sorted(items):
                loc, key, detail, pl = it[:4]
                f.write('%s %s %s\n    PL: %s\n' % (loc, key, detail, pl) if key else '%s\n' % detail)
            f.write('\n')
    print('translated keys: %d, landb files: %d, conflicts: %d' % (len(tm), n_landb, len(conflicts)))
    for check in order:
        print('%-10s %d' % (check, len(findings.get(check, []))))
    print('report:', REPORT)


if __name__ == '__main__':
    main()
