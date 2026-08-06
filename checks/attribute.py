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


# ---------------------------------------------------------------------------
# How loudly, from the rite's own law.
#
# Rubricae generales Missalis romani IX, n. 511 (transcribed in
# witnesses/raw/mr-rubricae-generales-ix.txt) lists what is said CLARA VOCE
# at low Mass and closes: "Cetera dicuntur secreto." So the list below is
# the exceptions, and the closing sentence supplies everything else — which
# is why a text absent from this table is secreto rather than unknown.
#
# This is what the rubrics inside our own texts could not give us: the
# Canon's silence is established once, in the law, and never repeated on
# the page.
#
# n. 512 defines the terms: what is said secreto he pronounces "ut ipsemet
# se audiat, et a circumstantibus non audiatur" — audible to himself, not
# to the bystanders. Submissa is the Ritus servandus's own middle voice,
# elata aliquantulum voce, for words the people are meant to catch.
CLARA = 'clara'
SECRETO = 'secreto'
SUBMISSA = 'submissa'

VOICE_RULINGS: dict[str, tuple[str, str]] = {
    # 511 a — the prayers at the foot of the altar, up to Oremus inclusive
    'ordinarium.introibo': (CLARA, 'RG 511 a'),
    'ordinarium.iudica-me': (CLARA, 'RG 511 a'),
    'ordinarium.adiutorium': (CLARA, 'RG 511 a — "ea quae sequuntur usque ad Oremus"'),
    'ordinarium.confiteor': (CLARA, 'RG 511 a — confessio'),
    'ordinarium.misereatur': (CLARA, 'RG 511 a'),
    'ordinarium.confiteor-sacerdotis': (CLARA, 'RG 511 a — confessio'),
    'ordinarium.misereatur-tui': (CLARA, 'RG 511 a'),
    'ordinarium.deus-tu-conversus': (CLARA, 'RG 511 a'),
    # 511 a names two prayers as secret inside that same passage
    'ordinarium.aufer-a-nobis': (SECRETO, 'RG 511 a — "Aufer a nobis ... dicuntur secreto"'),
    # 511 b, c, f, h — the sung ordinary and the preface
    'ordinarium.kyrie': (CLARA, 'RG 511 b'),
    'ordinarium.gloria': (CLARA, 'RG 511 c'),
    'ordinarium.credo': (CLARA, 'RG 511 f — symbolum'),
    'ordinarium.praefatio-dialogus': (CLARA, 'RG 511 h'),
    'ordinarium.praefatio-communis': (CLARA, 'RG 511 h'),
    'ordinarium.sanctus': (CLARA, 'RG 511 h'),
    # 511 i — from the Pater noster to the communion of the faithful
    'ordinarium.pater-noster': (CLARA, 'RG 511 i — oratio dominica cum sua praefatione'),
    'ordinarium.pax-domini': (CLARA, 'RG 511 i'),
    'ordinarium.agnus-dei': (CLARA, 'RG 511 i'),
    'ordinarium.ecce-agnus-dei': (CLARA, 'RG 511 i — formulae ad Communionem fidelium'),
    # 511 l — the dismissal, the blessing, the last gospel
    'ordinarium.ite-missa-est': (CLARA, 'RG 511 l'),
    'ordinarium.benedictio': (CLARA, 'RG 511 l'),
    'ordinarium.evangelium-ultimum': (CLARA, 'RG 511 l'),
    # Cetera dicuntur secreto — the offertory, the whole Canon, the prayers
    # before and after communion, the Placeat
    'ordinarium.suscipe-sancte-pater': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.deus-qui-humanae': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.offerimus-tibi': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.in-spiritu-humilitatis': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.lavabo': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.suscipe-sancta-trinitas': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.te-igitur': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.memento-vivorum': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.communicantes': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.hanc-igitur': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.quam-oblationem': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.qui-pridie': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.simili-modo': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.unde-et-memores': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.supra-quae': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.supplices-te-rogamus': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.memento-defunctorum': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.nobis-quoque': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.per-quem-haec-omnia': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.per-ipsum': (SECRETO, 'RG 500, 511 — Canon Missae secreto'),
    'ordinarium.libera-nos': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.haec-commixtio': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.qui-dixisti': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.fili-dei-vivi': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.perceptio-corporis': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.panem-caelestem': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.quid-retribuam': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.quod-ore-sumpsimus': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.corpus-tuum': (SECRETO, 'RG 511 — cetera'),
    'ordinarium.placeat-tibi': (SECRETO, 'RG 511 — cetera'),
}

