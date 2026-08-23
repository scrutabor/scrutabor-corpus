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

The Polish and English translations are either this edition's own renderings
from the printed Latin or revisions made openly from page-verified historical
translations that are in the public domain. A defined familiar core — such as
the Lord's Prayer, Hail Mary, Creeds, ordinary responses and selected litanies
— retains the forms readers know where those forms are historically attested
or consist of fixed elementary formulas. Modern vernacular missals and Bible
translations remain in the source registry only where they supplied reference
evidence or recorded prior exposure; no current segment cites them as its
wording source. The word-by-word glosses, notes, apparatus and rubrical
narratives are this edition's own work.

The editorial layer — the word-by-word glosses, analyses and notes,
apparatus, rubrical narratives, introductions, and translations this edition
wrote itself — is licensed under
[CC BY-SA 4.0](LICENSE), including the EU database right in the
compilation. The Latin texts this edition prints — the 1962 Missale
Romanum and the Clementine psalter — are in the public domain. The
historical translations named in per-segment `translation_citations` remain
public-domain source material; the citations identify the wording basis and
the exact pages examined rather than claiming ownership of those source
texts. Contemporary wording is not reproduced under a bare acknowledgement.
The validation code in `checks/` and
`run_checks.py` is licensed under [AGPL-3.0](checks/LICENSE).

The rights report counts every translated `verse segment × language` site,
including a translation with no wording citation. An uncited site is counted
as this edition's own wording; a site with several cited wording sources takes
the most restrictive recorded status. Removing a citation therefore changes a
site's classification instead of removing it from the denominator. These are
provenance states recorded by the repository, not legal conclusions.

[`translation-provenance.json`](translation-provenance.json) is the exhaustive
site ledger. It binds each public origin and review state to hashes of the exact
Latin source segment and target string, so a changed translation cannot retain
an old state silently. The schema still admits `working-unsettled` for future
work: it means that a site's independent-origin or historical-wording review is
not complete, not that infringement or ecclesiastical disapproval has been
established.

Witness transcriptions marked `do` were derived from the Divinum Officium
Project. The archived snapshot was checked at revision
`712035707cf1bbab75d22966fb1ceabaecae592f` (2026-08-05); that revision's
README grants the MIT License. Its required permission notice is preserved in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). These witness files are
source evidence, not an endorsement by the Divinum Officium Project.
