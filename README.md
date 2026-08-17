# Scrutabor corpus

Word-by-word annotated Latin sacral texts — the traditional Roman liturgy
(1962 Missale Romanum) first, the Church's common prayers as the corpus
grows — with gloss layers in Polish and English.

Every Latin word carries its lemma, a full morphological analysis, a
reading gloss, and a short explanation of its function in the sentence —
*why Deo and not Deum*. Rubrics carry a narrative layer describing what is
happening at the altar. The corpus is the data behind the Scrutabor
reading app ([scrutabor](https://github.com/scrutabor/scrutabor)).

**Status: working edition.** 72 texts, fully annotated in both languages:
the complete Ordinary of the Mass, the prayers after low Mass, the common
prayers, the first psalm stanza, and the complete Proper for the First Sunday
of Advent. Every analysis carries its sources, a confidence grade and a review
state, and nothing is presented as settled until it has passed expert review.
Every text has been collated against at least two independent witnesses and
adversarially reviewed, and the disputed readings are listed rather than
hidden.

## Design

Two layers per text, JSON, UTF-8:

```
texts/<category>/<name>.json           Latin source + morphology (language-neutral)
glosses/<lang>/<category>.<name>.json  per-language layer (glosses, functions,
                                       translations, rubric narratives)
witnesses/<text-id>/                   witness transcriptions + adjudicated apparatus
checks/, run_checks.py                 mechanical validation (see below)
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

The corpus content (texts, glosses, apparatus, documentation) is licensed
under [CC BY-SA 4.0](LICENSE). The validation code in `checks/` and
`run_checks.py` is licensed under [AGPL-3.0](checks/LICENSE).

Witness transcriptions marked `do` were derived from the Divinum Officium
Project. The archived snapshot was checked at revision
`712035707cf1bbab75d22966fb1ceabaecae592f` (2026-08-05); that revision's
README grants the MIT License. Its required permission notice is preserved in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). These witness files are
source evidence, not an endorsement by the Divinum Officium Project.

Liturgical Latin texts of the 1962 Missale Romanum are in the public
domain. The annotations, glosses, apparatus, and editorial contributions to
the translations are original work of the Scrutabor project; inherited or
received translation bases are identified beside the segments that use them.
