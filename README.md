# Scrutabor corpus

Word-by-word annotated Latin sacral texts — the traditional Roman liturgy
(1962 Missale Romanum) first, the Church's common prayers as the corpus
grows — with gloss layers in Polish and English.

Every Latin word carries its lemma, a full morphological analysis, and a
reading gloss. A deliberately smaller set also carries a contextual
explanation where idiom, ellipsis, translation, textual history, or sacred
imagery adds something the structured analysis cannot say. Rubrics carry a
narrative layer describing what is happening at the altar. The corpus is the
data behind the Scrutabor reading app
([scrutabor](https://github.com/scrutabor/scrutabor)), live at
[scrutabor.org](https://scrutabor.org).

**Status: working edition.** 122 texts, fully annotated in both languages:
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

Neutral cores and independently publishable language packages, JSON, UTF-8:

```
texts/<category>/<name>.json  Latin, morphology and neutral editorial topology
languages/<lang>/             manifest, text layers, senses and provenance
lexicon/lemmata.json          language-neutral dictionary heads
kalendarium/                  the 1962 temporal cycle, computed and verified
witnesses/<text-id>/          witness transcriptions + adjudicated apparatus
build_reader/, build.py       the reader edition the app ships
checks/, run_checks.py        mechanical validation (see below)
```

The reader edition uses descriptive base paths (`texts/`, `tables/`,
`lexicon/heads.json`, `calendar.json`, and `concordance.json`) and mirrors each
published language under `languages/<lang>/`. Root and language manifests make
the base and every language independently packageable for mobile downloads or
offline archives. The shared Latin concordance and each package's localized
concordance name candidate texts and segments before they are opened.
Localized titles and aliases travel in the same language manifest, so a
partial package exposes only readings it can render and a one-language mobile
download needs no index from another package. The compact JSON keeps one
logical record per line. Table and text addresses come from tracked append-only files
under `build_reader/registry/`; after adding a genuinely new record, run
`python -m build_reader.update_registry` and review only the appended lines.
Ordinary builds refuse to invent or renumber those addresses.

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
  and completeness against each language manifest run on every push.
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

Documents are kept in one layout, so that a diff over a text stays readable:
one Latin word to a line in the core and one target-language entry to a line in
its package. Editing Polish does not touch English or Latin.

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

Each [`languages/<lang>/translation-provenance.json`](languages/) is the
exhaustive ledger for that language's manifest. It binds each public origin and
review state to hashes of the exact
Latin source segment and target string, so a changed translation cannot retain
an old state silently. The schema still admits `working-unsettled` for future
work: it means that a site's independent-origin or historical-wording review is
not complete, not that infringement or ecclesiastical disapproval has been
established.

Each language also carries a grouped `translation-basis.json`. It distinguishes
wording that is exact, normalized, revised, or assembled as a traditional
composite. The build expands that relationship into the one language-and-text
file a reader has already requested, avoiding both a second request and a
repeated field at every authored translation site.

Witness transcriptions marked `do` were derived from the Divinum Officium
Project. The archived snapshot was checked at revision
`712035707cf1bbab75d22966fb1ceabaecae592f` (2026-08-05); that revision's
README grants the MIT License. Its required permission notice is preserved in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). These witness files are
source evidence, not an endorsement by the Divinum Officium Project.