# Segments whose voice differs from their text's, and why. These are the
# places the law names a few WORDS rather than a prayer.
VOICE_SEGMENT_RULINGS: dict[str, tuple[str, str]] = {
    # the conclusions the people answer, inside otherwise silent prayers
    'ordinarium.libera-nos.s12': (CLARA, 'RG 511 i — Per omnia saecula saeculorum'),
    'ordinarium.libera-nos.s13': (CLARA, 'RG 511 i — the answering Amen'),
    'ordinarium.per-ipsum.s08': (CLARA, 'RG 511 i — Per omnia saecula saeculorum'),
    'ordinarium.per-ipsum.s09': (CLARA, 'RG 511 i — the answering Amen'),
    # words the people are meant to catch: RG 511 i puts them among what is
    # said aloud, and the Ritus servandus gives the manner, elata
    # aliquantulum voce — a raised voice, not a full one
    'ordinarium.nobis-quoque.s02': (SUBMISSA, 'RG 511 i + RS VIII — elata aliquantulum voce'),
    'ordinarium.panem-caelestem.s04': (SUBMISSA, 'RG 511 i + RS X — Domine, non sum dignus'),
    'ordinarium.panem-caelestem.s07': (SUBMISSA, 'RG 511 i + RS X — the second time'),
    'ordinarium.panem-caelestem.s10': (SUBMISSA, 'RG 511 i + RS X — the third time'),
    # The Pater noster is said aloud (511 i), but the priest answers his own
    # last petition under his breath, and the page says so where the law does
    # not reach: "Sacerdos secrete dicit:". The specific rubric governs.
    'ordinarium.pater-noster.s14': (SECRETO, 'the text\'s own rubric — Sacerdos secrete dicit'),
    # the server answers aloud, and the priest is silent under him
    'ordinarium.orate-fratres.s04': (CLARA, 'RG 511 g — the answering Suscipiat'),
    'ordinarium.orate-fratres.s06': (CLARA, 'RG 511 g — the answering Amen'),
}

# Segments the law splits but our segmentation does not, so no single value
# is true of them. Left unattributed on purpose, with the reason here.
VOICE_UNSETTLED: dict[str, str] = {
    'ordinarium.orate-fratres.s02': (
        'RG 511 g names only the words "Orate, fratres" as said aloud, and the '
        'Ritus servandus has the priest continue "ut meum ac vestrum sacrificium" '
        'secreto. This segment holds both, so neither value is true of it; '
        'splitting the segment would renumber its words.'
    ),
}


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


def propose(doc, disagreements: list[str] | None = None) -> dict[str, dict]:
    lines = marked_lines(doc['id'])
    ruled = VOICE_RULINGS.get(doc['id'])
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

        ref = f"{doc['id']}.{seg['id']}"
        # The law first, then what the text's own rubrics say. Where the two
        # disagree the law wins and the disagreement is REPORTED, because a
        # rubric read one way and a rubric read the other way is a finding,
        # not a detail to settle silently.
        from_rubric = voice_of(doc, i)
        if ref in VOICE_UNSETTLED:
            pass  # named in the table above: no single value is true of it
        elif ref in VOICE_SEGMENT_RULINGS:
            proposal['voice'] = VOICE_SEGMENT_RULINGS[ref][0]
        elif ruled:
            proposal['voice'] = ruled[0]
        elif from_rubric:
            proposal['voice'] = from_rubric

        if disagreements is not None and from_rubric and 'voice' in proposal:
            if from_rubric != proposal['voice']:
                cite = (VOICE_SEGMENT_RULINGS.get(ref) or ruled or ('', '?'))[1]
                disagreements.append(
                    f"{ref}: the text's rubric reads {from_rubric}, "
                    f"{cite} rules {proposal['voice']}"
                )
        if proposal:
            out[seg['id']] = proposal
    return out


def main() -> None:
    write = '--write' in sys.argv
    total = attributed = voiced = 0
    disagreements: list[str] = []
    for path in sorted((CORPUS / 'texts').rglob('*.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        proposal = propose(doc, disagreements)
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
        # Two passes. The first learns which segments already carry a
        # speaker or a voice, because those lines come AFTER the "type"
        # line where a new one would be inserted — write in one pass and
        # every existing value gets a twin, which JSON accepts silently.
        # Words carry a morph "voice" of their own (act, pass, dep), and
        # some are written across several lines — so a key line counts as
        # the SEGMENT's only when it is indented exactly like the segment's
        # own "id". Matching on the name alone deletes verb voices.
        existing: dict[str, set[str]] = {}
        current, seg_indent = None, ''
        for line in lines:
            m = re.match(r'(\s*)"id": "(s\d+)",', line)
            if m:
                current, seg_indent = m.group(2), m.group(1)
            m_key = re.match(r'(\s*)"(speaker|voice)": "[a-z]+",', line)
            if current and m_key and m_key.group(1) == seg_indent:
                existing.setdefault(current, set()).add(m_key.group(2))

        out, current, seg_indent, changed = [], None, '', False
        for line in lines:
            m = re.match(r'(\s*)"id": "(s\d+)",', line)
            if m:
                current, seg_indent = m.group(2), m.group(1)
            m_key = re.match(r'(\s*)"(speaker|voice)": "[a-z]+",', line)
            if current and m_key and m_key.group(1) == seg_indent:
                key = m_key.group(2)
                value = (proposal.get(current) or {}).get(key)
                if value is None:
                    changed = True  # no longer proposed: drop the stale claim
                    continue
                indent = re.match(r'(\s*)', line).group(1)
                replacement = f'{indent}"{key}": "{value}",\n'
                if replacement != line:
                    changed = True
                out.append(replacement)
                continue
            out.append(line)
            if current and re.match(r'\s*"type": "verse",', line):
                p_ = proposal.get(current) or {}
                indent = re.match(r'(\s*)', line).group(1)
                for key in ('speaker', 'voice'):
                    if key in p_ and key not in existing.get(current, set()):
                        out.append(f'{indent}"{key}": "{p_[key]}",\n')
                        changed = True
        if changed:
            path.write_text(''.join(out), encoding='utf-8')
    for line in disagreements:
        print(f'DISAGREES  {line}')
    verb = 'applied' if write else 'proposed'
    print(f'\n{verb} {attributed}/{total} speakers, {voiced}/{total} voices'
          f' ({len(disagreements)} rubric/law disagreements)')


if __name__ == '__main__':
    main()
