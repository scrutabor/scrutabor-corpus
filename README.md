# Scrutabor corpus

Word-by-word annotated Latin sacral texts — the traditional Roman liturgy
(1962 Missale Romanum) first, the Church's common prayers as the corpus
grows — with gloss layers in Polish and English.

Every Latin word carries its lemma, a full morphological analysis, a
reading gloss, and a short explanation of its function in the sentence —
*why Deo and not Deum*. Rubrics carry a narrative layer describing what is
happening at the altar. The corpus is the data behind the Scrutabor
reading app ([scrutabor](https://github.com/scrutabor/scrutabor)).

**Status: working edition.** One text so far (the Confiteor, servers'
variant), fully annotated in both languages. Every analysis carries its
sources, a confidence grade, and a review state; nothing is presented as
settled until it has passed expert review.

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

The corpus content (texts, glosses, apparatus, documentation) is licensed
under [CC BY-SA 4.0](LICENSE). The validation code in `checks/` and
`run_checks.py` is licensed under [AGPL-3.0](checks/LICENSE).

Liturgical Latin texts of the 1962 Missale Romanum are in the public
domain; the annotations, glosses, translations, and apparatus are original
work of the Scrutabor project.
