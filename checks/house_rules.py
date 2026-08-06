"""Adjudicate the two differences this edition has by DECLARED RULE.

Every witness printed in a different house style disagrees with us in the
same two ways, over and over:

  * **i for j.** The typical edition sets iube, maiestatis, Ioannem where
    ORTHOGRAPHY.md prints jube, majestatis, Joannem.
  * **accents on capitals.** This edition accents them; most printings do
    not, so Ángeli meets Angeli and Ómnia meets Omnia.

Neither is a variant anyone needs to think about a second time: the rule
is declared, the reason is the same every time, and writing the ruling by
hand for each token invites a slip in the one entry that is not one of
these. So the two are generated — and ONLY the two. Anything else the
collation flags is left alone and reported, because a difference that is
not one of these is a difference someone has to read.

    python3 -m checks.house_rules <text-id> [--write]

Run it after adding a witness; whatever it reports as unhandled is the
real work.
"""

import json
import sys
import unicodedata
from pathlib import Path

from .collate import corpus_tokens, load_witness

CORPUS = Path(__file__).resolve().parent.parent

IJ_RULING = (
    "The i-form against this edition's j-form, by the house rule in ORTHOGRAPHY.md. Neither is a "
    "different word and neither page is wrong: the two orthographies are the conventions in which "
    "the same Latin has been printed for centuries, and this edition prints j."
)
CAPITAL_RULING = (
    "This edition accents capitals, by the house rule in ORTHOGRAPHY.md, because the accent tells a "
    "reader where the stress falls and a capital does not stop being a syllable. Most printings omit "
    "them; the reading is identical."
)


def bare(word: str) -> str:
    d = unicodedata.normalize('NFD', word)
    return ''.join(c for c in d if unicodedata.category(c) != 'Mn')


def classify(ours: str, theirs: str) -> tuple[str, str] | None:
    """('orthography'|'capital-accent', ruling) if a declared rule explains
    the difference, else None."""
    if bare(ours) == bare(theirs) and ours != theirs:
        # same letters, different accents — only ours may carry more
        if bare(ours) == ours.replace('́', '') and theirs == bare(theirs):
            return 'capital-accent', CAPITAL_RULING
        if theirs == bare(theirs):
            return 'capital-accent', CAPITAL_RULING
    fold = lambda w: bare(w).lower().replace('j', 'i').replace('v', 'u')
    if fold(ours) == fold(theirs) and ours != theirs:
        if ('j' in ours or 'J' in ours) and ('i' in theirs or 'I' in theirs):
            return 'orthography', IJ_RULING
    return None


def main(argv: list[str]) -> int:
    if not argv:
        print('usage: python3 -m checks.house_rules <text-id> [--write]')
        return 2
    text_id = argv[0]
    write = '--write' in argv
    category, name = text_id.split('.', 1)
    doc = json.loads((CORPUS / 'texts' / category / f'{name}.json').read_text(encoding='utf-8'))
    wdir = CORPUS / 'witnesses' / text_id
    apath = wdir / 'apparatus.json'
    apparatus = json.loads(apath.read_text(encoding='utf-8'))
    by_at = {e['at']: e for e in apparatus['adjudicated']}

    toks = corpus_tokens(doc)
    handled, unhandled = 0, []
    for wf in sorted(wdir.glob('*.txt')):
        meta, text = load_witness(wf)
        wid = meta.get('witness', wf.stem)
        wit = text.split()
        if len(wit) != len(toks):
            continue
        for (at, ours), theirs in zip(toks, wit):
            if ours == theirs:
                continue
            entry = by_at.get(at)
            if entry and entry['witnesses'].get(wid) == theirs:
                continue
            verdict = classify(ours, theirs)
            if verdict is None:
                unhandled.append(f'{at}: ours={ours!r} {wid}={theirs!r}')
                continue
            cls, ruling = verdict
            if entry is None:
                entry = {'at': at, 'ours': ours, 'witnesses': {}, 'class': cls, 'ruling': ruling}
                by_at[at] = entry
                apparatus['adjudicated'].append(entry)
            entry['witnesses'][wid] = theirs
            handled += 1

    if write and handled:
        apparatus['adjudicated'].sort(key=lambda e: e['at'])
        apath.write_text(json.dumps(apparatus, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{text_id}: {handled} by declared rule, {len(unhandled)} needing a reading')
    for line in unhandled:
        print(f'   {line}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
