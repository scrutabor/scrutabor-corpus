"""Propose who says each verse segment, and how loudly, FROM THE SOURCES.

Two facts a missal makes visible on the page and this corpus could not
say: who is speaking, and whether it is said aloud. Both are recoverable
rather than remembered.

WHO comes from the witnesses' own markers. The Divinum Officium files
print S. (sacerdos), M. (minister), V. and R. (a versicle and its
response, the priest's voice and the answering one), O. (omnes); the
transcriptions strip them, and every witness header says so. Each witness
header also records the lines it was taken from, so a text's segments are
matched against exactly those lines and not against the whole book.

HOW LOUDLY comes from the rubrics the corpus already carries. A rubric
saying *secreto* governs what follows until another rubric lifts it;
*clara voce* and *intellegibili voce* restore the ordinary voice; *elata
aliquantulum voce* is the raised-but-not-full voice of Domine non sum
dignus. A text whose rubrics say nothing is left unattributed rather than
assumed — silence here means "not read yet", not "spoken aloud".

Run it to see the proposal, or with --write to apply it:

    python3 -m checks.attribute            # print
    python3 -m checks.attribute --write    # apply

It never guesses: a segment it cannot source stays empty, and the check
in run_checks reports the coverage so the gap is visible.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent

MARKERS = {'S': 'sacerdos', 'M': 'minister', 'V': 'sacerdos', 'R': 'minister', 'O': 'omnes'}

# Rubric phrases that set the voice, longest first so that "elata
# aliquantulum voce" is not read as the plain "voce".
VOICE_RUBRICS = [
    ('elata aliquantulum voce', 'submissa'),
    ('intellegibili voce', 'clara'),
    ('intelligibili voce', 'clara'),
    ('clara voce', 'clara'),
    ('secreto', 'secreto'),
    ('secrete', 'secreto'),
]


def flatten(text: str) -> str:
    """Letters only, unaccented, u/v and i/j folded — enough to match a
    transcription against its own source across punctuation and accent
    conventions, not enough to match a different text."""
    s = unicodedata.normalize('NFD', text)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('æ', 'ae').replace('Æ', 'Ae').replace('œ', 'oe').replace('Œ', 'Oe')
    s = s.replace('j', 'i').replace('J', 'I').replace('v', 'u').replace('V', 'U')
    return re.sub(r'[^a-z]', '', s.lower())


def witness_ranges(text_id: str) -> list[tuple[Path, int, int]]:
    """(raw file, first line, last line) for each witness that records one."""
    out = []
    wdir = CORPUS / 'witnesses' / text_id
    if not wdir.is_dir():
        return out
    for wf in sorted(wdir.glob('*.txt')):
        header = wf.read_text(encoding='utf-8')
        # ranges are written as a human writes them: "lines 203-208", and
        # also "lines 5, 11-12" where the transcription skips a line. Take
        # the span from the first number to the last — a superset of the
        # text, which is all this needs to stop reading the whole book.
        m = re.search(r'#\s*path:[^(]*\(lines ([\d,\s-]+)\)', header)
        if not m:
            continue
        numbers = [int(n) for n in re.findall(r'\d+', m.group(1))]
        if not numbers:
            continue
        src = re.search(r'([\w.-]+\.txt)', re.search(r'#\s*path:\s*(\S+)', header).group(1))
        raw = CORPUS / 'witnesses' / 'raw'
        # the raw archives are named for the file they came from; match on stem
        for candidate in sorted(raw.glob('*.txt')):
            if src and Path(src.group(1)).stem.lower() in candidate.stem.lower().replace('-', ''):
                out.append((candidate, min(numbers), max(numbers)))
                break
    return out


def marked_lines(text_id: str) -> list[tuple[str, str]]:
    """(speaker, flattened text) for the marked lines of this text's own
    span in the archived sources; falls back to every archive when a
    witness records no line range."""
    spans = witness_ranges(text_id)
    files: list[list[str]] = []
    if spans:
        for raw, first, last in spans:
            lines = raw.read_text(encoding='utf-8').splitlines()
            files.append(lines[max(0, first - 1) : last])
    else:
        for raw in sorted((CORPUS / 'witnesses' / 'raw').glob('*.txt')):
            files.append(raw.read_text(encoding='utf-8').splitlines())
    out = []
    for lines in files:
        for line in lines:
            m = re.match(r'^([SMVRO])\.\s+(.*)$', line.strip())
            if m and m.group(2).strip():
                out.append((MARKERS[m.group(1)], flatten(m.group(2))))
    return out


def voice_of(doc, index: int) -> str | None:
    """The voice the nearest preceding rubric sets, if any says."""
    for seg in reversed(doc['segments'][:index]):
        if seg.get('type') != 'rubric':
            continue
        rubric = flatten(seg.get('text', ''))
        for phrase, voice in VOICE_RUBRICS:
            if flatten(phrase) in rubric:
                return voice
    return None


def propose(doc) -> dict[str, dict]:
    lines = marked_lines(doc['id'])
    out: dict[str, dict] = {}
    for i, seg in enumerate(doc['segments']):
        if seg.get('type') != 'verse':
            continue
        words = seg.get('words') or []
        if not words:
            continue
        key = flatten(''.join(w['form'] for w in words))
        hits = {speaker for speaker, line in lines if key and (key == line or key in line)}
        proposal = {}
        if len(hits) == 1:
            proposal['speaker'] = hits.pop()
        voice = voice_of(doc, i)
        if voice:
            proposal['voice'] = voice
        if proposal:
            out[seg['id']] = proposal
    return out


def main() -> None:
    write = '--write' in sys.argv
    total = attributed = voiced = 0
    for path in sorted((CORPUS / 'texts').rglob('*.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        proposal = propose(doc)
        verses = [s for s in doc['segments'] if s.get('type') == 'verse' and s.get('words')]
        total += len(verses)
        attributed += sum(1 for p in proposal.values() if 'speaker' in p)
        voiced += sum(1 for p in proposal.values() if 'voice' in p)
        if not write:
            if proposal:
                print(f"{doc['id']}")
                for sid, p in proposal.items():
                    print(f"   {sid:5} {p.get('speaker', '-'):10} {p.get('voice', '-')}")
            continue
        # Insert by TEXT, not by re-serializing: these documents are
        # hand-formatted (analysis blocks sit on one line) and a round trip
        # through json.dumps would reformat every file it touches, burying
        # two added fields in seventeen thousand changed lines.
        lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        out, current, changed = [], None, False
        for line in lines:
            m = re.match(r'(\s*)"id": "(s\d+)",', line)
            if m:
                current = m.group(2)
            out.append(line)
            if current and re.match(r'\s*"type": "verse",', line):
                p_ = proposal.get(current)
                if p_:
                    indent = re.match(r'(\s*)', line).group(1)
                    for key in ('speaker', 'voice'):
                        if key in p_:
                            out.append(f'{indent}"{key}": "{p_[key]}",\n')
                            changed = True
        if changed:
            path.write_text(''.join(out), encoding='utf-8')
    verb = 'applied' if write else 'proposed'
    print(f'\n{verb} {attributed}/{total} speakers, {voiced}/{total} voices')


if __name__ == '__main__':
    main()
