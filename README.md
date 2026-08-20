# Scrutabor corpus

Word-by-word annotated Latin sacral texts — the traditional Roman liturgy
(1962 Missale Romanum) first, the Church's common prayers as the corpus
grows — with gloss layers in Polish and English.

Every Latin word carries its lemma, a full morphological analysis, a
reading gloss, and a short explanation of its function in the sentence —
*why Deo and not Deum*. Rubrics carry a narrative layer describing what is
happening at the altar. The corpus is the data behind the Scrutabor
reading app ([scrutabor](https://github.com/scrutabor/scrutabor)), live at
[scrutabor.org](https://scrutabor.org).

**Status: working edition.** 111 texts, fully annotated in both languages:
the complete Ordinary of the Mass, the prayers after low Mass, the common
prayers, three litanies, the prayers for the dead, the first psalm stanza,
and the complete Propers of the four Sundays of Advent — with the 1962
temporal calendar computed for 76 years and verified against the Missale's
own table. Every analysis carries its sources, a confidence grade and a
review state, and nothing is presented as settled until it has passed
expert review. Every text has been collated against at least two
independent witnesses and adversarially reviewed, and the disputed
readings are listed rather than hidden.

## Design

One document per text, JSON, UTF-8 — the Latin, the parse, both gloss
layers and both translations together, every editorial claim gathered at
the foot:

```
texts/<category>/<name>.json  the text: Latin + morphology + both languages
lexicon/                      one lexicon, three files (heads, Polish, English)
kalendarium/                  the 1962 temporal cycle, computed and verified
witnesses/<text-id>/          witness transcriptions + adjudicated apparatus
build_reader/, build.py       the reader edition the app ships
checks/, run_checks.py        mechanical validation (see below)
```

Word ids are stable forever — external references (spaced-repetition
decks, links) never break. `SCHEMA.md` documents the format,
`ORTHOGRAPHY.md` the editorial policy (1962 liturgical orthography),
`TERMINOLOGY.md` the gloss-language vocabulary contract.

## How correctness is defended

The guiding rule: no unreviewed single-source claim. Concretely:

- **Text fidelity by collation.** Every text is compared, character by
  character, against independent witnesses of the same recension; the
  substantive text must match with zero divergence. Edition-variable
  accidentals (punctuation, capitalization, capital accents) are each
  adjudicated in a per-text apparatus with a recorded ruling.
- **Mechanical linting.** Orthography rules, accent-versus-syllable
  verification, cross-reference and quoted-form checks, terminology bans,
  and coverage parity between gloss languages run on every push.
- **Provenance on every claim.** Each analysis names its sources and
  confidence; disagreements are flagged for review rather than resolved
  silently.

Run the checks locally (Python 3.10+, standard library only):

```bash
python run_checks.py ordinarium.confiteor
python -m checks.apparatus --write  # regenerate derived apparatus summaries
```

The verdict line names its subject — text, word count, languages,
witnesses, adjudicated variants — and the gate refuses to pass on zero of
any of them.

Documents are kept in one layout, so that a diff over a text stays
readable: one word to a line, with its morphology beside it.

```bash
python -m checks.layout --check   # is every file in layout?
python -m checks.layout           # put them there
```

## Contributing

Corrections are welcome as issues or pull requests — a philological
argument with sources beats a bare diff. The review workflow and
contributor guide will be published as the corpus grows.

## License

Segment translations of prayers the modern Roman Missal still carries follow
the received wording of the current vernacular editions, so that a reader
meets the words in the form the Church prays them today: the English of the
International Commission on English in the Liturgy and the Polish of the
Mszał Rzymski dla diecezji polskich and, in the scripture the Mass reads,
the Biblia Tysiąclecia — all used with acknowledgement and adapted only
where this edition's Latin differs from theirs. The word-by-word glosses,
the notes, the apparatus and the rubrical narratives are this edition's own
work.

The editorial layer — the word-by-word glosses, the analyses and notes,
the apparatus, the rubrical narratives, the introductions, and the
translations this edition wrote itself — is licensed under
[CC BY-SA 4.0](LICENSE), including the EU database right in the
compilation. The Latin texts this edition prints — the 1962 Missale
Romanum and the Clementine psalter — are in the public domain. The
received vernacular wordings described above remain their owners' and
this repository does not relicense them: a passage that follows one names
the work it follows in a per-segment citation in the data
(`translation_citations`), whether that wording comes from a printed
translation of scripture or from the current Missal. One exception is
named here rather than left to be found: the Polish of the *Dómine, non
sum dignus* said at the rail keeps the traditional Wujek-shaped wording
against the current Missal's, and carries no citation until its exact
source is settled. The validation code in `checks/` and
`run_checks.py` is licensed under [AGPL-3.0](checks/LICENSE).

Witness transcriptions marked `do` were derived from the Divinum Officium
Project. The archived snapshot was checked at revision
`712035707cf1bbab75d22966fb1ceabaecae592f` (2026-08-05); that revision's
README grants the MIT License. Its required permission notice is preserved in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). These witness files are
source evidence, not an endorsement by the Divinum Officium Project.

