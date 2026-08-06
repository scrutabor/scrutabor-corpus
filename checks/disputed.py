"""The list of what this edition is not sure about.

The quality doctrine promises a disputed list before an expert is asked to
review anything, and a promise like that decays: the list was written by
hand when the corpus held five texts and had fallen to a third of the
tokens by the time it held fifty-eight. So it is generated.

A token is on the list when it says so itself — `review: disputed`, or a
confidence below high — through the cascade SCHEMA.md defines: the word's
own analysis, else the document's word default, else the document default.
Identical forms are grouped, because "quǽsumus" ruled the same way in five
places is one question for a reviewer, not five.

    python3 -m checks.disputed            # for reading
    python3 -m checks.disputed --count    # just the numbers, for CI

Nothing here decides anything. It reports what the corpus already admits,
which is the only honest basis for asking someone else to look.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent


def defaults(doc: dict) -> dict:
    return doc.get('analysis_defaults_words') or doc.get('analysis_defaults') or {}


def collect() -> dict[str, list[tuple[str, str, str, str]]]:
    """form -> [(text id, word id, review, confidence)], for every token the
    corpus does not stand fully behind."""
    out: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for path in sorted((CORPUS / 'texts').rglob('*.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        base = defaults(doc)
        for seg in doc['segments']:
            for word in seg.get('words') or []:
                analysis = word.get('analysis') or {}
                review = analysis.get('review', base.get('review'))
                confidence = analysis.get('confidence', base.get('confidence'))
                if review == 'disputed' or confidence in ('medium', 'low'):
                    out[word['form']].append((doc['id'], word['id'], review, confidence))
    return out


def main(argv: list[str]) -> int:
    found = collect()
    tokens = sum(len(v) for v in found.values())
    if '--count' in argv:
        print(f'disputed_forms={len(found)} disputed_tokens={tokens}')
        return 0
    print(f'{tokens} tokens under {len(found)} distinct forms.\n')
    # the ones that recur are the ones worth a reviewer's time first
    for form, where in sorted(found.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        flags = {f'{r}/{c}' for _, _, r, c in where}
        print(f'{form}  ({len(where)}×, {", ".join(sorted(flags))})')
        for text_id, word_id, _, _ in where:
            print(f'    {text_id}.{word_id}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
